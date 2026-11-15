# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Daily temperature swing, surface brightness, top-soil wetness and wind speed from NASA POWER.

Writes data/derived/power_extra_cells.json (the Moon part's areas, grazing_cells.json)
and data/derived/mars_power_extra.json (the Mars part's squares, mars_cells.json).

Two steps, each safe to run again (nothing on disk is asked for twice):

    uv run python scripts/build_power_extra.py fetch            # polar blocks first, then the rest of the world
    uv run python scripts/build_power_extra.py fetch --only moon
    uv run python scripts/build_power_extra.py build            # no network; writes the two JSON files

The four parameters, as the service's own parameter list names them (asked on
14 November 2026, saved under data/raw/power_extra/parameters/):
- T2M_RANGE       daily range of air temperature 2 m above the ground, C (POWER, from MERRA-2 hourly values);
- ALLSKY_SRF_ALB  all-sky surface albedo, dimensionless (CERES SYN1deg, 1 degree boxes);
- GWETTOP         surface soil wetness, top 5 cm, 0 dry to 1 saturated (MERRA-2 land model);
- WS10M           wind speed 10 m above the ground, m/s (POWER, from MERRA-2).

The service is asked one parameter and one 10 degree block at a time, one request
at a time and at least 1.5 seconds apart (another group uses the same service
tonight); on a refusal (429 or a server fault) it backs off a full minute; on a
dropped network it waits and tries again; on a request for a login it stops.
Raw answers are kept in data/raw/power_extra/ with a log of every request.
"""
from __future__ import annotations

import argparse
import datetime
import http.client
import json
import math
import os
import statistics
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from twinfinder import cloud, temperature

# ---- what is asked for --------------------------------------------------------------------------------

PARAMETERS = ("T2M_RANGE", "ALLSKY_SRF_ALB", "GWETTOP", "WS10M")
FIELD = {"T2M_RANGE": "t2m_range_c", "ALLSKY_SRF_ALB": "albedo", "GWETTOP": "soil_wetness_top",
         "WS10M": "wind_10m_ms"}
UNITS = {"T2M_RANGE": "C", "ALLSKY_SRF_ALB": "dimensionless", "GWETTOP": "1", "WS10M": "m/s"}   # as the answers name them
RANGE = {"T2M_RANGE": (0.0, 60.0), "ALLSKY_SRF_ALB": (0.0, 1.0), "GWETTOP": (0.0, 1.0), "WS10M": (0.0, 50.0)}
GRID = {"T2M_RANGE": "merra2", "ALLSKY_SRF_ALB": "ceres", "GWETTOP": "merra2", "WS10M": "merra2"}
MONTHS = cloud.MONTHS
FILL_VALUE = -999.0
ICE_WETNESS = 0.995     # top-soil wetness at or above this in all 12 months: the model's grid point is ice, not soil

USER_AGENT = cloud.USER_AGENT          # "twinfinder/0.1", nothing personal
URL_PATTERN = cloud.URL_PATTERN
MIN_GAP_S = 1.5                        # at least this long between two requests
REFUSAL_WAIT_S = 60.0                  # back off a full minute on 429 or a server fault
NET_WAIT_S = 20.0                      # first wait after a dropped connection; then 40, 60 ...
ATTEMPTS = 6

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data/raw/power_extra"
PARAMS_DIR = RAW / "parameters"
LOG = RAW / "fetch_log.jsonl"
MOON_PLACES = ROOT / "data/derived/grazing_cells.json"
MARS_PLACES = ROOT / "data/derived/mars_cells.json"
DAILY_POINTS = ROOT / "data/raw/power_temperature/daily_points"     # read only: the temperature group's daily series
OUT_MOON = ROOT / "data/derived/power_extra_cells.json"
OUT_MARS = ROOT / "data/derived/mars_power_extra.json"

CREDIT = ("The data was obtained from National Aeronautics and Space Administration (NASA) Langley Research "
          "Center's Prediction Of Worldwide Energy Resources (POWER) project funded through the NASA Earth "
          "Science Division. The data was obtained from the POWER Project's Climatology API {version} on {date}. "
          "(Daily temperature range, top-soil wetness and 10 m wind speed: MERRA-2. Surface albedo: CERES SYN1deg.)")
LICENCE = ("NASA POWER asks for the credit line above (https://power.larc.nasa.gov/docs/referencing/); NASA Earth "
           "science data carry no restriction on use unless marked (CC0; "
           "https://www.earthdata.nasa.gov/engage/open-data-services-software-policies/data-use-guidance). "
           "No key, no login.")


class LoginRequired(RuntimeError):
    """The service asked for a login or refused us (401 or 403): we do not go on."""


# ---- reading an answer ----------------------------------------------------------------------------------

def read_answer(raw, parameter: str) -> dict[tuple[float, float], tuple[list[float | None], float | None]]:
    """{(lat, lon): ([12 monthly values, January first], annual value)} from one regional answer.

    The service's fill value becomes None; a real 0.0 stays 0.0. The units must be
    those named in UNITS and every value inside RANGE; an answer without grid
    points (an error message), for another parameter, or with a text value is an error.
    """
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8")
    data = json.loads(raw) if isinstance(raw, str) else raw
    if not isinstance(data, dict) or not isinstance(data.get("features"), list) or not data["features"]:
        messages = data.get("messages") if isinstance(data, dict) else None
        raise ValueError(f"not a regional climatology answer: {messages!r}")
    units = ((data.get("parameters") or {}).get(parameter) or {}).get("units")
    if units != UNITS[parameter]:
        raise ValueError(f"{parameter}: units {units!r}, expected {UNITS[parameter]!r}")
    header = data.get("header") if isinstance(data.get("header"), dict) else {}
    fills = {FILL_VALUE}
    if isinstance(header.get("fill_value"), (int, float)) and not isinstance(header.get("fill_value"), bool):
        fills.add(float(header["fill_value"]))
    low, high = RANGE[parameter]

    def value(v, where):
        if v is None:
            return None
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise ValueError(f"{parameter} {where} is not a number: {v!r}")
        v = float(v)
        if v in fills or math.isnan(v):
            return None
        if not low <= v <= high:
            raise ValueError(f"{parameter} {where} out of range: {v}")
        return v

    out = {}
    for feature in data["features"]:
        try:
            lon, lat = (float(x) for x in feature["geometry"]["coordinates"][:2])   # GeoJSON: longitude first
            months = feature["properties"]["parameter"][parameter]
            if not isinstance(months, dict):
                raise TypeError("months are not a mapping")
        except (KeyError, TypeError, IndexError, ValueError) as error:
            raise ValueError(f"answer does not hold {parameter} by grid point: {error!r}") from error
        if lon >= 180.0:
            lon -= 360.0
        where = f"at {lat}, {lon}"
        out[(lat, lon)] = ([value(months.get(m), f"{m} {where}") for m in MONTHS],
                           value(months.get("ANN"), f"ANN {where}"))
    return out


# ---- grids and request blocks ----------------------------------------------------------------------------

def grid_key(parameter: str, lat: float, lon: float) -> tuple[float, float]:
    """The grid point a place reads its value at: nearest MERRA-2 point, or the 1 degree CERES box holding it."""
    if GRID[parameter] == "merra2":
        return temperature.grid_point(lat, lon)
    return cloud.grid_box(lat, lon)


def tiles_for(places) -> list[tuple[int, int, int, int]]:
    """10 degree blocks whose answers hold every place's MERRA-2 point and its 1 degree box."""
    return sorted(set(temperature.tiles_for_cells(places)) | set(cloud.tiles_for(cloud.boxes_of(places))))


def fetch_jobs(moon_tiles, mars_tiles) -> list[tuple[str, tuple[int, int, int, int], str]]:
    """(parameter, block, part) to ask, the Moon part's polar blocks first; a block is never listed twice."""
    jobs = [(p, tuple(t), "moon") for t in moon_tiles for p in PARAMETERS]
    seen = {tuple(t) for t in moon_tiles}
    for t in mars_tiles:
        if tuple(t) in seen:
            continue
        seen.add(tuple(t))
        jobs += [(p, tuple(t), "mars") for p in PARAMETERS]
    return jobs


# ---- fetching -----------------------------------------------------------------------------------------------

class Pacer:
    """Keeps the start of two requests at least `gap` seconds apart."""

    def __init__(self, gap: float = MIN_GAP_S, clock=time.monotonic, sleep=time.sleep):
        self.gap, self.clock, self.sleep, self.last = gap, clock, sleep, None

    def wait(self) -> None:
        if self.last is not None:
            since = self.clock() - self.last
            if since < self.gap:
                self.sleep(self.gap - since)
        self.last = self.clock()


def _retry_after(error: urllib.error.HTTPError) -> float | None:
    try:
        return min(max(float(error.headers.get("Retry-After")), 1.0), 600.0)
    except (AttributeError, TypeError, ValueError):
        return None


def fetch_one(parameter: str, tile, raw_dir: Path, opener=None, sleep=time.sleep, attempts: int = ATTEMPTS,
              timeout: float = 120.0) -> tuple[Path, bool]:
    """Path of the raw answer for one parameter and block, asking the service only if it is not on disk.

    Returns (path, asked). A refusal (429) or a server fault (5xx): wait at least a
    minute and try again. A dropped connection: wait 20, 40, 60 ... seconds and try
    again. A login request (401, 403): LoginRequired at once. Any other answer
    (404, 422): raised. A body that is not an answer is not kept.
    """
    raw_dir = Path(raw_dir)
    dest = raw_dir / cloud.raw_name(parameter, tuple(tile))
    if dest.exists():
        return dest, False
    opener = opener or urllib.request.urlopen
    request = urllib.request.Request(cloud.regional_url(parameter, tuple(tile)), headers={"User-Agent": USER_AGENT})
    body = b""
    for attempt in range(1, attempts + 1):
        try:
            with opener(request, timeout=timeout) as response:
                body = response.read()
            break
        except urllib.error.HTTPError as error:
            if error.code in (401, 403):
                raise LoginRequired(f"{error.code} from the service for {request.full_url}") from error
            busy = error.code == 429 or 500 <= error.code < 600
            if not busy or attempt == attempts:
                raise
            sleep(max(REFUSAL_WAIT_S, _retry_after(error) or 0.0))
        except (urllib.error.URLError, ConnectionError, TimeoutError, http.client.IncompleteRead, OSError):
            if attempt == attempts:
                raise
            sleep(min(NET_WAIT_S * attempt, 300.0))
    read_answer(body, parameter)                     # raises if this is not an answer: nothing is kept
    raw_dir.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    part.write_bytes(body)
    os.replace(part, dest)
    return dest, True


def now_utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_all(jobs, raw_dir: Path, log_path: Path, pacer: Pacer | None = None, fetch=fetch_one, sleep=time.sleep,
              rounds: int = 3, stop_after: int = 3, out=print) -> dict:
    """Make sure every job's raw answer is on disk. Returns counts and the jobs that failed.

    A job that fails all its rounds is listed and the run goes on with the next one;
    after `stop_after` failed jobs in a row (the network is down) the run stops, so a
    second run later picks up where this one ended. A login request stops the run.
    """
    raw_dir, log_path = Path(raw_dir), Path(log_path)
    raw_dir.mkdir(parents=True, exist_ok=True)
    pacer = pacer or Pacer()
    asked, on_disk, failed, in_a_row = 0, 0, [], 0
    started = time.time()

    def log(entry):
        with open(log_path, "a") as handle:
            handle.write(json.dumps({"time": now_utc(), **entry}) + "\n")

    for n, (parameter, tile, part) in enumerate(jobs, 1):
        name = cloud.raw_name(parameter, tuple(tile))
        if (raw_dir / name).exists():
            on_disk += 1
            continue
        for round_ in range(1, rounds + 1):
            pacer.wait()
            try:
                path, was_asked = fetch(parameter, tuple(tile), raw_dir, sleep=sleep)
            except LoginRequired as error:
                log({"file": name, "part": part, "error": f"LoginRequired: {error}", "round": round_})
                out(f"{now_utc()} STOP: the service asked for a login ({error})", flush=True)
                raise
            except Exception as error:  # noqa: BLE001 - logged, retried, then listed as failed
                log({"file": name, "part": part, "error": f"{type(error).__name__}: {error}", "round": round_})
                out(f"{now_utc()} {name}: {type(error).__name__}: {error} (round {round_} of {rounds})", flush=True)
                if round_ == rounds:
                    failed.append((parameter, tuple(tile), part))
                    in_a_row += 1
                else:
                    sleep(REFUSAL_WAIT_S * round_)
                continue
            in_a_row = 0
            if was_asked:
                asked += 1
                log({"url": cloud.regional_url(parameter, tuple(tile)), "file": name, "part": part,
                     "bytes": path.stat().st_size})
                if asked % 25 == 0:
                    rate = (time.time() - started) / asked
                    out(f"{now_utc()} asked {asked} (at {n} of {len(jobs)}, {part}); {rate:.1f} s a request",
                        flush=True)
            break
        if in_a_row >= stop_after:
            out(f"{now_utc()} {in_a_row} blocks failed in a row: stopping; run again later", flush=True)
            break
    return {"asked": asked, "on_disk_before": on_disk, "failed": failed}


# ---- the table of places ---------------------------------------------------------------------------------------

def place_record(lat: float, lon: float, by_param: dict) -> dict:
    """Twelve months and the year of each parameter at one place; null where unknown, never 0."""
    record = {}
    for parameter in PARAMETERS:
        row = by_param.get(parameter, {}).get(grid_key(parameter, lat, lon))
        months = None if row is None or all(v is None for v in row[0]) else list(row[0])
        field = FIELD[parameter]
        record[field] = months
        record[field + "_year"] = row[1] if months is not None else None
    wet = record["soil_wetness_top"]
    record["soil_wetness_ice_flag"] = (None if wet is None or any(v is None for v in wet)
                                       else all(v >= ICE_WETNESS for v in wet))
    merra, ceres = temperature.grid_point(lat, lon), cloud.grid_box(lat, lon)
    record["grid_merra2"] = [merra[0], merra[1]]
    record["grid_ceres"] = [ceres[0], ceres[1]]
    return record


def places_table(places, by_param: dict) -> dict:
    return {place["id"]: place_record(place["lat"], place["lon"], by_param) for place in places}


def annual_check(rows: dict) -> dict:
    """How the service's annual value sits against the plain mean of the months that have a value."""
    compared = equal = 0
    largest = 0.0
    for months, ann in rows.values():
        known = [v for v in months if v is not None]
        if not known or ann is None:
            continue
        compared += 1
        gap = abs(ann - sum(known) / len(known))
        equal += gap <= 0.006
        largest = max(largest, gap)
    return {"rows_compared": compared, "rows_equal_within_0.006": equal, "largest_gap": round(largest, 4)}


def mean_daily_range(highs: dict, lows: dict, last_year: int, first_year: int | None = None) -> list[float | None]:
    """Mean of (highest hour - lowest hour) of each day by calendar month, over the years up to last_year."""
    by_month: list[list[float]] = [[] for _ in range(12)]
    for day, high in highs.items():
        low = lows.get(day)
        if high is None or low is None or day.year > last_year or (first_year and day.year < first_year):
            continue
        by_month[day.month - 1].append(high - low)
    return [sum(v) / len(v) if v else None for v in by_month]


# ---- meta ----------------------------------------------------------------------------------------------------

def agreed_header(heads: list[dict]) -> dict:
    """The one header all raw answers of a parameter share; an error if they disagree."""
    if not heads:
        raise ValueError("no raw answer was read")
    first = heads[0]
    for head in heads[1:]:
        for key in ("version", "sources", "start", "end", "fill_value"):
            if head.get(key) != first.get(key):
                raise ValueError(f"raw answers disagree about {key}: {first.get(key)!r} and {head.get(key)!r}")
    return {key: first.get(key) for key in ("name", "version", "sources", "start", "end", "fill_value")}


def _date(text: str) -> str:
    return f"{text[0:4]}-{text[4:6]}-{text[6:8]}"


GRID_TEXT = {
    "merra2": ("MERRA-2 grid, 0.5 degree of latitude by 0.625 degree of longitude (about 55 km by 15 to 35 km at "
               "these latitudes); each place takes the nearest grid point (grid_merra2)"),
    "ceres": ("CERES SYN1deg grid, 1 degree boxes (about 111 km tall); each place takes the box that holds it "
              "(grid_ceres); polewards of 45 degrees neighbouring boxes along a latitude often carry the same value "
              "(see albedo_repeat_check)"),
}

WHAT = {
    "T2M_RANGE": (
        "Mean daily swing of air temperature 2 m above the ground: the day's warmest hour minus its coldest hour, "
        "averaged over the days of each calendar month, in degrees C. A model value (MERRA-2 reanalysis, worked out "
        "by POWER from hourly values) for the grid point nearest the place. Checked on this run against the daily "
        "series of six grid points kept by the temperature group: it equals the mean of the daily ranges of "
        "2001 to 2020 (see t2m_range_check)."),
    "ALLSKY_SRF_ALB": (
        "Surface albedo: the share of the sunlight reaching the ground that the ground sends back, 0 to 1, as a "
        "mean for each calendar month under the real sky (all sky, clouds included). It is the brightness of "
        "whatever covers the ground in that month, snow and ice included, over a coarse grid box of 1 degree "
        "(CERES SYN1deg as served by POWER). Null in months the service gives no value (no sunlight: polar night)."),
    "GWETTOP": (
        "Surface soil wetness of the top 5 cm: a model value from 0 (completely dry) to 1 (saturated), monthly "
        "mean, from the MERRA-2 land model (reanalysis) at the grid point nearest the place."),
    "WS10M": (
        "Mean wind speed 10 m above the ground, in metres per second, averaged over all hours of each calendar "
        "month: a model value (MERRA-2 reanalysis, served by POWER) at the grid point nearest the place."),
}
WHAT_NOT = {
    "T2M_RANGE": (
        "Not a measurement at the place and not the ground's own swing (the ground's surface swings more than the "
        "air above it). Not the swing on a clear day (it is an average over all days, cloudy ones included), not "
        "the range between the month's extremes, and not the swing during the hours of low Sun. A mean over a grid "
        "box at the box's own mean height, which near an ice cap or a mountain coast lies far from the place."),
    "ALLSKY_SRF_ALB": (
        "Not the colour or brightness of the bare rock at the place: a box of about 111 km by 20 to 110 km mixes "
        "rock, snow, ice, water and plants, and in the months when snow lies it is mostly the snow. Not a "
        "measurement at the place, and not the albedo of the ground at low Sun angles alone. Low-Sun months near "
        "the polar night rest on few hours of sunlight and are the least sure. Not comparable as-is with lunar "
        "albedo figures, which are measured another way (often at one wavelength and one viewing angle)."),
    "GWETTOP": (
        "Not a measurement: a model value, not a probe in the ground, and not a percent of water by volume. Near "
        "the poles and on high plateaus the top layer is frozen or under snow for much of the year; how the model "
        "counts frozen water was not checked on this run, so winter values say nothing sure about liquid water or "
        "dust. A grid box mixes the place with its surroundings, glaciers and wetlands included. Where the model's "
        "grid point is ice (glacier, ice sheet) it gives 1.00 in every month: that is the model's ice, not wet "
        "soil, and soil_wetness_ice_flag is true there (even where the place itself is bare rock, such as the "
        "McMurdo Dry Valleys)."),
    "WS10M": (
        "Not a measurement at the place and not the wind a person or a rover would meet at the ground (at 1 to 2 m "
        "the wind is slower, behind a ridge it can be far slower, in a gap or at the foot of an ice slope far "
        "faster). Not gusts, not the strongest wind of the month and not the wind direction. A mean over a grid "
        "box of tens of kilometres with smoothed hills, so it misses valley and katabatic winds smaller than the box."),
}
_ANN = ("the service's annual value (ANN), as given; it lies within a few hundredths of the plain mean of the 12 "
        "months shown (see annual_check)")
YEAR_TEXT = {
    "T2M_RANGE": _ANN,
    "ALLSKY_SRF_ALB": ("the service's annual value (ANN), as given: close to the plain mean of the months that have a "
                       "value, so near the poles a mean over the sunlit months only, not weighted by sunlight "
                       "(see annual_check)"),
    "GWETTOP": _ANN,
    "WS10M": _ANN,
}


def fields_meta(heads: dict, definitions: dict) -> dict:
    """What each field is and is not, with the service's own name, definition, units and sources."""
    out = {}
    for parameter in PARAMETERS:
        head, definition = heads[parameter], definitions[parameter]
        out[FIELD[parameter]] = {
            "parameter": parameter,
            "service_name": definition["name"],
            "service_definition": definition["definition"],
            "units": UNITS[parameter] if UNITS[parameter] != "1" else "1 (a fraction from 0 to 1)",
            "units_in_parameter_list": definition.get("units"),
            "sources_named_by_service": list(head["sources"] or []),
            "grid": GRID_TEXT[GRID[parameter]],
            "what_it_is": WHAT[parameter],
            "what_it_is_not": WHAT_NOT[parameter],
            "year_field": f"{FIELD[parameter]}_year: {YEAR_TEXT[parameter]}",
        }
    return out


def read_definitions() -> dict:
    listing = json.loads((PARAMS_DIR / "manager_list_RE_climatology.json").read_text())
    out = {}
    for parameter in PARAMETERS:
        item = listing[parameter]
        out[parameter] = {"name": item["name"], "definition": item["definition"], "units": item["units"],
                          "type": item.get("type"), "source_in_list": item.get("source")}
    return out


# ---- build -------------------------------------------------------------------------------------------------------

def write_json(path: Path, value) -> None:
    text = json.dumps(value, separators=(",", ":"), allow_nan=False)    # raises before anything is written
    path = Path(path)
    side = path.with_name(path.name + ".part")
    side.write_text(text)
    os.replace(side, path)


def moon_places() -> list[dict]:
    return [{"id": c["id"], "lat": c["lat"], "lon": c["lon"], "hemisphere": c.get("hemisphere")}
            for c in json.loads(MOON_PLACES.read_text())["cells"]]


def mars_places() -> list[dict]:
    return [{"id": c["id"], "lat": c["lat"], "lon": c["lon"]}
            for c in json.loads(MARS_PLACES.read_text())["cells"].values()]


def fetch(only: str, pause: float) -> int:
    moon, mars = moon_places(), mars_places()
    moon_tiles = tiles_for(moon) if only in ("moon", "all") else []
    mars_tiles = tiles_for(mars) if only in ("mars", "all") else []
    jobs = fetch_jobs(moon_tiles, mars_tiles)
    if only == "mars":
        jobs = [(p, t, "mars") for p, t, _ in jobs]
    print(f"{now_utc()} {len(moon)} Moon areas, {len(mars)} Mars squares; {len(jobs)} answers wanted "
          f"({sum(1 for j in jobs if j[2] == 'moon')} Moon part first); pause {pause} s", flush=True)
    result = fetch_all(jobs, RAW, LOG, pacer=Pacer(pause))
    on_disk = sum((RAW / cloud.raw_name(p, t)).exists() for p, t, _ in jobs)
    print(f"{now_utc()} done: asked {result['asked']}, already on disk {result['on_disk_before']}, "
          f"failed {len(result['failed'])}; on disk {on_disk} of {len(jobs)}", flush=True)
    for job in result["failed"][:20]:
        print(f"  FAILED {job}", flush=True)
    return 0 if on_disk == len(jobs) else 1


def load_rows(tiles) -> tuple[dict, dict]:
    """Rows by parameter and grid point from the raw answers of these blocks; and the agreed headers."""
    missing = [cloud.raw_name(p, t) for p in PARAMETERS for t in tiles if not (RAW / cloud.raw_name(p, t)).exists()]
    if missing:
        raise SystemExit(f"{len(missing)} raw answers missing (run fetch), first {missing[:3]}")
    by_param, heads = {}, {}
    for parameter in PARAMETERS:
        rows, headers = {}, []
        for tile in tiles:
            body = (RAW / cloud.raw_name(parameter, tile)).read_bytes()
            rows.update(read_answer(body, parameter))
            headers.append(cloud.answer_header(body))
        by_param[parameter], heads[parameter] = rows, agreed_header(headers)
    return by_param, heads


def fetched_span(names: set[str]) -> str | None:
    times = {}
    if LOG.exists():
        for line in LOG.read_text().splitlines():
            entry = json.loads(line)
            if "bytes" in entry:
                times[entry["file"]] = entry["time"]
    for name in names:
        if name not in times and (RAW / name).exists():
            stamp = datetime.datetime.fromtimestamp((RAW / name).stat().st_mtime, datetime.timezone.utc)
            times[name] = stamp.strftime("%Y-%m-%dT%H:%M:%SZ")
    used = sorted(times[n] for n in names if n in times)
    if not used:
        return None
    return used[0] if used[0] == used[-1] else f"{used[0]} to {used[-1]}"


def t2m_range_check(rows: dict) -> dict:
    """T2M_RANGE against the mean daily range of the daily series kept by the temperature group (read only)."""
    places = []
    for path in sorted(DAILY_POINTS.glob("daily_*.json")):
        raw = path.read_bytes()
        lat, lon, _ = temperature.daily_position(raw)
        row = rows.get(grid_key("T2M_RANGE", lat, lon))
        if row is None:
            continue
        highs, lows = temperature.read_daily(raw, "T2M_MAX"), temperature.read_daily(raw, "T2M_MIN")
        entry = {"grid_point": [lat, lon], "file": str(path.relative_to(ROOT))}
        for last in (2020, 2025):
            daily = mean_daily_range(highs, lows, last_year=last)
            gaps = [abs(c - d) for c, d in zip(row[0], daily) if c is not None and d is not None]
            entry[f"2001_to_{last}"] = {"months_compared": len(gaps),
                                        "months_within_0.011_c": sum(g < 0.011 for g in gaps),
                                        "largest_gap_c": round(max(gaps), 3) if gaps else None}
        places.append(entry)
    total = {last: sum(p[f"2001_to_{last}"]["months_within_0.011_c"] for p in places) for last in (2020, 2025)}
    compared = sum(p["2001_to_2020"]["months_compared"] for p in places)
    return {"how": ("for each daily series on disk (data/raw/power_temperature/daily_points/, NASA POWER daily "
                    "point API, T2M_MAX and T2M_MIN of each day, 2001 to 2025), the mean of (T2M_MAX - T2M_MIN) "
                    "by calendar month over 2001-2020 and over 2001-2025, against this file's T2M_RANGE of the "
                    "same grid point"),
            "months_compared": compared,
            "months_equal_within_0.011_c_2001_to_2020": total[2020],
            "months_equal_within_0.011_c_2001_to_2025": total[2025],
            "reading": ("T2M_RANGE is the mean daily range over 2001 to 2020, though the answers name 2001 to 2025"
                        if compared and total[2020] == compared else
                        "the climatology does not equal the 2001-2020 mean daily range everywhere: see places"),
            "places": places}


def albedo_repeat_check(rows: dict) -> dict:
    """Share of 1 degree boxes whose 12 months equal those of the box to the east, by band of latitude."""
    bands = {"45-70": (45, 70), "70-80": (70, 80), "80-90": (80, 90)}
    out = {}
    for name, (lo, hi) in bands.items():
        same = total = 0
        for (lat, lon), (months, _) in rows.items():
            if not lo <= abs(lat) < hi:
                continue
            east = rows.get((lat, lon + 1.0 if lon + 1.0 < 180 else lon + 1.0 - 360.0))
            if east is None or all(v is None for v in months):
                continue
            total += 1
            same += east[0] == months
        out[f"{name}_degrees_either_hemisphere"] = {"boxes_compared": total, "equal_to_the_box_east": same}
    return out


def counts(table: dict) -> dict:
    out = {"places": len(table)}
    for field in FIELD.values():
        rows = [r[field] for r in table.values()]
        out[field] = {"all_12_months": sum(1 for r in rows if r and all(v is not None for v in r)),
                      "some_months_null": sum(1 for r in rows if r and any(v is None for v in r)),
                      "no_value": sum(1 for r in rows if r is None)}
    out["soil_wetness_ice_flag_true"] = sum(1 for r in table.values() if r["soil_wetness_ice_flag"] is True)
    return out


def median(values) -> float | None:
    known = [v for v in values if v is not None]
    return round(statistics.median(known), 3) if known else None


def summary(table: dict, hemisphere: dict | None = None) -> dict:
    """Medians over places of the yearly values (and, for the Moon part, by hemisphere)."""
    groups = {"all": list(table)}
    if hemisphere:
        groups["north"] = [i for i in table if hemisphere.get(i) == "N"]
        groups["south"] = [i for i in table if hemisphere.get(i) == "S"]
    return {name: {f + "_year": median(table[i][f + "_year"] for i in ids) for f in FIELD.values()}
            for name, ids in groups.items()}


REFERENCE = [
    ("Haughton crater area, Devon Island", "moon", "75.3_-90.0"),
    ("south-west Iceland", "moon", "63.8_-22.6"),
    ("Pechora Sea coast", "moon", "68.9_54.3"),
    ("McMurdo Dry Valleys", "moon", "-77.6_161.5"),
    ("McMurdo Dry Valleys (Mars square)", "mars", "m_-77.75_161.75"),
    ("Atacama near Yungay", "mars", "m_-24.25_-70.25"),
    ("Tibetan Plateau (Changtang, north)", "mars", "m_36.25_86.75"),
]


def reference_places(moon_table: dict, mars_table: dict) -> list[dict]:
    out = []
    for name, part, pid in REFERENCE:
        record = (moon_table if part == "moon" else mars_table).get(pid)
        out.append({"name": name, "part": part, "id": pid, "values": record})
    return out


def base_meta(heads: dict, definitions: dict, tiles, by_param: dict) -> dict:
    first = heads[PARAMETERS[0]]
    for parameter in PARAMETERS[1:]:
        for key in ("version", "start", "end", "fill_value"):
            if heads[parameter][key] != first[key]:
                raise ValueError(f"{parameter} and {PARAMETERS[0]} disagree about {key}")
    names = {cloud.raw_name(p, t) for p in PARAMETERS for t in tiles}
    fetched = fetched_span(names)
    return {
        "source": (f"NASA POWER {first['name']} {first['version']}, regional endpoint, community RE; "
                   + "; ".join(f"{p}: {', '.join(heads[p]['sources'] or [])}" for p in PARAMETERS)),
        "parameters": list(PARAMETERS),
        "period_named_by_service": f"{_date(first['start'])} to {_date(first['end'])}",
        "period_caution": ("The answers name 2001 to 2025. T2M_RANGE was checked on this run and equals the "
                           "2001-2020 mean daily range (t2m_range_check); the temperature group found the same for "
                           "T2M (temperature_cells.json meta.years_fit). ALLSKY_SRF_ALB, GWETTOP and WS10M were not "
                           "checked for their years."),
        "fill_value": first["fill_value"],
        "url_pattern": URL_PATTERN,
        "fetched": fetched,
        "request_rules_followed": ("one parameter and one 10 x 10 degree block a request, one request at a time and "
                                   "at least 1.5 s apart, a minute's back-off on any refusal, User-Agent "
                                   "twinfinder/0.1, no key, no login"),
        "parameter_list": {"asked": "https://power.larc.nasa.gov/api/system/manager/parameters?community=RE&temporal=climatology",
                           "saved": str(PARAMS_DIR.relative_to(ROOT))},
        "fields": fields_meta(heads, definitions),
        "grid_fields": {"grid_merra2": "[lat, lon] of the MERRA-2 grid point the temperature range, soil wetness "
                                       "and wind speed were read at (nearest to the place centre)",
                        "grid_ceres": "[lat, lon] of the centre of the 1 degree box the albedo was read at",
                        "soil_wetness_ice_flag": (f"true when the top-soil wetness is {ICE_WETNESS} or more in all 12 "
                                                  "months: the model's grid point is ice, so the soil wetness says "
                                                  "nothing about soil there; false otherwise; null when unknown")},
        "null_rule": ("unknown is null, never 0: a field is null when the service gave no month at all for the grid "
                      "point; a month without a value is null inside the list; *_year is null with it"),
        "annual_check": {FIELD[p]: annual_check(by_param[p]) for p in PARAMETERS},
        "albedo_repeat_check": albedo_repeat_check(by_param["ALLSKY_SRF_ALB"]),
        "raw_answers": {"folder": str(RAW.relative_to(ROOT)), "files": len(names)},
        "credit": CREDIT.format(version=first["version"], date=(fetched or "")[:10].replace("-", "/")),
        "licence": LICENCE,
        "coarse_grid_warning": ("Every figure here is a value for a grid box tens of kilometres across, from a model "
                                "(MERRA-2) or a satellite product on a 1 degree grid (CERES); it is never a "
                                "measurement at the place, and many places share one value."),
        "enters_score": "no; displayed columns only",
        "written_by": "agent POWER-EXTRA, scripts/build_power_extra.py build",
    }


def build() -> None:
    """Writes the Moon file from the polar blocks; then the Mars file if all its blocks are on disk."""
    moon, mars = moon_places(), mars_places()
    moon_tiles, mars_tiles = tiles_for(moon), tiles_for(mars)
    definitions = read_definitions()
    for parameter in PARAMETERS:
        if definitions[parameter]["units"] != UNITS[parameter]:
            raise SystemExit(f"{parameter}: the list names units {definitions[parameter]['units']!r}, "
                             f"the answers {UNITS[parameter]!r}")

    moon_rows, moon_heads = load_rows(moon_tiles)
    try:
        mars_rows, mars_heads = load_rows(mars_tiles)
    except SystemExit as missing:
        print(f"Mars part not written: {missing}")
        mars_rows = mars_heads = None
    moon_table = places_table(moon, moon_rows)
    mars_table = places_table(mars, mars_rows) if mars_rows else {}
    range_check = t2m_range_check(moon_rows["T2M_RANGE"])
    refs = reference_places(moon_table, mars_table)
    written = now_utc()

    by_param, heads = moon_rows, moon_heads
    moon_meta = base_meta(heads, definitions, moon_tiles, by_param)
    moon_meta.update({
        "what": ("Daily temperature swing, surface albedo, top-soil wetness and 10 m wind speed by calendar month "
                 "for every area of the Moon part (data/derived/grazing_cells.json), from NASA POWER."),
        "places_source": str(MOON_PLACES.relative_to(ROOT)),
        "written": written,
        "t2m_range_check": range_check,
        "counts": counts(moon_table),
        "medians": summary(moon_table, {p["id"]: p["hemisphere"] for p in moon}),
        "reference_places": [r for r in refs if r["part"] == "moon"],
    })
    write_json(OUT_MOON, {"meta": moon_meta, "cells": moon_table})
    print(f"wrote {OUT_MOON.relative_to(ROOT)} ({OUT_MOON.stat().st_size / 1e6:.1f} MB)")
    if mars_rows is None:
        show(moon_meta, None, range_check, [r for r in refs if r["part"] == "moon"])
        return

    mars_meta = base_meta(mars_heads, definitions, mars_tiles, mars_rows)
    mars_meta.update({
        "what": ("Daily temperature swing, surface albedo, top-soil wetness and 10 m wind speed by calendar month for "
                 "every half-degree square of the Mars part (data/derived/mars_cells.json), from NASA POWER. A first pass, as coarse as "
                 "the squares."),
        "places_source": str(MARS_PLACES.relative_to(ROOT)),
        "written": written,
        "t2m_range_check": range_check,
        "counts": counts(mars_table),
        "medians": summary(mars_table),
        "reference_places": [r for r in refs if r["part"] == "mars"],
    })
    write_json(OUT_MARS, {"meta": mars_meta, "cells": mars_table})
    print(f"wrote {OUT_MARS.relative_to(ROOT)} ({OUT_MARS.stat().st_size / 1e6:.1f} MB)")
    show(moon_meta, mars_meta, range_check, refs)


def show(moon_meta: dict, mars_meta: dict | None, range_check: dict, refs: list[dict]) -> None:
    print(json.dumps({"moon_counts": moon_meta["counts"], "mars_counts": (mars_meta or {}).get("counts"),
                      "moon_medians": moon_meta["medians"], "mars_medians": (mars_meta or {}).get("medians"),
                      "annual_check": moon_meta["annual_check"], "albedo_repeat": moon_meta["albedo_repeat_check"],
                      "t2m_range_check": {k: v for k, v in range_check.items() if k != "places"}}, indent=1))
    for ref in refs:
        values = ref["values"]
        if values is None:
            print(f"{ref['name']} ({ref['id']}): not in the places file")
            continue
        print(f"{ref['name']} ({ref['id']}), MERRA-2 point {values['grid_merra2']}, CERES box {values['grid_ceres']}")
        for field in FIELD.values():
            months = values[field]
            shown = " ".join("  n/a" if v is None else f"{v:5.2f}" for v in months) if months else "no value"
            print(f"   {field:17s} {shown}   year {values[field + '_year']}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("step", choices=["fetch", "build"])
    parser.add_argument("--only", choices=["moon", "mars", "all"], default="all")
    parser.add_argument("--pause", type=float, default=MIN_GAP_S)
    args = parser.parse_args()
    if args.step == "fetch":
        if args.pause < MIN_GAP_S:
            raise SystemExit(f"--pause must be at least {MIN_GAP_S} s")
        sys.exit(fetch(args.only, args.pause))
    build()


if __name__ == "__main__":
    main()

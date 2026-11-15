# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Mars part, environment side. Writes data/derived/mars_environment.json.

For every ranked square of data/derived/mars_cells.json (bare share of at least 0.15): UV at
the ground, sunlight at the ground, clear-sky days and haze (aerosol optical depth), as monthly
climatology of the 1 degree grid box that holds the square centre, from the NASA POWER
climatology service (source named by the service: CERES SYN1deg).

Four steps, each safe to run again (nothing on disk is asked for twice):

    uv run python scripts/build_mars_environment.py fetch           # regional answers, ranked blocks first
    uv run python scripts/build_mars_environment.py fetch-uv-hours  # hour-based UV set, ranked blocks only
    uv run python scripts/build_mars_environment.py check-years     # monthly series at five boxes
    uv run python scripts/build_mars_environment.py build           # no network; writes the JSON

fetch-uv-hours asks the service's hour-based UV index set (ALLSKY_SFC_UV_INDEX_HR, 24 hourly values of
the mean day of each month, local solar time) for the blocks with ranked squares, because the daily
ALLSKY_SFC_UV_INDEX is a mean over all 24 hours and the brightest hour is four to five times higher.

fetch asks one parameter and one 10 degree block per request, one request at a time with a
pause, User-Agent twinfinder/0.1, no key and no login: first every parameter (in the job's order
of importance) for the blocks that hold ranked squares, then for the other blocks that hold land
squares of the Mars grid. Raw answers go to data/raw/power_global_environment/, a log of every
request to fetch_log.jsonl there. If the network drops, it waits and tries again; a second run
asks only for what is missing.

check-years asks the monthly series 2001-2025 at a few 1 degree boxes (one request a box) and
works out over which years the climatology was taken, and so how a CLRSKY_DAYS value (a count
summed over all years of the period, not days in one month) turns into days per month.

The parameter names, definitions and units are the service's own, read from its parameter list
(api/system/manager/parameters, kept in data/raw/power_global_environment/parameters/).
"""
from __future__ import annotations

import argparse
import datetime
import json
import math
import os
import statistics
import sys
import time
import urllib.request
from pathlib import Path

from twinfinder import cloud, temperature

RAW = Path("data/raw/power_global_environment")
LOG = RAW / "fetch_log.jsonl"
CHECKS = RAW / "checks"
PARAMETER_LIST = RAW / "parameters" / "manager_parameters_RE_climatology.json"
PARAMETER_LIST_URL = "https://power.larc.nasa.gov/api/system/manager/parameters?community=RE&temporal=climatology"
CELLS = Path("data/derived/mars_cells.json")
CLIMATE = Path("data/derived/mars_climate.json")
SITES = Path("data/derived/mars_sites.json")
OUT = Path("data/derived/mars_environment.json")
USER_AGENT = cloud.USER_AGENT

# The job's order of importance first: surface sunlight (all-sky), UV index, aerosol optical depth,
# clear-sky days; then the rest.
PARAMETERS = ("ALLSKY_SFC_SW_DWN", "ALLSKY_SFC_UV_INDEX", "AOD_55", "CLRSKY_DAYS",
              "CLRSKY_SFC_SW_DWN", "ALLSKY_KT", "ALLSKY_SFC_UVA", "ALLSKY_SFC_UVB", "AOD_55_ADJ", "TOA_SW_DWN")
UNITS = {"ALLSKY_SFC_SW_DWN": "kW-hr/m^2/day", "CLRSKY_SFC_SW_DWN": "kW-hr/m^2/day", "TOA_SW_DWN": "kW-hr/m^2/day",
         "ALLSKY_SFC_UVA": "kW-hr/m^2/day", "ALLSKY_SFC_UVB": "kW-hr/m^2/day", "ALLSKY_SFC_UV_INDEX": "W m-2 x 40",
         "ALLSKY_KT": "dimensionless", "AOD_55": "dimensionless", "AOD_55_ADJ": "dimensionless",
         "CLRSKY_DAYS": "Days"}
# Outside these a value is not what the parameter says it is (a day of sunlight at the top of the
# atmosphere is at most about 13.5 kWh/m2; CLRSKY_DAYS is a count summed over up to 25 years).
RANGE = {"ALLSKY_SFC_SW_DWN": (0.0, 15.0), "CLRSKY_SFC_SW_DWN": (0.0, 15.0), "TOA_SW_DWN": (0.0, 15.0),
         "ALLSKY_SFC_UVA": (0.0, 2.0), "ALLSKY_SFC_UVB": (0.0, 0.2), "ALLSKY_SFC_UV_INDEX": (0.0, 30.0),
         "ALLSKY_KT": (0.0, 1.0), "AOD_55": (0.0, 6.0), "AOD_55_ADJ": (0.0, 6.0),
         "CLRSKY_DAYS": (0.0, 366.0 * 25)}
MONTHS = cloud.MONTHS
FILL_VALUE = -999.0
GRID_DEG = 1.0
PAUSE_S = 0.5
ROUND_WAIT_S = 60.0
ROUNDS = 6


def now_utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_json(path: Path, value, indent=None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    side = path.with_name(path.name + ".part")
    side.write_text(json.dumps(value, separators=(",", ":") if indent is None else None, indent=indent,
                               allow_nan=False))
    os.replace(side, path)


# ---- reading a raw answer ------------------------------------------------------------------------------

def _parsed(raw) -> dict:
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8")
    data = json.loads(raw) if isinstance(raw, str) else raw
    if not isinstance(data, dict) or not isinstance(data.get("features"), list) or not data["features"]:
        messages = data.get("messages") if isinstance(data, dict) else None
        raise ValueError(f"not a regional climatology answer: {messages!r}")
    return data


def read_answer(raw, parameter: str) -> dict[tuple[float, float], tuple[list[float | None], float | None]]:
    """{(lat, lon): ([12 monthly values, January first], annual value)} from one regional answer.

    The fill value becomes None; a real 0.0 stays 0.0. The units must be the ones the service's
    parameter list gives; the grid must be the 1 degree grid with centres at x.5; a value outside the
    parameter's range, an error message or an answer for another parameter is an error.
    """
    data = _parsed(raw)
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
            lon, lat = (float(x) for x in feature["geometry"]["coordinates"][:2])
            months = feature["properties"]["parameter"][parameter]
        except (KeyError, TypeError, IndexError, ValueError) as error:
            raise ValueError(f"answer does not hold {parameter} by grid box: {error!r}") from error
        if lon >= 180.0:
            lon -= 360.0
        if abs(lat % 1.0 - 0.5) > 1e-6 or abs(lon % 1.0 - 0.5) > 1e-6:
            raise ValueError(f"{parameter}: point {lat}, {lon} is not on the 1 degree grid (centres at x.5)")
        where = f"at {lat}, {lon}"
        out[(lat, lon)] = ([value(months.get(m), f"{m} {where}") for m in MONTHS], value(months.get("ANN"), f"ANN {where}"))
    return out


def answer_header(raw) -> dict:
    data = _parsed(raw)
    header = data.get("header") if isinstance(data.get("header"), dict) else {}
    api = header.get("api") if isinstance(header.get("api"), dict) else {}
    return {"version": api.get("version"), "name": api.get("name"), "sources": header.get("sources"),
            "start": header.get("start"), "end": header.get("end"), "fill_value": header.get("fill_value"),
            "messages": data.get("messages"),
            "units": ((data.get("parameters") or {}).get(next(iter(data.get("parameters") or {"": 0}))) or {}).get("units")}


# ---- what to ask for, in which order -----------------------------------------------------------------

raw_name = cloud.raw_name


def wanted(ranked_tiles, land_tiles, parameters=PARAMETERS) -> list[tuple[str, tuple[int, int, int, int]]]:
    """Every (parameter, block) to have on disk: the ranked blocks for every parameter in the order of
    importance first, then the other land blocks for every parameter in the same order."""
    ranked = sorted(set(ranked_tiles))
    rest = sorted(set(land_tiles) - set(ranked))
    return [(p, t) for p in parameters for t in ranked] + [(p, t) for p in parameters for t in rest]


def fetch_one(parameter: str, tile, raw_dir: Path, opener=None, sleep=time.sleep) -> tuple[Path, bool]:
    """Path of the raw answer for one parameter and block, asked only if it is not on disk; (path, asked).

    Waits and tries again after a dropped network, a 429 or a server fault (twinfinder.temperature._fetch);
    a body that is not an answer is not kept.
    """
    dest = Path(raw_dir) / raw_name(parameter, tile)
    return temperature._fetch(cloud.regional_url(parameter, tile), dest, lambda body: read_answer(body, parameter),
                              opener=opener, sleep=sleep)


def log_request(url: str, path: Path, log: Path = LOG) -> None:
    with open(log, "a") as handle:
        handle.write(json.dumps({"time": now_utc(), "url": url, "file": str(path.relative_to(log.parent)),
                                 "bytes": path.stat().st_size}) + "\n")


def fetch_all(order, raw_dir: Path = RAW, pause_s: float = PAUSE_S, rounds: int = ROUNDS,
              round_wait_s: float = ROUND_WAIT_S) -> dict:
    """Make sure every (parameter, block) of `order` is on disk. A request that still fails after the
    retries of fetch_one is tried again in whole rounds, ROUND_WAIT_S x round apart; after the last round
    the run stops with what it has (a second run asks only for what is missing)."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    asked = 0
    started = time.time()
    todo = [(p, t) for p, t in order if not (raw_dir / raw_name(p, t)).exists()]
    print(f"{now_utc()} {len(order)} answers wanted, {len(order) - len(todo)} on disk, {len(todo)} to ask", flush=True)
    for n, (parameter, tile) in enumerate(todo, 1):
        for round_ in range(1, rounds + 1):
            try:
                path, did = fetch_one(parameter, tile, raw_dir)
                break
            except Exception as error:   # noqa: BLE001 - logged, waited on and tried again
                print(f"{now_utc()} {raw_name(parameter, tile)}: {type(error).__name__}: {error} (round {round_})",
                      flush=True)
                if round_ == rounds:
                    print(f"{now_utc()} giving up for now after {asked} requests; run again to go on", flush=True)
                    return {"asked": asked, "complete": False}
                time.sleep(round_wait_s * round_)
        if did:
            asked += 1
            log_request(cloud.regional_url(parameter, tile), path, raw_dir / LOG.name)
            if asked % 50 == 0:
                rate = (time.time() - started) / asked
                print(f"{now_utc()} asked {asked} of {len(todo)} ({parameter}); {rate:.2f} s a request; "
                      f"about {rate * (len(todo) - n) / 60:.0f} min to go", flush=True)
            time.sleep(pause_s)
    print(f"{now_utc()} done: asked {asked}; on disk "
          f"{sum((raw_dir / raw_name(p, t)).exists() for p, t in order)} of {len(order)}", flush=True)
    return {"asked": asked, "complete": True}


# ---- the brightest hour of the UV day (hour-based set, ranked blocks only) -------------------------------

UV_HOURS = "ALLSKY_SFC_UV_INDEX_HR"
UV_HOURS_RAW = RAW / "uv_hours"


def read_uv_hours(raw) -> dict[tuple[float, float], tuple[list[float | None], list[int | None]]]:
    """{(lat, lon): ([12 peak values], [12 hours])} from a regional answer of the hour-based UV set.

    For each month: the highest of the 24 hourly values (local solar time) of the month's mean day, and
    the hour it falls in. A month with any hour unknown is None in both lists. All 24 hours and the
    units 'W m-2 x 40' must be there.
    """
    data = _parsed(raw)
    names = [f"ALLSKY_SFC_UV_INDEX_{h:02d}" for h in range(24)]
    for name in names:
        units = ((data.get("parameters") or {}).get(name) or {}).get("units")
        if units != UNITS["ALLSKY_SFC_UV_INDEX"]:
            raise ValueError(f"{name}: units {units!r}, expected {UNITS['ALLSKY_SFC_UV_INDEX']!r}")
    out = {}
    for feature in data["features"]:
        lon, lat = (float(x) for x in feature["geometry"]["coordinates"][:2])
        if lon >= 180.0:
            lon -= 360.0
        hours = feature["properties"]["parameter"]
        if any(name not in hours for name in names):
            raise ValueError(f"not all 24 hours at {lat}, {lon}")
        peaks, at = [], []
        for month in MONTHS:
            values = []
            for name in names:
                v = hours[name].get(month)
                if v is None or isinstance(v, bool) or not isinstance(v, (int, float)) or float(v) == FILL_VALUE:
                    values = None
                    break
                v = float(v)
                if not 0.0 <= v <= RANGE["ALLSKY_SFC_UV_INDEX"][1]:
                    raise ValueError(f"UV index {name} {month} at {lat}, {lon} out of range: {v}")
                values.append(v)
            if values is None:
                peaks.append(None)
                at.append(None)
            else:
                top = max(values)
                peaks.append(top)
                at.append(values.index(top))
        out[(lat, lon)] = (peaks, at)
    return out


UV_CHECK = CHECKS / "climatology_hourly_UV_INDEX_S24.5_W069.5.json"
UV_CHECK_URL = ("https://power.larc.nasa.gov/api/temporal/climatology/point?parameters=ALLSKY_SFC_UV_INDEX_HR,"
                "ALLSKY_SFC_UV_INDEX&community=RE&longitude=-69.5&latitude=-24.5&format=JSON")


def uv_check(raw) -> dict:
    """The daily ALLSKY_SFC_UV_INDEX of a point climatology answer against the mean of its 24 hourly values,
    month by month, and how many times the daily value the brightest hour is."""
    data = json.loads(raw.decode("utf-8") if isinstance(raw, (bytes, bytearray)) else raw)
    p = data["properties"]["parameter"]
    gaps, ratio = [], {}
    for month in MONTHS:
        hours = [p[f"ALLSKY_SFC_UV_INDEX_{h:02d}"][month] for h in range(24)]
        daily = p["ALLSKY_SFC_UV_INDEX"][month]
        if daily in (None, FILL_VALUE) or any(v in (None, FILL_VALUE) for v in hours):
            continue
        gaps.append(daily - sum(hours) / 24.0)
        ratio[month] = round(max(hours) / daily, 2) if daily else None
    return {"months": len(gaps), "largest_gap_daily_minus_mean_of_24_hours": max(gaps, key=abs) if gaps else None,
            "brightest_hour_over_daily": ratio}


def fetch_uv_hours_step(pause_s: float) -> None:
    ranked = json.loads(CELLS.read_text())["cells"]
    order = [(UV_HOURS, t) for t in tiles_of(ranked)]
    UV_HOURS_RAW.mkdir(parents=True, exist_ok=True)
    todo = [(p, t) for p, t in order if not (UV_HOURS_RAW / raw_name(p, t)).exists()]
    print(f"{now_utc()} {len(order)} blocks of the hour-based UV set wanted, {len(todo)} to ask", flush=True)
    asked = 0
    for parameter, tile in todo:
        dest = UV_HOURS_RAW / raw_name(parameter, tile)
        url = cloud.regional_url(parameter, tile)
        for round_ in range(1, ROUNDS + 1):
            try:
                path, did = temperature._fetch(url, dest, read_uv_hours, timeout=180.0)
                break
            except Exception as error:   # noqa: BLE001 - logged, waited on and tried again
                print(f"{now_utc()} {dest.name}: {type(error).__name__}: {error} (round {round_})", flush=True)
                if round_ == ROUNDS:
                    sys.exit(2)
                time.sleep(ROUND_WAIT_S * round_)
        if did:
            asked += 1
            log_request(url, path)
            time.sleep(pause_s)
        if asked and asked % 25 == 0:
            print(f"{now_utc()} asked {asked} of {len(todo)}", flush=True)
    print(f"{now_utc()} done: asked {asked}", flush=True)


# ---- the squares and their blocks ----------------------------------------------------------------------

def _lat_lon(square_id: str) -> tuple[float, float]:
    _, lat, lon = square_id.split("_")
    return float(lat), float(lon)


def tiles_of(square_ids) -> list[tuple[int, int, int, int]]:
    """The 10 degree blocks that hold the 1 degree boxes of these squares."""
    return cloud.tiles_for({cloud.grid_box(*_lat_lon(i)) for i in square_ids})


def fetch_step(pause_s: float) -> None:
    ranked = json.loads(CELLS.read_text())["cells"]
    land = json.loads(CLIMATE.read_text())["cells"]
    order = wanted(tiles_of(ranked), tiles_of(land))
    print(f"{now_utc()} {len(ranked)} ranked squares in {len(tiles_of(ranked))} blocks; {len(land)} land squares "
          f"in {len(tiles_of(land))} blocks; {len(PARAMETERS)} parameters", flush=True)
    result = fetch_all(order, RAW, pause_s)
    if not result["complete"]:
        sys.exit(2)


# ---- over which years was the climatology taken (monthly series at a few boxes) -----------------------

MONTHLY_URL_PATTERN = (
    "https://power.larc.nasa.gov/api/temporal/monthly/point"
    "?parameters={parameters}&community=RE&longitude={lon}&latitude={lat}&start={start}&end={end}&format=JSON"
)
CHECK_PARAMETERS = ("ALLSKY_SFC_SW_DWN", "ALLSKY_SFC_UV_INDEX", "AOD_55", "CLRSKY_DAYS")
CHECK_START, CHECK_END = 2001, 2025
# 1 degree boxes of named places (box centres); one monthly request each
CHECK_POINTS = (("Atacama near Yungay", -24.5, -69.5), ("Utah desert station near Hanksville", 38.5, -110.5),
                ("Qaidam Basin (Dalangtan)", 38.5, 92.5), ("McMurdo Dry Valleys", -77.5, 162.5),
                ("Haughton crater", 75.5, -89.5))
# a month of the climatology counts as equal to the series when within this (the service rounds its values)
TOLERANCE = {"ALLSKY_SFC_SW_DWN": 0.011, "ALLSKY_SFC_UV_INDEX": 0.011, "AOD_55": 0.011, "CLRSKY_DAYS": 0.5}
HOW = {"ALLSKY_SFC_SW_DWN": "mean", "ALLSKY_SFC_UV_INDEX": "mean", "AOD_55": "mean", "CLRSKY_DAYS": "sum"}


def check_name(lat: float, lon: float) -> str:
    return (f"monthly_{'N' if lat >= 0 else 'S'}{abs(lat):04.1f}_{'E' if lon >= 0 else 'W'}{abs(lon):05.1f}_"
            f"{CHECK_START}_{CHECK_END}.json")


def monthly_url(lat: float, lon: float) -> str:
    return MONTHLY_URL_PATTERN.format(parameters=",".join(CHECK_PARAMETERS), lat=lat, lon=lon,
                                      start=CHECK_START, end=CHECK_END)


def read_series(raw, parameter: str) -> dict[tuple[int, int], float | None]:
    """{(year, month): value} of one parameter of a monthly point answer; month 13 (the year) left out,
    the fill value as None."""
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8")
    data = json.loads(raw) if isinstance(raw, str) else raw
    try:
        values = data["properties"]["parameter"][parameter]
    except (KeyError, TypeError) as error:
        raise ValueError(f"not a monthly point answer for {parameter}: "
                         f"{data.get('messages') if isinstance(data, dict) else None!r}") from error
    fills = {FILL_VALUE}
    fill = (data.get("header") or {}).get("fill_value")
    if isinstance(fill, (int, float)) and not isinstance(fill, bool):
        fills.add(float(fill))
    out = {}
    for key, value in values.items():
        year, month = int(key[:4]), int(key[4:6])
        if month == 13:
            continue
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float))):
            raise ValueError(f"{parameter} {key} is not a number: {value!r}")
        out[(year, month)] = None if value is None or float(value) in fills else float(value)
    return out


def fit_end_year(clim, series: dict, how: str, tolerance: float, first_year: int = CHECK_START) -> dict | None:
    """Over which years, first_year to some end year, do the monthly series give the climatology?

    clim is the 12 monthly climatology values; series {(year, month): value}. For each end year a month
    counts as equal when the mean (how="mean") or the sum (how="sum") of that calendar month over
    first_year to the end year is within `tolerance` of the climatology. The end year with the most equal
    months fits best (the later on a tie). None without a row or a series: unknown, never a guess.
    """
    if not clim or not series:
        return None
    years = sorted({y for (y, _), v in series.items() if v is not None and y >= first_year})
    if not years:
        return None
    equal = {year: 0 for year in years}
    compared = 0
    for month in range(1, 13):
        wanted_value = clim[month - 1]
        if wanted_value is None:
            continue
        got = {}
        for end in years:
            values = [series[(y, month)] for y in range(first_year, end + 1) if series.get((y, month)) is not None]
            if values:
                got[end] = sum(values) if how == "sum" else sum(values) / len(values)
        # a month whose mean (or sum) is the same for every end year, such as a month of 0 clear days in
        # every year, says nothing about the years and is not compared
        if not got or max(got.values()) - min(got.values()) <= tolerance:
            continue
        compared += 1
        for end, value in got.items():
            if abs(value - wanted_value) <= tolerance:
                equal[end] += 1
    if not compared:
        return None
    best = max(years, key=lambda year: (equal[year], year))
    return {"first_year": first_year, "end_year_that_fits_best": best, "months_compared": compared,
            "months_equal_at_that_end_year": equal[best], "months_equal_with_all_years": equal[years[-1]],
            "end_years_tied_at_best": [year for year in years if equal[year] == equal[best]],
            "months_equal_by_end_year": {str(year): equal[year] for year in years}}


def check_years_step(pause_s: float) -> None:
    CHECKS.mkdir(parents=True, exist_ok=True)

    def check(body):
        for parameter in CHECK_PARAMETERS:
            if not read_series(body, parameter):
                raise ValueError(f"no {parameter} in the answer")

    for name, lat, lon in CHECK_POINTS:
        dest = CHECKS / check_name(lat, lon)
        path, asked = temperature._fetch(monthly_url(lat, lon), dest, check, timeout=180.0)
        if asked:
            log_request(monthly_url(lat, lon), path)
            time.sleep(pause_s)
        print(f"{now_utc()} {name} ({lat}, {lon}): {'asked' if asked else 'on disk'} {path}", flush=True)


def years_check(read_box) -> dict:
    """For each checked parameter, the fit of every check point and all points added up.

    read_box(parameter, (lat, lon)) gives the climatology row ([12], annual) of a box or None. The end year
    that fits best is the one with the most equal months over all points (the later on a tie); the years
    the values fit are named only when at that end year every compared month of every point is equal.
    """
    out = {}
    for parameter in CHECK_PARAMETERS:
        points, by_year, compared = [], {}, 0
        for name, lat, lon in CHECK_POINTS:
            path = CHECKS / check_name(lat, lon)
            row = read_box(parameter, (lat, lon))
            if not path.exists() or row is None:
                points.append({"place": name, "box": [lat, lon], "fit": None})
                continue
            fit = fit_end_year(row[0], read_series(path.read_bytes(), parameter), HOW[parameter],
                               TOLERANCE[parameter])
            points.append({"place": name, "box": [lat, lon], "file": str(path), "fit": fit})
            if fit:
                compared += fit["months_compared"]
                for year, n in fit["months_equal_by_end_year"].items():
                    by_year[year] = by_year.get(year, 0) + n
        fits = [p["fit"] for p in points if p["fit"]]
        best = max(by_year, key=lambda y: (by_year[y], int(y))) if by_year else None
        # every month of every point equal at the end year that fits best over all points together
        agree = bool(fits) and all(f["months_equal_by_end_year"].get(best) == f["months_compared"] for f in fits)
        tied = sorted(int(y) for y, n in by_year.items() if best and n == by_year[best])
        if best and agree and len(tied) == 1:
            fit_text = f"{CHECK_START} to {best}"
        elif best and agree:
            fit_text = f"{CHECK_START} to any end year from {tied[0]} to {tied[-1]} (the check cannot tell them apart)"
        else:
            fit_text = None
        out[parameter] = {
            "how": HOW[parameter], "tolerance": TOLERANCE[parameter], "points": points,
            "months_compared": compared,
            "end_year_that_fits_best_all_points": int(best) if best else None,
            "end_years_tied_at_best_all_points": tied,
            "months_equal_at_that_end_year": by_year.get(best) if best else None,
            "months_equal_with_2001_to_2025": by_year.get(str(CHECK_END)),
            "all_points_agree": agree,
            "years_the_values_fit": fit_text,
            "end_year_settled": int(best) if best and agree and len(tied) == 1 else None,
        }
    return out


def days_per_month(counts, years: int | None) -> list[float | None] | None:
    """Clear-sky days in a typical month: the service's count over all years of the period / the years."""
    if counts is None:
        return None
    if years is None:
        return None
    if years <= 0:
        raise ValueError(f"years must be at least 1, got {years}")
    return [None if v is None else v / years for v in counts]


# ---- one square's record -------------------------------------------------------------------------------

FIELDS = {   # field stem: (parameter, decimals)
    "sun_kwh_m2_day": ("ALLSKY_SFC_SW_DWN", 2),
    "uv_index": ("ALLSKY_SFC_UV_INDEX", 2),
    "aod_550": ("AOD_55", 2),
}
YEAR_ONLY = {   # extra yearly fields: (parameter, decimals)
    "sun_clear_sky_kwh_m2_day_year": ("CLRSKY_SFC_SW_DWN", 2),
    "clearness_index_year": ("ALLSKY_KT", 2),
    "uva_kwh_m2_day_year": ("ALLSKY_SFC_UVA", 3),
    "uvb_kwh_m2_day_year": ("ALLSKY_SFC_UVB", 4),
    "aod_550_adjusted_year": ("AOD_55_ADJ", 2),
    "top_of_atmosphere_kwh_m2_day_year": ("TOA_SW_DWN", 2),
}


def _rounded(values, decimals: int):
    if values is None or all(v is None for v in values):
        return None
    return [None if v is None else round(v, decimals) for v in values]


def _r(value, decimals: int):
    return None if value is None else round(value, decimals)


def clear_days_year(row, clear_years: int | None) -> tuple[float | None, str | None]:
    """Clear-sky days a year from a CLRSKY_DAYS row ([12], annual) and the years it was summed over.

    (value, how): how is "annual" when the service's annual value is used, "sum of months" when the
    service gives its fill value for the year but all 12 months (it does so whenever the total passes
    1800), and None with value None when it cannot be known.
    """
    if not row or not clear_years:
        return None, None
    months, annual = row
    if annual is not None:
        return annual / clear_years, "annual"
    if months and all(v is not None for v in months):
        # month by month, as the build did before this helper, so that rounding stays the same
        return sum(v / clear_years for v in months), "sum of months"
    return None, None


def cell_record(lat: float, lon: float, by_param: dict, clear_years: int | None, uv_peaks: dict | None = None) -> dict:
    """The environment of one square: the rows of the 1 degree box that holds its centre.

    by_param maps a parameter to {(lat, lon) of a box: ([12], annual)}. A parameter not fetched, a box not
    answered or a row of fill values gives null; clear-sky days are null too while the years the service's
    count was summed over are not settled (clear_years None). uv_peaks maps a box to ([12 brightest-hour
    UV index values], [12 hours]) from the hour-based set. Never 0 for unknown.
    """
    box = cloud.grid_box(lat, lon)
    record: dict = {}
    peaks = (uv_peaks or {}).get(box)
    record["uv_index_brightest_hour"] = _rounded(peaks[0], 2) if peaks else None
    known = [v for v in peaks[0] if v is not None] if peaks else []
    record["uv_index_brightest_hour_max"] = round(max(known), 2) if known else None
    for stem, (parameter, decimals) in FIELDS.items():
        row = by_param.get(parameter, {}).get(box)
        record[f"{stem}_year"] = _r(row[1], decimals) if row else None
        record[stem] = _rounded(row[0], decimals) if row else None
    row = by_param.get("CLRSKY_DAYS", {}).get(box)
    months = days_per_month(row[0], clear_years) if row else None
    record["clear_days"] = _rounded(months, 1)
    year, _ = clear_days_year(row, clear_years)
    record["clear_days_year"] = _r(year, 1)
    for field, (parameter, decimals) in YEAR_ONLY.items():
        row = by_param.get(parameter, {}).get(box)
        record[field] = _r(row[1], decimals) if row else None
    record["grid"] = [box[0], box[1]]
    return record


# ---- what Mars is, from the project's own files ---------------------------------------------------------

MARS_FROM_FILE = {   # key: the "what" of a cannot_match item in data/derived/mars_sites.json
    "sunlight_top_of_atmosphere": "sunlight at the top of the atmosphere",
    "dust_optical_depth": "the dusty sky",
    "uv_cut_off": "ultraviolet light at the ground",
}
NOT_IN_OUR_DATA = {
    "sunlight_at_the_ground": "daily sunlight on level ground at a Mars site (kWh/m2 a day or W/m2)",
    "uv_index": "a UV index or UV irradiance at the ground of a Mars site",
    "cloud_free_days": "a count of cloud-free (or dust-free) days at a Mars site",
    "dust_only_optical_depth_earth": "a dust-only optical depth for Earth (the service offers none)",
}


def mars_figures(sites_doc: dict, file_name: str = "data/derived/mars_sites.json") -> dict:
    """The Mars comparison figures, each with number, unit and source, from the site cards; the same for
    every site or an error. A figure the cards do not hold is marked "not in our data"."""
    out = {}
    for key, what in MARS_FROM_FILE.items():
        found = []
        for site in sites_doc.get("sites") or []:
            for item in site.get("cannot_match") or []:
                if item.get("what") == what:
                    found.append(item)
        if not found:
            out[key] = {"what": what, "mars": "not in our data", "unit": None, "source": None}
            continue
        keys = ("mars", "earth", "unit", "number", "source")
        if len({json.dumps([f.get(k) for k in keys]) for f in found}) != 1:
            raise ValueError(f"the site cards disagree about {what!r}")
        first = found[0]
        out[key] = {"what": what, **{k: first.get(k) for k in keys},
                    **{k: first[k] for k in ("number_is", "note", "mars_range", "mars_range_how", "url") if k in first},
                    "from_file": file_name, "sites_holding_it": len(found)}
    for key, what in NOT_IN_OUR_DATA.items():
        out[key] = {"what": what, "mars": "not in our data", "unit": None, "source": None}
    return out


# ---- summaries -------------------------------------------------------------------------------------------

def spread(values) -> dict | None:
    known = sorted(v for v in values if v is not None)
    if not known:
        return None
    return {"median": round(statistics.median(known), 3), "min": known[0], "max": known[-1], "squares": len(known)}


def box_ranking(cells: dict, regions: dict, field: str, n: int = 5, highest: bool = True) -> list[dict]:
    """The n 1 degree boxes with the highest (or lowest) value of a field among the ranked squares.

    Boxes, not squares: every square in a box carries the same value. Unknown values are left out."""
    boxes: dict[tuple, dict] = {}
    for cid, record in cells.items():
        value = record.get(field)
        if value is None:
            continue
        key = tuple(record["grid"])
        entry = boxes.setdefault(key, {"grid": list(key), "value": value, "ranked_squares": 0, "regions": {},
                                       "example_square": cid})
        entry["ranked_squares"] += 1
        name = regions.get(cid) or "other"
        entry["regions"][name] = entry["regions"].get(name, 0) + 1
    ordered = sorted(boxes.values(), key=lambda e: (-e["value"] if highest else e["value"], e["grid"]))
    out = []
    for entry in ordered[:n]:
        entry = dict(entry)
        entry["regions"] = [r for r, _ in sorted(entry["regions"].items(), key=lambda kv: (-kv[1], kv[0]))]
        out.append(entry)
    return out


# ---- what each parameter is and is not -------------------------------------------------------------------

WHAT_IT_IS_NOT = {   # every sentence 25 words or fewer (tests/test_mars_environment.py)
    "ALLSKY_SFC_SW_DWN": ("Not the sunlight on a tilted panel or in one hour, and not a measurement at the square. "
                          "It is the energy reaching level ground in a mean day of the month, night included. "
                          "Satellite-based, under the real mix of cloud and clear, for a 1 degree box about 111 km tall."),
    "CLRSKY_SFC_SW_DWN": ("Not what reaches the ground on a typical day: what would reach a level surface on the "
                          "same days if there were no cloud."),
    "ALLSKY_KT": ("Not a share of clear days. "
                  "It is the share of top-of-atmosphere sunlight that reaches level ground in a mean day, cloud, haze and air together."),
    "ALLSKY_SFC_UV_INDEX": ("Not the noon UV index of a weather forecast. "
                            "It is the mean over all 24 hours of the month's mean day, night included. "
                            "Checked: the 24 hourly values of the service's hour-based set average to it within 2 percent in most box-months. "
                            "So it is several times lower than the brightest hour, which uv_index_brightest_hour gives."),
    "ALLSKY_SFC_UVA": "Not weighted for harm to skin or life: the plain energy of UVA light (315-400 nm) a day.",
    "ALLSKY_SFC_UVB": "Not weighted for harm to skin or life: the plain energy of UVB light (280-315 nm) a day.",
    "CLRSKY_DAYS": ("Not the days a camera at the square sees a clear sky. "
                    "A day counts only when daytime cloud over the whole 1 degree box is under 10 percent. "
                    "So a partly cloudy box, or a coastal box with sea cloud, counts as not clear. "
                    "The service sums the count over all years; it is divided here by the years the check found."),
    "AOD_55": ("Not dust alone and not dust on the ground. "
               "It is the optical depth at 550 nm of all fine particles in the air column together. "
               "That is dust, smoke, sea salt, haze and pollution, as a monthly mean for a 1 degree box."),
    "AOD_55_ADJ": ("Not explained by the service beyond the word 'adjusted'. "
                   "Kept beside AOD_55 for comparison only, and not used in any sentence. "
                   "The Moon-part file uses AOD_55_ADJ instead."),
    "TOA_SW_DWN": ("Not sunlight at the ground: what a level surface would receive above the atmosphere, kept to set "
                   "the ground figures against."),
    "ALLSKY_SFC_UV_INDEX_HR": ("Not one day's noon value and not the clearest day's. "
                               "It is the highest of the 24 hourly values of the month's mean day, all sky, for a 1 degree box. "
                               "Hours are local solar time, as the service labels them. "
                               "The service gives no definition of the hour-based set beyond its name."),
}
FIELD_MEANING = {   # every sentence 25 words or fewer
    "sun_kwh_m2_day": "ALLSKY_SFC_SW_DWN by month, kWh per m2 per day on level ground, all sky (January first)",
    "sun_kwh_m2_day_year": "ALLSKY_SFC_SW_DWN, the service's annual value, kWh per m2 per day",
    "uv_index": "ALLSKY_SFC_UV_INDEX by month: UV index averaged over all 24 hours of the day, night included",
    "uv_index_year": "ALLSKY_SFC_UV_INDEX, the service's annual value (24-hour mean)",
    "uv_index_brightest_hour": ("By month, the highest of the 24 hourly values of the month's mean day, local solar time. "
                                "From the service's hour-based set ALLSKY_SFC_UV_INDEX_HR. "
                                "It is the figure closest to a forecast's noon UV index."),
    "uv_index_brightest_hour_max": "the highest month of uv_index_brightest_hour",
    "clear_days": ("CLRSKY_DAYS by month divided by the years the count was summed over. "
                   "Days a month with daytime cloud over the 1 degree box under 10 percent. "
                   "Null if those years are not settled."),
    "clear_days_year": ("The service's annual CLRSKY_DAYS divided by the same years: such days a year. "
                        "The service gives its fill value for the year whenever the total passes 1800. "
                        "There the sum of its 12 months is used (counts.squares_with_clear_days_year_from_month_sum)."),
    "aod_550": "AOD_55 by month: aerosol optical depth at 550 nm, all particles in the air column, dimensionless",
    "aod_550_year": "AOD_55, the service's annual value",
    "sun_clear_sky_kwh_m2_day_year": "CLRSKY_SFC_SW_DWN annual: sunlight on level ground were there no cloud, kWh/m2/day",
    "clearness_index_year": "ALLSKY_KT annual: share of top-of-atmosphere sunlight that reaches the ground",
    "uva_kwh_m2_day_year": "ALLSKY_SFC_UVA annual, kWh/m2/day",
    "uvb_kwh_m2_day_year": "ALLSKY_SFC_UVB annual, kWh/m2/day",
    "aod_550_adjusted_year": "AOD_55_ADJ annual ('adjusted', not explained by the service)",
    "top_of_atmosphere_kwh_m2_day_year": "TOA_SW_DWN annual: sunlight on a level surface above the atmosphere, kWh/m2/day",
    "grid": "[lat, lon] of the centre of the 1 degree box that holds the square centre (all values are that box's)",
}
NAMED_POINTS = ("Atacama near Yungay", "McMurdo Dry Valleys", "Haughton crater", "Utah desert station near Hanksville",
                "Qaidam Basin")
NAMED_REGIONS = (   # (name, region of mars_cells.json, extra box or None)
    ("central Sahara (ranked squares of region 'Sahara' between 20 and 28 N and 0 and 20 E)", "Sahara",
     (20.0, 28.0, 0.0, 20.0)),
    ("Tibetan Plateau (ranked squares of region 'Tibetan Plateau')", "Tibetan Plateau", None),
    ("Qaidam Basin (ranked squares of region 'Qaidam Basin')", "Qaidam Basin", None),
)
YEAR_FIELDS = ("sun_kwh_m2_day_year", "uv_index_year", "uv_index_brightest_hour_max", "clear_days_year",
               "aod_550_year", "clearness_index_year", "sun_clear_sky_kwh_m2_day_year")


def load_parameter(parameter: str, tiles, folder: Path = RAW):
    """Rows by box, the headers and the blocks not on disk for one parameter."""
    rows, headers, missing = {}, [], []
    for tile in tiles:
        path = folder / raw_name(parameter, tile)
        if not path.exists():
            missing.append(tile)
            continue
        body = path.read_bytes()
        rows.update(read_answer(body, parameter))
        headers.append(answer_header(body))
    return rows, headers, missing


def agreed_header(parameter: str, headers: list[dict]) -> dict | None:
    if not headers:
        return None
    keys = ("version", "start", "end", "fill_value", "sources", "units")
    named = {json.dumps([h.get(k) for k in keys]) for h in headers}
    if len(named) != 1:
        raise ValueError(f"the answers of {parameter} disagree: {sorted(named)[:3]}")
    return {k: headers[0].get(k) for k in keys} | {"name": headers[0].get("name"), "messages": headers[0].get("messages")}


def _date(text: str | None) -> str | None:
    return None if not text else f"{text[0:4]}-{text[4:6]}-{text[6:8]}"


def build(out: Path = OUT) -> None:
    ranked_doc = json.loads(CELLS.read_text())
    ranked = ranked_doc["cells"]
    tiles = tiles_of(ranked)
    listing = json.loads(PARAMETER_LIST.read_text())
    by_param, heads, missing = {}, {}, {}
    for parameter in PARAMETERS:
        rows, headers, gone = load_parameter(parameter, tiles)
        by_param[parameter], missing[parameter] = rows, gone
        heads[parameter] = agreed_header(parameter, headers)
        if listing[parameter]["units"] != UNITS[parameter]:
            raise ValueError(f"{parameter}: the parameter list says {listing[parameter]['units']!r}")
    uv_peaks, uv_missing, uv_files, uv_heads = {}, [], 0, []
    for tile in tiles:
        path = UV_HOURS_RAW / raw_name(UV_HOURS, tile)
        if path.exists():
            body = path.read_bytes()
            uv_peaks.update(read_uv_hours(body))
            uv_heads.append(answer_header(body))
            uv_files += 1
        else:
            uv_missing.append(tile)

    def read_box(parameter, box):
        if box in by_param.get(parameter, {}):
            return by_param[parameter][box]
        path = RAW / raw_name(parameter, cloud.tile_of(box))
        return read_answer(path.read_bytes(), parameter).get(box) if path.exists() else None

    years = years_check(read_box)
    clear_end = years["CLRSKY_DAYS"]["end_year_settled"]
    clear_years = clear_end - CHECK_START + 1 if clear_end else None

    cells = {}
    for cid, cell in sorted(ranked.items()):
        if cell.get("bare") is None or cell["bare"] < 0.15:
            continue
        cells[cid] = cell_record(cell["lat"], cell["lon"], by_param, clear_years, uv_peaks)
    regions = {cid: ranked[cid].get("region") for cid in cells}

    # named places: the square that holds the place (mars_validation.json), its box read directly if not ranked
    validation = json.loads(Path("data/derived/mars_validation.json").read_text())
    named = []
    for site in validation.get("sites") or []:
        if site.get("named_in_job") not in NAMED_POINTS:
            continue
        lat, lon = _lat_lon(site["square"])
        rows = {p: {cloud.grid_box(lat, lon): read_box(p, cloud.grid_box(lat, lon))} for p in PARAMETERS}
        rows = {p: {k: v for k, v in r.items() if v is not None} for p, r in rows.items()}
        record = cells.get(site["square"]) or cell_record(lat, lon, rows, clear_years, uv_peaks)
        named.append({"named_in_job": site["named_in_job"], "entry": site["name"], "place": [site["lat"], site["lon"]],
                      "square": site["square"], "ranked": site["square"] in cells,
                      **{f: record.get(f) for f in YEAR_FIELDS}, "grid": record["grid"]})
    regional = []
    for name, region, box in NAMED_REGIONS:
        ids = [cid for cid in cells if regions[cid] == region and (
            box is None or (box[0] <= ranked[cid]["lat"] <= box[1] and box[2] <= ranked[cid]["lon"] <= box[3]))]
        regional.append({"name": name, "ranked_squares": len(ids),
                         "boxes": len({tuple(cells[c]["grid"]) for c in ids}),
                         **{f: spread(cells[c][f] for c in ids) for f in YEAR_FIELDS}})

    extremes = {
        "most_sunlight_at_the_ground": box_ranking(cells, regions, "sun_kwh_m2_day_year", 5, True),
        "highest_uv_index_24_hour_mean": box_ranking(cells, regions, "uv_index_year", 5, True),
        "highest_uv_index_brightest_hour": box_ranking(cells, regions, "uv_index_brightest_hour_max", 5, True),
        "most_clear_sky_days": box_ranking(cells, regions, "clear_days_year", 5, True),
        "least_haze": box_ranking(cells, regions, "aod_550_year", 5, False),
        "least_haze_north_of_60s": box_ranking({cid: c for cid, c in cells.items() if c["grid"][0] > -60.0}, regions,
                                               "aod_550_year", 5, False),
        "most_haze": box_ranking(cells, regions, "aod_550_year", 5, True),
        "least_sunlight_at_the_ground": box_ranking(cells, regions, "sun_kwh_m2_day_year", 3, False),
        "haziest_month": box_ranking(
            {cid: {"aod_550_month_max": max((v for v in c["aod_550"] or [] if v is not None), default=None),
                   "grid": c["grid"]} for cid, c in cells.items()}, regions, "aod_550_month_max", 5, True),
    }
    sites_doc = json.loads(SITES.read_text())
    mars = mars_figures(sites_doc)
    sentences = comparison_sentences(extremes, mars, cells)

    params_meta = {}
    for parameter in PARAMETERS + (UV_HOURS,):
        entry = listing.get(parameter) or {}
        head = heads.get(parameter) if parameter != UV_HOURS else agreed_header(UV_HOURS, uv_heads)
        params_meta[parameter] = {
            "name_in_the_service": entry.get("name"),
            "definition_in_the_service": entry.get("definition"),
            "units": entry.get("units") or UNITS.get("ALLSKY_SFC_UV_INDEX"),
            "type_in_the_service": entry.get("type"),
            "source_named_in_answers": head["sources"] if head else None,
            "grid": "1 x 1 degree, centres at x.5 (read from the answers)",
            "period_named_by_the_service": f"{_date(head['start'])} to {_date(head['end'])}" if head else None,
            "years_the_values_fit": years.get(parameter, {}).get("years_the_values_fit"),
            "blocks_missing": len(missing.get(parameter, [])) if parameter != UV_HOURS else len(uv_missing),
            "what_it_is_not": WHAT_IT_IS_NOT[parameter],
        }
    left_out = [p for p in PARAMETERS if missing[p]] + ([UV_HOURS] if uv_missing else [])
    first = heads[PARAMETERS[0]] or {}
    meta = {
        "what": ("Mars part, environment side: UV, sunlight at the ground, clear-sky days and haze (aerosol optical depth). "
                 "For every ranked half-degree square of data/derived/mars_cells.json (bare share at least 0.15). "
                 "Each value is the NASA POWER monthly climatology of the 1 degree box, about 111 km tall, holding the square. "
                 "It is not a measurement at the place; many squares share one box. "
                 "It enters no score."),
        "written": now_utc(), "written_by": "agent ENV-MARS, scripts/build_mars_environment.py build",
        "source": (f"NASA POWER, {first.get('name')} {first.get('version')}, regional endpoint, community RE. "
                   f"Data set named in the answers: CERES SYN1deg (SYN1DEG; ALLSKY_KT and CLRSKY_DAYS: SYN1DEG and POWER)."),
        "url_pattern": cloud.URL_PATTERN,
        "parameter_list": {"url": PARAMETER_LIST_URL, "file": str(PARAMETER_LIST),
                           "how_the_names_were_settled": ("Names, definitions and units read from the service's own "
                                                          "climatology parameter list (communities RE, AG and SB, all saved). "
                                                          "Names and definitions searched for dust, aerosol, smoke, haze and particulate. "
                                                          "Found AOD_55, AOD_55_ADJ and AOD_84 only, no dust-only parameter.")},
        "parameters": params_meta,
        "fields": FIELD_MEANING,
        "period_named_by_the_service": f"{_date(first.get('start'))} to {_date(first.get('end'))}",
        "years_check": {
            "what": ("The climatology of each checked parameter against the service's monthly series 2001-2025 of the same box. "
                     f"Five named places, one request a place, saved in {CHECKS}. "
                     "For each last year: how many calendar months the series mean over 2001 to that year equals the climatology. "
                     "For CLRSKY_DAYS the sum is compared, not the mean."),
            "monthly_url_pattern": MONTHLY_URL_PATTERN,
            "by_parameter": years,
            "clear_days_divided_by_years": clear_years,
            "note": ("The service's answers name January 2001 to December 2025. "
                     "data/derived/temperature_cells.json found its temperature values fit 2001 to 2020. "
                     "Read years_the_values_fit as what the numbers show, and the named period as what the service says."),
        },
        "clear_days_rule": ("The service's CLRSKY_DAYS climatology is a count summed over all years of its period. "
                            "Monthly values above 31 occur, such as 137 in January at 28.5 S 70.5 W. "
                            f"clear_days = that count / {clear_years} years." if clear_years else
                            "The years the count was summed over could not be settled: clear_days is null."),
        "uv_rule": ("uv_index is the service's ALLSKY_SFC_UV_INDEX, a mean over all 24 hours of the day, night included. "
                    "uv_index_brightest_hour is the highest hourly value of ALLSKY_SFC_UV_INDEX_HR for each month's mean day."),
        "uv_check": ({"place": "1 degree box 24.5 S 69.5 W (Atacama)", "file": str(UV_CHECK), "url": UV_CHECK_URL,
                      **uv_check(UV_CHECK.read_bytes())} if UV_CHECK.exists() else None),
        "cell_to_grid": "the 1 degree box that holds the square centre (twinfinder.cloud.grid_box); no square sits on a box edge",
        "null_rule": "unknown is null, never 0: a parameter or block not fetched, a fill value (-999), or clear days whose years are not settled",
        "request_rules_followed": ("One parameter and one 10 x 10 degree block a request, one at a time with a 0.5 s pause. "
                                   "User-Agent twinfinder/0.1, no key, no login; wait and try again after a dropped network or 429. "
                                   "On 15 November 2026 UTC the five monthly checks and two probes ran beside the main fetch. "
                                   "So for a few seconds two requests were open at once; the service allows five."),
        "raw_answers": {"folder": str(RAW), "log": str(LOG), "probe_log": str(RAW / "probe_log.jsonl"),
                        "blocks_with_ranked_squares": len(tiles), "uv_hour_blocks_on_disk": uv_files},
        "left_out": left_out,
        "aod_55_against_aod_55_adj": (lambda d: {
            "squares_compared": len(d), "share_with_the_same_yearly_value": round(sum(x < 0.005 for x in d) / len(d), 3),
            "largest_yearly_difference": round(max(d), 2)} if d else None)(
            [abs(c["aod_550_year"] - c["aod_550_adjusted_year"]) for c in cells.values()
             if c["aod_550_year"] is not None and c["aod_550_adjusted_year"] is not None]),
        "counts": {"ranked_squares": len(cells), "boxes": len({tuple(c["grid"]) for c in cells.values()}),
                   "squares_with_clear_days_year_from_month_sum": sum(
                       1 for cid, c in cells.items() if clear_days_year(
                           by_param.get("CLRSKY_DAYS", {}).get(tuple(c["grid"])), clear_years)[1] == "sum of months"),
                   **{f"squares_with_{f}": sum(1 for c in cells.values() if c[f] is not None)
                      for f in ("sun_kwh_m2_day_year", "uv_index_year", "uv_index_brightest_hour_max",
                                "clear_days_year", "aod_550_year")}},
        "named_places": {"points": named, "regions": regional,
                         "rule": ("points: the square that holds the place as data/derived/mars_validation.json names "
                                  "it, read from its 1 degree box; regions: median and range over the ranked squares")},
        "earth_extremes": extremes,
        "mars_comparison": {"figures": mars, "sentences": sentences,
                            "rule": ("Mars figures only as data/derived/mars_sites.json holds them (site cards made "
                                     "from mars_climate.json); 'not in our data' where they do not; nothing typed from "
                                     "memory")},
    }
    write_json(out, {"meta": meta, "cells": cells})
    report(meta, out)


def comparison_sentences(extremes: dict, mars: dict, cells: dict) -> dict:
    """One sentence per thing, Earth's best ranked box against what our data hold for Mars."""
    def top(key):
        return extremes[key][0] if extremes[key] else None

    sun, uv, uvh, clear, haze, dusty, month = (top(k) for k in (
        "most_sunlight_at_the_ground", "highest_uv_index_24_hour_mean", "highest_uv_index_brightest_hour",
        "most_clear_sky_days", "least_haze", "most_haze", "haziest_month"))
    toa = mars["sunlight_top_of_atmosphere"]
    dust = mars["dust_optical_depth"]
    cut = mars["uv_cut_off"]
    kt = cells[sun["example_square"]]["clearness_index_year"] if sun else None
    def where(box):
        named = [r for r in box["regions"][:2] if r != "other"]
        return f"{box['grid'][0]}, {box['grid'][1]}" + (f", {' and '.join(named)}" if named else "")

    out = {}   # every sentence 25 words or fewer (tests/test_mars_environment.py)
    if sun:
        out["sunlight"] = (
            f"Earth's sunniest ranked box ({where(sun)}) gets {sun['value']:.2f} kWh per m2 a day on level ground. "
            f"It keeps {kt} of the sunlight arriving above its air. "
            f"Above its air Mars gets {toa['mars']} {toa['unit']}, {toa['number']} of Earth's {toa['earth']}. "
            f"How much reaches the Mars ground is not in our data.")
    if uv and uvh:
        out["uv"] = (
            f"Earth's highest UV index is {uvh['value']:.1f} in the brightest hour of the mean day ({where(uvh)}). "
            f"As a 24-hour mean it is {uv['value']:.2f}. "
            f"No Earth place matches Mars in kind: sunlight down to {cut['mars']} nm reaches the Mars ground, "
            f"{cut['earth']} nm on Earth. "
            f"Source: {cut['source']}. "
            f"A Mars UV index is not in our data.")
    if clear:
        out["clear_days"] = (
            f"Earth's clearest ranked box ({where(clear)}) has {clear['value']:.0f} days a year with daytime cloud "
            f"under 10 percent over the whole box. "
            f"A count of clear days on Mars is not in our data. "
            f"Our files say dust is in the Mars sky all year ({dust.get('source')}).")
    if haze and dusty and month:
        north = extremes["least_haze_north_of_60s"][0] if extremes.get("least_haze_north_of_60s") else None
        out["haze"] = (
            f"Earth's ranked squares range in yearly aerosol optical depth from {haze['value']:.2f} ({where(haze)}) "
            f"to {dusty['value']:.2f} ({where(dusty)}). "
            + (f"North of 60 S the lowest is {north['value']:.2f} ({where(north)}). " if north else "")
            + f"The haziest month reaches {month['value']:.2f} ({where(month)}). "
            f"These are all particles together, not dust alone, rounded to two decimals. "
            f"Our files give Mars dust optical depth generally below 1 in the aphelion season. "
            f"At the peak of global dust storms it is above {dust['mars']} ({dust.get('source')}). "
            f"Earth's haziest month is {'within' if month['value'] < 1 else 'just above'} that 'below 1', and far from a Mars dust storm.")
    return out


def report(meta: dict, out: Path) -> None:
    print(f"wrote {out} ({out.stat().st_size / 1e6:.1f} MB): {json.dumps(meta['counts'])}")
    print(f"left out: {meta['left_out'] or 'nothing'}")
    for p, v in meta["years_check"]["by_parameter"].items():
        print(f"years check {p}: best end {v['end_year_that_fits_best_all_points']} with "
              f"{v['months_equal_at_that_end_year']} of {v['months_compared']} months; 2001-2025 "
              f"{v['months_equal_with_2001_to_2025']}; fits {v['years_the_values_fit']}")
    print(f"clear days divided by {meta['years_check']['clear_days_divided_by_years']} years")
    fields = ("sun_kwh_m2_day_year", "uv_index_year", "uv_index_brightest_hour_max", "clear_days_year", "aod_550_year",
              "clearness_index_year")
    print("\nplace | " + " | ".join(fields))
    for p in meta["named_places"]["points"]:
        print(f"{p['named_in_job']} {p['square']} ranked={p['ranked']} box {p['grid']} | "
              + " | ".join(str(p[f]) for f in fields))
    for r in meta["named_places"]["regions"]:
        print(f"{r['name']}: {r['ranked_squares']} squares, {r['boxes']} boxes | "
              + " | ".join(json.dumps(r[f]) for f in fields))
    for key, boxes in meta["earth_extremes"].items():
        print(f"\n{key}:")
        for b in boxes:
            print(f"   {b['grid']} {b['value']} ({b['ranked_squares']} squares; {', '.join(b['regions'])}; e.g. {b['example_square']})")
    print()
    for key, sentence in meta["mars_comparison"]["sentences"].items():
        print(f"{key}: {sentence}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("step", choices=["fetch", "fetch-uv-hours", "check-years", "build"])
    parser.add_argument("--pause", type=float, default=PAUSE_S)
    parser.add_argument("--out", type=Path, default=OUT, help="build: where to write (default %(default)s)")
    args = parser.parse_args()
    if args.step == "fetch":
        fetch_step(args.pause)
    elif args.step == "fetch-uv-hours":
        fetch_uv_hours_step(args.pause)
    elif args.step == "check-years":
        check_years_step(args.pause)
    else:
        build(args.out)


if __name__ == "__main__":
    main()

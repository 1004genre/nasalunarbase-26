# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Power on site: how solar, wind and geothermal power would do at every place, beside the Moon and Mars.

Writes data/derived/power_cells.json (the Moon part's areas, data/derived/grazing_cells.json) and
data/derived/mars_power.json (the Mars part's squares, data/derived/mars_cells.json).

A rough estimate by our own rule of thumb. It is not a measurement or an engineering study.

Three steps, each safe to run again (nothing on disk is asked for twice):

    uv run python scripts/build_power_cells.py fetch-sources   # WRI power plants; GVP eruptions if nobody has them
    uv run python scripts/build_power_cells.py fetch-power     # NASA POWER WS50M, polar blocks first (slow: run it
                                                               # in the background, it logs every request)
    uv run python scripts/build_power_cells.py build           # no network; writes the two JSON files

Every rule and every constant is in RULES below; the same words go into the meta of both outputs.

What is read from other groups (never written): NASA POWER sunlight answers kept by the environment
groups (data/raw/power_environment/, data/raw/power_global_environment/), 10 m wind of the
power-extra group (data/derived/power_extra_cells.json, data/derived/mars_power_extra.json or its raw
answers in data/raw/power_extra/), cloud (data/derived/cloud_cells.json), the low-Sun calendar
(data/derived/grazing_cells.json), the Smithsonian volcano list (data/raw/gvp_volcanoes/), the Moon
cards, the Mars sites and climate, and the saved NASA fact sheets.

Requests go only to NASA POWER (power.larc.nasa.gov), the Smithsonian Global Volcanism Program's
web services (webservices.volcano.si.edu) and the World Resources Institute's GitHub repository
(raw.githubusercontent.com/wri/global-power-plant-database), with User-Agent twinfinder/0.1 and
nothing personal; no key, no login. A request for a login stops the step.
"""
from __future__ import annotations

import argparse
import csv
import datetime
import http.client
import html
import io
import json
import math
import os
import re
import statistics
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from twinfinder import cloud, temperature  # noqa: E402

# ==== THE ONE TABLE: every rule and every constant ===============================================================
# key: (value, unit, the rule in plain words). The words go into the meta of both outputs as they stand.

RULES = {
    # -- 1a. ordinary solar yield -------------------------------------------------------------------------------
    "panel_factor": (0.75, "kWh per kW of panels per kWh per m2",
                     "Panel yield, rule of thumb: kWh a day from each kilowatt of panels = sunlight on level ground "
                     "(kWh per square metre per day) x 0.75. A panel's kilowatt rating assumes 1 kW per square metre "
                     "of sunlight; 0.75 allows for heat, dirt, snow, wiring and inverter losses. Panels tilted toward "
                     "the Sun do better at high latitude (a low Sun hits a level panel at a glancing angle); that is "
                     "not counted here."),
    "solar_good_kwh": (4.5, "kWh per m2 per day",
                       "Solar class 'good': yearly mean sunlight on level ground of at least 4.5 kWh per square metre "
                       "per day (about 1,640 kWh per square metre a year)."),
    "solar_fair_kwh": (3.0, "kWh per m2 per day",
                       "Solar class 'fair': from 3.0 up to 4.5 kWh per square metre per day; 'poor' below 3.0. These "
                       "cut values are our own: sunny deserts (5.5 to 7) read good, central Europe (about 3) fair to "
                       "poor, the high Arctic (about 2) poor."),
    "sunless_value": (0.0, "kWh per m2 per day",
                      "A month counts as having no sunlight (polar night) when NASA POWER gives exactly 0.0 for it; "
                      "a month the service leaves blank is unknown (null), not dark."),
    # -- 1b. solar under the lunar-like low Sun -----------------------------------------------------------------
    "solar_constant": (1361.0, "W per m2",
                       "Sunlight above the air at the distance of Earth and the Moon from the Sun: 1,361 watts per "
                       "square metre (NASA NSSDCA Earth and Moon fact sheets, saved in this project). At the Moon's "
                       "south pole a panel standing upright and facing a Sun on the horizon receives all of it, "
                       "because there is no air."),
    "kasten_young": ((0.50572, 6.07995, 1.6364), "a, b (degrees), c",
                     "Air mass at Sun height h (degrees), the thickness of air the sunlight crosses relative to a "
                     "Sun overhead, by Kasten and Young (1989), Applied Optics 28(22), 4735-4738: "
                     "AM = 1 / (sin h + 0.50572 x (h + 6.07995)^-1.6364). Sea level; the place's height is not counted."),
    "meinel": ((0.7, 0.678), "base, exponent",
               "Direct beam on a panel facing the Sun through clear air, by Meinel and Meinel (1976), Applied Solar "
               "Energy (Addison-Wesley), as quoted by PVEducation: beam = 1,361 x 0.7^(AM^0.678) watts per square "
               "metre. 0.7 is the share passed by one air mass of typical clear air; the exponent 0.678 allows for "
               "air that is not uniform."),
    "half_ceiling": (0.5, "share of the ceiling",
                     "The power is worked out at each lunar Sun ceiling (the limit_deg of each region in "
                     "grazing_cells.json) and at half its height, because the Sun spends much of the low-Sun hours "
                     "below the ceiling."),
    "clear_share_rule": (None, "0 to 1",
                         "A place's clear-sky share in its best ten-day periods = mean of (1 - cloud percent / 100) "
                         "over the months of the ten-day periods listed in grazing_cells.json under "
                         "targets.<region>.top_bins, weighted by the low-Sun hours of each period. Cloud percent is "
                         "cloud_pct of cloud_cells.json (monthly mean over all hours, CERES SYN1deg). The low-Sun "
                         "power under the place's typical sky = clear-sky figure x that share. Null where the "
                         "region has no best periods at the place or the cloud is unknown."),
    # -- 2. wind -------------------------------------------------------------------------------------------------
    "air_density_sea": (1.225, "kg per m3",
                        "Air density at sea level in the International Standard Atmosphere: 1.225 kilograms per "
                        "cubic metre."),
    "density_with_height": ((0.0065, 288.15, 4.2559), "lapse K per m, sea-level K, exponent",
                            "Air density at height z metres (International Standard Atmosphere, lower 11 km): "
                            "1.225 x (1 - 0.0065 x z / 288.15)^4.2559. z is the mean height of the model grid box "
                            "the 50 m wind is given for (as the service names it in each answer); where the "
                            "service gives no height, sea-level density is used and the height is null. Cold polar "
                            "air is denser than the standard atmosphere (about 10 % at -15 C), which would raise "
                            "the figure; that is not counted."),
    "speed_spread_factor": (1.91, "dimensionless",
                            "Factor for the usual spread of wind speeds: if speeds follow a Rayleigh distribution "
                            "the mean of the speed cubed is 6 / pi = 1.91 times the mean speed cubed, which is how "
                            "the standard 50 m wind classes were tied to mean speeds."),
    "wind_power_rule": (None, "W per m2 of rotor area",
                        "Power in the wind at 50 m = 0.5 x air density x 1.91 x (yearly mean speed)^3, in watts per "
                        "square metre of rotor area: the power the moving air carries, not what a turbine delivers "
                        "(a turbine takes at most 59 %, in practice 35 to 45 %). The yearly mean speed is the plain "
                        "mean of the 12 monthly means of NASA POWER's WS50M."),
    "wind_class_bands": ((200, 300, 400, 500, 600, 800), "W per m2 at 50 m",
                         "Wind power classes 1 to 7 at 50 m (US Department of Energy and NREL, Elliott et al. 1986, "
                         "Wind Energy Resource Atlas of the United States; at sea level these match mean speeds of "
                         "5.6, 6.4, 7.0, 7.5, 8.0 and 8.8 m/s): class 1 below 200 W per square metre, 2 from 200, "
                         "3 from 300, 4 from 400, 5 from 500, 6 from 600, 7 from 800. The bands are from the "
                         "published table as we know it; no copy was saved tonight."),
    "wind_good_w": (400, "W per m2",
                    "Wind class 'good': class 4 or higher (at least 400 watts per square metre at 50 m)."),
    "wind_fair_w": (200, "W per m2",
                    "Wind class 'fair': classes 2 and 3 (200 up to 400); 'poor': class 1 (below 200)."),
    # -- 3. geothermal -------------------------------------------------------------------------------------------
    "geo_good_plant_km": (50.0, "km",
                          "Geothermal class 'good': a working geothermal power plant (WRI Global Power Plant "
                          "Database, primary fuel geothermal) lies within 50 km ..."),
    "geo_good_volcano_km": (30.0, "km", "... or a volcano that erupted since 1990 lies within 30 km."),
    "geo_recent_year": (1990, "year",
                        "'Erupted since 1990': the Smithsonian list of volcanoes gives a last eruption year of 1990 "
                        "or later, or its list of eruptions holds a confirmed eruption that started or ended in "
                        "1990 or later."),
    "geo_fair_plant_km": (150.0, "km",
                          "Geothermal class 'fair': a working geothermal plant within 150 km, or any volcano of the "
                          "Holocene (the last 11,700 years) within 100 km ..."),
    "geo_fair_volcano_km": (100.0, "km", "... 'poor' otherwise."),
    "earth_radius_km": (6371.0088, "km",
                        "Distances are along the ground (great circle) from the area or square centre, on a sphere "
                        "of mean Earth radius 6,371 km."),
    # -- fetching ------------------------------------------------------------------------------------------------
    "min_gap_s": (2.0, "s", "NASA POWER is asked one request at a time, at least 2 seconds apart."),
    "refusal_wait_s": (60.0, "s", "On a refusal (429) or a server fault (5xx) we back off at least a minute."),
    "net_wait_s": (20.0, "s", "On a dropped network we wait 20, 40, 60 ... seconds (at most 300) and try again."),
}
R = {key: value for key, (value, _unit, _words) in RULES.items()}

ROUGH = "A rough estimate by our own rule of thumb. It is not a measurement or an engineering study."
LOW_SUN_SENTENCE = (
    "This is a textbook clear-air estimate: real polar air and haze vary from day to day, so a real panel can get "
    "less or somewhat more; it shows that Earth's low Sun delivers only a fraction of the power the same low Sun "
    "gives a panel on the Moon, where no air stands in the way.")

# ==== paths ======================================================================================================

RAW_WIND = ROOT / "data/raw/power_wind"
RAW_PLANTS = ROOT / "data/raw/power_plants"
WIND_LOG = RAW_WIND / "fetch_log.jsonl"
PLANTS_LOG = RAW_PLANTS / "downloads.jsonl"
MOON_PLACES = ROOT / "data/derived/grazing_cells.json"
MARS_PLACES = ROOT / "data/derived/mars_cells.json"
CLOUD = ROOT / "data/derived/cloud_cells.json"
POWER_EXTRA = ROOT / "data/derived/power_extra_cells.json"
MARS_POWER_EXTRA = ROOT / "data/derived/mars_power_extra.json"
POWER_EXTRA_RAW = ROOT / "data/raw/power_extra"
ENV_MOON = ROOT / "data/derived/environment_cells.json"
ENV_MARS = ROOT / "data/derived/mars_environment.json"
SUN_RAW_DIRS = [ROOT / "data/raw/power_environment", ROOT / "data/raw/power_global_environment", RAW_WIND]
PARAMETER_LISTS = [ROOT / "data/raw/power_extra/parameters/manager_list_RE_climatology.json",
                   ROOT / "data/raw/power_environment/parameters/manager_list_RE_climatology.json",
                   RAW_WIND / "parameters/manager_list_RE_climatology.json"]
GVP_VOLCANOES = ROOT / "data/raw/gvp_volcanoes/holocene_volcanoes.geojson"
GVP_VOLCANO_DOWNLOADS = ROOT / "data/raw/gvp_volcanoes/downloads.json"
GVP_CAPABILITIES = ROOT / "data/raw/gvp_volcanoes/wfs_capabilities_2.0.0.xml"
GVP_ERUPTIONS_OTHER = ROOT / "data/raw/gvp_eruptions"
GVP_ERUPTIONS_OWN = RAW_PLANTS / "gvp_holocene_eruptions.geojson"
STEADY = ROOT / "data/derived/steady_effects_cells.json"
MARS_STEADY = ROOT / "data/derived/mars_steady_effects.json"
GPPD_CSV = RAW_PLANTS / "global_power_plant_database.csv"
MOON_CARDS = ROOT / "data/derived/moon_cards.json"
MARS_SITES = ROOT / "data/derived/mars_sites.json"
MARS_CLIMATE = ROOT / "data/derived/mars_climate.json"
FACT_MARS = ROOT / "data/raw/mars_climate/factsheets/marsfact.html"
FACT_EARTH = ROOT / "data/raw/mars_climate/factsheets/earthfact.html"
FACT_MOON = ROOT / "data/raw/moon_provenance/nssdc_moonfact.html"
OUT_MOON = ROOT / "data/derived/power_cells.json"
OUT_MARS = ROOT / "data/derived/mars_power.json"

USER_AGENT = cloud.USER_AGENT          # "twinfinder/0.1", nothing personal
MANAGER_URL = "https://power.larc.nasa.gov/api/system/manager/parameters?community=RE&temporal=climatology"
GPPD_BASE = "https://raw.githubusercontent.com/wri/global-power-plant-database/master/"
GPPD_FILES = {"global_power_plant_database.csv": "output_database/global_power_plant_database.csv",
              "DATABASE_VERSION": "output_database/DATABASE_VERSION",
              "README.md": "README.md"}
GVP_WFS = "https://webservices.volcano.si.edu/geoserver/GVP-VOTW/wfs"
GVP_ERUPTIONS_URL = (GVP_WFS + "?service=WFS&version=2.0.0&request=GetFeature"
                     "&typeNames=GVP-VOTW:Smithsonian_VOTW_Holocene_Eruptions&outputFormat=application/json")

WIND_PARAMETER = "WS50M"
SUN_PARAMETER = "ALLSKY_SFC_SW_DWN"
UNITS = {"WS50M": "m/s", "WS10M": "m/s", "ALLSKY_SFC_SW_DWN": "kW-hr/m^2/day"}
RANGE = {"WS50M": (0.0, 60.0), "WS10M": (0.0, 50.0), "ALLSKY_SFC_SW_DWN": (0.0, 15.0)}
MONTHS = cloud.MONTHS
MONTH_NAMES = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
FILL_VALUE = -999.0
ATTEMPTS = 6
ROUNDS = 3

CREDIT_POWER = ("The data was obtained from the National Aeronautics and Space Administration (NASA) Langley Research "
                "Center (LaRC) Prediction of Worldwide Energy Resource (POWER) Project funded through the NASA Earth "
                "Science/Applied Science Program (https://power.larc.nasa.gov/docs/referencing/); POWER Climatology "
                "API {version}, read {date}. No key, no login.")


class LoginRequired(RuntimeError):
    """A source asked for a login or refused us (401 or 403): we do not go on."""


def now_utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_json(path: Path, value) -> None:
    side = path.with_name(path.name + ".part")
    side.write_text(json.dumps(value, separators=(",", ":"), allow_nan=False))
    os.replace(side, path)


def write_bytes(path: Path, body: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    side = path.with_name(path.name + ".part")
    side.write_bytes(body)
    os.replace(side, path)


def log_line(path: Path, entry: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as handle:
        handle.write(json.dumps({"time": now_utc(), **entry}) + "\n")


# ==== fetching ===================================================================================================

class Pacer:
    """Keeps the start of two requests at least `gap` seconds apart."""

    def __init__(self, gap: float = R["min_gap_s"]):
        self.gap, self.last = gap, None

    def wait(self) -> None:
        if self.last is not None:
            since = time.monotonic() - self.last
            if since < self.gap:
                time.sleep(self.gap - since)
        self.last = time.monotonic()


def _retry_after(error: urllib.error.HTTPError) -> float:
    try:
        return min(max(float(error.headers.get("Retry-After")), 1.0), 600.0)
    except (AttributeError, TypeError, ValueError):
        return 0.0


def http_get(url: str, timeout: float = 180.0, attempts: int = ATTEMPTS) -> bytes:
    """Body of one GET. Waits and tries again on 429, 5xx and dropped connections; stops on 401/403."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except urllib.error.HTTPError as error:
            if error.code in (401, 403):
                raise LoginRequired(f"{error.code} for {url}") from error
            busy = error.code == 429 or 500 <= error.code < 600
            if not busy or attempt == attempts:
                raise
            wait = max(R["refusal_wait_s"], _retry_after(error))
            print(f"{now_utc()} {error.code} from the service; waiting {wait:.0f} s", flush=True)
            time.sleep(wait)
        except (urllib.error.URLError, ConnectionError, TimeoutError, http.client.IncompleteRead, OSError) as error:
            if attempt == attempts:
                raise
            wait = min(R["net_wait_s"] * attempt, 300.0)
            print(f"{now_utc()} network: {type(error).__name__}: {error}; waiting {wait:.0f} s", flush=True)
            time.sleep(wait)
    raise RuntimeError("unreachable")


def read_power(raw, parameter: str) -> dict[tuple[float, float], tuple[list[float | None], float | None, float | None]]:
    """{(lat, lon): ([12 monthly values, January first], annual value, grid height m)} from one regional answer.

    The fill value becomes None, a real 0.0 stays 0.0. Units must be those in UNITS and every value inside
    RANGE; an answer without grid points (an error message) or for another parameter is an error.
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
        coordinates = feature["geometry"]["coordinates"]            # GeoJSON: longitude first
        lon, lat = float(coordinates[0]), float(coordinates[1])
        if lon >= 180.0:
            lon -= 360.0
        elev = coordinates[2] if len(coordinates) > 2 else None
        elev = (float(elev) if isinstance(elev, (int, float)) and not isinstance(elev, bool)
                and float(elev) not in fills else None)
        months = feature["properties"]["parameter"][parameter]
        where = f"at {lat}, {lon}"
        out[(lat, lon)] = ([value(months.get(m), f"{m} {where}") for m in MONTHS],
                           value(months.get("ANN"), f"ANN {where}"), elev)
    return out


def answer_header(raw) -> dict:
    data = json.loads(raw)
    header = data.get("header") or {}
    api = header.get("api") or {}
    return {"name": api.get("name"), "version": api.get("version"), "sources": header.get("sources"),
            "start": header.get("start"), "end": header.get("end"), "fill_value": header.get("fill_value")}


def sun_file(tile) -> Path | None:
    """The sunlight answer of one block, wherever a group keeps it (theirs first, ours last)."""
    name = cloud.raw_name(SUN_PARAMETER, tuple(tile))
    for folder in SUN_RAW_DIRS:
        if (folder / name).exists():
            return folder / name
    return None


def load_places() -> tuple[list[dict], list[dict]]:
    moon = json.loads(MOON_PLACES.read_text())["cells"]
    mars_cells = json.loads(MARS_PLACES.read_text())["cells"]
    mars = [{"id": key, "lat": c["lat"], "lon": c["lon"]} for key, c in mars_cells.items()]
    return moon, mars


def parameter_list_entry(name: str) -> tuple[dict | None, str | None]:
    for path in PARAMETER_LISTS:
        if path.exists():
            listing = json.loads(path.read_text())
            return listing.get(name), str(path.relative_to(ROOT))
    return None, None


def fetch_power(only: str | None) -> None:
    entry, where = parameter_list_entry(WIND_PARAMETER)
    if where is None:                                    # nobody kept the service's parameter list: ask it once
        print(f"{now_utc()} asking the service's parameter list", flush=True)
        body = http_get(MANAGER_URL)
        write_bytes(RAW_WIND / "parameters/manager_list_RE_climatology.json", body)
        log_line(WIND_LOG, {"url": MANAGER_URL, "file": "parameters/manager_list_RE_climatology.json",
                            "bytes": len(body)})
        entry, where = parameter_list_entry(WIND_PARAMETER)
    if not entry or entry.get("units") != "m/s":
        raise SystemExit(f"the service's parameter list ({where}) has no {WIND_PARAMETER} in m/s: {entry!r}")
    print(f"{now_utc()} {WIND_PARAMETER} in the service's list ({where}): {entry.get('name')}, {entry.get('units')}",
          flush=True)

    moon, mars = load_places()
    moon_tiles = temperature.tiles_for_cells(moon)
    mars_tiles = [t for t in temperature.tiles_for_cells(mars) if t not in set(moon_tiles)]
    jobs = []
    if only in (None, "moon"):
        jobs += [(WIND_PARAMETER, t, "moon") for t in moon_tiles]
    if only in (None, "mars"):
        jobs += [(WIND_PARAMETER, t, "mars") for t in mars_tiles]
    sun_moon = cloud.tiles_for(cloud.boxes_of(moon))
    sun_mars = [t for t in cloud.tiles_for(cloud.boxes_of(mars)) if t not in set(sun_moon)]
    if only in (None, "moon"):
        jobs += [(SUN_PARAMETER, t, "moon") for t in sun_moon]
    if only in (None, "mars"):
        jobs += [(SUN_PARAMETER, t, "mars") for t in sun_mars]

    RAW_WIND.mkdir(parents=True, exist_ok=True)
    pacer = Pacer()
    asked = skipped = 0
    failed = []
    in_a_row = 0
    started = time.time()
    print(f"{now_utc()} {len(jobs)} jobs ({len(moon_tiles)} polar blocks, {len(mars_tiles)} more worldwide)", flush=True)
    for n, (parameter, tile, part) in enumerate(jobs, 1):
        name = cloud.raw_name(parameter, tile)
        dest = RAW_WIND / name
        if dest.exists() or (parameter == SUN_PARAMETER and sun_file(tile) is not None):
            skipped += 1
            continue
        url = cloud.regional_url(parameter, tile)
        for round_ in range(1, ROUNDS + 1):
            pacer.wait()
            try:
                body = http_get(url)
                read_power(body, parameter)          # raises if this is not an answer: nothing is kept
            except LoginRequired as error:
                log_line(WIND_LOG, {"file": name, "part": part, "error": f"LoginRequired: {error}"})
                print(f"{now_utc()} STOP: the service asked for a login ({error})", flush=True)
                raise SystemExit(2)
            except Exception as error:  # noqa: BLE001 - logged, retried, then listed
                log_line(WIND_LOG, {"file": name, "part": part, "error": f"{type(error).__name__}: {error}",
                                    "round": round_})
                print(f"{now_utc()} {name}: {type(error).__name__}: {error} (round {round_} of {ROUNDS})", flush=True)
                if round_ == ROUNDS:
                    failed.append(name)
                    in_a_row += 1
                else:
                    time.sleep(R["refusal_wait_s"] * round_)
                continue
            write_bytes(dest, body)
            log_line(WIND_LOG, {"url": url, "file": name, "part": part, "bytes": len(body)})
            asked += 1
            in_a_row = 0
            if asked % 20 == 0:
                print(f"{now_utc()} asked {asked} (at {n} of {len(jobs)}, {part}); "
                      f"{(time.time() - started) / asked:.1f} s a request", flush=True)
            break
        if in_a_row >= 3:
            print(f"{now_utc()} three blocks failed in a row: stopping; run again later", flush=True)
            break
    print(f"{now_utc()} done: asked {asked}, already on disk {skipped}, failed {len(failed)} {failed[:10]}", flush=True)


def gvp_eruptions_elsewhere() -> Path | None:
    """An eruption list another group keeps (data/raw/gvp_eruptions/), if it holds one we can read."""
    if not GVP_ERUPTIONS_OTHER.is_dir():
        return None
    for path in sorted(GVP_ERUPTIONS_OTHER.glob("*json")):
        try:
            data = json.loads(path.read_text())
        except (ValueError, UnicodeDecodeError):
            continue
        features = data.get("features") if isinstance(data, dict) else None
        if features and isinstance(features[0], dict) and "Eruption_Number" in (features[0].get("properties") or {}):
            return path
    return None


def fetch_sources() -> None:
    RAW_PLANTS.mkdir(parents=True, exist_ok=True)
    for name, path in GPPD_FILES.items():
        dest = RAW_PLANTS / name
        if dest.exists():
            print(f"{now_utc()} on disk: {dest.relative_to(ROOT)}", flush=True)
            continue
        url = GPPD_BASE + path
        body = http_get(url)
        if name.endswith(".csv") and not body.startswith(b"country,"):
            raise SystemExit(f"{url} did not give the database CSV (starts {body[:80]!r})")
        write_bytes(dest, body)
        log_line(PLANTS_LOG, {"url": url, "file": name, "bytes": len(body)})
        print(f"{now_utc()} saved {dest.relative_to(ROOT)} ({len(body)} bytes)", flush=True)
        time.sleep(1.0)
    other = gvp_eruptions_elsewhere()
    if other is not None:
        print(f"{now_utc()} eruption list kept by another group: {other.relative_to(ROOT)}; not asked", flush=True)
    elif GVP_ERUPTIONS_OWN.exists():
        print(f"{now_utc()} on disk: {GVP_ERUPTIONS_OWN.relative_to(ROOT)}", flush=True)
    else:
        body = http_get(GVP_ERUPTIONS_URL, timeout=300.0)
        data = json.loads(body)
        if not data.get("features"):
            raise SystemExit(f"the eruption list came back empty: {body[:200]!r}")
        write_bytes(GVP_ERUPTIONS_OWN, body)
        log_line(PLANTS_LOG, {"url": GVP_ERUPTIONS_URL, "file": GVP_ERUPTIONS_OWN.name, "bytes": len(body),
                              "features": len(data["features"]), "numberMatched": data.get("numberMatched")})
        print(f"{now_utc()} saved {GVP_ERUPTIONS_OWN.relative_to(ROOT)} ({len(data['features'])} eruptions)", flush=True)


# ==== the rules as code ==========================================================================================

def air_mass(h_deg: float) -> float:
    a, b, c = R["kasten_young"]
    return 1.0 / (math.sin(math.radians(h_deg)) + a * (h_deg + b) ** (-c))


def clear_beam(h_deg: float) -> float:
    base, exponent = R["meinel"]
    return R["solar_constant"] * base ** (air_mass(h_deg) ** exponent)


def solar_class(year_kwh: float | None) -> str | None:
    if year_kwh is None:
        return None
    if year_kwh >= R["solar_good_kwh"]:
        return "good"
    return "fair" if year_kwh >= R["solar_fair_kwh"] else "poor"


def air_density(height_m: float | None) -> float:
    lapse, t0, exponent = R["density_with_height"]
    if height_m is None:
        return R["air_density_sea"]
    return R["air_density_sea"] * (1.0 - lapse * height_m / t0) ** exponent


def wind_power(speed: float, density: float) -> float:
    return 0.5 * density * R["speed_spread_factor"] * speed ** 3


def wind_classes(power: float | None) -> tuple[int | None, str | None]:
    if power is None:
        return None, None
    nrel = 1 + sum(power >= band for band in R["wind_class_bands"])
    word = "good" if power >= R["wind_good_w"] else "fair" if power >= R["wind_fair_w"] else "poor"
    return nrel, word


def geo_class(plant_km: float | None, recent_km: float | None, holocene_km: float | None) -> str:
    inf = float("inf")
    plant_km = inf if plant_km is None else plant_km
    recent_km = inf if recent_km is None else recent_km
    holocene_km = inf if holocene_km is None else holocene_km
    if plant_km <= R["geo_good_plant_km"] or recent_km <= R["geo_good_volcano_km"]:
        return "good"
    if plant_km <= R["geo_fair_plant_km"] or holocene_km <= R["geo_fair_volcano_km"]:
        return "fair"
    return "poor"


def plain_mean(values) -> float | None:
    if values is None or any(v is None for v in values):
        return None
    return sum(values) / len(values)


def rnd(value, digits):
    return None if value is None else round(value, digits)


# ==== reading the inputs =========================================================================================

def read_blocks(parameter: str, tiles, folders) -> tuple[dict, list[str], list[dict]]:
    """All grid points of a parameter from the answers on disk; the names of blocks not found; their headers."""
    by_point, missing, heads = {}, [], []
    for tile in tiles:
        name = cloud.raw_name(parameter, tuple(tile))
        path = next((folder / name for folder in folders if (folder / name).exists()), None)
        if path is None:
            missing.append(name)
            continue
        body = path.read_bytes()
        by_point.update(read_power(body, parameter))
        if len(heads) < 3:
            heads.append({**answer_header(body), "file": str(path.relative_to(ROOT))})
    return by_point, missing, heads


def read_plants() -> tuple[list[dict], dict]:
    """Working geothermal plants of the WRI Global Power Plant Database, with coordinates and capacity."""
    if not GPPD_CSV.exists():
        return [], {"found": False, "why": f"{GPPD_CSV.relative_to(ROOT)} is not on disk (run fetch-sources)"}
    rows = list(csv.DictReader(io.StringIO(GPPD_CSV.read_text(encoding="utf-8"))))
    plants = []
    for row in rows:
        if (row.get("primary_fuel") or "").strip().lower() != "geothermal":
            continue
        try:
            lat, lon = float(row["latitude"]), float(row["longitude"])
        except (TypeError, ValueError):
            continue
        try:
            mw = float(row["capacity_mw"])
        except (TypeError, ValueError):
            mw = None
        year = row.get("commissioning_year") or None
        plants.append({"name": row.get("name"), "country": row.get("country_long"), "mw": mw, "lat": lat, "lon": lon,
                       "id": row.get("gppd_idnr"), "commissioned": rnd(float(year), 0) if year else None})
    version_file = RAW_PLANTS / "DATABASE_VERSION"
    version = version_file.read_text().strip() if version_file.exists() else None
    log = [json.loads(line) for line in PLANTS_LOG.read_text().splitlines()] if PLANTS_LOG.exists() else []
    when = next((e["time"] for e in log if e.get("file") == GPPD_CSV.name), None)
    return plants, {"found": True, "rows": len(rows), "geothermal_plants": len(plants),
                    "geothermal_mw": round(sum(p["mw"] or 0 for p in plants), 1), "database_version": version,
                    "fetched": when}


def read_volcanoes() -> tuple[list[dict], dict]:
    """Holocene volcanoes, each with whether it erupted since 1990 (by either Smithsonian list)."""
    if not GVP_VOLCANOES.exists():
        return [], {"found": False, "why": f"{GVP_VOLCANOES.relative_to(ROOT)} is not on disk"}
    features = json.loads(GVP_VOLCANOES.read_text())["features"]
    volcanoes = {}
    for f in features:
        p = f["properties"]
        lat, lon = p.get("Latitude"), p.get("Longitude")
        if lat is None or lon is None:
            lon, lat = f["geometry"]["coordinates"][:2]
        volcanoes[p["Volcano_Number"]] = {"name": p.get("Volcano_Name"), "country": p.get("Country"),
                                          "lat": float(lat), "lon": float(lon),
                                          "last_eruption_year": p.get("Last_Eruption_Year"),
                                          "recent_by_volcano_list": (p.get("Last_Eruption_Year") is not None
                                                                     and p["Last_Eruption_Year"] >= R["geo_recent_year"]),
                                          "recent_by_eruption_list": False}
    eruption_path = gvp_eruptions_elsewhere() or (GVP_ERUPTIONS_OWN if GVP_ERUPTIONS_OWN.exists() else None)
    info = {"volcano_list": str(GVP_VOLCANOES.relative_to(ROOT)), "volcanoes": len(volcanoes)}
    if eruption_path is not None:
        eruptions = json.loads(eruption_path.read_text())["features"]
        confirmed = recent = 0
        for f in eruptions:
            p = f["properties"]
            if p.get("Activity_Type") != "Confirmed Eruption":
                continue
            confirmed += 1
            years = [y for y in (p.get("StartDateYear"), p.get("EndDateYear")) if isinstance(y, (int, float))]
            if not years or max(years) < R["geo_recent_year"]:
                continue
            recent += 1
            number = p.get("Volcano_Number")
            if number not in volcanoes:                        # an eruption of a volcano not in the list: keep it
                lon, lat = f["geometry"]["coordinates"][:2]
                volcanoes[number] = {"name": p.get("Volcano_Name"), "country": None, "lat": float(lat),
                                     "lon": float(lon), "last_eruption_year": None,
                                     "recent_by_volcano_list": False, "recent_by_eruption_list": True}
            volcanoes[number]["recent_by_eruption_list"] = True
        info.update({"eruption_list": str(eruption_path.relative_to(ROOT)), "eruptions": len(eruptions),
                     "confirmed_eruptions": confirmed, "confirmed_eruptions_since_1990": recent})
    else:
        info["eruption_list"] = None
    out = []
    for number, v in volcanoes.items():
        v["number"] = number
        v["recent"] = v["recent_by_volcano_list"] or v["recent_by_eruption_list"]
        out.append(v)
    info["erupted_since_1990"] = sum(v["recent"] for v in out)
    info["erupted_since_1990_by_volcano_list_only"] = sum(v["recent_by_volcano_list"] and not v["recent_by_eruption_list"]
                                                          for v in out)
    info["erupted_since_1990_by_eruption_list_only"] = sum(v["recent_by_eruption_list"] and not v["recent_by_volcano_list"]
                                                           for v in out)
    return out, info


def nearest(lats, lons, points, radius_km=None, weights=None):
    """Index and distance (km) of the nearest point to each place; and, with radius_km, count and weight sum within."""
    n = len(lats)
    idx = np.full(n, -1, dtype=int)
    dist = np.full(n, np.inf)
    count = np.zeros(n, dtype=int)
    total = np.zeros(n)
    if not points:
        return idx, dist, count, total
    plat = np.radians(np.array([p["lat"] for p in points]))[None, :]
    plon = np.radians(np.array([p["lon"] for p in points]))[None, :]
    w = np.array([0.0 if x is None else x for x in (weights or [0.0] * len(points))])[None, :]
    lat_all, lon_all = np.radians(np.asarray(lats, dtype=float)), np.radians(np.asarray(lons, dtype=float))
    for start in range(0, n, 1500):
        la = lat_all[start:start + 1500, None]
        lo = lon_all[start:start + 1500, None]
        a = np.sin((plat - la) / 2) ** 2 + np.cos(la) * np.cos(plat) * np.sin((plon - lo) / 2) ** 2
        d = 2 * R["earth_radius_km"] * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))
        idx[start:start + 1500] = np.argmin(d, axis=1)
        dist[start:start + 1500] = np.min(d, axis=1)
        if radius_km is not None:
            inside = d <= radius_km
            count[start:start + 1500] = inside.sum(axis=1)
            total[start:start + 1500] = (inside * w).sum(axis=1)
    return idx, dist, count, total


def geothermal_table(places, plants, volcanoes) -> list[dict]:
    lats = [p["lat"] for p in places]
    lons = [p["lon"] for p in places]
    recent = [v for v in volcanoes if v["recent"]]
    p_idx, p_km, p_n, p_mw = nearest(lats, lons, plants, R["geo_fair_plant_km"], [p["mw"] for p in plants])
    r_idx, r_km, _, _ = nearest(lats, lons, recent)
    h_idx, h_km, _, _ = nearest(lats, lons, volcanoes)
    rows = []
    for i in range(len(places)):
        plant = plants[p_idx[i]] if plants else None
        rv = recent[r_idx[i]] if recent else None
        hv = volcanoes[h_idx[i]] if volcanoes else None
        pk = float(p_km[i]) if plants else None
        rk = float(r_km[i]) if recent else None
        hk = float(h_km[i]) if volcanoes else None
        rows.append({
            "class": geo_class(pk, rk, hk) if (plants or volcanoes) else None,
            "plant": (None if plant is None else
                      {"name": plant["name"], "country": plant["country"], "mw": plant["mw"], "km": round(pk, 1)}),
            "plants_within_150_km": int(p_n[i]) if plants else None,
            "plant_mw_within_150_km": round(float(p_mw[i]), 1) if plants else None,
            "volcano_since_1990": (None if rv is None else
                                   {"name": rv["name"], "last_eruption_year": rv["last_eruption_year"],
                                    "km": round(rk, 1)}),
            "holocene_volcano": (None if hv is None else
                                 {"name": hv["name"], "last_eruption_year": hv["last_eruption_year"],
                                  "km": round(hk, 1)}),
        })
    return rows


# ==== per place ==================================================================================================

def solar_record(lat, lon, sun_by_box) -> dict:
    box = cloud.grid_box(lat, lon)
    row = sun_by_box.get(box)
    months = None if row is None or all(v is None for v in row[0]) else row[0]
    year = plain_mean(months)
    panel = None if months is None else [None if v is None else v * R["panel_factor"] for v in months]
    best = None
    if panel is not None and any(v is not None for v in panel):
        m = max((v, i) for i, v in enumerate(panel) if v is not None)[1]
        best = MONTH_NAMES[m]
    return {
        "sun_kwh_m2_day": None if months is None else [rnd(v, 2) for v in months],
        "sun_kwh_m2_day_year": rnd(year, 2),
        "months_without_sun": (None if months is None else
                               [MONTH_NAMES[i] for i, v in enumerate(months) if v is not None and v == R["sunless_value"]]),
        "panel_kwh_per_kw_day": None if panel is None else [rnd(v, 2) for v in panel],
        "panel_kwh_per_kw_day_year": rnd(None if year is None else year * R["panel_factor"], 2),
        "panel_best_month": best,
        "class": solar_class(year),
        "grid": [box[0], box[1]],
    }


def wind_record(lat, lon, ws50_by_point, ws10_year) -> dict:
    point = temperature.grid_point(lat, lon)
    row = ws50_by_point.get(point)
    months = None if row is None or all(v is None for v in row[0]) else row[0]
    year = plain_mean(months)
    height = None if row is None else row[2]
    density = air_density(height)
    power = None if year is None else wind_power(year, density)
    nrel, word = wind_classes(power)
    return {
        "ws50m_ms": None if months is None else [rnd(v, 2) for v in months],
        "ws50m_ms_year": rnd(year, 2),
        "ws10m_ms_year": rnd(ws10_year, 2),
        "grid_height_m": rnd(height, 0),
        "air_density_kg_m3": round(density, 3),
        "power_w_m2": rnd(power, 0),
        "class_1_to_7": nrel,
        "class": word,
        "grid": [point[0], point[1]],
    }


def low_sun_record(cell, cloud_row, clear_sky) -> dict:
    clear_by_bin = cloud.clear_share_by_bin(None if cloud_row is None else cloud_row.get("cloud_pct"))
    out = {}
    for region, figures in clear_sky.items():
        top = (cell.get("targets", {}).get(region) or {}).get("top_bins") or []
        pairs = [(clear_by_bin[int(b)], float(h)) for b, h in top if clear_by_bin[int(b)] is not None and h]
        share = sum(c * h for c, h in pairs) / sum(h for _, h in pairs) if pairs else None
        full, half = figures["at_ceiling_w_m2"], figures["at_half_ceiling_w_m2"]
        out[region] = {
            "clear_sky_w_m2": [round(full), round(half)],
            "best_bins": [int(b) for b, _ in top],
            "clear_share_best_bins": rnd(share, 3),
            "w_m2": None if share is None else [round(full * share), round(half * share)],
            "share_of_moon": None if share is None else [round(full * share / R["solar_constant"], 3),
                                                         round(half * share / R["solar_constant"], 3)],
        }
    return out


# ==== the Moon and Mars beside it ================================================================================

def _page_text(path: Path) -> str | None:
    if not path.exists():
        return None
    text = path.read_text(encoding="latin-1")
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text))


def _number(text: str | None, pattern: str) -> float | None:
    if text is None:
        return None
    match = re.search(pattern, text)
    return float(match.group(1).replace(",", "")) if match else None


def comparison(clear_sky: dict) -> tuple[list[dict], dict]:
    moon_text, mars_text, earth_text = _page_text(FACT_MOON), _page_text(FACT_MARS), _page_text(FACT_EARTH)
    moon_sun = _number(moon_text, r"Solar irradiance \(W/m 2 \) ([\d.]+)")
    moon_pressure = re.search(r"Surface pressure \(night\): ([^A]+?bar)", moon_text or "")
    moon_mass = _number(moon_text, r"Total mass of atmosphere: ~([\d,]+) kg")
    mars_rho = _number(mars_text, r"Surface density: ~([\d.]+)")
    earth_rho = _number(earth_text, r"Surface density: ([\d.]+)")
    mars_mw = _number(mars_text, r"Mean molecular weight: ([\d.]+)")
    mars_t = _number(mars_text, r"Average temperature: ~([\d.]+) K")
    mars_winds = re.search(r"Wind speeds: (.+?\(Viking Lander sites\))", mars_text or "")
    found = {str(p.relative_to(ROOT)): p.exists() for p in (FACT_MOON, FACT_MARS, FACT_EARTH, MOON_CARDS, MARS_SITES,
                                                             MARS_CLIMATE)}
    lines = []
    lines.append({"what": "solar on the Moon: a panel facing the Sun",
                  "number": moon_sun, "unit": "W per m2, at any Sun height above the local horizon (no air)",
                  "source": "NASA NSSDCA Moon Fact Sheet, 'Solar irradiance' (saved: data/raw/moon_provenance/"
                            "nssdc_moonfact.html)"})
    cards = json.loads(MOON_CARDS.read_text())["cards"] if MOON_CARDS.exists() else []
    for card in cards:
        region = card["id"]
        lit = card.get("lit") or {}
        best = clear_sky.get(region)
        lines.append({
            "what": f"solar on the Moon at {region}: full strength, but only for the share of time the Sun is up",
            "number": rnd(lit.get("mean_share"), 3), "best_point": rnd(lit.get("best_point_share"), 3),
            "unit": "share of time lit (mean over the region's box; its best 240 m point)",
            "earth_clear_air_at_this_ceiling_w_m2": None if best is None else round(best["at_ceiling_w_m2"]),
            "earth_share_of_moon_at_this_ceiling": None if best is None else round(best["share_of_moon"], 3),
            "source": "data/derived/moon_cards.json, cards[].lit (NASA Goddard average solar illumination map "
                      "AVGVISIB_65S_240M_201608, PGDA product 69: hourly steps over 18.6 years on LOLA terrain); the "
                      "Earth figure is this file's clear-air table at the region's Sun ceiling"})
    lines.append({"what": "wind on the Moon", "number": 0, "unit": "W per m2: no wind, no air to carry it",
                  "moon_surface_pressure": (re.sub(r"10 -(\d+)", r"10^-\1", moon_pressure.group(1).strip())
                                            if moon_pressure else None),
                  "moon_atmosphere_total_mass_kg": moon_mass,
                  "source": "NASA NSSDCA Moon Fact Sheet, 'Lunar Atmosphere' (saved: data/raw/moon_provenance/"
                            "nssdc_moonfact.html)"})
    mars_climate_sites = json.loads(MARS_CLIMATE.read_text())["sites"] if MARS_CLIMATE.exists() else []
    first = mars_climate_sites[0] if isinstance(mars_climate_sites, list) and mars_climate_sites else (
        next(iter(mars_climate_sites.values())) if isinstance(mars_climate_sites, dict) and mars_climate_sites else {})
    sunline = next((c for c in first.get("cannot_match", []) if c.get("what") == "sunlight at the top of the atmosphere"),
                   None)
    dust = next((c for c in first.get("cannot_match", []) if c.get("what") == "the dusty sky"), None)
    if sunline:
        lines.append({"what": "solar at Mars: sunlight above the air", "number": sunline.get("mars"), "unit": "W per m2",
                      "share_of_earth": sunline.get("number"), "range_over_the_mars_year": sunline.get("mars_range"),
                      "source": "data/derived/mars_climate.json, sites[].cannot_match 'sunlight at the top of the "
                                "atmosphere' (NASA NSSDCA Mars Fact Sheet)"})
    if dust:
        lines.append({"what": "solar at Mars: dust in the sky dims it", "number": dust.get("mars"),
                      "unit": dust.get("unit"), "note": dust.get("note"),
                      "source": "data/derived/mars_climate.json, sites[].cannot_match 'the dusty sky' "
                                "(Martinez et al. 2017, Space Science Reviews)"})
    sites = json.loads(MARS_SITES.read_text())["sites"] if MARS_SITES.exists() else []
    pressures = {s["id"]: (s.get("climate") or {}).get("pressure_pa") for s in sites}
    known = [p for p in pressures.values() if isinstance(p, (int, float))]
    lines.append({"what": "air pressure at the Mars sites", "number": [min(known), max(known)] if known else None,
                  "unit": "Pa (Earth at sea level: 101,325)", "by_site": pressures,
                  "source": "data/derived/mars_sites.json, sites[].climate.pressure_pa (Mars Climate Database v6.2, "
                            "model, yearly mean)"})
    ratio = None if mars_rho is None or earth_rho is None else mars_rho / earth_rho
    gas = None
    if known and mars_mw and mars_t:
        gas = [round(p * mars_mw / 1000.0 / (8.314462 * mars_t), 4) for p in (min(known), max(known))]
    lines.append({
        "what": "wind on Mars carries little power: the air is thin",
        "number": rnd(ratio, 4), "unit": "power at the same wind speed, Mars / Earth (= air density ratio)",
        "mars_air_density_kg_m3": mars_rho, "earth_air_density_kg_m3": earth_rho,
        "same_power_needs_wind_faster_by": None if ratio is None else round((1 / ratio) ** (1 / 3), 1),
        "example_10_m_s": (None if mars_rho is None else
                           {"mars_w_m2": round(wind_power(10.0, mars_rho)), "earth_sea_level_w_m2":
                            round(wind_power(10.0, R["air_density_sea"]))}),
        "cross_check_from_site_pressures_kg_m3": gas,
        "mars_wind_speeds": mars_winds.group(1) if mars_winds else None,
        "how": ("Air densities as the two NASA NSSDCA fact sheets give them (Mars 'Surface density ~0.016 +/- 0.006 "
                "kg/m3', Earth 'Surface density 1.217 kg/m3'; saved in data/raw/mars_climate/factsheets/). Power in "
                "the wind is proportional to air density at a given speed, so the ratio of the densities is the ratio "
                "of the power. Cross-check: density = pressure x molar mass / (gas constant x temperature), with the "
                "site pressures of mars_sites.json, the fact sheet's mean molecular weight 43.49 and average "
                "temperature 214 K."),
        "source": "NASA NSSDCA Mars and Earth Fact Sheets (saved); data/derived/mars_sites.json"})
    lines.append({"what": "geothermal on the Moon and Mars", "number": None, "unit": None,
                  "value": "not in our data", "source": None})
    return lines, found


def clear_sky_table(targets) -> dict:
    table = {}
    for target in targets:
        ceiling = float(target["limit_deg"])
        half = ceiling * R["half_ceiling"]
        full_w, half_w = clear_beam(ceiling), clear_beam(half)
        table[target["id"]] = {
            "name": target.get("name"), "ceiling_deg": ceiling, "half_ceiling_deg": round(half, 3),
            "air_mass_at_ceiling": round(air_mass(ceiling), 2), "air_mass_at_half": round(air_mass(half), 2),
            "at_ceiling_w_m2": round(full_w, 1), "at_half_ceiling_w_m2": round(half_w, 1),
            "share_of_moon": round(full_w / R["solar_constant"], 4),
            "share_of_moon_at_half": round(half_w / R["solar_constant"], 4),
            "moon_w_m2": R["solar_constant"],
        }
    return table


# ==== meta and checks ============================================================================================

def rules_in_words() -> list[str]:
    return [words for _value, _unit, words in RULES.values()]


def rules_table() -> dict:
    return {key: {"value": value, "unit": unit} for key, (value, unit, _words) in RULES.items()}


def class_counts(records, part: str) -> dict:
    counts = {}
    for rec in records:
        word = rec[part]["class"]
        key = "unknown" if word is None else word
        counts[key] = counts.get(key, 0) + 1
    return {k: counts.get(k, 0) for k in ("good", "fair", "poor", "unknown")}


def medians(records) -> dict:
    def med(values):
        values = [v for v in values if v is not None]
        return None if not values else round(statistics.median(values), 2)
    return {"sun_kwh_m2_day_year": med(r["solar"]["sun_kwh_m2_day_year"] for r in records),
            "ws50m_ms_year": med(r["wind"]["ws50m_ms_year"] for r in records),
            "power_w_m2": med(r["wind"]["power_w_m2"] for r in records),
            "nearest_geothermal_plant_km": med((r["geothermal"]["plant"] or {}).get("km") for r in records)}


WHAT = {
    "solar": ("Sunlight on level ground: NASA POWER ALLSKY_SFC_SW_DWN, all solar energy (direct plus diffuse) reaching "
              "a level surface per day under the real sky, monthly mean over the service's years, for the 1 degree "
              "box that holds the place (CERES SYN1deg). Yearly mean = plain mean of the 12 months. Panel yield and "
              "class by the rules above."),
    "solar_not": ("Not what a tilted or tracking panel would make, not a measurement at the place, and not the "
                  "light of the low-Sun hours only. A coarse box of about 111 km by 20 to 55 km at these latitudes."),
    "low_sun": ("Clear-air power on a panel facing a Sun at each lunar Sun ceiling and at half of it, from the air "
                "mass of Kasten and Young (1989) and the direct-beam formula of Meinel and Meinel (1976), then times "
                "the place's clear-sky share in its best low-Sun ten-day periods."),
    "low_sun_not": ("Not measured; diffuse light from the sky is left out; real polar air (haze, ice crystals, "
                    "aerosol) varies; cloud is a monthly mean over all hours and a box about 111 km tall, not over "
                    "the low-Sun hours. " + LOW_SUN_SENTENCE),
    "wind": ("Mean wind speed 50 m above the ground: NASA POWER WS50M (POWER from the MERRA-2 reanalysis), monthly "
             "mean over all hours, at the MERRA-2 grid point nearest the place (0.5 by 0.625 degrees). Power in the "
             "wind and class by the rules above. ws10m_ms_year is the 10 m speed of the power-extra group "
             "(WS10M), given for comparison."),
    "wind_not": ("A coarse grid mean (a box of about 55 km by 20 to 35 km here), not a measurement at the place: "
                 "local hills, coasts, valleys, ice slopes (katabatic winds) and icing of the blades change it "
                 "greatly. Not what a turbine would deliver."),
    "geothermal": ("A rule-of-thumb class from what is steadily there: working geothermal power plants (WRI Global "
                   "Power Plant Database) and volcanoes of the last 11,700 years and those that erupted since 1990 "
                   "(Smithsonian Global Volcanism Program). The figures behind it: nearest plant with name, size "
                   "and distance; plants and megawatts within 150 km; nearest volcano erupted since 1990; nearest "
                   "Holocene volcano."),
    "geothermal_not": ("Nobody has drilled or measured heat here: it only says that hot rock is likely to lie near "
                       "the surface. A place far from volcanoes can still have useful warm ground (deep basins, hot "
                       "springs) and a place by a volcano can be unusable. No open worldwide map of geothermal "
                       "potential could be fetched without a login tonight. The plant list stops in about 2021 and "
                       "misses some plants."),
}


def power_meta(header: dict | None, sun_heads: list[dict]) -> dict:
    head = header or {}
    sun = sun_heads[0] if sun_heads else {}
    return {
        "wind_parameter": WIND_PARAMETER, "sun_parameter": SUN_PARAMETER,
        "wind_answers": {k: head.get(k) for k in ("name", "version", "sources", "start", "end", "fill_value")},
        "sun_answers": {k: sun.get(k) for k in ("name", "version", "sources", "start", "end", "fill_value")},
        "url_pattern": cloud.URL_PATTERN,
        "credit": CREDIT_POWER.format(version=head.get("version") or sun.get("version"), date="15 November 2026 UTC"),
        "licence": ("NASA Earth science data carry no restriction on use unless marked; POWER asks for the credit "
                    "line above."),
    }


def gvp_citation() -> tuple[str | None, str | None]:
    """The GVP's own database citation, from a page another group saved (data/raw/gvp_eruptions/), if any."""
    for path in sorted(GVP_ERUPTIONS_OTHER.glob("*.html")) if GVP_ERUPTIONS_OTHER.is_dir() else []:
        text = _page_text(path) or ""
        match = re.search(r"(Global Volcanism Program, \d{4}\. \[Database\] Volcanoes of the World \(v\. [^)]+\)\. "
                          r"Distributed by Smithsonian Institution, compiled by [^.]+\. https://doi\.org/\S+)", text)
        if match:
            return match.group(1), str(path.relative_to(ROOT))
    return None, None


def sources_meta(plants_info, volcano_info) -> dict:
    gvp_note = None
    if GVP_VOLCANO_DOWNLOADS.exists():
        try:
            gvp_note = json.loads(GVP_VOLCANO_DOWNLOADS.read_text())
        except ValueError:
            gvp_note = None
    citation, citation_from = gvp_citation()
    return {
        "power_plants": {
            **plants_info,
            "what": "World Resources Institute, Global Power Plant Database: plants whose primary fuel is geothermal",
            "url": GPPD_BASE + GPPD_FILES["global_power_plant_database.csv"],
            "repository": "https://github.com/wri/global-power-plant-database",
            "licence": ("Creative Commons Attribution 4.0 International (CC BY 4.0), as the repository's README "
                        "states (saved: data/raw/power_plants/README.md); the README also says WRI no longer "
                        "maintains the project (early 2022) and that 1.3.0 is the last version"),
            "citation": ("Global Energy Observatory, Google, KTH Royal Institute of Technology in Stockholm, Enipedia, "
                         "World Resources Institute. Global Power Plant Database. Published on Resource Watch and "
                         "Google Earth Engine; http://resourcewatch.org/ https://earthengine.google.com/"),
            "kept": str(RAW_PLANTS.relative_to(ROOT)),
        },
        "volcanoes": {
            **volcano_info,
            "what": "Smithsonian Institution, Global Volcanism Program, Volcanoes of the World: Holocene volcanoes "
                    "(with last eruption year) and Holocene eruptions",
            "volcano_list_fetched_by_another_group": gvp_note,
            "service": GVP_WFS,
            "eruption_list_url": GVP_ERUPTIONS_URL,
            "terms": ("The service's own capabilities document (data/raw/gvp_volcanoes/wfs_capabilities_2.0.0.xml) "
                      "states Fees NONE and AccessConstraints NONE, provider 'Smithsonian Institution - Global "
                      "Volcanism Program'. The GVP pages link to the Smithsonian terms of use "
                      "(https://www.si.edu/termsofuse), which were not read in full tonight. Our own plain request "
                      "to https://volcano.si.edu/gvp_votw.cfm answered 403 (a bot check) and was not repeated; the "
                      "citation below is read from the copy another group saved."),
            "citation": citation or ("Global Volcanism Program, Smithsonian Institution. Volcanoes of the World "
                                     "(database), read through the GVP web services on 15 November 2026."),
            "citation_read_from": citation_from,
        },
    }


def cross_checks(moon, moon_records, mars, mars_records) -> dict:
    """Our figures against the same quantities other groups wrote from the same sources (read only)."""
    out = {}
    for path, places, records in ((ENV_MOON, moon, moon_records), (ENV_MARS, mars, mars_records)):
        key = f"sunlight_against_{path.name}"
        if not path.exists():
            out[key] = "file missing at build time"
            continue
        cells = json.loads(path.read_text())["cells"]
        compared = equal = 0
        largest = 0.0
        for place, rec in zip(places, records):
            theirs, mine = (cells.get(place["id"]) or {}).get("sun_kwh_m2_day"), rec["solar"]["sun_kwh_m2_day"]
            if not theirs or not mine:
                continue
            gaps = [abs(a - b) for a, b in zip(mine, theirs) if a is not None and b is not None]
            compared += 1
            gap = max(gaps) if gaps else 0.0
            equal += gap <= 0.006
            largest = max(largest, gap)
        out[key] = {"places_compared": compared, "all_months_within_0.006": equal, "largest_gap": round(largest, 4)}
    for path, places, records in ((STEADY, moon, moon_records), (MARS_STEADY, mars, mars_records)):
        key = f"volcano_distances_against_{path.name}"
        if not path.exists():
            out[key] = "file missing at build time"
            continue
        cells = json.loads(path.read_text())["cells"]
        compared = {"since_1990": [0, 0], "holocene": [0, 0]}
        for place, rec in zip(places, records):
            volcanic = (cells.get(place["id"]) or {}).get("volcanic") or {}
            for name, theirs_key, mine_key in (("since_1990", "nearest_erupted_since_1990", "volcano_since_1990"),
                                               ("holocene", "nearest_holocene", "holocene_volcano")):
                theirs = (volcanic.get(theirs_key) or {}).get("km")
                mine = (rec["geothermal"].get(mine_key) or {}).get("km")
                if theirs is None or mine is None:
                    continue
                compared[name][0] += 1
                compared[name][1] += abs(theirs - mine) <= 1.0
        out[key] = {name: {"places_compared": n, "within_1_km": k} for name, (n, k) in compared.items()}
    return out


def inputs_found() -> dict:
    paths = [MOON_PLACES, MARS_PLACES, CLOUD, POWER_EXTRA, MARS_POWER_EXTRA, ENV_MOON, ENV_MARS, STEADY, MARS_STEADY,
             GVP_VOLCANOES, GVP_ERUPTIONS_OTHER, MOON_CARDS, MARS_SITES, MARS_CLIMATE, FACT_MOON, FACT_MARS,
             FACT_EARTH, *SUN_RAW_DIRS, POWER_EXTRA_RAW]
    return {str(p.relative_to(ROOT)): ("found" if p.exists() else "missing") for p in paths}


REFERENCE_MOON = [("south-west Iceland", "63.8_-22.6", None, None), ("Haughton crater", "75.3_-90.0", None, None),
                  ("near Ulukhaktok", None, 70.736, -117.77), ("Pechora Sea coast", "68.9_54.3", None, None),
                  ("McMurdo Dry Valleys", "-77.6_161.5", None, None), ("Longyearbyen", "78.2_15.6", None, None)]
REFERENCE_MARS = [("Atacama near Yungay", None, -24.08, -70.01),
                  ("Atacama, the square inland of Yungay (next sunlight box east)", "m_-24.25_-69.75", None, None),
                  ("Tibetan Plateau", None, 33.0, 88.0),
                  ("south-west Iceland", None, 63.9, -22.4), ("Sahara (Hoggar)", None, 23.3, 5.6),
                  ("McMurdo Dry Valleys", None, -77.6, 161.5)]


NOTES = [
    ("Sunlight comes in 1 degree boxes. Yungay in the Atacama (square m_-24.25_-70.25) lies at the east edge of a "
     "box that reaches about 80 km out over the Pacific and its coastal cloud deck, so it reads 5.96 kWh per m2 per "
     "day; the next box inland (square m_-24.25_-69.75) reads 7.21, close to the highest in the file (7.38, on the "
     "Altiplano)."),
    ("The highest 50 m winds (yearly means of 17 to 19 m/s) are on the coastal slopes of East Antarctica, where the "
     "MERRA-2 model's katabatic winds run strong; the 10 m wind of the same model is nearly as high there. Model "
     "values, not checked against stations; blades there would also face extreme gusts and icing."),
    ("High ground has thin air: on the Tibetan Plateau (grid height about 5 km) the same mean wind carries about "
     "40 % less power than at sea level, a small step toward Mars, where it carries about 1 %."),
    ("Geothermal 'poor' does not mean no warm ground: Tibet has a working plant (Yangbajain) 400 km from our square "
     "and many hot springs without volcanoes, which this rule does not see."),
]


def reference(places, records, wanted, low_sun: bool) -> list[dict]:
    by_id = {p["id"]: i for i, p in enumerate(places)}
    lat = np.radians(np.array([p["lat"] for p in places]))
    lon = np.radians(np.array([p["lon"] for p in places]))
    out = []
    for name, key, plat, plon in wanted:
        if key is None or key not in by_id:
            if plat is None:
                out.append({"name": name, "id": key, "found": False})
                continue
            a = (np.sin((lat - math.radians(plat)) / 2) ** 2
                 + np.cos(lat) * math.cos(math.radians(plat)) * np.sin((lon - math.radians(plon)) / 2) ** 2)
            i = int(np.argmin(a))
        else:
            i = by_id[key]
        rec = records[i]
        entry = {"name": name, "id": places[i]["id"], "lat": places[i]["lat"], "lon": places[i]["lon"],
                 "solar": {k: rec["solar"][k] for k in ("sun_kwh_m2_day_year", "months_without_sun",
                                                        "panel_kwh_per_kw_day_year", "panel_best_month", "class")},
                 "sun_best_month_kwh_m2_day": (None if not rec["solar"]["sun_kwh_m2_day"] else
                                               max(v for v in rec["solar"]["sun_kwh_m2_day"] if v is not None)),
                 "wind": {k: rec["wind"][k] for k in ("ws50m_ms_year", "ws10m_ms_year", "air_density_kg_m3",
                                                      "power_w_m2", "class_1_to_7", "class")},
                 "geothermal": rec["geothermal"]}
        if low_sun:
            entry["low_sun"] = {r: {"clear_share_best_bins": v["clear_share_best_bins"], "w_m2": v["w_m2"]}
                                for r, v in rec["low_sun"].items()}
        out.append(entry)
    return out


# ==== build ======================================================================================================

def build() -> None:
    moon, mars = load_places()
    targets = json.loads(MOON_PLACES.read_text())["meta"]["targets"]
    clear_sky = clear_sky_table(targets)
    found = inputs_found()

    # sunlight (1 degree boxes): the environment groups' raw answers, ours only where theirs are missing
    sun_tiles = sorted(set(cloud.tiles_for(cloud.boxes_of(moon))) | set(cloud.tiles_for(cloud.boxes_of(mars))))
    sun_by_box, sun_missing, sun_heads = read_blocks(SUN_PARAMETER, sun_tiles, SUN_RAW_DIRS)
    sun_from = {}
    for tile in sun_tiles:
        path = sun_file(tile)
        if path is not None:
            key = str(path.parent.relative_to(ROOT))
            sun_from[key] = sun_from.get(key, 0) + 1

    # 50 m wind (MERRA-2 points): our own answers
    wind_tiles = sorted(set(temperature.tiles_for_cells(moon)) | set(temperature.tiles_for_cells(mars)))
    ws50_by_point, ws50_missing, ws50_heads = read_blocks(WIND_PARAMETER, wind_tiles, [RAW_WIND])

    # 10 m wind: the power-extra group's file for the Moon areas; for Mars their file, or else their raw answers
    ws10_moon = {}
    if POWER_EXTRA.exists():
        ws10_moon = {k: v.get("wind_10m_ms_year") for k, v in json.loads(POWER_EXTRA.read_text())["cells"].items()}
    ws10_mars, ws10_mars_from = {}, None
    if MARS_POWER_EXTRA.exists():
        ws10_mars = {k: v.get("wind_10m_ms_year") for k, v in json.loads(MARS_POWER_EXTRA.read_text())["cells"].items()}
        ws10_mars_from = str(MARS_POWER_EXTRA.relative_to(ROOT))
    else:
        tiles = temperature.tiles_for_cells(mars)
        points, missing10, _ = read_blocks("WS10M", tiles, [POWER_EXTRA_RAW])
        for p in mars:
            row = points.get(temperature.grid_point(p["lat"], p["lon"]))
            ws10_mars[p["id"]] = None if row is None else row[1]
        ws10_mars_from = (f"{POWER_EXTRA_RAW.relative_to(ROOT)} (raw WS10M answers, the service's annual value; "
                          f"{len(tiles) - len(missing10)} of {len(tiles)} blocks on disk at build time)")

    cloud_cells = json.loads(CLOUD.read_text())["cells"] if CLOUD.exists() else {}
    plants, plants_info = read_plants()
    volcanoes, volcano_info = read_volcanoes()
    lines, fact_found = comparison(clear_sky)

    moon_geo = geothermal_table(moon, plants, volcanoes)
    mars_geo = geothermal_table(mars, plants, volcanoes)

    moon_records = []
    for cell, geo in zip(moon, moon_geo):
        moon_records.append({
            "solar": solar_record(cell["lat"], cell["lon"], sun_by_box),
            "low_sun": low_sun_record(cell, cloud_cells.get(cell["id"]), clear_sky),
            "wind": wind_record(cell["lat"], cell["lon"], ws50_by_point, ws10_moon.get(cell["id"])),
            "geothermal": geo,
        })
    mars_records = []
    for square, geo in zip(mars, mars_geo):
        mars_records.append({
            "solar": solar_record(square["lat"], square["lon"], sun_by_box),
            "wind": wind_record(square["lat"], square["lon"], ws50_by_point, ws10_mars.get(square["id"])),
            "geothermal": geo,
        })

    common = {
        "what": ("Power on site: how well solar, wind and geothermal power would do at each place, with the Moon "
                 "and Mars beside it."),
        "rough_estimate": ROUGH,
        "rules_in_words": rules_in_words(),
        "rules": rules_table(),
        "classes": "each part has a class in plain words (good, fair, poor; null where its inputs are unknown) and "
                   "the figures behind it",
        "null_rule": "Unknown is null, never 0. A real 0.0 (a month of polar night) stays 0.0.",
        "what_it_is": {k: v for k, v in WHAT.items() if not k.endswith("_not")},
        "what_it_is_not": {k[:-4]: v for k, v in WHAT.items() if k.endswith("_not")},
        "clear_sky_low_sun_table": clear_sky,
        "low_sun_sentence": LOW_SUN_SENTENCE,
        "moon_and_mars": lines,
        "notes_from_the_sanity_look": NOTES,
        "inputs": found,
        "fact_sheets_found": fact_found,
        "cross_checks": cross_checks(moon, moon_records, mars, mars_records),
        "sunlight_answers_read_from": sun_from,
        "sunlight_blocks_missing": sun_missing,
        "wind_50m_blocks_missing": ws50_missing,
        "nasa_power": power_meta(ws50_heads[0] if ws50_heads else None, sun_heads),
        "sources": sources_meta(plants_info, volcano_info),
        "enters_score": False,
        "written": now_utc(),
        "written_by": "agent POWER, scripts/build_power_cells.py build",
        "how_to_rerun": ("uv run python scripts/build_power_cells.py fetch-sources; uv run python "
                         "scripts/build_power_cells.py fetch-power; uv run python scripts/build_power_cells.py build"),
    }

    moon_meta = {**common,
                 "places": "the Moon part's areas, data/derived/grazing_cells.json (about 11 km, poleward of 59 degrees)",
                 "fields": {
                     "solar": "sun_kwh_m2_day (12 months, Jan first), sun_kwh_m2_day_year, months_without_sun, "
                              "panel_kwh_per_kw_day (12), panel_kwh_per_kw_day_year, panel_best_month, class, grid "
                              "(1 degree box centre)",
                     "low_sun": "by lunar region: clear_sky_w_m2 [at the ceiling, at half], best_bins (ten-day "
                                "periods 0-35 from grazing_cells.json top_bins), clear_share_best_bins, w_m2 [at "
                                "the ceiling, at half] = clear-sky x clear share, share_of_moon [same / 1361]",
                     "wind": "ws50m_ms (12), ws50m_ms_year, ws10m_ms_year (power-extra group), grid_height_m, "
                             "air_density_kg_m3, power_w_m2, class_1_to_7, class, grid (MERRA-2 point)",
                     "geothermal": "class, plant {name, country, mw, km}, plants_within_150_km, "
                                   "plant_mw_within_150_km, volcano_since_1990 {name, last_eruption_year, km}, "
                                   "holocene_volcano {name, last_eruption_year, km}"},
                 "ws10m_from": str(POWER_EXTRA.relative_to(ROOT)) if POWER_EXTRA.exists() else None,
                 "counts": {"places": len(moon), "solar": class_counts(moon_records, "solar"),
                            "wind": class_counts(moon_records, "wind"),
                            "geothermal": class_counts(moon_records, "geothermal"),
                            "low_sun_known": {r: sum(rec["low_sun"][r]["w_m2"] is not None for rec in moon_records)
                                              for r in clear_sky}},
                 "medians": medians(moon_records),
                 "reference_places": reference(moon, moon_records, REFERENCE_MOON, True)}
    mars_meta = {**common,
                 "places": "the Mars part's half-degree squares, data/derived/mars_cells.json (worldwide)",
                 "parts": "solar (1a), wind and geothermal only; the lunar low-Sun part is for the Moon areas",
                 "fields": {k: v for k, v in moon_meta["fields"].items() if k != "low_sun"},
                 "ws10m_from": ws10_mars_from,
                 "counts": {"places": len(mars), "solar": class_counts(mars_records, "solar"),
                            "wind": class_counts(mars_records, "wind"),
                            "geothermal": class_counts(mars_records, "geothermal")},
                 "medians": medians(mars_records),
                 "reference_places": reference(mars, mars_records, REFERENCE_MARS, False)}
    mars_meta.pop("clear_sky_low_sun_table", None)
    mars_meta["clear_sky_low_sun_table_in"] = "data/derived/power_cells.json meta"

    write_json(OUT_MOON, {"meta": moon_meta, "cells": {c["id"]: r for c, r in zip(moon, moon_records)}})
    write_json(OUT_MARS, {"meta": mars_meta, "cells": {s["id"]: r for s, r in zip(mars, mars_records)}})
    for path, meta in ((OUT_MOON, moon_meta), (OUT_MARS, mars_meta)):
        print(f"wrote {path.relative_to(ROOT)} ({path.stat().st_size / 1e6:.1f} MB): {json.dumps(meta['counts'])}")
    print("missing blocks: sunlight", len(sun_missing), "wind 50 m", len(ws50_missing))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="step", required=True)
    sub.add_parser("fetch-sources")
    fp = sub.add_parser("fetch-power")
    fp.add_argument("--only", choices=("moon", "mars"))
    sub.add_parser("build")
    sub.add_parser("table", help="print the clear-air low-Sun table")
    args = parser.parse_args()
    os.chdir(ROOT)
    if args.step == "fetch-sources":
        fetch_sources()
    elif args.step == "fetch-power":
        fetch_power(args.only)
    elif args.step == "table":
        targets = json.loads(MOON_PLACES.read_text())["meta"]["targets"]
        print(json.dumps(clear_sky_table(targets), indent=1))
    else:
        build()


if __name__ == "__main__":
    main()

# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""UV, surface sunlight, clear-sky days and aerosol for every area, from the NASA POWER climatology service.

Eight monthly climatology parameters, all served on the 1 degree grid of CERES SYN1deg
(checked on every answer by `answer_grid`), for the grid box that holds the area centre:

- ALLSKY_SFC_UV_INDEX  UV index at the ground under the real sky (unit "W m-2 x 40");
- ALLSKY_SFC_UVA, ALLSKY_SFC_UVB  UVA (315-400 nm) and UVB (280-315 nm) at the ground, in
  kWh per square metre per day (the service's unit; not W per square metre);
- ALLSKY_SFC_SW_DWN, CLRSKY_SFC_SW_DWN  all solar energy reaching a level surface per day,
  under the real sky and as if the sky were clear, kWh per square metre per day;
- ALLSKY_KT  the share of the sunlight at the top of the air that reaches the ground;
- CLRSKY_DAYS  days whose daytime cloud amount is under 10 percent (the service's rule), counted
  over all the years of the period for each calendar month (values reach 355 in a January), so
  `clear_days_per_year` divides by the number of years before it is shown as days a month;
- AOD_55_ADJ  aerosol optical depth at 550 nm: all fine particles in the air column together.

The parameter names, definitions and units were read from the service's own parameter list
(api/system/manager/parameters, community RE, climatology) on 14 November 2026; no dust-only
parameter is in that list. Months without sunlight (polar night, `sunless_months`): the service
gives a real 0.0 for UV and sunlight and mostly the fill value (null here) for the clearness
index, but it still counts clear days there by its cloud rule; the build script counts what it
gives in those months (meta.polar_night).

These are monthly means for a box about 111 km tall, from satellite-based and model data. The
answers name 2001 to 2025, but at three boxes checked the values equal the 2001-2020 means of the
service's own daily series (meta.checks.period), as the project's temperature check found for
MERRA-2; `monthly_climatology` is the helper of that check. Nothing here
enters a score. Service rules as in twinfinder/cloud.py: one parameter and at most 10 x 10
degrees a regional request, one request at a time with a pause, no key, no login.
"""
from __future__ import annotations

import json
import math
import re
import statistics
import time
from pathlib import Path

from twinfinder import cloud, temperature

USER_AGENT = cloud.USER_AGENT
URL_PATTERN = cloud.URL_PATTERN
DAILY_URL_PATTERN = (
    "https://power.larc.nasa.gov/api/temporal/daily/point"
    "?parameters={parameters}&community=RE&longitude={lon}&latitude={lat}&start={start}&end={end}&format=JSON"
)
HOURLY_URL_PATTERN = (
    "https://power.larc.nasa.gov/api/temporal/hourly/point"
    "?parameters={parameters}&community=RE&longitude={lon}&latitude={lat}&start={start}&end={end}"
    "&time-standard=LST&format=JSON"
)
MANAGER_URL = "https://power.larc.nasa.gov/api/system/manager/parameters?community=RE&temporal=climatology"

FIELDS = {
    "uv_index": "ALLSKY_SFC_UV_INDEX",
    "uva_kwh_m2_day": "ALLSKY_SFC_UVA",
    "uvb_kwh_m2_day": "ALLSKY_SFC_UVB",
    "sun_kwh_m2_day": "ALLSKY_SFC_SW_DWN",
    "sun_clear_kwh_m2_day": "CLRSKY_SFC_SW_DWN",
    "clearness": "ALLSKY_KT",
    "clear_days_total": "CLRSKY_DAYS",
    "aod_550": "AOD_55_ADJ",
}
PARAMETERS = tuple(FIELDS.values())
MONTHS = cloud.MONTHS
N_BINS = cloud.N_BINS
FILL_VALUE = -999.0
GRID_DEG = {parameter: 1.0 for parameter in PARAMETERS}   # every one is a CERES SYN1deg parameter
# Outside these a value is not the quantity on Earth (top-of-air sunlight at a pole at midsummer
# is about 12.6 kWh/m2/day; CLRSKY_DAYS is a count over the years: at most 31 days x 25 years).
RANGES = {
    "ALLSKY_SFC_UV_INDEX": (0.0, 30.0),
    "ALLSKY_SFC_UVA": (0.0, 3.0),
    "ALLSKY_SFC_UVB": (0.0, 0.2),
    "ALLSKY_SFC_SW_DWN": (0.0, 13.0),
    "CLRSKY_SFC_SW_DWN": (0.0, 13.0),
    "ALLSKY_KT": (0.0, 1.0),
    "CLRSKY_DAYS": (0.0, 31.0 * 25),
    "AOD_55_ADJ": (0.0, 6.0),
}

ABOUT = {   # every sentence 25 words or fewer (tests/test_environment.py)
    "ALLSKY_SFC_UV_INDEX": {
        "field": "uv_index", "group": "UV exposure",
        "what_it_is": ("The UV index at the ground under the real sky, cloudy or clear, as a monthly mean. "
                       "It is UV light weighted by how strongly it burns skin, in W per square metre, times 40."),
        "what_it_is_not": ("Not the noon or peak UV index that weather services publish. "
                           "The service's daily value is the mean of all 24 hours (meta.checks.uv_index_daily_value). "
                           "At two boxes over ten summer days it equalled the hourly mean within 0.003. "
                           "There the brightest hour was 2.3 to 2.4 times larger. "
                           "Not a value at one spot: a box about 111 km tall. "
                           "Not UV on the Moon, which has no air and no ozone to filter it."),
    },
    "ALLSKY_SFC_UVA": {
        "field": "uva_kwh_m2_day", "group": "UV exposure",
        "what_it_is": "Energy of UVA light (315 to 400 nm) reaching the ground per day under the real sky, monthly mean.",
        "what_it_is_not": ("Not in W per square metre: the service gives kWh per square metre per day. "
                           "Divide by 24 and multiply by 1000 for the 24-hour mean in W per square metre. "
                           "Not weighted for harm to skin or materials."),
    },
    "ALLSKY_SFC_UVB": {
        "field": "uvb_kwh_m2_day", "group": "UV exposure",
        "what_it_is": "Energy of UVB light (280 to 315 nm) reaching the ground per day under the real sky, monthly mean.",
        "what_it_is_not": ("Not in W per square metre: the service's unit is kWh per square metre per day. "
                           "Not UVC: the air stops all UVC, which reaches the lunar surface unfiltered."),
    },
    "ALLSKY_SFC_SW_DWN": {
        "field": "sun_kwh_m2_day", "group": "surface sunlight",
        "what_it_is": ("All solar energy, direct plus diffuse, reaching a level surface per day under the real sky. "
                       "A monthly mean: the global horizontal irradiance."),
        "what_it_is_not": ("Not what a tilted or Sun-tracking panel would get. "
                           "With the Sun low, a vertical panel facing it gets much more than a level one. "
                           "Not a panel's output, and not the light of the low-Sun hours only: it is the whole day's total."),
    },
    "CLRSKY_SFC_SW_DWN": {
        "field": "sun_clear_kwh_m2_day", "group": "surface sunlight",
        "what_it_is": ("The same solar energy on a level surface per day as if there were no cloud, monthly mean. "
                       "The air and its aerosol stay in place."),
        "what_it_is_not": "Not a measurement on clear days: it is a computed clear-sky value for every day.",
    },
    "ALLSKY_KT": {
        "field": "clearness", "group": "surface sunlight",
        "what_it_is": ("Clearness index, 0 to 1, monthly mean. "
                       "It is the share of the sunlight arriving at the top of the air that reaches level ground."),
        "what_it_is_not": ("Not the share of clear sky and not a count of clear days. "
                           "Null (the service's fill value) in most months without sunlight, where it has no meaning."),
    },
    "CLRSKY_DAYS": {
        "field": "clear_days_total", "group": "cloud-free days",
        "what_it_is": ("The service's count of days whose daytime cloud over the grid box is under 10 percent. "
                       "It is added up over all the years, so it reaches 355 in one January. "
                       "The field clear_days divides it by the years that checks.period found it covers."),
        "what_it_is_not": ("Not days in a typical month until divided by the years, as clear_days does. "
                           "Not the hours a camera can see the Sun or the ground. "
                           "A day with 15 percent cloud counts as not clear; a clear spell of a few hours is not counted. "
                           "In months without sunlight the service still counts clear days by its cloud rule. "
                           "A count there says nothing about seeing by sunlight. "
                           "A box about 111 km tall is under 10 percent cloud on fewer days than one spot in it."),
    },
    "AOD_55_ADJ": {
        "field": "aod_550", "group": "haze (asked for as 'dust conditions')",
        "what_it_is": ("Aerosol optical depth at 550 nm, monthly mean, as the service adjusts it. "
                       "It says how much fine particles in the whole air column dim a vertical beam of green light. "
                       "A value of 0.1 dims it by about 10 percent."),
        "what_it_is_not": ("Not dust alone: all fine particles together, such as mineral dust, smoke, sea salt and sulphate haze. "
                           "Not dust on the ground, not blowing grit, and nothing like lunar regolith dust. "
                           "The service's climatology list holds no dust-only figure. "
                           "It is served to two decimals, so 0.0 means under 0.005, not an empty sky. "
                           "In months without sunlight the service still gives a number; how it makes it then was not checked."),
    },
}


# ---- words ------------------------------------------------------------------------------------

MAX_WORDS = 25
# keys whose text is not ours to shorten: the service's own words, sources and places on disk or the web
QUOTED_KEYS = {"definition_in_the_service", "name_in_the_service", "messages", "source", "source_in_the_list",
               "url", "url_pattern", "monthly_url_pattern", "file", "folder", "log", "probe_log", "moon_file",
               "how_to_read", "figures"}


def long_sentences(node, limit: int = MAX_WORDS, path: str = ""):
    """(path, sentence) for every sentence of more than `limit` words in the strings of a JSON-like value.

    Text under QUOTED_KEYS (the service's own words, citations, files and URLs) is not checked.
    """
    if isinstance(node, dict):
        for key, value in node.items():
            if key not in QUOTED_KEYS:
                yield from long_sentences(value, limit, f"{path}.{key}")
    elif isinstance(node, (list, tuple)):
        for n, value in enumerate(node):
            yield from long_sentences(value, limit, f"{path}[{n}]")
    elif isinstance(node, str):
        for sentence in re.split(r"(?<=[.!?])\s+", node):
            if len(sentence.split()) > limit:
                yield path, sentence


# ---- reading a raw answer ---------------------------------------------------------------------

def _parsed(raw) -> dict:
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8")
    data = json.loads(raw) if isinstance(raw, str) else raw
    if not isinstance(data, dict) or not isinstance(data.get("header"), dict):
        messages = data.get("messages") if isinstance(data, dict) else None
        raise ValueError(f"not an answer of the service: {messages!r}")
    return data


def _fills(data: dict) -> set[float]:
    fills = {FILL_VALUE}
    value = data["header"].get("fill_value")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        fills.add(float(value))
    return fills


def _value(value, parameter: str, fills: set[float], where: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{parameter} {where} is not a number: {value!r}")
    value = float(value)
    if value in fills or math.isnan(value):
        return None
    low, high = RANGES[parameter]
    if not low <= value <= high:
        raise ValueError(f"{parameter} {where} is out of range {low} to {high}: {value}")
    return value


def read_answer(raw, parameter: str) -> dict[tuple[float, float], list[float | None]]:
    """Monthly values by grid box from one regional answer: {(lat, lon): [12 values, January first]}.

    The service's fill value becomes None, never a number; a real 0.0 (polar night) stays 0.0.
    A value outside what the quantity can take, an answer without grid boxes (an error
    message) or an answer for another parameter is an error.
    """
    data = _parsed(raw)
    fills = _fills(data)
    features = data.get("features")
    if not isinstance(features, list) or not features:
        raise ValueError(f"not a regional climatology answer: {data.get('messages')!r}")
    out: dict[tuple[float, float], list[float | None]] = {}
    for feature in features:
        try:
            coordinates = feature["geometry"]["coordinates"]          # GeoJSON: longitude first
            lon, lat = float(coordinates[0]), float(coordinates[1])
            months = feature["properties"]["parameter"][parameter]
            values = [_value(months.get(name), parameter, fills, f"{name} at {lat}, {lon}") for name in MONTHS]
        except (KeyError, TypeError, IndexError, AttributeError) as error:
            raise ValueError(f"answer does not hold {parameter} by grid box: {error!r}") from error
        if lon >= 180.0:
            lon -= 360.0
        out[(lat, lon)] = values
    return out


def answer_units(raw, parameter: str) -> str | None:
    """The unit the answer names for the parameter, or None if it names none."""
    entry = (_parsed(raw).get("parameters") or {}).get(parameter) or {}
    return entry.get("units")


def answer_grid(raw) -> tuple[float, float]:
    """(latitude step, longitude step) in degrees of the grid an answer is on, from its grid boxes."""
    data = _parsed(raw)
    lats = sorted({round(float(f["geometry"]["coordinates"][1]), 6) for f in data.get("features") or []})
    lons = sorted({round(float(f["geometry"]["coordinates"][0]), 6) for f in data.get("features") or []})

    def step(values):
        gaps = {round(b - a, 6) for a, b in zip(values, values[1:])}
        return min(gaps) if gaps else None

    return step(lats), step(lons)


# ---- grid boxes, ten-day values, polar night ----------------------------------------------------

def grid_box(lat: float, lon: float, parameter: str) -> tuple[float, float]:
    """Centre of the grid box of `parameter` that holds a point. All eight are on 1 degree boxes."""
    if GRID_DEG[parameter] != 1.0:
        raise NotImplementedError(f"{parameter} is on a {GRID_DEG[parameter]} degree grid")
    return cloud.grid_box(lat, lon)


def ten_day_values(months) -> list[float | None]:
    """12 monthly values (January first) as 36 ten-day values, by the project's rule.

    Ten-day period = min((day_of_year - 1) // 10, 35); each period takes the month of its
    middle day. Null stays null and 0.0 stays 0.0.
    """
    return temperature.by_bin(months)


def sunless_months(clear_sun) -> list[int] | None:
    """Months (1 = January) in which no sunlight reaches a level surface even under a clear sky.

    clear_sun is the 12 monthly CLRSKY_SFC_SW_DWN values of a box; a month counts when its
    value is exactly 0.0 as served (polar night). A null month is unknown and not listed;
    a null row gives None.
    """
    if clear_sun is None:
        return None
    return [m + 1 for m, value in enumerate(clear_sun) if value is not None and value == 0.0]


# ---- fetching -----------------------------------------------------------------------------------

def fetch_tile(parameter: str, tile: tuple[int, int, int, int], raw_dir: Path, opener=None,
               sleep=time.sleep, attempts: int = 5, timeout: float = 120.0) -> tuple[Path, bool]:
    """The raw regional answer for one parameter and 10 degree block, kept as <parameter>_<block>.json.

    Asks only if the file is not on disk (returns (path, asked)); waits and tries again on 429
    and 5xx; keeps nothing that is not an answer for the parameter.
    """
    dest = Path(raw_dir) / cloud.raw_name(parameter, tile)
    return temperature._fetch(cloud.regional_url(parameter, tile), dest, lambda body: read_answer(body, parameter),
                              opener=opener, sleep=sleep, attempts=attempts, timeout=timeout)


def read_raw(raw_dir: Path, parameter: str, tiles) -> dict[tuple[float, float], list[float | None]]:
    """All grid boxes of a parameter from the raw answers on disk. A missing file is an error."""
    by_box: dict[tuple[float, float], list[float | None]] = {}
    for tile in tiles:
        by_box.update(read_answer((Path(raw_dir) / cloud.raw_name(parameter, tile)).read_bytes(), parameter))
    return by_box


# ---- the table of cells -------------------------------------------------------------------------

def _row_or_null(values) -> list[float | None] | None:
    if values is None or all(value is None for value in values):
        return None
    return list(values)


def clear_days_per_year(total, years: int | None) -> list[float | None] | None:
    """The service's clear-sky day counts (added up over the years) as days in a typical month.

    None when the row is null or the number of years is not known: never a guess, never 0.
    """
    if total is None or not years:
        return None
    return [None if value is None else round(value / years, 2) for value in total]


def cells_table(cells, by_parameter: dict, clear_day_years: int | None = None) -> dict:
    """The "cells" block of environment_cells.json.

    by_parameter maps each parameter name to its rows by grid box. Each cell gets one row of
    12 monthly values per field (null when the box has no value at all or the service gave
    no such box), "clear_days" (clear_days_total over clear_day_years, null when that number
    is not known), its box as {"lat", "lon", "deg"} and its sunless months.
    """
    table = {}
    for cell in cells:
        box = grid_box(cell["lat"], cell["lon"], PARAMETERS[0])
        record: dict = {}
        for field, parameter in FIELDS.items():
            if grid_box(cell["lat"], cell["lon"], parameter) != box:
                raise ValueError(f"{parameter} is on another grid than {PARAMETERS[0]}")
            record[field] = _row_or_null(by_parameter.get(parameter, {}).get(box))
        record["clear_days"] = clear_days_per_year(record["clear_days_total"], clear_day_years)
        record["grid"] = {"lat": box[0], "lon": box[1], "deg": GRID_DEG[PARAMETERS[0]]}
        record["sunless_months"] = sunless_months(record["sun_clear_kwh_m2_day"])
        table[cell["id"]] = record
    return table


# ---- daily and hourly series at a point (checks) -------------------------------------------------

def daily_url(lat: float, lon: float, start: str, end: str, parameters=PARAMETERS) -> str:
    return DAILY_URL_PATTERN.format(parameters=",".join(parameters), lat=lat, lon=lon, start=start, end=end)


def hourly_url(lat: float, lon: float, start: str, end: str, parameters=("ALLSKY_SFC_UV_INDEX",)) -> str:
    return HOURLY_URL_PATTERN.format(parameters=",".join(parameters), lat=lat, lon=lon, start=start, end=end)


def read_series(raw, parameter: str) -> dict[str, float | None]:
    """One parameter of a daily or hourly point answer: {"YYYYMMDD" or "YYYYMMDDHH": value}, fill as None."""
    data = _parsed(raw)
    fills = _fills(data)
    try:
        days = data["properties"]["parameter"][parameter]
        return {key: _value(value, parameter, fills, f"on {key}") for key, value in days.items()}
    except (KeyError, TypeError, AttributeError) as error:
        raise ValueError(f"answer does not hold the series of {parameter}: {error!r}") from error


def hours_to_days(series: dict) -> dict[str, dict]:
    """Mean and highest of the known hours of each day of an hourly series, and how many hours were known."""
    by_day: dict[str, list[float]] = {}
    for key, value in series.items():
        by_day.setdefault(key[:8], [])
        if value is not None:
            by_day[key[:8]].append(value)
    return {day: {"mean": statistics.fmean(v) if v else None, "max": max(v) if v else None, "hours": len(v)}
            for day, v in sorted(by_day.items())}


def monthly_climatology(series: dict, first_year: int, last_year: int, how: str = "mean") -> list[float | None]:
    """A daily series as 12 calendar-month figures over the years first_year to last_year.

    how="mean": the mean of all known days of that calendar month in those years.
    how="sum": the sum of the known days of the month in each year (a count, for clear days),
    averaged over the years that have at least one known day in that month.
    how="total": the sum of all known days of the month over all those years.
    A month with no known day is None, never 0.
    """
    if how not in ("mean", "sum", "total"):
        raise ValueError(how)
    days: list[list[float]] = [[] for _ in range(12)]
    sums: list[dict[int, float]] = [{} for _ in range(12)]
    for key, value in series.items():
        year, month = int(key[0:4]), int(key[4:6])
        if value is None or not first_year <= year <= last_year:
            continue
        days[month - 1].append(value)
        sums[month - 1][year] = sums[month - 1].get(year, 0.0) + value
    if how == "mean":
        return [statistics.fmean(v) if v else None for v in days]
    if how == "total":
        return [sum(v) if v else None for v in days]
    return [statistics.fmean(s.values()) if s else None for s in sums]

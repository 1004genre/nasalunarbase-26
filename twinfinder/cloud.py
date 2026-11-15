# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Typical cloud for every cell, from the NASA POWER climatology service.

What the number is: the monthly mean share of the sky covered by cloud, in
percent, averaged over all hours of the day and over the years the service
names (January 2001 to December 2025 when this was written), for the 1 degree
grid box that holds the cell centre. The data behind it is CERES SYN1deg.

What it is not: the chance that a Sun a few degrees above the horizon can be
seen. It enters no score; it is a displayed column only.

Service rules that this module follows (read from the POWER documentation and
from the service's own error messages on 14 November 2026):
- a regional request takes one parameter and a box of 2 to 10 degrees a side;
- no key and no login; at most five requests at once (one at a time here);
- answer 429 means too many requests: wait and try again;
- the fill value for "no data" is named in the answer's header (-999).
"""
from __future__ import annotations

import http.client
import json
import math
import time
import urllib.error
import urllib.request
from pathlib import Path

USER_AGENT = "twinfinder/0.1"
PARAMETERS = ("CLOUD_AMT", "CLOUD_AMT_DAY", "CLOUD_AMT_NIGHT")  # all hours, daylight hours, night hours
URL_PATTERN = (
    "https://power.larc.nasa.gov/api/temporal/climatology/regional"
    "?latitude-min={lat_min}&latitude-max={lat_max}&longitude-min={lon_min}&longitude-max={lon_max}"
    "&parameters={parameter}&community=RE&format=JSON"
)
MONTHS = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")
MONTH_DAYS = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
GRID_DEG = 1.0   # the grid the service answers on
TILE_DEG = 10    # the largest box a regional request may ask for
FILL_VALUE = -999.0
BIN_DAYS = 10
N_BINS = 36
WAIT_429_S = 10.0
EDGE = 1e-9      # a centre that should sit on a box edge but carries rounding noise goes to the box above

WHAT_IT_IS = (
    "Monthly mean share of the sky covered by cloud, in percent, averaged over all hours of the "
    "day and night and over the years of the period, for the 1 degree grid box that holds the "
    "cell centre (CERES SYN1deg cloud amount as served by NASA POWER). Many cells share one box."
)
WHAT_IT_IS_NOT = (
    "Not the chance that a low Sun is visible. A Sun a few degrees above the horizon shines "
    "through a long slanted path, so the same share of cloud hides it more often than it hides a "
    "high Sun. The figure is a mean over the whole day and over a box about 111 km tall, not over "
    "the hours of low Sun at the cell, and it says nothing about fog or local weather. It enters "
    "no score."
)


# ---- ten-day bins ------------------------------------------------------------------------------

def bin_index(day_of_year: int) -> int:
    """Ten-day bin of a day of year (1 to 366): the project's bin rule, as in sun.bin_index."""
    return min((day_of_year - 1) // BIN_DAYS, N_BINS - 1)


def month_of_day(day_of_year: int) -> int:
    """Month (0 = January) of a day of a 365-day year; day 366 is December."""
    left = day_of_year
    for month, days in enumerate(MONTH_DAYS):
        if left <= days:
            return month
        left -= days
    return 11


def _bin_months() -> tuple[int, ...]:
    months = []
    for b in range(N_BINS):
        days = [d for d in range(1, 366) if bin_index(d) == b]
        months.append(month_of_day(days[len(days) // 2]))
    return tuple(months)


BIN_MONTH = _bin_months()  # month (0 = January) of the middle day of each bin; it comes to bin // 3


def clear_share_by_bin(cloud_pct) -> list[float | None]:
    """Share of the sky that is clear in each of the 36 ten-day bins: 1 - cloud percent / 100.

    cloud_pct is 12 monthly means, January first. Each bin takes the month of its
    middle day. Null in, null out: None (or NaN) for a month gives None for its
    three bins, and None for the whole list gives 36 times None. Never 0 for unknown.
    """
    if cloud_pct is None:
        return [None] * N_BINS
    values = list(cloud_pct)
    if len(values) != 12:
        raise ValueError(f"cloud_pct must hold 12 months, got {len(values)}")
    by_month: list[float | None] = []
    for value in values:
        if value is None or math.isnan(float(value)):
            by_month.append(None)
            continue
        value = float(value)
        if not 0.0 <= value <= 100.0:
            raise ValueError(f"cloud percent out of range: {value}")
        by_month.append(round(1.0 - value / 100.0, 6))
    return [by_month[month] for month in BIN_MONTH]


# ---- grid boxes and request tiles ---------------------------------------------------------------

def grid_box(lat: float, lon: float) -> tuple[float, float]:
    """Centre (lat, lon) of the 1 degree grid box that holds a point, such as (63.5, -22.5)."""
    if lon >= 180.0 or lon < -180.0:
        lon = (lon + 180.0) % 360.0 - 180.0
    lat0 = min(max(math.floor(lat + EDGE), -90), 89)
    lon0 = math.floor(lon + EDGE)
    if lon0 >= 180:
        lon0 -= 360
    return lat0 + 0.5, lon0 + 0.5


def boxes_of(cells) -> list[tuple[float, float]]:
    """Every grid box that holds at least one cell centre, each once, sorted."""
    return sorted({grid_box(cell["lat"], cell["lon"]) for cell in cells})


def tile_of(box: tuple[float, float]) -> tuple[int, int, int, int]:
    """The 10 degree block (lat_min, lat_max, lon_min, lon_max) that holds a grid box."""
    lat0 = math.floor(box[0] / TILE_DEG) * TILE_DEG
    lon0 = math.floor(box[1] / TILE_DEG) * TILE_DEG
    return lat0, lat0 + TILE_DEG, lon0, lon0 + TILE_DEG


def tiles_for(boxes) -> list[tuple[int, int, int, int]]:
    return sorted({tile_of(box) for box in boxes})


def regional_url(parameter: str, tile: tuple[int, int, int, int]) -> str:
    lat_min, lat_max, lon_min, lon_max = tile
    return URL_PATTERN.format(lat_min=lat_min, lat_max=lat_max, lon_min=lon_min, lon_max=lon_max,
                              parameter=parameter)


def raw_name(parameter: str, tile: tuple[int, int, int, int]) -> str:
    """File name of one raw answer, such as CLOUD_AMT_N60_N70_W030_W020.json."""
    lat_min, lat_max, lon_min, lon_max = tile

    def lat_part(value: int) -> str:
        return f"{'N' if value >= 0 else 'S'}{abs(value):02d}"

    def lon_part(value: int) -> str:
        return f"{'E' if value >= 0 else 'W'}{abs(value):03d}"

    return f"{parameter}_{lat_part(lat_min)}_{lat_part(lat_max)}_{lon_part(lon_min)}_{lon_part(lon_max)}.json"


# ---- reading a raw answer ------------------------------------------------------------------------

def _parsed(raw) -> dict:
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8")
    data = json.loads(raw) if isinstance(raw, str) else raw
    if not isinstance(data, dict) or not isinstance(data.get("features"), list) or not data["features"]:
        messages = data.get("messages") if isinstance(data, dict) else None
        raise ValueError(f"not a regional climatology answer: {messages!r}")
    return data


def answer_header(raw) -> dict:
    """What the service said about an answer: version, sources, period and fill value."""
    data = _parsed(raw)
    header = data.get("header") if isinstance(data.get("header"), dict) else {}
    api = header.get("api") if isinstance(header.get("api"), dict) else {}
    return {
        "version": api.get("version"),
        "name": api.get("name"),
        "sources": header.get("sources"),
        "start": header.get("start"),
        "end": header.get("end"),
        "fill_value": header.get("fill_value"),
        "messages": data.get("messages"),
    }


def read_answer(raw, parameter: str) -> dict[tuple[float, float], list[float | None]]:
    """Monthly means by grid box from one raw answer: {(lat, lon): [12 values, January first]}.

    The service's fill value becomes None, never a number. A percent that is
    neither the fill value nor between 0 and 100 is an error, as is an answer
    without grid boxes (an error message, for example) or for another parameter.
    """
    data = _parsed(raw)
    header = data.get("header") if isinstance(data.get("header"), dict) else {}
    fills = {FILL_VALUE}
    if isinstance(header.get("fill_value"), (int, float)):
        fills.add(float(header["fill_value"]))
    out: dict[tuple[float, float], list[float | None]] = {}
    for feature in data["features"]:
        try:
            lon, lat = feature["geometry"]["coordinates"][:2]   # GeoJSON order: longitude first
            months = feature["properties"]["parameter"][parameter]
        except (KeyError, TypeError, IndexError, ValueError) as error:
            raise ValueError(f"answer does not hold {parameter} by grid box: {error!r}") from error
        values: list[float | None] = []
        for name in MONTHS:
            value = months.get(name)
            if value is None:
                values.append(None)
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{parameter} {name} at {lat}, {lon} is not a number: {value!r}")
            value = float(value)
            if value in fills or math.isnan(value):
                values.append(None)
            elif 0.0 <= value <= 100.0:
                values.append(value)
            else:
                raise ValueError(f"{parameter} {name} at {lat}, {lon} is not a percent: {value}")
        out[(float(lat), float(lon))] = values
    return out


# ---- fetching -------------------------------------------------------------------------------------

def _retry_after(error: urllib.error.HTTPError) -> float | None:
    try:
        value = float(error.headers.get("Retry-After"))
    except (AttributeError, TypeError, ValueError):
        return None
    return min(max(value, 1.0), 600.0)


def fetch_tile(parameter: str, tile: tuple[int, int, int, int], raw_dir: Path, opener=None,
               sleep=time.sleep, attempts: int = 5, timeout: float = 120.0) -> tuple[Path, bool]:
    """Path of the raw answer for one parameter and tile, asking the service only if it is not on disk.

    Returns (path, asked). On "too many requests" (429) or a server fault (5xx) it
    waits and tries again, up to `attempts` times. Any other refusal, such as a
    request for a login (401, 403) or a wrong request (422), is raised at once.
    An answer that cannot be read is not kept.
    """
    raw_dir = Path(raw_dir)
    dest = raw_dir / raw_name(parameter, tile)
    if dest.exists():
        return dest, False
    opener = opener or urllib.request.urlopen
    request = urllib.request.Request(regional_url(parameter, tile), headers={"User-Agent": USER_AGENT})
    body = b""
    for attempt in range(1, attempts + 1):
        try:
            with opener(request, timeout=timeout) as response:
                body = response.read()
            break
        except urllib.error.HTTPError as error:
            busy = error.code == 429 or 500 <= error.code < 600
            if not busy or attempt == attempts:
                raise
            sleep(_retry_after(error) or WAIT_429_S * attempt)
        except (urllib.error.URLError, ConnectionError, TimeoutError, http.client.IncompleteRead):
            if attempt == attempts:
                raise
            sleep(2.0 * attempt)
    read_answer(body, parameter)   # raises if this is not an answer; nothing is kept then
    raw_dir.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    part.write_bytes(body)
    part.rename(dest)
    return dest, True


def read_raw(raw_dir: Path, parameter: str, tiles) -> dict[tuple[float, float], list[float | None]]:
    """All grid boxes of a parameter from the raw answers on disk. A missing file is an error."""
    by_box: dict[tuple[float, float], list[float | None]] = {}
    for tile in tiles:
        path = Path(raw_dir) / raw_name(parameter, tile)
        by_box.update(read_answer(path.read_bytes(), parameter))
    return by_box


# ---- the table of cells ---------------------------------------------------------------------------

def _months_or_null(values) -> list[float | None] | None:
    if values is None or all(value is None for value in values):
        return None
    return list(values)


def cells_table(cells, by_box, extra: dict | None = None) -> dict:
    """The "cells" block of cloud_cells.json: {id: {"cloud_pct": [12] or null, "grid": [lat, lon]}}.

    A box with no value at all is null as a whole; a box with some months
    missing keeps its list with null in those months. `extra` maps a further
    field name to its own values by box (the daylight and night versions).
    """
    table = {}
    for cell in cells:
        box = grid_box(cell["lat"], cell["lon"])
        record = {"cloud_pct": _months_or_null(by_box.get(box)), "grid": [box[0], box[1]]}
        for name, values in (extra or {}).items():
            record[name] = _months_or_null(values.get(box))
        table[cell["id"]] = record
    return table


def _date(text: str) -> str:
    return f"{text[0:4]}-{text[4:6]}-{text[6:8]}"


def meta_from(headers: list[dict], fetched: str, parameter: str = PARAMETERS[0]) -> dict:
    """The "meta" block, filled from the headers of the raw answers of one parameter that were used.

    The service names SYN1DEG as the source of CLOUD_AMT, and SYN1DEG and POWER
    as the sources of the daylight and night versions, so each parameter is
    described from its own answers.
    """
    if not headers:
        raise ValueError("no raw answer was read")
    first = headers[0]
    for head in headers[1:]:
        for key in ("version", "sources", "start", "end", "fill_value"):
            if head.get(key) != first.get(key):
                raise ValueError(f"raw answers disagree about {key}: {first.get(key)!r} and {head.get(key)!r}")
    sources = ", ".join(first.get("sources") or [])
    return {
        "source": (f"NASA POWER, {first.get('name')} {first.get('version')}, regional endpoint; "
                   f"data source named by the service: {sources} (CERES SYN1deg)"),
        "parameter": parameter,
        "period": f"{_date(first['start'])} to {_date(first['end'])}",
        "grid_deg": GRID_DEG,
        "fetched": fetched,
        "url_pattern": URL_PATTERN,
        "fill_value": first.get("fill_value"),
        "units": "percent of sky covered, monthly mean, January first",
        "what_it_is": WHAT_IT_IS,
        "what_it_is_not": WHAT_IT_IS_NOT,
    }

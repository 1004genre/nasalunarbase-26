# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Earth temperature for every cell, from the NASA POWER climatology service (MERRA-2).

What the numbers are, for the grid point of the MERRA-2 reanalysis nearest to the
cell centre (the grid is 0.5 degree of latitude by 0.625 degree of longitude),
by calendar month over the years the service names (January 2001 to December
2025 when this was written):
- T2M      mean air temperature 2 m above the ground, all hours of day and night;
- TS       mean temperature of the surface itself ("skin");
- T2M_MAX  the highest hourly air temperature of that calendar month in the whole period;
- T2M_MIN  the lowest hourly air temperature of that calendar month in the whole period.

T2M_MAX and T2M_MIN of this service are extremes of many years, not the mean daily
maximum and minimum. The service says so ("the maximum hourly ... temperature
... in the period of interest"), and a check against the daily series of one
grid point on 14 November 2026 agreed: the July figure was 20.55 C, the hottest
July day of 2001 to 2025 was 20.55 C, the mean daily maximum of July was 12.65 C.
The mean daily maximum and minimum are only to be had from the daily series,
one point per request; `read_daily` and `daily_mean_by_bin` do that for a few
named places.

Which years the values cover: the service's answers name January 2001 to December
2025, but at the six grid points checked on 14 November 2026 every monthly extreme
equals the record of the daily series for 2001 to 2020 (72 of 72 months for the
maximum and for the minimum; 54 and 59 of 72 for 2001 to 2025), and the monthly
means agree with the 2001 to 2020 means of the daily series within 0.03 C (within
0.7 C for 2001 to 2025). `years_the_climatology_fits` repeats that check on every run.

These are model values (a reanalysis) for a grid box some 55 km tall, at the
mean height of that box, which near an ice sheet or a mountain coast can lie
hundreds of metres above the cell. They enter no score.

Service rules followed, as for the cloud column (see twinfinder/cloud.py): one
parameter and at most 10 x 10 degrees per regional request, one request at a
time with a pause, no key and no login, wait and try again on answer 429.
"""
from __future__ import annotations

import datetime
import http.client
import json
import math
import time
import urllib.error
import urllib.request
from pathlib import Path

from twinfinder import cloud

USER_AGENT = cloud.USER_AGENT
URL_PATTERN = cloud.URL_PATTERN
DAILY_URL_PATTERN = (
    "https://power.larc.nasa.gov/api/temporal/daily/point"
    "?parameters={parameters}&community=RE&longitude={lon}&latitude={lat}&start={start}&end={end}&format=JSON"
)
PARAMETERS = ("T2M", "T2M_MAX", "T2M_MIN", "TS")
FIELDS = {"t2m_c": "T2M", "t2m_max_c": "T2M_MAX", "t2m_min_c": "T2M_MIN", "ts_c": "TS"}
MONTHS = cloud.MONTHS
N_BINS = cloud.N_BINS
GRID_LAT_DEG = 0.5      # MERRA-2: rows at -90, -89.5, ... 90
GRID_LON_DEG = 0.625    # MERRA-2: columns at -180, -179.375, ... 179.375 (there is no column at +180)
N_LON = 576
FILL_VALUE = -999.0
MIN_C, MAX_C = -100.0, 70.0   # outside this a value is not an air or ground temperature on Earth in Celsius
WAIT_429_S = 10.0
EDGE = 1e-9             # a centre half-way between two grid points goes to the point above, rounding noise or not

FIELD_MEANING = {
    "t2m_c": "T2M: mean air temperature 2 m above the ground, all hours of day and night, by calendar month",
    "ts_c": "TS: mean temperature of the surface itself (skin temperature), all hours, by calendar month",
    "t2m_max_c": ("T2M_MAX: the highest hourly air temperature at 2 m of that calendar month in all the years "
                  "the values cover (an extreme of many years; meta.years_fit says which years); not the mean "
                  "daily maximum"),
    "t2m_min_c": ("T2M_MIN: the lowest hourly air temperature at 2 m of that calendar month in all the years "
                  "the values cover (an extreme of many years; meta.years_fit says which years); not the mean "
                  "daily minimum"),
    "grid": "[latitude, longitude] of the MERRA-2 grid point nearest to the cell centre",
    "grid_elev_m": "mean height of that grid box in metres, as the service names it; null if it names none",
}
WHAT_IT_IS = (
    "Air temperature 2 m above the ground (mean, and the highest and lowest hour of the period) and "
    "surface temperature (mean), in degrees Celsius, for each calendar month over the years of the "
    "period, at the MERRA-2 grid point nearest to the cell centre, as served by the NASA POWER "
    "climatology service. Model values (a reanalysis), not measurements at the cell. Many cells share "
    "one grid point."
)
WHAT_IT_IS_NOT = (
    "Not a measurement at the cell and not the temperature during the hours of low Sun: it is a mean "
    "over all hours of the month and over a grid box about 55 km tall and 15 to 35 km wide at these "
    "latitudes, at the mean height of that box (grid_elev_m), which near an ice sheet or a mountain "
    "coast can lie hundreds of metres above the cell. t2m_max_c and t2m_min_c are the extremes of all "
    "the years covered, not a typical day's high and low. It enters no score."
)


# ---- ten-day bins ------------------------------------------------------------------------------

def by_bin(values) -> list[float | None]:
    """A monthly row as 36 ten-day values: each bin takes the month of its middle day.

    values is 12 monthly figures, January first. The bins are the project's
    (bin = min((day_of_year - 1) // 10, 35)); the month of the middle day comes to
    bin // 3. Null in, null out: None or NaN for a month gives None for its three
    bins, None for the whole row gives 36 times None. Never 0 for unknown.
    """
    if values is None:
        return [None] * N_BINS
    months = list(values)
    if len(months) != 12:
        raise ValueError(f"a monthly row must hold 12 months, got {len(months)}")
    clean: list[float | None] = []
    for value in months:
        if value is None or math.isnan(float(value)):
            clean.append(None)
        else:
            clean.append(float(value))
    return [clean[month] for month in cloud.BIN_MONTH]


# ---- grid points and request blocks --------------------------------------------------------------

def grid_point(lat: float, lon: float) -> tuple[float, float]:
    """The MERRA-2 grid point (lat, lon) nearest to a place, such as (64.0, -22.5).

    A place exactly half-way between two points goes to the one above (north,
    east). East of 179.6875 the nearest column is -180, which is what is returned.
    """
    row = math.floor((lat + 90.0) / GRID_LAT_DEG + 0.5 + EDGE)
    row = min(max(row, 0), round(180.0 / GRID_LAT_DEG))
    column = math.floor((lon + 180.0) / GRID_LON_DEG + 0.5 + EDGE) % N_LON
    return -90.0 + row * GRID_LAT_DEG, -180.0 + column * GRID_LON_DEG


def points_of(cells) -> list[tuple[float, float]]:
    """Every grid point that is the nearest one of at least one cell centre, each once, sorted."""
    return sorted({grid_point(cell["lat"], cell["lon"]) for cell in cells})


def _inside(point: tuple[float, float], tile: tuple[int, int, int, int]) -> bool:
    return tile[0] <= point[0] <= tile[1] and tile[2] <= point[1] <= tile[3]


def tiles_for_cells(cells) -> list[tuple[int, int, int, int]]:
    """The 10 degree blocks to ask for so that the grid point of every cell is in an answer.

    A regional answer holds the grid points on the edges of its block too, so the
    block of the cell centre holds the cell's grid point, except across the date
    line: the point at -180 is only in the block that starts there.
    """
    tiles = set()
    for cell in cells:
        own = cloud.tile_of((cell["lat"], cell["lon"]))
        tiles.add(own)
        point = grid_point(cell["lat"], cell["lon"])
        if not _inside(point, own):
            tiles.add(cloud.tile_of(point))
    return sorted(tiles)


# ---- reading a raw answer ------------------------------------------------------------------------

def _parsed(raw, kind: str = "regional climatology") -> dict:
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8")
    data = json.loads(raw) if isinstance(raw, str) else raw
    if not isinstance(data, dict) or not isinstance(data.get("header"), dict):
        messages = data.get("messages") if isinstance(data, dict) else None
        raise ValueError(f"not a {kind} answer: {messages!r}")
    return data


def _fills(data: dict) -> set[float]:
    fills = {FILL_VALUE}
    value = data["header"].get("fill_value")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        fills.add(float(value))
    return fills


def _celsius(value, fills: set[float], where: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{where} is not a number: {value!r}")
    value = float(value)
    if value in fills or math.isnan(value):
        return None
    if not MIN_C <= value <= MAX_C:
        raise ValueError(f"{where} is not a temperature in Celsius: {value}")
    return value


def _features(data: dict) -> list:
    features = data.get("features")
    if not isinstance(features, list) or not features:
        raise ValueError(f"not a regional climatology answer: {data.get('messages')!r}")
    return features


def _position(feature) -> tuple[float, float, float | None]:
    coordinates = feature["geometry"]["coordinates"]      # GeoJSON order: longitude first
    lon, lat = float(coordinates[0]), float(coordinates[1])
    if lon >= 180.0:
        lon -= 360.0
    elev = coordinates[2] if len(coordinates) > 2 else None
    known = isinstance(elev, (int, float)) and not isinstance(elev, bool) and elev != FILL_VALUE
    return lat, lon, float(elev) if known else None


def read_answer(raw, parameter: str) -> dict[tuple[float, float], list[float | None]]:
    """Monthly values by grid point from one raw answer: {(lat, lon): [12 values, January first]}.

    The service's fill value becomes None, never a number; a real 0.0 stays 0.0.
    A value that is neither the fill value nor between -100 and 70 C is an error,
    as is an answer without grid points (an error message) or for another parameter.
    """
    data = _parsed(raw)
    fills = _fills(data)
    out: dict[tuple[float, float], list[float | None]] = {}
    for feature in _features(data):
        try:
            lat, lon, _ = _position(feature)
            months = feature["properties"]["parameter"][parameter]
            values = [_celsius(months.get(name), fills, f"{parameter} {name} at {lat}, {lon}") for name in MONTHS]
        except (KeyError, TypeError, IndexError, AttributeError) as error:
            raise ValueError(f"answer does not hold {parameter} by grid point: {error!r}") from error
        out[(lat, lon)] = values
    return out


def read_elevations(raw) -> dict[tuple[float, float], float | None]:
    """Mean height of each grid box in metres, as a raw answer names it (third coordinate)."""
    out = {}
    for feature in _features(_parsed(raw)):
        lat, lon, elev = _position(feature)
        out[(lat, lon)] = elev
    return out


# ---- fetching -------------------------------------------------------------------------------------

def _retry_after(error: urllib.error.HTTPError) -> float | None:
    try:
        value = float(error.headers.get("Retry-After"))
    except (AttributeError, TypeError, ValueError):
        return None
    return min(max(value, 1.0), 600.0)


def _fetch(url: str, dest: Path, check, opener=None, sleep=time.sleep, attempts: int = 5,
           timeout: float = 120.0) -> tuple[Path, bool]:
    """Path of one raw answer, asking the service only if it is not on disk. Returns (path, asked).

    On "too many requests" (429) or a server fault (5xx) it waits and tries again,
    up to `attempts` times. Any other refusal, such as a request for a login (401,
    403), is raised at once. `check` must raise for a body that is not an answer;
    such a body is not kept.
    """
    dest = Path(dest)
    if dest.exists():
        return dest, False
    opener = opener or urllib.request.urlopen
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
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
    check(body)
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    part.write_bytes(body)
    part.rename(dest)
    return dest, True


def fetch_tile(parameter: str, tile: tuple[int, int, int, int], raw_dir: Path, opener=None,
               sleep=time.sleep, attempts: int = 5, timeout: float = 120.0) -> tuple[Path, bool]:
    """The raw regional answer for one parameter and 10 degree block, kept as <parameter>_<block>.json."""
    dest = Path(raw_dir) / cloud.raw_name(parameter, tile)
    return _fetch(cloud.regional_url(parameter, tile), dest, lambda body: read_answer(body, parameter),
                  opener=opener, sleep=sleep, attempts=attempts, timeout=timeout)


def read_raw(raw_dir: Path, parameter: str, tiles) -> dict[tuple[float, float], list[float | None]]:
    """All grid points of a parameter from the raw answers on disk. A missing file is an error."""
    by_point: dict[tuple[float, float], list[float | None]] = {}
    for tile in tiles:
        by_point.update(read_answer((Path(raw_dir) / cloud.raw_name(parameter, tile)).read_bytes(), parameter))
    return by_point


# ---- the table of cells ---------------------------------------------------------------------------

def _months_or_null(values) -> list[float | None] | None:
    if values is None or all(value is None for value in values):
        return None
    return list(values)


def cells_table(cells, by_point: dict, elevations: dict | None = None) -> dict:
    """The "cells" block of temperature_cells.json.

    by_point maps a parameter name to its values by grid point. Each cell gets
    {"t2m_c", "t2m_max_c", "t2m_min_c", "ts_c": [12] or null, "grid": [lat, lon],
    "grid_elev_m"}. A row with no value at all (or a grid point the service did
    not give) is null as a whole; a row with some months missing keeps its list
    with null in those months.
    """
    elevations = elevations or {}
    table = {}
    for cell in cells:
        point = grid_point(cell["lat"], cell["lon"])
        record: dict = {field: _months_or_null(by_point.get(parameter, {}).get(point))
                        for field, parameter in FIELDS.items()}
        record["grid"] = [point[0], point[1]]
        record["grid_elev_m"] = elevations.get(point)
        table[cell["id"]] = record
    return table


def _date(text: str) -> str:
    return f"{text[0:4]}-{text[4:6]}-{text[6:8]}"


def meta_from(headers: dict, fetched: str) -> dict:
    """The "meta" block, from the headers (cloud.answer_header) of the raw answers used, by parameter.

    All answers must agree about period, fill value and service version. The
    service names MERRA2 as the source of T2M and TS, and MERRA2 and POWER as the
    sources of the two extremes (POWER works them out from hourly MERRA-2).
    """
    every = [head for parameter in PARAMETERS for head in headers.get(parameter) or []]
    if not every or any(not headers.get(parameter) for parameter in PARAMETERS):
        raise ValueError("no raw answer was read for at least one parameter")
    first = every[0]
    for head in every[1:]:
        for key in ("version", "start", "end", "fill_value"):
            if head.get(key) != first.get(key):
                raise ValueError(f"raw answers disagree about {key}: {first.get(key)!r} and {head.get(key)!r}")
    sources = {}
    for parameter in PARAMETERS:
        named = {tuple(head.get("sources") or []) for head in headers[parameter]}
        if len(named) != 1:
            raise ValueError(f"raw answers of {parameter} disagree about the source: {sorted(named)!r}")
        sources[parameter] = ", ".join(named.pop())
    said = "; ".join(f"{parameter}: {sources[parameter]}" for parameter in PARAMETERS)
    return {
        "source": (f"NASA POWER, {first.get('name')} {first.get('version')}, regional endpoint; data source "
                   f"named by the service for each parameter: {said} (MERRA-2 is NASA's reanalysis)"),
        "parameters": list(PARAMETERS),
        "period": f"{_date(first['start'])} to {_date(first['end'])}",
        "grid_deg": [GRID_LAT_DEG, GRID_LON_DEG],
        "grid_deg_order": "latitude step, longitude step",
        "fetched": fetched,
        "url_pattern": URL_PATTERN,
        "fill_value": first.get("fill_value"),
        "units": "degrees Celsius, one value per calendar month, January first",
        "what_it_is": WHAT_IT_IS,
        "what_it_is_not": WHAT_IT_IS_NOT,
        "fields": dict(FIELD_MEANING),
    }


# ---- daily series at one point (for a few named places) ---------------------------------------------

def daily_url(lat: float, lon: float, start: str, end: str, parameters=PARAMETERS) -> str:
    return DAILY_URL_PATTERN.format(parameters=",".join(parameters), lat=lat, lon=lon, start=start, end=end)


def read_daily(raw, parameter: str) -> dict[datetime.date, float | None]:
    """One parameter of a raw daily point answer: {date: value}, the fill value as None."""
    data = _parsed(raw, kind="daily point")
    fills = _fills(data)
    try:
        days = data["properties"]["parameter"][parameter]
        return {datetime.date(int(key[0:4]), int(key[4:6]), int(key[6:8])):
                _celsius(value, fills, f"{parameter} on {key}") for key, value in days.items()}
    except (KeyError, TypeError, AttributeError) as error:
        raise ValueError(f"answer does not hold daily {parameter}: {error!r}") from error


def daily_position(raw) -> tuple[float, float, float | None]:
    """(lat, lon, height in m) of the grid point a raw daily point answer is for."""
    return _position(_parsed(raw, kind="daily point"))


def fetch_daily(lat: float, lon: float, start: str, end: str, dest: Path, opener=None, sleep=time.sleep,
                attempts: int = 5, timeout: float = 180.0) -> tuple[Path, bool]:
    """The raw daily series of the four parameters at one point, asked only if it is not on disk."""
    def check(body):
        for parameter in PARAMETERS:
            read_daily(body, parameter)
    return _fetch(daily_url(lat, lon, start, end), dest, check, opener=opener, sleep=sleep,
                  attempts=attempts, timeout=timeout)


def daily_mean_by_bin(series: dict) -> tuple[list[float | None], list[int]]:
    """Mean of a daily series in each of the 36 ten-day bins, over all years, and the days counted.

    The bin of a day is the project's: min((day_of_year - 1) // 10, 35). A day
    without a value is left out; a bin without any day is None, never 0.
    """
    sums = [0.0] * N_BINS
    counts = [0] * N_BINS
    for day, value in series.items():
        if value is None:
            continue
        b = cloud.bin_index(day.timetuple().tm_yday)
        sums[b] += value
        counts[b] += 1
    return [sums[b] / counts[b] if counts[b] else None for b in range(N_BINS)], counts


def years_the_climatology_fits(clim_max, clim_min, daily_max: dict, daily_min: dict,
                               tolerance_c: float = 0.011) -> dict | None:
    """Over which years were the service's monthly extremes taken? A check against the daily series.

    clim_max and clim_min are the climatology's 12 monthly T2M_MAX and T2M_MIN (or None);
    daily_max and daily_min are {date: value} of the same grid point. For every last year
    from the first year of the series on, a month counts as equal when the highest (lowest)
    day of that calendar month in the years up to it equals the climatology within
    tolerance_c. The last year with the most equal months is the one that fits; on a tie
    the later year (a year without a new record fits as well as the year before it, so
    several places should be added up by months_equal_by_end_year before a year is named).
    None when there is no row or no series: unknown, never a guess.
    """
    pairs = [(clim, series, pick) for clim, series, pick in ((clim_max, daily_max, max), (clim_min, daily_min, min))
             if clim and series]
    years = sorted({day.year for _, series, _ in pairs for day, value in series.items() if value is not None})
    if not years:
        return None
    equal = {year: 0 for year in years}
    compared = 0
    for clim, series, pick in pairs:
        record: dict[tuple[int, int], float] = {}
        for day, value in series.items():
            if value is not None:
                key = (day.year, day.month)
                record[key] = value if key not in record else pick(record[key], value)
        for month in range(1, 13):
            wanted = clim[month - 1]
            if wanted is None:
                continue
            so_far = None
            for year in years:
                if (year, month) in record:
                    so_far = record[(year, month)] if so_far is None else pick(so_far, record[(year, month)])
                if so_far is not None and abs(so_far - wanted) < tolerance_c:
                    equal[year] += 1
            compared += so_far is not None
    if not compared:
        return None
    best = max(years, key=lambda year: (equal[year], year))
    return {"first_year": years[0], "last_year_of_the_daily_series": years[-1], "end_year_that_fits_best": best,
            "months_compared": compared, "months_equal_at_that_end_year": equal[best],
            "months_equal_with_all_years": equal[years[-1]],
            "months_equal_by_end_year": {str(year): equal[year] for year in years}}


def monthly_statistics(series: dict) -> dict[str, list[float | None]]:
    """Mean, highest and lowest value of a daily series by calendar month over all its years."""
    by_month: list[list[float]] = [[] for _ in range(12)]
    for day, value in series.items():
        if value is not None:
            by_month[day.month - 1].append(value)
    return {
        "mean": [sum(values) / len(values) if values else None for values in by_month],
        "highest": [max(values) if values else None for values in by_month],
        "lowest": [min(values) if values else None for values in by_month],
    }

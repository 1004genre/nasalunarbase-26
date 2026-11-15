"""The Sun's path over the horizon at a lunar landing region, beside its path at a place on Earth.

Data for the one picture that explains the project, and a first drawing of it.

The Moon: the Sun's azimuth and elevation, hour by hour, seen from the centre of the Malapert
Massif target and of the Connecting Ridge target (coordinates from
data/derived/moon_targets.json), asked of the public JPL Horizons API (no refraction: the Moon
has no air). The raw answers are kept in data/raw/horizons_sunpath/ and are not asked for again
while they are there.

The Earth: two places from the project's results, Haughton crater on Devon Island and the cell
that heads the Malapert lighting list in data/derived/ranking.txt when the script runs. For each:
the middle day of its best ten-day period for the Malapert target (top_bins in
data/derived/grazing_cells.json), the Sun's apparent path over those 24 hours (twinfinder.sun,
with refraction), and the terrain horizon of the cell by compass direction (twinfinder.horizon
on Copernicus GLO-90 tiles already in data/raw/glo90, on a 60 m grid, as
scripts/build_horizon_cells.py does). This script downloads no elevation tile: a cell whose
tiles are not on disk gets a null horizon and the reason.

    uv run python scripts/build_sunpath_demo.py                       writes data/derived/sunpath_demo.json
    uv run python scripts/build_sunpath_demo.py --preview out.svg     and a drawing (one SVG, plain strings)
    ... --preview-lunar connecting-ridge --preview-earth top-cell     which pair the drawing shows
    ... --refetch                                                     asks JPL Horizons again

Safe to run again at any time: every number comes from the files as they are at that moment, the
result is written beside the old file and renamed into place, and unknown is null, never 0.
Code written with AI assistance (Claude).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import ssl
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

import numpy as np

from twinfinder import earth, grid, horizon, sun

HORIZONS_API = "https://ssd.jpl.nasa.gov/api/horizons.api"
USER_AGENT = "twinfinder/0.1"
RAW_DIR = Path("data/raw/horizons_sunpath")
MOON_TARGETS = Path("data/derived/moon_targets.json")
RANKING = Path("data/derived/ranking.txt")
GRAZING = Path("data/derived/grazing_cells.json")
OUT = Path("data/derived/sunpath_demo.json")

YEAR = 2026
# The whole of 2026, with two months around it so that a full trip round the horizon is there
# for any date of the year. Year figures use the rows of 2026 only.
START, STOP, STEP = "2025-12-01 00:00", "2027-02-01 00:00", "1 h"
SITE_HEIGHT_KM = 0.0            # on the 1737.4 km sphere; height moves the Sun's direction by under a millionth of a degree
LUNAR_IDS = ("malapert", "connecting-ridge")
EARTH_TARGET = "malapert"       # the lunar site whose band the Earth places are measured against
HAUGHTON = {"id": "haughton", "name": "Haughton crater, Devon Island",
            "why": "NASA-funded rover tests used it (Haughton-Mars Project)", "place_lat": 75.38, "place_lon": -89.67}
PATH_STEP_MINUTES = 5           # the Earth path that is stored and drawn
COUNT_STEP_MINUTES = 1          # the step the minutes and spells are counted on, as in the project
PIXEL_M, HALF_KM, REACH_KM = 60.0, 5.0, 25.0   # as scripts/build_horizon_cells.py
EYE_M = 2.0                     # the default eye height of twinfinder.horizon.horizon_deg
CAPTION = "Drawn by code from JPL Horizons and Copernicus elevation data; code written with AI assistance."


# ---------------------------------------------------------------- JPL Horizons

def horizons_params(lon_east_deg: float, lat_deg: float, height_km: float, start: str, stop: str,
                    step: str = STEP) -> dict[str, str]:
    """What is asked of Horizons: the Sun (10) seen from a point on the Moon (301), azimuth and elevation, no air."""
    return {
        "format": "text",
        "COMMAND": "'10'",
        "OBJ_DATA": "'NO'",
        "MAKE_EPHEM": "'YES'",
        "EPHEM_TYPE": "'OBSERVER'",
        "CENTER": "'coord@301'",
        "COORD_TYPE": "'GEODETIC'",
        "SITE_COORD": f"'{lon_east_deg % 360.0:.6f},{lat_deg:.6f},{height_km:.3f}'",   # east longitude, latitude, km
        "START_TIME": f"'{start}'",
        "STOP_TIME": f"'{stop}'",
        "STEP_SIZE": f"'{step}'",
        "QUANTITIES": "'4'",
        "ANG_FORMAT": "'DEG'",
        "APPARENT": "'AIRLESS'",
        "CSV_FORMAT": "'YES'",
        "CAL_FORMAT": "'BOTH'",
    }


def horizons_url(params: dict[str, str]) -> str:
    return HORIZONS_API + "?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)


def _header(text: str, label: str) -> str | None:
    found = re.search(rf"^{re.escape(label)}\s*:\s*(.*?)\s*(\{{.*)?$", text, flags=re.MULTILINE)
    return found.group(1).strip() if found else None


def parse_horizons(text: str) -> dict:
    """Times, azimuths and elevations of a Horizons observer table, and what its header says about the frame.

    Horizons answers a bad request with HTTP 200 and a text without a table, so a
    missing table is an error here and never an empty path.
    """
    if "$$SOE" not in text or "$$EOE" not in text:
        raise ValueError("no table in the Horizons answer: " + " | ".join(text.strip().splitlines()[:6])[:400])
    head, body = text.split("$$SOE", 1)
    body = body.split("$$EOE", 1)[0]
    names = next((line for line in reversed(head.splitlines()) if "Azi_(" in line and "Elev_(" in line), None)
    if names is None:
        raise ValueError("no table with azimuth and elevation in the Horizons answer")
    columns = [name.strip() for name in names.split(",")]     # Azi_(a-app) without air, Azi_(r-app) refracted
    i_az = next(i for i, name in enumerate(columns) if name.startswith("Azi_("))
    i_el = next(i for i, name in enumerate(columns) if name.startswith("Elev_("))
    i_jd = next(i for i, name in enumerate(columns) if name.endswith("JDUT"))
    utc, jd, az, el = [], [], [], []
    for line in body.strip().splitlines():
        parts = [part.strip() for part in line.split(",")]
        utc.append(parts[0])
        jd.append(float(parts[i_jd]))
        az.append(float(parts[i_az]))
        el.append(float(parts[i_el]))
    return {"utc": utc, "jd": np.array(jd), "azimuth_deg": np.array(az), "elevation_deg": np.array(el),
            "header": {"frame": _header(text, "Center pole/equ"), "refraction": _header(text, "Atmos refraction"),
                       "site": _header(text, "Center geodetic"), "target": _header(text, "Target body name"),
                       "centre": _header(text, "Center body name"), "radii_km": _header(text, "Center radii")}}


def _checked_urlopen(request, timeout=None):
    """urlopen with certificates checked as always, against the system's list and, where it is installed, certifi's.

    The certificate file of macOS that this Python reads lacks the root the JPL server's chain
    ends in (Sectigo R46), so the plain call fails there. certifi comes with rasterio; nothing
    is added to the project, and without it the system's list alone is used.
    """
    context = ssl.create_default_context()
    try:
        import certifi
        context.load_verify_locations(certifi.where())
    except ImportError:
        pass
    return urllib.request.urlopen(request, timeout=timeout, context=context)


def fetch_horizons(site_id: str, lon_east_deg: float, lat_deg: float, raw_dir: Path = RAW_DIR,
                   refetch: bool = False, urlopen=_checked_urlopen) -> Path:
    """The raw Horizons answer for one site, asked for once and kept; beside it a note of the exact request."""
    raw_dir = Path(raw_dir)
    dest = raw_dir / f"sun_from_{site_id}_{START[:10]}_to_{STOP[:10]}_{STEP.replace(' ', '')}.txt"
    if dest.exists() and not refetch:
        return dest
    raw_dir.mkdir(parents=True, exist_ok=True)
    params = horizons_params(lon_east_deg, lat_deg, SITE_HEIGHT_KM, START, STOP)
    url = horizons_url(params)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=180) as response:
        body = response.read()
    part = dest.with_name(dest.name + ".part")
    part.write_bytes(body)
    try:
        parse_horizons(body.decode("utf-8", errors="replace"))
    except ValueError:
        os.replace(part, dest.with_name(dest.name + ".rejected"))   # kept to be looked at, never read as a path
        raise
    os.replace(part, dest)
    note = {"url": url, "params": params, "user_agent": USER_AGENT, "bytes": len(body),
            "fetched_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    write_text(dest.with_name(dest.name + ".request.json"), json.dumps(note, indent=1))
    return dest


def in_year(utc_labels: list[str], year: int) -> np.ndarray:
    return np.array([label.startswith(f"{year}-") for label in utc_labels], dtype=bool)


# ---------------------------------------------------------------- trips round the horizon

def progress_turns(azimuth_deg) -> tuple[np.ndarray, float]:
    """How many times the Sun has gone round the compass since the first row, and which way (+1 clockwise)."""
    unwrapped = np.degrees(np.unwrap(np.radians(np.asarray(azimuth_deg, dtype=float))))
    sign = 1.0 if unwrapped[-1] >= unwrapped[0] else -1.0
    turns = sign * (unwrapped - unwrapped[0]) / 360.0
    if np.any(np.diff(turns) <= 0.0):
        raise ValueError("the Sun does not move one way round the horizon in these rows")
    return turns, sign


def mean_trip_days(jd, azimuth_deg) -> float:
    """Mean time for one trip of the Sun round the horizon: the days covered over the turns made."""
    turns, _ = progress_turns(azimuth_deg)
    return float((jd[-1] - jd[0]) / turns[-1])


def trip_through(jd, azimuth_deg, index: int, start_az: float = 180.0) -> dict:
    """The one trip round the horizon, from start_az back to start_az, that holds row index.

    Rows first to last lie inside the trip; its start and end times are read between rows.
    If the data end before that trip is whole, the nearest whole trip is given and
    "complete" is False.
    """
    turns, sign = progress_turns(azimuth_deg)
    offset = (sign * (start_az - azimuth_deg[0]) / 360.0) % 1.0     # turns made when the Sun first stands at start_az
    k = math.floor(turns[index] - offset)
    k_min, k_max = math.ceil(turns[0] - offset), math.floor(turns[-1] - offset) - 1
    if k_max < k_min:
        raise ValueError("the rows do not hold one whole trip round the horizon")
    complete = k_min <= k <= k_max
    begin = offset + min(max(k, k_min), k_max)
    start_jd, end_jd = (float(v) for v in np.interp([begin, begin + 1.0], turns, jd))
    inside = np.flatnonzero((turns >= begin) & (turns <= begin + 1.0))
    first, last = int(inside[0]), int(inside[-1])
    return {"first": first, "last": last, "start_jd": start_jd, "end_jd": end_jd, "days": end_jd - start_jd,
            "complete": bool(complete), "hours_since_start": (np.asarray(jd[first:last + 1]) - start_jd) * 24.0}


def whole_trip_days(jd, azimuth_deg, start_az: float = 180.0) -> list[float]:
    """Length in days of every whole trip (start_az back to start_az) in the rows, in order of time."""
    turns, sign = progress_turns(azimuth_deg)
    offset = (sign * (start_az - azimuth_deg[0]) / 360.0) % 1.0
    k_min, k_max = math.ceil(turns[0] - offset), math.floor(turns[-1] - offset) - 1
    marks = np.interp([offset + k for k in range(k_min, k_max + 2)], turns, jd)
    return [float(d) for d in np.diff(marks)]


def ceiling_deg(target: dict) -> float:
    """The project's band limit for a lunar site: 90 - |latitude of the centre| + 1.54, to two decimals."""
    return round(float(target["sun_max_elev_deg"]), 2)


def lunar_record(target: dict, series: dict, year: int = YEAR) -> dict:
    """One lunar site: the year's highest Sun against the ceiling, the length of a trip, and one trip's path."""
    jd, az, el, utc = series["jd"], series["azimuth_deg"], series["elevation_deg"], series["utc"]
    rows = np.flatnonzero(in_year(utc, year))
    if not len(rows):
        raise ValueError(f"no rows of {year} in the Horizons answer for {target['id']}")
    peak = int(rows[np.argmax(el[rows])])
    low = int(rows[np.argmin(el[rows])])
    trip = trip_through(jd, az, peak)
    first, last = trip["first"], trip["last"]
    path_el = el[first:last + 1]
    limit = ceiling_deg(target)
    _, sign = progress_turns(az)
    step_h = float(np.median(np.diff(jd))) * 24.0
    return {
        "id": target["id"], "name": target["name"],
        "lat": round(float(target["centre_lat"]), 5), "lon_east": round(float(target["centre_lon"]) % 360.0, 5),
        "ceiling_deg": limit,
        "ceiling_rule": "90 - |latitude of the target centre| + 1.54 (the Moon's tilt), from moon_targets.json",
        "year": year,
        "year_max_elevation_deg": round(float(el[peak]), 3), "year_max_utc": utc[peak],
        "year_max_azimuth_deg": round(float(az[peak]), 2),
        "year_max_minus_ceiling_deg": round(float(el[peak]) - limit, 3),
        "year_min_elevation_deg": round(float(el[low]), 3), "year_min_utc": utc[low],
        "year_share_above_level_horizon": round(float((el[rows] > 0.0).mean()), 4),
        "year_share_above_ceiling": round(float((el[rows] > limit).mean()), 4),
        "mean_trip_days": round(mean_trip_days(jd[rows], az[rows]), 3),
        "shortest_trip_days": round(min(whole_trip_days(jd, az)), 3),
        "longest_trip_days": round(max(whole_trip_days(jd, az)), 3),
        "direction": ("clockwise (east to south to west)" if sign > 0 else "anticlockwise (east to north to west)"),
        "path_trip_days": round(trip["days"], 3),
        "path_days_above_level_horizon": round(float((path_el > 0.0).sum()) * step_h / 24.0, 2),
        "path_days_in_band": round(float(((path_el > 0.0) & (path_el <= limit)).sum()) * step_h / 24.0, 2),
        "path": {
            "what": "one trip of the Sun round the horizon, from due south back to due south, that holds the "
                    "year's highest Sun; one row an hour",
            "complete": trip["complete"], "start_utc": utc[first], "end_utc": utc[last],
            "hours_since_start": [round(float(h), 3) for h in trip["hours_since_start"]],
            "azimuth_deg": [round(float(a), 2) for a in az[first:last + 1]],
            "elevation_deg": [round(float(e), 3) for e in path_el],
        },
    }


# ---------------------------------------------------------------- choosing the Earth places

def ranking_top_cell(text: str, target_name: str, goal: str = "Low Sun on bare ground",
                     scope: str = "all sites") -> tuple[float, float]:
    """Latitude and longitude of the first row of a list of ranking.txt (the first such list is the northern one)."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        parts = [part.strip() for part in line.split("|")]
        if len(parts) >= 3 and parts[0] == goal and parts[1].startswith(target_name) and parts[2].startswith(scope):
            for row in lines[i + 1:]:
                if not row.strip():
                    break
                tokens = row.split()
                try:
                    return float(tokens[1]), float(tokens[2])
                except (ValueError, IndexError):
                    continue        # the line of column names
            raise ValueError(f"the list '{goal} | {target_name} | {scope}' of the ranking has no rows")
    raise ValueError(f"no list '{goal} | {target_name} | {scope}' in the ranking")


def find_cell(cells: list[dict], lat: float, lon: float, tolerance_deg: float = 0.006) -> dict:
    """The cell whose centre is the pair of coordinates the ranking prints (two decimals)."""
    near = [c for c in cells if abs(c["lat"] - lat) <= tolerance_deg and abs(c["lon"] - lon) <= tolerance_deg]
    if not near:
        raise ValueError(f"no cell at {lat}, {lon} in the cells file")
    return min(near, key=lambda c: abs(c["lat"] - lat) + abs(c["lon"] - lon))


def cell_holding(cells: list[dict], lat: float, lon: float) -> dict:
    """The grid cell that holds a point."""
    wanted = grid.cell_id(lat, lon)
    for cell in cells:
        if cell["id"] == wanted:
            return cell
    raise ValueError(f"no cell {wanted} (holding {lat}, {lon}) in the cells file")


def middle_day(bin_index: int) -> int:
    """Day of year in the middle of a ten-day period (the rule of scripts/export_site.py; the last period ends on day 365)."""
    first = bin_index * sun.BIN_DAYS + 1
    last = first + sun.BIN_DAYS - 1 if bin_index < sun.N_BINS - 1 else 365
    return first + (last - first) // 2


def bin_label(bin_index: int) -> str:
    first = bin_index * sun.BIN_DAYS + 1
    last = first + sun.BIN_DAYS - 1 if bin_index < sun.N_BINS - 1 else 365
    return f"{sun.doy_to_label(first)}-{sun.doy_to_label(last)}"


# ---------------------------------------------------------------- the Sun on Earth

def earth_path(lat: float, day_of_year: int, step_minutes: int = PATH_STEP_MINUTES) -> dict:
    """The Sun over 24 hours of local solar time: azimuth, apparent elevation (with refraction) and true elevation."""
    hours = np.arange(0, 1440 + step_minutes, step_minutes) / 60.0
    true, az = sun.elevation_azimuth(lat, day_of_year, hours)
    apparent = sun.apparent_elevation_deg(true)
    return {"solar_time_h": [round(float(h), 4) for h in hours],
            "azimuth_deg": [round(float(a), 2) for a in az],
            "elevation_deg": [round(float(e), 3) for e in apparent],
            "true_elevation_deg": [round(float(e), 3) for e in true]}


def _longest_run_touching_the_middle_day(inside: np.ndarray, steps: int) -> int:
    """Longest run of True that touches the middle one of three days of steps each, at most one day long."""
    best = run_start = 0
    padded = np.concatenate([inside, [False]])
    in_run = False
    for i, value in enumerate(padded):
        if value and not in_run:
            in_run, run_start = True, i
        elif not value and in_run:
            in_run = False
            if i > steps and run_start < 2 * steps:      # the run [run_start, i) reaches into the middle day
                best = max(best, i - run_start)
    return min(best, steps)


def band_stats(lat: float, day_of_year: int, limit_deg: float, horizon_by_sector=None,
               step_minutes: int = COUNT_STEP_MINUTES) -> dict:
    """Minutes of one day with the Sun's apparent centre in (0, limit], and the longest unbroken spell.

    Counted at the middle of each minute, as twinfinder.sun.longest_stretch_hours_by_day does. A
    spell that runs through midnight is one spell and counts in full (the days before and after
    are worked out too), but never as more than 24 hours. With a terrain horizon (36 values, one
    per 10-degree sector, sector k from 10k degrees) the same again for the minutes in which the
    Sun also stands above the ground in its direction; None when no horizon is given.
    """
    steps = 1440 // step_minutes
    hours = (np.arange(3 * steps) + 0.5) * (step_minutes / 60.0) - 24.0     # the day before, the day, the day after
    true, az = sun.elevation_azimuth(lat, day_of_year, hours)
    apparent = sun.apparent_elevation_deg(true)
    inside = (apparent > 0.0) & (apparent <= limit_deg)
    today = slice(steps, 2 * steps)
    stats = {"minutes_in_band": int(inside[today].sum()) * step_minutes,
             "longest_spell_minutes": _longest_run_touching_the_middle_day(inside, steps) * step_minutes,
             "minutes_above_terrain": None, "longest_spell_minutes_above_terrain": None}
    if horizon_by_sector is not None and all(value is not None for value in horizon_by_sector):
        ground = np.asarray(horizon_by_sector, dtype=float)[(az // 10.0).astype(int) % sun.AZ_SECTORS]
        seen = inside & (apparent > ground)
        stats["minutes_above_terrain"] = int(seen[today].sum()) * step_minutes
        stats["longest_spell_minutes_above_terrain"] = _longest_run_touching_the_middle_day(seen, steps) * step_minutes
    return stats


# ---------------------------------------------------------------- the ground on Earth

def cached_or_ocean(url: str, dest_dir: Path) -> Path | None:
    """Stands in for the tile download: the tile on disk, None for known ocean, never a request to a server."""
    name = url.rsplit("/", 1)[-1]
    path = Path(dest_dir) / name
    if path.exists():
        return path
    if (Path(dest_dir) / (name + ".missing")).exists():
        return None
    raise RuntimeError(f"tile not on disk: {url} (this script downloads no elevation tile; "
                       f"scripts/build_horizon_cells.py fetches them)")


def terrain_horizon(lat: float, lon: float, half_km: float = HALF_KM, reach_km: float = REACH_KM,
                    pixel_m: float = PIXEL_M) -> dict:
    """Terrain horizon of a cell by 10-degree sector: seen from its centre, and the median over its land pixels.

    The same window, grid, water rule and ray march as horizon.cell_open_share (which
    scripts/build_horizon_cells.py calls): the cell is the central square of half-width half_km,
    ground out to reach_km can stand in the way, the eye is 2 m above the ground, heights drop
    with distance for the Earth's curve and standard refraction.
    """
    half_window = half_km + reach_km
    land_z = earth.elevation_window(lat, lon, half_window, pixel_m)        # NaN on water and where there is no tile
    size = int(round(2 * half_km * 1000.0 / pixel_m))
    start = (land_z.shape[0] - size) // 2
    inner = (slice(start, start + size), slice(start, start + size))
    land = np.isfinite(land_z[inner])
    if not land.any():
        raise ValueError("no land pixels in the cell")
    z = earth.elevation_window(lat, lon, half_window, pixel_m, mask_water=False, sea_as_zero=True)
    angles = horizon.horizon_deg(z, pixel_m, horizon.SECTOR_CENTRES_DEG + [0.0, 180.0], inner, max_km=reach_km,
                                 eye_m=EYE_M)
    sectors = angles[:horizon.AZ_SECTORS]
    over_land = sectors[:, land]
    middle = size // 2
    return {
        "sector_centres_deg": [float(a) for a in horizon.SECTOR_CENTRES_DEG],
        "centre_deg": [round(float(v), 2) for v in sectors[:, middle, middle]],
        "cell_median_deg": [round(float(v), 2) for v in np.median(over_land, axis=1)],
        "cell_p10_deg": [round(float(v), 2) for v in np.percentile(over_land, 10, axis=1)],
        "cell_p90_deg": [round(float(v), 2) for v in np.percentile(over_land, 90, axis=1)],
        "north_deg": round(float(np.median(angles[horizon.AZ_SECTORS][land])), 2),
        "south_deg": round(float(np.median(angles[horizon.AZ_SECTORS + 1][land])), 2),
        "centre_is_land": bool(land[middle, middle]), "land_share": round(float(land.mean()), 3),
        "pixel_m": float(pixel_m), "half_km": float(half_km), "reach_km": float(reach_km), "eye_m": EYE_M,
    }


def horizon_or_reason(lat: float, lon: float) -> tuple[dict | None, str | None]:
    """The terrain horizon, or None and why it cannot be known (a tile not on disk, a window over the date line)."""
    try:
        return terrain_horizon(lat, lon), None
    except (RuntimeError, ValueError) as error:
        return None, str(error)


def earth_record(place: dict, cell: dict, target: dict, horizon_fn=horizon_or_reason) -> dict:
    """One Earth place on the middle day of its best ten-day period for a lunar target."""
    limit = ceiling_deg(target)
    top = ((cell.get("targets") or {}).get(target["id"]) or {}).get("top_bins") or []
    ground, why_not = horizon_fn(cell["lat"], cell["lon"])
    record = {
        **place, "cell_id": cell["id"], "cell_lat": cell["lat"], "cell_lon": cell["lon"],
        "region": cell.get("region"), "target": target["id"], "band_deg": [0.0, limit],
        "best_bin": None, "best_bin_label": None, "best_bin_hours": None, "day_of_year": None, "date": None,
        "path": None, "path_missing_because": None,
        "day_min_elevation_deg": None, "day_max_elevation_deg": None,
        "minutes_in_band": None, "longest_spell_minutes": None,
        "minutes_above_terrain": None, "longest_spell_minutes_above_terrain": None,
        "minutes_above_terrain_cell_median": None, "longest_spell_minutes_above_terrain_cell_median": None,
        "terrain_horizon": ground, "terrain_horizon_missing_because": why_not,
    }
    if not top:
        record["path_missing_because"] = f"no ten-day period with long-window hours for {target['id']} at this cell"
        return record
    best, hours = int(top[0][0]), top[0][1]
    day = middle_day(best)
    path = earth_path(cell["lat"], day)
    record.update({"best_bin": best, "best_bin_label": bin_label(best), "best_bin_hours": hours,
                   "day_of_year": day, "date": sun.doy_to_label(day), "path": path,
                   "day_min_elevation_deg": min(path["elevation_deg"]),
                   "day_max_elevation_deg": max(path["elevation_deg"])})
    record.update(band_stats(cell["lat"], day, limit, ground["centre_deg"] if ground else None))
    if ground:
        median = band_stats(cell["lat"], day, limit, ground["cell_median_deg"])
        record["minutes_above_terrain_cell_median"] = median["minutes_above_terrain"]
        record["longest_spell_minutes_above_terrain_cell_median"] = median["longest_spell_minutes_above_terrain"]
    return record


# ---------------------------------------------------------------- the drawing

WIDTH, HEIGHT = 1200, 700
LEFT, RIGHT, TOP, BOTTOM = 84.0, 1070.0, 150.0, 548.0
ELEV_MIN, ELEV_MAX = -2.0, 12.0
MOON_COLOUR, EARTH_COLOUR, BAND_COLOUR, GROUND_COLOUR, INK = "#0072B2", "#D55E00", "#F0E442", "#8C7B6B", "#222222"
COMPASS = [(-180, "south"), (-135, "SW"), (-90, "west"), (-45, "NW"), (0, "north"), (45, "NE"), (90, "east"),
           (135, "SE"), (180, "south")]


def compass_x(azimuth_deg: float) -> float:
    """Azimuth as a place on an axis with north in the middle: -180 (south) through 0 (north) to 180 (south)."""
    return (azimuth_deg + 180.0) % 360.0 - 180.0


def pieces(xs, ys) -> list[list[tuple[float, float]]]:
    """A path as runs of points, cut wherever it jumps from one edge of the compass axis to the other."""
    runs: list[list[tuple[float, float]]] = [[]]
    for x, y in zip(xs, ys):
        if runs[-1] and abs(x - runs[-1][-1][0]) > 180.0:
            runs.append([])
        runs[-1].append((x, y))
    return [run for run in runs if run]


def _px(x_deg: float) -> float:
    return LEFT + (x_deg + 180.0) / 360.0 * (RIGHT - LEFT)


def _py(elev_deg: float) -> float:
    return BOTTOM - (elev_deg - ELEV_MIN) / (ELEV_MAX - ELEV_MIN) * (BOTTOM - TOP)


def _polyline(run, colour: str, width: float) -> str:
    points = " ".join(f"{_px(x):.1f},{_py(y):.1f}" for x, y in run)
    return (f'<polyline points="{points}" fill="none" stroke="{colour}" stroke-width="{width}" '
            f'stroke-linejoin="round" stroke-linecap="round" clip-path="url(#plot)"/>')


def _text(x: float, y: float, words: str, size: int = 14, colour: str = INK, anchor: str = "start",
          weight: str = "normal", extra: str = "") -> str:
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{colour}" text-anchor="{anchor}" '
            f'font-weight="{weight}"{extra}>{escape(words)}</text>')


def _arrow(x0: float, y0: float, x1: float, y1: float, colour: str, size: float = 9.0) -> str:
    """A small arrowhead at (x1, y1) pointing the way from (x0, y0), in pixels."""
    angle = math.atan2(y1 - y0, x1 - x0)
    tip = (x1 + size * math.cos(angle), y1 + size * math.sin(angle))
    left = (x1 + 0.6 * size * math.cos(angle + 2.2), y1 + 0.6 * size * math.sin(angle + 2.2))
    right = (x1 + 0.6 * size * math.cos(angle - 2.2), y1 + 0.6 * size * math.sin(angle - 2.2))
    points = " ".join(f"{x:.1f},{y:.1f}" for x, y in (tip, left, right))
    return f'<polygon points="{points}" fill="{colour}" clip-path="url(#plot)"/>'


def _hours_minutes(minutes) -> str:
    minutes = int(round(minutes))
    return f"{minutes // 60} h {minutes % 60:02d} min"


def _latitude(lat: float) -> str:
    return f"{abs(lat):.2f}° {'N' if lat >= 0 else 'S'}"


def _longitude(lon: float) -> str:
    lon = (lon + 180.0) % 360.0 - 180.0
    return f"{abs(lon):.2f}° {'E' if lon >= 0 else 'W'}"


def _plain_date(horizons_label: str, with_year: bool = True) -> str:
    """ "2026-Nov-09 16:00" as "9 Nov 2026"; a label of another shape is given back as it is."""
    try:
        year, month, day = horizons_label.split(" ")[0].split("-")
        return f"{int(day)} {month}" + (f" {year}" if with_year else "")
    except ValueError:
        return horizons_label


def _index_near(values, wanted: float) -> int:
    return min(range(len(values)), key=lambda i: abs(values[i] - wanted))


def svg(lunar: dict, place: dict) -> str:
    """The drawing: both Sun paths against compass direction, the band shaded, the Earth ground as a silhouette."""
    limit = lunar["ceiling_deg"]
    moon, sun_path = lunar["path"], place["path"]
    if sun_path is None:
        raise ValueError(f"no Sun path for {place['id']}: {place['path_missing_because']}")
    ground = place["terrain_horizon"]
    counted = {key: place[key] for key in ("minutes_in_band", "longest_spell_minutes", "minutes_above_terrain")}
    if place["band_deg"][1] != limit:       # drawn against another lunar site than the place was counted for
        counted = band_stats(place["cell_lat"], place["day_of_year"], limit, ground["centre_deg"] if ground else None)
    moon_x = [compass_x(a) for a in moon["azimuth_deg"]]
    earth_x = [compass_x(a) for a in sun_path["azimuth_deg"]]
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {HEIGHT}" width="{WIDTH}" height="{HEIGHT}" '
           f'font-family="Helvetica, Arial, sans-serif">',
           f'<rect width="{WIDTH}" height="{HEIGHT}" fill="#ffffff"/>',
           f'<defs><clipPath id="plot"><rect x="{LEFT}" y="{TOP}" width="{RIGHT - LEFT}" height="{BOTTOM - TOP}"/>'
           f'</clipPath></defs>',
           _text(LEFT, 36, "The Sun's path over the horizon: a lunar landing region and a place on Earth, on the same axes",
                 22, weight="bold")]

    # the key, in plain words
    rows = [
        (MOON_COLOUR, "line", f"Moon, {lunar['name']} ({_latitude(lunar['lat'])}): one trip takes "
                              f"{lunar['mean_trip_days']:.1f} days. Drawn: {_plain_date(moon['start_utc'], False)} to "
                              f"{_plain_date(moon['end_utc'])}, the trip with the year's highest Sun. A dot a day."),
        (EARTH_COLOUR, "line", f"Earth, {place['name']} ({_latitude(place['cell_lat'])}, "
                               f"{_longitude(place['cell_lon'])}), {place['date']}: one trip takes 24 hours. "
                               f"A dot an hour, local solar time."),
    ]
    if ground:
        rows.append((GROUND_COLOUR, "block", "Ground that hides the horizon at the Earth place, seen from the middle "
                                             "of its 10 km cell (dashed: middle value over the cell)."))
    else:
        rows.append((GROUND_COLOUR, "none", "Earth ground horizon not known for this cell, so none is drawn."))
    for i, (colour, kind, words) in enumerate(rows):
        y = 66 + 24 * i
        if kind == "line":
            out.append(f'<line x1="{LEFT}" y1="{y - 5}" x2="{LEFT + 34}" y2="{y - 5}" stroke="{colour}" stroke-width="3.5"/>')
            out.append(f'<circle cx="{LEFT + 17}" cy="{y - 5}" r="4" fill="{colour}"/>')
        elif kind == "block":
            out.append(f'<rect x="{LEFT}" y="{y - 13}" width="34" height="14" fill="{colour}" fill-opacity="0.6"/>')
        out.append(_text(LEFT + 44, y, words, 14))

    # the band, the grid and the axes
    out.append(f'<rect x="{LEFT}" y="{_py(limit):.1f}" width="{RIGHT - LEFT}" height="{_py(0.0) - _py(limit):.1f}" '
               f'fill="{BAND_COLOUR}" fill-opacity="0.32"/>')
    for elev in range(int(ELEV_MIN), int(ELEV_MAX) + 1, 2):
        out.append(f'<line x1="{LEFT}" y1="{_py(elev):.1f}" x2="{RIGHT}" y2="{_py(elev):.1f}" stroke="#bbbbbb" '
                   f'stroke-width="0.6"/>')
        out.append(_text(LEFT - 8, _py(elev) + 5, f"{elev}°", 13, anchor="end"))
    for x_deg, name in COMPASS:
        out.append(f'<line x1="{_px(x_deg):.1f}" y1="{BOTTOM}" x2="{_px(x_deg):.1f}" y2="{BOTTOM + 6}" stroke="{INK}"/>')
        out.append(_text(_px(x_deg), BOTTOM + 22, name, 13, anchor="middle"))
    out.append(_text((LEFT + RIGHT) / 2, BOTTOM + 44, "compass direction of the Sun", 14, anchor="middle"))
    out.append(_text(22, (TOP + BOTTOM) / 2, "height of the Sun above a level horizon", 14, anchor="middle",
                     extra=f' transform="rotate(-90 22 {(TOP + BOTTOM) / 2:.1f})"'))

    # the Earth ground, as a silhouette from the bottom of the chart up to the horizon in each direction
    if ground:
        def outline(values):
            centres = [compass_x(a) for a in ground["sector_centres_deg"]]
            order = sorted(range(len(centres)), key=lambda i: centres[i])
            xs, ys = [centres[i] for i in order], [values[i] for i in order]
            edge = (ys[0] + ys[-1]) / 2.0                    # due south lies between the last and the first sector
            return [-180.0] + xs + [180.0], [edge] + ys + [edge]
        xs, ys = outline(ground["centre_deg"])
        points = " ".join(f"{_px(x):.1f},{_py(y):.1f}" for x, y in zip(xs, ys))
        out.append(f'<polygon id="terrain" points="{_px(-180.0):.1f},{BOTTOM} {points} {_px(180.0):.1f},{BOTTOM}" '
                   f'fill="{GROUND_COLOUR}" fill-opacity="0.6" clip-path="url(#plot)"/>')
        xs, ys = outline(ground["cell_median_deg"])
        points = " ".join(f"{_px(x):.1f},{_py(y):.1f}" for x, y in zip(xs, ys))
        out.append(f'<polyline points="{points}" fill="none" stroke="#5a4d40" stroke-width="1.2" '
                   f'stroke-dasharray="5 4" clip-path="url(#plot)"/>')

    out.append(f'<line x1="{LEFT}" y1="{_py(0.0):.1f}" x2="{RIGHT}" y2="{_py(0.0):.1f}" stroke="{INK}" stroke-width="1.4"/>')
    out.append(f'<line x1="{LEFT}" y1="{_py(limit):.1f}" x2="{RIGHT}" y2="{_py(limit):.1f}" stroke="#8a7a00" '
               f'stroke-width="1.2" stroke-dasharray="7 4"/>')
    out.append(f'<rect x="{LEFT}" y="{TOP}" width="{RIGHT - LEFT}" height="{BOTTOM - TOP}" fill="none" stroke="{INK}"/>')
    roomy = _py(0.0) - _py(limit) >= 90.0       # a low ceiling leaves no room for words beside the band
    first_line = _py(limit) - (4 if roomy else 34)
    out.append(_text(RIGHT + 8, first_line, f"{limit:.2f}°: the Sun never", 12))
    out.append(_text(RIGHT + 8, first_line + 15, "climbs higher at", 12))
    out.append(_text(RIGHT + 8, first_line + 30, "this lunar site", 12))
    out.append(_text(RIGHT + 8, _py(0.0) + 4, "0°: level horizon", 12))
    if roomy:
        out.append(_text(RIGHT + 8, (_py(limit) + _py(0.0)) / 2 + 18, "the band the", 12, colour="#6b5f00"))
        out.append(_text(RIGHT + 8, (_py(limit) + _py(0.0)) / 2 + 33, "project looks for", 12, colour="#6b5f00"))

    # the Moon: one trip, a dot every 24 hours
    for run in pieces(moon_x, moon["elevation_deg"]):
        out.append(_polyline(run, MOON_COLOUR, 3.0))
    hours = moon["hours_since_start"]
    for day in range(1, int(hours[-1] // 24) + 1):
        i = _index_near(hours, 24.0 * day)
        out.append(f'<circle cx="{_px(moon_x[i]):.1f}" cy="{_py(moon["elevation_deg"][i]):.1f}" r="3.6" '
                   f'fill="{MOON_COLOUR}" stroke="#ffffff" stroke-width="0.8" clip-path="url(#plot)"/>')
        if day % 5 == 0 and moon["elevation_deg"][i] > ELEV_MIN + 0.9:
            out.append(_text(_px(moon_x[i]), _py(moon["elevation_deg"][i]) - 9, f"day {day}", 11, MOON_COLOUR, "middle"))
    i = _index_near(moon_x, 78.0)
    j = min(i + 6, len(moon_x) - 1)
    out.append(_arrow(_px(moon_x[i]), _py(moon["elevation_deg"][i]), _px(moon_x[j]), _py(moon["elevation_deg"][j]),
                      MOON_COLOUR))
    out.append(_text(RIGHT - 10, _py(limit) - 9,
                     f"Moon: highest Sun of {lunar['year']}, {lunar['year_max_elevation_deg']:.2f}° "
                     f"on {_plain_date(lunar['year_max_utc'], False)}", 13, MOON_COLOUR, "end", "bold"))

    # the Earth: 24 hours, a dot every hour
    for run in pieces(earth_x, sun_path["elevation_deg"]):
        out.append(_polyline(run, EARTH_COLOUR, 3.0))
    per_hour = round(1.0 / (sun_path["solar_time_h"][1] - sun_path["solar_time_h"][0]))
    for hour in range(24):
        i = hour * per_hour
        elev = sun_path["elevation_deg"][i]
        if not ELEV_MIN <= elev <= ELEV_MAX:
            continue
        out.append(f'<circle cx="{_px(earth_x[i]):.1f}" cy="{_py(elev):.1f}" r="3.6" fill="{EARTH_COLOUR}" '
                   f'stroke="#ffffff" stroke-width="0.8"/>')
        if hour == 0:
            out.append(_text(_px(earth_x[i]), _py(elev) + 18, "midnight", 11, EARTH_COLOUR, "middle"))
        elif hour in (3, 21):               # written on the outer side of the path, clear of the lunar one
            before_noon = hour < 12
            out.append(_text(_px(earth_x[i]) + (10 if before_noon else -10), _py(elev) + 4, f"{hour}:00", 11,
                             EARTH_COLOUR, "start" if before_noon else "end"))
    i = _index_near(sun_path["solar_time_h"], 1.0)
    out.append(_arrow(_px(earth_x[i]), _py(sun_path["elevation_deg"][i]), _px(earth_x[i + 3]),
                      _py(sun_path["elevation_deg"][i + 3]), EARTH_COLOUR))
    if place["day_max_elevation_deg"] > ELEV_MAX:
        leaves = next((k for k in range(len(earth_x)) if sun_path["elevation_deg"][k] > ELEV_MAX), 0)
        out.append(_text(min(_px(earth_x[leaves]) + 12, RIGHT - 250), TOP + 20,
                         f"Earth: the Sun climbs on to {place['day_max_elevation_deg']:.0f}° at noon,", 13,
                         EARTH_COLOUR, weight="bold"))
        out.append(_text(min(_px(earth_x[leaves]) + 12, RIGHT - 250), TOP + 37, "far off the top of this chart", 13,
                         EARTH_COLOUR, weight="bold"))

    # what the two paths come to, in words
    out.append(_text(LEFT, BOTTOM + 74,
                     f"Moon: the Sun's centre is above a level horizon for {lunar['path_days_above_level_horizon']:.1f} "
                     f"of the {lunar['path_trip_days']:.1f} days of this trip. A smooth Moon is assumed: lunar hills are "
                     f"not drawn.", 14, MOON_COLOUR))
    words = f"Earth: the Sun is inside the band for {_hours_minutes(counted['minutes_in_band'])} of this "
    if counted["longest_spell_minutes"] > counted["minutes_in_band"]:
        # the spell is joined across midnight with the minutes of the next (or the last) day, so it can be longer
        # than the minutes of the calendar day; said in so many words, or the two numbers read as a mistake
        words += (f"calendar day; one unbroken spell runs through midnight and lasts "
                  f"{_hours_minutes(counted['longest_spell_minutes'])}")
    else:
        words += f"day, at most {_hours_minutes(counted['longest_spell_minutes'])} without a break"
    if counted["minutes_above_terrain"] is not None:
        words += f"; clear of the ground for {_hours_minutes(counted['minutes_above_terrain'])}"
    out.append(_text(LEFT, BOTTOM + 96, words + ".", 14, EARTH_COLOUR))
    out.append(_text(LEFT, HEIGHT - 14, CAPTION, 11, "#555555"))
    out.append("</svg>")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------- the run

def write_text(path: Path, text: str) -> None:
    path = Path(path)
    side = path.with_name(path.name + ".part")
    side.write_text(text, encoding="utf-8")
    os.replace(side, path)


def _file_time(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%dT%H:%M:%S")


def meta_block(raw_files: dict, headers: dict, top_cell: tuple[float, float]) -> dict:
    return {
        "written": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "written_by": "scripts/build_sunpath_demo.py (code written with AI assistance)",
        "run_again": "uv run python scripts/build_sunpath_demo.py [--preview some.svg]",
        "caption_for_any_drawing": CAPTION,
        "angles": "degrees; azimuth 0 = north, clockwise; elevation of the Sun's centre above a level horizon",
        "lunar_sites": {
            "source": "NASA/JPL Horizons API, " + HORIZONS_API,
            "asked_for": "the Sun (10) seen from a point on the Moon (CENTER coord@301), quantity 4 (apparent azimuth "
                         "and elevation), APPARENT = AIRLESS (no refraction), one row an hour",
            "point": "the centre of each target from data/derived/moon_targets.json (centre_lon as east longitude, "
                     f"centre_lat), height {SITE_HEIGHT_KM:g} km on the 1737.4 km sphere",
            "span": f"{START} to {STOP} UT; year figures use the rows of {YEAR} only",
            "what_horizons_says": headers,
            "raw_files": raw_files,
            "ceiling": "the project's band limit for the site, 90 - |latitude of the centre| + 1.54, to two decimals",
            "mean_trip_days": f"days of {YEAR} covered by the rows, over the turns the azimuth made in them",
            "shortest_trip_days, longest_trip_days": "over every whole trip, due south to due south, in the span",
            "path": "the trip from due south (azimuth 180) back to due south that holds the hour of the year's "
                    "highest Sun; start and end are read between the hourly rows; hours_since_start counts from "
                    "the start of the trip",
            "not_in_these_numbers": "lunar terrain (a smooth sphere is assumed, so no hill hides or uncovers the "
                                    "Sun) and the width of the Sun's disc (0.53 degrees; the centre is given)",
        },
        "earth_places": {
            "chosen": ["Haughton crater, Devon Island (75.38 N, 89.67 W): the grid cell that holds it",
                       f"the first row of the list 'Low Sun on bare ground | Malapert Massif | all sites' of "
                       f"{RANKING} as it was at {_file_time(RANKING)}: {top_cell[0]}, {top_cell[1]}"],
            "day": f"the middle day of the cell's best ten-day period for the {EARTH_TARGET} target: the first entry "
                   f"of targets.{EARTH_TARGET}.top_bins in {GRAZING} as it was at {_file_time(GRAZING)}",
            "path": f"twinfinder.sun.elevation_azimuth at the latitude of the cell centre, every {PATH_STEP_MINUTES} "
                    "minutes of local solar time (0 = midnight, 12 = noon); elevation_deg is apparent "
                    "(sun.apparent_elevation_deg, Saemundsson refraction at 10 C and 1010 hPa), true_elevation_deg "
                    "is without the air; a typical year, not one calendar year",
            "band_deg": "above 0 and at or below the ceiling of the lunar target",
            "minutes_in_band": f"minutes of that day (counted at the middle of each {COUNT_STEP_MINUTES}-minute "
                               "step) with the apparent centre of the Sun in the band, level horizon",
            "longest_spell_minutes": "the longest unbroken run of such minutes that touches the day; a run through "
                                     "midnight counts in full, as one, but never as more than 1440",
            "minutes_above_terrain": "the same minutes with the Sun also above terrain_horizon.centre_deg in the "
                                     "10-degree sector it stands in (sector k runs from 10k degrees); "
                                     "..._cell_median uses cell_median_deg instead",
            "terrain_horizon": f"twinfinder.horizon.horizon_deg on twinfinder.earth.elevation_window: Copernicus "
                               f"GLO-90 on a {PIXEL_M:g} m local grid, the 10 km cell and {REACH_KM:g} km of ground "
                               f"around it, eye {EYE_M:g} m above the ground, Earth curve and standard refraction "
                               "taken off; one value at the centre of each 10-degree sector; centre_deg is the view "
                               "from the pixel at the cell centre, cell_median_deg (and p10, p90) the spread over "
                               "the cell's land pixels; north_deg and south_deg are the cell medians due north and "
                               "due south, as in horizon_cells.json; tiles are read from data/raw/glo90 only",
        },
    }


def main(argv=None) -> dict:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--preview", type=Path, help="also write the drawing to this SVG file")
    parser.add_argument("--preview-lunar", default="malapert", choices=LUNAR_IDS)
    parser.add_argument("--preview-earth", default="haughton", choices=("haughton", "top-cell"))
    parser.add_argument("--refetch", action="store_true", help="ask JPL Horizons again even if the answers are on disk")
    args = parser.parse_args(argv)

    targets = {t["id"]: t for t in json.loads(MOON_TARGETS.read_text())}
    lunar, raw_files, headers = [], {}, {}
    for tid in LUNAR_IDS:
        target = targets[tid]
        before = time.monotonic()
        raw = fetch_horizons(tid, target["centre_lon"], target["centre_lat"], refetch=args.refetch)
        if time.monotonic() - before > 0.5:
            time.sleep(2.0)             # a server was asked: one request after another, with a pause
        series = parse_horizons(raw.read_text(encoding="utf-8", errors="replace"))
        lunar.append(lunar_record(target, series))
        raw_files[tid] = str(raw)
        headers[tid] = series["header"]

    cells = json.loads(GRAZING.read_text())["cells"]
    top_lat, top_lon = ranking_top_cell(RANKING.read_text(), targets[EARTH_TARGET]["name"])
    top_cell = find_cell(cells, top_lat, top_lon)
    top_place = {"id": "top-cell", "name": f"top-ranked cell, {top_cell.get('region') or 'region not named'}",
                 "why": "heads the Malapert lighting list (Low Sun on bare ground, all sites) of ranking.txt",
                 "place_lat": top_cell["lat"], "place_lon": top_cell["lon"]}
    earth.fetch_optional = cached_or_ocean      # from here on the elevation code can only read tiles already on disk
    places = [earth_record(HAUGHTON, cell_holding(cells, HAUGHTON["place_lat"], HAUGHTON["place_lon"]),
                           targets[EARTH_TARGET]),
              earth_record(top_place, top_cell, targets[EARTH_TARGET])]

    result = {"meta": meta_block(raw_files, headers, (top_lat, top_lon)), "lunar_sites": lunar, "earth_places": places}
    write_text(OUT, json.dumps(result, separators=(",", ":"), allow_nan=False))
    print(f"wrote {OUT}")
    for site in lunar:
        print(f"  Moon, {site['name']}: highest Sun of {site['year']} {site['year_max_elevation_deg']:.3f} deg on "
              f"{site['year_max_utc']} UT (ceiling {site['ceiling_deg']:.2f}, difference "
              f"{site['year_max_minus_ceiling_deg']:+.3f}); one trip {site['mean_trip_days']:.2f} days on average, "
              f"{site['path_trip_days']:.2f} days for the trip stored (from {site['path']['start_utc']} UT); "
              f"{site['direction']}")
    for place in places:
        if place["path"] is None:
            print(f"  Earth, {place['name']}: no path ({place['path_missing_because']})")
            continue
        ground = place["terrain_horizon"]
        print(f"  Earth, {place['name']} (cell {place['cell_id']}): {place['date']} (day {place['day_of_year']}, "
              f"best period {place['best_bin_label']}); Sun {place['day_min_elevation_deg']:.2f} to "
              f"{place['day_max_elevation_deg']:.2f} deg; in the band {place['minutes_in_band']} min, longest spell "
              f"{place['longest_spell_minutes']} min; above the ground at the centre "
              f"{place['minutes_above_terrain']} min; horizon "
              + (f"north {ground['north_deg']} south {ground['south_deg']} deg (cell medians)" if ground
                 else f"unknown: {place['terrain_horizon_missing_because']}"))
    if args.preview:
        chosen = next(site for site in lunar if site["id"] == args.preview_lunar)
        place = next(p for p in places if p["id"] == args.preview_earth)
        write_text(args.preview, svg(chosen, place))
        print(f"wrote {args.preview}")
    return result


if __name__ == "__main__":
    main()

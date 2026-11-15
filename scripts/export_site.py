"""Write the files the map page reads (site/data) from data/derived and data/reference.

    uv run python scripts/export_site.py

Only numpy and the standard library. The pipeline files are read, never written. Fields that the
third version of the pipeline adds (per-day long spells, both snow figures, cloud) are used when they
are there and left as unknown when they are not. Unknown is written as 255 in the byte files, as -1 in
the integer columns of cells.json and as null elsewhere; it is never written as 0.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
HALF_HOUR = 0.5        # one unit of the byte files
CAP = 254              # largest value a byte holds (127 h in a ten-day period)
UNKNOWN = 255
N_BINS = 36
BIN_DAYS = 10
LAND_LIMIT_DEG = 50.0  # the land outline is cut here
LAND_SCALE = 100       # land coordinates are whole hundredths of a degree
LAND_MAX_BYTES = 480_000
YEARLY_FIELDS = ["snow_free", "snow_free_winter", "open", "open_winter", "clear", "clear_winter",
                 "terrain", "lighting", "full",
                 "snow_free_summer", "open_summer", "clear_summer"]   # per cell and target, in yearly.bin
YEARLY_SCALE = {"terrain": 1000, "lighting": 1000, "full": 1000}   # the rest are hours, in tenths
YEARLY_UNKNOWN = 65535
EARTH_KM = 6371.0
SYNODIC_MONTH_DAYS = 29.530589   # at a lunar pole the Sun goes once round the horizon in this time
MOTION_LATS = (60, 70, 80)       # Earth latitudes at which the Sun's sideways pace is quoted
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
HEADLINE = "Where and when Earth copies the low Sun of the Moon's south pole"
PURPOSE = ("For choosing where and when to rehearse rover driving, cameras and crew work under the light of the "
           "Moon's south pole.")
SUBLINE = ("A map and a calendar of the places and dates where the Sun stays that low over bare, snow-free ground. "
           "It copies the Sun's height and the length of the shadows, not the hard contrast of a world without air.")
# Used only when data/derived/moon_cards.json is missing; with it the official names come from that file.
SHORT_NAMES = {"connecting-ridge": "Connecting ridge", "malapert": "Malapert", "mons-mouton": "Mons Mouton",
               "nobile-rim-2": "Nobile Rim 2"}
ONE_SET_FROM_SHARE = 0.97   # the calendar sums every step over the areas with a horizon once this share has one
SCALE_QUANTILE = 0.99       # the colour scale tops out at this quantile of the hours, over all the lunar regions
NICE_STEPS = [5, 10, 20, 30, 40, 50, 60, 80, 100, 150, 200, 250, 300, 400, 500, 600, 800, 1000, 1200, 1500, 2000]
NO_TERRAIN = "no terrain figure"
SOURCES = [
    {"name": "NASA LRO LOLA 5 m terrain models of the lunar south pole (NASA PGDA)",
     "used_for": "the highest Sun at the lunar regions with a NASA 5 m terrain model, and their slopes",
     "url": "https://pgda.gsfc.nasa.gov/products/78"},
    {"name": "NOAA / U.S. National Ice Center IMS daily snow and ice maps, 4 km (NSIDC G02156)",
     "used_for": "the snow-free odds, October 2015 to September 2025",
     "url": "https://nsidc.org/data/g02156"},
    {"name": "ESA WorldCover 2021, 10 m land cover",
     "used_for": "the share of bare ground in each northern area",
     "url": "https://esa-worldcover.org/"},
    {"name": "SCAR Antarctic Digital Database rock outcrop layers",
     "used_for": "bare rock in each Antarctic area",
     "url": "https://www.add.scar.org/"},
    {"name": "Copernicus DEM GLO-90 (ESA, open licence)",
     "used_for": "the terrain horizon around each area and its slopes",
     "url": "https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM"},
    {"name": "NASA POWER monthly cloud amount",
     "used_for": "typical cloud for each area and month",
     "url": "https://power.larc.nasa.gov/"},
    {"name": "NOAA GHCN-Daily weather stations",
     "used_for": "checking the satellite snow odds against snow depth on the ground",
     "url": "https://www.ncei.noaa.gov/products/land-based-station/global-historical-climatology-network-daily"},
    {"name": "Natural Earth 1:50m land (public domain)",
     "used_for": "the land outline on the map",
     "url": "https://www.naturalearthdata.com/"},
]


# ---- small helpers ----

def read_json(path: Path, default=None):
    """A JSON file, or the default when it is not there."""
    if not path.exists():
        return default
    with open(path) as handle:
        return json.load(handle)


def write_bytes(path: Path, data: bytes) -> None:
    """Write beside the target and rename, so a reader never sees half a file."""
    side = path.with_name(path.name + ".part")
    side.write_bytes(data)
    os.replace(side, path)


def write_json(path: Path, value) -> None:
    write_bytes(path, json.dumps(value, separators=(",", ":"), allow_nan=False).encode())


def known(value) -> bool:
    return value is not None and not (isinstance(value, float) and math.isnan(value))


def scaled(value, factor: float) -> int:
    """A whole number of 1/factor units; -1 when the value is unknown."""
    return int(round(float(value) * factor)) if known(value) else -1


def scaled_or_none(value, factor: float):
    return int(round(float(value) * factor)) if known(value) else None


def number_list(values, digits: int = 1) -> list:
    """Plain floats for JSON; an unknown value becomes null."""
    return [round(float(v), digits) if np.isfinite(v) else None for v in values]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = (math.sin((p2 - p1) / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2)
    return 2 * EARTH_KM * math.asin(min(1.0, math.sqrt(a)))


def horizon_note_label(reason: str) -> str:
    """What the page says of an area without a terrain horizon.

    The pipeline's reasons are long and speak of files and downloads; the public page says "no terrain
    figure" and adds a reason only where the reason is a fact about the place.
    """
    text = str(reason)
    if "antimeridian" in text:
        return NO_TERRAIN + ": the area lies on the date line"
    if "no land" in text:
        return NO_TERRAIN + ": no land in the terrain model"
    return NO_TERRAIN


def plain_reason(reason: str) -> str:
    """One of the pipeline's reasons for not ranking an area, in the page's words."""
    text = str(reason).strip()
    if "antimeridian" in text:
        return NO_TERRAIN + " (on the date line)"
    if text.startswith("no horizon") or "not fetched" in text:
        return NO_TERRAIN
    bare = re.fullmatch(r"bare under ([0-9.]+)", text)
    if bare:
        return f"less than {float(bare.group(1)) * 100:g}% bare ground"
    if "outside the screen" in text:
        return "a named place outside the search"
    return text.replace("cell", "area")


def nice_ceiling(value: float) -> int:
    """The first round figure at or above a value (the top of a colour scale)."""
    for step in NICE_STEPS:
        if step >= value:
            return step
    return int(math.ceil(value / 500.0) * 500)


def one_set(with_horizon: int, cells: int) -> bool:
    """Whether the calendar can sum all four steps over the areas that have a terrain horizon."""
    return cells > 0 and with_horizon / cells >= ONE_SET_FROM_SHARE


SEARCH_FROM_DEG = 59.0   # the southern edge of the northern search (twinfinder/grid.py MIN_LAT)


def lists_of(card: dict | None) -> list[str]:
    """The NASA lists of candidate regions that a lunar region is on, as short labels for the page."""
    on = (card or {}).get("nasa_list") or {}
    return ([label for label, key in (("NASA 2024 list", "on_2024_list_of_9"), ("NASA 2022 list", "on_2022_list_of_13"))
             if on.get(key)])


def names_in_words(names: list[str]) -> str:
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def hills_page_text(rows: list[dict]) -> str | None:
    """The sentence on the page that says which lunar regions have a lower bound for the hours after hills."""
    low = [r["name"] for r in rows if r.get("hills_exact") is False]
    if not low:
        return None
    exact = [r["name"] for r in rows if r.get("hills_exact") is True]
    text = (f"For {len(low)} of the {len(rows)} lunar regions, the hours after hills are a lower bound. The project "
            "has the horizons of the areas at nine bins of Sun height only. A new run of the horizon step at each Sun "
            "ceiling can increase these hours.")
    if exact:
        # not "exact": these regions use the full method of the first build, and that method is an approximation
        text += f" For {names_in_words(exact)}, these hours use the full method of the first build."
    return text


def south_of_search_text(rows: list[dict], headline: dict, search_from: float) -> str | None:
    """One sentence that names the regions whose two-hour spells start south of the edge of the search."""
    south = [(r["name"], headline[r["id"]]["first_latitude_with_spells"]) for r in rows
             if (headline.get(r["id"]) or {}).get("first_latitude_with_spells") is not None
             and headline[r["id"]]["first_latitude_with_spells"] < search_from]
    if not south:
        return None
    return (f"For {names_in_words([name for name, _ in south])}, a strip of Earth south of {search_from:g} degrees "
            "north also has spells of 2 hours, but the search does not include it.")


def list_line(card: dict) -> str | None:
    """One sentence on where a lunar site stands on NASA's two lists of candidate regions."""
    on = card.get("nasa_list") or {}
    if not on.get("on_2022_list_of_13"):
        return None
    old = on.get("name_2022")
    first = "On NASA's 2022 list of 13 candidate regions"
    if old and old != card.get("official_name"):
        first += f" as {old}"
    new = on.get("name_2024")
    if on.get("on_2024_list_of_9") and old and new and old != new:
        # a 2022 box with another name on the 2024 map (Leibnitz Beta Plateau and Mons Mouton): say what the map shows
        return (f"It is on the NASA list of 13 candidate regions of 2022, as {old}. The NASA map of the nine regions "
                f"of 28 October 2024 has the box {new} at the place of the 2022 box {old}.")
    if on.get("on_2024_list_of_9"):
        second = "among the nine kept in 2024"
    else:
        second = "not among the nine kept in 2024"
    return f"{first}; {second}."


def sun_motion(spell_h: float) -> dict:
    """How fast the Sun's compass direction moves near the horizon, in degrees an hour.

    On Earth about 15 x sin(latitude); at a lunar pole 360 degrees in a synodic month. The places on the
    page match the Sun's height and the shadow length, not this pace, and the page has to say so.
    """
    moon = 360.0 / (SYNODIC_MONTH_DAYS * 24.0)
    earth = {str(lat): 15.0 * math.sin(math.radians(lat)) for lat in MOTION_LATS}
    shown = {k: round(v, 1) for k, v in earth.items()}
    return {"moon_deg_per_hour": round(moon, 3), "earth_deg_per_hour": shown,
            "times_faster_on_earth": {k: round(v / moon, 1) for k, v in earth.items()},
            "swing_in_one_spell_deg": {"spell_h": spell_h,
                                       "earth": [round(spell_h * min(shown.values())),
                                                 round(spell_h * max(shown.values()))],
                                       "moon": round(spell_h * moon, 1)}}


# ---- encoding ----

def encode_hours(hours) -> np.ndarray:
    """Hours as bytes in units of half an hour, at most 254; unknown (NaN) is 255."""
    hours = np.asarray(hours, dtype=np.float64)
    out = np.full(hours.shape, UNKNOWN, dtype=np.uint8)
    seen = np.isfinite(hours)
    out[seen] = np.clip(np.rint(hours[seen] / HALF_HOUR), 0, CAP).astype(np.uint8)
    return out


def decode_hours(coded) -> np.ndarray:
    """The reverse of encode_hours: hours, NaN where the byte says unknown."""
    coded = np.asarray(coded)
    return np.where(coded == UNKNOWN, np.nan, coded.astype(np.float64) * HALF_HOUR)


def encode_yearly(value, field: str) -> int:
    """One value of yearly.bin: tenths of an hour or thousandths of a score; unknown is 65535."""
    if not known(value):
        return YEARLY_UNKNOWN
    return int(min(max(round(float(value) * YEARLY_SCALE.get(field, 10)), 0), YEARLY_UNKNOWN - 1))


def read_yearly(folder: Path, n: int, targets: list[str]) -> dict:
    """yearly.bin back as {target: {field: values}}, NaN where unknown (used by the tests)."""
    raw = np.frombuffer((Path(folder) / "yearly.bin").read_bytes(), dtype="<u2").reshape(n, len(targets),
                                                                                       len(YEARLY_FIELDS))
    out = {}
    for t, target in enumerate(targets):
        out[target] = {}
        for f, field in enumerate(YEARLY_FIELDS):
            column = raw[:, t, f].astype(np.float64)
            out[target][field] = np.where(raw[:, t, f] == YEARLY_UNKNOWN, np.nan,
                                          column / YEARLY_SCALE.get(field, 10))
    return out


def encode_percent(share) -> np.ndarray:
    """A share from 0 to 1 as whole percent; unknown is 255."""
    share = np.asarray(share, dtype=np.float64)
    out = np.full(share.shape, UNKNOWN, dtype=np.uint8)
    seen = np.isfinite(share)
    out[seen] = np.clip(np.rint(share[seen] * 100.0), 0, 100).astype(np.uint8)
    return out


# ---- the calendar ----

def _day_label(day_of_year: int) -> str:
    day = date(2025, 1, 1) + timedelta(days=day_of_year - 1)   # a year without a leap day
    return f"{day.day} {MONTHS[day.month - 1]}"


def bin_table() -> list[dict]:
    """The 36 ten-day periods of the year; the last one runs to 31 December."""
    table = []
    for index in range(N_BINS):
        first = index * BIN_DAYS + 1
        last = first + BIN_DAYS - 1 if index < N_BINS - 1 else 365
        middle = date(2025, 1, 1) + timedelta(days=first + (last - first) // 2 - 1)
        table.append({"label": f"{_day_label(first)}-{_day_label(last)}", "first_day": first, "last_day": last,
                      "month": middle.month})
    return table


def clear_share_by_bin(cloud_pct) -> list[float]:
    """Clear share (1 - cloud / 100) of each ten-day period, taken from the month of its middle day."""
    out = []
    for row in bin_table():
        value = cloud_pct[row["month"] - 1] if cloud_pct is not None else None
        out.append(1.0 - float(value) / 100.0 if known(value) else float("nan"))
    return out


def season_text(bins: list[int]) -> str:
    """'28 September to 31 March' for a run of periods that may wrap over the new year."""
    table = bin_table()
    inside = set(bins)
    first = next((b for b in bins if (b - 1) % N_BINS not in inside), bins[0])
    last = next((b for b in bins if (b + 1) % N_BINS not in inside), bins[-1])
    long_month = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
                  "October", "November", "December"]

    def words(day_of_year: int) -> str:
        day = date(2025, 1, 1) + timedelta(days=day_of_year - 1)
        return f"{day.day} {long_month[day.month - 1]}"

    return f"{words(table[first]['first_day'])} to {words(table[last]['last_day'])}"


# ---- long spells per ten-day period ----

def hours_in_words(hours: float) -> str:
    """The length of a spell as the page prints it: "two hours", "one hour", "1.5 hours"."""
    small = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve"]
    if float(hours).is_integer() and 0 <= hours < len(small):
        return f"{small[int(hours)]} {'hour' if int(hours) == 1 else 'hours'}"
    return f"{hours:g} hours"


def long_window_arrays(archive, stretch_min_h: float) -> tuple[np.ndarray, np.ndarray, np.ndarray, str]:
    """Hours inside spells of at least two hours per cell, target and period: flat, snow-free, open.

    The third version of the pipeline stores them (spells counted day by day). Before that, a period
    counts in full when its median longest spell reaches the minimum, and not at all otherwise.
    """
    names = ("long_flat", "long_snow_free", "long_open")
    if all(name in archive.files for name in names):
        return archive[names[0]], archive[names[1]], archive[names[2]], "per-day spells"
    counted = archive["stretch"] >= stretch_min_h
    flat, snow_free, opened = (np.where(counted, archive[name], np.float32(0.0)) for name in ("flat", "snow_free", "open"))
    return flat, snow_free, opened, "ten-day periods whose median longest spell reaches the minimum (version 2 rule)"


def snow_odds(archive) -> np.ndarray:
    """Snow-free odds per cell and period, read back from the hours the pipeline wrote.

    Snow-free hours are flat hours times the odds, so their ratio is the odds the pipeline used. A
    period with no low Sun at all has no ratio; it is left unknown (the odds do not matter there).
    """
    flat = archive["flat"].astype(np.float64)
    snow_free = archive["snow_free"].astype(np.float64)
    widest = flat.argmax(axis=1)[:, None, :]
    top = np.take_along_axis(flat, widest, axis=1)[:, 0, :]
    part = np.take_along_axis(snow_free, widest, axis=1)[:, 0, :]
    odds = np.full(top.shape, np.nan)
    usable = (top >= 0.05) & np.isfinite(part)
    odds[usable] = np.clip(part[usable] / top[usable], 0.0, 1.0)
    return odds


# ---- land outline ----

def clip_ring(ring: list, limit_deg: float, north: bool) -> list:
    """The part of a closed ring poleward of a parallel (Sutherland-Hodgman against one line)."""
    sign = 1.0 if north else -1.0

    def inside(point) -> bool:
        return sign * point[1] >= limit_deg

    def crossing(a, b) -> list:
        share = (sign * limit_deg - a[1]) / (b[1] - a[1])
        return [a[0] + share * (b[0] - a[0]), sign * limit_deg]

    points = ring[:-1] if len(ring) > 1 and ring[0] == ring[-1] else ring
    out = []
    for index, here in enumerate(points):
        before = points[index - 1]
        if inside(here):
            if not inside(before):
                out.append(crossing(before, here))
            out.append([float(here[0]), float(here[1])])
        elif inside(before):
            out.append(crossing(before, here))
    if len(out) < 3:
        return []
    out.append(list(out[0]))
    return out


def _along_the_cut(ring: list, limit_deg: float, north: bool, step_deg: float = 2.0) -> list:
    """Add points along the cut, so that it is drawn as an arc of the parallel and not as a chord."""
    edge = limit_deg if north else -limit_deg
    out = [ring[0]]
    for here in ring[1:]:
        before = out[-1]
        if abs(before[1] - edge) < 1e-9 and abs(here[1] - edge) < 1e-9 and abs(here[0] - before[0]) > step_deg:
            pieces = int(math.ceil(abs(here[0] - before[0]) / step_deg))
            for k in range(1, pieces):
                out.append([before[0] + (here[0] - before[0]) * k / pieces, edge])
        out.append(here)
    return out


def _polar_km(lon: float, lat: float, north: bool) -> tuple[float, float]:
    """Polar stereographic position in kilometres (sphere), for thinning only."""
    colat = math.radians(90.0 - (lat if north else -lat))
    r = 2.0 * EARTH_KM * math.tan(colat / 2.0)
    a = math.radians(lon)
    return r * math.sin(a), -r * math.cos(a)


def _thin(points: list, tolerance_km: float) -> list:
    """Douglas-Peucker on projected points; returns the indices kept."""
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        first, last = stack.pop()
        if last - first < 2:
            continue
        (x1, y1), (x2, y2) = points[first], points[last]
        dx, dy = x2 - x1, y2 - y1
        length = math.hypot(dx, dy)
        worst, where = 0.0, -1
        for index in range(first + 1, last):
            px, py = points[index]
            if length == 0.0:
                distance = math.hypot(px - x1, py - y1)
            else:
                distance = abs(dy * (px - x1) - dx * (py - y1)) / length
            if distance > worst:
                worst, where = distance, index
        if worst > tolerance_km:
            keep[where] = True
            stack.append((first, where))
            stack.append((where, last))
    return [index for index, kept in enumerate(keep) if kept]


def land_outline(path: Path | None) -> dict:
    """Land rings poleward of 50 degrees for the two polar views, thinned to stay under the size limit.

    Each ring is a flat list lon, lat, lon, lat ... in whole hundredths of a degree; the last point
    repeats the first. Points at a pole (the frame of the Antarctic polygon) are dropped.
    """
    empty = {"scale": LAND_SCALE, "limit_deg": LAND_LIMIT_DEG, "north": [], "south": [],
             "source": "Natural Earth 1:50m land (public domain), naturalearthdata.com", "tolerance_km": None}
    if path is None or not Path(path).exists():
        empty["source"] += "; file not found when the page data was exported"
        return empty
    with open(path) as handle:
        features = json.load(handle)["features"]
    raw = {"north": [], "south": []}
    for feature in features:
        geometry = feature.get("geometry") or {}
        polygons = geometry.get("coordinates", [])
        if geometry.get("type") == "Polygon":
            polygons = [polygons]
        for polygon in polygons:
            if not polygon:
                continue
            outer = [[float(p[0]), float(p[1])] for p in polygon[0] if abs(p[1]) < 89.99]
            for side, north in (("north", True), ("south", False)):
                if not any((p[1] if north else -p[1]) >= LAND_LIMIT_DEG for p in outer):
                    continue
                cut = clip_ring(outer, LAND_LIMIT_DEG, north)
                if cut:
                    raw[side].append(_along_the_cut(cut, LAND_LIMIT_DEG, north))
    tolerance, smallest = 1.0, 4.0
    while True:
        out = dict(empty, tolerance_km=round(tolerance, 2), smallest_island_km=round(smallest, 1))
        for side, north in (("north", True), ("south", False)):
            rings = []
            for ring in raw[side]:
                projected = [_polar_km(lon, lat, north) for lon, lat in ring]
                xs, ys = [p[0] for p in projected], [p[1] for p in projected]
                if math.hypot(max(xs) - min(xs), max(ys) - min(ys)) < smallest:
                    continue
                kept = _thin(projected, tolerance)
                if len(kept) < 4:
                    continue
                flat = []
                for index in kept:
                    lon, lat = ring[index]
                    lat = max(lat, LAND_LIMIT_DEG) if north else min(lat, -LAND_LIMIT_DEG)
                    flat.extend((int(round(lon * LAND_SCALE)), int(round(lat * LAND_SCALE))))
                rings.append(flat)
            out[side] = rings
        if len(json.dumps(out, separators=(",", ":"))) < LAND_MAX_BYTES:
            return out
        tolerance *= 1.25
        smallest *= 1.25


# ---- top lists ----

def cluster(rows: list[int], lat, lon, key, tie, limit: int, min_km: float) -> list[int]:
    """Best rows first, leaving out any row within min_km of a better one already kept (as score.cluster_sites)."""
    kept: list[int] = []
    scored = [r for r in rows if known(key(r)) and key(r) > 0.0]
    for row in sorted(scored, key=lambda r: (key(r), tie(r) if known(tie(r)) else 0.0), reverse=True):
        if len(kept) >= limit:
            break
        if all(haversine_km(lat[row], lon[row], lat[k], lon[k]) >= min_km for k in kept):
            kept.append(row)
    return kept


# ---- the export ----

def export(derived: Path, reference: Path, land_file: Path | None, out: Path) -> dict:
    """Write every file of site/data and return the content of meta.json."""
    derived, reference, out = Path(derived), Path(reference), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    grazing = read_json(derived / "grazing_cells.json")
    if grazing is None:
        raise SystemExit(f"{derived / 'grazing_cells.json'} is missing")
    archive = np.load(derived / "grazing_bins.npz", allow_pickle=False)
    cells = grazing["cells"]
    gmeta = grazing["meta"]
    ids = [c["id"] for c in cells]
    if ids != [str(i) for i in archive["ids"]]:
        raise SystemExit("grazing_cells.json and grazing_bins.npz do not list the same cells in the same order; "
                         "the pipeline may be in the middle of a run, try again")
    n = len(cells)
    targets = [t["id"] for t in gmeta["targets"]]
    if targets != [str(t) for t in archive["targets"]]:
        raise SystemExit("grazing_cells.json and grazing_bins.npz do not list the same targets")
    stretch_min = float(gmeta.get("stretch_min_h", 2.0))
    winter = list(gmeta["winter_bins_north"])
    summer = list(gmeta["summer_bins_north"])
    rock_season = list(gmeta["summer_bins_south"])
    bins = bin_table()

    scored_file = read_json(derived / "cells_scored.json", {"meta": {}, "cells": []})
    scored = {c["id"]: c for c in scored_file.get("cells", [])}
    smeta = scored_file.get("meta", {})
    validation = read_json(derived / "validation.json", {})
    profile_in = read_json(derived / "latitude_profile.json")
    moon = {t["id"]: t for t in read_json(derived / "moon_targets.json", [])}
    cards = {c["id"]: c for c in (read_json(derived / "moon_cards.json", {}) or {}).get("cards", [])}
    cloud_file = read_json(derived / "cloud_cells.json")
    antarctic = {s["name"]: s for s in read_json(reference / "antarctic_sites.json", [])}

    long_flat, long_snow, long_open, rule = long_window_arrays(archive, stretch_min)
    long_flat64 = long_flat.astype(np.float64)
    long_snow64 = long_snow.astype(np.float64)
    long_open64 = long_open.astype(np.float64)

    lat = np.array([c["lat"] for c in cells], dtype=np.float64)
    lon = np.array([c["lon"] for c in cells], dtype=np.float64)
    north = np.array([c["hemisphere"] == "N" for c in cells])
    gridded = np.array([bool(c.get("gridded", True)) for c in cells])
    status = [c["snow"]["status"] for c in cells]
    km2 = np.array([float(c.get("bare_km2") or 0.0) for c in cells])
    has_horizon = np.array([isinstance(c.get("horizon"), dict) and "north_deg" in c["horizon"] for c in cells])

    # ---- cloud ----
    has_cloud = cloud_file is not None
    clear = np.full((n, N_BINS), np.nan)
    cloud_pct = np.full((n, 12), np.nan)
    if has_cloud:
        for i, cid in enumerate(ids):
            months = (cloud_file["cells"].get(cid) or {}).get("cloud_pct")
            if months is None and cid in scored:
                months = (scored[cid].get("cloud") or {}).get("pct_by_month")
            if months is None:
                continue
            cloud_pct[i] = [float(v) if known(v) else np.nan for v in months]
            clear[i] = clear_share_by_bin(months)
        write_bytes(out / "cloud.bin", encode_percent(cloud_pct / 100.0).tobytes())
    elif (out / "cloud.bin").exists():
        (out / "cloud.bin").unlink()
    # clear-sky hours per period: unknown where the open hours or the cloud are unknown
    long_clear64 = long_open64 * clear[:, None, :]
    long_clear64[(long_open64 == 0.0) & np.isnan(clear)[:, None, :]] = 0.0

    # ---- byte files ----
    write_bytes(out / "snowfree.bin", encode_hours(long_snow64).tobytes())
    write_bytes(out / "open.bin", encode_hours(long_open64).tobytes())
    write_bytes(out / "snowodds.bin", encode_percent(snow_odds(archive)).tobytes())
    capped = {"snowfree": int((np.nan_to_num(long_snow64) > CAP * HALF_HOUR).sum()),
              "open": int((np.nan_to_num(long_open64) > CAP * HALF_HOUR).sum())}

    # ---- flat hours by latitude ----
    lat_values, flat_row = np.unique(np.round(lat, 4), return_inverse=True)
    first_of_row = np.zeros(len(lat_values), dtype=int)
    first_of_row[flat_row[::-1]] = np.arange(n)[::-1]
    spread = float(np.abs(long_flat64 - long_flat64[first_of_row[flat_row]]).max()) if n else 0.0
    flat_out = {"lat": [float(v) for v in lat_values], "unit": "tenths of an hour",
                "largest_difference_within_a_latitude_h": round(spread, 3), "targets": {}}
    for t, target in enumerate(targets):
        rows = long_flat64[first_of_row, t, :]
        flat_out["targets"][target] = {
            "bins": [[int(round(v * 10)) for v in row] for row in rows],
            "year": [scaled(cells[i]["targets"][target].get("long_flat_hours"), 10) for i in first_of_row],
            "poleward": [scaled(cells[i]["targets"][target].get("poleward_share"), 1000) for i in first_of_row],
            "longest": [scaled(cells[i]["targets"][target].get("longest_stretch_h"), 100) for i in first_of_row],
        }
    write_json(out / "flat.json", flat_out)

    # ---- per-cell columns ----
    def season_sum(values: np.ndarray, season: list[int]) -> float | None:
        """Sum over the periods of a season; unknown if a period that counts is unknown."""
        part = values[season]
        return None if np.isnan(part).any() else float(part.sum())

    def summer_half(own, year, winter_half) -> float | None:
        """The summer half as the pipeline wrote it. Year minus winter is used only when that field is
        missing: the three figures are rounded one by one, so the difference can be 0.1 h off."""
        if known(own):
            return float(own)
        if known(year) and known(winter_half):
            return max(0.0, round(float(year) - float(winter_half), 1))
        return None

    regions = sorted({c["region"] for c in cells})
    statuses = ["measured", "doubtful", "no data", "unmeasured"]
    statuses += sorted(set(status) - set(statuses))
    known_labels: list[str] = []
    why_labels: list[str] = []
    columns = {
        "n": n, "ids": ids,
        "unknown": "-1 in the whole-number columns, null in the horizon columns, 65535 in yearly.bin",
        "units": {"lat": "hundredths of a degree", "lon": "hundredths of a degree", "bare": "percent",
                  "bare_km2": "tenths of a km2", "horizon_n": "hundredths of a degree",
                  "hours": "tenths of an hour", "scores": "thousandths", "slope": "tenths of a degree"},
        "yearly": {"file": "yearly.bin", "type": "uint16, little-endian", "shape": [n, len(targets), len(YEARLY_FIELDS)],
                   "fields": YEARLY_FIELDS, "scale": {f: YEARLY_SCALE.get(f, 10) for f in YEARLY_FIELDS},
                   "unknown": YEARLY_UNKNOWN},
        "lat": [int(round(v * 100)) for v in lat], "lon": [int(round(v * 100)) for v in lon],
        "hemisphere": "".join("N" if v else "S" for v in north),
        "gridded": "".join("1" if v else "0" for v in gridded),
        "regions": regions, "region": [regions.index(c["region"]) for c in cells],
        "bare": [scaled(c.get("bare"), 100) for c in cells],
        "bare_km2": [scaled(c.get("bare_km2"), 10) for c in cells],
        "snow_statuses": statuses, "snow": [statuses.index(s) for s in status],
        "snow_pixels": [scaled(c["snow"].get("land_pixels"), 1) for c in cells],
        "snow_block": [], "stuck_winters": {}, "odds_labels": ["stale-flag rule", "as mapped"], "odds_used": [],
        "horizon_n": [], "horizon_s": [], "horizon_note_labels": [], "horizon_note": {},
        "slope": [], "relief": [], "rock": {}, "site": {},
        "known_labels": known_labels, "known": [], "ranked": "", "why_not_labels": why_labels, "why_not": [],
        "layers_disagree": [], "flat_row": [int(v) for v in flat_row],
        "south": {"cells": [], "targets": {t: {"rock_flat": [], "rock_open": [], "rock_clear": [],
                                               "poleward": []} for t in targets}},
        "doubtful": {},
    }
    ranked_flags = []
    yearly = np.full((n, len(targets), len(YEARLY_FIELDS)), YEARLY_UNKNOWN, dtype="<u2")
    for i, cell in enumerate(cells):
        record = scored.get(cell["id"])
        snow = cell["snow"]
        block = snow.get("block_pixels")
        if block is None:
            block = {"3x3": 9, "5x5": 25}.get(snow.get("source"))
        columns["snow_block"].append(scaled(block, 1))
        if known(snow.get("stuck_winters")) and snow["stuck_winters"] > 0:
            columns["stuck_winters"][str(i)] = int(snow["stuck_winters"])
        used = snow.get("odds_used")
        if used is None and north[i] and status[i] in ("measured", "doubtful"):
            used = "stale-flag rule"
        columns["odds_used"].append(columns["odds_labels"].index(used) if used in columns["odds_labels"] else -1)
        horizon = cell.get("horizon")
        if has_horizon[i]:
            columns["horizon_n"].append(scaled_or_none(horizon.get("north_deg"), 100))
            columns["horizon_s"].append(scaled_or_none(horizon.get("south_deg"), 100))
        else:
            columns["horizon_n"].append(None)
            columns["horizon_s"].append(None)
            if isinstance(horizon, dict) and horizon.get("skipped"):
                note = horizon_note_label(horizon["skipped"])
                if note not in columns["horizon_note_labels"]:
                    columns["horizon_note_labels"].append(note)
                columns["horizon_note"][str(i)] = columns["horizon_note_labels"].index(note)
        terrain = (record or {}).get("terrain") or {}
        columns["slope"].append(scaled(terrain.get("median_slope_deg"), 10))
        columns["relief"].append(scaled(terrain.get("relief_m"), 1))
        rock = (record or {}).get("rock") or {}
        if known(rock.get("score")) and rock["score"] > 0:
            columns["rock"][str(i)] = [scaled(rock["score"], 1000), rock.get("body")]
        name = cell.get("site_name") or (record or {}).get("site_name")
        if name:
            columns["site"][str(i)] = name
        if record is None or record.get("little_known") is None:
            columns["known"].append(-2)
        elif record["little_known"]:
            columns["known"].append(-1)
        else:
            label = record.get("known_region")
            near = record.get("known")
            if isinstance(near, dict) and near.get("name"):
                close = f"near the known analog site {near['name']}"   # no distance: keeps the list of labels short
                label = f"{label}; {close}" if label else close
            label = label or "known analog site or region"
            if label not in known_labels:
                known_labels.append(label)
            columns["known"].append(known_labels.index(label))
        ranked_flags.append(bool(record and record.get("ranked")))
        # The scores file can be older than the terrain figures. An area that has a terrain figure is never
        # told that it has none: that reason is dropped, and the reasons that still hold are kept.
        if record is None:
            reasons = [] if has_horizon[i] else [NO_TERRAIN]
        else:
            reasons = [plain_reason(r) for r in record.get("not_ranked_because") or []]
            if has_horizon[i]:
                reasons = [r for r in reasons if not r.startswith(NO_TERRAIN)]
        why = "; ".join(dict.fromkeys(reasons))
        if why and not ranked_flags[-1]:
            if why not in why_labels:
                why_labels.append(why)
            columns["why_not"].append(why_labels.index(why))
        else:
            columns["why_not"].append(-1)
        if cell.get("layers_disagree"):
            columns["layers_disagree"].append(i)
        if not north[i]:
            columns["south"]["cells"].append(i)
        for t, target in enumerate(targets):
            values = cell["targets"][target]
            more = (record or {}).get("targets", {}).get(target, {})
            row = {"snow_free": values.get("long_snow_free_hours"),
                   "snow_free_winter": values.get("long_snow_free_hours_winter"),
                   "snow_free_summer": summer_half(values.get("long_snow_free_hours_summer"),
                                                   values.get("long_snow_free_hours"),
                                                   values.get("long_snow_free_hours_winter")),
                   "open": values.get("long_open_hours"), "open_winter": values.get("long_open_hours_winter"),
                   "open_summer": summer_half(values.get("long_open_hours_summer"), values.get("long_open_hours"),
                                              values.get("long_open_hours_winter"))}
            clear_year = more.get("long_open_hours_clear", values.get("long_open_hours_clear"))
            clear_winter = more.get("long_open_hours_clear_winter", values.get("long_open_hours_clear_winter"))
            clear_summer = more.get("long_open_hours_clear_summer", values.get("long_open_hours_clear_summer"))
            if north[i] and has_cloud and known(values.get("long_open_hours")):
                if not known(clear_year):
                    clear_year = season_sum(long_clear64[i, t], list(range(N_BINS)))
                if not known(clear_winter):
                    clear_winter = season_sum(long_clear64[i, t], winter)
                if not known(clear_summer):
                    clear_summer = season_sum(long_clear64[i, t], summer)
            goals = more.get("goals") or {}
            row.update({"clear": clear_year if has_cloud and north[i] else None,
                        "clear_winter": clear_winter if has_cloud and north[i] else None,
                        "clear_summer": (summer_half(clear_summer, clear_year, clear_winter)
                                         if has_cloud and north[i] else None),
                        "terrain": more.get("terrain"), "lighting": goals.get("lighting"), "full": goals.get("full")})
            yearly[i, t] = [encode_yearly(row[field], field) for field in YEARLY_FIELDS]
            if not north[i]:
                rock_col = columns["south"]["targets"][target]
                rock_col["rock_flat"].append(scaled(values.get("long_summer_rock_hours"), 10))
                rock_open = values.get("long_summer_rock_open_hours")
                rock_col["rock_open"].append(scaled(rock_open, 10))
                rock_clear = more.get("long_summer_rock_open_hours_clear",
                                      values.get("long_summer_rock_open_hours_clear"))
                if has_cloud and known(rock_open) and not known(rock_clear):
                    rock_clear = season_sum(long_clear64[i, t], rock_season)
                rock_col["rock_clear"].append(scaled(rock_clear, 10) if has_cloud else -1)
                rock_col["poleward"].append(scaled(more.get("poleward_share_summer_rock"), 1000))
            if north[i] and status[i] == "doubtful":
                with_rule = values.get("long_snow_free_hours_with_rule", values.get("long_snow_free_hours"))
                columns["doubtful"].setdefault(str(i), {})[target] = [
                    scaled(with_rule, 10), scaled(values.get("long_snow_free_hours_as_mapped"), 10)]
    columns["ranked"] = "".join("1" if v else "0" for v in ranked_flags)
    write_json(out / "cells.json", columns)
    write_bytes(out / "yearly.bin", yearly.tobytes())
    year_values = {target: {field: [None if yearly[i, t, f] == YEARLY_UNKNOWN else
                                    float(yearly[i, t, f]) / YEARLY_SCALE.get(field, 10) for i in range(n)]
                            for f, field in enumerate(YEARLY_FIELDS)} for t, target in enumerate(targets)}

    # ---- the calendar: hours times bare km2, summed over cells ----
    def weighted(values: np.ndarray, rows: np.ndarray) -> list[float]:
        if not rows.any():
            return [0.0] * N_BINS
        return [round(float(v), 1) for v in np.nansum(values[rows] * km2[rows, None], axis=0)]

    def unknown_bins(values: np.ndarray, rows: np.ndarray) -> int:
        return int(np.isnan(values[rows]).sum())

    measured = north & gridded & np.array([s == "measured" for s in status])
    measured_h = measured & has_horizon
    southern = (~north) & gridded
    southern_h = southern & has_horizon
    calendar = {
        "unit": "hours in spells of two hours or more, times km2 of bare ground, per ten-day period",
        "north": {"cells": int(measured.sum()), "bare_km2": round(float(km2[measured].sum()), 1),
                  "cells_with_horizon": int(measured_h.sum()),
                  "bare_km2_with_horizon": round(float(km2[measured_h].sum()), 1),
                  "horizon_share": round(float(measured_h.sum()) / max(1, int(measured.sum())), 4),
                  "one_set": one_set(int(measured_h.sum()), int(measured.sum())),
                  "one_set_from_share": ONE_SET_FROM_SHARE,
                  "who": "northern areas in the search with measured snow odds", "targets": {}},
        "south": {"cells": int(southern.sum()), "bare_km2": round(float(km2[southern].sum()), 1),
                  "cells_with_horizon": int(southern_h.sum()),
                  "bare_km2_with_horizon": round(float(km2[southern_h].sum()), 1),
                  "horizon_share": round(float(southern_h.sum()) / max(1, int(southern.sum())), 4),
                  "one_set": one_set(int(southern_h.sum()), int(southern.sum())),
                  "one_set_from_share": ONE_SET_FROM_SHARE,
                  "who": "southern areas in the search; snow not measured", "rock_season_bins": rock_season,
                  "targets": {}},
    }
    for t, target in enumerate(targets):
        calendar["north"]["targets"][target] = {
            "sun": weighted(long_flat64[:, t], measured),
            "snow_free": weighted(long_snow64[:, t], measured),
            "snow_free_unknown_cell_periods": unknown_bins(long_snow64[:, t], measured),
            "sun_h": weighted(long_flat64[:, t], measured_h),
            "snow_free_h": weighted(long_snow64[:, t], measured_h),
            "open": weighted(long_open64[:, t], measured_h),
            "clear": weighted(long_clear64[:, t], measured_h) if has_cloud else None,
            "clear_unknown_cell_periods": unknown_bins(long_clear64[:, t], measured_h) if has_cloud else None,
        }
        calendar["south"]["targets"][target] = {
            "sun": weighted(long_flat64[:, t], southern),
            "snow_free": None,
            "sun_h": weighted(long_flat64[:, t], southern_h),
            "open": weighted(long_open64[:, t], southern_h),
            "clear": weighted(long_clear64[:, t], southern_h) if has_cloud else None,
        }
    write_json(out / "calendar.json", calendar)

    # ---- latitude profile ----
    profile_out = {"lat": [], "targets": {t: {"all": [], "long": [], "longest": []} for t in targets},
                   "thresholds": {}, "spell_h": stretch_min,
                   "search_band": {
                       "north": [float(lat[north & gridded].min()), float(lat[north & gridded].max())]
                       if (north & gridded).any() else None,
                       "south": [float(lat[~north & gridded].min()), float(lat[~north & gridded].max())]
                       if (~north & gridded).any() else None}}
    if profile_in:
        key = str(int(stretch_min)) if float(stretch_min).is_integer() else str(stretch_min)
        for row in profile_in["profile"]:
            profile_out["lat"].append(row["lat"])
            for target in targets:
                values = row["targets"][target]
                profile_out["targets"][target]["all"].append(values.get("flat_hours"))
                profile_out["targets"][target]["long"].append((values.get("long_flat_hours") or {}).get(key))
                profile_out["targets"][target]["longest"].append(values.get("longest_stretch_h"))
        for target in targets:
            sides = profile_in.get("thresholds", {}).get(target, {})
            profile_out["thresholds"][target] = {
                side: {"spells": (sides.get(side) or {}).get("lowest_lat_with_long_window"),
                       "all_day": (sides.get(side) or {}).get("lowest_lat_with_all_day_low_sun")}
                for side in ("N", "S")}
    write_json(out / "profile.json", profile_out)

    # ---- named sites and short lists ----
    index_of = {cid: i for i, cid in enumerate(ids)}
    named = []
    listed = (validation.get("named_sites") or {}).get("sites")
    if listed:
        for site in listed:
            if site.get("cell") not in index_of:
                continue
            extra = antarctic.get(site["name"], {})
            named.append({"name": site["name"], "lat": site.get("lat"), "lon": site.get("lon"),
                          "cell": index_of[site["cell"]], "hemisphere": site.get("hemisphere"),
                          "winter_snow_evidence": site.get("winter_snow_evidence",
                                                           extra.get("winter_snow_evidence")),
                          "winter_snow_note": extra.get("winter_snow_note"),
                          "analog_use": extra.get("existing_analog_use")})
    else:
        for i, cell in enumerate(cells):
            if cell.get("site_name"):
                extra = antarctic.get(cell["site_name"], {})
                named.append({"name": cell["site_name"], "lat": cell["lat"], "lon": cell["lon"], "cell": i,
                              "hemisphere": cell["hemisphere"],
                              "winter_snow_evidence": extra.get("winter_snow_evidence"),
                              "winter_snow_note": extra.get("winter_snow_note"),
                              "analog_use": extra.get("existing_analog_use")})
    same_site_km = float(smeta.get("same_site_km", 50.0))
    ranked_north = [i for i in range(n) if ranked_flags[i] and north[i]]
    ranked_south = [i for i in range(n) if ranked_flags[i] and not north[i]]
    measured_rows = [int(i) for i in np.flatnonzero(measured)]
    top = {}
    for target in targets:
        col = year_values[target]
        rock_open = columns["south"]["targets"][target]["rock_open"]
        south_at = {cell: k for k, cell in enumerate(columns["south"]["cells"])}

        def rock_hours(row: int, rock_open=rock_open, south_at=south_at):
            return rock_open[south_at[row]] / 10 if rock_open[south_at[row]] >= 0 else None

        def pick(rows, key, tie, limit, col=col):
            return cluster(rows, lat, lon, lambda r: col[key][r], tie, limit, same_site_km)

        def by_open(row: int, col=col):
            return col["open"][row]

        top[target] = {
            "north_lighting": [{"cell": r, "score": col["lighting"][r]}
                               for r in pick(ranked_north, "lighting", by_open, 10)],
            "north_full": [{"cell": r, "score": col["full"][r]} for r in pick(ranked_north, "full", by_open, 5)],
            "south_lighting": [{"cell": r, "score": col["lighting"][r]}
                               for r in pick(ranked_south, "lighting", rock_hours, 6)],
            "winter": [{"cell": r, "hours": col["snow_free_winter"][r]}
                       for r in pick(measured_rows, "snow_free_winter", lambda r, col=col: col["open_winter"][r], 8)],
            "snow_free_year": [{"cell": r, "hours": col["snow_free"][r]}
                               for r in pick(measured_rows, "snow_free", by_open, 8)],
        }
    sites = {"named": named, "top": top, "same_site_km": same_site_km,
             "evidence_note": "Winter-snow evidence for Antarctic sites is copied from the project's reference list."}
    write_json(out / "sites.json", sites)

    # ---- land ----
    land = land_outline(land_file)
    write_json(out / "land.json", land)

    # ---- copy: placeholders, written once; the team's wording is never overwritten ----
    if not (out / "copy.json").exists():
        write_json(out / "copy.json", {"headline": HEADLINE, "purpose": PURPOSE, "subline": SUBLINE})

    # ---- meta ----
    target_rows = []
    # the full method of the first build (true), or a lower bound (false), for the hours after hills of each region
    # (twinfinder/grazing.py, horizon_bins_note)
    hills_exact = (gmeta.get("horizon_bins") or {}).get("hills_exact") or {}
    for t in gmeta["targets"]:
        limit = float(t["limit_deg"])
        info = moon.get(t["id"], {})
        card = cards.get(t["id"])
        official = bool(card and card.get("official_name"))
        # the reason stored with the target is shown only where the lunar cards could confirm it
        confirmed = card is None or (card.get("why_check") or {}).get("confirmed") is True
        target_rows.append({"id": t["id"], "name": card["official_name"] if official else t["name"],
                            "short": card["official_name"] if official else SHORT_NAMES.get(t["id"], t["name"]),
                            "official": official, "name_in_pipeline": t["name"],
                            "name_note": (card or {}).get("name_note"),
                            "list_line": list_line(card) if card else None,
                            "list_summary": ((card or {}).get("nasa_list") or {}).get("summary"),
                            "list_links": ((card or {}).get("nasa_list") or {}).get("links") or [],
                            "lists": lists_of(card),
                            "hills_exact": hills_exact.get(t["id"]),
                            "limit_deg": limit, "shadow_m": round(1.0 / math.tan(math.radians(limit)), 2),
                            "why": info.get("why") if confirmed else None, "moon_lat": info.get("centre_lat"),
                            "terrain_source": info.get("source"),
                            # false: no NASA 5 m terrain model. The light hours are in full; the slope figures are null.
                            "has_model": bool(info.get("has_model", info.get("source") is not None)),
                            "position_how_sure": info.get("position_how_sure"),
                            "position_source": info.get("position_source") or info.get("source"),
                            "position_note": info.get("position_note")})
    headline = {}
    for t, target in enumerate(targets):
        col = year_values[target]
        series = calendar["north"]["targets"][target]
        total = sum(series["snow_free"])
        sun_total = sum(series["sun"])
        sides = profile_out["thresholds"].get(target, {})
        key = str(int(stretch_min)) if float(stretch_min).is_integer() else str(stretch_min)
        counts = {}
        for level in (50, 100, 200):
            counts[str(level)] = {
                "winter": sum(1 for r in measured_rows
                              if col["snow_free_winter"][r] is not None and col["snow_free_winter"][r] >= level),
                "summer": sum(1 for r in measured_rows
                              if col["snow_free_summer"][r] is not None and col["snow_free_summer"][r] >= level),
            }
        with_open = [r for r in ranked_north if col["open"][r] is not None]
        best_cell = max(with_open, key=lambda r: col["open"][r]) if with_open else None
        best_open = col["open"][best_cell] if best_cell is not None else None
        headline[target] = {
            "summer_share_snow_free": round(sum(series["snow_free"][b] for b in summer) / total, 4) if total else None,
            "winter_share_sun_only": round(sum(series["sun"][b] for b in winter) / sun_total, 4) if sun_total else None,
            "measured_cells_reaching": counts,
            "best_open_hours": best_open,
            "best_open_cell": best_cell,
            "first_latitude_with_spells": ((sides.get("N") or {}).get("spells") or {}).get(key),
        }
    # the two-hour spells of some regions start south of the edge of the search (twinfinder/grid.py MIN_LAT)
    for row in target_rows:
        start = (headline.get(row["id"]) or {}).get("first_latitude_with_spells")
        row["spells_start_deg_north"] = start
        row["spells_start_south_of_search"] = start is not None and start < SEARCH_FROM_DEG
        row["outside_search_text"] = (
            f"Spells of 2 hours start at {start:.2f} degrees north for this region, thus a strip of Earth south of "
            f"{SEARCH_FROM_DEG:g} degrees is outside the search."
            if start is not None and start < SEARCH_FROM_DEG else None)
    north_gridded = north & gridded
    # one colour scale for all the lunar regions, every step and both poles
    year_h, period_h = [], []
    for t, target in enumerate(targets):
        year_h += [v for r in measured_rows for v in [year_values[target]["snow_free"][r]] if v is not None and v > 0]
        year_h += [v / 10 for k, r in enumerate(columns["south"]["cells"]) if gridded[r]
                   for v in [columns["south"]["targets"][target]["rock_flat"][k]] if v > 0]
        north_part = long_snow64[measured, t, :]
        south_part = long_flat64[southern, t, :][:, rock_season]
        period_h += [north_part[north_part > 0], south_part[south_part > 0]]
    period_all = np.concatenate(period_h) if period_h else np.array([])
    scale = {"year_h": nice_ceiling(float(np.percentile(year_h, SCALE_QUANTILE * 100))) if year_h else None,
             "period_h": (nice_ceiling(float(np.percentile(period_all, SCALE_QUANTILE * 100)))
                          if period_all.size else None),
             "quantile": SCALE_QUANTILE,
             "how": ("One scale for all the lunar regions, every step and both poles: the top is the first round figure "
                     "above the 99th percentile of the hours on snow-free ground (north, measured snow) and in the rock "
                     "season (south). year_h is for a whole year or half-year, period_h for one ten-day period.")}
    cloud_years = None
    cloud_by_month = None
    if has_cloud:
        years = re.findall(r"\b(?:19|20)\d\d\b", str((cloud_file.get("meta") or {}).get("period") or ""))
        cloud_years = f"{years[0]} to {years[-1]}" if years else None
        if measured.any() and np.isfinite(cloud_pct[measured]).any():
            cloud_by_month = [round(float(v), 1) if np.isfinite(v) else None
                              for v in np.nanmean(cloud_pct[measured], axis=0)]
    by_status = {s: int(sum(1 for i in range(n) if north_gridded[i] and status[i] == s)) for s in statuses}
    check = {}
    for t, target in enumerate(targets):
        total = np.nansum(np.where(np.isnan(long_snow64[:, t]), 0.0, long_snow64[:, t]), axis=1)
        diffs = [abs(total[i] - cells[i]["targets"][target]["long_snow_free_hours"]) for i in measured_rows
                 if known(cells[i]["targets"][target].get("long_snow_free_hours"))
                 and not np.isnan(long_snow64[i, t]).any()]
        check[target] = round(float(max(diffs)), 2) if diffs else None
    measured_as_mapped = any(c["snow"].get("odds_used") == "as mapped" for c in cells)
    meta = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pipeline_written": {"grazing_cells": gmeta.get("written"),
                             "snow_archive": gmeta.get("snow_archive_written"),
                             "cells_scored": smeta.get("written")},
        "long_rule": {
            "used": rule, "pipeline_says": gmeta.get("long_rule"), "spell_h": stretch_min,
            "text": (f"Hours count only inside unbroken spells of at least {hours_in_words(stretch_min)}, "
                     "counted day by day."
                     if rule == "per-day spells" else
                     "Hours count in a ten-day period only if its typical longest unbroken spell reaches "
                     f"{hours_in_words(stretch_min)}."),
        },
        "targets": target_rows, "bins": bins,
        "seasons": {"winter_bins_north": winter, "summer_bins_north": summer, "rock_season_bins_south": rock_season,
                    "winter_text": season_text(winter), "summer_text": season_text(summer),
                    "rock_season_text": season_text(rock_season)},
        "counts": {"records": n, "north_cells": int(north_gridded.sum()), "south_cells": int(southern.sum()),
                   "north_by_snow_status": by_status,
                   "north_bare_km2_measured": calendar["north"]["bare_km2"],
                   "south_bare_km2": calendar["south"]["bare_km2"],
                   "with_horizon_north": int((north_gridded & has_horizon).sum()),
                   "with_horizon_south": int(southern_h.sum()),
                   "ranked_north": len(ranked_north), "ranked_south": len(ranked_south),
                   "scored_records": len(scored), "named_sites": len(named),
                   "outside_the_screen": int((~gridded).sum())},
        "scoring": {"full_hours": smeta.get("full_hours"), "rank_min_bare": smeta.get("rank_min_bare"),
                    "same_site_km": same_site_km, "min_bare": gmeta.get("min_bare"),
                    "cell_km": 11, "area_word": "area"},
        "snow": {"period": "October 2015 to September 2025", "maps": "daily, 4 km",
                 "measured_cells_use": ("the snow maps as they read" if measured_as_mapped else
                                        "the cautious stale-flag rule"),
                 # the same fact under the key the station check uses for its two sets of figures
                 "measured_cells_rule": "as_mapped" if measured_as_mapped else "with_stale_flag_rule"},
        "has_cloud": has_cloud, "cloud": (cloud_file or {}).get("meta"),
        "cloud_grid_km": (round(float(cloud_file["meta"]["grid_deg"]) * 2.0 * math.pi * EARTH_KM / 360.0)
                          if has_cloud and known((cloud_file.get("meta") or {}).get("grid_deg")) else None),
        "cloud_years": cloud_years, "cloud_by_month_north": cloud_by_month,
        "scale": scale,
        # the stored horizons are on the old nine bins: each region says if its hours after hills are a lower bound
        "horizon_bins": {**(gmeta.get("horizon_bins") or {}),
                         "page_text": hills_page_text(target_rows) if gmeta.get("horizon_bins") else None},
        "search_edge": {"north_deg": SEARCH_FROM_DEG,
                        "regions_with_spells_south_of_it": [r["id"] for r in target_rows
                                                            if r["spells_start_south_of_search"]],
                        "text": south_of_search_text(target_rows, headline, SEARCH_FROM_DEG)},
        "sun_motion": sun_motion(stretch_min),
        "encoding": {"unit_h": HALF_HOUR, "cap": CAP, "unknown": UNKNOWN, "capped_cell_periods": capped,
                     "bin_shape": [n, len(targets), N_BINS]},
        "headline": headline,
        "checks": {"largest_gap_between_period_sums_and_yearly_snow_free_hours_h": check,
                   "flat_hours_differ_within_a_latitude_by_h": round(spread, 3)},
        "sources": [s for s in SOURCES if has_cloud or "POWER" not in s["name"]],
        "land": {"source": land["source"], "tolerance_km": land.get("tolerance_km")},
    }
    write_json(out / "meta.json", meta)
    return meta


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--derived", type=Path, default=ROOT / "data" / "derived")
    parser.add_argument("--reference", type=Path, default=ROOT / "data" / "reference")
    parser.add_argument("--land", type=Path, default=ROOT / "data" / "raw" / "naturalearth" / "ne_50m_land.geojson")
    parser.add_argument("--out", type=Path, default=ROOT / "site" / "data")
    args = parser.parse_args()
    meta = export(args.derived, args.reference, args.land, args.out)
    total = sum(p.stat().st_size for p in args.out.iterdir() if p.is_file())
    print(f"{meta['counts']['records']} cells, long-spell rule: {meta['long_rule']['used']}, "
          f"cloud: {'yes' if meta['has_cloud'] else 'no'}; {total / 1e6:.2f} MB in {args.out}")
    for path in sorted(args.out.iterdir()):
        print(f"  {path.name:14s} {path.stat().st_size / 1e3:9.1f} KB")


if __name__ == "__main__":
    main()

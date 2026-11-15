"""Mars part, climate side: the Sun of a Mars site, and climate and bare ground of every
half-degree square of Earth (docs/superpowers/plans/2026-11-14-mars-part.md).

The Sun of a Mars site is worked out by formula from its latitude and the tilt of Mars
(25.19 degrees), with no orbit model: the Sun's declination runs between -25.19 and
+25.19 degrees over the Mars year, the noon Sun height is 90 - |latitude - declination|,
and the time from sunrise to sunset follows from the sunrise hour angle,
cos(H0) = -tan(latitude) tan(declination), as a share of a Mars solar day of 24.66 hours.
The Sun's centre on a flat horizon, no refraction (the thin Mars air bends light by
far less than a degree) and no terrain.

Earth: squares of 0.5 x 0.5 degrees, centres at .25 and .75, from 85 S to 84 N, id
m_<lat>_<lon> with two decimals. Climate is the NASA POWER climatology (MERRA-2) at the
grid point nearest to the square centre; see twinfinder/temperature.py for the
service, its grid and the finding that its values fit 2001 to 2020, not the period it
names. Unknown is None, never 0.
"""
from __future__ import annotations

import json
import math

import numpy as np

from twinfinder import cloud, grid

MARS_TILT_DEG = 25.19
EARTH_TILT_DEG = 23.44
SOL_H = 24.66                 # a Mars solar day in Earth hours (24 h 39 min 35 s = 24.6597 h)
EARTH_DAY_H = 24.0

SQUARE_DEG = 0.5
LAT_SOUTH, LAT_NORTH = -85.0, 84.0
EARTH_RADIUS_KM = 6371.0088   # mean radius
MIN_LAND_SHARE = 0.2
MIN_BARE = 0.15

POWER_PARAMETERS = ("T2M", "TS", "PRECTOTCORR", "PS")
POWER_UNITS = {"T2M": "C", "TS": "C", "PRECTOTCORR": "mm/day", "PS": "kPa"}
POWER_RANGE = {"T2M": (-100.0, 70.0), "TS": (-100.0, 90.0), "PRECTOTCORR": (0.0, 200.0), "PS": (30.0, 110.0)}
FILL_VALUE = -999.0
MONTHS = cloud.MONTHS
MONTH_DAYS_MEAN = (31.0, 28.25, 31.0, 30.0, 31.0, 30.0, 31.0, 31.0, 30.0, 31.0, 30.0, 31.0)

# ESA WorldCover classes
WC_NODATA, WC_WATER, WC_BARE = 0, 80, 60
WC_READ_PX = 360              # a 3 degree tile read as 360 x 360 samples, as for the Moon part
WC_TILE_DEG = 3
WC_PX_PER_SQUARE = round(WC_READ_PX * SQUARE_DEG / WC_TILE_DEG)   # 60


# ---- the Sun of a Mars site -------------------------------------------------------------------------

def noon_elevation_range(lat: float, tilt_deg: float = MARS_TILT_DEG) -> tuple[float, float]:
    """Lowest and highest noon Sun height of the year, in degrees, at a latitude.

    The noon height is 90 - |lat - declination|, with the declination between -tilt and
    +tilt. The lowest is 90 - (|lat| + tilt); below 0 the Sun stays down at noon on the
    darkest days (polar night). The highest is 90 where |lat| <= tilt (the Sun passes
    overhead), otherwise 90 - (|lat| - tilt).
    """
    a = abs(lat)
    low = 90.0 - (a + tilt_deg)
    high = 90.0 if a <= tilt_deg else 90.0 - (a - tilt_deg)
    return low, high


def day_length_h(lat: float, decl_deg: float, day_h: float = SOL_H) -> float:
    """Time from sunrise to sunset of the Sun's centre on a flat horizon, in hours of a day of day_h hours."""
    x = -math.tan(math.radians(lat)) * math.tan(math.radians(decl_deg))
    if x >= 1.0:
        return 0.0
    if x <= -1.0:
        return day_h
    return 2.0 * math.degrees(math.acos(x)) / 360.0 * day_h


def day_length_range(lat: float, tilt_deg: float = MARS_TILT_DEG, day_h: float = SOL_H) -> tuple[float, float]:
    """Shortest and longest day of the year (hours), at the two solstices."""
    a, b = day_length_h(lat, -tilt_deg, day_h), day_length_h(lat, tilt_deg, day_h)
    return min(a, b), max(a, b)


SUN_HOW = (
    "By formula from the site's latitude (planetocentric) and the tilt of Mars, 25.19 degrees: over the Mars "
    "year the Sun's declination runs between -25.19 and +25.19 degrees; noon Sun height = 90 - |latitude - "
    "declination|, so the lowest is 90 - (|latitude| + 25.19) (below 0: polar night) and the highest is 90 "
    "where |latitude| <= 25.19, else 90 - (|latitude| - 25.19). Day length = 2 H0 / 360 x 24.66 h, with "
    "cos H0 = -tan(latitude) tan(declination), at declination -25.19 and +25.19 (0 h in polar night, 24.66 h "
    "in polar day). A Mars solar day is 24.66 Earth hours. The Sun's centre on a flat horizon, no refraction, "
    "no terrain; the unequal length of the Mars seasons (orbit eccentricity 0.093) changes when, not how high."
)


def site_sun(lat: float) -> dict:
    low, high = noon_elevation_range(lat)
    short, long_ = day_length_range(lat)
    return {"noon_elev_min_deg": round(low, 2), "noon_elev_max_deg": round(high, 2),
            "day_length_min_h": round(short, 2), "day_length_max_h": round(long_, 2), "how": SUN_HOW}


# ---- the half-degree grid ----------------------------------------------------------------------------

def square_id(lat_c: float, lon_c: float) -> str:
    return f"m_{lat_c:.2f}_{lon_c:.2f}"


def square_of(lat: float, lon: float) -> tuple[float, float]:
    """Centre of the half-degree square that holds a point."""
    lat0 = math.floor(lat / SQUARE_DEG + 1e-9) * SQUARE_DEG
    lon0 = math.floor(lon / SQUARE_DEG + 1e-9) * SQUARE_DEG
    if lon0 >= 180.0:
        lon0 -= 360.0
    return round(lat0 + SQUARE_DEG / 2, 2), round(lon0 + SQUARE_DEG / 2, 2)


def row_centres() -> list[float]:
    n = round((LAT_NORTH - LAT_SOUTH) / SQUARE_DEG)
    return [round(LAT_SOUTH + (i + 0.5) * SQUARE_DEG, 2) for i in range(n)]


def column_centres() -> list[float]:
    return [round(-180.0 + (j + 0.5) * SQUARE_DEG, 2) for j in range(round(360 / SQUARE_DEG))]


def square_km2(lat_c: float) -> float:
    """Area of a half-degree square on a sphere of the Earth's mean radius."""
    s, n = math.radians(lat_c - SQUARE_DEG / 2), math.radians(lat_c + SQUARE_DEG / 2)
    return EARTH_RADIUS_KM ** 2 * math.radians(SQUARE_DEG) * (math.sin(n) - math.sin(s))


# ---- land share from the Natural Earth outline -------------------------------------------------------

def land_fraction_grid(geojson: dict, per_side: int = 20) -> np.ndarray:
    """Share of each half-degree square inside the land polygons, rows south to north (row_centres order).

    The polygons are burnt into a raster of per_side x per_side samples per square (sample
    centre inside = land) and averaged per square.
    """
    from rasterio import features, transform

    rows, cols = len(row_centres()), len(column_centres())
    height, width = rows * per_side, cols * per_side
    step = SQUARE_DEG / per_side
    affine = transform.from_origin(-180.0, LAT_NORTH, step, step)    # row 0 at the north edge
    shapes = [(f["geometry"], 1) for f in geojson["features"] if f.get("geometry")]
    burnt = features.rasterize(shapes, out_shape=(height, width), transform=affine, fill=0, dtype="uint8")
    frac = burnt.reshape(rows, per_side, cols, per_side).mean(axis=(1, 3))
    return frac[::-1].copy()                                          # row 0 at the south edge


# ---- POWER answers -------------------------------------------------------------------------------------

def read_power(raw, parameter: str) -> dict[tuple[float, float], tuple[list[float | None], float | None]]:
    """{(lat, lon): ([12 monthly values, January first], annual value)} from one regional answer.

    The fill value becomes None; a real 0.0 stays 0.0. Units must be the ones expected
    (C, mm/day, kPa); a value outside the parameter's range, an error message or an
    answer for another parameter is an error.
    """
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8")
    data = json.loads(raw) if isinstance(raw, str) else raw
    if not isinstance(data, dict) or not isinstance(data.get("features"), list) or not data["features"]:
        raise ValueError(f"not a regional climatology answer: {data.get('messages') if isinstance(data, dict) else None!r}")
    units = ((data.get("parameters") or {}).get(parameter) or {}).get("units")
    if units != POWER_UNITS[parameter]:
        raise ValueError(f"{parameter}: units {units!r}, expected {POWER_UNITS[parameter]!r}")
    header = data.get("header") if isinstance(data.get("header"), dict) else {}
    fills = {FILL_VALUE}
    if isinstance(header.get("fill_value"), (int, float)):
        fills.add(float(header["fill_value"]))
    low, high = POWER_RANGE[parameter]

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
            raise ValueError(f"answer does not hold {parameter} by grid point: {error!r}") from error
        if lon >= 180.0:
            lon -= 360.0
        where = f"at {lat}, {lon}"
        out[(lat, lon)] = ([value(months.get(m), f"{m} {where}") for m in MONTHS], value(months.get("ANN"), f"ANN {where}"))
    return out


# ---- precipitation units -------------------------------------------------------------------------------

def precip_mm_month(mm_per_day) -> list[float | None] | None:
    """Monthly totals in mm from monthly means in mm/day: times the days of the month (February 28.25)."""
    if mm_per_day is None:
        return None
    values = list(mm_per_day)
    if len(values) != 12:
        raise ValueError(f"12 months expected, got {len(values)}")
    return [None if v is None else v * d for v, d in zip(values, MONTH_DAYS_MEAN)]


def precip_mm_year(months) -> float | None:
    """Sum of the 12 monthly totals; None if any month is unknown."""
    if months is None or any(v is None for v in months):
        return None
    return float(sum(months))


# ---- bare ground per square from a WorldCover tile -----------------------------------------------------

def worldcover_squares(classes: np.ndarray, lat0: int, lon0: int) -> list[dict]:
    """Land share and bare share of the land for the 36 half-degree squares of one 3 degree tile.

    classes is the tile read as 360 x 360 samples, row 0 at the north edge. land_share is
    land samples (neither no data nor water) over all samples of the square: WorldCover
    leaves much of the open sea as no data, so dividing by mapped samples would count a
    coast as all land. bare is class 60 (bare or sparse vegetation) over the land samples.
    Squares without land are left out.
    """
    if classes.shape != (WC_READ_PX, WC_READ_PX):
        raise ValueError(f"a tile must be read as {WC_READ_PX} x {WC_READ_PX} samples, got {classes.shape}")
    n = WC_READ_PX // WC_PX_PER_SQUARE
    out = []
    for r in range(n):
        lat_c = round(lat0 + WC_TILE_DEG - (r + 0.5) * SQUARE_DEG, 2)
        for c in range(n):
            block = classes[r * WC_PX_PER_SQUARE:(r + 1) * WC_PX_PER_SQUARE,
                            c * WC_PX_PER_SQUARE:(c + 1) * WC_PX_PER_SQUARE]
            land = (block != WC_NODATA) & (block != WC_WATER)
            n_land = int(land.sum())
            if n_land == 0:
                continue
            lon_c = round(lon0 + (c + 0.5) * SQUARE_DEG, 2)
            out.append({"id": square_id(lat_c, lon_c), "lat": lat_c, "lon": lon_c,
                        "land_share": n_land / block.size,
                        "mapped_share": int((block != WC_NODATA).sum()) / block.size,
                        "bare": int((block == WC_BARE).sum()) / n_land})
    return out


# ---- bare ground in Antarctica from the rock-outcrop cells ---------------------------------------------

def south_rock_km2(cells) -> dict[tuple[float, float], float]:
    """Rock area (km2) per half-degree square from the 0.1 degree cells of landcover_cells_south.json.

    A cell's rock is the larger of its two layers (rock_landsat_km2, rock_medium_km2), as the
    cell's own "bare" is; it is spread over the squares its longitude span overlaps, in
    proportion to the overlap. Cells whose south edge is south of 85 S are left out.
    """
    out: dict[tuple[float, float], float] = {}
    for cell in cells:
        lat0, lon0 = (float(x) for x in cell["id"].split("_"))
        if lat0 < LAT_SOUTH - 1e-9:
            continue
        width = grid.lon_factor(lat0) * grid.CELL_DEG
        rock = max(cell["rock_landsat_km2"], cell["rock_medium_km2"])
        lat_c = square_of(lat0 + grid.CELL_DEG / 2, 0.0)[0]
        west, east = lon0, lon0 + width
        k = math.floor(west / SQUARE_DEG + 1e-9)
        while k * SQUARE_DEG < east - 1e-9:
            s_w, s_e = k * SQUARE_DEG, (k + 1) * SQUARE_DEG
            overlap = min(east, s_e) - max(west, s_w)
            if overlap > 1e-12:
                key = square_of(lat_c, s_w + SQUARE_DEG / 2)
                out[key] = out.get(key, 0.0) + rock * overlap / width
            k += 1
    return out


def south_bare(rock_km2: dict, land_km2: dict) -> dict[tuple[float, float], float]:
    """Bare share of the land: rock km2 over land km2, at most 1; squares without land are left out."""
    out = {}
    for key, rock in rock_km2.items():
        land = land_km2.get(key)
        if land:
            out[key] = min(1.0, rock / land)
    return out


# ---- Mars Climate Database tables (web interface, ASCII answer) -------------------------------------

MARS_ECCENTRICITY = 0.0934    # NASA Mars fact sheet, J2000 mean elements: 0.09341
LS_PERIHELION_DEG = 251.0     # Mars is nearest the Sun near Ls 251 degrees
PHOENIX_RECORD_S = 512.0      # one MET low-rate record averages 512 s
SOL_S = SOL_H * 3600.0
PHOENIX_MIN_SOL_SHARE = 0.8   # a sol counts for its highest and lowest value only if 80 % of it is covered
PHOENIX_MAX_SOL_SHARE = 1.25  # ... and if the file does not run over several sols


def read_mcd_table(text: str) -> dict[str, dict]:
    """The variables of one MCD v6.2 web answer laid out by Ls (rows) and local time (columns).

    {"Temperature (K)": {"ls": [...], "local_time": [...], "values": array (len ls, len local_time)}}.
    """
    tables: dict[str, dict] = {}
    name, ls, rows, local_time = None, [], [], None

    def close():
        if name is not None and rows:
            tables[name] = {"ls": list(ls), "local_time": list(local_time), "values": np.array(rows, dtype=float)}

    for line in text.splitlines():
        if line.startswith("### Columns 2+ are "):
            close()
            name, ls, rows, local_time = line[len("### Columns 2+ are "):].strip(), [], [], None
        elif line.startswith("---- ||"):
            local_time = [float(x) for x in line.split("||", 1)[1].split()]
        elif "||" in line and line[:1] in "+-" and line[1:2].isdigit():
            head, body = line.split("||", 1)
            values = [float(x) for x in body.split()]
            if local_time is None or len(values) != len(local_time):
                raise ValueError(f"row of {name!r} does not match its local times: {line[:60]!r}")
            ls.append(float(head))
            rows.append(values)
    close()
    if not tables:
        raise ValueError("no MCD table in this answer")
    return tables


def ls_weights(ls_deg) -> list[float]:
    """Share of the Mars year that each Ls step stands for: time per degree of Ls goes as r squared,
    r proportional to 1 / (1 + e cos(Ls - Ls_perihelion)). Normalised to sum to 1."""
    raw = [(1.0 + MARS_ECCENTRICITY * math.cos(math.radians(ls - LS_PERIHELION_DEG))) ** -2 for ls in ls_deg]
    total = sum(raw)
    return [w / total for w in raw]


def mcd_summary(table: dict) -> dict:
    """Year mean (time-weighted over Ls), and the highest and lowest value of the mean day of any season.

    The repeated last row (Ls 360 = Ls 0) and column (local time 24 = 0) are dropped. Local
    times are equally spaced, so the day mean is the plain mean of a row.
    """
    ls, lt, values = list(table["ls"]), list(table["local_time"]), np.asarray(table["values"], dtype=float)
    if len(ls) > 1 and abs(ls[-1] - ls[0] - 360.0) < 1e-6:
        ls, values = ls[:-1], values[:-1]
    if len(lt) > 1 and abs(lt[-1] - lt[0] - 24.0) < 1e-6:
        values = values[:, :-1]
    weights = ls_weights(ls)
    day_mean = values.mean(axis=1)
    warm_row, cold_row = int(values.max(axis=1).argmax()), int(values.min(axis=1).argmin())
    return {"annual_mean": float(sum(w * d for w, d in zip(weights, day_mean))),
            "warm_season_daily_max": float(values.max()), "warmest_ls": ls[warm_row],
            "cold_season_daily_min": float(values.min()), "coldest_ls": ls[cold_row]}


# ---- lander records ------------------------------------------------------------------------------------

def seasonal_extremes(sols, bin_deg: float = 15.0, min_sols: int = 5) -> dict:
    """Warm-season daily maximum and cold-season daily minimum from daily records (ls, min, max).

    Sols are grouped by Ls bins of bin_deg (the MCD's own step); in each bin with at least
    min_sols known values the daily maxima (minima) are averaged; the warm-season figure is
    the highest bin mean of the maxima, the cold-season figure the lowest bin mean of the
    minima. None when no bin has enough sols, never 0.
    """
    bins: dict[int, dict[str, list[float]]] = {}
    for ls, low, high in sols:
        b = bins.setdefault(int(math.floor(ls / bin_deg)) % round(360 / bin_deg), {"min": [], "max": []})
        if low is not None:
            b["min"].append(float(low))
        if high is not None:
            b["max"].append(float(high))
    means_max = {k: sum(v["max"]) / len(v["max"]) for k, v in bins.items() if len(v["max"]) >= min_sols}
    means_min = {k: sum(v["min"]) / len(v["min"]) for k, v in bins.items() if len(v["min"]) >= min_sols}
    used = sorted(set(means_max) | set(means_min))
    covered: list[list[float]] = []
    for k in used:
        lo, hi = k * bin_deg, (k + 1) * bin_deg
        if covered and abs(covered[-1][1] - lo) < 1e-9:
            covered[-1][1] = hi
        else:
            covered.append([lo, hi])
    return {"warm_season_daily_max": max(means_max.values()) if means_max else None,
            "cold_season_daily_min": min(means_min.values()) if means_min else None,
            "bins_used": len(used), "ls_covered": covered}


def phoenix_sol(text: str) -> dict:
    """Highest and lowest temperature of the 1000 mm mast sensor and mean pressure in one MET low-rate file.

    Columns (PDS label): 0 time in s, 1-4 pressure mean/sd/min/max (Pa), 5-8, 9-12 and 13-16
    mean/sd/min/max of the sensors at 250, 500 and 1000 mm (K). The highest and lowest values
    are given only if the records cover 80 to 125 % of a sol; otherwise None.
    """
    pressures, lows, highs = [], [], []
    for line in text.splitlines():
        parts = [p for p in line.replace(",", " ").split()]
        if len(parts) < 17:
            continue
        values = [float(p) for p in parts]
        pressures.append(values[1])
        lows.append(values[15])
        highs.append(values[16])
    hours = len(pressures) * PHOENIX_RECORD_S / 3600.0
    covered = len(pressures) * PHOENIX_RECORD_S
    whole = PHOENIX_MIN_SOL_SHARE * SOL_S <= covered <= PHOENIX_MAX_SOL_SHARE * SOL_S
    return {"min_k": min(lows) if whole and lows else None, "max_k": max(highs) if whole and highs else None,
            "pressure_pa": sum(pressures) / len(pressures) if pressures else None, "hours": hours}

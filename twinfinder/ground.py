# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Shape of the ground, defined once for Earth and the Moon: roughness at several baselines, a landform class
worked out from slope and relief, and the share of the low-Sun hours a typical point spends in terrain shadow.

Roughness at a baseline L, in metres. Take three points on a grid line, each L from the next. The middle
point's height minus the mean of the two outer heights is the height difference over L once the local
slope (the straight line through the outer two) is taken away:

    d = z(x) - (z(x - L) + z(x + L)) / 2  =  [z(x) - z(x - L)]  -  L * [z(x + L) - z(x - L)] / (2 L)

d is formed along both grid axes (east-west and north-south) at every point where all three heights are
known; the roughness is the root-mean-square of all of them pooled. A plane gives 0 at every baseline. A
sine wave of amplitude A and wavelength W along one axis gives A (1 - cos 2 pi L / W) / 2 (the other axis
adds zeros); an egg crate, A (1 - cos 2 pi L / W) / sqrt 2. The baseline must be a whole number of pixels:
on a 90 m grid 90, 270 and 810 m (1, 3 and 9 pixels), on the Moon's 5 m grid also 5, 15 and 45 m.

Terrain shadow: one minus the hours-weighted open share. The Sun table (minutes per ten-day bin, sector and
elevation bin) is weighted by the share of the area's land that sees the Sun in each sector and elevation
bin (horizon.open_share); grazing.flat_hours and grazing.open_hours do the sums. With snow-free odds, both
sums are weighted by them, as the cells file weighs its snow-free and open hours.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import rasterio

from twinfinder import grazing, terrain

BASELINES_EARTH_M = (90, 270, 810)   # what Copernicus GLO-90 at 90 m can see
BASELINES_FINE_M = (5, 15, 45)       # only the 5 m lunar models can see these
MIN_TRIPLETS = 500                   # fewer known triplets than this (both directions together) is too little
PIECE_KM, PIECE_STEP_KM = 10.0, 1.0  # as moon.PIECE_KM: Earth areas are 10 km windows
LUNAR_90M_FACTOR = 18                # 5 m to 90 m by block means, as moon.fingerprint does for its slopes

GENTLE_DEG = round(math.degrees(math.atan(0.08)), 2)   # 4.57 deg: an 8 % grade, Hammond's "gently sloping"
LANDFORM_THRESHOLDS = {
    "gentle_slope_deg": GENTLE_DEG,
    "hills_relief_m": 91.0,        # 300 ft, Hammond's lower bound of hills
    "mountains_relief_m": 305.0,   # 1000 ft, Hammond's lower bound of (low) mountains
}
LANDFORM_CLASSES = ("plain", "rolling ground", "hills", "mountains")
LANDFORM_TABLE = [   # checked in this order; the first row that fits gives the class
    {"class": "plain",
     "rule": f"relief under {LANDFORM_THRESHOLDS['hills_relief_m']:.0f} m and 90th-percentile slope under "
             f"{GENTLE_DEG} deg (at least nine-tenths of the ground gentler than an 8 % grade)"},
    {"class": "mountains",
     "rule": f"relief at least {LANDFORM_THRESHOLDS['mountains_relief_m']:.0f} m and median slope at least "
             f"{GENTLE_DEG} deg (at most half of the ground gentle)"},
    {"class": "hills",
     "rule": f"relief at least {LANDFORM_THRESHOLDS['hills_relief_m']:.0f} m (and under "
             f"{LANDFORM_THRESHOLDS['mountains_relief_m']:.0f} m) and median slope at least {GENTLE_DEG} deg"},
    {"class": "rolling ground",
     "rule": "everything else: relief under 91 m with steeper patches, or relief of 91 m or more on mostly gentle "
             "ground (plains with hills, tablelands, an ice margin with a few rock knobs)"},
]
LANDFORM_LABEL = "worked out from slope and relief, not a geomorphological map"
LANDFORM_INPUTS = ("median and 90th-percentile slope (degrees, central differences on the 90 m grid, a 180 m "
                   "baseline, terrain.slope_deg) and relief (95th minus 5th percentile of the heights, metres) of "
                   "the 10 km window of land; water and missing tiles left out")
LANDFORM_SOURCE = ("thresholds after E. H. Hammond (1964), 'Analysis of properties in land form geography', Annals of "
                   "the Association of American Geographers 54: relief classes of 300 and 1000 ft in a window of "
                   "about 10 km and 'gently sloping' under 8 %; Hammond's share of gentle ground is read here, "
                   "coarsely, from the median and 90th-percentile slope")

RELIEF_CLASSES_M = [   # for the Mars part only, where no landform class is given (relief over a 55 km square)
    (91.0, "low relief (under 91 m)"),
    (305.0, "moderate relief (91 to 305 m)"),
    (915.0, "high relief (305 to 915 m)"),
    (math.inf, "very high relief (915 m or more)"),
]


def _lag(pixel_m: float, baseline_m: float) -> int:
    lag = baseline_m / pixel_m
    if lag < 1 or abs(lag - round(lag)) > 1e-9:
        raise ValueError(f"a baseline of {baseline_m} m is not a whole number of {pixel_m} m pixels")
    return int(round(lag))


def _sum_of_squares(z: np.ndarray, lag: int, rows_at_once: int = 512) -> tuple[float, int]:
    """Sum of d squared and the number of known d, both axes, worked in blocks of rows to keep memory small."""
    total, count = 0.0, 0
    n_rows = z.shape[0]
    for top in range(0, n_rows, rows_at_once):
        block = np.asarray(z[top:top + rows_at_once], dtype="float64")
        d = block[:, lag:-lag] - 0.5 * (block[:, :-2 * lag] + block[:, 2 * lag:])        # east-west
        known = np.isfinite(d)
        total += float(np.square(d[known]).sum())
        count += int(known.sum())
        centre = range(max(top, lag), min(top + rows_at_once, n_rows - lag))           # north-south
        if len(centre):
            mid = np.asarray(z[centre.start:centre.stop], dtype="float64")
            above = np.asarray(z[centre.start - lag:centre.stop - lag], dtype="float64")
            below = np.asarray(z[centre.start + lag:centre.stop + lag], dtype="float64")
            d = mid - 0.5 * (above + below)
            known = np.isfinite(d)
            total += float(np.square(d[known]).sum())
            count += int(known.sum())
    return total, count


def roughness_m(z: np.ndarray, pixel_m: float, baseline_m: float, min_triplets: int = MIN_TRIPLETS) -> float:
    """Root-mean-square height difference over baseline_m after the local slope is taken away (module docstring).

    z is elevation in metres on a square metric grid, NaN where unknown (water, no tile). NaN when fewer than
    min_triplets triplets of known heights exist.
    """
    lag = _lag(pixel_m, baseline_m)
    if min(z.shape) <= 2 * lag:
        return math.nan
    total, count = _sum_of_squares(z, lag)
    return math.sqrt(total / count) if count >= min_triplets else math.nan


def known(value, digits: int):
    """A number for the files: rounded, or None when it is unknown."""
    if value is None:
        return None
    value = float(value)
    return round(value, digits) if math.isfinite(value) else None


def roughness_set(z: np.ndarray, pixel_m: float, baselines, digits: int = 2) -> dict:
    """Roughness at each baseline as {"90": metres or None, ...}."""
    return {str(b): known(roughness_m(z, pixel_m, b), digits) for b in baselines}


def ratio(a, b, digits: int = 3):
    """a / b, or None when either is unknown or b is not positive."""
    if a is None or b is None or not (math.isfinite(a) and math.isfinite(b)) or b <= 0:
        return None
    return round(a / b, digits)


def pieces(z: np.ndarray, pixel_m: float, piece_km: float = PIECE_KM, step_km: float = PIECE_STEP_KM):
    """Square pieces of piece_km cut every step_km, as in moon.self_overlap: what an Earth window of that size sees."""
    size = int(round(piece_km * 1000.0 / pixel_m))
    step = max(1, int(round(step_km * 1000.0 / pixel_m)))
    for r in range(0, z.shape[0] - size + 1, step):
        for c in range(0, z.shape[1] - size + 1, step):
            yield z[r:r + size, c:c + size]


def landform_class(median_slope_deg, p90_slope_deg, relief_m) -> str | None:
    """Plain, rolling ground, hills or mountains by LANDFORM_TABLE; None unless all three figures are known."""
    values = (median_slope_deg, p90_slope_deg, relief_m)
    if any(v is None or not math.isfinite(float(v)) for v in values):
        return None
    t = LANDFORM_THRESHOLDS
    if relief_m < t["hills_relief_m"] and p90_slope_deg < t["gentle_slope_deg"]:
        return "plain"
    if relief_m >= t["mountains_relief_m"] and median_slope_deg >= t["gentle_slope_deg"]:
        return "mountains"
    if relief_m >= t["hills_relief_m"] and median_slope_deg >= t["gentle_slope_deg"]:
        return "hills"
    return "rolling ground"


def relief_class(relief_m) -> str | None:
    """A relief band from RELIEF_CLASSES_M (Mars part); None when the relief is unknown."""
    if relief_m is None or not math.isfinite(float(relief_m)):
        return None
    return next(name for upper, name in RELIEF_CLASSES_M if relief_m < upper)


def slope_figures(z: np.ndarray, pixel_m: float, min_slope_pixels: int = MIN_TRIPLETS) -> dict:
    """Median and 90th-percentile slope and relief as terrain.terrain_summary gives them; None with too little land."""
    slope_pixels = int(np.isfinite(terrain.slope_deg(z, pixel_m)).sum())
    if slope_pixels < min_slope_pixels:
        return {"median_slope_deg": None, "p90_slope_deg": None, "relief_m": None, "slope_pixels": slope_pixels}
    s = terrain.terrain_summary(z, pixel_m)
    return {"median_slope_deg": round(s["median_slope_deg"], 2), "p90_slope_deg": round(s["p90_slope_deg"], 2),
            "relief_m": round(s["relief_m"], 1), "slope_pixels": slope_pixels}


def window_record(z: np.ndarray, pixel_m: float = 90.0) -> dict:
    """Roughness at 90, 270 and 810 m, slope figures and landform class of one 10 km window at 90 m."""
    slopes = slope_figures(z, pixel_m)
    return {
        "valid_share": round(float(np.isfinite(z).mean()), 3),
        "roughness_m": roughness_set(z, pixel_m, BASELINES_EARTH_M),
        **slopes,
        "landform": landform_class(slopes["median_slope_deg"], slopes["p90_slope_deg"], slopes["relief_m"]),
    }


def area_record(z: np.ndarray, pixel_m: float, moon_roughness: dict) -> dict:
    """window_record plus the area's roughness over each lunar region's at each baseline (first attempt's name).

    moon_roughness is {region id: {"90": metres, "270": ..., "810": ...}}.
    """
    record = window_record(z, pixel_m)
    rough = record["roughness_m"]
    record["roughness_vs_moon"] = {rid: {b: ratio(rough[b], theirs.get(b)) for b in rough}
                                   for rid, theirs in moon_roughness.items()}
    return record


def read_lunar_model(path: Path) -> tuple[np.ndarray, float]:
    """A 5 m lunar terrain model as moon.fingerprint reads it: float32 metres, NaN where empty, and its pixel size."""
    with rasterio.open(path) as ds:
        return ds.read(1, masked=True).astype("float32").filled(np.nan), float(ds.res[0])


def _spread(values) -> dict:
    """10th, 50th and 90th percentile of the known values, and how many there were."""
    v = np.array([x for x in values if x is not None and math.isfinite(x)], dtype=float)
    if not len(v):
        return {"p10": None, "median": None, "p90": None, "pieces": 0}
    p10, p50, p90 = np.percentile(v, [10, 50, 90])
    return {"p10": known(p10, 2), "median": known(p50, 2), "p90": known(p90, 2), "pieces": int(len(v))}


def lunar_region_record(z5: np.ndarray, pixel_m: float) -> dict:
    """Roughness, slope figures and landform class of one lunar 5 m model, whole and in 10 km pieces.

    The fine baselines are taken on the 5 m grid itself; the shared ones on block means of 18 by 18 pixels
    (90 m), the grid moon.fingerprint takes its 90 m slopes from. The 10 km pieces, cut every kilometre, are
    what an Earth window of that size would see if it lay inside the region.
    """
    factor = int(round(90.0 / pixel_m))
    if factor != LUNAR_90M_FACTOR:
        raise ValueError(f"expected a 5 m model, got {pixel_m} m pixels")
    z90 = terrain.block_mean(z5, factor)
    whole = window_record(z90, 90.0)
    per_piece = [window_record(p, 90.0) for p in pieces(z90, 90.0)]
    classes = {name: sum(p["landform"] == name for p in per_piece) for name in LANDFORM_CLASSES}
    typical = max(classes, key=classes.get) if per_piece else None
    return {
        "pixel_m_model": pixel_m,
        "extent_km": [round(z5.shape[1] * pixel_m / 1000.0, 2), round(z5.shape[0] * pixel_m / 1000.0, 2)],
        "valid_share_5m": round(float(np.isfinite(z5).mean()), 3),
        "roughness_m_fine": roughness_set(z5, pixel_m, BASELINES_FINE_M),
        "roughness_m": whole["roughness_m"],
        "roughness_m_10km_pieces": {b: _spread([p["roughness_m"][b] for p in per_piece]) for b in whole["roughness_m"]},
        "median_slope_deg": whole["median_slope_deg"], "p90_slope_deg": whole["p90_slope_deg"],
        "relief_m": whole["relief_m"],
        "landform_whole_region": whole["landform"],
        "landform_10km_pieces": {"counts": classes, "most_common": typical, "pieces": len(per_piece)},
        "relief_m_10km_pieces": _spread([p["relief_m"] for p in per_piece]),
    }


# Terrain shadow ---------------------------------------------------------------------------------------------------

def shadow_share_from_hours(base_hours, open_hours):
    """One minus the open hours over the base hours, both summed over the ten-day bins (last axis).

    NaN where the base is unknown or has no hours at all (there is nothing to be in shadow for).
    """
    base = grazing.total(np.asarray(base_hours, dtype=float))
    lit = grazing.total(np.asarray(open_hours, dtype=float))
    base, lit = np.asarray(base, dtype=float), np.asarray(lit, dtype=float)
    good = np.isfinite(base) & np.isfinite(lit) & (base > 0.0)
    share = np.where(good, 1.0 - lit / np.where(good, base, 1.0), np.nan)
    share = np.clip(share, 0.0, 1.0)
    return share if share.ndim else float(share)


def shadow_share(minutes, bins, open_share, snow_free_odds=None):
    """Share of the low-Sun minutes in minutes during which a typical point of the area is in terrain shadow.

    minutes is a Sun table [..., ten-day bin, sector, elevation bin] (sun.long_band_minutes_table for one limit
    gives the long-spell hours), bins the target's elevation bins, open_share [..., sector, elevation bin] as
    horizon.open_share gives it. With snow_free_odds (per ten-day bin) both sums are weighted by the odds.
    """
    base = grazing.flat_hours(minutes, bins)
    lit = grazing.open_hours(minutes, bins, open_share)
    if snow_free_odds is not None:
        base = grazing.snow_free_hours(base, snow_free_odds)
        lit = grazing.snow_free_hours(lit, snow_free_odds)
    return shadow_share_from_hours(base, lit)

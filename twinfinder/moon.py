# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Lunar south-pole targets and their fingerprints from NASA Goddard LOLA products."""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import rasterio
from rasterio.windows import from_bounds

from twinfinder import sun, terrain

PGDA_SITES = "https://pgda.gsfc.nasa.gov/data/LOLA_5mpp"
PGDA_ILLUM = "https://pgda.gsfc.nasa.gov/data/MoonIllumination"
ILLUMINATION_URL = f"{PGDA_ILLUM}/AVGVISIB_65S_240M_201608.TIF"
PSR_URL = f"{PGDA_ILLUM}/LPSR_65S_240M_201608.TIF"
MOON_RADIUS_M = 1_737_400.0
BASELINES_M = (30, 90)
PIECE_KM = 10.0       # Earth cells are compared as 10 km windows of 90 m pixels
PIECE_STEP_KM = 1.0   # pieces are cut every kilometre, so neighbours overlap


MAP_2024_URL = "https://www.nasa.gov/wp-content/uploads/2024/10/artemis-iii-landing-region-candidates.jpg"
REGION_LIST = "data/reference/lunar_candidate_regions.json"   # the sourced list of the regions (centres, boxes, sources)
FROM_MODEL = "from the terrain model"
FROM_MAP = "estimated from a map"
MODEL_NOTE = ("The centre is the centre of the grid of the NASA 5 m terrain model. The USGS box of the region has the "
              "same corners as the model.")
ONLY_2022 = ("One of the 13 candidate regions of NASA's list of 2022. It is not on the list of nine of 2024. A NASA "
             "abstract (NTRS 20250011660) says that a region off the list of nine is not thus unsuitable for future "
             "exploration.")
MAP_NOTE = ("NASA gives no table of centres. We read the centre of the box of this region on the NASA map of "
            "28 October 2024. We expect an error of less than 1 km.")


@dataclass(frozen=True)
class Target:
    """A lunar region. With pgda_site, the NASA 5 m terrain model gives its position, size and slopes.

    Without pgda_site, centre_lat, centre_lon and box_km give its position from a source (position_source),
    and position_note says how sure the position is. The region then has no slope figures.
    """
    id: str
    name: str
    pgda_site: str | None
    why: str
    position_source: str | None = None
    position_note: str | None = None
    centre_lat: float | None = None        # only without a model: degrees, south negative
    centre_lon: float | None = None        # only without a model: degrees east, 0 to 360
    box_km: tuple[float, float] | None = None   # only without a model: box width (x) and height (y), polar stereographic

    @property
    def has_model(self) -> bool:
        return self.pgda_site is not None

    @property
    def dem_url(self) -> str | None:
        if self.pgda_site is None:
            return None
        return f"{PGDA_SITES}/{self.pgda_site}/{self.pgda_site}_final_adj_5mpp_surf.tif"


# Names as on NASA's lists of candidate Artemis III regions (2022 list of 13, 2024 list of nine); the reasons
# are those the lunar cards (scripts/build_moon_cards.py) found sources for. The list is in order of the Sun
# ceiling, low to high: every array with a region axis follows this order. The centres, boxes and sources of
# the regions without a model come from data/reference/lunar_candidate_regions.json.
TARGETS = [
    Target("connecting-ridge", "Connecting Ridge", "Site01",
           "One of NASA's 13 candidate Artemis III regions of 2022 ('Connecting Ridge'); not among the nine kept in "
           "2024. NASA Goddard's lighting study of the 5 m models found it has the most area lit more than 70 % of "
           "the time."),
    Target("connecting-ridge-extension", "Connecting Ridge Extension", "SL3", ONLY_2022),
    Target("peak-near-shackleton", "Peak Near Shackleton", "Site07", ONLY_2022),
    Target("de-gerlache-rim-1", "de Gerlache Rim 1", "Site11", ONLY_2022),
    Target("de-gerlache-rim-2", "de Gerlache Rim 2", "SL2",
           "One of the nine candidate regions of NASA's list of 2024. It is also on the list of 13 of 2022."),
    Target("faustini-rim-a", "Faustini Rim A", "LM7", ONLY_2022),
    Target("slater-plain", "Slater Plain", None,
           "One of the nine candidate regions of NASA's list of 2024. It is a new region on that list.",
           position_source=MAP_2024_URL,
           position_note=MAP_NOTE + " The map is the only source for this region.",
           centre_lat=-87.15969892148003, centre_lon=125.56581010610674, box_km=(19.98, 19.98)),
    Target("haworth", "Haworth", "Haworth",
           "One of the nine candidate regions of NASA's list of 2024. It is also on the list of 13 of 2022."),
    Target("malapert", "Malapert Massif", "Site23", "One of NASA's nine candidate regions"),
    Target("de-gerlache-kocher-massif", "de Gerlache-Kocher Massif", "Site42", ONLY_2022),
    Target("nobile-rim-1", "Nobile Rim 1", "Site06",
           "One of the nine candidate regions of NASA's list of 2024. It is also on the list of 13 of 2022."),
    Target("mons-mouton", "Mons Mouton", "Site20v2",
           "Candidate region; Chang'e-8 also targets it"),
    Target("mons-mouton-plateau", "Mons Mouton Plateau", None,
           "One of the nine candidate regions of NASA's list of 2024. It is a new region on that list, north of "
           "Mons Mouton.",
           position_source=MAP_2024_URL,
           position_note=MAP_NOTE + " The LROC mosaic of the region agrees to approximately 1 km. The box is "
                         "approximately 77 km by 58 km, thus the Sun ceiling changes by approximately 2.9 degrees "
                         "from its south edge to its north edge.",
           centre_lat=-84.3342533577128, centre_lon=30.57490001717105, box_km=(76.99, 57.99)),
    Target("amundsen-rim", "Amundsen Rim", "DM1", ONLY_2022),
    Target("nobile-rim-2", "Nobile Rim 2", "DM2",
           "Candidate region; most top-ranked landing points in one study"),
    Target("peak-near-cabeus-b", "Peak near Cabeus B", None,
           "One of the nine candidate regions of NASA's list of 2024. It is a new region on that list.",
           position_source=MAP_2024_URL,
           position_note=MAP_NOTE + " The LROC mosaic of the region agrees to approximately 1 km.",
           centre_lat=-83.63814374165243, centre_lon=291.218861104298, box_km=(19.84, 20.12)),
]


def latlon_to_polar_xy(lat: float, lon_east: float) -> tuple[float, float]:
    """Latitude, east longitude to south polar stereographic metres (the inverse of polar_xy_to_latlon)."""
    r = 2.0 * MOON_RADIUS_M * math.tan(math.radians(90.0 + lat) / 2.0)
    return r * math.sin(math.radians(lon_east)), r * math.cos(math.radians(lon_east))


def polar_xy_to_latlon(x_m: float, y_m: float) -> tuple[float, float]:
    """South polar stereographic metres (true scale at the pole) to latitude, east longitude."""
    r = math.hypot(x_m, y_m)
    lat = -90.0 + math.degrees(2.0 * math.atan(r / (2.0 * MOON_RADIUS_M)))
    lon = math.degrees(math.atan2(x_m, y_m)) % 360.0
    return lat, lon


def read_scaled_window(path: Path, bounds) -> np.ndarray:
    """Physical values inside bounds: stored integers times the file's scale, plus its offset."""
    with rasterio.open(path) as ds:
        window = from_bounds(*bounds, transform=ds.transform)
        raw = ds.read(1, window=window, masked=True).astype("float64").filled(np.nan)
        return raw * ds.scales[0] + ds.offsets[0]


def self_overlap(z: np.ndarray, pixel_m: float, piece_km: float = PIECE_KM,
                 step_km: float = PIECE_STEP_KM) -> dict:
    """How well square pieces of a site match the slope histogram of the whole site.

    Each piece is treated like an Earth cell: its own slopes, its own histogram.
    Gives the 10th, 50th and 90th percentile of the overlaps, which is the range
    an Earth window of that size could reach if it were part of the site itself.
    All None when the site is smaller than one piece.
    """
    whole = terrain.slope_histogram(terrain.slope_deg(z, pixel_m))
    size = int(round(piece_km * 1000.0 / pixel_m))
    step = max(1, int(round(step_km * 1000.0 / pixel_m)))
    overlaps = [
        terrain.histogram_overlap(
            terrain.slope_histogram(terrain.slope_deg(z[r:r + size, c:c + size], pixel_m)), whole)
        for r in range(0, z.shape[0] - size + 1, step)
        for c in range(0, z.shape[1] - size + 1, step)
    ]
    if not overlaps:
        return {"p10": None, "median": None, "p90": None}
    p10, median, p90 = (float(v) for v in np.percentile(overlaps, [10, 50, 90]))
    return {"p10": p10, "median": median, "p90": p90}


def fingerprint(target: Target, dem_path: Path, illum_path: Path, psr_path: Path) -> dict:
    """Measured description of one lunar target."""
    with rasterio.open(dem_path) as ds:
        z5 = ds.read(1, masked=True).astype("float32").filled(np.nan)
        b, pixel_m = ds.bounds, ds.res[0]
    xs = (b.left, (b.left + b.right) / 2, b.right)
    ys = (b.bottom, (b.bottom + b.top) / 2, b.top)
    lats = [polar_xy_to_latlon(x, y)[0] for x in xs for y in ys]
    if b.left <= 0 <= b.right and b.bottom <= 0 <= b.top:
        lats.append(-90.0)
    centre_lat, centre_lon = polar_xy_to_latlon(xs[1], ys[1])
    terrain_by_baseline = {}
    for baseline in BASELINES_M:
        factor = round(baseline / pixel_m)
        z = terrain.block_mean(z5, factor)
        terrain_by_baseline[f"{baseline}m"] = terrain.terrain_summary(z, pixel_m * factor)
        if baseline == 90:  # the baseline Earth cells are measured at
            terrain_by_baseline["90m"]["self_overlap_10km"] = self_overlap(z, pixel_m * factor)
    illum = read_scaled_window(illum_path, b)  # share of time the Sun is visible, 0 to 1
    psr = read_scaled_window(psr_path, b)      # 1 where permanently shadowed, else 0
    return {
        "id": target.id,
        "name": target.name,
        "why": target.why,
        "source": target.dem_url,
        "centre_lat": centre_lat,
        "centre_lon": centre_lon,
        "lat_most_poleward": min(lats),
        "lat_least_poleward": max(lats),
        "sun_max_elev_deg": sun.lunar_max_sun_elevation_deg(centre_lat),
        "sun_max_elev_range_deg": [sun.lunar_max_sun_elevation_deg(min(lats)),
                                   sun.lunar_max_sun_elevation_deg(max(lats))],
        "extent_km": [(b.right - b.left) / 1000.0, (b.top - b.bottom) / 1000.0],
        "terrain": terrain_by_baseline,
        "illumination_mean": float(np.nanmean(illum)),
        "illumination_max": float(np.nanmax(illum)),
        "permanent_shadow_fraction": float(np.nanmean(psr > 0.5)),
        "has_model": True,
        "position_source": target.dem_url,
        "position_how_sure": FROM_MODEL,
        "position_note": MODEL_NOTE,
    }


def _nine_point_lats(left: float, bottom: float, right: float, top: float) -> list[float]:
    """Latitudes of the corners, edge centres and centre of a polar stereographic box (and the pole if inside)."""
    xs = (left, (left + right) / 2, right)
    ys = (bottom, (bottom + top) / 2, top)
    lats = [polar_xy_to_latlon(x, y)[0] for x in xs for y in ys]
    if left <= 0 <= right and bottom <= 0 <= top:
        lats.append(-90.0)
    return lats


def box_bounds_m(target: Target) -> tuple[float, float, float, float]:
    """The sourced box of a region without a model: left, bottom, right, top in polar stereographic metres."""
    x, y = latlon_to_polar_xy(target.centre_lat, target.centre_lon)
    half_w, half_h = 500.0 * target.box_km[0], 500.0 * target.box_km[1]
    return x - half_w, y - half_h, x + half_w, y + half_h


def fingerprint_without_model(target: Target, illum_path: Path, psr_path: Path) -> dict:
    """A lunar region without a NASA 5 m terrain model: the same keys as fingerprint.

    The position and the box come from the source in target.position_source. The Sun ceiling uses the
    centre latitude; its range uses the nine points of the box. The sunlight share and the permanent
    shadow come from the polar maps inside the box. The terrain is None: slope figures are unknown, not 0.
    """
    lats = [target.centre_lat]
    illum_mean = illum_max = shadow = None
    if target.box_km is not None:
        bounds = box_bounds_m(target)
        lats = _nine_point_lats(*bounds)
        illum = read_scaled_window(illum_path, bounds)
        psr = read_scaled_window(psr_path, bounds)
        illum_mean, illum_max = float(np.nanmean(illum)), float(np.nanmax(illum))
        shadow = float(np.nanmean(psr > 0.5))
    return {
        "id": target.id,
        "name": target.name,
        "why": target.why,
        "source": None,
        "centre_lat": target.centre_lat,
        "centre_lon": target.centre_lon,
        "lat_most_poleward": min(lats),
        "lat_least_poleward": max(lats),
        "sun_max_elev_deg": sun.lunar_max_sun_elevation_deg(target.centre_lat),
        "sun_max_elev_range_deg": [sun.lunar_max_sun_elevation_deg(min(lats)),
                                   sun.lunar_max_sun_elevation_deg(max(lats))],
        "extent_km": None,
        "box_km": list(target.box_km) if target.box_km is not None else None,
        "terrain": None,
        "illumination_mean": illum_mean,
        "illumination_max": illum_max,
        "permanent_shadow_fraction": shadow,
        "has_model": False,
        "position_source": target.position_source,
        "position_how_sure": FROM_MAP,
        "position_note": target.position_note,
    }

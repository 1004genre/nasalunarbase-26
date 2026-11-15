# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Year-round snow-free odds from NOAA IMS daily 4 km snow and ice maps (Northern Hemisphere)."""
from __future__ import annotations

from datetime import date, timedelta

import numpy as np
from rasterio.warp import transform

IMS_CRS = ("+proj=stere +lat_0=90 +lat_ts=60 +lon_0=-80 +x_0=0 +y_0=0 "
           "+a=6378137 +rf=291.505347349177 +units=m +no_defs")
IMS_SIZE = 6144
IMS_PIXEL_M = 4000.0
IMS_HALF_M = IMS_SIZE * IMS_PIXEL_M / 2
IMS_URL = "https://noaadata.apps.nsidc.org/NOAA/G02156/GIS/4km/{year}/ims{year}{day:03d}_4km_GIS_v1.3.tif.gz"
SNOW_FREE_LAND, SNOW_LAND = 2, 4
BIN_DAYS = 10
N_BINS = 36             # ten-day bins through the calendar year; the last holds days 351 to 366
SEASON_START_DOY = 274  # 1 October: a winter runs from this day ...
SEASON_END_DOY = 79     # ... to 20 March (days of a 365-day year; winter_of goes by the date, so leap years are right)
N_DEKADS = N_BINS       # old name, kept for earlier callers


def ims_rowcol(lats, lons) -> tuple[np.ndarray, np.ndarray]:
    """Fractional row and column in the IMS grid for points on Earth."""
    xs, ys = transform("EPSG:4326", IMS_CRS, list(lons), list(lats))
    cols = (np.asarray(xs) + IMS_HALF_M) / IMS_PIXEL_M
    rows = (IMS_HALF_M - np.asarray(ys)) / IMS_PIXEL_M
    return rows, cols


def ims_url(year: int, day_of_year: int) -> str:
    """Where the archive keeps the map of one day."""
    return IMS_URL.format(year=year, day=day_of_year)


def nearest_day(day_of_year: int, available, reach: int = 2) -> int | None:
    """The available day closest to the wanted one, at most reach days away (the earlier one on a tie)."""
    for step in range(reach + 1):
        for day in (day_of_year - step, day_of_year + step):
            if day in available:
                return day
    return None


def bin_index(day_of_year: int) -> int:
    """Ten-day bin of the calendar year, 0 to 35, for day of year 1 to 366."""
    return min((day_of_year - 1) // BIN_DAYS, N_BINS - 1)


def dekad_index(day_of_year: int) -> int:
    """Old name of bin_index. It used to count from 1 October and return None outside the winter."""
    return bin_index(day_of_year)


def winter_of(year: int, day_of_year: int) -> int | None:
    """The winter (named by the year of its October) a day belongs to, or None from 21 March to 30 September.

    It goes by the calendar date: in a leap year 1 October is day 275 and 20 March is day 80.
    """
    day = date(year, 1, 1) + timedelta(days=day_of_year - 1)
    if day.month >= 10:
        return year
    return year - 1 if (day.month, day.day) <= (3, 20) else None


def accumulate(snow_free_counts: np.ndarray, land_counts: np.ndarray,
               ims_day: np.ndarray, dekad: int, skip: np.ndarray | None = None) -> None:
    """Add one daily map to the running counts for its ten-day bin.

    Pixels where skip is true are left out of both counts.
    """
    snow_free = ims_day == SNOW_FREE_LAND
    land = snow_free | (ims_day == SNOW_LAND)
    if skip is not None:
        snow_free, land = snow_free & ~skip, land & ~skip
    snow_free_counts[dekad] += snow_free
    land_counts[dekad] += land


def stuck_pixels(winter_maps) -> np.ndarray:
    """Pixels that read snow-free land on every map of one winter.

    In the polar night nobody sees the ground, and a flag can stay "snow-free" for the
    whole winter without being observed. Such a pixel-winter counts as unobserved, and
    so do the pixel's maps after it until the flag first turns to snow (accumulate_after_winter).
    """
    stuck = np.ones(winter_maps[0].shape, dtype=bool)
    for ims_day in winter_maps:
        stuck &= ims_day == SNOW_FREE_LAND
    return stuck


def accumulate_winter(snow_free_counts: np.ndarray, land_counts: np.ndarray,
                      winter_maps, bins) -> np.ndarray:
    """Add the maps of one winter, leaving out its stuck pixels. Returns the mask of those pixels."""
    stuck = stuck_pixels(winter_maps)
    for ims_day, index in zip(winter_maps, bins):
        accumulate(snow_free_counts, land_counts, ims_day, index, skip=stuck)
    return stuck


def accumulate_after_winter(snow_free_counts: np.ndarray, land_counts: np.ndarray,
                            maps, bins, stuck: np.ndarray) -> np.ndarray:
    """Add the maps from 21 March to 30 September that follow one winter, in date order.

    A stale flag does not end with the winter: most stuck pixels still read snow-free on
    every map weeks or months later. So a pixel that was stuck in the winter stays left
    out until its first map that reads snow; that map and all later ones count. Only a
    snowy reading ends the run (a sea or sea-ice reading says nothing about the ground).
    Pixels that were not stuck are counted on every map. Returns the pixels still left
    out after the last map; the next winter is judged on its own.
    """
    stale = stuck.copy()
    for ims_day, index in zip(maps, bins):
        stale &= ims_day != SNOW_LAND
        accumulate(snow_free_counts, land_counts, ims_day, index, skip=stale)
    return stale


def _neighbourhood(crop: np.ndarray, row0: int, col0: int, lat: float, lon: float,
                   reach: int = 1) -> np.ndarray:
    """The block of pixels within reach of a point (3 x 3 for reach 1, 5 x 5 for reach 2), as (..., pixels).

    A point outside the crop, or one the IMS projection cannot place, gives an empty block.
    """
    rows, cols = ims_rowcol([lat], [lon])
    if not (np.isfinite(rows[0]) and np.isfinite(cols[0])):
        return crop[..., :0, :0].reshape(*crop.shape[:-2], 0)
    r, c = int(rows[0]) - row0, int(cols[0]) - col0
    block = crop[..., max(r - reach, 0):max(r + reach + 1, 0), max(c - reach, 0):max(c + reach + 1, 0)]
    return block.reshape(*crop.shape[:-2], -1)


def _bin_means(block: np.ndarray) -> np.ndarray:
    """Mean over the land pixels of a block for each bin; NaN where no pixel has a value."""
    out = np.full(block.shape[0], np.nan)
    seen = np.isfinite(block).any(axis=1)
    out[seen] = np.nanmean(block[seen], axis=1)
    return out


BLOCK_REACH = {"3x3": 1, "5x5": 2}   # the source named by cell_probabilities_filled, as pixels each way from the point


def block_reach(source: str | None) -> int | None:
    """Pixels each way from the point's own pixel for a block named "3x3" or "5x5"; None when there was no block."""
    return BLOCK_REACH.get(source)


def block_pixels(source: str | None) -> int | None:
    """How many pixels the named block holds: 9 or 25; None when there was no block."""
    reach = block_reach(source)
    return None if reach is None else (2 * reach + 1) ** 2


def cell_land_pixels(crop: np.ndarray, row0: int, col0: int, lat: float, lon: float, reach: int = 1) -> int:
    """How many pixels of the block around a point were ever observed as land.

    reach 1 is the 3 x 3 block (0 to 9), reach 2 the 5 x 5 block (0 to 25). Pass the reach of the
    block the odds came from (block_reach of the source), so a cell that borrowed the 5 x 5 block
    is not reported with the zero land pixels of its 3 x 3 block.
    """
    return int(np.isfinite(_neighbourhood(crop, row0, col0, lat, lon, reach)).any(axis=0).sum())


def cell_probabilities(crop: np.ndarray, row0: int, col0: int, lat: float, lon: float) -> np.ndarray:
    """Snow-free probability per ten-day bin around a point.

    crop is the (bins, rows, cols) probability array whose top-left pixel sits at
    row0, col0 of the full IMS grid. The 3 x 3 neighbourhood (12 km) is averaged,
    which matches the cell size and lets coastal cells borrow nearby land pixels.
    """
    return _bin_means(_neighbourhood(crop, row0, col0, lat, lon))


def cell_probabilities_filled(crop: np.ndarray, row0: int, col0: int, lat: float,
                              lon: float) -> tuple[np.ndarray, str | None]:
    """Like cell_probabilities, but a point without land in its 3 x 3 block borrows the 5 x 5 block (20 km).

    Returns the values and their source: "3x3", "5x5" or None when neither block has a land pixel.
    """
    for reach, source in ((1, "3x3"), (2, "5x5")):
        block = _neighbourhood(crop, row0, col0, lat, lon, reach)
        if np.isfinite(block).any():
            return _bin_means(block), source
    return np.full(crop.shape[0], np.nan), None


def cell_stuck_winters(stuck: np.ndarray, row0: int, col0: int, lat: float, lon: float,
                       reach: int = 1) -> int:
    """Most stuck winters of any pixel in the 3 x 3 block around a point (reach 2: the 5 x 5 block).

    stuck is the per-pixel count saved with the probabilities; only land pixels can be above zero.
    """
    block = _neighbourhood(stuck, row0, col0, lat, lon, reach)
    return int(block.max()) if block.size else 0


def snow_free_share(probabilities: np.ndarray, days: list[int]) -> float | None:
    """Average snow-free probability over the given days of year, or None if unobserved."""
    values = []
    for day in days:
        value = probabilities[bin_index(day)]
        if np.isfinite(value):
            values.append(float(value))
    return sum(values) / len(values) if values else None

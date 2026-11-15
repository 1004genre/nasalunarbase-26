# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Copernicus GLO-90 elevation around a point on Earth, on a metric grid."""
from __future__ import annotations

import math

import numpy as np
import rasterio
from rasterio.merge import merge
from rasterio.transform import from_origin
from rasterio.warp import Resampling, reproject
from rasterio.warp import transform as warp_transform

from twinfinder.fetch import RAW_DIR, fetch_optional

GLO90 = "https://copernicus-dem-90m.s3.amazonaws.com"
GLO90_DIR = RAW_DIR / "glo90"
KM_PER_DEG_LAT = 111.32
MERGE_MARGIN_PIXELS = 4  # tile pixels kept around the window so that resampling has neighbours
TILE_MARGIN_KM = 0.2  # a tile starts half a pixel before its whole degree, and resampling reads one pixel on


def tile_url(lat: float, lon: float, product: str = "DEM") -> str:
    """URL of the 1-degree tile containing a point. product is DEM (elevation) or WBM (water mask)."""
    lat0, lon0 = math.floor(lat), math.floor(lon)
    ns, ew = ("N" if lat0 >= 0 else "S"), ("E" if lon0 >= 0 else "W")
    name = f"Copernicus_DSM_COG_30_{ns}{abs(lat0):02d}_00_{ew}{abs(lon0):03d}_00"
    if product == "DEM":
        return f"{GLO90}/{name}_DEM/{name}_DEM.tif"
    if product == "WBM":
        return f"{GLO90}/{name}_DEM/AUXFILES/{name}_WBM.tif"
    raise ValueError(f"unknown product {product!r}")


def glo90_tile_url(lat: float, lon: float) -> str:
    return tile_url(lat, lon, "DEM")


def _local_crs(lat: float, lon: float) -> str:
    return f"+proj=aeqd +lat_0={lat} +lon_0={lon} +datum=WGS84 +units=m"


def window_bounds(lat: float, lon: float, half_km: float) -> tuple[float, float, float, float]:
    """West, south, east, north in degrees of the square window of half-width half_km.

    The window is square in metres, so its poleward corners reach further in longitude than
    its centre line. A window that crosses the antimeridian or holds a pole is refused,
    because the tiles on its far side would be left out without a word.
    """
    half_m = half_km * 1000.0
    if abs(lat) + half_km / 110.0 >= 90.0:
        raise ValueError(f"window at {lat}, {lon} holds a pole; not supported")
    edge = np.linspace(-half_m, half_m, 9)
    full = np.full(9, half_m)
    xs = np.concatenate([edge, edge, -full, full])
    ys = np.concatenate([-full, full, edge, edge])
    lons, lats = warp_transform(_local_crs(lat, lon), "EPSG:4326", xs, ys)
    offsets = (np.array(lons) - lon + 180.0) % 360.0 - 180.0
    west, east = lon + float(offsets.min()), lon + float(offsets.max())
    if west < -180.0 or east >= 180.0:
        raise ValueError(f"window at {lat}, {lon} crosses the antimeridian (longitudes {west:.2f} to "
                         f"{east:.2f}); not supported")
    return west, float(min(lats)), east, float(max(lats))


def tiles_for_window(lat: float, lon: float, half_km: float, product: str = "DEM") -> list[str]:
    """Tile URLs covering a square window of half-width half_km centred on lat, lon.

    Every tile between the corners is listed, and a tile whose edge lies within 200 m of the window.
    """
    west, south, east, north = window_bounds(lat, lon, half_km + TILE_MARGIN_KM)
    return sorted({tile_url(a, b, product)
                   for a in range(math.floor(south), math.floor(north) + 1)
                   for b in range(math.floor(west), math.floor(east) + 1)})


def _merge_same_grid(paths: list, bounds: tuple) -> tuple[np.ndarray, object]:
    """Tiles of one pixel spacing copied side by side: float32, NaN where no tile, cut to bounds."""
    west, south, east, north = bounds
    with rasterio.open(paths[0]) as ds:
        (res_x, res_y), left, top = ds.res, ds.transform.c, ds.transform.f
    pad = MERGE_MARGIN_PIXELS
    # the cut follows the tiles' own pixel edges, so merging copies pixels and resamples nothing
    col0 = math.floor((west - left) / res_x) - pad
    col1 = math.ceil((east - left) / res_x) + pad
    row0 = math.floor((top - north) / res_y) - pad
    row1 = math.ceil((top - south) / res_y) + pad
    snapped = (left + col0 * res_x, top - row1 * res_y, left + col1 * res_x, top - row0 * res_y)
    mosaic, transform = merge(paths, bounds=snapped, res=(res_x, res_y), nodata=np.nan, dtype="float32")
    return mosaic[0], transform


def _merge_tiles(paths: list, bounds: tuple, resampling: Resampling) -> tuple[np.ndarray, object]:
    """One float32 array (NaN where no tile) holding the part of the tiles inside bounds.

    Tiles have fewer columns poleward of 50, 60, 70, 80 and 85 degrees. A window across one
    of those lines gets its coarser tiles joined first and then resampled, as one piece, to
    the grid of the finer ones.
    """
    by_spacing: dict = {}
    for path in paths:
        with rasterio.open(path) as ds:
            by_spacing.setdefault(ds.res, []).append(path)
    mosaic = transform = None
    for spacing in sorted(by_spacing):  # finest first
        part, part_transform = _merge_same_grid(by_spacing[spacing], bounds)
        if mosaic is None:
            mosaic, transform = part, part_transform
            continue
        resampled = np.full_like(mosaic, np.nan)
        reproject(part, resampled, src_transform=part_transform, src_crs="EPSG:4326", src_nodata=np.nan,
                  dst_transform=transform, dst_crs="EPSG:4326", dst_nodata=np.nan, resampling=resampling)
        mosaic = np.where(np.isnan(mosaic), resampled, mosaic)
    return mosaic, transform


def _warp_window(lat: float, lon: float, half_km: float, pixel_m: float,
                 product: str, resampling: Resampling) -> np.ndarray:
    n = int(round(2 * half_km * 1000.0 / pixel_m))
    out = np.full((n, n), np.nan, dtype="float32")
    paths = [fetch_optional(url, GLO90_DIR) for url in tiles_for_window(lat, lon, half_km, product)]
    paths = [p for p in paths if p is not None]  # ocean tiles do not exist
    if not paths:
        return out
    # merge first, warp once: warping tile by tile left a seam along every tile edge
    mosaic, mosaic_transform = _merge_tiles(paths, window_bounds(lat, lon, half_km), resampling)
    reproject(mosaic, out, src_transform=mosaic_transform, src_crs="EPSG:4326", src_nodata=np.nan,
              dst_transform=from_origin(-half_km * 1000.0, half_km * 1000.0, pixel_m, pixel_m),
              dst_crs=_local_crs(lat, lon), dst_nodata=np.nan, resampling=resampling)
    return out


def elevation_window(lat: float, lon: float, half_km: float = 5.0, pixel_m: float = 90.0,
                     mask_water: bool = True, sea_as_zero: bool = False) -> np.ndarray:
    """Elevation in metres on a local equal-distance grid.

    NaN marks pixels with no land tile and, when mask_water is set, sea, lakes and rivers.
    With sea_as_zero those pixels are 0 m instead of NaN (for horizon work).
    """
    z = _warp_window(lat, lon, half_km, pixel_m, "DEM", Resampling.bilinear)
    if mask_water:
        water = _warp_window(lat, lon, half_km, pixel_m, "WBM", Resampling.nearest)
        z = np.where(water > 0, np.nan, z)
    if sea_as_zero:
        z = np.where(np.isnan(z), np.float32(0.0), z)
    return z

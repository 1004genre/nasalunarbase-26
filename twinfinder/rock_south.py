# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Rock outcrop area per southern grid cell, from two SCAR Antarctic Digital Database layers.

Both layers are zipped polygon shapefiles in Antarctic polar stereographic metres
(EPSG:3031, true scale at 71S). They are read with the standard library, burned
onto 30 m pixels, and each rock pixel adds its true area on the ellipsoid to the
cell of twinfinder.grid under its centre. Land for the shares comes from the
Copernicus GLO-90 water mask, in which the ice sheet is land.
"""
from __future__ import annotations

import math
import struct
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from rasterio.features import rasterize
from rasterio.transform import from_origin

from twinfinder import earth, grid
from twinfinder.fetch import RAW_DIR, fetch_optional

ADD_DIR = RAW_DIR / "antarctica"
LAYERS = {  # Landsat 8 outcrop v7.3 (Burton-Johnson et al. 2016 method) and medium-resolution outcrop v7.11
    "landsat": ADD_DIR / "add_rockoutcrop_landsat_v7.3" / "add_rockoutcrop_landsat_v7.3.zip",
    "medium": ADD_DIR / "add_rock_outcrop_medium_res_v7_11" / "add_rock_outcrop_medium_res_polygon_v7_11.shp.zip",
}
PIXEL_M = 30.0    # the Landsat layer mostly traces 30 m pixels whose edges lie on odd multiples of 15 m
BLOCK_PX = 2000   # polygons are burned in blocks of 2000 x 2000 pixels (60 km)
POLYGON = 5       # shapefile shape type

A = 6378137.0                # WGS84 equatorial radius, metres
F = 1 / 298.257223563
E = math.sqrt(2 * F - F * F)
B = A * (1 - F)
STANDARD_PARALLEL_DEG = 71.0  # the map is true to scale at 71S


def _t(phi):
    """Snyder's t for the polar stereographic map; phi is latitude in radians, positive southwards."""
    s = E * np.sin(phi)
    return np.tan(np.pi / 4 - phi / 2) / ((1 - s) / (1 + s)) ** (E / 2)


def _m(phi):
    return np.cos(phi) / np.sqrt(1 - (E * np.sin(phi)) ** 2)


_T71 = float(_t(math.radians(STANDARD_PARALLEL_DEG)))
_M71 = float(_m(math.radians(STANDARD_PARALLEL_DEG)))


def to_lat_lon(x, y):
    """Latitude and longitude in degrees of points given in EPSG:3031 metres (arrays)."""
    t = np.hypot(x, y) * _T71 / (A * _M71)
    phi = np.pi / 2 - 2 * np.arctan(t)
    for _ in range(6):  # each pass gains more than two digits
        s = E * np.sin(phi)
        phi = np.pi / 2 - 2 * np.arctan(t * ((1 - s) / (1 + s)) ** (E / 2))
    lon = np.degrees(np.arctan2(x, y))
    return -np.degrees(phi), np.where(lon >= 180.0, lon - 360.0, lon)


def map_scale(lat):
    """Map length over true length at a latitude in degrees.

    A mapped area divided by the square of this is the true area.
    """
    phi = np.radians(-np.asarray(lat, dtype="float64"))
    return _M71 * _t(phi) / (_T71 * _m(phi))


def read_shp(zip_path: Path) -> bytes:
    """The .shp member of a zipped shapefile."""
    with zipfile.ZipFile(zip_path) as z:
        name, = [n for n in z.namelist() if n.endswith(".shp")]
        return z.read(name)


def polygons(shp: bytes):
    """Yield (bounding box, rings) for every polygon record.

    The box is (xmin, ymin, xmax, ymax); each ring is an [n, 2] array of x, y.
    Outer rings run clockwise and holes counter-clockwise, as the format requires.
    """
    pos = 100  # after the file header
    while pos < len(shp):
        _, words = struct.unpack(">2i", shp[pos:pos + 8])
        start, pos = pos + 8, pos + 8 + 2 * words
        kind, = struct.unpack("<i", shp[start:start + 4])
        if kind == 0:
            continue  # a record without a shape
        if kind != POLYGON:
            raise ValueError(f"shape type {kind} is not a polygon")
        bbox = struct.unpack("<4d", shp[start + 4:start + 36])
        n_parts, n_points = struct.unpack("<2i", shp[start + 36:start + 44])
        parts = np.frombuffer(shp, "<i4", n_parts, start + 44).tolist() + [n_points]
        points = np.frombuffer(shp, "<f8", 2 * n_points, start + 44 + 4 * n_parts).reshape(-1, 2)
        yield bbox, [points[a:b] for a, b in zip(parts, parts[1:])]


# Columns per cell for each tenth-degree row from 90S up to the equator, taken from the grid module.
_FACTOR = np.array([grid.lon_factor(tenth / 10) for tenth in range(-900, 0)])


def cell_index(lat, lon) -> tuple[np.ndarray, np.ndarray]:
    """Cell of each southern point as whole tenths of a degree: (south edge, west edge). Matches grid.cell_id."""
    row = np.floor(np.asarray(lat) * 10 + 1e-9).astype(np.int64)
    k = _FACTOR[row + 900]
    col = np.floor(np.asarray(lon) / (k * grid.CELL_DEG) + 1e-9).astype(np.int64) * k
    return row, col


def cell_name(row: int, col: int) -> str:
    return f"{row / 10:.1f}_{col / 10:.1f}"


def _add(totals: dict, row: np.ndarray, col: np.ndarray, values: np.ndarray) -> None:
    """Add values into totals[(row, col)]."""
    keys, where = np.unique((row + 900) * 3600 + col + 1800, return_inverse=True)
    for key, value in zip(keys.tolist(), np.bincount(where, weights=values).tolist()):
        cell = (key // 3600 - 900, key % 3600 - 1800)
        totals[cell] = totals.get(cell, 0.0) + value


def rock_km2_per_cell(zip_path: Path, pixel_m: float = PIXEL_M) -> dict[str, float]:
    """True rock area in km2 for every grid cell one layer touches.

    The pixel grid is shifted by half a pixel so that it coincides with the
    Landsat layer's own pixels, which makes the area exact for the 98% of that
    layer's polygons that follow pixel edges; the rest (clipped or smoothed
    outlines, 37% of the area) and the medium layer are sampled at pixel
    centres. Polygons that overlap (the Landsat layer has some where scenes
    meet) count once.
    """
    block_m = BLOCK_PX * pixel_m

    def block(v: float) -> int:
        return math.floor((v - pixel_m / 2) / block_m)

    blocks: dict = {}
    for (xmin, ymin, xmax, ymax), rings in polygons(read_shp(zip_path)):
        geometry = {"type": "Polygon", "coordinates": [ring.tolist() for ring in rings]}
        for bx in range(block(xmin), block(xmax) + 1):
            for by in range(block(ymin), block(ymax) + 1):
                blocks.setdefault((bx, by), []).append(geometry)
    totals: dict = {}
    for (bx, by), shapes in blocks.items():
        west, north = pixel_m / 2 + bx * block_m, pixel_m / 2 + (by + 1) * block_m
        mask = rasterize(shapes, out_shape=(BLOCK_PX, BLOCK_PX), fill=0, dtype="uint8",
                         transform=from_origin(west, north, pixel_m, pixel_m))
        rows, cols = np.nonzero(mask)
        lat, lon = to_lat_lon(west + (cols + 0.5) * pixel_m, north - (rows + 0.5) * pixel_m)
        _add(totals, *cell_index(lat, lon), pixel_m ** 2 / map_scale(lat) ** 2)
    return {cell_name(r, c): m2 / 1e6 for (r, c), m2 in sorted(totals.items())}


def zone_area_km2(south_deg: float, north_deg: float, width_deg: float) -> float:
    """Area on the WGS84 ellipsoid between two parallels, over a width in longitude."""
    def q(lat_deg: float) -> float:
        s = E * math.sin(math.radians(lat_deg))
        return s / E / (1 - s * s) + math.atanh(s) / E
    return math.radians(width_deg) * B * B / 2 * (q(north_deg) - q(south_deg)) / 1e6


def cell_area_km2(cid: str) -> float:
    south, _ = (float(part) for part in cid.split("_"))
    return zone_area_km2(south, south + grid.CELL_DEG, grid.lon_factor(south) * grid.CELL_DEG)


def cell_tiles(cid: str) -> list[tuple[int, int]]:
    """South-west corners of the 1-degree tiles a cell touches."""
    south, west = (round(float(part) * 10) for part in cid.split("_"))
    return sorted({(south // 10, col // 10) for col in range(west, west + grid.lon_factor(south / 10))})


def water_tile(lat0: int, lon0: int) -> np.ndarray | None:
    """GLO-90 water mask of the 1-degree tile with this south-west corner (0 = land).

    None where the server has no tile, which is open sea.
    """
    path = fetch_optional(earth.tile_url(lat0 + 0.5, lon0 + 0.5, "WBM"), earth.GLO90_DIR)
    if path is None:
        return None
    with rasterio.open(path) as ds:
        return ds.read(1)


def land_share(cid: str, tile=water_tile) -> float | None:
    """Share of a cell that the GLO-90 water mask does not flag as sea, lake or river.

    tile(lat0, lon0) gives a tile's mask or None. The cell is read as blocks one
    tenth of a degree wide; a block in a missing tile is sea. None when the cell
    has no tile at all. Tile edges are taken as whole degrees, which is half a
    pixel (45 m) off.
    """
    south, west = (round(float(part) * 10) for part in cid.split("_"))
    lat0 = south // 10
    strip = (lat0 + 1) * 10 - south - 1  # tenth-degree strips counted from the tile's north edge
    shares, found = [], False
    for col in range(west, west + grid.lon_factor(south / 10)):
        mask = tile(lat0, col // 10)
        if mask is None:
            shares.append(0.0)
            continue
        found = True
        h, w = mask.shape[0] // 10, mask.shape[1] // 10
        block = mask[strip * h:(strip + 1) * h, (col % 10) * w:(col % 10 + 1) * w]
        shares.append(float((block == 0).mean()))
    return sum(shares) / len(shares) if found else None


def cell_record(cid: str, landsat_km2: float, medium_km2: float, mask_land: float | None) -> dict:
    """One southern land-cover record, shaped like the northern ones.

    mask_land is the cell's land share from the water mask, or None to use the
    whole cell. Rock is land, so land is never taken as less than the larger
    rock area. bare is the larger of the two layers' shares of land; ice is the
    rest of the land.

    land_source says where land_share came from: "glo90" (the water mask),
    "whole cell", or "rock area" where the mask shows less land than there is
    rock. In that last case bare is 1 by construction, not by measurement (the
    mask misses some islands, Franklin Island for one).
    """
    lat, lon = grid.cell_centre(cid)
    cell_km2 = cell_area_km2(cid)
    rock_km2 = max(landsat_km2, medium_km2)
    if mask_land is None:
        source = "whole cell"
    elif mask_land * cell_km2 >= rock_km2:
        source = "glo90"
    else:
        source = "rock area"
    share = min(1.0, max(1.0 if mask_land is None else mask_land, rock_km2 / cell_km2))
    land_km2 = share * cell_km2
    bare = min(1.0, rock_km2 / land_km2)
    return {
        "id": cid, "lat": round(lat, 2), "lon": round(lon, 2),
        "land_share": share, "land_source": source,
        "bare": bare, "lichen": 0.0, "ice": 1.0 - bare,
        "rock_landsat": min(1.0, landsat_km2 / land_km2), "rock_medium": min(1.0, medium_km2 / land_km2),
        "layers_disagree": max(landsat_km2, medium_km2) > 2 * min(landsat_km2, medium_km2),
        "rock_landsat_km2": landsat_km2, "rock_medium_km2": medium_km2, "cell_km2": cell_km2,
    }

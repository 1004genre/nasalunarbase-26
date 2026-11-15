# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""The search grid: cells 0.1 degree tall and roughly square in kilometres.

The northern search runs from 59N to 84N, the southern one from 87.5S to 59S.
A southern id is still the south-west corner, such as -66.3_100.5.
"""
from __future__ import annotations

import math

CELL_DEG = 0.1
MIN_LAT, MAX_LAT = 59.0, 84.0
SOUTH_MIN_LAT, SOUTH_MAX_LAT = -87.5, -59.0
TILE_DEG = 3  # land-cover tiles are 3 x 3 degrees


def lon_factor(lat: float) -> int:
    """How many 0.1-degree columns one cell spans at this latitude, north or south.

    Each value up to 84 degrees divides 30 (a land-cover tile); 12 is used only
    between 84 and 87.5 degrees, where the southern search has no such tiles.

    A cell takes its width from its south edge. In the south that edge is the
    pole side of the row, so the row from 64.5S to 64.4S is already 0.3 degrees
    wide (its northern mirror, 64.4N to 64.5N, is 0.2), and likewise the rows
    that end at 73S, 78S and 84S. Every latitude inside a row gives the row's value.
    """
    a = abs(_lat_floor(lat)) if lat < 0 else lat
    if a < 64.5:
        return 2
    if a < 73.0:
        return 3
    if a < 78.0:
        return 5
    if a < 84.0:
        return 6
    return 12


def _lat_floor(lat: float) -> float:
    return math.floor(lat * 10 + 1e-9) / 10


def cell_id(lat: float, lon: float) -> str:
    """Id of the cell containing a point: its south-west corner, such as 66.4_-52.2."""
    lat0 = _lat_floor(lat)
    width = lon_factor(lat0) * CELL_DEG
    lon0 = math.floor(lon / width + 1e-9) * width + 0.0  # + 0.0 turns -0.0 into 0.0
    return f"{lat0:.1f}_{lon0:.1f}"


def cell_centre(cid: str) -> tuple[float, float]:
    lat0, lon0 = (float(part) for part in cid.split("_"))
    return lat0 + CELL_DEG / 2, lon0 + lon_factor(lat0) * CELL_DEG / 2


def tile_origin(lat: float, lon: float) -> tuple[int, int]:
    """South-west corner of the 3-degree land-cover tile containing a point."""
    return math.floor(lat / TILE_DEG) * TILE_DEG, math.floor(lon / TILE_DEG) * TILE_DEG

# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Bare-ground shares per grid cell from ESA WorldCover (10 m, 2021)."""
from __future__ import annotations

import numpy as np

from twinfinder import grid

BASE = "https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map"
BARE, LICHEN, ICE, WATER, NODATA = 60, 100, 70, 80, 0
READ_PX = 360       # a 3-degree tile is read as 360 x 360 samples
PX_PER_CELL = 12    # so 0.1 degree is 12 samples
ROWS_PER_TILE = 30


def tile_url(lat0: int, lon0: int) -> str:
    """URL of the tile whose south-west corner is lat0, lon0 (multiples of 3)."""
    ns, ew = ("N" if lat0 >= 0 else "S"), ("E" if lon0 >= 0 else "W")
    return f"{BASE}/ESA_WorldCover_10m_2021_v200_{ns}{abs(lat0):02d}{ew}{abs(lon0):03d}_Map.tif"


def cell_shares(classes: np.ndarray, lat0: int, lon0: int) -> list[dict]:
    """Land-cover shares for every cell of one tile that contains land.

    classes is the tile as a 360 x 360 array with row 0 at the north edge.
    Shares of bare ground, lichen and ice are fractions of the cell's land;
    land_share is land as a fraction of the mapped (non-nodata) samples.
    """
    cells = []
    for r in range(ROWS_PER_TILE):
        south = round(lat0 + grid.TILE_DEG - (r + 1) * grid.CELL_DEG, 1)
        k = grid.lon_factor(south)
        rows = classes[r * PX_PER_CELL:(r + 1) * PX_PER_CELL]
        for c in range(0, ROWS_PER_TILE, k):
            block = rows[:, c * PX_PER_CELL:(c + k) * PX_PER_CELL]
            n_mapped = int((block != NODATA).sum())
            n_land = int(((block != NODATA) & (block != WATER)).sum())
            if n_land == 0:
                continue
            west = round(lon0 + c * grid.CELL_DEG, 1) + 0.0
            cells.append({
                "id": f"{south:.1f}_{west:.1f}",
                "lat": round(south + grid.CELL_DEG / 2, 2),
                "lon": round(west + k * grid.CELL_DEG / 2, 2),
                "land_share": n_land / n_mapped,
                "bare": int((block == BARE).sum()) / n_land,
                "lichen": int((block == LICHEN).sum()) / n_land,
                "ice": int((block == ICE).sum()) / n_land,
            })
    return cells

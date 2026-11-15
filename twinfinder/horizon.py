# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Terrain horizon: how high the ground stands in each direction, and how much of a cell sees a low Sun."""
from __future__ import annotations

import math

import numpy as np

from twinfinder import earth, sun

AZ_SECTORS = 36  # sector k covers azimuth [10k, 10k+10) degrees, 0 = north, clockwise
ELEV_EDGES_DEG = list(sun.ELEV_EDGES_DEG)  # the same elevation bins as the Sun table (one edge at each Sun ceiling)
# The edges of every record in data/derived/horizon_cells.json (9 bins): the stored shares are on these edges.
STORED_EDGES_DEG = list(sun.OLD_ELEV_EDGES_DEG)
SECTOR_CENTRES_DEG = [10.0 * k + 5.0 for k in range(AZ_SECTORS)]
EARTH_RADIUS_M = 6371000.0
REFRACTION_FACTOR = 7.0 / 6.0  # standard refraction bends light as if the Earth were this much larger
MIN_HORIZON_DEG = -1.0
NEAR_KM = 5.0  # out to here rays are read every quarter pixel; ground this close moves the horizon most
NEAR_STEP_PIXELS = 0.25


def _moved_block(z: np.ndarray, rows: slice, cols: slice, d_row: float, d_col: float) -> np.ndarray | None:
    """The block z[rows, cols] moved by d_row, d_col pixels, read by linear interpolation.

    Every pixel of the block moves by the same amount, so the result is a weighted sum of
    plain slices. Returns None once the moved block leaves the array.
    """
    r0, c0 = math.floor(d_row + 1e-6), math.floor(d_col + 1e-6)
    fr, fc = d_row - r0, d_col - c0
    fr, fc = (fr if fr > 1e-6 else 0.0), (fc if fc > 1e-6 else 0.0)
    top, bottom, left, right = rows.start + r0, rows.stop + r0, cols.start + c0, cols.stop + c0
    if top < 0 or left < 0 or bottom + (fr > 0) > z.shape[0] or right + (fc > 0) > z.shape[1]:
        return None
    block = z[top:bottom, left:right]
    if fc:
        block = block * (1.0 - fc) + z[top:bottom, left + 1:right + 1] * fc
    if fr:
        below = z[top + 1:bottom + 1, left:right]
        if fc:
            below = below * (1.0 - fc) + z[top + 1:bottom + 1, left + 1:right + 1] * fc
        block = block * (1.0 - fr) + below * fr
    return block


def _ray_distances(north: float, east: float, pixel_m: float, max_km: float) -> list[float]:
    """Distances in pixels along a ray at which the ground is read.

    Out to NEAR_KM: every quarter pixel. Beyond: where the ray crosses a grid line (rows for
    rays nearer north or south, else columns), 1 to 1.41 pixels apart, so that each read lies
    between two pixels only.
    """
    reach, near = max_km * 1000.0 / pixel_m, min(NEAR_KM, max_km) * 1000.0 / pixel_m
    line = 1.0 / max(abs(north), abs(east))
    return ([k * NEAR_STEP_PIXELS for k in range(1, int(near / NEAR_STEP_PIXELS) + 1)]
            + [k * line for k in range(int(near / line) + 1, int(reach / line) + 1)])


def horizon_deg(z: np.ndarray, pixel_m: float, azimuths_deg, inner: tuple[slice, slice],
                max_km: float = 25.0, eye_m: float = 2.0) -> np.ndarray:
    """Terrain horizon angle in degrees, [azimuth, row, col], seen from each pixel of z[inner].

    z is elevation in metres with no NaN (sea as 0 m); row 0 is its north edge; azimuth 0 is
    north, clockwise. From an eye eye_m above each pixel a ray is marched out to max_km and the
    steepest sight line to the ground along it is kept. Heights drop with distance for Earth
    curvature and standard refraction. A flat plain gives the small negative dip of its own
    horizon; values are clipped at -1 degree. The block is marched as one piece, so every ray
    of an azimuth ends where the block moved along it first leaves z: z needs max_km of ground
    around the block for the full reach, and a block that touches the edge sees nothing (-1).
    """
    z = np.asarray(z, dtype="float32")
    rows = slice(*inner[0].indices(z.shape[0])[:2])
    cols = slice(*inner[1].indices(z.shape[1])[:2])
    eye = z[rows, cols] + np.float32(eye_m)
    drop_per_m = 1.0 / (2.0 * EARTH_RADIUS_M * REFRACTION_FACTOR)
    out = np.empty((len(azimuths_deg),) + eye.shape, dtype="float32")
    slope = np.empty_like(eye)
    for i, azimuth in enumerate(azimuths_deg):
        north, east = math.cos(math.radians(azimuth)), math.sin(math.radians(azimuth))
        best = np.full(eye.shape, -np.inf, dtype="float32")
        for pixels in _ray_distances(north, east, pixel_m, max_km):
            ground = _moved_block(z, rows, cols, -pixels * north, pixels * east)
            if ground is None:
                break
            distance = pixels * pixel_m
            np.subtract(ground, eye, out=slope)
            slope *= 1.0 / distance
            slope -= distance * drop_per_m
            np.maximum(best, slope, out=best)
        out[i] = np.degrees(np.arctan(best))
    return np.maximum(out, np.float32(MIN_HORIZON_DEG))


def open_share(horizon: np.ndarray, land_mask: np.ndarray, elev_edges=ELEV_EDGES_DEG) -> np.ndarray:
    """Share of land pixels whose horizon is below the lower edge of each elevation bin, [sector, bin].

    horizon is [sector, row, col] for the sector centre azimuths 5, 15, ..., 355. A Sun in bin e
    and sector a is counted as seen from a pixel only if the whole bin clears its horizon.
    All NaN when there is no land pixel.
    """
    lower_edges = np.asarray(elev_edges, dtype="float32")[:-1]
    land = np.asarray(land_mask, dtype=bool)
    if not land.any():
        return np.full((horizon.shape[0], len(lower_edges)), np.nan, dtype="float32")
    seen_from = np.asarray(horizon, dtype="float32")[:, land]  # [sector, land pixel]
    return (seen_from[:, :, None] < lower_edges).mean(axis=1).astype("float32")


def share_on_edges(share, from_edges=STORED_EDGES_DEG, to_edges=ELEV_EDGES_DEG) -> np.ndarray:
    """Open shares [..., sector, bin] on from_edges, moved to the bins of to_edges.

    The share of a bin is the share of land pixels whose horizon is below the bin's LOWER edge (open_share).
    Each new bin takes the share of the stored bin that holds its lower edge. If the lower edge is a stored
    edge, the share is exact. Else it is the share at the stored edge below: a lower bound, because fewer
    pixels have a horizon below a lower angle. A bin above the top stored edge takes the share of the top
    stored bin. A split of a stored bin thus keeps the hours of the stored bin exactly.
    """
    share = np.asarray(share, dtype=float)
    lower_from = np.asarray(from_edges, dtype=float)[:-1]
    lower_to = np.asarray(to_edges, dtype=float)[:-1]
    which = np.searchsorted(lower_from, lower_to + 1e-9, side="right") - 1
    which = np.clip(which, 0, len(lower_from) - 1)
    return share[..., which]


def exact_new_bins(from_edges=STORED_EDGES_DEG, to_edges=ELEV_EDGES_DEG) -> list[bool]:
    """For each bin of to_edges: true if its lower edge is one of from_edges (share_on_edges is exact there)."""
    stored = [round(e, 6) for e in from_edges[:-1]]
    return [round(e, 6) in stored for e in to_edges[:-1]]


def cell_open_share(lat: float, lon: float, half_km: float = 5.0, reach_km: float = 25.0,
                    pixel_m: float = 90.0) -> tuple[np.ndarray, float, float, float]:
    """Open share [36, elevation bins] of one cell, its median horizon due north and due south, and its land share.

    The cell is the central square of half-width half_km; terrain out to reach_km around it can
    hide the Sun. Water inside the cell is not counted (the land share says how much is left),
    lakes keep their level as an obstacle or a gap, and sea without a tile is 0 m.
    """
    half_window = half_km + reach_km
    land_z = earth.elevation_window(lat, lon, half_window, pixel_m)  # NaN on water and where there is no tile
    size = int(round(2 * half_km * 1000.0 / pixel_m))
    start = (land_z.shape[0] - size) // 2
    inner = (slice(start, start + size), slice(start, start + size))
    land = np.isfinite(land_z[inner])
    valid_share = float(land.mean())
    if not land.any():
        nothing = np.full((AZ_SECTORS, len(ELEV_EDGES_DEG) - 1), np.nan, dtype="float32")
        return nothing, math.nan, math.nan, valid_share
    z = earth.elevation_window(lat, lon, half_window, pixel_m, mask_water=False, sea_as_zero=True)
    horizon = horizon_deg(z, pixel_m, SECTOR_CENTRES_DEG + [0.0, 180.0], inner, max_km=reach_km)
    north, south = horizon[AZ_SECTORS], horizon[AZ_SECTORS + 1]
    return (open_share(horizon[:AZ_SECTORS], land, ELEV_EDGES_DEG),
            float(np.median(north[land])), float(np.median(south[land])), valid_share)

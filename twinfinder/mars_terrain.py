"""Landscape slopes on Mars and on Earth, worked out the same way (plan docs/superpowers/plans/2026-11-14-mars-part.md).

Both planets are read on latitude-longitude grids whose pixel is about 1.85 km from north to south:
MOLA MEGDR at 32 pixels per degree on Mars, ETOPO 2022 at 60 arc-seconds on Earth. The slope of a
pixel is the arctangent of the gradient from central differences over its four neighbours, with
metric spacing on a sphere: north-south spacing R * pixel, east-west spacing that times cos(latitude).
A pixel without a height (water on Earth), or with a neighbour without one, has no slope.
"""
from __future__ import annotations

import math
import re
import warnings
from pathlib import Path

import numpy as np

MARS_RADIUS_M = 3_396_190.0     # IAU 2000 Mars equatorial radius, used as a sphere (the task's value)
EARTH_RADIUS_M = 6_371_008.8    # IUGG mean Earth radius, used as a sphere
MARS_PIXEL_DEG = 1 / 32         # MOLA MEGDR 32 pixels per degree: 1.852 km on Mars
EARTH_PIXEL_DEG = 1 / 60        # ETOPO 2022 60 arc-seconds: 1.853 km on Earth

SLOPE_EDGES_DEG = [0, 0.1, 0.25, 0.5, 1, 1.5, 2, 3, 4, 6, 8, 12, 16, 24, 90]
N_BINS = len(SLOPE_EDGES_DEG) - 1
_EDGES = np.array(SLOPE_EDGES_DEG, dtype=float)

SITE_BOX_DEG = 2.0              # a Mars site's landscape: the 2 x 2 degree box centred on it
SUB_BOXES = 4                   # split 4 x 4 into sixteen half-degree sub-boxes for the self-overlap
SQUARE_DEG = 0.5                # the Earth grid of the Mars part
MIN_LAND_SHARE = 0.2            # a square is kept if at least 20 percent of it is land


def slope_deg(z: np.ndarray, lat_deg: np.ndarray, pixel_deg: float, radius_m: float) -> np.ndarray:
    """Slope in degrees of every pixel of z (rows from north to south or south to north, columns eastward).

    lat_deg gives the latitude of each row's centre. Central differences over the four neighbours;
    the outer ring has no slope (no neighbour on one side), and neither has a pixel whose height or
    any neighbour's height is unknown (NaN)."""
    z = np.asarray(z, dtype=float)
    lat = np.radians(np.asarray(lat_deg, dtype=float))
    dy = radius_m * math.radians(pixel_deg)
    dx = dy * np.cos(lat[1:-1])[:, None]
    out = np.full(z.shape, np.nan)
    if z.shape[0] < 3 or z.shape[1] < 3:
        return out
    gy = (z[:-2, 1:-1] - z[2:, 1:-1]) / (2 * dy)
    gx = (z[1:-1, 2:] - z[1:-1, :-2]) / (2 * dx)
    inner = np.degrees(np.arctan(np.hypot(gx, gy)))
    inner[np.isnan(z[1:-1, 1:-1])] = np.nan
    out[1:-1, 1:-1] = inner
    return out


def _bin_index(s: np.ndarray) -> np.ndarray:
    """Bin of each slope on the plan's edges; a slope on an edge goes in the bin above, 90 in the last."""
    return np.clip(np.searchsorted(_EDGES, s, side="right") - 1, 0, N_BINS - 1)


def slope_histogram(slopes) -> list[float] | None:
    """Share of the known pixels in each of the 14 bins (sums to 1); None when no pixel is known."""
    s = np.asarray(slopes, dtype=float).ravel()
    s = s[np.isfinite(s)]
    if s.size == 0:
        return None
    counts = np.bincount(_bin_index(s), minlength=N_BINS)
    return [float(v) for v in counts / s.size]


def histogram_overlap(p, q) -> float | None:
    """Shared area of two histograms: 1 for identical, 0 for disjoint; None if either is unknown."""
    if p is None or q is None:
        return None
    return float(np.minimum(np.asarray(p, dtype=float), np.asarray(q, dtype=float)).sum())


def self_overlap(slopes: np.ndarray, parts: int = SUB_BOXES) -> float | None:
    """Median overlap between the box's histogram and those of its parts x parts sub-boxes.

    A sub-box without any known slope is left out; None if the box has no known slope at all."""
    s = np.asarray(slopes, dtype=float)
    whole = slope_histogram(s)
    if whole is None:
        return None
    rows = np.array_split(np.arange(s.shape[0]), parts)
    cols = np.array_split(np.arange(s.shape[1]), parts)
    overlaps = []
    for r in rows:
        for c in cols:
            h = slope_histogram(s[np.ix_(r, c)])
            if h is not None:
                overlaps.append(histogram_overlap(whole, h))
    return float(np.median(overlaps))


def area_summary(slopes, heights) -> dict:
    """Slope histogram, median and 90th-percentile slope, relief (95th minus 5th percentile height,
    as in the Moon part) and the number of pixels with a known slope. Unknown is None, never 0."""
    s = np.asarray(slopes, dtype=float).ravel()
    s = s[np.isfinite(s)]
    h = np.asarray(heights, dtype=float).ravel()
    h = h[np.isfinite(h)]
    return {
        "slope_hist": slope_histogram(s),
        "median_slope_deg": float(np.median(s)) if s.size else None,
        "p90_slope_deg": float(np.percentile(s, 90)) if s.size else None,
        "relief_m": float(np.percentile(h, 95) - np.percentile(h, 5)) if h.size else None,
        "pixels": int(s.size),
    }


def square_id(lat: float, lon: float) -> str:
    """Id of a half-degree square from its centre, as the plan writes it: m_<lat>_<lon>, two decimals."""
    return f"m_{lat:.2f}_{lon:.2f}"


def rounded(rec: dict) -> dict:
    """Shares and slopes to four decimals, metres to a tenth of a metre; None stays None."""
    out = {}
    for key, value in rec.items():
        if value is None or isinstance(value, (int, np.integer)) and not isinstance(value, bool):
            out[key] = value if value is None else int(value)
        elif key == "slope_hist":
            out[key] = [round(float(v), 4) for v in value]
        elif key.endswith("_m"):
            out[key] = round(float(value), 1)
        else:
            out[key] = round(float(value), 4)
    return out


# ---------------------------------------------------------------- Mars


def _label_value(text: str, key: str) -> str | None:
    m = re.search(rf"^\s*{key}\s*=\s*\"?([^\"\r\n<]+?)\"?\s*(<[^>]*>)?\s*$", text, flags=re.MULTILINE)
    return m.group(1).strip() if m else None


def read_megdr(img_path: Path, lbl_path: Path) -> tuple[np.ndarray, dict]:
    """Read a MOLA MEGDR image as its PDS3 label describes it (16-bit signed integers, most significant
    byte first, lines from north to south, samples eastward from the western longitude).
    Returns heights in the label's unit (read-only, memory-mapped) and the layout."""
    text = Path(lbl_path).read_text(errors="replace")
    lines = _label_value(text, "LINES")
    samples = _label_value(text, "LINE_SAMPLES")
    stype = _label_value(text, "SAMPLE_TYPE")
    bits = _label_value(text, "SAMPLE_BITS")
    if None in (lines, samples, stype, bits) or stype != "MSB_INTEGER" or int(bits) != 16:
        raise ValueError(f"unexpected MEGDR layout in {lbl_path}: {stype} {bits} bits, {lines} x {samples}")
    scale = float(_label_value(text, "SCALING_FACTOR") or 1.0)
    offset = float(_label_value(text, "OFFSET") or 0.0)
    info = {
        "lines": int(lines), "samples": int(samples),
        "ppd": float(_label_value(text, "MAP_RESOLUTION")),
        "top_lat": float(_label_value(text, "MAXIMUM_LATITUDE")),
        "west_lon": float(_label_value(text, "WESTERNMOST_LONGITUDE")),
        "unit": _label_value(text, "UNIT"),
        "scaling_factor": scale, "offset": offset,
    }
    size = Path(img_path).stat().st_size
    if size != info["lines"] * info["samples"] * 2:
        raise ValueError(f"{img_path} has {size} bytes, the label wants {info['lines'] * info['samples'] * 2}")
    z = np.memmap(img_path, dtype=">i2", mode="r", shape=(info["lines"], info["samples"]))
    if scale != 1.0 or offset != 0.0:
        z = z * scale + offset
    return z, info


def site_box(z: np.ndarray, lat: float, lon_east: float, ppd: float = 32, box_deg: float = SITE_BOX_DEG,
             top_lat: float = 90.0, west_lon: float = 0.0, rim: int = 1):
    """Heights of the box_deg x box_deg box centred on a site, with a rim of `rim` pixels for the slopes.

    The pixels inside are those whose centres lie in [lat - box/2, lat + box/2) and the same in
    longitude; columns wrap around 360 degrees. Returns heights (north first), row-centre latitudes
    and column-centre longitudes (not wrapped)."""
    half = box_deg / 2 * ppd
    n = int(round(box_deg * ppd))
    i0 = math.ceil((top_lat - lat) * ppd - half - 0.5) - rim
    j0 = math.ceil((lon_east - west_lon) * ppd - half - 0.5) - rim
    rows = np.arange(i0, i0 + n + 2 * rim)
    cols = np.arange(j0, j0 + n + 2 * rim)
    if rows[0] < 0 or rows[-1] >= z.shape[0]:
        raise ValueError("the site box runs off the top or bottom of the map")
    box = np.asarray(z[rows[0]:rows[-1] + 1][:, np.mod(cols, z.shape[1])], dtype=float)
    lats = top_lat - (rows + 0.5) / ppd
    lons = west_lon + (cols + 0.5) / ppd
    return box, lats, lons


def site_record(z: np.ndarray, lat: float, lon_east: float, ppd: float = 32,
                radius_m: float = MARS_RADIUS_M, top_lat: float = 90.0, west_lon: float = 0.0) -> dict:
    """The plan's site statistics: slope histogram, median and 90th-percentile slope, relief, self-overlap."""
    box, lats, _ = site_box(z, lat, lon_east, ppd=ppd, top_lat=top_lat, west_lon=west_lon)
    s = slope_deg(box, lats, 1 / ppd, radius_m)[1:-1, 1:-1]
    rec = area_summary(s, box[1:-1, 1:-1])
    rec["self_overlap"] = self_overlap(s)
    return rec


# ---------------------------------------------------------------- Earth


def band_squares(z: np.ndarray, land: np.ndarray, top_lat: float, pixel_deg: float, px: int,
                 radius_m: float = EARTH_RADIUS_M, west_lon: float = -180.0,
                 min_land: float = MIN_LAND_SHARE) -> dict:
    """Statistics of every square of a band of whole squares that has at least min_land of land.

    z and land span the full 360 degrees from west_lon, with one rim row above and one below the band;
    top_lat is the northern edge of the band's first square row. Water pixels have no height, so a
    land pixel that touches water has no slope; longitudes wrap at the edges of the map."""
    rows, width = z.shape
    n_rows = (rows - 2) // px
    n_cols = width // px
    if (rows - 2) % px or width % px:
        raise ValueError("the band must hold whole squares plus one rim row above and below")
    zz = np.where(land, np.asarray(z, dtype=float), np.nan)
    wrapped = np.concatenate([zz[:, -1:], zz, zz[:, :1]], axis=1)
    lats = top_lat + pixel_deg / 2 - np.arange(rows) * pixel_deg
    s = slope_deg(wrapped, lats, pixel_deg, radius_m)[1:-1, 1:-1]
    h = zz[1:-1]

    def per_square(a):
        return a.reshape(n_rows, px, n_cols, px).transpose(0, 2, 1, 3).reshape(n_rows * n_cols, px * px)

    land_share = per_square(np.asarray(land[1:-1], dtype=float)).mean(axis=1)
    keep = np.flatnonzero(land_share >= min_land)
    if keep.size == 0:
        return {}
    ss = per_square(s)[keep]
    hh = per_square(h)[keep]
    known = np.isfinite(ss)
    pixels = known.sum(axis=1)
    bins = np.where(known, _bin_index(np.nan_to_num(ss, nan=0.0)), N_BINS)    # N_BINS: not counted
    flat = (np.arange(keep.size)[:, None] * (N_BINS + 1) + bins).ravel()
    counts = np.bincount(flat, minlength=keep.size * (N_BINS + 1)).reshape(keep.size, N_BINS + 1)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)          # all-NaN squares give NaN
        median = np.nanmedian(ss, axis=1)
        p90 = np.nanpercentile(ss, 90, axis=1)
        relief = np.nanpercentile(hh, 95, axis=1) - np.nanpercentile(hh, 5, axis=1)
        mean = np.nanmean(hh, axis=1)

    def known_or_none(v):
        return float(v) if np.isfinite(v) else None

    out = {}
    for k, idx in enumerate(keep):
        r, c = divmod(int(idx), n_cols)
        lat_c = top_lat - (r + 0.5) * px * pixel_deg
        lon_c = west_lon + (c + 0.5) * px * pixel_deg
        n = int(pixels[k])
        out[square_id(lat_c, lon_c)] = {
            "slope_hist": [float(v) for v in counts[k, :N_BINS] / n] if n else None,
            "median_slope_deg": known_or_none(median[k]) if n else None,
            "p90_slope_deg": known_or_none(p90[k]) if n else None,
            "relief_m": known_or_none(relief[k]),
            "elev_mean_m": known_or_none(mean[k]),
            "land_share": float(land_share[idx]),
            "pixels": n,
        }
    return out

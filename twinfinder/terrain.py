# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Terrain statistics defined the same way for the Moon and for Earth."""
from __future__ import annotations

import warnings

import numpy as np

SLOPE_BINS = np.arange(0.0, 46.0, 1.0)  # 45 one-degree bins covering 0 to 45 degrees


def block_mean(a: np.ndarray, factor: int) -> np.ndarray:
    """Average non-overlapping factor-by-factor blocks, ignoring NaN."""
    rows = (a.shape[0] // factor) * factor
    cols = (a.shape[1] // factor) * factor
    blocks = a[:rows, :cols].reshape(rows // factor, factor, cols // factor, factor)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        return np.nanmean(blocks, axis=(1, 3))


def slope_deg(z: np.ndarray, pixel_m: float) -> np.ndarray:
    """Slope in degrees from central differences (a two-pixel baseline)."""
    dzdy, dzdx = np.gradient(z, pixel_m)
    return np.degrees(np.arctan(np.hypot(dzdx, dzdy)))


def slope_histogram(slope: np.ndarray) -> np.ndarray:
    """Share of valid pixels per one-degree bin. Slopes above 45 go in the last bin."""
    s = slope[np.isfinite(slope)]
    counts, _ = np.histogram(np.clip(s, 0.0, 44.999), bins=SLOPE_BINS)
    total = counts.sum()
    return counts / total if total else counts.astype(float)


def histogram_overlap(p: np.ndarray, q: np.ndarray) -> float:
    """Shared area of two normalised histograms: 1 is identical, 0 is disjoint."""
    return float(np.minimum(p, q).sum())


def terrain_summary(z: np.ndarray, pixel_m: float) -> dict:
    """Slope and relief statistics for one elevation grid."""
    s = slope_deg(z, pixel_m)
    valid = s[np.isfinite(s)]
    heights = z[np.isfinite(z)]
    return {
        "pixel_m": float(pixel_m),
        "median_slope_deg": float(np.median(valid)),
        "p90_slope_deg": float(np.percentile(valid, 90)),
        "relief_m": float(np.percentile(heights, 95) - np.percentile(heights, 5)),
        "slope_hist": [float(v) for v in slope_histogram(s)],
    }

# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
import numpy as np
import pytest
from twinfinder import terrain


def tilted_plane(deg, n=50, pixel_m=10.0):
    x = np.arange(n) * pixel_m
    return np.tile(x * np.tan(np.radians(deg)), (n, 1))


def test_block_mean_averages_blocks_and_ignores_nan():
    a = np.array([[1.0, 3.0, 5.0, 7.0], [1.0, 3.0, 5.0, np.nan]])
    assert terrain.block_mean(a, 2).tolist() == [[2.0, 17.0 / 3.0]]


def test_slope_of_tilted_plane():
    s = terrain.slope_deg(tilted_plane(10.0), 10.0)
    assert np.allclose(s, 10.0, atol=1e-6)


def test_histogram_sums_to_one_and_peaks_in_right_bin():
    h = terrain.slope_histogram(terrain.slope_deg(tilted_plane(10.5), 10.0))
    assert h.sum() == pytest.approx(1.0)
    assert h[10] == pytest.approx(1.0)


def test_steep_slopes_fall_in_last_bin():
    h = terrain.slope_histogram(np.array([60.0, 80.0]))
    assert h[-1] == pytest.approx(1.0)


def test_overlap_is_one_for_identical_and_zero_for_disjoint():
    flat = terrain.slope_histogram(np.full(100, 0.5))
    steep = terrain.slope_histogram(np.full(100, 30.5))
    assert terrain.histogram_overlap(flat, flat) == pytest.approx(1.0)
    assert terrain.histogram_overlap(flat, steep) == pytest.approx(0.0)


def test_summary_reports_slope_and_relief():
    z = tilted_plane(10.0)
    out = terrain.terrain_summary(z, 10.0)
    assert out["median_slope_deg"] == pytest.approx(10.0, abs=0.01)
    assert out["relief_m"] == pytest.approx(np.percentile(z, 95) - np.percentile(z, 5))
    assert len(out["slope_hist"]) == 45

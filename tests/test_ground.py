# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Tests for twinfinder/ground.py: roughness, landform class and terrain shadow on made-up ground."""
import math

import numpy as np
import pytest

from twinfinder import grazing, ground, horizon, sun


def plane(n=120, pixel_m=90.0, east_deg=7.0, north_deg=-3.0):
    y, x = np.mgrid[0:n, 0:n] * pixel_m
    return x * math.tan(math.radians(east_deg)) - y * math.tan(math.radians(north_deg)) + 500.0


def sine_east(lag, amplitude=10.0, wavelength_px=20, periods=10):
    """A sine wave running east-west; the triplets of each row cover whole periods exactly."""
    n = 2 * lag + wavelength_px * periods
    x = np.arange(n)
    return np.tile(amplitude * np.sin(2 * np.pi * x / wavelength_px), (n, 1))


# Roughness -------------------------------------------------------------------------------------------------------

def test_a_plane_has_no_roughness_at_any_baseline():
    z = plane()
    for baseline in ground.BASELINES_EARTH_M:
        assert ground.roughness_m(z, 90.0, baseline) == pytest.approx(0.0, abs=1e-6)


@pytest.mark.parametrize("lag", [1, 3, 9])
def test_a_sine_wave_gives_the_known_value(lag):
    amplitude, wavelength = 10.0, 20
    z = sine_east(lag, amplitude, wavelength)
    # east-west: d = A sin(kx) (1 - cos kL), mean square A^2 (1 - cos kL)^2 / 2; north-south: d = 0.
    # Both directions are pooled with the same number of triplets, so the mean square halves.
    expected = amplitude * (1.0 - math.cos(2 * math.pi * lag / wavelength)) / 2.0
    assert ground.roughness_m(z, 5.0, 5.0 * lag) == pytest.approx(expected, rel=1e-9)


def test_an_egg_crate_gives_the_known_value_in_both_directions():
    lag, amplitude, wavelength = 3, 4.0, 12
    n = 2 * lag + wavelength * 8
    y, x = np.mgrid[0:n, 0:n]
    k = 2 * np.pi / wavelength
    z = amplitude * np.sin(k * x) + amplitude * np.sin(k * y)
    expected = amplitude * (1.0 - math.cos(k * lag)) / math.sqrt(2.0)
    assert ground.roughness_m(z, 90.0, 270.0) == pytest.approx(expected, rel=1e-9)


def test_the_local_slope_is_taken_away():
    lag = 3
    z = sine_east(lag)
    tilted = z + plane(n=z.shape[0], pixel_m=90.0, east_deg=20.0, north_deg=10.0)
    assert ground.roughness_m(tilted, 90.0, 270.0) == pytest.approx(ground.roughness_m(z, 90.0, 270.0), rel=1e-6)


def test_the_baseline_must_be_a_whole_number_of_pixels():
    with pytest.raises(ValueError):
        ground.roughness_m(plane(), 90.0, 100.0)
    with pytest.raises(ValueError):
        ground.roughness_m(plane(), 90.0, 45.0)


def test_triplets_touching_water_are_left_out_and_too_few_is_unknown():
    lag = 1
    z = sine_east(lag)
    with_lake = z.copy()
    with_lake[50:60, 50:60] = np.nan
    assert ground.roughness_m(with_lake, 90.0, 90.0) == pytest.approx(ground.roughness_m(z, 90.0, 90.0), rel=0.05)
    almost_all_water = np.full_like(z, np.nan)
    almost_all_water[:5, :5] = z[:5, :5]
    assert math.isnan(ground.roughness_m(almost_all_water, 90.0, 90.0))


def test_roughness_set_uses_null_for_unknown():
    z = np.full((30, 30), np.nan)
    assert ground.roughness_set(z, 90.0, ground.BASELINES_EARTH_M) == {"90": None, "270": None, "810": None}


def test_ratio_is_unknown_when_either_side_is():
    assert ground.ratio(2.0, 4.0) == pytest.approx(0.5)
    assert ground.ratio(None, 4.0) is None
    assert ground.ratio(2.0, None) is None
    assert ground.ratio(2.0, 0.0) is None


def test_pieces_are_ten_km_squares_a_km_apart():
    z = np.zeros((222, 222))
    pieces = list(ground.pieces(z, 90.0))
    assert all(p.shape == (111, 111) for p in pieces)
    assert len(pieces) == len(range(0, 222 - 111 + 1, 11)) ** 2


# Landform class --------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("median, p90, relief, expected", [
    (0.8, 2.5, 40.0, "plain"),
    (2.0, 6.0, 60.0, "rolling ground"),        # low relief, but a tenth of the ground steeper than an 8 % grade
    (2.0, 9.0, 400.0, "rolling ground"),       # high relief on mostly gentle ground: plain with hills, tableland
    (6.0, 14.0, 200.0, "hills"),
    (6.0, 14.0, 90.0, "rolling ground"),       # steep but under the hills relief
    (12.0, 25.0, 900.0, "mountains"),
    (4.6, 12.0, 305.0, "mountains"),           # both thresholds met exactly
])
def test_landform_class_follows_the_table(median, p90, relief, expected):
    assert ground.landform_class(median, p90, relief) == expected


def test_landform_class_is_unknown_without_all_three_figures():
    assert ground.landform_class(None, 5.0, 100.0) is None
    assert ground.landform_class(3.0, float("nan"), 100.0) is None


def test_the_landform_table_names_four_classes_with_their_thresholds():
    assert [row["class"] for row in ground.LANDFORM_TABLE] == ["plain", "mountains", "hills", "rolling ground"]
    assert ground.LANDFORM_THRESHOLDS["gentle_slope_deg"] == pytest.approx(math.degrees(math.atan(0.08)), abs=0.01)


# Terrain shadow --------------------------------------------------------------------------------------------------

def walled_to_the_north():
    """Open share [36, 9] of a five-pixel area at the foot of a 70-degree wall that runs east-west along its north side."""
    n, pixel_m, foot = 41, 90.0, 20
    rows = np.arange(n, dtype=float)[:, None]
    north_m = (foot - rows) * pixel_m
    z = np.where(north_m > 0, north_m * math.tan(math.radians(70.0)), 0.0) * np.ones((1, n))
    inner = (slice(foot, foot + 1), slice(18, 23))
    seen = horizon.horizon_deg(z, pixel_m, horizon.SECTOR_CENTRES_DEG, inner, max_km=1.8)
    return seen, horizon.open_share(seen, np.ones((1, 5), dtype=bool))


def test_the_made_up_wall_hides_the_northern_half_of_the_sky_and_nothing_else():
    seen, share = walled_to_the_north()
    northern = grazing.poleward_sectors("N")
    southern = [k for k in range(36) if k not in northern]
    assert (seen[northern] > horizon.ELEV_EDGES_DEG[-1]).all()
    assert (seen[southern] < 0.0).all()
    assert (share[northern] == 0.0).all() and (share[southern] == 1.0).all()


def test_shadow_share_behind_a_wall_to_the_north_is_the_poleward_share_of_the_sun():
    _, share = walled_to_the_north()
    limit = 5.55
    bins = grazing.elev_bins(limit)
    minutes = sun.long_band_minutes_table([75.0], [limit], grazing.STRETCH_MIN_H, 5, year_phases=1)[0, 0]
    expected = grazing.poleward_share(minutes, bins, None, "N")   # minutes with the Sun within 90 deg of north
    assert 0.2 < expected < 0.8
    assert ground.shadow_share(minutes, bins, share) == pytest.approx(expected, abs=1e-6)
    # snow-free weighting with the same odds in every bin changes nothing
    assert ground.shadow_share(minutes, bins, share, np.full(36, 0.5)) == pytest.approx(expected, abs=1e-6)


def test_shadow_share_of_open_ground_is_zero_and_of_a_pit_is_one():
    limit = 2.08
    bins = grazing.elev_bins(limit)
    minutes = sun.long_band_minutes_table([72.0], [limit], grazing.STRETCH_MIN_H, 5, year_phases=1)[0, 0]
    assert ground.shadow_share(minutes, bins, np.ones((36, 9))) == pytest.approx(0.0, abs=1e-9)
    assert ground.shadow_share(minutes, bins, np.zeros((36, 9))) == pytest.approx(1.0, abs=1e-9)


def test_shadow_share_is_unknown_without_snow_odds_or_without_any_low_sun():
    limit = 5.55
    bins = grazing.elev_bins(limit)
    minutes = sun.long_band_minutes_table([75.0], [limit], grazing.STRETCH_MIN_H, 5, year_phases=1)[0, 0]
    assert math.isnan(ground.shadow_share(minutes, bins, np.ones((36, 9)), np.full(36, np.nan)))
    assert math.isnan(ground.shadow_share(np.zeros_like(minutes), bins, np.ones((36, 9))))


def test_shadow_share_from_hours_by_bin_weights_by_hours():
    base = np.zeros(36)
    base[[3, 4]] = [30.0, 10.0]
    lit = np.zeros(36)
    lit[[3, 4]] = [30.0, 0.0]          # bin 3 fully open, bin 4 fully shadowed
    assert ground.shadow_share_from_hours(base, lit) == pytest.approx(10.0 / 40.0)
    both = ground.shadow_share_from_hours(np.stack([base, np.zeros(36)]), np.stack([lit, np.zeros(36)]))
    assert both[0] == pytest.approx(0.25) and math.isnan(both[1])


# One area --------------------------------------------------------------------------------------------------------

def test_area_record_of_a_window_without_land_holds_nulls_not_zeros():
    record = ground.area_record(np.full((111, 111), np.nan), 90.0, {"t": {"90": 1.0, "270": 2.0, "810": 3.0}})
    assert record["roughness_m"] == {"90": None, "270": None, "810": None}
    assert record["landform"] is None and record["relief_m"] is None
    assert record["roughness_vs_moon"] == {"t": {"90": None, "270": None, "810": None}}


def test_area_record_of_rough_ground_compares_it_with_the_moon():
    lag = 1
    z = sine_east(lag, amplitude=50.0, wavelength_px=10, periods=11)[:111, :111] + plane(n=111, east_deg=3.0)
    moon = {"t": {"90": 10.0, "270": 10.0, "810": 10.0}}
    record = ground.area_record(z, 90.0, moon)
    for baseline in ("90", "270", "810"):
        assert record["roughness_vs_moon"]["t"][baseline] == pytest.approx(record["roughness_m"][baseline] / 10.0,
                                                                        abs=0.002)
    assert record["landform"] in {"plain", "rolling ground", "hills", "mountains"}

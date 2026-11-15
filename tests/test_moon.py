# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
import json
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from twinfinder import moon


def test_window_values_use_the_files_own_scale_and_offset(tmp_path):
    # NASA Goddard stores illumination as int16 with scale 4e-05, and permanent
    # shadow as -20000 / 20000 with scale 2.5e-05 and offset 0.5.
    path = tmp_path / "scaled.tif"
    raw = np.array([[20000, -20000], [0, -32768]], dtype="int16")
    with rasterio.open(path, "w", driver="GTiff", height=2, width=2, count=1, dtype="int16",
                       nodata=-32768, transform=from_origin(0.0, 480.0, 240.0, 240.0)) as ds:
        ds.write(raw, 1)
        ds.scales = (2.5e-05,)
        ds.offsets = (0.5,)
    values = moon.read_scaled_window(path, (0.0, 0.0, 480.0, 480.0))
    assert values[0, 0] == pytest.approx(1.0)
    assert values[0, 1] == pytest.approx(0.0)
    assert values[1, 0] == pytest.approx(0.5)
    assert np.isnan(values[1, 1])


def test_pole_maps_to_minus_90():
    lat, _ = moon.polar_xy_to_latlon(0.0, 0.0)
    assert lat == pytest.approx(-90.0)


def test_one_degree_from_pole_is_about_30_km():
    lat, lon = moon.polar_xy_to_latlon(0.0, 30323.0)  # along the 0-degree meridian
    assert lat == pytest.approx(-89.0, abs=0.01)
    assert lon == pytest.approx(0.0, abs=1e-6)


def test_positive_x_is_90_east():
    _, lon = moon.polar_xy_to_latlon(30323.0, 0.0)
    assert lon == pytest.approx(90.0)


def test_four_targets_with_goddard_urls():
    assert [t.pgda_site for t in moon.TARGETS] == ["Site01", "Site23", "Site20v2", "DM2"]
    assert moon.TARGETS[0].dem_url == (
        "https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/Site01/Site01_final_adj_5mpp_surf.tif")


def tilted(deg, rows, cols, pixel_m=90.0):
    x = np.arange(cols) * pixel_m
    return np.tile(x * np.tan(np.radians(deg)), (rows, 1))


def test_every_piece_of_a_uniform_site_matches_the_whole_site():
    out = moon.self_overlap(tilted(10.5, 200, 200), 90.0)  # 18 km across
    assert out == {"p10": pytest.approx(1.0), "median": pytest.approx(1.0), "p90": pytest.approx(1.0)}


def two_part_site():
    """20 km across: the west half slopes 2.5 degrees, the east half 20.5 degrees."""
    x = np.arange(222) * 90.0
    half = x[111]
    profile = np.where(x < half, x * np.tan(np.radians(2.5)),
                       half * np.tan(np.radians(2.5)) + (x - half) * np.tan(np.radians(20.5)))
    return np.tile(profile, (222, 1))


def test_pieces_of_a_two_part_site_match_it_only_partly():
    out = moon.self_overlap(two_part_site(), 90.0)
    assert out["p10"] == pytest.approx(0.5, abs=0.03)     # a piece inside one half shares half the histogram
    assert out["median"] == pytest.approx(0.7, abs=0.03)
    assert out["p90"] == pytest.approx(0.9, abs=0.03)     # pieces across the middle match best


def test_pieces_are_cut_down_the_site_as_well_as_across():
    # The same site turned a quarter: a gentle north half and a steep south half.
    out = moon.self_overlap(two_part_site().T, 90.0)
    assert out["p10"] == pytest.approx(0.5, abs=0.03)
    assert out["median"] == pytest.approx(0.7, abs=0.03)
    assert out["p90"] == pytest.approx(0.9, abs=0.03)


def test_a_site_smaller_than_one_piece_has_no_self_overlap():
    out = moon.self_overlap(tilted(10.5, 100, 100), 90.0)  # 9 km across
    assert out == {"p10": None, "median": None, "p90": None}


def test_a_piece_is_111_pixels_of_90_m_like_an_earth_cell():
    one = {"p10": pytest.approx(1.0), "median": pytest.approx(1.0), "p90": pytest.approx(1.0)}
    none = {"p10": None, "median": None, "p90": None}
    assert moon.self_overlap(tilted(10.5, 111, 111), 90.0) == one   # exactly one piece: the site itself
    assert moon.self_overlap(tilted(10.5, 110, 111), 90.0) == none  # one row short
    assert moon.self_overlap(tilted(10.5, 111, 110), 90.0) == none  # one column short


def write_raster(path, values, left, top, pixel_m, scale=None, offset=None):
    with rasterio.open(path, "w", driver="GTiff", height=values.shape[0], width=values.shape[1], count=1,
                       dtype=values.dtype, transform=from_origin(left, top, pixel_m, pixel_m)) as ds:
        ds.write(values, 1)
        if scale is not None:
            ds.scales, ds.offsets = (scale,), (offset,)


def test_fingerprint_adds_self_overlap_to_the_90m_terrain_only(tmp_path):
    # An 11 km square site, 10 to 21 km from the pole, sloping 10.5 degrees everywhere.
    write_raster(tmp_path / "dem.tif", tilted(10.5, 2200, 2200, 5.0).astype("float32"), 10_000.0, 21_000.0, 5.0)
    coarse = np.full((100, 100), 12500, dtype="int16")
    write_raster(tmp_path / "illum.tif", coarse, 0.0, 24_000.0, 240.0, scale=4e-05, offset=0.0)
    write_raster(tmp_path / "psr.tif", -coarse, 0.0, 24_000.0, 240.0, scale=2.5e-05, offset=0.5)
    fp = moon.fingerprint(moon.TARGETS[0], tmp_path / "dem.tif", tmp_path / "illum.tif", tmp_path / "psr.tif")
    assert fp["terrain"]["90m"]["self_overlap_10km"] == {
        "p10": pytest.approx(1.0), "median": pytest.approx(1.0), "p90": pytest.approx(1.0)}
    assert list(fp["terrain"]["90m"]) == ["pixel_m", "median_slope_deg", "p90_slope_deg", "relief_m",
                                          "slope_hist", "self_overlap_10km"]
    assert list(fp["terrain"]["30m"]) == ["pixel_m", "median_slope_deg", "p90_slope_deg", "relief_m", "slope_hist"]
    assert list(fp) == ["id", "name", "why", "source", "centre_lat", "centre_lon", "lat_most_poleward",
                        "lat_least_poleward", "sun_max_elev_deg", "sun_max_elev_range_deg", "extent_km",
                        "terrain", "illumination_mean", "illumination_max", "permanent_shadow_fraction"]
    assert fp["terrain"]["90m"]["median_slope_deg"] == pytest.approx(10.5, abs=0.01)
    assert fp["illumination_mean"] == pytest.approx(0.5)
    assert fp["permanent_shadow_fraction"] == pytest.approx(0.0)


OFFICIAL_NAMES = ["Connecting Ridge", "Malapert Massif", "Mons Mouton", "Nobile Rim 2"]   # the names on NASA's lists
RIDGE_WHY = ("One of NASA's 13 candidate Artemis III regions of 2022 ('Connecting Ridge'); not among the nine kept in "
             "2024. NASA Goddard's lighting study of the 5 m models found it has the most area lit more than 70 % of "
             "the time.")


def test_the_targets_carry_the_official_names_and_a_sourced_reason():
    assert [t.id for t in moon.TARGETS] == ["connecting-ridge", "malapert", "mons-mouton", "nobile-rim-2"]
    assert [t.name for t in moon.TARGETS] == OFFICIAL_NAMES
    assert moon.TARGETS[0].why == RIDGE_WHY                          # the wording the lunar cards found sources for
    assert not any("precursor" in t.why or "Moon Base" in t.why for t in moon.TARGETS)


def test_the_stored_target_file_has_the_names_and_reasons_of_the_code():
    # data/derived/moon_targets.json is written by scripts/build_moon_fingerprints.py from moon.TARGETS;
    # the rest of the pipeline takes the names from that file.
    stored = json.loads(Path("data/derived/moon_targets.json").read_text())
    assert [(t["id"], t["name"], t["why"]) for t in stored] == [(t.id, t.name, t.why) for t in moon.TARGETS]

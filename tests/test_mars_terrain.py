import math

import numpy as np
import pytest

from twinfinder import mars_terrain as mt

PLANETS = [
    pytest.param(mt.MARS_RADIUS_M, mt.MARS_PIXEL_DEG, id="mars"),
    pytest.param(mt.EARTH_RADIUS_M, mt.EARTH_PIXEL_DEG, id="earth"),
]


def plane_on_grid(lat0, radius_m, pixel_deg, slope_deg, azimuth_deg, n=5):
    """A plane of known slope laid on a latitude-longitude grid centred on lat0, longitude 0.

    East is measured along each row with that row's own cos(latitude), north along the meridian,
    so at the centre pixel the true gradient is exactly tan(slope) in the direction azimuth.
    Returns the heights (rows from north to south) and the row latitudes."""
    k = np.arange(n) - n // 2
    lats = lat0 - k * pixel_deg                       # first row is the northernmost
    lons = k * pixel_deg
    north_m = radius_m * np.radians(lats - lat0)[:, None] * np.ones((1, n))
    east_m = radius_m * np.cos(np.radians(lats))[:, None] * np.radians(lons)[None, :]
    t = math.tan(math.radians(slope_deg))
    a = math.radians(azimuth_deg)
    z = t * (math.sin(a) * east_m + math.cos(a) * north_m)
    return z, lats


@pytest.mark.parametrize("radius_m, pixel_deg", PLANETS)
@pytest.mark.parametrize("lat0", [0.0, 45.0, 80.0, -80.0])
@pytest.mark.parametrize("azimuth", [0.0, 90.0, 30.0])
@pytest.mark.parametrize("slope", [0.3, 5.0, 20.0])
def test_tilted_plane_gives_its_slope_with_metric_spacing(radius_m, pixel_deg, lat0, azimuth, slope):
    z, lats = plane_on_grid(lat0, radius_m, pixel_deg, slope, azimuth)
    s = mt.slope_deg(z, lats, pixel_deg, radius_m)
    assert s[2, 2] == pytest.approx(slope, rel=1e-6)


def test_east_west_spacing_shrinks_with_latitude():
    # the same height step per pixel is twice as steep where a pixel is half as wide (60 degrees)
    z = np.tile(np.arange(5.0) * 10.0, (5, 1))
    at_equator = mt.slope_deg(z, np.zeros(5), mt.MARS_PIXEL_DEG, mt.MARS_RADIUS_M)[2, 2]
    at_sixty = mt.slope_deg(z, np.full(5, 60.0), mt.MARS_PIXEL_DEG, mt.MARS_RADIUS_M)[2, 2]
    assert math.tan(math.radians(at_sixty)) == pytest.approx(2 * math.tan(math.radians(at_equator)), rel=1e-9)


def test_outer_ring_and_neighbours_of_unknown_pixels_have_no_slope():
    z = np.zeros((6, 6))
    z[3, 3] = np.nan
    s = mt.slope_deg(z, np.zeros(6), mt.EARTH_PIXEL_DEG, mt.EARTH_RADIUS_M)
    assert np.isnan(s[0, :]).all() and np.isnan(s[-1, :]).all()
    assert np.isnan(s[:, 0]).all() and np.isnan(s[:, -1]).all()
    for r, c in [(2, 3), (4, 3), (3, 2), (3, 4)]:           # its four neighbours use it
        assert np.isnan(s[r, c])
    assert np.isnan(s[3, 3])                                # it has neighbours but no height: it is not a pixel
    assert s[2, 2] == 0.0 and s[1, 1] == 0.0


def test_slope_edges_are_the_plans():
    assert mt.SLOPE_EDGES_DEG == [0, 0.1, 0.25, 0.5, 1, 1.5, 2, 3, 4, 6, 8, 12, 16, 24, 90]
    assert mt.N_BINS == 14


def test_histogram_sums_to_one_and_leaves_out_unknown():
    s = np.array([0.05, 0.3, 0.3, np.nan, 50.0, 89.99, np.nan])
    h = mt.slope_histogram(s)
    assert len(h) == 14
    assert sum(h) == pytest.approx(1.0)
    assert h[0] == pytest.approx(0.2)        # 0.05 in [0, 0.1)
    assert h[2] == pytest.approx(0.4)        # 0.3 in [0.25, 0.5)
    assert h[13] == pytest.approx(0.4)       # 50 and 89.99 in [24, 90]
    assert h[1] == 0.0


def test_values_on_an_edge_go_in_the_bin_above():
    h = mt.slope_histogram(np.array([0.1, 1.0, 24.0]))
    assert h[1] == pytest.approx(1 / 3) and h[4] == pytest.approx(1 / 3) and h[13] == pytest.approx(1 / 3)


def test_histogram_of_no_known_pixel_is_unknown():
    assert mt.slope_histogram(np.array([np.nan, np.nan])) is None
    assert mt.slope_histogram(np.array([])) is None


def test_overlap_identical_is_one_disjoint_is_zero_unknown_is_unknown():
    flat = mt.slope_histogram(np.full(50, 0.05))
    steep = mt.slope_histogram(np.full(50, 30.0))
    mixed = mt.slope_histogram(np.array([0.05, 30.0]))
    assert mt.histogram_overlap(flat, flat) == pytest.approx(1.0)
    assert mt.histogram_overlap(mixed, mixed) == pytest.approx(1.0)
    assert mt.histogram_overlap(flat, steep) == pytest.approx(0.0)
    assert mt.histogram_overlap(flat, mixed) == pytest.approx(0.5)
    assert mt.histogram_overlap(flat, None) is None


def test_self_overlap_of_an_even_box_is_one():
    assert mt.self_overlap(np.full((64, 64), 2.5)) == pytest.approx(1.0)


def test_self_overlap_is_the_median_of_the_sixteen_sub_boxes():
    s = np.full((64, 64), 0.05)
    s[:16, :16] = 30.0                                     # one sub-box of sixteen is steep
    # the box is 15/16 flat: fifteen flat sub-boxes overlap it by 15/16, the steep one by 1/16
    assert mt.self_overlap(s) == pytest.approx(15 / 16)
    half = np.full((64, 64), 0.05)
    half[32:, :] = 30.0                                    # every sub-box is pure, the box is half and half
    assert mt.self_overlap(half) == pytest.approx(0.5)


def test_self_overlap_leaves_out_sub_boxes_without_slopes():
    s = np.full((64, 64), 0.05)
    s[:16, :16] = np.nan
    assert mt.self_overlap(s) == pytest.approx(1.0)
    assert mt.self_overlap(np.full((64, 64), np.nan)) is None


def test_area_summary_reports_slopes_relief_and_known_pixels():
    slopes = np.array([[1.0, 2.0, np.nan], [3.0, 4.0, 5.0]])
    heights = np.arange(101.0)                            # 0..100 m: 95th minus 5th percentile is 90 m
    out = mt.area_summary(slopes, heights)
    assert out["pixels"] == 5
    assert out["median_slope_deg"] == pytest.approx(3.0)
    assert out["p90_slope_deg"] == pytest.approx(np.percentile([1, 2, 3, 4, 5], 90))
    assert out["relief_m"] == pytest.approx(90.0)
    assert sum(out["slope_hist"]) == pytest.approx(1.0)


def test_area_summary_of_nothing_is_unknown_not_zero():
    out = mt.area_summary(np.full((3, 3), np.nan), np.full(9, np.nan))
    assert out == {"slope_hist": None, "median_slope_deg": None, "p90_slope_deg": None,
                   "relief_m": None, "pixels": 0}


def test_square_id_has_two_decimals():
    assert mt.square_id(-77.75, 161.25) == "m_-77.75_161.25"
    assert mt.square_id(0.25, -179.75) == "m_0.25_-179.75"


def test_read_megdr_follows_the_label(tmp_path):
    values = np.array([[1, -2, 300, -8206], [21181, 0, 7, -1]], dtype=">i2")
    (tmp_path / "t.img").write_bytes(values.tobytes())
    (tmp_path / "t.lbl").write_text(
        "PDS_VERSION_ID = PDS3\r\nRECORD_BYTES = 8\r\n^IMAGE = \"T.IMG\"\r\nOBJECT = IMAGE\r\n"
        " LINES = 2\r\n LINE_SAMPLES = 4\r\n SAMPLE_TYPE = MSB_INTEGER\r\n SAMPLE_BITS = 16\r\n"
        " UNIT = METER\r\nEND_OBJECT = IMAGE\r\nOBJECT = IMAGE_MAP_PROJECTION\r\n"
        " MAP_RESOLUTION = 2.0 <PIXEL/DEGREE>\r\n MAXIMUM_LATITUDE = 90.0 <DEGREE>\r\n"
        " WESTERNMOST_LONGITUDE = 0.0 <DEGREE>\r\nEND_OBJECT = IMAGE_MAP_PROJECTION\r\nEND\r\n")
    z, info = mt.read_megdr(tmp_path / "t.img", tmp_path / "t.lbl")
    assert z.tolist() == values.astype(int).tolist()
    assert info["ppd"] == 2.0 and info["top_lat"] == 90.0 and info["west_lon"] == 0.0
    assert info["unit"] == "METER"


def test_read_megdr_refuses_a_layout_it_does_not_know(tmp_path):
    (tmp_path / "t.img").write_bytes(b"\0" * 16)
    (tmp_path / "t.lbl").write_text("OBJECT = IMAGE\n LINES = 2\n LINE_SAMPLES = 4\n SAMPLE_TYPE = PC_REAL\n"
                                    " SAMPLE_BITS = 16\nEND_OBJECT = IMAGE\n MAP_RESOLUTION = 2.0\n"
                                    " MAXIMUM_LATITUDE = 90.0\n WESTERNMOST_LONGITUDE = 0.0\nEND\n")
    with pytest.raises(ValueError):
        mt.read_megdr(tmp_path / "t.img", tmp_path / "t.lbl")


def global_mars(ppd=4):
    """A small global map whose heights encode the pixel centre: 1000 * latitude + longitude."""
    lats = 90 - (np.arange(180 * ppd) + 0.5) / ppd
    lons = (np.arange(360 * ppd) + 0.5) / ppd
    return 1000.0 * lats[:, None] + lons[None, :], lats, lons


def test_site_box_is_centred_and_has_a_one_pixel_rim():
    z, _, _ = global_mars(ppd=4)
    box, lats, lons = mt.site_box(z, 18.4, 77.4, ppd=4, box_deg=2.0)
    assert box.shape == (8 + 2, 8 + 2)
    inner_lats, inner_lons = lats[1:-1], lons[1:-1]
    assert (inner_lats >= 17.4).all() and (inner_lats < 19.4).all()
    assert (inner_lons >= 76.4).all() and (inner_lons < 78.4).all()
    assert box[1, 1] == pytest.approx(1000 * inner_lats[0] + inner_lons[0])
    assert lats[0] > lats[1]                              # north first, as in the file


def test_site_box_wraps_around_longitude_zero():
    z, _, _ = global_mars(ppd=4)
    box, lats, lons = mt.site_box(z, 10.0, 0.3, ppd=4, box_deg=2.0)
    assert box.shape == (10, 10)
    lon_of_pixel = box[1, :] - 1000 * lats[1]
    expected = np.mod(lons, 360.0)
    assert lon_of_pixel == pytest.approx(expected)
    assert (np.mod(lons[1:-1] - 359.3, 360.0) < 2.0).all()


def test_site_record_of_a_tilted_mars_box():
    ppd = 32
    lats = 90 - (np.arange(180 * ppd) + 0.5) / ppd
    north_m = mt.MARS_RADIUS_M * np.radians(lats)
    t = math.tan(math.radians(3.5))
    z = np.broadcast_to((t * north_m)[:, None], (180 * ppd, 360 * ppd))   # a 3.5 degree tilt to the north
    rec = mt.site_record(z, 39.0, 192.1, ppd=ppd)
    assert rec["pixels"] == 64 * 64
    assert rec["median_slope_deg"] == pytest.approx(3.5, rel=1e-6)
    assert rec["slope_hist"][7] == pytest.approx(1.0)          # [3, 4)
    assert rec["self_overlap"] == pytest.approx(1.0)
    assert rec["relief_m"] == pytest.approx(0.9 * 2 * math.radians(1) * mt.MARS_RADIUS_M * t, rel=0.02)


def earth_band(n_rows=2, n_cols=4, px=4, top_lat=60.0):
    """Heights and land for a band of n_rows x n_cols squares of px pixels, with one rim row above and below."""
    pixel_deg = 0.5 / px
    rows = n_rows * px + 2
    lats = top_lat + pixel_deg / 2 - np.arange(rows) * pixel_deg
    north_m = mt.EARTH_RADIUS_M * np.radians(lats)
    t = math.tan(math.radians(2.5))
    z = np.repeat((t * (north_m - north_m[0]))[:, None], n_cols * px, axis=1)
    land = np.ones(z.shape, dtype=bool)
    return z, land, pixel_deg


def test_band_squares_keep_squares_with_enough_land_and_measure_them():
    z, land, pixel_deg = earth_band()
    land[1:5, 4:8] = False                 # square (row 0, col 1): no land
    land[1:5, 8:10] = False                # square (row 0, col 2): 8 of 16 pixels are land
    land[5:9, 12:16] = False
    land[5, 12] = True                     # square (row 1, col 3): 1 of 16 land pixels, below 20 percent
    out = mt.band_squares(z, land, top_lat=60.0, pixel_deg=pixel_deg, px=4, radius_m=mt.EARTH_RADIUS_M,
                          west_lon=-180.0)
    first = mt.square_id(59.75, -179.75)
    assert set(out) == {first, mt.square_id(59.75, -178.75), mt.square_id(59.75, -178.25),
                        mt.square_id(59.25, -179.75), mt.square_id(59.25, -179.25),
                        mt.square_id(59.25, -178.75)}
    assert out[first]["land_share"] == 1.0
    assert out[first]["pixels"] == 12      # its last column touches the square with no land
    assert out[first]["median_slope_deg"] == pytest.approx(2.5, rel=1e-6)
    assert out[first]["slope_hist"][6] == pytest.approx(1.0)     # [2, 3)
    half = out[mt.square_id(59.75, -178.75)]
    assert half["land_share"] == 0.5
    assert half["pixels"] == 4             # 8 land pixels, of which those touching water have no slope
    assert half["elev_mean_m"] == pytest.approx(np.mean(z[1:5, 10:12]))


def test_band_squares_wrap_in_longitude_and_leave_water_out():
    z, land, pixel_deg = earth_band(n_rows=1, n_cols=2, px=4)
    z[:, -1] = 100_000.0                   # a cliff on the last column (pixels here are 7 km wide), across 180
    out = mt.band_squares(z, land, top_lat=60.0, pixel_deg=pixel_deg, px=4, radius_m=mt.EARTH_RADIUS_M,
                          west_lon=-180.0)
    west = out[mt.square_id(59.75, -179.75)]
    assert west["p90_slope_deg"] > 45      # the first column sees the cliff across the antimeridian
    z2, land2, _ = earth_band(n_rows=1, n_cols=2, px=4)
    land2[:, -1] = False                   # the cliff is water: it is left out, not used
    z2[:, -1] = -5000.0
    out2 = mt.band_squares(z2, land2, top_lat=60.0, pixel_deg=pixel_deg, px=4, radius_m=mt.EARTH_RADIUS_M,
                           west_lon=-180.0)
    assert out2[mt.square_id(59.75, -179.75)]["p90_slope_deg"] == pytest.approx(2.5, rel=1e-6)
    east = out2[mt.square_id(59.75, -179.25)]
    assert east["land_share"] == 0.75
    assert east["relief_m"] == pytest.approx(out2[mt.square_id(59.75, -179.75)]["relief_m"])  # no -5000 m


def test_rounding_keeps_unknown_and_shortens_numbers():
    rec = {"slope_hist": [0.123456, 0.876544], "median_slope_deg": 1.234567, "p90_slope_deg": None,
           "relief_m": 123.456, "elev_mean_m": -12.345, "land_share": 0.333333, "pixels": 7,
           "self_overlap": 0.987654}
    out = mt.rounded(rec)
    assert out == {"slope_hist": [0.1235, 0.8765], "median_slope_deg": 1.2346, "p90_slope_deg": None,
                   "relief_m": 123.5, "elev_mean_m": -12.3, "land_share": 0.3333, "pixels": 7,
                   "self_overlap": 0.9877}


# ---------------------------------------------------------------- the build script's own pieces

from scripts import build_mars_terrain as build  # noqa: E402


def test_bands_cover_85_south_to_84_north_in_whole_squares():
    bands = build.band_plan()
    assert bands[0][0] == 84.0
    assert sum(n for _, n in bands) == (84 + 85) * 2           # 338 square rows
    tops = [top for top, _ in bands]
    assert all(t2 == pytest.approx(t1 - n * 0.5) for (t1, n), t2 in zip(bands, tops[1:]))
    last_top, last_n = bands[-1]
    assert last_top - last_n * 0.5 == pytest.approx(-85.0)


def test_window_rows_add_one_rim_row_above_and_below():
    start, stop = build.window_rows(84.0, 10)
    assert start == 6 * 60 - 1                                # 84 N is row 360 of a map that starts at 90 N
    assert stop - start == 10 * 30 + 2


def test_land_mask_takes_pixels_whose_centre_is_inside():
    square = {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]}
    m = build.land_mask([square], row_start=0, rows=12, width=16, pixel_deg=0.25, west_lon=-1.0, top_lat=2.0)
    assert m.dtype == bool and m.shape == (12, 16)
    assert m.sum() == 16                                       # 1 x 1 degree at 0.25 degree pixels
    assert m[4:8, 4:8].all()                                   # rows for 1..0 N, columns for 0..1 E


def test_coast_counts_find_land_pixels_that_touch_water_across_the_antimeridian():
    land = np.ones((4, 6), dtype=bool)          # one rim row above and below, two band rows
    land[1, 5] = False                          # water on the last column: its neighbours lose their slope
    land[0, 2] = False                          # water in the rim row above touches band pixel (1, 2)
    z = np.full((4, 6), 100.0)
    z[1, 0] = -80.0                             # a land pixel below sea level next to the water across 180
    z[2, 5] = -10.0                             # below sea level, next to the water above it
    c = build.coast_counts(z, land)
    assert c["land_pixels"] == 11
    # touching water: (1,4) and (1,0) beside (1,5); (2,5) below it; (1,2) below the rim water
    assert c["land_pixels_touching_water"] == 4
    assert c["of_them_below_0_m"] == 2
    assert c["of_them_below_minus_50_m"] == 1
    assert c["land_pixels_below_0_m"] == 2


# ---- MARS-REVIEW: tests for breakages the suite above did not catch ---------------------------------

def test_mars_radius_is_the_mars_radius_and_one_mola_pixel_is_1_85_km():
    # the tests above take the radius from the module, so a wrong radius (Earth's, say) passed them all
    assert 3_389_000 <= mt.MARS_RADIUS_M <= 3_397_000
    assert 6_356_000 <= mt.EARTH_RADIUS_M <= 6_379_000
    assert mt.MARS_RADIUS_M * math.radians(mt.MARS_PIXEL_DEG) == pytest.approx(1852.0, abs=2.0)
    assert mt.EARTH_RADIUS_M * math.radians(mt.EARTH_PIXEL_DEG) == pytest.approx(1853.0, abs=2.0)


def test_site_record_uses_the_mars_radius_by_default():
    # heights fall 18.52 m a row southward on a Mars grid at the equator: slope atan(18.52 / 1852) = 0.573 deg
    ppd = 32
    z = -18.52 * np.arange(160, dtype=float)[:, None] * np.ones((1, 160))
    rec = mt.site_record(z, 0.0, 2.5, ppd=ppd, top_lat=2.5, west_lon=0.0)
    assert rec["median_slope_deg"] == pytest.approx(math.degrees(math.atan(18.52 / 1852.0)), abs=0.003)


def test_band_squares_keep_a_square_of_exactly_20_percent_land():
    px = 5
    z = np.zeros((px + 2, 2 * px))
    land = np.zeros_like(z, dtype=bool)
    land[3, 0:5] = True                       # 5 of the 25 pixels of the first square: share 0.2
    out = mt.band_squares(z, land, top_lat=10.0, pixel_deg=0.1, px=px)
    assert list(out) == ["m_9.75_-179.75"]
    assert out["m_9.75_-179.75"]["land_share"] == pytest.approx(0.2)

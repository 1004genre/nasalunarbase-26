# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
import math

import numpy as np
import pytest

from twinfinder import earth, horizon

PIXEL = 90.0
RADIUS = 6371000.0 * 7.0 / 6.0  # Earth radius as standard refraction makes it look


def expected_deg(height_m, distance_m, eye_m=2.0):
    """Angle to a point height_m above the viewer's ground at distance_m, on the refracting sphere."""
    return math.degrees(math.atan((height_m - eye_m) / distance_m - distance_m / (2.0 * RADIUS)))


def slow_horizon(z, row, col, azimuth_deg, max_km, eye_m=2.0, step=0.25):
    """Plain ray march from one pixel in quarter-pixel steps, reading the grid bilinearly."""
    a = math.radians(azimuth_deg)
    eye = z[row, col] + eye_m
    best = -math.inf
    for k in range(1, int(max_km * 1000.0 / (PIXEL * step)) + 1):
        r, c = row - k * step * math.cos(a), col + k * step * math.sin(a)
        r0, c0 = math.floor(r), math.floor(c)
        if r0 < 0 or c0 < 0 or r0 + 1 >= z.shape[0] or c0 + 1 >= z.shape[1]:
            break
        fr, fc = r - r0, c - c0
        height = ((1 - fr) * ((1 - fc) * z[r0, c0] + fc * z[r0, c0 + 1])
                  + fr * ((1 - fc) * z[r0 + 1, c0] + fc * z[r0 + 1, c0 + 1]))
        d = k * step * PIXEL
        best = max(best, (height - eye) / d - d / (2.0 * RADIUS))
    return max(-1.0, math.degrees(math.atan(best)))


def centre_block(n, size):
    start = (n - size) // 2
    return slice(start, start + size), slice(start, start + size)


def test_shared_constants():
    assert horizon.AZ_SECTORS == 36
    assert list(horizon.ELEV_EDGES_DEG) == [0.0, 0.5, 1.0, 1.5, 2.08, 3.0, 4.0, 5.55, 6.11, 7.59]
    assert list(horizon.SECTOR_CENTRES_DEG) == [5.0 + 10.0 * k for k in range(36)]


def test_constants_are_the_same_as_the_sun_table_uses():
    from twinfinder import sun
    assert horizon.AZ_SECTORS == sun.AZ_SECTORS
    assert list(horizon.ELEV_EDGES_DEG) == list(sun.ELEV_EDGES_DEG)


def test_flat_plain_is_open_in_every_sector_and_bin():
    z = np.full((400, 400), 120.0, dtype="float32")
    inner = centre_block(400, 20)
    h = horizon.horizon_deg(z, PIXEL, horizon.SECTOR_CENTRES_DEG, inner, max_km=15.0)
    assert h.shape == (36, 20, 20) and h.dtype == np.float32
    dip = -math.degrees(math.sqrt(2.0 * 2.0 / RADIUS))  # horizon of a 2 m high eye over a smooth sphere
    assert h.max() < 0.0
    assert np.abs(h - dip).max() < 0.001  # without refraction the dip would be 0.003 degrees deeper
    share = horizon.open_share(h, np.ones((20, 20), dtype=bool), horizon.ELEV_EDGES_DEG)
    assert share.shape == (36, 9) and share.dtype == np.float32
    assert (share == 1.0).all()


def test_wall_to_the_north_hides_the_north_and_leaves_the_south_open():
    n = 620
    z = np.zeros((n, n), dtype="float32")
    inner = centre_block(n, 4)
    wall_m, distance_px = 500.0, 111  # a 500 m step up, 9.99 km north of the block's north row
    z[: inner[0].start - distance_px + 1, :] = wall_m
    h = horizon.horizon_deg(z, PIXEL, horizon.SECTOR_CENTRES_DEG, inner, max_km=25.0)
    for sector, azimuth in ((0, 5.0), (35, 355.0), (1, 15.0), (34, 345.0), (4, 45.0), (31, 315.0)):
        for i in range(4):
            d = (distance_px + i) * PIXEL / math.cos(math.radians(azimuth))
            assert h[sector, i, :] == pytest.approx(expected_deg(wall_m, d), abs=0.1)
    assert expected_deg(wall_m, distance_px * PIXEL) == pytest.approx(2.82, abs=0.01)
    south = h[9:27]  # azimuths 95 to 265
    assert south.max() < 0.0
    share = horizon.open_share(h, np.ones((4, 4), dtype=bool), horizon.ELEV_EDGES_DEG)
    assert (share[9:27] == 1.0).all()
    # the wall stands 2.8 degrees high: bins that start below it are shut, bins from 3 degrees up are open
    assert (share[[0, 35], :5] == 0.0).all() and (share[[0, 35], 5:] == 1.0).all()


def test_azimuth_runs_clockwise_from_north():
    z = np.zeros((300, 300), dtype="float32")
    z[:, 200:] = 300.0  # high ground 4.5 km to the east
    h = horizon.horizon_deg(z, PIXEL, [0.0, 90.0, 180.0, 270.0], (slice(150, 151), slice(150, 151)), max_km=10.0)
    assert h[1, 0, 0] == pytest.approx(expected_deg(300.0, 50 * PIXEL), abs=0.1)
    assert h[0, 0, 0] < 0.0 and h[2, 0, 0] < 0.0 and h[3, 0, 0] < 0.0


def test_pixel_on_a_peak_sees_a_negative_horizon():
    n = 600
    rows, cols = np.mgrid[:n, :n]
    distance = np.hypot(rows - 300, cols - 300) * PIXEL
    z = np.maximum(0.0, 100.0 - 0.05 * distance).astype("float32")  # 100 m cone on a plain at sea level
    h = horizon.horizon_deg(z, PIXEL, [0.0, 45.0, 90.0, 180.0, 275.0], (slice(300, 301), slice(300, 301)), max_km=25.0)
    assert h.shape == (5, 1, 1)
    # the plain's own horizon would be 37 km out; within 25 km the highest thing seen is the plain's edge
    assert h.ravel() == pytest.approx(expected_deg(0.0, 25000.0, eye_m=102.0), abs=0.005)
    assert (h < -0.3).all()


def test_horizon_is_clipped_at_minus_one_degree():
    z = np.zeros((300, 300), dtype="float32")
    z[150, 150] = 3000.0
    h = horizon.horizon_deg(z, PIXEL, [0.0, 90.0], (slice(150, 151), slice(150, 151)), max_km=10.0)
    assert (h == -1.0).all()


def test_eye_height_matters_next_to_a_low_bank():
    z = np.zeros((200, 200), dtype="float32")
    z[:99, :] = 3.0  # a 3 m bank one pixel north of the viewer
    inner = (slice(100, 101), slice(100, 101))
    low = horizon.horizon_deg(z, PIXEL, [0.0], inner, max_km=5.0, eye_m=2.0)
    high = horizon.horizon_deg(z, PIXEL, [0.0], inner, max_km=5.0, eye_m=10.0)
    assert low[0, 0, 0] > 0.0 > high[0, 0, 0]


def test_ground_between_grid_lines_is_seen_close_by():
    # looking north-east out of a notch: the north and east neighbours stand 60 m high, the diagonal
    # one does not. The ray runs between the two over ground that rises as 120 t (1 - t) metres,
    # t being the fraction of the way to the diagonal neighbour 127 m off.
    z = np.zeros((60, 60), dtype="float32")
    z[29, 30] = z[30, 31] = 60.0
    h = horizon.horizon_deg(z, PIXEL, [45.0], (slice(30, 31), slice(30, 31)), max_km=2.0)
    t = math.sqrt(2.0 / 120.0)  # where (120 t (1 - t) - 2) / (127.3 t) peaks
    steepest = math.degrees(math.atan((120.0 * t * (1 - t) - 2.0) / (t * math.sqrt(2.0) * PIXEL)))
    assert steepest == pytest.approx(35.0, abs=0.1)
    assert h[0, 0, 0] == pytest.approx(steepest, abs=1.0)


def test_thin_ridge_far_away_is_not_stepped_over():
    # beyond the near field the march reads every grid line it crosses, so a ridge one pixel thick
    # is met whether it lies an even or an odd number of pixels away, straight on or at a slant
    n, c = 300, 150
    rows = np.zeros((n, n), dtype="float32")
    rows[c - 100, :] = rows[c + 101, :] = 300.0  # 100 pixels north and 101 pixels south
    cols = np.zeros((n, n), dtype="float32")
    cols[:, c + 100] = cols[:, c - 101] = 300.0  # 100 pixels east and 101 pixels west
    inner = (slice(c, c + 1), slice(c, c + 1))
    cases = ((rows, [(0.0, 100, 0.0), (20.0, 100, 20.0), (180.0, 101, 0.0), (200.0, 101, 20.0)]),
             (cols, [(90.0, 100, 0.0), (70.0, 100, 20.0), (270.0, 101, 0.0), (250.0, 101, 20.0)]))
    for z, rays in cases:
        h = horizon.horizon_deg(z, PIXEL, [azimuth for azimuth, _, _ in rays], inner, max_km=12.0)
        for i, (azimuth, pixels_off, slant_deg) in enumerate(rays):
            d = pixels_off * PIXEL / math.cos(math.radians(slant_deg))
            assert h[i, 0, 0] == pytest.approx(expected_deg(300.0, d), abs=0.05), azimuth


def test_pixel_size_sets_the_distance():
    z = np.zeros((300, 300), dtype="float32")
    z[:100, :] = 200.0  # high ground from 51 pixels north of the viewer
    inner = (slice(150, 151), slice(150, 151))
    for pixel_m, angle in ((30.0, 7.37), (90.0, 2.45)):
        h = horizon.horizon_deg(z, pixel_m, [0.0], inner, max_km=10.0)
        assert expected_deg(200.0, 51 * pixel_m) == pytest.approx(angle, abs=0.01)
        assert h[0, 0, 0] == pytest.approx(angle, abs=0.05)


def test_ground_beyond_the_reach_is_not_seen():
    z = np.zeros((400, 400), dtype="float32")
    z[:60, :] = 800.0  # high ground from 141 pixels (12.7 km) north of the viewer
    inner = (slice(200, 201), slice(200, 201))
    assert horizon.horizon_deg(z, PIXEL, [0.0], inner, max_km=10.0)[0, 0, 0] < 0.0
    seen = horizon.horizon_deg(z, PIXEL, [0.0], inner, max_km=15.0)[0, 0, 0]
    assert seen == pytest.approx(expected_deg(800.0, 141 * PIXEL), abs=0.05)


def test_ray_stops_at_the_edge_of_the_array():
    z = np.zeros((50, 50), dtype="float32")
    h = horizon.horizon_deg(z, PIXEL, horizon.SECTOR_CENTRES_DEG, centre_block(50, 2), max_km=25.0)
    assert np.isfinite(h).all() and (h < 0.0).all()


def test_matches_a_slow_ray_march_on_rough_ground():
    rng = np.random.default_rng(3)
    n = 260
    rows, cols = np.mgrid[:n, :n]
    z = np.zeros((n, n))
    for _ in range(40):  # forty hills, 0.3 to 1.5 km wide and up to 400 m high
        r, c, width = rng.uniform(0, n), rng.uniform(0, n), rng.uniform(3, 16)
        z += rng.uniform(50, 400) * np.exp(-((rows - r) ** 2 + (cols - c) ** 2) / (2 * width ** 2))
    z = z.astype("float32")
    inner = (slice(120, 140, None), slice(120, 140, None))
    azimuths = [0.0, 5.0, 45.0, 85.0, 135.0, 180.0, 215.0, 275.0, 355.0]
    fast = horizon.horizon_deg(z, PIXEL, azimuths, inner, max_km=10.0)
    slow = np.array([[[slow_horizon(z, r, c, a, 10.0) for c in range(120, 140, 5)]
                      for r in range(120, 140, 5)] for a in azimuths])
    error = np.abs(fast[:, ::5, ::5] - slow)
    assert slow.max() > 3.0  # the hills do hide part of the sky
    assert error.max() < 0.15 and error.mean() < 0.005


def test_open_share_counts_land_pixels_below_each_lower_edge():
    h = np.full((36, 2, 2), -0.04, dtype="float32")
    h[0] = [[-0.04, 0.2], [1.2, 9.0]]   # sector 0: one pixel open to the ground, the others shut in steps
    h[1] = [[2.08, 2.07], [50.0, 50.0]]  # sector 1: a horizon exactly on an edge does not count as below it
    land = np.array([[True, True], [True, True]])
    share = horizon.open_share(h, land, horizon.ELEV_EDGES_DEG)
    assert share[0] == pytest.approx([0.25, 0.5, 0.5, 0.75, 0.75, 0.75, 0.75, 0.75, 0.75])
    assert share[1] == pytest.approx([0.0, 0.0, 0.0, 0.0, 0.25, 0.5, 0.5, 0.5, 0.5])
    assert (share[2:] == 1.0).all()
    land[1, 1] = False  # the 9 degree pixel is water now
    share = horizon.open_share(h, land, horizon.ELEV_EDGES_DEG)
    assert share[0] == pytest.approx([1 / 3, 2 / 3, 2 / 3, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0])


def test_open_share_without_land_is_nan():
    h = np.zeros((36, 3, 3), dtype="float32")
    share = horizon.open_share(h, np.zeros((3, 3), dtype=bool), horizon.ELEV_EDGES_DEG)
    assert share.shape == (36, 9) and np.isnan(share).all()


# --- whole cells, with a made-up elevation window in place of the tiles ------------------------

def fake_window(surface, water):
    """Stand-in for earth.elevation_window: surface(x_m, y_m) is the height and water(x_m, y_m) the sea."""
    calls = []

    def window(lat, lon, half_km=5.0, pixel_m=90.0, mask_water=True, sea_as_zero=False):
        calls.append((half_km, pixel_m, mask_water, sea_as_zero))
        n = int(round(2 * half_km * 1000.0 / pixel_m))
        centres = -half_km * 1000.0 + (np.arange(n) + 0.5) * pixel_m
        x, y = np.meshgrid(centres, -centres)
        z = surface(x, y).astype("float32")
        if mask_water:
            z = np.where(water(x, y), np.nan, z)
        if sea_as_zero:
            z = np.where(np.isnan(z), np.float32(0.0), z)
        return z
    window.calls = calls
    return window


def test_cell_on_a_flat_island_is_open(monkeypatch):
    window = fake_window(lambda x, y: 30.0 + 0 * x, lambda x, y: x > 500.0)
    monkeypatch.setattr(earth, "elevation_window", window)
    share, north, south, valid = horizon.cell_open_share(70.0, 20.0, half_km=1.0, reach_km=8.0)
    assert share.shape == (36, 9) and (share == 1.0).all()
    assert -0.1 < north < 0.0 and -0.1 < south < 0.0
    assert valid == pytest.approx(0.75, abs=0.03)
    assert all(call[0] == 9.0 for call in window.calls)  # the window is the cell plus the reach


def test_cell_below_a_scarp_to_the_north(monkeypatch):
    window = fake_window(lambda x, y: np.where(y > 6000.0, 400.0, 0.0), lambda x, y: x < -1e9)
    monkeypatch.setattr(earth, "elevation_window", window)
    share, north, south, valid = horizon.cell_open_share(70.0, 20.0, half_km=1.0, reach_km=12.0)
    assert north == pytest.approx(expected_deg(400.0, 6000.0), abs=0.25)  # the cell's rows are 5 to 7 km away
    assert south < 0.0
    assert valid == 1.0
    # the scarp stands 3.2 to 4.5 degrees high across the cell: shut up to the 3 degree bin, open from 5.55
    assert (share[[0, 35], :6] == 0.0).all() and (share[[0, 35], 7:] == 1.0).all()
    assert 0.0 < share[0, 6] < 1.0
    assert (share[9:27] == 1.0).all()


def test_cell_in_open_sea_has_no_answer(monkeypatch):
    monkeypatch.setattr(earth, "elevation_window", fake_window(lambda x, y: 0 * x, lambda x, y: x > -1e9))
    share, north, south, valid = horizon.cell_open_share(70.0, 20.0, half_km=1.0, reach_km=8.0)
    assert share.shape == (36, 9) and np.isnan(share).all()
    assert math.isnan(north) and math.isnan(south)
    assert valid == 0.0


def test_lake_keeps_its_level_in_the_horizon(monkeypatch):
    # a plateau at 300 m with a lake to the north: the lake surface must not turn into a pit at sea level
    window = fake_window(lambda x, y: 300.0 + 0 * x, lambda x, y: y > 1500.0)
    monkeypatch.setattr(earth, "elevation_window", window)
    share, north, south, valid = horizon.cell_open_share(70.0, 20.0, half_km=1.0, reach_km=8.0)
    assert valid == 1.0
    assert north == pytest.approx(south, abs=0.005)


def test_cell_counts_its_land_pixels_only(monkeypatch):
    # a 385 m scarp to the north; the half of the cell nearer to it is a lake at the level of the plain.
    # The cell is 22 pixels across, centred in the window: its 11 land rows lie 34 to 44 pixels from the
    # scarp, its 11 lake rows 23 to 33 pixels.
    window = fake_window(lambda x, y: np.where(y > 3000.0, 385.0, 0.0), lambda x, y: (y > 0.0) & (y < 2000.0))
    monkeypatch.setattr(earth, "elevation_window", window)
    share, north, south, valid = horizon.cell_open_share(70.0, 20.0, half_km=1.0, reach_km=8.0)
    assert valid == 0.5
    assert north == pytest.approx(expected_deg(385.0, 39 * PIXEL), abs=0.05)  # 6.2; with the lake rows 7.2
    assert expected_deg(385.0, 33.5 * PIXEL) - expected_deg(385.0, 39 * PIXEL) > 0.9
    assert south < 0.0
    # from 40 pixels on the scarp stands under 6.11 degrees (5 of the 11 land rows, 5 of all 22),
    # and only from the last row under 5.55
    assert share[[0, 35], 8] == pytest.approx(5 / 11)
    assert share[[0, 35], 7] == pytest.approx(1 / 11)
    assert (share[[0, 35], :7] == 0.0).all()


def test_cell_reach_longer_than_the_usual_25_km(monkeypatch):
    window = fake_window(lambda x, y: np.where(y > 27000.0, 800.0, 0.0), lambda x, y: x < -1e9)
    monkeypatch.setattr(earth, "elevation_window", window)
    share, north, south, valid = horizon.cell_open_share(70.0, 20.0, half_km=0.5, reach_km=30.0)
    assert north == pytest.approx(expected_deg(800.0, 27000.0), abs=0.05)  # 1.6 degrees, seen only past 25 km
    assert south < 0.0
    assert (share[[0, 35], :3] == 0.0).all() and (share[[0, 35], 4:] == 1.0).all()


def test_cell_sectors_follow_the_compass(monkeypatch):
    # one hill on the bearings 11 to 19 degrees east of north, 5 to 7 km out, seen from a cell two
    # pixels across: only sector 1 (azimuth 10 to 20, ray at 15) is shut
    def hill(x, y):
        bearing, distance = np.degrees(np.arctan2(x, y)), np.hypot(x, y)
        return np.where((bearing > 11.0) & (bearing < 19.0) & (distance > 5000.0) & (distance < 7000.0), 600.0, 0.0)
    monkeypatch.setattr(earth, "elevation_window", fake_window(hill, lambda x, y: x < -1e9))
    share, north, south, valid = horizon.cell_open_share(70.0, 20.0, half_km=0.1, reach_km=8.0)
    assert valid == 1.0
    assert (share[1] == 0.0).all()  # the hill stands 6.7 degrees high, above the last lower edge
    assert (np.delete(share, 1, axis=0) == 1.0).all()
    assert north < 0.0 and south < 0.0


# --- one cell through the real elevation window, with a made-up tile in place of the downloads ---

def test_cell_from_tiles_with_open_sea_to_the_east(tmp_path, monkeypatch):
    import rasterio
    from rasterio.transform import from_origin

    def local(url, dest_dir=None):
        path = tmp_path / url.rsplit("/", 1)[-1]
        return path if path.exists() else None
    monkeypatch.setattr(earth, "fetch_optional", local)
    # the tile from 20E to 21E: a plain at 20 m with a 500 m plateau north of 10.56N. No tile east of 21E.
    lats = 11.0 - np.arange(1200) / 1200.0
    data = np.broadcast_to(np.where(lats > 10.56, 500.0, 20.0)[:, None], (1200, 1200)).astype("float32")
    path = tmp_path / earth.tile_url(10.5, 20.5, "DEM").rsplit("/", 1)[-1]
    with rasterio.open(path, "w", driver="GTiff", height=1200, width=1200, count=1, dtype="float32", crs="EPSG:4326",
                       transform=from_origin(20.0 - 0.5 / 1200, 11.0 + 0.5 / 1200, 1 / 1200, 1 / 1200)) as ds:
        ds.write(data, 1)
    share, north, south, valid = horizon.cell_open_share(10.5, 21.0, half_km=1.0, reach_km=8.0)
    assert valid == pytest.approx(0.47, abs=0.04)  # the cell's western half; where there is no tile is not land
    assert north == pytest.approx(expected_deg(480.0, 0.06 * 110600.0), abs=0.3)  # the plateau, 6.6 km north
    assert south < 0.0
    assert (share[35, :6] == 0.0).all() and (share[35, 7:] == 1.0).all()  # north-north-west: the plateau
    assert 0.0 < share[0, 0] < 1.0  # north-north-east: the pixels near the shore look past it over the sea
    assert (share[5:31] == 1.0).all()  # east over the sea (0 m where there is no tile), south and west over the plain

# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from rasterio.warp import transform as warp_transform

from twinfinder import earth


def test_tile_name_uses_south_west_corner():
    assert earth.glo90_tile_url(66.5, -52.3) == (
        "https://copernicus-dem-90m.s3.amazonaws.com/"
        "Copernicus_DSM_COG_30_N66_00_W053_00_DEM/Copernicus_DSM_COG_30_N66_00_W053_00_DEM.tif")


def test_tile_name_southern_and_eastern():
    assert "S78_00_E162_00" in earth.glo90_tile_url(-77.5, 162.4)


def test_water_mask_tile_sits_in_the_auxfiles_folder():
    assert earth.tile_url(55.9, -63.3, "WBM") == (
        "https://copernicus-dem-90m.s3.amazonaws.com/Copernicus_DSM_COG_30_N55_00_W064_00_DEM/"
        "AUXFILES/Copernicus_DSM_COG_30_N55_00_W064_00_WBM.tif")


def test_tiles_for_window_crossing_a_degree_line():
    urls = earth.tiles_for_window(66.99, -52.5, half_km=5.0)
    assert len(urls) == 2


def test_wide_window_lists_the_tiles_between_its_corners():
    # at 80.5N a 30 km half-width spans 3.3 degrees of longitude: 8.9E to 12.1E
    urls = earth.tiles_for_window(80.5, 10.5, half_km=30.0)
    assert [u.rsplit("_", 3)[1] for u in urls] == ["E008", "E009", "E010", "E011", "E012"]


def test_tile_just_past_the_window_edge_is_listed():
    # a tile's pixels start half a pixel before its whole degree and resampling reads one pixel
    # further, so a window that ends 100 m short of 21E still needs the tile east of it
    km_to_21_east = 111.32 * np.cos(np.radians(10.5)) * 0.3
    assert len(earth.tiles_for_window(10.5, 20.7, half_km=km_to_21_east - 0.1)) == 2
    assert len(earth.tiles_for_window(10.5, 20.7, half_km=km_to_21_east - 1.0)) == 1


def test_window_bounds_cover_the_poleward_corners():
    west, south, east, north = earth.window_bounds(80.5, 10.5, 30.0)
    assert north - 80.5 == pytest.approx(30.0 / 111.6, abs=0.005)
    assert 80.5 - south == pytest.approx(30.0 / 111.6, abs=0.005)
    # the northern corners sit at 80.77N, where a degree of longitude is shorter than at the centre
    assert east - 10.5 == pytest.approx(30.0 / (111.6 * np.cos(np.radians(80.77))), rel=0.01)
    assert 10.5 - west == pytest.approx(east - 10.5, rel=1e-6)


def test_window_across_the_antimeridian_is_refused():
    with pytest.raises(ValueError, match="antimeridian"):
        earth.tiles_for_window(66.15, 179.95, half_km=5.0)
    with pytest.raises(ValueError, match="antimeridian"):
        earth.elevation_window(66.15, -179.95, 5.0)
    assert len(earth.tiles_for_window(66.15, -179.55, half_km=5.0)) == 1  # close to it is fine


def test_window_holding_a_pole_is_refused():
    with pytest.raises(ValueError, match="pole"):
        earth.window_bounds(89.9, 0.0, 30.0)
    with pytest.raises(ValueError, match="pole"):
        earth.tiles_for_window(-89.9, 40.0, half_km=30.0)
    with pytest.raises(ValueError, match="pole"):
        earth.elevation_window(-89.99, 40.0, 5.0)
    # the last row of the southern search grid is far enough from the pole
    west, south, east, north = earth.window_bounds(-87.45, 40.0, 30.0)
    assert -87.75 < south < -87.70 and -87.20 < north < -87.15
    assert east - 40.0 == pytest.approx(30.0 / (111.6 * np.cos(np.radians(87.72))), rel=0.02)  # the southern corners


def test_window_in_the_south_west_lists_tiles_by_their_south_west_corners():
    urls = earth.tiles_for_window(-77.98, -162.98, half_km=5.0)
    names = sorted(u.rsplit("/", 1)[-1][22:36] for u in urls)
    assert names == ["S78_00_W163_00", "S78_00_W164_00", "S79_00_W163_00", "S79_00_W164_00"]


# --- warping, with small made-up tiles in place of downloads -------------------------------

def write_tile(folder, lat0, lon0, product, values, cols=1200):
    """A made-up tile laid out like the real ones: 1200 rows, pixel centres on the whole degree."""
    path = folder / earth.tile_url(lat0 + 0.5, lon0 + 0.5, product).rsplit("/", 1)[-1]
    rx, ry = 1.0 / cols, 1.0 / 1200
    lats = lat0 + 1.0 - np.arange(1200) * ry
    lons = lon0 + np.arange(cols) * rx
    dtype = "float32" if product == "DEM" else "uint8"
    data = np.broadcast_to(values(lats[:, None], lons[None, :]), (1200, cols)).astype(dtype)
    with rasterio.open(path, "w", driver="GTiff", height=1200, width=cols, count=1, dtype=dtype,
                       crs="EPSG:4326", transform=from_origin(lon0 - rx / 2, lat0 + 1.0 + ry / 2, rx, ry),
                       compress="deflate") as ds:
        ds.write(data, 1)


@pytest.fixture
def tiles(tmp_path, monkeypatch):
    """Folder that stands in for the tile server: a tile that is not there counts as ocean."""
    def local(url, dest_dir=None):
        path = tmp_path / url.rsplit("/", 1)[-1]
        return path if path.exists() else None
    monkeypatch.setattr(earth, "fetch_optional", local)
    return tmp_path


def lonlat_of_pixels(lat, lon, half_km, pixel_m=90.0):
    n = int(round(2 * half_km * 1000.0 / pixel_m))
    centres = -half_km * 1000.0 + (np.arange(n) + 0.5) * pixel_m
    x, y = np.meshgrid(centres, -centres)
    crs = f"+proj=aeqd +lat_0={lat} +lon_0={lon} +datum=WGS84 +units=m"
    lons, lats = warp_transform(crs, "EPSG:4326", x.ravel(), y.ravel())
    return np.array(lons).reshape(n, n), np.array(lats).reshape(n, n)


def ramp(lats, lons):
    """A steep plane: 20 m per 3 arc-second pixel eastward, 10 m northward."""
    return 24000.0 * (lons - 20.0) + 12000.0 * (lats - 10.0)


def test_plane_is_smooth_across_a_tile_seam(tiles):
    for lon0 in (20, 21):
        write_tile(tiles, 10, lon0, "DEM", ramp)
    z = earth.elevation_window(10.5, 21.0, 5.0, mask_water=False)
    lons, lats = lonlat_of_pixels(10.5, 21.0, 5.0)
    assert z.shape == (111, 111) and z.dtype == np.float32
    assert np.isfinite(z).all()
    assert np.abs(z - ramp(lats, lons)).max() < 0.1  # warping tile by tile was 1 m off along the seam


def test_plane_is_smooth_across_four_tiles(tiles):
    for lat0 in (10, 11):
        for lon0 in (20, 21):
            write_tile(tiles, lat0, lon0, "DEM", ramp)
    z = earth.elevation_window(11.0, 21.0, 5.0, mask_water=False)
    lons, lats = lonlat_of_pixels(11.0, 21.0, 5.0)
    assert np.abs(z - ramp(lats, lons)).max() < 0.1


def test_tiles_of_two_longitude_spacings_merge(tiles):
    # real tiles lose columns towards the poles (800 below 60N, 600 above); the made-up ones sit
    # near the equator, where the warp itself is exact enough to show a misplaced tile
    for lon0 in (20, 21):
        write_tile(tiles, 10, lon0, "DEM", ramp, cols=800)
        write_tile(tiles, 11, lon0, "DEM", ramp, cols=600)
    z = earth.elevation_window(11.0, 21.0, 5.0, mask_water=False)
    lons, lats = lonlat_of_pixels(11.0, 21.0, 5.0)
    assert np.abs(z - ramp(lats, lons)).max() < 0.1


def test_plane_in_the_south_west_is_smooth_across_a_seam(tiles):
    # south of the equator and west of Greenwich, with the 400-column tiles of 70 to 80 degrees
    def plane(lats, lons):
        return 2400.0 * (lons + 163.0) + 1200.0 * (lats + 77.5)  # 6 m per tile pixel eastward, 1 m northward
    for lon0 in (-164, -163):
        write_tile(tiles, -78, lon0, "DEM", plane, cols=400)
    z = earth.elevation_window(-77.5, -163.0, 5.0, mask_water=False)
    lons, lats = lonlat_of_pixels(-77.5, -163.0, 5.0)
    assert np.isfinite(z).all()
    assert z[0, 0] < z[0, -1] and z[-1, 0] < z[0, 0]  # higher to the east and to the north
    assert np.abs(z - plane(lats, lons)).max() < 1.0  # a tile one pixel out of place would be 6 m off


def test_missing_tile_is_nan_or_zero_with_sea_as_zero(tiles):
    write_tile(tiles, 10, 20, "DEM", lambda lats, lons: 50.0 + 0 * lons)
    z = earth.elevation_window(10.5, 21.0, 5.0, mask_water=False)
    assert np.isnan(z[:, 60:]).all() and (z[:, :50] == 50.0).all()
    filled = earth.elevation_window(10.5, 21.0, 5.0, mask_water=False, sea_as_zero=True)
    assert filled.dtype == np.float32
    assert (filled[:, 60:] == 0.0).all() and (filled[:, :50] == 50.0).all()


def test_no_tiles_at_all(tiles):
    assert np.isnan(earth.elevation_window(10.5, 20.5, 5.0)).all()
    assert (earth.elevation_window(10.5, 20.5, 5.0, sea_as_zero=True) == 0.0).all()


def test_water_is_nan_or_zero_with_sea_as_zero(tiles):
    write_tile(tiles, 10, 20, "DEM", lambda lats, lons: 50.0 + 0 * lons)
    write_tile(tiles, 10, 20, "WBM", lambda lats, lons: lons > 20.5)
    z = earth.elevation_window(10.5, 20.5, 5.0)
    assert z.dtype == np.float32
    assert np.isnan(z[:, 57:]).all() and (z[:, :54] == 50.0).all()
    filled = earth.elevation_window(10.5, 20.5, 5.0, sea_as_zero=True)
    assert filled.dtype == np.float32
    assert (filled[:, 57:] == 0.0).all() and (filled[:, :54] == 50.0).all()
    # without the water mask the surface of the water keeps its height
    assert (earth.elevation_window(10.5, 20.5, 5.0, mask_water=False, sea_as_zero=True) == 50.0).all()


def test_water_edge_follows_the_nearest_mask_pixel(tiles):
    # the first water pixel of the mask is centred on 20.5E. With the window 40 m east of that, column 54
    # is centred 55 m west of it (nearer to the last land pixel, 91 m west) and column 55 is 35 m east.
    write_tile(tiles, 10, 20, "DEM", lambda lats, lons: 50.0 + 0 * lons)
    write_tile(tiles, 10, 20, "WBM", lambda lats, lons: lons > 20.4995)
    forty_m = 40.0 / (111320.0 * np.cos(np.radians(10.5)))
    z = earth.elevation_window(10.5, 20.5 + forty_m, 5.0)
    assert (z[:, :55] == 50.0).all() and np.isnan(z[:, 55:]).all()

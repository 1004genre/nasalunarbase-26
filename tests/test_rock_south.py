# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
import json
import math
import struct
import zipfile
from pathlib import Path

import numpy as np
import pytest
from rasterio.warp import transform

from twinfinder import grid, regions, rock_south

A, E2 = 6378137.0, 0.00669437999014  # WGS84


def to_xy(lat, lon):
    """Antarctic polar stereographic metres from the PROJ library, as an independent check."""
    xs, ys = transform("EPSG:4326", "EPSG:3031", [lon], [lat])
    return xs[0], ys[0]


def box(x0, y0, width, height, hole=False):
    """A closed rectangle ring: clockwise as shapefiles store outer rings, reversed for a hole."""
    ring = [(x0, y0), (x0, y0 + height), (x0 + width, y0 + height), (x0 + width, y0), (x0, y0)]
    return ring[::-1] if hole else ring


def write_layer(path, polygons):
    """Write a zipped polygon shapefile. polygons is a list of records, each a list of rings."""
    records = b""
    for number, rings in enumerate(polygons, 1):
        points = [p for ring in rings for p in ring]
        xs, ys = zip(*points)
        starts = [sum(len(r) for r in rings[:i]) for i in range(len(rings))]
        body = struct.pack("<i4d2i", 5, min(xs), min(ys), max(xs), max(ys), len(rings), len(points))
        body += struct.pack(f"<{len(rings)}i", *starts)
        body += b"".join(struct.pack("<2d", *p) for p in points)
        records += struct.pack(">2i", number, len(body) // 2) + body
    header = struct.pack(">7i", 9994, 0, 0, 0, 0, 0, (100 + len(records)) // 2)
    header += struct.pack("<2i", 1000, 5) + struct.pack("<8d", *[0.0] * 8)
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("layer.shp", header + records)
        z.writestr("layer.dbf", b"")
    return path


def true_km2(projected_m2, lat):
    return projected_m2 / rock_south.map_scale(lat) ** 2 / 1e6


def snap(v):
    """Nearest pixel edge of the Landsat layer: an odd multiple of 15 m."""
    return round((v - 15) / 30) * 30 + 15


# --- map projection ---------------------------------------------------------------------------

@pytest.mark.parametrize("lat, lon", [(-66.27, 100.75), (-62.2, -58.95), (-77.52, 161.6), (-71.0, 0.0),
                                      (-87.4, -149.5), (-60.0, 179.9), (-69.0, -179.9), (-83.3, 90.0)])
def test_to_lat_lon_inverts_the_proj_library(lat, lon):
    x, y = to_xy(lat, lon)
    got_lat, got_lon = rock_south.to_lat_lon(np.array([x]), np.array([y]))
    assert got_lat[0] == pytest.approx(lat, abs=1e-8)
    assert got_lon[0] == pytest.approx(lon, abs=1e-8)


def test_longitude_runs_clockwise_from_the_greenwich_meridian_at_the_top():
    lat, lon = rock_south.to_lat_lon(np.array([0.0, 1e6, 0.0, -1e6]), np.array([1e6, 0.0, -1e6, 0.0]))
    assert lon.tolist() == pytest.approx([0.0, 90.0, -180.0, -90.0])
    assert np.all(lat == lat[0])


def test_map_scale_is_one_on_the_standard_parallel_and_smaller_towards_the_pole():
    assert rock_south.map_scale(-71.0) == pytest.approx(1.0, abs=1e-12)
    assert rock_south.map_scale(-60.0) > 1.0 > rock_south.map_scale(-80.0) > rock_south.map_scale(-89.0)


@pytest.mark.parametrize("lat", [-60.0, -66.25, -77.5, -87.0])
def test_map_scale_matches_the_radius_of_the_mapped_parallel(lat):
    radius_on_map, _ = to_xy(lat, 90.0)
    phi = math.radians(lat)
    radius_on_earth = A * math.cos(phi) / math.sqrt(1 - E2 * math.sin(phi) ** 2)
    assert rock_south.map_scale(lat) == pytest.approx(radius_on_map / radius_on_earth, rel=1e-9)


# --- reading the shapefile --------------------------------------------------------------------

def test_polygons_reads_boxes_and_rings_back(tmp_path):
    outer, hole = box(1000.0, 2000.0, 600.0, 300.0), box(1100.0, 2100.0, 60.0, 60.0, hole=True)
    path = write_layer(tmp_path / "layer.zip", [[outer, hole], [box(-50.0, -80.0, 30.0, 30.0)]])
    records = list(rock_south.polygons(rock_south.read_shp(path)))
    assert len(records) == 2
    bbox, rings = records[0]
    assert bbox == (1000.0, 2000.0, 1600.0, 2300.0)
    assert [ring.tolist() for ring in rings] == [[list(p) for p in outer], [list(p) for p in hole]]
    assert records[1][0] == (-50.0, -80.0, -20.0, -50.0)


def shp_bytes(path):
    with zipfile.ZipFile(path) as z:
        return z.read("layer.shp")


def test_polygons_skips_a_record_without_a_shape(tmp_path):
    shp = shp_bytes(write_layer(tmp_path / "layer.zip", [[box(0.0, 0.0, 30.0, 30.0)]]))
    empty = struct.pack(">2i", 2, 2) + struct.pack("<i", 0)  # record 2: four bytes, shape type 0
    more = shp_bytes(write_layer(tmp_path / "more.zip", [[box(90.0, 0.0, 30.0, 30.0)]]))[100:]
    boxes = [bbox for bbox, _ in rock_south.polygons(shp + empty + more)]
    assert boxes == [(0.0, 0.0, 30.0, 30.0), (90.0, 0.0, 120.0, 30.0)]


def test_polygons_refuses_a_layer_of_lines(tmp_path):
    shp = bytearray(shp_bytes(write_layer(tmp_path / "layer.zip", [[box(0.0, 0.0, 30.0, 30.0)]])))
    shp[108:112] = struct.pack("<i", 3)  # the first record becomes a polyline
    with pytest.raises(ValueError, match="not a polygon"):
        list(rock_south.polygons(bytes(shp)))


# --- grid cells -------------------------------------------------------------------------------

def test_cell_index_agrees_with_the_grid_module():
    rng = np.random.default_rng(0)
    lat = rng.uniform(-89.9, -59.0, 5000)
    lon = rng.uniform(-180.0, 180.0, 5000)
    row, col = rock_south.cell_index(lat, lon)
    names = [rock_south.cell_name(r, c) for r, c in zip(row.tolist(), col.tolist())]
    assert names == [grid.cell_id(a, b) for a, b in zip(lat.tolist(), lon.tolist())]


def test_cell_index_at_cell_corners_and_the_date_line():
    row, col = rock_south.cell_index(np.array([-66.3, -66.25, -64.5, -84.0, -70.0]),
                                     np.array([100.5, -0.05, -57.0, 165.6, -180.0]))
    names = [rock_south.cell_name(r, c) for r, c in zip(row.tolist(), col.tolist())]
    assert names == ["-66.3_100.5", "-66.3_-0.3", "-64.5_-57.0", "-84.0_165.6", "-70.0_-180.0"]


def test_cell_area_adds_up_to_the_whole_ellipsoid():
    assert rock_south.zone_area_km2(-90.0, 90.0, 360.0) == pytest.approx(510065621.7, rel=1e-8)


@pytest.mark.parametrize("cid", ["-66.3_100.5", "-62.2_-59.0", "-77.6_161.5", "-85.1_165.6",
                                 "-64.5_-57.0", "-73.0_100.0", "-78.0_100.2", "-84.0_165.6"])  # last four: pole-side rows
def test_cell_area_is_height_times_width_on_the_ellipsoid(cid):
    lat, _ = grid.cell_centre(cid)
    phi = math.radians(lat)
    w = 1 - E2 * math.sin(phi) ** 2
    km_per_deg_lat = math.radians(1) * A * (1 - E2) / w ** 1.5 / 1000
    km_per_deg_lon = math.radians(1) * A * math.cos(phi) / math.sqrt(w) / 1000
    expected = 0.1 * km_per_deg_lat * 0.1 * grid.lon_factor(lat) * km_per_deg_lon
    assert rock_south.cell_area_km2(cid) == pytest.approx(expected, rel=1e-4)


# --- rock area per cell -----------------------------------------------------------------------

def test_a_polygon_inside_one_cell_gives_that_cell_its_area(tmp_path):
    x, y = to_xy(-66.25, 100.65)  # centre of cell -66.3_100.5
    path = write_layer(tmp_path / "layer.zip", [[box(snap(x - 1500), snap(y - 1500), 3000, 3000)]])
    rock = rock_south.rock_km2_per_cell(path)
    assert list(rock) == ["-66.3_100.5"]
    assert rock["-66.3_100.5"] == pytest.approx(true_km2(9e6, -66.25), rel=1e-4)
    assert rock["-66.3_100.5"] == pytest.approx(8.72, abs=0.01)  # the map stretches areas by 3% here


def test_single_landsat_pixels_add_up_exactly(tmp_path):
    x, y = to_xy(-77.55, 161.75)  # centre of cell -77.6_161.5
    path = write_layer(tmp_path / "layer.zip", [[box(snap(x) + 90 * i, snap(y), 30, 30)] for i in range(10)])
    rock = rock_south.rock_km2_per_cell(path)
    assert rock == {"-77.6_161.5": pytest.approx(true_km2(9000.0, -77.55), rel=1e-4)}


def test_a_polygon_off_the_pixel_lattice_keeps_its_area_within_a_pixel_row(tmp_path):
    x, y = to_xy(-66.25, 100.65)
    path = write_layer(tmp_path / "layer.zip", [[box(x - 1507.3, y - 1493.1, 3000, 3000)]])
    rock = rock_south.rock_km2_per_cell(path)
    assert rock["-66.3_100.5"] == pytest.approx(true_km2(9e6, -66.25), rel=0.02)


def test_overlapping_polygons_count_once(tmp_path):
    x, y = to_xy(-66.25, 100.65)
    x, y = snap(x - 2250), snap(y - 1500)
    path = write_layer(tmp_path / "layer.zip", [[box(x, y, 3000, 3000)], [box(x + 1500, y, 3000, 3000)]])
    rock = rock_south.rock_km2_per_cell(path)
    assert rock == {"-66.3_100.5": pytest.approx(true_km2(13.5e6, -66.25), rel=1e-4)}


def test_a_polygon_across_a_meridian_is_shared_by_area(tmp_path):
    _, y = to_xy(-66.25, 0.0)  # the meridian between cells -66.3_-0.3 and -66.3_0.0 is the line x = 0
    path = write_layer(tmp_path / "layer.zip", [[box(-1995, snap(y - 1500), 6000, 3000)]])
    rock = rock_south.rock_km2_per_cell(path)
    total = true_km2(18e6, -66.25)
    assert set(rock) == {"-66.3_-0.3", "-66.3_0.0"}
    assert sum(rock.values()) == pytest.approx(total, rel=1e-4)
    assert rock["-66.3_-0.3"] == pytest.approx(total / 3, rel=0.02)
    assert rock["-66.3_0.0"] == pytest.approx(total * 2 / 3, rel=0.02)


def test_a_polygon_across_a_parallel_is_shared_by_area(tmp_path):
    # On the parallel between rows -66.4 and -66.3, in the middle of a column; near 90E north is +x.
    x, y = to_xy(-66.3, 90.15)
    path = write_layer(tmp_path / "layer.zip", [[box(snap(x - 1050), snap(y - 600), 4200, 1200)]])
    rock = rock_south.rock_km2_per_cell(path)
    total = true_km2(4200 * 1200, -66.3)
    assert set(rock) == {"-66.4_90.0", "-66.3_90.0"}
    assert sum(rock.values()) == pytest.approx(total, rel=1e-4)
    assert rock["-66.4_90.0"] == pytest.approx(total / 4, rel=0.02)
    assert rock["-66.3_90.0"] == pytest.approx(total * 3 / 4, rel=0.02)


def test_a_hole_is_left_out_of_the_cell_it_lies_in(tmp_path):
    _, y = to_xy(-66.25, 0.0)
    y = snap(y - 3000)
    outer = box(-3015, y, 6000, 6000)
    hole = box(495, y + 1980, 2010, 2010, hole=True)  # east of the meridian
    path = write_layer(tmp_path / "layer.zip", [[outer, hole]])
    rock = rock_south.rock_km2_per_cell(path)
    assert sum(rock.values()) == pytest.approx(true_km2(6000 * 6000 - 2010 * 2010, -66.25), rel=1e-4)
    assert rock["-66.3_-0.3"] == pytest.approx(true_km2(18e6, -66.25), rel=0.01)
    assert rock["-66.3_0.0"] == pytest.approx(true_km2(18e6 - 2010 * 2010, -66.25), rel=0.01)


def test_a_record_with_two_separate_parts_feeds_both_cells(tmp_path):
    xa, ya = to_xy(-66.25, 100.65)
    xb, yb = to_xy(-66.25, 101.25)  # two cells further east
    path = write_layer(tmp_path / "layer.zip", [[box(snap(xa), snap(ya), 1200, 1200),
                                                 box(snap(xb), snap(yb), 1200, 1200)]])
    rock = rock_south.rock_km2_per_cell(path)
    assert set(rock) == {"-66.3_100.5", "-66.3_101.1"}
    assert rock["-66.3_100.5"] == pytest.approx(true_km2(1.44e6, -66.25), rel=1e-4)
    assert rock["-66.3_101.1"] == pytest.approx(true_km2(1.44e6, -66.25), rel=1e-4)


def test_a_polygon_across_two_working_blocks_is_counted_once(tmp_path):
    # Blocks are 60 km wide and start half a pixel off the origin, so x = 15 m is a block edge.
    _, y = to_xy(-66.25, 0.0)
    path = write_layer(tmp_path / "layer.zip", [[box(-1485, snap(y - 1500), 3000, 3000)]])
    rock = rock_south.rock_km2_per_cell(path)
    assert sum(rock.values()) == pytest.approx(true_km2(9e6, -66.25), rel=1e-4)


def test_an_empty_layer_has_no_rock(tmp_path):
    assert rock_south.rock_km2_per_cell(write_layer(tmp_path / "layer.zip", [])) == {}


# --- land share from the GLO-90 water mask ----------------------------------------------------

def tiles(found):
    """A tile reader over a dict {(lat0, lon0): array}; any other tile is open sea."""
    return lambda lat0, lon0: found.get((lat0, lon0))


def test_cell_tiles_lists_every_one_degree_tile_a_cell_touches():
    assert rock_south.cell_tiles("-66.3_100.5") == [(-67, 100)]
    assert rock_south.cell_tiles("-66.3_100.8") == [(-67, 100), (-67, 101)]
    assert rock_south.cell_tiles("-85.1_-1.2") == [(-86, -2), (-86, -1)]
    assert rock_south.cell_tiles("-62.0_-59.0") == [(-62, -59)]
    assert rock_south.cell_tiles("-70.0_-180.0") == [(-70, -180)]


def test_land_share_is_one_on_an_all_land_tile():
    reader = tiles({(-67, 100): np.zeros((1200, 600), dtype="uint8")})
    assert rock_south.land_share("-66.3_100.5", reader) == pytest.approx(1.0)


def test_land_share_counts_sea_and_lakes_as_water():
    mask = np.zeros((1200, 600), dtype="uint8")
    mask[:, 300:330] = 1  # sea in the tenth-degree strip 100.5 to 100.55
    mask[:, 360:390] = 2  # a lake in 100.6 to 100.65
    reader = tiles({(-67, 100): mask})
    assert rock_south.land_share("-66.3_100.5", reader) == pytest.approx(4 / 6)


def test_land_share_reads_the_rows_of_its_own_latitude_strip():
    mask = np.ones((1200, 600), dtype="uint8")
    mask[240:360, :] = 0  # land only between 66.3S and 66.2S (row 0 is the tile's north edge at 66S)
    reader = tiles({(-67, 100): mask})
    assert rock_south.land_share("-66.3_100.5", reader) == pytest.approx(1.0)
    assert rock_south.land_share("-66.2_100.5", reader) == pytest.approx(0.0)
    assert rock_south.land_share("-66.4_100.5", reader) == pytest.approx(0.0)


def test_land_share_joins_two_tiles_and_treats_a_missing_one_as_sea():
    reader = tiles({(-67, 100): np.zeros((1200, 600), dtype="uint8")})
    # cell -66.3_100.8 spans 100.8 to 101.1: two tenths in tile 100, one in the missing tile 101
    assert rock_south.land_share("-66.3_100.8", reader) == pytest.approx(2 / 3)


def test_land_share_is_none_when_no_tile_exists():
    assert rock_south.land_share("-66.3_100.5", tiles({})) is None


def test_land_share_west_of_greenwich_and_on_narrow_polar_tiles():
    mask = np.zeros((1200, 240), dtype="uint8")
    mask[:, 0:120] = 1  # western half of tile 86S to 85S, 1W to 0
    reader = tiles({(-86, -1): mask, (-86, -2): np.zeros((1200, 240), dtype="uint8")})
    # cell -85.1_-1.2 spans 1.2W to 0: two tenths of tile -2, five water and five land tenths of tile -1
    assert rock_south.land_share("-85.1_-1.2", reader) == pytest.approx(7 / 12)


def test_water_tile_asks_for_the_tile_by_its_south_west_corner(tmp_path, monkeypatch):
    import rasterio
    from rasterio.transform import from_origin
    mask = np.zeros((12, 6), dtype="uint8")
    mask[0, 0] = 1
    with rasterio.open(tmp_path / "tile.tif", "w", driver="GTiff", height=12, width=6, count=1, dtype="uint8",
                       crs="EPSG:4326", transform=from_origin(100, -66, 1 / 6, 1 / 12)) as ds:
        ds.write(mask, 1)
    asked = []

    def fake_fetch(url, dest_dir):
        asked.append((url.rsplit("/", 1)[-1], dest_dir))
        return tmp_path / "tile.tif" if "E100" in url else None

    monkeypatch.setattr(rock_south, "fetch_optional", fake_fetch)
    assert rock_south.water_tile(-67, 100).tolist() == mask.tolist()
    assert rock_south.water_tile(-67, 101) is None
    assert rock_south.water_tile(-63, -59) is None
    assert asked == [("Copernicus_DSM_COG_30_S67_00_E100_00_WBM.tif", rock_south.earth.GLO90_DIR),
                     ("Copernicus_DSM_COG_30_S67_00_E101_00_WBM.tif", rock_south.earth.GLO90_DIR),
                     ("Copernicus_DSM_COG_30_S63_00_W059_00_WBM.tif", rock_south.earth.GLO90_DIR)]


# --- records ----------------------------------------------------------------------------------

def test_cell_record_gives_shares_of_land():
    area = rock_south.cell_area_km2("-66.3_100.5")
    record = rock_south.cell_record("-66.3_100.5", 0.10 * area, 0.15 * area, 0.5)
    assert record["id"] == "-66.3_100.5"
    assert (record["lat"], record["lon"]) == (-66.25, 100.65)
    assert record["land_share"] == pytest.approx(0.5)
    assert record["land_source"] == "glo90"
    assert record["rock_landsat"] == pytest.approx(0.2)
    assert record["rock_medium"] == pytest.approx(0.3)
    assert record["bare"] == pytest.approx(0.3)
    assert record["ice"] == pytest.approx(0.7)
    assert record["lichen"] == 0.0
    assert record["layers_disagree"] is False
    assert record["rock_landsat_km2"] == pytest.approx(0.10 * area, abs=1e-3)
    assert record["rock_medium_km2"] == pytest.approx(0.15 * area, abs=1e-3)
    assert record["cell_km2"] == pytest.approx(area, abs=1e-3)


def test_cell_record_uses_the_whole_cell_without_a_land_share():
    area = rock_south.cell_area_km2("-66.3_100.5")
    record = rock_south.cell_record("-66.3_100.5", 0.02 * area, 0.01 * area, None)
    assert record["land_share"] == 1.0
    assert record["land_source"] == "whole cell"
    assert record["bare"] == pytest.approx(0.02)
    assert record["ice"] == pytest.approx(0.98)


@pytest.mark.parametrize("landsat, medium, expected", [
    (0.10, 0.20, False), (0.10, 0.21, True), (0.21, 0.10, True), (0.0, 0.10, True), (0.10, 0.0, True),
    (0.0, 0.0, False),
])
def test_layers_disagree_beyond_a_factor_of_two(landsat, medium, expected):
    area = rock_south.cell_area_km2("-66.3_100.5")
    record = rock_south.cell_record("-66.3_100.5", landsat * area, medium * area, 1.0)
    assert record["layers_disagree"] is expected


def test_rock_never_exceeds_the_land_it_stands_on():
    # The water mask can miss a rock islet; rock is land, so land is at least the rock area.
    area = rock_south.cell_area_km2("-66.3_100.5")
    record = rock_south.cell_record("-66.3_100.5", 0.10 * area, 0.20 * area, 0.05)
    assert record["land_share"] == pytest.approx(0.20)
    assert record["land_source"] == "rock area"  # not the mask: the record must say so
    assert record["bare"] == pytest.approx(1.0)
    assert record["ice"] == pytest.approx(0.0)
    assert record["rock_landsat"] == pytest.approx(0.5)


def test_land_source_names_the_mask_only_when_the_mask_gave_the_land_share():
    area = rock_south.cell_area_km2("-66.3_100.5")
    assert rock_south.cell_record("-66.3_100.5", 0.10 * area, 0.20 * area, 0.20)["land_source"] == "glo90"
    assert rock_south.cell_record("-66.3_100.5", 0.10 * area, 0.20 * area, 0.19)["land_source"] == "rock area"
    assert rock_south.cell_record("-66.3_100.5", 0.10 * area, 0.20 * area, None)["land_source"] == "whole cell"


# --- the files the build writes ---------------------------------------------------------------

EVIDENCE = {"measured mostly bare", "literature: no continuous winter cover", "one qualitative report",
            "station shows snow", "no evidence"}
SITE_KEYS = {"name", "lat", "lon", "nearest_station", "station_year_round", "winter_snow_evidence",
             "existing_analog_use", "rock_type", "source_urls"}


def test_the_named_sites_file_has_fifteen_sites_with_the_agreed_fields():
    path = Path("data/reference/antarctic_sites.json")
    if not path.exists():
        pytest.skip("data/reference/antarctic_sites.json has not been written")
    sites = json.loads(path.read_text())
    assert len(sites) == 15
    assert len({site["name"] for site in sites}) == 15
    for site in sites:
        assert SITE_KEYS <= set(site), site["name"]
        assert site["winter_snow_evidence"] in EVIDENCE, site["name"]
        assert isinstance(site["station_year_round"], bool), site["name"]
        assert grid.SOUTH_MIN_LAT <= site["lat"] < grid.SOUTH_MAX_LAT and -180.0 <= site["lon"] < 180.0
        assert site["source_urls"] and all(url.startswith("https://") for url in site["source_urls"])
        assert regions.region(site["lat"], site["lon"]) != "Antarctica", site["name"]


def test_the_southern_cells_file_matches_the_grid_and_the_record_rules():
    path = Path("data/derived/landcover_cells_south.json")
    if not path.exists():
        pytest.skip("data/derived/landcover_cells_south.json has not been built")
    records = json.loads(path.read_text())
    assert len(records) == len({r["id"] for r in records}) > 1000
    for r in records:
        lat, lon = grid.cell_centre(r["id"])
        assert grid.cell_id(lat, lon) == r["id"]
        assert (r["lat"], r["lon"]) == (round(lat, 2), round(lon, 2))
        assert grid.SOUTH_MIN_LAT <= float(r["id"].split("_")[0]) < grid.SOUTH_MAX_LAT
        assert 0.05 <= r["bare"] <= 1.0 and 0.0 < r["land_share"] <= 1.0
        assert r["bare"] == max(r["rock_landsat"], r["rock_medium"])
        assert r["ice"] == pytest.approx(1.0 - r["bare"]) and r["lichen"] == 0.0
        assert r["land_source"] in ("glo90", "whole cell", "rock area")
        assert r["cell_km2"] == pytest.approx(rock_south.cell_area_km2(r["id"]))
        rock_share = max(r["rock_landsat_km2"], r["rock_medium_km2"]) / r["cell_km2"]
        assert r["bare"] == pytest.approx(min(1.0, rock_share / r["land_share"]))
        if r["land_source"] == "whole cell":
            assert r["land_share"] == 1.0
        if r["land_source"] == "rock area":
            assert r["land_share"] == pytest.approx(rock_share) and r["bare"] == pytest.approx(1.0)

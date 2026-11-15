# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
import pytest
from twinfinder import grid


def test_lon_factor_keeps_cells_roughly_square():
    assert [grid.lon_factor(lat) for lat in (60, 66, 75, 80)] == [2, 3, 5, 6]


def test_every_factor_divides_a_three_degree_tile():
    assert all(30 % grid.lon_factor(lat / 10) == 0 for lat in range(590, 840))


def test_cell_id_is_the_south_west_corner():
    assert grid.cell_id(66.47, -52.05) == "66.4_-52.2"
    assert grid.cell_id(60.01, 0.05) == "60.0_0.0"
    assert grid.cell_id(60.01, -0.05) == "60.0_-0.2"


def test_cell_centre_round_trips():
    assert grid.cell_centre("66.4_-52.2") == pytest.approx((66.45, -52.05))
    lat, lon = grid.cell_centre("75.3_20.0")
    assert grid.cell_id(lat, lon) == "75.3_20.0"


def test_tile_origin_is_a_multiple_of_three():
    assert grid.tile_origin(66.47, -52.05) == (66, -54)
    assert grid.tile_origin(59.5, 10.2) == (57, 9)


def test_southern_search_band():
    assert (grid.SOUTH_MIN_LAT, grid.SOUTH_MAX_LAT) == (-87.5, -59.0)


def test_lon_factor_mirrors_in_the_south_and_adds_a_band_above_84():
    assert [grid.lon_factor(lat) for lat in (-60, -66, -75, -80)] == [2, 3, 5, 6]
    assert [grid.lon_factor(lat) for lat in (-83.9, -84.0, -86, -87.5)] == [6, 12, 12, 12]


def test_every_factor_fits_a_whole_number_of_cells_around_the_globe():
    assert all(3600 % grid.lon_factor(-lat / 10) == 0 for lat in range(590, 876))


def test_southern_cell_id_is_the_south_west_corner():
    assert grid.cell_id(-66.27, 100.75) == "-66.3_100.5"      # Bunger Hills
    assert grid.cell_id(-62.2, -58.95) == "-62.2_-59.0"       # Fildes Peninsula
    assert grid.cell_id(-77.52, 161.6) == "-77.6_161.5"       # McMurdo Dry Valleys
    assert grid.cell_id(-85.01, 166.5) == "-85.1_165.6"       # 1.2-degree columns south of 84S
    assert grid.cell_id(-66.25, -0.05) == "-66.3_-0.3"
    assert grid.cell_id(-66.25, 0.05) == "-66.3_0.0"


def test_southern_cell_centre_round_trips():
    assert grid.cell_centre("-66.3_100.5") == pytest.approx((-66.25, 100.65))
    for cid in ("-66.3_100.5", "-62.2_-59.0", "-64.5_-57.0", "-77.6_161.5", "-80.0_-179.4", "-85.1_165.6",
                "-87.5_-180.0", "-59.1_-26.6"):
        assert grid.cell_id(*grid.cell_centre(cid)) == cid


def test_lon_factor_is_one_value_for_a_whole_southern_row():
    # A cell takes its width from its south edge. In the south that is the pole side of the row,
    # so the row from 64.5S to 64.4S is 0.3 degrees wide and every latitude inside it must say so.
    assert [grid.lon_factor(lat) for lat in (-64.45, -72.95, -77.95, -83.95)] == [3, 5, 6, 12]
    assert [grid.lon_factor(lat) for lat in (-64.35, -72.85, -77.85, -83.85)] == [2, 3, 5, 6]
    for tenth in range(-875, -590):
        south = tenth / 10
        assert grid.lon_factor(south + 0.05) == grid.lon_factor(south + 0.099) == grid.lon_factor(south)


def test_northern_rows_at_a_band_limit_are_unchanged():
    assert [grid.lon_factor(lat) for lat in (64.45, 64.5, 72.95, 73.0, 77.95, 78.0, 83.95)] == [2, 3, 3, 5, 5, 6, 6]
    assert grid.cell_id(64.45, 100.45) == "64.4_100.4"


def test_the_pole_side_row_of_each_southern_band_has_the_wider_cells():
    assert grid.cell_id(-64.45, 100.45) == "-64.5_100.2"   # 0.3 degrees wide
    assert grid.cell_id(-72.95, 100.45) == "-73.0_100.0"   # 0.5
    assert grid.cell_id(-77.95, 100.45) == "-78.0_100.2"   # 0.6
    assert grid.cell_id(-83.95, 100.45) == "-84.0_99.6"    # 1.2
    for cid in ("-64.5_100.2", "-73.0_100.0", "-78.0_100.2", "-84.0_99.6"):
        west = float(cid.split("_")[1])
        lat, lon = grid.cell_centre(cid)
        assert lon == pytest.approx(west + grid.lon_factor(lat) * grid.CELL_DEG / 2)


def test_a_point_on_a_south_west_corner_belongs_to_that_cell():
    for cid in ("-66.3_100.5", "-70.0_-180.0", "-84.0_165.6", "-59.1_0.0", "-87.5_-1.2", "66.4_-52.2"):
        lat, lon = (float(part) for part in cid.split("_"))
        assert grid.cell_id(lat, lon) == cid


def test_every_southern_row_round_trips_at_both_ends_of_the_globe():
    for tenth in range(-875, -590):
        south = tenth / 10
        width = grid.lon_factor(south) * grid.CELL_DEG
        for lon in (-180 + width / 2, -width / 2, width / 2, 180 - width / 2):
            cid = grid.cell_id(south + 0.05, lon)
            assert cid.startswith(f"{south:.1f}_")
            assert grid.cell_centre(cid) == pytest.approx((south + 0.05, lon))

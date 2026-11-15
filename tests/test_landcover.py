# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
import numpy as np
import pytest
from twinfinder import landcover

WATER, BARE, GRASS, NODATA = 80, 60, 30, 0


def water_tile():
    return np.full((360, 360), WATER, dtype="uint8")


def test_tile_urls():
    assert landcover.tile_url(66, -54).endswith("ESA_WorldCover_10m_2021_v200_N66W054_Map.tif")
    assert landcover.tile_url(60, 12).endswith("ESA_WorldCover_10m_2021_v200_N60E012_Map.tif")


def test_one_bare_block_gives_exactly_one_cell():
    # Tile 66N to 69N: every cell is three 0.1-degree columns wide (36 px) and 12 px tall.
    classes = water_tile()
    classes[0:12, 0:36] = BARE  # the north-west cell
    cells = landcover.cell_shares(classes, 66, -54)
    assert len(cells) == 1
    cell = cells[0]
    assert cell["id"] == "68.9_-54.0"
    assert (cell["lat"], cell["lon"]) == pytest.approx((68.95, -53.85))
    assert cell["bare"] == pytest.approx(1.0)
    assert cell["land_share"] == pytest.approx(1.0)


def test_half_bare_half_grass():
    classes = water_tile()
    classes[0:12, 0:18] = BARE
    classes[0:12, 18:36] = GRASS
    cell, = landcover.cell_shares(classes, 66, -54)
    assert cell["bare"] == pytest.approx(0.5)


def test_nodata_is_left_out_of_every_share():
    classes = water_tile()
    classes[0:12, 0:18] = BARE
    classes[0:12, 18:36] = NODATA
    cell, = landcover.cell_shares(classes, 66, -54)
    assert cell["bare"] == pytest.approx(1.0)
    assert cell["land_share"] == pytest.approx(1.0)


def test_water_lowers_land_share_but_not_bare_share():
    classes = water_tile()
    classes[0:12, 0:9] = BARE  # a quarter of the cell
    cell, = landcover.cell_shares(classes, 66, -54)
    assert cell["land_share"] == pytest.approx(0.25)
    assert cell["bare"] == pytest.approx(1.0)


def test_cells_are_two_columns_wide_below_64_5():
    classes = np.full((360, 360), BARE, dtype="uint8")
    cells = landcover.cell_shares(classes, 60, 12)  # tile 60N to 63N
    assert len(cells) == 30 * 15

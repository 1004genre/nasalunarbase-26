# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Rock type (GLiM) and permafrost (Obu et al.) per Moon area and Mars square (scripts/build_rock_frozen.py).

No test touches the network; the made-up grids and rasters are written to a temporary folder.
"""
from __future__ import annotations

import importlib
import math
import random
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from rasterio.warp import transform as warp

from twinfinder import grid

build = importlib.import_module("scripts.build_rock_frozen")

# The legend file as PANGAEA ships it: semicolons, quoted codes, Windows line ends.
LEGEND_TEXT = ('"OBJECTID";"Value_";"Count_";"xx"\r\n'
               + "".join(f'{i};{i};1000.000000;"{code}"\r\n' for i, code in enumerate(
                   ["su", "vb", "ss", "pb", "sm", "sc", "va", "mt", "pa", "vi", "wb", "py", "pi", "ev", "nd", "ig"],
                   start=1)))


def legend_file(tmp_path: Path, text: str = LEGEND_TEXT) -> Path:
    path = tmp_path / "Classnames.txt"
    path.write_bytes(text.encode("ascii"))
    return path


def ascii_grid(tmp_path: Path, rows: list[list[int]], west: float, south: float, size: float = 0.5) -> Path:
    """A small ESRI ASCII grid laid out like the GLiM file: first row is the northernmost."""
    head = (f"ncols         {len(rows[0])}\r\nnrows         {len(rows)}\r\nxllcorner     {west}\r\n"
            f"yllcorner     {south}\r\ncellsize      {size}\r\nNODATA_value  -9999\r\n")
    body = "".join(" ".join(str(v) for v in row) + "\r\n" for row in rows)
    path = tmp_path / "grid.asc"
    path.write_text(head + body)
    return path


# ---- the class table ----------------------------------------------------------------------------------

def test_every_class_of_the_legend_maps_to_plain_words_and_three_fields(tmp_path):
    legend = build.read_legend(legend_file(tmp_path))
    assert sorted(legend) == list(range(1, 17))
    for value, code in legend.items():
        rec = build.class_record(value, legend)
        assert rec["code"] == code
        assert isinstance(rec["class"], str) and len(rec["class"]) > 3
        for field in ("volcanic", "basic_volcanic", "loose_sediment"):
            assert rec[field] in (True, False, None), (code, field)
    by_code = {code: build.class_record(v, legend) for v, code in legend.items()}
    assert (by_code["vb"]["volcanic"], by_code["vb"]["basic_volcanic"], by_code["vb"]["loose_sediment"]) == (True, True, False)
    assert (by_code["va"]["volcanic"], by_code["va"]["basic_volcanic"]) == (True, False)
    assert (by_code["vi"]["volcanic"], by_code["vi"]["basic_volcanic"]) == (True, False)
    assert by_code["py"]["volcanic"] is True
    assert (by_code["su"]["volcanic"], by_code["su"]["loose_sediment"]) == (False, True)
    assert by_code["pb"]["basic_volcanic"] is False          # gabbro is basic but plutonic, not volcanic
    assert by_code["ss"]["loose_sediment"] is False          # consolidated sedimentary rock
    for code in ("wb", "ig", "nd"):                          # the rock under water or ice is not known
        assert (by_code[code]["volcanic"], by_code[code]["basic_volcanic"], by_code[code]["loose_sediment"]) == (None, None, None)


def test_a_legend_with_a_code_the_table_does_not_know_is_refused(tmp_path):
    text = LEGEND_TEXT + '17;17;5.000000;"xx"\r\n'
    with pytest.raises(ValueError, match="xx"):
        build.read_legend(legend_file(tmp_path, text))


def test_a_legend_missing_a_class_of_the_table_is_refused(tmp_path):
    text = "\r\n".join(LEGEND_TEXT.split("\r\n")[:-3]) + "\r\n"   # drops "nd" and "ig"
    with pytest.raises(ValueError, match="ig"):
        build.read_legend(legend_file(tmp_path, text))


def test_the_real_legend_matches_the_table():
    path = build.GLIM_LEGEND
    if not path.exists():
        pytest.skip("GLiM legend not downloaded")
    legend = build.read_legend(path)
    assert set(legend.values()) == set(build.CLASSES)


# ---- grid lookup --------------------------------------------------------------------------------------

def test_grid_lookup_on_a_made_up_grid(tmp_path):
    # 3 rows x 4 columns of 0.5 degree, from 60.0 to 61.5 N and from 1.0 W to 1.0 E
    path = ascii_grid(tmp_path, [[1, 2, 3, 4], [5, 6, -9999, 8], [9, 10, 11, 12]], west=-1.0, south=60.0)
    g = build.read_glim(path)
    assert g.value(61.2, -0.8) == 1          # top row is the north
    assert g.value(61.2, 0.9) == 4
    assert g.value(60.1, -0.9) == 9
    assert g.value(60.6, 0.2) is None        # NODATA (sea) stays null
    assert g.value(61.6, 0.0) is None        # north of the grid
    assert g.value(60.6, 1.2) is None        # east of the grid
    assert g.box_id(60.6, 0.2) == "60.75_0.25"


def test_a_mars_square_is_one_box_of_the_same_grid(tmp_path):
    path = ascii_grid(tmp_path, [[2, 1], [16, -9999]], west=0.0, south=60.0)
    g = build.read_glim(path)
    legend = build.read_legend(legend_file(tmp_path))
    rec = build.rock_for_square("m_60.75_0.25", g, legend)
    assert rec["code"] == "vb" and rec["basic_volcanic"] is True and rec["box"] == "60.75_0.25"
    assert build.rock_for_square("m_60.75_0.75", g, legend)["code"] == "su"
    assert build.rock_for_square("m_60.25_0.75", g, legend) is None   # sea box: unknown, not "no rock"
    with pytest.raises(ValueError):
        build.rock_for_square("m_60.5_0.25", g, legend)               # a centre on a box edge: grids do not line up


def test_an_area_takes_the_box_at_its_centre_and_lists_every_box_it_touches(tmp_path):
    # 80.0 to 80.5 N, 0 to 1 E: two boxes side by side
    path = ascii_grid(tmp_path, [[2, 1]], west=0.0, south=80.0)
    g = build.read_glim(path)
    legend = build.read_legend(legend_file(tmp_path))
    rec = build.rock_for_area("80.0_0.0", g, legend)     # 80.0-80.1 N, 0.0-0.6 E (6 columns of 0.1 at 80 N)
    assert rec["code"] == "vb" and rec["box_used"] == "centre" and rec["coarse"] is True
    assert rec["codes_in_touched_boxes"] == ["vb", "su"]


def test_an_area_whose_centre_box_is_sea_falls_back_to_the_nearest_touched_box(tmp_path):
    path = ascii_grid(tmp_path, [[-9999, 1]], west=0.0, south=80.0)
    g = build.read_glim(path)
    legend = build.read_legend(legend_file(tmp_path))
    rec = build.rock_for_area("80.0_0.0", g, legend)
    assert rec["code"] == "su" and rec["box_used"] == "nearest touched box with a class"
    path = ascii_grid(tmp_path, [[-9999, -9999]], west=0.0, south=80.0)
    assert build.rock_for_area("80.0_0.0", build.read_glim(path), legend) is None


# ---- permafrost ---------------------------------------------------------------------------------------

def test_zone_from_probability():
    assert build.zone(None) is None
    assert build.zone(0.0) == "none"
    assert build.zone(0.03) == "isolated patches"
    assert build.zone(0.1) == "sporadic"
    assert build.zone(0.5) == "discontinuous"
    assert build.zone(0.9) == "continuous"
    assert build.zone(1.0) == "continuous"


def test_a_missing_value_stays_null():
    assert build.class_record(None, {1: "su"}) is None
    assert build.mean_or_none(0.0, 0) is None                 # no pixel with a value: unknown, not 0
    assert build.mean_or_none(0.0, 5) == 0.0                  # five pixels that all say 0: a real 0
    assert build.zone(None) is None


def test_vector_cell_keys_match_grid_cell_id():
    rng = random.Random(4)
    lats = [rng.uniform(59.0, 83.999) for _ in range(3000)] + [rng.uniform(-87.499, -59.001) for _ in range(3000)]
    lons = [rng.uniform(-180.0, 179.999) for _ in range(6000)]
    keys = build.cell_keys(np.array(lats), np.array(lons))
    for lat, lon, key in zip(lats, lons, keys):
        cid = grid.cell_id(lat, lon)
        assert build.key_of_id(cid) == key, (lat, lon, cid)


def test_nine_points_spread_through_the_square():
    pts = build.nine_points(70.75, 0.75)
    assert len(pts) == 9 and (70.75, 0.75) in pts
    for lat, lon in pts:
        assert 70.5 < lat < 71.0 and 0.5 < lon < 1.0


def polar_raster(tmp_path: Path, name: str = "perprob.tif") -> Path:
    """A 1 km raster in EPSG:3995 over 70-71 N, 0-2.5 E: 0.95 north of 70.5 N, 0.2 south of it,
    and no value east of 1.5 E."""
    xs, ys = warp("EPSG:4326", "EPSG:3995", [0.0, 2.5, 0.0, 2.5], [70.0, 70.0, 71.0, 71.0])
    x0, x1 = math.floor(min(xs) / 1000) * 1000 - 5000, math.ceil(max(xs) / 1000) * 1000 + 5000
    y0, y1 = math.floor(min(ys) / 1000) * 1000 - 5000, math.ceil(max(ys) / 1000) * 1000 + 5000
    width, height = int((x1 - x0) / 1000), int((y1 - y0) / 1000)
    tr = from_origin(x0, y1, 1000, 1000)
    cols, rows = np.meshgrid(np.arange(width) + 0.5, np.arange(height) + 0.5)
    px, py = tr * (cols.ravel(), rows.ravel())
    lon, lat = warp("EPSG:3995", "EPSG:4326", px, py)
    lon, lat = np.array(lon).reshape(height, width), np.array(lat).reshape(height, width)
    nodata = -3.4028230607370965e+38
    data = np.where(lat >= 70.5, 0.95, 0.2).astype("float32")
    data[lon > 1.5] = nodata
    path = tmp_path / name
    with rasterio.open(path, "w", driver="GTiff", width=width, height=height, count=1, dtype="float32",
                       crs="EPSG:3995", transform=tr, nodata=nodata, tiled=True, blockxsize=128, blockysize=128) as dst:
        dst.write(data, 1)
    return path


def test_area_means_on_a_made_up_raster(tmp_path):
    path = polar_raster(tmp_path)
    ids = ["70.6_0.0", "70.2_0.0", "70.6_1.8", "70.4_1.2"]   # widths at 70 N: 0.3 degree
    got = build.area_means(path, ids, valid=(0.0, 1.0), strip_rows=7)
    mean, n, total = got["70.6_0.0"]
    assert mean == pytest.approx(0.95, abs=1e-6) and n == total and n > 50
    assert got["70.2_0.0"][0] == pytest.approx(0.2, abs=1e-6)
    assert got["70.6_1.8"][0] is None and got["70.6_1.8"][1] == 0 and got["70.6_1.8"][2] > 50   # no value: null
    assert got["70.4_1.2"][0] == pytest.approx(0.2, abs=1e-6)   # 70.4-70.5 N: all south of 70.5
    assert build.zone(got["70.6_0.0"][0]) == "continuous"


def test_square_means_read_nine_points(tmp_path):
    path = polar_raster(tmp_path)
    got = build.square_means(path, {"m_70.75_0.75": (70.75, 0.75), "m_70.25_0.25": (70.25, 0.25),
                                    "m_70.75_1.75": (70.75, 1.75), "m_70.75_1.25": (70.75, 1.25)}, valid=(0.0, 1.0))
    assert got["m_70.75_0.75"] == (pytest.approx(0.95, abs=1e-6), 9)
    assert got["m_70.25_0.25"] == (pytest.approx(0.2, abs=1e-6), 9)
    assert got["m_70.75_1.75"] == (None, 0)                     # every point without a value: null, not 0
    mean, n = got["m_70.75_1.25"]                               # points at 1.083, 1.25, 1.417 E: all inside
    assert n == 9 and mean == pytest.approx(0.95, abs=1e-6)

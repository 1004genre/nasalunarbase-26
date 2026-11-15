# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Fact cards for the four lunar targets: geometry, the Diviner table reader, the statistics and the card itself."""
import importlib
import json
import math
from pathlib import Path

import numpy as np
import pytest

from twinfinder import moon

cards = importlib.import_module("scripts.build_moon_cards")

ROOT = Path(__file__).resolve().parents[1]

# The heading and the first data record of dlre_prp_south.tab, as downloaded (each is 208 characters plus CR LF).
REAL_HEADER = ("      tri1_x,       tri1_y,       tri1_z,       tri2_x,       tri2_y,       tri2_z,"
               "       tri3_x,       tri3_y,       tri3_z,        tri_clon,        tri_clat,        tri_calt,"
               " temp_avg, temp_max,   ice_depth")
REAL_ROW = ("   299.52036,   -299.52036,  -1685.56519,    299.02863,   -299.52850,  -1685.65479,"
            "    299.03738,   -299.03738,  -1685.74780,   -45.015949249,   -75.905227661,     0.579086423,"
            "  162.934,  272.164,  -999.00000")
R_KM = 1737.4


def body_xyz(lat_deg: float, lon_deg: float, alt_km: float = 0.0) -> tuple[float, float, float]:
    """Moon-centred x, y, z in km, as the table gives its triangle corners."""
    lat, lon, r = math.radians(lat_deg), math.radians(lon_deg), R_KM + alt_km
    return r * math.cos(lat) * math.cos(lon), r * math.cos(lat) * math.sin(lon), r * math.sin(lat)


def map_to_latlon(x_km: float, y_km: float) -> tuple[float, float]:
    lat, lon = moon.polar_xy_to_latlon(x_km * 1000.0, y_km * 1000.0)
    return lat, lon


def prp_row(corners_xy_km, temp_avg: float, temp_max: float, ice_depth: float, alt_km: float = 0.0) -> str:
    """One table record for a triangle given by three map positions (km, the 5 m models' projection)."""
    numbers = []
    for x, y in corners_xy_km:
        numbers += [f"{v:12.5f}" for v in body_xyz(*map_to_latlon(x, y), alt_km)]
    cx = sum(x for x, _ in corners_xy_km) / 3.0
    cy = sum(y for _, y in corners_xy_km) / 3.0
    clat, clon = map_to_latlon(cx, cy)
    clon = clon - 360.0 if clon > 180.0 else clon      # the table runs from -180 to 180
    numbers += [f"{clon:15.9f}", f"{clat:15.9f}", f"{alt_km:15.9f}",
                f"{temp_avg:8.3f}", f"{temp_max:8.3f}", f"{ice_depth:11.5f}"]
    row = ", ".join(numbers)
    assert len(row) == 208
    return row


def write_table(path: Path, rows: list[str], header: str = REAL_HEADER) -> Path:
    path.write_bytes("".join(line + "\r\n" for line in [header, *rows]).encode("ascii"))
    return path


def square(x0: float, y0: float, size: float = 0.5):
    """Two triangles that fill one mesh square whose lower-left corner is (x0, y0), in km."""
    a, b, c, d = (x0, y0), (x0 + size, y0), (x0 + size, y0 + size), (x0, y0 + size)
    return [(a, b, c), (a, c, d)]


TARGET = {"id": "made-up", "name": "Made-up site", "centre_lat": moon.polar_xy_to_latlon(40_000.0, 30_000.0)[0],
          "centre_lon": moon.polar_xy_to_latlon(40_000.0, 30_000.0)[1], "extent_km": [2.0, 2.0],
          "sun_max_elev_deg": 2.0768, "sun_max_elev_range_deg": [1.70, 2.45],
          "illumination_mean": 0.2929, "illumination_max": 0.9348, "permanent_shadow_fraction": 0.0303,
          "source": "https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/Site01/Site01_final_adj_5mpp_surf.tif"}


# ---- geometry ----

def test_a_one_metre_object_throws_a_one_metre_shadow_at_45_degrees():
    assert cards.shadow_length_m(1.0, 45.0) == pytest.approx(1.0)


def test_shadow_at_the_lowest_ceiling_is_about_28_metres():
    assert cards.shadow_length_m(1.0, 2.076837165962993) == pytest.approx(27.58, abs=0.01)


def test_no_shadow_length_without_a_sun_above_the_horizon():
    assert cards.shadow_length_m(1.0, 0.0) is None
    assert cards.shadow_length_m(1.0, None) is None


def test_latlon_to_map_metres_undoes_the_projects_own_conversion():
    for x, y in [(0.0, 30_323.0), (30_323.0, 0.0), (-80_000.0, 95_000.0), (12_345.0, -180_000.0)]:
        lat, lon = moon.polar_xy_to_latlon(x, y)
        back_x, back_y = cards.latlon_to_polar_xy(lat, lon)
        assert back_x == pytest.approx(x, abs=1e-3)
        assert back_y == pytest.approx(y, abs=1e-3)


def test_latlon_to_map_metres_takes_arrays_and_negative_longitudes():
    x, y = cards.latlon_to_polar_xy(np.array([-89.0, -89.0]), np.array([90.0, -90.0]))
    assert x == pytest.approx([30_324.1, -30_324.1], abs=0.1)      # 2 R tan(0.5 degrees), one degree from the pole
    assert y == pytest.approx([0.0, 0.0], abs=1e-6)


def test_target_bounds_are_the_centre_plus_and_minus_half_the_extent():
    left, bottom, right, top = cards.target_bounds(TARGET)
    assert (left, right) == pytest.approx((39_000.0, 41_000.0), abs=1e-3)
    assert (bottom, top) == pytest.approx((29_000.0, 31_000.0), abs=1e-3)


def test_triangle_area_is_measured_on_the_map():
    corners = np.array([[body_xyz(*map_to_latlon(x, y)) for x, y in tri] for tri in square(40.0, 30.0)])
    assert cards.triangle_map_area_km2(corners) == pytest.approx([0.125, 0.125], rel=1e-4)


# ---- the table reader ----

def test_reader_returns_the_numbers_of_a_real_record(tmp_path):
    table = cards.open_prp(write_table(tmp_path / "t.tab", [REAL_ROW]))
    assert table.shape == (1, 210)
    assert cards.prp_column(table, "tri_clon")[0] == -45.015949249
    assert cards.prp_column(table, "tri_clat")[0] == -75.905227661
    assert cards.prp_column(table, "tri_calt")[0] == 0.579086423
    assert cards.prp_column(table, "temp_avg")[0] == 162.934
    assert cards.prp_column(table, "temp_max")[0] == 272.164
    assert cards.prp_column(table, "ice_depth")[0] == -999.0
    assert cards.prp_column(table, "tri1_x")[0] == 299.52036
    assert cards.prp_column(table, "tri3_z")[0] == -1685.7478


def test_reader_can_take_chosen_rows_only(tmp_path):
    rows = [prp_row(tri, 50.0 + k, 100.0 + k, 0.1 * k) for k, tri in enumerate(square(40.0, 30.0) + square(40.5, 30.0))]
    table = cards.open_prp(write_table(tmp_path / "t.tab", rows))
    assert cards.prp_column(table, "temp_avg", np.array([3, 1])) == pytest.approx([53.0, 51.0])


def test_reader_refuses_a_file_that_is_not_whole_records(tmp_path):
    path = write_table(tmp_path / "t.tab", [REAL_ROW])
    path.write_bytes(path.read_bytes()[:-7])
    with pytest.raises(ValueError, match="210"):
        cards.open_prp(path)


def test_reader_refuses_a_table_with_other_columns(tmp_path):
    other = REAL_HEADER.replace("ice_depth", "ice_thick")
    with pytest.raises(ValueError, match="column"):
        cards.open_prp(write_table(tmp_path / "t.tab", [REAL_ROW], header=other))


# ---- statistics ----

def test_area_stats_weigh_each_triangle_by_its_area():
    out = cards.area_stats(np.array([100.0, 200.0, 40.0]), np.array([1.0, 1.0, 2.0]))
    assert out == {"mean": pytest.approx(95.0), "min": pytest.approx(40.0), "max": pytest.approx(200.0)}


def test_area_stats_of_nothing_are_unknown_not_zero():
    assert cards.area_stats(np.array([]), np.array([])) == {"mean": None, "min": None, "max": None}


def test_minus_999_means_ice_is_not_stable_and_still_counts_as_area():
    depth = np.array([-999.0, 0.0, 0.5, 2.0])
    out = cards.ice_shares(depth, np.ones(4))
    assert out["stable_within_reach_share"] == pytest.approx(0.75)
    assert out["stable_at_surface_share"] == pytest.approx(0.25)
    assert out["not_stable_within_reach_share"] == pytest.approx(0.25)
    assert out["stable_within_1m_share"] == pytest.approx(0.5)
    assert out["shallowest_m"] == pytest.approx(0.0)
    assert out["deepest_stable_m"] == pytest.approx(2.0)


def test_the_undocumented_minus_1_is_read_as_ice_on_the_surface_and_reported_apart():
    depth = np.array([-1.0, -999.0, 0.0, 0.5])
    out = cards.ice_shares(depth, np.ones(4))
    assert out["stable_within_reach_share"] == pytest.approx(0.75)
    assert out["stable_at_surface_share"] == pytest.approx(0.5)
    assert out["surface_cold_trap_share"] == pytest.approx(0.25)
    assert out["stable_within_reach_share_without_undocumented_value"] == pytest.approx(0.5)
    assert out["shallowest_m"] == 0.0
    assert out["deepest_stable_m"] == pytest.approx(0.5)


@pytest.mark.parametrize("odd", [-5.0, 3.5, float("nan")])
def test_any_other_ice_value_is_refused(odd):
    with pytest.raises(ValueError, match="ice depth"):
        cards.ice_shares(np.array([0.2, odd]), np.ones(2))


def test_the_grounds_for_reading_minus_1_are_counted_over_the_whole_table(tmp_path):
    rows = [prp_row(tri, 40.0, t_max, ice) for tri, (t_max, ice) in
            zip(square(40.0, 30.0) + square(41.0, 30.0), [(60.0, -1.0), (95.0, -1.0), (105.0, 0.0), (250.0, -999.0)])]
    out = cards.undocumented_value_check(cards.open_prp(write_table(tmp_path / "t.tab", rows)))
    assert (out["records"], out["of_records"]) == (2, 4)
    assert out["highest_yearly_maximum_K_among_them"] == 95.0
    assert out["lowest_yearly_maximum_K_among_all_other_records"] == 105.0
    assert out["in_label"] is False


def test_ice_shares_are_shares_of_area_not_of_triangles():
    out = cards.ice_shares(np.array([-999.0, 0.3]), np.array([3.0, 1.0]))
    assert out["stable_within_reach_share"] == pytest.approx(0.25)


def test_ice_shares_of_nothing_are_unknown():
    out = cards.ice_shares(np.array([]), np.array([]))
    assert out["stable_within_reach_share"] is None
    assert out["stable_at_surface_share"] is None
    assert out["shallowest_m"] is None


def test_where_ice_is_nowhere_stable_the_share_is_a_real_zero_and_the_depth_is_unknown():
    out = cards.ice_shares(np.array([-999.0, -999.0]), np.ones(2))
    assert out["stable_within_reach_share"] == 0.0
    assert out["shallowest_m"] is None
    assert out["deepest_stable_m"] is None


def made_up_table(tmp_path: Path) -> Path:
    """Four squares inside the 2 km target (40, 30) and one square 5 km away, which must be left out."""
    rows = []
    inside = [(39.0, 29.0, 60.0, 150.0, -999.0), (40.0, 29.0, 80.0, 250.0, -999.0),
              (39.0, 30.0, 40.0, 90.0, 0.0), (40.0, 30.0, 100.0, 300.0, 1.5)]
    for x0, y0, t_avg, t_max, ice in inside:
        rows += [prp_row(tri, t_avg, t_max, ice) for tri in square(x0, y0, 1.0)]
    rows += [prp_row(tri, 390.0, 400.0, 0.0) for tri in square(45.0, 30.0, 1.0)]
    return write_table(tmp_path / "made_up.tab", rows)


def test_diviner_numbers_come_from_the_triangles_inside_the_target_only(tmp_path):
    table = cards.open_prp(made_up_table(tmp_path))
    x_m, y_m = cards.triangle_centres_xy(table)
    out = cards.diviner_for_target(table, x_m, y_m, TARGET)
    assert out["triangles"] == 8
    assert out["area_covered_km2"] == pytest.approx(4.0, rel=1e-3)
    assert out["annual_mean_temp_2cm_K"] == {"mean": pytest.approx(70.0, abs=0.01), "min": 40.0, "max": 100.0}
    assert out["annual_max_temp_surface_K"] == {"mean": pytest.approx(197.5, abs=0.01), "min": 90.0, "max": 300.0}
    assert out["ice"]["stable_within_reach_share"] == pytest.approx(0.5, abs=1e-4)
    assert out["ice"]["stable_at_surface_share"] == pytest.approx(0.25, abs=1e-4)
    assert out["model_based"] is True


def test_a_target_the_table_does_not_cover_gets_nulls(tmp_path):
    table = cards.open_prp(made_up_table(tmp_path))
    x_m, y_m = cards.triangle_centres_xy(table)
    lat, lon = moon.polar_xy_to_latlon(-150_000.0, 10_000.0)
    elsewhere = dict(TARGET, centre_lat=lat, centre_lon=lon)
    out = cards.diviner_for_target(table, x_m, y_m, elsewhere)
    assert out["triangles"] == 0
    assert out["annual_mean_temp_2cm_K"] == {"mean": None, "min": None, "max": None}
    assert out["ice"]["stable_within_reach_share"] is None


def test_temperatures_that_are_not_positive_are_left_out_and_counted(tmp_path):
    rows = [prp_row(tri, t, 200.0, -999.0) for tri, t in zip(square(40.0, 30.0, 1.0), (50.0, 0.0))]
    table = cards.open_prp(write_table(tmp_path / "t.tab", rows))
    x_m, y_m = cards.triangle_centres_xy(table)
    out = cards.diviner_for_target(table, x_m, y_m, TARGET)
    assert out["triangles"] == 2
    assert out["triangles_without_temperature"] == 1
    assert out["annual_mean_temp_2cm_K"]["mean"] == pytest.approx(50.0)


# ---- the saved LROC pages ----

MOSAIC_PAGE = """<table><tr><th>Image ID</th><th>Center Lat</th><th>Center Lon</th><th>Incidence</th><th>Pixel Scale</th></tr>
<tr><td>M108857717L</td><td>-85.63</td><td>60.43</td><td>84&deg;</td><td>1.70 m/px</td></tr>
<tr><td>M139580268R</td><td>-82.83</td><td>55.41</td><td>82&deg;</td><td>1.26 m/px</td></tr>
<tr><td>M1153615365R</td><td>-84.14</td><td>61.20</td><td>90&deg;</td><td>1.30 m/px</td></tr></table>"""


def test_images_of_a_mosaic_page_are_read_with_their_incidence():
    images = cards.mosaic_images(MOSAIC_PAGE)
    assert [image["id"] for image in images] == ["M108857717L", "M139580268R", "M1153615365R"]
    assert images[1] == {"id": "M139580268R", "lat": -82.83, "lon": 55.41, "incidence_deg": 82}


def test_sun_heights_of_a_mosaic_are_90_minus_incidence():
    out = cards.mosaic_sun_heights(MOSAIC_PAGE)
    assert (out["images_listed"], out["sun_height_min_deg"], out["sun_height_max_deg"]) == (3, 0, 8)
    assert out["images_above_flat_ceiling_at_their_latitude"] == 0     # 8 is under 90 - 82.83 + 1.54 = 8.71


def test_an_image_taken_above_the_flat_ceiling_is_counted():
    page = MOSAIC_PAGE.replace("<td>84&deg;</td>", "<td>80&deg;</td>")   # Sun 10 degrees up at 85.63 S: ceiling 5.91
    assert cards.mosaic_sun_heights(page)["images_above_flat_ceiling_at_their_latitude"] == 1


def test_a_page_without_an_image_table_gives_no_sun_heights():
    assert cards.mosaic_sun_heights("<html><body>nothing here</body></html>") is None


# ---- the cards ----

REAL_IDS = ["connecting-ridge", "malapert", "mons-mouton", "nobile-rim-2"]
MATCH_ITEMS = ["vacuum", "gravity", "dust", "temperature", "radiation", "black shadows", "slow Sun"]


def made_up_target(target_id: str) -> dict:
    return dict(TARGET, id=target_id)


def test_every_real_target_has_provenance_with_links():
    for target_id in REAL_IDS:
        facts = cards.PROVENANCE[target_id]
        assert facts["official_name"]
        assert facts["nasa_list"]["links"], target_id
        assert all(link.startswith("https://") for link in facts["nasa_list"]["links"])
        assert facts["pgda_model"]["page"] == "https://pgda.gsfc.nasa.gov/products/78"


def test_card_has_what_the_page_needs(tmp_path):
    table = cards.open_prp(made_up_table(tmp_path))
    x_m, y_m = cards.triangle_centres_xy(table)
    target = made_up_target("connecting-ridge")
    card = cards.build_card(target, cards.diviner_for_target(table, x_m, y_m, target))
    for key in ("id", "official_name", "name_in_project", "nasa_list", "pgda_model", "sun_ceiling",
                "shadow_of_1m_object_at_ceiling_m", "lit", "permanent_shadow", "diviner", "picture",
                "earth_cannot_match", "why_stored", "why_check"):
        assert key in card, key
    assert card["official_name"] == "Connecting Ridge"
    assert card["sun_ceiling"]["deg"] == pytest.approx(2.0768)
    assert "1.54" in card["sun_ceiling"]["how"]
    assert card["shadow_of_1m_object_at_ceiling_m"] == pytest.approx(27.58, abs=0.01)
    assert card["lit"]["mean_share"] == pytest.approx(0.2929)
    assert card["lit"]["best_point_share"] == pytest.approx(0.9348)
    assert card["permanent_shadow"]["share"] == pytest.approx(0.0303)
    assert card["lit"]["source"].startswith("https://pgda.gsfc.nasa.gov/")
    assert card["pgda_model"]["site"] == "Site01"
    assert card["pgda_model"]["dem_url"] == target["source"]


def test_the_stored_reason_for_the_ridge_is_the_sourced_wording():
    # The unconfirmed reason was replaced at the source (twinfinder/moon.py) by the wording this check proposed.
    card = cards.build_card(made_up_target("connecting-ridge"), cards.EMPTY_DIVINER)
    check = card["why_check"]
    assert check["confirmed"] is True and check["proposed_wording"] is None
    assert len(check["proposed_wording_sources"]) == 3 and all(u.startswith("https://") for u in check["proposed_wording_sources"])
    assert moon.TARGETS[0].why in check["note"] and "replaced" in check["note"]
    assert "Moon Base" not in json.dumps(card)


def test_earth_cannot_match_lists_the_seven_things_with_numbers_or_null(tmp_path):
    table = cards.open_prp(made_up_table(tmp_path))
    x_m, y_m = cards.triangle_centres_xy(table)
    target = made_up_target("malapert")
    card = cards.build_card(target, cards.diviner_for_target(table, x_m, y_m, target))
    items = {item["what"]: item for item in card["earth_cannot_match"]}
    assert list(items) == MATCH_ITEMS
    for item in items.values():
        assert set(item) >= {"what", "moon", "earth", "number", "unit", "source"}
    assert items["gravity"]["number"] == pytest.approx(1.62)
    assert items["slow Sun"]["number"] == pytest.approx(29.53)
    assert items["temperature"]["number"] == pytest.approx(70.0, abs=0.01)
    assert items["black shadows"]["number"] == pytest.approx(
        cards.shadow_length_m(1.0, target["sun_max_elev_deg"]), abs=0.005)       # written to the centimetre
    assert items["dust"]["number"] is None            # no number we could source: unknown, not zero


def test_card_without_diviner_numbers_keeps_them_null():
    card = cards.build_card(made_up_target("nobile-rim-2"), cards.EMPTY_DIVINER)
    assert card["diviner"]["annual_mean_temp_2cm_K"] == {"mean": None, "min": None, "max": None}
    items = {item["what"]: item for item in card["earth_cannot_match"]}
    assert items["temperature"]["number"] is None


def test_a_target_without_provenance_is_refused():
    with pytest.raises(KeyError):
        cards.build_card(made_up_target("somewhere-else"), cards.EMPTY_DIVINER)


def test_file_is_written_beside_and_renamed(tmp_path):
    out = tmp_path / "cards.json"
    cards.write_json(out, {"a": 1.23456789, "b": None})
    assert json.loads(out.read_text()) == {"a": 1.23456789, "b": None}
    assert [p.name for p in tmp_path.iterdir()] == ["cards.json"]


def test_not_a_number_is_never_written(tmp_path):
    with pytest.raises(ValueError):
        cards.write_json(tmp_path / "cards.json", {"a": float("nan")})
    assert list(tmp_path.iterdir()) == []


def test_whole_run_on_a_made_up_table(tmp_path):
    targets = tmp_path / "targets.json"
    targets.write_text(json.dumps([made_up_target(target_id) for target_id in REAL_IDS]))
    out = tmp_path / "moon_cards.json"
    cards.main(["--targets", str(targets), "--table", str(made_up_table(tmp_path)), "--out", str(out),
                "--dem-dir", str(tmp_path / "no_models_here")])
    result = json.loads(out.read_text())
    assert [card["id"] for card in result["cards"]] == REAL_IDS
    assert result["meta"]["diviner"]["special_value"]["value"] == -999.0
    assert result["cards"][0]["diviner"]["triangles"] == 8
    assert result["cards"][0]["diviner"]["altitude_check"] is None      # no 5 m model at hand: unknown


# ---- the file in the project, when it has been built ----

def test_built_file_agrees_with_the_targets_file():
    built, targets = ROOT / "data/derived/moon_cards.json", ROOT / "data/derived/moon_targets.json"
    if not built.exists():
        pytest.skip("data/derived/moon_cards.json has not been built")
    result = json.loads(built.read_text())
    by_id = {t["id"]: t for t in json.loads(targets.read_text())}
    assert [card["id"] for card in result["cards"]] == list(by_id)
    for card in result["cards"]:
        target = by_id[card["id"]]
        assert card["sun_ceiling"]["deg"] == pytest.approx(target["sun_max_elev_deg"])
        assert card["lit"]["mean_share"] == pytest.approx(target["illumination_mean"])
        assert card["permanent_shadow"]["share"] == pytest.approx(target["permanent_shadow_fraction"])
        mean_k = card["diviner"]["annual_mean_temp_2cm_K"]["mean"]
        assert mean_k is None or 20.0 < mean_k < 400.0
        share = card["diviner"]["ice"]["stable_within_reach_share"]
        assert share is None or 0.0 <= share <= 1.0


# ---- added by the member ADDITIONS-CHECK (14 November 2026) ----

def test_celsius_is_kelvin_minus_273_15_and_unknown_stays_null():
    assert cards._celsius({"mean": 273.15, "min": 0.0, "max": None}) == {"mean": 0.0, "min": -273.15, "max": None}
    assert cards._celsius({"mean": 122.52, "min": 39.186, "max": 186.478})["mean"] == pytest.approx(-150.63, abs=0.005)

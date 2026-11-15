# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Winter leads: what the bare-ground screen hides in the winter half. No test touches the network."""
import importlib
import json
from pathlib import Path

import numpy as np
import pytest

from twinfinder import grazing, regions, rock_south, sun

build = importlib.import_module("scripts.build_winter_leads")

OUT = Path("data/derived/winter_leads.json")
TARGETS = grazing.load_targets()
NOBILE = next(t for t in TARGETS if t["id"] == "nobile-rim-2")


def square(cid: str, lat: float, lon: float, land: float, bare: float, lichen: float = 0.0, ice: float = 0.0) -> dict:
    return {"id": cid, "lat": lat, "lon": lon, "land_share": land, "bare": bare, "lichen": lichen, "ice": ice}


# Places whose coordinates are not in doubt (town or airport, to two decimals).
KNOWN_PLACES = [
    ("Lerwick", 60.15, -1.15, "Shetland"),
    ("Westray", 59.30, -2.95, "Orkney"),
    ("Torshavn", 62.01, -6.77, "Faroe Islands"),
    ("Reykjavik", 64.15, -21.94, "Iceland"),
    ("Bergen", 60.39, 5.32, "Norway: Vestland"),
    ("Haugesund", 59.41, 5.27, "Norway: Rogaland"),
    ("Alesund", 62.47, 6.15, "Norway: More og Romsdal"),
    ("Bodo", 67.28, 14.40, "Norway: Nordland"),
    ("Tromso", 69.65, 18.96, "Norway: Troms"),
    ("Murmansk", 68.97, 33.08, "Kola Peninsula (Murmansk coast)"),
    ("Tallinn", 59.44, 24.75, "Estonia: north coast"),
    ("Yakutat", 59.55, -139.73, "Alaska: Gulf coast (Kenai to Yakutat)"),
    ("Qaqortoq", 60.72, -46.04, "South Greenland"),
]


@pytest.mark.parametrize("name, lat, lon, expected", KNOWN_PLACES)
def test_the_region_boxes_name_places_whose_coordinates_are_known(name, lat, lon, expected):
    assert build.region(lat, lon) == expected


def test_a_point_in_no_box_of_this_script_keeps_the_project_name():
    assert build.region(67.86, 20.23) == regions.region(67.86, 20.23) == "Norway, Sweden or Finland"   # Kiruna
    assert build.region(74.7, -95.0) == "Arctic Canada"                                               # Resolute


def test_bare_km2_is_cell_area_times_land_share_times_bare_share_as_in_the_cells_file():
    cell = square("62.2_-6.6", 62.25, -6.5, 0.5, 0.04)
    assert build.bare_km2(cell) == pytest.approx(rock_south.cell_area_km2("62.2_-6.6") * 0.5 * 0.04)
    stored = next(c for c in json.loads(Path("data/derived/grazing_cells.json").read_text())["cells"]
                  if c["gridded"] and c["hemisphere"] == "N")
    assert build.bare_km2(stored) == pytest.approx(stored["bare_km2"], abs=0.001)


def test_bare_samples_says_how_many_land_cover_samples_the_bare_ground_rests_on():
    # south of 64.5 N a square is 12 x 24 samples; half of it land, 2 of the 144 land samples bare
    assert build.bare_samples(square("60.5_-1.6", 60.55, -1.5, 0.5, 2 / 144)) == 2
    # between 64.5 and 73 N a square is 12 x 36 samples
    assert build.bare_samples(square("65.0_12.0", 65.05, 12.15, 1.0, 5 / 432)) == 5


def test_hidden_squares_are_those_under_the_screen_that_still_hold_bare_ground_at_the_floor():
    north = [square("60.0_0.0", 60.05, 0.1, 1.0, 0.20),      # passes the screen: not hidden
             square("60.0_0.2", 60.05, 0.3, 1.0, 0.149),     # hidden, about 19 km2 of bare ground
             square("60.0_0.4", 60.05, 0.5, 1.0, 0.004),     # hidden, about 0.5 km2
             square("60.0_0.6", 60.05, 0.7, 1.0, 0.0)]       # no bare ground at all
    assert [c["id"] for c in build.hidden_squares(north, 0.25)] == ["60.0_0.2", "60.0_0.4"]
    assert [c["id"] for c in build.hidden_squares(north, 1.0)] == ["60.0_0.2"]
    assert build.hidden_squares(north, 1.0)[0]["bare_km2"] == pytest.approx(build.bare_km2(north[1]))
    assert "bare_km2" not in north[1]   # the land-cover records are not changed


def test_the_screen_is_the_one_of_the_pipeline():
    assert build.MIN_BARE == importlib.import_module("scripts.build_grazing_cells").MIN_BARE == 0.15
    assert build.FLOOR_KM2 in build.FLOORS_KM2 and sorted(build.FLOORS_KM2) == [0.25, 1.0, 3.0]


def test_rest_of_land_is_what_the_land_cover_file_can_say():
    rest = build.rest_of_land(square("x", 60.05, 0.1, 1.0, 0.05, lichen=0.10, ice=0.02))
    assert rest == {"lichen_and_moss": 0.1, "ice_and_snow": 0.02, "other_cover_not_split_in_the_file": 0.83}


def snow_with_odds(n: int, odds: float) -> dict:
    return {"odds": np.full((n, sun.N_BINS), odds), "summaries": [{"status": "measured"}] * n}


def test_hours_come_from_the_project_sun_table_and_snow_odds():
    cells = [square("60.1_-1.2", 60.15, -1.1, 0.5, 0.01), square("62.0_-6.8", 62.05, -6.7, 0.5, 0.01)]
    table = sun.long_band_minutes_table([60.15, 62.05], [t["limit_deg"] for t in TARGETS],
                                        grazing.STRETCH_MIN_H, grazing.STEP_MINUTES)
    flat = grazing.flat_hours(table[TARGETS.index(NOBILE)], NOBILE["elev_bins"])
    got = build.hours(cells, TARGETS, snow_with_odds(2, 1.0), {})["nobile-rim-2"]
    for k in range(2):
        assert got["winter_flat"][k] == pytest.approx(grazing.total(flat[k], grazing.WINTER_BINS_NORTH), abs=0.01)
        assert got["year_flat"][k] == pytest.approx(grazing.total(flat[k]), abs=0.01)
    assert got["winter_snow_free"] == pytest.approx(got["winter_flat"])            # odds 1: nothing lost to snow
    assert 250 < got["winter_flat"][0] < 330 and got["winter_flat"][1] > got["winter_flat"][0]
    half = build.hours(cells, TARGETS, snow_with_odds(2, 0.5), {})["nobile-rim-2"]
    assert half["winter_snow_free"] == pytest.approx(0.5 * got["winter_flat"])
    assert half["winter_flat"] == pytest.approx(got["winter_flat"])


def test_hours_after_terrain_are_unknown_without_a_horizon_and_never_zero():
    cells = [square("60.1_-1.2", 60.15, -1.1, 0.5, 0.01), square("60.1_-1.4", 60.15, -1.3, 0.5, 0.01),
             square("60.1_-1.6", 60.15, -1.5, 0.5, 0.01)]
    n_elev = len(sun.ELEV_EDGES_DEG) - 1
    shares = {0: np.ones((sun.AZ_SECTORS, n_elev)), 1: np.zeros((sun.AZ_SECTORS, n_elev))}
    got = build.hours(cells, TARGETS, snow_with_odds(3, 0.8), shares)["nobile-rim-2"]
    assert got["winter_open"][0] == pytest.approx(got["winter_snow_free"][0])   # a fully open horizon takes nothing
    assert got["winter_open"][1] == 0.0                                         # a wall all round takes everything
    assert np.isnan(got["winter_open"][2]) and np.isnan(got["year_open"][2])    # no horizon: unknown
    assert build.known(got["winter_open"][2]) is None


def test_unknown_snow_gives_unknown_hours_not_zero():
    cells = [square("60.1_-1.2", 60.15, -1.1, 0.5, 0.01)]
    snow_of = {"odds": np.full((1, sun.N_BINS), np.nan), "summaries": [{"status": "no data"}]}
    got = build.hours(cells, TARGETS, snow_of, {})["nobile-rim-2"]
    assert np.isnan(got["winter_snow_free"][0]) and got["winter_flat"][0] > 0


def test_the_winter_sun_of_the_atlantic_rim_stands_in_the_south():
    cells = [square("60.1_-1.2", 60.15, -1.1, 0.5, 0.01)]
    got = build.hours(cells, TARGETS, snow_with_odds(1, 1.0), {})["nobile-rim-2"]
    assert 0.9 < got["south_share_winter"][0] <= 1.0


def skip_if_the_cells_file_is_older_than_the_sun_code(disagreement) -> None:
    """A disagreement with the cells file is a failure, unless the Sun code changed after that file was built."""
    if disagreement and not build.built_with()["same_code"]:
        pytest.skip("twinfinder/sun.py changed after grazing_cells.json was built and gives other hours: "
                    "build that file again first")


def test_hours_match_the_cells_file_for_squares_the_pipeline_already_holds():
    stored = json.loads(Path("data/derived/grazing_cells.json").read_text())
    if stored["meta"]["snow_archive_written"][:16] != build.archive_written()[:16]:
        pytest.skip("grazing_cells.json was built from another snow archive")
    cells = [c for c in stored["cells"] if c["gridded"] and c["hemisphere"] == "N" and c["snow"]["status"] == "measured"
             and (c["targets"]["nobile-rim-2"]["long_snow_free_hours_winter"] or 0) >= 100][:6]
    assert cells
    snow_of = grazing.snow_of_cells(cells, np.load(grazing.SNOW_ARCHIVE))
    got = build.hours(cells, TARGETS, snow_of, {})
    differ = []
    for target in TARGETS:
        for k, cell in enumerate(cells):
            want = cell["targets"][target["id"]]
            for name, field in (("winter_snow_free", "long_snow_free_hours_winter"),
                                ("year_snow_free", "long_snow_free_hours"), ("year_flat", "long_flat_hours")):
                mine = float(got[target["id"]][name][k])
                if abs(mine - want[field]) > 0.06:
                    differ.append((cell["id"], target["id"], field, round(mine, 2), want[field]))
    skip_if_the_cells_file_is_older_than_the_sun_code(differ)
    assert differ == []


def test_the_build_checks_its_hours_against_the_cells_file_and_sees_a_figure_that_does_not_fit():
    stored = json.loads(Path("data/derived/grazing_cells.json").read_text())["cells"]
    archive = np.load(grazing.SNOW_ARCHIVE)
    good = build.check_against_cells_file(stored, TARGETS, archive, count=5)
    skip_if_the_cells_file_is_older_than_the_sun_code(not good["agrees"])
    assert good["cells"] == 5 and good["agrees"] is True and good["largest_difference_h"] <= build.CHECK_TOLERANCE_H
    best = max((c for c in stored if c["gridded"] and c["hemisphere"] == "N" and c["snow"]["status"] == "measured"),
               key=lambda c: c["targets"]["nobile-rim-2"]["long_snow_free_hours_winter"] or 0.0)
    wrong = json.loads(json.dumps(best))
    wrong["targets"]["malapert"]["long_snow_free_hours_winter"] += 5.0
    bad = build.check_against_cells_file([wrong if c["id"] == best["id"] else c for c in stored], TARGETS, archive, count=5)
    assert bad["agrees"] is False and bad["largest_difference_h"] == pytest.approx(5.0, abs=0.1)


def test_the_squares_for_a_horizon_are_those_with_the_most_winter_hours_of_any_target():
    cells = [square(f"60.0_{k}.0", 60.05, k + 0.1, 1.0, 0.05) for k in range(5)]
    per_target = {"a": {"winter_snow_free": np.array([10.0, np.nan, 30.0, 5.0, 0.0])},
                  "b": {"winter_snow_free": np.array([50.0, np.nan, 20.0, 5.0, 0.0])}}
    best = build.most_winter_hours(per_target)
    assert best[:1].tolist() == [50.0] and np.isnan(best[1]) and best[2] == 30.0
    assert [c["id"] for c in build.top_squares(cells, best, 2)] == ["60.0_0.0", "60.0_2.0"]
    assert [c["id"] for c in build.top_squares(cells, best, 10)] == ["60.0_0.0", "60.0_2.0", "60.0_3.0"]   # none without hours


def test_counts_by_region_leave_out_unknown_hours_and_keep_measured_squares_only():
    leads = [{"region": "Shetland", "snow": {"status": "measured"}, "winter_hours_snow_free": 120.0},
             {"region": "Shetland", "snow": {"status": "measured"}, "winter_hours_snow_free": 60.0},
             {"region": "Shetland", "snow": {"status": "doubtful"}, "winter_hours_snow_free": 300.0},
             {"region": "Iceland", "snow": {"status": "measured"}, "winter_hours_snow_free": 100.0},
             {"region": "Iceland", "snow": {"status": "measured"}, "winter_hours_snow_free": None}]
    assert build.counts_by_region(leads, "winter_hours_snow_free") == {
        "50": {"Iceland": 1, "Shetland": 2}, "100": {"Iceland": 1, "Shetland": 1}}
    assert build.counts_by_region(leads, "winter_hours_snow_free", status="doubtful") == {
        "50": {"Shetland": 1}, "100": {"Shetland": 1}}


def test_a_lead_record_keeps_unknown_as_null():
    cell = {**square("60.5_-1.6", 60.55, -1.5, 0.47, 0.0074), "bare_km2": 0.42}
    values = {"winter_flat": 313.4, "winter_snow_free": 268.4, "winter_open": np.nan, "year_flat": 313.4,
              "year_snow_free": 268.4, "year_open": np.nan, "south_share_winter": 0.99,
              "best_periods": [[33, 31.2]]}
    record = build.lead_record(cell, {"status": "doubtful", "land_pixels": 3, "block_pixels": 9}, None, values, 1.0)
    assert record["region"] == "Shetland" and record["winter_hours_after_terrain"] is None
    assert record["year_hours_after_terrain"] is None and record["horizon"] is None
    assert record["winter_hours_snow_free"] == 268.4 and record["at_main_floor"] is False
    assert record["best_ten_day_periods"] == [{"bin": 33, "starts": build.bin_start_label(33), "hours": 31.2}]
    assert record["bare_km2"] == 0.42 and record["bare_samples"] == 1


def test_the_rim_summary_counts_land_squares_and_those_with_bare_ground():
    north = [square("60.1_-1.2", 60.15, -1.1, 0.5, 0.0), square("60.5_-1.6", 60.55, -1.5, 0.5, 0.0074),
             square("59.2_-3.0", 59.25, -2.9, 0.6, 0.0), square("62.2_-6.6", 62.25, -6.5, 0.6, 0.045),
             square("62.0_-6.8", 62.05, -6.7, 0.6, 0.2), square("64.1_-22.0", 64.15, -21.9, 1.0, 0.05)]
    rim = build.rim_summary(north)
    assert set(rim) == set(build.RIM)
    assert rim["Orkney"] == {"land_squares": 1, "pass_the_screen": 0, "below_the_screen_with_a_bare_sample": 0,
                             "of_them_at_the_main_floor": 0, "their_bare_km2": 0.0}
    assert rim["Shetland"]["land_squares"] == 2 and rim["Shetland"]["below_the_screen_with_a_bare_sample"] == 1
    assert rim["Shetland"]["of_them_at_the_main_floor"] == 0
    assert rim["Shetland"]["their_bare_km2"] == round(build.bare_km2(north[1]), 2)
    assert rim["Faroe Islands"] == {"land_squares": 2, "pass_the_screen": 1, "below_the_screen_with_a_bare_sample": 1,
                                    "of_them_at_the_main_floor": 1, "their_bare_km2": round(build.bare_km2(north[3]), 2)}


def test_a_ten_day_period_is_named_by_its_first_day():
    assert build.bin_start_label(0) == sun.doy_to_label(1)
    assert build.bin_start_label(27) == sun.doy_to_label(271)   # the winter half starts on 28 September


# The file itself, once built.

@pytest.fixture(scope="module")
def written():
    if not OUT.exists():
        pytest.skip("data/derived/winter_leads.json has not been built")
    return json.loads(OUT.read_text())


def test_the_file_says_what_it_relaxes_and_what_it_did_not_compute(written):
    meta = written["meta"]
    assert meta["floor_bare_km2"] == build.FLOOR_KM2 and meta["screen_relaxed"]["min_bare_of_the_pipeline"] == 0.15
    assert meta["warnings"] and meta["computed"] and meta["not_computed"]
    assert set(written["targets"]) == {t["id"] for t in TARGETS}
    assert set(written["floors"]) == {"0.25", "1.0", "3.0"}


def test_every_listed_lead_has_fifty_winter_hours_and_null_where_terrain_was_not_computed(written):
    for target in written["targets"].values():
        for lead in target["leads"]:
            assert lead["winter_hours_snow_free"] >= build.LIST_MIN_H
            assert lead["bare"] < build.MIN_BARE and lead["bare_km2"] >= min(build.FLOORS_KM2)
            if lead["horizon"] is None or "skipped" in lead["horizon"]:
                assert lead["winter_hours_after_terrain"] is None
            else:
                assert 0.0 <= lead["winter_hours_after_terrain"] <= lead["winter_hours_snow_free"] + 0.05


def test_the_counts_by_region_are_the_counts_of_the_listed_leads(written):
    for target in written["targets"].values():
        main = [lead for lead in target["leads"] if lead["at_main_floor"]]
        assert target["counts_by_region"] == build.counts_by_region(main, "winter_hours_snow_free")
        assert target["counts_by_region_after_terrain"] == build.counts_by_region(main, "winter_hours_after_terrain")
        at_floor = written["floors"][str(build.FLOOR_KM2)]["targets"]
        tid = target["id"]
        assert at_floor[tid]["50"] == sum(target["counts_by_region"]["50"].values())
        assert at_floor[tid]["100"] == sum(target["counts_by_region"]["100"].values())


def test_the_file_was_checked_against_the_cells_file_when_it_was_built(written):
    check = written["meta"]["built_with"]["check_against_cells_file"]
    assert check["cells"] >= 50 and check["agrees"] is True and check["largest_difference_h"] <= build.CHECK_TOLERANCE_H


def test_fewer_leads_at_a_higher_floor(written):
    for target in TARGETS:
        counts = [written["floors"][floor]["targets"][target["id"]]["50"] for floor in ("0.25", "1.0", "3.0")]
        assert counts == sorted(counts, reverse=True)


def test_built_with_says_whether_the_sun_code_is_newer_than_the_cells_file(tmp_path, monkeypatch):
    cells_file = tmp_path / "grazing_cells.json"
    cells_file.write_text("{}")
    monkeypatch.setattr(build, "SCREENED", cells_file)
    monkeypatch.setattr(build, "SUN_CODE_READ", "2000-01-01T00:00:00")
    assert build.built_with()["same_code"] is True
    monkeypatch.setattr(build, "SUN_CODE_READ", "2999-01-01T00:00:00")
    stamp = build.built_with()
    assert stamp["same_code"] is False and stamp["grazing_cells_written"] == build.written_at(cells_file)


def test_the_screened_comparison_is_the_count_of_the_results_file(written):
    if written["meta"]["built_with"]["grazing_cells_written"] != build.written_at("data/derived/grazing_cells.json"):
        pytest.skip("grazing_cells.json was built again after winter_leads.json: run scripts/build_winter_leads.py again")
    stored = json.loads(Path("data/derived/grazing_cells.json").read_text())["cells"]
    for target in TARGETS:
        hours = [c["targets"][target["id"]]["long_snow_free_hours_winter"] for c in stored
                 if c["gridded"] and c["hemisphere"] == "N" and c["snow"]["status"] == "measured"]
        screened = written["targets"][target["id"]]["screened_counts_by_region"]
        for limit in ("50", "100"):
            assert sum(screened[limit].values()) == sum(h is not None and h >= int(limit) for h in hours)

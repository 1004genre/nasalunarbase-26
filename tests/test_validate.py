# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
import importlib
import json
import math

import numpy as np
import pytest

validate = importlib.import_module("scripts.validate")

NAN = float("nan")


def year(**bins):
    """36 ten-day values, zero except the bins given as b17=3.0."""
    values = np.zeros(36)
    for name, value in bins.items():
        values[int(name[1:])] = value
    return values


# ---- sums over the ten-day bins ----

def test_bin_sums_add_the_ten_day_bins_and_can_be_held_to_a_season():
    hours = year(b0=10.0, b17=30.0, b34=7.0)
    assert validate.bin_sum(hours) == pytest.approx(47.0)
    assert validate.bin_sum(hours, bins=[33, 34, 35, 0, 1, 2]) == pytest.approx(17.0)


def test_bin_sums_are_unknown_when_a_counted_bin_is_unknown_or_nothing_is_known():
    assert math.isnan(validate.bin_sum(year(b0=NAN, b17=30.0)))
    assert math.isnan(validate.bin_sum(np.full(36, NAN)))
    assert math.isnan(validate.bin_sum(np.full(36, NAN), bins=[17]))
    # an unknown bin outside the season takes nothing away
    assert validate.bin_sum(year(b5=NAN, b17=30.0), bins=[17, 18]) == pytest.approx(30.0)


def test_bin_sums_work_on_many_cells_at_once():
    hours = np.stack([year(b17=30.0), year(b17=10.0, b18=10.0)])
    assert validate.bin_sum(hours).tolist() == [30.0, 20.0]


# ---- the calendar ----

def test_calendar_sum_weights_long_window_hours_by_bare_ground():
    long_snow_free = np.stack([year(b17=30.0), year(b17=20.0, b0=40.0)])
    calendar, unknown = validate.calendar_sum(long_snow_free, np.array([2.0, 10.0]))
    assert calendar.shape == (36,)
    assert calendar[17] == pytest.approx(30.0 * 2.0 + 20.0 * 10.0)
    assert calendar[18] == 0.0
    assert calendar[0] == pytest.approx(400.0)
    assert unknown == 0


def test_calendar_sum_leaves_out_unknown_bins_and_counts_them():
    calendar, unknown = validate.calendar_sum(np.stack([year(b17=NAN), year(b17=20.0)]), np.array([2.0, 10.0]))
    assert calendar[17] == pytest.approx(200.0)
    assert unknown == 1


def test_calendar_sum_of_no_cells_is_a_year_of_zeros():
    calendar, unknown = validate.calendar_sum(np.zeros((0, 36)), np.zeros(0))
    assert calendar.tolist() == [0.0] * 36 and unknown == 0


# ---- counts ----

def test_threshold_counts_give_cells_and_bare_area_at_each_level():
    hours = [250.0, 120.0, 60.0, 10.0, None]
    bare_km2 = [10.0, 20.0, 30.0, 40.0, 50.0]
    counts = validate.threshold_counts(hours, bare_km2, (50, 100, 200))
    assert counts["50"] == {"cells": 3, "bare_km2": 60.0}
    assert counts["100"] == {"cells": 2, "bare_km2": 30.0}
    assert counts["200"] == {"cells": 1, "bare_km2": 10.0}
    assert counts["unknown_cells"] == 1 and counts["cells_counted"] == 4


def test_threshold_counts_include_the_level_itself():
    assert validate.threshold_counts([100.0], [5.0], (100,))["100"] == {"cells": 1, "bare_km2": 5.0}


def test_region_counts_are_sorted_with_the_biggest_first():
    cells = [{"region": "Greenland"}, {"region": "Iceland"}, {"region": "Greenland"}]
    assert list(validate.region_counts(cells).items()) == [("Greenland", 2), ("Iceland", 1)]


def test_old_usable_day_counts_skip_unknown_values_and_the_pixel_note():
    light_v1 = {"a": {"malapert": {"usable_days": 12.0}, "nobile": {"usable_days": 9.9}, "_snow_land_pixels": 9},
                "b": {"malapert": {"usable_days": None}, "nobile": {"usable_days": 10.0}, "_snow_land_pixels": 2},
                "c": {"malapert": {"usable_days": 30.0}, "nobile": {"usable_days": 0.0}, "_snow_land_pixels": 9}}
    assert validate.old_usable_counts(light_v1, ["malapert", "nobile"], 10.0) == {"malapert": 2, "nobile": 1}


# ---- hours by half-year for the named sites ----

def test_half_year_hours_split_the_year_and_keep_all_and_long_apart():
    hours = year(b0=10.0, b17=30.0, b18=5.0)
    long = year(b17=28.0, b18=5.0)          # the part of those hours inside long spells
    winter, summer = [27, 28, 29, 30, 31, 32, 33, 34, 35, 0, 1, 2, 3, 4, 5, 6, 7, 8], list(range(9, 27))
    out = validate.half_year_hours(hours, long, winter, summer)
    assert out["all"] == {"year": 45.0, "winter_half": 10.0, "summer_half": 35.0}
    assert out["long"] == {"year": 33.0, "winter_half": 0.0, "summer_half": 33.0}


def test_half_year_hours_are_none_where_unknown():
    out = validate.half_year_hours(np.full(36, NAN), np.full(36, NAN), [0], [17])
    assert out["all"] == {"year": None, "winter_half": None, "summer_half": None}
    assert out["long"]["year"] is None


# ---- stability ----

def record(cid, lat, lon, hours, bare=0.6, terrain=0.5, pixels=9, flat_hours=None, horizon=True):
    return {"id": cid, "lat": lat, "lon": lon, "hemisphere": "N", "ranking": "north", "gridded": True, "bare": bare,
            "snow": {"status": "measured", "source": "3x3", "land_pixels": pixels, "stuck_winters": 0},
            "horizon": {"north_deg": 1.0, "south_deg": 1.0} if horizon else None,
            "targets": {"t": {"long_open_hours": hours, "long_snow_free_hours": flat_hours or hours,
                              "terrain": terrain, "rock": 0.0}}}


RECORDS = [record("a", 64.0, -20.0, 180.0, bare=0.7),
           record("b", 70.0, 25.0, 150.0, bare=0.3, pixels=3),
           record("c", 75.0, 60.0, 60.0, bare=0.8, flat_hours=400.0),
           record("d", 80.0, 20.0, None, horizon=False)]


def ids(sites):
    return [s["id"] for s in sites]


def test_variant_sites_rank_by_the_goal_and_leave_out_unknown_light():
    assert ids(validate.variant_sites(RECORDS, "t", "lighting", "north")) == ["a", "c", "b"]


def test_variant_sites_follow_each_screen():
    assert ids(validate.variant_sites(RECORDS, "t", "lighting", "north", min_bare=0.35)) == ["a", "c"]
    assert ids(validate.variant_sites(RECORDS, "t", "lighting", "north", min_snow_pixels=4)) == ["a", "c"]
    assert ids(validate.variant_sites(RECORDS, "t", "lighting", "north", basis="flat")) == ["c", "a", "b"]
    assert ids(validate.variant_sites(RECORDS, "t", "lighting", "north", top=1)) == ["a"]


def test_variant_sites_can_take_other_hours_for_the_stretch_check():
    other = {"a": {"t": 10.0}, "b": {"t": 150.0}, "c": {"t": None}, "d": {"t": None}}
    assert ids(validate.variant_sites(RECORDS, "t", "lighting", "north", hours=other)) == ["b", "a"]


def test_a_higher_cap_changes_the_order_only_where_cells_were_capped():
    capped = [record("a", 64.0, -20.0, 400.0, bare=0.5), record("b", 70.0, 25.0, 200.0, bare=0.6)]
    assert ids(validate.variant_sites(capped, "t", "lighting", "north")) == ["b", "a"]
    assert ids(validate.variant_sites(capped, "t", "lighting", "north", full_hours=400.0)) == ["a", "b"]


def test_stability_reports_survivors_out_of_the_baseline():
    variants = {"bare screen 0.35": {"min_bare": 0.35}, "snow pixels >= 4": {"min_snow_pixels": 4},
                "flat horizon": {"basis": "flat"}}
    out = validate.stability(RECORDS, "t", "lighting", "north", variants)
    assert out == {"baseline_sites": 3, "bare screen 0.35": 2, "snow pixels >= 4": 2, "flat horizon": 3}


def test_top_cells_take_the_best_ranked_cells_without_clustering():
    near = [record("a", 64.0, -20.0, 180.0), record("b", 64.05, -20.0, 170.0), record("c", 64.1, -20.0, 0.0)]
    top = validate.top_cells(near, "t", "lighting", "north", count=100)
    assert ids(top) == ["a", "b"]     # neighbours both count; a zero score is not a top cell


# ---- edges the first tests left open ----

def test_a_skipped_horizon_is_not_a_horizon():
    assert validate.has_horizon({"horizon": {"north_deg": 1.0, "south_deg": 2.0}}) is True
    assert validate.has_horizon({"horizon": None}) is False
    assert validate.has_horizon({"horizon": {"skipped": "no land pixels"}}) is False


def test_the_stability_variants_are_the_ones_the_job_names():
    by_stretch = {1.0: "one", 2.0: "two", 3.0: "three"}
    variants = validate.stability_variants(by_stretch, have_horizons=True)
    assert [variants[f"bare screen {v}"] for v in ("0.15", "0.25", "0.35")] == [
        {"min_bare": 0.15}, {"min_bare": 0.25}, {"min_bare": 0.35}]
    assert [variants[f"full marks at {v} h"] for v in (100, 200, 400)] == [
        {"full_hours": 100.0}, {"full_hours": 200.0}, {"full_hours": 400.0}]
    assert [variants[f"snow land pixels >= {v}"] for v in (1, 4, 7)] == [
        {"min_snow_pixels": 1}, {"min_snow_pixels": 4}, {"min_snow_pixels": 7}]
    assert variants["flat horizon instead of real"] == {"basis": "flat"}
    assert [variants[f"stretch minimum {v} h"] for v in (1, 2, 3)] == [{"hours": "one"}, {"hours": "two"}, {"hours": "three"}]
    assert "flat horizon instead of real" not in validate.stability_variants(by_stretch, have_horizons=False)


META = {"targets": [{"id": "t"}], "stretch_min_h": 2.0, "summer_bins_south": [33, 34, 35, 0, 1, 2, 3, 4, 5]}


def bins_archive():
    """Two cells: north (row 0) and south (row 1), one target."""
    def rows(north, south):
        return np.stack([north, south])[:, None, :]
    return {"flat": rows(year(b17=50.0, b18=40.0, b30=30.0), year(b34=80.0, b0=60.0, b12=90.0)),
            "snow_free": rows(year(b17=45.0, b18=35.0, b30=25.0), np.full(36, NAN)),
            "open": rows(year(b17=40.0, b18=30.0, b30=20.0), year(b34=70.0, b0=50.0, b12=85.0)),
            "stretch": rows(year(b17=5.0, b18=2.0, b30=1.5), year(b34=6.0, b0=2.5, b12=5.0))}


BIN_RECORDS = [{"id": "n", "hemisphere": "N"}, {"id": "s", "hemisphere": "S"}]
BIN_ROWS = {"n": 0, "s": 1}


def long_arrays(min_h: float = 2.0) -> dict:
    """Long-window hours per bin for the two cells: here a bin counts whole when its stretch reaches min_h."""
    archive = bins_archive()
    return {f"long_{kind}": np.where(np.isnan(archive[kind]), NAN, np.where(archive["stretch"] >= min_h, archive[kind], 0.0))
            for kind in ("flat", "snow_free", "open")}


def test_stretch_hours_read_each_cells_light_hours_from_a_set_of_long_window_arrays():
    def hours(min_h, basis):
        out = validate.stretch_hours(BIN_RECORDS, long_arrays(min_h), BIN_ROWS, META, basis)
        return out["n"]["t"], out["s"]["t"]
    assert hours(2.0, "open") == (70.0, 120.0)      # north: bins 17 and 18; south: the rock season only, not May
    assert hours(1.0, "open") == (90.0, 120.0)
    assert hours(3.0, "open") == (40.0, 70.0)


def test_stretch_hours_over_a_flat_horizon_keep_the_snow_in_the_north():
    out = validate.stretch_hours(BIN_RECORDS, long_arrays(), BIN_ROWS, META, "flat")
    assert out["n"]["t"] == 80.0       # snow-free hours, not the 90 h of the bare flat-horizon Sun
    assert out["s"]["t"] == 140.0      # the south has no snow figure: flat hours of the rock season


def test_stretch_hours_stay_unknown_without_a_horizon():
    arrays = long_arrays()
    arrays["long_open"][0] = NAN
    assert validate.stretch_hours(BIN_RECORDS, arrays, BIN_ROWS, META, "open")["n"]["t"] is None


def test_the_stored_minimum_uses_the_stored_arrays_and_another_minimum_asks_grazing(monkeypatch):
    calls = []

    def fake(cells, min_stretch_h, targets=None, inputs=None):
        calls.append(([c["id"] for c in cells], min_stretch_h, targets, inputs))
        return {"ids": [c["id"] for c in cells], "long_flat": "F", "long_snow_free": "S", "long_open": "O", "more": 1}

    monkeypatch.setattr(validate.grazing, "long_window_hours_by_bin", fake)
    archive = {"long_flat": 1, "long_snow_free": 2, "long_open": 3, "stretch": 4}
    cells = [{"id": "n"}, {"id": "s"}]
    assert validate.long_arrays_at(cells, 2.0, archive, META, "INPUTS") == {"long_flat": 1, "long_snow_free": 2, "long_open": 3}
    assert calls == []
    assert validate.long_arrays_at(cells, 3.0, archive, META, "INPUTS") == {"long_flat": "F", "long_snow_free": "S", "long_open": "O"}
    assert calls == [(["n", "s"], 3.0, META["targets"], "INPUTS")]


def test_another_minimum_must_come_back_in_the_order_of_the_cells(monkeypatch):
    monkeypatch.setattr(validate.grazing, "long_window_hours_by_bin",
                        lambda cells, min_stretch_h, targets=None, inputs=None: {"ids": ["s", "n"]})
    with pytest.raises(ValueError):
        validate.long_arrays_at([{"id": "n"}, {"id": "s"}], 1.0, {}, META, None)


# ---- what the terrain leaves, over a group of cells ----

def terrain_cell(opened, base, horizon=True, south=False):
    names = ("long_summer_rock_open_hours", "long_summer_rock_hours") if south else ("long_open_hours", "long_snow_free_hours")
    return {"hemisphere": "S" if south else "N", "horizon": {"north_deg": 1.0, "south_deg": 3.0} if horizon else None,
            "targets": {"t": dict(zip(names, (opened, base)))}}


def test_the_share_left_by_terrain_is_open_over_flat_among_cells_with_a_horizon_and_hours():
    cells = [terrain_cell(50.0, 100.0), terrain_cell(0.0, 40.0), terrain_cell(None, 100.0, horizon=False),
             terrain_cell(0.0, 0.0), terrain_cell(None, None)]
    assert validate.share_left(cells, "t") == [0.5, 0.0]       # no horizon, no hours and unknown hours are left out
    assert validate.share_left([terrain_cell(30.0, 120.0, south=True)], "t") == [0.25]


def test_a_spread_gives_the_count_and_percentiles_and_none_without_cells():
    assert validate.spread([0.0, 0.5, 1.0]) == {"cells": 3, "p10": 0.1, "p25": 0.25, "median": 0.5, "p75": 0.75, "p90": 0.9}
    assert validate.spread([]) == {"cells": 0, "p10": None, "p25": None, "median": None, "p75": None, "p90": None}


def test_horizon_medians_use_only_cells_with_a_horizon():
    cells = [terrain_cell(1.0, 1.0), terrain_cell(1.0, 1.0), terrain_cell(None, 1.0, horizon=False)]
    cells[1]["horizon"] = {"north_deg": 2.0, "south_deg": 5.0}
    assert validate.horizon_medians(cells) == {"cells": 2, "north_deg": 1.5, "south_deg": 4.0}
    assert validate.horizon_medians([]) == {"cells": 0, "north_deg": None, "south_deg": None}


def test_a_missing_horizon_says_why_in_few_words():
    assert validate.no_horizon_reason({"horizon": None}) == "no horizon record"
    assert validate.no_horizon_reason({"horizon": {"skipped": "window at 66, -179.9 crosses the antimeridian"}}) == \
        "window across the antimeridian"
    held = {"horizon": {"skipped": "tile not fetched: https://example.org/a.tif (downloads were off in this run)"}}
    assert validate.no_horizon_reason(held) == "elevation tile not fetched"
    assert validate.no_horizon_reason({"horizon": {"skipped": "no land pixels"}}) == "no land pixels"


def test_the_snow_odds_shown_for_a_cell_come_from_the_layer_the_cell_uses():
    both = ["probabilities", "probabilities_as_mapped"]
    assert validate.odds_layer({"snow": {"odds_used": "as mapped"}}, both) == "probabilities_as_mapped"
    assert validate.odds_layer({"snow": {"odds_used": "stale-flag rule"}}, both) == "probabilities"
    assert validate.odds_layer({"snow": {"odds_used": "as mapped"}}, ["probabilities"]) == "probabilities"
    assert validate.odds_layer({"snow": {}}, both) == "probabilities"


def test_the_recompute_check_reports_what_differs():
    def rec(cid, stored):
        return {"id": cid, "hemisphere": "N", "targets": {"t": {"long_open_hours": stored}}}
    records = [rec("a", 100.0), rec("b", None), rec("c", 50.0), rec("d", None)]
    recomputed = {"a": {"t": 100.4}, "b": {"t": None}, "c": {"t": None}, "d": {"t": 7.0}}
    assert validate.recompute_check(records, recomputed, "open") == {"largest_difference_h": 0.4, "known_in_one_only": 2}


# ---- the baseline of the stability check is the published ranking ----

score_tests = importlib.import_module("test_score")
score_cells = importlib.import_module("scripts.score_cells")


def awkward_records():
    """Scored records whose scores do not land on round numbers, three of them tied at three decimals."""
    def build(cid, lat, bare, hours, overlap):
        grazing = score_tests.grazing_cell(id=cid, lat=lat, lon=20.0 + lat, bare=bare,
                                           hours={"long_open_hours": hours, "long_snow_free_hours": hours + 31.7})
        land = {"median_slope_deg": 6.0, "p90_slope_deg": 20.0, "relief_m": 700.0, "valid_share": 1.0,
                "overlap": {"malapert": overlap}}
        bodies = [{"name": "Test body", "lat": lat, "lon": 20.0 + lat, "radius_km": 5, "an_low": 71.3, "an_high": 84.9}]
        return score_cells.scored_record(grazing, land, [score_tests.TARGET], {"malapert": 0.8089}, bodies=bodies,
                                         known_sites=[], south_sites=[])
    return [build("p", 61.0, 0.9996, 240.0, 0.0037), build("q", 63.0, 1.0, 250.0, 0.0041),
            build("r", 65.0, 0.99951, 201.0, 0.4567), build("s", 67.0, 0.6175298804780877, 33.3, 0.7001)]


def test_a_variant_with_nothing_changed_gives_the_published_score_exactly():
    for r in awkward_records():
        t = r["targets"]["malapert"]
        for goal in validate.score.GOALS:
            assert validate.variant_goal(r, "malapert", goal, 200.0, "open", None) == t["goals"][goal], (r["id"], goal)
            assert validate.variant_goal(r, "malapert", goal, 200.0, "flat", None) == t["goals_flat"][goal], (r["id"], goal)


def test_the_stability_baseline_is_the_published_top_ten():
    records = awkward_records()       # p, q and r all publish 1.000 for lighting; the one with more hours comes first
    published = validate.published_sites(records, "malapert", "lighting", "north")
    assert ids(published) == ["q", "p", "r", "s"]
    assert ids(published) == ids(score_cells.ranked_sites(records, "malapert", "lighting", "north"))
    assert ids(validate.variant_sites(records, "malapert", "lighting", "north")) == ids(published)
    assert validate.baseline_differences(records, ["malapert"], flat=False) == []
    assert ids(validate.published_sites(records, "malapert", "lighting", "south")) == []


def test_a_baseline_that_is_not_the_published_ranking_is_reported():
    records = awkward_records()
    records[0]["targets"]["malapert"]["goals"]["lighting"] = 0.5      # as if ranking.txt had been built another way
    assert validate.baseline_differences(records, ["malapert"], flat=False) == ["north malapert lighting"]


# ---- both scripts end to end on the small made-up project of test_score.py ----

@pytest.fixture
def tiny(tmp_path, monkeypatch, capsys):
    cells = score_tests.tiny_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(validate.snow, "cell_probabilities_filled",
                        lambda crop, row0, col0, lat, lon: (np.arange(36) / 100.0, "3x3"))
    # the 1 h and 3 h variants ask grazing.py; the made-up project has no real snow archive or horizon file
    monkeypatch.setattr(validate.grazing, "cell_inputs", lambda cells: "inputs of the made-up project")
    monkeypatch.setattr(validate.grazing, "long_window_hours_by_bin",
                        score_tests.fake_long_window_hours_by_bin(tmp_path))
    score_cells.main()
    validate.main()
    capsys.readouterr()
    return cells, json.loads((tmp_path / "data/derived/validation.json").read_text())


def test_validate_counts_only_measured_gridded_northern_cells(tiny):
    _, result = tiny
    big = result["big_picture_north"]
    assert big["measured_cells"] == 5            # a, b, no_horizon, skipped, haughton: no doubtful, no-data or named-only cell
    assert big["measured_bare_km2"] == pytest.approx(90.0 + 50.0 + 90.0 + 90.0 + 30.0)
    assert big["cells_with_a_horizon"] == 3      # a skipped window is not a horizon
    counts = big["targets"]["malapert"]["long_snow_free_hours"]
    assert counts["year"]["50"] == {"cells": 5, "bare_km2": 350.0}
    assert counts["year"]["100"] == {"cells": 3, "bare_km2": 230.0}
    assert counts["year"]["200"] == {"cells": 1, "bare_km2": 90.0}
    assert counts["summer_half"]["100"] == {"cells": 3, "bare_km2": 230.0}
    assert counts["winter_half"]["50"] == {"cells": 0, "bare_km2": 0}
    assert counts["year"]["unknown_cells"] == 0 and counts["year"]["cells_counted"] == 5


def test_validate_counts_open_hours_only_among_cells_with_a_horizon(tiny):
    _, result = tiny
    counts = result["big_picture_north"]["targets"]["malapert"]["long_open_hours_among_cells_with_a_horizon"]
    assert counts["year"]["cells_counted"] == 3 and counts["year"]["unknown_cells"] == 0
    assert counts["year"]["50"]["cells"] == 3
    assert counts["year"]["100"] == {"cells": 2, "bare_km2": 140.0}
    assert counts["summer_half"]["100"]["cells"] == 2 and counts["winter_half"]["50"]["cells"] == 0


def test_validate_puts_the_hours_on_the_calendar(tiny):
    _, result = tiny
    calendar = result["big_picture_north"]["targets"]["malapert"]["calendar_hours_times_bare_km2"]
    assert len(calendar) == 36
    assert calendar[17] == pytest.approx(110.0 * 90.0 + 250.0 * 90.0 + 80.0 * 90.0)
    assert calendar[18] == pytest.approx(60.0 * 90.0 + 120.0 * 50.0)     # a stretch of exactly 2 h is a long window
    assert calendar[19] == pytest.approx(17.5 * 30.0, abs=0.1)
    assert calendar[30] == 0.0                                            # 1.5 h is too short a stretch
    assert result["big_picture_north"]["targets"]["malapert"]["calendar_unknown_cell_bins"] == 0


def test_validate_sets_the_old_measure_beside_the_new(tiny):
    _, result = tiny
    old_new = result["old_against_new"]["targets"]["malapert"]
    assert old_new["old"] == 2                   # a and the doubtful cell in the first method's file
    assert old_new["new_measured"] == 1 and old_new["new_measured_regions"] == {"Norway, Sweden or Finland": 1}
    assert old_new["new_doubtful"] == 1          # listed apart; the named-only cells are in neither


def test_validate_breaks_the_regions_down(tiny):
    _, result = tiny
    regions = result["regions"]["malapert"]
    assert regions["measured_cells_100_long_snow_free_hours_winter_half"] == {}
    assert regions["measured_cells_100_long_snow_free_hours_summer_half"] == {
        "Norway, Sweden or Finland": 1, "Arctic Canada": 1, "Greenland": 1}
    assert regions["top_cells_lighting_real_horizon"] == {
        "cells": 3, "regions": {"Arctic Canada": 2, "Norway, Sweden or Finland": 1}}
    # the Greenland cell has 250 long-window snow-free hours over a flat horizon and no horizon of its own
    assert regions["measured_cells_with_full_flat_light_and_enough_bare"] == {"cells": 1, "of_them_with_a_horizon": 0}
    assert regions["top_cells_lighting_flat_horizon_all_measured"]["of_them_with_a_horizon"] == 3


def test_validate_stability_follows_each_change(tiny):
    _, result = tiny
    north = result["stability"]["north"]["malapert"]["lighting"]
    assert north["baseline_sites"] == 3
    assert (north["bare screen 0.15"], north["bare screen 0.25"], north["bare screen 0.35"]) == (3, 3, 2)
    assert (north["full marks at 100 h"], north["full marks at 200 h"], north["full marks at 400 h"]) == (3, 3, 3)
    assert (north["snow land pixels >= 1"], north["snow land pixels >= 4"], north["snow land pixels >= 7"]) == (3, 2, 2)
    assert north["flat horizon instead of real"] == 3
    # at 3 h cell b loses its only long window (2 h), so its score is zero and it is no site
    assert (north["stretch minimum 1 h"], north["stretch minimum 2 h"], north["stretch minimum 3 h"]) == (3, 3, 2)
    assert result["stability"]["north"]["malapert"]["shadows"]["baseline_sites"] == 1     # only cell a has terrain
    south = result["stability"]["south"]["malapert"]["lighting"]
    assert south["baseline_sites"] == 1 and south["stretch minimum 3 h"] == 1
    assert not any(label.startswith("snow") for label in south)
    assert result["recompute_check"] == {"largest_difference_h": 0.0, "known_in_one_only": 0}
    passed = {check["check"]: check["passed"] for check in result["checks"]}
    assert passed["the stability baseline is the top 10 that ranking.txt prints"] is True
    assert passed["long-window hours recomputed from the ten-day bins match the cells file within 0.1 h"] is True


def test_validate_reports_haughton_in_july(tiny):
    _, result = tiny
    h = result["haughton_july"]
    assert h["cell"] == "75.3_-90.0" and h["bins"] == [18, 19, 20]
    assert h["dates"] == ["30 Jun-9 Jul", "10 Jul-19 Jul", "20 Jul-29 Jul"]
    assert h["snow_free_odds"] == [0.18, 0.19, 0.2]
    t = h["targets"]["malapert"]
    assert t["flat_hours"] == [0.0, 19.8, 45.8] and t["snow_free_hours"] == [0.0, 17.5, 45.8]
    assert t["open_hours"] == [0.0, 16.1, 41.0] and t["open_hours_july"] == 57.1
    assert t["median_longest_stretch_h"] == [2.0, 2.3, 4.7]
    assert t["long_flat_hours"] == [0.0, 19.8, 45.8] and t["long_open_hours"] == [0.0, 16.1, 41.0]
    assert t["long_open_hours_july"] == 57.1
    assert h["snow_odds_layer"] == "probabilities"


def test_validate_reports_named_sites_on_their_own_with_local_seasons(tiny):
    _, result = tiny
    sites = {s["name"]: s for s in result["named_sites"]["sites"]}
    oasis = sites["Test oasis"]
    assert oasis["winter_snow_evidence"] == "no evidence" and oasis["snow"]["status"] == "unmeasured"
    hours = oasis["targets"]["malapert"]
    assert hours["flat"]["long"] == {"year": 230.0, "winter_half": 90.0, "summer_half": 140.0}   # December is summer there
    assert hours["open"]["long"]["summer_half"] == 120.0
    assert hours["snow_free"]["long"]["year"] is None and hours["snow_free"]["all"]["year"] is None
    assert hours["terrain"] == pytest.approx(0.5) and hours["terrain_overlap"] == pytest.approx(0.4)
    jan_mayen = sites["Jan Mayen, Norway"]
    assert jan_mayen["in_grazing_cells"] is True and jan_mayen["gridded"] is False
    assert jan_mayen["targets"]["malapert"]["open"]["long"]["year"] == 300.0
    assert sites["Reykjanes, Iceland"]["in_grazing_cells"] is False       # not in the small project
    assert "winter_snow_evidence" not in sites["Haughton crater, Devon Island, Canada"]


def test_top_cells_are_cut_on_the_exact_score_not_on_the_three_published_decimals():
    # Both publish 0.794; the cut of a top list must still take the better one, whatever its id.
    near = [record("a", 64.0, -20.0, 180.0, bare=0.6999), record("z", 70.0, 25.0, 180.0, bare=0.7)]
    assert validate.variant_goal(near[0], "t", "lighting", 200.0, "open", None) == \
        validate.variant_goal(near[1], "t", "lighting", 200.0, "open", None) == 0.794
    assert ids(validate.top_cells(near, "t", "lighting", "north", count=1)) == ["z"]


# --- added in the final step ---

def test_a_variant_orders_equal_scores_by_the_hours_it_uses():
    records = awkward_records()       # p 240 h, q 250 h, r 201 h: all 1.000 for lighting
    other = {"p": {"malapert": 400.0}, "q": {"malapert": 300.0}, "r": {"malapert": 500.0}, "s": {"malapert": 33.3}}
    assert ids(validate.variant_sites(records, "malapert", "lighting", "north", hours=other)) == ["r", "p", "q", "s"]
    assert ids(validate.variant_sites(records, "malapert", "lighting", "north", basis="flat")) == ["q", "p", "r", "s"]


def test_old_against_new_says_how_many_measured_cells_have_unknown_usable_days():
    def cell(days):
        return {"snow": {"status": "measured"}, "region": "X", "targets": {"t": {"usable_days": days}}}
    out = validate.old_against_new({}, [cell(12.0), cell(None), cell(3.0)], {"targets": [{"id": "t"}]})
    assert out["targets"]["t"]["new_measured"] == 1 and out["targets"]["t"]["new_measured_unknown"] == 1


# --- version 3: the census, the clear-sky row, the terrain share of all cells ---

def test_validate_says_how_many_measured_cells_have_no_horizon_and_why(tiny):
    _, result = tiny
    big = result["big_picture_north"]
    assert big["cells_with_a_horizon"] == 3
    assert big["cells_without_a_horizon"] == {
        "cells": 2, "why": {"no horizon record": 1, "window across the antimeridian": 1}}


def test_validate_counts_clear_sky_hours_among_cells_with_a_horizon(tiny):
    _, result = tiny
    counts = result["big_picture_north"]["targets"]["malapert"]["long_open_hours_clear_among_cells_with_a_horizon"]
    # a: 65.0 clear-sky hours; haughton: 63.1 open hours under a half-clear sky; b has no cloud figure
    assert counts["year"]["cells_counted"] == 2 and counts["year"]["unknown_cells"] == 1
    assert counts["year"]["50"] == {"cells": 1, "bare_km2": 90.0}
    assert counts["summer_half"]["50"]["cells"] == 1 and counts["winter_half"]["50"]["cells"] == 0


def test_validate_puts_open_and_clear_sky_hours_on_the_calendar(tiny):
    _, result = tiny
    target = result["big_picture_north"]["targets"]["malapert"]
    opened, clear = target["calendar_open_hours_times_bare_km2"], target["calendar_clear_hours_times_bare_km2"]
    assert opened[17] == pytest.approx(100.0 * 90.0) and opened[18] == pytest.approx(50.0 * 90.0 + 100.0 * 50.0)
    assert clear[17] == pytest.approx(25.0 * 90.0)
    assert clear[18] == pytest.approx(40.0 * 90.0)                  # cell b has hours there and no cloud figure: left out
    assert target["calendar_clear_unknown_cell_bins"] == 1
    assert target["calendar_open_unknown_cell_bins"] == 0


def test_validate_sets_the_terrain_share_of_all_cells_beside_the_blind_sample(tiny):
    _, result = tiny
    north, south = result["terrain_share_left"]["north"], result["terrain_share_left"]["south"]
    assert north["blind_sample"]["malapert"]["cells"] == 2          # a and haughton; cell b is not in the sample
    assert north["all_measured"]["malapert"]["cells"] == 3          # the two measured cells without a horizon cannot count
    assert north["all_measured"]["malapert"]["median"] == pytest.approx(150.0 / 170.0, abs=0.001)
    assert north["blind_sample"]["horizon"] == {"cells": 2, "north_deg": 1.0, "south_deg": 2.0}
    assert north["all_measured"]["cells_in_group"] == 5 and north["blind_sample"]["cells_in_group"] == 4
    assert south["all"]["malapert"] == south["blind_sample"]["malapert"]
    assert south["all"]["malapert"]["cells"] == 1 and south["all"]["malapert"]["median"] == pytest.approx(120.0 / 140.0, abs=0.001)


def test_validate_reports_clear_sky_hours_of_the_named_sites(tiny):
    _, result = tiny
    sites = {s["name"]: s for s in result["named_sites"]["sites"]}
    assert sites["Test oasis"]["targets"]["malapert"]["long_summer_rock_open_hours_clear"] == 53.0
    haughton = sites["Haughton crater, Devon Island, Canada"]["targets"]["malapert"]
    assert haughton["long_open_hours_clear"] == pytest.approx(63.1 * 0.5, abs=0.06)     # stored to one decimal
    assert haughton["long_open_hours_clear_summer"] == haughton["long_open_hours_clear"]


def test_validate_says_what_the_stability_check_draws_on(tiny):
    _, result = tiny
    assert result["meta"]["long_rule"] is None                        # the made-up project does not name its rule
    assert result["meta"]["stability_draws_on_records"] == result["meta"]["scored_records"] == 11
    assert result["meta"]["stretch_variants_from"] == "grazing.long_window_hours_by_bin"


# --- version 3: the station script's headline counts follow the per-day long hours (decision 19) ---

snow_many = importlib.import_module("scripts.validate_snow_many")


def test_the_station_script_reads_the_per_day_long_hours_when_the_archive_has_them():
    bins = {"flat": np.full((2, 1, 36), 4.0), "stretch": np.full((2, 1, 36), 3.0), "long_flat": np.full((2, 1, 36), 0.5)}
    bins["long_flat"][1] = 0.25
    out = snow_many.long_flat_by_bin(bins, np.array([1, 0]), 2.0)
    assert out.shape == (2, 1, 36) and (out[0] == 0.25).all() and (out[1] == 0.5).all()


def test_the_station_script_falls_back_to_whole_bins_for_a_version_2_archive():
    bins = {"flat": np.full((2, 1, 36), 4.0), "stretch": np.full((2, 1, 36), 3.0)}
    bins["stretch"][0, 0, :18] = 1.0
    out = snow_many.long_flat_by_bin(bins, np.array([1, 0]), 2.0)
    assert (out[0] == 4.0).all() and (out[1, 0, :18] == 0.0).all() and (out[1, 0, 18:] == 4.0).all()


def test_the_station_script_compares_its_as_is_hours_with_the_figure_under_the_stale_flag_rule():
    assert snow_many.stored_with_rule({"long_snow_free_hours": 23.0, "long_snow_free_hours_with_rule": 0.0}) == 0.0
    assert snow_many.stored_with_rule({"long_snow_free_hours": 23.0}) == 23.0        # a version 2 record
    assert math.isnan(snow_many.stored_with_rule({"long_snow_free_hours": None, "long_snow_free_hours_with_rule": None}))


# ---- added by the count check of version 3 (breakages that no test caught)

def test_the_old_bar_of_ten_usable_days_counts_a_cell_with_exactly_ten():
    def cell(days, status="measured"):
        return {"snow": {"status": status}, "region": "X", "targets": {"t": {"usable_days": days}}}
    out = validate.old_against_new({}, [cell(10.0), cell(9.9), cell(10.0, "doubtful")], {"targets": [{"id": "t"}]})
    assert out["targets"]["t"]["new_measured"] == 1 and out["targets"]["t"]["new_doubtful"] == 1


def test_the_snow_pixel_screen_keeps_a_cell_with_exactly_that_many_land_pixels():
    records = [record("a", 64.0, -20.0, 100.0, pixels=4), record("b", 70.0, 25.0, 100.0, pixels=3)]
    assert [r["id"] for r in validate.eligible(records, "north", 0.25, 4, True)] == ["a"]

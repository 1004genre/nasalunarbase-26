# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
import importlib
import json

import numpy as np
import pytest

from twinfinder import sun

extras = importlib.import_module("scripts.build_validation_extras")

TARGETS = [{"id": "low", "name": "Low", "limit_deg": 2.08, "elev_bins": [0, 1, 2, 3]},
           {"id": "high", "name": "High", "limit_deg": 7.59, "elev_bins": [0, 1, 2, 3, 4, 5, 6, 7, 8]}]


# ---- Sun geometry straight from twinfinder.sun ---------------------------------------------------

def flat_track(minutes_in_band: int, elevation: float = 1.0) -> np.ndarray:
    """A made-up year at a 1-minute step: the Sun sits at one elevation for so many minutes of day 200, else below."""
    elev = np.full((365, 1441), -10.0)
    elev[199, 600:600 + minutes_in_band + 1] = elevation
    return elev


def test_a_ninety_minute_spell_counts_under_a_one_hour_rule_and_not_under_a_two_hour_rule():
    elev = flat_track(90)
    one = extras.spell_hours_by_bin(elev, 2.08, 1.0, 1)
    two = extras.spell_hours_by_bin(elev, 2.08, 2.0, 1)
    assert one.shape == (36,)
    assert one.sum() == pytest.approx(1.5, abs=0.04)   # the two edge steps add a sliver each
    assert one[sun.bin_index(200)] == pytest.approx(one.sum())
    assert two.sum() == 0.0


def test_a_spell_above_the_ceiling_does_not_count_until_the_ceiling_is_raised():
    elev = flat_track(180, elevation=2.3)
    assert extras.spell_hours_by_bin(elev, 2.08, 2.0, 1).sum() == pytest.approx(0.0, abs=0.05)
    assert extras.spell_hours_by_bin(elev, 2.58, 2.0, 1).sum() == pytest.approx(3.0, abs=0.05)


def test_spell_hours_agree_with_the_tables_of_the_sun_module():
    # One calendar on each side: elevation_edges gives the single calendar, so the tables are asked for one too.
    lat, step = 70.05, 5
    elev = extras.elevation_edges(lat, step, refraction=True)
    assert elev.shape == (365, 289)
    for limit, bins in ((2.08, 4), (7.59, 9)):
        mine = extras.spell_hours_by_bin(elev, limit, 2.0, step)
        theirs = sun.long_band_minutes_table([lat], [limit], 2.0, step, year_phases=1)[0, 0][:, :, :bins].sum(axis=(1, 2)) / 60.0
        assert np.allclose(mine, theirs, atol=0.02)
        every = extras.spell_hours_by_bin(elev, limit, 0.0, step)
        table = sun.band_minutes_table([lat], step, year_phases=1)[0][:, :, :bins].sum(axis=(1, 2)) / 60.0
        assert np.allclose(every, table, atol=0.02)
        assert (mine <= every + 1e-6).all()


def test_elevation_edges_of_a_moved_calendar_agree_with_the_tables_of_that_calendar():
    lat, step, offset = 70.05, 5, 0.3125
    elev = extras.elevation_edges(lat, step, refraction=True, day_offset=offset)
    mine = extras.spell_hours_by_bin(elev, 7.59, 2.0, step)
    old = sun.DAY_ZERO_FROM_J2000
    try:
        sun.DAY_ZERO_FROM_J2000 = old + offset
        theirs = sun.long_band_minutes_table([lat], [7.59], 2.0, step, year_phases=1)[0, 0].sum(axis=(1, 2)) / 60.0
    finally:
        sun.DAY_ZERO_FROM_J2000 = old
    assert np.allclose(mine, theirs, atol=0.02)


def test_the_sensitivity_count_averages_the_calendars_the_cells_file_was_made_with():
    # Like with like: the Sun-module baseline is set beside the cells file's long_flat hours (checks.
    # sun_module_against_file_max_difference_h), which are the mean over the file's meta.year_phases calendars.
    lat, step, summer = 70.05, 5, list(range(9, 27))
    found = {}
    for phases in (1, 2):
        found[phases] = extras.sensitivity_summer_hours(lat, [2.08, 7.59], summer, step, year_phases=phases)
        for j, (limit, bins) in enumerate(((2.08, 4), (7.59, 9))):
            table = sun.long_band_minutes_table([lat], [limit], 2.0, step, year_phases=phases)[0, 0]
            assert found[phases]["baseline"][j] == pytest.approx(float(table[summer][:, :, :bins].sum()) / 60.0, abs=0.02)
    assert abs(found[1]["baseline"][0] - found[2]["baseline"][0]) > 0.05      # the count tells the calendars apart


def test_the_terrain_and_lower_site_tables_use_the_calendars_they_are_given():
    job = ([70.05], [7.59], 2.0, 5, 2)
    assert np.array_equal(extras._long_table_job(job), sun.long_band_minutes_table([70.05], [7.59], 2.0, 5, year_phases=2))
    site = {"name": "Moses Lake, Washington", "lat": 47.1, "lon": -119.3, "kind": "classic lower-latitude analog site"}
    row = extras.lower_site(site, TARGETS, profile_rows=None, step_minutes=5, year_phases=2)
    hours = float(sun.band_minutes_table([47.1], 5, year_phases=2)[0][:, :, :4].sum()) / 60.0
    assert row["targets"]["low"]["hours_a_year_in_band"] == round(hours, 1)
    assert row["targets"]["low"]["longest_spell_h"] == round(float(sun.longest_spell_hours([47.1], [2.08], 5, year_phases=2)[0, 0]), 2)


def test_the_calendars_are_read_from_the_cells_file_and_a_file_without_the_field_had_one():
    assert extras.year_phases_of({"year_phases": 8}) == 8
    assert extras.year_phases_of({}) == 1


def test_refraction_off_gives_the_true_elevation():
    with_air = extras.elevation_edges(65.0, 30, refraction=True)
    without = extras.elevation_edges(65.0, 30, refraction=False)
    assert (with_air >= without).all()
    low = np.abs(without) < 0.5
    assert (with_air[low] - without[low]).mean() == pytest.approx(0.48, abs=0.1)


def test_a_lower_latitude_site_has_minutes_at_dawn_and_dusk_and_no_two_hour_spell():
    row = extras.lower_site({"name": "Somewhere dry", "lat": -24.5, "lon": -67.5, "kind": "other teams' terrain twin"},
                            TARGETS, profile_rows=None, step_minutes=5)
    for tid in ("low", "high"):
        values = row["targets"][tid]
        assert values["hours_a_year_in_band"] > 100.0
        assert 0.0 < values["longest_spell_h"] < 1.0
        assert values["hours_in_spells_of_2h"] == 0.0
        assert values["has_a_2h_spell"] is False
        assert values["profile_hours_a_year_in_band"] is None   # no profile given: unknown, never 0
    assert row["targets"]["high"]["hours_a_year_in_band"] > row["targets"]["low"]["hours_a_year_in_band"]


def test_profile_values_are_read_between_the_two_nearest_half_degrees():
    rows = [{"lat": 35.5, "targets": {"low": {"flat_hours": 100.0, "long_flat_hours": {"1": 0.0, "2": 0.0, "3": 0.0}}}},
            {"lat": 36.0, "targets": {"low": {"flat_hours": 110.0, "long_flat_hours": {"1": 0.0, "2": 0.0, "3": 0.0}}}}]
    found = extras.profile_between(rows, 35.9, "low")
    assert found["flat_hours"] == pytest.approx(108.0)
    assert found["long_flat_hours_2h"] == 0.0
    assert extras.profile_between(rows, 50.0, "low") is None
    assert extras.profile_between(None, 35.9, "low") is None


# ---- arrays of the cells files, version 3 fields present or absent ----------------------------

def test_long_arrays_are_taken_from_the_file_when_it_has_them():
    arrays = {"flat": np.ones((2, 1, 36)), "snow_free": np.ones((2, 1, 36)), "open": np.ones((2, 1, 36)),
              "stretch": np.full((2, 1, 36), 3.0), "long_flat": np.full((2, 1, 36), 0.5),
              "long_snow_free": np.full((2, 1, 36), 0.25), "long_open": np.full((2, 1, 36), 0.125)}
    found = extras.long_arrays(arrays)
    assert found["rule"] == "per-day spells"
    assert found["long_flat"][0, 0, 0] == 0.5 and found["long_open"][1, 0, 35] == 0.125


def test_long_arrays_fall_back_to_the_version_2_rule_when_the_file_lacks_them():
    stretch = np.zeros((1, 1, 36))
    stretch[0, 0, 10] = 2.0
    stretch[0, 0, 11] = 1.9
    open_ = np.full((1, 1, 36), np.nan)
    arrays = {"flat": np.full((1, 1, 36), 4.0), "snow_free": np.full((1, 1, 36), 2.0), "open": open_, "stretch": stretch}
    found = extras.long_arrays(arrays)
    assert found["rule"] == "ten-day bins by median longest spell (version 2)"
    assert found["long_flat"][0, 0, 10] == 4.0 and found["long_flat"][0, 0, 11] == 0.0
    assert found["long_snow_free"][0, 0].sum() == 2.0
    assert np.isnan(found["long_open"][0, 0]).all()     # no horizon stays unknown, never 0


def test_sums_over_bins_stay_unknown_when_a_counted_bin_is_unknown():
    hours = np.array([[1.0] * 36, [np.nan] * 36, [1.0] * 35 + [np.nan]])
    year = extras.sum_bins(hours, None)
    assert year[0] == 36.0 and np.isnan(year[1]) and np.isnan(year[2])
    first = extras.sum_bins(hours, [0, 1, 2])
    assert first[0] == 3.0 and np.isnan(first[1]) and first[2] == 3.0


def test_clear_sky_hours_use_the_month_of_each_bin_and_keep_unknown_cloud_unknown():
    hours = np.zeros((2, 36))
    hours[:, 0] = 10.0      # January
    hours[:, 18] = 20.0     # July
    cloud = {"a": {"cloud_pct": [50.0] * 6 + [75.0] * 6}, "b": {"cloud_pct": None}}
    share = extras.clear_share_table(cloud, ["a", "b"])
    clear = extras.clear_hours(hours, share)
    assert clear[0, 0] == pytest.approx(5.0) and clear[0, 18] == pytest.approx(5.0)
    assert clear[0, 5] == 0.0                       # no hours, so none lost to cloud
    assert np.isnan(clear[1, 0]) and np.isnan(clear[1, 18])
    assert extras.clear_share_table(None, ["a"]) is None


# ---- counting ---------------------------------------------------------------------------------

def test_the_funnel_counts_cells_that_still_reach_the_threshold_after_each_step():
    flat = np.array([150.0, 150.0, 150.0, 150.0, 90.0])
    snow = np.array([120.0, 120.0, 80.0, np.nan, 90.0])
    open_ = np.array([110.0, np.nan, 80.0, np.nan, 90.0])
    km2 = np.array([10.0, 20.0, 30.0, 40.0, 50.0])
    steps = extras.funnel([("sun_alone", flat), ("after_snow", snow), ("after_terrain", open_)], km2, 100.0)
    sun_alone, after_snow, after_terrain = steps["sun_alone"], steps["after_snow"], steps["after_terrain"]
    assert steps["scope"] == {"cells": 5, "bare_km2": 150.0}
    assert (sun_alone["cells"], sun_alone["bare_km2"], sun_alone["unknown_cells"]) == (4, 100.0, 0)
    assert sun_alone["share_of_scope"] == pytest.approx(0.8)
    assert (after_snow["cells"], after_snow["bare_km2"], after_snow["unknown_cells"]) == (2, 30.0, 1)
    assert after_snow["share_of_sun_alone"] == pytest.approx(0.5)
    assert (after_terrain["cells"], after_terrain["bare_km2"], after_terrain["unknown_cells"]) == (1, 10.0, 1)
    assert after_terrain["share_of_sun_alone"] == pytest.approx(0.25)
    assert after_terrain["share_of_previous_step"] == pytest.approx(0.5)


def test_a_step_without_data_is_null_and_so_is_every_share_of_an_empty_start():
    flat = np.array([10.0, 20.0])
    steps = extras.funnel([("sun_alone", flat), ("after_snow", flat), ("after_cloud", None)], np.array([1.0, 1.0]), 100.0)
    assert steps["after_cloud"] is None
    assert steps["sun_alone"]["cells"] == 0
    assert steps["after_snow"]["share_of_sun_alone"] is None     # nothing to take a share of


def test_count_reaching_counts_known_values_only():
    found = extras.count_reaching(np.array([100.0, 99.9, np.nan, 250.0]), np.array([1.0, 2.0, 4.0, 8.0]), 100.0)
    assert found == {"cells": 2, "bare_km2": 9.0, "unknown_cells": 1}


def test_change_marks_what_moves_the_count_by_more_than_a_quarter():
    assert extras.change(100, 126) == {"change": 0.26, "moves_more_than_a_quarter": True}
    assert extras.change(100, 75) == {"change": -0.25, "moves_more_than_a_quarter": False}
    assert extras.change(100, None) == {"change": None, "moves_more_than_a_quarter": None}
    assert extras.change(0, 0) == {"change": None, "moves_more_than_a_quarter": False}
    assert extras.change(0, 5) == {"change": None, "moves_more_than_a_quarter": True}


def test_cells_by_latitude_are_counted_from_hours_per_latitude():
    hours_of_lat = {60.05: 20.0, 70.05: 150.0, 80.05: 100.0}
    lats = np.array([60.05, 70.05, 70.05, 80.05])
    km2 = np.array([1.0, 2.0, 3.0, 4.0])
    assert extras.count_by_latitude(hours_of_lat, lats, km2, 100.0) == {"cells": 3, "bare_km2": 9.0}


# ---- where a known site stands ------------------------------------------------------------------

def test_percentile_is_the_share_of_ranked_cells_with_fewer_hours_ties_counting_half():
    population = np.array([0.0, 10.0, 10.0, 20.0, 30.0, np.nan])
    assert extras.percentile_below(10.0, population) == pytest.approx(40.0)     # 1 below, 2 equal, of 5 known
    assert extras.percentile_below(31.0, population) == pytest.approx(100.0)
    assert extras.percentile_below(None, population) is None
    assert extras.percentile_below(5.0, np.array([])) is None
    assert extras.rank_from_top(20.0, population) == 2
    assert extras.rank_from_top(None, population) is None


def test_verdict_puts_a_percentile_in_plain_words():
    assert extras.verdict(80.0) == "high"
    assert extras.verdict(50.0) == "middling"
    assert extras.verdict(10.0) == "low"
    assert extras.verdict(None) is None


def cell(cid, lat, bare, status, horizon, hours, gridded=True, extra=None):
    values = {"long_flat_hours": 300.0, "long_snow_free_hours": None if status != "measured" else 200.0,
              "long_open_hours": hours if lat > 0 else None,
              "long_summer_rock_hours": None if lat > 0 else 250.0,
              "long_summer_rock_open_hours": None if lat > 0 else hours}
    values.update(extra or {})
    return {"id": cid, "lat": lat, "lon": 10.0, "hemisphere": "N" if lat > 0 else "S", "region": "Test", "bare": bare,
            "bare_km2": 50.0, "gridded": gridded, "snow": {"status": status}, "horizon": horizon,
            "targets": {"low": dict(values)}}


HORIZON = {"north_deg": 1.0, "south_deg": 1.0, "valid_share": 1.0, "pixel_m": 60.0}


def test_ranked_cells_follow_the_rule_of_the_score_module():
    cells = [cell("a", 70.05, 0.5, "measured", HORIZON, 100.0),
             cell("b", 70.05, 0.2, "measured", HORIZON, 100.0),          # too little bare ground
             cell("c", 70.05, 0.5, "doubtful", HORIZON, 100.0),
             cell("d", 70.05, 0.5, "measured", None, None),              # no horizon
             cell("e", 70.05, 0.5, "measured", {"skipped": "window across the antimeridian"}, None),
             cell("f", -70.05, 0.5, "unmeasured", HORIZON, 60.0),
             cell("g", 70.05, 0.5, "measured", HORIZON, 100.0, gridded=False)]
    assert [c["id"] for c in extras.ranked_cells(cells, "N")] == ["a"]
    assert [c["id"] for c in extras.ranked_cells(cells, "S")] == ["f"]
    assert [c["id"] for c in extras.ranked_cells(cells, "N", need_horizon=False)] == ["a", "d", "e"]


def test_a_known_site_gets_its_hours_and_its_place_among_the_ranked_cells():
    cells = [cell(f"7{i}.0_10.0", 70.05 + i, 0.5, "measured", HORIZON, 10.0 * i) for i in range(10)]
    site = {"name": "Crater", "lat": 73.02, "lon": 10.1, "source": "test"}
    row = extras.site_row(site, {c["id"]: c for c in cells}, TARGETS[:1],
                          {"N": extras.ranked_cells(cells, "N"), "S": []},
                          {"N": extras.ranked_cells(cells, "N", need_horizon=False), "S": []},
                          cell_id=lambda lat, lon: "73.0_10.0")
    values = row["targets"]["low"]
    assert row["cell"] == "73.0_10.0" and row["in_the_search"] is True and row["cell_ranked"] is True
    assert values["long_open_hours"] == 30.0
    assert values["hours_field"] == "long_open_hours"
    assert values["percentile_among_ranked"] == pytest.approx(35.0)      # 3 below, itself equal, of 10
    assert values["rank_from_top"] == 7 and values["ranked_cells"] == 10
    assert values["verdict"] == "middling"


def test_a_site_outside_the_search_or_without_a_horizon_has_unknown_hours_not_zero():
    cells = [cell("70.0_10.0", 70.05, 0.5, "measured", HORIZON, 50.0),
             cell("71.0_10.0", 71.05, 0.5, "measured", None, None)]
    by_id = {c["id"]: c for c in cells}
    ranked = {"N": extras.ranked_cells(cells, "N"), "S": []}
    rankable = {"N": extras.ranked_cells(cells, "N", need_horizon=False), "S": []}
    outside = extras.site_row({"name": "Ice dome", "lat": 75.0, "lon": 10.0, "source": "test"}, by_id, TARGETS[:1],
                              ranked, rankable, cell_id=lambda lat, lon: "75.0_10.0")
    assert outside["in_the_search"] is False and outside["cell_ranked"] is False
    assert outside["targets"]["low"]["long_open_hours"] is None
    assert outside["targets"]["low"]["percentile_among_ranked"] is None
    assert outside["targets"]["low"]["verdict"] is None
    no_horizon = extras.site_row({"name": "Plain", "lat": 71.0, "lon": 10.0, "source": "test"}, by_id, TARGETS[:1],
                                 ranked, rankable, cell_id=lambda lat, lon: "71.0_10.0")
    assert no_horizon["in_the_search"] is True and no_horizon["has_a_horizon"] is False
    assert no_horizon["targets"]["low"]["long_open_hours"] is None
    assert no_horizon["targets"]["low"]["long_snow_free_hours"] == 200.0
    assert no_horizon["targets"]["low"]["percentile_flat_among_rankable"] is not None


def test_a_southern_site_is_read_from_the_rock_season_hours():
    cells = [cell("-70.0_10.0", -69.95, 0.5, "unmeasured", HORIZON, 40.0),
             cell("-71.0_10.0", -70.95, 0.5, "unmeasured", HORIZON, 80.0)]
    row = extras.site_row({"name": "Oasis", "lat": -70.9, "lon": 10.2, "source": "test"}, {c["id"]: c for c in cells},
                          TARGETS[:1], {"N": [], "S": extras.ranked_cells(cells, "S")},
                          {"N": [], "S": extras.ranked_cells(cells, "S", need_horizon=False)},
                          cell_id=lambda lat, lon: "-71.0_10.0")
    values = row["targets"]["low"]
    assert values["hours_field"] == "long_summer_rock_open_hours"
    assert values["long_open_hours"] == 80.0
    assert values["long_snow_free_hours"] is None       # snow is not measured in the south
    assert values["percentile_among_ranked"] == pytest.approx(75.0)
    assert values["verdict"] == "high"


def test_site_summary_counts_each_cell_once():
    def row(name, cid, pct):
        return {"name": name, "cell": cid, "hemisphere": "N",
                "targets": {"low": {"percentile_among_ranked": pct, "verdict": extras.verdict(pct)}}}
    summary = extras.site_summary([row("A", "c1", 90.0), row("A again", "c1", 90.0), row("B", "c2", 20.0),
                                   row("C", "c3", None)], TARGETS[:1], "N")
    assert summary["low"] == {"cells_with_a_value": 2, "cells_without_a_value": 1, "median_percentile": 55.0,
                              "high": 1, "middling": 0, "low": 1}


# ---- the file ---------------------------------------------------------------------------------

def test_unknown_numbers_are_written_as_null():
    assert extras.clean({"a": float("nan"), "b": [1.0, np.float32(2.5), np.nan], "c": np.int64(3), "d": None,
                         "e": np.bool_(True)}) == {"a": None, "b": [1.0, 2.5, None], "c": 3, "d": None, "e": True}


def test_the_file_is_written_beside_the_old_one_and_renamed_into_place(tmp_path):
    path = tmp_path / "validation_extras.json"
    path.write_text("old")
    extras.write_json(path, {"x": float("nan"), "y": 1})
    assert json.loads(path.read_text()) == {"x": None, "y": 1}
    assert [p.name for p in tmp_path.iterdir()] == ["validation_extras.json"]


def test_the_lower_latitude_list_is_the_one_the_job_names():
    names = [s["name"] for s in extras.LOWER_SITES]
    assert len(names) == 11
    assert {(s["lat"], s["lon"]) for s in extras.LOWER_SITES} >= {(35.9, 76.5), (-24.5, -67.5), (47.1, -119.3)}
    assert all(abs(s["lat"]) < 59.0 for s in extras.LOWER_SITES)


# ---- added after the first run: what each step keeps, and the table --------------------------------

def test_the_funnel_says_what_each_step_keeps_of_the_hours_and_of_the_cells_with_a_value():
    flat = np.array([150.0, 150.0, 150.0, 150.0, 90.0])
    snow = np.array([120.0, 120.0, 80.0, np.nan, 90.0])
    open_ = np.array([110.0, np.nan, 80.0, np.nan, 90.0])
    steps = extras.funnel([("sun_alone", flat), ("after_snow", snow), ("after_terrain", open_)], np.ones(5), 100.0)
    assert steps["sun_alone"]["median_share_of_hours_kept"] is None
    assert steps["after_snow"]["median_share_of_hours_kept"] == pytest.approx(0.8)
    assert steps["after_snow"]["share_of_previous_step_with_a_value"] == pytest.approx(2 / 3, abs=1e-4)
    assert steps["after_snow"]["still_at_least_h"] == {"50": 3, "25": 3}
    assert steps["after_terrain"]["median_share_of_hours_kept"] == pytest.approx(110 / 120, abs=1e-3)
    assert steps["after_terrain"]["share_of_previous_step_with_a_value"] == 1.0
    assert steps["after_terrain"]["still_at_least_h"] == {"50": 1, "25": 1}


def test_the_sensitivity_table_lists_every_choice_with_its_change_and_names_the_big_movers():
    sun_rows = {"baseline": {"cells": 100, "bare_km2": 1000.0},
                "ceiling_minus_0.5_deg": {"cells": 60, "bare_km2": 600.0, "change": -0.4, "moves_more_than_a_quarter": True},
                "ceiling_plus_0.5_deg": {"cells": 110, "bare_km2": 1100.0, "change": 0.1, "moves_more_than_a_quarter": False},
                "spell_1_h": {"cells": 120, "bare_km2": 1.0, "change": 0.2, "moves_more_than_a_quarter": False},
                "spell_3_h": {"cells": 90, "bare_km2": 1.0, "change": -0.1, "moves_more_than_a_quarter": False},
                "refraction_off": {"cells": 95, "bare_km2": 1.0, "change": -0.05, "moves_more_than_a_quarter": False}}
    data_rows = {
        "all_measured_cells": {"cells_in_scope": 500, "sun_alone": {"cells": 100, "bare_km2": 1000.0},
                               "with_snow_odds_the_file_uses": {"cells": 70, "bare_km2": 700.0},
                               "with_snow_as_mapped": {"cells": 70, "bare_km2": 700.0},
                               "with_snow_with_rule": None},
        "measured_cells_with_a_horizon": {"cells_in_scope": 50, "sun_alone": {"cells": 40, "bare_km2": 400.0},
                                          "with_snow_no_terrain": {"cells": 32, "bare_km2": 320.0},
                                          "with_terrain_no_snow": None,
                                          "with_snow_and_terrain": {"cells": 20, "bare_km2": 200.0},
                                          "with_snow_terrain_and_cloud": None}}
    table = extras.sensitivity_table(sun_rows, data_rows)
    by_choice = {(row["choice"], row["scope"]): row for row in table}
    lower = by_choice[("Sun ceiling 0.5 degrees lower", "all measured cells")]
    assert (lower["cells"], lower["baseline_cells"], lower["change"], lower["moves_more_than_a_quarter"]) == (60, 100, -0.4, True)
    snow = by_choice[("snow-free odds as the maps read", "all measured cells")]
    assert (snow["cells"], snow["change"], snow["moves_more_than_a_quarter"]) == (70, -0.3, True)
    rule = by_choice[("snow-free odds with the stale-flag rule", "all measured cells")]
    assert rule["cells"] is None and rule["change"] is None and rule["moves_more_than_a_quarter"] is None
    both = by_choice[("snow-free odds and terrain horizon", "measured cells with a terrain horizon")]
    assert (both["cells"], both["baseline_cells"], both["change"], both["moves_more_than_a_quarter"]) == (20, 40, -0.5, True)
    assert by_choice[("terrain horizon, no snow", "measured cells with a terrain horizon")]["cells"] is None
    assert extras.big_movers(table) == ["Sun ceiling 0.5 degrees lower (all measured cells: 100 to 60 cells)",
                                        "snow-free odds as the maps read (all measured cells: 100 to 70 cells)",
                                        "snow-free odds and terrain horizon (measured cells with a terrain horizon: 40 to 20 cells)"]


def test_period_hours_are_rounded_like_the_cells_file_before_they_are_counted():
    hours = np.zeros((2, 36))
    hours[0, 10], hours[1, 10] = 99.96, 99.94
    found = extras.period_hours(hours, [9, 10, 11])
    assert found.tolist() == [100.0, 99.9]          # grazing_cells.json keeps one decimal, and the counts are made on that
    assert extras.count_by_latitude({60.05: 99.96, 70.05: 99.94}, np.array([60.05, 70.05]), np.ones(2), 100.0)["cells"] == 1

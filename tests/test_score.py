# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
import importlib

import pytest

from twinfinder import score

score_cells = importlib.import_module("scripts.score_cells")


# ---- factor scores at their edges ----

def test_two_hundred_long_window_hours_earn_full_light_marks():
    assert score.FULL_HOURS == 200.0
    assert score.light_score(100.0) == pytest.approx(0.5)
    assert score.light_score(200.0) == pytest.approx(1.0)
    assert score.light_score(950.0) == pytest.approx(1.0)


def test_no_hours_is_a_known_zero_and_unknown_hours_stay_unknown():
    assert score.light_score(0.0) == 0.0
    assert score.light_score(None) is None


def test_light_cap_can_be_changed_for_the_stability_check():
    assert score.light_score(100.0, full_hours=400.0) == pytest.approx(0.25)
    assert score.light_score(100.0, full_hours=100.0) == pytest.approx(1.0)


def test_terrain_score_is_the_overlap_against_the_lunar_sites_own_overlap():
    assert score.terrain_score(0.4, 0.8) == pytest.approx(0.5)
    assert score.terrain_score(0.8, 0.8) == pytest.approx(1.0)
    assert score.terrain_score(0.95, 0.8) == pytest.approx(1.0)   # a cell cannot beat the Moon against itself
    assert score.terrain_score(0.0, 0.8) == 0.0


def test_terrain_score_is_unknown_without_an_overlap_or_a_yardstick():
    assert score.terrain_score(None, 0.8) is None
    assert score.terrain_score(0.4, None) is None


def test_geometric_mean_sinks_on_any_zero():
    assert score.geometric_mean([1.0, 0.25]) == pytest.approx(0.5)
    assert score.geometric_mean([0.9, 0.0, 0.9]) == 0.0


def test_goal_scores_use_the_right_factors():
    goals = score.goal_scores({"light": 1.0, "terrain": 0.25, "bare": 1.0, "rock": 0.0})
    assert goals["lighting"] == pytest.approx(1.0)
    assert goals["shadows"] == pytest.approx(0.25 ** (1 / 3))
    assert goals["geology"] == 0.0
    assert goals["full"] == 0.0


def test_lighting_goal_is_light_and_bare_only():
    assert score.GOALS["lighting"] == ("light", "bare")
    goals = score.goal_scores({"light": 0.25, "terrain": None, "bare": 1.0, "rock": 0.0})
    assert goals["lighting"] == pytest.approx(0.5)


def test_a_goal_with_an_unknown_factor_is_unknown_not_zero():
    goals = score.goal_scores({"light": None, "terrain": 0.5, "bare": 0.5, "rock": 0.5})
    assert goals["lighting"] is None and goals["shadows"] is None and goals["full"] is None
    assert goals["geology"] == pytest.approx(0.5)   # geology does not use the light
    no_terrain = score.goal_scores({"light": 0.5, "terrain": None, "bare": 0.5, "rock": 0.5})
    assert no_terrain["lighting"] == pytest.approx(0.5)
    assert no_terrain["shadows"] is None and no_terrain["geology"] is None and no_terrain["full"] is None


def test_target_light_is_gone():
    assert not hasattr(score, "target_light")


# ---- which hours the light score is read from ----

def hours(**changes):
    values = {"long_open_hours": 120.0, "long_snow_free_hours": 180.0, "long_flat_hours": 400.0,
              "long_summer_rock_open_hours": None, "long_summer_rock_hours": None}
    return {**values, **changes}


def test_northern_light_comes_from_long_open_hours_and_flat_light_from_snow_free_hours():
    assert score.light_hours(hours(), "N") == 120.0
    assert score.light_hours(hours(), "N", basis="flat") == 180.0


def test_northern_light_is_unknown_without_a_horizon():
    assert score.light_hours(hours(long_open_hours=None), "N") is None


def test_southern_light_comes_from_the_summer_rock_hours():
    south = hours(long_open_hours=None, long_snow_free_hours=None,
                  long_summer_rock_open_hours=90.0, long_summer_rock_hours=150.0)
    assert score.light_hours(south, "S") == 90.0
    assert score.light_hours(south, "S", basis="flat") == 150.0


def test_an_unknown_basis_is_refused():
    with pytest.raises(ValueError):
        score.light_hours(hours(), "N", basis="noon")


# ---- the ranking filters ----

def cell(**changes):
    base = {"id": "70.0_20.0", "lat": 70.05, "lon": 20.15, "hemisphere": "N", "gridded": True, "bare": 0.6,
            "snow": {"status": "measured", "source": "3x3", "land_pixels": 9, "stuck_winters": 0},
            "horizon": {"north_deg": 1.0, "south_deg": 2.0, "valid_share": 1.0, "pixel_m": 60.0}}
    return {**base, **changes}


def test_a_measured_cell_with_a_horizon_and_enough_bare_ground_is_ranked():
    assert score.not_ranked_because(cell()) == []


def test_each_reason_for_not_ranking_is_named():
    doubtful = cell(snow={"status": "doubtful", "source": "3x3", "land_pixels": 4, "stuck_winters": 2})
    no_data = cell(snow={"status": "no data", "source": None, "land_pixels": 0, "stuck_winters": 0})
    assert score.not_ranked_because(doubtful) == ["snow doubtful"]
    assert score.not_ranked_because(no_data) == ["no snow data"]
    assert score.not_ranked_because(cell(horizon=None)) == ["no horizon"]
    assert score.not_ranked_because(cell(bare=0.2)) == ["bare under 0.25"]
    crossing = cell(horizon={"skipped": "window at 71.0, 179.9 crosses the antimeridian (longitudes 179.1 to 180.7); not supported"})
    assert score.not_ranked_because(crossing) == ["window across the antimeridian"]


def test_other_skipped_horizons_say_why():
    assert score.not_ranked_because(cell(horizon={"skipped": "no land pixels"})) == ["no horizon: no land pixels"]


def test_several_reasons_are_all_listed():
    reasons = score.not_ranked_because(cell(horizon=None, bare=0.1,
                                            snow={"status": "doubtful", "source": "5x5", "land_pixels": 0,
                                                  "stuck_winters": 1}))
    assert reasons == ["snow doubtful", "no horizon", "bare under 0.25"]


def test_the_bare_screen_can_be_moved():
    assert score.not_ranked_because(cell(bare=0.2), min_bare=0.15) == []
    assert score.not_ranked_because(cell(bare=0.3), min_bare=0.35) == ["bare under 0.35"]


def test_unknown_bare_ground_and_cells_outside_the_screen_are_not_ranked():
    assert score.not_ranked_because(cell(bare=None)) == ["bare unknown"]
    assert score.not_ranked_because(cell(gridded=False)) == ["named-site cell outside the screen"]


def test_southern_cells_are_not_held_back_by_their_unmeasured_snow():
    south = cell(hemisphere="S", lat=-70.0, snow={"status": "unmeasured", "source": None, "land_pixels": None,
                                                  "stuck_winters": None})
    assert score.not_ranked_because(south) == []


def test_the_horizon_rule_can_be_set_aside_for_flat_horizon_counts():
    assert score.not_ranked_because(cell(horizon=None), need_horizon=False) == []


# ---- sites ----

def test_cluster_sites_keeps_the_best_cell_of_each_neighbourhood():
    cells = [
        {"id": "a", "lat": 64.0, "lon": -20.0, "s": 0.9},
        {"id": "b", "lat": 64.1, "lon": -20.0, "s": 0.8},   # 11 km from a
        {"id": "c", "lat": 70.0, "lon": 25.0, "s": 0.7},
        {"id": "d", "lat": 64.0, "lon": -20.1, "s": 0.0},   # zero scores are never sites
    ]
    sites = score.cluster_sites(cells, key=lambda c: c["s"], min_separation_km=50.0)
    assert [c["id"] for c in sites] == ["a", "c"]


def test_top_sites_leaves_out_cells_whose_score_is_unknown():
    cells = [
        {"id": "a", "lat": 64.0, "lon": -20.0, "s": None},   # would crash or read as zero if it were compared
        {"id": "b", "lat": 70.0, "lon": 25.0, "s": 0.7},
        {"id": "c", "lat": 75.0, "lon": 60.0, "s": 0.9},
    ]
    assert [c["id"] for c in score.top_sites(cells, key=lambda c: c["s"])] == ["c", "b"]
    assert [c["id"] for c in score.top_sites(cells, key=lambda c: c["s"], top=1)] == ["c"]


def test_survivors_counts_baseline_sites_with_a_variant_site_within_fifty_km():
    baseline = [{"lat": 64.0, "lon": -20.0}, {"lat": 70.0, "lon": 25.0}, {"lat": 75.0, "lon": 60.0}]
    variant = [{"lat": 64.1, "lon": -20.0}, {"lat": 75.0, "lon": 60.0}, {"lat": 80.0, "lon": 20.0}]
    assert score.survivors(baseline, variant) == 2
    assert score.survivors(baseline, []) == 0
    assert score.survivors([], variant) == 0


# ---- scored records (scripts/score_cells.py) ----

TARGET = {"id": "malapert", "name": "Malapert Massif", "limit_deg": 5.55}
SELF_OVERLAP = {"malapert": 0.8}


def grazing_cell(**changes):
    values = {"flat_hours": 900.0, "snow_free_hours": 500.0, "open_hours": 300.0, "long_flat_hours": 400.0,
              "long_snow_free_hours": 180.0, "long_open_hours": 100.0, "long_summer_rock_hours": None,
              "long_summer_rock_open_hours": None, "poleward_share": 0.9, "top_bins": [[17, 40.0], [18, 35.5]]}
    values.update(changes.pop("hours", {}))
    base = cell(region="Norway, Sweden or Finland", bare_km2=30.0, land_share=0.9, layers_disagree=None,
                targets={"malapert": values})
    return {**base, **changes}


def scored(grazing, terrain={"median_slope_deg": 6.0, "p90_slope_deg": 20.0, "relief_m": 700.0, "valid_share": 1.0,
                             "overlap": {"malapert": 0.4}}):
    return score_cells.scored_record(grazing, terrain, [TARGET], SELF_OVERLAP, bodies=[], known_sites=[],
                                     south_sites=[])


def test_a_scored_record_carries_the_factors_and_goals_per_target():
    record = scored(grazing_cell())
    t = record["targets"]["malapert"]
    assert record["ranked"] is True and record["not_ranked_because"] == []
    assert t["light"] == pytest.approx(0.5)
    assert t["light_flat"] == pytest.approx(0.9)
    assert t["terrain_overlap"] == pytest.approx(0.4)
    assert t["terrain"] == pytest.approx(0.5)
    assert t["rock"] == 0.0 and record["rock"] == {"score": 0.0, "body": None}
    assert t["goals"]["lighting"] == pytest.approx((0.5 * 0.6) ** 0.5, abs=1e-3)
    assert t["goals"]["shadows"] == pytest.approx((0.5 * 0.5 * 0.6) ** (1 / 3), abs=1e-3)
    assert t["goals"]["geology"] == 0.0
    assert t["long_open_hours"] == 100.0 and t["top_bins"] == [[17, 40.0], [18, 35.5]]
    assert record["terrain"]["median_slope_deg"] == 6.0 and record["terrain"]["relief_m"] == 700.0


def test_a_cell_with_unknown_light_is_not_ranked_and_never_scored_zero():
    record = scored(grazing_cell(horizon=None, hours={"long_open_hours": None, "open_hours": None}))
    t = record["targets"]["malapert"]
    assert record["ranked"] is False and record["not_ranked_because"] == ["no horizon"]
    assert t["light"] is None
    assert t["goals"]["lighting"] is None and t["goals"]["shadows"] is None and t["goals"]["full"] is None
    assert t["light_flat"] == pytest.approx(0.9)   # kept for counts only


def test_a_cell_without_terrain_keeps_its_lighting_goal_and_has_no_terrain_goals():
    for missing in (None, {"skipped": "window refused"}, {"valid_share": 0.01, "slope_pixels": 12}):
        record = scored(grazing_cell(), terrain=missing)
        t = record["targets"]["malapert"]
        assert t["terrain"] is None and t["terrain_overlap"] is None
        assert t["goals"]["lighting"] is not None
        assert t["goals"]["shadows"] is None and t["goals"]["geology"] is None


def test_a_southern_record_takes_its_light_from_the_summer_rock_hours():
    south = grazing_cell(hemisphere="S", lat=-77.55, lon=161.75, region="Victoria Land",
                         snow={"status": "unmeasured", "source": None, "land_pixels": None, "stuck_winters": None},
                         hours={"long_open_hours": 700.0, "long_snow_free_hours": None, "snow_free_hours": None,
                                "long_summer_rock_hours": 300.0, "long_summer_rock_open_hours": 50.0})
    record = scored(south)
    assert record["ranked"] is True and record["ranking"] == "south"
    assert record["targets"]["malapert"]["light"] == pytest.approx(0.25)
    assert record["targets"]["malapert"]["light_flat"] == pytest.approx(1.0)


def test_iceland_svalbard_devon_island_and_the_dry_valleys_are_not_little_known():
    def flagged(lat, lon, region):
        return scored(grazing_cell(lat=lat, lon=lon, region=region))
    assert flagged(64.5, -18.0, "Iceland")["little_known"] is False
    assert flagged(78.5, 16.0, "Svalbard")["little_known"] is False
    assert flagged(75.4, -85.0, "Arctic Canada")["little_known"] is False        # Devon Island, 130 km east of Haughton
    assert flagged(-77.3, 162.0, "Victoria Land")["little_known"] is False       # McMurdo Dry Valleys
    assert flagged(72.0, -100.0, "Arctic Canada")["little_known"] is True
    assert flagged(-71.0, 165.0, "Victoria Land")["little_known"] is True


def test_a_cell_near_a_listed_analog_site_is_not_little_known():
    known = [{"name": "Kangerlussuaq", "lat": 67.0086, "lon": -50.6892, "tier": "B", "body": "Mars"}]
    record = score_cells.scored_record(grazing_cell(lat=67.05, lon=-50.75, region="Greenland"), None, [TARGET],
                                       SELF_OVERLAP, bodies=[], known_sites=known, south_sites=[])
    assert record["little_known"] is False and record["known"]["name"] == "Kangerlussuaq"


def test_a_southern_cell_near_a_site_with_analog_use_is_not_little_known():
    sites = [{"name": "Lake Untersee", "lat": -71.34, "lon": 13.45, "existing_analog_use": "Mars analog"},
             {"name": "Bunger Hills", "lat": -66.27, "lon": 100.75, "existing_analog_use": None}]
    near_use = grazing_cell(hemisphere="S", lat=-71.35, lon=13.35, region="Dronning Maud Land")
    near_none = grazing_cell(hemisphere="S", lat=-66.25, lon=100.65, region="Wilkes Land")
    def build(c):
        return score_cells.scored_record(c, None, [TARGET], SELF_OVERLAP, bodies=[], known_sites=[],
                                         south_sites=sites)
    assert build(near_use)["little_known"] is False
    assert build(near_none)["little_known"] is True


def test_rock_comes_from_the_listed_bodies():
    bodies = [{"name": "Test anorthosite", "lat": 70.05, "lon": 20.15, "radius_km": 5, "an_low": 86, "an_high": 88}]
    record = score_cells.scored_record(grazing_cell(), None, [TARGET], SELF_OVERLAP, bodies=bodies, known_sites=[],
                                       south_sites=[])
    assert record["rock"] == {"score": pytest.approx(0.82), "body": "Test anorthosite"}
    assert record["targets"]["malapert"]["rock"] == pytest.approx(0.82)


# ---- ranking tables ----

def test_a_ten_day_bin_reads_as_dates():
    assert score_cells.bin_dates(0) == "1 Jan-10 Jan"
    assert score_cells.bin_dates(17) == "20 Jun-29 Jun"
    assert score_cells.bin_dates(35) == "17 Dec-31 Dec"   # the last bin holds the days left over


def test_the_side_note_says_where_the_low_sun_stands():
    assert "midnight-Sun side" in score_cells.side_note(0.9, "N")
    assert "equator side" in score_cells.side_note(0.1, "N")
    assert score_cells.side_note(None, "N") == "no long window"


def test_ranked_sites_take_only_ranked_cells_of_one_hemisphere_with_a_known_score():
    north = scored(grazing_cell(id="a", lat=70.05, lon=20.15))
    far = scored(grazing_cell(id="b", lat=75.05, lon=60.15, hours={"long_open_hours": 190.0}))
    no_horizon = scored(grazing_cell(id="c", lat=80.05, lon=20.15, horizon=None, hours={"long_open_hours": None}))
    thin_bare = scored(grazing_cell(id="d", lat=65.05, lon=-40.15, bare=0.2, hours={"long_open_hours": 200.0}))
    south = scored(grazing_cell(id="e", hemisphere="S", lat=-77.55, lon=161.75,
                                hours={"long_summer_rock_open_hours": 200.0}))
    records = [north, far, no_horizon, thin_bare, south]
    sites = score_cells.ranked_sites(records, "malapert", "lighting", "north")
    assert [r["id"] for r in sites] == ["b", "a"]
    assert [r["id"] for r in score_cells.ranked_sites(records, "malapert", "lighting", "south")] == ["e"]


def test_old_results_are_renamed_once_and_never_overwritten(tmp_path):
    (tmp_path / "ranking.txt").write_text("scored cells: 3; old ranking")
    (tmp_path / "cells_scored.json").write_text("[]")
    score_cells.keep_old_results(tmp_path)
    assert (tmp_path / "ranking_v1.txt").read_text() == "scored cells: 3; old ranking"
    assert (tmp_path / "cells_scored_v1.json").read_text() == "[]"
    assert not (tmp_path / "ranking.txt").exists()
    (tmp_path / "ranking.txt").write_text("new ranking")
    score_cells.keep_old_results(tmp_path)   # a second run must leave the kept copy alone
    assert (tmp_path / "ranking_v1.txt").read_text() == "scored cells: 3; old ranking"
    assert (tmp_path / "ranking.txt").read_text() == "new ranking"


def test_best_bins_of_a_season_are_the_long_window_hours_inside_it():
    hours = [0.0] * 36          # long-window hours per ten-day bin (per-day spells, version 3)
    hours[34] = 50.0            # in the season
    hours[0] = 30.0             # in the season
    hours[17] = 90.0            # the other half of the year
    hours[2] = float("nan")     # unknown: left out, never a zero that is printed
    season = [33, 34, 35, 0, 1, 2, 3, 4, 5]
    assert score_cells.top_bins_in(hours, season) == [[34, 50.0], [0, 30.0]]
    assert score_cells.top_bins_in(hours, range(36), count=1) == [[17, 90.0]]


def test_the_poleward_sectors_are_the_half_circle_around_the_pole():
    assert score_cells.poleward_sectors("N") == list(range(0, 9)) + list(range(27, 36))
    assert score_cells.poleward_sectors("S") == list(range(9, 27))


def test_cluster_sites_can_stop_once_enough_sites_are_found():
    cells = [{"id": str(k), "lat": 60.0 + k, "lon": 0.0, "s": 1.0 - k / 100} for k in range(20)]
    calls = []

    def key(c):
        calls.append(c["id"])
        return c["s"]

    assert [c["id"] for c in score.cluster_sites(cells, key=key, limit=3)] == ["0", "1", "2"]
    assert len(score.cluster_sites(cells, key=key)) == 20   # without a limit every site is still returned
    assert [c["id"] for c in score.top_sites(cells, key=lambda c: c["s"], top=3)] == ["0", "1", "2"]


# ---- edges the first tests left open ----

def test_every_goal_that_names_bare_ground_uses_it():
    goals = score.goal_scores({"light": 1.0, "terrain": 1.0, "rock": 1.0, "bare": 0.0625})
    assert goals["lighting"] == pytest.approx(0.25)
    assert goals["shadows"] == pytest.approx(0.0625 ** (1 / 3))
    assert goals["geology"] == pytest.approx(0.0625 ** (1 / 3))
    assert goals["full"] == pytest.approx(0.5)


def test_bare_ground_exactly_at_the_screen_is_ranked():
    assert score.not_ranked_because(cell(bare=0.25)) == []
    assert score.not_ranked_because(cell(bare=0.2499)) == ["bare under 0.25"]


def test_survivors_reach_out_to_fifty_km_and_no_further():
    baseline = [{"lat": 64.0, "lon": -20.0}]
    assert score.survivors(baseline, [{"lat": 64.4, "lon": -20.0}]) == 1    # 44 km away
    assert score.survivors(baseline, [{"lat": 64.5, "lon": -20.0}]) == 0    # 56 km away


def test_published_scores_are_made_from_the_stored_factors():
    factors = {"light": 0.16650049, "terrain": 0.00457123456, "bare": 0.6175298804780877, "rock": 0.8166666666}
    stored = score.rounded_factors(factors)
    assert stored == {"light": 0.1665, "terrain": 0.004571, "bare": 0.61753, "rock": 0.816667}
    published = score.published_goals(factors)
    assert published == {goal: round(value, 3) for goal, value in score.goal_scores(stored).items()}
    assert score.published_goals(stored) == published        # so anyone can rebuild a score from the file
    unknown = score.published_goals({**factors, "light": None})
    assert unknown["lighting"] is None and unknown["geology"] == published["geology"]
    assert score.rounded_factors({"light": None, "bare": 0.5})["light"] is None


def test_a_scored_record_keeps_six_decimals_of_each_factor_and_scores_from_them():
    record = scored(grazing_cell(bare=0.6175298804780877, hours={"long_open_hours": 33.3, "long_snow_free_hours": 77.7}),
                    terrain={"median_slope_deg": 6.0, "p90_slope_deg": 20.0, "relief_m": 700.0, "valid_share": 1.0,
                             "overlap": {"malapert": 0.0037}})
    t = record["targets"]["malapert"]
    assert t["light"] == 0.1665 and t["light_flat"] == 0.3885
    assert t["bare"] == 0.61753 and t["terrain"] == 0.004625
    assert record["bare"] == 0.6175298804780877               # the cell's own value is kept whole
    for goal, factors in score.GOALS.items():
        if "rock" in factors:
            continue                                          # no rock body here: a known zero
        assert t["goals"][goal] == round(score.geometric_mean(t[f] for f in factors), 3)
    assert t["goals_flat"]["lighting"] == round((0.3885 * 0.61753) ** 0.5, 3)


def test_ranked_flat_still_refuses_doubtful_snow_and_only_sets_the_horizon_aside():
    no_horizon = scored(grazing_cell(horizon=None, hours={"long_open_hours": None}))
    doubtful = scored(grazing_cell(snow={"status": "doubtful", "source": "3x3", "land_pixels": 9, "stuck_winters": 2}))
    assert no_horizon["ranked"] is False and no_horizon["ranked_flat"] is True
    assert doubtful["ranked"] is False and doubtful["ranked_flat"] is False


def test_a_southern_cell_far_from_a_site_with_analog_use_stays_little_known():
    sites = [{"name": "Lake Untersee", "lat": -71.34, "lon": 13.45, "existing_analog_use": "Mars analog"}]
    far = grazing_cell(hemisphere="S", lat=-72.25, lon=13.45, region="Dronning Maud Land")    # 101 km south
    record = score_cells.scored_record(far, None, [TARGET], SELF_OVERLAP, bodies=[], known_sites=[], south_sites=sites)
    assert record["little_known"] is True


def test_the_devon_island_boxes_stop_at_jones_sound():
    def little_known(lat, lon):
        return scored(grazing_cell(lat=lat, lon=lon, region="Arctic Canada"))["little_known"]
    # Devon Island itself
    assert little_known(75.65, -84.75) is False     # Truelove Lowland on the north coast
    assert little_known(74.75, -91.75) is False     # the south-west, facing Lancaster Sound
    assert little_known(76.25, -89.75) is False     # Colin Archer Peninsula, towards Cape Vera
    assert little_known(76.55, -92.25) is False     # the neck north of it
    assert little_known(76.85, -96.75) is False     # Grinnell Peninsula
    # Across Jones Sound and Cardigan Strait: Ellesmere Island and North Kent Island are not Devon Island.
    assert little_known(76.45, -86.75) is True      # Ellesmere, south coast near Cape Storm
    assert little_known(76.85, -83.25) is True      # Ellesmere, north of Grise Fiord
    assert little_known(76.35, -87.75) is True
    assert little_known(76.55, -89.75) is True      # North Kent Island and Hell Gate


def test_a_best_bin_whose_hours_round_to_zero_is_left_out():
    hours = [0.0] * 36
    hours[34], hours[35] = 50.0, 0.04
    assert score_cells.top_bins_in(hours, [33, 34, 35]) == [[34, 50.0]]


def test_an_unknown_number_prints_as_a_dash_never_as_zero():
    assert score_cells.number(None, 6, 0).strip() == "-"
    assert score_cells.number(0.0, 6, 0).strip() == "0"
    assert len(score_cells.number(None, 6, 0)) == 6


# ---- both scripts end to end on a small made-up project ----

import json  # noqa: E402

import numpy as np  # noqa: E402

from twinfinder import grid  # noqa: E402

TINY_TARGET = {"id": "malapert", "name": "Malapert Massif", "limit_deg": 5.55, "elev_bins": [0, 1, 2, 3, 4, 5, 6]}
WINTER_NORTH = list(range(27, 36)) + list(range(0, 9))
SUMMER_NORTH = list(range(9, 27))
SUMMER_SOUTH = [33, 34, 35, 0, 1, 2, 3, 4, 5]
NORTH_STRETCH = {17: 5.0, 18: 2.0, 19: 2.3, 20: 4.7, 21: 3.0, 30: 1.5}   # bin 18 sits exactly on the 2 h minimum
SOUTH_STRETCH = {34: 6.0, 0: 4.0, 12: 5.0}                               # bin 12 is a long window outside the rock season
HORIZON = {"north_deg": 1.0, "south_deg": 2.0, "valid_share": 1.0, "pixel_m": 60.0}
ANTIMERIDIAN = {"skipped": "window at 66.15, -179.85 crosses the antimeridian (longitudes -180.53 to -179.17); not supported"}
DOUBTFUL = {"status": "doubtful", "source": "3x3", "land_pixels": 9, "stuck_winters": 2}
NO_DATA = {"status": "no data", "source": None, "land_pixels": 0, "stuck_winters": 0}
UNMEASURED = {"status": "unmeasured", "source": None, "land_pixels": None, "stuck_winters": None}


def measured(pixels: int = 9) -> dict:
    return {"status": "measured", "source": "3x3", "land_pixels": pixels, "stuck_winters": 0}


# nickname: where it is, its ground and snow, its horizon, and its hours per ten-day bin (None = unknown)
TINY_CELLS = {
    "a": dict(point=(70.05, 20.15), region="Norway, Sweden or Finland", bare=0.9, snow=measured(), horizon=HORIZON,
              flat={17: 120.0, 18: 70.0, 30: 50.0}, snow_free={17: 110.0, 18: 60.0, 30: 40.0},
              open={17: 100.0, 18: 50.0, 30: 40.0}, usable=12.0),
    "b": dict(point=(68.25, -96.15), region="Arctic Canada", bare=0.5, snow=measured(3), horizon=HORIZON,
              flat={18: 130.0}, snow_free={18: 120.0}, open={18: 100.0}, usable=3.0),
    "doubtful": dict(point=(72.05, 100.25), region="Siberia and the Russian Far East", bare=0.9, snow=DOUBTFUL,
                     horizon=HORIZON, flat={17: 220.0}, snow_free={17: 210.0}, open={17: 200.0}, usable=15.0),
    "no_data": dict(point=(80.05, 60.0), region="Franz Josef Land", bare=0.9, snow=NO_DATA, horizon=HORIZON,
                    flat={17: 150.0}, snow_free=None, open=None, usable=None),
    "no_horizon": dict(point=(66.05, -40.0), region="Greenland", bare=0.9, snow=measured(), horizon=None,
                       flat={17: 260.0}, snow_free={17: 250.0}, open=None, usable=0.0),
    "skipped": dict(point=(66.15, -179.85), region="Chukotka", bare=0.9, snow=measured(), horizon=ANTIMERIDIAN,
                    flat={17: 90.0}, snow_free={17: 80.0}, open=None, usable=0.0),
    "haughton": dict(point=(75.38, -89.67), region="Arctic Canada", bare=0.3, snow=measured(), horizon=HORIZON,
                     site_name="Haughton crater, Devon Island, Canada", flat={19: 19.8, 20: 45.8, 21: 7.0},
                     snow_free={19: 17.5, 20: 45.8, 21: 7.0}, open={19: 16.1, 20: 41.0, 21: 6.0}, usable=0.0),
    "bear_island": dict(point=(74.45, 19.25), region="Bear Island (Bjornoya)", bare=0.9, snow=DOUBTFUL, horizon=HORIZON,
                        gridded=False, site_name="Bear Island, Norway", flat={17: 300.0}, snow_free={17: 300.0},
                        open={17: 300.0}, usable=20.0),
    "jan_mayen": dict(point=(70.95, -8.55), region="Jan Mayen", bare=0.9, snow=measured(), horizon=HORIZON,
                      gridded=False, site_name="Jan Mayen, Norway", flat={17: 300.0}, snow_free={17: 300.0},
                      open={17: 300.0}, usable=20.0),
    "oasis": dict(point=(-70.05, 20.0), region="Dronning Maud Land", bare=0.8, snow=UNMEASURED, horizon=HORIZON,
                  site_name="Test oasis", flat={34: 80.0, 0: 60.0, 12: 90.0}, snow_free=None,
                  open={34: 70.0, 0: 50.0, 12: 85.0}, usable=None),
    "dry_valleys": dict(point=(-77.52, 161.6), region="Victoria Land", bare=0.8, snow=UNMEASURED, horizon=None,
                        flat={34: 100.0}, snow_free=None, open=None, usable=None),
}


def year_of(bins: dict | None) -> np.ndarray:
    values = np.full(36, np.nan) if bins is None else np.zeros(36)
    for b, value in (bins or {}).items():
        values[b] = value
    return values


def long_sum(hours: np.ndarray, stretch: np.ndarray, bins=None):
    if np.isnan(hours).all():
        return None
    keep = stretch >= 2.0
    if bins is not None:
        keep = keep & np.isin(np.arange(36), bins)
    return round(float(hours[keep].sum()), 1)


def long_part(hours: np.ndarray, stretch: np.ndarray, min_h: float = 2.0) -> np.ndarray:
    """The made-up long-window hours per bin: the bin's hours where its stretch reaches min_h; unknown stays unknown."""
    return np.where(np.isnan(hours), np.nan, np.where(stretch >= min_h, hours, 0.0))


def fake_long_window_hours_by_bin(root):
    """Stands in for grazing.long_window_hours_by_bin on the made-up project: the same rule as long_part."""
    def fake(cells, min_stretch_h=2.0, targets=None, inputs=None, **_):
        with np.load(root / "data" / "derived" / "grazing_bins.npz") as packed:
            archive = {name: packed[name] for name in packed.files}
        assert [c["id"] for c in cells] == archive["ids"].tolist()
        return {"ids": [c["id"] for c in cells], "targets": ["malapert"], "min_stretch_h": float(min_stretch_h),
                **{f"long_{kind}": long_part(archive[kind], archive["stretch"], min_stretch_h)
                   for kind in ("flat", "snow_free", "open")}}
    return fake


def best_bins(hours: np.ndarray, stretch: np.ndarray) -> list:
    order = sorted((b for b in range(36) if stretch[b] >= 2.0 and hours[b] > 0), key=lambda b: -hours[b])[:3]
    return [[b, float(hours[b])] for b in order]


def tiny_cell(spec: dict) -> tuple[dict, dict]:
    """A grazing_cells.json record and its rows for grazing_bins.npz, with every stored figure agreeing with the bins."""
    cid = grid.cell_id(*spec["point"])
    lat, lon = (round(v, 2) for v in grid.cell_centre(cid))
    south = lat < 0
    stretch = year_of(SOUTH_STRETCH if south else NORTH_STRETCH)
    rows = {"flat": year_of(spec["flat"]), "snow_free": year_of(spec["snow_free"]), "open": year_of(spec["open"]),
            "stretch": stretch}
    # version 3: long-window hours per bin are stored; here a bin counts whole when its stretch is at least 2 h
    rows.update({f"long_{kind}": long_part(rows[kind], stretch) for kind in ("flat", "snow_free", "open")})
    def total(kind):
        return None if np.isnan(rows[kind]).all() else round(float(rows[kind].sum()), 1)
    season = SUMMER_SOUTH if south else None
    values = {
        "flat_hours": total("flat"), "snow_free_hours": total("snow_free"), "open_hours": total("open"),
        "long_flat_hours": long_sum(rows["flat"], stretch), "long_snow_free_hours": long_sum(rows["snow_free"], stretch),
        "long_open_hours": long_sum(rows["open"], stretch),
        "long_snow_free_hours_winter": long_sum(rows["snow_free"], stretch, WINTER_NORTH),
        "long_snow_free_hours_summer": long_sum(rows["snow_free"], stretch, SUMMER_NORTH),
        "long_open_hours_winter": long_sum(rows["open"], stretch, WINTER_NORTH),
        "long_open_hours_summer": long_sum(rows["open"], stretch, SUMMER_NORTH),
        "long_snow_free_hours_as_mapped": long_sum(rows["snow_free"], stretch),
        "summer_rock_hours": round(float(rows["flat"][SUMMER_SOUTH].sum()), 1) if south else None,
        "long_summer_rock_hours": long_sum(rows["flat"], stretch, season) if south else None,
        "long_summer_rock_open_hours": long_sum(rows["open"], stretch, season) if south else None,
        "longest_stretch_h": float(stretch.max()), "best_stretch_bin": int(stretch.argmax()),
        "poleward_share": 0.2 if south else 0.9,
        "top_bins": best_bins(rows["flat"] if south else rows["open" if spec["open"] else "snow_free"]
                              if spec["snow_free"] else rows["flat"], stretch),
        "all_day_days": 0, "usable_days": spec["usable"],
    }
    record = {"id": cid, "lat": lat, "lon": lon, "hemisphere": "S" if south else "N", "region": spec["region"],
              "bare": spec["bare"], "land_share": 1.0, "cell_km2": 100.0, "bare_km2": round(100.0 * spec["bare"], 3),
              "layers_disagree": False if south else None, "gridded": spec.get("gridded", True),
              "site_name": spec.get("site_name"), "snow": spec["snow"], "horizon": spec["horizon"],
              "targets": {"malapert": values}}
    return record, rows


def tiny_cloud() -> dict:
    """Monthly cloud percent per nickname, January first. Cell b has no cloud record at all."""
    cloud = {name: [50.0] * 12 for name in TINY_CELLS if name != "b"}
    cloud["a"] = [50.0] * 5 + [75.0, 20.0] + [50.0] * 5       # June 75 %, July 20 %
    cloud["oasis"] = [50.0] * 11 + [60.0]                      # January 50 %, December 60 %
    return cloud


def tiny_project(root) -> dict:
    """Write a small made-up project under root; returns each nickname's grazing record."""
    derived, reference_dir = root / "data" / "derived", root / "data" / "reference"
    derived.mkdir(parents=True)
    reference_dir.mkdir(parents=True)
    built = {name: tiny_cell(spec) for name, spec in TINY_CELLS.items()}
    records = {name: record for name, (record, _) in built.items()}
    meta = {"targets": [TINY_TARGET], "stretch_min_h": 2.0, "bin_days": 10, "n_bins": 36,
            "winter_bins_north": WINTER_NORTH, "summer_bins_north": SUMMER_NORTH, "summer_bins_south": SUMMER_SOUTH,
            "snow_archive": "snow_free_dekads.npz", "horizons": 8}
    (derived / "grazing_cells.json").write_text(json.dumps({"meta": meta, "cells": list(records.values())}))
    np.savez(derived / "grazing_bins.npz", ids=np.array([r["id"] for r in records.values()]),
             targets=np.array(["malapert"]),
             **{kind: np.stack([rows[kind] for _, rows in built.values()])[:, None, :].astype(np.float32)
                for kind in ("flat", "snow_free", "open", "stretch", "long_flat", "long_snow_free", "long_open")})
    (derived / "cloud_cells.json").write_text(json.dumps({"meta": {"source": "made up"}, "cells": {
        records[name]["id"]: {"cloud_pct": pct, "grid": [0.5, 0.5]} for name, pct in tiny_cloud().items()}}))
    np.savez(derived / "snow_free_dekads.npz", probabilities=np.zeros((36, 3, 3), dtype=np.float32), row0=0, col0=0)
    (derived / "candidates.json").write_text(json.dumps(
        [{"id": r["id"], "lat": r["lat"], "lon": r["lon"], "hemisphere": r["hemisphere"],
          "why": ["all"] if name == "b" else ["sample"]} for name, r in records.items()]))
    land = {"median_slope_deg": 6.0, "p90_slope_deg": 20.0, "relief_m": 700.0, "valid_share": 1.0,
            "overlap": {"malapert": 0.4}}
    (derived / "terrain_cells.json").write_text(json.dumps({records["a"]["id"]: land, records["oasis"]["id"]: land}))
    (derived / "moon_targets.json").write_text(json.dumps(
        [{"id": "malapert", "terrain": {"90m": {"self_overlap_10km": {"p10": 0.6, "median": 0.8, "p90": 0.95}}}}]))
    (derived / "light_cells_v1.json").write_text(json.dumps(
        {records[name]["id"]: {"malapert": {"usable_days": days}, "_snow_land_pixels": 9}
         for name, days in (("a", 12.0), ("b", 3.0), ("doubtful", 30.0))}))
    (reference_dir / "anorthosite_bodies.json").write_text("[]")
    (reference_dir / "known_analogs.json").write_text("[]")
    (reference_dir / "antarctic_sites.json").write_text(json.dumps(
        [{"name": "Test oasis", "lat": -70.05, "lon": 20.0, "winter_snow_evidence": "no evidence",
          "existing_analog_use": None}]))
    return records


def table_row(text: str, record: dict) -> str | None:
    """The first line of a piece of ranking.txt that is this cell's table row."""
    place = f"{record['lat']:6.2f} {record['lon']:8.2f}"
    return next((line for line in text.split("\n") if place in line), None)


def test_score_cells_end_to_end_on_a_small_project(tmp_path, monkeypatch, capsys):
    cells = tiny_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    score_cells.main()
    capsys.readouterr()
    out = json.loads((tmp_path / "data/derived/cells_scored.json").read_text())
    scored_by_id = {r["id"]: r for r in out["cells"]}
    by_name = {name: scored_by_id[c["id"]] for name, c in cells.items()}
    assert len(out["cells"]) == len(cells) and out["meta"]["cells_from"] == "candidates.json"
    assert out["meta"]["full_hours"] == 200.0 and out["meta"]["rank_min_bare"] == 0.25

    # who is ranked, and why the others are not
    assert {name for name, r in by_name.items() if r["ranked"]} == {"a", "b", "haughton", "oasis"}
    assert by_name["doubtful"]["not_ranked_because"] == ["snow doubtful"]
    assert by_name["no_data"]["not_ranked_because"] == ["no snow data"]
    assert by_name["no_horizon"]["not_ranked_because"] == ["no horizon"]
    assert by_name["skipped"]["not_ranked_because"] == ["window across the antimeridian"]
    assert by_name["bear_island"]["not_ranked_because"] == ["named-site cell outside the screen", "snow doubtful"]
    assert by_name["jan_mayen"]["not_ranked_because"] == ["named-site cell outside the screen"]
    assert by_name["dry_valleys"]["not_ranked_because"] == ["no horizon"]
    assert out["meta"]["counts"]["ranked_north"] == 3 and out["meta"]["counts"]["ranked_south"] == 1
    assert out["meta"]["counts"]["with_a_horizon"] == 8

    # the scores
    a = by_name["a"]["targets"]["malapert"]
    assert a["light"] == pytest.approx(0.75) and a["light_flat"] == pytest.approx(0.85)
    assert a["terrain"] == pytest.approx(0.5) and a["terrain_overlap"] == pytest.approx(0.4)    # 0.4 against the median 0.8
    assert a["goals"]["lighting"] == pytest.approx((0.75 * 0.9) ** 0.5, abs=1e-3)
    unknown = by_name["no_horizon"]["targets"]["malapert"]
    assert unknown["light"] is None and unknown["goals"]["lighting"] is None and unknown["light_flat"] == 1.0
    assert by_name["no_data"]["targets"]["malapert"]["light"] is None
    assert by_name["no_data"]["targets"]["malapert"]["light_flat"] is None
    oasis = by_name["oasis"]["targets"]["malapert"]
    assert oasis["light"] == pytest.approx(0.6) and oasis["light_flat"] == pytest.approx(0.7)
    assert oasis["top_bins_summer_rock"] == [[34, 70.0], [0, 50.0]]          # the May bin is outside the rock season
    # the low Sun of the rock season at 70 S stands mostly in the south: midnight Sun in December and January,
    # and from early February sunsets and sunrises south of east and west (per-day spells, the whole season)
    assert 0.8 < oasis["poleward_share_summer_rock"] <= 1.0
    assert by_name["haughton"]["little_known"] is False and by_name["a"]["little_known"] is True
    assert by_name["dry_valleys"]["little_known"] is False

    # ranking.txt
    text = (tmp_path / "data/derived/ranking.txt").read_text()
    assert "PREVIEW" not in text
    north, rest = text.split("\nNORTH: measured cells with a horizon\n")[1].split("\nDOUBTFUL SNOW OR NO SNOW DATA")
    doubtful, rest = rest.split("\nNAMED SITES")
    named, south = rest.split("\nSOUTH: ")
    assert south.startswith("snow not measured: hours are for 27 November to 1 March, when the rock maps show the ground bare\n")
    assert "light = min(1, long_summer_rock_open_hours / 200)" in south
    for name in ("a", "b", "haughton"):
        assert table_row(north, by_name[name]) is not None and table_row(south, by_name[name]) is None
    for name in ("doubtful", "no_data", "no_horizon", "skipped", "bear_island", "jan_mayen", "oasis", "dry_valleys"):
        assert table_row(north, by_name[name]) is None, name
    row = table_row(north, by_name["a"])
    assert "20 Jun-29 Jun (100 h), 30 Jun-9 Jul (50 h)" in row and "90% midnight-Sun side (Sun in the north)" in row
    assert "KNOWN AREA: Devon Island" in table_row(north, by_name["haughton"])
    assert table_row(south, by_name["oasis"]) is not None and table_row(south, by_name["dry_valleys"]) is None
    row = table_row(south, by_name["oasis"])
    assert "7 Dec-16 Dec (70 h), 1 Jan-10 Jan (50 h)" in row and "May" not in row
    assert "midnight-Sun side (Sun in the south)" in row

    # the doubtful table: gridded doubtful and no-data cells only, unknown hours as a dash
    assert doubtful.startswith(": 2 gridded cells")
    assert table_row(doubtful, by_name["doubtful"]) is not None and table_row(doubtful, by_name["bear_island"]) is None
    row = table_row(doubtful, by_name["no_data"])
    assert row is not None and row.rstrip().endswith("-/     -/     -")
    assert table_row(doubtful, by_name["doubtful"]).rstrip().endswith("210/   210/   200")
    assert "Bear Island, Norway | cell" in named and "Test oasis | cell" in named
    assert "not ranked: named-site cell outside the screen, snow doubtful" in named


# ---- a table that is cut among equal scores ----

def test_a_full_table_that_ends_among_equal_scores_is_found():
    cells = [{"id": str(k), "lat": 60.0 + k, "lon": 0.0, "s": 1.0 if k < 14 else 0.5} for k in range(20)]

    def key(c):
        return c["s"]

    assert score_cells.cut_tie(cells, score.top_sites(cells, key, top=10), key, top=10) == (1.0, 14)
    fewer = cells[:10] + cells[14:]       # exactly ten cells at 1.0: all of them are shown
    assert score_cells.cut_tie(fewer, score.top_sites(fewer, key, top=10), key, top=10) is None
    assert score_cells.cut_tie(cells[:5], score.top_sites(cells[:5], key, top=10), key, top=10) is None   # not a full table


def test_the_ranking_table_says_when_its_last_places_are_a_tie():
    def table(count):
        records = [scored(grazing_cell(id=str(k), lat=60.05 + k, lon=20.15, bare=1.0, hours={"long_open_hours": 200.0 + k}))
                   for k in range(count)]
        return score_cells.ranking_table(records, TARGET, "lighting", "north")
    note = [line for line in table(12) if line.strip().startswith("note:")]
    assert len(note) == 1 and "12 ranked cells share the score 1.000" in note[0] and "fewer" in note[0]
    assert not [line for line in table(10) if line.strip().startswith("note:")]


# --- added in the final step ---

def test_equal_scores_can_be_ordered_by_a_second_key_that_never_outranks_the_score():
    cells = [{"id": str(k), "lat": 60.0 + k, "lon": 0.0, "s": 1.0, "h": 200.0 + k} for k in range(5)]
    cells.append({"id": "low", "lat": 70.0, "lon": 0.0, "s": 0.9, "h": 999.0})

    def by_score(c):
        return c["s"]

    assert [c["id"] for c in score.top_sites(cells, by_score, top=3)] == ["0", "1", "2"]          # the order given
    assert [c["id"] for c in score.top_sites(cells, by_score, top=3, tie_key=lambda c: c["h"])] == ["4", "3", "2"]
    assert [c["id"] for c in score.top_sites(cells, by_score, top=6, tie_key=lambda c: c["h"])][-1] == "low"
    assert [c["id"] for c in score.cluster_sites(cells, by_score, limit=2, tie_key=lambda c: c["h"])] == ["4", "3"]


def test_a_ranking_table_puts_the_cell_with_more_hours_first_among_equal_scores():
    records = [scored(grazing_cell(id=str(k), lat=60.05 + k, lon=20.15, bare=1.0, hours={"long_open_hours": 200.0 + k}))
               for k in range(12)]
    shown = score_cells.ranked_sites(records, "malapert", "lighting", "north")
    assert [r["id"] for r in shown] == [str(k) for k in range(11, 1, -1)]         # 211 h down to 202 h
    flat = [scored(grazing_cell(id=str(k), lat=60.05 + k, lon=20.15, bare=1.0, horizon=None,
                                hours={"long_open_hours": None, "long_snow_free_hours": 300.0 - k})) for k in range(3)]
    assert [r["id"] for r in score_cells.ranked_sites(flat, "malapert", "lighting", "north", flat=True)] == ["0", "1", "2"]
    note = [line for line in score_cells.ranking_table(records, TARGET, "lighting", "north") if "note:" in line]
    assert len(note) == 1 and "more long-window hours" in note[0] and "file" not in note[0]


def test_a_cell_on_an_anorthosite_body_already_in_use_is_not_little_known():
    def build(**extra):
        body = {"name": "Test mine", "lat": 67.05, "lon": -50.75, "radius_km": 5, "an_low": 80, "an_high": 83, **extra}
        return score_cells.scored_record(grazing_cell(lat=67.05, lon=-50.75, region="Greenland"), None, [TARGET],
                                         SELF_OVERLAP, bodies=[body], known_sites=[], south_sites=[])
    used = build(novel=False, existing_use="simulant feedstock")
    assert used["little_known"] is False and used["known_region"] == "Test mine: simulant feedstock"
    assert build(novel=True, existing_use="none found")["little_known"] is True
    assert build()["little_known"] is True                                        # a body without the flag is not held back


def test_a_best_bin_with_under_an_hour_is_not_printed_as_zero_hours():
    assert score_cells.bins_note([[17, 40.0], [33, 0.3]]) == "20 Jun-29 Jun (40 h), 27 Nov-6 Dec (0.3 h)"
    assert score_cells.bins_note([[33, 0.96]]) == "27 Nov-6 Dec (1.0 h)"
    assert score_cells.bins_note([]) == "none"


# ---- version 3: cloud column, tiles held back, files of the new method ----

import re  # noqa: E402


def test_clear_sky_hours_are_each_bins_hours_times_its_clear_share():
    hours, share = [0.0] * 36, [0.5] * 36
    hours[17], hours[18], share[18] = 40.0, 20.0, 0.25
    assert score.clear_hours(hours, share) == pytest.approx(25.0)
    assert score.clear_hours(hours, share, bins=[18, 19]) == pytest.approx(5.0)
    assert score.clear_hours(hours, share, bins=[0, 1]) == 0.0


def test_clear_sky_hours_are_unknown_not_zero_when_hours_or_cloud_are_unknown():
    hours, share = [0.0] * 36, [0.5] * 36
    hours[17] = 40.0
    no_cloud_there = list(share)
    no_cloud_there[17] = None
    assert score.clear_hours(hours, no_cloud_there) is None
    assert score.clear_hours(hours, no_cloud_there, bins=[0, 1]) == 0.0      # the unknown bin is not counted
    no_cloud_elsewhere = list(share)
    no_cloud_elsewhere[3] = None
    assert score.clear_hours(hours, no_cloud_elsewhere) == pytest.approx(20.0)   # no hours there, nothing to lose
    assert score.clear_hours([float("nan")] * 36, share) is None
    unknown_bin = list(hours)
    unknown_bin[20] = float("nan")
    assert score.clear_hours(unknown_bin, share) is None
    assert score.clear_hours(hours, [None] * 36) is None
    assert score.clear_hours(None, share) is None and score.clear_hours(hours, None) is None


def test_a_horizon_held_back_for_a_missing_tile_is_one_reason_whatever_the_tile():
    def held(tile):
        return cell(horizon={"skipped": f"tile not fetched: https://example.org/{tile}.tif (downloads were off in "
                                        "this run; 1 of the cell's 4 tiles are new)"})
    assert score.not_ranked_because(held("a")) == score.not_ranked_because(held("b")) == ["no horizon: tile not fetched"]
    assert score.not_ranked_because(cell(horizon={"skipped": "no land pixels"})) == ["no horizon: no land pixels"]


def test_terrain_held_back_for_a_missing_tile_is_not_called_a_refused_window():
    held = {"skipped": "tile not fetched: https://example.org/a.tif (downloads were off in this run)"}
    assert score_cells.terrain_parts(held) == (None, "not computed: tile not fetched")
    refused = score_cells.terrain_parts({"skipped": "window crosses the antimeridian"})
    assert refused == (None, "window refused: window crosses the antimeridian")


def test_results_of_the_new_method_are_never_renamed(tmp_path):
    new = {"cells_scored.json": '{"meta": {}, "cells": []}', "validation.json": '{"meta": {}, "checks": []}',
           "ranking.txt": "LuniMartian Atlas ranking, written 2026-11-14T16:30:00.\n"}
    for name, text in new.items():
        (tmp_path / name).write_text(text)
    assert score_cells.keep_old_results(tmp_path) == []       # no _v1 copy exists, and still nothing is renamed
    for name, text in new.items():
        assert (tmp_path / name).read_text() == text
    assert not list(tmp_path.glob("*_v1.*"))


def test_a_first_method_file_is_told_from_a_new_one(tmp_path):
    def first(name, text):
        (tmp_path / name).write_text(text)
        return score_cells.from_first_method(tmp_path / name)
    assert first("cells_scored.json", "[]") is True
    assert first("cells_scored.json", '{"meta": {}, "cells": []}') is False
    assert first("validation.json", '{"qaqortorsuaq": {}}') is True
    assert first("validation.json", '{"meta": {}}') is False
    assert first("ranking.txt", "scored cells: 1053; wrote data/derived/cells_scored.json\n") is True
    assert first("ranking.txt", "LuniMartian Atlas ranking, written 2026-11-14T14:39:00.\n") is False
    assert first("cells_scored.json", "{ not json") is False          # a file that cannot be read is left alone


def scored_tiny(tmp_path, monkeypatch, capsys):
    cells = tiny_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    score_cells.main()
    capsys.readouterr()
    out = json.loads((tmp_path / "data/derived/cells_scored.json").read_text())
    scored_by_id = {r["id"]: r for r in out["cells"]}
    return {name: scored_by_id[c["id"]] for name, c in cells.items()}, out


def test_score_cells_joins_the_cloud_column(tmp_path, monkeypatch, capsys):
    by_name, out = scored_tiny(tmp_path, monkeypatch, capsys)
    assert by_name["a"]["cloud"] == {"pct_by_month": [50.0] * 5 + [75.0, 20.0] + [50.0] * 5, "grid": [0.5, 0.5]}
    a = by_name["a"]["targets"]["malapert"]
    # long open hours: 100 h in bin 17 (June, a quarter of the sky clear) and 50 h in bin 18 (July, four fifths clear)
    assert a["long_open_hours_clear"] == 65.0
    assert a["long_open_hours_clear_summer"] == 65.0 and a["long_open_hours_clear_winter"] == 0.0
    assert a["long_summer_rock_open_hours_clear"] is None
    assert by_name["b"]["cloud"] == {"pct_by_month": None, "grid": None}       # no cloud record: unknown, never 0
    assert by_name["b"]["targets"]["malapert"]["long_open_hours_clear"] is None
    assert by_name["no_horizon"]["cloud"]["pct_by_month"] == [50.0] * 12
    assert by_name["no_horizon"]["targets"]["malapert"]["long_open_hours_clear"] is None    # open hours unknown
    oasis = by_name["oasis"]["targets"]["malapert"]
    assert oasis["long_summer_rock_open_hours_clear"] == 53.0      # 70 h in December at 40 % clear, 50 h in January at 50 %
    assert oasis["long_open_hours_clear"] is None                  # open hours of the south are kept in the rock-season field
    assert "cloud" in out["meta"] and out["meta"]["cloud"]["enters_a_score"] is False


def test_the_cloud_column_enters_no_score(tmp_path, monkeypatch, capsys):
    with_cloud, _ = scored_tiny(tmp_path, monkeypatch, capsys)
    (tmp_path / "data/derived/cloud_cells.json").unlink()
    score_cells.main()
    capsys.readouterr()
    without = {r["id"]: r for r in json.loads((tmp_path / "data/derived/cells_scored.json").read_text())["cells"]}
    for name, r in with_cloud.items():
        other = without[r["id"]]["targets"]["malapert"]
        assert other["goals"] == r["targets"]["malapert"]["goals"], name
        assert other["light"] == r["targets"]["malapert"]["light"]
        assert other["long_open_hours_clear"] is None and without[r["id"]]["cloud"] == {"pct_by_month": None, "grid": None}
        assert without[r["id"]]["ranked"] == r["ranked"]


def test_ranking_txt_prints_the_clear_sky_hours_as_a_column(tmp_path, monkeypatch, capsys):
    by_name, _ = scored_tiny(tmp_path, monkeypatch, capsys)
    text = (tmp_path / "data/derived/ranking.txt").read_text()
    assert score_cells.TABLE_HEAD.split()[5:8] == ["hours", "flat", "clear"]
    assert "clear   " in text and "not the chance that a low Sun is visible" in text
    north = text.split("\nNORTH: measured cells with a horizon\n")[1].split("\nDOUBTFUL SNOW")[0]
    assert re.search(r"0\.90\s+150\s+170\s+65\s", table_row(north, by_name["a"]))          # open, flat, clear-sky hours
    assert re.search(r"0\.50\s+100\s+120\s+-\s", table_row(north, by_name["b"]))           # unknown cloud prints a dash
    south = text.split("\nSOUTH: ")[1]
    assert re.search(r"0\.80\s+120\s+140\s+53\s", table_row(south, by_name["oasis"]))


def test_the_doubtful_table_prints_the_with_rule_figure_where_the_cells_file_names_it():
    doubtful = grazing_cell(snow={"status": "doubtful", "source": "3x3", "land_pixels": 9, "stuck_winters": 2},
                            hours={"long_snow_free_hours": 180.0, "long_snow_free_hours_with_rule": 177.0,
                                   "long_snow_free_hours_as_mapped": 230.0})
    lines = score_cells.doubtful_table([doubtful], [TARGET])
    assert lines[-1].rstrip().endswith("177/   230/   100")


# ---- added by the count check of version 3 (breakages that no test caught)

def test_clear_sky_hours_are_split_between_the_winter_half_and_the_summer_half(tmp_path):
    hours = np.zeros((1, 1, 36), dtype=np.float32)
    hours[0, 0, 2], hours[0, 0, 17] = 40.0, 100.0           # 40 h in January, 100 h in June
    np.savez(tmp_path / "bins.npz", ids=np.array(["a"]), long_open=hours)
    meta = {"targets": [{"id": "malapert"}], "winter_bins_north": [0, 1, 2, 33, 34, 35],
            "summer_bins_north": [15, 16, 17], "summer_bins_south": [0, 1]}
    record = {"id": "a", "hemisphere": "N", "targets": {"malapert": {}}}
    cloudy = {"a": {"cloud_pct": [50.0] * 5 + [75.0] + [50.0] * 6, "grid": [0.5, 0.5]}}   # June: a quarter of the sky clear
    score_cells.add_cloud([record], meta, tmp_path / "bins.npz", cloudy)
    t = record["targets"]["malapert"]
    assert (t["long_open_hours_clear_winter"], t["long_open_hours_clear_summer"], t["long_open_hours_clear"]) == (20.0, 25.0, 45.0)
    assert t["long_summer_rock_open_hours_clear"] is None


def test_a_little_known_table_holds_no_known_cell():
    def rec(cid, lat, lon, goal, little):
        return {"id": cid, "lat": lat, "lon": lon, "hemisphere": "N", "ranking": "north", "ranked": True, "ranked_flat": True,
                "little_known": little, "targets": {"t": {"goals": {"lighting": goal}, "goals_flat": {"lighting": goal},
                                                          "long_open_hours": 100.0, "long_snow_free_hours": 100.0}}}
    records = [rec("known", 64.0, -20.0, 0.9, False), rec("new", 70.0, 30.0, 0.5, True)]
    assert [r["id"] for r in score_cells.ranked_sites(records, "t", "lighting", "north", little_known_only=True)] == ["new"]
    assert [r["id"] for r in score_cells.ranked_sites(records, "t", "lighting", "north")] == ["known", "new"]


def test_the_thin_snow_note_starts_under_seven_land_pixels():
    def notes(pixels):
        return score_cells.row_notes({"rock": {"body": None}, "known": None, "known_region": None, "layers_disagree": None,
                                      "terrain_note": None, "snow": {"land_pixels": pixels, "block_pixels": 9}})
    assert notes(7) == "" and notes(6) == "snow odds thin (6 of 9 pixels)"


def test_the_southern_sun_side_uses_the_calendars_and_step_of_the_cells_file(tmp_path, monkeypatch):
    # The Sun's side in the rock season is read from sun.long_band_minutes_table, beside hours that the cells file made
    # with its own meta.year_phases and meta.step_minutes: the table must be asked for the same, not for the default.
    from twinfinder import sun
    asked = []

    def spy(lats, limits, min_stretch_h=2.0, step_minutes=1, refraction=True, year_phases=sun.YEAR_PHASES):
        asked.append((min_stretch_h, step_minutes, year_phases))
        return np.zeros((len(limits), len(lats), 36, 36, 9), dtype=np.float32)

    monkeypatch.setattr(sun, "long_band_minutes_table", spy)
    bins = tmp_path / "grazing_bins.npz"
    np.savez(bins, ids=np.array(["-70.0_10.0"]), long_flat=np.ones((1, 1, 36), np.float32),
             long_open=np.full((1, 1, 36), np.nan, np.float32))
    meta = {"targets": [TINY_TARGET], "stretch_min_h": 2.0, "summer_bins_south": SUMMER_SOUTH, "step_minutes": 2,
            "year_phases": 3}

    def record():
        return {"id": "-70.0_10.0", "hemisphere": "S", "lat": -70.0, "targets": {"malapert": {}}}
    score_cells.add_southern_summer([record()], meta, bins)
    assert asked == [(2.0, 2, 3)]
    asked.clear()
    del meta["year_phases"], meta["step_minutes"]          # a cells file from before the phases: one calendar, 1-minute steps
    score_cells.add_southern_summer([record()], meta, bins)
    assert asked == [(2.0, 1, 1)]

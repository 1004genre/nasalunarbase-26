# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
import math

import numpy as np
import pytest
from twinfinder import grazing, horizon, sun

NAN = math.nan

# A table small enough to work out by hand: 2 ten-day bins, 2 azimuth sectors, 3 elevation bins.
# The target uses elevation bins 0 and 1; the 99s sit above its limit and must never be counted.
MINUTES = np.array([[[60.0, 30.0, 99.0], [0.0, 30.0, 99.0]],
                    [[120.0, 0.0, 99.0], [60.0, 60.0, 99.0]]])
BINS = [0, 1]
OPEN_SHARE = np.array([[1.0, 0.5, 0.0], [0.0, 1.0, 0.0]])


def test_sun_and_horizon_use_the_same_sectors_and_elevation_bins():
    assert horizon.AZ_SECTORS == sun.AZ_SECTORS == 36
    assert list(horizon.ELEV_EDGES_DEG) == list(sun.ELEV_EDGES_DEG)
    grazing.check_shared_bins()  # the join refuses to run if the two ever drift apart


def test_each_target_uses_the_elevation_bins_up_to_its_limit():
    assert grazing.target_limit(2.076837165962993) == 2.08
    assert grazing.target_limit(5.545215316439248) == 5.55
    assert grazing.elev_bins(2.08) == [0, 1, 2, 3]
    assert grazing.elev_bins(5.55) == [0, 1, 2, 3, 4, 5, 6]
    assert grazing.elev_bins(6.11) == [0, 1, 2, 3, 4, 5, 6, 7]
    assert grazing.elev_bins(7.59) == [0, 1, 2, 3, 4, 5, 6, 7, 8]
    assert grazing.elev_bins(2.07) == [0, 1, 2]       # the bin that ends at 2.08 reaches above 2.07
    assert grazing.elev_bins(2.076) == [0, 1, 2, 3]   # within the 0.005 allowance


def test_the_four_targets_are_read_from_the_fingerprint_file():
    targets = grazing.load_targets()
    assert [t["id"] for t in targets] == ["connecting-ridge", "malapert", "mons-mouton", "nobile-rim-2"]
    assert [t["limit_deg"] for t in targets] == [2.08, 5.55, 6.11, 7.59]
    assert [len(t["elev_bins"]) for t in targets] == [4, 7, 8, 9]
    assert all(t["name"] for t in targets)


def test_flat_hours_sum_the_sectors_and_the_targets_elevation_bins():
    assert grazing.flat_hours(MINUTES, BINS).tolist() == [2.0, 4.0]          # (60+30+0+30)/60, (120+0+60+60)/60


def test_snow_free_hours_are_flat_hours_times_the_odds_of_the_bin():
    flat = grazing.flat_hours(MINUTES, BINS)
    assert grazing.snow_free_hours(flat, np.array([0.5, 0.25])).tolist() == [1.0, 1.0]


def test_open_hours_weigh_each_sector_and_elevation_bin_by_its_open_share():
    terrain_only = grazing.open_hours(MINUTES, BINS, OPEN_SHARE)
    assert terrain_only.tolist() == [1.75, 3.0]       # (60*1 + 30*0.5 + 0*0 + 30*1)/60, (120*1 + 0 + 60*0 + 60*1)/60
    with_snow = grazing.open_hours(MINUTES, BINS, OPEN_SHARE, np.array([0.5, 0.25]))
    assert with_snow.tolist() == [0.875, 0.75]
    assert with_snow.tolist() == grazing.snow_free_hours(terrain_only, np.array([0.5, 0.25])).tolist()


def test_a_fully_open_cell_has_the_flat_hours():
    assert grazing.open_hours(MINUTES, BINS, np.ones((2, 3))).tolist() == grazing.flat_hours(MINUTES, BINS).tolist()


def test_the_functions_take_many_cells_at_once():
    many = np.stack([MINUTES, 2 * MINUTES])
    assert grazing.flat_hours(many, BINS).tolist() == [[2.0, 4.0], [4.0, 8.0]]
    shares = np.stack([OPEN_SHARE, np.ones((2, 3))])
    assert grazing.open_hours(many, BINS, shares).tolist() == [[1.75, 3.0], [4.0, 8.0]]


def test_unknown_snow_gives_unknown_hours_not_zero():
    out = grazing.snow_free_hours(np.array([2.0, 4.0]), np.array([0.5, NAN]))
    assert out[0] == 1.0 and math.isnan(out[1])
    assert math.isnan(grazing.total(out))             # a year with an unknown part is unknown
    assert grazing.total(out, [0]) == 1.0             # the known part still adds up


def test_no_sun_means_no_hours_even_where_the_snow_was_never_seen():
    # Polar night: the snow maps see nothing, but there is no Sun to lose either.
    out = grazing.snow_free_hours(np.array([0.0, 4.0]), np.array([NAN, 0.5]))
    assert out.tolist() == [0.0, 2.0]


def test_a_cell_without_any_snow_odds_stays_unknown_in_every_bin():
    out = grazing.snow_free_hours(np.array([0.0, 4.0]), np.array([NAN, NAN]))
    assert np.isnan(out).all()


def test_the_old_bin_rule_is_kept_for_the_comparison_thresholds():
    # Version 2 called a whole ten-day bin a long window when its median longest stretch reached two hours.
    # Nothing in the cells file is gated by it any more (see the per-day tests below).
    assert grazing.STRETCH_MIN_H == 2.0 and grazing.LONG_RULE == "per-day spells"
    stretch = np.array([0.0, 1.97, 2.0, 2.03, 24.0])
    assert grazing.long_bins(stretch).tolist() == [False, False, True, True, True]
    assert grazing.long_bins(stretch, 3.0).tolist() == [False, False, False, False, True]
    assert grazing.long_bins(stretch, 1.0).tolist() == [False, True, True, True, True]


def test_season_bins_follow_the_calendar():
    assert grazing.WINTER_BINS_NORTH == list(range(27, 36)) + list(range(0, 9))
    assert grazing.SUMMER_BINS_NORTH == list(range(9, 27))
    assert grazing.SUMMER_BINS_SOUTH == [33, 34, 35, 0, 1, 2, 3, 4, 5]
    assert sorted(grazing.WINTER_BINS_NORTH + grazing.SUMMER_BINS_NORTH) == list(range(36))
    assert sun.bin_index(271) == 27 and sun.bin_index(90) == 8      # 28 September and 31 March
    assert sun.bin_index(91) == 9 and sun.bin_index(270) == 26      # 1 April and 27 September
    assert sun.bin_index(331) == 33 and sun.bin_index(60) == 5      # 27 November and 1 March
    assert sun.bin_index(330) == 32 and sun.bin_index(61) == 6


def test_total_adds_only_the_bins_asked_for():
    hours = np.arange(36.0)
    assert grazing.total(hours) == 630.0
    assert grazing.total(hours, grazing.SUMMER_BINS_NORTH) == sum(range(9, 27))
    keep = np.zeros(36, dtype=bool)
    keep[[2, 30]] = True
    assert grazing.total(hours, keep) == 32.0
    assert grazing.total(hours, np.zeros(36, dtype=bool)) == 0.0    # no bin asked for: a known zero
    assert grazing.total(np.stack([hours, 2 * hours]), [1, 2]).tolist() == [3.0, 6.0]


def test_poleward_side_is_north_for_northern_cells_and_south_for_southern_ones():
    assert grazing.poleward_sectors("N") == list(range(0, 9)) + list(range(27, 36))
    assert grazing.poleward_sectors("S") == list(range(9, 27))


def test_poleward_share_counts_long_window_minutes_on_the_poleward_side():
    minutes = np.zeros((36, 36, 9))
    minutes[17, 0, 0] = 90.0     # late June, Sun due north: midnight Sun for a northern cell
    minutes[17, 18, 0] = 30.0    # late June, Sun due south
    minutes[3, 18, 0] = 500.0    # a bin that is not a long window: left out
    minutes[17, 0, 8] = 999.0    # above the target's limit: left out
    long = np.zeros(36, dtype=bool)
    long[17] = True
    assert grazing.poleward_share(minutes, [0, 1], long, "N") == pytest.approx(0.75)
    assert grazing.poleward_share(minutes, [0, 1], long, "S") == pytest.approx(0.25)
    assert math.isnan(grazing.poleward_share(minutes, [0, 1], np.zeros(36, dtype=bool), "N"))  # no long hours: no share
    # A table that already holds long-spell minutes only is counted whole: no bin mask.
    assert grazing.poleward_share(minutes, [0, 1], None, "N") == pytest.approx(90.0 / 620.0)
    assert grazing.poleward_share(minutes, [0, 1], hemisphere="S") == pytest.approx(530.0 / 620.0)


def north_wall() -> np.ndarray:
    """Open share of a cell with a high wall all along its northern side and open ground to the south."""
    share = np.ones((36, 9))
    share[grazing.poleward_sectors("N")] = 0.0
    return share


def test_a_wall_to_the_north_of_a_northern_cell_removes_midnight_sun_not_noon_sun():
    minutes = sun.band_minutes_table([69.0])[0]
    bins = grazing.elev_bins(5.55)
    flat = grazing.flat_hours(minutes, bins)
    behind_wall = grazing.open_hours(minutes, bins, north_wall())
    late_june, mid_february = 17, 4
    assert flat[late_june] > 20.0 and behind_wall[late_june] == 0.0             # the midnight Sun is in the north
    assert flat[mid_february] > 20.0
    assert behind_wall[mid_february] == pytest.approx(flat[mid_february])       # the low noon Sun is in the south
    south_wall = 1.0 - north_wall()
    assert grazing.open_hours(minutes, bins, south_wall)[mid_february] == 0.0
    assert grazing.open_hours(minutes, bins, south_wall)[late_june] == pytest.approx(flat[late_june])


def test_a_wall_to_the_south_of_a_southern_cell_removes_its_midnight_sun():
    minutes = sun.band_minutes_table([-69.0])[0]
    bins = grazing.elev_bins(5.55)
    flat = grazing.flat_hours(minutes, bins)
    wall = np.ones((36, 9))
    wall[grazing.poleward_sectors("S")] = 0.0
    late_december = 35
    assert flat[late_december] > 20.0
    assert grazing.open_hours(minutes, bins, wall)[late_december] == 0.0
    long_minutes = sun.long_band_minutes_table([-69.0], [5.55])[0, 0]
    assert grazing.poleward_share(long_minutes, bins, None, "S") > grazing.poleward_share(long_minutes, bins, None, "N")


def test_snow_status_rules_at_their_edges():
    assert grazing.snow_status("N", "3x3", 0, 70.0) == "measured"
    assert grazing.snow_status("N", "5x5", 0, 70.0) == "measured"
    assert grazing.snow_status("N", "3x3", 1, 67.4) == "doubtful"      # polar night starts here
    assert grazing.snow_status("N", "3x3", 1, 67.39) == "measured"
    assert grazing.snow_status("N", "3x3", 2, 60.0) == "measured"
    assert grazing.snow_status("N", "3x3", 3, 60.0) == "doubtful"      # three stuck winters anywhere
    assert grazing.snow_status("N", "3x3", 1, 80.0) == "doubtful"
    assert grazing.snow_status("N", None, 0, 60.0) == "no data"
    assert grazing.snow_status("N", None, 5, 80.0) == "no data"
    assert grazing.snow_status("S", None, 0, -70.0) == "unmeasured"
    assert grazing.snow_status("S", "3x3", 0, -70.0) == "unmeasured"   # no product measures the south, whatever is passed


def test_usable_days_weigh_each_low_sun_day_by_the_odds_of_its_bin():
    per_bin = grazing.days_per_bin([1, 2, 11, 365])
    assert per_bin.shape == (36,) and per_bin.sum() == 4
    assert (per_bin[0], per_bin[1], per_bin[35]) == (2, 1, 1)
    odds = np.full(36, NAN)
    odds[[0, 1, 35]] = [0.5, 1.0, 0.25]
    assert grazing.usable_days(per_bin, odds) == pytest.approx(2 * 0.5 + 1.0 + 0.25)
    odds[35] = NAN
    assert math.isnan(grazing.usable_days(per_bin, odds))              # one day's snow unknown: the sum is unknown
    assert grazing.usable_days(grazing.days_per_bin([]), odds) == 0.0  # no low-Sun days: a known zero
    assert math.isnan(grazing.usable_days(per_bin, np.full(36, NAN)))


def test_best_stretch_is_the_longest_ten_day_median_and_its_bin():
    stretch = np.zeros(36)
    stretch[[4, 30]] = [5.5, 5.75]
    assert grazing.best_stretch(stretch) == (5.75, 30)
    assert grazing.best_stretch(np.zeros(36)) == (0.0, None)


def test_top_bins_are_the_three_long_window_bins_with_most_hours():
    hours = np.zeros(36)
    hours[[2, 5, 7, 9, 20]] = [10.0, 30.04, 20.0, 99.0, NAN]
    long = np.zeros(36, dtype=bool)
    long[[2, 5, 7, 20, 21]] = True          # bin 9 is not a long window, bin 20 is unknown, bin 21 has nothing
    assert grazing.top_bins(hours, long) == [[5, 30.0], [7, 20.0], [2, 10.0]]
    assert grazing.top_bins(hours, np.zeros(36, dtype=bool)) == []
    assert grazing.top_bins(hours) == [[9, 99.0], [5, 30.0], [7, 20.0]]   # long-spell hours need no mask


LONG_SHARE = 0.4      # in the made-up cells, this part of a bin's low-Sun hours lies in long spells ...
LONG_IN = [0, 1, 2, 3, 4, 5, 16, 17, 18, 19]   # ... in these bins, and none of it in the others


def long_part(hours):
    """The long-spell part of made-up hours [cells, 36]."""
    return np.where(grazing.bin_mask(LONG_IN), LONG_SHARE * np.asarray(hours, dtype=float), 0.0)


def one_cell(hemisphere, odds=None, terrain=None, as_mapped=None, with_rule=None):
    """Sums for one made-up cell: one flat hour per bin number, four tenths of it in long spells in ten of the bins."""
    flat = np.arange(36.0)[None, :]
    stretch = np.zeros((1, 36))
    stretch[0, LONG_IN] = 3.0
    stretch[0, 17] = 6.0
    unknown = np.full((1, 36), NAN)
    terrain = unknown if terrain is None else terrain
    sums = grazing.target_sums(hemisphere, flat, long_part(flat), terrain, long_part(terrain), stretch,
                               unknown if odds is None else odds,
                               unknown if as_mapped is None else as_mapped,
                               unknown if with_rule is None else with_rule)
    return grazing.rows(sums)[0]


def test_sums_for_a_northern_cell_with_snow_and_horizon():
    odds = np.full((1, 36), 0.5)
    row = one_cell("N", odds=odds, terrain=np.arange(36.0)[None, :] * 0.2, as_mapped=np.ones((1, 36)),
                   with_rule=np.full((1, 36), 0.25))
    winter_long, summer_long = 0.4 * (0 + 1 + 2 + 3 + 4 + 5), 0.4 * (16 + 17 + 18 + 19)    # 6 and 28 flat hours
    assert row["flat_hours"] == 630.0
    assert row["snow_free_hours"] == 315.0                 # flat times 0.5
    assert row["open_hours"] == 63.0                       # terrain keeps 0.2, snow keeps 0.5 of that
    assert row["long_flat_hours"] == 34.0                  # not 85: only the part of each bin that lies in long spells
    assert row["long_snow_free_hours"] == 17.0
    assert row["long_snow_free_hours_winter"] == 3.0
    assert row["long_snow_free_hours_summer"] == 14.0
    assert row["long_open_hours"] == 3.4
    assert row["long_open_hours_winter"] == 0.6
    assert row["long_open_hours_summer"] == 2.8
    assert row["long_snow_free_hours_as_mapped"] == pytest.approx(winter_long + summer_long)
    assert row["long_snow_free_hours_with_rule"] == 8.5    # the same long hours with the other odds
    assert (row["longest_stretch_h"], row["best_stretch_bin"]) == (6.0, 17)
    assert row["summer_rock_hours"] is None and row["long_summer_rock_hours"] is None
    assert row["long_summer_rock_open_hours"] is None


def test_the_bin_median_stretch_gates_nothing():
    # A bin whose median stretch is short still gives its long-spell hours, and a bin with a long median gives
    # only the hours that lie in long spells: version 2 did the opposite on both counts.
    flat = np.full((1, 36), 10.0)
    long_flat = np.zeros((1, 36))
    long_flat[0, [3, 20]] = [4.0, 6.0]
    stretch = np.zeros((1, 36))
    stretch[0, 20], stretch[0, 30] = 1.5, 5.0
    odds, unknown = np.full((1, 36), 0.5), np.full((1, 36), NAN)
    row = grazing.rows(grazing.target_sums("N", flat, long_flat, unknown, unknown, stretch, odds, unknown, unknown))[0]
    assert row["long_flat_hours"] == 10.0 and row["long_snow_free_hours"] == 5.0
    assert (row["long_snow_free_hours_winter"], row["long_snow_free_hours_summer"]) == (2.0, 3.0)
    assert (row["longest_stretch_h"], row["best_stretch_bin"]) == (5.0, 30)      # kept for information


def test_unknown_snow_and_missing_horizon_are_null_not_zero():
    row = one_cell("N")                                    # no snow odds, no horizon
    assert row["flat_hours"] == 630.0 and row["long_flat_hours"] == 34.0
    for field in ("snow_free_hours", "long_snow_free_hours", "long_snow_free_hours_winter",
                  "long_snow_free_hours_summer", "long_snow_free_hours_as_mapped", "long_snow_free_hours_with_rule",
                  "open_hours", "long_open_hours", "long_open_hours_winter", "long_open_hours_summer"):
        assert row[field] is None, field
    with_snow = one_cell("N", odds=np.full((1, 36), 0.5))  # snow odds but no horizon
    assert with_snow["long_snow_free_hours"] == 17.0
    assert with_snow["open_hours"] is None and with_snow["long_open_hours"] is None
    assert with_snow["long_snow_free_hours_as_mapped"] is None   # the archive had no as-mapped odds


def test_long_hours_are_unknown_only_when_a_bin_with_long_hours_has_unknown_snow():
    odds = np.full((1, 36), 0.5)
    odds[0, 10] = NAN                                      # a bin without long-spell hours: nothing is lost
    assert one_cell("N", odds=odds)["long_snow_free_hours"] == 17.0
    assert one_cell("N", odds=odds)["snow_free_hours"] is None           # the all-hours sum does need that bin
    odds[0, 17] = NAN                                      # a bin with long-spell hours
    row = one_cell("N", odds=odds)
    assert row["long_snow_free_hours"] is None and row["long_snow_free_hours_summer"] is None
    assert row["long_snow_free_hours_winter"] == 3.0       # the winter half is still known


def test_a_northern_cell_without_long_windows_has_zero_long_hours_when_its_snow_is_known():
    flat, odds = np.ones((1, 36)), np.full((1, 36), 0.5)
    unknown, none = np.full((1, 36), NAN), np.zeros((1, 36))
    row = grazing.rows(grazing.target_sums("N", flat, none, unknown, unknown, none, odds, unknown, unknown))[0]
    assert row["long_flat_hours"] == 0.0 and row["long_snow_free_hours"] == 0.0
    assert row["best_stretch_bin"] is None
    no_snow = grazing.rows(grazing.target_sums("N", flat, none, unknown, unknown, none, unknown, unknown, unknown))[0]
    assert no_snow["long_snow_free_hours"] is None           # but stays unknown where the snow is unknown


def test_sums_for_a_southern_cell_keep_snow_unknown_and_count_summer_rock_hours():
    terrain = np.arange(36.0)[None, :] / 2
    row = one_cell("S", odds=np.full((1, 36), 0.5), terrain=terrain)   # odds passed by mistake are not used
    summer = 33 + 34 + 35 + 0 + 1 + 2 + 3 + 4 + 5
    assert row["flat_hours"] == 630.0 and row["long_flat_hours"] == 34.0
    assert row["summer_rock_hours"] == summer
    assert row["long_summer_rock_hours"] == 6.0            # long spells inside 27 November to 1 March: 0.4 x (0 + ... + 5)
    assert row["long_summer_rock_open_hours"] == 3.0
    for field in ("snow_free_hours", "long_snow_free_hours", "long_snow_free_hours_winter",
                  "long_snow_free_hours_summer", "long_snow_free_hours_as_mapped", "long_snow_free_hours_with_rule",
                  "open_hours", "long_open_hours", "long_open_hours_winter", "long_open_hours_summer"):
        assert row[field] is None, field
    assert one_cell("S")["long_summer_rock_open_hours"] is None            # no horizon
    assert one_cell("S")["long_summer_rock_hours"] == 6.0


def test_the_odds_a_cell_uses_follow_its_snow_status():
    assert grazing.odds_used("measured") == "as mapped"            # station evidence: the rule moves the maps away from the ground
    assert grazing.odds_used("doubtful") == "stale-flag rule"      # the cautious, lower figure
    assert grazing.odds_used("no data") is None and grazing.odds_used("unmeasured") is None
    assert grazing.odds_used("measured", has_as_mapped=False) == "stale-flag rule"   # an old archive has nothing else
    with_rule, as_mapped = np.full((3, 36), 0.2), np.full((3, 36), 0.7)
    chosen = grazing.choose_odds(["as mapped", "stale-flag rule", None], with_rule, as_mapped)
    assert chosen[0].tolist() == [0.7] * 36 and chosen[1].tolist() == [0.2] * 36
    assert np.isnan(chosen[2]).all()


def test_top_bins_basis_is_open_then_snow_free_then_flat():
    flat = np.full((1, 36), 4.0)
    snow_free, open_ = np.full((1, 36), 2.0), np.full((1, 36), 1.0)
    unknown = np.full((1, 36), NAN)
    assert grazing.top_bins_basis("N", flat, snow_free, open_)[0, 0] == 1.0
    assert grazing.top_bins_basis("N", flat, snow_free, unknown)[0, 0] == 2.0
    assert grazing.top_bins_basis("N", flat, unknown, unknown)[0, 0] == 4.0
    assert grazing.top_bins_basis("S", flat, snow_free, open_)[0, 0] == 4.0   # the south has no snow odds: flat


def test_json_values_are_rounded_and_unknown_is_none():
    assert grazing.known(12.345) == 12.3
    assert grazing.known(NAN) is None
    assert grazing.known(0.0) == 0.0
    assert grazing.known(0.123456, 3) == 0.123


def test_named_northern_sites_are_listed_for_other_modules():
    sites = {name: (lat, lon) for name, lat, lon in grazing.NAMED_SITES_NORTH}
    assert len(grazing.NAMED_SITES_NORTH) == len(sites) == 12
    assert sites["Qaqortorsuaq anorthosite, Greenland"] == (66.5833, -52.2)
    assert sites["Lofoten anorthosite (Nusfjord), Norway"] == (68.04, 13.35)
    assert sites["Reykjanes, Iceland"] == (63.88, -22.45)
    assert sites["Haughton crater, Devon Island, Canada"] == (75.38, -89.67)
    assert sites["Myrdalssandur sand plain, Iceland"] == (63.45, -18.6)
    assert all(lat >= 59.0 for lat, _ in sites.values())


def test_flat_hours_from_the_real_sun_table_match_the_sun_owners_figures():
    minutes = sun.band_minutes_table([0.0, 69.0], year_phases=1)       # the owner's figures are for the single calendar
    to_malapert = grazing.flat_hours(minutes, grazing.elev_bins(5.55)).sum(axis=1)
    assert to_malapert[0] == pytest.approx(303.3, abs=0.2)
    assert to_malapert[1] == pytest.approx(1092.9, abs=0.2)
    phases = grazing.flat_hours(sun.band_minutes_table([0.0, 69.0]), grazing.elev_bins(5.55)).sum(axis=1)
    assert phases[0] == pytest.approx(303.3, abs=0.2)                  # the mean of eight calendars: the same at the equator,
    assert phases[1] == pytest.approx(1093.1, abs=0.2)                 # 0.15 h more at 69N (1093.05 h; 0.01 percent)


# The build script: glue around the functions above, checked with made-up inputs.

import importlib
import json

build = importlib.import_module("scripts.build_grazing_cells")


def land_cover(cid, lat, lon, bare, land_share=1.0, **more):
    return {"id": cid, "lat": lat, "lon": lon, "bare": bare, "land_share": land_share, "lichen": 0.0, "ice": 0.0, **more}


def test_screen_keeps_bare_northern_cells_and_southern_cells_with_enough_land():
    north = [land_cover("66.5_-52.2", 66.55, -52.05, 0.15), land_cover("66.6_-52.2", 66.65, -52.05, 0.149)]
    south = [land_cover("-66.3_100.5", -66.25, 100.65, 0.6, 0.2, layers_disagree=True),
             land_cover("-69.1_39.3", -69.05, 39.45, 0.52, 0.199, layers_disagree=False)]
    kept = build.screened(north, south)
    assert [c["id"] for c in kept] == ["66.5_-52.2", "-66.3_100.5"]
    assert [c["hemisphere"] for c in kept] == ["N", "S"]
    assert (kept[0]["layers_disagree"], kept[1]["layers_disagree"]) == (None, True)
    assert all(c["gridded"] for c in kept)


def test_named_sites_keep_their_cell_whatever_its_ground_and_stay_out_of_the_counts():
    inside = land_cover("63.4_-18.6", 63.45, -18.5, 0.9)
    outside = land_cover("68.0_13.2", 68.05, 13.35, 0.01)
    cells = build.screened([inside, outside], [])
    sites = [("Myrdalssandur", 63.45, -18.6), ("Lofoten", 68.04, 13.35), ("Nowhere", 75.01, 0.01)]
    build.add_named_sites(cells, {c["id"]: c for c in (inside, outside)}, sites)
    by_id = {c["id"]: c for c in cells}
    assert len(cells) == 3
    assert by_id["63.4_-18.6"]["named_site"] and by_id["63.4_-18.6"]["gridded"]       # passed the screen on its own
    assert by_id["68.0_13.2"]["site_name"] == "Lofoten" and not by_id["68.0_13.2"]["gridded"]
    nowhere = by_id["75.0_0.0"]                                                       # in no land-cover file
    assert nowhere["bare"] is None and nowhere["land_share"] is None and not nowhere["gridded"]
    assert (nowhere["lat"], nowhere["lon"], nowhere["hemisphere"]) == (75.05, 0.25, "N")
    records = [build.finished_record(c, {"status": "measured"}, None, {}) for c in cells]
    assert build.counts(records)["north_cells"] == 1
    assert build.counts(records)["by_snow_status"]["measured"] == 1
    assert build.counts(records)["named_site_cells"] == 3
    nowhere_record = records[[r["id"] for r in records].index("75.0_0.0")]
    assert nowhere_record["bare"] is None and nowhere_record["bare_km2"] is None      # unknown, not zero
    assert nowhere_record["cell_km2"] > 100.0


def test_a_record_has_the_cell_area_and_the_bare_area():
    cell = build.base_record(land_cover("66.5_-52.2", 66.55, -52.05, 0.5, 0.5), True)
    record = build.finished_record(cell, {"status": "measured"}, None, {})
    assert record["cell_km2"] == pytest.approx(148.6, abs=0.1)       # 0.1 x 0.3 degrees at 66.5N on the ellipsoid
    assert record["bare_km2"] == pytest.approx(148.6 / 4, abs=0.05)
    assert record["region"] == "Greenland" and "named_site" not in record


def test_horizons_are_read_per_cell_and_joined_with_the_sun_table(tmp_path, monkeypatch):
    wall = np.ones((36, 9))
    wall[grazing.poleward_sectors("N")] = 0.0
    stored = {"69.0_19.2": {"open_share": wall.tolist(), "north_deg": 30.0, "south_deg": -0.1,
                            "valid_share": 0.9, "pixel_m": 60.0},
              "69.1_19.2": {"skipped": "no land pixels"}}
    path = tmp_path / "horizon_cells.json"
    path.write_text(json.dumps(stored))
    monkeypatch.setattr(build, "HORIZONS", path)
    cells = [{"id": "69.0_19.2"}, {"id": "69.1_19.2"}, {"id": "69.2_19.2"}]
    summaries, shares = build.horizons_of_cells(cells)
    assert summaries[0] == {"north_deg": 30.0, "south_deg": -0.1, "valid_share": 0.9, "pixel_m": 60.0}
    assert summaries[1] == {"skipped": "no land pixels"} and summaries[2] is None
    assert list(shares) == [0]
    minutes = sun.band_minutes_table([69.05])
    bins = grazing.elev_bins(5.55)
    terrain = grazing.terrain_hours(minutes, np.array([0, 0, 0]), shares, bins)
    flat = grazing.flat_hours(minutes[0], bins)
    assert terrain[0, 17] == 0.0 and terrain[0, 4] == pytest.approx(flat[4])    # midnight Sun hidden, February noon kept
    assert np.isnan(terrain[1:]).all()                                         # skipped or missing: unknown, not zero


def test_without_a_horizon_file_no_cell_has_a_horizon(tmp_path, monkeypatch):
    monkeypatch.setattr(build, "HORIZONS", tmp_path / "missing.json")
    assert build.horizons_of_cells([{"id": "69.0_19.2"}]) == ([None], {})


def test_one_projection_call_gives_the_same_snow_answers(monkeypatch):
    from twinfinder import snow
    points = [(66.55, -52.05), (63.85, -22.5), (78.25, 15.75)]
    plain = [snow.ims_rowcol([lat], [lon]) for lat, lon in points]
    calls = []
    real = snow.ims_rowcol
    monkeypatch.setattr(snow, "ims_rowcol", lambda lats, lons: calls.append(len(lats)) or real(lats, lons))
    with build.projected_once(points):
        inside = [snow.ims_rowcol([lat], [lon]) for lat, lon in points]
        assert calls == [3]                                   # one call for all three points, none per point
        other = snow.ims_rowcol([70.0], [20.0])               # a point not in the table still works
    assert calls == [3, 1]
    for (rows_a, cols_a), (rows_b, cols_b) in zip(plain, inside):
        assert rows_a[0] == rows_b[0] and cols_a[0] == cols_b[0]
    assert np.isfinite(other[0][0])
    snow.ims_rowcol([70.0], [20.0])
    assert calls == [3, 1, 1]                                 # and the plain function is back afterwards


# Added in review: cases the tests above let through when the code was broken on purpose.

def test_open_hours_are_unknown_where_the_sun_stands_in_a_part_of_the_sky_with_no_open_share():
    share = OPEN_SHARE.copy()
    share[1, 0] = NAN                                   # sector 1, lowest bin: minutes only in the second ten-day bin
    out = grazing.open_hours(MINUTES, BINS, share)
    assert out[0] == 1.75 and math.isnan(out[1])        # not 2.0 (hidden) and not 3.0 (open): unknown
    share = OPEN_SHARE.copy()
    share[0, 2] = NAN                                   # a bin above the target's limit does not matter
    assert grazing.open_hours(MINUTES, BINS, share).tolist() == [1.75, 3.0]


def test_a_sum_over_chosen_bins_is_unknown_when_one_of_them_is_unknown():
    hours = np.arange(36.0)
    hours[17] = NAN
    keep = np.zeros(36, dtype=bool)
    keep[[16, 17]] = True
    assert math.isnan(grazing.total(hours, keep))       # true/false mask
    assert math.isnan(grazing.total(hours, [16, 17]))   # list of bins
    keep[17] = False
    assert grazing.total(hours, keep) == 16.0           # the unknown bin is not asked for
    assert math.isnan(grazing.total(hours))


def test_days_fall_in_the_calendar_bin_that_holds_them():
    per_bin = grazing.days_per_bin([10, 11, 20, 21, 350, 351, 360, 365])
    assert (per_bin[0], per_bin[1], per_bin[2]) == (1, 2, 1)        # day 10 ends the first bin, day 20 the second
    assert (per_bin[34], per_bin[35]) == (1, 3)                     # days 351 to 365 share the last bin
    assert per_bin.sum() == 8


def test_long_window_sums_split_at_the_edges_of_the_half_years():
    flat = np.full((1, 36), 10.0)
    long_flat = np.zeros((1, 36))
    long_flat[0, [8, 9, 26, 27]] = 10.0                 # 22 to 31 March, 1 to 10 April, 18 to 27 September, 28 September on
    long_flat[0, [0, 17]] = 10.0
    odds = (np.arange(36.0)[None, :] + 1.0) / 100.0     # bin 0 has odds 0.01, bin 35 has 0.36
    unknown = np.full((1, 36), NAN)
    sums = grazing.target_sums("N", flat, long_flat, flat * 0.4, long_flat * 0.4, np.zeros((1, 36)), odds, unknown, unknown)
    row = grazing.rows(sums)[0]
    assert row["long_snow_free_hours_winter"] == 3.8    # bins 0, 8 and 27: 10 x (0.01 + 0.09 + 0.28)
    assert row["long_snow_free_hours_summer"] == 5.5    # bins 9, 17 and 26: 10 x (0.10 + 0.18 + 0.27)
    assert row["long_open_hours_winter"] == 1.5         # 0.4 of 3.8
    assert row["long_open_hours_summer"] == 2.2         # 0.4 of 5.5
    assert row["long_snow_free_hours"] == 9.3 and row["long_open_hours"] == 3.7


def test_rows_keep_the_stretch_to_two_decimals_and_the_bin_as_a_whole_number():
    flat = np.ones((1, 36))
    stretch = np.zeros((1, 36))
    stretch[0, 30] = 1.9666667                          # the median of a bin: kept finer than the hours
    unknown, none = np.full((1, 36), NAN), np.zeros((1, 36))
    row = grazing.rows(grazing.target_sums("N", flat, none, unknown, unknown, stretch, unknown, unknown, unknown))[0]
    assert row["longest_stretch_h"] == 1.97
    assert row["best_stretch_bin"] == 30 and type(row["best_stretch_bin"]) is int
    assert row["long_flat_hours"] == 0.0
    never = grazing.rows(grazing.target_sums("N", flat, none, unknown, unknown, none, unknown, unknown, unknown))[0]
    assert never["best_stretch_bin"] is None and never["longest_stretch_h"] == 0.0


def test_the_join_refuses_to_run_when_sun_and_horizon_bins_differ(monkeypatch):
    monkeypatch.setattr(horizon, "AZ_SECTORS", 72)
    with pytest.raises(ValueError):
        grazing.check_shared_bins()
    monkeypatch.undo()
    monkeypatch.setattr(horizon, "ELEV_EDGES_DEG", [0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 5.55, 6.11, 7.59])
    with pytest.raises(ValueError):
        grazing.check_shared_bins()


# The whole build on a made-up world of seven cells: every figure of every cell is worked out here
# one cell at a time and compared with what the script writes, by cell id.

WORLD_NORTH = [   # deliberately not in latitude order
    land_cover("67.8_19.2", 67.85, 19.35, 0.5, 0.8),      # A: two land pixels, odds 0.2 and 0.6, as mapped 0.8
    land_cover("66.9_19.2", 66.95, 19.35, 0.9),           # B: odds 0.5, one stuck winter south of 67.4, wall to the north
    land_cover("67.4_19.2", 67.45, 19.35, 0.2),           # C: land only in the 5 x 5 ring, one stuck winter there: 0.6 with the rule, 1.0 as mapped
    land_cover("67.1_18.3", 67.15, 18.45, 0.3),           # D: no land pixel near: no data; its horizon was skipped
    land_cover("66.9_20.1", 66.95, 20.25, 0.1),           # E: too little bare ground, kept as a named site
    land_cover("67.8_20.1", 67.85, 20.25, 0.149),         # too little bare ground: left out
]
WORLD_SOUTH = [
    land_cover("-66.3_100.5", -66.25, 100.65, 0.6, 0.877, layers_disagree=True),    # S1: half of the sky open everywhere
    land_cover("-69.1_39.3", -69.05, 39.45, 0.52, 0.1, layers_disagree=False),      # S2: too little land, a named site
]
WORLD_ORDER = ["67.8_19.2", "66.9_19.2", "67.4_19.2", "67.1_18.3", "-66.3_100.5", "66.9_20.1", "-69.1_39.3"]


def made_up_snow_archive(path):
    """A small snow archive around the northern cells of the made-up world."""
    from twinfinder import snow
    place = {}
    for cell in WORLD_NORTH:
        rows_, cols_ = snow.ims_rowcol([cell["lat"]], [cell["lon"]])
        place[cell["id"]] = (int(rows_[0]), int(cols_[0]))
    row0 = min(r for r, _ in place.values()) - 8
    col0 = min(c for _, c in place.values()) - 8
    shape = (max(r for r, _ in place.values()) - row0 + 9, max(c for _, c in place.values()) - col0 + 9)
    near = [max(abs(r1 - r2), abs(c1 - c2)) for i, (r1, c1) in enumerate(place.values())
            for (r2, c2) in list(place.values())[i + 1:]]
    assert min(near) > 5                                   # no cell borrows another cell's made-up pixels
    odds = np.full((36,) + shape, NAN, dtype=np.float32)
    mapped = odds.copy()
    stuck = np.zeros(shape, dtype=np.uint8)
    r, c = place["67.8_19.2"][0] - row0, place["67.8_19.2"][1] - col0
    odds[:, r, c], odds[:, r + 1, c] = 0.2, 0.6
    mapped[:, r, c], mapped[:, r + 1, c] = 0.8, 0.8
    r, c = place["66.9_19.2"][0] - row0, place["66.9_19.2"][1] - col0
    odds[:, r, c], mapped[:, r, c], stuck[r, c] = 0.5, 0.5, 1
    r, c = place["67.4_19.2"][0] - row0, place["67.4_19.2"][1] - col0
    odds[:, r + 2, c], mapped[:, r + 2, c], stuck[r + 2, c] = 0.6, 1.0, 1
    r, c = place["66.9_20.1"][0] - row0, place["66.9_20.1"][1] - col0
    odds[:, r, c], mapped[:, r, c] = 0.25, 0.25
    np.savez(path, probabilities=odds, probabilities_as_mapped=mapped, stuck_winters=stuck,
             row0=row0, col0=col0, maps_per_bin=np.ones(36))


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    """Run the real build on the made-up world; gives the JSON, the per-bin arrays and the horizons used."""
    folder = tmp_path_factory.mktemp("world")
    wall = np.ones((36, 9))
    wall[grazing.poleward_sectors("N")] = 0.0
    horizons = {"66.9_19.2": {"open_share": wall.tolist(), "north_deg": 30.0, "south_deg": -0.1, "valid_share": 1.0,
                              "pixel_m": 60.0},
                "-66.3_100.5": {"open_share": np.full((36, 9), 0.5).tolist(), "north_deg": 4.0, "south_deg": 5.0,
                                "valid_share": 0.9, "pixel_m": 60.0},
                "67.1_18.3": {"skipped": "no land pixels"}}
    files = {"NORTH": WORLD_NORTH, "SOUTH": WORLD_SOUTH, "HORIZONS": horizons,
             "SITES_SOUTH": [{"name": "Syowa", "lat": -69.004, "lon": 39.582}]}
    patch = pytest.MonkeyPatch()
    for name, value in files.items():
        (folder / f"{name}.json").write_text(json.dumps(value))
        patch.setattr(build, name, folder / f"{name}.json")
    made_up_snow_archive(folder / "snow.npz")
    patch.setattr(build, "SNOW", folder / "snow.npz")
    patch.setattr(build, "OUT", folder / "grazing_cells.json")
    patch.setattr(build, "OUT_BINS", folder / "grazing_bins.npz")
    patch.setattr(grazing, "NAMED_SITES_NORTH", [("Somewhere", 66.97, 20.2)])
    try:
        build.main()
    finally:
        patch.undo()
    doc = json.loads((folder / "grazing_cells.json").read_text())
    return {"doc": doc, "cells": {c["id"]: c for c in doc["cells"]}, "bins": np.load(folder / "grazing_bins.npz"),
            "wall": wall, "leftovers": sorted(p.name for p in folder.iterdir())}


def one_cell_alone(lat, t, target):
    """Hours of one latitude and target straight from the Sun module: all hours, and hours in spells of two hours or more."""
    limits = [2.08, 5.55, 6.11, 7.59]
    minutes = sun.band_minutes_table([lat], step_minutes=1)[0]
    long_minutes = sun.long_band_minutes_table([lat], [limits[t]])[0, 0]
    stretch = sun.longest_stretch_hours_table([lat], limits)[0, :, t].astype(float)
    flat = grazing.flat_hours(minutes, target["elev_bins"])
    long_flat = grazing.flat_hours(long_minutes, target["elev_bins"])
    days = grazing.days_per_bin(sun.low_sun_days(lat, limits[t]))
    return {"minutes": minutes, "long_minutes": long_minutes, "flat": flat, "long_flat": long_flat,
            "stretch": stretch, "days": days}


def test_the_build_writes_cells_and_bins_in_the_same_order(world):
    assert [c["id"] for c in world["doc"]["cells"]] == WORLD_ORDER
    assert world["bins"]["ids"].tolist() == WORLD_ORDER
    assert world["bins"]["targets"].tolist() == ["connecting-ridge", "malapert", "mons-mouton", "nobile-rim-2"]
    for name in ("flat", "snow_free", "open", "stretch", "long_flat", "long_snow_free", "long_open"):
        assert world["bins"][name].shape == (7, 4, 36) and world["bins"][name].dtype == np.float32
    assert world["leftovers"] == ["HORIZONS.json", "NORTH.json", "SITES_SOUTH.json", "SOUTH.json",
                                  "grazing_bins.npz", "grazing_cells.json", "snow.npz"]   # no side file left behind


def test_the_build_says_which_long_rule_it_used(world):
    meta = world["doc"]["meta"]
    assert meta["long_rule"] == "per-day spells" and meta["stretch_min_h"] == 2.0
    assert meta["step_minutes"] == 1
    assert meta["year_phases"] == sun.YEAR_PHASES == grazing.YEAR_PHASES == 8      # the mean over eight calendars
    assert "an eighth of a day" in meta["year_phases_meaning"] and "quarter" not in meta["year_phases_meaning"]


def test_the_build_counts_only_the_screened_cells(world):
    meta = world["doc"]["meta"]
    assert meta["counts"]["north_cells"] == 4 and meta["counts"]["south_cells"] == 1
    assert meta["counts"]["by_snow_status"] == {"measured": 2, "doubtful": 1, "no data": 1, "unmeasured": 1}
    assert meta["counts"]["named_site_cells"] == 2 and meta["counts"]["named_site_cells_outside_the_screen"] == 2
    assert meta["horizons"] == 2                           # the skipped one is not a horizon
    assert meta["stretch_min_h"] == 2.0 and meta["n_bins"] == 36 and meta["bin_days"] == 10
    assert [t["limit_deg"] for t in meta["targets"]] == [2.08, 5.55, 6.11, 7.59]
    assert meta["summer_bins_south"] == [33, 34, 35, 0, 1, 2, 3, 4, 5]
    cells = world["cells"]
    assert [cells[i]["gridded"] for i in WORLD_ORDER] == [True, True, True, True, True, False, False]
    assert cells["66.9_20.1"]["site_name"] == "Somewhere" and cells["-69.1_39.3"]["site_name"] == "Syowa"
    assert cells["-69.1_39.3"]["bare"] == 0.52 and cells["-69.1_39.3"]["land_share"] == 0.1
    assert "named_site" not in cells["67.8_19.2"]
    assert (cells["67.8_19.2"]["layers_disagree"], cells["-66.3_100.5"]["layers_disagree"]) == (None, True)
    assert cells["67.8_19.2"]["bare_km2"] == pytest.approx(cells["67.8_19.2"]["cell_km2"] * 0.8 * 0.5, abs=0.001)


def test_the_build_reads_the_snow_of_each_cell(world):
    snow_of = {cid: world["cells"][cid]["snow"] for cid in WORLD_ORDER}
    assert snow_of["67.8_19.2"] == {"status": "measured", "source": "3x3", "land_pixels": 2, "block_pixels": 9,
                                    "stuck_winters": 0, "odds_used": "as mapped"}
    assert snow_of["66.9_19.2"] == {"status": "measured", "source": "3x3", "land_pixels": 1, "block_pixels": 9,
                                    "stuck_winters": 1, "odds_used": "as mapped"}              # 66.95N
    # the land pixel of the 5 x 5 block is counted now (version 2 looked in the 3 x 3 block and wrote 0)
    assert snow_of["67.4_19.2"] == {"status": "doubtful", "source": "5x5", "land_pixels": 1, "block_pixels": 25,
                                    "stuck_winters": 1, "odds_used": "stale-flag rule"}        # 67.45N
    assert snow_of["67.1_18.3"] == {"status": "no data", "source": None, "land_pixels": 0, "block_pixels": None,
                                    "stuck_winters": 0, "odds_used": None}
    unmeasured = {"status": "unmeasured", "source": None, "land_pixels": None, "block_pixels": None,
                  "stuck_winters": None, "odds_used": None}
    assert snow_of["-66.3_100.5"] == unmeasured and snow_of["-69.1_39.3"] == unmeasured
    horizons = {cid: world["cells"][cid]["horizon"] for cid in WORLD_ORDER}
    assert horizons["66.9_19.2"] == {"north_deg": 30.0, "south_deg": -0.1, "valid_share": 1.0, "pixel_m": 60.0}
    assert horizons["67.1_18.3"] == {"skipped": "no land pixels"} and horizons["67.8_19.2"] is None


# odds: what the cell's main numbers use. A is measured, so it uses the maps as they read (0.8), not the rule (0.4);
# C is doubtful, so it keeps the rule (0.6) and carries the as-mapped figure (1.0) beside it.
@pytest.mark.parametrize("cid, lat, odds, as_mapped, with_rule", [
    ("67.8_19.2", 67.85, 0.8, 0.8, 0.4), ("66.9_19.2", 66.95, 0.5, 0.5, 0.5), ("67.4_19.2", 67.45, 0.6, 1.0, 0.6),
    ("66.9_20.1", 66.95, 0.25, 0.25, 0.25)])
def test_the_build_gives_each_northern_cell_the_figures_of_its_own_latitude_and_target(world, cid, lat, odds, as_mapped,
                                                                                      with_rule):
    row = WORLD_ORDER.index(cid)
    winter, summer = grazing.WINTER_BINS_NORTH, grazing.SUMMER_BINS_NORTH
    some_long = 0.0
    for t, target in enumerate(world["doc"]["meta"]["targets"]):
        own = one_cell_alone(lat, t, target)
        flat, long_flat, stretch, days = own["flat"], own["long_flat"], own["stretch"], own["days"]
        got = world["cells"][cid]["targets"][target["id"]]
        some_long += long_flat.sum()
        assert got["flat_hours"] == round(flat.sum(), 1)
        assert got["long_flat_hours"] == round(long_flat.sum(), 1)
        assert got["long_flat_hours"] <= got["flat_hours"]
        assert got["snow_free_hours"] == round(odds * flat.sum(), 1)
        assert got["long_snow_free_hours"] == round(odds * long_flat.sum(), 1)
        assert got["long_snow_free_hours_winter"] == round(odds * long_flat[winter].sum(), 1)
        assert got["long_snow_free_hours_summer"] == round(odds * long_flat[summer].sum(), 1)
        assert got["long_snow_free_hours_as_mapped"] == round(as_mapped * long_flat.sum(), 1)
        assert got["long_snow_free_hours_with_rule"] == round(with_rule * long_flat.sum(), 1)
        assert got["longest_stretch_h"] == round(stretch.max(), 2) and got["best_stretch_bin"] == int(stretch.argmax())
        assert got["poleward_share"] == round(grazing.poleward_share(own["long_minutes"], target["elev_bins"], None, "N"), 3)
        assert got["all_day_days"] == days.sum() and type(got["all_day_days"]) is int
        assert got["usable_days"] == round(odds * days.sum(), 1)
        assert got["summer_rock_hours"] is None and got["long_summer_rock_hours"] is None
        assert world["bins"]["flat"][row, t] == pytest.approx(flat, abs=1e-3)
        assert world["bins"]["long_flat"][row, t] == pytest.approx(long_flat, abs=1e-3)
        assert world["bins"]["snow_free"][row, t] == pytest.approx(odds * flat, abs=1e-3)
        assert world["bins"]["long_snow_free"][row, t] == pytest.approx(odds * long_flat, abs=1e-3)
        assert world["bins"]["stretch"][row, t] == pytest.approx(stretch, abs=1e-6)
        assert np.all(world["bins"]["long_flat"][row, t] <= world["bins"]["flat"][row, t])
        if cid == "66.9_19.2":                             # the cell with the wall to the north
            terrain = grazing.open_hours(own["minutes"], target["elev_bins"], world["wall"])
            long_terrain = grazing.open_hours(own["long_minutes"], target["elev_bins"], world["wall"])
            assert got["open_hours"] == round(odds * terrain.sum(), 1)
            assert got["long_open_hours"] == round(odds * long_terrain.sum(), 1)
            assert got["long_open_hours_winter"] == round(odds * long_terrain[winter].sum(), 1)
            assert got["long_open_hours_summer"] == round(odds * long_terrain[summer].sum(), 1)
            assert flat[17] > 5.0 and terrain[17] == 0.0                       # the wall hides the midnight Sun of late June
            assert (world["bins"]["open"][row, t, 17] == 0.0) and world["bins"]["snow_free"][row, t, 17] > 2.5
            assert world["bins"]["open"][row, t] == pytest.approx(odds * terrain, abs=1e-3)
            assert world["bins"]["long_open"][row, t] == pytest.approx(odds * long_terrain, abs=1e-3)
            basis = odds * long_terrain
        else:
            assert got["open_hours"] is None and got["long_open_hours"] is None
            assert got["long_open_hours_winter"] is None and got["long_open_hours_summer"] is None
            assert np.isnan(world["bins"]["open"][row, t]).all() and np.isnan(world["bins"]["long_open"][row, t]).all()
            basis = odds * long_flat
        assert got["top_bins"] == grazing.top_bins(basis)
    assert some_long > 100.0                               # the test did meet long spells
    assert world["cells"]["67.8_19.2"]["targets"]["malapert"]["flat_hours"] != \
        world["cells"]["66.9_19.2"]["targets"]["malapert"]["flat_hours"]           # the latitudes do differ


def test_a_measured_cell_uses_the_maps_as_they_read_and_a_doubtful_one_the_rule(world):
    measured = world["cells"]["67.8_19.2"]["targets"]["malapert"]       # 0.4 with the rule, 0.8 as mapped
    assert measured["long_snow_free_hours"] == measured["long_snow_free_hours_as_mapped"] > 0.0
    assert measured["long_snow_free_hours_with_rule"] == pytest.approx(measured["long_snow_free_hours"] / 2, abs=0.06)
    assert measured["snow_free_hours"] == pytest.approx(0.8 * measured["flat_hours"], abs=0.06)
    doubtful = world["cells"]["67.4_19.2"]["targets"]["malapert"]       # 0.6 with the rule, 1.0 as mapped
    assert doubtful["long_snow_free_hours"] == doubtful["long_snow_free_hours_with_rule"] > 0.0
    assert doubtful["long_snow_free_hours_as_mapped"] == doubtful["long_flat_hours"]
    # both sides are rounded to 0.1 h: 0.05 on the left, 0.6 x 0.05 on the right
    assert doubtful["long_snow_free_hours"] == pytest.approx(0.6 * doubtful["long_flat_hours"], abs=0.081)


def test_other_code_can_ask_for_long_window_hours_at_another_minimum(world, tmp_path):
    """grazing.long_window_hours_by_bin: what validate.py calls for the 1 h and 3 h variants."""
    cells = [{"id": c["id"], "lat": c["lat"], "lon": c["lon"]} for c in world["doc"]["cells"]]
    made_up_snow_archive(tmp_path / "snow.npz")
    wall_cell, half_open = "66.9_19.2", "-66.3_100.5"
    horizons = {wall_cell: {"open_share": world["wall"].tolist()},
                half_open: {"open_share": np.full((36, 9), 0.5).tolist()}, "67.1_18.3": {"skipped": "no land pixels"}}
    (tmp_path / "horizons.json").write_text(json.dumps(horizons))
    paths = {"snow_archive": tmp_path / "snow.npz", "horizons": tmp_path / "horizons.json"}
    same = grazing.long_window_hours_by_bin(cells, 2.0, **paths)
    assert same["ids"] == WORLD_ORDER and same["targets"] == world["bins"]["targets"].tolist()
    assert same["min_stretch_h"] == 2.0
    for name in ("long_flat", "long_snow_free", "long_open"):                      # at two hours: the build's own figures
        assert same[name].shape == (7, 4, 36) and same[name].dtype == np.float32
        assert np.array_equal(same[name], world["bins"][name], equal_nan=True), name
    inputs = grazing.cell_inputs(cells, **paths)                                   # read once, used for both variants
    one = grazing.long_window_hours_by_bin(cells, 1.0, inputs=inputs)
    three = grazing.long_window_hours_by_bin(cells, 3.0, inputs=inputs)
    for name in ("long_flat", "long_snow_free", "long_open"):
        known = np.isfinite(same[name])
        assert np.array_equal(known, np.isfinite(one[name])) and np.array_equal(known, np.isfinite(three[name]))
        assert np.all(one[name][known] >= same[name][known]) and np.all(same[name][known] >= three[name][known])
    assert one["long_flat"].sum() > same["long_flat"].sum() > three["long_flat"].sum() > 0.0
    a = WORLD_ORDER.index("67.8_19.2")
    lone = sun.long_band_minutes_table([67.85], [5.55], min_stretch_h=3.0)[0, 0]
    assert three["long_flat"][a, 1] == pytest.approx(grazing.flat_hours(lone, grazing.elev_bins(5.55)), abs=1e-3)
    assert three["long_snow_free"][a, 1] == pytest.approx(0.8 * three["long_flat"][a, 1], abs=1e-3)


def test_the_build_keeps_a_cell_without_snow_data_unknown(world):
    for t, target in enumerate(world["doc"]["meta"]["targets"]):
        own = one_cell_alone(67.15, t, target)
        got = world["cells"]["67.1_18.3"]["targets"][target["id"]]
        assert got["flat_hours"] == round(own["flat"].sum(), 1) and got["long_flat_hours"] == round(own["long_flat"].sum(), 1)
        for field in ("snow_free_hours", "long_snow_free_hours", "long_snow_free_hours_winter",
                      "long_snow_free_hours_summer", "long_snow_free_hours_as_mapped", "long_snow_free_hours_with_rule",
                      "usable_days", "open_hours", "long_open_hours", "long_open_hours_winter", "long_open_hours_summer"):
            assert got[field] is None, field
        assert got["all_day_days"] == own["days"].sum()
        assert got["top_bins"] == grazing.top_bins(own["long_flat"])               # nothing better than flat hours to rank by
        for name in ("snow_free", "open", "long_snow_free", "long_open"):
            assert np.isnan(world["bins"][name][3, t]).all(), name


@pytest.mark.parametrize("cid, lat, share", [("-66.3_100.5", -66.25, 0.5), ("-69.1_39.3", -69.05, None)])
def test_the_build_gives_southern_cells_rock_hours_and_no_snow_figures(world, cid, lat, share):
    row = WORLD_ORDER.index(cid)
    rock_season = grazing.SUMMER_BINS_SOUTH
    for t, target in enumerate(world["doc"]["meta"]["targets"]):
        own = one_cell_alone(lat, t, target)
        flat, long_flat, stretch = own["flat"], own["long_flat"], own["stretch"]
        got = world["cells"][cid]["targets"][target["id"]]
        assert got["flat_hours"] == round(flat.sum(), 1) and got["long_flat_hours"] == round(long_flat.sum(), 1)
        assert got["summer_rock_hours"] == round(flat[rock_season].sum(), 1)
        assert got["long_summer_rock_hours"] == round(long_flat[rock_season].sum(), 1)
        assert got["poleward_share"] == round(grazing.poleward_share(own["long_minutes"], target["elev_bins"], None, "S"), 3)
        assert got["longest_stretch_h"] == round(stretch.max(), 2) and got["best_stretch_bin"] == int(stretch.argmax())
        assert got["all_day_days"] == own["days"].sum()
        for field in ("snow_free_hours", "long_snow_free_hours", "long_snow_free_hours_winter",
                      "long_snow_free_hours_summer", "long_snow_free_hours_as_mapped", "long_snow_free_hours_with_rule",
                      "usable_days", "open_hours", "long_open_hours", "long_open_hours_winter", "long_open_hours_summer"):
            assert got[field] is None, field                                       # the snow is not measured: never 0
        assert got["top_bins"] == grazing.top_bins(long_flat)
        assert np.isnan(world["bins"]["snow_free"][row, t]).all() and np.isnan(world["bins"]["long_snow_free"][row, t]).all()
        assert world["bins"]["long_flat"][row, t] == pytest.approx(long_flat, abs=1e-3)
        if share is None:
            assert got["long_summer_rock_open_hours"] is None and np.isnan(world["bins"]["open"][row, t]).all()
            assert np.isnan(world["bins"]["long_open"][row, t]).all()
        else:                                                                      # terrain only, no snow odds
            assert got["long_summer_rock_open_hours"] == round(share * long_flat[rock_season].sum(), 1)
            assert world["bins"]["open"][row, t] == pytest.approx(share * flat, abs=1e-3)
            assert world["bins"]["long_open"][row, t] == pytest.approx(share * long_flat, abs=1e-3)


# --- added in the final step ---

def test_top_bins_leave_out_a_bin_whose_hours_round_to_nothing():
    hours = np.zeros(36)
    hours[[2, 5, 7]] = [10.0, 0.04, 0.06]
    assert grazing.top_bins(hours, np.ones(36, dtype=bool)) == [[2, 10.0], [7, 0.1]]   # bin 5 would print as 0 h


# --- added in the version 3 review: breakages of the code that the tests above let through ---

def one_point_archive(path, lat, lon, fill):
    """A snow archive of 17 x 17 pixels around one point; fill(odds, mapped, stuck, r, c) writes the made-up pixels."""
    from twinfinder import snow
    rows_, cols_ = snow.ims_rowcol([lat], [lon])
    odds = np.full((36, 17, 17), NAN, dtype=np.float32)
    mapped, stuck = odds.copy(), np.zeros((17, 17), dtype=np.uint8)
    fill(odds, mapped, stuck, 8, 8)
    np.savez(path, probabilities=odds, probabilities_as_mapped=mapped, stuck_winters=stuck,
             row0=int(rows_[0]) - 8, col0=int(cols_[0]) - 8, maps_per_bin=np.ones(36))
    return np.load(path)


def test_a_measured_cell_counts_the_land_pixels_of_the_maps_it_uses(tmp_path):
    # One pixel is seen every winter; its neighbour is a stuck pixel that the rule leaves out all year round.
    def fill(odds, mapped, stuck, r, c):
        odds[:, r, c], mapped[:, r, c] = 0.5, 0.5
        mapped[:, r, c + 1], stuck[r, c + 1] = 0.9, 1

    cell = {"id": "62.0_-66.0", "lat": 62.05, "lon": -65.9}
    found = grazing.snow_of_cells([cell], one_point_archive(tmp_path / "snow.npz", cell["lat"], cell["lon"], fill))
    assert found["summaries"] == [{"status": "measured", "source": "3x3", "land_pixels": 2, "block_pixels": 9,
                                   "stuck_winters": 1, "odds_used": "as mapped"}]      # two pixels as mapped, one with the rule
    assert found["with_rule"][0] == pytest.approx(0.5) and found["as_mapped"][0] == pytest.approx(0.7)
    assert found["odds"][0] == pytest.approx(0.7)


def test_land_and_block_pixels_follow_the_block_of_the_odds_a_cell_uses(tmp_path):
    # The cell's own pixel is stuck and left out by the rule, so the rule borrows a pixel two away (5 x 5);
    # the maps as they read have the cell's own pixel (3 x 3). The cell is measured, so it uses the latter.
    def fill(odds, mapped, stuck, r, c):
        mapped[:, r, c], stuck[r, c] = 0.9, 1
        odds[:, r + 2, c], mapped[:, r + 2, c] = 0.4, 0.4

    cell = {"id": "62.0_-66.0", "lat": 62.05, "lon": -65.9}
    found = grazing.snow_of_cells([cell], one_point_archive(tmp_path / "snow.npz", cell["lat"], cell["lon"], fill))
    assert found["summaries"] == [{"status": "measured", "source": "5x5", "land_pixels": 1, "block_pixels": 9,
                                   "stuck_winters": 1, "odds_used": "as mapped"}]      # source: the block the status was judged on
    assert found["with_rule"][0] == pytest.approx(0.4) and found["odds"][0] == pytest.approx(0.9)
    # north of 67.4 the same pixels make the cell doubtful: it keeps the rule and reports the 5 x 5 block it came from
    north = {"id": "68.0_-66.0", "lat": 68.05, "lon": -65.9}
    found = grazing.snow_of_cells([north], one_point_archive(tmp_path / "north.npz", north["lat"], north["lon"], fill))
    assert found["summaries"] == [{"status": "doubtful", "source": "5x5", "land_pixels": 1, "block_pixels": 25,
                                   "stuck_winters": 1, "odds_used": "stale-flag rule"}]
    assert found["odds"][0] == pytest.approx(0.4) and found["as_mapped"][0] == pytest.approx(0.9)


def test_the_other_minimum_function_passes_its_time_step_on(tmp_path):
    cells = [{"id": "67.8_19.2", "lat": 67.85, "lon": 19.35}]
    made_up_snow_archive(tmp_path / "snow.npz")
    (tmp_path / "horizons.json").write_text("{}")
    paths = {"snow_archive": tmp_path / "snow.npz", "horizons": tmp_path / "horizons.json"}
    fine = grazing.long_window_hours_by_bin(cells, 2.0, **paths)                    # one-minute steps, like the cells file
    coarse = grazing.long_window_hours_by_bin(cells, 2.0, step_minutes=2, **paths)
    for step, got in ((1, fine), (2, coarse)):
        lone = sun.long_band_minutes_table([67.85], [5.55], 2.0, step_minutes=step)[0, 0]
        assert np.array_equal(got["long_flat"][0, 1], grazing.flat_hours(lone, grazing.elev_bins(5.55)).astype(np.float32)), step
    assert not np.array_equal(fine["long_flat"], coarse["long_flat"])
    assert np.abs(fine["long_flat"] - coarse["long_flat"]).max() < 0.05
    # ... and its number of calendars: four unless asked otherwise, one gives the single calendar
    single = grazing.long_window_hours_by_bin(cells, 2.0, year_phases=1, **paths)
    lone = sun.long_band_minutes_table([67.85], [5.55], 2.0, year_phases=1)[0, 0]
    assert np.array_equal(single["long_flat"][0, 1], grazing.flat_hours(lone, grazing.elev_bins(5.55)).astype(np.float32))
    assert not np.array_equal(single["long_flat"], fine["long_flat"])
    assert abs(float(single["long_flat"][0, 1].sum()) - float(fine["long_flat"][0, 1].sum())) < 10.0


def test_an_archive_without_as_mapped_odds_leaves_a_measured_cell_on_the_rule(tmp_path):
    from twinfinder import snow
    cell = {"id": "62.0_-66.0", "lat": 62.05, "lon": -65.9}
    rows_, cols_ = snow.ims_rowcol([cell["lat"]], [cell["lon"]])
    odds = np.full((36, 17, 17), NAN, dtype=np.float32)
    odds[:, 8, 8] = 0.3
    np.savez(tmp_path / "old.npz", probabilities=odds, stuck_winters=np.zeros((17, 17), dtype=np.uint8),
             row0=int(rows_[0]) - 8, col0=int(cols_[0]) - 8, maps_per_bin=np.ones(36))
    found = grazing.snow_of_cells([cell], np.load(tmp_path / "old.npz"))
    assert found["summaries"] == [{"status": "measured", "source": "3x3", "land_pixels": 1, "block_pixels": 9,
                                   "stuck_winters": 0, "odds_used": "stale-flag rule"}]
    assert found["odds"][0] == pytest.approx(0.3) and found["with_rule"][0] == pytest.approx(0.3)
    assert np.isnan(found["as_mapped"]).all()          # unknown, not zero

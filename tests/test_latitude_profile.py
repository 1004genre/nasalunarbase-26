# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
import importlib

import numpy as np
import pytest

profile = importlib.import_module("scripts.build_latitude_profile")

TARGETS = [{"id": "low", "name": "Low", "limit_deg": 2.08, "elev_bins": [0, 1, 2, 3]},
           {"id": "high", "name": "High", "limit_deg": 7.59, "elev_bins": [0, 1, 2, 3, 4, 5, 6, 7, 8]}]
PER_DAY_FIRST_LAT_2H = {2.08: 64.8, 5.55: 60.65, 6.11: 59.9, 7.59: 57.65}   # limit: first latitude with a two-hour spell


def test_profile_latitudes_run_from_pole_to_pole_in_half_degrees():
    lats = profile.profile_latitudes()
    assert len(lats) == 359
    assert (lats[0], lats[1], lats[179], lats[-1]) == (-89.5, -89.0, 0.0, 89.5)


def test_fine_latitudes_step_outward_from_the_equator():
    north, south = profile.fine_latitudes(1), profile.fine_latitudes(-1)
    assert (north[0], north[1], north[2], north[-1]) == (0.0, 0.05, 0.1, 89.95)
    assert (south[1], south[-1]) == (-0.05, -89.95)
    assert len(north) == len(south) == 1800


def made_up_long(january_low: float, january_high: float, june: float) -> np.ndarray:
    """Long-spell minutes [2 targets, 36, 36, 9] laid out like the row of made_up_row: so many minutes of each entry."""
    long = np.zeros((2, 36, 36, 9))
    long[:, 2, 18, 0] = january_low      # both targets use elevation bin 0
    long[1, 2, 18, 8] = january_high     # only the higher target reaches bin 8
    long[:, 17, 0, 3] = june
    return long


def made_up_row():
    """Bin 2 (January) holds 2 hours low and 1 hour higher up; bin 17 (June) holds 3 hours low.

    Spells: with a 1 h minimum all of it counts; with 2 h, half of January's low hours and all of June's;
    with 3 h, June's only.
    """
    minutes = np.zeros((36, 36, 9))
    minutes[2, 18, 0] = 120.0
    minutes[2, 18, 8] = 60.0
    minutes[17, 0, 3] = 180.0
    stretch = np.zeros((36, 2))
    stretch[2] = [1.5, 2.5]
    stretch[17] = [3.0, 3.0]
    long = {"1": made_up_long(120.0, 60.0, 180.0), "2": made_up_long(60.0, 0.0, 180.0), "3": made_up_long(0.0, 0.0, 180.0)}
    return profile.profile_row(70.0, minutes, stretch, TARGETS, long, np.array([3.2, 3.7]))


def test_a_profile_row_holds_flat_hours_and_their_split_by_half_year():
    row = made_up_row()
    assert row["lat"] == 70.0
    low, high = row["targets"]["low"], row["targets"]["high"]
    assert (low["flat_hours"], low["flat_hours_oct_mar"], low["flat_hours_apr_sep"]) == (5.0, 2.0, 3.0)
    assert (high["flat_hours"], high["flat_hours_oct_mar"], high["flat_hours_apr_sep"]) == (6.0, 3.0, 3.0)


def test_a_profile_row_holds_the_hours_inside_spells_of_each_minimum_length():
    low, high = made_up_row()["targets"]["low"], made_up_row()["targets"]["high"]
    assert low["long_flat_hours"] == {"1": 5.0, "2": 4.0, "3": 3.0}    # part of a bin can count: the rule goes by the day
    assert high["long_flat_hours"] == {"1": 6.0, "2": 4.0, "3": 3.0}
    assert (low["longest_stretch_h"], low["best_stretch_bin"]) == (3.0, 17)      # the old ten-day median, for information
    assert (low["longest_spell_h"], high["longest_spell_h"]) == (3.2, 3.7)       # the longest single spell of the year


def test_lowest_latitude_is_the_one_nearest_the_equator():
    assert profile.lowest_latitude([0.0, 0.05, 0.1, 0.15], [False, True, False, True]) == 0.05
    assert profile.lowest_latitude([0.0, -0.05, -0.1], [False, False, True]) == -0.1
    assert profile.lowest_latitude([0.0, 0.05], [False, False]) is None


def test_bin_median_search_walks_outward_until_every_minimum_is_found():
    asked = []

    def stretch_table(lats, limits):
        """Made-up Sun: the longest stretch is a tenth of the latitude in hours, twice that for the second limit."""
        asked.append(len(lats))
        table = np.zeros((len(lats), 36, len(limits)))
        table[:, 5, 0] = np.abs(lats) / 10.0
        table[:, 5, 1] = np.abs(lats) / 5.0
        return table

    found = profile.lowest_long_windows(-1, [2.08, 7.59], [1.0, 2.0, 3.0], stretch_table=stretch_table)
    assert found[0] == {"1": -10.0, "2": -20.0, "3": -30.0}
    assert found[1] == {"1": -5.0, "2": -10.0, "3": -15.0}
    assert sum(asked) < 1800       # it stopped once the last one was found


def test_the_version_2_rule_keeps_its_single_calendar(monkeypatch):
    # The bin-median thresholds are kept for comparison with version 2, so they are found as version 2 found them.
    from twinfinder import sun
    asked = []

    def spy(lats, limits, refraction=True, step_minutes=2, year_phases=sun.YEAR_PHASES):
        asked.append(year_phases)
        table = np.zeros((len(lats), 36, len(limits)))
        table[:, 5, 0] = np.abs(lats) / 10.0
        return table

    monkeypatch.setattr(sun, "longest_stretch_hours_table", spy)
    assert profile.lowest_long_windows(1, [2.08], [2.0]) == [{"2": 20.0}]
    assert asked and set(asked) == {1}


def test_bin_median_search_gives_none_where_no_latitude_qualifies():
    def never(lats, limits):
        return np.zeros((len(lats), 36, len(limits)))

    assert profile.lowest_long_windows(1, [2.08], [1.0], stretch_table=never) == [{"1": None}]


def test_per_day_search_finds_the_first_latitude_whose_longest_spell_reaches_each_minimum():
    asked = []

    def longest_spell(lats, limits):
        """Made-up Sun: the year's longest spell is a twentieth of the latitude in hours, twice that for the second limit."""
        asked.append(len(lats))
        best = np.abs(np.asarray(lats))[:, None] / 20.0 * np.array([1.0, 2.0])[None, :len(limits)]
        return best

    found = profile.lowest_long_spells(1, [2.08, 7.59], [1.0, 2.0, 3.0], longest_spell=longest_spell)
    assert found[0] == {"1": 20.0, "2": 40.0, "3": 60.0}
    assert found[1] == {"1": 10.0, "2": 20.0, "3": 30.0}
    assert sum(asked) < 1800
    south = profile.lowest_long_spells(-1, [2.08, 7.59], [1.0, 2.0, 3.0], longest_spell=longest_spell)
    assert south[0] == {"1": -20.0, "2": -40.0, "3": -60.0}
    assert profile.lowest_long_spells(1, [2.08], [2.0], longest_spell=lambda lats, limits: np.zeros((len(lats), 1))) == \
        [{"2": None}]


def test_the_real_per_day_thresholds_sit_where_the_longest_spell_first_reaches_two_hours():
    # Figures of the build of 14 November 2026 (one-minute steps, apparent Sun centre, flat horizon), per limit:
    # the first latitude on the 0.05 degree ladder with a spell of two hours on at least one day of the year.
    from twinfinder import sun
    for limit, first in PER_DAY_FIRST_LAT_2H.items():
        best = sun.longest_spell_hours([round(first - 0.05, 2), first, -round(first - 0.05, 2), -first], [limit])[:, 0]
        assert best[0] < 2.0 <= best[1], (limit, best)
        assert best[2] < 2.0 <= best[3], (limit, best)     # the same ladder step in the south


def test_lowest_latitude_with_an_all_day_low_sun_day_matches_the_sun_module():
    # sun's own tests: at a 5.0 degree limit there is no such day at 61.7N and there are some at 61.8N.
    assert 61.7 < profile.lowest_all_day(1, 5.0) <= 61.8
    assert -61.8 <= profile.lowest_all_day(-1, 5.0) < -61.5


# Added in review: cases the tests above let through when the code was broken on purpose.

def test_each_target_gets_its_own_best_stretch():
    minutes = np.zeros((36, 36, 9))
    minutes[2, 18, 0] = 120.0
    stretch = np.zeros((36, 2))
    stretch[2] = [1.5, 4.0]
    stretch[17] = [3.0, 3.5]
    long = {"1": made_up_long(120.0, 0.0, 0.0), "2": made_up_long(0.0, 0.0, 0.0), "3": made_up_long(0.0, 0.0, 0.0)}
    long["2"][1, 2, 18, 0] = long["3"][1, 2, 18, 0] = 120.0     # under the higher limit the same two hours are one spell
    row = profile.profile_row(70.0, minutes, stretch, TARGETS, long, np.array([1.5, 4.0]))
    low, high = row["targets"]["low"], row["targets"]["high"]
    assert (low["longest_stretch_h"], low["best_stretch_bin"]) == (3.0, 17)
    assert (high["longest_stretch_h"], high["best_stretch_bin"]) == (4.0, 2)
    assert low["long_flat_hours"] == {"1": 2.0, "2": 0.0, "3": 0.0}
    assert high["long_flat_hours"] == {"1": 2.0, "2": 2.0, "3": 2.0}
    assert (low["longest_spell_h"], high["longest_spell_h"]) == (1.5, 4.0)


def test_thresholds_are_filed_under_their_own_target_and_hemisphere(monkeypatch):
    def per_day(sign, limits, minimums):
        return [{profile.minimum_name(m): sign * (10 * limit + m) for m in minimums} for limit in limits]

    def bin_median(sign, limits, minimums):
        return [{profile.minimum_name(m): sign * (10 * limit + m + 0.5) for m in minimums} for limit in limits]

    monkeypatch.setattr(profile, "lowest_long_spells", per_day)
    monkeypatch.setattr(profile, "lowest_long_windows", bin_median)
    monkeypatch.setattr(profile, "lowest_all_day", lambda sign, limit: sign * limit)
    out = profile.thresholds(TARGETS)
    assert set(out) == {"low", "high"} and set(out["low"]) == set(out["high"]) == {"N", "S"}
    for target in TARGETS:
        for side, sign in (("N", 1), ("S", -1)):
            base = 10 * target["limit_deg"]
            assert out[target["id"]][side] == {
                "lowest_lat_with_long_window": {"1": sign * (base + 1.0), "2": sign * (base + 2.0), "3": sign * (base + 3.0)},
                "lowest_lat_with_long_window_bin_median": {"1": sign * (base + 1.5), "2": sign * (base + 2.5),
                                                           "3": sign * (base + 3.5)},
                "lowest_lat_with_all_day_low_sun": sign * target["limit_deg"]}


# --- added in the version 3 review: main() itself was not run by any test ---

def test_main_writes_each_latitude_and_minimum_from_its_own_per_day_table(tmp_path, monkeypatch):
    import json

    from twinfinder import grazing, sun

    lats = [59.5, 62.0, 70.0]
    asked = []
    all_hours = sun.band_minutes_table

    def spy(lats_, step_minutes=2, refraction=True):
        asked.append(step_minutes)
        return all_hours(lats_, step_minutes, refraction)       # the default phases, like the long tables beside it

    monkeypatch.setattr(sun, "band_minutes_table", spy)
    monkeypatch.setattr(profile, "profile_latitudes", lambda: lats)
    monkeypatch.setattr(profile, "thresholds", lambda targets: {"searched for": [t["id"] for t in targets]})
    monkeypatch.setattr(profile, "OUT", tmp_path / "latitude_profile.json")
    profile.main()
    assert [p.name for p in tmp_path.iterdir()] == ["latitude_profile.json"]         # no side file left behind
    doc = json.loads((tmp_path / "latitude_profile.json").read_text())
    targets = grazing.load_targets()
    limits = [t["limit_deg"] for t in targets]
    meta = doc["meta"]
    assert meta["long_rule"] == "per-day spells" and meta["step_minutes"] == 1
    assert meta["year_phases"] == sun.YEAR_PHASES == 8 and "an eighth of a day" in meta["year_phases_meaning"]
    assert meta["stretch_minimums_h"] == [1.0, 2.0, 3.0] and meta["targets"] == targets
    assert asked == [1]                  # all hours at the step of the long spells, so long hours can never exceed them
    assert doc["thresholds"] == {"searched for": [t["id"] for t in targets]}
    assert [row["lat"] for row in doc["profile"]] == lats

    every = all_hours(lats, step_minutes=1)
    longest = sun.longest_spell_hours(lats, limits)
    stretch = sun.longest_stretch_hours_table(lats, limits)
    long = {"1": sun.long_band_minutes_table(lats, limits, 1.0), "2": sun.long_band_minutes_table(lats, limits, 2.0),
            "3": sun.long_band_minutes_table(lats, limits, 3.0)}
    for i, row in enumerate(doc["profile"]):
        for t, target in enumerate(targets):
            got, bins = row["targets"][target["id"]], target["elev_bins"]
            assert got["flat_hours"] == round(float(grazing.flat_hours(every[i], bins).sum()), 1)
            assert got["long_flat_hours"] == {name: round(float(grazing.flat_hours(table[t, i], bins).sum()), 1)
                                              for name, table in long.items()}
            assert got["longest_spell_h"] == round(float(longest[i, t]), 2)
            assert got["longest_stretch_h"] == round(float(stretch[i, :, t].max()), 2)
            assert got["long_flat_hours"]["3"] <= got["long_flat_hours"]["2"] <= got["long_flat_hours"]["1"] <= got["flat_hours"]
    # the figures used here do tell the latitudes and the three minimums apart (Malapert, limit 5.55 degrees)
    malapert = [row["targets"]["malapert"] for row in doc["profile"]]
    assert malapert[0]["long_flat_hours"]["1"] > 300.0 and malapert[0]["long_flat_hours"]["2"] == 0.0     # 59.5N
    assert malapert[1]["long_flat_hours"]["1"] > malapert[1]["long_flat_hours"]["2"] + 400.0              # 62N
    assert malapert[1]["long_flat_hours"]["2"] > malapert[1]["long_flat_hours"]["3"] + 30.0 > 130.0
    assert malapert[2]["long_flat_hours"]["2"] > 500.0                                                    # 70N
    assert malapert[0]["longest_spell_h"] < 2.0 < malapert[1]["longest_spell_h"] < malapert[2]["longest_spell_h"]


# Added in the round 4 review: a breakage of the code that the tests above let through.

def test_the_per_day_thresholds_are_searched_in_every_calendar_of_the_sun_tables(monkeypatch):
    # The lowest latitude with a long spell is found from the Sun module's longest spell as it stands: the mean
    # over the calendars of sun.YEAR_PHASES, like the long-spell hours printed beside it. One calendar alone gives
    # the same latitudes today only because the calendars differ by seconds where the spells begin.
    from twinfinder import sun
    offsets = []
    track = sun._year_track

    def spy(solar_hours, day_offset=0.0):
        offsets.append(day_offset)
        return track(solar_hours, day_offset)

    monkeypatch.setattr(sun, "_year_track", spy)
    monkeypatch.setattr(profile, "SEARCH_BATCH", 2)                    # the equator and one step north: the search ends there
    found = profile.lowest_long_spells(1, [7.59], [0.25])              # at the equator the Sun needs half an hour to climb 7.59 degrees
    assert found == [{"0.25": 0.0}]
    assert sorted(set(offsets)) == pytest.approx([k / 8 - 0.4375 for k in range(8)])      # the eight calendars

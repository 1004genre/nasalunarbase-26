# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""The comparison with JPL Horizons: reading the saved answers, counting spells, and summing up honestly."""
import importlib
import json
from pathlib import Path

import numpy as np
import pytest

check = importlib.import_module("scripts.check_against_horizons")
RAW = Path(__file__).resolve().parents[1] / "data" / "raw" / "horizons_check"

TEXT = """header
$$SOE
 2026-Aug-07 00:00,*,m, 273.176704,    16.264124,
 2026-Aug-07 00:05,*,m, 274.380086,    15.949473,
 2026-Aug-07 00:10,*,m, 275.581732,    15.635367,
 2026-Aug-07 00:15,*,m, 276.781727,    15.321946,
$$EOE
footer"""


def test_a_horizons_table_is_read_in_ut_minutes_with_azimuth_and_elevation():
    when, az, el = check.parse_horizons(TEXT, step_minutes=5)
    assert str(when[0]) == "2026-08-07T00:00" and len(when) == 4
    assert az[1] == pytest.approx(274.380086) and el[3] == pytest.approx(15.321946)
    with pytest.raises(ValueError):
        check.parse_horizons("no table here")


def test_the_cubic_fill_in_passes_through_the_rows_and_follows_a_cubic_exactly():
    y = np.array([0.0, 1.0, 8.0, 27.0, 64.0, 125.0])         # x ** 3
    x, fine = check.upsample_cubic(y, 4)
    assert np.allclose(fine[::4], y)
    assert np.allclose(fine, x ** 3)


def test_spells_through_midnight_are_one_spell_and_credited_to_the_day_they_fall_in():
    step = 60.0                                               # hours as samples
    inside = np.array([0] * 22 + [1, 1] + [1, 1, 1] + [0] * 19 + [1] * 1 + [0] * 1, dtype=bool)   # 48 samples, two days
    day = np.repeat([1, 2], 24)
    stats = check.day_statistics(inside, day, step, min_spell_h=2.0)
    assert list(stats["band_h"]) == [2.0, 4.0]
    assert list(stats["long_h"]) == [2.0, 3.0]                # the 5 h spell counts on both days; the lone hour does not
    assert list(stats["longest_h"]) == [5.0, 5.0]


def test_the_summary_leaves_out_rows_whose_percentage_is_unknown_and_never_writes_zero_for_unknown():
    rows = [{"horizons_h": 10.0, "project_h": 10.5}, {"horizons_h": 0.0, "project_h": 0.0}, {"horizons_h": 0.0, "project_h": 0.2}]
    out = check.summary(rows)
    assert out["rows"] == 3 and out["rows_with_a_percentage"] == 1
    assert out["median_abs_difference_h"] == pytest.approx(0.2)
    assert out["largest_abs_difference_h"] == pytest.approx(0.5)
    assert out["largest_abs_difference_pct"] == pytest.approx(5.0)
    assert check.summary([])["median_abs_difference_h"] is None


def test_a_row_is_flagged_over_five_percent_or_one_hour():
    assert check.flagged({"horizons_h": 10.0, "project_h": 10.6})
    assert check.flagged({"horizons_h": 100.0, "project_h": 101.2})
    assert not check.flagged({"horizons_h": 100.0, "project_h": 100.9})
    assert not check.flagged({"horizons_h": 0.0, "project_h": 0.0})


def test_the_saved_answers_and_the_list_of_places_are_in_the_project():
    sites = json.loads((RAW / "sites.json").read_text())
    assert len(sites) == 9
    for site in sites:
        assert len(site["bins"]) == 4
        for b in site["bins"].values():
            assert (RAW / f"{site['site']}_bin{b:02d}.txt").exists()


def test_a_flagged_row_is_put_down_to_the_calendar_average_only_when_the_single_calendar_agrees():
    row = {"horizons_h": 22.1, "project_h": 20.5, "project_one_calendar_h": 21.9, "horizons_longest_h": [3.0] * 10}
    assert "average over calendars" in check.cause_of(row, "long")
    worse = {**row, "project_one_calendar_h": 20.0}
    assert check.cause_of(worse, "long") is None
    near = {**worse, "horizons_longest_h": [2.05] + [3.0] * 9}
    assert "within 15 minutes of the 2-hour cut" in check.cause_of(near, "long")
    small = {"horizons_h": 3.8, "project_h": 4.1, "project_one_calendar_h": 4.1}
    assert "small total" in check.cause_of(small, "all")

# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
import hashlib
import importlib
import json
from pathlib import Path

import pytest

from twinfinder import candidates

TARGETS = ["malapert", "nobile-rim-2"]


def cell(cid, lat=70.05, lon=20.0, bare=0.5, status="measured", gridded=True, named=None, **hours):
    """A grazing-cells record with the same hours for both targets; hours not given are unknown."""
    fields = ["long_snow_free_hours", "long_snow_free_hours_winter", "long_snow_free_hours_summer",
              "long_snow_free_hours_as_mapped", "long_flat_hours", "long_summer_rock_hours"]
    per_target = {name: hours.get(name) for name in fields}
    record = {"id": cid, "lat": lat, "lon": lon, "hemisphere": "N" if lat >= 0 else "S", "bare": bare,
              "gridded": gridded, "snow": {"status": status},
              "targets": {t: dict(per_target) for t in TARGETS}}
    if named:
        record["named_site"], record["site_name"] = True, named
    return record


def test_value_is_hours_times_bare_and_unknown_stays_unknown():
    c = cell("a", bare=0.5, long_snow_free_hours=100.0)
    assert candidates.value(c, "malapert", "long_snow_free_hours") == 50.0
    assert candidates.value(c, "malapert", "long_snow_free_hours_winter") is None
    no_ground = cell("b", bare=None, long_snow_free_hours=100.0)
    assert candidates.value(no_ground, "malapert", "long_snow_free_hours") is None


def test_top_list_is_best_first_and_leaves_out_zero_and_unknown():
    cells = [cell("low", long_snow_free_hours=10.0), cell("high", long_snow_free_hours=90.0),
             cell("bare", bare=1.0, long_snow_free_hours=50.0),      # 50 x 1.0 beats 90 x 0.5
             cell("zero", long_snow_free_hours=0.0), cell("unknown")]
    top = candidates.top_list(cells, "malapert", "long_snow_free_hours", 10)
    assert [c["id"] for c in top] == ["bare", "high", "low"]
    assert [c["id"] for c in candidates.top_list(cells, "malapert", "long_snow_free_hours", 2)] == ["bare", "high"]


def test_top_list_breaks_ties_by_id_so_a_second_run_gives_the_same_list():
    cells = [cell(cid, long_snow_free_hours=40.0) for cid in ("c", "a", "b")]
    assert [c["id"] for c in candidates.top_list(cells, "malapert", "long_snow_free_hours", 2)] == ["a", "b"]


def test_sample_is_the_first_ids_by_sha1_whatever_the_scores_or_the_order_given():
    cells = [cell(f"id{k}", long_snow_free_hours=float(k)) for k in range(40)]
    expected = sorted((c["id"] for c in cells), key=lambda cid: hashlib.sha1(cid.encode()).hexdigest())[:5]
    assert [c["id"] for c in candidates.sample(cells, 5)] == expected
    assert [c["id"] for c in candidates.sample(cells[::-1], 5)] == expected
    rescored = [cell(c["id"], long_snow_free_hours=1.0) for c in cells]
    assert [c["id"] for c in candidates.sample(rescored, 5)] == expected


def test_north_top_lists_take_measured_gridded_cells_only():
    cells = [cell("m1", long_snow_free_hours=80.0, long_snow_free_hours_winter=5.0),
             cell("m2", long_snow_free_hours=60.0, long_snow_free_hours_summer=60.0),
             cell("offgrid", gridded=False, long_snow_free_hours=500.0),
             cell("south", lat=-70.05, status="unmeasured", long_snow_free_hours=500.0)]
    found, sizes = candidates.build(cells, TARGETS, [], sizes={"year": 1, "winter": 1, "summer": 1},
                                    sample_north=0, sample_south=0)
    why = {c["id"]: c["why"] for c in found}
    assert why == {"m1": ["top malapert year", "top malapert winter", "top nobile-rim-2 year",
                          "top nobile-rim-2 winter"],
                   "m2": ["top malapert summer", "top nobile-rim-2 summer"]}
    assert sizes["top malapert year"] == 1 and sizes["union"] == 2


def test_doubtful_and_no_data_cells_enter_when_their_own_numbers_reach_the_list():
    cells = [cell("m1", long_snow_free_hours=80.0), cell("m2", long_snow_free_hours=60.0),
             cell("m3", long_snow_free_hours=10.0),
             cell("d_in", status="doubtful", long_snow_free_hours=70.0),
             cell("d_out", status="doubtful", long_snow_free_hours=20.0),
             cell("d_mapped", status="doubtful", long_snow_free_hours=1.0, long_snow_free_hours_as_mapped=75.0),
             cell("n_in", status="no data", long_flat_hours=300.0),
             cell("n_out", status="no data", long_flat_hours=30.0)]
    found, sizes = candidates.build(cells, ["malapert"], [], sizes={"year": 2, "winter": 2, "summer": 2},
                                    sample_north=0, sample_south=0)
    why = {c["id"]: c["why"] for c in found}
    assert set(why) == {"m1", "m2", "d_in", "d_mapped", "n_in"}      # the list ends at 60 x 0.5
    assert why["d_in"] == ["doubtful: would be top malapert year"]
    assert why["d_mapped"] == ["doubtful: would be top malapert year (as mapped)"]
    assert why["n_in"] == ["no data: flat hours would be top malapert year"]
    assert sizes["doubtful or no data"] == 3


def test_a_short_top_list_does_not_let_every_doubtful_cell_in():
    cells = [cell("m1", long_snow_free_hours=80.0), cell("d", status="doubtful", long_snow_free_hours=0.0)]
    found, _ = candidates.build(cells, ["malapert"], [], sample_north=0, sample_south=0)
    assert [c["id"] for c in found] == ["m1"]


def test_rock_cells_are_northern_cells_within_reach_of_a_body():
    body = {"name": "Test body", "lat": 70.0, "lon": 20.0, "radius_km": 5.0, "an_low": 80, "an_high": 90}
    cells = [cell("near", lat=70.05, lon=20.0), cell("far", lat=71.05, lon=20.0),
             cell("edge", lat=70.11, lon=20.0),                        # 12 km away: inside 5 km + the 8 km margin
             cell("south", lat=-70.0, lon=20.0, status="unmeasured")]
    southern_body = dict(body, lat=-70.0)
    found, sizes = candidates.build(cells, TARGETS, [body, southern_body], sample_north=0, sample_south=0)
    assert {c["id"]: c["why"] for c in found} == {"near": ["rock: Test body"], "edge": ["rock: Test body"]}
    assert sizes["rock"] == 2


def test_south_lists_use_summer_rock_hours_and_flat_hours():
    cells = [cell("s1", lat=-70.05, status="unmeasured", long_summer_rock_hours=50.0, long_flat_hours=10.0),
             cell("s2", lat=-71.05, status="unmeasured", long_summer_rock_hours=5.0, long_flat_hours=90.0),
             cell("s3", lat=-72.05, status="unmeasured", long_summer_rock_hours=1.0, long_flat_hours=1.0),
             cell("s_off", lat=-73.05, status="unmeasured", gridded=False, long_summer_rock_hours=99.0)]
    found, sizes = candidates.build(cells, ["malapert"], [], sizes={"summer rock": 1, "flat": 1},
                                    sample_north=0, sample_south=0)
    assert {c["id"]: c["why"] for c in found} == {"s1": ["south top malapert summer rock"],
                                                 "s2": ["south top malapert flat"]}
    assert sizes["south top malapert flat"] == 1


def test_samples_are_marked_and_named_sites_always_enter():
    north = [cell(f"n{k}", long_snow_free_hours=float(k)) for k in range(30)]
    south = [cell(f"s{k}", lat=-70.05, status="unmeasured") for k in range(30)]
    extra = [cell("doubt", status="doubtful"), cell("off", gridded=False),
             cell("site", bare=None, gridded=False, named="Lofoten"),
             cell("site_s", lat=-77.5, bare=0.01, status="unmeasured", gridded=False, named="Dry Valleys")]
    found, sizes = candidates.build(north + south + extra, ["malapert"], [],
                                    sizes={"year": 0, "winter": 0, "summer": 0, "summer rock": 0, "flat": 0},
                                    sample_north=4, sample_south=3)
    why = {c["id"]: c["why"] for c in found}
    assert why["site"] == ["named: Lofoten"] and why["site_s"] == ["named: Dry Valleys"]
    sampled = [cid for cid, reasons in why.items() if reasons == ["sample"]]
    assert sorted(sampled) == sorted(c["id"] for c in candidates.sample(north, 4) + candidates.sample(south, 3))
    assert "doubt" not in why and "off" not in why     # the sample is drawn from measured, gridded cells
    assert sizes["sample north"] == 4 and sizes["sample south"] == 3 and sizes["named"] == 2
    assert sizes["union"] == 9


def test_records_have_the_agreed_shape_and_every_reason():
    cells = [cell("70.0_20.0", named="Somewhere", long_snow_free_hours=80.0, long_snow_free_hours_winter=80.0)]
    found, _ = candidates.build(cells, ["malapert"], [], sample_north=1, sample_south=0)
    assert found == [{"id": "70.0_20.0", "lat": 70.05, "lon": 20.0, "hemisphere": "N",
                      "why": ["top malapert year", "top malapert winter", "sample", "named: Somewhere"],
                      "top_position": 1.0}]


def test_top_position_is_the_best_place_in_any_list_as_a_share_of_the_list():
    cells = [cell(f"c{k}", long_snow_free_hours=100.0 - k) for k in range(4)]
    found, _ = candidates.build(cells, ["malapert"], [], sizes={"year": 4, "winter": 0, "summer": 0},
                                sample_north=0, sample_south=0)
    assert {c["id"]: c["top_position"] for c in found} == {"c0": 0.25, "c1": 0.5, "c2": 0.75, "c3": 1.0}
    named_only, _ = candidates.build([cell("x", gridded=False, named="Site")], ["malapert"], [],
                                     sample_north=0, sample_south=0)
    assert named_only[0]["top_position"] is None


def test_only_cells_held_by_top_lists_alone_may_be_dropped_and_the_weakest_go_first():
    found = [{"id": "a", "why": ["top malapert year"], "top_position": 0.2},
             {"id": "b", "why": ["top malapert year", "south top malapert flat"], "top_position": 0.9},
             {"id": "c", "why": ["top malapert year", "sample"], "top_position": 1.0},
             {"id": "d", "why": ["top malapert winter", "named: X"], "top_position": 1.0},
             {"id": "e", "why": ["top malapert year", "rock: Y"], "top_position": 1.0},
             {"id": "f", "why": ["doubtful: would be top malapert year"], "top_position": None},
             {"id": "g", "why": ["top malapert summer"], "top_position": 0.9}]
    assert [c["id"] for c in candidates.drop_order(found)] == ["b", "g", "a"]


# --- added in review: breakages that the tests above did not notice ---

def test_the_lists_and_samples_have_the_agreed_sizes_by_default():
    assert candidates.TOP_NORTH == [("year", "long_snow_free_hours", 300),
                                    ("winter", "long_snow_free_hours_winter", 150),
                                    ("summer", "long_snow_free_hours_summer", 150)]
    assert candidates.TOP_SOUTH == [("summer rock", "long_summer_rock_hours", 150), ("flat", "long_flat_hours", 100)]
    north = [cell(f"n{k}", long_snow_free_hours=1.0 + k, long_snow_free_hours_winter=1.0 + k,
                  long_snow_free_hours_summer=1.0 + k) for k in range(320)]
    south = [cell(f"s{k}", lat=-70.05, status="unmeasured", long_summer_rock_hours=1.0 + k, long_flat_hours=1.0 + k)
             for k in range(170)]
    found, sizes = candidates.build(north + south, ["malapert"], [])
    assert (sizes["top malapert year"], sizes["top malapert winter"], sizes["top malapert summer"]) == (300, 150, 150)
    assert (sizes["south top malapert summer rock"], sizes["south top malapert flat"]) == (150, 100)
    assert (sizes["sample north"], sizes["sample south"]) == (300, 150)
    sampled = [c for c in found if "sample" in c["why"]]
    assert sum(c["hemisphere"] == "N" for c in sampled) == 300 and sum(c["hemisphere"] == "S" for c in sampled) == 150
    assert sizes["union"] == len(found)

def test_the_northern_sample_is_drawn_from_measured_gridded_cells_and_from_nothing_else():
    measured = [cell(f"n{k}") for k in range(6)]
    others = [cell("doubt", status="doubtful"), cell("blank", status="no data"), cell("off", gridded=False),
              cell("site", gridded=False, named="Somewhere")]
    found, sizes = candidates.build(measured + others, ["malapert"], [], sample_north=50, sample_south=50)
    assert sorted(c["id"] for c in found if "sample" in c["why"]) == sorted(c["id"] for c in measured)
    assert sizes["sample north"] == 6 and sizes["sample south"] == 0
    assert {c["id"]: c["why"] for c in found}["site"] == ["named: Somewhere"]


def test_the_sample_does_not_change_when_every_hour_changes():
    def cells(scale):
        return ([cell(f"n{k}", long_snow_free_hours=scale * k, long_flat_hours=scale * (50 - k)) for k in range(50)]
                + [cell(f"s{k}", lat=-70.05, status="unmeasured", long_summer_rock_hours=scale * k) for k in range(50)])
    picks = []
    for scale in (0.0, 1.0, 7.0):
        found, _ = candidates.build(cells(scale), ["malapert"], [], sample_north=10, sample_south=5)
        picks.append(sorted(c["id"] for c in found if "sample" in c["why"]))
    assert picks[0] == picks[1] == picks[2] and len(picks[0]) == 15


def test_a_doubtful_cell_level_with_the_last_member_enters_and_one_just_below_does_not():
    cells = [cell("m1", long_snow_free_hours=80.0), cell("m2", long_snow_free_hours=60.0),
             cell("d_level", status="doubtful", long_snow_free_hours=60.0),
             cell("d_below", status="doubtful", long_snow_free_hours=59.9)]
    found, _ = candidates.build(cells, ["malapert"], [], sizes={"year": 2, "winter": 2, "summer": 2},
                                sample_north=0, sample_south=0)
    assert {c["id"] for c in found} == {"m1", "m2", "d_level"}


def test_a_doubtful_cell_can_enter_by_the_winter_or_the_summer_list_alone():
    cells = [cell("m1", long_snow_free_hours=80.0, long_snow_free_hours_winter=20.0, long_snow_free_hours_summer=60.0),
             cell("d_winter", status="doubtful", long_snow_free_hours=30.0, long_snow_free_hours_winter=25.0,
                  long_snow_free_hours_summer=5.0),
             cell("d_summer", status="doubtful", long_snow_free_hours=70.0, long_snow_free_hours_winter=1.0,
                  long_snow_free_hours_summer=69.0),
             cell("d_mapped_winter", status="doubtful", long_snow_free_hours=1.0, long_snow_free_hours_winter=1.0,
                  long_snow_free_hours_summer=1.0, long_snow_free_hours_as_mapped=25.0)]
    found, sizes = candidates.build(cells, ["malapert"], [], sizes={"year": 1, "winter": 1, "summer": 1},
                                    sample_north=0, sample_south=0)
    why = {c["id"]: c["why"] for c in found}
    assert why["d_winter"] == ["doubtful: would be top malapert winter"]
    assert why["d_summer"] == ["doubtful: would be top malapert summer"]
    assert "d_mapped_winter" not in why      # hours as mapped are a year figure: 25 x 0.5 does not reach 80 x 0.5
    assert sizes["doubtful or no data"] == 2


def test_a_list_that_is_not_full_takes_a_doubtful_cell_with_any_hours():
    cells = [cell("m1", long_snow_free_hours=80.0), cell("d", status="doubtful", long_snow_free_hours=0.1)]
    found, _ = candidates.build(cells, ["malapert"], [], sizes={"year": 5, "winter": 0, "summer": 0},
                                sample_north=0, sample_south=0)
    assert {c["id"]: c["why"] for c in found}["d"] == ["doubtful: would be top malapert year"]


def test_the_rock_margin_is_8_km_and_no_more():
    body = {"name": "Test body", "lat": 70.0, "lon": 20.0, "radius_km": 5.0, "an_low": 80, "an_high": 90}
    cells = [cell("inside", lat=70.11, lon=20.0),        # 12.2 km from the centre: within 5 + 8 km
             cell("outside", lat=70.13, lon=20.0)]       # 14.5 km: beyond
    found, sizes = candidates.build(cells, TARGETS, [body], sample_north=0, sample_south=0)
    assert [c["id"] for c in found] == ["inside"] and sizes["rock"] == 1
    assert candidates.ROCK_MARGIN_KM == 8.0


def test_top_position_keeps_the_best_place_of_a_cell_that_is_in_two_lists():
    cells = [cell("a", long_snow_free_hours=90.0, long_snow_free_hours_winter=1.0),
             cell("b", long_snow_free_hours=80.0, long_snow_free_hours_winter=2.0),
             cell("c", long_snow_free_hours=70.0, long_snow_free_hours_winter=3.0),
             cell("d", long_snow_free_hours=60.0, long_snow_free_hours_winter=9.0)]
    found, _ = candidates.build(cells, ["malapert"], [], sizes={"year": 4, "winter": 2, "summer": 0},
                                sample_north=0, sample_south=0)
    # "d" is last of four by the year and first of two by the winter; "c" is third of four and second of two
    assert {c["id"]: c["top_position"] for c in found} == {"a": 0.25, "b": 0.5, "c": 0.75, "d": 0.5}


def test_a_southern_record_says_south_and_keeps_its_own_position():
    cells = [cell("-70.0_20.0", lat=-70.05, lon=20.5, status="unmeasured", long_summer_rock_hours=5.0)]
    found, _ = candidates.build(cells, ["malapert"], [], sample_north=0, sample_south=0)
    assert found == [{"id": "-70.0_20.0", "lat": -70.05, "lon": 20.5, "hemisphere": "S",
                      "why": ["south top malapert summer rock"], "top_position": 1.0}]


def test_the_script_writes_the_census_beside_the_old_file_and_prints_every_group(tmp_path, monkeypatch, capsys):
    script = importlib.import_module("scripts.build_candidates")
    cells = [cell("n1", long_snow_free_hours=80.0), cell("far", lat=75.05, lon=60.0, status="doubtful"),
             cell("site", lat=-77.5, status="unmeasured", gridded=False, named="Dry Valleys")]
    (tmp_path / "grazing_cells.json").write_text(json.dumps({"meta": {"targets": [{"id": t} for t in TARGETS]},
                                                             "cells": cells}))
    bodies = [{"name": "Test body", "lat": 70.0, "lon": 20.0, "radius_km": 5.0, "an_low": 80, "an_high": 90}]
    (tmp_path / "bodies.json").write_text(json.dumps(bodies))
    out = tmp_path / "candidates.json"
    out.write_text("[]")
    monkeypatch.setattr(script, "CELLS", tmp_path / "grazing_cells.json")
    monkeypatch.setattr(script, "BODIES", tmp_path / "bodies.json")
    monkeypatch.setattr(script, "OUT", out)
    moves = []
    real_replace = script.os.replace
    monkeypatch.setattr(script.os, "replace",
                        lambda source, target: (moves.append((str(source) != str(out), out.read_text())),
                                                real_replace(source, target)))
    script.main()
    expected, sizes = candidates.census(cells, TARGETS, bodies)
    assert json.loads(out.read_text()) == expected and [c["id"] for c in expected] == ["n1", "far", "site"]
    assert "rock: Test body" in expected[0]["why"] and expected[1]["why"] == ["all"]
    assert moves == [(True, "[]")]                        # the old file stays whole until the new one is complete
    assert [p.name for p in tmp_path.iterdir() if p.name.startswith("candidates")] == ["candidates.json"]
    said = capsys.readouterr().out
    assert all(name in said for name in sizes) and "candidates: 3 (north 2, south 1)" in said
    assert "in for the census alone: 1" in said


# --- added in the final step ---

def test_a_candidate_written_without_a_top_position_can_still_be_ordered_and_is_dropped_first():
    found = [{"id": "a", "why": ["top malapert year"], "top_position": 0.2},
             {"id": "b", "why": ["top malapert year"]},                       # the bare shape of the interface
             {"id": "c", "why": ["sample"]}]
    assert [c["id"] for c in candidates.drop_order(found)] == ["b", "a"]


# --- version 3: the blind sample is pinned before the census is added ---
# The ids below are the blind sample as it stood in data/derived/candidates.json on 14 November 2026, before any
# code of version 3 was written: 300 measured gridded northern cells and 150 gridded southern cells.

SAMPLE_NORTH_PINNED = """
59.5_-65.4 59.9_-44.4 60.1_-70.8 60.2_-72.0 60.3_-72.4 60.5_-153.8 60.6_-45.0 60.7_-70.6 60.9_-71.8
61.0_-143.2 61.0_-153.4 61.0_-69.6 61.0_-73.2 61.1_-142.0 61.2_-134.0 61.6_-132.8 61.6_142.2 61.6_173.2
61.7_-75.4 61.8_143.8 61.9_-73.0 61.9_140.0 61.9_143.6 62.0_-67.0 62.0_141.4 62.0_143.4 62.1_171.0
62.2_143.2 62.2_157.8 62.4_141.2 62.5_-42.4 62.5_-70.6 62.6_-127.6 62.7_-42.4 62.9_-126.0 62.9_-49.6
63.0_-42.4 63.0_-67.0 63.2_-41.6 63.2_-42.2 63.3_-144.0 63.3_-65.0 63.4_-66.0 63.7_-127.6 63.8_-50.2
64.0_-127.4 64.0_-71.6 64.0_-85.8 64.1_-65.6 64.1_-83.6 64.1_-88.8 64.2_-69.2 64.3_-130.8 64.4_-131.4
64.4_-136.0 64.4_-173.4 64.4_-19.2 64.5_-131.1 64.6_-132.0 64.7_147.0 64.8_-66.9 64.8_145.2 64.9_-76.2
65.0_-133.5 65.0_-84.3 65.1_144.6 65.3_-15.9 65.3_-51.6 65.3_-75.3 65.4_-86.1 65.4_-87.3 65.4_141.3
65.4_142.2 65.5_-67.5 65.5_-93.9 65.5_140.1 65.8_-72.6 65.8_-85.2 65.9_-37.8 66.0_-176.1 66.1_-180.0
66.1_-86.1 66.1_-89.4 66.2_145.5 66.4_144.0 66.5_-176.4 66.5_-90.9 66.6_144.3 66.7_-62.4 66.9_-88.8
67.1_-62.7 67.1_-69.6 67.1_-88.5 67.3_127.5 67.3_169.5 67.4_176.7 67.5_-67.8 67.6_-65.4 67.6_-76.8
67.8_128.1 67.9_-67.8 68.0_-84.0 68.0_-96.6 68.1_-150.9 68.1_-31.5 68.1_-69.3 68.2_-84.3 68.3_-70.5
68.3_-87.9 68.4_-115.8 68.6_-102.0 68.6_-75.0 68.8_-147.0 68.9_-117.6 68.9_-145.8 68.9_-79.2 68.9_-98.7
68.9_177.9 69.0_-100.5 69.0_-142.8 69.0_-81.6 69.0_-90.3 69.0_128.1 69.1_-144.3 69.1_-83.4 69.1_-96.3
69.2_-142.5 69.2_129.0 69.4_-114.6 69.4_-82.8 69.5_-70.8 69.6_-70.5 69.6_-73.2 69.6_-76.2 69.6_-97.5
69.8_91.8 69.9_-70.5 69.9_25.8 70.0_-53.7 70.0_-70.2 70.0_-92.4 70.1_-72.9 70.2_-83.1 70.2_-92.1 70.3_-25.8
70.3_-53.7 70.3_-72.9 70.3_-73.8 70.4_-69.0 70.4_-75.3 70.4_-76.2 70.5_-54.0 70.5_-75.3 70.6_-113.4
70.6_-26.1 70.6_-69.9 70.6_-93.9 70.6_-94.2 70.6_29.4 70.7_-51.6 70.8_-75.3 70.8_-93.3 71.0_-114.6
71.1_-53.7 71.1_-75.6 71.1_-84.3 71.2_-73.2 71.2_-81.6 71.2_53.4 71.2_53.7 71.3_-93.3 71.5_-121.8 71.5_-82.5
71.6_-24.6 71.7_-76.5 71.7_-89.1 71.7_-98.4 71.9_-112.8 71.9_-75.6 72.1_-86.7 72.1_-94.5 72.3_-119.7
72.3_-80.7 72.4_-108.9 72.4_-23.7 72.4_-79.8 72.5_-75.9 72.6_-101.4 72.6_-107.7 72.7_-23.4 72.7_-93.9
72.9_-95.7 73.0_-94.5 73.1_-115.5 73.2_-25.0 73.3_-24.0 73.4_-83.0 73.4_-88.5 73.4_-95.0 73.5_-56.5
73.7_54.5 73.8_-26.0 73.8_54.0 74.1_-20.5 74.1_-24.5 74.1_57.0 74.5_-86.0 74.5_-88.0 74.5_-90.0 74.7_-20.5
74.8_-80.0 74.8_59.5 75.0_-19.0 75.0_-90.5 75.0_-94.0 75.2_99.5 75.3_-18.0 75.4_-96.0 75.5_109.0 75.7_-84.5
75.8_-107.0 75.8_-121.0 75.8_107.5 75.9_-22.0 75.9_-98.5 75.9_106.5 75.9_139.0 76.0_-115.0 76.0_61.0
76.1_61.0 76.3_-122.5 76.4_-87.0 76.5_-90.0 76.6_-69.0 76.8_-109.0 76.8_-83.5 76.8_-97.0 76.9_-116.0
77.0_16.0 77.1_-66.0 77.3_23.0 77.4_-87.0 77.5_-117.0 77.5_-68.5 77.5_16.0 77.6_-111.0 77.6_-111.5
77.7_-112.0 77.7_-114.0 77.8_-97.0 77.9_15.0 78.0_107.4 78.2_-75.6 78.2_-96.0 78.4_-112.8 78.6_-110.4
78.6_-93.6 78.7_-92.4 78.8_-94.2 78.9_103.2 78.9_19.8 79.0_-82.2 79.1_-82.8 79.2_-80.4 79.2_13.2 79.3_-19.8
79.3_-92.4 79.6_-93.6 79.6_17.4 79.8_99.0 80.1_18.6 80.2_-80.4 80.2_97.2 80.3_-91.8 80.4_-21.6 80.6_-61.8
80.6_-88.2 80.7_-69.0 80.7_-69.6 80.7_-94.8 80.7_93.0 80.7_97.2 80.8_-83.4 80.9_-77.4 80.9_-93.6 81.2_-25.8
81.3_-67.2 81.5_-73.2 81.5_-77.4 81.6_-29.4 81.6_-53.4 81.8_-26.4 81.8_-82.8 81.9_-27.0 81.9_-35.4
82.0_-22.2 82.3_-32.4 82.4_-47.4 82.5_-63.6 82.7_-34.2
""".split()

SAMPLE_SOUTH_PINNED = """
-61.3_-54.2 -62.2_-59.0 -63.0_-60.6 -63.1_-62.6 -63.9_-58.0 -64.3_-59.2 -64.3_-59.8 -64.3_-60.0 -64.5_-60.3
-64.9_-61.5 -64.9_-63.0 -65.1_-62.1 -65.6_-62.4 -65.7_-62.7 -66.2_100.8 -66.4_-63.9 -66.5_110.4 -66.7_99.6
-66.9_50.7 -67.1_51.3 -67.2_50.7 -67.4_49.8 -67.5_-67.8 -67.7_-66.9 -67.8_-68.7 -67.9_-66.9 -68.3_-66.9
-69.3_-72.3 -69.4_-72.0 -70.5_65.1 -70.6_-62.4 -70.6_68.7 -70.9_-68.7 -71.3_67.2 -71.4_13.5 -71.5_-67.5
-71.5_11.4 -71.5_67.5 -71.6_-68.4 -71.6_11.4 -71.6_12.0 -71.6_12.3 -71.6_163.2 -71.6_67.2 -71.8_164.7
-71.8_169.8 -71.8_24.9 -71.8_9.6 -71.9_11.4 -71.9_163.5 -72.0_24.3 -72.0_6.0 -72.0_8.7 -72.1_24.6 -72.1_25.5
-72.1_4.5 -72.2_2.7 -72.2_24.3 -72.3_164.4 -72.3_24.9 -72.5_170.1 -72.8_68.4 -73.0_162.5 -73.6_169.5
-73.6_60.5 -74.0_162.5 -74.0_164.5 -74.1_163.0 -74.2_163.5 -74.4_162.0 -74.4_162.5 -74.8_163.5 -75.0_163.5
-75.7_160.5 -76.6_160.5 -76.8_161.5 -77.0_162.0 -77.2_160.0 -77.2_160.5 -77.6_160.0 -77.6_161.5 -77.7_163.5
-77.8_160.5 -77.8_161.5 -77.9_162.5 -78.2_-85.8 -78.3_163.2 -78.4_-86.4 -78.5_-86.4 -78.7_-85.8 -78.7_160.8
-78.8_-86.4 -79.2_156.6 -79.4_157.2 -79.6_-83.4 -79.8_-81.6 -79.8_-84.6 -79.9_158.4 -80.2_157.8 -80.7_-25.2
-82.0_162.6 -82.3_158.4 -82.8_154.8 -82.8_161.4 -83.1_156.6 -83.3_156.0 -83.6_171.0 -83.7_-55.8 -83.8_159.6
-83.8_162.6 -83.8_163.2 -83.8_168.0 -83.9_159.0 -83.9_159.6 -83.9_171.6 -84.4_-63.6 -84.4_164.4 -84.4_169.2
-84.5_168.0 -84.7_-63.6 -84.9_-175.2 -84.9_-176.4 -84.9_-63.6 -84.9_-64.8 -84.9_-66.0 -84.9_177.6
-85.0_-169.2 -85.0_176.4 -85.1_-172.8 -85.1_170.4 -85.2_165.6 -85.2_170.4 -85.5_170.4 -85.6_-126.0
-85.6_-157.2 -85.7_-129.6 -85.7_-138.0 -85.8_-132.0 -85.9_-158.4 -85.9_-162.0 -85.9_174.0 -86.0_-129.6
-86.0_-133.2 -86.0_-153.6 -86.0_-158.4 -86.0_-162.0 -86.2_-150.0 -86.3_-127.2 -86.3_-147.6 -87.4_-150.0
""".split()


GRAZING_CELLS = Path("data/derived/grazing_cells.json")
CANDIDATES_FILE = Path("data/derived/candidates.json")


def real_cells():
    if not GRAZING_CELLS.exists():
        pytest.skip("data/derived/grazing_cells.json is not here")
    return json.loads(GRAZING_CELLS.read_text())


def test_the_pinned_sample_has_300_northern_and_150_southern_ids_and_no_id_twice():
    assert len(SAMPLE_NORTH_PINNED) == len(set(SAMPLE_NORTH_PINNED)) == 300
    assert len(SAMPLE_SOUTH_PINNED) == len(set(SAMPLE_SOUTH_PINNED)) == 150
    assert all(float(cid.split("_")[0]) > 0 for cid in SAMPLE_NORTH_PINNED)
    assert all(float(cid.split("_")[0]) < 0 for cid in SAMPLE_SOUTH_PINNED)
    assert hashlib.sha256("\n".join(SAMPLE_NORTH_PINNED).encode()).hexdigest() == \
        "0561069deee46612f66dd2980899df116ef5d6802032a2d1db49508fc2774714"
    assert hashlib.sha256("\n".join(SAMPLE_SOUTH_PINNED).encode()).hexdigest() == \
        "ce512fcfee2e7f312760d187304871cf767917b2aeba2ddd98f980924d4a847e"


def test_the_blind_sample_drawn_from_the_real_cells_is_exactly_the_pinned_ids():
    cells = real_cells()["cells"]
    measured = [c for c in cells if c["hemisphere"] == "N" and c["gridded"] and c["snow"]["status"] == "measured"]
    south = [c for c in cells if c["hemisphere"] == "S" and c["gridded"]]
    assert sorted(c["id"] for c in candidates.sample(measured, 300)) == SAMPLE_NORTH_PINNED
    assert sorted(c["id"] for c in candidates.sample(south, 150)) == SAMPLE_SOUTH_PINNED


def test_the_candidates_file_marks_exactly_the_pinned_ids_as_the_sample():
    if not CANDIDATES_FILE.exists():
        pytest.skip("data/derived/candidates.json is not here")
    listed = json.loads(CANDIDATES_FILE.read_text())
    marked = {hemisphere: sorted(c["id"] for c in listed if c["hemisphere"] == hemisphere and "sample" in c["why"])
              for hemisphere in "NS"}
    assert marked == {"N": SAMPLE_NORTH_PINNED, "S": SAMPLE_SOUTH_PINNED}


# --- version 3, decision 15: every cell is a candidate ---

def test_the_census_lists_every_cell_in_the_order_given_and_marks_cells_with_no_other_reason_as_all():
    cells = [cell("m1", long_snow_free_hours=80.0), cell("m2", long_snow_free_hours=60.0),
             cell("m3", long_snow_free_hours=10.0), cell("doubt", status="doubtful"),
             cell("blank", status="no data"), cell("off", gridded=False),
             cell("s1", lat=-70.05, status="unmeasured"), cell("site", gridded=False, named="Lofoten")]
    kinds = dict(sizes={"year": 2, "winter": 0, "summer": 0, "summer rock": 0, "flat": 0},
                 sample_north=0, sample_south=0)
    chosen, chosen_sizes = candidates.build(cells, ["malapert"], [], **kinds)
    found, sizes = candidates.census(cells, ["malapert"], [], **kinds)
    assert [c["id"] for c in found] == [c["id"] for c in cells]
    why = {c["id"]: c["why"] for c in found}
    assert {cid: why[cid] for cid in ("m1", "m2", "site")} == {c["id"]: c["why"] for c in chosen}   # the old reasons, unchanged
    assert all(why[cid] == ["all"] for cid in ("m3", "doubt", "blank", "off", "s1"))
    assert not any("all" in why[cid] for cid in ("m1", "m2", "site"))      # "all" marks the cells the census alone brought in
    assert sizes["all"] == 5 and sizes["union"] == 8
    assert {name: size for name, size in sizes.items() if name not in ("all", "union")} == \
           {name: size for name, size in chosen_sizes.items() if name != "union"}


def test_a_census_record_keeps_top_position_and_says_how_bare_the_cell_is_and_how_its_snow_is_known():
    cells = [cell("70.0_20.0", bare=0.4, long_snow_free_hours=80.0), cell("70.0_21.0", lon=21.0, bare=0.3),
             cell("-70.0_20.0", lat=-70.05, bare=None, status="unmeasured")]
    found, _ = candidates.census(cells, ["malapert"], [], sizes={"year": 1, "winter": 0, "summer": 0},
                                 sample_north=0, sample_south=0)
    assert found == [
        {"id": "70.0_20.0", "lat": 70.05, "lon": 20.0, "hemisphere": "N", "why": ["top malapert year"],
         "top_position": 1.0, "bare": 0.4, "snow_status": "measured"},
        {"id": "70.0_21.0", "lat": 70.05, "lon": 21.0, "hemisphere": "N", "why": ["all"],
         "top_position": None, "bare": 0.3, "snow_status": "measured"},
        {"id": "-70.0_20.0", "lat": -70.05, "lon": 20.0, "hemisphere": "S", "why": ["all"],
         "top_position": None, "bare": None, "snow_status": "unmeasured"}]


def test_the_census_marks_the_same_sample_as_the_reasoned_choice():
    north = [cell(f"n{k}", long_snow_free_hours=float(k)) for k in range(40)]
    south = [cell(f"s{k}", lat=-70.05, status="unmeasured") for k in range(40)]
    chosen, _ = candidates.build(north + south, ["malapert"], [], sample_north=7, sample_south=4)
    found, sizes = candidates.census(north + south, ["malapert"], [], sample_north=7, sample_south=4)
    marked = sorted(c["id"] for c in found if "sample" in c["why"])
    assert marked == sorted(c["id"] for c in chosen if "sample" in c["why"]) and len(marked) == 11
    assert sizes["sample north"] == 7 and sizes["sample south"] == 4 and len(found) == 80


def test_the_census_of_the_real_cells_holds_every_cell_and_the_pinned_sample_and_nothing_else_is_marked_sample():
    grazing = real_cells()
    bodies = json.loads(Path("data/reference/anorthosite_bodies.json").read_text())
    found, sizes = candidates.census(grazing["cells"], [t["id"] for t in grazing["meta"]["targets"]], bodies)
    assert [c["id"] for c in found] == [c["id"] for c in grazing["cells"]]
    assert len({c["id"] for c in found}) == len(found) == sizes["union"]
    assert sorted(c["id"] for c in found if c["hemisphere"] == "N" and "sample" in c["why"]) == SAMPLE_NORTH_PINNED
    assert sorted(c["id"] for c in found if c["hemisphere"] == "S" and "sample" in c["why"]) == SAMPLE_SOUTH_PINNED
    assert all(c["why"] for c in found) and sizes["all"] == sum(c["why"] == ["all"] for c in found)
    assert all(set(c) == {"id", "lat", "lon", "hemisphere", "why", "top_position", "bare", "snow_status"} for c in found)


def test_the_candidates_file_holds_every_cell_of_the_grazing_file():
    if not CANDIDATES_FILE.exists():
        pytest.skip("data/derived/candidates.json is not here")
    listed = json.loads(CANDIDATES_FILE.read_text())
    assert [c["id"] for c in listed] == [c["id"] for c in real_cells()["cells"]]
    assert all("top_position" in c and c["why"] for c in listed)


def test_the_order_of_work_is_rankable_northern_cells_then_other_northern_cells_then_the_south():
    assert candidates.RANK_MIN_BARE == 0.25
    north = {"hemisphere": "N", "snow_status": "measured", "bare": 0.25}
    assert candidates.census_class(north) == 0
    assert candidates.census_class(dict(north, bare=0.249)) == 1
    assert candidates.census_class(dict(north, bare=None)) == 1
    assert candidates.census_class(dict(north, snow_status="doubtful")) == 1
    assert candidates.census_class(dict(north, snow_status="no data")) == 1
    assert candidates.census_class({"hemisphere": "S", "snow_status": "unmeasured", "bare": 0.9}) == 2
    assert candidates.census_class({"id": "old record without the new keys"}) == 1


def test_the_bare_limit_for_ranking_is_the_one_the_scoring_uses():
    from twinfinder import score
    assert candidates.RANK_MIN_BARE == score.RANK_MIN_BARE


def test_census_cells_are_the_first_to_be_left_out_south_before_north_and_rankable_cells_last():
    def census_cell(cid, hemisphere, bare, status):
        return {"id": cid, "hemisphere": hemisphere, "bare": bare, "snow_status": status, "why": ["all"],
                "top_position": None}
    found = [census_cell("n_rank_b", "N", 0.5, "measured"), census_cell("n_rank_a", "N", 0.3, "measured"),
             census_cell("n_thin", "N", 0.2, "measured"), census_cell("n_doubt", "N", 0.9, "doubtful"),
             census_cell("s_b", "S", 0.9, "unmeasured"), census_cell("s_a", "S", 0.2, "unmeasured"),
             {"id": "top_weak", "why": ["top malapert year"], "top_position": 0.9},
             {"id": "top_strong", "why": ["south top malapert flat"], "top_position": 0.1},
             {"id": "sampled", "why": ["sample"], "top_position": None},
             {"id": "named", "why": ["top malapert year", "named: X"], "top_position": 0.5}]
    assert all(candidates.droppable(c) for c in found[:8]) and not any(candidates.droppable(c) for c in found[8:])
    assert [c["id"] for c in candidates.drop_order(found)] == ["s_a", "s_b", "n_doubt", "n_thin", "n_rank_a", "n_rank_b",
                                                              "top_weak", "top_strong"]

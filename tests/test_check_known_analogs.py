# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
import importlib
import json

import pytest

check = importlib.import_module("scripts.check_known_analogs")


# ---- distance ----

def test_one_degree_of_latitude_is_about_111_km():
    assert check.km(0.0, 0.0, 1.0, 0.0) == pytest.approx(111.19, abs=0.05)
    assert check.km(75.0, 141.0, 75.0, 141.0) == 0.0


def test_distance_shrinks_with_the_cosine_of_latitude():
    assert check.km(60.0, 0.0, 60.0, 1.0) == pytest.approx(111.19 * 0.5, rel=0.01)


def test_distance_across_the_antimeridian_is_short():
    assert check.km(70.0, 179.5, 70.0, -179.5) < 40.0


# ---- the Wikipedia table ----

WIKI_SAMPLE = """intro text
{|class="wikitable"
|+List of currently used analogue sites
|-
! Location name !! Coordinates
|- valign="top"
| [[Devon Island]], Canada <BR> {{Location map | Canada
| relief  =
| label   = Haughton impact Crater
| lat_deg = 75 | lat_min =  23 | lat_sec = 0 | lat_dir = N
| lon_deg = 89 | lon_min = 40 | lon_sec = 0 | lon_dir = W }}
| text
|- valign="top"
| [[McMurdo Dry Valleys]], Antarctica <BR> {{Location map | Antarctica
| relief  =
| label   = McMurdo Dry Valleys
| lat_deg  = -77.466667
| lon_deg  = 162.516667  }}
| text
|-
|[[CHILL-ICE]], [[Iceland]]
|64.7869, -20.7144
|Volcanic analogue site
|-
|[[Asclepios Project|Asclepios]], [[Switzerland]]
| - (several locations)
|Student-led project
|}
"""


def test_wikipedia_rows_with_a_location_map_are_read_in_degrees_minutes_and_direction():
    rows = {r["name"]: r for r in check.parse_wikipedia_table(WIKI_SAMPLE)}
    haughton = rows["Haughton impact Crater"]
    assert haughton["lat"] == pytest.approx(75 + 23 / 60) and haughton["lon"] == pytest.approx(-(89 + 40 / 60))
    assert rows["McMurdo Dry Valleys"]["lat"] == pytest.approx(-77.466667)
    assert rows["McMurdo Dry Valleys"]["lon"] == pytest.approx(162.516667)


def test_wikipedia_rows_with_a_plain_pair_are_read_and_rows_without_a_point_are_kept_as_unknown():
    rows = {r["name"]: r for r in check.parse_wikipedia_table(WIKI_SAMPLE)}
    assert rows["CHILL-ICE, Iceland"]["lat"] == pytest.approx(64.7869)
    assert rows["CHILL-ICE, Iceland"]["lon"] == pytest.approx(-20.7144)
    assert rows["Asclepios, Switzerland"]["lat"] is None and rows["Asclepios, Switzerland"]["lon"] is None
    assert len(rows) == 4


# ---- comparing a published list with ours ----

OURS = [{"name": "Haughton impact structure, Devon Island", "lat": 75.383, "lon": -89.667},
        {"name": "Svalbard (AMASE)", "lat": 78.0, "lon": 16.0},
        {"name": "Atacama", "lat": -24.5, "lon": -69.25}]


def test_a_published_site_further_than_the_radius_from_all_of_ours_is_missing():
    published = [{"name": "Murchison Fjord", "lat": 79.8786, "lon": 18.4881}]
    missing, covered = check.compare(published, OURS, radius_km=50.0, min_abs_lat=55.0)
    assert [m["name"] for m in missing] == ["Murchison Fjord"] and covered == []
    assert missing[0]["nearest_of_ours"]["name"] == "Svalbard (AMASE)"
    assert missing[0]["nearest_of_ours"]["km"] > 200


def test_a_published_site_inside_the_radius_is_covered_and_low_latitudes_are_left_out():
    published = [{"name": "Adventtoppen", "lat": 78.273, "lon": 15.745},
                 {"name": "Yungay", "lat": -24.06, "lon": -69.92},
                 {"name": "No point", "lat": None, "lon": None}]
    missing, covered = check.compare(published, OURS, radius_km=50.0, min_abs_lat=55.0)
    assert missing == []
    assert [c["name"] for c in covered] == ["Adventtoppen"]
    assert covered[0]["nearest_of_ours"]["km"] == pytest.approx(31.0, abs=1.0)


def test_same_site_pairs_further_apart_than_the_tolerance_are_reported():
    published = [{"name": "Haughton", "lat": 75.3667, "lon": -89.6833, "listed_in": "x", "source_url": "u"},
                 {"name": "Far", "lat": 75.0, "lon": 30.0, "listed_in": "x", "source_url": "u"}]
    pairs = {"Haughton": "Haughton impact structure", "Far": "Svalbard (AMASE)", "Gone": "Not in our list"}
    out = check.offsets(published, OURS, pairs, tolerance_km=10.0)
    assert [o["ours"] for o in out] == ["Svalbard (AMASE)"]
    assert out[0]["published_name"] == "Far" and out[0]["km_apart"] > 200


def test_an_entry_is_not_doubtful_when_any_published_point_of_the_same_site_agrees():
    published = [{"name": "Rounded", "lat": 75.0, "lon": -80.0}, {"name": "Exact", "lat": 75.383, "lon": -89.66}]
    pairs = {"Rounded": "Haughton impact structure", "Exact": "Haughton impact structure"}
    assert check.offsets(published, OURS, pairs, tolerance_km=10.0) == []


def test_nearest_gives_none_beyond_the_largest_distance_that_still_means_something():
    points = [{"name": "A", "lat": 78.9, "lon": 11.9}]
    assert check.nearest(63.75, -20.7, points, max_km=800.0) is None
    assert check.nearest(63.75, -20.7, points)["name"] == "A"


def test_nearest_picks_the_closest_point_and_gives_none_for_an_empty_list():
    points = [{"name": "A", "lat": 68.94, "lon": 53.77}, {"name": "B", "lat": 67.64, "lon": 53.125}]
    hit = check.nearest(68.95, 54.45, points)
    assert hit["name"] == "A" and hit["km"] == pytest.approx(27.2, abs=1.0)
    assert check.nearest(68.95, 54.45, []) is None


# ---- cells near a point ----

def test_cells_near_counts_cells_and_little_known_flags_and_is_none_without_cells():
    cells = [{"id": "a", "lat": 80.15, "lon": 18.3, "little_known": True, "known": None},
             {"id": "b", "lat": 80.05, "lon": 18.9, "little_known": False, "known": "x"},
             {"id": "c", "lat": 60.0, "lon": 0.0, "little_known": True, "known": None}]
    assert check.cells_near(80.1, 18.5, cells, 50.0) == {"cells": 2, "flagged_little_known": 1}
    assert check.cells_near(80.1, 18.5, None, 50.0) is None


# ---- the curated tables ----

def test_every_curated_point_has_coordinates_in_range_and_a_source():
    rows = check.CATALOGUE_SITES + check.OTHER_PUBLISHED_SITES + check.FACILITIES
    assert len(check.CATALOGUE_SITES) >= 15
    for row in rows:
        assert -90 <= row["lat"] <= 90 and -180 <= row["lon"] <= 180, row["name"]
        assert row["source_url"].startswith("https://"), row["name"]


def test_every_top_place_has_points_and_a_finding_with_sources():
    names = [p["name"] for p in check.TOP_PLACES]
    assert len(names) == len(set(names)) == 10
    for place in check.TOP_PLACES:
        assert place["points"] and all(len(p) == 2 for p in place["points"])
        assert place["analog_use_found"] in (True, False)
        assert place["evidence"] and all(e["url"].startswith("https://") for e in place["evidence"])


# ---- the whole file ----

def test_build_writes_the_three_lists_and_keeps_unknown_as_null(tmp_path):
    ours = tmp_path / "known.json"
    ours.write_text(json.dumps(OURS))
    wiki = tmp_path / "wiki.txt"
    wiki.write_text(WIKI_SAMPLE)
    out = tmp_path / "check.json"
    result = check.build(known_path=ours, wiki_path=wiki, comnap_path=tmp_path / "absent.geojson",
                         cells_path=tmp_path / "absent.json", antarctic_path=tmp_path / "absent2.json", out_path=out)
    on_disk = json.loads(out.read_text())
    assert on_disk == result
    assert {"meta", "missing_from_our_list", "doubtful_in_our_list", "top_places"} <= set(on_disk)
    assert "Murchison Fjord (AMASE)" in [m["name"] for m in on_disk["missing_from_our_list"]]
    assert len(on_disk["top_places"]) == 10
    place = on_disk["top_places"][0]
    assert place["cells_within_50_km"] is None                 # no scored cells given: unknown, not 0
    vestfold = next(p for p in on_disk["top_places"] if p["name"].startswith("Vestfold"))
    assert vestfold["nearest_comnap_facility"] is None          # no COMNAP file given
    assert not list(tmp_path.glob("*.tmp"))                     # written to a side file and renamed
    iceland = next(p for p in on_disk["top_places"] if p["name"].startswith("Iceland"))
    assert iceland["points"][0]["nearest_station"]["km"] < 150  # never a station in another country
    assert [d["ours"] for d in on_disk["doubtful_in_our_list"]].count("Svalbard (AMASE)") == 1


def test_build_uses_the_comnap_file_and_the_scored_cells_when_they_exist(tmp_path):
    ours = tmp_path / "known.json"
    ours.write_text(json.dumps(OURS))
    wiki = tmp_path / "wiki.txt"
    wiki.write_text(WIKI_SAMPLE)
    comnap = tmp_path / "comnap.geojson"
    comnap.write_text(json.dumps({"features": [
        {"properties": {"facility_name_english": "Davis", "type": "Station", "seasonality": "Year-Round",
                        "status": "Open", "latitude_dd": -68.5759, "longitude_dd": 77.9695}},
        {"properties": {"facility_name_english": "Soyuz", "type": "Station", "seasonality": "Seasonal",
                        "status": "Temporarily Closed", "latitude_dd": -70.5766, "longitude_dd": 68.7949}}]}))
    cells = tmp_path / "cells.json"
    cells.write_text(json.dumps({"meta": {"written": "T"}, "cells": [
        {"id": "80.1_18.3", "lat": 80.15, "lon": 18.3, "little_known": True, "known": None}]}))
    out = tmp_path / "check.json"
    result = check.build(known_path=ours, wiki_path=wiki, comnap_path=comnap, cells_path=cells,
                         antarctic_path=tmp_path / "absent.json", out_path=out)
    vestfold = next(p for p in result["top_places"] if p["name"].startswith("Vestfold"))
    assert vestfold["nearest_comnap_facility"]["name"] == "Davis"
    assert "lat" not in vestfold["nearest_comnap_facility"]     # COMNAP coordinates are not copied into our file
    assert "non-commercial" in vestfold["nearest_comnap_facility"]["from"]
    assert result["meta"]["our_list"]["entries_citing_wikipedia"] == 0
    assert vestfold["nearest_year_round_comnap_station"]["km"] < 20
    north = next(p for p in result["top_places"] if p["name"].startswith("Nordaustlandet"))
    assert north["cells_within_50_km"] == {"cells": 1, "flagged_little_known": 1}
    murchison = next(m for m in result["missing_from_our_list"] if m["name"] == "Murchison Fjord (AMASE)")
    assert murchison["cells_within_50_km"] == {"cells": 1, "flagged_little_known": 1}
    assert result["meta"]["cells_scored_written"] == "T"


def test_shared_runs_counts_entries_whose_description_repeats_six_words_of_a_text():
    entries = [{"analog_for": "Cold dry valleys with polygons and gullies everywhere"}, {"analog_for": "Our own words"}]
    text = "the cold   dry valleys with polygons and gullies are famous"
    assert check.shared_runs(entries, text, words=6) == 1
    assert check.shared_runs(entries, "nothing alike", words=6) == 0


# ---- added by the member ADDITIONS-CHECK (14 November 2026) ----

def test_a_southern_published_site_poleward_of_55_is_compared_too():
    ours = [{"name": "Concordia Station (Dome C)", "lat": -75.1, "lon": 123.33}]
    published = [{"name": "Deep Lake, Vestfold Hills", "lat": -68.56, "lon": 78.196},
                 {"name": "Atacama", "lat": -24.1, "lon": -69.9}]
    missing, covered = check.compare(published, ours)
    assert [row["name"] for row in missing] == ["Deep Lake, Vestfold Hills"] and covered == []

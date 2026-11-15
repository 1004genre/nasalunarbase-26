# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Distance from every cell to the nearest airfield (scripts/build_access_cells.py). No test touches the network."""
from __future__ import annotations

import importlib
import json
import math
import random
from pathlib import Path

import numpy as np
import pytest

from twinfinder import reference

build = importlib.import_module("scripts.build_access_cells")

R = 6371.0   # the mean Earth radius the project uses (twinfinder/reference.py)
HEADER = ('"id","ident","type","name","latitude_deg","longitude_deg","elevation_ft","continent","iso_country",'
          '"iso_region","municipality","scheduled_service","icao_code","iata_code","gps_code","local_code",'
          '"home_link","wikipedia_link","keywords"')


def line(ident, kind, name, lat, lon, country="CA", scheduled="no", municipality=""):
    """One row laid out like the real table."""
    return (f'1,"{ident}","{kind}","{name}",{lat},{lon},10,"NA","{country}","{country}-XX","{municipality}",'
            f'"{scheduled}",,,,,,,')


def table(tmp_path: Path, *lines: str) -> Path:
    path = tmp_path / "airports.csv"
    path.write_text("\n".join((HEADER,) + lines) + "\n", encoding="utf-8")
    return path


def field(ident, lat, lon, kind="small_airport", scheduled=False, country="CA", name=None, municipality=None):
    return {"ident": ident, "type": kind, "name": name or f"{ident} field", "lat": lat, "lon": lon,
            "country": country, "municipality": municipality, "scheduled": scheduled}


def cell(cid, lat, lon):
    return {"id": cid, "lat": lat, "lon": lon}


# ---------------------------------------------------------------- distance

def test_distance_quarter_of_the_equator():
    # 90 degrees of arc: a quarter of the circumference, pi / 2 times the radius = 10,007.54 km
    assert build.great_circle_km(0.0, 0.0, 0.0, 90.0) == pytest.approx(math.pi / 2 * R, abs=1e-6)
    assert build.great_circle_km(0.0, 0.0, 0.0, 90.0) == pytest.approx(10007.543, abs=0.001)


def test_distance_one_degree_along_a_meridian():
    # one degree of arc is the radius times pi / 180 = 111.195 km, at any latitude
    assert build.great_circle_km(70.0, 20.0, 71.0, 20.0) == pytest.approx(111.195, abs=0.001)
    assert build.great_circle_km(-80.0, -150.0, -81.0, -150.0) == pytest.approx(111.195, abs=0.001)


def test_distance_goes_over_the_pole_not_round_the_parallel():
    # 60 N on opposite meridians: the short way is over the pole, 30 + 30 = 60 degrees of arc
    # = radius times pi / 3 = 6,671.70 km. Round the parallel it would be 10,007.5 km.
    assert build.great_circle_km(60.0, 0.0, 60.0, 180.0) == pytest.approx(6671.696, abs=0.001)


def test_distance_pole_to_pole_and_across_the_antimeridian():
    assert build.great_circle_km(90.0, 0.0, -90.0, 0.0) == pytest.approx(math.pi * R, abs=1e-6)
    assert build.great_circle_km(0.0, 179.5, 0.0, -179.5) == pytest.approx(111.195, abs=0.001)
    assert build.great_circle_km(12.0, 34.0, 12.0, 34.0) == 0.0


def test_distance_agrees_with_the_projects_own_function_and_takes_arrays():
    rng = random.Random(7)
    points = [(rng.uniform(-90, 90), rng.uniform(-180, 180), rng.uniform(-90, 90), rng.uniform(-180, 180))
              for _ in range(200)]
    a = np.array(points)
    got = build.great_circle_km(a[:, 0], a[:, 1], a[:, 2], a[:, 3])
    assert got.shape == (200,)
    for value, p in zip(got, points):
        assert value == pytest.approx(reference.haversine_km(*p), abs=1e-6)


# ---------------------------------------------------------------- reading the table

def test_read_airfields_parses_the_real_layout(tmp_path):
    path = table(tmp_path,
                 line("CYHK", "small_airport", "Gjoa Haven Airport", 68.635597, -95.849701, "CA", "yes", "Gjoa Haven"),
                 line("NO-0034", "closed", "Longyearbyen Airport, Adventdalen", 78.202486, 15.8237, "NO", "no"),
                 line("BGNO", "heliport", "Station Nord Heliport", 81.697844, -17.808838, "GL", "no"))
    rows, skipped = build.read_airfields(path)
    assert skipped == 0
    assert [r["ident"] for r in rows] == ["BGNO", "CYHK", "NO-0034"]   # ordered by ident, so a tie always falls the same way
    gjoa = rows[1]
    assert gjoa == {"ident": "CYHK", "type": "small_airport", "name": "Gjoa Haven Airport", "lat": 68.635597,
                    "lon": -95.849701, "country": "CA", "municipality": "Gjoa Haven", "scheduled": True}
    assert rows[0]["municipality"] is None and rows[0]["scheduled"] is False


def test_read_airfields_skips_rows_without_a_usable_position(tmp_path):
    path = table(tmp_path,
                 line("AAA", "small_airport", "no latitude", "", 10.0),
                 line("BBB", "small_airport", "not a number", "north", 10.0),
                 line("CCC", "small_airport", "off the globe", 95.0, 10.0),
                 line("DDD", "small_airport", "fine", 60.0, 10.0))
    rows, skipped = build.read_airfields(path)
    assert [r["ident"] for r in rows] == ["DDD"]
    assert skipped == 3


def test_kept_and_dropped_types():
    assert set(build.KEEP_TYPES) == {"small_airport", "medium_airport", "large_airport"}
    assert set(build.DROP_TYPES) == {"heliport", "seaplane_base", "balloonport", "closed"}
    rows = [field("A", 60, 0, "small_airport"), field("B", 60, 0, "medium_airport"), field("C", 60, 0, "large_airport"),
            field("D", 60, 0, "heliport", scheduled=True), field("E", 60, 0, "seaplane_base", scheduled=True),
            field("F", 60, 0, "balloonport"), field("G", 60, 0, "closed"), field("H", 60, 0, "spaceport")]
    assert [r["ident"] for r in build.fixed_wing(rows)] == ["A", "B", "C"]
    # a type the table did not have when this was written is not kept on trust, and it is counted
    assert build.type_counts(rows)["unknown_dropped"] == {"spaceport": 1}
    assert build.type_counts(rows)["kept"] == {"small_airport": 1, "medium_airport": 1, "large_airport": 1}
    assert build.type_counts(rows)["dropped"] == {"heliport": 1, "seaplane_base": 1, "balloonport": 1, "closed": 1}


def test_scheduled_means_fixed_wing_with_scheduled_service():
    rows = [field("A", 60, 0, "small_airport", scheduled=True), field("B", 60, 0, "medium_airport"),
            field("D", 60, 0, "heliport", scheduled=True), field("G", 60, 0, "closed", scheduled=True)]
    assert [r["ident"] for r in build.scheduled(rows)] == ["A"]


# ---------------------------------------------------------------- nearest

def test_nearest_matches_a_plain_loop():
    rng = random.Random(11)
    cells = [(rng.choice([-1, 1]) * rng.uniform(59, 88), rng.uniform(-180, 180)) for _ in range(300)]
    fields = [(rng.uniform(-90, 90), rng.uniform(-180, 180)) for _ in range(60)]   # few enough that some cells find none
    lat, lon = np.array(cells).T
    flat, flon = np.array(fields).T
    index, km = build.nearest(lat, lon, flat, flon, max_km=1500.0, chunk=64)
    found = 0
    for i, (clat, clon) in enumerate(cells):
        distances = [reference.haversine_km(clat, clon, a, b) for a, b in fields]
        best = min(range(len(fields)), key=distances.__getitem__)
        if distances[best] <= 1500.0:
            found += 1
            assert index[i] == best
            assert km[i] == pytest.approx(distances[best], abs=1e-6)
        else:
            assert index[i] == -1 and math.isnan(km[i])
    assert 0 < found < len(cells)   # the test saw both answers


def test_nearest_is_none_past_the_limit_and_found_just_inside():
    # along a meridian 1,500 km is 13.4898 degrees
    lat, lon = np.array([70.0]), np.array([0.0])
    index, km = build.nearest(lat, lon, np.array([70.0 - 13.52]), np.array([0.0]), max_km=1500.0)
    assert index[0] == -1 and math.isnan(km[0])
    index, km = build.nearest(lat, lon, np.array([70.0 - 13.46]), np.array([0.0]), max_km=1500.0)
    assert index[0] == 0 and km[0] == pytest.approx(13.46 * math.pi / 180 * R, abs=1e-6)


def test_nearest_sees_across_the_antimeridian_and_over_the_pole():
    index, km = build.nearest(np.array([70.0, 89.0]), np.array([179.9, 0.0]),
                              np.array([70.0, 70.0, 88.5]), np.array([170.0, -179.9, 180.0]), max_km=1500.0)
    assert index[0] == 1 and km[0] == pytest.approx(reference.haversine_km(70, 179.9, 70, -179.9), abs=1e-6)
    assert index[1] == 2 and km[1] == pytest.approx(2.5 * math.pi / 180 * R, abs=1e-6)   # 1 + 1.5 degrees over the pole


def test_nearest_with_no_fields_at_all():
    index, km = build.nearest(np.array([70.0]), np.array([0.0]), np.array([]), np.array([]), max_km=1500.0)
    assert index[0] == -1 and math.isnan(km[0])


# ---------------------------------------------------------------- the records

def test_cell_records_have_the_agreed_shape():
    rows = [field("CYHK", 68.635597, -95.849701, "small_airport", True, "CA", "Gjoa Haven Airport", "Gjoa Haven"),
            field("STRIP", 68.30, -96.20, "small_airport", False, "CA", "A gravel strip"),
            field("PAD", 68.26, -96.14, "heliport", True, "CA", "A helipad next door")]
    records = build.build_cells([cell("68.2_-96.3", 68.25, -96.15)], rows)
    record = records["68.2_-96.3"]
    assert set(record) == {"nearest", "nearest_scheduled", "country"}
    assert record["nearest"] == {"name": "A gravel strip", "ident": "STRIP", "country": "CA", "type": "small_airport",
                                 "km": round(reference.haversine_km(68.25, -96.15, 68.30, -96.20), 1),
                                 "municipality": None, "scheduled_service": False, "lat": 68.3, "lon": -96.2}
    assert record["nearest_scheduled"]["ident"] == "CYHK"          # the helipad with scheduled service is not taken
    assert record["nearest_scheduled"]["name"] == "Gjoa Haven Airport"
    assert record["nearest_scheduled"]["municipality"] == "Gjoa Haven"
    assert record["nearest_scheduled"]["km"] == round(reference.haversine_km(68.25, -96.15, 68.635597, -95.849701), 1)
    assert record["country"] == "CA"


def test_unknown_is_null_never_zero():
    rows = [field("FAR", 50.0, 0.0, "medium_airport", True, "GB"),        # about 2,200 km away
            field("NEAR", 66.0, 0.0, "small_airport", False, "NO")]       # about 445 km away
    record = build.build_cells([cell("x", 70.0, 0.0)], rows)["x"]
    assert record["nearest"]["ident"] == "NEAR"
    assert record["nearest_scheduled"] is None        # none within 1,500 km
    assert record["country"] is None                  # no field of any kind within 300 km
    empty = build.build_cells([cell("x", 70.0, 0.0)], [])["x"]
    assert empty == {"nearest": None, "nearest_scheduled": None, "country": None}


def test_country_comes_from_the_nearest_record_of_any_kind_within_300_km():
    rows = [field("PAD", 77.0, -68.0, "heliport", False, "GL"),            # 111 km: a helipad still says whose land it is
            field("RWY", 78.0, -76.0, "small_airport", False, "CA"),       # about 190 km
            field("OLD", 79.5, -68.0, "closed", False, "GL")]
    record = build.build_cells([cell("x", 78.0, -68.0)], rows)["x"]
    assert record["nearest"]["ident"] == "RWY" and record["nearest"]["country"] == "CA"
    assert record["country"] == "GL"
    just_outside = build.build_cells([cell("x", 78.0, -68.0)], [field("PAD", 75.2, -68.0, "heliport", False, "GL")])["x"]
    assert just_outside["country"] is None            # 311 km


def test_a_record_left_out_by_hand_is_never_the_answer():
    # AQ-0012 is a record named "Navaid" 0.2 km from the South Pole skiway: not a runway of its own
    assert "AQ-0012" in build.SKIP_IDENTS
    rows = [field("AQ-0012", -89.998, 139.273, "small_airport", False, "AQ", "Navaid"),
            field("NZSP", -90.0, -1.0, "medium_airport", False, "AQ", "South Pole Station Airport")]
    record = build.build_cells([cell("x", -89.95, 139.0)], rows)["x"]
    assert record["nearest"]["ident"] == "NZSP"
    assert record["country"] == "AQ"
    assert build.left_out_by_hand(rows) == {"AQ-0012": build.SKIP_IDENTS["AQ-0012"]}
    assert build.left_out_by_hand(rows[1:]) == {}


def test_country_is_withheld_when_the_cells_own_region_says_otherwise():
    alert = [field("CYLT", 82.517263, -62.283037, "medium_airport", False, "CA", "Alert Airport")]
    north_greenland = dict(cell("82.0_-50.0", 82.05, -49.5), region="Greenland")       # about 190 km from Alert, across the strait
    ellesmere = dict(cell("82.0_-65.0", 82.05, -64.5), region="North-west Greenland or Ellesmere")
    plain = cell("82.0_-66.0", 82.05, -66.5)                                         # no region on the record
    tally = {}
    records = build.build_cells([north_greenland, ellesmere, plain], alert, tally=tally)
    assert records["82.0_-50.0"]["nearest"]["country"] == "CA"      # the airfield keeps its own country
    assert records["82.0_-50.0"]["country"] is None                 # the cell's is unknown, not Canada
    assert records["82.0_-65.0"]["country"] == "CA"                 # a box that covers both countries does not object
    assert records["82.0_-66.0"]["country"] == "CA"
    assert tally == {"country_withheld": 1}
    assert build.REGION_COUNTRIES["Greenland"] == ("GL",)
    assert build.REGION_COUNTRIES["Arctic Canada"] == ("CA",) and build.REGION_COUNTRIES["Alaska"] == ("US",)
    assert build.REGION_COUNTRIES["Victoria Land"] == ("AQ",)
    assert "North-west Greenland or Ellesmere" not in build.REGION_COUNTRIES


def test_limits_can_be_changed():
    rows = [field("A", 69.0, 0.0, "small_airport", True, "NO")]           # 111 km
    assert build.build_cells([cell("x", 70.0, 0.0)], rows, max_km=100.0, country_km=100.0)["x"] == \
        {"nearest": None, "nearest_scheduled": None, "country": None}


# ---------------------------------------------------------------- meta and the file

def test_meta_says_what_this_is_and_is_not(tmp_path):
    rows = [field("A", 69.0, 0.0, "small_airport", True, "NO"), field("B", 69.0, 1.0, "heliport", False, "NO")]
    records = build.build_cells([cell("x", 70.0, 0.0)], rows)
    note = {"url": build.SOURCE_URL, "fetched_utc": "2026-11-15T01:54:18Z", "last_modified": "Sat, 14 Nov 2026 02:54:01 GMT",
            "bytes": 123, "sha256": "ab"}
    meta = build.make_meta(rows, skipped=0, records=records, download=note, country_withheld=0)
    text = meta["what_this_is_not"].lower()
    for word in ("road", "port", "permit", "cost", "straight-line"):
        assert word in text
    assert meta["source"]["url"] == build.SOURCE_URL
    assert "public domain" in meta["source"]["licence_statement"].lower()
    assert meta["source"]["fetched_utc"] == "2026-11-15T01:54:18Z"
    assert meta["max_km"] == 1500.0 and meta["country_within_km"] == 300.0
    assert meta["types_kept"] == list(build.KEEP_TYPES) and meta["types_dropped"] == list(build.DROP_TYPES)
    assert meta["rows"] == {"in_table": 2, "without_a_usable_position": 0, "left_out_by_hand": {}, "fixed_wing": 1,
                            "fixed_wing_scheduled": 1, "by_type": build.type_counts(rows)}
    assert meta["counts"] == {"cells": 1, "nearest_null": 0, "nearest_scheduled_null": 0, "country_null": 0,
                              "country_null_because_the_region_disagrees": 0}
    assert meta["earth_radius_km"] == 6371.0


def test_written_file_is_whole_and_has_no_nan(tmp_path):
    out = tmp_path / "access_cells.json"
    build.write_json(out, {"meta": {}, "cells": {"x": {"nearest": None}}})
    assert json.loads(out.read_text()) == {"meta": {}, "cells": {"x": {"nearest": None}}}
    assert not (tmp_path / "access_cells.json.part").exists()
    with pytest.raises(ValueError):
        build.write_json(out, {"km": float("nan")})
    assert json.loads(out.read_text())["cells"]["x"] == {"nearest": None}   # the old file is still there, whole


def test_main_builds_the_file_without_the_network(tmp_path, capsys):
    cells = tmp_path / "grazing_cells.json"
    cells.write_text(json.dumps({"meta": {}, "cells": [cell("68.2_-96.3", 68.25, -96.15), cell("-77.6_161.4", -77.55, 161.5)]}))
    path = table(tmp_path,
                 line("CYHK", "small_airport", "Gjoa Haven Airport", 68.635597, -95.849701, "CA", "yes", "Gjoa Haven"),
                 line("NZFX", "small_airport", "Phoenix Airfield", -77.956389, 166.766667, "AQ", "no", "McMurdo Station"))
    out = tmp_path / "access_cells.json"
    assert build.main(["--cells", str(cells), "--table", str(path), "--out", str(out), "--offline"]) == 0
    result = json.loads(out.read_text())
    assert set(result) == {"meta", "cells"}
    assert set(result["cells"]) == {"68.2_-96.3", "-77.6_161.4"}
    assert result["cells"]["68.2_-96.3"]["nearest_scheduled"]["ident"] == "CYHK"
    assert result["cells"]["-77.6_161.4"]["nearest"]["ident"] == "NZFX"
    assert result["cells"]["-77.6_161.4"]["nearest_scheduled"] is None
    assert result["cells"]["-77.6_161.4"]["country"] == "AQ"
    assert result["meta"]["counts"]["cells"] == 2


def test_offline_run_without_the_table_stops_with_a_plain_message(tmp_path):
    with pytest.raises(FileNotFoundError, match="airports.csv"):
        build.ensure_table(tmp_path / "airports.csv", offline=True)


def test_download_sends_the_project_user_agent_and_nothing_personal(tmp_path, monkeypatch):
    seen = []

    class Answer:
        headers = {"Last-Modified": "Sat, 14 Nov 2026 02:54:01 GMT", "Content-Length": "5"}

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self, n=-1):
            data, self.data = getattr(self, "data", b"a,b\n1"), b""
            return data

    def fake_urlopen(request, timeout=None):
        seen.append(request)
        return Answer()

    monkeypatch.setattr(build.urllib.request, "urlopen", fake_urlopen)
    dest = tmp_path / "raw" / "airports.csv"
    note = build.download(build.SOURCE_URL, dest)
    assert dest.read_bytes() == b"a,b\n1"
    assert len(seen) == 1 and seen[0].full_url == build.SOURCE_URL
    assert dict(seen[0].header_items()) == {"User-agent": "twinfinder/0.1"}
    assert note["url"] == build.SOURCE_URL and note["bytes"] == 5
    assert note["last_modified"] == "Sat, 14 Nov 2026 02:54:01 GMT"
    assert json.loads((tmp_path / "raw" / "download.json").read_text()) == note


# ---------------------------------------------------------------- the report

def scored(cid, lat, lon, hemisphere="N", ranked=True, hours=150.0, lighting=0.8, shadows=0.4, region="Arctic Canada",
           top_bins=((19, 50.0), (18, 40.0))):
    north = hemisphere == "N"
    values = {"long_open_hours": hours if north else None, "long_snow_free_hours": hours if north else None,
              "long_summer_rock_open_hours": None if north else hours, "long_summer_rock_hours": None if north else hours,
              "top_bins": [list(b) for b in top_bins], "goals": {"lighting": lighting, "shadows": shadows},
              "long_open_hours_clear": None, "long_summer_rock_open_hours_clear": None}
    if not north:
        values["top_bins_summer_rock"] = [list(b) for b in top_bins]
    return {"id": cid, "lat": lat, "lon": lon, "hemisphere": hemisphere, "region": region, "bare": 0.9,
            "ranking": "north" if north else "south", "ranked": ranked, "targets": {"malapert": values}}


def access(km_scheduled, km_any=10.0, country="CA", name="Somewhere Airport"):
    def rec(km, sched):
        return None if km is None else {"name": name, "ident": "XXXX", "country": country, "type": "small_airport",
                                        "km": km, "municipality": None, "scheduled_service": sched, "lat": 0.0, "lon": 0.0}
    return {"nearest": rec(km_any, False), "nearest_scheduled": rec(km_scheduled, True), "country": country}


def test_bin_dates_match_the_results_file():
    assert build.bin_dates(19) == "10 Jul-19 Jul"
    assert build.bin_dates(0) == "1 Jan-10 Jan"
    assert build.bin_dates(35) == "17 Dec-31 Dec"


def test_qualifying_cells_are_ranked_and_reach_the_hours():
    cells = [scored("a", 70, 0), scored("b", 70, 5, hours=99.9), scored("c", 70, 10, ranked=False),
             scored("d", 70, 15, hours=100.0), scored("s", -70, 0, hemisphere="S")]
    assert [c["id"] for c in build.qualifying(cells, "malapert", "N")] == ["a", "d"]
    assert [c["id"] for c in build.qualifying(cells, "malapert", "S")] == ["s"]
    unknown = scored("u", 70, 20)
    unknown["targets"]["malapert"]["long_open_hours"] = None
    assert build.qualifying([unknown], "malapert", "N") == []      # unknown hours are not counted as enough


def test_counts_within_distances_use_the_scheduled_airfield_in_the_north():
    cells = [scored("a", 70, 0), scored("b", 70, 5), scored("c", 70, 10), scored("d", 70, 15), scored("e", 70, 20)]
    acc = {"a": access(49.9), "b": access(50.0), "c": access(100.1), "d": access(200.0), "e": access(None)}
    counts = build.within_counts(cells, acc, "nearest_scheduled")
    assert counts == {"cells": 5, "within_km": {"50": 2, "100": 2, "200": 4}, "no_airfield_within_reach": 1,
                      "not_in_access_file": 0}
    assert build.within_counts(cells, acc, "nearest")["within_km"] == {"50": 5, "100": 5, "200": 5}


def test_a_cell_missing_from_the_access_file_is_counted_as_unknown_not_as_far():
    counts = build.within_counts([scored("a", 70, 0), scored("zz", 70, 5)], {"a": access(10.0)}, "nearest_scheduled")
    assert counts["cells"] == 2 and counts["within_km"]["50"] == 1 and counts["not_in_access_file"] == 1


def test_best_sites_within_reach_keep_one_per_50_km_and_carry_the_airfield():
    cells = [scored("a", 70.0, 0.0, lighting=0.9), scored("b", 70.1, 0.0, lighting=0.95),      # 11 km apart: one site
             scored("c", 72.0, 0.0, lighting=0.5), scored("far", 74.0, 0.0, lighting=1.0),
             scored("tie", 76.0, 0.0, lighting=0.5, hours=180.0)]
    acc = {"a": access(40.0), "b": access(45.0, name="Gjoa Haven Airport"), "c": access(99.0), "far": access(120.0),
           "tie": access(60.0)}
    rows = build.best_within(cells, acc, "malapert", "N", goal="lighting", key="nearest_scheduled", within_km=100.0, top=5)
    assert [r["id"] for r in rows] == ["b", "tie", "c"]            # "far" is past 100 km; equal scores go by hours
    first = rows[0]
    assert first["airfield"] == "Gjoa Haven Airport" and first["airfield_km"] == 45.0
    assert first["score"] == 0.95 and first["hours"] == 150.0
    assert first["best_periods"] == "10 Jul-19 Jul (50 h), 30 Jun-9 Jul (40 h)"
    assert first["region"] == "Arctic Canada" and first["country"] == "CA"


def test_southern_sites_use_the_rock_season_hours_and_any_airfield():
    cells = [scored("s", -70.0, 10.0, hemisphere="S", hours=120.0, lighting=0.7, top_bins=((35, 30.0),))]
    acc = {"s": access(None, km_any=80.0, country="AQ", name="Troll Airfield")}
    rows = build.best_within(cells, acc, "malapert", "S", goal="lighting", key="nearest", within_km=100.0, top=5)
    assert rows[0]["hours"] == 120.0 and rows[0]["airfield"] == "Troll Airfield"
    assert rows[0]["best_periods"] == "17 Dec-31 Dec (30 h)"


def test_country_shares_of_the_top_cells():
    cells = [scored(str(i), 70.0, i, lighting=1.0 - i / 100) for i in range(6)] + [scored("low", 70, 50, lighting=0.01)]
    acc = {str(i): access(10.0, country="RU" if i < 3 else "CA") for i in range(5)}
    acc["5"] = access(10.0, country=None)
    acc["low"] = access(10.0, country="NO")
    cells[5]["region"] = "Novaya Zemlya"
    shares = build.country_shares(cells, acc, "malapert", "N", top=6)
    assert shares == {"top": 6, "cells": {"RU": 3, "CA": 2, "unknown": 1},
                      "share": {"RU": 0.5, "CA": 0.333, "unknown": 0.167},
                      "regions_of_the_unknown": {"Novaya Zemlya": 1}}


def test_report_only_reads_the_files_on_disk_and_takes_another_hours_floor(tmp_path, capsys):
    cells = [scored("a", 70.0, 0.0, hours=150.0, lighting=0.9), scored("b", 72.0, 0.0, hours=40.0, lighting=0.4),
             scored("s", -70.0, 10.0, hemisphere="S", hours=120.0, lighting=0.7)]
    scored_file = tmp_path / "cells_scored.json"
    scored_file.write_text(json.dumps({"meta": {"written": "now", "targets": [
        {"id": "malapert", "name": "Malapert Massif", "limit_deg": 5.55}]}, "cells": cells}))
    access_file = tmp_path / "access_cells.json"
    access_file.write_text(json.dumps({"meta": {"written": "then"}, "cells": {
        "a": access(45.0, name="Gjoa Haven Airport"), "b": access(150.0), "s": access(None, km_any=80.0, country="AQ")}}))
    before = access_file.read_bytes()
    saved = tmp_path / "report.json"
    args = ["--report-only", "--scored", str(scored_file), "--out", str(access_file), "--report-json", str(saved)]
    assert build.main(args) == 0
    assert access_file.read_bytes() == before                      # nothing was rebuilt
    text = capsys.readouterr().out
    assert "Malapert Massif" in text and "Gjoa Haven Airport" in text and "not a permit" in text
    rep = json.loads(saved.read_text())
    north = rep["targets"]["malapert"]["north"]
    assert rep["min_hours"] == 100.0
    assert north["counts_scheduled"] == {"cells": 1, "within_km": {"50": 1, "100": 1, "200": 1},
                                         "no_airfield_within_reach": 0, "not_in_access_file": 0}
    assert [r["id"] for r in north["best_lighting"]] == ["a"]
    assert [r["id"] for r in north["best_lighting_anywhere"]] == ["a", "b"]
    assert north["airfields"][0]["airfield"] == "Gjoa Haven Airport" and north["airfields"][0]["cells"] == 1
    assert rep["targets"]["malapert"]["south"]["counts_any_airfield"]["within_km"] == {"50": 0, "100": 1, "200": 1}
    assert build.main(args + ["--min-hours", "25"]) == 0
    rep = json.loads(saved.read_text())
    assert rep["min_hours"] == 25.0
    assert rep["targets"]["malapert"]["north"]["counts_scheduled"]["cells"] == 2
    assert rep["targets"]["malapert"]["north"]["counts_scheduled"]["within_km"] == {"50": 1, "100": 1, "200": 2}


# ---------------------------------------------------------------- the real file, when it is there

REAL = Path("data/derived/access_cells.json")
GRAZING = Path("data/derived/grazing_cells.json")


@pytest.mark.skipif(not (REAL.exists() and GRAZING.exists()), reason="access_cells.json not built here")
def test_real_file_covers_every_cell_and_knows_gjoa_haven():
    result = json.loads(REAL.read_text())
    cells = json.loads(GRAZING.read_text())["cells"]
    assert set(result["cells"]) == {c["id"] for c in cells}
    for record in result["cells"].values():
        assert set(record) == {"nearest", "nearest_scheduled", "country"}
        for key in ("nearest", "nearest_scheduled"):
            if record[key] is not None:
                assert 0.0 <= record[key]["km"] <= result["meta"]["max_km"]
                assert record[key]["type"] in build.KEEP_TYPES
        if record["nearest"] is not None and record["nearest_scheduled"] is not None:
            assert record["nearest"]["km"] <= record["nearest_scheduled"]["km"]
    # the cell that holds Gjoa Haven's runway (68.6356 N, 95.8497 W), or its nearest neighbour on the grid
    close = min(cells, key=lambda c: reference.haversine_km(c["lat"], c["lon"], 68.6356, -95.8497))
    record = result["cells"][close["id"]]["nearest_scheduled"]
    assert record["ident"] == "CYHK"
    assert record["km"] == pytest.approx(reference.haversine_km(close["lat"], close["lon"], 68.635597, -95.849701), abs=0.06)

# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Earthquakes, volcanoes and people near every place (scripts/build_hazards_people.py). No test touches the network."""
from __future__ import annotations

import datetime
import importlib
import io
import json
import math
import zipfile

import numpy as np
import pytest

build = importlib.import_module("scripts.build_hazards_people")

R = 6371.0   # the mean Earth radius the project uses (twinfinder/reference.py)


# ---------------------------------------------------------------- distance, three pairs checked by hand

def test_quarter_of_the_equator_is_a_quarter_of_the_circumference():
    # (0 N, 0 E) to (0 N, 90 E): a quarter of a great circle, 2 pi R / 4 = 10,007.5 km
    assert build.great_circle_km(0.0, 0.0, 0.0, 90.0) == pytest.approx(math.pi * R / 2, abs=1e-6)


def test_pole_to_pole_is_half_the_circumference():
    # North Pole to South Pole: pi R = 20,015.1 km, whatever the longitudes
    assert build.great_circle_km(90.0, 0.0, -90.0, 123.0) == pytest.approx(math.pi * R, abs=1e-6)


def test_one_degree_across_the_date_line():
    # (0, 179.5) to (0, -179.5) is one degree of the equator, 2 pi R / 360 = 111.19 km, not 359 degrees
    assert build.great_circle_km(0.0, 179.5, 0.0, -179.5) == pytest.approx(2 * math.pi * R / 360, abs=1e-6)


def test_distance_takes_arrays_and_same_point_is_zero():
    km = build.great_circle_km(np.array([10.0, 60.0]), np.array([20.0, 5.0]), np.array([10.0, 61.0]), np.array([20.0, 5.0]))
    assert km[0] == pytest.approx(0.0, abs=1e-9)
    assert km[1] == pytest.approx(2 * math.pi * R / 360, abs=1e-6)   # one degree along a meridian


# ---------------------------------------------------------------- the grid index

def brute_within(lat, lon, plat, plon, km):
    return sorted(np.flatnonzero(build.great_circle_km(lat, lon, plat, plon) <= km).tolist())


@pytest.fixture(scope="module")
def cloud():
    rng = np.random.default_rng(7)
    n = 4000
    # uniform on the sphere, plus points crowded at the poles and on the date line
    plat = np.degrees(np.arcsin(rng.uniform(-1, 1, n)))
    plon = rng.uniform(-180, 180, n)
    plat = np.concatenate([plat, rng.uniform(85, 90, 200), rng.uniform(-90, -85, 200), rng.uniform(-60, 60, 200)])
    plon = np.concatenate([plon, rng.uniform(-180, 180, 400), rng.choice([-180.0, 179.99, 180.0, -179.99], 200)])
    return plat, plon


QUERIES = [(0.0, 0.0), (89.9, 10.0), (-89.95, -170.0), (75.3, -90.0), (0.0, 180.0), (0.0, -179.9),
           (63.8, -22.6), (-77.5, 162.0), (45.0, 179.5), (-30.0, -179.8), (88.0, 0.0), (90.0, 0.0), (-90.0, 0.0)]


@pytest.mark.parametrize("km", [50.0, 300.0, 1500.0, 7000.0, 25000.0])
def test_grid_within_matches_brute_force(cloud, km):
    plat, plon = cloud
    index = build.GridIndex(plat, plon, cell_deg=2.0)
    for lat, lon in QUERIES:
        assert sorted(index.within(lat, lon, km).tolist()) == brute_within(lat, lon, plat, plon, km), (lat, lon, km)


def test_grid_nearest_matches_brute_force(cloud):
    plat, plon = cloud
    index = build.GridIndex(plat, plon, cell_deg=1.0)
    rng = np.random.default_rng(3)
    queries = QUERIES + list(zip(np.degrees(np.arcsin(rng.uniform(-1, 1, 200))), rng.uniform(-180, 180, 200)))
    for lat, lon in queries:
        i, km = index.nearest(lat, lon)
        d = build.great_circle_km(lat, lon, plat, plon)
        assert km == pytest.approx(d.min(), abs=1e-9)
        assert d[i] == pytest.approx(d.min(), abs=1e-9)


def test_grid_nearest_of_a_lone_far_point_and_of_nothing():
    index = build.GridIndex(np.array([-89.0]), np.array([0.0]))
    i, km = index.nearest(89.0, 180.0)            # the far side of the Earth: the search must widen to the whole globe
    assert i == 0 and km == pytest.approx(build.great_circle_km(89.0, 180.0, -89.0, 0.0))
    empty = build.GridIndex(np.array([]), np.array([]))
    assert empty.nearest(10.0, 10.0) == (-1, None)
    assert empty.within(10.0, 10.0, 1000.0).size == 0


def test_cap_extent_covers_the_pole_when_it_should():
    lo, hi, dlon = build.cap_extent(80.0, 1500.0)    # 13.5 degrees: reaches past the North Pole
    assert hi >= 90.0 and dlon is None
    lo, hi, dlon = build.cap_extent(0.0, R * math.radians(10.0))
    assert lo == pytest.approx(-10.0) and hi == pytest.approx(10.0) and dlon == pytest.approx(10.0)
    lo, hi, dlon = build.cap_extent(60.0, R * math.radians(1.0))   # at 60 deg one degree of arc spans about 2 degrees of longitude
    assert dlon == pytest.approx(math.degrees(math.asin(math.sin(math.radians(1.0)) / 0.5)))


# ---------------------------------------------------------------- the earthquake catalogue

def test_year_spans_cover_1990_to_2025_without_gaps_and_inside_the_service_limits():
    spans = build.year_spans(1990, 2025)
    assert len(spans) == 36
    assert spans[0][0] == "1990-01-01T00:00:00" and spans[-1][1] == "2025-12-31T23:59:59.999"
    for (start, end), (next_start, _) in zip(spans, spans[1:]):
        assert end[:10] == f"{int(start[:4])}-12-31" and next_start == f"{int(start[:4]) + 1}-01-01T00:00:00"
    for start, end in spans:
        days = (datetime.date.fromisoformat(end[:10]) - datetime.date.fromisoformat(start[:10])).days + 1
        assert days <= 731    # the whole-world span the documentation says may be enforced
    url = build.quake_url(*spans[0])
    assert url.startswith("https://earthquake.usgs.gov/fdsnws/event/1/query?")
    for part in ("format=csv", "minmagnitude=5", "starttime=1990-01-01T00:00:00", "endtime=1990-12-31T23:59:59.999"):
        assert part in url


QUAKE_HEADER = ("time,latitude,longitude,depth,mag,magType,nst,gap,dmin,rms,net,id,updated,place,type,horizontalError,"
                "depthError,magError,magNst,status,locationSource,magSource\n")


def quake_row(time, lat, lon, mag, ident, kind="earthquake", place="somewhere"):
    return f'{time},{lat},{lon},10.0,{mag},mw,,,,1.0,us,{ident},2025-01-01T00:00:00.000Z,"{place}",{kind},,,,,reviewed,us,us\n'


def test_read_quakes_keeps_earthquakes_drops_others_and_duplicates(tmp_path):
    a = tmp_path / "usgs_m5_2000.csv"
    a.write_text(QUAKE_HEADER + quake_row("2000-03-01T01:02:03.000Z", 64.0, -21.0, 5.5, "q1", place="Iceland, south")
                 + quake_row("2000-04-01T00:00:00.000Z", 41.0, 129.0, 5.1, "x1", kind="nuclear explosion")
                 + quake_row("2000-05-01T00:00:00.000Z", 10.0, 10.0, 4.9, "low"))
    b = tmp_path / "usgs_m5_2001.csv"
    b.write_text(QUAKE_HEADER + quake_row("2000-03-01T01:02:03.000Z", 64.0, -21.0, 5.5, "q1")
                 + quake_row("2001-06-01T00:00:00.000Z", -20.0, 170.0, 6.2, "q2"))
    events, tally = build.read_quakes([a, b])
    assert sorted(events["id"].tolist()) == ["q1", "q2"]
    assert tally["rows"] == 5 and tally["duplicates"] == 1 and tally["below_magnitude"] == 1
    assert tally["not_earthquake"] == {"nuclear explosion": 1}
    assert events["date"][events["id"].tolist().index("q1")] == "2000-03-01"


def test_read_quakes_refuses_a_file_that_hit_the_service_limit(tmp_path):
    f = tmp_path / "usgs_m5_2000.csv"
    f.write_text(QUAKE_HEADER + "".join(quake_row("2000-03-01T00:00:00.000Z", 0.0, 0.0, 5.0, f"q{i}") for i in range(30)))
    with pytest.raises(ValueError, match="limit"):
        build.read_quakes([f], limit=30)


def test_quake_summary_counts_within_200_km_and_names_the_largest_and_latest():
    events = {"id": np.array(["a", "b", "c", "d"]), "lat": np.array([64.0, 64.5, 66.5, 0.0]),
              "lon": np.array([-21.0, -21.0, -21.0, 0.0]), "mag": np.array([5.0, 6.3, 7.0, 8.0]),
              "date": np.array(["2008-05-29", "1990-01-02", "2020-01-01", "2010-01-01"]),
              "place": np.array(["p", "q", "r", "s"])}
    index = build.GridIndex(events["lat"], events["lon"])
    s = build.quake_summary(index, events, 64.0, -21.0, km=200.0)
    assert s["count"] == 2                      # c is 278 km north, d is far away
    assert s["largest_mag"] == 6.3 and s["largest_date"] == "1990-01-02"
    assert s["latest_date"] == "2008-05-29" and s["latest_mag"] == 5.0
    assert s["nearest_km"] == 0.0


def test_quake_summary_with_none_nearby_is_a_count_of_zero_and_nulls():
    events = {"id": np.array(["d"]), "lat": np.array([0.0]), "lon": np.array([0.0]), "mag": np.array([8.0]),
              "date": np.array(["2010-01-01"]), "place": np.array(["s"])}
    s = build.quake_summary(build.GridIndex(events["lat"], events["lon"]), events, 70.0, 50.0, km=200.0)
    assert s == {"count": 0, "largest_mag": None, "largest_date": None, "latest_date": None, "latest_mag": None,
                 "nearest_km": None}


# ---------------------------------------------------------------- the volcano list

def volcano_feature(number, name, lat, lon, last, evidence="Eruption Dated"):
    return {"type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": {"Volcano_Number": number, "Volcano_Name": name, "Country": "Iceland", "Latitude": lat,
                           "Longitude": lon, "Last_Eruption_Year": last, "Evidence_Category": evidence,
                           "Primary_Volcano_Type": "Stratovolcano", "Geologic_Epoch": "Holocene"}}


def test_read_volcanoes_keeps_an_unknown_last_eruption_as_null_and_bce_years_negative(tmp_path):
    f = tmp_path / "holocene_volcanoes.geojson"
    f.write_text(json.dumps({"type": "FeatureCollection", "numberMatched": 3, "features": [
        volcano_feature(1, "Hekla", 63.98, -19.7, 2000), volcano_feature(2, "Old field", 50.0, 7.0, -8300),
        volcano_feature(3, "Quiet one", 10.0, 10.0, None, evidence="Evidence Uncertain")]}))
    volcanoes = build.read_volcanoes(f)
    assert [v["last_eruption_year"] for v in volcanoes] == [2000, -8300, None]
    assert volcanoes[2]["evidence"] == "Evidence Uncertain"


def test_read_volcanoes_refuses_a_partial_answer(tmp_path):
    f = tmp_path / "holocene_volcanoes.geojson"
    f.write_text(json.dumps({"type": "FeatureCollection", "numberMatched": 5,
                             "features": [volcano_feature(1, "Hekla", 63.98, -19.7, 2000)]}))
    with pytest.raises(ValueError, match="numberMatched"):
        build.read_volcanoes(f)


def test_volcano_summary_names_the_nearest():
    volcanoes = [{"number": 1, "name": "Hekla", "country": "Iceland", "lat": 63.98, "lon": -19.7,
                  "last_eruption_year": 2000, "evidence": "Eruption Observed", "type": "Stratovolcano"},
                 {"number": 2, "name": "Far", "country": "X", "lat": 0.0, "lon": 0.0, "last_eruption_year": None,
                  "evidence": "Evidence Uncertain", "type": "Shield"}]
    index = build.GridIndex(np.array([v["lat"] for v in volcanoes]), np.array([v["lon"] for v in volcanoes]))
    s = build.volcano_summary(index, volcanoes, 63.8, -22.6)
    assert s["name"] == "Hekla" and s["last_eruption_year"] == 2000
    assert s["km"] == pytest.approx(round(build.great_circle_km(63.8, -22.6, 63.98, -19.7), 1))
    s = build.volcano_summary(index, volcanoes, 1.0, 1.0)
    assert s["name"] == "Far" and s["last_eruption_year"] is None


# ---------------------------------------------------------------- the settlements

def geonames_line(gid, name, lat, lon, code, country, pop):
    cols = [str(gid), name, name, "", str(lat), str(lon), "P", code, country, "", "01", "", "", "", str(pop), "", "10",
            "Europe/X", "2024-01-01"]
    return "\t".join(cols) + "\n"


def make_zip(tmp_path, lines):
    path = tmp_path / "cities1000.zip"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("cities1000.txt", "".join(lines))
    return path


def test_read_settlements_leaves_out_city_sections_and_gone_places_and_keeps_unknown_population_null(tmp_path):
    path = make_zip(tmp_path, [
        geonames_line(1, "Town", 64.0, -22.0, "PPL", "IS", 5000),
        geonames_line(2, "Part of town", 64.0, -22.01, "PPLX", "IS", 3000),
        geonames_line(3, "Abandoned", 64.1, -22.0, "PPLQ", "IS", 2000),
        geonames_line(4, "Seat", 64.2, -22.0, "PPLA3", "IS", 0),
        geonames_line(5, "Historic", 64.3, -22.0, "PPLH", "IS", 9000)])
    places, tally = build.read_settlements(path)
    assert [p["name"] for p in places] == ["Town", "Seat"]
    assert places[1]["population"] is None
    assert tally["rows"] == 5 and tally["left_out"] == {"PPLH": 1, "PPLQ": 1, "PPLX": 1}


def test_people_summary_nearest_town_nearest_city_and_sum_within_100_km():
    places = [{"name": "Village", "country": "IS", "lat": 64.0, "lon": -22.0, "population": 1500, "code": "PPL"},
              {"name": "Seat", "country": "IS", "lat": 64.3, "lon": -22.0, "population": None, "code": "PPLA3"},
              {"name": "City", "country": "IS", "lat": 64.5, "lon": -22.0, "population": 120000, "code": "PPLC"},
              {"name": "Far city", "country": "IS", "lat": 66.0, "lon": -22.0, "population": 60000, "code": "PPL"}]
    s = build.people_summary(build.settlement_indexes(places), places, 64.0, -22.0, km=100.0, city_pop=50000)
    assert s["nearest"]["name"] == "Village" and s["nearest"]["km"] == 0.0
    assert s["nearest_city_50k"]["name"] == "City"
    assert s["nearest_city_50k"]["km"] == pytest.approx(round(2 * math.pi * R / 360 * 0.5, 1))
    assert s["population_within_100km"] == 121500        # Far city is 222 km away; the seat's unknown is not a 0
    assert s["settlements_within_100km"] == 3 and s["settlements_without_population_within_100km"] == 1


def test_people_summary_with_nobody_near_is_zero_people_and_still_names_the_nearest():
    places = [{"name": "Far city", "country": "NZ", "lat": -43.5, "lon": 172.6, "population": 380000, "code": "PPLA"}]
    s = build.people_summary(build.settlement_indexes(places), places, -77.5, 162.0, km=100.0, city_pop=50000)
    assert s["population_within_100km"] == 0 and s["settlements_within_100km"] == 0
    assert s["nearest"]["name"] == "Far city" and s["nearest"]["km"] > 3000
    assert s["nearest_city_50k"]["name"] == "Far city"


# ---------------------------------------------------------------- records and the file

def test_build_records_gives_every_place_all_three_parts():
    places = [{"id": "64.0_-22.0", "lat": 64.0, "lon": -22.0}, {"id": "m_0.25_0.25", "lat": 0.25, "lon": 0.25}]
    events = {"id": np.array(["a"]), "lat": np.array([64.0]), "lon": np.array([-21.0]), "mag": np.array([5.5]),
              "date": np.array(["2000-01-01"]), "place": np.array(["p"])}
    volcanoes = [{"number": 1, "name": "Hekla", "country": "Iceland", "lat": 63.98, "lon": -19.7,
                  "last_eruption_year": 2000, "evidence": "Eruption Observed", "type": "Stratovolcano"}]
    settlements = [{"name": "Town", "country": "IS", "lat": 64.1, "lon": -22.0, "population": 2000, "code": "PPL"}]
    records = build.build_records(places, events, volcanoes, settlements)
    assert set(records) == {"64.0_-22.0", "m_0.25_0.25"}
    r = records["64.0_-22.0"]
    assert r["quakes_m5_200km"]["count"] == 1 and r["volcano"]["name"] == "Hekla"
    assert r["people"]["nearest"]["name"] == "Town" and r["people"]["nearest_city_50k"] is None
    far = records["m_0.25_0.25"]
    assert far["quakes_m5_200km"]["count"] == 0 and far["people"]["population_within_100km"] == 0


def test_write_json_is_atomic_and_refuses_nan(tmp_path):
    out = tmp_path / "x.json"
    build.write_json(out, {"a": 1})
    assert json.loads(out.read_text()) == {"a": 1}
    with pytest.raises(ValueError):
        build.write_json(out, {"a": float("nan")})
    assert json.loads(out.read_text()) == {"a": 1}
    assert not list(tmp_path.glob("*.part"))

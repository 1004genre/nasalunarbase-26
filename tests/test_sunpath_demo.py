# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Tests of scripts/build_sunpath_demo.py: the Sun's path at a lunar site beside its path at a place on Earth.

No test asks a server for anything: the JPL Horizons answers are short texts written here, and
the ground is made up.
"""
import importlib
import json
import math
import xml.etree.ElementTree as ET

import numpy as np
import pytest

from twinfinder import earth, sun

build = importlib.import_module("scripts.build_sunpath_demo")

HORIZONS_ANSWER = """API VERSION: 1.2
API SOURCE: NASA/JPL Horizons API

Target body name: Sun (10)                        {source: DE441}
Center body name: Moon (301)                      {source: DE441}
Center geodetic : 359.7642162, -85.9947847, 0.0   {E-lon(deg),Lat(deg),Alt(km)}
Center pole/equ : MEAN_ME (high precision)        {East-longitude positive}
Atmos refraction: NO (AIRLESS)
*******************************************************************************
 Date__(UT)__HR:MN, Date_________JDUT, , ,Azi_(a-app), Elev_(a-app),
********************************************************************
$$SOE
 2025-Dec-31 23:00, 2461041.458333333,*,i,  33.376728,     4.693710,
 2026-Jan-01 00:00, 2461041.500000000,*,i,  32.870171,     4.712322,
 2026-Jan-01 01:00, 2461041.541666667, ,i,  32.363598,    -0.730671,
 2026-Jan-01 02:00, 2461041.583333333,*, ,  31.857009,     4.748755,
$$EOE
*******************************************************************************
Column meaning:
"""


def lunar_series(days: float = 80.0, trip_days: float = 29.5, start_az: float = 100.0, clockwise: bool = False,
                 colatitude: float = 4.0, season_peak_day: float = 40.0):
    """Hourly made-up Sun path at a lunar polar site: the Sun circles once in trip_days and is highest in the north."""
    hours = np.arange(0.0, days * 24.0 + 1.0)
    jd = 2461041.5 + hours / 24.0
    turn = (1.0 if clockwise else -1.0) * 360.0 * hours / (trip_days * 24.0)
    az = (start_az + turn) % 360.0
    season = 1.5 * np.cos(2.0 * np.pi * (hours / 24.0 - season_peak_day) / 346.6)
    el = season + colatitude * np.cos(np.radians(az))
    labels = [f"2026-day-{h / 24.0:07.3f}" for h in hours]
    return {"jd": jd, "azimuth_deg": az, "elevation_deg": el, "utc": labels}


# ---------------------------------------------------------------- JPL Horizons

def test_the_request_asks_for_the_sun_seen_from_a_point_on_the_moon_with_no_air():
    params = build.horizons_params(359.7642162301234, -85.99478468356075, 0.0, "2025-12-01 00:00", "2027-02-01 00:00")
    assert params["COMMAND"] == "'10'"                    # the Sun
    assert params["CENTER"] == "'coord@301'"              # a point given by coordinates on the Moon
    assert params["COORD_TYPE"] == "'GEODETIC'"
    assert params["SITE_COORD"] == "'359.764216,-85.994785,0.000'"   # east longitude, latitude, height in km
    assert params["APPARENT"] == "'AIRLESS'"              # no refraction
    assert params["QUANTITIES"] == "'4'"                  # azimuth and elevation
    assert params["STEP_SIZE"] == "'1 h'"
    assert params["START_TIME"] == "'2025-12-01 00:00'" and params["STOP_TIME"] == "'2027-02-01 00:00'"
    assert params["format"] == "text"
    assert not any("mail" in key.lower() for key in params)   # nothing personal goes out


def test_the_request_url_goes_to_the_public_horizons_api_and_is_encoded():
    url = build.horizons_url(build.horizons_params(222.5, -89.46, 0.0, "2026-01-01 00:00", "2026-01-02 00:00"))
    assert url.startswith("https://ssd.jpl.nasa.gov/api/horizons.api?")
    assert " " not in url and "'" not in url
    assert "CENTER=%27coord%40301%27" in url


def test_a_horizons_answer_is_read_into_times_directions_and_heights():
    series = build.parse_horizons(HORIZONS_ANSWER)
    assert series["utc"] == ["2025-Dec-31 23:00", "2026-Jan-01 00:00", "2026-Jan-01 01:00", "2026-Jan-01 02:00"]
    assert series["jd"].tolist() == [2461041.458333333, 2461041.5, 2461041.541666667, 2461041.583333333]
    assert series["azimuth_deg"].tolist() == [33.376728, 32.870171, 32.363598, 31.857009]
    assert series["elevation_deg"].tolist() == [4.69371, 4.712322, -0.730671, 4.748755]
    assert series["header"]["frame"].startswith("MEAN_ME")
    assert series["header"]["refraction"] == "NO (AIRLESS)"
    assert series["header"]["site"].startswith("359.7642162, -85.9947847, 0.0")


def test_a_refracted_table_for_a_point_on_earth_is_read_the_same_way():
    refracted = HORIZONS_ANSWER.replace("Azi_(a-app), Elev_(a-app)", "Azi_(r-app), Elev_(r-app)")
    series = build.parse_horizons(refracted)
    assert series["azimuth_deg"].tolist() == [33.376728, 32.870171, 32.363598, 31.857009]
    assert series["elevation_deg"][2] == -0.730671


def test_an_answer_without_a_table_is_an_error_not_an_empty_path():
    with pytest.raises(ValueError, match="no table"):
        build.parse_horizons("API VERSION: 1.2\nNo ephemeris for target \"Sun\" after A.D. 9999\n")


class FakeAnswer:
    def __init__(self, body: bytes):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self) -> bytes:
        return self.body


def test_the_raw_answer_is_kept_whole_and_not_asked_for_twice(tmp_path):
    asked = []

    def fake_urlopen(request, timeout=None):
        asked.append(request)
        return FakeAnswer(HORIZONS_ANSWER.encode())

    raw = tmp_path / "horizons_sunpath"
    first = build.fetch_horizons("malapert", 359.7642162301234, -85.99478468356075, raw, urlopen=fake_urlopen)
    again = build.fetch_horizons("malapert", 359.7642162301234, -85.99478468356075, raw, urlopen=fake_urlopen)
    assert first == again and first.read_text() == HORIZONS_ANSWER
    assert len(asked) == 1                                          # the second call read the file
    assert asked[0].get_header("User-agent") == "twinfinder/0.1"
    assert asked[0].full_url.startswith("https://ssd.jpl.nasa.gov/api/horizons.api?")
    assert sorted(path.name for path in raw.iterdir()) == [first.name, first.name + ".request.json"]
    note = json.loads((raw / (first.name + ".request.json")).read_text())
    assert note["params"]["SITE_COORD"] == "'359.764216,-85.994785,0.000'" and note["user_agent"] == "twinfinder/0.1"
    build.fetch_horizons("malapert", 359.7642162301234, -85.99478468356075, raw, refetch=True, urlopen=fake_urlopen)
    assert len(asked) == 2


def test_an_answer_without_a_table_is_set_aside_and_never_becomes_the_raw_file(tmp_path):
    def refusing(request, timeout=None):
        return FakeAnswer(b"API VERSION: 1.2\nCannot interpret date. Type \"?!\" or try YYYY-MMM-DD\n")

    with pytest.raises(ValueError, match="no table"):
        build.fetch_horizons("malapert", 359.76, -85.99, tmp_path, urlopen=refusing)
    assert [path.name for path in tmp_path.iterdir() if path.suffix == ".txt"] == []
    assert any(path.name.endswith(".rejected") for path in tmp_path.iterdir())


def test_rows_of_one_year_are_picked_by_their_date():
    series = build.parse_horizons(HORIZONS_ANSWER)
    assert build.in_year(series["utc"], 2026).tolist() == [False, True, True, True]


# ---------------------------------------------------------------- trips round the horizon

@pytest.mark.parametrize("clockwise", [False, True])
def test_the_mean_trip_is_the_time_the_sun_takes_to_go_once_round_the_compass(clockwise):
    series = lunar_series(trip_days=29.5, clockwise=clockwise)
    assert build.mean_trip_days(series["jd"], series["azimuth_deg"]) == pytest.approx(29.5, abs=1e-6)


def test_the_trip_through_the_highest_sun_runs_from_due_south_to_due_south():
    series = lunar_series(days=80.0, trip_days=29.5, start_az=100.0, season_peak_day=40.0)
    peak = int(np.argmax(series["elevation_deg"]))
    trip = build.trip_through(series["jd"], series["azimuth_deg"], peak)
    assert trip["complete"] is True
    assert trip["days"] == pytest.approx(29.5, abs=1e-6)
    first, last = trip["first"], trip["last"]
    assert first <= peak <= last
    az = series["azimuth_deg"][first:last + 1]
    assert 179.0 < az[0] <= 180.0 and 180.0 <= az[-1] < 181.0     # anticlockwise: it sets out from south towards east
    assert len(az) in (708, 709)                                   # one sample an hour for 29.5 days
    assert trip["hours_since_start"][0] == pytest.approx((180.0 - az[0]) / 360.0 * 29.5 * 24.0, abs=1e-6)
    assert trip["hours_since_start"][-1] <= 29.5 * 24.0
    # the highest Sun of the trip is in the north, half-way through
    middle = first + int(np.argmax(series["elevation_deg"][first:last + 1]))
    assert abs((series["azimuth_deg"][middle] + 180.0) % 360.0 - 180.0) < 1.0


def test_a_trip_cut_off_by_the_end_of_the_data_gives_way_to_the_nearest_whole_trip():
    series = lunar_series(days=80.0, start_az=100.0)
    trip = build.trip_through(series["jd"], series["azimuth_deg"], len(series["jd"]) - 3)
    assert trip["complete"] is False                # the trip that holds this hour is not whole ...
    assert trip["days"] == pytest.approx(29.5, abs=1e-6)   # ... so the last whole one is given
    assert trip["last"] < len(series["jd"]) - 3


def test_every_whole_trip_in_the_rows_is_measured():
    # from azimuth 100 the Sun first stands due south after 280 degrees, 22.9 days; trips then end on days 52.4 and 81.9
    series = lunar_series(days=90.0, trip_days=29.5, start_az=100.0)
    assert build.whole_trip_days(series["jd"], series["azimuth_deg"]) == pytest.approx([29.5, 29.5], abs=1e-6)
    shorter = lunar_series(days=80.0, trip_days=29.5, start_az=100.0)
    assert build.whole_trip_days(shorter["jd"], shorter["azimuth_deg"]) == pytest.approx([29.5], abs=1e-6)


def test_a_lunar_record_gives_the_years_highest_sun_against_the_ceiling():
    series = lunar_series(days=80.0, colatitude=4.0, season_peak_day=40.0)
    target = {"id": "malapert", "name": "Malapert Massif", "centre_lat": -86.0, "centre_lon": 359.76,
              "sun_max_elev_deg": 5.545215316439248}
    record = build.lunar_record(target, series, year=2026)
    assert record["ceiling_deg"] == 5.55
    assert record["year_max_elevation_deg"] == pytest.approx(float(series["elevation_deg"].max()), abs=1e-3)
    assert record["year_max_minus_ceiling_deg"] == pytest.approx(record["year_max_elevation_deg"] - 5.55, abs=1e-3)
    assert record["mean_trip_days"] == pytest.approx(29.5, abs=0.01)
    assert record["shortest_trip_days"] == record["longest_trip_days"] == 29.5
    path = record["path"]
    assert len(path["hours_since_start"]) == len(path["azimuth_deg"]) == len(path["elevation_deg"])
    assert path["hours_since_start"][0] >= 0.0 and path["hours_since_start"][-1] <= 29.5 * 24.0
    assert max(path["elevation_deg"]) == pytest.approx(record["year_max_elevation_deg"], abs=1e-3)
    assert record["path_days_above_level_horizon"] == pytest.approx(
        sum(1 for e in path["elevation_deg"] if e > 0.0) / 24.0, abs=0.05)
    assert record["direction"] == "anticlockwise (east to north to west)"


# ---------------------------------------------------------------- choosing the Earth places

RANKING = """Earth Twin Finder ranking, written 2026-11-14T14:39:06.

NORTH: measured cells with a horizon

Low Sun on bare ground | Connecting Ridge (Sun at or below 2.08 deg) | all sites
  score  lat     lon      region                             bare  hours
  0.49   68.25   -96.15  Arctic Canada                      0.96     50

Low Sun on bare ground | Malapert Massif (Sun at or below 5.55 deg) | all sites
  score  lat     lon      region                             bare  hours
  1.00   68.95    54.45  Kola and north-west Russia         1.00    243
  0.99   80.15    18.30  Svalbard                           0.99    203

Driving in long shadows | Malapert Massif (Sun at or below 5.55 deg) | all sites
  score  lat     lon      region                             bare  hours
  0.61   70.15  -116.85  Arctic Canada                      0.98    184

Low Sun on bare ground | Malapert Massif (Sun at or below 5.55 deg) | little-known sites only
  score  lat     lon      region                             bare  hours
  0.95   70.15  -116.85  Arctic Canada                      0.98    184
"""


def test_the_head_of_the_malapert_lighting_list_is_read_from_the_ranking():
    assert build.ranking_top_cell(RANKING, "Malapert Massif") == (68.95, 54.45)
    assert build.ranking_top_cell(RANKING, "Connecting Ridge") == (68.25, -96.15)


def test_a_ranking_without_the_list_is_an_error():
    with pytest.raises(ValueError, match="Nobile Rim 2"):
        build.ranking_top_cell(RANKING, "Nobile Rim 2")


def test_a_cell_is_found_by_the_coordinates_the_ranking_prints():
    cells = [{"id": "68.9_54.3", "lat": 68.95, "lon": 54.45}, {"id": "68.9_54.6", "lat": 68.95, "lon": 54.75}]
    assert build.find_cell(cells, 68.95, 54.45)["id"] == "68.9_54.3"
    with pytest.raises(ValueError, match="no cell"):
        build.find_cell(cells, 10.0, 10.0)


def test_the_cell_that_holds_a_place_is_found_by_the_grid():
    cells = [{"id": "75.3_-90.0", "lat": 75.35, "lon": -89.75}, {"id": "75.3_-89.5", "lat": 75.35, "lon": -89.25}]
    assert build.cell_holding(cells, 75.38, -89.67)["id"] == "75.3_-90.0"


def test_the_middle_day_of_a_ten_day_period_lies_in_that_period():
    assert build.middle_day(21) == 215     # 30 July to 8 August
    assert build.middle_day(0) == 5
    assert build.middle_day(35) == 358     # the last period runs to the end of the year
    assert all(sun.bin_index(build.middle_day(b)) == b for b in range(sun.N_BINS))


# ---------------------------------------------------------------- the Sun on Earth

def test_the_earth_path_is_24_hours_of_apparent_sun_at_five_minute_steps():
    path = build.earth_path(75.35, 215)
    hours = path["solar_time_h"]
    assert len(hours) == 289 and hours[0] == 0.0 and hours[-1] == 24.0
    assert hours[1] - hours[0] == pytest.approx(5.0 / 60.0, abs=1e-3)
    true, az = sun.elevation_azimuth(75.35, 215, np.array([0.0, 6.0, 12.0]))
    assert path["elevation_deg"][0] == pytest.approx(float(sun.apparent_elevation_deg(true[0])), abs=1e-3)
    assert path["elevation_deg"][144] == pytest.approx(float(sun.apparent_elevation_deg(true[2])), abs=1e-3)
    assert path["azimuth_deg"][72] == pytest.approx(float(az[1]), abs=1e-2)
    assert path["elevation_deg"][0] > path["true_elevation_deg"][0]       # the air lifts a low Sun
    assert min(path["elevation_deg"]) > 0.0                               # the midnight Sun of early August
    assert path["azimuth_deg"][0] in (0.0, 360.0) and path["azimuth_deg"][144] == pytest.approx(180.0, abs=1e-6)


def test_band_minutes_count_the_day_and_the_spell_runs_through_midnight():
    stats = build.band_stats(75.35, 215, 5.55)
    hours = (np.arange(1440) + 0.5) / 60.0
    apparent = sun.apparent_elevation_deg(sun.elevation_azimuth(75.35, 215, hours)[0])
    assert stats["minutes_in_band"] == int(((apparent > 0.0) & (apparent <= 5.55)).sum())
    # the low Sun sits around midnight, so the day holds two pieces of two different spells
    assert stats["longest_spell_minutes"] > stats["minutes_in_band"] / 2.0
    project = sun.longest_stretch_hours_by_day(75.35, [5.55], True, 1)[215 - 1, 0]
    assert stats["longest_spell_minutes"] == pytest.approx(60.0 * project, abs=1e-6)
    assert stats["minutes_above_terrain"] is None and stats["longest_spell_minutes_above_terrain"] is None


def test_a_sun_that_never_leaves_the_band_gives_the_whole_day():
    stats = build.band_stats(89.0, 100, 12.0)      # the pole in spring: the Sun circles at about 8 degrees
    assert stats["minutes_in_band"] == 1440 and stats["longest_spell_minutes"] == 1440


def test_ground_higher_than_the_sun_takes_minutes_out_of_the_band():
    flat = build.band_stats(75.35, 215, 5.55, horizon_by_sector=[-0.5] * 36)
    assert flat["minutes_above_terrain"] == flat["minutes_in_band"]       # ground under a level horizon hides nothing
    assert flat["longest_spell_minutes_above_terrain"] == flat["longest_spell_minutes"]
    wall = [-0.5] * 36
    wall[0] = wall[35] = 10.0                                             # a wall from 350 through north to 10 degrees
    hidden = build.band_stats(75.35, 215, 5.55, horizon_by_sector=wall)
    assert 0 < hidden["minutes_above_terrain"] < flat["minutes_in_band"]
    assert hidden["longest_spell_minutes_above_terrain"] < flat["longest_spell_minutes"]
    assert build.band_stats(75.35, 215, 5.55, horizon_by_sector=[10.0] * 36)["minutes_above_terrain"] == 0


# ---------------------------------------------------------------- the ground on Earth

def made_up_ground(lat, lon, half_km=5.0, pixel_m=90.0, mask_water=True, sea_as_zero=False):
    """A plain at 100 m with a 600 m wall 12 km south of the middle, and a lake in the north-east corner."""
    n = int(round(2 * half_km * 1000.0 / pixel_m))
    z = np.full((n, n), 100.0, dtype="float32")
    row_of_wall = n // 2 + int(round(12000.0 / pixel_m))
    z[row_of_wall:row_of_wall + 5, :] = 700.0
    if mask_water:
        z[:n // 2 - 150, n // 2 + 150:] = np.nan      # 9 km and more from the middle: outside the 10 km cell
    return z


def test_the_terrain_horizon_is_given_by_sector_for_the_centre_and_for_the_cell(monkeypatch):
    monkeypatch.setattr(earth, "elevation_window", made_up_ground)
    ground = build.terrain_horizon(70.0, 20.0)
    assert ground["sector_centres_deg"] == [10.0 * k + 5.0 for k in range(36)]
    assert len(ground["centre_deg"]) == len(ground["cell_median_deg"]) == 36
    assert ground["pixel_m"] == 60.0 and ground["reach_km"] == 25.0 and ground["half_km"] == 5.0
    south = ground["sector_centres_deg"].index(175.0)
    wall = math.degrees(math.atan(598.0 / 12000.0 - 12000.0 / (2 * 6371000.0 * 7.0 / 6.0)))   # 2.8 degrees
    assert ground["centre_deg"][south] == pytest.approx(wall, abs=0.1)
    assert ground["cell_median_deg"][south] == pytest.approx(wall, abs=0.3)
    assert -0.2 < ground["centre_deg"][0] < 0.0          # the far edge of the plain, a little under level
    assert ground["south_deg"] == pytest.approx(wall, abs=0.3) and -0.2 < ground["north_deg"] < 0.0
    assert ground["centre_is_land"] is True
    assert ground["land_share"] == 1.0                   # the lake lies outside the 10 km cell


def test_a_cell_whose_tiles_are_not_on_disk_has_no_horizon_and_says_why(monkeypatch, tmp_path):
    monkeypatch.setattr(earth, "GLO90_DIR", tmp_path)
    monkeypatch.setattr(earth, "fetch_optional", build.cached_or_ocean)
    assert build.horizon_or_reason(70.0, 20.0) == (None, build.horizon_or_reason(70.0, 20.0)[1])
    assert "not on disk" in build.horizon_or_reason(70.0, 20.0)[1]
    assert list(tmp_path.iterdir()) == []                # nothing was fetched and nothing was written


def test_the_stand_in_for_downloads_reads_the_cache_and_never_asks_a_server(tmp_path):
    (tmp_path / "a_DEM.tif").write_bytes(b"x")
    (tmp_path / "b_DEM.tif.missing").touch()
    assert build.cached_or_ocean("https://host/x/a_DEM.tif", tmp_path) == tmp_path / "a_DEM.tif"
    assert build.cached_or_ocean("https://host/x/b_DEM.tif", tmp_path) is None      # known ocean
    with pytest.raises(RuntimeError, match="not on disk"):
        build.cached_or_ocean("https://host/x/c_DEM.tif", tmp_path)


# ---------------------------------------------------------------- one Earth place, and the drawing

CELL = {"id": "75.3_-90.0", "lat": 75.35, "lon": -89.75, "region": "Arctic Canada",
        "targets": {"malapert": {"top_bins": [[21, 39.3], [22, 36.6], [23, 14.3]]}}}
PLACE = {"id": "haughton", "name": "Haughton crater, Devon Island", "why": "NASA-funded rover tests used it",
         "place_lat": 75.38, "place_lon": -89.67}
TARGET = {"id": "malapert", "name": "Malapert Massif", "centre_lat": -86.0, "centre_lon": 359.76,
          "sun_max_elev_deg": 5.545215316439248}
GROUND = {"sector_centres_deg": [10.0 * k + 5.0 for k in range(36)], "centre_deg": [3.5] * 36,   # hides the lowest Sun
          "cell_median_deg": [0.6] * 36, "pixel_m": 60.0, "reach_km": 25.0, "half_km": 5.0}


def test_an_earth_record_takes_the_middle_day_of_the_best_ten_day_period():
    record = build.earth_record(PLACE, CELL, TARGET, lambda lat, lon: (GROUND, None))
    assert record["cell_id"] == "75.3_-90.0" and record["target"] == "malapert"
    assert record["best_bin"] == 21 and record["best_bin_hours"] == 39.3
    assert record["day_of_year"] == 215 and record["date"] == "3 Aug"
    assert record["band_deg"] == [0.0, 5.55]
    assert len(record["path"]["solar_time_h"]) == 289
    assert record["terrain_horizon"] == GROUND and record["terrain_horizon_missing_because"] is None
    assert record["minutes_in_band"] > record["minutes_above_terrain"] > 0
    assert record["day_max_elevation_deg"] == pytest.approx(max(record["path"]["elevation_deg"]), abs=1e-3)


def test_unknown_stays_null_never_zero():
    no_ground = build.earth_record(PLACE, CELL, TARGET, lambda lat, lon: (None, "tile not on disk: x"))
    assert no_ground["terrain_horizon"] is None and no_ground["terrain_horizon_missing_because"] == "tile not on disk: x"
    assert no_ground["minutes_above_terrain"] is None and no_ground["minutes_in_band"] > 0
    no_period = {**CELL, "targets": {"malapert": {"top_bins": []}}}
    record = build.earth_record(PLACE, no_period, TARGET, lambda lat, lon: (GROUND, None))
    assert record["day_of_year"] is None and record["date"] is None and record["path"] is None
    assert record["minutes_in_band"] is None and record["longest_spell_minutes"] is None
    assert "no ten-day period" in record["path_missing_because"]
    json.dumps(record, allow_nan=False)                  # and no NaN can reach the file


def demo():
    lunar = build.lunar_record(TARGET, lunar_series(days=80.0), year=2026)
    place = build.earth_record(PLACE, CELL, TARGET, lambda lat, lon: (GROUND, None))
    return lunar, place


def test_the_drawing_is_one_svg_with_the_plain_labels_and_the_caption():
    lunar, place = demo()
    svg = build.svg(lunar, place)
    root = ET.fromstring(svg)                            # well-formed
    assert root.tag.endswith("svg") and root.attrib["viewBox"] == "0 0 1200 700"
    text = " ".join("".join(node.itertext()) for node in root.iter() if node.tag.endswith("text"))
    assert "one trip takes 29.5 days" in text
    assert "one trip takes 24 hours" in text
    assert "Malapert Massif" in text and "Haughton crater" in text and "3 Aug" in text
    assert "75.35° N, 89.75° W" in text                  # the cell centre the path was worked out for
    assert "5.55" in text
    assert build.CAPTION in text
    assert build.CAPTION == ("Drawn by code from JPL Horizons and Copernicus elevation data; "
                             "code written with AI assistance.")
    assert "nan" not in svg.lower() and "None" not in svg


def test_the_trip_label_follows_the_data():
    lunar = build.lunar_record(TARGET, lunar_series(days=80.0, trip_days=27.0), year=2026)
    place = build.earth_record(PLACE, CELL, TARGET, lambda lat, lon: (GROUND, None))
    assert "one trip takes 27.0 days" in build.svg(lunar, place)


def test_the_drawing_leaves_out_ground_it_does_not_know():
    lunar, _ = demo()
    place = build.earth_record(PLACE, CELL, TARGET, lambda lat, lon: (None, "tile not on disk: x"))
    svg = build.svg(lunar, place)
    ET.fromstring(svg)
    assert 'id="terrain"' not in svg and "ground horizon not known" in svg
    assert 'id="terrain"' in build.svg(*demo())


def test_drawn_against_another_lunar_site_the_minutes_are_counted_for_that_sites_band():
    ridge = {"id": "connecting-ridge", "name": "Connecting Ridge", "centre_lat": -89.46,
             "centre_lon": 222.51, "sun_max_elev_deg": 2.076837165962993}
    lunar = build.lunar_record(ridge, lunar_series(days=80.0, colatitude=0.54), year=2026)
    place = build.earth_record(PLACE, CELL, TARGET, lambda lat, lon: (None, "tile not on disk: x"))
    svg = build.svg(lunar, place)
    assert "2.08" in svg
    assert place["minutes_in_band"] > 0                       # counted for Malapert's 5.55 degrees
    assert "inside the band for 0 h 00 min" in svg            # on 3 August the Sun at Haughton never drops to 2.08


def test_a_horizons_date_is_written_in_plain_form():
    assert build._plain_date("2026-Nov-09 16:00") == "9 Nov 2026"
    assert build._plain_date("2026-Nov-09 16:00", with_year=False) == "9 Nov"
    assert build._plain_date("2026-day-012.345") == "2026-day-012.345"


def test_points_are_cut_where_the_path_jumps_across_the_edge_of_the_compass():
    pieces = build.pieces([170.0, 179.0, -179.0, -170.0], [1.0, 2.0, 3.0, 4.0])
    assert pieces == [[(170.0, 1.0), (179.0, 2.0)], [(-179.0, 3.0), (-170.0, 4.0)]]
    assert build.compass_x(350.0) == -10.0 and build.compass_x(10.0) == 10.0 and build.compass_x(180.0) == -180.0


# ---------------------------------------------------------------- added by the member ADDITIONS-CHECK (14 November 2026)

def _words(svg: str) -> str:
    return " ".join("".join(node.itertext()) for node in ET.fromstring(svg).iter() if node.tag.endswith("text"))


def test_the_years_highest_sun_is_looked_for_among_the_rows_of_that_year_only():
    series = lunar_series(days=80.0, colatitude=4.0, season_peak_day=40.0)
    series["utc"] = [("2025" if i < 24 * 45 else "2026") + label[4:] for i, label in enumerate(series["utc"])]
    rows = np.array([label.startswith("2026-") for label in series["utc"]])
    record = build.lunar_record(TARGET, series, year=2026)
    assert record["year_max_utc"].startswith("2026-")
    assert record["year_max_elevation_deg"] == pytest.approx(float(series["elevation_deg"][rows].max()), abs=1e-3)
    assert record["year_max_elevation_deg"] < float(series["elevation_deg"].max()) - 0.05    # the 2025 rows go higher


def test_a_spell_longer_than_the_days_minutes_is_said_to_run_through_midnight():
    lunar, place = demo()
    assert place["longest_spell_minutes"] > place["minutes_in_band"]     # 292 against 285 minutes at Haughton on 3 August
    words = _words(build.svg(lunar, place))
    assert "of this calendar day" in words and "runs through midnight" in words
    assert "at most" not in words                                        # "285 min, at most 292 min" reads as a mistake


def test_separate_dawn_and_dusk_spells_are_still_given_as_the_longest_without_a_break():
    lunar, _ = demo()
    cell = {"id": "55.0_10.0", "lat": 55.05, "lon": 10.05, "region": "made up",
            "targets": {"malapert": {"top_bins": [[8, 5.0]]}}}
    place = build.earth_record(PLACE, cell, TARGET, lambda lat, lon: (None, "tile not on disk: x"))
    assert 0 < place["longest_spell_minutes"] < place["minutes_in_band"]  # dawn and dusk, each under an hour
    words = _words(build.svg(lunar, place))
    assert "without a break" in words and "runs through midnight" not in words

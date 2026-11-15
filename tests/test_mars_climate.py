"""Mars part, climate side: the Sun of a Mars site, the half-degree Earth grid, POWER answers,
precipitation units, bare ground per square. No test touches the network."""
from __future__ import annotations

import json
import math

import numpy as np
import pytest

from twinfinder import mars_climate as mc

MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]


# ---- the Sun of a Mars site ---------------------------------------------------------------------

def test_noon_sun_at_the_equator_reaches_the_zenith_and_drops_by_the_tilt():
    low, high = mc.noon_elevation_range(0.0)
    assert high == pytest.approx(90.0)
    assert low == pytest.approx(90.0 - 25.19)


def test_noon_sun_at_the_tropic_of_mars():
    low, high = mc.noon_elevation_range(25.19)
    assert high == pytest.approx(90.0)
    assert low == pytest.approx(90.0 - 2 * 25.19)


def test_noon_sun_is_symmetric_north_and_south():
    assert mc.noon_elevation_range(-40.0) == pytest.approx(mc.noon_elevation_range(40.0))


def test_noon_sun_at_the_phoenix_site_goes_below_the_horizon():
    low, high = mc.noon_elevation_range(68.22)
    assert low == pytest.approx(90 - 68.22 - 25.19)      # -3.41: the Sun stays down at noon, polar night
    assert high == pytest.approx(90 - 68.22 + 25.19)     # 46.97
    assert low < 0


def test_earth_tilt_is_used_when_asked():
    low, high = mc.noon_elevation_range(60.0, tilt_deg=mc.EARTH_TILT_DEG)
    assert low == pytest.approx(90 - 60 - 23.44)
    assert high == pytest.approx(90 - 60 + 23.44)


def test_day_length_at_the_equator_is_half_a_sol_all_year():
    for decl in (-25.19, 0.0, 25.19):
        assert mc.day_length_h(0.0, decl) == pytest.approx(mc.SOL_H / 2)


def test_day_length_at_equinox_is_half_a_sol_everywhere():
    for lat in (-60.0, 18.4, 68.0):
        assert mc.day_length_h(lat, 0.0) == pytest.approx(mc.SOL_H / 2)


def test_day_length_follows_the_sunrise_hour_angle():
    lat, decl = 40.0, 25.19
    h0 = math.degrees(math.acos(-math.tan(math.radians(lat)) * math.tan(math.radians(decl))))
    assert mc.day_length_h(lat, decl) == pytest.approx(2 * h0 / 360 * 24.66)


def test_polar_night_and_polar_day():
    assert mc.day_length_h(68.22, -25.19) == 0.0
    assert mc.day_length_h(68.22, 25.19) == pytest.approx(24.66)


def test_day_length_range_of_a_polar_site():
    short, long_ = mc.day_length_range(68.22)
    assert short == 0.0 and long_ == pytest.approx(24.66)


def test_day_length_range_of_a_southern_site_mirrors_the_north():
    assert mc.day_length_range(-4.5895) == pytest.approx(mc.day_length_range(4.5895))
    short, long_ = mc.day_length_range(-4.5895)
    assert short < 12.33 < long_


def test_site_sun_block_has_the_plan_fields_and_says_how():
    block = mc.site_sun(18.442)
    assert set(block) == {"noon_elev_min_deg", "noon_elev_max_deg", "day_length_min_h", "day_length_max_h", "how"}
    assert block["noon_elev_max_deg"] == 90.0
    assert "25.19" in block["how"] and "24.66" in block["how"]


# ---- the half-degree grid -------------------------------------------------------------------------

def test_square_id_has_two_decimals():
    assert mc.square_id(-77.75, 161.25) == "m_-77.75_161.25"
    assert mc.square_id(10.25, 0.25) == "m_10.25_0.25"


def test_square_of_a_point():
    assert mc.square_of(-77.8, 161.3) == (-77.75, 161.25)
    assert mc.square_of(0.0, 0.0) == (0.25, 0.25)
    assert mc.square_of(-0.01, -0.01) == (-0.25, -0.25)
    assert mc.square_of(83.9, 179.99) == (83.75, 179.75)


def test_grid_rows_run_from_85_south_to_84_north():
    lats = mc.row_centres()
    assert lats[0] == -84.75 and lats[-1] == 83.75
    assert len(lats) == 338
    lons = mc.column_centres()
    assert lons[0] == -179.75 and lons[-1] == 179.75 and len(lons) == 720


def test_square_area():
    # a square at the equator: 0.5 deg by 0.5 deg on a sphere of 6371.0088 km
    r = 6371.0088
    expected = r * r * math.radians(0.5) * (math.sin(math.radians(0.5)) - 0.0)
    assert mc.square_km2(0.25) == pytest.approx(expected)
    assert mc.square_km2(-60.25) == pytest.approx(mc.square_km2(60.25))


# ---- POWER answers --------------------------------------------------------------------------------

def answer(parameter, units, points, fill=-999.0):
    features = []
    for (lat, lon), values in points.items():
        months = dict(zip(MONTHS, values[:12]))
        months["ANN"] = values[12]
        features.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat, 120.0]},
                         "properties": {"parameter": {parameter: months}}})
    return json.dumps({"type": "FeatureCollection", "features": features,
                       "header": {"api": {"version": "v2.10.1", "name": "POWER Climatology API"},
                                  "sources": ["MERRA2"], "fill_value": fill, "start": "20010101",
                                  "end": "20251231"},
                       "messages": [], "parameters": {parameter: {"units": units, "longname": parameter}}})


def test_read_power_precipitation_keeps_a_real_zero_and_nulls_the_fill_value():
    raw = answer("PRECTOTCORR", "mm/day", {(-24.0, -70.0): [0.0] * 11 + [-999.0, 0.01]})
    rows = mc.read_power(raw, "PRECTOTCORR")
    months, ann = rows[(-24.0, -70.0)]
    assert months[:11] == [0.0] * 11
    assert months[11] is None
    assert ann == 0.01


def test_read_power_refuses_wrong_units():
    raw = answer("PRECTOTCORR", "mm/hour", {(0.0, 0.0): [1.0] * 13})
    with pytest.raises(ValueError, match="units"):
        mc.read_power(raw, "PRECTOTCORR")


def test_read_power_refuses_values_out_of_range():
    raw = answer("PS", "kPa", {(0.0, 0.0): [101.0] * 11 + [500.0, 101.0]})
    with pytest.raises(ValueError, match="PS"):
        mc.read_power(raw, "PS")


def test_read_power_longitude_180_becomes_minus_180():
    raw = answer("T2M", "C", {(10.0, 180.0): [20.0] * 13})
    assert (10.0, -180.0) in mc.read_power(raw, "T2M")


def test_read_power_refuses_an_error_message():
    with pytest.raises(ValueError):
        mc.read_power(json.dumps({"messages": ["too many"], "header": {}}), "T2M")


# ---- precipitation units ----------------------------------------------------------------------------

def test_precipitation_per_month_is_mm_per_day_times_days():
    months = mc.precip_mm_month([1.0] * 12)
    assert months[0] == pytest.approx(31.0)
    assert months[1] == pytest.approx(28.25)     # February, mean of a 4-year leap cycle
    assert months[3] == pytest.approx(30.0)
    assert sum(months) == pytest.approx(365.25)


def test_precipitation_per_year_is_the_sum_of_the_months():
    months = mc.precip_mm_month([2.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.5])
    assert mc.precip_mm_year(months) == pytest.approx(2 * 31 + 31 + 0.5 * 31)


def test_precipitation_unknown_month_gives_unknown_year_never_zero():
    months = mc.precip_mm_month([1.0] * 11 + [None])
    assert months[11] is None
    assert mc.precip_mm_year(months) is None
    assert mc.precip_mm_month(None) is None


# ---- bare ground per square from a WorldCover tile -----------------------------------------------

def test_worldcover_tile_gives_36_squares_with_land_share_of_all_samples():
    classes = np.zeros((360, 360), dtype=np.uint8)          # all no data (open sea beyond the coast)
    classes[0:60, 0:60] = 60                                  # north-west square: all bare
    classes[0:60, 60:120] = 80                                # next square east: water
    classes[0:30, 60:120] = 30                                # half of it grass
    classes[60:120, 0:30] = 60                                # a square half bare, half no data
    squares = {s["id"]: s for s in mc.worldcover_squares(classes, 6, -72)}
    nw = squares[mc.square_id(8.75, -71.75)]
    assert nw["land_share"] == 1.0 and nw["bare"] == 1.0
    grass = squares[mc.square_id(8.75, -71.25)]
    assert grass["land_share"] == pytest.approx(0.5) and grass["bare"] == 0.0
    half = squares[mc.square_id(8.25, -71.75)]
    assert half["land_share"] == pytest.approx(0.5) and half["bare"] == 1.0
    assert len(squares) == 3                                  # squares without land are not listed


def test_worldcover_tile_must_be_360_samples():
    with pytest.raises(ValueError):
        mc.worldcover_squares(np.zeros((100, 100), dtype=np.uint8), 0, 0)


# ---- bare ground in Antarctica from the rock-outcrop cells ----------------------------------------

def test_south_rock_is_spread_by_longitude_overlap_and_divided_by_square_land():
    # a 0.1 deg row at 84.5 S, 1.2 deg wide (the project's width there), 100 km2 of rock
    cells = [{"id": "-84.5_160.0", "rock_landsat_km2": 40.0, "rock_medium_km2": 100.0}]
    land = {(-84.25, 160.25): 400.0, (-84.25, 160.75): 400.0, (-84.25, 161.25): 400.0}
    rock = mc.south_rock_km2(cells)
    assert rock[(-84.25, 160.25)] == pytest.approx(100.0 * 0.5 / 1.2)
    assert rock[(-84.25, 161.25)] == pytest.approx(100.0 * 0.2 / 1.2)
    assert sum(rock.values()) == pytest.approx(100.0)
    bare = mc.south_bare(rock, land)
    assert bare[(-84.25, 160.25)] == pytest.approx(100.0 * 0.5 / 1.2 / 400.0)


def test_south_bare_is_capped_at_one_and_unknown_without_land():
    bare = mc.south_bare({(-70.25, 10.25): 50.0, (-70.25, 10.75): 5.0}, {(-70.25, 10.25): 10.0})
    assert bare[(-70.25, 10.25)] == 1.0
    assert bare.get((-70.25, 10.75)) is None


def test_south_rock_leaves_out_cells_south_of_the_grid():
    cells = [{"id": "-85.3_0.0", "rock_landsat_km2": 1.0, "rock_medium_km2": 1.0}]
    assert mc.south_rock_km2(cells) == {}


# ---- land share from the Natural Earth outline ------------------------------------------------------

def test_land_fraction_of_a_box_polygon():
    geojson = {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {}, "geometry": {
        "type": "Polygon", "coordinates": [[[10.0, 20.0], [10.5, 20.0], [10.5, 20.25], [10.0, 20.25], [10.0, 20.0]]]}}]}
    frac = mc.land_fraction_grid(geojson, per_side=10)
    row = mc.row_centres().index(20.25)
    col = mc.column_centres().index(10.25)
    assert frac[row, col] == pytest.approx(0.5)
    assert frac[row, col + 1] == 0.0
    assert frac.shape == (338, 720)


# ---- Mars Climate Database tables (web interface, ASCII answer) -------------------------------------

def mcd_text(blocks):
    """An answer laid out as the MCD v6.2 web interface writes it: one block per variable."""
    out = []
    for name, rows in blocks:
        out += ["#" * 20, "### MCD_v6.2 with climatology average solar scenario.",
                "### Latitude 18.442N. Longitude 77.452E. Altitude 2.0 m ALS.",
                "### Column 1 is Areocentric longitude (degrees)", f"### Columns 2+ are {name}",
                "### Line 1 is Local time (Martian hour)", "#" * 20,
                "---- ||    0.00000e+00    1.20000e+01    2.40000e+01", "-" * 35]
        for ls, values in rows:
            out.append(f"+{ls:03d} ||" + "".join(f"    {v:.5e}" for v in values))
    return "\n".join(out) + "\n"


def test_read_mcd_table_gives_one_grid_per_variable():
    text = mcd_text([("Temperature (K)", [(0, [200.0, 240.0, 200.0]), (180, [210.0, 250.0, 210.0]),
                                          (360, [200.0, 240.0, 200.0])]),
                     ("Surface pressure (Pa)", [(0, [700.0, 701.0, 700.0]), (180, [800.0, 801.0, 800.0]),
                                                (360, [700.0, 701.0, 700.0])])])
    tables = mc.read_mcd_table(text)
    assert set(tables) == {"Temperature (K)", "Surface pressure (Pa)"}
    t = tables["Temperature (K)"]
    assert t["ls"] == [0.0, 180.0, 360.0]
    assert t["local_time"] == [0.0, 12.0, 24.0]
    assert t["values"].shape == (3, 3)
    assert t["values"][1, 1] == pytest.approx(250.0)


def test_ls_weights_follow_keplers_second_law():
    w = mc.ls_weights([71.0, 251.0])            # aphelion and perihelion seasons
    ratio = ((1 + 0.0934) / (1 - 0.0934)) ** 2   # time per degree of Ls goes as r squared
    assert w[0] / w[1] == pytest.approx(ratio)
    assert sum(mc.ls_weights(list(range(0, 360, 15)))) == pytest.approx(1.0)


def test_mcd_summary_drops_the_repeated_rows_and_weights_by_time():
    values = np.array([[200.0, 240.0, 200.0],      # Ls 0
                       [210.0, 260.0, 210.0],      # Ls 180
                       [200.0, 240.0, 200.0]])     # Ls 360, the same as Ls 0
    table = {"ls": [0.0, 180.0, 360.0], "local_time": [0.0, 12.0, 24.0], "values": values}
    out = mc.mcd_summary(table)
    w = mc.ls_weights([0.0, 180.0])
    daily_mean = [220.0, 235.0]                      # mean over local times 0 and 12 (24 repeats 0)
    assert out["annual_mean"] == pytest.approx(w[0] * daily_mean[0] + w[1] * daily_mean[1])
    assert out["warm_season_daily_max"] == pytest.approx(260.0)
    assert out["cold_season_daily_min"] == pytest.approx(200.0)
    assert out["warmest_ls"] == 180.0 and out["coldest_ls"] == 0.0


# ---- lander records ------------------------------------------------------------------------------------

def test_seasonal_extremes_use_bins_of_ls_and_need_enough_sols():
    sols = ([(10.0 + i * 0.1, -80.0, -20.0) for i in range(20)]      # bin 0-15: 20 sols
            + [(100.0, -60.0, -5.0)] * 3)                             # bin 90-105: 3 sols, too few
    out = mc.seasonal_extremes(sols, min_sols=5)
    assert out["warm_season_daily_max"] == pytest.approx(-20.0)
    assert out["cold_season_daily_min"] == pytest.approx(-80.0)
    assert out["bins_used"] == 1
    assert out["ls_covered"] == [[0.0, 15.0]]


def test_seasonal_extremes_skip_unknown_values_and_say_none_without_data():
    out = mc.seasonal_extremes([(10.0, None, -20.0)] * 6, min_sols=5)
    assert out["warm_season_daily_max"] == pytest.approx(-20.0)
    assert out["cold_season_daily_min"] is None
    assert mc.seasonal_extremes([], min_sols=5)["warm_season_daily_max"] is None


def test_phoenix_sol_reads_the_1000_mm_sensor_and_needs_most_of_a_sol():
    def row(t, p, tmin, tmax):
        values = [t, p, 0.0, p, p] + [230.0, 1.0, 229.0, 231.0] * 2 + [230.0, 1.0, tmin, tmax, 260.0, 0.0]
        return ",".join(f"{v:15.4f}" for v in values)
    rows = [row(512.0 * i, 800.0, 200.0 + i * 0.01, 250.0 - i * 0.01) for i in range(170)]
    out = mc.phoenix_sol("\n".join(rows))
    assert out["min_k"] == pytest.approx(200.0)
    assert out["max_k"] == pytest.approx(250.0)
    assert out["pressure_pa"] == pytest.approx(800.0)
    assert out["hours"] == pytest.approx(170 * 512 / 3600)
    short = mc.phoenix_sol("\n".join(rows[:50]))
    assert short["min_k"] is None and short["max_k"] is None and short["pressure_pa"] == pytest.approx(800.0)


def test_phoenix_file_of_several_sols_gives_no_daily_extremes():
    row = ",".join(f"{v:15.4f}" for v in [0.0, 800.0, 0.0, 800.0, 800.0] + [230.0, 1.0, 229.0, 231.0] * 2
                   + [230.0, 1.0, 200.0, 250.0, 260.0, 0.0])
    long_file = mc.phoenix_sol("\n".join([row] * 480))      # 68 h, about 2.8 sols
    assert long_file["min_k"] is None and long_file["max_k"] is None
    assert long_file["pressure_pa"] == pytest.approx(800.0)


# ---- the build script's own helpers (written after the script: see the MARS-CLIMATE report) ---------

import importlib  # noqa: E402

build = importlib.import_module("scripts.build_mars_climate")


def test_yearly_pressure_needs_every_ls_bin_and_weights_by_time():
    pairs = [(k * 15 + 1.0, 800.0 + k) for k in range(24)]
    w = mc.ls_weights([k * 15 + 7.5 for k in range(24)])
    assert build.ls_bin_pressure(pairs) == pytest.approx(sum(w[k] * (800.0 + k) for k in range(24)))
    assert build.ls_bin_pressure(pairs[:-1]) is None


def test_worldcover_tiles_are_asked_only_near_land():
    frac = np.zeros((338, 720))
    frac[mc.row_centres().index(10.25), mc.column_centres().index(20.25)] = 0.5
    origins = build.wc_origins(frac, -60, 57)
    assert (9, 18) in origins and len(origins) == 1


def test_every_cannot_match_item_has_a_number_or_says_why_and_a_source():
    climate = {"pressure_pa": 818, "kind_by_field": {"pressure_pa": "measured by a lander"},
               "source_by_field": {"pressure_pa": "measured by a lander (Curiosity REMS ...)"}}
    items = build.cannot_match({"id": "gale"}, climate, 55.0, "m_33.75_85.25")
    assert {i["what"] for i in items} >= {"surface air pressure", "gravity", "the dusty sky", "length of the year"}
    for item in items:
        assert {"what", "mars", "earth", "number", "unit", "source"} <= set(item)
        assert item["number"] is not None or "see note" in item["number_is"]
    pressure = items[0]
    assert pressure["mars"] == 818 and pressure["mars_site_over_earth_lowest_land_square"] == pytest.approx(818 / 55000, abs=1e-4)

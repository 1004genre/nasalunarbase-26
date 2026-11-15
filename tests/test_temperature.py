# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Earth temperature row from NASA POWER (survey of other teams, gap 3). No test touches the network."""
from __future__ import annotations

import datetime
import json
import urllib.error

import pytest

from twinfinder import cloud, sun, temperature

MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

# The first two grid points and the header of a real answer of the regional climatology
# service (asked on 14 November 2026 for 60 to 70 N, 30 to 20 W, T2M), unchanged.
REAL_ANSWER = (
    '{"features":[{"type":"Feature","geometry":{"type":"Point","coordinates":[-30.0,60.0,0.0]},'
    '"properties":{"parameter":{"T2M":{"JAN":4.62,"FEB":4.44,"MAR":4.51,"APR":5.45,"MAY":6.73,'
    '"JUN":8.66,"JUL":10.11,"AUG":10.77,"SEP":9.57,"OCT":7.73,"NOV":6.17,"DEC":5.12,"ANN":7.0}}}},'
    '{"type":"Feature","geometry":{"type":"Point","coordinates":[-29.375,60.0,0.0]},"properties":'
    '{"parameter":{"T2M":{"JAN":4.79,"FEB":4.63,"MAR":4.67,"APR":5.6,"MAY":6.87,"JUN":8.8,'
    '"JUL":10.26,"AUG":10.88,"SEP":9.69,"OCT":7.85,"NOV":6.32,"DEC":5.28,"ANN":7.15}}}}],'
    '"header":{"title":"NASA/POWER Source Native Resolution Climatology Climatologies","api":'
    '{"version":"v2.10.1","name":"POWER Climatology API"},"sources":["MERRA2"],"fill_value":-999.0,'
    '"time_standard":"LST","start":"20010101","end":"20251231"},"messages":["The requested '
    'parameters are retrieved from a pre-computed climatological period (January 2001 - December '
    '2025)"],"parameters":{"T2M":{"units":"C","longname":"Temperature at 2 Meters"}},'
    '"times":{"data":0.041,"process":0.08},"type":"FeatureCollection"}'
)

ERROR_ANSWER = (
    '{"header":"The POWER Climatology API failed to complete your request; please review the '
    'errors below and the POWER Docs (https://power.larc.nasa.gov/docs/).","messages":["Please '
    'provide a maximum of 10 degree range in latitude."]}'
)


def answer(points: dict, parameter: str = "T2M", fill=-999.0, elev: float = 12.3) -> str:
    """A made-up answer in the service's layout. points maps (lat, lon) to 12 values."""
    features = []
    for (lat, lon), values in points.items():
        months = dict(zip(MONTHS, values))
        months["ANN"] = 1.0
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat, elev]},  # GeoJSON: longitude first
            "properties": {"parameter": {parameter: months}},
        })
    header = {"api": {"version": "v2.10.1", "name": "POWER Climatology API"}, "sources": ["MERRA2"],
              "start": "20010101", "end": "20251231", "fill_value": fill}
    return json.dumps({"features": features, "header": header, "type": "FeatureCollection"})


# ---- ten-day bins ---------------------------------------------------------------------------

def test_by_bin_gives_36_values_each_bin_taking_the_month_of_its_middle_day():
    months = [float(m) for m in range(12)]            # January is 0.0, December is 11.0
    got = temperature.by_bin(months)
    assert len(got) == 36
    assert got == [float(b // 3) for b in range(36)]
    # the rule itself, spelled out against the project's bin rule: bin = min((day - 1) // 10, 35)
    for b in range(36):
        days = [d for d in range(1, 366) if sun.bin_index(d) == b]
        middle = days[len(days) // 2]
        month = (datetime.date(2025, 1, 1) + datetime.timedelta(days=middle - 1)).month - 1
        assert got[b] == float(month), b


def test_by_bin_keeps_negative_temperatures_and_null_stays_null():
    months = [-30.5, None, float("nan")] + [2.0] * 9
    got = temperature.by_bin(months)
    assert got[0:3] == [-30.5, -30.5, -30.5]
    assert got[3:9] == [None] * 6                      # February and March: unknown, never 0
    assert got[9] == 2.0
    assert temperature.by_bin(None) == [None] * 36


def test_by_bin_refuses_a_list_that_is_not_12_months():
    with pytest.raises(ValueError):
        temperature.by_bin([1.0] * 11)


# ---- the grid ---------------------------------------------------------------------------------

def test_grid_point_is_the_nearest_point_of_the_half_by_five_eighths_degree_grid():
    assert temperature.grid_point(63.85, -22.5) == (64.0, -22.5)
    assert temperature.grid_point(63.6, -22.2) == (63.5, -22.5)
    assert temperature.grid_point(63.6, -22.1) == (63.5, -21.875)      # -22.1875 is the half-way line
    assert temperature.grid_point(-68.45, 78.15) == (-68.5, 78.125)
    assert temperature.grid_point(74.95, 141.25) == (75.0, 141.25)


def test_grid_point_sends_a_centre_half_way_between_two_rows_to_the_row_above_noise_or_not():
    assert temperature.grid_point(59.25, 10.0) == (59.5, 10.0)
    assert temperature.grid_point(59.25 - 1e-12, 10.0) == (59.5, 10.0)
    assert temperature.grid_point(-68.25, 10.0) == (-68.0, 10.0)
    assert temperature.grid_point(-68.25 + 1e-12, 10.0) == (-68.0, 10.0)


def test_grid_point_wraps_at_the_date_line_because_the_grid_has_minus_180_and_not_plus_180():
    assert temperature.grid_point(70.05, 179.85) == (70.0, -180.0)
    assert temperature.grid_point(70.05, 179.6) == (70.0, 179.375)
    assert temperature.grid_point(70.05, -179.85) == (70.0, -180.0)


def test_tiles_for_cells_takes_each_cells_own_block_and_adds_the_block_across_the_date_line():
    cells = [{"id": "a", "lat": 63.85, "lon": -22.5},      # block 60..70, -30..-20
             {"id": "b", "lat": 69.95, "lon": -20.05},     # grid point 70.0, -20.0 is the corner of the same block
             {"id": "c", "lat": 70.05, "lon": 179.85}]     # grid point 70.0, -180.0 is not in block 170..180
    tiles = temperature.tiles_for_cells(cells)
    assert tiles == sorted([(60, 70, -30, -20), (70, 80, 170, 180), (70, 80, -180, -170)])


def test_every_grid_point_lies_in_a_block_that_tiles_for_cells_asks_for():
    cells = [{"id": str(n), "lat": lat, "lon": lon}
             for n, (lat, lon) in enumerate([(59.05, -109.1), (69.95, 29.95), (79.95, -0.05), (-68.45, 78.15),
                                             (82.75, 179.7), (-87.35, -179.9), (60.05, 0.05)])]
    tiles = temperature.tiles_for_cells(cells)
    for cell in cells:
        lat, lon = temperature.grid_point(cell["lat"], cell["lon"])
        assert any(t[0] <= lat <= t[1] and t[2] <= lon <= t[3] and not (lon == 180.0) for t in tiles), cell


# ---- reading a raw answer -------------------------------------------------------------------

def test_read_answer_reads_a_real_answer_with_latitude_first_and_january_first():
    got = temperature.read_answer(REAL_ANSWER, "T2M")
    assert set(got) == {(60.0, -30.0), (60.0, -29.375)}
    assert got[(60.0, -30.0)] == [4.62, 4.44, 4.51, 5.45, 6.73, 8.66, 10.11, 10.77, 9.57, 7.73, 6.17, 5.12]
    assert all(len(values) == 12 for values in got.values())   # the yearly figure "ANN" is left out


def test_read_answer_keeps_frost_and_turns_the_fill_value_into_null_not_a_number():
    values = [-999.0, -999, -45.07, 0.0] + [3.5] * 8
    got = temperature.read_answer(answer({(-70.0, 77.5): values}), "T2M")[(-70.0, 77.5)]
    assert got[0] is None and got[1] is None
    assert got[2] == -45.07
    assert got[3] == 0.0                                 # a real zero stays a zero


def test_read_answer_uses_the_fill_value_the_header_names():
    values = [-9999.0] + [1.0] * 11
    got = temperature.read_answer(answer({(60.0, 10.0): values}, fill=-9999.0), "T2M")[(60.0, 10.0)]
    assert got[0] is None


def test_read_answer_refuses_a_temperature_no_place_on_earth_has():
    with pytest.raises(ValueError):
        temperature.read_answer(answer({(60.0, 10.0): [250.0] + [1.0] * 11}), "T2M")   # kelvin, not Celsius
    with pytest.raises(ValueError):
        temperature.read_answer(answer({(60.0, 10.0): ["warm"] + [1.0] * 11}), "T2M")


def test_read_answer_refuses_an_error_message_and_another_parameter():
    with pytest.raises(ValueError):
        temperature.read_answer(ERROR_ANSWER, "T2M")
    with pytest.raises(ValueError):
        temperature.read_answer(REAL_ANSWER, "TS")


def test_read_elevations_gives_the_height_the_service_names_for_each_grid_point():
    raw = answer({(-70.0, 77.5): [1.0] * 12}, elev=1353.22)
    assert temperature.read_elevations(raw) == {(-70.0, 77.5): 1353.22}


# ---- fetching ---------------------------------------------------------------------------------

class FakeResponse:
    def __init__(self, body: bytes):
        self.body = body

    def read(self) -> bytes:
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_fetch_tile_asks_once_with_the_project_user_agent_and_then_reads_from_disk(tmp_path):
    asked = []

    def opener(request, timeout):
        asked.append(request)
        return FakeResponse(REAL_ANSWER.encode())

    tile = (60, 70, -30, -20)
    path, did_ask = temperature.fetch_tile("T2M", tile, tmp_path, opener=opener, sleep=lambda s: None)
    assert did_ask and path.read_bytes() == REAL_ANSWER.encode()
    assert path.name == "T2M_N60_N70_W030_W020.json"
    assert asked[0].get_header("User-agent") == "twinfinder/0.1"
    assert asked[0].full_url == cloud.regional_url("T2M", tile)
    assert "parameters=T2M&" in asked[0].full_url and "/climatology/regional?" in asked[0].full_url
    again, did_ask_again = temperature.fetch_tile("T2M", tile, tmp_path, opener=opener, sleep=lambda s: None)
    assert again == path and not did_ask_again and len(asked) == 1


def test_fetch_tile_waits_and_tries_again_when_the_service_says_too_many_requests(tmp_path):
    calls, waits = [], []

    def opener(request, timeout):
        calls.append(1)
        if len(calls) < 3:
            raise urllib.error.HTTPError(request.full_url, 429, "Too Many Requests", {"Retry-After": "7"}, None)
        return FakeResponse(REAL_ANSWER.encode())

    path, did_ask = temperature.fetch_tile("T2M", (60, 70, -30, -20), tmp_path, opener=opener, sleep=waits.append)
    assert did_ask and path.exists() and len(calls) == 3
    assert waits == [7.0, 7.0]


def test_fetch_tile_keeps_nothing_when_the_answer_is_an_error_message_or_asks_for_a_login(tmp_path):
    with pytest.raises(ValueError):
        temperature.fetch_tile("T2M", (60, 70, -30, -20), tmp_path,
                               opener=lambda request, timeout: FakeResponse(ERROR_ANSWER.encode()),
                               sleep=lambda s: None)

    def refuses(request, timeout):
        raise urllib.error.HTTPError(request.full_url, 401, "Unauthorized", {}, None)

    with pytest.raises(urllib.error.HTTPError):
        temperature.fetch_tile("T2M", (60, 70, -30, -20), tmp_path, opener=refuses, sleep=lambda s: None)
    assert list(tmp_path.iterdir()) == []


# ---- the table of cells -----------------------------------------------------------------------

def test_cells_table_gives_each_cell_its_grid_point_four_rows_and_null_for_unknown():
    cells = [{"id": "63.8_-22.6", "lat": 63.85, "lon": -22.5},
             {"id": "63.8_-22.4", "lat": 63.85, "lon": -22.3},      # same grid point
             {"id": "80.0_20.0", "lat": 80.05, "lon": 20.3},        # every month is fill
             {"id": "70.0_100.0", "lat": 70.05, "lon": 100.25}]     # the service gave no such point
    warm = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0]
    by_point = {
        "T2M": {(64.0, -22.5): warm, (80.0, 20.0): [None] * 12},
        "T2M_MAX": {(64.0, -22.5): [v + 8 for v in warm], (80.0, 20.0): [None] * 12},
        "T2M_MIN": {(64.0, -22.5): [v - 9 for v in warm], (80.0, 20.0): [None] * 12},
        "TS": {(64.0, -22.5): [None] + warm[1:], (80.0, 20.0): [None] * 12},
    }
    table = temperature.cells_table(cells, by_point, elevations={(64.0, -22.5): 58.88})
    assert list(table) == [cell["id"] for cell in cells]
    first = table["63.8_-22.6"]
    assert first == {"t2m_c": warm, "t2m_max_c": [v + 8 for v in warm], "t2m_min_c": [v - 9 for v in warm],
                     "ts_c": [None] + warm[1:], "grid": [64.0, -22.5], "grid_elev_m": 58.88}
    assert table["63.8_-22.4"] == first
    assert table["80.0_20.0"] == {"t2m_c": None, "t2m_max_c": None, "t2m_min_c": None, "ts_c": None,
                                  "grid": [80.0, 20.0], "grid_elev_m": None}
    assert table["70.0_100.0"]["t2m_c"] is None and table["70.0_100.0"]["grid"] == [70.0, 100.0]
    json.dumps(table, allow_nan=False)                   # nothing in it that JSON cannot hold


def test_meta_from_names_source_period_grid_and_what_the_extremes_are():
    headers = {p: [cloud.answer_header(answer({(60.0, 10.0): [1.0] * 12}, parameter=p))] for p in temperature.PARAMETERS}
    meta = temperature.meta_from(headers, fetched="2026-11-14T23:59:00Z")
    for key in ("source", "parameters", "period", "grid_deg", "fetched", "url_pattern", "what_it_is"):
        assert key in meta, key
    assert meta["parameters"] == ["T2M", "T2M_MAX", "T2M_MIN", "TS"]
    assert meta["period"] == "2001-01-01 to 2025-12-31"
    assert meta["grid_deg"] == [0.5, 0.625]
    assert "MERRA2" in meta["source"] and "POWER" in meta["source"]
    assert meta["url_pattern"] == cloud.URL_PATTERN
    assert "t2m_max_c" in meta["fields"] and "not the mean daily maximum" in meta["fields"]["t2m_max_c"]


def test_meta_from_refuses_answers_that_disagree_about_the_period():
    a = cloud.answer_header(answer({(60.0, 10.0): [1.0] * 12}))
    b = dict(a, end="20201231")
    with pytest.raises(ValueError):
        temperature.meta_from({p: [a, b] for p in temperature.PARAMETERS}, fetched="x")


# ---- daily series at a named place ------------------------------------------------------------

def daily_answer(series: dict) -> str:
    return json.dumps({"type": "Feature", "geometry": {"type": "Point", "coordinates": [-22.5, 64.0, 58.88]},
                       "properties": {"parameter": series},
                       "header": {"fill_value": -999.0, "start": "20010101", "end": "20011231",
                                  "api": {"version": "v2.8.20", "name": "POWER Daily API"}, "sources": ["MERRA2"]}})


def test_read_daily_gives_dates_and_turns_fill_into_null():
    raw = daily_answer({"T2M_MAX": {"20010101": 3.0, "20010102": -999.0}})
    got = temperature.read_daily(raw, "T2M_MAX")
    assert got == {datetime.date(2001, 1, 1): 3.0, datetime.date(2001, 1, 2): None}
    with pytest.raises(ValueError):
        temperature.read_daily(raw, "TS")


def test_daily_mean_by_bin_averages_days_into_the_projects_ten_day_bins():
    series = {}
    for year in (2001, 2004):                              # 2004 is a leap year
        day = datetime.date(year, 1, 1)
        while day.year == year:
            series[day] = float(sun.bin_index(day.timetuple().tm_yday))   # each day carries its own bin number
            day += datetime.timedelta(days=1)
    series[datetime.date(2001, 1, 5)] = None               # a missing day is left out, not counted as 0
    means, counts = temperature.daily_mean_by_bin(series)
    assert len(means) == 36 and len(counts) == 36
    assert means == [float(b) for b in range(36)]
    assert counts[0] == 19 and counts[1] == 20
    assert counts[35] == 15 + 16                           # days 351 to 365, and to 366 in the leap year


def test_daily_mean_by_bin_gives_null_for_a_bin_without_any_day():
    means, counts = temperature.daily_mean_by_bin({datetime.date(2001, 1, 1): -4.0, datetime.date(2001, 1, 2): -6.0})
    assert means[0] == -5.0 and counts[0] == 2
    assert means[1:] == [None] * 35 and counts[1:] == [0] * 35


def test_monthly_extremes_and_mean_tell_a_record_from_a_mean_daily_maximum():
    series = {datetime.date(2001, 7, d): 10.0 for d in range(1, 32)}
    series.update({datetime.date(2002, 7, d): 12.0 for d in range(1, 32)})
    series[datetime.date(2002, 7, 15)] = 21.0
    stats = temperature.monthly_statistics(series)
    assert stats["mean"][6] == pytest.approx((31 * 10.0 + 30 * 12.0 + 21.0) / 62)
    assert stats["highest"][6] == 21.0 and stats["lowest"][6] == 10.0
    assert stats["mean"][0] is None and stats["highest"][0] is None


# ---- the build script (no request: every raw answer is made up and already on disk) ---------------

import importlib  # noqa: E402
import sys  # noqa: E402

build = importlib.import_module("scripts.build_temperature_cells")


def test_bin_label_gives_the_dates_of_a_ten_day_bin():
    assert build.bin_label(0) == "1 Jan-10 Jan"
    assert build.bin_label(21) == "30 Jul-8 Aug"          # as RESULTS.md names bin 21
    assert build.bin_label(35) == "17 Dec-31 Dec"         # the last bin runs to the end of the year


def test_spread_gives_median_and_tenths_of_the_known_values_only():
    got = build.spread([None, 1.0, 2.0, 3.0, 4.0, 5.0, None])
    assert got == {"median": 3.0, "p10": 1.4, "p90": 4.6, "cells": 5}
    assert build.spread([None, None]) is None             # unknown stays unknown


def test_best_bins_north_reads_top_bins_and_south_reads_summer_rock_or_summer_bins_only():
    north = {"id": "n", "hemisphere": "N", "targets": {"malapert": {"top_bins": [[21, 39.3], [22, 36.6]]}}}
    assert build.best_bins(north, {}, [33, 34, 35, 0, 1])[0] == {"malapert": [[21, 39.3], [22, 36.6]]}
    south = {"id": "s", "hemisphere": "S", "targets": {"malapert": {"top_bins": [[35, 71.1], [14, 60.0], [1, 53.4]]}}}
    bins, source = build.best_bins(south, {}, [33, 34, 35, 0, 1])
    assert bins == {"malapert": [[35, 71.1], [1, 53.4]]} and "summer bins only" in source
    scored = {"s": {"targets": {"malapert": {"top_bins_summer_rock": [[35, 57.8], [34, 38.5]]}}}}
    bins, source = build.best_bins(south, scored, [33, 34, 35, 0, 1])
    assert bins == {"malapert": [[35, 57.8], [34, 38.5]]} and "top_bins_summer_rock" in source


def test_extremes_check_counts_the_months_in_which_the_climatology_is_the_record_of_the_daily_series():
    record = {"t2m_max_c": [20.0] * 11 + [None], "t2m_min_c": None}
    monthly = {"T2M_MAX": {"highest": [20.0] * 10 + [21.5, 20.0], "lowest": [0.0] * 12, "mean": [12.0] * 12},
               "T2M_MIN": {"highest": [0.0] * 12, "lowest": [-9.0] * 12, "mean": [-1.0] * 12}}
    got = build.extremes_check(record, monthly)
    assert got["T2M_MIN"] is None
    assert got["T2M_MAX"] == {"months_compared": 11, "months_equal_to_the_25_year_record_of_the_daily_series": 10,
                              "largest_gap_to_that_record_c": 1.5, "mean_gap_to_the_mean_daily_value_c": 8.0}


def test_build_script_offline_writes_the_file_in_the_agreed_shape(tmp_path, monkeypatch, capsys):
    raw = tmp_path / "raw"
    raw.mkdir()
    warm = [-3.0, -2.5, -1.0, 2.0, 6.0, 9.0, 11.0, 10.5, 8.0, 4.0, 0.5, -2.0]
    rows = {"T2M": warm, "T2M_MAX": [v + 9 for v in warm], "T2M_MIN": [v - 11 for v in warm],
            "TS": [-999.0] + warm[1:]}
    for parameter, values in rows.items():
        points = {(64.0, -22.5): values, (63.5, -22.5): [-999.0] * 12}
        (raw / cloud.raw_name(parameter, (60, 70, -30, -20))).write_text(answer(points, parameter=parameter, elev=58.88))
    cells = {"meta": {"summer_bins_south": [33, 34, 35, 0, 1, 2, 3, 4, 5]}, "cells": [
        {"id": "63.8_-22.6", "lat": 63.85, "lon": -22.5, "hemisphere": "N",
         "targets": {"malapert": {"top_bins": [[33, 34.4], [35, 21.1]]}, "connecting-ridge": {"top_bins": []}}},
        {"id": "63.5_-22.6", "lat": 63.55, "lon": -22.5, "hemisphere": "N", "targets": {}},
    ]}
    (tmp_path / "grazing_cells.json").write_text(json.dumps(cells))
    out = tmp_path / "temperature_cells.json"
    monkeypatch.setattr(build, "CELLS", tmp_path / "grazing_cells.json")
    monkeypatch.setattr(build, "SCORED", tmp_path / "cells_scored.json")
    monkeypatch.setattr(build, "MOON", tmp_path / "moon_cards.json")
    monkeypatch.setattr(build, "RAW", raw)
    monkeypatch.setattr(build, "DAILY", raw / "daily_points")
    monkeypatch.setattr(build, "LOG", raw / "fetch_log.jsonl")
    monkeypatch.setattr(build, "OUT", out)
    monkeypatch.setattr(sys, "argv", ["build_temperature_cells.py", "--offline"])
    build.main()
    capsys.readouterr()

    written = json.loads(out.read_text())
    assert set(written) == {"meta", "cells"}
    for key in ("source", "parameters", "period", "grid_deg", "fetched", "url_pattern", "what_it_is"):
        assert key in written["meta"], key
    assert written["cells"]["63.8_-22.6"] == {
        "t2m_c": warm, "t2m_max_c": [v + 9 for v in warm], "t2m_min_c": [v - 11 for v in warm],
        "ts_c": [None] + warm[1:], "grid": [64.0, -22.5], "grid_elev_m": 58.88}
    assert written["cells"]["63.5_-22.6"]["t2m_c"] is None           # all months fill: null, not zeros
    assert "-999" not in out.read_text().replace('"fill_value":-999.0', "")
    counts = written["meta"]["counts"]
    assert counts["cells"] == 2 and counts["cells_with_no_month"]["t2m_c"] == 1
    assert counts["north_cells"]["july"]["t2m_c"] == {"median": 11.0, "p10": 11.0, "p90": 11.0, "cells": 1}
    assert counts["south_cells"]["december"]["t2m_c"] is None
    places = {p["name"]: p for p in written["meta"]["named_places"]["places"]}
    reykjanes = places["Reykjanes"]
    assert reykjanes["cell"] == "63.8_-22.6" and reykjanes["daily_series"] is None   # offline: no daily series
    first = reykjanes["best_bins_by_target"]["malapert"][0]
    assert first["bin"] == 33 and first["dates"] == "27 Nov-6 Dec"
    assert first["month_climatology"]["t2m_c"] == -2.0               # bin 33 takes December
    assert reykjanes["best_bins_by_target"]["connecting-ridge"] == []
    assert "note" in places["Vestfold Hills"]                        # no such cell in this made-up project
    lunar = written["meta"]["lunar_comparison"]
    assert "moon_cards.json" in lunar["sentence"] and lunar["status"].startswith("placeholder")
    assert lunar["earth_low_c"] == -2.0 and lunar["earth_high_c"] == -2.0
    assert not list(tmp_path.glob("*.part"))


def test_build_script_offline_stops_when_a_raw_answer_is_missing(tmp_path, monkeypatch):
    (tmp_path / "grazing_cells.json").write_text(json.dumps({"meta": {}, "cells": [
        {"id": "63.8_-22.6", "lat": 63.85, "lon": -22.5, "hemisphere": "N", "targets": {}}]}))
    monkeypatch.setattr(build, "CELLS", tmp_path / "grazing_cells.json")
    monkeypatch.setattr(build, "RAW", tmp_path / "raw")
    monkeypatch.setattr(build, "LOG", tmp_path / "raw" / "fetch_log.jsonl")
    monkeypatch.setattr(build, "OUT", tmp_path / "temperature_cells.json")
    monkeypatch.setattr(sys, "argv", ["build_temperature_cells.py", "--offline"])
    with pytest.raises(SystemExit):
        build.main()
    assert not (tmp_path / "temperature_cells.json").exists()


def test_extremes_check_all_adds_the_places_up_and_is_null_without_any_check():
    equal = "months_equal_to_the_25_year_record_of_the_daily_series"
    one = {"months_compared": 12, equal: 8, "largest_gap_to_that_record_c": 1.5, "mean_gap_to_the_mean_daily_value_c": 6.0}
    two = {"months_compared": 12, equal: 11, "largest_gap_to_that_record_c": 4.85, "mean_gap_to_the_mean_daily_value_c": 10.0}
    places = [{"extremes_check": {"T2M_MAX": one, "T2M_MIN": None}}, {"extremes_check": {"T2M_MAX": two, "T2M_MIN": None}},
              {"extremes_check": None}, {"note": "no cell"}]
    assert build.extremes_check_all(places) == {"T2M_MAX": {
        "places": 2, "months_compared": 24, equal: 19, "largest_gap_to_that_record_c": 4.85,
        "mean_gap_to_the_mean_daily_value_c": 8.0}}
    assert build.extremes_check_all([{"extremes_check": None}]) is None


# ---- added by the member ADDITIONS-CHECK (14 November 2026) ----------------------------------------

def test_read_elevations_gives_null_when_the_service_names_the_fill_value_as_height():
    raw = answer({(-70.0, 77.5): [1.0] * 12}, elev=-999.0)
    assert temperature.read_elevations(raw) == {(-70.0, 77.5): None}     # -999 m is no height


def test_the_result_is_written_to_a_side_file_and_renamed_into_place(tmp_path, monkeypatch):
    moves = []
    real = build.os.replace
    monkeypatch.setattr(build.os, "replace", lambda src, dst: (moves.append((str(src), str(dst))), real(src, dst))[1])
    out = tmp_path / "temperature_cells.json"
    out.write_text('{"old": true}')
    build.write_json(out, {"cells": {}})
    assert json.loads(out.read_text()) == {"cells": {}}
    assert len(moves) == 1 and moves[0][1] == str(out) and moves[0][0] != str(out)
    assert moves[0][0].startswith(str(tmp_path))                          # the side file lies beside the result
    assert not list(tmp_path.glob("*.part"))


def test_the_field_meanings_do_not_say_how_many_years_the_extremes_cover():
    # The service names 2001 to 2025, but its values fit 2001 to 2020 (see years_the_climatology_fits).
    for words in (temperature.FIELD_MEANING["t2m_max_c"], temperature.FIELD_MEANING["t2m_min_c"],
                  temperature.WHAT_IT_IS_NOT):
        assert "25-year" not in words and "25 years" not in words
    assert "years_fit" in temperature.FIELD_MEANING["t2m_max_c"]         # points the reader to the check


def _days(year: int, month: int, values: list[float]) -> dict:
    return {datetime.date(year, month, day + 1): value for day, value in enumerate(values)}


def test_years_the_climatology_fits_finds_the_last_year_the_extremes_were_taken_over():
    daily_max, daily_min = {}, {}
    for year in range(2001, 2026):
        for month in range(1, 13):
            daily_max.update(_days(year, month, [10.0, 11.0 + 0.1 * (year - 2000)]))   # each year sets a new record
            daily_min.update(_days(year, month, [0.0, -5.0 - 0.1 * (year - 2000)]))
    clim_max = [13.0] * 12                                                          # the records as of 2020
    clim_min = [-7.0] * 12
    got = temperature.years_the_climatology_fits(clim_max, clim_min, daily_max, daily_min)
    by_year = got.pop("months_equal_by_end_year")
    assert got == {"first_year": 2001, "last_year_of_the_daily_series": 2025, "end_year_that_fits_best": 2020,
                   "months_compared": 24, "months_equal_at_that_end_year": 24, "months_equal_with_all_years": 0}
    assert by_year["2020"] == 24 and by_year["2019"] == 0 and by_year["2021"] == 0 and len(by_year) == 25
    through_2025 = temperature.years_the_climatology_fits([13.5] * 12, [-7.5] * 12,
                                                          daily_max, daily_min)
    assert through_2025["end_year_that_fits_best"] == 2025 and through_2025["months_equal_with_all_years"] == 24


def test_years_the_climatology_fits_is_null_without_a_row_or_a_series_and_skips_null_months():
    daily = _days(2001, 7, [20.0, 21.0])
    assert temperature.years_the_climatology_fits(None, None, daily, daily) is None
    assert temperature.years_the_climatology_fits([1.0] * 12, [1.0] * 12, {}, {}) is None
    got = temperature.years_the_climatology_fits([None] * 6 + [21.0] + [None] * 5, None, daily, daily)
    assert got["months_compared"] == 1 and got["months_equal_at_that_end_year"] == 1
    assert got["end_year_that_fits_best"] == 2001


def test_years_fit_all_adds_the_places_up_and_names_the_period_the_values_fit():
    # at the first place no record fell in 2021, so 2020 and 2021 fit it equally well; the places decide together
    one = {"first_year": 2001, "last_year_of_the_daily_series": 2025, "end_year_that_fits_best": 2021,
           "months_compared": 24, "months_equal_at_that_end_year": 24, "months_equal_with_all_years": 19,
           "months_equal_by_end_year": {"2019": 20, "2020": 24, "2021": 24, "2025": 19}}
    two = dict(one, end_year_that_fits_best=2020, months_equal_with_all_years=23,
               months_equal_by_end_year={"2019": 21, "2020": 24, "2021": 22, "2025": 23})
    got = build.years_fit_all([{"years_fit": one}, {"years_fit": two}, {"years_fit": None}, {"note": "no cell"}],
                              "2001-01-01 to 2025-12-31")
    assert got["period_named_by_the_service"] == "2001-01-01 to 2025-12-31"
    assert got["years_the_values_fit"] == "2001 to 2020" and got["places"] == 2
    assert got["months_compared"] == 48 and got["months_equal_over_the_years_that_fit"] == 48
    assert got["months_equal_over_the_period_named"] == 42
    assert got["agrees_with_the_period_named"] is False
    assert build.years_fit_all([{"years_fit": None}], "2001-01-01 to 2025-12-31") is None       # unknown stays unknown
    other = dict(two, first_year=1981)                                   # series that do not start together: no answer
    assert build.years_fit_all([{"years_fit": one}, {"years_fit": other}], "x")["years_the_values_fit"] is None


def test_the_lunar_sentence_is_filled_from_the_moon_cards_and_stays_a_placeholder_without_them():
    cards = {"cards": [
        {"diviner": {"annual_mean_temp_2cm_C": {"mean": -150.63, "min": -233.96, "max": -86.67}}},
        {"diviner": {"annual_mean_temp_2cm_C": {"mean": -129.67, "min": -219.51, "max": -71.77}}}]}
    places = [{"best_bins_any_target": [{"ten_day_mean_of_daily_series": {"t2m_c": -4.0}, "month_climatology": {}},
                                        {"ten_day_mean_of_daily_series": {"t2m_c": 10.1}, "month_climatology": {}}]}]
    filled = build.lunar_placeholder(places, cards)
    assert filled["status"] == "filled from the moon cards"
    assert "-151 to -130 C" in filled["sentence"] and "-234 C" in filled["sentence"]
    assert "model" in filled["sentence"] and "{" not in filled["sentence"]
    assert filled["lunar_mean_low_c"] == -150.6 and filled["lunar_mean_high_c"] == -129.7
    for unknown in (None, {"cards": []}, {"cards": [{"diviner": {"annual_mean_temp_2cm_C": {"mean": None, "min": None}}}]}):
        left = build.lunar_placeholder(places, unknown)
        assert left["status"].startswith("placeholder") and "{LUNAR" in left["sentence"]
        assert left["lunar_mean_low_c"] is None                         # never 0 for unknown

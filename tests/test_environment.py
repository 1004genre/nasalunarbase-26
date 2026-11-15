# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""UV, surface sunlight, clear-sky days and aerosol from NASA POWER. No test touches the network."""
from __future__ import annotations

import datetime
import io
import json
import urllib.error

import pytest

from twinfinder import cloud, environment

MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

# One grid box and the header of a real answer of the regional climatology service, asked on
# 14 November 2026 for 70 to 80 N, 10 to 20 E, ALLSKY_KT: the box of Longyearbyen, unchanged.
# January, November and December carry the fill value: there is no sunlight to be "clear".
REAL_KT_ANSWER = (
    '{"features":[{"type":"Feature","geometry":{"type":"Point","coordinates":[15.5,78.5,352.81]},'
    '"properties":{"parameter":{"ALLSKY_KT":{"JAN":-999.0,"FEB":0.36,"MAR":0.46,"APR":0.53,"MAY":0.5,'
    '"JUN":0.49,"JUL":0.46,"AUG":0.44,"SEP":0.42,"OCT":0.35,"NOV":-999.0,"DEC":-999.0,"ANN":0.48}}}}],'
    '"header":{"title":"NASA/POWER Source Native Resolution Climatology Climatologies","api":'
    '{"version":"v2.10.1","name":"POWER Climatology API"},"sources":["SYN1DEG","POWER"],'
    '"fill_value":-999.0,"time_standard":"LST","start":"20010101","end":"20251231"},'
    '"messages":["The requested parameters are retrieved from a pre-computed climatological period '
    '(January 2001 - December 2025)"],"parameters":{"ALLSKY_KT":{"units":"dimensionless",'
    '"longname":"All Sky Insolation Clearness Index"}},"type":"FeatureCollection"}'
)
# The same box, ALLSKY_SFC_UV_INDEX, same request day: polar night months are a real 0.0.
REAL_UV_MONTHS = [0.0, 0.0, 0.03, 0.2, 0.58, 0.91, 0.81, 0.41, 0.1, 0.01, 0.0, 0.0]

ERROR_ANSWER = (
    '{"header":"The POWER Climatology API failed to complete your request; please review the '
    'errors below and the POWER Docs (https://power.larc.nasa.gov/docs/).","messages":["Please '
    'provide a maximum of 10 degree range in latitude."]}'
)


def answer(boxes: dict, parameter: str, fill=-999.0, units="dimensionless", start="20010101") -> str:
    """A made-up answer in the service's layout. boxes maps (lat, lon) to 12 values."""
    features = []
    for (lat, lon), values in boxes.items():
        months = dict(zip(MONTHS, values))
        months["ANN"] = 1.0
        features.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat, 12.3]},
                         "properties": {"parameter": {parameter: months}}})
    header = {"api": {"version": "v2.10.1", "name": "POWER Climatology API"}, "sources": ["SYN1DEG"],
              "start": start, "end": "20251231", "fill_value": fill}
    return json.dumps({"features": features, "header": header,
                       "parameters": {parameter: {"units": units, "longname": "x"}}, "type": "FeatureCollection"})


# ---- the parameters ---------------------------------------------------------------------------

def test_the_fields_are_the_eight_parameters_the_service_lists_with_their_own_units():
    assert environment.FIELDS == {
        "uv_index": "ALLSKY_SFC_UV_INDEX",
        "uva_kwh_m2_day": "ALLSKY_SFC_UVA",
        "uvb_kwh_m2_day": "ALLSKY_SFC_UVB",
        "sun_kwh_m2_day": "ALLSKY_SFC_SW_DWN",
        "sun_clear_kwh_m2_day": "CLRSKY_SFC_SW_DWN",
        "clearness": "ALLSKY_KT",
        "clear_days_total": "CLRSKY_DAYS",
        "aod_550": "AOD_55_ADJ",
    }
    assert environment.PARAMETERS == tuple(environment.FIELDS.values())
    for parameter in environment.PARAMETERS:
        about = environment.ABOUT[parameter]
        assert about["what_it_is_not"] and about["field"] in environment.FIELDS
        assert environment.FIELDS[about["field"]] == parameter


# ---- reading a raw answer ---------------------------------------------------------------------

def test_read_answer_reads_a_real_answer_and_turns_the_fill_value_into_null_never_a_number():
    got = environment.read_answer(REAL_KT_ANSWER, "ALLSKY_KT")
    assert list(got) == [(78.5, 15.5)]          # latitude first, as the project keys boxes
    assert got[(78.5, 15.5)] == [None, 0.36, 0.46, 0.53, 0.5, 0.49, 0.46, 0.44, 0.42, 0.35, None, None]


def test_read_answer_keeps_a_real_zero_of_polar_night_as_zero():
    got = environment.read_answer(answer({(78.5, 15.5): REAL_UV_MONTHS}, "ALLSKY_SFC_UV_INDEX"),
                                  "ALLSKY_SFC_UV_INDEX")
    assert got[(78.5, 15.5)] == REAL_UV_MONTHS
    assert got[(78.5, 15.5)][0] == 0.0 and got[(78.5, 15.5)][0] is not None


def test_read_answer_uses_the_fill_value_the_header_names():
    got = environment.read_answer(answer({(70.5, 10.5): [-1.0] + [0.1] * 11}, "AOD_55_ADJ", fill=-1.0),
                                  "AOD_55_ADJ")
    assert got[(70.5, 10.5)][0] is None and got[(70.5, 10.5)][1] == 0.1


@pytest.mark.parametrize("parameter, bad", [("ALLSKY_SFC_UV_INDEX", 45.0), ("ALLSKY_KT", 1.4),
                                            ("CLRSKY_DAYS", 776.0), ("AOD_55_ADJ", -0.2),
                                            ("ALLSKY_SFC_SW_DWN", 14.0), ("ALLSKY_SFC_UVB", -0.1)])
def test_read_answer_refuses_a_value_the_quantity_cannot_take(parameter, bad):
    with pytest.raises(ValueError):
        environment.read_answer(answer({(70.5, 10.5): [bad] + [0.0] * 11}, parameter), parameter)


def test_read_answer_refuses_an_error_message_and_another_parameter():
    with pytest.raises(ValueError):
        environment.read_answer(ERROR_ANSWER, "ALLSKY_KT")
    with pytest.raises(ValueError):
        environment.read_answer(REAL_KT_ANSWER, "AOD_55_ADJ")


def test_answer_units_and_grid_are_read_from_the_answer_itself():
    assert environment.answer_units(REAL_KT_ANSWER, "ALLSKY_KT") == "dimensionless"
    boxes = {(lat + 0.5, lon + 0.5): [0.1] * 12 for lat in range(70, 73) for lon in range(10, 14)}
    assert environment.answer_grid(answer(boxes, "AOD_55_ADJ")) == (1.0, 1.0)
    merra = {(64.0 + 0.5 * i, -22.5 + 0.625 * j): [0.1] * 12 for i in range(3) for j in range(3)}
    assert environment.answer_grid(answer(merra, "AOD_55_ADJ")) == (0.5, 0.625)


# ---- grid boxes -------------------------------------------------------------------------------

def test_grid_box_is_the_one_degree_box_of_the_parameter_that_holds_the_area_centre():
    for parameter in environment.PARAMETERS:
        assert environment.GRID_DEG[parameter] == 1.0
        assert environment.grid_box(78.25, 15.9, parameter) == (78.5, 15.5)
        assert environment.grid_box(-77.55, 161.75, parameter) == (-77.5, 161.5)
        assert environment.grid_box(-68.45, 78.15, parameter) == cloud.grid_box(-68.45, 78.15)
    with pytest.raises(KeyError):
        environment.grid_box(78.25, 15.9, "T2M")


# ---- ten-day values ---------------------------------------------------------------------------

def test_ten_day_values_gives_36_values_each_period_taking_the_month_of_its_middle_day():
    months = [float(m) for m in range(1, 13)]
    got = environment.ten_day_values(months)
    assert len(got) == 36
    assert got[0] == got[1] == got[2] == 1.0       # 1 to 30 January
    assert got[3] == 2.0                           # 31 January to 9 February: middle day 5 February
    assert got[18] == 7.0                          # 30 June to 9 July: middle day 5 July
    assert got[35] == 12.0                         # 21 to 31 December
    for b in range(36):
        days = [d for d in range(1, 366) if min((d - 1) // 10, 35) == b]
        middle = datetime.date(2025, 1, 1) + datetime.timedelta(days=days[len(days) // 2] - 1)
        assert got[b] == float(middle.month)


def test_ten_day_values_keeps_zero_as_zero_and_null_as_null_and_refuses_a_wrong_length():
    got = environment.ten_day_values([0.0] + [None] + [0.5] * 10)
    assert got[0] == 0.0 and got[0] is not None
    assert got[3] is None and got[5] is None
    assert environment.ten_day_values(None) == [None] * 36
    with pytest.raises(ValueError):
        environment.ten_day_values([0.1] * 11)


# ---- polar night ------------------------------------------------------------------------------

def test_sunless_months_are_the_months_with_no_clear_sky_sunlight_and_unknown_is_not_sunless():
    clear_sun = [0.0, 0.0283, 1.146, 4.1, 7.4, 8.9, 7.8, 4.9, 1.9, 0.19, 0.0, 0.0]
    assert environment.sunless_months(clear_sun) == [1, 11, 12]
    assert environment.sunless_months([None] + clear_sun[1:]) == [11, 12]
    assert environment.sunless_months([5.0] * 12) == []
    assert environment.sunless_months(None) is None


# ---- the table of cells -----------------------------------------------------------------------

def test_cells_table_gives_every_field_its_box_row_and_null_for_unknown():
    cells = [{"id": "78.2_15.6", "lat": 78.25, "lon": 15.9}, {"id": "-77.6_161.5", "lat": -77.55, "lon": 161.75}]
    north = (78.5, 15.5)
    by_parameter = {parameter: {north: [0.0] + [0.2] * 10 + [0.0]} for parameter in environment.PARAMETERS}
    by_parameter["ALLSKY_KT"] = {north: [None] + [0.4] * 10 + [None]}
    table = environment.cells_table(cells, by_parameter)
    rec = table["78.2_15.6"]
    assert set(rec) == {*environment.FIELDS, "clear_days", "grid", "sunless_months"}
    assert rec["clear_days"] is None               # no number of years given: no count per month, not 0
    assert rec["uv_index"][0] == 0.0 and rec["clearness"][0] is None and rec["clearness"][1] == 0.4
    assert rec["grid"] == {"lat": 78.5, "lon": 15.5, "deg": 1.0}
    assert rec["sunless_months"] == [1, 12]
    south = table["-77.6_161.5"]                   # a box the service did not give
    assert all(south[field] is None for field in environment.FIELDS)
    assert south["sunless_months"] is None and south["grid"] == {"lat": -77.5, "lon": 161.5, "deg": 1.0}


def test_cells_table_makes_a_row_of_nothing_but_null_into_null_and_keeps_a_partial_row():
    cells = [{"id": "a", "lat": 70.2, "lon": 10.2}]
    box = (70.5, 10.5)
    by_parameter = {parameter: {box: [None] * 12} for parameter in environment.PARAMETERS}
    by_parameter["AOD_55_ADJ"] = {box: [None] * 6 + [0.1] * 6}
    rec = environment.cells_table(cells, by_parameter)["a"]
    assert rec["uv_index"] is None
    assert rec["aod_550"] == [None] * 6 + [0.1] * 6


# ---- fetching ---------------------------------------------------------------------------------

class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_fetch_tile_asks_once_with_the_project_user_agent_and_then_reads_from_disk(tmp_path):
    asked = []

    def opener(request, timeout):
        asked.append(request)
        return FakeResponse(REAL_KT_ANSWER.encode())

    tile = (70, 80, 10, 20)
    path, did = environment.fetch_tile("ALLSKY_KT", tile, tmp_path, opener=opener, sleep=lambda s: None)
    assert did and path.name == "ALLSKY_KT_N70_N80_E010_E020.json" and path.read_text() == REAL_KT_ANSWER
    assert asked[0].get_header("User-agent") == "twinfinder/0.1"
    assert "parameters=ALLSKY_KT" in asked[0].full_url and "power.larc.nasa.gov" in asked[0].full_url
    path2, did2 = environment.fetch_tile("ALLSKY_KT", tile, tmp_path, opener=opener, sleep=lambda s: None)
    assert path2 == path and not did2 and len(asked) == 1
    assert not list(tmp_path.glob("*.part"))


def test_fetch_tile_waits_on_too_many_requests_and_keeps_nothing_that_is_not_an_answer(tmp_path):
    calls = []

    def busy_then_error(request, timeout):
        calls.append(1)
        if len(calls) == 1:
            raise urllib.error.HTTPError(request.full_url, 429, "Too Many Requests", {}, None)
        return FakeResponse(ERROR_ANSWER.encode())

    with pytest.raises(ValueError):
        environment.fetch_tile("ALLSKY_KT", (70, 80, 10, 20), tmp_path, opener=busy_then_error, sleep=lambda s: None)
    assert len(calls) == 2 and not list(tmp_path.iterdir())


# ---- the period and the meaning of a daily value: checks against the service's daily and hourly series ----

def test_read_series_reads_daily_and_hourly_keys_and_turns_fill_into_null():
    raw = json.dumps({"header": {"fill_value": -999.0},
                      "properties": {"parameter": {"ALLSKY_SFC_UV_INDEX": {"2020060100": 0.2, "2020060112": 2.0,
                                                                           "2020060200": -999.0}}}})
    got = environment.read_series(raw, "ALLSKY_SFC_UV_INDEX")
    assert got == {"2020060100": 0.2, "2020060112": 2.0, "2020060200": None}


def test_hours_to_days_gives_the_mean_and_the_highest_hour_of_each_day_without_unknown_hours():
    series = {"2020060100": 0.0, "2020060106": 1.0, "2020060112": 2.0, "2020060118": None,
              "2020060200": None}
    got = environment.hours_to_days(series)
    assert got["20200601"] == {"mean": 1.0, "max": 2.0, "hours": 3}
    assert got["20200602"] == {"mean": None, "max": None, "hours": 0}


def test_monthly_climatology_of_a_daily_series_over_chosen_years_means_or_counts():
    series = {}
    for year in (2001, 2002, 2003):
        for day in range(1, 32):
            series[f"{year}01{day:02d}"] = float(year - 2000)    # 1, 2, 3
        series[f"{year}0201"] = None
    means = environment.monthly_climatology(series, 2001, 2002)
    assert means[0] == pytest.approx(1.5) and means[1] is None and means[5] is None
    clear = {f"2001{m:02d}01": 1.0 for m in range(1, 13)} | {"20010102": 1.0, "20020101": 0.0, "20020102": 0.0}
    counts = environment.monthly_climatology(clear, 2001, 2002, how="sum")
    assert counts[0] == pytest.approx(1.0)        # 2 clear days in 2001, 0 in 2002
    assert counts[1] == pytest.approx(1.0)        # February of 2002 has no day in the series: 1 year only


# ---- the build script, offline, on a made-up block ---------------------------------------------------

import importlib  # noqa: E402
import sys  # noqa: E402

build = importlib.import_module("scripts.build_environment_cells")

UNITS = {"ALLSKY_SFC_UV_INDEX": "W m-2 x 40", "ALLSKY_SFC_UVA": "kW-hr/m^2/day", "ALLSKY_SFC_UVB": "kW-hr/m^2/day",
         "ALLSKY_SFC_SW_DWN": "kW-hr/m^2/day", "CLRSKY_SFC_SW_DWN": "kW-hr/m^2/day", "ALLSKY_KT": "dimensionless",
         "CLRSKY_DAYS": "Days", "AOD_55_ADJ": "dimensionless"}


def _offline_run(tmp_path, monkeypatch, units=UNITS, argv=("--offline", "--no-checks")):
    raw = tmp_path / "raw"
    (raw / "parameters").mkdir(parents=True)
    sun_row = [0.0, 0.02, 0.8, 3.0, 5.1, 6.0, 5.1, 3.2, 1.2, 0.13, 0.0, 0.0]
    rows = {"ALLSKY_SFC_UV_INDEX": REAL_UV_MONTHS, "ALLSKY_SFC_UVA": [v / 16 for v in sun_row],
            "ALLSKY_SFC_UVB": [v / 1400 for v in sun_row], "ALLSKY_SFC_SW_DWN": sun_row,
            "CLRSKY_SFC_SW_DWN": [v * 1.4 for v in sun_row],
            "ALLSKY_KT": [-999.0, 0.36, 0.46, 0.53, 0.5, 0.49, 0.46, 0.44, 0.42, 0.35, -999.0, -999.0],
            "CLRSKY_DAYS": [0.0, 0.0, 0.0, 2.0, 4.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            "AOD_55_ADJ": [0.01, 0.02, 0.01, 0.04, 0.09, 0.11, 0.15, 0.12, 0.05, 0.02, 0.01, 0.01]}
    for parameter, values in rows.items():
        boxes = {(78.5, 15.5): values, (78.5, 16.5): [-999.0] * 12, (77.5, 15.5): values}
        (raw / cloud.raw_name(parameter, (70, 80, 10, 20))).write_text(answer(boxes, parameter, units=units[parameter]))
    listing = {p: {"name": p.title(), "definition": f"definition of {p}", "units": UNITS[p], "source": "SOURCE"}
               for p in environment.PARAMETERS}
    (raw / "parameters" / "list.json").write_text(json.dumps(listing))
    cells = {"meta": {"summer_bins_south": [33, 34, 35, 0, 1, 2, 3, 4, 5], "summer_bins_north": list(range(9, 27))},
             "cells": [{"id": "78.2_15.6", "lat": 78.25, "lon": 15.9, "hemisphere": "N",
                        "targets": {"malapert": {"top_bins": [[23, 4.2], [24, 3.7]]}}},
                       {"id": "78.7_16.6", "lat": 78.75, "lon": 16.6, "hemisphere": "N",
                        "targets": {"malapert": {"top_bins": []}}}]}
    (tmp_path / "grazing_cells.json").write_text(json.dumps(cells))
    out = tmp_path / "environment_cells.json"
    for name, value in (("CELLS", tmp_path / "grazing_cells.json"), ("MOON", tmp_path / "moon_cards.json"),
                        ("RAW", raw), ("POINTS", raw / "points"), ("LISTING", raw / "parameters" / "list.json"),
                        ("LOG", raw / "fetch_log.jsonl"), ("OUT", out),
                        ("PLACES", [("Longyearbyen", "78.2_15.6", None, None)])):
        monkeypatch.setattr(build, name, value)
    monkeypatch.setattr(sys, "argv", ["build_environment_cells.py", *argv])
    build.main()
    return out


def test_build_script_offline_writes_every_area_with_null_for_unknown_and_the_service_words(tmp_path, monkeypatch,
                                                                                           capsys):
    out = _offline_run(tmp_path, monkeypatch)
    capsys.readouterr()
    written = json.loads(out.read_text())
    assert set(written) == {"meta", "cells"} and not list(tmp_path.glob("*.part"))
    rec = written["cells"]["78.2_15.6"]
    assert rec["uv_index"] == REAL_UV_MONTHS and rec["clearness"][0] is None and rec["clear_days_total"][4] == 4.0
    assert rec["clear_days"] is None               # --no-checks: the years behind the total are not known
    assert rec["grid"] == {"lat": 78.5, "lon": 15.5, "deg": 1.0} and rec["sunless_months"] == [1, 11, 12]
    empty = written["cells"]["78.7_16.6"]                  # its box holds nothing but the fill value
    assert all(empty[field] is None for field in environment.FIELDS) and empty["sunless_months"] is None
    meta = written["meta"]
    for parameter in environment.PARAMETERS:
        about = meta["parameters"][parameter]
        assert about["unit"] == UNITS[parameter] and about["definition_in_the_service"] == f"definition of {parameter}"
        assert about["what_it_is_not"] and about["period_named_by_the_service"] == "2001-01-01 to 2025-12-31"
        assert about["grid"].startswith("1 x 1 degree")
    facts = meta["polar_night"]["facts"]
    # one box with three dark months; the box of nothing but fill is unknown, not dark
    assert facts["box_months_without_sunlight"] == 3
    assert facts["ALLSKY_KT"] == {"zero": 0, "null": 3, "other": 0, "largest_other": None}
    assert facts["ALLSKY_SFC_UV_INDEX"]["zero"] == 3 and facts["CLRSKY_DAYS"]["zero"] == 3
    place = meta["named_places"]["places"][0]
    assert [b["bin"] for b in place["best_bins"]] == [23, 24]
    assert place["best_bins"][0]["values"]["uv_index"] == REAL_UV_MONTHS[7]     # bin 23: 18 to 27 August
    assert "not in our data" in meta["lunar_comparison"]["dust"]


def test_build_script_stops_when_an_answer_names_another_unit_than_the_parameter_list(tmp_path, monkeypatch):
    with pytest.raises(SystemExit):
        _offline_run(tmp_path, monkeypatch, units=UNITS | {"ALLSKY_SFC_UVA": "W/m^2"})


# ---- clear-sky days: the service's figure is a count over all the years, not days in a typical month ----

def test_read_answer_takes_a_clear_day_count_above_31_because_it_is_a_total_over_the_years():
    # 355 is what the service gave for January at 79.5 S, 30.5 E on 14 November 2026
    got = environment.read_answer(answer({(-79.5, 30.5): [355.0] + [0.0] * 11}, "CLRSKY_DAYS"), "CLRSKY_DAYS")
    assert got[(-79.5, 30.5)][0] == 355.0


def test_clear_days_per_year_divides_the_total_by_the_years_and_is_null_without_them():
    total = [355.0, 120.0, 0.0, None] + [0.0] * 8
    got = environment.clear_days_per_year(total, 20)
    assert got[:4] == [17.75, 6.0, 0.0, None]
    assert environment.clear_days_per_year(total, None) is None
    assert environment.clear_days_per_year(None, 20) is None


def test_cells_table_gives_clear_days_per_month_when_the_years_are_known():
    cells = [{"id": "a", "lat": 70.2, "lon": 10.2}]
    box = (70.5, 10.5)
    by_parameter = {parameter: {box: [1.0] * 12} for parameter in environment.PARAMETERS}
    by_parameter["CLRSKY_DAYS"] = {box: [50.0] * 12}
    rec = environment.cells_table(cells, by_parameter, clear_day_years=25)["a"]
    assert rec["clear_days_total"] == [50.0] * 12 and rec["clear_days"] == [2.0] * 12


def test_monthly_climatology_total_adds_every_known_day_of_the_month_over_the_years():
    series = {"20010101": 1.0, "20010102": 0.0, "20020101": 1.0, "20030101": 1.0, "20010201": None}
    got = environment.monthly_climatology(series, 2001, 2002, how="total")
    assert got[0] == 2.0 and got[1] is None and got[2] is None


def test_clear_day_years_takes_the_period_whose_totals_equal_the_climatology_best_and_else_none():
    def point(gap_20, gap_25):
        return {"by_parameter": {"CLRSKY_DAYS": {"2001-2020": {"mean_abs_difference": gap_20},
                                                 "2001-2025": {"mean_abs_difference": gap_25}}}}
    checks = {"period": {"points": [point(0.0, 0.083), point(0.0, 70.2), point(0.0, 41.5)]}}
    got = build.clear_day_years(checks)
    assert got["years"] == 20 and got["period"] == "2001-2020"
    assert build.clear_day_years({"period": {"points": [point(3.0, 4.0)]}})["years"] is None
    assert build.clear_day_years({"period": {"points": [point(0.0, 0.0)]}})["years"] is None
    assert build.clear_day_years(None)["years"] is None


# ---- words (added by ENV-CHECK): sentences of 25 words or fewer, the aerosol parameters named right ----

import re  # noqa: E402
from pathlib import Path  # noqa: E402

DERIVED = Path(__file__).resolve().parents[1] / "data" / "derived"


def test_long_sentences_finds_a_sentence_over_25_words_and_skips_the_services_own_words():
    long = "one " * 26
    doc = {"a": "Short. " + long.strip() + ".", "definition_in_the_service": long, "url": long,
           "b": ["fine", {"c": long}], "source": long}
    found = list(environment.long_sentences(doc))
    assert [path for path, _ in found] == [".a", ".b[1].c"]
    assert list(environment.long_sentences({"a": "A short one. Another short one."})) == []


def test_what_each_parameter_is_and_is_not_is_said_in_sentences_of_25_words_or_fewer():
    assert list(environment.long_sentences(environment.ABOUT)) == []


def test_the_dust_note_names_every_aerosol_parameter_in_the_list_not_only_the_one_used():
    listing = {"AOD_55": {"name": "Aerosol Optical Depth 55", "definition": "The optical thickness at 0.55 um."},
               "AOD_55_ADJ": {"name": "Adjusted Aerosol Optical Depth 55", "definition": "The adjusted optical thickness."},
               "AOD_84": {"name": "Aerosol Optical Depth 84", "definition": "The optical thickness at 0.84 um."},
               "CLOUD_AMT": {"name": "Cloud Amount", "definition": "The average percent of cloud amount."}}
    words = build.dust_only_figure(listing)
    for name in ("AOD_55", "AOD_55_ADJ", "AOD_84"):
        assert name in words
    assert "CLOUD_AMT" not in words and "only aerosol" not in words
    assert list(environment.long_sentences({"w": words})) == []


def test_the_build_scripts_own_sentences_are_25_words_or_fewer_with_checks_and_lunar_cards(tmp_path, monkeypatch,
                                                                                          capsys):
    cards = {"cards": [{"id": t, "lit": {"mean_share": 0.3}, "sun_ceiling": {"deg": d},
                        "earth_cannot_match": [{"what": "vacuum", "number": 3e-15},
                                               {"what": "dust", "moon": "Sharp-grained regolith that clings to gear."}]}
                       for t, d in (("connecting-ridge", 2.08), ("malapert", 5.55))]}
    (tmp_path / "moon_cards.json").write_text(json.dumps(cards))
    out = _offline_run(tmp_path, monkeypatch, argv=["--offline"])
    capsys.readouterr()
    meta = json.loads(out.read_text())["meta"]
    assert meta["checks"] is not None
    assert list(environment.long_sentences(meta)) == []


def test_the_real_file_says_everything_in_sentences_of_25_words_or_fewer():
    path = DERIVED / "environment_cells.json"
    if not path.exists():
        pytest.skip("data/derived/environment_cells.json not built")
    meta = json.loads(path.read_text())["meta"]
    assert list(environment.long_sentences(meta)) == []


# ---- added by ENV-CHECK for breakages the tests above did not catch ----

def test_read_answer_wraps_a_longitude_past_180_to_the_west():
    got = environment.read_answer(answer({(70.5, 190.5): [1.0] * 12}, "AOD_55_ADJ"), "AOD_55_ADJ")
    assert list(got) == [(70.5, -169.5)]


def test_the_dust_note_names_an_aod_parameter_even_when_its_name_lacks_the_word_aerosol():
    words = build.dust_only_figure({"AOD_99": {"name": "Optical Depth 99", "definition": "The optical thickness."}})
    assert "AOD_99" in words

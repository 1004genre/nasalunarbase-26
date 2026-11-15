# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Daily temperature range, surface albedo and top-soil wetness from NASA POWER
(scripts/build_power_extra.py). No test touches the network."""
from __future__ import annotations

import datetime
import importlib
import io
import json
import math
import urllib.error
from pathlib import Path

import pytest

build = importlib.import_module("scripts.build_power_extra")

MONTHS = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")
UNITS = {"T2M_RANGE": "C", "ALLSKY_SRF_ALB": "dimensionless", "GWETTOP": "1"}
SOURCES = {"T2M_RANGE": ["MERRA2", "POWER"], "ALLSKY_SRF_ALB": ["SYN1DEG", "POWER"], "GWETTOP": ["MERRA2"]}


def answer(parameter: str, points, units: str | None = None, sources=None, start="20010101", end="20251231",
           version="v2.10.1", fill=-999.0) -> bytes:
    """A regional climatology answer laid out like the real one.

    points: [(lat, lon, [12 monthly values], annual value)].
    """
    features = []
    for lat, lon, months, ann in points:
        values = dict(zip(MONTHS, months))
        values["ANN"] = ann
        features.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat, 100.0]},
                         "properties": {"parameter": {parameter: values}}})
    return json.dumps({
        "type": "FeatureCollection",
        "features": features,
        "header": {"title": "NASA/POWER Source Native Resolution Climatology Climatologies",
                   "api": {"version": version, "name": "POWER Climatology API"},
                   "sources": sources if sources is not None else SOURCES[parameter],
                   "fill_value": fill, "time_standard": "LST", "start": start, "end": end},
        "messages": ["The requested parameters are retrieved from a pre-computed climatological period "
                     "(January 2001 - December 2025)"],
        "parameters": {parameter: {"units": units if units is not None else UNITS[parameter],
                                   "longname": parameter}},
        "times": {"data": 0.1, "process": 0.1},
    }).encode()


# ---- reading an answer -------------------------------------------------------------------------------

def test_read_answer_turns_the_fill_value_into_none_and_keeps_a_real_zero():
    months = [-999.0, 0.43, 0.66, 0.74, 0.72, 0.54, 0.25, 0.18, 0.29, 0.4, 0.0, -999.0]
    rows = build.read_answer(answer("ALLSKY_SRF_ALB", [(75.5, -89.5, months, 0.46)]), "ALLSKY_SRF_ALB")
    values, ann = rows[(75.5, -89.5)]
    assert values[0] is None and values[11] is None
    assert values[10] == 0.0 and values[10] is not None
    assert values[1] == 0.43
    assert ann == 0.46


def test_read_answer_annual_fill_is_none():
    rows = build.read_answer(answer("GWETTOP", [(-77.5, 161.25, [-999.0] * 12, -999.0)]), "GWETTOP")
    assert rows[(-77.5, 161.25)] == ([None] * 12, None)


def test_read_answer_wraps_longitude_180_to_minus_180():
    rows = build.read_answer(answer("T2M_RANGE", [(80.0, 180.0, [5.0] * 12, 5.0)]), "T2M_RANGE")
    assert (80.0, -180.0) in rows


@pytest.mark.parametrize("parameter, bad", [("T2M_RANGE", -0.5), ("T2M_RANGE", 75.0),
                                            ("ALLSKY_SRF_ALB", 1.2), ("GWETTOP", -0.1), ("GWETTOP", 1.5)])
def test_read_answer_rejects_values_out_of_range(parameter, bad):
    months = [0.5] * 12
    months[3] = bad
    with pytest.raises(ValueError, match="out of range"):
        build.read_answer(answer(parameter, [(70.0, 10.0, months, 0.5)]), parameter)


def test_read_answer_rejects_unexpected_units():
    with pytest.raises(ValueError, match="units"):
        build.read_answer(answer("T2M_RANGE", [(70.0, 10.0, [5.0] * 12, 5.0)], units="K"), "T2M_RANGE")


def test_read_answer_rejects_an_error_message():
    body = json.dumps({"messages": ["Parameter not found"], "header": {}}).encode()
    with pytest.raises(ValueError, match="not a regional climatology answer"):
        build.read_answer(body, "GWETTOP")


def test_read_answer_rejects_an_answer_for_another_parameter():
    with pytest.raises(ValueError):
        build.read_answer(answer("GWETTOP", [(70.0, 10.0, [0.5] * 12, 0.5)]), "T2M_RANGE")


def test_read_answer_rejects_a_text_value():
    months: list = [0.5] * 12
    months[0] = "wet"
    with pytest.raises(ValueError, match="not a number"):
        build.read_answer(answer("GWETTOP", [(70.0, 10.0, months, 0.5)]), "GWETTOP")


# ---- grids and request blocks ------------------------------------------------------------------------

def test_merra2_parameters_use_the_nearest_merra2_point_and_albedo_the_one_degree_box():
    assert build.grid_key("T2M_RANGE", 63.85, -22.5) == (64.0, -22.5)
    assert build.grid_key("GWETTOP", 63.85, -22.5) == (64.0, -22.5)
    assert build.grid_key("ALLSKY_SRF_ALB", 63.85, -22.5) == (63.5, -22.5)
    assert build.grid_key("ALLSKY_SRF_ALB", -77.55, 161.75) == (-77.5, 161.5)


def test_tiles_cover_the_grid_point_across_the_date_line():
    places = [{"id": "a", "lat": 70.2, "lon": 179.9}]
    tiles = build.tiles_for(places)
    assert (70, 80, 170, 180) in tiles          # the 1 degree box 70.5, 179.5 and the cell itself
    assert (70, 80, -180, -170) in tiles        # the MERRA-2 point at -180


def test_fetch_jobs_put_the_moon_blocks_first_and_never_ask_a_block_twice():
    moon = [(60, 70, 0, 10), (70, 80, 0, 10)]
    mars = [(70, 80, 0, 10), (20, 30, 40, 50)]
    jobs = build.fetch_jobs(moon, mars)
    params = build.PARAMETERS
    assert len(jobs) == 3 * len(params)
    assert jobs[: 2 * len(params)] == [(p, t, "moon") for t in moon for p in params]
    assert jobs[2 * len(params):] == [(p, (20, 30, 40, 50), "mars") for p in params]


# ---- fetching ------------------------------------------------------------------------------------------

class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("https://power.larc.nasa.gov/x", code, "refused", {}, None)


class Opener:
    """Plays back a list of outcomes: bytes for an answer, an exception to raise."""

    def __init__(self, *outcomes):
        self.outcomes = list(outcomes)
        self.requests = []

    def __call__(self, request, timeout=None):
        self.requests.append(request)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return FakeResponse(outcome)


GOOD = answer("GWETTOP", [(70.0, 10.0, [0.5] * 12, 0.5)])
TILE = (70, 80, 10, 20)


def test_fetch_one_keeps_the_answer_with_our_user_agent(tmp_path):
    opener = Opener(GOOD)
    path, asked = build.fetch_one("GWETTOP", TILE, tmp_path, opener=opener, sleep=lambda s: None)
    assert asked is True
    assert path == tmp_path / "GWETTOP_N70_N80_E010_E020.json"
    assert path.read_bytes() == GOOD
    request = opener.requests[0]
    assert request.get_header("User-agent") == "twinfinder/0.1"
    assert "parameters=GWETTOP" in request.full_url and "latitude-min=70" in request.full_url
    assert not list(tmp_path.glob("*.part"))


def test_fetch_one_asks_nothing_when_the_answer_is_on_disk(tmp_path):
    (tmp_path / "GWETTOP_N70_N80_E010_E020.json").write_bytes(GOOD)
    opener = Opener()
    path, asked = build.fetch_one("GWETTOP", TILE, tmp_path, opener=opener, sleep=lambda s: None)
    assert asked is False and opener.requests == []


def test_fetch_one_backs_off_a_full_minute_on_a_refusal(tmp_path):
    waits = []
    opener = Opener(http_error(429), http_error(503), GOOD)
    path, asked = build.fetch_one("GWETTOP", TILE, tmp_path, opener=opener, sleep=waits.append)
    assert asked and path.exists()
    assert len(waits) == 2 and all(w >= 60.0 for w in waits)


def test_fetch_one_stops_at_once_when_a_login_is_asked_for(tmp_path):
    opener = Opener(http_error(403))
    with pytest.raises(build.LoginRequired):
        build.fetch_one("GWETTOP", TILE, tmp_path, opener=opener, sleep=lambda s: None)
    assert len(opener.requests) == 1
    assert not list(tmp_path.iterdir())


def test_fetch_one_waits_and_tries_again_when_the_network_drops(tmp_path):
    waits = []
    opener = Opener(urllib.error.URLError("no route"), ConnectionResetError("reset"), GOOD)
    path, asked = build.fetch_one("GWETTOP", TILE, tmp_path, opener=opener, sleep=waits.append)
    assert asked and path.exists()
    assert len(waits) == 2 and waits[0] >= 15.0 and waits[1] > waits[0]


def test_fetch_one_does_not_keep_a_body_that_is_not_an_answer(tmp_path):
    opener = Opener(json.dumps({"messages": ["oops"], "header": {}}).encode())
    with pytest.raises(ValueError):
        build.fetch_one("GWETTOP", TILE, tmp_path, opener=opener, sleep=lambda s: None)
    assert not list(tmp_path.iterdir())


def test_pacer_keeps_requests_at_least_one_and_a_half_seconds_apart():
    now = [100.0]
    waits = []

    def sleep(s):
        waits.append(s)
        now[0] += s

    pacer = build.Pacer(1.5, clock=lambda: now[0], sleep=sleep)
    pacer.wait()                 # first request: no wait
    now[0] += 0.4                # the request took 0.4 s
    pacer.wait()
    assert waits == [pytest.approx(1.1)]
    now[0] += 3.0
    pacer.wait()                 # already 3 s later: no wait
    assert len(waits) == 1


def test_fetch_all_logs_each_request_and_goes_on_past_a_block_that_fails(tmp_path):
    good = {p: answer(p, [(70.0, 10.0, [0.5] * 12, 0.5)]) for p in build.PARAMETERS}
    jobs = [(p, TILE, "moon") for p in build.PARAMETERS]

    def fake_fetch(parameter, tile, raw_dir, opener=None, sleep=None):
        if parameter == "ALLSKY_SRF_ALB":
            raise urllib.error.URLError("network down")
        dest = Path(raw_dir) / build.cloud.raw_name(parameter, tile)
        dest.write_bytes(good[parameter])
        return dest, True

    log = tmp_path / "fetch_log.jsonl"
    result = build.fetch_all(jobs, tmp_path, log, pacer=build.Pacer(0.0, sleep=lambda s: None),
                             fetch=fake_fetch, sleep=lambda s: None, rounds=2)
    assert result["asked"] == 2
    assert result["failed"] == [("ALLSKY_SRF_ALB", TILE, "moon")]
    lines = [json.loads(line) for line in log.read_text().splitlines()]
    assert {line["file"] for line in lines if "bytes" in line} == {
        "T2M_RANGE_N70_N80_E010_E020.json", "GWETTOP_N70_N80_E010_E020.json"}
    assert any(line.get("error") for line in lines)


def test_fetch_all_stops_on_a_login_request(tmp_path):
    jobs = [(p, TILE, "moon") for p in build.PARAMETERS]

    def fake_fetch(parameter, tile, raw_dir, opener=None, sleep=None):
        raise build.LoginRequired("403")

    with pytest.raises(build.LoginRequired):
        build.fetch_all(jobs, tmp_path, tmp_path / "log.jsonl", pacer=build.Pacer(0.0, sleep=lambda s: None),
                        fetch=fake_fetch, sleep=lambda s: None)


# ---- the table of places --------------------------------------------------------------------------------

def by_param():
    return {
        "T2M_RANGE": {(64.0, -22.5): ([4.0] * 12, 4.0)},
        "ALLSKY_SRF_ALB": {(63.5, -22.5): ([None, 0.5, 0.4, 0.3, 0.2, 0.1, 0.1, 0.1, 0.2, 0.3, 0.5, None], 0.27)},
        "GWETTOP": {(64.0, -22.5): ([None] * 12, None)},
    }


def test_place_record_holds_twelve_months_and_the_year_with_null_for_unknown():
    record = build.place_record(63.85, -22.5, by_param())
    assert record["t2m_range_c"] == [4.0] * 12 and record["t2m_range_c_year"] == 4.0
    assert record["albedo"][0] is None and record["albedo"][1] == 0.5 and len(record["albedo"]) == 12
    assert record["albedo_year"] == 0.27
    assert record["soil_wetness_top"] is None and record["soil_wetness_top_year"] is None
    assert record["grid_merra2"] == [64.0, -22.5] and record["grid_ceres"] == [63.5, -22.5]


def test_place_record_is_null_not_zero_where_the_service_gave_no_point():
    record = build.place_record(10.25, 10.25, by_param())
    for field in ("t2m_range_c", "albedo", "soil_wetness_top"):
        assert record[field] is None and record[field + "_year"] is None


def test_places_table_is_keyed_by_id():
    table = build.places_table([{"id": "63.8_-22.6", "lat": 63.85, "lon": -22.5}], by_param())
    assert list(table) == ["63.8_-22.6"]


def test_annual_check_counts_rows_whose_annual_value_is_not_the_mean_of_known_months():
    rows = {(1.0, 1.0): ([1.0] * 6 + [None] * 6, 1.0),        # equal
            (2.0, 2.0): ([1.0] * 11 + [2.0], 1.08),             # 13/12 = 1.0833: equal within rounding
            (3.0, 3.0): ([1.0] * 12, 1.5),                      # not equal
            (4.0, 4.0): ([None] * 12, None)}                    # nothing to compare
    check = build.annual_check(rows)
    assert check == {"rows_compared": 3, "rows_equal_within_0.006": 2, "largest_gap": 0.5}


# ---- what the daily range is: a check against daily series ------------------------------------------------

def test_mean_daily_range_by_month_over_chosen_years():
    days = {}
    for year in (2001, 2002, 2021):
        for day in (1, 2):
            days[datetime.date(year, 7, day)] = (10.0 + day, 2.0)       # ranges 9 and 10
    days[datetime.date(2002, 1, 5)] = (0.0, -6.0)                        # range 6
    days[datetime.date(2002, 1, 6)] = (None, -6.0)                       # a missing day is left out
    highs = {d: v[0] for d, v in days.items()}
    lows = {d: v[1] for d, v in days.items()}
    out = build.mean_daily_range(highs, lows, last_year=2020)
    assert out[6] == pytest.approx(9.5)
    assert out[0] == pytest.approx(6.0)
    assert out[1] is None
    assert len(out) == 12


# ---- writing -----------------------------------------------------------------------------------------

def test_write_json_goes_through_a_side_file_and_refuses_nan(tmp_path):
    path = tmp_path / "out.json"
    build.write_json(path, {"a": [1, None]})
    assert json.loads(path.read_text()) == {"a": [1, None]}
    assert not list(tmp_path.glob("*.part"))
    with pytest.raises(ValueError):
        build.write_json(path, {"a": math.nan})
    assert json.loads(path.read_text()) == {"a": [1, None]}


def test_headers_must_agree():
    heads = [build.cloud.answer_header(answer("GWETTOP", [(70.0, 10.0, [0.5] * 12, 0.5)])),
             build.cloud.answer_header(answer("GWETTOP", [(70.0, 10.0, [0.5] * 12, 0.5)], end="20201231"))]
    with pytest.raises(ValueError, match="disagree"):
        build.agreed_header(heads)
    one = build.agreed_header(heads[:1])
    assert one["sources"] == ["MERRA2"] and one["start"] == "20010101"


def test_meta_says_what_each_figure_is_and_is_not():
    heads = {p: build.cloud.answer_header(answer(p, [(70.0, 10.0, [0.5] * 12, 0.5)])) for p in build.PARAMETERS}
    definitions = {p: {"name": f"name of {p}", "definition": f"definition of {p}", "units": UNITS[p],
                       "type": "X", "source_in_list": "POWER"} for p in build.PARAMETERS}
    meta = build.fields_meta(heads, definitions)
    assert set(meta) == {"t2m_range_c", "albedo", "soil_wetness_top"}
    for field, info in meta.items():
        for key in ("parameter", "service_name", "service_definition", "units", "sources_named_by_service",
                    "grid", "what_it_is", "what_it_is_not", "year_field"):
            assert info[key], (field, key)
    assert "snow" in meta["albedo"]["what_it_is"]
    assert "grid box" in meta["albedo"]["what_it_is"]
    assert "model" in meta["soil_wetness_top"]["what_it_is"] and "0" in meta["soil_wetness_top"]["what_it_is"]
    assert "not a measurement" in meta["soil_wetness_top"]["what_it_is_not"].lower()
    assert "not a measurement" in meta["t2m_range_c"]["what_it_is_not"].lower()
    assert "NASA" in build.CREDIT and "POWER" in build.CREDIT

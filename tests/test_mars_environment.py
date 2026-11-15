"""Mars part, environment side: UV, surface sunlight, clear-sky days and haze for every ranked square.
No test touches the network."""
from __future__ import annotations

import importlib
import io
import json
import urllib.error

import pytest

ENV = importlib.import_module("scripts.build_mars_environment")

MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]


def answer(parameter, points, units=None, sources=("SYN1DEG",), fill=-999.0):
    """A regional climatology answer: points is {(lat, lon): [12 values] + [annual]}."""
    units = units or ENV.UNITS[parameter]
    features = []
    for (lat, lon), values in points.items():
        months = dict(zip(MONTHS + ["ANN"], values))
        features.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat, 100.0]},
                         "properties": {"parameter": {parameter: months}}})
    return json.dumps({
        "type": "FeatureCollection", "features": features,
        "header": {"api": {"version": "v2.10.1", "name": "POWER Climatology API"}, "sources": list(sources),
                   "fill_value": fill, "start": "20010101", "end": "20251231"},
        "messages": ["from a pre-computed climatological period"],
        "parameters": {parameter: {"units": units, "longname": "x"}},
    }).encode()


# ---- reading a raw answer ---------------------------------------------------------------------------

def test_read_answer_gives_months_and_the_annual_value_by_one_degree_box():
    raw = answer("ALLSKY_SFC_SW_DWN", {(-24.5, -69.5): [8.2] * 12 + [6.0]})
    out = ENV.read_answer(raw, "ALLSKY_SFC_SW_DWN")
    assert out == {(-24.5, -69.5): ([8.2] * 12, 6.0)}


def test_fill_value_becomes_none_and_a_real_zero_stays_zero():
    raw = answer("CLRSKY_DAYS", {(-24.5, -70.5): [0.0] * 11 + [-999.0] + [0.0]})
    months, year = ENV.read_answer(raw, "CLRSKY_DAYS")[(-24.5, -70.5)]
    assert months[:11] == [0.0] * 11
    assert months[11] is None
    assert year == 0.0


def test_wrong_units_are_refused():
    raw = answer("ALLSKY_SFC_SW_DWN", {(0.5, 0.5): [5.0] * 13}, units="MJ/m^2/day")
    with pytest.raises(ValueError, match="units"):
        ENV.read_answer(raw, "ALLSKY_SFC_SW_DWN")


def test_a_value_out_of_range_is_refused():
    raw = answer("AOD_55", {(0.5, 0.5): [0.1] * 11 + [12.0] + [0.1]})
    with pytest.raises(ValueError, match="out of range"):
        ENV.read_answer(raw, "AOD_55")


def test_an_answer_off_the_one_degree_grid_is_refused():
    raw = answer("AOD_55", {(0.25, 0.3125): [0.1] * 13})
    with pytest.raises(ValueError, match="grid"):
        ENV.read_answer(raw, "AOD_55")


def test_an_error_message_is_not_an_answer():
    with pytest.raises(ValueError):
        ENV.read_answer(json.dumps({"messages": ["Rate limit"], "header": {}}).encode(), "AOD_55")


def test_an_answer_for_another_parameter_is_refused():
    raw = answer("AOD_55", {(0.5, 0.5): [0.1] * 13})
    with pytest.raises(ValueError):
        ENV.read_answer(raw, "ALLSKY_SFC_UV_INDEX")


def test_longitude_past_180_is_wrapped():
    raw = answer("AOD_55", {(0.5, 180.5): [0.1] * 13})
    assert list(ENV.read_answer(raw, "AOD_55")) == [(0.5, -179.5)]


# ---- what to ask for, in which order ---------------------------------------------------------------

def test_wanted_puts_every_parameter_of_the_ranked_blocks_first_in_priority_order():
    ranked = [(0, 10, 0, 10)]
    land = [(0, 10, 0, 10), (10, 20, 0, 10)]
    order = ENV.wanted(ranked, land, ("A", "B"))
    assert order == [("A", (0, 10, 0, 10)), ("B", (0, 10, 0, 10)), ("A", (10, 20, 0, 10)), ("B", (10, 20, 0, 10))]


def test_the_priority_order_is_the_jobs():
    assert ENV.PARAMETERS[:4] == ("ALLSKY_SFC_SW_DWN", "ALLSKY_SFC_UV_INDEX", "AOD_55", "CLRSKY_DAYS")


# ---- fetching ----------------------------------------------------------------------------------------

class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_fetch_asks_nothing_for_an_answer_on_disk(tmp_path):
    tile = (0, 10, 0, 10)
    (tmp_path / ENV.raw_name("AOD_55", tile)).write_bytes(answer("AOD_55", {(0.5, 0.5): [0.1] * 13}))

    def opener(*args, **kwargs):
        raise AssertionError("asked the service for an answer that is on disk")

    path, asked = ENV.fetch_one("AOD_55", tile, tmp_path, opener=opener, sleep=lambda s: None)
    assert asked is False and path.exists()


def test_fetch_waits_and_tries_again_after_a_dropped_network_and_keeps_the_answer(tmp_path):
    tile = (0, 10, 0, 10)
    calls = []
    body = answer("AOD_55", {(0.5, 0.5): [0.1] * 13})

    def opener(request, timeout):
        calls.append(request.full_url)
        assert request.get_header("User-agent") == "twinfinder/0.1"
        if len(calls) == 1:
            raise urllib.error.URLError("network is unreachable")
        return FakeResponse(body)

    waits = []
    path, asked = ENV.fetch_one("AOD_55", tile, tmp_path, opener=opener, sleep=waits.append)
    assert asked is True and path.read_bytes() == body
    assert len(calls) == 2 and waits
    assert "parameters=AOD_55" in calls[0] and "latitude-min=0" in calls[0]
    assert not list(tmp_path.glob("*.part"))


def test_fetch_keeps_nothing_when_the_body_is_not_an_answer(tmp_path):
    def opener(request, timeout):
        return FakeResponse(json.dumps({"messages": ["error"], "header": {}}).encode())

    with pytest.raises(ValueError):
        ENV.fetch_one("AOD_55", (0, 10, 0, 10), tmp_path, opener=opener, sleep=lambda s: None)
    assert not list(tmp_path.iterdir())


# ---- over which years was the climatology taken ------------------------------------------------------

def monthly_answer(series: dict) -> bytes:
    """A monthly point answer: series is {parameter: {"YYYYMM": value}} (month 13 is the year)."""
    return json.dumps({"type": "Feature", "geometry": {"type": "Point", "coordinates": [-69.5, -24.5, 2367.0]},
                       "properties": {"parameter": series},
                       "header": {"fill_value": -999.0, "start": "20010101", "end": "20251231",
                                  "sources": ["SYN1DEG", "POWER"]}, "messages": []}).encode()


def test_read_series_skips_the_annual_month_and_turns_the_fill_value_into_none():
    raw = monthly_answer({"CLRSKY_DAYS": {"200101": 2.0, "200102": -999.0, "200113": 33.0}})
    assert ENV.read_series(raw, "CLRSKY_DAYS") == {(2001, 1): 2.0, (2001, 2): None}


def test_fit_end_year_finds_the_years_a_mean_was_taken_over():
    series = {(y, m): float(y - 2000) for y in range(2001, 2026) for m in range(1, 13)}
    clim = [sum(range(1, 21)) / 20] * 12          # mean over 2001 to 2020
    fit = ENV.fit_end_year(clim, series, how="mean", tolerance=0.01)
    assert fit["end_year_that_fits_best"] == 2020
    assert fit["months_equal_at_that_end_year"] == 12
    assert fit["months_equal_by_end_year"]["2025"] == 0


def test_fit_end_year_finds_a_count_summed_over_the_years():
    series = {(y, m): 1.0 for y in range(2001, 2026) for m in range(1, 13)}
    fit = ENV.fit_end_year([25.0] * 12, series, how="sum", tolerance=0.5)
    assert fit["end_year_that_fits_best"] == 2025
    assert fit["months_equal_at_that_end_year"] == 12


def test_fit_end_year_is_none_without_a_series():
    assert ENV.fit_end_year([1.0] * 12, {}, how="mean", tolerance=0.01) is None
    assert ENV.fit_end_year(None, {(2001, 1): 1.0}, how="mean", tolerance=0.01) is None


def test_days_per_month_divides_the_count_of_all_years_and_keeps_unknown_unknown():
    assert ENV.days_per_month([40.0, 0.0, None] + [20.0] * 9, 20) == [2.0, 0.0, None] + [1.0] * 9
    assert ENV.days_per_month(None, 20) is None
    with pytest.raises(ValueError):
        ENV.days_per_month([1.0] * 12, 0)


# ---- one square's record -----------------------------------------------------------------------------

def rows(value=1.0, year=1.0):
    return ([value] * 12, year)


def test_cell_record_reads_the_box_of_the_square_and_divides_clear_days_by_the_years():
    box = (-24.5, -69.5)
    by_param = {"ALLSKY_SFC_SW_DWN": {box: rows(8.123, 7.111)}, "ALLSKY_SFC_UV_INDEX": {box: rows(3.5, 2.2)},
                "AOD_55": {box: rows(0.05, 0.04)}, "CLRSKY_DAYS": {box: ([40.0] * 12, 480.0)}}
    record = ENV.cell_record(-24.25, -69.75, by_param, clear_years=20)
    assert record["grid"] == [-24.5, -69.5]
    assert record["sun_kwh_m2_day"] == [8.12] * 12 and record["sun_kwh_m2_day_year"] == 7.11
    assert record["uv_index_year"] == 2.2 and record["aod_550_year"] == 0.04
    assert record["clear_days"] == [2.0] * 12 and record["clear_days_year"] == 24.0


def test_cell_record_is_null_where_unknown_never_zero():
    box = (-24.5, -69.5)
    by_param = {"ALLSKY_SFC_SW_DWN": {box: ([None] * 12, None)}, "CLRSKY_DAYS": {box: ([0.0] * 12, 0.0)}}
    record = ENV.cell_record(-24.25, -69.75, by_param, clear_years=None)
    assert record["sun_kwh_m2_day"] is None and record["sun_kwh_m2_day_year"] is None
    assert record["uv_index"] is None and record["uv_index_year"] is None       # parameter not fetched
    assert record["clear_days"] is None and record["clear_days_year"] is None   # years not settled
    record = ENV.cell_record(-24.25, -69.75, by_param, clear_years=25)
    assert record["clear_days"] == [0.0] * 12 and record["clear_days_year"] == 0.0


# ---- what Mars is, from the project's own files ---------------------------------------------------------

def test_mars_figures_come_from_the_files_and_say_not_in_our_data_otherwise():
    sites = {"sites": [{"id": "a", "cannot_match": [
        {"what": "sunlight at the top of the atmosphere", "mars": 586.2, "earth": 1361.0, "unit": "W/m2",
         "number": 0.431, "source": "fact sheet"},
        {"what": "the dusty sky", "mars": 3, "earth": 0.13, "unit": "aerosol optical depth", "source": "paper",
         "note": "n"}]}]}
    figures = ENV.mars_figures(sites)
    top = figures["sunlight_top_of_atmosphere"]
    assert top["mars"] == 586.2 and top["unit"] == "W/m2" and top["source"] == "fact sheet"
    assert top["from_file"] == "data/derived/mars_sites.json"
    assert figures["dust_optical_depth"]["mars"] == 3
    assert figures["uv_cut_off"]["mars"] == "not in our data"
    assert figures["sunlight_at_the_ground"]["mars"] == "not in our data"
    assert figures["cloud_free_days"]["mars"] == "not in our data"


def test_mars_figures_refuse_sites_that_disagree():
    sites = {"sites": [{"id": s, "cannot_match": [{"what": "the dusty sky", "mars": m, "unit": "x", "source": "y"}]}
                       for s, m in (("a", 3), ("b", 4))]}
    with pytest.raises(ValueError, match="disagree"):
        ENV.mars_figures(sites)


def test_write_json_goes_through_a_side_file(tmp_path):
    out = tmp_path / "x.json"
    ENV.write_json(out, {"a": None})
    assert json.loads(out.read_text()) == {"a": None}
    assert not list(tmp_path.glob("*.part"))


# ---- the brightest hour of the UV day ---------------------------------------------------------------

def hours_answer(points, units="W m-2 x 40"):
    """points is {(lat, lon): {hour: [12 values] + [annual]}} for the hour-based UV set."""
    features = []
    for (lat, lon), hours in points.items():
        parameter = {f"ALLSKY_SFC_UV_INDEX_{h:02d}": dict(zip(MONTHS + ["ANN"], values)) for h, values in hours.items()}
        features.append({"geometry": {"coordinates": [lon, lat, 0.0]}, "properties": {"parameter": parameter}})
    return json.dumps({"features": features, "header": {"fill_value": -999.0, "sources": ["SYN1DEG", "POWER"]},
                       "parameters": {f"ALLSKY_SFC_UV_INDEX_{h:02d}": {"units": units} for h in range(24)}}).encode()


def test_peak_hour_is_the_highest_hour_of_each_months_mean_day():
    hours = {h: [0.0] * 13 for h in range(24)}
    hours[12] = [16.0] * 6 + [6.0] * 6 + [11.0]
    hours[13] = [15.0] * 6 + [6.5] * 6 + [10.0]
    out = ENV.read_uv_hours(hours_answer({(-24.5, -69.5): hours}))
    assert out[(-24.5, -69.5)] == ([16.0] * 6 + [6.5] * 6, [12] * 6 + [13] * 6)


def test_peak_hour_needs_all_24_hours_and_the_right_units():
    hours = {h: [0.0] * 13 for h in range(23)}
    with pytest.raises(ValueError, match="24"):
        ENV.read_uv_hours(hours_answer({(-24.5, -69.5): hours}))
    with pytest.raises(ValueError, match="units"):
        ENV.read_uv_hours(hours_answer({(-24.5, -69.5): {h: [0.0] * 13 for h in range(24)}}, units="x"))


def test_peak_hour_of_a_month_with_a_missing_hour_is_unknown():
    hours = {h: [1.0] * 13 for h in range(24)}
    hours[5] = [-999.0] + [1.0] * 12
    months, at = ENV.read_uv_hours(hours_answer({(0.5, 0.5): hours}))[(0.5, 0.5)]
    assert months[0] is None and at[0] is None and months[1] == 1.0


def test_years_check_names_the_years_only_when_every_month_of_every_point_is_equal(tmp_path, monkeypatch):
    monkeypatch.setattr(ENV, "CHECKS", tmp_path)
    monkeypatch.setattr(ENV, "CHECK_POINTS", (("a", 0.5, 0.5), ("b", 1.5, 0.5)))
    series = {p: {f"{y}{m:02d}": float(y - 2000) for y in range(2001, 2026) for m in range(1, 13)}
              for p in ENV.CHECK_PARAMETERS}
    for _, lat, lon in ENV.CHECK_POINTS:
        (tmp_path / ENV.check_name(lat, lon)).write_bytes(monthly_answer(series))
    mean_2020 = sum(range(1, 21)) / 20

    def read_box(parameter, box):
        return ([mean_2020] * 12, None) if box == (0.5, 0.5) else ([mean_2020] * 11 + [13.0], None)

    out = ENV.years_check(read_box)["ALLSKY_SFC_SW_DWN"]
    assert out["end_year_that_fits_best_all_points"] == 2020
    assert out["months_equal_at_that_end_year"] == 23
    assert out["all_points_agree"] is False and out["years_the_values_fit"] is None


def test_cell_record_carries_the_brightest_hour_of_the_uv_day_and_null_without_it():
    box = (-24.5, -69.5)
    peaks = {box: ([16.371] + [None] + [5.0] * 10, [11] + [None] + [11] * 10)}
    record = ENV.cell_record(-24.25, -69.75, {}, clear_years=20, uv_peaks=peaks)
    assert record["uv_index_brightest_hour"] == [16.37, None] + [5.0] * 10
    assert record["uv_index_brightest_hour_max"] == 16.37
    record = ENV.cell_record(-24.25, -69.75, {}, clear_years=20)
    assert record["uv_index_brightest_hour"] is None and record["uv_index_brightest_hour_max"] is None


def test_box_summary_ranks_boxes_not_squares_and_skips_unknown():
    cells = {"m_1": {"sun_kwh_m2_day_year": 7.0, "grid": [0.5, 0.5]}, "m_2": {"sun_kwh_m2_day_year": 7.0, "grid": [0.5, 0.5]},
             "m_3": {"sun_kwh_m2_day_year": 6.0, "grid": [1.5, 0.5]}, "m_4": {"sun_kwh_m2_day_year": None, "grid": [2.5, 0.5]}}
    regions = {"m_1": "Sahara", "m_2": "Sahara", "m_3": "other", "m_4": "other"}
    top = ENV.box_ranking(cells, regions, "sun_kwh_m2_day_year", n=5, highest=True)
    assert [t["grid"] for t in top] == [[0.5, 0.5], [1.5, 0.5]]
    assert top[0]["ranked_squares"] == 2 and top[0]["regions"] == ["Sahara"] and top[0]["value"] == 7.0
    low = ENV.box_ranking(cells, regions, "sun_kwh_m2_day_year", n=1, highest=False)
    assert low[0]["grid"] == [1.5, 0.5]


def test_spread_is_median_and_range_of_the_known_values():
    assert ENV.spread([3.0, None, 1.0, 2.0]) == {"median": 2.0, "min": 1.0, "max": 3.0, "squares": 3}
    assert ENV.spread([None]) is None


def test_fit_end_year_does_not_count_a_month_that_says_nothing_about_the_years():
    series = {(y, m): 0.0 for y in range(2001, 2026) for m in range(1, 13)}
    assert ENV.fit_end_year([0.0] * 12, series, how="sum", tolerance=0.5) is None
    series.update({(y, 1): 1.0 for y in range(2001, 2026)})
    fit = ENV.fit_end_year([20.0] + [0.0] * 11, series, how="sum", tolerance=0.5)
    assert fit["months_compared"] == 1 and fit["end_year_that_fits_best"] == 2020
    assert fit["end_years_tied_at_best"] == [2020]


def test_fit_end_year_lists_end_years_that_fit_equally_well():
    series = {(y, m): (1.0 if y <= 2020 else 1.004) for y in range(2001, 2026) for m in range(1, 13)}
    series.update({(2001, m): 2.0 for m in range(1, 13)})
    fit = ENV.fit_end_year([1.05] * 12, series, how="mean", tolerance=0.011)
    tied = fit["end_years_tied_at_best"]
    assert 2020 in tied and len(tied) > 1 and tied == sorted(tied)
    assert fit["end_year_that_fits_best"] == tied[-1]


def test_uv_check_compares_the_daily_index_with_the_mean_of_its_24_hours():
    parameter = {f"ALLSKY_SFC_UV_INDEX_{h:02d}": dict(zip(MONTHS + ["ANN"], [(2.4 if 10 <= h <= 13 else 0.0)] * 13))
                 for h in range(24)}
    parameter["ALLSKY_SFC_UV_INDEX"] = dict(zip(MONTHS + ["ANN"], [0.4] * 13))
    raw = json.dumps({"properties": {"parameter": parameter}, "header": {"fill_value": -999.0}}).encode()
    check = ENV.uv_check(raw)
    assert check["months"] == 12
    assert check["largest_gap_daily_minus_mean_of_24_hours"] == pytest.approx(0.0)
    assert check["brightest_hour_over_daily"]["JAN"] == pytest.approx(6.0)


# ---- added by ENV-CHECK: the yearly clear-day count where the service withholds it, and the words ----

from pathlib import Path  # noqa: E402

from twinfinder import environment as moon_env  # noqa: E402

DERIVED = Path(__file__).resolve().parents[1] / "data" / "derived"


def test_clear_days_year_says_whether_it_is_the_services_annual_or_the_sum_of_its_months():
    months = [100.0] * 12
    assert ENV.clear_days_year((months, 1200.0), 20) == (60.0, "annual")
    # the service gives its fill value for the year whenever the total passes 1800; the months are all there
    assert ENV.clear_days_year((months, None), 20) == (60.0, "sum of months")
    assert ENV.clear_days_year(([None] + months[1:], None), 20) == (None, None)
    assert ENV.clear_days_year((months, 1200.0), None) == (None, None)
    assert ENV.clear_days_year(None, 20) == (None, None)


def test_the_meaning_and_what_it_is_not_of_every_field_are_said_in_sentences_of_25_words_or_fewer():
    assert list(moon_env.long_sentences(ENV.WHAT_IT_IS_NOT)) == []
    assert list(moon_env.long_sentences(ENV.FIELD_MEANING)) == []


def _box(value, grid=(23.5, 27.5), regions=("Sahara",), square="m_23.25_27.25"):
    return {"grid": list(grid), "value": value, "ranked_squares": 3, "regions": list(regions), "example_square": square}


def test_the_mars_comparison_sentences_are_25_words_or_fewer_and_keep_their_figures():
    extremes = {"most_sunlight_at_the_ground": [_box(7.37)], "highest_uv_index_24_hour_mean": [_box(3.38)],
                "highest_uv_index_brightest_hour": [_box(19.7)], "most_clear_sky_days": [_box(276.0)],
                "least_haze": [_box(0.0, regions=("Transantarctic Mountains",))],
                "least_haze_north_of_60s": [_box(0.02, regions=("Patagonian Desert",))],
                "most_haze": [_box(0.72)], "haziest_month": [_box(1.13, regions=("other",))]}
    mars = {"sunlight_top_of_atmosphere": {"mars": 586.2, "earth": 1361.0, "unit": "W/m2", "number": 0.431},
            "dust_optical_depth": {"mars": 3, "source": "Mars: Martinez et al. 2017, Space Science Reviews, section 3.1"},
            "uv_cut_off": {"mars": 190, "earth": 290, "source": "literature, not checked against a saved file"}}
    cells = {"m_23.25_27.25": {"clearness_index_year": 0.8}}
    sentences = ENV.comparison_sentences(extremes, mars, cells)
    assert set(sentences) == {"sunlight", "uv", "clear_days", "haze"}
    assert list(moon_env.long_sentences(sentences)) == []
    assert "7.37" in sentences["sunlight"] and "586.2" in sentences["sunlight"] and "0.431" in sentences["sunlight"]
    assert "19.7" in sentences["uv"] and "190" in sentences["uv"] and "not checked" in sentences["uv"]
    assert "276" in sentences["clear_days"] and "1.13" in sentences["haze"] and "3" in sentences["haze"]
    assert "(other" not in sentences["haze"]


def test_the_real_file_says_everything_in_sentences_of_25_words_or_fewer():
    path = DERIVED / "mars_environment.json"
    if not path.exists():
        pytest.skip("data/derived/mars_environment.json not built")
    meta = json.loads(path.read_text())["meta"]
    assert list(moon_env.long_sentences(meta)) == []
    assert "month_sum" in json.dumps(meta["counts"])


# ---- added by ENV-CHECK for breakages the tests above did not catch ----

def _haze_sentence(month_value, month_regions=("other",)):
    extremes = {"least_haze": [_box(0.0)], "least_haze_north_of_60s": [_box(0.02)], "most_haze": [_box(0.72)],
                "haziest_month": [_box(month_value, grid=(31.5, 72.5), regions=month_regions)],
                "most_sunlight_at_the_ground": [], "highest_uv_index_24_hour_mean": [],
                "highest_uv_index_brightest_hour": [], "most_clear_sky_days": []}
    mars = {"sunlight_top_of_atmosphere": {}, "dust_optical_depth": {"mars": 3, "source": "Martinez et al. 2017"},
            "uv_cut_off": {}}
    return ENV.comparison_sentences(extremes, mars, {})["haze"]


def test_the_haze_sentence_says_within_or_above_the_clear_mars_season_by_the_number():
    assert "just above that 'below 1'" in _haze_sentence(1.13)
    assert "within that 'below 1'" in _haze_sentence(0.9)


def test_a_box_outside_every_named_region_is_given_by_its_place_not_as_other():
    said = _haze_sentence(1.13)
    assert "other" not in said and "(31.5, 72.5)" in said

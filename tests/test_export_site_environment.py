"""The export of UV, sunlight at the ground, clear-sky days and haze for the map page.

Unknown must never become 0, the rows must follow the page's own order of areas (site/data/cells.json)
and of Mars squares (site/data/mars.json, else data/derived/mars_cells.json), the figures must equal
the source at the stated precision, and the script must still run when the Mars file is missing.
"""
import importlib
import json
import re
from pathlib import Path

import numpy as np
import pytest

env = importlib.import_module("scripts.export_site_environment")

ROOT = Path(__file__).resolve().parents[1]
DERIVED = ROOT / "data" / "derived"
SITE_DATA = ROOT / "site" / "data"
REAL = all((p).exists() for p in (DERIVED / "environment_cells.json", SITE_DATA / "cells.json"))


# ---- a tiny project tree ----

def _months(value):
    return [value] * 12


def _env_record(uv=0.5, sun=3.21, clear=4.05, days=0.1, aod=0.12):
    return {"uv_index": _months(uv), "sun_kwh_m2_day": _months(sun), "sun_clear_kwh_m2_day": _months(clear),
            "clear_days": _months(days), "clear_days_total": _months(None if days is None else days * 20),
            "aod_550": _months(aod), "grid": {"lat": 75.5, "lon": -89.5, "deg": 1.0}, "sunless_months": []}


def _env_meta():
    parameter = {"name_in_the_service": "x", "definition_in_the_service": "The number of Clear Sky Days if the daytime "
                 "cloud amount is less than 10 percent.", "unit": "Days", "source_named_by_the_service": ["SYN1DEG"],
                 "grid": "1 x 1 degree boxes", "period_named_by_the_service": "2001-01-01 to 2025-12-31",
                 "what_it_is": "w", "what_it_is_not": "n"}
    fields = {"uv_index": "ALLSKY_SFC_UV_INDEX", "sun_kwh_m2_day": "ALLSKY_SFC_SW_DWN",
              "sun_clear_kwh_m2_day": "CLRSKY_SFC_SW_DWN", "clear_days_total": "CLRSKY_DAYS", "aod_550": "AOD_55_ADJ"}
    return {"fields": fields, "parameters": {name: {**parameter, "field": field} for field, name in fields.items()},
            "clear_days": {"years": 20, "period": "2001-2020"}, "written": "2026-11-15T05:49:36Z",
            "checks": {"period": {"summary": {"ALLSKY_SFC_SW_DWN": {"fits_better": "2001-2020"}}},
                       "uv_index_daily_value": {"points": [{"result": {"mean_of_hours_mean": 1.0, "highest_hour_mean": 2.3}}]}}}


def _tree(tmp_path: Path, ids, records, mars=True, site_mars=True) -> Path:
    root = tmp_path / "project"
    (root / "site" / "data").mkdir(parents=True)
    (root / "data" / "derived").mkdir(parents=True)
    cells = {"n": len(ids), "ids": ids, "lat": [7530] * len(ids), "lon": [-9000] * len(ids), "hemisphere": "N" * len(ids),
             "units": {"lat": "hundredths of a degree", "lon": "hundredths of a degree"}}
    (root / "site" / "data" / "cells.json").write_text(json.dumps(cells))
    (root / "data" / "derived" / "environment_cells.json").write_text(json.dumps({"meta": _env_meta(), "cells": records}))
    (root / "data" / "derived" / "cloud_cells.json").write_text(json.dumps(
        {"meta": {"parameter": "CLOUD_AMT"}, "cells": {i: {"cloud_pct_day": _months(61.25)} for i in ids}}))
    if mars:
        squares = {"m_1.25_2.25": {"uv_index": _months(2.5), "uv_index_brightest_hour": _months(11.0),
                                   "sun_kwh_m2_day": _months(6.0), "clear_days": _months(None), "aod_550": _months(0.3),
                                   "sun_kwh_m2_day_year": 6.0, "sun_clear_sky_kwh_m2_day_year": 7.0, "uv_index_year": 2.5,
                                   "uv_index_brightest_hour_max": 11.0, "clear_days_year": None, "aod_550_year": 0.3,
                                   "clearness_index_year": 0.6, "top_of_atmosphere_kwh_m2_day_year": 10.0, "grid": [1.5, 2.5]},
                   "m_0.25_0.25": {"uv_index": _months(0.0), "uv_index_brightest_hour": _months(0.0),
                                   "sun_kwh_m2_day": _months(0.0), "clear_days": _months(0.0), "aod_550": _months(0.0),
                                   "sun_kwh_m2_day_year": 0.0, "sun_clear_sky_kwh_m2_day_year": 0.0, "uv_index_year": 0.0,
                                   "uv_index_brightest_hour_max": 0.0, "clear_days_year": 0.0, "aod_550_year": 0.0,
                                   "clearness_index_year": None, "top_of_atmosphere_kwh_m2_day_year": 0.0, "grid": [0.5, 0.5]}}
        (root / "data" / "derived" / "mars_environment.json").write_text(json.dumps({"meta": {"written": "w"}, "cells": squares}))
        # the scoring file lists the squares in one order, the page's file in another
        (root / "data" / "derived" / "mars_cells.json").write_text(json.dumps(
            {"cells": {"m_1.25_2.25": {"id": "m_1.25_2.25"}, "m_0.25_0.25": {"id": "m_0.25_0.25"}}}))
        if site_mars:
            (root / "site" / "data" / "mars.json").write_text(json.dumps(
                {"squares": {"file": "mars_squares.bin", "count": 2, "ids": ["m_0.25_0.25", "m_1.25_2.25"]}}))
    return root


def _read(out: Path, name: str):
    return json.loads((out / name).read_text())


def _table(out: Path, name: str, layout: dict) -> np.ndarray:
    raw = np.frombuffer((out / name).read_bytes(), dtype="<u2")
    return raw[:int(np.prod(layout["shape"]))].reshape(layout["shape"])


# ---- packing ----

def test_unknown_gets_its_own_value_and_a_real_zero_stays_zero():
    packed = env.pack([[None, 0.0, 0.01, 2.5]], 100)
    assert packed.dtype == np.dtype("<u2")
    assert packed.tolist() == [[env.UNKNOWN, 0, 1, 250]]


def test_a_value_too_large_for_the_layout_is_refused_not_turned_into_unknown():
    with pytest.raises(env.EnvError):
        env.pack([[env.UNKNOWN / 100.0]], 100)
    with pytest.raises(env.EnvError):
        env.pack([[-0.5]], 100)


def test_nan_is_unknown():
    assert env.pack([[float("nan")]], 100).tolist() == [[env.UNKNOWN]]


# ---- the Moon part ----

def test_rows_follow_the_page_order_and_figures_equal_the_source(tmp_path):
    ids = ["b", "a", "c"]
    records = {"a": _env_record(uv=0.25), "b": _env_record(uv=1.5, sun=5.0282), "c": _env_record(uv=0.0, sun=0.0)}
    root = _tree(tmp_path, ids, records)
    out = tmp_path / "out"
    summary = env.export(root, out)
    doc = _read(out, "environment.json")
    assert doc["areas"]["count"] == 3 and doc["areas"]["first_id"] == "b" and doc["areas"]["last_id"] == "c"
    table = _table(out, "environment.bin", doc["layout"])
    names = doc["layout"]["fields"]
    assert table.shape == (3, len(names), 12)
    uv = names.index("uv_index")
    assert table[:, uv, 0].tolist() == [150, 25, 0]
    sun = names.index("sun_kwh_m2_day")
    assert table[0, sun, 0] == 503             # 5.0282 kept to hundredths
    assert table[2, sun, 0] == 0               # polar night: a real zero
    assert summary["environment"]["areas"] == 3


def test_unknown_in_the_source_is_unknown_in_the_file_never_0(tmp_path):
    record = _env_record()
    record["uv_index"][3] = None
    record["aod_550"] = None
    root = _tree(tmp_path, ["a"], {"a": record})
    out = tmp_path / "out"
    env.export(root, out)
    doc = _read(out, "environment.json")
    table = _table(out, "environment.bin", doc["layout"])
    names = doc["layout"]["fields"]
    assert table[0, names.index("uv_index"), 3] == doc["layout"]["unknown"] == env.UNKNOWN
    assert (table[0, names.index("aod_550")] == env.UNKNOWN).all()
    assert table[0, names.index("uv_index"), 2] != env.UNKNOWN


def test_cloud_amount_is_stored_only_where_clear_days_are_unknown_and_flagged(tmp_path):
    root = _tree(tmp_path, ["a", "b"], {"a": _env_record(days=None), "b": _env_record(days=0.65)})
    out = tmp_path / "out"
    env.export(root, out)
    doc = _read(out, "environment.json")
    table = _table(out, "environment.bin", doc["layout"])
    names = doc["layout"]["fields"]
    days, cloud = names.index("clear_days"), names.index("cloud_day_pct_fallback")
    assert (table[0, days] == env.UNKNOWN).all() and (table[0, cloud] == 6125).all()
    assert table[1, days, 0] == 65 and (table[1, cloud] == env.UNKNOWN).all()
    assert doc["clear_days_fallback"]["area_months_using_it"] == 12
    assert doc["clear_days_fallback"]["areas_using_it"] == 1


def test_an_area_the_source_lacks_stops_the_export(tmp_path):
    root = _tree(tmp_path, ["a", "b"], {"a": _env_record()})
    with pytest.raises(env.EnvError, match="lacks 1"):
        env.export(root, tmp_path / "out")


def test_the_layout_is_stated_exactly(tmp_path):
    root = _tree(tmp_path, ["a"], {"a": _env_record()})
    out = tmp_path / "out"
    env.export(root, out)
    doc = _read(out, "environment.json")
    layout = doc["layout"]
    assert layout["dtype"] == "uint16" and layout["byte_order"] == "little-endian"
    assert layout["shape"] == [1, len(layout["fields"]), 12]
    assert layout["bytes"] == (out / "environment.bin").stat().st_size == 2 * 1 * len(layout["fields"]) * 12
    assert layout["unknown"] == 65535 and all(s == 100 for s in layout["divide_by"].values())
    assert "offset" in layout["how_to_read"]
    assert not list(out.glob("*.part"))       # written beside, then renamed


def test_page_sentences_are_short_and_say_area_and_lunar_region(tmp_path):
    root = _tree(tmp_path, ["a"], {"a": _env_record()})
    out = tmp_path / "out"
    env.export(root, out)
    doc = _read(out, "environment.json")
    sentences = env.page_sentences(doc)
    assert len(sentences) > 10
    for sentence in sentences:
        assert len(sentence.split()) <= 25, sentence
        assert not re.search(r"\bcells?\b", sentence), sentence
    groups = {group["key"] for group in doc["groups"]}
    assert groups == {"sunlight", "uv", "clear_days", "haze"}
    haze = next(group for group in doc["groups"] if group["key"] == "haze")
    assert "all fine particles in the air, not dust alone" in haze["label_words"]


def test_each_row_has_one_scale_for_all_areas_and_unknown_does_not_set_it(tmp_path):
    high = _env_record(uv=2.75, sun=6.5, clear=7.25, aod=0.31)
    high["uv_index"][0] = None
    root = _tree(tmp_path, ["a", "b"], {"a": _env_record(), "b": high})
    out = tmp_path / "out"
    env.export(root, out)
    groups = {g["key"]: g for g in _read(out, "environment.json")["groups"]}
    assert groups["uv"]["scale_top"] == 2.75
    assert groups["sunlight"]["scale_top"] == 7.25          # the clear-sky figure is the larger of the two
    assert groups["haze"]["scale_top"] == 0.31


# ---- the Mars part ----

def test_mars_rows_follow_the_page_mars_file_and_say_so(tmp_path):
    root = _tree(tmp_path, ["a"], {"a": _env_record()})
    out = tmp_path / "out"
    summary = env.export(root, out)
    doc = _read(out, "mars_environment.json")
    assert doc["squares"]["ids"] == ["m_0.25_0.25", "m_1.25_2.25"]
    assert "site/data/mars.json" in doc["squares"]["order"]
    monthly = _table(out, "mars_environment.bin", doc["layout"]["monthly"])
    names = doc["layout"]["monthly"]["fields"]
    assert monthly[0, names.index("uv_index"), 0] == 0                       # a real zero
    assert monthly[1, names.index("uv_index"), 0] == 250
    assert (monthly[1, names.index("clear_days")] == env.UNKNOWN).all()       # null stays unknown
    yearly_layout = doc["layout"]["yearly"]
    raw = np.frombuffer((out / "mars_environment.bin").read_bytes(), dtype="<u2")
    start = yearly_layout["offset_bytes"] // 2
    yearly = raw[start:start + int(np.prod(yearly_layout["shape"]))].reshape(yearly_layout["shape"])
    ynames = yearly_layout["fields"]
    assert yearly[1, ynames.index("clear_days_year")] == env.UNKNOWN
    assert yearly[0, ynames.index("clearness_index_year")] == env.UNKNOWN
    assert yearly[1, ynames.index("top_of_atmosphere_kwh_m2_day_year")] == 1000
    assert summary["mars"]["order_from"] == "site/data/mars.json"


def test_mars_order_falls_back_to_the_scoring_file(tmp_path):
    root = _tree(tmp_path, ["a"], {"a": _env_record()}, site_mars=False)
    out = tmp_path / "out"
    env.export(root, out)
    doc = _read(out, "mars_environment.json")
    assert doc["squares"]["ids"] == ["m_1.25_2.25", "m_0.25_0.25"]
    assert "data/derived/mars_cells.json" in doc["squares"]["order"]


def test_the_script_runs_without_the_mars_file_and_says_so(tmp_path, capsys):
    root = _tree(tmp_path, ["a"], {"a": _env_record()}, mars=False)
    out = tmp_path / "out"
    code = env.main(["--root", str(root), "--out", str(out)])
    assert code == 0
    assert (out / "environment.json").exists() and (out / "environment.bin").exists()
    assert not (out / "mars_environment.json").exists()
    said = capsys.readouterr().out
    assert "mars_environment.json" in said and "missing" in said
    doc = _read(out, "environment.json")
    assert doc["mars_file"] is None


# ---- the real files ----

@pytest.mark.skipif(not REAL, reason="the pipeline files are not here")
def test_real_export_matches_the_page_and_the_source(tmp_path):
    out = tmp_path / "out"
    env.export(ROOT, out)
    cells = json.loads((SITE_DATA / "cells.json").read_text())
    doc = _read(out, "environment.json")
    assert doc["areas"]["count"] == cells["n"] == len(cells["ids"])
    assert doc["areas"]["first_id"] == cells["ids"][0] and doc["areas"]["last_id"] == cells["ids"][-1]
    table = _table(out, "environment.bin", doc["layout"])
    source = json.loads((DERIVED / "environment_cells.json").read_text())["cells"]
    names = doc["layout"]["fields"]
    for field in ("uv_index", "sun_kwh_m2_day", "sun_clear_kwh_m2_day", "clear_days", "aod_550"):
        f = names.index(field)
        want = np.array([[np.nan if v is None else v for v in (source[i][field] or [None] * 12)] for i in cells["ids"]])
        got = table[:, f, :]
        unknown = np.isnan(want)
        assert ((got == env.UNKNOWN) == unknown).all(), field
        assert np.allclose(got[~unknown] / 100.0, np.round(want[~unknown], 2), atol=1e-9), field
    for sentence in env.page_sentences(doc):
        assert len(sentence.split()) <= 25, sentence
    if (DERIVED / "mars_environment.json").exists():
        mars = _read(out, "mars_environment.json")
        page = SITE_DATA / "mars.json"
        if page.exists():
            assert mars["squares"]["ids"] == json.loads(page.read_text())["squares"]["ids"]
        assert mars["squares"]["count"] == len(mars["squares"]["ids"])


# ---- added by ENV-CHECK: figures said no wider than the check behind them, and short sentences in every file ----

from twinfinder import environment as moon_env  # noqa: E402


def test_the_uv_ratio_is_said_for_the_boxes_and_days_it_was_checked_at_not_for_every_area(tmp_path):
    root = _tree(tmp_path, ["a"], {"a": _env_record()})
    out = tmp_path / "out"
    env.export(root, out)
    uv = next(group for group in _read(out, "environment.json")["groups"] if group["key"] == "uv")
    said = " ".join(uv["is_not"])
    assert "2.3" in said and "one box checked" in said and "summer" in said


def test_the_lit_share_is_said_as_a_mean_over_the_mapped_area():
    targets = [{"id": "malapert", "name": "Malapert Massif", "limit_deg": 5.55}]
    cards = {"cards": [{"id": "malapert", "lit": {"mean_share": 0.359}, "earth_cannot_match": []}]}
    env_doc = {"meta": _env_meta(), "cells": {"a": _env_record()}}
    groups, _, _ = env.moon_groups(env_doc, cards, targets)
    sun = next(group for group in groups if group["key"] == "sunlight")
    lit = next(s for s in sun["moon_by_target"]["malapert"] if "lit" in s)
    assert "36 percent" in lit and "averaged over the mapped area" in lit.lower()


@pytest.mark.skipif(not REAL, reason="the real data files are not built")
def test_every_sentence_of_the_real_page_files_is_25_words_or_fewer(tmp_path):
    out = tmp_path / "out"
    env.export(ROOT, out)
    assert list(moon_env.long_sentences(_read(out, "environment.json"))) == []
    if (DERIVED / "mars_environment.json").exists():
        mars = _read(out, "mars_environment.json")
        mars.pop("squares")
        assert list(moon_env.long_sentences(mars)) == []
        assert "mars_comparison_note" not in mars


def test_the_years_the_values_fit_are_said_as_found_at_the_boxes_checked_not_as_the_services_word(tmp_path):
    root = _tree(tmp_path, ["a"], {"a": _env_record()})
    out = tmp_path / "out"
    env.export(root, out)
    doc = _read(out, "environment.json")
    clear = next(group for group in doc["groups"] if group["key"] == "clear_days")
    years = next(s for s in clear["is"] if "2020" in s)
    assert "boxes checked" in years and "we divide by 20" in years
    fit = next(s for s in doc["general"] if "2025" in s)
    assert "boxes checked" in fit and "2001 to 2020" in fit


# ---- added by ENV-CHECK for breakages the tests above did not catch ----

def test_an_area_listed_twice_in_the_page_order_stops_the_export():
    with pytest.raises(env.EnvError):
        env.page_area_ids({"n": 3, "ids": ["a", "b", "a"]})


def test_a_mars_count_that_does_not_match_its_ids_stops_the_export():
    with pytest.raises(env.EnvError):
        env.mars_order({"squares": {"count": 3, "ids": ["m_0.25_0.25", "m_1.25_2.25"]}}, None)


def test_the_uv_ratio_keeps_its_low_and_high_end_and_names_the_boxes():
    meta = {"checks": {"uv_index_daily_value": {"points": [
        {"result": {"mean_of_hours_mean": 1.0, "highest_hour_mean": 2.3}},
        {"result": {"mean_of_hours_mean": 1.0, "highest_hour_mean": 2.4}}]}}}
    ratio = env._uv_ratio(meta)
    assert ratio == (2.3, 2.4, 2)
    assert "2.3 to 2.4 times" in env._uv_ratio_words(ratio) and "two boxes checked" in env._uv_ratio_words(ratio)


def test_a_one_degree_grid_box_is_said_to_be_about_111_km_tall():
    assert env.grid_km(1.0) == 111 and env.grid_km(None) is None

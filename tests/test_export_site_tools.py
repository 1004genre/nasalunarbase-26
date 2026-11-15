"""The third export for the map page: the data behind the round 3 tools.

Unknown must stay unknown, per-area files must follow the page's own list of areas, every figure must
equal its source, and no sentence written into a file may run over 25 words.
"""
import importlib
import json
import math
import re
from pathlib import Path

import numpy as np
import pytest

tools = importlib.import_module("scripts.export_site_tools")

ROOT = Path(__file__).resolve().parents[1]
DERIVED = ROOT / "data" / "derived"
SITE_DATA = ROOT / "site" / "data"
TARGET_IDS = ["connecting-ridge", "malapert", "mons-mouton", "nobile-rim-2"]
JSON_OUTPUTS = ["famous.json", "basis.json", "search.json", "glossary.json", "tour.json", "airfields.json",
                "winter_leads.json", "tools.json"]
OPTIONAL = ["checks.json", "access_cells.json", "winter_leads.json"]

needs_data = pytest.mark.skipif(not (SITE_DATA / "cells.json").exists() or not (DERIVED / "validation_extras.json").exists(),
                                reason="the page's cells.json or the pipeline's validation_extras.json is not on disk")


# ---- helpers ----

def words(sentence: str) -> int:
    return len(sentence.split())


def sentences(text: str) -> list[str]:
    return [part for part in re.split(r"(?<=[.!?])\s+", text.strip()) if part]


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, inner in value.items():
            yield from strings(key)
            yield from strings(inner)
    elif isinstance(value, list):
        for inner in value:
            yield from strings(inner)


def read(folder: Path, name: str):
    return json.loads((folder / name).read_text())


def tiny_areas(ids, lats, lons):
    return {"ids": list(ids), "index": {a: i for i, a in enumerate(ids)}, "lat": list(lats), "lon": list(lons),
            "hemisphere": ["N" if v > 0 else "S" for v in lats], "region": None}


def airfield(name, ident, km, scheduled, lat=70.0, lon=20.0):
    return {"name": name, "ident": ident, "country": "NO", "type": "small_airport", "km": km, "municipality": None,
            "scheduled_service": scheduled, "lat": lat, "lon": lon}


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    """One full run on the files on disk, into a folder of its own."""
    if not (SITE_DATA / "cells.json").exists():
        pytest.skip("site/data/cells.json is not on disk")
    out = tmp_path_factory.mktemp("tools_out")
    report = tools.export(DERIVED, SITE_DATA, out)
    return out, report


@pytest.fixture(scope="module")
def run_without_optional(tmp_path_factory):
    """A run with checks.json, access_cells.json and winter_leads.json missing."""
    if not (SITE_DATA / "cells.json").exists():
        pytest.skip("site/data/cells.json is not on disk")
    derived = tmp_path_factory.mktemp("derived_missing")
    for path in DERIVED.iterdir():
        if path.name not in OPTIONAL:
            (derived / path.name).symlink_to(path)
    out = tmp_path_factory.mktemp("tools_out_missing")
    report = tools.export(derived, SITE_DATA, out)
    return out, report


# ---- the sentence guard ----

def test_say_returns_none_when_a_value_is_unknown_and_never_writes_a_long_sentence():
    assert tools.say("It has {h} hours.", h=None) is None
    assert tools.say("It has {h} hours.", h=12) == "It has 12 hours."
    long = " ".join(["word"] * 26) + "."
    assert tools.first_short(long, "Short enough.") == "Short enough."
    assert tools.first_short(long) is None


def test_the_writer_refuses_a_sentence_over_25_words(tmp_path):
    with pytest.raises(tools.ToolsError):
        tools.checked_json({"text": " ".join(["word"] * 26) + "."})
    assert tools.checked_json({"text": "A short one. Another short one."})


# ---- access ----

def test_access_unknown_is_65535_never_0_and_a_true_zero_stays_0():
    areas = tiny_areas(["a", "b", "c"], [70.0, 71.0, -70.0], [20.0, 21.0, 10.0])
    doc = {"cells": {
        "a": {"nearest": airfield("Here", "H1", 0.0, True), "nearest_scheduled": airfield("Here", "H1", 0.0, True)},
        "b": {"nearest": airfield("Strip", "S1", 12.4, False), "nearest_scheduled": None},
        "c": {"nearest": None, "nearest_scheduled": None}}}
    table, fields = tools.access_table(doc, areas)
    assert table.dtype == np.uint16 and table.shape == (3, 4)
    assert table[0].tolist() == [0, 0, 0, 0]                    # the airfield is at the centre: a real 0 km
    assert table[1, 0] == 65535 and table[1, 1] == 65535        # no scheduled airfield known
    assert table[1, 3] == 12 and fields[table[1, 2]]["ident"] == "S1"
    assert table[2].tolist() == [65535] * 4
    assert fields[0]["scheduled"] is True and fields[table[1, 2]]["scheduled"] is False


def test_access_follows_the_pages_order_and_a_missing_area_fails_loudly():
    areas = tiny_areas(["b", "a"], [70.0, 71.0], [20.0, 21.0])
    doc = {"cells": {"a": {"nearest": airfield("A", "A1", 5.0, True), "nearest_scheduled": airfield("A", "A1", 5.0, True)},
                     "b": {"nearest": airfield("B", "B1", 9.0, True), "nearest_scheduled": airfield("B", "B1", 9.0, True)}}}
    table, fields = tools.access_table(doc, areas)
    assert fields[table[0, 0]]["ident"] == "B1" and table[0, 1] == 9
    assert fields[table[1, 0]]["ident"] == "A1" and table[1, 1] == 5
    with pytest.raises(tools.ToolsError, match="z9"):
        tools.access_table(doc, tiny_areas(["a", "z9"], [70.0, 70.0], [1.0, 2.0]))


# ---- the famous sites ----

TARGETS = [{"id": "malapert", "name": "Malapert Massif", "short": "Malapert Massif", "limit_deg": 5.55}]


def row(flat, snow, opened, verdict="middling", hemisphere="N", rock=None):
    return {"name": "X", "cell": "70.0_20.0", "lat": 70.0, "lon": 20.0, "hemisphere": hemisphere, "in_the_search": True,
            "region": "Svalbard", "cell_ranked": True, "not_ranked_because": [],
            "targets": {"malapert": {"long_flat_hours": flat, "long_snow_free_hours": snow, "long_open_hours": opened,
                                     "percentile_among_ranked": 50.0, "rank_from_top": 10, "ranked_cells": 100,
                                     "verdict": verdict, "flat_horizon_hours": rock if hemisphere == "S" else snow}}}


def test_the_step_that_removes_a_site_or_costs_it_most():
    def judge(flat, snow, opened, cloud, verdict="middling"):
        return tools.judge_area(row(flat, snow, opened, verdict), {"malapert": cloud}, TARGETS)["malapert"]
    assert judge(0.0, 0.0, 0.0, 0.0)["step"] == "sun"                   # no two-hour spell over a flat horizon
    assert judge(256.0, 0.0, 0.0, 0.0)["step"] == "snow"                 # snow takes every hour
    assert judge(120.0, 80.0, 0.0, 0.0)["step"] == "hills"
    assert judge(500.0, 150.0, 100.0, 30.0, "high")["step"] == "holds-up"
    costly = judge(500.0, 150.0, 100.0, 30.0)
    assert costly["step"] == "snow" and costly["costliest"] == "snow"
    assert judge(300.0, 280.0, 60.0, 20.0)["costliest"] == "hills"
    assert judge(80.0, 21.7, 0.1, 0.0)["step"] == "hills"                # under half an hour left is no hour left


def test_a_costly_step_is_never_worded_as_one_that_removes_the_site():
    v = tools.judge_area(row(503.7, 170.9, 43.4, 11.3), {"malapert": 11.3}, TARGETS)["malapert"]
    assert v["step"] == "snow" and v["removed"] is False
    assert "costs most" in v["sentence"] and "504" in v["sentence"] and "171" in v["sentence"]
    v = tools.judge_area(row(255.6, 0.0, 0.0, 0.0), {"malapert": 0.0}, TARGETS)["malapert"]
    assert v["removed"] is True and "costs most" not in v["sentence"] and "256" in v["sentence"]


def test_unknown_stays_null_in_the_famous_figures():
    south = row(500.0, None, 70.0, "high", hemisphere="S", rock=185.0)
    verdict = tools.judge_area(south, {"malapert": None}, TARGETS)["malapert"]
    assert verdict["hours"]["snow"] == 185.0                  # the rock season stands in for the snow step
    assert verdict["hours"]["cloud"] is None                  # not known: null, never 0
    out_of_search = row(None, None, None, None)
    out_of_search["in_the_search"] = False
    verdict = tools.judge_area(out_of_search, {"malapert": None}, TARGETS)["malapert"]
    assert verdict["step"] is None and set(verdict["hours"].values()) == {None}


def test_a_lower_latitude_site_gets_its_sun_only_figures():
    site = {"name": "Mauna Kea", "lat": 19.8, "lon": -155.5, "kind": "classic lower-latitude analog site",
            "targets": {"malapert": {"hours_a_year_in_band": 330.0, "longest_spell_minutes": 31, "longest_spell_h": 0.52,
                                     "hours_in_spells_of_2h": 0.0, "has_a_2h_spell": False}}}
    verdict = tools.judge_latitude(site, TARGETS)["malapert"]
    assert verdict["step"] == "sun" and verdict["hours_a_year_in_band"] == 330.0 and verdict["longest_spell_minutes"] == 31
    assert "330 hours" in verdict["sentence"] and "31 minutes" in verdict["sentence"]


# ---- the full run on the files on disk ----

@needs_data
def test_a_full_run_writes_every_file_and_an_index(run):
    out, report = run
    assert not report["failed"], report["failed"]
    for name in JSON_OUTPUTS + ["access.bin"]:
        if name in report["left_out"]:
            continue
        assert (out / name).exists(), name
    index = read(out, "tools.json")
    for name in index["files"]:
        assert (out / name).stat().st_size == index["files"][name]["bytes"]
        assert index["files"][name]["layout"] and index["files"][name]["from"]
    assert index["areas"]["count"] == len(read(SITE_DATA, "cells.json")["ids"])
    for label, stamp in index["sources_written"].items():
        assert stamp is None or "modified" in stamp


@needs_data
def test_the_binary_file_has_the_pages_area_count_and_order(run):
    out, report = run
    if "access.bin" in report["left_out"]:
        pytest.skip("access_cells.json is not on disk")
    ids = read(SITE_DATA, "cells.json")["ids"]
    table = np.frombuffer((out / "access.bin").read_bytes(), dtype="<u2").reshape(-1, 4)
    assert table.shape[0] == len(ids)
    fields = read(out, "airfields.json")["airfields"]
    access = json.loads((DERIVED / "access_cells.json").read_text())["cells"]
    for position, area_id in enumerate(ids):
        record = access[area_id]
        for column, key in ((0, "nearest_scheduled"), (2, "nearest")):
            field = record.get(key)
            if field is None:
                assert table[position, column] == 65535 and table[position, column + 1] == 65535
            else:
                assert fields[table[position, column]]["ident"] == field["ident"]
                assert table[position, column + 1] == int(math.floor(field["km"] + 0.5))
    layout = read(out, "tools.json")["files"]["access.bin"]["layout"]
    assert layout["shape"] == [len(ids), 4] and layout["unknown"] == 65535


@needs_data
def test_every_figure_in_famous_equals_its_source(run):
    out, _ = run
    famous = read(out, "famous.json")
    extras = json.loads((DERIVED / "validation_extras.json").read_text())
    scored = {c["id"]: c for c in json.loads((DERIVED / "cells_scored.json").read_text())["cells"]}
    lower = {s["name"]: s for s in extras["lower_latitude_sites"]["sites"]}
    checked = 0
    for site in famous["sites"]:
        source = site["source"]
        assert source["file"] == "data/derived/validation_extras.json"      # on today's files every site is in it
        row = extras
        for step in source["list"].split("."):
            row = row[step]
        row = row[source["row"]]
        assert row["name"] == site["name"]
        for target, v in site["targets"].items():
            if site["basis"] == "latitude":
                src = row["targets"][target]
                for key in ("hours_a_year_in_band", "longest_spell_minutes", "hours_in_spells_of_2h", "has_a_2h_spell"):
                    assert v[key] == src[key], (site["name"], target, key)
                    checked += 1
                continue
            src = row["targets"][target]
            south = site["hemisphere"] == "S"
            assert v["hours"]["sun"] == src["long_flat_hours"]
            assert v["hours"]["snow"] == (src["flat_horizon_hours"] if south else src["long_snow_free_hours"])
            assert v["hours"]["hills"] == src["long_open_hours"]
            for key in ("percentile_among_ranked", "rank_from_top", "ranked_cells", "verdict"):
                assert v[key] == src[key]
            cell = scored.get(site["area"])
            field = "long_summer_rock_open_hours_clear" if south else "long_open_hours_clear"
            assert v["hours"]["cloud"] == (cell["targets"][target][field] if cell else None)
            checked += 8
    assert checked > 100
    assert {s["name"] for s in famous["sites"] if s["basis"] == "latitude"} == set(lower)
    named = {s["name"] for s in json.loads((DERIVED / "validation.json").read_text())["named_sites"]["sites"]}
    listed = {s["name"] for s in famous["sites"]} | {n for s in famous["sites"] for n in s.get("other_names", [])}
    assert named <= listed


@needs_data
def test_every_famous_site_says_what_its_figures_are_for(run):
    out, _ = run
    for site in read(out, "famous.json")["sites"]:
        assert site["basis"] in ("area", "latitude")
        assert site["basis_text"]
        for v in site["targets"].values():
            assert v["step"] in (None, "sun", "snow", "hills", "cloud", "holds-up")
            assert v["sentence"] is None or words(v["sentence"]) <= 25


@needs_data
def test_every_figure_in_winter_leads_equals_its_source(run):
    out, report = run
    if "winter_leads.json" in report["left_out"]:
        pytest.skip("winter_leads.json is not on disk")
    written = read(out, "winter_leads.json")
    source = json.loads((DERIVED / "winter_leads.json").read_text())["targets"]
    for target in written["targets"]:
        src = source[target["id"]]
        expected = {l["id"]: l for l in src["leads"] if l.get("at_main_floor") and (l.get("snow") or {}).get("status") == "measured"}
        assert {l["id"] for l in target["leads"]} == set(expected)
        for lead in target["leads"]:
            s = expected[lead["id"]]
            for key in ("lat", "lon", "region", "bare_km2", "winter_hours_flat", "winter_hours_snow_free",
                        "winter_hours_after_terrain"):
                assert lead[key] == s[key], (lead["id"], key)
            assert lead["best_ten_day_periods"] == s["best_ten_day_periods"]
        assert target["counts_by_region"] == src["counts_by_region"]
        assert target["counts_by_region_after_terrain"] == src["counts_by_region_after_terrain"]
    assert written["cautions"] and all(words(c) <= 25 for c in written["cautions"])


@needs_data
def test_every_tour_caption_is_filled_and_short(run):
    out, _ = run
    tour = read(out, "tour.json")
    assert 1 <= len(tour["steps"]) <= 8
    total = 0
    for step in tour["steps"]:
        caption = step["caption"]
        assert "{" not in caption and "}" not in caption and "None" not in caption and "nan" not in caption
        assert words(caption) <= 25
        assert set(step["state"]) <= {"view", "target", "step", "period", "place", "tab", "go", "moon"}
        assert step["fragment"].startswith("view=") or step["fragment"].startswith("go=")
        total += step["seconds"]
    assert total == tour["total_seconds"] and 50 <= total <= 70


@needs_data
def test_the_search_index_is_small_lower_cased_and_without_duplicates(run):
    out, _ = run
    path = out / "search.json"
    assert path.stat().st_size < 300_000
    index = read(out, "search.json")
    cols = index["columns"]
    seen = set()
    ids = set(read(SITE_DATA, "cells.json")["ids"])
    kinds = set()
    for entry in index["entries"]:
        e = dict(zip(cols, entry))
        kinds.add(index["kinds"][e["kind"]])
        assert e["key"] == e["key"].lower() and e["key"].isascii()
        assert (e["ascii"] or e["name"]).isascii()
        assert (e["kind"], e["key"]) not in seen
        seen.add((e["kind"], e["key"]))
        assert e["area"] is None or e["area"] in ids
    assert {"named site", "place", "Earth region", "lunar region"} <= kinds
    names = {dict(zip(cols, e))["name"] for e in index["entries"]}
    for place in read(SITE_DATA, "places.json")["places"]:
        assert place["name"] in names


@needs_data
def test_the_basis_takes_its_check_figures_from_checks_json(run):
    out, _ = run
    basis = read(out, "basis.json")
    checks = json.loads((DERIVED / "checks.json").read_text())
    assert basis["check_figures"]["recount_largest_difference_h_a_year"] == checks["independent_recount"]["largest_difference_h_a_year"]
    assert basis["check_figures"]["horizons_median_abs_difference_pct"] == checks["jpl_horizons"]["all_hours"]["median_abs_difference_pct"]
    assert len(basis["steps"]) == 4 and basis["assumptions"]


@needs_data
def test_the_glossary_has_the_nine_terms(run):
    out, _ = run
    terms = {t["term"] for t in read(out, "glossary.json")["terms"]}
    assert terms == {"spell", "ten-day period", "Sun ceiling", "horizon", "snow-free odds", "rock season", "anorthosite",
                     "area", "lunar region"}


@needs_data
def test_no_sentence_in_any_file_is_over_25_words(run, run_without_optional):
    for out in (run[0], run_without_optional[0]):
        for name in JSON_OUTPUTS:
            if not (out / name).exists():
                continue
            for text in strings(read(out, name)):
                for sentence in sentences(text):
                    assert words(sentence) <= 25, (name, sentence)


@needs_data
def test_the_run_goes_on_without_the_optional_inputs_and_says_what_it_left_out(run_without_optional):
    out, report = run_without_optional
    assert not report["failed"], report["failed"]
    for name in ("access.bin", "airfields.json", "winter_leads.json"):
        assert name in report["left_out"] and not (out / name).exists()
    basis = read(out, "basis.json")
    assert basis["check_figures"] == {"recount_largest_difference_h_a_year": None, "horizons_median_abs_difference_pct": None}
    index = read(out, "tools.json")
    left = {entry["file"] for entry in index["left_out"]}
    assert {"access.bin", "airfields.json", "winter_leads.json"} <= left
    lacking = {entry["input"] for entry in index["written_without"]}
    assert {"data/derived/checks.json", "data/derived/access_cells.json"} <= lacking
    search = read(out, "search.json")
    assert "airfield" not in {search["kinds"][e[search["columns"].index("kind")]] for e in search["entries"]}
    for name in ("famous.json", "basis.json", "search.json", "glossary.json", "tour.json"):
        assert (out / name).exists()

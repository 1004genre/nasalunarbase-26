# Written with an AI assistant; see README.md, section 'How AI was used'.
"""The Mars page preserves the source numbers, missing values and export limits."""

import copy
import importlib
import json
import re
import struct
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
EXPORTER = importlib.import_module("scripts.export_site_mars")


@pytest.fixture(scope="module")
def source():
    def read(relative):
        return json.loads((ROOT / relative).read_text())

    return {
        "sites_doc": read("data/derived/mars_sites.json"),
        "cells_doc": read("data/derived/mars_cells.json"),
        "validation_doc": read("data/derived/mars_validation.json"),
        "moon_doc": read("data/derived/moon_cards.json"),
        "land_doc": read("data/raw/naturalearth/ne_50m_land.geojson"),
    }


@pytest.fixture(scope="module")
def exported(source):
    files = EXPORTER.build_export(**source)
    return files, json.loads(files["mars.json"])


def numbers(value, path=()):
    if isinstance(value, bool):
        return
    if isinstance(value, (int, float)):
        yield path, value
    elif isinstance(value, dict):
        for key, inner in value.items():
            yield from numbers(inner, path + (key,))
    elif isinstance(value, list):
        for index, inner in enumerate(value):
            yield from numbers(inner, path + (index,))


def at(value, path):
    for step in path:
        value = value[step]
    return value


def decode(files, manifest, field, index):
    spec = manifest["squares"]["columns"][field]
    formats = {"uint8": "B", "uint16": "H", "uint32": "I", "int16": "h", "int32": "i", "float64": "d"}
    fmt = "<" + formats[spec["type"]]
    raw = struct.unpack_from(fmt, files["mars_squares.bin"], spec["offset"] + index * struct.calcsize(fmt))[0]
    if raw == spec["unknown"] or (spec["type"] == "float64" and raw != raw):
        return None
    return raw / spec["scale"]


def test_all_site_card_and_top_list_numbers_match_source(source, exported):
    _, manifest = exported
    for original, written in zip(source["sites_doc"]["sites"], manifest["sites"], strict=True):
        for path, value in numbers(original):
            if path[0] != "best_places":
                assert at(written, path) == value, (original["id"], path)
    assert manifest["best_places"] == source["cells_doc"]["best_places"]


def test_every_binary_value_matches_source_including_unknown(source, exported):
    files, manifest = exported
    unknown_count = 0
    for index, cell_id in enumerate(manifest["squares"]["ids"]):
        original = source["cells_doc"]["cells"][cell_id]
        for field in manifest["squares"]["columns"]:
            if "best_month" in field or field == "region":
                continue
            expected = at(original, field.split("."))
            actual = decode(files, manifest, field, index)
            assert actual == expected, (cell_id, field, expected, actual)
            unknown_count += expected is None
        region = decode(files, manifest, "region", index)
        assert manifest["squares"]["regions"][int(region)] == original["region"]
        for site_id, score in original["sites"].items():
            prefix = f"sites.{site_id}."
            count = decode(files, manifest, prefix + "best_months_count", index)
            assert count == len(score["best_months"])
            actual_months = [manifest["squares"]["months"][int(decode(files, manifest, prefix + f"best_month_{n}", index))] for n in range(int(count))]
            assert actual_months == score["best_months"]
    assert unknown_count > 0


def test_missing_optional_fields_are_unknown_and_reported(source):
    small = copy.deepcopy(source)
    cell_id, cell = next(iter(small["cells_doc"]["cells"].items()))
    small["cells_doc"]["cells"] = {cell_id: cell}
    del cell["pressure_kpa"]
    site_id = small["sites_doc"]["sites"][0]["id"]
    del cell["sites"][site_id]["best_months"]
    del small["sites_doc"]["sites"][0]["climate"]["annual_mean_c"]
    files = EXPORTER.build_export(**small)
    manifest = json.loads(files["mars.json"])
    assert decode(files, manifest, "pressure_kpa", 0) is None
    assert decode(files, manifest, f"sites.{site_id}.best_months_count", 0) is None
    assert manifest["sites"][0]["climate"]["annual_mean_c"] is None
    assert any("pressure_kpa" in warning for warning in manifest["warnings"])
    assert any("best_months" in warning for warning in manifest["warnings"])
    assert any("annual_mean_c" in warning for warning in manifest["warnings"])


def test_zero_is_not_confused_with_unknown(source, exported):
    files, manifest = exported
    site_id = manifest["sites"][0]["id"]
    index = next(index for index, cell_id in enumerate(manifest["squares"]["ids"])
                 if source["cells_doc"]["cells"][cell_id]["sites"][site_id]["dry"] == 0
                 and source["cells_doc"]["cells"][cell_id]["sites"][site_id]["terrain"] is None)
    assert decode(files, manifest, f"sites.{site_id}.dry", index) == 0
    assert decode(files, manifest, f"sites.{site_id}.terrain", index) is None


def test_export_is_small_and_world_rings_are_closed(exported):
    files, _ = exported
    assert sum(len(content) for content in files.values()) < 3_000_000
    assert len(files["mars_world.json"]) < 400_000
    world = json.loads(files["mars_world.json"])
    assert world["type"] == "MultiPolygon"
    for polygon in world["coordinates"]:
        for ring in polygon:
            assert len(ring) >= 4
            assert ring[0] == ring[-1]


def test_locators_use_exact_source_coordinates(source, exported):
    _, manifest = exported
    for card, point in zip(source["moon_doc"]["cards"], manifest["locators"]["moon"], strict=True):
        assert point["lat"] == card["centre"]["lat"]
        assert point["lon_east"] == card["centre"]["lon_east"]
    for card, point in zip(source["sites_doc"]["sites"], manifest["locators"]["mars"], strict=True):
        assert point["lat"] == card["lat"]
        assert point["lon_east"] == card["lon_east"]


def test_no_picture_is_invented_and_export_is_repeatable(source, exported):
    files, manifest = exported
    for original, written in zip(source["sites_doc"]["sites"], manifest["sites"], strict=True):
        if "picture" not in original:
            assert "picture" not in written
        assert written["kind"] == original["kind"]
    assert EXPORTER.build_export(**source) == files


def test_unverified_evidence_cautions_and_status_are_preserved(exported):
    _, manifest = exported
    assert "first pass" in manifest["meta"]["first_pass"]
    assert "coarser" in manifest["meta"]["first_pass"]
    assert "does not show" in " ".join(manifest["meta"]["validation_caution"])
    for site in manifest["sites"]:
        for item in site["cannot_match"]:
            if "ultraviolet" in item["what"] or "ionising" in item["what"]:
                assert "not checked" in item["source"]
            if "dusty" in item["what"]:
                assert "not checked" in item["note"]
        if site["kind"] != "visited by a NASA mission":
            assert "candidate" in site["display_status"]


def test_personal_attribution_is_not_exported(source, exported):
    _, manifest = exported
    for original, site in zip(source["sites_doc"]["sites"], manifest["sites"], strict=True):
        if " Landing)" in original["name"]:
            assert " Landing)" not in site["name"]
        assert "et al." not in json.dumps(site)
    # A synthetic attribution exercises compound surnames without naming a person.
    assert EXPORTER.without_personal_attribution("Example, OtherName and Third 2025, abstract 1002") == "Study published in 2025, abstract 1002"


def test_provenance_and_scientific_prose_survive_name_removal(source, exported):
    _, manifest = exported
    for original, written in zip(source["sites_doc"]["sites"], manifest["sites"], strict=True):
        assert written["why"].startswith(original["why"].split(" (")[0])
    for original, written in zip(source["validation_doc"]["sites"], manifest["validation"]["sites"], strict=True):
        assert written.get("bare_source") == original.get("bare_source")
    for label in ("ESA WorldCover 2021", "NASA POWER 2025", "ETOPO 2022", "Mars Climate Database v6.2"):
        assert EXPORTER.without_personal_attribution(label) == label


def test_textual_measurements_are_not_deleted(source, exported):
    _, manifest = exported

    def strings(value, path=()):
        if isinstance(value, str):
            yield path, value
        elif isinstance(value, dict):
            for key, inner in value.items():
                if key != "best_places":
                    yield from strings(inner, path + (key,))
        elif isinstance(value, list):
            for index, inner in enumerate(value):
                yield from strings(inner, path + (index,))

    def numeric_tokens(text):
        # Citation filenames and URLs are provenance identifiers, not figures.
        text = re.sub(r"(?:https?://|data/)[^\s)]+", "", text)
        return re.findall(r"\d+(?:[.,]\d+)*", text)

    for original, written in zip(source["sites_doc"]["sites"], manifest["sites"], strict=True):
        for path, value in strings(original):
            assert numeric_tokens(at(written, path)) == numeric_tokens(value), (original["id"], path)


def test_short_rationales_are_plain_and_update_safely(source, exported):
    _, manifest = exported
    for card in manifest["sites"]:
        assert card["why_sentences"]
        for sentence in card["why_sentences"]:
            assert len(sentence.split()) <= 25
            assert sentence.endswith(".")
            assert not re.search(r"\d|selected|chosen", sentence)
    changed = copy.deepcopy(source)
    changed["sites_doc"]["sites"][0]["why"] = "The saved rationale has changed."
    manifest = json.loads(EXPORTER.build_export(**changed)["mars.json"])
    assert "why_sentences" not in manifest["sites"][0]
    assert any("rationale changed" in warning for warning in manifest["warnings"])


def test_extra_precision_falls_back_without_losing_unknown_or_zero():
    values = [None, 0, 0.123456789123456]
    payload, spec = EXPORTER.encode_column(values)
    assert spec["type"] == "float64"
    assert spec["unknown"] == "NaN"
    spec["offset"] = 0
    manifest = {"squares": {"columns": {"test": spec}}}
    files = {"mars_squares.bin": payload}
    assert [decode(files, manifest, "test", index) for index in range(len(values))] == values

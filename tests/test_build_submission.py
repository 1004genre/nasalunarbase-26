# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""The text for the Space Apps form (scripts/build_submission.py). No test touches the network.

Written with SI assistance (Claude, by Anthropic, through Claude Code).
"""
import copy
import importlib
import re
from datetime import datetime
from pathlib import Path

import pytest

build = importlib.import_module("scripts.build_submission")

REAL_FILES = [build.DERIVED / name for name in build.REQUIRED.values()] + [build.TEMPLATE]
needs_data = pytest.mark.skipif(not all(path.exists() for path in REAL_FILES),
                                reason="the data files or the template are not here")
WHEN = datetime(2026, 11, 14, 18, 30)

CANDIDATES = [
    "Earth copies the Moon's south-pole Sun only at the edge of the midnight Sun. Here is where and when.",
    "Winter has the right Sun but the ground is under snow. Summer nights are the real rehearsal season.",
    "The harder the lunar site, the less of Earth can copy it. The ridge by Shackleton has almost no twin.",
    "NASA rehearses south-pole light at night with one lamp. We show where and when the real Sun does it over "
    "kilometres of bare ground.",
]


# ---------------------------------------------------------------- filling

def test_a_placeholder_with_no_value_and_no_fallback_stops_the_build():
    with pytest.raises(build.MissingValue, match="areas_unknown") as caught:
        build.fill("We searched {areas_total} areas and {areas_unknown} more, {also_unknown}.", {"areas_total": "16"})
    assert "also_unknown" in str(caught.value) and "areas_total" not in str(caught.value)


def test_a_value_of_none_counts_as_no_value():
    with pytest.raises(build.MissingValue):
        build.fill("{x}", {"x": None})


def test_a_fallback_is_used_only_when_the_value_is_missing():
    assert build.fill("{a} and {b}", {"a": "1"}, {"a": "no", "b": build.NOT_YET}) == "1 and [not yet measured]"


def test_every_placeholder_is_replaced_and_repeats_are_filled_too():
    assert build.fill("{a}, {a} and {b_2}", {"a": "x", "b_2": "y"}) == "x, x and y"
    assert build.placeholders_in("{a}, {a} and {b_2}") == ["a", "b_2"]


# ---------------------------------------------------------------- optional files

def test_a_missing_optional_file_gives_not_yet_measured_and_never_a_number():
    values, notes = build.values_access({"access": None, "scored": {"cells": []}})
    assert set(values.values()) == {build.NOT_YET} and "access_cells.json" in notes[0]
    values, notes = build.values_winter_leads({"winter_leads": None})
    assert set(values.values()) == {build.NOT_YET} and "winter_leads.json" in notes[0]
    checks = build.values_checks({"count_check": None, "snow_check": None})
    for key in ("recount_areas", "recount_largest_difference", "snow_stations", "snow_bias_winter", "snow_bias_summer"):
        assert checks[key] == build.NOT_YET


def test_an_optional_file_of_another_shape_gives_not_yet_measured_and_a_note():
    values, notes = build.values_winter_leads({"winter_leads": {"meta": {}, "something_else": 3}})
    assert set(values.values()) == {build.NOT_YET}
    assert "could not be read as expected" in notes[0]
    values, notes = build.values_access({"access": {"meta": {}}, "scored": {"cells": []}})
    assert set(values.values()) == {build.NOT_YET} and "could not be read as expected" in notes[0]


def scored_cell(cid, hours, lighting, region="Arctic Canada"):
    target = {"long_open_hours": hours, "goals": {"lighting": lighting}}
    return {"id": cid, "ranked": True, "ranking": "north", "region": region,
            "targets": {"malapert": target, "nobile-rim-2": dict(target)}}


def test_reachable_places_are_counted_by_the_runway_with_scheduled_flights():
    def runway(km, name="Somewhere Airport"):
        return {"nearest_scheduled": None if km is None else {"km": km, "name": name}, "nearest": None, "country": "CA"}

    cells = [scored_cell("near", 150.0, 0.8), scored_cell("best", 180.0, 0.9), scored_cell("far", 300.0, 1.0),
             scored_cell("unknown", 250.0, 1.0), scored_cell("dim", 99.0, 0.99), scored_cell("absent", 200.0, 1.0)]
    access = {"meta": {"source": {"name": "OurAirports, airports.csv", "licence": "public domain", "url": "https://example.org/a.csv"}},
              "cells": {"near": runway(40.0), "best": runway(99.9, "Gjoa Haven Airport"), "far": runway(100.1),
                        "unknown": runway(None), "dim": runway(5.0)}}
    values, notes = build.values_access({"access": access, "scored": {"cells": cells}})
    assert notes == []
    text = values["access_text"]
    assert "5 areas in our northern ranking have 100 hours or more" in text      # "dim" has 99 hours
    assert "Of these, 2 lie within 100 km" in text                               # unknown and absent are not counted as near
    assert "Gjoa Haven Airport, about 100 km away" in text or "Gjoa Haven Airport, 100 km away" in text
    assert "about 180 hours a year" in text
    assert values["access_reference_line"] == "OurAirports, airports.csv (public domain): https://example.org/a.csv"
    assert build.long_sentences(text) == []


def test_small_bare_patches_merge_the_norwegian_counties_and_show_the_rim():
    leads = {"meta": {"floor_bare_km2": 1.0},
             "targets": {"nobile-rim-2": {
                 "counts_by_region": {"50": {}, "100": {"Iceland": 50, "Norway: Vestland": 5, "Norway: Troms": 8,
                                                         "Faroe Islands": 1, "Orkney": 0}},
                 "counts_by_region_after_terrain": {"50": {}, "100": {"Iceland": 24}}}}}
    values, notes = build.values_winter_leads({"winter_leads": leads})
    assert notes == []
    text = values["winter_leads_text"]
    assert "64 more areas hold at least 1 km2 of bare ground" in text
    assert "By region: Iceland 50, Norway 13, Faroe Islands 1." in text
    assert "Shetland 0, Orkney 0, Faroe Islands 1." in text
    assert "24 keep 100 hours: Iceland 24." in text
    assert build.long_sentences(text) == []


def test_a_missing_required_file_stops_loudly(tmp_path, capsys):
    with pytest.raises(build.MissingInput, match="validation.json"):
        build.load_inputs(tmp_path)
    template = tmp_path / "t.md"
    template.write_text("x")
    assert build.main(["--derived", str(tmp_path), "--template", str(template), "--out", str(tmp_path / "S.md")]) == 1
    assert "STOPPED" in capsys.readouterr().err and not (tmp_path / "S.md").exists()


def test_a_required_file_of_another_shape_stops_loudly_and_writes_nothing(tmp_path, capsys):
    for name in build.REQUIRED.values():
        (tmp_path / name).write_text("{}")
    template = tmp_path / "t.md"
    template.write_text("{areas_total}")
    assert build.main(["--derived", str(tmp_path), "--template", str(template), "--out", str(tmp_path / "S.md")]) == 1
    assert "STOPPED" in capsys.readouterr().err and not (tmp_path / "S.md").exists()


# ---------------------------------------------------------------- numbers and dates

def test_numbers_are_rounded_honestly():
    assert build.approx(7353) == "about 7,400"
    assert build.approx(16184) == "about 16,000"
    assert build.approx(695226.7) == "about 700,000"
    assert build.approx(16) == "16" and build.approx(0) == "0" and build.approx(76.9) == "77"
    assert build.exact(16184) == "16,184"
    assert build.trim(57.65) == "57.65" and build.trim(64.8) == "64.8" and build.trim(60.0) == "60"
    assert build.pct(0.565) in ("56", "57") and build.pct(0.0056, 1) == "0.6"
    assert build.count_word(4, 4) == "all four" and build.count_word(3, 4) == "three of the four"
    assert build.count_word(0, 4) == "none of the four"


def test_ten_day_periods_are_named_as_in_the_results_file():
    assert build.bin_first_day(0) == "1 January" and build.bin_last_day(0) == "10 January"
    assert build.bin_first_day(18) == "30 June" and build.bin_last_day(18) == "9 July"
    assert build.bin_first_day(21) == "30 July" and build.bin_last_day(23) == "28 August"
    assert build.bin_first_day(35) == "17 December" and build.bin_last_day(35) == "31 December"


def test_regions_are_listed_largest_first_and_the_rest_summed():
    counts = {"Iceland": 40, "Norway": 3, "Alaska": 6, "Faroe Islands": 1, "Svalbard": 2, "Orkney": 0}
    assert build.regions_text(counts) == "Iceland 40, Alaska 6, Norway 3, Svalbard 2, other regions 1"


# ---------------------------------------------------------------- sentences

def test_sentences_are_split_at_full_stops_and_a_list_item_starts_afresh():
    text = "## A heading\n\nOne two three. Four five? Six seven!\n\n- A list item of five words.\n1. Numbered one. And two."
    assert build.sentences(text) == ["A heading", "One two three.", "Four five?", "Six seven!",
                                     "A list item of five words.", "Numbered one.", "And two."]


def test_a_decimal_number_and_a_link_do_not_end_a_sentence_and_a_link_is_one_word():
    line = "The Sun stays below 2.08 degrees: https://pgda.gsfc.nasa.gov/products/78 says so."
    assert build.sentences(line) == ["The Sun stays below 2.08 degrees: URL says so."]
    assert build.word_count("The Sun stays below 2.08 degrees: URL says so.") == 9
    assert build.word_count("- | ** --") == 0


def test_table_cells_are_separate_and_the_rule_row_is_ignored():
    table = "| Field | Limit |\n|---|---|\n| Project Name | limit not confirmed |"
    assert build.sentences(table) == ["Field", "Limit", "Project Name", "limit not confirmed"]


def test_a_sentence_of_26_words_is_caught_and_one_of_25_is_not():
    words = ["word"] * 25
    assert build.long_sentences(" ".join(words) + ".") == []
    found = build.long_sentences("Short one. " + " ".join(words + ["more"]) + ".")
    assert len(found) == 1 and found[0][0] == 26


def test_exact_credit_lines_are_left_out_until_the_next_heading():
    long_credit = "Menne and " + " and ".join(["Author"] * 30) + ", 2012: a very long title."
    text = f"## 8c. Exact credit lines, as asked\n\n- {long_credit}\n\n## 9. Next\n\nA short one."
    assert build.long_sentences(text) == []
    assert "A short one." in build.sentences(text)
    assert build.long_sentences(f"## 8b. Other references\n\n- {long_credit}") != []     # only the marked section is exempt


def test_gaps_are_found_with_the_heading_they_stand_under():
    text = "## One\n\n[LINK TO THE DEMO] and [Data Set] and [14 November 2026].\n\n## Two\n\n[not yet measured] [LINK TO THE DEMO]"
    assert build.team_gaps(text) == [("[LINK TO THE DEMO]", ["One", "Two"]), ("[not yet measured]", ["Two"])]


def test_the_check_refuses_braces_long_sentences_and_a_long_summary():
    good = ("A. \"Lead one.\"\n\n*BEGIN TEXT FOR THE FORM: summary*\n\n" + build.LEAD_GAP + "\n\nShort text.\n\n"
            "*END TEXT FOR THE FORM: summary*\n\n*BEGIN TEXT FOR THE FORM: summary, short version*\n\nShorter.\n\n"
            "*END TEXT FOR THE FORM: summary, short version*\n")
    assert build.form_text(good, "summary") == build.LEAD_GAP + "\n\nShort text."
    assert build.form_text(good, "summary, short version") == "Shorter."
    with pytest.raises(build.OutputCheckFailed, match="no block"):
        build.form_text(good, "description")
    build.check_output(good)
    with pytest.raises(build.OutputCheckFailed, match="curly braces"):
        build.check_output(good + "\nA {left_over} one.")
    with pytest.raises(build.OutputCheckFailed, match="over 25 words"):
        build.check_output(good + "\n" + " ".join(["word"] * 26) + ".")
    long_summary = good.replace("Short text.", " ".join(["Six words are in this sentence."] * 30))
    with pytest.raises(build.OutputCheckFailed, match="short summary"):
        build.check_output(long_summary)


# ---------------------------------------------------------------- the real template and the real data

@pytest.fixture(scope="module")
def inputs():
    return build.load_inputs(build.DERIVED)


@pytest.fixture(scope="module")
def template():
    return build.TEMPLATE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def built(inputs, template):
    return build.build(template, inputs, WHEN)[0]


@needs_data
def test_every_placeholder_of_the_template_has_a_value(inputs, template):
    values, _ = build.compute_values(inputs, WHEN)
    known = {name for name in values if not name.startswith("_")} | {"team_gaps"}
    assert [name for name in build.placeholders_in(template) if name not in known] == []
    assert all(isinstance(value, str) and value for name, value in values.items() if not name.startswith("_"))


@needs_data
def test_no_curly_brace_is_left(built):
    assert "{" not in built and "}" not in built


@needs_data
def test_every_sentence_has_25_words_or_fewer(built):
    assert build.long_sentences(built) == []
    assert len(build.sentences(built)) > 200          # the check really read the text


@needs_data
def test_the_form_text_avoids_abbreviations_that_would_fool_the_sentence_count(built):
    for name in ("summary", "description", "SI"):
        text = build.form_text(built, name)
        assert not re.search(r"\b(e\.g\.|i\.e\.|etc\.|et al\.|approx\.|vs\.)", text), name


@needs_data
def test_the_four_lead_sentences_are_offered_as_given(built):
    assert build.lead_candidates(built) == CANDIDATES
    assert "the team's choice" in built and build.LEAD_GAP in build.form_text(built, "summary")


@needs_data
def test_the_short_summary_is_within_its_limit_with_any_lead_sentence(built):
    summary = build.form_text(built, "summary")
    for lead in CANDIDATES:
        whole = summary.replace(build.LEAD_GAP, lead)
        assert build.word_count(whole) <= build.SUMMARY_MAX_WORDS, lead
        assert len(whole) <= build.SUMMARY_MAX_CHARS, lead
    short = build.form_text(built, "summary, short version")
    assert build.word_count(short) <= 60


@needs_data
def test_the_description_answers_the_questions_in_the_asked_order(built):
    description = build.form_text(built, "description")
    headings = ["What the challenge asks, and what we chose", "Why light", "What the tool does", "What we found",
                "How it helps prepare for exploration", "How it works", "How we checked it",
                "What Earth cannot copy, and what we did not do", "What comes next"]
    places = [description.index("### " + heading) for heading in headings]
    assert places == sorted(places)


@needs_data
def test_wording_the_red_team_ruled_out_is_not_in_the_form_text(built):
    for name in ("summary", "summary, short version", "description"):
        text = build.form_text(built, name)
        assert "only Iceland" not in text and "nobody" not in text.lower() and "no one else" not in text.lower()
        assert "base sites" not in text
        assert text.count("base site") == text.count("has not chosen a base site")
    description = build.form_text(built, "description")
    assert "candidate landing regions" in description
    assert "none maps the Sun's height at these regions onto Earth with hills and snow counted" in description
    assert "We have no Mars result." in description


@needs_data
def test_the_si_paragraph_says_who_did_what_and_is_marked_for_the_team_lead(built):
    section = built.split("## 6. Use of Super Intelligence (SI)")[1].split("## 7.")[0]
    assert "the team lead must check and finalise this paragraph" in section
    text = build.form_text(built, "SI")
    for phrase in ("Claude", "Anthropic", "Claude Code", "wrote all the code and all the tests", "proposed directions",
                   "The team chose the challenge.", "is responsible for the submission",
                   "Every chart is drawn by code from open data."):
        assert phrase in text, phrase
    assert "team wrote" not in text and "our own idea" not in text


@needs_data
def test_the_data_fields_follow_the_sources_file(built):
    nasa = build.form_text(built, "NASA data")
    for name in ("LOLA", "PGDA product 78", "PGDA product 69", "NASA POWER", "Diviner", "JPL Horizons"):
        assert name in nasa, name
    assert "WorldCover" not in nasa and "IMS" not in nasa
    partner = build.form_text(built, "partner data")
    assert "ESA WorldCover" in partner and "Copernicus DEM GLO-90" in partner and "NOAA" not in partner
    references = build.form_text(built, "references")
    numbers = [int(n) for n in re.findall(r"^(\d+)\. ", references, flags=re.MULTILINE)]
    assert numbers == list(range(1, len(numbers) + 1)) and len(numbers) >= 25
    numbered = [line for line in references.splitlines() if re.match(r"^\d+\. ", line)]
    assert all("http" in line or build.NOT_YET in line for line in numbered)
    assert "educational and non-commercial use only" in references and "Apache License 2.0" in references


@needs_data
def test_every_gap_in_the_text_is_listed_at_the_top(built):
    top = built.split("## For the team to fill in")[1].split("## Choose the lead sentence")[0]
    rest = built.split("## Choose the lead sentence")[1]
    gaps = [gap for gap, _ in build.team_gaps(rest)]
    assert gaps and all(gap in top for gap in gaps)
    assert build.LEAD_GAP in gaps and "[LINK TO THE DEMO]" in gaps and "[LINK TO THE PAGE]" in gaps


@needs_data
def test_no_person_path_or_address_is_in_the_text(built):
    assert "/Users/" not in built and "/private/" not in built and "/home/" not in built
    assert not re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", built)


@needs_data
def test_without_the_optional_files_the_text_says_not_yet_measured_and_still_passes(inputs, template):
    bare = dict(inputs, winter_leads=None, access=None, snow_check=None, count_check=None)
    text, notes = build.build(template, bare, WHEN)
    assert len(notes) == 4
    assert "{" not in text and build.long_sentences(text) == []
    description = build.form_text(text, "description")
    assert "3. Small bare patches escape that screen. [not yet measured]" in description
    assert "9. Some good places are near a runway. [not yet measured]" in description
    assert "8. [not yet measured]" in description
    assert "We compared the snow maps with [not yet measured] weather stations." in description
    assert "runway with scheduled flights" not in description and "Ulukhaktok" not in description
    top = text.split("## For the team to fill in")[1].split("## Choose the lead sentence")[0]
    assert "[not yet measured]" in top and "winter_leads.json is not there" in top


@needs_data
def test_words_the_data_no_longer_supports_stop_the_build(inputs, template):
    changed = dict(inputs, extras=copy.deepcopy(inputs["extras"]))
    changed["extras"]["lower_latitude_sites"]["summary"]["malapert"]["sites_with_a_2h_spell"] = 1
    with pytest.raises(build.ClaimNoLongerHolds, match="lower-latitude"):
        build.build(template, changed, WHEN)
    changed = dict(inputs, validation=copy.deepcopy(inputs["validation"]))
    changed["validation"]["terrain_share_left"]["north"]["blind_sample"]["malapert"]["median"] = 0.9
    with pytest.raises(build.ClaimNoLongerHolds, match="about half"):
        build.build(template, changed, WHEN)


@needs_data
def test_the_numbers_in_the_text_are_those_of_the_files(inputs, built):
    validation, profile = inputs["validation"], inputs["profile"]
    snow_left = inputs["extras"]["latitude_against_full_method"]["targets"]["malapert"]["winter_half"]["all_measured_cells"]
    assert f"Once snow is counted, {build.approx(snow_left['after_snow']['cells'])} are left." in built
    first = profile["thresholds"]["nobile-rim-2"]["N"]["lowest_lat_with_long_window"]["2"]
    assert f"begin at {build.trim(first)} degrees for Nobile Rim 2" in built
    sample = validation["terrain_share_left"]["north"]["blind_sample"]
    assert f"For Connecting Ridge it keeps {build.pct(sample['connecting-ridge']['median'])} percent." in built
    ceilings = [round(card["sun_ceiling"]["deg"], 2) for card in inputs["moon"]["cards"]]
    assert "at or below " + ", ".join(build.trim(c) for c in ceilings[:3]) + f" and {build.trim(ceilings[3])} degrees" in built
    assert f"squares of Arctic and Antarctic ground" in built
    assert f"We searched {build.approx(inputs['scored']['meta']['counts']['records'])} squares" in built


@needs_data
def test_main_writes_the_whole_file_and_leaves_no_part_file(tmp_path, capsys):
    out = tmp_path / "SUBMISSION.md"
    assert build.main(["--out", str(out)]) == 0
    text = out.read_text(encoding="utf-8")
    assert text.startswith("# LuniMartian Atlas") and "{" not in text
    assert not (tmp_path / "SUBMISSION.md.part").exists()
    assert "none over 25 words" in capsys.readouterr().out
    assert build.main(["--check", "--out", str(tmp_path / "other.md")]) == 0
    assert not (tmp_path / "other.md").exists()


WRITTEN = build.OUT


@pytest.mark.skipif(not WRITTEN.exists(), reason="SUBMISSION.md has not been written here")
def test_the_written_file_has_no_brace_and_no_long_sentence():
    text = WRITTEN.read_text(encoding="utf-8")
    assert "{" not in text and "}" not in text
    assert build.long_sentences(text) == []
    words, chars = build.summary_size(text)
    assert words <= build.SUMMARY_MAX_WORDS and chars <= build.SUMMARY_MAX_CHARS


# ---------------------------------------------------------------- the two checks, from data/derived/checks.json (final run)

HORIZONS_RECORD = {"places": [{"name": f"p{i}"} for i in range(9)],
                   "all_hours": {"median_abs_difference_pct": 0.113, "largest_abs_difference_pct": 6.346}}
RECOUNT_RECORD = {"cells": 16184, "outside_tolerance": 0, "largest_difference_h_a_year": 0.071}


def test_the_horizons_figures_are_no_longer_typed_in():
    assert not any(key.startswith("horizons_") for key in build.FIXED_FACTS)


def test_the_horizons_figures_are_read_from_checks_json_or_say_not_yet_measured():
    values = build.values_horizons({"checks": {"jpl_horizons": HORIZONS_RECORD}})
    assert values == {"horizons_agreement_pct": "0.1", "horizons_largest_pct": "6.3", "horizons_places": "nine"}
    for missing in ({"checks": None}, {"checks": {}}, {"checks": {"jpl_horizons": {"places": []}}}):
        assert set(build.values_horizons(missing).values()) == {build.NOT_YET}


def test_the_recount_is_read_from_checks_json_before_an_older_count_check_file():
    old = {"first_principles": {"cells": 16184, "largest_difference_h_a_year": 0.09, "outside_tolerance": 0}}
    values = build.values_checks({"checks": {"independent_recount": RECOUNT_RECORD}, "count_check": old, "snow_check": None})
    assert values["recount_areas"] == "16,184" and values["recount_largest_difference"] == "0.07"
    assert values["_recount_outside_tolerance"] == 0
    fallback = build.values_checks({"checks": None, "count_check": old, "snow_check": None})
    assert fallback["recount_largest_difference"] == "0.09"

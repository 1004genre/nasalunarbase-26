# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""scripts/make_results.py on the real files of data/derived: it runs, every section is there, and figures
picked from different tables equal the JSON they say they come from."""
import importlib
import json
import re
from pathlib import Path

import pytest

make_results = importlib.import_module("scripts.make_results")

DERIVED = Path("data/derived")
NEEDED = ("grazing_cells.json", "grazing_bins.npz", "cells_scored.json", "validation.json", "latitude_profile.json",
          "candidates.json", "cloud_cells.json", "ranking.txt", "validation_v2.json", "cells_scored_v2.json")


@pytest.fixture(scope="module")
def built():
    missing = [name for name in NEEDED if not (DERIVED / name).exists()]
    if missing:
        pytest.skip(f"the chain has not been run: {missing} not in data/derived")
    lines, numbers = make_results.build()
    return "\n".join(lines) + "\n", numbers


def load(name):
    return json.loads((DERIVED / name).read_text())


def section(text: str, letter: str) -> str:
    """The text of one lettered section, from its heading to the next heading of the same level."""
    start = text.index(f"\n## ({letter}) ")
    end = text.find("\n## ", start + 1)
    return text[start:end if end != -1 else len(text)]


def rows_of(text: str, first_cell: str) -> list[list[str]]:
    """The table rows whose first cell is first_cell, as lists of cell texts."""
    return [[cell.strip() for cell in line.strip().strip("|").split("|")]
            for line in text.split("\n") if line.startswith(f"| {first_cell} |")]


def whole(text: str) -> int:
    return int(text.replace(",", ""))


def test_it_runs_on_the_real_files(built):
    text, numbers = built
    assert len(text) > 30000 and text.startswith("# LuniMartian Atlas")
    assert len(numbers) > 100 and all(set(n) == {"label", "value", "how"} for n in numbers)
    assert not re.search(r"\bnan\b|\binf\b|Infinity|None", text)      # unknown is written n/a


def test_every_section_heading_is_present(built):
    text, _ = built
    headings = re.findall(r"^## (.+)$", text, flags=re.M)
    assert headings[0] == "How to read this" and headings[-1] == "Files"
    assert [h[:3] for h in headings[1:-1]] == [f"({letter})" for letter in "abcdefghijklm"]
    assert headings[1:-1] == [f"({letter}) {title}" for letter, title in make_results.SECTIONS]
    for wanted in ("### What this match is and is not", "### Lowest latitude with spells of 1, 2 and 3 hours",
                   "### What was searched"):
        assert wanted in text


def test_the_winter_count_in_b_equals_validation_json(built):
    text, _ = built
    counts = load("validation.json")["big_picture_north"]["targets"]["malapert"]["long_snow_free_hours"]["winter_half"]
    row = rows_of(section(text, "b"), "Malapert")[0]
    assert whole(row[2].split(" cells")[0]) == counts["100"]["cells"]
    assert whole(row[1].split(" cells")[0]) == counts["50"]["cells"]


def test_the_two_hour_threshold_in_a_equals_latitude_profile_json(built):
    text, _ = built
    found = load("latitude_profile.json")["thresholds"]["malapert"]["N"]
    row = rows_of(section(text, "a"), "Malapert Massif (≤ 5.55°)")
    assert float(row[0][2].split(" N")[0]) == found["lowest_lat_with_long_window"]["2"]              # the per-day rule
    assert float(row[1][2].split(" N")[0]) == found["lowest_lat_with_long_window_bin_median"]["2"]   # the version 2 rule


def test_the_clear_sky_count_in_j_equals_validation_json(built):
    text, _ = built
    target = load("validation.json")["big_picture_north"]["targets"]["malapert"]
    with_cloud = target["long_open_hours_clear_among_cells_with_a_horizon"]["summer_half"]
    without = target["long_open_hours_among_cells_with_a_horizon"]["summer_half"]
    row = rows_of(section(text, "j"), "Malapert, summer half")[0]
    assert [whole(c) for c in row[1].split(" / ")] == [without[k]["cells"] for k in ("50", "100", "200")]
    assert [whole(c) for c in row[2].split(" / ")] == [with_cloud[k]["cells"] for k in ("50", "100", "200")]


def test_a_named_site_row_in_f_equals_validation_json(built):
    text, _ = built
    site = next(s for s in load("validation.json")["named_sites"]["sites"] if s["name"] == "Reykjanes, Iceland")
    hours = site["targets"]["malapert"]
    row = rows_of(section(text, "f"), "Reykjanes, Iceland")[0]
    assert site["cell"] == row[1]
    assert [float(c.replace(",", "")) for c in row[6].split(" / ")] == [
        round(hours[kind]["long"]["year"]) for kind in ("flat", "snow_free", "open")]


def test_the_version_2_column_in_k_comes_from_the_kept_version_2_file(built):
    text, _ = built
    old = load("validation_v2.json")["big_picture_north"]["targets"]["malapert"]["long_snow_free_hours"]
    new = load("validation.json")["big_picture_north"]["targets"]["malapert"]["long_snow_free_hours"]
    row = rows_of(section(text, "k"), "Malapert, summer half, ≥ 100 h")[0]
    assert whole(row[1]) == old["summer_half"]["100"]["cells"] and whole(row[2]) == new["summer_half"]["100"]["cells"]


def test_main_writes_beside_the_old_file_and_renames(tmp_path, built, capsys):
    out = tmp_path / "RESULTS.md"
    out.write_text("old")
    make_results.main(out)
    capsys.readouterr()
    text = out.read_text()
    assert text.startswith("# LuniMartian Atlas") and text.endswith("\n")
    assert [p.name for p in tmp_path.iterdir()] == ["RESULTS.md"]        # no side file is left behind


def test_the_script_reads_only_project_files():
    source = Path(make_results.__file__).read_text()
    assert "scratchpad" not in source and "/private/tmp" not in source and "/tmp/" not in source
    assert make_results.OUT == Path("data/derived/RESULTS.md")
    assert "light_cells.json" not in source


# ---- added by the count check of version 3: sentences that said more than their tables, and tables without a source

def test_a_number_is_never_printed_as_minus_zero():
    assert make_results.f(-0.04, 1) == "0.0" and make_results.f(-0.4) == "0"
    assert make_results.f(-0.06, 1) == "-0.1" and make_results.f(-1234.5, 1) == "-1,234.5"
    assert make_results.f(None) == "n/a" and make_results.f(0.0, 1) == "0.0"


def test_level_counts_leave_unknown_hours_out_and_sum_the_bare_ground():
    def cell(hours, km2):
        return {"bare_km2": km2, "targets": {"t": {"h": hours}}}
    cells = [cell(49.9, 1.0), cell(50.0, 2.0), cell(150.0, 4.0), cell(None, 8.0), cell(200.0, 16.0)]
    assert make_results.level_counts(cells, "t", "h") == {
        "50": {"cells": 3, "bare_km2": 22.0}, "100": {"cells": 2, "bare_km2": 20.0}, "200": {"cells": 1, "bare_km2": 16.0}}


def test_levels_that_differ_are_counted_one_by_one():
    mine = {"50": {"cells": 3, "bare_km2": 22.0}, "100": {"cells": 2, "bare_km2": 20.0}, "200": {"cells": 1, "bare_km2": 16.0}}
    theirs = {"50": {"cells": 3, "bare_km2": 22.04}, "100": {"cells": 1, "bare_km2": 20.0}, "200": {"cells": 1, "bare_km2": 17.0},
              "cells_counted": 4, "unknown_cells": 1}
    assert make_results.levels_that_differ(mine, mine) == 0
    assert make_results.levels_that_differ(mine, theirs) == 2          # one cell count and one area; 0.04 km2 is rounding


def test_stuck_station_check_counts_where_the_maps_as_they_read_are_closer():
    def station(stuck, mapped, ruled, truth, lat=60.0):
        return {"stuck_winters": stuck, "lat": lat, "satellite_as_mapped": mapped, "satellite": ruled, "station_share": truth}
    stations = [station(1, [0.5, 0.5], [0.2, 0.2], [0.6, 0.6], 59.3),          # as mapped closer
                station(2, [0.5, None], [0.7, 0.9], [0.8, 0.0], 67.9),         # the rule closer, on the one bin both have
                station(1, [0.5, 0.5], [0.5, 0.5], [1.0, 1.0], 61.0),          # the same
                station(0, [0.0, 0.0], [1.0, 1.0], [1.0, 1.0], 80.0)]          # no stuck winter: not in the group
    assert make_results.stuck_station_check(stations) == {
        "stations": 3, "as_mapped_closer": 1, "rule_closer": 1, "same": 1, "lat_min": 59.3, "lat_max": 67.9}


def tables_with_what_follows(text: str):
    """Each table of a lettered or named section as (header line, the section's text after the table)."""
    for part in re.split(r"\n(?=## )", text):
        lines = part.split("\n")
        i = 0
        while i < len(lines):
            if lines[i].startswith("|"):
                j = i
                while j < len(lines) and lines[j].startswith("|"):
                    j += 1
                yield lines[i], "\n".join(lines[j:])
                i = j
            else:
                i += 1


def test_every_table_names_its_source(built):
    text, _ = built
    without = [head[:80] for head, after in tables_with_what_follows(text)
               if "| Source |" not in head and not re.search(r"^Source: ", after, flags=re.M)]
    assert without == []


def test_the_blind_sample_sentence_says_how_many_sample_cells_have_a_horizon(built):
    text, _ = built
    share = load("validation.json")["terrain_share_left"]
    north, south = share["north"]["blind_sample"], share["south"]["blind_sample"]
    assert (f"{north['horizon']['cells']} of its {north['cells_in_group']} northern cells and "
            f"{south['horizon']['cells']} of its {south['cells_in_group']} southern cells have a horizon") in section(text, "d")
    if north["horizon"]["cells"] < north["cells_in_group"]:
        assert "every sample cell has a horizon" not in text
        assert "(without one: north " + ", ".join(f"{k}: {v}" for k, v in north["without_a_horizon"].items()) in section(text, "d")


def test_the_counts_of_b_and_c_are_made_again_in_this_run(built):
    text, numbers = built
    found = re.search(r"made again in this run from `grazing_cells.json`.*?: (\d+) counts, (\d+) differ", section(text, "b"))
    assert found and int(found.group(1)) == 2 * 4 * 3 * 2 * 2 and int(found.group(2)) == 0   # halves, targets, levels, flat and open, cells and km2
    assert "by the cross-check of the integration step" not in json.dumps(numbers)


def test_the_station_sentence_quotes_the_odds_the_measured_cells_use(built):
    text, _ = built
    periods = load("snow_validation_many.json")["periods"]
    mapped, ruled = periods["winter_half"]["as_mapped"]["mean_bias"], periods["winter_half"]["with_stale_flag_rule"]["mean_bias"]
    part = section(text, "i")
    assert f"{mapped:+.3f} in the winter half" in part and f"{ruled:+.3f}" in part
    assert "as the maps read" in part.split("Checked against weather stations")[1].split("\n")[0]


def test_the_stuck_station_sentence_is_counted_not_typed(built):
    text, _ = built
    check = make_results.stuck_station_check(load("snow_validation_many.json")["stations"])
    assert f"at {check['as_mapped_closer']} of the {check['stations']} trusted stations with a stuck pixel" in section(text, "i")
    assert "at all 9 trusted stations" not in Path(make_results.__file__).read_text()


def test_the_cells_that_rise_from_zero_are_placed_from_the_data(built):
    text, _ = built
    cells = [c for c in load("grazing_cells.json")["cells"]
             if c["gridded"] and c["hemisphere"] == "N" and c["snow"]["status"] == "measured"]
    risen = [c for c in cells if any(v["long_snow_free_hours_with_rule"] == 0.0 and (v["long_snow_free_hours"] or 0) > 0
                                     for v in c["targets"].values())]
    lats = [c["lat"] for c in risen]
    assert f"at {min(lats):.2f} to {max(lats):.2f} N" in section(text, "i")
    assert "61.5 to 64.4 N" not in Path(make_results.__file__).read_text()


def test_the_haughton_table_says_which_hours_it_counts(built):
    text, _ = built
    july = load("validation.json")["haughton_july"]["targets"]["nobile-rim-2"]
    part = text[text.index("### Haughton crater"):text.index("## (g)")]
    assert "any spell length" in part
    row = rows_of(part, "Nobile Rim 2")[0]
    assert [float(c) for c in row[-2].split(" / ")] == [july["long_flat_hours_july"], july["long_snow_free_hours_july"],
                                                        july["long_open_hours_july"]]


def test_southern_tables_do_not_call_rock_season_hours_hours_a_year(built):
    text, _ = built
    heads = [line for line in section(text, "g").split("\n") if line.startswith("| # |")]
    assert len(heads) == 4 and all("in the rock season" in h and "a year" not in h for h in heads)
    north_heads = [line for line in section(text, "e").split("\n") if line.startswith("| # |")]
    assert north_heads and all("snow-free over a flat horizon" in h for h in north_heads)


def test_ranked_cells_without_a_score_are_owned_up_to(built):
    text, _ = built
    ranked = [r for r in load("cells_scored.json")["cells"] if r["ranked"] and r["ranking"] == "north"]
    unknown = sum(any(v["goals"]["lighting"] is None for v in r["targets"].values()) for r in ranked)
    assert f"{unknown} of them have unknown snow-free hours" in section(text, "e")


def test_what_moved_a_site_is_called_an_inference(built):
    text, _ = built
    assert "by elimination" in section(text, "k").split("### The first three lighting sites")[1]


def test_figures_typed_into_sentences_are_read_from_the_files(built):
    text, _ = built
    old = load("cells_scored_v2.json")["cells"]
    assert f"not only for {len(old):,} candidates" in section(text, "k")
    outside = sum(not c["gridded"] for c in load("grazing_cells.json")["cells"])
    assert f"the {outside} cells outside the screens" in section(text, "f")


def test_the_check_bullets_are_read_from_checks_json_or_say_there_is_no_record(built):
    text, _ = built
    path = DERIVED / "checks.json"
    part = section(text, "i")
    if not path.exists():
        assert "No record of the independent recount" in part and "No record of the comparison" in part
        return
    checks = json.loads(path.read_text())
    if "independent_recount" in checks:
        rec = checks["independent_recount"]
        assert "Counted again from first principles" in part
        assert f"{rec['comparisons']:,} figures" in part and f"{rec['outside_tolerance']} outside" in part
    if "jpl_horizons" in checks:
        assert f"At {len(checks['jpl_horizons']['places'])} places" in part


def test_a_count_that_disagrees_with_the_cells_file_is_reported(monkeypatch, built):
    real = make_results.load

    def tampered(name):
        data = real(name)
        if name == "validation.json":
            data["big_picture_north"]["targets"]["malapert"]["long_snow_free_hours"]["winter_half"]["100"]["cells"] += 1
        return data
    monkeypatch.setattr(make_results, "load", tampered)
    lines, _ = make_results.build()
    assert re.search(r": \d+ counts, 1 differ\.", section("\n".join(lines) + "\n", "b"))


# ---- added before the final run (14 Nov 2026, evening): wording, the leap-cycle average, winter leads and access

TARGETS = [{"id": "connecting-ridge", "name": "Connecting Ridge", "limit_deg": 2.08},
           {"id": "nobile-rim-2", "name": "Nobile Rim 2", "limit_deg": 7.59}]
GENERATORS = ("scripts/make_results.py", "scripts/build_sunpath_demo.py", "scripts/build_validation_extras.py",
              "scripts/build_moon_cards.py", "scripts/score_cells.py", "scripts/validate.py", "scripts/build_winter_leads.py",
              "scripts/build_access_cells.py")


def test_the_generators_say_landing_region_and_promise_no_pending_work():
    for path in GENERATORS:
        text = Path(path).read_text()
        for phrase in ("candidate base site", "Moon base site", "lunar base site", "go-ahead", "not done yet"):
            assert phrase.lower() not in text.lower(), (path, phrase)
    assert "candidate landing regions" in Path("scripts/make_results.py").read_text()
    assert "lunar landing region" in Path("scripts/build_sunpath_demo.py").read_text()


def test_results_say_once_that_a_cell_is_an_area_on_the_page(built):
    text, _ = built
    assert text.count('called an "area"') == 1
    assert "go-ahead" not in text and "not done yet" not in text and "base site" not in text


def lead(i, after, region="Iceland", status="measured", main=True):
    return {"id": f"63.{i}_-20.0", "lat": 63.05 + i / 10, "lon": -20.05, "region": region, "bare_km2": 1.5 + i,
            "bare_samples": 4 + i, "at_main_floor": main, "snow": {"status": status, "land_pixels": 5, "block_pixels": 9},
            "winter_hours_flat": 250.0 - i, "winter_hours_snow_free": 220.0 - i, "winter_hours_after_terrain": after,
            "best_ten_day_periods": [{"bin": 31, "starts": "7 Nov", "hours": 40.0}], "south_share_winter": 1.0}


def winter_doc():
    counts = {"50": {"Iceland": 12, "Faroe Islands": 1}, "100": {"Iceland": 5, "Norway: Vestland": 2}}
    after = {"50": {"Iceland": 7}, "100": {"Iceland": 3}}
    leads = [lead(i, 200.0 - 10 * i) for i in range(11)] + [lead(20, None, "Norway: Vestland"), lead(21, 300.0, status="doubtful"),
                                                            lead(22, 290.0, main=False)]
    return {"meta": {"screen_relaxed": {"min_bare_of_the_pipeline": 0.15}, "floor_bare_km2": 1.0,
                     "squares": {"northern_land_squares_in_the_land_cover_file": 1000, "below_the_screen": 900,
                                 "below_the_screen_with_a_bare_sample": 300},
                     "built_with": {"year_phases": 8}, "warnings": ["No cloud is taken into account.", "The bare class can be a beach."],
                     "not_computed": ["cloud", "access"]},
            "floors": {"1.0": {"squares": 120}},
            "targets": {"connecting-ridge": {"leads": [], "counts_by_region": {"50": {}, "100": {}},
                                             "counts_by_region_after_terrain": {"50": {}, "100": {}},
                                             "screened_counts_by_region": {"50": {}, "100": {}},
                                             "screened_counts_by_region_after_terrain": {"50": {}, "100": {}}},
                        "nobile-rim-2": {"leads": leads, "counts_by_region": counts, "counts_by_region_after_terrain": after,
                                         "screened_counts_by_region": {"50": {"Iceland": 9}, "100": {"Iceland": 4, "Svalbard": 1}},
                                         "screened_counts_by_region_after_terrain": {"50": {"Iceland": 6}, "100": {"Iceland": 2}}}}}


def test_the_winter_section_reads_the_leads_file():
    text = "\n".join(make_results.winter_lines(winter_doc(), TARGETS, year_phases=8))
    assert "900" in text and "300" in text and "120" in text and "15%" in text           # what the screen hides
    row = rows_of(text, "Nobile Rim 2")[0]
    assert row[1].startswith("7 (") and "Iceland 5" in row[1] and "Norway: Vestland 2" in row[1]     # hidden, flat horizon
    assert row[2].startswith("3 (") and row[3].startswith("5 (") and row[4].startswith("2 (")
    assert rows_of(text, "Connecting Ridge")[0][1] == "0"
    best = [r for r in (rows_of(text, str(k)) for k in range(1, 12)) if r]
    assert len(best) == 10                                                                 # the ten best leads
    assert best[0][0][3] == "200.0" and best[9][0][3] == "110.0"                           # by hours after terrain
    assert "300.0" not in text and "290.0" not in text          # a doubtful square and one under the main floor are not leads
    for caution in ("No cloud is taken into account.", "The bare class can be a beach.", "cloud, access"):
        assert caution in text
    assert "Source: `winter_leads.json`" in text


def test_the_winter_section_says_so_when_the_file_was_made_with_other_calendars():
    text = "\n".join(make_results.winter_lines(winter_doc(), TARGETS, year_phases=4))
    assert "8 calendars" in text and "4" in text


def test_a_missing_file_leaves_one_line_and_the_section_heading():
    assert make_results.winter_lines(None, TARGETS) == ["`winter_leads.json` is not in `data/derived`, so this section has no figures."]
    assert make_results.access_lines(None, [], TARGETS) == ["`access_cells.json` is not in `data/derived`, so this section has no figures."]


def area(cid, lat, lon, score, hours, region="Arctic Canada"):
    return {"id": cid, "lat": lat, "lon": lon, "region": region, "ranked": True, "ranking": "north",
            "targets": {"connecting-ridge": {"long_open_hours": hours / 4, "goals": {"lighting": score / 2}},
                        "nobile-rim-2": {"long_open_hours": hours, "goals": {"lighting": score}}}}


def airfield(km, name="Gjoa Haven Airport", country="CA"):
    return {"nearest": {"name": name, "km": km}, "nearest_scheduled": {"name": name, "km": km, "country": country}, "country": country}


def test_the_access_section_counts_areas_within_reach_and_names_the_best():
    recs = [area("a", 68.0, -96.0, 1.0, 300.0), area("b", 68.1, -96.0, 0.99, 310.0),       # b lies within 50 km of a
            area("c", 70.0, -116.0, 0.9, 150.0), area("d", 72.0, -100.0, 0.95, 120.0),
            area("e", 74.0, -95.0, 0.8, 90.0), area("f", 75.0, 140.0, 1.0, 400.0, "Siberia and the Russian Far East"),
            dict(area("g", 60.0, -100.0, 1.0, 500.0), ranked=False)]
    access = {"meta": {"what_this_is_not": "Not a road or a port, not a permit, not a cost.",
                       "source": {"name": "OurAirports, airports.csv", "fetched_utc": "2026-11-15T01:54:18Z", "licence": "public domain"}},
              "cells": {"a": airfield(40.0), "b": airfield(45.0), "c": airfield(77.0, "Ulukhaktok", "CA"),
                        "d": airfield(150.0), "e": airfield(20.0), "f": airfield(505.0, "Chokurdakh", "RU"),
                        "g": airfield(5.0)}}
    text = "\n".join(make_results.access_lines(access, recs, TARGETS))
    row = rows_of(text, "Nobile Rim 2")[0]
    assert row[1] == "5" and row[2] == "2 / 3 / 4"            # areas with >= 100 h: a, b, c, d, f; e has 90 h; g is not ranked
    assert rows_of(text, "Connecting Ridge")[0] == ["Connecting Ridge", "1", "0 / 0 / 0", "100"]    # only f, 505 km away
    best = [line for line in text.split("\n") if line.startswith("| Nobile Rim 2 | ")]
    assert "68.00, -96.00" in text and "68.10, -96.00" not in text          # one area per 50 km
    assert "Ulukhaktok (77.0 km)" in text and "Chokurdakh" not in text.split("Share of the top")[0].split("Best reachable")[-1]
    assert "Not a road or a port, not a permit, not a cost." in text
    assert "CA 83%, RU 17%" in text                            # countries of the top areas: a, b, c, d, e in CA, f in RU
    assert text.count("Source: `cells_scored.json`") == 3 and best      # every table names its source


def test_the_leap_cycle_paragraph_names_the_calendars_and_what_remains():
    eight = make_results.leap_paragraph({"year_phases": 8})
    assert "eight calendars" in eight and "1.5 h" in eight and "2%" in eight and "`meta.year_phases`" in eight
    four = make_results.leap_paragraph({"year_phases": 4})
    assert "four calendars" in four and "3.2 h" in four
    assert "one calendar" in make_results.leap_paragraph({}) and "9.1 h" in make_results.leap_paragraph({})


def test_the_results_carry_the_leap_paragraph_and_the_new_sections(built):
    text, _ = built
    assert "**The leap-cycle average.**" in section(text, "i")
    assert "## (l) Winter on small bare patches" in text and "## (m) How reachable the best areas are" in text


# ---- added in the final run (14 Nov 2026, night): the two checks are read from data/derived/checks.json

RECOUNT = {"ran_utc": "2026-11-15T04:20:00Z", "cells": 16184, "targets": 4, "comparisons": 1359456, "year_phases": 8,
           "tolerance": "the larger of 2 percent and 1 hour a year; or known in one and unknown in the other",
           "outside_tolerance": 0, "largest_difference_h_a_year": 0.07, "largest_difference_h_in_a_ten_day_bin": 0.012,
           "snow_summaries_that_differ": 0,
           "against": [{"file": "data/derived/grazing_cells.json", "sha256": "aaa"}, {"file": "data/derived/grazing_bins.npz", "sha256": "bbb"}],
           "calendar_moved": {"days": 0.14, "targets": {"connecting-ridge": {"cells_with_long_window_flat_hours": 12000,
                                                                             "cells_outside_tolerance": 12, "largest_difference_h": 1.4}}}}
HORIZONS = {"ran_utc": "2026-11-15T04:00:00Z", "places": [{"name": f"p{i}"} for i in range(9)], "periods_per_place": 4,
            "year_phases": 8, "sun_code_sha256": "sss",
            "all_hours": {"rows": 144, "median_abs_difference_pct": 0.113, "largest_abs_difference_pct": 6.35, "largest_abs_difference_h": 0.63},
            "hours_in_spells_of_2_h_or_more": {"rows": 144, "median_abs_difference_pct": 0.259, "largest_abs_difference_pct": 7.96,
                                               "largest_abs_difference_h": 1.6},
            "rows_flagged": [{"hours": "all hours", "place": "vestfold", "period": "midsummer", "target": "connecting-ridge",
                              "difference_h": 0.24, "difference_pct": 6.35, "cause": "a small total"},
                             {"hours": "hours in spells of 2 h or more", "place": "lofoten", "period": "best", "target": "connecting-ridge",
                              "difference_h": -1.6, "difference_pct": -7.23, "cause": None}]}
NOW = {"grazing_cells.json": "aaa", "grazing_bins.npz": "bbb", "sun.py": "sss"}


def test_without_checks_json_both_checks_say_in_one_line_that_there_is_no_record():
    lines, numbers = make_results.checks_lines(None, NOW)
    assert len(lines) == 2 and all("checks.json" in line for line in lines)
    assert numbers == []


def test_the_recount_bullet_reads_its_figures_and_says_it_ran_on_the_files_of_this_report():
    lines, numbers = make_results.checks_lines({"independent_recount": RECOUNT}, NOW)
    text = " ".join(lines)
    assert "16,184 cells" in text and "1,359,456 figures" in text and "0 outside" in text
    assert "0.07 h a year" in text and "eight calendars" in text
    assert "on the files this report reads" in text
    assert "12 of the 12,000" in text and "up to 1.4 h" in text
    assert any(n[0].startswith("independent recount") for n in numbers)
    stale = make_results.checks_lines({"independent_recount": RECOUNT}, {**NOW, "grazing_bins.npz": "new"})[0]
    assert "earlier files" in " ".join(stale) and "on the files this report reads" not in " ".join(stale)


def test_the_horizons_bullet_reads_median_and_largest_and_lists_the_flagged_rows_with_their_cause():
    lines, numbers = make_results.checks_lines({"jpl_horizons": HORIZONS}, NOW)
    text = " ".join(lines)
    assert "JPL Horizons" in text and "9 places" in text and "4 ten-day periods" in text
    assert "0.11 percent" in text and "6.3 percent" in text and "0.26 percent" in text and "8.0 percent" in text
    assert "vestfold" in text.lower() and "cause not known" in text
    assert "Sun code of this run" in text
    old = " ".join(make_results.checks_lines({"jpl_horizons": HORIZONS}, {**NOW, "sun.py": "other"})[0])
    assert "earlier version of the Sun code" in old
    assert any(n[0].startswith("JPL Horizons") for n in numbers)


def test_unknown_figures_in_a_check_record_are_written_n_a_never_0():
    rec = {**RECOUNT, "largest_difference_h_a_year": None, "largest_difference_h_in_a_ten_day_bin": None}
    text = " ".join(make_results.checks_lines({"independent_recount": rec}, NOW)[0])
    assert "n/a h a year" in text


def _sample(cells, with_h, without):
    return {"cells_in_group": cells, "horizon": {"cells": with_h}, "without_a_horizon": without}


def test_the_census_line_calls_the_census_partial_only_while_elevation_tiles_are_missing():
    ns, ss = _sample(300, 299, {"window across the antimeridian": 1}), _sample(150, 148, {"window across the antimeridian": 2})
    partial = make_results.census_line({"cells": 5773, "why": {"elevation tile not fetched": 5743, "window across the antimeridian": 30}}, ns, ss)
    assert "not complete" in partial and "until the remaining tiles are fetched" in partial
    full = make_results.census_line({"cells": 30, "why": {"window across the antimeridian": 30}}, ns, ss)
    assert "not complete" not in full and "remaining tiles" not in full and "already on disk" not in full
    assert "30 measured northern cells" in full and "antimeridian" in full and "299 of its 300" in full

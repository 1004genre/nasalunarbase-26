# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Write SUBMISSION.md: the text for every field of the Space Apps project form.

The words live in docs/submission_template.md. The numbers are placeholders in
curly braces there, and this script fills them from the files in data/derived:

    required   validation.json, validation_extras.json, latitude_profile.json,
               moon_cards.json, cloud_cells.json, cells_scored.json
    optional   winter_leads.json, access_cells.json, snow_validation_many.json, checks.json,
               factor_matrix.json, mars_cells.json, mars_sites.json, mars_validation.json,
               mars_sites_base.json, count_check_v*.json (the newest);
               also site/data/meta.json (which lunar regions have hours after hills from the full
               method) and data/reference/mars_exploration_zones_2015.json (the count of zones)
    words      data/SOURCES.md, section 3: section 8c copies each credit line, word for word, in
               the order of the file (scripts/write_readme_credits.py puts the same lines in README.md)

The lunar regions and the Mars sites are not typed in here. The script reads the regions from
moon_cards.json (in the order of the Sun ceiling, lowest first) and the sites from mars_sites.json.

Rules the script keeps:
  * a placeholder with no value and no fallback stops the build (MissingValue);
  * a missing optional file leaves "[not yet measured]" in the text, never a number;
  * a sentence of the template that the data no longer supports stops the build
    (ClaimNoLongerHolds), so that refreshed numbers cannot sit under stale words;
  * before anything is written the result is checked: no curly brace left, no
    sentence over 25 words (outside the exact credit lines), the short summary
    within its working limit.

    uv run python scripts/build_submission.py            writes SUBMISSION.md
    uv run python scripts/build_submission.py --check    builds and checks, writes nothing

Written with SI assistance (Claude, by Anthropic, through Claude Code).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import statistics
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DERIVED = ROOT / "data" / "derived"
TEMPLATE = ROOT / "docs" / "submission_template.md"
OUT = ROOT / "SUBMISSION.md"

REQUIRED = {
    "validation": "validation.json",
    "extras": "validation_extras.json",
    "profile": "latitude_profile.json",
    "moon": "moon_cards.json",
    "cloud": "cloud_cells.json",
    "scored": "cells_scored.json",
}
OPTIONAL = {
    "winter_leads": "winter_leads.json",
    "access": "access_cells.json",
    "snow_check": "snow_validation_many.json",
    "checks": "checks.json",                  # the independent recount and the JPL Horizons comparison
    "factors": "factor_matrix.json",          # the table of factors and its counts by status
    "mars_cells": "mars_cells.json",          # the Mars first pass: squares, best places, shortfalls
    "mars_sites": "mars_sites.json",          # the Mars sites, with their lists and kinds
    "mars_validation": "mars_validation.json",  # where known Mars analog sites come out (AUC test)
    "mars_base": "mars_sites_base.json",      # the 2015 zones that are left out, and why
}
PAGE_META = ROOT / "site" / "data" / "meta.json"                          # hills_exact of each lunar region
ZONES_2015 = ROOT / "data" / "reference" / "mars_exploration_zones_2015.json"
SOURCES = ROOT / "data" / "SOURCES.md"    # section 3: the credit lines that section 8c copies word for word
COUNT_CHECK_GLOB = "count_check_v*.json"

NOT_YET = "[not yet measured]"
EXAMPLE_REGION = "malapert"               # the template uses Malapert Massif (on both NASA lists) as its example
LIST_NASA, LIST_2021, LIST_2015 = "NASA landing site", "2021 shortlist for human landings", "2015 exploration zone"
RUSSIAN_REGIONS = ("Kola and north-west Russia", "Siberia and the Russian Far East", "Novaya Zemlya",
                   "Severnaya Zemlya", "Chukotka", "Franz Josef Land")

MAX_WORDS = 25                            # the team's rule for every sentence
SUMMARY_MAX_WORDS = 150                   # working limits: the form's own limit is not in our notes
SUMMARY_MAX_CHARS = 1000
SEARCH_BAND_NORTH_DEG = 59.0              # the northern search runs from 59 to 84 degrees (RESULTS.md, section (a))
EXACT_WORDING_MARK = "exact credit lines"  # a section whose heading holds these words is not prose
LEAD_GAP = "[LEAD SENTENCE A, B, C OR D]"

# Facts that are in no file of data/derived. They do not refresh; each says where it comes from.
FIXED_FACTS = {
    # The JPL Horizons figures (horizons_agreement_pct, horizons_largest_pct, horizons_places) are no longer
    # typed in here: values_horizons reads them from data/derived/checks.json (scripts/check_against_horizons.py).
    # data/SOURCES.md, rows 15 and 16: the two hand-compiled reference lists.
    "known_sites_in_list": "85",
    "anorthosite_bodies": "28",
    # Survey report, section 2b (lamp halls and built fields, with links).
    "lamp_field_small_m2": "77",
    # Survey report, lines 44 and 90: the highest Sun the NASA NESC paper gives for the sites it studied.
    "nesc_sun_deg": "7",
    # The 2026 Project Submission Guide, as read in the research notes.
    "demo_max_seconds": "30",
    "demo_max_slides": "7",
    "image_max_mb": "10",
}

MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December")
MONTH_DAYS = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
WORDS = ("none", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten")


class BuildError(Exception):
    """Anything that must stop the build with a plain message."""


class MissingInput(BuildError):
    pass


class MissingValue(BuildError):
    pass


class ClaimNoLongerHolds(BuildError):
    pass


class OutputCheckFailed(BuildError):
    pass


# ---------------------------------------------------------------- reading the files

def load_json(path: Path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def newest(paths: list[Path]) -> Path | None:
    return max(paths, key=lambda p: (p.stat().st_mtime, p.name)) if paths else None


def load_inputs(derived: Path) -> dict:
    """Every required file, or MissingInput naming all that are absent; optional files are None when absent."""
    missing = [name for name in REQUIRED.values() if not (derived / name).exists()]
    if missing:
        raise MissingInput("required data file(s) not found in " + str(derived) + ": " + ", ".join(missing))
    inputs = {key: load_json(derived / name) for key, name in REQUIRED.items()}
    for key, name in OPTIONAL.items():
        inputs[key] = load_json(derived / name) if (derived / name).exists() else None
    count_check = newest(sorted(derived.glob(COUNT_CHECK_GLOB)))
    inputs["count_check"] = load_json(count_check) if count_check else None
    inputs["count_check_name"] = count_check.name if count_check else None
    inputs["page_meta"] = load_json(PAGE_META) if PAGE_META.exists() else None
    inputs["zones_2015"] = load_json(ZONES_2015) if ZONES_2015.exists() else None
    inputs["sources_text"] = SOURCES.read_text(encoding="utf-8") if SOURCES.exists() else None
    return inputs


# ---------------------------------------------------------------- the credit lines of data/SOURCES.md

CREDIT_LINE = re.compile(r"^\*\*([A-Z]{1,2})\. (.+?)([:.])\*\*\s*(.*)$", re.S)


def credit_lines(sources_text: str) -> list[dict]:
    """Every credit line of data/SOURCES.md, section 3, in the order of the file.

    A credit line is a bullet that starts '- **X. Title:**' (X is one or two capitals), with its
    continuation lines. Each item gives the letter, the bullet as it stands in the file ('lines',
    for the README) and the same bullet on one line without the bold marks ('one_line', for section 8c).
    A bullet of section 3 without a letter (a cross-reference) is not a credit line.
    """
    section, inside = [], False
    for line in sources_text.split("\n"):
        if re.match(r"^## \d+\.", line):
            inside = line.startswith("## 3.")
            continue
        if inside:
            section.append(line)
    bullets, current = [], None
    for line in section:
        if line.startswith("- "):
            if current:
                bullets.append(current)
            current = [line]
        elif current is not None and line.strip():
            current.append(line)
        else:
            if current:
                bullets.append(current)
            current = None
    if current:
        bullets.append(current)
    found = []
    for lines in bullets:
        joined = " ".join(part.strip() for part in lines)[2:]
        match = CREDIT_LINE.match(joined)
        if not match:
            continue
        letter, title, mark, text = match.groups()
        found.append({"ref": letter, "lines": lines,
                      "one_line": f"- {letter}. {title}{mark} {text}".rstrip()})
    return found


def values_credits(inputs: dict) -> dict:
    text = inputs.get("sources_text")
    if text is None:                        # inputs made by hand: read the file here
        if not SOURCES.exists():
            raise MissingInput(f"{SOURCES} not found: section 8c copies its credit lines")
        text = SOURCES.read_text(encoding="utf-8")
    lines = credit_lines(text)
    if not lines:
        raise MissingValue("data/SOURCES.md, section 3, has no credit line of the form '- **X. Title:** text'")
    return {"credit_lines": "\n".join(item["one_line"] for item in lines),
            "credit_count": exact(len(lines)), "credit_first": lines[0]["ref"], "credit_last": lines[-1]["ref"]}


def regions(inputs: dict) -> list[str]:
    """The lunar region ids of moon_cards.json, in the order of the Sun ceiling, lowest first."""
    if "_regions" not in inputs:
        cards = sorted(inputs["moon"]["cards"], key=lambda card: card["sun_ceiling"]["deg"])
        inputs["_regions"] = [card["id"] for card in cards]
    return inputs["_regions"]


def region_names(inputs: dict) -> dict:
    return {card["id"]: card["official_name"] for card in inputs["moon"]["cards"]}


def mars_ids(inputs: dict) -> list[str]:
    """The Mars site ids of mars_sites.json, in the order of that file."""
    return [site["id"] for site in inputs["mars_sites"]["sites"]]


def and_list(names: list[str]) -> str:
    """'A', 'A and B', 'A, B and C'."""
    names = list(names)
    if not names:
        return "none"
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


# ---------------------------------------------------------------- saying numbers honestly

def exact(n) -> str:
    return f"{int(round(n)):,}"


def round_sig(n: float, digits: int = 2) -> int:
    if n == 0:
        return 0
    scale = 10 ** (int(math.floor(math.log10(abs(n)))) - digits + 1)
    return int(round(n / scale) * scale)


def approx(n) -> str:
    """'16' stays exact; 7,353 becomes 'approximately 7,400' (two significant figures; the STE word for a rounded quantity)."""
    n = float(n)
    if abs(n) < 100:
        return exact(n)
    return "approximately " + exact(round_sig(n, 2))


def trim(x: float, places: int = 2) -> str:
    """57.65 -> '57.65', 59.9 -> '59.9', 64.80 -> '64.8'."""
    text = f"{x:.{places}f}"
    return text.rstrip("0").rstrip(".") if "." in text else text


def pct(share: float, places: int = 0) -> str:
    return trim(round(100.0 * share, places), places)


def number_word(n: int) -> str:
    """Words up to ten, numerals above: 'four', '16'."""
    return WORDS[n] if 0 <= n < len(WORDS) else exact(n)


def count_word(n: int, of: int) -> str:
    """'all 16', 'three of the four', 'none of the 16'."""
    if n == of:
        return f"all {number_word(of)}"
    if n == 0:
        return f"none of the {number_word(of)}"
    return f"{number_word(n)} of the {number_word(of)}"


def day_month(day_of_year: int) -> str:
    """Day 1 is 1 January, in a 365-day year."""
    left = day_of_year
    for month, days in zip(MONTHS, MONTH_DAYS):
        if left <= days:
            return f"{left} {month}"
        left -= days
    raise ValueError(f"day of year out of range: {day_of_year}")


def bin_first_day(index: int) -> str:
    """The 36 ten-day periods start on day 1, 11, 21, ...; the last one runs to 31 December."""
    return day_month(10 * index + 1)


def bin_last_day(index: int) -> str:
    return day_month(365 if index == 35 else 10 * index + 10)


def low_high(values, fmt=trim) -> tuple[str, str]:
    values = [v for v in values if v is not None]
    return fmt(min(values)), fmt(max(values))


def regions_text(counts: dict, limit: int = 4) -> str:
    """'Iceland 50, Norway 13, Faroe Islands 1' (the largest first; the rest summed as 'other regions')."""
    rows = sorted(((n, name) for name, n in counts.items() if n), key=lambda r: (-r[0], r[1]))
    shown = [f"{name} {exact(n)}" for n, name in rows[:limit]]
    rest = sum(n for n, _ in rows[limit:])
    if rest:
        shown.append(f"other regions {exact(rest)}")
    return ", ".join(shown)


# ---------------------------------------------------------------- the values, group by group

def ranked_north(scored: dict) -> list[dict]:
    return [c for c in scored["cells"] if c.get("ranked") and c.get("ranking") == "north"]


def measured_north(scored: dict) -> list[dict]:
    return [c for c in scored["cells"]
            if c["hemisphere"] == "N" and c["gridded"] and c["snow"]["status"] == "measured"]


def lighting_order(cells: list[dict], target: str) -> list[dict]:
    """Ranked cells with a lighting score, best first; equal scores go by hours (as in RESULTS.md)."""
    rows = [c for c in cells if c["targets"][target]["goals"]["lighting"] is not None]
    return sorted(rows, key=lambda c: (-c["targets"][target]["goals"]["lighting"],
                                       -(c["targets"][target]["long_open_hours"] or 0.0)))


def values_search(inputs: dict) -> dict:
    scored, validation = inputs["scored"], inputs["validation"]
    cells = scored["cells"]
    counts = scored["meta"]["counts"]
    north = [c for c in cells if c["hemisphere"] == "N" and c["gridded"]]
    south = [c for c in cells if c["hemisphere"] == "S" and c["gridded"]]
    with_horizon, records = counts["with_a_horizon"], counts["records"]
    out = {
        "areas_total": approx(records),
        "areas_total_exact": exact(records),
        "areas_north": approx(len(north)),
        "areas_south": approx(len(south)),
        "areas_measured_north": approx(validation["big_picture_north"]["measured_cells"]),
        "ranked_north": approx(counts["ranked_north"]),
        "ranked_south": approx(counts["ranked_south"]),
        "data_written": validation["meta"]["written"].replace("T", " at ")[:19],
    }
    without = records - with_horizon                    # exact counts: 16,133 of 16,184 must not read "16,000 of 16,000"
    across = counts.get("not_ranked_because", {}).get("window across the antimeridian", 0)
    if without <= 0:
        out["terrain_coverage_sentence"] = "Hills are measured for every area."
        out["terrain_next_step"] = "Test our 90 m hills against finer elevation data at a few places."
    elif across == without:
        out["terrain_coverage_sentence"] = (
            f"Hills are measured for {exact(with_horizon)} of {exact(records)} areas. "
            f"The other {exact(without)} lie across the 180-degree meridian, where our hill tool stops.")
        out["terrain_next_step"] = (f"Test our 90 m hills against finer elevation data, and add hills for the "
                                    f"{exact(without)} areas across the 180-degree meridian.")
    else:
        out["terrain_coverage_sentence"] = (
            f"Hills are measured for {exact(with_horizon)} of {exact(records)} areas, "
            "so counts with hills are lower bounds.")
        out["terrain_next_step"] = (f"Measure hills for the {exact(without)} areas still without them, "
                                    "then test them against finer elevation data.")
    out["areas_with_horizon"] = exact(with_horizon)
    out["areas_without_horizon"] = exact(without)
    return out


def lists_label(card: dict) -> str:
    on_2022, on_2024 = card["nasa_list"]["on_2022_list_of_13"], card["nasa_list"]["on_2024_list_of_9"]
    if on_2022 and on_2024:
        return "on the lists of 2022 and 2024"
    return "on the list of 2022 only" if on_2022 else "on the list of 2024 only"


def values_moon(inputs: dict) -> dict:
    cards = {card["id"]: card for card in inputs["moon"]["cards"]}
    targets = regions(inputs)
    lowest, highest = cards[targets[0]], cards[targets[-1]]
    on_2022 = [t for t in targets if cards[t]["nasa_list"]["on_2022_list_of_13"]]
    on_2024 = [t for t in targets if cards[t]["nasa_list"]["on_2024_list_of_9"]]
    without = [cards[t]["official_name"] for t in targets if not cards[t]["has_model"]]
    out = {
        "regions_total": exact(len(targets)),
        "regions_2022": exact(len(on_2022)),
        "regions_2024": exact(len(on_2024)),
        "regions_both": exact(len(set(on_2022) & set(on_2024))),
        "regions_only_2022": number_word(len(set(on_2022) - set(on_2024))),
        "regions_only_2024": number_word(len(set(on_2024) - set(on_2022))),
        "regions_with_model": exact(len(targets) - len(without)),
        "regions_without_model": number_word(len(without)),
        "regions_without_model_cap": number_word(len(without)).capitalize(),
        "regions_without_model_names": and_list(without),
        "lowest_name": lowest["official_name"],
        "highest_name": highest["official_name"],
        "ceil_min": trim(round(lowest["sun_ceiling"]["deg"], 2)),
        "ceil_max": trim(round(highest["sun_ceiling"]["deg"], 2)),
        # whole metres: the page and moon_cards.json differ in the first decimal
        "shadow_min": trim(round(highest["shadow_of_1m_object_at_ceiling_m"], 0), 0),
        "shadow_max": trim(round(lowest["shadow_of_1m_object_at_ceiling_m"], 0), 0),
        "_without_model_n": len(without),
    }
    above = [cards[t]["official_name"] for t in targets
             if cards[t]["sun_ceiling"]["deg"] > float(FIXED_FACTS["nesc_sun_deg"])]
    out["regions_above_nesc"] = number_word(len(above))
    out["regions_above_nesc_names"] = and_list(above)
    rows = []
    for t in targets:
        card = cards[t]
        model = ("NASA 5 m terrain model" if card["has_model"]
                 else "no NASA 5 m model; placed from NASA's map of 2024")
        rows.append(f"- {card['official_name']}: {lists_label(card)}; Sun ceiling "
                    f"{trim(round(card['sun_ceiling']['deg'], 2))} degrees; {model}.")
    out["regions_list"] = "\n".join(rows)
    page = inputs.get("page_meta")
    try:
        exact_ids = [t["id"] for t in page["targets"] if t["hills_exact"]]
        if set(t["id"] for t in page["targets"]) != set(targets):
            raise KeyError("site/data/meta.json has other lunar regions than moon_cards.json")
        out["regions_hills_full"] = and_list([cards[t]["official_name"] for t in targets if t in exact_ids])
        out["regions_hills_lower_bound"] = exact(len(targets) - len(exact_ids))
    except (TypeError, KeyError):
        out["regions_hills_full"] = out["regions_hills_lower_bound"] = NOT_YET
    facts = {item["what"]: item for item in cards[EXAMPLE_REGION]["earth_cannot_match"]}
    synodic_days = facts["slow Sun"]["number"]
    moon_deg_per_hour = 360.0 / (synodic_days * 24.0)
    earth_deg_per_hour = 15.0 * math.sin(math.radians(70.0))        # near the horizon, at 70 degrees of latitude
    out["sun_turn_days"] = trim(synodic_days, 2)
    out["moon_deg_per_hour"] = trim(round(moon_deg_per_hour, 2))
    out["earth_deg_per_hour"] = trim(round(earth_deg_per_hour, 0), 0)
    out["sun_speed_ratio"] = trim(round(earth_deg_per_hour / moon_deg_per_hour, 0), 0)
    for lat in (60, 80):                                             # the ratio depends on latitude: say its range
        ratio = 15.0 * math.sin(math.radians(lat)) / moon_deg_per_hour
        out[f"sun_speed_ratio_{lat}"] = trim(round(ratio, 0), 0)
    out["moon_gravity"] = trim(facts["gravity"]["number"], 2)
    means = [cards[t]["diviner"]["annual_mean_temp_2cm_C"]["mean"] for t in targets
             if (cards[t].get("diviner") or {}).get("annual_mean_temp_2cm_C")]
    out["moon_temp_warmest"] = trim(round(max(means), 0), 0).replace("-", "minus ")
    out["moon_temp_coldest"] = trim(round(min(means), 0), 0).replace("-", "minus ")
    return out


def values_latitude(inputs: dict) -> dict:
    profile, extras = inputs["profile"], inputs["extras"]
    targets, names = regions(inputs), region_names(inputs)
    first = {t: profile["thresholds"][t]["N"]["lowest_lat_with_long_window"]["2"] for t in targets}
    out = {"lat_2h_lowest": trim(first[targets[0]]), "lat_2h_highest": trim(first[targets[-1]])}
    out["lat_2h_min"] = trim(round(min(first.values()), 0), 0)
    out["lat_2h_max"] = trim(round(max(first.values()), 0), 0)
    one_hour = profile["thresholds"][targets[-1]]["N"]["lowest_lat_with_long_window"]["1"]
    out["lat_1h_highest"] = trim(round(one_hour, 0), 0)               # where spells of 1 to 2 hours begin
    south = [t for t in targets if first[t] < SEARCH_BAND_NORTH_DEG]
    out["regions_outside_search"] = number_word(len(south))
    out["regions_outside_search_names"] = and_list([names[t] for t in south])
    out["_regions_outside_search_n"] = len(south)
    row30 = min(profile["profile"], key=lambda r: abs(r["lat"] - 30.0))
    out["spell_30n_minutes"] = exact(60.0 * max(row30["targets"][t]["longest_spell_h"] for t in targets))
    low = extras["lower_latitude_sites"]["summary"]
    out["lowlat_places"] = exact(max(low[t]["sites"] for t in targets))
    out["lowlat_longest_minutes"] = exact(max(low[t]["longest_spell_minutes_max"] for t in targets))
    out["search_band_north"] = trim(SEARCH_BAND_NORTH_DEG)
    kinds = [site.get("kind", "") for site in extras["lower_latitude_sites"]["sites"]]
    out["lowlat_other_teams"] = exact(sum("other teams" in kind for kind in kinds))
    out["lowlat_classic"] = exact(sum("classic" in kind for kind in kinds))
    if int(out["lowlat_other_teams"]) + int(out["lowlat_classic"]) != len(kinds):
        raise BuildError("a lower-latitude place in validation_extras.json is neither an other-team twin nor a classic site: "
                         "reword the sentence on lower latitudes in the template")
    return out


def winter_bins(profile: dict) -> list[int]:
    return list(profile["meta"]["oct_mar_bins"])


def values_seasons(inputs: dict) -> dict:
    validation, extras, profile = inputs["validation"], inputs["extras"], inputs["profile"]
    big = validation["big_picture_north"]["targets"]
    chain = extras["latitude_against_full_method"]["targets"]
    winter = set(winter_bins(profile))
    targets = regions(inputs)
    out = {"winter_half_dates": extras["meta"]["winter_half"], "summer_half_dates": extras["meta"]["summer_half"]}
    winter_shares, peak_bins, peak_shares = [], set(), []
    for t in targets:
        calendar = big[t]["calendar_hours_times_bare_km2"]
        total = sum(calendar)
        winter_shares.append(sum(v for i, v in enumerate(calendar) if i in winter) / total)
        top3 = sorted(range(len(calendar)), key=lambda i: -calendar[i])[:3]
        peak_bins.update(top3)
        peak_shares.append(sum(calendar[i] for i in top3) / total)
    out["summer_share_low"], out["summer_share_high"] = low_high([1.0 - s for s in winter_shares], pct)
    out["winter_share_low"], out["winter_share_high"] = low_high(winter_shares, lambda s: pct(s, 1))
    out["peak_from"] = bin_first_day(min(peak_bins))
    out["peak_to"] = bin_last_day(max(peak_bins))
    out["peak_share_low"], out["peak_share_high"] = low_high(peak_shares, pct)
    clear_bins = set()                                    # the busiest periods once typical cloud is counted
    for t in targets:
        clear = big[t]["calendar_clear_hours_times_bare_km2"]
        clear_bins.update(sorted(range(len(clear)), key=lambda i: -clear[i])[:3])
    out["peak_clear_from"] = bin_first_day(min(clear_bins))
    out["peak_clear_to"] = bin_last_day(max(clear_bins))
    out["_peak_moves_earlier"] = min(clear_bins) < min(peak_bins)
    for t, short in ((targets[0], "lowest"), (EXAMPLE_REGION, "malapert"), (targets[-1], "highest")):
        flat = big[t]["long_snow_free_hours"]
        hills = big[t]["long_open_hours_among_cells_with_a_horizon"]
        out[f"summer_100_{short}"] = approx(flat["summer_half"]["100"]["cells"])
        out[f"winter_100_{short}"] = approx(flat["winter_half"]["100"]["cells"])
        out[f"summer_100_hills_{short}"] = approx(hills["summer_half"]["100"]["cells"])
        steps = chain[t]["winter_half"]["all_measured_cells"]
        out[f"winter_sun_alone_{short}"] = approx(steps["sun_alone"]["cells"])
        out[f"winter_after_snow_{short}"] = approx(steps["after_snow"]["cells"])
    # Malapert Massif only: finding 2 and lead B speak of that one lunar region, so its region split must be its own
    # (the largest count over all four regions mixed in Nobile Rim 2's Svalbard area).
    split = {name: n for name, n in
             validation["regions"]["malapert"]["measured_cells_100_long_snow_free_hours_winter_half"].items() if n}
    if not split:
        out["winter_regions_sentence"] = "Among large bare areas, none reaches 100 winter hours for Malapert Massif."
    elif set(split) == {"Iceland"}:
        out["winter_regions_sentence"] = ("Among large bare areas, each one that reaches 100 winter hours "
                                          "for Malapert Massif is in Iceland.")
    else:
        out["winter_regions_sentence"] = ("Among large bare areas, the areas that reach 100 winter hours for Malapert "
                                          "Massif are in: " + regions_text(split) + ".")
    winter = big["malapert"]["long_snow_free_hours"]["winter_half"]["100"]
    out["winter_bare_share_malapert"] = pct(winter["bare_km2"] / validation["big_picture_north"]["measured_bare_km2"], 1)
    hills = big["malapert"]["long_open_hours_among_cells_with_a_horizon"]["winter_half"]["100"]["cells"]
    out["winter_after_hills_malapert"] = approx(hills)
    return out


def values_ridge_and_best(inputs: dict) -> dict:
    ranked = ranked_north(inputs["scored"])
    targets = regions(inputs)
    lowest = targets[0]
    out = {}
    russia, first_regions = 0, {}
    for t, short in ((lowest, "lowest"), (targets[-1], "highest")):
        hours = [c["targets"][t]["long_open_hours"] for c in ranked if c["targets"][t]["long_open_hours"] is not None]
        out[f"best_hours_{short}"] = approx(max(hours))
    for t in targets:
        order = lighting_order(ranked, t)
        russia += order[0]["region"] in RUSSIAN_REGIONS
        first_regions[order[0]["region"]] = first_regions.get(order[0]["region"], 0) + 1
    out["top_in_russia"] = count_word(russia, len(targets))
    out["first_by_light_regions"] = regions_text(first_regions, limit=6)
    out["_top_in_russia_n"] = russia
    # the lowest region: how fragile the count of areas at 100 summer hours is, and the best area after hills.
    summer = [c["targets"][lowest]["long_snow_free_hours_summer"] for c in measured_north(inputs["scored"])]
    below = [h for h in summer if h is not None and h < 100.0]
    out["lowest_next_below_100"] = trim(math.floor(max(below)), 0) if below else NOT_YET
    best = max((c for c in ranked if c["targets"][lowest]["long_open_hours"] is not None),
               key=lambda c: c["targets"][lowest]["long_open_hours"])
    out["best_region_lowest"] = best["region"]
    out["best_clear_lowest"] = approx(best["targets"][lowest]["long_open_hours_clear"])
    year = inputs["validation"]["big_picture_north"]["targets"][lowest][
        "long_open_hours_among_cells_with_a_horizon"]["year"]["100"]["cells"]
    out["_lowest_year_100_after_hills"] = year
    return out


def values_terrain(inputs: dict) -> dict:
    """The census of every measured northern area with a horizon; the blind sample is the cross-check."""
    validation = inputs["validation"]
    targets = regions(inputs)
    share = validation["terrain_share_left"]["north"]
    sample, census = share["blind_sample"], share["all_measured"]
    out = {"terrain_sample_areas": exact(sample["cells_in_group"]),
           "terrain_census_areas": exact(validation["big_picture_north"]["cells_with_a_horizon"])}
    out["terrain_kept_low"], out["terrain_kept_high"] = low_high([census[t]["median"] for t in targets], pct)
    gap = max(abs(sample[t]["median"] - census[t]["median"]) for t in targets)
    out["terrain_sample_gap_points"] = trim(math.ceil(100.0 * gap), 0)
    # weighted by hours: the share of all snow-free hours that the hills leave, over measured areas with a horizon
    weighted = []
    for t in targets:
        rows = [c["targets"][t] for c in measured_north(inputs["scored"])
                if c["targets"][t]["long_open_hours"] is not None and c["targets"][t]["long_snow_free_hours"]]
        weighted.append(sum(r["long_open_hours"] for r in rows) / sum(r["long_snow_free_hours"] for r in rows))
    out["terrain_weighted_low"], out["terrain_weighted_high"] = low_high(weighted, pct)
    out["_terrain_census"] = [census[t]["median"] for t in targets]       # in the order of the Sun ceiling
    return out


def values_cloud(inputs: dict) -> dict:
    """Sky cover where the Malapert Massif hours are: measured northern areas with 100 summer hours after hills,
    as in RESULTS.md section (j). The median over every northern area would describe ground that holds no hours."""
    cloud = inputs["cloud"]["cells"]
    north = [c for c in measured_north(inputs["scored"])
             if (c["targets"]["malapert"]["long_open_hours_summer"] or 0.0) >= 100.0]

    def median_of(month: int) -> float:
        values = [cloud[c["id"]]["cloud_pct"][month] for c in north
                  if cloud.get(c["id"]) and cloud[c["id"]].get("cloud_pct") and cloud[c["id"]]["cloud_pct"][month] is not None]
        if not values:
            raise BuildError("no cloud figure for any measured northern area: cloud_cells.json does not match cells_scored.json")
        return statistics.median(values)

    big = inputs["validation"]["big_picture_north"]["targets"]
    kept = [sum(big[t]["calendar_clear_hours_times_bare_km2"]) / sum(big[t]["calendar_open_hours_times_bare_km2"])
            for t in regions(inputs) if sum(big[t]["calendar_open_hours_times_bare_km2"]) > 0]
    low, high = low_high(kept, pct)
    return {"cloud_july": trim(round(median_of(6), 0), 0), "cloud_august": trim(round(median_of(7), 0), 0),
            "cloud_areas_malapert": approx(len(north)),
            "clear_kept": low if low == high else f"{low} to {high}"}


def values_midnight(inputs: dict) -> dict:
    north = measured_north(inputs["scored"])
    shares = [c["targets"]["malapert"]["poleward_share"] for c in north
              if (c["targets"]["malapert"]["long_snow_free_hours_summer"] or 0.0) >= 100.0
              and c["targets"]["malapert"]["poleward_share"] is not None]
    if not shares:
        raise BuildError("no measured northern area reaches 100 summer hours for Malapert Massif: the template needs a rewrite")
    return {"north_sun_share": pct(statistics.median(shares)), "_north_sun_share": statistics.median(shares)}


def values_known(inputs: dict) -> dict:
    known = inputs["extras"]["known_sites"]
    targets = regions(inputs)
    summary = known["summary"]["north_all_listed_sites"]
    low, high = low_high([summary[t]["median_percentile"] for t in targets], lambda v: trim(round(v, 0), 0))
    haughton = next((site for site in known["sites"]["known_analogs_poleward_of_59"] + known["sites"]["named_sites_north"]
                     if "Haughton" in site["name"]), None)
    if haughton is None:
        raise BuildError("Haughton crater is not in validation_extras.json: known_sites")
    verdicts = [haughton["targets"][t]["verdict"] for t in targets]
    high_n = sum(v == "high" for v in verdicts)
    july = [inputs["validation"]["haughton_july"]["targets"][t]["long_open_hours_july"] for t in targets]
    southern = [site for site in inputs["validation"]["named_sites"]["sites"]
                if site.get("hemisphere") == "S" and site.get("winter_snow_evidence")]
    return {"haughton_july_low": trim(round(min(july), 0), 0), "haughton_july_high": trim(round(max(july), 0), 0),
            "south_named_sites": exact(len(southern)),
            "south_station_snow": exact(sum(site["winter_snow_evidence"] == "station shows snow" for site in southern)),
            "known_percentile_low": low, "known_percentile_high": high,
            "known_sites_listed": exact(max(summary[t]["cells_with_a_value"] for t in targets)),
            "haughton_top_third": count_word(high_n, len(targets)),
            "_haughton_high_n": high_n, "_regions_n": len(targets),
            "_known_percentile_high": max(summary[t]["median_percentile"] for t in targets),
            "_known_percentile_low": min(summary[t]["median_percentile"] for t in targets)}


def values_checks(inputs: dict) -> dict:
    """The recount and the station check are read when their files are there; if not, the text says so."""
    out = {}
    check = inputs.get("count_check")
    recount = (inputs.get("checks") or {}).get("independent_recount")
    if recount:                               # checks.json, written by scripts/independent_recount.py, comes first
        check = {"first_principles": recount}
    try:
        first = check["first_principles"]
        out["recount_areas"] = exact(first["cells"])
        out["recount_largest_difference"] = trim(first["largest_difference_h_a_year"], 2)
        out["_recount_outside_tolerance"] = first["outside_tolerance"]
    except (TypeError, KeyError):
        out["recount_areas"] = out["recount_largest_difference"] = NOT_YET
        out["_recount_outside_tolerance"] = None
    try:                                      # the calendar moved a fraction of a day: how far the hours move
        moved = recount["calendar_moved"]
        out["calendar_shift_days"] = trim(moved["days"], 2)
        out["calendar_shift_largest_h"] = trim(round(max(t["largest_difference_h"] for t in moved["targets"].values()), 1), 1)
        out["recount_comparisons"] = approx(recount["comparisons"])
        names = region_names(inputs)       # the regions that the recount covered (the checks did not run again)
        checked = [t for t in regions(inputs) if t in moved["targets"]]
        out["checks_regions"] = number_word(len(checked))
        out["checks_regions_names"] = and_list([names[t] for t in checked])
    except (TypeError, KeyError):
        out["calendar_shift_days"] = out["calendar_shift_largest_h"] = out["recount_comparisons"] = NOT_YET
        out["checks_regions"] = out["checks_regions_names"] = NOT_YET
    snow = inputs.get("snow_check")
    try:
        periods = snow["periods"]
        out["snow_stations"] = exact(snow["overall"]["stations"])
        out["snow_bias_winter"] = trim(round(-100.0 * periods["winter_half"]["as_mapped"]["mean_bias"], 0), 0)
        out["snow_bias_summer"] = trim(round(-100.0 * periods["summer_half"]["as_mapped"]["mean_bias"], 0), 0)
        out["_snow_bias_sign_ok"] = (periods["winter_half"]["as_mapped"]["mean_bias"] < 0
                                     and periods["summer_half"]["as_mapped"]["mean_bias"] < 0)
    except (TypeError, KeyError):
        out["snow_stations"] = out["snow_bias_winter"] = out["snow_bias_summer"] = NOT_YET
        out["_snow_bias_sign_ok"] = None
    return out


def values_horizons(inputs: dict) -> dict:
    """The JPL Horizons comparison, from checks.json: median and largest difference of all hours in a band, places."""
    keys = ("horizons_agreement_pct", "horizons_largest_pct", "horizons_places", "horizons_spells_pct",
            "horizons_spells_largest_pct", "horizons_spells_largest_h", "horizons_flag_sentence")
    record = (inputs.get("checks") or {}).get("jpl_horizons")
    try:
        hours, places = record["all_hours"], len(record["places"])
        spells = record["hours_in_spells_of_2_h_or_more"]
        if not places:
            raise KeyError("places")
        flagged = record["rows_flagged"]
        names = {r["target"] for r in flagged}
        if not flagged:
            flag = "No row differs by more than 5 percent or 1 hour."
        elif names == {regions(inputs)[0]}:
            flag = (f"All {exact(len(flagged))} rows that differ by more than 5 percent or 1 hour are for "
                    f"{region_names(inputs)[regions(inputs)[0]]}, the lowest Sun.")
        else:
            flag = f"{exact(len(flagged))} rows differ by more than 5 percent or 1 hour."
        return {"horizons_agreement_pct": trim(round(hours["median_abs_difference_pct"], 2), 2),
                "horizons_largest_pct": trim(round(hours["largest_abs_difference_pct"], 1), 1),
                "horizons_places": WORDS[places] if places < len(WORDS) else exact(places),
                "horizons_spells_pct": trim(round(spells["median_abs_difference_pct"], 2), 2),
                "horizons_spells_largest_pct": trim(round(spells["largest_abs_difference_pct"], 0), 0),
                "horizons_spells_largest_h": trim(round(spells["largest_abs_difference_h"], 1), 1),
                "horizons_flag_sentence": flag}
    except (TypeError, KeyError):
        return dict.fromkeys(keys, NOT_YET)


def values_factors(inputs: dict) -> dict:
    """The table of factors (factor_matrix.json): how many factors, and how many of each status."""
    keys = ("factors_total", "factors_ranked", "factors_shown", "factors_rough", "factors_not_built",
            "factors_planet_only", "factor_not_built_names", "factor_planet_only_names")
    matrix = inputs.get("factors")
    try:
        meta, rows = matrix["meta"], matrix["rows"]
        counts = meta["counts_by_status"]
        if sum(counts.values()) != len(rows):
            raise BuildError("factor_matrix.json: the counts by status do not add up to the number of rows")
        names = lambda status: " and ".join(r["name"].lower() for r in rows if r["status"] == status) or "none"
        return {"factors_total": exact(len(rows)),
                "factors_ranked": exact(counts.get("measured and used in the ranking", 0)),
                "factors_shown": exact(counts.get("measured and shown", 0)),
                "factors_rough": exact(counts.get("rough estimate by our own rule", 0)),
                "factors_not_built": exact(counts.get("not built", 0)),
                "factors_planet_only": exact(counts.get("planet side only", 0)),
                "factor_not_built_names": names("not built"),
                "factor_planet_only_names": names("planet side only")}
    except (TypeError, KeyError):
        return dict.fromkeys(keys, NOT_YET)


def values_mars(inputs: dict) -> dict:
    """The Mars first pass: squares, sites and their lists, the closest squares on all five factors, the cold gap,
    the known-site test. The sites come from mars_sites.json, the left-out 2015 zones from mars_sites_base.json."""
    keys = ("mars_square_deg", "mars_square_km", "mars_squares_ranked", "mars_min_bare_pct", "mars_full_regions",
            "mars_full_low", "mars_full_high", "mars_landscape_ties_low", "mars_landscape_ties_high",
            "mars_cold_highest", "mars_coldest_c", "mars_colder_low", "mars_colder_high", "mars_pressure_low",
            "mars_pressure_high", "mars_known_squares", "mars_auc_landscape_low", "mars_auc_landscape_high",
            "mars_auc_bare", "mars_known_bare_squares", "mars_auc_bare_full_low", "mars_auc_bare_full_high",
            "mars_sites_total", "mars_nasa_landed", "mars_nasa_landed_names", "mars_2021", "mars_2021_names",
            "mars_2015_on_list", "mars_2015_own", "mars_2015_shared", "mars_other_studied", "mars_other_studied_names",
            "mars_zones_total", "mars_zones_left_out", "mars_zones_left_out_names", "mars_zones_same_place")
    cells, sites, test = inputs.get("mars_cells"), inputs.get("mars_sites"), inputs.get("mars_validation")
    try:
        meta = cells["meta"]
        cards = {site["id"]: site for site in sites["sites"]}
        ids = mars_ids(inputs)
        on = lambda name: [s for s in ids if name in cards[s]["lists"]]
        landed, short_2021, zones = on(LIST_NASA), on(LIST_2021), on(LIST_2015)
        own_zone = [s for s in zones if cards[s]["kind"] == "proposed as an exploration zone in 2015"]
        others = [s for s in ids if not cards[s]["lists"] or
                  (cards[s]["kind"] == "studied for a human landing" and s not in short_2021)]
        if len(landed) + len(short_2021) + len(own_zone) + len(others) != len(ids):
            raise BuildError("mars_sites.json: the sites do not divide into the NASA landing sites, the 2021 shortlist, "
                             "the zones of their own and the other studied sites; reword the Mars list text")
        leaders = {s: cells["best_places"][s]["full"][0] for s in ids}
        by_region: dict[str, int] = {}
        for place in leaders.values():
            by_region[place["region"]] = by_region.get(place["region"], 0) + 1
        coldest = min(c["t2m_year_c"] for c in cells["cells"].values() if c.get("t2m_year_c") is not None)
        colder = [coldest - cards[s]["climate"]["annual_mean_c"] for s in ids]
        pressure = [next(row["number"] for row in cards[s]["cannot_match"] if row["what"] == "surface air pressure")
                    for s in ids]
        summary = meta["factor_summary"]
        all_land, bare = test["test_against_all_land"], test["test_against_bare_squares"]
        two = lambda v: trim(round(v, 2), 2)
        left = [entry for entry in (inputs.get("mars_base") or {}).get("meta", {}).get("left_out", [])
                if entry["what"].startswith("exploration zone") and "as a site of its own" not in entry["what"]]
        same = [entry for entry in (inputs.get("mars_base") or {}).get("meta", {}).get("left_out", [])
                if entry["what"].startswith("exploration zone") and "as a site of its own" in entry["what"]]
        zone_file = inputs.get("zones_2015") or {}
        short_name = lambda s: cards[s]["name"].split(" (")[0]

        def mission(s: str) -> str:
            """'Gale crater, Curiosity landing site' -> 'Curiosity'."""
            parts = [p.strip() for p in cards[s]["name"].split(",")]
            found = next((p.replace(" landing site", "") for p in parts if "landing site" in p), cards[s]["name"])
            return found.split(" (")[0]

        def codes_2021(sites_2021: list[str]) -> str:
            """'PM-1 and PM-7 (Phlegra Montes), AP-1, AP-8 and AP-9 (Arcadia Planitia), ...' in the order of the file."""
            groups: dict[str, list[str]] = {}
            for s in sites_2021:
                found = re.search(r"\b([A-Z]{2}-\d+)\b", cards[s]["name"])
                groups.setdefault(short_name(s), []).append(found.group(1) if found else cards[s]["name"])
            return "; ".join(and_list(sorted(codes, key=lambda c: (c[:2], int(c[3:]) if c[3:].isdigit() else 0)))
                             + f" ({region})" for region, codes in groups.items())

        def zone_label(entry: dict) -> str:
            """'1030 (South-western Meridiani Planum (Endeavour crater area))' -> 'zone 1030 (South-western Meridiani Planum)'."""
            number, _, name = entry["what"].replace("exploration zone ", "").partition(" ")
            return f"zone {number} ({name.strip()[1:].split(' (')[0].rstrip(')')})"
        out = {
            "mars_square_deg": trim(meta["square_deg"], 2),
            "mars_square_km": exact(meta["square_km_about"]),
            "mars_squares_ranked": approx(meta["counts"]["squares_kept_bare_at_least_0.15"]),
            "mars_min_bare_pct": pct(meta["min_bare"]),
            "mars_full_regions": regions_text(by_region, limit=4),
            "mars_landscape_ties_low": exact(min(meta["best_places_tied_at_top"][s]["landscape"] for s in ids)),
            "mars_landscape_ties_high": exact(max(meta["best_places_tied_at_top"][s]["landscape"] for s in ids)),
            "mars_cold_highest": two(max(summary[s]["cold"]["highest"] for s in ids)),
            "mars_coldest_c": trim(round(coldest, 1), 1).replace("-", "minus "),
            "mars_colder_low": trim(round(min(colder), 0), 0), "mars_colder_high": trim(round(max(colder), 0), 0),
            "mars_pressure_low": pct(min(pressure), 2), "mars_pressure_high": pct(max(pressure), 2),
            "mars_known_squares": exact(test["meta"]["test"]["known_squares"]),
            "mars_known_bare_squares": exact(test["meta"]["test"]["known_squares_bare_at_least_0.15"]),
            "mars_auc_bare": pct(all_land[ids[0]]["bare"]["auc"]),
            "mars_sites_total": exact(len(ids)),
            "mars_nasa_landed": number_word(len(landed)),
            "mars_nasa_landed_names": and_list([mission(s) for s in landed]),
            "mars_2021": number_word(len(short_2021)),
            "mars_2021_names": codes_2021(short_2021),
            "mars_2015_on_list": exact(len(zones)),
            "mars_2015_own": exact(len(own_zone)),
            "mars_2015_shared": number_word(len(zones) - len(own_zone)),
            "mars_other_studied": number_word(len(others)),
            "mars_other_studied_names": and_list([short_name(s) for s in others]),
            "mars_zones_total": exact(zone_file["meta"]["counts"]["zones"]) if zone_file else NOT_YET,
            "mars_zones_left_out": number_word(len(left)),
            "mars_zones_left_out_names": and_list([zone_label(e) for e in left]),
            "mars_zones_same_place": number_word(len(same)),
            "_mars_cold_at_1": sum(summary[s]["cold"]["squares_at_1"] for s in ids),
        }
        out["mars_full_low"], out["mars_full_high"] = low_high([p["score"] for p in leaders.values()], two)
        out["mars_auc_landscape_low"], out["mars_auc_landscape_high"] = low_high(
            [all_land[s]["landscape"]["auc"] for s in ids], pct)
        out["mars_auc_bare_full_low"], out["mars_auc_bare_full_high"] = low_high(
            [bare[s]["full"]["auc"] for s in ids], pct)
        out["_mars_bare_full_high"] = max(bare[s]["full"]["auc"] for s in ids)
        return out
    except (TypeError, KeyError, StopIteration):
        out = dict.fromkeys(keys, NOT_YET)
        out.update({"_mars_cold_at_1": None, "_mars_bare_full_high": None})
        return out


def values_access(inputs: dict) -> tuple[dict, list[str]]:
    """Reachable places: ranked northern areas with 100 hours or more, by distance to a runway with scheduled service."""
    keys = ("access_text", "access_method_line", "access_reference_line")
    access = inputs.get("access")
    if access is None:
        return {k: NOT_YET for k in keys}, ["access_cells.json is not there: the reachable-places text says " + NOT_YET]
    try:
        records = access["cells"]
        ranked = ranked_north(inputs["scored"])

        def runway(cell):
            record = records.get(cell["id"]) or {}
            return record.get("nearest_scheduled")

        def within(target, km=100.0):
            rows = [c for c in ranked if (c["targets"][target]["long_open_hours"] or 0.0) >= 100.0]
            near = [c for c in rows if runway(c) is not None and runway(c)["km"] <= km]
            return rows, lighting_order(near, target)

        sentences = []
        names = region_names(inputs)
        rows, near = within(EXAMPLE_REGION)
        sentences.append(f"For {names[EXAMPLE_REGION]}, {approx(len(rows))} areas in our northern ranking have "
                         "100 hours or more a year.")
        sentences.append(f"Of these, {approx(len(near))} lie within 100 km of a runway with scheduled flights.")
        highest = regions(inputs)[-1]
        for target, name in ((EXAMPLE_REGION, names[EXAMPLE_REGION]), (highest, names[highest])):
            _, near = within(target)
            if not near:
                sentences.append(f"For {name}, no such area lies within 100 km of such a runway.")
                continue
            best = near[0]
            field = runway(best)
            sentences.append(f"For {name}, the best such area by light is in {best['region']}.")
            sentences.append(f"Its nearest such runway is {field['name']}, {approx(field['km'])} km away.")
            sentences.append(f"It has {approx(best['targets'][target]['long_open_hours'])} hours a year.")
        sentences.append("These are straight-line distances from a volunteer-edited table of airfields.")
        sentences.append("We did not check roads, boats, permits, flight timetables or cost.")
        source = access["meta"]["source"]
        return {
            "access_text": " ".join(sentences),
            "access_method_line": ("Reach: the straight-line distance from each area to the nearest runway, "
                                   "from the OurAirports table."),
            "access_reference_line": f"{source['name']} ({source['licence']}): {source['url']}",
        }, []
    except (KeyError, TypeError, AttributeError) as error:
        return {k: NOT_YET for k in keys}, [
            f"access_cells.json is there but could not be read as expected ({type(error).__name__}: {error}); "
            "the reachable-places text says " + NOT_YET]


def merged_regions(counts: dict) -> dict:
    """'Norway: Vestland' and 'Norway: Troms' are counted together as 'Norway'; zero counts are dropped."""
    merged: dict[str, int] = {}
    for name, n in counts.items():
        if n:
            short = name.split(":")[0].strip()
            merged[short] = merged.get(short, 0) + n
    return merged


def values_winter_leads(inputs: dict) -> tuple[dict, list[str]]:
    """Small bare patches under the 15 percent screen, for the widest band (the region with the highest Sun), winter half."""
    keys = ("winter_leads_text", "winter_leads_short")
    leads = inputs.get("winter_leads")
    if leads is None:
        return {k: NOT_YET for k in keys}, ["winter_leads.json is not there: the small-bare-patch text says " + NOT_YET]
    try:
        floor = leads["meta"]["floor_bare_km2"]
        top = region_names(inputs)[regions(inputs)[-1]]
        target = leads["targets"][regions(inputs)[-1]]
        flat = merged_regions(target["counts_by_region"]["100"])
        hills = merged_regions(target["counts_by_region_after_terrain"]["100"])
        total, total_hills = sum(flat.values()), sum(hills.values())
        rim = {name: flat.get(name, 0) for name in ("Shetland", "Orkney", "Faroe Islands")}
        malapert = leads["targets"][EXAMPLE_REGION]
        m_flat = merged_regions(malapert["counts_by_region"]["100"])
        m_hills = merged_regions(malapert["counts_by_region_after_terrain"]["100"])
        m_total, m_total_hills = sum(m_flat.values()), sum(m_hills.values())
        # every sentence names its one lunar region, so that no figure of one is read as the other's
        def where(counts: dict) -> str:
            """', all in Iceland.' for one region; ': Iceland 8, Norway 1.' for several; '.' for none."""
            if not counts:
                return "."
            if len(counts) == 1:
                return f", all in {next(iter(counts))}."
            return ": " + regions_text(counts) + "."

        sentences = [
            f"Below our screen, {approx(m_total)} more areas hold at least {trim(floor)} km2 of bare ground "
            "and reach 100 winter hours for Malapert Massif.",
            f"With real hills counted, {approx(m_total_hills)} of them keep 100 hours for Malapert Massif"
            + where(m_hills),
            f"For {top}, the lunar region with the highest Sun, the count is {approx(total)}.",
        ]
        if flat:
            sentences.append(f"For {top} they lie in: " + regions_text(flat) + ".")
        sentences.append(f"On the Atlantic rim the {top} counts are: "
                         + ", ".join(f"{name} {exact(n)}" for name, n in rim.items()) + ".")
        sentences.append("A zero means our land-cover sample shows no bare patch that large with a trusted snow record.")
        if total_hills:
            sentences.append(f"With real hills counted, {approx(total_hills)} keep 100 hours for {top}"
                             + where(hills))
        else:
            sentences.append(f"With real hills counted, none keeps 100 hours for {top}.")
        sentences.append("No cloud is counted here, and the Atlantic rim is very cloudy in winter.")
        sentences.append("These figures rest on few land-cover samples and few snow pixels.")
        sentences.append("Treat them as leads to check, not as results.")
        short = (f"{approx(m_total)} more areas with at least {trim(floor)} km2 of bare ground reach 100 winter hours "
                 "for Malapert Massif")
        return {"winter_leads_text": " ".join(sentences), "winter_leads_short": short}, []
    except (KeyError, TypeError, AttributeError) as error:
        return {k: NOT_YET for k in keys}, [
            f"winter_leads.json is there but could not be read as expected ({type(error).__name__}: {error}); "
            "the small-bare-patch text says " + NOT_YET]


def compute_values(inputs: dict, now: datetime | None = None) -> tuple[dict, list[str]]:
    """Every placeholder of the template, as text. Keys that start with '_' are raw numbers for check_claims."""
    now = now or datetime.now()
    values = dict(FIXED_FACTS)
    values["generated_on"] = f"{now.day} {MONTHS[now.month - 1]} {now.year} at {now:%H:%M}"
    values["summary_max_words"] = exact(SUMMARY_MAX_WORDS)
    values["summary_max_chars"] = exact(SUMMARY_MAX_CHARS)
    values["max_words"] = exact(MAX_WORDS)
    for group in (values_search, values_moon, values_latitude, values_seasons, values_ridge_and_best, values_terrain,
                  values_cloud, values_midnight, values_known, values_checks, values_horizons, values_factors,
                  values_mars, values_credits):
        values.update(group(inputs))
    notes = []
    for group in (values_access, values_winter_leads):
        found, group_notes = group(inputs)
        values.update(found)
        notes.extend(group_notes)
    if inputs.get("count_check") is None:
        notes.append("no count_check_v*.json: the recount figures say " + NOT_YET)
    if inputs.get("snow_check") is None:
        notes.append("snow_validation_many.json is not there: the station figures say " + NOT_YET)
    for key, name in (("factors", "factor_matrix.json"), ("mars_cells", "mars_cells.json"),
                      ("mars_sites", "mars_sites.json"), ("mars_validation", "mars_validation.json")):
        if inputs.get(key) is None:
            notes.append(f"{name} is not there: the text that needs it says " + NOT_YET)
    return values, notes


# ---------------------------------------------------------------- words that depend on the data

def check_claims(inputs: dict, values: dict) -> None:
    """The template says these things in words. If the data stops supporting one, stop and say which."""
    broken = []
    extras, validation = inputs["extras"], inputs["validation"]
    targets = regions(inputs)
    lowest, highest = targets[0], targets[-1]
    low = extras["lower_latitude_sites"]["summary"]
    if any(low[t]["sites_with_a_2h_spell"] for t in targets):
        broken.append("'none of the lower-latitude places has a spell of two hours': validation_extras.json now lists one")
    big = validation["big_picture_north"]["targets"]
    for t in targets:
        calendar = big[t]["calendar_hours_times_bare_km2"]
        winter = set(winter_bins(inputs["profile"]))
        if sum(v for i, v in enumerate(calendar) if i in winter) / sum(calendar) > 0.10:
            broken.append(f"'nearly all usable hours fall in the summer half': the winter share for {t} is now over 10 percent")
        after = extras["latitude_against_full_method"]["targets"][t]["winter_half"]["all_measured_cells"]
        if after["sun_alone"]["cells"] and after["after_snow"]["cells"] > 0.05 * after["sun_alone"]["cells"]:
            broken.append(f"'in winter the ground is under snow almost everywhere': over 5 percent of areas keep their hours for {t}")
    ridge = big[lowest]["long_snow_free_hours"]["summer_half"]["100"]["cells"]
    top = big[highest]["long_snow_free_hours"]["summer_half"]["100"]["cells"]
    if ridge > 0.01 * top:
        broken.append(f"'the lowest region has almost no match': {ridge} areas now reach 100 hours for {lowest}")
    if values["_lowest_year_100_after_hills"]:
        broken.append(f"'after real hills no area reaches 100 hours for {lowest}': some areas now do")
    census = values["_terrain_census"]
    if any(later < earlier - 0.01 for earlier, later in zip(census, census[1:])):
        broken.append("'the lower the Sun ceiling, the smaller the share of hours that the hills leave': "
                      "the census medians no longer increase with the Sun ceiling")
    if not values["_peak_moves_earlier"]:
        broken.append("'with cloud counted, the busiest periods move earlier': they no longer do")
    if values["_mars_cold_at_1"] not in (None, 0):
        broken.append("'no square reaches a full cold score for any Mars site': mars_cells.json now has one")
    if values["_mars_bare_full_high"] is not None and values["_mars_bare_full_high"] >= 0.6:
        broken.append("'among bare squares, the scores do not find the known analog sites much better than a random "
                      "order': an AUC on all factors is now 0.6 or more")
    if not (20.0 <= values["_known_percentile_low"] and values["_known_percentile_high"] <= 67.0):
        broken.append("'known analog sites come out middling': a median percentile is now outside 20 to 67")
    if 2 * values["_haughton_high_n"] <= values["_regions_n"]:
        broken.append("'Haughton crater comes out in the top third for most regions': it now does for half or fewer")
    if values["_north_sun_share"] <= 0.5:
        broken.append("'slightly over half with the Sun in the northern sky': the Sun is no longer in the north "
                      "for most of the hours")
    if values["_recount_outside_tolerance"] not in (None, 0):
        broken.append("'the recount reproduced the hours of every area': some figures are now outside its tolerance")
    if values["_snow_bias_sign_ok"] is False:
        broken.append("'the snow maps lean toward more snow than the stations': the sign of the difference has changed")
    cards = {card["id"]: card for card in inputs["moon"]["cards"]}
    if cards[lowest]["nasa_list"]["on_2024_list_of_9"] or not cards[lowest]["nasa_list"]["on_2022_list_of_13"]:
        broken.append(f"'{lowest} is on the 2022 list only': moon_cards.json disagrees")
    mouton = cards["mons-mouton"]["nasa_list"]
    if mouton.get("name_2022") != "Leibnitz Beta Plateau" or mouton.get("name_2024") != "Mons Mouton":
        broken.append("'NASA's map of 2024 has the box Mons Mouton at the place of the 2022 box Leibnitz Beta Plateau': "
                      "moon_cards.json no longer says so")
    if values["_regions_outside_search_n"] == 0:
        broken.append("'for some regions, long spells begin south of our search band': they now begin inside the band")
    if values["_without_model_n"] == 0:
        broken.append("'some regions have no NASA 5 m terrain model': moon_cards.json now has a model for each")
    if broken:
        raise ClaimNoLongerHolds("the template says things the data no longer supports; rewrite these sentences in "
                                 "docs/submission_template.md (and the test in check_claims):\n  - " + "\n  - ".join(broken))


# ---------------------------------------------------------------- filling the template

PLACEHOLDER = re.compile(r"\{([a-z][a-z0-9_]*)\}")


def placeholders_in(template: str) -> list[str]:
    seen = []
    for name in PLACEHOLDER.findall(template):
        if name not in seen:
            seen.append(name)
    return seen


def fill(template: str, values: dict, fallbacks: dict | None = None) -> str:
    """Replace every {name}. A name with no value and no fallback raises MissingValue, naming all such names."""
    fallbacks = fallbacks or {}
    missing = [name for name in placeholders_in(template)
               if values.get(name) is None and fallbacks.get(name) is None]
    if missing:
        raise MissingValue("placeholder(s) in the template with no value and no fallback: " + ", ".join(sorted(missing)))

    def swap(match: re.Match) -> str:
        name = match.group(1)
        value = values.get(name)
        return str(value if value is not None else fallbacks[name])

    return PLACEHOLDER.sub(swap, template)


GAP = re.compile(r"\[(?:[A-Z][A-Z0-9 ,:'/\-]{2,}|not yet measured)\]")


def team_gaps(text: str) -> list[tuple[str, list[str]]]:
    """Every square-bracket gap in the text, with the headings under which it stands."""
    found: dict[str, list[str]] = {}
    heading = "the top of the file"
    for line in text.splitlines():
        if line.startswith("#"):
            heading = line.lstrip("#").strip()
            continue
        for gap in GAP.findall(line):
            places = found.setdefault(gap, [])
            if heading not in places:
                places.append(heading)
    return list(found.items())


def gaps_block(text: str, notes: list[str]) -> str:
    lines = []
    for gap, places in team_gaps(text):
        where = "; ".join(f'"{place}"' for place in places[:3])
        more = f"; and {len(places) - 3} more" if len(places) > 3 else ""
        lines.append(f"- {gap} stands under: {where}{more}")
    for note in notes:
        lines.append(f"- Note from the script: {note}")
    return "\n".join(lines) if lines else "- Nothing is left to fill in."


# ---------------------------------------------------------------- checking the result

URL = re.compile(r"https?://\S+")
LIST_MARK = re.compile(r"^\s*(?:[-*+]|\d+[.)]|[A-D]\.)\s+")
SENTENCE_END = re.compile(r"(?<=[.!?])\s+|(?<=[.!?][\"')\]])\s+")


def word_count(text: str) -> int:
    return sum(1 for token in text.split() if any(ch.isalnum() for ch in token))


def sentences(markdown: str, skip_exact_wording: bool = True) -> list[str]:
    """The prose of a markdown text, sentence by sentence. A list item, a table cell and a heading each start afresh."""
    found, skipping = [], False
    for raw in markdown.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            title = line.lstrip("#").strip()
            # exact credit lines run from their heading to the next heading of any level
            skipping = skip_exact_wording and EXACT_WORDING_MARK in title.lower()
            found.append(title)
            continue
        if skipping:
            continue
        if line.startswith("|"):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            pieces = [cell for cell in cells if cell and not set(cell) <= set("-: ")]
        else:
            pieces = [LIST_MARK.sub("", line.lstrip("> ").strip())]
        for piece in pieces:
            piece = URL.sub("URL", piece.replace("**", "").replace("`", ""))
            found.extend(part.strip() for part in SENTENCE_END.split(piece) if part.strip())
    return found


def long_sentences(markdown: str, limit: int = MAX_WORDS) -> list[tuple[int, str]]:
    return [(word_count(s), s) for s in sentences(markdown) if word_count(s) > limit]


def form_text(markdown: str, name: str) -> str:
    """The lines between '*BEGIN TEXT FOR THE FORM: name*' and '*END TEXT FOR THE FORM: name*'."""
    begin, end = f"*BEGIN TEXT FOR THE FORM: {name}*", f"*END TEXT FOR THE FORM: {name}*"
    if begin not in markdown or end not in markdown:
        raise OutputCheckFailed(f"no block of form text named '{name}' in the file")
    return markdown.split(begin, 1)[1].split(end, 1)[0].strip()


def lead_candidates(markdown: str) -> list[str]:
    """The four offered lead sentences: lines that start with 'A. ' to 'D. ' followed by a quoted text."""
    return re.findall(r'^[A-D]\. "([^"]+)"', markdown, flags=re.MULTILINE)


def summary_size(markdown: str) -> tuple[int, int]:
    """Words and characters of the short summary with the longest of the lead candidates put in."""
    summary = form_text(markdown, "summary")
    candidates = lead_candidates(markdown) or [""]
    longest = max(candidates, key=len)
    whole = summary.replace(LEAD_GAP, longest)
    return word_count(whole), len(whole)


def check_output(text: str) -> None:
    problems = []
    if "{" in text or "}" in text:
        left = sorted(set(re.findall(r"\{[^{}\n]{0,40}\}?", text)))
        problems.append("curly braces are left in the text: " + ", ".join(left[:8]))
    too_long = long_sentences(text)
    if too_long:
        problems.append(f"{len(too_long)} sentence(s) over {MAX_WORDS} words:\n      "
                        + "\n      ".join(f"{n} words: {s}" for n, s in too_long[:12]))
    words, chars = summary_size(text)
    if words > SUMMARY_MAX_WORDS or chars > SUMMARY_MAX_CHARS:
        problems.append(f"the short summary is {words} words and {chars} characters with its longest lead sentence; "
                        f"the working limit is {SUMMARY_MAX_WORDS} words and {SUMMARY_MAX_CHARS} characters")
    if problems:
        raise OutputCheckFailed("SUBMISSION.md was not written:\n  - " + "\n  - ".join(problems))


# ---------------------------------------------------------------- the build

def build(template: str, inputs: dict, now: datetime | None = None) -> tuple[str, list[str]]:
    values, notes = compute_values(inputs, now)
    check_claims(inputs, values)
    public = {name: value for name, value in values.items() if not name.startswith("_")}
    public["team_gaps"] = "{team_gaps}"                       # filled last, from the finished text
    text = fill(template, public)
    text = text.replace("{team_gaps}", gaps_block(text.replace("{team_gaps}", ""), notes))
    check_output(text)
    return text, notes


def write_whole(path: Path, text: str) -> None:
    part = path.with_name(path.name + ".part")
    part.write_text(text, encoding="utf-8")
    os.replace(part, path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fill the submission template from the data files.")
    parser.add_argument("--derived", type=Path, default=DERIVED, help="folder with the data files")
    parser.add_argument("--template", type=Path, default=TEMPLATE)
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--check", action="store_true", help="build and check, write nothing")
    args = parser.parse_args(argv)
    try:
        if not args.template.exists():
            raise MissingInput(f"template not found: {args.template}")
        text, notes = build(args.template.read_text(encoding="utf-8"), load_inputs(args.derived))
    except BuildError as error:
        print(f"build_submission: STOPPED. {type(error).__name__}: {error}", file=sys.stderr)
        return 1
    except (KeyError, IndexError, TypeError, ValueError) as error:
        print("build_submission: STOPPED. A required data file does not hold a field this script reads "
              f"({type(error).__name__}: {error}). Nothing was written; the script needs to be brought in line "
              "with the data files.", file=sys.stderr)
        return 1
    if not args.check:
        write_whole(args.out, text)
    words, chars = summary_size(text)
    gaps = team_gaps(text)
    description = form_text(text, "description")
    print(f"build_submission: {'checked' if args.check else 'wrote ' + args.out.name}; "
          f"{len(sentences(text))} sentences, none over {MAX_WORDS} words; summary {words} words, {chars} characters; "
          f"description {word_count(description)} words, {len(description)} characters; "
          f"{len(gaps)} gap(s) for the team")
    for note in notes:
        print(f"  note: {note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

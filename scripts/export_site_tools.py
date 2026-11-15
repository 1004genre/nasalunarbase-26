# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Write the data behind the round 3 tools of the map page (site/data).

    uv run python scripts/export_site.py           # first: it decides the order of the areas
    uv run python scripts/export_site_tools.py     # then this (any time after)

Only numpy and the standard library. Nothing under data/ is written. Every number comes from the
pipeline's files or the page's own files; the words are ours and no sentence has more than 25 words.

Writes, into site/data:
    famous.json        feature 1: for each well-known analog site and lunar region, the step that removes it or costs it most
    basis.json         feature 2: what each step rests on, the two check figures, the assumptions for the fold-out
    search.json        feature 3: an index for the place-name search box
    glossary.json      feature 4: one line for each word the page uses
    tour.json          feature 5: the timed tour, at most eight steps of the guided views
    access.bin         feature 12: uint16 [areas, 4]: nearest scheduled airfield and nearest airfield, index and km; 65535 = unknown
    airfields.json     feature 12: the airfields access.bin points at, and what the distance is not
    winter_leads.json  feature 12: the winter list of small bare patches, trimmed to what a list shows
    tools.json         an index of the files above: layouts, inputs and when each input was written

An optional input that is not there leaves its output out (or a figure null) and the run says so.
Unknown is null in JSON and 65535 in access.bin; it is never 0.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
MAX_WORDS = 25                   # the page's rule: no sentence over 25 words
UNKNOWN_U16 = 65535              # the unknown value of access.bin
EARTH_KM = 6371.0                # the sphere the pipeline's distances use (access_cells.json earth_radius_km)
SEARCH_MIN_HOURS = 50.0          # feature 3: airfields near areas with at least this many low-Sun hours after terrain
SEARCH_AIRFIELD_KM = 200.0       # ... within this distance
SEARCH_MAX_BYTES = 300_000       # feature 3: keep the index under this size
TOUR_SECONDS = 60                # feature 5: about one minute in all
TOUR_MAX_STEPS = 8
TOUR_MIN_STEP_SECONDS = 5
STEPS = ("sun", "snow", "hills", "cloud")
STEP_LABELS = {"sun": "no two-hour spell at its latitude", "snow": "snow", "hills": "hills", "cloud": "cloud",
               "holds-up": "it holds up"}
STEP_LABELS_SOUTH = {**STEP_LABELS, "snow": "rock season only (snow not measured)"}


class ToolsError(Exception):
    """An input does not say what the page needs; the output it feeds is not written."""


# ---- small helpers ----

def read_json(path: Path):
    with open(path) as handle:
        return json.load(handle)


def write_bytes(path: Path, data: bytes) -> int:
    """Write beside the target and rename, so a reader never sees half a file."""
    side = path.with_name(path.name + ".part")
    side.write_bytes(data)
    os.replace(side, path)
    return len(data)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def modified(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def known(value) -> bool:
    return value is not None and not (isinstance(value, float) and math.isnan(value))


def word_count(sentence: str) -> int:
    return len(sentence.split())


def sentences_of(text: str) -> list[str]:
    return [part for part in re.split(r"(?<=[.!?])\s+", text.strip()) if part]


def short_enough(text: str) -> bool:
    return all(word_count(s) <= MAX_WORDS for s in sentences_of(text))


def say(template: str, **values) -> str | None:
    """The template filled in, or None when any value is unknown."""
    if any(not known(v) for v in values.values()):
        return None
    return template.format(**values)


def first_short(*candidates) -> str | None:
    """The first candidate that is known and has no sentence over 25 words."""
    for text in candidates:
        if text is not None and short_enough(text):
            return text
    return None


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, inner in value.items():
            yield key
            yield from _strings(inner)
    elif isinstance(value, list):
        for inner in value:
            yield from _strings(inner)


def checked_json(value) -> bytes:
    """Compact JSON, refused when any sentence in it runs over 25 words or a number is not finite."""
    for text in _strings(value):
        for sentence in sentences_of(text):
            if word_count(sentence) > MAX_WORDS:
                raise ToolsError(f"a sentence has {word_count(sentence)} words: {sentence[:80]!r}")
    return json.dumps(value, separators=(",", ":"), allow_nan=False, ensure_ascii=False).encode()


def hours(value) -> str | None:
    """Whole hours with a thousands comma, halves rounded up."""
    return None if not known(value) else f"{int(math.floor(value + 0.5)):,}"


def whole(value) -> int:
    return int(math.floor(value + 0.5))


def percent(share) -> str | None:
    return None if not known(share) else f"{whole(share * 100)}"


def count(value) -> str | None:
    return None if not known(value) else f"{int(value):,}"


def small_number(value) -> str | None:
    """A decimal figure as written, without a trailing .0."""
    if not known(value):
        return None
    return f"{value:g}"


NUMBER_WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine"}

SPECIAL = str.maketrans({"ø": "o", "Ø": "O", "æ": "ae", "Æ": "Ae", "ð": "d", "Ð": "D", "þ": "th", "Þ": "Th", "ß": "ss",
                         "ł": "l", "Ł": "L", "đ": "d", "Đ": "D", "ı": "i", "œ": "oe", "Œ": "Oe", "’": "'", "‘": "'",
                         "“": '"', "”": '"', "–": "-", "—": "-"})


def ascii_name(text: str) -> str:
    """The name in plain ASCII: accents dropped, the few letters without a plain form spelled out."""
    decomposed = unicodedata.normalize("NFKD", text.translate(SPECIAL))
    plain = "".join(c for c in decomposed if not unicodedata.combining(c)).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", plain).strip()


def km_from(lat: float, lon: float, lats: np.ndarray, lons: np.ndarray) -> np.ndarray:
    """Great-circle distance in km from one point to many."""
    p1, p2 = math.radians(lat), np.radians(lats)
    dlat, dlon = p2 - p1, np.radians(lons - lon)
    a = np.sin(dlat / 2) ** 2 + math.cos(p1) * np.cos(p2) * np.sin(dlon / 2) ** 2
    return 2 * EARTH_KM * np.arcsin(np.minimum(1.0, np.sqrt(a)))


# ---- the page's areas and lunar regions ----

def areas_of(cells_doc: dict) -> dict:
    """The page's areas in the page's order: ids, centres in degrees, hemisphere, region names."""
    ids = cells_doc.get("ids")
    if not isinstance(ids, list) or not ids:
        raise ToolsError("site/data/cells.json has no list of ids")
    index = {}
    for position, area_id in enumerate(ids):
        if area_id in index:
            raise ToolsError(f"site/data/cells.json lists the area {area_id} twice")
        index[area_id] = position
    units = cells_doc.get("units") or {}
    for key in ("lat", "lon"):
        if "hundredths" not in str(units.get(key, "")):
            raise ToolsError(f"site/data/cells.json: {key} is expected in hundredths of a degree, it says {units.get(key)!r}")
        if len(cells_doc.get(key) or []) != len(ids):
            raise ToolsError(f"site/data/cells.json: {key} has not one value for each id")
    lat = [v / 100.0 for v in cells_doc["lat"]]
    lon = [v / 100.0 for v in cells_doc["lon"]]
    letters = cells_doc.get("hemisphere")
    hemisphere = list(letters) if isinstance(letters, str) and len(letters) == len(ids) else ["N" if v > 0 else "S" for v in lat]
    names, rows = cells_doc.get("regions"), cells_doc.get("region")
    region = ([names[r] if isinstance(r, int) and 0 <= r < len(names) else None for r in rows]
              if names and rows and len(rows) == len(ids) else None)
    return {"ids": list(ids), "index": index, "lat": lat, "lon": lon, "hemisphere": hemisphere, "region": region}


def targets_of(meta: dict) -> list[dict]:
    """The lunar regions in the page's order with official names, short names and Sun ceilings."""
    targets = (meta or {}).get("targets")
    if not isinstance(targets, list) or not targets:
        raise ToolsError("site/data/meta.json has no list of targets")
    out = []
    for t in targets:
        if not isinstance(t, dict) or "id" not in t or "name" not in t:
            raise ToolsError("site/data/meta.json: a target has no id or name")
        out.append({"id": t["id"], "name": t["name"], "short": t.get("short") or t["name"], "limit_deg": t.get("limit_deg")})
    return out


def nearest_area(lat: float, lon: float, areas: dict, among: list[int] | None = None) -> tuple[str | None, float | None]:
    """The page's area whose centre is nearest, and how far that centre is, in km to a tenth."""
    if not known(lat) or not known(lon):
        return None, None
    rows = np.arange(len(areas["ids"])) if among is None else np.asarray(among)
    if rows.size == 0:
        return None, None
    lats, lons = areas["_lat"][rows], areas["_lon"][rows]
    distance = km_from(lat, lon, lats, lons)
    best = int(np.argmin(distance))
    return areas["ids"][int(rows[best])], round(float(distance[best]), 1)


# ---- feature 1: why not the famous sites ----

def _hours_after_steps(row: dict, target: str, south: bool, cloud) -> dict:
    src = (row.get("targets") or {}).get(target) or {}
    return {"sun": src.get("long_flat_hours"),
            "snow": src.get("flat_horizon_hours") if south else src.get("long_snow_free_hours"),
            "hills": src.get("long_open_hours"),
            "cloud": cloud}


def _none_left(value) -> bool:
    """No whole hour left: under half an hour a year."""
    return known(value) and value < 0.5


def _removed_by(hours_after: dict) -> str | None:
    """The first step after which not one whole hour is left (the Sun step: no two-hour spell at all)."""
    if _none_left(hours_after["sun"]):
        return "sun"
    before = hours_after["sun"]
    for step in STEPS[1:]:
        value = hours_after[step]
        if not known(value):
            continue
        if _none_left(value) and known(before) and not _none_left(before):
            return step
        before = value
    return None


def _left(value) -> str | None:
    """Hours left, with a tenth when under one hour."""
    if not known(value):
        return None
    return "0" if value == 0 else (f"{value:.1f}" if value < 1 else hours(value))


def _costliest(hours_after: dict) -> tuple[str | None, float | None]:
    """The step that takes the most hours from the one before it (both known); None when no step takes any."""
    best, loss = None, None
    for before, step in zip(STEPS, STEPS[1:]):
        a, b = hours_after[before], hours_after[step]
        if known(a) and known(b) and a - b > 0 and (loss is None or a - b > loss):
            best, loss = step, a - b
    return best, loss


def _area_sentence(step: str | None, removed: str | None, costliest: str | None, h: dict, short: str, south: bool,
                   rock_text: str | None, in_search: bool, why_out: str | None) -> str | None:
    sun, snow, hills, cloud = (hours(h[k]) for k in STEPS)
    ground = "in the rock season" if south else "on snow-free ground"
    if not in_search or step is None and not known(h["sun"]):
        return why_out
    if removed == "sun":
        return say("Over a flat horizon its area has no two-hour spell under the {short} ceiling.", short=short)
    if removed == "snow" and not south:
        return first_short(say("Snow leaves {left} of its {sun} hours of two-hour spells under the {short} ceiling on snow-free ground.",
                               sun=sun, short=short, left=_left(h["snow"])))
    if removed == "snow" and south:
        return first_short(say("It has {sun} hours of two-hour spells under the {short} ceiling, but none of them are in the "
                               "rock season, {rock}.", sun=sun, short=short, rock=rock_text),
                           say("It has {sun} hours of two-hour spells under the {short} ceiling, but none of them are in the "
                               "rock season.", sun=sun, short=short))
    if removed == "hills":
        return first_short(say("Hills leave {left} of the {snow} {unit} {ground} under the {short} ceiling.",
                               left=_left(h["hills"]), snow=snow, unit=_unit(snow), ground=ground, short=short))
    if removed == "cloud":
        return first_short(say("Typical cloud leaves {left} of the {hills} {unit} after hills under the {short} ceiling.",
                               left=_left(h["cloud"]), hills=hills, unit=_unit(hills), short=short))
    after = "in the rock season after hills" if south else "after snow and hills"
    if step == "holds-up":   # STE wording at the source, as data/reference/ste/moon.json gives it
        return first_short(say("For {short}, no step removes it. It keeps {hills} hours a year {after}, and {cloud} under "
                               "typical cloud. Its area is in the top third of ranked areas.",
                               short=short, hills=hills, after=after, cloud=cloud),
                           say("For {short}, no step removes it. It keeps {hills} hours {after}, and {cloud} under typical "
                               "cloud. Its area is in the top third of ranked areas.",
                               short=short, hills=hills, after=after, cloud=cloud),
                           say("For {short}, no step removes it. It keeps {hills} hours a year {after}. Its area is in the "
                               "top third of ranked areas.", short=short, hills=hills, after=after))
    if costliest is None:
        return None
    name = {"snow": "The rock season limit removes" if south else "Snow removes", "hills": "Hills remove",
            "cloud": "Cloud removes"}[costliest]
    return first_short(   # STE wording at the source, as data/reference/ste/moon.json gives it
        say("{name} the most hours. Under the {short} ceiling, it has {sun} hours of two-hour spells, {snow} {ground}, "
            "{hills} after hills and {cloud} under typical cloud.", name=name, sun=sun, short=short, snow=snow,
            ground=ground, hills=hills, cloud=cloud),
        say("{name} the most hours. It has {sun} hours of two-hour spells, {snow} {ground}, {hills} after hills and "
            "{cloud} under typical cloud.", name=name, sun=sun, snow=snow, ground=ground, hills=hills, cloud=cloud),
        say("{name} the most hours. Under the {short} ceiling, it has {sun} hours of two-hour spells, {snow} {ground} "
            "and {hills} after hills.", name=name, sun=sun, short=short, snow=snow, ground=ground, hills=hills),
        say("{name} the most hours. It has {sun} hours of two-hour spells, {snow} {ground} and {hills} after hills.",
            name=name, sun=sun, snow=snow, ground=ground, hills=hills))


def _unit(figure: str | None) -> str:
    return "hour" if figure == "1" else "hours"


def _why_out(row: dict) -> str:
    reasons = " ".join(row.get("not_ranked_because") or [])
    if "not among the searched" in reasons and "bare" in reasons:
        return "Its area is outside our search: too little bare ground, or no land-cover record."
    return "Its area is outside our search, so we have no figures for it."


def judge_area(row: dict, clouds: dict, targets: list[dict], rock_text: str | None = None) -> dict:
    """Per lunar region: the hours after each step, the step that removes the site or costs it most, and a sentence.

    'holds-up' is our rule of thumb: nothing removes it and its area is in the top third of ranked areas after terrain
    (the source's own verdict 'high').
    """
    south = row.get("hemisphere") == "S"
    in_search = bool(row.get("in_the_search", True))
    out = {}
    for t in targets:
        src = (row.get("targets") or {}).get(t["id"]) or {}
        h = _hours_after_steps(row, t["id"], south, clouds.get(t["id"]))
        if not in_search or not known(h["sun"]):
            step, removed, costliest, loss = None, None, None, None
        else:
            removed = _removed_by(h)
            costliest, loss = _costliest(h)
            step = removed or ("holds-up" if src.get("verdict") == "high" else costliest)
        out[t["id"]] = {
            "hours": h,
            "step": step,
            "removed": removed is not None,
            "costliest": costliest,
            "costliest_loss_h": None if loss is None else round(loss, 1),
            "percentile_among_ranked": src.get("percentile_among_ranked"),
            "rank_from_top": src.get("rank_from_top"),
            "ranked_cells": src.get("ranked_cells"),
            "verdict": src.get("verdict"),
            "sentence": _area_sentence(step, removed, costliest, h, t["short"], south, rock_text, in_search,
                                       None if in_search else _why_out(row)),
        }
    return out


def judge_latitude(site: dict, targets: list[dict]) -> dict:
    """A site outside our search: the Sun-only figures at its latitude."""
    out = {}
    for t in targets:
        src = (site.get("targets") or {}).get(t["id"]) or {}
        has = src.get("has_a_2h_spell")
        sentence = (say("At its latitude, the Sun is under the {short} ceiling for {h} hours a year, but its longest spell is {m} minutes.",
                        h=hours(src.get("hours_a_year_in_band")), short=t["short"], m=src.get("longest_spell_minutes"))
                    if has is False else
                    say("At its latitude the Sun spends {h} hours a year under the {short} ceiling, {h2} of them in two-hour spells.",
                        h=hours(src.get("hours_a_year_in_band")), short=t["short"], h2=hours(src.get("hours_in_spells_of_2h"))))
        out[t["id"]] = {
            "step": "sun" if has is False else None,
            "hours_a_year_in_band": src.get("hours_a_year_in_band"),
            "longest_spell_minutes": src.get("longest_spell_minutes"),
            "longest_spell_h": src.get("longest_spell_h"),
            "hours_in_spells_of_2h": src.get("hours_in_spells_of_2h"),
            "has_a_2h_spell": has,
            "sentence": first_short(sentence),
        }
    return out


FAMOUS_LISTS = (("named_sites_north", "named site"), ("antarctic_sites", "named site"),
                ("known_analogs_poleward_of_59", "known analog site"))


def _named_row(site: dict) -> dict:
    """A named site of validation.json that validation_extras.json lacks, in the shape of an extras row."""
    south = site.get("hemisphere") == "S"
    targets = {}
    for target, block in (site.get("targets") or {}).items():
        targets[target] = {
            "long_flat_hours": ((block.get("flat") or {}).get("long") or {}).get("year"),
            "long_snow_free_hours": ((block.get("snow_free") or {}).get("long") or {}).get("year"),
            "flat_horizon_hours": block.get("long_summer_rock_hours") if south else ((block.get("snow_free") or {}).get("long") or {}).get("year"),
            "long_open_hours": block.get("long_summer_rock_open_hours") if south else ((block.get("open") or {}).get("long") or {}).get("year"),
            "percentile_among_ranked": None, "rank_from_top": None, "ranked_cells": None, "verdict": None}
    return {"name": site.get("name"), "lat": site.get("lat"), "lon": site.get("lon"), "cell": site.get("cell"),
            "hemisphere": site.get("hemisphere"), "in_the_search": True, "region": site.get("region"),
            "snow_status": (site.get("snow") or {}).get("status"), "targets": targets}


def famous(extras: dict, validation_doc: dict | None, scored: dict | None, areas: dict, targets: list[dict],
           rock_text: str | None, cell_km) -> dict:
    """Feature 1. One record per area (sites on the same area are merged), then the lower-latitude sites."""
    lists = (extras.get("known_sites") or {}).get("sites") or {}
    entries, by_area = [], {}

    def clouds_for(cell: str | None, south: bool) -> dict:
        record = (scored or {}).get(cell) if cell else None
        field = "long_summer_rock_open_hours_clear" if south else "long_open_hours_clear"
        return {t["id"]: ((record or {}).get("targets") or {}).get(t["id"], {}).get(field) if record else None for t in targets}

    def add(row: dict, kind: str, source: dict) -> None:
        cell = row.get("cell")
        if cell and cell in by_area:
            entry = by_area[cell]
            if row.get("name") != entry["name"] and row.get("name") not in entry["other_names"]:
                entry["other_names"].append(row["name"])
            return
        south = row.get("hemisphere") == "S"
        in_search = bool(row.get("in_the_search", True))
        entry = {
            "name": row.get("name"),
            "other_names": [],
            "kind": kind,
            "lat": row.get("lat"), "lon": row.get("lon"), "hemisphere": row.get("hemisphere"),
            "basis": "area",
            "basis_text": first_short(say("Figures for the area that holds it, a square about {km} km across.", km=cell_km),
                                      "Figures for the area that holds it."),
            "area": cell if cell in areas["index"] else None,
            "area_in_page": cell in areas["index"],
            "in_search": in_search,
            "ranked": row.get("cell_ranked"),
            "region": row.get("region"),
            "snow_status": row.get("snow_status"),
            "snow_measured": None if not in_search else not south,
            "source": source,
            "targets": judge_area(row, clouds_for(cell, south), targets, rock_text),
        }
        if row.get("tier"):
            entry["tier"] = row["tier"]
        if row.get("analog_for") and short_enough(row["analog_for"]):
            entry["analog_for"] = row["analog_for"]
        entries.append(entry)
        if cell:
            by_area[cell] = entry

    for list_name, kind in FAMOUS_LISTS:
        for position, row in enumerate(lists.get(list_name) or []):
            add(row, kind, {"file": "data/derived/validation_extras.json", "list": f"known_sites.sites.{list_name}", "row": position})
    listed = {e["name"] for e in entries} | {n for e in entries for n in e["other_names"]}
    for position, site in enumerate(((validation_doc or {}).get("named_sites") or {}).get("sites") or []):
        if site.get("name") not in listed:
            add(_named_row(site), "named site", {"file": "data/derived/validation.json", "list": "named_sites.sites", "row": position})

    lower = extras.get("lower_latitude_sites") or {}
    for position, site in enumerate(lower.get("sites") or []):
        entries.append({
            "name": site.get("name"), "other_names": [], "kind": "lower-latitude site", "kind_note": site.get("kind"),
            "lat": site.get("lat"), "lon": site.get("lon"), "hemisphere": "N" if (site.get("lat") or 0) > 0 else "S",
            "basis": "latitude",
            "basis_text": "Figures for its latitude alone, over a flat horizon: it lies outside our search.",
            "area": None, "area_in_page": False, "in_search": False, "ranked": False, "region": None,
            "snow_status": None, "snow_measured": None,
            "source": {"file": "data/derived/validation_extras.json", "list": "lower_latitude_sites.sites", "row": position},
            "targets": judge_latitude(site, targets),
        })
    cloud_source = "data/derived/cells_scored.json" if scored is not None else None
    return {
        "targets": [t["id"] for t in targets],
        "step_order": list(STEPS),
        "step_labels": STEP_LABELS,
        "step_labels_south": STEP_LABELS_SOUTH,
        "rule": "Our rule of thumb. A step removes a site when no hour is left after it. "
                "A site holds up when nothing removes it and its area is in the top third of ranked areas after terrain. "
                "Otherwise the step named is the one that takes the most hours.",
        "hours_what": "Hours a year inside two-hour spells after each step. In Antarctica the snow step is the rock season, because snow is not measured.",
        "cloud_from": cloud_source,
        "cloud_note": None if scored is not None else "The hours under typical cloud are unknown in this run.",
        "sites": entries,
    }


# ---- feature 2: what the numbers rest on ----

def _source_name(sources: dict | None, used_for_start: str) -> str | None:
    for record in (sources or {}).get("sources") or []:
        if str(record.get("used_for", "")).startswith(used_for_start):
            return re.sub(r"\s*\([^)]*\)\s*$", "", record.get("name") or "").strip() or None
    return None


def _most_common_pixel(horizon_doc: dict | None):
    if not isinstance(horizon_doc, dict):
        return None
    pixels = Counter(r.get("pixel_m") for r in horizon_doc.values() if isinstance(r, dict) and known(r.get("pixel_m")))
    return pixels.most_common(1)[0][0] if pixels else None


def basis(meta: dict, checks: dict | None, snow_many: dict | None, snow_maps: int | None, cloud_meta: dict | None,
          horizon_pixel, sources: dict | None, extras: dict | None) -> dict:
    """Feature 2: one line per step, the two check figures, the assumptions."""
    recount = (checks or {}).get("independent_recount") if isinstance(checks, dict) else None
    horizons = (checks or {}).get("jpl_horizons") if isinstance(checks, dict) else None
    all_hours = (horizons or {}).get("all_hours") or {}
    spells = (horizons or {}).get("hours_in_spells_of_2_h_or_more") or {}
    figures = {"recount_largest_difference_h_a_year": (recount or {}).get("largest_difference_h_a_year"),
               "horizons_median_abs_difference_pct": all_hours.get("median_abs_difference_pct")}
    step_minutes = ((extras or {}).get("meta") or {}).get("step_minutes")
    snow = meta.get("snow") or {}
    stations = ((snow_many or {}).get("overall") or {}).get("stations")
    cloud_name = None
    if cloud_meta and cloud_meta.get("source"):
        match = re.search(r"\(([^)]*)\)\s*$", cloud_meta["source"])
        cloud_name = match.group(1) if match else None
    cloud_years = meta.get("cloud_years")
    cloud_grid = (cloud_meta or {}).get("grid_deg")
    elevation = _source_name(sources, "Terrain horizon")
    spell_h = (meta.get("long_rule") or {}).get("spell_h")
    seasons = meta.get("seasons") or {}
    cell_km = (meta.get("scoring") or {}).get("cell_km")

    sun_line = [first_short(say("Sun only: our own Sun positions at {m}-minute steps over a flat horizon.", m=step_minutes),
                            "Sun only: our own Sun positions over a flat horizon.")]
    check_line = first_short(say("An independent recount differs by at most {r} hours a year; JPL Horizons by a median {p} percent.",
                                 r=small_number(figures["recount_largest_difference_h_a_year"]),
                                 p=None if figures["horizons_median_abs_difference_pct"] is None
                                 else f"{figures['horizons_median_abs_difference_pct']:.2f}"))
    if check_line:
        sun_line.append(check_line)
    snow_line = first_short(
        say("Snow-free ground: {n} IMS satellite snow maps ({maps}) from {period}, checked against {s} weather stations.",
            n=count(snow_maps), maps=snow.get("maps"), period=snow.get("period"), s=count(stations)),
        say("Snow-free ground: IMS satellite snow maps ({maps}) from {period}, checked against {s} weather stations.",
            maps=snow.get("maps"), period=snow.get("period"), s=count(stations)),
        say("Snow-free ground: IMS satellite snow maps ({maps}) from {period}.", maps=snow.get("maps"), period=snow.get("period")),
        "Snow-free ground: IMS satellite snow maps.")
    hills_line = first_short(
        say("After terrain: each area's horizon from {dem} elevation data, read on a {px} m grid.", dem=elevation, px=small_number(horizon_pixel)),
        say("After terrain: each area's horizon from {dem} elevation data.", dem=elevation),
        "After terrain: each area's horizon from elevation data.")
    cloud_line = first_short(
        say("Typical cloud: monthly mean cloud from NASA POWER ({name}), {years}, on a {grid}-degree grid of about {km} km.",
            name=cloud_name, years=cloud_years, grid=small_number(cloud_grid), km=meta.get("cloud_grid_km")),
        say("Typical cloud: monthly mean cloud from NASA POWER, {years}, on a {grid}-degree grid.",
            years=cloud_years, grid=small_number(cloud_grid)),
        "Typical cloud: monthly mean cloud from NASA POWER." if cloud_meta else None)
    steps = [
        {"step": 1, "name": "Sun only", "line": " ".join(s for s in sun_line if s),
         "rests_on": {"step_minutes": step_minutes, **figures}},
        {"step": 2, "name": "snow-free ground", "line": snow_line,
         "rests_on": {"maps": snow_maps, "maps_kind": snow.get("maps"), "period": snow.get("period"), "weather_stations": stations,
                      "station_mean_abs_difference": ((snow_many or {}).get("overall") or {}).get("mean_abs_difference")}},
        {"step": 3, "name": "after terrain", "line": hills_line,
         "rests_on": {"elevation_data": elevation, "horizon_grid_m": horizon_pixel}},
        {"step": 4, "name": "typical cloud", "line": cloud_line,
         "rests_on": {"cloud_source": (cloud_meta or {}).get("source"), "cloud_period": (cloud_meta or {}).get("period"),
                      "grid_deg": cloud_grid, "grid_km": meta.get("cloud_grid_km")}},
    ]
    short = {1: first_short(say("Sun: our own positions, checked against JPL Horizons.") if horizons else "Sun: our own positions."),
             2: first_short(say("Snow: IMS satellite maps, checked at {s} weather stations.", s=count(stations)), "Snow: IMS satellite maps."),
             3: first_short(say("Hills: {dem} elevation.", dem=elevation), "Hills: elevation data."),
             4: first_short(say("Cloud: NASA POWER monthly means.") if cloud_meta else None)}
    assumptions = [
        {"key": "area", "text": first_short(say("An area is a square about {km} km across; one figure stands for all of it.", km=cell_km),
                                            "An area is a square of ground; one figure stands for all of it.")},
        {"key": "cloud", "text": "Cloud is a monthly mean over all hours of day and night, not the chance of seeing a low Sun."
            if cloud_meta and "all hours of the day and night" in str(cloud_meta.get("what_it_is", "")) else
            "Cloud is a monthly mean, not the chance of seeing a low Sun."},
        {"key": "antarctic_snow", "text": first_short(
            say("Snow on Antarctic rock is not measured; there we count only the rock season, {rock}.", rock=seasons.get("rock_season_text")),
            "Snow on Antarctic rock is not measured; there we count only the rock season.")},
        {"key": "two_hours", "text": first_short(
            say("Counting only spells of at least {n} hours is our choice, not an agency rule.", n=NUMBER_WORDS.get(spell_h, small_number(spell_h))),
            "Counting only long spells is our choice, not an agency rule.")},
        {"key": "snow_odds", "text": first_short(
            say("Snow-free odds are typical for each ten-day period over {period}, not a forecast for one year.", period=snow.get("period")),
            "Snow-free odds are typical for each ten-day period, not a forecast for one year.")},
    ]
    lower_what = str(((extras or {}).get("lower_latitude_sites") or {}).get("what", ""))
    if "standard refraction" in lower_what:
        assumptions.append({"key": "refraction", "text": "Sun heights allow for the usual bending of light by the air (standard refraction)."})
    checks_block = {
        "independent_recount": None if recount is None else {
            "cells": recount.get("cells"), "comparisons": recount.get("comparisons"), "outside_tolerance": recount.get("outside_tolerance"),
            "largest_difference_h_a_year": recount.get("largest_difference_h_a_year"),
            "largest_difference_h_in_a_ten_day_bin": recount.get("largest_difference_h_in_a_ten_day_bin"),
            "ran_utc": recount.get("ran_utc")},
        "jpl_horizons": None if horizons is None else {
            "places": len(horizons.get("places") or []) or None,
            "rows": all_hours.get("rows"),
            "all_hours": {k: all_hours.get(k) for k in ("median_abs_difference_h", "largest_abs_difference_h",
                                                        "median_abs_difference_pct", "largest_abs_difference_pct")},
            "hours_in_spells_of_2_h_or_more": {k: spells.get(k) for k in ("median_abs_difference_h", "largest_abs_difference_h",
                                                                          "median_abs_difference_pct", "largest_abs_difference_pct")},
            "rows_flagged": len(horizons.get("rows_flagged") or []), "ran_utc": horizons.get("ran_utc")},
    }
    return {
        "steps": steps,
        "line": " ".join(s for s in (short[1], short[2], short[3], short[4]) if s),
        "check_figures": figures,
        "checks": checks_block,
        "checks_note": None if checks is not None else "data/derived/checks.json was not there: the two check figures are unknown.",
        "link": {"text": "How sure are we", "fragment": "go=sure"},
        "assumptions": [a for a in assumptions if a["text"]],
    }


# ---- feature 3: the search index ----

SEARCH_KINDS = ["named site", "known analog site", "lower-latitude site", "place", "airfield", "Earth region", "lunar region"]
SEARCH_OPENS = {"named site": "the place card of its area", "known analog site": "the place card of its area",
                "lower-latitude site": "the box of famous sites under the lists", "place": "the place card of its nearest area",
                "airfield": "the map, centred on the airfield", "Earth region": "the map, centred on the region",
                "lunar region": "the lunar region card"}


def _view(hemisphere: str | None) -> str:
    return "antarctic" if hemisphere == "S" else "arctic"


def _open_hours_by_area(scored: dict | None, targets: list[dict]) -> dict[str, float]:
    """The most low-Sun hours after terrain of any lunar region, per area (rock season in the south)."""
    out = {}
    for cell_id, record in (scored or {}).items():
        south = record.get("hemisphere") == "S"
        field = "long_summer_rock_open_hours" if south else "long_open_hours"
        values = [((record.get("targets") or {}).get(t["id"]) or {}).get(field) for t in targets]
        values = [v for v in values if known(v)]
        if values:
            out[cell_id] = max(values)
    return out


def search_index(famous_doc: dict, places_doc: dict | None, access: dict | None, scored: dict | None, areas: dict,
                 targets: list[dict]) -> tuple[dict, list[str]]:
    """Feature 3. Returns the index and what it lacks."""
    lacking = []
    entries, seen = [], set()
    kind_of = {k: i for i, k in enumerate(SEARCH_KINDS)}

    def add(kind: str, name: str, lat, lon, area: str | None, km, view: str, extra_key: str | None = None) -> None:
        if not name:
            return
        plain = ascii_name(name)
        key = plain.lower() + (f" {extra_key.lower()}" if extra_key else "")
        if (kind, key) in seen:
            return
        seen.add((kind, key))
        entries.append([kind_of[kind], name, None if plain == name else plain, key,
                        None if lat is None else round(lat, 3), None if lon is None else round(lon, 3), area, km, view])

    for site in famous_doc.get("sites") or []:
        if site["basis"] == "latitude":
            for name in [site["name"]] + site.get("other_names", []):
                add("lower-latitude site", name, site["lat"], site["lon"], None, None, "go=lists&tab=famous")
            continue
        area, km = (site["area"], None) if site["area"] else (None, None)
        if site["area"]:
            i = areas["index"][site["area"]]
            km = round(float(km_from(site["lat"], site["lon"], areas["_lat"][i:i + 1], areas["_lon"][i:i + 1])[0]), 1)
            view = f"view={_view(site['hemisphere'])}&place={site['area']}"
        else:
            area, km = nearest_area(site["lat"], site["lon"], areas)
            view = f"view={_view(site['hemisphere'])}&place={area}" if area else "go=lists&tab=famous"
        for name in [site["name"]] + site.get("other_names", []):
            add(site["kind"], name, site["lat"], site["lon"], area, km, view)

    if places_doc is None:
        lacking.append("site/data/places.json")
    for place in (places_doc or {}).get("places") or []:
        point = (place.get("points") or [{}])[0]
        area, km = nearest_area(point.get("lat"), point.get("lon"), areas)
        add("place", place.get("name"), point.get("lat"), point.get("lon"), area, km,
            f"view={_view('S' if (point.get('lat') or 0) < 0 else 'N')}&place={area}" if area else "go=lists")

    if access is None:
        lacking.append("data/derived/access_cells.json")
    elif scored is None:
        lacking.append("data/derived/cells_scored.json")
    else:
        best = _open_hours_by_area(scored, targets)
        cells = access.get("cells") or {}
        fields = {}
        for area_id in areas["ids"]:
            if best.get(area_id, -1) < SEARCH_MIN_HOURS:
                continue
            for key in ("nearest_scheduled", "nearest"):
                field = (cells.get(area_id) or {}).get(key)
                if field and known(field.get("km")) and field["km"] <= SEARCH_AIRFIELD_KM and field.get("ident"):
                    fields.setdefault(field["ident"], field)
        rows = np.arange(len(areas["ids"]))
        for ident, field in sorted(fields.items(), key=lambda kv: (kv[1].get("name") or "", kv[0])):
            area, km = nearest_area(field["lat"], field["lon"], areas, rows)
            add("airfield", field.get("name"), field.get("lat"), field.get("lon"), area, km,
                f"view={_view('S' if field['lat'] < 0 else 'N')}", extra_key=ident)

    if areas["region"] is not None:
        groups: dict[str, list[int]] = {}
        for i, name in enumerate(areas["region"]):
            if name:
                groups.setdefault(name, []).append(i)
        for name, rows in groups.items():
            lat_r, lon_r = np.radians(areas["_lat"][rows]), np.radians(areas["_lon"][rows])
            x, y, z = (np.cos(lat_r) * np.cos(lon_r)).mean(), (np.cos(lat_r) * np.sin(lon_r)).mean(), np.sin(lat_r).mean()
            lat, lon = math.degrees(math.atan2(z, math.hypot(x, y))), math.degrees(math.atan2(y, x))
            area, km = nearest_area(lat, lon, areas, rows)
            add("Earth region", name, lat, lon, area, km, f"view={_view(areas['hemisphere'][rows[0]])}")

    for t in targets:
        add("lunar region", t["name"], None, None, None, None, f"moon={t['id']}&target={t['id']}")
        if t["short"] != t["name"]:
            add("lunar region", t["short"], None, None, None, None, f"moon={t['id']}&target={t['id']}")

    doc = {
        "columns": ["kind", "name", "ascii", "key", "lat", "lon", "area", "km", "view"],
        "columns_what": {"kind": "index into kinds", "name": "the name as written", "ascii": "the name in plain ASCII, or null when the same",
                         "key": "lower-cased ASCII search key", "lat": "degrees", "lon": "degrees", "area": "id of the nearest area, or null",
                         "km": "km from the point to the centre of that area", "view": "the URL fragment to open, without the hash"},
        "kinds": SEARCH_KINDS,
        "opens": SEARCH_OPENS,
        "rules": {"airfields_near_areas_with_hours_after_terrain_at_least": SEARCH_MIN_HOURS,
                  "airfields_within_km": SEARCH_AIRFIELD_KM,
                  "airfields_what": "The nearest airfield and the nearest with scheduled flights of each such area, when within that distance.",
                  "centre_what": "For a map move, centre the map on lat and lon; the page works out its own zoom."},
        "lacking": lacking,
        "entries": entries,
    }
    return doc, lacking


# ---- feature 4: glossary ----

def glossary(meta: dict, targets: list[dict], elevation: str | None) -> dict:
    bins = meta.get("bins") or []
    spell_h = (meta.get("long_rule") or {}).get("spell_h")
    limits = [t["limit_deg"] for t in targets if known(t.get("limit_deg"))]
    low = min(targets, key=lambda t: t["limit_deg"]) if limits else None
    high = max(targets, key=lambda t: t["limit_deg"]) if limits else None
    last = bins[-1] if bins else {}
    last_days = (last.get("last_day") - last.get("first_day") + 1) if known(last.get("last_day")) and known(last.get("first_day")) else None
    seasons = meta.get("seasons") or {}
    snow = meta.get("snow") or {}
    names = ", ".join(t["name"] for t in targets)
    terms = [
        ("spell", first_short(
            say("An unbroken stretch of time with the Sun above the horizon and under a lunar region's ceiling. We count spells of {n} hours or more.",
                n=NUMBER_WORDS.get(spell_h, small_number(spell_h))),
            "An unbroken stretch of time with the Sun above the horizon and under a lunar region's ceiling.")),
        ("ten-day period", first_short(
            say("One of the {n} parts of our year, ten days each from {first}; the last runs {d} days to close the year.",
                n=len(bins) or None, first=(bins[0] or {}).get("label", "").split("-")[0] if bins else None,
                d=last_days if last_days != 10 else None),
            say("One of the {n} parts of our year, ten days each.", n=len(bins) or None),
            "A part of our year about ten days long.")),
        ("Sun ceiling", first_short(
            say("The highest the Sun climbs at a lunar region, in degrees above a level horizon: {lo} at {lo_name}, {hi} at {hi_name}.",
                lo=small_number(low["limit_deg"]) if low else None, lo_name=low["name"] if low else None,
                hi=small_number(high["limit_deg"]) if high else None, hi_name=high["name"] if high else None),
            "The highest the Sun climbs at a lunar region, in degrees above a level horizon.")),
        ("horizon", first_short(
            say("The line where land meets sky, seen from an area. Hills raise it and can hide a low Sun; ours comes from {dem} elevation data.",
                dem=elevation),
            "The line where land meets sky, seen from an area. Hills raise it and can hide a low Sun.")),
        ("snow-free odds", first_short(
            say("How often the satellite snow maps of {period} show the ground free of snow in a given ten-day period.",
                period=snow.get("period")),
            "How often the satellite snow maps show the ground free of snow in a given ten-day period.")),
        ("rock season", first_short(
            say("In Antarctica we count only {rock}, when the rock maps show the ground bare. Snow there is not measured.",
                rock=seasons.get("rock_season_text")),
            "The part of the Antarctic summer we count, when the rock maps show the ground bare.")),
        ("anorthosite", "A pale rock made mostly of plagioclase feldspar, like much of the Moon's bright highland crust. Our rock match looks for it."),
        ("area", first_short(
            say("A square of ground about {km} km across: the unit of our map and lists. One figure stands for all of it.",
                km=(meta.get("scoring") or {}).get("cell_km")),
            "A square of ground: the unit of our map and lists.")),
        ("lunar region", first_short(
            say("One of the {n} candidate landing regions near the Moon's south pole whose light we copy: {names}.",
                n=NUMBER_WORDS.get(len(targets), str(len(targets))), names=names),
            "A candidate landing region near the Moon's south pole whose light we copy.")),
    ]
    return {"terms": [{"term": term, "text": text} for term, text in terms if text]}


# ---- feature 5: the timed tour ----

def _split_seconds(weights: list[int], total: int, minimum: int) -> list[int]:
    """Whole seconds per step: each gets the minimum, the rest goes by the weights (largest remainder)."""
    n = len(weights)
    if n == 0:
        return []
    spare = max(0, total - minimum * n)
    raw = [spare * w / sum(weights) for w in weights]
    out = [minimum + int(r) for r in raw]
    for i in sorted(range(n), key=lambda i: raw[i] - int(raw[i]), reverse=True)[: total - sum(out)]:
        out[i] += 1
    return out


def tour(meta: dict, extras: dict, famous_doc: dict, targets: list[dict]) -> dict:
    """Feature 5: the guided views as a timed tour, captions filled from the data."""
    ids = [t["id"] for t in targets]
    default = "malapert" if "malapert" in ids else ids[0]
    dt = next(t for t in targets if t["id"] == default)
    hard = min((t for t in targets if known(t.get("limit_deg"))), key=lambda t: t["limit_deg"], default=None)
    counts = meta.get("counts") or {}
    last_step = 3 if known(counts.get("with_horizon_north")) and known(counts.get("north_cells")) and \
        counts["with_horizon_north"] >= 0.9 * counts["north_cells"] else 2
    funnel = ((extras.get("latitude_against_full_method") or {}).get("targets") or {}).get(default) or {}
    threshold = (extras.get("latitude_against_full_method") or {}).get("threshold_h")
    winter = (funnel.get("winter_half") or {}).get("all_measured_cells") or {}
    summer = (funnel.get("summer_half") or {}).get("all_measured_cells") or {}
    seasons = meta.get("seasons") or {}
    headline = (meta.get("headline") or {}).get(hard["id"]) if hard else None
    has_cloud = bool(meta.get("has_cloud"))
    after_cloud = summer.get("after_cloud") or {}

    sites = famous_doc.get("sites") or []
    haughton = next((s for s in sites if s["area"] and "Haughton" in s["name"]), None)
    lower = [s for s in sites if s["basis"] == "latitude"]
    lower_without = [s for s in lower if (s["targets"].get(default) or {}).get("has_a_2h_spell") is False]
    arctic_named = [s for s in sites if s["kind"] == "named site" and s["hemisphere"] == "N" and s["in_search"]]
    snow_most = [s for s in arctic_named if (s["targets"].get(default) or {}).get("costliest") == "snow"]

    def state(**kw):
        return {k: v for k, v in kw.items() if v is not None}

    candidates = [
        (state(view="arctic", target=default, step=1, period="winter"),
         say("Winter half, Sun only: {n} measured areas get at least {h} hours of two-hour spells under the {short} ceiling.",
             n=count((winter.get("sun_alone") or {}).get("cells")), h=hours(threshold), short=dt["short"])),
        (state(view="arctic", target=default, step=2, period="winter"),
         say("On snow-free ground only {n} of them keep {h} hours in the winter half.",
             n=count((winter.get("after_snow") or {}).get("cells")), h=hours(threshold))),
        (state(view="arctic", target=default, step=last_step, period="summer"),
         say("Summer half: {n} measured areas keep at least {h} hours after snow and hills.",
             n=count((summer.get("after_terrain") or {}).get("cells")), h=hours(threshold)) if last_step == 3 else
         say("Summer half: {n} measured areas keep at least {h} hours on snow-free ground.",
             n=count((summer.get("after_snow") or {}).get("cells")), h=hours(threshold))),
        (state(view="arctic", target=default, step=4, period="summer"),
         say("Typical cloud keeps a median {p} percent of those hours; {n} areas still have at least 50 hours.",
             p=percent(after_cloud.get("median_share_of_hours_kept")), n=count((after_cloud.get("still_at_least_h") or {}).get("50")))
         if has_cloud else None),
        (state(view="arctic", target=hard["id"] if hard else None, step=2, period="summer"),
         say("{name} has the lowest Sun ceiling, {deg} degrees; its two-hour spells start only at {lat} degrees north.",
             name=hard["name"], deg=small_number(hard["limit_deg"]), lat=small_number((headline or {}).get("first_latitude_with_spells")))
         if hard else None),
        (state(view="arctic", target=default, step=last_step, period="summer", place=haughton["area"]) if haughton else None,
         say("Devon Island, Haughton crater: its area keeps {h} hours a year of two-hour spells for {short} after snow and hills.",
             h=hours(((haughton["targets"].get(default) or {}).get("hours") or {}).get("hills")), short=dt["short"]) if haughton else None),
        (state(view="antarctic", target=default, step=min(3, max(2, last_step)), period="rock"),
         say("Antarctica: snow on rock is not measured, so only the rock season counts, {rock}. {n} areas there are ranked.",
             rock=seasons.get("rock_season_text"), n=count(counts.get("ranked_south")))),
        (state(view="arctic", target=default, step=last_step, period="year", tab="famous", go="lists"),
         say("All {n} lower-latitude analog sites lack a two-hour spell; for {short}, snow costs most at {k} of {m} Arctic named sites.",
             n=len(lower_without) if lower and len(lower_without) == len(lower) else None, short=dt["short"],
             k=len(snow_most) if arctic_named else None, m=len(arctic_named) or None)),
    ]
    steps = []
    for st, caption in candidates:
        caption = first_short(caption)
        if st is None or caption is None or word_count(caption) > MAX_WORDS:
            continue
        steps.append({"state": st, "caption": caption})
    steps = steps[:TOUR_MAX_STEPS]
    seconds = _split_seconds([word_count(s["caption"]) for s in steps], TOUR_SECONDS, TOUR_MIN_STEP_SECONDS)
    for step, s in zip(steps, seconds):
        step["seconds"] = s
        keys = ("view", "target", "step", "period", "place", "tab", "go", "moon")
        step["fragment"] = "&".join(f"{k}={step['state'][k]}" for k in keys if k in step["state"])
    total = sum(seconds)
    return {"label": f"Take the tour ({total} seconds)", "total_seconds": total, "steps": steps,
            "stops_on": ["key", "click", "touch"],
            "reduced_motion": "With reduced motion the tour waits for the reader to press next.",
            "seconds_what": "Each step gets five seconds, and the rest of the minute goes by the length of its caption."}


# ---- feature 12: access ----

AIRFIELD_KEYS = ("name", "ident", "country", "type", "lat", "lon", "municipality")


def access_table(doc: dict, areas: dict) -> tuple[np.ndarray, list[dict]]:
    """uint16 [areas, 4]: index and km of the nearest scheduled airfield, index and km of the nearest airfield."""
    cells = doc.get("cells")
    if not isinstance(cells, dict):
        raise ToolsError("access_cells.json has no record of cells")
    missing = [a for a in areas["ids"] if a not in cells]
    if missing:
        raise ToolsError(f"access_cells.json lacks {len(missing)} of the page's areas, the first {missing[0]}")
    table = np.full((len(areas["ids"]), 4), UNKNOWN_U16, dtype=np.uint16)
    fields: list[dict] = []
    position: dict[str, int] = {}
    for row, area_id in enumerate(areas["ids"]):
        record = cells[area_id] or {}
        for column, key in ((0, "nearest_scheduled"), (2, "nearest")):
            field = record.get(key)
            if not field or not known(field.get("km")):
                continue
            ident = field.get("ident") or f"{field.get('name')}|{field.get('lat')}|{field.get('lon')}"
            if ident not in position:
                position[ident] = len(fields)
                fields.append({**{k: field.get(k) for k in AIRFIELD_KEYS}, "scheduled": bool(field.get("scheduled_service"))})
            km = whole(field["km"])
            if not 0 <= km < UNKNOWN_U16 or position[ident] >= UNKNOWN_U16:
                raise ToolsError(f"access_cells.json: {area_id} {key} does not fit a uint16")
            table[row, column] = position[ident]
            table[row, column + 1] = km
    return table, fields


def airfields_doc(doc: dict, fields: list[dict]) -> dict:
    meta = doc.get("meta") or {}
    source = meta.get("source") or {}
    return {
        "airfields": fields,
        "what_it_is_not": "A straight-line distance from the centre of the area to a runway. It is not a road, a port, a permit or a cost.",
        "scheduled_what": "Scheduled flights is the airport table's own yes or no. We did not check it against any timetable.",
        "source": {"name": source.get("name"), "licence": source.get("licence"), "fetched_utc": source.get("fetched_utc")},
        "written_inside": meta.get("written"),
    }


# ---- feature 12: the winter list of small bare patches ----

LEAD_KEYS = ("id", "lat", "lon", "region", "bare_km2", "winter_hours_flat", "winter_hours_snow_free", "winter_hours_after_terrain",
             "best_ten_day_periods")


def winter_cautions(meta: dict) -> list[str]:
    warnings = " ".join(meta.get("warnings") or [])
    not_computed = " ".join(meta.get("not_computed") or [])
    horizon = meta.get("horizon") or {}
    land = (meta.get("screen_relaxed") or {}).get("min_land_share_of_the_land_cover_file")
    far_north = re.search(r"North of about (\d+(?:\.\d+)?) N", warnings)
    out = [
        say("Winter here means {w}.", w=meta.get("winter_half")),
        say("Only areas with at least {f} square km of bare ground are listed.", f=small_number(meta.get("floor_bare_km2"))),
        "Cloud is not counted: these are hours of low Sun on ground likely free of snow, not hours of visible Sun."
        if "cloud" in not_computed else None,
        "Near a coast the snow odds rest on few land pixels of the snow maps; each lead says how many."
        if "land pixels" in warnings else None,
        "Bare ground at a coast can be beach, tidal flat, rock or a quarry. We did not look which."
        if "what the bare ground is" in not_computed else None,
        "The bare area of a lead with few land-cover samples is uncertain by about its own size."
        if "uncertain by about its own size" in warnings else None,
        say("Areas with under {p} percent land are missing, so small islands and skerries are not here.",
            p=percent(land)) if "skerries" in warnings else None,
        say("Hours after terrain exist only for the {n} areas given a terrain horizon.", n=count(horizon.get("with_a_horizon"))),
        "Hours after terrain average over all the land of an area, not over its bare ground."
        if "average over all the land" in warnings else None,
        say("North of about {lat} N the winter hours fall in October and March, not in midwinter.",
            lat=far_north.group(1) if far_north else None),
        "Region names come from rough boxes of latitude and longitude; an area near a border can carry its neighbour's name."
        if "first match wins" in warnings else None,
    ]
    return [c for c in out if c and short_enough(c)]


def winter_leads(doc: dict, targets: list[dict]) -> dict:
    meta = doc.get("meta") or {}
    src_targets = doc.get("targets") or {}
    out = []
    for t in targets:
        src = src_targets.get(t["id"])
        if src is None:
            raise ToolsError(f"winter_leads.json has no lunar region {t['id']}")
        leads = []
        for lead in src.get("leads") or []:
            snow = lead.get("snow") or {}
            if not lead.get("at_main_floor") or snow.get("status") != "measured":
                continue
            leads.append({**{k: lead.get(k) for k in LEAD_KEYS},
                          "snow_land_pixels": snow.get("land_pixels"), "snow_block_pixels": snow.get("block_pixels")})
        leads.sort(key=lambda l: (-(l["winter_hours_after_terrain"] if known(l["winter_hours_after_terrain"]) else -1),
                                  -(l["winter_hours_snow_free"] if known(l["winter_hours_snow_free"]) else -1)))
        out.append({"id": t["id"], "name": t["name"], "leads": leads,
                    "counts_by_region": src.get("counts_by_region"),
                    "counts_by_region_after_terrain": src.get("counts_by_region_after_terrain")})
    return {
        "winter_half": meta.get("winter_half"),
        "floor_bare_km2": meta.get("floor_bare_km2"),
        "count_thresholds_h": meta.get("count_thresholds_h"),
        "list_min_winter_hours": meta.get("list_min_winter_hours"),
        "what": "Areas the bare-ground screen leaves out that still hold some bare ground, with measured snow. They are in no ranking.",
        "order": "Most winter hours after terrain first; areas without a terrain figure last.",
        "counts_what": "Areas with at least that many winter hours, by region, before and after terrain.",
        "targets": out,
        "cautions": winter_cautions(meta),
        "written_inside": meta.get("written"),
    }


# ---- the whole run ----

LAYOUTS = {
    "famous.json": {"layout": {"sites": "[{name, other_names, kind, lat, lon, hemisphere, basis (area or latitude), basis_text, area (id or null), "
                                        "in_search, ranked, region, snow_status, snow_measured, source, targets{id: ...}}]",
                               "targets (basis area)": "{hours {sun, snow, hills, cloud}, step, costliest, costliest_loss_h, "
                                                       "percentile_among_ranked, rank_from_top, ranked_cells, verdict, sentence}",
                               "targets (basis latitude)": "{step, hours_a_year_in_band, longest_spell_minutes, longest_spell_h, "
                                                           "hours_in_spells_of_2h, has_a_2h_spell, sentence}",
                               "step": "sun, snow, hills, cloud, holds-up or null; labels in step_labels and step_labels_south"},
                    "feeds": "feature 1, the box of famous sites under the short lists"},
    "basis.json": {"layout": {"steps": "[{step 1 to 4, name, line, rests_on}]", "line": "the one line under the calendar and the map",
                              "check_figures": "the two check figures, null without checks.json", "checks": "more figures of the two checks",
                              "link": "the link to the checks section", "assumptions": "[{key, text}] for the fold-out"},
                   "feeds": "feature 2, what the numbers rest on"},
    "search.json": {"layout": {"entries": "rows in the order of columns", "kinds": "the kind names", "opens": "what each kind opens",
                               "rules": "the two thresholds for airfields"},
                    "feeds": "feature 3, the place-name search box"},
    "glossary.json": {"layout": {"terms": "[{term, text}]"}, "feeds": "feature 4, the glossary"},
    "tour.json": {"layout": {"steps": "[{state, caption, seconds, fragment}]", "label": "the button text",
                             "total_seconds": "the sum of the steps", "reduced_motion": "what to do with reduced motion"},
                  "feeds": "feature 5, the timed tour"},
    "airfields.json": {"layout": {"airfields": "[{name, ident, country, type, lat, lon, municipality, scheduled}]",
                                  "what_it_is_not": "print beside any distance", "source": "the airport table and its licence"},
                       "feeds": "feature 12, the airfield names behind access.bin"},
    "winter_leads.json": {"layout": {"targets": "[{id, name, leads[], counts_by_region, counts_by_region_after_terrain}]",
                                     "leads": "{id, lat, lon, region, bare_km2, winter_hours_flat, winter_hours_snow_free, "
                                              "winter_hours_after_terrain, best_ten_day_periods, snow_land_pixels, snow_block_pixels}",
                                     "cautions": "short sentences to print with the list"},
                          "feeds": "feature 12, the winter list for small bare patches"},
    "access.bin": {"feeds": "feature 12, the nearest airfield in every list row and on the place card; the reachable-only switch"},
}

NEEDS = {
    "famous.json": ["data/derived/validation_extras.json", "data/derived/validation.json", "data/derived/cells_scored.json",
                    "site/data/cells.json", "site/data/meta.json"],
    "basis.json": ["site/data/meta.json", "data/derived/checks.json", "data/derived/snow_validation_many.json",
                   "data/derived/snow_free_dekads.npz", "data/derived/cloud_cells.json", "data/derived/horizon_cells.json",
                   "site/data/sources.json", "data/derived/validation_extras.json"],
    "search.json": ["data/derived/validation_extras.json", "data/derived/validation.json", "site/data/places.json",
                    "data/derived/access_cells.json", "data/derived/cells_scored.json", "site/data/cells.json", "site/data/meta.json"],
    "glossary.json": ["site/data/meta.json", "site/data/sources.json"],
    "tour.json": ["site/data/meta.json", "data/derived/validation_extras.json", "data/derived/validation.json"],
    "access.bin": ["data/derived/access_cells.json", "site/data/cells.json"],
    "airfields.json": ["data/derived/access_cells.json"],
    "winter_leads.json": ["data/derived/winter_leads.json", "site/data/meta.json"],
}

# inputs that only add detail: the file is written without them, and the run says what it then lacks
DETAIL_INPUTS = (
    ("famous.json", "data/derived/validation.json", "named sites that validation_extras.json lacks"),
    ("famous.json", "data/derived/cells_scored.json", "the hours under typical cloud: they are null"),
    ("basis.json", "data/derived/checks.json", "the two check figures: they are null"),
    ("basis.json", "data/derived/snow_validation_many.json", "the number of weather stations"),
    ("basis.json", "data/derived/snow_free_dekads.npz", "the number of snow maps"),
    ("basis.json", "data/derived/cloud_cells.json", "the cloud source and its grid"),
    ("basis.json", "data/derived/horizon_cells.json", "the grid of the terrain horizon"),
    ("basis.json", "site/data/sources.json", "the name of the elevation data"),
    ("search.json", "data/derived/access_cells.json", "the airfields"),
    ("search.json", "data/derived/cells_scored.json", "the airfields, which need the hours after terrain"),
    ("search.json", "site/data/places.json", "the top places"),
    ("glossary.json", "site/data/sources.json", "the name of the elevation data"),
    ("tour.json", "data/derived/validation.json", "nothing: the named sites come from validation_extras.json"),
)

AREA_FILES = ("access.bin",)


def export(derived: Path, site_data: Path, out: Path | None = None) -> dict:
    """Build every file and write those whose inputs are there; return what was written, left out and failed."""
    derived, site_data = Path(derived), Path(site_data)
    out = Path(out) if out is not None else site_data
    cells_path = site_data / "cells.json"
    if not cells_path.exists():
        raise FileNotFoundError(f"{cells_path} is not there: run scripts/export_site.py first, it decides the order of the areas")
    areas = areas_of(read_json(cells_path))
    areas["_lat"], areas["_lon"] = np.asarray(areas["lat"]), np.asarray(areas["lon"])
    n = len(areas["ids"])
    ids_hash = hashlib.sha256("\n".join(areas["ids"]).encode()).hexdigest()
    meta_path = site_data / "meta.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"{meta_path} is not there: run scripts/export_site.py first, it names the lunar regions")
    meta = read_json(meta_path)
    targets = targets_of(meta)
    try:
        previous = read_json(out / "tools.json") if (out / "tools.json").exists() else None
    except ValueError:
        previous = None
    made_for = ((previous or {}).get("areas") or {}).get("ids_sha256") if isinstance(previous, dict) else None

    inputs = {
        "data/derived/validation_extras.json": derived / "validation_extras.json",
        "data/derived/validation.json": derived / "validation.json",
        "data/derived/cells_scored.json": derived / "cells_scored.json",
        "data/derived/checks.json": derived / "checks.json",
        "data/derived/access_cells.json": derived / "access_cells.json",
        "data/derived/winter_leads.json": derived / "winter_leads.json",
        "data/derived/snow_validation_many.json": derived / "snow_validation_many.json",
        "data/derived/snow_free_dekads.npz": derived / "snow_free_dekads.npz",
        "data/derived/cloud_cells.json": derived / "cloud_cells.json",
        "data/derived/horizon_cells.json": derived / "horizon_cells.json",
        "site/data/cells.json": cells_path,
        "site/data/meta.json": meta_path,
        "site/data/places.json": site_data / "places.json",
        "site/data/sources.json": site_data / "sources.json",
    }
    docs: dict = {}
    for label, path in inputs.items():
        if not path.exists():
            docs[label] = None
        elif label in ("site/data/cells.json", "site/data/meta.json"):
            docs[label] = True
        elif path.suffix == ".npz":
            with np.load(path, allow_pickle=False) as archive:
                docs[label] = {"files": int(archive["files"])} if "files" in archive.files else {}
        else:
            docs[label] = read_json(path)
    sources_written = {}
    for label, path in inputs.items():
        if docs[label] is None:
            sources_written[label] = None
            continue
        inside = None
        doc = docs[label]
        if isinstance(doc, dict) and isinstance(doc.get("meta"), dict):
            inside = doc["meta"].get("written_utc") or doc["meta"].get("written")
        if label == "site/data/meta.json":
            inside = meta.get("generated")
        sources_written[label] = {"modified": modified(path), "written_inside": inside, "bytes": path.stat().st_size}

    scored = None
    if docs["data/derived/cells_scored.json"] is not None:
        scored = {c["id"]: c for c in docs["data/derived/cells_scored.json"].get("cells") or [] if isinstance(c, dict) and "id" in c}
    seasons = meta.get("seasons") or {}
    elevation = _source_name(docs["site/data/sources.json"], "Terrain horizon")

    built: dict[str, bytes] = {}
    layouts: dict[str, dict] = {}
    left_out: dict[str, str] = {}
    failed: dict[str, str] = {}
    lacking_extra: list[dict] = []
    state: dict = {}

    def attempt(names: list[str], needs: list[str], build) -> None:
        missing = [label for label in needs if docs[label] is None]
        if missing:
            for name in names:
                left_out[name] = f"{missing[0]} is not there"
            return
        try:
            build()
        except (ToolsError, KeyError, TypeError, ValueError, IndexError, AttributeError) as error:
            for name in names:
                built.pop(name, None)
                failed[name] = f"{type(error).__name__}: {error}"

    def build_famous():
        doc = famous(docs["data/derived/validation_extras.json"], docs["data/derived/validation.json"], scored, areas, targets,
                     seasons.get("rock_season_text"), (meta.get("scoring") or {}).get("cell_km"))
        state["famous"] = doc
        built["famous.json"] = checked_json({"generated": utc_now(), **doc})

    def build_basis():
        doc = basis(meta, docs["data/derived/checks.json"], docs["data/derived/snow_validation_many.json"],
                    (docs["data/derived/snow_free_dekads.npz"] or {}).get("files"),
                    (docs["data/derived/cloud_cells.json"] or {}).get("meta"),
                    _most_common_pixel(docs["data/derived/horizon_cells.json"]), docs["site/data/sources.json"],
                    docs["data/derived/validation_extras.json"])
        built["basis.json"] = checked_json({"generated": utc_now(), **doc})

    def build_search():
        doc, lacking = search_index(state["famous"], docs["site/data/places.json"], docs["data/derived/access_cells.json"], scored,
                                    areas, targets)
        data = checked_json({"generated": utc_now(), **doc})
        if len(data) >= SEARCH_MAX_BYTES:
            raise ToolsError(f"search.json would be {len(data):,} bytes, over {SEARCH_MAX_BYTES:,}")
        built["search.json"] = data

    def build_glossary():
        built["glossary.json"] = checked_json({"generated": utc_now(), **glossary(meta, targets, elevation)})

    def build_tour():
        built["tour.json"] = checked_json({"generated": utc_now(), **tour(meta, docs["data/derived/validation_extras.json"],
                                                                          state["famous"], targets)})

    def build_access():
        doc = docs["data/derived/access_cells.json"]
        table, fields = access_table(doc, areas)
        built["access.bin"] = table.astype("<u2").tobytes()
        built["airfields.json"] = checked_json({"generated": utc_now(), **airfields_doc(doc, fields)})
        layouts["access.bin"] = {"type": "uint16, little-endian", "shape": [n, 4],
                                 "order": "area (the order of ids in cells.json), then the four columns",
                                 "columns": ["scheduled_index", "scheduled_km", "any_index", "any_km"],
                                 "columns_what": "index into airfields.json airfields and whole km, for the nearest airfield with "
                                                 "scheduled flights and the nearest airfield of any kind",
                                 "unknown": UNKNOWN_U16}

    def build_winter():
        built["winter_leads.json"] = checked_json({"generated": utc_now(), **winter_leads(docs["data/derived/winter_leads.json"], targets)})

    attempt(["famous.json"], ["data/derived/validation_extras.json"], build_famous)
    attempt(["basis.json"], ["site/data/meta.json"], build_basis)
    if "famous" in state:
        attempt(["search.json"], ["data/derived/validation_extras.json"], build_search)
        attempt(["tour.json"], ["data/derived/validation_extras.json"], build_tour)
    else:
        for name in ("search.json", "tour.json"):
            (failed if "famous.json" in failed else left_out)[name] = "famous.json was not built"
    attempt(["glossary.json"], ["site/data/meta.json"], build_glossary)
    attempt(["access.bin", "airfields.json"], ["data/derived/access_cells.json"], build_access)
    attempt(["winter_leads.json"], ["data/derived/winter_leads.json"], build_winter)

    out.mkdir(parents=True, exist_ok=True)
    written = {name: write_bytes(out / name, data) for name, data in built.items()}
    removed = {}
    for name in dict.fromkeys(list(left_out) + list(failed)):
        if name in AREA_FILES and (out / name).exists() and made_for != ids_hash:
            (out / name).unlink()
            removed[name] = "it was made for another list of areas than the page has now, or no index says which"
    without = [{"file": name, "input": label, "lacks": lacks} for name, label, lacks in DETAIL_INPUTS
               if name in written and docs[label] is None]
    files = {}
    for name, size in written.items():
        files[name] = {"bytes": size, "from": [label for label in NEEDS[name] if docs[label] is not None],
                       "layout": layouts.get(name) or LAYOUTS[name]["layout"], "feeds": LAYOUTS[name]["feeds"]}
    index = {
        "generated": utc_now(),
        "script": "scripts/export_site_tools.py",
        "how_to_rerun": "uv run python scripts/export_site.py, then uv run python scripts/export_site_tools.py",
        "unknown": "null in the JSON files, 65535 in access.bin; never 0",
        "areas": {"count": n, "order": "the ids of site/data/cells.json, as it was when this ran", "ids_sha256": ids_hash,
                  "ids_sha256_what": "SHA-256 of the ids joined by a line feed, in order",
                  "what": "access.bin follows this order. The JSON files name areas by id."},
        "targets": [t["id"] for t in targets],
        "files": files,
        "files_what": "The files this run made. Read a file only when it is listed here.",
        "left_out": [{"file": name, "because": reason, "older_copy_kept": (out / name).exists()} for name, reason in left_out.items()],
        "failed": [{"file": name, "because": reason, "older_copy_kept": (out / name).exists()} for name, reason in failed.items()],
        "written_without": without,
        "older_copies_removed": [{"file": name, "because": reason} for name, reason in removed.items()],
        "sources_written": sources_written,
    }
    written["tools.json"] = write_bytes(out / "tools.json", checked_json(index))
    for name, reason in left_out.items():
        print(f"left out: {name} ({reason}{'; an older copy stays in place' if (out / name).exists() else ''})")
    for name, reason in removed.items():
        print(f"removed an older copy: {name} ({reason})")
    for entry in without:
        print(f"written without {entry['input']}: {entry['file']} lacks {entry['lacks']}")
    return {"written": written, "left_out": left_out, "failed": failed, "without": without, "removed": removed,
            "out": str(out), "areas": n}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--derived", type=Path, default=ROOT / "data" / "derived")
    parser.add_argument("--site-data", type=Path, default=ROOT / "site" / "data",
                        help="the folder with the page's cells.json and meta.json")
    parser.add_argument("--out", type=Path, default=None, help="where to write (default: the site-data folder)")
    args = parser.parse_args()
    report = export(args.derived, args.site_data, args.out)
    print(f"{report['areas']} areas; wrote into {report['out']}:")
    for name, size in report["written"].items():
        print(f"  {name:20s} {size:>9,d} bytes")
    if report["failed"]:
        for name, reason in report["failed"].items():
            print(f"FAILED: {name} was not written: {reason}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()

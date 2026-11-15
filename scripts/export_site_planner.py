# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Write the planner files of the map page (round 3, features 7 to 11) into site/data.

    uv run python scripts/export_site.py            # first: it decides the order of the areas
    uv run python scripts/export_site_planner.py    # then this (about five minutes: the Sun table by compass sector)

numpy, the standard library and the project's own modules for the hours (twinfinder.grazing, sun, score).
Nothing under data/ is written. Every per-area file follows the order of the ids in site/data/cells.json;
an area that an input lacks stops the run with an error, so no row can land on the wrong area.

Writes, into site/data:
    rehearsal_rules.json  the four rehearsal activities: inputs, pass and near rules, suggestions and their tags
    rehearsal.bin         per area and lunar region: H30, the first period of its stretch, four verdict codes
    yearplan.json         per lunar region and month: the best ranked area north and south, and the best reachable one
    rose.bin              per area and lunar region: the share of the low-Sun hours from each of 36 compass sectors
    skyline.bin           per area and compass sector: the lowest elevation bin that half the area's ground sees
                          (on the nine old bins of the stored horizons, not on the bins of the Sun tables)
    planner.json          an index of the files above: byte layouts, codes, source files and when they were written

An input that is not there leaves out the files that need it, and planner.json says which and why.
Unknown is null in the JSON files, 255 in the uint8 bytes and 65535 in the uint16 block; it is never 0.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from twinfinder import grazing, horizon, score, sun  # noqa: E402

SURVEY = ROOT / "reports" / "Other teams and prior projects survey.md"
SURVEY_SECTION = "2b"
LABEL = "our rule of thumb, not an agency standard"
STRETCH_PERIODS = 3          # H30: three ten-day periods in a row
REACH_KM = 100.0             # the year plan's "reachable": this close to an airfield (round 3 plan, feature 10)
MIN_MONTH_HOURS = 5.0        # a month in which no ranked area has more than this has no entry
SKYLINE_OPEN_SHARE = 0.5     # an elevation bin is open in a sector when at least this share of the ground sees over the skyline
ROSE_TOP = 200               # the largest sector of a rose is written as this
ROSE_GIVEN, ROSE_NO_HOURS = 0, 1
UNKNOWN8, UNKNOWN16 = 255, 65535
BATCH = 256                  # areas joined with their horizon at a time
INF = math.inf
VERDICT_CODES = {"pass": 3, "near": 2, "does not pass": 1, "cannot tell": 255}   # 0 is never written
VERDICT_MEANS = {
    "pass": "The area meets every part of the pass rule.",
    "near": "The area misses the pass rule but meets every part of the near rule.",
    "does not pass": "The known inputs miss both rules, whatever any unknown input might be.",
    "cannot tell": "An input that could change the verdict is unknown.",
}
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]
AREA_FILES = ("rehearsal.bin", "yearplan.json", "rose.bin", "skyline.bin")

# ---- the one table of rules (round 3 plan, feature 8) ----

INPUTS = {
    "H30": {"symbol": "H30", "name": "low-Sun hours after snow and terrain in the best three ten-day periods in a row",
            "unit": "h", "low": 0.0, "high": INF, "digits": 1},
    "S": {"symbol": "S", "name": "mean snow-free odds over those three periods", "unit": "share from 0 to 1",
          "low": 0.0, "high": 1.0, "digits": 2},
    "C": {"symbol": "C", "name": "clear share of the sky in the months of those periods", "unit": "share from 0 to 1",
          "low": 0.0, "high": 1.0, "digits": 2},
    "K": {"symbol": "K", "name": "share of the snow-free low-Sun hours in those periods that the terrain leaves",
          "unit": "share from 0 to 1", "low": 0.0, "high": 1.0, "digits": 2},
    "P90": {"symbol": "P90", "name": "slope that 90 percent of the ground is below", "unit": "degrees",
            "low": 0.0, "high": 90.0, "digits": 1},
    "B": {"symbol": "B", "name": "bare share of the area", "unit": "share from 0 to 1", "low": 0.0, "high": 1.0, "digits": 2},
    "T": {"symbol": "T", "name": "mean air temperature in the months of those periods", "unit": "°C",
          "low": -INF, "high": INF, "digits": 1},
    "D": {"symbol": "D", "name": "distance to the nearest airfield with scheduled flights; in Antarctica, to any listed airfield",
          "unit": "km", "low": 0.0, "high": INF, "digits": 1},
    "H30xC": {"symbol": "H30 × C", "name": "H30 times C: low-Sun hours under a typically clear sky", "unit": "h",
              "low": 0.0, "high": INF, "digits": 1},
}

SOURCES = {   # each link is checked against section 2b of the survey when the rules file is written
    "drats": {"name": "NASA D-RATS 2022 test report (the 2022 lamp test)",
              "link": "https://ntrs.nasa.gov/api/citations/20230017073/downloads/D-RATS%202022%20Test%20Report%20Final.pdf"},
    "jett5": {"name": "USGS page on the JETT5 Artemis III mission tests",
              "link": "https://www.usgs.gov/centers/astrogeology-science-center/news/artemis-iii-mission-tests-san-francisco-volcanic-field"},
    "jsc": {"name": "Johnson Space Center lighting study (Litaker and others, 2024)",
            "link": "https://ntrs.nasa.gov/api/citations/20240011393/downloads/Lighiting%20Study%20IEEE%20Paper%20FINAL-1.pdf"},
}

ACTIVITIES = [
    {"id": "rover", "activity": "Rover driving in long shadows",
     "pass": [("H30", ">=", 40), ("B", ">=", 0.25), ("P90", "<=", 15), ("S", ">=", 0.8)],
     "near": [("H30", ">=", 20), ("B", ">=", 0.15), ("P90", "<=", 20), ("S", ">=", 0.5)],
     "suggestions": [
         {"text": "Drive one route up-sun, across the Sun and down-sun, and compare what the driver can see.",
          "tag": "done by NASA", "source": "jsc",
          "done_how": "NASA did this in a virtual scene with the Sun 1.2 degrees high, not on real ground."},
         {"text": "Drive through the long shadows of boulders and ridges at the Sun heights of the lunar region.",
          "tag": "our suggestion"}]},
    {"id": "camera", "activity": "Camera and navigation tests",
     "pass": [("H30xC", ">=", 10), ("K", ">=", 0.6)],
     "near": [("H30xC", ">=", 5)],
     "suggestions": [
         {"text": "Photograph the same rocks at several Sun heights inside the band, to test cameras and navigation software.",
          "tag": "our suggestion"}]},
    {"id": "crew", "activity": "Crew work on foot",
     "pass": [("H30", ">=", 40), ("D", "<=", 100), ("T", ">=", -10), ("S", ">=", 0.8)],
     "near": [("H30", ">=", 20), ("D", "<=", 200), ("T", ">=", -20)],
     "suggestions": [
         {"text": "Walk a geology traverse in low, raking light.", "tag": "done by NASA", "source": "jett5",
          "done_how": "In JETT5 the low light came from a spotlight at night; here it would be the real Sun."},
         {"text": "Set up and read instruments with the Sun low behind, beside and ahead of the crew.",
          "tag": "our suggestion"}]},
    {"id": "lamp", "activity": "Checking a lamp simulator against the real Sun",
     "pass": [("H30xC", ">=", 5), ("D", "<=", 100)],
     "near": [("H30", ">=", 10)],
     "suggestions": [
         {"text": "Light a patch of ground at night with one portable lamp, to copy the light of the south pole.",
          "tag": "done by NASA", "source": "drats", "done_how": "D-RATS 2022 did this with one portable lamp at night."},
         {"text": "Photograph the same patch under the lamp and under the real low Sun at the same height, and compare the shadows.",
          "tag": "our suggestion"}]},
]

LEFT_OUT_SOURCES = [
    {"name": "the 2001 Hyperion rover test",
     "why": "It is not in section 2b of our survey, so it is not cited. Our own notes say it was not a low-Sun test."},
]


class PlannerError(Exception):
    """An input does not say what the planner files need."""


# ---- small helpers ----

def read_json(path: Path, default=None):
    path = Path(path)
    if not path.exists():
        return default
    with open(path) as handle:
        return json.load(handle)


def json_bytes(value) -> bytes:
    return json.dumps(value, separators=(",", ":"), allow_nan=False, ensure_ascii=False).encode()


def write_bytes(path: Path, data: bytes) -> int:
    """Write beside the target and rename, so a reader never sees half a file."""
    side = path.with_name(path.name + ".part")
    side.write_bytes(data)
    os.replace(side, path)
    return len(data)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def modified(path: Path) -> str:
    return datetime.fromtimestamp(Path(path).stat().st_mtime, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def finite(value) -> bool:
    return value is not None and not (isinstance(value, float) and math.isnan(value))


def rounded(value, digits: int):
    """A number for a file or a rule: rounded as printed, or None when unknown."""
    if value is None:
        return None
    value = float(value)
    return round(value, digits) if math.isfinite(value) else None


def ids_sha256(ids: list[str]) -> str:
    return hashlib.sha256("\n".join(ids).encode()).hexdigest()


# ---- the rules ----

def _range(key: str, values: dict) -> tuple[float, float]:
    """What is known of one input: (low, high). A known value v is (v, v); an unknown one spans its whole range."""
    if key == "H30xC":
        (h_lo, h_hi), (c_lo, c_hi) = _range("H30", values), _range("C", values)
        if h_lo == h_hi and c_lo == c_hi:
            product = round(h_lo * c_lo, INPUTS["H30xC"]["digits"])
            return product, product

        def times(a, b):
            return 0.0 if a == 0.0 or b == 0.0 else a * b
        return times(h_lo, c_lo), times(h_hi, c_hi)
    value = values.get(key)
    if isinstance(value, tuple):
        return float(value[0]), float(value[1])
    if not finite(value):
        return INPUTS[key]["low"], INPUTS[key]["high"]
    return float(value), float(value)


def _holds(condition, values: dict):
    """True, False, or None when an unknown input leaves it open."""
    key, op, threshold = condition
    low, high = _range(key, values)
    if op == ">=":
        return True if low >= threshold else (False if high < threshold else None)
    if op == "<=":
        return True if high <= threshold else (False if low > threshold else None)
    raise ValueError(f"unknown comparison {op!r}")


def _all(results) -> bool | None:
    results = list(results)
    if any(r is False for r in results):
        return False
    return True if all(r is True for r in results) else None


def evaluate(activity: dict, values: dict) -> str:
    """'pass', 'near', 'does not pass' or 'cannot tell' for one area.

    values maps an input to a number, to None when unknown, or to (low, high) when only a range is known.
    An unknown input is never counted as a fail: the verdict is 'cannot tell' whenever it could change it.
    """
    passed = _all(_holds(c, values) for c in activity["pass"])
    if passed is True:
        return "pass"
    if passed is None:
        return "cannot tell"
    near = _all(_holds(c, values) for c in activity["near"])
    return {True: "near", False: "does not pass", None: "cannot tell"}[near]


def _value_words(key: str, value) -> str:
    unit = INPUTS[key]["unit"]
    number = f"{value:g}".replace("-", "−") if isinstance(value, (int, float)) else str(value)
    return number if unit.startswith("share") else f"{number} {unit}"


def rule_words(word: str, conditions) -> str:
    """'Pass when H30 is at least 40 h, B at least 0.25, P90 at most 15 degrees and S at least 0.8.'"""
    ops = {">=": "at least", "<=": "at most"}
    parts = [f"{INPUTS[k]['symbol']}{' is' if n == 0 else ''} {ops[op]} {_value_words(k, v)}"
             for n, (k, op, v) in enumerate(conditions)]
    joined = parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]
    return f"{word} when {joined}."


def _input_keys(activity: dict) -> list[str]:
    keys = []
    for key, _, _ in activity["pass"] + activity["near"]:
        for one in (["H30", "C", "H30xC"] if key == "H30xC" else [key]):
            if one not in keys:
                keys.append(one)
    return keys


def section_links(text: str, section: str) -> set[str]:
    """Every link in one numbered section of a Markdown report ('### 2b.' up to the next heading)."""
    out, inside = set(), False
    for line in text.splitlines():
        if line.startswith("#"):
            inside = bool(re.match(rf"#+\s+{re.escape(section)}\.", line))
            continue
        if inside:
            out.update(m.rstrip(".,;") for m in re.findall(r"https?://[^\s`\"\)\]|]+", line))
    return out


def rules_document(survey_text: str | None, rock_text: str | None = None, stretch_h: float | None = None,
                   max_km: float | None = None) -> dict:
    """rehearsal_rules.json: the table above, worded as the page prints it."""
    if survey_text is not None:
        listed = section_links(survey_text, SURVEY_SECTION)
        missing = [s["link"] for s in SOURCES.values() if s["link"] not in listed]
        if missing:
            raise PlannerError(f"these links are not in section {SURVEY_SECTION} of the survey: {missing}")
    activities = []
    for one in ACTIVITIES:
        suggestions = []
        for s in one["suggestions"]:
            entry = {"text": s["text"], "tag": s["tag"], "source": dict(SOURCES[s["source"]]) if s.get("source") else None}
            if s.get("done_how"):
                entry["done_how"] = s["done_how"]
            suggestions.append(entry)
        activities.append({
            "id": one["id"], "activity": one["activity"],
            "inputs": [{"key": k, "symbol": INPUTS[k]["symbol"], "name": INPUTS[k]["name"], "unit": INPUTS[k]["unit"]}
                       for k in _input_keys(one)],
            "pass": [{"input": k, "op": op, "value": v} for k, op, v in one["pass"]],
            "near": [{"input": k, "op": op, "value": v} for k, op, v in one["near"]],
            "pass_rule": rule_words("Pass", one["pass"]), "near_rule": rule_words("Near", one["near"]),
            "label": LABEL, "suggestions": suggestions})
    notes = [
        "An unknown input is never counted as a fail.",
        "Each input is rounded as it is printed before the rule is applied.",
        "C and T are means over the three periods, each taken from the month of its middle day.",
        "The three periods may run over the new year.",
        "Where the snow maps are doubtful, the lower and more cautious snow-free odds are used.",
        "In Antarctica the snow is not measured, so S is unknown there.",
        "A rule that needs S then reads 'cannot tell', unless the known inputs already decide the verdict.",
        "In Antarctica K is the share of all low-Sun hours in those periods that the terrain leaves.",
        "C counts cloud over all hours of the month, so it says too little about a Sun this low.",
        "T is a model mean over all hours and a wide grid box, not the air during the low-Sun hours.",
    ]
    if stretch_h is not None:
        notes.insert(3, f"H30 counts only hours inside spells of at least {stretch_h:g} hours with the Sun in the band.")
    if rock_text:
        notes.append(f"In Antarctica H30 counts the rock season only, {rock_text}, with terrain but without snow.")
    if max_km is not None:
        notes.append(f"When no airfield of that kind lies within {max_km:,.0f} km, D counts as more than {max_km:,.0f} km.")
    return {
        "label": LABEL,
        "inputs": [{"key": k, "symbol": v["symbol"], "name": v["name"], "unit": v["unit"]} for k, v in INPUTS.items()],
        "activities": activities,
        "verdicts": [{"word": w, "code": c, "means": VERDICT_MEANS[w]} for w, c in VERDICT_CODES.items()],
        "notes": notes,
        "sources_from": f"reports/Other teams and prior projects survey.md, section {SURVEY_SECTION}",
        "left_out_sources": LEFT_OUT_SOURCES,
    }


SKIP_WORDS = {"id", "key", "input", "op", "link", "generated", "script", "symbol", "code", "word", "sources_from"}


def all_words(value, key=None):
    """Every text of a file that the page may print (for the word checks)."""
    if key in SKIP_WORDS:
        return
    if isinstance(value, str):
        if not value.startswith("http"):
            yield value
    elif isinstance(value, dict):
        for k, v in value.items():
            yield from all_words(v, k)
    elif isinstance(value, list):
        for v in value:
            yield from all_words(v, key)


# ---- the best three-period stretch ----

def stretch_windows(season: list[int] | None, n_bins: int = sun.N_BINS, length: int = STRETCH_PERIODS) -> list[list[int]]:
    """Every run of `length` ten-day periods in a row: round the whole year, or inside one season (a run that may wrap)."""
    if season is None:
        return [[(start + k) % n_bins for k in range(length)] for start in range(n_bins)]
    season = [int(b) for b in season]
    for a, b in zip(season, season[1:]):
        if (a + 1) % n_bins != b:
            raise PlannerError(f"the season {season} is not one run of periods in a row")
    return [season[i:i + length] for i in range(len(season) - length + 1)]


def best_stretch(hours, windows) -> tuple[np.ndarray, np.ndarray]:
    """H30 and the first period of the best window, per row of hours [rows, 36].

    Unknown (NaN, NaN) when a period the windows use is unknown. When the best sum rounds to 0.0 h there
    is no stretch to name: H30 is 0 and the first period NaN. Ties go to the earliest window in the list.
    """
    hours = np.atleast_2d(np.asarray(hours, dtype=float))
    index = np.asarray(windows, dtype=int)
    sums = hours[:, index].sum(axis=-1)                                    # [rows, windows]
    unknown = np.isnan(hours[:, sorted(set(index.ravel()))]).any(axis=-1)
    best = np.where(unknown[:, None], 0.0, sums).argmax(axis=-1)
    h30 = sums[np.arange(len(hours)), best]
    first = index[best, 0].astype(float)
    h30[unknown] = np.nan
    first[unknown | (np.round(np.nan_to_num(h30), 1) <= 0.0)] = np.nan
    return h30, first


# ---- rose and skyline ----

def sector_hours(minutes, elev_bins, lat_of_cell, north, odds, shares: dict, south_season=None) -> np.ndarray:
    """Low-Sun hours per compass sector [areas, 36]: the project's open_hours with each sector passed as its own row.

    minutes is one lunar region's long-spell Sun table [latitudes, 36 periods, 36 sectors, 9 elevation bins].
    North: the year, times the area's snow-free odds. South: the periods of south_season, terrain only
    (the snow is not measured). Rows of areas without an open share stay unknown.
    """
    lat_of_cell, north = np.asarray(lat_of_cell, dtype=int), np.asarray(north, dtype=bool)
    out = np.full((len(lat_of_cell), sun.AZ_SECTORS), np.nan)
    for side in (True, False):
        rows = [i for i in sorted(shares) if north[i] == side]
        for start in range(0, len(rows), BATCH):
            batch = rows[start:start + BATCH]
            lit = np.moveaxis(np.asarray(minutes)[lat_of_cell[batch]], -2, 1)[:, :, :, None, :]   # [area, sector, period, 1, elev]
            share = np.stack([np.asarray(shares[i], dtype=float) for i in batch])[:, :, None, :]  # [area, sector, 1, elev]
            snow = np.asarray(odds, dtype=float)[batch][:, None, :] if side else None             # [area, 1, period]
            per_period = grazing.open_hours(lit, elev_bins, share, snow)                          # [area, sector, period]
            out[batch] = grazing.total(per_period, None if side else list(south_season))
    return out


def rose_bytes(hours) -> np.ndarray:
    """uint8 [..., 37]: 36 sectors scaled so the largest is 200, then a status byte (0 given, 1 no hours, 255 unknown)."""
    hours = np.asarray(hours, dtype=float)
    out = np.full(hours.shape[:-1] + (sun.AZ_SECTORS + 1,), UNKNOWN8, dtype=np.uint8)
    known = np.isfinite(hours).all(axis=-1)
    safe = np.where(known[..., None], hours, 0.0)
    top = safe.max(axis=-1)
    none = known & (np.round(safe.sum(axis=-1), 1) <= 0.0)
    given = known & ~none & (top > 0.0)
    scaled = np.rint(ROSE_TOP * safe / np.where(top > 0.0, top, 1.0)[..., None])
    out[..., :-1][given] = np.clip(scaled[given], 0, ROSE_TOP).astype(np.uint8)
    out[..., -1][given] = ROSE_GIVEN
    out[..., -1][none] = ROSE_NO_HOURS
    return out


# The skyline is written on the edges where the stored horizons (data/derived/horizon_cells.json) give the open
# share: the nine old bins (horizon.STORED_EDGES_DEG). The Sun tables have more bins, with an edge at each Sun
# ceiling, but a new edge only repeats the share of the old edge below it (horizon.share_on_edges). A skyline code
# on a new edge would thus give a range that is narrower than the data can tell.
SKYLINE_EDGES_DEG = list(horizon.STORED_EDGES_DEG)


def skyline_columns(edges=None, from_edges=None) -> list[int]:
    """The bins of from_edges (the bins of the shares now) whose lower edge is a lower edge of the skyline edges."""
    edges = SKYLINE_EDGES_DEG if edges is None else edges
    from_edges = sun.ELEV_EDGES_DEG if from_edges is None else from_edges
    lower = [round(e, 6) for e in from_edges[:-1]]
    missing = [e for e in edges[:-1] if round(e, 6) not in lower]
    if missing:
        raise PlannerError(f"the skyline edges {missing} are not lower edges of the Sun table bins")
    return [lower.index(round(e, 6)) for e in edges[:-1]]


def skyline_bytes(shares: dict, n: int) -> np.ndarray:
    """uint8 [areas, 36]: per sector the lowest skyline bin (SKYLINE_EDGES_DEG) that SKYLINE_OPEN_SHARE of the
    ground sees; the bin count for none; 255 unknown."""
    n_elev = len(sun.ELEV_EDGES_DEG) - 1
    columns = skyline_columns()
    n_sky = len(columns)
    out = np.full((n, sun.AZ_SECTORS), UNKNOWN8, dtype=np.uint8)
    for i, share in shares.items():
        share = np.asarray(share, dtype=float)
        if share.shape != (sun.AZ_SECTORS, n_elev) or not np.isfinite(share).all():
            continue
        opened = share[:, columns] >= SKYLINE_OPEN_SHARE
        out[i] = np.where(opened.any(axis=-1), opened.argmax(axis=-1), n_sky)
    return out


def sector_label(k: int) -> str:
    return f"{10 * k}-{10 * k + 10} degrees"


# ---- the whole run ----

def _page_ids(cells_doc: dict) -> list[str]:
    ids = cells_doc.get("ids")
    if not isinstance(ids, list) or not ids:
        raise PlannerError("site/data/cells.json has no list of ids")
    if len(set(ids)) != len(ids):
        raise PlannerError("site/data/cells.json lists an area twice")
    return list(ids)


def _lacking(source: str, ids: list[str], present) -> None:
    missing = [i for i in ids if i not in present]
    if missing:
        raise PlannerError(f"{source} lacks {len(missing)} of the page's {len(ids)} areas, for example {', '.join(missing[:5])}")


def _monthly(doc: dict, field: str, ids: list[str], source: str) -> np.ndarray:
    """[areas, 12] of one monthly field, NaN where unknown."""
    cells = doc.get("cells") or {}
    _lacking(source, ids, cells)
    table = np.full((len(ids), 12), np.nan)
    for row, area_id in enumerate(ids):
        values = (cells[area_id] or {}).get(field)
        if values is None:
            continue
        if len(values) != 12:
            raise PlannerError(f"{source}: {field} of {area_id} has {len(values)} months where 12 are expected")
        table[row] = [float(v) if finite(v) else np.nan for v in values]
    return table


def _airfield(record: dict | None) -> dict | None:
    if not record:
        return None
    return {"name": record.get("name"), "ident": record.get("ident"), "km": rounded(record.get("km"), 1),
            "scheduled_flights": bool(record.get("scheduled_service"))}


def export(derived: Path, site_data: Path, out: Path | None = None, survey: Path | None = SURVEY,
           cell_inputs=grazing.cell_inputs, sun_table=sun.long_band_minutes_table) -> dict:
    """Build every planner file whose inputs are there and write them; return what was written and left out."""
    derived, site_data = Path(derived), Path(site_data)
    out = Path(out) if out is not None else site_data
    paths = {
        "site/data/cells.json": site_data / "cells.json",
        "site/data/meta.json": site_data / "meta.json",
        "data/derived/grazing_cells.json": derived / "grazing_cells.json",
        "data/derived/grazing_bins.npz": derived / "grazing_bins.npz",
        "data/derived/snow_free_dekads.npz": derived / "snow_free_dekads.npz",
        "data/derived/horizon_cells.json": derived / "horizon_cells.json",
        "data/derived/cloud_cells.json": derived / "cloud_cells.json",
        "data/derived/temperature_cells.json": derived / "temperature_cells.json",
        "data/derived/terrain_cells.json": derived / "terrain_cells.json",
        "data/derived/access_cells.json": derived / "access_cells.json",
    }
    if survey is not None:
        paths["reports/Other teams and prior projects survey.md"] = Path(survey)
    there = {label: path.exists() for label, path in paths.items()}
    for label in ("site/data/cells.json", "site/data/meta.json", "data/derived/grazing_cells.json",
                  "data/derived/grazing_bins.npz"):
        if not there[label]:
            raise FileNotFoundError(f"{paths[label]} is not there; run the pipeline and scripts/export_site.py first")

    # ---- the page's areas and lunar regions, and the pipeline's hours in that order ----
    ids = _page_ids(read_json(paths["site/data/cells.json"]))
    n = len(ids)
    meta = read_json(paths["site/data/meta.json"])
    targets = [t for t in (meta.get("targets") or []) if isinstance(t, dict) and "id" in t]
    if not targets:
        raise PlannerError("site/data/meta.json names no lunar regions")
    month_of_bin = [int(b["month"]) for b in meta["bins"]]
    if len(month_of_bin) != sun.N_BINS:
        raise PlannerError(f"site/data/meta.json has {len(month_of_bin)} ten-day periods where {sun.N_BINS} are expected")
    seasons = meta.get("seasons") or {}
    gdoc = read_json(paths["data/derived/grazing_cells.json"])
    gmeta = gdoc["meta"]
    season = [int(b) for b in seasons.get("rock_season_bins_south", gmeta["summer_bins_south"])]
    if season != [int(b) for b in gmeta["summer_bins_south"]]:
        raise PlannerError("site/data/meta.json and grazing_cells.json name different rock seasons; run export_site.py again")
    rock_text = seasons.get("rock_season_text")
    archive = np.load(paths["data/derived/grazing_bins.npz"], allow_pickle=False)
    g_ids = [c["id"] for c in gdoc["cells"]]
    if g_ids != [str(i) for i in archive["ids"]]:
        raise PlannerError("grazing_cells.json and grazing_bins.npz do not list the same areas in the same order; "
                           "the pipeline may be in the middle of a run, try again")
    g_targets = [t["id"] for t in gmeta["targets"]]
    if g_targets != [str(t) for t in archive["targets"]]:
        raise PlannerError("grazing_cells.json and grazing_bins.npz do not list the same lunar regions")
    position = {cid: k for k, cid in enumerate(g_ids)}
    _lacking("data/derived/grazing_cells.json", ids, position)
    missing_targets = [t["id"] for t in targets if t["id"] not in g_targets]
    if missing_targets:
        raise PlannerError(f"grazing_cells.json lacks the lunar regions {missing_targets}")
    rows = np.array([position[i] for i in ids])
    cols = [g_targets.index(t["id"]) for t in targets]
    tmeta = [gmeta["targets"][c] for c in cols]
    n_t = len(targets)
    cells = [gdoc["cells"][r] for r in rows]
    long_flat = archive["long_flat"][rows][:, cols].astype(float)         # [areas, regions, periods]
    long_snow = archive["long_snow_free"][rows][:, cols].astype(float)
    long_open = archive["long_open"][rows][:, cols].astype(float)
    north = np.array([c["hemisphere"] == "N" for c in cells])
    ranked = np.array([not score.not_ranked_because(c) for c in cells])

    # ---- snow odds and open shares, by the project's own join ----
    odds, shares, snow_check = None, {}, None
    if there["data/derived/snow_free_dekads.npz"]:
        joined = cell_inputs([{"id": c["id"], "lat": c["lat"], "lon": c["lon"]} for c in cells],
                             paths["data/derived/snow_free_dekads.npz"], paths["data/derived/horizon_cells.json"])
        odds = np.asarray(joined["snow"]["odds"], dtype=float)
        shares = dict(joined["shares"])
        again = grazing.snow_free_hours(long_flat, odds[:, None, :])
        both = north[:, None, None] & np.isfinite(again) & np.isfinite(long_snow)
        snow_check = {"largest_difference_h": rounded(float(np.abs(again - long_snow)[both].max()) if both.any() else 0.0, 4),
                      "what": "snow-free hours per period rebuilt from the odds of this run against grazing_bins.npz, north"}
    elif there["data/derived/horizon_cells.json"]:
        _, shares = grazing.horizons_of_cells(cells, paths["data/derived/horizon_cells.json"])

    access = read_json(paths["data/derived/access_cells.json"]) if there["data/derived/access_cells.json"] else None
    max_km = (access.get("meta") or {}).get("max_km") if access else None
    survey_text = paths["reports/Other teams and prior projects survey.md"].read_text() \
        if survey is not None and there["reports/Other teams and prior projects survey.md"] else None

    built: dict[str, bytes] = {}
    left_out: dict[str, str] = {}
    needs: dict[str, list[str]] = {}
    summary: dict = {}
    checks: dict = {"snow_odds_against_grazing_bins": snow_check,
                    "ranked_areas": {"north": int((ranked & north).sum()), "south": int((ranked & ~north).sum())}}

    def lacks(name: str, labels: list[str]) -> bool:
        needs[name] = labels
        missing = [label for label in labels if not there[label]]
        if missing:
            left_out[name] = f"{', '.join(missing)} {'is' if len(missing) == 1 else 'are'} not there"
        return bool(missing)

    built["rehearsal_rules.json"] = json_bytes({"generated": utc_now(), **rules_document(
        survey_text, rock_text, gmeta.get("stretch_min_h"), max_km)})
    needs["rehearsal_rules.json"] = ["reports/Other teams and prior projects survey.md", "data/derived/access_cells.json",
                                     "site/data/meta.json"]

    # ---- distances (D) ----
    km = np.full(n, np.nan)
    beyond = np.zeros(n, dtype=bool)
    field_of = []
    if access:
        records = access.get("cells") or {}
        _lacking("data/derived/access_cells.json", ids, records)
        for i, area_id in enumerate(ids):
            one = records[area_id] or {}
            field = one.get("nearest_scheduled") if north[i] else one.get("nearest")
            field_of.append(field)
            if field and finite(field.get("km")):
                km[i] = float(field["km"])
            elif field is None and max_km is not None and ("nearest_scheduled" if north[i] else "nearest") in one:
                beyond[i] = True
    clear = None
    if there["data/derived/cloud_cells.json"]:
        clear = 1.0 - _monthly(read_json(paths["data/derived/cloud_cells.json"]), "cloud_pct", ids,
                               "data/derived/cloud_cells.json") / 100.0

    # ---- rehearsal.bin ----
    north_windows, south_windows = stretch_windows(None), stretch_windows(season)
    if not lacks("rehearsal.bin", ["data/derived/snow_free_dekads.npz", "data/derived/cloud_cells.json",
                                   "data/derived/temperature_cells.json", "data/derived/terrain_cells.json",
                                   "data/derived/access_cells.json"]):
        t2m = _monthly(read_json(paths["data/derived/temperature_cells.json"]), "t2m_c", ids,
                       "data/derived/temperature_cells.json")
        terrain = read_json(paths["data/derived/terrain_cells.json"])
        _lacking("data/derived/terrain_cells.json", ids, terrain)
        p90 = [rounded((terrain[i] or {}).get("p90_slope_deg"), 1) for i in ids]
        h30 = np.full((n, n_t), np.nan)
        first = np.full((n, n_t), np.nan)
        for side, windows in ((True, north_windows), (False, south_windows)):
            pick = np.flatnonzero(north == side)
            for t in range(n_t):
                h30[pick, t], first[pick, t] = best_stretch(long_open[pick, t], windows)
        verdicts = np.full((n, n_t, len(ACTIVITIES)), VERDICT_CODES["cannot tell"], dtype=np.uint8)
        tally = {t["id"]: {side: {a["id"]: Counter() for a in ACTIVITIES} for side in ("north", "south")} for t in targets}
        for i in range(n):
            bare = rounded(cells[i].get("bare"), 2)
            distance = (max_km, INF) if beyond[i] else rounded(km[i], 1)
            for t in range(n_t):
                values = {"H30": rounded(h30[i, t], 1), "P90": p90[i], "B": bare, "D": distance,
                          "S": None, "C": None, "K": None, "T": None}
                if np.isfinite(first[i, t]):
                    start = int(first[i, t])
                    bins = [(start + k) % sun.N_BINS for k in range(STRETCH_PERIODS)]
                    months = [month_of_bin[b] - 1 for b in bins]
                    if north[i]:
                        values["S"] = rounded(np.mean(odds[i, bins]), 2)
                    values["C"] = rounded(np.mean(clear[i, months]), 2)
                    values["T"] = rounded(np.mean(t2m[i, months]), 1)
                    base = (long_snow if north[i] else long_flat)[i, t, bins].sum()
                    if np.isfinite(base) and base > 0:
                        values["K"] = rounded(long_open[i, t, bins].sum() / base, 2)
                side = "north" if north[i] else "south"
                for a, one in enumerate(ACTIVITIES):
                    word = evaluate(one, values)
                    verdicts[i, t, a] = VERDICT_CODES[word]
                    tally[targets[t]["id"]][side][one["id"]][word] += 1
        h30_tenths = np.where(np.isfinite(h30), np.clip(np.rint(np.nan_to_num(h30) * 10), 0, UNKNOWN16 - 1), UNKNOWN16)
        first_bytes = np.where(np.isfinite(first), np.nan_to_num(first), UNKNOWN8)
        built["rehearsal.bin"] = (h30_tenths.astype("<u2").tobytes() + first_bytes.astype(np.uint8).tobytes()
                                  + verdicts.tobytes())
        summary["rehearsal"] = {t: {side: {a: dict(c) for a, c in by.items()} for side, by in sides.items()}
                                for t, sides in tally.items()}

    # ---- yearplan.json ----
    if not lacks("yearplan.json", ["data/derived/snow_free_dekads.npz", "data/derived/cloud_cells.json",
                                   "data/derived/access_cells.json"]):
        def entry(i: int, t: int, month: int, bins: list[int], hours: float) -> dict:
            snow_known = bool(north[i])
            return {"id": ids[i], "area": i, "lat": cells[i]["lat"], "lon": cells[i]["lon"], "region": cells[i].get("region"),
                    "hours": rounded(hours, 1), "periods": bins,
                    "snow_free_odds": rounded(np.mean(odds[i, bins]), 2) if snow_known else None,
                    "snow": cells[i]["snow"]["status"] if snow_known else "snow not measured",
                    "clear_share": rounded(clear[i, month - 1], 2),
                    "airfield": _airfield(field_of[i]),
                    "airfield_beyond_km": max_km if beyond[i] else None}

        plan = {}
        for t, target in enumerate(targets):
            strips = {"north": [], "south": [], "north_reachable": [], "south_reachable": []}
            for month in range(1, 13):
                in_month = [b for b in range(sun.N_BINS) if month_of_bin[b] == month]
                for side in ("north", "south"):
                    bins = in_month if side == "north" else [b for b in in_month if b in season]
                    best = reach = None
                    if bins:
                        hours = long_open[:, t, bins].sum(axis=-1)             # NaN when a period is unknown
                        allowed = ranked & (north if side == "north" else ~north) & np.isfinite(hours)
                        allowed &= np.round(np.nan_to_num(hours), 1) > MIN_MONTH_HOURS
                        for kind in ("best", "reach"):
                            pool = allowed & (km <= REACH_KM) if kind == "reach" else allowed
                            if pool.any():
                                i = int(np.flatnonzero(pool)[np.argmax(hours[pool])])
                                one = entry(i, t, month, bins, float(hours[i]))
                                best, reach = (one, reach) if kind == "best" else (best, one)
                    strips[side].append(best)
                    strips[f"{side}_reachable"].append(reach)
            plan[target["id"]] = {"name": target.get("name"), **strips}
        south_months = sorted({month_of_bin[b] for b in season}, key=lambda m: [month_of_bin[b] for b in season].index(m))
        built["yearplan.json"] = json_bytes({
            "generated": utc_now(), "months": MONTHS, "min_hours": MIN_MONTH_HOURS, "reach_km": REACH_KM,
            "south_months": south_months, "targets": plan,
            "words": {
                "hours": "Low-Sun hours after snow and terrain in the ten-day periods whose middle day falls in the month.",
                "ranked": f"Only ranked areas are named: measured snow in the north, a terrain figure, and a bare share "
                          f"of at least {score.RANK_MIN_BARE:g}.",
                "reachable": f"Reachable: within {REACH_KM:g} km of an airfield with scheduled flights; in Antarctica, "
                             f"of any listed airfield.",
                "distance": "Distances are straight lines from the middle of the area to the runway.",
                "south": (f"In Antarctica only the rock season counts, {rock_text}." if rock_text
                          else "In Antarctica only the rock season counts."),
                "snow": "Antarctic entries carry the words 'snow not measured'.",
                "none": f"No entry means that no ranked area has more than {MIN_MONTH_HOURS:g} h in that month.",
                "clear": "The clear share is one minus the mean cloud cover of the month, over all hours of day and night.",
            },
        })
        summary["yearplan_months_with_an_entry"] = {
            t: {k: sum(e is not None for e in v) for k, v in strips.items() if isinstance(v, list)} for t, strips in plan.items()}

    # ---- rose.bin ----
    if not lacks("rose.bin", ["data/derived/snow_free_dekads.npz", "data/derived/horizon_cells.json"]):
        lats = sorted({cells[i]["lat"] for i in shares})
        lat_index = {lat: k for k, lat in enumerate(lats)}
        lat_of_cell = np.array([lat_index.get(c["lat"], 0) for c in cells])
        table = sun_table(lats, [t["limit_deg"] for t in tmeta], float(gmeta["stretch_min_h"]), gmeta["step_minutes"],
                          year_phases=int(gmeta["year_phases"])) if lats else None
        rose = np.full((n, n_t, sun.AZ_SECTORS + 1), UNKNOWN8, dtype=np.uint8)
        largest, apart, known_differs = 0.0, 0, 0
        directions = {}
        for t in range(n_t):
            if table is None:
                break
            by_sector = sector_hours(table[t], tmeta[t]["elev_bins"], lat_of_cell, north, odds, shares, south_season=season)
            rose[:, t] = rose_bytes(by_sector)
            mine = by_sector.sum(axis=-1)
            theirs = np.where(north, grazing.total(long_open[:, t]), grazing.total(long_open[:, t], season))
            both = np.isfinite(mine) & np.isfinite(theirs)
            gap = np.abs(mine - theirs)[both]
            largest = max(largest, float(gap.max()) if gap.size else 0.0)
            apart += int((gap > 0.1).sum())
            known_differs += int((np.isfinite(mine) != np.isfinite(theirs)).sum())
            for side, mask in (("north", north), ("south", ~north)):
                many = mask & np.isfinite(mine) & (mine >= 100.0)
                top = Counter(int(k) for k in np.argmax(by_sector[many], axis=-1)) if many.any() else Counter()
                directions.setdefault(targets[t]["id"], {})[side] = {
                    "areas_with_at_least_100_h": int(many.sum()),
                    "most_common_strongest_sector": [{"sector": k, "azimuth": sector_label(k), "areas": c}
                                                     for k, c in top.most_common(3)]}
        built["rose.bin"] = rose.tobytes()
        checks["rose_against_grazing_bins"] = {
            "largest_difference_h": round(largest, 4), "areas_more_than_0_1_h_apart": apart,
            "areas_known_in_one_and_unknown_in_the_other": known_differs,
            "what": "sum of the 36 sectors against the hours of grazing_bins.npz (north: the year; south: the rock season), "
                    "over all lunar regions"}
        summary["rose_directions"] = directions

    # ---- skyline.bin ----
    if not lacks("skyline.bin", ["data/derived/horizon_cells.json"]):
        built["skyline.bin"] = skyline_bytes(shares, n).tobytes()

    # ---- write, then the index ----
    out.mkdir(parents=True, exist_ok=True)
    previous = read_json(out / "planner.json") if (out / "planner.json").exists() else None
    made_for = ((previous or {}).get("areas") or {}).get("ids_sha256")
    written = {name: write_bytes(out / name, data) for name, data in built.items()}
    removed = {}
    for name in left_out:
        if name in AREA_FILES and (out / name).exists() and made_for != ids_sha256(ids):
            (out / name).unlink()
            removed[name] = "it was made for another list of areas than the page has now"
    sources_written = {}
    for label, path in paths.items():
        if not there[label]:
            sources_written[label] = None
            continue
        inside = None
        if label == "data/derived/access_cells.json" and access:
            inside = (access.get("meta") or {}).get("written")
        elif label == "site/data/meta.json":
            inside = meta.get("generated")
        sources_written[label] = {"modified": modified(path), "bytes": path.stat().st_size, "written_inside": inside}
    layouts = file_layouts(n, n_t, max_km)
    index = {
        "generated": utc_now(),
        "script": "scripts/export_site_planner.py",
        "how_to_rerun": "uv run python scripts/export_site.py, then uv run python scripts/export_site_planner.py",
        "unknown": "null in the JSON files; 255 in the uint8 bytes and 65535 in the uint16 block of rehearsal.bin; never 0",
        "areas": {"count": n, "order": "the ids of site/data/cells.json, as it was when this ran", "ids_sha256": ids_sha256(ids),
                  "ids_sha256_what": "SHA-256 of the ids joined by a line feed, in order",
                  "what": "read a per-area file only when count and ids_sha256 match the page's cells.json"},
        "targets": [t["id"] for t in targets], "target_names": [t.get("name") for t in targets],
        "files": {name: {"bytes": size, "from": [label for label in needs.get(name, []) if there.get(label)],
                         "layout": layouts[name]["layout"], "feeds": layouts[name]["feeds"]}
                  for name, size in written.items()},
        "left_out": [{"file": name, "because": why, "older_copy_kept": (out / name).exists()} for name, why in left_out.items()],
        "older_copies_removed": [{"file": k, "because": v} for k, v in removed.items()],
        "sources_written": sources_written,
        "checks": checks,
        "summary": summary,
    }
    write_bytes(out / "planner.json", json_bytes(index))
    return {"written": written, "left_out": left_out, "removed": removed, "out": str(out), "areas": n,
            "summary": summary, "checks": checks}


def file_layouts(n: int, n_t: int, max_km) -> dict:
    """What planner.json says of each file: its exact layout and the feature it feeds."""
    order = "area (the order of ids in cells.json), then lunar region (the order of targets here)"
    edges = list(sun.ELEV_EDGES_DEG)
    sky = list(SKYLINE_EDGES_DEG)   # the skyline: the old bins only (see skyline_bytes)
    return {
        "rehearsal_rules.json": {
            "layout": {"label": "the words to print with every verdict",
                       "inputs": "[{key, symbol, name, unit}] every input of the rules",
                       "activities": "[{id, activity, inputs [{key, symbol, name, unit}], pass [{input, op, value}], near [...], "
                                     "pass_rule, near_rule (print as written), label, suggestions [{text, tag ('done by NASA' "
                                     "or 'our suggestion'), source {name, link} or null, done_how}]}], in the order of the "
                                     "verdict bytes of rehearsal.bin",
                       "verdicts": "[{word, code, means}]", "notes": "sentences to print under the rules",
                       "left_out_sources": "sources the plan named that we do not cite, and why"},
            "feeds": "features 7 and 8: the four choices, the rules printed on the place card, the tags of the suggestions"},
        "rehearsal.bin": {
            "layout": {"byte_order": "little-endian; three blocks one after another",
                       "total_bytes": n * n_t * (3 + len(ACTIVITIES)),
                       "blocks": [
                           {"name": "h30", "offset_bytes": 0, "type": "uint16", "shape": [n, n_t], "order": order,
                            "unit": "tenths of an hour", "unknown": UNKNOWN16,
                            "what": "the most low-Sun hours after snow and terrain in three ten-day periods in a row; "
                                    "Antarctica: inside the rock season, terrain only"},
                           {"name": "first_period", "offset_bytes": 2 * n * n_t, "type": "uint8", "shape": [n, n_t],
                            "order": order, "what": "the ten-day period (0 to 35, meta.json bins) that starts that stretch",
                            "unknown": UNKNOWN8, "also_255": "no stretch to name, because H30 is 0"},
                           {"name": "verdicts", "offset_bytes": 3 * n * n_t, "type": "uint8",
                            "shape": [n, n_t, len(ACTIVITIES)], "order": order + ", then activity",
                            "activities": [a["id"] for a in ACTIVITIES], "codes": VERDICT_CODES,
                            "never": "0 is never written: a 0 means a broken file"}],
                       "read_in_js": f"new Uint16Array(buf, 0, {n}*{n_t}); new Uint8Array(buf, 2*{n}*{n_t}, {n}*{n_t}); "
                                     f"new Uint8Array(buf, 3*{n}*{n_t}, {n}*{n_t}*{len(ACTIVITIES)})",
                       "distance_beyond_km": max_km},
            "feeds": "features 7 and 8: re-sorting the short lists by activity, and pass, near or does not pass on the card"},
        "yearplan.json": {
            "layout": {"months": "the twelve month names", "min_hours": "an entry needs more than this many hours",
                       "reach_km": "the distance that counts as reachable", "south_months": "months of the rock season",
                       "targets": "{lunar region id: {name, north, south, north_reachable, south_reachable}}: each a list of "
                                  "12 entries, January first; an entry is null when no ranked area qualifies, or {id, area "
                                  "(index in cells.json), lat, lon, region, hours, periods, snow_free_odds (null in "
                                  "Antarctica), snow, clear_share (null when unknown), airfield {name, ident, km, "
                                  "scheduled_flights} or null, airfield_beyond_km}",
                       "words": "sentences to print with the strip"},
            "feeds": "feature 10: the twelve-column year plan"},
        "rose.bin": {
            "layout": {"type": "uint8", "shape": [n, n_t, sun.AZ_SECTORS + 1], "order": order + ", then byte",
                       "bytes_0_to_35": "compass sector k covers azimuth 10k to 10k + 10 degrees, 0 = north, clockwise",
                       "scale": f"the largest sector is {ROSE_TOP}; the share of sector k is byte k over the sum of bytes 0 to 35",
                       "byte_36": f"{ROSE_GIVEN} = shares given; {ROSE_NO_HOURS} = no such hours (a known zero, bytes 0 to 35 "
                                  f"are 255); {UNKNOWN8} = total unknown, no terrain figure or no snow odds (bytes 0 to 35 "
                                  f"are 255)",
                       "hours": "north: the year's low-Sun hours after snow and terrain; Antarctica: the rock season, "
                                "after terrain, snow not measured",
                       "unknown": UNKNOWN8},
            "feeds": "feature 11: the compass picture of where the low Sun stands"},
        "skyline.bin": {
            "layout": {"type": "uint8", "shape": [n, sun.AZ_SECTORS], "order": "area (cells.json), then compass sector",
                       "value": f"e, the lowest elevation bin that at least {SKYLINE_OPEN_SHARE:g} of the area's ground sees "
                                f"over the skyline in that sector",
                       "elevation_bin_edges_deg": sky,
                       "meaning": f"0: that skyline is below {sky[0]:g} degrees; e from 1 to {len(sky) - 2}: it lies from "
                                  f"edges[e-1] up to edges[e]; {len(sky) - 1}: it is at or above {sky[-2]:g} degrees",
                       "edges": (f"The skyline uses the {len(sky) - 1} old bins of Sun height. The stored horizons give the "
                                 f"open share at these edges only. The Sun tables use {len(edges) - 1} bins, with an edge "
                                 f"at each Sun ceiling. At a new edge, the open share is the share of the old edge below "
                                 f"it. Thus the skyline does not use the new edges."),
                       "unknown": UNKNOWN8},
            "feeds": "feature 11: the ring of the terrain skyline around the compass picture"},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--derived", type=Path, default=ROOT / "data" / "derived")
    parser.add_argument("--site-data", type=Path, default=ROOT / "site" / "data")
    parser.add_argument("--survey", type=Path, default=SURVEY)
    parser.add_argument("--out", type=Path, default=None, help="where to write (default: the site-data folder)")
    args = parser.parse_args()
    report = export(args.derived, args.site_data, args.out, args.survey)
    print(f"{report['areas']} areas; wrote into {report['out']}:")
    for name, size in report["written"].items():
        print(f"  {name:22s} {size:>10,d} bytes")
    for name, why in report["left_out"].items():
        print(f"left out: {name} ({why})")
    for name, why in report["removed"].items():
        print(f"removed an older copy: {name} ({why})")
    rose = report["checks"].get("rose_against_grazing_bins")
    if rose:
        print(f"rose against grazing_bins.npz: largest difference {rose['largest_difference_h']} h, "
              f"{rose['areas_more_than_0_1_h_apart']} more than 0.1 h apart")


if __name__ == "__main__":
    main()

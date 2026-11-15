"""Write UV, sunlight at the ground, clear-sky days and haze as files the map page can read (site/data).

    uv run python scripts/export_site.py                  # first: it decides the order of the areas
    uv run python scripts/export_site_environment.py      # then this (no network)

Only numpy and the standard library. Nothing under data/ is written. The order of the areas is taken
from site/data/cells.json; the order of the Mars squares from site/data/mars.json when it is there,
else from data/derived/mars_cells.json. An area or square the source lacks stops that file with an
error instead of shifting its rows.

Writes, into site/data (or --out):
    environment.json        layout of environment.bin, what each figure is and is not, sources, and
                            the short sentences the page prints (Moon comparison included)
    environment.bin         uint16 little-endian [areas, fields, 12 months], hundredths; 65535 = unknown
    mars_environment.json   the same for the Mars squares, when data/derived/mars_environment.json is there
    mars_environment.bin    uint16 little-endian: a monthly block, then a yearly block; 65535 = unknown

Every value is a NASA POWER monthly climatology of the 1 degree grid box that holds the area: a coarse
mean, not a measurement at the place. Unknown is null in JSON and 65535 in the binary files, never 0.
"""
from __future__ import annotations

import argparse
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
UNKNOWN = 65535                  # the unknown value of the binary files
SCALE = 100                      # every stored value is in hundredths of its unit
EARTH_KM = 6371.0                # the sphere the rest of the project measures on
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]
TAG = "NASA POWER, monthly mean on a coarse grid"
CAPTION = "Drawn by code from open data; the code was written with AI assistance."
BEST_PERIODS = 3                 # the card names the area's best three ten-day periods
BEST_FROM_STEP = 3               # ... at the terrain step
FALLBACK_STEP = 2                # ... or at the snow-free step when the area has no terrain hours
MOON_FIELDS = ["uv_index", "sun_kwh_m2_day", "sun_clear_kwh_m2_day", "clear_days", "aod_550", "cloud_day_pct_fallback"]
MARS_MONTHLY = ["uv_index", "uv_index_brightest_hour", "sun_kwh_m2_day", "clear_days", "aod_550"]
MARS_YEARLY = ["sun_kwh_m2_day_year", "sun_clear_sky_kwh_m2_day_year", "uv_index_year", "uv_index_brightest_hour_max",
               "clear_days_year", "aod_550_year", "clearness_index_year", "top_of_atmosphere_kwh_m2_day_year"]
NUMBER_WORDS = {1: "one", 2: "two", 3: "three", 4: "four"}


class EnvError(Exception):
    """An input does not say what the page needs; the file it feeds is not written."""


# ---- small helpers ----

def read_json(path: Path):
    if not path.exists():
        return None
    with open(path) as handle:
        return json.load(handle)


def write_bytes(path: Path, data: bytes) -> int:
    """Write beside the target and rename, so a reader never sees half a file. Returns the size."""
    path.parent.mkdir(parents=True, exist_ok=True)
    side = path.with_name(path.name + ".part")
    side.write_bytes(data)
    os.replace(side, path)
    return len(data)


def json_bytes(value) -> bytes:
    return json.dumps(value, separators=(",", ":"), allow_nan=False, ensure_ascii=False).encode()


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def known(value) -> bool:
    return value is not None and not (isinstance(value, float) and math.isnan(value))


def pack(rows, scale: int = SCALE) -> np.ndarray:
    """uint16 of round(value * scale); None and NaN become UNKNOWN. A value that cannot be held is an error."""
    table = np.array([[v if known(v) else np.nan for v in row] for row in rows], dtype=float)
    unknown = np.isnan(table)
    scaled = np.round(np.where(unknown, 0.0, table) * scale)
    if (scaled < 0).any() or (scaled >= UNKNOWN).any():
        raise EnvError(f"a value lies outside 0 to {(UNKNOWN - 1) / scale}: it cannot be stored in hundredths")
    out = scaled.astype("<u2")
    out[unknown] = UNKNOWN
    return out


def decimals_served(values) -> int | None:
    """The fewest decimals that hold every value as served (at most 6); None without a value."""
    values = [v for v in values if known(v)]
    if not values:
        return None
    for digits in range(7):
        if all(abs(round(v, digits) - v) < 1e-9 for v in values):
            return digits
    return 6


def grid_km(deg: float | None) -> int | None:
    return None if deg is None else int(round(deg * math.pi * EARTH_KM / 180.0))


def superscript(text: str) -> str:
    return text.translate(str.maketrans("-0123456789", "⁻⁰¹²³⁴⁵⁶⁷⁸⁹"))


def sci(value: float) -> str:
    """3e-15 as '3 × 10⁻¹⁵'."""
    mantissa, exponent = f"{value:.0e}".split("e")
    return f"{mantissa} × 10{superscript(str(int(exponent)))}"


def years_words(period: str | None) -> str | None:
    """'2001-01-01 to 2025-12-31' or '2001-2020' as '2001 to 2020'."""
    found = re.findall(r"\b(\d{4})\b", period or "")
    return f"{found[0]} to {found[-1]}" if len(found) >= 2 else None


def _say(template: str, **values) -> str | None:
    return None if any(v is None for v in values.values()) else template.format(**values)


def _keep(*sentences) -> list[str]:
    return [s for s in sentences if s]


# ---- the page's order ----

def page_area_ids(cells_doc: dict | None) -> list[str]:
    ids = (cells_doc or {}).get("ids")
    if not isinstance(ids, list) or not ids:
        raise EnvError("site/data/cells.json has no list of ids")
    if len(set(ids)) != len(ids):
        raise EnvError("site/data/cells.json lists an area twice")
    if (cells_doc or {}).get("n") not in (None, len(ids)):
        raise EnvError("site/data/cells.json: n does not equal the number of ids")
    return ids


def mars_order(site_mars: dict | None, mars_cells: dict | None) -> tuple[list[str], str, str]:
    """The Mars squares in the page's order: (ids, where the order came from, the words that say so)."""
    squares = (site_mars or {}).get("squares")
    if isinstance(squares, dict) and isinstance(squares.get("ids"), list) and squares["ids"]:
        ids = squares["ids"]
        if squares.get("count") not in (None, len(ids)):
            raise EnvError("site/data/mars.json: squares.count does not equal the number of squares.ids")
        return ids, "site/data/mars.json", "the order of squares.ids in site/data/mars.json (the page's Mars file)"
    cells = (mars_cells or {}).get("cells")
    if isinstance(cells, dict) and cells:
        return list(cells), "data/derived/mars_cells.json", \
            "the order of cells in data/derived/mars_cells.json (site/data/mars.json was not there)"
    if isinstance(cells, list) and cells:
        return [c["id"] for c in cells], "data/derived/mars_cells.json", \
            "the order of cells in data/derived/mars_cells.json (site/data/mars.json was not there)"
    raise EnvError("no order for the Mars squares: neither site/data/mars.json nor data/derived/mars_cells.json lists them")


# ---- the Moon part ----

def moon_table(env_doc: dict, ids: list[str], cloud_doc: dict | None) -> tuple[np.ndarray, dict]:
    """uint16 [areas, MOON_FIELDS, 12] in the order of ids, and what the cloud fallback did."""
    cells = env_doc.get("cells") or {}
    missing = [i for i in ids if i not in cells]
    if missing:
        raise EnvError(f"environment_cells.json lacks {len(missing)} of the page's {len(ids)} areas, "
                       f"for example {', '.join(missing[:5])}")
    cloud_cells = (cloud_doc or {}).get("cells") or {}
    planes, area_months, areas = [], 0, 0
    rows = {field: [] for field in MOON_FIELDS}
    for area_id in ids:
        record = cells[area_id]
        for field in MOON_FIELDS[:-1]:
            values = record.get(field)
            if values is None:
                values = [None] * 12
            if len(values) != 12:
                raise EnvError(f"environment_cells.json: {field} of {area_id} has {len(values)} months where 12 are expected")
            rows[field].append(values)
        cloud = (cloud_cells.get(area_id) or {}).get("cloud_pct_day") or [None] * 12
        fallback = [cloud[m] if not known(rows["clear_days"][-1][m]) and known(cloud[m]) else None for m in range(12)]
        used = sum(1 for v in fallback if v is not None)
        area_months += used
        areas += 1 if used else 0
        rows["cloud_day_pct_fallback"].append(fallback)
    for field in MOON_FIELDS:
        planes.append(pack(rows[field]))
    table = np.stack(planes, axis=1)
    return table, {"area_months_using_it": area_months, "areas_using_it": areas}


def _lunar_facts(moon_cards: dict | None, targets: list[dict]) -> dict:
    """What the Moon comparison needs from moon_cards.json: the vacuum, the dust line, the share of time lit."""
    cards = {c.get("id"): c for c in (moon_cards or {}).get("cards") or []}
    vacuum, dust = None, None
    for card in cards.values():
        for item in card.get("earth_cannot_match") or []:
            if item.get("what") == "vacuum" and known(item.get("number")):
                vacuum = vacuum or {"bar": item["number"], "source": item.get("source")}
            if item.get("what") == "dust" and item.get("moon"):
                dust = dust or item["moon"]
    lit = {}
    for target in targets:
        share = ((cards.get(target["id"]) or {}).get("lit") or {}).get("mean_share")
        lit[target["id"]] = None if not known(share) else int(round(share * 100))
    return {"vacuum": vacuum, "dust": dust, "lit": lit}


def _targets(meta_doc: dict | None) -> list[dict]:
    return [{"id": t["id"], "name": t.get("name") or t["id"], "limit_deg": t.get("limit_deg")}
            for t in (meta_doc or {}).get("targets") or [] if isinstance(t, dict) and "id" in t]


def _uv_ratio(meta: dict) -> tuple[float, float, int] | None:
    """(lowest, highest, boxes) of the brightest hour over the 24-hour mean at the boxes the build checked."""
    ratios = []
    for point in ((meta.get("checks") or {}).get("uv_index_daily_value") or {}).get("points") or []:
        result = point.get("result") or {}
        mean, high = result.get("mean_of_hours_mean"), result.get("highest_hour_mean")
        if known(mean) and known(high) and mean > 0:
            ratios.append(high / mean)
    return (round(min(ratios), 1), round(max(ratios), 1), len(ratios)) if ratios else None


def _uv_ratio_words(ratio) -> str | None:
    """The ratio said only for where it was checked: ten summer days at the build's check boxes."""
    if ratio is None:
        return None
    lo, hi, n = ratio
    boxes = f"{NUMBER_WORDS.get(n, n)} box{'es' if n != 1 else ''} checked"
    times = f"about {lo:g}" if lo == hi else f"{lo:g} to {hi:g}"
    return f"Over ten summer days at {boxes}, the brightest hour was {times} times the 24-hour mean."


def _years_fit(meta: dict, parameters: list[str]) -> str | None:
    summary = ((meta.get("checks") or {}).get("period") or {}).get("summary") or {}
    fits = Counter(summary[p]["fits_better"] for p in parameters if isinstance(summary.get(p), dict) and summary[p].get("fits_better"))
    return years_words(fits.most_common(1)[0][0]) if fits else None


def _field_record(meta: dict, field: str, parameter: str | None, served: int | None, unit_words: str) -> dict:
    p = (meta.get("parameters") or {}).get(parameter) or {}
    return {"parameter": parameter, "name_in_the_service": p.get("name_in_the_service"),
            "definition_in_the_service": p.get("definition_in_the_service"),
            "unit_in_the_service": p.get("unit"), "unit_words": unit_words,
            "source_named_by_the_service": p.get("source_named_by_the_service"), "grid": p.get("grid"),
            "period_named_by_the_service": p.get("period_named_by_the_service"),
            "decimals_served": served, "stored_in": "hundredths (value = stored / 100)",
            "rounded_when_stored": None if served is None else served > 2,
            "what_it_is_source_words": p.get("what_it_is"), "what_it_is_not_source_words": p.get("what_it_is_not")}


def moon_groups(env_doc: dict, moon_cards: dict | None, targets: list[dict]) -> tuple[list[dict], dict, list[str]]:
    """The four rows of the card, the field records, and the general sentences, all with the data's own figures."""
    meta = env_doc.get("meta") or {}
    names = meta.get("fields") or {}
    cells = env_doc.get("cells") or {}
    sample = list(cells.values())
    served = {f: decimals_served([v for r in sample for v in (r.get(f) or [])]) for f in MOON_FIELDS[:-1]}
    first_grid = next((r.get("grid") for r in sample if isinstance(r.get("grid"), dict)), {}) or {}
    km = grid_km(first_grid.get("deg"))
    facts = _lunar_facts(moon_cards, targets)
    clear_parameter = names.get("clear_days_total")
    definition = ((meta.get("parameters") or {}).get(clear_parameter) or {}).get("definition_in_the_service") or ""
    limit = re.search(r"less than (\d+) percent", definition)
    cloud_limit = limit.group(1) if limit else None
    years = (meta.get("clear_days") or {}).get("years")
    years_period = years_words((meta.get("clear_days") or {}).get("period"))
    ratio = _uv_ratio(meta)
    aod_digits = served.get("aod_550")
    vacuum = facts["vacuum"]
    no_air = "The Moon has no air" + ("" if vacuum is None else f" (surface pressure about {sci(vacuum['bar'])} bar at night)")

    fields = {
        "uv_index": _field_record(meta, "uv_index", names.get("uv_index"), served["uv_index"], "UV index"),
        "sun_kwh_m2_day": _field_record(meta, "sun_kwh_m2_day", names.get("sun_kwh_m2_day"), served["sun_kwh_m2_day"],
                                        "kilowatt-hours per square metre per day"),
        "sun_clear_kwh_m2_day": _field_record(meta, "sun_clear_kwh_m2_day", names.get("sun_clear_kwh_m2_day"),
                                              served["sun_clear_kwh_m2_day"], "kilowatt-hours per square metre per day"),
        "clear_days": {**_field_record(meta, "clear_days", clear_parameter, served["clear_days"], "days a month"),
                       "how": "the service's count summed over the years, divided by the number of years",
                       "years": years, "years_period": years_period},
        "aod_550": _field_record(meta, "aod_550", names.get("aod_550"), served["aod_550"], "optical depth, no unit"),
        "cloud_day_pct_fallback": {"parameter": "CLOUD_AMT_DAY", "source": "data/derived/cloud_cells.json, cloud_pct_day",
                                   "unit_words": "percent of the sky, daylight hours", "stored_in": "hundredths",
                                   "rule": "stored only in a month whose clear-day count is unknown; unknown everywhere else"},
    }
    moon_sun = {}
    for target in targets:
        moon_sun[target["id"]] = _keep(
            "No air dims or scatters the Sun there before it reaches the ground.",
            _say("As a mean over the mapped area, the ground at {name} is in sunlight for approximately {pct} percent of "
                 "the time.",   # STE at the source, as data/reference/ste/factors.json gives it
                 name=target["name"], pct=facts["lit"].get(target["id"])),
            "Energy per day on the lunar surface is not in our data.")
    groups = [
        {"key": "sunlight", "heading": "Surface sunlight", "fields": ["sun_kwh_m2_day", "sun_clear_kwh_m2_day"],
         "unit": "kWh/m² a day", "unit_words": "kilowatt-hours per square metre per day", "digits": 2, "unit_inline": True,
         "label_words": "solar energy reaching level ground in a day, all sky; clear-sky figure beside it",
         "is": _keep("Solar energy reaching level ground in a day, direct plus diffuse, under the real mix of cloud and clear.",
                     "The clear-sky figure is worked out as if there were no cloud."),
         "is_not": _keep("It is not what a tilted or Sun-facing panel gets, and not a panel's output.",
                         "It is a whole day's total, not the light in the hours of low Sun."),
         "moon_by_target": moon_sun},
        {"key": "uv", "heading": "UV index", "fields": ["uv_index"], "unit": "UV index", "unit_words": "UV index, no unit",
         "digits": 2, "unit_inline": False, "label_words": "averaged over all 24 hours, not the noon peak",
         "is": _keep("The UV index at the ground under the real sky, averaged over all 24 hours of the day."),
         "is_not": _keep("It is not the noon peak a forecast gives.", _uv_ratio_words(ratio)),
         "moon": _keep(no_air + " and no ozone, so nothing filters its UV, UVC included.",
                       "A lunar UV figure is not in our data.")},
        {"key": "clear_days", "heading": "Clear-sky days", "fields": ["clear_days"], "unit": "days a month",
         "unit_words": "days a month", "digits": 2, "unit_inline": True,
         "label_words": _say("days a month with daytime cloud under {p} percent over the whole grid box", p=cloud_limit)
                        or "days a month with almost no daytime cloud over the whole grid box",
         "fallback_words": "The service gave no clear-day count here, so this is the daytime cloud amount instead.",
         "fallback_unit": "percent of the sky",
         "is": _keep(_say("Days a month when daytime cloud over the whole grid box is under {p} percent.", p=cloud_limit),
                     _say("The service adds its count up over the years; at the boxes checked it fits {n} years ({years}), "
                          "so we divide by {n}.", n=years, years=years_period)),
         "is_not": _keep("It is not the hours a camera can see: a day with some cloud over the box counts as not clear.",
                         "In months without sunlight the count says nothing about seeing by sunlight."),
         "moon": _keep(no_air + " and so no cloud: every day there is cloud-free.")},
        {"key": "haze", "heading": "Haze", "fields": ["aod_550"], "unit": "optical depth", "unit_words": "aerosol optical depth at 550 nm, no unit",
         "digits": 2, "unit_inline": False, "label_words": "all fine particles in the air, not dust alone",
         "is": _keep("Aerosol optical depth at 550 nm: how much fine particles in the whole air column dim sunlight."),
         "is_not": _keep("All fine particles in the air, not dust alone: dust, smoke, sea salt and haze together.",
                         "It says nothing about dust on the ground; the service offers no dust-only figure.",
                         None if aod_digits is None else
                         f"The service gives it to {NUMBER_WORDS.get(aod_digits, aod_digits)} decimals, "
                         f"so 0.{'0' * aod_digits} means below {0.5 * 10 ** -aod_digits:g}."),
         "moon": _keep("The Moon has no air to hold particles; its dust lies on the ground.",
                       None if not facts["dust"] or len(facts["dust"].split()) > 25 else facts["dust"])},
    ]
    named = years_words(next((p.get("period_named_by_the_service") for p in (meta.get("parameters") or {}).values()
                              if p.get("period_named_by_the_service")), None))
    fit = _years_fit(meta, [names.get(f) for f in ("uv_index", "sun_kwh_m2_day", "sun_clear_kwh_m2_day", "clear_days_total", "aod_550")])
    general = _keep(
        _say("Each figure is a monthly mean for a grid box about {km} km tall, not a measurement at the area.", km=km)
        or "Each figure is a monthly mean for a large grid box, not a measurement at the area.",
        "Many areas share one grid box, so neighbours often show the same figures.",
        None if named is None or fit is None or named == fit else
        f"The service names the years {named}, but at the boxes checked its values fit {fit} better.",
        "Every figure is a whole-day mean; none is the hours of low Sun alone.",
        "None of these figures enters any score or ranking.",
        "A month without sunlight shows a true zero for sunlight and UV.",
        f"Figures are shown to {NUMBER_WORDS[round(math.log10(SCALE))]} decimals, "
        f"so {0:.{round(math.log10(SCALE))}f} can be a value below {0.5 / SCALE:g}.")
    return groups, fields, general


def page_sentences(doc: dict) -> list[str]:
    """Every sentence of a page file that the page may print, for the length and wording checks."""
    out = list(doc.get("general") or [])
    for group in doc.get("groups") or []:
        out += [group.get("label_words"), group.get("fallback_words")]
        for key in ("is", "is_not", "moon"):
            out += group.get(key) or []
        for sentences in (group.get("moon_by_target") or {}).values():
            out += sentences
    out += [(doc.get("strip") or {}).get(k) for k in ("caption", "unknown_words", "sunless_words", "best_words", "scale_words", "step_fallback_words",
                                                    "no_best_words", "list_note")]
    sentences = []
    for text in out:
        if text:
            sentences += [s for s in re.split(r"(?<=[.!?])\s+", text) if s]
    return sentences


def environment_doc(env_doc: dict, ids: list[str], table: np.ndarray, fallback: dict, moon_cards: dict | None,
                    targets: list[dict], size: int, mars_file: dict | None) -> dict:
    meta = env_doc.get("meta") or {}
    groups, fields, general = moon_groups(env_doc, moon_cards, targets)
    n, f, m = table.shape
    for group in groups:      # one scale for every area, so the strips of two places can be compared
        planes = table[:, [MOON_FIELDS.index(name) for name in group["fields"]], :]
        known_values = planes[planes != UNKNOWN]
        group["scale_top"] = None if known_values.size == 0 else float(known_values.max()) / SCALE
    return {
        "what": "UV, sunlight at the ground, clear-sky days and haze for every area, by month, for the place card.",
        "source": "data/derived/environment_cells.json", "source_written": meta.get("written"),
        "service": meta.get("source"), "written": utc_now(),
        "areas": {"count": n, "first_id": ids[0], "last_id": ids[-1], "order": "the order of ids in site/data/cells.json"},
        "layout": {"file": "environment.bin", "dtype": "uint16", "byte_order": "little-endian", "shape": [n, f, m],
                   "fields": list(MOON_FIELDS), "months": list(MONTHS), "divide_by": {name: SCALE for name in MOON_FIELDS},
                   "unknown": UNKNOWN, "bytes": size,
                   "how_to_read": "the value of area i, field k, month j (0 = January) is the uint16 at byte offset "
                                  f"2 * ((i * {f} + k) * {m} + j); divide by divide_by[field]; {UNKNOWN} = unknown, never 0"},
        "fields": fields,
        "groups": groups,
        "tag": TAG,
        "general": general,
        "strip": {"caption": CAPTION, "unknown_words": "unknown",
                  "best_periods": BEST_PERIODS, "best_from_step": BEST_FROM_STEP, "fallback_step": FALLBACK_STEP,
                  "sunless_words": "Months without sunlight sit on a tinted band.",
                  "best_words": "Months of the best ten-day periods are marked.",
                  "scale_words": "Each strip uses one scale for all areas, so two places can be compared.",
                  "step_fallback_words": "This area has no terrain hours, so the best periods come from snow-free ground instead.",
                  "no_best_words": "No ten-day period has hours for this lunar region, so the whole year is shown.",
                  "list_note": "clear days a month in the best month"},
        "sunless_rule": "a month whose clear-sky sunlight (sun_clear_kwh_m2_day) is a known 0 has no sunlight at the area's grid box",
        "clear_days_fallback": {"field": "cloud_day_pct_fallback", **fallback,
                                "words": groups[2]["fallback_words"]},
        "unknown": f"{UNKNOWN} in environment.bin and null here: never 0",
        "not_checked": meta.get("not_checked"),
        "mars_file": mars_file,
    }


# ---- the Mars part ----

def mars_tables(mars_doc: dict, ids: list[str]) -> tuple[np.ndarray, np.ndarray]:
    cells = mars_doc.get("cells") or {}
    missing = [i for i in ids if i not in cells]
    if missing:
        raise EnvError(f"mars_environment.json lacks {len(missing)} of the page's {len(ids)} Mars squares, "
                       f"for example {', '.join(missing[:5])}")
    planes = []
    for field in MARS_MONTHLY:
        rows = []
        for square in ids:
            values = cells[square].get(field)
            values = [None] * 12 if values is None else values
            if len(values) != 12:
                raise EnvError(f"mars_environment.json: {field} of {square} has {len(values)} months where 12 are expected")
            rows.append(values)
        planes.append(pack(rows))
    monthly = np.stack(planes, axis=1)
    yearly = pack([[cells[square].get(field) for field in MARS_YEARLY] for square in ids])
    return monthly, yearly


def mars_doc_out(mars_doc: dict, ids: list[str], order_from: str, order_words: str, monthly: np.ndarray,
                 yearly: np.ndarray) -> dict:
    meta = mars_doc.get("meta") or {}
    n, f, m = monthly.shape
    first = monthly.nbytes
    descriptions = meta.get("fields") or {}
    parameters = meta.get("parameters") or {}
    by_field = {"uv_index": "ALLSKY_SFC_UV_INDEX", "uv_index_brightest_hour": "ALLSKY_SFC_UV_INDEX_HR",
                "sun_kwh_m2_day": "ALLSKY_SFC_SW_DWN", "clear_days": "CLRSKY_DAYS", "aod_550": "AOD_55",
                "sun_kwh_m2_day_year": "ALLSKY_SFC_SW_DWN", "sun_clear_sky_kwh_m2_day_year": "CLRSKY_SFC_SW_DWN",
                "uv_index_year": "ALLSKY_SFC_UV_INDEX", "uv_index_brightest_hour_max": "ALLSKY_SFC_UV_INDEX_HR",
                "clear_days_year": "CLRSKY_DAYS", "aod_550_year": "AOD_55", "clearness_index_year": "ALLSKY_KT",
                "top_of_atmosphere_kwh_m2_day_year": "TOA_SW_DWN"}
    fields = {}
    for field in MARS_MONTHLY + MARS_YEARLY:
        p = parameters.get(by_field[field]) or {}
        fields[field] = {"what": descriptions.get(field), "parameter": by_field[field],
                         "unit_in_the_service": p.get("units"), "years_the_values_fit": p.get("years_the_values_fit"),
                         "what_it_is_not": p.get("what_it_is_not"), "stored_in": "hundredths (value = stored / 100)"}
    return {
        "what": "UV, sunlight at the ground, clear-sky days and haze for every ranked Mars-part square.",
        "source": "data/derived/mars_environment.json", "source_written": meta.get("written"),
        "service": meta.get("source"), "written": utc_now(),
        "squares": {"count": n, "ids": list(ids), "order": order_words, "order_from": order_from},
        "layout": {
            "file": "mars_environment.bin", "dtype": "uint16", "byte_order": "little-endian", "unknown": UNKNOWN,
            "bytes": first + yearly.nbytes,
            "monthly": {"offset_bytes": 0, "shape": [n, f, m], "fields": list(MARS_MONTHLY), "months": list(MONTHS),
                        "divide_by": {name: SCALE for name in MARS_MONTHLY},
                        "how_to_read": f"square i, field k, month j (0 = January): the uint16 at byte offset 2 * ((i * {f} + k) * {m} + j)"},
            "yearly": {"offset_bytes": first, "shape": [n, len(MARS_YEARLY)], "fields": list(MARS_YEARLY),
                       "divide_by": {name: SCALE for name in MARS_YEARLY},
                       "how_to_read": f"square i, field k: the uint16 at byte offset {first} + 2 * (i * {len(MARS_YEARLY)} + k)"},
            "not_by_month": "clear-sky sunlight, clearness and top-of-atmosphere sunlight are in the source as yearly values only",
        },
        "fields": fields,
        "tag": TAG,
        "rules": {key: meta.get(key) for key in ("clear_days_rule", "uv_rule", "cell_to_grid", "null_rule")},
        "clear_days_fallback": "none: the Mars source carries no cloud amount, so an unknown clear-day count reads unknown",
        "mars_comparison": meta.get("mars_comparison"),
        "unknown": f"{UNKNOWN} in mars_environment.bin and null here: never 0",
    }


# ---- the export ----

def export(root: Path = ROOT, out: Path | None = None) -> dict:
    """Write the page files; return what was written and what was missing."""
    out = out or root / "site" / "data"
    derived = root / "data" / "derived"
    summary = {"written": [], "missing": [], "environment": None, "mars": None}
    cells_doc = read_json(root / "site" / "data" / "cells.json")
    env_doc = read_json(derived / "environment_cells.json")
    if cells_doc is None or env_doc is None:
        raise EnvError("site/data/cells.json and data/derived/environment_cells.json are both needed")
    ids = page_area_ids(cells_doc)
    targets = _targets(read_json(root / "site" / "data" / "meta.json"))
    moon_cards = read_json(derived / "moon_cards.json")
    if moon_cards is None:
        summary["missing"].append("data/derived/moon_cards.json (the Moon sentences are written without its figures)")
    cloud_doc = read_json(derived / "cloud_cells.json")
    if cloud_doc is None:
        summary["missing"].append("data/derived/cloud_cells.json (no cloud amount for a month without a clear-day count)")

    mars_file = None
    mars_doc = read_json(derived / "mars_environment.json")
    if mars_doc is None:
        summary["missing"].append("data/derived/mars_environment.json (mars_environment.json and .bin not written)")
    else:
        squares, order_from, order_words = mars_order(read_json(root / "site" / "data" / "mars.json"),
                                                      read_json(derived / "mars_cells.json"))
        monthly, yearly = mars_tables(mars_doc, squares)
        size = write_bytes(out / "mars_environment.bin", monthly.tobytes() + yearly.tobytes())
        write_bytes(out / "mars_environment.json", json_bytes(mars_doc_out(mars_doc, squares, order_from, order_words, monthly, yearly)))
        summary["written"] += ["mars_environment.bin", "mars_environment.json"]
        summary["mars"] = {"squares": len(squares), "order_from": order_from, "bytes": size}
        mars_file = {"file": "mars_environment.json", "squares": len(squares), "order_from": order_from}

    table, fallback = moon_table(env_doc, ids, cloud_doc)
    size = write_bytes(out / "environment.bin", table.tobytes())
    doc = environment_doc(env_doc, ids, table, fallback, moon_cards, targets, size, mars_file)
    write_bytes(out / "environment.json", json_bytes(doc))
    summary["written"] += ["environment.bin", "environment.json"]
    summary["environment"] = {"areas": len(ids), "bytes": size, **fallback}
    return summary


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--root", type=Path, default=ROOT, help="project root (default: this project)")
    parser.add_argument("--out", type=Path, default=None, help="folder to write into (default: <root>/site/data)")
    args = parser.parse_args(argv)
    try:
        summary = export(args.root, args.out)
    except EnvError as error:
        print(f"export_site_environment: {error}", file=sys.stderr)
        return 1
    for name in summary["written"]:
        print(f"wrote {name}")
    for name in summary["missing"]:
        print(f"missing: {name}")
    env = summary["environment"]
    print(f"areas {env['areas']}; months using the cloud fallback {env['area_months_using_it']} in {env['areas_using_it']} areas")
    if summary["mars"]:
        print(f"Mars squares {summary['mars']['squares']}, order from {summary['mars']['order_from']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

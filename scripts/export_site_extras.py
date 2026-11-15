"""Write the survey additions as files the map page can read (site/data).

    uv run python scripts/export_site.py           # first: it decides the order of the areas
    uv run python scripts/export_site_extras.py    # then this

Only numpy and the standard library. Nothing under data/ is written. The order of the areas is taken
from site/data/cells.json, so every per-area file here lines up with the page's other files; an area
that a source lacks stops that file with an error instead of shifting its rows.

Writes, into site/data:
    moon.json                 the four lunar fact cards, in the page's site order
    temperature.bin           int8 [areas, 12]: mean air temperature by month, whole degrees C, -128 = unknown
    temperature_surface.bin   the same for the surface temperature, when the source has it
    sunpath.json              the Sun's path at Malapert Massif and at Haughton crater, thinned for a drawing
    validation.json           lower-latitude places, the funnel, known sites, sensitivity, headline sentences,
                              and the station check of the snow maps (from snow_validation_many.json, when it is there)
    sources.json              every source of data/SOURCES.md as a record, the credit lines, the licence line
    places.json               what is known about the places that head the lists; areas not to call little known
    cloud_regions.json        median sky cover by region in the months that matter, and two sentences
    extras.json               an index of the files above: layouts, when each source was written, sizes

An input that is not there is skipped: the outputs that need it are left out and named, and the rest
is still written. Four inputs only add detail (meta.json, grazing_cells.json, antarctic_sites.json, and
moon_cards.json for the picture): without one the file is still written, and the run says what it lacks.
An older copy of a left-out file stays in place, except a per-area file made for another list of areas,
which is removed. extras.json lists what this run made; the page should read only the files it lists.
Unknown is null in the JSON files and -128 in the byte files; it is never 0.
"""
from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import math
import os
import re
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
T_UNKNOWN = -128                 # the unknown byte of the temperature files
T_LOW, T_HIGH = -127, 127        # a real value is held inside these, so it can never read as unknown
EARTH_KM = 6371.0                # the sphere scripts/check_known_analogs.py measures on
RADIUS_KM = 50.0                 # "near a place": the radius the known-site check uses
MIN_AREAS_TO_NAME_A_REGION = 20  # a region with fewer areas is not named as the clearest
DAYTIME_POINTS = 5.0             # daytime cloud "differs" when it is more than this many points away
MOON_LINE_HOURS = 4.0            # the lunar curve keeps one row in this many hours
MOON_MARK_HOURS = 24             # marks a day apart on the Moon
EARTH_LINE_HOURS = 0.25          # the Earth curve keeps one row in this many hours
EARTH_MARK_HOURS = 1             # marks an hour apart on Earth
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]
NORTH_MONTHS = (6, 7)            # July and August: the season of the northern long windows
SOUTH_MONTHS = (11, 0)           # December and January: the Antarctic rock season
LUNAR_SITE = "malapert"          # the lunar path the picture shows
EARTH_PLACE = "haughton"         # the Earth path the picture shows
MODEL_LABEL = "model-based (Diviner Polar Resource Product)"
WORDING = {True: "Not a little-known place: published space-analog work exists here.",
           False: "We found no published space-analog use here.",
           None: "Whether this place has been used as a space analog was not checked."}
URL = re.compile(r"https?://[^\s`\"\)\]]+")


class ExtrasError(Exception):
    """An input does not say what the page needs; the output it feeds is not written."""


# ---- small helpers ----

def read_json(path: Path, default=None):
    """A JSON file, or the default when it is not there."""
    if not path.exists():
        return default
    with open(path) as handle:
        return json.load(handle)


def write_bytes(path: Path, data: bytes) -> int:
    """Write beside the target and rename, so a reader never sees half a file. Returns the size."""
    side = path.with_name(path.name + ".part")
    side.write_bytes(data)
    os.replace(side, path)
    return len(data)


def json_bytes(value) -> bytes:
    return json.dumps(value, separators=(",", ":"), allow_nan=False, ensure_ascii=False).encode()


def known(value) -> bool:
    return value is not None and not (isinstance(value, float) and math.isnan(value))


def pick(record: dict | None, keys) -> dict | None:
    """The named keys of a record, in the order asked, where it has them."""
    if record is None:
        return None
    return {key: record[key] for key in keys if key in record}


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def modified(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def written_inside(doc) -> str | None:
    """When a pipeline file says it was written, in its own words; None when it does not say."""
    meta = doc.get("meta") if isinstance(doc, dict) else None
    if not isinstance(meta, dict):
        return None
    for key in ("written_utc", "written", "generated"):
        if isinstance(meta.get(key), str):
            return meta[key]
    return None


def median_or_none(values, digits: int = 1):
    values = [v for v in values if known(v)]
    return round(statistics.median(values), digits) if values else None


def km_from(lat: float, lon: float, lats: np.ndarray, lons: np.ndarray) -> np.ndarray:
    """Great-circle distance in km from one point to many, on the sphere the known-site check uses."""
    p1, p2 = math.radians(lat), np.radians(lats)
    dlat, dlon = p2 - p1, np.radians(lons - lon)
    a = np.sin(dlat / 2) ** 2 + math.cos(p1) * np.cos(p2) * np.sin(dlon / 2) ** 2
    return 2 * EARTH_KM * np.arcsin(np.minimum(1.0, np.sqrt(a)))


# ---- the page's areas and sites ----

def areas_of(cells_doc: dict) -> dict:
    """The page's areas in the page's order: ids, centres in degrees, hemisphere, region name, known flag."""
    ids = cells_doc.get("ids")
    if not isinstance(ids, list) or not ids:
        raise ExtrasError("site/data/cells.json has no list of ids")
    index = {}
    for position, area_id in enumerate(ids):
        if area_id in index:
            raise ExtrasError(f"site/data/cells.json lists the area {area_id} twice")
        index[area_id] = position
    units = cells_doc.get("units") or {}
    for key in ("lat", "lon"):
        if "hundredths" not in str(units.get(key, "")):
            raise ExtrasError(f"site/data/cells.json: {key} is expected in hundredths of a degree, it says {units.get(key)!r}")
        if len(cells_doc.get(key) or []) != len(ids):
            raise ExtrasError(f"site/data/cells.json: {key} has not one value for each id")
    lat = [v / 100.0 for v in cells_doc["lat"]]
    lon = [v / 100.0 for v in cells_doc["lon"]]
    letters = cells_doc.get("hemisphere")
    hemisphere = list(letters) if isinstance(letters, str) and len(letters) == len(ids) else ["N" if v > 0 else "S" for v in lat]
    names, rows = cells_doc.get("regions"), cells_doc.get("region")
    region = [names[r] if 0 <= r < len(names) else None for r in rows] if names and rows and len(rows) == len(ids) else None
    flags = cells_doc.get("known")
    return {"ids": list(ids), "index": index, "lat": lat, "lon": lon, "hemisphere": hemisphere, "region": region,
            "known": list(flags) if isinstance(flags, list) and len(flags) == len(ids) else None}


def page_targets(meta_doc: dict | None) -> list[dict] | None:
    """The lunar sites in the page's order (site/data/meta.json), or None when the page has not said."""
    targets = (meta_doc or {}).get("targets")
    if not isinstance(targets, list) or not targets:
        return None
    return [{"id": t["id"], "short": t.get("short")} for t in targets if isinstance(t, dict) and "id" in t]


# ---- temperature ----

def temperature_table(doc: dict, ids: list[str], field: str) -> np.ndarray | None:
    """int8 [areas, 12] of whole degrees C in the order of ids; -128 where the source has no value.

    None when no record of the source carries the field at all. An id the source lacks is an error:
    a shorter table would put every later area on the wrong row.
    """
    cells = doc.get("cells") or {}
    if not any(isinstance(record, dict) and field in record for record in cells.values()):
        return None
    missing = [area_id for area_id in ids if area_id not in cells]
    if missing:
        raise ExtrasError(f"temperature_cells.json lacks {len(missing)} of the page's {len(ids)} areas, "
                          f"for example {', '.join(missing[:5])}")
    table = np.full((len(ids), 12), np.nan)
    for row, area_id in enumerate(ids):
        values = cells[area_id].get(field)
        if values is None:
            continue
        if len(values) != 12:
            raise ExtrasError(f"temperature_cells.json: {field} of {area_id} has {len(values)} months where 12 are expected")
        table[row] = [v if known(v) else np.nan for v in values]
    unknown = np.isnan(table)
    filled = np.where(unknown, 0.0, table)
    whole = np.where(filled >= 0, np.floor(filled + 0.5), np.ceil(filled - 0.5))      # halves away from zero
    out = np.clip(whole, T_LOW, T_HIGH).astype(np.int8)
    out[unknown] = T_UNKNOWN
    return out


def temperature_notes(doc: dict, areas: dict) -> dict:
    """What the page prints beside a temperature: the source, its limits, the lunar figure, the grid heights."""
    meta = doc.get("meta") or {}
    cells = doc.get("cells") or {}
    heights = []
    for area_id in areas["ids"]:
        height = (cells.get(area_id) or {}).get("grid_elev_m")
        heights.append(int(round(height)) if known(height) else None)
    medians = {}
    for side, key in (("north", "north_cells"), ("south", "south_cells")):
        block = (meta.get("counts") or {}).get(key)
        if not isinstance(block, dict):
            medians[side] = None
            continue
        medians[side] = {"areas": block.get("cells")}
        for month, fields in block.items():
            if isinstance(fields, dict):
                # the monthly "max" and "min" of the source are extremes of many years, not a day's high and low
                medians[side][month] = {field: fields[field] for field in ("t2m_c", "ts_c") if field in fields}
    places = []
    for place in ((meta.get("named_places") or {}).get("places") or []):
        by_target = {}
        for target, rows in (place.get("best_bins_by_target") or {}).items():
            by_target[target] = [pick(row, ("bin", "dates", "hours", "ten_day_mean_of_daily_series")) for row in rows]
        places.append({"name": place.get("name"), "cell": place.get("cell"), "area": areas["index"].get(place.get("cell")),
                       "lat": place.get("lat"), "lon": place.get("lon"), "grid_elev_m": place.get("grid_elev_m"),
                       "best_bins_by_target": by_target,
                       "best_bins_any_target": [pick(row, ("bin", "dates", "ten_day_mean_of_daily_series"))
                                                for row in (place.get("best_bins_any_target") or [])]})
    return {
        "source": meta.get("source"), "period": meta.get("period"),
        "years_the_values_fit": (meta.get("years_fit") or {}).get("years_the_values_fit"),
        "grid_deg": meta.get("grid_deg"), "grid_deg_order": meta.get("grid_deg_order"),
        "what_it_is": meta.get("what_it_is"), "what_it_is_not": meta.get("what_it_is_not"),
        "fields": pick(meta.get("fields"), ("t2m_c", "ts_c")),
        "by_bin_rule": meta.get("by_bin_rule"),
        "medians": medians,
        "lunar_comparison": meta.get("lunar_comparison"),
        "named_places": places,
        "named_places_what": "ten_day_mean_of_daily_series: mean air temperature (t2m_c), mean daily maximum and minimum "
                             "(t2m_daily_max_c, t2m_daily_min_c) and surface temperature (ts_c) of the ten-day period, "
                             "from the daily series of the same grid point; degrees C",
        "grid_height_m": heights,
        "grid_height_what": "mean height in metres of the model's grid box for each area, in the page's area order; null "
                            "where the service named none. A box far above the area reads too cold.",
    }


# ---- the lunar cards ----

def _short_name(official: str, page_short: str | None) -> str:
    """The page's short name in the official spelling: 'Connecting ridge' becomes 'Connecting Ridge'."""
    if page_short and official.lower().startswith(page_short.lower()):
        return official[:len(page_short)]
    return official


def _why(card: dict) -> dict:
    check = card.get("why_check") or {}
    confirmed = check.get("confirmed")
    proposed = check.get("proposed_wording")
    if confirmed is False and proposed:
        text, sourced = proposed, True
    else:
        text, sourced = card.get("why_stored"), confirmed is True
    return {"text": text, "confirmed": confirmed, "sourced": sourced,
            "sources": list(check.get("proposed_wording_sources") or []), "note": check.get("note")}


def _card(card: dict, page_short: str | None) -> dict:
    diviner = card.get("diviner") or {}
    picture = card.get("picture") or {}
    return {
        "id": card["id"],
        "official_name": card.get("official_name"),
        "short_name": _short_name(card.get("official_name") or "", page_short) or None,
        "name_in_project": card.get("name_in_project"),
        "name_note": card.get("name_note"),
        "nasa_list": card.get("nasa_list"),
        "why": _why(card),
        "has_model": bool(card.get("has_model", card.get("pgda_model") is not None)),
        "model_note": card.get("model_note"),
        "position": card.get("position"),
        "pgda_model": (pick(card.get("pgda_model"), ("site", "pgda_name", "page", "what", "citation"))
                       if card.get("pgda_model") else None),
        "centre": card.get("centre"),
        "extent_km": card.get("extent_km"),
        "box_km": card.get("box_km"),
        "sun_ceiling": card.get("sun_ceiling"),
        "shadow_of_1m_object_at_ceiling_m": card.get("shadow_of_1m_object_at_ceiling_m"),
        "shadow_how": card.get("shadow_how"),
        "lit": pick(card.get("lit"), ("mean_share", "best_point_share", "how", "kind", "source")),
        "permanent_shadow": pick(card.get("permanent_shadow"), ("share", "how", "kind", "source")),
        "diviner": {"label": MODEL_LABEL,
                    **pick(diviner, ("model_based", "annual_mean_temp_2cm_K", "annual_max_temp_surface_K",
                                     "annual_mean_temp_2cm_C", "annual_max_temp_surface_C", "ice", "kind", "how", "source",
                                     "citation"))},
        "picture": pick(picture, ("page", "title", "note", "credit", "credit_source", "citation", "alternative",
                                  "sun_heights_of_images")),
        "earth_cannot_match": card.get("earth_cannot_match"),
    }


def moon_cards(doc: dict, targets: list[dict] | None) -> dict:
    """The lunar cards trimmed to what a card shows, in the page's site order (the file's own without one)."""
    meta = doc.get("meta") or {}
    by_id = {card["id"]: card for card in doc.get("cards") or []}
    if targets is None:
        order = [{"id": card_id, "short": None} for card_id in by_id]
    else:
        order = targets
        missing = [t["id"] for t in targets if t["id"] not in by_id]
        if missing:
            raise ExtrasError(f"moon_cards.json has no card for the page's site {', '.join(missing)}")
    diviner = meta.get("diviner") or {}
    return {
        "source": "data/derived/moon_cards.json", "source_written": written_inside(doc),
        "pages_read_on": meta.get("pages_read_on"),
        "unknown": "null: no figure, no picture or not on that list; never 0",
        "order": "the page's site order (site/data/meta.json targets)" if targets is not None else "the order of moon_cards.json",
        "lists": meta.get("lists"),
        "diviner": {"label": MODEL_LABEL,
                    **pick(diviner, ("product", "folder", "model_based", "columns_used", "special_value",
                                     "undocumented_value", "mesh", "not_checked"))},
        "picture_credit": meta.get("picture_credit"),
        "units": meta.get("units"),
        "cards": [_card(by_id[t["id"]], t.get("short")) for t in order],
    }


# ---- the Sun-path picture ----

def _nearest_rows(times: list[float], every: float) -> list[int]:
    """Rows nearest to the first time plus whole multiples of `every`, where one lies within half a step."""
    if len(times) < 2:
        return list(range(len(times)))
    tolerance = statistics.median(b - a for a, b in zip(times, times[1:])) / 2 + 1e-6
    rows, k = [], 0
    while times[0] + k * every <= times[-1] + tolerance:
        want = times[0] + k * every
        at = bisect.bisect_left(times, want)
        best = min((i for i in (at - 1, at) if 0 <= i < len(times)), key=lambda i: abs(times[i] - want))
        if abs(times[best] - want) <= tolerance and (not rows or rows[-1] != best):
            rows.append(best)
        k += 1
    return rows


def _thinned(times: list[float], line_every: float, always: list[int]) -> list[int]:
    """Rows for the drawn line: one in line_every, the first, the last, and the rows that must stay."""
    step = 1
    if len(times) > 1:
        sampling = statistics.median(b - a for a, b in zip(times, times[1:]))
        step = max(1, int(round(line_every / sampling))) if sampling > 0 else 1
    keep = set(range(0, len(times), step)) | {0, len(times) - 1} | set(always)
    return sorted(keep)


def _series(path: dict, time_key: str, rows: list[int]) -> dict:
    return {key: [path[key][i] for i in rows] for key in (time_key, "azimuth_deg", "elevation_deg")}


def _curve(path: dict | None, time_key: str, line_every: float, mark_every: float) -> tuple[dict | None, dict | None]:
    """The thinned line and the time marks of one path, every value a row of the source."""
    if not path or not path.get(time_key):
        return None, None
    times, elevation = path[time_key], path["elevation_deg"]
    marks = _nearest_rows(times, mark_every)
    extremes = [max(range(len(elevation)), key=elevation.__getitem__), min(range(len(elevation)), key=elevation.__getitem__)]
    rows = _thinned(times, line_every, marks + extremes)
    line = _series(path, time_key, rows)
    line["rows_in_source"] = len(times)
    marked = {"every_hours": mark_every, **_series(path, time_key, marks)}
    return line, marked


def _compass(azimuth: float) -> str:
    return ["north", "east", "south", "west"][int(((azimuth % 360.0) + 45.0) // 90.0) % 4]


def _hours_minutes(minutes: float) -> str:
    hours, rest = divmod(int(round(minutes)), 60)
    return f"{hours} h {rest:02d} min" if hours else f"{rest} min"


def _say(template: str, **values) -> str | None:
    """The sentence, or None when a figure it needs is unknown (a sentence never prints 'None')."""
    return None if any(v is None for v in values.values()) else template.format(**values)


def _sentences(*candidates) -> list[str]:
    return [s for s in candidates if s]


def _picture_words(moon: dict | None, earth: dict | None, source_path: dict | None) -> tuple[list[str], list[dict]]:
    """What the picture shows and how it can mislead, as short sentences with the file's own figures."""
    m, e = moon or {}, earth or {}
    solar = (source_path or {}).get("solar_time_h") or []
    elevation = (source_path or {}).get("elevation_deg") or []
    azimuth = (source_path or {}).get("azimuth_deg") or []
    lowest_at = min(range(len(elevation)), key=elevation.__getitem__) if elevation else None
    when = ""
    if lowest_at is not None and solar:
        hour = solar[lowest_at] % 24.0
        when = ", around midnight" if min(hour, 24.0 - hour) <= 3.0 else (", around noon" if abs(hour - 12.0) <= 3.0 else "")
    hidden = None
    if e.get("minutes_in_band") is not None and e.get("minutes_above_terrain") is not None:
        hidden = e["minutes_in_band"] - e["minutes_above_terrain"]
    shows = _sentences(
        _say("At {name} the Sun takes {days:.1f} days to go once round the horizon.", name=m.get("name"), days=m.get("mean_trip_days")),
        _say("In the trip drawn, the one with the highest Sun of {year}, its centre never climbs above {top:.2f} degrees.",
             year=m.get("year"), top=m.get("year_max_elevation_deg")),
        _say("It stays above a level horizon for {days:.1f} of those days.", days=m.get("path_days_above_level_horizon")),
        _say("At {name} on {date} the Sun goes round in one day.", name=e.get("name"), date=e.get("date")),
        _say("It is inside the same band for {time} that day{when}.",
             time=None if e.get("minutes_in_band") is None else _hours_minutes(e["minutes_in_band"]), when=when),
        None if hidden is None else ("The ground drawn here does not hide it in those minutes." if hidden <= 0
                                     else f"The ground drawn here hides it for {hidden} of those minutes."),
        _say("Then it climbs to {top:.0f} degrees at noon, far above the band.", top=e.get("day_max_elevation_deg")),
    )
    turn = (m.get("direction") or "").split(" ")[0] or None
    earth_turn = None
    if len(azimuth) > 2:
        steps = [((b - a + 180.0) % 360.0) - 180.0 for a, b in zip(azimuth, azimuth[1:])]
        earth_turn = "clockwise" if statistics.median(steps) > 0 else "anticlockwise"
    step = elevation[-1] - elevation[0] if len(elevation) > 1 else None
    horizon = e.get("terrain_horizon") or {}
    high = [v for v in (horizon.get("cell_p90_deg") or []) if known(v)]
    cautions = [
        {"key": "best_cases", "main": True, "sentences": _sentences(
            "Both curves are best cases.",
            _say("The Moon's trip holds the highest Sun of {year}; in lunar winter the Sun there sinks to {low:.1f} degrees.",
                 year=m.get("year"), low=m.get("year_min_elevation_deg")),
            _say("The Earth day is the middle of the place's best ten-day period, {label}.", label=e.get("best_bin_label")))},
        {"key": "smooth_moon", "main": True, "sentences": _sentences(
            "The grey ground belongs to the Earth place only." if earth else None,
            "The Moon's curve assumes a smooth Moon; real lunar hills hide and uncover the Sun.")},
        {"key": "height_only", "main": True, "sentences": _sentences(
            _say("The upper limit of the band, {ceiling:.2f} degrees, is the ceiling from our formula; the highest Sun found "
                 "for {year} is {top:.2f} degrees.", ceiling=m.get("ceiling_deg"), year=m.get("year"), top=m.get("year_max_elevation_deg")),
            "The picture matches the Sun's height only, not brightness, sky light or how dark the shadows are.")},
        {"key": "times", "main": False, "sentences": _sentences(
            "Equal lengths of curve are not equal times.",
            "Dots on the Moon's curve are one day apart; dots on the Earth's curve are one hour apart." if earth else None,
            _say("The Earth's Sun crosses the band about {ratio:.1f} times faster.", ratio=m.get("mean_trip_days")) if earth else None)},
        {"key": "directions", "main": False, "sentences": _sentences(
            _say("The Sun moves {moon} at the lunar site and {earth} at the Earth place.", moon=turn, earth=earth_turn),
            _say("The Moon's Sun is highest in the {high}; the Earth's Sun is lowest in the {low}.",
                 high=None if m.get("year_max_azimuth_deg") is None else _compass(m["year_max_azimuth_deg"]),
                 low=None if lowest_at is None or not azimuth else _compass(azimuth[lowest_at])))},
        {"key": "off_chart", "main": False, "sentences": _sentences(
            _say("Most of the Earth day is off the chart: the Sun climbs to {top:.0f} degrees at noon.", top=e.get("day_max_elevation_deg")))},
        {"key": "step", "main": False, "sentences": _sentences(
            None if step is None or abs(step) < 0.05 else
            f"The small step in the Earth curve is real: the Sun ends the day {abs(step):.2f} degrees "
            f"{'lower' if step < 0 else 'higher'} than it began.")},
        {"key": "one_view", "main": False, "sentences": _sentences(
            _say("The Earth ground is one view, from the middle of the area, {eye:g} m above the ground.", eye=horizon.get("eye_m")),
            None if not high else f"A tenth of the area's points see ground above {min(high):.1f} to {max(high):.1f} degrees, "
                                  "depending on direction, which would hide a low Sun.")},
        {"key": "centre", "main": False, "sentences": _sentences(
            "The curves follow the Sun's centre, not its upper edge.",
            "The Earth curve includes the bending of light by the air; the Moon has no air." if earth else None)},
    ]
    return shows, [c for c in cautions if c["sentences"]]


def sun_paths(doc: dict, moon_doc: dict | None, areas: dict) -> dict:
    """The lunar path and the Earth path of the picture, thinned, with time marks, band, minutes and cautions."""
    meta = doc.get("meta") or {}
    problems = []
    lunar = next((s for s in doc.get("lunar_sites") or [] if s.get("id") == LUNAR_SITE), None)
    place = next((p for p in doc.get("earth_places") or [] if p.get("id") == EARTH_PLACE), None)
    official = {c["id"]: c.get("official_name") for c in (moon_doc or {}).get("cards") or []}
    moon = None
    if lunar is None:
        problems.append(f"sunpath_demo.json has no lunar site '{LUNAR_SITE}'")
    else:
        path = lunar.get("path") or {}
        line, marks = _curve(path, "hours_since_start", MOON_LINE_HOURS, MOON_MARK_HOURS)
        moon = {key: value for key, value in lunar.items() if key != "path"}
        moon["name"] = official.get(lunar["id"]) or lunar.get("name")
        moon.update({"start_utc": path.get("start_utc"), "end_utc": path.get("end_utc"), "path_complete": path.get("complete"),
                     "path": line, "marks": marks, "assumes": (meta.get("lunar_sites") or {}).get("not_in_these_numbers")})
    earth = None
    if place is None:
        problems.append(f"sunpath_demo.json has no Earth place '{EARTH_PLACE}'")
    else:
        line, marks = _curve(place.get("path"), "solar_time_h", EARTH_LINE_HOURS, EARTH_MARK_HOURS)
        earth = {key: value for key, value in place.items() if key not in ("path", "terrain_horizon")}
        earth.update({"area": areas["index"].get(place.get("cell_id")), "path": line, "marks": marks,
                      "elevation_is": "apparent: the bending of light by the air is included",
                      "terrain_horizon": pick(place.get("terrain_horizon"),
                                              ("sector_centres_deg", "centre_deg", "cell_median_deg", "cell_p10_deg",
                                               "cell_p90_deg", "north_deg", "south_deg", "eye_m", "reach_km", "half_km", "pixel_m"))})
    shows, cautions = _picture_words(moon, earth, (place or {}).get("path"))
    band = (earth or {}).get("band_deg") or (None if moon is None or moon.get("ceiling_deg") is None else [0.0, moon["ceiling_deg"]])
    also = {"lunar_sites": [{k: v for k, v in s.items() if k != "path"} for s in doc.get("lunar_sites") or [] if s.get("id") != LUNAR_SITE],
            "earth_places": [{k: v for k, v in p.items() if k not in ("path", "terrain_horizon")}
                             for p in doc.get("earth_places") or [] if p.get("id") != EARTH_PLACE]}
    return {
        "source": "data/derived/sunpath_demo.json", "source_written": written_inside(doc),
        "caption": meta.get("caption_for_any_drawing"), "angles": meta.get("angles"),
        "band_deg": band,
        "axis_centre": None if place is None or place.get("cell_lat") is None else ("north" if place["cell_lat"] >= 0 else "south"),
        "axis_why": "centre the sideways axis on this direction, so the Earth's midnight Sun and the Moon's highest Sun sit in the middle",
        "moon": moon, "earth": earth,
        "shows": shows, "cautions": cautions,
        "also_in_the_source_without_a_path_here": also,
        "problems": problems,
    }


# ---- how sure are we ----

LOWER_LATITUDE_DROPPED = ("best_day", "profile_hours_a_year_in_band", "profile_hours_in_spells_of_2h")


SNOW_CHECK_STATS = ("stations", "n", "mean_bias", "median_bias", "mean_abs_difference", "median_of_station_means",
                    "mean_bias_95_interval")


def snow_station_check(doc: dict | None) -> dict | None:
    """The station check of the snow maps: the overall figures, the same by part of the year, and the calibration rows.

    The per-station rows stay in the pipeline's file. Anything the file does not say is null, never 0.
    """
    if doc is None:
        return None
    if not isinstance(doc, dict):
        raise ExtrasError("snow_validation_many.json is not a record")
    method = doc.get("method") or {}
    selection = doc.get("selection") or {}
    periods = {}
    for key, block in (doc.get("periods") or {}).items():
        periods[key] = {**(pick(block, ("what", "days", "min_lat", "stations_in_group")) or {}),
                        "with_stale_flag_rule": pick(block.get("with_stale_flag_rule"), SNOW_CHECK_STATS),
                        "as_mapped": pick(block.get("as_mapped"), SNOW_CHECK_STATS)}
    calibration = doc.get("calibration")
    return {
        "source": "data/derived/snow_validation_many.json",
        "what": "satellite snow-free odds against the share of days on which weather stations reported no snow on the ground, "
                "per station and ten-day period; with_stale_flag_rule is the odds the project uses",
        "method": pick(method, ("source", "period", "min_lat", "bias", "n", "stations", "trust_rule")),
        "selection": pick(selection, ("examined", "kept")),
        "overall": pick(doc.get("overall"), SNOW_CHECK_STATS),
        "periods": periods or None,
        "calibration": ([pick(row, ("ims_low", "ims_high", "n_station_bins", "mean_ims", "mean_station_snow_free"))
                         for row in calibration] if isinstance(calibration, list) else None),
    }


def validation(doc: dict, areas: dict, snow_check: dict | None = None) -> dict:
    """The validation extras as the page needs them: same places, same numbers, less bulk, plus the census flags."""
    meta = doc.get("meta") or {}
    lower = doc.get("lower_latitude_sites") or {}
    funnel = doc.get("latitude_against_full_method") or {}
    known_sites = doc.get("known_sites") or {}
    sensitivity = doc.get("sensitivity") or {}
    sites = []
    for site in lower.get("sites") or []:
        sites.append({**{k: v for k, v in site.items() if k != "targets"},
                      "targets": {target: {k: v for k, v in values.items() if k not in LOWER_LATITUDE_DROPPED}
                                  for target, values in (site.get("targets") or {}).items()}})
    lists = {}
    for name, rows in (known_sites.get("sites") or {}).items():
        lists[name] = [{**{k: v for k, v in row.items() if k != "source"}, "area": areas["index"].get(row.get("cell"))}
                       for row in rows]
    ranked = known_sites.get("ranked_population") or {}
    return {
        "source": "data/derived/validation_extras.json",
        "source_written": meta.get("written_utc") or meta.get("written"),
        "unknown": "null means unknown or not computed; never 0",
        "flags": {
            "terrain_step_is_a_census": funnel.get("with_a_horizon_is_a_census"),
            "horizon_coverage": funnel.get("horizon_coverage"),
            "measured_cells": funnel.get("measured_cells"),
            "measured_cells_with_a_horizon": funnel.get("measured_cells_with_a_horizon"),
            "ranked_is_a_census": {side: (ranked.get(side) or {}).get("ranked_is_a_census") for side in ("N", "S")},
            "cloud": funnel.get("cloud"),
            "what": "while terrain_step_is_a_census is not true, word the terrain and cloud steps as 'among the areas with a "
                    "terrain horizon so far' and read them from measured_cells_with_a_horizon; the first two steps come from "
                    "all_measured_cells",
        },
        "meta": pick(meta, ("written", "written_utc", "targets", "threshold_h", "long_rule", "stretch_min_h", "step_minutes",
                            "winter_half", "summer_half", "version_3_fields", "input_files_written",
                            "an_input_changed_during_the_run", "unknown", "ai_note")),
        "lower_latitude_sites": {**{k: v for k, v in lower.items() if k != "sites"}, "sites": sites},
        "latitude_against_full_method": funnel,
        "known_sites": {**{k: v for k, v in known_sites.items() if k != "sites"}, "sites": lists},
        "sensitivity": {**{k: v for k, v in sensitivity.items() if k not in ("targets", "checks")},
                        "targets": {target: pick(block, ("limit_deg", "table", "moves_more_than_a_quarter"))
                                    for target, block in (sensitivity.get("targets") or {}).items()}},
        "snow_station_check": snow_station_check(snow_check),
        "headlines": doc.get("headlines"),
        "notes": [
            "The source says 'cells' and uses the project's working site names; the page says 'areas' and takes names from moon.json.",
            "The headline sentences are copied as written and many are longer than 25 words: reword before printing.",
            "Never show a count 'after cloud' alone: show after_cloud.median_share_of_hours_kept and still_at_least_h with it.",
            "The lower-latitude figures are for a flat horizon at one latitude, not a measurement of another team's site.",
            "In the known-site rows a null verdict or percentile means unknown: draw it as unknown, never as 0.",
        ],
    }


# ---- sources ----

def _plain(text: str) -> str:
    """Markdown marks off, white space to single spaces."""
    return " ".join(text.replace("`", "").replace("**", "").split())


def _split_row(line: str) -> list[str]:
    """The cells of one table row. A bar inside backticks or after a backslash is part of the cell."""
    cells, current, in_code, i = [], [], False, 0
    while i < len(line):
        char = line[i]
        if char == "\\" and i + 1 < len(line) and line[i + 1] == "|":
            current.append("|")
            i += 2
            continue
        if char == "`":
            in_code = not in_code
        if char == "|" and not in_code:
            cells.append("".join(current))
            current = []
        else:
            current.append(char)
        i += 1
    cells.append("".join(current))
    if cells and not cells[0].strip():
        cells = cells[1:]
    if cells and not cells[-1].strip():
        cells = cells[:-1]
    return [cell.strip() for cell in cells]


def _links(raw: str) -> list[dict]:
    """Every address in a piece of Markdown: the address, whether it sat in backticks, whether it is a pattern."""
    found = []
    for match in URL.finditer(raw):
        address = match.group(0).rstrip(".,;:")
        found.append({"url": address, "in_code": raw.count("`", 0, match.start()) % 2 == 1,
                      "pattern": any(char in address for char in "<>{}")})
    return found


def _sections(text: str) -> dict[int, list[str]]:
    sections, current = {}, None
    for line in text.split("\n"):
        heading = re.match(r"^## (\d+)\.", line)
        if heading:
            current = int(heading.group(1))
            sections[current] = []
        elif current is not None:
            sections[current].append(line)
    return sections


def _bullets(lines: list[str]) -> list[str]:
    """Bullet items of a run of lines, each joined over its continuation lines."""
    items, current = [], None
    for line in lines:
        if line.startswith("- "):
            if current is not None:
                items.append(current)
            current = line[2:].strip()
        elif current is not None and line.strip():
            current += " " + line.strip()
        elif current is not None:
            items.append(current)
            current = None
    if current is not None:
        items.append(current)
    return items


def _credits(lines: list[str]) -> list[dict]:
    """The credit lines of section 3: every '- **X. Title:** text' bullet (X is one or two capitals), each whole."""
    credits = []
    for item in _bullets(lines):
        match = re.match(r"^\*\*([A-Z]{1,2})\. (.+?)([:.])\*\*\s*(.*)$", item, re.S)
        if not match:
            continue   # a bullet of section 3 that is not a credit line
        text = _plain(match.group(4))
        credits.append({"ref": match.group(1), "title": _plain(match.group(2)), "mark": match.group(3), "text": text,
                        "quotes": re.findall(r'"([^"]+)"', text), "links": [l["url"] for l in _links(match.group(4)) if not l["pattern"]]})
    return credits


def _field_items(bullets: list[str]) -> list[dict]:
    items = []
    for raw in bullets:
        text = _plain(raw)
        links = [l["url"] for l in _links(raw) if not l["pattern"]]
        link = links[0] if links else None
        name, note = text, None
        if link and link in text:
            before, after = text.split(link, 1)
            name = before.strip().rstrip(":").strip()
            note = after.strip() or None
        items.append({"name": name, "link": link, "note": note, "text": text,
                      "only_if_the_page_links_to_it": "only if" in text.lower()})
    return items


def parse_sources(text: str) -> dict:
    """data/SOURCES.md as records: the sources table, the credit lines, the licence line, the form fields."""
    sections = _sections(text)
    problems = []
    credits = _credits(sections.get(3, []))
    by_ref = {c["ref"]: c for c in credits}
    if not credits:
        problems.append("no credit lines found in section 3")

    # the table of section 1
    table = [line for line in sections.get(1, []) if line.startswith("|")]
    sources = []
    if len(table) < 3:
        problems.append("no table of sources found in section 1")
    else:
        header = [_plain(cell).lower() for cell in _split_row(table[0])]
        wanted = {"n": "#", "name": "full name", "provider": "provider", "group": "group", "used_for": "what we use",
                  "link": "link", "licence": "licence", "credit": "credit", "raw": "raw files", "derived": "derived products"}
        column = {}
        for key, words in wanted.items():
            hits = [i for i, title in enumerate(header) if title.startswith(words)]
            if not hits:
                raise ExtrasError(f"data/SOURCES.md, table of sources: no column that begins '{words}'")
            column[key] = hits[0]
        for line in table[2:]:
            cells = _split_row(line)
            if cells and not _plain(cells[0]).isdigit():
                continue   # the heading rows of a second table (section 1b)
            if len(cells) != len(header):
                raise ExtrasError(f"data/SOURCES.md, table of sources, row {cells[0] if cells else '?'}: "
                                  f"{len(cells)} cells where {len(header)} are expected")
            raw = {key: cells[i] for key, i in column.items()}
            group_text = _plain(raw["group"])
            note = re.search(r"\((.+)\)", group_text)
            group = "NASA" if group_text.lower().startswith("nasa") else ("partner agency" if group_text.lower().startswith("partner") else "other")
            fetch, licence = _links(raw["link"]), _links(raw["licence"])
            candidates = ([l["url"] for l in fetch if not l["in_code"] and not l["pattern"]]
                          + [l["url"] for l in licence if not l["pattern"]]
                          + [l["url"] for l in fetch if l["in_code"] and not l["pattern"]])
            credit_cell = _plain(raw["credit"])
            ref = re.search(r"\bCredit ([A-Z]{1,2})\b", credit_cell)
            credit = None
            if ref:
                credit = (by_ref.get(ref.group(1)) or {}).get("text")
                if credit is None:
                    problems.append(f"row {_plain(raw['n'])} names Credit {ref.group(1)}, which section 3 does not have")
            elif credit_cell.lower().startswith("cite as:"):
                credit = credit_cell[len("cite as:"):].strip()
            number = _plain(raw["n"])
            sources.append({
                "n": int(number) if number.isdigit() else number,
                "name": _plain(raw["name"]), "provider": _plain(raw["provider"]),
                "group": group, "group_note": note.group(1) if note else None,
                "used_for": _plain(raw["used_for"]),
                "link": candidates[0] if candidates else None,
                "fetch_from": _plain(raw["link"]),
                "licence": _plain(raw["licence"]),
                "licence_links": [l["url"] for l in licence if not l["pattern"]],
                "credit_ref": ref.group(1) if ref else None, "credit": credit, "credit_note": credit_cell,
                "raw_files_public": _plain(raw["raw"]), "derived_public": _plain(raw["derived"]),
            })

    # the licence line of section 3
    licence_line = None
    joined = "\n".join(sections.get(3, []))
    match = re.search(r"One line for the page footer[^\"]*\"(.+?)\"\s*(?:\n\s*\n|$)", joined, re.S)
    if match:
        licence_line = _plain(match.group(1))
    else:
        problems.append("no licence line ('One line for the page footer ...') found in section 3")

    # the form fields of section 4
    fields = {"nasa_data": None, "partner_data": None, "partner_data_note": None, "other_open_data": None}
    blocks, current = [], []
    for line in sections.get(4, []):
        if line.strip():
            current.append(line)
        elif current:
            blocks.append(current)
            current = []
    if current:
        blocks.append(current)
    for block in blocks:
        label = re.match(r"^\*\*(.+?)\*\*", block[0])
        if not label:
            continue
        title = label.group(1).lower()
        first_bullet = next((i for i, line in enumerate(block) if line.startswith("- ")), len(block))
        lead = _plain(" ".join(block[:first_bullet]))
        if title.startswith("nasa data"):
            fields["nasa_data"] = _field_items(_bullets(block[first_bullet:]))
        elif "partner data" in title:
            fields["partner_data"] = _field_items(_bullets(block[first_bullet:]))
            fields["partner_data_note"] = lead
        elif title.startswith("other open data"):
            fields["other_open_data"] = _plain(" ".join(block[1:])) or None
            fields["other_open_data_note"] = _plain(block[0])
    for key in ("nasa_data", "partner_data", "other_open_data"):
        if not fields[key]:
            problems.append(f"section 4: nothing found for {key}")

    quotes = [quote for credit in credits for quote in credit["quotes"]]
    return {
        "source": "data/SOURCES.md",
        "sources": sources,
        "credits": credits,
        "credits_what": "the credit lines of section 3, each whole and in the file's order; print as written. "
                        "'quotes' are the passages the file puts in quotation marks.",
        "notices": {
            "copernicus_dem": next((q for q in quotes if q.startswith("produced using")), None),
            "copernicus_liability": next((q for q in quotes if q.startswith("The organisations in charge")), None),
            "comnap": next((c["text"] for c in credits if "COMNAP" in c["title"]), None),
            "worldcover": next((c["text"] for c in credits if "WorldCover" in c["title"] or "WorldCover" in c["text"]), None),
        },
        "licence_line": licence_line,
        **fields,
        "problems": problems,
    }


# ---- places ----

def _near(lat: float, lon: float, areas: dict) -> tuple[np.ndarray, np.ndarray]:
    distance = km_from(lat, lon, np.asarray(areas["lat"]), np.asarray(areas["lon"]))
    return np.flatnonzero(distance <= RADIUS_KM), distance


def _point(point: dict) -> dict:
    return {"lat": point.get("lat"), "lon": point.get("lon"),
            "station": point.get("nearest_station") or point.get("nearest_comnap_facility"),
            "year_round_station": point.get("nearest_year_round_comnap_station"),
            "airfield": point.get("nearest_airfield"),
            "airfield_note": point.get("nearest_airfield_note"),
            "nearest_known_site_of_ours": point.get("nearest_known_site_of_ours"),
            "nearest_published_site_missing_from_ours": point.get("nearest_published_site_missing_from_ours")}


def places(check: dict, antarctic: list | None, areas: dict) -> dict:
    """The places that head the lists, the page's areas near each, and the areas not to call little known."""
    ids = areas["ids"]
    out_places, area_place, comnap_credit = [], {}, None
    for number, place in enumerate(check.get("top_places") or []):
        points = [_point(p) for p in place.get("points") or []]
        nearest: dict[int, tuple[int, float]] = {}
        for which, point in enumerate(points):
            if point["lat"] is None or point["lon"] is None:
                continue
            rows, distance = _near(point["lat"], point["lon"], areas)
            for row in rows.tolist():
                if row not in nearest or distance[row] < nearest[row][1]:
                    nearest[row] = (which, float(distance[row]))
            for key in ("station", "year_round_station", "airfield"):
                comnap_credit = comnap_credit or (point[key] or {}).get("from")
        near = [{"id": ids[row], "index": row, "point": nearest[row][0], "km_to_point": round(nearest[row][1], 1)}
                for row in sorted(nearest)]
        for entry in near:
            key = str(entry["index"])
            if key not in area_place:
                area_place[key] = [number, entry["point"]]
        evidence = place.get("evidence") or []
        counted = place.get("cells_within_50_km") or {}
        found = place.get("analog_use_found")
        out_places.append({
            "name": place.get("name"), "analog_use_found": found,
            "wording": WORDING[found if isinstance(found, bool) else None],
            "detail": place.get("hosts_analog_or_polar_field_work"),
            "not_checked": place.get("not_checked"),
            "evidence": evidence,
            "evidence_levels": list(dict.fromkeys(e.get("level") for e in evidence if e.get("level"))),
            "links": list(dict.fromkeys(e.get("url") for e in evidence if e.get("url"))),
            "points": points,
            "areas": near,
            "cells_in_the_check_file": counted.get("cells"),
            "flagged_little_known_in_the_check_file": counted.get("flagged_little_known"),
        })

    # areas the page must not call little known: near a place where published analog work was found
    because = []
    for place, original in zip(out_places, check.get("top_places") or []):
        if place["analog_use_found"] is True:
            rows = [a["index"] for a in place["areas"]]
            point = place["points"][0] if place["points"] else {}
            because.append({"name": place["name"], "kind": "top place with published analog work",
                            "why": place["detail"], "source_url": place["links"][0] if place["links"] else None,
                            "evidence": place["evidence_levels"][0] if place["evidence_levels"] else None,
                            "lat": point.get("lat"), "lon": point.get("lon"), "areas": rows, "ids": [ids[r] for r in rows]})
    for key, kind in (("also_published_elsewhere_and_missing", "published analog site found while checking"),
                      ("missing_from_our_list", "catalogue site missing from our list")):
        for site in check.get(key) or []:
            if site.get("lat") is None or site.get("lon") is None:
                continue
            rows = _near(site["lat"], site["lon"], areas)[0].tolist()
            because.append({"name": site.get("name"), "kind": kind, "why": site.get("analog_for"),
                            "source_url": site.get("source_url"), "evidence": site.get("evidence") or site.get("listed_in"),
                            "lat": site["lat"], "lon": site["lon"], "areas": rows, "ids": [ids[r] for r in rows]})
    union = sorted({row for entry in because for row in entry["areas"]})
    marked = None if areas.get("known") is None else sum(1 for row in union if areas["known"][row] == -1)

    sites = None
    if antarctic is not None:
        suggested = {change.get("site"): change for change in check.get("antarctic_sites_suggested_changes") or []}
        sites = []
        for site in antarctic:
            rows = [] if site.get("lat") is None else _near(site["lat"], site["lon"], areas)[0].tolist()
            sites.append({**pick(site, ("name", "lat", "lon", "nearest_station", "nearest_station_km",
                                        "nearest_station_seasonality", "nearest_year_round_station",
                                        "nearest_year_round_station_km", "station_year_round", "winter_snow_evidence",
                                        "existing_analog_use")),
                          "suggested_change": pick(suggested.get(site.get("name")), ("suggest", "effect", "source_url", "evidence")),
                          "areas": rows, "ids": [ids[r] for r in rows]})
    meta = check.get("meta") or {}
    return {
        "source": "data/reference/known_analogs_check.json", "source_written": written_inside(check),
        "radius_km": RADIUS_KM,
        "radius_what": "an area is near a place when its centre lies within this distance of one of the place's points "
                       "(great circle, sphere of 6371 km)",
        "wording_what": "analog_use_found false means one search found no published space-analog use; it does not mean never studied",
        "evidence_levels": meta.get("evidence_levels"),
        "not_checked": meta.get("not_checked"),
        "places": out_places,
        "area_place": area_place,
        "area_place_what": "area index (as text) to [index in places, index of the nearest of that place's points]",
        "not_little_known": {"areas": union, "ids": [ids[r] for r in union],
                             "marked_little_known_on_the_page_now": marked, "because": because},
        "antarctic_sites": sites,
        "comnap_credit": comnap_credit,
        "comnap_what": "print this beside any Antarctic station name or distance",
    }


# ---- cloud by region ----

def _season(rows: list[int], regions: list, cloud: dict, ids: list[str], months: tuple[int, int], min_areas: int) -> dict:
    names = [MONTHS[m] for m in months]

    def summary(members: list[int]) -> dict:
        per_month = {name: [] for name in names}
        both = []
        for row in members:
            values = (cloud.get(ids[row]) or {}).get("cloud_pct")
            pair = [values[m] if values is not None and known(values[m]) else None for m in months]
            for name, value in zip(names, pair):
                if value is not None:
                    per_month[name].append(value)
            if None not in pair:
                both.append(sum(pair) / 2.0)
        return {"areas": len(members),
                "with_a_value": {**{name: len(per_month[name]) for name in names}, "both": len(both)},
                "median_pct": {**{name: median_or_none(per_month[name]) for name in names}, "both": median_or_none(both)}}

    by_region: dict[str, list[int]] = {}
    for row in rows:
        by_region.setdefault(regions[row] or "Unnamed region", []).append(row)
    listed = [{"region": name, **summary(members)} for name, members in by_region.items()]
    listed.sort(key=lambda r: (r["median_pct"]["both"] is None, r["median_pct"]["both"] or 0.0, r["region"]))
    nameable = [r for r in listed if r["median_pct"]["both"] is not None and r["with_a_value"]["both"] >= min_areas
                and r["region"] != "Unnamed region"]
    return {"months": names, "month_index": list(months), "areas": len(rows), "all": summary(rows), "regions": listed,
            "clearest": nameable[0]["region"] if nameable else None,
            "cloudiest": nameable[-1]["region"] if len(nameable) > 1 else None}


def _clearest_sentence(season: dict, side: str) -> str | None:
    if season["clearest"] is None:
        return None
    region = next(r for r in season["regions"] if r["region"] == season["clearest"])
    first, second = season["months"]
    lead = (f"{region['region']} is the clearest {side} region in {first} and {second}: "
            f"median sky cover {region['median_pct']['both']:.0f} percent")
    overall = season["all"]["median_pct"]["both"]
    full = f"{lead}, against {overall:.0f} for all {side} areas." if overall is not None else lead + "."
    return full if len(full.split()) <= 25 else lead + "."


def _daytime(rows: list[int], cloud: dict, ids: list[str], months: tuple[int, int]) -> dict:
    names = [MONTHS[m] for m in months]
    compared = {name: 0 for name in names}
    differ = {name: 0 for name in names}
    any_compared = any_differ = 0
    for row in rows:
        record = cloud.get(ids[row]) or {}
        all_hours, day = record.get("cloud_pct"), record.get("cloud_pct_day")
        seen = far = False
        for name, month in zip(names, months):
            if all_hours is None or day is None or not known(all_hours[month]) or not known(day[month]):
                continue
            seen = True
            compared[name] += 1
            if abs(day[month] - all_hours[month]) > DAYTIME_POINTS:
                differ[name] += 1
                far = True
        any_compared += seen
        any_differ += far

    def share(part: int, whole: int) -> dict:
        return {"areas_compared": whole, "differ": part, "share": round(part / whole, 4) if whole else None}

    return {**{name: share(differ[name], compared[name]) for name in names}, "either_month": share(any_differ, any_compared)}


def cloud_regions(cloud_doc: dict, grazing_doc: dict | None, areas: dict, min_areas: int = MIN_AREAS_TO_NAME_A_REGION) -> dict:
    """Median sky cover by region in the months of the long windows, two sentences, and the daytime difference."""
    meta = cloud_doc.get("meta") or {}
    cloud = cloud_doc.get("cells") or {}
    ids = areas["ids"]
    regions, regions_from = areas["region"], "site/data/cells.json"
    if grazing_doc is not None:
        by_id = {cell.get("id"): cell.get("region") for cell in grazing_doc.get("cells") or []}
        if all(area_id in by_id for area_id in ids):
            regions, regions_from = [by_id[area_id] for area_id in ids], "data/derived/grazing_cells.json"
    if regions is None:
        raise ExtrasError("no region names: neither grazing_cells.json nor site/data/cells.json gives a region for every area")
    north = [row for row, side in enumerate(areas["hemisphere"]) if side == "N"]
    south = [row for row, side in enumerate(areas["hemisphere"]) if side != "N"]
    seasons = {"north": _season(north, regions, cloud, ids, NORTH_MONTHS, min_areas),
               "south": _season(south, regions, cloud, ids, SOUTH_MONTHS, min_areas)}
    has_day = any(isinstance(record, dict) and "cloud_pct_day" in record for record in cloud.values())
    return {
        "source": "data/derived/cloud_cells.json", "source_written": written_inside(cloud_doc),
        "cloud_source": meta.get("source"), "period": meta.get("period"), "grid_deg": meta.get("grid_deg"),
        "units": "percent of sky covered, monthly mean over all hours; medians over the areas of a region",
        "what_it_is": meta.get("what_it_is"), "what_it_is_not": meta.get("what_it_is_not"),
        "regions_from": regions_from,
        "both_what": "'both' is the median over areas of the mean of the two months, for areas with a value in each",
        "min_areas_to_be_named": min_areas,
        "areas_not_in_the_cloud_file": sum(1 for area_id in ids if area_id not in cloud),
        **seasons,
        "sentences": [_clearest_sentence(seasons["north"], "northern"), _clearest_sentence(seasons["south"], "southern")],
        "caution": "Sky cover is a monthly mean over all hours on a coarse grid, not the chance of seeing a low Sun.",
        "daytime": None if not has_day else {
            "more_than_points": DAYTIME_POINTS,
            "what": "share of areas whose daytime-only sky cover differs from the all-hours figure by more than this many "
                    "points, among areas with both values in that month",
            "north": _daytime(north, cloud, ids, NORTH_MONTHS), "south": _daytime(south, cloud, ids, SOUTH_MONTHS)},
    }


# ---- the whole run ----

LAYOUTS = {
    "moon.json": {
        "layout": {"cards": "one per lunar site, in the page's site order: id, has_model (false: no NASA 5 m terrain model, "
                            "thus pgda_model and extent_km are null and box_km gives the sourced box), model_note, "
                            "position {how_sure, source, note}, official_name, short_name, name_in_project, name_note, "
                            "nasa_list {on_2022_list_of_13, name_2022, on_2024_list_of_9, name_2024, summary, links}, "
                            "why {text, confirmed, sourced, sources, note}, sun_ceiling {deg, range_deg, how, kind, source}, "
                            "shadow_of_1m_object_at_ceiling_m, shadow_how, lit {mean_share, best_point_share, how, kind, source}, "
                            "permanent_shadow {share, how, kind, source}, diviner {label, model_based, annual_mean_temp_2cm_K/C and "
                            "annual_max_temp_surface_K/C each {mean, min, max}, ice {...shares 0 to 1}, how, source, citation}, "
                            "picture {page, title, note, credit, credit_source, alternative, sun_heights_of_images} (page and credit "
                            "null where no low-Sun picture exists), earth_cannot_match [{what, number, unit, moon, earth, source, note}]",
                   "lists": "what NASA's 2022 and 2024 lists are, with links",
                   "diviner": "the product, its label 'model-based', and the caveat on the value -1 (undocumented_value)",
                   "picture_credit": "the credit line for any linked LROC picture"},
        "feeds": "decision 9 (lunar site cards); decision 7 'What is different' (the lunar temperature and earth_cannot_match); "
                 "decision 12 (what Earth cannot copy); official names everywhere",
    },
    "temperature.bin": {
        "feeds": "decision 7 'What is different': the area's mean air temperature in the month of a ten-day period "
                 "(month = meta.json bins[b].month - 1), beside extras.json temperature.lunar_comparison",
    },
    "temperature_surface.bin": {
        "feeds": "decision 7 'What is different': the mean surface (skin) temperature, same use as temperature.bin",
    },
    "sunpath.json": {
        "layout": {"band_deg": "[low, high] limits of the band, degrees",
                   "moon": "the lunar site: name, ceiling_deg, year figures, start_utc, end_utc, path {hours_since_start, azimuth_deg, "
                           "elevation_deg, rows_in_source} thinned, marks {every_hours: 24, ...} one day apart",
                   "earth": "the Earth place: name, date, best_bin_label, minutes_in_band, longest_spell_minutes, minutes_above_terrain, "
                            "area (index of its place card), path {solar_time_h, azimuth_deg, elevation_deg} thinned, marks "
                            "{every_hours: 1, ...} one hour apart, terrain_horizon {sector_centres_deg, centre_deg, cell_median_deg, "
                            "cell_p10_deg, cell_p90_deg} 36 sectors",
                   "shows": "short sentences saying what the picture shows",
                   "cautions": "[{key, main, sentences}]; main marks the three for the caption (best cases, smooth Moon, height only)",
                   "caption": "the drawn-by-code caption", "axis_centre": "north or south: the direction to put in the middle",
                   "angles": "azimuth 0 = north, clockwise; elevation above a level horizon; degrees"},
        "feeds": "decision 10 (the Sun-path picture in 'The light we want to copy')",
    },
    "validation.json": {
        "layout": {"flags": "terrain_step_is_a_census, horizon_coverage, ranked_is_a_census {N, S}: whether the terrain step covers every measured area yet",
                   "lower_latitude_sites": "sites[] {name, lat, lon, kind, targets{site id: hours_a_year_in_band, longest_spell_minutes, "
                                           "hours_in_spells_of_2h, has_a_2h_spell, ...}} and summary{site id}",
                   "latitude_against_full_method": "targets{site id}{winter_half, summer_half, year}{all_measured_cells, "
                                                   "measured_cells_with_a_horizon}{scope, sun_alone, after_snow, after_terrain, after_cloud}"
                                                   "{cells, bare_km2, share_of_sun_alone, median_share_of_hours_kept, still_at_least_h}",
                   "known_sites": "caveat, summary, sites{known_analogs_poleward_of_59, named_sites_north, antarctic_sites}[] {name, cell, "
                                  "area (index or null), targets{site id: long_open_hours, percentile_among_ranked, rank_from_top, "
                                  "ranked_cells, verdict}}",
                   "sensitivity": "targets{site id}{limit_deg, table[] {choice, scope, cells, bare_km2, baseline_cells, change, "
                                  "moves_more_than_a_quarter}, moves_more_than_a_quarter[]}",
                   "snow_station_check": "the station check of the snow maps, or null: overall {stations, n, mean_bias, "
                                         "mean_abs_difference, mean_bias_95_interval}, periods{whole_year, winter_half, summer_half, "
                                         "...}{days, with_stale_flag_rule, as_mapped}, calibration[] {ims_low, ims_high, "
                                         "n_station_bins, mean_ims, mean_station_snow_free}, method, selection {examined, kept}",
                   "headlines": "ready sentences, as written in the source", "notes": "how to word these on the page"},
        "feeds": "decision 11 ('How sure are we'): lower-latitude places, the funnel, known sites, the sensitivity table, "
                 "the station check of the snow maps",
    },
    "sources.json": {
        "layout": {"sources": "[{n, name, provider, group (NASA, partner agency, other), group_note, used_for, link, fetch_from, licence, "
                              "licence_links, credit_ref, credit, credit_note, raw_files_public, derived_public}]",
                   "credits": "[{ref, title, mark, text, quotes, links}] the exact credit lines of section 3",
                   "notices": "copernicus_dem (print beside the map and any horizon or slope figure), copernicus_liability, comnap, worldcover",
                   "licence_line": "the one line for the page footer and inside any saved file",
                   "nasa_data, partner_data": "[{name, link, note, text, only_if_the_page_links_to_it}] for the two form fields",
                   "other_open_data": "the sentence naming the other open data", "problems": "what could not be read; empty when all was"},
        "feeds": "decision 12 (sources with exact credit lines, licence line); decision 13 (source and licence line inside the saved "
                 "CSV and GeoJSON); the map caption (notices.copernicus_dem); the NASA Data and Partner Data form fields",
    },
    "places.json": {
        "layout": {"places": "[{name, analog_use_found, wording, detail, not_checked, evidence, links, points[] {lat, lon, station "
                             "{name, km, ...}, year_round_station, airfield {name, km, ...} or null, airfield_note}, areas[] "
                             "{id, index, point, km_to_point}}]",
                   "area_place": "area index (as text) to [place index, point index]",
                   "not_little_known": "{areas (indices), ids, because[] {name, kind, why, source_url, evidence, areas, ids}}: "
                                       "the page must not call these areas little known",
                   "antarctic_sites": "[{name, lat, lon, nearest_station, nearest_station_km, ..., existing_analog_use, "
                                      "suggested_change, areas, ids}] or null",
                   "comnap_credit": "print beside any Antarctic station name or distance"},
        "feeds": "decision 7 (practical notes of the place card: nearest station or airfield, known use); the rule that "
                 "Nordaustlandet, Vestfold Hills, Schirmacher Oasis and Tunnunik are not little known; the 'little known' switch",
    },
    "cloud_regions.json": {
        "layout": {"north, south": "{months, areas, all {areas, with_a_value, median_pct}, regions[] {region, areas, with_a_value, "
                                   "median_pct {month, month, both}} clearest first, clearest, cloudiest}",
                   "sentences": "[northern sentence, southern sentence]; null when no region is large enough to name",
                   "caution": "print with any cloud figure",
                   "daytime": "{more_than_points, north, south {month {areas_compared, differ, share}, either_month}} or null"},
        "feeds": "decision 7 'What is different' (cloud) and the cloud step of the calendar: where it is clearest, with the caution "
                 "that sky cover is not the chance of seeing a low Sun",
    },
}


# files whose rows or area numbers follow the page's list of areas: an older copy is only right for the list it was made for
AREA_FILES = ("temperature.bin", "temperature_surface.bin", "sunpath.json", "validation.json", "places.json")

# inputs that only add detail to a file: the file is written without them, and the run says what it then lacks
DETAIL_INPUTS = (
    ("moon.json", "site/data/meta.json",
     "the page's order and short names of the lunar sites: the cards come in the order of moon_cards.json"),
    ("sunpath.json", "data/derived/moon_cards.json",
     "the official name of the lunar site: the name in sunpath_demo.json is used"),
    ("places.json", "data/reference/antarctic_sites.json",
     "antarctic_sites, the Antarctic sites with their stations: it is null"),
    ("validation.json", "data/derived/snow_validation_many.json",
     "snow_station_check, the station check of the snow maps: it is null"),
    ("cloud_regions.json", "data/derived/grazing_cells.json",
     "the pipeline's region names: the regions of site/data/cells.json are used"),
)


def export(derived: Path, reference: Path, sources_md: Path, site_data: Path, out: Path | None = None) -> dict:
    """Build every file and write those whose inputs are there.

    Returns what was written, left out and failed, what was written without a detail, and which older copies were removed.
    """
    out = Path(out) if out is not None else Path(site_data)
    cells_path = Path(site_data) / "cells.json"
    if not cells_path.exists():
        raise FileNotFoundError(f"{cells_path} is not there: run scripts/export_site.py first, it decides the order of the areas")
    areas = areas_of(read_json(cells_path))
    n = len(areas["ids"])
    ids_hash = hashlib.sha256("\n".join(areas["ids"]).encode()).hexdigest()
    try:
        previous = read_json(out / "extras.json")
    except ValueError:
        previous = None
    made_for = ((previous.get("areas") or {}).get("ids_sha256") if isinstance(previous, dict) else None)
    meta_doc = read_json(Path(site_data) / "meta.json")
    targets = page_targets(meta_doc)

    inputs = {
        "data/derived/moon_cards.json": Path(derived) / "moon_cards.json",
        "data/derived/temperature_cells.json": Path(derived) / "temperature_cells.json",
        "data/derived/validation_extras.json": Path(derived) / "validation_extras.json",
        "data/derived/snow_validation_many.json": Path(derived) / "snow_validation_many.json",
        "data/derived/sunpath_demo.json": Path(derived) / "sunpath_demo.json",
        "data/derived/cloud_cells.json": Path(derived) / "cloud_cells.json",
        "data/derived/grazing_cells.json": Path(derived) / "grazing_cells.json",
        "data/reference/known_analogs_check.json": Path(reference) / "known_analogs_check.json",
        "data/reference/antarctic_sites.json": Path(reference) / "antarctic_sites.json",
        "data/SOURCES.md": Path(sources_md),
        "site/data/cells.json": cells_path,
        "site/data/meta.json": Path(site_data) / "meta.json",
    }
    docs = {}
    for label, path in inputs.items():
        if not path.exists():
            docs[label] = None
        elif path.suffix == ".md":
            docs[label] = path.read_text()
        elif label in ("site/data/cells.json", "site/data/meta.json"):
            docs[label] = True          # read above
        else:
            docs[label] = read_json(path)
    sources_written = {}
    for label, path in inputs.items():
        if docs[label] is None:
            sources_written[label] = None
        else:
            inside = written_inside(docs[label]) if isinstance(docs[label], (dict, list)) else None
            if label == "site/data/meta.json" and isinstance(meta_doc, dict):
                inside = meta_doc.get("generated")
            sources_written[label] = {"modified": modified(path), "written_inside": inside, "bytes": path.stat().st_size}

    built: dict[str, bytes] = {}
    layouts: dict[str, dict] = {}
    left_out: dict[str, str] = {}
    failed: dict[str, str] = {}
    temperature_block = None

    def attempt(names: list[str], needs: str, build) -> None:
        """Run one builder; a missing input leaves its files out, a bad input fails them, the rest goes on."""
        if docs[needs] is None:
            for name in names:
                left_out[name] = f"{needs} is not there"
            return
        try:
            build()
        except (ExtrasError, KeyError, TypeError, ValueError, IndexError) as error:
            for name in names:
                built.pop(name, None)
                failed[name] = f"{type(error).__name__}: {error}"

    def build_moon():
        built["moon.json"] = json_bytes({"generated": utc_now(), **moon_cards(docs["data/derived/moon_cards.json"], targets)})

    def build_temperature():
        nonlocal temperature_block
        doc = docs["data/derived/temperature_cells.json"]
        fields = (doc.get("meta") or {}).get("fields") or {}
        for name, field in (("temperature.bin", "t2m_c"), ("temperature_surface.bin", "ts_c")):
            table = temperature_table(doc, areas["ids"], field)
            if table is None:
                left_out[name] = f"data/derived/temperature_cells.json has no field {field}"
                continue
            built[name] = table.tobytes()
            layouts[name] = {"type": "int8", "shape": [n, 12],
                             "order": "area (the order of ids in cells.json), then month, January first",
                             "unit": "whole degrees Celsius, halves rounded away from zero, held inside -127 to 127",
                             "unknown": T_UNKNOWN, "field": field, "what": fields.get(field)}
        temperature_block = temperature_notes(doc, areas)

    def build_sunpath():
        result = sun_paths(docs["data/derived/sunpath_demo.json"], docs["data/derived/moon_cards.json"], areas)
        built["sunpath.json"] = json_bytes({"generated": utc_now(), **result})

    def build_validation():
        result = validation(docs["data/derived/validation_extras.json"], areas, docs["data/derived/snow_validation_many.json"])
        built["validation.json"] = json_bytes({"generated": utc_now(), **result})

    def build_sources():
        built["sources.json"] = json_bytes({"generated": utc_now(), **parse_sources(docs["data/SOURCES.md"])})

    def build_places():
        result = places(docs["data/reference/known_analogs_check.json"], docs["data/reference/antarctic_sites.json"], areas)
        built["places.json"] = json_bytes({"generated": utc_now(), **result})

    def build_cloud():
        result = cloud_regions(docs["data/derived/cloud_cells.json"], docs["data/derived/grazing_cells.json"], areas)
        built["cloud_regions.json"] = json_bytes({"generated": utc_now(), **result})

    attempt(["moon.json"], "data/derived/moon_cards.json", build_moon)
    attempt(["temperature.bin", "temperature_surface.bin"], "data/derived/temperature_cells.json", build_temperature)
    attempt(["sunpath.json"], "data/derived/sunpath_demo.json", build_sunpath)
    attempt(["validation.json"], "data/derived/validation_extras.json", build_validation)
    attempt(["sources.json"], "data/SOURCES.md", build_sources)
    attempt(["places.json"], "data/reference/known_analogs_check.json", build_places)
    attempt(["cloud_regions.json"], "data/derived/cloud_cells.json", build_cloud)

    out.mkdir(parents=True, exist_ok=True)
    written = {name: write_bytes(out / name, data) for name, data in built.items()}

    # An older copy of a file this run could not make may stay only while it fits the page's list of areas:
    # its rows and area numbers would otherwise sit on the wrong areas.
    removed: dict[str, str] = {}
    for name in dict.fromkeys(list(left_out) + list(failed)):
        if name in AREA_FILES and name not in written and (out / name).exists() and made_for != ids_hash:
            (out / name).unlink()
            removed[name] = ("it was made for another list of areas than the page has now" if made_for is not None
                             else "no index says which list of areas it was made for")
    lacking = {label: docs[label] is None for _, label, _ in DETAIL_INPUTS}
    lacking["site/data/meta.json"] = targets is None
    without = [{"file": name, "input": label, "lacks": lacks} for name, label, lacks in DETAIL_INPUTS
               if name in written and lacking[label]]
    needs = {"moon.json": ["data/derived/moon_cards.json", "site/data/meta.json"],
             "temperature.bin": ["data/derived/temperature_cells.json", "site/data/cells.json"],
             "temperature_surface.bin": ["data/derived/temperature_cells.json", "site/data/cells.json"],
             "sunpath.json": ["data/derived/sunpath_demo.json", "data/derived/moon_cards.json"],
             "validation.json": ["data/derived/validation_extras.json", "data/derived/snow_validation_many.json",
                                 "site/data/cells.json"],
             "sources.json": ["data/SOURCES.md"],
             "places.json": ["data/reference/known_analogs_check.json", "data/reference/antarctic_sites.json", "site/data/cells.json"],
             "cloud_regions.json": ["data/derived/cloud_cells.json", "data/derived/grazing_cells.json", "site/data/cells.json"]}
    files = {}
    for name, size in written.items():
        files[name] = {"bytes": size, "from": [label for label in needs[name] if docs[label] is not None],
                       "layout": layouts.get(name) or LAYOUTS[name]["layout"], "feeds": LAYOUTS[name]["feeds"]}
    index = {
        "generated": utc_now(),
        "script": "scripts/export_site_extras.py",
        "how_to_rerun": "uv run python scripts/export_site.py, then uv run python scripts/export_site_extras.py",
        "unknown": "null in the JSON files, -128 in the temperature byte files; never 0",
        "areas": {"count": n, "order": "the ids of site/data/cells.json, as it was when this ran",
                  "ids_sha256": ids_hash,
                  "ids_sha256_what": "SHA-256 of the ids joined by a line feed, in order",
                  "what": "the per-area files here (temperature.bin, temperature_surface.bin, temperature.grid_height_m, and every "
                          "'area' or 'index' in the JSON files) follow this order; run this script again after export_site.py"},
        "targets": [t["id"] for t in targets] if targets else None,
        "files": files,
        "files_what": "the files this run made. Read a file only when it is listed here: one named under left_out or failed "
                      "was not made by this run, and a copy of it in the folder is an older one.",
        "left_out": [{"file": name, "because": reason, "older_copy_kept": (out / name).exists()} for name, reason in left_out.items()],
        "failed": [{"file": name, "because": reason, "older_copy_kept": (out / name).exists()} for name, reason in failed.items()],
        "written_without": without,
        "written_without_what": "files made without an input that only adds detail, and what each then lacks",
        "older_copies_removed": [{"file": name, "because": reason} for name, reason in removed.items()],
        "sources_written": sources_written,
        "temperature": temperature_block,
    }
    written["extras.json"] = write_bytes(out / "extras.json", json_bytes(index))
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
    parser.add_argument("--reference", type=Path, default=ROOT / "data" / "reference")
    parser.add_argument("--sources", type=Path, default=ROOT / "data" / "SOURCES.md")
    parser.add_argument("--site-data", type=Path, default=ROOT / "site" / "data",
                        help="the folder with the page's cells.json and meta.json")
    parser.add_argument("--out", type=Path, default=None, help="where to write (default: the site-data folder)")
    args = parser.parse_args()
    report = export(args.derived, args.reference, args.sources, args.site_data, args.out)
    print(f"{report['areas']} areas; wrote into {report['out']}:")
    for name, size in report["written"].items():
        print(f"  {name:26s} {size:>9,d} bytes")
    print(f"  {'total':26s} {sum(report['written'].values()):>9,d} bytes")
    if report["failed"]:
        for name, reason in report["failed"].items():
            print(f"FAILED: {name} was not written: {reason}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()

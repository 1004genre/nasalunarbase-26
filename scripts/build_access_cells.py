# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""How far every cell is from a runway. Writes data/derived/access_cells.json.

For each cell of data/derived/grazing_cells.json: the nearest airfield that
takes fixed-wing aircraft, the nearest such airfield with scheduled service,
and the country or territory the cell most likely lies in, all read from the
OurAirports airports table (public domain), kept under data/raw/ourairports/.

What this is: a straight-line (great-circle) distance from the cell centre to
a runway. What it is not: not a road or a port, not a permit, not a cost.

Run it again (no network needed once the table is on disk, about 10 seconds):

    uv run python scripts/build_access_cells.py --offline

The access file depends only on the cell list and the airports table, so it
needs rebuilding only when grazing_cells.json gains or loses cells. The tables
that set access beside the scores are read fresh from cells_scored.json:

    uv run python scripts/build_access_cells.py --report-only

(`--report` builds and then reports; `--report-json PATH` also saves the
tables as JSON; `--min-hours 25` lowers the hours a cell needs to be counted,
which the 2.08 degree target needs: no ranked cell reaches 100 h there.)
The result is written beside the old file and renamed into place.
"""
import argparse
import csv
import datetime
import hashlib
import http.client
import json
import math
import os
import shutil
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np

from twinfinder import fetch, reference, score, sun

SOURCE_URL = "https://davidmegginson.github.io/ourairports-data/airports.csv"
FALLBACK_URL = "https://raw.githubusercontent.com/davidmegginson/ourairports-data/main/airports.csv"
RAW = Path("data/raw/ourairports")
TABLE = RAW / "airports.csv"
DOWNLOAD_NOTE = "download.json"
CELLS = Path("data/derived/grazing_cells.json")
SCORED = Path("data/derived/cells_scored.json")
OUT = Path("data/derived/access_cells.json")

EARTH_RADIUS_KM = reference.EARTH_RADIUS_KM   # 6371.0, the sphere the rest of the project measures on
MAX_KM = 1500.0        # no airfield within this distance is stored as null
COUNTRY_KM = 300.0     # a cell takes its country from the nearest record of the table within this distance
KEEP_TYPES = ("small_airport", "medium_airport", "large_airport")       # runways for fixed-wing aircraft
DROP_TYPES = ("heliport", "seaplane_base", "balloonport", "closed")     # no runway, or no longer in use
# Records of the table that are not a runway of their own, left out by hand, each with the reason.
SKIP_IDENTS = {
    "AQ-0012": "a record named 'Navaid' at 89.998 S, 0.2 km from the South Pole station skiway (NZSP): a placeholder, "
               "not a second runway; without this it would be the 'nearest airfield' of 217 cells",
}
# The country a cell's own region box stands for, where the box (twinfinder/regions.py) covers one country only.
# A country guessed from the nearest record that contradicts it is withheld (null): the two disagree, so it is unknown.
REGION_COUNTRIES = {
    "Alaska": ("US",), "Arctic Canada": ("CA",), "Greenland": ("GL",), "Iceland": ("IS",),
    "Svalbard": ("NO", "SJ"), "Jan Mayen": ("NO", "SJ"), "Bear Island (Bjornoya)": ("NO", "SJ"),
    "Faroe Islands": ("FO",), "Shetland and Orkney": ("GB",),
    "Franz Josef Land": ("RU",), "Novaya Zemlya": ("RU",), "Severnaya Zemlya": ("RU",),
    "Kola and north-west Russia": ("RU",), "Siberia and the Russian Far East": ("RU",), "Chukotka": ("RU",),
    "South Orkney Islands": ("AQ",), "Antarctic Peninsula and South Shetlands": ("AQ",), "Dronning Maud Land": ("AQ",),
    "Enderby and Mac.Robertson Land": ("AQ",), "Princess Elizabeth Land": ("AQ",), "Wilkes Land": ("AQ",),
    "Victoria Land": ("AQ",), "Transantarctic Mountains": ("AQ",), "Ellsworth Mountains": ("AQ",), "Antarctica": ("AQ",),
}
ATTEMPTS = 4
MIN_HOURS = 100.0      # long-spell hours after terrain that a cell needs to be counted in the report
WITHIN_KM = (50, 100, 200)
REACH_KM = 100.0       # "within reach" in the lists of the report
LICENCE_STATEMENT = (
    "This is free and unencumbered software released into the public domain. "
    "(first line of the LICENSE file, The Unlicense, of github.com/davidmegginson/ourairports-data, "
    "the repository the table is published from; copy kept as data/raw/ourairports/LICENSE)"
)
NOT = (
    "Not a road or a port, not a permit, not a cost: a straight-line distance to a runway. "
    "It does not say that a road, a track or a boat links the airfield to the cell, that the runway is open, "
    "long enough or has fuel, that anyone flies there on the day, that the land may be entered, or what the trip costs. "
    "Water, ice caps, mountains and borders between the cell and the runway are ignored. "
    "\"Scheduled service\" is the table's own yes/no flag, entered by volunteers; it was not checked against any timetable."
)


# ---------------------------------------------------------------- distance

def great_circle_km(lat1, lon1, lat2, lon2):
    """Distance along the great circle between points given in degrees, on a sphere of radius 6371.0 km (haversine).

    Takes numbers or arrays that broadcast against each other.
    """
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dp = p2 - p1
    dl = np.radians(np.asarray(lon2, dtype=float) - np.asarray(lon1, dtype=float))
    a = np.sin(dp / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    km = 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))
    return float(km) if np.ndim(km) == 0 else km


def unit_vectors(lat, lon) -> np.ndarray:
    lat, lon = np.radians(np.asarray(lat, dtype=float)), np.radians(np.asarray(lon, dtype=float))
    return np.stack([np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)], axis=-1)


def nearest(lat, lon, field_lat, field_lon, max_km: float = MAX_KM, chunk: int = 512):
    """For each point the index of the nearest field and its distance in km; -1 and NaN when none lies within max_km.

    The nearest field is the one whose direction from the Earth's centre is closest to the point's
    (largest dot product); its distance is then worked out with great_circle_km. Only fields within
    max_km in latitude of a batch of points are looked at, which cannot lose a field that is in reach.
    """
    lat, lon = np.asarray(lat, dtype=float), np.asarray(lon, dtype=float)
    field_lat, field_lon = np.asarray(field_lat, dtype=float), np.asarray(field_lon, dtype=float)
    index = np.full(lat.shape, -1, dtype=int)
    km = np.full(lat.shape, np.nan)
    if lat.size == 0 or field_lat.size == 0:
        return index, km
    band = math.degrees(max_km / EARTH_RADIUS_KM) + 0.01
    vectors = unit_vectors(field_lat, field_lon)
    order = np.argsort(lat, kind="stable")
    for start in range(0, order.size, chunk):
        part = order[start:start + chunk]
        near = np.flatnonzero((field_lat >= lat[part].min() - band) & (field_lat <= lat[part].max() + band))
        if near.size == 0:
            continue
        best = near[(unit_vectors(lat[part], lon[part]) @ vectors[near].T).argmax(axis=1)]
        distance = great_circle_km(lat[part], lon[part], field_lat[best], field_lon[best])
        found = distance <= max_km
        index[part[found]] = best[found]
        km[part[found]] = distance[found]
    return index, km


# ---------------------------------------------------------------- the table

def read_airfields(path: Path) -> tuple[list[dict], int]:
    """Every row of the airports table with a usable position, ordered by ident; and how many rows had none."""
    rows, skipped = [], 0
    with open(path, newline="", encoding="utf-8") as handle:
        for raw in csv.DictReader(handle):
            try:
                lat, lon = float(raw["latitude_deg"]), float(raw["longitude_deg"])
            except (TypeError, ValueError):
                skipped += 1
                continue
            if not (math.isfinite(lat) and math.isfinite(lon) and abs(lat) <= 90.0 and abs(lon) <= 180.0):
                skipped += 1
                continue
            rows.append({"ident": raw["ident"], "type": raw["type"], "name": raw["name"] or None, "lat": lat, "lon": lon,
                         "country": (raw["iso_country"] or "").strip() or None,
                         "municipality": (raw["municipality"] or "").strip() or None,
                         "scheduled": (raw["scheduled_service"] or "").strip().lower() == "yes"})
    rows.sort(key=lambda r: (r["ident"], r["name"] or "", r["lat"], r["lon"]))
    return rows, skipped


def fixed_wing(rows: list[dict]) -> list[dict]:
    """The airfields with a runway for fixed-wing aircraft: small, medium and large airports."""
    return [r for r in rows if r["type"] in KEEP_TYPES]


def scheduled(rows: list[dict]) -> list[dict]:
    """Fixed-wing airfields the table flags as having scheduled service (a helipad or seaplane base with the flag is not one)."""
    return [r for r in fixed_wing(rows) if r["scheduled"]]


def left_out_by_hand(rows: list[dict]) -> dict:
    """The records of SKIP_IDENTS that the table holds, each with the reason it is left out."""
    present = {r["ident"] for r in rows}
    return {ident: why for ident, why in SKIP_IDENTS.items() if ident in present}


def usable(rows: list[dict]) -> list[dict]:
    return [r for r in rows if r["ident"] not in SKIP_IDENTS]


def type_counts(rows: list[dict]) -> dict:
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["type"]] = counts.get(r["type"], 0) + 1
    return {"kept": {t: counts[t] for t in KEEP_TYPES if t in counts},
            "dropped": {t: counts[t] for t in DROP_TYPES if t in counts},
            "unknown_dropped": {t: n for t, n in sorted(counts.items()) if t not in KEEP_TYPES + DROP_TYPES}}


def now_utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def download(url: str, dest: Path) -> dict:
    """Fetch the table with the project's User-Agent and nothing else; keep a note of where and when beside it."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    request = urllib.request.Request(url, headers={"User-Agent": fetch.USER_AGENT})
    for attempt in range(1, ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(request, timeout=120) as response, open(part, "wb") as out:
                shutil.copyfileobj(response, out)
                expected = response.headers.get("Content-Length")
                last_modified = response.headers.get("Last-Modified")
            got = part.stat().st_size
            if expected is not None and got != int(expected):
                raise ConnectionError(f"short body: {got} of {expected} bytes from {url}")
            break
        except urllib.error.HTTPError:
            part.unlink(missing_ok=True)
            raise   # the server answered; the caller may try the other address
        except (urllib.error.URLError, ConnectionError, TimeoutError, http.client.IncompleteRead):
            part.unlink(missing_ok=True)
            if attempt == ATTEMPTS:
                raise
            time.sleep(5.0 * attempt)
    note = {"url": url, "fetched_utc": now_utc(), "last_modified": last_modified, "bytes": part.stat().st_size,
            "sha256": sha256_of(part)}
    os.replace(part, dest)
    write_json(dest.with_name(DOWNLOAD_NOTE), note)
    return note


def ensure_table(table: Path = TABLE, offline: bool = False) -> dict:
    """Make sure the table is on disk; return the note of its download (address, time, size, checksum)."""
    if not table.exists():
        if offline:
            raise FileNotFoundError(f"{table} is missing and --offline forbids the download; run once without --offline")
        try:
            return download(SOURCE_URL, table)
        except (urllib.error.URLError, ConnectionError, TimeoutError, http.client.IncompleteRead):
            return download(FALLBACK_URL, table)
    note_path = table.with_name(DOWNLOAD_NOTE)
    if note_path.exists():
        note = json.loads(note_path.read_text())
    else:
        stamp = datetime.datetime.fromtimestamp(table.stat().st_mtime, datetime.timezone.utc)
        note = {"url": None, "fetched_utc": stamp.strftime("%Y-%m-%dT%H:%M:%SZ"), "last_modified": None,
                "note": "no download note beside the table; the time is the file's own"}
    note["bytes"], note["sha256"] = table.stat().st_size, sha256_of(table)   # of the file that is read now
    return note


# ---------------------------------------------------------------- the records

def airfield_record(row: dict, km: float) -> dict:
    return {"name": row["name"], "ident": row["ident"], "country": row["country"], "type": row["type"],
            "km": round(float(km), 1), "municipality": row["municipality"], "scheduled_service": bool(row["scheduled"]),
            "lat": round(row["lat"], 4), "lon": round(row["lon"], 4)}


def build_cells(cells: list[dict], rows: list[dict], max_km: float = MAX_KM, country_km: float = COUNTRY_KM,
                tally: dict | None = None) -> dict:
    """The access record of every cell: nearest fixed-wing airfield, nearest with scheduled service, country.

    Distances are from the cell centre (the record's lat and lon). Unknown is None, never 0.
    The country is the country code of the nearest table record of any type (helipads and closed
    fields included: they still say whose land it is) within country_km, else None. It is also None
    when the cell's own region box stands for one country and the guess names another (REGION_COUNTRIES);
    tally, if given, receives how often that happened. Records of SKIP_IDENTS are never used.
    """
    rows = usable(rows)
    withheld = 0
    lat = np.array([c["lat"] for c in cells], dtype=float)
    lon = np.array([c["lon"] for c in cells], dtype=float)

    def look(fields: list[dict], limit: float):
        return nearest(lat, lon, [f["lat"] for f in fields], [f["lon"] for f in fields], limit)

    any_fields, sched_fields = fixed_wing(rows), scheduled(rows)
    any_i, any_km = look(any_fields, max_km)
    sched_i, sched_km = look(sched_fields, max_km)
    land_i, _ = look(rows, country_km)
    records = {}
    for n, c in enumerate(cells):
        country = rows[land_i[n]]["country"] if land_i[n] >= 0 else None
        allowed = REGION_COUNTRIES.get(c.get("region"))
        if country is not None and allowed is not None and country not in allowed:
            country, withheld = None, withheld + 1
        records[c["id"]] = {
            "nearest": airfield_record(any_fields[any_i[n]], any_km[n]) if any_i[n] >= 0 else None,
            "nearest_scheduled": airfield_record(sched_fields[sched_i[n]], sched_km[n]) if sched_i[n] >= 0 else None,
            "country": country,
        }
    if tally is not None:
        tally["country_withheld"] = withheld
    return records


def make_meta(rows: list[dict], skipped: int, records: dict, download: dict, max_km: float = MAX_KM,
              country_km: float = COUNTRY_KM, cells_file: str = CELLS.name, country_withheld: int = 0) -> dict:
    values = list(records.values())
    return {
        "written": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "what_this_is": "For every cell of the search: the straight-line (great-circle) distance from the cell centre "
                        "to the nearest runway, and to the nearest runway with scheduled service, with the airfield's "
                        "name. A first look at how reachable a place is, to be read beside the ranking by light.",
        "what_this_is_not": NOT,
        "source": {
            "name": "OurAirports, airports.csv",
            "url": download.get("url") or SOURCE_URL,
            "fallback_url": FALLBACK_URL,
            "licence": "public domain",
            "licence_statement": LICENCE_STATEMENT,
            "fetched_utc": download.get("fetched_utc"),
            "last_modified": download.get("last_modified"),
            "bytes": download.get("bytes"),
            "sha256": download.get("sha256"),
            "raw_folder": str(RAW),
            "columns_used": ["ident", "type", "name", "latitude_deg", "longitude_deg", "iso_country", "municipality",
                             "scheduled_service"],
            "columns_note": "The table's data dictionary page (ourairports.com/help/data-dictionary.html) could not be "
                            "read on 14 November 2026: the site's certificate had expired on 6 November and the check "
                            "was not switched off. The columns were read from the file itself: `type` holds exactly "
                            "the seven values listed under types_kept and types_dropped, `scheduled_service` holds "
                            "yes or no, `iso_country` a two-letter code on every row, and every row has coordinates "
                            "in decimal degrees.",
        },
        "cells_from": cells_file,
        "cell_point": "the cell centre (lat and lon of the cell's record); a cell is about 11 km across, so the "
                      "distance from any point of the cell differs from the stored one by up to about 8 km",
        "distance": "great circle on a sphere, haversine formula; against the real ellipsoid this is within about "
                    "0.5 percent",
        "earth_radius_km": EARTH_RADIUS_KM,
        "max_km": max_km,
        "country_within_km": country_km,
        "types_kept": list(KEEP_TYPES),
        "types_dropped": list(DROP_TYPES),
        "types_note": "Kept: small, medium and large airports, which have a runway for fixed-wing aircraft (gravel and "
                      "ice strips are small airports in this table). Dropped: heliports, seaplane bases, balloon ports "
                      "and closed fields. So a settlement served only by helicopter (many in Greenland) does not count "
                      "as an airfield here.",
        "scheduled_rule": "nearest_scheduled is the nearest kept airfield whose scheduled_service is yes; heliports "
                          "and seaplane bases with scheduled service are not counted",
        "country_rule": "country is the iso_country of the nearest record of the table of any type (heliports and "
                        "closed fields included) within country_within_km of the cell centre, else null. It is a "
                        "guess from the nearest neighbour, not a border test: close to a border or across a strait it "
                        "can name the neighbour. Where the cell's own region box (the `region` of its record) stands "
                        "for one country and the guess names another, the country is null as well "
                        "(counts.country_null_because_the_region_disagrees): for example the north coast of Greenland, "
                        "whose nearest record is Alert in Canada. Svalbard and Jan Mayen carry Norway's code (NO) in "
                        "this table, Greenland GL, Antarctica AQ.",
        "region_countries": {name: list(codes) for name, codes in REGION_COUNTRIES.items()},
        "record": {"nearest": "nearest kept airfield within max_km, or null",
                   "nearest_scheduled": "nearest kept airfield with scheduled service within max_km, or null",
                   "country": "two-letter code, or null",
                   "airfield_fields": {"name": "airfield name", "ident": "OurAirports ident (the ICAO code where one exists)",
                                       "country": "iso_country of the airfield", "type": "one of types_kept",
                                       "km": "great-circle km from the cell centre, one decimal",
                                       "municipality": "the place the table names for the airfield, or null",
                                       "scheduled_service": "true or false, the table's flag",
                                       "lat": "airfield latitude, degrees", "lon": "airfield longitude, degrees"}},
        "rows": {"in_table": len(rows) + skipped, "without_a_usable_position": skipped,
                 "left_out_by_hand": left_out_by_hand(rows),
                 "fixed_wing": len(fixed_wing(usable(rows))), "fixed_wing_scheduled": len(scheduled(usable(rows))),
                 "by_type": type_counts(rows)},
        "counts": {"cells": len(values),
                   "nearest_null": sum(v["nearest"] is None for v in values),
                   "nearest_scheduled_null": sum(v["nearest_scheduled"] is None for v in values),
                   "country_null": sum(v["country"] is None for v in values),
                   "country_null_because_the_region_disagrees": country_withheld},
        "rerun": "uv run python scripts/build_access_cells.py --offline   (the tables: add --report, or --report-only "
                 "after cells_scored.json is rebuilt)",
    }


def write_json(path: Path, value) -> None:
    """Write beside the file and rename into place, so a reader never sees half a file. NaN is refused."""
    side = path.with_name(path.name + ".part")
    try:
        side.write_text(json.dumps(value, separators=(",", ":"), allow_nan=False, ensure_ascii=False), encoding="utf-8")
    except ValueError:
        side.unlink(missing_ok=True)
        raise
    os.replace(side, path)


# ---------------------------------------------------------------- the report: access beside the scores

def bin_dates(b: int) -> str:
    """A ten-day bin as dates, such as 20 Jun-29 Jun; the last bin runs to the end of the year."""
    first = b * sun.BIN_DAYS + 1
    last = 365 if b == sun.N_BINS - 1 else first + sun.BIN_DAYS - 1
    return f"{sun.doy_to_label(first)}-{sun.doy_to_label(last)}"


def periods_note(top_bins) -> str:
    return ", ".join(f"{bin_dates(b)} ({hours:.{0 if hours >= 1.0 else 1}f} h)" for b, hours in top_bins or []) or "none"


def ranked_cells(cells: list[dict], hemisphere: str) -> list[dict]:
    ranking = "north" if hemisphere == "N" else "south"
    return [c for c in cells if c.get("ranked") and c.get("ranking") == ranking]


def qualifying(cells: list[dict], target: str, hemisphere: str, min_hours: float | None = MIN_HOURS) -> list[dict]:
    """Ranked cells of a hemisphere whose long-spell hours after terrain reach min_hours (the hours the light score uses).

    North: long_open_hours (snow-free, terrain applied). South: long_summer_rock_open_hours (rock season, terrain applied).
    """
    out = []
    for c in ranked_cells(cells, hemisphere):
        hours = score.light_hours(c["targets"][target], hemisphere, "open")
        if min_hours is None or (hours is not None and hours >= min_hours):
            out.append(c)
    return out


def within_counts(cells: list[dict], access: dict, key: str, limits=WITHIN_KM) -> dict:
    """How many of the cells lie within each distance of the airfield stored under key (nearest or nearest_scheduled)."""
    counts = {str(limit): 0 for limit in limits}
    none = missing = 0
    for c in cells:
        record = access.get(c["id"])
        if record is None:
            missing += 1
        elif record[key] is None:
            none += 1
        else:
            for limit in limits:
                counts[str(limit)] += record[key]["km"] <= limit
    return {"cells": len(cells), "within_km": counts, "no_airfield_within_reach": none, "not_in_access_file": missing}


def goal_key(target: str, goal: str):
    return lambda c: c["targets"][target]["goals"].get(goal)


def tie_key(target: str, hemisphere: str):
    return lambda c: score.tie_hours(c["targets"][target], hemisphere)


def in_order(cells: list[dict], target: str, hemisphere: str, goal: str) -> list[dict]:
    """Ranked cells with a known score above zero, best first; equal scores go by the uncapped hours (as in RESULTS.md)."""
    key, tie = goal_key(target, goal), tie_key(target, hemisphere)
    known = [c for c in ranked_cells(cells, hemisphere) if key(c) is not None and key(c) > 0.0]
    return sorted(known, key=lambda c: (key(c), tie(c)), reverse=True)


def site_row(c: dict, access: dict, target: str, hemisphere: str, goal: str, key: str, place: int | None, of: int) -> dict:
    values = c["targets"][target]
    record = access.get(c["id"]) or {}
    field = record.get(key)
    south = hemisphere == "S"
    return {"id": c["id"], "lat": c["lat"], "lon": c["lon"], "region": c.get("region"), "country": record.get("country"),
            "site_name": c.get("site_name"), "bare": None if c.get("bare") is None else round(c["bare"], 2),
            "score": values["goals"].get(goal), "goal": goal, "place_among_ranked_cells": place, "ranked_cells_with_a_score": of,
            "hours": score.light_hours(values, hemisphere, "open"),
            "hours_flat_horizon": score.light_hours(values, hemisphere, "flat"),
            "clear_sky_hours": values.get("long_summer_rock_open_hours_clear" if south else "long_open_hours_clear"),
            "best_periods": periods_note(values.get("top_bins_summer_rock") if south else values.get("top_bins")),
            "airfield": field["name"] if field else None, "airfield_ident": field["ident"] if field else None,
            "airfield_km": field["km"] if field else None, "airfield_country": field["country"] if field else None,
            "airfield_place": field["municipality"] if field else None}


def best_within(cells: list[dict], access: dict, target: str, hemisphere: str, goal: str, key: str,
                within_km: float | None = REACH_KM, top: int = 5, min_hours: float | None = MIN_HOURS) -> list[dict]:
    """The best sites (one per 50 km, as everywhere in the project) among the qualifying cells within reach of an airfield.

    within_km=None and min_hours=None give the plain best sites of the ranking, with their airfield beside them.
    """
    order = in_order(cells, target, hemisphere, goal)
    place = {c["id"]: n for n, c in enumerate(order, 1)}
    pool = []
    for c in qualifying(cells, target, hemisphere, min_hours):
        field = (access.get(c["id"]) or {}).get(key)
        if within_km is None or (field is not None and field["km"] <= within_km):
            pool.append(c)
    sites = score.top_sites(pool, goal_key(target, goal), top=top, tie_key=tie_key(target, hemisphere))
    return [site_row(c, access, target, hemisphere, goal, key, place.get(c["id"]), len(order)) for c in sites]


def country_shares(cells: list[dict], access: dict, target: str, hemisphere: str, top: int = 50, sites: bool = False,
                   goal: str = "lighting") -> dict:
    """Which countries the best cells (or, with sites=True, the best sites one per 50 km) of a goal lie in."""
    order = in_order(cells, target, hemisphere, goal)
    if sites:
        order = score.top_sites(order, goal_key(target, goal), top=top, tie_key=tie_key(target, hemisphere))
    counts: dict[str, int] = {}
    unknown: dict[str, int] = {}
    taken = order[:top]
    for c in taken:
        country = (access.get(c["id"]) or {}).get("country") or "unknown"
        counts[country] = counts.get(country, 0) + 1
        if country == "unknown":
            unknown[str(c.get("region"))] = unknown.get(str(c.get("region")), 0) + 1
    by_count = dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))
    return {"top": len(taken), "cells": by_count,
            "share": {k: round(v / len(taken), 3) for k, v in by_count.items()} if taken else {},
            "regions_of_the_unknown": dict(sorted(unknown.items(), key=lambda kv: (-kv[1], kv[0])))}


def hubs(cells: list[dict], access: dict, target: str, hemisphere: str, key: str, within_km: float = REACH_KM) -> list[dict]:
    """Airfields with qualifying cells within reach: how many, how close, and the best of them. Most cells first."""
    light = goal_key(target, "lighting")
    found: dict[str, dict] = {}
    for c in cells:
        field = (access.get(c["id"]) or {}).get(key)
        if field is None or field["km"] > within_km:
            continue
        hours = score.light_hours(c["targets"][target], hemisphere, "open")
        hub = found.setdefault(field["ident"], {"ident": field["ident"], "airfield": field["name"],
                                                "place": field["municipality"], "country": field["country"],
                                                "type": field["type"], "cells": 0, "closest_km": field["km"],
                                                "most_hours": hours, "best_lighting": None, "best_cell": None,
                                                "best_cell_km": None, "best_cell_hours": None, "best_cell_periods": None,
                                                "best_shadows": None, "bare_km2": 0.0})
        hub["cells"] += 1
        hub["bare_km2"] = round(hub["bare_km2"] + (c.get("bare_km2") or 0.0), 1)
        hub["closest_km"] = min(hub["closest_km"], field["km"])
        hub["most_hours"] = max(hub["most_hours"], hours)
        shadows = c["targets"][target]["goals"].get("shadows")
        if shadows is not None and (hub["best_shadows"] is None or shadows > hub["best_shadows"]):
            hub["best_shadows"] = shadows
        value = light(c)
        if value is not None and (hub["best_lighting"] is None or (value, hours) > (hub["best_lighting"], hub["best_cell_hours"])):
            south = hemisphere == "S"
            hub.update(best_lighting=value, best_cell=c["id"], best_cell_km=field["km"], best_cell_hours=hours,
                       best_cell_periods=periods_note(c["targets"][target].get("top_bins_summer_rock") if south
                                                      else c["targets"][target].get("top_bins")))
    return sorted(found.values(), key=lambda h: (-h["cells"], h["ident"]))


def report(scored: dict, access_file: dict, min_hours: float = MIN_HOURS, reach_km: float = REACH_KM, top: int = 5,
           top_share: int = 50) -> dict:
    """Access set beside the scores, per target: counts, best sites within reach, airfields that serve them, countries."""
    cells, access = scored["cells"], access_file["cells"]
    out = {"scored_written": scored["meta"].get("written"), "access_written": access_file["meta"].get("written"),
           "min_hours": min_hours, "reach_km": reach_km, "within_km": list(WITHIN_KM),
           "ranked": {"north": len(ranked_cells(cells, "N")), "south": len(ranked_cells(cells, "S"))},
           "note": "north: distance to the nearest airfield with scheduled service; south: to the nearest airfield of any "
                   "kept type (no airfield south of 55 S has scheduled service in the table). Sites are one per 50 km. "
                   + NOT,
           "targets": {}}
    for t in scored["meta"]["targets"]:
        tid = t["id"]
        north, south = qualifying(cells, tid, "N", min_hours), qualifying(cells, tid, "S", min_hours)
        out["targets"][tid] = {
            "name": t["name"], "limit_deg": t["limit_deg"],
            "north": {
                "counts_scheduled": within_counts(north, access, "nearest_scheduled"),
                "counts_any_airfield": within_counts(north, access, "nearest"),
                "best_lighting": best_within(cells, access, tid, "N", "lighting", "nearest_scheduled", reach_km, top, min_hours),
                "best_shadows": best_within(cells, access, tid, "N", "shadows", "nearest_scheduled", reach_km, top, min_hours),
                "best_lighting_anywhere": best_within(cells, access, tid, "N", "lighting", "nearest_scheduled", None, top, None),
                "airfields": hubs(north, access, tid, "N", "nearest_scheduled", reach_km),
                "top_lighting_countries_cells": country_shares(cells, access, tid, "N", top_share),
                "top_lighting_countries_sites": country_shares(cells, access, tid, "N", top_share, sites=True),
            },
            "south": {
                "counts_any_airfield": within_counts(south, access, "nearest"),
                "best_lighting": best_within(cells, access, tid, "S", "lighting", "nearest", reach_km, top, min_hours),
                "best_shadows": best_within(cells, access, tid, "S", "shadows", "nearest", reach_km, top, min_hours),
                "best_lighting_anywhere": best_within(cells, access, tid, "S", "lighting", "nearest", None, top, None),
                "airfields": hubs(south, access, tid, "S", "nearest", reach_km),
            },
        }
    return out


def _num(value, digits: int = 0) -> str:
    return "n/a" if value is None else f"{value:,.{digits}f}"


def _site_lines(rows: list[dict]) -> list[str]:
    lines = []
    for n, r in enumerate(rows, 1):
        lines.append(f"    {n}. {r['lat']:.2f}, {r['lon']:.2f} ({r['id']}), {r['region']}, country {r['country'] or 'n/a'}: "
                     f"score {_num(r['score'], 3)} (place {r['place_among_ranked_cells']} of {r['ranked_cells_with_a_score']:,} "
                     f"ranked cells), {_num(r['hours'])} h after terrain ({_num(r['hours_flat_horizon'])} h flat horizon, "
                     f"{_num(r['clear_sky_hours'])} h typical clear sky), bare {_num(r['bare'], 2)}; "
                     f"{_num(r['airfield_km'], 1)} km from {r['airfield'] or 'no airfield within 1,500 km'}"
                     f"{' [' + r['airfield_ident'] + ', ' + str(r['airfield_country']) + ']' if r['airfield'] else ''}; "
                     f"best periods {r['best_periods']}")
    return lines or ["    none"]


def _hub_lines(rows: list[dict], most: int = 12) -> list[str]:
    lines = [f"    {h['airfield']} [{h['ident']}, {h['country']}]: {h['cells']} cells ({_num(h['bare_km2'])} km2 bare), "
             f"closest {h['closest_km']:.1f} km, most hours {_num(h['most_hours'])}, best lighting {_num(h['best_lighting'], 3)} "
             f"at {h['best_cell']} ({_num(h['best_cell_km'], 1)} km, {_num(h['best_cell_hours'])} h; {h['best_cell_periods']}), "
             f"best shadows {_num(h['best_shadows'], 3)}" for h in rows[:most]]
    if len(rows) > most:
        lines.append(f"    ... and {len(rows) - most} more airfields")
    return lines or ["    none"]


def format_report(rep: dict) -> str:
    """The report as plain text."""
    a = [f"ACCESS BESIDE THE SCORES (cells_scored.json written {rep['scored_written']}, access_cells.json written "
         f"{rep['access_written']})",
         f"Ranked cells: {rep['ranked']['north']:,} north, {rep['ranked']['south']:,} south. A cell counts when it is ranked "
         f"and has at least {rep['min_hours']:g} long-spell hours a year after terrain.",
         rep["note"], ""]
    for tid, t in rep["targets"].items():
        n, s = t["north"], t["south"]
        a.append(f"== {t['name']} (Sun at or below {t['limit_deg']} deg) ==")
        c = n["counts_scheduled"]
        a.append(f"  NORTH: {c['cells']:,} ranked cells with >= {rep['min_hours']:g} h. Within 50 / 100 / 200 km of a "
                 f"scheduled-service airfield: {c['within_km']['50']:,} / {c['within_km']['100']:,} / {c['within_km']['200']:,}"
                 f" (none within 1,500 km: {c['no_airfield_within_reach']}; not in the access file: {c['not_in_access_file']}).")
        c = n["counts_any_airfield"]
        a.append(f"         Within 50 / 100 / 200 km of any airfield: {c['within_km']['50']:,} / {c['within_km']['100']:,} / "
                 f"{c['within_km']['200']:,}.")
        a.append(f"  Best lighting sites within {rep['reach_km']:g} km of a scheduled-service airfield:")
        a += _site_lines(n["best_lighting"])
        a.append(f"  Best shadows sites (light, Moon-like slopes, bare ground) within {rep['reach_km']:g} km:")
        a += _site_lines(n["best_shadows"])
        a.append("  For comparison, the best lighting sites anywhere in the north, with their nearest scheduled-service airfield:")
        a += _site_lines(n["best_lighting_anywhere"])
        a.append(f"  Scheduled-service airfields with such cells within {rep['reach_km']:g} km ({len(n['airfields'])} airfields):")
        a += _hub_lines(n["airfields"])
        for label, key in (("cells", "top_lighting_countries_cells"), ("sites, one per 50 km", "top_lighting_countries_sites")):
            share = n[key]
            a.append(f"  Countries of the top {share['top']} lighting {label}: "
                     + (", ".join(f"{k} {v} ({share['share'][k]:.0%})" for k, v in share["cells"].items()) or "none")
                     + ("; the unknown lie in: " + ", ".join(f"{k} {v}" for k, v in share["regions_of_the_unknown"].items())
                        if share["regions_of_the_unknown"] else ""))
        c = s["counts_any_airfield"]
        a.append(f"  SOUTH (rock season only, snow not measured): {c['cells']:,} ranked cells with >= {rep['min_hours']:g} h. "
                 f"Within 50 / 100 / 200 km of any airfield: {c['within_km']['50']:,} / {c['within_km']['100']:,} / "
                 f"{c['within_km']['200']:,} (none within 1,500 km: {c['no_airfield_within_reach']}).")
        a.append(f"  Best lighting sites within {rep['reach_km']:g} km of any airfield:")
        a += _site_lines(s["best_lighting"])
        a.append(f"  Best shadows sites within {rep['reach_km']:g} km of any airfield:")
        a += _site_lines(s["best_shadows"])
        a.append(f"  Airfields with such cells within {rep['reach_km']:g} km ({len(s['airfields'])} airfields):")
        a += _hub_lines(s["airfields"])
        a.append("")
    return "\n".join(a)


# ---------------------------------------------------------------- command line

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--cells", type=Path, default=CELLS, help="the cell list (grazing_cells.json)")
    parser.add_argument("--table", type=Path, default=TABLE, help="the OurAirports airports.csv")
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--scored", type=Path, default=SCORED, help="cells_scored.json, for the report")
    parser.add_argument("--offline", action="store_true", help="never download; stop if the table is not on disk")
    parser.add_argument("--report", action="store_true", help="after building, print access beside the scores")
    parser.add_argument("--report-only", action="store_true", help="do not rebuild; print the report from the files on disk")
    parser.add_argument("--report-json", type=Path, default=None, help="also save the report's tables as JSON here")
    parser.add_argument("--min-hours", type=float, default=MIN_HOURS,
                        help="long-spell hours after terrain a cell needs to be counted in the report (default 100)")
    args = parser.parse_args(argv)

    if not args.report_only:
        started = time.time()
        note = ensure_table(args.table, offline=args.offline)
        rows, skipped = read_airfields(args.table)
        cells = json.loads(args.cells.read_text())["cells"]
        tally: dict = {}
        records = build_cells(cells, rows, tally=tally)
        meta = make_meta(rows, skipped, records, note, cells_file=args.cells.name,
                         country_withheld=tally["country_withheld"])
        write_json(args.out, {"meta": meta, "cells": records})
        counts = meta["counts"]
        print(f"{args.out}: {counts['cells']:,} cells from {meta['rows']['fixed_wing']:,} fixed-wing airfields "
              f"({meta['rows']['fixed_wing_scheduled']:,} with scheduled service) of {meta['rows']['in_table']:,} rows; "
              f"no airfield within {MAX_KM:g} km: {counts['nearest_null']}; no scheduled one: "
              f"{counts['nearest_scheduled_null']}; no country: {counts['country_null']}; {time.time() - started:.1f} s",
              file=sys.stderr)
    if args.report or args.report_only:
        rep = report(json.loads(args.scored.read_text()), json.loads(args.out.read_text()), min_hours=args.min_hours)
        print(format_report(rep))
        if args.report_json is not None:
            write_json(args.report_json, rep)
    return 0


if __name__ == "__main__":
    sys.exit(main())

# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Earthquakes, volcanoes and people near every place of the search.

Writes data/derived/hazards_people_cells.json (the Moon part: the areas of data/derived/grazing_cells.json)
and data/derived/mars_hazards_people.json (the Mars part: the squares of data/derived/mars_cells.json).

For every place, from its centre:
  - earthquakes: the number of magnitude 5 and larger earthquakes from 1990 through 2025 within 200 km, the
    largest magnitude and the date of the latest (USGS earthquake catalogue, ComCat, public domain);
  - volcanoes: the nearest volcano of the Smithsonian Global Volcanism Program's list of volcanoes active in
    the Holocene (the last ~11,700 years), its distance and the year of its last known eruption if the list
    gives one;
  - people: the nearest settlement of the GeoNames list of populated places (cities1000), the nearest with at
    least 50,000 people, and the sum of the listed population within 100 km (GeoNames, CC BY 4.0).

Every distance is a straight line along the Earth's surface (great circle), never a travel distance.

Run it again (no network needed once the raw files are on disk, about a minute):

    uv run python scripts/build_hazards_people.py --offline --report

Without --offline any raw file that is missing is downloaded (USGS: one request per calendar year, kept as
data/raw/usgs_quakes/usgs_m5_YYYY.csv; GVP: data/raw/gvp_volcanoes/holocene_volcanoes.geojson; GeoNames:
data/raw/geonames/cities1000.zip). A file already on disk is never asked for again.
Both results are written beside the old file and renamed into place.
"""
from __future__ import annotations

import argparse
import csv
import datetime
import hashlib
import http.client
import io
import json
import math
import os
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

import numpy as np

from twinfinder import fetch, reference

EARTH_RADIUS_KM = reference.EARTH_RADIUS_KM    # 6371.0, the sphere the rest of the project measures on
HALF_CIRCUMFERENCE_KM = math.pi * EARTH_RADIUS_KM

QUAKE_SERVICE = "https://earthquake.usgs.gov/fdsnws/event/1/query"
QUAKE_FIRST_YEAR, QUAKE_LAST_YEAR = 1990, 2025
QUAKE_MIN_MAG = 5.0
QUAKE_LIMIT = 20000          # the service answers at most this many events; a file that reaches it may be cut short
QUAKE_KM = 200.0
VOLCANO_WFS = ("https://webservices.volcano.si.edu/geoserver/GVP-VOTW/wfs?service=WFS&version=2.0.0&request=GetFeature"
               "&typeNames=GVP-VOTW:Smithsonian_VOTW_Holocene_Volcanoes&outputFormat=application/json")
GEONAMES_URL = "https://download.geonames.org/export/dump/cities1000.zip"
GEONAMES_README = "https://download.geonames.org/export/dump/readme.txt"
PEOPLE_KM = 100.0
CITY_POP = 50000

RAW_QUAKES = Path("data/raw/usgs_quakes")
RAW_VOLCANOES = Path("data/raw/gvp_volcanoes")
RAW_GEONAMES = Path("data/raw/geonames")
VOLCANO_FILE = RAW_VOLCANOES / "holocene_volcanoes.geojson"
GEONAMES_FILE = RAW_GEONAMES / "cities1000.zip"
DOWNLOADS_NOTE = "downloads.json"
MOON_CELLS = Path("data/derived/grazing_cells.json")
MARS_CELLS = Path("data/derived/mars_cells.json")
MOON_OUT = Path("data/derived/hazards_people_cells.json")
MARS_OUT = Path("data/derived/mars_hazards_people.json")
ATTEMPTS = 6

# GeoNames feature codes that are not a settlement of their own today, left out everywhere:
LEFT_OUT_CODES = {
    "PPLX": "section of a populated place (a district of a city; its people are already in the city's figure)",
    "PPLH": "historical populated place", "PPLQ": "abandoned populated place", "PPLW": "destroyed populated place",
    "PPLCH": "historical capital",
}

# ---------------------------------------------------------------- what each figure is not

QUAKES_NOT = (
    "Not a hazard map and not a forecast. It counts the earthquakes of magnitude 5 and above that the USGS "
    "catalogue lists from 1 January 1990 through 31 December 2025 with an epicentre within 200 km of the place's "
    "centre: 36 years of a catalogue, not the shaking a site can expect. Smaller earthquakes, which can still be "
    "felt, are not counted; depth is ignored (a deep earthquake 200 km away is counted like a shallow one); "
    "magnitudes are the catalogue's preferred value of mixed types (mw, mb, ms, ...), so 'magnitude 5' is not one "
    "scale everywhere. Events the catalogue types as anything other than 'earthquake' (nuclear explosions, "
    "volcanic eruptions, a mine collapse, a landslide) are left out.")
VOLCANO_NOT = (
    "Not a hazard map and not a forecast. It is the straight-line distance from the place's centre to the listed "
    "position (one point, usually the summit or the centre of a volcanic field) of the nearest volcano in the "
    "Smithsonian list of Holocene volcanoes. A volcanic field or a fissure system can reach far from its point. "
    "'Last eruption year' is the list's own field (negative = BCE); null means the list gives none, which is "
    "common for volcanoes whose Holocene activity is uncertain or undated, not that the volcano never erupted. "
    "Pleistocene volcanoes (older than ~11,700 years) are not in the list.")
PEOPLE_NOT = (
    "Straight-line distance, not travel time: no road, sea, ice or border is considered. A list of settlements, "
    "not a population map: GeoNames cities1000 lists places with more than 1,000 people plus seats of "
    "administrative divisions down to the third level; settlements under 1,000 people (most Arctic and many "
    "desert camps, all Antarctic stations) are not in it, so 'no settlement within 100 km' does not mean nobody "
    "lives there. 'Population within 100 km' is the sum of the populations the list gives for the settlements "
    "whose point lies within 100 km: a whole town counts if its point is inside, none of it if outside; the "
    "figures are of mixed years; a municipality's figure can cover land far from its point; listed places with "
    "no population figure are counted apart (settlements_without_population_within_100km), never as 0. City "
    "sections (PPLX) and abandoned, destroyed or historical places are left out.")


# ---------------------------------------------------------------- distance

def great_circle_km(lat1, lon1, lat2, lon2):
    """Distance along the great circle between points given in degrees, on a sphere of radius 6371.0 km (haversine).

    Takes numbers or arrays that broadcast against each other; a number in gives a float out.
    """
    p1, p2 = np.radians(np.asarray(lat1, dtype=float)), np.radians(np.asarray(lat2, dtype=float))
    dl = np.radians(np.asarray(lon2, dtype=float) - np.asarray(lon1, dtype=float))
    a = np.sin((p2 - p1) / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    km = 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))
    return float(km) if np.ndim(km) == 0 else km


def cap_extent(lat: float, km: float) -> tuple[float, float, float | None]:
    """Latitude range and half-width in longitude (degrees) of the circle of radius km around a point at lat.

    The half-width is None when the circle reaches a pole: then every longitude is inside the range.
    For a circle of angular radius a around latitude p that holds no pole, the widest longitude is
    asin(sin a / cos p) from the centre (exact on the sphere).
    """
    a = km / EARTH_RADIUS_KM
    lo, hi = lat - math.degrees(a), lat + math.degrees(a)
    if hi >= 90.0 or lo <= -90.0 or a >= math.pi / 2:
        return lo, hi, None
    ratio = math.sin(a) / math.cos(math.radians(lat))
    if ratio >= 1.0:
        return lo, hi, None
    return lo, hi, math.degrees(math.asin(ratio))


class GridIndex:
    """Points sorted into cells of cell_deg by cell_deg degrees, so a search reads only the cells a circle can reach.

    within(lat, lon, km) gives the indices of every point within km (exact: the cells only narrow the
    candidates, the great-circle distance decides). nearest(lat, lon) widens a circle from start_km,
    doubling, until it holds a point, then returns the closest one; the circle grows to the whole globe
    if needed, so a point is always found when there is one.
    """

    def __init__(self, lat, lon, cell_deg: float = 1.0):
        self.lat = np.asarray(lat, dtype=float)
        self.lon = np.asarray(lon, dtype=float)
        self.cell = float(cell_deg)
        self.nrow = int(math.ceil(180.0 / self.cell))
        self.ncol = int(math.ceil(360.0 / self.cell))
        keys = self._row(self.lat) * self.ncol + self._col(self.lon)
        self.order = np.argsort(keys, kind="stable")
        sorted_keys = keys[self.order]
        self.start = np.searchsorted(sorted_keys, np.arange(self.nrow * self.ncol), side="left")
        self.end = np.searchsorted(sorted_keys, np.arange(self.nrow * self.ncol), side="right")

    def _row(self, lat):
        return np.clip(np.floor((np.asarray(lat, dtype=float) + 90.0) / self.cell).astype(int), 0, self.nrow - 1)

    def _col(self, lon):
        return np.floor((np.asarray(lon, dtype=float) + 180.0) / self.cell).astype(int) % self.ncol

    def candidates(self, lat: float, lon: float, km: float) -> np.ndarray:
        if self.lat.size == 0:
            return np.zeros(0, dtype=int)
        lo, hi, dlon = cap_extent(lat, km)
        rows = range(int(self._row(max(lo, -90.0))), int(self._row(min(hi, 90.0))) + 1)
        if dlon is None or 2 * dlon >= 360.0 - 2 * self.cell:
            cols = range(self.ncol)
        else:
            c0 = int(math.floor((lon - dlon + 180.0) / self.cell))
            c1 = int(math.floor((lon + dlon + 180.0) / self.cell))
            cols = sorted({c % self.ncol for c in range(c0, c1 + 1)})
        parts = []
        for r in rows:
            base = r * self.ncol
            if len(cols) == self.ncol:
                s, e = self.start[base], self.end[base + self.ncol - 1]
                if e > s:
                    parts.append(self.order[s:e])
                continue
            for c in cols:
                s, e = self.start[base + c], self.end[base + c]
                if e > s:
                    parts.append(self.order[s:e])
        return np.concatenate(parts) if parts else np.zeros(0, dtype=int)

    def within(self, lat: float, lon: float, km: float, return_km: bool = False):
        idx = self.candidates(lat, lon, km)
        d = great_circle_km(lat, lon, self.lat[idx], self.lon[idx]) if idx.size else np.zeros(0)
        keep = d <= km
        return (idx[keep], d[keep]) if return_km else idx[keep]

    def nearest(self, lat: float, lon: float, start_km: float = 25.0) -> tuple[int, float | None]:
        if self.lat.size == 0:
            return -1, None
        km = start_km
        while True:
            idx, d = self.within(lat, lon, km, return_km=True)
            if idx.size:
                best = int(np.argmin(d))
                return int(idx[best]), float(d[best])
            if km > HALF_CIRCUMFERENCE_KM:   # the whole globe was searched (cannot happen with points present)
                return -1, None
            km *= 2.0


# ---------------------------------------------------------------- downloads

def now_utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def download(url: str, dest: Path) -> dict:
    """Fetch url to dest with the project's User-Agent and nothing else, retrying a dropped connection."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    request = urllib.request.Request(url, headers={"User-Agent": fetch.USER_AGENT})
    for attempt in range(1, ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(request, timeout=300) as response, open(part, "wb") as out:
                shutil.copyfileobj(response, out)
                expected = response.headers.get("Content-Length")
            if expected is not None and part.stat().st_size != int(expected):
                raise ConnectionError(f"short body from {url}")
            break
        except urllib.error.HTTPError as error:
            part.unlink(missing_ok=True)
            if error.code < 500 or attempt == ATTEMPTS:
                raise
        except (urllib.error.URLError, ConnectionError, TimeoutError, http.client.IncompleteRead):
            part.unlink(missing_ok=True)
            if attempt == ATTEMPTS:
                raise
        time.sleep(10.0 * attempt)
    os.replace(part, dest)
    return {"url": url, "file": dest.name, "fetched_utc": now_utc(), "bytes": dest.stat().st_size, "sha256": sha256_of(dest)}


def read_notes(folder: Path) -> dict:
    path = folder / DOWNLOADS_NOTE
    return json.loads(path.read_text()) if path.exists() else {}


def ensure(url: str, dest: Path, offline: bool) -> dict:
    """The download note of dest, fetching it first when it is missing (never twice)."""
    notes = read_notes(dest.parent)
    if not dest.exists():
        if offline:
            raise FileNotFoundError(f"{dest} is missing and --offline forbids the download")
        notes[dest.name] = download(url, dest)
        write_json(dest.parent / DOWNLOADS_NOTE, notes)
    if dest.name not in notes:
        stamp = datetime.datetime.fromtimestamp(dest.stat().st_mtime, datetime.timezone.utc)
        notes[dest.name] = {"url": url, "file": dest.name, "fetched_utc": stamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
                            "note": "fetched with curl from this URL with the same User-Agent before the script "
                                    "existed; the time is the file's own"}
        if not offline:
            write_json(dest.parent / DOWNLOADS_NOTE, notes)
    note = dict(notes[dest.name])
    note["bytes"], note["sha256"] = dest.stat().st_size, sha256_of(dest)
    return note


def year_spans(first: int = QUAKE_FIRST_YEAR, last: int = QUAKE_LAST_YEAR) -> list[tuple[str, str]]:
    """One span per calendar year, start and end both inclusive (the service's starttime and endtime are)."""
    return [(f"{y}-01-01T00:00:00", f"{y}-12-31T23:59:59.999") for y in range(first, last + 1)]


def quake_url(start: str, end: str) -> str:
    query = {"format": "csv", "starttime": start, "endtime": end, "minmagnitude": f"{QUAKE_MIN_MAG:g}",
             "orderby": "time-asc"}
    return QUAKE_SERVICE + "?" + urllib.parse.urlencode(query, safe=":")


def quake_files(offline: bool) -> tuple[list[Path], list[dict]]:
    paths, notes = [], []
    for start, end in year_spans():
        dest = RAW_QUAKES / f"usgs_m5_{start[:4]}.csv"
        notes.append(ensure(quake_url(start, end), dest, offline))
        paths.append(dest)
    return paths, notes


# ---------------------------------------------------------------- the earthquake catalogue

def read_quakes(paths, limit: int = QUAKE_LIMIT, min_mag: float = QUAKE_MIN_MAG) -> tuple[dict, dict]:
    """Earthquakes of magnitude min_mag and above from the USGS CSV files, each event once (by its id).

    Returns arrays id, lat, lon, mag, date (YYYY-MM-DD, UTC), place; and a tally of what was left out.
    A file with limit rows or more may have been cut short by the service, so it is refused.
    """
    seen: dict[str, dict] = {}
    tally = {"rows": 0, "duplicates": 0, "below_magnitude": 0, "without_position_or_magnitude": 0,
             "not_earthquake": {}}
    for path in paths:
        with open(path, newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        if len(rows) >= limit:
            raise ValueError(f"{path} holds {len(rows)} rows, the service limit: the answer may be cut short; ask in "
                             "shorter spans")
        for row in rows:
            tally["rows"] += 1
            kind = (row.get("type") or "").strip()
            if kind != "earthquake":
                tally["not_earthquake"][kind or "(blank)"] = tally["not_earthquake"].get(kind or "(blank)", 0) + 1
                continue
            try:
                lat, lon, mag = float(row["latitude"]), float(row["longitude"]), float(row["mag"])
            except (TypeError, ValueError):
                tally["without_position_or_magnitude"] += 1
                continue
            if mag < min_mag:
                tally["below_magnitude"] += 1
                continue
            if row["id"] in seen:
                tally["duplicates"] += 1
                continue
            seen[row["id"]] = {"id": row["id"], "lat": lat, "lon": lon, "mag": mag, "date": row["time"][:10],
                               "place": row.get("place") or ""}
    tally["not_earthquake"] = dict(sorted(tally["not_earthquake"].items()))
    events = sorted(seen.values(), key=lambda e: (e["date"], e["id"]))
    arrays = {"id": np.array([e["id"] for e in events], dtype=object),
              "lat": np.array([e["lat"] for e in events], dtype=float),
              "lon": np.array([e["lon"] for e in events], dtype=float),
              "mag": np.array([e["mag"] for e in events], dtype=float),
              "date": np.array([e["date"] for e in events], dtype=object),
              "place": np.array([e["place"] for e in events], dtype=object)}
    tally["kept"] = len(events)
    return arrays, tally


def quake_summary(index: GridIndex, events: dict, lat: float, lon: float, km: float = QUAKE_KM) -> dict:
    """Count, largest and latest of the catalogue's earthquakes within km of the point. None nearby: 0 and nulls."""
    idx, d = index.within(lat, lon, km, return_km=True)
    if idx.size == 0:
        return {"count": 0, "largest_mag": None, "largest_date": None, "latest_date": None, "latest_mag": None,
                "nearest_km": None}
    mags, dates = events["mag"][idx], events["date"][idx]
    big = int(np.lexsort((dates, -mags))[0])            # largest magnitude; equal ones: the earliest
    late = max(range(idx.size), key=lambda k: (dates[k], mags[k]))
    return {"count": int(idx.size), "largest_mag": round(float(mags[big]), 2), "largest_date": str(dates[big]),
            "latest_date": str(dates[late]), "latest_mag": round(float(mags[late]), 2),
            "nearest_km": round(float(d.min()), 1)}


# ---------------------------------------------------------------- the volcano list

def read_volcanoes(path: Path) -> list[dict]:
    """The Holocene volcanoes of the GVP GeoJSON answer. Refused if the answer holds fewer than it says it matched."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    features = data["features"]
    matched = data.get("numberMatched")
    if matched is not None and int(matched) != len(features):
        raise ValueError(f"{path}: {len(features)} features but numberMatched {matched}: a partial answer")
    out = []
    for f in features:
        p = f["properties"]
        lon, lat = f["geometry"]["coordinates"][:2] if f.get("geometry") else (p["Longitude"], p["Latitude"])
        last = p.get("Last_Eruption_Year")
        out.append({"number": p.get("Volcano_Number"), "name": p.get("Volcano_Name"), "country": p.get("Country"),
                    "lat": float(lat), "lon": float(lon),
                    "last_eruption_year": None if last is None else int(last),
                    "evidence": p.get("Evidence_Category"), "type": p.get("Primary_Volcano_Type")})
    return out


def volcano_summary(index: GridIndex, volcanoes: list[dict], lat: float, lon: float) -> dict | None:
    i, km = index.nearest(lat, lon)
    if i < 0:
        return None
    v = volcanoes[i]
    return {"name": v["name"], "number": v["number"], "country": v["country"], "km": round(km, 1),
            "last_eruption_year": v["last_eruption_year"], "evidence": v["evidence"], "type": v["type"],
            "lat": round(v["lat"], 3), "lon": round(v["lon"], 3)}


# ---------------------------------------------------------------- the settlements

GEONAMES_COLUMNS = ["geonameid", "name", "asciiname", "alternatenames", "latitude", "longitude", "feature_class",
                    "feature_code", "country_code", "cc2", "admin1", "admin2", "admin3", "admin4", "population",
                    "elevation", "dem", "timezone", "modified"]


def read_settlements(path: Path) -> tuple[list[dict], dict]:
    """The settlements of cities1000.zip, without the codes of LEFT_OUT_CODES. A population of 0 is unknown: None."""
    places, left_out, rows = [], {}, 0
    with zipfile.ZipFile(path) as z:
        with z.open("cities1000.txt") as raw:
            for line in io.TextIOWrapper(raw, encoding="utf-8"):
                cols = line.rstrip("\n").split("\t")
                if len(cols) < len(GEONAMES_COLUMNS):
                    continue
                rows += 1
                code = cols[7]
                if code in LEFT_OUT_CODES:
                    left_out[code] = left_out.get(code, 0) + 1
                    continue
                pop = int(cols[14]) if cols[14].strip() else 0
                places.append({"name": cols[1], "country": cols[8] or None, "lat": float(cols[4]), "lon": float(cols[5]),
                               "population": pop if pop > 0 else None, "code": code, "geonameid": int(cols[0])})
    return places, {"rows": rows, "left_out": dict(sorted(left_out.items())), "kept": len(places),
                    "kept_without_population": sum(p["population"] is None for p in places)}


def settlement_indexes(places: list[dict], city_pop: int = CITY_POP) -> dict:
    lat = np.array([p["lat"] for p in places], dtype=float)
    lon = np.array([p["lon"] for p in places], dtype=float)
    pop = np.array([p["population"] or 0 for p in places], dtype=float)
    known = np.array([p["population"] is not None for p in places], dtype=bool)
    cities = np.flatnonzero(pop >= city_pop)
    return {"all": GridIndex(lat, lon), "pop": pop, "known": known, "cities": cities,
            "city": GridIndex(lat[cities], lon[cities])}


def settlement_record(p: dict, km: float) -> dict:
    return {"name": p["name"], "country": p["country"], "population": p["population"], "km": round(km, 1),
            "lat": round(p["lat"], 4), "lon": round(p["lon"], 4)}


def people_summary(ix: dict, places: list[dict], lat: float, lon: float, km: float = PEOPLE_KM,
                   city_pop: int = CITY_POP) -> dict:
    i, d = ix["all"].nearest(lat, lon)
    j, dj = ix["city"].nearest(lat, lon)
    near = ix["all"].within(lat, lon, km)
    known_near = int(ix["known"][near].sum())
    # none listed: a real 0; listed but none with a figure: unknown (null); some without a figure: a lower bound
    total = 0 if near.size == 0 else (int(ix["pop"][near].sum()) if known_near else None)
    return {"nearest": settlement_record(places[i], d) if i >= 0 else None,
            "nearest_city_50k": settlement_record(places[int(ix["cities"][j])], dj) if j >= 0 else None,
            "population_within_100km": total,
            "settlements_within_100km": int(near.size),
            "settlements_without_population_within_100km": int((~ix["known"][near]).sum())}


# ---------------------------------------------------------------- the records

def build_records(places: list[dict], events: dict, volcanoes: list[dict], settlements: list[dict]) -> dict:
    """The record of every place (id, lat, lon): quakes_m5_200km, volcano, people."""
    q_index = GridIndex(events["lat"], events["lon"])
    v_index = GridIndex(np.array([v["lat"] for v in volcanoes], dtype=float),
                        np.array([v["lon"] for v in volcanoes], dtype=float), cell_deg=2.0)
    s_index = settlement_indexes(settlements)
    out = {}
    for p in places:
        lat, lon = float(p["lat"]), float(p["lon"])
        out[p["id"]] = {"quakes_m5_200km": quake_summary(q_index, events, lat, lon),
                        "volcano": volcano_summary(v_index, volcanoes, lat, lon),
                        "people": people_summary(s_index, settlements, lat, lon)}
    return out


def counts(records: dict) -> dict:
    values = list(records.values())
    people = [v["people"] for v in values]
    return {"places": len(values),
            "with_an_m5_quake_within_200km": sum(v["quakes_m5_200km"]["count"] > 0 for v in values),
            "volcano_within_100km": sum(v["volcano"] is not None and v["volcano"]["km"] <= 100 for v in values),
            "volcano_within_300km": sum(v["volcano"] is not None and v["volcano"]["km"] <= 300 for v in values),
            "no_settlement_within_100km": sum(p["nearest"] is None or p["nearest"]["km"] > PEOPLE_KM for p in people),
            "no_settlement_within_50km": sum(p["nearest"] is None or p["nearest"]["km"] > 50 for p in people),
            "no_city_50k_within_500km": sum(p["nearest_city_50k"] is None or p["nearest_city_50k"]["km"] > 500
                                            for p in people)}


def make_meta(part: str, cells_file: Path, records: dict, quake_tally: dict, quake_notes: list[dict],
              volcanoes: list[dict], volcano_note: dict, settle_tally: dict, geonames_note: dict) -> dict:
    point = ("the area centre (lat and lon of the area's record in grazing_cells.json); an area is about 11 km "
             "across, so a distance from any point of it differs by up to about 8 km" if part == "moon" else
             "the square centre (lat and lon of the square's record in mars_cells.json); a square is half a degree "
             "(about 55 km north-south, less east-west away from the equator), so a distance from any point of it "
             "differs by up to about 40 km, and a 100 or 200 km circle from the centre is not the square")
    return {
        "written": datetime.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z"),
        "made_by": "agent HAZARDS-PEOPLE, scripts/build_hazards_people.py",
        "part": part,
        "places_from": str(cells_file),
        "place_point": point,
        "what_this_is": "For every place: earthquakes of magnitude 5 and above within 200 km (1990-2025), the nearest "
                        "volcano of the Holocene list, and the settlements nearby. Facts from three public lists, "
                        "measured from the place's centre along the great circle; read beside the light ranking, "
                        "not part of it.",
        "what_this_is_not": {"quakes_m5_200km": QUAKES_NOT, "volcano": VOLCANO_NOT, "people": PEOPLE_NOT},
        "distance": "great circle on a sphere of radius 6371.0 km (haversine); against the real ellipsoid within "
                    "about 0.5 percent",
        "search": "a grid index (cells of 1 degree, 2 degrees for the volcanoes) narrows the candidates; every kept "
                  "point is decided by its great-circle distance, and the nearest-point search widens until it "
                  "finds one, up to the whole globe, so no distance is capped",
        "record": {
            "quakes_m5_200km": {"count": "earthquakes within 200 km (0 is a real zero: none listed)",
                                "largest_mag": "largest magnitude among them, or null", "largest_date": "its UTC date",
                                "latest_date": "UTC date of the most recent one, or null", "latest_mag": "its magnitude",
                                "nearest_km": "distance to the closest epicentre among them, or null"},
            "volcano": {"name": "GVP volcano name", "number": "GVP volcano number", "country": "as the list gives",
                        "km": "great-circle km to the volcano's listed point", "last_eruption_year":
                        "the list's Last_Eruption_Year (negative = BCE), or null when the list gives none",
                        "evidence": "the list's Evidence_Category", "type": "the list's Primary_Volcano_Type",
                        "lat": "volcano latitude", "lon": "volcano longitude"},
            "people": {"nearest": "nearest listed settlement (any population figure, or none given) with km",
                       "nearest_city_50k": "nearest listed settlement with a population of at least 50,000, with km",
                       "population_within_100km": "sum of the listed populations within 100 km: 0 when no settlement "
                                                  "is listed there, null when some are listed but none gives a "
                                                  "figure, and a lower bound when only some lack one (see "
                                                  "settlements_without_population_within_100km)",
                       "settlements_within_100km": "how many listed settlements lie within 100 km",
                       "settlements_without_population_within_100km": "how many of them have no population figure",
                       "settlement_fields": {"population": "the list's figure, or null when it gives 0 (unknown)"}},
        },
        "sources": {
            "earthquakes": {
                "name": "USGS ANSS Comprehensive Earthquake Catalog (ComCat), FDSN event web service",
                "service": QUAKE_SERVICE, "documentation": "https://earthquake.usgs.gov/fdsnws/event/1/ (copy: "
                "data/raw/usgs_quakes/fdsnws_event_1_documentation.html)",
                "query": f"format=csv, minmagnitude={QUAKE_MIN_MAG:g}, one request per calendar year "
                         f"{QUAKE_FIRST_YEAR}-{QUAKE_LAST_YEAR} (start and end inclusive, UTC); the service answers "
                         "at most 20,000 events per request (each year held under 2,000) and its documentation names "
                         "731 days as a possible future limit for whole-world requests",
                "licence": "U.S. public domain",
                "licence_statement": "USGS-authored or produced data and information are considered to be in the U.S. "
                                     "Public Domain. (usgs.gov, Copyrights and Credits; copy: "
                                     "data/raw/usgs_quakes/usgs_copyrights_and_credits.html)",
                "credit": "Credit: U.S. Geological Survey (the form the USGS page asks for)",
                "raw_folder": str(RAW_QUAKES), "files": quake_notes, "tally": quake_tally},
            "volcanoes": {
                "name": "Smithsonian Institution, Global Volcanism Program: Volcanoes of the World, Holocene volcano "
                        "list (layer GVP-VOTW:Smithsonian_VOTW_Holocene_Volcanoes of the GVP GeoServer web feature "
                        "service)",
                "service": VOLCANO_WFS, "raw_folder": str(RAW_VOLCANOES), "file": volcano_note,
                "volcanoes": len(volcanoes),
                "without_last_eruption_year": sum(v["last_eruption_year"] is None for v in volcanoes),
                "licence": VOLCANO_TERMS["licence"], "terms_of_use": VOLCANO_TERMS["terms"],
                "credit": VOLCANO_TERMS["credit"]},
            "people": {
                "name": "GeoNames gazetteer, cities1000 (populated places)", "url": GEONAMES_URL,
                "readme": GEONAMES_README + " (copy: data/raw/geonames/readme.txt)",
                "licence": "CC BY 4.0",
                "licence_statement": "This work is licensed under a Creative Commons Attribution 4.0 License, see "
                                     "https://creativecommons.org/licenses/by/4.0/ (first lines of the readme)",
                "credit": "GeoNames (geonames.org), CC BY 4.0",
                "file_description": "cities1000.zip: all cities with a population > 1000 or seats of adm div down "
                                    "to PPLA3 (the readme's words); so a few listed places have fewer than 1,000 "
                                    "people or no figure",
                "left_out_codes": LEFT_OUT_CODES,
                "raw_folder": str(RAW_GEONAMES), "file": geonames_note, "tally": settle_tally},
        },
        "radii_km": {"quakes": QUAKE_KM, "people": PEOPLE_KM}, "city_population": CITY_POP,
        "counts": counts(records),
        "null_rule": "unknown is null, never 0; a count of 0 means the list holds none within the radius",
        "rerun": "uv run python scripts/build_hazards_people.py --offline --report",
    }


# Filled from what could be read on 14 November 2026; see the meta and the report of agent HAZARDS-PEOPLE.
VOLCANO_TERMS = {
    "licence": "not stated in the web service answer or its capabilities document (Fees: NONE, AccessConstraints: "
               "NONE); the GVP website, which holds the terms of use, could not be read tonight",
    "terms": "volcano.si.edu answered 403 'Smithsonian site temporarily unavailable' on every try on 14 November 2026 "
             "(05:12-05:40 UTC), and si.edu/termsofuse asked for a browser verification, which was not attempted: "
             "the terms of use and the exact citation of the current database version were NOT read. To be "
             "checked before publishing.",
    "credit": "Global Volcanism Program, Smithsonian Institution, Volcanoes of the World database (the GVP asks to "
              "be cited as 'Global Volcanism Program, <year>. [Database] Volcanoes of the World (v. <version>; "
              "<date>). Distributed by Smithsonian Institution, compiled by Venzke, E.' with a DOI; the version, "
              "date and DOI of this download were not read and are to be filled in)",
}


def write_json(path: Path, value) -> None:
    """Write beside the file and rename into place, so a reader never sees half a file. NaN is refused."""
    path = Path(path)
    side = path.with_name(path.name + ".part")
    try:
        side.write_text(json.dumps(value, separators=(",", ":"), allow_nan=False, ensure_ascii=False), encoding="utf-8")
    except ValueError:
        side.unlink(missing_ok=True)
        raise
    os.replace(side, path)


# ---------------------------------------------------------------- the report

NAMED = [  # (label, part, id or None, lat, lon): with an id the place is that record; else the nearest record
    ("Haughton crater, Devon Island", "moon", "75.3_-90.0", None, None),
    ("Haughton crater, Devon Island", "mars", "m_75.25_-89.75", None, None),
    ("south-west Iceland", "moon", "63.8_-22.6", None, None),
    ("Pechora Sea coast", "moon", "68.9_54.3", None, None),
    ("near Ulukhaktok", "moon", None, 70.736, -117.770),
    ("McMurdo Dry Valleys", "moon", None, -77.47, 162.52),
    ("McMurdo Dry Valleys", "mars", "m_-77.25_162.75", None, None),
    ("Atacama near Yungay", "mars", "m_-24.25_-69.75", None, None),
    ("Tibetan Plateau", "mars", None, 33.0, 88.0),
]


def nearest_place(places: list[dict], lat: float, lon: float) -> dict:
    plat = np.array([p["lat"] for p in places]); plon = np.array([p["lon"] for p in places])
    return places[int(np.argmin(great_circle_km(lat, lon, plat, plon)))]


def report_rows(sets: dict) -> list[dict]:
    rows = []
    for label, part, pid, lat, lon in NAMED:
        places, records = sets[part]
        if pid is None:
            p = nearest_place(places, lat, lon)
            pid, how = p["id"], f"the {part} record nearest to {lat}, {lon} ({great_circle_km(lat, lon, p['lat'], p['lon']):.1f} km away)"
        else:
            how = "the named record"
        r = records.get(pid)
        rows.append({"label": label, "part": part, "id": pid, "how": how, "record": r})
    return rows


def format_rows(rows: list[dict]) -> str:
    out = []
    for row in rows:
        r = row["record"]
        if r is None:
            out.append(f"{row['label']} [{row['part']} {row['id']}]: not in the file")
            continue
        q, v, p = r["quakes_m5_200km"], r["volcano"], r["people"]
        quake = (f"{q['count']} M5+ earthquakes within 200 km 1990-2025" +
                 (f", largest M{q['largest_mag']} on {q['largest_date']}, latest {q['latest_date']} (M{q['latest_mag']})"
                  if q["count"] else ""))
        volc = (f"nearest Holocene volcano {v['name']} ({v['country']}) {v['km']:,.1f} km, last eruption "
                f"{'unknown' if v['last_eruption_year'] is None else v['last_eruption_year']}") if v else "no volcano"
        n, c = p["nearest"], p["nearest_city_50k"]
        ppl = (f"nearest settlement {n['name']} ({n['country']}, pop {n['population'] if n['population'] is not None else 'n/a'}) "
               f"{n['km']:,.1f} km; nearest 50k city {c['name']} ({c['country']}) {c['km']:,.1f} km; "
               f"{'unknown' if p['population_within_100km'] is None else format(p['population_within_100km'], ',')} "
               f"people listed within 100 km in {p['settlements_within_100km']} settlements")
        out.append(f"{row['label']} [{row['part']} {row['id']}; {row['how']}]:\n    {quake};\n    {volc};\n    {ppl}")
    return "\n".join(out)


# ---------------------------------------------------------------- command line

def load_places(part: str, path: Path) -> list[dict]:
    cells = json.loads(path.read_text())["cells"]
    values = cells.values() if isinstance(cells, dict) else cells
    return [{"id": c["id"], "lat": c["lat"], "lon": c["lon"]} for c in values]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--offline", action="store_true", help="never download; stop if a raw file is missing")
    parser.add_argument("--fetch-only", action="store_true", help="download what is missing, build nothing")
    parser.add_argument("--report", action="store_true", help="print the figures at the named places")
    parser.add_argument("--report-json", type=Path, default=None, help="also save the named places as JSON")
    args = parser.parse_args(argv)

    started = time.time()
    quake_paths, quake_notes = quake_files(args.offline)
    volcano_note = ensure(VOLCANO_WFS, VOLCANO_FILE, args.offline)
    geonames_note = ensure(GEONAMES_URL, GEONAMES_FILE, args.offline)
    ensure(GEONAMES_README, RAW_GEONAMES / "readme.txt", args.offline)
    if args.fetch_only:
        return 0
    events, quake_tally = read_quakes(quake_paths)
    volcanoes = read_volcanoes(VOLCANO_FILE)
    settlements, settle_tally = read_settlements(GEONAMES_FILE)
    print(f"{quake_tally['kept']:,} earthquakes, {len(volcanoes):,} volcanoes, {len(settlements):,} settlements "
          f"({time.time() - started:.1f} s)", file=sys.stderr)
    sets = {}
    for part, cells_file, out in (("moon", MOON_CELLS, MOON_OUT), ("mars", MARS_CELLS, MARS_OUT)):
        places = load_places(part, cells_file)
        records = build_records(places, events, volcanoes, settlements)
        meta = make_meta(part, cells_file, records, quake_tally, quake_notes, volcanoes, volcano_note, settle_tally,
                         geonames_note)
        write_json(out, {"meta": meta, "cells": records})
        sets[part] = (places, records)
        print(f"{out}: {len(records):,} places; {json.dumps(meta['counts'])} ({time.time() - started:.1f} s)",
              file=sys.stderr)
    if args.report or args.report_json:
        rows = report_rows(sets)
        print(format_rows(rows))
        for part in ("moon", "mars"):
            c = counts(sets[part][1])
            print(f"{part} part: {c['no_settlement_within_100km']:,} of {c['places']:,} places have no listed settlement "
                  f"within 100 km")
        if args.report_json:
            write_json(args.report_json, rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())

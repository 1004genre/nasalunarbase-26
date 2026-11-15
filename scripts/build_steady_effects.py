# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""What volcanoes and people steadily do to a place, and a rough small-tremor guess where the catalogue is blind.

Not the risk of a rare event (an eruption, a disaster): what is present at a place week after week and gets in
the way of field work and instruments, or helps it.

Writes data/derived/steady_effects_cells.json (the Moon part: the areas of data/derived/grazing_cells.json) and
data/derived/mars_steady_effects.json (the Mars part: the squares of data/derived/mars_cells.json). For every
place, from its centre, three results, each a class in plain words plus the figures behind it:

  volcanic       steady volcanic presence (an erupting volcano close by), and "young volcanic ground";
  human          steady human disturbance (towns, main roads and railways, airfields), and "help within reach";
  small_tremors  the small-tremor verdict of data/derived/tremors_cells.json where the catalogue can see small
                 tremors, and our rough estimate where it cannot.

Every rule is in RULES just below; the same table, in words, goes into the meta of both outputs.

Run it again (no network needed once the raw files are on disk, about two minutes):

    uv run python scripts/build_steady_effects.py --offline --report

Without --offline any raw file that is missing is downloaded once and kept (data/raw/gvp_eruptions/,
data/raw/naturalearth_roads/; the volcano list, GeoNames and OurAirports files already in data/raw/ are
reused). Both results are written beside the old file and renamed into place.
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
import urllib.request
import zipfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from twinfinder import fetch, reference  # noqa: E402

# ================================================================ THE RULES (one table; the code reads its numbers)
#
# Each row: (result, outcome, words, numbers). The words are filled from the numbers, so the meta and the code
# can never disagree. Rows of one result are tried from the top; the first whose test holds is the class.

SINCE = 1990          # "erupted since 1990": a confirmed eruption in progress in 1990 or any later year
RECENT = 2015         # "erupted at any time since 2015"

VOLCANIC_EFFECTS = [
    "gas and volcanic haze that can corrode and fog instruments and optics",
    "fine ash and abrasive dust on the ground and in the air",
    "warm or steaming ground that upsets temperature readings",
    "small volcanic tremors",
    "closures of the area when it erupts",
]
HUMAN_EFFECTS = [
    "vibration from vehicles and aircraft",
    "radio noise",
    "dust raised by traffic",
    "artificial light",
    "tracks and litter in camera views",
]

RULES = [
    # ---- A. volcanic influence, as a steady presence
    ("volcanic", "steady volcanic effects likely",
     "a volcano that erupted in {min_years} or more separate years since {since}, or at any time since {recent}, "
     "lies within {km:g} km of the place's centre",
     {"km": 30.0, "min_years": 3, "since": SINCE, "recent": RECENT, "effects": VOLCANIC_EFFECTS}),
    ("volcanic", "volcanic effects come and go",
     "a volcano that erupted since {since} lies within {km:g} km",
     {"km": 100.0, "since": SINCE, "effects": VOLCANIC_EFFECTS}),
    ("volcanic", "none expected", "otherwise", {"effects": []}),
    ("volcanic", "young volcanic ground (useful side, yes or no)",
     "yes when a Holocene volcano (active in the last ~11,700 years, any date) lies within {km:g} km and the rock map "
     "(data/derived/rock_frozen_cells.json or mars_rock_frozen.json, when present) calls the place's rock volcanic; "
     "no when there is no such volcano within {km:g} km or the rock map says the rock is not volcanic; null when a "
     "volcano is that close but the rock map gives no class. Fresh lava and ash are a good stand-in for the basalt "
     "soil of the Moon's dark plains and of Mars",
     {"km": 50.0}),
    # ---- B. human influence, as a steady presence
    ("human", "steady human disturbance likely",
     "a listed settlement of {pop:,} or more people lies within {settlement_km:g} km, or a main road or railway "
     "within {road_km:g} km, or an airfield with scheduled flights within {scheduled_km:g} km",
     {"pop": 1000, "settlement_km": 5.0, "road_km": 2.0, "scheduled_km": 10.0, "effects": HUMAN_EFFECTS}),
    ("human", "human disturbance possible",
     "a listed settlement of any size lies within {settlement_km:g} km, or a main road or railway within "
     "{road_km:g} km, or an airfield of any kind within {airfield_km:g} km",
     {"settlement_km": 25.0, "road_km": 10.0, "airfield_km": 10.0, "effects": HUMAN_EFFECTS}),
    ("human", "undisturbed as far as our lists show", "otherwise", {"effects": []}),
    ("human", "help within reach (useful side, yes or no)",
     "yes when a listed settlement of {pop:,} or more lies within {settlement_km:g} km or an airfield with "
     "scheduled flights within {scheduled_km:g} km (power, shelter, rescue); no otherwise",
     {"pop": 1000, "settlement_km": 50.0, "scheduled_km": 100.0}),
    # ---- C. small tremors where the catalogue is blind (our estimate; the catalogue's verdict is kept elsewhere)
    ("small_tremors", "small tremors likely",
     "a volcano that erupted since {since} lies within {volcano_km:g} km, or at least {m5_min} earthquakes of "
     "magnitude 5 or more were catalogued within {m5_km:g} km since {since}",
     {"volcano_km": 50.0, "since": SINCE, "m5_min": 5, "m5_km": 200.0}),
    ("small_tremors", "small tremors possible",
     "a Holocene volcano of any date lies within {volcano_km:g} km, or {m5_low} to {m5_high} earthquakes of "
     "magnitude 5 or more within {m5_km:g} km since {since}, or glacier ice covers {ice_share:.0%} or more of the "
     "area's land (moving ice makes small quakes)",
     {"volcano_km": 100.0, "m5_low": 1, "m5_high": 4, "m5_km": 200.0, "since": SINCE, "ice_share": 0.10}),
    ("small_tremors", "small tremors unlikely", "otherwise", {}),
]

DISCLAIMER = "A rough guide by our own rule of thumb. It is not a measurement."


def rule(result: str, outcome_start: str) -> dict:
    for r, outcome, _words, numbers in RULES:
        if r == result and outcome.startswith(outcome_start):
            return numbers
    raise KeyError((result, outcome_start))


def rules_in_words() -> list[dict]:
    out = []
    for result, outcome, words, numbers in RULES:
        fill = {k: v for k, v in numbers.items() if not isinstance(v, list)}
        row = {"result": result, "outcome": outcome, "when": words.format(**fill)}
        if numbers.get("effects"):
            row["what_the_effects_are"] = numbers["effects"]
        out.append(row)
    return out


# ================================================================ sources and files

EARTH_RADIUS_KM = reference.EARTH_RADIUS_KM    # 6371.0, the sphere the rest of the project measures on
HALF_CIRCUMFERENCE_KM = math.pi * EARTH_RADIUS_KM

GVP_WFS = "https://webservices.volcano.si.edu/geoserver/GVP-VOTW/wfs"
VOLCANO_URL = (GVP_WFS + "?service=WFS&version=2.0.0&request=GetFeature"
               "&typeNames=GVP-VOTW:Smithsonian_VOTW_Holocene_Volcanoes&outputFormat=application/json")
ERUPTION_URL = (GVP_WFS + "?service=WFS&version=2.0.0&request=GetFeature"
                "&typeNames=GVP-VOTW:Smithsonian_VOTW_Holocene_Eruptions&outputFormat=application/json")
GVP_PAGES = {"https://volcano.si.edu/gvp_votw.cfm": "gvp_votw_page.html",          # database versions, citation
             "https://volcano.si.edu/gvp_cite.cfm": "gvp_cite_page.html",          # how to cite
             "https://volcano.si.edu/gvp_termsofuse.cfm": "gvp_termsofuse_page.html",
             "https://volcano.si.edu/database/webservices.cfm": "gvp_webservices_page.html"}
GEONAMES_URL = "https://download.geonames.org/export/dump/cities1000.zip"
NE_BASE = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/"
NE_FILES = {"ne_10m_roads.geojson": NE_BASE + "geojson/ne_10m_roads.geojson",
            "ne_10m_railroads.geojson": NE_BASE + "geojson/ne_10m_railroads.geojson",
            "LICENSE.md": NE_BASE + "LICENSE.md", "VERSION": NE_BASE + "VERSION"}

RAW_VOLCANOES_SHARED = Path("data/raw/gvp_volcanoes")      # fetched by another member; reused when present
RAW_ERUPTIONS = Path("data/raw/gvp_eruptions")
RAW_GEONAMES = Path("data/raw/geonames")
RAW_AIRPORTS = Path("data/raw/ourairports/airports.csv")
RAW_ROADS = Path("data/raw/naturalearth_roads")
DOWNLOADS_NOTE = "downloads.json"

MOON_CELLS = Path("data/derived/grazing_cells.json")
MARS_CELLS = Path("data/derived/mars_cells.json")
MOON_OUT = Path("data/derived/steady_effects_cells.json")
MARS_OUT = Path("data/derived/mars_steady_effects.json")
OPTIONAL = {  # part -> name -> path (read if present, never required)
    "moon": {"tremors": Path("data/derived/tremors_cells.json"),
             "hazards": Path("data/derived/hazards_people_cells.json"),
             "rock": Path("data/derived/rock_frozen_cells.json"),
             "landcover_north": Path("data/derived/landcover_cells.json"),
             "landcover_south": Path("data/derived/landcover_cells_south.json"),
             "access": Path("data/derived/access_cells.json")},
    "mars": {"tremors": Path("data/derived/mars_tremors.json"),
             "hazards": Path("data/derived/mars_hazards_people.json"),
             "rock": Path("data/derived/mars_rock_frozen.json")},
}

ATTEMPTS = 6
ROAD_STEP_KM = 1.5       # points are added along road and rail lines so no two are farther apart than this
ROAD_SEARCH_KM = 1000.0  # the nearest road or railway is searched up to this far; beyond, "none within 1000 km"
AIRFIELD_TYPES = ("small_airport", "medium_airport", "large_airport")
AIRFIELD_LEFT_OUT = {"AQ-0012": "a record named 'Navaid' at the South Pole, not a runway (left out as in "
                                "data/derived/access_cells.json)"}
SETTLEMENT_LEFT_OUT = {
    "PPLX": "section of a populated place (its people are already in the city's figure)",
    "PPLH": "historical populated place", "PPLQ": "abandoned populated place", "PPLW": "destroyed populated place",
    "PPLCH": "historical capital",
}
# Natural Earth feature classes that are not a road or a railway on land: left out
LINE_LEFT_OUT = ("ferry",)


# ================================================================ distance and the grid index

def great_circle_km(lat1, lon1, lat2, lon2):
    """Haversine distance in km on a sphere of radius 6371.0 km; numbers or broadcasting arrays in degrees."""
    p1, p2 = np.radians(np.asarray(lat1, dtype=float)), np.radians(np.asarray(lat2, dtype=float))
    dl = np.radians(np.asarray(lon2, dtype=float) - np.asarray(lon1, dtype=float))
    a = np.sin((p2 - p1) / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    km = 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))
    return float(km) if np.ndim(km) == 0 else km


def distance_check() -> list[dict]:
    """The distance against pairs worked out by hand; stops the run if any is off by more than a metre."""
    one_degree = math.pi * EARTH_RADIUS_KM / 180.0           # 111.19 km: one degree of a great circle
    pairs = [((0.0, 0.0), (0.0, 1.0), one_degree, "one degree along the equator = pi x 6371 / 180"),
             ((0.0, 0.0), (90.0, 0.0), 90 * one_degree, "equator to pole = a quarter of the circumference"),
             ((89.5, 0.0), (89.5, 180.0), one_degree, "across the North Pole, 0.5 degree each side"),
             ((60.0, 10.0), (60.0, 190.0), 60 * one_degree, "60N to 60N over the pole = 60 degrees of arc")]
    out = []
    for (a, b, expected, how) in pairs:
        got = great_circle_km(a[0], a[1], b[0], b[1])
        if abs(got - expected) > 0.001:
            raise AssertionError(f"distance check failed: {a} {b}: {got} km, expected {expected} km ({how})")
        out.append({"from": a, "to": b, "km": round(got, 4), "by_hand_km": round(expected, 4), "how": how})
    return out


def cap_extent(lat: float, km: float) -> tuple[float, float, float | None]:
    """Latitude range and longitude half-width (degrees) of the circle of radius km; half-width None at a pole."""
    a = km / EARTH_RADIUS_KM
    lo, hi = lat - math.degrees(a), lat + math.degrees(a)
    if hi >= 90.0 or lo <= -90.0 or a >= math.pi / 2:
        return lo, hi, None
    ratio = math.sin(a) / math.cos(math.radians(lat))
    if ratio >= 1.0:
        return lo, hi, None
    return lo, hi, math.degrees(math.asin(ratio))


class GridIndex:
    """Points sorted into cell_deg cells, so a search reads only the cells a circle can reach (same scheme as
    scripts/build_hazards_people.py). within() is exact: the cells only narrow the candidates and the great-circle
    distance decides. nearest() widens a circle from start_km, doubling, up to max_km (or the whole globe)."""

    def __init__(self, lat, lon, cell_deg: float = 1.0):
        self.lat = np.asarray(lat, dtype=float)
        self.lon = np.asarray(lon, dtype=float)
        self.cell = float(cell_deg)
        self.nrow = int(math.ceil(180.0 / self.cell))
        self.ncol = int(math.ceil(360.0 / self.cell))
        keys = self._row(self.lat) * self.ncol + self._col(self.lon)
        self.order = np.argsort(keys, kind="stable")
        sorted_keys = keys[self.order]
        cells = np.arange(self.nrow * self.ncol)
        self.start = np.searchsorted(sorted_keys, cells, side="left")
        self.end = np.searchsorted(sorted_keys, cells, side="right")

    def _row(self, lat):
        return np.clip(np.floor((np.asarray(lat, dtype=float) + 90.0) / self.cell).astype(int), 0, self.nrow - 1)

    def _col(self, lon):
        return np.floor((np.asarray(lon, dtype=float) + 180.0) / self.cell).astype(int) % self.ncol

    def candidates(self, lat: float, lon: float, km: float) -> np.ndarray:
        if self.lat.size == 0:
            return np.zeros(0, dtype=int)
        lo, hi, dlon = cap_extent(lat, km)
        rows = range(int(self._row(max(lo, -90.0))), int(self._row(min(hi, 90.0))) + 1)
        whole = dlon is None or 2 * dlon >= 360.0 - 2 * self.cell
        if not whole:
            c0 = int(math.floor((lon - dlon + 180.0) / self.cell))
            c1 = int(math.floor((lon + dlon + 180.0) / self.cell))
            cols = sorted({c % self.ncol for c in range(c0, c1 + 1)})
        parts = []
        for r in rows:
            base = r * self.ncol
            if whole:
                s, e = self.start[base], self.end[base + self.ncol - 1]
                if e > s:
                    parts.append(self.order[s:e])
                continue
            for c in cols:
                s, e = self.start[base + c], self.end[base + c]
                if e > s:
                    parts.append(self.order[s:e])
        return np.concatenate(parts) if parts else np.zeros(0, dtype=int)

    def within(self, lat: float, lon: float, km: float):
        idx = self.candidates(lat, lon, km)
        if idx.size == 0:
            return idx, np.zeros(0)
        d = great_circle_km(lat, lon, self.lat[idx], self.lon[idx])
        keep = d <= km
        return idx[keep], d[keep]

    def nearest(self, lat: float, lon: float, start_km: float = 25.0, max_km: float | None = None):
        """(index, km) of the closest point, or (-1, None) when none lies within max_km (or none at all)."""
        if self.lat.size == 0:
            return -1, None
        limit = HALF_CIRCUMFERENCE_KM * 1.01 if max_km is None else max_km
        km = min(start_km, limit)
        while True:
            idx, d = self.within(lat, lon, km)
            if idx.size:
                best = int(np.argmin(d))
                return int(idx[best]), float(d[best])
            if km >= limit:
                return -1, None
            km = min(km * 2.0, limit)


# ================================================================ downloads (each raw file once, kept)

def now_utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def download(url: str, dest: Path, attempts: int = ATTEMPTS) -> dict:
    """Fetch url to dest with the project's User-Agent and nothing else; a dropped connection is retried after
    a growing wait; a refusal (HTTP 4xx) is not retried."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    request = urllib.request.Request(url, headers={"User-Agent": fetch.USER_AGENT})
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=300) as response, open(part, "wb") as out:
                shutil.copyfileobj(response, out)
                expected = response.headers.get("Content-Length")
            if expected is not None and part.stat().st_size != int(expected):
                raise ConnectionError(f"short body from {url}")
            break
        except urllib.error.HTTPError as error:
            part.unlink(missing_ok=True)
            if error.code < 500 or attempt == attempts:
                raise
        except (urllib.error.URLError, ConnectionError, TimeoutError, http.client.IncompleteRead):
            part.unlink(missing_ok=True)
            if attempt == attempts:
                raise
        print(f"  retrying {url} in {10 * attempt} s (attempt {attempt} failed)", file=sys.stderr)
        time.sleep(10.0 * attempt)
    os.replace(part, dest)
    return {"url": url, "file": dest.name, "fetched_utc": now_utc(), "bytes": dest.stat().st_size,
            "sha256": sha256_of(dest), "how": f"urllib with the header User-Agent: {fetch.USER_AGENT}"}


def read_notes(folder: Path) -> dict:
    path = folder / DOWNLOADS_NOTE
    return json.loads(path.read_text()) if path.exists() else {}


def ensure(url: str, dest: Path, offline: bool) -> dict:
    """The download note of dest, fetching it first when it is missing (never twice)."""
    notes = read_notes(dest.parent)
    if not dest.exists():
        if offline:
            raise FileNotFoundError(f"{dest} is missing and --offline forbids the download")
        print(f"fetching {url}", file=sys.stderr)
        notes[dest.name] = download(url, dest)
        write_json(dest.parent / DOWNLOADS_NOTE, notes)
    note = dict(notes.get(dest.name) or {"url": url, "file": dest.name, "note": "on disk before this script; no "
                                         "download note of its own"})
    note["path"] = str(dest)
    note["bytes"], note["sha256"] = dest.stat().st_size, sha256_of(dest)
    return note


def try_terms_pages(offline: bool) -> list[dict]:
    """One polite try for each GVP page on citation and terms; a refusal is noted, never worked around."""
    out = []
    notes = read_notes(RAW_ERUPTIONS)
    for url, name in GVP_PAGES.items():
        dest = RAW_ERUPTIONS / name
        if dest.exists():
            out.append({"url": url, "kept_as": str(dest), "status": "on disk",
                        "fetched_utc": (notes.get(name) or {}).get("fetched_utc")})
            continue
        if offline:
            out.append({"url": url, "status": "not tried (--offline)"})
            continue
        try:
            notes[name] = download(url, dest, attempts=2)
            write_json(RAW_ERUPTIONS / DOWNLOADS_NOTE, notes)
            out.append({"url": url, "kept_as": str(dest), "status": "fetched", "fetched_utc": notes[name]["fetched_utc"]})
        except urllib.error.HTTPError as error:
            out.append({"url": url, "status": f"HTTP {error.code} at {now_utc()}; not worked around"})
        except Exception as error:  # noqa: BLE001  a failed courtesy read must not stop the build
            out.append({"url": url, "status": f"failed at {now_utc()}: {error}"})
    return out


def write_json(path: Path, value) -> None:
    """Write beside the file and rename into place, so a reader never sees half a file. NaN is refused."""
    path = Path(path)
    side = path.with_name(path.name + ".part")
    try:
        side.write_text(json.dumps(value, separators=(",", ":"), allow_nan=False, ensure_ascii=False),
                        encoding="utf-8")
    except ValueError:
        side.unlink(missing_ok=True)
        raise
    os.replace(side, path)


# ================================================================ volcanoes and eruptions

def read_volcanoes(path: Path) -> dict[int, dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    matched = data.get("numberMatched")
    if matched is not None and int(matched) != len(data["features"]):
        raise ValueError(f"{path}: {len(data['features'])} features but numberMatched {matched}: a partial answer")
    out = {}
    for f in data["features"]:
        p = f["properties"]
        lon, lat = f["geometry"]["coordinates"][:2] if f.get("geometry") else (p["Longitude"], p["Latitude"])
        out[int(p["Volcano_Number"])] = {"number": int(p["Volcano_Number"]), "name": p.get("Volcano_Name"),
                                         "country": p.get("Country"), "lat": float(lat), "lon": float(lon),
                                         "list_last_eruption_year": p.get("Last_Eruption_Year")}
    return out


def read_eruptions(path: Path, volcanoes: dict[int, dict], this_year: int) -> tuple[dict[int, dict], dict]:
    """Per volcano: the calendar years since SINCE in which a confirmed eruption was in progress.

    An eruption with a start and an end year counts every year from start to end; one without an end year counts
    its start year only (its length is not known); an end year marked '>' is the list's way of saying the
    eruption was still going on at its last report (Erebus: 1972 to >2026), so it counts through that year.
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    matched = data.get("numberMatched")
    if matched is not None and int(matched) != len(data["features"]):
        raise ValueError(f"{path}: {len(data['features'])} features but numberMatched {matched}: a partial answer")
    tally = {"records": len(data["features"]), "by_activity_type": {}, "confirmed_without_start_year": 0,
             "confirmed_since_%d" % SINCE: 0, "continuing": 0, "volcano_not_in_holocene_list": 0}
    per: dict[int, dict] = {}
    for f in data["features"]:
        p = f["properties"]
        kind = p.get("Activity_Type") or "(blank)"
        tally["by_activity_type"][kind] = tally["by_activity_type"].get(kind, 0) + 1
        if kind != "Confirmed Eruption":
            continue
        start = p.get("StartDateYear")
        if start is None:
            tally["confirmed_without_start_year"] += 1
            continue
        start = int(start)
        end = p.get("EndDateYear")
        continuing = (p.get("EndDateYearModifier") or "").strip() == ">"
        if continuing:
            tally["continuing"] += 1
            end = this_year if end is None else end
        end = start if end is None or int(end) < start else min(int(end), this_year)
        if end < SINCE:
            continue
        tally["confirmed_since_%d" % SINCE] += 1
        number = int(p["Volcano_Number"])
        if number not in volcanoes:
            tally["volcano_not_in_holocene_list"] += 1
            lon, lat = f["geometry"]["coordinates"][:2]
            volcanoes[number] = {"number": number, "name": p.get("Volcano_Name"), "country": None,
                                 "lat": float(lat), "lon": float(lon), "list_last_eruption_year": None}
        rec = per.setdefault(number, {"years": set(), "continuing": False})
        rec["years"].update(range(max(start, SINCE), end + 1))
        rec["continuing"] = rec["continuing"] or continuing
    tally["by_activity_type"] = dict(sorted(tally["by_activity_type"].items()))
    steady = rule("volcanic", "steady")
    active = {}
    for number, rec in per.items():
        years = sorted(rec["years"])
        v = volcanoes[number]
        active[number] = {**v, "years_erupting_since_%d" % SINCE: len(years), "last_eruption_year": years[-1],
                          "first_year_since_%d" % SINCE: years[0], "continuing": rec["continuing"],
                          "steady": len(years) >= steady["min_years"] or years[-1] >= steady["recent"]}
    tally["volcanoes_erupted_since_%d" % SINCE] = len(active)
    tally["of_them_meeting_the_steady_test"] = sum(a["steady"] for a in active.values())
    return active, tally


def volcano_record(v: dict, km: float, active: bool) -> dict:
    out = {"name": v["name"], "number": v["number"], "country": v["country"], "km": round(km, 1),
           "lat": round(v["lat"], 3), "lon": round(v["lon"], 3)}
    if active:
        out.update({"years_erupting_since_%d" % SINCE: v["years_erupting_since_%d" % SINCE],
                    "last_eruption_year": v["last_eruption_year"], "continuing": v["continuing"]})
    return out


# ================================================================ settlements, airfields, roads

GEONAMES_COLUMNS = 19


def read_settlements(path: Path) -> tuple[dict, dict]:
    lat, lon, pop, name, country = [], [], [], [], []
    left_out, rows = {}, 0
    with zipfile.ZipFile(path) as z, z.open("cities1000.txt") as raw:
        for line in io.TextIOWrapper(raw, encoding="utf-8"):
            cols = line.rstrip("\n").split("\t")
            if len(cols) < GEONAMES_COLUMNS:
                continue
            rows += 1
            if cols[7] in SETTLEMENT_LEFT_OUT:
                left_out[cols[7]] = left_out.get(cols[7], 0) + 1
                continue
            p = int(cols[14]) if cols[14].strip() else 0
            lat.append(float(cols[4])); lon.append(float(cols[5]))
            pop.append(p if p > 0 else -1)          # -1: the list gives no figure (it writes 0)
            name.append(cols[1]); country.append(cols[8] or None)
    s = {"lat": np.array(lat), "lon": np.array(lon), "pop": np.array(pop, dtype=np.int64),
         "name": name, "country": country}
    s["index"] = GridIndex(s["lat"], s["lon"])
    big = np.flatnonzero(s["pop"] >= rule("human", "steady")["pop"])
    s["big"], s["big_index"] = big, GridIndex(s["lat"][big], s["lon"][big])
    tally = {"rows": rows, "left_out": dict(sorted(left_out.items())), "kept": len(lat),
             "kept_without_population": int((s["pop"] < 0).sum()), "with_1000_or_more": int(big.size)}
    return s, tally


def settlement_record(s: dict, i: int, km: float) -> dict:
    p = int(s["pop"][i])
    return {"name": s["name"][i], "country": s["country"][i], "population": p if p > 0 else None, "km": round(km, 1)}


def read_airfields(path: Path) -> tuple[dict, dict]:
    rows = list(csv.DictReader(open(path, newline="", encoding="utf-8")))
    keep = [r for r in rows if r["type"] in AIRFIELD_TYPES and r["ident"] not in AIRFIELD_LEFT_OUT
            and r["latitude_deg"] and r["longitude_deg"]]
    a = {"lat": np.array([float(r["latitude_deg"]) for r in keep]),
         "lon": np.array([float(r["longitude_deg"]) for r in keep]),
         "rows": [{"name": r["name"], "ident": r["ident"], "type": r["type"], "country": r["iso_country"] or None}
                  for r in keep],
         "scheduled": np.array([r["scheduled_service"] == "yes" for r in keep])}
    a["index"] = GridIndex(a["lat"], a["lon"])
    sched = np.flatnonzero(a["scheduled"])
    a["sched"], a["sched_index"] = sched, GridIndex(a["lat"][sched], a["lon"][sched])
    by_type = {}
    for r in rows:
        by_type[r["type"]] = by_type.get(r["type"], 0) + 1
    return a, {"rows": len(rows), "kept": len(keep), "kept_with_scheduled_flights": int(sched.size),
               "by_type_in_table": dict(sorted(by_type.items())), "left_out_by_hand": AIRFIELD_LEFT_OUT}


def airfield_record(a: dict, i: int, km: float) -> dict:
    return {**a["rows"][i], "scheduled_flights": bool(a["scheduled"][i]), "km": round(km, 1)}


def to_unit(lat, lon):
    la, lo = np.radians(lat), np.radians(lon)
    return np.stack([np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)], axis=-1)


def read_lines(path: Path, kind: str, step_km: float = ROAD_STEP_KM) -> tuple[dict, dict]:
    """Points along every road or railway line of a Natural Earth GeoJSON, at most step_km apart.

    The nearest of these points is at most step_km / 2 farther than the line itself (a point beside the middle
    of a stretch between two points), so the distance to a road is overstated by at most 0.75 km.
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    feats, a_parts, b_parts, seg_feat, ends = [], [], [], [], []
    tally = {"features": len(data["features"]), "left_out": {}, "kept": 0, "by_class_kept": {}}
    for f in data["features"]:
        p = f.get("properties") or {}
        cla = str(p.get("featurecla") or "")
        typ = str(p.get("type") or "")
        if any(w in cla.lower() or w in typ.lower() for w in LINE_LEFT_OUT):
            key = cla + (" / " + typ if typ else "")
            tally["left_out"][key] = tally["left_out"].get(key, 0) + 1
            continue
        g = f.get("geometry") or {}
        lines = ([g["coordinates"]] if g.get("type") == "LineString" else
                 g["coordinates"] if g.get("type") == "MultiLineString" else [])
        k = len(feats)
        feats.append({"kind": kind, "class": cla or None, "type": typ or None,
                      "name": (p.get("name") or p.get("label") or None) if kind == "road" else (p.get("name") or None)})
        tally["kept"] += 1
        tally["by_class_kept"][cla + (" / " + typ if typ else "")] = \
            tally["by_class_kept"].get(cla + (" / " + typ if typ else ""), 0) + 1
        for line in lines:
            c = np.asarray(line, dtype=float)
            if c.ndim != 2 or len(c) == 0:
                continue
            v = to_unit(c[:, 1], c[:, 0])
            if len(v) == 1:
                ends.append((v[0], k))
                continue
            a_parts.append(v[:-1]); b_parts.append(v[1:]); seg_feat.append(np.full(len(v) - 1, k))
            ends.append((v[-1], k))
    a, b, sf = np.concatenate(a_parts), np.concatenate(b_parts), np.concatenate(seg_feat)
    ang = np.arctan2(np.linalg.norm(np.cross(a, b), axis=1), np.einsum("ij,ij->i", a, b))
    n = np.maximum(1, np.ceil(ang * EARTH_RADIUS_KM / step_km)).astype(np.int64)
    seg = np.repeat(np.arange(len(n)), n)
    k = np.arange(int(n.sum())) - np.repeat(np.cumsum(n) - n, n)
    t = (k / n[seg])[:, None]
    pts = a[seg] * (1.0 - t) + b[seg] * t
    pts = np.concatenate([pts, np.array([e[0] for e in ends])])
    owner = np.concatenate([sf[seg], np.array([e[1] for e in ends], dtype=np.int64)])
    pts /= np.linalg.norm(pts, axis=1)[:, None]
    lat = np.degrees(np.arcsin(np.clip(pts[:, 2], -1, 1)))
    lon = np.degrees(np.arctan2(pts[:, 1], pts[:, 0]))
    tally["by_class_kept"] = dict(sorted(tally["by_class_kept"].items()))
    tally["left_out"] = dict(sorted(tally["left_out"].items()))
    tally["line_km"] = round(float((ang * EARTH_RADIUS_KM).sum()))
    tally["points_after_adding"] = int(len(lat))
    tally["longest_original_stretch_km"] = round(float(ang.max() * EARTH_RADIUS_KM), 1)
    return {"lat": lat, "lon": lon, "owner": owner, "feats": feats}, tally


def merge_lines(roads: dict, rails: dict) -> dict:
    shift = len(roads["feats"])
    out = {"lat": np.concatenate([roads["lat"], rails["lat"]]), "lon": np.concatenate([roads["lon"], rails["lon"]]),
           "owner": np.concatenate([roads["owner"], rails["owner"] + shift]), "feats": roads["feats"] + rails["feats"]}
    out["index"] = GridIndex(out["lat"], out["lon"], cell_deg=0.5)
    return out


# ================================================================ optional inputs of other members

def read_optional(part: str) -> tuple[dict, list[dict]]:
    found, notes = {}, []
    for name, path in OPTIONAL[part].items():
        if not path.exists():
            notes.append({"name": name, "path": str(path), "found": False})
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        meta = data.get("meta", {}) if isinstance(data, dict) else {}
        cells = data["cells"] if isinstance(data, dict) else data
        if isinstance(cells, list):
            cells = {c["id"]: c for c in cells}
        found[name] = cells
        notes.append({"name": name, "path": str(path), "found": True, "places": len(cells),
                      "made_by": meta.get("made_by"), "written": meta.get("written") or meta.get("made"),
                      "file_time_utc": datetime.datetime.fromtimestamp(path.stat().st_mtime, datetime.timezone.utc)
                      .strftime("%Y-%m-%dT%H:%M:%SZ")})
    return found, notes


def ice_share(opt: dict, pid: str) -> float | None:
    for name in ("landcover_north", "landcover_south"):
        rec = opt.get(name, {}).get(pid)
        if rec is not None and rec.get("ice") is not None:
            return float(rec["ice"])
    return None


# ================================================================ the three results for one place

def volcanic_result(lat, lon, act, act_index, act_list, hol_index, hol_list, rock_cells, pid):
    steady_r, come_r, young_r = rule("volcanic", "steady"), rule("volcanic", "volcanic effects come"), \
        rule("volcanic", "young")
    idx, d = act_index.within(lat, lon, come_r["km"])
    order = np.argsort(d)
    idx, d = idx[order], d[order]
    cls, decided = "none expected", None
    steady_hits = [(int(i), float(k)) for i, k in zip(idx, d) if k <= steady_r["km"] and act_list[int(i)]["steady"]]
    if steady_hits:
        cls, decided = "steady volcanic effects likely", volcano_record(act_list[steady_hits[0][0]], steady_hits[0][1], True)
    elif idx.size:
        cls, decided = "volcanic effects come and go", volcano_record(act_list[int(idx[0])], float(d[0]), True)
    i, km = act_index.nearest(lat, lon, start_km=50.0)
    nearest_active = volcano_record(act_list[i], km, True) if i >= 0 else None
    j, kmj = hol_index.nearest(lat, lon, start_km=50.0)
    nearest_hol = volcano_record(hol_list[j], kmj, False) if j >= 0 else None
    out = {"class": cls, "effects": rule("volcanic", cls)["effects"], "decided_by": decided,
           "nearest_erupted_since_%d" % SINCE: nearest_active, "nearest_holocene": nearest_hol}
    near = nearest_hol is not None and kmj <= young_r["km"]
    rock = None
    if rock_cells is not None:
        r = (rock_cells.get(pid) or {}).get("rock") or {}
        rock = r.get("volcanic")
        out["rock_map_volcanic"] = rock
        out["rock_map_class"] = r.get("class")
    if not near:
        out["young_volcanic_ground"], why = False, f"no Holocene volcano within {young_r['km']:g} km"
    elif rock_cells is None:
        out["young_volcanic_ground"], why = True, (f"a Holocene volcano within {young_r['km']:g} km (no rock map "
                                                   "was found to confirm)")
    elif rock is True:
        out["young_volcanic_ground"], why = True, (f"a Holocene volcano within {young_r['km']:g} km and the rock "
                                                   "map says volcanic")
    elif rock is False:
        out["young_volcanic_ground"], why = False, (f"a Holocene volcano within {young_r['km']:g} km, but the rock "
                                                    "map says the rock here is not volcanic")
    else:
        out["young_volcanic_ground"], why = None, (f"a Holocene volcano within {young_r['km']:g} km, but the rock "
                                                   "map gives no class here")
    out["young_volcanic_ground_why"] = why
    return out


def human_result(lat, lon, s, a, lines):
    st, po, help_r = rule("human", "steady"), rule("human", "human disturbance possible"), rule("human", "help")
    i, km = s["index"].nearest(lat, lon, start_km=25.0)
    nearest = settlement_record(s, i, km) if i >= 0 else None
    j, kmj = s["big_index"].nearest(lat, lon, start_km=25.0)
    nearest_big = settlement_record(s, int(s["big"][j]), kmj) if j >= 0 else None
    near, _ = s["index"].within(lat, lon, po["settlement_km"])
    pops = s["pop"][near]
    known = int((pops > 0).sum())
    total = 0 if near.size == 0 else (int(pops[pops > 0].sum()) if known else None)
    r, kmr = lines["index"].nearest(lat, lon, start_km=5.0, max_km=ROAD_SEARCH_KM)
    if r >= 0:
        f = lines["feats"][int(lines["owner"][r])]
        road = {"kind": f["kind"], "class": f["class"], "type": f["type"], "name": f["name"], "km": round(kmr, 1)}
    else:
        road = {"kind": None, "km": None, "none_within_km": ROAD_SEARCH_KM}
    k, kmk = a["index"].nearest(lat, lon, start_km=25.0)
    airfield = airfield_record(a, k, kmk) if k >= 0 else None
    q, kmq = a["sched_index"].nearest(lat, lon, start_km=25.0)
    scheduled = airfield_record(a, int(a["sched"][q]), kmq) if q >= 0 else None

    def within(rec, limit):
        return rec is not None and rec.get("km") is not None and rec["km"] <= limit

    def say(rec, what):
        pop = rec.get("population")
        return f"{what} {rec.get('name') or '(unnamed)'}{f' ({pop:,} people)' if pop else ''} {rec['km']:g} km away"

    steady_why, possible_why = [], []
    if within(nearest_big, st["settlement_km"]):
        steady_why.append(say(nearest_big, "settlement"))
    if within(road, st["road_km"]):
        steady_why.append(say(road, "main " + road["kind"]))
    if within(scheduled, st["scheduled_km"]):
        steady_why.append(say(scheduled, "airfield with scheduled flights"))
    if within(nearest, po["settlement_km"]):
        possible_why.append(say(nearest, "settlement"))
    if within(road, po["road_km"]):
        possible_why.append(say(road, "main " + road["kind"]))
    if within(airfield, po["airfield_km"]):
        possible_why.append(say(airfield, "airfield"))
    if steady_why:
        cls, why = "steady human disturbance likely", steady_why
    elif possible_why:
        cls, why = "human disturbance possible", possible_why
    else:
        cls, why = "undisturbed as far as our lists show", []
    help_why = []
    if within(nearest_big, help_r["settlement_km"]):
        help_why.append(say(nearest_big, "settlement"))
    if within(scheduled, help_r["scheduled_km"]):
        help_why.append(say(scheduled, "airfield with scheduled flights"))
    return {"class": cls, "effects": rule("human", cls)["effects"], "why": why,
            "nearest_settlement": nearest, "nearest_settlement_1000_or_more": nearest_big,
            "population_within_25km": total, "settlements_within_25km": int(near.size),
            "settlements_without_population_within_25km": int(near.size - known),
            "nearest_main_road_or_railway": road, "nearest_airfield": airfield,
            "nearest_airfield_with_scheduled_flights": scheduled,
            "help_within_reach": bool(help_why), "help_within_reach_why": help_why}


def tremor_estimate(volc: dict, m5: int | None, ice: float | None, use_ice: bool) -> tuple[str, list[str]]:
    lk, ps = rule("small_tremors", "small tremors likely"), rule("small_tremors", "small tremors possible")
    act = volc["nearest_erupted_since_%d" % SINCE]
    hol = volc["nearest_holocene"]
    likely, possible = [], []
    if act is not None and act["km"] <= lk["volcano_km"]:
        likely.append(f"{act['name']} (erupted since {SINCE}) {act['km']:g} km away")
    if m5 is not None and m5 >= lk["m5_min"]:
        likely.append(f"{m5} earthquakes of magnitude 5+ within {lk['m5_km']:g} km since {SINCE}")
    if hol is not None and hol["km"] <= ps["volcano_km"]:
        possible.append(f"Holocene volcano {hol['name']} {hol['km']:g} km away")
    if m5 is not None and ps["m5_low"] <= m5 <= ps["m5_high"]:
        possible.append(f"{m5} earthquake{'s' if m5 > 1 else ''} of magnitude 5+ within {ps['m5_km']:g} km since {SINCE}")
    if use_ice and ice is not None and ice >= ps["ice_share"]:
        possible.append(f"glacier ice on {ice:.0%} of the land")
    if likely:
        return "small tremors likely", likely
    if possible:
        return "small tremors possible", possible
    return "small tremors unlikely", []


def tremor_result(pid, volc, opt, use_ice):
    trem = opt.get("tremors")
    haz = opt.get("hazards")
    t = (trem or {}).get(pid)
    verdict = t.get("verdict") if t else None
    m5 = None
    if haz is not None and pid in haz:
        m5 = (haz[pid].get("quakes_m5_200km") or {}).get("count")
    ice = ice_share(opt, pid) if use_ice else None
    est, why = tremor_estimate(volc, m5, ice, use_ice)
    if verdict is not None and verdict != "cannot tell":
        cls, source = verdict, "catalogue"
    else:
        cls, source = est, "our rough estimate"
    return {"class": cls, "source": source,
            "source_words": ("the catalogue's own verdict (tremors file)" if source == "catalogue" else
                             "our rough estimate: the catalogue cannot see small tremors here" if trem is not None
                             else "our rough estimate: no tremors file was found"),
            "catalogue_verdict": verdict, "catalogue_status": t.get("status") if t else None,
            "our_estimate": est, "our_estimate_why": why,
            "m5_quakes_200km_since_%d" % SINCE: m5, "glacier_ice_share": None if ice is None else round(ice, 3)}


# ================================================================ meta

def counts(records: dict) -> dict:
    def tally(values):
        out = {}
        for v in values:
            key = "null" if v is None else str(v).lower() if isinstance(v, bool) else v
            out[key] = out.get(key, 0) + 1
        return dict(sorted(out.items(), key=lambda kv: -kv[1]))
    vals = list(records.values())
    cross = {}
    for v in vals:
        t = v["small_tremors"]
        if t["source"] == "catalogue":
            key = f"catalogue '{t['catalogue_verdict']}' vs our estimate '{t['our_estimate']}'"
            cross[key] = cross.get(key, 0) + 1
    return {"places": len(vals),
            "volcanic": tally(v["volcanic"]["class"] for v in vals),
            "young_volcanic_ground": tally(v["volcanic"]["young_volcanic_ground"] for v in vals),
            "human": tally(v["human"]["class"] for v in vals),
            "help_within_reach": tally(v["human"]["help_within_reach"] for v in vals),
            "small_tremors": tally(v["small_tremors"]["class"] for v in vals),
            "small_tremors_by_source": tally(v["small_tremors"]["source"] for v in vals),
            "small_tremors_our_estimate_only_where_catalogue_blind":
                tally(v["small_tremors"]["class"] for v in vals if v["small_tremors"]["source"] != "catalogue"),
            "check_where_the_catalogue_sees_small_tremors": dict(sorted(cross.items(), key=lambda kv: -kv[1]))}


GVP_TERMS = {  # as read on 14 November 2026 (local evening); the pages are kept in data/raw/gvp_eruptions/
    "licence": "not stated in the web feature service's answer; its capabilities document says Fees: NONE and "
               "AccessConstraints: NONE; no login is asked for",
    "terms_of_use": "NOT READ. The GVP's Terms of Use page (volcano.si.edu/gvp_termsofuse.cfm) and its How to Cite "
                    "page answered HTTP 403 ('Smithsonian site temporarily unavailable'); the site answers only now "
                    "and then tonight, and si.edu/termsofuse asked for a browser verification, which was not "
                    "attempted. To be read before publishing.",
    "citation_asked_for": "Global Volcanism Program, 2026. [Database] Volcanoes of the World (v. 5.4.0; 7 Aug 2026). "
                          "Distributed by Smithsonian Institution, compiled by Venzke, E. "
                          "https://doi.org/10.5479/si.GVP.VOTW5-2026.5.4 (the 'General Database Citation (example "
                          "for today)' of volcano.si.edu/gvp_votw.cfm and the citation on "
                          "volcano.si.edu/database/webservices.cfm, both kept in data/raw/gvp_eruptions/; the page "
                          "says previous versions are not available, so a use should name the version and date)",
    "credit": "Global Volcanism Program, Smithsonian Institution: Volcanoes of the World v. 5.4.0 (7 Aug 2026), "
              "Holocene volcano and eruption lists, from its public web feature service",
}


def field_notes() -> dict:
    return {
        "volcanic": {
            "class": "one of the three classes of the rules",
            "effects": "the fixed list of what a steady or recurring volcanic presence does to field work; the same "
                       "words for every place of the class, not observed at the place; empty for 'none expected'",
            "decided_by": "the volcano that set the class (the nearest one meeting the class's test), or null",
            "nearest_erupted_since_%d" % SINCE: "the nearest volcano with a confirmed eruption in progress in %d or "
                                               "later, any distance: name, GVP number, km, the number of separate "
                                               "calendar years since %d with an eruption in progress, the last such "
                                               "year, and whether the list says it is still going on" % (SINCE, SINCE),
            "nearest_holocene": "the nearest volcano of the Holocene list, any date (it can be the same volcano)",
            "young_volcanic_ground": "true, false or null by the rule; the useful side, kept apart from the class",
            "rock_map_volcanic": "the rock map's own yes/no (null when it gives none), copied from the rock file",
            "is_not": "Not a hazard map, not an eruption forecast. A volcano is one listed point (summit or field "
                      "centre); a fissure system or field can reach well beyond it, and gas or ash can drift much "
                      "farther than 100 km downwind. 'Years erupting' counts calendar years in which the list has a "
                      "confirmed eruption in progress: an eruption with no end year counts its start year only; "
                      "uncertain and discredited eruptions are left out; lava lakes and steady degassing between "
                      "listed eruptions are not counted (a volcano can steam and smell for decades between them).",
        },
        "human": {
            "class": "one of the three classes of the rules", "why": "which of the class's tests held, in words",
            "effects": "the fixed list of what steady human presence does to field work; empty when undisturbed",
            "nearest_settlement": "nearest listed settlement (GeoNames cities1000), its population (null when the "
                                  "list gives none) and km",
            "nearest_settlement_1000_or_more": "nearest listed settlement whose listed population is 1,000 or more",
            "population_within_25km": "sum of the listed populations of the settlements whose point lies within "
                                      "25 km: 0 when none is listed, null when some are listed but none has a "
                                      "figure, a lower bound when only some lack one",
            "nearest_main_road_or_railway": "the nearest Natural Earth 1:10m road or railway (ferry routes left "
                                            "out), with its class, type, name and km; km null and none_within_km "
                                            "1000 when there is none that close",
            "nearest_airfield": "nearest runway airfield of any size (OurAirports small, medium or large airport, "
                                "gravel and ice strips included; heliports, seaplane bases and closed fields left "
                                "out, as in data/derived/access_cells.json), with km",
            "nearest_airfield_with_scheduled_flights": "the same, among airfields the table flags as having "
                                                       "scheduled service",
            "help_within_reach": "true or false by the rule; the useful side, kept apart from the class",
            "is_not": "Not a population map and not a noise or light measurement. A straight line, not a travel "
                      "distance. GeoNames cities1000 lists places of more than 1,000 people and seats of local "
                      "government, so camps, stations, mines and hamlets are missing; Natural Earth holds main roads "
                      "and railways only, so a missing road is not proof of no road (tracks, winter roads, mine "
                      "roads are mostly absent); an airfield's traffic is not known, only that it exists.",
        },
        "small_tremors": {
            "class": "the catalogue's verdict from the tremors file where it has one, else our estimate",
            "source": "'catalogue' or 'our rough estimate'",
            "catalogue_verdict": "the verdict of data/derived/tremors_cells.json (or mars_tremors.json), null if "
                                 "the file or the place is missing",
            "our_estimate": "our rule's class, worked out for every place so it can be compared where the "
                            "catalogue sees",
            "m5_quakes_200km_since_%d" % SINCE: "earthquakes of magnitude 5 or more within 200 km, 1990-2025, from "
                                               "the hazards file (null if the file is missing)",
            "glacier_ice_share": "share of the area's land mapped as snow and ice (ESA WorldCover in the north; the "
                                 "south's ice-sheet share), from the landcover files; null for the Mars squares",
            "is_not": "Not a count and not a measurement of small tremors: a guess from what usually makes them "
                      "(active volcanoes, a seismically busy region, moving glaciers). Small tremors can occur "
                      "where it says unlikely, and need not occur where it says likely.",
        },
    }


def make_meta(part, cells_file, records, opt_notes, eruption_tally, volc_counts, settle_tally, air_tally,
              road_tally, rail_tally, notes, terms_try, dist_check, use_ice, access_check) -> dict:
    point = ("the area centre (lat and lon in grazing_cells.json); an area is about 11 km across, so any point of "
             "it can be up to about 8 km nearer or farther than the figures say" if part == "moon" else
             "the square centre (lat and lon in mars_cells.json); a square is half a degree (about 55 km north-south) "
             "so the 2, 5, 10 and 25 km tests describe only the middle of the square")
    left_out = []
    if not use_ice:
        left_out.append("small tremors: the glacier-ice part of the 'possible' test is left out for the Mars "
                        "squares, which have no ice share in the project's files")
    if "hazards" not in opt_notes_found(opt_notes):
        left_out.append("small tremors: the earthquake parts of the tests are left out (no hazards file); nothing "
                        "was fetched for them")
    return {
        "written": datetime.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z"),
        "made_by": "agent STEADY-EFFECTS, scripts/build_steady_effects.py",
        "part": part, "places_from": str(cells_file), "place_point": point,
        "what_this_is": "For every place: what volcanoes and people steadily do there (not the risk of a rare "
                        "event), with the useful side of each (young volcanic ground; help within reach), and a "
                        "small-tremor class (the catalogue's verdict where it can see small tremors, our rough "
                        "estimate where it cannot). Read beside the light ranking, not part of it.",
        "rule_of_thumb": DISCLAIMER,
        "rules_in_plain_words": [DISCLAIMER] + [
            f"{r['result'].replace('_', ' ')}, '{r['outcome']}': {r['when']}."
            + (f" What it means for the work: {'; '.join(r['what_the_effects_are'])}." if r.get("what_the_effects_are")
               else "") for r in rules_in_words()],
        "rules": rules_in_words(),
        "rules_left_out_here": left_out,
        "fields": field_notes(),
        "counts": counts(records),
        "optional_inputs": opt_notes,
        "distance": "great circle on a sphere of radius 6371.0 km (haversine); against the real ellipsoid within "
                    "about 0.5 percent",
        "distance_check": dist_check,
        "search": f"grid indexes (1 degree cells; 0.5 degree for road and rail points); every kept point is decided "
                  f"by its great-circle distance; nearest searches widen until they find a point (roads and "
                  f"railways: up to {ROAD_SEARCH_KM:g} km)",
        "roads_accuracy": f"points added along every road and railway so none is more than {ROAD_STEP_KM:g} km "
                          f"from the next; the distance to the nearest point overstates the distance to the line "
                          f"by at most {ROAD_STEP_KM / 2:g} km. Natural Earth 1:10m lines are themselves "
                          "generalised (often a kilometre or more off the real road)",
        "airfields_check_against_access_cells": access_check,
        "sources": {
            "volcanoes": {"name": "Smithsonian Institution, Global Volcanism Program (GVP): Volcanoes of the World, "
                                  "Holocene volcano list (layer GVP-VOTW:Smithsonian_VOTW_Holocene_Volcanoes)",
                          "service": VOLCANO_URL, "file": notes["volcanoes"], **volc_counts,
                          **{k: GVP_TERMS[k] for k in ("licence", "terms_of_use", "citation_asked_for", "credit")}},
            "eruptions": {"name": "GVP Volcanoes of the World, Holocene eruption list (layer "
                                  "GVP-VOTW:Smithsonian_VOTW_Holocene_Eruptions)",
                          "service": ERUPTION_URL, "file": notes["eruptions"], "tally": eruption_tally,
                          "kept": "Activity_Type 'Confirmed Eruption' only; years from StartDateYear to EndDateYear "
                                  "(an end year marked '>' = still going on at the list's last report, counted "
                                  "through the year given; no end year = the start year only)",
                          "terms_page_try": terms_try,
                          **{k: GVP_TERMS[k] for k in ("licence", "terms_of_use", "citation_asked_for", "credit")}},
            "settlements": {"name": "GeoNames gazetteer, cities1000", "url": GEONAMES_URL, "file": notes["geonames"],
                            "licence": "CC BY 4.0", "credit": "GeoNames (geonames.org), CC BY 4.0",
                            "left_out_codes": SETTLEMENT_LEFT_OUT, "tally": settle_tally},
            "airfields": {"name": "OurAirports, airports.csv", "file": notes["airports"],
                          "licence": "public domain (The Unlicense, the LICENSE file of "
                                     "github.com/davidmegginson/ourairports-data; copy in data/raw/ourairports/)",
                          "credit": "OurAirports (ourairports.com), public domain", "types_kept": list(AIRFIELD_TYPES),
                          "tally": air_tally},
            "roads_and_railways": {
                "name": "Natural Earth 1:10m Cultural Vectors: roads (ne_10m_roads) and railroads (ne_10m_railroads), "
                        "GeoJSON from github.com/nvkelso/natural-earth-vector",
                "files": notes["roads"], "version": notes.get("ne_version"),
                "licence": "public domain (the repository's LICENSE.md: 'Everything here is public domain.'; "
                           "no permission needed and credit not required; copy kept in data/raw/naturalearth_roads/)",
                "credit": "Made with Natural Earth. Free vector and raster map data @ naturalearthdata.com. (the "
                          "long credit text LICENSE.md offers)",
                "main_roads_only": "Natural Earth holds main roads and railways only, drawn for maps of a whole "
                                   "continent: a missing road is not proof of no road.",
                "roads_tally": road_tally, "railways_tally": rail_tally},
        },
        "null_rule": "unknown is null, never 0; a count of 0 means the list holds none within the radius",
        "rerun": "uv run python scripts/build_steady_effects.py --offline --report",
    }


def opt_notes_found(opt_notes) -> set:
    return {n["name"] for n in opt_notes if n["found"]}


# ================================================================ the report

NAMED = [  # (label, part, id or None, lat, lon)
    ("south-west Iceland (Reykjanes)", "moon", "63.8_-22.6", None, None),
    ("Haughton crater, Devon Island", "moon", "75.3_-90.0", None, None),
    ("near Ulukhaktok", "moon", None, 70.736, -117.770),
    ("Longyearbyen", "moon", "78.2_15.6", None, None),
    ("Pechora Sea coast", "moon", "68.9_54.3", None, None),
    ("McMurdo Dry Valleys", "moon", "-77.6_161.5", None, None),
    ("Atacama near Yungay", "mars", "m_-24.25_-69.75", None, None),
    ("Tibetan Plateau", "mars", None, 33.0, 88.0),
    ("Haughton crater (Mars square)", "mars", "m_75.25_-89.75", None, None),
]


def report(sets: dict) -> str:
    out = []
    for label, part, pid, lat, lon in NAMED:
        places, records = sets[part]
        how = "named"
        if pid is None or pid not in records:
            want_lat, want_lon = (lat, lon) if pid is None else (None, None)
            if want_lat is None:
                out.append(f"{label} [{part} {pid}]: not in the file")
                continue
            plat = np.array([p["lat"] for p in places]); plon = np.array([p["lon"] for p in places])
            d = great_circle_km(want_lat, want_lon, plat, plon)
            k = int(np.argmin(d)); pid = places[k]["id"]
            how = f"nearest record to {want_lat}, {want_lon} ({d[k]:.1f} km)"
        r = records[pid]
        v, h, t = r["volcanic"], r["human"], r["small_tremors"]
        a, hol = v["nearest_erupted_since_%d" % SINCE], v["nearest_holocene"]
        out.append(
            f"{label} [{part} {pid}; {how}]\n"
            f"   volcanic: {v['class']}; young volcanic ground {v['young_volcanic_ground']} ({v['young_volcanic_ground_why']})\n"
            f"     nearest erupted since {SINCE}: {a['name']} {a['km']:g} km, {a['years_erupting_since_%d' % SINCE]} years, "
            f"last {a['last_eruption_year']}{' (continuing)' if a['continuing'] else ''}; nearest Holocene: "
            f"{hol['name']} {hol['km']:g} km; decided by {v['decided_by']['name'] if v['decided_by'] else '-'}\n"
            f"   human: {h['class']} {h['why']}; help within reach {h['help_within_reach']} {h['help_within_reach_why']}\n"
            f"     nearest settlement {h['nearest_settlement']}; 1000+ {h['nearest_settlement_1000_or_more']}; "
            f"pop within 25 km {h['population_within_25km']} ({h['settlements_within_25km']} places)\n"
            f"     road/rail {h['nearest_main_road_or_railway']}\n"
            f"     airfield {h['nearest_airfield']}; scheduled {h['nearest_airfield_with_scheduled_flights']}\n"
            f"   small tremors: {t['class']} ({t['source']}; catalogue {t['catalogue_verdict']!r}; our estimate "
            f"{t['our_estimate']!r} {t['our_estimate_why']}; M5+ {t['m5_quakes_200km_since_%d' % SINCE]}; ice "
            f"{t['glacier_ice_share']})")
    return "\n".join(out)


# ================================================================ command line

def load_places(path: Path) -> list[dict]:
    cells = json.loads(path.read_text(encoding="utf-8"))["cells"]
    values = cells.values() if isinstance(cells, dict) else cells
    return [{"id": c["id"], "lat": float(c["lat"]), "lon": float(c["lon"])} for c in values]


def check_access(records: dict, access: dict | None) -> dict | None:
    """Our nearest airfield against data/derived/access_cells.json (same table, same rules): how many differ."""
    if access is None:
        return None
    same = differ = 0
    examples = []
    for pid, r in records.items():
        mine = r["human"]["nearest_airfield"]
        theirs = (access.get(pid) or {}).get("nearest")
        if theirs is None or mine is None:
            continue
        if abs(mine["km"] - theirs["km"]) <= 0.15:
            same += 1
        else:
            differ += 1
            if len(examples) < 3:
                examples.append({"id": pid, "ours": [mine["ident"], mine["km"]], "theirs": [theirs["ident"], theirs["km"]]})
    return {"places_compared": same + differ, "same_within_0.15_km": same, "different": differ, "examples": examples}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--offline", action="store_true", help="never download; stop if a raw file is missing")
    parser.add_argument("--fetch-only", action="store_true", help="download what is missing, build nothing")
    parser.add_argument("--report", action="store_true", help="print the results at the named places")
    args = parser.parse_args(argv)
    os.chdir(ROOT)
    started = time.time()
    dist = distance_check()

    shared_volcanoes = RAW_VOLCANOES_SHARED / "holocene_volcanoes.geojson"
    volcano_file = shared_volcanoes if shared_volcanoes.exists() else RAW_ERUPTIONS / "holocene_volcanoes.geojson"
    notes = {"volcanoes": ensure(VOLCANO_URL, volcano_file, args.offline),
             "eruptions": ensure(ERUPTION_URL, RAW_ERUPTIONS / "holocene_eruptions.geojson", args.offline),
             "geonames": ensure(GEONAMES_URL, RAW_GEONAMES / "cities1000.zip", args.offline),
             "roads": {name: ensure(url, RAW_ROADS / name, args.offline) for name, url in NE_FILES.items()}}
    if not RAW_AIRPORTS.exists():
        raise FileNotFoundError(f"{RAW_AIRPORTS} is missing (fetched by scripts/build_access_cells.py)")
    air_note = json.loads((RAW_AIRPORTS.parent / "download.json").read_text()) \
        if (RAW_AIRPORTS.parent / "download.json").exists() else {}
    notes["airports"] = {**air_note, "path": str(RAW_AIRPORTS), "bytes": RAW_AIRPORTS.stat().st_size,
                         "sha256": sha256_of(RAW_AIRPORTS)}
    notes["ne_version"] = (RAW_ROADS / "VERSION").read_text().strip()
    terms_try = try_terms_pages(args.offline)
    if args.fetch_only:
        return 0

    this_year = datetime.date.today().year
    volcanoes = read_volcanoes(volcano_file)
    active, eruption_tally = read_eruptions(RAW_ERUPTIONS / "holocene_eruptions.geojson", volcanoes, this_year)
    hol_list = list(volcanoes.values())
    hol_index = GridIndex([v["lat"] for v in hol_list], [v["lon"] for v in hol_list], cell_deg=2.0)
    act_list = list(active.values())
    act_index = GridIndex([v["lat"] for v in act_list], [v["lon"] for v in act_list], cell_deg=2.0)
    volc_counts = {"volcanoes": len(volcanoes), "volcanoes_erupted_since_%d" % SINCE: len(act_list)}
    settlements, settle_tally = read_settlements(RAW_GEONAMES / "cities1000.zip")
    airfields, air_tally = read_airfields(RAW_AIRPORTS)
    roads, road_tally = read_lines(RAW_ROADS / "ne_10m_roads.geojson", "road")
    rails, rail_tally = read_lines(RAW_ROADS / "ne_10m_railroads.geojson", "railway")
    lines = merge_lines(roads, rails)
    print(f"{len(volcanoes):,} volcanoes ({len(act_list)} erupted since {SINCE}), {settle_tally['kept']:,} "
          f"settlements, {air_tally['kept']:,} airfields, {len(lines['lat']):,} road and rail points "
          f"({time.time() - started:.1f} s)", file=sys.stderr)

    sets = {}
    for part, cells_file, out in (("moon", MOON_CELLS, MOON_OUT), ("mars", MARS_CELLS, MARS_OUT)):
        opt, opt_notes = read_optional(part)
        use_ice = part == "moon" and ("landcover_north" in opt or "landcover_south" in opt)
        places = load_places(cells_file)
        records = {}
        for p in places:
            volc = volcanic_result(p["lat"], p["lon"], active, act_index, act_list, hol_index, hol_list,
                                   opt.get("rock"), p["id"])
            records[p["id"]] = {"volcanic": volc,
                                "human": human_result(p["lat"], p["lon"], settlements, airfields, lines),
                                "small_tremors": tremor_result(p["id"], volc, opt, use_ice)}
        access_check = check_access(records, opt.get("access"))
        meta = make_meta(part, cells_file, records, opt_notes, eruption_tally, volc_counts, settle_tally, air_tally,
                         road_tally, rail_tally, notes, terms_try, dist, use_ice, access_check)
        write_json(out, {"meta": meta, "cells": records})
        sets[part] = (places, records)
        c = meta["counts"]
        print(f"{out}: {c['places']:,} places ({time.time() - started:.1f} s)\n  volcanic {c['volcanic']}\n"
              f"  young ground {c['young_volcanic_ground']}\n  human {c['human']}\n  help {c['help_within_reach']}\n"
              f"  tremors {c['small_tremors']}\n  tremors by source {c['small_tremors_by_source']}\n"
              f"  estimate where blind {c['small_tremors_our_estimate_only_where_catalogue_blind']}\n"
              f"  where the catalogue sees {c['check_where_the_catalogue_sees_small_tremors']}\n"
              f"  airfields vs access_cells {access_check}", file=sys.stderr)
    if args.report:
        print(report(sets))
    return 0


if __name__ == "__main__":
    sys.exit(main())

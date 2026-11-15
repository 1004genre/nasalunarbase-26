# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Small tremors near each place, and whether the catalogue can see them there.

Writes data/derived/tremors_cells.json (Moon areas, from grazing_cells.json)
and data/derived/mars_tremors.json (Mars squares, from mars_cells.json).

The question is not "are there big earthquakes" but "is there steady small
shaking that could disturb an instrument". For each place: how many small
events the USGS catalogue (ComCat) lists within 50 km and 100 km, in how many
of the 16 years 2010-2025 at least one was listed, their magnitudes, the
nearest one, and the smallest magnitude the catalogue reliably records in the
region (the "detection floor"). Where the catalogue cannot see small tremors
the counts are null, not 0: no record is not the same as no tremors.

What this is: a count of catalogued events. What it is not: not a measurement
of ground motion at the place, not a hazard map. A seismometer on site is the
only real test.

Source: the USGS FDSN event web service, https://earthquake.usgs.gov/fdsnws/event/1/
(CSV, at most 20,000 events an answer; a larger answer is refused with HTTP 400,
which this script records and answers by asking again in smaller pieces).
Every answer is kept under data/raw/usgs_small_quakes/, so a second run asks
for nothing twice.

    uv run python scripts/build_tremors.py            # fetch what is missing, build both files
    uv run python scripts/build_tremors.py --offline  # build from the answers on disk only
    uv run python scripts/build_tremors.py --moon     # Moon areas only (or --mars)
    uv run python scripts/build_tremors.py --report   # also print the check places

Results are written beside the old file and renamed into place.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import http.client
import json
import math
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "usgs_small_quakes"
MOON_CELLS = ROOT / "data" / "derived" / "grazing_cells.json"
MARS_CELLS = ROOT / "data" / "derived" / "mars_cells.json"
MOON_OUT = ROOT / "data" / "derived" / "tremors_cells.json"
MARS_OUT = ROOT / "data" / "derived" / "mars_tremors.json"

SERVICE = "https://earthquake.usgs.gov/fdsnws/event/1/query"
USER_AGENT = "twinfinder/0.1"
LIMIT = 20000
FIRST_YEAR, LAST_YEAR = 2010, 2025
N_YEARS = LAST_YEAR - FIRST_YEAR + 1
EARTH_R_KM = 6371.0088  # mean Earth radius (IUGG)

FLOOR_RADIUS_KM = 500.0
FLOOR_PERCENTILE = 10
FLOOR_MIN_EVENTS = 30
LOCAL_CHECK_KM = 200.0
STEADY_MIN_YEARS = 12
STEADY_MIN_RATE = 5.0

STATUS_SEEN = "small tremors are recorded here"
STATUS_UNSEEN = "small tremors cannot be seen in this catalogue here"
VERDICTS = ("steady small tremors", "occasional small tremors", "none recorded", "cannot tell")

# Each body: the band of the world it covers and the magnitudes it asks for.
BODIES = {
    "moon": {
        "mag_min": 1.0,
        "bands": [  # (tag, lat0, lat1, first span length)
            ("N", 55.0, 90.0, "month"),
            ("S", -90.0, -55.0, "year"),
        ],
        # the lowest magnitude fetched; a floor at or below seen_floor reads "recorded"
        "seen_floor": 2.5,
    },
    "mars": {
        "mag_min": 2.5,
        "bands": [("W", -90.0, 90.0, "quarter")],
        # Only magnitude 2.5 and up was fetched, so the 10th percentile can never be
        # under 2.5; a catalogue complete from 2.5 gives about 2.5 to 2.55. Under 2.6
        # is read as "at or below 2.5" here.
        "seen_floor": 2.6,
    },
}
MAG_MAX = 5.0  # exclusive


# ----------------------------------------------------------------------------- fetching

class TooMany(Exception):
    """The service refused the answer as larger than its 20,000-event limit."""


def log(*parts) -> None:
    print(*parts, flush=True)


def span_name(tag, t0, t1, lat0, lat1, lon0, lon1) -> str:
    return f"{tag}_{t0:%Y%m%d}_{t1:%Y%m%d}_lat{lat0:g}_{lat1:g}_lon{lon0:g}_{lon1:g}.csv"


def span_url(t0, t1, lat0, lat1, lon0, lon1, mag_min) -> str:
    params = {
        "format": "csv",
        "starttime": t0.isoformat(),
        "endtime": t1.isoformat(),
        "minlatitude": f"{lat0:g}",
        "maxlatitude": f"{lat1:g}",
        "minlongitude": f"{lon0:g}",
        "maxlongitude": f"{lon1:g}",
        "minmagnitude": f"{mag_min:g}",
        "maxmagnitude": f"{MAG_MAX:g}",
        "orderby": "time-asc",
    }
    return SERVICE + "?" + urllib.parse.urlencode(params)


def load_manifest(folder: Path) -> dict:
    path = folder / "manifest.json"
    if path.exists():
        return json.loads(path.read_text())
    return {}


def save_manifest(folder: Path, manifest: dict) -> None:
    write_json(folder / "manifest.json", manifest, indent=1)


def http_get(url: str) -> bytes:
    """GET with patience: the network has dropped twice tonight. 400 'too many' raises TooMany."""
    waits = [5, 10, 20, 40, 60, 90, 120, 180]
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(len(waits) + 1):
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                body = response.read()
                expected = response.headers.get("Content-Length")
                if expected is not None and len(body) != int(expected):
                    raise ConnectionError(f"short body: {len(body)} of {expected} bytes")
                if response.status == 204:
                    return b""
                if body and not body.endswith(b"\n"):
                    raise ConnectionError("answer does not end with a full line")
                return body
        except urllib.error.HTTPError as error:
            text = error.read().decode("utf-8", "replace")
            if error.code == 400 and ("exceeds" in text or str(LIMIT) in text):
                raise TooMany(text.strip()[:200]) from None
            if error.code not in (429, 500, 502, 503, 504):
                raise RuntimeError(f"HTTP {error.code} for {url}: {text[:300]}") from None
            reason = f"HTTP {error.code}"
        except (urllib.error.URLError, ConnectionError, TimeoutError, http.client.HTTPException, OSError) as error:
            reason = repr(error)
        if attempt == len(waits):
            raise RuntimeError(f"gave up after {attempt + 1} tries: {url} ({reason})")
        log(f"    try {attempt + 1} failed ({reason}); waiting {waits[attempt]} s")
        time.sleep(waits[attempt])
    raise AssertionError("unreachable")


def add_months(day: dt.date, months: int) -> dt.date:
    m = day.month - 1 + months
    return dt.date(day.year + m // 12, m % 12 + 1, 1)


def first_spans(kind: str) -> list[tuple[dt.date, dt.date]]:
    step = {"month": 1, "quarter": 3, "year": 12}[kind]
    out, day, end = [], dt.date(FIRST_YEAR, 1, 1), dt.date(LAST_YEAR + 1, 1, 1)
    while day < end:
        nxt = add_months(day, step)
        out.append((day, nxt))
        day = nxt
    return out


def split_span(t0, t1, lon0, lon1):
    """Smaller pieces: months first, then halves of longitude, then halves of time."""
    days = (t1 - t0).days
    if days > 31:
        pieces, day = [], t0
        while day < t1:
            nxt = min(add_months(day, 1), t1)
            pieces.append((day, nxt, lon0, lon1))
            day = nxt
        return pieces
    if lon1 - lon0 > 30:
        mid = (lon0 + lon1) / 2
        return [(t0, t1, lon0, mid), (t0, t1, mid, lon1)]
    if days > 1:
        mid = t0 + dt.timedelta(days=days // 2)
        return [(t0, mid, lon0, lon1), (mid, t1, lon0, lon1)]
    raise RuntimeError(f"cannot split {t0}..{t1} lon {lon0}..{lon1} further")


def fetch_body(body_name: str, offline: bool, budget_s: float | None) -> tuple[list[Path], dict]:
    """Every answer for one body, fetched if missing. Returns the CSV files and a coverage summary."""
    cfg = BODIES[body_name]
    folder = RAW / body_name
    folder.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest(folder)
    started = time.monotonic()
    files: list[Path] = []
    missing: list[str] = []
    asked = refused = 0
    stopped_at = None
    for tag, lat0, lat1, kind in cfg["bands"]:
        todo = [(t0, t1, -180.0, 180.0) for t0, t1 in first_spans(kind)]
        while todo:
            t0, t1, lon0, lon1 = todo.pop(0)
            name = span_name(tag, t0, t1, lat0, lat1, lon0, lon1)
            path, marker = folder / name, folder / (name + ".toomany")
            if marker.exists():
                todo[0:0] = split_span(t0, t1, lon0, lon1)
                continue
            if path.exists():
                files.append(path)
                continue
            if offline or stopped_at is not None:
                missing.append(name)
                continue
            if budget_s is not None and time.monotonic() - started > budget_s:
                stopped_at = f"{tag} {t0}"
                missing.append(name)
                continue
            url = span_url(t0, t1, lat0, lat1, lon0, lon1, cfg["mag_min"])
            now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
            asked += 1
            try:
                raw = http_get(url)
            except TooMany as why:
                refused += 1
                marker.write_text(why.args[0] + "\n")
                manifest[name] = {"url": url, "answer": "refused: more than 20000 events", "fetched": now}
                save_manifest(folder, manifest)
                log(f"  {name}: too many events, splitting")
                todo[0:0] = split_span(t0, t1, lon0, lon1)
                continue
            rows = max(raw.count(b"\n") - 1, 0)
            if rows >= LIMIT:  # never expected without a limit parameter, but never trust a cut
                refused += 1
                marker.write_text(f"answer held {rows} rows, at the limit\n")
                manifest[name] = {"url": url, "answer": f"{rows} rows, at the limit; split", "fetched": now}
                save_manifest(folder, manifest)
                todo[0:0] = split_span(t0, t1, lon0, lon1)
                continue
            part = path.with_name(path.name + ".part")
            part.write_bytes(raw)
            os.replace(part, path)
            manifest[name] = {"url": url, "rows": rows, "fetched": now}
            save_manifest(folder, manifest)
            files.append(path)
            log(f"  {name}: {rows} events")
            time.sleep(0.3)
    fetched = sorted(v["fetched"] for k, v in manifest.items() if (folder / k) in set(files))
    coverage = {
        "answers_used": len(files),
        "answers_missing": len(missing),
        "requests_this_run": asked,
        "refused_as_too_large_this_run": refused,
        "fetched_first": fetched[0] if fetched else None,
        "fetched_last": fetched[-1] if fetched else None,
        "stopped_at": stopped_at,
        "missing": missing[:50],
    }
    return files, coverage


# ----------------------------------------------------------------------------- events

def read_events(files: list[Path], mag_min: float) -> dict:
    """All events in the files, one row per event id, inside the years and magnitudes."""
    seen: set[str] = set()
    lat, lon, mag, year, typ = [], [], [], [], []
    for path in files:
        with open(path, newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                eid = row["id"]
                if eid in seen or not row["mag"]:
                    continue
                m = float(row["mag"])
                y = int(row["time"][:4])
                if not (mag_min <= m < MAG_MAX) or not (FIRST_YEAR <= y <= LAST_YEAR):
                    continue
                seen.add(eid)
                lat.append(float(row["latitude"]))
                lon.append(float(row["longitude"]))
                mag.append(m)
                year.append(y)
                typ.append(row["type"] or "unknown")
    types, type_code = np.unique(np.array(typ, dtype=object), return_inverse=True) if typ else (np.array([]), np.array([], int))
    return {
        "lat": np.array(lat), "lon": np.array(lon), "mag": np.array(mag),
        "year": np.array(year, dtype=np.int16), "type": type_code.astype(np.int16),
        "type_names": [str(t) for t in types],
    }


def great_circle_km(lat1, lon1, lat2, lon2):
    """Haversine distance on a sphere of the mean Earth radius."""
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dp, dl = p2 - p1, np.radians(lon2) - np.radians(lon1)
    a = np.sin(dp / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * EARTH_R_KM * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))


def check_distance() -> dict:
    """Pairs worked out by hand: a degree of the equator, a quarter of it, and across the pole at 80 N."""
    cases = [
        ((0.0, 0.0, 1.0, 0.0), EARTH_R_KM * math.pi / 180),        # 111.195 km
        ((0.0, 0.0, 0.0, 90.0), EARTH_R_KM * math.pi / 2),         # 10007.5 km
        ((80.0, 0.0, 80.0, 180.0), EARTH_R_KM * math.radians(20)),  # over the pole: 20 degrees of arc
        ((70.0, 179.5, 70.0, -179.5), None),                        # across the date line, about 38 km
    ]
    out = []
    for (a, b, c, d), want in cases:
        got = float(great_circle_km(a, b, c, d))
        if want is None:  # 1 degree of longitude at 70 N, small-angle: R * cos(70) * pi/180
            want = EARTH_R_KM * math.cos(math.radians(70)) * math.pi / 180
            tol = 0.01
        else:
            tol = 1e-6
        assert abs(got - want) <= tol * max(want, 1.0), (a, b, c, d, got, want)
        out.append({"from": [a, b], "to": [c, d], "km": round(got, 3), "by_hand_km": round(want, 3)})
    return {"formula": "haversine, sphere of radius 6371.0088 km", "checked_pairs": out}


class GridIndex:
    """Events sorted into 1-degree bins so a circle search reads only nearby bins."""

    def __init__(self, ev: dict):
        ilat = np.clip(np.floor(ev["lat"] + 90).astype(int), 0, 179)
        ilon = np.floor(ev["lon"] + 180).astype(int) % 360
        key = ilat * 360 + ilon
        order = np.argsort(key, kind="stable")
        self.ev = {k: v[order] for k, v in ev.items() if isinstance(v, np.ndarray)}
        counts = np.bincount(key, minlength=180 * 360)
        self.offsets = np.concatenate([[0], np.cumsum(counts)])

    def within(self, lat: float, lon: float, radius_km: float):
        """Indices (into the sorted arrays) and distances of events within radius_km."""
        d_deg = math.degrees(radius_km / EARTH_R_KM)
        lat_lo, lat_hi = lat - d_deg, lat + d_deg
        r0 = max(int(math.floor(lat_lo + 90)), 0)
        r1 = min(int(math.floor(lat_hi + 90)), 179)
        if lat_hi >= 90 or lat_lo <= -90:
            half = 180.0
        else:
            half = math.degrees(math.asin(min(1.0, math.sin(math.radians(d_deg)) / math.cos(math.radians(lat))))) + 1.0
        if half >= 180:
            col_ranges = [(0, 359)]
        else:
            c0 = int(math.floor(lon - half + 180))
            c1 = int(math.floor(lon + half + 180))
            if c0 < 0:
                col_ranges = [(c0 + 360, 359), (0, c1)]
            elif c1 > 359:
                col_ranges = [(c0, 359), (0, c1 - 360)]
            else:
                col_ranges = [(c0, c1)]
        pieces = []
        for r in range(r0, r1 + 1):
            for c0, c1 in col_ranges:
                s, e = self.offsets[r * 360 + c0], self.offsets[r * 360 + c1 + 1]
                if e > s:
                    pieces.append(np.arange(s, e))
        if not pieces:
            return np.array([], int), np.array([])
        idx = np.concatenate(pieces)
        dist = great_circle_km(lat, lon, self.ev["lat"][idx], self.ev["lon"][idx])
        keep = dist <= radius_km
        return idx[keep], dist[keep]


# ----------------------------------------------------------------------------- figures

def status_for(floor, seen_floor: float) -> str:
    if floor is None or floor > 3.5:
        return STATUS_UNSEEN
    if floor <= seen_floor:
        return STATUS_SEEN
    return f"only tremors of magnitude {floor:.1f} and above are recorded here"


def figures_for(index: GridIndex, eq_type: int | None, lat: float, lon: float, seen_floor: float) -> dict:
    ev = index.ev
    idx, dist = index.within(lat, lon, FLOOR_RADIUS_KM)
    mags = ev["mag"][idx]
    floor = round(float(np.percentile(mags, FLOOR_PERCENTILE)), 2) if len(idx) >= FLOOR_MIN_EVENTS else None
    status = status_for(floor, seen_floor)
    floor_check = None
    if status == STATUS_SEEN:
        # A 500 km circle can borrow a good network's reach from across a border (western
        # Alaska seen from Chukotka, Texas from Coahuila). Trust "recorded" only where the
        # catalogue lists at least one small event near the place itself.
        if ((dist <= LOCAL_CHECK_KM) & (mags < seen_floor)).any():
            floor_check = "passed"
        else:
            floor_check = f"failed: no event under magnitude {seen_floor:g} catalogued within {LOCAL_CHECK_KM:g} km"
            status = STATUS_UNSEEN
    near = dist <= 100.0
    n100 = int(near.sum())
    n50 = int((dist <= 50.0).sum())
    years100 = int(len(np.unique(ev["year"][idx[near]]))) if n100 else 0
    rate100 = n100 / N_YEARS
    out = {
        "small_per_year_50km": round(n50 / N_YEARS, 2),
        "small_per_year_100km": round(rate100, 2),
        "years_with_events_100km": years100,
        "median_magnitude_100km": round(float(np.median(mags[near])), 2) if n100 else None,
        "largest_small_magnitude_100km": round(float(mags[near].max()), 2) if n100 else None,
        "nearest_small_event_km": round(float(dist.min()), 1) if len(idx) else None,
        "share_not_earthquake_100km": (round(float((ev["type"][idx[near]] != eq_type).mean()), 2) if n100 else None),
        "events_500km_for_floor": int(len(idx)),
        "detection_floor": floor,
        "floor_check": floor_check,
        "status": status,
        "catalogued_anyway_100km": None,
    }
    if status == STATUS_UNSEEN:
        out["verdict"] = "cannot tell"
        for key in ("small_per_year_50km", "small_per_year_100km", "years_with_events_100km"):
            out[key] = None  # no record is not the same as no tremors
        if n100:  # larger events the catalogue does list here: a sign of activity, not a rate of small tremors
            out["catalogued_anyway_100km"] = {
                "events": n100, "years": years100, "smallest_magnitude": round(float(mags[near].min()), 2),
            }
    elif n100 == 0:
        # "none recorded" only where the catalogue sees small tremors; where it sees only
        # magnitude 2.6+ (or whatever the floor is), an empty circle says nothing about M1-2.
        out["verdict"] = "none recorded" if status == STATUS_SEEN else "cannot tell"
    elif years100 >= STEADY_MIN_YEARS and rate100 >= STEADY_MIN_RATE:
        out["verdict"] = "steady small tremors"
    else:
        out["verdict"] = "occasional small tremors"
    return out


def rule_of_thumb(seen_floor: float, mag_min: float) -> dict:
    floor_words = (
        f"The detection floor is the 10th percentile of the magnitudes of all catalogued events "
        f"from {mag_min:g} to under {MAG_MAX:g} within {FLOOR_RADIUS_KM:g} km over the 16 years "
        f"(null if fewer than {FLOOR_MIN_EVENTS} events)."
    )
    if seen_floor != 2.5:
        floor_words += (
            f" Only magnitude {mag_min:g} and up was fetched here, so the floor cannot be read below "
            f"{mag_min:g}; a floor under {seen_floor:g} is read as 'at or below 2.5'."
        )
    return {
        "words": (
            "our rule of thumb, not an engineering standard: 'steady small tremors' when catalogued events "
            f"fell within 100 km in at least {STEADY_MIN_YEARS} of the 16 years and at a rate of at least "
            f"{STEADY_MIN_RATE:g} a year; 'occasional small tremors' when at least one fell within 100 km but "
            "not steadily (in 1 to 11 of the years, or under 5 a year; 1 to 3 years is usually a single swarm); "
            "'none recorded' when the catalogue records small tremors here and none was catalogued within "
            "100 km; 'cannot tell' when the catalogue cannot see small tremors here, and also when it sees only "
            "tremors above some magnitude between 2.5 and 3.5 and none was catalogued within 100 km (an empty "
            "circle then says nothing about smaller ones)."
        ),
        "status_words": (
            floor_words + " 'small tremors are recorded here' when the floor is at or below 2.5; "
            "'only tremors of magnitude M and above are recorded here' when it is above 2.5 and at most 3.5; "
            "'small tremors cannot be seen in this catalogue here' when it is above 3.5 or there are too few "
            "events to tell. A floor at or below 2.5 counts only if the catalogue also lists at least one event "
            f"under that magnitude within {LOCAL_CHECK_KM:g} km of the place (field floor_check); otherwise the low "
            "floor is borrowed from a better-watched network farther away, as western Alaska seen from Chukotka or "
            "Texas seen from Coahuila, and the place is read as 'cannot be seen'. Where small tremors cannot be "
            "seen the counts are null, never 0: no record is not the same as no tremors."
        ),
        "steady_min_years": STEADY_MIN_YEARS,
        "steady_min_per_year": STEADY_MIN_RATE,
        "floor_radius_km": FLOOR_RADIUS_KM,
        "floor_percentile": FLOOR_PERCENTILE,
        "floor_min_events": FLOOR_MIN_EVENTS,
        "status_thresholds": {"recorded_at_or_below": 2.5, "cannot_see_above": 3.5},
    }


def field_words(mag_min: float) -> dict:
    rng = f"magnitude {mag_min:g} to under {MAG_MAX:g}"
    return {
        "small_per_year_50km": f"mean number a year of catalogued events of {rng} within 50 km of the place centre, 2010-2025; null when the catalogue cannot see small tremors here",
        "small_per_year_100km": f"the same within 100 km",
        "years_with_events_100km": "in how many of the 16 years at least one such event was catalogued within 100 km (the 'consistent' part: 14 of 16 is steady, 1 of 16 is one swarm); null when the catalogue cannot see small tremors here",
        "median_magnitude_100km": "median magnitude of those events within 100 km (null if none)",
        "largest_small_magnitude_100km": "largest magnitude among them, always under 5 (null if none)",
        "nearest_small_event_km": f"distance to the nearest catalogued event of {rng}, searched out to {FLOOR_RADIUS_KM:g} km (null if none that close)",
        "share_not_earthquake_100km": "share of the events within 100 km that the catalogue types as something other than an earthquake (quarry blast, explosion, ice quake and so on); these shake instruments too and are counted",
        "events_500km_for_floor": f"how many catalogued events of {rng} lie within {FLOOR_RADIUS_KM:g} km: the sample the floor is read from",
        "detection_floor": "estimated smallest magnitude the catalogue reliably records in this region: the 10th percentile of the magnitudes within 500 km (null if fewer than 30 events)",
        "floor_check": f"'passed' or 'failed: ...' where the floor was at or below the 'recorded' line: whether at least one event under it is catalogued within {LOCAL_CHECK_KM:g} km; a failed check turns the status to 'cannot be seen' (null where the check does not apply)",
        "status": "plain words for the floor",
        "catalogued_anyway_100km": "only where small tremors cannot be seen: the events the catalogue still lists within 100 km (count, years, smallest magnitude), mostly magnitude 4 and up; a sign of activity and a lower bound, not a rate of small tremors (null otherwise)",
        "verdict": "plain verdict for instruments, by the rule of thumb in meta.rule_of_thumb",
    }


WHAT_IT_IS_NOT = (
    "A count of catalogued events, not a measurement of ground motion at the place; "
    "not a hazard map; a seismometer on site is the only real test. The catalogue lists only what "
    "nearby seismometers detected, so its reach differs by region: in Alaska it sees magnitude 1 to 2, "
    "in the remote Arctic, Siberia and Antarctica almost nothing under 4. The networks also grew during the "
    "16 years (north of 55 N the catalogue lists about 1.6 times as many events of magnitude 1 to 5 a year "
    "in 2017-2025 as in 2010-2015; in some places, such as the Kobuk valley, several times as many), so early "
    "years undercount and 'years with events' leans low. Distances are from the place centre."
)


def build(body_name: str, cells: list[tuple[str, float, float]], files: list[Path], coverage: dict) -> dict:
    cfg = BODIES[body_name]
    t_start = time.monotonic()
    ev = read_events(files, cfg["mag_min"])
    log(f"{body_name}: {len(ev['mag'])} events from {len(files)} answers")
    index = GridIndex(ev)
    names = ev["type_names"]
    eq_type = names.index("earthquake") if "earthquake" in names else None
    out_cells = {}
    for cid, lat, lon in cells:
        out_cells[cid] = figures_for(index, eq_type, lat, lon, cfg["seen_floor"])
    by_verdict = {v: 0 for v in VERDICTS}
    by_status: dict[str, int] = {}
    for f in out_cells.values():
        by_verdict[f["verdict"]] += 1
        s = f["status"]
        key = s if s in (STATUS_SEEN, STATUS_UNSEEN) else "only tremors of magnitude M and above are recorded here (M between 2.5 and 3.5)"
        by_status[key] = by_status.get(key, 0) + 1
    type_counts = {names[i]: int(n) for i, n in enumerate(np.bincount(ev["type"], minlength=len(names)))}
    bands = [f"{lat0:g} to {lat1:g} degrees latitude" for _, lat0, lat1, _ in cfg["bands"]]
    meta = {
        "what": (
            "Small tremors near each place: catalogued events of "
            f"magnitude {cfg['mag_min']:g} to under {MAG_MAX:g}, how often, how steadily, how large, and "
            "whether the catalogue can see small tremors there at all."
        ),
        "source": "USGS ANSS Comprehensive Earthquake Catalog (ComCat) via the FDSN event web service, https://earthquake.usgs.gov/fdsnws/event/1/ (public domain, U.S. Geological Survey)",
        "query": {
            "template": span_url(dt.date(FIRST_YEAR, 1, 1), dt.date(FIRST_YEAR, 2, 1), cfg["bands"][0][1], cfg["bands"][0][2], -180, 180, cfg["mag_min"]),
            "bands": bands,
            "spans": "Moon: months north of 55 N, years south of 55 S; Mars: quarters worldwide; any answer refused as over 20,000 events was asked again by month, then by halves of longitude",
            "event_types": "all types the catalogue lists (earthquakes, quarry blasts, explosions, ice quakes and others); duplicates across spans removed by event id",
            "raw_answers": f"data/raw/usgs_small_quakes/{body_name}/ (manifest.json lists each URL, its row count and when it was fetched)",
        },
        "years": f"{FIRST_YEAR}-{LAST_YEAR} ({N_YEARS} years)",
        "magnitude_range": f"{cfg['mag_min']:.1f} up to (not including) {MAG_MAX:.1f}, any magnitude type, as the catalogue gives it",
        "rule_of_thumb": rule_of_thumb(cfg["seen_floor"], cfg["mag_min"]),
        "fields": field_words(cfg["mag_min"]),
        "what_it_is_not": WHAT_IT_IS_NOT,
        "counts": {
            "places": len(out_cells),
            "by_verdict": by_verdict,
            "by_status": by_status,
            "events_used": int(len(ev["mag"])),
            "events_by_type": type_counts,
        },
        "fetched": coverage,
        "distance": check_distance(),
        "grid_index": "events in 1-degree bins; each search reads only the bins that can reach the circle, then measures great-circle distance",
        "made": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "made_by": "agent TREMORS, scripts/build_tremors.py",
    }
    if body_name == "moon":
        meta["edge_note"] = (
            "Events were fetched poleward of 55 degrees. For areas between 59 and about 59.5 N the 500 km "
            "circle reaches a little south of 55 N, so the floor there is read from slightly fewer events."
        )
    else:
        meta["edge_note"] = (
            "Only magnitude 2.5 and up was fetched worldwide, so 'small' here means 2.5 to under 5 and the "
            "Mars squares cannot be compared one to one with the Moon areas (magnitude 1 and up)."
        )
    log(f"{body_name}: figures for {len(out_cells)} places in {time.monotonic() - t_start:.0f} s")
    return {"meta": meta, "cells": out_cells}


# ----------------------------------------------------------------------------- files

def write_json(path: Path, value, indent=None) -> None:
    """Write beside the file and rename into place, so a reader never sees half a file."""
    side = path.with_name(path.name + ".part")
    with open(side, "w", encoding="utf-8") as out:
        json.dump(value, out, indent=indent, allow_nan=False, separators=None if indent else (",", ":"))
    os.replace(side, path)


def moon_cells() -> list[tuple[str, float, float]]:
    cells = json.loads(MOON_CELLS.read_text())["cells"]
    return [(c["id"], float(c["lat"]), float(c["lon"])) for c in cells]


def mars_cells() -> list[tuple[str, float, float]]:
    cells = json.loads(MARS_CELLS.read_text())["cells"]
    return [(cid, float(c["lat"]), float(c["lon"])) for cid, c in cells.items()]


CHECK_PLACES = [
    ("south-west Iceland (Reykjanes)", "63.8_-22.6"),
    ("Haughton crater", "75.3_-90.0"),
    ("near Ulukhaktok", "70.7_-117.9"),
    ("Kobuk valley", "67.0_-159.0"),
    ("Longyearbyen", "78.2_15.6"),
    ("Pechora Sea coast", "68.9_54.3"),
    ("Vestfold Hills", "-68.5_78.0"),
]


def report(result: dict, places=CHECK_PLACES) -> None:
    for label, cid in places:
        f = result["cells"].get(cid)
        if f is None:
            log(f"  {label} {cid}: not in file")
            continue
        log(
            f"  {label} {cid}: {f['verdict']} | {f['status']} | floor {f['detection_floor']} from "
            f"{f['events_500km_for_floor']} | /yr 50km {f['small_per_year_50km']} 100km {f['small_per_year_100km']} | "
            f"years {f['years_with_events_100km']} | median {f['median_magnitude_100km']} max "
            f"{f['largest_small_magnitude_100km']} | nearest {f['nearest_small_event_km']} km"
        )
    log("  by verdict:", result["meta"]["counts"]["by_verdict"])
    log("  by status:", result["meta"]["counts"]["by_status"])


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--offline", action="store_true", help="use only the answers already on disk")
    parser.add_argument("--moon", action="store_true", help="Moon areas only")
    parser.add_argument("--mars", action="store_true", help="Mars squares only")
    parser.add_argument("--mars-minutes", type=float, default=None, help="stop asking for Mars spans after this many minutes")
    parser.add_argument("--report", action="store_true", help="print the check places and counts")
    args = parser.parse_args(argv)
    bodies = ["moon", "mars"] if args.moon == args.mars else (["moon"] if args.moon else ["mars"])
    check_distance()
    for body in bodies:
        log(f"{body}: fetching what is missing" if not args.offline else f"{body}: reading answers on disk")
        budget = args.mars_minutes * 60 if (body == "mars" and args.mars_minutes) else None
        files, coverage = fetch_body(body, args.offline, budget)
        if coverage["answers_missing"]:
            log(f"{body}: {coverage['answers_missing']} answers missing (stopped at {coverage['stopped_at']}); "
                "the file says so in meta.fetched")
        cells = moon_cells() if body == "moon" else mars_cells()
        result = build(body, cells, files, coverage)
        if coverage["answers_missing"]:
            result["meta"]["incomplete"] = (
                f"{coverage['answers_missing']} of the spans were not fetched; per-year figures divide by 16 "
                "years all the same, so they are too low"
            )
        out = MOON_OUT if body == "moon" else MARS_OUT
        write_json(out, result)
        log(f"{body}: wrote {out.relative_to(ROOT)}")
        if args.report:
            if body == "moon":
                report(result)
            else:
                report(result, places=[])
    return 0


if __name__ == "__main__":
    sys.exit(main())

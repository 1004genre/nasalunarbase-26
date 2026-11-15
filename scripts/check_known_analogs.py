# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Check our list of known analog sites against two published lists, and describe the places that head the ranking.

Writes data/reference/known_analogs_check.json with:
  missing_from_our_list   sites poleward of 55 degrees in the ESA / Open University Catalogue of Planetary
                          Analogues (2012) or in the table of the Wikipedia page "Terrestrial analogue site"
                          that have no entry of ours within 50 km (the radius the pipeline uses for "known")
  doubtful_in_our_list    entries of ours whose coordinates look wrong or stand for a whole region
  top_places              for each place that heads the ranking: whether sources show space-analog or polar
                          field work there, and the nearest station and airfield with distances

The catalogue coordinates and the findings about each place were transcribed by hand on 14 November 2026 from
the raw files in data/raw/analog_catalogues/ and from the pages linked beside each entry; they are the tables
in this file. Everything that depends on files other members rewrite (the scored cells, our own list) is
computed here, so the file can be refreshed at any time:

    uv run python scripts/check_known_analogs.py

Missing inputs are tolerated: without cells_scored.json the cell counts are null, without the COMNAP file the
Antarctic stations are null. Unknown is null, never 0.
"""
import argparse
import json
import math
import os
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KNOWN = ROOT / "data" / "reference" / "known_analogs.json"
ANTARCTIC = ROOT / "data" / "reference" / "antarctic_sites.json"
WIKI = ROOT / "data" / "raw" / "analog_catalogues" / "wikipedia_Terrestrial_analogue_site.wikitext"
COMNAP = ROOT / "data" / "raw" / "antarctica" / "comnap_facilities" / "antarctic_facilities_4326.geojson"
CELLS = ROOT / "data" / "derived" / "cells_scored.json"
OUT = ROOT / "data" / "reference" / "known_analogs_check.json"

RADIUS_KM = 50.0        # the pipeline calls a cell "known" within this distance of a listed site
MIN_ABS_LAT = 55.0
OFFSET_TOLERANCE_KM = 10.0
FAR_KM = 800.0          # beyond this a "nearest" station or airfield is reported as null
EARTH_RADIUS_KM = 6371.0

CATALOGUE = "ESA / Open University, The Catalogue of Planetary Analogues (2012)"
CATALOGUE_URL = "https://freight.cargo.site/m/D1821053255089660420449933921929/The-Catalogue-of-Planetary-Analogues.pdf"
WIKI_TABLE = "Wikipedia, Terrestrial analogue site (table read 14 November 2026)"
WIKI_URL = "https://en.wikipedia.org/wiki/Terrestrial_analogue_site"
COMNAP_CREDIT = ("COMNAP Antarctic Facilities list, version 3.2.0 of 13 May 2019 as served by the SCAR Antarctic Digital Database "
                 "(COMNAP 2019); copyright COMNAP, free for educational and non-commercial use only")


def km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in kilometres on a sphere of radius 6371 km."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat, dlon = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(a)))


def nearest(lat: float, lon: float, points: list[dict], max_km: float | None = None) -> dict | None:
    """The closest of points (each with name, lat, lon) with its distance in km.

    None for an empty list, and None when the closest lies beyond max_km (a station 2,000 km away is no answer)."""
    best = None
    for point in points:
        if point.get("lat") is None or point.get("lon") is None:
            continue
        d = km(lat, lon, point["lat"], point["lon"])
        if best is None or d < best["km"]:
            best = {**point, "km": round(d, 1)}
    if best is not None and max_km is not None and best["km"] > max_km:
        return None
    return best


# ---------------------------------------------------------------- the Wikipedia table

def _plain(text: str) -> str:
    """Wiki markup to plain words: links keep their label, files, templates and tags go."""
    text = re.sub(r"\[\[(?:File|Image):[^\]]*\]\]", "", text)
    text = re.sub(r"\[\[[^\]|]*\|([^\]]*)\]\]", r"\1", text)
    text = re.sub(r"\[\[([^\]]*)\]\]", r"\1", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\{\{.*", "", text, flags=re.S)
    return re.sub(r"\s+", " ", text).strip(" ,")


def _number(row: str, key: str) -> float | None:
    found = re.search(rf"{key}\s*=\s*(-?\d+(?:\.\d+)?)", row)
    return float(found.group(1)) if found else None


def _angle(row: str, axis: str) -> float | None:
    """lat or lon of a {{Location map}} row: decimal degrees, or degrees, minutes, seconds and a direction."""
    degrees = _number(row, f"{axis}_deg")
    if degrees is None:
        return None
    value = abs(degrees) + (_number(row, f"{axis}_min") or 0.0) / 60 + (_number(row, f"{axis}_sec") or 0.0) / 3600
    direction = re.search(rf"{axis}_dir\s*=\s*([NSEW])", row)
    negative = degrees < 0 or (direction is not None and direction.group(1) in "SW")
    return -value if negative else value


def parse_wikipedia_table(text: str) -> list[dict]:
    """Name, lat and lon of every row of the first table. A row without a point keeps lat and lon as None."""
    start = text.find("{|")
    if start < 0:
        return []
    table = text[start:].split("\n|}")[0]
    rows = []
    for chunk in table.split("\n|-")[1:]:
        body = chunk.split("\n", 1)[1] if "\n" in chunk else ""
        if not body.strip():
            continue
        if "lat_deg" in body:
            label = re.search(r"label\s*=[ \t]*([^\n|}]*)", body)
            first = re.split(r"\n\s*\|", "\n" + body)[1] if "\n|" in "\n" + body else body
            name = (label.group(1).strip() if label else "") or _plain(first.split("|")[-1])
            rows.append({"name": name, "lat": _angle(body, "lat"), "lon": _angle(body, "lon")})
            continue
        if body.lstrip().startswith("!"):
            continue                                   # the header row
        cells = [c for c in re.split(r"\n\|", "\n" + body)[1:]]
        if not cells:
            continue
        pair = re.search(r"(-?\d+\.\d+)\s*,\s*(-?\d+\.\d+)", cells[1]) if len(cells) > 1 else None
        rows.append({"name": _plain(cells[0]),
                     "lat": float(pair.group(1)) if pair else None,
                     "lon": float(pair.group(2)) if pair else None})
    return rows


# ---------------------------------------------------------------- comparing lists

def compare(published: list[dict], ours: list[dict], radius_km: float = RADIUS_KM,
            min_abs_lat: float = MIN_ABS_LAT) -> tuple[list[dict], list[dict]]:
    """Published sites poleward of min_abs_lat, split into (missing, covered).

    Missing: no entry of ours within radius_km. Covered: one is. Each row gains nearest_of_ours
    {name, km}. Sites without a point, or nearer the equator, are left out of both lists."""
    missing, covered = [], []
    for site in published:
        if site.get("lat") is None or site.get("lon") is None or abs(site["lat"]) < min_abs_lat:
            continue
        hit = nearest(site["lat"], site["lon"], ours)
        row = {**site, "nearest_of_ours": {"name": hit["name"], "km": hit["km"]} if hit else None}
        (missing if hit is None or hit["km"] > radius_km else covered).append(row)
    return missing, covered


def _ours_named(ours: list[dict], prefix: str) -> dict | None:
    return next((o for o in ours if o["name"].startswith(prefix)), None)


def offsets(published: list[dict], ours: list[dict], pairs: dict[str, str],
            tolerance_km: float = OFFSET_TOLERANCE_KM) -> list[dict]:
    """Entries of ours that lie further than tolerance_km from every published point of the same site.

    pairs maps a published name to the start of our name for the same site. Where several published points
    exist for one entry (a rounded regional point and an exact one), agreement with any of them is enough."""
    worst, agreed = {}, set()
    for site in published:
        mine = _ours_named(ours, pairs[site["name"]]) if site["name"] in pairs else None
        if mine is None or site.get("lat") is None:
            continue
        apart = km(site["lat"], site["lon"], mine["lat"], mine["lon"])
        if apart <= tolerance_km:
            agreed.add(mine["name"])                     # one published point agrees: the entry stands
        elif mine["name"] not in worst or apart > worst[mine["name"]]["km_apart"]:
            worst[mine["name"]] = {
                "ours": mine["name"], "our_lat": mine["lat"], "our_lon": mine["lon"],
                "our_coord_quality": mine.get("coord_quality"),
                "published_name": site["name"], "published_lat": site["lat"], "published_lon": site["lon"],
                "km_apart": round(apart, 1), "listed_in": site.get("listed_in"), "source_url": site.get("source_url"),
                "why": f"our point is {apart:.0f} km from the point printed for the same site, and no published point agrees with it"}
    return [row for name, row in worst.items() if name not in agreed]


def shared_runs(entries: list[dict], text: str, words: int = 6) -> int:
    """How many entries have a description that repeats a run of that many words from text (case and spacing ignored)."""
    flat = " ".join(text.lower().split())
    count = 0
    for entry in entries:
        parts = (entry.get("analog_for") or "").lower().split()
        if any(" ".join(parts[i:i + words]) in flat for i in range(max(0, len(parts) - words + 1)) if len(parts) >= words):
            count += 1
    return count


def cells_near(lat: float, lon: float, cells: list[dict] | None, radius_km: float = RADIUS_KM) -> dict | None:
    """How many scored cells lie within radius_km and how many of them carry little_known. None without cells."""
    if cells is None:
        return None
    close = [c for c in cells if km(lat, lon, c["lat"], c["lon"]) <= radius_km]
    return {"cells": len(close), "flagged_little_known": sum(1 for c in close if c.get("little_known") is True)}


# ---------------------------------------------------------------- transcribed tables

def _cat(name, lat, lon, as_printed, chapter, analog_for, note=None):
    return {"name": name, "lat": lat, "lon": lon, "as_printed": as_printed, "chapter": chapter,
            "analog_for": analog_for, "note": note, "listed_in": CATALOGUE, "source_url": CATALOGUE_URL}


# Every site of the catalogue poleward of 55 degrees. lat and lon are our reading of the printed value.
CATALOGUE_SITES = [
    _cat("McMurdo Dry Valleys (general point)", -77.5, 163.0, "77°30'S 163°00'E", "1", "Mars: cold dry valleys, polygons, gullies"),
    _cat("Blood Falls", -77.722053, 162.271861, "77.722053°S, 162.271861°E", "1.6.1", "Mars: subglacial brine"),
    _cat("Wright Valley, South Fork study area", -77.556, 161.172, "77.3336°S, 161.1724°E", "1.6.2", "Mars: brines, Don Juan Pond basin",
         "printed as decimal degrees but reads as 77°33.36' S (the South Fork with Don Juan Pond lies at 77.56 S); taken as that"),
    _cat("Beacon Valley", -77.842, 160.844, "77.842°S 160.844°E", "1.6.3", "Mars: buried ice, polygons"),
    _cat("Axel Heiberg Island (McGill Arctic Research Station area)", 79.4333, -90.7667, "79°26' N, 90°46' W", "4", "Mars: cold saline springs, permafrost"),
    _cat("Gypsum Hill saline springs, Axel Heiberg Island", 79.409175, -90.732765, "Gypsum Hill: 79.409175N, 90.732765W", "4.6.1", "Mars: perennial saline springs"),
    _cat("Polygonal terrain, Axel Heiberg Island", 79.386, -90.843, "79.2314N, 90.505907W", "4.6.2", "Mars: polygon terrain",
         "printed value read as degrees and decimal minutes (79°23.14' N, 90°50.59' W); as decimal degrees it would lie 25 km to the south-east"),
    _cat("Colour Lake fen, Axel Heiberg Island", 79.415, -90.757, "79.24918N, 90.45424W", "4.6.3", "Mars: cold wetland, astrobiology",
         "printed value read as degrees and decimal minutes (79°24.918' N, 90°45.424' W), which is where Colour Lake is"),
    _cat("The Golden Deposit", 65.1994, -124.6375, "65° 11'58\"N, 124° 38'15\"W", "9", "Mars: jarosite deposit from cold acid seeps"),
    _cat("Haughton impact structure", 75.3667, -89.6833, "75° 22' N, 89° 41' W", "10", "Moon and Mars: impact crater in polar desert"),
    _cat("Haughton hydrothermal supersite", 75.3514, -89.5444, "75.21.5N 89.32.40W", "10.6.1", "Mars: impact hydrothermal deposits",
         "printed without units; read as 75°21'05\" N, 89°32'40\" W"),
    _cat("Haughton ice wedge polygons", 75.3574, -88.6798, "75.21.26.8 N 88.40.47.2 W", "10.6.3", "Mars: polygon terrain"),
    _cat("Iceland (general point)", 65.0, -18.0, "65° 0' 0\" N, 18° 0' 0\" W", "12", "Moon and Mars: volcanism with ice"),
    _cat("Askja", 65.03, -16.75, "65° 1' 48\" N, 16° 45' 0\" W", "12.6.1", "Moon: Apollo training site; volcanic caldera"),
    _cat("Eyjafjallajokull", 63.6333, -19.6, "63° 38' 0\" N, 19° 36' 0\" W", "12.6.2", "Mars: volcano and ice, volcanic habitats"),
    _cat("Krysuvik", 63.8958, -22.0525, "63° 53' 45.02\" N, 22° 3' 8.96\" W", "12.6.3", "Mars: hydrothermal alteration"),
    _cat("Laki flow field (1783 to 1784)", 64.0647, -18.2261, None, "12.6.4", "Mars: flood lava",
         "the catalogue prints no coordinates; the point is the one on the Wikipedia page for Laki"),
    _cat("Klyuchevskaya volcano group, Kamchatka", 56.056, 160.6441, None, "13.6.2", "Moon and Mars: volcanic structures and deposits",
         "the catalogue gives Kamchatka only as 51 to 61 N; the point is the one on the Wikipedia page for Klyuchevskaya Sopka"),
    _cat("Mistastin Lake crater", 55.8833, -63.3, "N 55° 53' W 63° 18'", "17", "Moon: impact crater in anorthosite"),
    _cat("Svalbard (general point)", 78.0, 16.0, "78°N 16°E", "26", "Mars: AMASE instrument tests"),
    _cat("Bockfjord Volcanic Complex", 79.4981, 13.2056, "79°29'53\" N, 13°12'20\" E", "26.6.1", "Mars: carbonates in volcanic rocks; AMASE"),
    _cat("Ebbadalen Formation, Billefjorden", 78.7097, 16.7178, "78°42'35\" N, 16°43'04\" E", "26.6.2", "Mars: sulphate evaporites; AMASE cliff rover tests"),
    _cat("Murchison Fjord (AMASE)", 79.8786, 18.4881, "79°52'43\" N, 18°29'17\" E", "26.6.3", "Mars: old stromatolites and carbonates sampled for biosignatures; AMASE"),
    _cat("Adventtoppen and Hiorthfjellet", 78.273, 15.745, "78° 16' 22.8\" N, 15° 44' 42\" E", "26.6.4", "Mars: small fans and gullies"),
]

# A catalogue point we could not place: it is listed so nobody trips over it later.
CATALOGUE_MISPRINTS = [
    {"name": "Haughton impact breccia supersite", "as_printed": "75.11.53N, 81.51.4W", "chapter": "10.6.2",
     "note": "81.5 W is 215 km east of the crater; almost certainly a misprint for 89.5 W. Left out of the comparison.",
     "source_url": CATALOGUE_URL},
]

# Which entry of ours is the same site as a published one (published name -> start of our name).
SAME_SITE = {
    "McMurdo Dry Valleys (general point)": "McMurdo Dry Valleys",
    "Blood Falls": "Blood Falls",
    "Wright Valley, South Fork study area": "Don Juan Pond",
    "Beacon Valley": "Beacon Valley",
    "Gypsum Hill saline springs, Axel Heiberg Island": "Axel Heiberg Island springs",
    "The Golden Deposit": "The Golden Deposit",
    "Haughton impact structure": "Haughton impact structure",
    "Askja": "Askja",
    "Eyjafjallajokull": "Fimmvorduhals",
    "Mistastin Lake crater": "Mistastin",
    "Svalbard (general point)": "Svalbard (AMASE)",
    "Bockfjord Volcanic Complex": "Bockfjord Volcanic Complex",
    "Haughton impact Crater": "Haughton impact structure",
    "Svalbard": "Svalbard (AMASE)",
    "McMurdo Dry Valleys": "McMurdo Dry Valleys",
    "Concordia station": "Concordia Station",
    "CHILL-ICE, Iceland": "CHILL-ICE",
}

# Entries of ours flagged by reading, not by arithmetic.
HAND_FLAGS = [
    {"ours_starts_with": "Svalbard (AMASE)",
     "why": "78.0 N 16.0 E is the rounded point both sources print for the whole archipelago, yet our file marks it "
            "coord_quality 'source'. No AMASE field site is there: the catalogue's four Svalbard sites lie 30 to 215 km "
            "away (distances below). Cells within 50 km of this point are called known for a site that is elsewhere, and "
            "cells at the real sites are not.",
     "suggest": "replace it with the four catalogue sites (Bockfjord is already ours), or mark it as a regional point"},
    {"ours_starts_with": "Iceland field sites (Europlanet",
     "why": "64.9 N 18.5 W is the middle of Iceland, beside the Hofsjokull ice cap; it stands for a programme with several "
            "sites, not for a place. Our file marks it 'estimated', which is honest, but any cell within 50 km is called known.",
     "suggest": "replace it with the named Icelandic sites (Krysuvik and Laki are missing, see missing_from_our_list)"},
]


def _other(name, lat, lon, analog_for, source_url, evidence, coord_source_url):
    return {"name": name, "lat": lat, "lon": lon, "analog_for": analog_for, "source_url": source_url,
            "evidence": evidence, "coord_source_url": coord_source_url, "listed_in": "literature found while checking"}


# Published analog sites poleward of 55 degrees that are in neither catalogue, found while doing the named checks.
OTHER_PUBLISHED_SITES = [
    _other("Flashline Mars Arctic Research Station (FMARS), Devon Island", 75.4313, -89.8234,
           "Mars: crewed habitat simulations on the rim of Haughton crater (Mars Society)",
           "https://en.wikipedia.org/wiki/Flashline_Mars_Arctic_Research_Station", "search result summary",
           "https://en.wikipedia.org/wiki/Flashline_Mars_Arctic_Research_Station"),
    _other("McGill Arctic Research Station, Axel Heiberg Island", 79.4333, -90.7667,
           "Mars: base for the cold-spring and permafrost work at Expedition Fiord",
           "https://en.wikipedia.org/wiki/McGill_Arctic_Research_Station", "catalogue chapter 4 names the station",
           "https://en.wikipedia.org/wiki/McGill_Arctic_Research_Station"),
    _other("Tunnunik impact structure, Victoria Island", 72.4667, -113.9333,
           "Moon and Mars: eroded 25 km impact structure in polar desert; a Canadian Space Agency funded expedition with "
           "astronaut field training was reported for about 2015",
           "https://spaceq.ca/canadas_arctic_as_a_moon_and_mars_analog_for_our_astronauts/", "search result summary",
           "https://en.wikipedia.org/wiki/Tunnunik_impact_structure"),
    _other("Deep Lake, Vestfold Hills", -68.56, 78.1958,
           "Mars: hypersaline lake that stays liquid to about -20 C; its salt-loving microbes are studied as a model for "
           "Martian cold brines",
           "https://en.wikipedia.org/wiki/Deep_Lake_(Vestfold_Hills,_Antarctica)", "search result summary; the papers were not opened",
           "https://en.wikipedia.org/wiki/Deep_Lake_(Vestfold_Hills,_Antarctica)"),
    _other("Schirmacher Oasis", -70.7583, 11.6444,
           "Mars: lakes, glaciofluvial landforms and polygons proposed as an analog for early Mars (conference abstract "
           "with fieldwork; the abstract itself calls the oasis seldom studied)",
           "https://meetingorganizer.copernicus.org/EGU26/EGU26-15988.html", "opened today",
           "https://en.wikipedia.org/wiki/Schirmacher_Oasis"),
]

# Seen while checking, but without a point we can stand behind.
SEEN_BUT_NOT_PLACED = [
    {"name": "Borup Fiord Pass, Ellesmere Island", "what": "sulfur and iron deposits on ice studied as an astrobiology analog",
     "source_url": "https://www.frontiersin.org/articles/10.3389/fspas.2022.825019/full", "evidence": "search result summary"},
    {"name": "North-east Siberian permafrost (Kolyma lowland)", "what": "described in a NASA Ames methods paper as perhaps the best "
     "Earth analog for Martian permafrost; no site coordinates given in what we read",
     "source_url": "https://visualize.jove.com/11540067-From-Siberia-to-Mars", "evidence": "search result summary"},
    {"name": "Star City, Russia (55.88 N)", "what": "named in the Wikipedia article's text as a training pool, not as an analog field site",
     "source_url": WIKI_URL, "evidence": "raw file on disk"},
    {"name": "Kangerlussuaq", "what": "already ours; confirmed as a Europlanet field facility with Mars-analog campaigns in 2021 and 2023",
     "source_url": "https://europlanet-society.org/?p=8745", "evidence": "search result summary"},
]


def _fac(name, kind, lat, lon, source_url, note=None):
    return {"name": name, "kind": kind, "lat": lat, "lon": lon, "source_url": source_url, "note": note}


W = "https://en.wikipedia.org/wiki/"
# Stations and airfields outside Antarctica. Coordinates are those on each linked Wikipedia page (read through
# the Wikipedia API on 14 November 2026). Antarctic stations come from the COMNAP file instead.
FACILITIES = [
    _fac("Khodovarikha weather station", "station", 68.941, 53.769, W + "Khodovarikha", "staffed weather station since 1933; not a research station"),
    _fac("Naryan-Mar Airport", "airfield", 67.64, 53.125, W + "Naryan-Mar_Airport"),
    _fac("Varandey Airport", "airfield", 68.8478, 58.1986, W + "Varandey_Airport", "serves the oil terminal"),
    _fac("Temp air base, Kotelny Island", "airfield", 75.7667, 137.58, W + "Temp_(air_base)", "military; reported rebuilt from 2013"),
    _fac("Kotelny Island base (at Temp)", "station", 75.7667, 137.58, "https://barentsobserver.com/en/node/26037",
         "research station and military base 1933 to 1993, military base revived; not open to visitors as far as we read"),
    _fac("Sachs Harbour Airport, Banks Island", "airfield", 71.9936, -125.2414, W + "Sachs_Harbour_(David_Nasogaluak_Jr._Saaryuaq)_Airport"),
    _fac("Ulukhaktok Airport, Victoria Island", "airfield", 70.7628, -117.8061, W + "Ulukhaktok/Holman_Airport"),
    _fac("Paulatuk Airport", "airfield", 69.3606, -124.0758, W + "Paulatuk_(Nora_Aliqatchialuk_Ruben)_Airport"),
    _fac("Cambridge Bay Airport", "airfield", 69.1081, -105.1372, W + "Cambridge_Bay_Airport"),
    _fac("Canadian High Arctic Research Station, Cambridge Bay", "station", 69.1139, -105.0528, W + "Canadian_High_Arctic_Research_Station",
         "the point is the hamlet of Cambridge Bay"),
    _fac("Gjoa Haven Airport", "airfield", 68.6356, -95.8503, W + "Gjoa_Haven_Airport"),
    _fac("Taloyoak Airport", "airfield", 69.5467, -93.5769, W + "Taloyoak_Airport"),
    _fac("Kugaaruk Airport", "airfield", 68.5358, -89.8053, W + "Kugaaruk_Airport"),
    _fac("Svalbard Airport, Longyear", "airfield", 78.2461, 15.4656, W + "Svalbard_Airport,_Longyear"),
    _fac("Ny-Alesund research town", "station", 78.925, 11.922, W + "Ny-%C3%85lesund", "year-round international research base; the point is the one in our own list"),
    _fac("Kinnvika, Murchisonfjorden", "station", 80.0031, 18.4852, W + "Murchisonfjorden",
         "station of the International Geophysical Year 1957-58, used again 2007-09, now empty; the point is the fjord's, the huts are a few km away"),
    _fac("Kapp Lee, Edgeoya", "station", 78.1149, 20.8282, W + "Kapp_Lee",
         "site of the Dutch station (wintering 1968-69, summer visits to 1988, expeditions 2015 and 2022); no standing staffed station"),
    _fac("Reykjavik (University of Iceland, Icelandic Meteorological Office)", "station", 64.1269, -21.9025, W + "Reykjav%C3%ADk",
         "the capital's research institutions; the point is the Reykjavik weather station used in our snow check (GHCN IC000004030)"),
    _fac("Keflavik International Airport", "airfield", 63.985, -22.6056, W + "Keflav%C3%ADk_International_Airport",
         "small airfields at Hella and Bakki are closer; their coordinates were not verified today"),
]


def _ev(claim, url, level):
    return {"claim": claim, "url": url, "level": level}


OPENED, SEARCH, ON_DISK = "opened today", "search result summary", "raw file on disk"

# The places that head the ranking. points are the coordinates the coordinator named (range ends for a range).
TOP_PLACES = [
    {"name": "Pechora Sea coast, Russia", "points": [(68.95, 54.45)],
     "analog_use_found": False,
     "polar_field_work": "A staffed weather station (Khodovarikha, since 1933) stands on the same coast. We found no research station and no space-analog work.",
     "evidence": [_ev("Khodovarikha: weather station opened 1933, still operating, 68.941 N 53.769 E", W + "Khodovarikha", SEARCH)],
     "not_checked": "Russian-language sources; whether the coast lies inside the Nenets nature reserve (one search did not confirm it); access rules."},
    {"name": "New Siberian Islands, Russia (Bunge Land and Kotelny)", "points": [(75.0, 141.0), (75.0, 143.0)],
     "analog_use_found": False,
     "polar_field_work": "Yes, polar science but no space-analog use found. Bunge Land is a 6,200 km2 bare sand plain between Kotelny and Faddeyevsky, "
                         "studied by Russian and German permafrost teams (Schirrmeister and others 2010) and shown by NASA Earth Observatory. "
                         "Kotelny had a research station and base from 1933 to 1993; the Temp airfield is now military.",
     "evidence": [_ev("Bunge Land: about 6,200 km2 of sand, mostly under 8 m above the sea, origin studied by Schirrmeister et al. 2010", W + "Bunge_Land", SEARCH),
                  _ev("NASA Earth Observatory image story on the sandy plains", "https://science.nasa.gov/earth/earth-observatory/sandy-plains-in-the-arctic-147359/", SEARCH),
                  _ev("Kotelny: research station and base 1933 to 1993, Temp airfield to be rebuilt by the Northern Fleet", "https://barentsobserver.com/en/node/26037", SEARCH)],
     "not_checked": "Whether the airfield or base operates now; permits (the area is a military zone). The article date was not shown."},
    {"name": "Victoria Island and Banks Island, Canada", "points": [(70.0, -115.0), (70.0, -125.0)],
     "analog_use_found": False,
     "polar_field_work": "No analog work found at these points. The nearest published analog is the Tunnunik impact structure further north on Victoria Island "
                         "(Canadian Space Agency funded expedition with astronaut training, about 2015). Nothing found for Banks Island.",
     "evidence": [_ev("Tunnunik: expedition led by Western University with astronaut field training", "https://spaceq.ca/canadas_arctic_as_a_moon_and_mars_analog_for_our_astronauts/", SEARCH),
                  _ev("Tunnunik impact structure, 72.47 N 113.93 W, about 25 km across", W + "Tunnunik_impact_structure", SEARCH)],
     "not_checked": "Aulavik National Park and other protected areas; community research licences (Northwest Territories and Nunavut both require one)."},
    {"name": "Mainland coast of Arctic Canada (Kitikmeot, Nunavut)", "points": [(68.3, -88.0), (68.3, -99.0)],
     "analog_use_found": False,
     "polar_field_work": "None found in one search: no research station and no space-analog work near Gjoa Haven, Taloyoak or Kugaaruk. "
                         "The nearest research station is the Canadian High Arctic Research Station at Cambridge Bay.",
     "evidence": [_ev("One search for analog or station work at Boothia, Gjoa Haven, Kugaaruk, Taloyoak returned only Devon and Ellesmere sites", "https://science.nasa.gov/?p=1151788", SEARCH)],
     "not_checked": "Nunavut Research Institute licence records; mining or geological survey camps."},
    {"name": "Nordaustlandet, Svalbard (Murchisonfjorden)", "points": [(80.15, 18.3)],
     "analog_use_found": True,
     "polar_field_work": "Yes, both. The ESA / Open University catalogue lists Murchison Fjord (79.88 N 18.49 E) as an AMASE Mars-analog site. "
                         "The Kinnvika station in the same fjord was built for the International Geophysical Year 1957-58 and used again in 2007-09; "
                         "it is empty now. The place is polar desert inside the Nordaust-Svalbard nature reserve. It is not a little-known place.",
     "evidence": [_ev("Catalogue chapter 26.6.3: Murchison Fjord, prior analogue usage AMASE", CATALOGUE_URL, ON_DISK),
                  _ev("Kinnvika: built 1957-58 by a Swedish-Finnish-Swiss expedition, revived for the Polar Year 2007-09, inside the nature reserve",
                      "https://cruise-handbook.npolar.no/en/northeast_reserve/nordaustlandet-history-and-cultural-remains.html", SEARCH)],
     "not_checked": "Which AMASE years worked there; current landing and research permit rules of the reserve."},
    {"name": "Edgeoya, Svalbard", "points": [(77.55, 22.75)],
     "analog_use_found": False,
     "polar_field_work": "Polar field work yes, space-analog none found. A Dutch team wintered at Kapp Lee in 1968-69, made summer visits to 1988, "
                         "and came back with the SEES expeditions of 2015 and 2022. No staffed station today.",
     "evidence": [_ev("Dutch station history and the 2015 return", "https://spitsbergen-svalbard.com/photos-panoramas-videos-and-webcams/spitsbergen-panoramas/dolerittneset-kapp-lee.html", SEARCH),
                  _ev("SEES expedition 13 to 22 July 2022, sampling at Kapp Lee", "https://www.rug.nl/research/arctisch-centrum/collaboration/dutchcollaboration/wbpi/.sees/scientist/research-plans/baseline-contaminant-assessment-on-the-remote-storfjorden-coasts-of-southeast-svalbard", SEARCH)],
     "not_checked": "Protected-area rules (the island lies in a nature reserve; not confirmed today)."},
    {"name": "Iceland, south coast (Landeyjar sands)", "points": [(63.75, -20.7)],
     "analog_use_found": False,
     "polar_field_work": "No analog work found for this sand plain itself, but it sits inside the best-studied analog country: the catalogue's "
                         "Eyjafjallajokull and Krysuvik sites are 55 to 70 km away, and NASA rover tests (SAND-E, 2019 and 2021) used sands near Langjokull. "
                         "The challenge text itself calls Iceland widely studied.",
     "evidence": [_ev("Catalogue chapter 12: Askja, Eyjafjallajokull, Krysuvik, Laki", CATALOGUE_URL, ON_DISK),
                  _ev("SAND-E rover tests at Lambahraun near Langjokull", "https://missioncontrolspace.com/stories/semi-autonomous-navigation-for-detrital-environments-sand-e/", SEARCH)],
     "not_checked": "Icelandic-language sources; the small airfields at Hella and Bakki (coordinates not verified)."},
    {"name": "Vestfold Hills, Antarctica", "points": [(-68.5, 78.2)],
     "analog_use_found": True,
     "polar_field_work": "Yes. Australia's year-round Davis station is at the edge of the hills, and the hypersaline Deep Lake there is studied as a model "
                         "for cold Martian brines. It is a well-studied place, not a little-known one.",
     "evidence": [_ev("Deep Lake: about 270 g/L salt, liquid to about -20 C, microbial community studied since the 1980s", W + "Deep_Lake_(Vestfold_Hills,_Antarctica)", SEARCH),
                  _ev("Davis station in the COMNAP facilities list", "https://www.comnap.aq/antarctic-facilities-information", ON_DISK)],
     "not_checked": "The Mars-analog wording comes from a search summary of a 2026 paper we did not open. Davis's ski landing area and sea-ice runway (no airfield entry in the COMNAP file)."},
    {"name": "Northern Prince Charles Mountains, Antarctica (Amery Oasis, Beaver Lake)", "points": [(-70.75, 68.0)],
     "analog_use_found": False,
     "polar_field_work": "Polar field work yes, space-analog none found. Russia's summer station Soyuz stood on Beaver Lake (opened 1982; closed since 2007 "
                         "by one account, 'temporarily closed' in the COMNAP list), and Australia set up a summer base at Beaver Lake in 1995.",
     "evidence": [_ev("Soyuz station: on Beaver Lake, opened December 1982, closed 2007", W + "Soyuz_Station", SEARCH),
                  _ev("Beaver Lake base established 1995 for northern Prince Charles Mountains work", "https://www.antarctica.gov.au/antarctic-operations/stations-and-field-locations/field-sites/", SEARCH)],
     "not_checked": "Whether either camp is usable now; aircraft landing sites (none in the COMNAP file here)."},
    {"name": "Southern Prince Charles Mountains, Antarctica (Mount Menzies area)", "points": [(-73.45, 61.75)],
     "analog_use_found": False,
     "polar_field_work": "None found beyond occasional geological expeditions; no station within several hundred km. Mount Menzies (73.5 S 61.83 E) is the nearest named peak.",
     "evidence": [_ev("Mount Menzies coordinates", W + "Mount_Menzies", OPENED)],
     "not_checked": "Expedition records of the Australian and Russian programmes."},
]


# data/reference/antarctic_sites.json decides which southern cells are called known: a cell within the pipeline's
# radius of a site whose existing_analog_use is filled in is "known". Two of its nulls have a source against them.
ANTARCTIC_SUGGESTIONS = [
    {"site": "Vestfold Hills", "field": "existing_analog_use", "now": None,
     "suggest": "Deep Lake (68.56 S 78.20 E) is studied as a model for cold Martian brines; Davis station (year-round) is 12 km away",
     "effect": "the Vestfold Hills cells would stop being called little known",
     "source_url": W + "Deep_Lake_(Vestfold_Hills,_Antarctica)", "evidence": SEARCH},
    {"site": "Schirmacher Oasis", "field": "existing_analog_use", "now": None,
     "suggest": "proposed as an Earth analog for glaciofluvial landforms on early Mars, with fieldwork (EGU26-15988, 2026); "
                "the abstract itself calls the oasis seldom studied",
     "effect": "cells near Schirmacher Oasis would stop being called little known",
     "source_url": "https://meetingorganizer.copernicus.org/EGU26/EGU26-15988.html", "evidence": OPENED},
    {"site": "Bunger Hills", "field": "existing_analog_use", "now": None,
     "suggest": "leave null: one search found no analog or astrobiology paper naming it",
     "effect": "none", "source_url": W + "Bunger_Hills", "evidence": SEARCH},
]


# ---------------------------------------------------------------- putting it together

def _load(path: Path):
    return json.loads(path.read_text()) if path.exists() else None


def _comnap_points(comnap: dict | None) -> list[dict] | None:
    if comnap is None:
        return None
    return [{"name": p["facility_name_english"], "lat": p["latitude_dd"], "lon": p["longitude_dd"], "type": p.get("type"),
             "seasonality": p.get("seasonality"), "status": p.get("status"), "from": COMNAP_CREDIT}
            for p in (f["properties"] for f in comnap["features"])]


def _slim(hit: dict | None, keys=("name", "km", "kind", "lat", "lon", "type", "seasonality", "status", "note", "source_url", "from")) -> dict | None:
    """The fields worth printing. A COMNAP row keeps its name, distance and status but not its coordinates."""
    if hit is None:
        return None
    if "from" in hit:
        keys = tuple(k for k in keys if k not in ("lat", "lon"))
    return {k: hit[k] for k in keys if k in hit and hit[k] is not None}


def _union_cells(points, cells, radius_km=RADIUS_KM) -> dict | None:
    if cells is None:
        return None
    close = [c for c in cells if any(km(lat, lon, c["lat"], c["lon"]) <= radius_km for lat, lon in points)]
    return {"cells": len(close), "flagged_little_known": sum(1 for c in close if c.get("little_known") is True)}


def top_place(place: dict, ours: list[dict], published_missing: list[dict], other: list[dict],
              comnap: list[dict] | None, cells: list[dict] | None) -> dict:
    points = [tuple(p) for p in place["points"]]
    south = points[0][0] < 0
    per_point = []
    for lat, lon in points:
        row = {"lat": lat, "lon": lon,
               "nearest_known_site_of_ours": _slim(nearest(lat, lon, ours), ("name", "km")),
               "nearest_published_site_missing_from_ours": _slim(nearest(lat, lon, published_missing + other), ("name", "km", "listed_in"))}
        if south:
            row["nearest_comnap_facility"] = _slim(nearest(lat, lon, comnap, FAR_KM)) if comnap is not None else None
            year_round = None if comnap is None else [c for c in comnap if c["seasonality"] == "Year-Round" and c["status"] == "Open"]
            row["nearest_year_round_comnap_station"] = _slim(nearest(lat, lon, year_round, FAR_KM)) if year_round is not None else None
            row["nearest_airfield"] = (_slim(nearest(lat, lon, [c for c in comnap if c["type"] == "Airfield Camp"], FAR_KM))
                                       if comnap is not None else None)
            row["nearest_airfield_note"] = (f"the COMNAP list (2019 copy) has no airfield camp within {FAR_KM:g} km; station skiways "
                                            "and sea-ice runways are not in it" if comnap is not None and row["nearest_airfield"] is None
                                            else None)
        else:
            row["nearest_station"] = _slim(nearest(lat, lon, [f for f in FACILITIES if f["kind"] == "station"], FAR_KM))
            row["nearest_airfield"] = _slim(nearest(lat, lon, [f for f in FACILITIES if f["kind"] == "airfield"], FAR_KM))
        per_point.append(row)
    out = {"name": place["name"], "analog_use_found": place["analog_use_found"],
           "hosts_analog_or_polar_field_work": place["polar_field_work"], "evidence": place["evidence"],
           "not_checked": place["not_checked"], "points": per_point,
           "cells_within_50_km": _union_cells(points, cells)}
    if south:                                  # the first point's answer, for a quick read
        out["nearest_comnap_facility"] = per_point[0]["nearest_comnap_facility"]
        out["nearest_year_round_comnap_station"] = per_point[0]["nearest_year_round_comnap_station"]
    return out


def requested_checks(ours: list[dict], antarctic: list[dict] | None) -> list[dict]:
    """The places the coordinator asked about by name: is each in our lists, and how far is our point from the published one."""
    def where(name_start, lat, lon):
        mine = _ours_named(ours, name_start)
        return None if mine is None else {"ours": mine["name"], "km_from_published_point": round(km(lat, lon, mine["lat"], mine["lon"]), 1)}

    def antarctic_row(name_start):
        row = None if antarctic is None else next((a for a in antarctic if a["name"].startswith(name_start)), None)
        return None if row is None else {"name": row["name"], "lat": row["lat"], "lon": row["lon"], "existing_analog_use": row.get("existing_analog_use")}

    return [
        {"asked": "Bunger Hills", "in_known_analogs": _ours_named(ours, "Bunger") is not None, "in_antarctic_sites": antarctic_row("Bunger"),
         "finding": "In neither catalogue. One search found no Mars-analog or astrobiology paper naming Bunger Hills, so we have no source for calling it a known analog; "
                    "another Space Apps team is pitching it this weekend. Our point (66.27 S 100.75 E) is 2 km from the Wikipedia point (66.283 S 100.783 E).",
         "evidence": [_ev("Bunger Hills coordinates", W + "Bunger_Hills", OPENED)]},
        {"asked": "Vestfold Hills", "in_known_analogs": _ours_named(ours, "Vestfold") is not None, "in_antarctic_sites": antarctic_row("Vestfold"),
         "finding": "In neither catalogue, but Deep Lake in the hills has an astrobiology literature (model for cold Martian brines). antarctic_sites.json says "
                    "existing_analog_use null: that should say so. Our point equals the Wikipedia point (68.55 S 78.25 E).",
         "evidence": [_ev("Deep Lake", W + "Deep_Lake_(Vestfold_Hills,_Antarctica)", SEARCH)]},
        {"asked": "Schirmacher Oasis", "in_known_analogs": _ours_named(ours, "Schirmacher") is not None, "in_antarctic_sites": antarctic_row("Schirmacher"),
         "finding": "In neither catalogue. A 2026 conference abstract with fieldwork proposes it as an early-Mars analog and calls it seldom studied. "
                    "antarctic_sites.json says existing_analog_use null: that should cite the abstract. Our point (70.76 S 11.65 E) matches Wikipedia (70.758 S 11.644 E).",
         "evidence": [_ev("EGU26-15988", "https://meetingorganizer.copernicus.org/EGU26/EGU26-15988.html", OPENED)]},
        {"asked": "Devon Island sites other than Haughton", "ours": where("Haughton", 75.3667, -89.6833),
         "finding": "The catalogue's three Haughton sub-sites and the FMARS habitat (75.431 N 89.823 W) all lie within 50 km of our Haughton entry, so cells there "
                    "are already called known. One catalogue sub-site is misprinted (see catalogue_misprints). The Truelove Lowland station (75.67 N 84.58 W) is "
                    "an ecology station, not an analog site.",
         "evidence": [_ev("FMARS", W + "Flashline_Mars_Arctic_Research_Station", SEARCH)]},
        {"asked": "Axel Heiberg Island (McGill Arctic Research Station)", "ours": where("Axel Heiberg", 79.409175, -90.732765),
         "finding": "Ours is right: it is within 1 km of the catalogue's Gypsum Hill point and about 2 km from the station (79.433 N 90.767 W). "
                    "Two catalogue sub-site coordinates are printed in a mixed format (see the notes on those rows).",
         "evidence": [_ev("Catalogue chapter 4", CATALOGUE_URL, ON_DISK)]},
        {"asked": "Svalbard sites (AMASE)", "ours": where("Svalbard (AMASE)", 78.0, 16.0),
         "finding": "Our general entry is a rounded regional point (see doubtful_in_our_list). Of the catalogue's four field sites we have Bockfjord only; "
                    "Ebbadalen and Murchison Fjord are missing, Adventtoppen is within 50 km of the regional point but not named.",
         "evidence": [_ev("Catalogue chapter 26", CATALOGUE_URL, ON_DISK)]},
        {"asked": "Kangerlussuaq", "ours": where("Kangerlussuaq", 67.012, -50.711),
         "finding": "Ours is right (the settlement and airport). It is in neither catalogue; it is a Europlanet field facility with Mars-analog campaigns "
                    "in 2021 and 2023, so listing it as known is justified.",
         "evidence": [_ev("Europlanet facility page", "https://europlanet-society.org/?p=8745", SEARCH)]},
        {"asked": "Iceland sites", "ours": where("Askja", 65.03, -16.75),
         "finding": "Askja and Eyjafjallajokull (as Fimmvorduhals, 8 km away) and CHILL-ICE match the published points. Krysuvik and the Laki flow field are missing. "
                    "'Iceland field sites (Europlanet/Matis)' is a mid-island placeholder (see doubtful_in_our_list); 'Iceland highlands' duplicates Askja.",
         "evidence": [_ev("Catalogue chapter 12", CATALOGUE_URL, ON_DISK)]},
        {"asked": "Arctic Russia", "ours": None,
         "finding": "Neither catalogue has a site in Arctic Russia. The catalogue's only Russian chapter is Kamchatka (51 to 61 N; the Klyuchevskaya group at 56 N "
                    "is missing from ours, our Koryaksky entry is at 53.3 N). The Wikipedia text names Star City only as a training pool. North-east Siberian "
                    "permafrost is called a Mars analog in the literature without a site we could place. So our top Russian places have no listed analog nearby.",
         "evidence": [_ev("Catalogue chapter 13", CATALOGUE_URL, ON_DISK)]},
    ]


def build(known_path: Path = KNOWN, wiki_path: Path = WIKI, comnap_path: Path = COMNAP, cells_path: Path = CELLS,
          antarctic_path: Path = ANTARCTIC, out_path: Path = OUT) -> dict:
    ours = json.loads(known_path.read_text())
    antarctic = _load(antarctic_path)
    scored = _load(cells_path)
    cells = None if scored is None else (scored["cells"] if isinstance(scored, dict) else scored)
    comnap = _comnap_points(_load(comnap_path))
    wiki_text = wiki_path.read_text(encoding="utf-8") if wiki_path.exists() else None
    wiki_rows = [{**row, "listed_in": WIKI_TABLE, "source_url": WIKI_URL}
                 for row in (parse_wikipedia_table(wiki_text) if wiki_text is not None else [])]

    published = CATALOGUE_SITES + wiki_rows
    missing, covered = compare(published, ours)
    other_missing, other_covered = compare(OTHER_PUBLISHED_SITES, ours)
    for row in missing + other_missing:
        row["cells_within_50_km"] = cells_near(row["lat"], row["lon"], cells)

    doubtful = offsets(published, ours, SAME_SITE)
    hand_flagged = {m["name"] for m in (_ours_named(ours, f["ours_starts_with"]) for f in HAND_FLAGS) if m is not None}
    for mine in ours:
        if mine["name"] not in hand_flagged and abs(mine["lat"]) >= MIN_ABS_LAT and (mine["lat"] * 2).is_integer() and (mine["lon"] * 2).is_integer() \
                and mine.get("coord_quality") == "source":
            doubtful.append({"ours": mine["name"], "our_lat": mine["lat"], "our_lon": mine["lon"],
                             "our_coord_quality": "source",
                             "why": "both coordinates are whole or half degrees although the entry is marked 'source': it reads as a regional point"})
    for flag in HAND_FLAGS:
        mine = _ours_named(ours, flag["ours_starts_with"])
        if mine is None:
            continue
        doubtful.append({"ours": mine["name"], "our_lat": mine["lat"], "our_lon": mine["lon"],
                         "our_coord_quality": mine.get("coord_quality"), "why": flag["why"], "suggest": flag["suggest"],
                         "km_to_catalogue_sites_in_the_same_region": {
                             s["name"]: round(km(mine["lat"], mine["lon"], s["lat"], s["lon"]), 1) for s in CATALOGUE_SITES
                             if km(mine["lat"], mine["lon"], s["lat"], s["lon"]) < 400 and not s["name"].endswith("(general point)")}})

    result = {
        "meta": {
            "written": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "script": "scripts/check_known_analogs.py",
            "our_list": {"file": "data/reference/known_analogs.json", "entries": len(ours),
                         "poleward_of_55": sum(1 for o in ours if abs(o["lat"]) >= MIN_ABS_LAT),
                         "entries_citing_wikipedia": sum(1 for o in ours if "wikipedia.org" in o.get("source_url", "")),
                         "entries_citing_the_wikipedia_table_page": sum(1 for o in ours if o.get("source_url", "").startswith(WIKI_URL)),
                         "descriptions_sharing_six_words_in_a_row_with_the_wikipedia_article":
                             None if wiki_text is None else shared_runs(ours, re.sub(r"[\[\]|']", " ", wiki_text)),
                         "licence": "names and coordinates are facts taken from the pages linked in each entry; the descriptions are our "
                                    "own words. Because many entries rest on Wikipedia (CC BY-SA 4.0; the count is above), the list is offered "
                                    "under CC BY-SA 4.0 with credit to Wikipedia contributors, not under the code's Apache 2.0. See data/SOURCES.md."},
            "compared_with": [
                {"name": CATALOGUE, "url": CATALOGUE_URL, "raw_file": "data/raw/analog_catalogues/The-Catalogue-of-Planetary-Analogues.pdf",
                 "chapters": 30, "sites_poleward_of_55_transcribed": len(CATALOGUE_SITES),
                 "note": "the copy is on a third-party host; the title page says it was written by the Open University under ESA contract 4000104716/11/NL/AF, final version 5 December 2012"},
                {"name": WIKI_TABLE, "url": WIKI_URL, "raw_file": "data/raw/analog_catalogues/wikipedia_Terrestrial_analogue_site.wikitext",
                 "rows": len(wiki_rows), "rows_with_a_point": sum(1 for r in wiki_rows if r["lat"] is not None),
                 "rows_poleward_of_55": sum(1 for r in wiki_rows if r["lat"] is not None and abs(r["lat"]) >= MIN_ABS_LAT)}],
            "rule": f"a published site poleward of {MIN_ABS_LAT:g} degrees is missing when no entry of ours lies within {RADIUS_KM:g} km "
                    f"(great circle, sphere of {EARTH_RADIUS_KM:g} km); an entry of ours is doubtful when it lies more than "
                    f"{OFFSET_TOLERANCE_KM:g} km from the published point of the same site, or stands for a region",
            "cells_scored_written": None if not isinstance(scored, dict) else scored.get("meta", {}).get("written"),
            "cells_scored_records": None if cells is None else len(cells),
            "comnap_facilities": None if comnap is None else len(comnap),
            "evidence_levels": {OPENED: "we read the page itself", SEARCH: "we read a search engine's summary of the page, not the page",
                                ON_DISK: "read from a raw file kept in data/raw"},
            "not_checked": ["sites in the two lists between 55 degrees north and 55 degrees south",
                            "the USGS analog-site layer and other catalogues",
                            "Russian, Norwegian, Icelandic and Danish language sources",
                            "permits and protected-area rules at every place"],
        },
        "missing_from_our_list": missing,
        "covered_within_50_km_but_under_another_name": covered,
        "also_published_elsewhere_and_missing": other_missing,
        "also_published_elsewhere_and_covered": other_covered,
        "seen_but_not_placed": SEEN_BUT_NOT_PLACED,
        "catalogue_misprints": CATALOGUE_MISPRINTS,
        "doubtful_in_our_list": doubtful,
        "requested_checks": requested_checks(ours, antarctic),
        "antarctic_sites_suggested_changes": ANTARCTIC_SUGGESTIONS,
        "top_places": [top_place(p, ours, missing, other_missing, comnap, cells) for p in TOP_PLACES],
    }
    side = out_path.with_name(out_path.name + ".tmp")
    side.write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(side, out_path)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    result = build(out_path=args.out)
    print(f"wrote {args.out}")
    print(f"  missing from our list (poleward of 55): {len(result['missing_from_our_list'])}")
    for row in result["missing_from_our_list"]:
        print(f"    {row['name']}: {row['lat']:.3f}, {row['lon']:.3f}; nearest of ours {row['nearest_of_ours']['name']} "
              f"at {row['nearest_of_ours']['km']} km; cells within 50 km {row['cells_within_50_km']}")
    print(f"  also published elsewhere and missing: {[r['name'] for r in result['also_published_elsewhere_and_missing']]}")
    print(f"  doubtful in our list: {[(d['ours'], d.get('km_apart')) for d in result['doubtful_in_our_list']]}")
    for place in result["top_places"]:
        first = place["points"][0]
        near = first.get("nearest_station") or first.get("nearest_comnap_facility")
        print(f"  {place['name']}: analog use found {place['analog_use_found']}; cells {place['cells_within_50_km']}; "
              f"nearest station {near and (near['name'], near['km'])}; airfield {first.get('nearest_airfield') and (first['nearest_airfield']['name'], first['nearest_airfield']['km'])}")


if __name__ == "__main__":
    main()

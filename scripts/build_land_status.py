# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Land status and permits for each area: data/derived/land_status_cells.json and data/derived/mars_land_status.json.

    uv run python scripts/build_land_status.py

Who owns or governs the ground at the centre of each area, whether a map puts that centre in a protected area,
and whom a researcher must ask. Two kinds of content, each labelled:
    "from a map"                  an open map with clear terms says something about the centre point
    "by territory, a rough guide" a statement about the whole territory, read on an official page

The territory comes from Natural Earth admin-0 and admin-1 boundaries (public domain), kept in
data/raw/land_status/naturalearth/. They are downloaded once with the project's User-Agent when missing.

The regional additions (data/raw/land_status/additions/<region>.json) add territory rules and open maps of
protected areas and of owners. Each map is a GeoJSON file in longitude and latitude, cut by its region's agent to
the polygons that matter. This script reads them from disk and makes no network request for them. A map covers only
its own region: outside its polygons it says nothing, so a centre that no polygon holds is not thereby private or
unprotected. Only numpy and the standard library.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from twinfinder import fetch  # noqa: E402

RAW = ROOT / "data" / "raw" / "land_status" / "naturalearth"
ADDITIONS = ROOT / "data" / "raw" / "land_status" / "additions"
DERIVED = ROOT / "data" / "derived"
SITE_DATA = ROOT / "site" / "data"
OUT = DERIVED / "land_status_cells.json"
OUT_MARS = DERIVED / "mars_land_status.json"
NE_BASE = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/"
NE_FILES = ["ne_10m_admin_0_countries.geojson", "ne_10m_admin_1_states_provinces.geojson"]
NEAREST_KM = 30.0          # a centre just off the mapped coast takes the nearest territory within this reach
READ_ON = "2026-11-15"

FROM_MAP = "from a map"
BY_TERRITORY = "by territory, a rough guide"
MIXED = "mixed or cannot tell at this scale"
UNKNOWN = "unknown"
# Classes that a map can set on its own. "mixed" sets the class only when the map's own owner field says it.
DEFINITE = {"no owner: Antarctic Treaty area", "public land in a protected area", "public land",
            "Indigenous-owned land", "private land"}

CLASSES = {
    "no owner: Antarctic Treaty area":
        "The centre lies south of 60 degrees South, in the Antarctic Treaty area. The Treaty freezes all claims to territorial sovereignty.",
    "public land in a protected area":
        "A map puts the centre inside a protected area. The map or an official page says that the land there is public.",
    "public land":
        "A map gives a public owner or manager at the centre, or the territory rule says that the land is public.",
    "Indigenous-owned land":
        "A map of Indigenous-owned land puts the centre inside such land.",
    "private land":
        "A map of owners puts the centre on private land.",
    "mixed or cannot tell at this scale":
        "The territory rule or the map names more than one kind of owner. No map that we checked decides between them at the centre.",
    "unknown":
        "We did not read an official page about who owns the land in this territory, and no map that we checked gives an owner. We make no statement.",
}

# The official pages read on the night of the first pass. Each statement below names the pages it rests on.
PAGES = {
    "ats_treaty": {"title": "The Antarctic Treaty", "publisher": "Secretariat of the Antarctic Treaty",
                   "url": "https://www.ats.aq/e/antarctictreaty.html"},
    "aad_approvals": {"title": "Environmental approval requirements", "publisher": "Australian Antarctic Division",
                      "url": "https://www.antarctica.gov.au/about-antarctica/environment/environmental-impact-assessment-approvals-and-permits/"},
    "aad_protected": {"title": "Protecting and managing special areas", "publisher": "Australian Antarctic Division",
                      "url": "https://www.antarctica.gov.au/about-antarctica/environment/protecting-and-managing-special-areas/"},
    "cirnac_nunavut": {"title": "Land and resource management overview (Nunavut)",
                       "publisher": "Crown-Indigenous Relations and Northern Affairs Canada",
                       "url": "https://www.rcaanc-cirnac.gc.ca/eng/1646153802021/1646251899137"},
    "nri_licence": {"title": "Research licensing applications", "publisher": "Nunavut Research Institute",
                    "url": "https://www.nri.nu.ca/research-licencing-applications"},
    "gnwt_licence": {"title": "Do I need a licence to do research?",
                     "publisher": "Government of the Northwest Territories, Environment and Climate Change",
                     "url": "https://www.gov.nt.ca/ecc/en/services/water-management-and-monitoring/do-i-need-licence-do-research"},
    "sysselmesteren_research": {"title": "Research and educational activity", "publisher": "Sysselmesteren på Svalbard (the Governor of Svalbard)",
                                "url": "https://www.sysselmesteren.no/en/research-and-educational-activity/"},
    "blm_alaska": {"title": "Alaska Land Transfer Program", "publisher": "U.S. Bureau of Land Management",
                   "url": "https://www.blm.gov/programs/lands-and-realty/regional-information/alaska/land-transfer"},
    "is_thjodlendur": {"title": "Þjóðlendur (national lands)", "publisher": "Stjórnarráð Íslands, Forsætisráðuneytið",
                       "url": "https://www.stjornarradid.is/verkefni/rekstur-og-eignir-rikisins/eignir-rikisins/thjodlendur/"},
}

# Pages we tried and could not read: no statement rests on them.
PAGES_NOT_READ = [
    {"url": "https://yukon.ca/en/scientists-explorers-licence", "why": "the server refused the request (HTTP 403)"},
    {"url": "https://www.regjeringen.no/en/topics/business-and-industry/state-ownership-of-land-in-svalbard/id2898480",
     "why": "the server refused the request (HTTP 403)"},
    {"url": "https://www.ats.aq/e/protectedareas.html", "why": "not found (the protected area list of the Secretariat needs a log-in)"},
]

# Territory rules of the first pass. owner: who owns the land in general (None = no official page read; no
# statement). ask: the authority to ask for a permit or a research licence. land: the class that the rule alone
# gives. The additions replace and extend these in merge_rules().
TERRITORIES = {
    "antarctica": {
        "name": "Antarctica (Antarctic Treaty area)",
        "owner": "No state owns Antarctica under the Antarctic Treaty. Seven states claim parts of it, and Article IV of the Treaty freezes all claims.",
        "ask": "Ask the national Antarctic authority of the country that organises your visit. Entry to an Antarctic Specially Protected Area must have a permit.",
        "ask_note": "In Australia, for example, all activities in the Antarctic region must have an environmental authorisation first.",
        "pages": ["ats_treaty", "aad_approvals", "aad_protected"], "land": "no owner: Antarctic Treaty area"},
    "nunavut": {
        "name": "Canada: Nunavut",
        "owner": "Land in Nunavut is Crown land, Commissioner's land or Inuit Owned Land.",
        "ask": "Research in Nunavut must have a Scientific Research Licence from the Nunavut Research Institute. On Inuit Owned Land, ask the Regional Inuit Association.",
        "pages": ["cirnac_nunavut", "nri_licence"], "land": MIXED},
    "northwest_territories": {
        "name": "Canada: Northwest Territories",
        "owner": None,
        "ask": "All research in the Northwest Territories must have a licence or a permit. The Aurora Research Institute licenses most research.",
        "pages": ["gnwt_licence"], "land": UNKNOWN},
    "svalbard": {
        "name": "Norway: Svalbard",
        "owner": None,
        "ask": "Register all research in the Research in Svalbard (RiS) portal. Most field activities must have permission from Sysselmesteren på Svalbard (the Governor).",
        "pages": ["sysselmesteren_research"], "land": UNKNOWN},
    "alaska": {
        "name": "United States: Alaska",
        "owner": "Alaska is a mix of federal land, State of Alaska land, Alaska Native Corporation land and other private land.",
        "ask": "Find the owner or the manager of the land first: a federal agency, the State of Alaska or an Alaska Native Corporation.",
        "pages": ["blm_alaska"], "land": MIXED},
    "iceland": {
        "name": "Iceland",
        "owner": "Iceland has private land and national lands (þjóðlendur). On national lands, the Icelandic state owns the land and the land rights that are not private.",
        "ask": "On national lands, use of land must have a permit from the municipality concerned. On other land, we did not read who gives permits.",
        "pages": ["is_thjodlendur"], "land": MIXED},
}
UNKNOWN_ASK = "We did not read an official page for this territory. Find the permit authority before any field work."
UNKNOWN_OWNER = "unknown: we did not read an official page about who owns the land."
# The first-pass owner sentence stays in front of the addition's sentences for these territories.
OWNER_KEEP_FIRST = {"alaska"}
# Our own reading of a rule, shown with it. Greenland: the official page says "joint ownership", not "public".
CLASS_NOTES = {
    "greenland": "The page says joint ownership, not public land. Our class 'public land' stands for this joint ownership.",
}

# Natural Earth admin units to territory keys and names. Anything not listed keeps its Natural Earth name.
ADMIN1 = {("CAN", "Nunavut"): "nunavut", ("CAN", "Northwest Territories"): "northwest_territories",
          ("CAN", "Yukon"): "yukon", ("CAN", "Québec"): "quebec", ("CAN", "Newfoundland and Labrador"): "newfoundland_labrador",
          ("CAN", "Manitoba"): "manitoba", ("CAN", "Saskatchewan"): "saskatchewan", ("CAN", "Alberta"): "alberta",
          ("CAN", "British Columbia"): "british_columbia", ("CAN", "Ontario"): "ontario",
          ("USA", "Alaska"): "alaska", ("NOR", "Svalbard"): "svalbard", ("NOR", "Finnmark"): "finnmark"}
OTHER_NAMES = {"yukon": "Canada: Yukon", "quebec": "Canada: Québec (Nunavik)", "newfoundland_labrador": "Canada: Newfoundland and Labrador",
               "manitoba": "Canada: Manitoba", "saskatchewan": "Canada: Saskatchewan", "alberta": "Canada: Alberta",
               "british_columbia": "Canada: British Columbia", "ontario": "Canada: Ontario", "greenland": "Greenland",
               "jan_mayen": "Norway: Jan Mayen", "norway": "Norway (mainland)", "finnmark": "Norway: Finnmark",
               "sweden": "Sweden", "finland": "Finland", "russia": "Russia", "iceland": "Iceland"}
ADMIN0 = {"ATA": "antarctica", "GRL": "greenland", "ISL": "iceland", "SWE": "sweden", "FIN": "finland", "RUS": "russia",
          "NOR": "norway"}
CANADA = {"nunavut", "northwest_territories", "yukon", "quebec", "newfoundland_labrador", "manitoba", "saskatchewan",
          "alberta", "british_columbia", "ontario"}

# The Natural Earth admin-1 unit "Nationalparken" of Greenland, the national park in the north-east (first pass).
PROTECTED_FROM_ADMIN1 = {("GRL", "Nationalparken"): {"type": "national park (Natural Earth admin-1 unit)",
                                                      "entry": "A permit is always necessary in the National Park in North and East Greenland.",
                                                      "source": "Natural Earth admin-1"}}
NE_PARK_MAP = {"id": "ne_nationalparken", "short": "Natural Earth admin-1 unit 'Nationalparken' (Greenland)",
               "what": "protected areas", "covers": ["greenland"], "mars_complete": True}


def P(props, key):
    """A property, with the empty words of the source files read as no value."""
    if key is None:
        return None
    value = props.get(key)
    if value is None or (isinstance(value, str) and value.strip() in ("", "None", "null")):
        return None
    return value


# ---- per-map readers. Each takes the feature's properties and the map's entry in its additions file. ----
ALASKA_ENTRY = {   # by the BLM surface management agency; each sentence rests on a page of the Alaska rule
    "NPS": "Research on National Park Service land must have a Scientific Research and Collecting Permit.",
    "FWS": "Research on a national wildlife refuge must have a Special Use Permit when the Service does not take part in it.",
    "BLM": "The BLM issues leases and permits for use of public lands. Contact the local BLM office.",
    "ST": "Low-impact research on State land can use the Research Permit of the Division of Mining, Land and Water.",
    "NTVPIC": "To leave a 17(b) easement and go onto Native land without permission from the owner is trespass.",
    "PVT": "The BLM map shows private land. Ask the owner before you go onto the land.",
}
BLM_CAVEAT = "The BLM map is not a legal document or a land survey. Ask the surface manager agency for current facts."
PADUS_ACCESS = {"OA": "PAD-US gives the public access as open (OA).",
                "RA": "PAD-US gives the public access as restricted (RA): a special permit or a registration is necessary.",
                "XA": "PAD-US gives the public access as closed (XA).",
                "UK": "PAD-US gives the public access as unknown (UK)."}
CANADA_OWNER_ENTRY = {
    "Inuit Owned Land": "The Regional Inuit Association of the region manages the surface rights of Inuit Owned Land.",
    "Yukon First Nations Settlement Land": "On Settlement Land, the Yukon First Nation holds rights equivalent to fee simple, or fee simple title.",
    "Sahtu Land": "Designated Sahtu organizations hold title in fee simple to the Sahtu settlement lands.",
}

MAP_SETUP = {
    # file name: id, short name for the page, territories that the map covers, whether its cut also holds every polygon
    # at a Mars square, its rank (lower first when two maps of a kind hold a centre), and readers that differ from the
    # additions file's own fields.
    "ats_aspa_2024.geojson": dict(id="ats_aspa", short="Antarctic Treaty Secretariat, ASPA map (2024)",
                                  covers=["antarctica"], mars_complete=False, rank=0),
    "ats_asma_2024.geojson": dict(id="ats_asma", short="Antarctic Treaty Secretariat, ASMA map (2024)",
                                  covers=["antarctica"], mars_complete=False, rank=1),
    "cpcad_north.geojson": dict(id="cpcad", short="Canadian Protected and Conserved Areas Database",
                                covers=sorted(CANADA), mars_complete=False, rank=2,
                                owner=lambda p, m: P(p, "OWNER_E")),
    "aboriginal_lands_north.geojson": dict(
        id="nrcan_aboriginal", short="Aboriginal Lands of Canada Legislative Boundaries",
        covers=sorted(CANADA), mars_complete=False, rank=1,
        owner=lambda p, m: f"{P(p, 'distributionTypeEng')}: {P(p, 'adminAreaNameEng')}",
        entry=lambda p, m: CANADA_OWNER_ENTRY.get(P(p, "distributionTypeEng"))),
    "iceland_protected_areas.geojson": dict(
        id="is_fridlyst", short="Friðlýst svæði á Íslandi", covers=["iceland"], mars_complete=True, rank=3,
        entry=lambda p, m: m["entry"] + (" We did not read the permit page of this national park."
                                         if P(p, "odesignate") == "Þjóðgarður" else "")),
    "jan_mayen_naturvernomrade.geojson": dict(
        id="no_janmayen", short="Naturvernområder, Jan Mayen (Miljødirektoratet)", covers=["jan_mayen"],
        mars_complete=True, rank=4, name=lambda p, m: P(p, "offisieltNavn") or P(p, "navn"),
        dedupe=lambda p: P(p, "naturvernId")),
    "norway_protected_areas_miljodirektoratet.geojson": dict(
        id="no_naturvern", short="Naturvernområder (Miljødirektoratet)", covers=["svalbard", "jan_mayen", "finnmark", "norway"],
        mars_complete=True, rank=5, name=lambda p, m: P(p, "offisieltNavn") or P(p, "navn"),
        type=lambda p, m: P(p, "verneformAggregert") or P(p, "verneform"),
        dedupe=lambda p: P(p, "naturvernId"),
        entry=lambda p, m: " ".join(s for s in (
            ("Sysselmesteren på Svalbard manages all protected areas in Svalbard. "
             "Traffic is banned in 16 bird reserves from 15 May to 15 August.") if P(p, "territory_rule") == "Norway: Svalbard" else None,
            f"The management authority (forvaltningsmyndighet) is {P(p, 'forvaltningsmyndighet')}."
            if P(p, "forvaltningsmyndighet") and P(p, "territory_rule") != "Norway: Svalbard" else None)
            if s) or None),
    "sweden_protected_areas_naturvardsverket.geojson": dict(
        id="se_skyddade", short="Skyddade områden (Naturvårdsverket)", covers=["sweden"], mars_complete=False, rank=6,
        entry=lambda p, m: f"The manager (förvaltare) of this national park is {P(p, 'FORVALTARE')}." if P(p, "FORVALTARE") else None),
    "padus41_fee_managers_alaska.geojson": dict(
        id="padus", short="Protected Areas Database of the United States (PAD-US) 4.1, Fee Managers",
        covers=["alaska"], mars_complete=False, rank=8,
        type=lambda p, m: f"PAD-US GAP status {P(p, 'GAP_Sts')}",
        # GAP status 3 and 4 give a public manager, not a protected area: the hit then names the manager.
        role=lambda p, m: "protected" if str(P(p, "GAP_Sts")) in ("1", "2") else "owner",
        owner=lambda p, m: f"{P(p, 'Unit_Nm')} (manager {P(p, 'Mang_Name')}, from PAD-US)" if str(P(p, "GAP_Sts")) not in ("1", "2") else None,
        entry=lambda p, m: PADUS_ACCESS.get(P(p, "Pub_Access"))),
    "blm_ak_administered_lands_sma_alaska.geojson": dict(
        id="blm_sma", short="BLM AK Administered Lands (surface management agency)", covers=["alaska"],
        mars_complete=False, rank=0,
        name=lambda p, m: P(p, "ADMIN_UNIT_NAME") or P(p, "AGENCY_NAME"),
        owner=lambda p, m: (f"{P(p, 'AGENCY_NAME')}: {P(p, 'ADMIN_UNIT_NAME')}" if P(p, "ADMIN_UNIT_NAME") else P(p, "AGENCY_NAME")),
        entry=lambda p, m: ALASKA_ENTRY.get(P(p, "ADMIN_AGENCY_CODE"), BLM_CAVEAT)
        if not (P(p, "ADMIN_AGENCY_CODE") == "ST" and P(p, "ADMIN_UNIT_TYPE") == "State Park")
        else "We did not read an official page about research in Alaska state parks."),
}


def ensure_raw() -> dict:
    """The Natural Earth files: on disk, or downloaded once. Returns notes of where and when."""
    RAW.mkdir(parents=True, exist_ok=True)
    log_path = RAW / "downloads.json"
    log = json.loads(log_path.read_text()) if log_path.exists() else {}
    for name in NE_FILES:
        path = RAW / name
        if not path.exists():
            fetch.fetch(NE_BASE + name, RAW)
        if name not in log:
            log[name] = {"url": NE_BASE + name, "bytes": path.stat().st_size,
                         "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                         "fetched_utc": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                         "how": "curl or urllib with the header User-Agent: twinfinder/0.1"}
    log_path.write_text(json.dumps(log, indent=1))
    return log


def polygons(geometry):
    if geometry is None:
        return []
    if geometry["type"] == "Polygon":
        return [geometry["coordinates"]]
    if geometry["type"] == "MultiPolygon":
        return geometry["coordinates"]
    return []


def inside(lon, lat, rings):
    """Even-odd test of points against one polygon (outer ring plus holes)."""
    hit = np.zeros(lon.shape, bool)
    for ring in rings:
        r = np.asarray(ring, float)[:, :2]
        keep = r[:-1, 1] != r[1:, 1]
        a, b = r[:-1, 0][keep], r[:-1, 1][keep]
        c, d = r[1:, 0][keep], r[1:, 1][keep]
        if a.size == 0:
            continue
        step = max(1, 4_000_000 // a.size)           # points per block, so a block holds a few million pairs
        for s in range(0, lon.size, step):
            px, py = lon[s:s + step, None], lat[s:s + step, None]
            crosses = (b > py) != (d > py)
            xs = a + (py - b) * (c - a) / (d - b)
            hit[s:s + step] ^= (np.count_nonzero(crosses & (px < xs), axis=1) % 2).astype(bool)
    return hit


class Layer:
    def __init__(self, features, key):
        self.items = []
        for f in features:
            for poly in polygons(f["geometry"]):
                outer = np.asarray(poly[0], float)
                box = (outer[:, 0].min(), outer[:, 1].min(), outer[:, 0].max(), outer[:, 1].max())
                self.items.append((key(f["properties"]), poly, box, outer))

    def locate(self, lon, lat):
        out = np.full(lon.shape, None, object)
        for value, poly, (x0, y0, x1, y1), _outer in self.items:
            sel = np.where((lon >= x0) & (lon <= x1) & (lat >= y0) & (lat <= y1) & (out == None))[0]  # noqa: E711
            if sel.size == 0:
                continue
            hit = inside(lon[sel], lat[sel], poly)
            for i in sel[hit]:
                out[i] = value
        return out

    def nearest(self, lon, lat, reach_km):
        """The value of the nearest boundary vertex within reach, for points no polygon holds."""
        best, best_km = None, reach_km
        pad = reach_km / 111.0
        for value, _poly, (x0, y0, x1, y1), outer in self.items:
            wide = pad / max(np.cos(np.radians(lat)), 0.05)
            if not (x0 - wide <= lon <= x1 + wide and y0 - pad <= lat <= y1 + pad):
                continue
            dx = (outer[:, 0] - lon) * np.cos(np.radians(lat)) * 111.32
            dy = (outer[:, 1] - lat) * 110.57
            km = float(np.sqrt(dx * dx + dy * dy).min())
            if km < best_km:
                best, best_km = value, km
        return best, (best_km if best is not None else None)


class MapLayer:
    """One map of the additions. hits() gives, for each point, every feature whose polygon holds it.
    Bounding boxes come first: the box of the whole map, then the box of each polygon part."""

    def __init__(self, spec, setup, features):
        self.spec, self.setup = spec, setup
        self.id, self.short = setup["id"], setup["short"]
        self.what = spec["what"]
        self.features = features
        self.parts = []
        x0 = y0 = np.inf
        x1 = y1 = -np.inf
        for k, f in enumerate(features):
            for poly in polygons(f["geometry"]):
                outer = np.asarray(poly[0], float)
                box = (outer[:, 0].min(), outer[:, 1].min(), outer[:, 0].max(), outer[:, 1].max())
                self.parts.append((k, poly, box))
                x0, y0, x1, y1 = min(x0, box[0]), min(y0, box[1]), max(x1, box[2]), max(y1, box[3])
        self.box = (x0, y0, x1, y1)

    def hits(self, lon, lat):
        out = [set() for _ in range(lon.size)]
        x0, y0, x1, y1 = self.box
        near = np.where((lon >= x0) & (lon <= x1) & (lat >= y0) & (lat <= y1))[0]
        if near.size == 0:
            return out
        lo, la = lon[near], lat[near]
        for k, poly, (a0, b0, a1, b1) in self.parts:
            sel = np.where((lo >= a0) & (lo <= a1) & (la >= b0) & (la <= b1))[0]
            if sel.size == 0:
                continue
            got = inside(lo[sel], la[sel], poly)
            for j in sel[got]:
                out[near[j]].add(k)
        return out

    def read(self, k):
        """What feature k says: name, type, class, whether the class comes from an owner field, role, owner, entry."""
        p, m, s = self.features[k]["properties"], self.spec, self.setup
        name = s["name"](p, m) if "name" in s else P(p, m.get("name_field"))
        kind = s["type"](p, m) if "type" in s else P(p, m.get("type_field"))
        rule = m.get("class")
        if isinstance(rule, dict):
            cls = rule["values"].get(str(P(p, rule["field"])))
            from_field = rule["field"] != "territory_rule"
        else:
            cls, from_field = rule, False
        role = s["role"](p, m) if "role" in s else ("owner" if m["what"] == "owner type" else "protected")
        owner = s["owner"](p, m) if "owner" in s else None
        entry = s["entry"](p, m) if "entry" in s else m.get("entry")
        dedupe = s["dedupe"](p) if "dedupe" in s else None
        return {"map": self.id, "rank": s["rank"], "name": name, "type": kind, "class": cls, "from_field": from_field,
                "role": role, "owner": owner, "entry": entry, "dedupe": dedupe or name}


def territory_of(a0, a1):
    """Territory key from the admin-0 code and the admin-1 (country code, name) pair."""
    if a1 is not None:
        code, name = a1
        if (code, name) in ADMIN1:
            return ADMIN1[(code, name)]
        if code == "NOR" and name and "Jan Mayen" in name:
            return "jan_mayen"
        if code in ADMIN0:
            return ADMIN0[code]
    if a0 is not None:
        return ADMIN0.get(a0[0], "other:" + a0[1])
    return None


def assign(ids, lats, lons, a0_layer, a1_layer):
    lat, lon = np.asarray(lats, float), np.asarray(lons, float)
    a1 = a1_layer.locate(lon, lat)
    a0 = a0_layer.locate(lon, lat)
    out = {}
    for i, pid in enumerate(ids):
        how = "centre inside the boundary"
        if lat[i] < -60:
            key = "antarctica"
            how = "centre south of 60 degrees South"
        else:
            key = territory_of(a0[i], a1[i])
            if key is None:
                near1, km = a1_layer.nearest(lon[i], lat[i], NEAREST_KM)
                if near1 is not None:
                    key = territory_of(None, near1)
                    how = f"centre off the mapped coast; nearest territory, approximately {round(km)} km"
                else:
                    near0, km = a0_layer.nearest(lon[i], lat[i], NEAREST_KM)
                    if near0 is not None:
                        key = territory_of(near0, None)
                        how = f"centre off the mapped coast; nearest territory, approximately {round(km)} km"
        if key == "norway" and lon[i] < 0:          # Natural Earth keeps Jan Mayen inside Norway
            key = "jan_mayen"
        hit = None
        if a1[i] is not None and tuple(a1[i]) in PROTECTED_FROM_ADMIN1:
            spec = PROTECTED_FROM_ADMIN1[tuple(a1[i])]
            hit = {"map": NE_PARK_MAP["id"], "rank": 9, "name": a1[i][1], "type": spec["type"], "class": None,
                   "from_field": False, "role": "protected", "owner": None, "entry": spec["entry"], "dedupe": a1[i][1]}
        out[pid] = (key, how, hit)
    return out


def territory_name(key):
    if key is None:
        return "no territory within reach"
    if key in TERRITORIES:
        return TERRITORIES[key]["name"]
    if key.startswith("other:"):
        return key[6:]
    return OTHER_NAMES.get(key, key)


# ---- the additions ----

def name_to_key():
    names = {rule["name"]: key for key, rule in TERRITORIES.items()}
    names.update({v: k for k, v in OTHER_NAMES.items()})
    names["Antarctica"] = "antarctica"
    return names


def page_record(page):
    out = {"title": page.get("title"), "url": page.get("url"), "read_on": page.get("read_on", READ_ON)}
    if page.get("publisher"):
        out["publisher"] = page["publisher"]
    if page.get("what_it_says"):
        out["what_it_says"] = page["what_it_says"]
    return out


def read_additions():
    """Every additions file, checked. Returns (rules by territory key, map layers, notes, problems)."""
    keys = name_to_key()
    rules, layers, notes, problems = {}, [], {}, []
    for path in sorted(ADDITIONS.glob("*.json")):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            problems.append(f"{path.name}: does not load ({error})")
            continue
        region = doc.get("region") or path.stem
        notes[region] = {"rejected": doc.get("rejected") or [], "not_done": doc.get("not_done") or []}
        for rule in doc.get("territory_rules") or []:
            key = keys.get(rule.get("territory"))
            if key is None:
                problems.append(f"{region}: territory rule '{rule.get('territory')}' matches no territory key; left out")
                continue
            pages = rule.get("pages") or []
            states = rule.get("ownership") or rule.get("class_by_territory")
            if states and not pages:
                problems.append(f"{region}: rule for {rule['territory']} states an owner or a class with no page; left out")
                continue
            if rule.get("class_by_territory") not in (None, *CLASSES):
                problems.append(f"{region}: rule for {rule['territory']} has the class '{rule['class_by_territory']}', which is not one of ours; left out")
                continue
            rules[key] = dict(rule, region=region)
        for spec in doc.get("maps") or []:
            file = spec.get("file") or ""
            setup = MAP_SETUP.get(Path(file).name)
            if setup is None:
                problems.append(f"{region}: map {file} has no reader in this script; left out")
                continue
            if not spec.get("licence") or not spec.get("credit"):
                problems.append(f"{region}: map {file} gives no licence or no credit; left out")
                continue
            try:
                features = json.loads((ROOT / file).read_text(encoding="utf-8"))["features"]
            except (OSError, ValueError, KeyError) as error:
                problems.append(f"{region}: map {file} does not load ({error}); left out")
                continue
            layer = MapLayer(spec, setup, features)
            x0, y0, x1, y1 = layer.box
            if not (-180 <= x0 <= x1 <= 180 and -90 <= y0 <= y1 <= 90):
                problems.append(f"{region}: map {file} has coordinates outside longitude and latitude; left out")
                continue
            layer.region = region
            layers.append(layer)
    return rules, layers, notes, problems


def merge_rules(added):
    """The additions replace 'unknown' rules of the first pass and extend the others. Every page is kept."""
    for key, rule in TERRITORIES.items():
        rule["pages"] = [page_record(dict(PAGES[p], read_on=READ_ON)) if isinstance(p, str) else p for p in rule["pages"]]
    for key, add in added.items():
        old = TERRITORIES.get(key)
        pages = [page_record(p) for p in add.get("pages") or []]
        if old is None:
            TERRITORIES[key] = {"name": territory_name(key), "owner": add.get("ownership"), "ask": add.get("ask"),
                                "pages": pages, "land": add.get("class_by_territory") or UNKNOWN,
                                "from_additions": add["region"]}
            continue
        owner = add.get("ownership")
        if owner and key in OWNER_KEEP_FIRST and old.get("owner"):
            owner = old["owner"] + " " + owner
        old["owner"] = owner or old.get("owner")
        old["ask"] = add.get("ask") or old.get("ask")
        old["land"] = add.get("class_by_territory") or old["land"]
        have = {p["url"]: p for p in old["pages"]}
        for p in pages:
            if p["url"] in have:
                have[p["url"]].setdefault("what_it_says", p.get("what_it_says"))
            else:
                old["pages"].append(p)
        old["from_additions"] = add["region"]
    for key, note in CLASS_NOTES.items():
        if key in TERRITORIES:
            TERRITORIES[key]["class_note"] = note


# ---- one record for each place ----

def tested_maps(key, layers, mars):
    """The maps whose region holds this territory. For a Mars square, only maps whose cut kept every polygon there."""
    out = []
    for layer in layers:
        if key in layer.setup["covers"] and (not mars or layer.setup["mars_complete"]):
            out.append(layer.id)
    if key in NE_PARK_MAP["covers"]:
        out.append(NE_PARK_MAP["id"])
    return out


def decide(hits):
    """The hit that sets the class: an owner map with a firm class, then a protected-areas map with a firm class,
    then a map whose own owner field says mixed."""
    owner = sorted((h for h in hits if h["role"] == "owner"), key=lambda h: h["rank"])
    prot = sorted((h for h in hits if h["role"] == "protected"), key=lambda h: h["rank"])
    for group, test in ((owner, lambda h: h["class"] in DEFINITE), (prot, lambda h: h["class"] in DEFINITE),
                        (owner, lambda h: h["class"] == MIXED and h["from_field"]),
                        (prot, lambda h: h["class"] == MIXED and h["from_field"])):
        for h in group:
            if test(h):
                return h
    return None


def record(key, how, hits, tested, sources):
    rule = TERRITORIES.get(key)
    land = rule["land"] if rule else UNKNOWN
    decided, by_map = BY_TERRITORY, None
    chosen = decide(hits)
    prot = sorted((h for h in hits if h["role"] == "protected"), key=lambda h: h["rank"])
    owners = sorted((h for h in hits if h["role"] == "owner"), key=lambda h: h["rank"])
    if chosen is not None:
        land, decided, by_map = chosen["class"], FROM_MAP, chosen["map"]
        # An owner map that cannot tell the owner here, against a protected-areas map with a public owner: say mixed.
        if chosen["role"] == "protected" and any(h["class"] not in DEFINITE for h in owners):
            land = MIXED
    elif prot and land == "public land":
        land, decided, by_map = "public land in a protected area", FROM_MAP, prot[0]["map"]
    areas, seen = [], set()
    for h in prot:
        if h["name"] and h["dedupe"] not in seen:
            seen.add(h["dedupe"])
            areas.append({"name": h["name"], "type": h["type"], "source": sources.get(h["map"], h["map"])})
    owner = next(({"text": h["owner"], "source": sources.get(h["map"], h["map"])} for h in owners + prot if h["owner"]), None)
    entries = []
    for h in owners + prot:
        if h["entry"] and h["entry"] not in entries:
            entries.append(h["entry"])
    holding = sorted({h["map"] for h in hits})
    tested = sorted(set(tested) | set(holding))
    protected_maps = {l for l, w in MAP_WHAT.items() if w == "protected areas"}
    return {
        "territory": key, "territory_name": territory_name(key), "territory_how": how,
        "class": land, "decided": decided, "decided_by_map": by_map,
        "protected_area": areas[0] if areas else None,
        "protected_areas": areas,
        "owner_from_map": owner,
        "protected_checked": any(m in protected_maps for m in tested),
        "entry": " ".join(entries) or None,
        "maps_tested": tested,
        "maps_holding": holding,
        "ask_key": key if (rule and rule.get("ask")) else "unknown",
    }


MAP_WHAT = {NE_PARK_MAP["id"]: "protected areas"}


def build_part(ids, lats, lons, a0, a1, layers, mars):
    lat, lon = np.asarray(lats, float), np.asarray(lons, float)
    base = assign(ids, lats, lons, a0, a1)
    per_map = [(layer, layer.hits(lon, lat)) for layer in layers]
    sources = {layer.id: layer.short for layer in layers}
    sources[NE_PARK_MAP["id"]] = NE_PARK_MAP["short"]
    out = {}
    for i, pid in enumerate(ids):
        key, how, ne_hit = base[pid]
        hits = [ne_hit] if ne_hit else []
        for layer, found in per_map:
            hits.extend(layer.read(k) for k in sorted(found[i]))
        out[pid] = record(key, how, hits, tested_maps(key, layers, mars), sources)
    return out


def meta_block(counts_moon, counts_mars, log, n_moon, n_mars, layers, notes, problems):
    territory_rules = {}
    for key, rule in TERRITORIES.items():
        territory_rules[key] = {"name": rule["name"],
                                "owner": rule["owner"] or UNKNOWN_OWNER,
                                "class_note": rule.get("class_note"),
                                "ask": rule["ask"] or UNKNOWN_ASK, "ask_note": rule.get("ask_note"),
                                "class_by_rule": rule["land"],
                                "pages": rule["pages"]}
    ask = {key: rule["ask"] for key, rule in TERRITORIES.items() if rule.get("ask")}
    ask["unknown"] = UNKNOWN_ASK
    owner_words = {key: " ".join(s for s in ((rule["owner"] or UNKNOWN_OWNER), rule.get("class_note")) if s)
                   for key, rule in TERRITORIES.items()}
    owner_words["unknown"] = UNKNOWN_OWNER
    maps = [{"id": l.id, "short": l.short, "name": l.spec["name"], "what": l.what, "region": l.region,
             "covers_territories": l.setup["covers"], "covers_mars_squares": l.setup["mars_complete"],
             "file": l.spec["file"], "features": len(l.features), "polygon_parts": len(l.parts),
             "provider": l.spec.get("provider"), "source_url": l.spec.get("source_url"), "file_url": l.spec.get("file_url"),
             "fetched": l.spec.get("fetched"), "licence": l.spec.get("licence"), "credit": l.spec.get("credit"),
             "class_rule": l.spec.get("class")} for l in layers]
    maps.append({"id": NE_PARK_MAP["id"], "short": NE_PARK_MAP["short"], "what": "protected areas",
                 "covers_territories": NE_PARK_MAP["covers"], "covers_mars_squares": True,
                 "licence": "public domain (Natural Earth terms of use)", "credit": "Made with Natural Earth."})
    all_pages = {}
    for rule in TERRITORIES.values():
        for p in rule["pages"]:
            all_pages.setdefault(p["url"], p)
    return {
        "what": "Land status and permits: who owns or governs the ground at the centre of each area, and whom to ask.",
        "what_it_is": ("A class for the centre of each area, with the territory and the authority to ask for a permit. "
                       "Some classes come from open maps of protected areas and of owners. The others come from a statement about the whole territory."),
        "what_it_is_not": ("This is not legal advice. We test the centre of each area only, and an area of approximately 11 km can be partly in another class. "
                           "A territory rule is a rough guide and not a land survey. A map covers only its own region."),
        "honest_limit": ("No open map of private against public land exists for the whole world. Where we cannot tell, the class is 'unknown' or 'mixed or cannot tell at this scale'. "
                         "A centre that no polygon of a map holds is not thereby private or unprotected."),
        "made": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "made_by": "scripts/build_land_status.py",
        "how_to_rerun": "uv run python scripts/build_land_status.py",
        "decided_words": {FROM_MAP: "An open map with clear terms says something about the centre point.",
                          BY_TERRITORY: "A statement about the whole territory, read on an official page. It is not a survey of the area."},
        "classes": CLASSES,
        "territory_rules": territory_rules,
        "ask": ask,
        "owner_words": owner_words,
        "territory_method": ("The territory is the Natural Earth admin-1 unit (or admin-0 country) that holds the centre. "
                             f"A centre off the mapped coast takes the nearest unit within {round(NEAREST_KM)} km. "
                             "Every centre south of 60 degrees South is in the Antarctic Treaty area."),
        "map_rule": ("We test the centre point against every map. An owner map with a firm class sets the class first. "
                     "Then a protected-areas map with a firm class sets it. A map whose class is 'unknown', or 'mixed' with no owner field, gives only the name and the entry. "
                     "Without a map, the territory rule sets the class. maps_tested names the maps whose region holds the centre."),
        "protected_area_rule": ("We test the centre point only. A protected area gives its name and type. Where an owner map also holds the centre, "
                                "the owner map sets the class, and the record keeps both."),
        "maps": maps,
        "sources": [
            {"name": "Natural Earth 1:10m Cultural Vectors, Admin 0 - Countries and Admin 1 - States, Provinces",
             "licence": "public domain (Natural Earth terms of use)", "credit": "Made with Natural Earth.",
             "url": "https://www.naturalearthdata.com/", "files": log},
            *[{"name": l.spec["name"], "licence": l.spec.get("licence"), "credit": l.spec.get("credit"),
               "url": l.spec.get("source_url")} for l in layers],
            *[dict(p, licence="official page, read for facts only; no text copied beyond short facts")
              for p in all_pages.values()],
        ],
        "pages_not_read": PAGES_NOT_READ,
        "additions": {"read": sorted(notes), "left_out": problems,
                      "rejected_by_region": {r: n["rejected"] for r, n in notes.items()},
                      "not_done_by_region": {r: n["not_done"] for r, n in notes.items()}},
        "not_checked": [
            "Owners in Svalbard, Jan Mayen, mainland Norway outside Finnmark, Sweden outside national parks, Finland and the Northwest Territories: no official page read, so the class is 'unknown' there.",
            "Russia has no map of protected areas or of owners here, and no page on permits for foreign researchers was read.",
            "Greenland has no open map of protected areas other than the National Park unit of Natural Earth.",
            "The World Database on Protected and Conserved Areas: not used. Its terms do not let an openly licensed page carry it.",
            "The Mars squares: most maps were cut to the Moon-part areas, so for a Mars square only a hit counts.",
        ],
        "counts": {"areas": n_moon, "by_class": counts_moon["class"], "by_territory": counts_moon["territory"],
                   "by_decided": counts_moon["decided"], "with_protected_area": counts_moon["protected"],
                   "by_class_and_decided": counts_moon["class_decided"], "by_map_holding": counts_moon["maps"],
                   "by_territory_class": counts_moon["territory_class"],
                   "mars_squares": n_mars, "mars_by_class": counts_mars["class"], "mars_by_territory": counts_mars["territory"],
                   "mars_by_decided": counts_mars["decided"], "mars_by_map_holding": counts_mars["maps"]},
        "unknown_is": "null",
    }


def counts_of(cells):
    tc = {}
    for c in cells.values():
        row = tc.setdefault(c["territory_name"], {"areas": 0, "by_class": Counter(), "from_a_map": 0})
        row["areas"] += 1
        row["by_class"][c["class"]] += 1
        row["from_a_map"] += c["decided"] == FROM_MAP
    for row in tc.values():
        row["by_class"] = dict(row["by_class"].most_common())
    return {"class": dict(Counter(c["class"] for c in cells.values()).most_common()),
            "territory": dict(Counter(c["territory_name"] for c in cells.values()).most_common()),
            "decided": dict(Counter(c["decided"] for c in cells.values()).most_common()),
            "class_decided": dict(Counter(f"{c['class']} | {c['decided']}" for c in cells.values()).most_common()),
            "maps": dict(Counter(m for c in cells.values() for m in c["maps_holding"]).most_common()),
            "territory_class": dict(sorted(tc.items(), key=lambda kv: -kv[1]["areas"])),
            "protected": sum(1 for c in cells.values() if c["protected_area"])}


def write_json(path: Path, value) -> None:
    side = path.with_name(path.name + ".part")
    side.write_text(json.dumps(value, ensure_ascii=False, indent=1, allow_nan=False))
    os.replace(side, path)


def main() -> None:
    log = ensure_raw()
    added, layers, notes, problems = read_additions()
    merge_rules(added)
    for layer in layers:
        MAP_WHAT[layer.id] = layer.what
    a0f = json.loads((RAW / NE_FILES[0]).read_text())["features"]
    a1f = json.loads((RAW / NE_FILES[1]).read_text())["features"]
    a0 = Layer(a0f, lambda p: (p.get("ADM0_A3"), p.get("NAME")))
    a1 = Layer(a1f, lambda p: (p.get("adm0_a3"), p.get("name")))

    cells_doc = json.loads((SITE_DATA / "cells.json").read_text())
    ids = cells_doc["ids"]
    lats = [float(pid.split("_")[0]) for pid in ids]
    lons = [float(pid.split("_")[1]) for pid in ids]
    moon = build_part(ids, lats, lons, a0, a1, layers, mars=False)

    mars_doc = json.loads((DERIVED / "mars_cells.json").read_text())
    mcells = mars_doc["cells"]
    mids = list(mcells)
    mars = build_part(mids, [mcells[p]["lat"] for p in mids], [mcells[p]["lon"] for p in mids], a0, a1, layers, mars=True)

    cm, cmars = counts_of(moon), counts_of(mars)
    meta = meta_block(cm, cmars, log, len(moon), len(mars), layers, notes, problems)
    write_json(OUT, {"meta": meta, "cells": moon})
    mars_meta = dict(meta, what="Land status and permits for the Mars squares on Earth. A map counts for a square only where its cut covers the square.")
    write_json(OUT_MARS, {"meta": mars_meta, "cells": mars})
    print(f"maps read: {len(layers)}; rules added: {len(added)}; left out: {problems or 'nothing'}")
    print(f"wrote {OUT.relative_to(ROOT)}: {len(moon)} areas")
    for k in ("class", "decided", "class_decided", "maps", "protected"):
        print(" ", k, cm[k])
    print(f"wrote {OUT_MARS.relative_to(ROOT)}: {len(mars)} squares")
    print("  class", cmars["class"])
    print("  decided", cmars["decided"], "maps", cmars["maps"])


if __name__ == "__main__":
    sys.exit(main())

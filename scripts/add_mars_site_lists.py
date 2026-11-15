# This file was written with AI assistance (Claude, Anthropic) for the Earth Twin Finder project.
"""Add the Mars sites of two lists to data/derived/mars_sites_base.json, and give each site its lists.

    uv run python scripts/add_mars_site_lists.py

List A: the 2021 shortlist for human landings, Table 1 of Golombek et al. 2021 (LPSC abstract 2420,
data/raw/mars_sites/golombek2021_lpsc_2420.pdf). PM-1 is the present site "phlegra-montes"; the other
six sites are added with the position that Table 1 gives.

List B: the exploration zones of NASA's First Landing Site/Exploration Zone Workshop (2015), from
data/reference/mars_exploration_zones_2015.json. Each zone with "use": true is added with the position
that its abstract states, unless it lies at the same place (less than 50 km) as a present site; that
site then gets the list "2015 exploration zone" and the abstract number. Of the zones with "use": false,
only 1051 is added, with the centre of its circle on NASA's map of the proposed zones.

A new site is added only if its Mars Climate Database table is in data/raw/mars_climate/mcd/.
The twelve earlier records keep their values; they get only the fields "lists" and, where it applies,
"exploration_zone_abstracts" and a source line for each abstract that their sources did not hold.
The script starts again from the twelve earlier records each time, so a second run gives the same file.
"""
from __future__ import annotations

import datetime
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "data" / "derived" / "mars_sites_base.json"
ZONES = ROOT / "data" / "reference" / "mars_exploration_zones_2015.json"
MCD = ROOT / "data" / "raw" / "mars_climate" / "mcd"
GOLOMBEK_FILE = "data/raw/mars_sites/golombek2021_lpsc_2420.pdf"
GOLOMBEK_URL = "https://www.hou.usra.edu/meetings/lpsc2021/pdf/2420.pdf"
ZONE_FOLDER = "data/raw/mars_sites/ezworkshop2015/"
MAP_FILE = ZONE_FOLDER + "nasa_exploration_zone_map_v10.pdf"
MAP_URL = "https://www3.nasa.gov/sites/default/files/atoms/files/exploration-zone-map-v10.pdf"
WORKSHOP = "First Landing Site/Exploration Zone Workshop for Human Missions to the Surface of Mars"

EARLIER = ["jezero", "gale", "phoenix", "arcadia-planitia", "deuteronilus-mensae", "viking-1", "viking-2",
           "pathfinder", "spirit", "opportunity", "insight", "phlegra-montes"]
NASA_LANDED = {"jezero", "gale", "phoenix", "viking-1", "viking-2", "pathfinder", "spirit", "opportunity", "insight"}

L_NASA, L_2021, L_2015 = "NASA landing site", "2021 shortlist for human landings", "2015 exploration zone"
K_VISITED, K_STUDIED, K_ZONE = ("visited by a NASA mission", "studied for a human landing",
                                "proposed as an exploration zone in 2015")
POS_FROM_MAP = "read from NASA's map of the proposed zones"

# Zones at the same place as a present site (less than 50 km; for 1040 the same named target).
# 1008 and 1019: the list file was made before the first pass added Spirit and Viking 1, so its
# "same_as" field does not name them; the distances are 6 km and 19 km.
SAME_PLACE = {"ez-1011a-erebus-montes": "arcadia-planitia", "ez-1020-gale-crater-msl-ellipse": "gale",
              "ez-1022-gale-crater-aeolis-palus": "gale", "ez-1040-gale-crater-msl-ground-truth": "gale",
              "ez-1033-deuteronilus-mensae-dichotomy": "deuteronilus-mensae",
              "ez-1034-jezero-crater-watershed": "jezero", "ez-1008-gusev-crater": "spirit",
              "ez-1019-chryse-viking-1": "viking-1"}
FROM_MAP = {"ez-1051-hypanis-delta"}
LEFT_OUT = {
    "ez-1030-southwest-meridiani-planum": "The abstract states no position in words. The list file says that the circle on NASA's map "
                                          "(0.04 N, 359.88 E) is 5 to 6 degrees east of the craters that the abstract names, thus not a "
                                          "usable position.",
    "ez-1049-holden-crater": "The abstract states no position in words, and the zone is not on NASA's map of the proposed zones.",
}

# Table 1 of Golombek et al. 2021: label, lat (deg N), lon (deg E), elevation (km, MOLA geoid), group.
LIST_A = [
    ("arcadia-ap-1", "AP-1", "39.8", "202.1", "-3.9", "prime", "Arcadia Planitia",
     "AP-1 is one of four prime sites in a 2021 study of Starship landing sites. "
     "It looked the safest site, with a moderate score for ice.",
     "safest site; moderate combined SWIM score for ice; on the sinuous unit"),
    ("arcadia-ap-9", "AP-9", "40.02", "203.35", "-3.9", "prime", "Arcadia Planitia",
     "AP-9 is one of four prime sites in a 2021 study of Starship landing sites. "
     "Radar shows the thickest ice of the Arcadia sites on the sinuous unit, but the ground looks slightly rocky and rough.",
     "thickest ice from radar returns; highest combined SWIM score for ice; slightly rocky and rough; on the sinuous unit"),
    ("erebus-em-16", "EM-16", "39.89", "192.03", "-3.9", "prime", "Erebus Montes",
     "EM-16 is one of four prime sites in a 2021 study of Starship landing sites. "
     "A debris apron lies next to it, and radar shows the strongest return from shallow ice.",
     "lobate debris apron; strongest radar return for shallow ice; highest combined SWIM score"),
    ("arcadia-ap-8", "AP-8", "40.75", "201.3", "-3.9", "secondary", "Arcadia Planitia",
     "AP-8 is one of three secondary sites in a 2021 study of Starship landing sites. "
     "Next to the sinuous unit, it looked the safest site, with the highest scores for ice.",
     "adjacent to the sinuous unit; appears the safest; highest neutron and combined SWIM scores for ice"),
    ("erebus-em-15", "EM-15", "39.75", "195.62", "-3.9", "secondary", "Erebus Montes",
     "EM-15 is one of three secondary sites in a 2021 study of Starship landing sites. "
     "It lies near a debris apron, with well-developed polygons and smooth ground.",
     "prominent but less extensive lobate debris apron; well developed polygons; appears smooth"),
    ("phlegra-pm-7", "PM-7", "36.43", "162.16", "-2.3", "secondary", "Phlegra Montes",
     "PM-7 is one of three secondary sites in a 2021 study of Starship landing sites. "
     "It lies next to valley fill from glacial flow and looked the safest Phlegra site.",
     "adjacent to lineated valley fill; appeared the safest of the Phlegra sites"),
]

# The "why" of each zone is the list file's sentence, with the changes that the writing rules of the page
# (handoff/ste-rules.md) ask for: "can" for "may" and "could", "thus" for "so", "give" for "supply",
# no word ending in -ing used as a verb, no "chosen", and two short sentences where one was long.
WHY_STE = {
    "ez-1002-phlegra-dorsa": "Ground ice fills the top tens of metres here, thus crews can mine water. Low dust and few rocks suit heavy landers.",
    "ez-1005-southern-nectaris-fossae": "River valleys, a double crater with possible ice, an old volcano and faults lie close together. Clays can give water, and mafic rock can give metals.",
    "ez-1006-valles-marineris-mouth": "Floods carried rock from the southern highlands and chaos terrain to these plains, thus crews can sample many types of rock in one place.",
    "ez-1007-east-melas-chasma": "This deep, low canyon floor holds seasonal dark streaks (RSL) and thick sulfate beds for water. It also has old layered rock and a possible lake bed.",
    "ez-1009-mawrth-vallis": "Thick beds of ancient clay can keep signs of past life, and the clays can give water, iron, aluminium and silicon.",
    "ez-1010-nili-fossae": "Orbiters see ice, sulfates and clays near the planned base for water, with deep troughs and Hargraves crater for geology.",
    "ez-1011b-acheron-fossae": "The flat, low plains hold shallow ground ice for water, next to old faulted highland blocks, lava flows and rock glaciers.",
    "ez-1012-hebrus-valles": "An outflow channel with pits and possible caves can give shelter to crews, and buried ice in nearby plains can give water.",
    "ez-1015-newton-crater": "This large, low highland crater has gullies from past water, ground ice and old magnetised crust that can hold traces of early life.",
    "ez-1016-zephyria-planum-hills": "The author thinks that these cone-shaped hills hold ice that deep groundwater pushed up, a possible source of water, heat, metals and modern life.",
    "ez-1017-cerberus": "Young lava flows, older knobby ground, fresh faults and possible source rock of shergottite meteorites lie together, with signs of ground ice.",
    "ez-1018-amazonis-planitia-ice": "New impact craters show clean ice only 0.15 m below the surface, and the site has no hazards in a landing ellipse of 25 km.",
    "ez-1021-noachis-terra-chlorides": "Salt deposits in an old lake basin can keep traces of life, and buried ice in a nearby crater can give water.",
    "ez-1023-south-valles-marineris": "Seasonal dark streaks (RSL), salts, clays and rampart craters lie near smooth ground with little dust, with sand for construction.",
    "ez-1025-mclaughlin-crater": "This deep crater held a lake that groundwater fed. Its layered clays and carbonates can record deep life and can give water.",
    "ez-1026-south-of-firsoff-crater": "Sulfate layers, possible spring mounds and salt-flat beds record water across a long span of time, with sulfates and basalt as resources.",
    "ez-1027-ismenius-cavus": "An old lake basin with deltas and clay beds lies next to ice-rich glacial deposits, thus it gives both science and water.",
    "ez-1028-hale-crater": "Seasonal dark streaks (RSL) on the central peak can hold brine that crews can move through pipes for water. Gullies and old channels add science.",
    "ez-1029-copernicus-crater": "This huge crater in ancient crust has gullies and olivine dunes. Its name honours an important astronomer.",
    "ez-1032-huygens-crater": "This large old impact basin brought deep crust to the surface. It has clays and carbonates from past water, and volcanic plains that give ages.",
    "ez-1035-mesopotamia-east-hellas": "Ice-rich debris aprons give water. Valley networks, a young crater and two volcanic units give biology and ages for the history of Mars.",
    "ez-1036-western-coprates-chasma": "Seasonal dark streaks (RSL) can carry brines with modern life and water, and nearby fans and craters can keep old organics.",
    "ez-1037-hellas-rim": "Debris aprons hold more than 400 km3 of mostly water ice, near ancient Hellas rock, an old lake basin and valley networks.",
    "ez-1038-eastern-hellas-rim": "Ice in buried glaciers gives water, and very old rock from the Hellas impact and Reull Vallis channel deposits give science.",
    "ez-1041-columbus-crater": "A former crater lake that groundwater fed left many minerals that water made, which record past climate and can give water.",
    "ez-1042-southwest-sinus-meridiani": "Crews can test if a huge river fan laid down the Meridiani rocks, with Miyamoto crater, hematite and the route of Opportunity nearby.",
    "ez-1043-apollinaris-sulci": "Soft ridges that the wind cut give shelter, ice-rich ground near the surface gives water, and rocks of many ages lie near.",
    "ez-1044-deuteronilus-mensae-debris-apron": "A debris apron next to the base holds almost pure ice hundreds of metres thick, beside rocks from three major ages.",
    "ez-1045a-ausonia-cavus": "A possible old lake below a volcano has clays, lava flows and possible lava tubes, with ice-rich debris aprons for water.",
    "ez-1045b-kasei-valles": "Huge flood channels cut through old highland rock. Gravel bars, fine sediment and possible buried ice give science and resources.",
    "ez-1046-gusev-apollinaris-sulci": "The zone spans Gusev and Apollinaris Sulci, with hot-spring silica, carbonates, lavas and lake beds, and also the Spirit rover to inspect.",
    "ez-1048-aram-chaos": "Groundwater stayed here for a long time and left hematite and sulfates. The sulfates can give water, and the hematite can give iron.",
    "ez-1050-noctis-landing": "A canyon floor between Tharsis and Valles Marineris gives long rock records, hydrated and iron-sulfur minerals, and a deep drill target.",
    "ez-1051-hypanis-delta": "River deltas and lake beds can keep signs of past life, and nearby sand and clays can give water. "
                             "The position is read from NASA's map of the proposed zones, because the abstract gives no position in words.",
    "ez-1052-hadriacus-palus": "Pits show more than 800 m of volcanic, river, wind and impact layers in an exhumed basin that can hold shallow ice.",
    "ez-1053-protonilus-mensae": "Ice-rich debris aprons and valley fills give water, and outflow channels, a crater lake and old highland rock give science.",
    "ez-1054-eastern-valles-marineris-outlet": "Canyon walls show approximately 3 km of old layers, flood deposits and chaos terrain, with hydrated minerals for water.",
    "ez-1056-tempe-terra": "Ice-rich debris aprons give water, and grabens, three volcanic units and old highland rock give science and ages.",
    "ez-1057-southern-meridiani-endeavour": "Hard, flat plains near Endeavour crater give old clay-altered rock, sulfate salts and buried ice for water, and hematite for iron.",
}

A, B = 3396.19, 3376.20   # IAU 2000 ellipsoid of Mars, km


def planetographic_shift(lat: float) -> float | None:
    """How much smaller the planetocentric latitude is, if the stated latitude were planetographic."""
    if abs(lat) >= 89.9:
        return None
    centric = math.degrees(math.atan((B / A) ** 2 * math.tan(math.radians(lat))))
    return round(abs(lat - centric), 2)


def authors_short(authors: str) -> str:
    authors = authors.split(" (")[0]
    if " and " in authors and "co-author" in authors:
        return authors.split(" and ")[0].split()[-1] + " and others"
    suffixes = {"Jr.", "Jr", "II", "III", "IV"}
    names = []
    for a in authors.split(","):
        parts = [x for x in a.strip().split() if x not in suffixes]
        if parts:
            names.append(parts[-1])
    if len(names) == 1:
        return names[0]
    if len(names) <= 3:
        return ", ".join(names[:-1]) + " and " + names[-1]
    return names[0] + " and others"


def zone_source(z: dict) -> dict:
    url = z["abstract_url"].split(" (")[0]
    return {"what": f"{authors_short(z['authors'])} 2015, abstract {z['abstract']}, {WORKSHOP}: {z['name']}; "
                    f"position as written: {z['position_as_written']}",
            "url": url}


def has_mcd(site_id: str) -> bool:
    path = MCD / f"{site_id}_2d.txt"
    return path.exists() and "Surface pressure" in path.read_text(errors="replace")


def main() -> None:
    doc = json.loads(BASE.read_text(encoding="utf-8"))
    meta = doc["meta"]
    by_id = {s["id"]: s for s in doc["sites"]}
    missing = [i for i in EARLIER if i not in by_id]
    if missing:
        raise SystemExit(f"add_mars_site_lists: earlier sites missing from the base file: {missing}")
    sites = [by_id[i] for i in EARLIER]
    for s in sites:   # remove what an earlier run of this script added, so that a second run gives the same file
        s.pop("lists", None)
        s.pop("exploration_zone_abstracts", None)
        s["sources"] = [src for src in s["sources"] if "; position as written: " not in src["what"]]
    zones_doc = json.loads(ZONES.read_text(encoding="utf-8"))
    zones = sorted(zones_doc["zones"], key=lambda z: (z["abstract"], z["id"]))
    zone_by_id = {z["id"]: z for z in zones}
    coords = {k: v for k, v in meta["coordinates"].items() if k in EARLIER}

    # Lists of the earlier sites.
    zone_abstracts: dict[str, list[int]] = {}
    for zid, sid in SAME_PLACE.items():
        zone_abstracts.setdefault(sid, []).append(zone_by_id[zid]["abstract"])
    for s in sites:
        lists = []
        if s["id"] in NASA_LANDED:
            lists.append(L_NASA)
        if s["id"] == "phlegra-montes":
            lists.append(L_2021)
        if s["id"] in zone_abstracts:
            lists.append(L_2015)
            s["exploration_zone_abstracts"] = sorted(set(zone_abstracts[s["id"]]))
            urls = {src["url"] for src in s["sources"]}
            for zid, sid in SAME_PLACE.items():
                if sid == s["id"]:
                    src = zone_source(zone_by_id[zid])
                    if src["url"] not in urls:
                        s["sources"].append(src)
                        urls.add(src["url"])
        s["lists"] = lists

    added, not_added = [], []
    # List A.
    for sid, label, lat, lon, elev, group, region, why, words in LIST_A:
        if not has_mcd(sid):
            not_added.append({"id": sid, "why": "The Mars Climate Database table did not arrive."})
            continue
        sites.append({
            "id": sid, "name": f"{region} (site {label} of a 2021 Starship landing site study)",
            "lat": float(lat), "lon_east": float(lon), "kind": K_STUDIED, "why": why,
            "position_kind": "landing site, stated in Table 1",
            "lists": [L_2021],
            "sources": [{"what": f"Golombek et al. 2021, SpaceX Starship landing sites on Mars, 52nd Lunar and Planetary Science "
                                 f"Conference, abstract 2420 (JPL, SpaceX and university authors), Table 1: {label} at {lat} N, "
                                 f"{lon} E, {elev} km (MOLA geoid), a {group} site; {words}",
                         "url": GOLOMBEK_URL}],
        })
        coords[sid] = {"file": GOLOMBEK_FILE, "lat_as_written": lat, "lon_as_written": lon,
                       "source_convention": "Table 1 heads the columns °N and °E; the abstract does not name the latitude system",
                       "if_it_were_planetographic_deg": planetographic_shift(float(lat)),
                       "note": f"site {label} in Table 1 ({group} site), a landing point for Starship, elevation {elev} km "
                               "with respect to the MOLA geoid"}
        added.append(sid)

    # List B.
    for z in zones:
        zid = z["id"]
        if zid in SAME_PLACE or zid in LEFT_OUT:
            continue
        if not z["use"] and zid not in FROM_MAP:
            continue
        if not has_mcd(zid):
            not_added.append({"id": zid, "why": "The Mars Climate Database table did not arrive."})
            continue
        if zid in FROM_MAP:
            m = z["official_check"]["nasa_map_v10"]
            lat, lon = m["lat"], m["lon_east_360"]
            pos_kind = POS_FROM_MAP
            coords[zid] = {"file": MAP_FILE, "position_as_written": f"circle '{m['label']}' on the map; its centre is at "
                                                                     f"{lat} N, {lon} E",
                           "lat_as_written": str(lat), "lon_as_written": str(lon),
                           "source_convention": "the map's own graticule (Mercator, east longitude); circle centres taken from the "
                                                "vector paths, good to approximately 0.05 degree (list file, meta.official_sources_compared)",
                           "if_it_were_planetographic_deg": planetographic_shift(lat),
                           "list_file": "data/reference/mars_exploration_zones_2015.json", "zone": zid,
                           "note": "The abstract states no position in words. " + z["use_reason"]}
            sources = [zone_source(z), {"what": "NASA Mars Program Office, Potential Exploration Zones for Human Missions to the "
                                                f"Surface of Mars (map, version 10): circle '{m['label']}' at {lat} N, {lon} E",
                                        "url": MAP_URL}]
        else:
            lat, lon = z["lat"], z["lon_east_360"]
            pos_kind = z["position_kind"]
            coords[zid] = {"file": ZONE_FOLDER + z["raw_file"], "position_as_written": z["position_as_written"],
                           "lat_as_written": None, "lon_as_written": None,
                           "source_convention": z["convention"],
                           "if_it_were_planetographic_deg": planetographic_shift(lat),
                           "list_file": "data/reference/mars_exploration_zones_2015.json", "zone": zid,
                           "note": "lat and lon_east are the list file's reading of these words (degrees-minutes-seconds turned "
                                   "into decimal degrees; west longitude turned into east = 360 - west)"
                                   + (f". {z['note']}" if z.get("note") else "")}
            sources = [zone_source(z)]
        sites.append({"id": zid, "name": z["name"], "lat": lat, "lon_east": lon, "kind": K_ZONE,
                      "why": WHY_STE[zid], "position_kind": pos_kind, "lists": [L_2015],
                      "exploration_zone_abstracts": [z["abstract"]], "sources": sources})
        added.append(zid)

    doc["sites"] = sites
    meta["coordinates"] = coords
    meta["kinds"] = [K_VISITED, K_STUDIED, K_ZONE]
    meta["lists"] = {
        L_NASA: "A place where a NASA lander or rover landed and worked.",
        L_2021: "A site of Table 1 of Golombek et al. 2021 (LPSC abstract 2420), a study of landing sites for SpaceX Starship "
                "by JPL, SpaceX and university authors. It is a study, not a NASA decision.",
        L_2015: "An exploration zone proposed in an abstract of NASA's " + WORKSHOP + " (Lunar and Planetary Institute, Houston, "
                "27-30 October 2015). A proposal is not a NASA decision.",
    }
    meta["left_out"] = [x for x in meta.get("left_out", [])
                        if "the other six Starship study sites" not in x.get("what", "")
                        and not x.get("what", "").startswith("exploration zone")]
    for zid, why in LEFT_OUT.items():
        meta["left_out"].append({"what": f"exploration zone {zone_by_id[zid]['abstract']} ({zone_by_id[zid]['name']})", "why": why})
    for zid, sid in SAME_PLACE.items():
        z = zone_by_id[zid]
        meta["left_out"].append({"what": f"exploration zone {z['abstract']} ({z['name']}) as a site of its own",
                                 "why": f"It lies at the same place as the site '{sid}', which got the list '{L_2015}' and the "
                                        f"abstract number {z['abstract']}."})
    for x in not_added:
        meta["left_out"].append({"what": x["id"], "why": x["why"]})
    inputs = meta.get("inputs", [])
    for z in zones:
        p = ZONE_FOLDER + z["raw_file"]
        if (z["id"] in added or z["id"] in SAME_PLACE) and p not in inputs:
            inputs.append(p)
    for p in (MAP_FILE, "data/reference/mars_exploration_zones_2015.json"):
        if p not in inputs:
            inputs.append(p)
    meta["inputs"] = inputs
    stamp = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    meta["updated_second_pass"] = (
        f"{stamp}: {len(added)} sites added by scripts/add_mars_site_lists.py (six of the 2021 shortlist, "
        f"{len(added) - sum(1 for a in added if not a.startswith('ez-'))} exploration zones of 2015). Each position is copied "
        "from one saved source. Every site has the field 'lists'. The twelve earlier records keep their values. "
        "Climate tables: data/raw/mars_climate/mcd/_downloads_2026-11-15_second_pass.tsv.")
    meta["status"] = (meta["status"].rstrip() + " The second pass adds the other six sites of the 2021 shortlist and the "
                      "exploration zones proposed at the 2015 workshop. A proposal or a study is not a NASA decision."
                      ) if "second pass" not in meta["status"] else meta["status"]
    BASE.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"add_mars_site_lists: {len(sites)} sites ({len(added)} added); not added: {len(not_added)}")
    for x in not_added:
        print("  not added:", x["id"], x["why"])


if __name__ == "__main__":
    main()

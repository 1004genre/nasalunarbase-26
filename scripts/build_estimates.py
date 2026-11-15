# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Rough estimates by our own rules for the factors that have no open Earth data.

Writes data/derived/estimates_cells.json (the Moon part: the areas of data/derived/grazing_cells.json) and
data/derived/mars_estimates.json (the Mars part: the squares of data/derived/mars_cells.json).

Seven estimates, each a word plus the figures that produced it, from layers the project already holds:
rockiness, how fast the ground heats and cools, mineral family, water in the top soil (with ground ice),
depth to frozen ground, sand and dust on the move, and whether ilmenite-bearing rock is possible.
All rules are in twinfinder/estimates.py (RULES) and are copied, in plain words, into both metas.
"A rough estimate by our own rule. It is not a measurement."

    uv run python scripts/build_estimates.py            # build (no network, under a minute)
    uv run python scripts/build_estimates.py fetch      # download any missing source page, then stop

The only downloads are the pages opened for the depth-to-frozen-ground rule (data/raw/estimates/),
each asked for once with User-Agent twinfinder/0.1 and kept.
"""
from __future__ import annotations

import collections
import datetime
import json
import math
import os
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from twinfinder import estimates as E  # noqa: E402
from twinfinder import reference  # noqa: E402

DERIVED = Path("data/derived")
REFERENCE = Path("data/reference")
RAW = Path("data/raw/estimates")
OUT_MOON = DERIVED / "estimates_cells.json"
OUT_MARS = DERIVED / "mars_estimates.json"
ROCK_MARGIN_KM_MOON = 8.0   # as scripts/score_cells.py (half the diagonal of an area); used only as a fallback

SOURCE_PAGES = [
    {"file": "nsidc_frozen_ground_permafrost.html",
     "url": "https://nsidc.org/learn/parts-cryosphere/frozen-ground-permafrost",
     "title": "Frozen Ground & Permafrost, National Snow and Ice Data Center (NSIDC)",
     "gave": "defines the active layer as the maximum seasonal thaw depth in permafrost; gives the IPA zones; "
             "no thickness figure by zone"},
    {"file": "nsidc_quick-facts-frozen-ground.html",
     "url": "https://nsidc.org/learn/parts-cryosphere/frozen-ground-permafrost/quick-facts-frozen-ground",
     "title": "Quick Facts on Frozen Ground, NSIDC",
     "gave": "zone shares: discontinuous 50 to 90 %, sporadic 10 to 50 %, isolated 10 % or less of the ground "
             "frozen; no active-layer thickness by zone"},
    {"file": "nsidc_science-frozen-ground.html",
     "url": "https://nsidc.org/learn/parts-cryosphere/frozen-ground-permafrost/science-frozen-ground",
     "title": "Science of Frozen Ground, NSIDC",
     "gave": "describes the active layer and its monitoring; no thickness figure by zone"},
    {"file": "calm_program.html",
     "url": "https://www2.gwu.edu/~calm/about/program.html",
     "title": "CALM (Circumpolar Active Layer Monitoring) Program Description, George Washington University",
     "gave": "defines the active layer and says it is measured by probing; no thickness figure by zone"},
    {"file": "frontiers_feart_2022_910078.html",
     "url": "https://www.frontiersin.org/journals/earth-science/articles/10.3389/feart.2022.910078/full",
     "title": "Rossi M. et al. (2022) Active Layer and Permafrost Investigations Using Geophysical and "
              "Geocryological Methods: A Case Study of the Khanovey Area, Near Vorkuta, in the NE European Russian "
              "Arctic. Frontiers in Earth Science 10, 910078. doi 10.3389/feart.2022.910078 (CC BY)",
     "gave": "one place only, in the continuous zone near Vorkuta: active layer about 1 m by probing, and the "
             "nearby Talnik CALM site's mean active layer grew from 76 to 152 cm over 1998 to 2019; one site, "
             "not a rule of thumb by zone, so not used for metres"},
]


def load(path: Path):
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def write_atomic(path: Path, obj) -> None:
    part = path.with_suffix(path.suffix + ".part")
    with open(part, "w") as f:
        json.dump(obj, f, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    os.replace(part, path)


# --- fetch --------------------------------------------------------------------------------------------------
def fetch_pages() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    log_path = RAW / "downloads.json"
    log = load(log_path) or []
    for page in SOURCE_PAGES:
        dest = RAW / page["file"]
        if dest.exists():
            continue
        for attempt in range(1, 5):
            try:
                req = urllib.request.Request(page["url"], headers={"User-Agent": "twinfinder/0.1"})
                with urllib.request.urlopen(req, timeout=60) as resp:
                    body = resp.read()
                    status = resp.status
                part = dest.with_suffix(dest.suffix + ".part")
                part.write_bytes(body)
                os.replace(part, dest)
                log.append({"file": page["file"], "url": page["url"], "status": status, "bytes": len(body),
                            "fetched": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")})
                break
            except Exception as exc:  # the network has dropped tonight; wait and try again
                print(f"  {page['url']}: {exc}; try {attempt} of 4")
                if attempt == 4:
                    log.append({"file": page["file"], "url": page["url"], "status": f"failed: {exc}"})
                else:
                    time.sleep(10 * attempt)
        time.sleep(2)
    write_atomic(log_path, log)
    print(f"source pages: {sum((RAW / p['file']).exists() for p in SOURCE_PAGES)} of {len(SOURCE_PAGES)} on disk")


# --- shared pieces ------------------------------------------------------------------------------------------
def bodies_by_name():
    bodies = load(REFERENCE / "anorthosite_bodies.json") or []
    return bodies, {b["name"]: b for b in bodies}


def body_at(lat, lon, bodies, margin_km):
    best, best_d = None, None
    for b in bodies:
        d = reference.haversine_km(lat, lon, b["lat"], b["lon"])
        if d <= b["radius_km"] + margin_km and (best_d is None or d < best_d):
            best, best_d = b, d
    return best


def water_sentence(planet):
    # the count of lunar regions and the hydrogen range come from planet_factors.json (twinfinder/estimates.py);
    # scripts/export_site_mars_extra.py makes the same sentence again from the same file
    return E.water_sentence(planet)


WHAT_IT_IS_NOT = {
    "rockiness": "Not a count of rocks or boulders and not the Diviner-style rock abundance: Earth's 90 m height "
                 "data cannot see single rocks, the slopes and roughness are for a 10 km window (Moon part) or a "
                 "55 km square (Mars part), and the rock map gives one class for a box about 55 km across.",
    "heat_response": "Not thermal inertia. The swing is that of the air 2 m above the ground in a MERRA-2 grid box "
                     "about 55 km across, and the albedo that of a 1 degree CERES box; cloud, humidity, wind and "
                     "the sea damp the swing as much as the ground does, so a coastal place can read 'slow' "
                     "because of the sea, not the rock. Thirds are relative to the places of the same file.",
    "mineral_family": "Not read from spectra and not a sample analysis: the usual minerals of the rock map's class "
                      "for a box about 55 km across, or of a listed anorthosite body. The map has no anorthosite "
                      "class; bodies not on our list are missed.",
    "topsoil_water": "Not hydrogen content and not percent water: a model wetness (0 dry to 1 saturated) of the "
                     "top 5 cm in a MERRA-2 grid box, split into thirds relative to the places of the same file. "
                     "Ground ice is from a 1 km model of permafrost probability, not a borehole.",
    "frozen_ground_depth": "Not a depth: a class from the permafrost zone only, with no metres. The thaw depth "
                           "changes from metre to metre with soil, water and plants.",
    "sand_dust": "Not an observation of moving dunes or dust storms. The wind is a monthly mean at 10 m, not the "
                 "gusts that move sand, and whether sand moves depends on grain size and crusts we do not hold.",
    "ilmenite": "Not a detection. Ilmenite also occurs in gabbro and other rocks, and most basalt holds only a "
                "few per cent of it; 'possible' means only that the rock type can host iron-titanium oxide.",
}


def tally(cells):
    out = {}
    for key in ["rockiness", "heat_response", "mineral_family", "topsoil_water", "frozen_ground_depth",
                "sand_dust", "ilmenite"]:
        out[key] = dict(collections.Counter(str(c[key]["estimate"]) if c[key]["estimate"] is not None else "null"
                                            for c in cells.values()).most_common())
    out["ground_ice"] = dict(collections.Counter(str(c["topsoil_water"]["ground_ice"])
                                                 if c["topsoil_water"]["ground_ice"] else "null"
                                                 for c in cells.values()).most_common())
    return out


def base_meta(part, inputs, missing, cuts, planet, extra_sources):
    return {
        "what": f"Rough estimates, by our own stated rules, for seven factors that have no open Earth data, for "
                f"every place of the {part}.",
        "sentence": E.NOT_A_MEASUREMENT,
        "made": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "made_by": "agent ESTIMATES, scripts/build_estimates.py (rules in twinfinder/estimates.py)",
        "rules": [dict(rule, note=E.NOT_A_MEASUREMENT) for rule in E.RULES],
        "thresholds": E.T,
        "cuts": cuts,
        "mineral_family_table": E.MINERAL_FAMILY,
        "heat_response_reads": E.HEAT_READS,
        "frozen_ground_depth_table": {k: {"estimate": v[0], "reads": v[1]} for k, v in E.FROZEN_DEPTH.items()},
        "frozen_ground_depth_sources": {
            "metres": None,
            "why_no_metres": "No open page opened tonight gave a rule of thumb for the summer-thawed layer by "
                             "permafrost zone, so the classes carry no metres, as the job asked.",
            "pages_opened": [{k: p[k] for k in ("title", "url", "gave")} | {"saved": str(RAW / p["file"]),
                                                                          "on_disk": (RAW / p["file"]).exists()}
                             for p in SOURCE_PAGES],
            "licences": "NSIDC pages: NSIDC asks for credit ('Courtesy of the National Snow and Ice Data Center'); "
                        "CALM page: George Washington University, read only; Rossi et al. 2022: CC BY 4.0 "
                        "(Frontiers). Only facts are taken, nothing is copied into the data.",
        },
        "water_sentence": water_sentence(planet),
        "what_it_is_not": WHAT_IT_IS_NOT,
        "fields": {
            "snow_free_months": "rule 0: month numbers, 1 = January",
            "<estimate>.estimate": "the word; null when an input is unknown",
            "<estimate>.figures": "the figures that produced the word, null where unknown",
            "topsoil_water.ground_ice": "likely, possible or unlikely (rule 4)",
            "frozen_ground_depth.metres": "always null (no zone rule of thumb found; see meta.frozen_ground_depth_sources)",
            "mineral_family.estimate": "a family name; its plain-words reading and Moon/Mars likeness are in "
                                       "meta.mineral_family_table (the key 'anorthosite' for plagioclase-rich)",
            "heat_response.estimate": "fast, medium or slow; readings in meta.heat_response_reads",
        },
        "null_rule": "unknown is null, never 0; a rule whose inputs are unknown gives null unless a known input "
                     "settles it on its own (for example under a quarter bare gives low rockiness whatever the slope)",
        "coarse_warning": "Every input here is a grid or map value (NASA POWER grids of 55 km and 1 degree, a rock map "
                          "of 0.5 degree boxes, a 1 km permafrost model, 90 m heights). None of these estimates is a "
                          "measurement at the place.",
        "inputs": inputs,
        "missing_inputs": missing,
        "sources": extra_sources,
        "enters_score": "no; display only",
    }


def source_credits(power_meta, rock_meta, part_files):
    out = {"derived_files_read": part_files}
    if power_meta:
        out["nasa_power"] = {"credit": power_meta.get("credit"), "licence": power_meta.get("licence")}
    if rock_meta:
        srcs = rock_meta.get("sources") or {}
        out["glim"] = {k: (srcs.get("glim") or {}).get(k) for k in ("citation", "licence", "credit")}
        out["permafrost"] = {k: (srcs.get("permafrost") or {}).get(k) for k in ("citation", "licence", "credit")}
        out["rock_frozen_credit_line"] = rock_meta.get("credit_line")
    out["anorthosite_bodies"] = ("data/reference/anorthosite_bodies.json: the project's hand-compiled list; each "
                                 "body carries its own source_url")
    out["bare_share"] = "ESA WorldCover 2021 (CC BY 4.0, credit: ESA WorldCover project 2021 / Contains modified " \
                        "Copernicus Sentinel data (2021) processed by ESA WorldCover consortium), as used by " \
                        "grazing_cells.json and mars_climate.json"
    out["heights"] = "Copernicus DEM GLO-90 (Moon part slopes and roughness; credit: Copernicus DEM, ESA, produced " \
                     "using Copernicus WorldDEM-90, DLR e.V. 2010-2014 and Airbus Defence and Space GmbH 2014-2018) " \
                     "and ETOPO 2022 (Mars part slopes; NOAA NCEI, public domain)"
    return out


# --- the Moon part ------------------------------------------------------------------------------------------
def build_moon(bodies, body_names, planet):
    grazing = load(DERIVED / "grazing_cells.json")
    if grazing is None:
        print("grazing_cells.json missing: no Moon-part estimates")
        return None
    terrain = load(DERIVED / "terrain_cells.json")
    ground = load(DERIVED / "ground_cells.json")
    ground_moon = load(DERIVED / "ground_moon.json")
    power = load(DERIVED / "power_extra_cells.json")
    rockf = load(DERIVED / "rock_frozen_cells.json")
    temp = load(DERIVED / "temperature_cells.json")
    scored = load(DERIVED / "cells_scored.json")
    files = {"grazing_cells.json": "bare share, place list", "terrain_cells.json": "90th-percentile slope",
             "ground_cells.json": "roughness at 90 m", "ground_moon.json": "the lunar regions' 90 m roughness",
             "power_extra_cells.json": "albedo, daily swing, soil wetness, wind",
             "rock_frozen_cells.json": "rock class, permafrost", "temperature_cells.json": "snow-free months, yearly air",
             "cells_scored.json": "anorthosite body (rock score)", "anorthosite_bodies.json": "body composition",
             "planet_factors.json": "lunar hydrogen for the water sentence"}
    got = {"grazing_cells.json": grazing, "terrain_cells.json": terrain, "ground_cells.json": ground,
           "ground_moon.json": ground_moon, "power_extra_cells.json": power, "rock_frozen_cells.json": rockf,
           "temperature_cells.json": temp, "cells_scored.json": scored,
           "anorthosite_bodies.json": bodies or None, "planet_factors.json": planet}
    missing = [f"{k} ({files[k]}): estimates that need it are null" for k, v in got.items() if v is None]
    inputs = {k: {"used_for": files[k], "present": v is not None,
                  "meta_written": ((v or {}).get("meta") or {}).get("written") or ((v or {}).get("meta") or {}).get("made")
                  if isinstance(v, dict) else None} for k, v in got.items()}

    smooth = None
    smooth_region = None
    if ground_moon:
        rough = {rid: reg["roughness_m"]["90"] for rid, reg in ground_moon["regions"].items()
                 if reg.get("roughness_m", {}).get("90") is not None}
        if rough:
            smooth_region = min(rough, key=rough.get)
            smooth = rough[smooth_region]
    body_of = {}
    if scored:
        for c in scored["cells"]:
            name = (c.get("rock") or {}).get("body")
            if name:
                body_of[c["id"]] = body_names.get(name)
    tcells = (terrain or {})
    gcells = (ground or {}).get("cells", {})
    pcells = (power or {}).get("cells", {})
    rcells = (rockf or {}).get("cells", {})
    mcells = (temp or {}).get("cells", {})

    rows = {}
    for c in grazing["cells"]:
        cid = c["id"]
        t2m = (mcells.get(cid) or {}).get("t2m_c")
        months = E.snow_free_months(t2m)
        t2m_year = None if not t2m or any(v is None for v in t2m) else sum(t2m) / 12
        p = pcells.get(cid) or {}
        rk = (rcells.get(cid) or {}).get("rock") or {}
        pf = (rcells.get(cid) or {}).get("permafrost") or {}
        code = rk.get("class_code") if rcells.get(cid) else None
        body = body_of.get(cid) if scored else body_at(c["lat"], c["lon"], bodies, ROCK_MARGIN_KM_MOON)
        antarctic = "permafrost throughout" in (pf.get("note") or "")
        idx = E.heat_index(p.get("albedo"), p.get("t2m_range_c"), months)
        rows[cid] = {
            "lat": c["lat"], "lon": c["lon"], "months": months, "t2m_year": t2m_year, "p": p, "code": code,
            "body": body, "pf": pf, "antarctic": antarctic, "heat": idx,
            "wet": E.mean_over(p.get("soil_wetness_top"), months),
            "wind": E.mean_over(p.get("wind_10m_ms"), months),
            "bare": c.get("bare"), "p90": (tcells.get(cid) or {}).get("p90_slope_deg"),
            "rough90": ((gcells.get(cid) or {}).get("roughness_m") or {}).get("90"),
        }
    cuts = {"heat_index_per_c": E.thirds(r["heat"][0] for r in rows.values()),
            "soil_wetness": E.thirds(r["wet"] for r in rows.values() if r["p"].get("soil_wetness_ice_flag") is False),
            "smoothest_lunar_roughness_90m_m": smooth, "smoothest_lunar_region": smooth_region}
    cells = {cid: make_record(r, cuts, smooth, use_roughness=True) for cid, r in rows.items()}
    cuts_out = {"heat_index_per_c": [E.r(v, 4) for v in cuts["heat_index_per_c"] or []] or None,
                "heat_index_reading": "below the first value: fast; from the first to below the second: medium; "
                                      "the second or more: slow (thirds of the Moon-part areas with a value)",
                "soil_wetness": [E.r(v, 3) for v in cuts["soil_wetness"] or []] or None,
                "soil_wetness_reading": "below the first value: dry; from the first to below the second: moist; the "
                                        "second or more: wet (thirds of the Moon-part areas whose grid point is not ice)",
                "smoothest_lunar_roughness_90m_m": smooth, "smoothest_lunar_region": smooth_region}
    meta = base_meta("Moon part (the areas of data/derived/grazing_cells.json)", inputs, missing, cuts_out, planet,
                     source_credits((power or {}).get("meta"), (rockf or {}).get("meta"), list(files)))
    meta["part_notes"] = [
        "Rock class: the half-degree GLiM box holding the area's centre (coarse = true in rock_frozen_cells.json).",
        "Anorthosite body: the body named by the rock score of cells_scored.json (a listed body whose radius plus "
        "8 km reaches the area centre).",
        f"Roughness test: an area's 90 m roughness against the smoothest lunar region's whole-model 90 m roughness "
        f"({smooth} m, {smooth_region}, ground_moon.json).",
        "Southern areas (Antarctica and nearby islands): permafrost is not in our map; ground ice and frozen ground "
        "use the literature note of rock_frozen_cells.json for all of them, which is a blanket statement and may "
        "overstate frozen ground on the warmer sub-Antarctic islands.",
    ]
    meta["counts"] = {"places": len(cells)} | tally(cells)
    return {"meta": meta, "cells": cells}


def make_record(r, cuts, smooth, use_roughness):
    p = r["p"]
    idx, absorbed, swing, used = r["heat"]
    water = E.topsoil_water(r["wet"], p.get("soil_wetness_ice_flag") if p else None, cuts["soil_wetness"],
                            r["pf"].get("prob_mean"), r["antarctic"], r["t2m_year"])
    dust = E.sand_dust(r["code"], r["bare"], water["estimate"], r["wind"], p.get("soil_wetness_ice_flag") if p else None)
    return {
        "snow_free_months": r["months"],
        "rockiness": E.rockiness(r["bare"], r["p90"], r["rough90"], smooth, r["code"], use_roughness=use_roughness),
        "heat_response": E.heat_response(idx, absorbed, swing, used, cuts["heat_index_per_c"]),
        "mineral_family": E.mineral_family(r["code"], r["body"]),
        "topsoil_water": water,
        "frozen_ground_depth": E.frozen_ground_depth(r["pf"].get("zone"), r["antarctic"], r["t2m_year"]),
        "sand_dust": dust,
        "ilmenite": E.ilmenite(r["code"], r["body"]),
    }


# --- the Mars part ------------------------------------------------------------------------------------------
def build_mars(bodies, planet):
    mcells_file = load(DERIVED / "mars_cells.json")
    if mcells_file is None:
        print("mars_cells.json missing: no Mars-part estimates")
        return None
    terrain = load(DERIVED / "mars_terrain.json")
    power = load(DERIVED / "mars_power_extra.json")
    rockf = load(DERIVED / "mars_rock_frozen.json")
    climate = load(DERIVED / "mars_climate.json")
    files = {"mars_cells.json": "bare share, yearly air, place list", "mars_terrain.json": "90th-percentile slope",
             "mars_power_extra.json": "albedo, daily swing, soil wetness, wind",
             "mars_rock_frozen.json": "rock class, permafrost", "mars_climate.json": "snow-free months",
             "anorthosite_bodies.json": "anorthosite bodies and composition",
             "planet_factors.json": "lunar hydrogen for the water sentence"}
    got = {"mars_cells.json": mcells_file, "mars_terrain.json": terrain, "mars_power_extra.json": power,
           "mars_rock_frozen.json": rockf, "mars_climate.json": climate, "anorthosite_bodies.json": bodies or None,
           "planet_factors.json": planet}
    missing = [f"{k} ({files[k]}): estimates that need it are null" for k, v in got.items() if v is None]
    missing.append("no 90 m roughness for the Mars squares: rockiness uses the slope test alone")
    inputs = {k: {"used_for": files[k], "present": v is not None,
                  "meta_written": ((v or {}).get("meta") or {}).get("written") or ((v or {}).get("meta") or {}).get("made")
                  if isinstance(v, dict) else None} for k, v in got.items()}
    tcells = (terrain or {}).get("cells", {})
    pcells = (power or {}).get("cells", {})
    rcells = (rockf or {}).get("cells", {})
    ccells = (climate or {}).get("cells", {})
    rows = {}
    for cid, c in mcells_file["cells"].items():
        t2m = (ccells.get(cid) or {}).get("t2m_c")
        months = E.snow_free_months(t2m)
        p = pcells.get(cid) or {}
        rk = (rcells.get(cid) or {}).get("rock") or {}
        pf = (rcells.get(cid) or {}).get("permafrost") or {}
        code = rk.get("class_code") if rcells.get(cid) else None
        half = 0.25 * 111.2
        margin = math.hypot(half, half * math.cos(math.radians(c["lat"])))
        body = body_at(c["lat"], c["lon"], bodies, margin)
        antarctic = "permafrost throughout" in (pf.get("note") or "")
        rows[cid] = {
            "lat": c["lat"], "lon": c["lon"], "months": months, "t2m_year": c.get("t2m_year_c"), "p": p,
            "code": code, "body": body, "pf": pf, "antarctic": antarctic,
            "heat": E.heat_index(p.get("albedo"), p.get("t2m_range_c"), months),
            "wet": E.mean_over(p.get("soil_wetness_top"), months),
            "wind": E.mean_over(p.get("wind_10m_ms"), months),
            "bare": c.get("bare"), "p90": (tcells.get(cid) or {}).get("p90_slope_deg"), "rough90": None,
        }
    cuts = {"heat_index_per_c": E.thirds(r["heat"][0] for r in rows.values()),
            "soil_wetness": E.thirds(r["wet"] for r in rows.values() if r["p"].get("soil_wetness_ice_flag") is False)}
    cells = {cid: make_record(r, cuts, None, use_roughness=False) for cid, r in rows.items()}
    cuts_out = {"heat_index_per_c": [E.r(v, 4) for v in cuts["heat_index_per_c"] or []] or None,
                "heat_index_reading": "below the first value: fast; from the first to below the second: medium; "
                                      "the second or more: slow (thirds of the Mars-part squares with a value)",
                "soil_wetness": [E.r(v, 3) for v in cuts["soil_wetness"] or []] or None,
                "soil_wetness_reading": "below the first value: dry; from the first to below the second: moist; the "
                                        "second or more: wet (thirds of the Mars-part squares whose grid point is not ice)"}
    meta = base_meta("Mars part (the squares of data/derived/mars_cells.json)", inputs, missing, cuts_out, planet,
                     source_credits((power or {}).get("meta"), (rockf or {}).get("meta"), list(files)))
    meta["part_notes"] = [
        "Rock class: the GLiM half-degree box that is the square itself.",
        "Anorthosite body: a listed body whose radius plus half the square's diagonal reaches the square's centre "
        "(our own test here; cells_scored.json covers only the Moon part).",
        "Rockiness: slopes from mars_terrain.json are taken across about 3.7 km on ETOPO 2022 heights, so they read "
        "far flatter than 90 m slopes, and no roughness is held: the Mars part has fewer 'high' than the Moon part "
        "for that reason, not because the ground is smoother.",
        "Permafrost: the map covers land from 25 N northward; Antarctic squares use the literature note; elsewhere "
        "without a map value, ground ice is unlikely by the yearly-mean-air test of rule 4 or null.",
    ]
    meta["counts"] = {"places": len(cells)} | tally(cells)
    return {"meta": meta, "cells": cells}


# --- sanity look --------------------------------------------------------------------------------------------
def show(label, cid, rec):
    if rec is None:
        print(f"  {label} ({cid}): not in the file")
        return
    c = rec
    print(f"  {label} ({cid}): months {c['snow_free_months']}")
    for key in ["rockiness", "heat_response", "mineral_family", "topsoil_water", "frozen_ground_depth", "sand_dust",
                "ilmenite"]:
        extra = f", ground ice {c[key]['ground_ice']}" if key == "topsoil_water" else ""
        print(f"     {key}: {c[key]['estimate']}{extra}  {json.dumps(c[key]['figures'], ensure_ascii=False)}")


def nearest_square(cells, lat, lon):
    best = min(cells, key=lambda k: (float(k.split('_')[1]) - lat) ** 2 + (float(k.split('_')[2]) - lon) ** 2)
    return best


def main(argv):
    if argv and argv[0] == "fetch":
        fetch_pages()
        return
    if not all((RAW / p["file"]).exists() for p in SOURCE_PAGES):
        print("note: some source pages are not on disk; run 'build_estimates.py fetch' to get them (build goes on)")
    t0 = time.time()
    bodies, names = bodies_by_name()
    planet = load(DERIVED / "planet_factors.json")
    moon = build_moon(bodies, names, planet)
    if moon:
        write_atomic(OUT_MOON, moon)
        print(f"wrote {OUT_MOON} ({len(moon['cells'])} areas, {OUT_MOON.stat().st_size / 1e6:.1f} MB)")
    mars = build_mars(bodies, planet)
    if mars:
        write_atomic(OUT_MARS, mars)
        print(f"wrote {OUT_MARS} ({len(mars['cells'])} squares, {OUT_MARS.stat().st_size / 1e6:.1f} MB)")
    print(f"{time.time() - t0:.1f} s")
    if moon:
        print("Moon part cuts:", json.dumps(moon["meta"]["cuts"]))
        print("Moon part counts:", json.dumps(moon["meta"]["counts"], ensure_ascii=False))
        for label, cid in [("Haughton crater", "75.3_-90.0"), ("south-west Iceland", "63.8_-22.6"),
                           ("Pechora Sea coast", "68.9_54.3"), ("Dry Valleys", "-77.6_161.5")]:
            show(label, cid, moon["cells"].get(cid))
    if mars:
        print("Mars part cuts:", json.dumps(mars["meta"]["cuts"]))
        print("Mars part counts:", json.dumps(mars["meta"]["counts"], ensure_ascii=False))
        for label, lat, lon in [("Atacama near Yungay", -24.1, -70.0), ("Tibetan Plateau", 34.5, 86.0)]:
            cid = nearest_square(mars["cells"], lat, lon)
            show(label, cid, mars["cells"][cid])


if __name__ == "__main__":
    main(sys.argv[1:])

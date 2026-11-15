# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Shape of the ground: roughness at several baselines, a landform class and the share of the low-Sun hours in
terrain shadow, for every Moon-part area, the lunar regions and (coarsely, from what is already there) the
Mars-part squares. Functions in twinfinder/ground.py.

Writes
    data/derived/ground_moon.json     the lunar regions (5 m LOLA models on disk; null figures without a model)
    data/derived/ground_cells.json    every area of data/derived/grazing_cells.json (Copernicus GLO-90 on disk)
    data/derived/mars_ground.json     every square of data/derived/mars_cells.json, re-labelled from mars_terrain.json

    uv run python scripts/build_ground_cells.py                 reuses the roughness already in ground_cells.json
    uv run python scripts/build_ground_cells.py --fresh         works every area out again
    uv run python scripts/build_ground_cells.py --limit 200     only the first 200 areas still to do (a trial run)
    uv run python scripts/build_ground_cells.py --processes 4   fewer processes (8 unless told otherwise)

Asks no server for anything: every elevation tile is read from data/raw/glo90, and an area that would need a
tile that is not on disk is written with its reason and null figures. The shadow shares come from
data/derived/grazing_bins.npz, which scripts/build_grazing_cells.py made with the project's Sun table
(sun.long_band_minutes_table) and grazing.hours_by_bin; the sanity look at the end works a few areas out
again from the Sun table itself (grazing.long_window_hours_by_bin) and prints both.
"""
import json
import math
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from pathlib import Path

import numpy as np

from twinfinder import earth, grazing, ground

try:                                             # imported as part of the scripts folder
    from scripts import build_horizon_cells as tiles
except ImportError:                              # started as a script: the sister script is next to this one
    import build_horizon_cells as tiles

CELLS = Path("data/derived/grazing_cells.json")
BINS = Path("data/derived/grazing_bins.npz")
TARGETS = Path("data/derived/moon_targets.json")
MARS_TERRAIN = Path("data/derived/mars_terrain.json")
MARS_CELLS = Path("data/derived/mars_cells.json")
OUT_CELLS = Path("data/derived/ground_cells.json")
OUT_MOON = Path("data/derived/ground_moon.json")
OUT_MARS = Path("data/derived/mars_ground.json")
RAW = Path("data/raw")
HALF_KM = 5.0          # as build_terrain_cells.py: a 10 km window of 90 m pixels around the area's centre
PIXEL_M = 90.0
PROCESSES = 8
SAVE_EVERY = 2000
NOT_YET = "not worked out yet (run without --limit)"
MADE_BY = "agent GROUND-SHAPE, scripts/build_ground_cells.py (functions in twinfinder/ground.py)"

SANITY = [   # (what, lat, lon): the nearest area is shown
    ("Haughton crater, Devon Island", 75.38, -89.67),
    ("Reykjanes, south-west Iceland", 63.88, -22.45),
    ("Hellisheidi lava, south-west Iceland", 64.03, -21.35),
    ("Pechora Sea coast", 68.95, 54.45),           # as build_cloud_cells.py and check_known_analogs.py
    ("Dry Valleys, Wright Valley", -77.52, 161.85),
    ("Dry Valleys, Taylor Valley", -77.62, 162.90),
]

SOURCES = {
    "Copernicus DEM GLO-90": {
        "files": "data/raw/glo90/*_DEM.tif and *_WBM.tif (on disk; nothing fetched by this script)",
        "url": "https://copernicus-dem-90m.s3.amazonaws.com",
        "licence": "Licence for COP-DEM-GLO-90-F Global 90m Full, Free & Open (see data/SOURCES.md, row 6)",
        "credit": "produced using Copernicus WorldDEM-90 (c) DLR e.V. 2010-2014 and (c) Airbus Defence and Space "
                  "GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved. "
                  "The organisations in charge of the Copernicus programme by law or by delegation do not incur any "
                  "liability for any use of the Copernicus WorldDEM-90.",
    },
    "LOLA 5 m terrain models (PGDA product 78)": {
        "files": "data/raw/Site01_, Site23_, Site20v2_, DM2_final_adj_5mpp_surf.tif (on disk)",
        "url": "https://pgda.gsfc.nasa.gov/products/78",
        "licence": "Data Usage Policy on the product page: cite the paper; NASA material is not copyrighted in the US "
                   "(data/SOURCES.md, row 1)",
        "credit": "Barker, M.K., et al. (2021), Improved LOLA Elevation Maps for South Pole Landing Sites: Error "
                  "Estimates and Their Impact on Illumination Conditions, Planetary & Space Science, Volume 203, "
                  "105119, doi:10.1016/j.pss.2020.105119. Data: NASA Goddard Planetary Geodesy Data Archive.",
    },
    "LOLA illumination map (PGDA product 69), read through moon_targets.json": {
        "url": "https://pgda.gsfc.nasa.gov/products/69",
        "licence": "cite the paper (data/SOURCES.md, row 2)",
        "credit": "Mazarico, E., et al. (2011), Illumination conditions of the lunar polar regions using LOLA "
                  "topography, Icarus, Volume 211, Issue 2, 1066-1081, doi:10.1016/j.icarus.2010.10.030.",
    },
    "Sun table, snow-free odds and horizons, read through grazing_bins.npz and horizon_cells.json": {
        "licence": "the project's own files (CC BY 4.0); the snow odds carry the IMS credit line of NOTICE (G) and "
                   "the horizons the Copernicus line above",
        "credit": "U.S. National Ice Center. (2008). IMS Daily Northern Hemisphere Snow and Ice Analysis at 1 km, "
                  "4 km, and 24 km Resolutions. (G02156, Version 1). NSIDC. https://doi.org/10.7265/N52R3PMC",
    },
}
SOURCES_MARS = {
    "MGS MOLA MEGDR, 32 pixels per degree, read through mars_terrain.json": {
        "url": "https://pds-geosciences.wustl.edu/mgs/urn-nasa-pds-mgs_mola_topography_derived/meg032/",
        "licence": "NASA Planetary Data System archive; NASA material is not copyrighted in the US (general NASA "
                   "policy; no licence page was opened tonight)",
        "credit": "Smith, D. E., et al., Mars Global Surveyor Laser Altimeter Mission Experiment Gridded Data Record, "
                  "MGS-M-MOLA-5-MEGDR-L3-V1.0, NASA Planetary Data System.",
    },
    "NOAA NCEI ETOPO 2022, 60 arc-seconds, read through mars_terrain.json": {
        "url": "https://www.ncei.noaa.gov/products/etopo-global-relief-model",
        "licence": "NOAA data, US public domain (general NOAA policy; no licence page was opened tonight)",
        "credit": "NOAA National Centers for Environmental Information. 2022: ETOPO 2022 15 Arc-Second Global Relief "
                  "Model. NOAA National Centers for Environmental Information. doi:10.25921/fd45-gt74",
    },
}


def write_json(path: Path, value) -> None:
    side = path.with_name(path.name + ".part")
    side.write_text(json.dumps(value, separators=(",", ":"), allow_nan=False))
    os.replace(side, path)


def _init() -> None:
    """Run once in every worker: the elevation code can only read tiles already on disk."""
    tiles.no_downloads()


def one_area(cell: dict) -> tuple[str, dict, float]:
    """One area in a worker: its id, its record and the seconds it took."""
    started = time.perf_counter()
    try:
        result = ground.window_record(earth.elevation_window(cell["lat"], cell["lon"], HALF_KM, PIXEL_M), PIXEL_M)
    except ValueError as error:      # a window across the antimeridian or over a pole
        result = {"skipped": str(error)}
    except Exception as error:       # a tile not on disk, or anything else: kept, tried again next run
        result = {"skipped": f"failed: {type(error).__name__}: {error}"}
    return cell["id"], result, time.perf_counter() - started


def settled(stored: dict | None) -> bool:
    """True for a stored area that needs no new reading: it has roughness, or it was refused for good."""
    if stored is None:
        return False
    skipped = stored.get("skipped", "")
    return "roughness_m" in stored or (bool(skipped) and not skipped.startswith(("failed", NOT_YET)))


# The lunar regions --------------------------------------------------------------------------------------------------

NO_MODEL = ("NASA gives no 5 m terrain model of this lunar region. Thus its roughness, slope and landform are "
            "unknown.")


def region_without_model(target: dict) -> dict:
    """The ground record of a lunar region without a 5 m model: the same keys, each figure null, and the reason."""
    fine = {str(b): None for b in ground.BASELINES_FINE_M}
    earth_baselines = {str(b): None for b in ground.BASELINES_EARTH_M}
    return {
        "pixel_m_model": None, "extent_km": None, "valid_share_5m": None,
        "roughness_m_fine": fine, "roughness_m": earth_baselines,
        "roughness_m_10km_pieces": {b: None for b in earth_baselines},
        "median_slope_deg": None, "p90_slope_deg": None, "relief_m": None, "landform_whole_region": None,
        "landform_10km_pieces": {"counts": None, "most_common": None, "pieces": None}, "relief_m_10km_pieces": None,
        "has_model": False, "why_null": NO_MODEL,
        "name": target["name"], "model_file": None, "centre_lat": round(target["centre_lat"], 3),
        "centre_lon": round(target["centre_lon"], 3), "sun_limit_deg": grazing.target_limit(target["sun_max_elev_deg"]),
        "sunlit_share_of_all_time": ground.known(target.get("illumination_mean"), 3),
        "permanent_shadow_share": ground.known(target.get("permanent_shadow_fraction"), 4),
        "position_source": target.get("position_source"), "position_how_sure": target.get("position_how_sure"),
    }


def lunar_regions() -> dict:
    regions = {}
    for target in json.loads(TARGETS.read_text()):
        if not target.get("source"):
            regions[target["id"]] = region_without_model(target)
            print(f"  {target['name']:18s} no 5 m model: roughness, slope and landform unknown", flush=True)
            continue
        path = RAW / target["source"].rsplit("/", 1)[-1]
        started = time.perf_counter()
        z5, pixel_m = ground.read_lunar_model(path)
        record = ground.lunar_region_record(z5, pixel_m)
        record.update({
            "has_model": True,
            "name": target["name"], "model_file": str(path), "centre_lat": round(target["centre_lat"], 3),
            "centre_lon": round(target["centre_lon"], 3), "sun_limit_deg": grazing.target_limit(target["sun_max_elev_deg"]),
            "sunlit_share_of_all_time": ground.known(target.get("illumination_mean"), 3),
            "permanent_shadow_share": ground.known(target.get("permanent_shadow_fraction"), 4),
        })
        regions[target["id"]] = record
        print(f"  {target['name']:18s} {path.name}: {z5.shape[0]} x {z5.shape[1]} px, {time.perf_counter() - started:.1f} s;"
              f" roughness 5/15/45 m: {list(record['roughness_m_fine'].values())} m;"
              f" 90/270/810 m: {list(record['roughness_m'].values())} m; landform (10 km pieces): "
              f"{record['landform_10km_pieces']['most_common']} {record['landform_10km_pieces']['counts']}", flush=True)
    return regions


def moon_meta(regions: dict) -> dict:
    return {
        "what": "Shape of the ground of the lunar regions: roughness at 5, 15, 45, 90, 270 and 810 m, slope "
                "figures and a landform class, from NASA Goddard's 5 m LOLA terrain models. A region without a "
                "model (has_model false) has null figures and the reason in why_null.",
        "made": datetime.now().astimezone().isoformat(timespec="seconds"), "made_by": MADE_BY,
        "roughness_definition": ground.__doc__.split("Terrain shadow:")[0].strip(),
        "roughness_grids": "5, 15 and 45 m on the 5 m model itself (lags of 1, 3 and 9 pixels); 90, 270 and 810 m on "
                           "block means of 18 x 18 pixels (90 m), the grid moon.fingerprint takes its 90 m slopes from, "
                           "so that they compare with Earth's 90 m windows",
        "fine_baselines_note": "Earth's 90 m Copernicus data cannot see 5, 15 or 45 m: those three are given for the "
                               "Moon only and no Earth area has a ratio at them. Roughness at 5 m is set in part by "
                               "how the LOLA 5 m model was interpolated between laser tracks; read it as an upper "
                               "bound of model detail, not of boulders.",
        "roughness_m_10km_pieces": "spread (10th, 50th, 90th percentile) over 10 km squares cut every kilometre: what an "
                                   "Earth window of that size would see if it lay inside the region",
        "landform_table": ground.LANDFORM_TABLE, "landform_thresholds": ground.LANDFORM_THRESHOLDS,
        "landform_label": ground.LANDFORM_LABEL, "landform_source": ground.LANDFORM_SOURCE,
        "landform_note": "landform_whole_region uses the whole model (16 to 26 km across, so its relief is larger than "
                         "a 10 km window's); landform_10km_pieces is the class of each 10 km piece, the size of an "
                         "Earth window, and the one to compare with Earth areas",
        "sunlit_share_of_all_time": "mean over the region of NASA Goddard's 240 m map of the share of time the Sun is "
                                    "visible (moon_targets.json illumination_mean); it covers all times, not only low-Sun "
                                    "hours, and is NOT the same measure as the Earth areas' shadow share",
        "sources": SOURCES, "regions": list(regions),
    }


# Terrain shadow from the binned hours ------------------------------------------------------------------------------

def shadow_shares(cells: list[dict], targets: list[str]) -> dict[str, dict]:
    """Per area: shadow share per lunar region, its basis and the low-Sun hours it is a share of."""
    bins = np.load(BINS)
    ids = [str(i) for i in bins["ids"]]
    if [str(t) for t in bins["targets"]] != targets:
        raise ValueError(f"{BINS} has targets {list(bins['targets'])}, expected {targets}")
    where = {cid: k for k, cid in enumerate(ids)}
    long_flat, long_snow_free, long_open = bins["long_flat"], bins["long_snow_free"], bins["long_open"]
    out = {}
    for cell in cells:
        k = where.get(cell["id"])
        north = cell["hemisphere"] == "N"
        record = {"basis": "snow-free low-Sun hours" if north else "all low-Sun hours (snow not measured in the south)",
                  "share": {t: None for t in targets}, "low_sun_hours": {t: None for t in targets}}
        if k is not None:
            base = long_snow_free[k] if north else long_flat[k]          # [targets, 36]
            share = ground.shadow_share_from_hours(base, long_open[k])
            hours = grazing.total(base)
            for t, tid in enumerate(targets):
                record["share"][tid] = ground.known(share[t], 3)
                record["low_sun_hours"][tid] = ground.known(hours[t], 1)
        out[cell["id"]] = record
    return out


def fresh_check(cells: list[dict], targets: list[dict]) -> dict[str, list]:
    """The shadow share of a few areas worked out again from the Sun table itself (sun.long_band_minutes_table)."""
    got = grazing.long_window_hours_by_bin(cells, targets=targets)
    out = {}
    for i, cell in enumerate(cells):
        base = got["long_snow_free"][i] if cell["hemisphere"] == "N" else got["long_flat"][i]
        out[cell["id"]] = [ground.known(v, 3) for v in ground.shadow_share_from_hours(base, got["long_open"][i])]
    return out


def cells_meta(regions: dict, counts: dict, seconds: float) -> dict:
    return {
        "what": "Shape of the ground of every Moon-part area: roughness at 90, 270 and 810 m, slope figures and a "
                "landform class from a 10 km window of Copernicus GLO-90 at 90 m, the roughness against each lunar "
                "region, and the share of the low-Sun hours a typical point of the area spends in terrain shadow.",
        "made": datetime.now().astimezone().isoformat(timespec="seconds"), "made_by": MADE_BY,
        "areas_file": str(CELLS), "window": "10 km square of 90 m pixels on a local equal-distance grid centred on "
                                            "the area's centre (earth.elevation_window, as terrain_cells.json); water "
                                            "(Copernicus water mask) and missing tiles are left out",
        "roughness_definition": ground.__doc__.split("Terrain shadow:")[0].strip(),
        "roughness_m": "metres, root-mean-square at each baseline (90, 270, 810 m) over the land of the window",
        "roughness_is_not": "not a measurement at one point, not boulders or rock fields (nothing under 90 m is seen; "
                            "Earth's 90 m data cannot see 5, 15 or 45 m at all), and not bare-earth everywhere: "
                            "Copernicus GLO-90 is a surface model (tops of forest and buildings). The 90 m figure is "
                            "smoothed by the bilinear resampling from the tiles' 3 arc-second grid; the lunar 90 m "
                            "figure by 90 m block means: both are smoothed, not identically.",
        "roughness_vs_region": "the area's roughness divided by the lunar region's (whole 5 m model, at 90 m) at the "
                               "same baseline: 1 is as rough, under 1 smoother, over 1 rougher. Ratios use the region's "
                               "whole-model value; its spread over 10 km pieces is in ground_moon.json",
        "landform": ground.LANDFORM_LABEL, "landform_table": ground.LANDFORM_TABLE,
        "landform_thresholds": ground.LANDFORM_THRESHOLDS, "landform_inputs": ground.LANDFORM_INPUTS,
        "landform_source": ground.LANDFORM_SOURCE,
        "shadow": "share of the low-Sun hours (Sun's centre above 0 and at or below the region's limit, inside spells "
                  "of at least 2 h, the long_* hours of grazing_cells.json) during which a typical point of the area "
                  "lies in terrain shadow: one minus the long-window open hours over the long-window snow-free hours "
                  "(north) or over the long-window flat hours (south, where the snow is not measured: terrain only). "
                  "Both sums are weighted by the same snow-free odds, so the snow cancels except in how it weighs the "
                  "ten-day bins.",
        "shadow_is_not": "not the shadow at one spot; a share of the area's land averaged over the hours. A Sun bin "
                         "counts as seen from a pixel only when the whole elevation bin clears its horizon, so the "
                         "share leans high. Horizons from Copernicus GLO-90 resampled to 60 m, reach 25 km, eye 2 m "
                         "(horizon_cells.json); no clouds, no vegetation shade, no buildings. Null where the area has "
                         "no low-Sun hours in long spells (nothing to be in shadow for), no horizon, or unknown snow.",
        "low_sun_hours": "hours per year the shadow share is a share of (long-window snow-free hours in the north, "
                         "long-window flat hours in the south), per lunar region",
        "shadow_inputs": f"{BINS} (long_flat, long_snow_free, long_open; built by scripts/build_grazing_cells.py with "
                         f"sun.long_band_minutes_table and grazing.hours_by_bin from horizon_cells.json)",
        "regions": {rid: {"name": r["name"], "roughness_m": r["roughness_m"], "sun_limit_deg": r["sun_limit_deg"],
                          "has_model": r.get("has_model", True)}
                    for rid, r in regions.items()},
        "counts": counts, "seconds": round(seconds, 1), "sources": SOURCES,
        "null_rule": "unknown is null, never 0",
    }


def counts_of(records: dict, targets: list[str]) -> dict:
    landform = {name: 0 for name in ground.LANDFORM_CLASSES}
    landform["unknown"] = 0
    skipped = {}
    with_roughness = 0
    for r in records.values():
        landform[r.get("landform") or "unknown"] += 1
        if r.get("roughness_m") and r["roughness_m"].get("90") is not None:
            with_roughness += 1
        if "skipped" in r:
            key = "crosses the antimeridian" if "antimeridian" in r["skipped"] else r["skipped"].split(":")[0]
            skipped[key] = skipped.get(key, 0) + 1
    shadow_known = {t: sum(r["shadow"]["share"][t] is not None for r in records.values()) for t in targets}
    return {"areas": len(records), "with_roughness_90m": with_roughness, "by_landform": landform,
            "skipped": skipped, "with_shadow_share": shadow_known}


# Mars part ----------------------------------------------------------------------------------------------------------

def mars_record(src: dict | None) -> dict:
    if src is None:
        return {"median_slope_deg": None, "p90_slope_deg": None, "relief_m": None, "relief_class": None,
                "slope_pixels": None, "why_null": "not in mars_terrain.json (under 20 % land inside the outline)"}
    return {"median_slope_deg": src.get("median_slope_deg"), "p90_slope_deg": src.get("p90_slope_deg"),
            "relief_m": src.get("relief_m"), "relief_class": ground.relief_class(src.get("relief_m")),
            "slope_pixels": src.get("pixels")}


def mars_part() -> dict:
    terrain = json.loads(MARS_TERRAIN.read_text())
    squares = json.loads(MARS_CELLS.read_text())["cells"]
    cells = {sid: mars_record(terrain["cells"].get(sid)) for sid in squares}
    sites = {sid: mars_record(s) for sid, s in terrain["sites"].items()}
    by_relief = {}
    for r in cells.values():
        by_relief[r["relief_class"] or "unknown"] = by_relief.get(r["relief_class"] or "unknown", 0) + 1
    meta = {
        "what": "Mars part, first pass: the slope and relief that mars_terrain.json already holds for every square of "
                "mars_cells.json and for the Mars sites, re-labelled. Nothing finer is worked out: MOLA (Mars) "
                "and ETOPO 2022 (Earth) give a height every 1.85 km.",
        "made": datetime.now().astimezone().isoformat(timespec="seconds"), "made_by": MADE_BY,
        "from": str(MARS_TERRAIN), "squares_file": str(MARS_CELLS),
        "fields": {
            "median_slope_deg": "median slope, degrees, over a span of about 3.7 km (heights every 1.85 km), over the "
                                "square's land (Earth, 0.5 degree, about 55 km north-south) or the site's 2 x 2 degree "
                                "box (Mars, about 118 km)",
            "p90_slope_deg": "90th-percentile slope, same span",
            "relief_m": "95th minus 5th percentile of the heights, metres, over the square or the site box",
            "relief_class": "a band of relief_m (table relief_classes), over 55 km squares or 118 km boxes",
            "slope_pixels": "pixels with a slope (about 1.85 km each)",
        },
        "relief_classes": [{"under_m": None if math.isinf(u) else u, "class": name} for u, name in ground.RELIEF_CLASSES_M],
        "is_not": [
            "No roughness at 90, 270 or 810 m and no landform class: a height every 1.85 km cannot see them, and the "
            "Moon part's landform table was set for 10 km windows of 90 m pixels; its slope thresholds would put "
            "almost every square in 'plain' at a 3.7 km span. Both are null by design, not unknown by accident.",
            "No terrain shadow: the Mars part has no Sun table by sector and Sun height and no horizon file.",
            "A Mars site box (118 km) is about twice an Earth square (55 km north-south, narrower east-west), so their "
            "reliefs are not over the same area.",
            "Slopes over 3.7 km are much gentler than slopes a rover or a person meets.",
        ],
        "roughness_m": None, "landform": None, "shadow": None,
        "counts": {"squares": len(cells), "with_slope": sum(r["median_slope_deg"] is not None for r in cells.values()),
                   "by_relief_class": by_relief},
        "sources": SOURCES_MARS, "null_rule": "unknown is null, never 0",
    }
    return {"meta": meta, "sites": sites, "cells": cells}


# Main ---------------------------------------------------------------------------------------------------------------

def nearest(cells: list[dict], lat: float, lon: float) -> dict:
    def km(c):
        dlat = c["lat"] - lat
        dlon = ((c["lon"] - lon + 180.0) % 360.0 - 180.0) * math.cos(math.radians(lat))
        return math.hypot(dlat, dlon) * 111.32
    best = min(cells, key=km)
    return {**best, "_km": km(best)}


def main(fresh: bool = False, limit: int | None = None, processes: int = PROCESSES) -> None:
    started = time.perf_counter()
    grazing.check_shared_bins()

    print("lunar regions (5 m models):", flush=True)
    regions = lunar_regions()
    write_json(OUT_MOON, {"meta": moon_meta(regions), "regions": regions})
    print(f"wrote {OUT_MOON}", flush=True)

    cells = json.loads(CELLS.read_text())["cells"]
    targets = [t["id"] for t in grazing.load_targets()]
    stored = {}
    if OUT_CELLS.exists() and not fresh:
        stored = {cid: {k: v for k, v in r.items() if k not in ("roughness_vs_region", "shadow")}
                  for cid, r in json.loads(OUT_CELLS.read_text())["cells"].items()}
    todo = [c for c in cells if not settled(stored.get(c["id"]))]
    if limit is not None:
        todo = todo[:limit]
    print(f"areas: {len(cells)}; already done: {len(cells) - len([c for c in cells if not settled(stored.get(c['id']))])};"
          f" to do in this run: {len(todo)}", flush=True)

    if todo:
        _init()
        cid, result, took = one_area(todo[0])                    # one area first, timed, in this process
        stored[cid] = result
        print(f"one area timed: {cid}: {took:.3f} s -> {json.dumps(result)}", flush=True)
        compute_started = time.perf_counter()
        seconds = [took]
        with ProcessPoolExecutor(max_workers=processes, initializer=_init) as pool:
            for count, (cid, result, took) in enumerate(pool.map(one_area, todo[1:], chunksize=16), start=2):
                stored[cid] = result
                seconds.append(took)
                if count % SAVE_EVERY == 0:
                    print(f"  {count} of {len(todo)} areas, {time.perf_counter() - compute_started:.0f} s", flush=True)
        print(f"worked out {len(seconds)} areas in {time.perf_counter() - compute_started:.0f} s with {processes} "
              f"processes; inside a worker: mean {np.mean(seconds):.3f} s, max {np.max(seconds):.2f} s per area", flush=True)

    shadows = shadow_shares(cells, targets)
    records = {}
    for c in cells:
        r = dict(stored.get(c["id"]) or {"skipped": NOT_YET})
        r = {"lat": c["lat"], "lon": c["lon"], "hemisphere": c["hemisphere"], **r}
        rough = r.get("roughness_m") or {}
        r["roughness_vs_region"] = {rid: {b: ground.ratio(rough.get(b), reg["roughness_m"].get(b))
                                          for b in map(str, ground.BASELINES_EARTH_M)}
                                    for rid, reg in regions.items()}
        r["shadow"] = shadows[c["id"]]
        records[c["id"]] = r
    counts = counts_of(records, targets)
    write_json(OUT_CELLS, {"meta": cells_meta(regions, counts, time.perf_counter() - started), "cells": records})
    print(f"wrote {OUT_CELLS}; counts: {json.dumps(counts)}", flush=True)

    mars = mars_part()
    write_json(OUT_MARS, mars)
    print(f"wrote {OUT_MARS}; counts: {json.dumps(mars['meta']['counts'])}", flush=True)

    sanity(cells, records, regions, mars)
    print(f"whole run {time.perf_counter() - started:.0f} s")


def sanity(cells: list[dict], records: dict, regions: dict, mars: dict) -> None:
    print("\nSANITY LOOK")
    for rid, r in regions.items():
        print(f"  {r['name']:18s} rough 5/15/45 m {list(r['roughness_m_fine'].values())}  90/270/810 m "
              f"{list(r['roughness_m'].values())}  median/p90 slope {r['median_slope_deg']}/{r['p90_slope_deg']} deg  "
              f"relief {r['relief_m']} m  10 km pieces: {r['landform_10km_pieces']['counts']}  "
              f"sunlit share of all time {r['sunlit_share_of_all_time']}")
    targets = grazing.load_targets()
    picked = []
    for what, lat, lon in SANITY:
        c = nearest(cells, lat, lon)
        picked.append((what, c))
    try:
        t0 = time.perf_counter()
        fresh = fresh_check([c for _, c in picked], targets)
        print(f"  (fresh shadow shares from the Sun table for {len(picked)} areas in {time.perf_counter() - t0:.0f} s)")
    except Exception as error:       # the check must not lose the files already written
        fresh = {}
        print(f"  fresh check from the Sun table failed: {type(error).__name__}: {error}")
    for what, c in picked:
        r = records[c["id"]]
        print(f"  {what} -> area {c['id']} ({c['_km']:.0f} km off): {r.get('landform')}; rough 90/270/810 m "
              f"{list((r.get('roughness_m') or {}).values())}; slope median/p90 {r.get('median_slope_deg')}/"
              f"{r.get('p90_slope_deg')} deg; relief {r.get('relief_m')} m; vs Mons Mouton "
              f"{list(r['roughness_vs_region']['mons-mouton'].values())}")
        print(f"      shadow share ({r['shadow']['basis']}): {r['shadow']['share']} of hours {r['shadow']['low_sun_hours']};"
              f" fresh from the Sun table: {fresh.get(c['id'])}" + (f"; skipped: {r['skipped']}" if 'skipped' in r else ""))
    print(f"  landform counts: {json.dumps(counts_of(records, [t['id'] for t in targets])['by_landform'])}")
    for sid, s in mars["sites"].items():
        print(f"  Mars site {sid}: {s}")


def options(arguments: list[str]) -> dict:
    found = {"fresh": False, "limit": None, "processes": PROCESSES}
    rest = list(arguments)
    while rest:
        argument = rest.pop(0)
        if argument == "--fresh":
            found["fresh"] = True
        elif argument in ("--limit", "--processes") and rest and rest[0].isdigit() and int(rest[0]) >= 1:
            found[argument[2:]] = int(rest.pop(0))
        else:
            sys.exit(f"cannot read the argument {argument!r}; known: --fresh, --limit N, --processes N")
    return found


if __name__ == "__main__":
    main(**options(sys.argv[1:]))

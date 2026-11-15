# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Winter leads: what the bare-ground screen hides in the winter half (28 September to 31 March).

The pipeline keeps a northern land square only when at least 15 percent of its
land is bare by ESA WorldCover. This script takes the squares the screen leaves
out that still hold some bare ground (at least FLOOR_KM2 of it), and works out
for each, with the pipeline's own functions, the long-spell low-Sun hours on
snow-free ground in the winter half and in the whole year for the four lunar
targets, over a flat horizon. For the TOP_HORIZONS squares with the most winter
hours it also computes the terrain horizon (60 m, as build_horizon_cells.py
does) and the hours that survive terrain.

Writes data/derived/winter_leads.json. Safe to run again: horizons already in
the file are reused, the file is written beside the old one and renamed.

    uv run python scripts/build_winter_leads.py                 downloads missing elevation tiles
    uv run python scripts/build_winter_leads.py --cached-only   asks the server for nothing
"""
import importlib
import json
import os
import sys
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:   # so that the sibling build scripts can be imported when this file is run directly
    sys.path.insert(0, str(ROOT))

from twinfinder import earth, grazing, grid, landcover, regions, rock_south, sun  # noqa: E402

grazing_build = importlib.import_module("scripts.build_grazing_cells")
horizon_build = importlib.import_module("scripts.build_horizon_cells")

NORTH = Path("data/derived/landcover_cells.json")
SCREENED = Path("data/derived/grazing_cells.json")
SNOW = grazing.SNOW_ARCHIVE
OUT = Path("data/derived/winter_leads.json")

MIN_BARE = grazing_build.MIN_BARE     # the screen of the pipeline: squares under it are the ones looked at here
FLOOR_KM2 = 1.0                       # "some bare ground": at least this much in the square (the main floor)
FLOORS_KM2 = (0.25, 1.0, 3.0)         # the count of leads is shown at each of these
LIST_MIN_H = 50.0                     # a square is listed as a lead from this many winter hours on snow-free ground
THRESHOLDS = (50, 100)                # counts by region are given at these hours
FLOOR_THRESHOLDS = (50, 100, 200)
TOP_HORIZONS = 300                    # squares at the main floor that get a terrain horizon, most winter hours first
RIM = ("Shetland", "Orkney", "Faroe Islands")   # every square of these regions gets a horizon too, at any floor shown
PROCESSES = 6
FETCH_ROUNDS = 3                      # the network drops now and then: failed tiles are asked for again
SOUTH_BATCH = 256
CHECK_CELLS = 60                      # screened squares worked out again here and held against the cells file
CHECK_TOLERANCE_H = 0.06              # the cells file is rounded to 0.1 h

known = grazing.known


def written_at(path) -> str:
    return datetime.fromtimestamp(Path(path).stat().st_mtime).isoformat(timespec="seconds")


SUN_CODE_READ = written_at(sun.__file__)   # the Sun code as it stood when this run loaded it
# The calendars the pipeline averages its Sun tables over, passed on exactly as build_grazing_cells.py passes them
# (the Sun code before the leap-cycle average has no such setting and uses one calendar).
YEAR_PHASES = {"year_phases": grazing.YEAR_PHASES} if hasattr(grazing, "YEAR_PHASES") else {}

# (name, south, north, west, east). Rough boxes, a reading aid only; the first match wins, and a point in none
# of them keeps the name the project's own table gives it (twinfinder.regions).
BOXES = [
    ("Orkney", 58.6, 59.45, -3.6, -2.2),
    ("Shetland", 59.45, 61.0, -2.3, -0.5),
    ("Faroe Islands", 61.3, 62.5, -7.8, -6.2),
    ("Iceland", 63.0, 67.0, -25.0, -13.0),
    ("South Greenland", 59.0, 61.5, -49.0, -42.0),
    ("Norway: Rogaland", 59.0, 59.55, 4.5, 7.3),
    ("Norway: Vestland", 59.55, 62.0, 4.5, 7.9),
    ("Norway: More og Romsdal", 62.0, 63.45, 5.0, 9.6),
    ("Norway: Trondelag", 63.45, 65.15, 7.5, 9.6),
    ("Norway: Trondelag", 62.9, 64.0, 9.6, 12.2),
    ("Norway: Trondelag", 64.0, 65.15, 9.6, 13.9),
    ("Norway: Troms", 68.55, 70.4, 16.3, 22.0),
    ("Norway: Nordland", 65.15, 66.3, 11.0, 14.6),
    ("Norway: Nordland", 66.3, 67.3, 11.0, 16.0),
    ("Norway: Nordland", 67.3, 69.35, 11.0, 18.1),
    ("Norway: Finnmark", 69.75, 71.3, 21.0, 31.2),
    ("Norway: Oslofjord and the south-east", 59.0, 61.0, 9.0, 11.7),
    ("Sweden: Svealand (Varmland to Uppland)", 59.0, 61.6, 11.9, 19.3),
    ("Aland and south-west Finland", 59.7, 61.9, 19.3, 23.5),
    ("Estonia: north coast", 59.0, 59.7, 21.7, 28.2),
    ("Finland: south", 59.7, 61.9, 23.5, 27.8),
    ("Finland: south", 60.55, 61.9, 27.8, 28.6),
    ("Russia: St Petersburg and the Gulf of Finland", 59.0, 61.2, 27.8, 32.0),
    ("Gulf of Bothnia side of Sweden and Finland", 61.6, 66.0, 16.5, 26.5),
    ("Kola Peninsula (Murmansk coast)", 66.2, 69.95, 30.8, 41.5),
    ("Alaska: St Matthew Island (Bering Sea)", 60.2, 60.7, -173.3, -172.0),
    ("Alaska: Gulf coast (Kenai to Yakutat)", 59.0, 61.3, -150.5, -138.5),
    ("Kamchatka and the Koryak coast", 59.0, 62.5, 159.0, 172.0),
    ("Magadan coast (Sea of Okhotsk)", 59.0, 60.3, 147.0, 156.0),
]

# (place, lat, lon, expected name): coordinates that are not in doubt; main() stops if a box no longer names them.
LABEL_CHECKS = [
    ("Lerwick", 60.15, -1.15, "Shetland"),
    ("Torshavn", 62.01, -6.77, "Faroe Islands"),
    ("Reykjavik", 64.15, -21.94, "Iceland"),
    ("Bergen", 60.39, 5.32, "Norway: Vestland"),
    ("Alesund", 62.47, 6.15, "Norway: More og Romsdal"),
    ("Bodo", 67.28, 14.40, "Norway: Nordland"),
    ("Tromso", 69.65, 18.96, "Norway: Troms"),
    ("Murmansk", 68.97, 33.08, "Kola Peninsula (Murmansk coast)"),
    ("Tallinn", 59.44, 24.75, "Estonia: north coast"),
    ("Yakutat", 59.55, -139.73, "Alaska: Gulf coast (Kenai to Yakutat)"),
]


def region(lat: float, lon: float) -> str:
    """A plain name for a point: this script's finer boxes first, else the project's own region name."""
    for name, south, north, west, east in BOXES:
        if south <= lat <= north and west <= lon <= east:
            return name
    return regions.region(lat, lon)


def bare_km2(cell: dict) -> float:
    """Bare ground in the square: its area on the ellipsoid times land share times bare share (as in the cells file)."""
    return rock_south.cell_area_km2(cell["id"]) * cell["land_share"] * cell["bare"]


def bare_samples(cell: dict) -> int:
    """How many samples of the land-cover reading were bare, if every sample of the square was mapped.

    The land-cover file was read at 12 samples per 0.1 degree (one 10 m pixel about every 900 m
    north to south), so a square's bare share is a count of a few hundred samples at most.
    """
    south = float(cell["id"].split("_")[0])
    samples = landcover.PX_PER_CELL ** 2 * grid.lon_factor(south)
    return int(round(cell["bare"] * cell["land_share"] * samples))


def hidden_squares(north: list[dict], floor_km2: float) -> list[dict]:
    """The land squares the bare-ground screen leaves out that still hold at least floor_km2 of bare ground.

    north is the land-cover file. Copies are returned, each with its bare_km2.
    """
    found = []
    for cell in north:
        if 0.0 < cell["bare"] < MIN_BARE:
            km2 = bare_km2(cell)
            if km2 >= floor_km2:
                found.append({**cell, "bare_km2": km2})
    return found


def rest_of_land(cell: dict) -> dict:
    """What covers the land that is not bare, as far as the land-cover file says (it keeps lichen and ice only)."""
    lichen, ice = cell.get("lichen") or 0.0, cell.get("ice") or 0.0
    return {"lichen_and_moss": round(lichen, 4), "ice_and_snow": round(ice, 4),
            "other_cover_not_split_in_the_file": round(1.0 - cell["bare"] - lichen - ice, 4)}


def bin_start_label(b: int) -> str:
    """The first day of a ten-day period, such as "28 Sep"."""
    return sun.doy_to_label(b * sun.BIN_DAYS + 1)


def archive_written() -> str:
    return written_at(SNOW)


def built_with() -> dict:
    """The inputs this run rests on, so a reader can tell whether the file still goes with the cells file.

    The hidden squares get their hours from the Sun code as loaded; the screened squares are read
    from grazing_cells.json. If the Sun code is newer than that file the two sides of the
    comparison were not made by the same code, and same_code is false until both are built again.
    """
    cells_written = written_at(SCREENED)
    return {"grazing_cells_written": cells_written, "sun_code_modified": SUN_CODE_READ,
            "same_code": SUN_CODE_READ <= cells_written, "year_phases": YEAR_PHASES.get("year_phases", 1)}


def sun_table(cells: list[dict], targets: list[dict]) -> tuple[list[float], np.ndarray]:
    """The latitudes of the cells and the pipeline's long-spell Sun table for them, [targets, latitudes, ...]."""
    lats = sorted({c["lat"] for c in cells})
    return lats, sun.long_band_minutes_table(lats, [t["limit_deg"] for t in targets], grazing.STRETCH_MIN_H,
                                             grazing.STEP_MINUTES, **YEAR_PHASES)


def south_share(minutes, bins, lat_of_cell, odds, keep_bins) -> np.ndarray:
    """Share of the counted snow-free long-spell hours with the Sun within 90 degrees of south, per cell.

    Each ten-day bin's minutes are weighted by its snow-free odds, then grazing.poleward_share
    gives the share on the north side; this is one minus it. NaN where there are no such hours.
    """
    weight = np.where(np.isfinite(odds), odds, 0.0)
    out = np.full(len(lat_of_cell), np.nan)
    for start in range(0, len(lat_of_cell), SOUTH_BATCH):
        rows = slice(start, start + SOUTH_BATCH)
        weighted = minutes[lat_of_cell[rows]] * weight[rows][:, :, None, None]
        out[rows] = 1.0 - np.atleast_1d(grazing.poleward_share(weighted, bins, keep_bins, "N"))
    return out


def hours(cells: list[dict], targets: list[dict], snow_of: dict, shares: dict, table=None) -> dict:
    """Long-spell hours of northern cells per target: winter half and whole year; flat, snow-free and after terrain.

    snow_of is what grazing.snow_of_cells returns, shares the open shares by cell number as
    grazing.horizons_of_cells returns them (cells without one get NaN after terrain). The hours
    per ten-day bin come from grazing.hours_by_bin on the pipeline's long-spell Sun table, the
    sums from grazing.total with the pipeline's winter bins, so a square that is also in
    grazing_cells.json gets the figures that file holds. Returns {target id: {name: array [cells]}}.
    """
    lats, long_minutes = sun_table(cells, targets) if table is None else table
    place = {lat: k for k, lat in enumerate(lats)}
    lat_of_cell = np.array([place[c["lat"]] for c in cells], dtype=int)
    north = np.ones(len(cells), dtype=bool)
    winter = grazing.bin_mask(grazing.WINTER_BINS_NORTH)
    out = {}
    for t, target in enumerate(targets):
        by_bin = grazing.hours_by_bin(long_minutes[t], target["elev_bins"], lat_of_cell, north, snow_of["odds"], shares)
        out[target["id"]] = {
            "winter_flat": grazing.total(by_bin["flat"], grazing.WINTER_BINS_NORTH),
            "winter_snow_free": grazing.total(by_bin["snow_free"], grazing.WINTER_BINS_NORTH),
            "winter_open": grazing.total(by_bin["open"], grazing.WINTER_BINS_NORTH),
            "year_flat": grazing.total(by_bin["flat"]),
            "year_snow_free": grazing.total(by_bin["snow_free"]),
            "year_open": grazing.total(by_bin["open"]),
            "south_share_winter": south_share(long_minutes[t], target["elev_bins"], lat_of_cell, snow_of["odds"], winter),
            "by_bin_snow_free": by_bin["snow_free"],
        }
    return out


def check_against_cells_file(stored_cells: list[dict], targets: list[dict], archive, count: int = CHECK_CELLS) -> dict:
    """Work out the hours of screened squares again with this script and hold them against grazing_cells.json.

    Takes the count measured gridded northern cells with the most winter hours for the last target
    and compares winter and whole-year snow-free hours and whole-year flat hours for every target.
    If they agree, the hidden squares (worked out here) and the screened squares (read from the
    file) were made by the same Sun code and snow odds; file times alone cannot show that.
    """
    key = targets[-1]["id"]
    pool = [c for c in stored_cells if c["gridded"] and c["hemisphere"] == "N" and c["snow"]["status"] == "measured"]
    pool.sort(key=lambda c: -(c["targets"][key]["long_snow_free_hours_winter"] or 0.0))
    cells = pool[:count]
    got = hours(cells, targets, grazing.snow_of_cells(cells, archive), {})
    pairs = (("winter_snow_free", "long_snow_free_hours_winter"), ("year_snow_free", "long_snow_free_hours"),
             ("year_flat", "long_flat_hours"))
    worst, compared = 0.0, 0
    for target in targets:
        for name, field in pairs:
            for k, cell in enumerate(cells):
                want, mine = cell["targets"][target["id"]][field], float(got[target["id"]][name][k])
                if want is not None and np.isfinite(mine):
                    worst, compared = max(worst, abs(mine - want)), compared + 1
    return {"cells": len(cells), "figures_compared": compared, "largest_difference_h": round(worst, 3),
            "tolerance_h": CHECK_TOLERANCE_H, "agrees": bool(compared > 0 and worst <= CHECK_TOLERANCE_H)}


def most_winter_hours(per_target: dict) -> np.ndarray:
    """Each cell's winter hours on snow-free ground for the target that has most; NaN where no target is known."""
    stacked = np.stack([np.asarray(values["winter_snow_free"], dtype=float) for values in per_target.values()])
    return np.fmax.reduce(stacked, axis=0)


def top_squares(cells: list[dict], best: np.ndarray, count: int) -> list[dict]:
    """The count cells with the most winter hours, best first; cells with unknown or no hours are never taken."""
    best = np.asarray(best, dtype=float)
    order = [int(i) for i in np.argsort(-np.where(np.isfinite(best), best, -1.0), kind="stable")
             if np.isfinite(best[i]) and best[i] > 0.0]
    return [cells[i] for i in order[:count]]


def squares_for_horizon(cells: list[dict], best: np.ndarray) -> list[dict]:
    """The TOP_HORIZONS squares at the main floor with the most winter hours, and every rim square with hours."""
    main = [i for i, c in enumerate(cells) if c["bare_km2"] >= FLOOR_KM2]
    chosen = top_squares([cells[i] for i in main], np.asarray(best)[main], TOP_HORIZONS)
    taken = {c["id"] for c in chosen}
    rim = [i for i, c in enumerate(cells) if c["id"] not in taken and region(c["lat"], c["lon"]) in RIM]
    return chosen + top_squares([cells[i] for i in rim], np.asarray(best)[rim], len(rim))


def compute_horizons(cells: list[dict], stored: dict, downloads: bool = True, save=None) -> tuple[dict, dict]:
    """Terrain horizon records by cell id, made exactly as build_horizon_cells.py makes them, and what was fetched.

    stored holds records from an earlier run; those at the same pixel size are kept. Tiles are
    fetched first by the project's own fetch code (a few at a time, failed ones asked for again),
    then the cells are worked out in worker processes that may only read tiles already on disk.
    A cell that needs a tile that could not be fetched is stored as skipped, never read as sea.
    """
    done = {c["id"]: stored[c["id"]] for c in cells if c["id"] in stored}
    todo = [c for c in cells if horizon_build.needs_horizon(done.get(c["id"]), horizon_build.PIXEL_M)]
    tiles = {}
    for cell in todo:
        urls, refused = horizon_build.tile_urls(cell)
        if refused is None:
            tiles[cell["id"]] = urls
        else:
            done[cell["id"]] = {"skipped": refused}
    every_url = sorted({url for urls in tiles.values() for url in urls})
    states = [horizon_build.tile_state(url, earth.GLO90_DIR) for url in every_url]
    log = {"cells_wanted": len(cells), "cells_reused": len(cells) - len(todo), "tiles_needed": len(every_url),
           "tiles_new": states.count("new"), "tiles_fetched": 0, "bytes_fetched": 0, "tiles_ocean_404": 0,
           "tiles_failed": 0, "downloads": downloads}
    print(f"horizons wanted: {len(cells)}; reused: {log['cells_reused']}; tiles needed: {len(every_url)} "
          f"(new {log['tiles_new']})", flush=True)
    if downloads:
        failures = {}
        for attempt in range(1, FETCH_ROUNDS + 1):
            fetched = horizon_build.fetch_tiles(every_url, earth.GLO90_DIR)
            log["tiles_fetched"] += fetched["fetched"]
            log["bytes_fetched"] += fetched["bytes"]
            log["tiles_ocean_404"] += fetched["ocean"]
            failures = fetched["failures"]
            print(f"  fetch round {attempt}: asked {fetched['asked']}, fetched {fetched['fetched']} "
                  f"({fetched['bytes'] / 1e6:.1f} MB), ocean {fetched['ocean']}, failed {len(failures)}", flush=True)
            if not failures:
                break
            time.sleep(20 * attempt)
        log["tiles_failed"] = len(failures)
        held = horizon_build.held_back(tiles, failures)
    else:
        held = horizon_build.without_new_tiles(tiles, earth.GLO90_DIR)
    for cid, reason in held.items():
        done[cid] = {"skipped": reason}
    todo = [c for c in todo if c["id"] in tiles and c["id"] not in held]
    started = time.perf_counter()
    with ProcessPoolExecutor(max_workers=PROCESSES, initializer=horizon_build.no_downloads) as pool:
        for count, (cid, result, _) in enumerate(pool.map(horizon_build.compute, todo, chunksize=2), start=1):
            done[cid] = result
            if count % 50 == 0:
                print(f"  {count} of {len(todo)} horizons, {time.perf_counter() - started:.0f} s", flush=True)
                if save is not None:
                    save(done)
    log["cells_computed_now"] = len(todo)
    log["cells_held_back"] = len(held)
    return done, log


def horizon_shares(cells: list[dict], horizons: dict) -> tuple[list, dict]:
    """Horizon summaries and open shares by cell number, read by the pipeline's own grazing.horizons_of_cells."""
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "horizons.json"
        path.write_text(json.dumps(horizons))
        return grazing.horizons_of_cells(cells, path)


def lead_record(cell: dict, snow_summary: dict, horizon_summary, values: dict, floor_km2: float = FLOOR_KM2) -> dict:
    """One square for one target as it is written. Unknown is None, never 0."""
    record = {
        "id": cell["id"], "lat": cell["lat"], "lon": cell["lon"], "region": region(cell["lat"], cell["lon"]),
        "land_share": round(cell["land_share"], 3), "bare": round(cell["bare"], 4),
        "bare_km2": round(cell["bare_km2"], 2), "bare_samples": bare_samples(cell),
        "at_main_floor": bool(cell["bare_km2"] >= floor_km2), "rest_of_land": rest_of_land(cell),
        "snow": snow_summary,
        "winter_hours_flat": known(values["winter_flat"]),
        "winter_hours_snow_free": known(values["winter_snow_free"]),
        "winter_hours_after_terrain": known(values["winter_open"]),
        "year_hours_flat": known(values["year_flat"]),
        "year_hours_snow_free": known(values["year_snow_free"]),
        "year_hours_after_terrain": known(values["year_open"]),
        "horizon": horizon_summary,
        "best_ten_day_periods": [{"bin": b, "starts": bin_start_label(b), "hours": h} for b, h in values["best_periods"]],
        "south_share_winter": known(values["south_share_winter"], 3),
    }
    return record


def counts_by_region(leads: list[dict], field: str, status: str = "measured", thresholds=THRESHOLDS) -> dict:
    """How many squares of one snow status reach each threshold in the given hours field, by region name."""
    out = {}
    for limit in thresholds:
        found: dict[str, int] = {}
        for lead in leads:
            value = lead.get(field)
            if lead["snow"]["status"] == status and value is not None and value >= limit:
                found[lead["region"]] = found.get(lead["region"], 0) + 1
        out[str(limit)] = dict(sorted(found.items()))
    return out


def floor_table(cells: list[dict], statuses: list[str], per_target: dict) -> dict:
    """How the count of leads changes with the floor: squares and, per target, measured squares at each threshold."""
    km2 = np.array([c["bare_km2"] for c in cells])
    measured = np.array([s == "measured" for s in statuses])
    doubtful = np.array([s == "doubtful" for s in statuses])
    out = {}
    for floor in FLOORS_KM2:
        at = km2 >= floor
        row = {"squares": int(at.sum()), "measured": int((at & measured).sum()), "doubtful": int((at & doubtful).sum()),
               "no_snow_data": int((at & ~measured & ~doubtful).sum()), "targets": {}}
        for tid, values in per_target.items():
            winter = np.asarray(values["winter_snow_free"], dtype=float)
            with np.errstate(invalid="ignore"):
                row["targets"][tid] = {
                    **{str(limit): int((at & measured & (winter >= limit)).sum()) for limit in FLOOR_THRESHOLDS},
                    "unknown_hours": int((at & measured & ~np.isfinite(winter)).sum()),
                    "doubtful_50": int((at & doubtful & (winter >= THRESHOLDS[0])).sum())}
        out[str(float(floor))] = row
    return out


def screened_counts(stored_cells: list[dict], target_id: str) -> dict:
    """The same counts for the squares that pass the screen: measured gridded northern cells of grazing_cells.json."""
    rows = [{"region": region(c["lat"], c["lon"]), "snow": c["snow"],
             "flat": c["targets"][target_id]["long_snow_free_hours_winter"],
             "terrain": c["targets"][target_id]["long_open_hours_winter"]}
            for c in stored_cells if c["gridded"] and c["hemisphere"] == "N"]
    return {"snow_free": counts_by_region(rows, "flat"), "after_terrain": counts_by_region(rows, "terrain")}


def rim_summary(north: list[dict]) -> dict:
    """What the land-cover file holds of each rim region: land squares, and how much bare ground the screen hides."""
    out = {name: {"land_squares": 0, "pass_the_screen": 0, "below_the_screen_with_a_bare_sample": 0,
                  "of_them_at_the_main_floor": 0, "their_bare_km2": 0.0} for name in RIM}
    for cell in north:
        row = out.get(region(cell["lat"], cell["lon"]))
        if row is None:
            continue
        row["land_squares"] += 1
        if cell["bare"] >= MIN_BARE:
            row["pass_the_screen"] += 1
        elif cell["bare"] > 0.0:
            km2 = bare_km2(cell)
            row["below_the_screen_with_a_bare_sample"] += 1
            row["of_them_at_the_main_floor"] += int(km2 >= FLOOR_KM2)
            row["their_bare_km2"] += km2
    for row in out.values():
        row["their_bare_km2"] = round(row["their_bare_km2"], 2)
    return out


def write_json(path: Path, value) -> None:
    side = path.with_name(path.name + ".part")
    side.write_text(json.dumps(value, separators=(",", ":")))
    os.replace(side, path)


def check_labels() -> list[dict]:
    checks = []
    for place, lat, lon, expected in LABEL_CHECKS:
        got = region(lat, lon)
        if got != expected:
            raise ValueError(f"region box check failed: {place} at {lat}, {lon} is named {got!r}, not {expected!r}")
        checks.append({"place": place, "lat": lat, "lon": lon, "named": got})
    return checks


WARNINGS = [
    "Snow-free odds at a coast rest on few land pixels of the 4 km snow maps: see snow.land_pixels of snow.block_pixels "
    "for each lead. Squares with snow status 'doubtful' use the lower odds of the stale-flag rule and are counted apart.",
    "No cloud is taken into account. The Atlantic rim is very cloudy in winter; these are hours of Sun geometry on "
    "ground that is probably free of snow, not hours of visible Sun.",
    "WorldCover's bare class at a coast can be beach, tidal flat, rock, a quarry or other worked ground. What the bare "
    "ground of a lead is was not looked at.",
    "The land-cover file is a sample: one 10 m pixel about every 900 m (12 samples per 0.1 degree). South of 64.5 N one "
    "bare sample stands for about 0.4 km2, so the 0.25 km2 floor means one bare sample, 1 km2 means three or more and "
    "3 km2 seven or more; bare_km2 of a lead with few samples (bare_samples) is uncertain by about its own size, and a "
    "square with bare ground between the samples reads as having none.",
    "Squares with less than 20 percent land were left out when the land-cover file was built, so small islands and "
    "skerries are not here at all.",
    "The terrain horizon was computed only for the squares named in meta.horizon; winter_hours_after_terrain is null "
    "elsewhere and the counts after terrain cover only squares that have a horizon.",
    "Hours after terrain are an average over all the land of a square (the share of its land that sees the Sun), not "
    "over its bare ground. A bare summit or headland can see more of a low southern Sun than that average, a quarry "
    "or beach under a hill less.",
    "The winter half runs from 28 September to 31 March. North of about 67 N the hours counted here fall in October "
    "and March, not in midwinter.",
    "Region names come from rough latitude and longitude boxes (first match wins); a square near a border can carry "
    "its neighbour's name.",
    "Hours are for a 365-day year with standard refraction, a 2 h minimum spell and 1-minute steps, as in the "
    "pipeline; the limits listed in section (i) of RESULTS.md apply here too.",
]


def assemble(cells, snow_of, horizons, summaries, per_target, targets, stored_cells, horizon_log, checks,
             squares: dict, rim: dict, check: dict) -> dict:
    statuses = [s["status"] for s in snow_of["summaries"]]
    winter = grazing.bin_mask(grazing.WINTER_BINS_NORTH)
    out_targets = {}
    for target in targets:
        values = per_target[target["id"]]
        listed = [i for i in np.argsort(-np.where(np.isfinite(values["winter_snow_free"]), values["winter_snow_free"], -1.0),
                                        kind="stable")
                  if np.isfinite(values["winter_snow_free"][i]) and values["winter_snow_free"][i] >= LIST_MIN_H]
        leads = []
        for i in listed:
            one = {name: values[name][i] for name in ("winter_flat", "winter_snow_free", "winter_open", "year_flat",
                                                      "year_snow_free", "year_open", "south_share_winter")}
            one["best_periods"] = grazing.top_bins(values["by_bin_snow_free"][i], winter)
            lead = lead_record(cells[i], snow_of["summaries"][i], summaries[i], one)
            if lead["winter_hours_snow_free"] >= LIST_MIN_H:   # 49.96 rounds to 50.0 and stays; 49.94 does not
                leads.append(lead)
        main = [lead for lead in leads if lead["at_main_floor"]]
        with_horizon = [lead for lead in main if lead["winter_hours_after_terrain"] is not None]
        out_targets[target["id"]] = {
            "id": target["id"], "name": target["name"], "limit_deg": target["limit_deg"],
            "leads": leads,
            "counts_by_region": counts_by_region(main, "winter_hours_snow_free"),
            "counts_by_region_after_terrain": counts_by_region(main, "winter_hours_after_terrain"),
            "counts_by_region_doubtful": counts_by_region(main, "winter_hours_snow_free", "doubtful"),
            "main_floor_leads_with_a_horizon": {
                "measured": sum(lead["snow"]["status"] == "measured" for lead in with_horizon),
                "of_measured": sum(lead["snow"]["status"] == "measured" for lead in main)},
            "screened_counts_by_region": screened_counts(stored_cells, target["id"])["snow_free"],
            "screened_counts_by_region_after_terrain": screened_counts(stored_cells, target["id"])["after_terrain"],
        }
    with_share = sum("open_share" in record for record in horizons.values())
    skipped: dict[str, int] = {}
    for record in horizons.values():
        if "skipped" in record:
            key = record["skipped"].split(":")[0]
            skipped[key] = skipped.get(key, 0) + 1
    meta = {
        "written": datetime.now().isoformat(timespec="seconds"),
        "what": "Northern land squares that the pipeline's bare-ground screen leaves out and that still hold some bare "
                "ground: long-spell low-Sun hours on snow-free ground in the winter half and the whole year.",
        "screen_relaxed": {"min_bare_of_the_pipeline": MIN_BARE,
                           "kept_here": "0 < bare share < min_bare and bare_km2 >= the floor",
                           "min_land_share_of_the_land_cover_file": 0.2},
        "floor_bare_km2": FLOOR_KM2, "floors_shown_km2": list(FLOORS_KM2),
        "floor_meaning": "counts_by_region and the terrain pass use the main floor; leads lists every square at or "
                         "above the smallest floor shown, with at_main_floor true or false",
        "list_min_winter_hours": LIST_MIN_H, "count_thresholds_h": list(THRESHOLDS),
        "winter_half": "28 September to 31 March", "winter_bins": grazing.WINTER_BINS_NORTH,
        "stretch_min_h": grazing.STRETCH_MIN_H, "step_minutes": grazing.STEP_MINUTES, "long_rule": grazing.LONG_RULE,
        "targets": targets,
        "snow_archive": SNOW.name, "snow_archive_written": archive_written(), "built_with": {**built_with(), "check_against_cells_file": check},
        "snow_odds_rule": "as in grazing_cells.json: measured squares use the odds as mapped, doubtful squares the "
                          "odds with the stale-flag rule; counts are over measured squares, doubtful ones apart",
        "squares": squares,
        "rim": {"what": "Shetland, Orkney and the Faroe Islands in the land-cover file (squares with at least 20 "
                        "percent land): how many squares, and how much bare ground the screen hides there",
                **rim},
        "horizon": {"pixel_m": horizon_build.PIXEL_M, "half_km": horizon_build.HALF_KM, "reach_km": horizon_build.REACH_KM,
                    "chosen": f"the {TOP_HORIZONS} squares at the main floor with the most winter hours on snow-free "
                              f"ground for any target, and every square of {', '.join(RIM)} at any floor shown",
                    "wanted": len(horizons), "with_a_horizon": with_share, "skipped": skipped, "run": horizon_log},
        "computed": [
            f"long-spell hours over a flat horizon, winter half and whole year, {len(targets)} targets, every square at "
            "or above the smallest floor",
            "the same on snow-free ground (ten-day snow-free odds of the 4 km snow maps) with snow status and pixels",
            "the same after terrain for the squares of meta.horizon",
            "share of the winter snow-free hours with the Sun within 90 degrees of south",
            "counts by region at 50 and 100 winter hours, and the same counts for the screened squares",
        ],
        "not_computed": [
            "cloud", "what the bare ground is (beach, tidal flat, rock, quarry)", "access, ownership, permits",
            "terrain for squares outside meta.horizon", "squares with less than 20 percent land",
            "slope and the other scores of cells_scored.json",
        ],
        "warnings": WARNINGS + ([] if check["agrees"] else [
            "THE HIDDEN AND THE SCREENED SQUARES DO NOT GO TOGETHER: hours worked out here for screened squares differ "
            "from grazing_cells.json (meta.built_with.check_against_cells_file). Build the cells file again, then "
            "this file."]),
        "label_checks": checks,
        "fields": {
            "winter_hours_flat": "long-spell hours, 28 September to 31 March, flat horizon, no snow",
            "winter_hours_snow_free": "the same times the snow-free odds of each ten-day period",
            "winter_hours_after_terrain": "the same counted only where the terrain horizon of the square leaves the "
                                          "Sun in view (share of the square's land); null where no horizon was computed",
            "bare_samples": "bare samples of the land-cover reading behind bare_km2, if every sample was mapped",
            "south_share_winter": "share of winter_hours_snow_free with the Sun within 90 degrees of south",
            "best_ten_day_periods": "the three ten-day periods of the winter half with the most snow-free hours",
        },
    }
    return {"meta": meta, "floors": floor_table(cells, statuses, per_target), "targets": out_targets,
            "horizons": horizons}


def main(downloads: bool = True) -> None:
    started = time.perf_counter()
    grazing.check_shared_bins()
    if not built_with()["same_code"]:
        print(f"WARNING: twinfinder/sun.py ({SUN_CODE_READ}) is newer than {SCREENED} "
              f"({built_with()['grazing_cells_written']}): the hidden squares get hours from the new Sun code, the "
              f"screened squares from the old file. Build the cells file again, then run this script again.", flush=True)
    checks = check_labels()
    targets = grazing.load_targets()
    north = json.loads(NORTH.read_text())
    stored = json.loads(SCREENED.read_text())
    stored_cells = stored["cells"]
    stored_ids = {c["id"] for c in stored_cells}
    cells = hidden_squares(north, min(FLOORS_KM2))
    squares = {"northern_land_squares_in_the_land_cover_file": len(north),
               "below_the_screen": sum(c["bare"] < MIN_BARE for c in north),
               "below_the_screen_with_no_bare_sample": sum(c["bare"] == 0.0 for c in north),
               "below_the_screen_with_a_bare_sample": sum(0.0 < c["bare"] < MIN_BARE for c in north),
               "at_or_above_the_smallest_floor": len(cells),
               "of_them_already_in_grazing_cells_json_as_named_sites": sum(c["id"] in stored_ids for c in cells)}
    print(f"squares: {json.dumps(squares)}", flush=True)

    archive = np.load(SNOW)
    check = check_against_cells_file(stored_cells, targets, archive)
    print(f"check against {SCREENED}: {json.dumps(check)}", flush=True)
    if not check["agrees"]:
        print("WARNING: the hours of screened squares worked out here differ from the cells file; the comparison of "
              "hidden and screened squares is not like with like until that file is built again.", flush=True)
    snow_of = grazing.snow_of_cells(cells, archive)
    table = sun_table(cells, targets)
    first = hours(cells, targets, snow_of, {}, table)
    best = most_winter_hours(first)
    wanted = squares_for_horizon(cells, best)
    print(f"flat pass done, {time.perf_counter() - started:.0f} s; squares for a horizon: {len(wanted)}", flush=True)

    previous = json.loads(OUT.read_text()) if OUT.exists() else {}
    kept = previous.get("horizons", {})

    def save(done: dict) -> None:
        if previous:   # keep the file valid while the terrain pass runs: only the horizon store grows
            write_json(OUT, {**previous, "horizons": {**kept, **done}})

    horizons, horizon_log = compute_horizons(wanted, kept, downloads, save)
    summaries, shares = horizon_shares(cells, horizons)
    per_target = hours(cells, targets, snow_of, shares, table)
    output = assemble(cells, snow_of, horizons, summaries, per_target, targets, stored_cells, horizon_log, checks,
                      squares, rim_summary(north), check)
    write_json(OUT, output)

    for floor, row in output["floors"].items():
        print(f"floor {floor} km2: {row['squares']} squares ({row['measured']} measured); measured with >= 50 / 100 / 200 "
              f"winter hours: " + "; ".join(f"{tid} {v['50']} / {v['100']} / {v['200']}" for tid, v in row["targets"].items()))
    for tid, target in output["targets"].items():
        print(f"{tid}: leads listed {len(target['leads'])}")
        for limit in ("50", "100"):
            print(f"  >= {limit} h hidden by the screen (floor {FLOOR_KM2} km2): {json.dumps(target['counts_by_region'][limit])}")
            print(f"  >= {limit} h after terrain: {json.dumps(target['counts_by_region_after_terrain'][limit])}")
            print(f"  >= {limit} h screened squares: {json.dumps(target['screened_counts_by_region'][limit])}")
    print(f"horizons: {json.dumps(output['meta']['horizon']['run'])}; skipped: {output['meta']['horizon']['skipped']}")
    print(f"wrote {OUT}; whole run {time.perf_counter() - started:.0f} s")


if __name__ == "__main__":
    unknown = [argument for argument in sys.argv[1:] if argument != "--cached-only"]
    if unknown:
        sys.exit(f"unknown argument: {unknown[0]} (the only one is --cached-only)")
    main(downloads="--cached-only" not in sys.argv[1:])

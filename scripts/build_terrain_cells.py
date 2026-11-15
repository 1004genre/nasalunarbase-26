# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Slope statistics and lunar-terrain overlap for candidate cells. Writes data/derived/terrain_cells.json.

The cells are the records of data/derived/candidates.json (since version 3: every cell). The cells
that must have terrain come first: every cell bare enough to be ranked (bare at least 0.25, north
or south) and every named site; the other cells follow, or are left alone with --must-only.

All elevation and water-mask tiles are fetched first, six at a time, and only then are the cells
worked out in several processes. A tile the server does not have (404) is ocean. Any other failed
download is reported and the cells that need that tile are held back, as in build_horizon_cells.py.

    uv run python scripts/build_terrain_cells.py                  every cell, downloading what is missing
    uv run python scripts/build_terrain_cells.py --must-only      only the cells that must have terrain
    uv run python scripts/build_terrain_cells.py --cached-only    asks the server for nothing; cells that need a
                                                                  tile that is not on disk are held back
    uv run python scripts/build_terrain_cells.py --processes 3    fewer processes (8 unless told otherwise)

Safe to run again: only cells without numbers are worked out, progress is saved every 200 cells,
and the file is always written beside the old one and renamed into place.
"""
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

from twinfinder import earth, terrain

try:                                             # imported by the tests as part of the scripts folder
    from scripts import build_horizon_cells as tiles
except ImportError:                              # started as a script: the sister script is next to this one
    import build_horizon_cells as tiles

CANDIDATES = Path("data/derived/candidates.json")
TARGETS = Path("data/derived/moon_targets.json")
OUT = Path("data/derived/terrain_cells.json")
MIN_SLOPE_PIXELS = 500   # fewer land pixels with a slope than this is too little to describe a cell
HALF_KM = 5.0
MUST_MIN_BARE = 0.25     # as score.RANK_MIN_BARE: a cell with less bare ground is never ranked
DOWNLOADS_AT_ONCE = 6    # polite to the tile server
PROCESSES = 8
SAVE_EVERY = 200
FAILED = "failed"

_TARGET_HISTS: dict = {}


def _init(target_hists: dict, cached_only: bool = False) -> None:
    """Run once in every worker: the lunar slope histograms, and no downloads in a cached-only run."""
    global _TARGET_HISTS
    _TARGET_HISTS = target_hists
    if cached_only:
        tiles.no_downloads()


def needs_terrain(stored: dict | None, modelled: tuple = ()) -> bool:
    """True for a cell with no stored result, or one stored without terrain and without a pixel count.

    A record with "overlap" has its numbers; one with "slope_pixels" alone has too little land,
    which is settled. Everything else (a refused window, a tile that was not fetched, a failure)
    is tried again; a refused window costs nothing to refuse again. A record whose overlap lacks
    one of the modelled lunar regions (ids in modelled) is also worked out again.
    """
    if stored is None or ("overlap" not in stored and "slope_pixels" not in stored):
        return True
    return "overlap" in stored and any(tid not in stored["overlap"] for tid in modelled)


def tile_urls(cell: dict) -> list[str]:
    """Elevation and water-mask tiles for a cell's window; none when the window is refused."""
    try:
        return [u for product in ("DEM", "WBM")
                for u in earth.tiles_for_window(cell["lat"], cell["lon"], HALF_KM, product)]
    except ValueError:
        return []  # summarise records the reason


def must_have(candidate: dict) -> bool:
    """True for a cell that can be ranked on its bare ground (north or south) and for every named site."""
    bare = candidate.get("bare")
    named = any(reason.startswith("named: ") for reason in candidate.get("why", []))
    return named or (bare is not None and bare >= MUST_MIN_BARE)


def work_order(cells: list[dict]) -> list[dict]:
    """The cells that must have terrain first, then the rest; inside each group the order of the file."""
    return [c for c in cells if must_have(c)] + [c for c in cells if not must_have(c)]


def summarise(cell: dict) -> tuple[str, dict, float]:
    """One cell in a worker process: its id, its record and the seconds it took."""
    started = time.perf_counter()
    try:
        result = slope_record(earth.elevation_window(cell["lat"], cell["lon"], HALF_KM))
    except ValueError as error:   # a window across the antimeridian or over a pole
        result = {"skipped": str(error)}
    except Exception as error:    # one bad cell must not lose the run; it is tried again next time
        result = {"skipped": f"{FAILED}: {type(error).__name__}: {error}"}
    return cell["id"], result, time.perf_counter() - started


def slope_record(z: np.ndarray) -> dict:
    """What is stored for one cell from its elevation window (90 m pixels, NaN on water and where there is no tile)."""
    slope_pixels = int(np.isfinite(terrain.slope_deg(z, 90.0)).sum())
    result = {"valid_share": round(float(np.isfinite(z).mean()), 3), "slope_pixels": slope_pixels}
    if slope_pixels < MIN_SLOPE_PIXELS:
        return result
    summary = terrain.terrain_summary(z, 90.0)
    hist = np.array(summary["slope_hist"])
    result.update({
        "median_slope_deg": round(summary["median_slope_deg"], 2),
        "p90_slope_deg": round(summary["p90_slope_deg"], 2),
        "relief_m": round(summary["relief_m"], 1),
        "overlap": {tid: round(terrain.histogram_overlap(hist, np.array(h)), 3)
                    for tid, h in _TARGET_HISTS.items()},
    })
    return result


def write_json(path: Path, value) -> None:
    side = path.with_name(path.name + ".part")
    side.write_text(json.dumps(value, separators=(",", ":")))
    os.replace(side, path)


def summary_line(done: dict, wanted: list[dict]) -> str:
    """Counts over the candidates: cells with terrain numbers, with too little land, and the skipped ones by reason."""
    reasons: dict[str, int] = {}
    with_terrain = too_little = missing = 0
    for cell in wanted:
        stored = done.get(cell["id"])
        if stored is None:
            missing += 1
        elif "overlap" in stored:
            with_terrain += 1
        elif "slope_pixels" in stored:
            too_little += 1
        else:
            reason = stored.get("skipped", "no reason stored")
            key = ("crosses the antimeridian" if "antimeridian" in reason else
                   next((prefix for prefix in (tiles.NOT_FETCHED, FAILED) if reason.startswith(prefix)), reason))
            reasons[key] = reasons.get(key, 0) + 1
    return (f"candidates: {len(wanted)}; with terrain: {with_terrain}; under {MIN_SLOPE_PIXELS} slope pixels: "
            f"{too_little}; skipped: {json.dumps(reasons)}; not in the file: {missing}")


def main(cached_only: bool = False, must_only: bool = False, processes: int = PROCESSES) -> None:
    started = time.perf_counter()
    # Only a region with a NASA 5 m terrain model has a slope histogram; the others get no overlap (unknown).
    target_hists = {t["id"]: t["terrain"]["90m"]["slope_hist"] for t in json.loads(TARGETS.read_text())
                    if t.get("terrain") is not None}
    done = json.loads(OUT.read_text()) if OUT.exists() else {}
    wanted = json.loads(CANDIDATES.read_text())
    chosen = [c for c in wanted if must_have(c)] if must_only else wanted
    todo = work_order([c for c in chosen if needs_terrain(done.get(c["id"]), tuple(target_hists))])
    print(f"candidates: {len(wanted)} ({CANDIDATES}); must have terrain: {sum(must_have(c) for c in wanted)}; "
          f"in this run: {len(chosen)}; already done: {len(chosen) - len(todo)}; to do: {len(todo)}")

    needed = {c["id"]: tile_urls(c) for c in todo}
    every_url = sorted({url for urls in needed.values() for url in urls})
    states = [tiles.tile_state(url, earth.GLO90_DIR) for url in every_url]
    print(f"tiles needed: {len(every_url)} (cached {states.count('cached')}, known ocean {states.count('ocean')}, "
          f"new {states.count('new')})")
    failures: dict[str, str] = {}
    if cached_only:
        held = tiles.without_new_tiles(needed, earth.GLO90_DIR)
        print(f"DOWNLOADS ARE OFF (--cached-only): no tile is asked for; cells held back: {len(held)}; "
              f"run again without --cached-only to fetch their tiles")
    else:
        fetch_started = time.perf_counter()
        fetched = tiles.fetch_tiles(every_url, earth.GLO90_DIR, workers=DOWNLOADS_AT_ONCE)
        failures = fetched["failures"]
        print(f"tiles asked for: {fetched['asked']}; fetched: {fetched['fetched']} ({fetched['bytes'] / 1e6:.1f} MB); "
              f"ocean (404): {fetched['ocean']}; failed: {len(failures)}; "
              f"download time: {time.perf_counter() - fetch_started:.0f} s", flush=True)
        held = tiles.held_back(needed, failures)
        if failures:
            print(f"FAILED DOWNLOADS (run again to retry); cells held back: {len(held)}",
                  *[f"{url}: {error}" for url, error in list(failures.items())[:20]], sep="\n  ")
    for cid, reason in held.items():
        done[cid] = {"skipped": reason}
    todo = [c for c in todo if c["id"] not in held]
    write_json(OUT, done)
    print(f"cells to work out now: {len(todo)}", flush=True)

    compute_started = time.perf_counter()
    seconds = []
    with ProcessPoolExecutor(max_workers=processes, initializer=_init, initargs=(target_hists, cached_only)) as pool:
        for count, (cid, result, took) in enumerate(pool.map(summarise, todo, chunksize=4), start=1):
            done[cid] = result
            seconds.append(took)
            if count % SAVE_EVERY == 0:
                write_json(OUT, done)
                print(f"  {count} of {len(todo)} cells, {time.perf_counter() - compute_started:.0f} s", flush=True)
    write_json(OUT, done)
    if seconds:
        print(f"computed {len(seconds)} cells in {time.perf_counter() - compute_started:.0f} s with {processes} "
              f"processes; inside a worker: mean {np.mean(seconds):.3f} s, max {np.max(seconds):.2f} s per cell")
    print(summary_line(done, wanted))
    print(f"wrote {OUT}; whole run {time.perf_counter() - started:.0f} s")
    if failures:
        sys.exit(1)


def options(arguments: list[str]) -> dict:
    """The command line as the keyword arguments of main; anything it does not know stops the run."""
    found = {"cached_only": False, "must_only": False, "processes": PROCESSES}
    rest = list(arguments)
    while rest:
        argument = rest.pop(0)
        if argument == "--cached-only":
            found["cached_only"] = True
        elif argument == "--must-only":
            found["must_only"] = True
        elif argument == "--processes" and rest and rest[0].isdigit() and int(rest[0]) >= 1:
            found["processes"] = int(rest.pop(0))
        else:
            sys.exit(f"cannot read the argument {argument!r}; known: --cached-only, --must-only, --processes N (N at least 1)")
    return found


if __name__ == "__main__":
    main(**options(sys.argv[1:]))

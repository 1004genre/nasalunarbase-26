# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Terrain horizon of every candidate cell: how much of the cell sees a low Sun in each direction.

Writes data/derived/horizon_cells.json, one record per cell of
data/derived/candidates.json (since version 3: every cell). All elevation and
water-mask tiles are fetched first, a few at a time, and only then are the
cells worked out in several processes (two processes asking for the same tile
would write the same file). A tile the server does not have (404) is ocean.
Any other failed download is reported, and the cells that need that tile are
held back: a missing land tile read as sea would make the horizon too open.

Order of work: named sites, samples, rock and doubtful cells, then the top
lists, then the cells that are in for the census alone: northern cells that
can be ranked (measured snow, bare at least 0.25), other northern cells, the
south.

    uv run python scripts/build_horizon_cells.py                 downloads what is missing (up to BUDGET_BYTES)
    uv run python scripts/build_horizon_cells.py --cached-only   asks the server for nothing: works out the cells
                                                                 whose tiles are all on disk and holds back the rest

Safe to run again: cells already stored at the same pixel size are skipped,
progress is saved every few hundred cells, and the file is always written
beside the old one and renamed into place. A cell held back by a cached-only
run is taken up again by the next run that may download.
"""
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from pathlib import Path

import numpy as np

from twinfinder import candidates, earth, horizon
from twinfinder.fetch import fetch_optional

CANDIDATES = Path("data/derived/candidates.json")
OUT = Path("data/derived/horizon_cells.json")
PIXEL_M = 60.0             # the 90 m grid reads horizons 0.1 to 0.9 degrees low; 60 m closes most of that gap
HALF_KM, REACH_KM = 5.0, 25.0
DOWNLOADS_AT_ONCE = 6      # polite to the tile server
PROCESSES = 8
SAVE_EVERY = 200
BUDGET_BYTES = 8e9         # new downloads allowed in one run
DEFAULT_TILE_BYTES = {"DEM": 1.3e6, "WBM": 2.0e4}   # used only when the cache holds no tile of that kind yet
NO_LAND = "no land pixels"
# reasons that may be gone on the next run; every other skip is settled and not tried again
NOT_FETCHED = "tile not fetched"
OVER_BUDGET = "left out to keep downloads under the budget"
FAILED = "failed"
DOWNLOADS_OFF = "downloads were off in this run"
TRY_AGAIN = (NOT_FETCHED, OVER_BUDGET, FAILED)


def tile_urls(cell: dict) -> tuple[list[str], str | None]:
    """Elevation and water-mask tiles of the cell's 30 km window, or no tiles and why the window is refused."""
    try:
        return [url for product in ("DEM", "WBM")
                for url in earth.tiles_for_window(cell["lat"], cell["lon"], HALF_KM + REACH_KM, product)], None
    except ValueError as error:  # across the antimeridian or over a pole
        return [], str(error)


def tile_state(url: str, cache_dir: Path) -> str:
    """ "cached" (the file is here), "ocean" (the server said 404 before) or "new" (not asked for yet)."""
    name = url.rsplit("/", 1)[-1]
    if (Path(cache_dir) / name).exists():
        return "cached"
    return "ocean" if (Path(cache_dir) / (name + ".missing")).exists() else "new"


def product_of(url: str) -> str:
    return "WBM" if url.endswith("_WBM.tif") else "DEM"


def expected_bytes(urls: list[str], cache_dir: Path) -> dict[str, float]:
    """Bytes each tile is expected to add: 0 if cached or known ocean, else the mean size of cached tiles of its kind."""
    sizes: dict[str, list[int]] = {"DEM": [], "WBM": []}
    for path in Path(cache_dir).glob("*.tif"):
        sizes[product_of(path.name)].append(path.stat().st_size)
    mean = {kind: (sum(found) / len(found) if found else DEFAULT_TILE_BYTES[kind]) for kind, found in sizes.items()}
    return {url: (mean[product_of(url)] if tile_state(url, cache_dir) == "new" else 0) for url in urls}


def over_budget(order: list[str], tiles: dict[str, list[str]], cost: dict[str, float], budget: float) -> list[str]:
    """Cell ids to leave out, taken from order one by one, until the tiles of the remaining cells fit the budget.

    tiles lists every cell's tiles (also cells that can never be dropped). A
    tile still needed by a cell that stays goes on counting.
    """
    users: dict[str, int] = {}
    for urls in tiles.values():
        for url in urls:
            users[url] = users.get(url, 0) + 1
    total = sum(cost[url] for url in users)
    dropped = []
    for cid in order:
        if total <= budget:
            break
        dropped.append(cid)
        for url in tiles[cid]:
            users[url] -= 1
            if users[url] == 0:
                total -= cost[url]
    return dropped


def fetch_tiles(urls: list[str], cache_dir: Path, fetch_one=fetch_optional, workers: int = DOWNLOADS_AT_ONCE) -> dict:
    """Download the tiles not asked for yet, a few at a time.

    Gives {"asked", "fetched", "bytes", "ocean", "failures"}: ocean counts the
    tiles the server does not have, failures maps every other url to what went
    wrong (for example a 403, which says nothing about land or sea).
    """
    new = [url for url in urls if tile_state(url, cache_dir) == "new"]

    def one(url: str):
        try:
            return url, fetch_one(url, cache_dir), None
        except Exception as error:
            return url, None, f"{type(error).__name__}: {error}"

    result = {"asked": len(new), "fetched": 0, "bytes": 0, "ocean": 0, "failures": {}}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for url, path, error in pool.map(one, new):
            if error is not None:
                result["failures"][url] = error
            elif path is None:
                result["ocean"] += 1
            else:
                result["fetched"] += 1
                result["bytes"] += Path(path).stat().st_size
    return result


def held_back(tiles: dict[str, list[str]], failures: dict[str, str]) -> dict[str, str]:
    """The cells that need a tile whose download failed, each with the reason to store."""
    held = {}
    for cid, urls in tiles.items():
        missing = [url for url in urls if url in failures]
        if missing:
            held[cid] = f"{NOT_FETCHED}: {missing[0]} ({failures[missing[0]]})"
    return held


def cached_or_ocean(url: str, dest_dir: Path) -> Path | None:
    """Stands in for the download in a cached-only run: the tile on disk, None for known ocean, never a request.

    A tile that was never asked for is an error, so a worker cannot fetch it
    behind the back of the run (and cannot read a missing land tile as sea).
    """
    state = tile_state(url, dest_dir)
    if state == "new":
        raise RuntimeError(f"{NOT_FETCHED}: {url} ({DOWNLOADS_OFF})")
    return Path(dest_dir) / url.rsplit("/", 1)[-1] if state == "cached" else None


def no_downloads() -> None:
    """Run once in every worker of a cached-only run: the elevation code can then only read tiles already here."""
    earth.fetch_optional = cached_or_ocean


def without_new_tiles(tiles: dict[str, list[str]], cache_dir: Path) -> dict[str, str]:
    """The cells that need a tile never asked for, each with the reason to store in a cached-only run."""
    held = {}
    for cid, urls in tiles.items():
        new = [url for url in urls if tile_state(url, cache_dir) == "new"]
        if new:
            held[cid] = f"{NOT_FETCHED}: {new[0]} ({DOWNLOADS_OFF}; {len(new)} of the cell's {len(urls)} tiles are new)"
    return held


def needs_horizon(stored: dict | None, pixel_m: float) -> bool:
    """True for a cell with no result, a result at another pixel size, or a skip that may pass on a new run."""
    if stored is None:
        return True
    if "skipped" in stored:
        return stored["skipped"].startswith(TRY_AGAIN)
    return stored.get("pixel_m") != pixel_m


def number(value: float, digits: int) -> float | None:
    """A rounded number for the file, or None when it cannot be known."""
    value = float(value)
    return round(value, digits) if np.isfinite(value) else None


def record(open_share, north_deg: float, south_deg: float, valid_share: float, pixel_m: float) -> dict:
    """What is stored for one cell, from what horizon.cell_open_share returns.

    A cell with no land pixel has no open share at all; it is stored as
    skipped, so nobody reads it as a cell with zero open hours.
    """
    share = np.asarray(open_share, dtype=float)
    if not np.isfinite(share).any():
        return {"skipped": NO_LAND}
    return {"open_share": [[number(v, 4) for v in row] for row in share],
            "north_deg": number(north_deg, 2), "south_deg": number(south_deg, 2),
            "valid_share": number(valid_share, 3), "pixel_m": pixel_m,
            "elev_edges": list(horizon.ELEV_EDGES_DEG)}   # the bins of open_share (grazing.horizons_of_cells reads them)


def work_order(cells: list[dict]) -> list[dict]:
    """Named sites, samples, rock and doubtful cells first, then the top lists from their best cell down,
    then the cells in for the census alone: rankable northern cells, other northern cells, the south."""
    fixed = [c for c in cells if not candidates.droppable(c)]
    return fixed + candidates.drop_order(cells)[::-1]


def compute(cell: dict) -> tuple[str, dict, float]:
    """One cell in a worker process: its id, its record and the seconds it took."""
    started = time.perf_counter()
    try:
        result = record(*horizon.cell_open_share(cell["lat"], cell["lon"], HALF_KM, REACH_KM, PIXEL_M), PIXEL_M)
    except ValueError as error:   # a window across the antimeridian or over a pole
        result = {"skipped": str(error)}
    except Exception as error:    # one bad cell must not lose the run; it is tried again next time
        result = {"skipped": f"{FAILED}: {type(error).__name__}: {error}"}
    return cell["id"], result, time.perf_counter() - started


def write_json(path: Path, value) -> None:
    side = path.with_name(path.name + ".part")
    side.write_text(json.dumps(value, separators=(",", ":")))
    os.replace(side, path)


def summary(done: dict, wanted: list[dict]) -> str:
    """Counts over the candidates: cells with a horizon, and the skipped ones by reason."""
    reasons: dict[str, int] = {}
    with_horizon = missing = 0
    for cell in wanted:
        stored = done.get(cell["id"])
        if stored is None:
            missing += 1
        elif "skipped" in stored:
            reason = stored["skipped"]
            key = ("crosses the antimeridian" if "antimeridian" in reason else
                   next((prefix for prefix in TRY_AGAIN if reason.startswith(prefix)), reason))
            reasons[key] = reasons.get(key, 0) + 1
        else:
            with_horizon += 1
    return (f"candidates: {len(wanted)}; with a horizon: {with_horizon}; skipped: {json.dumps(reasons)}; "
            f"not in the file: {missing}")


def main(cached_only: bool = False) -> None:
    started = time.perf_counter()
    wanted = json.loads(CANDIDATES.read_text())
    done = json.loads(OUT.read_text()) if OUT.exists() else {}
    todo = work_order([c for c in wanted if needs_horizon(done.get(c["id"]), PIXEL_M)])
    print(f"candidates: {len(wanted)}; already done at {PIXEL_M:g} m: {len(wanted) - len(todo)}; to do: {len(todo)}")

    tiles: dict[str, list[str]] = {}
    refused_now = []
    for cell in todo:
        urls, refused = tile_urls(cell)
        if refused is None:
            tiles[cell["id"]] = urls
        else:
            done[cell["id"]] = {"skipped": refused}
            refused_now.append(cell["id"])
    todo = [c for c in todo if c["id"] in tiles]
    every_url = sorted({url for urls in tiles.values() for url in urls})
    states = [tile_state(url, earth.GLO90_DIR) for url in every_url]
    cost = expected_bytes(every_url, earth.GLO90_DIR)
    print(f"windows refused: {len(refused_now)}; "
          f"tiles needed: {len(every_url)} (cached {states.count('cached')}, known ocean {states.count('ocean')}, "
          f"new {states.count('new')}); expected new download: {sum(cost.values()) / 1e6:.0f} MB")

    if cached_only:
        fetched = {"asked": 0, "fetched": 0, "bytes": 0, "ocean": 0, "failures": {}}
        held = without_new_tiles(tiles, earth.GLO90_DIR)
        new_tiles = sorted({url for cid in held for url in tiles[cid] if tile_state(url, earth.GLO90_DIR) == "new"})
        print(f"DOWNLOADS ARE OFF (--cached-only): no tile is asked for; cells held back: {len(held)} "
              f"(they need {len(new_tiles)} tiles that are not on disk, about "
              f"{sum(cost[url] for url in new_tiles) / 1e6:.0f} MB); run again without --cached-only to fetch them")
    else:
        dropped = over_budget([c["id"] for c in candidates.drop_order(todo)], tiles, cost, BUDGET_BYTES)
        if dropped:
            print(f"OVER THE DOWNLOAD BUDGET of {BUDGET_BYTES / 1e9:.1f} GB: left out {len(dropped)} cells, census "
                  f"cells first (south, then north), then from the bottom of the top lists:", *dropped, sep="\n  ")
            for cid in dropped:
                done[cid] = {"skipped": OVER_BUDGET}
                del tiles[cid]
            todo = [c for c in todo if c["id"] in tiles]
            every_url = sorted({url for urls in tiles.values() for url in urls})

        fetch_started = time.perf_counter()
        fetched = fetch_tiles(every_url, earth.GLO90_DIR)
        print(f"tiles asked for: {fetched['asked']}; fetched: {fetched['fetched']} ({fetched['bytes'] / 1e6:.1f} MB); "
              f"ocean (404): {fetched['ocean']}; failed: {len(fetched['failures'])}; "
              f"download time: {time.perf_counter() - fetch_started:.0f} s", flush=True)
        held = held_back(tiles, fetched["failures"])
        if fetched["failures"]:
            print(f"FAILED DOWNLOADS (run again to retry); cells held back: {len(held)}",
                  *[f"{url}: {error}" for url, error in fetched["failures"].items()], sep="\n  ")
    for cid, reason in held.items():
        done[cid] = {"skipped": reason}
    todo = [c for c in todo if c["id"] not in held]
    write_json(OUT, done)
    print(f"cells to work out now: {len(todo)}", flush=True)

    compute_started = time.perf_counter()
    seconds = []
    with ProcessPoolExecutor(max_workers=PROCESSES, initializer=no_downloads if cached_only else None) as pool:
        for count, (cid, result, took) in enumerate(pool.map(compute, todo, chunksize=2), start=1):
            done[cid] = result
            seconds.append(took)
            if count % SAVE_EVERY == 0:
                write_json(OUT, done)
                print(f"  {count} of {len(todo)} cells, {time.perf_counter() - compute_started:.0f} s", flush=True)
    write_json(OUT, done)
    if seconds:
        print(f"computed {len(seconds)} cells in {time.perf_counter() - compute_started:.0f} s with {PROCESSES} "
              f"processes; inside a worker: mean {np.mean(seconds):.2f} s, max {np.max(seconds):.2f} s per cell")
    print(summary(done, wanted))
    print(f"wrote {OUT}; whole run {time.perf_counter() - started:.0f} s")
    if fetched["failures"]:
        sys.exit(1)


if __name__ == "__main__":
    unknown = [argument for argument in sys.argv[1:] if argument != "--cached-only"]
    if unknown:
        sys.exit(f"unknown argument: {unknown[0]} (the only one is --cached-only)")
    main(cached_only="--cached-only" in sys.argv[1:])

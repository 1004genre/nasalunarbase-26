# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Rock shares per southern grid cell from the two Antarctic rock-outcrop layers.

Writes records shaped like the northern land-cover cells. "bare" is the larger
of the two layers' rock shares of the cell's land, and "ice" is the rest: the
ice sheet counts as land, as glaciers do in the north.

"land_source" says where each cell's land share came from: "glo90" (the water
mask), "whole cell" (no mask looked up) or "rock area" (the mask shows less
land than there is rock, so bare is 1 by construction). Unlike the northern
file, cells with a small land share are kept; screen on land_share as well as
on bare.
"""
import json
import time
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path

from twinfinder import earth, grid, rock_south

OUT = Path("data/derived/landcover_cells_south.json")
SITES = Path("data/reference/antarctic_sites.json")
MIN_BARE = 0.05  # cells below this are not written
# The land share is looked up in the water mask only where rock covers 3% of the whole cell, and only
# north of 79S: the open sea does not reach further south, and this keeps the downloads near 400 tiles.
MASK_MIN_ROCK = 0.03
MASK_SOUTH_EDGE = -79.0
CHECK_TILES = 12  # water masks sampled south of that line to test the claim
THRESHOLDS = (0.05, 0.15, 0.25)
SCOUT_BAND_SOUTH = -84.0  # the scout counted cells between 59S and 84S


def south_edge(cid: str) -> float:
    return float(cid.split("_")[0])


def mask_path(tile: tuple[int, int]) -> Path:
    return earth.GLO90_DIR / earth.tile_url(tile[0] + 0.5, tile[1] + 0.5, "WBM").rsplit("/", 1)[-1]


def fetch_masks(tiles: list[tuple[int, int]]) -> tuple[int, int]:
    """Download the water masks not yet cached, six at a time. Returns (fetched, not on the server)."""
    new = [tile for tile in tiles if not mask_path(tile).exists()]
    with ThreadPoolExecutor(max_workers=6) as pool:
        found = list(pool.map(lambda tile: rock_south.water_tile(*tile) is not None, new))
    return sum(found), len(tiles) - sum(mask_path(tile).exists() for tile in tiles)


def all_land(tile: tuple[int, int]) -> bool:
    mask = rock_south.water_tile(*tile)
    return mask is not None and not mask.any()


def whole_cell_shares(r: dict) -> tuple[float, float, float]:
    """Rock shares of the whole cell: Landsat layer, medium layer, the larger."""
    landsat, medium = r["rock_landsat_km2"] / r["cell_km2"], r["rock_medium_km2"] / r["cell_km2"]
    return landsat, medium, max(landsat, medium)


def count_table(records: list[dict], title: str) -> None:
    """Cells at or above each threshold, per layer and for the larger, by both denominators."""
    print(f"\n{title}: {len(records)} cells with rock")
    print("  share >=   of whole cell: landsat medium larger   of land: landsat medium larger")
    for threshold in THRESHOLDS:
        whole = [sum(whole_cell_shares(r)[i] >= threshold for r in records) for i in range(3)]
        land = [sum(r[key] >= threshold for r in records) for key in ("rock_landsat", "rock_medium", "bare")]
        print(f"  {threshold:<9}                {whole[0]:7d} {whole[1]:6d} {whole[2]:6d}"
              f"            {land[0]:7d} {land[1]:6d} {land[2]:6d}")


def print_sites(by_id: dict) -> None:
    print("\nnamed sites (the cell under each site's point)")
    print("  site                                 cell            bare  landsat medium  land  source")
    for site in json.loads(SITES.read_text()):
        cid = grid.cell_id(site["lat"], site["lon"])
        r = by_id.get(cid)
        if r is None:
            print(f"  {site['name'][:36]:36s} {cid:14s}  no rock in either layer")
            continue
        print(f"  {site['name'][:36]:36s} {cid:14s} {r['bare']:5.3f}  {r['rock_landsat']:5.3f}  "
              f"{r['rock_medium']:5.3f} {r['land_share']:5.3f}  {r['land_source']}")


def main() -> None:
    start = time.time()
    rock = {name: rock_south.rock_km2_per_cell(path) for name, path in rock_south.LAYERS.items()}
    for name, cells in rock.items():
        print(f"{name}: rock in {len(cells)} cells, {sum(cells.values()):.0f} km2")
    touched = set(rock["landsat"]) | set(rock["medium"])
    cells = sorted(cid for cid in touched if grid.SOUTH_MIN_LAT <= south_edge(cid) < grid.SOUTH_MAX_LAT)
    print(f"cells with rock in the search band: {len(cells)} ({len(touched) - len(cells)} outside it)")

    def whole_share(cid: str) -> float:
        return max(rock["landsat"].get(cid, 0.0), rock["medium"].get(cid, 0.0)) / rock_south.cell_area_km2(cid)

    rocky = [cid for cid in cells if whole_share(cid) >= MASK_MIN_ROCK]
    masked = {cid for cid in rocky if south_edge(cid) >= MASK_SOUTH_EDGE}
    tiles = sorted({tile for cid in masked for tile in rock_south.cell_tiles(cid)})
    fetched, absent = fetch_masks(tiles)
    print(f"water masks for {len(masked)} cells: {len(tiles)} tiles, {fetched} downloaded now, "
          f"{absent} not on the server (open sea)")

    read_tile = lru_cache(maxsize=16)(rock_south.water_tile)
    records, lifted = [], 0
    for cid in cells:
        share = rock_south.land_share(cid, read_tile) if cid in masked else None
        record = rock_south.cell_record(cid, rock["landsat"].get(cid, 0.0), rock["medium"].get(cid, 0.0), share)
        lifted += share is not None and share < record["land_share"]
        records.append(record)
    count_table([r for r in records if south_edge(r["id"]) >= SCOUT_BAND_SOUTH], "59S to 84S")
    count_table(records, f"59S to {-grid.SOUTH_MIN_LAT}S")
    print(f"\ncells where the mask shows less land than rock (land raised to the rock area): {lifted}")
    kept = [r for r in records if r["bare"] >= MIN_BARE]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(kept))
    print(f"wrote {OUT}: {len(kept)} cells with bare >= {MIN_BARE}")
    for threshold in THRESHOLDS:
        chosen = [r for r in kept if r["bare"] >= threshold]
        print(f"  bare >= {threshold}: {len(chosen)} cells; layers disagree by more than 2x in "
              f"{sum(r['layers_disagree'] for r in chosen)}; land from the water mask in "
              f"{sum(r['land_source'] == 'glo90' for r in chosen)}, set to the rock area in "
              f"{sum(r['land_source'] == 'rock area' for r in chosen)}; land share under 0.2 in "
              f"{sum(r['land_share'] < 0.2 for r in chosen)}")
    if SITES.exists():
        print_sites({r["id"]: r for r in records})

    unmasked = sorted({tile for cid in rocky if cid not in masked for tile in rock_south.cell_tiles(cid)})
    sample = unmasked[::max(1, len(unmasked) // CHECK_TILES)][:CHECK_TILES]
    fetched, _ = fetch_masks(sample)
    wet = [tile for tile in sample if not all_land(tile)]
    print(f"\nsouth of {-MASK_SOUTH_EDGE}S the whole cell is taken as land ({len(rocky) - len(masked)} cells "
          f"on {len(unmasked)} tiles). Check on {len(sample)} of those tiles ({fetched} downloaded now): "
          f"{len(wet)} contain water or are missing {wet}")
    print(f"run time {time.time() - start:.0f} s")


if __name__ == "__main__":
    main()

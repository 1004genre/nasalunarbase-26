# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Read every WorldCover tile north of 57N at low resolution and write land-cover shares per cell."""
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import rasterio

from twinfinder import grid, landcover
from twinfinder.fetch import exists_on_server

OUT = Path("data/derived/landcover_cells.json")
CACHE = Path("data/raw/worldcover")
MIN_LAND_SHARE = 0.2
GDAL_OPTIONS = {
    "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
    "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif",
    "GDAL_HTTP_USERAGENT": "twinfinder/0.1",
    "GDAL_HTTP_MAX_RETRY": "3",
    "GDAL_HTTP_RETRY_DELAY": "2",
}


def read_tile(origin: tuple[int, int]):
    """Return (origin, class array or None for ocean, error text or None)."""
    lat0, lon0 = origin
    cached = CACHE / f"{lat0}_{lon0}.npy"
    missing = CACHE / f"{lat0}_{lon0}.missing"
    if cached.exists():
        return origin, np.load(cached), None
    if missing.exists():
        return origin, None, None
    url = landcover.tile_url(lat0, lon0)
    try:
        if not exists_on_server(url):  # only a 404 counts as open ocean; a 403 is reported as a failure
            missing.touch()
            return origin, None, None
        with rasterio.Env(**GDAL_OPTIONS), rasterio.open("/vsicurl/" + url) as ds:
            classes = ds.read(1, out_shape=(landcover.READ_PX, landcover.READ_PX))
    except Exception as error:  # reported and counted below; never treated as ocean
        return origin, None, f"{type(error).__name__}: {error}"
    np.save(cached, classes)
    return origin, classes, None


def main() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    origins = [(lat0, lon0) for lat0 in range(57, 84, grid.TILE_DEG)
               for lon0 in range(-180, 180, grid.TILE_DEG)]
    cells, land_tiles, failures = [], 0, []
    with ThreadPoolExecutor(max_workers=8) as pool:
        for (lat0, lon0), classes, error in pool.map(read_tile, origins):
            if error:
                failures.append(f"{lat0},{lon0}: {error}")
            elif classes is not None:
                land_tiles += 1
                cells.extend(c for c in landcover.cell_shares(classes, lat0, lon0)
                             if c["lat"] >= grid.MIN_LAT and c["land_share"] >= MIN_LAND_SHARE)
    cells.sort(key=lambda c: c["id"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(cells))
    bare = [c for c in cells if c["bare"] >= 0.25]
    print(f"tiles: {len(origins)} tried, {land_tiles} with land, {len(failures)} failed")
    print(f"cells with land: {len(cells)}; bare share at least 0.25: {len(bare)}; "
          f"at least 0.5: {sum(c['bare'] >= 0.5 for c in cells)}")
    print(f"wrote {OUT}")
    if failures:
        print("FAILED TILES (re-run to retry):", *failures[:20], sep="\n  ")
        sys.exit(1)


if __name__ == "__main__":
    main()

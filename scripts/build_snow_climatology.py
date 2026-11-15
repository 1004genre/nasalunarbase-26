# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Turn the IMS daily maps into year-round snow-free odds per ten-day bin, north of about 59N.

Run from the project root:
  uv run python scripts/build_snow_climatology.py              build from the maps on disk
  uv run python scripts/build_snow_climatology.py --download   first fetch the maps that are not on disk yet
"""
import gzip
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path

import numpy as np
from rasterio.io import MemoryFile

from twinfinder import snow
from twinfinder.fetch import fetch

IMS_DIR = Path("data/raw/ims")
URLS = IMS_DIR / "urls.txt"
OUT = Path("data/derived/snow_free_dekads.npz")
CROP_HALF_PX = 840  # 3,360 km from the pole, which reaches south of 59N
FIRST, LAST = (2015, 274), (2025, 273)   # 1 October 2015 to 30 September 2025, as (year, day of year)
# Every 5th day. The first download began on 1 October (day 274), so that run restarts there each year.
RHYTHM = list(range(1, 272, 5)) + list(range(274, 365, 5))
REACH_DAYS = 2        # a day the server lacks is replaced by the nearest one this close
PARALLEL = 6          # connections to the one host
MIN_WINTER_MAPS = 30  # of 34 or 35; with fewer, "snow-free on every map" says too little to call a pixel stuck

CHECKS = [
    ("Qaqortorsuaq, Greenland", 66.5833, -52.2),
    ("Lofoten, Norway", 68.04, 13.35),
    ("Reykjanes, Iceland", 63.88, -22.45),
    ("Longyearbyen, Svalbard", 78.2, 15.6),
    ("Bear Island", 74.45, 19.25),
    ("Jan Mayen", 70.95, -8.55),
    ("Baffin point", 63.15, -64.90),
    ("Devon Island, Haughton crater", 75.38, -89.67),
]


def year_and_day(path: Path) -> tuple[int, int]:
    year, day = re.match(r"ims(\d{4})(\d{3})_", path.name).groups()
    return int(year), int(day)


def map_files() -> list[Path]:
    return sorted(IMS_DIR.glob("ims*_4km_GIS_v1.3.tif.gz"))


def days_on_server(year: int) -> set[int]:
    """Days of one year that the archive folder lists."""
    folder = snow.ims_url(year, 1).rsplit("/", 1)[0] + "/"
    request = urllib.request.Request(folder, headers={"User-Agent": "twinfinder/0.1"})
    with urllib.request.urlopen(request, timeout=120) as response:
        text = response.read().decode()
    return {int(day) for day in re.findall(rf'href="ims{year}(\d{{3}})_4km_GIS_v1\.3\.tif\.gz"', text)}


def download_missing() -> None:
    """Fetch the map of every 5th day that is not on disk, taking a neighbouring day where the server has a gap."""
    have = {}
    for path in map_files():
        year, day = year_and_day(path)
        have.setdefault(year, set()).add(day)
    wanted = [(year, day) for year in range(FIRST[0], LAST[0] + 1) for day in RHYTHM
              if FIRST <= (year, day) <= LAST]
    gaps = [(year, day) for year, day in wanted
            if snow.nearest_day(day, have.get(year, ()), REACH_DAYS) is None]
    listed = {year: days_on_server(year) for year in sorted({year for year, _ in gaps})}
    picks, replaced, missing = [], [], []
    for year, day in gaps:
        found = snow.nearest_day(day, listed[year], REACH_DAYS)
        if found is None:
            missing.append(f"{year}-{day:03d}")
            continue
        picks.append((year, found))
        if found != day:
            replaced.append(f"{year}-{day:03d} by {year}-{found:03d}")
    print(f"wanted {len(wanted)} maps (every 5th day); {len(wanted) - len(gaps)} on disk, "
          f"{len(picks)} to download", flush=True)
    with ThreadPoolExecutor(PARALLEL) as pool:
        list(pool.map(lambda pick: fetch(snow.ims_url(*pick), IMS_DIR), picks))
    print(f"days replaced by a neighbour: {replaced or 'none'}")
    print(f"days with no map within {REACH_DAYS} days on the server: {missing or 'none'}")
    URLS.write_text("".join(snow.ims_url(*year_and_day(path)) + "\n" for path in map_files()))


def read_map(path: Path, row0: int, col0: int, n: int) -> np.ndarray:
    """The part of one daily map around the pole."""
    with gzip.open(path, "rb") as zipped, MemoryFile(zipped.read()) as memory, memory.open() as ds:
        if (ds.width, ds.height) != (snow.IMS_SIZE, snow.IMS_SIZE):
            raise SystemExit(f"{path.name}: unexpected size {ds.width} x {ds.height}")
        return ds.read(1, window=((row0, row0 + n), (col0, col0 + n)))


def by_season(files: list[Path]) -> tuple[dict, dict]:
    """Sort the maps into winters and the open seasons between them, each in date order.

    A winter (1 October to 20 March) is keyed by the year of its October. An open season
    (21 March to 30 September) is keyed by its own year, so the one after winter w is w + 1.
    """
    winters, open_seasons = {}, {}
    for path in files:
        year, day = year_and_day(path)
        winter = snow.winter_of(year, day)
        season = open_seasons.setdefault(year, []) if winter is None else winters.setdefault(winter, [])
        season.append((year, day, path))
    for season in (*winters.values(), *open_seasons.values()):
        season.sort()
    return winters, open_seasons


def read_season(entries: list, row0: int, col0: int, n: int) -> tuple[list, list]:
    """The maps of one season and the ten-day bin of each."""
    maps = [read_map(path, row0, col0, n) for _, _, path in entries]
    return maps, [snow.bin_index(day) for _, day, _ in entries]


def new_counts(n: int) -> tuple[np.ndarray, np.ndarray]:
    """Empty snow-free and land counts per bin and pixel."""
    return (np.zeros((snow.N_BINS, n, n), dtype="uint16"), np.zeros((snow.N_BINS, n, n), dtype="uint16"))


def add_maps(counts: tuple, maps: list, bins: list) -> None:
    """Add maps to the counts just as they read."""
    for ims_day, index in zip(maps, bins):
        snow.accumulate(*counts, ims_day, index)


def odds(free: np.ndarray, land: np.ndarray) -> np.ndarray:
    """Snow-free share of the land readings per bin; NaN where a pixel has no land reading in that bin."""
    out = np.full(free.shape, np.nan, dtype="float32")
    with np.errstate(invalid="ignore", divide="ignore"):
        for index in range(free.shape[0]):
            out[index] = np.where(land[index] > 0, free[index] / land[index], np.nan)
    return out


def build(files: list[Path], stale_flag_rule: bool = True) -> dict:
    """Count snow-free and land readings per ten-day bin and turn them into odds, in two versions.

    probabilities_as_mapped takes every map as it reads. probabilities follows the stale-flag
    rule: maps from 1 October to 20 March are handled one winter at a time, a pixel that reads
    snow-free on every map of a winter is left out of that winter, and it stays left out after
    20 March until its first map that reads snow, or 30 September if that comes first.
    """
    row0 = col0 = snow.IMS_SIZE // 2 - CROP_HALF_PX
    n = 2 * CROP_HALF_PX
    ruled, mapped = new_counts(n), new_counts(n)
    stuck_winters = np.zeros((n, n), dtype="uint8")
    maps_per_bin = np.zeros(snow.N_BINS, dtype="int16")
    for path in files:
        maps_per_bin[snow.bin_index(year_and_day(path)[1])] += 1
    winters, open_seasons = by_season(files)
    stuck_in, maps_per_winter, stale_runs = {}, {}, {}
    for winter, entries in sorted(winters.items()):
        maps, bins = read_season(entries, row0, col0, n)
        maps_per_winter[winter] = len(maps)
        add_maps(mapped, maps, bins)
        if stale_flag_rule and len(maps) >= MIN_WINTER_MAPS:
            stuck_in[winter] = snow.accumulate_winter(*ruled, maps, bins)
            stuck_winters += stuck_in[winter]
        else:
            add_maps(ruled, maps, bins)
    nobody = np.zeros((n, n), dtype=bool)
    for year, entries in sorted(open_seasons.items()):
        maps, bins = read_season(entries, row0, col0, n)
        add_maps(mapped, maps, bins)
        stuck = stuck_in.get(year - 1, nobody)      # only the winter just before reaches into this season
        still = snow.accumulate_after_winter(*ruled, maps, bins, stuck)
        if year - 1 in stuck_in:
            stale_runs[year - 1] = (int(stuck.sum()), int(still.sum()))
    return {"probabilities": odds(*ruled), "probabilities_as_mapped": odds(*mapped), "row0": row0, "col0": col0,
            "stuck_winters": stuck_winters, "maps_per_bin": maps_per_bin, "maps_per_winter": maps_per_winter,
            "stale_runs": stale_runs}


def bin_label(index: int) -> str:
    """First day of a ten-day bin, such as Oct08."""
    return (date(2023, 1, 1) + timedelta(days=snow.BIN_DAYS * index)).strftime("%b%d")


def print_checks(title: str, probabilities: np.ndarray, row0: int, col0: int) -> None:
    print(f"\n{title} (each bin is named by its first day; the last runs to 31 December):")
    rows = [(name, snow.cell_probabilities(probabilities, row0, col0, lat, lon)) for name, lat, lon in CHECKS]
    for bins in (range(0, 18), range(18, 36)):
        print(" " * 36 + " ".join(f"{bin_label(index):>5s}" for index in bins))
        for name, values in rows:
            print(f"{name:36s}" + " ".join("    -" if np.isnan(values[i]) else f"{values[i]:5.2f}" for i in bins))


def main() -> None:
    if "--download" in sys.argv[1:]:
        download_missing()
    files = map_files()
    result = build(files)
    maps_per_winter, stale_runs = result.pop("maps_per_winter"), result.pop("stale_runs")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    part = OUT.with_name(OUT.stem + ".part.npz")   # written beside the archive and swapped in whole
    np.savez_compressed(part, files=len(files), **result)
    part.replace(OUT)
    stuck = result["stuck_winters"]
    print(f"used {len(files)} maps; maps per bin: {result['maps_per_bin'].tolist()}")
    print(f"maps per winter (1 October to 20 March): {maps_per_winter}")
    short = [winter for winter, count in maps_per_winter.items() if count < MIN_WINTER_MAPS]
    if short:
        print(f"winters with fewer than {MIN_WINTER_MAPS} maps, stale-flag rule not applied: {short}")
    print(f"pixels snow-free on every map of at least one winter (left out of that winter): "
          f"{int((stuck > 0).sum())}; highest count of such winters at one pixel: {int(stuck.max())}")
    print("after each winter, (stuck pixels, of which still without a snowy map on 30 September): "
          f"{stale_runs}")
    print(f"wrote {OUT}")
    print_checks("Snow-free odds by ten-day bin, with the stale-flag rule",
                 result["probabilities"], result["row0"], result["col0"])
    print_checks("The same as mapped, with no rule",
                 result["probabilities_as_mapped"], result["row0"], result["col0"])


if __name__ == "__main__":
    main()

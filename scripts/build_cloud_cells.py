# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Typical cloud for every cell. Writes data/derived/cloud_cells.json (decision 17 of version 3).

For each cell of data/derived/grazing_cells.json: the 12 monthly means of cloud
amount (percent of sky covered, all hours of the day) of the 1 degree grid box
that holds the cell centre, from the NASA POWER climatology service (CERES
SYN1deg). The daylight-hours and night-hours versions are kept beside it.

The service is asked once per parameter and 10 degree block, one request at a
time with a pause; every raw answer is kept under data/raw/power/ and a second
run makes no request. `--offline` forbids requests altogether. The result is
written beside the old file and renamed into place.

Mean cloud amount is not the chance that a low Sun is visible. See
twinfinder/cloud.py for what the number is and is not.
"""
import argparse
import datetime
import json
import os
import statistics
import time
from pathlib import Path

from twinfinder import cloud

CELLS = Path("data/derived/grazing_cells.json")
RAW = Path("data/raw/power")
LOG = RAW / "fetch_log.jsonl"
OUT = Path("data/derived/cloud_cells.json")
EXTRA = {"cloud_pct_day": "CLOUD_AMT_DAY", "cloud_pct_night": "CLOUD_AMT_NIGHT"}
PLACES = [
    ("Reykjanes", 63.88, -22.45),
    ("Resolute", 74.7, -94.97),
    ("Longyearbyen", 78.2, 15.6),
    ("Kotelny Island", 75.0, 141.25),
    ("Pechora Sea coast", 68.95, 54.45),
    ("Vestfold Hills", -68.55, 78.15),
    ("McMurdo Dry Valleys", -77.6, 161.5),
]


def write_json(path: Path, value) -> None:
    side = path.with_name(path.name + ".part")
    side.write_text(json.dumps(value, separators=(",", ":"), allow_nan=False))
    os.replace(side, path)


def now_utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_all(tiles, offline: bool, pause_s: float) -> int:
    """Make sure every raw answer is on disk. Returns the number of requests made."""
    asked = 0
    wanted = [(parameter, tile) for parameter in cloud.PARAMETERS for tile in tiles]
    for n, (parameter, tile) in enumerate(wanted, 1):
        path = RAW / cloud.raw_name(parameter, tile)
        if path.exists():
            continue
        if offline:
            raise SystemExit(f"--offline, but {path} is missing")
        cloud.fetch_tile(parameter, tile, RAW)
        asked += 1
        with open(LOG, "a") as log:
            log.write(json.dumps({"time": now_utc(), "url": cloud.regional_url(parameter, tile),
                                  "file": path.name, "bytes": path.stat().st_size}) + "\n")
        if asked % 25 == 0:
            print(f"  asked {asked} (at {n} of {len(wanted)})", flush=True)
        time.sleep(pause_s)
    return asked


def fetched_span(names: set[str]) -> str:
    """When the raw answers that were used came from the service (UTC), from the log or the file times."""
    times = {}
    if LOG.exists():
        for line in LOG.read_text().splitlines():
            entry = json.loads(line)
            times[entry["file"]] = entry["time"]
    for name in names:
        if name not in times:
            stamp = datetime.datetime.fromtimestamp((RAW / name).stat().st_mtime, datetime.timezone.utc)
            times[name] = stamp.strftime("%Y-%m-%dT%H:%M:%SZ")
    used = sorted(times[name] for name in names)
    return used[0] if used[0] == used[-1] else f"{used[0]} to {used[-1]}"


def median(values) -> float | None:
    known = [v for v in values if v is not None]
    return round(statistics.median(known), 1) if known else None


def summary(cells, table) -> dict:
    """Counts and medians over cells, for the meta block and the printed report."""
    north = [c["id"] for c in cells if c["hemisphere"] == "N"]
    south = [c["id"] for c in cells if c["hemisphere"] == "S"]

    def month(ids, field, m):
        return median(table[i][field][m] if table[i][field] else None for i in ids)

    def whole(field):
        return sum(1 for r in table.values() if r[field] and all(v is not None for v in r[field]))

    def partly(field):
        return sum(1 for r in table.values() if r[field] and any(v is None for v in r[field]))

    return {
        "cells": len(table),
        "grid_boxes": len({tuple(r["grid"]) for r in table.values()}),
        "cells_with_all_12_months": {f: whole(f) for f in ("cloud_pct", *EXTRA)},
        "cells_with_some_months": {f: partly(f) for f in ("cloud_pct", *EXTRA)},
        "cells_with_no_month": {f: sum(1 for r in table.values() if not r[f]) for f in ("cloud_pct", *EXTRA)},
        "median_pct_north_cells": {name: {"july": month(north, f, 6), "august": month(north, f, 7)}
                                   for name, f in (("all_hours", "cloud_pct"), ("daylight", "cloud_pct_day"))},
        "median_pct_south_cells": {name: {"december": month(south, f, 11), "january": month(south, f, 0)}
                                   for name, f in (("all_hours", "cloud_pct"), ("daylight", "cloud_pct_day"))},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--offline", action="store_true", help="make no request; fail if a raw answer is missing")
    parser.add_argument("--pause", type=float, default=0.6, help="seconds between two requests")
    args = parser.parse_args()

    cells = json.loads(CELLS.read_text())["cells"]
    boxes = cloud.boxes_of(cells)
    tiles = cloud.tiles_for(boxes)
    print(f"{len(cells)} cells in {len(boxes)} grid boxes of {cloud.GRID_DEG:g} degree; "
          f"{len(tiles)} blocks of {cloud.TILE_DEG} degrees x {len(cloud.PARAMETERS)} parameters", flush=True)
    RAW.mkdir(parents=True, exist_ok=True)
    asked = fetch_all(tiles, args.offline, args.pause)
    print(f"requests made in this run: {asked}", flush=True)

    by_box = {parameter: cloud.read_raw(RAW, parameter, tiles) for parameter in cloud.PARAMETERS}
    names = {cloud.raw_name(parameter, tile) for parameter in cloud.PARAMETERS for tile in tiles}
    headers = {parameter: [cloud.answer_header((RAW / cloud.raw_name(parameter, tile)).read_bytes()) for tile in tiles]
               for parameter in cloud.PARAMETERS}
    missing = [box for box in boxes if box not in by_box[cloud.PARAMETERS[0]]]
    if missing:
        print(f"WARNING: the service returned no grid box for {len(missing)} boxes, first {missing[:5]}")

    table = cloud.cells_table(cells, by_box[cloud.PARAMETERS[0]],
                              extra={field: by_box[parameter] for field, parameter in EXTRA.items()})
    counts = summary(cells, table)
    meta = cloud.meta_from(headers[cloud.PARAMETERS[0]], fetched=fetched_span(names))
    meanings = {
        "cloud_pct_day": "the same mean over daylight hours only; null in months without daylight",
        "cloud_pct_night": "the same mean over night hours only; null in months without night",
    }
    extra_fields = {}
    for field, parameter in EXTRA.items():
        own = cloud.meta_from(headers[parameter], fetched=meta["fetched"], parameter=parameter)
        if own["period"] != meta["period"] or own["fill_value"] != meta["fill_value"]:
            raise SystemExit(f"{parameter} covers {own['period']}, fill {own['fill_value']}; "
                             f"{meta['parameter']} covers {meta['period']}, fill {meta['fill_value']}")
        extra_fields[field] = {"parameter": parameter, "meaning": meanings[field], "source": own["source"]}
    meta.update({
        "extra_fields": extra_fields,
        "null_rule": "cloud_pct is null when no month has a value; a single month without a value is null inside the list",
        "cell_to_grid": "the 1 degree box that holds the cell centre (lat, lon of grazing_cells.json); grid = [lat, lon] of the box centre",
        "resolution_note": ("the service answers on a 1 degree grid, but polewards of 45 degrees neighbouring boxes "
                            "along a latitude carry the same or nearly the same value in groups (CERES nested grid: "
                            "about 2 degrees of longitude from 45 to 70, 4 from 70 to 80, 8 from 80 to 89)"),
        "request_rules_followed": "one parameter and at most 10 x 10 degrees per request, one request at a time, no key, no login",
        "raw_answers": {"folder": str(RAW), "files": len(names)},
        "cells_source": str(CELLS),
        "written": now_utc(),
        "counts": counts,
    })
    write_json(OUT, {"meta": meta, "cells": table})

    print(f"wrote {OUT}: {counts['cells']} cells, {counts['grid_boxes']} grid boxes")
    print(json.dumps(counts, indent=1))
    print(f"period {meta['period']}; fetched {meta['fetched']}; source: {meta['source']}")
    for name, lat, lon in PLACES:
        box = cloud.grid_box(lat, lon)
        tile = cloud.tile_of(box)
        for parameter in cloud.PARAMETERS:
            path = RAW / cloud.raw_name(parameter, tile)
            if not path.exists():
                print(f"{name} {box} {parameter}: block {tile} not fetched (no cell there)")
                continue
            values = cloud.read_answer(path.read_bytes(), parameter).get(box)
            shown = " ".join("  n/a" if v is None else f"{v:5.1f}" for v in values) if values else "no such box"
            print(f"{name:20s} {str(box):16s} {parameter:16s} {shown}")


if __name__ == "__main__":
    main()

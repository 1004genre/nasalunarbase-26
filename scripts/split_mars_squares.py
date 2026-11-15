# This file was written with AI assistance (Claude, Anthropic) for the Earth Twin Finder project.
"""Divide the Mars scores file of the page so that the page loads one Mars site at a time.

site/data/mars_squares.bin holds, for every Earth square, a few shared columns and 15 columns for
each Mars site. With many Mars sites the file is too large to load at once. This script writes:

    mars_squares.bin          the shared columns, and six new ones: for each square, the three Mars
                              sites that it comes nearest to on all factors (their index in
                              mars.json "sites") and those three scores
    mars_site_<id>.bin        the 15 columns of one Mars site
    mars.json                 the same file with each column's new place: a column that has a
                              "file" field is in that file, at its "offset" there; a column without
                              a "file" field is in mars_squares.bin

    uv run python scripts/split_mars_squares.py                      # site/data
    uv run python scripts/split_mars_squares.py --site-data <folder>

It changes no value. Run it after scripts/export_site_mars.py. It does nothing if the file is
divided already.
"""
from __future__ import annotations

import argparse
import json
import os
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SIZES = {"int8": 1, "uint8": 1, "int16": 2, "uint16": 2, "int32": 4, "uint32": 4, "float32": 4, "float64": 8}
CODES = {"int8": "b", "uint8": "B", "int16": "h", "uint16": "H", "int32": "i", "uint32": "I", "float32": "f", "float64": "d"}
NEAREST = 3


def write(path: Path, data: bytes) -> None:
    side = path.with_name(path.name + ".part")
    side.write_bytes(data)
    os.replace(side, path)


def column_bytes(data: bytes, spec: dict, count: int) -> bytes:
    size = SIZES[spec["type"]] * count
    return data[spec["offset"]:spec["offset"] + size]


def values(raw: bytes, spec: dict, count: int) -> list:
    return list(struct.unpack("<" + str(count) + CODES[spec["type"]], raw))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--site-data", type=Path, default=ROOT / "site" / "data")
    args = parser.parse_args()
    folder = args.site_data
    doc = json.loads((folder / "mars.json").read_text(encoding="utf-8"))
    squares = doc["squares"]
    columns = squares["columns"]
    if any("file" in spec for spec in columns.values()):
        print("split_mars_squares: the file is divided already; nothing done")
        return
    count = squares["count"]
    data = (folder / squares["file"]).read_bytes()
    site_ids = [site["id"] for site in doc["sites"]]

    shared, by_site = [], {site_id: [] for site_id in site_ids}
    for name, spec in columns.items():
        if name.startswith("sites."):
            # A column name is sites.<site id>.<column>, and the column part can hold dots.
            owner = next((i for i in sorted(site_ids, key=len, reverse=True) if name.startswith(f"sites.{i}.")), None)
            if owner is None:
                raise SystemExit(f"split_mars_squares: column {name} names a site that mars.json does not hold")
            by_site[owner].append(name)
        else:
            shared.append(name)

    new_columns: dict[str, dict] = {}
    out = bytearray()
    for name in shared:
        spec = dict(columns[name])
        raw = column_bytes(data, spec, count)
        spec["offset"] = len(out)
        out += raw
        new_columns[name] = spec

    # For each square: the three sites with the highest score on all factors (known scores only).
    full = {}
    for site_id in site_ids:
        spec = columns.get(f"sites.{site_id}.full")
        if spec is None:
            raise SystemExit(f"split_mars_squares: no column sites.{site_id}.full")
        full[site_id] = (values(column_bytes(data, spec, count), spec, count), spec)
    ref = next(iter(full.values()))[1]
    nearest_site = [[255] * count for _ in range(NEAREST)]
    nearest_score = [[ref["unknown"]] * count for _ in range(NEAREST)]
    for k in range(count):
        ranked = sorted(((vals[k], i) for i, (vals, spec) in enumerate(full.values()) if vals[k] != spec["unknown"]),
                        key=lambda pair: (-pair[0], pair[1]))[:NEAREST]
        for place, (score, index) in enumerate(ranked):
            nearest_site[place][k] = index
            nearest_score[place][k] = score
    for place in range(NEAREST):
        new_columns[f"nearest_site_{place}"] = {"type": "uint8", "scale": 1, "unknown": 255, "offset": len(out),
                                                "what": f"Index in 'sites' of the Mars site with rank {place + 1} for this square on all factors."}
        out += struct.pack("<" + str(count) + "B", *nearest_site[place])
    for place in range(NEAREST):
        new_columns[f"nearest_full_{place}"] = {"type": ref["type"], "scale": ref["scale"], "unknown": ref["unknown"], "offset": len(out),
                                                "what": f"The score on all factors of the site with rank {place + 1} for this square."}
        out += struct.pack("<" + str(count) + CODES[ref["type"]], *nearest_score[place])
    write(folder / squares["file"], bytes(out))

    site_files = {}
    for site_id in site_ids:
        part = bytearray()
        file_name = f"mars_site_{site_id}.bin"
        for name in by_site[site_id]:
            spec = dict(columns[name])
            raw = column_bytes(data, spec, count)
            spec["offset"] = len(part)
            spec["file"] = file_name
            part += raw
            new_columns[name] = spec
        write(folder / file_name, bytes(part))
        site_files[site_id] = {"file": file_name, "bytes": len(part)}

    squares["columns"] = new_columns
    squares["site_files"] = site_files
    squares["bytes"] = len(out)
    squares["layout"] = (squares.get("layout", "").rstrip() + " A column that has a 'file' field is in that file, at its 'offset' there. "
                         "A column without a 'file' field is in the file that 'file' of this block names. "
                         "The columns nearest_site_0 to nearest_site_2 give, for each square, the index in 'sites' of the three Mars sites "
                         "with the highest score on all factors; nearest_full_0 to nearest_full_2 give those scores.").strip()
    write(folder / "mars.json", json.dumps(doc, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8"))
    print(f"split_mars_squares: {len(shared)} shared columns and {2 * NEAREST} new ones in {squares['file']} ({len(out):,} bytes); "
          f"{len(site_ids)} site files of {next(iter(site_files.values()))['bytes']:,} bytes each")


if __name__ == "__main__":
    main()

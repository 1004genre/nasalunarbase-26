# This file was written with AI assistance (Claude, Anthropic) for the Earth Twin Finder project.
"""Write a compressed copy of each large data file of the page.

For each .bin and .json file in site/data, this script writes the same
bytes compressed with gzip beside it, as <name>.gz. The page asks for <name>.gz first and opens it in
the browser; if that file is not there, it asks for <name>. So the page works with and without the
compressed copies. The plain files stay: the build scripts and the checks read them.

    uv run python scripts/compress_site_data.py                      # site/data
    uv run python scripts/compress_site_data.py --site-data <folder>

Run it last, after every script that writes site/data (the exporters, split_mars_squares.py and
apply_ste_text.py). A compressed copy that is older than its plain file is written again; one whose
plain file is gone is removed.
"""
from __future__ import annotations

import argparse
import gzip
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIMIT = 0   # every file gets a compressed copy, so that the page never asks for a copy that is not there


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--site-data", type=Path, default=ROOT / "site" / "data")
    args = parser.parse_args()
    folder = args.site_data
    plain_total = packed_total = written = 0
    for packed in sorted(folder.glob("*.gz")):
        if not packed.with_suffix("").exists():
            packed.unlink()
    for path in sorted(list(folder.glob("*.bin")) + list(folder.glob("*.json"))):
        size = path.stat().st_size
        packed = path.with_name(path.name + ".gz")
        if size < LIMIT:
            if packed.exists():
                packed.unlink()
            continue
        if not packed.exists() or packed.stat().st_mtime < path.stat().st_mtime:
            side = packed.with_name(packed.name + ".part")
            with open(side, "wb") as raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=9, mtime=0) as out:
                out.write(path.read_bytes())
            os.replace(side, packed)
            written += 1
        plain_total += size
        packed_total += packed.stat().st_size
    print(f"compress_site_data: {written} file(s) written; {plain_total / 1e6:.1f} MB of large files are {packed_total / 1e6:.1f} MB compressed")


if __name__ == "__main__":
    main()

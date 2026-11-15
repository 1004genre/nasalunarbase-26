# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""List the cells that get a terrain horizon and slope statistics. Writes data/derived/candidates.json.

Since version 3 that is every cell of data/derived/grazing_cells.json, gridded
and named. Each record keeps the reasons twinfinder.candidates gave it before:
a top cell per lunar target by light on bare ground, a cell on an anorthosite
body, a doubtful cell that would have ranked, the blind sample, a named site.
A cell with none of these has the single reason "all". Safe to run again: the
file is written beside the old one and renamed into place, and the same input
gives the same list.
"""
import json
import os
from pathlib import Path

from twinfinder import candidates

CELLS = Path("data/derived/grazing_cells.json")
BODIES = Path("data/reference/anorthosite_bodies.json")
OUT = Path("data/derived/candidates.json")


def write_json(path: Path, value) -> None:
    side = path.with_name(path.name + ".part")
    side.write_text(json.dumps(value, separators=(",", ":")))
    os.replace(side, path)


def main() -> None:
    grazing_cells = json.loads(CELLS.read_text())
    target_ids = [t["id"] for t in grazing_cells["meta"]["targets"]]
    bodies = json.loads(BODIES.read_text())
    found, sizes = candidates.census(grazing_cells["cells"], target_ids, bodies)
    write_json(OUT, found)
    for name, size in sizes.items():
        print(f"  {name:38s} {size:5d}")
    north = sum(c["hemisphere"] == "N" for c in found)
    census_only = sizes[candidates.ALL]
    print(f"candidates: {len(found)} (north {north}, south {len(found) - north}); "
          f"in for the census alone: {census_only}; "
          f"held by top lists alone: {len(candidates.drop_order(found)) - census_only}; wrote {OUT}")


if __name__ == "__main__":
    main()

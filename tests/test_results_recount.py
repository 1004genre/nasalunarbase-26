# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""RESULTS.md against an independent recount: tests/recount_results.py counts the tables again from the stored cells,
with its own code, and every figure scripts/make_results.py prints must be what it finds."""
import importlib
import runpy
from pathlib import Path

import pytest

make_results = importlib.import_module("scripts.make_results")

DERIVED = Path("data/derived")
NEEDED = ("grazing_cells.json", "grazing_bins.npz", "cells_scored.json", "validation.json", "latitude_profile.json",
          "candidates.json", "cloud_cells.json", "ranking.txt", "validation_v2.json", "cells_scored_v2.json",
          "light_cells_v1.json")


@pytest.fixture(scope="module")
def recount():
    missing = [name for name in NEEDED if not (DERIVED / name).exists()]
    if missing:
        pytest.skip(f"the chain has not been run: {missing} not in data/derived")
    lines, _ = make_results.build()
    return runpy.run_path("tests/recount_results.py", init_globals={"TEXT": "\n".join(lines) + "\n"})


def test_every_table_figure_equals_the_independent_recount(recount, capsys):
    capsys.readouterr()
    assert recount["differ"] == []


def test_the_recount_covers_the_tables(recount):
    assert recount["checked"] > 1700        # figures and texts compared, sections (b) to (k) without (a) and (f)

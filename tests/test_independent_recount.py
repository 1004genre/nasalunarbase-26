# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""The independent recount: it shares no code with the pipeline, and its eight-calendar Sun agrees with the pipeline's."""
import ast
import importlib
import json
from pathlib import Path

import numpy as np

from twinfinder import sun

recount = importlib.import_module("scripts.independent_recount")
SOURCE = Path(__file__).resolve().parents[1] / "scripts" / "independent_recount.py"


def test_the_program_imports_nothing_of_the_pipeline():
    tree = ast.parse(SOURCE.read_text())
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            names.add((node.module or "").split(".")[0])
    assert "twinfinder" not in names and "scripts" not in names
    assert names <= {"__future__", "argparse", "hashlib", "json", "math", "os", "time", "concurrent", "datetime",
                     "pathlib", "numpy"}


def test_its_calendars_are_the_pipelines_eight_written_again():
    assert recount.PHASES == sun.YEAR_PHASES == 8
    assert recount.phase_offsets() == sun.phase_offsets()
    assert recount.DAY0 == sun.DAY_ZERO_FROM_J2000


def test_its_eight_calendar_long_hours_agree_with_the_pipelines_table():
    lat, limit = 70.05, 5.55
    mine = recount.year_tables(lat, [limit])["long"][0]                  # [36 bins, 36 sectors, 9 elevation bins], minutes
    theirs = sun.long_band_minutes_table([lat], [limit])[0, 0]
    assert abs(mine.sum() - theirs.sum()) / 60.0 < 0.05                  # hours a year
    assert np.abs(mine.sum(axis=(1, 2)) - theirs.sum(axis=(1, 2))).max() / 60.0 < 0.02   # hours in any ten-day bin
    one = recount.year_tables(lat, [limit], phases=1)["long"][0]
    assert abs(one.sum() - mine.sum()) > 0.0                             # the average is not one calendar


def test_a_check_record_is_added_beside_the_others(tmp_path):
    path = tmp_path / "checks.json"
    path.write_text(json.dumps({"jpl_horizons": {"places": 9}}))
    recount.write_check("independent_recount", {"cells": 3, "largest_difference_h_a_year": None}, path)
    whole = json.loads(path.read_text())
    assert whole["jpl_horizons"] == {"places": 9}
    assert whole["independent_recount"] == {"cells": 3, "largest_difference_h_a_year": None}
    assert not (tmp_path / "checks.json.part").exists()


def test_outside_uses_the_larger_of_two_percent_and_one_hour_and_flags_unknown_on_one_side():
    assert recount.outside(40.9, 40.0)[0] is False                      # under 50 h the 1 h rule is the larger
    assert recount.outside(41.1, 40.0)[0] is True
    assert recount.outside(509.0, 500.0)[0] is False                    # 2 percent of 500 is 10 h
    assert recount.outside(511.0, 500.0)[0] is True
    assert recount.outside(None, None) == (False, 0.0)
    assert recount.outside(None, 3.0)[0] is True

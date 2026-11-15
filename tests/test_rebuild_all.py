# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""The one-command rebuild: its order, its offline switches and its stop on the first failure."""
import importlib
import subprocess
import sys
from pathlib import Path

import pytest

rebuild = importlib.import_module("scripts.rebuild_all")

ROOT = Path(__file__).resolve().parents[1]

MOON_ORDER = [
    "build_candidates", "build_grazing_cells", "build_latitude_profile", "build_cloud_cells",
    "score_cells", "build_temperature_cells", "validate", "validate_snow_many", "build_moon_cards",
    "build_validation_extras", "check_known_analogs", "build_sunpath_demo", "build_winter_leads",
    "build_access_cells", "make_results",
]
OUTSIDE_ORDER = ["export_site", "export_site_extras", "build_submission"]


def names(steps):
    return [s.name for s in steps]


def test_the_moon_part_runs_in_the_order_its_files_need():
    moon = [s for s in rebuild.plan(ROOT) if s.part == "moon"]
    assert names(moon) == MOON_ORDER


def test_each_step_comes_after_the_steps_whose_files_it_reads():
    order = names(rebuild.plan(ROOT))
    needs = {
        "build_cloud_cells": ["build_grazing_cells"],                      # reads grazing_cells.json
        "score_cells": ["build_grazing_cells", "build_cloud_cells"],       # grazing_bins.npz, cloud_cells.json
        "build_temperature_cells": ["score_cells"],                        # cells_scored.json top_bins_summer_rock
        "validate": ["score_cells"],
        "build_validation_extras": ["build_latitude_profile", "score_cells", "build_cloud_cells"],
        "check_known_analogs": ["score_cells"],
        "build_sunpath_demo": ["score_cells"],                             # ranking.txt
        "make_results": ["validate", "validate_snow_many", "build_winter_leads", "build_access_cells",
                         "build_latitude_profile"],
        "build_submission": ["make_results", "build_validation_extras", "build_moon_cards"],
    }
    for step, before in needs.items():
        for b in before:
            assert order.index(b) < order.index(step), f"{b} must run before {step}"


def test_page_and_submission_come_last_and_only_when_their_scripts_exist(tmp_path):
    full = names(rebuild.plan(ROOT))
    present = [n for n in OUTSIDE_ORDER if (ROOT / "scripts" / f"{n}.py").exists()]
    assert full == MOON_ORDER + present
    (tmp_path / "scripts").mkdir()
    for n in MOON_ORDER:
        (tmp_path / "scripts" / f"{n}.py").write_text("")
    (tmp_path / "scripts" / "build_submission.py").write_text("")
    assert names(rebuild.plan(tmp_path)) == MOON_ORDER + ["build_submission"]


def test_skip_profile_leaves_out_the_latitude_profile_and_nothing_else():
    full = names(rebuild.plan(ROOT))
    short = names(rebuild.plan(ROOT, skip_profile=True))
    assert "build_latitude_profile" in full
    assert short == [n for n in full if n != "build_latitude_profile"]


def test_every_step_that_could_download_is_run_in_its_offline_or_cached_mode():
    args = {s.name: s.args for s in rebuild.plan(ROOT)}
    assert "--offline" in args["build_cloud_cells"]
    assert "--offline" in args["build_temperature_cells"]
    assert "--offline" in args["validate_snow_many"]
    assert "--cached-only" in args["build_winter_leads"]
    assert "--offline" in args["build_access_cells"]
    assert "--refetch" not in args["build_sunpath_demo"]


def test_the_children_get_a_dead_proxy_so_a_forgotten_request_fails_instead_of_downloading():
    env = rebuild.offline_env({"PATH": "/bin", "NO_PROXY": "*"})
    for key in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"):
        assert env[key] == rebuild.DEAD_PROXY
    assert "NO_PROXY" not in env and "no_proxy" not in env
    out = subprocess.run([sys.executable, "-c", "import urllib.request; print(urllib.request.getproxies()['https'])"],
                         env=env, capture_output=True, text=True, check=True).stdout.strip()
    assert out == rebuild.DEAD_PROXY


def test_from_starts_at_the_named_step_and_an_unknown_name_is_refused():
    steps = rebuild.plan(ROOT)
    assert names(rebuild.start_at(steps, "score_cells"))[0] == "score_cells"
    assert len(rebuild.start_at(steps, "score_cells")) == len(steps) - MOON_ORDER.index("score_cells")
    with pytest.raises(SystemExit):
        rebuild.start_at(steps, "no_such_step")


def _stand_ins(tmp_path, bodies):
    (tmp_path / "scripts").mkdir()
    steps = []
    for name, body in bodies:
        (tmp_path / "scripts" / f"{name}.py").write_text(body)
        steps.append(rebuild.Step(name))
    return steps


def test_the_steps_run_in_order_and_each_is_timed(tmp_path):
    mark = "import pathlib, sys; pathlib.Path('order.txt').open('a').write(pathlib.Path(sys.argv[0]).stem + '\\n')\n"
    steps = _stand_ins(tmp_path, [("first", mark), ("second", mark), ("third", mark)])
    lines = []
    times = rebuild.run(steps, tmp_path, out=lines.append)
    assert (tmp_path / "order.txt").read_text().split() == ["first", "second", "third"]
    assert [n for n, _ in times] == ["first", "second", "third"]
    assert all(t >= 0 for _, t in times)
    assert any("second" in line and " s" in line for line in lines)


def test_a_failing_step_stops_the_run_and_says_which_step_and_what_was_not_run(tmp_path):
    steps = _stand_ins(tmp_path, [
        ("ok_step", "open('ok.done', 'w').write('x')\n"),
        ("bad_step", "import sys; sys.exit(3)\n"),
        ("never_step", "open('never.done', 'w').write('x')\n"),
    ])
    lines = []
    with pytest.raises(rebuild.StepFailed) as caught:
        rebuild.run(steps, tmp_path, out=lines.append)
    message = str(caught.value)
    assert "bad_step" in message and "exit code 3" in message
    assert "never_step" in message and "--from bad_step" in message
    assert (tmp_path / "ok.done").exists()
    assert not (tmp_path / "never.done").exists()


def test_a_missing_script_of_the_moon_part_stops_before_anything_runs(tmp_path):
    steps = _stand_ins(tmp_path, [("present", "open('present.done', 'w').write('x')\n")])
    steps.append(rebuild.Step("absent"))
    with pytest.raises(rebuild.StepFailed) as caught:
        rebuild.run(steps, tmp_path, out=lambda line: None)
    assert "absent" in str(caught.value)
    assert not (tmp_path / "present.done").exists()


def test_main_exits_with_a_non_zero_status_on_a_failure(tmp_path, monkeypatch, capsys):
    steps = _stand_ins(tmp_path, [("bad_step", "raise SystemExit(2)\n")])
    monkeypatch.setattr(rebuild, "plan", lambda root, skip_profile=False: steps)
    with pytest.raises(SystemExit) as caught:
        rebuild.main(["--root", str(tmp_path)])
    assert caught.value.code == 1
    assert "STOPPED" in capsys.readouterr().out


def test_list_prints_the_plan_and_runs_nothing(capsys):
    rebuild.main(["--list"])
    out = capsys.readouterr().out
    assert out.index("build_candidates") < out.index("make_results")

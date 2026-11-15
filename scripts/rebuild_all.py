# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Rebuild every data file of the Moon part, in order and offline, then the page data and SUBMISSION.md.

    uv run python scripts/rebuild_all.py                   everything (38 minutes on 14 Nov 2026: 2,259 s)
    uv run python scripts/rebuild_all.py --skip-profile    leave out the latitude profile (19 minutes less)
    uv run python scripts/rebuild_all.py --list            print the steps and stop
    uv run python scripts/rebuild_all.py --from validate   start at that step, for example after a stop

Each step is one script of scripts/, run as its own process from the project root, one after
the other. The time each takes is printed. The first step that fails stops the run, with a
message that names the step, its exit code and the steps that were not run.

No step downloads. Every script that can ask a server is run in its offline or cached mode
(build_cloud_cells, build_temperature_cells and validate_snow_many with --offline,
build_winter_leads with --cached-only, build_access_cells with --offline, build_sunpath_demo
without --refetch). build_moon_cards reads the Diviner table on disk. As a second guard, every
step runs with its web proxy set to a closed local port, so a request that slipped through
fails at once instead of downloading.

The order follows the files each script reads:
  build_candidates          grazing_cells.json (the cell list) -> candidates.json
  build_grazing_cells       horizon, land cover, snow -> grazing_cells.json, grazing_bins.npz
  build_latitude_profile    the Sun alone -> latitude_profile.json (slow; --skip-profile)
  build_cloud_cells         grazing_cells.json + saved NASA POWER answers -> cloud_cells.json
  score_cells               grazing, cloud, terrain, candidates -> cells_scored.json, ranking.txt
  build_temperature_cells   grazing_cells.json, cells_scored.json + saved answers -> temperature_cells.json
  validate                  cells_scored.json, grazing -> validation.json
  validate_snow_many        grazing_bins.npz + station files on disk -> snow_validation_many.json
  build_moon_cards          moon_targets.json + Diviner table -> moon_cards.json
  build_validation_extras   grazing, cells_scored, cloud, latitude profile -> validation_extras.json
  check_known_analogs       cells_scored.json -> data/reference/known_analogs_check.json
  build_sunpath_demo        saved JPL Horizons answers, grazing, ranking.txt -> sunpath_demo.json
  build_winter_leads        grazing, land cover, stored horizons -> winter_leads.json
  build_access_cells        grazing_cells.json + airports table on disk -> access_cells.json (+ report)
  make_results              all of the above -> RESULTS.md
and then, outside the Moon part, when their scripts exist: export_site, export_site_extras
(site/data) and build_submission (SUBMISSION.md).

The two independent checks (scripts/independent_recount.py, scripts/check_against_horizons.py)
are not steps: they check the files this command writes and record what they compared in
data/derived/checks.json. Run them after this command when the Sun code or the cells change.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILE = "build_latitude_profile"
DEAD_PROXY = "http://127.0.0.1:9"       # the discard port: nothing listens, so any request is refused at once
PROXY_KEYS = ("http_proxy", "https_proxy", "ftp_proxy", "all_proxy",
              "HTTP_PROXY", "HTTPS_PROXY", "FTP_PROXY", "ALL_PROXY")


@dataclass(frozen=True)
class Step:
    name: str
    args: tuple[str, ...] = ()
    part: str = "moon"      # "moon": the script must exist; "outside": run only when it exists

    def script(self, root: Path) -> Path:
        return Path(root) / "scripts" / f"{self.name}.py"


MOON_STEPS = (
    Step("build_candidates"),
    Step("build_grazing_cells"),
    Step(PROFILE),
    Step("build_cloud_cells", ("--offline",)),
    Step("score_cells"),
    Step("build_temperature_cells", ("--offline",)),
    Step("validate"),
    Step("validate_snow_many", ("--offline",)),
    Step("build_moon_cards"),
    Step("build_validation_extras"),
    Step("check_known_analogs"),
    Step("build_sunpath_demo"),
    Step("build_winter_leads", ("--cached-only",)),
    Step("build_access_cells", ("--offline", "--report")),
    Step("make_results"),
)
OUTSIDE_STEPS = (
    Step("export_site", part="outside"),
    Step("export_site_extras", part="outside"),
    Step("build_submission", part="outside"),
)


class StepFailed(Exception):
    """A step failed or is missing; the message says which and what was not run."""


def plan(root: Path = ROOT, skip_profile: bool = False) -> list[Step]:
    """The steps in order: every Moon step (less the profile if asked), then the outside steps whose script exists."""
    steps = [s for s in MOON_STEPS if not (skip_profile and s.name == PROFILE)]
    steps += [s for s in OUTSIDE_STEPS if s.script(root).exists()]
    return steps


def start_at(steps: list[Step], name: str | None) -> list[Step]:
    if name is None:
        return list(steps)
    known = [s.name for s in steps]
    if name not in known:
        raise SystemExit(f"--from {name}: no such step; the steps are {', '.join(known)}")
    return list(steps[known.index(name):])


def offline_env(base: dict | None = None) -> dict:
    """The environment of every step: the parent's, with every web proxy pointing at a closed local port."""
    env = dict(os.environ if base is None else base)
    for key in ("no_proxy", "NO_PROXY"):
        env.pop(key, None)
    for key in PROXY_KEYS:
        env[key] = DEAD_PROXY
    env["PYTHONUNBUFFERED"] = "1"
    return env


def _left(steps: list[Step], i: int) -> str:
    rest = [s.name for s in steps[i + 1:]]
    return ", ".join(rest) if rest else "none"


def say(line: str) -> None:
    print(line, flush=True)             # flushed, so the lines stay in order with the steps' own output in a log


def run(steps: list[Step], root: Path = ROOT, runner=subprocess.run, clock=time.monotonic, out=say) -> list[tuple[str, float]]:
    """Run the steps one after the other; return (name, seconds) for each. Raise StepFailed at the first failure."""
    root = Path(root)
    missing = [s.name for s in steps if s.part == "moon" and not s.script(root).exists()]
    if missing:
        raise StepFailed(f"STOPPED before the first step: no script for {', '.join(missing)} in {root / 'scripts'}")
    env = offline_env()
    times = []
    started = clock()
    for i, step in enumerate(steps):
        command = [sys.executable, str(step.script(root)), *step.args]
        out(f"[{i + 1}/{len(steps)}] {step.name} {' '.join(step.args)}".rstrip() + f"  (start {time.strftime('%H:%M:%S')})")
        before = clock()
        try:
            code = runner(command, cwd=root, env=env).returncode
        except OSError as error:
            code, why = None, f"could not be started ({error})"
        else:
            why = f"exit code {code}"
        seconds = clock() - before
        if code != 0:
            raise StepFailed(f"STOPPED: step {i + 1} of {len(steps)}, {step.name}, failed with {why} after {seconds:.1f} s. "
                             f"Steps not run: {_left(steps, i)}. Fix the cause, then start again from this step with "
                             f"--from {step.name}.")
        times.append((step.name, seconds))
        out(f"[{i + 1}/{len(steps)}] {step.name} done in {seconds:.1f} s")
    out(f"all {len(steps)} steps done in {clock() - started:.1f} s")
    return times


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--skip-profile", action="store_true", help="leave out build_latitude_profile (about 19 minutes)")
    parser.add_argument("--from", dest="start", default=None, help="start at this step")
    parser.add_argument("--list", action="store_true", help="print the steps and stop")
    parser.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    steps = start_at(plan(args.root, skip_profile=args.skip_profile), args.start)
    if args.list:
        for i, s in enumerate(steps):
            print(f"{i + 1:2d}. {s.name} {' '.join(s.args)}".rstrip() + ("" if s.part == "moon" else "   (outside the Moon part)"))
        return
    try:
        times = run(steps, args.root)
    except StepFailed as failure:
        print(failure, flush=True)
        raise SystemExit(1)
    print("time per step:")
    for name, seconds in times:
        print(f"  {name:26s} {seconds:8.1f} s")


if __name__ == "__main__":
    main()

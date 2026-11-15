"""The planner export (round 3, features 7 to 11): rehearsal rules and verdicts, the year plan, the low-Sun rose, the skyline.

Hand-made inputs check each rule, the wrap of the three-period stretch, the byte files' order and
unknown values. Three real areas check the rose against a slow loop written here, apart from the script.
"""
import hashlib
import importlib
import json
import re
from pathlib import Path

import numpy as np
import pytest

planner = importlib.import_module("scripts.export_site_planner")

ROOT = Path(__file__).resolve().parents[1]
DERIVED = ROOT / "data" / "derived"
SITE_DATA = ROOT / "site" / "data"
SURVEY = ROOT / "reports" / "Other teams and prior projects survey.md"
N_BINS = 36


def activity(key):
    return next(a for a in planner.ACTIVITIES if a["id"] == key)


def judge(key, **values):
    return planner.evaluate(activity(key), values)


# ---- the rules, on hand-made inputs ----

ROVER_PASS = dict(H30=45.0, B=0.30, P90=12.0, S=0.85)
CREW_PASS = dict(H30=45.0, D=80.0, T=-5.0, S=0.85)


def test_rover_pass_near_fail():
    assert judge("rover", **ROVER_PASS) == "pass"
    assert judge("rover", **{**ROVER_PASS, "H30": 25.0}) == "near"
    assert judge("rover", **{**ROVER_PASS, "P90": 18.0}) == "near"
    assert judge("rover", **{**ROVER_PASS, "S": 0.6}) == "near"
    assert judge("rover", **{**ROVER_PASS, "H30": 10.0}) == "does not pass"
    assert judge("rover", **{**ROVER_PASS, "B": 0.10}) == "does not pass"
    assert judge("rover", **{**ROVER_PASS, "P90": 25.0}) == "does not pass"


def test_rover_thresholds_are_inclusive():
    assert judge("rover", H30=40.0, B=0.25, P90=15.0, S=0.8) == "pass"
    assert judge("rover", H30=20.0, B=0.15, P90=20.0, S=0.5) == "near"


def test_camera_pass_near_fail():
    assert judge("camera", H30=40.0, C=0.3, K=0.7) == "pass"          # 12 clear hours
    assert judge("camera", H30=40.0, C=0.3, K=0.5) == "near"          # terrain takes too much
    assert judge("camera", H30=20.0, C=0.3, K=0.9) == "near"          # 6 clear hours
    assert judge("camera", H30=10.0, C=0.3, K=0.9) == "does not pass"  # 3 clear hours


def test_crew_pass_near_fail():
    assert judge("crew", **CREW_PASS) == "pass"
    assert judge("crew", **{**CREW_PASS, "D": 150.0}) == "near"
    assert judge("crew", **{**CREW_PASS, "T": -15.0}) == "near"
    assert judge("crew", **{**CREW_PASS, "D": 250.0}) == "does not pass"
    assert judge("crew", **{**CREW_PASS, "T": -25.0}) == "does not pass"


def test_lamp_pass_near_fail():
    assert judge("lamp", H30=20.0, C=0.3, D=50.0) == "pass"           # 6 clear hours, close
    assert judge("lamp", H30=20.0, C=0.3, D=300.0) == "near"          # far, but 20 h
    assert judge("lamp", H30=8.0, C=0.3, D=300.0) == "does not pass"


@pytest.mark.parametrize("key,values,missing", [
    ("rover", ROVER_PASS, "S"), ("rover", ROVER_PASS, "P90"), ("rover", ROVER_PASS, "H30"),
    ("camera", dict(H30=40.0, C=0.3, K=0.7), "K"), ("camera", dict(H30=40.0, C=0.3, K=0.7), "C"),
    ("crew", CREW_PASS, "T"), ("crew", CREW_PASS, "D"), ("crew", CREW_PASS, "S"),
    ("lamp", dict(H30=20.0, C=0.3, D=50.0), "C"), ("lamp", dict(H30=20.0, C=0.3, D=50.0), "D"),
])
def test_an_unknown_input_that_matters_gives_cannot_tell(key, values, missing):
    assert judge(key, **{**values, missing: None}) == "cannot tell"


def test_unknown_never_reads_as_does_not_pass_where_it_could_matter():
    # snow unknown (Antarctica) with everything else at pass level: never "does not pass", never "near"
    assert judge("rover", H30=100.0, B=0.9, P90=5.0, S=None) == "cannot tell"
    # every input unknown: cannot tell for every activity
    for one in planner.ACTIVITIES:
        assert planner.evaluate(one, {}) == "cannot tell"


def test_known_inputs_that_fail_both_rules_decide_without_the_unknown_one():
    # no low Sun at all: no snow figure can make it pass or come near
    assert judge("rover", H30=0.0, B=0.9, P90=5.0, S=None) == "does not pass"
    assert judge("camera", H30=0.0, C=None, K=None) == "does not pass"
    # crew work near rule needs no snow figure: an Antarctic area can be near
    assert judge("crew", H30=45.0, D=150.0, T=-5.0, S=None) == "near"


def test_distance_beyond_the_search_counts_as_far():
    beyond = (1500.0, float("inf"))                 # no airfield with scheduled flights within the search
    assert judge("crew", **{**CREW_PASS, "D": beyond}) == "does not pass"
    assert judge("lamp", H30=20.0, C=0.3, D=beyond) == "near"


def test_verdict_codes_never_use_zero():
    assert set(planner.VERDICT_CODES) == {"pass", "near", "does not pass", "cannot tell"}
    assert 0 not in planner.VERDICT_CODES.values()
    assert planner.VERDICT_CODES["cannot tell"] == 255


# ---- the three-period stretch ----

def test_h30_wraps_round_the_year_end():
    hours = np.zeros((1, N_BINS))
    hours[0, [35, 0, 1]] = [10.0, 12.0, 8.0]
    hours[0, 10] = 25.0
    h30, first = planner.best_stretch(hours, planner.stretch_windows(None))
    assert h30[0] == pytest.approx(30.0)
    assert first[0] == 35


def test_h30_in_the_south_stays_inside_the_rock_season():
    season = [33, 34, 35, 0, 1, 2, 3, 4, 5]
    hours = np.zeros((1, N_BINS))
    hours[0, [4, 5]] = [10.0, 10.0]
    hours[0, [6, 7, 8]] = 50.0                     # March: outside the rock season, must not count
    hours[0, [34, 35, 0]] = [3.0, 4.0, 5.0]
    windows = planner.stretch_windows(season)
    assert all(set(w) <= set(season) for w in windows)
    assert [33, 34, 35] in windows and [3, 4, 5] in windows and [4, 5, 6] not in windows
    h30, first = planner.best_stretch(hours, windows)
    assert h30[0] == pytest.approx(20.0)
    assert first[0] == 3


def test_h30_unknown_and_zero():
    hours = np.zeros((2, N_BINS))
    hours[0, 5] = np.nan
    h30, first = planner.best_stretch(hours, planner.stretch_windows(None))
    assert np.isnan(h30[0]) and np.isnan(first[0])
    assert h30[1] == 0.0 and np.isnan(first[1])    # no low Sun: no stretch to name


# ---- skyline and rose bytes ----

def test_skyline_is_the_lowest_open_elevation_bin():
    share = np.zeros((36, 9))
    share[0] = [0.0, 0.2, 0.6, 0.9, 1, 1, 1, 1, 1]     # half the ground sees the Sun from bin 2
    share[1] = 1.0                                      # open right down to the horizon
    share[2] = 0.3                                      # never open for half the ground
    out = planner.skyline_bytes({0: share, 2: np.full((36, 9), np.nan)}, 3)
    assert out.shape == (3, 36) and out.dtype == np.uint8
    assert list(out[0, :3]) == [2, 0, 9]
    assert (out[1] == 255).all()                       # no horizon
    assert (out[2] == 255).all()                       # no land pixel: unknown, not 0


def test_rose_bytes_scale_and_unknown():
    hours = np.zeros((3, 36))
    hours[0, 0], hours[0, 18], hours[0, 9] = 40.0, 10.0, 0.0
    hours[2] = np.nan
    out = planner.rose_bytes(hours)
    assert out.shape == (3, 37) and out.dtype == np.uint8
    assert out[0, 0] == 200 and out[0, 18] == 50 and out[0, 9] == 0 and out[0, 36] == 0
    assert (out[1, :36] == 255).all() and out[1, 36] == 1      # no such hours: a known zero total
    assert (out[2, :36] == 255).all() and out[2, 36] == 255    # unknown total


def fake_minutes(n_lats, elev_bins, per_sector):
    """A Sun table [lats, 36 bins, 36 sectors, 9 elevation bins]: per_sector minutes in every bin, lowest elevation bin."""
    table = np.zeros((n_lats, N_BINS, 36, 9))
    for sector, minutes in per_sector.items():
        table[:, :, sector, elev_bins[0]] = minutes
    return table


def test_rose_loses_the_sectors_behind_a_high_skyline():
    bins = [0, 1, 2, 3]
    minutes = fake_minutes(1, bins, {0: 60.0, 1: 60.0, 18: 60.0})
    blocked_north = np.ones((36, 9))
    blocked_north[[33, 34, 35, 0, 1, 2, 3]] = 0.0
    shares = {0: blocked_north, 1: np.ones((36, 9))}
    odds = np.full((2, N_BINS), 0.5)
    hours = planner.sector_hours(minutes, bins, np.array([0, 0]), np.array([True, True]), odds, shares, south_season=None)
    assert hours[0, 0] == 0.0 and hours[0, 1] == 0.0
    assert hours[0, 18] == pytest.approx(36 * 0.5)            # one hour a period, 36 periods, half the ground snow-free
    assert hours[1, 0] == pytest.approx(36 * 0.5)
    rose = planner.rose_bytes(hours)
    assert rose[0, 0] == 0 and rose[0, 18] == 200


def test_rose_in_the_south_counts_the_rock_season_and_no_snow():
    bins = [0, 1, 2, 3]
    minutes = fake_minutes(1, bins, {18: 60.0})
    season = [33, 34, 35, 0, 1, 2, 3, 4, 5]
    hours = planner.sector_hours(minutes, bins, np.array([0]), np.array([False]), np.full((1, N_BINS), np.nan),
                                 {0: np.ones((36, 9))}, south_season=season)
    assert hours[0, 18] == pytest.approx(len(season))


def test_rose_without_a_horizon_is_unknown():
    bins = [0]
    minutes = fake_minutes(1, bins, {0: 60.0})
    hours = planner.sector_hours(minutes, bins, np.array([0]), np.array([True]), np.full((1, N_BINS), 1.0), {},
                                 south_season=None)
    assert np.isnan(hours).all()


# ---- the rules file ----

def test_rules_document_words_and_sources():
    doc = planner.rules_document(SURVEY.read_text() if SURVEY.exists() else None)
    assert doc["label"] == "our rule of thumb, not an agency standard"
    assert [a["id"] for a in doc["activities"]] == ["rover", "camera", "crew", "lamp"]
    links_2b = planner.section_links(SURVEY.read_text(), "2b") if SURVEY.exists() else None
    for one in doc["activities"]:
        assert one["pass_rule"].startswith("Pass") and one["near_rule"].startswith("Near")
        assert one["inputs"] and all(i["name"] and i["unit"] for i in one["inputs"])
        assert one["suggestions"]
        for s in one["suggestions"]:
            assert s["tag"] in ("done by NASA", "our suggestion")
            if s["tag"] == "done by NASA":
                assert s["source"]["link"].startswith("https://")
                if links_2b is not None:
                    assert s["source"]["link"] in links_2b
            else:
                assert s.get("source") is None
    # every sentence we wrote: at most 25 words, our names for things
    for text in planner.all_words(doc):
        for sentence in re.split(r"(?<=[.!?])\s+", text):
            assert len(sentence.split()) <= 25, sentence
        assert "cell" not in text.lower().split(), text


def test_rules_document_thresholds_match_the_table():
    doc = planner.rules_document(None)
    rover = next(a for a in doc["activities"] if a["id"] == "rover")
    assert {"input": "H30", "op": ">=", "value": 40} in rover["pass"]
    assert {"input": "P90", "op": "<=", "value": 15} in rover["pass"]
    assert "40 h" in rover["pass_rule"] and "15" in rover["pass_rule"]


# ---- the whole export on a small hand-made world ----

TARGETS = [{"id": "malapert", "name": "Malapert Massif", "limit_deg": 5.55, "elev_bins": [0, 1, 2, 3, 4, 5, 6]},
           {"id": "nobile-rim-2", "name": "Nobile Rim 2", "limit_deg": 7.59, "elev_bins": [0, 1, 2, 3, 4, 5, 6, 7, 8]}]
SEASON = [33, 34, 35, 0, 1, 2, 3, 4, 5]
MONTH_OF_BIN = [1 + b // 3 for b in range(N_BINS)]
ODDS = 0.9


def cell(cid, lat, lon, bare, status, horizon=True, region="Somewhere"):
    return {"id": cid, "lat": lat, "lon": lon, "hemisphere": "N" if lat > 0 else "S", "region": region, "bare": bare,
            "land_share": 1.0, "gridded": True, "snow": {"status": status},
            "horizon": {"north_deg": 0.1, "south_deg": 0.1} if horizon else None, "targets": {}}


def write_world(tmp_path: Path) -> dict:
    derived, site = tmp_path / "derived", tmp_path / "site"
    derived.mkdir()
    site.mkdir()
    cells = [cell("70.0_10.0", 70.05, 10.1, 0.5, "measured"),           # A: winter stretch across the new year
             cell("71.0_11.0", 71.05, 11.1, 0.2, "measured"),           # B: most July hours, but too little bare ground
             cell("72.0_12.0", 72.05, 12.1, 0.6, "measured", horizon=False),   # C: no terrain figure
             cell("-70.0_60.0", -70.05, 60.1, 0.6, "unmeasured"),       # D: Antarctica
             cell("73.0_13.0", 73.05, 13.1, 0.5, "measured")]           # E: July hours, an airfield close by
    n = len(cells)
    flat = np.zeros((n, 2, N_BINS), dtype=np.float32)
    flat[0, :, [35, 0, 1]] = 20.0
    flat[1, :, [18, 19, 20]] = 40.0
    flat[2, :, [18, 19, 20]] = 30.0
    flat[3, :, [0, 1, 2]] = 15.0
    flat[3, :, 20] = 90.0                       # outside the rock season: must not count anywhere
    flat[4, :, [18, 19, 20]] = 20.0
    snow_free = flat * ODDS
    snow_free[3] = np.nan
    open_ = snow_free * 0.8
    open_[2] = np.nan
    open_[3] = flat[3] * 0.7
    np.savez(derived / "grazing_bins.npz", ids=np.array([c["id"] for c in cells]),
             targets=np.array([t["id"] for t in TARGETS]), long_flat=flat, long_snow_free=snow_free, long_open=open_)
    meta = {"targets": TARGETS, "stretch_min_h": 2.0, "step_minutes": 1, "year_phases": 1, "summer_bins_south": SEASON}
    (derived / "grazing_cells.json").write_text(json.dumps({"meta": meta, "cells": cells}))
    cloud = {c["id"]: {"cloud_pct": [70.0] * 12} for c in cells}
    cloud["73.0_13.0"]["cloud_pct"][6] = None                       # July cloud unknown at E
    (derived / "cloud_cells.json").write_text(json.dumps({"meta": {}, "cells": cloud}))
    (derived / "temperature_cells.json").write_text(json.dumps(
        {"meta": {}, "cells": {c["id"]: {"t2m_c": [-20.0] * 6 + [5.0] * 3 + [-20.0] * 3} for c in cells}}))
    terrain = {c["id"]: {"p90_slope_deg": 10.0} for c in cells}
    terrain["70.0_10.0"] = {"slope_pixels": 0}                      # A: slope unknown
    (derived / "terrain_cells.json").write_text(json.dumps(terrain))

    def field(km, scheduled):
        return {"name": f"Field {km}", "ident": "XX", "km": km, "scheduled_service": scheduled, "lat": 0, "lon": 0}
    access = {c["id"]: {"nearest": field(300.0, False), "nearest_scheduled": field(400.0, True)} for c in cells}
    access["73.0_13.0"]["nearest_scheduled"] = field(50.0, True)
    access["-70.0_60.0"] = {"nearest": field(60.0, False), "nearest_scheduled": None}
    (derived / "access_cells.json").write_text(json.dumps({"meta": {"max_km": 1500.0}, "cells": access}))
    (derived / "horizon_cells.json").write_text("{}")
    (derived / "snow_free_dekads.npz").write_bytes(b"")             # present; the fake join below stands in for it
    order = ["73.0_13.0", "-70.0_60.0", "72.0_12.0", "71.0_11.0", "70.0_10.0"]   # the page's order differs
    (site / "cells.json").write_text(json.dumps({"ids": order}))
    bins = [{"label": f"p{b}", "first_day": 10 * b + 1, "last_day": 10 * b + 10, "month": MONTH_OF_BIN[b]}
            for b in range(N_BINS)]
    (site / "meta.json").write_text(json.dumps({
        "targets": [{"id": t["id"], "name": t["name"], "short": t["name"]} for t in TARGETS], "bins": bins,
        "seasons": {"rock_season_bins_south": SEASON, "rock_season_text": "27 November to 1 March"}}))
    return {"derived": derived, "site": site, "cells": cells, "order": order}


NO_HORIZON = {"72.0_12.0"}


def fake_inputs(cells, snow_archive=None, horizons=None):
    """Stands in for grazing.cell_inputs: open sky all round, snow-free odds of 0.9 in the north, none in the south."""
    shares = {i: np.ones((36, 9)) for i, c in enumerate(cells) if c["id"] not in NO_HORIZON}
    odds = np.array([[ODDS] * N_BINS if c["lat"] > 0 else [np.nan] * N_BINS for c in cells])
    return {"snow": {"odds": odds}, "shares": shares}


def fake_sun(lats, limits, min_h, step, year_phases=1):
    table = np.zeros((len(limits), len(lats), N_BINS, 36, 9), dtype=np.float32)
    table[:, :, :, 0, 0] = 60.0      # one hour a period with the Sun due north
    table[:, :, :, 18, 0] = 30.0     # half an hour with the Sun due south
    return table


@pytest.fixture
def world(tmp_path):
    w = write_world(tmp_path)
    out = tmp_path / "out"
    report = planner.export(w["derived"], w["site"], out, survey=None, cell_inputs=fake_inputs, sun_table=fake_sun)
    w.update(out=out, report=report)
    return w


def read_rehearsal(out: Path, n: int, t: int, a: int):
    raw = (out / "rehearsal.bin").read_bytes()
    assert len(raw) == n * t * (2 + 1 + a)
    h30 = np.frombuffer(raw, dtype="<u2", count=n * t).reshape(n, t)
    first = np.frombuffer(raw, dtype=np.uint8, count=n * t, offset=2 * n * t).reshape(n, t)
    verdicts = np.frombuffer(raw, dtype=np.uint8, offset=3 * n * t).reshape(n, t, a)
    return h30, first, verdicts


def test_export_writes_every_file(world):
    for name in ("rehearsal_rules.json", "rehearsal.bin", "yearplan.json", "rose.bin", "skyline.bin", "planner.json"):
        assert (world["out"] / name).exists(), name
    index = json.loads((world["out"] / "planner.json").read_text())
    assert index["areas"]["count"] == 5
    assert index["areas"]["ids_sha256"] == hashlib.sha256("\n".join(world["order"]).encode()).hexdigest()
    assert index["targets"] == ["malapert", "nobile-rim-2"]
    assert set(index["files"]) == {"rehearsal_rules.json", "rehearsal.bin", "yearplan.json", "rose.bin", "skyline.bin"}
    assert index["left_out"] == []
    layout = index["files"]["rehearsal.bin"]["layout"]
    assert [b["name"] for b in layout["blocks"]] == ["h30", "first_period", "verdicts"]
    assert layout["blocks"][1]["offset_bytes"] == 2 * 5 * 2 and layout["blocks"][2]["offset_bytes"] == 3 * 5 * 2


def test_binary_files_follow_the_page_order(world):
    n, order = 5, world["order"]
    h30, first, verdicts = read_rehearsal(world["out"], n, 2, 4)
    a = order.index("70.0_10.0")
    assert h30[a, 0] == round(60.0 * ODDS * 0.8 * 10)               # 3 periods of 20 h x odds x terrain, in tenths
    assert first[a, 0] == 35                                       # the stretch wraps round the year end
    e = order.index("73.0_13.0")
    assert h30[e, 0] == round(60.0 * ODDS * 0.8 * 10) and first[e, 0] == 18
    rose = np.frombuffer((world["out"] / "rose.bin").read_bytes(), dtype=np.uint8).reshape(n, 2, 37)
    sky = np.frombuffer((world["out"] / "skyline.bin").read_bytes(), dtype=np.uint8).reshape(n, 36)
    c = order.index("72.0_12.0")
    assert (rose[c, :, :36] == 255).all() and (rose[c, :, 36] == 255).all()
    assert (sky[c] == 255).all() and (sky[a] == 0).all()
    assert rose[a, 0, 0] == 200 and rose[a, 0, 18] == 100


def test_missing_area_fails_loudly(tmp_path):
    w = write_world(tmp_path)
    ids = json.loads((w["site"] / "cells.json").read_text())["ids"] + ["79.9_0.1"]
    (w["site"] / "cells.json").write_text(json.dumps({"ids": ids}))
    with pytest.raises(planner.PlannerError, match="79.9_0.1"):
        planner.export(w["derived"], w["site"], tmp_path / "out", survey=None, cell_inputs=fake_inputs, sun_table=fake_sun)


def test_unknown_stays_unknown_in_the_byte_files(world):
    n, order = 5, world["order"]
    h30, first, verdicts = read_rehearsal(world["out"], n, 2, 4)
    assert not (verdicts == 0).any()
    c = order.index("72.0_12.0")                    # no terrain figure: H30 unknown
    assert (h30[c] == 65535).all() and (first[c] == 255).all()
    rover, camera, crew, lamp = range(4)
    for k in (rover, camera, lamp):
        assert (verdicts[c, :, k] == planner.VERDICT_CODES["cannot tell"]).all()
    # crew work on foot: the nearest airfield with scheduled flights is 400 km away, which fails both rules
    # whatever the hours; the unknown hours did not decide it
    assert (verdicts[c, :, crew] == planner.VERDICT_CODES["does not pass"]).all()
    a = order.index("70.0_10.0")                    # slope unknown: rover driving cannot tell, not "does not pass"
    assert verdicts[a, 0, 0] == planner.VERDICT_CODES["cannot tell"]
    d = order.index("-70.0_60.0")                   # Antarctica: snow unknown, rover cannot pass
    assert verdicts[d, 0, 0] in (planner.VERDICT_CODES["cannot tell"], planner.VERDICT_CODES["does not pass"])
    assert verdicts[d, 0, 0] != planner.VERDICT_CODES["pass"] and verdicts[d, 0, 0] != planner.VERDICT_CODES["near"]


def test_south_h30_ignores_hours_outside_the_rock_season(world):
    h30, first, _ = read_rehearsal(world["out"], 5, 2, 4)
    d = world["order"].index("-70.0_60.0")
    assert h30[d, 0] == round(45.0 * 0.7 * 10) and first[d, 0] == 0


def test_year_plan_names_only_ranked_areas(world):
    plan = json.loads((world["out"] / "yearplan.json").read_text())
    july = plan["targets"]["malapert"]["north"][6]
    assert july["id"] == "73.0_13.0"                # B has more hours but less than a quarter bare ground
    assert july["hours"] == pytest.approx(round(60.0 * ODDS * 0.8, 1))
    assert july["clear_share"] is None              # July cloud unknown: null, never 0
    assert july["snow_free_odds"] == pytest.approx(ODDS)
    assert plan["targets"]["malapert"]["north_reachable"][6]["id"] == "73.0_13.0"
    named = {e["id"] for t in plan["targets"].values() for strip in t.values() if isinstance(strip, list)
             for e in strip if e}
    assert "71.0_11.0" not in named and "72.0_12.0" not in named
    south = plan["targets"]["malapert"]["south"]
    assert south[0]["id"] == "-70.0_60.0" and south[0]["snow"] == "snow not measured"
    assert south[0]["snow_free_odds"] is None
    assert south[6] is None                         # July is outside the rock season
    assert plan["targets"]["malapert"]["south_reachable"][0]["airfield"]["km"] == 60.0
    assert plan["targets"]["malapert"]["north"][3] is None        # April: no area above 5 h
    for text in planner.all_words(plan["words"]):
        for sentence in re.split(r"(?<=[.!?])\s+", text):
            assert len(sentence.split()) <= 25, sentence


# ---- the rose of three real areas against a slow loop written here ----

def slow_rose(minutes, elev_bins, share, odds, bins):
    """Hours per compass sector, one multiplication at a time: Sun minutes x open share x snow-free odds."""
    out = []
    for sector in range(36):
        total = 0.0
        for b in bins:
            hours = 0.0
            for e in elev_bins:
                if minutes[b, sector, e] > 0:
                    hours += minutes[b, sector, e] * share[sector, e] / 60.0
            if odds is not None and hours != 0.0:
                hours *= odds[b]
            total += hours
        out.append(total)
    return np.array(out)


@pytest.mark.skipif(not (DERIVED / "grazing_cells.json").exists() or not (DERIVED / "horizon_cells.json").exists(),
                    reason="the pipeline files are not there")
def test_rose_of_three_real_areas_against_a_slow_loop():
    from twinfinder import grazing, sun
    doc = json.loads((DERIVED / "grazing_cells.json").read_text())
    archive = np.load(DERIVED / "grazing_bins.npz")
    ids = [str(i) for i in archive["ids"]]
    t = [x["id"] for x in doc["meta"]["targets"]].index("malapert")
    target = doc["meta"]["targets"][t]
    season = doc["meta"]["summer_bins_south"]
    long_open = archive["long_open"][:, t].astype(float)
    row = {cid: k for k, cid in enumerate(ids)}

    def pick(test):
        return next(c for c in doc["cells"] if c["id"] in row and isinstance(c.get("horizon"), dict)
                    and "north_deg" in c["horizon"] and test(c, long_open[row[c["id"]]]))
    walled = pick(lambda c, h: c["snow"]["status"] == "measured" and c["lat"] > 68 and c["horizon"]["north_deg"] > 10
                  and np.nansum(h) > 1)
    level = pick(lambda c, h: c["snow"]["status"] == "measured" and abs(c["horizon"]["north_deg"]) < 0.5
                 and abs(c["horizon"]["south_deg"]) < 0.5 and np.nansum(h) > 100)
    south = pick(lambda c, h: c["hemisphere"] == "S" and np.nansum(h[season]) > 50)
    three = [{"id": c["id"], "lat": c["lat"], "lon": c["lon"]} for c in (walled, level, south)]
    joined = grazing.cell_inputs(three, DERIVED / "snow_free_dekads.npz", DERIVED / "horizon_cells.json")
    lats = sorted({c["lat"] for c in three})
    table = sun.long_band_minutes_table(lats, [target["limit_deg"]], doc["meta"]["stretch_min_h"],
                                        doc["meta"]["step_minutes"], year_phases=doc["meta"]["year_phases"])[0]
    lat_of_cell = np.array([lats.index(c["lat"]) for c in three])
    north = np.array([c["lat"] > 0 for c in three])
    fast = planner.sector_hours(table, target["elev_bins"], lat_of_cell, north, joined["snow"]["odds"],
                                joined["shares"], south_season=season)
    for k, c in enumerate(three):
        minutes = table[lat_of_cell[k]].astype(float)
        share = joined["shares"][k]
        odds = joined["snow"]["odds"][k] if north[k] else None
        slow = slow_rose(minutes, target["elev_bins"], share, odds, range(N_BINS) if north[k] else season)
        np.testing.assert_allclose(fast[k], slow, rtol=1e-9, atol=1e-9)
        stored = long_open[row[c["id"]]]
        expected = np.nansum(stored) if north[k] else np.nansum(stored[season])
        assert slow.sum() == pytest.approx(expected, abs=0.05), c["id"]     # the pipeline's own hours
    # a high skyline to the north takes most of the northern Sun away
    minutes = table[lat_of_cell[0]].astype(float)
    bare = slow_rose(minutes, target["elev_bins"], np.ones((36, 9)), joined["snow"]["odds"][0], range(N_BINS))
    near_north = [35, 0]
    assert bare[near_north].sum() > 0
    assert fast[0, near_north].sum() < 0.5 * bare[near_north].sum()


# ---- the files as written into site/data (skipped until the export has run for the page's areas) ----

def written_index():
    path = SITE_DATA / "planner.json"
    if not path.exists() or not (SITE_DATA / "cells.json").exists():
        pytest.skip("site/data/planner.json is not there yet")
    index = json.loads(path.read_text())
    ids = json.loads((SITE_DATA / "cells.json").read_text())["ids"]
    if index["areas"]["ids_sha256"] != hashlib.sha256("\n".join(ids).encode()).hexdigest():
        pytest.skip("planner.json was made for another list of areas: run scripts/export_site_planner.py again")
    return index, ids


def test_written_files_match_the_page_areas():
    index, ids = written_index()
    n, t = len(ids), len(index["targets"])
    sizes = {"rehearsal.bin": n * t * (3 + len(planner.ACTIVITIES)), "rose.bin": n * t * 37, "skyline.bin": n * 36}
    for name, size in sizes.items():
        if name in index["files"]:
            assert (SITE_DATA / name).stat().st_size == size, name
    if "rehearsal.bin" in index["files"]:
        _, _, verdicts = read_rehearsal(SITE_DATA, n, t, len(planner.ACTIVITIES))
        assert not (verdicts == 0).any()
        assert set(np.unique(verdicts)) <= set(planner.VERDICT_CODES.values())
    if "rose.bin" in index["files"]:
        rose = np.frombuffer((SITE_DATA / "rose.bin").read_bytes(), dtype=np.uint8).reshape(n, t, 37)
        assert set(np.unique(rose[:, :, 36])) <= {0, 1, 255}
        given = rose[:, :, 36] == 0
        assert (rose[:, :, :36][given].max(axis=-1) == 200).all()


def test_written_year_plan_names_only_ranked_areas():
    index, ids = written_index()
    if "yearplan.json" not in index["files"]:
        pytest.skip("no year plan was written")
    from twinfinder import score
    records = {c["id"]: c for c in json.loads((DERIVED / "grazing_cells.json").read_text())["cells"]}
    plan = json.loads((SITE_DATA / "yearplan.json").read_text())
    for target in plan["targets"].values():
        for key in ("north", "south", "north_reachable", "south_reachable"):
            for entry in target[key]:
                if entry is None:
                    continue
                assert not score.not_ranked_because(records[entry["id"]]), entry["id"]
                assert ids[entry["area"]] == entry["id"]
                assert entry["hours"] > plan["min_hours"]
                if key.endswith("reachable"):
                    assert entry["airfield"]["km"] <= plan["reach_km"]

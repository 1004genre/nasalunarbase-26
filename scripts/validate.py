# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Checks on the grazing-hours results: named sites, big-picture counts, terrain, old against new, stability, regions, prior use.

Reads data/derived/grazing_cells.json, grazing_bins.npz, cells_scored.json
(run scripts/score_cells.py first), terrain_cells.json, candidates.json (for
the blind sample), cloud_cells.json, light_cells_v1.json, the snow archive and
the lists in data/reference. Writes data/derived/validation.json. Safe to run
again: the file is written beside the old one and renamed into place. Nothing
is downloaded.

Long-window hours are per-day spells (version 3): the stored arrays long_flat,
long_snow_free and long_open of grazing_bins.npz at the stored minimum, and
grazing.long_window_hours_by_bin for the 1 h and 3 h stability variants.
Named sites are reported on their own cell and never enter a gridded count.
"""
import json
import os
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

import numpy as np

from twinfinder import cloud, grazing, grid, reference, score, snow, sun
from twinfinder.grazing import NAMED_SITES_NORTH

DERIVED = Path("data/derived")
REFERENCE = Path("data/reference")
OUT = DERIVED / "validation.json"
OLD_OUT = DERIVED / "validation_v1.json"
LONG_KINDS = ("long_flat", "long_snow_free", "long_open")
ROCK_MARGIN_KM = 8.0
THRESHOLDS_H = (50, 100, 200)             # long-window hours a year
OLD_MIN_USABLE_DAYS = 10.0                # the first method's bar: usable all-day low-Sun days a year
OLD_EXPECTED = [0, 49, 52, 57]            # cells at that bar per target in light_cells_v1.json
OLD_IDS = ["connecting-ridge", "malapert", "mons-mouton", "nobile-rim-2"]   # the four targets of light_cells_v1.json
BARE_SCREENS = (0.15, 0.25, 0.35)
FULL_HOURS_VARIANTS = (100.0, 200.0, 400.0)
SNOW_PIXEL_SCREENS = (1, 4, 7)
STRETCH_VARIANTS_H = (1.0, 2.0, 3.0)
TOP_CELLS = 100
HAUGHTON = (75.38, -89.67)
JULY_BINS = (18, 19, 20)                  # 30 June to 29 July
HAUGHTON_NOTE = ("A NASA-funded rover test used the 24-hour Sun at Haughton crater in July 2001; "
                 "the hours below are what this method gives for the same place and month.")


def load(path: Path, default=None):
    return json.loads(path.read_text()) if path.exists() else default


def write_json(path: Path, value) -> None:
    side = path.with_name(path.name + ".part")
    side.write_text(json.dumps(value, indent=1))
    os.replace(side, path)


def load_bins(path: Path) -> dict:
    """The hours per ten-day bin as plain arrays, read once (an open .npz unpacks an array again on every look)."""
    with np.load(path) as archive:
        return {name: archive[name] for name in archive.files}


def known(value, digits: int = 1):
    """A number for the JSON file: rounded, or None when it cannot be known."""
    value = float(value)
    return round(value, digits) if np.isfinite(value) else None


def bin_sum(hours, bins=None):
    """Hours summed over the ten-day bins (those in bins, if given).

    Unknown (NaN) if a counted bin is unknown, or if no bin of the row is known at all.
    """
    hours = np.asarray(hours, dtype=float)
    counted = hours if bins is None else hours[..., list(bins)]
    out = np.where(np.isfinite(hours).any(axis=-1), counted.sum(axis=-1), np.nan)
    return out if out.ndim else float(out)


def half_year_hours(all_hours, long_hours, winter_bins, summer_bins) -> dict:
    """One kind of hours for the year, the winter half and the summer half: every hour, and inside long spells only."""
    def split(hours) -> dict:
        return {"year": known(bin_sum(hours)), "winter_half": known(bin_sum(hours, winter_bins)),
                "summer_half": known(bin_sum(hours, summer_bins))}
    return {"all": split(all_hours), "long": split(long_hours)}


def calendar_sum(long_hours, bare_km2) -> tuple[np.ndarray, int]:
    """Per ten-day bin, the sum over cells of long-window hours times bare km2.

    Also returns how many cell-bins were unknown and so left out.
    """
    weighted = np.asarray(long_hours, dtype=float).reshape(-1, sun.N_BINS) * np.asarray(bare_km2, dtype=float)[:, None]
    return np.nansum(weighted, axis=0), int(np.isnan(weighted).sum())


def threshold_counts(hours, bare_km2, thresholds=THRESHOLDS_H) -> dict:
    """How many cells, and how much bare ground, reach each level of hours; unknown hours are counted apart."""
    pairs = [(h, a) for h, a in zip(hours, bare_km2) if h is not None]
    out = {str(level): {"cells": sum(h >= level for h, _ in pairs),
                        "bare_km2": round(sum(a for h, a in pairs if h >= level), 1)} for level in thresholds}
    out["cells_counted"], out["unknown_cells"] = len(pairs), len(hours) - len(pairs)
    return out


def region_counts(cells) -> dict:
    """Cells per region, biggest first."""
    return dict(Counter(c["region"] for c in cells).most_common())


def old_usable_counts(light_v1: dict, target_ids, min_days: float = OLD_MIN_USABLE_DAYS) -> dict:
    """Cells per target with at least min_days usable days in the first method's file."""
    return {tid: (sum((per_target[tid]["usable_days"] or 0.0) >= min_days for per_target in light_v1.values())
                  if tid in OLD_IDS else None)
            for tid in target_ids}


def eligible(records, ranking: str, min_bare: float, min_snow_pixels: int, need_horizon: bool) -> list[dict]:
    """The cells of one ranking that pass the screens. The snow-pixel screen applies in the north only."""
    side = "S" if ranking == "south" else "N"
    return [r for r in records if r["hemisphere"] == side
            and not score.not_ranked_because(r, min_bare, need_horizon)
            and (side == "S" or (r["snow"].get("land_pixels") or 0) >= min_snow_pixels)]


def variant_hours(r: dict, tid: str, basis: str, hours: dict | None):
    """The long-window hours a variant reads a cell's light from: the stored ones, or another set by cell id."""
    return hours[r["id"]][tid] if hours is not None else score.light_hours(r["targets"][tid], r["hemisphere"], basis)


def variant_goal(r: dict, tid: str, goal: str, full_hours: float, basis: str, hours: dict | None,
                 published: bool = True):
    """A cell's goal score with a chosen cap, horizon basis or set of hours; None when a factor is unknown.

    Made and rounded the way cells_scored.json makes its scores, so with nothing changed it is the published
    score. published=False gives the score before that rounding, for cutting a long list of near-equal cells.
    """
    t = r["targets"][tid]
    lit = variant_hours(r, tid, basis, hours)
    factors = {"light": score.light_score(lit, full_hours), "terrain": t.get("terrain"),
               "bare": r["bare"], "rock": t.get("rock")}
    return (score.published_goals if published else score.goal_scores)(factors)[goal]


def scored_cells(records, tid, goal, ranking, min_bare=score.RANK_MIN_BARE, full_hours=score.FULL_HOURS,
                 min_snow_pixels=0, basis="open", hours=None, need_horizon=True,
                 published=True) -> tuple[list[dict], dict]:
    cells = eligible(records, ranking, min_bare, min_snow_pixels, need_horizon)
    return cells, {r["id"]: variant_goal(r, tid, goal, full_hours, basis, hours, published) for r in cells}


def variant_sites(records, tid: str, goal: str, ranking: str, top: int = 10, **changes) -> list[dict]:
    """The top sites (one per 50 km) under one set of choices; see scored_cells for what can be changed.

    Equal scores are ordered by the hours the variant uses, as ranking.txt orders them by the stored hours.
    """
    cells, scores = scored_cells(records, tid, goal, ranking, **changes)
    basis, hours = changes.get("basis", "open"), changes.get("hours")
    return score.top_sites(cells, key=lambda r: scores[r["id"]], top=top,
                           tie_key=lambda r: variant_hours(r, tid, basis, hours) or 0.0)


def published_sites(records, tid: str, goal: str, ranking: str, flat: bool = False, top: int = 10) -> list[dict]:
    """The top sites as ranking.txt prints them: the ranked cells of one ranking by their stored goal score."""
    allowed, goals = ("ranked_flat", "goals_flat") if flat else ("ranked", "goals")
    cells = [r for r in records if r["ranking"] == ranking and r[allowed]]
    return score.top_sites(cells, key=lambda r: r["targets"][tid][goals][goal], top=top,
                           tie_key=lambda r: score.tie_hours(r["targets"][tid], r["hemisphere"], "flat" if flat else "open"))


def baseline_differences(records, target_ids, flat: bool) -> list[str]:
    """The rankings whose stability baseline is not, site for site, the top 10 that ranking.txt prints."""
    base = {"basis": "flat", "need_horizon": False} if flat else {}
    return [f"{ranking} {tid} {goal}" for ranking in ("north", "south") for tid in target_ids for goal in score.GOALS
            if [r["id"] for r in variant_sites(records, tid, goal, ranking, **base)]
            != [r["id"] for r in published_sites(records, tid, goal, ranking, flat)]]


def top_cells(records, tid: str, goal: str, ranking: str, count: int = TOP_CELLS, **changes) -> list[dict]:
    """The best cells, neighbours included, with a known score above zero; cut on the score before rounding."""
    cells, scores = scored_cells(records, tid, goal, ranking, published=False, **changes)
    cells = [r for r in cells if scores[r["id"]] is not None and scores[r["id"]] > 0.0]
    return sorted(cells, key=lambda r: (-scores[r["id"]], r["id"]))[:count]


def stability(records, tid: str, goal: str, ranking: str, variants: dict, **base) -> dict:
    """How many of the baseline top sites keep a site within 50 km under each change."""
    baseline = variant_sites(records, tid, goal, ranking, **base)
    out = {"baseline_sites": len(baseline)}
    for label, changes in variants.items():
        out[label] = score.survivors(baseline, variant_sites(records, tid, goal, ranking, **{**base, **changes}))
    return out


def has_horizon(cell: dict) -> bool:
    return bool(cell.get("horizon")) and "skipped" not in cell["horizon"]


def no_horizon_reason(cell: dict) -> str:
    """Why a cell has no horizon, in few words (the stored text of a held-back cell names its tile)."""
    horizon = cell.get("horizon")
    if horizon is None:
        return "no horizon record"
    why = str(horizon.get("skipped", ""))
    if "antimeridian" in why.lower():
        return "window across the antimeridian"
    if why.startswith(score.TILE_NOT_FETCHED):
        return "elevation tile not fetched"
    return why or "unknown"


def long_arrays_at(cells: list[dict], min_h: float, archive: dict, meta: dict, inputs) -> dict:
    """Long-window hours per ten-day bin of every cell, for one minimum spell length.

    At the stored minimum these are the arrays of grazing_bins.npz. Any other minimum is
    worked out by grazing.long_window_hours_by_bin (per-day spells, the same join as the build);
    inputs is grazing.cell_inputs of the same cells, read once for all minimums.
    """
    if float(min_h) == float(meta["stretch_min_h"]):
        return {kind: archive[kind] for kind in LONG_KINDS}
    out = grazing.long_window_hours_by_bin(cells, min_h, targets=meta["targets"], inputs=inputs)
    if list(out["ids"]) != [c["id"] for c in cells]:
        raise ValueError("grazing.long_window_hours_by_bin returned the cells in another order")
    return {kind: out[kind] for kind in LONG_KINDS}


def stretch_hours(records, long: dict, rows: dict, meta: dict, basis: str) -> dict:
    """Each record's light hours per target, summed from one set of long-window arrays (see long_arrays_at).

    North: open hours, or snow-free hours over a flat horizon. South: the rock season only; open hours
    there count the terrain alone, and the flat basis is the Sun over a flat horizon.
    """
    out = {}
    for r in records:
        i, south = rows[r["id"]], r["hemisphere"] == "S"
        name = "long_open" if basis == "open" else ("long_flat" if south else "long_snow_free")
        season = meta["summer_bins_south"] if south else None
        out[r["id"]] = {t["id"]: known(bin_sum(long[name][i, k], season)) for k, t in enumerate(meta["targets"])}
    return out


def recompute_check(records, recomputed: dict, basis: str) -> dict:
    """The recomputed hours at the stored stretch minimum against the cells file: they should agree to rounding."""
    worst, differ_in_known = 0.0, 0
    for r in records:
        for tid, value in recomputed[r["id"]].items():
            stored = score.light_hours(r["targets"][tid], r["hemisphere"], basis)
            if (stored is None) != (value is None):
                differ_in_known += 1
            elif stored is not None:
                worst = max(worst, abs(stored - value))
    return {"largest_difference_h": round(worst, 2), "known_in_one_only": differ_in_known}


CLEAR_FIELDS = ("long_open_hours_clear", "long_open_hours_clear_winter", "long_open_hours_clear_summer",
                "long_summer_rock_open_hours_clear")
SNOW_FIELDS = ("long_snow_free_hours_as_mapped", "long_snow_free_hours_with_rule")


def site_report(name, lat, lon, cells, rows, archive, meta, terrain, self_overlap, bodies, evidence=None,
                scored: dict | None = None) -> dict:
    """One named place on its own cell: ground, snow, the three kinds of hours by half-year, horizon, terrain, rock, cloud."""
    cid = grid.cell_id(lat, lon)
    cell = cells.get(cid)
    rock, body = reference.rock_match(lat, lon, bodies, ROCK_MARGIN_KM)
    report = {"name": name, "lat": lat, "lon": lon, "cell": cid, "rock": {"score": round(rock, 3), "body": body}}
    if evidence is not None:
        report["winter_snow_evidence"] = evidence
    if cell is None:
        return {**report, "in_grazing_cells": False}
    south = cell["hemisphere"] == "S"
    winter, summer = meta["winter_bins_north"], meta["summer_bins_north"]
    if south:
        winter, summer = summer, winter   # the local seasons: the southern summer half is 28 September to 31 March
    land = terrain.get(cid) or {}
    record = (scored or {}).get(cid) or {}
    i, per_target = rows[cid], {}
    for k, t in enumerate(meta["targets"]):
        values = cell["targets"][t["id"]]
        clear = record.get("targets", {}).get(t["id"], {})
        overlap = (land.get("overlap") or {}).get(t["id"])
        per_target[t["id"]] = {
            **{kind: half_year_hours(archive[kind][i, k], archive[f"long_{kind}"][i, k], winter, summer)
               for kind in ("flat", "snow_free", "open")},
            **{key: values[key] for key in ("longest_stretch_h", "best_stretch_bin", "poleward_share", "top_bins",
                                            "all_day_days", "usable_days", "summer_rock_hours",
                                            "long_summer_rock_hours", "long_summer_rock_open_hours")},
            **{key: values.get(key) for key in SNOW_FIELDS},
            **{key: clear.get(key) for key in CLEAR_FIELDS},
            "terrain_overlap": overlap,
            "terrain": known(score.terrain_score(overlap, self_overlap.get(t["id"])) if overlap is not None else np.nan, 3),
        }
    return {**report, "in_grazing_cells": True, "hemisphere": cell["hemisphere"], "region": cell["region"],
            "gridded": cell["gridded"], "bare": cell["bare"], "land_share": cell["land_share"],
            "snow": cell["snow"], "horizon": cell["horizon"],
            "cloud_pct_by_month": (record.get("cloud") or {}).get("pct_by_month"),
            "terrain": {key: land.get(key) for key in ("median_slope_deg", "p90_slope_deg", "relief_m")}
            if "overlap" in land else None,
            "targets": per_target}


def clear_share_of(cells: list[dict], cloud_cells: dict | None) -> np.ndarray:
    """The clear share of the sky per cell and ten-day bin, [cells, 36]; NaN where there is no cloud figure."""
    shares = [cloud.clear_share_by_bin(((cloud_cells or {}).get(c["id"]) or {}).get("cloud_pct")) for c in cells]
    return np.array(shares, dtype=float).reshape(len(cells), sun.N_BINS)


def big_picture(measured: list[dict], rows: dict, archive, meta: dict, scored: dict | None = None,
                cloud_cells: dict | None = None) -> dict:
    """Counts over the measured northern gridded cells: cells and bare km2 at each level of hours, and the calendar.

    Snow-free hours (flat horizon) are counted over every measured cell. Open hours and
    clear-sky hours can only be counted over the measured cells that have a horizon; how many
    have none, and why, is reported beside them. Clear-sky hours are read from the scored records.
    """
    with_horizon = [c for c in measured if has_horizon(c)]
    without = Counter(no_horizon_reason(c) for c in measured if not has_horizon(c))
    index = np.array([rows[c["id"]] for c in measured], dtype=int)
    bare_km2 = np.array([c["bare_km2"] for c in measured])
    h_index = np.array([rows[c["id"]] for c in with_horizon], dtype=int)
    h_bare = np.array([c["bare_km2"] for c in with_horizon], dtype=float)
    share = clear_share_of(with_horizon, cloud_cells)
    scored = scored or {}
    seasons = {"winter_half": "_winter", "summer_half": "_summer", "year": ""}
    out = {}
    for k, t in enumerate(meta["targets"]):
        def counts(group, field, source=None):
            def value(c):
                record = c if source is None else source.get(c["id"], {"targets": {}})
                return record["targets"].get(t["id"], {}).get(field)
            return threshold_counts([value(c) for c in group], [c["bare_km2"] for c in group])
        calendar, unknown = calendar_sum(archive["long_snow_free"][index, k], bare_km2)
        opened = np.asarray(archive["long_open"][h_index, k], dtype=float).reshape(len(with_horizon), sun.N_BINS)
        calendar_open, unknown_open = calendar_sum(opened, h_bare)
        calendar_clear, unknown_clear = calendar_sum(np.where(opened == 0.0, 0.0, opened * share), h_bare)
        out[t["id"]] = {
            "long_snow_free_hours": {s: counts(measured, f"long_snow_free_hours{end}") for s, end in seasons.items()},
            "long_open_hours_among_cells_with_a_horizon": {
                s: counts(with_horizon, f"long_open_hours{end}") for s, end in seasons.items()},
            "long_open_hours_clear_among_cells_with_a_horizon": {
                s: counts(with_horizon, f"long_open_hours_clear{end}", scored) for s, end in seasons.items()},
            "calendar_hours_times_bare_km2": [round(float(v), 1) for v in calendar],
            "calendar_unknown_cell_bins": unknown,
            "calendar_open_hours_times_bare_km2": [round(float(v), 1) for v in calendar_open],
            "calendar_open_unknown_cell_bins": unknown_open,
            "calendar_clear_hours_times_bare_km2": [round(float(v), 1) for v in calendar_clear],
            "calendar_clear_unknown_cell_bins": unknown_clear,
        }
    return {"measured_cells": len(measured), "measured_bare_km2": round(float(bare_km2.sum()), 1),
            "cells_with_a_horizon": len(with_horizon),
            "bare_km2_of_cells_with_a_horizon": round(float(h_bare.sum()), 1),
            "cells_without_a_horizon": {"cells": sum(without.values()), "why": dict(sorted(without.items()))},
            "note": ("long_snow_free_hours counts every measured cell over a flat horizon. The two rows 'among cells with "
                     "a horizon' and the open and clear calendars count only the measured cells that have a terrain "
                     "horizon. Clear-sky hours are open hours times the monthly mean clear share of the sky; that is "
                     "not the chance that a low Sun is visible."),
            "targets": out}


def share_left(cells: list[dict], tid: str) -> list[float]:
    """Per cell, the share of its long-window hours that the terrain leaves: open over flat-horizon hours.

    North: long_open_hours over long_snow_free_hours. South: the same for the rock season.
    Cells without a horizon, without such hours, or with unknown hours are left out.
    """
    out = []
    for c in cells:
        if not has_horizon(c):
            continue
        values = c["targets"][tid]
        opened = score.light_hours(values, c["hemisphere"], "open")
        base = score.light_hours(values, c["hemisphere"], "flat")
        if opened is not None and base:
            out.append(opened / base)
    return out


def spread(values, digits: int = 3) -> dict:
    """How many values, and their 10th, 25th, 50th, 75th and 90th percentiles; None without values."""
    names = ("p10", "p25", "median", "p75", "p90")
    if not len(values):
        return {"cells": 0, **{name: None for name in names}}
    found = np.percentile(np.array(values, dtype=float), [10, 25, 50, 75, 90])
    return {"cells": len(values), **{name: round(float(v), digits) for name, v in zip(names, found)}}


def horizon_medians(cells: list[dict]) -> dict:
    """Median terrain horizon looking north and looking south, over the cells that have one."""
    have = [c["horizon"] for c in cells if has_horizon(c)]

    def median(key):
        return round(float(np.median([h[key] for h in have])), 2) if have else None
    return {"cells": len(have), "north_deg": median("north_deg"), "south_deg": median("south_deg")}


def terrain_share_left(measured: list[dict], south: list[dict], sample_ids: set, targets: list[dict]) -> dict:
    """What the terrain leaves of the long-window hours: the blind sample beside every cell that has a horizon."""
    groups = {"north": {"blind_sample": [c for c in measured if c["id"] in sample_ids], "all_measured": measured},
              "south": {"blind_sample": [c for c in south if c["id"] in sample_ids], "all": south}}
    out = {"note": ("Share = long-window open hours / long-window flat-horizon hours per cell (north: snow-free hours; "
                    "south: rock-season hours), over the cells of the group that have a horizon and any such hours. "
                    "blind_sample: the cells candidates.json marks 'sample', drawn before any score was looked at. "
                    "all_measured / all: every gridded cell of that side. cells_in_group counts the group, "
                    "horizon.cells those of it with a horizon.")}
    for side, named in groups.items():
        out[side] = {name: {"cells_in_group": len(group), "horizon": horizon_medians(group),
                            "without_a_horizon": dict(sorted(Counter(
                                no_horizon_reason(c) for c in group if not has_horizon(c)).items())),
                            **{t["id"]: spread(share_left(group, t["id"])) for t in targets}}
                     for name, group in named.items()}
    return out


def old_against_new(light_v1: dict, north: list[dict], meta: dict) -> dict:
    """Cells with at least ten usable all-day low-Sun days: the first method's file against the corrected Sun and snow."""
    tids = [t["id"] for t in meta["targets"]]
    old = old_usable_counts(light_v1, tids)
    out = {"old_cells_in_file": len(light_v1), "old_expected": dict(zip(OLD_IDS, OLD_EXPECTED)),
           "old_note": "light_cells_v1.json holds the four regions of the first method only; old is null for the others",
           "targets": {}}
    for tid in tids:
        def reach(status):
            return [c for c in north if c["snow"]["status"] == status
                    and (c["targets"][tid]["usable_days"] or 0.0) >= OLD_MIN_USABLE_DAYS]
        new = reach("measured")
        unknown = sum(c["snow"]["status"] == "measured" and c["targets"][tid]["usable_days"] is None for c in north)
        out["targets"][tid] = {"old": old[tid], "new_measured": len(new), "new_measured_unknown": unknown,
                               "new_doubtful": len(reach("doubtful")), "new_measured_regions": region_counts(new)}
    return out


def region_breakdown(scored: list[dict], measured: list[dict], meta: dict, have_horizons: bool) -> dict:
    """Where the best lighting cells are, and where every measured cell with 100 long-window hours in a half-year is."""
    out = {}
    for t in meta["targets"]:
        tid = t["id"]
        top = top_cells(scored, tid, "lighting", "north") if have_horizons else []
        flat = top_cells(measured, tid, "lighting", "north", basis="flat", need_horizon=False)
        full = [c for c in measured if c["bare"] >= score.RANK_MIN_BARE
                and (c["targets"][tid]["long_snow_free_hours"] or 0.0) >= score.FULL_HOURS]
        out[tid] = {
            "measured_cells_with_full_flat_light_and_enough_bare": {
                "cells": len(full), "of_them_with_a_horizon": sum(has_horizon(c) for c in full)},
            "top_cells_lighting_real_horizon": {"cells": len(top), "regions": region_counts(top)},
            "top_cells_lighting_flat_horizon_all_measured": {
                "cells": len(flat), "regions": region_counts(flat),
                "of_them_with_a_horizon": sum(has_horizon(c) for c in flat)},
            "measured_cells_100_long_snow_free_hours_winter_half": region_counts(
                c for c in measured if (c["targets"][tid]["long_snow_free_hours_winter"] or 0.0) >= 100),
            "measured_cells_100_long_snow_free_hours_summer_half": region_counts(
                c for c in measured if (c["targets"][tid]["long_snow_free_hours_summer"] or 0.0) >= 100),
        }
    return out


def odds_layer(cell: dict, layers) -> str:
    """The layer of the snow archive whose odds a cell's hours use: as mapped for measured cells (decision 13)."""
    as_mapped = "probabilities_as_mapped"
    return as_mapped if cell["snow"].get("odds_used") == "as mapped" and as_mapped in layers else "probabilities"


def haughton_july(cells: dict, rows: dict, archive, meta: dict) -> dict:
    """Haughton crater in July: hours in each target's band per ten-day bin, and the snow-free odds."""
    cid = grid.cell_id(*HAUGHTON)
    cell, i = cells[cid], rows[cid]
    snow_archive = np.load(DERIVED / meta["snow_archive"])
    layer = odds_layer(cell, snow_archive.files)
    odds, source = snow.cell_probabilities_filled(snow_archive[layer], int(snow_archive["row0"]),
                                                  int(snow_archive["col0"]), cell["lat"], cell["lon"])
    out = {"note": HAUGHTON_NOTE, "cell": cid, "bins": list(JULY_BINS),
           "dates": [f"{sun.doy_to_label(b * 10 + 1)}-{sun.doy_to_label(b * 10 + 10)}" for b in JULY_BINS],
           "snow_free_odds": [known(odds[b], 3) for b in JULY_BINS], "snow_source": source, "snow_odds_layer": layer,
           "horizon": cell["horizon"], "targets": {}}
    kinds = ("flat", "snow_free", "open", "long_flat", "long_snow_free", "long_open")
    for k, t in enumerate(meta["targets"]):
        out["targets"][t["id"]] = {
            "median_longest_stretch_h": [known(archive["stretch"][i, k, b], 2) for b in JULY_BINS],
            **{f"{kind}_hours": [known(archive[kind][i, k, b]) for b in JULY_BINS] for kind in kinds},
            **{f"{kind}_hours_july": known(np.sum(archive[kind][i, k, list(JULY_BINS)])) for kind in kinds},
        }
    return out


def stability_variants(by_stretch: dict, have_horizons: bool) -> dict:
    variants = {f"bare screen {v:g}": {"min_bare": v} for v in BARE_SCREENS}
    variants.update({f"full marks at {v:g} h": {"full_hours": v} for v in FULL_HOURS_VARIANTS})
    variants.update({f"snow land pixels >= {v}": {"min_snow_pixels": v} for v in SNOW_PIXEL_SCREENS})
    if have_horizons:
        variants["flat horizon instead of real"] = {"basis": "flat"}
    variants.update({f"stretch minimum {v:g} h": {"hours": by_stretch[v]} for v in STRETCH_VARIANTS_H})
    return variants


def main() -> None:
    scored_file = load(DERIVED / "cells_scored.json")
    if not isinstance(scored_file, dict):
        sys.exit("data/derived/cells_scored.json is missing or from the first method: run scripts/score_cells.py first")
    if OUT.exists() and not OLD_OUT.exists() and "meta" not in load(OUT):
        os.replace(OUT, OLD_OUT)   # the first method's file is kept, never overwritten
    cells_file = load(DERIVED / "grazing_cells.json")
    meta, cells = cells_file["meta"], {c["id"]: c for c in cells_file["cells"]}
    archive = load_bins(DERIVED / "grazing_bins.npz")
    rows = {cid: i for i, cid in enumerate(archive["ids"].tolist())}
    records = scored_file["cells"]
    scored = {r["id"]: r for r in records}
    cloud_cells = (load(DERIVED / "cloud_cells.json") or {}).get("cells")
    sample_ids = {c["id"] for c in load(DERIVED / "candidates.json", []) if "sample" in c.get("why", [])}
    terrain = load(DERIVED / "terrain_cells.json", {})
    # A region without a NASA 5 m terrain model has no slopes: its self-overlap is None, so its terrain factor
    # and the goals that use the terrain are unknown (None), never 0.
    self_overlap = {t["id"]: ((t.get("terrain") or {}).get("90m") or {}).get("self_overlap_10km", {}).get("median")
                    for t in load(DERIVED / "moon_targets.json")}
    bodies = load(REFERENCE / "anorthosite_bodies.json", [])
    south_sites = load(REFERENCE / "antarctic_sites.json", [])
    north = [c for c in cells.values() if c["gridded"] and c["hemisphere"] == "N"]
    south = [c for c in cells.values() if c["gridded"] and c["hemisphere"] == "S"]
    measured = [c for c in north if c["snow"]["status"] == "measured"]
    have_horizons = any(has_horizon(r) for r in records)
    basis = "open" if have_horizons else "flat"
    targets = meta["targets"]
    result = {"meta": {"written": datetime.now().isoformat(timespec="seconds"),
                       "cells_scored_written": scored_file["meta"]["written"],
                       "grazing_cells_with_a_horizon": meta.get("horizons"),
                       "scored_records": len(records), "scored_records_with_a_horizon": sum(has_horizon(r) for r in records),
                       "light_basis_of_stability_and_top_cells": basis,
                       "provisional": not have_horizons,
                       "stretch_min_h": meta["stretch_min_h"], "long_rule": meta.get("long_rule"),
                       "full_hours": score.FULL_HOURS, "rank_min_bare": score.RANK_MIN_BARE,
                       "stability_draws_on_records": len(records),
                       "stretch_variants_from": "grazing.long_window_hours_by_bin",
                       "cloud_cells": len(cloud_cells) if cloud_cells is not None else None,
                       "blind_sample_cells": len(sample_ids)},
              "checks": []}

    print("1. NAMED SITES (on their own cells; never in the gridded counts)")
    sites = [(name, lat, lon, None) for name, lat, lon in NAMED_SITES_NORTH]
    sites += [(s["name"], s["lat"], s["lon"], s["winter_snow_evidence"]) for s in south_sites]
    reports = [site_report(name, lat, lon, cells, rows, archive, meta, terrain, self_overlap, bodies, evidence, scored)
               for name, lat, lon, evidence in sites]
    result["named_sites"] = {
        "note": ("Hours per target are flat (no snow, no terrain), snow_free and open, each for the year and the local "
                 "winter and summer halves, as every hour ('all') and inside long spells only ('long'). In the south the "
                 "snow is unmeasured (snow_free is null) and open hours count the terrain only. The *_clear fields "
                 "are typical clear-sky hours from cells_scored.json (open hours times the monthly clear share)."),
        "sites": reports}
    for rep in reports:
        if not rep["in_grazing_cells"]:
            print(f"  {rep['name']}: cell {rep['cell']} is not in grazing_cells.json")
            continue
        horizon = rep["horizon"] if rep["horizon"] and "skipped" not in rep["horizon"] else {}
        label = f" | winter snow: {rep['winter_snow_evidence']}" if "winter_snow_evidence" in rep else ""
        print(f"  {rep['name']} | cell {rep['cell']} | bare {rep['bare']} | snow {rep['snow']['status']} | horizon N/S "
              f"{horizon.get('north_deg')}/{horizon.get('south_deg')} | rock {rep['rock']['score']} ({rep['rock']['body']}){label}")
        for t in targets:
            v = rep["targets"][t["id"]]
            print(f"      {t['id']:17s} long-window hours, year (winter half, summer half): "
                  + "; ".join(f"{kind} {v[kind]['long']['year']} ({v[kind]['long']['winter_half']}, {v[kind]['long']['summer_half']})"
                              for kind in ("flat", "snow_free", "open")) + f"; terrain {v['terrain']}")

    print(f"\n2. BIG PICTURE: {len(measured)} measured northern cells")
    result["big_picture_north"] = big_picture(measured, rows, archive, meta, scored, cloud_cells)
    lacking = result["big_picture_north"]["cells_without_a_horizon"]
    print(f"  with a horizon: {result['big_picture_north']['cells_with_a_horizon']}; without: {lacking['cells']} {lacking['why']}")
    for t in targets:
        b = result["big_picture_north"]["targets"][t["id"]]
        for field, label in (("long_snow_free_hours", "snow-free"), ("long_open_hours_among_cells_with_a_horizon", "open"),
                             ("long_open_hours_clear_among_cells_with_a_horizon", "clear sky")):
            if label != "snow-free" and not result["big_picture_north"]["cells_with_a_horizon"]:
                print(f"  {t['id']:17s} {label:9s} no measured cell has a horizon yet")
                continue
            print(f"  {t['id']:17s} {label:9s} " + " | ".join(
                f"{season} " + ", ".join(f">={level}: {b[field][season][str(level)]['cells']} cells "
                                         f"{b[field][season][str(level)]['bare_km2']:.0f} km2" for level in THRESHOLDS_H)
                for season in ("winter_half", "summer_half", "year")))
        best = sorted(range(sun.N_BINS), key=lambda k: -b["calendar_hours_times_bare_km2"][k])[:3]
        print(f"  {t['id']:17s} calendar peaks (bin: hours x km2): "
              + ", ".join(f"{k}: {b['calendar_hours_times_bare_km2'][k]:.0f}" for k in best)
              + f"; unknown cell-bins left out: {b['calendar_unknown_cell_bins']}")

    print("\n2b. TERRAIN: share of long-window hours left, the blind sample beside every cell with a horizon")
    result["terrain_share_left"] = terrain_share_left(measured, south, sample_ids, targets)
    for side, named in result["terrain_share_left"].items():
        if side == "note":
            continue
        for name, group in named.items():
            print(f"  {side:5s} {name:12s} cells {group['cells_in_group']}, with a horizon {group['horizon']['cells']} "
                  f"(median north {group['horizon']['north_deg']}, south {group['horizon']['south_deg']} deg) | medians: "
                  + ", ".join(f"{t['id']} {group[t['id']]['median']} (n {group[t['id']]['cells']})" for t in targets))

    print("\n3. OLD MEASURE AGAINST NEW: cells with at least 10 usable all-day low-Sun days")
    result["old_against_new"] = old_against_new(load(DERIVED / "light_cells_v1.json", {}), north, meta)
    for t in targets:
        v = result["old_against_new"]["targets"][t["id"]]
        print(f"  {t['id']:17s} old {v['old']} | new, measured {v['new_measured']} (unknown: {v['new_measured_unknown']}; "
              f"doubtful, not counted: {v['new_doubtful']}) | regions of the new: {v['new_measured_regions']}")
    old_counts = [result["old_against_new"]["targets"][tid]["old"] for tid in OLD_IDS]
    result["checks"].append({"check": f"old usable-day counts are {OLD_EXPECTED}", "passed": old_counts == OLD_EXPECTED,
                             "found": old_counts})

    print(f"\n4. STABILITY of the top 10 sites (survivors of the baseline top 10; light basis: {basis})")
    cell_list = cells_file["cells"]
    others = [v for v in STRETCH_VARIANTS_H if float(v) != float(meta["stretch_min_h"])]
    inputs = grazing.cell_inputs(cell_list) if others else None   # snow and horizons, read once for all minimums
    by_stretch = {v: stretch_hours(records, long_arrays_at(cell_list, v, archive, meta, inputs), rows, meta, basis)
                  for v in STRETCH_VARIANTS_H}
    result["recompute_check"] = recompute_check(records, by_stretch[meta["stretch_min_h"]], basis)
    result["checks"].append({"check": "long-window hours recomputed from the ten-day bins match the cells file within 0.1 h",
                             "how": "sum of the long_* arrays of grazing_bins.npz against the long_* fields of cells_scored.json",
                             "passed": result["recompute_check"]["largest_difference_h"] <= 0.1
                             and result["recompute_check"]["known_in_one_only"] == 0,
                             "found": result["recompute_check"]})
    variants = stability_variants(by_stretch, have_horizons)
    base = {} if have_horizons else {"basis": "flat", "need_horizon": False}
    unlike = baseline_differences(records, [t["id"] for t in targets], flat=not have_horizons)
    result["checks"].append({"check": "the stability baseline is the top 10 that ranking.txt prints",
                             "passed": not unlike, "found": unlike})
    result["stability"] = {"note": "survivors: baseline top-10 sites that keep a site within 50 km under the change. "
                                   + ("" if have_horizons else "PROVISIONAL: no horizons yet, so the flat-horizon light is used "
                                      "and the flat-against-real comparison is left out."),
                           "north": {}, "south": {}}
    for ranking in ("north", "south"):
        chosen = {k: v for k, v in variants.items() if ranking == "north" or not k.startswith("snow")}
        for t in targets:
            result["stability"][ranking][t["id"]] = {
                goal: stability(records, t["id"], goal, ranking, chosen, **base) for goal in score.GOALS}
            for goal, counts in result["stability"][ranking][t["id"]].items():
                n = counts["baseline_sites"]
                print(f"  {ranking:5s} {t['id']:17s} {goal:8s} baseline {n:2d} | "
                      + "; ".join(f"{label}: {v}" for label, v in counts.items() if label != "baseline_sites"))

    print(f"\n5. REGIONS of the top {TOP_CELLS} lighting cells per target, and of cells with 100 long-window hours in a half-year")
    result["regions"] = region_breakdown(records, measured, meta, have_horizons)
    for t in targets:
        v = result["regions"][t["id"]]
        full = v["measured_cells_with_full_flat_light_and_enough_bare"]
        print(f"  {t['id']}: {full['cells']} measured cells already have full flat-horizon light marks and bare >= "
              f"{score.RANK_MIN_BARE:g}; {full['of_them_with_a_horizon']} of them have a horizon")
        print(f"      top cells, real horizon ({v['top_cells_lighting_real_horizon']['cells']}): "
              f"{v['top_cells_lighting_real_horizon']['regions']}")
        flat = v["top_cells_lighting_flat_horizon_all_measured"]
        print(f"      top cells, flat horizon, all measured cells ({flat['cells']}; {flat['of_them_with_a_horizon']} "
              f"have a horizon): {flat['regions']}")
        print(f"      >= 100 h winter half: {v['measured_cells_100_long_snow_free_hours_winter_half']}")
        print(f"      >= 100 h summer half: {v['measured_cells_100_long_snow_free_hours_summer_half']}")

    print("\n6. PRIOR USE: Haughton crater, Devon Island, in July")
    result["haughton_july"] = haughton_july(cells, rows, archive, meta)
    h = result["haughton_july"]
    print(f"  {HAUGHTON_NOTE}")
    print(f"  cell {h['cell']}; bins {h['dates']}; snow-free odds {h['snow_free_odds']} ({h['snow_source']})")
    for t in targets:
        v = h["targets"][t["id"]]
        print(f"      {t['id']:17s} flat {v['flat_hours']} | snow-free {v['snow_free_hours']} | open {v['open_hours']} | "
              f"median longest stretch {v['median_longest_stretch_h']} h")
    top_target = h["targets"][targets[-1]["id"]]
    result["checks"].append({"check": "Haughton has grazing hours in July for the highest target and its snow-free odds are known",
                             "passed": (top_target["flat_hours_july"] or 0) > 0 and all(o is not None for o in h["snow_free_odds"]),
                             "found": {"flat_hours_july": top_target["flat_hours_july"], "snow_free_odds": h["snow_free_odds"]}})

    print()
    for check in result["checks"]:
        print(f"  {'PASS' if check['passed'] else 'FAIL'}: {check['check']} (found {check['found']})")
    write_json(OUT, result)
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()

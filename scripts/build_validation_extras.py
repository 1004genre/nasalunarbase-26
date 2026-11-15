"""Numbers for one validation slide and one sensitivity table: what the extra data change.

Reads data/derived/grazing_cells.json, grazing_bins.npz, latitude_profile.json, and, when they are
there, cloud_cells.json, horizon_cells.json, snow_free_dekads.npz and cells_scored.json, plus the
two site lists in data/reference. Writes data/derived/validation_extras.json with four parts:

1. lower_latitude_sites: the places other teams' terrain searches land on and classic analog
   sites below 59 degrees: hours a year with the Sun in each lunar band, the longest unbroken
   spell, and the hours inside spells of two hours or more (flat horizon, twinfinder.sun).
2. latitude_against_full_method: over the measured northern cells, how many reach 100 long-window
   hours on Sun geometry alone, and how many of those still do after snow-free odds, after
   terrain and after typical cloud.
3. known_sites: the known high-latitude analog sites, the named sites and the Antarctic sites:
   long-window open hours per target and where that puts each among the ranked cells.
4. sensitivity: the count of cells reaching 100 summer-half hours when the Sun ceiling, the spell
   rule or refraction change (twinfinder.sun at the cells' latitudes), and with or without snow,
   terrain and the stale-flag snow rule (the data files).

It takes the files as they are: fields of version 3 (per-day spells, both snow odds, cloud) are
used when present and reported as null when absent. Unknown is null, never 0. Safe to run again
at any time: the file is written beside the old one and renamed into place. Run from anywhere:

    uv run python scripts/build_validation_extras.py

Written with AI assistance (Claude).
"""
from __future__ import annotations

import argparse
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from twinfinder import grazing, grid, score, sun

ROOT = Path(__file__).resolve().parents[1]
DERIVED = ROOT / "data" / "derived"
REFERENCE = ROOT / "data" / "reference"
OUT = DERIVED / "validation_extras.json"

THRESHOLD_H = 100.0          # a cell "reaches" a period when it has this many long-window hours in it
HIGH_LAT_DEG = 59.0          # known analog sites poleward of this are looked up in the search
QUARTER = 0.25               # a choice that moves a count by more than this is called out
HOURS_DIGITS = 1             # hours are rounded to this many decimals before they are counted, as in grazing_cells.json
LOWER_THRESHOLDS_H = (50.0, 25.0)   # each step of the funnel also says how many cells keep this many hours
HIGH_FROM, LOW_BELOW = 200.0 / 3.0, 100.0 / 3.0   # percentile thirds: high, middling, low
CEILING_SHIFTS_DEG = (-0.5, 0.5)
SPELL_RULES_H = (1.0, 2.0, 3.0)
V2_RULE = "ten-day bins by median longest spell (version 2)"

# (shift of the Sun ceiling in degrees, shortest spell in hours, refraction on)
VARIANTS = {
    "baseline": (0.0, 2.0, True),
    "ceiling_minus_0.5_deg": (-0.5, 2.0, True),
    "ceiling_plus_0.5_deg": (0.5, 2.0, True),
    "spell_1_h": (0.0, 1.0, True),
    "spell_3_h": (0.0, 3.0, True),
    "refraction_off": (0.0, 2.0, False),
}

TWIN, CLASSIC = "other teams' terrain twin", "classic lower-latitude analog site"
LOWER_SITES = [
    {"name": "Karakoram", "lat": 35.9, "lon": 76.5, "kind": TWIN},
    {"name": "Central Tibet", "lat": 33.0, "lon": 88.0, "kind": TWIN},
    {"name": "Pamir", "lat": 38.5, "lon": 73.5, "kind": TWIN},
    {"name": "Puna de Atacama", "lat": -24.5, "lon": -67.5, "kind": TWIN},
    {"name": "Peruvian Andes", "lat": -13.5, "lon": -71.5, "kind": TWIN},
    {"name": "Atacama near Yungay", "lat": -24.1, "lon": -70.0, "kind": CLASSIC},
    {"name": "Mauna Kea, Hawaii", "lat": 19.8, "lon": -155.5, "kind": CLASSIC},
    {"name": "Lanzarote", "lat": 29.0, "lon": -13.6, "kind": CLASSIC},
    {"name": "San Francisco Volcanic Field, Arizona", "lat": 35.4, "lon": -111.6, "kind": CLASSIC},
    {"name": "Utah desert station", "lat": 38.4, "lon": -110.8, "kind": CLASSIC},
    {"name": "Moses Lake, Washington", "lat": 47.1, "lon": -119.3, "kind": CLASSIC},
]

OPEN_FIELD = {"N": "long_open_hours", "S": "long_summer_rock_open_hours"}      # with terrain (and snow in the north)
FLAT_FIELD = {"N": "long_snow_free_hours", "S": "long_summer_rock_hours"}      # flat horizon (with snow in the north)
NOT_SEARCHED = "cell not among the searched cells (bare ground under 0.15 of the cell, or no land-cover record)"
SANITY_NOTE = ("With so few known lighting analogs this is a sanity check, not a test of the ranking: the "
               "sites were chosen for geology, landforms, life or logistics, never for Sun height.")


# ---- Sun geometry straight from twinfinder.sun ---------------------------------------------------

def year_phases_of(meta: dict) -> int:
    """How many calendars the cells file's Sun tables were averaged over (meta.year_phases); a file without the
    field was made before the phases were added, with one calendar."""
    return int(meta.get("year_phases", 1))


def elevation_edges(lat: float, step_minutes: float = 1, refraction: bool = True, day_offset: float = 0.0) -> np.ndarray:
    """Elevation of the Sun's centre at the edges of each time step of a 365-day year: [365, steps + 1].

    Local solar time, flat horizon, the same days and hours as the tables of twinfinder.sun.
    With refraction the apparent elevation, without it the true one. day_offset moves the
    calendar as the tables' phases do (sun.phase_offsets): the Sun of day d is taken that many
    days later.
    """
    steps = round(1440.0 / step_minutes)
    if steps < 1 or abs(steps * step_minutes - 1440.0) > 1e-6:
        raise ValueError(f"step_minutes must divide the 1440 minutes of a day, got {step_minutes}")
    hours = np.arange(steps + 1) * (step_minutes / 60.0)
    elev, _ = sun.elevation_azimuth(lat, np.arange(1, 366)[:, None] + day_offset, hours[None, :])
    return sun.apparent_elevation_deg(elev) if refraction else elev


def spell_hours_by_bin(elev: np.ndarray, top_deg: float, min_h: float, step_minutes: float) -> np.ndarray:
    """Hours per ten-day bin with the Sun in (0, top_deg] inside unbroken spells of at least min_h hours: [36].

    elev is [365, steps + 1] as elevation_edges gives it. The spells are those of
    sun.steps_in_long_spells (followed through midnight and the year end); within a step the Sun
    moves on a straight line in elevation, as in the tables of twinfinder.sun, so at a ceiling
    that is one of the module's bin edges the result equals sun.long_band_minutes_table. Unlike
    that table the ceiling may be any number, which is what the ceiling test needs.
    """
    keep = sun.steps_in_long_spells(elev, top_deg, 60.0 * min_h, step_minutes)
    day, step = np.nonzero(keep)
    start, end = elev[day, step], elev[day, step + 1]
    low = np.minimum(start, end)
    high = np.maximum(np.maximum(start, end), low + 1e-9)
    minutes = step_minutes * np.clip(np.minimum(high, top_deg) - np.maximum(low, 0.0), 0.0, None) / (high - low)
    per_day = np.bincount(day, weights=minutes, minlength=elev.shape[0])
    day_bin = np.array([sun.bin_index(d) for d in range(1, elev.shape[0] + 1)])
    return np.bincount(day_bin, weights=per_day, minlength=sun.N_BINS) / 60.0


def sensitivity_summer_hours(lat: float, limits: list[float], summer_bins: list[int], step_minutes: float = 1,
                             year_phases: int = 1) -> dict:
    """Summer-half hours inside long spells at one latitude for every variant: {variant: [one value per limit]}.

    The mean over the same calendars as the Sun tables with year_phases (sun.phase_offsets), so that with
    the cells file's meta.year_phases the baseline is the figure of its long_flat hours and every variant is
    set beside it like with like. year_phases=1 is the single calendar.
    """
    offsets = sun.phase_offsets(year_phases)
    out = {name: [0.0] * len(limits) for name in VARIANTS}
    for offset in offsets:
        true = elevation_edges(lat, step_minutes, refraction=False, day_offset=offset)
        seen = sun.apparent_elevation_deg(true)
        for name, (shift, spell, refraction) in VARIANTS.items():
            elev = seen if refraction else true
            for j, limit in enumerate(limits):
                out[name][j] += float(spell_hours_by_bin(elev, limit + shift, spell, step_minutes)[summer_bins].sum())
    return {name: [v / len(offsets) for v in values] for name, values in out.items()}


def _sensitivity_job(job) -> tuple[float, dict]:
    lat, limits, summer_bins, step_minutes, year_phases = job
    return lat, sensitivity_summer_hours(lat, limits, summer_bins, step_minutes, year_phases)


def _long_table_job(job) -> np.ndarray:
    lats, limits, min_h, step_minutes, year_phases = job
    return sun.long_band_minutes_table(lats, limits, min_h, step_minutes, year_phases=year_phases)


def run_jobs(function, jobs: list, workers: int) -> list:
    """Run the jobs in order, in a process pool when more than one worker is asked for."""
    if workers <= 1 or len(jobs) <= 1:
        return [function(job) for job in jobs]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(function, jobs, chunksize=4))


# ---- part 1: lower-latitude sites ---------------------------------------------------------------

def profile_between(profile_rows, lat: float, tid: str) -> dict | None:
    """A target's values of latitude_profile.json read between the two rows that bracket a latitude; None without them."""
    if not profile_rows:
        return None
    below = [r for r in profile_rows if r["lat"] <= lat and tid in r.get("targets", {})]
    above = [r for r in profile_rows if r["lat"] >= lat and tid in r.get("targets", {})]
    if not below or not above:
        return None
    a, b = max(below, key=lambda r: r["lat"]), min(above, key=lambda r: r["lat"])
    if b["lat"] - a["lat"] > 1.0 + 1e-9:
        return None
    part = 0.0 if b["lat"] == a["lat"] else (lat - a["lat"]) / (b["lat"] - a["lat"])
    ta, tb = a["targets"][tid], b["targets"][tid]

    def between(get):
        try:
            x, y = get(ta), get(tb)
        except (KeyError, TypeError):
            return None
        return None if x is None or y is None else round(x + part * (y - x), 2)

    return {"flat_hours": between(lambda t: t["flat_hours"]),
            "long_flat_hours_1h": between(lambda t: t["long_flat_hours"]["1"]),
            "long_flat_hours_2h": between(lambda t: t["long_flat_hours"]["2"]),
            "long_flat_hours_3h": between(lambda t: t["long_flat_hours"]["3"]),
            "rows": [a["lat"], b["lat"]]}


def lower_site(site: dict, targets: list[dict], profile_rows=None, step_minutes: float = 1,
               year_phases: int = sun.YEAR_PHASES) -> dict:
    """One lower-latitude place: for each target the hours in the band, the longest spell and the long-spell hours.

    The tables average year_phases calendars (main passes the cells file's, which latitude_profile.json shares);
    best_day comes from the day-by-day series, which has one calendar only.
    """
    lat, limits = site["lat"], [t["limit_deg"] for t in targets]
    minutes = sun.band_minutes_table([lat], step_minutes=step_minutes, year_phases=year_phases)[0]   # [36, 36, 9]
    longest = sun.longest_spell_hours([lat], limits, step_minutes, year_phases=year_phases)[0]       # [targets]
    by_day = sun.longest_stretch_hours_by_day(lat, limits)                                          # [365, targets]
    long = {h: sun.long_band_minutes_table([lat], limits, h, step_minutes, year_phases=year_phases)[:, 0]
            for h in SPELL_RULES_H}
    per_target = {}
    for j, target in enumerate(targets):
        bins = target["elev_bins"]
        hours = float(minutes[:, :, bins].sum()) / 60.0
        in_spells = {h: float(long[h][j][:, :, bins].sum()) / 60.0 for h in SPELL_RULES_H}
        profile = profile_between(profile_rows, lat, target["id"])
        per_target[target["id"]] = {
            "limit_deg": target["limit_deg"],
            "hours_a_year_in_band": round(hours, 1),
            "mean_minutes_a_day_in_band": round(hours * 60.0 / 365.0, 1),
            "longest_spell_h": round(float(longest[j]), 2),
            "longest_spell_minutes": round(float(longest[j]) * 60.0),
            "best_day": sun.doy_to_label(int(by_day[:, j].argmax()) + 1) if by_day[:, j].max() > 0 else None,
            "hours_in_spells_of_1h": round(in_spells[1.0], 1),
            "hours_in_spells_of_2h": round(in_spells[2.0], 1),
            "hours_in_spells_of_3h": round(in_spells[3.0], 1),
            "has_a_2h_spell": bool(in_spells[2.0] > 0.0),
            "profile_hours_a_year_in_band": None if profile is None else profile["flat_hours"],
            "profile_hours_in_spells_of_2h": None if profile is None else profile["long_flat_hours_2h"],
        }
    return {"name": site["name"], "lat": lat, "lon": site["lon"], "kind": site.get("kind"), "targets": per_target}


def lower_sites_part(targets: list[dict], profile_rows, step_minutes: float, year_phases: int = sun.YEAR_PHASES) -> dict:
    sites = [lower_site(site, targets, profile_rows, step_minutes, year_phases) for site in LOWER_SITES]
    summary = {}
    for target in targets:
        values = [s["targets"][target["id"]] for s in sites]
        summary[target["id"]] = {
            "sites": len(values),
            "sites_with_a_2h_spell": sum(v["has_a_2h_spell"] for v in values),
            "sites_with_a_1h_spell": sum(v["hours_in_spells_of_1h"] > 0.0 for v in values),
            "hours_a_year_in_band_min": min(v["hours_a_year_in_band"] for v in values),
            "hours_a_year_in_band_max": max(v["hours_a_year_in_band"] for v in values),
            "longest_spell_minutes_min": min(v["longest_spell_minutes"] for v in values),
            "longest_spell_minutes_max": max(v["longest_spell_minutes"] for v in values),
            "longest_spell_site": max(sites, key=lambda s: s["targets"][target["id"]]["longest_spell_h"])["name"],
        }
    return {"what": "flat horizon, standard refraction, Sun's apparent centre in (0, limit]; hours per 365-day year "
                    "computed by twinfinder.sun at each site's own latitude (longitude does not enter); the profile_* "
                    "values are read from latitude_profile.json between its two nearest half-degree rows, as a check",
            "sites": sites, "summary": summary}


# ---- arrays of the cells files ---------------------------------------------------------------------

def long_arrays(arrays) -> dict:
    """Long-window hours per ten-day bin [cells, targets, 36]: flat, snow-free and open, and the rule behind them.

    Version 3 files hold them (per-day spells). An older file does not: then they are made by the
    version 2 rule, the hours of the bins whose median longest spell is at least two hours.
    """
    names = set(getattr(arrays, "files", arrays))
    if {"long_flat", "long_snow_free", "long_open"} <= names:
        return {"rule": grazing.LONG_RULE, "long_flat": np.asarray(arrays["long_flat"], dtype=float),
                "long_snow_free": np.asarray(arrays["long_snow_free"], dtype=float),
                "long_open": np.asarray(arrays["long_open"], dtype=float)}
    long = np.asarray(arrays["stretch"], dtype=float) >= grazing.STRETCH_MIN_H
    out = {"rule": V2_RULE}
    for name in ("flat", "snow_free", "open"):
        hours = np.asarray(arrays[name], dtype=float)
        out[f"long_{name}"] = np.where(long | np.isnan(hours), hours, 0.0)     # an unknown bin stays unknown
    return out


def sum_bins(hours, bins=None) -> np.ndarray:
    """Sum over ten-day bins (all, or a list); unknown if a counted bin is unknown or the whole row is."""
    return np.atleast_1d(grazing.total(hours, None if bins is None else list(bins)))


def period_hours(hours, bins=None) -> np.ndarray:
    """sum_bins rounded to one decimal, as grazing_cells.json keeps its hours, so counts agree with counts made on that file."""
    return np.round(sum_bins(hours, bins), HOURS_DIGITS)


def clear_share_table(cloud_cells, ids: list[str]):
    """Clear-sky share per cell and ten-day bin [cells, 36] from the "cells" of cloud_cells.json; None without the file.

    Each bin takes the month of its middle day (bin // 3): share = 1 - cloud percent / 100. NaN where unknown.
    """
    if cloud_cells is None:
        return None
    try:
        from twinfinder import cloud
        by_bin = cloud.clear_share_by_bin
    except Exception:                                    # the cloud module is another owner's and may be absent
        def by_bin(pct):
            if pct is None:
                return [None] * sun.N_BINS
            return [None if pct[b // 3] is None else 1.0 - float(pct[b // 3]) / 100.0 for b in range(sun.N_BINS)]
    table = np.full((len(ids), sun.N_BINS), np.nan)
    for i, cid in enumerate(ids):
        entry = cloud_cells.get(cid)
        if entry is not None:
            table[i] = [np.nan if v is None else v for v in by_bin(entry.get("cloud_pct"))]
    return table


def clear_hours(hours, share) -> np.ndarray:
    """Hours per bin times the clear-sky share; a bin without hours loses none; unknown cloud stays unknown."""
    hours, share = np.asarray(hours, dtype=float), np.asarray(share, dtype=float)
    return np.where(hours == 0.0, 0.0, hours * share)


# ---- counting ---------------------------------------------------------------------------------

def share(count, whole):
    return None if not whole else round(count / whole, 4)


def count_reaching(values, bare_km2, threshold: float = THRESHOLD_H) -> dict:
    """Cells whose known value reaches the threshold, their bare ground, and how many values are unknown."""
    values, km2 = np.asarray(values, dtype=float), np.asarray(bare_km2, dtype=float)
    known = np.isfinite(values)
    reach = known & (np.where(known, values, 0.0) >= threshold)
    return {"cells": int(reach.sum()), "bare_km2": round(float(np.nansum(km2[reach])), 1),
            "unknown_cells": int((~known).sum())}


def count_by_latitude(hours_of_lat: dict, lats, bare_km2, threshold: float = THRESHOLD_H) -> dict:
    """Cells that reach the threshold when every cell takes the hours of its latitude."""
    hours = np.round(np.array([hours_of_lat[float(lat)] for lat in np.asarray(lats, dtype=float)]), HOURS_DIGITS)
    reach = hours >= threshold
    return {"cells": int(reach.sum()), "bare_km2": round(float(np.nansum(np.asarray(bare_km2, dtype=float)[reach])), 1)}


def funnel(steps: list, bare_km2, threshold: float = THRESHOLD_H, also=LOWER_THRESHOLDS_H) -> dict:
    """How many cells still reach the threshold after each step, each step applied to those that passed the one before.

    steps is [(name, hours per cell or None)]. A step without data is null and passes the cells on
    unchanged. A cell whose value is unknown at a step drops out there and is counted as unknown,
    not as failing. Shares: of all cells in scope, of those passing the first step, of those
    passing the step before, and of those passing the step before that have a value here.
    median_share_of_hours_kept is the median, over the cells that passed the step before, of this
    step's hours over that step's hours. still_at_least_h counts the cells that passed the step
    before and keep at least each lower number of hours here.
    """
    km2 = np.asarray(bare_km2, dtype=float)
    out = {"scope": {"cells": int(len(km2)), "bare_km2": round(float(np.nansum(km2)), 1)}}
    passing, first, previous, before = np.ones(len(km2), dtype=bool), None, len(km2), None
    for name, values in steps:
        if values is None:
            out[name] = None
            continue
        values = np.asarray(values, dtype=float)
        known = np.isfinite(values)
        filled = np.where(known, values, 0.0)
        was, unknown = passing, passing & ~known
        kept = None
        if before is not None:
            both = was & known & np.isfinite(before) & (np.where(np.isfinite(before), before, 0.0) > 0.0)
            kept = round(float(np.median(values[both] / before[both])), 3) if both.any() else None
        passing = was & known & (filled >= threshold)
        n = int(passing.sum())
        first = n if first is None else first
        out[name] = {"cells": n, "bare_km2": round(float(np.nansum(km2[passing])), 1),
                     "unknown_cells": int(unknown.sum()), "share_of_scope": share(n, len(km2)),
                     "share_of_sun_alone": share(n, first), "share_of_previous_step": share(n, previous),
                     "share_of_previous_step_with_a_value": share(n, previous - int(unknown.sum())),
                     "median_share_of_hours_kept": kept,
                     "still_at_least_h": {f"{h:g}": int((was & known & (filled >= h)).sum()) for h in also}}
        previous, before = n, values
    return out


def change(base, variant) -> dict:
    """How far a variant's count lies from the baseline's, as a share of the baseline, and whether that is over a quarter."""
    if base is None or variant is None:
        return {"change": None, "moves_more_than_a_quarter": None}
    if base == 0:
        return {"change": None, "moves_more_than_a_quarter": bool(variant != 0)}
    relative = (variant - base) / base
    return {"change": round(relative, 4), "moves_more_than_a_quarter": bool(abs(relative) > QUARTER)}


# ---- where a known site stands ------------------------------------------------------------------

def percentile_below(value, population):
    """Share (in percent) of the known values of a population that lie below a value; equal values count half."""
    if value is None:
        return None
    population = np.asarray(population, dtype=float)
    population = population[np.isfinite(population)]
    if not len(population):
        return None
    below, equal = (population < value).sum(), (population == value).sum()
    return round(100.0 * (below + 0.5 * equal) / len(population), 1)


def rank_from_top(value, population):
    """1 for the most hours: one more than the number of known values above this one."""
    if value is None:
        return None
    population = np.asarray(population, dtype=float)
    return int((population[np.isfinite(population)] > value).sum()) + 1


def verdict(percentile):
    """A percentile in plain words: the top third is high, the bottom third low."""
    if percentile is None:
        return None
    return "high" if percentile >= HIGH_FROM else ("low" if percentile < LOW_BELOW else "middling")


def ranked_cells(cells: list[dict], hemisphere: str, need_horizon: bool = True) -> list[dict]:
    """The cells of one hemisphere that the ranking takes (twinfinder.score.not_ranked_because gives no reason)."""
    return [c for c in cells if c["hemisphere"] == hemisphere
            and not score.not_ranked_because(c, need_horizon=need_horizon)]


def _values(cells: list[dict], tid: str, field: str) -> np.ndarray:
    return np.array([np.nan if c["targets"][tid].get(field) is None else c["targets"][tid][field] for c in cells],
                    dtype=float)


def site_row(site: dict, by_id: dict, targets: list[dict], ranked: dict, rankable: dict, cell_id=grid.cell_id,
             cache: dict | None = None) -> dict:
    """One known site: its cell, its long-window hours per target and where they stand among the ranked cells.

    ranked and rankable are {"N": [cells], "S": [cells]}: the ranked cells (with a horizon) and
    those that would be ranked over a flat horizon. North: open hours are long_open_hours (snow and
    terrain) and the flat figure is long_snow_free_hours. South: the rock season only,
    long_summer_rock_open_hours (terrain) and long_summer_rock_hours; snow is not measured there.
    A site whose cell was not searched, or has no horizon, has null hours, never 0.
    """
    cache = {} if cache is None else cache
    hemisphere = "N" if site["lat"] >= 0 else "S"
    cid = cell_id(site["lat"], site["lon"])
    cell = by_id.get(cid)
    row = {"name": site["name"], "source": site.get("source"), "lat": site["lat"], "lon": site["lon"], "cell": cid,
           "hemisphere": hemisphere, "in_the_search": cell is not None}
    if cell is None:
        row.update(region=None, bare=None, snow_status=None, has_a_horizon=None, cell_ranked=False,
                   not_ranked_because=[NOT_SEARCHED])
    else:
        horizon = cell.get("horizon")
        reasons = score.not_ranked_because(cell)
        row.update(region=cell.get("region"), bare=None if cell.get("bare") is None else round(cell["bare"], 2),
                   snow_status=cell["snow"]["status"],
                   has_a_horizon=isinstance(horizon, dict) and "skipped" not in horizon,
                   cell_ranked=not reasons, not_ranked_because=reasons)
    for key in ("winter_snow_evidence", "analog_for", "tier"):
        if site.get(key) is not None:
            row[key] = site[key]
    row["targets"] = {}
    for target in targets:
        tid = target["id"]
        values = cell["targets"].get(tid, {}) if cell is not None else {}
        hours, flat = values.get(OPEN_FIELD[hemisphere]), values.get(FLAT_FIELD[hemisphere])
        for name, group, field in (("ranked", ranked, OPEN_FIELD), ("rankable", rankable, FLAT_FIELD)):
            if (name, hemisphere, tid) not in cache:
                cache[(name, hemisphere, tid)] = _values(group[hemisphere], tid, field[hemisphere])
        population, flat_population = cache[("ranked", hemisphere, tid)], cache[("rankable", hemisphere, tid)]
        percentile = percentile_below(hours, population)
        row["targets"][tid] = {
            "long_flat_hours": values.get("long_flat_hours"),
            "long_snow_free_hours": values.get("long_snow_free_hours") if hemisphere == "N" else None,
            "long_open_hours": hours, "hours_field": OPEN_FIELD[hemisphere],
            "percentile_among_ranked": percentile, "rank_from_top": rank_from_top(hours, population),
            "ranked_cells": int(np.isfinite(population).sum()), "verdict": verdict(percentile),
            "flat_horizon_hours": flat, "flat_field": FLAT_FIELD[hemisphere],
            "percentile_flat_among_rankable": percentile_below(flat, flat_population),
            "rankable_cells": int(np.isfinite(flat_population).sum()),
        }
    return row


def site_summary(rows: list[dict], targets: list[dict], hemisphere: str) -> dict:
    """Per target: how the sites of one hemisphere come out, each cell counted once."""
    seen, unique = set(), []
    for row in rows:
        if row["hemisphere"] == hemisphere and row["cell"] not in seen:
            seen.add(row["cell"])
            unique.append(row)
    out = {}
    for target in targets:
        found = [r["targets"][target["id"]] for r in unique]
        known = [f["percentile_among_ranked"] for f in found if f["percentile_among_ranked"] is not None]
        words = [f["verdict"] for f in found]
        out[target["id"]] = {"cells_with_a_value": len(known), "cells_without_a_value": len(found) - len(known),
                             "median_percentile": round(float(np.median(known)), 1) if known else None,
                             "high": words.count("high"), "middling": words.count("middling"), "low": words.count("low")}
    return out


def known_sites_part(cells: list[dict], targets: list[dict], known_analogs: list[dict], antarctic: list[dict],
                     scored: dict | None) -> dict:
    by_id = {c["id"]: c for c in cells}
    ranked = {h: ranked_cells(cells, h) for h in ("N", "S")}
    rankable = {h: ranked_cells(cells, h, need_horizon=False) for h in ("N", "S")}
    cache: dict = {}
    groups = {
        "known_analogs_poleward_of_59": [dict(s, source="data/reference/known_analogs.json") for s in known_analogs
                                         if abs(s["lat"]) >= HIGH_LAT_DEG],
        "named_sites_north": [{"name": name, "lat": lat, "lon": lon, "source": "RESULTS.md section (f), named site"}
                              for name, lat, lon in grazing.NAMED_SITES_NORTH],
        "antarctic_sites": [dict(s, source="data/reference/antarctic_sites.json") for s in antarctic],
    }
    rows = {name: [site_row(s, by_id, targets, ranked, rankable, cache=cache) for s in sites]
            for name, sites in groups.items()}
    everything = [r for group in rows.values() for r in group]
    summaries = {"north_all_listed_sites": site_summary(everything, targets, "N"),
                 "south_all_listed_sites": site_summary(everything, targets, "S"),
                 "north_known_analogs_only": site_summary(rows["known_analogs_poleward_of_59"], targets, "N"),
                 "south_known_analogs_only": site_summary(rows["known_analogs_poleward_of_59"], targets, "S")}
    population = {}
    for h in ("N", "S"):
        with_horizon = sum(1 for c in rankable[h] if isinstance(c.get("horizon"), dict) and "skipped" not in c["horizon"])
        population[h] = {"ranked_cells": len(ranked[h]), "cells_rankable_over_a_flat_horizon": len(rankable[h]),
                         "share_of_those_with_a_horizon": share(with_horizon, len(rankable[h])),
                         "ranked_is_a_census": bool(rankable[h]) and with_horizon / len(rankable[h]) >= 0.99}
    if scored is not None:
        records = scored.get("cells", []) if isinstance(scored, dict) else scored
        theirs = {h: {r["id"] for r in records if r.get("ranked") and r.get("hemisphere") == h} for h in ("N", "S")}
        for h in ("N", "S"):
            mine = {c["id"] for c in ranked[h]}
            population[h]["ranked_in_cells_scored_json"] = len(theirs[h])
            population[h]["same_cells_as_cells_scored_json"] = mine == theirs[h]
    return {
        "what": "each site is read on the cell that holds it. North: long_open_hours a year (2 h spells, snow-free "
                "odds, terrain). South: long_summer_rock_open_hours (27 November to 1 March, terrain; snow not "
                "measured). The percentile is the share of the ranked cells of the same hemisphere with fewer such "
                "hours (equal hours count half); high = top third, low = bottom third. percentile_flat_among_rankable "
                "is the same over a flat horizon among every cell that could be ranked without a horizon.",
        "ranked_rule": "gridded, bare ground at least 0.25, a terrain horizon, and in the north measured snow "
                       "(twinfinder.score.not_ranked_because on grazing_cells.json)",
        "caveat": SANITY_NOTE,
        "ranked_population": population, "sites": rows, "summary": summaries,
    }


# ---- part 2: latitude alone against the full method ---------------------------------------------------

def measured_north(cells: list[dict]) -> np.ndarray:
    return np.array([c["hemisphere"] == "N" and c.get("gridded", True) and c["snow"]["status"] == "measured"
                     for c in cells], dtype=bool)


def has_horizon(cells: list[dict]) -> np.ndarray:
    return np.array([isinstance(c.get("horizon"), dict) and "skipped" not in c["horizon"] for c in cells], dtype=bool)


def full_method_part(cells, targets, long, clear, periods: dict) -> dict:
    measured, horizon = measured_north(cells), has_horizon(cells)
    km2 = np.array([np.nan if c.get("bare_km2") is None else c["bare_km2"] for c in cells], dtype=float)
    scopes = {"all_measured_cells": measured, "measured_cells_with_a_horizon": measured & horizon}
    out = {}
    for t, target in enumerate(targets):
        per_period = {}
        for period, bins in periods.items():
            flat, snow = period_hours(long["long_flat"][:, t], bins), period_hours(long["long_snow_free"][:, t], bins)
            open_ = period_hours(long["long_open"][:, t], bins)
            cloud = None if clear is None else period_hours(clear_hours(long["long_open"][:, t], clear), bins)
            per_period[period] = {
                name: funnel([("sun_alone", flat[mask]), ("after_snow", snow[mask]), ("after_terrain", open_[mask]),
                              ("after_cloud", None if cloud is None else cloud[mask])], km2[mask])
                for name, mask in scopes.items()}
        out[target["id"]] = per_period
    coverage = share(int((measured & horizon).sum()), int(measured.sum()))
    return {
        "what": f"measured northern cells (gridded, bare ground at least 0.15, 59 to 84 N, snow status measured). A cell "
                f"reaches a period with at least {THRESHOLD_H:g} long-window hours in it. Steps, each applied to the cells "
                "that passed the one before: sun_alone (flat horizon, long_flat), after_snow (times snow-free odds, "
                "long_snow_free), after_terrain (terrain horizon too, long_open), after_cloud (long_open times the "
                "clear-sky share of the bin's month, NASA POWER CERES cloud amount; mean cloud is not the chance that a "
                "low Sun is visible). unknown_cells passed the step before but have no value at this one (no horizon, "
                "partial snow odds) and are counted in no later step.",
        "threshold_h": THRESHOLD_H, "long_rule": long["rule"],
        "measured_cells": int(measured.sum()), "measured_cells_with_a_horizon": int((measured & horizon).sum()),
        "horizon_coverage": coverage, "with_a_horizon_is_a_census": bool(coverage is not None and coverage >= 0.99),
        "cloud": "present" if clear is not None else None,
        "targets": out,
    }


# ---- part 4: sensitivity ----------------------------------------------------------------------------

def sun_sensitivity(cells, targets, summer_bins, step_minutes: float, workers: int, year_phases: int = 1) -> tuple[dict, dict]:
    """Counts of measured cells reaching the threshold in the summer half for each Sun-geometry variant, per target."""
    measured = measured_north(cells)
    lats = np.array([c["lat"] for c in cells], dtype=float)[measured]
    km2 = np.array([c["bare_km2"] for c in cells], dtype=float)[measured]
    limits = [t["limit_deg"] for t in targets]
    unique = sorted({float(lat) for lat in lats})
    found = dict(run_jobs(_sensitivity_job, [(lat, limits, list(summer_bins), step_minutes, year_phases) for lat in unique],
                          workers))
    out = {}
    for j, target in enumerate(targets):
        rows = {}
        for name, (shift, spell, refraction) in VARIANTS.items():
            counted = count_by_latitude({lat: found[lat][name][j] for lat in unique}, lats, km2)
            rows[name] = {"sun_ceiling_deg": round(target["limit_deg"] + shift, 2), "shortest_spell_h": spell,
                          "refraction": refraction, **counted}
        for name, row in rows.items():
            if name != "baseline":
                row.update(change(rows["baseline"]["cells"], row["cells"]))
        out[target["id"]] = rows
    hours = {target["id"]: np.array([found[float(lat)]["baseline"][j] for lat in lats])
             for j, target in enumerate(targets)}
    return out, hours


def snow_variants(cells, long_flat, archive_path: Path) -> dict | None:
    """Long snow-free hours per bin of the measured northern cells under each set of odds: [cells, targets, 36]; None without the archive."""
    if not archive_path.exists():
        return None
    measured = measured_north(cells)
    snow = grazing.snow_of_cells([c for c, m in zip(cells, measured) if m], np.load(archive_path))
    flat = long_flat[measured]
    out = {}
    for name in ("as_mapped", "with_rule"):
        odds = snow[name]
        out[name] = None if not np.isfinite(odds).any() else np.stack(
            [grazing.snow_free_hours(flat[:, t], odds) for t in range(flat.shape[1])], axis=1)
    return out


def terrain_only(cells, targets, horizon_path: Path, min_h: float, step_minutes: float, workers: int, year_phases: int = 1):
    """Terrain-only long-window hours per bin [cells, targets, 36] for the measured northern cells with a horizon.

    NaN for every other cell. None when the horizon file is missing.
    """
    if not horizon_path.exists():
        return None
    wanted = measured_north(cells) & has_horizon(cells)
    numbers = np.flatnonzero(wanted)
    out = np.full((len(cells), len(targets), sun.N_BINS), np.nan)
    if not len(numbers):
        return out
    chosen = [cells[i] for i in numbers]
    _, shares = grazing.horizons_of_cells(chosen, horizon_path)
    lats = sorted({c["lat"] for c in chosen})
    place = {lat: k for k, lat in enumerate(lats)}
    lat_of_cell = np.array([place[c["lat"]] for c in chosen], dtype=int)
    limits = [t["limit_deg"] for t in targets]
    chunks = [lats[i:i + 8] for i in range(0, len(lats), 8)]
    minutes = np.concatenate(run_jobs(_long_table_job, [(chunk, limits, min_h, step_minutes, year_phases) for chunk in chunks],
                                      workers), axis=1)                                 # [targets, latitudes, 36, 36, 9]
    for t, target in enumerate(targets):
        out[numbers, t] = grazing.terrain_hours(minutes[t], lat_of_cell, shares, target["elev_bins"])
    return out


def data_sensitivity(cells, targets, long, clear, summer_bins, snow_sets, terrain) -> dict:
    """Summer-half counts from the data files with snow, terrain and the snow rule switched on and off, per target."""
    measured, horizon = measured_north(cells), has_horizon(cells)
    km2 = np.array([np.nan if c.get("bare_km2") is None else c["bare_km2"] for c in cells], dtype=float)
    with_horizon = measured & horizon
    inside = horizon[measured]                                     # the measured cells that have a horizon
    out = {}
    for t, target in enumerate(targets):
        def summer(array, mask):
            return period_hours(array[:, t], summer_bins)[mask]

        everyone = {"sun_alone": count_reaching(summer(long["long_flat"], measured), km2[measured]),
                    "with_snow_odds_the_file_uses": count_reaching(summer(long["long_snow_free"], measured), km2[measured])}
        for name in ("as_mapped", "with_rule"):
            hours = None if snow_sets is None or snow_sets[name] is None else snow_sets[name]
            everyone[f"with_snow_{name}"] = None if hours is None else count_reaching(
                period_hours(hours[:, t], summer_bins), km2[measured])
        subset = {"sun_alone": count_reaching(summer(long["long_flat"], with_horizon), km2[with_horizon]),
                  "with_snow_no_terrain": count_reaching(summer(long["long_snow_free"], with_horizon), km2[with_horizon]),
                  "with_terrain_no_snow": None if terrain is None else count_reaching(
                      summer(terrain, with_horizon), km2[with_horizon]),
                  "with_snow_and_terrain": count_reaching(summer(long["long_open"], with_horizon), km2[with_horizon]),
                  "with_snow_terrain_and_cloud": None if clear is None else count_reaching(
                      period_hours(clear_hours(long["long_open"][:, t], clear), summer_bins)[with_horizon], km2[with_horizon])}
        for group in (everyone, subset):
            for name, row in group.items():
                if row is not None and name != "sun_alone":
                    row["against_sun_alone"] = change(group["sun_alone"]["cells"], row["cells"])
        if everyone["with_snow_as_mapped"] is not None and everyone["with_snow_with_rule"] is not None:
            everyone["with_snow_with_rule"]["against_as_mapped"] = change(
                everyone["with_snow_as_mapped"]["cells"], everyone["with_snow_with_rule"]["cells"])
        if subset["with_terrain_no_snow"] is not None:
            subset["with_snow_and_terrain"]["against_snow_no_terrain"] = change(
                subset["with_snow_no_terrain"]["cells"], subset["with_snow_and_terrain"]["cells"])
            subset["with_snow_and_terrain"]["against_terrain_no_snow"] = change(
                subset["with_terrain_no_snow"]["cells"], subset["with_snow_and_terrain"]["cells"])
        if snow_sets is not None and all(snow_sets[n] is not None for n in ("as_mapped", "with_rule")):
            a = period_hours(snow_sets["as_mapped"][:, t], summer_bins)[inside]
            b = period_hours(snow_sets["with_rule"][:, t], summer_bins)[inside]
            subset["snow_rule_among_cells_with_a_horizon"] = {
                "as_mapped": count_reaching(a, km2[with_horizon]), "with_rule": count_reaching(b, km2[with_horizon])}
        out[target["id"]] = {"all_measured_cells": {"cells_in_scope": int(measured.sum()), **everyone},
                             "measured_cells_with_a_horizon": {"cells_in_scope": int(with_horizon.sum()), **subset}}
    return out


EVERYONE, WITH_HORIZON = "all measured cells", "measured cells with a terrain horizon"
SUN_CHOICES = [("ceiling_minus_0.5_deg", "Sun ceiling 0.5 degrees lower"),
               ("ceiling_plus_0.5_deg", "Sun ceiling 0.5 degrees higher"),
               ("spell_1_h", "spells of 1 hour or more instead of 2"),
               ("spell_3_h", "spells of 3 hours or more instead of 2"),
               ("refraction_off", "no refraction")]
DATA_CHOICES = [("all_measured_cells", EVERYONE, "with_snow_as_mapped", "snow-free odds as the maps read"),
                ("all_measured_cells", EVERYONE, "with_snow_with_rule", "snow-free odds with the stale-flag rule"),
                ("measured_cells_with_a_horizon", WITH_HORIZON, "with_snow_no_terrain", "snow-free odds, flat horizon"),
                ("measured_cells_with_a_horizon", WITH_HORIZON, "with_terrain_no_snow", "terrain horizon, no snow"),
                ("measured_cells_with_a_horizon", WITH_HORIZON, "with_snow_and_terrain", "snow-free odds and terrain horizon"),
                ("measured_cells_with_a_horizon", WITH_HORIZON, "with_snow_terrain_and_cloud",
                 "snow-free odds, terrain horizon and typical cloud")]


def sensitivity_table(sun_rows: dict, data_rows: dict) -> list[dict]:
    """One target's sensitivity table as rows: the choice, its count, the baseline it is set against and the change.

    The baseline is always Sun geometry alone (the target's ceiling, spells of 2 h or more, standard
    refraction, flat horizon, no snow) over the same cells. A choice without data has null numbers.
    """
    def row(choice, scope, found, base):
        cells = None if found is None else found["cells"]
        return {"choice": choice, "scope": scope, "cells": cells,
                "bare_km2": None if found is None else found.get("bare_km2"),
                "baseline_cells": base, **change(base, cells)}

    base = sun_rows["baseline"]["cells"]
    table = [{"choice": "baseline: Sun geometry alone", "scope": EVERYONE, "cells": base,
              "bare_km2": sun_rows["baseline"].get("bare_km2"), "baseline_cells": base, "change": None,
              "moves_more_than_a_quarter": None}]
    table += [row(label, EVERYONE, sun_rows.get(name), base) for name, label in SUN_CHOICES]
    for key, scope, name, label in DATA_CHOICES:
        group = data_rows.get(key, {})
        if scope == WITH_HORIZON and name == "with_snow_no_terrain":
            subset = group.get("sun_alone") or {}
            table.append({"choice": "baseline: Sun geometry alone", "scope": WITH_HORIZON, "cells": subset.get("cells"),
                          "bare_km2": subset.get("bare_km2"), "baseline_cells": subset.get("cells"), "change": None,
                          "moves_more_than_a_quarter": None})
        table.append(row(label, scope, group.get(name), (group.get("sun_alone") or {}).get("cells")))
    return table


def big_movers(table: list[dict]) -> list[str]:
    """The choices of a sensitivity table that move the count by more than a quarter, in plain words."""
    return [f"{row['choice']} ({row['scope']}: {row['baseline_cells']} to {row['cells']} cells)"
            for row in table if row["moves_more_than_a_quarter"]]


# ---- the file ---------------------------------------------------------------------------------

def clean(value):
    """A value ready for JSON: numpy numbers as plain ones, NaN and infinity as null."""
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if isinstance(value, np.ndarray):
        return clean(value.tolist())
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, np.integer)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        return float(value) if np.isfinite(value) else None
    return value


def write_json(path: Path, value) -> None:
    side = path.with_name(path.name + ".part")
    side.write_text(json.dumps(clean(value), allow_nan=False, indent=1))
    os.replace(side, path)


def read_json(path: Path):
    return json.loads(path.read_text()) if path.exists() else None


def file_times(paths: list[Path]) -> dict:
    return {p.name: (datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec="seconds") if p.exists() else None)
            for p in paths}


def headlines(targets, part1, part2, part3, part4) -> list[str]:
    """The figures most worth quoting, each as one plain sentence made from the numbers of this run."""
    lines = []
    summary = part1["summary"]
    low, high = targets[0]["id"], targets[-1]["id"]
    with_spell = max(summary[t["id"]]["sites_with_a_2h_spell"] for t in targets)
    lats = [s["lat"] for s in part1["sites"]]
    lines.append(
        f"At the {len(part1['sites'])} lower-latitude places ({abs(min(lats)):g} {'S' if min(lats) < 0 else 'N'} to "
        f"{abs(max(lats)):g} {'S' if max(lats) < 0 else 'N'}) the Sun is in the "
        f"lunar bands for {summary[low]['hours_a_year_in_band_min']:.0f} to {summary[high]['hours_a_year_in_band_max']:.0f} "
        f"hours a year, but {'none has' if with_spell == 0 else str(with_spell) + ' have'} a spell of two hours or more; "
        f"the longest single spell is {summary[high]['longest_spell_minutes_max']} minutes "
        f"({summary[high]['longest_spell_site']}, Sun at or below {targets[-1]['limit_deg']} degrees).")
    census = part2["with_a_horizon_is_a_census"]
    for target in targets:
        tid = target["id"]
        summer = part2["targets"][tid]["summer_half"]
        everyone, subset = summer["all_measured_cells"], summer["measured_cells_with_a_horizon"]
        line = (f"{target['name']} (Sun at or below {target['limit_deg']} degrees), summer half: "
                f"{everyone['sun_alone']['cells']:,} of {everyone['scope']['cells']:,} measured cells reach {THRESHOLD_H:g} "
                f"long-window hours on Sun geometry alone ({everyone['sun_alone']['bare_km2']:,.0f} km2 of bare ground); "
                f"{everyone['after_snow']['cells']:,} of those still do after snow-free odds "
                f"({everyone['after_snow']['bare_km2']:,.0f} km2)")
        if subset["scope"]["cells"]:
            line += (f"; among {'the' if census else 'the ' + format(subset['scope']['cells'], ',') + ' cells that so far have'}"
                     f"{' cells with' if census else ''} a terrain horizon: {subset['sun_alone']['cells']:,} on Sun alone, "
                     f"{subset['after_snow']['cells']:,} after snow, {subset['after_terrain']['cells']:,} after terrain "
                     f"({subset['after_terrain']['bare_km2']:,.0f} km2)")
            if subset["after_cloud"] is not None:
                line += f", {subset['after_cloud']['cells']:,} after typical cloud"
        lines.append(line + ".")
    winter = {t["id"]: part2["targets"][t["id"]]["winter_half"]["all_measured_cells"] for t in targets}
    lines.append("Winter half, targets in order of rising Sun ceiling: " + ", ".join(
        f"{winter[t['id']]['sun_alone']['cells']:,}" for t in targets) + " measured cells reach 100 long-window hours on "
        "Sun geometry alone; after snow-free odds " + ", ".join(
        f"{winter[t['id']]['after_snow']['cells']:,}" for t in targets) + " are left.")
    cloud = part2["targets"][high]["summer_half"]["measured_cells_with_a_horizon"]["after_cloud"]
    if cloud is not None:
        lines.append(
            f"Typical cloud ({targets[-1]['name']}, summer half, cells that reach 100 hours after snow and terrain): the "
            f"median cell keeps {cloud['median_share_of_hours_kept']} of its hours when they are multiplied by the monthly "
            f"clear-sky share; {cloud['cells']:,} keep 100 hours, {cloud['still_at_least_h']['50']:,} keep 50 and "
            f"{cloud['still_at_least_h']['25']:,} keep 25. Mean cloud amount is not the chance that a low Sun is visible.")
    for name, label in (("north_all_listed_sites", "Known and named northern sites"),
                        ("south_all_listed_sites", "Antarctic sites (rock season, snow not measured)")):
        found = part3["summary"][name]
        lines.append(f"{label}, median percentile of long-window open hours among the ranked cells of their hemisphere: "
                     + ", ".join(f"{t['name']} {found[t['id']]['median_percentile']}" for t in targets)
                     + f"; for {targets[-1]['name']} {found[high]['high']} cells come out high, {found[high]['middling']} "
                       f"middling and {found[high]['low']} low. " + SANITY_NOTE)
    for target in targets:
        moved = part4["targets"][target["id"]]["moves_more_than_a_quarter"]
        lines.append(f"{target['name']}: choices that move the summer-half count of cells by more than a quarter: "
                     + ("; ".join(moved) if moved else "none") + ".")
    return lines


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 1))
    parser.add_argument("--step-minutes", type=float, default=None, help="time step of the Sun tables (default: the cells file's)")
    args = parser.parse_args()
    started = time.time()

    cells_path, bins_path = DERIVED / "grazing_cells.json", DERIVED / "grazing_bins.npz"
    profile_path, cloud_path = DERIVED / "latitude_profile.json", DERIVED / "cloud_cells.json"
    horizon_path, snow_path = DERIVED / "horizon_cells.json", DERIVED / "snow_free_dekads.npz"
    scored_path = DERIVED / "cells_scored.json"
    inputs = [cells_path, bins_path, profile_path, cloud_path, horizon_path, snow_path, scored_path,
              REFERENCE / "known_analogs.json", REFERENCE / "antarctic_sites.json"]
    times_before = file_times(inputs)

    grazing_file = json.loads(cells_path.read_text())
    meta, cells = grazing_file["meta"], grazing_file["cells"]
    arrays = np.load(bins_path)
    if [str(i) for i in arrays["ids"]] != [c["id"] for c in cells]:
        raise SystemExit("grazing_cells.json and grazing_bins.npz do not hold the same cells in the same order: one of "
                         "them is being rewritten. Run again in a minute.")
    targets = meta["targets"]
    if [str(t) for t in arrays["targets"]] != [t["id"] for t in targets]:
        raise SystemExit("grazing_cells.json and grazing_bins.npz do not list the same targets. Run again in a minute.")
    step_minutes = args.step_minutes or meta.get("step_minutes") or grazing.STEP_MINUTES
    summer_bins = list(meta.get("summer_bins_north", grazing.SUMMER_BINS_NORTH))
    winter_bins = list(meta.get("winter_bins_north", grazing.WINTER_BINS_NORTH))
    long = long_arrays(arrays)
    per_day = long["rule"] == grazing.LONG_RULE and meta.get("long_rule", grazing.LONG_RULE) == grazing.LONG_RULE
    min_h = float(meta.get("stretch_min_h", grazing.STRETCH_MIN_H))
    phases = year_phases_of(meta)        # every Sun count here averages the calendars the cells file was made with

    profile = read_json(profile_path)
    cloud_file = read_json(cloud_path)
    clear = clear_share_table(None if cloud_file is None else cloud_file.get("cells"), [c["id"] for c in cells])
    scored = read_json(scored_path)

    print("part 1: lower-latitude sites")
    part1 = lower_sites_part(targets, None if profile is None else profile.get("profile"), step_minutes, phases)

    print("part 2: latitude alone against the full method")
    part2 = full_method_part(cells, targets, long, clear,
                             {"winter_half": winter_bins, "summer_half": summer_bins, "year": None})

    print("part 3: known sites")
    part3 = known_sites_part(cells, targets, read_json(REFERENCE / "known_analogs.json") or [],
                             read_json(REFERENCE / "antarctic_sites.json") or [], scored)

    print("part 4: sensitivity (Sun geometry at the cells' latitudes)")
    sun_rows, baseline_hours = sun_sensitivity(cells, targets, summer_bins, step_minutes, args.workers, phases)
    print("part 4: sensitivity (snow odds and terrain from the data files)")
    snow_sets = snow_variants(cells, long["long_flat"], snow_path)
    terrain = terrain_only(cells, targets, horizon_path, min_h, step_minutes, args.workers, phases) if per_day else None
    data_rows = data_sensitivity(cells, targets, long, clear, summer_bins, snow_sets, terrain)

    measured, horizon = measured_north(cells), has_horizon(cells)
    checks = {}
    for t, target in enumerate(targets):
        tid = target["id"]
        file_flat = period_hours(long["long_flat"][:, t], summer_bins)[measured]
        fields = {"after_snow": "long_snow_free_hours_summer", "after_terrain": "long_open_hours_summer"}
        from_fields = {step: sum(1 for c, m in zip(cells, measured) if m and (c["targets"][tid].get(field) or 0.0) >= THRESHOLD_H)
                       for step, field in fields.items()}
        check = {"sun_module_against_file_max_difference_h": round(float(np.abs(file_flat - baseline_hours[tid]).max()), 2),
                 "sun_module_count": sun_rows[tid]["baseline"]["cells"],
                 "file_count": data_rows[tid]["all_measured_cells"]["sun_alone"]["cells"],
                 "summer_count_after_snow_from_the_fields_of_grazing_cells_json": from_fields["after_snow"],
                 "summer_count_after_snow_here": part2["targets"][tid]["summer_half"]["all_measured_cells"]["after_snow"]["cells"],
                 "summer_count_after_terrain_from_the_fields_of_grazing_cells_json": from_fields["after_terrain"],
                 "summer_count_after_terrain_here": part2["targets"][tid]["summer_half"]["all_measured_cells"]["after_terrain"]["cells"]}
        if snow_sets is not None:
            file_snow = long["long_snow_free"][measured, t]
            for name in ("as_mapped", "with_rule"):
                if snow_sets[name] is not None:
                    gap = np.abs(snow_sets[name][:, t] - file_snow)
                    check[f"snow_{name}_against_file_max_difference_h_per_bin"] = (
                        round(float(np.nanmax(gap)), 2) if np.isfinite(gap).any() else None)
        if terrain is not None and snow_sets is not None:
            both = measured & horizon
            odds_name = min((n for n in ("as_mapped", "with_rule") if snow_sets[n] is not None),
                            key=lambda n: check.get(f"snow_{n}_against_file_max_difference_h_per_bin") or 0.0, default=None)
            if odds_name is not None and both.any():
                flat = long["long_flat"][both, t]
                with np.errstate(invalid="ignore", divide="ignore"):
                    odds = np.where(flat > 0.0, snow_sets[odds_name][horizon[measured], t] / np.where(flat > 0.0, flat, 1.0), 0.0)
                rebuilt = np.where(terrain[both, t] == 0.0, 0.0, terrain[both, t] * odds)
                gap = np.abs(rebuilt - long["long_open"][both, t])
                check["terrain_times_snow_against_file_max_difference_h_per_bin"] = (
                    round(float(np.nanmax(gap)), 2) if np.isfinite(gap).any() else None)
                check["snow_odds_the_file_matches"] = odds_name
        checks[tid] = check

    part4 = {
        "what": f"count of measured northern cells with at least {THRESHOLD_H:g} long-window hours in the summer half "
                "(1 April to 27 September). from_the_sun_module: flat horizon, no snow, no terrain, computed by "
                "twinfinder.sun at each cell's latitude; one choice is changed at a time from the baseline (the target's "
                "Sun ceiling, spells of at least 2 h, standard refraction). from_the_data_files: the same count from "
                "grazing_bins.npz with snow and terrain switched on and off; snow as mapped against the stale-flag rule "
                "from snow_free_dekads.npz; terrain without snow from horizon_cells.json. 'change' is the variant's "
                "count over the baseline's, minus 1.",
        "threshold_h": THRESHOLD_H, "step_minutes": step_minutes, "year_phases": phases,
        "terrain_without_snow": "computed" if terrain is not None else None,
        "snow_rule_comparison": "computed" if snow_sets is not None else None,
        "targets": {t["id"]: {"limit_deg": t["limit_deg"], "from_the_sun_module": sun_rows[t["id"]],
                              "from_the_data_files": data_rows[t["id"]],
                              "table": sensitivity_table(sun_rows[t["id"]], data_rows[t["id"]])}
                    for t in targets},
        "checks": checks,
    }
    for rows in part4["targets"].values():
        rows["moves_more_than_a_quarter"] = big_movers(rows["table"])

    times_after = file_times(inputs)
    result = {
        "meta": {
            "written": datetime.now().isoformat(timespec="seconds"),
            "written_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "script": "scripts/build_validation_extras.py", "how_to_run": "uv run python scripts/build_validation_extras.py",
            "targets": [{"id": t["id"], "name": t["name"], "limit_deg": t["limit_deg"]} for t in targets],
            "threshold_h": THRESHOLD_H, "long_rule": long["rule"], "stretch_min_h": min_h, "step_minutes": step_minutes,
            "year_phases": phases,
            "year_phases_meaning": "every Sun count of this file (lower sites, the Sun-geometry variants, terrain without "
                                   "snow) is the mean over the calendars of the cells file's meta.year_phases, like its hours",
            "winter_half": "28 September to 31 March", "summer_half": "1 April to 27 September",
            "version_3_fields": {
                "per_day_long_arrays_in_grazing_bins": long["rule"] == grazing.LONG_RULE,
                "snow_odds_used_field": any("odds_used" in c.get("snow", {}) for c in cells[:50]),
                "long_snow_free_hours_with_rule_field": any(
                    "long_snow_free_hours_with_rule" in v for c in cells[:50] for v in c["targets"].values()),
                "cloud_cells_json": cloud_file is not None,
                "horizons_in_grazing_cells": int(horizon.sum()), "cells": len(cells),
            },
            "input_files_written": times_after,
            "an_input_changed_during_the_run": times_before != times_after,
            "unknown": "null means unknown, never 0",
            "ai_note": "computed by code written with AI assistance (Claude) from open data",
        },
        "lower_latitude_sites": part1,
        "latitude_against_full_method": part2,
        "known_sites": part3,
        "sensitivity": part4,
    }
    result["headlines"] = headlines(targets, part1, part2, part3, part4)
    write_json(OUT, result)
    print(f"wrote {OUT} in {time.time() - started:.0f} s")
    for line in result["headlines"]:
        print(" -", line)
    if times_before != times_after:
        print("NOTE: an input file changed during the run; run again when the data files have settled.")


if __name__ == "__main__":
    main()

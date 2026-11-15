# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Independent recount of every cell's hours. Its own code: it imports nothing of twinfinder.

    uv run python scripts/independent_recount.py                 all cells, record in data/derived/checks.json
    uv run python scripts/independent_recount.py --shift 0.14    also: how far the yearly hours move with the calendar
    uv run python scripts/independent_recount.py --cells 50 --no-write     a quick look at the first 50 cells

What it does, apart from the pipeline (twinfinder/sun.py, grazing.py, snow.py):
- Sun: the Astronomical Almanac low-precision solar longitude (the same published series as the
  project's, written out again here), at the edges of 1-minute steps of local solar time, with
  Saemundsson refraction at standard conditions. Day 0 is 9495.86 days after J2000.0.
- Calendars: the yearly tables are the mean over eight calendars an eighth of a day apart, from
  7/16 day earlier to 7/16 day later (the leap-cycle average of the pipeline, written here again:
  in calendar p the Sun of day d is the Sun of day d + (p + 0.5) / 8 - 0.5).
- Spells: unbroken time with the apparent centre in (0, limit]; crossing times are found by
  straight-line interpolation inside the minute, joined through midnight and the year end; a spell
  counts when it lasts 120 minutes or more. The time inside is sampled every 6 seconds (the Sun
  worked out at each sample) and put into ten-day bin, 10-degree azimuth sector and elevation bin.
- Snow: its own ellipsoidal polar-stereographic projection of the IMS 4 km grid and its own
  3 x 3 / 5 x 5 block reading of data/derived/snow_free_dekads.npz.
- Terrain: the open share per sector and elevation bin is read from data/derived/horizon_cells.json
  (taken as given; this program does not recompute horizons).

It compares, for every cell and target, the six per-bin arrays of grazing_bins.npz and the yearly
fields of grazing_cells.json (all hours and long-window hours; flat, snow-free and open; halves of
the year; the southern rock season; the as-mapped and stale-flag-rule snow figures) and the
poleward share, and the snow summary of every northern cell. A figure is outside when the two
differ by more than the larger of 2 percent and 1 hour a year, or when one is known and the other
is not. The outcome goes to data/derived/checks.json under "independent_recount".

First written by the count check of version 3 (one calendar); the eight-calendar average, the
process pool and the record in checks.json were added for the final run.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

D = Path("data/derived")
CHECKS = D / "checks.json"
EDGES = np.array([0.0, 0.5, 1.0, 1.5, 2.08, 3.0, 4.0, 5.55, 6.11, 7.59])
WINTER_N = list(range(27, 36)) + list(range(0, 9))
SUMMER_N = list(range(9, 27))
ROCK_S = [33, 34, 35, 0, 1, 2, 3, 4, 5]
K = 10                      # samples per minute inside the band
MIN_SPELL_MIN = 120.0
DAY0 = 9495.86              # days from J2000.0 to "day 0": the project's stated convention (2026, mid leap cycle)
PHASES = 8                  # calendars averaged, an eighth of a day apart, centred on DAY0
TOLERANCE = "the larger of 2 percent and 1 hour a year; or known in one and unknown in the other"
ARRAYS = ("flat", "snow_free", "open", "long_flat", "long_snow_free", "long_open")


def phase_offsets(n: int = PHASES) -> list[float]:
    """n calendar offsets in days, 1/n day apart and centred on 0: for eight, -7/16 to +7/16."""
    return [(p + 0.5) / n - 0.5 for p in range(n)]


def declination(n_days, decl: str = "almanac"):
    """Solar declination in radians, n_days from J2000.0."""
    n = np.asarray(n_days, dtype=float)
    if decl == "almanac":
        L = np.radians(280.460 + 0.9856474 * n)
        g = np.radians(357.528 + 0.9856003 * n)
        lam = L + np.radians(1.915) * np.sin(g) + np.radians(0.020) * np.sin(2 * g)
        eps = np.radians(23.439 - 0.0000004 * n)
        return np.arcsin(np.sin(eps) * np.sin(lam))
    T = n / 36525.0                                     # Meeus, chapter 25, low accuracy: a second opinion
    L0 = 280.46646 + 36000.76983 * T + 0.0003032 * T * T
    M = np.radians(357.52911 + 35999.05029 * T - 0.0001537 * T * T)
    C = ((1.914602 - 0.004817 * T - 0.000014 * T * T) * np.sin(M) + (0.019993 - 0.000101 * T) * np.sin(2 * M)
         + 0.000289 * np.sin(3 * M))
    omega = np.radians(125.04 - 1934.136 * T)
    lam = np.radians(L0 + C - 0.00569 - 0.00478 * np.sin(omega))
    eps = np.radians(23.0 + 26.0 / 60 + 21.448 / 3600 - (46.8150 * T + 0.00059 * T * T - 0.001813 * T ** 3) / 3600
                     + 0.00256 * np.cos(omega))
    return np.arcsin(np.sin(eps) * np.sin(lam))


def apparent_elev_az(lat_deg, day, hours, day0=DAY0, decl="almanac"):
    """Apparent elevation (deg) and azimuth (deg from north, clockwise) at local solar time; day 1..365."""
    phi = math.radians(lat_deg)
    dec = declination(day0 + day + (hours - 12.0) / 24.0, decl)
    H = np.radians(15.0 * (hours - 12.0))
    s = math.sin(phi) * np.sin(dec) + math.cos(phi) * np.cos(dec) * np.cos(H)
    true = np.degrees(np.arcsin(np.clip(s, -1, 1)))
    h = np.maximum(true, -2.0)
    lift = 1.02 / np.tan(np.radians(h + 10.3 / (h + 5.11))) / 60.0      # Saemundsson, arc minutes -> degrees
    app = np.where(true < -2.0, true, true + np.maximum(lift, 0.0))
    az_from_south_west = np.arctan2(np.sin(H), np.cos(H) * math.sin(phi) - np.tan(dec) * math.cos(phi))  # Meeus 13.5
    az = (np.degrees(az_from_south_west) + 180.0) % 360.0
    return app, az


def long_steps(a, top, min_minutes):
    """a: apparent elevation at step edges [365, 1441]. True for 1-minute steps that hold part of a long spell."""
    a0, a1 = a[:, :-1].ravel(), a[:, 1:].ravel()
    d = a1 - a0
    safe = np.where(d == 0, 1.0, d)
    u_a, u_b = (0.0 - a0) / safe, (top - a0) / safe
    lo, hi = np.minimum(u_a, u_b), np.maximum(u_a, u_b)
    level = d == 0
    inside_level = (a0 > 0) & (a0 <= top)
    lo = np.where(level, np.where(inside_level, -1.0, 2.0), lo)
    hi = np.where(level, np.where(inside_level, 2.0, 2.0), hi)
    length = np.clip(np.minimum(hi, 1.0) - np.maximum(lo, 0.0), 0.0, None)
    has = length > 0
    begins = has & (lo <= 0.0)
    ends = has & (hi >= 1.0)
    cont = np.roll(ends, 1) & begins
    start = has & ~cont
    if not start.any():
        return (has & (length.sum() >= min_minutes - 1e-6)).reshape(a.shape[0], -1), length.sum()
    sid = np.cumsum(start) - 1
    sid[sid < 0] = sid.max()
    spell_len = np.bincount(sid[has], weights=length[has], minlength=sid.max() + 1)
    keep = has & (spell_len[sid] >= min_minutes - 1e-6)
    return keep.reshape(a.shape[0], -1), float(spell_len.max())


def one_calendar(lat, limits, day0, decl="almanac", min_minutes=MIN_SPELL_MIN):
    """{'all': [L, 36, 36, 9], 'long': [L, 36, 36, 9]} minutes per year by ten-day bin, sector, elevation bin."""
    days = np.arange(1, 366)[:, None]
    edge_h = np.arange(1441)[None, :] / 60.0
    a, _ = apparent_elev_az(lat, days, edge_h, day0, decl)
    a0, a1 = a[:, :-1], a[:, 1:]
    near = (np.maximum(a0, a1) > 0.0) & (np.minimum(a0, a1) < EDGES[-1])
    di, si = np.nonzero(near)
    sub = (np.arange(K) + 0.5) / K
    hrs = (si[:, None] + sub[None, :]) / 60.0
    elev, az = apparent_elev_az(lat, (di + 1)[:, None], hrs, day0, decl)
    ebin = np.searchsorted(EDGES, elev, side="left") - 1          # EDGES[e] < elev <= EDGES[e+1]
    inband = (elev > 0.0) & (elev <= EDGES[-1])
    sector = np.floor(az / 10.0).astype(int) % 36
    tbin = np.minimum(di // 10, 35)[:, None] * np.ones((1, K), dtype=int)
    out = {"all": np.zeros((len(limits), 36, 36, 9)), "long": np.zeros((len(limits), 36, 36, 9)), "longest_h": []}
    for j, top in enumerate(limits):
        keep, longest = long_steps(a, top, min_minutes)
        out["longest_h"].append(longest / 60.0)
        ok = inband & (elev <= top)
        for name, sel in (("all", ok), ("long", ok & keep[di, si][:, None])):
            flat_index = (tbin[sel] * 36 + sector[sel]) * 9 + ebin[sel]
            out[name][j] = np.bincount(flat_index, minlength=36 * 36 * 9).reshape(36, 36, 9) / K
    return out


def year_tables(lat, limits, phases=PHASES, shift=0.0, decl="almanac"):
    """The mean of one_calendar over the phase calendars (spells judged in each calendar, then averaged)."""
    parts = [one_calendar(lat, limits, DAY0 + shift + off, decl) for off in phase_offsets(phases)]
    return {"all": sum(p["all"] for p in parts) / len(parts), "long": sum(p["long"] for p in parts) / len(parts),
            "longest_h": [float(np.mean([p["longest_h"][j] for p in parts])) for j in range(len(limits))]}


def _job(args):
    lat, limits, phases, shift, decl = args
    return lat, year_tables(lat, limits, phases, shift, decl)


# --- snow grid: own projection (polar stereographic on the IMS ellipsoid, true scale at 60 N, centre meridian 80 W)
IMS_A, IMS_RF = 6378137.0, 291.505347349177
IMS_N, IMS_PX = 6144, 4000.0


def ims_rowcol(lat, lon):
    f = 1.0 / IMS_RF
    e = math.sqrt(2 * f - f * f)

    def t(phi):
        return math.tan(math.pi / 4 - phi / 2) / ((1 - e * math.sin(phi)) / (1 + e * math.sin(phi))) ** (e / 2)

    phic = math.radians(60.0)
    mc = math.cos(phic) / math.sqrt(1 - e * e * math.sin(phic) ** 2)
    rho = IMS_A * mc * t(math.radians(lat)) / t(phic)
    lam = math.radians(lon + 80.0)
    x, y = rho * math.sin(lam), -rho * math.cos(lam)
    half = IMS_N * IMS_PX / 2
    return (half - y) / IMS_PX, (x + half) / IMS_PX


def block(arr, row0, col0, lat, lon, reach):
    r, c = ims_rowcol(lat, lon)
    r, c = int(math.floor(r)) - row0, int(math.floor(c)) - col0
    return arr[..., max(r - reach, 0):max(r + reach + 1, 0), max(c - reach, 0):max(c + reach + 1, 0)]


def odds_of(arr, row0, col0, lat, lon):
    """Mean over the block's land pixels per bin; 3 x 3, or 5 x 5 when the 3 x 3 has no land pixel at all."""
    for reach, name in ((1, "3x3"), (2, "5x5")):
        b = block(arr, row0, col0, lat, lon, reach).reshape(arr.shape[0], -1)
        if np.isfinite(b).any():
            out = np.full(arr.shape[0], np.nan)
            for k in range(arr.shape[0]):
                v = b[k][np.isfinite(b[k])]
                if len(v):
                    out[k] = float(np.mean(v.astype(float)))
            land = int(np.isfinite(b).any(axis=0).sum())
            return out, name, reach, land
    return np.full(arr.shape[0], np.nan), None, None, 0


def snow_free(hours, odds):
    some = np.isfinite(odds).any()
    return np.where((hours == 0.0) & some, 0.0, hours * odds)


def tot(x, bins=None):
    x = np.asarray(x, dtype=float)
    if not np.isfinite(x).any():
        return float("nan")
    return float(x.sum() if bins is None else x[bins].sum())


def centre_of(cid):
    lat0, lon0 = (float(p) for p in cid.split("_"))
    a = abs(lat0)
    w = 2 if a < 64.5 else 3 if a < 73 else 5 if a < 78 else 6 if a < 84 else 12
    return lat0 + 0.05, lon0 + w * 0.1 / 2


def recompute(cell, targets, tb, snow, horizons):
    """My figures for one cell: per target arrays [36] and the yearly sums."""
    lat, lon = cell["lat"], cell["lon"]
    north = lat >= 0
    status = cell["snow"]["status"]
    mine_snow = {}
    odds = np.full(36, np.nan)
    rule = mapped = np.full(36, np.nan)
    if north:
        rule, src, reach, land = odds_of(snow["probabilities"], snow["row0"], snow["col0"], lat, lon)
        stuck = 0
        if reach:
            sb = block(snow["stuck_winters"], snow["row0"], snow["col0"], lat, lon, reach)
            stuck = int(sb.max()) if sb.size else 0
        my_status = "no data" if src is None else "doubtful" if ((stuck >= 1 and lat >= 67.4) or stuck >= 3) else "measured"
        mapped, msrc, mreach, mland = odds_of(snow["probabilities_as_mapped"], snow["row0"], snow["col0"], lat, lon)
        if status == "measured":
            odds, used_land, used_block = mapped, mland, msrc
        elif status == "doubtful":
            odds, used_land, used_block = rule, land, src
        else:
            used_land, used_block = land, src
        mine_snow = {"status": my_status, "source": src, "stuck_winters": stuck, "land_pixels": used_land,
                     "block_pixels": {"3x3": 9, "5x5": 25}.get(used_block)}
    h = horizons.get(cell["id"])
    share = np.array(h["open_share"], dtype=float) if h and "open_share" in h else None
    out = {"snow": mine_snow, "targets": {}}
    for j, t in enumerate(targets):
        res = {}
        for kind in ("all", "long"):
            m = tb[kind][j]
            flat = m.sum(axis=(1, 2)) / 60.0
            terrain = (m * share[None]).sum(axis=(1, 2)) / 60.0 if share is not None else np.full(36, np.nan)
            if north:
                sf, op = snow_free(flat, odds), snow_free(terrain, odds)
            else:
                sf, op = np.full(36, np.nan), terrain
            p = "long_" if kind == "long" else ""
            res[p + "flat"], res[p + "snow_free"], res[p + "open"] = flat, sf, op
            if kind == "long":
                res["yearly"] = {
                    "long_flat_hours": tot(flat), "long_snow_free_hours": tot(sf), "long_open_hours": tot(op) if north else float("nan"),
                    "long_snow_free_hours_winter": tot(sf, WINTER_N), "long_snow_free_hours_summer": tot(sf, SUMMER_N),
                    "long_open_hours_winter": tot(op, WINTER_N) if north else float("nan"),
                    "long_open_hours_summer": tot(op, SUMMER_N) if north else float("nan"),
                    "long_snow_free_hours_as_mapped": tot(snow_free(flat, mapped)) if north else float("nan"),
                    "long_snow_free_hours_with_rule": tot(snow_free(flat, rule)) if north else float("nan"),
                    "long_summer_rock_hours": float("nan") if north else tot(flat, ROCK_S),
                    "long_summer_rock_open_hours": float("nan") if north else tot(terrain, ROCK_S),
                }
                sect = m.sum(axis=(0, 2))
                pole = sect[:9].sum() + sect[27:].sum() if north else sect[9:27].sum()
                res["poleward_share"] = float(pole / sect.sum()) if sect.sum() > 0 else float("nan")
            else:
                res["yearly_all"] = {"flat_hours": tot(flat), "snow_free_hours": tot(sf) if north else float("nan"),
                                     "open_hours": tot(op) if north else float("nan")}
        out["targets"][t] = res
    return out


def outside(mine, theirs):
    """True when the two differ by more than 2 percent or 1 hour, whichever is larger; or known in one only."""
    a, b = (float("nan") if v is None else float(v) for v in (mine, theirs))
    if math.isnan(a) and math.isnan(b):
        return False, 0.0
    if math.isnan(a) != math.isnan(b):
        return True, float("nan")
    diff = abs(a - b)
    return diff > max(1.0, 0.02 * abs(b)), diff


def file_note(path: Path) -> dict:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    stamp = datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat(timespec="seconds")
    return {"file": str(path), "sha256": digest.hexdigest(), "modified": stamp}


def write_check(key: str, record: dict, path: Path = CHECKS) -> None:
    """Put one record into checks.json under key, keeping the other keys; side file, then rename."""
    path = Path(path)
    whole = json.loads(path.read_text()) if path.exists() else {}
    whole[key] = record
    side = path.with_name(path.name + ".part")
    side.write_text(json.dumps(whole, indent=1, allow_nan=False) + "\n")
    os.replace(side, path)


def tables_for(lats, limits, phases, shift, decl, workers):
    jobs = [(lat, limits, phases, shift, decl) for lat in sorted(set(lats))]
    if workers <= 1:
        return dict(_job(j) for j in jobs)
    with ProcessPoolExecutor(max_workers=workers) as pool:
        return dict(pool.map(_job, jobs, chunksize=4))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--cells", type=int, default=None, help="only the first N cells (a quick look; implies --no-write)")
    parser.add_argument("--decl", default="almanac", choices=("almanac", "meeus"))
    parser.add_argument("--shift", type=float, default=None,
                        help="also count again with every calendar moved by this many days and report how far the yearly long-window flat hours move")
    parser.add_argument("--no-write", action="store_true", help="print, do not write checks.json")
    parser.add_argument("--report", type=Path, default=None, help="also write the full list of differences here")
    args = parser.parse_args(argv)
    t0 = time.time()

    g = json.loads((D / "grazing_cells.json").read_text())
    cells = g["cells"][: args.cells] if args.cells else g["cells"]
    meta = g["meta"]
    targets = [t["id"] for t in meta["targets"]]
    if int(meta.get("year_phases", 1)) != PHASES:
        raise SystemExit(f"grazing_cells.json averages {meta.get('year_phases', 1)} calendars, this program {PHASES}: "
                         "not like with like; set PHASES or rebuild the cells file")
    if float(meta.get("step_minutes", 1)) != 1.0:
        raise SystemExit(f"grazing_cells.json uses {meta.get('step_minutes')}-minute steps, this program 1-minute steps")
    moon = {m["id"]: round(m["sun_max_elev_deg"], 2) for m in json.loads((D / "moon_targets.json").read_text())}
    limits = [moon[t] for t in targets]
    assert limits == [t["limit_deg"] for t in meta["targets"]], (limits, meta["targets"])
    z = np.load(D / "snow_free_dekads.npz")
    snow = {"probabilities": z["probabilities"], "probabilities_as_mapped": z["probabilities_as_mapped"],
            "stuck_winters": z["stuck_winters"], "row0": int(z["row0"]), "col0": int(z["col0"])}
    horizons = json.loads((D / "horizon_cells.json").read_text())
    with np.load(D / "grazing_bins.npz") as packed:
        bins = {name: packed[name] for name in packed.files}
    index = {cid: i for i, cid in enumerate(bins["ids"].tolist())}
    assert list(bins["targets"]) == targets

    tables = tables_for([c["lat"] for c in cells], limits, PHASES, 0.0, args.decl, args.workers)
    t_tables = time.time() - t0
    report = {"cells": 0, "comparisons": 0, "outside": [], "max_abs_diff_h": {}, "max_bin_diff_h": {},
              "snow_mismatch": [], "centre_mismatch": [], "share_worst": 0.0}
    for cell in cells:
        cid = cell["id"]
        clat, clon = centre_of(cid)
        if abs(clat - cell["lat"]) > 0.006 or abs(clon - cell["lon"]) > 0.006:
            report["centre_mismatch"].append([cid, cell["lat"], cell["lon"], clat, clon])
        mine = recompute(cell, targets, tables[cell["lat"]], snow, horizons)
        report["cells"] += 1
        if cell["hemisphere"] == "N":
            for key, val in mine["snow"].items():
                if cell["snow"].get(key) != val:
                    report["snow_mismatch"].append([cid, key, cell["snow"].get(key), val])
        i = index[cid]
        for j, t in enumerate(targets):
            res, theirs = mine["targets"][t], cell["targets"][t]
            for name in ARRAYS:
                ref, m = bins[name][i, j].astype(float), res[name]
                if (np.isfinite(ref) != np.isfinite(m)).any():
                    report["outside"].append([cid, t, "npz " + name, "known in one only", int(np.isfinite(m).sum()), int(np.isfinite(ref).sum())])
                    continue
                report["comparisons"] += 1
                if np.isfinite(ref).any():
                    bd = float(np.nanmax(np.abs(ref - m)))
                    report["max_bin_diff_h"][name] = max(report["max_bin_diff_h"].get(name, 0.0), bd)
                    bad, diff = outside(np.nansum(m), np.nansum(ref))
                    report["max_abs_diff_h"]["npz " + name] = max(report["max_abs_diff_h"].get("npz " + name, 0.0), diff)
                    if bad:
                        report["outside"].append([cid, t, "npz " + name + " (year sum)", round(float(np.nansum(m)), 2),
                                                  round(float(np.nansum(ref)), 2), round(bd, 2)])
            for field, value in {**res["yearly"], **res["yearly_all"]}.items():
                bad, diff = outside(value, theirs.get(field))
                report["comparisons"] += 1
                if not math.isnan(diff):
                    report["max_abs_diff_h"][field] = max(report["max_abs_diff_h"].get(field, 0.0), diff)
                if bad:
                    report["outside"].append([cid, t, field, None if math.isnan(value) else round(value, 2), theirs.get(field)])
            ps, theirs_ps = res["poleward_share"], theirs.get("poleward_share")
            report["comparisons"] += 1
            if (theirs_ps is None) != math.isnan(ps):
                report["outside"].append([cid, t, "poleward_share", None if math.isnan(ps) else round(ps, 3), theirs_ps])
            elif theirs_ps is not None:
                report["share_worst"] = max(report["share_worst"], abs(ps - theirs_ps))
                if abs(ps - theirs_ps) > 0.02:
                    report["outside"].append([cid, t, "poleward_share", round(ps, 3), theirs_ps])

    largest = max(report["max_abs_diff_h"].values()) if report["max_abs_diff_h"] else None
    largest_bin = max(report["max_bin_diff_h"].values()) if report["max_bin_diff_h"] else None
    record = {
        "ran_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "program": "scripts/independent_recount.py (imports nothing of twinfinder)",
        "method": "own Sun position at the edges of 1-minute steps with Saemundsson refraction; mean of "
                  f"{PHASES} calendars 1/{PHASES} day apart, centred on day 0 = J2000.0 + {DAY0} days; own spell finding "
                  "with crossing times inside the minute, joined through midnight and the year end, 120 min minimum; "
                  "the band sampled every 6 seconds; own polar-stereographic reading of the snow grid; the terrain's open "
                  "share read from horizon_cells.json",
        "sun_series": "Astronomical Almanac low-precision series (the project's), written out again in the program"
                      if args.decl == "almanac" else "Meeus low-accuracy series (not the project's)",
        "year_phases": PHASES,
        "cells": report["cells"], "targets": len(targets),
        "comparisons": report["comparisons"],
        "compared": "per cell and target: the six per-bin arrays of grazing_bins.npz (flat, snow_free, open and their "
                    "long_ twins, by yearly sum and by ten-day bin) and 13 yearly fields of grazing_cells.json, plus the "
                    "poleward share; and the snow summary of every northern cell",
        "tolerance": TOLERANCE,
        "outside_tolerance": len(report["outside"]),
        "largest_difference_h_a_year": None if largest is None else round(largest, 3),
        "largest_difference_h_in_a_ten_day_bin": None if largest_bin is None else round(largest_bin, 3),
        "largest_poleward_share_difference": round(report["share_worst"], 4),
        "snow_summaries_that_differ": len(report["snow_mismatch"]),
        "cell_centres_that_differ": len(report["centre_mismatch"]),
        "first_rows_outside": report["outside"][:20],
        "against": [file_note(D / n) for n in ("grazing_cells.json", "grazing_bins.npz", "horizon_cells.json",
                                                 "snow_free_dekads.npz", "moon_targets.json")],
        "seconds": None,
    }
    if args.shift is not None:
        moved = tables_for([c["lat"] for c in cells], limits, PHASES, args.shift, args.decl, args.workers)
        by_target = {}
        for j, t in enumerate(targets):
            stored = np.array([np.nansum(bins["long_flat"][index[c["id"]], j].astype(float)) for c in cells])
            shifted = np.array([moved[c["lat"]]["long"][j].sum() / 60.0 for c in cells])
            has = stored > 0
            diff = np.abs(shifted - stored)
            out_ = diff > np.maximum(1.0, 0.02 * np.abs(stored))
            by_target[t] = {"cells_with_long_window_flat_hours": int(has.sum()), "cells_outside_tolerance": int(out_.sum()),
                            "largest_difference_h": round(float(diff.max()), 2) if len(diff) else None,
                            "median_difference_h": round(float(np.median(diff[has])), 2) if has.any() else None,
                            "p90_difference_h": round(float(np.percentile(diff[has], 90)), 2) if has.any() else None}
        record["calendar_moved"] = {
            "what": f"every one of the {PHASES} calendars moved {args.shift:g} day later; yearly long-window flat hours of each "
                    "cell against grazing_bins.npz long_flat",
            "days": args.shift, "cells": len(cells), "targets": by_target}
    record["seconds"] = round(time.time() - t0, 1)
    print(json.dumps({k: v for k, v in record.items() if k not in ("against",)}, indent=1))
    print(f"tables {t_tables:.0f} s; latitudes {len(tables)}")
    if args.report:
        args.report.write_text(json.dumps(report, indent=1))
    if not args.no_write and args.cells is None:
        write_check("independent_recount", record)
        print(f"wrote {CHECKS} -> independent_recount")
    return record


if __name__ == "__main__":
    main()

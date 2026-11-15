# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Compare the project's Sun tables with NASA JPL Horizons, from saved answers only: no request is made.

    uv run python scripts/check_against_horizons.py            writes data/derived/checks.json -> jpl_horizons
    uv run python scripts/check_against_horizons.py --no-write print only

The saved answers are in data/raw/horizons_check/: 36 Horizons observer tables (the Sun seen from
the Earth's surface, refracted apparent azimuth and elevation every 5 minutes, UT), asked for on
14 November 2026 by the geometry check of version 3, for 9 places and 4 ten-day periods each
(sites.json lists them: a best period, midwinter, the March equinox and midsummer). Each file
keeps the header Horizons sent, with its request.

For each place, period and lunar limit (2.08, 5.55, 6.11, 7.59 degrees) it counts, from the
Horizons rows filled in to 15-second steps by a cubic through the four nearest rows, over the
local days of the period (local mean solar time, UT + longitude / 15 h, dates of 2026):
- all hours with the Sun's apparent centre in (0, limit];
- hours inside unbroken spells of 2 hours or more (a spell through midnight is one spell).
It sets beside them what twinfinder.sun gives for the same latitude and ten-day bin, as the
pipeline calls it now (band_minutes_table and long_band_minutes_table at 1-minute steps, the mean
of sun.YEAR_PHASES calendars). Differences are project minus Horizons. A row is flagged when they
differ by more than 5 percent or more than 1 hour.

What this does not test: the project's tables are for a 365-day year at the middle of the leap
cycle, averaged over calendars a fraction of a day apart; Horizons gives the real dates of 2026.
So differences in long-spell hours include the effect of the year, and are not all error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "horizons_check"
CHECKS = ROOT / "data" / "derived" / "checks.json"
LIMITS = [2.08, 5.55, 6.11, 7.59]
TARGETS = ["connecting-ridge", "malapert", "mons-mouton", "nobile-rim-2"]
FACTOR = 20                         # 5-minute rows filled in to 15-second steps
FINE_MIN = 5.0 / FACTOR
MIN_SPELL_H = 2.0
FLAG_PCT, FLAG_H = 5.0, 1.0
YEAR_START = np.datetime64("2026-01-01T00:00:00", "s")
MONTHS = {m: i + 1 for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])}


def parse_horizons(text: str, step_minutes: float | None = None):
    """Times (UT, datetime64 minutes), azimuth and elevation from a Horizons observer table in CSV form."""
    lines = text.splitlines()
    try:
        first, last = lines.index("$$SOE"), lines.index("$$EOE")
    except ValueError as err:
        raise ValueError("no $$SOE / $$EOE block in the Horizons text") from err
    when, az, el = [], [], []
    for line in lines[first + 1:last]:
        parts = [p.strip() for p in line.split(",")]
        stamp = parts[0].split()
        year, month, dom = stamp[0].split("-")
        when.append(np.datetime64(f"{year}-{MONTHS[month]:02d}-{dom}T{stamp[1][:5]}", "m"))
        az.append(float(parts[3]))
        el.append(float(parts[4]))
    when = np.array(when)
    if step_minutes is not None and len(when) > 1:
        gaps = np.diff(when).astype("timedelta64[m]").astype(int)
        if np.any(gaps != int(step_minutes)):
            raise ValueError(f"the table is not in steady steps of {step_minutes} minutes")
    return when, np.array(az), np.array(el)


def upsample_cubic(y, factor: int):
    """Values at `factor` times finer spacing by a cubic through the four nearest samples (positions in row units)."""
    y = np.asarray(y, dtype=float)
    n = len(y)
    fine_x = np.arange((n - 1) * factor + 1) / factor
    left = np.clip(np.floor(fine_x).astype(int) - 1, 0, n - 4)
    t = fine_x - left
    w0 = -(t - 1) * (t - 2) * (t - 3) / 6.0
    w1 = t * (t - 2) * (t - 3) / 2.0
    w2 = -t * (t - 1) * (t - 3) / 2.0
    w3 = t * (t - 1) * (t - 2) / 6.0
    return fine_x, w0 * y[left] + w1 * y[left + 1] + w2 * y[left + 2] + w3 * y[left + 3]


def run_length(inside):
    """For each sample, the length (in samples) of the unbroken run of True it belongs to; 0 where False."""
    inside = np.asarray(inside, dtype=bool)
    if len(inside) == 0:
        return np.zeros(0, dtype=np.int64)
    change = np.diff(np.concatenate([[False], inside, [False]]).astype(np.int8))
    starts, ends = np.flatnonzero(change == 1), np.flatnonzero(change == -1)
    out = np.zeros(len(inside), dtype=np.int64)
    lengths = ends - starts
    out[inside] = np.repeat(lengths, lengths)
    return out


def day_statistics(inside, day, step_minutes: float, min_spell_h: float = MIN_SPELL_H) -> dict:
    """Per day: hours in the band, hours inside spells of min_spell_h or more, the longest spell touching the day."""
    inside = np.asarray(inside, dtype=bool)
    length_h = run_length(inside) * (step_minutes / 60.0)
    labels, index = np.unique(np.asarray(day), return_inverse=True)
    step_h = step_minutes / 60.0
    band = np.bincount(index, weights=inside * step_h, minlength=len(labels))
    is_long = inside & (length_h >= min_spell_h - 1e-9)
    long = np.bincount(index, weights=is_long * step_h, minlength=len(labels))
    longest = np.zeros(len(labels))
    np.maximum.at(longest, index, length_h)
    return {"days": labels, "band_h": band, "long_h": long, "longest_h": np.minimum(longest, 24.0)}


def bin_days(b: int) -> tuple[int, int]:
    return 10 * b + 1, (10 * b + 10 if b < 35 else 365)


def horizons_counts(path: Path, lon: float, b: int) -> dict:
    """Per limit: all hours and long-spell hours over the local days of bin b, and the daily longest spells."""
    when, _, el = parse_horizons(path.read_text(encoding="utf-8", errors="replace"), step_minutes=5)
    _, fine = upsample_cubic(el, FACTOR)
    when_s = when[0].astype("datetime64[s]") + (np.arange(len(fine)) * 15).astype("timedelta64[s]")
    seconds = (when_s - YEAR_START).astype("int64") + int(round(lon * 240.0))
    doy = np.floor_divide(seconds, 86400) + 1
    first, last = bin_days(b)
    in_bin = (doy >= first) & (doy <= last)
    per_day = np.bincount((doy[in_bin] - first).astype(int), minlength=last - first + 1)
    if not np.all(per_day == round(1440.0 / FINE_MIN)):
        raise ValueError(f"{path.name}: the table does not cover every local day of bin {b} in full")
    out = {}
    for limit in LIMITS:
        stats = day_statistics((fine > 0.0) & (fine <= limit), doy, FINE_MIN)
        keep = (stats["days"] >= first) & (stats["days"] <= last)
        out[limit] = {"all_h": float(stats["band_h"][keep].sum()), "long_h": float(stats["long_h"][keep].sum()),
                      "longest_h": [round(float(v), 3) for v in stats["longest_h"][keep]]}
    return out


def project_counts(lat: float, year_phases: int | None = None) -> dict:
    """{limit: (all hours [36 bins], long hours [36 bins])} from twinfinder.sun at this latitude, 1-minute steps."""
    from twinfinder import sun
    phases = sun.YEAR_PHASES if year_phases is None else year_phases
    minutes = sun.band_minutes_table([lat], step_minutes=1, year_phases=phases)[0]          # [36, sectors, 9]
    long_min = sun.long_band_minutes_table([lat], LIMITS, MIN_SPELL_H, 1, year_phases=phases)[:, 0]
    edges = sun.ELEV_EDGES_DEG
    out = {}
    for j, limit in enumerate(LIMITS):
        use = [e for e in range(9) if edges[e + 1] <= limit + 0.005]
        out[limit] = (minutes[:, :, use].sum(axis=(1, 2)) / 60.0, long_min[j][:, :, use].sum(axis=(1, 2)) / 60.0)
    return out


def pct(row: dict):
    h, p = row["horizons_h"], row["project_h"]
    return None if h == 0 else 100.0 * (p - h) / h


def flagged(row: dict) -> bool:
    d, p = abs(row["project_h"] - row["horizons_h"]), pct(row)
    return d > FLAG_H or (p is not None and abs(p) > FLAG_PCT)


def summary(rows: list[dict]) -> dict:
    """Median and largest difference, in hours over all rows and in percent over the rows where Horizons has hours."""
    diffs = [abs(r["project_h"] - r["horizons_h"]) for r in rows]
    pcts = [abs(p) for p in (pct(r) for r in rows) if p is not None]
    return {"rows": len(rows), "rows_with_a_percentage": len(pcts),
            "median_abs_difference_h": round(float(np.median(diffs)), 3) if diffs else None,
            "largest_abs_difference_h": round(float(max(diffs)), 3) if diffs else None,
            "median_abs_difference_pct": round(float(np.median(pcts)), 3) if pcts else None,
            "largest_abs_difference_pct": round(float(max(pcts)), 3) if pcts else None,
            "horizons_total_h": round(float(sum(r["horizons_h"] for r in rows)), 1),
            "project_total_h": round(float(sum(r["project_h"] for r in rows)), 1)}


def cause_of(row: dict, kind: str) -> str | None:
    """A cause for a flagged row when one can be shown from the numbers; None when it is not known."""
    one = row.get("project_one_calendar_h")
    if one is not None and not flagged({**row, "project_h": one}):
        return (f"the average over calendars: the project's single calendar of day 0 gives {one:.2f} h, within the flag rule of "
                f"Horizons' {row['horizons_h']:.2f} h; the mean of the calendars a fraction of a day apart gives {row['project_h']:.2f} h"
                + (" (at the two-hour cut, the day on which spells first or last reach 2 h differs between calendars)"
                   if kind == "long" else ""))
    if kind == "long":
        near = [v for v in row.get("horizons_longest_h", []) if abs(v - MIN_SPELL_H) <= 0.25]
        if near:
            return (f"on {len(near)} of the {len(row['horizons_longest_h'])} days the longest Horizons spell is within 15 minutes "
                    f"of the 2-hour cut ({', '.join(f'{v:.2f}' for v in near)} h), so a small shift of the calendar decides whether "
                    "the day counts" + ("" if one is None else f"; the project's single calendar gives {one:.2f} h"))
    if row["horizons_h"] < 5.0:
        return "a small total: under 5 hours in the period, so a quarter of an hour makes the percentage large"
    return None


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_check(key: str, record: dict, path: Path = CHECKS) -> None:
    whole = json.loads(path.read_text()) if path.exists() else {}
    whole[key] = record
    side = path.with_name(path.name + ".part")
    side.write_text(json.dumps(whole, indent=1, allow_nan=False) + "\n")
    os.replace(side, path)


def main(argv=None) -> dict:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args(argv)
    from twinfinder import sun
    sites = json.loads((RAW / "sites.json").read_text())
    rows = {"all": [], "long": []}
    cache = {}
    for site in sites:
        lat, lon = site["lat"], site["lon"]
        if lat not in cache:
            cache[lat] = project_counts(lat)
        for role, b in site["bins"].items():
            path = RAW / f"{site['site']}_bin{b:02d}.txt"
            hz = horizons_counts(path, lon, b)
            for j, limit in enumerate(LIMITS):
                all_h, long_h = cache[lat][limit]
                base = {"place": site["site"], "lat": lat, "lon": lon, "bin": b, "period": role, "target": TARGETS[j],
                        "limit_deg": limit}
                rows["all"].append({**base, "horizons_h": round(hz[limit]["all_h"], 3), "project_h": round(float(all_h[b]), 3)})
                rows["long"].append({**base, "horizons_h": round(hz[limit]["long_h"], 3), "project_h": round(float(long_h[b]), 3),
                                     "horizons_longest_h": hz[limit]["longest_h"]})
    flags = []
    one_cache = {}
    for kind in ("all", "long"):
        for row in rows[kind]:
            if not flagged(row):
                continue
            if row["lat"] not in one_cache:
                one_cache[row["lat"]] = project_counts(row["lat"], year_phases=1)
            row["project_one_calendar_h"] = round(float(one_cache[row["lat"]][row["limit_deg"]][0 if kind == "all" else 1][row["bin"]]), 3)
            p = pct(row)
            flags.append({"hours": "all hours" if kind == "all" else "hours in spells of 2 h or more",
                          **{k: row[k] for k in ("place", "lat", "lon", "bin", "period", "target", "limit_deg", "horizons_h", "project_h")},
                          "difference_h": round(row["project_h"] - row["horizons_h"], 3),
                          "difference_pct": None if p is None else round(p, 2),
                          "project_one_calendar_h": row.get("project_one_calendar_h"),
                          "cause": cause_of(row, kind)})
    record = {
        "ran_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "program": "scripts/check_against_horizons.py (saved answers only; no request made)",
        "horizons_answers": "data/raw/horizons_check/*.txt, asked for on 14 November 2026 (see each file's header)",
        "places": [{"name": s["site"], "lat": s["lat"], "lon": s["lon"]} for s in sites],
        "periods_per_place": 4,
        "periods": {s["site"]: s["bins"] for s in sites},
        "limits_deg": LIMITS,
        "project_side": f"twinfinder.sun band_minutes_table and long_band_minutes_table at the place's latitude, 1-minute steps, "
                        f"mean of {sun.YEAR_PHASES} calendars",
        "sun_code_sha256": file_sha(ROOT / "twinfinder" / "sun.py"),
        "year_phases": sun.YEAR_PHASES,
        "differences": "project minus Horizons; percent of the Horizons figure, over rows where Horizons has hours",
        "all_hours": summary(rows["all"]),
        "hours_in_spells_of_2_h_or_more": summary(rows["long"]),
        "flag_rule": f"more than {FLAG_PCT:g} percent or more than {FLAG_H:g} hour",
        "rows_flagged": flags,
    }
    print(json.dumps({k: v for k, v in record.items() if k not in ("periods", "places")}, indent=1))
    if not args.no_write:
        write_check("jpl_horizons", record)
        print(f"wrote {CHECKS} -> jpl_horizons")
    return record


if __name__ == "__main__":
    main()

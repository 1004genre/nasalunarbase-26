# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Grazing hours by latitude over a flat horizon, per lunar target: Sun geometry only, with refraction.

No snow and no terrain enter. Writes data/derived/latitude_profile.json: one
row per half degree from 89.5S to 89.5N, and per target and hemisphere the
lowest latitude (found at 0.05 degree steps) with a long low-Sun spell on at
least one day of the year, the same by the version 2 rule (a ten-day bin whose
median longest stretch reaches the minimum) and the lowest latitude with an
all-day low-Sun day. Safe to run again: the file is written beside the old one
and renamed into place.

The Sun tables are the mean over sun.YEAR_PHASES (eight) calendars an eighth of
a day apart (spread over the phases of the leap cycle). The version 2 thresholds
alone keep the single calendar version 2 used. With four phases the run took
12.5 minutes; with eight expect about 25 minutes, so start it in the background.
"""
import json
import os
from pathlib import Path

import numpy as np

from twinfinder import grazing, sun

OUT = Path("data/derived/latitude_profile.json")
STEP_DEG = 0.5
FINE_STEP_DEG = 0.05
STRETCH_MINIMUMS_H = [1.0, 2.0, 3.0]
SEARCH_BATCH = 100   # latitudes per call while walking outward from the equator (5 degrees)


def profile_latitudes() -> list[float]:
    """Every half degree from 89.5S to 89.5N."""
    return [round(-89.5 + STEP_DEG * k, 1) for k in range(359)]


def fine_latitudes(sign: int) -> list[float]:
    """0 to 89.95 degrees in steps of 0.05, north (sign 1) or south (sign -1), outward from the equator."""
    return [round(sign * FINE_STEP_DEG * k, 2) + 0.0 for k in range(1800)]


def minimum_name(min_h: float) -> str:
    return f"{min_h:g}"


def profile_row(lat: float, minutes: np.ndarray, stretch: np.ndarray, targets: list[dict], long_minutes: dict,
                longest_spell) -> dict:
    """One latitude: per target the flat hours, their split by half-year, long-window hours and the longest spell.

    minutes is [36, sectors, elevation bins] and stretch [36, targets] for this latitude.
    long_minutes holds, per minimum spell length ("1", "2", "3"), this latitude's long-spell
    minutes [targets, 36, sectors, elevation bins]; longest_spell is the year's longest single
    spell per target, in hours. The ten-day median stretch is kept for information.
    """
    per_target = {}
    for t, target in enumerate(targets):
        flat = grazing.flat_hours(minutes, target["elev_bins"])
        longest, best_bin = grazing.best_stretch(stretch[:, t])
        per_target[target["id"]] = {
            "flat_hours": grazing.known(grazing.total(flat)),
            "flat_hours_oct_mar": grazing.known(grazing.total(flat, grazing.WINTER_BINS_NORTH)),
            "flat_hours_apr_sep": grazing.known(grazing.total(flat, grazing.SUMMER_BINS_NORTH)),
            "long_flat_hours": {name: grazing.known(grazing.total(grazing.flat_hours(table[t], target["elev_bins"])))
                                for name, table in long_minutes.items()},
            "longest_spell_h": grazing.known(longest_spell[t], 2),
            "longest_stretch_h": grazing.known(longest, 2), "best_stretch_bin": best_bin,
        }
    return {"lat": lat, "targets": per_target}


def lowest_latitude(lats, found) -> float | None:
    """The latitude nearest the equator at which found is true, or None."""
    hits = [lat for lat, yes in zip(lats, found) if yes]
    return min(hits, key=abs) if hits else None


def lowest_per_minimum(sign: int, limits, minimums, best_of) -> list[dict]:
    """Per limit and minimum: the lowest latitude at which best_of(latitudes) [latitudes, limits] reaches the minimum.

    Walks outward from the equator a batch of latitudes at a time and stops
    when everything is found, so nothing between the steps is assumed.
    """
    found = [{minimum_name(m): None for m in minimums} for _ in limits]
    lats = fine_latitudes(sign)
    for start in range(0, len(lats), SEARCH_BATCH):
        batch = lats[start:start + SEARCH_BATCH]
        best = np.asarray(best_of(np.array(batch)))
        for j in range(len(limits)):
            for m in minimums:
                if found[j][minimum_name(m)] is None:
                    found[j][minimum_name(m)] = lowest_latitude(batch, best[:, j] >= m)
        if all(value is not None for per_limit in found for value in per_limit.values()):
            break
    return found


def lowest_long_spells(sign: int, limits, minimums, longest_spell=sun.longest_spell_hours) -> list[dict]:
    """Per limit: the lowest latitude with an unbroken low-Sun spell of each minimum length on at least one day."""
    return lowest_per_minimum(sign, limits, minimums, lambda lats: longest_spell(lats, limits))


def version_2_stretch_table(lats, limits) -> np.ndarray:
    """The median longest stretch per ten-day bin as version 2 had it: one calendar, two-minute steps."""
    return sun.longest_stretch_hours_table(lats, limits, year_phases=1)


def lowest_long_windows(sign: int, limits, minimums, stretch_table=None) -> list[dict]:
    """The version 2 rule, per limit: the lowest latitude with a ten-day bin whose median longest stretch reaches each minimum.

    Kept for comparison with version 2, so it uses that version's single calendar (version_2_stretch_table).
    """
    stretch_table = version_2_stretch_table if stretch_table is None else stretch_table
    return lowest_per_minimum(sign, limits, minimums, lambda lats: np.asarray(stretch_table(lats, limits)).max(axis=1))


def lowest_all_day(sign: int, limit: float) -> float | None:
    """The lowest latitude with at least one day on which the Sun rises and stays at or below the limit."""
    lats = fine_latitudes(sign)
    return lowest_latitude(lats, [bool(sun.low_sun_days(lat, limit)) for lat in lats])


def thresholds(targets: list[dict]) -> dict:
    """Per target and hemisphere: where long spells (per-day rule, and the old bin rule) and all-day low-Sun days begin."""
    limits = [t["limit_deg"] for t in targets]
    out = {t["id"]: {} for t in targets}
    for side, sign in (("N", 1), ("S", -1)):
        per_day = lowest_long_spells(sign, limits, STRETCH_MINIMUMS_H)
        bin_median = lowest_long_windows(sign, limits, STRETCH_MINIMUMS_H)
        for target, spells, medians in zip(targets, per_day, bin_median):
            out[target["id"]][side] = {"lowest_lat_with_long_window": spells,
                                       "lowest_lat_with_long_window_bin_median": medians,
                                       "lowest_lat_with_all_day_low_sun": lowest_all_day(sign, target["limit_deg"])}
    return out


def write_json(path: Path, value) -> None:
    side = path.with_name(path.name + ".part")
    side.write_text(json.dumps(value))
    os.replace(side, path)


def main() -> None:
    targets = grazing.load_targets()
    limits = [t["limit_deg"] for t in targets]
    lats = profile_latitudes()
    minutes = sun.band_minutes_table(lats, step_minutes=grazing.STEP_MINUTES)
    stretch = sun.longest_stretch_hours_table(lats, limits)
    long_minutes = {minimum_name(m): sun.long_band_minutes_table(lats, limits, m, grazing.STEP_MINUTES)
                    for m in STRETCH_MINIMUMS_H}                                    # each [targets, latitudes, ...]
    longest_spell = sun.longest_spell_hours(lats, limits, grazing.STEP_MINUTES)
    rows = [profile_row(lat, minutes[i], stretch[i], targets, {name: table[:, i] for name, table in long_minutes.items()},
                        longest_spell[i]) for i, lat in enumerate(lats)]
    meta = {
        "what": "flat horizon, apparent Sun centre (standard refraction), no snow, no terrain; hours per 365-day year",
        "targets": targets, "step_deg": STEP_DEG, "threshold_step_deg": FINE_STEP_DEG,
        "stretch_minimums_h": STRETCH_MINIMUMS_H, "long_rule": grazing.LONG_RULE, "step_minutes": grazing.STEP_MINUTES,
        "year_phases": sun.YEAR_PHASES,
        "year_phases_meaning": grazing.YEAR_PHASES_MEANING + "; longest_spell_h is the mean of the calendars' longest "
                               "spells; the version 2 thresholds (bin median) keep a single calendar",
        "long_window": "the time inside unbroken spells of at least the minimum length with the Sun in the band, "
                       "followed day by day (a spell through midnight is one spell)",
        "lowest_lat_with_long_window": "the lowest latitude at which the longest spell of the year (mean over the "
                                       "calendars; they differ by seconds there) reaches the minimum",
        "lowest_lat_with_long_window_bin_median": "the version 2 rule, kept for comparison: the lowest latitude with a "
                                                  "ten-day bin whose median longest stretch (two-minute steps) reaches "
                                                  "the minimum",
        "longest_spell_h": "the longest single spell of the year (not capped at a day)",
        "longest_stretch_h": "the best ten-day median of the longest stretch per day (version 2; for information)",
        "oct_mar_bins": grazing.WINTER_BINS_NORTH, "apr_sep_bins": grazing.SUMMER_BINS_NORTH,
        "half_years": "oct_mar is 28 September to 31 March (northern winter, southern summer); apr_sep is the rest",
    }
    write_json(OUT, {"meta": meta, "profile": rows, "thresholds": thresholds(targets)})
    print(f"wrote {OUT}: {len(rows)} latitudes, {len(targets)} targets")


if __name__ == "__main__":
    main()

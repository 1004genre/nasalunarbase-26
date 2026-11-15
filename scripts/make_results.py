# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Write data/derived/RESULTS.md from the files in data/derived. Every number is read or computed here, in this run.

Reads only project files: grazing_cells.json, latitude_profile.json, validation.json, cells_scored.json,
candidates.json, cloud_cells.json, ranking.txt, light_cells_v1.json, ranking_v1.txt, snow_validation_many.json,
the kept version 2 files (validation_v2.json, cells_scored_v2.json) and two lists in data/reference.
It does not use the pipeline's counting or ranking code: the tables are rebuilt here from the stored records
(only sun.refraction_deg is called, for one stated figure). Run from the project root:
    uv run python scripts/make_results.py
The file is written beside the old one and renamed into place. Unknown values are written n/a, never 0.
"""
import hashlib
import json
import math
import os
import re
import sys
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np

from twinfinder import sun

D = Path("data/derived")
REFERENCE = Path("data/reference")
OUT = D / "RESULTS.md"
NUMBERS = []          # (label, value, how) of the run in progress; build() returns a copy
MOON_SYNODIC_DAYS = 29.530589     # the Sun goes once round the lunar horizon in one synodic month
EARTH_DEG_PER_HOUR = 15.0         # the Sun's hour angle moves 15 degrees an hour
SECTIONS = [
    ("a", "Where on Earth the Sun grazes the horizon for hours"),
    ("b", "The north in the winter half (28 September to 31 March)"),
    ("c", "The north in the summer half (1 April to 27 September): the midnight-Sun side"),
    ("d", "What real terrain takes away"),
    ("e", "The top sites per target"),
    ("f", "The named sites"),
    ("g", "Antarctica: snow not measured"),
    ("h", "The old measure against the new"),
    ("i", "What is doubtful or not covered"),
    ("j", "Cloud: typical clear-sky hours"),
    ("k", "Version 2 against version 3"),
    ("l", "Winter on small bare patches"),
    ("m", "How reachable the best areas are"),
]
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def num(label, value, how):
    NUMBERS.append({"label": label, "value": str(value), "how": how})
    return value


def load(name):
    return json.loads((D / name).read_text())


def mtime(name):
    return datetime.fromtimestamp((D / name).stat().st_mtime).strftime("%H:%M:%S")


def f(v, d=0):
    """A number for a table; unknown is 'n/a'."""
    if v is None:
        return "n/a"
    text = f"{v:,.{d}f}"
    return text[1:] if text.startswith("-") and not text.strip("-0.,") else text   # -0.04 at one decimal is 0.0, not -0.0


def day_label(doy):
    return (date(2025, 1, 1) + timedelta(days=doy - 1)).strftime("%-d %b")


def bin_dates(b):
    first = b * 10 + 1
    last = 365 if b == 35 else first + 9
    return f"{day_label(first)}-{day_label(last)}"


def bins_text(top_bins):
    return ", ".join(f"{bin_dates(b)} ({h:.0f} h)" if h >= 1 else f"{bin_dates(b)} ({h:.1f} h)" for b, h in top_bins) or "none"


def hav(a, b):
    p1, p2 = math.radians(a["lat"]), math.radians(b["lat"])
    dl = math.radians(b["lon"] - a["lon"])
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371.0088 * math.asin(math.sqrt(h))


def pct(values, q):
    return float(np.percentile(np.array(values, dtype=float), q))


def table(head, rows):
    out = ["| " + " | ".join(head) + " |", "|" + "|".join("---" for _ in head) + "|"]
    out += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return out


def has_h(c):
    return bool(c["horizon"]) and "skipped" not in c["horizon"]


def horizon_state(c):
    """Whether a cell has a terrain horizon, or in few words why not (a held-back cell's stored text names its tile)."""
    h = c.get("horizon")
    if h is None:
        return "no horizon record"
    if "skipped" not in h:
        return "horizon"
    why = str(h["skipped"])
    if "antimeridian" in why.lower():
        return "window across the antimeridian"
    if why.startswith("tile not fetched"):
        return "elevation tile not fetched"
    return why


def spread_text(d):
    """A spread of validation.json as 10th / 25th / median / 75th / 90th percentile, with the three decimals stored there."""
    if not d["cells"]:
        return "n/a"
    return " / ".join(f"{d[k]:.3f}" for k in ("p10", "p25", "median", "p75", "p90"))


def moved(old, new, digits=0):
    """A change for a table: signed, or 'same'."""
    if old is None or new is None:
        return "n/a"
    change = round(new - old, digits)
    return "same" if change == 0 else f"{change:+,.{digits}f}"


LEVELS_H = (50, 100, 200)


def level_counts(group, tid, field, levels=LEVELS_H):
    """Cells of a group, and their bare km2, whose hours in one field reach each level; unknown hours are in no count."""
    out = {}
    for level in levels:
        got = [c for c in group if c["targets"][tid].get(field) is not None and c["targets"][tid][field] >= level]
        out[str(level)] = {"cells": len(got), "bare_km2": round(sum(c["bare_km2"] for c in got), 1)}
    return out


def levels_that_differ(mine, theirs, levels=LEVELS_H):
    """How many of the figures of level_counts differ from another count of the same thing (areas: by more than 0.1 km2)."""
    return sum((mine[str(k)]["cells"] != theirs[str(k)]["cells"]) + (abs(mine[str(k)]["bare_km2"] - theirs[str(k)]["bare_km2"]) > 0.1)
               for k in levels)


def stuck_station_check(stations):
    """The trusted stations with a stuck winter in their 3 x 3 snow block: where are the odds as mapped closer to the station?

    For each such station the mean absolute difference from the station's own snow-free share, over the ten-day bins
    in which all three are known, is taken twice: for the satellite odds as mapped and for those with the stale-flag rule.
    """
    out = {"stations": 0, "as_mapped_closer": 0, "rule_closer": 0, "same": 0, "lat_min": None, "lat_max": None}
    lats = []
    for station in stations:
        if (station.get("stuck_winters") or 0) < 1:
            continue
        both = [(m, r, t) for m, r, t in zip(station["satellite_as_mapped"], station["satellite"], station["station_share"])
                if m is not None and r is not None and t is not None]
        if not both:
            continue
        mapped = sum(abs(m - t) for m, _, t in both) / len(both)
        ruled = sum(abs(r - t) for _, r, t in both) / len(both)
        out["stations"] += 1
        out["as_mapped_closer" if mapped < ruled else "rule_closer" if ruled < mapped else "same"] += 1
        lats.append(station["lat"])
    if lats:
        out["lat_min"], out["lat_max"] = min(lats), max(lats)
    return out


SHORT = {"connecting-ridge": "Connecting ridge", "malapert": "Malapert", "mons-mouton": "Mons Mouton", "nobile-rim-2": "Nobile Rim 2"}
OLD_FOUR = tuple(SHORT)   # the four regions of the kept version 1 and version 2 files: only they are compared with them


def short_names(targets: list[dict]) -> None:
    """Add a short name for each region the table above does not know: its own name."""
    for t in targets:
        SHORT.setdefault(t["id"], t["name"])


# ---- the leap-cycle average, the winter leads (l) and the distance to airfields (m)

PHASE_WORDS = {1: "one", 2: "two", 4: "four", 8: "eight"}
# What a move of the calendar still does to a latitude's yearly long-window hours, by the number of calendars the Sun
# tables average (measured with twinfinder.sun by the leap-cycle step of 14 Nov 2026; the bounds for 4 and 8 are
# asserted by tests/test_sun.py on every test run).
LEAP_REMAINS = {
    1: "a single calendar moved by 0.14 day changes a latitude's yearly long-window hours by up to 9.1 h, and 4,874 of the "
       "12,559 cells with such hours under the lowest limit by more than the larger of 2% and 1 h",
    4: "a move of the calendar by 0.14 day still changes a latitude's yearly long-window hours by up to 3.2 h; 939 of the "
       "12,559 cells with such hours under the lowest limit move by more than the larger of 2% and 1 h",
    8: "the worst move of the calendar (1/16 day) changes a latitude's yearly long-window hours by at most 1.5 h over all 468 "
       "cell latitudes, never by more than the larger of 2% and 1 h; at 65, 67, 70, 75 and 80° north and south by at most "
       "1.0 h, within 1% or half an hour (a move of 0.14 day: at most 0.75 h)",
}
ACCESS_MIN_H = 100.0          # long-window open hours an area needs to be counted in (m)
ACCESS_KM = (50, 100, 200)    # distances to a scheduled-service airfield counted in (m)
REACH_KM = 100                # "within reach" for the best areas of (m)
TOP_AREAS = 50                # how many of the best lighting areas the country shares of (m) cover
WINTER_LEVEL = "100"          # winter-half hours a square needs to be counted in (l)


def leap_paragraph(meta):
    """The (i) paragraph on the leap-cycle average, for the number of calendars the cells file was made with."""
    n = int(meta.get("year_phases", 1))
    word = PHASE_WORDS.get(n, str(n))
    remains = LEAP_REMAINS.get(n, "what remains with this number of calendars was not measured")
    made = (f"every Sun table behind the hours of this file is the mean over {word} calendars, 1/{n} day apart and centred on "
            "the middle of the 2024 to 2028 leap cycle" if n > 1 else
            "the Sun tables behind the hours of this file use one calendar, that of the middle of the 2024 to 2028 leap cycle")
    return ("**The leap-cycle average.** Where noon falls against the seasons moves by a quarter of a day from one year to the next "
            "(and back in a leap year), and it moves with longitude too, so a sharp two-hour rule makes a single calendar's long-window "
            f"hours depend on where that calendar sits. So {made} (`grazing_cells.json` → `meta.year_phases` = {n}). What remains: "
            f"{remains}. Read long-window hours as about ±1 h, not to the hour; all-hours figures move by far less. "
            "(Measured with the project's Sun code by the leap-cycle step; not recomputed here.)")


def file_sha256(path) -> str | None:
    path = Path(path)
    if not path.exists():
        return None
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def census_line(lacking, ns, ss):
    """The (d) bullet on how complete the terrain census is: partial only while elevation tiles are missing."""
    why = lacking["why"]
    tiles_missing = sum(v for k, v in why.items() if "tile" in k)
    reasons = ", ".join(f"{k}: {v:,}" for k, v in why.items())
    sample = (f"The blind sample was drawn over all measured cells without looking at any score, and {ns['horizon']['cells']} of its "
              f"{ns['cells_in_group']} northern cells and {ss['horizon']['cells']} of its {ss['cells_in_group']} southern cells have a horizon"
              + (" (without one: " + "; ".join(f"{side} {', '.join(f'{k}: {v}' for k, v in grp['without_a_horizon'].items())}"
                                              for side, grp in (("north", ns), ("south", ss)) if grp["without_a_horizon"]) + ")"
                 if ns["without_a_horizon"] or ss["without_a_horizon"] else ""))
    if tiles_missing:
        return (f"- **The census is not complete, and the part that is missing is not a random part.** {lacking['cells']:,} measured northern "
                f"cells have no horizon ({reasons}). The cells that do have one are those whose elevation tiles were already on disk, which are "
                f"the tiles around the version 2 candidates. {sample}, so the sample remains the better estimate of a typical cell; "
                "the census figures are provisional until the remaining tiles are fetched, and the two differ as the table shows.")
    return (f"- **The census covers every measured cell but those across the 180° meridian.** {lacking['cells']:,} measured northern cells "
            f"have no horizon ({reasons}); every other measured cell has one, so the census figures no longer rest on the cells whose "
            f"elevation tiles happened to be on disk. {sample}. The two are two estimates of a typical cell and differ as the table shows.")


def checks_lines(checks, now):
    """The (i) bullets of the two independent checks, from data/derived/checks.json, and their headline numbers.

    checks: the parsed checks.json or None. now: sha256 of grazing_cells.json, grazing_bins.npz and sun.py as they
    are for this report, so a check made on other files says so instead of passing for one made on these.
    """
    checks = checks or {}
    lines, numbers = [], []
    rec = checks.get("independent_recount")
    if not rec:
        lines.append("- **Counted again from first principles.** No record of the independent recount in `checks.json`; "
                     "run `scripts/independent_recount.py`.")
    else:
        n = int(rec.get("year_phases", 1))
        against = {Path(a["file"]).name: a.get("sha256") for a in rec.get("against", [])}
        same = all(against.get(k) is not None and against.get(k) == now.get(k) for k in ("grazing_cells.json", "grazing_bins.npz"))
        numbers.append(("independent recount of every cell: figures compared / outside the tolerance",
                        f"{rec['comparisons']} / {rec['outside_tolerance']}", "checks.json independent_recount (read, not recomputed here)"))
        numbers.append(("independent recount: largest difference, h a year", f(rec.get("largest_difference_h_a_year"), 2),
                        "checks.json independent_recount.largest_difference_h_a_year"))
        text = (f"- **Counted again from first principles.** A separate program that uses none of the project's code "
                f"(`scripts/independent_recount.py`: its own Sun position at 1-minute steps, the mean of "
                f"{PHASE_WORDS.get(n, str(n))} calendars 1/{n} day apart written in its own code, its own finding of the spells, its own "
                "reading of the snow grid; the Sun series and the terrain's open share are the project's) worked out the hours of all "
                f"{rec['cells']:,} cells for the {rec['targets']} targets again on {rec['ran_utc'][:10]}: {rec['comparisons']:,} figures, "
                f"{rec['outside_tolerance']} outside a tolerance of {rec['tolerance']}; the largest difference is "
                f"{f(rec.get('largest_difference_h_a_year'), 2)} h a year and {f(rec.get('largest_difference_h_in_a_ten_day_bin'), 3)} h "
                f"in a ten-day bin; {rec.get('snow_summaries_that_differ', 'n/a')} snow summaries differ. ")
        text += ("It was run on the files this report reads (same sha256 of `grazing_cells.json` and `grazing_bins.npz`). " if same else
                 "It was run on earlier files (`grazing_cells.json` or `grazing_bins.npz` has changed since), so its agreement with "
                 "this run is not established. ")
        moved = rec.get("calendar_moved")
        if moved:
            parts = [f"{v['cells_outside_tolerance']:,} of the {v['cells_with_long_window_flat_hours']:,} cells with such hours for "
                     f"{SHORT.get(t, t)} (up to {f(v.get('largest_difference_h'), 1)} h)" for t, v in moved["targets"].items()]
            text += (f"With every calendar moved {moved['days']:g} day later, the yearly long-window flat hours move by more than "
                     "that tolerance in " + ", ".join(parts) + ". ")
        lines.append(text + "(`checks.json` → `independent_recount`.)")
    hz = checks.get("jpl_horizons")
    if not hz:
        lines.append("- **Sun geometry against NASA JPL Horizons.** No record of the comparison in `checks.json`; "
                     "run `scripts/check_against_horizons.py`.")
    else:
        a, lg = hz["all_hours"], hz["hours_in_spells_of_2_h_or_more"]
        same_sun = hz.get("sun_code_sha256") is not None and hz.get("sun_code_sha256") == now.get("sun.py")
        numbers.append(("JPL Horizons: median / largest difference of all hours in the band, percent",
                        f"{f(a.get('median_abs_difference_pct'), 2)} / {f(a.get('largest_abs_difference_pct'), 1)}",
                        "checks.json jpl_horizons.all_hours (read, not recomputed here)"))
        numbers.append(("JPL Horizons: median / largest difference of hours in spells of 2 h or more, percent",
                        f"{f(lg.get('median_abs_difference_pct'), 2)} / {f(lg.get('largest_abs_difference_pct'), 1)}",
                        "checks.json jpl_horizons.hours_in_spells_of_2_h_or_more"))
        flagged = hz.get("rows_flagged") or []
        text = (f"- **Sun geometry against NASA JPL Horizons.** At {len(hz['places'])} places and {hz['periods_per_place']} ten-day periods "
                f"each, the Sun tables ({'the Sun code of this run' if same_sun else 'an earlier version of the Sun code than this run'}, "
                f"mean of {hz.get('year_phases', 'n/a')} calendars) were set beside Horizons' refracted Sun for the dates of 2026, read from "
                f"saved answers ({hz['ran_utc'][:10]}). All hours in each band differ by a median of {f(a.get('median_abs_difference_pct'), 2)} percent "
                f"(largest {f(a.get('largest_abs_difference_pct'), 1)} percent, {f(a.get('largest_abs_difference_h'), 2)} h, over {a['rows']} rows); "
                f"hours in spells of 2 h or more by a median of {f(lg.get('median_abs_difference_pct'), 2)} percent "
                f"(largest {f(lg.get('largest_abs_difference_pct'), 1)} percent, {f(lg.get('largest_abs_difference_h'), 2)} h). "
                f"{len(flagged)} rows differ by more than 5 percent or 1 hour")
        if flagged:
            text += ": " + "; ".join(
                f"{r['place']}, {r['period']} period, {SHORT.get(r['target'], r['target'])}, {r['hours']}, "
                f"{r['difference_h']:+.2f} h ({'n/a' if r.get('difference_pct') is None else format(r['difference_pct'], '+.1f')} percent; "
                f"{r['cause'] or 'cause not known'})" for r in flagged)
        lines.append(text + ". (`checks.json` → `jpl_horizons`; the raw answers are in `data/raw/horizons_check/`.)")
    return lines, numbers


def _regions(counts):
    """'n (region a, region b ...)' from a {region: count} table; '0' when empty."""
    total = sum(counts.values())
    if not total:
        return "0"
    return f"{total:,} (" + ", ".join(f"{k} {v:,}" for k, v in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))) + ")"


def winter_lines(doc, targets, year_phases=None):
    """Section (l) from winter_leads.json: what the bare-ground screen hides in the winter half."""
    if doc is None:
        return ["`winter_leads.json` is not in `data/derived`, so this section has no figures."]
    m, out = doc["meta"], []
    sq, floor = m["squares"], m["floor_bare_km2"]
    floor_key = next((k for k in doc.get("floors", {}) if float(k) == float(floor)), None)
    at_floor = doc["floors"][floor_key]["squares"] if floor_key else None
    out.append(f"The search keeps only cells whose land is at least {m['screen_relaxed']['min_bare_of_the_pipeline']:.0%} bare. "
               f"Of the {sq['northern_land_squares_in_the_land_cover_file']:,} northern land squares of the land-cover file, "
               f"{sq['below_the_screen']:,} are below that screen; {sq['below_the_screen_with_a_bare_sample']:,} of them still hold "
               f"some bare ground, and {f(at_floor)} hold at least {floor:g} km² of it. Their long-window hours in the winter half "
               "(28 September to 31 March) on snow-free ground were worked out with the pipeline's own functions, and a terrain "
               "horizon for the squares with the most hours. These squares are in no other section and in no ranking.")
    built = (m.get("built_with") or {}).get("year_phases")
    if year_phases is not None and built is not None and int(built) != int(year_phases):
        out.append("")
        out.append(f"**Made with other Sun tables.** `winter_leads.json` was built with {built} calendars and `grazing_cells.json` with "
                   f"{year_phases}; run `scripts/build_winter_leads.py` again before these figures are quoted.")
    out.append("")
    rows = []
    for t in targets:
        v = doc["targets"].get(t["id"])
        if v is None:
            rows.append([t["name"]] + ["n/a"] * 4)
            continue
        rows.append([t["name"]] + [_regions(v[key].get(WINTER_LEVEL, {})) for key in (
            "counts_by_region", "counts_by_region_after_terrain", "screened_counts_by_region", "screened_counts_by_region_after_terrain")])
    out += table(["Target", f"Hidden by the screen: squares with ≥ {WINTER_LEVEL} winter-half hours, flat horizon (regions)",
                  "the same after terrain", "Cells that pass the screen, flat horizon", "the same after terrain"], rows)
    out.append("")
    out.append(f"Source: `winter_leads.json` → `targets.<target>.counts_by_region[\"{WINTER_LEVEL}\"]`, `counts_by_region_after_terrain`, "
               f"`screened_counts_by_region`, `screened_counts_by_region_after_terrain` (measured snow odds; squares with at least {floor:g} km² "
               "of bare ground; after terrain only squares that have a horizon).")
    out.append("")
    last = targets[-1]
    leads = [x for x in (doc["targets"].get(last["id"]) or {}).get("leads", [])
             if x.get("at_main_floor") and x["snow"]["status"] == "measured"]
    leads.sort(key=lambda x: (x["winter_hours_after_terrain"] is not None, x["winter_hours_after_terrain"] or 0.0,
                              x["winter_hours_snow_free"] or 0.0), reverse=True)
    out.append(f"The ten best leads for {last['name']} (the highest limit), by winter-half hours after terrain:")
    out.append("")
    out += table(["#", "Centre (lat, lon)", "Region", "Winter-half hours after terrain", "on snow-free ground, flat horizon",
                  "Bare km² (samples)", "Snow land pixels", "Best ten-day periods"],
                 [[k, f"{x['lat']:.2f}, {x['lon']:.2f}", x["region"], f(x["winter_hours_after_terrain"], 1), f(x["winter_hours_snow_free"], 1),
                   f"{x['bare_km2']:.2f} ({x['bare_samples']})", f"{x['snow']['land_pixels']} of {x['snow'].get('block_pixels', 9)}",
                   ", ".join(f"{p['starts']} ({p['hours']:.0f} h)" for p in x.get("best_ten_day_periods", [])) or "none"]
                  for k, x in enumerate(leads[:10], 1)])
    out.append("")
    out.append(f"Source: `winter_leads.json` → `targets.{last['id']}.leads` with `at_main_floor` true and `snow.status` measured "
               "(`winter_hours_after_terrain`, `winter_hours_snow_free`, `bare_km2`, `bare_samples`, `snow.land_pixels`, `best_ten_day_periods`).")
    out.append("")
    out.append("Cautions the file carries (`meta.warnings`):")
    out.append("")
    out += [f"- {w}" for w in m.get("warnings", [])]
    if m.get("not_computed"):
        out.append(f"- Not computed for these squares: {', '.join(m['not_computed'])} (`meta.not_computed`).")
    return out


def thin_to_sites(records, km=50.0, top=None):
    """Keep records in the order given, leaving out any within km of one already kept (one site per 50 km)."""
    kept = []
    for r in records:
        if all(hav(r, k) > km for k in kept):
            kept.append(r)
            if top is not None and len(kept) == top:
                break
    return kept


def access_lines(access, recs, targets, min_hours=ACCESS_MIN_H):
    """Section (m) from access_cells.json beside cells_scored.json: how far the best areas are from scheduled flights."""
    if access is None:
        return ["`access_cells.json` is not in `data/derived`, so this section has no figures."]
    cells, m = access["cells"], access["meta"]
    north = [r for r in recs if r.get("ranked") and r.get("ranking") == "north"]

    def km(r):
        field = (cells.get(r["id"]) or {}).get("nearest_scheduled")
        return None if field is None else field["km"]

    out = [f"The straight-line distance from the centre of each area to the nearest runway with scheduled flights (`access_cells.json`, "
           f"from {m['source']['name']}, downloaded {m['source'].get('fetched_utc', 'n/a')}, {m['source'].get('licence', 'n/a')}). "
           f"Counted over the ranked northern areas with at least {min_hours:g} long-window open hours a year.", ""]
    rows, best, shares = [], [], []
    for t in targets:
        tid = t["id"]

        def hours(r):
            return r["targets"][tid].get("long_open_hours")

        def score(r):
            return r["targets"][tid]["goals"].get("lighting")
        enough = [r for r in north if hours(r) is not None and hours(r) >= min_hours]
        rows.append([t["name"], f(len(enough)), " / ".join(f(sum(1 for r in enough if km(r) is not None and km(r) <= d)) for d in ACCESS_KM),
                     f(max((hours(r) for r in north if hours(r) is not None), default=None))])
        reach = sorted((r for r in enough if score(r) is not None and km(r) is not None and km(r) <= REACH_KM),
                       key=lambda r: (score(r), hours(r)), reverse=True)
        for k, r in enumerate(thin_to_sites(reach, top=3), 1):
            field = cells[r["id"]]["nearest_scheduled"]
            best.append([t["name"], k, f"{r['lat']:.2f}, {r['lon']:.2f}", r.get("region") or "n/a", f(score(r), 3), f(hours(r)),
                         f"{field['name']} ({field['km']:.1f} km)"])
        top = sorted((r for r in north if score(r) is not None and score(r) > 0.0),
                     key=lambda r: (score(r), hours(r) or 0.0), reverse=True)[:TOP_AREAS]
        countries = Counter((cells.get(r["id"]) or {}).get("country") or "unknown" for r in top)
        shares.append([t["name"], f(len(top)), ", ".join(f"{k} {100.0 * v / len(top):.0f}%" for k, v in
                                                       sorted(countries.items(), key=lambda kv: (-kv[1], kv[0]))) or "none"])
    out += table(["Target", f"Ranked northern areas with ≥ {min_hours:g} h", "of them within " + " / ".join(f"{d} km" for d in ACCESS_KM)
                  + " of a scheduled-service airfield", "Most long-window open hours of any ranked area"], rows)
    out.append("")
    out.append("Source: `cells_scored.json` → `ranked`, `ranking`, `targets.<target>.long_open_hours`; `access_cells.json` → "
               "`cells.<id>.nearest_scheduled.km`. The southern areas are left out: no listed Antarctic runway has scheduled service.")
    out.append("")
    out.append(f"Best reachable areas: the three best lighting areas per target within {REACH_KM} km of a scheduled-service airfield, one per 50 km:")
    out.append("")
    out += table(["Target", "#", "Centre (lat, lon)", "Region", "Lighting score", "Long-window open hours a year", "Nearest scheduled-service airfield"],
                 best) if best else ["No area qualifies for any target."]
    out.append("")
    out.append("Source: `cells_scored.json` → `targets.<target>.goals.lighting`, `long_open_hours` (ties by hours); `access_cells.json` → "
               "`nearest_scheduled.name`, `.km`.")
    out.append("")
    out.append(f"Share of the top {TOP_AREAS} lighting areas by country (areas, not thinned to one per 50 km):")
    out.append("")
    out += table(["Target", "Areas", "Countries (two-letter codes of the airports table; NO includes Svalbard and Jan Mayen)"], shares)
    out.append("")
    out.append("Source: `cells_scored.json` → `goals.lighting`; `access_cells.json` → `cells.<id>.country` (a guess from the nearest table "
               "record within 300 km, not a border test; unknown where it is null).")
    out.append("")
    out.append(f"What the distance is not: {m['what_this_is_not']} (`access_cells.json` → `meta.what_this_is_not`)")
    return out


def build():
    """The lines of RESULTS.md and the list of headline numbers, from the files as they stand."""
    NUMBERS.clear()
    g = load("grazing_cells.json")
    meta, cells = g["meta"], g["cells"]
    targets = meta["targets"]
    tids = [t["id"] for t in targets]
    short_names(targets)
    old_tids = [t for t in tids if t in OLD_FOUR]    # version 1 and version 2 hold these four only
    tname = {t["id"]: t["name"] for t in targets}
    limit = {t["id"]: t["limit_deg"] for t in targets}
    by_id = {c["id"]: c for c in cells}
    lp = load("latitude_profile.json")
    prof = {r["lat"]: r["targets"] for r in lp["profile"]}
    val = load("validation.json")
    val2 = load("validation_v2.json")
    scored = load("cells_scored.json")
    recs = scored["cells"]
    rec_of = {r["id"]: r for r in recs}
    recs2 = load("cells_scored_v2.json")["cells"]
    cand = load("candidates.json")
    v1 = load("light_cells_v1.json")
    stations = load("snow_validation_many.json")
    cloud_file = load("cloud_cells.json")
    south_sites = json.loads((REFERENCE / "antarctic_sites.json").read_text())
    WINTER = meta["winter_bins_north"]

    gridded = [c for c in cells if c["gridded"]]
    north = [c for c in gridded if c["hemisphere"] == "N"]
    south = [c for c in gridded if c["hemisphere"] == "S"]
    measured = [c for c in north if c["snow"]["status"] == "measured"]
    doubtful = [c for c in north if c["snow"]["status"] == "doubtful"]
    nodata = [c for c in north if c["snow"]["status"] == "no data"]
    bp = val["big_picture_north"]
    lacking = bp["cells_without_a_horizon"]
    hstate = Counter(horizon_state(c) for c in cells)
    n_h, n_tile, n_anti = hstate["horizon"], hstate["elevation tile not fetched"], hstate["window across the antimeridian"]
    rankable = [c for c in measured if c["bare"] >= scored["meta"]["rank_min_bare"]]
    rankable_waiting = [c for c in rankable if not has_h(c)]
    s_h = [c for c in south if has_h(c)]
    odds_used = Counter(c["snow"].get("odds_used") for c in north)

    L = []
    A = L.append
    A("# LuniMartian Atlas: results, version 3")
    A("")
    A(f"Generated {datetime.now().strftime('%A %-d %B %Y, %H:%M')} Pacific by `scripts/make_results.py` from the files in "
      "`data/derived/` as they stood after the chain was run again on the version 3 inputs. Every number below was read from those files or "
      "computed from them in that run; each table names the file and field it comes from. Unknown values are written `n/a`, never 0. "
      "Version 2 of this file is kept as `RESULTS_v2.md`; section (k) sets the two side by side.")
    A("")
    A(f"**What this is.** A measured search for places and dates on Earth where the Sun sits as low as it does at {len(tids)} "
      "candidate landing regions near the Moon's south pole, for hours at a time, on bare and snow-free ground, with the surrounding terrain taken into account.")
    A("")
    A("## How to read this")
    A("")
    A("- **Grazing hour**: an hour with the Sun's apparent centre above the horizon and at or below a lunar site's highest Sun. "
      f"The {len(tids)} lunar targets and their limits (`grazing_cells.json` → `meta.targets[].limit_deg`): "
      + "; ".join(f"{tname[t]} {limit[t]:.2f}°" for t in tids) + ".")
    A(f"- **Long window (the per-day rule of version 3)**: an unbroken spell of at least {meta['stretch_min_h']:g} h with the Sun in that band, "
      f"over a flat horizon, followed day by day at {meta.get('step_minutes', 1):g}-minute steps. A spell that runs through midnight is one spell; "
      "each of its minutes is counted in the day and ten-day bin in which it falls; a Sun that stays in the band for more than 24 h counts in full "
      f"(`meta.long_rule` = \"{meta.get('long_rule')}\", `meta.stretch_min_h`). \"Long-window hours\" are the hours inside such spells. "
      "Version 2 instead took or dropped a whole ten-day bin by its median longest spell.")
    A("- Three versions are kept apart: **flat** (Sun geometry only), **snow-free** (times the odds that the ground is snow-free "
      "in that ten-day bin, NOAA IMS 4 km maps of October 2015 to September 2025), **open** (snow-free, and the terrain does not hide the Sun; "
      f"only for the {n_h:,} of {len(cells):,} cells that have a computed terrain horizon).")
    A(f"- **Which snow odds a cell uses** (`snow.odds_used`): a cell with status \"measured\" uses the snow maps as they read ({odds_used['as mapped']:,} northern cells); "
      f"a \"doubtful\" cell uses the stale-flag rule, which gives the lower figure ({odds_used['stale-flag rule']:,} cells); \"no data\" cells have no odds; "
      "southern cells are \"unmeasured\". Both figures are stored for every northern cell with odds "
      "(`long_snow_free_hours_as_mapped`, `long_snow_free_hours_with_rule`).")
    A("- **Typical clear-sky hours**: open hours times the share of the sky that is clear in a typical month (section (j)). "
      "A displayed column only; it enters no score, and it is not the chance that a low Sun is visible.")
    A("- Winter half = 28 September to 31 March; summer half = 1 April to 27 September (`meta.winter_bins_north`, `meta.summer_bins_north`). "
      "Southern rock season = 27 November to 1 March (`meta.summer_bins_south`).")
    A("- A cell is about 11 km across. Bare ground is the share of the cell's land that is bare (`bare`). On the web page a cell is called an \"area\"; "
      "the data files and this file keep the word cell.")
    A("")
    n_rec = num("records in grazing_cells.json", len(cells), "len(cells) of grazing_cells.json")
    st = Counter(c["snow"]["status"] for c in gridded)
    num("gridded northern cells", len(north), "cells with gridded true and hemisphere N, counted from grazing_cells.json")
    num("gridded southern cells", len(south), "cells with gridded true and hemisphere S, counted from grazing_cells.json")
    num("measured northern cells", st["measured"], "gridded cells with snow.status measured, counted from grazing_cells.json")
    num("doubtful northern cells", st["doubtful"], "gridded cells with snow.status doubtful")
    num("no-data northern cells", st["no data"], "gridded cells with snow.status no data")
    n_t = sum(r["terrain"] is not None for r in recs)
    num("cells with a terrain horizon", n_h, "records of grazing_cells.json whose horizon is not null and not skipped")
    num("cells waiting for an elevation tile (no horizon)", n_tile, "records of grazing_cells.json whose horizon.skipped begins 'tile not fetched'")
    num("cells refused at the antimeridian (no horizon)", n_anti, "records of grazing_cells.json whose horizon.skipped names the antimeridian")
    num("measured northern cells with a horizon / without", f"{bp['cells_with_a_horizon']} / {lacking['cells']}", "validation.json big_picture_north.cells_with_a_horizon and .cells_without_a_horizon.cells; recounted here from grazing_cells.json")
    assert bp["cells_with_a_horizon"] == sum(has_h(c) for c in measured)
    num("cells with slope statistics", n_t, "cells_scored.json records whose terrain is not null")
    rn = [r for r in recs if r["ranked"] and r["ranking"] == "north"]
    rs = [r for r in recs if r["ranked"] and r["ranking"] == "south"]
    num("ranked northern cells", len(rn), "cells_scored.json records with ranked true and ranking north")
    num("ranked southern cells", len(rs), "cells_scored.json records with ranked true and ranking south")
    num("measured northern cells with bare >= 0.25 that wait for a horizon", len(rankable_waiting), "measured gridded cells of grazing_cells.json with bare >= rank_min_bare and no horizon")
    A("### What was searched")
    A("")
    L += table(["What", "Count", "Source"], [
        ["Cell records", f(n_rec), "`grazing_cells.json` → `cells`"],
        ["Northern cells in the search (bare ≥ 0.15, 59 to 84 N)", f(len(north)), "`gridded` true, `hemisphere` N"],
        ["of them with measured snow odds", f(st["measured"]), "`snow.status` = measured"],
        ["of them doubtful / no snow data (listed, not ranked)", f"{st['doubtful']} / {st['no data']}", "`snow.status`"],
        ["Southern cells (bare ≥ 0.15, land share ≥ 0.2, 59 to 87.5 S); snow not measured", f(len(south)), "`gridded` true, `hemisphere` S"],
        ["Named-site cells outside those screens (reported apart)", f(sum(not c["gridded"] for c in cells)), "`gridded` false"],
        ["Cells with a terrain horizon", f"{n_h:,} of {len(cells):,}", "`horizon` with `north_deg`"],
        ["Cells without one: elevation tiles not fetched / window across the antimeridian", f"{n_tile:,} / {n_anti}", "`horizon.skipped`"],
        ["Measured northern cells with a horizon / without", f"{bp['cells_with_a_horizon']:,} / {lacking['cells']:,}", "`validation.json` → `big_picture_north.cells_with_a_horizon`, `.cells_without_a_horizon`"],
        ["Southern cells with a horizon / without", f"{len(s_h):,} / {len(south) - len(s_h)}", "`horizon`, `hemisphere` S, `gridded`"],
        ["Cells with slope statistics", f(n_t), "`cells_scored.json` → `terrain`"],
        ["Ranked cells, north / south", f"{len(rn):,} / {len(rs)}", "`cells_scored.json` → `ranked`, `ranking`"],
        ["Measured northern cells with bare ≥ 0.25 that cannot be ranked because they have no horizon", f"{len(rankable_waiting):,} of {len(rankable):,}", "`bare`, `snow.status`, `horizon`"],
    ])
    A("")
    A(f"The {n_tile + n_anti:,} cells without a horizon ({n_tile:,} without an elevation tile on disk, {n_anti} across the antimeridian) keep complete flat and "
      "snow-free hours; their open hours, clear-sky hours and light scores are `n/a`, and they are in no ranking.")
    A("")

    # ---- (a)
    A("## (a) Where on Earth the Sun grazes the horizon for hours")
    A("")
    A("Pure Sun geometry: flat horizon, standard refraction, no snow, no terrain. Hours per year.")
    A("")
    show = [0.0, 30.0, 45.0, 50.0, 55.0, 57.5, 59.0, 60.0, 62.5, 65.0, 66.5, 67.5, 70.0, 72.5, 75.0, 80.0, 85.0, 89.5]
    rows = []
    for lat in show:
        rows.append([f"{lat:g} N"] + [f"{f(prof[lat][t]['flat_hours'])} / {f(prof[lat][t]['long_flat_hours']['2'])} / {f(prof[lat][t]['longest_spell_h'], 1)}" for t in tids])
    for lat in (-59.0, -66.5, -70.0, -77.5, -85.0):
        rows.append([f"{-lat:g} S"] + [f"{f(prof[lat][t]['flat_hours'])} / {f(prof[lat][t]['long_flat_hours']['2'])} / {f(prof[lat][t]['longest_spell_h'], 1)}" for t in tids])
    L += table(["Latitude"] + [f"{SHORT[t]} (≤ {limit[t]:.2f}°): all hours / hours inside spells of 2 h or more / longest single spell of the year, h" for t in tids], rows)
    A("")
    A("Source: `latitude_profile.json` → `profile[].targets.<target>.flat_hours`, `.long_flat_hours[\"2\"]`, `.longest_spell_h` "
      "(the longest single unbroken spell of the year; near the poles it runs for days).")
    A("")
    eq = {t: prof[0.0][t]["flat_hours"] for t in tids}
    peak = {t: max(lp["profile"], key=lambda r: r["targets"][t]["flat_hours"]) for t in tids}
    peak_long = {t: max((r for r in lp["profile"] if r["lat"] > 0), key=lambda r: r["targets"][t]["long_flat_hours"]["2"]) for t in tids}
    for t in tids:
        num(f"flat hours at the equator, {t}", eq[t], "latitude_profile.json profile row lat 0.0, flat_hours")
        num(f"latitude of most flat hours, {t}", f"{peak[t]['lat']} ({peak[t]['targets'][t]['flat_hours']} h)", "max of flat_hours over the 359 profile rows")
    A("- Grazing hours exist at every latitude, but below the latitudes in the next table they come in spells of under an hour at "
      "sunrise and sunset. At the equator the yearly total is "
      + ", ".join(f"{f(eq[t])} h ({SHORT[t]})" for t in tids) + ", and the longest spell is "
      + ", ".join(f"{prof[0.0][t]['longest_spell_h']:.2f} h" for t in tids) + ".")
    A("- The yearly total is largest near the polar circle: "
      + "; ".join(f"{SHORT[t]} {f(peak[t]['targets'][t]['flat_hours'])} h at {abs(peak[t]['lat']):g}° {'N' if peak[t]['lat'] > 0 else 'S'}" for t in tids)
      + f" ({', '.join(f'{peak[t]['targets'][t]['flat_hours'] / eq[t]:.1f}' for t in tids)} times the equator's total).")
    A("- Long-window hours in the northern half are largest at "
      + "; ".join(f"{SHORT[t]} {f(peak_long[t]['targets'][t]['long_flat_hours']['2'])} h at {peak_long[t]['lat']:g}° N" for t in tids) + ".")
    A("")
    A("### Lowest latitude with spells of 1, 2 and 3 hours")
    A("")
    th = lp["thresholds"]
    rows = []
    for t in tids:
        n, s = th[t]["N"], th[t]["S"]
        rows.append([f"{tname[t]} (≤ {limit[t]:.2f}°)"] + [f"{n['lowest_lat_with_long_window'][k]:.2f} N / {abs(s['lowest_lat_with_long_window'][k]):.2f} S" for k in ("1", "2", "3")]
                    + [f"{n['lowest_lat_with_all_day_low_sun']:.2f} N / {abs(s['lowest_lat_with_all_day_low_sun']):.2f} S"])
        for k in ("1", "2", "3"):
            num(f"lowest latitude with a {k} h long window, {t}, north", n["lowest_lat_with_long_window"][k], f"latitude_profile.json thresholds.{t}.N.lowest_lat_with_long_window[{k}]")
    L += table(["Target", "1 h spell", "2 h spell", "3 h spell", "Sun under the limit all day (the old measure)"], rows)
    A("")
    A("Source: `latitude_profile.json` → `thresholds.<target>.<N|S>.lowest_lat_with_long_window[\"1\"|\"2\"|\"3\"]` and "
      "`.lowest_lat_with_all_day_low_sun`; found at steps of 0.05°. **Per-day rule (version 3):** the lowest latitude at which at least one day of the year has an unbroken spell that long.")
    A("")
    A("The same thresholds under the version 2 rule, kept for comparison (the lowest latitude with a ten-day bin whose median longest daily spell, at two-minute steps, reaches the minimum):")
    A("")
    rows = []
    for t in tids:
        n, s = th[t]["N"], th[t]["S"]
        rows.append([f"{tname[t]} (≤ {limit[t]:.2f}°)"] + [f"{n['lowest_lat_with_long_window_bin_median'][k]:.2f} N / {abs(s['lowest_lat_with_long_window_bin_median'][k]):.2f} S" for k in ("1", "2", "3")])
        for k in ("1", "2", "3"):
            num(f"lowest latitude with a {k} h long window under the version 2 bin-median rule, {t}, north", n["lowest_lat_with_long_window_bin_median"][k], f"latitude_profile.json thresholds.{t}.N.lowest_lat_with_long_window_bin_median[{k}]")
    L += table(["Target", "1 h spell", "2 h spell", "3 h spell"], rows)
    A("")
    A("Source: `latitude_profile.json` → `thresholds.<target>.<N|S>.lowest_lat_with_long_window_bin_median[\"1\"|\"2\"|\"3\"]`.")
    A("")
    A("### What the search band does not cover")
    A("")
    A("The search looked at land from 59 to 84 N and from 59 to 87.5 S (`twinfinder/grid.py`: `MIN_LAT`, `MAX_LAT`, `SOUTH_MIN_LAT`, `SOUTH_MAX_LAT`). "
      "Degrees of latitude between the first long window and the band edge, in each hemisphere:")
    A("")
    rows = []
    for t in tids:
        row = [SHORT[t]]
        for k in ("1", "2", "3"):
            lo = th[t]["N"]["lowest_lat_with_long_window"][k]
            gap = 59.0 - lo
            row.append(f"{gap:.2f}° ({lo:.2f} to 59)" if gap > 0 else f"none (starts at {lo:.2f})")
            if gap > 0:
                num(f"latitude not covered below 59, {k} h spells, {t}", f"{gap:.2f} deg", f"59.0 minus thresholds.{t}.N.lowest_lat_with_long_window[{k}]")
        rows.append(row)
    L += table(["Target", "1 h spells", "2 h spells (the rule used)", "3 h spells"], rows)
    A("")
    A("Source: 59.0 minus `latitude_profile.json` → `thresholds.<target>.N.lowest_lat_with_long_window[\"1\"|\"2\"|\"3\"]` (the table above; the southern values are the same to 0.05°).")
    A("")
    outside = [t for t in tids if (th[t]["N"]["lowest_lat_with_long_window"]["2"] or 90.0) < 59.0]
    for t in outside:
        start = th[t]["N"]["lowest_lat_with_long_window"]["2"]
        h58, h585, h59 = (prof[lat][t]["long_flat_hours"]["2"] for lat in (58.0, 58.5, 59.0))
        num(f"{SHORT[t]} long-window flat hours at 58.0, 58.5, 59.0 N", f"{h58}, {h585}, {h59}",
            "latitude_profile.json profile rows 58.0, 58.5, 59.0, long_flat_hours[2]")
        A(f"- With the 2 h rule used for the ranking, {SHORT[t]} loses ground: its long windows begin at {start:.2f}°, so a strip "
          f"of {59 - start:.2f}° on each side of the Earth was not looked at. Flat-horizon long-window hours there: {f(h58)} h a "
          f"year at 58.0 N, {f(h585)} h at 58.5 N, {f(h59)} h at 59.0 N (`profile[].targets.{t}.long_flat_hours[\"2\"]`).")
    if not outside:
        A("- With the 2 h rule used for the ranking, every target's belt starts inside the band.")
    A("- With a 1 h rule the belt would reach much further toward the equator (first column); none of that ground was searched.")
    A("- With a 3 h rule every target's belt starts inside the band.")
    A("")

    # ---- (b) and (c)
    num("bare ground of the measured northern cells, km2", bp["measured_bare_km2"], "validation.json big_picture_north.measured_bare_km2; equals my own sum of bare_km2 over measured cells")


    measured_h = [c for c in measured if has_h(c)]
    recount = {"counts": 0, "differ": 0}

    def season_section(season, label):
        rows = []
        end = {"winter_half": "_winter", "summer_half": "_summer"}[season]
        for t in tids:
            b = bp["targets"][t]["long_snow_free_hours"][season]
            o = bp["targets"][t]["long_open_hours_among_cells_with_a_horizon"][season]
            for mine, theirs in ((level_counts(measured, t, f"long_snow_free_hours{end}"), b),
                                 (level_counts(measured_h, t, f"long_open_hours{end}"), o)):
                recount["counts"] += 2 * len(LEVELS_H)
                recount["differ"] += levels_that_differ(mine, theirs)
            rows.append([SHORT[t]] + [f"{f(b[k]['cells'])} cells, {f(b[k]['bare_km2'])} km²" for k in ("50", "100", "200")]
                        + [" / ".join(f(o[k]["cells"]) for k in ("50", "100", "200"))])
            for k in ("50", "100", "200"):
                num(f"measured cells with >= {k} long-window snow-free hours, {label}, {t}", f"{b[k]['cells']} cells, {b[k]['bare_km2']} km2",
                    f"validation.json big_picture_north.targets.{t}.long_snow_free_hours.{season}[{k}]; counted again here from grazing_cells.json (level_counts)")
        return table(["Target", "≥ 50 h", "≥ 100 h", "≥ 200 h", f"with the real horizon, over the {bp['cells_with_a_horizon']:,} measured cells that have one ({lacking['cells']:,} have none): cells ≥ 50 / 100 / 200 h"], rows)


    def cal_share(t):
        cal = bp["targets"][t]["calendar_hours_times_bare_km2"]
        return sum(cal[b] for b in WINTER) / sum(cal), cal


    A("## (b) The north in the winter half (28 September to 31 March)")
    A("")
    A(f"Long-window hours on snow-free ground, flat horizon, over the {len(measured):,} measured northern cells "
      f"({f(bp['measured_bare_km2'])} km² of bare ground; {bp['targets'][tids[0]]['long_snow_free_hours']['year']['unknown_cells']} of the cells have unknown hours and are counted in no column).")
    A("")
    winter_table, summer_table = season_section("winter_half", "winter half"), season_section("summer_half", "summer half")
    num("counts of (b) and (c) made again in this run from grazing_cells.json", f"{recount['counts']} counts, {recount['differ']} differ",
        "make_results.level_counts over the measured cells (snow-free hours) and the measured cells with a horizon (open hours), against validation.json")
    L += winter_table
    A("")
    A("Source: `validation.json` → `big_picture_north.targets.<target>.long_snow_free_hours.winter_half.<50|100|200>.cells` and `.bare_km2`; "
      "last column `...long_open_hours_among_cells_with_a_horizon.winter_half` (every measured cell that has a terrain horizon; the cells without one are described in (i), so that column is a lower bound on the true count). "
      "The cell counts and areas of this table and of the one in (c), with their real-horizon columns, were made again in this run from `grazing_cells.json` "
      f"(`targets.<target>.long_snow_free_hours_winter`, `_summer`, `long_open_hours_winter`, `_summer`, `bare_km2`): {recount['counts']} counts, {recount['differ']} differ.")
    A("")
    for t in tids:
        share, cal = cal_share(t)
        num(f"winter-half share of long-window snow-free hours x bare km2, {t}", f"{share:.4f}", f"sum of validation.json big_picture_north.targets.{t}.calendar_hours_times_bare_km2 over winter bins / over all bins")
    A("- Share of all long-window snow-free hours × bare km² that falls in the winter half: "
      + "; ".join(f"{SHORT[t]} {cal_share(t)[0]:.1%}" for t in tids)
      + " (`big_picture_north.targets.<target>.calendar_hours_times_bare_km2`, winter bins over all bins).")
    wr = {t: val["regions"][t]["measured_cells_100_long_snow_free_hours_winter_half"] for t in tids}
    A("- Regions of the cells with at least 100 winter-half hours: "
      + "; ".join(f"{SHORT[t]}: " + (", ".join(f"{k} {v}" for k, v in wr[t].items()) or "no cell") for t in tids)
      + " (`validation.json` → `regions.<target>.measured_cells_100_long_snow_free_hours_winter_half`).")
    best_rows = []
    for t in tids:
        known = [c for c in measured if c["targets"][t]["long_snow_free_hours_winter"] is not None]
        best = max(known, key=lambda c: c["targets"][t]["long_snow_free_hours_winter"])
        v = best["targets"][t]
        best_rows.append([SHORT[t], f"{best['lat']:.2f}, {best['lon']:.2f}", best["region"], f"{best['bare']:.2f}", f(v["long_snow_free_hours_winter"], 1),
                          f(v["long_open_hours_winter"], 1), f(v["poleward_share"], 2)])
        num(f"most winter-half long-window snow-free hours in one measured cell, {t}", f"{v['long_snow_free_hours_winter']} h at {best['id']}", "max of long_snow_free_hours_winter over measured cells of grazing_cells.json")
    A("")
    A("The measured cell with the most winter-half hours per target:")
    A("")
    L += table(["Target", "Cell centre", "Region", "Bare", "Winter-half hours, snow-free", "the same with the real horizon", "Share of the year's long-window hours with the Sun on the poleward side"], best_rows)
    A("")
    A("Source: `grazing_cells.json` → `targets.<target>.long_snow_free_hours_winter`, `long_open_hours_winter`, `poleward_share`. "
      "A poleward share near 0 means the low Sun stands in the south: dawn, dusk and low noon, not midnight Sun.")
    A("")

    A("## (c) The north in the summer half (1 April to 27 September): the midnight-Sun side")
    A("")
    L += summer_table
    A("")
    A("Source: as in (b), with `summer_half` (`long_snow_free_hours_summer`, `long_open_hours_summer` in `grazing_cells.json`).")
    A("")
    for t in tids:
        share, cal = cal_share(t)
        top = sorted(range(36), key=lambda b: -cal[b])[:3]
        A(f"- {SHORT[t]}: {1 - share:.1%} of the long-window snow-free hours × bare km² fall in the summer half; the three ten-day bins "
          f"with the most are {', '.join(f'{bin_dates(b)} ({cal[b] / sum(cal):.0%})' for b in top)}.")
    A("")
    rows = []
    for t in tids:
        reg = val["regions"][t]["measured_cells_100_long_snow_free_hours_summer_half"]
        items = list(reg.items())
        rows.append([SHORT[t], f(sum(reg.values())), ", ".join(f"{k} {v:,}" for k, v in items[:6]) + (f"; other regions {sum(v for _, v in items[6:]):,}" if len(items) > 6 else "")])
    L += table(["Target", "Cells with ≥ 100 summer-half hours", "Regions (cells)"], rows)
    A("")
    A("Source: `validation.json` → `regions.<target>.measured_cells_100_long_snow_free_hours_summer_half`.")
    A("")
    rows = []
    for t in tids:
        group = [c for c in measured if (c["targets"][t]["long_snow_free_hours_summer"] or 0) >= 100 and c["targets"][t]["poleward_share"] is not None]
        if group:
            shares = [c["targets"][t]["poleward_share"] for c in group]
            lats = [c["lat"] for c in group]
            rows.append([SHORT[t], f(len(group)), f"{pct(shares, 50):.2f}", f"{pct(shares, 10):.2f} to {pct(shares, 90):.2f}", f"{pct(lats, 10):.1f} to {pct(lats, 90):.1f} N"])
            num(f"median poleward share of cells with >= 100 summer-half hours, {t}", f"{pct(shares, 50):.2f}", "median of poleward_share over measured cells with long_snow_free_hours_summer >= 100")
    L += table(["Target", "Cells with ≥ 100 summer-half hours", "Median share of long-window hours with the Sun within 90° of north", "10th to 90th percentile", "Latitudes, 10th to 90th percentile"], rows)
    A("")
    A("Source: `grazing_cells.json` → `targets.<target>.poleward_share` (whole year, flat horizon), `long_snow_free_hours_summer`, `lat`. "
      "A share above 0.5 means most of the long-window hours come with the Sun in the northern half of the sky, around local midnight.")
    A("")

    # ---- (d)
    A("## (d) What real terrain takes away")
    A("")
    tsl = val["terrain_share_left"]
    ns, na, ss, sa = tsl["north"]["blind_sample"], tsl["north"]["all_measured"], tsl["south"]["blind_sample"], tsl["south"]["all"]
    A(f"Version 2 could measure this only on a blind sample: {ns['cells_in_group']} measured northern and {ss['cells_in_group']} southern cells drawn without looking at any score "
      f"(`candidates.json` → `why` contains `sample`). Version 3 has a terrain horizon for {na['horizon']['cells']:,} of the {na['cells_in_group']:,} measured northern cells "
      f"and {sa['horizon']['cells']:,} of the {sa['cells_in_group']:,} southern cells, so the same statistic is given for all of them beside the sample's. "
      "The share is long-window open hours ÷ long-window flat-horizon hours per cell (north: snow-free hours; south: rock-season hours), over the cells that have a horizon and any such hours.")
    A("")
    rows = []
    for t in tids:
        rows.append([SHORT[t], ns[t]["cells"], spread_text(ns[t]), f(na[t]["cells"]), spread_text(na[t]),
                     ss[t]["cells"], spread_text(ss[t]), f(sa[t]["cells"]), spread_text(sa[t])])
        num(f"median share of long-window hours left by terrain, north: blind sample / all measured cells with a horizon, {t}",
            f"{ns[t]['median']} (n {ns[t]['cells']}) / {na[t]['median']} (n {na[t]['cells']})", f"validation.json terrain_share_left.north.blind_sample.{t} and .all_measured.{t}")
        num(f"median share of long-window rock-season hours left by terrain, south: blind sample / all cells with a horizon, {t}",
            f"{ss[t]['median']} (n {ss[t]['cells']}) / {sa[t]['median']} (n {sa[t]['cells']})", f"validation.json terrain_share_left.south.blind_sample.{t} and .all.{t}")
    L += table(["Target", "North, blind sample: cells", "share left, 10th / 25th / median / 75th / 90th percentile", "North, every measured cell with a horizon: cells", "share left",
                "South, blind sample: cells", "share left", "South, every cell with a horizon: cells", "share left"], rows)
    A("")
    A("Source: `validation.json` → `terrain_share_left.<north|south>.<blind_sample|all_measured|all>.<target>` (`cells`, `p10`, `p25`, `median`, `p75`, `p90`), "
      "computed from `grazing_cells.json` → `targets.<target>.long_open_hours` ÷ `long_snow_free_hours` (north), `long_summer_rock_open_hours` ÷ `long_summer_rock_hours` (south).")
    A("")
    num("median terrain horizon north / south, deg: northern blind sample", f"{ns['horizon']['north_deg']} / {ns['horizon']['south_deg']}", "validation.json terrain_share_left.north.blind_sample.horizon")
    num("median terrain horizon north / south, deg: all measured northern cells with a horizon", f"{na['horizon']['north_deg']} / {na['horizon']['south_deg']} (n {na['horizon']['cells']})", "validation.json terrain_share_left.north.all_measured.horizon")
    A("- The lower the Sun limit, the more the terrain takes. The median measured northern cell with a horizon keeps "
      + ", ".join(f"{na[t]['median']:.1%} ({SHORT[t]})" for t in tids) + "; the blind sample said "
      + ", ".join(f"{ns[t]['median']:.1%}" for t in tids) + ".")
    A(f"- Median terrain horizon: blind sample {ns['horizon']['north_deg']:.2f}° looking north and {ns['horizon']['south_deg']:.2f}° looking south; "
      f"all {na['horizon']['cells']:,} measured cells with a horizon {na['horizon']['north_deg']:.2f}° and {na['horizon']['south_deg']:.2f}° "
      "(`terrain_share_left.north.<group>.horizon`; the median over the cell's land of the horizon in the due-north and due-south sectors).")
    A(census_line(lacking, ns, ss))
    A("")
    A("Named examples (the cell that holds the site; hours are for Malapert, long windows, whole year):")
    A("")
    site_reports = {s["name"]: s for s in val["named_sites"]["sites"]}
    rows = []
    for name in ("Qaqortorsuaq anorthosite, Greenland", "Lofoten anorthosite (Nusfjord), Norway", "Longyearbyen, Svalbard", "Myrdalssandur sand plain, Iceland"):
        s = site_reports[name]
        m = s["targets"]["malapert"]
        hz = s["horizon"] if s["horizon"] and "skipped" not in s["horizon"] else {}
        left = m["open"]["long"]["year"] / m["snow_free"]["long"]["year"] if m["snow_free"]["long"]["year"] else None
        rows.append([name, s["cell"], f"{f(hz.get('north_deg'), 2)}° / {f(hz.get('south_deg'), 2)}°", f(m["flat"]["long"]["year"], 1), f(m["snow_free"]["long"]["year"], 1),
                     f(m["open"]["long"]["year"], 1), "n/a" if left is None else f"{left:.0%}"])
        num(f"{name}: Malapert long-window hours flat / snow-free / open", f"{m['flat']['long']['year']} / {m['snow_free']['long']['year']} / {m['open']['long']['year']}",
            "validation.json named_sites.sites[].targets.malapert.<flat|snow_free|open>.long.year")
    L += table(["Site", "Cell", "Horizon north / south", "Flat", "Snow-free", "Open", "Share of snow-free hours left"], rows)
    A("")
    A("Source: `validation.json` → `named_sites.sites[].targets.malapert.<flat|snow_free|open>.long.year` and `.horizon`.")
    A("")

    # ---- (e)
    A("## (e) The top sites per target")
    A("")
    A("Scores: light = min(1, long-window open hours ÷ 200); \"lighting\" = √(light × bare); \"full\" = fourth root of light × terrain × rock × bare "
      f"(`cells_scored.json` → `meta.full_hours`, `meta.goals`). Only measured northern cells with a horizon and bare ≥ {scored['meta']['rank_min_bare']} are ranked "
      f"({len(rn):,} cells, though {sum(any(v['goals']['lighting'] is None for v in r['targets'].values()) for r in rn)} of them have unknown snow-free hours, so no score, and are in no table; "
      f"{len(rankable_waiting):,} more measured cells with enough bare ground have no horizon and could not compete), "
      f"one site per {scored['meta']['same_site_km']:g} km. Cells with equal scores are ordered by their long-window open hours. "
      "The clear-sky column is for information (see (j)); it enters no score.")
    A("")
    GOAL_LABEL = {"lighting": "Low Sun on bare ground", "full": "Full match"}
    txt = (D / "ranking.txt").read_text().splitlines()
    i_north = txt.index("NORTH: measured cells with a horizon")
    i_doubt = next(i for i, l in enumerate(txt) if l.startswith("DOUBTFUL SNOW OR NO SNOW DATA"))
    i_south = next(i for i, l in enumerate(txt) if l.startswith("SOUTH: "))


    def printed(section, goal, t):
        """The (lat, lon) rows that ranking.txt prints for one table."""
        lo, hi = (i_north, i_doubt) if section == "north" else (i_south, len(txt))
        labels = {'lighting': 'Low Sun on bare ground', 'shadows': 'Driving in long shadows', 'geology': 'Geology training', 'full': 'Full match'}
        head = f"{labels[goal]} | {tname[t]} (Sun at or below {limit[t]:.2f} deg) | all sites"
        start = next(i for i in range(lo, hi) if txt[i] == head)
        out = []
        for line in txt[start + 1:hi]:
            if not line.strip():
                break
            m = re.match(r"\s+(\d\.\d\d)\s+(-?\d+\.\d\d)\s+(-?\d+\.\d\d)\s", line)
            if m:
                out.append((float(m.group(2)), float(m.group(3))))
        return out


    def my_sites(ranking, goal, t, n=10, records=None):
        field = "long_open_hours" if ranking == "north" else "long_summer_rock_open_hours"
        pool = [r for r in (recs if records is None else records)
                if r["ranking"] == ranking and r["ranked"] and (r["targets"][t]["goals"][goal] or 0) > 0]
        pool.sort(key=lambda r: (-r["targets"][t]["goals"][goal], -(r["targets"][t][field] or 0.0)))
        sites = []
        for r in pool:
            if all(hav(r, s) >= 50.0 for s in sites):
                sites.append(r)
            if len(sites) == n:
                break
        return sites, pool


    mismatch = 0
    tables_checked = 0
    for ranking in ("north", "south"):
        for goal in ("lighting", "shadows", "geology", "full"):
            for t in tids:
                mine = [(round(r["lat"], 2), round(r["lon"], 2)) for r in my_sites(ranking, goal, t)[0]]
                tables_checked += 1
                if mine != printed(ranking, goal, t):
                    mismatch += 1
                    print("RANKING MISMATCH", ranking, goal, t, mine[:3], printed(ranking, goal, t)[:3], file=sys.stderr)
    num("ranking tables of ranking.txt rebuilt from cells_scored.json by my own sort and 50 km rule", f"{tables_checked} tables, {mismatch} differ", "make_results.py: sort ranked cells by (score, hours), keep one per 50 km, compare lat/lon rows with ranking.txt")


    def known_text(r):
        if r["known"]:
            return f"known: {r['known']['name']} ({r['known']['distance_km']:.0f} km)"
        if r["known_region"]:
            return "known: " + r["known_region"].split(":")[0]
        return "little known"


    def side_text(share, hemisphere):
        if share is None:
            return "n/a"
        pole, equator = ("north", "south") if hemisphere == "N" else ("south", "north")
        if share >= 0.5:
            return f"{share:.0%} of the hours with the Sun in the {pole} (around midnight)"
        return f"{1 - share:.0%} of the hours with the Sun in the {equator} (dawn, dusk, low noon)"


    def site_rows(ranking, goal, t, n):
        sites, pool = my_sites(ranking, goal, t, n)
        rows = []
        for k, r in enumerate(sites, start=1):
            v = r["targets"][t]
            south_ = r["hemisphere"] == "S"
            hours = v["long_summer_rock_open_hours"] if south_ else v["long_open_hours"]
            flat = v["long_summer_rock_hours"] if south_ else v["long_snow_free_hours"]
            tb = v.get("top_bins_summer_rock") if south_ else v["top_bins"]
            share = v.get("poleward_share_summer_rock") if south_ else v["poleward_share"]
            clear = v.get("long_summer_rock_open_hours_clear") if south_ else v.get("long_open_hours_clear")
            rows.append([k, f"{r['lat']:.2f}, {r['lon']:.2f}", r["region"], f"{r['bare']:.2f}", f"{f(hours)} ({f(flat)})", f(clear), f"{v['goals'][goal]:.3f}",
                         bins_text(tb), side_text(share, r["hemisphere"]), known_text(r)])
        return rows, sites, pool


    HEAD = ["#", "Cell centre (lat, lon)", "Region", "Bare", "Long-window hours a year: open (snow-free over a flat horizon)", "Typical clear-sky hours a year", "Score", "When to go: best ten-day bins", "Time of day", "Known or little known"]
    HEAD_SOUTH = HEAD[:4] + ["Long-window hours in the rock season: open (flat horizon)", "Typical clear-sky hours in the rock season"] + HEAD[6:]
    for t in tids:
        A(f"### {tname[t]} (Sun at or below {limit[t]:.2f}°)")
        A("")
        rows, sites, pool = site_rows("north", "lighting", t, 5)
        A("**Lighting goal (low Sun on bare ground), top 5 of the north:**")
        A("")
        L += table(HEAD, rows)
        A("")
        top_score = pool[0]["targets"][t]["goals"]["lighting"] if pool else None
        tied = sum(r["targets"][t]["goals"]["lighting"] == top_score for r in pool)
        full_marks = sum((r["targets"][t]["light"] or 0) >= 1.0 for r in rn)
        num(f"ranked northern cells with full light marks, {t}", full_marks, "cells_scored.json: ranked north records with targets.<t>.light = 1")
        num(f"top lighting site, north, {t}", f"{sites[0]['id']} score {sites[0]['targets'][t]['goals']['lighting']} hours {sites[0]['targets'][t]['long_open_hours']}", "first site of my own ranking from cells_scored.json; same as ranking.txt")
        A(f"{tied} ranked cell(s) hold the top score {top_score:.3f}; {full_marks:,} of the {len(rn):,} ranked cells have full light marks (≥ 200 open hours).")
        A("")
        rows, sites, pool = site_rows("north", "full", t, 5)
        A(f"**Full match (light, terrain, rock, bare), north: {len(pool)} ranked cell(s) score above zero, {len(my_sites('north', 'full', t)[0])} site(s):**")
        A("")
        if rows:
            full_rows = []
            for row, r in zip(rows, sites):
                v = r["targets"][t]
                full_rows.append(row[:6] + [f"{v['goals']['full']:.3f} (light {v['light']:.2f}, terrain {v['terrain']:.2f}, rock {v['rock']:.2f}: {r['rock']['body']})"] + row[7:])
            L += table(HEAD, full_rows)
            num(f"top full-match site, north, {t}", f"{sites[0]['id']} score {sites[0]['targets'][t]['goals']['full']}", "first site of my own ranking from cells_scored.json; same as ranking.txt")
        else:
            A("No ranked cell scores above zero.")
        A("")
    A("Source: `cells_scored.json` → `cells[].targets.<target>.goals.lighting`, `.goals.full`, `.long_open_hours`, `.long_snow_free_hours`, `.top_bins`, "
      "`.poleward_share`, `.long_open_hours_clear`, `.light`, `.terrain`, `.rock`; `cells[].known`, `.known_region`, `.little_known`. The same tables, ten rows each, are in `ranking.txt`; "
      f"all {tables_checked} north and south tables there were rebuilt here from `cells_scored.json` and {tables_checked - mismatch} agree row for row.")
    A("")
    A("What decides the tables, and how firm they are:")
    A("")
    on_rock = sum(r["rock"]["score"] > 0 for r in rn)
    num("ranked northern cells with a rock score above 0", on_rock, "cells_scored.json: ranked north records with rock.score > 0")
    A(f"- The full-match goal needs a listed anorthosite body: {on_rock} of the {len(rn):,} ranked northern cells have a rock score above 0 (`cells[].rock.score`), so those tables are short. "
      "The highest full-match score is "
      + f"{max(my_sites('north', 'full', t)[1][0]['targets'][t]['goals']['full'] for t in tids if my_sites('north', 'full', t)[1]):.2f}"
      + "; the factor scores are in the tables.")
    A("")
    rows = []
    keys = ["full marks at 100 h", "full marks at 400 h", "stretch minimum 1 h", "stretch minimum 3 h", "snow land pixels >= 4", "snow land pixels >= 7", "flat horizon instead of real", "bare screen 0.15", "bare screen 0.35"]
    for t in tids:
        s = val["stability"]["north"][t]["lighting"]
        rows.append([SHORT[t], s["baseline_sites"]] + [s[k] for k in keys])
        num(f"lighting top-10 sites kept with full marks at 100 h / 400 h, north, {t}", f"{s['full marks at 100 h']} / {s['full marks at 400 h']} of {s['baseline_sites']}", f"validation.json stability.north.{t}.lighting")
    L += table(["Target (lighting, north)", "Sites in the top list"] + ["kept: " + k for k in keys], rows)
    A("")
    A("Source: `validation.json` → `stability.north.<target>.lighting`: how many of the top-10 sites still have a site within 50 km when one choice is changed. "
      f"The check draws on every scored cell ({val['meta']['stability_draws_on_records']:,} records); the 1 h and 3 h columns are per-day spells worked out again by `{val['meta']['stretch_variants_from']}`.")
    A("")
    rows = []
    for t in tids:
        r = val["regions"][t]["measured_cells_with_full_flat_light_and_enough_bare"]
        rows.append([SHORT[t], f(r["cells"]), f(r["of_them_with_a_horizon"])])
        num(f"measured cells with bare >= 0.25 and >= 200 flat-horizon long-window hours / of them with a horizon, {t}", f"{r['cells']} / {r['of_them_with_a_horizon']}", f"validation.json regions.{t}.measured_cells_with_full_flat_light_and_enough_bare")
    L += table(["Target", "Measured cells with bare ≥ 0.25 that already have 200 long-window snow-free hours over a flat horizon", "of them with a terrain horizon"], rows)
    A("")
    A("Source: `validation.json` → `regions.<target>.measured_cells_with_full_flat_light_and_enough_bare`. The ranking can only choose among cells that have a horizon; "
      "the cells in the second column but not the third have no horizon, so some of them may be as good as the sites listed.")
    A("")

    # ---- (f)
    A("## (f) The named sites")
    A("")
    A("Each named place is reported on the cell that holds it, whatever the screens say; the " + str(sum(not c["gridded"] for c in cells)) + " cells outside the screens are in no count above. "
      "Hours are long-window hours a year: flat / snow-free / open. Horizons are for the cell's 10 km square, not the site's exact point.")
    A("")
    rows = []
    assert all(s["in_grazing_cells"] for s in val["named_sites"]["sites"])
    for s in val["named_sites"]["sites"]:
        if s["hemisphere"] != "N":
            continue
        c = by_id[s["cell"]]
        hz = s["horizon"] if s["horizon"] and "skipped" not in s["horizon"] else {}
        r = rec_of.get(s["cell"])
        cells_t = []
        for t in tids:
            m = s["targets"][t]
            cells_t.append(f"{f(m['flat']['long']['year'])} / {f(m['snow_free']['long']['year'])} / {f(m['open']['long']['year'])}")
        rows.append([s["name"], s["cell"], f(s["bare"], 2), s["snow"]["status"] + ("" if c["gridded"] else ", outside the screen"),
                     f"{f(hz.get('north_deg'), 1)}° / {f(hz.get('south_deg'), 1)}°"] + cells_t + [f"{s['rock']['score']:.2f}"])
    L += table(["Site (north)", "Cell", "Bare", "Snow odds", "Horizon N / S"] + [SHORT[t] for t in tids] + ["Rock match"], rows)
    A("")
    A("Source: `validation.json` → `named_sites.sites[]`: `.cell`, `.bare`, `.snow.status`, `.gridded`, `.horizon`, `.targets.<target>.<flat|snow_free|open>.long.year`, `.rock.score`.")
    A("")
    q = site_reports["Qaqortorsuaq anorthosite, Greenland"]
    A(f"- Qaqortorsuaq (the simulant mine): its cell has {q['targets']['malapert']['all_day_days']} all-day low-Sun days for Malapert but "
      f"{f(q['targets']['malapert']['usable_days'], 1)} usable days, because the snow odds are 0 on those days; its long-window snow-free hours "
      f"({f(q['targets']['malapert']['snow_free']['long']['year'], 1)} h) are all in the summer half "
      f"(winter half {f(q['targets']['malapert']['snow_free']['long']['winter_half'], 1)} h), and the terrain leaves {f(q['targets']['malapert']['open']['long']['year'], 1)} h "
      "(`named_sites.sites[].targets.malapert.all_day_days`, `.usable_days`, `.snow_free.long`, `.open.long`).")
    num("Qaqortorsuaq cell, Malapert: all-day days / usable days", f"{q['targets']['malapert']['all_day_days']} / {q['targets']['malapert']['usable_days']}", "validation.json named_sites, site Qaqortorsuaq, targets.malapert.all_day_days and usable_days")
    A("")
    hj = val["haughton_july"]
    A("### Haughton crater, Devon Island, in July")
    A("")
    A(f"{hj['note']} Cell {hj['cell']}; horizon {hj['horizon']['north_deg']}° north, {hj['horizon']['south_deg']}° south; "
      f"snow-free odds in the three ten-day bins {', '.join(hj['dates'])}: {', '.join(f'{o:.2f}' for o in hj['snow_free_odds'])}.")
    A("")
    rows = []
    for t in tids:
        h = hj["targets"][t]
        rows.append([SHORT[t], " / ".join(f(x, 1) for x in h["flat_hours"]), f(h["flat_hours_july"], 1), f(h["snow_free_hours_july"], 1), f(h["open_hours_july"], 1),
                     " / ".join(f(h[f"long_{kind}_hours_july"], 1) for kind in ("flat", "snow_free", "open")),
                     " / ".join(f"{x:.2f}" for x in h["median_longest_stretch_h"])])
        num(f"Haughton in July, {t}: flat / snow-free / open hours", f"{h['flat_hours_july']} / {h['snow_free_hours_july']} / {h['open_hours_july']}", f"validation.json haughton_july.targets.{t}.*_hours_july")
    L += table(["Target", "All hours in the band (any spell length), flat horizon, in the three bins", "July, all hours: flat", "snow-free", "open",
                "July, long-window hours only (spells of 2 h or more): flat / snow-free / open",
                "Median longest daily spell in each bin, h (for information; it gates nothing now)"], rows)
    A("")
    A("Source: `validation.json` → `haughton_july.targets.<target>.flat_hours`, `.flat_hours_july`, `.snow_free_hours_july`, `.open_hours_july`, "
      "`.long_flat_hours_july`, `.long_snow_free_hours_july`, `.long_open_hours_july`, `.median_longest_stretch_h`; `haughton_july.snow_free_odds`. "
      "Unlike the other tables of this file, the first four columns count every hour in the band, whatever the length of the spell.")
    A("")
    hy = site_reports["Haughton crater, Devon Island, Canada"]["targets"]
    first_bin = {t: next((d for d, h in zip(hj["dates"], hj["targets"][t]["flat_hours"]) if h > 0), None) for t in tids}
    A(f"- At {site_reports['Haughton crater, Devon Island, Canada']['lat']:.1f} N the July Sun stays above the limits for most of the month. Flat-horizon hours in the band in July, any spell length: "
      + ", ".join(f"{f(hj['targets'][t]['flat_hours_july'], 1)} h ({SHORT[t]}; " + ("none in July" if first_bin[t] is None else f"first in the bin {first_bin[t]}") + ")" for t in tids)
      + ". The 2001 test used 24-hour daylight, which is not the same as Sun inside a lunar band.")
    A("- Over the whole year the Haughton cell has long-window open hours of "
      + ", ".join(f"{f(hy[t]['open']['long']['year'], 1)} h ({SHORT[t]})" for t in tids)
      + "; best bins for Nobile Rim 2: " + bins_text(hy["nobile-rim-2"]["top_bins"]) + " (`named_sites.sites[].targets.<target>.open.long.year`, `.top_bins`).")
    A("")

    # ---- (g)
    A("## (g) Antarctica: snow not measured")
    A("")
    A(f"No open product measures winter snow on Antarctic rock, so the {len(south):,} southern cells have no snow-free hours (`snow.status` = unmeasured, `snow_free_hours` null). "
      "Their light counts the rock season only, 27 November to 1 March, when the rock maps were made from snow-free scenes; they are ranked apart from the north.")
    A("")
    rows = []
    for t in tids:
        row = [SHORT[t]]
        for level in (50, 100, 200):
            got = [c for c in south if (c["targets"][t]["long_summer_rock_hours"] or 0) >= level]
            row.append(f"{len(got):,} cells, {sum(c['bare_km2'] for c in got):,.0f} km²")
            num(f"southern cells with >= {level} rock-season long-window flat hours, {t}", len(got), "count over gridded southern cells of grazing_cells.json, long_summer_rock_hours")
        row.append(" / ".join(str(sum((c["targets"][t]["long_summer_rock_open_hours"] or 0) >= level for c in s_h)) for level in (50, 100, 200)))
        rows.append(row)
    L += table(["Target", "Flat horizon ≥ 50 h", "≥ 100 h", "≥ 200 h", f"with the real horizon, over the {len(s_h):,} southern cells that have one ({len(south) - len(s_h)} have none): cells ≥ 50 / 100 / 200 h"], rows)
    A("")
    A("Source: `grazing_cells.json` → southern gridded cells, `targets.<target>.long_summer_rock_hours`, `long_summer_rock_open_hours`, `bare_km2`.")
    A("")
    sreg = Counter(c["region"] for c in south)
    num("bare ground of the southern cells, km2", round(sum(c["bare_km2"] for c in south), 1), "sum of bare_km2 over gridded southern cells")
    num("southern cells whose two rock layers disagree", sum(bool(c["layers_disagree"]) for c in south), "count of layers_disagree true over gridded southern cells")
    A(f"- The {len(south):,} cells hold {sum(c['bare_km2'] for c in south):,.0f} km² of mapped rock; regions: " + ", ".join(f"{k} {v}" for k, v in sreg.most_common()) + " (`region`, `bare_km2`).")
    A(f"- In {sum(bool(c['layers_disagree']) for c in south)} of them the two rock-outcrop layers differ by more than a factor of 2 (`layers_disagree`).")
    A(f"- {len(rs)} southern cells are ranked (a horizon and bare ≥ 0.25). See (d) for what terrain takes away in the south.")
    A("")
    for t in tids:
        rows, sites, pool = site_rows("south", "lighting", t, 3)
        A(f"**{tname[t]}: lighting goal, top 3 of the south (rock season only):**")
        A("")
        L += table(HEAD_SOUTH, rows)
        A("")
        if sites:
            num(f"top lighting site, south, {t}", f"{sites[0]['id']} score {sites[0]['targets'][t]['goals']['lighting']} hours {sites[0]['targets'][t]['long_summer_rock_open_hours']}", "first site of my own ranking of southern ranked cells in cells_scored.json; same as ranking.txt")
    A("Source: `cells_scored.json` → southern records: `targets.<target>.goals.lighting`, `.long_summer_rock_open_hours`, `.long_summer_rock_hours`, `.long_summer_rock_open_hours_clear`, `.top_bins_summer_rock`, `.poleward_share_summer_rock`.")
    A("")
    A("The named southern sites, with what is known about their winter snow:")
    A("")
    ev = {s["name"]: s for s in south_sites}
    rows = []
    for s in val["named_sites"]["sites"]:
        if s["hemisphere"] != "S":
            continue
        c = by_id[s["cell"]]
        hz = s["horizon"] if s["horizon"] and "skipped" not in s["horizon"] else {}
        rows.append([s["name"], s["cell"], f"{f(s['bare'], 2)} / {f(s['land_share'], 2)}", "yes" if c["gridded"] else "no", s["winter_snow_evidence"],
                     f"{f(hz.get('north_deg'), 1)}° / {f(hz.get('south_deg'), 1)}°"]
                    + [f"{f(s['targets'][t]['long_summer_rock_hours'])} / {f(s['targets'][t]['long_summer_rock_open_hours'])}" for t in ("malapert", "nobile-rim-2")])
    L += table(["Site (south)", "Cell", "Bare / land share", "In the screen", "Winter-snow evidence", "Horizon N / S", "Malapert: rock-season long-window hours flat / open", "Nobile Rim 2: the same"], rows)
    A("")
    A("Source: `validation.json` → `named_sites.sites[]` (`.winter_snow_evidence` is copied from `data/reference/antarctic_sites.json`; `.targets.<target>.long_summer_rock_hours`, `.long_summer_rock_open_hours`).")
    A("")
    evc = Counter(s["winter_snow_evidence"] for s in south_sites)
    A("- Evidence labels of the " + str(len(south_sites)) + " sites: " + ", ".join(f"\"{k}\" {v}" for k, v in evc.most_common()) + ". \"Measured mostly bare\": "
      + ", ".join(s["name"] for s in south_sites if s["winter_snow_evidence"] == "measured mostly bare") + ".")
    A("")

    # ---- (h)
    A("## (h) The old measure against the new")
    A("")
    A("The first method counted days on which the Sun stays under the limit even at noon, times the snow-free odds (\"usable days\"). "
      "The new files keep that column with the corrected Sun and snow (`usable_days`).")
    A("")
    oan = val["old_against_new"]["targets"]
    rows = []
    for t in old_tids:
        old_ids = [cid for cid, per in v1.items() if (per[t]["usable_days"] or 0) >= 10]
        now = Counter()
        for cid in old_ids:
            c = by_id.get(cid)
            if c is None:
                now["not in the new file"] += 1
            elif c["snow"]["status"] != "measured":
                now[c["snow"]["status"]] += 1
            elif (c["targets"][t]["usable_days"] or 0) >= 10:
                now["still ≥ 10"] += 1
            else:
                now["measured, now under 10"] += 1
        b100 = bp["targets"][t]["long_snow_free_hours"]["year"]["100"]["cells"]
        rows.append([SHORT[t], oan[t]["old"], oan[t]["new_measured"], oan[t]["new_doubtful"],
                     ", ".join(f"{k} {v}" for k, v in oan[t]["new_measured_regions"].items()) or "none",
                     "; ".join(f"{k}: {v}" for k, v in now.most_common()) or "none", f(b100)])
        num(f"cells with >= 10 usable all-day low-Sun days, old file / new measured / new doubtful, {t}", f"{oan[t]['old']} / {oan[t]['new_measured']} / {oan[t]['new_doubtful']}",
            f"validation.json old_against_new.targets.{t}")
    L += table(["Target", "Old file: cells with ≥ 10 usable days", "New: measured cells with ≥ 10", "New: doubtful cells with ≥ 10 (not counted)", "Regions of the new measured cells",
                "Where the old cells are now", "For scale: measured cells with ≥ 100 long-window snow-free hours"], rows)
    A("")
    A("Source: `validation.json` → `old_against_new.targets.<target>.old`, `.new_measured`, `.new_doubtful`, `.new_measured_regions`; "
      "\"where the old cells are now\" was worked out here from `light_cells_v1.json` (`<cell>.<target>.usable_days`) and `grazing_cells.json` (`snow.status`, `usable_days`); "
      "last column `big_picture_north.targets.<target>.long_snow_free_hours.year.100.cells`.")
    A("")
    rows = []
    for t in tids:
        sites = my_sites("north", "lighting", t)[0]
        days = [s["targets"][t]["usable_days"] for s in sites]
        rows.append([SHORT[t], len(sites), sum(d is not None and d >= 10 for d in days), sum(d == 0 for d in days), f(max(d for d in days if d is not None), 1)])
        num(f"top-10 lighting sites with >= 10 usable days under the old measure, {t}", sum(d is not None and d >= 10 for d in days), "usable_days of the ten top lighting sites, cells_scored.json")
    L += table(["Target", "Top lighting sites (new measure)", "of them with ≥ 10 usable days (old measure)", "of them with 0 usable days", "Most usable days among them"], rows)
    A("")
    A("Source: `cells_scored.json` → `targets.<target>.usable_days` of the top-10 lighting sites.")
    A("")
    A("- The old measure counts winter noon light only. The new one adds the dawn, dusk and midnight-Sun hours; of the long-window snow-free hours × bare km² "
      + ", ".join(f"{1 - cal_share(t)[0]:.1%}" for t in tids) + " fall in the summer half for the four targets (see (b) and (c)).")
    old_top = (D / "ranking_v1.txt").read_text().splitlines()
    first_row = next(l for l in old_top if re.match(r"\s+\d\.\d\d\s", l))
    bj = [(n_, by_id[site_reports[n_]["cell"]]["snow"]) for n_ in ("Bear Island, Norway", "Jan Mayen, Norway")]
    A("- The first row of the old ranking (`ranking_v1.txt`) was: `" + " ".join(first_row.split()[:6]) + " ...`. In the new files "
      + " and ".join(f"the cell of {n_.split(',')[0]} is \"{s_['status']}\" ({s_['stuck_winters']} stuck winters)" for n_, s_ in bj) + ", so neither is ranked; see (i).")
    A("")

    # ---- (i)
    A("## (i) What is doubtful or not covered")
    A("")
    A("### Cells without a terrain horizon")
    A("")
    wreg = Counter(c["region"] for c in measured if not has_h(c))
    A(f"- {n_h:,} of the {len(cells):,} cell records have a terrain horizon. {n_tile:,} are stored as \"tile not fetched\": their elevation tiles were not on disk when the horizons were computed. "
      f"{n_anti} are refused because their 30 km window crosses the 180° meridian (`grazing_cells.json` → `horizon.skipped`).")
    A(f"- Among the {len(measured):,} measured northern cells {lacking['cells']:,} have no horizon; among the {len(rankable):,} of them with bare ≥ 0.25, {len(rankable_waiting):,}. "
      f"Among the {len(south):,} southern cells {len(south) - len(s_h)} have none. Regions of the measured northern cells without a horizon: "
      + ", ".join(f"{k} {v:,}" for k, v in wreg.most_common(7)) + (f"; other regions {sum(v for _, v in wreg.most_common()[7:]):,}" if len(wreg) > 7 else "") + ".")
    A("- For those cells the open hours, the clear-sky hours and every score that uses light are `n/a`; they are in no ranking; and every \"with the real horizon\" count in (b), (c), (g) and (j) "
      "is a count over the cells that have a horizon, so it is a lower bound. The flat-horizon counts in (b) and (c) cover every measured cell.")
    A("")
    A("### Doubtful and no-data cells")
    A("")
    dreg, nreg = Counter(c["region"] for c in doubtful), Counter(c["region"] for c in nodata)
    A(f"- {len(doubtful)} gridded northern cells are **doubtful**: at least one winter in which a snow pixel read \"snow-free\" on every map at or north of 67.4 N, or three such winters anywhere "
      f"(regions: {', '.join(f'{k} {v}' for k, v in dreg.most_common())}). {len(nodata)} have **no snow data**: no land pixel of the 4 km snow grid within the 5 × 5 block "
      f"(regions: {', '.join(f'{k} {v}' for k, v in nreg.most_common())}). Neither group is ranked or counted; all {len(doubtful) + len(nodata)} are listed with both versions of their hours in `ranking.txt` "
      "under \"DOUBTFUL SNOW OR NO SNOW DATA\" (`grazing_cells.json` → `snow.status`, `snow.stuck_winters`, `region`).")
    A("- For a doubtful cell the main figure uses the stale-flag rule and is the lower one; the hours as the maps read are the upper one. The rule leaves out a pixel's whole spring and summer "
      "after a stuck winter if the pixel never reads snow before 30 September, so it lowers summer odds too:")
    A("")
    rows = []
    for name in ("Bear Island, Norway", "Jan Mayen, Norway", "Lofoten anorthosite (Nusfjord), Norway"):
        s = site_reports[name]
        c = by_id[s["cell"]]
        rows.append([name, s["cell"], c["snow"]["status"], c["snow"]["stuck_winters"], f"{c['snow']['land_pixels']} of {c['snow'].get('block_pixels', 9)}"]
                    + [f"{f(c['targets'][t]['long_snow_free_hours_with_rule'], 1)} / {f(c['targets'][t]['long_snow_free_hours_as_mapped'], 1)} / {f(c['targets'][t]['long_open_hours'], 1)}" for t in ("malapert", "nobile-rim-2")])
        num(f"{name}: Malapert long-window snow-free hours with the rule / as mapped / open", f"{c['targets']['malapert']['long_snow_free_hours_with_rule']} / {c['targets']['malapert']['long_snow_free_hours_as_mapped']} / {c['targets']['malapert']['long_open_hours']}",
            "grazing_cells.json, the site's cell, targets.malapert.long_snow_free_hours_with_rule, long_snow_free_hours_as_mapped, long_open_hours")
    L += table(["Site", "Cell", "Status", "Stuck winters", "Snow land pixels (of the block used)", "Malapert: with the rule / as mapped / open (with the rule and terrain)", "Nobile Rim 2: the same"], rows)
    A("")
    A("Source: `grazing_cells.json` → `snow.status`, `snow.stuck_winters`, `snow.land_pixels`, `snow.block_pixels`, `targets.<target>.long_snow_free_hours_with_rule`, `long_snow_free_hours_as_mapped`, `long_open_hours`.")
    A("")
    A("### Measured cells with a stuck winter: the maps as they read")
    A("")
    stuck = [c for c in measured if (c["snow"]["stuck_winters"] or 0) >= 1]
    num("measured cells with at least one stuck winter", len(stuck), "measured gridded cells of grazing_cells.json with snow.stuck_winters >= 1")
    ssc = stuck_station_check(stations["stations"])
    num("trusted stations with a stuck pixel nearby: all / maps as they read closer / rule closer / the same", f"{ssc['stations']} / {ssc['as_mapped_closer']} / {ssc['rule_closer']} / {ssc['same']}",
        "make_results.stuck_station_check over snow_validation_many.json stations with stuck_winters >= 1: mean absolute difference from station_share of satellite_as_mapped and of satellite")
    A(f"- {len(stuck)} measured cells have one or two stuck winters (south of 67.4 N, so not doubtful). Since version 3 every measured cell uses the maps as they read, "
      f"because at {ssc['as_mapped_closer']} of the {ssc['stations']} trusted stations with a stuck pixel nearby the odds as the maps read are closer to the station record than the odds with the stale-flag rule "
      f"(at {ssc['rule_closer']} the rule is closer, at {ssc['same']} they are the same; mean absolute difference over the ten-day bins compared, worked out here from "
      f"`snow_validation_many.json` → `stations[].satellite_as_mapped`, `.satellite`, `.station_share`; those stations lie at {ssc['lat_min']:.1f} to {ssc['lat_max']:.1f} N). "
      "For these cells the figure the rule would give is kept beside the main one:")
    A("")
    rows = []
    risen = {}
    for t in tids:
        pairs = [(c, c["targets"][t]["long_snow_free_hours"], c["targets"][t]["long_snow_free_hours_with_rule"]) for c in measured]
        pairs = [(c, a, b) for c, a, b in pairs if a is not None and b is not None]
        differ = [(c, a, b) for c, a, b in pairs if a != b]
        from_zero = [(c, a, b) for c, a, b in differ if b == 0.0 and a > 0]
        winter_only = sum(c["targets"][t]["long_snow_free_hours_summer"] == 0.0 for c, a, b in from_zero)
        if differ:
            top = max(differ, key=lambda x: x[1] - x[2])
            biggest = f"{top[1] - top[2]:+.1f} h ({top[2]:.1f} to {top[1]:.1f}) at {top[0]['lat']:.2f}, {top[0]['lon']:.2f}, {top[0]['region']}"
        else:
            biggest = "none"
        risen.update({c["id"]: c for c, _, _ in from_zero})
        rows.append([SHORT[t], len(differ), biggest, len(from_zero), f(max((a for _, a, _ in from_zero), default=None), 1), winter_only])
        num(f"measured cells whose long-window snow-free hours differ between the maps as they read and the stale-flag rule / of them 0.0 h with the rule, {t}",
            f"{len(differ)} / {len(from_zero)}", "measured gridded cells of grazing_cells.json: long_snow_free_hours against long_snow_free_hours_with_rule")
    L += table(["Target", "Measured cells whose figure differs from the rule's", "Largest rise", "Cells with 0.0 h under the rule and more as mapped", "their largest figure, h", "of them with all those hours in the winter half"], rows)
    A("")
    A("Source: `grazing_cells.json` → measured gridded cells, `targets.<target>.long_snow_free_hours` (as mapped) against `long_snow_free_hours_with_rule`, `long_snow_free_hours_summer`.")
    A("")
    risen_where = Counter(c["region"] for c in risen.values())
    A((f"- The {len(risen)} cells that rise from 0.0 h for at least one target do so on maps that read \"snow-free\" through a stuck winter (the last column says for how many of them all those hours are in the winter half), "
       f"at {min(c['lat'] for c in risen.values()):.2f} to {max(c['lat'] for c in risen.values()):.2f} N (cell centres; " + ", ".join(f"{k} {v}" for k, v in risen_where.most_common()) + "). "
       if risen else "- No measured cell rises from 0.0 h. ")
      + "Whether a midwinter snow-free reading there is believable was not checked against any station; treat those winter hours as an upper figure. "
      "They move no count in (b) by more than one cell (the build's own before-and-after comparison; not recomputed here).")
    part = [c["id"] for c in measured if c["targets"][tids[0]]["long_snow_free_hours"] is None]
    A(f"- {len(part)} measured cells ({', '.join(part)}) have snow odds in only some ten-day bins; their snow-free hours are `null` and they appear as \"unknown\" in every count.")
    num("measured cells with unknown snow-free hours", len(part), "measured gridded cells of grazing_cells.json whose long_snow_free_hours is null")
    A("")
    A("### Snow odds: what they rest on")
    A("")
    thin = sum((c["snow"]["land_pixels"] or 0) < 7 for c in measured)
    five = sum(c["snow"]["source"] == "5x5" for c in measured)
    thin_ranked = sum((r["snow"]["land_pixels"] or 0) < 7 for r in rn)
    num("measured cells with under 7 snow pixels on land", thin, "count over measured gridded cells, snow.land_pixels < 7")
    num("measured cells whose odds come from the 5 x 5 block", five, "count over measured gridded cells, snow.source = 5x5")
    A(f"- **4 km snow pixels.** A cell's odds are the mean of the land pixels in a 3 × 3 block (12 km), so a coastal cell can rest on few pixels: {thin:,} of the {len(measured):,} measured cells "
      f"have fewer than 7 pixels on land, and {five} take their odds from the wider 5 × 5 block because the 3 × 3 block has none (`snow.land_pixels` now counts the block that was used, `snow.block_pixels` = 9 or 25). "
      f"Among the {len(rn):,} ranked northern cells {thin_ranked:,} have fewer than 7 (`snow.land_pixels`, `snow.source`). The stability table in (e) shows what a pixel screen does to the top lists.")
    p = stations["periods"]
    wb = p["winter_half"]["with_stale_flag_rule"]["mean_bias"]
    sb = p["summer_half"]["with_stale_flag_rule"]["mean_bias"]
    mb = p["may_to_august_north_of_66"]["with_stale_flag_rule"]
    wm, sm, mm = (p[k]["as_mapped"]["mean_bias"] for k in ("winter_half", "summer_half", "may_to_august_north_of_66"))
    num("satellite minus station snow-free share with the odds as mapped: winter half / summer half / May-August north of 66N", f"{wm:.3f} / {sm:.3f} / {mm:.3f}",
        "snow_validation_many.json periods.<period>.as_mapped.mean_bias (read, not recomputed)")
    n66 = stations["north_of_66"]
    num("stations kept for the snow check", stations["overall"]["stations"], "snow_validation_many.json overall.stations (read, not recomputed)")
    num("satellite minus station snow-free share: winter half / summer half / May-August north of 66N", f"{wb:.3f} / {sb:.3f} / {mb['mean_bias']:.3f}", "snow_validation_many.json periods.<period>.with_stale_flag_rule.mean_bias (read, not recomputed; computed with the stale-flag rule)")
    A(f"- **Checked against weather stations (read from the station file of version 2, not recomputed).** Against {stations['overall']['stations']} trusted stations the satellite odds of snow-free ground as the maps read, "
      "which are the odds every measured cell uses, are lower than the station record on average: "
      f"{wm:+.3f} in the winter half, {sm:+.3f} in the summer half, {mm:+.3f} for May to August at the {mb['stations']} stations at or north of 66 N that have such a bin "
      f"({mb['n']} station-bins); with the stale-flag rule the same three figures are {wb:+.3f}, {sb:+.3f} and {mb['mean_bias']:+.3f}. "
      "So, on average over these stations, the snow-free odds err on the low side where they can be tested; single stations differ either way. "
      f"North of 66 N there are {n66['kept']} kept stations ({n66['kept_with_a_may_to_august_bin']} with a May-to-August bin) and none in {', '.join(r for r in n66['regions_without_a_kept_station'] if r != 'Other')}; Russia has {n66['by_region']['Russia']['kept']}. "
      "(`snow_validation_many.json` → `overall.stations`, `periods.<period>.as_mapped.mean_bias`, `.with_stale_flag_rule.mean_bias`, `north_of_66`. That file's own cell counts under calibrated odds were made with the version 2 long-window rule and the stale-flag rule for every cell, so they are not quoted here.)")
    A("- **Stale snow flags in summer on small Arctic islands.** The reverse fault is on record too: the build contract (decision 11) notes that Bear Island reads \"snow\" through the whole summer of 2024. "
      "No rule corrects it and it was not measured again here, so summer hours on such islands are understated by an unknown amount.")
    A("")
    A("### Sun and terrain geometry")
    A("")
    refr = float(sun.refraction_deg(0.0))
    num("standard refraction at a true elevation of 0, deg", f"{refr:.2f}", "sun.refraction_deg(0.0)")
    A(f"- **Standard refraction.** The Sun's apparent height uses refraction at standard pressure and temperature ({refr:.2f}° at a true elevation of 0°, `sun.refraction_deg`). "
      f"That value alone is {refr / limit['connecting-ridge']:.0%} of the {limit['connecting-ridge']:.2f}° band and {refr / limit['nobile-rim-2']:.0%} of the {limit['nobile-rim-2']:.2f}° band; "
      "real polar air can bend light more or less than the standard value, and nothing here measures by how much.")
    A(f"- **One ray per ten-degree sector.** The terrain horizon is taken along one ray at the centre of each of 36 azimuth sectors, on a 60 m grid, out to 25 km. "
      f"At 25 km a sector is {2 * math.pi * 25 / 36:.1f} km wide, so a peak or gap narrower than that can fall between rays.")
    A("- **The two-hour cut is sharp.** Version 3 follows each spell day by day, so a cell's total no longer hangs on whether a whole ten-day bin's median reaches 2.00 h. "
      "The minimum itself still matters, most where the Sun takes close to two hours to cross the band at sunrise and sunset. Flat-horizon hours a year inside spells of at least 1, 2 and 3 hours:")
    A("")
    rows = []
    for lat in (62.0, 66.0, 70.0, 74.5, 78.0):
        row = [f"{lat:g} N"]
        for t in ("malapert", "nobile-rim-2"):
            h = prof[lat][t]["long_flat_hours"]
            row.append(f"{f(h['1'])} / {f(h['2'])} / {f(h['3'])}")
        rows.append(row)
        num(f"Nobile Rim 2 flat-horizon hours inside spells of at least 1 / 2 / 3 h at {lat:g} N", " / ".join(str(prof[lat]["nobile-rim-2"]["long_flat_hours"][k]) for k in ("1", "2", "3")),
            f"latitude_profile.json profile row lat {lat}, targets.nobile-rim-2.long_flat_hours")
    L += table(["Latitude", "Malapert: 1 h / 2 h / 3 h minimum", "Nobile Rim 2: 1 h / 2 h / 3 h minimum"], rows)
    A("")
    A("Source: `latitude_profile.json` → `profile[].targets.<target>.long_flat_hours[\"1\"|\"2\"|\"3\"]`.")
    A("")
    A("- The reviewer of the per-day rule measured, by an independent route, that moving the minimum by one minute either way (1 h 59 min to 2 h 01 min) changes a cell's yearly long-window flat hours "
      "by 6 to 8 h at the median latitude and by up to 84 h (7%) near 74 to 78 degrees (reported by that review; not recomputed here). "
      "So these hours should not be read to the last hour; the 1 h and 3 h columns of the stability table in (e) bracket the choice.")
    checks_doc = load("checks.json") if (D / "checks.json").exists() else None
    now_sha = {"grazing_cells.json": file_sha256(D / "grazing_cells.json"), "grazing_bins.npz": file_sha256(D / "grazing_bins.npz"),
               "sun.py": file_sha256(Path(sun.__file__))}
    check_text, check_numbers = checks_lines(checks_doc, now_sha)
    for label, value, how in check_numbers:
        num(label, value, how)
    for line in check_text:
        A(line)
    A("- " + leap_paragraph(meta))
    A("- **The 59-degree band edge.** See (a): with the 2 h rule "
      + ("; ".join(f"{SHORT[t]}'s belt begins at {th[t]['N']['lowest_lat_with_long_window']['2']:.2f}°, "
                   f"{59 - th[t]['N']['lowest_lat_with_long_window']['2']:.2f}° outside the band" for t in outside) or "no belt begins outside the band")
      + f"; the other {len(tids) - len(outside)} targets start inside it.")
    known_list = json.loads((REFERENCE / "known_analogs.json").read_text())
    A(f"- **Known or little known.** A cell counts as known when it lies within 50 km of one of the {len(known_list)} sites of `data/reference/known_analogs.json`, in Iceland or Svalbard, "
      "inside hand-drawn boxes for Devon Island and the McMurdo Dry Valleys, within 50 km of a southern site with analog use, or on an anorthosite body the rock list marks as already used. "
      f"{sum(r['little_known'] for r in rn):,} of the {len(rn):,} ranked northern cells and {sum(r['little_known'] for r in rs)} of the {len(rs)} ranked southern cells are little known (`cells_scored.json` → `little_known`). "
      "The boxes were not checked against a coastline file.")
    A("- **Light score.** It stops at 200 hours, so cells with 200 and 400 open hours score the same; the tables in (e) order such ties by hours.")
    A("")
    A("### What this match is and is not")
    A("")
    shadow = {t: 1 / math.tan(math.radians(limit[t])) for t in tids}
    for t in tids:
        num(f"shadow length of a 1 m object at the limit, {t}", f"{shadow[t]:.1f} m", "1 / tan(limit_deg)")
    A("- These sites match the **height of the Sun and the length of shadows**, for hours at a time. At the four limits a 1 m rock throws a shadow of at least "
      + ", ".join(f"{shadow[t]:.1f} m ({SHORT[t]})" for t in tids) + " (1 ÷ tan of the limit).")
    moon_rate = 360.0 / (MOON_SYNODIC_DAYS * 24.0)
    rates = {lat: EARTH_DEG_PER_HOUR * math.sin(math.radians(lat)) for lat in (60, 70, 80)}
    for lat, rate in rates.items():
        num(f"how fast the Sun's compass direction moves near the horizon at {lat} degrees latitude, Earth against Moon", f"{rate:.2f} deg/h against {moon_rate:.3f} deg/h: {rate / moon_rate:.1f} times",
            f"15 x sin({lat} deg) / (360 / ({MOON_SYNODIC_DAYS} x 24))")
    A(f"- They do not match **how fast the Sun's compass direction moves**. Near the horizon it moves about 15° × sin(latitude) per hour on Earth: "
      + ", ".join(f"{rate:.1f}° per hour at {lat}°" for lat, rate in rates.items())
      + f". At the Moon's south pole the Sun goes once round the horizon in a synodic month, {moon_rate:.3f}° per hour (about 0.51). The ratio is "
      + ", ".join(f"{rate / moon_rate:.1f} at {lat}°" for lat, rate in rates.items())
      + f". In a two-hour low-Sun spell on Earth the shadows swing through {2 * rates[60]:.0f}° to {2 * rates[80]:.0f}°; on the Moon through {2 * moon_rate:.1f}°. "
      "A test that needs the lunar pace of the shadows cannot get it at any of these sites (15 × sin φ and 360 ÷ 29.53 days; computed here, not read from a file).")
    A("- They do not match lunar **contrast**. Earth's air scatters light into shadows and dims and reddens a Sun this low; on the Moon shadows are black and the Sun is at full strength. "
      "No number in this file measures that difference.")
    A("- They do not promise a **visible Sun**. Section (j) gives typical clear-sky hours from monthly mean cloud; that is a coarse guide, not a forecast.")
    A("- What no site on Earth matches at all: vacuum, lunar dust, one-sixth gravity, the Moon's temperature swings, and its radiation.")
    A("")

    # ---- (j)
    A("## (j) Cloud: typical clear-sky hours")
    A("")
    cm = cloud_file["meta"]
    cloud_cells = cloud_file["cells"]
    A(f"**What the column is.** {cm.get('what_it_is', 'Monthly mean share of the sky covered by cloud.')} Source: {cm['source']}; parameter `{cm['parameter']}`; period {cm['period']}. "
      "A cell's typical clear-sky hours are its long-window open hours in each ten-day bin times (1 − cloud percent ÷ 100) of the bin's month, summed "
      "(`cells_scored.json` → `cloud.pct_by_month`, `targets.<target>.long_open_hours_clear`, `long_open_hours_clear_winter`, `long_open_hours_clear_summer`; southern cells `long_summer_rock_open_hours_clear`).")
    A("")
    A(f"**What it is not.** {cm.get('what_it_is_not', 'Not the chance that a low Sun is visible.')} "
      f"The grid is coarse ({cm.get('resolution_note', 'about 100 km')}), so coast, sea and inland share one value. "
      "Winter values in the polar night may be too low, because satellites see cloud poorly over snow in the dark (a known weakness, not tested here); winter clear-sky hours are the least sure. "
      "No station cloud record was compared.")
    A("")
    with_cloud = sum(r["cloud"]["pct_by_month"] is not None for r in recs)
    num("scored records with a cloud figure", f"{with_cloud} of {len(recs)}", "cells_scored.json records whose cloud.pct_by_month is not null")
    A(f"{with_cloud:,} of the {len(recs):,} scored records have a cloud figure (`cells_scored.json` → `cloud.pct_by_month`).")
    A("")
    A("### Median clear share of the sky by month, where the summer hours are")
    A("")
    rows = []
    for t in tids:
        group = [c for c in measured if (c["targets"][t]["long_open_hours_summer"] or 0) >= 100 and (cloud_cells.get(c["id"]) or {}).get("cloud_pct")]
        if not group:
            rows.append([SHORT[t], 0] + ["n/a"] * 12)
            continue
        clear = np.array([[1.0 - v / 100.0 if v is not None else np.nan for v in cloud_cells[c["id"]]["cloud_pct"]] for c in group], dtype=float)
        med = np.nanmedian(clear, axis=0)
        rows.append([SHORT[t], f(len(group))] + [f"{m:.2f}" for m in med])
        num(f"median clear share of the sky in July / August over measured northern cells with >= 100 summer-half long-window open hours, {t}",
            f"{med[6]:.3f} / {med[7]:.3f} (n {len(group)})", "median over those cells of 1 - cloud_cells.json cloud_pct[month] / 100")
    L += table(["Target", "Measured northern cells with ≥ 100 summer-half open hours"] + list(MONTHS), rows)
    A("")
    A("Source: `cloud_cells.json` → `cells.<id>.cloud_pct` (clear share = 1 − percent ÷ 100) for the measured northern cells whose `grazing_cells.json` → `targets.<target>.long_open_hours_summer` is at least 100; the median over those cells, month by month.")
    A("")
    A("### The big-picture counts with and without the clear-sky factor")
    A("")
    A(f"Measured northern cells with a horizon ({bp['cells_with_a_horizon']:,}; {lacking['cells']:,} measured cells have none and are not counted): cells reaching 50 / 100 / 200 long-window hours.")
    A("")
    rows = []
    for t in tids:
        for season, label in (("winter_half", "winter half"), ("summer_half", "summer half"), ("year", "year")):
            o = bp["targets"][t]["long_open_hours_among_cells_with_a_horizon"][season]
            c = bp["targets"][t]["long_open_hours_clear_among_cells_with_a_horizon"][season]
            rows.append([f"{SHORT[t]}, {label}", " / ".join(f(o[k]["cells"]) for k in ("50", "100", "200")), " / ".join(f(c[k]["cells"]) for k in ("50", "100", "200")),
                         f"{o['unknown_cells']} / {c['unknown_cells']}"])
            if season != "year":
                num(f"measured cells with a horizon reaching 50 / 100 / 200 long-window hours, {label}, open and typical clear-sky, {t}",
                    " / ".join(str(o[k]["cells"]) for k in ("50", "100", "200")) + " open; " + " / ".join(str(c[k]["cells"]) for k in ("50", "100", "200")) + " clear-sky",
                    f"validation.json big_picture_north.targets.{t}.long_open_hours_among_cells_with_a_horizon.{season} and .long_open_hours_clear_among_cells_with_a_horizon.{season}")
    L += table(["Target and period", "Open hours: cells ≥ 50 / 100 / 200 h", "Typical clear-sky hours: cells ≥ 50 / 100 / 200 h", "Cells with unknown hours: open / clear-sky"], rows)
    A("")
    A("Source: `validation.json` → `big_picture_north.targets.<target>.long_open_hours_among_cells_with_a_horizon.<period>.<50|100|200>.cells` and "
      "`.long_open_hours_clear_among_cells_with_a_horizon.<period>`; the clear-sky figures per cell are `cells_scored.json` → `targets.<target>.long_open_hours_clear` and its `_winter` and `_summer` splits.")
    A("")
    rows = []
    for t in tids:
        co, cc = bp["targets"][t]["calendar_open_hours_times_bare_km2"], bp["targets"][t]["calendar_clear_hours_times_bare_km2"]
        summer_bins = [b for b in range(36) if b not in WINTER]
        wo, wc = sum(co[b] for b in WINTER), sum(cc[b] for b in WINTER)
        so, sc = sum(co[b] for b in summer_bins), sum(cc[b] for b in summer_bins)
        rows.append([SHORT[t], f"{sum(cc) / sum(co):.0%}" if sum(co) else "n/a", f"{wc / wo:.0%}" if wo else "n/a", f"{sc / so:.0%}" if so else "n/a",
                     bp["targets"][t]["calendar_clear_unknown_cell_bins"]])
        if sum(co):
            num(f"share of long-window open hours x bare km2 left by the clear-sky factor: year / winter half / summer half, {t}",
                f"{sum(cc) / sum(co):.3f} / " + (f"{wc / wo:.3f}" if wo else "n/a") + " / " + (f"{sc / so:.3f}" if so else "n/a"),
                f"validation.json big_picture_north.targets.{t}.calendar_clear_hours_times_bare_km2 over .calendar_open_hours_times_bare_km2")
    L += table(["Target", "Share of open hours × bare km² left by the clear-sky factor: year", "winter half", "summer half", "Cell-bins left out as unknown (open hours unknown, or hours without a cloud figure)"], rows)
    A("")
    A("Source: `validation.json` → `big_picture_north.targets.<target>.calendar_clear_hours_times_bare_km2` ÷ `.calendar_open_hours_times_bare_km2` (sums over the measured cells with a horizon).")
    A("")
    A("### The top lighting sites with their typical clear-sky hours")
    A("")
    A("The ranking does not use cloud. These are the top five lighting sites of (e) with the clear-sky column beside their hours, and then, for information, the three ranked sites with the most clear-sky hours (one per 50 km).")
    A("")
    for t in tids:
        sites = my_sites("north", "lighting", t, 5)[0]
        rows = []
        for k, r in enumerate(sites, start=1):
            v = r["targets"][t]
            ratio = v["long_open_hours_clear"] / v["long_open_hours"] if v["long_open_hours_clear"] is not None and v["long_open_hours"] else None
            rows.append([f"lighting #{k}", f"{r['lat']:.2f}, {r['lon']:.2f}", r["region"], f"{r['bare']:.2f}", f(v["long_open_hours"]), f(v["long_open_hours_clear"]),
                         "n/a" if ratio is None else f"{ratio:.0%}", f"{v['goals']['lighting']:.3f}"])
        if sites:
            v0 = sites[0]["targets"][t]
            num(f"top lighting site, north, {t}: long-window open hours / typical clear-sky hours", f"{v0['long_open_hours']} / {v0['long_open_hours_clear']} at {sites[0]['id']}",
                "cells_scored.json, first site of the lighting ranking: targets.<t>.long_open_hours and long_open_hours_clear")
        pool = sorted((r for r in rn if r["targets"][t]["long_open_hours_clear"] is not None and r["targets"][t]["long_open_hours_clear"] > 0),
                      key=lambda r: -r["targets"][t]["long_open_hours_clear"])
        clearest = []
        for r in pool:
            if all(hav(r, s) >= 50.0 for s in clearest):
                clearest.append(r)
            if len(clearest) == 3:
                break
        for k, r in enumerate(clearest, start=1):
            v = r["targets"][t]
            rows.append([f"most clear-sky hours #{k}", f"{r['lat']:.2f}, {r['lon']:.2f}", r["region"], f"{r['bare']:.2f}", f(v["long_open_hours"]), f(v["long_open_hours_clear"]),
                         f"{v['long_open_hours_clear'] / v['long_open_hours']:.0%}" if v["long_open_hours"] else "n/a", f"{v['goals']['lighting']:.3f}"])
        if clearest:
            vc = clearest[0]["targets"][t]
            num(f"ranked northern cell with the most typical clear-sky hours, {t}", f"{vc['long_open_hours_clear']} h (open {vc['long_open_hours']} h) at {clearest[0]['id']}, {clearest[0]['region']}",
                "max of targets.<t>.long_open_hours_clear over ranked northern records of cells_scored.json")
        A(f"**{tname[t]}:**")
        A("")
        L += table(["Site", "Cell centre (lat, lon)", "Region", "Bare", "Long-window open hours a year", "Typical clear-sky hours", "Clear-sky ÷ open", "Lighting score"], rows)
        A("")
    A("Source: `cells_scored.json` → ranked northern records, `targets.<target>.long_open_hours`, `.long_open_hours_clear`, `.goals.lighting`.")
    A("")

    # ---- (k)
    A("## (k) Version 2 against version 3")
    A("")
    A("Version 2 values are read from the kept files `validation_v2.json`, `cells_scored_v2.json` and the `_bin_median` thresholds of `latitude_profile.json`; version 3 values from the present files. "
      "The decisions are those of the version 3 plan: **12** long spells counted per day instead of per ten-day bin; **13** measured cells use the snow maps as they read; "
      f"**15** a terrain horizon for every cell that has elevation tiles on disk, not only for {len(recs2):,} candidates; **17** the cloud column (moves no figure below).")
    A("")
    A("### Lowest latitude with a 2 h spell")
    A("")
    rows = []
    for t in tids:
        for hemi in ("N", "S"):
            old_, new_ = th[t][hemi]["lowest_lat_with_long_window_bin_median"]["2"], th[t][hemi]["lowest_lat_with_long_window"]["2"]
            rows.append([f"{SHORT[t]}, {'north' if hemi == 'N' else 'south'}", f"{abs(old_):.2f}°", f"{abs(new_):.2f}°", moved(abs(old_), abs(new_), 2), "12"])
        num(f"lowest latitude with a 2 h spell, north, version 2 / version 3, {t}", f"{th[t]['N']['lowest_lat_with_long_window_bin_median']['2']} / {th[t]['N']['lowest_lat_with_long_window']['2']}",
            f"latitude_profile.json thresholds.{t}.N.lowest_lat_with_long_window_bin_median[2] and .lowest_lat_with_long_window[2]")
    L += table(["Target and hemisphere", "Version 2 (bin median)", "Version 3 (per day)", "Change", "Decision"], rows)
    A("")
    A("Source: `latitude_profile.json` → `thresholds.<target>.<N|S>.lowest_lat_with_long_window_bin_median[\"2\"]` and `.lowest_lat_with_long_window[\"2\"]`.")
    A("")
    A("### Measured northern cells reaching 50, 100 and 200 long-window snow-free hours (flat horizon)")
    A("")
    bp2 = val2["big_picture_north"]
    rows = []
    for t in old_tids:
        for season, label in (("winter_half", "winter half"), ("summer_half", "summer half")):
            for level in ("50", "100", "200"):
                old_ = bp2["targets"][t]["long_snow_free_hours"][season][level]["cells"]
                new_ = bp["targets"][t]["long_snow_free_hours"][season][level]["cells"]
                rows.append([f"{SHORT[t]}, {label}, ≥ {level} h", f(old_), f(new_), moved(old_, new_), "12 (13 moves a count by at most 1)"])
                num(f"measured cells with >= {level} long-window snow-free hours, {label}, version 2 / version 3, {t}", f"{old_} / {new_}",
                    f"validation_v2.json and validation.json big_picture_north.targets.{t}.long_snow_free_hours.{season}[{level}].cells")
    L += table(["Target, period and level", "Version 2", "Version 3", "Change", "Decision"], rows)
    A("")
    A("Source: `validation_v2.json` and `validation.json` → `big_picture_north.targets.<target>.long_snow_free_hours.<winter_half|summer_half>.<50|100|200>.cells`. "
      "That decision 13 moves a half-year count by at most one cell is from the build's own three-way comparison (before / decision 12 only / after); it was not recomputed here.")
    A("")
    A("### Winter-half share of the long-window snow-free hours × bare km²")
    A("")
    rows = []
    for t in old_tids:
        cal2 = bp2["targets"][t]["calendar_hours_times_bare_km2"]
        old_ = sum(cal2[b] for b in WINTER) / sum(cal2)
        new_ = cal_share(t)[0]
        rows.append([SHORT[t], f"{old_:.2%}", f"{new_:.2%}", f"{(new_ - old_) * 100:+.2f} points", "12 and 13"])
        num(f"winter-half share of long-window snow-free hours x bare km2, version 2 / version 3, {t}", f"{old_:.4f} / {new_:.4f}",
            f"validation_v2.json and validation.json big_picture_north.targets.{t}.calendar_hours_times_bare_km2, winter bins over all bins")
    L += table(["Target", "Version 2", "Version 3", "Change", "Decision"], rows)
    A("")
    A("Source: `validation_v2.json` and `validation.json` → `big_picture_north.targets.<target>.calendar_hours_times_bare_km2`, winter bins over all bins.")
    A("")
    A("### Share of long-window hours the terrain leaves (median)")
    A("")
    sample_ids = {c["id"] for c in cand if "sample" in c["why"]}
    rows = []
    for t in old_tids:
        old_n = [r["targets"][t]["long_open_hours"] / r["targets"][t]["long_snow_free_hours"] for r in recs2
                 if r["id"] in sample_ids and r["hemisphere"] == "N" and has_h(r) and (r["targets"][t]["long_snow_free_hours"] or 0) > 0 and r["targets"][t]["long_open_hours"] is not None]
        old_s = [r["targets"][t]["long_summer_rock_open_hours"] / r["targets"][t]["long_summer_rock_hours"] for r in recs2
                 if r["id"] in sample_ids and r["hemisphere"] == "S" and has_h(r) and (r["targets"][t]["long_summer_rock_hours"] or 0) > 0 and r["targets"][t]["long_summer_rock_open_hours"] is not None]
        rows.append([f"{SHORT[t]}, north", f"{pct(old_n, 50):.3f} (n {len(old_n)})" if old_n else "n/a", f"{ns[t]['median']:.3f} (n {ns[t]['cells']})" if ns[t]["cells"] else "n/a",
                     f"{na[t]['median']:.3f} (n {na[t]['cells']:,})" if na[t]["cells"] else "n/a", "12 (sample); 15 (all cells)"])
        rows.append([f"{SHORT[t]}, south", f"{pct(old_s, 50):.3f} (n {len(old_s)})" if old_s else "n/a", f"{ss[t]['median']:.3f} (n {ss[t]['cells']})" if ss[t]["cells"] else "n/a",
                     f"{sa[t]['median']:.3f} (n {sa[t]['cells']:,})" if sa[t]["cells"] else "n/a", "12 (sample); 15 (all cells)"])
        if old_n:
            num(f"median share of long-window hours left by terrain, northern blind sample, version 2 / version 3, {t}", f"{pct(old_n, 50):.3f} (n {len(old_n)}) / {ns[t]['median']} (n {ns[t]['cells']})",
                "cells_scored_v2.json sample cells: long_open_hours / long_snow_free_hours; validation.json terrain_share_left.north.blind_sample")
    L += table(["Target and side", "Version 2: blind sample", "Version 3: the same blind sample", "Version 3: every cell with a horizon", "Decision"], rows)
    A("")
    A("Source: version 2 from `cells_scored_v2.json` (the sample cells of `candidates.json`: `long_open_hours` ÷ `long_snow_free_hours`, south `long_summer_rock_open_hours` ÷ `long_summer_rock_hours`); "
      f"version 3 from `validation.json` → `terrain_share_left`. The sample is the same {ns['cells_in_group']} + {ss['cells_in_group']} cells in both versions; n is the number of them with a horizon and such hours.")
    A("")
    A("### The named sites, Malapert, long-window hours a year")
    A("")
    sites2 = {s["name"]: s for s in val2["named_sites"]["sites"]}
    rows = []
    for s in val["named_sites"]["sites"]:
        o = sites2.get(s["name"])
        if o is None or not s["in_grazing_cells"] or not o.get("in_grazing_cells"):
            continue
        m, m2 = s["targets"]["malapert"], o["targets"]["malapert"]
        c = by_id[s["cell"]]
        if s["hemisphere"] == "N":
            old_ = " / ".join(f(m2[k]["long"]["year"], 1) for k in ("flat", "snow_free", "open"))
            new_ = " / ".join(f(m[k]["long"]["year"], 1) for k in ("flat", "snow_free", "open"))
            why = "12" + (" and 13" if c["snow"]["status"] == "measured" and (c["snow"]["stuck_winters"] or 0) >= 1 else "")
            num(f"{s['name']}: Malapert long-window hours flat / snow-free / open, version 2 then version 3", f"{old_} then {new_}",
                "validation_v2.json and validation.json named_sites.sites[].targets.malapert.<flat|snow_free|open>.long.year")
        else:
            old_ = f"{f(m2['long_summer_rock_hours'], 1)} / n/a / {f(m2['long_summer_rock_open_hours'], 1)}"
            new_ = f"{f(m['long_summer_rock_hours'], 1)} / n/a / {f(m['long_summer_rock_open_hours'], 1)}"
            why = "12"
        rows.append([s["name"], s["snow"]["status"], old_, new_, "no change" if old_ == new_ else why])
    L += table(["Site", "Snow odds", "Version 2: flat / snow-free / open", "Version 3: flat / snow-free / open", "Decision"], rows)
    A("")
    A("Source: `validation_v2.json` and `validation.json` → `named_sites.sites[].targets.malapert.<flat|snow_free|open>.long.year`; southern sites `long_summer_rock_hours` and `long_summer_rock_open_hours` (rock season; snow not measured). "
      "The horizons of these cells are the same in both versions.")
    A("")
    A("### The first three lighting sites per target (north)")
    A("")
    ids2 = {r["id"] for r in recs2}
    rows = []
    for t in old_tids:
        old_sites = my_sites("north", "lighting", t, 3, recs2)[0]
        new_sites = my_sites("north", "lighting", t, 3)[0]
        for k in range(3):
            o = old_sites[k] if k < len(old_sites) else None
            n_ = new_sites[k] if k < len(new_sites) else None
            def show(r):
                if r is None:
                    return "none"
                v = r["targets"][t]
                return f"{r['lat']:.2f}, {r['lon']:.2f} ({r['region']}); {f(v['long_open_hours'])} h; score {v['goals']['lighting']:.3f}"
            if n_ is None or o is None:
                note = "n/a"
            elif n_["id"] == o["id"]:
                note = "same cell (12, 13 move its hours)"
            elif n_["id"] not in ids2:
                note = "15: the new cell had no horizon in version 2"
            else:
                note = "12, 13: both cells had a horizon in version 2"
            rows.append([f"{SHORT[t]} #{k + 1}", show(o), show(n_), note])
        num(f"first three lighting sites, north, version 2, {t}", "; ".join(r["id"] for r in old_sites), "my own ranking of cells_scored_v2.json (ranked north, score then hours, one per 50 km)")
        num(f"first three lighting sites, north, version 3, {t}", "; ".join(f"{r['id']} ({r['targets'][t]['long_open_hours']} h, {r['targets'][t]['goals']['lighting']})" for r in new_sites),
            "my own ranking of cells_scored.json (ranked north, score then hours, one per 50 km); same as ranking.txt")
    L += table(["Target and place", "Version 2: cell centre (region); open hours; score", "Version 3", "What moved it"], rows)
    A("")
    A(f"Source: `cells_scored_v2.json` ({len(recs2):,} records, {sum(r['ranked'] and r['ranking'] == 'north' for r in recs2):,} ranked in the north) and `cells_scored.json` ({len(recs):,} records, {len(rn):,} ranked in the north), "
      "each ranked here by lighting score, then hours, one site per 50 km. The last column is by elimination (which of the decisions could act on the two cells: "
      "a cell that had no horizon in version 2 can only have entered through 15; otherwise 12 and 13 are left), not from running the chain with one decision at a time.")
    A("")

    # ---- (l) and (m)
    winter_doc = load("winter_leads.json") if (D / "winter_leads.json").exists() else None
    A("## (l) Winter on small bare patches")
    A("")
    L += winter_lines(winter_doc, targets, meta.get("year_phases", 1))
    A("")
    access_doc = load("access_cells.json") if (D / "access_cells.json").exists() else None
    A("## (m) How reachable the best areas are")
    A("")
    L += access_lines(access_doc, recs, targets)
    A("")

    # ---- files
    A("## Files")
    A("")
    L += table(["File", "Written", "What"], [
        ["`latitude_profile.json`", mtime("latitude_profile.json"), "Sun geometry by latitude (a); both sets of thresholds"],
        ["`grazing_cells.json`, `grazing_bins.npz`", mtime("grazing_cells.json"), "hours per cell and target; per ten-day bin (per-day long spells)"],
        ["`candidates.json`", mtime("candidates.json"), "every cell, with the reasons of version 2 and the blind sample"],
        ["`horizon_cells.json`, `terrain_cells.json`", mtime("horizon_cells.json") + ", " + mtime("terrain_cells.json"), "terrain horizon; slope statistics"],
        ["`cloud_cells.json`", mtime("cloud_cells.json"), "monthly mean cloud amount per cell (NASA POWER)"],
        ["`cells_scored.json`, `ranking.txt`", mtime("cells_scored.json"), "scores, clear-sky hours and the ranking tables, every cell"],
        ["`validation.json`", mtime("validation.json"), "named sites, counts, terrain share, old against new, stability, regions, Haughton"],
        ["`snow_free_dekads.npz`", mtime("snow_free_dekads.npz"), "snow-free odds per ten-day bin (input)"],
        ["`snow_validation_many.json`", mtime("snow_validation_many.json"), "the station check of the snow odds (version 2 figures)"],
        ["`winter_leads.json`", mtime("winter_leads.json") if (D / "winter_leads.json").exists() else "n/a", "squares the bare-ground screen hides, winter half (l)"],
        ["`access_cells.json`", mtime("access_cells.json") if (D / "access_cells.json").exists() else "n/a", "distance to the nearest airfield (m)"],
        ["`checks.json`", mtime("checks.json") if (D / "checks.json").exists() else "n/a", "the independent recount and the comparison with JPL Horizons (i)"],
        ["`RESULTS_v2.md`, `validation_v2.json`, `ranking_v2.txt`, `cells_scored_v2.json`", mtime("validation_v2.json"), "version 2, kept for section (k)"],
    ])
    A("")
    A("Source: the time each file in `data/derived/` was last written, read from the file system when this file was generated (local time).")
    A("")
    return L, list(NUMBERS)


def main(out: Path = OUT) -> None:
    lines, numbers = build()
    side = out.with_name(out.name + ".part")
    side.write_text("\n".join(lines) + "\n")
    os.replace(side, out)
    print(f"wrote {out}: {len(lines)} lines; numbers: {len(numbers)}")


if __name__ == "__main__":
    main()

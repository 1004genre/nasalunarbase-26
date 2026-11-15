# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""UV, surface sunlight, clear-sky days and aerosol for every area. Writes data/derived/environment_cells.json.

For each cell of data/derived/grazing_cells.json: the 12 monthly climatology values of eight
NASA POWER parameters (see twinfinder/environment.py) for the 1 degree grid box that holds the
cell centre. The parameter names, definitions and units come from the service's own parameter
list, kept in data/raw/power_environment/parameters/.

The service is asked once per parameter and 10 degree block, one request at a time with a
pause; every raw answer is kept under data/raw/power_environment/ and a second run asks only
for what is missing. `--offline` forbids requests altogether. Two checks ask a little more
(kept under data/raw/power_environment/points/): the daily series 2001 to 2025 at three grid
boxes, to see which years the climatology fits, and the hourly UV index of ten days at two
boxes, to see whether the daily UV index is a mean of the hours or the highest hour.
`--no-checks` leaves them out.

    uv run python scripts/build_environment_cells.py            # asks only for what is not on disk
    uv run python scripts/build_environment_cells.py --offline  # makes no request

The result is written beside the old file and renamed into place. Nothing here enters a score.
"""
import argparse
import datetime
import json
import os
import statistics
import time
from pathlib import Path

from twinfinder import cloud, environment, temperature

CELLS = Path("data/derived/grazing_cells.json")
MOON = Path("data/derived/moon_cards.json")
RAW = Path("data/raw/power_environment")
POINTS = RAW / "points"
LISTING = RAW / "parameters" / "manager_list_RE_climatology.json"
LOG = RAW / "fetch_log.jsonl"
OUT = Path("data/derived/environment_cells.json")
TARGET = "malapert"
PLACES = [   # (name, area id or None, lat, lon): an id is used as given; without one, the nearest area
    ("Haughton crater", "75.3_-90.0", None, None),
    ("south-west Iceland (Reykjanes)", "63.8_-22.6", None, None),
    ("Pechora Sea coast", "68.9_54.3", None, None),
    ("near Ulukhaktok", None, 70.736, -117.77),
    ("Longyearbyen", "78.2_15.6", None, None),
    ("Vestfold Hills", "-68.5_78.0", None, None),
    ("McMurdo Dry Valleys", "-77.6_161.5", None, None),
]
DAILY_POINTS = [("Longyearbyen box", 78.5, 15.5), ("Haughton box", 75.5, -89.5), ("Dry Valleys box", -77.5, 161.5)]
HOURLY_POINTS = [("Longyearbyen box", 78.5, 15.5, "20200601", "20200610"),
                 ("Dry Valleys box", -77.5, 161.5, "20191215", "20191224")]
PERIODS = ((2001, 2020), (2001, 2025))
SHOWN = [*environment.FIELDS, "clear_days"]   # the eight rows as served, and clear days per typical month


def write_json(path: Path, value) -> None:
    side = path.with_name(path.name + ".part")
    side.write_text(json.dumps(value, separators=(",", ":"), allow_nan=False))
    os.replace(side, path)


def now_utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log_request(url: str, path: Path) -> None:
    with open(LOG, "a") as log:
        log.write(json.dumps({"time": now_utc(), "url": url, "file": str(path.relative_to(RAW)),
                              "bytes": path.stat().st_size}) + "\n")


def fetch_all(tiles, offline: bool, pause_s: float) -> tuple[int, list]:
    """Make sure every raw regional answer is on disk. Returns (requests made, what failed)."""
    asked, failed = 0, []
    wanted = [(parameter, tile) for parameter in environment.PARAMETERS for tile in tiles]
    missing = [(p, t) for p, t in wanted if not (RAW / cloud.raw_name(p, t)).exists()]
    print(f"{len(wanted)} raw answers wanted, {len(wanted) - len(missing)} on disk, {len(missing)} to ask", flush=True)
    if missing and offline:
        raise SystemExit(f"--offline, but {len(missing)} raw answers are missing, first {cloud.raw_name(*missing[0])}")
    for n, (parameter, tile) in enumerate(missing, 1):
        path = RAW / cloud.raw_name(parameter, tile)
        try:
            environment.fetch_tile(parameter, tile, RAW)
        except Exception as error:      # the network has dropped this evening: note it, go on, ask again next run
            failed.append({"file": path.name, "error": repr(error)[:300]})
            print(f"  FAILED {path.name}: {error!r}"[:300], flush=True)
            time.sleep(10.0)
            continue
        asked += 1
        log_request(cloud.regional_url(parameter, tile), path)
        if asked % 25 == 0:
            print(f"  {now_utc()} asked {asked} (at {n} of {len(missing)})", flush=True)
        time.sleep(pause_s)
    return asked, failed


def fetched_span(names) -> str:
    times = {}
    if LOG.exists():
        for line in LOG.read_text().splitlines():
            entry = json.loads(line)
            times[entry["file"]] = entry["time"]
    for name in names:
        if name not in times:
            stamp = datetime.datetime.fromtimestamp((RAW / name).stat().st_mtime, datetime.timezone.utc)
            times[name] = stamp.strftime("%Y-%m-%dT%H:%M:%SZ")
    used = sorted(times[name] for name in names)
    return used[0] if used[0] == used[-1] else f"{used[0]} to {used[-1]}"


def rnd(value, digits=4):
    return None if value is None else round(value, digits)


def spread(values) -> dict | None:
    known = sorted(v for v in values if v is not None)
    if not known:
        return None
    if len(known) == 1:
        return {"median": rnd(known[0]), "p10": rnd(known[0]), "p90": rnd(known[0]), "cells": 1}
    tenths = statistics.quantiles(known, n=10, method="inclusive")
    return {"median": rnd(statistics.median(known)), "p10": rnd(tenths[0]), "p90": rnd(tenths[8]), "cells": len(known)}


# ---- meta -----------------------------------------------------------------------------------------

def parameter_meta(parameter: str, listing: dict, raws: list[bytes]) -> dict:
    """What the service says about one parameter, checked against every raw answer used."""
    listed = listing.get(parameter)
    if not listed:
        raise SystemExit(f"{parameter} is not in the service's parameter list {LISTING}")
    heads = [cloud.answer_header(raw) for raw in raws]
    first = heads[0]
    for head in heads[1:]:
        for key in ("version", "sources", "start", "end", "fill_value"):
            if head.get(key) != first.get(key):
                raise SystemExit(f"{parameter}: raw answers disagree about {key}: {first.get(key)!r}, {head.get(key)!r}")
    units = {environment.answer_units(raw, parameter) for raw in raws}
    grids = {environment.answer_grid(raw) for raw in raws}
    if len(units) != 1 or units != {listed["units"]}:
        raise SystemExit(f"{parameter}: units in the answers {units} differ from the list's {listed['units']!r}")
    if grids != {(1.0, 1.0)}:
        raise SystemExit(f"{parameter}: answers are on grids {grids}, not 1 x 1 degree")
    about = environment.ABOUT[parameter]
    return {
        "field": about["field"],
        "group": about["group"],
        "name_in_the_service": listed["name"],
        "definition_in_the_service": listed["definition"],
        "unit": listed["units"],
        "source_named_by_the_service": first.get("sources"),
        "source_in_the_list": listed["source"],
        "grid": "1 x 1 degree boxes (centres at x.5 degrees), read from every answer; the CERES SYN1deg grid",
        "period_named_by_the_service": f"{first['start'][:4]}-{first['start'][4:6]}-{first['start'][6:]} to "
                                       f"{first['end'][:4]}-{first['end'][4:6]}-{first['end'][6:]}",
        "messages": first.get("messages"),
        "fill_value": first.get("fill_value"),
        "what_it_is": about["what_it_is"],
        "what_it_is_not": about["what_it_is_not"],
    }


def polar_night_facts(by_parameter: dict, boxes) -> dict:
    """What the service gives, box by box, in months whose clear-sky sunlight is 0.0."""
    clear = by_parameter["CLRSKY_SFC_SW_DWN"]
    dark = [(box, m) for box in boxes if clear.get(box) for m in range(12) if clear[box][m] == 0.0]
    facts = {"box_months_without_sunlight": len(dark)}
    for parameter in environment.PARAMETERS:
        rows = by_parameter[parameter]
        values = [rows.get(box, [None] * 12)[m] for box, m in dark]
        facts[parameter] = {"zero": sum(1 for v in values if v == 0.0), "null": sum(1 for v in values if v is None),
                            "other": sum(1 for v in values if v not in (None, 0.0)),
                            "largest_other": max((v for v in values if v not in (None, 0.0)), default=None)}
    return facts


# ---- checks against the daily and hourly series -----------------------------------------------------

def fetch_point(url: str, dest: Path, check, offline: bool, pause_s: float) -> bytes | None:
    if not dest.exists():
        if offline:
            return None
        try:
            temperature._fetch(url, dest, check, timeout=300.0)
        except Exception as error:
            print(f"  check request failed, left out: {error!r}"[:300], flush=True)
            return None
        log_request(url, dest)
        time.sleep(pause_s)
    return dest.read_bytes()


def period_check(by_parameter: dict, offline: bool, pause_s: float) -> dict:
    """The climatology of each box against the mean of the daily series over 2001-2020 and 2001-2025."""
    out = {"what": ("For three grid boxes, the service's monthly climatology against the daily series of the same box. "
                    "The series is averaged over 2001 to 2020 and over 2001 to 2025. "
                    "Mean and largest absolute difference over the months with a value on both sides. "
                    "The smaller mean difference shows which years the climatology fits."),
           "clear_days_rule": ("CLRSKY_DAYS is compared as the daily clear days of each calendar month added up over "
                               "all years, since the climatology's values exceed 31."),
           "points": []}
    for name, lat, lon in DAILY_POINTS:
        dest = POINTS / f"daily_{lat}_{lon}_20010101_20251231.json"
        url = environment.daily_url(lat, lon, "20010101", "20251231")
        raw = fetch_point(url, dest, lambda body: [environment.read_series(body, p) for p in environment.PARAMETERS],
                          offline, pause_s)
        entry = {"name": name, "box": [lat, lon], "file": str(dest) if raw else None, "by_parameter": None}
        if raw:
            answered = json.loads(raw)["geometry"]["coordinates"][:2]
            entry["point_answered_lon_lat"] = answered
            entry["by_parameter"] = {}
            for parameter in environment.PARAMETERS:
                clim = by_parameter[parameter].get((lat, lon))
                series = environment.read_series(raw, parameter)
                how = "total" if parameter == "CLRSKY_DAYS" else "mean"
                result = {}
                for first, last in PERIODS:
                    own = environment.monthly_climatology(series, first, last, how=how)
                    pairs = [(c, o) for c, o in zip(clim or [], own) if c is not None and o is not None]
                    result[f"{first}-{last}"] = ({"months": len(pairs),
                                                  "mean_abs_difference": rnd(statistics.fmean(abs(c - o) for c, o in pairs)),
                                                  "largest_abs_difference": rnd(max(abs(c - o) for c, o in pairs)),
                                                  "series_monthly": [rnd(v) for v in own]} if pairs else None)
                entry["by_parameter"][parameter] = result
        out["points"].append(entry)
    fits = {}
    for parameter in environment.PARAMETERS:
        sums = {f"{a}-{b}": [] for a, b in PERIODS}
        for entry in out["points"]:
            for period in sums:
                got = (entry["by_parameter"] or {}).get(parameter, {}).get(period)
                if got:
                    sums[period].append(got["mean_abs_difference"])
        means = {period: rnd(statistics.fmean(v)) if v else None for period, v in sums.items()}
        known = {p: v for p, v in means.items() if v is not None}
        fits[parameter] = {"mean_abs_difference_by_period": means,
                           "fits_better": min(known, key=known.get) if len(known) == len(PERIODS) else None}
    out["summary"] = fits
    return out


def uv_hours_check(offline: bool, pause_s: float) -> dict:
    """Is the service's daily UV index the mean of the day's hours or its highest hour? Ten days at two boxes."""
    out = {"what": ("The daily ALLSKY_SFC_UV_INDEX against the mean and the highest hour of the hourly series. "
                    "Same days and box; hours in local solar time."), "points": []}
    for name, lat, lon, start, end in HOURLY_POINTS:
        dest = POINTS / f"hourly_UV_{lat}_{lon}_{start}_{end}.json"
        hourly = fetch_point(environment.hourly_url(lat, lon, start, end), dest,
                             lambda body: environment.read_series(body, "ALLSKY_SFC_UV_INDEX"), offline, pause_s)
        daily_dest = POINTS / f"daily_UV_{lat}_{lon}_{start}_{end}.json"
        daily = fetch_point(environment.daily_url(lat, lon, start, end, ("ALLSKY_SFC_UV_INDEX",)), daily_dest,
                            lambda body: environment.read_series(body, "ALLSKY_SFC_UV_INDEX"), offline, pause_s)
        entry = {"name": name, "box": [lat, lon], "days": f"{start} to {end}", "result": None}
        if hourly and daily:
            by_day = environment.hours_to_days(environment.read_series(hourly, "ALLSKY_SFC_UV_INDEX"))
            days = environment.read_series(daily, "ALLSKY_SFC_UV_INDEX")
            rows = [(days[d], by_day[d]["mean"], by_day[d]["max"]) for d in days
                    if days[d] is not None and d in by_day and by_day[d]["mean"] is not None]
            if rows:
                entry["result"] = {
                    "days": len(rows),
                    "daily_value_mean": rnd(statistics.fmean(r[0] for r in rows), 3),
                    "mean_of_hours_mean": rnd(statistics.fmean(r[1] for r in rows), 3),
                    "highest_hour_mean": rnd(statistics.fmean(r[2] for r in rows), 3),
                    "mean_abs_gap_to_mean_of_hours": rnd(statistics.fmean(abs(r[0] - r[1]) for r in rows), 3),
                    "mean_abs_gap_to_highest_hour": rnd(statistics.fmean(abs(r[0] - r[2]) for r in rows), 3),
                }
        out["points"].append(entry)
    results = [p["result"] for p in out["points"] if p["result"]]
    if results:
        to_mean = statistics.fmean(r["mean_abs_gap_to_mean_of_hours"] for r in results)
        to_max = statistics.fmean(r["mean_abs_gap_to_highest_hour"] for r in results)
        out["daily_value_is"] = "the mean of the hours" if to_mean < to_max else "nearer the highest hour"
    else:
        out["daily_value_is"] = None
    return out


def clear_day_years(checks) -> dict:
    """How many years the service's CLRSKY_DAYS totals cover, from the period check; years None if unsettled.

    Settled when the daily series' totals over a period equal the climatology at every box
    checked within half a day on average, and its gaps added up are smaller than those of
    every other period that does so too.
    """
    out = {"years": None, "period": None, "how": None}
    if not checks:
        out["how"] = "no check was run"
        return out
    by_period = {}
    for entry in checks["period"]["points"]:
        got = (entry.get("by_parameter") or {}).get("CLRSKY_DAYS") or {}
        for period, result in got.items():
            if result:
                by_period.setdefault(period, []).append(result["mean_abs_difference"])
    good = [period for period, gaps in by_period.items()
            if len(gaps) == len(checks["period"]["points"]) and max(gaps) <= 0.5]
    ranked = sorted(good, key=lambda period: sum(by_period[period]))
    if ranked and (len(ranked) == 1 or sum(by_period[ranked[0]]) < sum(by_period[ranked[1]])):
        best = ranked[0]
        first, last = (int(year) for year in best.split("-"))
        out.update(years=last - first + 1, period=best,
                   how=(f"The daily clear days added up over {best} equal the climatology at every box checked. "
                        f"Mean gaps by box: {by_period[best]} days. "
                        f"Other periods: { {p: g for p, g in by_period.items() if p != best} }."))
    else:
        out["how"] = f"not settled: mean gaps by period {by_period}"
    return out


# ---- named places and the lunar comparison --------------------------------------------------------------

def find_cell(cells, by_id, cid, lat, lon):
    if cid:
        return by_id.get(cid)
    return min(cells, key=lambda c: (c["lat"] - lat) ** 2 + ((c["lon"] - lon) * 0.33) ** 2)


def place_report(name, cell, record, summer_south, summer_north) -> dict:
    if cell is None or record is None:
        return {"name": name, "note": "no such area"}
    pairs = cell["targets"][TARGET].get("top_bins") or []
    season = summer_south if cell["hemisphere"] == "S" else summer_north
    rows = {field: environment.ten_day_values(record[field]) for field in SHOWN}
    bins = []
    for b, hours in pairs:
        bins.append({"bin": b, "dates": bin_label(b), "long_window_hours": hours,
                     "in_" + ("southern_rock_season" if cell["hemisphere"] == "S" else "northern_summer_half"): b in season,
                     "month": cloud.BIN_MONTH[b] + 1,
                     "values": {field: rows[field][b] for field in SHOWN}})
    return {"name": name, "area": cell["id"], "centre": [cell["lat"], cell["lon"]], "site_name": cell.get("site_name"),
            "grid": record["grid"], "sunless_months": record["sunless_months"],
            "best_bins_source": f"{CELLS} targets.{TARGET}.top_bins", "best_bins": bins}


def bin_label(b: int) -> str:
    first = datetime.date(2025, 1, 1) + datetime.timedelta(days=b * 10)
    last = datetime.date(2025, 12, 31) if b == cloud.N_BINS - 1 else first + datetime.timedelta(days=9)
    return f"{first.day} {first.strftime('%b')}-{last.day} {last.strftime('%b')}"


def lunar_comparison(counts: dict) -> dict:
    """One sentence per thing, Earth from the medians above, the Moon from moon_cards.json or 'not in our data'."""
    try:
        cards = json.loads(MOON.read_text())["cards"]
    except (OSError, ValueError, KeyError):
        cards = []
    vacuum = next((row for card in cards for row in card.get("earth_cannot_match") or [] if row.get("what") == "vacuum"), None)
    dust = next((row for card in cards for row in card.get("earth_cannot_match") or [] if row.get("what") == "dust"), None)
    lit = {card["id"]: card.get("lit", {}).get("mean_share") for card in cards}
    ceiling = {card["id"]: card.get("sun_ceiling", {}).get("deg") for card in cards}
    north, south = counts["north_cells"], counts["south_cells"]

    def med(half, month, field):
        got = half[month][field]
        return "n/a" if not got else f"{got['median']:g}"

    pressure = f"{vacuum['number']:g} bar" if vacuum and vacuum.get("number") is not None else "not in our data"
    lit_text = (", ".join(f"{k} {v:.0%}" for k, v in lit.items() if v is not None) if any(lit.values())
                else "not in our data")
    known_ceilings = [v for v in ceiling.values() if v is not None]
    ceiling_text = (f"the Sun stays below {min(known_ceilings):.2f} to {max(known_ceilings):.2f} degrees"
                    if known_ceilings else "the highest Sun is not in our data")
    dust_words = dust["moon"] if dust and dust.get("moon") and len(dust["moon"].split()) <= 25 else None
    return {   # every sentence 25 words or fewer (tests/test_environment.py)
        "moon_file": str(MOON),
        "uv": (f"Median UV index (24-hour monthly mean, all sky): northern areas in July {med(north, 'july', 'uv_index')}, "
               f"southern areas in December {med(south, 'december', 'uv_index')}. "
               f"The Moon has no air (surface pressure {pressure}, moon_cards.json), so nothing filters UV, UVC included. "
               f"A lunar UV figure is not in our data."),
        "sunlight": (f"Median sunlight on level ground, northern areas in July: {med(north, 'july', 'sun_kwh_m2_day')} "
                     f"kWh/m2/day, clear-sky {med(north, 'july', 'sun_clear_kwh_m2_day')}. "
                     f"At the lunar sites no air dims it, and {ceiling_text} (moon_cards.json). "
                     f"Mean share of time lit, averaged over each mapped area: {lit_text}. "
                     f"The energy per day on a lunar surface is not in our data."),
        "cloud_free": (f"Median clear-sky days a month (daytime cloud under 10 percent): northern areas "
                       f"{med(north, 'july', 'clear_days')} in July, {med(north, 'august', 'clear_days')} in August. "
                       f"Southern areas: {med(south, 'december', 'clear_days')} in December, "
                       f"{med(south, 'january', 'clear_days')} in January. "
                       f"The Moon has no air (surface pressure {pressure}, moon_cards.json), so no cloud."),
        "dust": (f"Median aerosol optical depth at 550 nm: northern areas in July {med(north, 'july', 'aod_550')}, "
                 f"southern areas in December {med(south, 'december', 'aod_550')}. "
                 f"These are particles in the air, not dust on the ground. "
                 f"The Moon has no air to hold particles; its dust lies on the ground. "
                 + (f"moon_cards.json: {dust_words} " if dust_words else "")
                 + "A lunar dust figure is not in our data."),
    }


def dust_only_figure(listing: dict) -> str:
    """What the service's parameter list offers for dust, read from the list itself: its aerosol parameters."""
    aerosol = sorted(name for name, entry in listing.items()
                     if name.startswith("AOD") or "aerosol" in f"{entry.get('name')} {entry.get('definition')}".lower())
    dusty = sorted(name for name, entry in listing.items()
                   if "DUST" in name or "dust" in f"{entry.get('name')} {entry.get('definition')}".lower())
    used = environment.FIELDS["aod_550"]
    return (("No dust-only figure: no parameter has dust in its name or definition. " if not dusty else
             f"Parameters naming dust: {', '.join(dusty)}. ")
            + f"Aerosol parameters in the list: {', '.join(aerosol) or 'none'}. "
            + f"This file uses {used}, all fine particles together.")


# ---- main ---------------------------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--offline", action="store_true", help="make no request; fail if a raw regional answer is missing")
    parser.add_argument("--pause", type=float, default=0.6, help="seconds between two requests")
    parser.add_argument("--no-checks", action="store_true", help="leave out the daily and hourly checks")
    args = parser.parse_args()

    grazing = json.loads(CELLS.read_text())
    cells = grazing["cells"]
    boxes = cloud.boxes_of(cells)
    tiles = cloud.tiles_for(boxes)
    print(f"{len(cells)} cells in {len(boxes)} grid boxes of 1 degree; {len(tiles)} blocks of {cloud.TILE_DEG} "
          f"degrees x {len(environment.PARAMETERS)} parameters", flush=True)
    RAW.mkdir(parents=True, exist_ok=True)
    POINTS.mkdir(parents=True, exist_ok=True)
    asked, failed = fetch_all(tiles, args.offline, args.pause)
    print(f"regional requests made in this run: {asked}; failed: {len(failed)}", flush=True)
    if failed:
        raise SystemExit(f"{len(failed)} raw answers could not be had; run again to ask only for those")

    listing = json.loads(LISTING.read_text())
    by_parameter, parameters_meta = {}, {}
    for parameter in environment.PARAMETERS:
        raws = [(RAW / cloud.raw_name(parameter, tile)).read_bytes() for tile in tiles]
        by_parameter[parameter] = environment.read_raw(RAW, parameter, tiles)
        parameters_meta[parameter] = parameter_meta(parameter, listing, raws)
    names = {cloud.raw_name(p, t) for p in environment.PARAMETERS for t in tiles}
    missing = {p: [b for b in boxes if b not in by_parameter[p]] for p in environment.PARAMETERS}

    checks = None
    if not args.no_checks:
        checks = {"period": period_check(by_parameter, args.offline, args.pause),
                  "uv_index_daily_value": uv_hours_check(args.offline, args.pause)}
    clear_years = clear_day_years(checks)
    table = environment.cells_table(cells, by_parameter, clear_day_years=clear_years["years"])
    north = [c["id"] for c in cells if c["hemisphere"] == "N"]
    south = [c["id"] for c in cells if c["hemisphere"] == "S"]
    fields = list(SHOWN)

    def month(ids, field, m):
        return spread(table[i][field][m] if table[i][field] else None for i in ids)

    counts = {
        "cells": len(table), "grid_boxes": len(boxes), "raw_answers": len(names),
        "grid_boxes_the_service_did_not_give": {p: len(v) for p, v in missing.items()},
        "cells_with_all_12_months": {f: sum(1 for r in table.values() if r[f] and all(v is not None for v in r[f]))
                                     for f in fields},
        "cells_with_some_months_null": {f: sum(1 for r in table.values() if r[f] and any(v is None for v in r[f]))
                                        for f in fields},
        "cells_with_null_row": {f: sum(1 for r in table.values() if not r[f]) for f in fields},
        "cells_with_a_sunless_month": sum(1 for r in table.values() if r["sunless_months"]),
        "north_cells": {"cells": len(north), "july": {f: month(north, f, 6) for f in fields},
                        "august": {f: month(north, f, 7) for f in fields}},
        "south_cells": {"cells": len(south), "december": {f: month(south, f, 11) for f in fields},
                        "january": {f: month(south, f, 0) for f in fields}},
    }
    by_id = {c["id"]: c for c in cells}
    places = []
    for name, cid, lat, lon in PLACES:
        cell = find_cell(cells, by_id, cid, lat, lon)
        places.append(place_report(name, cell, table.get(cell["id"]) if cell else None,
                                   grazing["meta"]["summer_bins_south"], grazing["meta"]["summer_bins_north"]))

    meta = {
        "what": ("UV exposure, surface sunlight, cloud-free days and haze for every area of grazing_cells.json. "
                 "The team asked for haze as 'dust conditions'; the figure is aerosol optical depth. "
                 "Each field holds 12 monthly NASA POWER climatology values, January first. "
                 "They are for the 1 degree grid box that holds the area centre; many areas share one box. "
                 "Satellite-based and model values for a box about 111 km tall, not measurements at the area. "
                 "Nothing here enters a score."),
        "source": "NASA POWER, POWER Climatology API (version in each parameter's answers), regional endpoint, community RE",
        "parameter_list": {"url": environment.MANAGER_URL, "file": str(LISTING),
                           "read_on": "2026-11-14",
                           "dust_only_figure": dust_only_figure(listing)},
        "parameters": parameters_meta,
        "fields": {about["field"]: parameter for parameter, about in environment.ABOUT.items()},
        "clear_days": {"meaning": ("clear_days_total (the service's CLRSKY_DAYS, added up over the years) divided by the "
                                   "years it covers. That gives clear-sky days in a typical calendar month. "
                                   "Null when checks.period could not settle the number of years."),
                       **clear_years},
        "field_names_note": ("uva_kwh_m2_day and uvb_kwh_m2_day replace the uva_w_m2 and uvb_w_m2 that were asked for. "
                             "The service gives UVA and UVB in kWh per square metre per day, not W per square metre. "
                             "clear_days_total is CLRSKY_DAYS as served; clear_days is per typical month."),
        "period_caution": ("Every answer names 2001-01-01 to 2025-12-31. "
                           "The temperature column found the MERRA-2 values fit 2001 to 2020 instead (temperature_cells.json). "
                           "For these SYN1deg parameters, checks.period tests both periods at three boxes. "
                           "Read period_named_by_the_service as what the service says."),
        "polar_night": {
            "rule": ("sunless_months lists the months (1 = January) whose clear-sky sunlight in the box is 0.0 as served. "
                     "facts counts what the service gives in those box-months: zero, null (its fill value) or another number. "
                     "UV and sunlight there are a real zero. "
                     "The clearness index is mostly the fill value. "
                     "Clear-day totals are often above 0 there, since the service counts days by its cloud rule. "
                     "So they say nothing about seeing by sunlight in those months."),
            "facts": polar_night_facts(by_parameter, boxes),
        },
        "null_rule": ("A row is null when no month has a value or the service gave no such box. "
                      "A single month without a value is null inside the row. "
                      "The service's fill value is never turned into a number."),
        "cell_to_grid": "the 1 degree box that holds the cell centre (cloud.grid_box); grid = {lat, lon of the box centre, deg}",
        "ten_day_rule": ("environment.ten_day_values(row) gives 36 ten-day values. "
                         "Each period takes the month of its middle day; period = min((day_of_year - 1) // 10, 35)."),
        "request_rules_followed": ("One parameter and at most 10 x 10 degrees a request, one request at a time with "
                                   "a pause, User-Agent twinfinder/0.1, no key, no login."),
        "raw_answers": {"folder": str(RAW), "files": len(names), "log": str(LOG)},
        "fetched": fetched_span(names),
        "cells_source": str(CELLS),
        "written": now_utc(),
        "counts": counts,
        "checks": checks,
        "named_places": {"target": TARGET, "places": places},
        "lunar_comparison": lunar_comparison(counts),
        "not_checked": ["how CERES SYN1deg makes its aerosol and UV values (the service names SYN1DEG; nothing else "
                        "was read)", "any comparison with ground stations",
                        "the hours of low Sun: every value is a whole-day or monthly mean"],
    }
    write_json(OUT, {"meta": meta, "cells": table})
    print(f"wrote {OUT}: {counts['cells']} cells, {counts['grid_boxes']} grid boxes, {len(names)} raw answers")


if __name__ == "__main__":
    main()

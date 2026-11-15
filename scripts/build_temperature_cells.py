# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Earth temperature for every cell. Writes data/derived/temperature_cells.json.

For each cell of data/derived/grazing_cells.json: the monthly climatology of air
temperature at 2 m (mean T2M, and the service's T2M_MAX and T2M_MIN, which are the
highest and lowest hour of each calendar month in the whole period, not mean daily
extremes) and of the surface temperature (TS), at the MERRA-2 grid point nearest
to the cell centre, from the NASA POWER climatology service.

The service is asked once per parameter and 10 degree block, one request at a time
with a pause; every raw answer is kept under data/raw/power_temperature/ and a
second run makes no request. `--offline` forbids requests altogether.

For six named places it also asks the daily series of the cell's grid point (one
request a place, kept under data/raw/power_temperature/daily_points/), because the
mean daily maximum and minimum by ten-day period can only be worked out from days.
`--no-places` leaves that out. The places and their best ten-day periods are read
from grazing_cells.json (and, for southern cells, from cells_scored.json if it is
there) at run time, so run this again after those files change:

    uv run python scripts/build_temperature_cells.py            # asks only for what is not on disk
    uv run python scripts/build_temperature_cells.py --offline  # makes no request

The result is written beside the old file and renamed into place. Temperature
enters no score. See twinfinder/temperature.py for what the numbers are and are not.
"""
import argparse
import datetime
import json
import os
import statistics
import time
from pathlib import Path

from twinfinder import cloud, grid, temperature

CELLS = Path("data/derived/grazing_cells.json")
SCORED = Path("data/derived/cells_scored.json")
MOON = Path("data/derived/moon_cards.json")     # written by the member LUNAR-CARDS; only named here
RAW = Path("data/raw/power_temperature")
DAILY = RAW / "daily_points"
LOG = RAW / "fetch_log.jsonl"
OUT = Path("data/derived/temperature_cells.json")
PLACES = [
    ("Reykjanes", 63.88, -22.45),
    ("Haughton crater", 75.38, -89.67),
    ("Pechora Sea coast", 68.95, 54.45),
    ("Kotelny Island", 74.95, 141.25),
    ("Longyearbyen", 78.2, 15.6),
    ("Vestfold Hills", -68.45, 78.15),
]
DAILY_FIELDS = {"t2m_c": "T2M", "t2m_daily_max_c": "T2M_MAX", "t2m_daily_min_c": "T2M_MIN", "ts_c": "TS"}
LUNAR_SENTENCE = (
    "Earth does not match the Moon in temperature: in their best ten-day periods the Earth places above "
    "have mean air temperatures between {earth_low} and {earth_high} C, while the lunar south-pole sites "
    "are at {LUNAR: fill in from data/derived/moon_cards.json, the Diviner figures of the member "
    "LUNAR-CARDS}; a field test there rehearses the light, not the cold."
)


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


def fetch_all(tiles, offline: bool, pause_s: float) -> int:
    """Make sure every raw regional answer is on disk. Returns the number of requests made."""
    asked = 0
    wanted = [(parameter, tile) for parameter in temperature.PARAMETERS for tile in tiles]
    for n, (parameter, tile) in enumerate(wanted, 1):
        path = RAW / cloud.raw_name(parameter, tile)
        if path.exists():
            continue
        if offline:
            raise SystemExit(f"--offline, but {path} is missing")
        temperature.fetch_tile(parameter, tile, RAW)
        asked += 1
        log_request(cloud.regional_url(parameter, tile), path)
        if asked % 25 == 0:
            print(f"  asked {asked} (at {n} of {len(wanted)})", flush=True)
        time.sleep(pause_s)
    return asked


def fetched_span(names) -> str:
    """When the raw answers that were used came from the service (UTC), from the log or the file times."""
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


def r1(value):
    return None if value is None else round(value, 1)


def spread(values) -> dict | None:
    """Median, 10th and 90th percentile and count of the known values; None if there is none."""
    known = sorted(v for v in values if v is not None)
    if not known:
        return None
    if len(known) == 1:
        return {"median": r1(known[0]), "p10": r1(known[0]), "p90": r1(known[0]), "cells": 1}
    tenths = statistics.quantiles(known, n=10, method="inclusive")
    return {"median": r1(statistics.median(known)), "p10": r1(tenths[0]), "p90": r1(tenths[8]), "cells": len(known)}


def summary(cells, table) -> dict:
    """Counts and medians over cells, for the meta block and the printed report."""
    north = [c["id"] for c in cells if c["hemisphere"] == "N"]
    south = [c["id"] for c in cells if c["hemisphere"] == "S"]
    fields = list(temperature.FIELDS)

    def month(ids, field, m):
        return spread(table[i][field][m] if table[i][field] else None for i in ids)

    return {
        "cells": len(table),
        "grid_points": len({tuple(r["grid"]) for r in table.values()}),
        "cells_with_all_12_months": {f: sum(1 for r in table.values() if r[f] and all(v is not None for v in r[f]))
                                     for f in fields},
        "cells_with_some_months": {f: sum(1 for r in table.values() if r[f] and any(v is None for v in r[f]))
                                   for f in fields},
        "cells_with_no_month": {f: sum(1 for r in table.values() if not r[f]) for f in fields},
        "north_cells": {"cells": len(north),
                        "july": {f: month(north, f, 6) for f in fields},
                        "august": {f: month(north, f, 7) for f in fields}},
        "south_cells": {"cells": len(south),
                        "december": {f: month(south, f, 11) for f in fields},
                        "january": {f: month(south, f, 0) for f in fields}},
    }


# ---- the six named places ---------------------------------------------------------------------------

def bin_label(b: int) -> str:
    """Dates of a ten-day bin in a 365-day year, such as "30 Jul-8 Aug" for bin 21."""
    first = datetime.date(2025, 1, 1) + datetime.timedelta(days=b * 10)
    last = datetime.date(2025, 12, 31) if b == cloud.N_BINS - 1 else first + datetime.timedelta(days=9)
    return f"{first.day} {first.strftime('%b')}-{last.day} {last.strftime('%b')}"


def lat_lon_name(lat: float, lon: float) -> str:
    return f"{'N' if lat >= 0 else 'S'}{abs(lat):06.3f}_{'E' if lon >= 0 else 'W'}{abs(lon):07.3f}"


def best_bins(cell: dict, scored: dict, summer_south: list[int]) -> tuple[dict, str]:
    """Best ten-day bins of a cell by target, [[bin, hours], ...], and where they were read from.

    North: `top_bins` of grazing_cells.json. South: `top_bins_summer_rock` of
    cells_scored.json if the cell is there, otherwise the summer bins among
    `top_bins` of grazing_cells.json (the southern search counts summer only).
    """
    if cell["hemisphere"] == "S":
        record = scored.get(cell["id"])
        if record and all(t.get("top_bins_summer_rock") is not None for t in record["targets"].values()):
            return ({name: t["top_bins_summer_rock"] for name, t in record["targets"].items()},
                    f"{SCORED} targets.<target>.top_bins_summer_rock")
        return ({name: [pair for pair in t.get("top_bins") or [] if pair[0] in summer_south]
                 for name, t in cell["targets"].items()},
                f"{CELLS} targets.<target>.top_bins, summer bins only")
    return ({name: t.get("top_bins") or [] for name, t in cell["targets"].items()},
            f"{CELLS} targets.<target>.top_bins")


def daily_rows(raw: bytes) -> tuple[dict, dict]:
    """Ten-day means of the daily series (by field) and its monthly statistics (by parameter)."""
    rows, monthly = {}, {}
    for field, parameter in DAILY_FIELDS.items():
        series = temperature.read_daily(raw, parameter)
        means, counts = temperature.daily_mean_by_bin(series)
        rows[field] = [r1(v) for v in means]
        rows.setdefault("days_counted", counts)
        monthly[parameter] = temperature.monthly_statistics(series)
    return rows, monthly


def extremes_check(record: dict, monthly: dict) -> dict:
    """How the climatology's T2M_MAX and T2M_MIN sit against the daily series of the same grid point."""
    out = {}
    for field, parameter, record_key in (("t2m_max_c", "T2M_MAX", "highest"), ("t2m_min_c", "T2M_MIN", "lowest")):
        clim = record[field]
        if not clim:
            out[parameter] = None
            continue
        pairs = [(c, monthly[parameter][record_key][m], monthly[parameter]["mean"][m])
                 for m, c in enumerate(clim) if c is not None and monthly[parameter]["mean"][m] is not None]
        out[parameter] = {
            "months_compared": len(pairs),
            "months_equal_to_the_25_year_record_of_the_daily_series": sum(1 for c, rec, _ in pairs if abs(c - rec) < 0.011),
            "largest_gap_to_that_record_c": round(max(abs(c - rec) for c, rec, _ in pairs), 2),
            "mean_gap_to_the_mean_daily_value_c": round(statistics.mean(c - mean for c, _, mean in pairs), 2),
        }
    return out


def extremes_check_all(places: list[dict]) -> dict | None:
    """The extremes checks of all places added up, by parameter; None if no place has one."""
    out = {}
    for parameter in ("T2M_MAX", "T2M_MIN"):
        checks = [p["extremes_check"][parameter] for p in places
                  if p.get("extremes_check") and p["extremes_check"].get(parameter)]
        if not checks:
            continue
        equal = "months_equal_to_the_25_year_record_of_the_daily_series"
        out[parameter] = {
            "places": len(checks),
            "months_compared": sum(c["months_compared"] for c in checks),
            equal: sum(c[equal] for c in checks),
            "largest_gap_to_that_record_c": max(c["largest_gap_to_that_record_c"] for c in checks),
            "mean_gap_to_the_mean_daily_value_c": round(
                statistics.mean(c["mean_gap_to_the_mean_daily_value_c"] for c in checks), 2),
        }
    return out or None


def years_fit_all(places: list[dict], period_named: str) -> dict | None:
    """The years the climatology's values fit, over all places with a daily series; None if no place has one.

    The service's answers name a period. Whether its monthly extremes were really taken over that
    period is checked place by place (temperature.years_the_climatology_fits); here the places are
    added up and decide together: the last year with the most equal months over all places (the
    later year on a tie). years_the_values_fit is null when the series do not start in the same year.
    """
    fits = [p["years_fit"] for p in places if p.get("years_fit")]
    if not fits:
        return None
    by_year: dict[str, int] = {}
    for fit in fits:
        for year, months in fit["months_equal_by_end_year"].items():
            by_year[year] = by_year.get(year, 0) + months
    together = len({f["first_year"] for f in fits}) == 1 and all(
        set(f["months_equal_by_end_year"]) == set(by_year) for f in fits)
    best = max(by_year, key=lambda year: (by_year[year], int(year)))
    compared = sum(f["months_compared"] for f in fits)
    named = sum(f["months_equal_with_all_years"] for f in fits)
    return {
        "period_named_by_the_service": period_named,
        "years_the_values_fit": f"{fits[0]['first_year']} to {best}" if together else None,
        "places": len(fits),
        "months_compared": compared,
        "months_equal_over_the_years_that_fit": by_year[best] if together else None,
        "months_equal_by_last_year": dict(sorted(by_year.items())) if together else None,
        "months_equal_over_the_period_named": named,
        "agrees_with_the_period_named": named == compared,
        "meaning": ("the climatology's monthly T2M_MAX and T2M_MIN against the highest and lowest day of the "
                    "daily series of the same grid point: months_compared counts both, for every place; a month "
                    "is equal when the two agree within 0.011 C. If the values fit fewer years than the service "
                    "names, read `period` as what the service says, and years_the_values_fit as what the "
                    "numbers show; the monthly means (t2m_c, ts_c) come from the same pre-computed table"),
    }


def place_report(name, lat, lon, by_id, scored, table, summer_south, period, offline, pause_s) -> dict:
    cid = grid.cell_id(lat, lon)
    cell = by_id.get(cid)
    if cell is None:
        return {"name": name, "lat": lat, "lon": lon, "cell": cid, "note": f"no cell {cid} in {CELLS}"}
    record = table[cid]
    bins, source = best_bins(cell, scored, summer_south)
    out = {"name": name, "lat": lat, "lon": lon, "cell": cid, "cell_centre": [cell["lat"], cell["lon"]],
           "site_name": cell.get("site_name"), "grid": record["grid"], "grid_elev_m": record["grid_elev_m"],
           "best_bins_source": source, "daily_series": None, "extremes_check": None, "years_fit": None}
    rows = None
    if period is not None:
        start, end = period
        path = DAILY / f"daily_{lat_lon_name(*record['grid'])}_{start}_{end}.json"
        if not path.exists() and not offline:
            temperature.fetch_daily(record["grid"][0], record["grid"][1], start, end, path)
            log_request(temperature.daily_url(record["grid"][0], record["grid"][1], start, end), path)
            time.sleep(pause_s)
        if path.exists():
            raw = path.read_bytes()
            rows, monthly = daily_rows(raw)
            where = temperature.daily_position(raw)
            out["daily_series"] = {"file": str(path), "grid_point_answered": [where[0], where[1]],
                                   "same_grid_point": [where[0], where[1]] == record["grid"],
                                   "years": f"{start[:4]} to {end[:4]}", "by_bin": rows}
            out["extremes_check"] = extremes_check(record, monthly)
            out["years_fit"] = temperature.years_the_climatology_fits(
                record["t2m_max_c"], record["t2m_min_c"],
                temperature.read_daily(raw, "T2M_MAX"), temperature.read_daily(raw, "T2M_MIN"))
    by_month = {field: temperature.by_bin(record[field]) for field in temperature.FIELDS}
    targets, union = {}, set()
    for target, pairs in bins.items():
        listed = []
        for b, hours in pairs:
            union.add(b)
            entry = {"bin": b, "dates": bin_label(b), "hours": hours,
                     "month_climatology": {field: by_month[field][b] for field in temperature.FIELDS}}
            if rows:
                entry["ten_day_mean_of_daily_series"] = {field: rows[field][b] for field in DAILY_FIELDS}
            listed.append(entry)
        targets[target] = listed
    out["best_bins_by_target"] = targets
    out["best_bins_any_target"] = [
        {"bin": b, "dates": bin_label(b),
         "month_climatology": {field: by_month[field][b] for field in temperature.FIELDS},
         "ten_day_mean_of_daily_series": {field: rows[field][b] for field in DAILY_FIELDS} if rows else None}
        for b in sorted(union)]
    return out


LUNAR_GAP = ("{LUNAR: fill in from data/derived/moon_cards.json, the Diviner figures of the member "
             "LUNAR-CARDS}")


def lunar_figures(cards) -> dict | None:
    """Lowest and highest site mean, and the coldest spot, of the Diviner annual mean temperature 2 cm under
    the surface on the lunar cards, in Celsius. None when the cards are absent or any card lacks a figure."""
    try:
        rows = [card["diviner"]["annual_mean_temp_2cm_C"] for card in cards["cards"]]
        means, coldest = [row["mean"] for row in rows], [row["min"] for row in rows]
    except (KeyError, TypeError):
        return None
    if not means or any(value is None for value in means + coldest):
        return None
    return {"low": min(means), "high": max(means), "coldest": min(coldest)}


def lunar_placeholder(places: list[dict], cards=None) -> dict:
    """The sentence that sets Earth against the Moon; the lunar part is filled only when the cards hold it."""
    moon = lunar_figures(cards)
    means = []
    for place in places:
        for entry in place.get("best_bins_any_target") or []:
            daily = entry["ten_day_mean_of_daily_series"]
            value = daily["t2m_c"] if daily else entry["month_climatology"]["t2m_c"]
            if value is not None:
                means.append(value)
    low, high = (f"{min(means):.0f}", f"{max(means):.0f}") if means else ("null", "null")
    sentence = LUNAR_SENTENCE.replace("{earth_low}", low).replace("{earth_high}", high)
    if moon:
        sentence = sentence.replace(LUNAR_GAP, (
            f"annual mean temperatures 2 cm under the surface of {moon['low']:.0f} to {moon['high']:.0f} C averaged "
            f"over each site, down to {moon['coldest']:.0f} C in the coldest spot (LRO Diviner Polar Resource "
            f"Product: model values, not measurements)"))
    return {"status": "filled from the moon cards" if moon else "placeholder: the lunar figure is not filled in",
            "moon_file": str(MOON), "moon_file_was_there_at_this_run": MOON.exists(),
            "earth_low_c": r1(min(means)) if means else None, "earth_high_c": r1(max(means)) if means else None,
            "lunar_mean_low_c": r1(moon["low"]) if moon else None,
            "lunar_mean_high_c": r1(moon["high"]) if moon else None,
            "lunar_coldest_c": r1(moon["coldest"]) if moon else None,
            "lunar_what": ("LRO Diviner annual mean temperature 2 cm under the surface (model-based): lowest and "
                           "highest of the area means of the lunar sites, and the coldest triangle of any site"),
            "sentence": sentence}


def read_moon_cards():
    """The lunar cards if the file is there and whole; None otherwise (the sentence then keeps its gap)."""
    try:
        return json.loads(MOON.read_text())
    except (OSError, ValueError):
        return None


def show(value) -> str:
    return "  n/a" if value is None else f"{value:5.1f}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--offline", action="store_true", help="make no request; fail if a raw regional answer is missing")
    parser.add_argument("--pause", type=float, default=0.6, help="seconds between two requests")
    parser.add_argument("--no-places", action="store_true", help="leave out the daily series of the named places")
    args = parser.parse_args()

    grazing = json.loads(CELLS.read_text())
    cells = grazing["cells"]
    points = temperature.points_of(cells)
    tiles = temperature.tiles_for_cells(cells)
    print(f"{len(cells)} cells at {len(points)} grid points of {temperature.GRID_LAT_DEG:g} x "
          f"{temperature.GRID_LON_DEG:g} degrees; {len(tiles)} blocks of {cloud.TILE_DEG} degrees x "
          f"{len(temperature.PARAMETERS)} parameters", flush=True)
    RAW.mkdir(parents=True, exist_ok=True)
    asked = fetch_all(tiles, args.offline, args.pause)
    print(f"regional requests made in this run: {asked}", flush=True)

    by_point = {parameter: temperature.read_raw(RAW, parameter, tiles) for parameter in temperature.PARAMETERS}
    elevations = {}
    for tile in tiles:
        elevations.update(temperature.read_elevations((RAW / cloud.raw_name("T2M", tile)).read_bytes()))
    names = {cloud.raw_name(parameter, tile) for parameter in temperature.PARAMETERS for tile in tiles}
    headers = {parameter: [cloud.answer_header((RAW / cloud.raw_name(parameter, tile)).read_bytes()) for tile in tiles]
               for parameter in temperature.PARAMETERS}
    missing = {parameter: [p for p in points if p not in by_point[parameter]] for parameter in temperature.PARAMETERS}
    for parameter, gone in missing.items():
        if gone:
            print(f"WARNING: the service returned no {parameter} for {len(gone)} grid points, first {gone[:5]}")

    table = temperature.cells_table(cells, by_point, elevations)
    counts = summary(cells, table)
    meta = temperature.meta_from(headers, fetched=fetched_span(names))

    places = []
    if not args.no_places:
        scored = {}
        if SCORED.exists():
            scored = {c["id"]: c for c in json.loads(SCORED.read_text())["cells"]}
        first = headers["T2M"][0]
        period = (first["start"], first["end"]) if first.get("start") and first.get("end") else None
        by_id = {c["id"]: c for c in cells}
        summer_south = grazing["meta"].get("summer_bins_south") or []
        for name, lat, lon in PLACES:
            places.append(place_report(name, lat, lon, by_id, scored, table, summer_south, period,
                                       args.offline, args.pause))

    meta.update({
        "null_rule": ("a row (t2m_c, t2m_max_c, t2m_min_c or ts_c) is null when no month has a value or the "
                      "service gave no such grid point; a single month without a value is null inside the list"),
        "cell_to_grid": ("the MERRA-2 grid point nearest to the cell centre (lat, lon of grazing_cells.json); "
                         "a centre half-way between two rows, as every centre at x.25 or x.75 degrees of "
                         "latitude is, goes to the row to the north"),
        "by_bin_rule": ("temperature.by_bin(row) gives 36 ten-day values, each bin taking the month of its "
                        "middle day (bin // 3); bin = min((day_of_year - 1) // 10, 35)"),
        "request_rules_followed": ("one parameter and at most 10 x 10 degrees per regional request, one request "
                                   "at a time with a pause, no key, no login, wait and try again on answer 429"),
        "raw_answers": {"folder": str(RAW), "files": len(names),
                        "grid_points_missing_by_parameter": {p: len(gone) for p, gone in missing.items()}},
        "cells_source": str(CELLS),
        "written": now_utc(),
        "counts": counts,
        "named_places": {
            "what": ("for six named places: the cell that holds the place, its best ten-day bins by target, and "
                     "the temperature in them, both from the month's climatology (as in `cells`) and from the "
                     "daily series of the same grid point averaged over the days of that ten-day bin in all "
                     "years (t2m_daily_max_c and t2m_daily_min_c there are mean daily maximum and minimum)"),
            "daily_url_pattern": temperature.DAILY_URL_PATTERN,
            "extremes_check_all_places": extremes_check_all(places),
            "extremes_check_meaning": ("the climatology's T2M_MAX and T2M_MIN of each calendar month against the "
                                       "daily series of the same grid point: in how many months they equal the "
                                       "highest or lowest day of all years, the largest gap to it, and how far "
                                       "they lie from the mean daily maximum or minimum"),
            "places": places,
        } if not args.no_places else None,
        "years_fit": years_fit_all(places, meta["period"]),
        "period_note": ("`period` is what the service's answers name. Whether the values cover it is checked in "
                        "`years_fit` against the daily series of the named places (null without them)."),
        "lunar_comparison": lunar_placeholder(places, read_moon_cards()),
    })
    write_json(OUT, {"meta": meta, "cells": table})

    print(f"wrote {OUT}: {counts['cells']} cells, {counts['grid_points']} grid points")
    print(json.dumps({k: v for k, v in counts.items() if k not in ("north_cells", "south_cells")}, indent=1))
    for half, months in (("north_cells", ("july", "august")), ("south_cells", ("december", "january"))):
        for month in months:
            for field in temperature.FIELDS:
                print(f"{half} {month:9s} {field:10s} {json.dumps(counts[half][month][field])}")
    print(f"period {meta['period']}; fetched {meta['fetched']}")
    print(f"source: {meta['source']}")
    for place in places:
        print(f"\n{place['name']} ({place['lat']}, {place['lon']}): cell {place['cell']}", end="")
        if "note" in place:
            print(f"; {place['note']}")
            continue
        print(f", grid point {place['grid']} at {place['grid_elev_m']} m; best bins from {place['best_bins_source']}")
        record = table[place["cell"]]
        for field in temperature.FIELDS:
            print(f"  {field:10s} " + (" ".join(show(v) for v in record[field]) if record[field] else "null"))
        if place["extremes_check"]:
            print(f"  extremes check: {json.dumps(place['extremes_check'])}")
        for target, listed in place["best_bins_by_target"].items():
            parts = []
            for entry in listed:
                daily = entry.get("ten_day_mean_of_daily_series")
                clim = entry["month_climatology"]
                text = (f"mean {show(daily['t2m_c']).strip()}, daily max {show(daily['t2m_daily_max_c']).strip()}, "
                        f"daily min {show(daily['t2m_daily_min_c']).strip()}, skin {show(daily['ts_c']).strip()}"
                        if daily else f"month mean {show(clim['t2m_c']).strip()}")
                parts.append(f"{entry['dates']} ({entry['hours']} h): {text}")
            print(f"  {target:17s} " + ("; ".join(parts) if parts else "no long window"))
    if places:
        print(f"\nextremes check, all places: {json.dumps(meta['named_places']['extremes_check_all_places'])}")
    fit = meta["years_fit"]
    if fit:
        print(f"years the climatology's values fit: {fit['years_the_values_fit']} "
              f"({fit['months_equal_over_the_years_that_fit']} of {fit['months_compared']} monthly extremes equal; "
              f"{fit['months_equal_over_the_period_named']} of {fit['months_compared']} over the period the service "
              f"names, {fit['period_named_by_the_service']})")
    print("\n" + meta["lunar_comparison"]["sentence"])


if __name__ == "__main__":
    main()

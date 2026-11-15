# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Check the satellite snow layer against many weather stations, year-round, then see how far the headline counts could move.

Stations come from NOAA GHCN-Daily (snow depth, element SNWD). A station is kept only
if its record can stand for a snow-free share; see twinfinder/station_select.py.
Bias is always satellite minus station, so a negative bias means the satellite layer
shows more snow than the station does.

The comparison runs in the 36 calendar ten-day bins of the snow layer over ten snow
years (1 October 2015 to 30 September 2025). A station is still judged on its winter
halves; its share then comes from the whole snow years of its well-reported winters,
and a bin is compared only where the station reported on 80% of the bin's days.
Results are given for the whole year, the winter half, the summer half and for May to
August north of 66N, each with the stale-flag rule (the project's odds) and as mapped.

Run from the project root: uv run python scripts/validate_snow_many.py [--offline]
--offline never downloads: a station whose file is not in data/raw/ghcn is listed as such.
"""
import argparse
import json
import urllib.error
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

from twinfinder import grazing, score, snow, stations
from twinfinder import station_select as sel
from twinfinder.fetch import fetch

DERIVED = Path("data/derived")
GHCN_DIR = Path("data/raw/ghcn")
OUT = DERIVED / "snow_validation_many.json"
FIRST_WINTER, LAST_WINTER = 2015, 2024    # snow years named by their October: the same ten as the satellite maps
MIN_LAT = 59.0
SEED = 2026
PARALLEL = 6                              # connections to the one host
# Kept stations wanted per region. Regions not listed are so thin that every candidate is examined.
# Russia and Finland ran out of candidates with almost nothing kept, so the other large regions carry more.
QUOTAS = {"Norway (mainland)": 40, "Sweden": 15, "Finland": 12, "Russia": 30, "Alaska": 40, "Canada": 40}
THIN_REGIONS = (sel.ARCTIC_ISLANDS, "Iceland", "Greenland")
SCANDINAVIA = ("Norway (mainland)", "Sweden", "Finland")
REGION_ORDER = ["Norway (mainland)", "Sweden", "Finland", "Russia", "Alaska", "Canada",
                sel.ARCTIC_ISLANDS, "Iceland", "Greenland", "Other"]
# Three guards beyond the rule as first written, each prompted by stations that slipped through it:
# 1. A stray snow report is not enough. Jan Mayen: zero on 890 winter days, above zero on one; the next
#    lowest kept station has over 100 days above zero.
MIN_SNOW_REPORTS = 10
# 2. Bare ground after a cold, wet week is not credible (sel.cold_wet_days). Jan Mayen reports it on 16 of
#    16 such days and Kugaaruk, a faulty automatic sensor at 68.5N, on 21 of 50; credible stations on under 5%.
MIN_COLD_WET_DAYS, MAX_COLD_WET_BARE = 10, 0.2
# 3. A ten-day bin is compared only if the station reported on 80% of its days (sel.complete_bins). Novy-Port
#    and many Canadian automatic stations skip snow depth on bare days in autumn: 1 and 7 reports in the
#    first two October bins of six winters at Novy-Port. The same guard drops the summer bins of stations
#    that stop writing snow depth down once the ground is bare.
ALWAYS_SNOW = "never zero in winter, zero at other times of year"
NO_SATELLITE = "no satellite land pixel within 6 km of the station"
NO_COMPLETE_BIN = "no ten-day bin reported on 80% of its days"
NOT_CREDIBLE = "bare ground reported after cold, wet weeks"
NOT_ON_DISK = "station file not on disk (offline run, nothing downloaded)"
MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MONTH_BINS = {name: [3 * i, 3 * i + 1, 3 * i + 2] for i, name in enumerate(MONTH_NAMES)}   # three calendar bins each
MIDWINTER_BINS = [33, 34, 35, 0, 1, 2, 3, 4, 5]   # 27 November to 1 March
NORTH_LAT = 66.0                          # the new findings lean on May to August north of here
# name: (what, bins, lowest station latitude or None)
PERIODS = {
    "whole_year": ("all 36 bins", list(range(snow.N_BINS)), None),
    "winter_half": ("winter half", stations.WINTER_HALF_BINS, None),
    "summer_half": ("summer half", stations.SUMMER_HALF_BINS, None),
    "may_to_august": ("May to August", stations.MAY_TO_AUGUST_BINS, None),
    "may_to_august_north_of_66": ("May to August, stations at or north of 66N", stations.MAY_TO_AUGUST_BINS, NORTH_LAT),
    "winter_half_north_of_66": ("winter half, stations at or north of 66N", stations.WINTER_HALF_BINS, NORTH_LAT),
    "summer_half_north_of_66": ("summer half, stations at or north of 66N", stations.SUMMER_HALF_BINS, NORTH_LAT),
}
PRINTED_PERIODS = ("winter_half", "summer_half", "may_to_august_north_of_66")
VERSIONS = {"with_stale_flag_rule": "satellite", "as_mapped": "satellite_as_mapped"}
LAT_BANDS = [(59.0, 62.0), (62.0, 66.0), (66.0, 70.0), (70.0, 75.0), (75.0, 90.0)]
ASSUMED_REGIONS = ("Iceland", "Greenland")   # no trustworthy station; read under an assumption, kept out of all statistics
MIN_REPORTS_ASSUMED = 30
HOURS_THRESHOLDS = (score.FULL_HOURS / 2, score.FULL_HOURS, score.FULL_HOURS * 2)   # long-window snow-free hours a year


def nullable(values) -> list:
    return [None if not np.isfinite(v) else round(float(v), 4) for v in values]


def examine(station: dict, layers: dict, row0: int, col0: int, offline: bool = False) -> dict:
    """Read one station (downloaded once, then cached) and decide whether its snow depth can be trusted.

    layers holds the satellite odds with the stale-flag rule ("satellite") and without it
    ("satellite_as_mapped", or None when the archive has none). The verdict uses the first only.
    """
    result = {key: station[key] for key in ("id", "name", "lat", "lon", "elevation_m", "region", "supplementary")}
    result.update(keep=False, as_written=False, always_snow=False)
    if offline and not (GHCN_DIR / f"{station['id']}.csv").exists():
        return {**result, "reason": NOT_ON_DISK}
    try:
        text = fetch(stations.station_url(station["id"]), GHCN_DIR).read_text()
    except urllib.error.HTTPError as error:
        return {**result, "reason": f"download failed (HTTP {error.code})"}
    except (urllib.error.URLError, ConnectionError, TimeoutError) as error:
        return {**result, "reason": f"download failed ({type(error).__name__})"}
    records, flagged = sel.parse_snow_depth(text)
    verdict = sel.assess(records, FIRST_WINTER, LAST_WINTER, min_snow_reports=MIN_SNOW_REPORTS)
    as_written = sel.assess(records, FIRST_WINTER, LAST_WINTER)["keep"]   # the rule without the three guards
    good = verdict["good_winters"]
    result.update(keep=verdict["keep"], reason=verdict["reason"], good_winters=len(good), flagged_reports=flagged)
    if not (as_written or verdict["reason"] == ALWAYS_SNOW):
        return result
    # The whole snow years of the well-reported winters, summer included; only bins reported on 80% of their days.
    share_any, counts = stations.snow_free_by_bin(verdict["year_records"], FIRST_WINTER, LAST_WINTER)
    possible = stations.days_per_bin(good)
    share = np.where(sel.complete_bins(counts, possible), share_any, np.nan)
    share_all_years, _ = stations.snow_free_by_bin(records, FIRST_WINTER, LAST_WINTER)
    lat, lon = station["lat"], station["lon"]
    satellite = snow.cell_probabilities(layers["satellite"], row0, col0, lat, lon)
    as_mapped = (np.full(snow.N_BINS, np.nan) if layers["satellite_as_mapped"] is None
                 else snow.cell_probabilities(layers["satellite_as_mapped"], row0, col0, lat, lon))
    result.update(
        winter_coverage=round(float(np.mean([verdict["coverage"][w] for w in good])), 4),
        land_pixels=snow.cell_land_pixels(layers["satellite"], row0, col0, lat, lon),
        stuck_winters=snow.cell_stuck_winters(layers["stuck_winters"], row0, col0, lat, lon),
        satellite=satellite, satellite_as_mapped=as_mapped, station_share=share, station_share_any=share_any,
        reports=counts, possible_days=possible, station_share_all_years=share_all_years)
    if not np.isfinite(satellite).any():
        return {**result, "keep": False, "reason": NO_SATELLITE}
    tested, bare = sel.cold_wet_days(verdict["records"], sel.parse_weather(text), good)
    result.update(cold_wet_days=tested, cold_wet_days_reported_bare=bare)
    if result["keep"] and tested >= MIN_COLD_WET_DAYS and bare > MAX_COLD_WET_BARE * tested:
        result.update(keep=False, reason=NOT_CREDIBLE)
    if result["keep"] and not (np.isfinite(satellite) & np.isfinite(share)).any():
        result.update(keep=False, reason=NO_COMPLETE_BIN)
    result.update(as_written=as_written, always_snow=verdict["reason"] == ALWAYS_SNOW)
    return result


def select_stations(pools: dict, layers: dict, row0, col0, offline: bool) -> list[dict]:
    """Work through each region's queue in rounds until its quota of kept stations is met or it runs out."""
    position, kept, examined = Counter(), Counter(), []
    with ThreadPoolExecutor(PARALLEL) as pool:
        while True:
            batch = []
            for region, queue in pools.items():
                need = QUOTAS.get(region, len(queue)) - kept[region]
                take = queue[position[region]:position[region] + max(need, 0)]
                position[region] += len(take)
                batch += take
            if not batch:
                return examined
            for result in pool.map(lambda s: examine(s, layers, row0, col0, offline), batch):
                kept[result["region"]] += result["keep"]
                examined.append(result)
            print(f"  examined {len(examined):4d} stations, kept {sum(kept.values()):4d}", flush=True)


def stack(rows: list[dict], key: str) -> np.ndarray:
    return np.array([row[key] for row in rows], dtype=float).reshape(len(rows), snow.N_DEKADS)


def compare(rows: list[dict], bins, satellite_key: str = "satellite", station_key: str = "station_share",
            calibration: bool = True) -> dict:
    """Satellite against station over some bins: stations with a compared bin, station-bins, differences.

    "stations" counts only stations with at least one bin where both exist. The median is
    given two ways: over station-bins, and over the stations' own mean differences.
    """
    satellite, station = stack(rows, satellite_key)[:, bins], stack(rows, station_key)[:, bins]
    compared = np.isfinite(satellite - station).any(axis=1) if len(rows) else np.zeros(0, dtype=bool)
    per_station = sel.station_biases(satellite, station) if len(rows) else np.zeros(0)
    out = {"stations": int(compared.sum()), **sel.summarise(satellite, station),
           "median_of_station_means": float(np.median(per_station)) if per_station.size else None}
    if compared.sum() >= 10:   # an interval from fewer stations would mean little
        out["mean_bias_95_interval"] = [round(v, 4) for v in sel.resampled_bias_interval(
            satellite[compared], station[compared], SEED)]
    if calibration:
        out["calibration"] = sel.calibration_table(satellite, station)
    return out


def period_results(kept: list[dict], always_snow: list[dict]) -> dict:
    """The comparison for each part of the year and each version of the satellite odds."""
    out = {}
    for name, (what, bins, min_lat) in PERIODS.items():
        chosen = [r for r in kept if min_lat is None or r["lat"] >= min_lat]
        added = [r for r in always_snow if min_lat is None or r["lat"] >= min_lat]
        out[name] = {
            "what": what, "bins": bins, "days": stations.bin_span(bins), "min_lat": min_lat,
            "stations_in_group": len(chosen),
            **{version: compare(chosen, bins, key) for version, key in VERSIONS.items()},
            "with_stations_under_snow_all_winter_added": {
                "stations_added": [f"{r['id']} {r['name']}" for r in added],
                **{version: compare(chosen + added, bins, key) for version, key in VERSIONS.items()}}}
    return out


def group_rows(rows: list[dict]) -> list[dict]:
    """Bias (with the stale-flag rule) by region, by region and half-year, by land pixels, and by month."""
    out = []

    def add(label: str, chosen: list[dict], bins=slice(None)) -> None:
        result = compare(chosen, bins, calibration=False)
        as_mapped = compare(chosen, bins, "satellite_as_mapped", calibration=False)
        out.append({"group": label, "stations_in_group": len(chosen), **result,
                    "mean_bias_as_mapped": as_mapped["mean_bias"]})

    for region in REGION_ORDER:
        add(f"region: {region}", [r for r in rows if r["region"] == region])
    add("region: Scandinavia combined (Norway + Sweden + Finland, already counted above)",
        [r for r in rows if r["region"] in SCANDINAVIA])
    for half, bins in (("winter half", stations.WINTER_HALF_BINS), ("summer half", stations.SUMMER_HALF_BINS)):
        for region in REGION_ORDER:
            add(f"{half}, region: {region}", [r for r in rows if r["region"] == region], bins)
    add("land pixels around station: under 7 of 9", [r for r in rows if r["land_pixels"] < 7])
    add("land pixels around station: 7 to 9 of 9", [r for r in rows if r["land_pixels"] >= 7])
    add("stations with a stuck winter in their 3 x 3 block", [r for r in rows if r["stuck_winters"] >= 1])
    for month, bins in MONTH_BINS.items():
        add(f"month: {month} ({stations.bin_span(bins)})", rows, bins)
    for low, high in LAT_BANDS:
        add(f"latitude: {low:.0f} to {high:.0f}N", [r for r in rows if low <= r["lat"] < high])
    return out


def north_of_66(pools: dict, examined: list[dict], kept: list[dict], always_snow: list[dict]) -> dict:
    """Where the stations at or north of 66N are, by country, and where there are none."""
    bins = stations.MAY_TO_AUGUST_BINS

    def summer_bins(row: dict) -> int:
        return int((np.isfinite(row["satellite"]) & np.isfinite(row["station_share"]))[bins].sum())

    by_region = {}
    for region in REGION_ORDER:
        north = lambda rows: [r for r in rows if r["region"] == region and r["lat"] >= NORTH_LAT]
        mine = north(kept)
        by_region[region] = {
            "candidates": len(north(pools[region])), "examined": len(north(examined)), "kept": len(mine),
            "kept_with_a_may_to_august_bin": sum(summer_bins(r) > 0 for r in mine),
            "under_snow_all_winter_not_kept": len(north(always_snow)),
            "rejected": dict(Counter(r["reason"] for r in north(examined) if not r["keep"]))}
    north_kept = sorted((r for r in kept if r["lat"] >= NORTH_LAT), key=lambda r: -r["lat"])
    return {
        "min_lat": NORTH_LAT, "kept": len(north_kept),
        "kept_with_a_may_to_august_bin": sum(summer_bins(r) > 0 for r in north_kept),
        "by_region": by_region,
        "regions_without_a_kept_station": [region for region, row in by_region.items() if row["kept"] == 0],
        "kept_by_latitude_band": {f"{low:.0f} to {high:.0f}N": sum(low <= r["lat"] < high for r in kept)
                                  for low, high in LAT_BANDS},
        "stations": [{"id": r["id"], "name": r["name"], "lat": r["lat"], "lon": r["lon"], "region": r["region"],
                      "elevation_m": r["elevation_m"], "land_pixels": r["land_pixels"],
                      "may_to_august_bins_compared": summer_bins(r),
                      **{f"may_to_august_mean_bias_{version}": sel.summarise(r[key][bins], r["station_share"][bins])["mean_bias"]
                         for version, key in VERSIONS.items()}} for r in north_kept],
        "under_snow_all_winter_not_kept": [f"{r['id']} {r['name']} ({r['lat']:.2f}N, {r['region']})"
                                           for r in always_snow if r["lat"] >= NORTH_LAT]}


def assumed_bare(station: dict, probabilities, row0, col0, offline: bool = False) -> dict | None:
    """A station that reports snow depth on snow days only, read as bare on its other reporting days.

    The assumption is made for the winter half only (1 October to 31 March), so only
    bins that lie wholly inside it are compared: 8 October to 31 March.
    """
    if offline and not (GHCN_DIR / f"{station['id']}.csv").exists():
        return None
    text = fetch(stations.station_url(station["id"]), GHCN_DIR).read_text()
    records, _ = sel.parse_snow_depth(text)
    filled, winters = sel.unreported_as_bare(records, sel.parse_observed_days(text), FIRST_WINTER, LAST_WINTER,
                                             MIN_REPORTS_ASSUMED)
    share, _ = stations.snow_free_by_bin(filled, FIRST_WINTER, LAST_WINTER, half="winter")
    all_years = range(FIRST_WINTER, LAST_WINTER + 1)
    inside_winter = stations.days_per_bin(all_years, half="winter") == stations.days_per_bin(all_years)
    share = np.where(inside_winter, share, np.nan)
    satellite = snow.cell_probabilities(probabilities, row0, col0, station["lat"], station["lon"])
    return {"id": station["id"], "name": station["name"], "lat": station["lat"], "lon": station["lon"],
            "region": station["region"], "winters_used": winters,
            "snow_depth_reports_per_winter_used": round(sum(d > 0 for _, d in filled) / len(winters), 1) if winters else None,
            "land_pixels": snow.cell_land_pixels(probabilities, row0, col0, station["lat"], station["lon"]),
            "satellite": nullable(satellite), "assumed_station_share": nullable(share),
            **{k: v for k, v in sel.summarise(satellite, share).items() if k != "n"},
            "mean_bias_27_nov_to_1_mar": sel.summarise(satellite[MIDWINTER_BINS], share[MIDWINTER_BINS])["mean_bias"]}


def long_flat_by_bin(bins, rows, stretch_min_h: float) -> np.ndarray:
    """Flat-horizon long-window hours per ten-day bin for the chosen rows, [cells, targets, bins].

    Version 3 archives hold them (long_flat: the time inside per-day spells of at least the minimum).
    A version 2 archive has only the hours and the median longest stretch per bin; there a bin counts whole.
    """
    if "long_flat" in getattr(bins, "files", bins):
        return bins["long_flat"][rows].astype(float)
    return np.where(bins["stretch"][rows] >= stretch_min_h, bins["flat"][rows].astype(float), 0.0)


def stored_with_rule(target_values: dict) -> float:
    """A cell's stored long-window snow-free hours under the stale-flag rule (NaN if unknown).

    Since version 3 a measured cell's main figure uses the maps as they read, and the figure
    with the rule is kept beside it; a version 2 record has only the main figure, made with the rule.
    """
    value = target_values.get("long_snow_free_hours_with_rule", target_values["long_snow_free_hours"])
    return float("nan") if value is None else float(value)


def headline_counts(tables: dict, archive) -> dict:
    """Cells with at least so many long-window snow-free hours per target, under each treatment of the snow odds.

    Works from the grazing files: the flat-horizon long-window hours per ten-day bin
    (grazing_bins.npz) and the measured northern cells (grazing_cells.json).
    The "as is" treatment (odds with the stale-flag rule) must reproduce the stored
    long_snow_free_hours_with_rule; the main figure of a measured cell is "as_mapped".
    """
    cells_path, bins_path = DERIVED / "grazing_cells.json", DERIVED / "grazing_bins.npz"
    if not (cells_path.exists() and bins_path.exists()):
        return {"skipped": "grazing_cells.json or grazing_bins.npz not found; run scripts/build_grazing_cells.py"}
    stored, bins = json.loads(cells_path.read_text()), np.load(bins_path)
    targets = stored["meta"]["targets"]
    if [t["id"] for t in targets] != [str(t) for t in bins["targets"]]:
        return {"skipped": "grazing_cells.json and grazing_bins.npz list different targets"}
    position = {str(cell_id): i for i, cell_id in enumerate(bins["ids"])}
    cells = [c for c in stored["cells"] if c["hemisphere"] == "N" and c["gridded"]
             and c["snow"]["status"] == "measured" and c["id"] in position]
    rows = np.array([position[c["id"]] for c in cells])
    long_flat = long_flat_by_bin(bins, rows, stored["meta"]["stretch_min_h"])   # [cells, targets, bins]
    row0, col0 = int(archive["row0"]), int(archive["col0"])

    def odds_of(layer) -> np.ndarray:
        return np.array([snow.cell_probabilities_filled(layer, row0, col0, c["lat"], c["lon"])[0] for c in cells])

    odds = odds_of(archive["probabilities"])
    treated = {"as_is": odds, "doubled_capped": sel.doubled(odds),
               **{name: sel.calibrate(odds, table) for name, table in tables.items()}}
    if "probabilities_as_mapped" in archive.files:
        treated["as_mapped"] = odds_of(archive["probabilities_as_mapped"])
    hours = {name: grazing.total(grazing.snow_free_hours(long_flat, values[:, None, :]))
             for name, values in treated.items()}                             # [cells, targets]
    before = np.array([[stored_with_rule(c["targets"][t["id"]]) for t in targets] for c in cells])
    now = hours["as_is"]
    differ = (np.isfinite(before) != np.isfinite(now)) | (np.abs(before - now) > 0.051)
    region_of = [c["region"] for c in cells]
    out = {"measure": "long-window snow-free hours a year over a flat horizon (grazing_cells.json): hours with the "
                      f"Sun in the target's band inside spells of at least {stored['meta']['stretch_min_h']} h "
                      f"({stored['meta'].get('long_rule', 'whole ten-day bins by their median longest stretch')}), "
                      "times the snow-free odds",
           "cells": "northern gridded cells with snow status 'measured'", "n_cells": len(cells),
           "as_is_values_differing_from_grazing_cells_json": int(differ.sum()),
           "targets": [{"id": t["id"], "name": t["name"], "limit_deg": t["limit_deg"]} for t in targets],
           "treatments": {
               "as_is": "satellite odds with the stale-flag rule, unchanged (reproduces long_snow_free_hours_with_rule "
                        "of grazing_cells.json)",
               "as_mapped": "satellite odds without the stale-flag rule (the main figure of a measured cell since version 3)",
               "calibrated": "each ten-day probability replaced by the station share on straight lines through "
                             "the year-round calibration table's points (mean satellite value, mean station "
                             "share), flat beyond the first and last point",
               "doubled_capped": "upper bound: each ten-day probability doubled and capped at 1"},
           "thresholds_hours": list(HOURS_THRESHOLDS), "counts": {}, "regions_at_full_hours": {}}
    for name, values in hours.items():
        out["counts"][name] = {t["id"]: {f"at_least_{n:.0f}": sel.count_at_least(
            [None if not np.isfinite(v) else v for v in values[:, k]], n) for n in HOURS_THRESHOLDS}
            for k, t in enumerate(targets)}
        out["regions_at_full_hours"][name] = {
            t["id"]: dict(Counter(region for region, v in zip(region_of, values[:, k])
                                  if np.isfinite(v) and v >= score.FULL_HOURS).most_common())
            for k, t in enumerate(targets)}
    return out


def print_period(name: str, period: dict) -> None:
    """One part of the year: both versions of the satellite odds, then both calibration tables side by side."""
    print(f"\n{period['what']} ({period['days']}); kept stations in the group: {period['stations_in_group']}")
    for version in VERSIONS:
        r = period[version]
        if not r["n"]:
            print(f"  {version:21s} no station-bin to compare")
            continue
        interval = ("  95% interval {:+.3f} to {:+.3f}".format(*r["mean_bias_95_interval"])
                    if "mean_bias_95_interval" in r else "")
        print(f"  {version:21s} stations {r['stations']:3d}  station-bins {r['n']:5d}  mean {r['mean_bias']:+.3f}  "
              f"median {r['median_bias']:+.3f}  median of station means {r['median_of_station_means']:+.3f}  "
              f"mean absolute {r['mean_abs_difference']:.3f}{interval}")
    added = period["with_stations_under_snow_all_winter_added"]
    if added["stations_added"] and added["with_stale_flag_rule"]["n"]:
        r = added["with_stale_flag_rule"]
        print(f"  with the {len(added['stations_added'])} stations under snow all winter added: stations "
              f"{r['stations']}, station-bins {r['n']}, mean {r['mean_bias']:+.3f}, median {r['median_bias']:+.3f}")
    print("  satellite band | with the rule: bins, mean satellite, mean station | as mapped: bins, mean satellite, mean station")
    for with_rule, mapped in zip(period["with_stale_flag_rule"].get("calibration", []),
                                 period["as_mapped"].get("calibration", [])):
        closing = "]" if with_rule["ims_high"] == 1.0 else ")"
        cells = ["      -        -        -" if not row["n_station_bins"] else
                 f"{row['n_station_bins']:7d}  {row['mean_ims']:7.3f}  {row['mean_station_snow_free']:7.3f}"
                 for row in (with_rule, mapped)]
        print(f"    [{with_rule['ims_low']:.1f}, {with_rule['ims_high']:.1f}{closing}   | {cells[0]}   | {cells[1]}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--offline", action="store_true", help="never download; list stations whose file is missing")
    offline = parser.parse_args().offline
    archive = np.load(DERIVED / "snow_free_dekads.npz")
    probabilities, row0, col0 = archive["probabilities"], int(archive["row0"]), int(archive["col0"])
    layers = {"satellite": probabilities, "stuck_winters": archive["stuck_winters"],
              "satellite_as_mapped": archive["probabilities_as_mapped"]
              if "probabilities_as_mapped" in archive.files else None}
    listed = sel.parse_stations((GHCN_DIR / "ghcnd-stations.txt").read_text())
    inventory = sel.parse_inventory((GHCN_DIR / "ghcnd-inventory.txt").read_text())

    strict = sel.candidates(listed, inventory, MIN_LAT, FIRST_WINTER, LAST_WINTER)
    # Thin regions also get stations whose inventory merely overlaps the period enough to hold five winters.
    loose = sel.candidates(listed, inventory, MIN_LAT, FIRST_WINTER + 5, LAST_WINTER - 4)
    strict_ids = {s["id"] for s in strict}
    pools = {region: [] for region in REGION_ORDER}
    for station in loose:
        station["region"] = sel.region_group(station["id"], station["lat"], station["lon"])
        station["supplementary"] = station["id"] not in strict_ids
        if not station["supplementary"] or station["region"] in THIN_REGIONS:
            pools[station["region"]].append(station)
    pools = {region: sel.spread_order(queue, seed=SEED) for region, queue in pools.items()}
    supplementary = sum(s["supplementary"] for queue in pools.values() for s in queue)
    print(f"stations at or north of {MIN_LAT:.0f}N with snow depth in the inventory from {FIRST_WINTER} to "
          f"{LAST_WINTER}: {len(strict)}; added in thin regions on a looser inventory rule: {supplementary}")

    examined = select_stations(pools, layers, row0, col0, offline)
    kept = [r for r in examined if r["keep"]]
    as_written = [r for r in examined if r["as_written"]]
    always_snow = [r for r in examined if r["always_snow"]]
    reasons = Counter(r["reason"] for r in examined)

    print(f"\nexamined {len(examined)}, kept {len(kept)}")
    for reason, n in reasons.most_common():
        print(f"  {n:4d}  {reason}")
    print(f"\n{'region':38s} candidates examined kept")
    selection_by_region = {}
    for region in REGION_ORDER:
        mine = [r for r in examined if r["region"] == region]
        selection_by_region[region] = {
            "candidates": len(pools[region]), "examined": len(mine), "kept": sum(r["keep"] for r in mine),
            "rejected": dict(Counter(r["reason"] for r in mine if not r["keep"]))}
        print(f"{region:38s} {len(pools[region]):10d} {len(mine):8d} {sum(r['keep'] for r in mine):4d}")

    satellite, station = stack(kept, "satellite"), stack(kept, "station_share")
    periods = period_results(kept, always_snow)
    overall = {k: v for k, v in periods["whole_year"]["with_stale_flag_rule"].items() if k != "calibration"}
    table = periods["whole_year"]["with_stale_flag_rule"]["calibration"]
    groups = group_rows(kept)
    north = north_of_66(pools, examined, kept, always_snow)
    for row in kept:
        row.update({k: v for k, v in sel.summarise(row["satellite"], row["station_share"]).items() if k != "n"})
        row["bins_compared"] = int((np.isfinite(row["satellite"]) & np.isfinite(row["station_share"])).sum())
    station_bias = np.array([row["mean_bias"] for row in kept])

    # The same comparison under other reasonable choices, to see whether the answer depends on them.
    coastal = [r for r in kept if r["land_pixels"] < 7]
    with_always = kept + always_snow
    exactly_zero = np.round(satellite, 6) == 0.0
    both = np.isfinite(satellite) & np.isfinite(station)
    kept_ids = {r["id"] for r in kept}
    stricter = np.array([np.where(sel.complete_bins(r["reports"], r["possible_days"], 0.95), r["station_share_any"], np.nan)
                         for r in kept])
    tested = [r for r in kept if r["cold_wet_days"] >= MIN_COLD_WET_DAYS]
    checks = {
        "all_checks_cover": "the whole year (36 bins), satellite odds with the stale-flag rule",
        "rule_as_first_written_without_the_three_guards": {
            "what": "every examined station passing the 80%-of-days-in-5-winters and zero-and-non-zero rule, "
                    "compared over every bin with any report",
            "stations": len(as_written),
            "stations_the_guards_remove": [f"{r['id']} {r['name']}" for r in as_written if r["id"] not in kept_ids],
            **sel.summarise(stack(as_written, "satellite"), stack(as_written, "station_share_any")),
            "calibration": sel.calibration_table(stack(as_written, "satellite"), stack(as_written, "station_share_any"))},
        "kept_stations_over_every_bin_with_any_report": sel.summarise(satellite, stack(kept, "station_share_any")),
        "kept_stations_only_bins_reported_on_95_percent_of_days": sel.summarise(satellite, stricter),
        "cold_wet_week_test": {
            "what": f"days ending a week with daily maximum below -1.0 C and at least 5 mm of precipitation; a "
                    f"station is dropped if it reports bare ground on over {MAX_COLD_WET_BARE:.0%} of at least "
                    f"{MIN_COLD_WET_DAYS} such days",
            "kept_stations_tested": len(tested), "kept_stations_untestable": len(kept) - len(tested),
            "highest_bare_share_among_kept": max((r["cold_wet_days_reported_bare"] / r["cold_wet_days"]
                                                  for r in tested), default=None)},
        "kept_stations_every_bin_all_ten_snow_years_not_only_well_reported_ones":
            sel.summarise(satellite, stack(kept, "station_share_all_years")),
        "with_stations_under_snow_all_winter_added": {
            "what": "stations with daily reports whose snow depth is never zero from October to March but is "
                    "zero in summer; the rule drops them although their winter snow-free share is a true zero",
            "stations_added": [f"{r['id']} {r['name']}" for r in always_snow],
            **sel.summarise(stack(with_always, "satellite"), stack(with_always, "station_share")),
            "calibration": sel.calibration_table(stack(with_always, "satellite"), stack(with_always, "station_share"))},
        "stations_with_under_7_land_pixels_only": {
            "stations": len(coastal),
            "calibration": sel.calibration_table(stack(coastal, "satellite"), stack(coastal, "station_share"))},
        "satellite_exactly_zero": {"n_station_bins": int((exactly_zero & both).sum()),
                                   "mean_station_snow_free": float(station[exactly_zero & both].mean())
                                   if (exactly_zero & both).any() else None},
        "satellite_above_zero_below_0.1": sel.calibration_table(
            np.where(exactly_zero, np.nan, satellite), station)[0],
        "per_station_mean_bias": {
            "median": float(np.median(station_bias)), "lowest": float(station_bias.min()),
            "highest": float(station_bias.max()),
            "stations_below_minus_0.1": int((station_bias < -0.1).sum()),
            "stations_within_0.1": int((np.abs(station_bias) <= 0.1).sum()),
            "stations_above_plus_0.1": int((station_bias > 0.1).sum())},
    }

    print(f"\nwhole year, satellite minus station over {overall['n']} station-bins at {len(kept)} stations: "
          f"mean {overall['mean_bias']:+.3f} (95% interval {overall['mean_bias_95_interval'][0]:+.3f} to "
          f"{overall['mean_bias_95_interval'][1]:+.3f}, resampling whole stations), median "
          f"{overall['median_bias']:+.3f}, mean absolute {overall['mean_abs_difference']:.3f}")
    for name in PRINTED_PERIODS:
        print_period(name, periods[name])

    print(f"\nkept stations at or north of {NORTH_LAT:.0f}N: {north['kept']} "
          f"({north['kept_with_a_may_to_august_bin']} with a May-to-August bin to compare)")
    print(f"  {'region':38s} candidates examined kept  with a May-Aug bin  under snow all winter (not kept)")
    for region, row in north["by_region"].items():
        print(f"  {region:38s} {row['candidates']:10d} {row['examined']:8d} {row['kept']:4d} "
              f"{row['kept_with_a_may_to_august_bin']:19d} {row['under_snow_all_winter_not_kept']:6d}")
    print(f"  no kept station at or north of {NORTH_LAT:.0f}N in: {', '.join(north['regions_without_a_kept_station'])}")
    print("  kept stations by latitude band: " + ", ".join(f"{k}: {v}" for k, v in north["kept_by_latitude_band"].items()))

    print(f"\n{'group (satellite with the stale-flag rule)':82s} stations  bins    bias  abs diff  as mapped  95% interval of bias")
    for g in groups:
        bias = "      -       -" if g["n"] == 0 else f"{g['mean_bias']:+7.3f} {g['mean_abs_difference']:7.3f}"
        mapped = "        -" if g["mean_bias_as_mapped"] is None else f"{g['mean_bias_as_mapped']:+9.3f}"
        interval = "  {:+.3f} to {:+.3f}".format(*g["mean_bias_95_interval"]) if "mean_bias_95_interval" in g else ""
        print(f"{g['group']:82s} {g['stations']:6d} {g['n']:6d} {bias}  {mapped}{interval}")
    print("\nwhole year: satellite snow-free probability | station-bins | mean satellite | mean station snow-free share")
    for row in table:
        closing = "]" if row["ims_high"] == 1.0 else ")"
        values = "      -        -" if not row["n_station_bins"] else \
            f"{row['mean_ims']:7.3f}  {row['mean_station_snow_free']:7.3f}"
        print(f"  [{row['ims_low']:.1f}, {row['ims_high']:.1f}{closing} {row['n_station_bins']:8d}   {values}")
    print("\nchecks:")
    for name, check in checks.items():
        if isinstance(check, str):
            print(f"  {name}: {check}")
            continue
        short = {k: (round(v, 4) if isinstance(v, float) else v) for k, v in check.items()
                 if k not in ("calibration", "what")}
        print(f"  {name}: {short}")
    print("\nstations whose mean bias is beyond 0.15 either way:")
    for row in sorted(kept, key=lambda r: r["mean_bias"]):
        if abs(row["mean_bias"]) > 0.15:
            print(f"  {row['id']} {row['name'][:26]:26s} {row['lat']:6.2f} {row['lon']:8.2f} {row['elevation_m']:5.0f} m"
                  f"  land pixels {row['land_pixels']}  bias {row['mean_bias']:+.2f}")

    assumed = [assumed_bare(s, probabilities, row0, col0, offline)
               for region in ASSUMED_REGIONS for s in sorted(pools[region], key=lambda s: s["id"])]
    assumed = [a for a in assumed if a is not None]
    print("\nNOT IN THE STATISTICS. Stations that report snow depth on snow days only, read as bare ground on "
          f"other reporting days, in winters with at least {MIN_REPORTS_ASSUMED} snow-depth reports "
          "(bins from 8 October to 31 March only):")
    for a in assumed:
        if a["mean_bias"] is None:
            print(f"  {a['id']} {a['name'][:16]:16s} no winter qualifies")
            continue
        midwinter = a["mean_bias_27_nov_to_1_mar"]
        print(f"  {a['id']} {a['name'][:16]:16s} winters {a['winters_used'][0]}-{a['winters_used'][-1]} "
              f"({len(a['winters_used'])}), snow days per winter {a['snow_depth_reports_per_winter_used']:5.1f}, "
              f"bias {a['mean_bias']:+.2f}, 27 Nov-1 Mar " + ("-" if midwinter is None else f"{midwinter:+.2f}"))

    headline = headline_counts({
        "calibrated": table,
        "calibrated_rule_as_first_written": checks["rule_as_first_written_without_the_three_guards"]["calibration"],
        "calibrated_with_always_snow_stations": checks["with_stations_under_snow_all_winter_added"]["calibration"],
        "calibrated_stations_with_under_7_land_pixels": checks["stations_with_under_7_land_pixels_only"]["calibration"]},
        archive)
    if "skipped" in headline:
        print(f"\nheadline counts skipped: {headline['skipped']}")
    else:
        print(f"\n{headline['cells']}: {headline['n_cells']}; recomputed long-window snow-free hours that differ "
              f"from grazing_cells.json: {headline['as_is_values_differing_from_grazing_cells_json']}")
        print(f"cells with at least {score.FULL_HOURS:.0f} long-window snow-free hours a year (flat horizon):")
        print(f"  {'treatment of the satellite snow odds':46s}" + "".join(f"{t['id']:>18s}" for t in headline["targets"]))
        for name, per_target in headline["counts"].items():
            print(f"  {name:46s}" + "".join(f"{per_target[t['id']][f'at_least_{score.FULL_HOURS:.0f}']:18d}"
                                            for t in headline["targets"]))

    def station_record(row: dict) -> dict:
        record = {k: row[k] for k in ("id", "name", "lat", "lon", "elevation_m", "region", "supplementary",
                                      "reason", "good_winters", "flagged_reports", "cold_wet_days",
                                      "cold_wet_days_reported_bare") if k in row}
        if "satellite" in row:
            record.update(land_pixels=row["land_pixels"], stuck_winters=row["stuck_winters"],
                          winter_coverage=row["winter_coverage"],
                          satellite=nullable(row["satellite"]), satellite_as_mapped=nullable(row["satellite_as_mapped"]),
                          station_share=nullable(row["station_share"]),
                          station_share_any_report=nullable(row["station_share_any"]),
                          reports=[int(n) for n in row["reports"]],
                          possible_days=[int(n) for n in row["possible_days"]])
        if "mean_bias" in row:
            record.update(mean_bias=row["mean_bias"], median_bias=row["median_bias"],
                          mean_abs_difference=row["mean_abs_difference"], bins_compared=row["bins_compared"])
        return record

    side = OUT.with_suffix(".part.json")
    side.write_text(json.dumps({
        "method": {
            "source": "NOAA GHCN-Daily snow depth (SNWD), per-station CSV files",
            "snow_years": [FIRST_WINTER, LAST_WINTER], "min_lat": MIN_LAT,
            "period": "ten snow years, 1 October 2015 to 30 September 2025; a snow year is named by its October",
            "bins": "36 calendar ten-day bins, bin 0 = 1 to 10 January, bin 35 = 17 to 31 December; a report is "
                    "binned by its own day of year, as the satellite maps are",
            "half_years": {"winter_half": f"bins 27 to 35 and 0 to 8 ({stations.bin_span(stations.WINTER_HALF_BINS)})",
                           "summer_half": f"bins 9 to 26 ({stations.bin_span(stations.SUMMER_HALF_BINS)})",
                           "may_to_august": f"bins 12 to 23 ({stations.bin_span(stations.MAY_TO_AUGUST_BINS)})"},
            "satellite_versions": {
                "with_stale_flag_rule": "key probabilities of snow_free_dekads.npz: the project's odds",
                "as_mapped": "key probabilities_as_mapped: the same maps without the stale-flag rule"},
            "offline_run": offline,
            "inventory_rule": f"SNWD first year <= {FIRST_WINTER} and last year >= {LAST_WINTER}; in "
                              f"{', '.join(THIN_REGIONS)} also first year <= {FIRST_WINTER + 5} and last year >= "
                              f"{LAST_WINTER - 4}",
            "trust_rule": f"snow depth on at least {sel.MIN_COVERAGE:.0%} of days (1 Oct to 31 Mar) in at least "
                          f"{sel.MIN_WINTERS} winters, with zero depths and at least {MIN_SNOW_REPORTS} non-zero "
                          "depths in those winters; not bare on over 20% of at least 10 days that end a cold, "
                          "wet week; reports that failed GHCN quality control are dropped; the station share "
                          "uses the whole snow years (1 Oct to 30 Sep) of the well-reported winters; a ten-day "
                          "bin is compared only if the station reported on 80% of the calendar days the bin "
                          "holds in those snow years (15 or 16 a year for the last bin)",
            "order": f"per region, turns between 5-degree latitude bands from the north, shuffled with seed {SEED}",
            "quotas_kept_per_region": QUOTAS,
            "bias": "satellite (IMS, mean of the 3 x 3 pixels around the station) minus station; negative means "
                    "the satellite layer shows more snow",
            "n": "station-bins: one station in one ten-day bin",
            "stations": "in a comparison: stations with at least one compared bin in that part of the year",
            "median_bias": "median over station-bins; median_of_station_means is the median of the stations' own "
                           "mean differences",
            "mean_bias_95_interval": "2.5th to 97.5th percentile of the mean bias over 4000 draws of whole "
                                     "stations with replacement",
        },
        "selection": {"candidates_inventory_rule": len(strict), "candidates_added_in_thin_regions": supplementary,
                      "examined": len(examined), "kept": len(kept),
                      "reasons": dict(reasons.most_common()), "by_region": selection_by_region},
        "overall": {"stations": len(kept), **overall},
        "periods": periods, "north_of_66": north,
        "by_group": groups, "calibration": table, "checks": checks, "headline": headline,
        "assumption_based_not_in_statistics": {
            "what": "stations that report snow depth on snow days only; days with a temperature or precipitation "
                    f"report but no snow depth are read as bare ground, in winters with at least "
                    f"{MIN_REPORTS_ASSUMED} snow-depth reports, over bins from 8 October to 31 March. An "
                    "assumption, not a measurement: it gives believable numbers in Iceland and plainly wrong "
                    "ones at Thule.",
            "stations": assumed},
        "stations": [station_record(r) for r in kept],
        "not_kept": [station_record(r) for r in examined if not r["keep"]],
    }, indent=1))
    side.rename(OUT)
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()

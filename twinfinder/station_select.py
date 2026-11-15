# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Pick weather stations whose snow depth can be trusted for a snow-free share, and compare them with the satellite snow layer.

Stations differ in practice: some write down snow depth every day, zeros included; some
only on days with snow; some rarely. Only the first kind gives a snow-free share.
Column positions follow the GHCN-Daily readme (sections IV and VII).

Dates are grouped as twinfinder/stations.py states it: a snow year runs from 1 October
to 30 September and is named by its October; its winter half is 1 October to 31 March.
A station is judged on its winter halves (that is where zeros and snow both occur); the
comparison with the satellite layer then runs over the whole snow years of the
well-reported winters, in the 36 calendar ten-day bins.
"""
from __future__ import annotations

import csv
import io
import math
import random
from collections import defaultdict
from datetime import date, timedelta

import numpy as np

from twinfinder import grazing, regions
from twinfinder.stations import snow_year_of, winter_half_of

MIN_COVERAGE = 0.8      # share of days from 1 October to 31 March that must carry a snow depth
MIN_WINTERS = 5         # winters that must reach that share
CALIBRATION_EDGES = (0.0, 0.1, 0.3, 0.5, 0.7, 0.9, 1.0)
COLD_WET_SPELL_DAYS = 7     # a week that never thaws ...
COLD_WET_MAX_TMAX = -10     # ... daily maximum below -1.0 C (tenths of a degree) ...
COLD_WET_MIN_PRECIP = 50    # ... with at least 5.0 mm of precipitation (tenths of a millimetre)
ARCTIC_ISLANDS = "Svalbard, Bear Island and Jan Mayen"
_ISLAND_BOXES = {"Svalbard", "Bear Island (Bjornoya)", "Jan Mayen"}
_COUNTRIES = {"NO": "Norway (mainland)", "SW": "Sweden", "FI": "Finland", "RS": "Russia",
              "US": "Alaska", "CA": "Canada", "IC": "Iceland", "GL": "Greenland"}


# --- station list and inventory ---------------------------------------------

def parse_stations(text: str) -> dict[str, dict]:
    """ghcnd-stations.txt: id (columns 1-11), latitude (13-20), longitude (22-30), elevation (32-37), name (42-71)."""
    stations = {}
    for line in text.splitlines():
        if len(line) < 37:
            continue
        stations[line[0:11]] = {"lat": float(line[12:20]), "lon": float(line[21:30]),
                                "elevation_m": float(line[31:37]), "name": line[41:71].strip()}
    return stations


def parse_inventory(text: str, element: str = "SNWD") -> dict[str, tuple[int, int]]:
    """ghcnd-inventory.txt: first and last year of one element (columns 32-35, 37-40, 42-45) per station."""
    years = {}
    for line in text.splitlines():
        if line[31:35] == element:
            years[line[0:11]] = (int(line[36:40]), int(line[41:45]))
    return years


def candidates(stations: dict, inventory: dict, min_lat: float = 59.0,
               first_year: int = 2015, last_year: int = 2024) -> list[dict]:
    """Stations at or north of min_lat whose inventory spans first_year to last_year, in id order."""
    found = []
    for station_id in sorted(stations):
        station = stations[station_id]
        if station["lat"] < min_lat or station_id not in inventory:
            continue
        first, last = inventory[station_id]
        if first <= first_year and last >= last_year:
            found.append({"id": station_id, **station, "first_year": first, "last_year": last})
    return found


def region_group(station_id: str, lat: float, lon: float) -> str:
    """Region for the comparison tables: the id's country code, except on the Arctic islands."""
    if regions.region(lat, lon) in _ISLAND_BOXES:
        return ARCTIC_ISLANDS
    return _COUNTRIES.get(station_id[:2], "Other")


def spread_order(stations: list[dict], seed: int = 0, band_deg: float = 5.0) -> list[dict]:
    """A repeatable order that takes turns between latitude bands, north first, shuffled within a band.

    Stations cluster in the south of every region; taking turns stops the first few
    dozen examined from all sitting near 60N.
    """
    bands = defaultdict(list)
    for station in sorted(stations, key=lambda s: s["id"]):
        bands[math.floor(station["lat"] / band_deg)].append(station)
    rng = random.Random(seed)
    queues = []
    for band in sorted(bands, reverse=True):
        rng.shuffle(bands[band])
        queues.append(bands[band])
    order = []
    while any(queues):
        order += [queue.pop(0) for queue in queues if queue]
    return order


# --- one station's snow depth -----------------------------------------------

def parse_snow_depth(text: str) -> tuple[list[tuple[date, int]], int]:
    """(day, snow depth in mm) for each report that passed quality control, and how many did not.

    SNWD_ATTRIBUTES is "measurement flag,quality flag,source flag"; any quality flag means a failed check.
    """
    records, flagged = [], 0
    for row in csv.DictReader(io.StringIO(text)):
        value = (row.get("SNWD") or "").strip()
        if not value:
            continue
        attributes = (row.get("SNWD_ATTRIBUTES") or "").split(",")
        if len(attributes) > 1 and attributes[1].strip():
            flagged += 1
            continue
        records.append((date.fromisoformat(row["DATE"]), int(value)))
    return records, flagged


def winter_coverage(records, first_winter: int, last_winter: int) -> dict[int, float]:
    """Share of the days from 1 October to 31 March that carry a report, for each winter."""
    seen = {winter: set() for winter in range(first_winter, last_winter + 1)}
    for day, _ in records:
        winter = winter_half_of(day)
        if winter in seen:
            seen[winter].add(day)
    return {winter: len(days) / ((date(winter + 1, 4, 1) - date(winter, 10, 1)).days)
            for winter, days in seen.items()}


def assess(records, first_winter: int, last_winter: int, min_coverage: float = MIN_COVERAGE,
           min_winters: int = MIN_WINTERS, min_snow_reports: int = 1) -> dict:
    """Decide whether a station's snow depth can stand for a snow-free share.

    Kept stations report on at least min_coverage of the days in at least min_winters
    winter halves (1 October to 31 March), and those winters hold both zero and
    non-zero depths. "records" in the result holds only the well-reported winter
    halves, which is what the verdict rests on. "year_records" holds the whole snow
    years of those winters (the summer that follows each one included), ready for
    stations.snow_free_by_bin; reports from April to September never change the verdict.
    min_snow_reports above 1 also rejects a record whose only snow is a stray report
    or two: such a station writes zero by default, not by measurement.
    """
    coverage = winter_coverage(records, first_winter, last_winter)
    good = [winter for winter, share in coverage.items() if share >= min_coverage]
    used = [(day, depth) for day, depth in records if winter_half_of(day) in good]
    whole_years = [(day, depth) for day, depth in records if snow_year_of(day) in good]
    verdict = {"keep": False, "good_winters": good, "coverage": coverage, "records": used,
               "year_records": whole_years}
    if not any(coverage.values()):
        reason = "no snow depth in these winters"
    elif len(good) < min_winters:
        reason = f"fewer than {min_winters} winters with snow depth on {min_coverage:.0%} of days"
    elif not any(depth > 0 for _, depth in used):
        reason = "never above zero"
    elif sum(depth > 0 for _, depth in used) < min_snow_reports:
        reason = f"above zero on fewer than {min_snow_reports} days"
    elif not any(depth == 0 for _, depth in used):
        elsewhere = any(depth == 0 and first_winter <= day.year <= last_winter + 1 for day, depth in records)
        reason = ("never zero in winter, zero at other times of year" if elsewhere
                  else "never zero at any time of year")
    else:
        reason = "kept"
        verdict["keep"] = True
    verdict["reason"] = reason
    return verdict


def parse_weather(text: str) -> dict[date, tuple[int | None, int | None]]:
    """Daily maximum temperature (tenths of a degree C) and precipitation (tenths of a mm) per day."""
    def number(row: dict, key: str) -> int | None:
        value = (row.get(key) or "").strip()
        return int(value) if value else None

    return {date.fromisoformat(row["DATE"]): (number(row, "TMAX"), number(row, "PRCP"))
            for row in csv.DictReader(io.StringIO(text))}


def cold_wet_days(records, weather: dict, winters) -> tuple[int, int]:
    """Snow-depth reports that end a cold, wet week, and how many of them say bare ground.

    After a week whose daily maximum stayed below -1.0 C and which brought at least
    5 mm of precipitation (on the six days before the report), snow must lie. A station
    that often reports zero then is writing zero by default or has a faulty sensor.
    """
    found = bare = 0
    for day, depth in records:
        if winter_half_of(day) not in winters:
            continue
        week = [weather.get(day - timedelta(days=back), (None, None)) for back in range(COLD_WET_SPELL_DAYS)]
        if any(tmax is None or tmax >= COLD_WET_MAX_TMAX for tmax, _ in week):
            continue
        if sum(precip or 0 for _, precip in week[1:]) < COLD_WET_MIN_PRECIP:
            continue
        found += 1
        bare += depth == 0
    return found, bare


def parse_observed_days(text: str) -> set[date]:
    """Days on which the station reported any temperature or precipitation."""
    days = set()
    for row in csv.DictReader(io.StringIO(text)):
        if any((row.get(key) or "").strip() for key in ("TMAX", "TMIN", "TAVG", "PRCP")):
            days.add(date.fromisoformat(row["DATE"]))
    return days


def unreported_as_bare(records, observed_days, first_winter: int, last_winter: int,
                       min_reports: int = 30) -> tuple[list[tuple[date, int]], list[int]]:
    """Read "weather reported, snow depth not" as bare ground. An assumption, not a measurement.

    Only for stations that write snow depth down on snow days alone, and only in winters
    with at least min_reports snow-depth reports, which shows the snow depth was reaching
    the archive that winter. Returns the filled records and the winters used.
    """
    depth_on = {day: depth for day, depth in records}
    reports = {winter: 0 for winter in range(first_winter, last_winter + 1)}
    for day in depth_on:
        if winter_half_of(day) in reports:
            reports[winter_half_of(day)] += 1
    winters = [winter for winter, n in reports.items() if n >= min_reports]
    days = sorted(day for day in set(observed_days) | set(depth_on) if winter_half_of(day) in winters)
    return [(day, depth_on.get(day, 0)) for day in days], winters


def complete_bins(counts, possible_days, min_share: float = MIN_COVERAGE) -> np.ndarray:
    """Which ten-day bins carry reports on at least min_share of the days they could.

    possible_days is stations.days_per_bin of the snow years the counts come from: the
    calendar days each bin really holds there, so the last bin needs 80% of its 15 or
    16 days a year, not of ten. Count whole bins, also on a season edge: the satellite
    value of bin 27 stands for 28 September to 7 October, so a record that only starts
    on 1 October covers 70% of it and the bin is left out.
    """
    counts, possible_days = np.asarray(counts), np.asarray(possible_days)
    return (counts > 0) & (possible_days > 0) & (counts >= min_share * possible_days - 1e-9)


# --- satellite against stations ---------------------------------------------

def _pairs(satellite, station) -> tuple[np.ndarray, np.ndarray]:
    satellite = np.asarray(satellite, dtype=float).ravel()
    station = np.asarray(station, dtype=float).ravel()
    both = np.isfinite(satellite) & np.isfinite(station)
    return satellite[both], station[both]


def summarise(satellite, station) -> dict:
    """Mean and median of (satellite minus station) and the mean of its absolute value, over bins where both exist."""
    satellite, station = _pairs(satellite, station)
    if satellite.size == 0:
        return {"n": 0, "mean_bias": None, "median_bias": None, "mean_abs_difference": None}
    difference = satellite - station
    return {"n": int(difference.size), "mean_bias": float(difference.mean()),
            "median_bias": float(np.median(difference)),
            "mean_abs_difference": float(np.abs(difference).mean())}


def station_biases(satellite, station) -> np.ndarray:
    """Mean of (satellite minus station) for each station (row) that has at least one bin with both."""
    difference = np.atleast_2d(np.asarray(satellite, dtype=float) - np.asarray(station, dtype=float))
    counts = np.isfinite(difference).sum(axis=1)
    return np.nansum(difference, axis=1)[counts > 0] / counts[counts > 0]


def resampled_bias_interval(satellite, station, seed: int = 0, draws: int = 4000) -> tuple[float, float]:
    """95% interval for the mean bias, from drawing whole stations (rows) with replacement.

    Bins of one station are not independent, so stations are the unit that is resampled.
    """
    difference = np.asarray(satellite, dtype=float) - np.asarray(station, dtype=float)
    sums, counts = np.nansum(difference, axis=1), np.isfinite(difference).sum(axis=1)
    picks = np.random.default_rng(seed).integers(0, len(sums), size=(draws, len(sums)))
    means = sums[picks].sum(axis=1) / counts[picks].sum(axis=1)
    low, high = np.percentile(means, [2.5, 97.5])
    return float(low), float(high)


def calibration_table(satellite, station, edges=CALIBRATION_EDGES) -> list[dict]:
    """Mean station snow-free share for each band of satellite probability.

    Bands are closed on the left and open on the right, except the last, which includes 1.
    Satellite values are rounded to six decimals first: they are stored as 32-bit
    numbers, so 0.7 arrives as 0.69999999 and would fall in the wrong band.
    """
    satellite, station = _pairs(satellite, station)
    satellite = np.round(satellite, 6)
    table = []
    for i, (low, high) in enumerate(zip(edges[:-1], edges[1:])):
        last = i == len(edges) - 2
        inside = (satellite >= low) & ((satellite <= high) if last else (satellite < high))
        n = int(inside.sum())
        table.append({"ims_low": low, "ims_high": high, "n_station_bins": n,
                      "mean_ims": float(satellite[inside].mean()) if n else None,
                      "mean_station_snow_free": float(station[inside].mean()) if n else None})
    return table


def calibrate(probabilities, table: list[dict]) -> np.ndarray:
    """Replace satellite probabilities by the station share the table pairs them with.

    Straight lines join the table's points (mean satellite value, mean station share);
    beyond the first and last point the curve is flat. Empty bands are skipped.
    """
    points = [(row["mean_ims"], row["mean_station_snow_free"]) for row in table if row["n_station_bins"]]
    xs, ys = zip(*sorted(points))
    return np.interp(np.asarray(probabilities, dtype=float), xs, ys)


def doubled(probabilities) -> np.ndarray:
    """An upper bound: twice the satellite probability, capped at 1."""
    return np.minimum(1.0, 2.0 * np.asarray(probabilities, dtype=float))


def usable_days(days: list[int], probabilities) -> float | None:
    """All-day low-Sun days, each weighted by the snow-free odds of its ten-day bin (the old measure).

    Counted exactly as grazing.usable_days counts them for the cells file: None when a
    day falls in a bin without odds, or when there are no odds at all.
    """
    value = float(grazing.usable_days(grazing.days_per_bin(days), probabilities))
    return value if np.isfinite(value) else None


def count_at_least(values, threshold: float) -> int:
    """How many values reach the threshold; unknowns (None) do not."""
    return sum(1 for value in values if value is not None and value >= threshold)

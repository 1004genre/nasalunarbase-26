# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Snow-free odds from weather-station snow depth (NOAA GHCN-Daily), to check the satellite snow layer.

Station reports are sorted into the same 36 calendar ten-day bins as the satellite
maps. How dates are grouped is stated here, once, for every station script:

- A snow year is the twelve months from 1 October, named by the year of that October.
  The satellite maps cover ten of them, 1 October 2015 to 30 September 2025.
- Its winter half is 1 October to 31 March, its summer half 1 April to 30 September.
- Summaries by half-year go by whole bins, with the project's bin lists (grazing.py):
  winter bins 27 to 35 and 0 to 8 (28 September to 31 March), summer bins 9 to 26.

The stale-flag rule of the snow layer uses a shorter winter, 1 October to 20 March.
That one is snow.winter_of; it is a different thing and keeps its own name.
"""
from __future__ import annotations

import csv
import io
from datetime import date, timedelta

import numpy as np

from twinfinder import snow, sun
from twinfinder.grazing import SUMMER_BINS_NORTH, WINTER_BINS_NORTH

GHCN_ACCESS = "https://www.ncei.noaa.gov/data/global-historical-climatology-network-daily/access"
WINTER_HALF_BINS = list(WINTER_BINS_NORTH)   # 28 September to 31 March
SUMMER_HALF_BINS = list(SUMMER_BINS_NORTH)   # 1 April to 27 September
MAY_TO_AUGUST_BINS = list(range(12, 24))     # 1 May to 28 August
HALVES = (None, "winter", "summer")          # None is the whole snow year


def station_url(station_id: str) -> str:
    return f"{GHCN_ACCESS}/{station_id}.csv"


def parse_snow_depth(text: str) -> list[tuple[date, int]]:
    """(day, snow depth in mm) for every row that reports a snow depth."""
    records = []
    for row in csv.DictReader(io.StringIO(text)):
        value = (row.get("SNWD") or "").strip()
        if value:
            records.append((date.fromisoformat(row["DATE"]), int(value)))
    return records


# --- how dates are grouped ----------------------------------------------------

def snow_year_of(day: date) -> int:
    """The snow year (1 October to 30 September, named by its October) a date belongs to."""
    return day.year if day.month >= 10 else day.year - 1


def winter_half_of(day: date) -> int | None:
    """The snow year of a date from 1 October to 31 March; None from April to September."""
    return snow_year_of(day) if day.month >= 10 or day.month <= 3 else None


def summer_half_of(day: date) -> int | None:
    """The snow year of a date from 1 April to 30 September; None from October to March."""
    return snow_year_of(day) if winter_half_of(day) is None else None


def in_half(day: date, half: str | None) -> bool:
    """Whether a date lies in the asked half of its snow year; None asks for the whole year."""
    if half not in HALVES:
        raise ValueError(f"half must be None, 'winter' or 'summer', not {half!r}")
    if half is None:
        return True
    return (winter_half_of(day) is not None) == (half == "winter")


def bin_of(day: date) -> int:
    """Calendar ten-day bin of a date, taken from its own day of year, exactly as the satellite maps are binned.

    So in a leap year every bin after February starts one calendar day earlier,
    and day 366 stays in the last bin.
    """
    return snow.bin_index(day.timetuple().tm_yday)


def bin_label(index: int) -> str:
    """A bin named by its first day in a common year: Jan01, Jan11, ..., Dec17."""
    return (date(2027, 1, 1) + timedelta(days=snow.BIN_DAYS * index)).strftime("%b%d")


def bin_span(bins) -> str:
    """First and last day of a run of bins in a common year, such as "1 May-28 Aug".

    The run is read in the order given, so the winter bins (27 to 35, then 0 to 8) give "28 Sep-31 Mar".
    """
    first, last = list(bins)[0], list(bins)[-1]
    end = 365 if last == snow.N_BINS - 1 else snow.BIN_DAYS * (last + 1)
    return f"{sun.doy_to_label(snow.BIN_DAYS * first + 1)}-{sun.doy_to_label(end)}"


# --- snow-free share per bin ---------------------------------------------------

def snow_free_by_bin(records, first_year: int, last_year: int,
                     half: str | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Share of reports with zero snow depth per calendar ten-day bin, and the number of reports.

    Only reports of the snow years first_year to last_year count, so January 2021
    and July 2021 both belong to 2020. half="winter" or "summer" keeps the dates of
    that half only; a bin that straddles 1 October or 1 April then holds part of its days.
    """
    free = np.zeros(snow.N_BINS)
    seen = np.zeros(snow.N_BINS)
    for day, depth_mm in records:
        if not first_year <= snow_year_of(day) <= last_year or not in_half(day, half):
            continue
        index = bin_of(day)
        seen[index] += 1
        free[index] += depth_mm == 0
    with np.errstate(invalid="ignore", divide="ignore"):
        shares = np.where(seen > 0, free / seen, np.nan)
    return shares, seen.astype(int)


snow_free_by_dekad = snow_free_by_bin   # old name, kept for earlier callers; it now covers the whole year


def days_per_bin(snow_years, half: str | None = None) -> np.ndarray:
    """How many calendar days each ten-day bin holds within the given snow years.

    Ten per year for every bin but the last, which holds 15 (16 when its December
    is in a leap year). With half="winter" or "summer" only the days of that half
    are counted, which splits the bins on the season edges.
    """
    days = np.zeros(snow.N_BINS, dtype=int)
    for year in snow_years:
        day = date(year, 10, 1)
        while day < date(year + 1, 10, 1):
            days[bin_of(day)] += in_half(day, half)
            day += timedelta(days=1)
    return days

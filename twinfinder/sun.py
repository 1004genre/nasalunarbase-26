# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Solar geometry: when, and for how long, is the Sun as low as at the lunar south pole?"""
from __future__ import annotations

import multiprocessing
import os
from concurrent.futures import ProcessPoolExecutor
from datetime import date, timedelta

import numpy as np

LUNAR_AXIAL_TILT_DEG = 1.54

# Shared with the snow, horizon and grazing modules (see the build contract).
BIN_DAYS = 10
N_BINS = 36       # ten-day bins; the last one holds days 351 to 366
AZ_SECTORS = 36   # sector k covers azimuth [10k, 10k + 10) degrees, 0 = north, clockwise
# The Sun ceiling of each lunar region (two decimals, grazing.target_limit) is an edge, so that a region's band
# ends at its own ceiling. Sixteen regions: 2.08 Connecting Ridge, 2.51 Connecting Ridge Extension, 2.73 Peak Near
# Shackleton, 2.86 de Gerlache Rim 1, 3.31 de Gerlache Rim 2, 3.65 Faustini Rim A, 4.38 Slater Plain, 4.78 Haworth,
# 5.55 Malapert Massif, 5.71 de Gerlache-Kocher Massif, 6.10 Nobile Rim 1, 6.11 Mons Mouton, 7.21 Mons Mouton
# Plateau, 7.31 Amundsen Rim, 7.59 Nobile Rim 2, 7.90 Peak near Cabeus B. The other edges (0.5, 1.0, 1.5, 3.0, 4.0)
# are the old fixed ones.
ELEV_EDGES_DEG = [0.0, 0.5, 1.0, 1.5, 2.08, 2.51, 2.73, 2.86, 3.0, 3.31, 3.65, 4.0, 4.38, 4.78, 5.55, 5.71, 6.10, 6.11,
                  7.21, 7.31, 7.59, 7.90]  # 21 bins
OLD_ELEV_EDGES_DEG = [0.0, 0.5, 1.0, 1.5, 2.08, 3.0, 4.0, 5.55, 6.11, 7.59]  # the 9 bins of the four-region build
# the 15 bins of the ten-region build (first pass, 15 November 2026): winter_leads.json holds horizons on these
TEN_REGION_ELEV_EDGES_DEG = [0.0, 0.5, 1.0, 1.5, 2.08, 3.0, 3.31, 4.0, 4.38, 4.78, 5.55, 6.10, 6.11, 7.21, 7.59, 7.90]
LIMIT_SLACK_DEG = 0.005      # a target's limit may sit this far below a bin's upper edge and still use the bin
SPELL_SLACK_MINUTES = 1e-6   # a spell this close under the minimum length counts (rounding of the sums only)

# Days from 2000-01-01 12:00 to 12:00 UT on "day 0" of the year: 2026, moved 0.14 day
# earlier so the series sits in the middle of the 2024 to 2028 leap-year cycle.
DAY_ZERO_FROM_J2000 = 9495.86

# The yearly tables are the mean over this many calendars, each 1 / YEAR_PHASES day on from the one
# before and centred on the calendar of DAY_ZERO_FROM_J2000: with eight, from 7/16 day earlier to
# 7/16 day later in steps of an eighth of a day. The four years of a leap cycle sit a quarter day
# apart (noon falls a quarter day later against the seasons from one year to the next and jumps back
# in a leap year), and noon also falls earlier or later by longitude, so no single alignment is the
# right one; with a sharp two-hour rule a single one moves a latitude's long-spell hours by up to
# 9 hours a year. Four phases left up to 3.2 h and missed the test of 1 percent or half an hour at
# 4 of 40 test cases; eight meet it there (largest 1.0 h at the worst move of 1/16 day) and keep every
# cell latitude within the larger of 2 percent and 1 h (decided 14 Nov 2026, at twice the run time
# of four). year_phases=1 gives the single calendar of DAY_ZERO_FROM_J2000.
YEAR_PHASES = 8

# The Sun tables are worked out latitude by latitude, and each latitude is independent of the others. A pool of
# worker processes takes the latitudes in small groups; the result is the same, number for number, as one process
# gives. TWINFINDER_WORKERS=1 turns the pool off.
WORKERS = max(1, int(os.environ.get("TWINFINDER_WORKERS", str(max(1, min(10, (os.cpu_count() or 2) - 1))))))
LATS_PER_TASK = 3
_POOL = None
_IN_WORKER = False
_SHARED = ("ELEV_EDGES_DEG", "DAY_ZERO_FROM_J2000", "LIMIT_SLACK_DEG", "SPELL_SLACK_MINUTES")


def _mark_worker() -> None:
    global _IN_WORKER
    _IN_WORKER = True


def _pool() -> ProcessPoolExecutor:
    global _POOL
    if _POOL is None:
        _POOL = ProcessPoolExecutor(WORKERS, mp_context=multiprocessing.get_context("spawn"), initializer=_mark_worker)
    return _POOL


def _task(job):
    name, lats, args, kwargs, shared = job
    globals().update(shared)
    return _SERIAL[name](lats, *args, **kwargs)


def _over_latitudes(name: str, lats, args: tuple, kwargs: dict, axis: int):
    """Run the serial table function name over lats, in worker processes when there are many latitudes."""
    lats = list(lats)
    # only the main process starts a pool: a worker of any pool (this one or a script's own) runs the latitudes itself
    if _IN_WORKER or multiprocessing.parent_process() is not None or WORKERS < 2 or len(lats) < 2 * LATS_PER_TASK:
        return _SERIAL[name](lats, *args, **kwargs)
    shared = {key: globals()[key] for key in _SHARED}
    jobs = [(name, lats[i:i + LATS_PER_TASK], args, kwargs, shared) for i in range(0, len(lats), LATS_PER_TASK)]
    return np.concatenate(list(_pool().map(_task, jobs)), axis=axis)


def bin_index(day_of_year: int) -> int:
    """Ten-day bin of a day of year (1 to 366)."""
    return min((day_of_year - 1) // BIN_DAYS, N_BINS - 1)


def declination_deg(day_of_year):
    """Solar declination at 12:00 UT (Astronomical Almanac low-precision formula).

    Takes a number or an array; half a day later is day_of_year + 0.5. Within
    0.16 degrees of JPL Horizons on every day of 2024 to 2028; the same day of
    year differs by up to 0.30 degrees between those years, so no series by day
    of year alone can do better than 0.15.
    """
    n = DAY_ZERO_FROM_J2000 + np.asarray(day_of_year, dtype=float)
    mean_lon = 280.460 + 0.9856474 * n
    anomaly = np.radians(357.528 + 0.9856003 * n)
    lon = np.radians(mean_lon + 1.915 * np.sin(anomaly) + 0.020 * np.sin(2.0 * anomaly))
    tilt = np.radians(23.439 - 0.0000004 * n)
    dec = np.degrees(np.arcsin(np.sin(tilt) * np.sin(lon)))
    return dec if dec.ndim else float(dec)


def refraction_deg(true_elev_deg):
    """How far the air lifts the Sun (Saemundsson 1986, at 10 C and 1010 hPa); 0 below -2 degrees."""
    true = np.asarray(true_elev_deg, dtype=float)
    h = np.maximum(true, -2.0)
    lift = 1.02 / np.tan(np.radians(h + 10.3 / (h + 5.11))) / 60.0
    lift = np.where(true < -2.0, 0.0, np.maximum(lift, 0.0))
    return lift if lift.ndim else float(lift)


def apparent_elevation_deg(true_elev_deg):
    """Elevation of the Sun's centre as seen through the air."""
    return true_elev_deg + refraction_deg(true_elev_deg)


def _elevation(lat_rad, dec_rad, hour_angle_rad):
    """True elevation in degrees."""
    sine = np.sin(lat_rad) * np.sin(dec_rad) + np.cos(lat_rad) * np.cos(dec_rad) * np.cos(hour_angle_rad)
    return np.degrees(np.arcsin(np.clip(sine, -1.0, 1.0)))


def _azimuth(lat_rad, dec_rad, hour_angle_rad):
    """Azimuth in degrees, 0 = north, clockwise."""
    east = -np.cos(dec_rad) * np.sin(hour_angle_rad)
    north = np.cos(lat_rad) * np.sin(dec_rad) - np.sin(lat_rad) * np.cos(dec_rad) * np.cos(hour_angle_rad)
    az = np.degrees(np.arctan2(east, north)) % 360.0
    return np.where(az >= 360.0, 0.0, az)


def elevation_azimuth(lat_deg, day_of_year, solar_hours):
    """True elevation and azimuth (degrees, 0 = north, clockwise) at local solar time.

    Numbers or arrays that broadcast. Noon is solar_hours 12, so longitude and
    the equation of time do not enter the hour angle. The declination follows
    the hour (12:00 solar time is taken as 12:00 UT of the day); the equation of
    time would shift it by under 0.005 degrees and is left out.
    """
    hours = np.asarray(solar_hours, dtype=float)
    lat = np.radians(lat_deg)
    dec = np.radians(declination_deg(np.asarray(day_of_year) + (hours - 12.0) / 24.0))
    hour_angle = np.radians(15.0 * (hours - 12.0))
    elev, az = _elevation(lat, dec, hour_angle), _azimuth(lat, dec, hour_angle)
    return (elev, az) if elev.ndim else (float(elev), float(az))


def _year_track(solar_hours: np.ndarray, day_offset: float = 0.0) -> tuple[np.ndarray, np.ndarray]:
    """Declination and hour angle (radians) at these solar hours on each day of a 365-day year: [365, hours].

    day_offset moves the calendar: the Sun of day d is taken day_offset days later in the year.
    """
    days = np.arange(1, 366)[:, None] + day_offset
    dec = np.radians(declination_deg(days + (solar_hours - 12.0) / 24.0))
    return dec, np.broadcast_to(np.radians(15.0 * (solar_hours - 12.0)), dec.shape)


def _phase_offsets(year_phases: int) -> list[float]:
    """The calendar offsets, in days, that a table is averaged over: n of them, 1/n day apart, centred on 0.

    One phase: 0. Four: -0.375, -0.125, 0.125, 0.375. Eight (the default): -0.4375 to 0.4375 in steps of
    0.125. Centred, so that the mean calendar stays the
    one of DAY_ZERO_FROM_J2000 and no hours drift from one ten-day bin into the next.
    """
    if year_phases != int(year_phases) or year_phases < 1:
        raise ValueError(f"year_phases must be a whole number of at least 1, got {year_phases}")
    n = int(year_phases)
    return [(p + 0.5) / n - 0.5 for p in range(n)]


def phase_offsets(year_phases: int = YEAR_PHASES) -> list[float]:
    """The calendar offsets, in days, that the tables average over (see _phase_offsets); for code outside this module."""
    return _phase_offsets(year_phases)


def _phase_tracks(solar_hours: np.ndarray, year_phases: int) -> list[tuple[np.ndarray, np.ndarray]]:
    """_year_track for each calendar a table is averaged over."""
    return [_year_track(solar_hours, offset) for offset in _phase_offsets(year_phases)]


def _step_hours(step_minutes: float) -> tuple[np.ndarray, np.ndarray]:
    """Solar hours at the edges of a day's time steps (one more than the steps) and at their middles."""
    steps = round(1440.0 / step_minutes) if step_minutes > 0 else 0
    if steps < 1 or abs(steps * step_minutes - 1440.0) > 1e-6:
        raise ValueError(f"step_minutes must divide the 1440 minutes of a day, got {step_minutes}")
    edges = np.arange(steps + 1) * (step_minutes / 60.0)
    return edges, edges[:-1] + step_minutes / 120.0


def _day_bins() -> np.ndarray:
    """Ten-day bin of each day of a 365-day year."""
    return np.array([bin_index(d) for d in range(1, 366)])


def _add_minutes(rows: np.ndarray, slot: np.ndarray, start: np.ndarray, end: np.ndarray, minutes: np.ndarray) -> None:
    """Add pieces of time to rows [slots, elevation bins].

    Each piece's minutes are shared between the elevation bins on the straight
    line from its start elevation to its end elevation.
    """
    low = np.minimum(start, end)
    high = np.maximum(np.maximum(start, end), low + 1e-9)
    for e in range(rows.shape[1]):
        within = np.minimum(high, ELEV_EDGES_DEG[e + 1]) - np.maximum(low, ELEV_EDGES_DEG[e])
        rows[:, e] += np.bincount(slot, weights=minutes * np.clip(within, 0.0, None) / (high - low),
                                  minlength=len(rows))


def _add_steps(rows: np.ndarray, lat_rad: float, dec: np.ndarray, hour_angle: np.ndarray, elev: np.ndarray,
               keep: np.ndarray, row_bin: np.ndarray, step_minutes: float) -> None:
    """Add the time steps marked in keep [days, steps] to rows [N_BINS * AZ_SECTORS, elevation bins from the lowest up].

    dec, hour_angle and elev are given at the edges of the steps [days, steps + 1]. The Sun moves on a
    straight line in elevation and azimuth during a step; the step is cut where it crosses a sector
    border, and each piece's minutes are shared between the elevation bins it passes through.
    """
    sector_deg = 360.0 / AZ_SECTORS
    start, end, slot = elev[:, :-1][keep], elev[:, 1:][keep], row_bin[keep] * AZ_SECTORS
    az = _azimuth(lat_rad, dec[:, :-1][keep], hour_angle[:, :-1][keep])
    az_end = _azimuth(lat_rad, dec[:, 1:][keep], hour_angle[:, 1:][keep])
    turn = (az_end - az + 180.0) % 360.0 - 180.0  # change in azimuth during the step, clockwise positive
    first = np.floor(az / sector_deg).astype(int)
    last = np.floor((az + turn) / sector_deg).astype(int)
    crossing = first != last
    # part of the step spent in its first sector, and the elevation where it leaves that sector
    part = np.ones_like(az)
    part[crossing] = (sector_deg * np.maximum(first, last)[crossing] - az[crossing]) / turn[crossing]
    border = start + part * (end - start)
    _add_minutes(rows, slot + first % AZ_SECTORS, start, border, step_minutes * part)
    _add_minutes(rows, (slot + last % AZ_SECTORS)[crossing], border[crossing], end[crossing],
                 step_minutes * (1.0 - part[crossing]))


def band_minutes_table(lats, step_minutes: float = 2, refraction: bool = True,
                       year_phases: int = YEAR_PHASES) -> np.ndarray:
    """See _band_minutes_table; run over the latitudes in worker processes."""
    return _over_latitudes("band", lats, (step_minutes, refraction, year_phases), {}, 0)


def _band_minutes_table(lats, step_minutes: float = 2, refraction: bool = True,
                        year_phases: int = YEAR_PHASES) -> np.ndarray:
    """Minutes per year with the Sun's centre in each elevation bin and azimuth sector.

    Returns float32 [len(lats), N_BINS, AZ_SECTORS, len(ELEV_EDGES_DEG) - 1] for a 365-day year, summed
    over the days of each ten-day bin, flat horizon, local solar time. Elevation
    bin i covers ELEV_EDGES_DEG[i] < elevation <= ELEV_EDGES_DEG[i + 1], using
    the apparent (refracted) elevation unless refraction is False.

    Whole time steps are not counted into one cell: near a solstice the Sun
    crosses a bin edge or a sector border at the same clock time day after day,
    and the rounding piles up. Instead the Sun moves on a straight line in
    elevation and azimuth during a step; the step is cut where it crosses a
    sector border, and each piece's minutes are shared between the elevation
    bins it passes through. step_minutes must divide the day and should stay
    under about half an hour (one sector border per step at most).

    The table is the mean over year_phases calendars (see YEAR_PHASES); with
    year_phases=1 it is the single calendar of DAY_ZERO_FROM_J2000. A single
    calendar moves a latitude's hours by up to 0.4 percent when the calendar is
    moved by 0.14 day, four phases by at most 0.12 percent (0.6 h a year) over
    the 468 latitudes of the cells; eight phases by at most 0.007 percent
    (0.02 h) at 65, 67, 70, 75 and 80 degrees north and south.
    """
    n_elev = len(ELEV_EDGES_DEG) - 1
    tracks = _phase_tracks(_step_hours(step_minutes)[0], year_phases)
    row_bin = np.broadcast_to(_day_bins()[:, None], (365, tracks[0][0].shape[1] - 1))
    table = np.zeros((len(lats), N_BINS * AZ_SECTORS, n_elev))
    for i, lat in enumerate(lats):
        lat_rad = np.radians(lat)
        for dec, hour_angle in tracks:
            elev = _elevation(lat_rad, dec, hour_angle)
            if refraction:
                elev = apparent_elevation_deg(elev)
            start, end = elev[:, :-1], elev[:, 1:]
            inside = (np.maximum(start, end) > ELEV_EDGES_DEG[0]) & (np.minimum(start, end) < ELEV_EDGES_DEG[-1])
            _add_steps(table[i], lat_rad, dec, hour_angle, elev, inside, row_bin, step_minutes)
    return (table / len(tracks)).reshape(len(lats), N_BINS, AZ_SECTORS, n_elev).astype(np.float32)


def bins_up_to(limit_deg: float) -> int:
    """How many elevation bins, counted from the horizon, lie wholly at or below a limit (with the shared allowance)."""
    return sum(1 for upper in ELEV_EDGES_DEG[1:] if upper <= limit_deg + LIMIT_SLACK_DEG)


def _spells(elev: np.ndarray, top_deg: float, step_minutes: float) -> tuple[np.ndarray, np.ndarray]:
    """The time steps that touch the band (0, top_deg], and the length in minutes of the spell each belongs to.

    elev is the Sun's elevation at the edges of the steps, [days, steps + 1]; the days follow one
    another and the last is followed by the first. Returns the places of the steps in the year
    (day * steps + step, in order) and, for each, the minutes of its whole spell.

    The Sun moves on a straight line in elevation during a step, as in band_minutes_table, so a step
    holds one unbroken piece of time in the band. Two steps that follow one another belong to the
    same spell when the Sun is in the band at the moment between them. A spell is not cut at
    midnight, at the end of a ten-day bin or at the year end, and it has no upper length.
    """
    start, end = elev[:, :-1].ravel(), elev[:, 1:].ravel()
    low, high = np.minimum(start, end), np.maximum(start, end)
    where = np.flatnonzero((high > ELEV_EDGES_DEG[0]) & (low < top_deg))
    if not len(where):
        return where, np.zeros(0)
    low, high = low[where], np.maximum(high[where], low[where] + 1e-9)
    minutes = step_minutes * (np.minimum(high, top_deg) - np.maximum(low, ELEV_EDGES_DEG[0])) / (high - low)
    before, now = np.roll(end[where], 1), start[where]       # the Sun at the moment between a step and the one before
    carries_on = ((where - np.roll(where, 1)) % len(start) == 1) if len(start) > 1 else np.ones(1, dtype=bool)
    carries_on &= (before > ELEV_EDGES_DEG[0]) & (before <= top_deg) & (now > ELEV_EDGES_DEG[0]) & (now <= top_deg)
    if carries_on.all():                                      # in the band all year round
        return where, np.full(len(where), minutes.sum())
    spell = np.cumsum(~carries_on) - 1
    spell[spell < 0] = spell[-1]                              # the year's first steps carry on the spell of its last ones
    return where, np.bincount(spell, weights=minutes)[spell]


def steps_in_long_spells(elev: np.ndarray, top_deg: float, min_minutes: float, step_minutes: float) -> np.ndarray:
    """Which time steps lie in a spell of at least min_minutes with the Sun in (0, top_deg]: true/false [days, steps].

    elev is the elevation at the edges of the steps, [days, steps + 1] (see _spells for how a spell
    is followed from step to step, through midnight and through the year end). Every step that
    holds a part of a long enough spell is marked, in the day it belongs to itself.
    """
    where, length = _spells(elev, top_deg, step_minutes)
    keep = np.zeros((elev.shape[0], elev.shape[1] - 1), dtype=bool)
    keep.ravel()[where[length >= min_minutes - SPELL_SLACK_MINUTES]] = True
    return keep


def long_band_minutes_table(lats, limits_deg, min_stretch_h: float = 2.0, step_minutes: float = 1,
                            refraction: bool = True, year_phases: int = YEAR_PHASES) -> np.ndarray:
    """See _long_band_minutes_table; run over the latitudes in worker processes."""
    return _over_latitudes("long", lats, (list(limits_deg), min_stretch_h, step_minutes, refraction, year_phases), {}, 1)


def _long_band_minutes_table(lats, limits_deg, min_stretch_h: float = 2.0, step_minutes: float = 1,
                             refraction: bool = True, year_phases: int = YEAR_PHASES) -> np.ndarray:
    """Minutes per year the Sun's centre spends in (0, limit] inside unbroken spells of at least min_stretch_h hours.

    Returns float32 [len(limits_deg), len(lats), N_BINS, AZ_SECTORS, elevation bins], laid out exactly like
    band_minutes_table (same 365 days, same sectors, same elevation bins, flat horizon, local solar
    time). Each limit has its own layer, because a spell under a low limit ends where the Sun
    climbs through that limit. A limit uses the elevation bins whose upper edge is at most the
    limit plus 0.005 (bins_up_to); the band of its spells ends at the upper edge of the highest of
    them, and the bins above stay zero.

    A spell is followed minute by minute through the year (_spells): one that runs through midnight
    is one spell, and each of its minutes is counted in the day and ten-day bin in which it falls;
    a Sun that stays in the band for more than a day counts in full.

    The table is the mean over year_phases calendars, each 1 / year_phases day on from the one
    before and centred on the single calendar (see YEAR_PHASES): the whole count, spells and
    all, is made for each calendar and the minutes are averaged, so a spell that reaches the
    minimum in one calendar of eight counts an eighth. year_phases=1 is the single calendar of
    DAY_ZERO_FROM_J2000, whose yearly hours move
    by up to 9 h when the calendar is moved by 0.14 day. With four phases the same move changes
    them by at most 3.2 h over the 468 latitudes of the cells (at 65, 67, 70, 75 and 80 degrees
    north and south: at most 2.0 h, and never more than the larger of 2 percent and 1 h). The
    rest is the two-hour rule itself: a spell that crosses the mark comes or goes in one calendar
    at a time, half an hour a year at a stroke with four, a quarter of an hour with eight. Eight
    phases (the default) keep every cell latitude within the larger of 2 percent and 1 h (at most
    1.5 h at the worst move of 1/16 day) and those ten latitudes within the larger of 1 percent
    and half an hour (at most 1.0 h at 1/16 day, 0.75 h at 0.14 day), at twice the run time of four.

    With the same year_phases and step: a layer with min_stretch_h = 0 equals band_minutes_table
    in the bins the limit uses, cell by cell, and no layer ever exceeds that table.
    """
    n_elev = len(ELEV_EDGES_DEG) - 1
    tracks = _phase_tracks(_step_hours(step_minutes)[0], year_phases)
    row_bin = np.broadcast_to(_day_bins()[:, None], (365, tracks[0][0].shape[1] - 1))
    used = [bins_up_to(limit) for limit in limits_deg]
    table = np.zeros((len(limits_deg), len(lats), N_BINS, AZ_SECTORS, n_elev), dtype=np.float32)
    for i, lat in enumerate(lats):
        lat_rad = np.radians(lat)
        rows = [np.zeros((N_BINS * AZ_SECTORS, n)) for n in used]
        for dec, hour_angle in tracks:
            elev = _elevation(lat_rad, dec, hour_angle)
            if refraction:
                elev = apparent_elevation_deg(elev)
            for j, n in enumerate(used):
                if n == 0:
                    continue
                keep = steps_in_long_spells(elev, ELEV_EDGES_DEG[n], 60.0 * min_stretch_h, step_minutes)
                _add_steps(rows[j], lat_rad, dec, hour_angle, elev, keep, row_bin, step_minutes)
        for j, n in enumerate(used):
            if n:
                table[j, i, :, :, :n] = (rows[j] / len(tracks)).reshape(N_BINS, AZ_SECTORS, n)
    return table


def longest_spell_hours(lats, limits_deg, step_minutes: float = 1, refraction: bool = True,
                        year_phases: int = YEAR_PHASES) -> np.ndarray:
    """See _longest_spell_hours; run over the latitudes in worker processes."""
    return _over_latitudes("spell", lats, (list(limits_deg), step_minutes, refraction, year_phases), {}, 0)


def _longest_spell_hours(lats, limits_deg, step_minutes: float = 1, refraction: bool = True,
                         year_phases: int = YEAR_PHASES) -> np.ndarray:
    """The longest unbroken spell of the year with the Sun's centre in (0, limit], in hours: [len(lats), len(limits_deg)].

    The same spells as long_band_minutes_table counts (flat horizon; not cut at midnight; not capped
    at a day, so near the poles it runs to hundreds of hours). 0 where the Sun never enters the band.

    The mean, over the year_phases calendars of that table, of each calendar's longest spell.
    Where the longest spell comes at a solstice (every latitude at which two-hour spells begin)
    the calendars differ by seconds; at 65 to 80 degrees by up to a quarter of an hour; within
    three degrees of a pole, where one spell lasts for weeks, by up to a day.
    """
    tracks = _phase_tracks(_step_hours(step_minutes)[0], year_phases)
    used = [bins_up_to(limit) for limit in limits_deg]
    best = np.zeros((len(lats), len(limits_deg)))
    for i, lat in enumerate(lats):
        for dec, hour_angle in tracks:
            elev = _elevation(np.radians(lat), dec, hour_angle)
            if refraction:
                elev = apparent_elevation_deg(elev)
            for j, n in enumerate(used):
                length = _spells(elev, ELEV_EDGES_DEG[n], step_minutes)[1] if n else np.zeros(0)
                best[i, j] += length.max() / 60.0 if len(length) else 0.0
    return best / len(tracks)


def _run_so_far(inside: np.ndarray) -> np.ndarray:
    """Length of the run of True that ends at each place (0 where False)."""
    count = np.cumsum(inside, dtype=np.int32)
    return count - np.maximum.accumulate(np.where(inside, 0, count))


def _longest_run(inside: np.ndarray) -> np.ndarray:
    """Longest run of True that touches each day of inside [days, steps], in steps, at most one day long.

    The days follow one another (and the last is followed by the first), so a
    run that goes on past midnight counts in full for both days it touches.
    """
    days, steps = inside.shape
    year = np.concatenate([inside[-1], inside.ravel(), inside[0]])  # one long row with a day added at each end
    run = np.where(year, _run_so_far(year) + _run_so_far(year[::-1])[::-1] - 1, 0)
    return np.minimum(run[steps:-steps].reshape(days, steps).max(axis=1), steps)


def _stretch_hours(lat_deg, limits, refraction, step_minutes, dec, hour_angle) -> np.ndarray:
    elev = _elevation(np.radians(lat_deg), dec, hour_angle)
    if refraction:
        elev = apparent_elevation_deg(elev)
    hours = np.zeros((elev.shape[0], len(limits)))
    for j, limit in enumerate(limits):
        hours[:, j] = _longest_run((elev > 0.0) & (elev <= limit)) * (step_minutes / 60.0)
    return hours


def longest_stretch_hours_by_day(lat_deg: float, limits, refraction: bool = True,
                                 step_minutes: float = 2) -> np.ndarray:
    """Longest continuous time each day with the Sun's centre in (0, limit], flat horizon.

    Returns hours as [365, len(limits)], counted in whole time steps (sampled at
    the middle of each). A stretch that runs through midnight counts as one, in
    full, for both days it touches (the evening is joined to the next day's
    morning, not to the same day's); a stretch of a day or longer gives 24.
    One calendar only (that of DAY_ZERO_FROM_J2000): a day-by-day series has no
    phases to average over.
    """
    dec, hour_angle = _year_track(_step_hours(step_minutes)[1])
    return _stretch_hours(lat_deg, limits, refraction, step_minutes, dec, hour_angle)


def longest_stretch_hours_table(lats, limits, refraction: bool = True, step_minutes: float = 2,
                                year_phases: int = YEAR_PHASES) -> np.ndarray:
    """See _longest_stretch_hours_table; run over the latitudes in worker processes."""
    return _over_latitudes("stretch", lats, (list(limits), refraction, step_minutes, year_phases), {}, 0)


def _longest_stretch_hours_table(lats, limits, refraction: bool = True, step_minutes: float = 2,
                                 year_phases: int = YEAR_PHASES) -> np.ndarray:
    """Typical longest low-Sun stretch per day: float32 [len(lats), N_BINS, len(limits)], in hours.

    The median, over the days of each ten-day bin, of longest_stretch_hours_by_day; then the mean
    of those medians over the year_phases calendars (see YEAR_PHASES). With year_phases=1 it is
    the single calendar, as version 2 used it.
    """
    tracks = _phase_tracks(_step_hours(step_minutes)[1], year_phases)
    day_bin = _day_bins()
    table = np.zeros((len(lats), N_BINS, len(limits)))
    for i, lat in enumerate(lats):
        for dec, hour_angle in tracks:
            by_day = _stretch_hours(lat, limits, refraction, step_minutes, dec, hour_angle)
            for b in range(N_BINS):
                table[i, b] += np.median(by_day[day_bin == b], axis=0)
    return (table / len(tracks)).astype(np.float32)


_SERIAL = {"band": _band_minutes_table, "long": _long_band_minutes_table, "spell": _longest_spell_hours,
           "stretch": _longest_stretch_hours_table}


def noon_elevation_deg(lat_deg: float, day_of_year):
    """True elevation of the Sun's centre at local solar noon. Negative means it is below the horizon."""
    return 90.0 - abs(lat_deg - declination_deg(day_of_year))


def low_sun_days(lat_deg: float, max_elev_deg: float, min_elev_deg: float = 0.0,
                 refraction: bool = True) -> list[int]:
    """Days of year when the apparent noon Sun is above min_elev_deg and at or below max_elev_deg."""
    days = np.arange(1, 366)
    noon = noon_elevation_deg(lat_deg, days)
    if refraction:
        noon = apparent_elevation_deg(noon)
    return [int(d) for d in days[(noon > min_elev_deg) & (noon <= max_elev_deg)]]


def all_day_low_sun_days(lat_deg: float, limit_deg: float, refraction: bool = True) -> list[int]:
    """Days of year on which the Sun rises and stays at or below limit_deg all day.

    That is: apparent noon elevation above 0 and at or below the limit.
    refraction=False gives the geometric rule (true noon elevation).
    """
    return low_sun_days(lat_deg, limit_deg, refraction=refraction)


def windows(days: list[int]) -> list[tuple[int, int]]:
    """Group days of year into (start, end) runs, joining a run that crosses New Year."""
    if not days:
        return []
    runs: list[tuple[int, int]] = []
    start = prev = days[0]
    for d in days[1:]:
        if d != prev + 1:
            runs.append((start, prev))
            start = d
        prev = d
    runs.append((start, prev))
    if len(runs) > 1 and runs[0][0] == 1 and runs[-1][1] == 365:
        runs = [(runs[-1][0], runs[0][1])] + runs[1:-1]
    return runs


def doy_to_label(day_of_year: int) -> str:
    d = date(2027, 1, 1) + timedelta(days=day_of_year - 1)  # 2027 is not a leap year
    return f"{d.day} {d.strftime('%b')}"


def lunar_max_sun_elevation_deg(lat_deg: float) -> float:
    """Highest the Sun's centre climbs above a flat horizon at a lunar latitude."""
    return 90.0 - abs(lat_deg) + LUNAR_AXIAL_TILT_DEG

# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
import calendar
import math
from datetime import date

import numpy as np
import pytest

from twinfinder import sun

JUNE_SOLSTICE = 172  # 21 June
DEC_SOLSTICE = 355   # 21 December

# Azimuth sectors (10 degrees each, 0 = north, clockwise) on the northern and southern half of the sky.
NORTH_SECTORS = list(range(0, 9)) + list(range(27, 36))
SOUTH_SECTORS = list(range(9, 27))

# JPL Horizons (DE441), Sun seen from Earth's centre, airless apparent declination at 12:00 UT.
HORIZONS_DEC_12UT = {
    (2024, 80): 0.14651,     # 20 Mar 2024
    (2025, 172): 23.43783,   # 21 Jun 2025
    (2026, 266): -0.19313,   # 23 Sep 2026
    (2027, 356): -23.43649,  # 22 Dec 2027
    (2028, 60): -7.65701,    # 29 Feb 2028
}

# Verification run of 14 Nov 2026: hours per year with the geometric Sun centre above a flat
# horizon and at or below a limit. The table's nearest bin edge stands in for each limit.
VERIFIED_HOURS = {
    2.1: {0.0: 107, 60.0: 259, 67.0: 458, 69.0: 390},
    5.5: {0.0: 279, 50.0: 470, 60.0: 704, 67.0: 992, 69.0: 1006},
    7.6: {0.0: 386, 60.0: 1036, 67.0: 1275, 69.0: 1304},
}
TABLE_EDGE = {2.1: 2.08, 5.5: 5.55, 7.6: 7.59}
LATS = [0.0, 50.0, 60.0, 67.0, 69.0, -69.0]


def near(a, b, tol=2):
    return abs(a - b) <= tol


def ephemeris_declination_deg(year: int, day_of_year: int) -> float:
    """Apparent declination at 12 UT (Meeus, Astronomical Algorithms, chapter 25).

    Agrees with JPL Horizons to 0.003 degrees on every day of 2024 to 2028.
    """
    jd = date(year, 1, 1).toordinal() + 1721424.5 + (day_of_year - 1) + 0.5
    t = (jd - 2451545.0) / 36525.0
    mean_lon = 280.46646 + 36000.76983 * t + 0.0003032 * t * t
    anomaly = math.radians(357.52911 + 35999.05029 * t - 0.0001537 * t * t)
    centre = ((1.914602 - 0.004817 * t - 0.000014 * t * t) * math.sin(anomaly)
              + (0.019993 - 0.000101 * t) * math.sin(2 * anomaly) + 0.000289 * math.sin(3 * anomaly))
    node = math.radians(125.04 - 1934.136 * t)
    lon = math.radians(mean_lon + centre - 0.00569 - 0.00478 * math.sin(node))
    tilt = 23.0 + 26.0 / 60 + 21.448 / 3600 - (46.8150 * t + 0.00059 * t * t - 0.001813 * t ** 3) / 3600
    tilt = math.radians(tilt + 0.00256 * math.cos(node))
    return math.degrees(math.asin(math.sin(tilt) * math.sin(lon)))


def hours_up_to(table_row, limit: float) -> float:
    """Hours per year in (0, limit] from one latitude's [bins, sectors, elevation bins] slice."""
    n = sum(1 for upper in sun.ELEV_EDGES_DEG[1:] if upper <= limit + 0.005)
    return float(table_row[:, :, :n].sum()) / 60.0


def slow_count(lat: float, days, refraction: bool, fine: float = 0.1) -> np.ndarray:
    """Minutes per azimuth sector and elevation bin, counting samples every `fine` minutes one condition at a time."""
    hours = (np.arange(0.0, 1440.0, fine) + fine / 2) / 60.0
    slow = np.zeros((sun.AZ_SECTORS, 9))
    for doy in days:
        elev, az = sun.elevation_azimuth(lat, doy, hours)
        if refraction:
            elev = sun.apparent_elevation_deg(elev)
        for k in range(sun.AZ_SECTORS):
            in_sector = (az >= 10.0 * k) & (az < 10.0 * k + 10.0)
            for i in range(9):
                in_band = (elev > sun.ELEV_EDGES_DEG[i]) & (elev <= sun.ELEV_EDGES_DEG[i + 1])
                slow[k, i] += fine * np.count_nonzero(in_sector & in_band)
    return slow


def bennett_true_elevation_deg(apparent_deg: float) -> float:
    """True elevation seen at an apparent elevation (Bennett 1982): a second refraction formula, run the other way."""
    return apparent_deg - 1.0 / math.tan(math.radians(apparent_deg + 7.31 / (apparent_deg + 4.4))) / 60.0


def hour_angle_hours(lat: float, low_deg: float, high_deg: float) -> float:
    """Hours per year with the true Sun centre in (low, high], from each day's rising and setting hour angles."""
    dec = np.radians(sun.declination_deg(np.arange(1, 366)))
    phi = math.radians(lat)

    def half_arc_deg(elev_deg):
        cosine = (math.sin(math.radians(elev_deg)) - math.sin(phi) * np.sin(dec)) / (math.cos(phi) * np.cos(dec))
        return np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0)))

    return float((2.0 * (half_arc_deg(low_deg) - half_arc_deg(high_deg)) / 15.0).sum())


def day_length_hours(lat: float, day_of_year: int) -> float:
    """Hours with the true Sun centre above a flat horizon (sunrise equation, noon declination)."""
    dec = math.radians(sun.declination_deg(day_of_year))
    return 2.0 * math.degrees(math.acos(max(-1.0, min(1.0, -math.tan(math.radians(lat)) * math.tan(dec))))) / 15.0


# The tests down to the round 4 section check the mechanics of the tables against counts made for one calendar,
# so they ask for year_phases=1 (the single calendar of sun.DAY_ZERO_FROM_J2000). The default is eight phases.

@pytest.fixture(scope="module")
def geometric_table():
    return sun.band_minutes_table(LATS, refraction=False, year_phases=1)


@pytest.fixture(scope="module")
def apparent_table():
    return sun.band_minutes_table(LATS, year_phases=1)


# Shared constants

def test_shared_constants_match_the_contract():
    assert (sun.BIN_DAYS, sun.N_BINS, sun.AZ_SECTORS) == (10, 36, 36)
    assert list(sun.ELEV_EDGES_DEG) == [0.0, 0.5, 1.0, 1.5, 2.08, 3.0, 4.0, 5.55, 6.11, 7.59]


def test_bin_index_puts_days_351_to_366_in_the_last_bin():
    assert [sun.bin_index(d) for d in (1, 10, 11, 350, 351, 365, 366)] == [0, 0, 1, 34, 35, 35, 35]


# Declination

def test_reference_ephemeris_matches_jpl_horizons():
    for (year, doy), dec in HORIZONS_DEC_12UT.items():
        assert ephemeris_declination_deg(year, doy) == pytest.approx(dec, abs=0.005)


def test_declination_stays_within_0_3_deg_of_the_ephemeris_2024_to_2028():
    worst = 0.0
    for year in range(2024, 2029):
        for doy in range(1, 366 + calendar.isleap(year)):
            worst = max(worst, abs(sun.declination_deg(doy) - ephemeris_declination_deg(year, doy)))
    assert worst < 0.3   # the contract's bound
    # The series sits in the middle of the leap-year cycle: the same day of year differs by 0.30 degrees
    # between these years, so 0.15 is the best a day-of-year series can do. A quarter-day slip breaks this.
    assert worst < 0.16


def test_declination_takes_arrays_and_parts_of_a_day():
    dec = sun.declination_deg(np.array([JUNE_SOLSTICE, DEC_SOLSTICE]))
    assert dec.shape == (2,)
    assert dec[0] == pytest.approx(23.44, abs=0.01) and dec[1] == pytest.approx(-23.44, abs=0.01)
    assert isinstance(sun.declination_deg(80), float)
    assert sun.declination_deg(80) < sun.declination_deg(80.5) < sun.declination_deg(81)


# Refraction

def test_refraction_is_saemundsson_at_standard_conditions():
    assert sun.refraction_deg(0.0) == pytest.approx(0.4830, abs=0.0005)  # 29 arc minutes
    assert sun.refraction_deg(5.0) == pytest.approx(0.1612, abs=0.0005)
    assert sun.refraction_deg(45.0) == pytest.approx(0.0169, abs=0.0005)
    assert isinstance(sun.refraction_deg(0.0), float)


def test_refraction_is_zero_below_minus_two_degrees():
    assert sun.refraction_deg(-1.99) == pytest.approx(0.7427, abs=0.0005)
    assert sun.refraction_deg(-2.01) == 0.0
    lift = sun.refraction_deg(np.array([-90.0, -5.11, -2.5, 0.0, 90.0]))
    assert np.all(np.isfinite(lift)) and np.all(lift >= 0.0)
    assert list(lift[:3]) == [0.0, 0.0, 0.0]
    assert lift[4] == pytest.approx(0.0, abs=0.001)


def test_apparent_elevation_adds_the_lift():
    assert sun.apparent_elevation_deg(-0.574) == pytest.approx(0.0, abs=0.002)  # centre seen on the horizon
    assert sun.apparent_elevation_deg(5.0) == pytest.approx(5.1612, abs=0.0005)
    assert sun.apparent_elevation_deg(-10.0) == -10.0
    apparent = sun.apparent_elevation_deg(np.linspace(-5.0, 90.0, 2000))
    assert np.all(np.diff(apparent) > 0.0)


# Elevation and azimuth

def test_noon_sun_is_due_south_in_the_north_and_due_north_in_the_south():
    elev, az = sun.elevation_azimuth(50.0, JUNE_SOLSTICE, 12.0)
    assert elev == pytest.approx(63.44, abs=0.02) and az == pytest.approx(180.0, abs=0.01)
    elev, az = sun.elevation_azimuth(-50.0, JUNE_SOLSTICE, 12.0)
    assert elev == pytest.approx(16.56, abs=0.02) and min(az, 360.0 - az) < 0.01


def test_midnight_sun_is_due_north_at_69N_and_due_south_at_69S():
    elev, az = sun.elevation_azimuth(69.0, JUNE_SOLSTICE, 0.0)
    assert elev == pytest.approx(2.44, abs=0.03) and min(az, 360.0 - az) < 0.01
    elev, az = sun.elevation_azimuth(-69.0, DEC_SOLSTICE, 24.0)
    assert elev == pytest.approx(2.44, abs=0.03) and az == pytest.approx(180.0, abs=0.01)


def test_sun_is_east_in_the_morning_and_west_in_the_evening():
    hours = np.array([6.0, 9.0, 15.0, 18.0])
    elev, az = sun.elevation_azimuth(40.0, 80, hours)
    assert az[0] == pytest.approx(90.0, abs=1.0) and az[3] == pytest.approx(270.0, abs=1.0)
    assert 90.0 < az[1] < 180.0 < az[2] < 270.0
    assert elev[0] == pytest.approx(0.0, abs=0.5) and elev[1] == pytest.approx(elev[2], abs=0.2)
    _, az_south = sun.elevation_azimuth(-40.0, 80, hours)
    assert 0.0 < az_south[1] < 90.0 and 270.0 < az_south[2] < 360.0  # the Sun passes through north


def test_elevation_azimuth_broadcasts():
    elev, az = sun.elevation_azimuth(np.array([[0.0], [60.0]]), JUNE_SOLSTICE, np.arange(0.0, 24.0, 0.5))
    assert elev.shape == az.shape == (2, 48)
    assert np.all((az >= 0.0) & (az < 360.0))
    assert elev[0].max() == pytest.approx(66.56, abs=0.05) and elev[1].max() == pytest.approx(53.44, abs=0.05)


# Minutes per elevation band and azimuth sector

def test_band_minutes_table_shape(geometric_table):
    assert geometric_table.shape == (len(LATS), sun.N_BINS, sun.AZ_SECTORS, 9)
    assert geometric_table.dtype == np.float32
    assert geometric_table.min() >= 0.0


@pytest.mark.parametrize("limit", sorted(VERIFIED_HOURS))
def test_geometric_hours_match_the_verification_run(geometric_table, limit):
    for lat, hours in VERIFIED_HOURS[limit].items():
        got = hours_up_to(geometric_table[LATS.index(lat)], TABLE_EDGE[limit])
        assert got == pytest.approx(hours, rel=0.03), (lat, limit)


def test_refraction_adds_hours_within_a_looser_bound(geometric_table, apparent_table):
    for lat, hours in VERIFIED_HOURS[5.5].items():
        i = LATS.index(lat)
        got = hours_up_to(apparent_table[i], 5.55)
        assert got > hours_up_to(geometric_table[i], 5.55)
        assert got == pytest.approx(hours, rel=0.15), lat
    # verification run: 458 h in (0, 2.1] at 67N without refraction, about 549 h with it
    assert hours_up_to(apparent_table[LATS.index(67.0)], 2.08) == pytest.approx(549, rel=0.05)


def test_last_bin_sums_fifteen_days(geometric_table):
    equator = geometric_table[0].sum(axis=(1, 2))
    assert equator[35] / equator[34] == pytest.approx(1.5, rel=0.03)


@pytest.mark.parametrize("lat, first_day, refraction", [
    (60.0, 81, False),   # equinox dawn and dusk
    (78.2, 41, True),    # the Sun comes back in mid February: one day early or late changes every cell
    (70.0, 151, True),   # midnight Sun low in the north
    (-69.0, 351, True),  # midnight Sun low in the south, in the fifteen-day last bin
])
def test_table_matches_a_fine_slow_count_cell_by_cell(lat, first_day, refraction):
    b = sun.bin_index(first_day)
    days = [d for d in range(1, 366) if sun.bin_index(d) == b]
    assert days[0] == first_day
    slow = slow_count(lat, days, refraction)
    assert slow.sum() > 500.0
    table = sun.band_minutes_table([lat], refraction=refraction, year_phases=1)[0, b]
    # Minutes per bin of ten (or fifteen) days. The Sun crosses a sector border at nearly the same clock
    # time every day near a solstice, so giving each whole time step to one sector piles up an error
    # of up to a minute a day in the same cells (11 minutes at 69S before the steps were split).
    assert np.abs(table.sum(axis=0) - slow.sum(axis=0)).max() <= 1.0   # each elevation bin
    assert np.abs(table.sum(axis=1) - slow.sum(axis=1)).max() <= 1.0   # each azimuth sector
    assert np.abs(table - slow).max() <= 1.0                           # each cell


@pytest.mark.parametrize("lat", [0.0, 50.0, 60.0, 67.0, 69.0, -69.0])
def test_table_hours_match_the_hour_angle_formula(geometric_table, apparent_table, lat):
    # An independent route: no time steps, one declination per day, and for the apparent Sun
    # Bennett's refraction formula turned round instead of Saemundsson's.
    i = LATS.index(lat)
    for limit in (2.08, 5.55, 6.11, 7.59):
        geometric = hour_angle_hours(lat, 0.0, limit)
        apparent = hour_angle_hours(lat, bennett_true_elevation_deg(0.0), bennett_true_elevation_deg(limit))
        assert hours_up_to(geometric_table[i], limit) == pytest.approx(geometric, rel=0.004), limit
        assert hours_up_to(apparent_table[i], limit) == pytest.approx(apparent, rel=0.004), limit


def test_sector_minutes_do_not_depend_on_the_step(apparent_table):
    # hours per year in each azimuth sector under 7.59 degrees: two-minute steps against six-second steps
    fine = sun.band_minutes_table(LATS, step_minutes=0.1, year_phases=1)
    by_sector = apparent_table.sum(axis=(1, 3)) / 60.0
    fine_by_sector = fine.sum(axis=(1, 3)) / 60.0
    assert np.abs(by_sector - fine_by_sector).max() <= 0.02


def test_table_handles_no_latitudes_and_refuses_steps_that_do_not_fill_the_day():
    assert sun.band_minutes_table([], year_phases=1).shape == (0, sun.N_BINS, sun.AZ_SECTORS, 9)
    assert sun.band_minutes_table(np.array([67.0]), step_minutes=0.5, year_phases=1).shape == (1, sun.N_BINS, sun.AZ_SECTORS, 9)
    with pytest.raises(ValueError):
        sun.band_minutes_table([67.0], step_minutes=7, year_phases=1)   # 1440 / 7 is not whole: the last step would run past midnight
    with pytest.raises(ValueError):
        sun.longest_stretch_hours_table([67.0], [5.55], step_minutes=7, year_phases=1)


def test_two_minute_steps_agree_with_fine_steps(geometric_table, apparent_table):
    # Sunrise is at 06:00 solar time every day at the equator: counting whole two-minute
    # samples at fixed clock times loses 3.5% of the hours under 2.08 degrees there.
    # Sharing each step between the elevation bins it crosses does not.
    for table, refraction in ((geometric_table, False), (apparent_table, True)):
        fine = sun.band_minutes_table(LATS, step_minutes=0.25, refraction=refraction, year_phases=1)
        for limit in (2.08, 5.55, 7.59):
            n = sum(1 for upper in sun.ELEV_EDGES_DEG[1:] if upper <= limit + 0.005)
            by_bin = table[:, :, :, :n].sum(axis=(2, 3))
            fine_by_bin = fine[:, :, :, :n].sum(axis=(2, 3))
            assert np.abs(by_bin - fine_by_bin).max() <= 1.5  # minutes in any ten-day bin
            assert np.allclose(by_bin.sum(axis=1), fine_by_bin.sum(axis=1), rtol=0.001)  # per year


def test_midnight_sun_at_69N_falls_in_the_northern_sectors(geometric_table, apparent_table):
    elev, _ = sun.elevation_azimuth(69.0, 175, np.arange(0.0, 24.0, 0.25))
    assert elev.min() > 0.0  # the Sun never sets in late June
    for table in (geometric_table, apparent_table):
        late_june = table[LATS.index(69.0), sun.bin_index(175)]
        assert late_june[0].sum() > 0.0 and late_june[35].sum() > 0.0
        assert late_june[SOUTH_SECTORS].sum() == 0.0
        assert late_june[NORTH_SECTORS].sum() / 60.0 == pytest.approx(10 * 5.8, rel=0.15)  # hours under 7.59


def test_southern_mirror_at_69S_in_late_december(geometric_table, apparent_table):
    elev, _ = sun.elevation_azimuth(-69.0, 358, np.arange(0.0, 24.0, 0.25))
    assert elev.min() > 0.0
    for table in (geometric_table, apparent_table):
        late_december = table[LATS.index(-69.0), sun.bin_index(358)]
        assert late_december[17].sum() > 0.0 and late_december[18].sum() > 0.0
        assert late_december[NORTH_SECTORS].sum() == 0.0
        assert late_december[SOUTH_SECTORS].sum() / 60.0 == pytest.approx(15 * 5.8, rel=0.15)


# Longest continuous stretch

def test_longest_stretch_by_day_matches_the_verification_run():
    # geometric, 5.5 degree limit: about 5.7 h at 67N and 5.9 h at 69N on the best day
    assert sun.longest_stretch_hours_by_day(67.0, [5.5], refraction=False).max() == pytest.approx(5.7, rel=0.03)
    assert sun.longest_stretch_hours_by_day(69.0, [5.5], refraction=False).max() == pytest.approx(5.9, rel=0.03)


def test_a_stretch_through_midnight_counts_as_one():
    by_day = sun.longest_stretch_hours_by_day(69.0, [2.08, 7.59], refraction=False)
    assert by_day.shape == (365, 2)
    # 21 June: under 7.59 degrees from about 21:07 to 02:53, never under 2.08 (lowest 2.44)
    assert by_day[JUNE_SOLSTICE - 1, 1] == pytest.approx(5.77, abs=0.15)
    assert by_day[JUNE_SOLSTICE - 1, 0] == 0.0


def test_longest_stretch_table():
    limits = [2.08, 5.55, 7.59]
    lats = [0.0, 67.0, 75.0, 89.0]
    table = sun.longest_stretch_hours_table(lats, limits, refraction=False, year_phases=1)
    assert table.shape == (4, sun.N_BINS, 3) and table.dtype == np.float32
    # equator: the Sun climbs through 5.55 degrees in 22 to 24 minutes on every day of the year
    assert table[0, :, 1].min() > 0.33 and table[0, :, 1].max() < 0.44
    assert np.all(table[2, 35] == 0.0)   # polar night at 75N in late December
    assert table[3, 8, 2] == 24.0        # 89N in late March: up all day and never above 7.59
    assert np.all(table[..., 0] <= table[..., 1]) and np.all(table[..., 1] <= table[..., 2])
    by_day = sun.longest_stretch_hours_by_day(67.0, limits, refraction=False)
    assert table[1, 16, 1] == pytest.approx(np.median(by_day[160:170, 1]))


def test_longest_stretch_ends_at_the_horizon_and_at_the_limit():
    # Equator at the March equinox: the Sun climbs 15 degrees an hour straight up, so the stretch is
    # the height of the band over 15. Apparent band (0, 5.55] is true (-0.574, 5.399].
    geometric = sun.longest_stretch_hours_by_day(0.0, [2.08, 5.55], refraction=False, step_minutes=0.25)[79]
    assert geometric[0] == pytest.approx(2.08 / 15.0, abs=0.006)
    assert geometric[1] == pytest.approx(5.55 / 15.0, abs=0.006)
    apparent = sun.longest_stretch_hours_by_day(0.0, [5.55], step_minutes=0.25)[79, 0]
    lowest, highest = bennett_true_elevation_deg(0.0), bennett_true_elevation_deg(5.55)
    assert apparent == pytest.approx((highest - lowest) / 15.0, abs=0.006)
    assert apparent > geometric[1] + 0.02


def test_longest_stretch_follows_the_calendar_day():
    # 78.2N as the Sun comes back: under 7.59 degrees all day, so the stretch is the day length,
    # which grows by about 25 minutes a day. A table one day early or late would be 0.4 h off.
    by_day = sun.longest_stretch_hours_by_day(78.2, [7.59], refraction=False)[:, 0]
    assert by_day[47] == 0.0 and by_day[49] > 0.0   # day 48 still dark, day 50 not
    for doy in range(51, 61):
        assert sun.noon_elevation_deg(78.2, doy) < 7.59
        assert by_day[doy - 1] == pytest.approx(day_length_hours(78.2, doy), abs=0.1)
    assert by_day[60 - 1] - by_day[51 - 1] > 3.0
    table = sun.longest_stretch_hours_table([78.2], [7.59], refraction=False, year_phases=1)
    expected = float(np.median([day_length_hours(78.2, doy) for doy in range(51, 61)]))
    assert table[0, sun.bin_index(51), 0] == pytest.approx(expected, abs=0.1)
    for b in range(sun.N_BINS):
        days = [d for d in range(1, 366) if sun.bin_index(d) == b]
        assert table[0, b, 0] == pytest.approx(np.median(by_day[days[0] - 1:days[-1]]))


def slow_longest_stretch_hours(lat: float, limit: float, day_of_year: int, refraction: bool, step: float = 2.0) -> float:
    """Longest stretch in (0, limit] that touches a day: walk the samples from the day before to the day after."""
    hours = (np.arange(0.0, 1440.0, step) + step / 2) / 60.0
    in_band = []
    for doy in (day_of_year - 1, day_of_year, day_of_year + 1):
        elev, _ = sun.elevation_azimuth(lat, doy, hours)
        if refraction:
            elev = sun.apparent_elevation_deg(elev)
        in_band.extend(bool(x) for x in (elev > 0.0) & (elev <= limit))
    n, best, start = len(hours), 0, None
    for j, ok in enumerate(in_band + [False]):
        if ok and start is None:
            start = j
        elif not ok and start is not None:
            if start < 2 * n and j > n:   # some of it falls in the middle day
                best = max(best, j - start)
            start = None
    return min(best, n) * step / 60.0


@pytest.mark.parametrize("lat, limit, refraction, days", [
    (67.0, 5.55, True, range(150, 166)),    # the first nights of midnight Sun
    (72.0, 5.55, False, range(125, 140)),   # the night stretch shrinks by minutes a day
    (-85.0, 7.59, True, range(268, 284)),   # near the pole the Sun climbs in a spiral: a day does not close on itself
    (-69.0, 7.59, True, [364, 365, 1, 2]),  # southern midnight Sun: the night of day 365 runs into day 1
])
def test_longest_stretch_joins_each_night_to_the_next_morning(lat, limit, refraction, days):
    by_day = sun.longest_stretch_hours_by_day(lat, [limit], refraction=refraction)[:, 0]
    slow = [slow_longest_stretch_hours(lat, limit, doy, refraction) for doy in days]
    assert max(slow) > 5.0
    for doy, expected in zip(days, slow):
        assert by_day[doy - 1] == pytest.approx(expected, abs=0.04), doy   # one two-minute step


def test_longest_stretch_counts_the_night_for_both_days_it_touches():
    # 67N without refraction: the Sun first stays up through the night of day 161 to 162 (0.06 degrees
    # up at midnight; 0.02 degrees down the night before), under 5.5 degrees from about 21:10 to 02:50.
    # That one stretch belongs to both days; day 160 still has two short ones, at dusk and at dawn.
    assert sun.elevation_azimuth(67.0, 160, 24.0)[0] < 0.0 < sun.elevation_azimuth(67.0, 161, 24.0)[0]
    by_day = sun.longest_stretch_hours_by_day(67.0, [5.5], refraction=False)[:, 0]
    assert by_day[160 - 1] == pytest.approx(2.7, abs=0.1)
    assert by_day[161 - 1] == pytest.approx(5.67, abs=0.05)
    assert by_day[162 - 1] == pytest.approx(5.67, abs=0.05)
    # a stretch longer than a day counts as 24 hours for every day it touches
    polar = sun.longest_stretch_hours_by_day(89.5, [7.59])[:, 0]
    assert polar.max() == 24.0 and np.count_nonzero(polar == 24.0) > 20


def test_longest_stretch_with_no_limits_or_no_latitudes():
    assert sun.longest_stretch_hours_by_day(67.0, []).shape == (365, 0)
    assert sun.longest_stretch_hours_table([67.0, 69.0], [], year_phases=1).shape == (2, sun.N_BINS, 0)
    assert sun.longest_stretch_hours_table([], [5.55], year_phases=1).shape == (0, sun.N_BINS, 1)


def test_refraction_lifts_the_midwinter_sun_into_view_at_67N():
    late_december = sun.bin_index(DEC_SOLSTICE)
    assert sun.longest_stretch_hours_table([67.0], [5.55], refraction=False, year_phases=1)[0, late_december, 0] == 0.0
    assert sun.longest_stretch_hours_table([67.0], [5.55], year_phases=1)[0, late_december, 0] > 0.5


# All-day low-Sun days (apparent noon Sun above the horizon and at or below the limit)

def test_noon_sun_at_65N_on_solstice_matches_lunar_pole():
    assert sun.noon_elevation_deg(65.0, DEC_SOLSTICE) == pytest.approx(1.56, abs=0.1)


def test_all_day_low_sun_days_use_the_apparent_sun():
    # At 67N the Sun's centre is 0.4 degrees under the horizon at noon on the December solstice,
    # and refraction lifts it into view.
    days = sun.all_day_low_sun_days(67.0, 5.0)
    assert DEC_SOLSTICE in days
    assert DEC_SOLSTICE not in sun.all_day_low_sun_days(67.0, 5.0, refraction=False)
    assert len(days) in (75, 76) and len(sun.windows(days)) == 1
    assert days == sun.low_sun_days(67.0, 5.0)
    assert all(type(d) is int for d in days)


def test_arctic_circle_has_72_low_sun_days_in_one_window():
    days = sun.low_sun_days(66.5, max_elev_deg=5.0)
    assert len(days) in (71, 72)
    (start, end), = sun.windows(days)
    assert start == 320 and end in (25, 26)  # 16 Nov to 26 Jan


def test_reykjavik_and_fairbanks():
    assert len(sun.low_sun_days(64.1, 5.0)) in (49, 50)
    assert len(sun.low_sun_days(64.8, 5.0)) in (56, 57)


def test_longyearbyen_has_two_short_windows():
    days = sun.low_sun_days(78.2, 5.0)
    assert 28 <= len(days) <= 30
    spring, autumn = sun.windows(days)
    assert spring[0] in (47, 48) and spring[1] == 61       # 16 Feb to 2 Mar
    assert autumn[0] in (284, 285) and autumn[1] in (298, 299)  # 11 Oct to 25 Oct


def test_mistastin_never_gets_low_sun():
    assert sun.low_sun_days(55.9, 5.0) == []
    lowest = min(sun.noon_elevation_deg(55.9, d) for d in range(1, 366))
    assert lowest == pytest.approx(10.7, abs=0.2)


def test_threshold_latitude_is_about_61_75():
    assert sun.low_sun_days(61.7, 5.0) == []
    assert len(sun.low_sun_days(61.8, 5.0)) in (8, 9)


def test_southern_window_is_a_few_days_longer_than_northern():
    # Earth moves slowest near aphelion in July, so the Sun lingers at high
    # northern declination: about 14 May to 29 Jul, 76 days against 72.
    days = sun.low_sun_days(-66.5, 5.0)
    assert len(days) in (76, 77)
    (start, end), = sun.windows(days)
    assert start in (134, 135) and end in (209, 210)


def test_lunar_sun_limit():
    assert sun.lunar_max_sun_elevation_deg(-90.0) == pytest.approx(1.54)
    assert sun.lunar_max_sun_elevation_deg(-84.0) == pytest.approx(7.54)


def test_labels():
    assert sun.doy_to_label(320) == "16 Nov"
    assert sun.doy_to_label(27) == "27 Jan"


# --- version 3, decision 12: long spells are counted per day, not per ten-day bin ---

LONG_LIMITS = [2.08, 5.55, 6.11, 7.59]
LONG_LATS = [0.0, 45.0, 60.0, 64.0, 67.0, 70.0, 78.2, 89.5, -70.0]
BINS_USED = {2.08: 4, 5.55: 7, 6.11: 8, 7.59: 9}   # elevation bins whose upper edge is at most the limit


@pytest.fixture(scope="module")
def long_table():
    """Minutes inside spells of two hours or more, one-minute steps: [limits, latitudes, 36, 36, 9]."""
    return sun.long_band_minutes_table(LONG_LATS, LONG_LIMITS, year_phases=1)


@pytest.fixture(scope="module")
def minute_table():
    """All hours, at the same one-minute step as the long table."""
    return sun.band_minutes_table(LONG_LATS, step_minutes=1, year_phases=1)


def made_up_track(days: int, in_band_hours: dict, inside: float = 3.0, outside: float = -5.0) -> np.ndarray:
    """Elevation at the 25 hour marks (0 to 24) of each day: `inside` at the marks listed per day, else `outside`."""
    elev = np.full((days, 25), outside)
    for day, marks in in_band_hours.items():
        elev[day, list(marks)] = inside
    assert all(elev[d, 24] == elev[(d + 1) % days, 0] for d in range(days))   # midnight is the same moment for both days
    return elev


def test_long_table_has_one_layer_per_limit_laid_out_like_the_all_hours_table(long_table):
    assert long_table.shape == (4, len(LONG_LATS), sun.N_BINS, sun.AZ_SECTORS, 9)
    assert long_table.dtype == np.float32
    for j, limit in enumerate(LONG_LIMITS):
        assert np.all(long_table[j][..., BINS_USED[limit]:] == 0.0), limit   # nothing above the limit
    assert long_table[1, LONG_LATS.index(70.0)].sum() > 60.0 * 500.0             # 70N has hundreds of such hours a year
    assert sun.long_band_minutes_table([], LONG_LIMITS, year_phases=1).shape == (4, 0, sun.N_BINS, sun.AZ_SECTORS, 9)
    assert sun.long_band_minutes_table([70.0], [], year_phases=1).shape == (0, 1, sun.N_BINS, sun.AZ_SECTORS, 9)
    with pytest.raises(ValueError):
        sun.long_band_minutes_table([70.0], [5.55], step_minutes=7, year_phases=1)


def test_with_no_minimum_the_long_table_is_the_all_hours_table_in_the_bins_the_limit_uses(minute_table):
    every = sun.long_band_minutes_table(LONG_LATS, LONG_LIMITS, min_stretch_h=0.0, year_phases=1)
    for j, limit in enumerate(LONG_LIMITS):
        n = BINS_USED[limit]
        assert np.array_equal(every[j][..., :n], minute_table[..., :n]), limit
        assert np.all(every[j][..., n:] == 0.0), limit
    two_minute = sun.long_band_minutes_table([67.0, -70.0], [5.55], min_stretch_h=0.0, step_minutes=2, year_phases=1)
    assert np.array_equal(two_minute[0][..., :7], sun.band_minutes_table([67.0, -70.0], year_phases=1)[..., :7])
    geometric = sun.long_band_minutes_table([67.0], [7.59], min_stretch_h=0.0, refraction=False, year_phases=1)
    assert np.array_equal(geometric[0], sun.band_minutes_table([67.0], step_minutes=1, refraction=False, year_phases=1))


def test_the_long_table_never_exceeds_the_all_hours_table(long_table, minute_table):
    for j, limit in enumerate(LONG_LIMITS):
        assert np.all(long_table[j] <= minute_table), limit
    for hours in (1.0, 3.0):
        other = sun.long_band_minutes_table(LONG_LATS, LONG_LIMITS, min_stretch_h=hours, year_phases=1)
        assert np.all(other <= minute_table[None])
        if hours > 2.0:
            assert np.all(other <= long_table)        # a longer minimum never adds minutes
        else:
            assert np.all(other >= long_table)
    assert np.any(long_table[1] < minute_table)       # and the rule does take something away


def test_the_equator_has_no_two_hour_spell_under_any_limit(long_table, minute_table):
    # The Sun climbs 15 degrees an hour there: it is through the widest band in half an hour.
    i = LONG_LATS.index(0.0)
    assert minute_table[i].sum() > 60.0 * 300.0
    assert np.all(long_table[:, i] == 0.0)
    assert np.all(long_table[:, LONG_LATS.index(45.0)] == 0.0)


def brute_force_long_minutes(lat: float, limit: float, b: int, min_minutes: int = 120) -> np.ndarray:
    """Minutes of one ten-day bin inside long spells, [sectors, elevation bins], by walking the year minute by minute.

    Its own route: one elevation and azimuth call per minute (taken at the middle of the minute), its own
    search for unbroken runs of minutes in (0, limit], from the day before the bin to the day after it.
    """
    days = [d for d in range(1, 366) if sun.bin_index(d) == b]
    walk = [(days[0] - 2) % 365 + 1] + days + [days[-1] % 365 + 1]
    samples = []
    for doy in walk:
        for minute in range(1440):
            elev, az = sun.elevation_azimuth(lat, doy, (minute + 0.5) / 60.0)
            samples.append((doy, sun.apparent_elevation_deg(elev), az))
    counted = np.zeros((sun.AZ_SECTORS, 9))
    k = 0
    while k < len(samples):
        end = k
        while end < len(samples) and 0.0 < samples[end][1] <= limit:
            end += 1
        if end - k >= min_minutes:
            if any(doy in days for doy, _, _ in samples[k:end]):
                assert 0 < k and end < len(samples)   # the walk holds the whole of every spell that touches the bin
            for doy, elev, az in samples[k:end]:
                if doy in days:
                    e = max(i for i in range(9) if sun.ELEV_EDGES_DEG[i] < elev)
                    counted[int(az // 10.0) % sun.AZ_SECTORS, e] += 1.0
        k = max(end, k + 1)
    return counted


@pytest.mark.parametrize("lat, limit, b", [
    (70.0, 5.55, 17),    # midsummer: one spell a night around midnight, about 3.6 h, under 2 h on each side of midnight
    (64.0, 5.55, 35),    # midwinter: the whole short day is one spell, in the fifteen-day last bin
    (-70.0, 5.55, 0),    # southern midnight Sun: the spell of the night of 31 December runs on into 1 January
    (-70.0, 5.55, 35),
])
def test_long_table_equals_a_brute_force_walk_minute_by_minute(long_table, lat, limit, b):
    slow = brute_force_long_minutes(lat, limit, b)
    table = long_table[LONG_LIMITS.index(limit), LONG_LATS.index(lat), b].astype(float)
    days = 15 if b == 35 else 10
    assert slow.sum() > 120.0 * days                     # a spell of two hours or more on every day of the bin
    assert table.sum() == pytest.approx(slow.sum(), abs=days)        # a spell's two ends are each read to half a minute
    # The slow walk gives a whole minute to one sector and one elevation bin; near a solstice the Sun crosses
    # the same border at the same clock time day after day, so a cell can gather up to half a minute a day at
    # each of its borders (measured: at most 6.3 minutes in a cell, 7.0 in a sector, 3.4 in an elevation bin).
    assert np.abs(table - slow).max() <= 0.75 * days
    assert np.abs(table.sum(axis=0) - slow.sum(axis=0)).max() <= 0.5 * days          # each elevation bin
    assert np.abs(table.sum(axis=1) - slow.sum(axis=1)).max() <= 0.75 * days         # each azimuth sector
    assert np.count_nonzero(table) >= np.count_nonzero(slow) >= 8                    # spread over sectors and elevation bins


def test_the_night_spell_at_70N_is_long_only_because_midnight_does_not_cut_it(long_table, minute_table):
    # 21 June at 70N: under 5.55 degrees from about 22:12 to 01:48. Each side of midnight is under two hours.
    hours = np.arange(0.0, 24.0, 1.0 / 60.0) + 1.0 / 120.0
    elev = sun.apparent_elevation_deg(sun.elevation_azimuth(70.0, JUNE_SOLSTICE, hours)[0])
    low = (elev > 0.0) & (elev <= 5.55)
    assert 60 < np.count_nonzero(low[:720]) < 120 and 60 < np.count_nonzero(low[720:]) < 120
    i = LONG_LATS.index(70.0)
    assert long_table[1, i, 17].sum() == pytest.approx(minute_table[i, 17, :, :7].sum(), abs=1e-3)
    assert long_table[1, i, 17].sum() > 10 * 180.0


def test_steps_in_a_spell_through_midnight_stay_in_their_own_day():
    # Hourly steps. In the band at 22:00, 23:00, 24:00 of day 0 and 00:00, 01:00, 02:00 of day 1; climbing in from
    # -5 to 3 degrees takes the last 3/8 of the hour before (22.5 minutes), and the same on the way out.
    elev = made_up_track(3, {0: [22, 23, 24], 1: [0, 1, 2, 10, 11]})
    keep = sun.steps_in_long_spells(elev, 5.55, min_minutes=240.0, step_minutes=60.0)
    assert keep.shape == (3, 24) and keep.dtype == bool
    assert np.flatnonzero(keep[0]).tolist() == [21, 22, 23]      # the evening of day 0, in day 0
    assert np.flatnonzero(keep[1]).tolist() == [0, 1, 2]         # the morning of day 1, in day 1
    assert not keep[2].any()
    # the whole spell lasts 4 h 45 min; the second one (10:00 to 11:00, with its ends) 1 h 45 min
    assert sun.steps_in_long_spells(elev, 5.55, 285.0, 60.0).sum() == 6
    assert sun.steps_in_long_spells(elev, 5.55, 286.0, 60.0).sum() == 0
    assert np.flatnonzero(sun.steps_in_long_spells(elev, 5.55, 105.0, 60.0)[1]).tolist() == [0, 1, 2, 9, 10, 11]
    assert sun.steps_in_long_spells(elev, 5.55, 0.0, 60.0).sum() == 9


def test_a_spell_across_the_year_end_is_one_spell():
    # In the band from 23:00 of the last day to 01:00 of the first: 2 h 45 min with its ends, 82.5 minutes in each year.
    elev = made_up_track(4, {3: [23, 24], 0: [0, 1]})
    keep = sun.steps_in_long_spells(elev, 5.55, min_minutes=120.0, step_minutes=60.0)
    assert np.flatnonzero(keep[3]).tolist() == [22, 23] and np.flatnonzero(keep[0]).tolist() == [0, 1]
    assert keep.sum() == 4
    assert sun.steps_in_long_spells(elev, 5.55, 165.0, 60.0).sum() == 4
    assert sun.steps_in_long_spells(elev, 5.55, 166.0, 60.0).sum() == 0


def test_a_spell_ends_where_the_sun_leaves_the_band_at_the_top_or_at_the_horizon():
    # Two hours in the band, one mark above the limit, two more hours in the band: two spells, not one.
    elev = made_up_track(2, {0: [5, 6, 7, 9, 10, 11]})
    elev[0, 8] = 9.0
    up = (5.55 - 3.0) / 6.0 * 60.0      # minutes of the hour from 3 to 9 degrees spent at or below 5.55
    each = 22.5 + 120.0 + up
    assert sun.steps_in_long_spells(elev, 5.55, each - 0.01, 60.0).sum() == 8
    assert sun.steps_in_long_spells(elev, 5.55, each + 0.01, 60.0).sum() == 0
    assert sun.steps_in_long_spells(elev, 9.5, 2 * 22.5 + 360.0 - 0.01, 60.0).sum() == 8    # under a higher limit it is one
    # a Sun that just touches the limit stays inside (the band is 0 < elevation <= limit) ...
    at_limit = made_up_track(2, {0: [5, 6, 7, 8, 9]})
    at_limit[0, 7] = 5.55
    assert sun.steps_in_long_spells(at_limit, 5.55, 285.0, 60.0).sum() == 6
    at_limit[0, 7] = 5.56
    assert sun.steps_in_long_spells(at_limit, 5.55, 143.0, 60.0).sum() == 0     # ... a hair above it cuts the spell in two
    assert sun.steps_in_long_spells(at_limit, 5.55, 142.0, 60.0).sum() == 6
    # ... and one that just touches the horizon is cut there
    on_horizon = made_up_track(2, {0: [5, 6, 8, 9]})
    on_horizon[0, 7] = 0.0
    assert sun.steps_in_long_spells(on_horizon, 5.55, 143.0, 60.0).sum() == 0
    assert sun.steps_in_long_spells(on_horizon, 5.55, 142.5, 60.0).sum() == 6
    assert sun.steps_in_long_spells(made_up_track(2, {0: [5, 6, 7]}, inside=0.0), 5.55, 0.0, 60.0).sum() == 0


def test_a_sun_that_stays_in_the_band_for_days_counts_every_minute(long_table, minute_table):
    # Made up: in the band at every mark of two days out of four.
    elev = made_up_track(4, {0: [24], 1: range(25), 2: range(25), 3: [0]})
    keep = sun.steps_in_long_spells(elev, 5.55, 120.0, 60.0)
    assert keep[1].all() and keep[2].all() and keep.sum() == 50      # and the two hours of climbing in and out
    # The real Sun at 89.5N under 7.59 degrees: it circles in the band for days on end in late March.
    i = LONG_LATS.index(89.5)
    full = [b for b in range(sun.N_BINS) if abs(minute_table[i, b].sum() - 14400.0) < 0.01]
    assert 8 in full                                                 # 22 to 31 March: all ten days, every minute
    for limit_index in (3,):
        assert long_table[limit_index, i, 8].sum() == pytest.approx(14400.0, abs=0.01)
    assert np.array_equal(long_table[3, i], minute_table[i])         # there every low-Sun minute of the year is in a long spell


def test_one_and_two_minute_steps_give_nearly_the_same_long_table(long_table):
    coarse = sun.long_band_minutes_table(LONG_LATS, LONG_LIMITS, step_minutes=2, year_phases=1)
    by_bin = long_table.sum(axis=(3, 4)) / 60.0          # hours per ten-day bin
    coarse_by_bin = coarse.sum(axis=(3, 4)) / 60.0
    assert np.abs(by_bin - coarse_by_bin).max() <= 0.05
    assert np.abs(by_bin.sum(axis=2) - coarse_by_bin.sum(axis=2)).max() <= 0.2   # hours a year


def test_longest_spell_of_the_year():
    best = sun.longest_spell_hours([0.0, 64.0, 70.0, 89.5], [2.08, 5.55, 7.59], year_phases=1)
    assert best.shape == (4, 3)
    assert 0.33 < best[0, 1] < 0.44                      # equator: through 5.55 degrees in 22 to 24 minutes
    assert np.all(best[0] < 1.0)
    assert best[3, 2] > 10 * 24.0                        # 89.5N: in the band for days on end, not capped at a day
    assert np.all(best[:, 0] <= best[:, 1]) and np.all(best[:, 1] <= best[:, 2])
    # 64N in midwinter: the whole day, sunrise to sunset, is under 5.55 degrees
    by_day = sun.longest_stretch_hours_by_day(64.0, [5.55], step_minutes=1)[:, 0]
    assert best[1, 1] == pytest.approx(by_day.max(), abs=0.04)
    assert sun.longest_spell_hours([], [5.55], year_phases=1).shape == (0, 1)


def test_the_long_table_is_empty_exactly_where_no_spell_reaches_the_minimum():
    lats = [50.0, 55.0, 58.0, 60.0, 62.0, 64.0]
    best = sun.longest_spell_hours(lats, LONG_LIMITS, year_phases=1)
    table = sun.long_band_minutes_table(lats, LONG_LIMITS, year_phases=1)
    has_hours = table.sum(axis=(2, 3, 4)) > 0.0          # [limits, latitudes]
    assert np.array_equal(has_hours, (best >= 2.0).T)
    assert has_hours.any() and not has_hours.all()


# --- added in the version 3 review: breakages of the code that the tests above let through ---

def test_a_sun_that_never_leaves_the_band_is_one_spell_as_long_as_the_year():
    elev = np.full((3, 25), 3.0)                 # a made-up year of three days, in the band at every moment
    where, length = sun._spells(elev, 5.55, 60.0)
    assert where.tolist() == list(range(72)) and np.all(length == 72 * 60.0)
    assert sun.steps_in_long_spells(elev, 5.55, 72 * 60.0, 60.0).all()
    assert not sun.steps_in_long_spells(elev, 5.55, 72 * 60.0 + 1.0, 60.0).any()


def test_at_the_year_end_the_sun_must_be_in_the_band_on_both_sides_of_midnight():
    # The table's year closes on itself, so its last moment and its first are not quite the same Sun.
    elev = made_up_track(3, {2: [22, 23, 24], 0: [0, 1, 2]})
    assert sun.steps_in_long_spells(elev, 5.55, 285.0, 60.0).sum() == 6       # one spell of 4 h 45 min across the year end
    old_year_above = elev.copy()
    old_year_above[2, 24] = 9.0     # the old year ends above the limit: 22.5 + 60 + 25.5 minutes before, 142.5 after
    assert sun.steps_in_long_spells(old_year_above, 5.55, 143.0, 60.0).sum() == 0
    assert np.flatnonzero(sun.steps_in_long_spells(old_year_above, 5.55, 142.0, 60.0)[0]).tolist() == [0, 1, 2]
    assert sun.steps_in_long_spells(old_year_above, 5.55, 108.0, 60.0).sum() == 6
    new_year_above = elev.copy()
    new_year_above[0, 0] = 9.0      # the new year starts above the limit: 142.5 minutes before, 25.5 + 60 + 22.5 after
    assert sun.steps_in_long_spells(new_year_above, 5.55, 143.0, 60.0).sum() == 0
    assert np.flatnonzero(sun.steps_in_long_spells(new_year_above, 5.55, 142.0, 60.0)[2]).tolist() == [21, 22, 23]


def test_the_longest_spell_is_read_at_one_minute_steps_unless_asked_otherwise():
    lats, limits = [60.65, 64.0], [5.55]
    default = sun.longest_spell_hours(lats, limits, year_phases=1)
    assert np.array_equal(default, sun.longest_spell_hours(lats, limits, step_minutes=1, year_phases=1))
    coarse = sun.longest_spell_hours(lats, limits, step_minutes=2, year_phases=1)
    assert not np.array_equal(default, coarse) and np.abs(default - coarse).max() < 0.001   # a tenth of a second or so
    assert default[0, 0] == pytest.approx(2.0038, abs=0.0002)     # 60.65N under 5.55 degrees: two hours and 14 seconds


# --- round 4: the tables are the mean over the phases of the leap cycle (calendars a quarter day apart) ---

PHASE_LATS = [60.0, 64.0, 67.0, 70.0, 75.0, 78.2, -70.0]
# The single-calendar tables as they stood before the phases were added (14 Nov 2026), one-minute steps.
SAVED_LONG_MINUTES_A_YEAR = [        # [limit][latitude]: minutes inside spells of two hours or more
    [0.00, 0.00, 10393.15, 5958.12, 4836.60, 5364.77, 5648.59],
    [0.00, 16734.81, 30991.27, 35338.26, 31675.76, 42862.54, 34585.47],
    [2946.97, 19318.64, 35302.65, 40758.32, 39061.97, 52644.66, 39904.50],
    [16772.23, 32598.36, 48560.59, 56880.07, 71034.96, 65677.46, 55799.62],
]
SAVED_LONG_MINUTES_BY_BIN = {        # (latitude, limit): minutes per ten-day bin
    (67.0, 2.08): [1235.86, 818.64, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1131.99, 1772.54,
                   1712.71, 1693.36, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1632.55, 395.5,
                   0.0],
    (75.0, 5.55): [0.0, 0.0, 0.0, 304.75, 2851.5, 3399.11, 490.3, 0.0, 0.0, 0.0, 123.16, 3173.68, 3491.93, 1947.3, 0.0,
                   0.0, 0.0, 0.0, 0.0, 0.0, 1029.6, 3061.66, 3639.27, 1152.41, 0.0, 0.0, 0.0, 0.0, 2129.8, 3597.1,
                   1284.18, 0.0, 0.0, 0.0, 0.0, 0.0],
}
SAVED_ALL_MINUTES_A_YEAR = [         # [limit][latitude]: every minute in the bins the limit uses
    [17442.98, 23465.14, 32700.77, 23854.66, 19827.67, 18749.74, 23755.46],
    [45624.01, 59985.49, 67449.51, 64685.70, 51593.25, 48157.71, 63673.42],
    [50631.46, 64729.73, 72250.70, 70044.87, 56956.15, 52973.67, 68919.32],
    [65355.57, 76537.25, 84298.06, 83271.08, 72029.64, 66047.27, 81878.00],
]
SAVED_LONGEST_SPELL_H = [[0.5784, 2.0038, 5.5581, 6.141], [1.019, 5.5138, 5.8003, 6.4044],     # 60.65N, 64N,
                         [3.8601, 6.2897, 6.6044, 7.3836], [3.8843, 6.2638, 6.5796, 7.3609]]   # 70N, 70S
SHIFT_LATS = [sign * lat for sign in (1, -1) for lat in (65.0, 67.0, 70.0, 75.0, 80.0)]
QUARTERS = [-0.375, -0.125, 0.125, 0.375]      # four calendars, in days from the single one: a quarter day apart
EIGHTHS = [k / 8 - 0.4375 for k in range(8)]   # the eight calendars of the default: an eighth of a day apart


def with_calendar_moved(monkeypatch, days: float, function, *args, **kwargs):
    """The result of a Sun function with the whole calendar moved by a part of a day."""
    with monkeypatch.context() as patch:
        patch.setattr(sun, "DAY_ZERO_FROM_J2000", sun.DAY_ZERO_FROM_J2000 + days)
        return function(*args, **kwargs)


def hours_a_year(table) -> np.ndarray:
    """A long-spell table [limits, latitudes, ...] as hours a year [limits, latitudes]."""
    return table.sum(axis=(2, 3, 4), dtype=float) / 60.0


def test_the_tables_take_eight_phases_of_the_leap_cycle_unless_told_otherwise():
    # The coordinator's decision of 14 Nov 2026 (evening): eight calendars, not four, so the long-spell hours meet the
    # brief's test of 1 percent or half an hour (see the tests of the calendar moved by a part of a day below).
    assert sun.YEAR_PHASES == 8
    assert sun._phase_offsets(1) == [0.0]                                  # one phase: the calendar as it stands
    assert sun._phase_offsets(4) == QUARTERS                               # centred on it: no drift between ten-day bins
    assert sun._phase_offsets(8) == pytest.approx(EIGHTHS)
    assert sun.phase_offsets() == pytest.approx(EIGHTHS) and sun.phase_offsets(4) == QUARTERS
    lats, limits = [67.0, -75.0], [2.08, 7.59]
    assert np.array_equal(sun.long_band_minutes_table(lats, limits), sun.long_band_minutes_table(lats, limits, year_phases=8))
    assert np.array_equal(sun.band_minutes_table(lats), sun.band_minutes_table(lats, year_phases=8))
    assert np.array_equal(sun.longest_spell_hours(lats, limits), sun.longest_spell_hours(lats, limits, year_phases=8))
    assert np.array_equal(sun.longest_stretch_hours_table(lats, limits),
                          sun.longest_stretch_hours_table(lats, limits, year_phases=8))
    for bad in (0, -1, 2.5):
        with pytest.raises(ValueError):
            sun.long_band_minutes_table(lats, limits, year_phases=bad)
        with pytest.raises(ValueError):
            sun.band_minutes_table(lats, year_phases=bad)


def test_one_year_phase_gives_the_single_calendar_tables_as_they_were_saved():
    long = sun.long_band_minutes_table(PHASE_LATS, LONG_LIMITS, year_phases=1)
    assert np.allclose(long.sum(axis=(2, 3, 4), dtype=float), SAVED_LONG_MINUTES_A_YEAR, rtol=0.0, atol=0.02)
    for (lat, limit), saved in SAVED_LONG_MINUTES_BY_BIN.items():
        by_bin = long[LONG_LIMITS.index(limit), PHASE_LATS.index(lat)].sum(axis=(1, 2), dtype=float)
        assert np.allclose(by_bin, saved, rtol=0.0, atol=0.02), (lat, limit)
    every = sun.band_minutes_table(PHASE_LATS, step_minutes=1, year_phases=1)
    for j, limit in enumerate(LONG_LIMITS):
        found = every[..., :BINS_USED[limit]].sum(axis=(1, 2, 3), dtype=float)
        assert np.allclose(found, SAVED_ALL_MINUTES_A_YEAR[j], rtol=0.0, atol=0.02), limit
    best = sun.longest_spell_hours([60.65, 64.0, 70.0, -70.0], LONG_LIMITS, year_phases=1)
    assert np.allclose(best, SAVED_LONGEST_SPELL_H, rtol=0.0, atol=0.0001)
    stretch = sun.longest_stretch_hours_table([67.0, 75.0], LONG_LIMITS, year_phases=1)
    assert stretch[0, 17].tolist() == pytest.approx([2.83333, 5.46667, 5.76667, 6.53333], abs=1e-4)
    assert stretch[1, 8].tolist() == pytest.approx([0.63333, 1.56667, 1.7, 2.1], abs=1e-4)
    assert float(stretch.sum(dtype=float)) == pytest.approx(547.88333, abs=1e-3)


def test_four_year_phases_are_the_mean_of_four_calendars_a_quarter_day_apart(monkeypatch):
    lats, limits = [67.0, 75.0, -70.0], [2.08, 5.55, 7.59]
    apart = [with_calendar_moved(monkeypatch, q, sun.long_band_minutes_table, lats, limits, year_phases=1) for q in QUARTERS]
    assert not np.array_equal(apart[0], apart[1])
    mean = np.mean([t.astype(float) for t in apart], axis=0)
    assert np.allclose(sun.long_band_minutes_table(lats, limits, year_phases=4), mean, rtol=0.0, atol=2e-3)   # float32 only
    three_hours = [with_calendar_moved(monkeypatch, q, sun.long_band_minutes_table, lats, limits, 3.0, 2, False, 1)
                   for q in QUARTERS]
    assert np.allclose(sun.long_band_minutes_table(lats, limits, 3.0, 2, False, year_phases=4),
                       np.mean([t.astype(float) for t in three_hours], axis=0), rtol=0.0, atol=2e-3)
    every = [with_calendar_moved(monkeypatch, q, sun.band_minutes_table, lats, 1, True, 1) for q in QUARTERS]
    assert np.allclose(sun.band_minutes_table(lats, 1, year_phases=4), np.mean([t.astype(float) for t in every], axis=0),
                       rtol=0.0, atol=2e-3)
    halves = [with_calendar_moved(monkeypatch, q, sun.long_band_minutes_table, lats, limits, year_phases=1)
              for q in (-0.25, 0.25)]
    assert np.allclose(sun.long_band_minutes_table(lats, limits, year_phases=2),
                       np.mean([t.astype(float) for t in halves], axis=0), rtol=0.0, atol=2e-3)
    spells = [with_calendar_moved(monkeypatch, q, sun.longest_spell_hours, lats, limits, year_phases=1) for q in QUARTERS]
    assert np.allclose(sun.longest_spell_hours(lats, limits, year_phases=4), np.mean(spells, axis=0), rtol=0.0, atol=1e-9)
    stretches = [with_calendar_moved(monkeypatch, q, sun.longest_stretch_hours_table, lats, limits, year_phases=1)
                 for q in QUARTERS]
    assert np.allclose(sun.longest_stretch_hours_table(lats, limits, year_phases=4),
                       np.mean([t.astype(float) for t in stretches], axis=0), rtol=0.0, atol=1e-5)


def test_the_default_tables_are_the_mean_of_eight_calendars_an_eighth_of_a_day_apart(monkeypatch):
    lats, limits = [67.0, -70.0], [2.08, 7.59]
    apart = [with_calendar_moved(monkeypatch, q, sun.long_band_minutes_table, lats, limits, year_phases=1) for q in EIGHTHS]
    assert np.allclose(sun.long_band_minutes_table(lats, limits), np.mean([t.astype(float) for t in apart], axis=0),
                       rtol=0.0, atol=2e-3)
    every = [with_calendar_moved(monkeypatch, q, sun.band_minutes_table, lats, 1, True, 1) for q in EIGHTHS]
    assert np.allclose(sun.band_minutes_table(lats, 1), np.mean([t.astype(float) for t in every], axis=0), rtol=0.0, atol=2e-3)
    spells = [with_calendar_moved(monkeypatch, q, sun.longest_spell_hours, lats, limits, year_phases=1) for q in EIGHTHS]
    assert np.allclose(sun.longest_spell_hours(lats, limits), np.mean(spells, axis=0), rtol=0.0, atol=1e-9)


def test_with_four_phases_a_calendar_moved_by_0_14_day_moves_the_long_hours_far_less(monkeypatch):
    # 0.14 day is the step from the middle of the leap cycle to the plain year 2026; one year differs from the next by 0.24.
    one = hours_a_year(sun.long_band_minutes_table(SHIFT_LATS, LONG_LIMITS, year_phases=1))
    one_moved = hours_a_year(with_calendar_moved(monkeypatch, 0.14, sun.long_band_minutes_table, SHIFT_LATS, LONG_LIMITS,
                                                 year_phases=1))
    four = hours_a_year(sun.long_band_minutes_table(SHIFT_LATS, LONG_LIMITS, year_phases=4))
    four_moved = hours_a_year(with_calendar_moved(monkeypatch, 0.14, sun.long_band_minutes_table, SHIFT_LATS, LONG_LIMITS,
                                                  year_phases=4))
    assert four.min() > 50.0                                      # every one of the forty has long spells
    change_one, change_four = np.abs(one_moved - one), np.abs(four_moved - four)
    # A single calendar: up to 8 hours and 10 percent (75N and 65N under 2.08 degrees).
    assert 7.5 < change_one.max() < 8.5 and (change_one / one).max() > 0.06
    assert np.count_nonzero(change_one > np.maximum(1.0, 0.02 * one)) >= 6
    # Four phases: every one within 2 percent or 1 hour, whichever is larger (the tolerance of the count check) ...
    assert np.all(change_four <= np.maximum(1.0, 0.02 * four))
    assert change_four.max() < 2.1 and (change_four / four).max() < 0.02       # measured: 2.02 h and 1.87 percent
    assert change_four.mean() < 0.4 * change_one.mean()
    # ... but NOT every one within 1 percent or half an hour: each spell that crosses the two-hour mark still comes or
    # goes in one of the four calendars at a time, half an hour a year at a stroke. Measured: 4 of the 40 lie outside.
    assert 2 <= np.count_nonzero(change_four > np.maximum(0.5, 0.01 * four)) <= 8
    # That is why the default is eight phases (tests below): with eight all forty are within 1 percent or half an hour.


def test_with_the_default_eight_phases_every_long_hours_figure_stays_within_one_percent_or_half_an_hour(monkeypatch):
    # The brief's test, at all ten latitudes (65, 67, 70, 75 and 80 degrees, north and south) and the four limits.
    # The worst move for eight phases is half the gap between two of its calendars, a sixteenth of a day; 0.14 day
    # (the step from the middle of the leap cycle to 2026) is the move the brief named. Measured on 14 Nov 2026:
    # 1/16 day: largest 1.02 h (0.88 percent); +0.14 day: 0.75 h (0.91 percent); -0.14 day: 0.51 h. None outside.
    assert sun.YEAR_PHASES == 8
    eight = hours_a_year(sun.long_band_minutes_table(SHIFT_LATS, LONG_LIMITS))
    assert eight.min() > 50.0
    for days, most in ((0.0625, 1.05), (0.14, 0.8), (-0.14, 0.6)):
        moved = hours_a_year(with_calendar_moved(monkeypatch, days, sun.long_band_minutes_table, SHIFT_LATS, LONG_LIMITS))
        change = np.abs(moved - eight)
        assert np.all(change <= np.maximum(0.5, 0.01 * eight)), days
        assert np.all(change <= np.maximum(1.0, 0.02 * eight)), days
        assert change.max() < most and (change / eight).max() < 0.01, days


def test_eight_phases_keep_every_latitude_within_two_percent_or_an_hour_but_not_all_within_one_percent(monkeypatch):
    # Away from the ten test latitudes the brief's bound is not met everywhere: under 2.08 degrees at 71.5 N and 76.5 N
    # the worst move of 1/16 day changes the yearly long-spell hours by 1.00 h and 0.97 h (86.5 h and 84.1 h a year),
    # more than 1 percent and more than half an hour. The bound eight phases meet at every latitude of the cells is the
    # larger of 2 percent and 1 hour: over all 468 cell latitudes at most 1.5 h (LEAP-AVERAGE, 14 Nov 2026; 953 / 5 / 0 / 0
    # cells outside 1 percent or half an hour for the four limits at that move).
    lats = [71.5, 76.5]
    eight = hours_a_year(sun.long_band_minutes_table(lats, [2.08]))
    moved = hours_a_year(with_calendar_moved(monkeypatch, 0.0625, sun.long_band_minutes_table, lats, [2.08]))
    change = np.abs(moved - eight)
    assert np.all(change <= np.maximum(1.0, 0.02 * eight))
    assert np.all(change > np.maximum(0.5, 0.01 * eight))
    assert 0.9 < change.min() and change.max() < 1.1


def test_the_all_hours_table_moves_by_under_a_tenth_of_a_percent_with_four_phases(monkeypatch):
    def hours(table):
        return np.stack([table[..., :BINS_USED[limit]].sum(axis=(1, 2, 3), dtype=float) / 60.0 for limit in LONG_LIMITS])

    one = hours(sun.band_minutes_table(SHIFT_LATS, 1, year_phases=1))
    one_moved = hours(with_calendar_moved(monkeypatch, 0.14, sun.band_minutes_table, SHIFT_LATS, 1, year_phases=1))
    four = hours(sun.band_minutes_table(SHIFT_LATS, 1, year_phases=4))
    four_moved = hours(with_calendar_moved(monkeypatch, 0.14, sun.band_minutes_table, SHIFT_LATS, 1, year_phases=4))
    assert 0.003 < (np.abs(one_moved - one) / one).max() < 0.005       # a single calendar: up to 0.38 percent (1.1 h)
    assert (np.abs(four_moved - four) / four).max() < 0.001            # four phases: 0.07 percent (0.25 h)
    assert np.abs(four_moved - four).max() < 0.26
    eight = hours(sun.band_minutes_table(SHIFT_LATS, 1))
    eight_moved = hours(with_calendar_moved(monkeypatch, 0.14, sun.band_minutes_table, SHIFT_LATS, 1))
    assert (np.abs(eight_moved - eight) / eight).max() < 0.0002        # the default, eight phases: 0.007 percent (0.02 h)
    assert np.abs(eight_moved - eight).max() < 0.05


def test_with_phases_the_long_table_still_never_exceeds_the_all_hours_table_and_equals_it_without_a_minimum():
    lats = [64.0, 67.0, 75.0, 89.5, -70.0]
    every = sun.band_minutes_table(lats, step_minutes=1)
    long = sun.long_band_minutes_table(lats, LONG_LIMITS)
    none = sun.long_band_minutes_table(lats, LONG_LIMITS, min_stretch_h=0.0)
    for j, limit in enumerate(LONG_LIMITS):
        n = BINS_USED[limit]
        assert np.all(long[j] <= every), limit
        assert np.array_equal(none[j][..., :n], every[..., :n]), limit       # exactly, cell by cell: same phases, same step
        assert np.all(none[j][..., n:] == 0.0), limit
    assert np.any(long[0] < every[..., :])
    # with a different number of phases on the two sides neither holds cell by cell
    assert not np.array_equal(none[3], sun.band_minutes_table(lats, step_minutes=1, year_phases=1))


def test_with_phases_the_long_table_has_hours_where_any_of_its_calendars_has_a_long_spell(monkeypatch):
    lats = [50.0, 55.0, 58.0, 60.0, 60.65, 62.0, 64.0]
    table = sun.long_band_minutes_table(lats, LONG_LIMITS)
    has_hours = table.sum(axis=(2, 3, 4)) > 0.0                                   # [limits, latitudes]
    best = [with_calendar_moved(monkeypatch, q, sun.longest_spell_hours, lats, LONG_LIMITS, year_phases=1) for q in EIGHTHS]
    assert np.array_equal(has_hours, (np.max(best, axis=0) >= 2.0).T)
    # Where the longest spell is near two hours it comes at a solstice, and part of a day changes it by seconds:
    # so the mean of the eight calendars' longest spells (longest_spell_hours) reaches two hours at the same latitudes.
    near_two_hours = np.abs(np.mean(best, axis=0) - 2.0) < 0.25
    assert near_two_hours.sum() >= 2 and np.ptp(best, axis=0)[near_two_hours].max() < 0.002
    assert np.array_equal(has_hours, (sun.longest_spell_hours(lats, LONG_LIMITS) >= 2.0).T)
    assert 0.05 < np.ptp(best, axis=0).max() < 0.1    # 64N: the longest day that stays under the limit; minutes apart


# --- added in the round 4 review: the phase tables (now eight, the default) against a count that shares no code ---

def independent_hours_by_bin(lat: float, limit: float, offsets, min_hours: float = 2.0, dt_s: float = 20.0):
    """Hours per ten-day bin with the Sun in (0, limit], mean over calendars: all of them, and those inside long spells.

    The reviewer's own route. Own declination (the Almanac's low-precision Sun written out again), own refraction
    (Saemundsson, turned round into the true altitudes at which the apparent Sun stands at 0 and at the limit),
    and spells as intervals between the moments the Sun crosses those two altitudes (read from samples 20 s
    apart), not as sums of time steps. The year is a ring of 365 days, as in the module.
    """
    def lift(h):
        return 1.02 / math.tan(math.radians(h + 10.3 / (h + 5.11))) / 60.0

    def true_altitude(apparent):
        low, high = -1.9, 10.0
        for _ in range(60):
            mid = 0.5 * (low + high)
            low, high = (mid, high) if mid + lift(mid) < apparent else (low, mid)
        return 0.5 * (low + high)

    s_low, s_high = (math.sin(math.radians(true_altitude(apparent))) for apparent in (0.0, limit))
    edges = np.array([10.0 * b for b in range(36)] + [365.0])
    t = np.arange(round(365 * 86400 / dt_s) + 1) * (dt_s / 86400.0)             # days from 0 h of day 1
    every, long = np.zeros(36), np.zeros(36)
    for offset in offsets:
        n = 9495.86 + offset + 0.5 + t                                           # days from 2000-01-01 12:00
        g = np.radians(357.528 + 0.9856003 * n)
        lon = np.radians(280.460 + 0.9856474 * n + 1.915 * np.sin(g) + 0.020 * np.sin(2.0 * g))
        dec = np.arcsin(np.sin(np.radians(23.439 - 0.0000004 * n)) * np.sin(lon))
        s = (math.sin(math.radians(lat)) * np.sin(dec)
             + math.cos(math.radians(lat)) * np.cos(dec) * np.cos(2.0 * np.pi * (t - 0.5)))
        inside = (s > s_low) & (s <= s_high)
        change = np.flatnonzero(inside[:-1] != inside[1:])
        assert len(change) > 0                                                   # not for a Sun that never enters or leaves
        a, b = s[change], s[change + 1]
        crossed = np.where(np.where(inside[change], b, a) <= s_low, s_low, s_high)
        when = t[change] + (dt_s / 86400.0) * (crossed - a) / (b - a)
        starts, ends = list(when[~inside[change]]), list(when[inside[change]])
        if inside[0] and inside[-1]:
            ends.append(ends.pop(0) + 365.0)                                     # one spell through the year end
        else:
            starts, ends = ([0.0] if inside[0] else []) + starts, ends + ([365.0] if inside[-1] else [])
        assert len(starts) == len(ends)
        for start, end in zip(starts, ends):
            for first, last in ((start, min(end, 365.0)), (0.0, end - 365.0)):
                piece = np.clip(np.minimum(last, edges[1:]) - np.maximum(first, edges[:-1]), 0.0, None) * 24.0
                every += piece
                if (end - start) * 24.0 >= min_hours:
                    long += piece
    return every / len(offsets), long / len(offsets)


@pytest.mark.parametrize("lat, limit", [
    (67.0, 2.08),     # winter days and summer nights under the lowest limit
    (75.0, 5.55),     # four seasons of spells a year
    (-70.0, 7.59),    # the southern midnight Sun: a spell is open at the year end
])
def test_the_default_phase_tables_agree_with_a_count_that_shares_no_code_with_the_module(lat, limit):
    n = BINS_USED[limit]
    long = sun.long_band_minutes_table([lat], [limit])[0, 0].sum(axis=(1, 2), dtype=float) / 60.0        # hours per bin
    every = sun.band_minutes_table([lat], step_minutes=1)[0][..., :n].sum(axis=(1, 2), dtype=float) / 60.0
    own_every, own_long = independent_hours_by_bin(lat, limit, EIGHTHS)
    assert 50.0 < own_long.sum() < own_every.sum() - 50.0
    # Measured over 40 latitudes (59 to 85 degrees, north and south) and the four limits: the yearly long-spell
    # hours agree to 0.003 h, all hours to 0.007 h, any ten-day bin to 0.002 h.
    assert long.sum() == pytest.approx(own_long.sum(), abs=0.02)
    assert every.sum() == pytest.approx(own_every.sum(), abs=0.02)
    assert np.abs(long - own_long).max() < 0.01 and np.abs(every - own_every).max() < 0.01
    # The single calendar is a different table: the count tells them apart.
    one = sun.long_band_minutes_table([lat], [limit], year_phases=1)[0, 0].sum(axis=(1, 2), dtype=float) / 60.0
    assert np.abs(one - own_long).max() > 0.2

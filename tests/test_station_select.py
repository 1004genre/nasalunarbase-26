# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
from datetime import date, timedelta

import numpy as np
import pytest
from twinfinder import snow, stations
from twinfinder import station_select as sel

# Real lines from ghcnd-stations.txt and ghcnd-inventory.txt (fixed-width columns).
STATIONS_TEXT = (
    "ACW00011604  17.1167  -61.7833   10.1    ST JOHNS COOLIDGE FLD                       \n"
    "NO000099710  74.5167   19.0167   16.0    BJOERNOEYA                     GSN     01028\n"
    "USW00026411  64.8031 -147.8761  131.1 AK FAIRBANKS INTL AP              GSN     70261\n"
)
INVENTORY_TEXT = (
    "ACW00011604  17.1167  -61.7833 SNWD 1949 1949\n"
    "NO000099710  74.5167   19.0167 TMAX 1937 2026\n"
    "NO000099710  74.5167   19.0167 SNWD 1922 2024\n"
    "USW00026411  64.8031 -147.8761 TMAX 1929 2026\n"
    "USW00026411  64.8031 -147.8761 SNWD 1929 2026\n"
)


def daily(first: date, last: date, depth_mm) -> list[tuple[date, int]]:
    """One report per day; depth_mm is a number or a function of the day."""
    days = [first + timedelta(days=i) for i in range((last - first).days + 1)]
    return [(d, depth_mm(d) if callable(depth_mm) else depth_mm) for d in days]


def bare_october_then_snow(day: date) -> int:
    return 0 if day.month == 10 else 300


def full_winters(first_winter: int, last_winter: int, depth_mm=bare_october_then_snow):
    records = []
    for winter in range(first_winter, last_winter + 1):
        records += daily(date(winter, 10, 1), date(winter + 1, 3, 31), depth_mm)
    return records


# --- station list and inventory ---------------------------------------------

def test_station_list_is_read_by_column_position():
    stations = sel.parse_stations(STATIONS_TEXT)
    assert set(stations) == {"ACW00011604", "NO000099710", "USW00026411"}
    fairbanks = stations["USW00026411"]
    assert fairbanks["lat"] == pytest.approx(64.8031)
    assert fairbanks["lon"] == pytest.approx(-147.8761)
    assert fairbanks["elevation_m"] == pytest.approx(131.1)
    assert fairbanks["name"] == "FAIRBANKS INTL AP"   # the state code AK sits in its own columns
    assert stations["NO000099710"]["name"] == "BJOERNOEYA"


def test_inventory_gives_first_and_last_year_of_one_element():
    assert sel.parse_inventory(INVENTORY_TEXT) == {
        "ACW00011604": (1949, 1949), "NO000099710": (1922, 2024), "USW00026411": (1929, 2026)}
    assert sel.parse_inventory(INVENTORY_TEXT, element="TMAX") == {
        "NO000099710": (1937, 2026), "USW00026411": (1929, 2026)}


def test_candidates_are_far_north_with_snow_depth_across_the_whole_period():
    stations = sel.parse_stations(STATIONS_TEXT)
    inventory = sel.parse_inventory(INVENTORY_TEXT)
    found = sel.candidates(stations, inventory, min_lat=59.0, first_year=2015, last_year=2024)
    assert [s["id"] for s in found] == ["NO000099710", "USW00026411"]   # the Caribbean station is out
    assert found[1]["first_year"] == 1929 and found[1]["last_year"] == 2026
    # A record that stops before the period ends is not a candidate.
    assert [s["id"] for s in sel.candidates(stations, inventory, 59.0, 2015, 2025)] == ["USW00026411"]
    # Nor is one that starts after the period begins.
    assert sel.candidates(stations, {"USW00026411": (2016, 2026)}, 59.0, 2015, 2024) == []


def test_candidates_need_an_inventory_entry_and_the_latitude_limit_is_inclusive():
    stations = {"A": {"lat": 59.0, "lon": 10.0, "elevation_m": 1.0, "name": "ON THE LINE"},
                "B": {"lat": 58.99, "lon": 10.0, "elevation_m": 1.0, "name": "JUST SOUTH"},
                "C": {"lat": 70.0, "lon": 10.0, "elevation_m": 1.0, "name": "NO SNOW DEPTH"}}
    inventory = {"A": (2000, 2026), "B": (2000, 2026)}
    assert [s["id"] for s in sel.candidates(stations, inventory)] == ["A"]


def test_regions_follow_the_country_code_except_on_the_arctic_islands():
    islands = "Svalbard, Bear Island and Jan Mayen"
    assert sel.region_group("NO000099710", 74.5167, 19.0167) == islands     # Norwegian id, Bear Island
    assert sel.region_group("NOE00134778", 78.923, 11.9331) == islands      # Norwegian id, Ny-Alesund
    assert sel.region_group("SV000001008", 78.25, 15.4667) == islands
    assert sel.region_group("JNM00001001", 70.9331, -8.6667) == islands
    assert sel.region_group("NO000001026", 69.65, 18.93) == "Norway (mainland)"
    assert sel.region_group("SWE00140000", 65.0, 20.0) == "Sweden"
    assert sel.region_group("FIE00140000", 65.0, 26.0) == "Finland"
    assert sel.region_group("RSM00022113", 68.97, 33.05) == "Russia"
    assert sel.region_group("USW00026411", 64.8, -147.9) == "Alaska"
    assert sel.region_group("CA002400300", 82.5, -62.3) == "Canada"
    assert sel.region_group("IC000004030", 64.13, -21.9) == "Iceland"
    assert sel.region_group("GLW00017605", 76.5, -68.8) == "Greenland"
    assert sel.region_group("UK000003005", 60.13, -1.18) == "Other"


def test_spread_order_takes_turns_between_latitude_bands_from_the_north():
    stations = [{"id": f"S{i}", "lat": lat} for i, lat in enumerate([61.0, 62.0, 63.0, 64.0, 71.0, 76.0, 77.0])]
    order = sel.spread_order(stations, seed=1)
    assert sorted(s["id"] for s in order) == sorted(s["id"] for s in stations)   # nothing lost or repeated
    assert order[0]["lat"] >= 75.0                 # first turn: one from each band, north first
    assert order[1]["lat"] == 71.0
    assert 60.0 <= order[2]["lat"] < 65.0
    assert order[3]["lat"] >= 75.0                 # second turn starts in the north again
    assert all(60.0 <= s["lat"] < 65.0 for s in order[4:])


def test_spread_order_is_repeatable_and_ignores_input_order():
    stations = [{"id": f"S{i:02d}", "lat": 60.0 + i * 0.1} for i in range(30)]
    first = [s["id"] for s in sel.spread_order(stations, seed=7)]
    again = [s["id"] for s in sel.spread_order(list(reversed(stations)), seed=7)]
    assert first == again
    assert first != sorted(first)                  # shuffled inside the band, not in id order
    assert first != [s["id"] for s in sel.spread_order(stations, seed=8)]


# --- one station's snow depth -----------------------------------------------

def test_snow_depth_that_failed_quality_control_is_dropped_and_counted():
    text = ('"STATION","DATE","SNWD","SNWD_ATTRIBUTES","TMAX"\n'
            '"X","2020-10-01","   0",",,E","  12"\n'
            '"X","2020-10-02","9999",",I,E","  -3"\n'     # failed the internal consistency check
            '"X","2020-10-03","",""," -10"\n'             # no snow depth that day
            '"X","2020-10-04","  50",",,S","  -8"\n')
    records, flagged = sel.parse_snow_depth(text)
    assert records == [(date(2020, 10, 1), 0), (date(2020, 10, 4), 50)]
    assert flagged == 1


def test_snow_depth_parse_copes_with_no_snow_depth_column():
    assert sel.parse_snow_depth('"STATION","DATE","TMAX"\n"X","2020-10-01","12"\n') == ([], 0)


def test_the_winter_grouping_is_stated_once_in_the_stations_module():
    # station_select has no winter rule of its own: 1 October to 31 March is stations.winter_half_of.
    assert not hasattr(sel, "winter_of")
    assert stations.winter_half_of(date(2021, 3, 31)) == 2020
    assert stations.winter_half_of(date(2021, 4, 1)) is None


def test_winter_coverage_is_the_share_of_days_from_october_to_march_with_a_report():
    records = daily(date(2021, 10, 1), date(2022, 3, 31), 100)          # all 182 days
    records += daily(date(2019, 10, 1), date(2019, 12, 31), 100)        # 92 of 183 days (leap year 2020)
    records += [(date(2019, 10, 1), 100)]                               # a repeated day counts once
    records += daily(date(2022, 6, 1), date(2022, 8, 31), 0)            # summer does not count
    coverage = sel.winter_coverage(records, 2019, 2021)
    assert coverage[2021] == pytest.approx(1.0)
    assert coverage[2019] == pytest.approx(92 / 183)
    assert coverage[2020] == 0.0
    assert set(coverage) == {2019, 2020, 2021}


def test_a_station_with_five_well_reported_winters_and_both_bare_and_snowy_days_is_kept():
    verdict = sel.assess(full_winters(2015, 2019), 2015, 2024)
    assert verdict["keep"] is True
    assert verdict["reason"] == "kept"
    assert verdict["good_winters"] == [2015, 2016, 2017, 2018, 2019]


def test_four_good_winters_are_not_enough():
    verdict = sel.assess(full_winters(2015, 2018), 2015, 2024)
    assert verdict["keep"] is False
    assert verdict["reason"] == "fewer than 5 winters with snow depth on 80% of days"
    assert verdict["good_winters"] == [2015, 2016, 2017, 2018]


def test_a_winter_reported_on_under_80_percent_of_days_does_not_count():
    records = full_winters(2015, 2018)
    records += daily(date(2019, 10, 1), date(2020, 2, 15), bare_october_then_snow)   # 138 of 183 days = 75%
    assert sel.assess(records, 2015, 2024)["keep"] is False
    records += daily(date(2020, 2, 16), date(2020, 2, 25), 300)                      # 148 of 183 days = 81%
    assert sel.assess(records, 2015, 2024)["keep"] is True


def test_a_station_with_no_snow_depth_in_the_period_is_rejected():
    verdict = sel.assess(full_winters(2005, 2012), 2015, 2024)
    assert verdict["keep"] is False
    assert verdict["reason"] == "no snow depth in these winters"


def test_a_station_that_reports_only_on_snow_days_is_rejected():
    # Snow lies from 20 October, so reports cover 89% of each winter, but a zero is never written down.
    records = []
    for winter in range(2015, 2025):
        records += daily(date(winter, 10, 20), date(winter + 1, 3, 31), 300)
    verdict = sel.assess(records, 2015, 2024)
    assert verdict["keep"] is False
    assert verdict["reason"] == "never zero at any time of year"


def test_a_high_arctic_station_under_snow_all_winter_is_rejected_but_told_apart():
    # Daily reports all year: bare ground in July and August, snow from September to June.
    records = daily(date(2015, 7, 1), date(2025, 6, 30), lambda d: 0 if d.month in (7, 8) else 400)
    verdict = sel.assess(records, 2015, 2024)
    assert verdict["keep"] is False
    assert verdict["reason"] == "never zero in winter, zero at other times of year"
    assert len(verdict["good_winters"]) == 10


def test_a_station_that_never_reports_snow_on_the_ground_is_rejected():
    verdict = sel.assess(full_winters(2015, 2024, depth_mm=0), 2015, 2024)
    assert verdict["keep"] is False
    assert verdict["reason"] == "never above zero"


def test_only_the_well_reported_winters_are_passed_on():
    records = full_winters(2015, 2019)
    records += [(date(2021, 1, 15), 0), (date(2021, 1, 16), 0)]     # two stray reports in a poor winter
    records += daily(date(2016, 7, 1), date(2016, 7, 31), 0)        # summer reports
    verdict = sel.assess(records, 2015, 2024)
    assert verdict["keep"] is True
    assert len(verdict["records"]) == len(full_winters(2015, 2019))
    assert all(stations.winter_half_of(day) in verdict["good_winters"] for day, _ in verdict["records"])


def test_whole_snow_years_of_the_well_reported_winters_are_passed_on_too():
    records = full_winters(2015, 2019)
    records += daily(date(2016, 7, 1), date(2016, 7, 31), 0)        # the summer after well-reported winter 2015
    records += daily(date(2021, 7, 1), date(2021, 7, 31), 0)        # the summer after poor winter 2020
    records += [(date(2021, 1, 15), 0)]                             # a stray report in poor winter 2020
    verdict = sel.assess(records, 2015, 2024)
    assert verdict["keep"] is True
    assert len(verdict["year_records"]) == len(full_winters(2015, 2019)) + 31
    assert all(stations.snow_year_of(day) in verdict["good_winters"] for day, _ in verdict["year_records"])
    summer = [day for day, _ in verdict["year_records"] if stations.winter_half_of(day) is None]
    assert min(summer) == date(2016, 7, 1) and max(summer) == date(2016, 7, 31)


def test_summer_reports_do_not_make_a_winter_well_reported_or_change_the_verdict():
    # Daily reports from April to September only, in every year: no winter reaches 80% of its days.
    records = []
    for year in range(2016, 2026):
        records += daily(date(year, 4, 1), date(year, 9, 30), lambda d: 300 if d.month == 4 else 0)
    verdict = sel.assess(records, 2015, 2024)
    assert verdict["keep"] is False
    assert verdict["reason"] == "no snow depth in these winters"
    assert verdict["year_records"] == []


def test_bins_reported_on_enough_of_their_days_are_marked_complete():
    counts = np.array([50, 40, 39, 0])     # reports per ten-day bin over five snow years
    possible = np.array([50, 50, 50, 50])  # calendar days those bins hold in the five years
    assert sel.complete_bins(counts, possible).tolist() == [True, True, False, False]
    assert sel.complete_bins(counts, possible, min_share=0.5).tolist() == [True, True, True, False]


def test_the_long_last_bin_needs_80_percent_of_its_fifteen_days():
    # Five snow years without a leap December: bin 35 holds 75 days, an ordinary bin 50.
    possible = stations.days_per_bin([2021, 2022])          # two years: 30 and 20
    assert possible[35] == 30 and possible[0] == 20
    counts = np.zeros(snow.N_BINS, dtype=int)
    counts[0], counts[35] = 16, 16                          # 16 reports: 80% of bin 0, 53% of bin 35
    complete = sel.complete_bins(counts, possible)
    assert bool(complete[0]) is True
    assert bool(complete[35]) is False                      # the old rule (0.8 x 10 x winters) let this through
    counts[35] = 24
    assert bool(sel.complete_bins(counts, possible)[35]) is True


def test_a_bin_with_no_possible_day_is_never_complete():
    assert sel.complete_bins(np.array([0, 3]), np.array([0, 0])).tolist() == [False, False]


def test_a_station_reporting_all_year_has_every_bin_complete():
    years = [2015, 2016, 2017, 2018, 2019]                  # holds two leap days
    records = daily(date(2015, 10, 1), date(2020, 9, 30), 0)
    _, counts = stations.snow_free_by_bin(records, 2015, 2019)
    assert sel.complete_bins(counts, stations.days_per_bin(years)).all()
    assert sel.complete_bins(counts, stations.days_per_bin(years), min_share=1.0).all()


def test_a_station_reporting_only_in_winter_misses_the_bins_on_the_season_edge():
    # Bin 27 runs from 28 September to 7 October. A record that starts each year on 1 October covers
    # seven of its ten days, so the bin is not complete: the satellite value stands for all ten.
    years = [2021, 2022, 2023, 2024, 2025]
    records = full_winters(2021, 2025, depth_mm=0)
    _, counts = stations.snow_free_by_bin(records, 2021, 2025)
    possible = stations.days_per_bin(years)
    complete = sel.complete_bins(counts, possible)
    assert counts[27] == 5 * 7 - 1                          # 2024 is a leap year: 1 October is day 275
    assert bool(complete[27]) is False
    assert bool(sel.complete_bins(counts, possible, min_share=0.6)[27]) is True
    assert complete[28:].all() and complete[:9].all()       # 8 October to 31 March
    assert not complete[9:27].any()                         # nothing from April to September
    assert counts[9] == 1                                   # 31 March 2024 is day 91
    # With its April-to-September reports added the same station has every bin complete.
    records += [(day, 0) for year in range(2022, 2027) for day, _ in daily(date(year, 4, 1), date(year, 9, 30), 0)]
    _, counts = stations.snow_free_by_bin(records, 2021, 2025)
    assert sel.complete_bins(counts, possible).all()


def test_summer_bins_are_compared_only_where_the_station_keeps_reporting():
    # A station that writes snow depth down daily in winter and on snow days only from May on.
    records = []
    for year in range(2015, 2020):
        records += daily(date(year, 10, 1), date(year + 1, 4, 30), lambda d: 0 if d.month in (10, 4) else 300)
        records += [(date(year + 1, 5, 3), 80), (date(year + 1, 6, 2), 10)]
    verdict = sel.assess(records, 2015, 2024)
    assert verdict["keep"] is True
    share, counts = stations.snow_free_by_bin(verdict["year_records"], 2015, 2024)
    complete = sel.complete_bins(counts, stations.days_per_bin(verdict["good_winters"]))
    assert complete[9:12].all() and share[10:12].tolist() == [1.0, 1.0]     # April: bare, well reported
    # May: five snow-day reports (and 30 April of the two leap years, day 121) would read as mostly snow ...
    assert counts[12] == 7 and share[12] == pytest.approx(2 / 7)
    assert counts[15] == 5 and share[15] == 0.0
    assert not complete[12:27].any()                        # ... so those bins are left out


# --- satellite against stations ---------------------------------------------

def test_summary_uses_only_bins_where_both_exist():
    satellite = np.array([[0.0, 0.5, np.nan], [1.0, 0.2, 0.3]])
    station = np.array([[0.2, 0.5, 0.9], [0.9, np.nan, 0.1]])
    out = sel.summarise(satellite, station)
    assert out["n"] == 4
    assert out["mean_bias"] == pytest.approx((-0.2 + 0.0 + 0.1 + 0.2) / 4)     # satellite minus station
    assert out["mean_abs_difference"] == pytest.approx((0.2 + 0.0 + 0.1 + 0.2) / 4)


def test_summary_of_nothing_is_none_not_nan():
    out = sel.summarise(np.array([np.nan]), np.array([0.5]))
    assert out == {"n": 0, "mean_bias": None, "median_bias": None, "mean_abs_difference": None}


def test_calibration_table_bins_by_satellite_probability():
    satellite = np.array([0.0, 0.05, 0.1, 0.29, 0.9, 1.0, np.nan, 0.6])
    station = np.array([0.1, 0.3, 0.4, 0.6, 0.8, 1.0, 0.5, np.nan])
    table = sel.calibration_table(satellite, station)
    assert [(row["ims_low"], row["ims_high"]) for row in table] == [
        (0.0, 0.1), (0.1, 0.3), (0.3, 0.5), (0.5, 0.7), (0.7, 0.9), (0.9, 1.0)]
    assert [row["n_station_bins"] for row in table] == [2, 2, 0, 0, 0, 2]   # 0.1 opens the second bin; 1.0 is in the last
    assert table[0]["mean_station_snow_free"] == pytest.approx(0.2)
    assert table[0]["mean_ims"] == pytest.approx(0.025)
    assert table[1]["mean_station_snow_free"] == pytest.approx(0.5)
    assert table[5]["mean_station_snow_free"] == pytest.approx(0.9)
    assert table[5]["mean_ims"] == pytest.approx(0.95)
    assert table[2]["mean_station_snow_free"] is None and table[2]["mean_ims"] is None


def test_calibration_bands_survive_32_bit_satellite_values():
    # The snow layer is stored as float32, where 0.7 is 0.69999999 and 0.9 is 0.89999998.
    satellite = np.array([0.7, 0.9, 0.3], dtype="float32")
    table = sel.calibration_table(satellite, np.array([0.5, 0.5, 0.5]))
    assert [row["n_station_bins"] for row in table] == [0, 0, 1, 0, 1, 1]


def test_calibrate_runs_straight_lines_between_the_table_points():
    table = [
        {"ims_low": 0.0, "ims_high": 0.1, "n_station_bins": 10, "mean_ims": 0.02, "mean_station_snow_free": 0.1},
        {"ims_low": 0.1, "ims_high": 0.3, "n_station_bins": 0, "mean_ims": None, "mean_station_snow_free": None},
        {"ims_low": 0.3, "ims_high": 0.5, "n_station_bins": 10, "mean_ims": 0.42, "mean_station_snow_free": 0.7},
        {"ims_low": 0.9, "ims_high": 1.0, "n_station_bins": 10, "mean_ims": 0.98, "mean_station_snow_free": 0.9},
    ]
    out = sel.calibrate(np.array([0.0, 0.02, 0.22, 0.42, 0.70, 0.98, 1.0, np.nan]), table)
    assert out[:7] == pytest.approx([0.1, 0.1, 0.4, 0.7, 0.8, 0.9, 0.9])   # flat beyond the end points
    assert np.isnan(out[7])                                               # unobserved stays unobserved


def test_doubling_is_capped_at_certainty():
    out = sel.doubled(np.array([0.0, 0.2, 0.5, 0.8, np.nan]))
    assert out[:4] == pytest.approx([0.0, 0.4, 1.0, 1.0])
    assert np.isnan(out[4])


def test_usable_days_are_low_sun_days_weighted_by_the_snow_free_odds_of_their_bins():
    probabilities = np.full(36, np.nan)
    probabilities[27] = 1.0     # days 271 to 280 (28 September to 7 October)
    probabilities[28] = 0.5     # days 281 to 290
    probabilities[18] = 0.25    # days 181 to 190: a summer bin counts like any other
    assert sel.usable_days(list(range(276, 286)), probabilities) == pytest.approx(5 * 1.0 + 5 * 0.5)
    assert sel.usable_days([185, 186], probabilities) == pytest.approx(0.5)
    assert sel.usable_days([], probabilities) == 0.0                 # the Sun never gets that low: a known zero
    assert sel.usable_days([300, 301], probabilities) is None        # low Sun but no snow observation
    assert sel.usable_days([280, 300], probabilities) is None        # one unobserved day makes the sum unknown
    assert sel.usable_days([], np.full(36, np.nan)) is None          # no snow odds at all: never a known zero


def test_usable_days_agree_with_the_grazing_module():
    from twinfinder import grazing, sun
    probabilities = np.linspace(0.9, 0.0, 36)
    for lat, limit in [(63.95, 5.55), (70.85, 2.08), (78.75, 7.59), (59.05, 2.08)]:
        days = sun.all_day_low_sun_days(lat, limit)
        expected = grazing.usable_days(grazing.days_per_bin(days), probabilities)
        assert sel.usable_days(days, probabilities) == pytest.approx(float(expected))


def test_counting_cells_at_or_above_a_threshold_ignores_unknowns():
    assert sel.count_at_least([9.99, 10.0, 25.0, None, 0.0], 10.0) == 2


# --- guards added after the first run ----------------------------------------

def test_one_stray_snow_report_passes_the_rule_as_written_but_not_a_minimum():
    # Jan Mayen's record: snow depth zero on 890 winter days and above zero on one.
    records = full_winters(2015, 2019, depth_mm=0)
    records[100] = (records[100][0], 50)
    assert sel.assess(records, 2015, 2024)["keep"] is True
    verdict = sel.assess(records, 2015, 2024, min_snow_reports=10)
    assert verdict["keep"] is False
    assert verdict["reason"] == "above zero on fewer than 10 days"
    assert sel.assess(full_winters(2015, 2019), 2015, 2024, min_snow_reports=10)["keep"] is True


def test_days_with_any_temperature_or_precipitation_report_are_found():
    text = ('"STATION","DATE","PRCP","PRCP_ATTRIBUTES","SNWD","SNWD_ATTRIBUTES","TMAX","TAVG"\n'
            '"X","2020-10-01","  12",",,S","","","",""\n'          # rain only
            '"X","2020-10-02","","","  50",",,S","",""\n'          # snow depth only: not a weather report
            '"X","2020-10-03","","","","",""," -31"\n'             # mean temperature only
            '"X","2020-10-04","","","","","",""\n')                # nothing at all
    assert sel.parse_observed_days(text) == {date(2020, 10, 1), date(2020, 10, 3)}


def test_unreported_snow_depth_is_read_as_bare_ground_only_in_winters_with_enough_snow_reports():
    # Winter 2015: snow depth written down on 40 snowy days in January and February, weather reported daily.
    snowy = daily(date(2016, 1, 10), date(2016, 2, 18), 120)
    # Winter 2016: only three snow-depth reports, so the snow-depth channel cannot be trusted that winter.
    stray = daily(date(2017, 1, 1), date(2017, 1, 3), 80)
    observed = {day for day, _ in daily(date(2015, 10, 1), date(2017, 3, 31), 0)}
    filled, winters = sel.unreported_as_bare(snowy + stray, observed, 2015, 2024, min_reports=30)
    assert winters == [2015]
    assert len(filled) == 183                                       # every observed day of winter 2015 (leap year)
    assert sum(depth == 0 for _, depth in filled) == 183 - 40
    assert dict(filled)[date(2016, 1, 10)] == 120                   # reported depths are kept
    assert all(stations.winter_half_of(day) == 2015 for day, _ in filled)


def test_weather_parse_reads_daily_maximum_and_precipitation_in_tenths():
    text = ('"STATION","DATE","PRCP","PRCP_ATTRIBUTES","TMAX","TMAX_ATTRIBUTES"\n'
            '"X","2020-12-01","  12",",,S","  -35",",,S"\n'
            '"X","2020-12-02","","","",""\n')
    assert sel.parse_weather(text) == {date(2020, 12, 1): (-35, 12), date(2020, 12, 2): (None, None)}
    assert sel.parse_weather('"STATION","DATE","SNWD"\n"X","2020-12-01","5"\n') == {date(2020, 12, 1): (None, None)}


def december(tmax_tenths, precip_tenths) -> dict:
    """Weather for 1 to 20 December 2020; each argument is a number or a function of the day."""
    value = lambda v, d: v(d) if callable(v) else v
    return {d: (value(tmax_tenths, d), value(precip_tenths, d)) for d, _ in daily(date(2020, 12, 1), date(2020, 12, 20), 0)}


def test_zero_depth_after_a_cold_wet_week_is_counted():
    # A week that never thaws (maximum below -1.0 C every day) with at least 5 mm of
    # precipitation must leave snow on the ground. 2 mm a day at -5 C does that from 7 December on.
    weather = december(-50, 20)
    bare = daily(date(2020, 12, 1), date(2020, 12, 20), 0)
    snowy = daily(date(2020, 12, 1), date(2020, 12, 20), 150)
    assert sel.cold_wet_days(bare, weather, winters=[2020]) == (14, 14)     # 7 to 20 December, all reported bare
    assert sel.cold_wet_days(snowy, weather, winters=[2020]) == (14, 0)
    assert sel.cold_wet_days(bare, weather, winters=[2019]) == (0, 0)       # only the chosen winters count


def test_a_thaw_a_dry_spell_or_a_missing_maximum_breaks_the_cold_wet_week():
    bare = daily(date(2020, 12, 1), date(2020, 12, 20), 0)
    thaw = december(lambda d: 10 if d.day == 10 else -50, 20)               # +1.0 C on the 10th
    assert sel.cold_wet_days(bare, thaw, winters=[2020]) == (7, 7)          # 7 to 9 and 17 to 20 December
    assert sel.cold_wet_days(bare, december(-50, 0), winters=[2020]) == (0, 0)          # frost but no precipitation
    assert sel.cold_wet_days(bare, december(-5, 20), winters=[2020]) == (0, 0)          # -0.5 C is not cold enough
    gap = december(lambda d: None if d.day == 10 else -50, 20)
    assert sel.cold_wet_days(bare, gap, winters=[2020]) == (7, 7)
    assert sel.cold_wet_days(bare, {}, winters=[2020]) == (0, 0)            # a station with no thermometer


def test_precipitation_on_the_day_itself_does_not_count_towards_the_week():
    # Snow depth is read in the morning; that day's precipitation may fall after the reading.
    weather = december(-50, lambda d: 60 if d.day == 15 else 0)             # 6 mm on the 15th only
    bare = daily(date(2020, 12, 1), date(2020, 12, 20), 0)
    assert sel.cold_wet_days(bare, weather, winters=[2020]) == (5, 5)       # 16 to 20 December, not the 15th


def test_stricter_bin_completeness_can_be_asked_for():
    possible = np.array([50, 50, 50])
    assert sel.complete_bins(np.array([50, 48, 47]), possible, min_share=0.95).tolist() == [True, True, False]


def test_summaries_can_be_taken_over_one_group_of_bins():
    satellite = np.tile(np.linspace(0.0, 0.35, 36), (3, 1))         # three stations, 36 calendar bins
    station = satellite + 0.1
    station[:, stations.SUMMER_HALF_BINS] = satellite[:, stations.SUMMER_HALF_BINS] - 0.2
    winter = sel.summarise(satellite[:, stations.WINTER_HALF_BINS], station[:, stations.WINTER_HALF_BINS])
    summer = sel.summarise(satellite[:, stations.SUMMER_HALF_BINS], station[:, stations.SUMMER_HALF_BINS])
    assert winter["n"] == summer["n"] == 3 * 18
    assert winter["mean_bias"] == pytest.approx(-0.1) and summer["mean_bias"] == pytest.approx(0.2)
    assert winter["median_bias"] == pytest.approx(-0.1) and summer["median_bias"] == pytest.approx(0.2)


def test_the_median_difference_is_reported_beside_the_mean():
    out = sel.summarise(np.array([0.0, 0.0, 0.9]), np.array([0.1, 0.1, 0.1]))
    assert out["mean_bias"] == pytest.approx(0.2)
    assert out["median_bias"] == pytest.approx(-0.1)


def test_per_station_differences_skip_stations_without_a_compared_bin():
    satellite = np.array([[0.2, 0.4, np.nan], [np.nan, np.nan, 0.5], [0.9, np.nan, np.nan]])
    station = np.array([[0.1, 0.1, 0.9], [0.1, 0.2, np.nan], [1.0, 0.3, np.nan]])
    assert sel.station_biases(satellite, station) == pytest.approx([0.2, -0.1])   # the middle station has no pair
    assert sel.station_biases(satellite[1:2], station[1:2]).size == 0


def test_resampled_interval_brackets_the_mean_bias_and_is_repeatable():
    rng = np.random.default_rng(3)
    station = rng.uniform(0.0, 1.0, size=(30, 36))                  # rows are stations
    satellite = station - 0.05 + rng.normal(0.0, 0.1, size=(30, 36))
    satellite[0, :5] = np.nan
    low, high = sel.resampled_bias_interval(satellite, station, seed=1)
    assert low < sel.summarise(satellite, station)["mean_bias"] < high
    assert high - low < 0.1
    assert (low, high) == sel.resampled_bias_interval(satellite, station, seed=1)


def test_resampled_interval_has_no_width_when_every_station_agrees():
    low, high = sel.resampled_bias_interval(np.full((5, 36), 0.4), np.full((5, 36), 0.5))
    assert low == pytest.approx(-0.1) and high == pytest.approx(-0.1)


# --- the validation scripts on calendar bins ---------------------------------

def station_row(lat: float, satellite, station_share) -> dict:
    """A made-up examined station as scripts/validate_snow_many.py keeps it."""
    satellite, station_share = np.asarray(satellite, dtype=float), np.asarray(station_share, dtype=float)
    return {"lat": lat, "satellite": satellite, "satellite_as_mapped": satellite + 0.1, "station_share": station_share}


def test_script_month_groups_and_midwinter_use_calendar_bins():
    import importlib
    many = importlib.import_module("scripts.validate_snow_many")
    assert sorted(b for bins in many.MONTH_BINS.values() for b in bins) == list(range(snow.N_BINS))
    assert many.MONTH_BINS["Jan"] == [0, 1, 2] and many.MONTH_BINS["Oct"] == [27, 28, 29]
    assert stations.bin_span(many.MONTH_BINS["Oct"]) == "28 Sep-27 Oct"
    assert stations.bin_span(many.MIDWINTER_BINS) == "27 Nov-1 Mar"      # one run across New Year, not a slice
    assert many.PERIODS["may_to_august_north_of_66"][1:] == (stations.MAY_TO_AUGUST_BINS, 66.0)
    assert many.PERIODS["winter_half"][1] == stations.WINTER_HALF_BINS


def test_script_comparison_is_taken_over_the_asked_bins_and_counts_stations_with_a_pair():
    import importlib
    many = importlib.import_module("scripts.validate_snow_many")
    summer_only = np.where(grazing_mask(stations.SUMMER_HALF_BINS), 0.5, np.nan)   # reports from April to September only
    rows = [station_row(70.0, np.full(36, 0.4), np.full(36, 0.5)),
            station_row(60.0, np.full(36, 0.8), summer_only),
            station_row(68.0, np.full(36, np.nan), np.full(36, 0.5))]             # no satellite land pixel
    winter = many.compare(rows, stations.WINTER_HALF_BINS)
    summer = many.compare(rows, stations.SUMMER_HALF_BINS)
    assert (winter["stations"], winter["n"]) == (1, 18)
    assert winter["mean_bias"] == pytest.approx(-0.1)
    assert (summer["stations"], summer["n"]) == (2, 36)
    assert summer["mean_bias"] == pytest.approx(0.1)                              # eighteen at -0.1, eighteen at +0.3
    assert summer["median_of_station_means"] == pytest.approx(0.1)
    assert sum(row["n_station_bins"] for row in summer["calibration"]) == 36
    mapped = many.compare(rows, stations.SUMMER_HALF_BINS, "satellite_as_mapped", calibration=False)
    assert mapped["mean_bias"] == pytest.approx(0.2) and "calibration" not in mapped
    periods = many.period_results(rows, always_snow=[])
    north = periods["may_to_august_north_of_66"]
    assert north["stations_in_group"] == 2                                       # 70N and 68N; the 60N station is out
    assert (north["with_stale_flag_rule"]["stations"], north["with_stale_flag_rule"]["n"]) == (1, 12)
    assert north["days"] == "1 May-28 Aug"


def grazing_mask(bins) -> np.ndarray:
    mask = np.zeros(snow.N_BINS, dtype=bool)
    mask[list(bins)] = True
    return mask


def test_second_opinion_window_tests_go_by_date_not_by_a_missing_bin():
    import importlib
    second = importlib.import_module("scripts.second_opinion_snow")
    assert second.outside_october_to_march(90) is False        # 31 March
    assert second.outside_october_to_march(91) is True         # 1 April
    assert second.outside_october_to_march(273) is True        # 30 September
    assert second.outside_october_to_march(274) is False       # 1 October
    assert not hasattr(second, "winter_of")                    # the groupings come from stations and snow


def test_second_opinion_counts_maps_per_winter_as_the_stale_flag_rule_does():
    import importlib
    second = importlib.import_module("scripts.second_opinion_snow")
    days = [date(2015, 10, 1) + timedelta(days=5 * i) for i in range(73)]          # every fifth day for a year
    state = np.array([1.0 if d < date(2016, 3, 26) else 0.0 for d in days])
    out = second.ims_persistence(days, state)
    in_rule_winter = sum(date(2015, 10, 1) <= d <= date(2016, 3, 20) for d in days)
    assert in_rule_winter == 35
    assert out["winters_snow_free_on_every_map"] == [2015]     # the change on 26 March comes after the rule's winter
    assert out["state_changes_per_winter"] == [0]


def test_second_opinion_leaves_out_station_shares_written_for_the_old_bins(tmp_path, monkeypatch):
    import importlib
    import json
    second = importlib.import_module("scripts.second_opinion_snow")
    check = tmp_path / "snow_validation.json"
    check.write_text(json.dumps([{"station": "OLD", "station_share": [0.5] * 18},
                                 {"station": "NEW", "station_share": [0.5] * 35 + [None]}]))
    monkeypatch.setattr(second, "STATION_CHECK", check)
    shares, stale = second.station_bins()
    assert stale == ["OLD"] and list(shares) == ["NEW"]
    assert len(shares["NEW"]) == 36 and np.isnan(shares["NEW"][35])

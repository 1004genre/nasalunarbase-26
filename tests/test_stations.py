# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
from datetime import date, timedelta

import numpy as np
import pytest
from twinfinder import snow, stations, sun


def daily(first: date, last: date, depth_mm: int = 0) -> list[tuple[date, int]]:
    return [(first + timedelta(days=i), depth_mm) for i in range((last - first).days + 1)]


def test_parse_reads_snow_depth_and_skips_blank_reports():
    text = ('"STATION","DATE","LATITUDE","SNWD","SNWD_ATTRIBUTES","TMAX"\n'
            '"X","2020-10-01","74.5","   0",",,S","  12"\n'
            '"X","2020-10-02","74.5","  50",",,S","  -3"\n'
            '"X","2020-10-03","74.5","",""," -10"\n')
    assert stations.parse_snow_depth(text) == [(date(2020, 10, 1), 0), (date(2020, 10, 2), 50)]


def test_parse_without_a_snow_depth_column_gives_nothing():
    assert stations.parse_snow_depth('"STATION","DATE","TMAX"\n"X","2020-10-01","12"\n') == []


# --- how dates are grouped ----------------------------------------------------

def test_a_snow_year_runs_from_october_to_september_and_is_named_by_its_october():
    assert stations.snow_year_of(date(2020, 10, 1)) == 2020
    assert stations.snow_year_of(date(2021, 1, 15)) == 2020
    assert stations.snow_year_of(date(2021, 7, 1)) == 2020      # the summer after the winter
    assert stations.snow_year_of(date(2021, 9, 30)) == 2020
    assert stations.snow_year_of(date(2021, 10, 1)) == 2021


def test_the_winter_half_is_october_to_march_and_the_summer_half_is_the_rest():
    assert stations.winter_half_of(date(2020, 10, 1)) == 2020
    assert stations.winter_half_of(date(2021, 3, 31)) == 2020
    assert stations.winter_half_of(date(2021, 4, 1)) is None
    assert stations.winter_half_of(date(2020, 9, 30)) is None
    assert stations.summer_half_of(date(2021, 4, 1)) == 2020
    assert stations.summer_half_of(date(2021, 9, 30)) == 2020
    assert stations.summer_half_of(date(2021, 3, 31)) is None
    assert stations.summer_half_of(date(2021, 10, 1)) is None


def test_the_winter_half_is_longer_than_the_winter_of_the_stale_flag_rule():
    # Two definitions on purpose: the snow layer's rule stops on 20 March, the station half-year on 31 March.
    day = date(2021, 3, 25)
    assert stations.winter_half_of(day) == 2020
    assert snow.winter_of(day.year, day.timetuple().tm_yday) is None


def test_a_date_is_binned_by_its_own_day_of_year_like_the_satellite_maps():
    assert stations.bin_of(date(2021, 1, 1)) == 0
    assert stations.bin_of(date(2021, 10, 1)) == 27            # day 274
    assert stations.bin_of(date(2021, 12, 17)) == 35           # day 351 opens the long last bin
    assert stations.bin_of(date(2021, 12, 31)) == 35
    assert stations.bin_of(date(2020, 12, 31)) == 35           # day 366 of a leap year stays in the last bin
    assert stations.bin_of(date(2021, 3, 31)) == 8             # day 90
    assert stations.bin_of(date(2020, 3, 31)) == 9             # day 91 in a leap year: one bin later
    for day in (date(2021, 6, 30), date(2020, 6, 30)):
        assert stations.bin_of(day) == sun.bin_index(day.timetuple().tm_yday)


def test_the_bin_halves_are_the_contract_ones_and_cover_the_year_once():
    assert stations.WINTER_HALF_BINS == list(range(27, 36)) + list(range(0, 9))
    assert stations.SUMMER_HALF_BINS == list(range(9, 27))
    assert sorted(stations.WINTER_HALF_BINS + stations.SUMMER_HALF_BINS) == list(range(snow.N_BINS))
    assert stations.MAY_TO_AUGUST_BINS == list(range(12, 24))
    assert stations.bin_span(stations.MAY_TO_AUGUST_BINS) == "1 May-28 Aug"


def test_bin_labels_name_the_first_day_and_spans_name_both_ends():
    assert stations.bin_label(0) == "Jan01"
    assert stations.bin_label(27) == "Sep28"
    assert stations.bin_label(35) == "Dec17"
    assert stations.bin_span([0, 1, 2]) == "1 Jan-30 Jan"
    assert stations.bin_span([33, 34, 35]) == "27 Nov-31 Dec"    # the last bin runs to the end of the year
    assert stations.bin_span(stations.WINTER_HALF_BINS) == "28 Sep-31 Mar"   # a run across New Year
    assert stations.bin_span(stations.SUMMER_HALF_BINS) == "1 Apr-27 Sep"
    assert len({stations.bin_label(index) for index in range(snow.N_BINS)}) == snow.N_BINS


# --- snow-free share per bin ---------------------------------------------------

def test_snow_free_share_per_calendar_bin():
    records = [(date(2021, 10, d), 0) for d in range(8, 13)]            # 8 to 12 October: five snow-free days, bin 28
    records += [(date(2021, 10, d), 30) for d in range(13, 18)]         # 13 to 17 October: five snow days, bin 28
    records += [(date(2022, 1, 2), 0), (date(2022, 1, 3), 0)]           # bin 0, all snow-free
    shares, counts = stations.snow_free_by_bin(records, 2021, 2021)
    assert shares[28] == pytest.approx(0.5)
    assert counts[28] == 10
    assert shares[0] == pytest.approx(1.0)
    assert counts[0] == 2
    assert np.isnan(shares[1])
    assert len(shares) == len(counts) == snow.N_BINS == 36


def test_records_outside_the_chosen_snow_years_are_ignored():
    records = [(date(2014, 10, 1), 0), (date(2020, 10, 1), 30)]
    shares, counts = stations.snow_free_by_bin(records, 2020, 2020)
    assert shares[27] == pytest.approx(0.0)
    assert counts[27] == 1 and counts.sum() == 1


def test_a_january_day_belongs_to_the_snow_year_that_began_the_october_before():
    records = [(date(2021, 1, 15), 0)]
    assert stations.snow_free_by_bin(records, 2020, 2020)[1].sum() == 1
    assert stations.snow_free_by_bin(records, 2021, 2021)[1].sum() == 0


def test_a_july_report_is_counted_in_its_summer_bin_of_the_snow_year_before():
    # The old code only left summer out because the bin lookup returned None; now it is counted on purpose.
    records = [(date(2021, 7, 5), 0), (date(2021, 7, 6), 120)]          # day 186 and 187: bin 18
    shares, counts = stations.snow_free_by_bin(records, 2020, 2020)
    assert counts[18] == 2 and counts.sum() == 2
    assert shares[18] == pytest.approx(0.5)
    assert stations.snow_free_by_bin(records, 2021, 2021)[1].sum() == 0  # July 2021 is not snow year 2021


def test_one_half_of_the_year_can_be_asked_for_by_date():
    records = [(date(2021, 3, 31), 0), (date(2021, 4, 1), 50), (date(2021, 9, 30), 0), (date(2020, 10, 1), 50)]
    winter = stations.snow_free_by_bin(records, 2020, 2020, half="winter")[1]
    summer = stations.snow_free_by_bin(records, 2020, 2020, half="summer")[1]
    whole = stations.snow_free_by_bin(records, 2020, 2020)[1]
    assert winter.sum() == 2 and winter[8] == 1 and winter[27] == 1
    assert summer.sum() == 2 and summer[9] == 1 and summer[27] == 1     # bin 27 straddles 1 October
    assert (winter + summer == whole).all()
    with pytest.raises(ValueError):
        stations.snow_free_by_bin(records, 2020, 2020, half="spring")


def test_the_old_name_still_works_and_now_covers_the_whole_year():
    records = [(date(2021, 7, 5), 0), (date(2021, 1, 5), 0)]
    shares, counts = stations.snow_free_by_dekad(records, 2020, 2020)
    assert counts.sum() == 2 and len(shares) == 36


def test_april_to_september_reports_of_a_whole_year_land_in_bins_9_to_27():
    records = daily(date(2021, 4, 1), date(2021, 9, 30))
    _, counts = stations.snow_free_by_bin(records, 2020, 2020)
    assert counts.sum() == 183
    assert counts[9:27].tolist() == [10] * 18                           # 1 April to 27 September
    assert counts[27] == 3                                              # 28 to 30 September
    assert counts[:9].sum() == 0 and counts[28:].sum() == 0


# --- how many days a bin can hold ----------------------------------------------

def test_days_per_bin_counts_calendar_days_of_the_chosen_snow_years():
    one = stations.days_per_bin([2021])                 # 1 October 2021 to 30 September 2022, no leap day
    assert one.sum() == 365
    assert one[:35].tolist() == [10] * 35
    assert one[35] == 15                                # 17 to 31 December
    leap = stations.days_per_bin([2019])                # holds 29 February 2020
    assert leap.sum() == 366
    assert leap[35] == 15                               # December 2019 is not in a leap year
    assert leap[27] == 11                               # 1 to 7 October 2019 plus 27 to 30 September 2020
    assert stations.days_per_bin([2020])[35] == 16      # 16 to 31 December 2020 are days 351 to 366
    assert (stations.days_per_bin([2019, 2021]) == one + leap).all()
    assert stations.days_per_bin([]).sum() == 0


def test_days_per_bin_of_one_half_splits_the_bins_on_the_season_edge():
    winter = stations.days_per_bin([2021], half="winter")
    summer = stations.days_per_bin([2021], half="summer")
    assert winter[27] == 7 and summer[27] == 3          # 28 to 30 September against 1 to 7 October
    assert winter[8] == 10 and summer[8] == 0           # 22 to 31 March
    assert winter[9] == 0 and summer[9] == 10
    assert (winter + summer == stations.days_per_bin([2021])).all()
    # In a leap year 31 March is day 91, the first day of bin 9.
    assert stations.days_per_bin([2019], half="winter")[9] == 1

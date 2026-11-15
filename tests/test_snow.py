# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
import importlib
from pathlib import Path

import numpy as np
import pytest
from twinfinder import snow

FREE, SNOWY, SEA, SEA_ICE = 2, 4, 1, 3   # IMS values: snow-free land, snow on land, open sea, sea ice
ARCHIVE = Path(__file__).resolve().parents[1] / "data" / "derived" / "snow_free_dekads.npz"


def test_north_pole_is_the_grid_centre():
    rows, cols = snow.ims_rowcol([90.0], [0.0])
    assert rows[0] == pytest.approx(3072.0, abs=0.01)
    assert cols[0] == pytest.approx(3072.0, abs=0.01)


def test_60N_on_the_central_meridian_is_straight_down_from_the_pole():
    # True scale at 60N puts that parallel about 3,197 km from the pole: 799 four-km pixels.
    rows, cols = snow.ims_rowcol([60.0], [-80.0])
    assert cols[0] == pytest.approx(3072.0, abs=0.01)
    assert rows[0] == pytest.approx(3871.3, abs=3.0)


def test_bins_are_ten_calendar_days_and_cover_the_whole_year():
    assert (snow.BIN_DAYS, snow.N_BINS) == (10, 36)
    assert snow.bin_index(1) == 0
    assert snow.bin_index(10) == 0
    assert snow.bin_index(11) == 1
    assert snow.bin_index(200) == 19     # July now has a bin
    assert snow.bin_index(274) == 27     # 1 October
    assert snow.bin_index(350) == 34
    assert snow.bin_index(351) == 35
    assert snow.bin_index(365) == 35     # the last bin holds days 351 to 366
    assert snow.bin_index(366) == 35


def test_old_names_still_work_and_mean_the_calendar_bin():
    assert snow.N_DEKADS == snow.N_BINS
    assert snow.SEASON_START_DOY == 274
    assert [snow.dekad_index(day) for day in (1, 200, 274, 366)] == [0, 19, 27, 35]


def test_columns_grow_to_the_east_of_the_central_meridian_and_rows_grow_away_from_it():
    # 90 degrees east of the 80W meridian (10E) lies to the right of the pole, 100E above it, 170W to the left.
    for lon, row, col in ((10.0, 3072.0, 3871.32), (100.0, 2272.68, 3072.0), (-170.0, 3072.0, 2272.68)):
        rows, cols = snow.ims_rowcol([60.0], [lon])
        assert (rows[0], cols[0]) == pytest.approx((row, col), abs=0.02)


def test_real_places_land_where_the_map_files_put_them():
    # Worked out apart from this module: the projection formula by hand and the files' own
    # georeferencing (4 km pixels, top-left corner at x = -12,288 km, y = +12,288 km).
    rows, cols = snow.ims_rowcol([63.88, 78.2, 63.15], [-22.45, 15.6, -64.90])   # Reykjanes, Longyearbyen, Baffin
    assert rows == pytest.approx([3443.382, 3041.894, 3759.592], abs=0.01)
    assert cols == pytest.approx([3656.077, 3379.042, 3257.527], abs=0.01)


def test_a_winter_runs_from_1_october_to_20_march_and_is_named_by_its_october():
    assert snow.winter_of(2015, 274) == 2015   # 1 October 2015
    assert snow.winter_of(2015, 365) == 2015
    assert snow.winter_of(2017, 1) == 2016     # 1 January 2017 belongs to winter 2016
    assert snow.winter_of(2017, 79) == 2016    # 20 March 2017
    assert snow.winter_of(2017, 80) is None    # 21 March 2017
    assert snow.winter_of(2017, 200) is None
    assert snow.winter_of(2017, 273) is None   # 30 September 2017


def test_a_winter_goes_by_the_calendar_date_in_leap_years():
    assert snow.winter_of(2016, 79) == 2015    # 19 March 2016
    assert snow.winter_of(2016, 80) == 2015    # 20 March 2016 is day 80
    assert snow.winter_of(2016, 81) is None    # 21 March 2016
    assert snow.winter_of(2016, 274) is None   # 30 September 2016: not winter yet
    assert snow.winter_of(2016, 275) == 2016   # 1 October 2016
    assert snow.winter_of(2016, 366) == 2016   # 31 December 2016


def test_accumulate_counts_land_only():
    day = np.array([[FREE, SNOWY], [SEA, SEA_ICE]], dtype="uint8")
    free = np.zeros((snow.N_BINS, 2, 2), dtype="uint16")
    land = np.zeros((snow.N_BINS, 2, 2), dtype="uint16")
    snow.accumulate(free, land, day, dekad=3)
    snow.accumulate(free, land, day, dekad=3)
    assert free[3].tolist() == [[2, 0], [0, 0]]
    assert land[3].tolist() == [[2, 2], [0, 0]]
    assert free[0].sum() == 0


def test_accumulate_leaves_skipped_pixels_out_of_both_counts():
    day = np.array([[FREE, SNOWY], [FREE, SNOWY]], dtype="uint8")
    skip = np.array([[True, True], [False, False]])
    free = np.zeros((snow.N_BINS, 2, 2), dtype="uint16")
    land = np.zeros((snow.N_BINS, 2, 2), dtype="uint16")
    snow.accumulate(free, land, day, 30, skip=skip)
    assert free[30].tolist() == [[0, 0], [1, 0]]
    assert land[30].tolist() == [[0, 0], [1, 1]]


def test_stuck_pixels_read_snow_free_land_on_every_map_of_the_winter():
    maps = [np.array([[FREE, FREE], [SEA, FREE]], dtype="uint8"),
            np.array([[FREE, SNOWY], [SEA, SEA_ICE]], dtype="uint8"),
            np.array([[FREE, FREE], [SEA, FREE]], dtype="uint8")]
    # Only the first pixel never changes; one snowy map or one sea-ice map is enough to count as observed.
    assert snow.stuck_pixels(maps).tolist() == [[True, False], [False, False]]


def test_a_stuck_winter_is_left_out_and_the_other_winters_give_the_odds():
    free = np.zeros((snow.N_BINS, 1, 2), dtype="uint16")
    land = np.zeros((snow.N_BINS, 1, 2), dtype="uint16")
    bins = [snow.bin_index(day) for day in (274, 284, 1)]
    # Winter one: the left pixel says snow-free on every map (a stale flag in the polar night).
    winter_one = [np.array([[FREE, FREE]], dtype="uint8"),
                  np.array([[FREE, SNOWY]], dtype="uint8"),
                  np.array([[FREE, SNOWY]], dtype="uint8")]
    # Winter two: it is seen to change, so this winter counts.
    winter_two = [np.array([[FREE, FREE]], dtype="uint8"),
                  np.array([[SNOWY, SNOWY]], dtype="uint8"),
                  np.array([[SNOWY, SNOWY]], dtype="uint8")]
    stuck_one = snow.accumulate_winter(free, land, winter_one, bins)
    stuck_two = snow.accumulate_winter(free, land, winter_two, bins)
    assert stuck_one.tolist() == [[True, False]]
    assert stuck_two.tolist() == [[False, False]]
    assert land[bins[0]].tolist() == [[1, 2]]     # the left pixel was counted in one winter only
    assert free[bins[0]].tolist() == [[1, 2]]
    assert land[bins[1]].tolist() == [[1, 2]]
    assert free[bins[1]].tolist() == [[0, 0]]     # without the rule the left pixel would read 1 of 2


def test_after_a_stuck_winter_a_pixel_stays_left_out_until_its_first_snowy_map():
    free = np.zeros((snow.N_BINS, 1, 3), dtype="uint16")
    land = np.zeros((snow.N_BINS, 1, 3), dtype="uint16")
    stuck = np.array([[True, True, False]])           # the right pixel was seen to change in the winter
    spring = [np.array([[FREE, FREE, FREE]], dtype="uint8"),
              np.array([[FREE, SNOWY, SNOWY]], dtype="uint8"),
              np.array([[FREE, FREE, FREE]], dtype="uint8")]
    still = snow.accumulate_after_winter(free, land, spring, [8, 9, 10], stuck)
    # Left: never snowy, so never counted. Middle: counted from its first snowy map on, that map included.
    assert land[[8, 9, 10]].tolist() == [[[0, 0, 1]], [[0, 1, 1]], [[0, 1, 1]]]
    assert free[[8, 9, 10]].tolist() == [[[0, 0, 1]], [[0, 0, 0]], [[0, 1, 1]]]
    assert still.tolist() == [[True, False, False]]   # the left pixel's flag is still unchanged at the end
    assert stuck.tolist() == [[True, True, False]]    # the winter's mask itself is not altered


def test_only_a_snowy_map_ends_the_stale_run():
    # A sea or sea-ice reading is not a look at the ground: the flag after it is no better than before.
    free = np.zeros((snow.N_BINS, 1, 2), dtype="uint16")
    land = np.zeros((snow.N_BINS, 1, 2), dtype="uint16")
    spring = [np.array([[SEA_ICE, SEA]], dtype="uint8"), np.array([[FREE, FREE]], dtype="uint8")]
    still = snow.accumulate_after_winter(free, land, spring, [8, 9], np.array([[True, True]]))
    assert land.sum() == 0 and free.sum() == 0
    assert still.tolist() == [[True, True]]


def test_after_a_winter_without_stuck_pixels_every_map_counts():
    free = np.zeros((snow.N_BINS, 1, 2), dtype="uint16")
    land = np.zeros((snow.N_BINS, 1, 2), dtype="uint16")
    spring = [np.array([[FREE, SNOWY]], dtype="uint8"), np.array([[FREE, SEA]], dtype="uint8")]
    snow.accumulate_after_winter(free, land, spring, [8, 8], np.array([[False, False]]))
    assert land[8].tolist() == [[2, 1]] and free[8].tolist() == [[2, 0]]


def test_ims_url_follows_the_archive_pattern():
    assert snow.ims_url(2015, 274) == ("https://noaadata.apps.nsidc.org/NOAA/G02156/GIS/4km/2015/"
                                       "ims2015274_4km_GIS_v1.3.tif.gz")
    assert snow.ims_url(2016, 6).endswith("/2016/ims2016006_4km_GIS_v1.3.tif.gz")


def test_nearest_day_takes_the_closest_map_within_two_days():
    assert snow.nearest_day(81, {76, 81, 86}) == 81
    assert snow.nearest_day(195, {190, 194, 197}) == 194
    assert snow.nearest_day(195, {193, 197}) == 193      # a tie goes to the earlier day
    assert snow.nearest_day(195, {190, 198, 200}) is None
    assert snow.nearest_day(195, {196, 197}, reach=0) is None


def test_cell_probabilities_average_the_three_by_three_neighbourhood():
    # A 5 x 5 crop whose centre pixel is the North Pole (grid position 3072, 3072).
    crop = np.full((snow.N_BINS, 5, 5), 1.0, dtype="float32")
    crop[:, 2, 2] = np.nan      # the centre pixel itself is sea
    crop[0, 1, 1] = 0.2         # one neighbour differs in the first bin
    values = snow.cell_probabilities(crop, row0=3070, col0=3070, lat=90.0, lon=0.0)
    assert values.shape == (snow.N_BINS,)
    assert values[0] == pytest.approx((7 * 1.0 + 0.2) / 8)
    assert values[1] == pytest.approx(1.0)


def test_the_block_sits_around_the_pixel_that_holds_the_point():
    # A point on Baffin Island falls at row 3759.59, column 3257.53 of the grid: pixel row 3759, column 3257
    # (the fractions are cut off, not rounded). In this 20 x 12 crop that pixel is crop[9, 7].
    lat, lon, row0, col0 = 63.15, -64.90, 3750, 3250
    crop = np.full((snow.N_BINS, 20, 12), np.nan, dtype="float32")
    crop[:, 8, 6] = 0.2      # top-left corner of the 3 x 3 block
    crop[:, 11, 9] = 0.9     # one step past its bottom-right corner: only a rounded-up pixel would reach it
    crop[:, 6, 10] = 0.7     # where the block would sit with rows and columns swapped
    assert snow.cell_probabilities(crop, row0, col0, lat, lon) == pytest.approx(np.full(snow.N_BINS, 0.2))
    assert snow.cell_land_pixels(crop, row0, col0, lat, lon) == 1
    values, source = snow.cell_probabilities_filled(crop, row0, col0, lat, lon)
    assert source == "3x3" and values == pytest.approx(np.full(snow.N_BINS, 0.2))
    stuck = np.zeros((20, 12), dtype="uint8")
    stuck[10, 8] = 4         # bottom-right corner of the 3 x 3 block
    stuck[11, 9] = 9         # bottom-right corner of the 5 x 5 block
    stuck[6, 10] = 7
    assert snow.cell_stuck_winters(stuck, row0, col0, lat, lon) == 4
    assert snow.cell_stuck_winters(stuck, row0, col0, lat, lon, reach=2) == 9


def test_the_five_by_five_block_is_two_pixels_each_way_off_the_pole_too():
    lat, lon, row0, col0 = 63.15, -64.90, 3750, 3250             # the point's pixel is crop[9, 7]
    crop = np.full((snow.N_BINS, 20, 12), np.nan, dtype="float32")
    crop[:, 7, 5] = 0.4      # top-left corner of the 5 x 5 block
    crop[:, 12, 7] = 0.0     # three rows down: never used
    crop[:, 9, 10] = 0.0     # three columns right: never used
    values, source = snow.cell_probabilities_filled(crop, row0, col0, lat, lon)
    assert source == "5x5" and values == pytest.approx(np.full(snow.N_BINS, 0.4))
    assert snow.cell_land_pixels(crop, row0, col0, lat, lon) == 0


def test_cell_probabilities_are_nan_when_no_land_is_near():
    crop = np.full((snow.N_BINS, 5, 5), np.nan, dtype="float32")
    values = snow.cell_probabilities(crop, row0=3070, col0=3070, lat=90.0, lon=0.0)
    assert np.isnan(values).all()


def test_a_point_outside_the_crop_has_no_snow_data():
    # 89N on the 100E meridian lies 26 pixels above the top edge of this crop; nothing may be borrowed from inside it.
    crop = np.full((snow.N_BINS, 40, 40), 0.5, dtype="float32")
    values = snow.cell_probabilities(crop, row0=3072, col0=3052, lat=89.0, lon=100.0)
    assert np.isnan(values).all()
    assert snow.cell_land_pixels(crop, row0=3072, col0=3052, lat=89.0, lon=100.0) == 0
    values, source = snow.cell_probabilities_filled(crop, row0=3072, col0=3052, lat=89.0, lon=100.0)
    assert np.isnan(values).all() and source is None
    # Antarctica is far outside the northern grid.
    assert np.isnan(snow.cell_probabilities(crop, row0=3072, col0=3052, lat=-77.5, lon=162.0)).all()


def test_cell_land_pixels_counts_observed_neighbours():
    # Few land pixels around a point means a fjord, a coast or a small island,
    # where the 4 km snow maps are least reliable.
    crop = np.full((snow.N_BINS, 5, 5), np.nan, dtype="float32")
    crop[:, 1, 1] = 0.5
    crop[:, 2, 3] = 0.0
    assert snow.cell_land_pixels(crop, row0=3070, col0=3070, lat=90.0, lon=0.0) == 2


def test_filled_lookup_uses_the_three_by_three_block_when_it_has_land():
    crop = np.full((snow.N_BINS, 5, 5), 0.0, dtype="float32")   # the outer ring is always snowy ...
    crop[:, 1:4, 1:4] = np.nan
    crop[:, 1, 2] = 0.6                                         # ... and one inner neighbour is land
    crop[5, 1, 2] = np.nan                                      # except in one bin, which stays unknown
    values, source = snow.cell_probabilities_filled(crop, row0=3070, col0=3070, lat=90.0, lon=0.0)
    assert source == "3x3"
    assert values[0] == pytest.approx(0.6)
    assert np.isnan(values[5])                                  # the 5 x 5 ring does not fill single bins
    plain = snow.cell_probabilities(crop, row0=3070, col0=3070, lat=90.0, lon=0.0)
    assert np.array_equal(values, plain, equal_nan=True)


def test_filled_lookup_borrows_the_five_by_five_block_only_without_nearer_land():
    crop = np.full((snow.N_BINS, 7, 7), np.nan, dtype="float32")
    crop[:, 1, 3] = 0.4         # two pixels up from the centre: inside 5 x 5, outside 3 x 3
    crop[:, 5, 5] = 0.8         # the far corner of the 5 x 5 block
    crop[:, 0, 0] = 0.0         # three pixels away: never used
    values, source = snow.cell_probabilities_filled(crop, row0=3069, col0=3069, lat=90.0, lon=0.0)
    assert source == "5x5"
    assert values == pytest.approx(np.full(snow.N_BINS, 0.6))
    assert np.isnan(snow.cell_probabilities(crop, row0=3069, col0=3069, lat=90.0, lon=0.0)).all()


def test_filled_lookup_says_none_when_no_land_is_within_two_pixels():
    crop = np.full((snow.N_BINS, 7, 7), np.nan, dtype="float32")
    crop[:, 0, 0] = 0.3
    values, source = snow.cell_probabilities_filled(crop, row0=3069, col0=3069, lat=90.0, lon=0.0)
    assert source is None
    assert values.shape == (snow.N_BINS,) and np.isnan(values).all()


def test_cell_stuck_winters_is_the_worst_pixel_of_the_block():
    stuck = np.zeros((7, 7), dtype="uint8")
    stuck[2, 4] = 3             # inside the 3 x 3 block around the centre
    stuck[1, 3] = 7             # only inside the 5 x 5 block
    assert snow.cell_stuck_winters(stuck, row0=3069, col0=3069, lat=90.0, lon=0.0) == 3
    assert snow.cell_stuck_winters(stuck, row0=3069, col0=3069, lat=90.0, lon=0.0, reach=2) == 7
    assert snow.cell_stuck_winters(stuck, row0=3069, col0=3069, lat=-77.5, lon=162.0) == 0


def test_snow_free_share_averages_over_the_window_days():
    probabilities = np.full(snow.N_BINS, np.nan)
    probabilities[27] = 1.0   # 28 September to 7 October
    probabilities[28] = 0.5   # 8 to 17 October
    days = list(range(276, 286))  # five days in each bin
    assert snow.snow_free_share(probabilities, days) == pytest.approx(0.75)


def test_snow_free_share_covers_summer_days_too():
    probabilities = np.zeros(snow.N_BINS)
    probabilities[19] = 1.0   # 10 to 19 July
    probabilities[20] = 0.5   # 20 to 29 July
    assert snow.snow_free_share(probabilities, list(range(196, 206))) == pytest.approx(0.75)
    assert snow.snow_free_share(probabilities, [366]) == pytest.approx(0.0)


def test_snow_free_share_is_none_without_observations():
    assert snow.snow_free_share(np.full(snow.N_BINS, np.nan), [300, 301]) is None
    assert snow.snow_free_share(np.ones(snow.N_BINS), []) is None


def test_the_build_takes_one_winter_at_a_time(monkeypatch):
    script = importlib.import_module("scripts.build_snow_climatology")
    # Readings of four pixels on ten maps, as (year, day of year): a pixel whose flag never changes,
    # an ordinary one, open sea, and one that turns snow-free for good in summer 2016.
    series = {
        (2015, 271): (FREE, FREE, SEA, SNOWY),    # 28 September 2015: before the winter
        (2015, 274): (FREE, FREE, SEA, SNOWY),    # 1 October: winter 2015 begins
        (2015, 364): (FREE, FREE, SEA, SNOWY),
        (2016, 1): (FREE, SNOWY, SEA, SNOWY),     # the same winter goes on after the year turns
        (2016, 76): (FREE, SNOWY, SEA, SNOWY),
        (2016, 81): (FREE, SNOWY, SEA, SNOWY),    # 21 March 2016: after the winter
        (2016, 200): (FREE, FREE, SEA, FREE),
        (2016, 274): (FREE, FREE, SEA, SNOWY),    # 30 September of a leap year: not winter yet
        (2016, 279): (FREE, FREE, SEA, FREE),     # winter 2016
        (2017, 6): (FREE, SNOWY, SEA, FREE),
    }
    monkeypatch.setattr(script, "CROP_HALF_PX", 1)
    monkeypatch.setattr(script, "MIN_WINTER_MAPS", 1)
    monkeypatch.setattr(script, "read_map", lambda path, row0, col0, n: np.array(
        series[script.year_and_day(path)], dtype="uint8").reshape(2, 2))
    files = [Path(f"ims{year}{day:03d}_4km_GIS_v1.3.tif.gz") for year, day in sorted(series)]

    result = script.build(files)
    odds = result["probabilities"]
    assert odds.shape == (snow.N_BINS, 2, 2) and odds.dtype == np.float32
    assert (result["row0"], result["col0"]) == (3071, 3071)
    assert result["maps_per_winter"] == {2015: 4, 2016: 2}
    per_bin = result["maps_per_bin"].tolist()
    assert (per_bin[0], per_bin[7], per_bin[8], per_bin[19], per_bin[27], per_bin[35]) == (2, 1, 1, 1, 4, 1)
    assert sum(per_bin) == 10
    # The unchanging pixel is stuck in both winters; the ordinary one was free until December and is
    # not stuck, because January belongs to the same winter; the last one is stuck in winter 2016 only.
    assert result["stuck_winters"].dtype == np.uint8
    assert result["stuck_winters"].tolist() == [[2, 0], [0, 1]]
    stale, normal, sea, late = (odds[:, row, col] for row, col in ((0, 0), (0, 1), (1, 0), (1, 1)))
    assert np.isnan(stale[[0, 7, 35]]).all()                  # its winter readings are left out ...
    assert np.isnan(stale[[8, 19]]).all()                     # ... and so are 21 March and July, since it never read snow
    assert stale[27] == 1.0                                   # only 28 September 2015, before the first winter, counts
    assert normal[[0, 7, 8, 19, 27, 35]].tolist() == [0.0, 0.0, 0.0, 1.0, 1.0, 1.0]
    assert np.isnan(sea).all()
    assert late[[0, 7, 8, 19, 27, 35]].tolist() == [0.0, 0.0, 0.0, 1.0, 0.0, 0.0]   # bin 27: 0 of 3, bin 0: 0 of 1

    plain = script.build(files, stale_flag_rule=False)
    assert plain["stuck_winters"].tolist() == [[0, 0], [0, 0]]
    assert plain["probabilities"][[0, 7, 35], 0, 0].tolist() == [1.0, 1.0, 1.0]
    assert plain["probabilities"][[0, 27], 1, 1].tolist() == [0.5, 0.25]
    assert plain["probabilities"][[8, 19, 27], 0, 0].tolist() == [1.0, 1.0, 1.0]


# Four made-up pixels on 16 maps over two winters and the two open seasons after them, as (year, day of year).
#   late:   stuck in winter 2015; its flag first changes on 10 May 2016.
#   never:  stuck in winter 2015 and snow-free on every map up to 30 September 2016; seen to change in winter 2016.
#   normal: changes in both winters.
#   second: changes in winter 2015, stuck in winter 2016; reads snow again on 20 July 2017.
SPRING_SERIES = {
    (2015, 274): (FREE, FREE, FREE, FREE),      # 1 October 2015: winter 2015 begins            bin 27
    (2015, 334): (FREE, FREE, SNOWY, FREE),     #                                               bin 33
    (2016, 31): (FREE, FREE, SNOWY, SNOWY),     #                                               bin 3
    (2016, 80): (FREE, FREE, SNOWY, FREE),      # 20 March 2016 (leap year): last winter day    bin 7
    (2016, 81): (FREE, FREE, SNOWY, SNOWY),     # 21 March 2016                                 bin 8
    (2016, 111): (FREE, FREE, SNOWY, SNOWY),    #                                               bin 11
    (2016, 131): (SNOWY, FREE, FREE, FREE),     # 10 May 2016: the only map in its bin          bin 13
    (2016, 201): (FREE, FREE, FREE, FREE),      #                                               bin 20
    (2016, 274): (FREE, FREE, FREE, FREE),      # 30 September 2016: last day before the winter bin 27
    (2016, 275): (FREE, SNOWY, FREE, FREE),     # 1 October 2016: winter 2016 begins            bin 27
    (2016, 335): (SNOWY, FREE, SNOWY, FREE),    #                                               bin 33
    (2017, 31): (SNOWY, FREE, SNOWY, FREE),     #                                               bin 3
    (2017, 79): (SNOWY, FREE, SNOWY, FREE),     # 20 March 2017                                 bin 7
    (2017, 81): (SNOWY, FREE, FREE, FREE),      # 22 March 2017                                 bin 8
    (2017, 111): (SNOWY, SNOWY, FREE, FREE),    #                                               bin 11
    (2017, 201): (SNOWY, SNOWY, FREE, SNOWY),   # 20 July 2017                                  bin 20
}
SPRING_BINS = [3, 7, 8, 11, 13, 20, 27, 33]


def spring_build(monkeypatch, **options) -> dict:
    """Run the build on the made-up maps above; the four pixels come back as odds[:, 0, 0] ... odds[:, 1, 1]."""
    script = importlib.import_module("scripts.build_snow_climatology")
    monkeypatch.setattr(script, "CROP_HALF_PX", 1)
    monkeypatch.setattr(script, "MIN_WINTER_MAPS", 1)
    monkeypatch.setattr(script, "read_map", lambda path, row0, col0, n: np.array(
        SPRING_SERIES[script.year_and_day(path)], dtype="uint8").reshape(2, 2))
    files = [Path(f"ims{year}{day:03d}_4km_GIS_v1.3.tif.gz") for year, day in sorted(SPRING_SERIES)]
    return script.build(files, **options)


def test_a_stuck_pixel_stays_left_out_in_spring_until_its_first_snowy_map(monkeypatch):
    result = spring_build(monkeypatch)
    assert result["stuck_winters"].tolist() == [[1, 1], [0, 1]]
    late = result["probabilities"][SPRING_BINS, 0, 0]
    # Winter 2015 and the maps of 21 March and 20 April 2016 are left out, so those bins rest on 2017 alone.
    # 10 May 2016 is its first snowy map and counts (0 of 1, not unknown); 19 July 2016 counts too (1 of 2).
    assert late.tolist() == [0.0, 0.0, 0.0, 0.0, 0.0, 0.5, 1.0, 0.0]
    as_mapped = result["probabilities_as_mapped"][SPRING_BINS, 0, 0]
    assert as_mapped.tolist() == [0.5, 0.5, 0.5, 0.5, 0.0, 0.5, 1.0, 0.5]


def test_a_stuck_pixel_that_never_reads_snow_is_left_out_to_30_september_and_the_next_winter_is_judged_afresh(monkeypatch):
    result = spring_build(monkeypatch)
    never = result["probabilities"][SPRING_BINS, 0, 1]
    # Bin 13 holds only the map of 10 May 2016: unknown. Bin 27 holds 1 October 2015 and 30 September 2016
    # (both left out) and 1 October 2016 (snowy, counted): 0 of 1. With 30 September counted it would be 0.5.
    # Winter 2016 is not stuck, so its maps and those of spring 2017 count as they read.
    assert np.isnan(never[4])
    assert never[[0, 1, 2, 3, 5, 6, 7]].tolist() == [1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 1.0]
    as_mapped = result["probabilities_as_mapped"][SPRING_BINS, 0, 1]
    assert as_mapped.tolist() == pytest.approx([1.0, 1.0, 1.0, 0.5, 1.0, 0.5, 2 / 3, 1.0])


def test_a_pixel_that_is_not_stuck_is_untouched_by_the_rule(monkeypatch):
    result = spring_build(monkeypatch)
    plain = spring_build(monkeypatch, stale_flag_rule=False)
    normal = result["probabilities"][:, 1, 0]
    assert np.array_equal(normal, plain["probabilities"][:, 1, 0], equal_nan=True)
    assert normal[SPRING_BINS].tolist() == [0.0, 0.0, 0.5, 0.5, 1.0, 1.0, 1.0, 0.0]
    # The pixel stuck in the second winter only: spring 2016 counts as it reads (two snowy maps, bins 8 and 11),
    # winter 2016 and spring 2017 are left out up to its snowy map of 20 July 2017.
    second = result["probabilities"][SPRING_BINS, 1, 1]
    assert second.tolist() == [0.0, 1.0, 0.0, 0.0, 1.0, 0.5, 1.0, 1.0]
    assert plain["probabilities"][SPRING_BINS, 1, 1].tolist() == [0.5, 1.0, 0.5, 0.5, 1.0, 0.5, 1.0, 1.0]


def test_the_build_also_gives_the_odds_as_mapped_with_no_rule_at_all(monkeypatch):
    result = spring_build(monkeypatch)
    plain = spring_build(monkeypatch, stale_flag_rule=False)
    as_mapped = result["probabilities_as_mapped"]
    assert as_mapped.shape == result["probabilities"].shape == (snow.N_BINS, 2, 2)
    assert as_mapped.dtype == np.float32
    assert np.array_equal(as_mapped, plain["probabilities"], equal_nan=True)
    assert np.array_equal(plain["probabilities_as_mapped"], plain["probabilities"], equal_nan=True)
    assert plain["stuck_winters"].tolist() == [[0, 0], [0, 0]]
    assert not np.array_equal(as_mapped, result["probabilities"], equal_nan=True)


def made_up_build(monkeypatch, series, min_winter_maps=1, order=sorted, **options) -> dict:
    """Run the build on made-up maps; series gives the readings of four pixels per (year, day of year)."""
    script = importlib.import_module("scripts.build_snow_climatology")
    monkeypatch.setattr(script, "CROP_HALF_PX", 1)
    monkeypatch.setattr(script, "MIN_WINTER_MAPS", min_winter_maps)
    monkeypatch.setattr(script, "read_map", lambda path, row0, col0, n: np.array(
        series[script.year_and_day(path)], dtype="uint8").reshape(2, 2))
    files = [Path(f"ims{year}{day:03d}_4km_GIS_v1.3.tif.gz") for year, day in order(series)]
    return script.build(files, **options)


def test_a_stale_run_ends_on_30_september_even_if_the_flag_has_still_not_changed(monkeypatch):
    # The left pixel is stuck in winter 2015 and stays snow-free through 1 October 2016; it turns snowy in
    # November. Winter 2016 is seen to change, so all of its maps count, the snow-free one of 1 October
    # included: the run that began in winter 2015 does not reach past 30 September.
    series = {
        (2015, 274): (FREE, SNOWY, SEA, SEA),     # 1 October 2015                  bin 27
        (2016, 31): (FREE, SNOWY, SEA, SEA),      #                                 bin 3
        (2016, 201): (FREE, SNOWY, SEA, SEA),     # 19 July 2016: left out          bin 20
        (2016, 274): (FREE, SNOWY, SEA, SEA),     # 30 September 2016: left out     bin 27
        (2016, 275): (FREE, SNOWY, SEA, SEA),     # 1 October 2016: counts          bin 27
        (2016, 335): (SNOWY, SNOWY, SEA, SEA),    # 30 November 2016                bin 33
        (2017, 201): (FREE, SNOWY, SEA, SEA),     # 20 July 2017: counts            bin 20
    }
    result = made_up_build(monkeypatch, series)
    assert result["stuck_winters"].tolist() == [[1, 0], [0, 0]]
    odds = result["probabilities"][:, 0, 0]
    assert np.isnan(odds[3])                                  # only the stuck winter has a map there
    assert odds[[20, 27, 33]].tolist() == [1.0, 1.0, 0.0]     # one reading each; bin 27 is 1 October 2016
    assert result["probabilities_as_mapped"][[3, 20, 27, 33], 0, 0].tolist() == [1.0, 1.0, 1.0, 0.0]
    assert (result["probabilities"][:, 0, 1][[3, 20, 27, 33]] == 0).all()   # the ordinary pixel beside it


def test_a_winter_with_too_few_maps_is_not_judged_and_nothing_follows_it(monkeypatch):
    # The left pixel reads snow-free on every map. Winter 2015 has two maps where three are asked for, so
    # "snow-free on every map" says too little: that winter and the spring after it count as they read.
    # Winter 2016 has exactly three maps and is judged: stuck, and left out with the spring after it.
    series = {
        (2015, 274): (FREE, SNOWY, SEA, SEA),     # winter 2015, 1 October          bin 27
        (2016, 31): (FREE, SNOWY, SEA, SEA),      #                                 bin 3
        (2016, 111): (FREE, SNOWY, SEA, SEA),     # 20 April 2016                   bin 11
        (2016, 275): (FREE, SNOWY, SEA, SEA),     # winter 2016, 1 October          bin 27
        (2016, 335): (FREE, SNOWY, SEA, SEA),     #                                 bin 33
        (2017, 31): (FREE, SNOWY, SEA, SEA),      #                                 bin 3
        (2017, 111): (FREE, SNOWY, SEA, SEA),     # 21 April 2017                   bin 11
    }
    result = made_up_build(monkeypatch, series, min_winter_maps=3)
    assert result["maps_per_winter"] == {2015: 2, 2016: 3}
    assert result["stuck_winters"].tolist() == [[1, 0], [0, 0]]
    odds = result["probabilities"][:, 0, 0]
    assert odds[[3, 11, 27]].tolist() == [1.0, 1.0, 1.0]      # the readings of 2015/16
    assert np.isnan(odds[33])                                 # only the stuck winter has a map in this bin
    assert set(result["stale_runs"]) == {2016}                # no run follows the short winter


def test_the_build_puts_the_maps_in_date_order_itself(monkeypatch):
    in_order = made_up_build(monkeypatch, SPRING_SERIES)
    backwards = made_up_build(monkeypatch, SPRING_SERIES, order=lambda series: sorted(series, reverse=True))
    for key in ("probabilities", "probabilities_as_mapped", "stuck_winters", "maps_per_bin"):
        assert np.array_equal(in_order[key], backwards[key], equal_nan=True)
    assert backwards["probabilities"][SPRING_BINS, 0, 0].tolist() == [0.0, 0.0, 0.0, 0.0, 0.0, 0.5, 1.0, 0.0]


def test_cell_land_pixels_counts_a_pixel_seen_as_land_in_any_bin():
    # Under the stale-flag rule a land pixel can be unknown in some bins; it is still a land pixel.
    crop = np.full((snow.N_BINS, 5, 5), np.nan, dtype="float32")
    crop[20, 2, 2] = 1.0        # known in one summer bin only
    crop[:, 1, 2] = 0.0
    assert snow.cell_land_pixels(crop, row0=3070, col0=3070, lat=90.0, lon=0.0) == 2


def test_main_writes_the_archive_to_a_side_file_and_swaps_it_in(monkeypatch, tmp_path, capsys):
    script = importlib.import_module("scripts.build_snow_climatology")
    out = tmp_path / "derived" / "snow_free_dekads.npz"
    out.parent.mkdir()
    out.write_bytes(b"the archive of the run before")
    monkeypatch.setattr(script, "OUT", out)
    monkeypatch.setattr(script, "CROP_HALF_PX", 1)
    monkeypatch.setattr(script, "MIN_WINTER_MAPS", 1)
    monkeypatch.setattr(script, "read_map", lambda path, row0, col0, n: np.array(
        SPRING_SERIES[script.year_and_day(path)], dtype="uint8").reshape(2, 2))
    monkeypatch.setattr(script, "map_files", lambda: [
        Path(f"ims{year}{day:03d}_4km_GIS_v1.3.tif.gz") for year, day in sorted(SPRING_SERIES)])
    monkeypatch.setattr(script.sys, "argv", ["build_snow_climatology.py"])
    written, tables = [], []
    real_save = np.savez_compressed

    def watched_save(path, **arrays):
        written.append(Path(path))
        assert out.read_bytes() == b"the archive of the run before"   # a reader still finds the old one whole
        real_save(path, **arrays)

    monkeypatch.setattr(script.np, "savez_compressed", watched_save)
    monkeypatch.setattr(script, "print_checks", lambda title, odds, row0, col0: tables.append((title, odds)))
    script.main()

    assert written == [out.with_name("snow_free_dekads.part.npz")]
    assert [path.name for path in out.parent.iterdir()] == ["snow_free_dekads.npz"]    # the side file is gone
    archive = np.load(out)                                    # no pickled objects: plain arrays only
    assert sorted(archive.files) == ["col0", "files", "maps_per_bin", "probabilities",
                                     "probabilities_as_mapped", "row0", "stuck_winters"]
    assert int(archive["files"]) == len(SPRING_SERIES) == 16
    assert (int(archive["row0"]), int(archive["col0"])) == (3071, 3071)
    odds, as_mapped = archive["probabilities"], archive["probabilities_as_mapped"]
    assert odds.dtype == as_mapped.dtype == np.float32
    assert odds.shape == as_mapped.shape == (snow.N_BINS, 2, 2)
    assert archive["stuck_winters"].dtype == np.uint8 and archive["stuck_winters"].tolist() == [[1, 1], [0, 1]]
    assert archive["maps_per_bin"].shape == (snow.N_BINS,) and int(archive["maps_per_bin"].sum()) == 16
    assert odds[SPRING_BINS, 0, 0].tolist() == [0.0, 0.0, 0.0, 0.0, 0.0, 0.5, 1.0, 0.0]
    assert as_mapped[SPRING_BINS, 0, 0].tolist() == [0.5, 0.5, 0.5, 0.5, 0.0, 0.5, 1.0, 0.5]
    # The check table is printed twice: first with the rule, then as mapped.
    assert len(tables) == 2
    assert "with the stale-flag rule" in tables[0][0] and np.array_equal(tables[0][1], odds, equal_nan=True)
    assert "as mapped" in tables[1][0] and np.array_equal(tables[1][1], as_mapped, equal_nan=True)
    assert "used 16 maps" in capsys.readouterr().out


def test_the_check_table_uses_the_eight_named_points_and_shows_an_unknown_bin_as_a_dash(capsys):
    script = importlib.import_module("scripts.build_snow_climatology")
    names = [name for name, _, _ in script.CHECKS]
    assert [(lat, lon) for _, lat, lon in script.CHECKS] == [
        (66.5833, -52.2), (68.04, 13.35), (63.88, -22.45), (78.2, 15.6),
        (74.45, 19.25), (70.95, -8.55), (63.15, -64.90), (75.38, -89.67)]
    for name, word in zip(names, ("Qaqortorsuaq", "Lofoten", "Reykjanes", "Longyearbyen",
                                  "Bear Island", "Jan Mayen", "Baffin", "Devon Island")):
        assert word in name
    # Three by three pixels around the one that holds Bear Island (row 3006, column 3474 of the grid,
    # worked out apart from this module); the other seven points lie outside this crop.
    crop = np.full((snow.N_BINS, 3, 3), np.nan, dtype="float32")
    crop[:, 1, 1] = 0.25
    crop[8, 1, 1] = np.nan          # one bin without a land reading
    crop[35, 1, 1] = 0.0            # a bin that is known and always snowy
    script.print_checks("Made-up odds", crop, 3005, 3473)
    lines = capsys.readouterr().out.splitlines()
    rows = {name: [line[36:].split() for line in lines if line.startswith(name)] for name in names}
    assert all(len(halves) == 2 for halves in rows.values())  # one line per half-year for each point
    assert rows["Bear Island"][0] == ["0.25"] * 8 + ["-"] + ["0.25"] * 9
    assert rows["Bear Island"][1] == ["0.25"] * 17 + ["0.00"]
    for name in names:
        if name != "Bear Island":
            assert rows[name] == [["-"] * 18, ["-"] * 18]     # no data is a dash, never 0.00


def test_the_download_takes_a_neighbouring_day_for_a_gap_and_reports_what_is_missing(monkeypatch, tmp_path, capsys):
    script = importlib.import_module("scripts.build_snow_climatology")
    name = "ims2017{:03d}_4km_GIS_v1.3.tif.gz"
    (tmp_path / name.format(314)).touch()                      # one of the wanted maps is on disk already
    fetched = []

    def fake_fetch(url, dest_dir):
        fetched.append(url)
        (dest_dir / url.rsplit("/", 1)[-1]).touch()

    monkeypatch.setattr(script, "IMS_DIR", tmp_path)
    monkeypatch.setattr(script, "URLS", tmp_path / "urls.txt")
    monkeypatch.setattr(script, "FIRST", (2017, 300))          # the every-5th-day run holds days 304, 309, 314, 319
    monkeypatch.setattr(script, "LAST", (2017, 320))
    monkeypatch.setattr(script, "fetch", fake_fetch)
    # The server lacks days 303 to 305, 307 to 311, 318 and 319.
    monkeypatch.setattr(script, "days_on_server", lambda year: {300, 301, 302, 306, 312, 313, 314, 315, 316, 317, 320})

    script.download_missing()
    assert sorted(fetched) == [snow.ims_url(2017, 302), snow.ims_url(2017, 320)]   # 302 and 306 tie: the earlier one
    said = capsys.readouterr().out
    assert "wanted 4 maps" in said and "1 on disk" in said
    assert "2017-304 by 2017-302" in said and "2017-319 by 2017-320" in said
    assert "['2017-309']" in said                              # no map within two days: reported, not replaced
    assert (tmp_path / "urls.txt").read_text().splitlines() == [snow.ims_url(2017, day) for day in (302, 314, 320)]

    fetched.clear()
    script.download_missing()                                  # the neighbours now stand in for their days
    assert fetched == []


@pytest.mark.skipif(not ARCHIVE.exists(), reason="the snow archive has not been built")
def test_the_built_archive_has_the_agreed_layout_and_calendar_bins():
    archive = np.load(ARCHIVE)
    odds, stuck, per_bin = archive["probabilities"], archive["stuck_winters"], archive["maps_per_bin"]
    row0, col0 = int(archive["row0"]), int(archive["col0"])
    assert odds.dtype == np.float32 and odds.shape[0] == snow.N_BINS
    assert stuck.dtype == np.uint8 and stuck.shape == odds.shape[1:]
    assert per_bin.shape == (snow.N_BINS,) and per_bin.min() > 0
    assert np.nanmin(odds) >= 0 and np.nanmax(odds) <= 1
    assert not stuck[~np.isfinite(odds).any(axis=0)].any()        # only land pixels can be stuck
    # The bins follow the calendar year, not the old count from 1 October.
    ice_sheet = snow.cell_probabilities(odds, row0, col0, 72.0, -40.0)
    assert (ice_sheet == 0).all()
    reykjanes = snow.cell_probabilities(odds, row0, col0, 63.88, -22.45)
    assert reykjanes[12:27].min() > 0.95 and reykjanes[0:6].max() < 0.5     # May to September; January and February
    longyearbyen = snow.cell_probabilities(odds, row0, col0, 78.2, 15.6)
    assert longyearbyen[0:12].max() < 0.02 and 21 <= longyearbyen.argmax() <= 24   # bare ground peaks in August
    # The two islands that ranked high on stale flags are marked.
    assert snow.cell_stuck_winters(stuck, row0, col0, 74.45, 19.25) >= 1     # Bear Island
    assert snow.cell_stuck_winters(stuck, row0, col0, 70.95, -8.55) >= 1     # Jan Mayen


@pytest.mark.skipif(not ARCHIVE.exists(), reason="the snow archive has not been built")
def test_the_built_archive_keeps_the_odds_as_mapped_beside_the_ruled_ones():
    archive = np.load(ARCHIVE)
    odds, as_mapped, stuck = archive["probabilities"], archive["probabilities_as_mapped"], archive["stuck_winters"]
    row0, col0 = int(archive["row0"]), int(archive["col0"])
    assert as_mapped.dtype == np.float32 and as_mapped.shape == odds.shape
    assert set(archive.files) >= {"files", "probabilities", "probabilities_as_mapped", "row0", "col0",
                                  "stuck_winters", "maps_per_bin"}
    assert int(archive["files"]) == int(archive["maps_per_bin"].sum())
    assert np.array_equal(np.isfinite(as_mapped).any(axis=0), np.isfinite(odds).any(axis=0) | (stuck > 0))
    # A pixel without a stuck winter is untouched by the rule.
    assert np.array_equal(odds[:, stuck == 0], as_mapped[:, stuck == 0], equal_nan=True)
    # The rule only leaves out snow-free readings, so at a stuck pixel it can lower the odds, never raise them.
    ruled_stuck, mapped_stuck = odds[:, stuck > 0], as_mapped[:, stuck > 0]
    assert np.isfinite(mapped_stuck[np.isfinite(ruled_stuck)]).all()
    assert (ruled_stuck <= mapped_stuck)[np.isfinite(ruled_stuck)].all()
    assert (ruled_stuck < mapped_stuck).any()
    # Bear Island and Jan Mayen: the stale flags of the stuck winters no longer come back on 21 March.
    for lat, lon in ((74.45, 19.25), (70.95, -8.55)):
        ruled = snow.cell_probabilities(odds, row0, col0, lat, lon)
        mapped = snow.cell_probabilities(as_mapped, row0, col0, lat, lon)
        assert mapped[8] - mapped[7] < 0.1                     # as mapped there is no step either: stale all through
        assert ruled[8] - ruled[7] < 0.1 and ruled[8] < mapped[8] - 0.2


# --- version 3, decision 14: the land pixels of the block that was actually used ---

def test_cell_land_pixels_counts_the_block_the_odds_came_from():
    lat, lon, row0, col0 = 63.15, -64.90, 3750, 3250             # the point's pixel is crop[9, 7]
    crop = np.full((snow.N_BINS, 20, 12), np.nan, dtype="float32")
    crop[:, 7, 5] = 0.4      # top-left corner of the 5 x 5 block
    crop[3, 11, 9] = 1.0     # its bottom-right corner, seen as land in one bin only
    crop[:, 12, 7] = 0.0     # three rows down: outside both blocks
    values, source = snow.cell_probabilities_filled(crop, row0, col0, lat, lon)
    assert source == "5x5"
    assert snow.cell_land_pixels(crop, row0, col0, lat, lon) == 0                # the 3 x 3 block holds no land ...
    assert snow.cell_land_pixels(crop, row0, col0, lat, lon, reach=2) == 2       # ... the block the odds came from holds two
    assert snow.cell_land_pixels(crop, row0, col0, lat, lon, reach=snow.block_reach(source)) == 2
    crop[:, 9, 7] = 0.1      # the point's own pixel
    assert snow.cell_land_pixels(crop, row0, col0, lat, lon, reach=1) == 1
    assert snow.cell_land_pixels(crop, row0, col0, lat, lon, reach=2) == 3


def test_a_block_is_named_by_its_side_and_has_nine_or_twenty_five_pixels():
    assert (snow.block_reach("3x3"), snow.block_reach("5x5"), snow.block_reach(None)) == (1, 2, None)
    assert (snow.block_pixels("3x3"), snow.block_pixels("5x5"), snow.block_pixels(None)) == (9, 25, None)

"""Mars part, scores (twinfinder/mars_score.py) and the builder's own helpers (scripts/build_mars_cells.py).

Every formula is tested at its end points and at one middle value worked by hand; unknown in gives
unknown out. No test reads the data files or touches the network.
"""
import hashlib
import importlib
import math
from pathlib import Path

import pytest

from twinfinder import mars_score as ms
from twinfinder import sun

build = importlib.import_module("scripts.build_mars_cells")


# ---- terrain ---------------------------------------------------------------------------------------

def test_terrain_end_points():
    assert ms.terrain_score(0.8, 0.8) == 1.0
    assert ms.terrain_score(0.95, 0.8) == 1.0          # capped at 1
    assert ms.terrain_score(0.0, 0.8) == 0.0


def test_terrain_middle_by_hand():
    assert ms.terrain_score(0.4, 0.8) == pytest.approx(0.5)


def test_terrain_unknown():
    assert ms.terrain_score(None, 0.8) is None
    assert ms.terrain_score(0.5, None) is None
    assert ms.terrain_score(0.5, 0.0) is None          # no self-overlap to scale by


# ---- dry -------------------------------------------------------------------------------------------

def test_dry_end_points():
    assert ms.dry_score(25.0) == 1.0
    assert ms.dry_score(0.0) == 1.0
    assert ms.dry_score(10.0) == 1.0
    assert ms.dry_score(500.0) == 0.0
    assert ms.dry_score(900.0) == 0.0


def test_dry_middle_by_hand():
    # log scale: (ln 500 - ln 100) / (ln 500 - ln 25) = ln 5 / ln 20 = 1.609438 / 2.995732
    assert ms.dry_score(100.0) == pytest.approx(0.537244, abs=1e-6)
    assert ms.dry_score(math.sqrt(25.0 * 500.0)) == pytest.approx(0.5)


def test_dry_unknown():
    assert ms.dry_score(None) is None
    assert ms.dry_score(-1.0) is None


# ---- cold ------------------------------------------------------------------------------------------

def test_cold_zero_point_is_30c():
    # coordinator's decision 1 (14 Nov 2026): the scale runs over Earth's whole range, 0 at +30 C
    assert ms.COLD_ZERO_C == 30.0


def test_cold_end_points():
    assert ms.cold_score(-56.6, -56.6) == 1.0
    assert ms.cold_score(-70.0, -56.6) == 1.0          # colder than the site still counts as 1
    assert ms.cold_score(30.0, -56.6) == 0.0
    assert ms.cold_score(33.6, -56.6) == 0.0           # the warmest square in the climate file
    assert ms.cold_score(15.0, -56.6) > 0.0            # +15 C is no longer the zero point


def test_cold_middle_by_hand():
    assert ms.cold_score(0.0, -60.0) == pytest.approx(30.0 / 90.0)
    # the coldest bare square against Jezero: (30 + 38.3) / (30 + 56.6) = 68.3 / 86.6
    assert ms.cold_score(-38.3, -56.6) == pytest.approx(0.788684, abs=1e-6)
    # the hyperarid Atacama near Yungay (17.1 C) against Jezero: 12.9 / 86.6
    assert ms.cold_score(17.1, -56.6) == pytest.approx(0.148961, abs=1e-6)


def test_cold_with_another_zero_point_for_comparison():
    assert ms.cold_score(0.0, -60.0, zero_c=15.0) == pytest.approx(15.0 / 75.0)
    assert ms.cold_score(17.1, -56.6, zero_c=15.0) == 0.0


def test_cold_unknown():
    assert ms.cold_score(None, -56.6) is None
    assert ms.cold_score(0.0, None) is None
    assert ms.cold_score(0.0, 30.0) is None             # a site at or above +30 C has no scale
    assert ms.cold_score(0.0, 35.0) is None


def test_cold_formulas_in_words_name_the_zero_point():
    assert "0 at +30 C or warmer" in ms.FORMULAS["cold"]
    assert "+30 C" in ms.FORMULAS["month"]
    assert "+15" not in ms.FORMULAS["cold"] and "+15" not in ms.FORMULAS["month"]


# ---- bare ------------------------------------------------------------------------------------------

def test_bare():
    assert ms.bare_score(0.0) == 0.0
    assert ms.bare_score(1.0) == 1.0
    assert ms.bare_score(0.37) == pytest.approx(0.37)
    assert ms.bare_score(None) is None


# ---- sun -------------------------------------------------------------------------------------------

def test_earth_noon_range():
    assert ms.earth_noon_range(0.0) == pytest.approx((66.56, 90.0))
    assert ms.earth_noon_range(-30.0) == pytest.approx((36.56, 83.44))   # absolute latitude
    assert ms.earth_noon_range(30.0) == ms.earth_noon_range(-30.0)


def test_sun_end_points():
    assert ms.sun_score((40.0, 90.0), (40.0, 90.0)) == 1.0
    assert ms.sun_score((40.0, 90.0), (20.0, 90.0)) == 1.0   # a wider square range still covers all of it
    assert ms.sun_score((40.0, 60.0), (61.0, 90.0)) == 0.0   # no overlap


def test_sun_middle_by_hand():
    assert ms.sun_score((40.0, 90.0), (50.0, 90.0)) == pytest.approx(0.8)
    # Phoenix (-3.41 to 46.97) against an Earth square at the same latitude, 68.22:
    # -1.66 to 45.22, so 46.88 of 50.38 degrees
    assert ms.sun_score((-3.41, 46.97), ms.earth_noon_range(68.22)) == pytest.approx(46.88 / 50.38, abs=1e-6)


def test_sun_unknown():
    assert ms.sun_score(None, (40.0, 90.0)) is None
    assert ms.sun_score((40.0, 90.0), None) is None
    assert ms.sun_score((40.0, 40.0), (30.0, 90.0)) is None   # no site range to share


# ---- goals -----------------------------------------------------------------------------------------

def test_geometric_mean():
    assert ms.geometric_mean([1.0, 1.0]) == 1.0
    assert ms.geometric_mean([0.0, 0.5]) == 0.0
    assert ms.geometric_mean([0.25, 1.0]) == pytest.approx(0.5)
    assert ms.geometric_mean([0.5, 0.8, 0.2]) == pytest.approx(0.08 ** (1 / 3))
    assert ms.geometric_mean([None, 1.0]) is None
    assert ms.geometric_mean([]) is None


def test_goals_by_hand():
    f = {"terrain": 0.9, "dry": 0.5, "cold": 0.4, "bare": 0.8, "sun": 1.0}
    g = ms.goals(f)
    assert g["landscape"] == pytest.approx(math.sqrt(0.9 * 0.8))
    assert g["environment"] == pytest.approx((0.5 * 0.4 * 0.8) ** (1 / 3))
    assert g["full"] == pytest.approx((0.9 * 0.5 * 0.4 * 0.8 * 1.0) ** (1 / 5))


def test_goals_end_points_and_unknown():
    assert ms.goals({k: 1.0 for k in ms.FACTORS}) == {"landscape": 1.0, "environment": 1.0, "full": 1.0}
    zero = ms.goals({"terrain": 1.0, "dry": 1.0, "cold": 1.0, "bare": 0.0, "sun": 1.0})
    assert zero == {"landscape": 0.0, "environment": 0.0, "full": 0.0}
    g = ms.goals({"terrain": None, "dry": 0.5, "cold": 0.4, "bare": 0.8, "sun": 1.0})
    assert g["landscape"] is None and g["full"] is None
    assert g["environment"] == pytest.approx((0.5 * 0.4 * 0.8) ** (1 / 3))


# ---- Sun by month and the calendar -----------------------------------------------------------------

def test_noon_sun_by_month_uses_mid_month_days():
    assert ms.MID_MONTH_DOY == (15, 46, 74, 105, 135, 166, 196, 227, 258, 288, 319, 349)
    got = ms.noon_sun_by_month(45.0)
    assert len(got) == 12
    for m, doy in enumerate(ms.MID_MONTH_DOY):
        assert got[m] == pytest.approx(sun.noon_elevation_deg(45.0, doy))


def test_noon_sun_by_month_end_points():
    north = ms.noon_sun_by_month(66.0)
    assert north[5] == pytest.approx(90 - 66 + 23.3, abs=0.3)    # June, near the solstice
    assert north[11] == pytest.approx(90 - 66 - 23.3, abs=0.3)   # December
    south = ms.noon_sun_by_month(-40.0)
    assert south[11] > 70 and south[5] < 30                       # seasons swap in the south
    assert ms.noon_sun_by_month(None) is None


def test_month_scores_by_hand():
    site_t, site_range = -60.0, (40.0, 90.0)
    t2m = [0.0] * 12
    t2m[6] = -15.0
    precip = [25.0 / 12.0] * 12                                   # times 12 = 25 mm: dry = 1
    got = ms.month_scores(t2m, precip, 0.0, site_t, site_range)   # equator: noon Sun always above 66
    assert got[0] == pytest.approx((1 / 3) ** (1 / 3))            # cold (30 - 0) / 90 = 1/3
    assert got[6] == pytest.approx(0.5 ** (1 / 3))                # cold (30 + 15) / 90 = 0.5


def test_month_cold_is_zero_at_30c():
    t2m = [20.0] * 12
    t2m[0], t2m[1] = 30.0, 29.0
    got = ms.month_scores(t2m, [1.0] * 12, 0.0, -60.0, (40.0, 90.0))
    assert got[0] == 0.0 and got[1] > 0.0 and got[2] > 0.0


def test_month_scores_sun_outside_range_gives_zero():
    got = ms.month_scores([-20.0] * 12, [1.0] * 12, 60.0, -60.0, (40.0, 90.0))
    assert got[11] == 0.0             # 60 N in December: noon Sun near 7 degrees, below 40
    assert got[5] > 0.0               # June: near 53 degrees, inside


def test_month_scores_unknown():
    t2m = [0.0] * 12
    t2m[3] = None
    got = ms.month_scores(t2m, [1.0] * 12, 0.0, -60.0, (40.0, 90.0))
    assert got[3] is None and got[2] is not None
    assert ms.month_scores(None, [1.0] * 12, 0.0, -60.0, (40.0, 90.0)) is None
    assert ms.month_scores([0.0] * 12, [1.0] * 12, 0.0, None, (40.0, 90.0)) is None


def test_best_months():
    scores = [0.1, 0.5, None, 0.5, 0.9] + [0.0] * 7
    assert ms.best_months(scores) == ["May", "Feb", "Apr"]        # ties keep calendar order
    assert ms.best_months([0.3, 0.0] + [None] * 10) == ["Jan"]    # a zero month is never a best month
    assert ms.best_months([None] * 12) == []
    assert ms.best_months(None) is None


# ---- falls short by --------------------------------------------------------------------------------

def test_falls_short_by_hand():
    # Atacama near Yungay against Jezero
    got = ms.falls_short(17.1, -56.6, 8.4, 61.29, 721.0)
    assert got["colder_on_mars_by_c"] == pytest.approx(73.7)
    assert got["times_wetter_than_25_mm"] == pytest.approx(0.336)
    assert got["pressure_mars_over_square"] == pytest.approx(721.0 / 61290.0)


def test_falls_short_unknown():
    got = ms.falls_short(None, -56.6, None, None, 721.0)
    assert got == {"colder_on_mars_by_c": None, "times_wetter_than_25_mm": None,
                   "pressure_mars_over_square": None}


# ---- places, ranks and the test of the ranking -----------------------------------------------------

def test_distance_km():
    assert ms.distance_km(0.0, 0.0, 0.0, 1.0) == pytest.approx(111.195, abs=0.01)
    assert ms.distance_km(10.0, 179.75, 10.0, -179.75) == pytest.approx(0.5 * 111.195 * math.cos(math.radians(10)), rel=1e-3)


def test_pick_best_one_per_300_km():
    rows = [
        {"id": "a", "lat": 0.0, "lon": 0.0, "score": 0.9},
        {"id": "b", "lat": 0.0, "lon": 1.0, "score": 0.8},    # 111 km from a: skipped
        {"id": "c", "lat": 0.0, "lon": 5.0, "score": 0.7},
        {"id": "d", "lat": 0.0, "lon": 10.0, "score": None},  # unknown: never picked
        {"id": "e", "lat": 0.0, "lon": 20.0, "score": 0.7},   # ties: by id
    ]
    got = ms.pick_best(rows, "score", n=10, min_km=300.0)
    assert [r["id"] for r in got] == ["a", "c", "e"]
    assert [r["id"] for r in ms.pick_best(rows, "score", n=1)] == ["a"]


def test_pick_best_breaks_ties_by_a_second_key():
    rows = [
        {"id": "a", "lat": 0.0, "lon": 0.0, "score": 1.0, "tie": 0.80},
        {"id": "b", "lat": 0.0, "lon": 10.0, "score": 1.0, "tie": 0.95},
        {"id": "c", "lat": 0.0, "lon": 20.0, "score": 1.0, "tie": None},   # unknown second key goes last
        {"id": "d", "lat": 0.0, "lon": 30.0, "score": 0.9, "tie": 0.99},
    ]
    assert [r["id"] for r in ms.pick_best(rows, "score", tie="tie")] == ["b", "a", "c", "d"]


def test_pick_best_breaks_ties_by_several_keys_in_turn():
    # decision 2: landscape ties go by bare km2, then by the environment score, then by id
    rows = [
        {"id": "a", "lat": 0.0, "lon": 0.0, "score": 1.0, "km2": 900.0, "env": 0.2},
        {"id": "b", "lat": 0.0, "lon": 10.0, "score": 1.0, "km2": 2500.0, "env": 0.1},
        {"id": "c", "lat": 0.0, "lon": 20.0, "score": 1.0, "km2": 900.0, "env": 0.6},
        {"id": "d", "lat": 0.0, "lon": 30.0, "score": 1.0, "km2": 900.0, "env": None},   # unknown goes last
        {"id": "e", "lat": 0.0, "lon": 40.0, "score": 1.0, "km2": None, "env": 0.9},
        {"id": "f", "lat": 0.0, "lon": 50.0, "score": 0.9, "km2": 9999.0, "env": 1.0},
    ]
    got = ms.pick_best(rows, "score", tie=("km2", "env"))
    assert [r["id"] for r in got] == ["b", "c", "a", "d", "e", "f"]


def test_count_at_score():
    assert ms.count_at([1.0, 1.0, 0.5, None, 1.0], 1.0) == 3
    assert ms.count_at([0.5], 1.0) == 0
    assert ms.count_at([0.5, None], None) == 0


def test_auc_by_hand():
    assert ms.auc([1.0, 2.0], [0.0, 1.0]) == pytest.approx(3.5 / 4)
    assert ms.auc([2.0, 3.0], [0.0, 1.0]) == 1.0
    assert ms.auc([0.0], [1.0, 2.0]) == 0.0
    assert ms.auc([1.0, None], [0.0, None]) == 1.0      # unknown values are left out
    assert ms.auc([], [1.0]) is None
    assert ms.auc([None], [1.0]) is None


def test_percentile_by_hand():
    assert ms.percentile(3.0, [1.0, 2.0, 3.0, 4.0]) == pytest.approx(62.5)
    assert ms.percentile(9.0, [1.0, 2.0]) == 100.0
    assert ms.percentile(0.0, [1.0, 2.0]) == 0.0
    assert ms.percentile(None, [1.0]) is None
    assert ms.percentile(1.0, []) is None


def test_control_ids_are_drawn_by_sha1():
    ids = [f"m_{i}.25_0.25" for i in range(50)]
    got = ms.control_ids(ids, 10, exclude={ids[0]})
    want = sorted((i for i in ids if i != ids[0]), key=lambda s: hashlib.sha1(s.encode()).hexdigest())[:10]
    assert got == want
    assert ms.control_ids(ids, 10, exclude={ids[0]}) == got   # the same every run


# ---- the builder's region table --------------------------------------------------------------------

@pytest.mark.parametrize("lat, lon, elev, name, group", [
    (-24.1, -70.0, 2069.0, "Atacama Desert", "great desert"),            # Yungay
    (-25.25, -68.75, 4087.0, "Altiplano and Puna", "high plateau"),       # the high Andes east of the desert
    (-77.47, 162.52, 900.0, "McMurdo Dry Valleys", "polar desert"),
    (75.38, -89.67, 200.0, "Canadian High Arctic", "polar desert"),      # Haughton crater, Devon Island
    (38.41, -110.79, 1400.0, "Colorado Plateau", "high plateau"),        # Utah station near Hanksville
    (35.0, -115.5, 900.0, "North American deserts", "great desert"),     # Mojave
    (38.0, 92.5, 2850.0, "Qaidam Basin", "high plateau"),
    (37.25, 90.75, 4390.0, "Tibetan Plateau", "high plateau"),           # Kunlun, south-west of the Qaidam floor
    (37.25, 87.25, 4525.0, "Tibetan Plateau", "high plateau"),           # Kunlun, south of the Tarim Basin
    (39.0, 83.0, 1100.0, "Taklamakan and Tarim Basin", "great desert"),
    (18.5, 54.5, 450.0, "Arabian Desert", "great desert"),               # Dhofar
    (27.75, 35.75, 527.0, "Arabian Desert", "great desert"),             # Saudi coast, east of the Red Sea
    (-21.1, 119.4, 400.0, "Australian deserts", "great desert"),         # Pilbara
    (78.0, 16.0, 300.0, "Svalbard", "polar desert"),
    (23.25, 10.25, 900.0, "Sahara", "great desert"),                     # Djado plateau
    (33.25, 88.25, 4900.0, "Tibetan Plateau", "high plateau"),           # Changtang
    (29.0, -13.7, 200.0, "Canary Islands", "other"),                     # Lanzarote
    (37.4, -6.34, 300.0, "other", "other"),                              # Rio Tinto
    (28.25, 61.75, 1500.0, "other", "other"),                            # south-east Iran, not the Lut
    (-80.25, 155.75, 2000.0, "Transantarctic Mountains", "polar desert"),
    (-70.0, 10.0, 2500.0, "Antarctica", "polar desert"),
])
def test_region_labels(lat, lon, elev, name, group):
    assert build.region(lat, lon, elev) == (name, group)


def test_region_with_unknown_height_skips_boxes_that_need_one():
    assert build.region(33.25, 88.25, None) == ("other", "other")
    assert build.region(23.25, 10.25, None) == ("Sahara", "great desert")


def test_touching_squares():
    assert build.touching_squares(-24.1, -70.0) == ["m_-24.25_-70.25", "m_-24.25_-69.75"]
    assert build.touching_squares(29.0, -13.7) == ["m_28.75_-13.75", "m_29.25_-13.75"]
    assert build.touching_squares(38.0, 92.5) == ["m_37.75_92.25", "m_37.75_92.75", "m_38.25_92.25", "m_38.25_92.75"]
    assert build.touching_squares(38.41, -110.79) == ["m_38.25_-110.75"]


def test_known_sets_count_each_square_once():
    recs = [{"square": "a", "in_climate": True, "ranked": True}, {"square": "a", "in_climate": True, "ranked": True},
            {"square": "b", "in_climate": True, "ranked": False}, {"square": "c", "in_climate": False, "ranked": False}]
    assert build.known_sets(recs) == (["a", "b"], ["a"])


# ---- the builder's plain-words check ---------------------------------------------------------------

def test_long_sentences():
    ok = " ".join(["word"] * 25) + "."
    bad = " ".join(["word"] * 26) + "."
    text = f"# A heading\n\n{ok} Short one.\n\n| a | {bad} |\n\n- {bad}\n"
    got = build.long_sentences(text, max_words=25)
    assert len(got) == 1 and got[0].startswith("word word")


# ---- the builder on a tiny made-up input -----------------------------------------------------------

def tiny_inputs():
    hist = [0.0] * 14
    hist[3] = 1.0
    sites_base = {"meta": {}, "sites": [{"id": "s1", "name": "Site one", "lat": 10.0, "lon_east": 20.0,
                                          "kind": "visited by a NASA mission", "why": "A test.",
                                          "sources": [{"what": "x", "url": "https://example.org"}]}]}
    terrain = {"meta": {}, "sites": {"s1": {"slope_hist": hist, "median_slope_deg": 0.7, "p90_slope_deg": 0.9,
                                            "relief_m": 100.0, "self_overlap": 0.8, "pixels": 4096}},
               "cells": {"m_10.25_20.25": {"slope_hist": hist, "median_slope_deg": 0.7, "p90_slope_deg": 0.9,
                                           "relief_m": 50.0, "elev_mean_m": 300.0, "land_share": 1.0,
                                           "pixels": 900},
                         "m_40.25_20.25": {"slope_hist": hist, "median_slope_deg": 0.7, "p90_slope_deg": 0.9,
                                           "relief_m": 50.0, "elev_mean_m": 300.0, "land_share": 1.0,
                                           "pixels": 900}}}
    def cell(bare, t=10.0, p=1.0):
        return {"bare": bare, "bare_source": None if bare is None else "ESA WorldCover 2021", "land_share": 1.0,
                "t2m_c": [t] * 12, "ts_c": [t] * 12, "precip_mm": [p] * 12, "precip_mm_year": 12 * p,
                "pressure_kpa": 90.0, "t2m_year_c": t, "cloud_pct": None, "grid": [0, 0]}
    climate = {"meta": {}, "sites": {"s1": {
        "sun": {"noon_elev_min_deg": 54.81, "noon_elev_max_deg": 90.0, "day_length_min_h": 11.0,
                "day_length_max_h": 13.0, "how": "formula"},
        "climate": {"annual_mean_c": -60.0, "warm_season_daily_max_c": -10.0, "cold_season_daily_min_c": -90.0,
                    "pressure_pa": 750, "kind": "model", "source": "MCD", "url": "https://example.org"},
        "cannot_match": []}},
        "cells": {"m_10.25_20.25": cell(0.5), "m_40.25_20.25": cell(0.9),
                  "m_-10.25_20.25": cell(0.1), "m_-20.25_20.25": cell(None)}}
    return sites_base, terrain, climate


def test_build_cells_keeps_bare_squares_and_unknowns():
    sites_base, terrain, climate = tiny_inputs()
    cells, counts = build.score_cells(build.site_cards(sites_base, terrain, climate), terrain, climate)
    assert set(cells) == {"m_10.25_20.25", "m_40.25_20.25"}       # bare 0.1 and bare unknown are not kept
    a = cells["m_10.25_20.25"]["sites"]["s1"]
    assert a["terrain"] == 1.0 and a["bare"] == 0.5
    assert a["cold"] == pytest.approx(20.0 / 90.0, abs=1e-4)          # (30 - 10) / (30 + 60)
    assert a["landscape"] == pytest.approx(math.sqrt(0.5), abs=1e-4)
    assert cells["m_10.25_20.25"]["bare_km2"] == pytest.approx(0.5 * build.mc.square_km2(10.25), rel=1e-3)
    assert counts["squares_in_climate_only"] == 2 and counts["squares_in_terrain_only"] == 0


def test_build_cells_unknown_terrain_gives_unknown_goals():
    sites_base, terrain, climate = tiny_inputs()
    del terrain["cells"]["m_40.25_20.25"]
    cells, _ = build.score_cells(build.site_cards(sites_base, terrain, climate), terrain, climate)
    b = cells["m_40.25_20.25"]["sites"]["s1"]
    assert b["terrain"] is None and b["landscape"] is None and b["full"] is None
    assert b["environment"] is not None


# ---- MARS-REVIEW: the words of MARS-RESULTS.md that keep it from being read as a climate match --------

def review_cards_and_summary():
    def pressure(mars, sea, low):
        return {"what": "surface air pressure", "mars": mars, "earth": 101325, "unit": "Pa", "number": sea,
                "mars_site_over_earth_lowest_land_square": low, "earth_lowest_land_square_where": "m_35.25_77.25"}
    cards = [{"id": "a", "lat": 18.4, "cannot_match": [pressure(721, 0.0071, 0.014)]},
             {"id": "b", "lat": 68.2, "cannot_match": [pressure(834, 0.0082, 0.0162)]}]
    cold = {"id": "m_-80.25_155.75", "region": "Transantarctic Mountains", "t2m_year_c": -38.3}
    summary = {"a": {"coldest_square": dict(cold, colder_on_mars_by_c=18.3)},
               "b": {"coldest_square": dict(cold, colder_on_mars_by_c=56.4)}}
    return cards, summary


def test_climate_gap_lines_say_it_is_not_a_climate_match_with_numbers():
    cards, summary = review_cards_and_summary()
    text = " ".join(build.climate_gap_lines(cards, summary))
    assert "not a climate match" in text
    assert "-38.3 °C" in text and "18.3 to 56.4 °C colder" in text
    assert "0.71 to 0.82 %" in text and "1.40 to 1.62 %" in text
    assert not build.long_sentences("\n".join(build.climate_gap_lines(cards, summary)))


def test_climate_gap_lines_without_pressure_still_give_the_temperature_gap():
    cards, summary = review_cards_and_summary()
    for c in cards:
        c["cannot_match"] = []
    lines = build.climate_gap_lines(cards, summary)
    assert any("18.3 to 56.4 °C colder" in s for s in lines)
    assert not any(" % of Earth's" in s for s in lines)


def test_a_score_is_not_a_share_of_likeness():
    assert "not a share of likeness" in build.SCORE_IS_NOT_LIKENESS
    assert not build.long_sentences(build.SCORE_IS_NOT_LIKENESS)


def test_slope_baseline_text_names_the_two_pixel_span():
    assert "1.85 km" in build.BASELINE_TEXT and "3.7 km" in build.BASELINE_TEXT
    assert not build.long_sentences(build.BASELINE_TEXT)


def test_dusty_sky_row_gives_the_range_not_the_storm_peak_alone():
    item = {"what": "the dusty sky", "mars": 3, "earth": 0.13, "unit": "aerosol optical depth", "number": None}
    mars, earth = build.cannot_match_cells(item)
    assert "below 1" in mars and "above 3" in mars
    assert "0.13" in earth and "memory" in earth
    plain = {"what": "gravity", "mars": 3.73, "earth": 9.82, "unit": "m/s2", "number": 0.38}
    assert build.cannot_match_cells(plain) == ("3.73", "9.82")


def test_model_precip_line_gives_the_range_of_the_labelled_squares():
    cells = {"x": {"region": "McMurdo Dry Valleys", "precip_mm_year": 80.4},
             "y": {"region": "McMurdo Dry Valleys", "precip_mm_year": 122.6},
             "z": {"region": "McMurdo Dry Valleys", "precip_mm_year": None},
             "w": {"region": "Sahara", "precip_mm_year": 5.0}}
    line = build.model_precip_line(cells)
    assert "2 ranked squares" in line and "80 to 123 mm" in line and "too wet" in line
    assert not build.long_sentences(line)
    assert build.model_precip_line({"w": {"region": "Sahara", "precip_mm_year": 5.0}}) is None


def test_bare_class_line_names_lichen_and_the_haughton_value():
    val = {"sites": [{"named_in_job": "Haughton crater", "bare": 0.1812}, {"named_in_job": None, "bare": 0.5}]}
    line = build.bare_class_line(val)
    assert "moss and lichen" in line and "0.18" in line
    assert not build.long_sentences(line)
    assert "0.18" not in build.bare_class_line({"sites": []})


def test_kind_word_does_not_call_a_rover_a_lander():
    assert build.kind_word("measured by a lander") == "measured"
    assert build.kind_word("model") == "model"
    assert build.kind_word(None) == "n/a"


# ---- MARS-REVIEW: tests for breakages the suite above did not catch ---------------------------------

def test_pick_best_keeps_a_place_exactly_at_the_minimum_distance():
    rows = [{"id": "a", "lat": 0.0, "lon": 0.0, "score": 0.9}, {"id": "b", "lat": 0.0, "lon": 3.0, "score": 0.8}]
    d = ms.distance_km(0.0, 0.0, 0.0, 3.0)
    assert [r["id"] for r in ms.pick_best(rows, "score", min_km=d)] == ["a", "b"]


def test_month_dry_uses_the_months_precipitation_times_12():
    precip = [10.0] * 12                                          # times 12 = 120 mm a year
    got = ms.month_scores([-60.0] * 12, precip, 0.0, -60.0, (40.0, 90.0))
    dry = math.log(500.0 / 120.0) / math.log(500.0 / 25.0)
    assert got[0] == pytest.approx(dry ** (1 / 3))                # cold 1, sun inside 1


def test_month_sun_exactly_on_the_edge_of_the_site_range_counts_as_inside():
    lat = 60.0
    noon = ms.noon_sun_by_month(lat)
    got = ms.month_scores([-60.0] * 12, [1.0] * 12, lat, -60.0, (noon[5], 90.0))
    assert got[5] > 0.0
    got = ms.month_scores([-60.0] * 12, [1.0] * 12, lat, -60.0, (0.0, noon[11]))
    assert got[11] > 0.0


def test_known_list_text_says_the_known_sites_are_only_a_test():
    assert "not an input" in build.KNOWN_LIST_TEXT and "known_analogs.json" in build.KNOWN_LIST_TEXT
    assert not build.long_sentences(build.KNOWN_LIST_TEXT)


# ---- MARS-TUNE: the coordinator's four decisions of 14 November 2026 ---------------------------------

# decision 1: cold is 0 at +30 C

def test_counts_name_the_squares_at_the_cold_zero_point():
    sites_base, terrain, climate = tiny_inputs()
    climate["cells"]["m_40.25_20.25"]["t2m_year_c"] = 31.0
    climate["cells"]["m_10.25_20.25"]["t2m_year_c"] = 20.0
    cells, counts = build.score_cells(build.site_cards(sites_base, terrain, climate), terrain, climate)
    assert counts["kept_squares_at_cold_zero_or_warmer"] == 1      # new field: 30 C or more
    assert counts["kept_squares_yearly_mean_15c_or_more"] == 2     # the old field keeps its meaning
    assert cells["m_40.25_20.25"]["sites"]["s1"]["cold"] == 0.0
    assert cells["m_10.25_20.25"]["sites"]["s1"]["cold"] == pytest.approx(10.0 / 90.0, abs=1e-4)


def test_cold_scale_lines_give_the_zero_point_and_the_warmest_square():
    cells = {"x": {"id": "m_13.25_40.75", "region": "Danakil Depression", "t2m_year_c": 33.6},
             "y": {"id": "m_0.25_0.25", "region": "other", "t2m_year_c": 20.0},
             "z": {"id": "m_1.25_0.25", "region": "other", "t2m_year_c": None}}
    text = " ".join(build.cold_scale_lines(cells))
    assert "+30 °C" in text and "`m_13.25_40.75` (Danakil Depression)" in text and "33.6 °C" in text
    assert "+15" not in text
    assert not build.long_sentences(text)


def test_score_square_can_use_the_previous_zero_point():
    sites_base, terrain, climate = tiny_inputs()
    card = build.site_cards(sites_base, terrain, climate)[0]
    sq = "m_10.25_20.25"
    now = build.score_square(sq, card, terrain["cells"][sq], climate["cells"][sq], with_months=False)
    old = build.score_square(sq, card, terrain["cells"][sq], climate["cells"][sq], with_months=False,
                             cold_zero_c=15.0)
    assert now["cold"] == pytest.approx(20.0 / 90.0, abs=1e-4)
    assert old["cold"] == pytest.approx(5.0 / 75.0, abs=1e-4)


def test_plan_scores_section_gives_the_30c_zero_point():
    plan = (Path(__file__).resolve().parents[1] / "docs" / "superpowers" / "plans" / "2026-11-14-mars-part.md").read_text()
    scores = plan.split("## Scores", 1)[1].split("\n## ", 1)[0]
    assert "0 at +30 C or warmer" in scores and "0 at +15 C" not in scores   # the history may name +15 C


# decision 2: ties in the landscape lists

def tie_inputs():
    """Three squares that all tie on landscape: two at 10.25 N with the same bare area, one further north."""
    sites_base, terrain, climate = tiny_inputs()
    terrain["cells"]["m_10.25_30.25"] = dict(terrain["cells"]["m_10.25_20.25"])
    climate["cells"]["m_10.25_30.25"] = dict(climate["cells"]["m_10.25_20.25"])
    for sq in ("m_10.25_20.25", "m_10.25_30.25", "m_40.25_20.25"):
        climate["cells"][sq]["bare"] = 0.9
    wet = climate["cells"]["m_10.25_20.25"]
    wet["precip_mm"], wet["precip_mm_year"] = [10.0] * 12, 120.0   # wetter: lower environment, lower id
    return sites_base, terrain, climate


def test_landscape_lists_order_ties_by_bare_area_then_environment_and_count_them():
    sites_base, terrain, climate = tie_inputs()
    cards = build.site_cards(sites_base, terrain, climate)
    cells, _ = build.score_cells(cards, terrain, climate)
    best = build.best_places(cells, cards, climate)
    land = best["s1"]["landscape"]
    # 10.25 N squares have more bare km2 than the 40.25 N one; between them the drier (higher environment) first
    assert [p["id"] for p in land] == ["m_10.25_30.25", "m_10.25_20.25", "m_40.25_20.25"]
    assert all(p["squares_with_this_score"] == 3 for p in land)
    assert land[0]["bare_km2"] == cells["m_10.25_30.25"]["bare_km2"]
    assert build.tied_at_top(best) == {"s1": {"landscape": 3, "environment": 2, "full": 1}}


def test_landscape_tie_line_says_how_many_tie():
    places = [{"score": 1.0, "squares_with_this_score": 410}]
    line = build.landscape_tie_line(places)
    assert "410 ranked squares tie at the top score of 1.000" in line and "not a ranking" in line
    assert "bare area" in line and "environment" in line
    assert not build.long_sentences(line)
    assert "Only one" in build.landscape_tie_line([{"score": 0.8, "squares_with_this_score": 1}])
    assert build.landscape_tie_line([]) is not None


# decision 3: wording

def test_first_pass_text_gives_the_height_spacing_and_the_slope_span():
    assert "heights every 1.85 km, slopes across about 3.7 km" in build.BASELINE_SHORT
    assert build.BASELINE_SHORT in build.FIRST_PASS


def test_no_output_text_calls_1_85_km_the_slope_span():
    src = Path(build.__file__).read_text() + Path(ms.__file__).read_text()
    assert "slopes over about 1.85" not in src and "slopes over 1.85" not in src


FEED = ("measured by a lander (Curiosity REMS, daily pressure, from NASA's weather feed, which carries the CAB note "
        "'for outreach purposes only'; the scientific record is the REMS data in PDS, not read here)")


def test_curiosity_figures_are_cited_as_from_the_outreach_feed():
    gale = {"id": "gale", "name": "Gale crater",
            "climate": {"kind_by_field": {"annual_mean_c": "model", "pressure_pa": "measured by a lander"},
                        "source_by_field": {"annual_mean_c": "model (MCD)", "pressure_pa": FEED}}}
    assert build.feed_fields(gale) == ["pressure_pa"]
    line = build.feed_citation_line([gale])
    assert "Gale" in line and "NASA's public weather feed" in line and "outreach" in line
    assert "not archive data" in line
    assert not build.long_sentences(line)
    pds = {"id": "phoenix", "name": "Phoenix",
           "climate": {"kind_by_field": {"warm_season_daily_max_c": "measured by a lander"},
                       "source_by_field": {"warm_season_daily_max_c": "measured by a lander (Phoenix MET, PDS)"}}}
    assert build.feed_fields(pds) == [] and build.feed_citation_line([pds]) is None
    assert "outreach" in build.SOURCES["data/derived/mars_climate.json"]
    assert "NASA/PDS lander data" not in build.SOURCES["data/derived/mars_climate.json"]


def test_site_cards_carry_the_citation_note_for_feed_figures():
    sites_base, terrain, climate = tiny_inputs()
    cl = climate["sites"]["s1"]["climate"]
    assert build.site_cards(sites_base, terrain, climate)[0]["climate"]["citation_note"] is None
    cl["kind_by_field"] = {"pressure_pa": "measured by a lander"}
    cl["source_by_field"] = {"pressure_pa": FEED}
    assert build.site_cards(sites_base, terrain, climate)[0]["climate"]["citation_note"] == build.CURIOSITY_CITE


def test_score_caveats_say_both_things_in_short_sentences():
    assert "not a climate match" in build.SCORE_CAVEATS
    assert "not a share of likeness" in build.SCORE_CAVEATS
    assert not build.long_sentences(build.SCORE_CAVEATS)


def test_blocks_missing_caveats_finds_score_blocks_without_them():
    ok = f"## 4. Lists\n\n{build.SCORE_CAVEATS}\n\n| # | Square | Score |\n|---|---|---|\n| 1 | a | 0.5 |\n"
    bad = "### Jezero\n\n| # | Square | Score |\n|---|---|---|\n| 1 | a | 0.5 |\n"
    bad2 = "## 7. Known\n\n**full: score (percentile among ranked squares)**\n"
    bad3 = "## 5. Short\n\n| Site | Highest cold | Highest full |\n"
    bad4 = "### Gale\n\nThe closest square is `x`, with a score of 0.6.\n"
    plain = "## 6. No match\n\n| What | Mars | Earth |\n"
    assert build.blocks_missing_caveats(ok + plain) == []
    assert build.blocks_missing_caveats(ok + bad) == ["### Jezero"]
    assert build.blocks_missing_caveats(bad2 + bad3 + bad4) == ["## 7. Known", "## 5. Short", "### Gale"]


# decision 4: the known sites and the test against controls, before and after

def test_cold_change_line_says_plainly_better_or_worse():
    now = {"a": {"full": {"auc": 0.62}}, "b": {"full": {"auc": 0.60}}}
    before = {"a": {"full": {"auc": 0.54}}, "b": {"full": {"auc": 0.57}}}
    line = build.cold_change_line(now, before, "full", "all land")
    assert "0.540 to 0.570" in line and "0.600 to 0.620" in line and "better" in line
    assert "+15 °C" in line and "+30 °C" in line
    assert not build.long_sentences(line)
    assert "worse" in build.cold_change_line(before, now, "full", "all land")
    assert "unchanged" in build.cold_change_line(now, now, "full", "all land")
    mixed = {"a": {"full": {"auc": 0.50}}, "b": {"full": {"auc": 0.70}}}
    assert "mixed" in build.cold_change_line(mixed, before, "full", "all land")


def test_zero_environment_line_names_the_known_sites_still_at_0_and_why():
    named = [{"named_in_job": "A", "sites": {"x": {"environment": 0.0, "dry": 0.0, "cold": 0.2, "bare": 0.5}}},
             {"named_in_job": "B", "sites": {"x": {"environment": 0.3, "dry": 0.4, "cold": 0.2, "bare": 0.5}}},
             {"named_in_job": "C", "sites": {"x": {"environment": None, "dry": None, "cold": None, "bare": None}}},
             {"named_in_job": "D", "sites": {"x": {"environment": 0.0, "dry": 0.5, "cold": 0.2, "bare": 0.0}}}]
    line = build.zero_environment_line(named, "x")
    assert "A (dry 0)" in line and "D (bare 0)" in line and "B" not in line and "C" not in line
    assert not build.long_sentences(line)
    assert build.zero_environment_line(named[1:3], "x") is None


def test_baseline_text_uses_the_agreed_words():
    assert build.BASELINE_SHORT in build.BASELINE_TEXT

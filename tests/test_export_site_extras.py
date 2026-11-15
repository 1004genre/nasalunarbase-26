"""The second export for the map page: the survey additions, as the page reads them.

What the page reads must say what the pipeline files say, unknown must stay unknown, and every
per-area file must line up with the page's own list of areas (site/data/cells.json).
"""
import hashlib
import importlib
import json
import math
import os
import shutil
from pathlib import Path

import numpy as np
import pytest

extras = importlib.import_module("scripts.export_site_extras")

ROOT = Path(__file__).resolve().parents[1]
DERIVED = ROOT / "data" / "derived"
REFERENCE = ROOT / "data" / "reference"
SOURCES_MD = ROOT / "data" / "SOURCES.md"
SITE_DATA = ROOT / "site" / "data"
TARGET_IDS = ["connecting-ridge", "malapert", "mons-mouton", "nobile-rim-2"]
ADDED_KEYS = {"area", "areas", "index", "point", "km_to_point"}     # keys the export adds; not in the source


# ---- small helpers ----

def numbers(value, path=()):
    """Every number in a nested value, with the path that leads to it."""
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return
    if isinstance(value, (int, float)):
        yield path, value
    elif isinstance(value, dict):
        for key, inner in value.items():
            if key not in ADDED_KEYS:
                yield from numbers(inner, path + (key,))
    elif isinstance(value, list):
        for index, inner in enumerate(value):
            yield from numbers(inner, path + (index,))


def at(value, path):
    for step in path:
        value = value[step]
    return value


def same_numbers(written, source) -> int:
    """Check every number of `written` against the same place in `source`; how many were checked."""
    count = 0
    for path, number in numbers(written):
        assert at(source, path) == number, path
        count += 1
    return count


def words(sentence: str) -> int:
    return len(sentence.split())


def write(path: Path, value) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value, str):
        path.write_text(value)
    else:
        path.write_text(json.dumps(value))
    return path


# ---- small made-up inputs ----

# five areas: three around 70 N 20 E, one in Arctic Canada, one in Antarctica
AREA_IDS = ["70.0_20.0", "70.3_20.0", "70.6_20.0", "72.4_-114.0", "-68.6_78.0"]
AREA_LAT = [70.05, 70.35, 70.65, 72.45, -68.55]
AREA_LON = [20.1, 20.1, 20.1, -113.9, 78.1]
REGIONS = ["Clear Land", "Grey Land", "South Land"]
AREA_REGION = [0, 0, 1, 1, 2]


def page_cells(ids=AREA_IDS) -> dict:
    n = len(ids)
    return {"n": n, "ids": list(ids),
            "units": {"lat": "hundredths of a degree", "lon": "hundredths of a degree"},
            "lat": [int(round(v * 100)) for v in AREA_LAT[:n]], "lon": [int(round(v * 100)) for v in AREA_LON[:n]],
            "hemisphere": "".join("N" if v > 0 else "S" for v in AREA_LAT[:n]),
            "regions": REGIONS, "region": AREA_REGION[:n],
            "known_labels": ["a known place"], "known": [-1, -1, 0, -1, -1][:n]}


def page_meta() -> dict:
    return {"targets": [{"id": "connecting-ridge", "name": "Shackleton-de Gerlache connecting ridge", "short": "Connecting ridge"},
                        {"id": "malapert", "name": "Malapert Massif", "short": "Malapert"}]}


def temperature_doc() -> dict:
    cells = {
        "70.6_20.0": {"t2m_c": [-20.4, -20.5, -20.6, 0.4, 0.5, 0.49, -0.5, -0.49, 17.5, 3.0, None, -30.0],
                      "ts_c": [1.0] * 12, "grid": [70.5, 20.0], "grid_elev_m": 352.81},
        "70.0_20.0": {"t2m_c": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0],
                      "ts_c": [0.0] * 12, "grid": [70.0, 20.0], "grid_elev_m": 0.0},
        "70.3_20.0": {"t2m_c": None, "ts_c": None, "grid": None, "grid_elev_m": None},
        "72.4_-114.0": {"t2m_c": [-140.0, 140.0] + [0.0] * 10, "ts_c": [2.0] * 12, "grid": [72.5, -113.75], "grid_elev_m": 612.4},
        "-68.6_78.0": {"t2m_c": [-3.2] * 12, "ts_c": [-4.6] * 12, "grid": [-68.5, 78.125], "grid_elev_m": 88.0},
    }
    meta = {"source": "NASA POWER, made up", "period": "2001-01-01 to 2025-12-31", "grid_deg": [0.5, 0.625],
            "what_it_is": "Air temperature, made up.", "what_it_is_not": "Not a measurement at the cell.",
            "fields": {"t2m_c": "mean air temperature", "ts_c": "mean surface temperature"},
            "by_bin_rule": "the month of the middle day", "written": "2026-11-15T00:31:57Z",
            "years_fit": {"years_the_values_fit": "2001 to 2020", "agrees_with_the_period_named": False},
            "counts": {"north_cells": {"cells": 4, "july": {"t2m_c": {"median": 5.7, "p10": 1.9, "p90": 9.7, "cells": 4},
                                                              "ts_c": {"median": 5.3, "p10": 0.1, "p90": 10.1, "cells": 4},
                                                              "t2m_max_c": {"median": 17.2, "p10": 8.6, "p90": 23.8, "cells": 4}}},
                       "south_cells": {"cells": 1, "january": {"t2m_c": {"median": -13.0, "p10": -20.0, "p90": -3.3, "cells": 1}}}},
            "lunar_comparison": {"status": "filled from the moon cards", "earth_low_c": -4.0, "earth_high_c": 10.1,
                                 "lunar_mean_low_c": -155.8, "lunar_mean_high_c": -129.7, "lunar_coldest_c": -234.0,
                                 "sentence": "Earth does not match the Moon in temperature."},
            "named_places": {"places": [
                {"name": "Somewhere", "lat": 70.6, "lon": 20.0, "cell": "70.6_20.0", "grid_elev_m": 352.81,
                 "daily_series": {"by_bin": {"t2m_c": [0.0] * 36}},
                 "best_bins_by_target": {"malapert": [
                     {"bin": 23, "dates": "19 Aug-28 Aug", "hours": 4.2,
                      "month_climatology": {"t2m_c": 1.9, "t2m_max_c": 9.69, "t2m_min_c": -5.85, "ts_c": 1.47},
                      "ten_day_mean_of_daily_series": {"t2m_c": 1.5, "t2m_daily_max_c": 2.6, "t2m_daily_min_c": 0.2, "ts_c": 1.1}}],
                     "connecting-ridge": []},
                 "best_bins_any_target": []},
                {"name": "Off the page", "lat": 10.0, "lon": 10.0, "cell": "10.0_10.0", "grid_elev_m": None,
                 "best_bins_by_target": {}}]}}
    return {"meta": meta, "cells": cells}


def moon_card(target: str, official: str, in_project: str, picture: bool, confirmed) -> dict:
    return {
        "id": target, "official_name": official, "name_in_project": in_project, "name_note": "a note on the name",
        "nasa_list": {"on_2022_list_of_13": True, "name_2022": official, "on_2024_list_of_9": picture,
                      "name_2024": official if picture else None, "summary": "On the 2022 list of 13.",
                      "links": ["https://example.org/2022"]},
        "why_stored": "a stored reason",
        "why_check": {"confirmed": confirmed, "note": "a note",
                      "proposed_wording": None if confirmed else "a sourced wording",
                      "proposed_wording_sources": ["https://example.org/why"]},
        "pgda_model": {"site": "Site01", "page": "https://example.org/78", "dem_url": "https://example.org/dem.tif",
                       "pixel_m": 5, "what": "a 5 m model", "citation": "Barker et al. (2021)"},
        "centre": {"lat": -89.463162834037, "lon_east": 222.51044707800082}, "extent_km": [16.0, 16.0],
        "sun_ceiling": {"deg": 2.076837165962993, "range_deg": [1.7048893172816486, 2.449716391078007],
                        "how": "90 - |latitude| + 1.54 degrees", "kind": "derived from latitude", "source": "https://example.org/dem.tif"},
        "shadow_of_1m_object_at_ceiling_m": 27.58, "shadow_how": "1 m divided by the tangent of the Sun ceiling.",
        "lit": {"mean_share": 0.29287081309868573, "best_point_share": 0.93476, "how": "a map", "kind": "measured terrain, modelled Sun",
                "source": "https://example.org/69", "file": "https://example.org/AVGVISIB.TIF"},
        "permanent_shadow": {"share": 0.030296279795054577, "how": "a map", "kind": "measured terrain, modelled Sun",
                             "source": "https://example.org/69", "file": "https://example.org/LPSR.TIF"},
        "diviner": {"model_based": True, "triangles": 1985, "triangles_without_temperature": 0, "area_covered_km2": 254.793,
                    "target_area_km2": 256.0,
                    "annual_mean_temp_2cm_K": {"mean": 122.52, "min": 39.186, "max": 186.478},
                    "annual_max_temp_surface_K": {"mean": 247.697, "min": 63.803, "max": 321.106},
                    "annual_mean_temp_2cm_C": {"mean": -150.63, "min": -233.96, "max": -86.67},
                    "annual_max_temp_surface_C": {"mean": -25.45, "min": -209.35, "max": 47.96},
                    "ice": {"stable_within_reach_share": 0.36222, "stable_at_surface_share": 0.0,
                            "surface_cold_trap_share": 0.00655, "stable_within_1m_share": 0.35466,
                            "not_stable_within_reach_share": 0.63778,
                            "stable_within_reach_share_without_undocumented_value": 0.35567,
                            "shallowest_m": 0.0, "deepest_stable_m": 1.2319},
                    "altitude_check": {"triangles_compared": 1985, "correlation": 0.9946},
                    "kind": "model-based", "how": "thermal-model fits", "source": "https://example.org/diviner",
                    "citation": "Paige et al., 2018"},
        "picture": ({"page": "https://example.org/mosaic", "title": "a low-Sun mosaic", "product": "NAC_ROI_X",
                     "note": "1 m per pixel", "credit": "NASA/GSFC/Arizona State University",
                     "credit_source": "https://example.org/terms", "citation": "Henriksen et al. (2023)",
                     "sun_heights_of_images": {"images_listed": 184, "sun_height_min_deg": -1, "sun_height_max_deg": 6,
                                               "images_above_flat_ceiling_at_their_latitude": 0},
                     "image_downloaded": False} if picture else
                    {"page": None, "title": None, "product": None, "note": "No low-Sun mosaic is named for it.",
                     "nearby": ["https://example.org/near"],
                     "alternative": {"page": "https://example.org/dtm", "title": "a terrain model", "what": "not a mosaic",
                                     "credit": "NASA/GSFC/Arizona State University", "credit_source": "https://example.org/terms"},
                     "credit": None, "credit_source": None, "citation": None, "sun_heights_of_images": None,
                     "image_downloaded": False}),
        "earth_cannot_match": [
            {"what": "vacuum", "number": 3e-15, "unit": "bar", "moon": "No air.", "earth": "About 1 bar.", "source": "https://example.org/fact"},
            {"what": "dust", "number": None, "unit": None, "moon": "Sharp dust.", "earth": "Rounded soil.", "source": None,
             "note": "No number: we read no dust dataset."},
            {"what": "black shadows", "number": 0.0, "unit": "made-up zero", "moon": "Black.", "earth": "Lit by the sky.", "source": None}],
    }


def moon_doc() -> dict:
    return {"meta": {"generated": "2026-11-14", "pages_read_on": "2026-11-14",
                     "lists": {"2022": {"what": "NASA's 13 candidate regions", "links": ["https://example.org/2022"]},
                               "2024": {"what": "NASA's nine candidate regions", "links": ["https://example.org/2024"], "note": "a note"}},
                     "diviner": {"product": "LRO Diviner Polar Resource Product", "folder": "https://example.org/diviner",
                                 "model_based": True,
                                 "columns_used": {"temp_avg": "annual average temperature, K, 2 cm below the surface"},
                                 "special_value": {"value": -999.0, "column": "ice_depth", "meaning": "deeper than 2.8738 m"},
                                 "undocumented_value": {"value": -1.0, "column": "ice_depth", "in_label": False, "records": 100319,
                                                        "of_records": 2880000, "our_reading": "Ice stable on the surface itself."},
                                 "mesh": "2,880,000 triangles", "not_checked": "the product's own uncertainty"},
                     "picture_credit": {"credit": "NASA/GSFC/Arizona State University", "source": "https://example.org/terms",
                                        "note": "Links and credits only; no image was downloaded."},
                     "unknown_is": "null"},
            # on purpose not in the page's order
            "cards": [moon_card("malapert", "Malapert Massif", "Malapert Massif", True, True),
                      moon_card("connecting-ridge", "Connecting Ridge", "Shackleton-de Gerlache connecting ridge", False, False)]}


def sunpath_doc() -> dict:
    hours = [round(0.572 + k, 3) for k in range(120)]                       # five days of hourly rows
    lunar_az = [round((180.0 - 0.51 * h) % 360.0, 2) for h in hours]
    lunar_el = [round(5.0 * math.sin(math.radians(0.51 * h)) - 1.0, 3) for h in hours]
    solar = [round(k / 12.0, 4) for k in range(289)]                         # every 5 minutes, 0 to 24 h
    earth_az = [round(15.0 * t, 2) for t in solar]
    earth_el = [round(17.5 - 14.5 * math.cos(math.radians(15.0 * t)) - 0.01 * t, 3) for t in solar]
    return {
        "meta": {"written": "2026-11-14T16:32:00", "caption_for_any_drawing": "Drawn by code from made-up data; code written with AI assistance.",
                 "angles": "degrees; azimuth 0 = north, clockwise",
                 "lunar_sites": {"source": "NASA/JPL Horizons API", "not_in_these_numbers": "lunar terrain (a smooth sphere is assumed)"},
                 "earth_places": {"path": "every 5 minutes of local solar time", "terrain_horizon": "one value per 10-degree sector"}},
        "lunar_sites": [
            {"id": "connecting-ridge", "name": "Shackleton-de Gerlache connecting ridge", "ceiling_deg": 2.08, "year": 2026,
             "year_max_elevation_deg": 2.05, "year_max_utc": "2026-Nov-06 14:00", "mean_trip_days": 29.531,
             "path": {"complete": True, "hours_since_start": hours, "azimuth_deg": lunar_az, "elevation_deg": lunar_el}},
            {"id": "malapert", "name": "Malapert Massif", "lat": -85.99478, "lon_east": 359.76422, "ceiling_deg": 5.55,
             "ceiling_rule": "90 - |latitude| + 1.54", "year": 2026, "year_max_elevation_deg": 5.527,
             "year_max_utc": "2026-Nov-24 09:00", "year_max_azimuth_deg": 0.73, "year_max_minus_ceiling_deg": -0.023,
             "year_min_elevation_deg": -5.489, "year_min_utc": "2026-May-16 17:00", "year_share_above_level_horizon": 0.5158,
             "year_share_above_ceiling": 0.0, "mean_trip_days": 29.531, "shortest_trip_days": 29.455, "longest_trip_days": 29.611,
             "direction": "anticlockwise (east to north to west)", "path_trip_days": 29.592,
             "path_days_above_level_horizon": 18.46, "path_days_in_band": 18.46,
             "path": {"what": "one trip of the Sun round the horizon", "complete": True, "start_utc": "2026-Nov-09 16:00",
                      "end_utc": "2026-Dec-09 05:00", "hours_since_start": hours, "azimuth_deg": lunar_az, "elevation_deg": lunar_el}}],
        "earth_places": [
            {"id": "top", "name": "A flat coast", "cell_id": "68.9_54.3", "minutes_in_band": 332, "path": None},
            {"id": "haughton", "name": "Haughton crater, Devon Island", "why": "rover tests", "place_lat": 75.38, "place_lon": -89.67,
             "cell_id": "70.6_20.0", "cell_lat": 75.35, "cell_lon": -89.75, "region": "Arctic Canada", "target": "malapert",
             "band_deg": [0.0, 5.55], "best_bin": 21, "best_bin_label": "30 Jul-8 Aug", "best_bin_hours": 39.3, "day_of_year": 215,
             "date": "3 Aug",
             "path": {"solar_time_h": solar, "azimuth_deg": earth_az, "elevation_deg": earth_el,
                      "true_elevation_deg": [round(v - 0.2, 3) for v in earth_el]},
             "path_missing_because": None, "day_min_elevation_deg": 2.916, "day_max_elevation_deg": 32.131,
             "minutes_in_band": 285, "longest_spell_minutes": 292, "minutes_above_terrain": 285,
             "longest_spell_minutes_above_terrain": 292, "minutes_above_terrain_cell_median": 285,
             "longest_spell_minutes_above_terrain_cell_median": 292,
             "terrain_horizon": {"sector_centres_deg": [5.0 + 10 * k for k in range(36)], "centre_deg": [0.26] * 36,
                                 "cell_median_deg": [0.72] * 36, "cell_p10_deg": [0.06] * 36,
                                 "cell_p90_deg": [round(4.5 + 0.04 * k, 2) for k in range(36)], "north_deg": 0.77, "south_deg": 1.79,
                                 "centre_is_land": True, "land_share": 1.0, "pixel_m": 60.0, "half_km": 5.0, "reach_km": 25.0,
                                 "eye_m": 2.0},
             "terrain_horizon_missing_because": None}]}


def funnel_step(cells, unknown=0, kept=None):
    return {"cells": cells, "bare_km2": cells * 50.5, "unknown_cells": unknown, "share_of_scope": 0.5,
            "share_of_sun_alone": 0.25, "share_of_previous_step": 0.5, "share_of_previous_step_with_a_value": 0.5,
            "median_share_of_hours_kept": kept, "still_at_least_h": {"50": cells + 2, "25": cells + 4}}


def funnel_scope(n):
    return {"scope": {"cells": n, "bare_km2": n * 46.7}, "sun_alone": funnel_step(40), "after_snow": funnel_step(20, 3, 0.382),
            "after_terrain": funnel_step(7, 5, 0.664), "after_cloud": funnel_step(0, 0, 0.243)}


def known_row(name, cell, verdict, hours):
    return {"name": name, "source": "data/reference/known_analogs.json", "lat": 70.6, "lon": 20.0, "cell": cell, "hemisphere": "N",
            "in_the_search": True, "region": "Grey Land", "bare": 0.53, "snow_status": "measured", "has_a_horizon": hours is not None,
            "cell_ranked": hours is not None, "not_ranked_because": [] if hours is not None else ["no horizon"],
            "analog_for": "impact crater", "tier": "A",
            "targets": {t: {"long_flat_hours": 80.2, "long_snow_free_hours": 22.3, "long_open_hours": hours,
                            "hours_field": "long_open_hours", "percentile_among_ranked": None if hours is None else 72.2,
                            "rank_from_top": None if hours is None else 1970, "ranked_cells": 7123, "verdict": verdict,
                            "flat_horizon_hours": 22.3, "flat_field": "long_snow_free_hours",
                            "percentile_flat_among_rankable": 71.1, "rankable_cells": 10849} for t in TARGET_IDS[:2]}}


def validation_doc(census=False) -> dict:
    targets = TARGET_IDS[:2]
    return {
        "meta": {"written": "2026-11-14T16:31:40", "written_utc": "2026-11-15T00:31:40+00:00",
                 "targets": [{"id": t, "name": t, "limit_deg": 2.08} for t in targets], "threshold_h": 100.0,
                 "long_rule": "per-day spells", "stretch_min_h": 2.0, "winter_half": "28 September to 31 March",
                 "summer_half": "1 April to 27 September", "an_input_changed_during_the_run": False,
                 "unknown": "null means unknown, never 0"},
        "lower_latitude_sites": {
            "what": "flat horizon",
            "sites": [{"name": "Karakoram", "lat": 35.9, "lon": 76.5, "kind": "other teams' terrain twin",
                       "targets": {t: {"limit_deg": 2.08, "hours_a_year_in_band": 151.5, "mean_minutes_a_day_in_band": 24.9,
                                       "longest_spell_h": 0.22, "longest_spell_minutes": 13, "best_day": "1 Jan",
                                       "hours_in_spells_of_1h": 0.0, "hours_in_spells_of_2h": 0.0, "hours_in_spells_of_3h": 0.0,
                                       "has_a_2h_spell": False, "profile_hours_a_year_in_band": 151.58,
                                       "profile_hours_in_spells_of_2h": 0.0} for t in targets}}],
            "summary": {t: {"sites": 1, "sites_with_a_2h_spell": 0, "hours_a_year_in_band_min": 123.4,
                            "hours_a_year_in_band_max": 186.6, "longest_spell_minutes_max": 17,
                            "longest_spell_site": "Karakoram"} for t in targets}},
        "latitude_against_full_method": {
            "what": "measured northern cells", "threshold_h": 100.0, "long_rule": "per-day spells",
            "measured_cells": 100, "measured_cells_with_a_horizon": 100 if census else 61, "horizon_coverage": 1.0 if census else 0.6116,
            "with_a_horizon_is_a_census": census, "cloud": "present",
            "targets": {t: {half: {"all_measured_cells": funnel_scope(100), "measured_cells_with_a_horizon": funnel_scope(61)}
                            for half in ("winter_half", "summer_half", "year")} for t in targets}},
        "known_sites": {
            "what": "each site is read on the cell that holds it", "ranked_rule": "gridded, bare ground at least 0.25",
            "caveat": "With so few known lighting analogs this is a sanity check, not a test of the ranking.",
            "ranked_population": {"N": {"ranked_cells": 7125, "ranked_is_a_census": census}, "S": {"ranked_cells": 560, "ranked_is_a_census": False}},
            "summary": {"north_all_listed_sites": {t: {"cells_with_a_value": 1, "cells_without_a_value": 1, "median_percentile": 27.3,
                                                       "high": 1, "middling": 0, "low": 0} for t in targets}},
            "sites": {"known_analogs_poleward_of_59": [known_row("Haughton", "70.6_20.0", "high", 10.8),
                                                      known_row("Never searched", "10.0_10.0", None, None)],
                      "named_sites_north": [], "antarctic_sites": []}},
        "sensitivity": {
            "what": "count of measured northern cells", "threshold_h": 100.0, "step_minutes": 1,
            "checks": {t: {"sun_module_count": 624} for t in targets},
            "targets": {t: {"limit_deg": 2.08,
                            "from_the_sun_module": {"baseline": {"cells": 624, "bare_km2": 29643.1}},
                            "from_the_data_files": {"all_measured_cells": {"cells_in_scope": 100}},
                            "table": [{"choice": "baseline: Sun geometry alone", "scope": "all measured cells", "cells": 624,
                                       "bare_km2": 29643.1, "baseline_cells": 624, "change": None, "moves_more_than_a_quarter": None},
                                      {"choice": "Sun ceiling 0.5 degrees lower", "scope": "all measured cells", "cells": 0,
                                       "bare_km2": 0.0, "baseline_cells": 624, "change": -1.0, "moves_more_than_a_quarter": True}],
                            "moves_more_than_a_quarter": ["Sun ceiling 0.5 degrees lower (all measured cells: 624 to 0 cells)"]}
                        for t in targets}},
        "headlines": ["At the 11 lower-latitude places none has a spell of two hours or more.",
                      "Malapert Massif, summer half: 10,803 of 14,863 measured cells reach 100 long-window hours."]}


def snow_stats(stations, n, bias, difference, calibration=True):
    stats = {"stations": stations, "n": n, "mean_bias": bias, "median_bias": 0.0, "mean_abs_difference": difference,
             "median_of_station_means": -0.03, "mean_bias_95_interval": [-0.09, -0.05]}
    if calibration:
        stats["calibration"] = [{"ims_low": 0.0, "ims_high": 0.1, "n_station_bins": 7, "mean_ims": 0.01, "mean_station_snow_free": 0.05}]
    return stats


def snow_check_doc() -> dict:
    """The station check of the snow maps, as data/derived/snow_validation_many.json holds it (cut down)."""
    def period(what, days, stations, n, bias, difference):
        return {"what": what, "bins": [0, 1, 2], "days": days, "min_lat": None, "stations_in_group": 139,
                "with_stale_flag_rule": snow_stats(stations, n, bias, difference),
                "as_mapped": snow_stats(stations, n, None if bias is None else bias + 0.002,
                                        None if difference is None else difference - 0.001),
                "with_stations_under_snow_all_winter_added": {"stations_added": ["X"]}}
    return {
        "method": {"source": "NOAA GHCN-Daily snow depth (SNWD), per-station CSV files", "snow_years": [2015, 2024], "min_lat": 59.0,
                   "period": "ten snow years, 1 October 2015 to 30 September 2025", "trust_rule": "snow depth on at least 80% of days",
                   "bias": "satellite minus station; negative means the satellite layer shows more snow",
                   "n": "station-bins: one station in one ten-day bin"},
        "selection": {"candidates_inventory_rule": 891, "examined": 426, "kept": 139, "reasons": {"kept": 139}},
        "overall": snow_stats(139, 4289, -0.0701, 0.0862, calibration=False),
        "periods": {"whole_year": period("all 36 bins", "1 Jan-31 Dec", 139, 4289, -0.0701, 0.0862),
                    "winter_half": period("winter half", "28 Sep-31 Mar", 139, 2401, -0.0513, 0.0723),
                    "summer_half": period("summer half", "1 Apr-27 Sep", 139, 1888, -0.094, 0.1039),
                    "may_to_august": period("May to August", "1 May-28 Aug", 119, 1203, None, None)},
        "calibration": [{"ims_low": 0.0, "ims_high": 0.1, "n_station_bins": 2016, "mean_ims": 0.0085, "mean_station_snow_free": 0.052},
                        {"ims_low": 0.1, "ims_high": 0.3, "n_station_bins": 0, "mean_ims": None, "mean_station_snow_free": None},
                        {"ims_low": 0.9, "ims_high": 1.0, "n_station_bins": 1171, "mean_ims": 0.988, "mean_station_snow_free": 0.995}],
        "stations": [{"id": "NOE00134910", "name": "GRUNNFJORD - STAKKEN", "satellite": [0.1] * 36}],
        "not_kept": [{"id": "NOE00133182", "name": "REPVAG"}]}


SOURCES_TEXT = """# Data sources, licences and credit lines

Some words first.

## 1. The sources

| # | Full name | Provider | Group | What we use it for | Link we fetch from | Licence or terms | Credit the provider asks for | Raw files in a public repository? | Derived products in a public repository? |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Lunar terrain models (product 78): `Site01`, `Site23` | NASA Goddard | NASA | The four lunar sites | `https://example.gov/data/<site>/<site>_surf.tif` | "Data Usage Policy" on https://example.gov/products/78 : cite the paper | Credit A | Allowed, but large: do not commit | Yes, with the citation |
| 2 | A table with a pipe in its name: `a|b.tab` | A \\| B consortium | Partner (ESA) | Bare ground | `https://example.org/v200/2021/map` | CC BY 4.0, stated on https://example.org/en/data-access | Credit F | Allowed with credit | Yes, with credit |
| 3 | Snow maps | U.S. National Ice Center (NOAA) | Other (NOAA) | Snow-free odds | https://example.com/snow (the page) | **Not open. Settled:** terms on https://example.com/terms . | Credit G | Free to share | Yes |
| 4 | Our own list, `data/reference/known.json` | Compiled by the team | Other | Marks areas | Hand-compiled; `source_url` in each entry | Facts with links | Cite each `source_url`; Credit N for the Wikipedia entries | Yes | Yes |
| 5 | A catalogue | The Open University | Other (ESA-funded literature, not ESA data) | A check | https://example.net/catalogue.pdf | No licence in the document | Cite as: Preston, L. (2012), The Catalogue, under contract 4000104716/11/NL/AF | **No** | Yes |

Downloaded while scouting and **used by nothing**: some things.

## 2. Must not be committed to a public repository

- `data/raw/` stays out.

## 3. Credit lines to print on the page and in the README

Print these as written. Dates in brackets are the day we fetched the data.

- **A. Lunar terrain (product 78):** Barker, M.K., et al. (2021), Improved Elevation Maps: Error Estimates
  and Their Impact, Planetary & Space Science, Volume 203, 105119, doi:10.1016/j.pss.2020.105119. Data: the archive,
  https://example.gov/products/78
- **E. Elevation model.** Beside anything we computed from it:
  "produced using Copernicus WorldDEM-90 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018
  provided under COPERNICUS by the European Union and ESA; all rights reserved".
  The licence also prescribes: "The organisations in
  charge of the Copernicus programme by law or by delegation do not incur any liability for any use of the
  Copernicus WorldDEM-90". And we must not give the impression that our work is endorsed by them.
- **F. Land cover:** © ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021)
  processed by ESA WorldCover consortium. https://doi.org/10.5281/zenodo.7254221 (CC BY 4.0).
- **G. Snow maps:** U.S. National Ice Center. (2008). Snow and Ice Analysis. [Data Set]. Date Accessed 11-14-2026.
- **L. COMNAP:** Station names, status and distances: COMNAP Antarctic Facilities list, version 3.2.0
  (COMNAP 2019), copyright COMNAP, used here for educational and non-commercial purposes only.
- **N. Wikipedia:** Site names come in part from Wikipedia (`known.json`), by Wikipedia
  contributors, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/). The list is shared under the
  same licence.

One line for the page footer and the README licence section: "Code: Apache License 2.0. Our result files:
CC BY 4.0, except `data/reference/known.json` (CC BY-SA 4.0). Not a NASA product; no endorsement by NASA
or any other provider is implied."

The page's source list today names 8 sources.

## 4. What to put in the submission form

**NASA Data field:**
- Lunar terrain models, product 78 (Barker et al. 2021):
  https://example.gov/products/78
- NASA Worldview, only if the page really links to it: https://worldview.example.gov/ (it is in the
  challenge's own resource list; our pipeline does not read it).

**Space Agency Partner Data field** (ESA is a 2026 partner, and the challenge lists a
partner resource):
- Land cover 10 m 2021 v200: https://example.org/

**Other open data (not NASA, not a partner agency; name them in the project text, not in the two fields):**
Snow maps; station records; Natural Earth; Wikipedia.
The UK Space Agency is a partner, but the survey is a different body.

## 5. Not checked

- Many things.
"""


def station(name, km_value):
    return {"name": name, "km": km_value, "kind": "station", "lat": 70.0, "lon": 20.5, "note": "a weather station",
            "source_url": "https://example.org/station"}


def comnap(name, km_value, seasonality="Year-Round"):
    return {"name": name, "km": km_value, "type": "Station", "seasonality": seasonality, "status": "Open",
            "from": "COMNAP Antarctic Facilities list (COMNAP 2019); copyright COMNAP, free for educational and non-commercial use only"}


def check_doc() -> dict:
    return {
        "meta": {"written": "2026-11-15T00:31:13Z", "rule": "missing when no entry of ours lies within 50 km",
                 "evidence_levels": {"opened today": "we read the page itself"}, "not_checked": ["permits"]},
        "missing_from_our_list": [
            {"name": "A catalogue site", "lat": 70.66, "lon": 20.1, "analog_for": "Mars: carbonates", "listed_in": "a catalogue",
             "source_url": "https://example.org/catalogue.pdf", "cells_within_50_km": {"cells": 2, "flagged_little_known": 0}}],
        "also_published_elsewhere_and_missing": [
            {"name": "Tunnunik impact structure, Victoria Island", "lat": 72.4667, "lon": -113.9333,
             "analog_for": "Moon and Mars: eroded impact structure", "source_url": "https://example.org/tunnunik",
             "evidence": "search result summary", "cells_within_50_km": {"cells": 1, "flagged_little_known": 1}}],
        "antarctic_sites_suggested_changes": [
            {"site": "Vestfold Hills", "field": "existing_analog_use", "now": None, "suggest": "Deep Lake is studied as a model for Martian brines",
             "effect": "the cells would stop being called little known", "source_url": "https://example.org/deep-lake",
             "evidence": "search result summary"}],
        "top_places": [
            {"name": "A quiet coast", "analog_use_found": False,
             "hosts_analog_or_polar_field_work": "A staffed weather station stands on the same coast. We found no space-analog work.",
             "evidence": [{"claim": "the station", "url": "https://example.org/station", "level": "search result summary"}],
             "not_checked": "Sources in other languages.",
             "points": [{"lat": 70.05, "lon": 20.1, "nearest_known_site_of_ours": {"name": "Far away", "km": 1528.5},
                         "nearest_published_site_missing_from_ours": {"name": "Also far", "km": 1542.8, "listed_in": "a catalogue"},
                         "nearest_station": station("Near station", 27.2), "nearest_airfield": None},
                        {"lat": 70.65, "lon": 20.1, "nearest_known_site_of_ours": {"name": "Far away", "km": 1500.0},
                         "nearest_published_site_missing_from_ours": None,
                         "nearest_station": station("Other station", 128.3),
                         "nearest_airfield": {"name": "An airfield", "km": 150.5, "kind": "airfield", "note": "gravel",
                                              "source_url": "https://example.org/airfield"}}],
             "cells_within_50_km": {"cells": 3, "flagged_little_known": 2}},
            {"name": "Vestfold Hills, Antarctica", "analog_use_found": True,
             "hosts_analog_or_polar_field_work": "Yes. A year-round station is at the edge of the hills.",
             "evidence": [{"claim": "the lake", "url": "https://example.org/deep-lake", "level": "search result summary"},
                          {"claim": "the station", "url": "https://example.org/davis", "level": "opened today"}],
             "not_checked": "Permits.",
             "points": [{"lat": -68.5, "lon": 78.2, "nearest_known_site_of_ours": {"name": "Concordia", "km": 1670.9},
                         "nearest_published_site_missing_from_ours": None,
                         "nearest_comnap_facility": comnap("Davis", 12.6), "nearest_year_round_comnap_station": comnap("Davis", 12.6),
                         "nearest_airfield": None, "nearest_airfield_note": "the COMNAP list has no airfield camp within 800 km"}],
             "cells_within_50_km": {"cells": 1, "flagged_little_known": 1},
             "nearest_comnap_facility": comnap("Davis", 12.6), "nearest_year_round_comnap_station": comnap("Davis", 12.6)},
            {"name": "Not looked at", "analog_use_found": None, "hosts_analog_or_polar_field_work": None, "evidence": [],
             "not_checked": None, "points": [{"lat": 10.0, "lon": 10.0}], "cells_within_50_km": None}]}


def antarctic_doc() -> list:
    return [{"name": "Vestfold Hills", "lat": -68.55, "lon": 78.25, "nearest_station": "Davis", "nearest_station_km": 11.8,
             "nearest_station_seasonality": "Year-Round", "nearest_year_round_station": "Davis",
             "nearest_year_round_station_km": 11.8, "station_year_round": True, "winter_snow_evidence": "one qualitative report",
             "winter_snow_note": "a long note", "existing_analog_use": None, "rock_type": None,
             "source_urls": ["https://example.org/wfs"]},
            {"name": "Far Oasis", "lat": -70.76, "lon": 11.65, "nearest_station": "Maitri", "nearest_station_km": 2.0,
             "nearest_station_seasonality": "Year-Round", "nearest_year_round_station": "Maitri",
             "nearest_year_round_station_km": 2.0, "station_year_round": True, "winter_snow_evidence": None,
             "existing_analog_use": None, "rock_type": None, "source_urls": []}]


def cloud_doc(day=True) -> dict:
    def row(july, august, december, january):
        values = [january, 50.0, 50.0, 50.0, 50.0, 50.0, july, august, 50.0, 50.0, 50.0, december]
        return values
    cells = {
        "70.0_20.0": {"cloud_pct": row(40.0, 50.0, 80.0, 80.0), "grid": [70.5, 20.5]},
        "70.3_20.0": {"cloud_pct": row(60.0, None, 80.0, 80.0), "grid": [70.5, 20.5]},
        "70.6_20.0": {"cloud_pct": row(80.0, 90.0, 80.0, 80.0), "grid": [70.5, 20.5]},
        "72.4_-114.0": {"cloud_pct": None, "grid": None},
        "-68.6_78.0": {"cloud_pct": row(90.0, 90.0, 51.2, 55.0), "grid": [-68.5, 78.5]},
    }
    if day:
        cells["70.0_20.0"]["cloud_pct_day"] = row(46.0, 50.0, None, None)        # July differs by 6 points
        cells["70.3_20.0"]["cloud_pct_day"] = row(62.0, 70.0, None, None)        # August has no all-hours value
        cells["70.6_20.0"]["cloud_pct_day"] = row(80.0, 95.0, None, None)        # exactly 5 points: not "more than"
        cells["72.4_-114.0"]["cloud_pct_day"] = None
        cells["-68.6_78.0"]["cloud_pct_day"] = row(90.0, 90.0, 51.2, 61.0)       # January differs by 6 points
    return {"meta": {"source": "NASA POWER, made up", "parameter": "CLOUD_AMT", "period": "2001-01-01 to 2025-12-31", "grid_deg": 1.0,
                     "units": "percent of sky covered, monthly mean, January first", "what_it_is": "Monthly mean share of the sky covered by cloud.",
                     "what_it_is_not": "Not the chance that a low Sun is visible.", "written": "2026-11-15T00:13:16Z"},
            "cells": cells}


def grazing_doc() -> dict:
    regions = ["Clear Land", "Clear Land", "Grey Land", "Grey Land", "South Land"]
    return {"meta": {}, "cells": [{"id": i, "lat": la, "lon": lo, "hemisphere": "N" if la > 0 else "S", "region": r}
                                  for i, la, lo, r in zip(AREA_IDS, AREA_LAT, AREA_LON, regions)]}


@pytest.fixture
def project(tmp_path):
    """A made-up project folder with every input the export reads."""
    derived, reference, site = tmp_path / "data" / "derived", tmp_path / "data" / "reference", tmp_path / "site" / "data"
    write(site / "cells.json", page_cells())
    write(site / "meta.json", page_meta())
    write(derived / "moon_cards.json", moon_doc())
    write(derived / "temperature_cells.json", temperature_doc())
    write(derived / "validation_extras.json", validation_doc())
    write(derived / "snow_validation_many.json", snow_check_doc())
    write(derived / "sunpath_demo.json", sunpath_doc())
    write(derived / "cloud_cells.json", cloud_doc())
    write(derived / "grazing_cells.json", grazing_doc())
    write(reference / "known_analogs_check.json", check_doc())
    write(reference / "antarctic_sites.json", antarctic_doc())
    write(tmp_path / "data" / "SOURCES.md", SOURCES_TEXT)
    return {"root": tmp_path, "derived": derived, "reference": reference, "site": site, "sources": tmp_path / "data" / "SOURCES.md"}


def run(project, out=None) -> dict:
    return extras.export(project["derived"], project["reference"], project["sources"], project["site"], out)


def areas():
    return extras.areas_of(page_cells())


# ---- the page's areas ----

def test_areas_are_read_in_the_pages_order_with_degrees():
    got = areas()
    assert got["ids"] == AREA_IDS
    assert got["lat"] == pytest.approx(AREA_LAT)
    assert got["lon"] == pytest.approx(AREA_LON)
    assert got["hemisphere"] == ["N", "N", "N", "N", "S"]
    assert got["region"] == ["Clear Land", "Clear Land", "Grey Land", "Grey Land", "South Land"]
    assert got["index"]["72.4_-114.0"] == 3


def test_areas_refuse_a_cells_file_with_a_repeated_id_or_unknown_units():
    doc = page_cells()
    doc["ids"][1] = doc["ids"][0]
    with pytest.raises(extras.ExtrasError, match="twice"):
        extras.areas_of(doc)
    doc = page_cells()
    doc["units"]["lat"] = "degrees"
    with pytest.raises(extras.ExtrasError, match="hundredths"):
        extras.areas_of(doc)


def test_the_export_needs_the_pages_cells_file(project):
    (project["site"] / "cells.json").unlink()
    with pytest.raises(FileNotFoundError, match="export_site.py"):
        run(project)


# ---- temperature ----

def test_temperature_is_whole_degrees_and_unknown_is_minus_128_never_0():
    table = extras.temperature_table(temperature_doc(), AREA_IDS, "t2m_c")
    assert table.dtype == np.int8 and table.shape == (5, 12)
    assert table[0].tolist() == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
    assert table[1].tolist() == [-128] * 12                               # the whole row is unknown
    # halves round away from zero, as a reader expects of "-20.5"
    assert table[2].tolist() == [-20, -21, -21, 0, 1, 0, -1, 0, 18, 3, -128, -30]
    assert table[3].tolist()[:2] == [-127, 127]                           # out of range is held at the ends, never the unknown byte
    assert table[4].tolist() == [-3] * 12


def test_a_true_zero_is_written_as_0_and_an_unknown_never_is():
    doc = temperature_doc()
    surface = extras.temperature_table(doc, AREA_IDS, "ts_c")
    assert surface[0].tolist() == [0] * 12                                # measured zero
    assert surface[1].tolist() == [-128] * 12                             # unknown
    assert extras.T_UNKNOWN == -128


def test_temperature_rows_follow_the_order_given_not_the_order_of_the_source():
    doc = temperature_doc()
    order = ["-68.6_78.0", "70.0_20.0"]
    table = extras.temperature_table(doc, order, "t2m_c")
    assert table[:, 0].tolist() == [-3, 1]


def test_a_missing_area_fails_loudly_and_names_it():
    doc = temperature_doc()
    del doc["cells"]["70.3_20.0"]
    with pytest.raises(extras.ExtrasError, match="70.3_20.0"):
        extras.temperature_table(doc, AREA_IDS, "t2m_c")


def test_a_row_of_the_wrong_length_fails_loudly():
    doc = temperature_doc()
    doc["cells"]["70.0_20.0"]["t2m_c"] = [1.0] * 11
    with pytest.raises(extras.ExtrasError, match="12"):
        extras.temperature_table(doc, AREA_IDS, "t2m_c")


def test_no_surface_table_when_the_source_has_no_surface_field():
    doc = temperature_doc()
    for record in doc["cells"].values():
        record.pop("ts_c")
    assert extras.temperature_table(doc, AREA_IDS, "ts_c") is None


def test_temperature_files_have_the_pages_area_count_and_order(project):
    report = run(project)
    raw = np.frombuffer((project["site"] / "temperature.bin").read_bytes(), dtype=np.int8).reshape(5, 12)
    assert raw[0, 0] == 1 and raw[2, 11] == -30 and raw[4, 0] == -3
    assert (raw[1] == -128).all()
    surface = np.frombuffer((project["site"] / "temperature_surface.bin").read_bytes(), dtype=np.int8).reshape(5, 12)
    assert surface[4, 0] == -5 and (surface[1] == -128).all()
    index = json.loads((project["site"] / "extras.json").read_text())
    layout = index["files"]["temperature.bin"]["layout"]
    assert layout["type"] == "int8" and layout["shape"] == [5, 12] and layout["unknown"] == -128
    assert index["files"]["temperature_surface.bin"]["layout"]["shape"] == [5, 12]
    assert index["areas"]["count"] == 5
    assert "temperature.bin" in report["written"]


def test_the_temperature_notes_keep_unknown_heights_as_null_and_the_lunar_sentence(project):
    run(project)
    block = json.loads((project["site"] / "extras.json").read_text())["temperature"]
    assert block["grid_height_m"] == [0, None, 353, 612, 88]              # null, never 0, where the service named none
    assert block["lunar_comparison"]["lunar_mean_low_c"] == -155.8
    assert block["years_the_values_fit"] == "2001 to 2020"
    assert block["medians"]["north"]["july"]["t2m_c"]["median"] == 5.7
    assert "t2m_max_c" not in block["medians"]["north"]["july"]          # an extreme of many years, easy to misread as a daily high
    place = block["named_places"][0]
    assert place["area"] == 2 and place["grid_elev_m"] == 352.81
    assert place["best_bins_by_target"]["malapert"][0]["ten_day_mean_of_daily_series"]["t2m_daily_max_c"] == 2.6
    assert block["named_places"][1]["area"] is None                       # a place whose cell is not on the page


def test_a_missing_area_stops_only_the_temperature_files_and_is_reported(project):
    doc = temperature_doc()
    del doc["cells"]["70.3_20.0"]
    write(project["derived"] / "temperature_cells.json", doc)
    report = run(project)
    assert "temperature.bin" in report["failed"] and "70.3_20.0" in report["failed"]["temperature.bin"]
    assert not (project["site"] / "temperature.bin").exists()
    assert (project["site"] / "moon.json").exists()


# ---- the lunar cards ----

def test_cards_come_in_the_pages_site_order_with_official_and_short_names():
    out = extras.moon_cards(moon_doc(), page_meta()["targets"])
    assert [c["id"] for c in out["cards"]] == ["connecting-ridge", "malapert"]
    assert [c["official_name"] for c in out["cards"]] == ["Connecting Ridge", "Malapert Massif"]
    assert [c["short_name"] for c in out["cards"]] == ["Connecting Ridge", "Malapert"]
    assert out["cards"][0]["name_in_project"] == "Shackleton-de Gerlache connecting ridge"


def test_every_number_on_a_card_equals_the_source():
    source = moon_doc()
    out = extras.moon_cards(source, page_meta()["targets"])
    by_id = {c["id"]: c for c in source["cards"]}
    checked = sum(same_numbers(card, by_id[card["id"]]) for card in out["cards"])
    assert checked > 60
    assert same_numbers(out["lists"], source["meta"]["lists"]) == 0       # words and links only
    assert same_numbers(out["diviner"], source["meta"]["diviner"]) > 2


def test_unknown_on_a_card_stays_null_and_a_true_zero_stays_zero():
    out = extras.moon_cards(moon_doc(), page_meta()["targets"])
    ridge, malapert = out["cards"]
    assert ridge["picture"]["page"] is None and ridge["picture"]["credit"] is None
    assert ridge["picture"]["sun_heights_of_images"] is None
    assert ridge["picture"]["alternative"]["page"] == "https://example.org/dtm"
    assert malapert["picture"]["page"] == "https://example.org/mosaic"
    assert malapert["picture"]["credit"] == "NASA/GSFC/Arizona State University"
    dust = [item for item in ridge["earth_cannot_match"] if item["what"] == "dust"][0]
    assert dust["number"] is None and dust["unit"] is None
    assert [item["what"] for item in ridge["earth_cannot_match"]] == ["vacuum", "dust", "black shadows"]
    assert ridge["earth_cannot_match"][2]["number"] == 0.0
    assert ridge["diviner"]["ice"]["stable_at_surface_share"] == 0.0
    assert ridge["nasa_list"]["name_2024"] is None and ridge["nasa_list"]["on_2024_list_of_9"] is False


def test_diviner_figures_carry_the_words_model_based():
    out = extras.moon_cards(moon_doc(), None)
    assert "model-based" in out["diviner"]["label"]
    for card in out["cards"]:
        assert card["diviner"]["model_based"] is True
        assert "model-based" in card["diviner"]["label"]
        assert "altitude_check" not in card["diviner"]                    # trimmed to what a card shows
    assert [c["id"] for c in out["cards"]] == ["malapert", "connecting-ridge"]   # no page order given: the file's own


def test_an_unconfirmed_reason_is_replaced_by_the_sourced_wording():
    out = extras.moon_cards(moon_doc(), page_meta()["targets"])
    ridge, malapert = out["cards"]
    assert ridge["why"] == {"text": "a sourced wording", "confirmed": False, "sourced": True,
                            "sources": ["https://example.org/why"], "note": "a note"}
    assert malapert["why"]["text"] == "a stored reason" and malapert["why"]["confirmed"] is True and malapert["why"]["sourced"] is True
    source = moon_doc()
    source["cards"][0]["why_check"] = {"confirmed": None, "note": "not checked", "proposed_wording": None, "proposed_wording_sources": []}
    unchecked = extras.moon_cards(source, None)["cards"][0]["why"]
    assert unchecked["confirmed"] is None and unchecked["sourced"] is False


def test_a_page_site_without_a_card_fails_loudly():
    targets = page_meta()["targets"] + [{"id": "nobile-rim-2", "short": "Nobile Rim 2"}]
    with pytest.raises(extras.ExtrasError, match="nobile-rim-2"):
        extras.moon_cards(moon_doc(), targets)


# ---- the Sun-path picture ----

def test_the_picture_has_the_malapert_path_and_the_haughton_path_with_its_ground():
    out = extras.sun_paths(sunpath_doc(), moon_doc(), areas())
    assert out["moon"]["id"] == "malapert" and out["earth"]["id"] == "haughton"
    assert out["moon"]["name"] == "Malapert Massif"
    assert out["band_deg"] == [0.0, 5.55] and out["moon"]["ceiling_deg"] == 5.55
    assert out["earth"]["minutes_in_band"] == 285 and out["earth"]["longest_spell_minutes"] == 292
    assert out["earth"]["date"] == "3 Aug" and out["earth"]["best_bin_label"] == "30 Jul-8 Aug"
    assert out["moon"]["start_utc"] == "2026-Nov-09 16:00" and out["moon"]["year_max_utc"] == "2026-Nov-24 09:00"
    ground = out["earth"]["terrain_horizon"]
    assert len(ground["sector_centres_deg"]) == 36 and ground["centre_deg"] == [0.26] * 36
    assert len(ground["cell_p90_deg"]) == 36 and ground["eye_m"] == 2.0
    assert out["earth"]["area"] == 2                                        # the place card it can open
    assert out["caption"].startswith("Drawn by code")


def test_every_kept_row_is_a_row_of_the_source_and_the_time_stamps_are_kept():
    source = sunpath_doc()
    out = extras.sun_paths(source, None, areas())
    lunar = source["lunar_sites"][1]["path"]
    rows = set(zip(lunar["hours_since_start"], lunar["azimuth_deg"], lunar["elevation_deg"]))
    kept = out["moon"]["path"]
    assert len(kept["hours_since_start"]) == len(kept["azimuth_deg"]) == len(kept["elevation_deg"])
    assert set(zip(kept["hours_since_start"], kept["azimuth_deg"], kept["elevation_deg"])) <= rows
    assert len(kept["hours_since_start"]) < len(lunar["hours_since_start"])            # thinned
    assert kept["hours_since_start"][0] == lunar["hours_since_start"][0]
    assert kept["hours_since_start"][-1] == lunar["hours_since_start"][-1]
    assert max(kept["elevation_deg"]) == max(lunar["elevation_deg"])                   # the highest point is never thinned away
    assert kept["rows_in_source"] == 120
    earth = source["earth_places"][1]["path"]
    rows = set(zip(earth["solar_time_h"], earth["azimuth_deg"], earth["elevation_deg"]))
    kept = out["earth"]["path"]
    assert set(zip(kept["solar_time_h"], kept["azimuth_deg"], kept["elevation_deg"])) <= rows
    assert kept["solar_time_h"][0] == 0.0 and kept["solar_time_h"][-1] == 24.0
    assert min(kept["elevation_deg"]) == min(earth["elevation_deg"])
    assert "true_elevation_deg" not in kept


def test_marks_are_a_day_apart_on_the_moon_and_an_hour_apart_on_earth():
    out = extras.sun_paths(sunpath_doc(), None, areas())
    moon = out["moon"]["marks"]
    assert moon["every_hours"] == 24
    assert np.diff(moon["hours_since_start"]).tolist() == pytest.approx([24.0] * 4)
    assert len(moon["azimuth_deg"]) == len(moon["elevation_deg"]) == 5
    earth = out["earth"]["marks"]
    assert earth["every_hours"] == 1
    assert earth["solar_time_h"] == pytest.approx([float(h) for h in range(25)])
    assert earth["elevation_deg"][0] == sunpath_doc()["earth_places"][1]["path"]["elevation_deg"][0]
    # every mark is also a point of the drawn line
    assert set(moon["hours_since_start"]) <= set(out["moon"]["path"]["hours_since_start"])
    assert set(earth["solar_time_h"]) <= set(out["earth"]["path"]["solar_time_h"])


def test_cautions_are_short_sentences_built_from_the_file():
    out = extras.sun_paths(sunpath_doc(), None, areas())
    keys = [c["key"] for c in out["cautions"]]
    assert len(keys) == len(set(keys)) and len(keys) >= 8
    assert {c["key"] for c in out["cautions"] if c["main"]} == {"best_cases", "smooth_moon", "height_only"}
    for sentence in [s for c in out["cautions"] for s in c["sentences"]] + out["shows"]:
        assert words(sentence) <= 25, sentence
        assert sentence[0].isupper() and sentence.endswith(".")
    text = " ".join(s for c in out["cautions"] for s in c["sentences"])
    assert "5.55 degrees" in text and "5.53 degrees" in text and "-5.5 degrees" in text
    assert "29.5 times" in text and "32 degrees" in text
    assert "4.5 to 5.9 degrees" in text                                    # the tenth of the area that sees the highest ground
    assert "anticlockwise" in text and "clockwise" in text
    shows = " ".join(out["shows"])
    assert "29.5 days" in shows and "4 h 45 min" in shows and "3 Aug" in shows and "18.5" in shows


def test_a_missing_earth_place_or_path_is_null_not_a_made_up_curve():
    doc = sunpath_doc()
    doc["earth_places"] = [doc["earth_places"][0]]
    out = extras.sun_paths(doc, None, areas())
    assert out["earth"] is None and out["moon"]["id"] == "malapert"
    assert any("haughton" in problem for problem in out["problems"])
    doc = sunpath_doc()
    doc["earth_places"][1]["path"] = None
    doc["earth_places"][1]["path_missing_because"] = "no best period"
    doc["earth_places"][1]["terrain_horizon"] = None
    out = extras.sun_paths(doc, None, areas())
    assert out["earth"]["path"] is None and out["earth"]["marks"] is None and out["earth"]["terrain_horizon"] is None
    assert out["earth"]["path_missing_because"] == "no best period"


# ---- how sure are we ----

def test_every_number_of_the_validation_file_equals_the_source():
    source = validation_doc()
    out = extras.validation(source, areas())
    checked = 0
    for part in ("meta", "lower_latitude_sites", "latitude_against_full_method", "known_sites", "sensitivity"):
        checked += same_numbers(out[part], source[part])
    assert checked > 300
    assert out["headlines"] == source["headlines"]
    assert out["source_written"] == "2026-11-15T00:31:40+00:00"


def test_the_validation_file_keeps_the_funnel_per_site_and_season():
    out = extras.validation(validation_doc(), areas())
    step = out["latitude_against_full_method"]["targets"]["malapert"]["summer_half"]["measured_cells_with_a_horizon"]["after_cloud"]
    assert step["cells"] == 0 and step["median_share_of_hours_kept"] == 0.243 and step["still_at_least_h"] == {"50": 2, "25": 4}
    sun = out["latitude_against_full_method"]["targets"]["malapert"]["winter_half"]["all_measured_cells"]["sun_alone"]
    assert sun["median_share_of_hours_kept"] is None                       # no step before it: unknown, not 0
    assert set(out["latitude_against_full_method"]["targets"]["connecting-ridge"]) == {"winter_half", "summer_half", "year"}


def test_flags_say_whether_the_terrain_step_is_a_census():
    out = extras.validation(validation_doc(census=False), areas())
    assert out["flags"]["terrain_step_is_a_census"] is False
    assert out["flags"]["horizon_coverage"] == 0.6116
    assert out["flags"]["measured_cells"] == 100 and out["flags"]["measured_cells_with_a_horizon"] == 61
    assert out["flags"]["ranked_is_a_census"] == {"N": False, "S": False}
    assert out["flags"]["cloud"] == "present"
    out = extras.validation(validation_doc(census=True), areas())
    assert out["flags"]["terrain_step_is_a_census"] is True and out["flags"]["ranked_is_a_census"]["N"] is True
    doc = validation_doc()
    del doc["latitude_against_full_method"]["with_a_horizon_is_a_census"]
    assert extras.validation(doc, areas())["flags"]["terrain_step_is_a_census"] is None   # not said: unknown, not "no"


def test_known_site_rows_keep_null_verdicts_and_point_at_the_pages_area():
    out = extras.validation(validation_doc(), areas())
    rows = out["known_sites"]["sites"]["known_analogs_poleward_of_59"]
    assert rows[0]["area"] == 2 and rows[0]["targets"]["malapert"]["verdict"] == "high"
    assert rows[1]["area"] is None
    assert rows[1]["targets"]["malapert"]["verdict"] is None
    assert rows[1]["targets"]["malapert"]["long_open_hours"] is None
    assert rows[1]["targets"]["malapert"]["percentile_among_ranked"] is None
    assert out["known_sites"]["caveat"].startswith("With so few")


def test_the_validation_file_leaves_out_what_must_not_be_quoted():
    out = extras.validation(validation_doc(), areas())
    place = out["lower_latitude_sites"]["sites"][0]["targets"]["malapert"]
    assert "best_day" not in place and "profile_hours_a_year_in_band" not in place
    assert place["longest_spell_minutes"] == 13 and place["hours_in_spells_of_2h"] == 0.0 and place["has_a_2h_spell"] is False
    sens = out["sensitivity"]["targets"]["malapert"]
    assert set(sens) == {"limit_deg", "table", "moves_more_than_a_quarter"}
    assert sens["table"][0]["change"] is None and sens["table"][1]["change"] == -1.0
    assert "checks" not in out["sensitivity"]


def test_the_station_check_of_the_snow_maps_keeps_its_figures_and_drops_the_bulk():
    source = snow_check_doc()
    out = extras.snow_station_check(source)
    assert out["source"] == "data/derived/snow_validation_many.json"
    assert out["overall"] == source["overall"]
    assert out["overall"]["stations"] == 139 and out["overall"]["n"] == 4289 and out["overall"]["mean_abs_difference"] == 0.0862
    assert same_numbers({k: out[k] for k in ("overall", "periods", "calibration", "selection")}, source) > 60
    assert set(out["periods"]) == {"whole_year", "winter_half", "summer_half", "may_to_august"}
    winter = out["periods"]["winter_half"]
    assert winter["days"] == "28 Sep-31 Mar" and winter["with_stale_flag_rule"]["mean_bias"] == -0.0513
    assert winter["as_mapped"]["n"] == 2401
    assert "calibration" not in winter["with_stale_flag_rule"] and "bins" not in winter
    assert "with_stations_under_snow_all_winter_added" not in winter
    assert out["method"]["period"].startswith("ten snow years") and out["method"]["min_lat"] == 59.0
    assert out["method"]["bias"].startswith("satellite minus station")
    assert out["selection"] == {"examined": 426, "kept": 139}
    assert "stations" not in out and "not_kept" not in out          # 139 stations with 36 values each stay in the pipeline


def test_unknown_in_the_station_check_stays_null_never_0():
    out = extras.snow_station_check(snow_check_doc())
    summer = out["periods"]["may_to_august"]["with_stale_flag_rule"]
    assert summer["mean_bias"] is None and summer["mean_abs_difference"] is None and summer["n"] == 1203
    assert out["calibration"][1]["mean_station_snow_free"] is None and out["calibration"][1]["n_station_bins"] == 0
    doc = snow_check_doc()
    del doc["overall"], doc["calibration"]
    out = extras.snow_station_check(doc)
    assert out["overall"] is None and out["calibration"] is None    # not said: unknown, not zero and not an empty list


def test_the_validation_file_carries_the_station_check_or_null():
    out = extras.validation(validation_doc(), areas(), snow_check_doc())
    assert out["snow_station_check"]["overall"]["stations"] == 139
    assert extras.validation(validation_doc(), areas())["snow_station_check"] is None
    assert extras.validation(validation_doc(), areas(), None)["snow_station_check"] is None


# ---- sources ----

def test_table_cells_are_split_on_real_column_bars_only():
    parsed = extras.parse_sources(SOURCES_TEXT)
    assert [s["n"] for s in parsed["sources"]] == [1, 2, 3, 4, 5]
    second = parsed["sources"][1]
    assert second["name"] == "A table with a pipe in its name: a|b.tab"
    assert second["provider"] == "A | B consortium"
    assert second["used_for"] == "Bare ground"


def test_each_source_is_a_record_with_group_link_licence_and_credit():
    parsed = extras.parse_sources(SOURCES_TEXT)
    first, second, third, fourth, fifth = parsed["sources"]
    assert first["name"] == "Lunar terrain models (product 78): Site01, Site23"
    assert first["provider"] == "NASA Goddard" and first["group"] == "NASA" and first["group_note"] is None
    assert first["used_for"] == "The four lunar sites"
    assert first["fetch_from"] == "https://example.gov/data/<site>/<site>_surf.tif"
    assert first["link"] == "https://example.gov/products/78"            # a pattern with <site> in it is not a link
    assert first["licence_links"] == ["https://example.gov/products/78"]
    assert first["credit_ref"] == "A" and first["credit"].startswith("Barker, M.K., et al. (2021)")
    assert second["group"] == "partner agency" and second["group_note"] == "ESA"
    assert second["link"] == "https://example.org/en/data-access"
    assert second["licence"] == "CC BY 4.0, stated on https://example.org/en/data-access"
    assert third["group"] == "other" and third["group_note"] == "NOAA"
    assert third["link"] == "https://example.com/snow"
    assert third["licence"] == "Not open. Settled: terms on https://example.com/terms ."
    assert third["licence_links"] == ["https://example.com/terms"]
    assert fourth["link"] is None and fourth["licence_links"] == []      # unknown stays null
    assert fourth["credit_ref"] == "N" and fourth["credit_note"] == "Cite each source_url; Credit N for the Wikipedia entries"
    assert fifth["credit_ref"] is None
    assert fifth["credit"] == "Preston, L. (2012), The Catalogue, under contract 4000104716/11/NL/AF"
    assert fifth["group"] == "other" and fifth["group_note"] == "ESA-funded literature, not ESA data"
    assert fifth["raw_files_public"] == "No"


def _credit_region(text: str) -> str:
    """The credit bullets of section 3 as one line of plain text, read independently of the parser."""
    section = text.split("\n## 3.")[1].split("\n## 4.")[0]
    lines = section.split("\n")
    first = next(i for i, line in enumerate(lines) if line.startswith("- **"))
    last = first
    for i in range(first, len(lines)):
        if lines[i].strip() == "":
            break
        last = i
    return " ".join(" ".join(lines[first:last + 1]).replace("`", "").replace("**", "").split())


def _credits_joined(parsed) -> str:
    return " ".join(f"- {c['ref']}. {c['title']}{c['mark']} {c['text']}" for c in parsed["credits"])


def test_no_credit_line_is_cut_short():
    parsed = extras.parse_sources(SOURCES_TEXT)
    assert [c["ref"] for c in parsed["credits"]] == ["A", "E", "F", "G", "L", "N"]
    assert _credits_joined(parsed) == _credit_region(SOURCES_TEXT)
    by_ref = {c["ref"]: c for c in parsed["credits"]}
    assert by_ref["A"]["title"] == "Lunar terrain (product 78)"
    assert by_ref["A"]["text"].endswith("Data: the archive, https://example.gov/products/78")
    assert by_ref["N"]["text"].endswith("The list is shared under the same licence.")
    assert by_ref["F"]["text"].startswith("© ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021) processed by")
    assert by_ref["E"]["quotes"][0] == ("produced using Copernicus WorldDEM-90 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH "
                                        "2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved")
    assert parsed["notices"]["copernicus_dem"] == by_ref["E"]["quotes"][0]
    assert parsed["notices"]["copernicus_liability"].startswith("The organisations in charge of the Copernicus programme")
    assert parsed["notices"]["copernicus_liability"].endswith("any use of the Copernicus WorldDEM-90")
    assert parsed["notices"]["comnap"] == by_ref["L"]["text"]
    assert parsed["notices"]["worldcover"] == by_ref["F"]["text"]


def test_the_licence_line_and_the_two_form_fields_are_read_whole():
    parsed = extras.parse_sources(SOURCES_TEXT)
    assert parsed["licence_line"] == ("Code: Apache License 2.0. Our result files: CC BY 4.0, except data/reference/known.json "
                                      "(CC BY-SA 4.0). Not a NASA product; no endorsement by NASA or any other provider is implied.")
    nasa = parsed["nasa_data"]
    assert [item["link"] for item in nasa] == ["https://example.gov/products/78", "https://worldview.example.gov/"]
    assert nasa[0]["name"] == "Lunar terrain models, product 78 (Barker et al. 2021)"
    assert nasa[0]["only_if_the_page_links_to_it"] is False and nasa[1]["only_if_the_page_links_to_it"] is True
    assert nasa[1]["text"].endswith("our pipeline does not read it).")
    assert [item["link"] for item in parsed["partner_data"]] == ["https://example.org/"]
    assert parsed["partner_data"][0]["name"] == "Land cover 10 m 2021 v200"
    assert parsed["other_open_data"].startswith("Snow maps; station records")
    assert parsed["other_open_data"].endswith("the survey is a different body.")
    assert parsed["problems"] == []


def test_a_table_row_with_the_wrong_number_of_cells_fails_loudly():
    broken = SOURCES_TEXT.replace("| 3 | Snow maps | U.S. National Ice Center (NOAA) |", "| 3 | Snow maps |")
    with pytest.raises(extras.ExtrasError, match="row 3"):
        extras.parse_sources(broken)


def test_a_credit_named_in_the_table_but_not_written_is_null_and_reported():
    broken = SOURCES_TEXT.replace("- **G. Snow maps:** U.S. National Ice Center. (2008). Snow and Ice Analysis. [Data Set]. Date Accessed 11-14-2026.\n", "")
    parsed = extras.parse_sources(broken)
    third = parsed["sources"][2]
    assert third["credit_ref"] == "G" and third["credit"] is None
    assert any("Credit G" in problem for problem in parsed["problems"])


# ---- places ----

def test_areas_within_50_km_are_listed_with_their_nearest_point():
    out = extras.places(check_doc(), antarctic_doc(), areas())
    coast = out["places"][0]
    assert coast["name"] == "A quiet coast"
    assert [a["id"] for a in coast["areas"]] == ["70.0_20.0", "70.3_20.0", "70.6_20.0"]
    assert [a["index"] for a in coast["areas"]] == [0, 1, 2]
    assert [a["point"] for a in coast["areas"]] == [0, 0, 1]              # the middle one is 33 km from each: the first wins a tie
    assert coast["areas"][0]["km_to_point"] == 0.0
    assert coast["areas"][1]["km_to_point"] == pytest.approx(33.4, abs=0.1)
    assert coast["cells_in_the_check_file"] == 3
    assert out["radius_km"] == 50.0
    assert out["area_place"] == {"0": [0, 0], "1": [0, 0], "2": [0, 1], "4": [1, 0]}


def test_station_and_airfield_are_copied_with_their_distance_and_null_stays_null():
    out = extras.places(check_doc(), antarctic_doc(), areas())
    coast, vestfold, unknown = out["places"]
    assert coast["points"][0]["station"]["name"] == "Near station" and coast["points"][0]["station"]["km"] == 27.2
    assert coast["points"][0]["airfield"] is None
    assert coast["points"][1]["airfield"] == {"name": "An airfield", "km": 150.5, "kind": "airfield", "note": "gravel",
                                              "source_url": "https://example.org/airfield"}
    assert vestfold["points"][0]["station"]["name"] == "Davis" and vestfold["points"][0]["station"]["km"] == 12.6
    assert vestfold["points"][0]["station"]["seasonality"] == "Year-Round"
    assert vestfold["points"][0]["year_round_station"]["km"] == 12.6
    assert vestfold["points"][0]["airfield"] is None
    assert vestfold["points"][0]["airfield_note"].startswith("the COMNAP list has no airfield")
    assert out["comnap_credit"].startswith("COMNAP Antarctic Facilities list")
    assert unknown["points"][0]["station"] is None and unknown["areas"] == []
    assert unknown["cells_in_the_check_file"] is None


def test_the_wording_is_honest_about_what_was_found():
    out = extras.places(check_doc(), antarctic_doc(), areas())
    coast, vestfold, unknown = out["places"]
    assert coast["analog_use_found"] is False and coast["wording"] == "We found no published space-analog use here."
    assert vestfold["analog_use_found"] is True and vestfold["wording"].startswith("Not a little-known place")
    assert unknown["analog_use_found"] is None and "not checked" in unknown["wording"]
    for place in out["places"]:
        assert words(place["wording"]) <= 25
        assert "never" not in place["wording"]
    assert coast["detail"].startswith("A staffed weather station")
    assert coast["links"] == ["https://example.org/station"]
    assert vestfold["links"] == ["https://example.org/deep-lake", "https://example.org/davis"]
    assert vestfold["evidence_levels"] == ["search result summary", "opened today"]


def test_the_areas_the_page_must_not_call_little_known():
    out = extras.places(check_doc(), antarctic_doc(), areas())
    block = out["not_little_known"]
    names = [entry["name"] for entry in block["because"]]
    assert names == ["Vestfold Hills, Antarctica", "Tunnunik impact structure, Victoria Island", "A catalogue site"]
    assert block["areas"] == [1, 2, 3, 4] and block["ids"] == ["70.3_20.0", "70.6_20.0", "72.4_-114.0", "-68.6_78.0"]
    tunnunik = block["because"][1]
    assert tunnunik["areas"] == [3] and tunnunik["source_url"] == "https://example.org/tunnunik"
    assert tunnunik["why"] == "Moon and Mars: eroded impact structure" and tunnunik["evidence"] == "search result summary"
    assert block["because"][2]["areas"] == [1, 2]
    # the quiet coast has no published analog use: its areas are not on the list because of it
    assert 0 not in block["areas"]
    assert block["marked_little_known_on_the_page_now"] == 3              # areas 1, 3 and 4 have known = -1 in cells.json


def test_antarctic_sites_carry_their_station_and_the_suggested_correction():
    out = extras.places(check_doc(), antarctic_doc(), areas())
    vestfold, far = out["antarctic_sites"]
    assert vestfold["nearest_station"] == "Davis" and vestfold["nearest_station_km"] == 11.8
    assert vestfold["existing_analog_use"] is None
    assert vestfold["suggested_change"]["suggest"].startswith("Deep Lake")
    assert vestfold["areas"] == [4]
    assert far["suggested_change"] is None and far["areas"] == []
    assert "winter_snow_note" not in vestfold
    out = extras.places(check_doc(), None, areas())
    assert out["antarctic_sites"] is None                                  # the file was not there: unknown, not an empty list


# ---- cloud by region ----

def test_medians_by_region_count_only_areas_with_a_value():
    out = extras.cloud_regions(cloud_doc(), grazing_doc(), areas(), min_areas=1)
    north = out["north"]
    assert north["months"] == ["July", "August"] and north["areas"] == 4
    clear = [r for r in north["regions"] if r["region"] == "Clear Land"][0]
    assert clear["areas"] == 2
    assert clear["with_a_value"] == {"July": 2, "August": 1, "both": 1}
    assert clear["median_pct"] == {"July": 50.0, "August": 50.0, "both": 45.0}
    grey = [r for r in north["regions"] if r["region"] == "Grey Land"][0]
    assert grey["areas"] == 2 and grey["with_a_value"] == {"July": 1, "August": 1, "both": 1}
    assert grey["median_pct"] == {"July": 80.0, "August": 90.0, "both": 85.0}
    assert north["all"]["median_pct"] == {"July": 60.0, "August": 70.0, "both": 65.0}
    assert north["all"]["with_a_value"] == {"July": 3, "August": 2, "both": 2}
    south = out["south"]
    assert south["months"] == ["December", "January"]
    assert south["regions"][0]["median_pct"] == {"December": 51.2, "January": 55.0, "both": 53.1}
    assert [r["region"] for r in north["regions"]] == ["Clear Land", "Grey Land"]          # clearest first
    assert north["clearest"] == "Clear Land" and south["clearest"] == "South Land"
    assert out["regions_from"] == "data/derived/grazing_cells.json"


def test_a_region_with_no_value_has_a_null_median_never_0():
    doc = cloud_doc()
    doc["cells"]["70.6_20.0"]["cloud_pct"] = None
    out = extras.cloud_regions(doc, grazing_doc(), areas(), min_areas=1)
    grey = [r for r in out["north"]["regions"] if r["region"] == "Grey Land"][0]
    assert grey["with_a_value"] == {"July": 0, "August": 0, "both": 0}
    assert grey["median_pct"] == {"July": None, "August": None, "both": None}
    assert out["north"]["regions"][-1]["region"] == "Grey Land"            # unknown sorts last, not first


def test_the_two_cloud_sentences_are_short_and_name_the_clearest_regions():
    out = extras.cloud_regions(cloud_doc(), grazing_doc(), areas(), min_areas=1)
    assert len(out["sentences"]) == 2
    north, south = out["sentences"]
    assert north.startswith("Clear Land is the clearest northern region in July and August")
    assert "45 percent" in north and "65" in north
    assert south.startswith("South Land is the clearest southern region in December and January")
    assert "53 percent" in south
    for sentence in out["sentences"] + [out["caution"]]:
        assert words(sentence) <= 25 and sentence.endswith(".")
    assert "not the chance" in out["caution"]


def test_small_regions_are_not_named_as_the_clearest():
    out = extras.cloud_regions(cloud_doc(), grazing_doc(), areas(), min_areas=3)
    assert out["north"]["clearest"] is None and out["south"]["clearest"] is None
    assert out["sentences"] == [None, None]                                # nothing to say: null, not an invented region
    assert out["min_areas_to_be_named"] == 3


def test_the_share_of_areas_whose_daytime_cloud_differs_by_more_than_5_points():
    out = extras.cloud_regions(cloud_doc(), grazing_doc(), areas(), min_areas=1)
    day = out["daytime"]
    assert day["more_than_points"] == 5.0
    assert day["north"]["July"] == {"areas_compared": 3, "differ": 1, "share": pytest.approx(1 / 3, abs=1e-4)}
    assert day["north"]["August"] == {"areas_compared": 2, "differ": 0, "share": 0.0}    # exactly 5 points is not more than 5
    assert day["north"]["either_month"] == {"areas_compared": 3, "differ": 1, "share": pytest.approx(1 / 3, abs=1e-4)}
    assert day["south"]["December"] == {"areas_compared": 1, "differ": 0, "share": 0.0}
    assert day["south"]["January"] == {"areas_compared": 1, "differ": 1, "share": 1.0}
    out = extras.cloud_regions(cloud_doc(day=False), grazing_doc(), areas(), min_areas=1)
    assert out["daytime"] is None                                          # the field is not there


def test_regions_fall_back_to_the_pages_own_when_the_grazing_file_is_missing():
    out = extras.cloud_regions(cloud_doc(), None, areas(), min_areas=1)
    assert out["regions_from"] == "site/data/cells.json"
    assert out["north"]["areas"] == 4
    assert [r["region"] for r in out["north"]["regions"]] == ["Clear Land", "Grey Land"]


def test_an_area_missing_from_the_cloud_file_is_counted_as_unknown_and_reported():
    doc = cloud_doc()
    del doc["cells"]["70.6_20.0"]
    out = extras.cloud_regions(doc, grazing_doc(), areas(), min_areas=1)
    assert out["areas_not_in_the_cloud_file"] == 1
    grey = [r for r in out["north"]["regions"] if r["region"] == "Grey Land"][0]
    assert grey["areas"] == 2 and grey["with_a_value"]["July"] == 0


# ---- the whole run ----

OUTPUTS = ["moon.json", "temperature.bin", "temperature_surface.bin", "sunpath.json", "validation.json", "sources.json",
           "places.json", "cloud_regions.json", "extras.json"]


def test_a_full_run_writes_every_file_and_an_index_with_layouts_and_sizes(project):
    report = run(project)
    assert sorted(report["written"]) == sorted(OUTPUTS)
    assert report["left_out"] == {} and report["failed"] == {}
    index = json.loads((project["site"] / "extras.json").read_text())
    for name in OUTPUTS[:-1]:
        entry = index["files"][name]
        assert entry["bytes"] == (project["site"] / name).stat().st_size == report["written"][name]
        assert entry["layout"] and entry["feeds"]
        assert entry["from"]
    assert index["unknown"].startswith("null")
    written = index["sources_written"]["data/derived/moon_cards.json"]
    assert written["modified"].endswith("Z") and written["written_inside"] == "2026-11-14"
    assert index["sources_written"]["data/derived/temperature_cells.json"]["written_inside"] == "2026-11-15T00:31:57Z"
    assert index["targets"] == ["connecting-ridge", "malapert"]
    assert not list(project["site"].glob("*.part"))


def test_the_run_writes_nothing_outside_the_output_folder(project, tmp_path):
    before = {p: p.stat().st_mtime_ns for p in (project["root"] / "data").rglob("*") if p.is_file()}
    out = tmp_path / "elsewhere"
    run(project, out)
    after = {p: p.stat().st_mtime_ns for p in (project["root"] / "data").rglob("*") if p.is_file()}
    assert before == after
    assert sorted(p.name for p in out.iterdir()) == sorted(OUTPUTS)
    assert not (project["site"] / "moon.json").exists()


@pytest.mark.parametrize("missing, left_out", [
    ("derived/moon_cards.json", ["moon.json"]),
    ("derived/temperature_cells.json", ["temperature.bin", "temperature_surface.bin"]),
    ("derived/sunpath_demo.json", ["sunpath.json"]),
    ("derived/validation_extras.json", ["validation.json"]),
    ("derived/cloud_cells.json", ["cloud_regions.json"]),
    ("reference/known_analogs_check.json", ["places.json"]),
    ("SOURCES.md", ["sources.json"]),
])
def test_the_run_goes_on_without_an_optional_input_and_says_what_it_left_out(project, missing, left_out, capsys):
    (project["root"] / "data" / missing).unlink()
    report = run(project)
    assert sorted(report["left_out"]) == sorted(left_out)
    assert Path(missing).name in " ".join(report["left_out"].values())
    assert report["failed"] == {}
    for name in OUTPUTS:
        assert (project["site"] / name).exists() == (name not in left_out)
    index = json.loads((project["site"] / "extras.json").read_text())
    assert sorted(entry["file"] for entry in index["left_out"]) == sorted(left_out)
    assert all(name not in index["files"] for name in left_out)
    assert index["sources_written"]["data/" + missing] is None
    printed = capsys.readouterr().out
    for name in left_out:
        assert name in printed


def test_the_run_goes_on_without_the_files_that_only_add_detail(project):
    (project["derived"] / "grazing_cells.json").unlink()
    (project["reference"] / "antarctic_sites.json").unlink()
    (project["site"] / "meta.json").unlink()
    report = run(project)
    assert report["left_out"] == {} and report["failed"] == {}
    assert json.loads((project["site"] / "cloud_regions.json").read_text())["regions_from"] == "site/data/cells.json"
    assert json.loads((project["site"] / "places.json").read_text())["antarctic_sites"] is None
    assert [c["id"] for c in json.loads((project["site"] / "moon.json").read_text())["cards"]] == ["malapert", "connecting-ridge"]


def test_an_older_copy_of_a_left_out_file_is_kept_and_reported(project):
    run(project)
    (project["derived"] / "moon_cards.json").unlink()
    report = run(project)
    assert (project["site"] / "moon.json").exists()
    index = json.loads((project["site"] / "extras.json").read_text())
    assert index["left_out"] == [{"file": "moon.json", "because": report["left_out"]["moon.json"], "older_copy_kept": True}]


def test_a_full_run_lacks_nothing_and_removes_nothing(project, capsys):
    report = run(project)
    index = json.loads((project["site"] / "extras.json").read_text())
    assert index["written_without"] == [] and index["older_copies_removed"] == []
    assert report["without"] == [] and report["removed"] == {}
    assert "without" not in capsys.readouterr().out


def test_an_input_that_only_adds_detail_is_named_when_it_is_missing(project, capsys):
    """Three inputs only add detail to a file. Without one the file is still written, and the run says what it lacks."""
    (project["derived"] / "grazing_cells.json").unlink()
    (project["reference"] / "antarctic_sites.json").unlink()
    (project["site"] / "meta.json").unlink()
    report = run(project)
    assert report["left_out"] == {} and report["failed"] == {}
    index = json.loads((project["site"] / "extras.json").read_text())
    assert {(entry["file"], entry["input"]) for entry in index["written_without"]} == {
        ("cloud_regions.json", "data/derived/grazing_cells.json"),
        ("places.json", "data/reference/antarctic_sites.json"),
        ("moon.json", "site/data/meta.json")}
    assert all(len(entry["lacks"]) > 20 for entry in index["written_without"])
    assert report["without"] == index["written_without"]
    printed = capsys.readouterr().out
    for entry in index["written_without"]:
        assert entry["file"] in printed and Path(entry["input"]).name in printed and entry["lacks"] in printed


def test_the_picture_is_written_without_the_moon_cards_and_says_what_it_lacks(project, capsys):
    (project["derived"] / "moon_cards.json").unlink()
    report = run(project)
    assert sorted(report["left_out"]) == ["moon.json"]
    index = json.loads((project["site"] / "extras.json").read_text())
    assert [(entry["file"], entry["input"]) for entry in index["written_without"]] == [("sunpath.json", "data/derived/moon_cards.json")]
    assert "official name" in index["written_without"][0]["lacks"]
    assert "sunpath.json" in capsys.readouterr().out
    assert json.loads((project["site"] / "sunpath.json").read_text())["moon"]["name"]      # the source's own name, not null


def test_a_full_run_puts_the_station_check_into_the_validation_file(project):
    run(project)
    out = json.loads((project["site"] / "validation.json").read_text())
    assert out["snow_station_check"]["overall"] == snow_check_doc()["overall"]
    index = json.loads((project["site"] / "extras.json").read_text())
    assert "data/derived/snow_validation_many.json" in index["files"]["validation.json"]["from"]
    assert "snow_station_check" in index["files"]["validation.json"]["layout"]
    assert index["sources_written"]["data/derived/snow_validation_many.json"]["bytes"] > 0


def test_the_validation_file_is_written_without_the_station_check_and_says_so(project, capsys):
    (project["derived"] / "snow_validation_many.json").unlink()
    report = run(project)
    assert report["left_out"] == {} and report["failed"] == {}
    out = json.loads((project["site"] / "validation.json").read_text())
    assert out["snow_station_check"] is None
    assert out["lower_latitude_sites"]["sites"]                     # the rest of the file is whole
    index = json.loads((project["site"] / "extras.json").read_text())
    assert [(entry["file"], entry["input"]) for entry in index["written_without"]] == [
        ("validation.json", "data/derived/snow_validation_many.json")]
    assert "station check" in index["written_without"][0]["lacks"]
    assert "snow_validation_many.json" in capsys.readouterr().out
    assert index["sources_written"]["data/derived/snow_validation_many.json"] is None


def test_a_station_check_that_is_not_a_record_stops_only_the_validation_file(project):
    write(project["derived"] / "snow_validation_many.json", ["not", "a", "record"])
    report = run(project)
    assert sorted(report["failed"]) == ["validation.json"]
    assert (project["site"] / "moon.json").exists() and not (project["site"] / "validation.json").exists()


def test_a_detail_is_not_reported_as_lacking_when_its_file_was_not_written_at_all(project):
    (project["derived"] / "grazing_cells.json").unlink()
    (project["derived"] / "cloud_cells.json").unlink()
    report = run(project)
    assert sorted(report["left_out"]) == ["cloud_regions.json"]
    assert report["without"] == []


def test_an_older_per_area_file_is_kept_while_the_list_of_areas_is_the_same(project):
    run(project)
    before = (project["site"] / "temperature.bin").read_bytes()
    (project["derived"] / "temperature_cells.json").unlink()
    report = run(project)
    assert (project["site"] / "temperature.bin").read_bytes() == before
    assert report["removed"] == {}
    index = json.loads((project["site"] / "extras.json").read_text())
    assert {entry["file"]: entry["older_copy_kept"] for entry in index["left_out"]} == {"temperature.bin": True,
                                                                                         "temperature_surface.bin": True}
    assert index["older_copies_removed"] == []


def test_an_older_per_area_file_made_for_another_list_of_areas_is_removed(project, capsys):
    """Rows and area numbers of an older copy would sit on the wrong areas once the page's list has changed."""
    run(project)
    write(project["site"] / "cells.json", page_cells(ids=AREA_IDS[::-1]))        # the page now lists its areas in another order
    for name in ("temperature_cells.json", "moon_cards.json", "validation_extras.json", "sunpath_demo.json", "cloud_cells.json"):
        (project["derived"] / name).unlink()
    (project["reference"] / "known_analogs_check.json").unlink()
    report = run(project)
    gone = ["places.json", "sunpath.json", "temperature.bin", "temperature_surface.bin", "validation.json"]
    assert sorted(report["removed"]) == gone
    for name in gone:
        assert not (project["site"] / name).exists(), name
    for name in ("moon.json", "cloud_regions.json", "sources.json"):                # these hold no row or number of an area
        assert (project["site"] / name).exists(), name
    index = json.loads((project["site"] / "extras.json").read_text())
    assert sorted(entry["file"] for entry in index["older_copies_removed"]) == gone
    assert all("list of areas" in entry["because"] for entry in index["older_copies_removed"])
    kept = {entry["file"]: entry["older_copy_kept"] for entry in index["left_out"]}
    assert kept["temperature.bin"] is False and kept["places.json"] is False
    assert kept["moon.json"] is True and kept["cloud_regions.json"] is True
    printed = capsys.readouterr().out
    assert "removed" in printed and "temperature.bin" in printed


def test_a_failed_per_area_file_leaves_no_copy_made_for_other_areas(project):
    run(project)
    write(project["site"] / "cells.json", page_cells(ids=AREA_IDS[:4]))          # one area fewer than the older copy has rows
    doc = temperature_doc()
    del doc["cells"]["70.3_20.0"]
    write(project["derived"] / "temperature_cells.json", doc)
    report = run(project)
    assert "temperature.bin" in report["failed"] and "temperature.bin" in report["removed"]
    assert not (project["site"] / "temperature.bin").exists() and not (project["site"] / "temperature_surface.bin").exists()
    index = json.loads((project["site"] / "extras.json").read_text())
    assert {entry["file"]: entry["older_copy_kept"] for entry in index["failed"]} == {"temperature.bin": False,
                                                                                       "temperature_surface.bin": False}


def test_an_older_per_area_file_is_removed_when_no_index_says_what_it_was_made_for(project):
    run(project)
    (project["site"] / "extras.json").unlink()
    (project["derived"] / "temperature_cells.json").unlink()
    report = run(project)
    assert sorted(report["removed"]) == ["temperature.bin", "temperature_surface.bin"]
    assert not (project["site"] / "temperature.bin").exists()


def test_the_index_carries_a_fingerprint_of_the_pages_area_order(project):
    run(project)
    first = json.loads((project["site"] / "extras.json").read_text())["areas"]
    assert first["ids_sha256"] == hashlib.sha256("\n".join(AREA_IDS).encode()).hexdigest()
    write(project["site"] / "cells.json", page_cells(ids=AREA_IDS[::-1]))
    run(project)
    second = json.loads((project["site"] / "extras.json").read_text())["areas"]
    assert second["ids_sha256"] == hashlib.sha256("\n".join(AREA_IDS[::-1]).encode()).hexdigest() != first["ids_sha256"]
    assert second["count"] == first["count"] == 5


def test_every_file_is_written_beside_its_place_and_then_renamed(project, monkeypatch):
    """A reader of site/data must never see half a file: each is written whole under another name and moved."""
    moved = []
    real_replace = os.replace

    def watched(source, target):
        assert Path(source).name == Path(target).name + ".part" and Path(source).stat().st_size > 0
        moved.append(Path(target).name)
        real_replace(source, target)

    monkeypatch.setattr(extras.os, "replace", watched)
    run(project)
    assert sorted(moved) == sorted(OUTPUTS)
    assert not list(project["site"].glob("*.part"))


def test_a_number_that_is_not_a_number_in_an_input_stops_that_file_and_never_reaches_the_page(project):
    doc = validation_doc()
    doc["known_sites"]["sites"]["known_analogs_poleward_of_59"][0]["targets"]["malapert"]["percentile_among_ranked"] = float("nan")
    write(project["derived"] / "validation_extras.json", doc)
    assert "NaN" in (project["derived"] / "validation_extras.json").read_text()
    report = run(project)
    assert list(report["failed"]) == ["validation.json"]
    assert not (project["site"] / "validation.json").exists()
    for name in OUTPUTS:
        if name.endswith(".json") and name != "validation.json":
            assert "NaN" not in (project["site"] / name).read_text()


def test_no_output_holds_a_number_that_is_not_a_number(project):
    run(project)
    for name in OUTPUTS:
        if name.endswith(".json"):
            text = (project["site"] / name).read_text()
            assert "NaN" not in text and "Infinity" not in text
            json.loads(text)


def test_the_command_line_exits_with_an_error_when_an_output_failed(project, monkeypatch, capsys):
    doc = temperature_doc()
    del doc["cells"]["70.3_20.0"]
    write(project["derived"] / "temperature_cells.json", doc)
    monkeypatch.setattr("sys.argv", ["export_site_extras.py", "--derived", str(project["derived"]), "--reference", str(project["reference"]),
                                     "--sources", str(project["sources"]), "--site-data", str(project["site"])])
    with pytest.raises(SystemExit) as stop:
        extras.main()
    assert stop.value.code == 1
    assert "70.3_20.0" in capsys.readouterr().err


# ---- the real files ----

REAL_INPUTS = [SITE_DATA / "cells.json", DERIVED / "moon_cards.json", DERIVED / "temperature_cells.json",
               DERIVED / "validation_extras.json", DERIVED / "sunpath_demo.json", DERIVED / "cloud_cells.json",
               REFERENCE / "known_analogs_check.json", SOURCES_MD]
real = pytest.mark.skipif(not all(p.exists() for p in REAL_INPUTS), reason="the pipeline files are not all there")


@pytest.fixture(scope="module")
def real_run(tmp_path_factory):
    out = tmp_path_factory.mktemp("extras")
    # a copy of the page's two files, so that a rewrite of site/data during the test cannot split the run
    site = tmp_path_factory.mktemp("site")
    shutil.copy(SITE_DATA / "cells.json", site / "cells.json")
    if (SITE_DATA / "meta.json").exists():
        shutil.copy(SITE_DATA / "meta.json", site / "meta.json")
    report = extras.export(DERIVED, REFERENCE, SOURCES_MD, site, out)
    return {"out": out, "site": site, "report": report, "ids": json.loads((site / "cells.json").read_text())["ids"]}


def _json(real_run, name):
    return json.loads((real_run["out"] / name).read_text())


@real
def test_real_run_writes_everything_under_one_and_a_half_megabytes(real_run):
    report = real_run["report"]
    assert report["failed"] == {} and report["left_out"] == {}
    assert sorted(report["written"]) == sorted(OUTPUTS)
    total = sum(p.stat().st_size for p in real_run["out"].iterdir())
    assert total < 1_500_000, total
    assert total == sum(report["written"].values())


@real
def test_real_temperature_files_line_up_with_the_pages_areas(real_run):
    ids = real_run["ids"]
    source = json.loads((DERIVED / "temperature_cells.json").read_text())["cells"]
    air = np.frombuffer((real_run["out"] / "temperature.bin").read_bytes(), dtype=np.int8)
    assert air.size == len(ids) * 12
    air = air.reshape(len(ids), 12)
    surface = np.frombuffer((real_run["out"] / "temperature_surface.bin").read_bytes(), dtype=np.int8).reshape(len(ids), 12)
    for row in list(range(0, len(ids), 397)) + [len(ids) - 1]:
        for field, table in (("t2m_c", air), ("ts_c", surface)):
            values = source[ids[row]][field]
            for month in range(12):
                if values is None or values[month] is None:
                    assert table[row, month] == -128
                else:
                    assert abs(int(table[row, month]) - values[month]) <= 0.5 + 1e-9
    known_months = sum(1 for i in ids for v in (source[i]["t2m_c"] or [None] * 12) if v is not None)
    assert int((air != -128).sum()) == known_months
    index = _json(real_run, "extras.json")
    assert index["areas"]["count"] == len(ids)
    assert len(index["temperature"]["grid_height_m"]) == len(ids)


@real
def test_real_moon_cards_say_what_the_source_says(real_run):
    source = json.loads((DERIVED / "moon_cards.json").read_text())
    out = _json(real_run, "moon.json")
    by_id = {c["id"]: c for c in source["cards"]}
    assert len(out["cards"]) == len(source["cards"]) == 4
    assert sum(same_numbers(card, by_id[card["id"]]) for card in out["cards"]) > 140
    meta_path = real_run["site"] / "meta.json"
    if meta_path.exists():
        assert [c["id"] for c in out["cards"]] == [t["id"] for t in json.loads(meta_path.read_text())["targets"]]
    for card in out["cards"]:
        assert card["official_name"] == by_id[card["id"]]["official_name"]
        assert card["picture"]["page"] == by_id[card["id"]]["picture"]["page"]
        assert card["picture"]["credit"] == by_id[card["id"]]["picture"]["credit"]
        assert card["earth_cannot_match"] == by_id[card["id"]]["earth_cannot_match"]
        assert "model-based" in card["diviner"]["label"]
        assert card["nasa_list"]["links"]


@real
def test_real_validation_file_says_what_the_source_says(real_run):
    source = json.loads((DERIVED / "validation_extras.json").read_text())
    out = _json(real_run, "validation.json")
    checked = sum(same_numbers(out[part], source[part])
                  for part in ("meta", "lower_latitude_sites", "latitude_against_full_method", "known_sites", "sensitivity"))
    assert checked > 2500
    assert out["headlines"] == source["headlines"]
    assert out["flags"]["terrain_step_is_a_census"] == source["latitude_against_full_method"]["with_a_horizon_is_a_census"]
    assert out["flags"]["horizon_coverage"] == source["latitude_against_full_method"]["horizon_coverage"]
    ids = real_run["ids"]
    for rows in out["known_sites"]["sites"].values():
        for row in rows:
            assert row["area"] is None or ids[row["area"]] == row["cell"]


@real
def test_real_station_check_says_what_the_snow_file_says(real_run):
    path = DERIVED / "snow_validation_many.json"
    out = _json(real_run, "validation.json")
    if not path.exists():
        assert out["snow_station_check"] is None
        return
    source = json.loads(path.read_text())
    check = out["snow_station_check"]
    assert check["overall"] == source["overall"]
    assert same_numbers({k: check[k] for k in ("overall", "periods", "calibration", "selection")}, source) > 80
    assert len(json.dumps(check)) < 10000          # the 139 stations' own rows stay in the pipeline's file (about 590 KB)


@real
def test_real_credit_lines_are_whole(real_run):
    text = SOURCES_MD.read_text()
    out = _json(real_run, "sources.json")
    assert _credits_joined(out) == _credit_region(text)
    assert len(out["credits"]) >= 14
    assert len(out["sources"]) >= 18 and [s["n"] for s in out["sources"]] == list(range(1, len(out["sources"]) + 1))
    for source in out["sources"]:
        assert source["name"] and source["provider"] and source["used_for"] and source["licence"]
        assert source["group"] in ("NASA", "partner agency", "other")
        if source["credit_ref"] is not None:
            assert source["credit"], source["n"]
    for credit in out["credits"]:
        assert credit["text"][-1] in ".)" or credit["text"].split()[-1].startswith("http"), credit["ref"]
    assert out["licence_line"].startswith("Code: Apache License 2.0.") and out["licence_line"].endswith("is implied.")
    assert "`" not in json.dumps(out["credits"]) and "**" not in json.dumps(out["sources"])
    assert len(out["nasa_data"]) >= 4 and all(item["link"] for item in out["nasa_data"])
    assert len(out["partner_data"]) >= 2 and all(item["link"] for item in out["partner_data"])
    assert out["notices"]["copernicus_dem"].startswith("produced using Copernicus WorldDEM-90")
    assert out["notices"]["copernicus_dem"].endswith("all rights reserved")
    assert out["problems"] == []


@real
def test_real_sun_paths_keep_rows_of_the_source(real_run):
    source = json.loads((DERIVED / "sunpath_demo.json").read_text())
    out = _json(real_run, "sunpath.json")
    lunar = [s for s in source["lunar_sites"] if s["id"] == "malapert"][0]
    place = [p for p in source["earth_places"] if p["id"] == "haughton"][0]
    assert out["moon"]["ceiling_deg"] == lunar["ceiling_deg"] and out["band_deg"] == place["band_deg"]
    assert out["earth"]["minutes_in_band"] == place["minutes_in_band"]
    assert out["earth"]["date"] == place["date"]
    rows = set(zip(lunar["path"]["hours_since_start"], lunar["path"]["azimuth_deg"], lunar["path"]["elevation_deg"]))
    kept = out["moon"]["path"]
    assert set(zip(kept["hours_since_start"], kept["azimuth_deg"], kept["elevation_deg"])) <= rows
    assert max(kept["elevation_deg"]) == max(lunar["path"]["elevation_deg"])
    gaps = np.diff(out["moon"]["marks"]["hours_since_start"])
    assert np.allclose(gaps, 24.0) and len(gaps) >= 27
    assert np.allclose(np.diff(out["earth"]["marks"]["solar_time_h"]), 1.0, atol=1e-3)
    assert out["earth"]["terrain_horizon"]["centre_deg"] == place["terrain_horizon"]["centre_deg"]
    for sentence in [s for c in out["cautions"] for s in c["sentences"]] + out["shows"]:
        assert words(sentence) <= 25, sentence
    if out["earth"]["area"] is not None:
        assert real_run["ids"][out["earth"]["area"]] == place["cell_id"]


@real
def test_real_places_and_the_little_known_corrections(real_run):
    source = json.loads((REFERENCE / "known_analogs_check.json").read_text())
    out = _json(real_run, "places.json")
    ids = real_run["ids"]
    assert [p["name"] for p in out["places"]] == [p["name"] for p in source["top_places"]]
    for place, original in zip(out["places"], source["top_places"]):
        assert place["analog_use_found"] == original["analog_use_found"]
        assert all(ids[a["index"]] == a["id"] for a in place["areas"])
        assert all(a["km_to_point"] <= 50.0 for a in place["areas"])
        for point, was in zip(place["points"], original["points"]):
            station = was.get("nearest_station") or was.get("nearest_comnap_facility")
            assert (point["station"] or {}).get("km") == (station or {}).get("km")
            assert (point["airfield"] or {}).get("km") == (was.get("nearest_airfield") or {}).get("km")
    names = " | ".join(entry["name"] for entry in out["not_little_known"]["because"])
    for expected in ("Nordaustlandet", "Vestfold Hills", "Schirmacher Oasis", "Tunnunik"):
        assert expected in names
    assert out["not_little_known"]["areas"] == sorted(set(out["not_little_known"]["areas"]))
    assert [ids[i] for i in out["not_little_known"]["areas"]] == out["not_little_known"]["ids"]
    assert len(out["not_little_known"]["areas"]) > 40


@real
def test_real_cloud_regions_agree_with_the_cloud_files_own_medians(real_run):
    source = json.loads((DERIVED / "cloud_cells.json").read_text())
    out = _json(real_run, "cloud_regions.json")
    assert sum(r["areas"] for r in out["north"]["regions"]) == out["north"]["areas"]
    assert sum(r["areas"] for r in out["south"]["regions"]) == out["south"]["areas"]
    assert out["north"]["areas"] + out["south"]["areas"] == len(real_run["ids"])
    told = source["meta"].get("counts", {}).get("median_pct_north_cells", {}).get("all_hours")
    if told and len(source["cells"]) == len(real_run["ids"]):
        assert out["north"]["all"]["median_pct"]["July"] == pytest.approx(told["july"], abs=0.05)
        assert out["north"]["all"]["median_pct"]["August"] == pytest.approx(told["august"], abs=0.05)
    for sentence in out["sentences"]:
        assert sentence is None or words(sentence) <= 25
    if out["daytime"] is not None:
        assert 0.0 <= out["daytime"]["north"]["July"]["share"] <= 1.0

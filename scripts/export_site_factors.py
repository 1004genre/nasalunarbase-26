# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Write the factor matrix and every new per-place factor for the page (site/data).

    uv run python scripts/build_factor_matrix.py    # optional: the exporter builds the matrix itself if it is missing
    uv run python scripts/export_site_factors.py

Writes, into site/data:
    factors.json      the matrix, definitions, units, sources, credit lines, what each figure is not, the rules of
                      thumb in words, the lunar region and Mars site figures, and the exact byte layout of the two files below
    factors.bin       the new factors of each Moon-part area, in the order of the ids of site/data/cells.json
    mars_factors.bin  the same for the Mars squares, in the order of site/data/mars.json squares.ids when that file exists,
                      else of data/derived/mars_cells.json

Byte files are column blocks: for each field, one value per place, little-endian, each block starting on a 4-byte
boundary. value = stored / scale. Every type has its own unknown value (u8 255, u16 65535, u32 4294967295); unknown is
never 0. A missing input file is skipped: its fields are left out and its factors read "not built".
Only numpy and the standard library; no network.
"""
from __future__ import annotations

import importlib.util
import json
import math
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DERIVED = ROOT / "data" / "derived"
SITE_DATA = ROOT / "site" / "data"
TYPES = {"u8": (np.dtype("<u1"), 255), "u16": (np.dtype("<u2"), 65535), "u32": (np.dtype("<u4"), 4294967295)}
BEYOND_U16 = 65534               # "none within the search reach" (a known answer, not unknown)
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
CAPTION = "Drawn by code from open data; the code was written with AI assistance."
NAV_SENTENCE = "These are parts of the problem of finding your way by sight; we give no single score."
MAX_WORDS = 25
KIND_TAGS = {"measured": "measured", "model": "model", "coarse map": "coarse map",
             "rough estimate by our rule": "rough estimate by our rule"}
# Preferred order of class words; words not listed follow in the order first met.
ORDER = {
    "landform": ["plain", "rolling ground", "hills", "mountains"],
    "three": ["low", "medium", "high", "fast", "slow", "dry", "moist", "wet", "unlikely", "possible", "likely"],
    "yesno": ["no", "yes"],
}


def load_matrix_builder():
    spec = importlib.util.spec_from_file_location("build_factor_matrix", ROOT / "scripts" / "build_factor_matrix.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read(path: Path):
    try:
        with open(path) as handle:
            return json.load(handle)
    except FileNotFoundError:
        return None


def cells(doc) -> dict:
    if not isinstance(doc, dict):
        return {}
    value = doc.get("cells")
    if isinstance(value, dict):
        return value
    if isinstance(value, list):
        return {c.get("id"): c for c in value}
    return {}


def g(*path):
    def get(record):
        for key in path:
            if not isinstance(record, dict):
                return None
            record = record.get(key)
        return record
    return get


def num(x):
    return x if isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) else None


def mean12(values, skip_months=None):
    """Mean of the known monthly values, leaving out the months named (1 = January); None if none known."""
    if not isinstance(values, list):
        return None
    keep = [num(v) for i, v in enumerate(values) if not (skip_months and (i + 1) in skip_months)]
    keep = [v for v in keep if v is not None]
    return sum(keep) / len(keep) if keep else None


def sum12(values):
    if not isinstance(values, list) or len(values) != 12 or any(num(v) is None for v in values):
        return None
    return float(sum(values))


def yesno(value):
    return None if value is None else ("yes" if value else "no")


def month_mask(months):
    if not isinstance(months, list) or not months:
        return None
    return sum(1 << (int(m) - 1) for m in months if isinstance(m, int) and 1 <= m <= 12)


def road_km(record):
    road = g("human", "nearest_main_road_or_railway")(record.get("steady") or {})
    if not isinstance(road, dict):
        return None
    if num(road.get("km")) is not None:
        return road["km"]
    if num(road.get("none_within_km")) is not None:
        return "beyond"
    return None


# ---- the fields ----
# (id, row, label, unit, type, scale, digits, kind, moon getter, mars getter, extra)
# A getter takes the merged record {file key: that file's record of the place}. kind "code" fields hold class words.

def F(fid, row, label, unit, typ, scale, digits, kind, moon, mars=None, **extra):
    return dict(id=fid, row=row, label=label, unit=unit, type=typ, scale=scale, digits=digits, kind=kind,
                moon=moon, mars=mars, **extra)


def env_mean(field):
    return lambda r: mean12(g("env", field)(r), g("env", "sunless_months")(r))


FIELDS = [
    # light and sky
    F("uv_index_year", "uv", "UV index, yearly mean of the 24-hour mean", "UV index", "u8", 50, 2, "coarse map",
      lambda r: mean12(g("env", "uv_index")(r)), g("m_env", "uv_index_year")),
    F("uv_index_brightest_hour_max", "uv", "UV index of the brightest hour, highest month", "UV index", "u8", 10, 1,
      "coarse map", None, g("m_env", "uv_index_brightest_hour_max")),
    F("sun_kwh_year", "sunlight", "Sunlight on level ground, yearly mean", "kWh per m2 per day", "u8", 20, 2, "coarse map",
      lambda r: mean12(g("env", "sun_kwh_m2_day")(r)), g("m_env", "sun_kwh_m2_day_year")),
    F("clear_days_year", "clear_days", "Clear-sky days in a typical year", "days a year", "u16", 10, 1, "coarse map",
      lambda r: sum12(g("env", "clear_days")(r)), g("m_env", "clear_days_year")),
    F("aod_year", "haze", "Haze (aerosol optical depth), mean of the sunlit months", "optical depth", "u8", 200, 2,
      "coarse map", env_mean("aod_550"), g("m_env", "aod_550_year")),
    # ground shape
    F("rough_90", "roughness", "Roughness at 90 m", "m", "u16", 100, 2, "measured", g("ground", "roughness_m", "90")),
    F("rough_270", "roughness", "Roughness at 270 m", "m", "u16", 100, 1, "measured", g("ground", "roughness_m", "270")),
    F("rough_810", "roughness", "Roughness at 810 m", "m", "u16", 100, 0, "measured", g("ground", "roughness_m", "810")),
    F("median_slope", "slope", "Median slope", "degrees", "u16", 100, 1, "measured", g("ground", "median_slope_deg"),
      g("m_ground", "median_slope_deg")),
    F("p90_slope", "slope", "Slope that 90 percent of the ground stays under", "degrees", "u16", 100, 1, "measured",
      g("ground", "p90_slope_deg"), g("m_ground", "p90_slope_deg")),
    F("relief", "landform", "Relief (95th minus 5th percentile height)", "m", "u16", 1, 0, "measured",
      g("ground", "relief_m"), g("m_ground", "relief_m")),
    F("landform", "landform", "Landform", "class", "u8", None, None, "rough estimate by our rule", g("ground", "landform"),
      g("m_ground", "relief_class"), order="landform"),
    F("shadow_basis", "visual_navigation", "Shadow share is a share of", "words", "u8", None, None, "measured",
      g("ground", "shadow", "basis")),
    # ground material
    F("albedo_year", "albedo", "Albedo, mean of the sunlit months", "fraction 0 to 1", "u8", 250, 2, "coarse map",
      g("pex", "albedo_year"), g("m_pex", "albedo_year")),
    F("rock_class", "volcanic_rock", "Main rock of the half-degree box", "class", "u8", None, None, "coarse map",
      g("rock", "rock", "class"), g("m_rock", "rock", "class")),
    F("rock_box", "volcanic_rock", "Rock class taken from", "words", "u8", None, None, "coarse map",
      lambda r: {"own": "the box itself", "neighbour": "the boxes around it"}.get(g("rock", "rock", "box")(r)),
      lambda r: {"own": "the box itself", "neighbour": "the boxes around it"}.get(g("m_rock", "rock", "box")(r))),
    F("volcanic", "volcanic_rock", "Volcanic rock", "yes or no", "u8", None, None, "coarse map",
      lambda r: yesno(g("rock", "rock", "volcanic")(r)), lambda r: yesno(g("m_rock", "rock", "volcanic")(r)), order="yesno"),
    F("basic_volcanic", "volcanic_rock", "Basalt-like (basic volcanic) rock", "yes or no", "u8", None, None, "coarse map",
      lambda r: yesno(g("rock", "rock", "basic_volcanic")(r)), lambda r: yesno(g("m_rock", "rock", "basic_volcanic")(r)),
      order="yesno"),
    F("loose_sediment", "volcanic_rock", "Loose sediment", "yes or no", "u8", None, None, "coarse map",
      lambda r: yesno(g("rock", "rock", "loose_sediment")(r)), lambda r: yesno(g("m_rock", "rock", "loose_sediment")(r)),
      order="yesno"),
    F("mineral_family", "mineralogy", "Mineral family", "class", "u8", None, None, "rough estimate by our rule",
      g("est", "mineral_family", "estimate"), g("m_est", "mineral_family", "estimate")),
    F("heat_response", "thermal_inertia", "How fast the ground heats and cools", "class", "u8", None, None,
      "rough estimate by our rule", g("est", "heat_response", "estimate"), g("m_est", "heat_response", "estimate"),
      order="three"),
    F("heat_index", "thermal_inertia", "Heat index, (1 - albedo) over the daily swing", "per degree C", "u16", 10000, 3,
      "rough estimate by our rule", g("est", "heat_response", "figures", "index_per_c"),
      g("m_est", "heat_response", "figures", "index_per_c")),
    F("ilmenite", "resources", "Ilmenite-bearing rock", "class", "u8", None, None, "rough estimate by our rule",
      g("est", "ilmenite", "estimate"), g("m_est", "ilmenite", "estimate"), order="three"),
    F("rockiness", "rock_abundance", "Rockiness", "class", "u8", None, None, "rough estimate by our rule",
      g("est", "rockiness", "estimate"), g("m_est", "rockiness", "estimate"), order="three"),
    F("sand_dust", "haze", "Blowing sand and dust", "class", "u8", None, None, "rough estimate by our rule",
      g("est", "sand_dust", "estimate"), g("m_est", "sand_dust", "estimate"), order="three"),
    # climate
    F("t2m_range_year", "temp_swing", "Daily air temperature swing, yearly mean", "degrees C", "u16", 100, 1, "model",
      g("pex", "t2m_range_c_year"), g("m_pex", "t2m_range_c_year")),
    F("wind_year", "wind", "Wind at 10 m, yearly mean", "m/s", "u16", 100, 1, "model", g("pex", "wind_10m_ms_year"),
      g("m_pex", "wind_10m_ms_year")),
    F("soil_wetness_year", "soil_moisture", "Top-soil wetness, yearly mean", "fraction 0 to 1", "u8", 250, 2, "model",
      g("pex", "soil_wetness_top_year"), g("m_pex", "soil_wetness_top_year")),
    F("soil_ice_flag", "soil_moisture", "Model grid point is ice (wetness 1 all year)", "yes or no", "u8", None, None,
      "model", lambda r: yesno(g("pex", "soil_wetness_ice_flag")(r)), lambda r: yesno(g("m_pex", "soil_wetness_ice_flag")(r)),
      order="yesno"),
    F("snow_free_months", "soil_moisture", "Months above 0 C used by our rules", "months", "u16", "mask", None,
      "rough estimate by our rule", lambda r: month_mask(g("est", "snow_free_months")(r)),
      lambda r: month_mask(g("m_est", "snow_free_months")(r))),
    # below the ground
    F("permafrost_prob", "permafrost", "Permafrost probability, mean over the area", "probability 0 to 1", "u8", 250, 2,
      "coarse map", g("rock", "permafrost", "prob_mean"), g("m_rock", "permafrost", "prob_mean")),
    F("permafrost_zone", "permafrost", "Permafrost zone", "class", "u8", None, None, "coarse map",
      g("rock", "permafrost", "zone"), g("m_rock", "permafrost", "zone")),
    F("frozen_depth", "ice_depth", "Depth to frozen ground", "class", "u8", None, None, "rough estimate by our rule",
      g("est", "frozen_ground_depth", "estimate"), g("m_est", "frozen_ground_depth", "estimate")),
    F("topsoil_water", "hydrogen", "Water in the top soil", "class", "u8", None, None, "rough estimate by our rule",
      g("est", "topsoil_water", "estimate"), g("m_est", "topsoil_water", "estimate"), order="three"),
    F("ground_ice", "hydrogen", "Ground ice", "class", "u8", None, None, "rough estimate by our rule",
      g("est", "topsoil_water", "ground_ice"), g("m_est", "topsoil_water", "ground_ice"), order="three"),
    # hazards
    F("quakes_count", "large_quakes", "Earthquakes of magnitude 5+ within 200 km, 1990-2025", "count", "u16", 1, 0,
      "measured", g("hazards", "quakes_m5_200km", "count"), g("m_hazards", "quakes_m5_200km", "count")),
    F("quakes_largest", "large_quakes", "Largest of them", "magnitude", "u8", 20, 1, "measured",
      g("hazards", "quakes_m5_200km", "largest_mag"), g("m_hazards", "quakes_m5_200km", "largest_mag")),
    F("quakes_nearest_km", "large_quakes", "Nearest of them", "km", "u16", 10, 0, "measured",
      g("hazards", "quakes_m5_200km", "nearest_km"), g("m_hazards", "quakes_m5_200km", "nearest_km")),
    F("tremor_verdict", "small_tremors", "Small tremors: verdict for instruments", "class", "u8", None, None, "measured",
      g("tremors", "verdict"), g("m_tremors", "verdict")),
    F("tremor_status", "small_tremors", "Can the catalogue see small tremors here", "words", "u8", None, None, "measured",
      g("tremors", "status"), g("m_tremors", "status")),
    F("tremors_per_year_100", "small_tremors", "Small events a year within 100 km", "events a year", "u16", 10, 1,
      "measured", g("tremors", "small_per_year_100km"), g("m_tremors", "small_per_year_100km")),
    F("tremors_per_year_50", "small_tremors", "Small events a year within 50 km", "events a year", "u16", 10, 1,
      "measured", g("tremors", "small_per_year_50km"), g("m_tremors", "small_per_year_50km")),
    F("tremor_years_100", "small_tremors", "Years with events within 100 km, of 16", "years", "u8", 1, 0, "measured",
      g("tremors", "years_with_events_100km"), g("m_tremors", "years_with_events_100km")),
    F("tremor_median_mag", "small_tremors", "Median magnitude within 100 km", "magnitude", "u8", 20, 1, "measured",
      g("tremors", "median_magnitude_100km"), g("m_tremors", "median_magnitude_100km")),
    F("tremor_floor", "small_tremors", "Smallest magnitude the catalogue sees here (10th percentile)", "magnitude", "u8", 20, 1,
      "measured", g("tremors", "detection_floor"), g("m_tremors", "detection_floor")),
    F("tremor_nearest_km", "small_tremors", "Nearest small event", "km", "u16", 10, 0, "measured",
      g("tremors", "nearest_small_event_km"), g("m_tremors", "nearest_small_event_km")),
    F("tremor_our_estimate", "small_tremors", "Our rough estimate where the catalogue is blind", "class", "u8", None, None,
      "rough estimate by our rule", g("steady", "small_tremors", "our_estimate"), g("m_steady", "small_tremors", "our_estimate")),
    F("volcanic_class", "active_volcanism", "Volcanic effects", "class", "u8", None, None, "rough estimate by our rule",
      g("steady", "volcanic", "class"), g("m_steady", "volcanic", "class")),
    F("young_volcanic_ground", "active_volcanism", "Young volcanic ground", "yes or no", "u8", None, None,
      "rough estimate by our rule", lambda r: yesno(g("steady", "volcanic", "young_volcanic_ground")(r)),
      lambda r: yesno(g("m_steady", "volcanic", "young_volcanic_ground")(r)), order="yesno"),
    F("volcano_ref", "active_volcanism", "Nearest Holocene volcano", "name", "u16", "ref:volcanoes", None, "measured",
      g("hazards", "volcano"), g("m_hazards", "volcano")),
    F("volcano_km", "active_volcanism", "Distance to it", "km", "u16", 1, 0, "measured", g("hazards", "volcano", "km"),
      g("m_hazards", "volcano", "km")),
    # people and access
    F("airfield_ref", "airfield", "Nearest airfield", "name", "u16", "ref:places", None, "measured",
      g("access", "nearest"), g("m_steady", "human", "nearest_airfield")),
    F("airfield_km", "airfield", "Distance to it", "km", "u16", 10, 0, "measured", g("access", "nearest", "km"),
      g("m_steady", "human", "nearest_airfield", "km")),
    F("airfield_sched_km", "airfield", "Nearest airfield with scheduled flights", "km", "u16", 10, 0, "measured",
      g("access", "nearest_scheduled", "km"), g("m_steady", "human", "nearest_airfield_with_scheduled_flights", "km")),
    F("human_class", "human_footprint", "Human disturbance", "class", "u8", None, None, "rough estimate by our rule",
      g("steady", "human", "class"), g("m_steady", "human", "class")),
    F("pop_100km", "human_footprint", "People in listed settlements within 100 km", "people", "u32", 1, 0, "measured",
      g("hazards", "people", "population_within_100km"), g("m_hazards", "people", "population_within_100km")),
    F("road_km", "human_footprint", "Nearest main road or railway", "km", "u16", 10, 0, "measured", road_km,
      lambda r: road_km({"steady": r.get("m_steady")}), beyond="none within 1,000 km"),
    F("settlement_ref", "remoteness", "Nearest listed settlement", "name", "u16", "ref:places", None, "measured",
      g("hazards", "people", "nearest"), g("m_hazards", "people", "nearest")),
    F("settlement_km", "remoteness", "Distance to it", "km", "u16", 10, 0, "measured",
      g("hazards", "people", "nearest", "km"), g("m_hazards", "people", "nearest", "km")),
    F("city_ref", "remoteness", "Nearest city of 50,000 or more", "name", "u16", "ref:places", None, "measured",
      g("hazards", "people", "nearest_city_50k"), g("m_hazards", "people", "nearest_city_50k")),
    F("city_km", "remoteness", "Distance to it", "km", "u16", 1, 0, "measured",
      g("hazards", "people", "nearest_city_50k", "km"), g("m_hazards", "people", "nearest_city_50k", "km")),
    F("help_within_reach", "remoteness", "Help within reach", "yes or no", "u8", None, None, "rough estimate by our rule",
      lambda r: yesno(g("steady", "human", "help_within_reach")(r)),
      lambda r: yesno(g("m_steady", "human", "help_within_reach")(r)), order="yesno"),
    F("solar_class", "power", "Solar panels", "class", "u8", None, None, "rough estimate by our rule",
      g("power", "solar", "class"), g("m_power", "solar", "class")),
    F("wind_class", "power", "Wind power", "class", "u8", None, None, "rough estimate by our rule",
      g("power", "wind", "class"), g("m_power", "wind", "class")),
    F("geothermal_class", "power", "Ground heat", "class", "u8", None, None, "rough estimate by our rule",
      g("power", "geothermal", "class"), g("m_power", "geothermal", "class")),
    F("land_class", "land_status", "Land status at the centre", "class", "u8", None, None, "rough estimate by our rule",
      g("land", "class"), g("m_land", "class")),
    F("land_decided", "land_status", "How the class was decided", "words", "u8", None, None, "rough estimate by our rule",
      g("land", "decided"), g("m_land", "decided")),
    F("land_territory", "land_status", "Territory that holds the centre", "name", "u8", None, None, "coarse map",
      g("land", "territory_name"), g("m_land", "territory_name")),
    F("land_rule", "land_status", "What the territory rule says about owners", "words", "u8", None, None,
      "rough estimate by our rule",
      lambda r: LAND_OWNER.get(g("land", "territory")(r)), lambda r: LAND_OWNER.get(g("m_land", "territory")(r))),
    F("land_protected", "land_status", "Protected area at the centre (name, type)", "name", "u16", None, None, "measured",
      lambda r: land_protected(r.get("land")), lambda r: land_protected(r.get("m_land"))),
    F("land_owner", "land_status", "Owner or manager at the centre, from a map", "name", "u16", None, None, "measured",
      lambda r: land_owner(r.get("land")), lambda r: land_owner(r.get("m_land"))),
    F("land_entry", "land_status", "Entry and permits, from the map", "words", "u16", None, None, "measured",
      g("land", "entry"), g("m_land", "entry")),
    F("land_ask", "land_status", "Whom to ask", "words", "u8", None, None, "rough estimate by our rule",
      lambda r: LAND_ASK.get(g("land", "ask_key")(r)), lambda r: LAND_ASK.get(g("m_land", "ask_key")(r))),
    F("land_maps", "land_status", "Maps tested at the centre", "names", "u8", None, None, "measured",
      lambda r: land_maps(r.get("land")), lambda r: land_maps(r.get("m_land"))),
]
LAND_ASK = {}   # filled in main() from the land status file: the "whom to ask" sentences by key
LAND_OWNER = {}  # the same: what each territory rule says about owners, by territory key
LAND_MAPS = {}   # the same: the short name of each map, by map id


def land_protected(record):
    """Every protected area that holds the centre, with its type, as the maps give them; 'none' only where a
    protected-areas map covers the territory."""
    if not isinstance(record, dict):
        return None
    areas = record.get("protected_areas") or ([record["protected_area"]] if record.get("protected_area") else [])
    names = [f"{a['name']} ({a['type']})" if a.get("type") else a["name"] for a in areas if isinstance(a, dict) and a.get("name")]
    if names:
        return "; ".join(names)
    return "none in the maps we checked" if record.get("protected_checked") else None


def land_owner(record):
    if not isinstance(record, dict):
        return None
    owner = record.get("owner_from_map")
    if isinstance(owner, dict) and owner.get("text"):
        return owner["text"]
    return None


def land_maps(record):
    if not isinstance(record, dict) or not record.get("maps_tested"):
        return None
    return "; ".join(LAND_MAPS.get(m, m) for m in record["maps_tested"])
# Fields with one value per lunar region (Moon part only).
TARGET_FIELDS = [
    ("shadow_share", "visual_navigation", "Share of the low-Sun hours in terrain shadow", "share 0 to 1", "u8", 250, 2,
     "measured", ("ground", "shadow", "share")),
    ("low_sun_hours", "visual_navigation", "Low-Sun hours that share is of", "hours a year", "u16", 10, 0, "measured",
     ("ground", "shadow", "low_sun_hours")),
    ("rough_vs_region_90", "visual_navigation", "Roughness at 90 m over the lunar region's", "ratio", "u16", 1000, 2,
     "measured", ("ground", "roughness_vs_region", None, "90")),
]
MOON_FILES = {"env": "environment_cells.json", "tremors": "tremors_cells.json", "pex": "power_extra_cells.json",
              "ground": "ground_cells.json", "hazards": "hazards_people_cells.json", "rock": "rock_frozen_cells.json",
              "est": "estimates_cells.json", "steady": "steady_effects_cells.json", "power": "power_cells.json",
              "access": "access_cells.json", "land": "land_status_cells.json"}
MARS_FILES = {"m_env": "mars_environment.json", "m_tremors": "mars_tremors.json", "m_pex": "mars_power_extra.json",
              "m_ground": "mars_ground.json", "m_hazards": "mars_hazards_people.json", "m_rock": "mars_rock_frozen.json",
              "m_est": "mars_estimates.json", "m_steady": "mars_steady_effects.json", "m_power": "mars_power.json",
              "m_land": "mars_land_status.json"}


class Refs:
    """Name tables for the ref: fields (volcanoes; settlements, cities and airfields)."""

    def __init__(self):
        self.tables = {"volcanoes": [], "places": []}
        self.index = {"volcanoes": {}, "places": {}}

    def ref(self, table, record):
        if not isinstance(record, dict) or not record.get("name"):
            return None
        if table == "volcanoes":
            entry = {"name": record["name"], "country": record.get("country"),
                     "last_eruption_year": record.get("last_eruption_year")}
        else:
            entry = {"name": record["name"], "country": record.get("country"), "population": record.get("population")}
            if record.get("ident"):
                entry["ident"] = record["ident"]
        key = json.dumps(entry, sort_keys=True)
        if key not in self.index[table]:
            self.index[table][key] = len(self.tables[table])
            self.tables[table].append(entry)
        return self.index[table][key]


def pack(ids, merged, specs, refs, part):
    """Column blocks for the places in ids. Returns (bytes, layout list, counts)."""
    blocks, layout, offset = [], [], 0
    n = len(ids)
    for spec in specs:
        getter = spec["getter"]
        if getter is None:
            continue
        dtype, unknown = TYPES[spec["type"]]
        values = [getter(merged.get(pid) or {}) for pid in ids]
        entry = {k: spec[k] for k in ("id", "row", "label", "unit", "type", "kind") if k in spec}
        if spec.get("target"):
            entry["base"], entry["target"] = spec["base"], spec["target"]
        entry["unknown"] = unknown
        entry["size"] = dtype.itemsize
        data = np.full(n, unknown, dtype=dtype)
        clipped = 0
        scale = spec["scale"]
        if scale is None:                                  # class words
            words = []
            for v in values:
                if isinstance(v, str) and v not in words:
                    words.append(v)
            preferred = ORDER.get(spec.get("order"), [])
            first = {w: i for i, w in enumerate(words)}
            words = sorted(words, key=lambda w: (preferred.index(w) if w in preferred else len(preferred), first[w]))
            lookup = {w: i for i, w in enumerate(words)}
            for i, v in enumerate(values):
                if isinstance(v, str):
                    data[i] = lookup[v]
            entry["codes"] = words
        elif isinstance(scale, str) and scale.startswith("ref:"):
            table = scale[4:]
            for i, v in enumerate(values):
                r = refs.ref(table, v)
                if r is not None:
                    data[i] = r
            entry["ref"] = table
        elif scale == "mask":
            for i, v in enumerate(values):
                if isinstance(v, int):
                    data[i] = v
            entry["mask"] = MONTHS
        else:
            top = unknown - 2 if spec.get("beyond") else unknown - 1
            for i, v in enumerate(values):
                if v == "beyond":
                    data[i] = BEYOND_U16
                    continue
                v = num(v)
                if v is None:
                    continue
                stored = int(round(v * scale))
                if stored < 0:
                    stored, clipped = 0, clipped + 1
                elif stored > top:
                    stored, clipped = top, clipped + 1
                data[i] = stored
            entry["scale"] = scale
            entry["digits"] = spec["digits"]
            if spec.get("beyond"):
                entry["beyond"] = {"stored": BEYOND_U16, "words": spec["beyond"]}
            if clipped:
                entry["clipped_to_range"] = clipped
        pad = (-offset) % 4
        if pad:
            blocks.append(b"\0" * pad)
            offset += pad
        raw = data.tobytes()
        entry["offset"] = offset
        entry["bytes"] = len(raw)
        entry["known"] = int((data != unknown).sum())
        blocks.append(raw)
        offset += len(raw)
        layout.append(entry)
    return b"".join(blocks), layout


def specs_for(part, targets):
    out = []
    for f in FIELDS:
        getter = f["moon"] if part == "moon" else f["mars"]
        if getter is not None:
            out.append(dict(f, getter=getter))
    if part == "moon":
        for base, row, label, unit, typ, scale, digits, kind, path in TARGET_FIELDS:
            for t in targets:
                steps = [t if p is None else p for p in path]
                if None not in path:
                    steps = list(path) + [t]
                out.append(dict(id=f"{base}@{t}", base=base, target=t, row=row, label=label, unit=unit, type=typ,
                                scale=scale, digits=digits, kind=kind, getter=g(*steps)))
    return out


def fit(text):
    """The sentences of a stored text with at most 25 words, cut at semicolons first (as the page's fit())."""
    if not isinstance(text, str):
        return None
    keep = []
    for sentence in re.split(r"(?<=[.!?])\s+", text.strip()):
        parts = [sentence] if len(sentence.split()) <= MAX_WORDS else [p.strip() for p in sentence.split(";")]
        for p in parts:
            if p and len(p.split()) <= MAX_WORDS:
                keep.append(p if p.endswith((".", "!", "?")) else p + ".")
    return " ".join(keep) or None


def planet_figures(matrix_rows, pf, gm, mc, mars_ground, mars_sites, env_meta):
    """The lunar region and Mars site figures, keyed by region or site id, then by matrix row id."""
    moon, mars = {}, {}
    factors = {f.get("id"): f for f in (pf or {}).get("factors", [])}
    pf_rows = {"thermal_inertia": "thermal_inertia", "rock_abundance": "rock_abundance", "hydrogen": "hydrogen",
               "ice_depth": "ice_depth", "surface_activity": "surface_activity", "large_quakes": "quakes",
               "small_tremors": "quakes", "albedo": "albedo", "temp_swing": "daily_temperature_swing",
               "resources": "hydrogen"}

    def put(store, body_id, row, fig):
        store.setdefault(body_id, {}).setdefault(row, []).append(fig)

    def unit_for(unit, body):
        """'Moon: ppm H; Mars: wt %' -> the part for this body."""
        if isinstance(unit, str) and "Moon:" in unit and "Mars:" in unit:
            for part in unit.split(";"):
                if part.strip().lower().startswith(body + ":"):
                    return part.split(":", 1)[1].strip()
        return unit

    for row, fid in pf_rows.items():
        f = factors.get(fid)
        if not f:
            continue
        for body, store in (("moon", moon), ("mars", mars)):
            for body_id, e in (f.get(body) or {}).items():
                value = e.get("value")
                put(store, body_id, row, {"label": f.get("name"), "value": value if not isinstance(value, list) else None,
                                          "range": value if isinstance(value, list) else None,
                                          "text": e.get("value_text"), "unit": unit_for(f.get("unit"), body),
                                          "kind": e.get("kind"), "note": fit(e.get("note")), "source": e.get("source")})
    for card in (mc or {}).get("cards", []):
        rid = card.get("id")
        sc = card.get("sun_ceiling") or {}
        put(moon, rid, "sun_low_hours", {"label": "Sun ceiling: the highest the Sun climbs", "value": sc.get("deg"),
                                         "unit": "degrees", "digits": 2, "kind": "computed from latitude",
                                         "note": "The same band of Sun heights is counted at every Earth area."})
        if num(card.get("shadow_of_1m_object_at_ceiling_m")) is not None:
            put(moon, rid, "sun_low_hours", {"label": "Shadow of a 1 m object at that height",
                                             "value": card["shadow_of_1m_object_at_ceiling_m"], "unit": "m", "digits": 1,
                                             "kind": "computed"})
        lit = (card.get("lit") or {}).get("mean_share")
        if num(lit) is not None:
            put(moon, rid, "sunlight", {"label": "Share of all time a typical point is lit", "value": lit,
                                        "unit": "share 0 to 1", "digits": 2, "kind": (card.get("lit") or {}).get("kind")})
            put(moon, rid, "visual_navigation", {"label": "Share of all time a typical point is in shadow",
                                                 "value": round(1 - lit, 4), "unit": "share 0 to 1", "digits": 2,
                                                 "kind": "measured terrain, modelled Sun",
                                                 "note": "One minus the mean lit share: all time, not only the low-Sun spells."})
        div = card.get("diviner") or {}
        for key, label in (("annual_mean_temp_2cm_C", "Yearly mean 2 cm down"),
                           ("annual_max_temp_surface_C", "Yearly highest at the surface")):
            v = (div.get(key) or {}).get("mean")
            if num(v) is not None:
                put(moon, rid, "temperature", {"label": label, "value": v, "unit": "degrees C", "digits": 0,
                                               "kind": "model (Diviner)"})
        ice = div.get("ice") or {}
        if num(ice.get("stable_within_1m_share")) is not None:
            put(moon, rid, "ice_depth", {"label": "Share of ground with ice stable within 1 m",
                                         "value": ice["stable_within_1m_share"], "unit": "share 0 to 1", "digits": 2,
                                         "kind": "model (Diviner)"})
        for item in card.get("earth_cannot_match") or []:
            if item.get("what") == "vacuum":
                put(moon, rid, "haze", {"label": "Air", "value": None, "text": fit(item.get("moon")), "unit": None,
                                        "kind": "published figure"})
    for rid, reg in ((gm or {}).get("regions") or {}).items():
        for base in ("5", "15", "45"):
            v = (reg.get("roughness_m_fine") or {}).get(base)
            if num(v) is not None:
                put(moon, rid, "roughness", {"label": f"Roughness at {base} m", "value": v, "unit": "m", "digits": 2,
                                             "kind": "measured", "base": base})
        for base in ("90", "270", "810"):
            v = (reg.get("roughness_m") or {}).get(base)
            if num(v) is not None:
                put(moon, rid, "roughness", {"label": f"Roughness at {base} m", "value": v, "unit": "m", "digits": 2,
                                             "kind": "measured", "base": base})
        for key, label, unit, digits in (("median_slope_deg", "Median slope", "degrees", 1),
                                         ("p90_slope_deg", "Slope that 90 percent of the ground stays under", "degrees", 1)):
            if num(reg.get(key)) is not None:
                put(moon, rid, "slope", {"label": label, "value": reg[key], "unit": unit, "digits": digits,
                                         "kind": "measured", "field": {"median_slope_deg": "median_slope",
                                                                       "p90_slope_deg": "p90_slope"}[key]})
        if num(reg.get("relief_m")) is not None:
            put(moon, rid, "landform", {"label": "Relief of the whole model", "value": reg["relief_m"], "unit": "m",
                                        "digits": 0, "kind": "measured", "field": "relief"})
        if reg.get("landform_whole_region"):
            put(moon, rid, "landform", {"label": "Landform", "value": None, "text": reg["landform_whole_region"],
                                        "kind": "rough estimate by our rule", "field": "landform"})
    for sid, site in ((mars_ground or {}).get("sites") or {}).items():
        for key, label, unit, digits in (("median_slope_deg", "Median slope", "degrees", 1),
                                         ("p90_slope_deg", "Slope that 90 percent of the ground stays under", "degrees", 1),
                                         ("relief_m", "Relief", "m", 0)):
            if num(site.get(key)) is not None:
                put(mars, sid, "slope" if key != "relief_m" else "landform",
                    {"label": label, "value": site[key], "unit": unit, "digits": digits, "kind": "measured"})
        if site.get("relief_class"):
            put(mars, sid, "landform", {"label": "Relief class", "value": None, "text": site["relief_class"],
                                        "kind": "rough estimate by our rule"})
    return moon, mars


def rules_in_words(docs):
    """Every rule of thumb in words, from the files that hold one."""
    out = []
    est = (docs.get("est") or {}).get("meta") or {}
    for rule in est.get("rules") or []:
        out.append({"file": "estimates_cells.json", "name": rule.get("name"), "stands_in_for": rule.get("stands_in_for"),
                    "words": rule.get("rule"), "note": rule.get("note")})
    steady = (docs.get("steady") or {}).get("meta") or {}
    for words in steady.get("rules_in_plain_words") or []:
        out.append({"file": "steady_effects_cells.json", "name": None, "words": words})
    trem = (docs.get("tremors") or {}).get("meta") or {}
    rot = trem.get("rule_of_thumb") or {}
    for key in ("words", "status_words"):
        if isinstance(rot.get(key), str):
            out.append({"file": "tremors_cells.json", "name": "small tremors" if key == "words" else "can the catalogue see",
                        "words": rot[key]})
    power = (docs.get("power") or {}).get("meta") or {}
    rw = power.get("rules_in_words")
    for words in (rw if isinstance(rw, list) else [rw] if isinstance(rw, str) else []):
        out.append({"file": "power_cells.json", "name": "power", "words": words if isinstance(words, str) else json.dumps(words)})
    ground = (docs.get("ground") or {}).get("meta") or {}
    if ground.get("landform_thresholds") is not None:
        out.append({"file": "ground_cells.json", "name": "landform", "words": json.dumps(ground.get("landform_table"))
                    if not isinstance(ground.get("landform_table"), str) else ground["landform_table"]})
    rock = (docs.get("rock") or {}).get("meta") or {}
    if rock.get("permafrost_zone_limits") is not None:
        z = rock["permafrost_zone_limits"]
        out.append({"file": "rock_frozen_cells.json", "name": "permafrost zones",
                    "words": z if isinstance(z, str) else json.dumps(z)})
    for r in out:
        r["words_on_page"] = fit(r["words"]) if isinstance(r.get("words"), str) else None
    return out


def credits(matrix_meta, sources_doc):
    lines = []
    for file, records in (matrix_meta.get("credits_and_licences_by_file") or {}).items():
        for rec in records:
            lines.append({"file": file, "name": rec.get("name"), "licence": rec.get("licence"), "credit": rec.get("credit")})
    return {"by_file": lines, "page_credits": (sources_doc or {}).get("credits"),
            "licence_line": (sources_doc or {}).get("licence_line")}


def long_sentences(value, path=""):
    """My own texts with a sentence over 25 words (printed as a warning, nothing stops)."""
    found = []
    if isinstance(value, str):
        for s in re.split(r"(?<=[.!?])\s+", value):
            if len(s.split()) > MAX_WORDS:
                found.append((path, s))
    return found


FILE_NAME = re.compile(r"[\w/\-]+\.(?:json|py|bin|npz|md|txt)\b")
# Sentences the bracket rule below cannot mend, said again without the file name.
PLAIN_WORDS = {
    "The parts' own sources (Sun path, horizons, GLO-90, NASA POWER aerosol); ground_cells.json for the shadow share.":
        "The parts' own sources (Sun path, horizons, GLO-90, NASA POWER aerosol).",
    "ESA WorldCover 10 m 2021 (north) and the SCAR rock outcrop layer (south), in grazing_cells.json.":
        "ESA WorldCover 10 m 2021 (north) and the SCAR rock outcrop layer (south).",
    "grazing_cells.json, terrain and ground figures and GLiM (estimates_cells.json rockiness).":
        "The bare-ground share, the terrain and ground figures and the GLiM rock map.",
}


def plain_source(text):
    """A source sentence for a reader of the page: our own file names taken out, the data set's name kept."""
    if not isinstance(text, str) or not FILE_NAME.search(text):
        return text
    if text in PLAIN_WORDS:
        return PLAIN_WORDS[text]

    def bracket(match):
        kept = [part.strip() for part in re.split(r"[,;]", match.group(1)) if not FILE_NAME.search(part)]
        return f" ({', '.join(kept)})" if kept else ""

    text = re.sub(r"\s*\(([^()]*)\)", lambda m: bracket(m) if FILE_NAME.search(m.group(1)) else m.group(0), text)
    # A whole sentence that only points at one of our files says nothing to a reader: drop it.
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", text) if not FILE_NAME.search(s)]
    text = " ".join(sentences)
    return re.sub(r"\s+([,;.])", r"\1", re.sub(r"\s{2,}", " ", text)).strip()


def plain_page_words(doc):
    """Take our own file names out of every sentence the factor table shows."""
    for row in doc.get("matrix") or []:
        for key in ("earth_figure_from", "moon_figure_from", "mars_figure_from", "status_reason"):
            row[key] = plain_source(row.get(key)) or row.get(key)
    for body in ("lunar_regions", "mars_sites"):
        for figures in (doc.get(body) or {}).values():
            for group in figures.values():
                for fig in group if isinstance(group, list) else [group]:
                    if isinstance(fig, dict) and fig.get("note"):
                        fig["note"] = plain_source(fig["note"]) or None
    return doc


def write(path: Path, data: bytes) -> int:
    side = path.with_name(path.name + ".part")
    side.write_bytes(data)
    os.replace(side, path)
    return len(data)


def main() -> None:
    builder = load_matrix_builder()
    matrix = read(DERIVED / "factor_matrix.json")
    if matrix is None:
        print("data/derived/factor_matrix.json is missing: building it now")
        matrix = builder.build()
        builder.write_json(DERIVED / "factor_matrix.json", matrix)
    cells_doc = read(SITE_DATA / "cells.json")
    meta_doc = read(SITE_DATA / "meta.json") or {}
    targets = [t["id"] for t in meta_doc.get("targets", [])] or ["connecting-ridge", "malapert", "mons-mouton", "nobile-rim-2"]
    docs = {k: read(DERIVED / v) for k, v in {**MOON_FILES, **MARS_FILES}.items()}
    missing = sorted(v for k, v in {**MOON_FILES, **MARS_FILES}.items() if docs[k] is None)
    land_meta = (docs.get("land") or {}).get("meta") or {}
    LAND_ASK.update(land_meta.get("ask") or {})
    LAND_OWNER.update(land_meta.get("owner_words") or {})
    LAND_MAPS.update({m["id"]: m["short"] for m in land_meta.get("maps") or [] if m.get("id")})
    refs = Refs()
    out = {}

    # Moon part
    moon_layout = None
    if cells_doc and cells_doc.get("ids"):
        ids = cells_doc["ids"]
        merged = {pid: {} for pid in ids}
        for key in MOON_FILES:
            for pid, rec in cells(docs[key]).items():
                if pid in merged:
                    merged[pid][key] = rec
        specs = [s for s in specs_for("moon", targets)]
        data, layout = pack(ids, merged, specs, refs, "moon")
        size = write(SITE_DATA / "factors.bin", data)
        moon_layout = {"file": "factors.bin", "count": len(ids), "bytes": size,
                       "order": "the order of ids in site/data/cells.json",
                       "byte_order": "little-endian", "block_alignment": 4,
                       "how_to_read": "For a field, value of place i = stored at offset + i * size of its type, divided by scale. "
                                      "codes: the stored number indexes the word list. ref: it indexes the named table. "
                                      "mask: bit m-1 set means month m. The field's unknown value means unknown, never 0.",
                       "fields": layout}
        out["factors.bin"] = size
    else:
        print("site/data/cells.json is missing: factors.bin not written")

    # Mars part
    mars_doc = read(SITE_DATA / "mars.json")
    mars_ids, mars_order = None, None
    if mars_doc and isinstance(mars_doc.get("squares"), dict) and mars_doc["squares"].get("ids"):
        mars_ids, mars_order = mars_doc["squares"]["ids"], "the order of squares.ids in site/data/mars.json"
    else:
        mc = read(DERIVED / "mars_cells.json")
        if mc:
            mars_ids, mars_order = list(cells(mc).keys()), "the order of cells in data/derived/mars_cells.json"
    mars_layout = None
    if mars_ids:
        merged = {pid: {} for pid in mars_ids}
        for key in MARS_FILES:
            for pid, rec in cells(docs[key]).items():
                if pid in merged:
                    merged[pid][key] = rec
        data, layout = pack(mars_ids, merged, specs_for("mars", targets), refs, "mars")
        size = write(SITE_DATA / "mars_factors.bin", data)
        mars_layout = {"file": "mars_factors.bin", "count": len(mars_ids), "bytes": size, "order": mars_order,
                       "byte_order": "little-endian", "block_alignment": 4,
                       "how_to_read": moon_layout["how_to_read"] if moon_layout else None, "fields": layout}
        out["mars_factors.bin"] = size

    # Fields whose input file is missing mark their rows "not built" on the page too.
    rows = matrix["rows"]
    have = {f["row"] for f in (moon_layout or {}).get("fields", []) if f["known"] > 0}
    aliases = {"silicate": "mineralogy"}          # the silicate row reads the mineral family field
    for row in rows:
        wanted = aliases.get(row["id"], row["id"])
        row["fields_on_page"] = [f["id"] for f in (moon_layout or {}).get("fields", []) if f["row"] == wanted]
        row["mars_fields"] = [f["id"] for f in (mars_layout or {}).get("fields", []) if f["row"] == wanted]
        if row["status"] not in ("not built", "being built", "planet side only") and row["coverage"].get("moon_part_areas") \
                and not row["fields_on_page"] and row["id"] not in ("sun_low_hours", "cloud", "hills", "slope_likeness",
                                                                   "bare", "snow", "anorthosite", "temperature"):
            row["status"], row["status_reason"] = "not built", "No per-area field was written for the page."
    counts = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1

    pf, gm, mcards = read(DERIVED / "planet_factors.json"), read(DERIVED / "ground_moon.json"), read(DERIVED / "moon_cards.json")
    moon_fig, mars_fig = planet_figures(rows, pf, gm, mcards, docs.get("m_ground"), read(DERIVED / "mars_sites.json"),
                                        (docs.get("env") or {}).get("meta"))
    region_names = {c.get("id"): c.get("official_name") for c in (mcards or {}).get("cards", [])}
    tremor_meta = (docs.get("tremors") or {}).get("meta") or {}
    doc = {
        "meta": {
            "what": "Every factor of the project with its status, and the new per-place factors for the page.",
            "made": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "made_by": "agent FACTOR-MATRIX, scripts/export_site_factors.py",
            "matrix_made": matrix["meta"].get("made"),
            "groups": matrix["meta"]["groups"], "statuses": matrix["meta"]["statuses"], "kinds": matrix["meta"]["kinds"],
            "kind_tags": KIND_TAGS, "status_rule": matrix["meta"].get("status_rule"),
            "counts_by_status": counts, "left_out": matrix["meta"].get("left_out"),
            "inputs_missing": missing, "caption": CAPTION, "nav_sentence": NAV_SENTENCE,
            "unknown_word": "unknown", "months": MONTHS, "planet_digits": 2, "targets": targets, "region_names": region_names,
            "coarse_warning": "A coarse grid value is the value of a box much larger than the area, not a measurement at the place.",
            "card_title": "More about this place",
            "card_lead": "New factors for this area, each tagged by kind, with the lunar region's own figure where we hold one.",
            "south_permafrost_note": fit("Ice-free ground in Antarctica is permafrost throughout, by the literature; the permafrost map does not cover it."),
            "tremor_blind_spots": fit(tremor_meta.get("what_it_is_not")),
            "tremor_cannot_tell": "Cannot tell: the catalogue does not record small tremors here, so an empty circle says nothing.",
            "existing_rows_note": "Factors already on the page's own card are not repeated here.",
        },
        "matrix": rows,
        "layout": moon_layout,
        "mars_layout": mars_layout,
        "tables": refs.tables,
        "lunar_regions": moon_fig,
        "mars_sites": mars_fig,
        "rules": rules_in_words(docs),
        "sources": credits(matrix["meta"], read(SITE_DATA / "sources.json")),
    }
    for row in rows:
        for key in ("what_it_is", "what_it_is_not", "status_reason"):
            for path, s in long_sentences(row.get(key), f"{row['id']}.{key}"):
                print(f"  warning: over {MAX_WORDS} words in {path}: {s}")
    plain_page_words(doc)
    size = write(SITE_DATA / "factors.json", json.dumps(doc, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode())
    out["factors.json"] = size
    for name, n in out.items():
        print(f"wrote site/data/{name}: {n:,} bytes")
    print("status counts:", counts)
    if missing:
        print("inputs missing (their fields left out):", ", ".join(missing))
    if moon_layout:
        clipped = [(f["id"], f["clipped_to_range"]) for f in moon_layout["fields"] if f.get("clipped_to_range")]
        if clipped:
            print("clipped to the byte range (Moon part):", clipped)
    if mars_layout:
        clipped = [(f["id"], f["clipped_to_range"]) for f in mars_layout["fields"] if f.get("clipped_to_range")]
        if clipped:
            print("clipped to the byte range (Mars part):", clipped)
    print(f"name tables: {len(refs.tables['volcanoes'])} volcanoes, {len(refs.tables['places'])} places")


if __name__ == "__main__":
    sys.exit(main())

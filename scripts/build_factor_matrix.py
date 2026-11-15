# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""One table of every factor the project shows or was asked for: data/derived/factor_matrix.json.

    uv run python scripts/build_factor_matrix.py

No network. Each row names the factor, its group, what it is, where the Earth, Moon and Mars figures
come from, and a status read from what the files on disk actually hold (counts of known values).
A missing input file never stops the run: its factors read "not built" (or "being built" for the
environment and small-tremor files, which other members may still be writing).
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DERIVED = ROOT / "data" / "derived"
SITE_DATA = ROOT / "site" / "data"
OUT = DERIVED / "factor_matrix.json"

GROUPS = ["light and sky", "ground shape", "ground material", "climate", "below the ground", "hazards",
          "people and access"]
STATUSES = {
    "measured and used in the ranking": "Measured (or computed from measured data) and part of the score that orders the lists.",
    "measured and shown": "Read from a measured map, a catalogue or a model grid, and shown for each place; not in the score.",
    "rough estimate by our own rule": "A word set by a stated rule of our own from other layers. It is not a measurement.",
    "planet side only": "We hold figures for the lunar regions or the Mars sites, but none for the places on Earth.",
    "being built": "Another member is still writing the input file.",
    "not built": "No figure: the reason is given.",
}
KINDS = {
    "measured": "measured from a map, a catalogue or the Sun's computed path, for the area itself",
    "model": "a model value (reanalysis or climate model) at the nearest grid point",
    "coarse map": "a value of a grid box much larger than the area; not a measurement at the place",
    "rough estimate by our rule": "a word set by our own stated rule; not a measurement",
}

# Input files by short key: (file name, part). Parts: moon (the Moon-part areas), mars (the Mars squares),
# planet (the lunar regions and Mars sites), page (the page's own exported files).
FILES = {
    "grazing": ("grazing_cells.json", "moon"), "cloud": ("cloud_cells.json", "moon"),
    "temperature": ("temperature_cells.json", "moon"), "access": ("access_cells.json", "moon"),
    "env": ("environment_cells.json", "moon"), "tremors": ("tremors_cells.json", "moon"),
    "pex": ("power_extra_cells.json", "moon"), "ground": ("ground_cells.json", "moon"),
    "hazards": ("hazards_people_cells.json", "moon"), "rock": ("rock_frozen_cells.json", "moon"),
    "est": ("estimates_cells.json", "moon"), "steady": ("steady_effects_cells.json", "moon"),
    "power": ("power_cells.json", "moon"),
    "m_cells": ("mars_cells.json", "mars"), "m_env": ("mars_environment.json", "mars"),
    "m_tremors": ("mars_tremors.json", "mars"), "m_pex": ("mars_power_extra.json", "mars"),
    "m_ground": ("mars_ground.json", "mars"), "m_hazards": ("mars_hazards_people.json", "mars"),
    "m_rock": ("mars_rock_frozen.json", "mars"), "m_est": ("mars_estimates.json", "mars"),
    "m_steady": ("mars_steady_effects.json", "mars"), "m_power": ("mars_power.json", "mars"),
    "land": ("land_status_cells.json", "moon"), "m_land": ("mars_land_status.json", "mars"),
    "planet": ("planet_factors.json", "planet"), "ground_moon": ("ground_moon.json", "planet"),
    "moon_cards": ("moon_cards.json", "planet"), "mars_sites": ("mars_sites.json", "planet"),
}
BEING_BUILT = {"env", "tremors", "m_env", "m_tremors"}


def g(*path):
    """A getter that walks dict keys; None as soon as a step is missing."""
    def get(record):
        for key in path:
            if not isinstance(record, dict):
                return None
            record = record.get(key)
        return record
    return get


def known(value) -> bool:
    if value is None:
        return False
    if isinstance(value, list):
        return any(known(v) for v in value)
    if isinstance(value, dict):
        return any(known(v) for v in value.values())
    return True


# Each row. earth: list of (file key, getter) probed over the Moon-part areas; mars: the same over the
# Mars squares; planet: (file key, planet_factors id or a special name) for the lunar regions and Mars sites.
ROWS = [
    # ---- light and sky ----
    dict(id="sun_low_hours", name="Sun height and low-Sun hours", group="light and sky", kind="measured", ranked=True,
         unit="hours a year; degrees",
         what="Hours a year in spells of 2 h or more with the Sun's centre above the horizon but under the lunar region's ceiling.",
         earth_from="The Sun's path computed every minute for each area (twinfinder/sun.py), over a flat horizon, then over the real hills.",
         moon_from="The Sun ceiling at each lunar region from its latitude and the Moon's 1.54 degree tilt (moon_cards.json).",
         mars_from="Not used in the Mars part, which compares climate and ground, not low Sun.",
         what_not="Not sunshine under cloud, and not the Sun's height at any one moment.",
         earth=[("grazing", g("targets"))], mars=[], planet=[("moon_cards", "sun_ceiling")]),
    dict(id="cloud", name="Cloud", group="light and sky", kind="coarse map", ranked=False,
         status_note="Step 4 of the map takes typical cloud out of the hours. No ranking score uses it.", unit="percent of sky",
         what="Mean cloud amount by month for the 1 degree box that holds the area; step 4 keeps the hours under typical cloud.",
         earth_from="NASA POWER climatology, CERES SYN1deg cloud amount (cloud_cells.json).",
         moon_from="No air and no cloud on the Moon.", mars_from="Not used in the Mars part.",
         what_not="Not the cloud at the low-Sun hours themselves, and not a measurement at the area.",
         earth=[("cloud", g("cloud_pct"))], mars=[], planet=[]),
    dict(id="uv", name="UV exposure", group="light and sky", kind="coarse map", ranked=False, unit="UV index",
         what="The UV index at the ground under the real sky, averaged over all 24 hours of the day, by month.",
         earth_from="NASA POWER climatology ALLSKY_SFC_UV_INDEX, CERES SYN1deg 1 degree box (environment_cells.json, mars_environment.json).",
         moon_from="No air or ozone on the Moon to filter UV; no lunar UV figure is in our data.",
         mars_from="No Mars UV figure is in our data.",
         what_not="Not the noon UV index of a weather forecast, and not a measurement at the place.",
         earth=[("env", g("uv_index"))], mars=[("m_env", g("uv_index_year"))], planet=[]),
    dict(id="sunlight", name="Surface sunlight", group="light and sky", kind="coarse map", ranked=False,
         unit="kWh per m2 per day",
         what="Sunlight reaching level ground in a mean day of each month, night included, under the real mix of cloud and clear.",
         earth_from="NASA POWER climatology ALLSKY_SFC_SW_DWN, CERES SYN1deg (environment_cells.json, mars_environment.json).",
         moon_from="The lunar regions' lit share of all time (PGDA illumination maps, moon_cards.json); the energy a day is not in our data.",
         mars_from="Sunlight at the top of the Mars atmosphere from the NASA fact sheet (mars_environment.json meta).",
         what_not="Not the light on a tilted panel, and not a measurement at the place.",
         earth=[("env", g("sun_kwh_m2_day"))], mars=[("m_env", g("sun_kwh_m2_day_year"))], planet=[("moon_cards", "lit")]),
    dict(id="clear_days", name="Clear-sky days", group="light and sky", kind="coarse map", ranked=False,
         unit="days a year",
         what="Days with daytime cloud under 10 percent in the 1 degree box, in a typical year (2001 to 2020).",
         earth_from="NASA POWER climatology CLRSKY_DAYS, divided by its 20 years (environment_cells.json, mars_environment.json).",
         moon_from="Every day is clear on the Moon: there is no air.", mars_from="No Mars figure in our data.",
         what_not="Not days of clear sky during the low-Sun hours, and not a count at the place.",
         earth=[("env", g("clear_days"))], mars=[("m_env", g("clear_days_year"))], planet=[]),
    dict(id="haze", name="Dust and haze", group="light and sky", kind="coarse map", ranked=False,
         unit="aerosol optical depth at 550 nm",
         what="How much the air's dust, smoke and haze dim the Sun, as the aerosol optical depth of the 1 degree box.",
         earth_from="NASA POWER climatology AOD_55_ADJ for the areas and AOD_55 for the Mars squares (environment_cells.json, mars_environment.json); the service has no dust-only figure.",
         moon_from="No air on the Moon, so no haze; lunar dust is on the ground.",
         mars_from="The dusty Mars sky from Martinez et al. 2017 (mars_environment.json meta), words only.",
         what_not="Not dust on the ground, and not dust alone: all aerosol together.",
         earth=[("env", g("aod_550"))], mars=[("m_env", g("aod_550_year"))], planet=[]),
    # ---- ground shape ----
    dict(id="hills", name="Hills around the area", group="ground shape", kind="measured", ranked=True,
         unit="degrees of horizon; hours",
         what="The real horizon of each area from a 60 m height model; it removes the low-Sun hours the hills hide.",
         earth_from="Copernicus DEM GLO-90 horizons (horizon_cells.json), step 3 of the map.",
         moon_from="The lunar regions' 5 m LOLA models (PGDA product 78).", mars_from="Not used in the Mars part.",
         what_not="Not shade from plants or buildings.",
         earth=[("grazing", g("horizon", "north_deg"))], mars=[], planet=[("ground_moon", "relief_m")]),
    dict(id="slope", name="Slope", group="ground shape", kind="measured", ranked=False, unit="degrees",
         what="The median and 90th-percentile slope of the ground in a 10 km window, from a 90 m height model.",
         earth_from="Copernicus DEM GLO-90 (ground_cells.json, as terrain_cells.json); Mars squares: slopes across about 3.7 km (mars_ground.json).",
         moon_from="LOLA 5 m models, slopes on 90 m blocks (ground_moon.json).",
         mars_from="MOLA heights every 1.85 km at the Mars sites (mars_ground.json).",
         what_not="Not the slope under one footprint: 90 m pixels smooth out small steps.",
         earth=[("ground", g("median_slope_deg"))], mars=[("m_ground", g("median_slope_deg"))],
         planet=[("ground_moon", "median_slope_deg"), ("m_ground_sites", "median_slope_deg")]),
    dict(id="slope_likeness", name="Slope likeness", group="ground shape", kind="measured", ranked=True,
         unit="score 0 to 1",
         what="How much the area's spread of slopes overlaps the lunar region's own spread of slopes.",
         earth_from="Copernicus DEM GLO-90 slopes (the terrain score in site/data/yearly.bin).",
         moon_from="LOLA 5 m models on 90 m blocks (moon_cards.json fingerprints).",
         mars_from="MOLA slopes across about 3.7 km (the terrain score of mars_cells.json).",
         what_not="Not a match of single landforms, and blind to anything under 90 m.",
         earth=[("page_terrain_score", None)], mars=[("m_cells", g("sites", "jezero", "slope_overlap"))], planet=[]),
    dict(id="roughness", name="Roughness at several scales", group="ground shape", kind="measured", ranked=False,
         unit="m",
         what="How bumpy the ground is once the local slope is taken away, at baselines of 90, 270 and 810 m.",
         earth_from="Copernicus DEM GLO-90 in a 10 km window (ground_cells.json).",
         moon_from="LOLA 5 m models at 5, 15, 45, 90, 270 and 810 m (ground_moon.json).",
         mars_from="Not worked out for the Mars squares: their heights are 1.85 km apart.",
         what_not="Not boulders: nothing under 90 m is seen on Earth. GLO-90 includes forest and buildings.",
         earth=[("ground", g("roughness_m"))], mars=[], planet=[("ground_moon", "roughness_m")]),
    dict(id="landform", name="Landforms", group="ground shape", kind="rough estimate by our rule", ranked=False,
         unit="class",
         what="Plain, rolling ground, hills or mountains, set from slope and relief by thresholds after Hammond (1964).",
         earth_from="Copernicus DEM GLO-90 window (ground_cells.json); Mars squares: a relief class only (mars_ground.json).",
         moon_from="The same rule on 10 km pieces of the 5 m LOLA models (ground_moon.json).",
         mars_from="A relief class at the Mars sites (mars_ground.json).",
         what_not="Not a geomorphological map, and not checked in the field.",
         earth=[("ground", g("landform"))], mars=[("m_ground", g("relief_class"))],
         planet=[("ground_moon", "landform_whole_region"), ("m_ground_sites", "relief_class")]),
    dict(id="visual_navigation", name="Visual navigation difficulty", group="ground shape", kind="measured", ranked=False,
         unit="shown as its parts",
         what="Shown as its parts side by side: the Sun's height, the share of ground in terrain shadow, roughness at 90 m and haze.",
         earth_from="The parts' own sources (Sun path, horizons, GLO-90, NASA POWER aerosol); ground_cells.json for the shadow share.",
         moon_from="The lunar regions' Sun ceiling, lit share and roughness (moon_cards.json, ground_moon.json).",
         mars_from="Not built for the Mars part.",
         what_not="Not a single score: we give none.",
         earth=[("ground", g("shadow", "share"))], mars=[], planet=[("ground_moon", "roughness_m")]),
    # ---- ground material ----
    dict(id="bare", name="Bare ground", group="ground material", kind="measured", ranked=True, unit="share of land",
         what="The share of the area's land that is bare rock, gravel or sand, without plants or permanent ice.",
         earth_from="ESA WorldCover 10 m 2021 (north) and the SCAR rock outcrop layer (south), in grazing_cells.json.",
         moon_from="The lunar regions are bare regolith.", mars_from="ESA WorldCover 2021 for the Mars squares (mars_cells.json).",
         what_not="Not snow-free in every season: snow is a separate step.",
         earth=[("grazing", g("bare"))], mars=[("m_cells", g("bare"))], planet=[]),
    dict(id="snow", name="Snow", group="ground material", kind="measured", ranked=True, unit="odds in percent",
         what="The odds that the area is free of snow in each ten-day period, from daily snow maps of past years.",
         earth_from="NOAA / U.S. National Ice Center IMS snow maps through NSIDC (snow_free_dekads.npz, grazing_cells.json).",
         moon_from="No snow on the Moon.", mars_from="Not used in the Mars part; it uses temperature and dryness.",
         what_not="Not measured in the south, where the rock season is used instead.",
         earth=[("grazing", lambda c: True if g("snow", "status")(c) == "measured" else None)], mars=[], planet=[]),
    dict(id="anorthosite", name="Anorthosite", group="ground material", kind="coarse map", ranked=True,
         unit="named body; An number",
         what="Whether the area lies on a listed anorthosite body, the rock of the Moon's bright highlands.",
         earth_from="Our list of anorthosite bodies from the literature (data/reference/anorthosite_bodies.json; site/data/cells.json rock).",
         moon_from="The lunar regions are highland anorthosite.", mars_from="Mars squares on a listed body (mars_estimates.json mineral family).",
         what_not="Not a rock map of the area: a listed body is a circle around its published centre.",
         earth=[("page_rock", None)], mars=[("m_est", g("mineral_family", "figures", "anorthosite_body"))], planet=[]),
    dict(id="albedo", name="Albedo (surface brightness)", group="ground material", kind="coarse map", ranked=False,
         unit="fraction 0 to 1",
         what="The share of sunlight the ground reflects, as a mean over the sunlit months of the year, for a 1 degree box.",
         earth_from="NASA POWER ALLSKY_SRF_ALB, CERES SYN1deg (power_extra_cells.json, mars_power_extra.json).",
         moon_from="No lunar albedo file was read tonight (planet_factors.json).",
         mars_from="MGS TES albedo mosaic at each Mars site (planet_factors.json).",
         what_not="Not the brightness of bare rock: the box mixes snow, sea and plants.",
         earth=[("pex", g("albedo_year"))], mars=[("m_pex", g("albedo_year"))], planet=[("planet", "albedo")]),
    dict(id="volcanic_rock", name="Volcanic and basaltic material", group="ground material", kind="coarse map", ranked=False,
         unit="yes or no",
         what="Whether the main rock of the half-degree box is volcanic, and whether it is basalt-like (basic volcanic).",
         earth_from="GLiM rock map, Hartmann and Moosdorf 2012, half-degree grid (rock_frozen_cells.json, mars_rock_frozen.json).",
         moon_from="The lunar regions are highland anorthosite, not mare basalt.", mars_from="No per-site rock class in our data.",
         what_not="Not the rock at the place: only the main rock of a box about 55 km across.",
         earth=[("rock", g("rock", "volcanic"))], mars=[("m_rock", g("rock", "volcanic"))], planet=[]),
    dict(id="mineralogy", name="Mineralogy", group="ground material", kind="rough estimate by our rule", ranked=False,
         unit="mineral family",
         what="The usual minerals of the area's mapped rock class, with a Moon and Mars likeness, from one table of ours.",
         earth_from="GLiM rock class and our anorthosite list (estimates_cells.json, mars_estimates.json).",
         moon_from="Highland anorthosite (plagioclase-rich) at the lunar regions.", mars_from="No per-site mineral figure in our data.",
         what_not="Read from a rock map, not from spectra.",
         earth=[("est", g("mineral_family", "estimate"))], mars=[("m_est", g("mineral_family", "estimate"))], planet=[]),
    dict(id="silicate", name="Silicate composition", group="ground material", kind="rough estimate by our rule", ranked=False,
         unit="mineral family",
         what="Which silicate minerals lead (plagioclase, pyroxene and olivine, quartz), read from the mineral family.",
         earth_from="The mineral family row stands in (estimates_cells.json).", moon_from="Plagioclase-rich highland rock.",
         mars_from="No per-site figure in our data.",
         what_not="Not a chemical analysis: no element or oxide figure was read.",
         earth=[("est", g("mineral_family", "estimate"))], mars=[("m_est", g("mineral_family", "estimate"))], planet=[]),
    dict(id="spectral_match", name="Spectral match", group="ground material", kind="measured", ranked=False, unit="none",
         what="How closely the ground's reflected spectrum matches lunar or Mars spectra.",
         earth_from="Not built.", moon_from="Not built.", mars_from="Not built.",
         what_not="The mineral family is not a spectral match.",
         not_built="No spectra of Earth places or of the lunar regions were read tonight; the mineral family row stands in.",
         earth=[], mars=[], planet=[]),
    dict(id="thermal_inertia", name="Thermal inertia", group="ground material", kind="rough estimate by our rule", ranked=False,
         unit="class; index in 1 per degree C",
         what="How fast the ground heats and cools: our index of (1 - albedo) over the daily air temperature swing, cut into thirds.",
         earth_from="NASA POWER albedo and temperature swing (estimates_cells.json heat_response).",
         moon_from="No Diviner polar thermal-inertia product exists (planet_factors.json).",
         mars_from="TES night thermal inertia map at the Mars sites (planet_factors.json).",
         what_not="Not thermal inertia: an index from coarse climate grids.",
         earth=[("est", g("heat_response", "estimate"))], mars=[("m_est", g("heat_response", "estimate"))],
         planet=[("planet", "thermal_inertia")]),
    dict(id="resources", name="Resource-use materials", group="ground material", kind="rough estimate by our rule", ranked=False,
         unit="class",
         what="Whether ilmenite-bearing rock (the oxygen ore of lunar plans) is possible, by the mapped rock class.",
         earth_from="GLiM rock class and our anorthosite list (estimates_cells.json ilmenite).",
         moon_from="Lunar Prospector hydrogen at the lunar regions (planet_factors.json) is the main resource figure.",
         mars_from="Odyssey GRS water at the Mars sites (planet_factors.json).",
         what_not="Not an ore survey: no assay or grade.",
         earth=[("est", g("ilmenite", "estimate"))], mars=[("m_est", g("ilmenite", "estimate"))], planet=[("planet", "hydrogen")]),
    dict(id="rock_abundance", name="Rock abundance", group="ground material", kind="rough estimate by our rule", ranked=False,
         unit="class",
         what="Rockiness: our word from bare share, steep or rough ground and loose sediment, standing in for rock abundance.",
         earth_from="grazing_cells.json, terrain and ground figures and GLiM (estimates_cells.json rockiness).",
         moon_from="The Diviner rock map stops at 80 S; all the lunar regions lie further south (planet_factors.json).",
         mars_from="No numeric Mars rock-abundance file was found (planet_factors.json).",
         what_not="Not a count of rocks or boulders: 90 m heights cannot see single rocks.",
         earth=[("est", g("rockiness", "estimate"))], mars=[("m_est", g("rockiness", "estimate"))],
         planet=[("planet", "rock_abundance")]),
    dict(id="surface_activity", name="Surface activity", group="ground material", kind="measured", ranked=False,
         unit="m per year where given",
         what="Ground that changes by itself today: moving dunes, slope streaks, frost.",
         earth_from="No per-area figure.", moon_from="None expected (NASA 2024 release, planet_factors.json).",
         mars_from="About 1 m a year of dune advance at Gale (NASA APOD; planet_factors.json).",
         what_not="The Gale rate is the dune field's, not the landing point's.",
         earth=[], mars=[], planet=[("planet", "surface_activity")]),
    # ---- climate ----
    dict(id="temperature", name="Temperature", group="climate", kind="model", ranked=False, unit="degrees C",
         what="Mean air temperature 2 m above the ground by month, at the nearest grid point.",
         earth_from="NASA POWER climatology T2M, MERRA-2 (temperature_cells.json; site/data/temperature.bin).",
         moon_from="Diviner model temperatures at the lunar regions (moon_cards.json).",
         mars_from="Mars Climate Database at the Mars sites (mars_sites.json).",
         what_not="Not the ground surface temperature, and not measured at the place.",
         earth=[("temperature", g("t2m_c"))], mars=[("m_cells", g("t2m_year_c"))], planet=[("moon_cards", "diviner")]),
    dict(id="temp_swing", name="Daily temperature swing", group="climate", kind="model", ranked=False, unit="degrees C",
         what="The day's warmest hour minus its coldest hour for air 2 m above the ground, averaged over each month.",
         earth_from="NASA POWER T2M_RANGE, MERRA-2 (power_extra_cells.json, mars_power_extra.json).",
         moon_from="Diviner polar tables were too large to read tonight (planet_factors.json).",
         mars_from="Mars Climate Database ground and air swing (planet_factors.json).",
         what_not="Not the swing of the ground surface, and not measured at the place.",
         earth=[("pex", g("t2m_range_c_year"))], mars=[("m_pex", g("t2m_range_c_year"))],
         planet=[("planet", "daily_temperature_swing")]),
    dict(id="wind", name="Wind", group="climate", kind="model", ranked=False, unit="m/s",
         what="Mean wind speed 10 m above the ground over all hours, at the nearest grid point.",
         earth_from="NASA POWER WS10M, MERRA-2 (power_extra_cells.json, mars_power_extra.json).",
         moon_from="No air, no wind.", mars_from="No Mars wind figure in our data.",
         what_not="Not gusts and not valley winds smaller than the grid box.",
         earth=[("pex", g("wind_10m_ms_year"))], mars=[("m_pex", g("wind_10m_ms_year"))], planet=[]),
    dict(id="soil_moisture", name="Soil moisture", group="climate", kind="model", ranked=False, unit="fraction 0 to 1",
         what="Wetness of the top 5 cm of soil, from 0 (dry) to 1 (saturated), from a land model.",
         earth_from="NASA POWER GWETTOP, MERRA-2 (power_extra_cells.json, mars_power_extra.json).",
         moon_from="Lunar soil holds no liquid water.", mars_from="No liquid water at the surface; see near-surface water.",
         what_not="Not a probe measurement. A value of 1 all year means the model's grid point is ice.",
         earth=[("pex", g("soil_wetness_top_year"))], mars=[("m_pex", g("soil_wetness_top_year"))], planet=[]),
    # ---- below the ground ----
    dict(id="permafrost", name="Permafrost", group="below the ground", kind="coarse map", ranked=False,
         unit="probability 0 to 1; zone",
         what="The modelled probability of permafrost, as a mean of 1 km pixels over the area, and its zone.",
         earth_from="Obu et al. 2019 Northern Hemisphere permafrost map, 1 km (rock_frozen_cells.json, mars_rock_frozen.json).",
         moon_from="Lunar polar ground is frozen all year; see depth to stable ice.",
         mars_from="Mars ice depth at the sites; see depth to stable ice.",
         what_not="Not a measurement in the ground. Antarctica is not in this map.",
         earth=[("rock", g("permafrost", "prob_mean"))], mars=[("m_rock", g("permafrost", "prob_mean"))], planet=[]),
    dict(id="ice_depth", name="Depth to stable ice", group="below the ground", kind="rough estimate by our rule", ranked=False,
         unit="class (Earth); m (Moon, Mars)",
         what="How far down frozen ground or stable ice starts. Earth: a class by our rule from the permafrost zone.",
         earth_from="Our rule on the permafrost zone (estimates_cells.json frozen_ground_depth); no metres were found.",
         moon_from="Diviner model depth to stable ice (moon_cards.json).",
         mars_from="Phoenix 3 to 5 cm by digging; published words for Arcadia and Deuteronilus (planet_factors.json).",
         what_not="Not a thaw-depth measurement on Earth.",
         earth=[("est", g("frozen_ground_depth", "estimate"))], mars=[("m_est", g("frozen_ground_depth", "estimate"))],
         planet=[("moon_cards", "ice"), ("planet", "ice_depth")]),
    dict(id="hydrogen", name="Near-surface hydrogen or water", group="below the ground", kind="rough estimate by our rule",
         ranked=False, unit="class (Earth); ppm H (Moon); weight % water (Mars)",
         what="Earth: top-soil water and ground ice by our rule. Moon and Mars: hydrogen seen from orbit.",
         earth_from="NASA POWER top-soil wetness and the permafrost map (estimates_cells.json topsoil_water).",
         moon_from="Lunar Prospector neutron spectrometer, half-degree bins (planet_factors.json).",
         mars_from="Mars Odyssey GRS, 5 degree bins (planet_factors.json).",
         what_not="Not an orbital hydrogen measurement on Earth; the planet figures are regional, not at the landing point.",
         earth=[("est", g("topsoil_water", "estimate"))], mars=[("m_est", g("topsoil_water", "estimate"))],
         planet=[("planet", "hydrogen")]),
    # ---- hazards ----
    dict(id="large_quakes", name="Large earthquakes", group="hazards", kind="measured", ranked=False,
         unit="count; magnitude; km",
         what="Catalogued earthquakes of magnitude 5 or more within 200 km, 1990 to 2025, with the largest and the nearest.",
         earth_from="USGS ANSS ComCat (hazards_people_cells.json, mars_hazards_people.json).",
         moon_from="NASA 2024 release on south-polar moonquakes, words only (planet_factors.json).",
         mars_from="InSight's 1,319 marsquakes for the whole planet (planet_factors.json).",
         what_not="Not a hazard map and not a forecast.",
         earth=[("hazards", g("quakes_m5_200km", "count"))], mars=[("m_hazards", g("quakes_m5_200km", "count"))],
         planet=[("planet", "quakes")]),
    dict(id="small_tremors", name="Steady small tremors", group="hazards", kind="measured", ranked=False,
         unit="events a year; years of 16",
         what="Catalogued events of magnitude 1 to under 5 within 100 km, 2010 to 2025, and whether the catalogue can see them here.",
         earth_from="USGS ANSS ComCat small events (tremors_cells.json, mars_tremors.json).",
         moon_from="No seismometer has worked near the south pole (planet_factors.json).",
         mars_from="InSight, planet-wide only (planet_factors.json).",
         what_not="Not ground motion at the place; where the network is thin the answer is 'cannot tell'.",
         earth=[("tremors", g("verdict"))], mars=[("m_tremors", g("verdict"))], planet=[("planet", "quakes")]),
    dict(id="active_volcanism", name="Active volcanism", group="hazards", kind="rough estimate by our rule", ranked=False,
         unit="class; km",
         what="Our class from volcanoes that erupted since 1990 within 30 or 100 km, with the nearest Holocene volcano.",
         earth_from="Smithsonian GVP Holocene volcano list (steady_effects_cells.json, hazards_people_cells.json).",
         moon_from="No active volcanism on the Moon.", mars_from="No active volcanism known on Mars today.",
         what_not="Not a hazard map and not an eruption forecast.",
         earth=[("steady", g("volcanic", "class"))], mars=[("m_steady", g("volcanic", "class"))], planet=[]),
    # ---- people and access ----
    dict(id="airfield", name="Airfield distance", group="people and access", kind="measured", ranked=False, unit="km",
         what="Straight-line distance to the nearest airfield, and to the nearest with scheduled flights.",
         earth_from="OurAirports, public domain (access_cells.json).",
         moon_from="Not applicable.", mars_from="Airfields near the Mars squares (mars_steady_effects.json).",
         what_not="Straight-line distance, not travel time.",
         earth=[("access", g("nearest", "km"))], mars=[("m_steady", g("human", "nearest_airfield", "km"))], planet=[]),
    dict(id="human_footprint", name="Human footprint", group="people and access", kind="rough estimate by our rule",
         ranked=False, unit="class; people; km",
         what="Our class from settlements, main roads and airfields nearby, with the people listed within 100 km.",
         earth_from="GeoNames cities1000, Natural Earth roads, OurAirports (steady_effects_cells.json, hazards_people_cells.json).",
         moon_from="No people.", mars_from="No people.",
         what_not="Not a population map: settlements under 1,000 people and stations are not listed.",
         earth=[("steady", g("human", "class"))], mars=[("m_steady", g("human", "class"))], planet=[]),
    dict(id="remoteness", name="Remoteness", group="people and access", kind="measured", ranked=False, unit="km",
         what="Straight-line distance to the nearest listed settlement and to the nearest city of 50,000 or more.",
         earth_from="GeoNames cities1000, CC BY 4.0 (hazards_people_cells.json, mars_hazards_people.json).",
         moon_from="Not applicable.", mars_from="Not applicable.",
         what_not="Not travel time; 'no settlement within 100 km' does not mean nobody lives there.",
         earth=[("hazards", g("people", "nearest", "km"))], mars=[("m_hazards", g("people", "nearest", "km"))], planet=[]),
    dict(id="power", name="Power from sun, wind and ground heat", group="people and access", kind="rough estimate by our rule",
         ranked=False, unit="class",
         what="Our classes for solar panels, wind at 50 m and geothermal plants nearby.",
         earth_from="NASA POWER and the geothermal plant list (power_cells.json, mars_power.json).",
         moon_from="Lunar lit share (moon_cards.json).", mars_from="Mars sunlight from the fact sheet (mars_power.json meta).",
         what_not="Not a power-yield figure for any real system.",
         earth=[("power", g("solar", "class"))], mars=[("m_power", g("solar", "class"))], planet=[]),
    dict(id="land_status", name="Land status and permits", group="people and access", kind="rough estimate by our rule",
         ranked=False, unit="class; territory; authority",
         what=("Who owns or governs the ground at the area's centre, any protected area there, and whom to ask for a permit. "
               "Some classes come from open maps, and the others from territory rules."),
         earth_from=("Natural Earth boundaries give the territory, and official pages give each territory rule. "
                     "Open maps of protected areas and owners set the class where a polygon holds the centre."),
         moon_from="Not applicable: no lunar land status is in our data.",
         mars_from="The same territory rules and maps for the Mars squares on Earth, where a map covers the square.",
         what_not=("Not legal advice. We test the centre of the area only. A territory rule is a rough guide, not a land survey. "
                   "A map covers only its own region."),
         earth=[("land", lambda c: c.get("class") if c.get("class") != "unknown" else None)],
         mars=[("m_land", lambda c: c.get("class") if c.get("class") != "unknown" else None)], planet=[]),
]

# The lunar region and Mars site figures that do not come from planet_factors.json.
PLANET_SPECIAL = {"sun_ceiling", "lit", "diviner", "ice", "relief_m", "median_slope_deg", "roughness_m",
                  "landform_whole_region", "relief_class"}


def read(path: Path):
    try:
        with open(path) as handle:
            return json.load(handle)
    except FileNotFoundError:
        return None


def cells_of(doc):
    """The per-place records of a pipeline file as (id, record) pairs."""
    if doc is None:
        return []
    cells = doc.get("cells") if isinstance(doc, dict) else None
    if isinstance(cells, dict):
        return list(cells.items())
    if isinstance(cells, list):
        return [(c.get("id"), c) for c in cells]
    return []


def page_counts():
    """Counts read from the page's own files: anorthosite matches and the terrain (slope likeness) score."""
    out = {}
    cells = read(SITE_DATA / "cells.json")
    if cells:
        out["page_rock"] = (len(cells.get("rock") or {}), cells.get("n"))
        try:
            import numpy as np
            yearly = cells["yearly"]
            data = np.fromfile(SITE_DATA / yearly["file"], dtype="<u2").reshape(yearly["shape"])
            column = yearly["fields"].index("terrain")
            terrain = data[:, :, column]
            out["page_terrain_score"] = (int((terrain != yearly.get("unknown", 65535)).any(axis=1).sum()), cells.get("n"))
        except (OSError, KeyError, ValueError):
            pass
    return out


def credits_in(meta, prefix=""):
    """Every dict inside a file's meta that names a licence or a credit line, flattened to records."""
    found = []
    if isinstance(meta, dict):
        keys = {k.lower(): k for k in meta}
        lic = next((meta[keys[k]] for k in ("licence", "license") if k in keys), None)
        cred = next((meta[keys[k]] for k in ("credit", "credit_line", "citation") if k in keys), None)
        if isinstance(lic, str) or isinstance(cred, str):
            found.append({"name": meta.get("name") if isinstance(meta.get("name"), str) else prefix or None,
                          "licence": lic if isinstance(lic, str) else None,
                          "credit": cred if isinstance(cred, str) else None})
        for key, value in meta.items():
            if isinstance(value, dict):
                found.extend(credits_in(value, key))
    return found


def build() -> dict:
    docs, present, missing = {}, [], []
    for key, (name, _part) in FILES.items():
        doc = read(DERIVED / name)
        docs[key] = doc
        (present if doc is not None else missing).append(name)
    page = page_counts()
    m_ground_sites = (docs.get("m_ground") or {}).get("sites") or {}
    lunar_count = len((docs.get("moon_cards") or {}).get("cards") or [])   # the lunar regions of the run
    rows = []
    for spec in ROWS:
        row = {k: spec[k] for k in ("id", "name", "group", "kind", "unit", "what", "what_not")}
        row["what_it_is"] = row.pop("what")
        row["what_it_is_not"] = row.pop("what_not")
        row["earth_figure_from"] = spec["earth_from"]
        row["moon_figure_from"] = spec["moon_from"]
        row["mars_figure_from"] = spec["mars_from"]
        coverage = {"moon_part_areas": None, "mars_squares": None, "lunar_regions": None, "mars_sites": None}
        files_used, files_missing = [], []

        def probe(probes):
            total, places, seen = 0, 0, False
            for key, getter in probes:
                if key in page:
                    seen = True
                    total, places = page[key]
                    files_used.append("site/data/cells.json")
                    continue
                if key.startswith("page_"):
                    files_missing.append("site/data/cells.json")
                    continue
                doc = docs.get(key)
                if doc is None:
                    files_missing.append(FILES[key][0])
                    continue
                seen = True
                files_used.append(FILES[key][0])
                records = cells_of(doc)
                places = len(records)
                total = max(total, sum(1 for _id, rec in records if known(getter(rec))))
            return (total, places) if seen else None

        earth = probe(spec["earth"])
        mars = probe(spec["mars"])
        if earth:
            coverage["moon_part_areas"] = {"known": earth[0], "of": earth[1]}
        if mars:
            coverage["mars_squares"] = {"known": mars[0], "of": mars[1]}
        moon_known = mars_known = 0
        moon_any = mars_any = False
        for key, what in spec["planet"]:
            if key == "planet":
                doc = docs.get("planet")
                if doc is None:
                    files_missing.append("planet_factors.json")
                    continue
                files_used.append("planet_factors.json")
                factor = next((f for f in doc.get("factors", []) if f.get("id") == what), None)
                for body, attr in (("moon", "moon"), ("mars", "mars")):
                    entries = (factor or {}).get(body) or {}
                    good = sum(1 for e in entries.values() if known(e.get("value")) or known(e.get("value_text")))
                    if body == "moon":
                        moon_known, moon_any = max(moon_known, good), True
                    else:
                        mars_known, mars_any = max(mars_known, good), True
            elif key in ("moon_cards", "ground_moon"):
                doc = docs.get(key)
                if doc is None:
                    files_missing.append(FILES[key][0])
                    continue
                files_used.append(FILES[key][0])
                if key == "moon_cards":
                    regions = doc.get("cards") or []
                    get = (lambda c: (c.get("diviner") or {}).get("ice")) if what == "ice" else (lambda c: c.get(what))
                else:
                    regions = list((doc.get("regions") or {}).values())
                    get = lambda c: c.get(what)
                moon_known, moon_any = max(moon_known, sum(1 for c in regions if known(get(c)))), True
            elif key == "m_ground_sites":
                if docs.get("m_ground") is None:
                    files_missing.append("mars_ground.json")
                    continue
                mars_known, mars_any = max(mars_known, sum(1 for s in m_ground_sites.values() if known(s.get(what)))), True
        if moon_any:
            coverage["lunar_regions"] = {"known": moon_known, "of": lunar_count}
        if mars_any:
            coverage["mars_sites"] = {"known": mars_known, "of": len((docs.get("mars_sites") or {}).get("sites") or []) or 5}
        row["coverage"] = coverage
        row["files"] = sorted(set(files_used))
        row["files_missing"] = sorted(set(files_missing))
        earth_known = (earth[0] if earth else 0) + (mars[0] if mars else 0)
        planet_known = moon_known + mars_known
        if spec.get("not_built"):
            status, reason = "not built", spec["not_built"]
        elif earth_known > 0:
            if spec["ranked"]:
                status = "measured and used in the ranking"
            elif spec["kind"] == "rough estimate by our rule":
                status = "rough estimate by our own rule"
            else:
                status = "measured and shown"
            reason = spec.get("status_note")
        elif planet_known > 0:
            status, reason = "planet side only", "No per-place Earth figure; figures exist for the lunar regions or the Mars sites."
        elif row["files_missing"] and any(FILES.get(k, ("", ""))[0] in row["files_missing"] for k in BEING_BUILT):
            status, reason = "being built", "Waiting for " + ", ".join(row["files_missing"]) + "."
        elif row["files_missing"]:
            status, reason = "not built", "Input file missing: " + ", ".join(row["files_missing"]) + "."
        else:
            status, reason = "not built", "The input files hold no known value for it."
        row["status"] = status
        row["status_reason"] = reason
        row["enters_score"] = bool(spec["ranked"])
        rows.append(row)

    counts = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    credits = {}
    for key, (name, _part) in FILES.items():
        meta = (docs.get(key) or {}).get("meta") if isinstance(docs.get(key), dict) else None
        if not isinstance(meta, dict):
            continue
        records = credits_in(meta)
        for field in ("source", "credit", "licence", "credit_line"):
            if isinstance(meta.get(field), str):
                records.append({"name": field, "licence": meta.get("licence") if field == "source" else None,
                                "credit": meta[field] if field != "licence" else None})
        if records:
            seen, unique = set(), []
            for rec in records:
                sig = (rec.get("licence"), rec.get("credit"))
                if sig not in seen:
                    seen.add(sig)
                    unique.append(rec)
            credits[name] = unique
    return {
        "meta": {
            "what": "One row for every factor the project shows or was asked for, with where its figures come from and its status, read from the files on disk.",
            "made": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "made_by": "agent FACTOR-MATRIX, scripts/build_factor_matrix.py",
            "how_to_rerun": "uv run python scripts/build_factor_matrix.py",
            "groups": GROUPS, "statuses": STATUSES, "kinds": KINDS,
            "status_rule": "Read from the files: a factor with known values for Earth places is measured (in the ranking or shown) or a rough estimate by its kind; with figures only for the lunar regions or Mars sites it is 'planet side only'; otherwise 'not built' with the reason, or 'being built' when another member's file is still missing.",
            "left_out": "Pits, caves and skylights: dropped by the team lead, no row.",
            "counts_by_status": counts, "rows": len(rows),
            "inputs_present": present, "inputs_missing": missing,
            "credits_and_licences_by_file": credits,
            "page_licence_line": ((read(SITE_DATA / "sources.json") or {}).get("licence_line")),
            "unknown_is": "null",
        },
        "rows": rows,
    }


def write_json(path: Path, value) -> None:
    side = path.with_name(path.name + ".part")
    side.write_text(json.dumps(value, ensure_ascii=False, indent=1, allow_nan=False))
    os.replace(side, path)


def main() -> None:
    matrix = build()
    write_json(OUT, matrix)
    meta = matrix["meta"]
    print(f"wrote {OUT.relative_to(ROOT)}: {meta['rows']} rows")
    for status, n in meta["counts_by_status"].items():
        print(f"  {n:3d}  {status}")
    if meta["inputs_missing"]:
        print("  missing inputs:", ", ".join(meta["inputs_missing"]))


if __name__ == "__main__":
    sys.exit(main())

# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Rough estimates, by our own stated rules, for factors that have no open Earth data.

Every estimate here is a word (low, medium, high, or a few named classes) worked out by a simple rule from
layers the project already holds (bare share, slopes, roughness, rock map, permafrost map, NASA POWER
climate grids). None of them is a measurement. All the rules are in RULES below, and the build script
(scripts/build_estimates.py) writes that table, in plain words, into the meta of both output files.

Unknown is None (null in the files), never 0 and never a guess: a rule whose inputs are unknown gives None,
unless one of its inputs already settles the answer on its own.
"""
from __future__ import annotations

import math

NOT_A_MEASUREMENT = "A rough estimate by our own rule. It is not a measurement."


def water_sentence(planet: dict | None) -> str:
    """The sentence that sets the water of dry Earth soil beside the hydrogen of lunar soil.

    The count of lunar regions and the hydrogen range come from planet_factors.json (factor "hydrogen",
    the moon block), so the sentence follows the regions of the run. Without a figure it gives no number.
    """
    values, regions = [], 0
    for factor in (planet or {}).get("factors", []):
        if factor.get("id") == "hydrogen":
            block = factor.get("moon") or {}
            regions = len(block)
            values = [v.get("value") for v in block.values() if isinstance(v, dict) and v.get("value") is not None]
    if values:
        lo, hi = min(values), max(values)
        where = (f"the {len(values)} lunar regions" if len(values) == regions
                 else f"{len(values)} of the {regions} lunar regions")
        return (f"Dry soil on Earth holds much more water than lunar soil. Lunar Prospector gives approximately "
                f"{lo:.0f} to {hi:.0f} ppm of hydrogen at {where} (planet_factors.json). If all of this hydrogen "
                f"is in water, the lunar soil holds only approximately {lo * 9 / 1e4:.2f} to {hi * 9 / 1e4:.2f} % "
                f"water by weight. A top-soil wetness of 0.1 is approximately 4 % water by volume in a soil with "
                f"40 % pore space.")
    return ("Dry soil on Earth holds much more water than lunar soil. Away from the cold traps, lunar soil holds "
            "approximately 0.1 % water or less. A top-soil wetness of 0.1 is approximately 4 % water by volume in "
            "a soil with 40 % pore space.")

# --- every number a rule uses -----------------------------------------------------------------------------
T = {
    # snow-free months (used by rules 2, 4 and 6)
    "snow_free_air_c": 0.0,          # a month counts as snow-free when its mean air temperature at 2 m is above this
    # rule 1, rockiness
    "rock_bare_high": 0.5,           # at least half the land bare
    "rock_bare_low": 0.25,           # under a quarter bare
    "rock_p90_steep_deg": 10.0,      # 90th-percentile slope at or above this is steep
    "rock_p90_flat_deg": 5.0,        # loose sediment with a 90th-percentile slope under this is low
    # rule 4, ground ice from the permafrost probability
    "ice_likely_prob": 0.5,
    "ice_possible_prob": 0.1,
    "ice_unlikely_air_c": 3.0,       # outside the permafrost map: yearly mean air at or above this -> unlikely
    # rule 6, sand and dust on the move
    "dust_wind_ms": 6.0,
    "dust_bare_mostly": 0.5,
    "dust_bare_vegetated": 0.25,
}

# GLiM first-level class codes (data/derived/rock_frozen_cells.json meta.rock_classes)
ROCK_UNKNOWN_CODES = {None, "nd", "wb"}   # no data, water: the map says nothing about rock
ICE_CODE = "ig"

# --- rule 3, mineral family: one line per rock class ---------------------------------------------------------
MINERAL_FAMILY = {
    "anorthosite": {"family": "plagioclase-rich",
                    "reads": "plagioclase-rich: like the Moon's bright highlands",
                    "like_moon": True, "like_mars": False},
    "vb": {"family": "basalt minerals",
           "reads": "basalt minerals (plagioclase, pyroxene, olivine): like the Moon's dark plains and like Mars",
           "like_moon": True, "like_mars": True},
    "pb": {"family": "basalt minerals, coarse-grained",
           "reads": "the minerals of basalt (plagioclase, pyroxene, olivine) in coarse crystals (gabbro): "
                    "close in minerals to the Moon's dark plains and to Mars, not in grain size",
           "like_moon": True, "like_mars": True},
    "vi": {"family": "andesite minerals",
           "reads": "plagioclase with pyroxene and amphibole (andesite): unlike the Moon; a little like some Mars rock",
           "like_moon": False, "like_mars": None},
    "pi": {"family": "diorite minerals",
           "reads": "plagioclase, amphibole and some quartz (diorite): unlike the Moon and Mars",
           "like_moon": False, "like_mars": False},
    "va": {"family": "rhyolite minerals",
           "reads": "quartz, alkali feldspar and plagioclase (rhyolite, dacite): unlike the Moon and Mars",
           "like_moon": False, "like_mars": False},
    "pa": {"family": "granite minerals",
           "reads": "quartz, alkali feldspar and mica (granite): unlike the Moon and Mars",
           "like_moon": False, "like_mars": False},
    "py": {"family": "volcanic glass and ash",
           "reads": "volcanic glass and ash whose make-up varies: unlike the Moon's rock; Mars has ash-like deposits",
           "like_moon": False, "like_mars": None},
    "mt": {"family": "gneiss and schist minerals",
           "reads": "quartz, feldspar and mica, often with garnet or amphibole (gneiss, schist): unlike the Moon and Mars",
           "like_moon": False, "like_mars": False},
    "ss": {"family": "sandstone and shale minerals",
           "reads": "grains of quartz, feldspar and clay (sandstone, siltstone, shale): unlike the Moon; "
                    "Mars has some sandstone and mudstone",
           "like_moon": False, "like_mars": None},
    "sm": {"family": "mixed sedimentary minerals",
           "reads": "quartz, clay and calcite in mixed layers: unlike the Moon; partly like Mars sedimentary rock",
           "like_moon": False, "like_mars": None},
    "sc": {"family": "carbonate minerals",
           "reads": "calcite and dolomite (limestone, dolomite): unlike the Moon; carbonate is rare on Mars",
           "like_moon": False, "like_mars": False},
    "ev": {"family": "salt minerals",
           "reads": "halite and gypsum (rock salt): unlike the Moon; Mars has sulfate and chloride salt deposits",
           "like_moon": False, "like_mars": None},
    "su": {"family": "loose mixed grains",
           "reads": "loose grains of quartz, feldspar and clay of mixed make-up: unlike lunar soil in minerals; "
                    "Mars soil is mostly basalt grains",
           "like_moon": False, "like_mars": False},
}

# --- rule 2, heat response, by third -------------------------------------------------------------------------
HEAT_READS = {
    "fast": "heats and cools fast, like dry dust or sand",
    "medium": "in between",
    "slow": "slow, like rock or wet ground",
}

# --- rule 5, depth to frozen ground, by permafrost zone (classes without metres; see build meta) -------------
FROZEN_DEPTH = {
    "continuous": ("shallow", "frozen ground under the summer-thawed top layer almost everywhere"),
    "discontinuous": ("shallow in most of the area", "frozen ground under the summer-thawed top layer in half "
                      "to nine-tenths of the area, none in the rest"),
    "sporadic": ("patchy", "frozen ground in patches only (a tenth to half of the area)"),
    "isolated patches": ("rare", "frozen ground only in rare patches (under a tenth of the area)"),
    "none": ("none expected", "no frozen ground expected"),
    "antarctic literature": ("shallow (literature)", "ice-free ground in Antarctica is permafrost throughout, by "
                             "the literature: frozen ground under the summer-thawed top layer; not our map"),
}

# --- the table of rules, in plain words (written into the meta of both outputs) ------------------------------
RULES = [
    {"number": 0, "id": "snow_free_months", "name": "Snow-free months (used by rules 2, 4 and 6)",
     "rule": f"The calendar months whose mean air temperature 2 m above the ground is above "
             f"{T['snow_free_air_c']:g} C in the NASA POWER grid (temperature_cells.json for the Moon part, "
             f"mars_climate.json for the Mars part). Where no month is above {T['snow_free_air_c']:g} C, the single "
             f"warmest month. Taken from temperature, not from the snow maps, so that the Moon and Mars parts "
             f"use the same rule.",
     "classes": "a list of month numbers, 1 = January"},
    {"number": 1, "id": "rockiness", "stands_in_for": "rock abundance",
     "name": "Rockiness",
     "rule": f"high when at least {T['rock_bare_high']:g} of the land is bare, the ground is steep or rough "
             f"(90th-percentile slope of {T['rock_p90_steep_deg']:g} degrees or more, or roughness at 90 m at least "
             f"that of the smoothest lunar region) and the rock map does not say loose sediment; low when under "
             f"{T['rock_bare_low']:g} of the land is bare, or the rock map says loose sediment and the "
             f"90th-percentile slope is under {T['rock_p90_flat_deg']:g} degrees; medium otherwise. "
             f"Mars part: no 90 m roughness is held, so steep-or-rough is the slope test alone, and its slopes are "
             f"taken across about 3.7 km, which reads flatter than the Moon part's 90 m slopes.",
     "classes": "low, medium, high"},
    {"number": 2, "id": "heat_response", "stands_in_for": "thermal inertia",
     "name": "How fast the ground heats and cools",
     "rule": "index = mean of (1 - albedo) over the snow-free months divided by the mean daily temperature swing of "
             "air at 2 m over the same months (months where both are known), in 1 per degree C. The places of "
             "each output file are cut into thirds by this index: the lowest third reads 'heats and cools fast, "
             "like dry dust or sand', the middle third 'in between', the highest third 'slow, like rock or wet "
             "ground'. Both inputs come from coarse climate grids (NASA POWER: CERES 1 degree albedo, MERRA-2 "
             "air temperature swing), not from the ground at the place.",
     "classes": "fast, medium, slow"},
    {"number": 3, "id": "mineral_family", "stands_in_for": "mineralogy, spectral match and silicate composition",
     "name": "Mineral family",
     "rule": "read from the rock map's class by one table (meta.mineral_family_table): basic volcanic rock gives "
             "'basalt minerals (plagioclase, pyroxene, olivine): like the Moon's dark plains and like Mars'; a place "
             "on a listed anorthosite body (data/reference/anorthosite_bodies.json) gives 'plagioclase-rich: like "
             "the Moon's bright highlands' with the body's listed feldspar composition (An number), and this wins "
             "over the map's class; every other class gets its usual minerals in a few plain words. Ice, water and "
             "no-data boxes give null. Read from a rock map, not from spectra.",
     "classes": "the families of meta.mineral_family_table"},
    {"number": 4, "id": "topsoil_water", "stands_in_for": "near-surface hydrogen and water",
     "name": "Water in the top soil",
     "rule": f"dry, moist or wet by thirds of the mean top-soil wetness (NASA POWER GWETTOP, 0 dry to 1 saturated) "
             f"over the snow-free months, cut over the places of each output file (cut values in meta.cuts); null "
             f"where the model's grid point is ice (soil_wetness_ice_flag). Ground ice: likely when the mean "
             f"permafrost probability is {T['ice_likely_prob']:g} or more, possible from {T['ice_possible_prob']:g} "
             f"to under {T['ice_likely_prob']:g}, unlikely under {T['ice_possible_prob']:g}; in Antarctica likely, by "
             f"the literature note of rock_frozen_cells.json (not a map value); where the map has no value, "
             f"unlikely when the yearly mean air temperature is {T['ice_unlikely_air_c']:g} C or more, else null.",
     "classes": "dry, moist, wet; ground ice likely, possible, unlikely"},
    {"number": 5, "id": "frozen_ground_depth", "stands_in_for": "depth to stable ice",
     "name": "Depth to frozen ground",
     "rule": "from the permafrost zone: continuous -> shallow; discontinuous -> shallow in most of the area; "
             "sporadic -> patchy; isolated patches -> rare; none -> none expected; Antarctica -> shallow "
             "(literature); where the map has no value, none expected when the yearly mean air temperature is "
             f"{T['ice_unlikely_air_c']:g} C or more (as in rule 4), else null. Classes only, no metres: the open "
             "pages opened tonight gave no zone-by-zone rule of thumb for the thickness of the summer-thawed layer "
             "(meta.frozen_ground_depth_sources).",
     "classes": "shallow, shallow in most of the area, patchy, rare, none expected, shallow (literature)"},
    {"number": 6, "id": "sand_dust", "stands_in_for": "surface activity",
     "name": "Sand and dust on the move",
     "rule": f"likely where the ground is loose sediment (rock map) or mostly bare (bare share "
             f"{T['dust_bare_mostly']:g} or more), the top soil is in the dry third and the mean wind at 10 m over "
             f"the snow-free months is {T['dust_wind_ms']:g} m/s or more; unlikely where the top soil is in the wet "
             f"third, or the ground is frozen (the model's grid point is ice, or the rock map says ice and "
             f"glaciers), or mostly not bare (bare share under {T['dust_bare_vegetated']:g}: plants, ice or water); "
             f"possible otherwise.",
     "classes": "likely, possible, unlikely"},
    {"number": 7, "id": "ilmenite", "stands_in_for": "ilmenite (iron-titanium oxide) in the rock",
     "name": "Ilmenite-bearing rock possible",
     "rule": "possible where the rock map says basic volcanic rock or the place lies on a listed anorthosite body "
             "(iron-titanium oxide deposits occur in both); otherwise unlikely; null where the map says ice, water "
             "or no data and no body is listed.",
     "classes": "possible, unlikely"},
]


# --- small helpers --------------------------------------------------------------------------------------------
def r(value, digits: int = 3):
    return None if value is None else round(float(value), digits)


def all_of(*values):
    """Three-valued and: False wins, then unknown."""
    if any(v is False for v in values):
        return False
    if any(v is None for v in values):
        return None
    return True


def any_of(*values):
    """Three-valued or: True wins, then unknown."""
    if any(v is True for v in values):
        return True
    if any(v is None for v in values):
        return None
    return False


def cmp(value, op: str, limit: float):
    if value is None:
        return None
    return {">=": value >= limit, "<": value < limit, ">": value > limit}[op]


def snow_free_months(t2m_c):
    """Month numbers (1-12) with mean 2 m air temperature above the limit; else the warmest month; None if unknown."""
    if not t2m_c:
        return None
    known = [(i + 1, v) for i, v in enumerate(t2m_c) if v is not None]
    if not known:
        return None
    months = [m for m, v in known if v > T["snow_free_air_c"]]
    return months or [max(known, key=lambda mv: mv[1])[0]]


def mean_over(values, months):
    if values is None or months is None:
        return None
    got = [values[m - 1] for m in months if values[m - 1] is not None]
    return sum(got) / len(got) if got else None


def thirds(values):
    """The two cut values that split the known values into thirds (None if under three values)."""
    got = sorted(v for v in values if v is not None)
    if len(got) < 3:
        return None

    def q(p):
        k = (len(got) - 1) * p
        lo, hi = math.floor(k), math.ceil(k)
        return got[lo] + (got[hi] - got[lo]) * (k - lo)

    return [q(1 / 3), q(2 / 3)]


def third_of(value, cuts, words):
    if value is None or cuts is None:
        return None
    if value < cuts[0]:
        return words[0]
    if value < cuts[1]:
        return words[1]
    return words[2]


def rock_code_known(code) -> bool:
    return code not in ROCK_UNKNOWN_CODES


# --- the seven estimates ------------------------------------------------------------------------------------
def rockiness(bare, p90_slope_deg, roughness_90m_m, smoothest_lunar_90m_m, rock_code, use_roughness=True):
    loose = None if not rock_code_known(rock_code) else rock_code == "su"
    steep = cmp(p90_slope_deg, ">=", T["rock_p90_steep_deg"])
    if use_roughness:
        rough = None if smoothest_lunar_90m_m is None else cmp(roughness_90m_m, ">=", smoothest_lunar_90m_m)
        steep_or_rough = any_of(steep, rough)
    else:
        steep_or_rough = steep
    high = all_of(cmp(bare, ">=", T["rock_bare_high"]), steep_or_rough, None if loose is None else not loose)
    low = any_of(cmp(bare, "<", T["rock_bare_low"]), all_of(loose, cmp(p90_slope_deg, "<", T["rock_p90_flat_deg"])))
    if low is True:
        word = "low"
    elif high is True:
        word = "high"
    elif low is False and high is False:
        word = "medium"
    else:
        word = None
    figures = {"bare": r(bare), "p90_slope_deg": r(p90_slope_deg, 2), "loose_sediment": loose}
    if use_roughness:
        figures["roughness_90m_m"] = r(roughness_90m_m, 2)
    return {"estimate": word, "figures": figures}


def heat_index(albedo, t2m_range_c, months):
    """(1 - albedo) / daily swing over the snow-free months where both are known."""
    if albedo is None or t2m_range_c is None or months is None:
        return None, None, None, []
    used = [m for m in months if albedo[m - 1] is not None and t2m_range_c[m - 1] is not None]
    if not used:
        return None, None, None, []
    absorbed = sum(1 - albedo[m - 1] for m in used) / len(used)
    swing = sum(t2m_range_c[m - 1] for m in used) / len(used)
    if swing <= 0:
        return None, absorbed, swing, used
    return absorbed / swing, absorbed, swing, used


def heat_response(index, absorbed, swing, used, cuts):
    word = third_of(index, cuts, ["fast", "medium", "slow"])
    return {"estimate": word,
            "figures": {"index_per_c": r(index, 4), "one_minus_albedo": r(absorbed), "t2m_range_c": r(swing, 2),
                        "months_used": used or None}}


def mineral_family(rock_code, body):
    if body is not None:
        row = MINERAL_FAMILY["anorthosite"]
        lo, hi = body.get("an_low"), body.get("an_high")
        comp = None if lo is None or hi is None else (f"An{lo:g}" if lo == hi else f"An{lo:g}-{hi:g}")
        return {"estimate": row["family"], "figures": {"rock_class_code": rock_code, "anorthosite_body": body["name"],
                                                       "an_low": lo, "an_high": hi, "composition": comp}}
    if not rock_code_known(rock_code) or rock_code == ICE_CODE or rock_code not in MINERAL_FAMILY:
        return {"estimate": None, "figures": {"rock_class_code": rock_code, "anorthosite_body": None}}
    return {"estimate": MINERAL_FAMILY[rock_code]["family"],
            "figures": {"rock_class_code": rock_code, "anorthosite_body": None}}


def ground_ice(prob_mean, antarctic_note: bool, t2m_year_c):
    if prob_mean is not None:
        if prob_mean >= T["ice_likely_prob"]:
            return "likely", "permafrost map"
        if prob_mean >= T["ice_possible_prob"]:
            return "possible", "permafrost map"
        return "unlikely", "permafrost map"
    if antarctic_note:
        return "likely", "literature note (Antarctica), not a map value"
    if t2m_year_c is not None and t2m_year_c >= T["ice_unlikely_air_c"]:
        return "unlikely", f"no map value; yearly mean air {t2m_year_c:.1f} C"
    return None, None


def topsoil_water(wetness, ice_flag, cuts, prob_mean, antarctic_note, t2m_year_c):
    word = None if ice_flag is True or ice_flag is None else third_of(wetness, cuts, ["dry", "moist", "wet"])
    ice_word, ice_basis = ground_ice(prob_mean, antarctic_note, t2m_year_c)
    return {"estimate": word, "ground_ice": ice_word,
            "figures": {"soil_wetness": r(wetness), "ice_flag": ice_flag, "permafrost_prob_mean": r(prob_mean),
                        "ground_ice_basis": ice_basis}}


def frozen_ground_depth(zone, antarctic_note, t2m_year_c=None):
    basis = "permafrost map" if zone in FROZEN_DEPTH else None
    key = zone if zone in FROZEN_DEPTH else None
    if key is None and antarctic_note:
        key, basis = "antarctic literature", "literature note (Antarctica), not a map value"
    if key is None and t2m_year_c is not None and t2m_year_c >= T["ice_unlikely_air_c"]:
        key, basis = "none", f"no map value; yearly mean air {t2m_year_c:.1f} C"
    return {"estimate": None if key is None else FROZEN_DEPTH[key][0], "metres": None,
            "figures": {"permafrost_zone": zone, "basis": basis}}


def sand_dust(rock_code, bare, water_word, wind_ms, ice_flag):
    loose = None if not rock_code_known(rock_code) else rock_code == "su"
    frozen = any_of(ice_flag, None if rock_code is None else rock_code == ICE_CODE)
    wet = None if water_word is None else water_word == "wet"
    dry = None if water_word is None else water_word == "dry"
    unlikely = any_of(wet, frozen, cmp(bare, "<", T["dust_bare_vegetated"]))
    likely = all_of(any_of(loose, cmp(bare, ">=", T["dust_bare_mostly"])), dry, cmp(wind_ms, ">=", T["dust_wind_ms"]))
    if unlikely is True:
        word = "unlikely"
    elif likely is True:
        word = "likely"
    elif unlikely is False and likely is False:
        word = "possible"
    else:
        word = None
    return {"estimate": word, "figures": {"loose_sediment": loose, "bare": r(bare), "topsoil": water_word,
                                          "wind_10m_ms": r(wind_ms, 2), "frozen": frozen}}


def ilmenite(rock_code, body):
    if body is not None or rock_code == "vb":
        word = "possible"
    elif rock_code_known(rock_code) and rock_code != ICE_CODE:
        word = "unlikely"
    else:
        word = None
    return {"estimate": word, "figures": {"rock_class_code": rock_code,
                                          "anorthosite_body": None if body is None else body["name"]}}

"""Mars part, scores: how close a half-degree Earth square comes to a Mars site, factor by factor
(docs/superpowers/plans/2026-11-14-mars-part.md, section "Scores").

Each factor lies between 0 and 1 and is kept apart; a goal is the geometric mean of its factors.
Unknown is None, never 0: an unknown factor makes every goal that uses it unknown.
"""
from __future__ import annotations

import bisect
import hashlib
import math

from twinfinder import sun
from twinfinder.mars_climate import EARTH_TILT_DEG, noon_elevation_range

FACTORS = ("terrain", "dry", "cold", "bare", "sun")
GOALS = {
    "landscape": ("terrain", "bare"),
    "environment": ("dry", "cold", "bare"),
    "full": FACTORS,
}

DRY_FULL_MM = 25.0        # dry = 1 at 25 mm a year of rain and snow, or less
DRY_ZERO_MM = 500.0       # dry = 0 at 500 mm a year or more
# cold = 0 at a yearly mean of +30 C or warmer: about the warmest yearly mean anywhere on Earth, so the scale runs
# over Earth's whole range (coordinator's decision of 14 Nov 2026; it was +15 C, which put the hyperarid Atacama,
# the Mojave, Dhofar and the Pilbara at 0)
COLD_ZERO_C = 30.0
PREVIOUS_COLD_ZERO_C = 15.0   # the first pass's zero point, kept only to report the change
EARTH_RADIUS_KM = 6371.0088
SAME_PLACE_KM = 300.0     # the best places are kept at least this far apart

MONTH_NAMES = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
MID_MONTH_DOY = (15, 46, 74, 105, 135, 166, 196, 227, 258, 288, 319, 349)   # the 15th, common year

FORMULAS = {
    "terrain": "min(1, overlap of the square's and the site's slope histograms / the site's self-overlap)",
    "dry": "1 at 25 mm of rain and snow a year or less, 0 at 500 mm or more, a straight line on a log scale between",
    "cold": f"1 where the square's yearly mean air temperature equals the site's (or is colder), 0 at "
            f"+{COLD_ZERO_C:g} C or warmer, a straight line between",
    "bare": "the bare share of the square's land",
    "sun": "the share of the site's yearly range of noon Sun height that the square's own yearly range covers "
           "(absolute latitude on both planets; tilt 25.19 degrees on Mars, 23.44 on Earth)",
    "landscape": "geometric mean of terrain and bare",
    "environment": "geometric mean of dry, cold and bare",
    "full": "geometric mean of terrain, dry, cold, bare and sun",
    "goal_rule": "any unknown factor makes the goal unknown; a factor of 0 makes the goal 0",
    "month": f"per month, the geometric mean of that month's cold (monthly mean air temperature against the site's "
             f"yearly mean, on the same scale: 0 at +{COLD_ZERO_C:g} C or warmer), dry (the month's precipitation "
             f"times 12) and 1 or 0 for whether the square's noon Sun height on the 15th of the month lies inside "
             f"the site's yearly range",
    "best_months": "the three months with the highest month score above 0, best first; ties keep calendar order",
}


# ---- factors -----------------------------------------------------------------------------------------

def _clip01(x: float) -> float:
    return min(1.0, max(0.0, x))


def terrain_score(overlap: float | None, self_overlap: float | None) -> float | None:
    if overlap is None or self_overlap is None or self_overlap <= 0.0:
        return None
    return _clip01(overlap / self_overlap)


def dry_score(precip_mm_year: float | None) -> float | None:
    if precip_mm_year is None or precip_mm_year < 0.0:
        return None
    if precip_mm_year <= DRY_FULL_MM:
        return 1.0
    if precip_mm_year >= DRY_ZERO_MM:
        return 0.0
    return (math.log(DRY_ZERO_MM) - math.log(precip_mm_year)) / (math.log(DRY_ZERO_MM) - math.log(DRY_FULL_MM))


def cold_score(temp_c: float | None, site_temp_c: float | None, zero_c: float = COLD_ZERO_C) -> float | None:
    """1 at the site's temperature or colder, 0 at zero_c or warmer, a straight line between.

    zero_c is COLD_ZERO_C for every score; another value is used only to report what the change of scale did."""
    if temp_c is None or site_temp_c is None or site_temp_c >= zero_c:
        return None
    return _clip01((zero_c - temp_c) / (zero_c - site_temp_c))


def bare_score(bare: float | None) -> float | None:
    return None if bare is None else _clip01(bare)


def earth_noon_range(lat: float | None) -> tuple[float, float] | None:
    """Lowest and highest noon Sun height of the year at an Earth latitude (tilt 23.44 degrees)."""
    return None if lat is None else noon_elevation_range(lat, EARTH_TILT_DEG)


def sun_score(site_range, cell_range) -> float | None:
    """Share of the site's yearly range of noon Sun height that the square's yearly range covers."""
    if site_range is None or cell_range is None:
        return None
    lo, hi = site_range
    if hi - lo <= 0.0:
        return None
    shared = min(hi, cell_range[1]) - max(lo, cell_range[0])
    return _clip01(shared / (hi - lo))


# ---- goals -------------------------------------------------------------------------------------------

def geometric_mean(values) -> float | None:
    values = list(values)
    if not values or any(v is None for v in values):
        return None
    if any(v <= 0.0 for v in values):
        return 0.0
    return math.exp(sum(math.log(v) for v in values) / len(values))


def goals(factors: dict) -> dict:
    return {goal: geometric_mean(factors.get(f) for f in names) for goal, names in GOALS.items()}


# ---- the Sun by month and the calendar ---------------------------------------------------------------

def noon_sun_by_month(lat: float | None) -> list[float] | None:
    """Noon Sun height (true, Sun's centre, flat horizon) on the 15th of each month, degrees."""
    if lat is None:
        return None
    return [float(sun.noon_elevation_deg(lat, doy)) for doy in MID_MONTH_DOY]


def month_scores(t2m_c, precip_mm, lat, site_temp_c, site_range) -> list[float | None] | None:
    if t2m_c is None or precip_mm is None or lat is None or site_temp_c is None or site_range is None:
        return None
    noon = noon_sun_by_month(lat)
    lo, hi = site_range
    out = []
    for m in range(12):
        t, p = t2m_c[m], precip_mm[m]
        cold = cold_score(t, site_temp_c)
        dry = None if p is None else dry_score(12.0 * p)
        inside = 1.0 if lo <= noon[m] <= hi else 0.0
        out.append(geometric_mean([cold, dry, inside]))
    return out


def best_months(scores, n: int = 3) -> list[str] | None:
    if scores is None:
        return None
    known = [(s, m) for m, s in enumerate(scores) if s is not None and s > 0.0]
    known.sort(key=lambda x: (-x[0], x[1]))
    return [MONTH_NAMES[m] for _, m in known[:n]]


# ---- what falls short --------------------------------------------------------------------------------

def falls_short(temp_year_c, site_temp_c, precip_mm_year, pressure_kpa, site_pressure_pa) -> dict:
    colder = None if temp_year_c is None or site_temp_c is None else temp_year_c - site_temp_c
    wetter = None if precip_mm_year is None else precip_mm_year / DRY_FULL_MM
    ratio = (None if pressure_kpa is None or site_pressure_pa is None or pressure_kpa <= 0.0
             else site_pressure_pa / (pressure_kpa * 1000.0))
    return {"colder_on_mars_by_c": colder, "times_wetter_than_25_mm": wetter, "pressure_mars_over_square": ratio}


# ---- places, ranks and the test of the ranking -------------------------------------------------------

def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2.0 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(h)))


def pick_best(rows, key: str, n: int = 10, min_km: float = SAME_PLACE_KM, tie=None) -> list[dict]:
    """The n best rows by rows[key], highest first, each at least min_km from those before.

    Equal scores are ordered by rows[tie] (highest first, unknown last) when tie is given, then by id. tie may be
    one key or a tuple of keys used in turn."""
    ties = () if tie is None else (tie,) if isinstance(tie, str) else tuple(tie)

    def order(r):
        out = [-r[key]]
        for k in ties:
            t = r.get(k)
            out += [t is None, 0.0 if t is None else -t]
        return (*out, r["id"])
    known = sorted((r for r in rows if r.get(key) is not None), key=order)
    out: list[dict] = []
    for r in known:
        if all(distance_km(r["lat"], r["lon"], q["lat"], q["lon"]) >= min_km for q in out):
            out.append(r)
            if len(out) == n:
                break
    return out


def count_at(values, value) -> int:
    """How many of the values equal value exactly (unknown never counts)."""
    if value is None:
        return 0
    return sum(1 for v in values if v is not None and v == value)


def auc(known, controls) -> float | None:
    """Share of (known, control) pairs in which the known value is higher; a tie counts one half."""
    k = sorted(v for v in known if v is not None)
    c = sorted(v for v in controls if v is not None)
    if not k or not c:
        return None
    total = 0.0
    for v in k:
        below = bisect.bisect_left(c, v)
        ties = bisect.bisect_right(c, v) - below
        total += below + 0.5 * ties
    return total / (len(k) * len(c))


def percentile(value, population) -> float | None:
    """Percent of the population below the value, ties counting one half."""
    pop = sorted(v for v in population if v is not None)
    if value is None or not pop:
        return None
    below = bisect.bisect_left(pop, value)
    ties = bisect.bisect_right(pop, value) - below
    return 100.0 * (below + 0.5 * ties) / len(pop)


def sha1_key(square_id: str) -> str:
    return hashlib.sha1(square_id.encode()).hexdigest()


def control_ids(ids, n: int, exclude=()) -> list[str]:
    """The n ids with the lowest sha1 of the id, leaving out those in exclude: the same every run."""
    ex = set(exclude)
    return sorted((i for i in ids if i not in ex), key=sha1_key)[:n]

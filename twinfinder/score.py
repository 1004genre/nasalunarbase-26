# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Turn separate factor scores (each 0 to 1) into goal scores, ranking filters and ranked sites.

The four factors stay separate: light (long-window grazing hours), terrain
(slope overlap against the lunar site's own overlap), bare ground and rock.
A factor that cannot be known is None, and so is every goal that uses it: an
unknown cell is left out of a ranking, never ranked as a zero.
"""
from __future__ import annotations

import math

from twinfinder import reference

FULL_HOURS = 200.0     # long-window grazing hours a year that earn full light marks (about forty five-hour sessions)
RANK_MIN_BARE = 0.25   # cells with less bare ground than this are listed but not ranked
SAME_SITE_KM = 50.0    # cells closer than this count as one site
FACTOR_DIGITS = 6      # decimals kept of each stored factor score
GOAL_DIGITS = 3        # decimals kept of each stored goal score; sites are ranked on these

GOALS = {
    "lighting": ("light", "bare"),
    "shadows": ("light", "terrain", "bare"),
    "geology": ("rock", "terrain", "bare"),
    "full": ("light", "terrain", "rock", "bare"),
}

# Which hours figure of a grazing record the light score is read from.
# North: snow-free hours, with the terrain ("open") or over a flat horizon.
# South: the snow is not measured, so the hours of 27 November to 1 March, when the rock maps show bare ground.
LIGHT_HOURS = {
    ("N", "open"): "long_open_hours",
    ("N", "flat"): "long_snow_free_hours",
    ("S", "open"): "long_summer_rock_open_hours",
    ("S", "flat"): "long_summer_rock_hours",
}

SNOW_REASONS = {"doubtful": "snow doubtful", "no data": "no snow data"}
TILE_NOT_FETCHED = "tile not fetched"   # how a horizon or terrain record held back for a missing elevation tile begins


def light_score(long_hours: float | None, full_hours: float = FULL_HOURS) -> float | None:
    """Long-window grazing hours as a share of full marks, capped at 1; None when the hours are unknown."""
    if long_hours is None:
        return None
    return min(1.0, max(0.0, long_hours) / full_hours)


def terrain_score(overlap: float | None, self_overlap_median: float | None) -> float | None:
    """A cell's slope overlap with a lunar site, against what a 10 km piece of that site reaches on itself.

    A piece of the Moon does not overlap its own site perfectly, so the raw
    overlap can never reach 1; this puts "as alike as the site is to itself" at 1.
    """
    if overlap is None or not self_overlap_median:
        return None
    return min(1.0, max(0.0, overlap) / self_overlap_median)


def light_hours(target_values: dict, hemisphere: str, basis: str = "open") -> float | None:
    """The hours a cell's light score is read from; basis "open" uses the terrain, "flat" a flat horizon."""
    if (hemisphere, basis) not in LIGHT_HOURS:
        raise ValueError(f"unknown hemisphere or basis: {hemisphere!r}, {basis!r}")
    return target_values.get(LIGHT_HOURS[(hemisphere, basis)])


def clear_hours(hours_by_bin, clear_share_by_bin, bins=None) -> float | None:
    """Hours times the typical clear share of the sky, summed over the ten-day bins (those in bins, if given).

    A displayed column only: it enters no factor and no goal. None when it cannot
    be known: no hours or no cloud figure at all, an unknown bin of hours among
    those counted, or hours in a counted bin whose cloud figure is unknown. A
    counted bin without hours adds nothing, whatever its cloud. Not rounded.
    """
    if hours_by_bin is None or clear_share_by_bin is None:
        return None
    hours = [float(h) for h in hours_by_bin]
    share = [None if s is None or math.isnan(float(s)) else float(s) for s in clear_share_by_bin]
    if len(hours) != len(share):
        raise ValueError(f"{len(hours)} bins of hours against {len(share)} bins of cloud")
    if all(math.isnan(h) for h in hours) or all(s is None for s in share):
        return None
    total = 0.0
    for b in (range(len(hours)) if bins is None else bins):
        if math.isnan(hours[b]):
            return None
        if hours[b] == 0.0:
            continue
        if share[b] is None:
            return None
        total += hours[b] * share[b]
    return total


def geometric_mean(values) -> float:
    """Geometric mean; any zero (or missing) factor gives zero."""
    values = list(values)
    if not values or any(v is None or v <= 0.0 for v in values):
        return 0.0
    return math.exp(sum(math.log(v) for v in values) / len(values))


def goal_scores(scores: dict) -> dict:
    """Each goal's geometric mean of its factors; None when one of its factors is unknown."""
    out = {}
    for goal, factors in GOALS.items():
        values = [scores.get(f) for f in factors]
        out[goal] = None if any(v is None for v in values) else geometric_mean(values)
    return out


def rounded_factors(scores: dict) -> dict:
    """The factor scores as they are stored: FACTOR_DIGITS decimals, unknown stays None."""
    return {name: None if value is None else round(value, FACTOR_DIGITS) for name, value in scores.items()}


def published_goals(scores: dict) -> dict:
    """The goal scores as they are stored and ranked: made from the stored factors, GOAL_DIGITS decimals.

    Every table and every check goes through here, so a score can be rebuilt
    from the factors in cells_scored.json and two scripts never order the
    same cells differently because one of them rounded later.
    """
    return {goal: None if value is None else round(value, GOAL_DIGITS)
            for goal, value in goal_scores(rounded_factors(scores)).items()}


def not_ranked_because(cell: dict, min_bare: float = RANK_MIN_BARE, need_horizon: bool = True) -> list[str]:
    """Why a cell is left out of the ranking, in plain words; an empty list means it is ranked.

    Works on a record of grazing_cells.json. Southern cells are never held
    back by their snow: it is unmeasured for all of them and they are ranked
    on their own. need_horizon=False is for flat-horizon counts only.
    """
    reasons = []
    if not cell.get("gridded", True):
        reasons.append("named-site cell outside the screen")
    snow_reason = SNOW_REASONS.get(cell["snow"]["status"])
    if snow_reason:
        reasons.append(snow_reason)
    if need_horizon:
        horizon = cell.get("horizon")
        if horizon is None:
            reasons.append("no horizon")
        elif "skipped" in horizon:
            why = str(horizon["skipped"])
            if "antimeridian" in why.lower():
                reasons.append("window across the antimeridian")
            elif why.startswith(TILE_NOT_FETCHED):
                reasons.append(f"no horizon: {TILE_NOT_FETCHED}")   # the stored text names the tile; the reason is one
            else:
                reasons.append(f"no horizon: {why}")
    if cell.get("bare") is None:
        reasons.append("bare unknown")
    elif cell["bare"] < min_bare:
        reasons.append(f"bare under {min_bare:g}")
    return reasons


def cluster_sites(cells: list[dict], key, min_separation_km: float = SAME_SITE_KM,
                  limit: int | None = None, tie_key=None) -> list[dict]:
    """Best-scoring cells, skipping any within min_separation_km of a better one already kept.

    With a limit the search stops once that many sites are found; the sites are the same, only fewer.
    Equal scores keep the order given, unless tie_key says which of them comes first (the larger value).
    """
    sites: list[dict] = []
    order = key if tie_key is None else (lambda c: (key(c), tie_key(c)))
    for cell in sorted(cells, key=order, reverse=True):
        if key(cell) <= 0.0 or (limit is not None and len(sites) >= limit):
            break
        if all(reference.haversine_km(cell["lat"], cell["lon"], s["lat"], s["lon"]) >= min_separation_km
               for s in sites):
            sites.append(cell)
    return sites


def top_sites(cells: list[dict], key, top: int = 10, min_separation_km: float = SAME_SITE_KM,
              tie_key=None) -> list[dict]:
    """The best sites among the cells whose score is known; cells scoring None are left out, not ranked last.

    tie_key orders cells whose scores are equal (larger first); the light score stops at full marks,
    so without it many cells with different hours would be ranked by their place in the file.
    """
    return cluster_sites([c for c in cells if key(c) is not None], key, min_separation_km, limit=top, tie_key=tie_key)


def tie_hours(target_values: dict, hemisphere: str, basis: str = "open") -> float:
    """What orders cells with equal scores: the long-window hours behind the light score, uncapped; unknown counts as none."""
    return light_hours(target_values, hemisphere, basis) or 0.0


def survivors(baseline: list[dict], variant: list[dict], same_site_km: float = SAME_SITE_KM) -> int:
    """How many baseline sites still have a site within same_site_km of them in the variant list."""
    return sum(any(reference.haversine_km(b["lat"], b["lon"], v["lat"], v["lon"]) < same_site_km for v in variant)
               for b in baseline)

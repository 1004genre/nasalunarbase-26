# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Lookups against the hand-compiled lists of known analog sites and anorthosite bodies."""
from __future__ import annotations

import math

EARTH_RADIUS_KM = 6371.0
LUNAR_AN = 96.0       # mid feldspar calcium number of lunar highland anorthosite (94 to 98)
AN_SPAN = 50.0        # a body this many An units below the Moon scores zero
UNKNOWN_AN_SCORE = 0.5


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def nearest_known(lat: float, lon: float, sites: list[dict], max_km: float = 50.0) -> dict | None:
    """The closest known analog site within max_km, with its distance, else None."""
    best = None
    for site in sites:
        d = haversine_km(lat, lon, site["lat"], site["lon"])
        if d <= max_km and (best is None or d < best["distance_km"]):
            best = {"name": site["name"], "tier": site.get("tier"), "body": site.get("body"),
                    "distance_km": d}
    return best


def an_score(body: dict) -> float:
    """How close a body's feldspar chemistry is to lunar highland rock, 0 to 1."""
    lo, hi = body.get("an_low"), body.get("an_high")
    if lo is None or hi is None:
        return UNKNOWN_AN_SCORE
    return max(0.0, min(1.0, 1.0 - (LUNAR_AN - (lo + hi) / 2.0) / AN_SPAN))


def rock_match(lat: float, lon: float, bodies: list[dict], margin_km: float = 0.0) -> tuple[float, str | None]:
    """Best rock score among anorthosite bodies whose radius (plus margin) reaches the point."""
    best_score, best_name = 0.0, None
    for body in bodies:
        if haversine_km(lat, lon, body["lat"], body["lon"]) <= body["radius_km"] + margin_km:
            s = an_score(body)
            if best_name is None or s > best_score:
                best_score, best_name = s, body["name"]
    return best_score, best_name

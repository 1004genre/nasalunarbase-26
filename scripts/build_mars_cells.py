"""Mars part, scores: join the site list, the slopes and the climate, score every bare half-degree Earth
square against every Mars site, and write

    data/derived/mars_sites.json       one card per Mars site
    data/derived/mars_cells.json       every square with at least 15 % bare ground, scored per site
    data/derived/mars_validation.json  where the known Mars analog sites come out, and a test of the ranking
    data/derived/MARS-RESULTS.md       the plain-words summary

(plan docs/superpowers/plans/2026-11-14-mars-part.md). No network. Run from the project root:
    uv run python scripts/build_mars_cells.py
"""
from __future__ import annotations

import bisect
import datetime as dt
import json
import math
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from twinfinder import mars_climate as mc  # noqa: E402
from twinfinder import mars_score as ms  # noqa: E402
from twinfinder.mars_terrain import histogram_overlap  # noqa: E402

DERIVED = ROOT / "data" / "derived"
SITES_BASE = DERIVED / "mars_sites_base.json"
TERRAIN = DERIVED / "mars_terrain.json"
CLIMATE = DERIVED / "mars_climate.json"
ANALOGS = ROOT / "data" / "reference" / "known_analogs.json"
OUT_SITES = DERIVED / "mars_sites.json"
OUT_CELLS = DERIVED / "mars_cells.json"
OUT_VALIDATION = DERIVED / "mars_validation.json"
OUT_MD = DERIVED / "MARS-RESULTS.md"

MIN_BARE = 0.15
N_BEST = 10
N_CONTROLS = 2000
FACTOR_DIGITS = 4
GOAL_DIGITS = 4
GOAL_NAMES = tuple(ms.GOALS)
ZERO = f"+{ms.COLD_ZERO_C:g} °C"                 # the cold scale's zero point, as printed in MARS-RESULTS.md
PREVIOUS_ZERO = f"+{ms.PREVIOUS_COLD_ZERO_C:g} °C"

# The agreed words for the slope baseline (coordinator's decision 3 of 14 Nov 2026), used in every output.
BASELINE_SHORT = "heights every 1.85 km, slopes across about 3.7 km"
FIRST_PASS = f"first pass: squares of 0.5 degree (about 55 km), {BASELINE_SHORT} on both planets; coarser than the Moon part"

# Curiosity's figures come from NASA's public weather feed, which says it is for outreach (decision 3).
CURIOSITY_CITE = ("Curiosity's weather figures are from NASA's public weather feed, which says it is for outreach; "
                  "they are not archive data.")
SOURCES = {
    "data/derived/mars_sites_base.json": "the Mars sites (agent MARS-SITES)",
    "data/derived/mars_terrain.json": "slopes of the sites and of the Earth squares (agent MARS-TERRAIN): "
                                      "MOLA MEGDR and ETOPO 2022",
    "data/derived/mars_climate.json": "Sun, climate and the cannot-match list of the sites; climate and bare "
                                      "ground of the Earth squares (agent MARS-CLIMATE): NASA POWER (MERRA-2), "
                                      "ESA WorldCover 2021, Mars Climate Database, Phoenix MET data from NASA's PDS "
                                      "archive, and Curiosity REMS figures from NASA's public weather feed, which says "
                                      "it is for outreach, not archive data",
}

# The known analog sites the job names, and the entry of data/reference/known_analogs.json that stands for each.
REQUIRED = {
    "Atacama near Yungay": "Yungay (Atacama hyperarid core)",
    "McMurdo Dry Valleys": "McMurdo Dry Valleys",
    "Haughton crater": "Haughton impact structure, Devon Island",
    "Mojave": "Mojave Desert",
    "Utah desert station near Hanksville": "Mars Desert Research Station (MDRS), Hanksville",
    "Iceland's highlands": "Askja",
    "Rio Tinto": "Rio Tinto",
    "Qaidam Basin": "Qaidam Basin (incl. Dalangtan)",
    "Pilbara": "Pilbara stromatolites",
    "Dhofar in Oman": "Dhofar desert (AMADEE-18)",
    "Lanzarote": "Lanzarote (Timanfaya, Corona lava tube)",
    "Svalbard": "Svalbard (AMASE)",
}

# ---- plain region names ------------------------------------------------------------------------------
# (name, group, south, north, west, east, lowest mean height m, highest mean height m); the first box that holds
# the point wins. A height limit uses the square's mean land height from mars_terrain.json and fails when that is
# unknown. Rough reading aids for the tables, not geography: boxes are rectangles and cut across coasts and borders.
REGION_BOXES = [
    ("McMurdo Dry Valleys", "polar desert", -78.2, -76.8, 160.0, 164.5, None, None),
    ("Transantarctic Mountains", "polar desert", -90.0, -78.6, 150.0, 180.0, None, None),
    ("Transantarctic Mountains", "polar desert", -90.0, -83.0, -180.0, -85.0, None, None),
    ("Transantarctic Mountains", "polar desert", -86.0, -82.0, -70.0, -40.0, None, None),
    ("Victoria Land", "polar desert", -78.6, -70.0, 154.0, 172.0, None, None),
    ("Antarctic Peninsula", "polar desert", -75.0, -60.0, -80.0, -53.0, None, None),
    ("Antarctica", "polar desert", -90.0, -60.0, -180.0, 180.0, None, None),
    ("Svalbard", "polar desert", 76.0, 81.0, 10.0, 35.0, None, None),
    ("Russian High Arctic", "polar desert", 73.5, 82.0, 45.0, 160.0, None, None),
    ("Ellesmere or north-west Greenland", "polar desert", 76.0, 84.0, -73.0, -61.0, None, None),
    ("Canadian High Arctic", "polar desert", 72.0, 76.0, -125.0, -68.0, None, None),
    ("Canadian High Arctic", "polar desert", 76.0, 84.0, -125.0, -73.0, None, None),
    ("Iceland", "other", 63.0, 67.0, -25.0, -13.0, None, None),
    ("Greenland", "polar desert", 72.0, 84.0, -75.0, -10.0, None, None),
    ("Greenland", "other", 59.5, 72.0, -60.0, -10.0, None, None),
    ("Atacama Desert", "great desert", -30.0, -17.5, -71.6, -68.0, None, 3500.0),
    ("Altiplano and Puna", "high plateau", -30.0, -14.0, -71.6, -64.5, 3000.0, None),
    ("Patagonian Desert", "great desert", -52.0, -38.0, -71.0, -63.0, None, None),
    ("Namib Desert", "great desert", -29.0, -14.0, 11.5, 15.5, None, None),
    ("Kalahari", "great desert", -28.0, -18.0, 18.0, 26.0, None, None),
    ("Canary Islands", "other", 27.5, 29.5, -18.5, -13.3, None, None),
    ("Sinai, Negev and Wadi Rum", "great desert", 28.0, 31.5, 32.5, 35.6, None, None),
    ("Sahara", "great desert", 15.0, 22.0, -17.5, 37.0, None, None),
    ("Sahara", "great desert", 22.0, 26.0, -17.5, 35.5, None, None),
    ("Sahara", "great desert", 26.0, 32.0, -17.5, 33.8, None, None),
    ("Danakil Depression", "great desert", 11.5, 15.5, 39.6, 42.5, None, None),
    ("Ethiopian Highlands", "high plateau", 5.0, 15.0, 35.0, 40.5, None, None),
    ("Horn of Africa deserts", "great desert", -1.0, 12.0, 40.5, 52.0, None, None),
    ("Iranian deserts (Lut, Kavir)", "great desert", 29.0, 36.5, 51.5, 60.5, None, None),
    ("Arabian Desert", "great desert", 12.0, 32.0, 34.0, 60.0, None, None),
    ("Syrian Desert", "great desert", 32.0, 37.0, 36.0, 44.0, None, None),
    ("Thar Desert", "great desert", 24.0, 30.5, 69.0, 76.0, None, None),
    ("Karakum and Kyzylkum", "great desert", 37.0, 46.0, 52.0, 68.0, None, None),
    ("Pamir and Karakoram", "high plateau", 34.5, 40.0, 70.0, 78.0, None, None),
    ("Qaidam Basin", "high plateau", 35.5, 39.5, 90.0, 99.0, None, 3500.0),
    ("Tibetan Plateau", "high plateau", 27.5, 39.5, 75.0, 103.0, 3000.0, None),
    ("Taklamakan and Tarim Basin", "great desert", 36.0, 42.5, 75.0, 92.0, None, None),
    ("Gobi Desert", "great desert", 37.0, 46.0, 92.0, 115.0, None, None),
    ("Colorado Plateau", "high plateau", 35.0, 40.5, -112.5, -106.5, None, None),
    ("North American deserts", "great desert", 23.0, 43.0, -121.0, -101.0, None, None),
    ("Australian deserts", "great desert", -32.0, -19.0, 113.0, 142.0, None, None),
]


def region(lat: float, lon: float, elev_m: float | None = None) -> tuple[str, str]:
    for name, group, south, north, west, east, low, high in REGION_BOXES:
        if not (south <= lat <= north and west <= lon <= east):
            continue
        if (low is not None or high is not None) and elev_m is None:
            continue
        if low is not None and elev_m < low:
            continue
        if high is not None and elev_m > high:
            continue
        return name, group
    return "other", "other"


def touching_squares(lat: float, lon: float) -> list[str]:
    """Ids of every half-degree square whose closed box holds the point: 1, or 2 on an edge, or 4 at a corner."""
    def centres(x):
        lo = math.floor(x / 0.5 + 1e-9) * 0.5
        out = [lo + 0.25]
        if on_square_edge(x):
            out.insert(0, lo - 0.25)
        return out
    ids = []
    for la in centres(lat):
        for lo in centres(lon):
            lo = lo - 360.0 if lo >= 180.0 else lo + 360.0 if lo < -180.0 else lo
            ids.append(mc.square_id(round(la, 2), round(lo, 2)))
    return ids


def neighbours(lat_c: float, lon_c: float) -> list[str]:
    """The eight squares around a square centre."""
    out = []
    for dy in (-0.5, 0.0, 0.5):
        for dx in (-0.5, 0.0, 0.5):
            if dy or dx:
                lo = lon_c + dx
                lo = lo - 360.0 if lo >= 180.0 else lo + 360.0 if lo < -180.0 else lo
                out.append(mc.square_id(round(lat_c + dy, 2), round(lo, 2)))
    return out


def known_sets(records) -> tuple[list[str], list[str]]:
    """Distinct squares of the known sites: all with climate data, and those with at least 15 % bare ground."""
    return (sorted({r["square"] for r in records if r["in_climate"]}),
            sorted({r["square"] for r in records if r["ranked"]}))


# ---- plain words -------------------------------------------------------------------------------------

def long_sentences(text: str, max_words: int = 25) -> list[str]:
    """Sentences of prose (not table rows, headings or code) with more than max_words words."""
    out, code = [], False
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("```"):
            code = not code
            continue
        if code or not s or s.startswith("|") or s.startswith("#"):
            continue
        s = re.sub(r"^(-|\d+\.)\s+", "", s)
        for sentence in re.split(r"(?<=[.!?:;])\s+", s):
            if len(sentence.split()) > max_words:
                out.append(sentence)
    return out


SALES_WORDS = ("perfect", "ideal", "unique", "unrivalled", "unparalleled", "world-class", "cutting-edge",
               "groundbreaking", "revolutionary", "stunning", "remarkable", "exceptional", "best-in-class")


def sales_words(text: str) -> list[str]:
    low = text.lower()
    return [w for w in SALES_WORDS if re.search(rf"\b{re.escape(w)}\b", low)]


# The two caveats every place that shows a Mars score must carry (MARS-REVIEW, kept by decision 3).
SCORE_CAVEATS = ("Caveats: it is not a climate match, and a score is a position on each factor's own scale, "
                 "not a share of likeness.")
# A block (the text under one heading) shows a score if it holds one of these.
SCORE_MARKERS = ("| Score |", "score (percentile", "Highest full", "with a score of")


def blocks_missing_caveats(text: str) -> list[str]:
    """Headings of the blocks that show a Mars score but lack either caveat."""
    blocks, head, body = [], "", []
    for line in text.splitlines():
        if line.startswith("#"):
            blocks.append((head, "\n".join(body)))
            head, body = line.strip(), []
        else:
            body.append(line)
    blocks.append((head, "\n".join(body)))
    return [h for h, b in blocks
            if any(m in b for m in SCORE_MARKERS)
            and not ("not a climate match" in b and "not a share of likeness" in b)]


# ---- helpers -----------------------------------------------------------------------------------------

def rnd(x, digits):
    return None if x is None else round(float(x), digits)


def id_lat_lon(square: str) -> tuple[float, float]:
    _, lat, lon = square.split("_")
    return float(lat), float(lon)


def load(path: Path):
    with open(path) as f:
        return json.load(f)


def write_json(path: Path, obj) -> None:
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w") as f:
        json.dump(obj, f, separators=(",", ":"), ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)


def write_text(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text)
    os.replace(tmp, path)


# ---- the site cards ----------------------------------------------------------------------------------

FEED_FIELD_WORDS = {"pressure_pa": "pressure", "warm_season_daily_max_c": "warm-season daily maximum",
                    "cold_season_daily_min_c": "cold-season daily minimum", "annual_mean_c": "yearly mean"}


def feed_fields(card: dict) -> list[str]:
    """The site's measured climate fields that come from NASA's public weather feed."""
    cl = card.get("climate") or {}
    kinds, srcs = cl.get("kind_by_field") or {}, cl.get("source_by_field") or {}
    return [f for f, k in kinds.items()
            if k and k.startswith("measured") and "weather feed" in (srcs.get(f) or "")]


def feed_citation_line(cards) -> str | None:
    """A sentence naming the figures from the weather feed, and how to cite them."""
    parts = [f"{short_name(c)} ({', '.join(FEED_FIELD_WORDS.get(f, f) for f in feed_fields(c))})"
             for c in cards if feed_fields(c)]
    if not parts:
        return None
    return f"The measured figures at {', '.join(parts)} are Curiosity's. {CURIOSITY_CITE}"


def site_cards(sites_base: dict, terrain: dict, climate: dict) -> list[dict]:
    cards = []
    for s in sites_base["sites"]:
        sid = s["id"]
        t = terrain["sites"][sid]
        c = climate["sites"][sid]
        cl = c["climate"]
        cards.append({
            "id": sid, "name": s["name"], "kind": s["kind"], "why": s["why"],
            "lat": s["lat"], "lon_east": s["lon_east"], "sources": s["sources"],
            # Second pass (15 Nov 2026): the lists that name the site, and the 2015 workshop abstracts of its zone.
            "lists": list(s.get("lists") or []),
            "exploration_zone_abstracts": s.get("exploration_zone_abstracts"),
            "position_kind": s.get("position_kind"),
            "sun": c["sun"],
            "landscape": {k: t.get(k) for k in ("median_slope_deg", "p90_slope_deg", "relief_m", "self_overlap",
                                                 "pixels", "slope_hist")},
            "climate": {k: cl.get(k) for k in ("annual_mean_c", "warm_season_daily_max_c", "cold_season_daily_min_c",
                                                "pressure_pa", "kind", "kind_by_field", "source", "source_by_field",
                                                "url", "urls")},
            "cannot_match": c.get("cannot_match", []),
        })
        cards[-1]["climate"]["citation_note"] = CURIOSITY_CITE if feed_fields(cards[-1]) else None
    return cards


def _site_range(card: dict):
    sun = card["sun"]
    lo, hi = sun.get("noon_elev_min_deg"), sun.get("noon_elev_max_deg")
    return None if lo is None or hi is None else (lo, hi)


def score_square(square: str, card: dict, tcell: dict | None, ccell: dict | None, with_months: bool = True,
                 cold_zero_c: float = ms.COLD_ZERO_C) -> dict:
    """Factors, goals, best months and shortfalls of one square against one site.

    cold_zero_c other than ms.COLD_ZERO_C is used only to report the first pass's scale (with_months False)."""
    lat, _ = id_lat_lon(square)
    site_t = card["climate"]["annual_mean_c"]
    site_range = _site_range(card)
    overlap = None if tcell is None else histogram_overlap(tcell.get("slope_hist"), card["landscape"]["slope_hist"])
    f = {
        "terrain": ms.terrain_score(overlap, card["landscape"]["self_overlap"]),
        "dry": ms.dry_score(None if ccell is None else ccell.get("precip_mm_year")),
        "cold": ms.cold_score(None if ccell is None else ccell.get("t2m_year_c"), site_t, zero_c=cold_zero_c),
        "bare": ms.bare_score(None if ccell is None else ccell.get("bare")),
        "sun": ms.sun_score(site_range, ms.earth_noon_range(lat)),
    }
    f = {k: rnd(v, FACTOR_DIGITS) for k, v in f.items()}
    g = {k: rnd(v, GOAL_DIGITS) for k, v in ms.goals(f).items()}
    out = {**f, **g, "slope_overlap": rnd(overlap, FACTOR_DIGITS)}
    if with_months:
        months = (None if ccell is None else
                  ms.month_scores(ccell.get("t2m_c"), ccell.get("precip_mm"), lat, site_t, site_range))
        out["best_months"] = ms.best_months(months)
        short = ms.falls_short(None if ccell is None else ccell.get("t2m_year_c"), site_t,
                               None if ccell is None else ccell.get("precip_mm_year"),
                               None if ccell is None else ccell.get("pressure_kpa"),
                               card["climate"]["pressure_pa"])
        out["falls_short"] = {"colder_on_mars_by_c": rnd(short["colder_on_mars_by_c"], 1),
                              "times_wetter_than_25_mm": rnd(short["times_wetter_than_25_mm"], 2),
                              "pressure_mars_over_square": rnd(short["pressure_mars_over_square"], 5)}
    return out


def square_base(square: str, tcell: dict | None, ccell: dict | None) -> dict:
    lat, lon = id_lat_lon(square)
    name, group = region(lat, lon, None if tcell is None else tcell.get("elev_mean_m"))
    land = None if ccell is None else ccell.get("land_share")
    bare = None if ccell is None else ccell.get("bare")
    km2 = None if land is None or bare is None else bare * land * mc.square_km2(lat)
    return {
        "id": square, "lat": lat, "lon": lon, "region": name, "region_group": group,
        "land_share": land, "bare": bare, "bare_source": None if ccell is None else ccell.get("bare_source"),
        "bare_km2": rnd(km2, 1),
        "t2m_year_c": None if ccell is None else ccell.get("t2m_year_c"),
        "precip_mm_year": None if ccell is None else ccell.get("precip_mm_year"),
        "pressure_kpa": None if ccell is None else ccell.get("pressure_kpa"),
        "elev_mean_m": None if tcell is None else tcell.get("elev_mean_m"),
        "median_slope_deg": None if tcell is None else tcell.get("median_slope_deg"),
    }


def score_cells(cards: list[dict], terrain: dict, climate: dict) -> tuple[dict, dict]:
    tcells, ccells = terrain["cells"], climate["cells"]
    cells = {}
    for square, ccell in ccells.items():
        bare = ccell.get("bare")
        if bare is None or bare < MIN_BARE:
            continue
        tcell = tcells.get(square)
        rec = square_base(square, tcell, ccell)
        rec["sites"] = {card["id"]: score_square(square, card, tcell, ccell) for card in cards}
        cells[square] = rec
    t_ids, c_ids = set(tcells), set(ccells)
    counts = {
        "squares_in_terrain": len(t_ids), "squares_in_climate": len(c_ids),
        "squares_in_both": len(t_ids & c_ids),
        "squares_in_terrain_only": len(t_ids - c_ids), "squares_in_climate_only": len(c_ids - t_ids),
        "squares_with_bare_unknown": sum(1 for c in ccells.values() if c.get("bare") is None),
        "squares_kept_bare_at_least_0.15": len(cells),
        "kept_squares_without_slopes": sum(1 for s in cells if s not in tcells),
        "kept_squares_yearly_mean_15c_or_more": sum(1 for c in cells.values()
                                                    if c["t2m_year_c"] is not None and c["t2m_year_c"] >= 15.0),
        "kept_squares_at_cold_zero_or_warmer": sum(1 for c in cells.values()
                                                   if c["t2m_year_c"] is not None and c["t2m_year_c"] >= ms.COLD_ZERO_C),
        "kept_squares_precip_25_mm_or_less": sum(1 for c in cells.values()
                                                 if c["precip_mm_year"] is not None and c["precip_mm_year"] <= ms.DRY_FULL_MM),
    }
    return cells, counts


# ---- the best places ---------------------------------------------------------------------------------

def best_places(cells: dict, cards: list[dict], climate: dict) -> dict:
    out = {}
    for card in cards:
        sid = card["id"]
        out[sid] = {}
        for goal in GOAL_NAMES:
            rows = [{"id": c["id"], "lat": c["lat"], "lon": c["lon"], "score": c["sites"][sid][goal],
                     "tie": c["sites"][sid]["slope_overlap"], "km2": c["bare_km2"],
                     "env": c["sites"][sid]["environment"]} for c in cells.values()]
            # landscape ties (8 to 410 squares at 1.000): by bare area, then environment (decision 2)
            tie = ("km2", "env") if goal == "landscape" else "tie"
            picked = ms.pick_best(rows, "score", n=N_BEST, min_km=ms.SAME_PLACE_KM, tie=tie)
            all_scores = [r["score"] for r in rows]
            places = []
            for rank, r in enumerate(picked, start=1):
                c = cells[r["id"]]
                ccell = climate["cells"][r["id"]]
                months = ms.month_scores(ccell.get("t2m_c"), ccell.get("precip_mm"), c["lat"],
                                         card["climate"]["annual_mean_c"], _site_range(card))
                places.append({
                    "rank": rank, "id": c["id"], "lat": c["lat"], "lon": c["lon"], "region": c["region"],
                    "region_group": c["region_group"], "score": r["score"],
                    "scores": {k: c["sites"][sid][k] for k in ms.FACTORS + GOAL_NAMES + ("slope_overlap",)},
                    "best_months": c["sites"][sid]["best_months"],
                    "month_scores": None if months is None else [rnd(v, 3) for v in months],
                    "falls_short": c["sites"][sid]["falls_short"],
                    "bare": c["bare"], "t2m_year_c": c["t2m_year_c"], "precip_mm_year": c["precip_mm_year"],
                    "pressure_kpa": c["pressure_kpa"], "elev_mean_m": c["elev_mean_m"],
                    "median_slope_deg": c["median_slope_deg"],
                    "bare_km2": c["bare_km2"],
                    "squares_with_this_score": ms.count_at(all_scores, r["score"]),
                })
            out[sid][goal] = places
    return out


def tied_at_top(best: dict) -> dict:
    """Per site and goal: how many ranked squares share the top score of the list."""
    return {sid: {goal: (places[0]["squares_with_this_score"] if places else 0) for goal, places in goals.items()}
            for sid, goals in best.items()}


def factor_summary(cells: dict, cards: list[dict]) -> dict:
    """Per site: the highest value of each factor among the kept squares, where, and how many squares reach 1."""
    out = {}
    for card in cards:
        sid = card["id"]
        s = {}
        for k in ms.FACTORS + GOAL_NAMES:
            vals = [(c["sites"][sid][k], c["id"]) for c in cells.values() if c["sites"][sid][k] is not None]
            if not vals:
                s[k] = {"highest": None, "where": None, "squares_at_1": 0, "squares_known": 0}
                continue
            best = max(vals, key=lambda x: (x[0], [-ord(ch) for ch in x[1]]))
            s[k] = {"highest": best[0], "where": best[1], "squares_at_1": sum(1 for v, _ in vals if v >= 1.0),
                    "squares_known": len(vals)}
        cold_sq = s["cold"]["where"]
        s["coldest_square"] = None if cold_sq is None else {
            "id": cold_sq, "region": cells[cold_sq]["region"], "t2m_year_c": cells[cold_sq]["t2m_year_c"],
            "colder_on_mars_by_c": cells[cold_sq]["sites"][sid]["falls_short"]["colder_on_mars_by_c"]}
        out[sid] = s
    return out


# ---- validation --------------------------------------------------------------------------------------

def on_square_edge(x: float) -> bool:
    return abs(x * 2 - round(x * 2)) < 1e-9


def validation(cells: dict, cards: list[dict], terrain: dict, climate: dict, analogs: list[dict]) -> dict:
    tcells, ccells = terrain["cells"], climate["cells"]
    mars = [a for a in analogs if a.get("body") in ("Mars", "both")]
    names = {a["name"] for a in mars}
    missing = [k for k, v in REQUIRED.items() if v not in names]
    if missing:
        raise SystemExit(f"known_analogs.json lacks the job's sites: {missing}")
    named = {v: k for k, v in REQUIRED.items()}

    ranked_sorted = {card["id"]: {g: sorted(c["sites"][card["id"]][g] for c in cells.values()
                                            if c["sites"][card["id"]][g] is not None) for g in GOAL_NAMES}
                     for card in cards}

    def rank_of(value, pop):
        if value is None:
            return None
        return len(pop) - bisect.bisect_right(pop, value) + 1

    def goals_only(square):
        tc, cc = tcells.get(square), ccells.get(square)
        out = {"square": square, "in_climate": cc is not None, "ranked": square in cells,
               "bare": None if cc is None else cc.get("bare"),
               "land_share": None if cc is None else cc.get("land_share"), "sites": {}}
        for card in cards:
            sc = score_square(square, card, tc, cc, with_months=False)
            out["sites"][card["id"]] = {g: sc[g] for g in GOAL_NAMES}
        return out

    sites_out = []
    for a in mars:
        lat_c, lon_c = mc.square_of(a["lat"], a["lon"])
        square = mc.square_id(lat_c, lon_c)
        touching = touching_squares(a["lat"], a["lon"])
        ccell, tcell = ccells.get(square), tcells.get(square)
        base = square_base(square, tcell, ccell)
        rec = {
            "name": a["name"], "named_in_job": named.get(a["name"]), "country": a["country"],
            "lat": a["lat"], "lon": a["lon"], "body": a["body"], "tier": a["tier"],
            "coord_quality": a["coord_quality"], "source_url": a["source_url"], "analog_for": a["analog_for"],
            "square": square, "on_square_edge": on_square_edge(a["lat"]) or on_square_edge(a["lon"]),
            "in_climate": ccell is not None, "in_terrain": tcell is not None,
            "ranked": square in cells,
            "other_squares_at_the_point": [goals_only(q) for q in touching
                                           if q != square],
            "neighbours_with_data": ([] if ccell is not None else
                                     [goals_only(q) for q in neighbours(lat_c, lon_c)
                                      if q in ccells and q not in touching]),
            **{k: base[k] for k in ("region", "region_group", "land_share", "bare", "bare_source", "t2m_year_c",
                                    "precip_mm_year", "pressure_kpa", "elev_mean_m", "median_slope_deg")},
            "sites": {},
        }
        for card in cards:
            sc = score_square(square, card, tcell, ccell)
            sc["percentile"] = {g: rnd(ms.percentile(sc[g], ranked_sorted[card["id"]][g]), 1) for g in GOAL_NAMES}
            sc["rank_among_kept"] = {g: rank_of(sc[g], ranked_sorted[card["id"]][g]) for g in GOAL_NAMES}
            rec["sites"][card["id"]] = sc
        sites_out.append(rec)

    # the test of the ranking: distinct known squares against controls drawn by the sha1 of their id
    known_squares, known_bare = known_sets(sites_out)
    all_land = sorted(ccells)
    controls_land = ms.control_ids(all_land, N_CONTROLS, exclude=set(known_squares))
    controls_bare = ms.control_ids(sorted(cells), N_CONTROLS, exclude=set(known_squares))

    def scores_for(squares, card, zero_c):
        return [score_square(s, card, tcells.get(s), ccells.get(s), with_months=False, cold_zero_c=zero_c)
                for s in squares]

    def test(known, controls, zero_c=ms.COLD_ZERO_C):
        res = {}
        for card in cards:
            k = scores_for(known, card, zero_c)
            c = scores_for(controls, card, zero_c)
            res[card["id"]] = {}
            for key in GOAL_NAMES + ms.FACTORS:
                kv = [x[key] for x in k if x[key] is not None]
                cv = [x[key] for x in c if x[key] is not None]
                res[card["id"]][key] = {"auc": rnd(ms.auc(kv, cv), 3), "known": len(kv), "controls": len(cv)}
        return res

    return {
        "meta": {
            "what": "Where the known Mars analog sites of data/reference/known_analogs.json come out in the Mars "
                    "part's scores, and one test of the ranking. A first pass: half-degree squares (about 55 km), "
                    f"{BASELINE_SHORT}.",
            "cold_zero_c": ms.COLD_ZERO_C,
            "made": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
            "made_by": "agent MARS-SCORE, scripts/build_mars_cells.py",
            "which_entries": "every entry with body 'Mars' or 'both' (the file marks the body in the field 'body': "
                             "'Mars', 'Moon' or 'both')",
            "entries": len(sites_out),
            "named_in_job": REQUIRED,
            "square_rule": "the half-degree square that holds the entry's point (twinfinder.mars_climate.square_of); "
                           "a point on a square edge goes to the square to its north and east",
            "percentile": "percent of the kept squares (bare >= 0.15) with a lower goal score, ties counting one "
                          "half; 100 means no kept square scores higher",
            "rank_among_kept": "1 + the number of kept squares with a higher goal score",
            "scores_outside_kept": "a known site whose square has under 15 % bare ground is scored all the same "
                                   "(ranked false); its percentile says where its score would fall",
            "test": {
                "how": "area under the curve (AUC): the share of (known square, control square) pairs in which the "
                       "known square scores higher, ties counting one half; 0.5 is no better than chance, 1 means "
                       "every known square outranks every control",
                "known": "distinct squares of the Mars and both entries that have climate data; a square holding "
                         "several entries (such as the Dry Valleys) counts once",
                "known_squares": len(known_squares), "known_squares_bare_at_least_0.15": len(known_bare),
                "controls_all_land": f"the {N_CONTROLS} squares of mars_climate.json (all squares with at least "
                                     "20 % land) with the lowest sha1 of their id, known squares left out",
                "controls_bare": f"the {N_CONTROLS} kept squares (bare >= 0.15) with the lowest sha1 of their id, "
                                 "known squares left out; tested against the known squares that are kept themselves "
                                 "(an extra, harder test beyond the plan)",
                "other_squares_at_the_point": "for a point on a square edge or corner, the other squares that touch "
                                              "it, with their goals; not used in the test",
                "neighbours_with_data": "for a point whose own square has no climate data, the eight squares "
                                        "around it that have; not used in the test",
                "unknown": "a square with an unknown score is left out of that score's test; the counts say how many "
                           "remain",
            },
        },
        "sites": sites_out,
        "test_against_all_land": test(known_squares, controls_land),
        "test_against_bare_squares": test(known_bare, controls_bare),
        "previous_cold_zero": {
            "what": f"the same two tests with the first pass's cold scale, 0 at +{ms.PREVIOUS_COLD_ZERO_C:g} C or "
                    f"warmer, to show what moving the zero point to +{ms.COLD_ZERO_C:g} C did (coordinator's "
                    "decision of 14 Nov 2026); same known and control squares; not used anywhere else",
            "cold_zero_c": ms.PREVIOUS_COLD_ZERO_C,
            "test_against_all_land": test(known_squares, controls_land, ms.PREVIOUS_COLD_ZERO_C),
            "test_against_bare_squares": test(known_bare, controls_bare, ms.PREVIOUS_COLD_ZERO_C),
        },
        "control_squares_all_land": controls_land,
        "control_squares_bare": controls_bare,
    }


# ---- the plain-words summary -------------------------------------------------------------------------

def fmt(x, digits=2, unit=""):
    if x is None:
        return "n/a"
    if isinstance(x, (int,)) and not isinstance(x, bool):
        return f"{x:,}{unit}"
    return f"{x:,.{digits}f}{unit}"


def short_name(card):
    return {"jezero": "Jezero", "gale": "Gale", "phoenix": "Phoenix", "arcadia-planitia": "Arcadia Planitia",
            "deuteronilus-mensae": "Deuteronilus Mensae", "viking-1": "Viking 1", "viking-2": "Viking 2",
            "pathfinder": "Pathfinder", "spirit": "Spirit", "opportunity": "Opportunity", "insight": "InSight",
            "phlegra-montes": "Phlegra Montes",
            # second pass (15 Nov 2026): the other six sites of the 2021 shortlist
            "arcadia-ap-1": "AP-1 (Arcadia Planitia)", "arcadia-ap-9": "AP-9 (Arcadia Planitia)",
            "erebus-em-16": "EM-16 (Erebus Montes)", "arcadia-ap-8": "AP-8 (Arcadia Planitia)",
            "erebus-em-15": "EM-15 (Erebus Montes)", "phlegra-pm-7": "PM-7 (Phlegra Montes)"}.get(card["id"], card["name"])


def name_list(names) -> str:
    """'A', 'A and B', or 'A, B and C'."""
    names = list(names)
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


# Second pass (15 Nov 2026): the three lists of Mars sites, in this order.
SITE_LISTS = ("NASA landing site", "2021 shortlist for human landings", "2015 exploration zone")
LIST_WORDS = {
    "NASA landing site": "A NASA lander or rover landed and worked there.",
    "2021 shortlist for human landings": "Table 1 of Golombek et al. 2021 (LPSC abstract 2420), a study of Starship landing sites.",
    "2015 exploration zone": "A zone proposed in an abstract of NASA's 2015 workshop on human landing sites and exploration zones.",
}


def sites_by_list_lines(cards) -> list[str]:
    """The table of the Mars sites by list (a site can be on more than one list)."""
    out = ["", "**The sites by list**", "",
           "From `mars_sites.json` → `sites[].lists`. A site can be on more than one list.",
           "A study or a proposal is not a NASA decision. NASA has not made a decision on a human landing site on Mars.",
           "", "| List | What it is | Sites | Names |", "|---|---|---|---|"]
    for name in SITE_LISTS:
        on = [c for c in cards if name in (c.get("lists") or [])]
        labels = []
        for c in on:
            ab = c.get("exploration_zone_abstracts")
            labels.append(short_name(c) + (f" ({', '.join(str(a) for a in ab)})" if name == SITE_LISTS[2] and ab else ""))
        out.append(f"| {name} | {LIST_WORDS[name]} | {len(on)} | {'; '.join(labels)} |")
    kinds = {}
    for c in cards:
        kinds.setdefault(c["kind"], 0)
        kinds[c["kind"]] += 1
    out.append("")
    out.append("The numbers in brackets are the numbers of the 2015 abstracts.")
    out.append("Kinds of site: " + "; ".join(f"{k}, {n}" for k, n in kinds.items()) + ".")
    return out


def nearest_regions_lines(cards, best) -> list[str]:
    """A compact table: for each site, the three first places on all five factors (at least 300 km apart)."""
    out = ["### In short: the nearest Earth regions on all five factors", "",
           "From `mars_cells.json` → `best_places.<site>.full`, places 1 to 3. Each place is a square of approximately 55 km.",
           "This is a first pass on squares of approximately 55 km, thus a score describes a large region.",
           SCORE_CAVEATS, "",
           "| Site | Lists | 1st: region, square | Score | 2nd: region | Score | 3rd: region | Score |",
           "|---|---|---|---|---|---|---|---|"]
    for c in cards:
        places = best[c["id"]]["full"][:3]
        cols = []
        for i, p in enumerate(places):
            cols.append(f"{p['region']}, `{p['id']}`" if i == 0 else p["region"])
            cols.append(fmt(p["score"], 3))
        while len(cols) < 6:
            cols.extend(["n/a", "n/a"])
        lists = ", ".join(c.get("lists") or []) or "n/a"
        out.append(f"| {short_name(c)} | {lists} | " + " | ".join(cols) + " |")
    out.append("")
    return out


# Sentences added by MARS-REVIEW so that the summary cannot be read as a climate match (tests in
# tests/test_mars_score.py). Each number in them is computed from the inputs, never typed.
SCORE_IS_NOT_LIKENESS = ("A score is a place on each factor's own scale between two set end points, "
                         "not a share of likeness to Mars.")
BASELINE_TEXT = f"The slope baseline is the same on both planets: {BASELINE_SHORT}, which is two pixels."
KNOWN_LIST_TEXT = ("The known sites are places that analog programmes and field studies have used, "
                   "from `data/reference/known_analogs.json`. They test the ranking and are not an input to it.")


# ---- MARS-TUNE: sentences for the coordinator's decisions of 14 Nov 2026 (tests in tests/test_mars_score.py) ----

def cold_scale_lines(cells: dict) -> list[str]:
    """The cold scale in words, with the warmest ranked square from the data."""
    lines = [f"For example, cold 0.5 means a yearly mean half-way between {ZERO} and the Mars site's.",
             f"{ZERO} is about the warmest yearly mean on Earth, so the cold scale spans Earth's whole range."]
    known = [c for c in cells.values() if c.get("t2m_year_c") is not None]
    if known:
        warm = max(known, key=lambda c: (c["t2m_year_c"], c["id"]))
        lines.append(f"The warmest ranked square, `{warm['id']}` ({warm['region']}), has a yearly mean of "
                     f"{warm['t2m_year_c']:.1f} °C.")
    return lines


def landscape_tie_line(places) -> str:
    """How many ranked squares share the top landscape score, and how the ties are ordered."""
    if not places:
        return "No ranked square has a known landscape score."
    n, top = places[0]["squares_with_this_score"], places[0]["score"]
    if n <= 1:
        return f"Only one ranked square has the top score of {top:.3f}."
    return (f"{n:,} ranked squares tie at the top score of {top:.3f}, so their order here is not a ranking. "
            "Tied squares are listed by bare area, then by environment score.")


def _range3(vals) -> str:
    lo, hi = min(vals), max(vals)
    return f"{lo:.3f}" if f"{lo:.3f}" == f"{hi:.3f}" else f"{lo:.3f} to {hi:.3f}"


def cold_change_line(now: dict, before: dict, key: str, label: str) -> str:
    """Whether moving the cold zero point made the known sites win more or fewer pairs on one score."""
    pairs = [(now[s][key]["auc"], before[s][key]["auc"]) for s in now
             if now[s][key]["auc"] is not None and before.get(s, {}).get(key, {}).get("auc") is not None]
    up = sum(1 for n, b in pairs if n > b)
    down = sum(1 for n, b in pairs if n < b)
    if not up and not down:
        verdict = "unchanged"
    elif not down:
        verdict = "better"
    elif not up:
        verdict = "worse"
    else:
        verdict = f"mixed: better for {up} sites, worse for {down}"
    return (f"Against {label}, on {key}, known squares won {_range3([b for _, b in pairs])} of pairs with the zero "
            f"point at {PREVIOUS_ZERO}. At {ZERO} they win {_range3([n for n, _ in pairs])}, so agreement with the "
            f"known sites is {verdict}.")


def zero_environment_line(named, site_id: str) -> str | None:
    """The known sites whose environment score is still 0, and which factor makes it 0."""
    out = []
    for r in named:
        sc = r["sites"][site_id]
        if sc.get("environment") == 0.0:
            why = [f for f in ms.GOALS["environment"] if sc.get(f) == 0.0]
            out.append(f"{r['named_in_job']} ({' and '.join(f'{f} 0' for f in why)})")
    if not out:
        return None
    return f"On environment these known sites still score 0, because one factor is 0: {', '.join(out)}."


def climate_gap_lines(cards, summary) -> list[str]:
    """Bullets for the opening section: the temperature and pressure gaps that no square closes."""
    gaps = [summary[c["id"]]["coldest_square"]["colder_on_mars_by_c"] for c in cards]
    cs = summary[cards[0]["id"]]["coldest_square"]
    lines = ["- It is not a climate match.",
             f"- The coldest ranked square, `{cs['id']}` ({cs['region']}), has a yearly mean of "
             f"{cs['t2m_year_c']:.1f} °C. Each Mars site is {min(gaps):.1f} to {max(gaps):.1f} °C colder."]
    p = [i for c in cards for i in c.get("cannot_match", []) if i.get("what") == "surface air pressure"]
    if p:
        sea = [100 * i["number"] for i in p]
        low = [100 * i["mars_site_over_earth_lowest_land_square"] for i in p]
        lines.append(f"- Mars air pressure at the sites is {min(sea):.2f} to {max(sea):.2f} % of Earth's at sea level. "
                     f"That is {min(low):.2f} to {max(low):.2f} % of the lowest yearly mean of any Earth land square.")
    return lines


def kind_word(kind) -> str:
    """'measured' or 'model' for a table cell: Curiosity and Perseverance are rovers, not landers."""
    if kind is None:
        return "n/a"
    return "measured" if kind.startswith("measured") else kind


def cannot_match_cells(item) -> tuple[str, str]:
    """The Mars and Earth cells of a cannot-match row. The dusty sky gives its seasonal range, not the storm peak."""
    if item.get("what") == "the dusty sky":
        return ("below 1 in the clear season, above 3 in global dust storms", f"about {item['earth']} (from memory)")
    return (str(item["mars"]), str(item["earth"]))


def model_precip_line(cells, region: str = "McMurdo Dry Valleys") -> str | None:
    """A limit bullet: the model precipitation of the squares labelled with a polar-desert region."""
    vals = [c["precip_mm_year"] for c in cells.values() if c.get("region") == region and c.get("precip_mm_year") is not None]
    if not vals:
        return None
    return (f"- The model gives the {len(vals)} ranked squares labelled {region} {min(vals):.0f} to {max(vals):.0f} mm a year. "
            "Measured snowfall there is usually put at under about 50 mm of water a year (from memory, not checked). "
            "So the model is likely too wet in polar deserts.")


def bare_class_line(val) -> str:
    """A limit bullet: WorldCover's bare class leaves out moss and lichen, so polar deserts read as less bare."""
    h = next((r for r in val.get("sites", []) if r.get("named_in_job") == "Haughton crater" and r.get("bare") is not None), None)
    tail = f" Haughton crater's square gets {h['bare']:.2f}." if h else ""
    return ("- Bare ground is WorldCover class 60, bare or sparse vegetation. "
            "Ground mapped as moss and lichen does not count, so polar deserts read as less bare." + tail)


def results_md(cards, cells, counts, best, summary, val, climate_meta, made) -> str:
    L = []
    w = L.append
    w("# LuniMartian Atlas: the Mars part, a first pass")
    w("")
    w(f"Generated {made} by `scripts/build_mars_cells.py`. "
      "It reads `mars_sites_base.json`, `mars_terrain.json` and `mars_climate.json` in `data/derived/`. "
      "Every number below was read from those files or computed from them in this run. "
      "Each table names its file and field. Unknown values are written `n/a`, never 0.")
    w("")
    w("## What this is, and what it is not")
    w("")
    w("- This is a first pass, and it is coarser than the Moon part.")
    w("- Earth is cut into squares of half a degree, about 55 km across. The Moon part used cells of about 11 km.")
    w(f"- {BASELINE_TEXT} "
      "Rocks, dunes, small craters, gullies and anything a rover would feel are not seen.")
    w("- For each Mars site it asks where on Earth, and in which months, five factors come closest. "
      "The factors are landscape slopes, dryness, cold, bare ground and noon Sun height.")
    w("- Each factor is kept apart, and each shortfall is given in plain numbers.")
    w("- Some things have no match anywhere on Earth. Section 6 lists them with numbers.")
    w("- It does not measure soil chemistry, minerals, ground ice, lava tubes, impact features or life. "
      "Many known analog sites were chosen for exactly those things.")
    w("- Earth climate is a model (NASA POWER, MERRA-2) for a grid box, not a measurement at the square.")
    for line in climate_gap_lines(cards, summary):
        w(line)
    w("")

    w("## 1. How the scores work")
    w("")
    w("Every score lies between 0 and 1. The formulas are also stored in `mars_cells.json` → `meta.formulas`.")
    w(f"It is not a climate match. {SCORE_IS_NOT_LIKENESS}")
    for line in cold_scale_lines(cells):
        w(line)
    w(f"The first pass put the zero point at {PREVIOUS_ZERO}. "
      "That gave the hyperarid Atacama, the Mojave, Dhofar and the Pilbara a cold score of 0.")
    w("")
    w("| Score | In words | Field |")
    w("|---|---|---|")
    for k in ms.FACTORS + GOAL_NAMES:
        w(f"| {k} | {ms.FORMULAS[k]} | `cells.<id>.sites.<site>.{k}` |")
    w("| months | a score per month, below | `best_places.<site>.<goal>[].month_scores` |")
    w(f"| best months | {ms.FORMULAS['best_months']} | `cells.<id>.sites.<site>.best_months` |")
    w("")
    w("Each month gets a score of its own: the geometric mean of three parts. "
      "The first is cold, from that month's mean air temperature against the site's yearly mean. "
      f"It uses the same scale, 0 at {ZERO} or warmer. "
      "The second is dry, from that month's precipitation times 12. "
      "The third is 1 if the noon Sun on the 15th lies inside the site's yearly range, and 0 if not.")
    w("")
    w("A goal is unknown when any of its factors is unknown. A factor of 0 makes its goals 0.")
    w("Only squares with at least 15 % bare ground are ranked, as in the Moon part.")
    w("")

    w("## 2. The Mars sites")
    w("")
    w("From `mars_sites.json` → `sites[]` (fields `sun`, `climate`, `landscape`). "
      "Latitudes are planetocentric; longitudes run east from 0 to 360.")
    w("")
    w("| Site | Kind | Lat | Lon E | Noon Sun, lowest to highest | Yearly mean air temp. | Pressure | "
      "Median slope / 90th pct. | Relief | Self-overlap |")
    w("|---|---|---|---|---|---|---|---|---|---|")
    for c in cards:
        cl, sn, la = c["climate"], c["sun"], c["landscape"]
        w(f"| {short_name(c)} | {c['kind']} | {c['lat']} | {c['lon_east']} | "
          f"{fmt(sn['noon_elev_min_deg'])}° to {fmt(sn['noon_elev_max_deg'])}° | "
          f"{fmt(cl['annual_mean_c'], 1)} °C ({kind_word((cl.get('kind_by_field') or {}).get('annual_mean_c', cl['kind']))}) | "
          f"{fmt(cl['pressure_pa'])} Pa ({kind_word((cl.get('kind_by_field') or {}).get('pressure_pa', cl['kind']))}) | "
          f"{fmt(la['median_slope_deg'])}° / {fmt(la['p90_slope_deg'])}° | "
          f"{fmt(la['relief_m'], 0)} m | {fmt(la['self_overlap'], 3)} |")
    w("")
    if len(cards) <= 12:
        visited = [short_name(c) for c in cards if c["kind"] == "visited by a NASA mission"]
        studied = [short_name(c) for c in cards if c["kind"] == "studied for a human landing"]
        w(f"{name_list(visited)} were visited by NASA missions. "
          f"{name_list(studied)} are candidate regions, studied for a human landing. "
          "NASA has not chosen a human landing site on Mars.")
    else:
        for line in sites_by_list_lines(cards):
            w(line)
    model_means = [c for c in cards if (c["climate"].get("kind_by_field") or {}).get("annual_mean_c", c["climate"]["kind"]) == "model"]
    if len(model_means) == len(cards):
        w(f"All {len(cards)} yearly mean temperatures are model values (Mars Climate Database, LMD with ESA and CNES). "
          "So the cold score compares like with like across the sites.")
    else:
        w(f"{len(model_means)} of the {len(cards)} yearly mean temperatures are model values (Mars Climate Database).")
    w("Relief is the 95th minus the 5th percentile height in the 2 x 2 degree box around the site.")
    feed = feed_citation_line(cards)
    if feed:
        w(feed)
    dark = [short_name(c) for c in cards if c["sun"]["noon_elev_min_deg"] is not None and c["sun"]["noon_elev_min_deg"] < 0]
    if dark:
        w(f"A lowest noon Sun below 0° means the Sun stays below the horizon all day at midwinter ({', '.join(dark)}).")
    w("")

    w("## 3. What was searched")
    w("")
    w("| What | Count | Source |")
    w("|---|---|---|")
    w(f"| Squares with slopes | {fmt(counts['squares_in_terrain'])} | `mars_terrain.json` → `cells` |")
    w(f"| Squares with climate | {fmt(counts['squares_in_climate'])} | `mars_climate.json` → `cells` |")
    w(f"| In both files | {fmt(counts['squares_in_both'])} | joined by `id` |")
    w(f"| In the slope file only / the climate file only | {fmt(counts['squares_in_terrain_only'])} / "
      f"{fmt(counts['squares_in_climate_only'])} | joined by `id` |")
    w(f"| Squares with bare ground unknown | {fmt(counts['squares_with_bare_unknown'])} | `mars_climate.json` → `cells.<id>.bare` null |")
    w(f"| Ranked squares (bare ≥ 0.15) | {fmt(counts['squares_kept_bare_at_least_0.15'])} | `mars_cells.json` → `cells` |")
    w(f"| of them without slopes (landscape and full unknown) | {fmt(counts['kept_squares_without_slopes'])} | `mars_cells.json` → `cells.<id>.sites.<site>.terrain` null |")
    w(f"| of them with a yearly mean of {ZERO} or more (cold, environment and full are 0) | "
      f"{fmt(counts['kept_squares_at_cold_zero_or_warmer'])} | `mars_cells.json` → `cells.<id>.t2m_year_c` |")
    w(f"| of them with a yearly mean of {PREVIOUS_ZERO} or more (cold was 0 there in the first pass) | "
      f"{fmt(counts['kept_squares_yearly_mean_15c_or_more'])} | `mars_cells.json` → `cells.<id>.t2m_year_c` |")
    w(f"| of them with 25 mm of precipitation a year or less (dry is 1) | "
      f"{fmt(counts['kept_squares_precip_25_mm_or_less'])} | `mars_cells.json` → `cells.<id>.precip_mm_year` |")
    by_group = {}
    for c in cells.values():
        by_group[c["region_group"]] = by_group.get(c["region_group"], 0) + 1
    for g in ("great desert", "high plateau", "polar desert", "other"):
        w(f"| Ranked squares in a box of the kind '{g}' | {fmt(by_group.get(g, 0))} | `mars_cells.json` → `cells.<id>.region_group` |")
    w("")

    w("## 4. Where on Earth comes closest, and when")
    w("")
    w("Ten places per site and goal, at least 300 km apart, best first. "
      "From `mars_cells.json` → `best_places.<site>.<goal>`. "
      "The months are the three best of the calendar score. "
      "Region names come from rough boxes in the script, not from a map.")
    w(SCORE_CAVEATS)
    ties = [summary[c["id"]]["landscape"]["squares_at_1"] for c in cards]
    w(f"By landscape, {min(ties):,} to {max(ties):,} squares per site reach 1.000. "
      "So the landscape lists are ten of many equal places, not a ranking.")
    w("In the landscape lists, equal scores are ordered by bare area (`bare_km2`), then by environment score, then by id.")
    w("In the other lists, equal scores are ordered by the slope overlap before the cap (`scores.slope_overlap`), then by id.")
    w("Each place carries `squares_with_this_score`, the number of ranked squares with exactly its score.")
    w(f"A month with a mean of {ZERO} or more scores 0, so warm squares can have fewer than three best months.")
    w("Closest means the highest score among Earth squares, not close to Mars. Sections 5 and 6 give the gaps.")
    w("The environment lists hold the same squares in the same order for every site, because only the scale of cold changes.")
    w("")
    goal_words = {"landscape": "Closest by landscape (slopes and bare ground)",
                  "environment": "Closest by environment (dry, cold and bare)",
                  "full": "Closest on all five factors"}
    if len(cards) > 12:
        for line in nearest_regions_lines(cards, best):
            w(line)
    for c in cards:
        sid = c["id"]
        w(f"### {short_name(c)}")
        w("")
        w(SCORE_CAVEATS)
        w("")
        for goal in GOAL_NAMES:
            w(f"**{goal_words[goal]}**")
            w("")
            if goal == "landscape":
                w(landscape_tie_line(best[sid][goal]))
                w("")
            w("| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |")
            w("|---|---|---|---|---|---|---|---|---|---|---|---|")
            for p in best[sid][goal]:
                s = p["scores"]
                months = ", ".join(p["best_months"] or []) or "none"
                w(f"| {p['rank']} | `{p['id']}` | {p['region']} | {fmt(p['score'], 3)} | {fmt(s['terrain'], 2)} | "
                  f"{fmt(s['dry'], 2)} | {fmt(s['cold'], 2)} | {fmt(s['bare'], 2)} | {fmt(s['sun'], 2)} | {months} | "
                  f"{fmt(p['t2m_year_c'], 1)} °C | {fmt(p['precip_mm_year'], 0)} mm |")
            w("")
        top = best[sid]["full"][0] if best[sid]["full"] else None
        if top:
            fs = top["falls_short"]
            w(f"The closest square on all factors is `{top['id']}` ({top['region']}), with a score of "
              f"{fmt(top['score'], 3)}.")
            w(f"There, Mars is {fmt(fs['colder_on_mars_by_c'], 1)} °C colder in the yearly mean.")
            w(f"The square gets {fmt(fs['times_wetter_than_25_mm'], 2)} times 25 mm of precipitation a year.")
            w(f"Mars air pressure is {fmt(100 * fs['pressure_mars_over_square'] if fs['pressure_mars_over_square'] is not None else None, 2)} % "
              f"of the square's.")
            w("")

    w("## 5. What falls short, and by how much")
    w("")
    w("From `mars_cells.json` → `meta.factor_summary.<site>`: the highest value of each factor among the ranked squares, "
      "and how many ranked squares reach 1.")
    w(SCORE_CAVEATS)
    w("")
    w("| Site | Highest cold | Coldest ranked square | Its yearly temp. | Mars colder by | Squares at dry 1 | "
      "Squares at terrain 1 | Squares at sun 1 | Highest full |")
    w("|---|---|---|---|---|---|---|---|---|")
    for c in cards:
        s = summary[c["id"]]
        cs = s["coldest_square"]
        w(f"| {short_name(c)} | {fmt(s['cold']['highest'], 3)} | `{cs['id']}` ({cs['region']}) | "
          f"{fmt(cs['t2m_year_c'], 1)} °C | {fmt(cs['colder_on_mars_by_c'], 1)} °C | {fmt(s['dry']['squares_at_1'])} | "
          f"{fmt(s['terrain']['squares_at_1'])} | {fmt(s['sun']['squares_at_1'])} | {fmt(s['full']['highest'], 3)} |")
    w("")
    gaps = [summary[c["id"]]["coldest_square"]["colder_on_mars_by_c"] for c in cards]
    cold_top = [summary[c["id"]]["cold"]["highest"] for c in cards]
    terr1 = [summary[c["id"]]["terrain"]["squares_at_1"] for c in cards]
    w(f"No ranked square reaches a cold score of 1 for any site; the highest is {max(cold_top):.3f}.")
    cs = summary[cards[0]["id"]]["coldest_square"]
    w(f"The coldest ranked square is `{cs['id']}` ({cs['region']}), at {cs['t2m_year_c']:.1f} °C a year. "
      f"Each Mars site is {min(gaps):.1f} to {max(gaps):.1f} °C colder than that.")
    w(f"Slopes alone pick out little: terrain reaches 1 in {min(terr1):,} to {max(terr1):,} of the "
      f"{len(cells):,} ranked squares.")
    w(f"Dryness is matched in many places too: {counts['kept_squares_precip_25_mm_or_less']:,} ranked squares get "
      "25 mm a year or less.")
    w(f"Cold is 0 in {counts['kept_squares_at_cold_zero_or_warmer']:,} of the {len(cells):,} ranked squares, "
      f"those at {ZERO} or warmer, so their environment and full scores are 0.")
    hi_lat = [c for c in cards if abs(c["lat"]) > mc.EARTH_TILT_DEG]
    if hi_lat:
        best_sun = max(summary[c["id"]]["sun"]["highest"] for c in hi_lat)
        if len(hi_lat) <= 6:
            w(f"For {', '.join(short_name(c) for c in hi_lat)}, no square reaches sun 1; the best is {best_sun:.3f}. "
              "The tilt of Mars is 1.75 degrees larger, so its yearly range of noon Sun is wider.")
        else:
            w(f"For the {len(hi_lat)} sites more than {mc.EARTH_TILT_DEG} degrees from the equator, no square reaches "
              f"sun 1; the best is {best_sun:.3f}. "
              "The tilt of Mars is 1.75 degrees larger, so its yearly range of noon Sun is wider.")
    w("")

    w("## 6. What no place on Earth matches")
    w("")
    w("From `mars_sites.json` → `sites[].cannot_match` (written by MARS-CLIMATE). "
      f"Pressure differs by site; the other rows are the same for all {len(cards)}.")
    w("")
    w("| What | Mars | Earth | Unit | Number | Number is |")
    w("|---|---|---|---|---|---|")
    first = cards[0]
    for item in first["cannot_match"]:
        if item["what"] == "surface air pressure":
            continue
        mars_cell, earth_cell = cannot_match_cells(item)
        w(f"| {item['what']} | {mars_cell} | {earth_cell} | {item['unit']} | "
          f"{'n/a' if item.get('number') is None else item['number']} | {item.get('number_is', '')} |")
    w("")
    w("| Site | Yearly mean pressure, Pa | Share of sea level | Share of the lowest land square |")
    w("|---|---|---|---|")
    for c in cards:
        p = next((i for i in c["cannot_match"] if i["what"] == "surface air pressure"), None)
        if p:
            w(f"| {short_name(c)} | {p['mars']} | {fmt(100 * p['number'], 2)} % | "
              f"{fmt(100 * p['mars_site_over_earth_lowest_land_square'], 2)} % (`{p['earth_lowest_land_square_where']}`) |")
    w("")
    if feed:
        w(feed)
        w("")
    w("Three of these rows are literature figures typed from memory by MARS-CLIMATE and not checked against a saved file. "
      "They are the UV cut-off, the radiation dose and the Earth dust optical depth.")
    w("")

    w("## 7. Where the known analog sites come out")
    w("")
    w("From `mars_validation.json` → `sites[]`. Each entry is placed in the square that holds its point. "
      "The percentile is the share of ranked squares that score lower, so 100 is the top.")
    w(KNOWN_LIST_TEXT)
    w(SCORE_CAVEATS)
    w("")
    named = [r for r in val["sites"] if r["named_in_job"]]
    named.sort(key=lambda r: list(REQUIRED).index(r["named_in_job"]))
    w("| Site | Square | Region | Bare | Yearly temp. | Precip. | Ranked |")
    w("|---|---|---|---|---|---|---|")
    for r in named:
        edge = " (point on a square edge)" if r["on_square_edge"] else ""
        w(f"| {r['named_in_job']} | `{r['square']}`{edge} | {r['region']} | {fmt(r['bare'], 2)} | "
          f"{fmt(r['t2m_year_c'], 1)} °C | {fmt(r['precip_mm_year'], 0)} mm | {'yes' if r['ranked'] else 'no'} |")
    w("")
    for goal in GOAL_NAMES:
        w(f"**{goal}: score (percentile among ranked squares)**")
        w("")
        w("| Site | " + " | ".join(short_name(c) for c in cards) + " |")
        w("|---|" + "---|" * len(cards))
        for r in named:
            cols = []
            for c in cards:
                sc = r["sites"][c["id"]]
                cols.append(f"{fmt(sc[goal], 3)} ({fmt(sc['percentile'][goal], 1)})")
            w(f"| {r['named_in_job']} | " + " | ".join(cols) + " |")
        w("")
    w("**Points on a square edge, and points whose square has no data: the other squares nearby**")
    w("")
    w("From `mars_validation.json` → `sites[].other_squares_at_the_point` and `sites[].neighbours_with_data`. "
      "These squares are not used in section 8.")
    w("")
    w(f"| Site | Square used | Its highest full over the {len(cards)} sites | Other square | Ranked | Bare | Its highest full |")
    w("|---|---|---|---|---|---|---|")
    for r in named:
        others = list({q["square"]: q for q in r["other_squares_at_the_point"] + r["neighbours_with_data"]}.values())
        own = [r["sites"][c["id"]]["full"] for c in cards if r["sites"][c["id"]]["full"] is not None]
        for q in others:
            qf = [q["sites"][c["id"]]["full"] for c in cards if q["sites"][c["id"]]["full"] is not None]
            w(f"| {r['named_in_job']} | `{r['square']}` | {fmt(max(own) if own else None, 3)} | `{q['square']}` | "
              f"{'yes' if q['ranked'] else 'no'} | {fmt(q['bare'], 2)} | {fmt(max(qf) if qf else None, 3)} |")
    w("")
    not_in = [r["named_in_job"] for r in named if not r["in_climate"]]
    if not_in:
        w(f"No climate square holds these points, so their scores are unknown: {', '.join(not_in)}.")
        w("")
    not_ranked = [r["named_in_job"] for r in named if r["in_climate"] and not r["ranked"]]
    if not_ranked:
        w(f"These squares have under 15 % bare ground and are not ranked: {', '.join(not_ranked)}. "
          "They are scored all the same.")
        w("")
    zero_env = zero_environment_line(named, cards[0]["id"])
    if zero_env:
        w(zero_env)
        w("")

    w("## 8. A test of the ranking")
    w("")
    t = val["meta"]["test"]
    w(f"Known squares: {t['known_squares']} distinct squares of the {val['meta']['entries']} Mars entries. "
      f"Of them, {t['known_squares_bare_at_least_0.15']} have at least 15 % bare ground.")
    w(f"Controls: {N_CONTROLS:,} squares drawn by the sha1 of their id from all squares with land. "
      f"A second set of {N_CONTROLS:,} is drawn the same way from the ranked squares only.")
    w("The number is the area under the curve (AUC). "
      "It is the chance that a known square outranks a control, ties counting one half. "
      "0.5 is chance; 1 means every known square wins.")
    w("")
    for key, label in (("test_against_all_land", "Against all squares with land"),
                       ("test_against_bare_squares", "Against ranked squares only (bare ≥ 0.15)")):
        w(f"**{label}** (`mars_validation.json` → `{key}.<site>.<score>.auc`)")
        w("")
        cols = list(GOAL_NAMES) + ["bare", "dry", "cold", "terrain", "sun"]
        w("| Site | " + " | ".join(cols) + " |")
        w("|---|" + "---|" * len(cols))
        for c in cards:
            res = val[key][c["id"]]
            w(f"| {short_name(c)} | " + " | ".join(fmt(res[k]["auc"], 3) for k in cols) + " |")
        w("")
        n = val[key][cards[0]["id"]]["full"]
        w(f"Pairs for `full`: {n['known']} known squares against {n['controls']:,} controls.")
        w("")
    land = val["test_against_all_land"]
    bare_t = val["test_against_bare_squares"]
    def rng(a, b):
        return f"{a:.2f}" if f"{a:.2f}" == f"{b:.2f}" else f"{a:.2f} to {b:.2f}"

    def span(res, key):
        v = [res[c["id"]][key]["auc"] for c in cards if res[c["id"]][key]["auc"] is not None]
        return (min(v), max(v)) if v else (None, None)
    lo_l, hi_l = span(land, "landscape")
    lo_f, hi_f = span(land, "full")
    lo_e, hi_e = span(land, "environment")
    b_l = span(land, "bare")[0]
    c_l = span(land, "cold")[0]
    lo_fb, hi_fb = span(bare_t, "full")
    lo_lb, hi_lb = span(bare_t, "landscape")
    w(f"Against all land, known squares outrank controls on landscape in {rng(lo_l, hi_l)} of pairs. "
      f"Bare ground alone gives {b_l:.2f}.")
    w(f"On environment the figure is {rng(lo_e, hi_e)}, and on all five factors {rng(lo_f, hi_f)}.")
    if hi_f < 0.65:
        w("That is only a little better than chance.")
    w("Environment puts the squares in the same order for every site, because only the scale of cold changes.")
    if c_l < 0.5:
        w(f"Cold alone gives {c_l:.2f}, below chance. "
          "The controls include the Antarctic ice sheet, which is colder than any known site.")
    else:
        w(f"Cold alone gives {c_l:.2f}.")
    w(f"Against bare squares only, the {t['known_squares_bare_at_least_0.15']} bare known squares win "
      f"{rng(lo_fb, hi_fb)} of pairs on all factors and {rng(lo_lb, hi_lb)} on landscape.")
    b_b, d_b = span(bare_t, "bare")[0], span(bare_t, "dry")[0]
    if hi_fb < 0.55:
        w("So among bare ground, the scores do not pick out the places scientists chose.")
    if b_b < 0.5 and d_b < 0.5:
        w(f"The bare known squares are less bare (AUC {b_b:.2f}) and wetter (AUC {d_b:.2f}) than a typical bare square.")
    w("")
    prev = val["previous_cold_zero"]
    w(f"**What moving the cold zero point from {PREVIOUS_ZERO} to {ZERO} did** "
      "(`mars_validation.json` → `previous_cold_zero`)")
    w("")
    for key, label in (("test_against_all_land", "all land"), ("test_against_bare_squares", "bare squares only")):
        for score in ("environment", "full"):
            w(cold_change_line(val[key], prev[key], score, label))
    w("Landscape does not use cold, so its figures are the same as before.")
    w("")
    w("What it does not show: that a top square is a better analog than a known site. "
      "Known sites were picked partly for being bare and dry, so the test against all land is partly circular.")
    w("It also says nothing about chemistry, minerals, ice or life, which these factors do not measure. "
      "The known list comes from encyclopedia and project pages, and many of its points are estimated.")
    w("")

    w("## 9. Limits")
    w("")
    w("- Squares are half a degree, about 55 km. A small site such as a crater or a valley fills a fraction of one.")
    w(f"- {BASELINE_TEXT} So slopes are much gentler than at rover scale.")
    w("- East-west spacing shrinks with latitude, so high-latitude squares mix a shorter baseline into their slopes.")
    w("- Slopes alone saturate: they reach the full terrain score in thousands of squares.")
    w("- Earth temperature, precipitation and pressure are NASA POWER (MERRA-2) values for a grid box.")
    dv = model_precip_line(cells)
    if dv:
        w(dv)
    wet = [r for r in val["sites"] if r["named_in_job"] in ("Iceland's highlands", "Svalbard")
           and r["precip_mm_year"] is not None]
    if wet:
        w("- Model precipitation decides some known sites. The model gives "
          + " and ".join(f"{r['named_in_job']} {r['precip_mm_year']:.0f} mm" for r in wet)
          + " a year, so dry is 0 there.")
        w("- MARS-CLIMATE judged the Iceland figure too wet against general knowledge; the Svalbard figure was not checked.")
    w("- A square is placed by the analog list's point, and many of those points are estimated or sit on a square edge.")
    w("- POWER names 2001 to 2025, but its values most likely fit 2001 to 2020 (see `mars_climate.json` → `meta.climate_period_caution`).")
    w("- Bare ground is ESA WorldCover 2021 north of 60 S. In Antarctica it is the project's rock-outcrop layer, a lower bound.")
    w(bare_class_line(val))
    w("- Lakes inside the land outline count as land, and their slopes are lake-bed slopes (`mars_terrain.json` notes).")
    w("- The Mars yearly means are model values; the model understates daily extremes, by its makers' own warning.")
    w("- The cold score uses the yearly mean only. Daily and seasonal swings on Mars are far larger than on Earth.")
    w("- The month score uses the noon Sun on the 15th of each month and the monthly means.")
    w("- Cloud cover is not used: `cloud_pct` is null for every square in this pass.")
    w("- Region names are rough rectangles in the script, not a map.")
    w("- Nothing here was checked in the field.")
    w("")

    w("## 10. Files")
    w("")
    w("| File | What |")
    w("|---|---|")
    w("| `data/derived/mars_sites.json` | One card per Mars site: name, kind, why, sources, Sun, landscape, climate, cannot-match list, best places |")
    w("| `data/derived/mars_cells.json` | Every ranked square with its scores per site, best months and shortfalls; the best places |")
    w("| `data/derived/mars_validation.json` | The known analog sites per site and goal, and the AUC test |")
    w("| `data/derived/MARS-RESULTS.md` | This summary |")
    w("")
    return "\n".join(L)


# ---- main --------------------------------------------------------------------------------------------

def main() -> int:
    made = dt.datetime.now().astimezone()
    made_s = made.strftime("%A %d %B %Y, %H:%M %Z")
    sites_base, terrain, climate = load(SITES_BASE), load(TERRAIN), load(CLIMATE)
    analogs = load(ANALOGS)

    cards = site_cards(sites_base, terrain, climate)
    cells, counts = score_cells(cards, terrain, climate)
    best = best_places(cells, cards, climate)
    summary = factor_summary(cells, cards)
    val = validation(cells, cards, terrain, climate, analogs)

    tied = tied_at_top(best)
    for card in cards:
        card["best_places"] = best[card["id"]]
        card["best_places_tied_at_top"] = tied[card["id"]]
        card["factor_summary"] = summary[card["id"]]

    sources = SOURCES
    first_pass = FIRST_PASS
    meta = {
        "what": "Every half-degree Earth square with at least 15 % bare ground, scored against each Mars site.",
        "first_pass": first_pass,
        "square_deg": 0.5, "square_km_about": 55, "slope_baseline_km_about": 1.85, "min_bare": MIN_BARE,
        "height_spacing_km_about": 1.85, "slope_span_km_about": 3.7,
        "cold_zero_c": ms.COLD_ZERO_C,
        "best_places_tied_at_top": tied,
        "changes": [
            f"14 Nov 2026, coordinator's decisions: cold is 0 at +{ms.COLD_ZERO_C:g} C or warmer (it was "
            f"+{ms.PREVIOUS_COLD_ZERO_C:g} C), in the yearly and the monthly score",
            "landscape ties are ordered by bare_km2, then by environment, then by id; each place gives "
            "squares_with_this_score and each list's tie count is in best_places_tied_at_top",
            f"the slope baseline is written '{BASELINE_SHORT}'; Curiosity's figures are cited as from NASA's public "
            "weather feed, which says it is for outreach, not as archive data",
        ],
        "made": made.isoformat(timespec="seconds"),
        "made_by": "agent MARS-SCORE, scripts/build_mars_cells.py (scores in twinfinder/mars_score.py)",
        "sources": sources,
        "formulas": ms.FORMULAS,
        "fields": {
            "land_share": "share of the whole square that is land, from mars_climate.json (WorldCover north of 60 S, "
                          "Natural Earth south of it); the denominator of bare",
            "bare": "bare share of the land (mars_climate.json)",
            "bare_km2": "bare x land_share x the square's area on a sphere of radius 6,371.0088 km",
            "t2m_year_c": "yearly mean air temperature 2 m above the ground, NASA POWER (MERRA-2), C",
            "precip_mm_year": "yearly precipitation, rain and snow as water, NASA POWER PRECTOTCORR, mm",
            "pressure_kpa": "yearly mean surface pressure, NASA POWER PS, kPa",
            "region / region_group": "a plain name from a table of rough boxes in scripts/build_mars_cells.py; group "
                                     "is 'great desert', 'high plateau', 'polar desert' or 'other'",
            "sites.<site>": "the five factor scores, the three goals, best_months and falls_short",
            "falls_short.colder_on_mars_by_c": "the square's yearly mean air temperature minus the site's, C",
            "falls_short.times_wetter_than_25_mm": "the square's yearly precipitation / 25 mm (1 or less: dry enough)",
            "falls_short.pressure_mars_over_square": "the site's yearly mean pressure / the square's",
            "best_places.<site>.<goal>": f"the {N_BEST} best squares by that goal, each at least "
                                         f"{ms.SAME_PLACE_KM:.0f} km from those before it, with the month scores; "
                                         "equal scores ordered by bare_km2, then environment, then id for landscape, "
                                         "and by slope_overlap, then id for the other goals",
            "best_places.<site>.<goal>[].squares_with_this_score": "how many ranked squares have exactly this "
                                                                    "score (four decimals), this one included",
            "best_places.<site>.<goal>[].bare_km2": "the square's bare area, as in cells.<id>.bare_km2",
            "best_places_tied_at_top": "per site and goal, how many ranked squares share the list's top score",
            "slope_baseline_km_about": "the spacing of the heights (1.85 km); each slope spans two pixels, about "
                                       "3.7 km (slope_span_km_about)",
            "counts.kept_squares_at_cold_zero_or_warmer": f"ranked squares with a yearly mean of +{ms.COLD_ZERO_C:g} "
                                                          "C or more: cold, environment and full are 0",
            "counts.kept_squares_yearly_mean_15c_or_more": "ranked squares with a yearly mean of +15 C or more, the "
                                                           "first pass's zero point; their cold is no longer 0",
            "climate.citation_note (site cards)": "how to cite a site's measured figures when they come from NASA's "
                                                  "public weather feed; null otherwise",
        },
        "counts": counts,
        "factor_summary": summary,
        "null_rule": "unknown is null, never 0; a goal with an unknown factor is null",
        "plan_departures": [
            "cells carry region_group, bare_source, elev_mean_m and median_slope_deg besides the job's fields",
            "the cold score uses t2m_year_c, the POWER annual T2M, as MARS-CLIMATE advised",
            "the square's noon Sun height for a month is taken on the 15th of the month",
        ],
    }
    cells_out = {"meta": meta, "best_places": best, "cells": cells}
    sites_out = {
        "meta": {
            "what": "One card per Mars site of the Mars part: everything a site card shows.",
            "first_pass": first_pass,
            "cold_zero_c": ms.COLD_ZERO_C,
            "made": made.isoformat(timespec="seconds"),
            "made_by": "agent MARS-SCORE, scripts/build_mars_cells.py",
            "sources": sources,
            "kinds": {"visited by a NASA mission": "a NASA lander or rover worked there",
                      "studied for a human landing": "a candidate region studied for a human landing; NASA has not "
                                                     "chosen a human landing site on Mars",
                      "proposed as an exploration zone in 2015": "an exploration zone proposed in an abstract of NASA's "
                                                                 "2015 workshop on human landing sites; a proposal is "
                                                                 "not a NASA decision"},
            "lists": dict(zip(SITE_LISTS, (LIST_WORDS[n] for n in SITE_LISTS))),
            "best_places": "the same lists as mars_cells.json -> best_places",
            "sites_base_meta": sites_base.get("meta", {}),
        },
        "sites": cards,
    }

    md = results_md(cards, cells, counts, best, summary, val, climate.get("meta", {}), made_s)
    long = long_sentences(md)
    bad = sales_words(md)
    no_caveats = blocks_missing_caveats(md)
    if long or bad or no_caveats:
        for s in long:
            print("LONG SENTENCE:", len(s.split()), s, file=sys.stderr)
        for s in bad:
            print("SALES WORD:", s, file=sys.stderr)
        for s in no_caveats:
            print("SCORES WITHOUT THE TWO CAVEATS UNDER:", s, file=sys.stderr)
        return 1

    write_json(OUT_SITES, sites_out)
    write_json(OUT_CELLS, cells_out)
    write_json(OUT_VALIDATION, val)
    write_text(OUT_MD, md)
    print(f"wrote {OUT_SITES.name}, {OUT_CELLS.name} ({len(cells):,} squares), {OUT_VALIDATION.name}, {OUT_MD.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# Written with an AI assistant; see README.md, section 'How AI was used'.
"""Export the independent Mars module without rounding source measurements.

Run with ``uv run python scripts/export_site_mars.py`` after rebuilding the Mars
pipeline. The binary is columnar, little endian. Each column records its type,
scale and unknown sentinel in mars.json. No dependency beyond numpy is needed.
"""

from __future__ import annotations

import calendar
import copy
import json
import math
import re
from decimal import Decimal
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCORES = ("terrain", "dry", "cold", "bare", "sun", "landscape", "environment", "full")
COMMON = ("lat", "lon", "bare", "t2m_year_c", "precip_mm_year", "pressure_kpa")
SHORTFALLS = ("colder_on_mars_by_c", "times_wetter_than_25_mm", "pressure_mars_over_square")
MONTHS = list(calendar.month_abbr)[1:]
TYPE_NAMES = {"u1": "uint8", "u2": "uint16", "u4": "uint32", "i2": "int16", "i4": "int32"}
# Plain summaries of the saved rationale. Original wording remains in ``why``.
# Each entry is enabled only while its identifying evidence is in that source.
WHY_SUMMARIES = {
    "jezero": ("lake and a river delta", [
        "Perseverance explores a crater that once held a lake and a river delta.",
        "Its MEDA weather station measures conditions at the surface.",
    ]),
    "gale": ("REMS station recorded", [
        "Curiosity studies this crater while driving uphill from its landing point.",
        "Its REMS station has recorded air temperature, ground temperature and pressure.",
    ]),
    "phoenix": ("ice in a trench", [
        "Phoenix tested for water ice under a thin cover of soil.",
        "Ice exposed in a trench disappeared within days.",
        "Its MET station measured weather during the northern summer.",
    ]),
    "arcadia-planitia": ("Smooth northern plains", [
        "These smooth northern plains may hold abundant shallow water ice.",
        "NASA's workshop studied the region as a candidate for human landings.",
        "The SWIM project names it as a region with accessible shallow ice.",
    ]),
    "deuteronilus-mensae": ("Mesas ringed by debris aprons", [
        "Orbital radar indicates that debris aprons around the mesas contain water ice under rocky cover.",
        "NASA's workshop studied the region as a candidate for human landings.",
        "The SWIM project names its glacier-filled valleys as a region with accessible ice.",
    ]),
    "viking-1": ("western Chryse Planitia", [
        "Viking 1 touched down on the plains of western Chryse Planitia in 1976.",
        "It found surface material like iron-rich clay.",
        "It worked on the surface until November 1982.",
    ]),
    "viking-2": ("Utopia Planitia on 3 September 1976", [
        "Viking 2 touched down in Utopia Planitia in 1976, with one leg on a rock.",
        "It found surface material like iron-rich clay.",
        "It worked on the surface for 1,281 sols.",
    ]),
    "pathfinder": ("Ares Vallis outwash", [
        "Mars Pathfinder and its Sojourner rover landed on the Ares Vallis plain in 1997.",
        "A huge flood made this outwash plain.",
        "The mission studied the rocks and soil near the lander.",
    ]),
    "spirit": ("in Gusev crater", [
        "Spirit landed on a flat plain with many small rocks in Gusev crater in 2004.",
        "The crater looks like an old lake bed.",
        "Spirit searched the Columbia Hills for signs of past water.",
    ]),
    "opportunity": ("coarse-grained hematite", [
        "Opportunity landed in a small crater on Meridiani Planum in 2004.",
        "The plain holds coarse-grained hematite.",
        "For more than 14 years, the rover studied rock that water laid down.",
    ]),
    "insight": ("degraded impact crater", [
        "InSight landed in a degraded impact crater in Elysium Planitia in 2018.",
        "The ground is smooth sand, granules and pebbles with few rocks.",
        "The lander worked until December 2022.",
    ]),
    "phlegra-montes": ("prime site (PM-1)", [
        "Lobate debris aprons and polygons at this site are signs of ground ice.",
        "A 2021 study by JPL and SpaceX lists it as a prime candidate site for Starship landings.",
        "This study is not a NASA selection.",
    ]),
}


def compact(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def without_personal_attribution(text):
    """Keep places, dates and source URLs; omit personal naming and bylines."""
    if not isinstance(text, str) or re.match(r"https?://", text):
        return text
    text = re.sub(r"\s*\([^()]* Landing\)", "", text)
    text = re.sub(r"\([^()]*; [^()]* of JPL\)", "", text)
    text = re.sub(r"\([A-Z][A-Za-z]+(?:, [A-Z][A-Za-z]+)* and [A-Z][A-Za-z]+\)", "", text)
    text = re.sub(r"[A-Z][a-z]+(?:-[A-Z][a-z]+)? et al\. (?=\d{4})", "study published in ", text)
    # Only a surname or a comma/"and" list followed immediately by a year is a
    # byline. Ordinary prose and product names must retain their provenance.
    byline = r"^[A-Z][a-z]+(?:-[A-Z][a-z]+)?(?:(?:, | and )[A-Z][A-Za-z-]+)* \d{4}\b"
    if re.match(byline, text):
        text = re.sub(r"^.*?(?=\d{4})", "Study published in ", text, count=1)
    text = re.sub(r"\(saved: data/[^()]+\)", "(saved source file)", text)
    return re.sub(r" {2,}", " ", text).strip()


def clean_text(value):
    if isinstance(value, str):
        return without_personal_attribution(value)
    if isinstance(value, dict):
        return {key: clean_text(inner) for key, inner in value.items()}
    if isinstance(value, list):
        return [clean_text(inner) for inner in value]
    return value


def need(mapping, key, warnings, label):
    if not isinstance(mapping, dict) or key not in mapping:
        warnings.add(f"Optional field missing: {label}.{key}; shown as unknown.")
        return None
    return mapping[key]


def encode_column(values):
    """Choose the smallest lossless integer scale, reserving a separate null."""
    known = [value for value in values if value is not None and math.isfinite(value)]
    decimals = max((max(0, -Decimal(str(value)).as_tuple().exponent) for value in known), default=0)
    scale = 10 ** decimals
    encoded = [None if value is None or not math.isfinite(value) else int(Decimal(str(value)) * scale) for value in values]
    present = [value for value in encoded if value is not None]
    low, high = min(present, default=0), max(present, default=0)
    for dtype in ("u1", "u2", "u4", "i2", "i4"):
        info = np.iinfo(dtype)
        sentinel = int(info.max if info.min == 0 else info.min)
        fits = low >= info.min and high < info.max if info.min == 0 else low > info.min and high <= info.max
        if fits:
            payload = np.asarray([sentinel if value is None else value for value in encoded], dtype="<" + dtype).tobytes()
            return payload, {"type": TYPE_NAMES[dtype], "scale": scale, "unknown": sentinel}
    # A later pipeline may write more precision. Preserve it rather than round it.
    payload = np.asarray([np.nan if value is None else value for value in values], dtype="<f8").tobytes()
    return payload, {"type": "float64", "scale": 1, "unknown": "NaN"}


def encode_squares(cells_doc, site_ids, warnings):
    cells = list(cells_doc["cells"].values())
    regions = list(dict.fromkeys(cell.get("region") for cell in cells if cell.get("region") is not None))
    region_index = {name: index for index, name in enumerate(regions)}
    columns, chunks, offset = {}, [], 0

    def add(name, values):
        nonlocal offset
        payload, spec = encode_column(values)
        spec["offset"] = offset
        columns[name] = spec
        chunks.append(payload)
        offset += len(payload)

    for field in COMMON:
        add(field, [need(cell, field, warnings, "squares") for cell in cells])
    add("region", [region_index.get(need(cell, "region", warnings, "squares")) for cell in cells])
    for site_id in site_ids:
        scores = [need(cell.get("sites"), site_id, warnings, "squares.sites") or {} for cell in cells]
        prefix = f"sites.{site_id}."
        for field in SCORES:
            add(prefix + field, [need(score, field, warnings, prefix.rstrip(".")) for score in scores])
        for field in SHORTFALLS:
            add(prefix + "falls_short." + field, [need(score.get("falls_short"), field, warnings, prefix + "falls_short") for score in scores])
        months = [need(score, "best_months", warnings, prefix.rstrip(".")) for score in scores]
        add(prefix + "best_months_count", [len(value) if value is not None else None for value in months])
        for position in range(3):
            add(prefix + f"best_month_{position}", [MONTHS.index(value[position]) if value is not None and len(value) > position else None for value in months])
    return b"".join(chunks), {"file": "mars_squares.bin", "count": len(cells), "ids": [cell["id"] for cell in cells],
                              "regions": regions, "months": MONTHS, "columns": columns,
                              "layout": "Columnar little endian. Decode each column as raw / scale; its unknown sentinel means null. A float64 NaN means unknown.",
                              "best_months_rule": "A count of zero means no month scored above zero. An unknown count means the months are unknown."}


def simplify_line(points, tolerance):
    """Iterative perpendicular-distance thinning, keeping each ring closed."""
    coordinates = np.asarray(points, dtype=float)
    if len(coordinates) <= 4:
        return coordinates.tolist()
    keep = {0, len(coordinates) - 1}
    pending = [(0, len(coordinates) - 1)]
    while pending:
        start, end = pending.pop()
        if end <= start + 1:
            continue
        delta = coordinates[end] - coordinates[start]
        inner = coordinates[start + 1:end] - coordinates[start]
        length = float(delta @ delta)
        if not length:
            distances = np.sum(inner * inner, axis=1)
        else:
            parameter = np.clip((inner @ delta) / length, 0, 1)
            distances = np.sum((inner - parameter[:, None] * delta) ** 2, axis=1)
        relative = int(np.argmax(distances))
        if distances[relative] > tolerance * tolerance:
            middle = start + 1 + relative
            keep.add(middle)
            pending.extend(((start, middle), (middle, end)))
    result = coordinates[sorted(keep)].tolist()
    if len(result) < 4:
        return []
    return [[round(lon, 4), round(lat, 4)] for lon, lat in result]


def export_world(land_doc):
    polygons = []
    for feature in land_doc.get("features", []):
        geometry = feature.get("geometry") or {}
        if geometry.get("type") == "Polygon":
            polygons.append(geometry["coordinates"])
        elif geometry.get("type") == "MultiPolygon":
            polygons.extend(geometry["coordinates"])
    tolerance = 0.08
    while True:
        result = []
        for polygon in polygons:
            rings = [simplify_line(ring, tolerance) for ring in polygon]
            if rings and rings[0]:
                result.append([ring for ring in rings if ring])
        payload = compact({"type": "MultiPolygon", "coordinates": result,
                           "meta": {"source": "data/raw/naturalearth/ne_50m_land.geojson", "licence": "Natural Earth, public domain",
                                    "simplification_degrees": tolerance, "use": "A thinned land outline for the flat world map."}})
        if len(payload) < 400_000:
            return payload
        tolerance *= 1.5


def site_cards(sites_doc, warnings):
    cards = []
    numeric_fields = {"sun": ("noon_elev_min_deg", "noon_elev_max_deg", "day_length_min_h", "day_length_max_h"),
                      "landscape": ("median_slope_deg", "p90_slope_deg", "relief_m", "self_overlap"),
                      "climate": ("annual_mean_c", "warm_season_daily_max_c", "cold_season_daily_min_c", "pressure_pa")}
    for source in sites_doc["sites"]:
        card = clean_text({key: copy.deepcopy(value) for key, value in source.items() if key != "best_places"})
        marker, summary = WHY_SUMMARIES.get(source["id"], (None, None))
        if marker and marker in source.get("why", ""):
            card["why_sentences"] = list(summary)
        elif marker:
            warnings.add(f"Site rationale changed: {source['id']}; the page uses the current source wording.")
        # A site of the second pass (15 Nov 2026) has no summary here: its "why" is already short text
        # in the page's wording rules, so the page uses it as it is and no warning is necessary.
        for group, fields in numeric_fields.items():
            if not isinstance(card.get(group), dict):
                card[group] = {}
            for field in fields:
                card[group][field] = need(card[group], field, warnings, f"sites.{source['id']}.{group}")
        card["display_status"] = (source["kind"] if source["kind"] in ("visited by a NASA mission",
                                                                       "proposed as an exploration zone in 2015")
                                  else "studied as a candidate for a human landing")
        card["lists"] = list(source.get("lists") or [])
        cards.append(card)
    return cards


def build_export(sites_doc, cells_doc, validation_doc, moon_doc, land_doc):
    """Build bytes in memory; tests do not create files outside the owned outputs."""
    warnings = set()
    cards = site_cards(sites_doc, warnings)
    binary, squares = encode_squares(cells_doc, [card["id"] for card in cards], warnings)
    meta = clean_text(copy.deepcopy(cells_doc["meta"]))
    dry_numbers = re.findall(r"(?<![\w.])\d+(?:\.\d+)?", meta["formulas"]["dry"])
    meta["score_scale"] = sorted([int(dry_numbers[0]), int(dry_numbers[2])])
    meta["dry_reference_mm"] = float(dry_numbers[1])
    meta["status_caution"] = "NASA has selected no human landing site on Mars."
    meta["climate_caution"] = "Earth climate comes from a grid-box model, not measurements at each square. Mars yearly mean temperatures also come from a model."
    meta["validation_caution"] = [
        "This check asks whether known analog squares outrank control squares.",
        "It does not show that a top square is a better analog than a known site.",
        "Known sites were partly picked for bare and dry ground, so the check against all land is partly circular.",
        "Among bare ground, the scores do not pick out the places scientists studied.",
        "These factors do not measure chemistry, minerals, ice or life. Many known-site coordinates are estimated.",
    ]
    meta["score_caution"] = "Scores are positions on each factor's scale. They are not shares of likeness to Mars."
    meta["intro"] = "This first pass compares Earth squares with Mars sites through the year. It is coarser than the Moon part."
    meta["hard_part"] = "The Sun is the easy part for Mars. Cold, dryness, bare ground and landscape are the hard parts."
    validation = {key: clean_text(copy.deepcopy(value)) for key, value in validation_doc.items() if not key.startswith("control_squares") and key != "sites"}
    validation["sites"] = [{key: clean_text(copy.deepcopy(value)) for key, value in site.items()
                            if key not in ("other_squares_at_the_point", "neighbours_with_data")}
                           for site in validation_doc.get("sites", [])]
    moon_points = [{"id": card["id"], "name": card.get("official_name", card.get("name_in_project", card["id"])),
                    "lat": need(card.get("centre"), "lat", warnings, "moon.centre"),
                    "lon_east": need(card.get("centre"), "lon_east", warnings, "moon.centre")}
                   for card in moon_doc.get("cards", [])]
    manifest = {"meta": meta, "sites": cards, "best_places": copy.deepcopy(cells_doc["best_places"]),
                "validation": validation, "squares": squares,
                "locators": {"moon": moon_points,
                             "mars": [{key: card[key] for key in ("id", "name", "lat", "lon_east")} for card in cards]},
                "warnings": sorted(warnings)}
    files = {"mars.json": compact(manifest), "mars_squares.bin": binary, "mars_world.json": export_world(land_doc)}
    # Raised from 3,000,000 on 15 November 2026: twelve Mars sites need 15 columns each in mars_squares.bin
    # (approximately 5.5 MB in all, approximately 2.6 MB with gzip). A decision for the team lead to confirm.
    # Raised again from 6,000,000 on 15 November 2026 (second pass, 57 Mars sites): mars_squares.bin is then
    # approximately 21 MB. The page does not load this file as it is: scripts/split_mars_squares.py divides it
    # next into the shared columns (mars_squares.bin) and one file for each site (mars_site_<id>.bin), and
    # scripts/compress_site_data.py writes a compressed copy of each large file. Run both after this script.
    if sum(map(len, files.values())) >= 26_000_000:
        raise ValueError("Mars export exceeds the total size limit; no files were written.")
    return files


def main():
    def read(relative):
        return json.loads((ROOT / relative).read_text(encoding="utf-8"))

    files = build_export(sites_doc=read("data/derived/mars_sites.json"),
                         cells_doc=read("data/derived/mars_cells.json"),
                         validation_doc=read("data/derived/mars_validation.json"),
                         moon_doc=read("data/derived/moon_cards.json"),
                         land_doc=read("data/raw/naturalearth/ne_50m_land.geojson"))
    destination = ROOT / "site" / "data"
    destination.mkdir(parents=True, exist_ok=True)
    for name, payload in files.items():
        (destination / name).write_bytes(payload)
        print(f"{name}: {len(payload):,} bytes")
    for warning in json.loads(files["mars.json"])["warnings"]:
        print(f"Warning: {warning}")
    print(f"Mars export total: {sum(map(len, files.values())):,} bytes; first pass.")


if __name__ == "__main__":
    main()

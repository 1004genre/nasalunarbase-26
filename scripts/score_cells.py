# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Join every layer per cell, score each cell against each lunar target, and write the ranked sites.

Reads data/derived/grazing_cells.json and grazing_bins.npz (hours, snow, horizon),
terrain_cells.json, cloud_cells.json, moon_targets.json and the lists in
data/reference. Writes data/derived/cells_scored.json (one record per cell of
candidates.json, which since version 3 is every cell) and data/derived/ranking.txt
(the tables in plain words). The cloud column is joined here and enters no score.
The results of the first method are kept beside them as cells_scored_v1.json,
ranking_v1.txt and validation_v1.json. Safe to run again: each file is written
beside the old one and renamed into place, and the kept copies are never overwritten.
"""
import json
import os
from datetime import datetime
from pathlib import Path

import numpy as np

from twinfinder import cloud, grazing, grid, reference, score, sun
from twinfinder.grazing import NAMED_SITES_NORTH

DERIVED = Path("data/derived")
REFERENCE = Path("data/reference")
OUT = DERIVED / "cells_scored.json"
RANKING = DERIVED / "ranking.txt"
CLOUD = DERIVED / "cloud_cells.json"
OLD_RESULTS = {"cells_scored.json": "cells_scored_v1.json", "ranking.txt": "ranking_v1.txt",
               "validation.json": "validation_v1.json"}
FIRST_RANKING_START = "scored cells:"   # how the first method's ranking.txt begins
CLOUD_NOTE = ("Typical clear-sky hours: the long-window open hours of each ten-day bin times the share of the sky "
              "that is clear in the bin's month (1 - monthly mean cloud amount / 100). The cloud amount is the mean "
              "share of sky covered over all hours of day and night, 2001 to 2025, on a grid about 100 km across "
              "(NASA POWER, CERES SYN1deg). It is not the chance that a low Sun is visible, and it enters no score.")
ROCK_MARGIN_KM = 8.0       # half the diagonal of a cell, so a body inside the cell is not missed
KNOWN_SITE_KM = 50.0       # a cell this close to a listed analog site is not little-known
MIN_SNOW_LAND_PIXELS = 7   # fewer of the nine 4 km snow pixels being land marks the snow odds as thin (a note only)
TOP = 10
GOAL_LABELS = {"lighting": "Low Sun on bare ground", "shadows": "Driving in long shadows",
               "geology": "Geology training", "full": "Full match"}
SOUTH_LABEL = ("snow not measured: hours are for 27 November to 1 March, "
               "when the rock maps show the ground bare")
# Whole regions already used as analogs, beyond the point list in known_analogs.json.
KNOWN_REGIONS = {
    "Iceland": "named in the challenge as widely studied",
    "Svalbard": "named in the challenge; used by the AMASE Mars campaigns",
}
# (name, south, north, west, east, why): classic analog areas larger than the 50 km around their listed point.
# Devon Island is three boxes so that they stop at the water: Jones Sound lies between its north coast
# (near 75.9 N east of 89 W) and Ellesmere Island (from 76.3 N), and Cardigan Strait between its
# north-west and North Kent Island (90.7 to 89.8 W). Checked against the land cells of landcover_cells.json.
KNOWN_AREAS = [
    ("Devon Island", 74.4, 76.0, -92.5, -79.3, "classic analog site (Haughton-Mars Project)"),
    ("Devon Island (north-west)", 76.0, 76.42, -97.0, -89.0, "classic analog site (Haughton-Mars Project)"),
    ("Devon Island (north-west)", 76.42, 77.1, -97.0, -91.0, "classic analog site (Haughton-Mars Project)"),
    ("McMurdo Dry Valleys", -78.5, -76.5, 159.5, 164.5, "classic Moon and Mars analog site"),
]


def load(path: Path, default=None):
    return json.loads(path.read_text()) if path.exists() else default


def write_text(path: Path, text: str) -> None:
    """Write beside the old file and rename into place, so a reader never sees half a file."""
    side = path.with_name(path.name + ".part")
    side.write_text(text)
    os.replace(side, path)


def from_first_method(path: Path) -> bool:
    """Whether a results file was written by the first method: the only kind keep_old_results may rename.

    The first method wrote cells_scored.json as a bare list, validation.json without a "meta" block, and a
    ranking.txt that begins "scored cells:". A file that cannot be read is left alone.
    """
    try:
        if path.suffix != ".json":
            return path.read_text().startswith(FIRST_RANKING_START)
        content = json.loads(path.read_text())
    except (OSError, ValueError):
        return False
    if path.name == "cells_scored.json":
        return isinstance(content, list)
    return isinstance(content, dict) and "meta" not in content


def keep_old_results(folder: Path = DERIVED) -> list[str]:
    """Rename the first method's results to their _v1 names, once; a kept copy is never overwritten.

    A file of the new method is never renamed, whether or not a _v1 copy exists.
    """
    kept = []
    for old, new in OLD_RESULTS.items():
        if (folder / old).exists() and not (folder / new).exists() and from_first_method(folder / old):
            os.replace(folder / old, folder / new)
            kept.append(new)
    return kept


def known_area(lat: float, lon: float) -> str | None:
    for name, south, north, west, east, why in KNOWN_AREAS:
        if south <= lat <= north and west <= lon <= east:
            return f"{name}: {why}"
    return None


def used_body(body: str | None, bodies: list[dict]) -> str | None:
    """Why a cell's anorthosite body counts as already used: the rock list marks it as not novel (a simulant mine, a training site)."""
    for listed in bodies:
        if body is not None and listed["name"] == body and listed.get("novel") is False:
            return f"{body}: {listed.get('existing_use') or 'already used'}"
    return None


def known_region(cell: dict, south_sites: list[dict]) -> str | None:
    """Why the place around a cell counts as already used: a known region, a classic area, or a southern site with analog use."""
    if cell["region"] in KNOWN_REGIONS:
        return f"{cell['region']}: {KNOWN_REGIONS[cell['region']]}"
    area = known_area(cell["lat"], cell["lon"])
    if area:
        return area
    for site in south_sites:
        if site.get("existing_analog_use") and reference.haversine_km(
                cell["lat"], cell["lon"], site["lat"], site["lon"]) <= KNOWN_SITE_KM:
            return f"{site['name']}: {site['existing_analog_use']}"
    return None


def terrain_parts(terrain: dict | None) -> tuple[dict | None, str | None]:
    """The terrain numbers of a cell for its record, or None with the reason they are missing."""
    if terrain is None:
        return None, "not computed"
    if "overlap" not in terrain:
        if "skipped" in terrain:
            if str(terrain["skipped"]).startswith(score.TILE_NOT_FETCHED):
                return None, f"not computed: {score.TILE_NOT_FETCHED}"   # held back for an elevation tile, not refused
            return None, f"window refused: {terrain['skipped']}"
        return None, f"too few land pixels with a slope ({terrain.get('slope_pixels')})"
    kept = {k: terrain.get(k) for k in ("median_slope_deg", "p90_slope_deg", "relief_m", "valid_share")}
    return {**kept, "overlap": dict(terrain["overlap"])}, None


def rounded(value, digits: int = 3):
    return None if value is None else round(value, digits)


def scored_record(cell: dict, terrain: dict | None, targets: list[dict], self_overlap: dict,
                  bodies: list[dict], known_sites: list[dict], south_sites: list[dict]) -> dict:
    """One cell of grazing_cells.json with its terrain, rock, factor scores and goal scores per target.

    light uses the terrain horizon and is None without one; light_flat (flat
    horizon) is kept for counts and for the with-and-without comparison, and
    goals_flat are the goals it would give. Nothing unknown is turned into 0.
    """
    south = cell["hemisphere"] == "S"
    land, terrain_note = terrain_parts(terrain)
    rock, body = reference.rock_match(cell["lat"], cell["lon"], bodies, ROCK_MARGIN_KM)
    known = reference.nearest_known(cell["lat"], cell["lon"], known_sites, KNOWN_SITE_KM)
    region_note = known_region(cell, south_sites) or used_body(body, bodies)
    reasons = score.not_ranked_because(cell)
    per_target = {}
    for t in targets:
        values = cell["targets"][t["id"]]
        overlap = None if land is None else land["overlap"].get(t["id"])
        factors = {"light": score.light_score(score.light_hours(values, cell["hemisphere"])),
                   "terrain": score.terrain_score(overlap, self_overlap.get(t["id"])),
                   "bare": cell["bare"], "rock": rock}
        flat = {**factors, "light": score.light_score(score.light_hours(values, cell["hemisphere"], "flat"))}
        per_target[t["id"]] = {
            **values, **score.rounded_factors(factors),
            "light_flat": score.rounded_factors(flat)["light"], "terrain_overlap": overlap,
            "goals": score.published_goals(factors), "goals_flat": score.published_goals(flat),
        }
    return {
        "id": cell["id"], "lat": cell["lat"], "lon": cell["lon"], "hemisphere": cell["hemisphere"],
        "region": cell["region"], "gridded": cell.get("gridded", True), "site_name": cell.get("site_name"),
        "bare": cell["bare"], "bare_km2": cell.get("bare_km2"), "land_share": rounded(cell.get("land_share")),
        "layers_disagree": cell.get("layers_disagree"),
        "snow": cell["snow"], "horizon": cell.get("horizon"),
        "terrain": land, "terrain_note": terrain_note,
        "rock": {"score": round(rock, 3), "body": body},
        "known": None if known is None else {**known, "distance_km": round(known["distance_km"], 1)},
        "known_region": region_note, "little_known": known is None and region_note is None,
        "ranking": "south" if south else "north",
        "ranked": not reasons, "not_ranked_because": reasons,
        "ranked_flat": not score.not_ranked_because(cell, need_horizon=False),
        "targets": per_target,
    }


def top_bins_in(long_hours, allowed_bins, count: int = 3) -> list[list]:
    """The allowed bins with the most long-window hours, best first, as [bin, hours].

    long_hours are per ten-day bin and already count long spells only (the long_* arrays of
    grazing_bins.npz). Unknown bins and bins whose hours round to 0.0 are left out.
    """
    hours = np.asarray(long_hours, dtype=float)
    allowed = np.zeros(len(hours), dtype=bool)
    allowed[list(allowed_bins)] = True
    usable = np.where(allowed & np.isfinite(hours), hours, 0.0)
    order = np.argsort(-usable, kind="stable")[:count]
    return [[int(b), round(float(usable[b]), 1)] for b in order if round(float(usable[b]), 1) > 0.0]


def poleward_sectors(hemisphere: str) -> list[int]:
    """Sectors with the Sun within 90 degrees of north (north) or of south (south): the midnight-Sun side."""
    quarter = sun.AZ_SECTORS // 4
    if hemisphere == "N":
        return list(range(0, quarter)) + list(range(3 * quarter, sun.AZ_SECTORS))
    return list(range(quarter, 3 * quarter))


def load_bins(bins_file: Path, names) -> dict:
    """Arrays of grazing_bins.npz, read once (an open .npz unpacks an array again on every look)."""
    with np.load(bins_file) as packed:
        return {name: packed[name] for name in names}


def add_southern_summer(records: list[dict], meta: dict, bins_file: Path) -> None:
    """For southern records: the best bins and the Sun's side within the rock season only.

    The cells file gives a southern cell's top bins and poleward share over the
    whole year, which includes the low noon Sun of the southern winter, when
    nothing says the ground is bare. The ranking counts 27 November to 1 March
    only, so its dates and its side note must come from those bins too. Both use
    the per-day long spells: the stored long_open (or long_flat) hours per bin,
    and sun.long_band_minutes_table for the Sun's side.
    """
    south = [r for r in records if r["hemisphere"] == "S"]
    if not south:
        return
    archive = load_bins(bins_file, ("ids", "long_flat", "long_open"))
    row = {cid: i for i, cid in enumerate(archive["ids"].tolist())}
    season = meta["summer_bins_south"]
    in_season = np.zeros(sun.N_BINS, dtype=bool)
    in_season[season] = True
    lats = sorted({r["lat"] for r in south})
    place = {lat: k for k, lat in enumerate(lats)}
    # the same calendars and step as the cells file's hours (its meta), not the module's default: a cells file
    # from before the phases were added has no year_phases and was made with one calendar at 1-minute steps
    minutes = sun.long_band_minutes_table(lats, [t["limit_deg"] for t in meta["targets"]], meta["stretch_min_h"],
                                          step_minutes=meta.get("step_minutes", 1), year_phases=meta.get("year_phases", 1))
    for r in south:
        i = row[r["id"]]
        for t, target in enumerate(meta["targets"]):
            values = r["targets"][target["id"]]
            opened = archive["long_open"][i, t]
            hours = opened if np.isfinite(opened).any() else archive["long_flat"][i, t]
            values["top_bins_summer_rock"] = top_bins_in(hours, season)
            share = grazing.poleward_share(minutes[t, place[r["lat"]]], target["elev_bins"], in_season, "S")
            values["poleward_share_summer_rock"] = round(float(share), 3) if np.isfinite(share) else None


def add_cloud(records: list[dict], meta: dict, bins_file: Path, cloud_cells: dict | None) -> None:
    """Join the cloud column: each record's monthly cloud percent and, per target, its typical clear-sky hours.

    Clear-sky hours are the long-window open hours of each ten-day bin times the
    clear share of the bin's month (twinfinder.cloud.clear_share_by_bin), summed
    over the year and over the winter and summer halves; for southern records
    over the rock season, where the open hours count the terrain only. A record
    without a cloud figure, or without open hours, gets None, never 0. Nothing
    here touches a factor or a goal score.
    """
    archive = load_bins(bins_file, ("ids", "long_open"))
    row = {cid: i for i, cid in enumerate(archive["ids"].tolist())}
    winter, summer, rock = meta["winter_bins_north"], meta["summer_bins_north"], meta["summer_bins_south"]
    for r in records:
        entry = (cloud_cells or {}).get(r["id"]) or {}
        pct = entry.get("cloud_pct")
        r["cloud"] = {"pct_by_month": pct, "grid": entry.get("grid") if pct is not None else None}
        share = None if pct is None else cloud.clear_share_by_bin(pct)
        north = r["hemisphere"] == "N"
        for t, target in enumerate(meta["targets"]):
            hours = archive["long_open"][row[r["id"]], t]

            def clear(bins=None):
                return rounded(score.clear_hours(hours, share, bins), 1)

            r["targets"][target["id"]].update({
                "long_open_hours_clear": clear() if north else None,
                "long_open_hours_clear_winter": clear(winter) if north else None,
                "long_open_hours_clear_summer": clear(summer) if north else None,
                "long_summer_rock_open_hours_clear": None if north else clear(rock)})


def clear_sky_hours(target_values: dict, hemisphere: str) -> float | None:
    """The clear-sky figure that goes with a record's light hours: the year in the north, the rock season in the south."""
    return target_values.get("long_open_hours_clear" if hemisphere == "N" else "long_summer_rock_open_hours_clear")


def bin_dates(b: int) -> str:
    """A ten-day bin as dates, such as 20 Jun-29 Jun; the last bin runs to the end of the year."""
    first = b * sun.BIN_DAYS + 1
    last = 365 if b == sun.N_BINS - 1 else first + sun.BIN_DAYS - 1
    return f"{sun.doy_to_label(first)}-{sun.doy_to_label(last)}"


def bins_note(top_bins: list) -> str:
    """The best bins as dates and whole hours; under one hour a decimal is kept, so nothing reads as 0 h."""
    return ", ".join(f"{bin_dates(b)} ({hours:.{0 if hours >= 1.0 else 1}f} h)" for b, hours in top_bins) or "none"


def side_note(poleward_share: float | None, hemisphere: str) -> str:
    """Where the low Sun stands during the long windows: the midnight-Sun side or the equator side."""
    if poleward_share is None:
        return "no long window"
    pole, equator = ("north", "south") if hemisphere == "N" else ("south", "north")
    if poleward_share >= 0.5:
        return f"{poleward_share:.0%} midnight-Sun side (Sun in the {pole})"
    return f"{1 - poleward_share:.0%} equator side (Sun in the {equator}: dawn, dusk, low noon)"


def ranked_sites(records: list[dict], tid: str, goal: str, ranking: str, top: int = TOP,
                 little_known_only: bool = False, flat: bool = False) -> list[dict]:
    """The best sites of one ranking ("north" or "south") for a target and goal, one per 50 km.

    Only ranked cells with a known goal score enter. flat=True ranks by the
    flat-horizon light instead and does not ask for a horizon; it is used for
    the comparison with the real horizon and for a preview before horizons exist.
    """
    cells, key = rankable(records, tid, goal, ranking, little_known_only, flat)
    return score.top_sites(cells, key=key, top=top, tie_key=tie_key(tid, flat))


def tie_key(tid: str, flat: bool = False):
    """Among equal scores the cell with more long-window hours comes first (the light score stops at full marks)."""
    return lambda r: score.tie_hours(r["targets"][tid], r["hemisphere"], "flat" if flat else "open")


def rankable(records: list[dict], tid: str, goal: str, ranking: str, little_known_only: bool = False,
             flat: bool = False) -> tuple[list[dict], object]:
    """The cells one table may draw on, and the stored score it orders them by."""
    allowed, goals = ("ranked_flat", "goals_flat") if flat else ("ranked", "goals")
    cells = [r for r in records if r["ranking"] == ranking and r[allowed]
             and (not little_known_only or r["little_known"])]
    return cells, lambda r: r["targets"][tid][goals][goal]


def cut_tie(cells: list[dict], sites: list[dict], key, top: int = TOP) -> tuple[float, int] | None:
    """When a full table ends among equal scores: that score and how many cells hold it, else None.

    Cells with equal scores are ordered by their long-window hours, so a full
    table shows the ones with the most hours, and it says that others score the same.
    """
    if len(sites) < top:
        return None
    last = key(sites[-1])
    equal = sum(1 for c in cells if key(c) == last)
    return (last, equal) if equal > sum(1 for s in sites if key(s) == last) else None


def number(value, width: int, digits: int = 2) -> str:
    return f"{'-':>{width}s}" if value is None else f"{value:{width}.{digits}f}"


def row_notes(r: dict) -> str:
    notes = []
    if r["rock"]["body"]:
        notes.append(f"rock: {r['rock']['body']}")
    if r["known"]:
        notes.append(f"KNOWN: {r['known']['name']} (tier {r['known']['tier']}, {r['known']['distance_km']:.0f} km)")
    elif r["known_region"]:
        notes.append(f"KNOWN AREA: {r['known_region']}")
    pixels = r["snow"].get("land_pixels")
    if pixels is not None and pixels < MIN_SNOW_LAND_PIXELS:
        notes.append(f"snow odds thin ({pixels} of {r['snow'].get('block_pixels') or 9} pixels)")
    if r["layers_disagree"]:
        notes.append("rock layers disagree")
    if r["terrain_note"]:
        notes.append(f"terrain {r['terrain_note']}")
    return " | ".join(notes)


TABLE_HEAD = ("  score  lat     lon      region                             bare  hours   flat  clear  light terrain rock"
              "  best ten-day bins | where the Sun stands | notes")


def site_row(r: dict, tid: str, goal: str, flat: bool = False) -> str:
    t = r["targets"][tid]
    south = r["hemisphere"] == "S"
    bins = t.get("top_bins_summer_rock", []) if south else t["top_bins"]
    share = t.get("poleward_share_summer_rock") if south else t["poleward_share"]
    tail = " | ".join(part for part in (bins_note(bins), side_note(share, r["hemisphere"]), row_notes(r)) if part)
    return (f"  {t['goals_flat' if flat else 'goals'][goal]:.2f}  {r['lat']:6.2f} {r['lon']:8.2f}  {r['region'][:33]:33s}  "
            f"{r['bare']:.2f} {number(score.light_hours(t, r['hemisphere']), 6, 0)} "
            f"{number(score.light_hours(t, r['hemisphere'], 'flat'), 6, 0)} {number(clear_sky_hours(t, r['hemisphere']), 6, 0)}  "
            f"{number(t['light_flat' if flat else 'light'], 5)}  "
            f"{number(t['terrain'], 5)}  {number(t['rock'], 4)}  {tail}")


def ranking_table(records, target: dict, goal: str, ranking: str, little_known_only=False, flat=False) -> list[str]:
    sites = ranked_sites(records, target["id"], goal, ranking, little_known_only=little_known_only, flat=flat)
    scope = "little-known sites only" if little_known_only else "all sites"
    lines = ["", f"{GOAL_LABELS[goal]} | {target['name']} (Sun at or below {target['limit_deg']:.2f} deg) | {scope}"]
    if not sites:
        return lines + ["  no ranked cell scores above zero"]
    lines += [TABLE_HEAD] + [site_row(r, target["id"], goal, flat) for r in sites]
    cells, key = rankable(records, target["id"], goal, ranking, little_known_only, flat)
    tie = cut_tie(cells, sites, key)
    if tie:
        lines.append(f"  note: {tie[1]} ranked cells share the score {tie[0]:.3f} of the last site shown; among equal scores "
                     "the cells with more long-window hours come first, so the cells left out score the same with fewer hours.")
    return lines


def ranking_section(records, targets, ranking: str, flat: bool = False) -> list[str]:
    """Every table of one ranking: per target each goal, and the little-known sites for the two light goals."""
    lines = []
    for target in targets:
        for goal in score.GOALS:
            lines += ranking_table(records, target, goal, ranking, flat=flat)
        for goal in ("lighting", "shadows"):
            lines += ranking_table(records, target, goal, ranking, little_known_only=True, flat=flat)
    return lines


def doubtful_table(cells: list[dict], targets: list[dict]) -> list[str]:
    """Gridded cells whose snow odds are doubtful or missing: listed with both versions of their hours, not ranked."""
    listed = [c for c in cells if c.get("gridded", True) and c["snow"]["status"] in ("doubtful", "no data")]
    lines = ["", f"DOUBTFUL SNOW OR NO SNOW DATA: {len(listed)} gridded cells, listed and not ranked",
             "  Long-window snow-free hours per target: with the stale-flag rule / as the maps read / with the terrain horizon.",
             "  lat     lon      region                     bare  status    stuck pixels  "
             + "  ".join(f"{t['id']:>20s}" for t in targets)]
    for c in sorted(listed, key=lambda c: (c["snow"]["status"], -c["lat"], c["lon"])):
        hours = "  ".join(f"{number(v.get('long_snow_free_hours_with_rule', v['long_snow_free_hours']), 6, 0)}"
                          f"/{number(v['long_snow_free_hours_as_mapped'], 6, 0)}"
                          f"/{number(v['long_open_hours'], 6, 0)}" for v in (c["targets"][t["id"]] for t in targets))
        lines.append(f"  {c['lat']:6.2f} {c['lon']:8.2f}  {c['region'][:25]:25s}  {c['bare']:.2f}  {c['snow']['status']:8s}  "
                     f"{c['snow']['stuck_winters']:5d} {c['snow']['land_pixels']:6d}  {hours}")
    return lines


def named_sites(south_sites: list[dict]) -> list[tuple[str, float, float]]:
    return list(NAMED_SITES_NORTH) + [(s["name"], s["lat"], s["lon"]) for s in south_sites]


def named_sites_table(record_of, targets: list[dict], south_sites: list[dict]) -> list[str]:
    """Each named place on its own cell, whatever the screens say; these never enter the gridded counts."""
    lines = ["", "NAMED SITES: reported on their own, never inside the gridded counts",
             "  Per target: long-window hours flat / snow-free / open (north); flat / open in the rock season (south); "
             "then the terrain score."]
    for name, lat, lon in named_sites(south_sites):
        r = record_of(grid.cell_id(lat, lon))
        if r is None:
            lines.append(f"  {name}: its cell {grid.cell_id(lat, lon)} is not in grazing_cells.json")
            continue
        horizon = r["horizon"] or {}
        lines.append(f"  {name} | cell {r['id']} | bare {number(r['bare'], 4)} | snow {r['snow']['status']} | "
                     f"horizon north {number(horizon.get('north_deg'), 4, 1)} south {number(horizon.get('south_deg'), 4, 1)} | "
                     f"rock {r['rock']['score']:.2f} ({r['rock']['body']}) | "
                     f"{'ranked' if r['ranked'] else 'not ranked: ' + ', '.join(r['not_ranked_because'])}")
        for t in targets:
            v = r["targets"][t["id"]]
            if r["hemisphere"] == "N":
                hours = (f"{number(v['long_flat_hours'], 6, 0)} /{number(v['long_snow_free_hours'], 6, 0)} /"
                         f"{number(v['long_open_hours'], 6, 0)}")
            else:
                hours = f"{number(v['long_summer_rock_hours'], 6, 0)} /{number(v['long_summer_rock_open_hours'], 6, 0)}"
            lines.append(f"      {t['name']:42s} {hours}   terrain {number(v['terrain'], 4)}")
    return lines


def candidate_ids(cells: dict) -> tuple[list[str], str]:
    """The cells to score: candidates.json when it exists, else every cell with a horizon."""
    listed = load(DERIVED / "candidates.json")
    if listed is not None:
        return [c["id"] for c in listed if c["id"] in cells], "candidates.json"
    return [cid for cid, c in cells.items() if c.get("horizon") is not None], "every cell with a horizon"


def counts(records: list[dict]) -> dict:
    reasons: dict[str, int] = {}
    for r in records:
        for reason in r["not_ranked_because"]:
            reasons[reason] = reasons.get(reason, 0) + 1
    return {"records": len(records),
            "with_a_horizon": sum(bool(r["horizon"]) and "skipped" not in r["horizon"] for r in records),
            "with_terrain": sum(r["terrain"] is not None for r in records),
            "ranked_north": sum(r["ranked"] and r["ranking"] == "north" for r in records),
            "ranked_south": sum(r["ranked"] and r["ranking"] == "south" for r in records),
            "not_ranked_because": dict(sorted(reasons.items()))}


def main() -> None:
    kept = keep_old_results()
    if kept:
        print("kept the first method's results as: " + ", ".join(kept))
    grazing = load(DERIVED / "grazing_cells.json")
    meta, cells = grazing["meta"], {c["id"]: c for c in grazing["cells"]}
    targets = meta["targets"]
    # A region without a NASA 5 m terrain model has no slopes: its self-overlap is None, so its terrain factor
    # and the goals that use the terrain are unknown (None), never 0.
    self_overlap = {t["id"]: ((t.get("terrain") or {}).get("90m") or {}).get("self_overlap_10km", {}).get("median")
                    for t in load(DERIVED / "moon_targets.json")}
    terrain = load(DERIVED / "terrain_cells.json", {})
    bodies = load(REFERENCE / "anorthosite_bodies.json", [])
    known_sites = load(REFERENCE / "known_analogs.json", [])
    south_sites = load(REFERENCE / "antarctic_sites.json", [])

    def build(cid: str) -> dict:
        return scored_record(cells[cid], terrain.get(cid), targets, self_overlap, bodies, known_sites, south_sites)

    ids, source = candidate_ids(cells)
    records = [build(cid) for cid in ids]
    by_id = {r["id"]: r for r in records}
    extra = [build(grid.cell_id(lat, lon)) for _, lat, lon in named_sites(south_sites)
             if grid.cell_id(lat, lon) in cells and grid.cell_id(lat, lon) not in by_id]
    add_southern_summer(records + extra, meta, DERIVED / "grazing_bins.npz")
    cloud_file = load(CLOUD)
    add_cloud(records + extra, meta, DERIVED / "grazing_bins.npz", (cloud_file or {}).get("cells"))
    by_id.update({r["id"]: r for r in extra})

    tally = counts(records)
    preview = tally["with_a_horizon"] == 0
    out_meta = {
        "written": datetime.now().isoformat(timespec="seconds"), "cells_from": source,
        "full_hours": score.FULL_HOURS, "rank_min_bare": score.RANK_MIN_BARE, "same_site_km": score.SAME_SITE_KM,
        "stretch_min_h": meta["stretch_min_h"], "long_rule": meta.get("long_rule"),
        "goals": {g: list(f) for g, f in score.GOALS.items()},
        "targets": [{"id": t["id"], "name": t["name"], "limit_deg": t["limit_deg"],
                     "self_overlap_median": (None if self_overlap.get(t["id"]) is None
                                             else round(self_overlap[t["id"]], 4)),
                     "has_model": t.get("has_model", self_overlap.get(t["id"]) is not None)} for t in targets],
        "south_label": SOUTH_LABEL, "counts": tally,
        "grazing_horizons": meta.get("horizons"), "terrain_cells_in_file": len(terrain),
        "cloud": {"file": CLOUD.name if cloud_file else None, "enters_a_score": False, "note": CLOUD_NOTE,
                  "records_with_a_cloud_figure": sum(r["cloud"]["pct_by_month"] is not None for r in records),
                  **{key: (cloud_file or {}).get("meta", {}).get(key) for key in ("source", "parameter", "period", "grid_deg")}},
    }
    write_text(OUT, json.dumps({"meta": out_meta, "cells": records}, separators=(",", ":")))

    lines = [f"LuniMartian Atlas ranking, written {out_meta['written']}.",
             f"Cells scored: {tally['records']} (from {source}); with a horizon: {tally['with_a_horizon']}; "
             f"with terrain: {tally['with_terrain']}; ranked north: {tally['ranked_north']}; "
             f"ranked south: {tally['ranked_south']}.",
             f"Not ranked because: {json.dumps(tally['not_ranked_because'])}",
             "", "How to read the tables",
             f"  hours   long-window grazing hours a year behind the light score: Sun above the horizon and at or below the",
             f"          lunar site's limit, inside unbroken spells of at least {meta['stretch_min_h']:g} h (followed day by day), on",
             "          snow-free ground and clear of the terrain (north); in the south 27 November to 1 March, clear of the terrain.",
             "  flat    the same hours over a flat horizon (no terrain).",
             "  clear   typical clear-sky hours: the hours column, each ten-day bin times the share of the sky that is clear",
             "          in its month (NASA POWER monthly mean cloud amount, all hours of day and night, 2001 to 2025, on a",
             "          grid about 100 km across). This is not the chance that a low Sun is visible, and it enters no score.",
             f"  light   min(1, hours / {score.FULL_HOURS:g}).   terrain   slope overlap with the lunar site / the site's overlap with itself.",
             "  score   geometric mean of the goal's factors: " + "; ".join(
                 f"{GOAL_LABELS[g]} = {' x '.join(f)}" for g, f in score.GOALS.items()) + ".",
             "  where the Sun stands   share of the long-window flat-horizon hours with the Sun within 90 degrees of the pole",
             "          (the midnight-Sun side) or on the equator side; whole year in the north, the rock season in the south.",
             "  best ten-day bins   the three long-window bins with the most hours (open hours where a horizon exists).",
             f"  One site per {score.SAME_SITE_KM:g} km; cells with bare ground under {score.RANK_MIN_BARE:g} are not ranked.",
             "", "NORTH: measured cells with a horizon"]
    lines += ranking_section(records, targets, "north")
    if preview:
        lines += ["", "PREVIEW, NOT A RANKING: no cell has a horizon yet, so the tables below use the flat-horizon light",
                  "(snow-free hours without terrain). They are replaced once the horizons are computed."]
        lines += ranking_section(records, targets, "north", flat=True)
    lines += doubtful_table(list(cells.values()), targets)
    lines += named_sites_table(by_id.get, targets, south_sites)
    lines += ["", f"SOUTH: {SOUTH_LABEL}", f"  light = min(1, long_summer_rock_open_hours / {score.FULL_HOURS:g})."]
    lines += ranking_section(records, targets, "south")
    if preview:
        lines += ["", "PREVIEW, NOT A RANKING (south): flat-horizon hours of 27 November to 1 March, no terrain."]
        lines += ranking_section(records, targets, "south", flat=True)
    write_text(RANKING, "\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\nwrote {OUT} and {RANKING}")


if __name__ == "__main__":
    main()

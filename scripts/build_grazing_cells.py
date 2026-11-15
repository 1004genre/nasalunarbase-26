# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Grazing hours per lunar target for every screened cell, north and south, and for the cells of the named sites.

Writes data/derived/grazing_cells.json (one record per cell) and
data/derived/grazing_bins.npz (the same hours split by ten-day bin). Safe to
run again: both files are written beside the old ones and renamed into place.

Long-window hours are counted per day (sun.long_band_minutes_table): the time
inside unbroken low-Sun spells of at least grazing.STRETCH_MIN_H hours. Every
Sun table is the mean over grazing.YEAR_PHASES (eight) calendars an eighth of a
day apart (spread over the phases of the leap cycle); with four phases the build
took 3.5 to 6 minutes, with eight expect 7 to 12 minutes.
"""
import json
import os
from datetime import datetime
from pathlib import Path

import numpy as np

from twinfinder import grazing, grid, regions, rock_south, sun

NORTH = Path("data/derived/landcover_cells.json")
SOUTH = Path("data/derived/landcover_cells_south.json")
SITES_SOUTH = Path("data/reference/antarctic_sites.json")
SNOW = Path("data/derived/snow_free_dekads.npz")
HORIZONS = Path("data/derived/horizon_cells.json")
OUT = Path("data/derived/grazing_cells.json")
OUT_BINS = Path("data/derived/grazing_bins.npz")
MIN_BARE = 0.15         # the bare-ground screen, north and south
MIN_LAND_SOUTH = 0.2    # the northern file was already cut at this land share when it was built
BIN_ARRAYS = ("flat", "snow_free", "open", "stretch", "long_flat", "long_snow_free", "long_open")

projected_once = grazing.projected_once   # moved to grazing.py with the rest of the join; the old names still work
terrain_hours = grazing.terrain_hours


def base_record(cell: dict, gridded: bool) -> dict:
    """What is kept of a land-cover record. gridded: the cell passes its hemisphere's screen and is counted."""
    return {"id": cell["id"], "lat": cell["lat"], "lon": cell["lon"], "hemisphere": grazing.hemisphere(cell["lat"]),
            "bare": cell["bare"], "land_share": cell["land_share"],
            "layers_disagree": cell.get("layers_disagree"), "gridded": gridded}


def screened(north: list[dict], south: list[dict]) -> list[dict]:
    """The gridded cells: north with enough bare ground, south with enough bare ground and enough land."""
    return ([base_record(c, True) for c in north if c["bare"] >= MIN_BARE]
            + [base_record(c, True) for c in south if c["bare"] >= MIN_BARE and c["land_share"] >= MIN_LAND_SOUTH])


def named_sites() -> list[tuple[str, float, float]]:
    """Every named site, north and south, as (name, lat, lon)."""
    south = [(s["name"], s["lat"], s["lon"]) for s in json.loads(SITES_SOUTH.read_text())]
    return list(grazing.NAMED_SITES_NORTH) + south


def add_named_sites(cells: list[dict], everything: dict[str, dict], sites) -> None:
    """Mark the cell of each named site, adding it when the screen left it out.

    A site's cell is kept whatever its bare or land share. If no land-cover
    file has the cell, the record is made from the grid alone and its bare and
    land shares are unknown.
    """
    by_id = {c["id"]: c for c in cells}
    for name, lat, lon in sites:
        cid = grid.cell_id(lat, lon)
        if cid not in by_id:
            if cid in everything:
                by_id[cid] = base_record(everything[cid], False)
            else:
                centre_lat, centre_lon = grid.cell_centre(cid)
                by_id[cid] = {"id": cid, "lat": round(centre_lat, 2), "lon": round(centre_lon, 2),
                              "hemisphere": grazing.hemisphere(centre_lat), "bare": None, "land_share": None,
                              "layers_disagree": None, "gridded": False}
            cells.append(by_id[cid])
        cell = by_id[cid]
        cell["site_name"] = f"{cell['site_name']} / {name}" if cell.get("named_site") else name
        cell["named_site"] = True


def horizons_of_cells(cells: list[dict]) -> tuple[list, dict[int, np.ndarray]]:
    """Each cell's horizon summary for the record (None when it has none) and the open shares by cell number."""
    return grazing.horizons_of_cells(cells, HORIZONS)


def low_sun_days_per_bin(lats, limit: float) -> np.ndarray:
    """All-day low-Sun days in each ten-day bin, [latitudes, 36]."""
    return np.stack([grazing.days_per_bin(sun.low_sun_days(lat, limit)) for lat in lats])


def target_values(target: dict, minutes, long_minutes, stretch_t, lats, lat_of_cell, cells, snow_of, shares):
    """One target for all cells: the per-cell dicts and the hours per ten-day bin, named as in grazing_bins.npz.

    minutes is the all-hours Sun table [latitudes, ...], long_minutes the long-spell table of this
    target's limit, stretch_t the median longest stretch [latitudes, 36] (information only).
    """
    bins = target["elev_bins"]
    north = np.array([c["hemisphere"] == "N" for c in cells])
    odds = snow_of["odds"]
    every = grazing.hours_by_bin(minutes, bins, lat_of_cell, north, odds, shares)
    long = grazing.hours_by_bin(long_minutes, bins, lat_of_cell, north, odds, shares)
    stretch = stretch_t[lat_of_cell].astype(float)
    days = low_sun_days_per_bin(lats, target["limit_deg"])
    out = [None] * len(cells)
    for side in ("N", "S"):
        rows = np.flatnonzero(north == (side == "N"))
        if not len(rows):
            continue
        which = lat_of_cell[rows]
        sums = grazing.target_sums(side, every["flat"][rows], long["flat"][rows], every["terrain"][rows],
                                   long["terrain"][rows], stretch[rows], odds[rows],
                                   snow_of["as_mapped"][rows], snow_of["with_rule"][rows])
        share_by_lat = grazing.poleward_share(long_minutes, bins, None, side)
        basis = grazing.top_bins_basis(side, long["flat"][rows], long["snow_free"][rows], long["open"][rows])
        usable = grazing.usable_days(days[which], odds[rows]) if side == "N" else np.full(len(rows), np.nan)
        for k, values in enumerate(grazing.rows(sums)):
            values["poleward_share"] = grazing.known(share_by_lat[which[k]], 3)
            values["top_bins"] = grazing.top_bins(basis[k])
            values["all_day_days"] = int(days[which[k]].sum())
            values["usable_days"] = grazing.known(usable[k])
            out[rows[k]] = values
    by_bin = {"flat": every["flat"], "snow_free": every["snow_free"], "open": every["open"], "stretch": stretch,
              "long_flat": long["flat"], "long_snow_free": long["snow_free"], "long_open": long["open"]}
    return out, by_bin


def finished_record(cell: dict, snow_summary: dict, horizon_summary, per_target: dict) -> dict:
    """One cell as it is written: place, ground, snow, horizon and the values per target."""
    cell_km2 = rock_south.cell_area_km2(cell["id"])   # ellipsoid area between the cell's edges; same formula both hemispheres
    known_ground = cell["bare"] is not None and cell["land_share"] is not None
    record = {
        "id": cell["id"], "lat": cell["lat"], "lon": cell["lon"], "hemisphere": cell["hemisphere"],
        "region": regions.region(cell["lat"], cell["lon"]),
        "bare": cell["bare"], "land_share": cell["land_share"], "cell_km2": round(cell_km2, 3),
        "bare_km2": round(cell_km2 * cell["land_share"] * cell["bare"], 3) if known_ground else None,
        "layers_disagree": cell["layers_disagree"], "gridded": cell["gridded"],
    }
    if cell.get("named_site"):
        record["named_site"], record["site_name"] = True, cell["site_name"]
    record["snow"], record["horizon"], record["targets"] = snow_summary, horizon_summary, per_target
    return record


def counts(records: list[dict]) -> dict:
    """Counts over the gridded cells only; named-site cells that the screen left out are not in them."""
    gridded = [r for r in records if r["gridded"]]
    by_status = {status: 0 for status in ("measured", "doubtful", "no data", "unmeasured")}
    for r in gridded:
        by_status[r["snow"]["status"]] += 1
    return {"north_cells": sum(r["hemisphere"] == "N" for r in gridded),
            "south_cells": sum(r["hemisphere"] == "S" for r in gridded),
            "by_snow_status": by_status,
            "named_site_cells": sum(bool(r.get("named_site")) for r in records),
            "named_site_cells_outside_the_screen": sum(not r["gridded"] for r in records)}


def write_json(path: Path, value) -> None:
    side = path.with_name(path.name + ".part")
    side.write_text(json.dumps(value, separators=(",", ":")))
    os.replace(side, path)


def write_bins(path: Path, **arrays) -> None:
    side = path.with_name("part_" + path.name)   # numpy insists on the .npz ending
    np.savez_compressed(side, **arrays)
    os.replace(side, path)


def main() -> None:
    grazing.check_shared_bins()
    targets = grazing.load_targets()
    north, south = json.loads(NORTH.read_text()), json.loads(SOUTH.read_text())
    cells = screened(north, south)
    add_named_sites(cells, {c["id"]: c for c in north + south}, named_sites())

    archive = np.load(SNOW)
    snow_of = grazing.snow_of_cells(cells, archive)
    horizon_summaries, shares = horizons_of_cells(cells)

    lats = sorted({c["lat"] for c in cells})
    lat_of_cell = np.array([lats.index(c["lat"]) for c in cells])
    limits = [t["limit_deg"] for t in targets]
    phases = grazing.YEAR_PHASES    # the same calendars for all three, so long hours never exceed all hours
    minutes = sun.band_minutes_table(lats, step_minutes=grazing.STEP_MINUTES, year_phases=phases)
    long_minutes = sun.long_band_minutes_table(lats, limits, grazing.STRETCH_MIN_H, grazing.STEP_MINUTES, year_phases=phases)
    stretch = sun.longest_stretch_hours_table(lats, limits, year_phases=phases)

    per_cell = [{} for _ in cells]
    binned = {name: np.empty((len(cells), len(targets), sun.N_BINS), dtype=np.float32) for name in BIN_ARRAYS}
    for t, target in enumerate(targets):
        values, by_bin = target_values(target, minutes, long_minutes[t], stretch[:, :, t], lats, lat_of_cell, cells,
                                       snow_of, shares)
        for i, one in enumerate(values):
            per_cell[i][target["id"]] = one
        for name in BIN_ARRAYS:
            binned[name][:, t] = by_bin[name]

    records = [finished_record(*parts) for parts in zip(cells, snow_of["summaries"], horizon_summaries, per_cell)]
    meta = {
        "targets": targets, "stretch_min_h": grazing.STRETCH_MIN_H, "long_rule": grazing.LONG_RULE,
        "long_rule_meaning": "long_* fields count the time inside unbroken spells of at least stretch_min_h hours with "
                             "the Sun's apparent centre in (0, limit], flat horizon; a spell through midnight is one "
                             "spell and each minute is counted in the ten-day bin it falls in",
        "step_minutes": grazing.STEP_MINUTES, "bin_days": sun.BIN_DAYS, "n_bins": sun.N_BINS,
        "year_phases": grazing.YEAR_PHASES, "year_phases_meaning": grazing.YEAR_PHASES_MEANING,
        "winter_bins_north": grazing.WINTER_BINS_NORTH, "summer_bins_north": grazing.SUMMER_BINS_NORTH,
        "summer_bins_south": grazing.SUMMER_BINS_SOUTH, "counts": counts(records),
        "snow_archive": SNOW.name,
        "snow_archive_written": datetime.fromtimestamp(SNOW.stat().st_mtime).isoformat(timespec="seconds"),
        "snow_archive_has_as_mapped": "probabilities_as_mapped" in archive.files,
        "snow_odds_rule": "measured cells use the odds as mapped; doubtful cells use the odds with the stale-flag "
                          "rule; see snow.odds_used of each cell",
        "horizons": len(shares), "horizon_bins": grazing.horizon_bins_note(targets),
        "min_bare": MIN_BARE, "min_land_share_south": MIN_LAND_SOUTH,
    }
    write_json(OUT, {"meta": meta, "cells": records})
    write_bins(OUT_BINS, ids=np.array([c["id"] for c in cells]), targets=np.array([t["id"] for t in targets]), **binned)

    print(f"cells written: {len(records)}; counts: {json.dumps(meta['counts'])}")
    print(f"snow archive {SNOW} written {meta['snow_archive_written']}, "
          f"as-mapped odds: {meta['snow_archive_has_as_mapped']}; cells with a horizon: {len(shares)}")
    measured = [r for r in records if r["gridded"] and r["snow"]["status"] == "measured"]
    for target in targets:
        hours = [r["targets"][target["id"]]["long_snow_free_hours"] for r in measured]
        unknown = sum(h is None for h in hours)
        print(f"  {target['name']:42s} limit {target['limit_deg']:.2f} deg | measured northern cells with long-window"
              f" snow-free hours >= 50: {sum(h is not None and h >= 50 for h in hours):5d}"
              f" | >= 100: {sum(h is not None and h >= 100 for h in hours):5d}"
              f" | >= 200: {sum(h is not None and h >= 200 for h in hours):5d} | unknown: {unknown}")
    print(f"wrote {OUT} and {OUT_BINS}")


if __name__ == "__main__":
    main()

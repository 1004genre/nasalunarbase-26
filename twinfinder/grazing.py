# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Grazing hours: the Sun table, the snow-free odds and the terrain horizon joined per cell and lunar target.

A grazing hour is an hour with the Sun's apparent centre above the horizon and
at or below the lunar site's limit. Three versions are kept side by side and
never merged: flat (no snow, no terrain), snow-free (times the odds that the
ground is snow-free in that ten-day bin) and open (snow-free, and only where
the terrain does not hide the Sun).

Each version is kept twice: all hours, and long-window hours, which are the
hours inside unbroken spells of at least STRETCH_MIN_H with the Sun in the band
(sun.long_band_minutes_table: spells are followed day by day, through midnight;
no ten-day bin is taken or left out as a whole). The Sun tables are the mean
over sun.YEAR_PHASES (eight) calendars an eighth of a day apart, spread over the
four years of the leap cycle, so the hours do not hang on where one calendar
happens to sit.

Every function works on arrays whose last axes are the ten-day bins (and, for
the Sun table, sectors and elevation bins), so one cell or many cells can be
passed. An hours figure that cannot be known is NaN here and null in the files,
never 0.
"""
from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path

import numpy as np

from twinfinder import horizon, snow, sun

TARGETS = Path("data/derived/moon_targets.json")
SNOW_ARCHIVE = Path("data/derived/snow_free_dekads.npz")
HORIZONS = Path("data/derived/horizon_cells.json")
STRETCH_MIN_H = 2.0   # a low-Sun spell is a "long window" when it lasts at least this long without a break
LONG_RULE = "per-day spells"   # version 2 took whole ten-day bins by their median longest stretch (long_bins)
STEP_MINUTES = 1      # time step of the Sun tables behind the cells file: all hours and long spells use the same one
YEAR_PHASES = sun.YEAR_PHASES   # calendars the Sun tables are averaged over (an eighth of a day apart)
YEAR_PHASES_MEANING = ("every Sun table (all hours, long spells, median stretch) is the mean over year_phases calendars, "
                       "each an eighth of a day on from the one before, centred on the middle of the leap cycle: where "
                       "noon falls against the seasons differs from "
                       "year to year inside the leap cycle and with longitude, and a single calendar moved a cell's "
                       "long-spell hours by up to 9 h a year")
LIMIT_SLACK_DEG = sun.LIMIT_SLACK_DEG
ODDS_AS_MAPPED, ODDS_WITH_RULE = "as mapped", "stale-flag rule"
HORIZON_BATCH = 256   # cells joined with their horizon at a time (keeps the working array small)
WINTER_BINS_NORTH = list(range(27, 36)) + list(range(0, 9))   # 28 September to 31 March
SUMMER_BINS_NORTH = list(range(9, 27))                        # 1 April to 27 September
SUMMER_BINS_SOUTH = [33, 34, 35, 0, 1, 2, 3, 4, 5]            # 27 November to 1 March: when the rock layers were mapped
POLAR_NIGHT_LAT = 67.4    # from here north the snow maps cannot be checked by eye in midwinter
STUCK_ANYWHERE = 3        # this many stuck winters make a cell's odds doubtful at any latitude

# (name, lat, lon): places reported in their own table, outside the gridded counts.
NAMED_SITES_NORTH = [
    ("Qaqortorsuaq anorthosite, Greenland", 66.5833, -52.2),
    ("Fiskenaesset anorthosite, Greenland", 63.25, -50.0),
    ("Lofoten anorthosite (Nusfjord), Norway", 68.04, 13.35),
    ("Bergen Arcs anorthosite, Norway", 60.58, 5.25),
    ("Bear Island, Norway", 74.45, 19.25),
    ("Jan Mayen, Norway", 70.95, -8.55),
    ("Reykjanes, Iceland", 63.88, -22.45),
    ("Skeidararsandur, Iceland", 63.95, -17.5),
    ("Myrdalssandur sand plain, Iceland", 63.45, -18.6),
    ("Haughton crater, Devon Island, Canada", 75.38, -89.67),
    ("Longyearbyen, Svalbard", 78.2, 15.6),
    ("Kangerlussuaq, Greenland", 67.01, -50.7),
]


def check_shared_bins() -> None:
    """Stop if the Sun table and the horizon module ever disagree on sectors or elevation bins."""
    if horizon.AZ_SECTORS != sun.AZ_SECTORS or list(horizon.ELEV_EDGES_DEG) != list(sun.ELEV_EDGES_DEG):
        raise ValueError("sun.py and horizon.py no longer use the same azimuth sectors and elevation bins")


def target_limit(sun_max_elev_deg: float) -> float:
    """A target's Sun limit as used everywhere: two decimals, so it lands on an elevation bin edge."""
    return round(sun_max_elev_deg, 2)


def elev_bins(limit_deg: float) -> list[int]:
    """The elevation bins of the Sun table that lie wholly at or below a target's limit."""
    return [e for e, upper in enumerate(sun.ELEV_EDGES_DEG[1:]) if upper <= limit_deg + LIMIT_SLACK_DEG]


def load_targets(path: Path = TARGETS) -> list[dict]:
    """The lunar targets with their Sun limit, the elevation bins each one uses and if it has a terrain model.

    Stops if a limit is not an elevation bin edge (within LIMIT_SLACK_DEG): the band would end at the edge
    below it without a word. has_model is false for a region without a NASA 5 m terrain model: its light
    hours are counted in full, its slope figures are unknown.
    """
    out = []
    for target in json.loads(Path(path).read_text()):
        limit = target_limit(target["sun_max_elev_deg"])
        if not any(abs(limit - edge) <= LIMIT_SLACK_DEG for edge in sun.ELEV_EDGES_DEG[1:]):
            raise ValueError(f"the Sun limit {limit:.2f} of {target['id']} is not an elevation bin edge; add it to "
                             f"sun.ELEV_EDGES_DEG")
        out.append({"id": target["id"], "name": target["name"], "limit_deg": limit, "elev_bins": elev_bins(limit),
                     "has_model": bool(target.get("has_model", target.get("terrain") is not None))})
    return out


def hemisphere(lat: float) -> str:
    return "N" if lat >= 0 else "S"


def flat_hours(minutes, bins) -> np.ndarray:
    """Hours per ten-day bin over a flat horizon: the Sun table summed over sectors and the target's elevation bins.

    minutes is [..., ten-day bin, sector, elevation bin] in minutes per year.
    """
    return np.asarray(minutes, dtype=float)[..., bins].sum(axis=(-2, -1)) / 60.0


def snow_free_hours(hours, odds) -> np.ndarray:
    """Hours per ten-day bin times the odds that the ground is snow-free in that bin.

    Unknown odds give unknown hours, with one exception: a bin without any
    hours has none on snow-free ground either (in the polar night the snow
    maps see nothing, but there is no Sun to lose). A cell with no odds at all
    stays unknown in every bin.
    """
    hours, odds = np.asarray(hours, dtype=float), np.asarray(odds, dtype=float)
    some_odds = np.isfinite(odds).any(axis=-1, keepdims=True)
    return np.where((hours == 0.0) & some_odds, 0.0, hours * odds)


def open_hours(minutes, bins, open_share, snow_free=None) -> np.ndarray:
    """Hours per ten-day bin with the Sun in the target's band and clear of the terrain.

    open_share is [..., sector, elevation bin] as horizon.cell_open_share gives
    it: the share of the cell's land that sees the Sun there. Sector k is the
    same 10 degrees of azimuth in both tables (0 = north), so a wall to the
    north takes away the Sun when it stands in the north. With snow_free (odds
    per ten-day bin) the result is also weighted by the snow; without it the
    terrain alone is counted, which is what the south uses.
    """
    lit = np.asarray(minutes, dtype=float)[..., bins]                              # [..., bin, sector, elevation]
    share = np.asarray(open_share, dtype=float)[..., bins][..., None, :, :]        # [..., 1, sector, elevation]
    seen = np.where(lit > 0.0, lit * share, 0.0)
    hours = seen.sum(axis=(-2, -1)) / 60.0
    return hours if snow_free is None else snow_free_hours(hours, snow_free)


def long_bins(stretch, min_h: float = STRETCH_MIN_H) -> np.ndarray:
    """The version 2 rule: ten-day bins whose median longest continuous low-Sun stretch is at least min_h hours.

    Nothing in the cells file is gated by it any more; the latitude profile keeps its thresholds for comparison.
    """
    return np.asarray(stretch) >= min_h


def bin_mask(bins) -> np.ndarray:
    """A list of ten-day bins as a true/false array over the year."""
    mask = np.zeros(sun.N_BINS, dtype=bool)
    mask[list(bins)] = True
    return mask


def total(hours, bins=None):
    """Sum over ten-day bins: all of them, a list of bins, or a true/false array per bin.

    Unknown if any counted bin is unknown, and also if no bin of the row is
    known at all (so a cell without snow odds never reads as a known zero).
    """
    hours = np.asarray(hours, dtype=float)
    if bins is None:
        out = hours.sum(axis=-1)
    else:
        keep = np.asarray(bins)
        if keep.dtype == bool:
            out = np.where(keep, hours, 0.0).sum(axis=-1)
        else:
            out = hours[..., keep.astype(int)].sum(axis=-1)
    out = np.where(np.isfinite(hours).any(axis=-1), out, np.nan)
    return out if out.ndim else float(out)


def poleward_sectors(hemisphere: str) -> list[int]:
    """Sectors with the Sun within 90 degrees of north (northern cells) or of south: the midnight-Sun side."""
    quarter = sun.AZ_SECTORS // 4
    if hemisphere == "N":
        return list(range(0, quarter)) + list(range(3 * quarter, sun.AZ_SECTORS))
    return list(range(quarter, 3 * quarter))


def poleward_share(minutes, bins, long=None, hemisphere: str = "N"):
    """Share of the low-Sun minutes that come with the Sun on the poleward side; NaN without such minutes.

    Pass the long-spell table (sun.long_band_minutes_table, one limit) to get the share of the
    long-window flat hours. long, if given, is a true/false array per ten-day bin: only those bins count.
    """
    by_sector = np.asarray(minutes, dtype=float)[..., bins].sum(axis=-1)           # [..., bin, sector]
    if long is not None:
        by_sector = np.where(np.asarray(long, dtype=bool)[..., None], by_sector, 0.0)
    whole = by_sector.sum(axis=(-2, -1))
    poleward = by_sector[..., poleward_sectors(hemisphere)].sum(axis=(-2, -1))
    share = np.where(whole > 0.0, poleward / np.where(whole > 0.0, whole, 1.0), np.nan)
    return share if share.ndim else float(share)


def best_stretch(stretch) -> tuple[float, int | None]:
    """The longest ten-day median stretch of the year and its bin (no bin when the Sun is never in the band)."""
    stretch = np.asarray(stretch, dtype=float)
    best = int(stretch.argmax())
    return float(stretch[best]), (best if stretch[best] > 0.0 else None)


def top_bins(hours, long=None, count: int = 3) -> list[list]:
    """The bins with the most hours, best first, as [bin, hours]; unknown and empty bins are left out.

    Pass long-window hours per bin. long, if given, is a true/false array per bin: only those bins count.
    A bin whose hours round to 0.0 counts as empty, so no table prints "0 h" as a best time to go.
    """
    hours = np.asarray(hours, dtype=float)
    counted = np.isfinite(hours) if long is None else np.asarray(long, dtype=bool) & np.isfinite(hours)
    hours = np.where(counted, hours, 0.0)
    order = np.argsort(-hours, kind="stable")[:count]
    found = [[int(b), round(float(hours[b]), 1)] for b in order]
    return [pair for pair in found if pair[1] > 0.0]


def top_bins_basis(hemisphere: str, flat, snow_free, open_) -> np.ndarray:
    """The hours the top bins are ranked by: open where known, else snow-free, else flat (always flat in the south)."""
    basis = np.array(flat, dtype=float)
    if hemisphere == "N":
        for better in (snow_free, open_):
            better = np.asarray(better, dtype=float)
            basis = np.where(np.isfinite(better).any(axis=-1, keepdims=True), better, basis)
    return basis


def snow_status(hemisphere: str, source: str | None, stuck_winters: int, lat: float) -> str:
    """How far a cell's snow odds can be trusted: "measured", "doubtful", "no data" or "unmeasured".

    Unmeasured: every southern cell (no open product measures winter snow on
    Antarctic rock). No data: no land pixel within the 5 x 5 block. Doubtful:
    a stuck winter in the polar night, or three stuck winters anywhere.
    """
    if hemisphere == "S":
        return "unmeasured"
    if source is None:
        return "no data"
    if (stuck_winters >= 1 and lat >= POLAR_NIGHT_LAT) or stuck_winters >= STUCK_ANYWHERE:
        return "doubtful"
    return "measured"


def odds_used(status: str, has_as_mapped: bool = True) -> str | None:
    """Which snow odds a cell's main numbers use, by its snow status (decision 13).

    Measured: the maps as they read ("as mapped"). At all nine trusted stations with a stuck pixel
    nearby the stale-flag rule moved the satellite away from the station, so it is not applied
    where the maps can be trusted. Doubtful: the stale-flag rule, the lower and cautious figure.
    No data and unmeasured: None. An archive without as-mapped odds leaves only the rule.
    """
    if status == "measured":
        return ODDS_AS_MAPPED if has_as_mapped else ODDS_WITH_RULE
    return ODDS_WITH_RULE if status == "doubtful" else None


def choose_odds(used: list, with_rule, as_mapped) -> np.ndarray:
    """Each cell's row of odds [cells, bins] by the name odds_used gave it; all unknown where that is None."""
    with_rule, as_mapped = np.asarray(with_rule, dtype=float), np.asarray(as_mapped, dtype=float)
    out = np.full(with_rule.shape, np.nan)
    for i, name in enumerate(used):
        if name is not None:
            out[i] = as_mapped[i] if name == ODDS_AS_MAPPED else with_rule[i]
    return out


def days_per_bin(days) -> np.ndarray:
    """How many of the given days of year fall in each ten-day bin."""
    return np.bincount(np.array([sun.bin_index(d) for d in days], dtype=int), minlength=sun.N_BINS)


def usable_days(per_bin, odds):
    """All-day low-Sun days, each weighted by the snow-free odds of its bin (the old measure). NaN if unknown."""
    return total(snow_free_hours(per_bin, odds))


def target_sums(hemisphere: str, flat, long_flat, terrain, long_terrain, stretch, odds, as_mapped, with_rule) -> dict:
    """Every hours figure of the cells file for cells of one hemisphere and one target, as arrays [cells].

    All inputs are [cells, ten-day bins]. flat and terrain are all hours: over a flat horizon, and
    with the terrain's open share (NaN rows without a horizon). long_flat and long_terrain are the
    same, counting only the hours inside spells of at least the minimum length. stretch is the
    median longest stretch per bin, kept for information; it gates nothing. odds are the snow-free
    odds the cell's main numbers use (NaN where unknown); as_mapped and with_rule are the two
    versions of the odds, each kept beside the main figure.

    In the north snow-free hours are flat times odds and open hours are terrain times odds. In the
    south the snow is not measured: those figures stay unknown, and the summer rock hours
    (27 November to 1 March) are given instead, flat and terrain-only.
    """
    flat, long_flat = np.asarray(flat, dtype=float), np.asarray(long_flat, dtype=float)
    terrain, long_terrain = np.asarray(terrain, dtype=float), np.asarray(long_terrain, dtype=float)
    stretch = np.asarray(stretch, dtype=float)
    north = hemisphere == "N"
    unknown = np.full(flat.shape, np.nan)

    def with_snow(hours, which):
        return snow_free_hours(hours, which) if north else unknown

    snow_free, open_ = with_snow(flat, odds), with_snow(terrain, odds)
    long_snow_free, long_open = with_snow(long_flat, odds), with_snow(long_terrain, odds)
    longest = stretch.max(axis=-1)
    return {
        "flat_hours": total(flat), "snow_free_hours": total(snow_free), "open_hours": total(open_),
        "long_flat_hours": total(long_flat),
        "long_snow_free_hours": total(long_snow_free), "long_open_hours": total(long_open),
        "long_snow_free_hours_winter": total(long_snow_free, WINTER_BINS_NORTH),
        "long_snow_free_hours_summer": total(long_snow_free, SUMMER_BINS_NORTH),
        "long_open_hours_winter": total(long_open, WINTER_BINS_NORTH),
        "long_open_hours_summer": total(long_open, SUMMER_BINS_NORTH),
        "long_snow_free_hours_as_mapped": total(with_snow(long_flat, as_mapped)),
        "long_snow_free_hours_with_rule": total(with_snow(long_flat, with_rule)),
        "summer_rock_hours": total(unknown if north else flat, SUMMER_BINS_SOUTH),
        "long_summer_rock_hours": total(unknown if north else long_flat, SUMMER_BINS_SOUTH),
        "long_summer_rock_open_hours": total(unknown if north else long_terrain, SUMMER_BINS_SOUTH),
        "longest_stretch_h": longest,
        "best_stretch_bin": np.where(longest > 0.0, stretch.argmax(axis=-1), np.nan),
    }


DIGITS = {"longest_stretch_h": 2}   # stretches are kept finer than hours, so 1.97 h does not read as a 2.0 h window


def known(value, digits: int = 1):
    """A number for the JSON files: rounded, or None when it cannot be known."""
    value = float(value)
    return round(value, digits) if np.isfinite(value) else None


def rows(sums: dict) -> list[dict]:
    """The arrays of target_sums as one dict per cell, rounded, with None for unknown."""
    columns = []
    for name, values in sums.items():
        column = [known(v, DIGITS.get(name, 1)) for v in np.atleast_1d(values).tolist()]
        if name.endswith("_bin"):
            column = [None if v is None else int(v) for v in column]
        columns.append(column)
    return [dict(zip(sums, values)) for values in zip(*columns)]


# Joining cells with their snow odds and horizons. The build script and long_window_hours_by_bin share this code.

@contextmanager
def projected_once(points):
    """Let the snow module place many points with one map-projection call.

    snow's cell functions project one point per call (about half a millisecond)
    and are asked three or four things per cell. Inside this block they read
    each point's place from a table made with a single call; any other point
    is still projected the plain way.
    """
    rows, cols = snow.ims_rowcol([lat for lat, _ in points], [lon for _, lon in points])
    table = {point: (rows[i:i + 1], cols[i:i + 1]) for i, point in enumerate(points)}
    plain = snow.ims_rowcol

    def placed(lats, lons):
        found = table.get((lats[0], lons[0])) if len(lats) == 1 else None
        return found if found is not None else plain(lats, lons)

    snow.ims_rowcol = placed
    try:
        yield
    finally:
        snow.ims_rowcol = plain


def snow_of_cells(cells: list[dict], archive) -> dict:
    """The snow of each cell: its summary for the record and three sets of odds, each [cells, 36].

    Returns {"summaries", "odds" (what the cell's main numbers use), "as_mapped", "with_rule"}.
    The status is judged as before, on the odds with the stale-flag rule and the stuck winters of
    their block. A measured cell then uses the odds as mapped, a doubtful one the odds with the
    rule (odds_used). land_pixels and block_pixels describe the block the used odds came from.
    Southern cells are not looked up: the snow maps cover the Northern Hemisphere only. The
    as-mapped odds are all unknown when the archive does not hold them.
    """
    n = len(cells)
    with_rule, as_mapped = np.full((n, sun.N_BINS), np.nan), np.full((n, sun.N_BINS), np.nan)
    summaries = [{"status": "unmeasured", "source": None, "land_pixels": None, "block_pixels": None,
                  "stuck_winters": None, "odds_used": None} for _ in cells]
    main, row0, col0 = archive["probabilities"], int(archive["row0"]), int(archive["col0"])
    stuck = archive["stuck_winters"]
    plain = archive["probabilities_as_mapped"] if "probabilities_as_mapped" in archive.files else None
    north = [i for i, c in enumerate(cells) if hemisphere(c["lat"]) == "N"]
    with projected_once([(cells[i]["lat"], cells[i]["lon"]) for i in north]):
        for i in north:
            lat, lon = cells[i]["lat"], cells[i]["lon"]
            with_rule[i], source = snow.cell_probabilities_filled(main, row0, col0, lat, lon)
            winters = snow.cell_stuck_winters(stuck, row0, col0, lat, lon, reach=snow.block_reach(source) or 1)
            status = snow_status("N", source, winters, lat)
            used, layer, block = odds_used(status, plain is not None), main, source
            if plain is not None:
                as_mapped[i], mapped_source = snow.cell_probabilities_filled(plain, row0, col0, lat, lon)
                if used == ODDS_AS_MAPPED:
                    layer, block = plain, mapped_source
            summaries[i] = {"status": status, "source": source,
                            "land_pixels": snow.cell_land_pixels(layer, row0, col0, lat, lon,
                                                                 reach=snow.block_reach(block) or 1),
                            "block_pixels": snow.block_pixels(block), "stuck_winters": winters, "odds_used": used}
    odds = choose_odds([s["odds_used"] for s in summaries], with_rule, as_mapped)
    return {"summaries": summaries, "odds": odds, "as_mapped": as_mapped, "with_rule": with_rule}


def stored_on_old_bins(path: Path = HORIZONS) -> int:
    """How many records of the horizon file hold their open shares on the old nine bins (horizon.STORED_EDGES_DEG)."""
    path = Path(path)
    if not path.exists():
        return 0
    old = len(horizon.STORED_EDGES_DEG) - 1
    return sum(1 for entry in json.loads(path.read_text()).values()
               if "open_share" in entry and len(entry["open_share"][0]) == old != len(sun.ELEV_EDGES_DEG) - 1)


def hills_exact(limit_deg: float, old_records: int) -> bool:
    """True if the hours after hills of a region with this Sun limit use the full method of the first build: each bin
    of its band starts at an edge where the stored horizons give the open share. If any record is on the old bins and
    a bin of the band starts at a new edge, the hours after hills are a lower bound (see horizon.share_on_edges).
    The name of the key stays "hills_exact" for the page, but the method itself is an approximation: it counts the
    Sun as seen from a point only if the whole bin of Sun height is above the horizon of the point (36 directions)."""
    if old_records == 0:
        return True
    exact = horizon.exact_new_bins()
    return all(exact[e] for e in elev_bins(limit_deg))


HORIZON_BINS_NOTE = (
    "The horizons of horizon_cells.json give the open share at the old nine bins only. Each new bin takes the share "
    "of the old bin that holds its lower edge. For the four regions of the first build, this gives the same hours "
    "after hills as that build. Some regions have a band in which each bin starts at an old edge. For these regions, "
    "the hours after hills use the full method of the first build. For the other regions, the hours after hills are "
    "a lower bound: with the open share at each new edge, more hours can count. The full method is also an "
    "approximation. It counts the Sun as seen from a point only if the whole bin of Sun height is above the horizon "
    "of the point. It uses 36 directions of 10 degrees.")


def horizon_bins_note(targets: list[dict] | None = None, path: Path = HORIZONS) -> dict:
    """What the files say about the stored horizons and the new elevation bins (see horizon.share_on_edges).

    With targets: for each region, if its hours after hills use the full method of the first build (hills_exact
    true) or are a lower bound (false).
    """
    exact = horizon.exact_new_bins()
    edges = sun.ELEV_EDGES_DEG
    old_records = stored_on_old_bins(path)
    note = {
        "stored_edges_deg": list(horizon.STORED_EDGES_DEG), "edges_deg": list(edges),
        "records_on_the_old_bins": old_records,
        "bins_with_a_lower_bound": ([[edges[e], edges[e + 1]] for e, ok in enumerate(exact) if not ok]
                                    if old_records else []),
        "note": HORIZON_BINS_NOTE,
    }
    if targets is not None:
        note["hills_exact"] = {t["id"]: hills_exact(float(t["limit_deg"]), old_records) for t in targets}
    return note


def edges_by_bins(n_bins: int) -> list[float]:
    """The elevation edges of a stored horizon record without an elev_edges field, from its number of bins."""
    known = {len(e) - 1: list(e) for e in (sun.OLD_ELEV_EDGES_DEG, sun.TEN_REGION_ELEV_EDGES_DEG, sun.ELEV_EDGES_DEG)}
    if n_bins not in known:
        raise ValueError(f"a stored horizon record has {n_bins} elevation bins; no known edge list has that many")
    return known[n_bins]


def horizons_of_cells(cells: list[dict], path: Path = HORIZONS) -> tuple[list, dict[int, np.ndarray]]:
    """Each cell's horizon summary for the record (None when it has none) and the open shares by cell number.

    The shares come on the bins of sun.ELEV_EDGES_DEG. A record stored on the old nine bins is moved to them
    with horizon.share_on_edges (exact for each bin whose lower edge is an old edge, else a lower bound).
    """
    path = Path(path)
    stored = json.loads(path.read_text()) if path.exists() else {}
    summaries, shares = [], {}
    for i, cell in enumerate(cells):
        entry = stored.get(cell["id"])
        if entry is None:
            summaries.append(None)
        elif "skipped" in entry:
            summaries.append({"skipped": entry["skipped"]})
        else:
            share = np.array(entry["open_share"], dtype=float)
            # a record gives its edges, or the edges follow from its number of bins (9: the four-region build,
            # 15: the ten-region build); shares on other edges move to the bins of now (horizon.share_on_edges)
            edges = entry.get("elev_edges") or edges_by_bins(share.shape[-1])
            if [round(e, 6) for e in edges] != [round(e, 6) for e in sun.ELEV_EDGES_DEG]:
                share = horizon.share_on_edges(share, edges, sun.ELEV_EDGES_DEG)
            shares[i] = share
            summaries.append({k: entry.get(k) for k in ("north_deg", "south_deg", "valid_share", "pixel_m")})
    return summaries, shares


def terrain_hours(minutes: np.ndarray, lat_of_cell: np.ndarray, shares: dict[int, np.ndarray], bins) -> np.ndarray:
    """Terrain-only open hours [cells, 36] for one target; NaN rows for cells without a horizon.

    minutes is a Sun table [latitudes, 36, sectors, elevation bins] (all hours, or one limit's long spells).
    """
    out = np.full((len(lat_of_cell), sun.N_BINS), np.nan)
    numbers = sorted(shares)
    for start in range(0, len(numbers), HORIZON_BATCH):
        batch = numbers[start:start + HORIZON_BATCH]
        out[batch] = open_hours(minutes[lat_of_cell[batch]], bins, np.stack([shares[i] for i in batch]))
    return out


def hours_by_bin(minutes, bins, lat_of_cell, north, odds, shares) -> dict:
    """One target's hours per ten-day bin for all cells, from one Sun table: flat, terrain-only, snow-free and open.

    minutes is [latitudes, 36, sectors, elevation bins]: the all-hours table, or the long-spell
    table of this target's limit. north is true/false per cell. Snow-free hours are unknown in the
    south; open hours are terrain times odds in the north and terrain only in the south, and
    unknown without a horizon.
    """
    north = np.asarray(north, dtype=bool)[:, None]
    flat = flat_hours(minutes, bins)[lat_of_cell]
    terrain = terrain_hours(minutes, lat_of_cell, shares, bins)
    return {"flat": flat, "terrain": terrain,
            "snow_free": np.where(north, snow_free_hours(flat, odds), np.nan),
            "open": np.where(north, snow_free_hours(terrain, odds), terrain)}


def cell_inputs(cells: list[dict], snow_archive: Path = SNOW_ARCHIVE, horizons: Path = HORIZONS) -> dict:
    """What the join needs to know of each cell: its snow (snow_of_cells) and its horizon (horizons_of_cells).

    cells are records with "id", "lat" and "lon". Returns {"snow": ..., "horizon_summaries", "shares"}.
    """
    summaries, shares = horizons_of_cells(cells, horizons)
    return {"snow": snow_of_cells(cells, np.load(snow_archive)), "horizon_summaries": summaries, "shares": shares}


def long_window_hours_by_bin(cells: list[dict], min_stretch_h: float = STRETCH_MIN_H, targets: list[dict] | None = None,
                             inputs: dict | None = None, snow_archive: Path = SNOW_ARCHIVE, horizons: Path = HORIZONS,
                             step_minutes: float = STEP_MINUTES, year_phases: int = YEAR_PHASES) -> dict:
    """Long-window hours per ten-day bin for a list of cells, with another minimum spell length if wanted.

    cells are records with "id", "lat" and "lon" (those of grazing_cells.json will do). Returns
    {"ids", "targets", "min_stretch_h", "long_flat", "long_snow_free", "long_open"}; the three
    arrays are float32 [cells, targets, 36], built by the same code as the arrays of those names
    in grazing_bins.npz and with the same rules: snow-free hours use the odds that go with the
    cell's snow status and are NaN where the snow is unknown (every southern cell); open hours are
    NaN without a horizon, and terrain-only in the south. At min_stretch_h = STRETCH_MIN_H the
    result equals grazing_bins.npz (given the same snow archive and horizon file). The Sun table
    is the mean over year_phases calendars, as in the build; year_phases=1 gives a single calendar.

    The cells' snow and horizons are read from the two files, or taken from inputs (cell_inputs
    of the same cells) so that several minimums can share one reading.
    """
    targets = load_targets() if targets is None else targets
    inputs = cell_inputs(cells, snow_archive, horizons) if inputs is None else inputs
    lats = sorted({c["lat"] for c in cells})
    place = {lat: k for k, lat in enumerate(lats)}
    lat_of_cell = np.array([place[c["lat"]] for c in cells], dtype=int)
    north = np.array([hemisphere(c["lat"]) == "N" for c in cells], dtype=bool)
    long_minutes = sun.long_band_minutes_table(lats, [t["limit_deg"] for t in targets], min_stretch_h, step_minutes,
                                               year_phases=year_phases)
    out = {name: np.empty((len(cells), len(targets), sun.N_BINS), dtype=np.float32)
           for name in ("long_flat", "long_snow_free", "long_open")}
    for t, target in enumerate(targets):
        hours = hours_by_bin(long_minutes[t], target["elev_bins"], lat_of_cell, north, inputs["snow"]["odds"], inputs["shares"])
        out["long_flat"][:, t], out["long_snow_free"][:, t] = hours["flat"], hours["snow_free"]
        out["long_open"][:, t] = hours["open"]
    return {"ids": [c["id"] for c in cells], "targets": [t["id"] for t in targets],
            "min_stretch_h": float(min_stretch_h), **out}

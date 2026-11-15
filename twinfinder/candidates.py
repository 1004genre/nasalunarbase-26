# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Which cells get a terrain horizon and slope statistics, and why.

Since version 3 every cell is a candidate (census). The reasons of the earlier,
narrower choice are kept on each record: the best cells by light on bare
ground, the cells on an anorthosite body, the doubtful cells that would have
ranked, the named sites, and a sample drawn without looking at any score. A
cell that is in for none of these carries the single reason "all". The sample
stays what it was: it is how we can say what terrain does to a typical cell
without having looked at the answer first.

Cells are the records of data/derived/grazing_cells.json.
"""
from __future__ import annotations

import hashlib

from twinfinder import reference

ROCK_MARGIN_KM = 8.0   # half the diagonal of a cell, as in scripts/score_cells.py
# (label, field of the cell's target record, how many cells): hours are multiplied by the bare share
TOP_NORTH = [("year", "long_snow_free_hours", 300),
             ("winter", "long_snow_free_hours_winter", 150),
             ("summer", "long_snow_free_hours_summer", 150)]
TOP_SOUTH = [("summer rock", "long_summer_rock_hours", 150),
             ("flat", "long_flat_hours", 100)]
SAMPLE_NORTH, SAMPLE_SOUTH = 300, 150
TOP_PREFIXES = ("top ", "south top ")
ALL = "all"            # the only reason of a cell that is a candidate because every cell is one
RANK_MIN_BARE = 0.25   # as in twinfinder/score.py: cells with less bare ground are listed but not ranked


def value(cell: dict, target_id: str, field: str) -> float | None:
    """Hours times the bare share of the cell; None when either is unknown."""
    hours, bare = cell["targets"][target_id].get(field), cell.get("bare")
    return None if hours is None or bare is None else hours * bare


def top_list(cells: list[dict], target_id: str, field: str, count: int) -> list[dict]:
    """The count cells with the most hours times bare, best first.

    Cells with no hours or unknown hours are left out, so a list can be short.
    Equal values are ordered by id, so a second run gives the same list.
    """
    valued = [(value(c, target_id, field), c) for c in cells]
    valued = [(v, c) for v, c in valued if v is not None and v > 0.0]
    valued.sort(key=lambda pair: (-pair[0], pair[1]["id"]))
    return [c for _, c in valued[:count]]


def would_enter(own: float | None, members: list[dict], target_id: str, field: str, count: int) -> bool:
    """True if a value would have put a cell in a top list: it is above zero and reaches the list's last member."""
    if own is None or own <= 0.0 or count <= 0:
        return False
    return len(members) < count or own >= value(members[-1], target_id, field)


def sample(cells: list[dict], count: int) -> list[dict]:
    """The first count cells when ids are sorted by their sha1: fixed, and blind to every score."""
    return sorted(cells, key=lambda c: hashlib.sha1(c["id"].encode()).hexdigest())[:count]


def doubtful_reasons(cell: dict, target_id: str, label: str, field: str, members: list[dict], count: int) -> list[str]:
    """Why a doubtful or no-data cell belongs beside a northern top list, judged on its own numbers.

    A doubtful cell is tried with its hours under the stale-flag rule and, for
    the year list, with its hours as mapped. A cell without snow data has only
    flat-horizon hours (the most it could have), kept for the year list.
    """
    name = f"top {target_id} {label}"
    status = cell["snow"]["status"]

    def enters(own_field: str) -> bool:
        return would_enter(value(cell, target_id, own_field), members, target_id, field, count)

    if status == "doubtful":
        if enters(field):
            return [f"doubtful: would be {name}"]
        if label == "year" and enters("long_snow_free_hours_as_mapped"):
            return [f"doubtful: would be {name} (as mapped)"]
    if status == "no data" and label == "year" and enters("long_flat_hours"):
        return [f"no data: flat hours would be {name}"]
    return []


def droppable(candidate: dict) -> bool:
    """True for a candidate that only the census or top lists hold: never a named site, a sample, a rock or a doubtful cell."""
    return all(reason == ALL or reason.startswith(TOP_PREFIXES) for reason in candidate["why"])


def census_class(candidate: dict) -> int:
    """Where a cell stands in the order of work.

    0: a northern cell with measured snow and bare ground of at least
    RANK_MIN_BARE (it can be ranked); 1: any other northern cell; 2: a southern
    cell. A record without the keys "hemisphere", "bare" and "snow_status"
    counts as 1.
    """
    if candidate.get("hemisphere") == "S":
        return 2
    bare = candidate.get("bare")
    rankable = candidate.get("snow_status") == "measured" and bare is not None and bare >= RANK_MIN_BARE
    return 0 if rankable else 1


def drop_order(found: list[dict]) -> list[dict]:
    """Candidates that may be left out when downloads must shrink, the first to go first.

    Cells that only the census holds go first: the south, then the northern
    cells that cannot be ranked, then the ones that can. After them the cells
    held by top lists alone, from the bottom of the lists upward. A top-list
    record without a top_position (the interface lists five keys, this is a
    sixth) counts as last in its list.
    """
    def place(candidate: dict) -> float:
        position = candidate.get("top_position")
        return 1.0 if position is None else position

    census_only = sorted((c for c in found if c["why"] == [ALL]), key=lambda c: (-census_class(c), c["id"]))
    top_only = sorted((c for c in found if droppable(c) and c["why"] != [ALL]), key=lambda c: (-place(c), c["id"]))
    return census_only + top_only


def build(cells: list[dict], target_ids: list[str], bodies: list[dict], sizes: dict | None = None,
          sample_north: int = SAMPLE_NORTH, sample_south: int = SAMPLE_SOUTH) -> tuple[list[dict], dict]:
    """The candidate records, in the order of the cells given, and the size of each group and of the union.

    sizes replaces the length of a top list by its label ("year", "winter",
    "summer", "summer rock", "flat"). A record is {"id", "lat", "lon",
    "hemisphere", "why", "top_position"}: why lists every reason, and
    top_position is the cell's best place in any top list as a share of that
    list (0 to 1, small is good; None for a cell in no top list).
    """
    sizes = sizes or {}
    why: dict[str, list[str]] = {}
    position: dict[str, float] = {}
    unsure_why: dict[str, list[str]] = {}   # doubtful and no-data cells: reasons gathered list by list
    group_sizes: dict[str, int] = {}

    def add(cell: dict, reason: str) -> None:
        why.setdefault(cell["id"], []).append(reason)

    def add_top(prefix: str, pool: list[dict], lists: list[tuple], unsure: list[dict]) -> None:
        for target_id in target_ids:
            for label, field, count in lists:
                count = sizes.get(label, count)
                members = top_list(pool, target_id, field, count)
                group_sizes[f"{prefix} {target_id} {label}"] = len(members)
                for rank, cell in enumerate(members, start=1):
                    add(cell, f"{prefix} {target_id} {label}")
                    position[cell["id"]] = min(position.get(cell["id"], 1.0), rank / len(members))
                for cell in unsure:
                    unsure_why.setdefault(cell["id"], []).extend(
                        doubtful_reasons(cell, target_id, label, field, members, count))

    north = [c for c in cells if c["hemisphere"] == "N"]
    south = [c for c in cells if c["hemisphere"] == "S" and c["gridded"]]
    measured = [c for c in north if c["gridded"] and c["snow"]["status"] == "measured"]
    unsure = [c for c in north if c["snow"]["status"] in ("doubtful", "no data")]

    add_top("top", measured, TOP_NORTH, unsure)
    rock = [(c, reference.rock_match(c["lat"], c["lon"], bodies, ROCK_MARGIN_KM)[1]) for c in north]
    for cell, body in rock:
        if body is not None:
            add(cell, f"rock: {body}")
    group_sizes["rock"] = sum(body is not None for _, body in rock)
    for cell in unsure:
        for reason in unsure_why.get(cell["id"], []):
            add(cell, reason)
    group_sizes["doubtful or no data"] = sum(bool(reasons) for reasons in unsure_why.values())
    for name, pool, count in (("sample north", measured, sample_north), ("sample south", south, sample_south)):
        chosen = sample(pool, count)
        group_sizes[name] = len(chosen)
        for cell in chosen:
            add(cell, "sample")
    add_top("south top", south, TOP_SOUTH, [])
    named = [c for c in cells if c.get("named_site")]
    for cell in named:
        add(cell, f"named: {cell['site_name']}")
    group_sizes["named"] = len(named)

    found = [{"id": c["id"], "lat": c["lat"], "lon": c["lon"], "hemisphere": c["hemisphere"],
              "why": why[c["id"]], "top_position": position.get(c["id"])}
             for c in cells if c["id"] in why]
    group_sizes["union"] = len(found)
    return found, group_sizes


def census(cells: list[dict], target_ids: list[str], bodies: list[dict], sizes: dict | None = None,
           sample_north: int = SAMPLE_NORTH, sample_south: int = SAMPLE_SOUTH) -> tuple[list[dict], dict]:
    """Every cell as a candidate record, in the order given, and the size of each group.

    A cell that build() chooses keeps exactly the reasons and the top_position
    build() gives it; every other cell has why == ["all"] and no top_position.
    The sample is drawn by build(), so it is the same sample. Each record also
    carries "bare" and "snow_status" (the cell's own values), which the slow
    scripts use to decide what to work out first. The sizes are those of
    build(), plus "all" (cells in for the census alone); "union" is every cell.
    """
    chosen, group_sizes = build(cells, target_ids, bodies, sizes, sample_north, sample_south)
    by_id = {c["id"]: c for c in chosen}
    found = []
    for cell in cells:
        record = dict(by_id.get(cell["id"]) or {"id": cell["id"], "lat": cell["lat"], "lon": cell["lon"],
                                                 "hemisphere": cell["hemisphere"], "why": [ALL],
                                                 "top_position": None})
        record["bare"] = cell.get("bare")
        record["snow_status"] = (cell.get("snow") or {}).get("status")
        found.append(record)
    group_sizes = dict(group_sizes)
    group_sizes[ALL] = sum(c["why"] == [ALL] for c in found)
    group_sizes["union"] = len(found)
    return found, group_sizes

# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""An independent recount of the tables of RESULTS.md: sections (b), (c), (d), (e: first five rows), (g), (h), (j), (k),
the table "What was searched" and some figures of (i). Written by the count check of version 3.

It imports nothing of the project and does not use scripts/make_results.py: every figure is counted again here
from grazing_cells.json and cells_scored.json (ten-day-bin figures from grazing_bins.npz), version 2 figures from
the kept _v2 files, the old measure from light_cells_v1.json. Run from the project root:
    uv run python tests/recount_results.py [path of RESULTS.md]
or let tests/test_results_recount.py run it on the text scripts/make_results.py builds (it passes TEXT in).
After the run: `checked` figures and texts compared, `differ` lists every one that is not what is printed,
`notes` lists things a reader should know that are not differences.
"""
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np

D = Path("data/derived")
if "TEXT" not in globals():   # the test passes the text in; from the command line the file is read
    TEXT = Path(sys.argv[1] if len(sys.argv) > 1 and __name__ == "__main__" else D / "RESULTS.md").read_text()
NUM = re.compile(r"(?<![\w.])-?\d[\d,]*(?:\.\d+)?")
checked, differ, notes = 0, [], []


def nums(text):
    return [float(m.replace(",", "")) for m in NUM.findall(str(text))]


def check(name, expected, actual, tol=0.0):
    """expected: list of numbers (None = skip); actual: text or list of numbers."""
    global checked
    got = actual if isinstance(actual, list) else nums(actual)
    if len(got) != len(expected):
        differ.append(f"{name}: {len(expected)} figures expected, {len(got)} printed | mine {expected} | printed {got}")
        return
    for k, (e, a) in enumerate(zip(expected, got)):
        if e is None:
            continue
        checked += 1
        if abs(e - a) > tol + 1e-9:
            differ.append(f"{name}: figure {k + 1}: mine {e} | printed {a}")


def check_text(name, expected, actual):
    global checked
    checked += 1
    if expected != actual:
        differ.append(f"{name}: mine {expected!r} | printed {actual!r}")


def section(letter):
    start = TEXT.index(f"\n## ({letter}) ")
    end = TEXT.find("\n## ", start + 1)
    return TEXT[start:end if end != -1 else len(TEXT)]


def tables(text):
    """Tables in order: each a list of rows, a row a list of cell texts; the header row first, the rule row dropped."""
    out, cur = [], None
    for line in text.split("\n"):
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if cur is None:
                cur = []
                out.append(cur)
            if not all(set(c) <= {"-"} for c in cells):
                cur.append(cells)
        else:
            cur = None
    return out


def hav(a, b):
    p1, p2 = math.radians(a["lat"]), math.radians(b["lat"])
    dl = math.radians(b["lon"] - a["lon"])
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(h))


def has_h(c):
    return isinstance(c.get("horizon"), dict) and "north_deg" in c["horizon"]


def pc(values, q):
    return float(np.percentile(np.array(values, dtype=float), q))


def r_(x, d):
    return None if x is None else round(x, d)


g = json.loads((D / "grazing_cells.json").read_text())
cells, meta = g["cells"], g["meta"]
scored = json.loads((D / "cells_scored.json").read_text())
recs = scored["cells"]
rec = {r["id"]: r for r in recs}
by_id = {c["id"]: c for c in cells}
tids = [t["id"] for t in meta["targets"]]
SHORT = {"connecting-ridge": "Connecting ridge", "malapert": "Malapert", "mons-mouton": "Mons Mouton", "nobile-rim-2": "Nobile Rim 2"}
WINTER, SUMMER = meta["winter_bins_north"], meta["summer_bins_north"]
north = [c for c in cells if c["gridded"] and c["hemisphere"] == "N"]
south = [c for c in cells if c["gridded"] and c["hemisphere"] == "S"]
measured = [c for c in north if c["snow"]["status"] == "measured"]
m_h = [c for c in measured if has_h(c)]
s_h = [c for c in south if has_h(c)]
bins = np.load(D / "grazing_bins.npz")
row_of = {cid: i for i, cid in enumerate(bins["ids"].tolist())}
LSF, LOP = bins["long_snow_free"].astype(float), bins["long_open"].astype(float)
km = np.array([c["bare_km2"] for c in measured], dtype=float)
m_rows = np.array([row_of[c["id"]] for c in measured])
LEVELS = (50, 100, 200)


def day_label(doy):
    month_days = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    for m, n in enumerate(month_days):
        if doy <= n:
            return f"{doy} {names[m]}"
        doy -= n


def bin_label(b):
    return f"{day_label(b * 10 + 1)}-{day_label(365 if b == 35 else b * 10 + 10)}"


def counts(group, field, t, source=None):
    out = []
    for level in LEVELS:
        got = [c for c in group if (source[c["id"]] if source else c)["targets"][t].get(field) is not None
               and (source[c["id"]] if source else c)["targets"][t][field] >= level]
        out.append((len(got), sum(c["bare_km2"] for c in got)))
    return out


def calendar(t):
    k = tids.index(t)
    return np.nansum(LSF[m_rows, k, :] * km[:, None], axis=0)


def winter_share(t):
    cal = calendar(t)
    return float(cal[WINTER].sum() / cal.sum()), cal


# ---------------------------------------------------------------- (b) and (c)
for letter, suffix, label in (("b", "_winter", "winter"), ("c", "_summer", "summer")):
    sec = section(letter)
    tb = tables(sec)
    head = tb[0][0]
    check(f"({letter}) table 1 header: measured cells with / without a horizon", [len(m_h), len(measured) - len(m_h), 50, 100, 200], head[4])
    for t, row in zip(tids, tb[0][1:]):
        flat = counts(measured, f"long_snow_free_hours{suffix}", t)
        opened = counts(m_h, f"long_open_hours{suffix}", t)
        check(f"({letter}) table 1, {t}: cells", [flat[0][0], None, flat[1][0], None, flat[2][0], None] + [o[0] for o in opened], " ".join(row[1:]))
        check(f"({letter}) table 1, {t}: km2", [None, flat[0][1], None, flat[1][1], None, flat[2][1], None, None, None], " ".join(row[1:]), tol=1.0)
    if letter == "b":
        intro = re.search(r"over the ([\d,]+) measured northern cells \(([\d,]+) km² of bare ground; (\d+) of the cells", sec)
        check("(b) intro: measured cells, bare km2, cells with unknown hours",
              [len(measured), sum(c["bare_km2"] for c in measured), sum(c["targets"][tids[0]]["long_snow_free_hours"] is None for c in measured)],
              [float(x.replace(",", "")) for x in intro.groups()], tol=1.0)
        line = next(l for l in sec.split("\n") if l.startswith("- Share of all long-window snow-free hours"))
        check("(b) winter-half share of hours x km2, percent", [round(100 * winter_share(t)[0], 1) for t in tids], [float(x) for x in re.findall(r"([\d.]+)%", line)], tol=0.051)
        line = next(l for l in sec.split("\n") if l.startswith("- Regions of the cells with at least 100 winter-half hours"))
        mine = "; ".join(f"{SHORT[t]}: " + (", ".join(f"{k} {v}" for k, v in Counter(
            c["region"] for c in measured if (c["targets"][t]["long_snow_free_hours_winter"] or 0) >= 100).most_common()) or "no cell") for t in tids)
        check_text("(b) regions of cells with 100 winter-half hours", mine, line.split(": ", 1)[1].split(" (`")[0])
        for t, row in zip(tids, tb[1][1:]):
            known = [c for c in measured if c["targets"][t]["long_snow_free_hours_winter"] is not None]
            best = max(known, key=lambda c: (c["targets"][t]["long_snow_free_hours_winter"]))
            v = best["targets"][t]
            check(f"(b) table 2 best winter cell, {t}", [best["lat"], best["lon"], round(best["bare"], 2), v["long_snow_free_hours_winter"], v["long_open_hours_winter"], round(v["poleward_share"], 2)],
                  " ".join([row[1], row[3], row[4], row[5], row[6]]), tol=0.0051)
            check_text(f"(b) table 2 region, {t}", best["region"], row[2])
            ties = sum(c["targets"][t]["long_snow_free_hours_winter"] == v["long_snow_free_hours_winter"] for c in known)
            if ties > 1:
                notes.append(f"(b) table 2, {t}: {ties} measured cells tie for the most winter-half hours ({v['long_snow_free_hours_winter']})")
    else:
        lines = [l for l in sec.split("\n") if re.match(r"- (Connecting ridge|Malapert|Mons Mouton|Nobile Rim 2): ", l)]
        for t, line in zip(tids, lines):
            share, cal = winter_share(t)
            top = sorted(range(36), key=lambda b: -cal[b])[:3]
            mine = f"- {SHORT[t]}: {1 - share:.1%} of the long-window snow-free hours × bare km² fall in the summer half; the three ten-day bins with the most are " \
                   + ", ".join(f"{bin_label(b)} ({cal[b] / cal.sum():.0%})" for b in top) + "."
            check_text(f"(c) summer share and top bins, {t}", mine, line)
        for t, row in zip(tids, tb[1][1:]):
            reg = Counter(c["region"] for c in measured if (c["targets"][t]["long_snow_free_hours_summer"] or 0) >= 100).most_common()
            mine = ", ".join(f"{k} {v:,}" for k, v in reg[:6]) + (f"; other regions {sum(v for _, v in reg[6:]):,}" if len(reg) > 6 else "")
            check(f"(c) table 2 cells with 100 summer-half hours, {t}", [sum(v for _, v in reg)], row[1])
            check_text(f"(c) table 2 regions, {t}", mine, row[2])
        for t, row in zip(tids, tb[2][1:]):
            grp = [c for c in measured if (c["targets"][t]["long_snow_free_hours_summer"] or 0) >= 100 and c["targets"][t]["poleward_share"] is not None]
            sh, la = [c["targets"][t]["poleward_share"] for c in grp], [c["lat"] for c in grp]
            check(f"(c) table 3 poleward share, {t}", [len(grp), round(pc(sh, 50), 2), round(pc(sh, 10), 2), round(pc(sh, 90), 2), round(pc(la, 10), 1), round(pc(la, 90), 1)],
                  " ".join(row[1:]), tol=0.0051)

# ---------------------------------------------------------------- (d)
sec = section("d")
tb = tables(sec)
cand = json.loads((D / "candidates.json").read_text())
sample_ids = {c["id"] for c in cand if "sample" in c["why"]}
groups = {"north sample": [c for c in measured if c["id"] in sample_ids], "north all": measured,
          "south sample": [c for c in south if c["id"] in sample_ids], "south all": south}


def shares(group, t):
    out = []
    for c in group:
        if not has_h(c):
            continue
        v = c["targets"][t]
        o, b = (v["long_open_hours"], v["long_snow_free_hours"]) if c["hemisphere"] == "N" else (v["long_summer_rock_open_hours"], v["long_summer_rock_hours"])
        if o is not None and b is not None and b > 0:
            out.append(o / b)
    return out


def spread(vals):
    return [len(vals)] + ([round(pc(vals, q), 3) for q in (10, 25, 50, 75, 90)] if vals else [])


for t, row in zip(tids, tb[0][1:]):
    mine = []
    for name in ("north sample", "north all", "south sample", "south all"):
        mine += spread(shares(groups[name], t))
    check(f"(d) table 1 share left, {t}", mine, " ".join(row[1:]), tol=0.00051)
intro = sec.split("\n")[3]
check("(d) intro: sample sizes and horizon counts",
      [2, len(groups["north sample"]), len(groups["south sample"]), 3, len(m_h), len(measured), len(s_h), len(south)],
      nums(intro.split("(`")[0]) + nums(intro.split("`). ")[1].split(", so the same")[0]))
no_h_sample = [c["id"] for c in groups["north sample"] + groups["south sample"] if not has_h(c)]
if "every sample cell has a horizon" in sec and no_h_sample:
    differ.append(f"(d) text says every sample cell has a horizon; {len(no_h_sample)} sample cells have none: {no_h_sample[:5]}")
found = re.search(r"(\d+) of its (\d+) northern cells and (\d+) of its (\d+) southern cells have a horizon", sec)
if found:
    check("(d) sample cells with a horizon", [sum(has_h(c) for c in groups["north sample"]), len(groups["north sample"]),
                                              sum(has_h(c) for c in groups["south sample"]), len(groups["south sample"])], [float(x) for x in found.groups()])
line = next(l for l in sec.split("\n") if l.startswith("- Median terrain horizon"))
med = lambda grp, key: round(float(np.median([c["horizon"][key] for c in grp if has_h(c)])), 2)
check("(d) median horizons", [med(groups["north sample"], "north_deg"), med(groups["north sample"], "south_deg"), len(m_h), med(measured, "north_deg"), med(measured, "south_deg")],
      nums(line.split("(`")[0]), tol=0.0051)
line = next(l for l in sec.split("\n") if l.startswith("- The lower the Sun limit"))
check("(d) median share kept, percent: all measured then sample",
      [round(100 * pc(shares(measured, t), 50), 1) for t in tids] + [round(100 * pc(shares(groups["north sample"], t), 50), 1) for t in tids], [float(x) for x in re.findall(r"([\d.]+)%", line)], tol=0.051)
for row in tb[1][1:]:
    c = by_id[row[1]]
    v = c["targets"]["malapert"]
    left = round(100 * v["long_open_hours"] / v["long_snow_free_hours"]) if v["long_snow_free_hours"] else None
    check(f"(d) table 2 named example {row[0]}", [round(c["horizon"]["north_deg"], 2), round(c["horizon"]["south_deg"], 2), v["long_flat_hours"], v["long_snow_free_hours"], v["long_open_hours"], left],
          " ".join(row[2:]), tol=0.0051)

# ---------------------------------------------------------------- (e) first five rows
rn = [r for r in recs if r["ranked"] and r["ranking"] == "north"]
rs = [r for r in recs if r["ranked"] and r["ranking"] == "south"]


def sites_of(pool_records, goal, t, n, south_=False):
    field = "long_summer_rock_open_hours" if south_ else "long_open_hours"
    pool = [r for r in pool_records if r["targets"][t]["goals"][goal] is not None and r["targets"][t]["goals"][goal] > 0]
    pool.sort(key=lambda r: (-r["targets"][t]["goals"][goal], -(r["targets"][t][field] or 0.0)))
    out = []
    for r in pool:
        if all(hav(r, s) >= 50.0 for s in out):
            out.append(r)
        if len(out) == n:
            break
    return out, pool


def site_numbers(r, t, goal):
    v = r["targets"][t]
    if r["hemisphere"] == "S":
        h, fl, cl = v["long_summer_rock_open_hours"], v["long_summer_rock_hours"], v["long_summer_rock_open_hours_clear"]
    else:
        h, fl, cl = v["long_open_hours"], v["long_snow_free_hours"], v["long_open_hours_clear"]
    return [r["lat"], r["lon"], round(r["bare"], 2), round(h), round(fl), None if cl is None else round(cl), v["goals"][goal]]


sec = section("e")
tb = tables(sec)
k = 0
for t in tids:
    sites, pool = sites_of(rn, "lighting", t, 5)
    for n, (r, row) in enumerate(zip(sites, tb[k][1:]), start=1):
        check(f"(e) lighting top 5, {t}, row {n}", site_numbers(r, t, "lighting"), " ".join([row[1], row[3], row[4], row[5], row[6]]), tol=0.5001 if False else 0.0)
        check_text(f"(e) lighting top 5, {t}, row {n}: region", r["region"], row[2])
        tbn = ", ".join(f"{bin_label(b)} ({h:.0f} h)" if h >= 1 else f"{bin_label(b)} ({h:.1f} h)" for b, h in r["targets"][t]["top_bins"]) or "none"
        check_text(f"(e) lighting top 5, {t}, row {n}: best bins", tbn, row[7])
    if len(tb[k]) - 1 != len(sites):
        differ.append(f"(e) lighting {t}: {len(sites)} sites mine, {len(tb[k]) - 1} rows printed")
    k += 1
    top = pool[0]["targets"][t]["goals"]["lighting"]
    line = re.search(rf"### {re.escape(next(x['name'] for x in meta['targets'] if x['id'] == t))}.*?\n(\d+) ranked cell\(s\) hold the top score ([\d.]+); ([\d,]+) of the ([\d,]+) ranked cells", sec, flags=re.S)
    check(f"(e) tie and full-marks sentence, {t}", [sum(r["targets"][t]["goals"]["lighting"] == top for r in pool), top,
                                                     sum((r["targets"][t]["light"] or 0) >= 1.0 for r in rn), len(rn)], [float(x.replace(",", "")) for x in line.groups()])
    full_sites, full_pool = sites_of(rn, "full", t, 5)
    all_full = sites_of(rn, "full", t, 10)[0]
    line = re.search(rf"### {re.escape(next(x['name'] for x in meta['targets'] if x['id'] == t))}.*?Full match \(light, terrain, rock, bare\), north: (\d+) ranked cell\(s\) score above zero, (\d+) site", sec, flags=re.S)
    check(f"(e) full match header, {t}", [len(full_pool), len(all_full)], [float(x) for x in line.groups()])
    if full_sites:
        for n, (r, row) in enumerate(zip(full_sites, tb[k][1:]), start=1):
            v = r["targets"][t]
            check(f"(e) full match, {t}, row {n}", site_numbers(r, t, "full") + [round(v["light"], 2), round(v["terrain"], 2), round(v["rock"], 2)],
                  " ".join([row[1], row[3], row[4], row[5], row[6].split(":")[0]]), tol=0.0051)
        if len(tb[k]) - 1 != len(full_sites):
            differ.append(f"(e) full match {t}: {len(full_sites)} sites mine, {len(tb[k]) - 1} rows printed")
        k += 1

# ---------------------------------------------------------------- (g)
sec = section("g")
tb = tables(sec)
check("(g) table 1 header: southern cells with / without a horizon", [len(s_h), len(south) - len(s_h), 50, 100, 200], tb[0][0][4])
for t, row in zip(tids, tb[0][1:]):
    flat = counts(south, "long_summer_rock_hours", t)
    opened = counts(s_h, "long_summer_rock_open_hours", t)
    check(f"(g) table 1, {t}: cells", [flat[0][0], None, flat[1][0], None, flat[2][0], None] + [o[0] for o in opened], " ".join(row[1:]))
    check(f"(g) table 1, {t}: km2", [None, flat[0][1], None, flat[1][1], None, flat[2][1], None, None, None], " ".join(row[1:]), tol=1.0)
line = next(l for l in sec.split("\n") if l.startswith("- The ") and "km² of mapped rock" in l)
check("(g) southern cells and km2 of rock", [len(south), sum(c["bare_km2"] for c in south)], nums(line.split(";")[0]), tol=1.0)
check_text("(g) southern regions", ", ".join(f"{k_} {v}" for k_, v in Counter(c["region"] for c in south).most_common()), line.split("regions: ")[1].split(" (`")[0])
line = next(l for l in sec.split("\n") if "rock-outcrop layers differ" in l)
check("(g) layers disagree", [sum(bool(c["layers_disagree"]) for c in south), 2], nums(line.split("(`")[0]))
line = next(l for l in sec.split("\n") if "southern cells are ranked" in l)
check("(g) ranked southern cells", [len(rs), 0.25], nums(line.split(". See")[0]))
for n_t, t in enumerate(tids):
    sites, pool = sites_of(rs, "lighting", t, 3, south_=True)
    for n, (r, row) in enumerate(zip(sites, tb[1 + n_t][1:]), start=1):
        check(f"(g) south lighting top 3, {t}, row {n}", site_numbers(r, t, "lighting"), " ".join([row[1], row[3], row[4], row[5], row[6]]))
        tbn = ", ".join(f"{bin_label(b)} ({h:.0f} h)" if h >= 1 else f"{bin_label(b)} ({h:.1f} h)" for b, h in r["targets"][t]["top_bins_summer_rock"]) or "none"
        check_text(f"(g) south lighting top 3, {t}, row {n}: best bins", tbn, row[7])
for row in tb[5][1:]:
    c = by_id[row[1]]
    hz = c["horizon"]
    mine = [round(c["bare"], 2), round(c["land_share"], 2), round(hz["north_deg"], 1), round(hz["south_deg"], 1)]
    for t in ("malapert", "nobile-rim-2"):
        mine += [round(c["targets"][t]["long_summer_rock_hours"]), round(c["targets"][t]["long_summer_rock_open_hours"])]
    check(f"(g) named southern site {row[0]}", mine, " ".join([row[2], row[5], row[6], row[7]]), tol=0.051)
    check_text(f"(g) named southern site {row[0]}: in the screen", "yes" if c["gridded"] else "no", row[3])

# ---------------------------------------------------------------- (h)
sec = section("h")
tb = tables(sec)
v1 = json.loads((D / "light_cells_v1.json").read_text())
for t, row in zip(tids, tb[0][1:]):
    old_ids = [cid for cid, per in v1.items() if per[t]["usable_days"] is not None and per[t]["usable_days"] >= 10]
    new = [c for c in north if c["snow"]["status"] == "measured" and c["targets"][t]["usable_days"] is not None and c["targets"][t]["usable_days"] >= 10]
    doubt = [c for c in north if c["snow"]["status"] == "doubtful" and c["targets"][t]["usable_days"] is not None and c["targets"][t]["usable_days"] >= 10]
    year100 = sum(c["targets"][t]["long_snow_free_hours"] is not None and c["targets"][t]["long_snow_free_hours"] >= 100 for c in measured)
    check(f"(h) table 1, {t}: old / new measured / new doubtful / year 100 h", [len(old_ids), len(new), len(doubt), year100], " ".join([row[1], row[2], row[3], row[6]]))
    check_text(f"(h) table 1, {t}: regions", ", ".join(f"{k_} {v}" for k_, v in Counter(c["region"] for c in new).most_common()) or "none", row[4])
    now = Counter()
    for cid in old_ids:
        c = by_id.get(cid)
        if c is None:
            now["not in the new file"] += 1
        elif c["snow"]["status"] != "measured":
            now[c["snow"]["status"]] += 1
        elif c["targets"][t]["usable_days"] is not None and c["targets"][t]["usable_days"] >= 10:
            now["still ≥ 10"] += 1
        else:
            now["measured, now under 10"] += 1
    check_text(f"(h) table 1, {t}: where the old cells are now", "; ".join(f"{k_}: {v}" for k_, v in now.most_common()) or "none", row[5])
    non_gridded_old = [cid for cid in old_ids if cid in by_id and not by_id[cid]["gridded"]]
    if non_gridded_old:
        notes.append(f"(h) table 1, {t}: {len(non_gridded_old)} old cells are named-site cells outside the screen now: {non_gridded_old}")
for t, row in zip(tids, tb[1][1:]):
    sites = sites_of(rn, "lighting", t, 10)[0]
    days = [s["targets"][t]["usable_days"] for s in sites]
    check(f"(h) table 2, {t}", [len(sites), sum(d is not None and d >= 10 for d in days), sum(d is not None and d == 0 for d in days), max(d for d in days if d is not None)], " ".join(row[1:]))
    if any(d is None for d in days):
        notes.append(f"(h) table 2, {t}: {sum(d is None for d in days)} top sites have unknown usable days")

# ---------------------------------------------------------------- (j)
sec = section("j")
tb = tables(sec)
for t, row in zip(tids, tb[0][1:]):
    grp = [c for c in measured if (c["targets"][t]["long_open_hours_summer"] or 0) >= 100 and rec[c["id"]]["cloud"]["pct_by_month"] is not None]
    if not grp:
        check(f"(j) table 1, {t}: no cells", [0], row[1])
        check_text(f"(j) table 1, {t}: n/a row", ["n/a"] * 12, row[2:])
        continue
    arr = np.array([[np.nan if v is None else 1 - v / 100 for v in rec[c["id"]]["cloud"]["pct_by_month"]] for c in grp])
    check(f"(j) table 1 median clear share by month, {t}", [len(grp)] + [round(float(x), 2) for x in np.nanmedian(arr, axis=0)], " ".join(row[1:]), tol=0.0051)
check("(j) intro to table 2", [len(m_h), len(measured) - len(m_h), 50, 100, 200], next(l for l in sec.split("\n") if l.startswith("Measured northern cells with a horizon (")))
i = 1
for t in tids:
    for suffix in ("_winter", "_summer", ""):
        row = tb[1][i]
        i += 1
        o = counts(m_h, f"long_open_hours{suffix}", t)
        cl = counts(m_h, f"long_open_hours_clear{suffix}", t, source=rec)
        unk_o = sum(c["targets"][t][f"long_open_hours{suffix}"] is None for c in m_h)
        unk_c = sum(rec[c["id"]]["targets"][t][f"long_open_hours_clear{suffix}"] is None for c in m_h)
        check(f"(j) table 2, {row[0]}", [x[0] for x in o] + [x[0] for x in cl] + [unk_o, unk_c], " ".join(row[1:]))
h_km = np.array([c["bare_km2"] for c in m_h], dtype=float)
h_rows = np.array([row_of[c["id"]] for c in m_h])
month_of_bin = [b // 3 for b in range(36)]
clear_share = np.array([[np.nan if rec[c["id"]]["cloud"]["pct_by_month"] is None or rec[c["id"]]["cloud"]["pct_by_month"][month_of_bin[b]] is None
                         else 1 - rec[c["id"]]["cloud"]["pct_by_month"][month_of_bin[b]] / 100 for b in range(36)] for c in m_h])
for t, row in zip(tids, tb[2][1:]):
    op = LOP[h_rows, tids.index(t), :]
    cl = np.where(op == 0.0, 0.0, op * clear_share)
    co, cc = np.nansum(op * h_km[:, None], axis=0), np.nansum(cl * h_km[:, None], axis=0)
    mine = [round(100 * cc.sum() / co.sum()), round(100 * cc[WINTER].sum() / co[WINTER].sum()), round(100 * cc[SUMMER].sum() / co[SUMMER].sum()), int(np.isnan(cl).sum())]
    check(f"(j) table 3 share left by the clear-sky factor, {t}", mine, " ".join(row[1:]), tol=0.0)
for n_t, t in enumerate(tids):
    rows = tb[3 + n_t][1:]
    sites = sites_of(rn, "lighting", t, 5)[0]
    pool = sorted((r for r in rn if (r["targets"][t]["long_open_hours_clear"] or 0) > 0), key=lambda r: -r["targets"][t]["long_open_hours_clear"])
    clearest = []
    for r in pool:
        if all(hav(r, s) >= 50.0 for s in clearest):
            clearest.append(r)
        if len(clearest) == 3:
            break
    for r, row in zip(sites + clearest, rows):
        v = r["targets"][t]
        ratio = round(100 * v["long_open_hours_clear"] / v["long_open_hours"]) if v["long_open_hours"] and v["long_open_hours_clear"] is not None else None
        check(f"(j) top sites with clear-sky hours, {t}, {row[0]}", [r["lat"], r["lon"], round(r["bare"], 2), round(v["long_open_hours"]), round(v["long_open_hours_clear"]), ratio, v["goals"]["lighting"]],
              " ".join(row[1:2] + row[3:]), tol=0.0)
    if len(rows) != len(sites) + len(clearest):
        differ.append(f"(j) top sites table {t}: {len(sites) + len(clearest)} rows mine, {len(rows)} printed")

# ---------------------------------------------------------------- (k)
sec = section("k")
tb = tables(sec)
lp = json.loads((D / "latitude_profile.json").read_text())
val2 = json.loads((D / "validation_v2.json").read_text())
recs2 = json.loads((D / "cells_scored_v2.json").read_text())["cells"]
i = 1
for t in tids:
    for hemi in ("N", "S"):
        row = tb[0][i]
        i += 1
        a, b = abs(lp["thresholds"][t][hemi]["lowest_lat_with_long_window_bin_median"]["2"]), abs(lp["thresholds"][t][hemi]["lowest_lat_with_long_window"]["2"])
        check(f"(k) table 1 {row[0]}", [a, b] + ([round(b - a, 2)] if round(b - a, 2) else []), " ".join(row[1:4]), tol=0.0051)
i = 1
bp2 = val2["big_picture_north"]["targets"]
for t in tids:
    for season, suffix in (("winter_half", "_winter"), ("summer_half", "_summer")):
        mine = counts(measured, f"long_snow_free_hours{suffix}", t)
        for n_l, level in enumerate(LEVELS):
            row = tb[1][i]
            i += 1
            old = bp2[t]["long_snow_free_hours"][season][str(level)]["cells"]
            new = mine[n_l][0]
            check(f"(k) table 2 {row[0]}", [old, new] + ([new - old] if new != old else []), " ".join(row[1:4]))
for t, row in zip(tids, tb[2][1:]):
    cal2 = bp2[t]["calendar_hours_times_bare_km2"]
    old = 100 * sum(cal2[b] for b in WINTER) / sum(cal2)
    new = 100 * winter_share(t)[0]
    check(f"(k) table 3 winter share, {t}", [round(old, 2), round(new, 2), round(new - old, 2)], " ".join(row[1:4]), tol=0.0051)
i = 1
for t in tids:
    for side, hemi in (("north", "N"), ("south", "S")):
        row = tb[3][i]
        i += 1
        grp2 = [r for r in recs2 if r["id"] in sample_ids and r["hemisphere"] == hemi]
        old = shares(grp2, t)
        new_s = shares(groups[f"{side} sample"], t)
        new_a = shares(groups[f"{side} all"], t)
        check(f"(k) table 4 {row[0]}", [round(pc(old, 50), 3), len(old), round(pc(new_s, 50), 3), len(new_s), round(pc(new_a, 50), 3), len(new_a)], " ".join(row[1:4]), tol=0.00051)
sites2 = {s["name"]: s for s in val2["named_sites"]["sites"]}
val = json.loads((D / "validation.json").read_text())
cell_of_site = {s["name"]: s["cell"] for s in val["named_sites"]["sites"]}
for row in tb[4][1:]:
    c = by_id[cell_of_site[row[0]]]
    m2 = sites2[row[0]]["targets"]["malapert"]
    v = c["targets"]["malapert"]
    if c["hemisphere"] == "N":
        mine = [m2[k_]["long"]["year"] for k_ in ("flat", "snow_free", "open")] + [v["long_flat_hours"], v["long_snow_free_hours"], v["long_open_hours"]]
    else:
        mine = [m2["long_summer_rock_hours"], m2["long_summer_rock_open_hours"], v["long_summer_rock_hours"], v["long_summer_rock_open_hours"]]
    check(f"(k) table 5 {row[0]}", mine, " ".join(row[2:4]), tol=0.0)
    check_text(f"(k) table 5 {row[0]}: snow odds", c["snow"]["status"], row[1])
i = 1
rn2 = [r for r in recs2 if r["ranked"] and r["ranking"] == "north"]
for t in tids:
    old_sites, new_sites = sites_of(rn2, "lighting", t, 3)[0], sites_of(rn, "lighting", t, 3)[0]
    for n in range(3):
        row = tb[5][i]
        i += 1
        mine = []
        for r in (old_sites[n], new_sites[n]):
            mine += [r["lat"], r["lon"], round(r["targets"][t]["long_open_hours"]), r["targets"][t]["goals"]["lighting"]]
        check(f"(k) table 6 {row[0]}", mine, " ".join(row[1:3]))
        o_, n_ = old_sites[n], new_sites[n]
        want = "same cell" if o_["id"] == n_["id"] else ("15" if n_["id"] not in {r["id"] for r in recs2} else "12, 13")
        check_text(f"(k) table 6 {row[0]}: what moved it begins '{want}'", True, row[3].startswith(want))
src = next(l for l in sec.split("\n") if l.startswith("Source: `cells_scored_v2.json` ("))
check("(k) table 6 source line", [2, len(recs2), len(rn2), len(recs), len(rn), 50], nums(src.replace("`cells_scored_v2.json`", "").replace("`cells_scored.json`", "")) if False else
      [2, float(re.search(r"\(([\d,]+) records", src).group(1).replace(",", "")), float(re.search(r"records, ([\d,]+) ranked", src).group(1).replace(",", "")),
       float(re.findall(r"\(([\d,]+) records", src)[1].replace(",", "")), float(re.findall(r"records, ([\d,]+) ranked", src)[1].replace(",", "")), 50])

# ---------------------------------------------------------------- what was searched, and figures of (i)
head_rows = {row[0]: row[1] for row in tables(TEXT[:TEXT.index("\n## (a) ")])[0][1:]}
n_h = sum(has_h(c) for c in cells)
rankable = [c for c in measured if c["bare"] >= scored["meta"]["rank_min_bare"]]
check("searched: cell records", [len(cells)], head_rows["Cell records"])
check("searched: named-site cells outside the screens", [sum(not c["gridded"] for c in cells)], head_rows["Named-site cells outside those screens (reported apart)"])
check("searched: cells with a terrain horizon", [n_h, len(cells)], head_rows["Cells with a terrain horizon"])
check("searched: measured northern cells with a horizon / without", [len(m_h), len(measured) - len(m_h)], head_rows["Measured northern cells with a horizon / without"])
check("searched: southern cells with a horizon / without", [len(s_h), len(south) - len(s_h)], head_rows["Southern cells with a horizon / without"])
check("searched: ranked cells, north / south", [len(rn), len(rs)], head_rows["Ranked cells, north / south"])
waiting_label = next(k_ for k_ in head_rows if k_.startswith("Measured northern cells with bare"))
check("searched: measured cells with enough bare ground and no horizon", [sum(not has_h(c) for c in rankable), len(rankable)], head_rows[waiting_label])
sec = section("i")
rule_table = next(tb_ for tb_ in tables(sec) if len(tb_[0]) > 1 and tb_[0][1].startswith("Measured cells whose figure differs"))
for t, row in zip(tids, rule_table[1:]):
    pairs = [(c["targets"][t]["long_snow_free_hours"], c["targets"][t]["long_snow_free_hours_with_rule"], c) for c in measured]
    pairs = [p for p in pairs if p[0] is not None and p[1] is not None]
    unlike = [p for p in pairs if p[0] != p[1]]
    zero = [p for p in unlike if p[1] == 0.0 and p[0] > 0]
    check(f"(i) measured cells whose figure differs from the rule's, {t}", [len(unlike)], row[1])
    check(f"(i) cells with 0.0 h under the rule, {t}", [len(zero), max(p[0] for p in zero) if zero else None,
                                                         sum(p[2]["targets"][t]["long_snow_free_hours_summer"] == 0.0 for p in zero)],
          " ".join(row[3:6]) if zero else [float(len(zero)), None, 0.0])
found = re.search(r"([\d,]+) of the ([\d,]+) measured cells have fewer than 7 pixels on land, and (\d+) take", sec)
check("(i) thin snow: measured cells under 7 land pixels, measured cells, cells on the 5 x 5 block",
      [sum((c["snow"]["land_pixels"] or 0) < 7 for c in measured), len(measured), sum(c["snow"]["source"] == "5x5" for c in measured)],
      [float(x.replace(",", "")) for x in found.groups()])
found = re.search(r"Among the ([\d,]+) ranked northern cells ([\d,]+) have fewer than 7", sec)
check("(i) thin snow among ranked cells", [len(rn), sum((r["snow"]["land_pixels"] or 0) < 7 for r in rn)], [float(x.replace(",", "")) for x in found.groups()])
line = next(l for l in sec.split("\n") if "throws a shadow of at least" in l)
check("(i) shadow of a 1 m rock at each limit, m", [round(1 / math.tan(math.radians(t_["limit_deg"])), 1) for t_ in meta["targets"]],
      [float(x) for x in re.findall(r"([\d.]+) m \(", line)], tol=0.051)
found = re.search(r"The ratio is ([\d.]+) at 60°, ([\d.]+) at 70°, ([\d.]+) at 80°", sec)
moon_deg_per_hour = 360.0 / (29.530589 * 24.0)     # once round the horizon in a synodic month
check("(i) how many times faster the Sun's compass direction moves on Earth", [round(15.0 * math.sin(math.radians(lat)) / moon_deg_per_hour, 1) for lat in (60, 70, 80)],
      [float(x) for x in found.groups()], tol=0.051)

print(f"figures and texts compared: {checked}")
print(f"differences: {len(differ)}")
for d in differ:
    print("  ", d)
for d in notes:
    print("   note:", d)

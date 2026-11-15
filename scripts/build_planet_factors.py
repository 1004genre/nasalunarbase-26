# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Planet-side factors for the lunar regions (moon_cards.json) and the Mars sites (mars_sites.json).

Figures that exist only on the Moon or Mars: thermal inertia, rock abundance,
near-surface hydrogen, depth to ice (Mars), surface activity, quakes, albedo and
the daily temperature swing. Each value is either read from a small public data
file at the place's coordinates, or copied from a published sentence that was
opened and saved in data/raw/planet_factors/pages. Where no public figure was
found or could be read tonight, the value is null and the note says why.

Reads (never changes) data/derived/moon_cards.json, data/derived/mars_sites.json
and the MCD hourly tables already saved by the Mars-climate job in
data/raw/mars_climate/mcd. Downloads only what is missing from
data/raw/planet_factors (User-Agent twinfinder/0.1, retries), so a second run
asks for nothing. Writes data/derived/planet_factors.json beside the old file and
renames it into place.

    uv run python scripts/build_planet_factors.py            # fetch missing, build
    uv run python scripts/build_planet_factors.py --offline  # build from saved files only
"""
from __future__ import annotations

import argparse
import html
import json
import math
import os
import re
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "planet_factors"
DERIVED = ROOT / "data" / "derived"
OUT = DERIVED / "planet_factors.json"
UA = "twinfinder/0.1"

MOON_RADIUS_KM = 1737.4  # volumetric mean radius, NSSDCA Moon Fact Sheet (saved: data/raw/moon_provenance/nssdc_moonfact.html)

# ---------------------------------------------------------------- sources
# key -> (url, saved path under data/raw/planet_factors)
SOURCES = {
    "tes_ti_img": ("https://pds-geosciences.wustl.edu/mgs/mgs-m-tes-5-timap-v1/mgst_9001/data/global_ti_night_2007.img", "tes_ti/global_ti_night_2007.img"),
    "tes_ti_lbl": ("https://pds-geosciences.wustl.edu/mgs/mgs-m-tes-5-timap-v1/mgst_9001/data/global_ti_night_2007.lbl", "tes_ti/global_ti_night_2007.lbl"),
    "tes_ti_msk": ("https://pds-geosciences.wustl.edu/mgs/mgs-m-tes-5-timap-v1/mgst_9001/data/global_ti_msk_night_2007.img", "tes_ti/global_ti_msk_night_2007.img"),
    "tes_ti_msk_lbl": ("https://pds-geosciences.wustl.edu/mgs/mgs-m-tes-5-timap-v1/mgst_9001/data/global_ti_msk_night_2007.lbl", "tes_ti/global_ti_msk_night_2007.lbl"),
    "tes_albedo": ("https://planetarymaps.usgs.gov/mosaic/Mars_MGS_TES_Albedo_mosaic_global_7410m.tif", "tes_albedo/Mars_MGS_TES_Albedo_mosaic_global_7410m.tif"),
    "tes_albedo_page": ("https://astrogeology.usgs.gov/search/map/mars_mgs_tes_global_bolometric_albedo_map_7410m", "usgs_tes_albedo_page.html"),
    "grs_h2o_tab": ("https://pds-geosciences.wustl.edu/ody/ody-m-grs-5-elements-v1/odgm_xxxx/data/smoothed/h2o_sr_5x5.tab", "grs/h2o_sr_5x5.tab"),
    "grs_h2o_lbl": ("https://pds-geosciences.wustl.edu/ody/ody-m-grs-5-elements-v1/odgm_xxxx/data/smoothed/h2o_sr_5x5.lbl", "grs/h2o_sr_5x5.lbl"),
    "lp_h_halfdeg": ("https://pds-geosciences.wustl.edu/missions/lunarp/reduced/hydrogenhd.txt", "lp/hydrogenhd.txt"),
    "diviner_ra_lbl": ("https://pds-geosciences.wustl.edu/lro/urn-nasa-pds-lro_diviner_derived1/data_derived_gdr_l3/cylindrical/img/dgdr_ra_avg_cyl_128_img.lbl", "diviner/dgdr_ra_avg_cyl_128_img.lbl"),
    "diviner_gdr_inv": ("https://pds-geosciences.wustl.edu/lro/urn-nasa-pds-lro_diviner_derived1/data_derived_gdr_l3/collection_data_derived_gdr_level3_inventory.csv", "diviner/gdr_l3_inventory.csv"),
    "diviner_pcp_inv": ("https://pds-geosciences.wustl.edu/lro/urn-nasa-pds-lro_diviner_derived1/data_derived_pcp/collection_data_derived_pcp_inventory.csv", "diviner/pcp_inventory.csv"),
    "asu_irtm_rocks": ("https://www.mars.asu.edu/data/irtm_rocks/", "pages/asu_irtm_rocks.html"),
    "nasa_moonquakes": ("https://www.nasa.gov/solar-system/moon/shrinking-moon-causing-moonquakes-and-faults-near-lunar-south-pole/", "pages/nasa_shrinking_moon_south_pole.html"),
    "nasa_insight_end": ("https://mars.nasa.gov/news/9321/nasa-retires-insight-mars-lander-mission-after-years-of-science/?site=insight", "pages/nasa_insight_retired.html"),
    "nasa_dodo": ("https://science.nasa.gov/photojournal/dodo-goldilocks-trench-dug-by-phoenix/", "pages/nasa_dodo_goldilocks.html"),
    "arvidson2009": ("https://www-robotics.jpl.nasa.gov/media/documents/2009JE003408.pdf", "pages/jpl_arvidson2009_phoenix_arm.pdf"),
    "morgan2021": ("https://ntrs.nasa.gov/api/citations/20205008958/downloads/Morgan_etal_NA_Perspective_NATASTRON_19122833C%20.pdf", "pages/ntrs_morgan2021_swim.pdf"),
    "apod_namib": ("https://science.nasa.gov/image-article/apod-2016-january-19-a-dark-sand-dune-on-mars/", "pages/nasa_apod_namib_dune.html"),
}

# Sources tried tonight that did not answer (kept so the notes can say so).
FAILED = {
    "https://swim.psi.edu/": "HTTP 523 (server unreachable) on 4 tries, 14 Nov 2026",
    "https://www.jpl.nasa.gov/news/*": "HTTP 403 to scripted requests on 4 tries for each of 4 news pages",
    "https://iopscience.iop.org/article/10.3847/PSJ/ad1332": "answered with a search/robot page, not the paper (Watters et al. 2024); the NASA release was used instead",
    "https://www.nasa.gov/missions/insight/nasa-marsquake-data-reveals-lumpy-nature-of-red-planets-interior/": "HTTP 429 (too many requests); the mars.nasa.gov InSight retirement release gives the same count",
}

LICENCES = {
    "NASA PDS (TES thermal inertia, Odyssey GRS, Lunar Prospector, LRO Diviner)": {
        "licence": "Public NASA archive data; no login; no copyright restriction stated on the PDS Geosciences Node pages",
        "credit": "NASA Planetary Data System, Geosciences Node (Washington University in St. Louis), with the instrument teams named per factor",
    },
    "USGS Astrogeology (TES albedo mosaic)": {
        "licence": "Access constraints: public domain (USGS product page); 'Please cite authors'",
        "credit": "Christensen, P., et al. (2001), MGS TES; originator Arizona State University; publisher USGS Astrogeology Science Center",
    },
    "NASA web pages (nasa.gov, mars.nasa.gov, science.nasa.gov)": {
        "licence": "NASA content, generally not subject to copyright in the US; credit NASA",
        "credit": "NASA / JPL-Caltech; image credits as on each page",
    },
    "Arvidson et al. 2009 (JGR 114, E00E02)": {
        "licence": "Copyright 2009 American Geophysical Union; open copy on the JPL robotics site; only a short phrase is quoted",
        "credit": "Arvidson, R. E., et al. (2009), Results from the Mars Phoenix Lander Robotic Arm experiment, J. Geophys. Res., 114, E00E02, doi:10.1029/2009JE003408",
    },
    "Morgan et al. 2021 (Nature Astronomy), NASA-funded SWIM project": {
        "licence": "Author manuscript on NASA NTRS (20205008958); only short phrases are quoted",
        "credit": "Morgan, G. A., et al. (2021), Availability of subsurface water-ice resources in the northern mid-latitudes of Mars, Nature Astronomy 5, 230-236",
    },
    "Mars Climate Database (daily swing, from the Mars-climate job's saved tables)": {
        "licence": "MCD web interface output; free for research use with credit",
        "credit": "Mars Climate Database v6.2 (c) LMD/LATMOS/OU/IAA/ESA/CNES",
    },
}


def fetch(url: str, dest: Path, tries: int = 4) -> bool:
    """Download url to dest unless dest already holds data. Logs to <folder>/_downloads.tsv."""
    if dest.exists() and dest.stat().st_size > 0:
        return True
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    for i in range(1, tries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=180) as r, open(part, "wb") as f:
                while chunk := r.read(1 << 20):
                    f.write(chunk)
            os.replace(part, dest)
            with open(dest.parent / "_downloads.tsv", "a") as log:
                log.write(f"{url}\t{dest.name}\t{datetime.now(timezone.utc):%Y-%m-%dT%H:%M:%SZ}\n")
            return True
        except Exception as e:  # network has dropped twice tonight: wait and retry
            print(f"  try {i} failed for {url}: {e}")
            time.sleep(5 * i)
    part.unlink(missing_ok=True)
    return False


def page_text(path: Path) -> str:
    t = path.read_text(errors="replace")
    t = re.sub(r"(?s)<script.*?</script>|<style.*?</style>", " ", t)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t)))


def must_contain(path: Path, phrase: str) -> str:
    """Return phrase if the saved page really contains it, so no sentence is cited from memory."""
    if phrase not in page_text(path):
        raise SystemExit(f"{path.name} no longer contains: {phrase!r}")
    return phrase


def e(value=None, kind=None, source=None, url=None, note=None, **extra):
    d = {"value": value, "kind": kind, "source": source, "url": url, "note": note}
    d.update(extra)
    return d


def lon180(lon_east: float) -> float:
    return ((lon_east + 180.0) % 360.0) - 180.0


def fnum(x, nd=3):
    return None if x is None or (isinstance(x, float) and not math.isfinite(x)) else round(float(x), nd)


# ---------------------------------------------------------------- Mars readers
def read_tes_ti(sites):
    lbl = (RAW / SOURCES["tes_ti_lbl"][1]).read_text()
    lines = int(re.search(r"LINES\s*=\s*(\d+)", lbl).group(1))
    samples = int(re.search(r"LINE_SAMPLES\s*=\s*(\d+)", lbl).group(1))
    ppd = float(re.search(r"MAP_RESOLUTION\s*=\s*([\d.]+)", lbl).group(1))
    ti = np.memmap(RAW / SOURCES["tes_ti_img"][1], dtype=">i2", mode="r", shape=(lines, samples))
    msk = np.memmap(RAW / SOURCES["tes_ti_msk"][1], dtype="u1", mode="r", shape=(lines, samples))
    out = {}
    for s in sites:
        lat, lon = s["lat"], lon180(s["lon_east"])
        r = min(int((90.0 - lat) * ppd), lines - 1)
        c = min(int((lon + 180.0) * ppd), samples - 1)
        v = int(ti[r, c])
        h = int(round(0.25 * ppd))  # 0.5 degree box, the size of a Mars square
        box = np.asarray(ti[max(r - h, 0): r + h, max(c - h, 0): c + h], dtype=float)
        box[box <= 0] = np.nan
        out[s["id"]] = {
            "pixel": v if v > 0 else None,
            "interpolated": bool(msk[r, c] == 0),
            "box_median": fnum(np.nanmedian(box), 0) if np.isfinite(box).any() else None,
            "box_min": fnum(np.nanmin(box), 0) if np.isfinite(box).any() else None,
            "box_max": fnum(np.nanmax(box), 0) if np.isfinite(box).any() else None,
            "pixel_km": round(3396.0 * math.pi / 180.0 / ppd, 2),
        }
    return out


def read_tes_albedo(sites):
    out = {}
    with rasterio.open(RAW / SOURCES["tes_albedo"][1]) as ds:
        a = ds.read(1).astype(float)
        nod = ds.nodata
        R = 3396000.0
        for s in sites:
            x = math.radians(lon180(s["lon_east"])) * R
            y = math.radians(s["lat"]) * R
            r, c = ds.index(x, y)
            v = a[r, c]
            ok = np.isfinite(v) and (nod is None or v != nod) and v > 0
            h = 2  # 8 ppd: +-2 pixels is about a 0.5 degree box
            box = a[max(r - h, 0): r + h, max(c - h, 0): c + h].copy()
            box[(box <= 0) | ~np.isfinite(box) | (box == nod)] = np.nan
            out[s["id"]] = {
                "pixel": fnum(v, 3) if ok else None,
                "box_median": fnum(np.nanmedian(box), 3) if np.isfinite(box).any() else None,
                "pixel_km": round(abs(ds.transform.a) / 1000.0, 2),
            }
    return out


def read_grs_h2o(sites):
    rows = {}
    for line in (RAW / SOURCES["grs_h2o_tab"][1]).read_text().splitlines():
        p = line.split()
        if len(p) < 4:
            continue
        lat, lon, conc, sig = map(float, p[:4])
        rows[(lat, lon)] = (None if conc >= 9999 else conc, None if sig >= 9999 else sig)
    out = {}
    for s in sites:
        latc = math.floor(s["lat"] / 5.0) * 5.0 + 2.5
        lonc = math.floor((s["lon_east"] % 360.0) / 5.0) * 5.0 + 2.5
        conc, sig = rows.get((latc, lonc), (None, None))
        out[s["id"]] = {"bin_lat": latc, "bin_lon_east": lonc, "wt_pct": conc, "sigma": sig}
    return out


def read_mcd_swing(site_id):
    """Daily max minus min, per season (Ls step 15 deg), from the Mars-climate job's saved MCD table."""
    path = ROOT / "data" / "raw" / "mars_climate" / "mcd" / f"{site_id}_2d.txt"
    if not path.exists():
        return None
    blocks, cur = {}, None
    for line in path.read_text().splitlines():
        m = re.match(r"### Columns 2\+ are (.+?) \((\w+)\)", line)
        if m:
            cur = m.group(1)
            blocks[cur] = []
            continue
        m = re.match(r"^([+-]\d{3}) \|\|(.*)$", line)
        if m and cur:
            vals = [float(v) for v in m.group(2).split()]
            blocks[cur].append(vals)
    res = {}
    for name, key in (("Surface temperature", "ground"), ("Temperature", "air_2m")):
        rows = np.array(blocks.get(name) or [], dtype=float)
        if rows.size == 0:
            continue
        sw = rows.max(axis=1) - rows.min(axis=1)
        res[key] = {"mean_K": fnum(sw.mean(), 1), "smallest_K": fnum(sw.min(), 1), "largest_K": fnum(sw.max(), 1), "seasons": int(len(sw))}
    return res, path


# ---------------------------------------------------------------- Moon readers
def read_lp_hydrogen(cards):
    # A few bins hold '**********' (a Fortran-style overflow mark in the file): read as unknown.
    text = (RAW / SOURCES["lp_h_halfdeg"][1]).read_text().replace("**********", "nan")
    data = np.loadtxt(text.splitlines(), comments="#", delimiter=",")
    lat_c = (data[:, 0] + data[:, 1]) / 2.0
    lon_c = (data[:, 2] + data[:, 3]) / 2.0
    h = data[:, 4]
    out = {}
    for c in cards:
        lat0, lon0 = c["centre"]["lat"], lon180(c["centre"]["lon_east"])
        inside = (data[:, 0] <= lat0) & (lat0 < data[:, 1]) & (data[:, 2] <= lon0) & (lon0 < data[:, 3])
        centre_val = float(h[inside][0]) if inside.any() else None
        # great-circle distance from the region centre to every bin centre in the far south
        sel = lat_c < -75
        la, lo = np.radians(lat_c[sel]), np.radians(lon_c[sel])
        p0, l0 = math.radians(lat0), math.radians(lon0)
        d = MOON_RADIUS_KM * np.arccos(np.clip(np.sin(p0) * np.sin(la) + np.cos(p0) * np.cos(la) * np.cos(lo - l0), -1, 1))
        half = max(c.get("extent_km") or [16.0]) / 2.0
        near = h[sel][d <= half * math.sqrt(2)]
        out[c["id"]] = {
            "centre_bin": fnum(centre_val, 1),
            "bins_in_region": int(near.size),
            "region_min": fnum(near.min(), 1) if near.size else None,
            "region_max": fnum(near.max(), 1) if near.size else None,
        }
    return out


def diviner_ra_limits():
    lbl = (RAW / SOURCES["diviner_ra_lbl"][1]).read_text()
    mx = float(re.search(r"MAXIMUM_LATITUDE\s*=\s*(-?[\d.]+)", lbl).group(1))
    mn = float(re.search(r"MINIMUM_LATITUDE\s*=\s*(-?[\d.]+)", lbl).group(1))
    return mn, mx


def diviner_polar_products():
    """Which kinds of product the Diviner derived bundle publishes in polar projection."""
    kinds = set()
    for key in ("diviner_gdr_inv", "diviner_pcp_inv"):
        for line in (RAW / SOURCES[key][1]).read_text().splitlines():
            name = line.split("::")[0].split(":")[-1]
            if "_pols" in name or "_poln" in name:
                kinds.add(re.sub(r"_(\d{8}[dn]?|ltim\d+|slon\d+|ls\d+|sum|win|\d{3}|img)(?=_|$)", "", name))
    return sorted(kinds)


# ---------------------------------------------------------------- build
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="use saved files only; never touch the network")
    args = ap.parse_args()

    missing = []
    for key, (url, rel) in SOURCES.items():
        p = RAW / rel
        if not (p.exists() and p.stat().st_size > 0):
            if args.offline or not fetch(url, p):
                missing.append(key)
    if missing:
        print("missing raw files (their factors will be null):", missing)

    moon_cards = json.loads((DERIVED / "moon_cards.json").read_text())["cards"]
    mars_sites = json.loads((DERIVED / "mars_sites.json").read_text())["sites"]
    moon_ids = [c["id"] for c in moon_cards]
    mars_ids = [s["id"] for s in mars_sites]
    mars_by_id = {s["id"]: s for s in mars_sites}
    moon_by_id = {c["id"]: c for c in moon_cards}

    def has(*keys):
        return all(k not in missing for k in keys)

    factors = []
    pages = {k: RAW / SOURCES[k][1] for k in SOURCES}
    url = {k: SOURCES[k][0] for k in SOURCES}

    # ---------- 1 thermal inertia
    ti = read_tes_ti(mars_sites) if has("tes_ti_img", "tes_ti_lbl", "tes_ti_msk") else {}
    polar = diviner_polar_products() if has("diviner_gdr_inv", "diviner_pcp_inv") else []
    f = {"id": "thermal_inertia", "name": "Thermal inertia",
         "what_it_is": "How strongly the top few centimetres of ground resist heating and cooling. Loose dust is low (below about 100), sand and crusted soil middle, rock and ice-cemented ground high.",
         "unit": "J m-2 K-1 s-1/2 (tiu)", "moon": {}, "mars": {}}
    for cid in moon_ids:
        f["moon"][cid] = e(None, None, "LRO Diviner derived data bundle, PDS (product inventories read)",
                           "https://pds-geosciences.wustl.edu/lro/urn-nasa-pds-lro_diviner_derived1/",
                           "No public Diviner thermal-inertia figure found for the polar regions. The bundle's polar (pols/poln) products are only "
                           + ", ".join(polar) + " (bolometric temperatures). The cylindrical maps stop at 80 deg. "
                           "Diviner model temperatures and ice depth for this region are already in data/derived/moon_cards.json -> cards[id].diviner.",
                           scope=None)
    for sid in mars_ids:
        r = ti.get(sid)
        if not r or r["pixel"] is None:
            f["mars"][sid] = e(None, None, "MGS TES night-time thermal inertia, Putzig & Mellon 2007", url["tes_ti_img"], "no value at this pixel or file missing")
            continue
        f["mars"][sid] = e(r["pixel"], "measured", "MGS TES night-time thermal inertia map (PDS MGS-M-TES-5-TIMAP-V1.0, Putzig & Mellon 2007)", url["tes_ti_img"],
                           f"Pixel of {r['pixel_km']} km at the site; derived from TES night-time surface temperatures through a thermal model. "
                           f"{'This pixel was filled by interpolation in the map (mask = 0), not observed. ' if r['interpolated'] else ''}"
                           f"Across a 0.5 deg box around the site: median {r['box_median']}, range {r['box_min']} to {r['box_max']}. A map pixel, not a measurement on the ground at the landing point.",
                           scope=f"{r['pixel_km']} km map pixel", box_0_5deg={"median": r["box_median"], "min": r["box_min"], "max": r["box_max"]},
                           interpolated=r["interpolated"])
    factors.append(f)

    # ---------- 2 rock abundance
    mn, mx = diviner_ra_limits() if has("diviner_ra_lbl") else (None, None)
    f = {"id": "rock_abundance", "name": "Rock abundance",
         "what_it_is": "Share of the ground covered by rocks big enough to stay warm at night (Diviner: about 1 m and larger; Viking IRTM: about 15 cm and larger), from night-time thermal infrared.",
         "unit": "fraction of area (0 to 1)", "moon": {}, "mars": {}}
    for cid in moon_ids:
        lat = moon_by_id[cid]["centre"]["lat"]
        f["moon"][cid] = e(None, None, "LRO Diviner Level 3 rock abundance, label dgdr_ra_avg_cyl_128_img.lbl", url["diviner_ra_lbl"],
                           f"Confirmed: the Diviner rock-abundance map covers latitudes {mn:g} to {mx:g} deg only (label MINIMUM/MAXIMUM_LATITUDE). "
                           f"This region's centre is at {lat:.2f} deg, poleward of the map's edge, so Diviner publishes no rock abundance here. No other public lunar polar rock-abundance map was found.",
                           map_edge_deg=mn)
    for sid in mars_ids:
        f["mars"][sid] = e(None, None, "Viking IRTM rock abundance (Christensen 1986), ASU Mars Global Data Sets", url["asu_irtm_rocks"],
                           "Not filled tonight. The global rock-abundance maps were found only as coloured pictures (ASU's WMS PNG and JMARS layer), "
                           "not as a numeric file on PDS or USGS Astrogeology; the TES rock-abundance map (Nowicki & Christensen 2007) was not found as a download. "
                           "Reading numbers back from colours was not done.")
    factors.append(f)

    # ---------- 3 near-surface hydrogen / water
    lp = read_lp_hydrogen(moon_cards) if has("lp_h_halfdeg") else {}
    grs = read_grs_h2o(mars_sites) if has("grs_h2o_tab") else {}
    f = {"id": "hydrogen", "name": "Near-surface hydrogen or water",
         "what_it_is": "Hydrogen in the top tens of centimetres to about a metre, seen from orbit by the neutrons or gamma rays the ground gives off. Moon: hydrogen in ppm by weight. Mars: the same signal expressed as water (H2O) in weight per cent.",
         "unit": "Moon: ppm H by weight; Mars: weight % H2O", "moon": {}, "mars": {}}
    for cid in moon_ids:
        r = lp.get(cid)
        if not r or r["centre_bin"] is None:
            f["moon"][cid] = e(None, None, "Lunar Prospector neutron spectrometer hydrogen, half-degree", url["lp_h_halfdeg"], "file missing")
            continue
        f["moon"][cid] = e(r["centre_bin"], "measured", "Lunar Prospector neutron spectrometer, 'Hydrogen_halfdeg' (Feldman et al. 2001), PDS Geosciences Node", url["lp_h_halfdeg"],
                           f"Half-degree bin holding the region centre; {r['bins_in_region']} bins centred inside the region range {r['region_min']} to {r['region_max']} ppm. "
                           "The instrument's footprint is tens of kilometres, much wider than a half-degree bin near the pole, so this is a regional value, not a measurement at the landing point. "
                           "It cannot tell ice in a cold trap from hydrogen spread through the soil.",
                           scope="regional (orbital neutron footprint of tens of km)", region_range=[r["region_min"], r["region_max"]])
    for sid in mars_ids:
        r = grs.get(sid)
        if not r or r["wt_pct"] is None:
            f["mars"][sid] = e(None, None, "Mars Odyssey GRS H2O, 5x5 deg smoothed", url["grs_h2o_tab"], f"The PDS product leaves this 5 deg bin blank (9999.999, 'not applicable'), as it does the other high-latitude bins checked (62.5 and 67.5 N). "
                               "No value at this site from this map; the Phoenix lander itself dug to ice (see ice_depth).")
            continue
        f["mars"][sid] = e(r["wt_pct"], "measured", "Mars Odyssey Gamma Ray Spectrometer, H2O concentration, 5 x 5 deg smoothed (PDS ODY-M-GRS-5-ELEMENTS-V1.0)", url["grs_h2o_tab"],
                           f"5 x 5 deg bin centred {r['bin_lat']} N, {r['bin_lon_east']} E (about 300 km across), after a 10 deg box-car smoothing; "
                           f"one sigma {r['sigma']} wt %. Senses roughly the top few tens of centimetres. A coarse regional value, not a figure at the site.",
                           scope="5 x 5 deg bin, smoothed over 10 deg", sigma=r["sigma"], bin={"lat": r["bin_lat"], "lon_east": r["bin_lon_east"]})
    factors.append(f)

    # ---------- 4 depth to stable ice (Mars)
    f = {"id": "ice_depth", "name": "Depth to water ice",
         "what_it_is": "How far down buried water ice starts. Mars only here; the Moon's model ice depth is already on the Moon cards.",
         "unit": "m", "moon": {}, "mars": {}}
    for cid in moon_ids:
        f["moon"][cid] = e(None, None, "already held", None,
                           "Not repeated here: the Diviner model depth to stable ice for this region is in data/derived/moon_cards.json -> cards[id].diviner.ice.",
                           held_in=f"data/derived/moon_cards.json#cards[id={cid}].diviner.ice")
    # The Arvidson abstract is a PDF (read by eye on 14 Nov 2026, page 1); the NASA page is checked here.
    if has("nasa_dodo"):
        must_contain(pages["nasa_dodo"], "At its deepest point, the trench is 7 to 8 centimeters")
    f["mars"]["phoenix"] = e([0.03, 0.05], "published figure", "Arvidson et al. 2009, JGR 114, E00E02 (Phoenix Robotic Arm), abstract", url["arvidson2009"],
                             "Measured by digging at the site: the paper's abstract speaks of '3-5 cm deep icy soil interfaces' in the trenches. "
                             "NASA's photojournal for the Dodo-Goldilocks trench (dug 12 June 2008, 7 to 8 cm deep) shows white material, later judged ice, in its upper part.",
                             value_text="3 to 5 cm (dug by the lander's arm)", also=url["nasa_dodo"])
    if has("morgan2021"):
        f["mars"]["arcadia-planitia"] = e(None, "published figure", "SWIM project: Morgan et al. 2021, Nature Astronomy (manuscript on NASA NTRS 20205008958)", url["morgan2021"],
                                          "No single depth is published. The SWIM paper infers ice 'present close to the surface in Arcadia' and maps a radar reflector, read as the base of an ice-bearing layer, "
                                          "at depths of 15 to more than 100 m. SWIM's own map files (swim.psi.edu) did not answer tonight (HTTP 523), so nothing was read at the site's coordinates.",
                                          value_text="close to the surface (published words); ice-bearing layer reaching 15 to >100 m")
        f["mars"]["deuteronilus-mensae"] = e(None, "published figure", "SWIM project: Morgan et al. 2021, Nature Astronomy (manuscript on NASA NTRS 20205008958)", url["morgan2021"],
                                             "No single depth is published. For the glaciers of Deuteronilus Mensae the paper offers two readings: ice under a very thin debris cover of less than 2 m, "
                                             "or under meters of highly porous material. SWIM's map files did not answer tonight (HTTP 523).",
                                             value_text="under less than 2 m of debris, or under metres of porous material (two published readings)")
    f["mars"]["jezero"] = e(None, None, "SWIM project (Morgan et al. 2021)", url["morgan2021"],
                            "No public figure found. Jezero (18.4 N) lies inside the SWIM study area, but SWIM's map files were unreachable tonight; the paper's Fig. 1a puts the theoretical 3 m ice-stability zone far poleward of the site.")
    f["mars"]["gale"] = e(None, None, "SWIM project (Morgan et al. 2021)", url["morgan2021"],
                          "No public figure found. Gale (4.6 S) is south of the SWIM study area (equator to 60 N); no ice-depth map was found for it.")
    for sid in mars_ids:   # the sites added on 15 November 2026
        if sid not in f["mars"]:
            f["mars"][sid] = e(None, None, None, None,
                               "We did not open a published depth to ice at this site for this version of the page. The value is empty, not zero.")
    factors.append(f)

    # ---------- 5 surface activity
    f = {"id": "surface_activity", "name": "Surface activity",
         "what_it_is": "Ground that changes by itself today: moving dunes, slope streaks, frost. Moon: none expected (no wind, no water).",
         "unit": "m per Earth year where a rate is given", "moon": {}, "mars": {}}
    lands = must_contain(pages["nasa_moonquakes"], "some areas are susceptible to regolith landslides from even light seismic shaking") if has("nasa_moonquakes") else None
    for cid in moon_ids:
        note = ("None expected: no wind and no liquid water. New impact craters and rare slope slides are the only known changes. "
                "NASA's 2024 south-pole release says some slopes could slide with light seismic shaking (it names Shackleton's inner walls and Nobile Rim 1).")
        f["moon"][cid] = e(None, None, "NASA release, 25 January 2024 (Watters et al. 2024, Planetary Science Journal)", url["nasa_moonquakes"], note, value_text="none expected")
    if has("apod_namib"):
        must_contain(pages["apod_namib"], "advance about one meter a year")
        f["mars"]["gale"] = e(1.0, "published figure", "NASA Astronomy Picture of the Day, 19 January 2016, Namib Dune (Curiosity)", url["apod_namib"],
                              "The Bagnold Dunes on Mount Sharp's northwestern flank, inside Gale crater, are active: wind pushes Namib Dune forward by about one meter a year. "
                              "This is the dune field near the rover's route, not the landing point itself.",
                              value_text="active dunes, about 1 m per year", scope="Bagnold Dunes, Gale crater")
    for sid in ("jezero", "phoenix", "arcadia-planitia", "deuteronilus-mensae"):
        f["mars"][sid] = e(None, None, None, None,
                           "No published record of dune movement or slope streaks at this site was opened tonight (JPL news pages refused scripted requests, HTTP 403). Left empty, not zero.")
    for sid in mars_ids:   # the sites added on 15 November 2026
        if sid not in f["mars"]:
            f["mars"][sid] = e(None, None, None, None,
                               "We did not open a published record of dune movement or slope streaks at this site for this version of the page. The value is empty, not zero.")
    factors.append(f)

    # ---------- 6 quakes
    f = {"id": "quakes", "name": "Quakes",
         "what_it_is": "Ground shaking from inside the planet. Moon: shallow moonquakes from faults as the Moon cools and shrinks. Mars: marsquakes heard by NASA's InSight lander (2018-2022).",
         "unit": "count or published words", "moon": {}, "mars": {}}
    if has("nasa_moonquakes"):
        must_contain(pages["nasa_moonquakes"], "The strongest recorded shallow moonquake had an epicenter in the south-polar region")
        must_contain(pages["nasa_moonquakes"], "the exact location of the epicenter could not be accurately determined")
        for cid in moon_ids:
            f["moon"][cid] = e(None, "published figure", "NASA release, 25 January 2024 (Watters et al. 2024, Planetary Science Journal)", url["nasa_moonquakes"],
                               "The strongest shallow moonquake recorded by the Apollo seismometers (1969-1977) had its epicentre in the south-polar region, but its exact place could not be fixed; "
                               "the cloud of possible epicentres covers many Artemis III candidate regions. Young thrust-fault scarps lie near and inside some of them. "
                               "No count or rate is published for this region; no seismometer has worked near the south pole.",
                               value_text="strong shallow moonquakes possible in the south-polar region; no local count", scope="south-polar region")
    if has("nasa_insight_end"):
        must_contain(pages["nasa_insight_end"], "detected 1,319 marsquakes")
        for sid in mars_ids:
            if sid == "insight":   # the seismometer itself stood at this site
                f["mars"][sid] = e(None, "published figure", "NASA release on InSight's retirement, 21 December 2022", url["nasa_insight_end"],
                                   "The single seismometer of InSight stood at this site and detected 1,319 marsquakes during its mission. The quakes came from many places on Mars. "
                                   "Thus this is a count for the whole planet from this site, not a count of quakes at this site.",
                                   value_text="1,319 marsquakes heard here by InSight, from the whole planet", planet_count=1319, scope="whole planet, one seismometer at this site")
                continue
            f["mars"][sid] = e(None, "published figure", "NASA release on InSight's retirement, 21 December 2022", url["nasa_insight_end"],
                               "InSight's single seismometer, at Elysium Planitia, detected 1,319 marsquakes in its mission; this is a count for the whole planet as heard from one place, "
                               "not a count at this site. No public catalogue of quake locations near this site was read tonight.",
                               value_text="1,319 marsquakes heard planet-wide by InSight; none located at this site", planet_count=1319, scope="whole planet, one seismometer")
    factors.append(f)

    # ---------- 7 albedo
    alb = read_tes_albedo(mars_sites) if has("tes_albedo") else {}
    f = {"id": "albedo", "name": "Surface brightness (albedo)",
         "what_it_is": "Share of sunlight the ground reflects. Mars: TES broadband Lambert albedo (dark basalt sand about 0.1, bright dust about 0.25 and up).",
         "unit": "fraction (0 to 1)", "moon": {}, "mars": {}}
    for cid in moon_ids:
        f["moon"][cid] = e(None, None, None, None,
                           "Not filled tonight: no lunar albedo file was read, and the Moon cards hold none. (Not repeated from memory.)")
    for sid in mars_ids:
        r = alb.get(sid)
        if not r or r["pixel"] is None:
            f["mars"][sid] = e(None, None, "MGS TES albedo, USGS mosaic", url["tes_albedo"], "no value at this pixel or file missing")
            continue
        f["mars"][sid] = e(r["pixel"], "measured", "MGS TES global albedo mosaic, 8 pixels per degree (Christensen et al. 2001; USGS Astrogeology)", url["tes_albedo"],
                           f"Pixel of {r['pixel_km']} km at the site; median over a 0.5 deg box {r['box_median']}. A map pixel averaged over years of TES orbits; dust storms change it from season to season.",
                           scope=f"{r['pixel_km']} km map pixel", box_0_5deg_median=r["box_median"])
    factors.append(f)

    # ---------- 8 daily temperature swing
    f = {"id": "daily_temperature_swing", "name": "Daily temperature swing",
         "what_it_is": "Warmest minus coldest temperature over one day. Mars: one sol (24.66 h), ground surface and air at 2 m, averaged over the 24 seasons of the year.",
         "unit": "K (same as degrees C of difference)", "moon": {}, "mars": {}}
    for cid in moon_ids:
        f["moon"][cid] = e(None, None, "LRO Diviner polar diurnal temperatures (PCP), PDS",
                           "https://pds-geosciences.wustl.edu/lro/urn-nasa-pds-lro_diviner_derived1/data_derived_pcp/diurnal/ltim/pols/",
                           "Not filled tonight. Diviner publishes south-polar temperatures by local time (96 tables per season, about 210 MB each); reading them was too large for tonight. "
                           "The Moon cards already hold the yearly maximum at the surface and the yearly mean at 2 cm (Diviner PRP model), which are not a daily swing.",
                           held_in="data/derived/moon_cards.json#cards[].diviner")
    for sid in mars_ids:
        got = read_mcd_swing(sid)
        if not got or "ground" not in got[0]:
            f["mars"][sid] = e(None, None, "Mars Climate Database v6.2", "https://www-mars.lmd.jussieu.fr/mcd_python/", "the saved MCD table for this site is missing")
            continue
        sw, path = got
        g, a = sw["ground"], sw.get("air_2m") or {}
        f["mars"][sid] = e(g["mean_K"], "model", "Mars Climate Database v6.2 (LMD/LATMOS/OU/IAA/ESA/CNES), climatology average solar scenario; table saved by the Mars-climate job",
                           "https://www-mars.lmd.jussieu.fr/mcd_python/",
                           f"Ground surface: daily swing {g['smallest_K']} to {g['largest_K']} K over the year, mean {g['mean_K']} K. "
                           f"Air at 2 m: mean {a.get('mean_K')} K, largest {a.get('largest_K')} K. Model values on the MCD grid, hourly steps; not a measurement. "
                           "mars_sites.json holds the warm-season daily maximum and cold-season daily minimum, which come from different seasons and are not a daily swing.",
                           ground=g, air_2m=a, read_from=str(path.relative_to(ROOT)))
    factors.append(f)

    # ---------- summary of what filled
    filled = {}
    for fac in factors:
        for body in ("moon", "mars"):
            vals = fac[body]
            n = sum(1 for v in vals.values() if v.get("value") is not None)
            t = sum(1 for v in vals.values() if v.get("value") is None and v.get("value_text"))
            filled[f"{fac['id']}.{body}"] = {"numbers": n, "published_words_only": t, "empty": len(vals) - n - t, "of": len(vals)}

    out = {
        "meta": {
            "what": f"Figures that exist only on the Moon or Mars, for the {len(moon_ids)} lunar regions (moon_cards.json) and the {len(mars_ids)} Mars sites (mars_sites.json). Nothing already on those cards is repeated; links point to it.",
            "made": datetime.now().astimezone().isoformat(timespec="seconds"),
            "made_by": "agent PLANET-SIDE, scripts/build_planet_factors.py",
            "how_to_rerun": "uv run python scripts/build_planet_factors.py   (add --offline to use saved files only)",
            "kinds": {
                "measured": "read from an orbital map at the site's coordinates; a map pixel or bin, never a measurement on the ground at the landing point (see scope)",
                "model": "a model value (e.g. the Mars Climate Database)",
                "published figure": "a number or sentence copied from a saved NASA page or paper",
                "null": "no figure; the note says why",
            },
            "value_text": "Where a published source gives words or a range instead of one number, value is null or a [low, high] pair and value_text holds the words to show.",
            "unknown_is": "null",
            "raw_folder": "data/raw/planet_factors (every download logged in a _downloads.tsv beside it)",
            "sources_failed_tonight": FAILED,
            "licences_and_credits": LICENCES,
            "not_used": "data/raw/planet_factors/mgc3 (Mars cave catalogue) and the LROC pit pages were fetched by an earlier attempt; pits and caves were dropped by the team lead and are not used.",
            "filled": filled,
            "coordinates": {"moon": "moon_cards.json cards[].centre (lat, lon_east)", "mars": "mars_sites.json sites[] (lat, lon_east, planetocentric)"},
        },
        "factors": factors,
    }
    tmp = OUT.with_name(OUT.name + ".tmp")
    tmp.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    os.replace(tmp, OUT)
    print(f"wrote {OUT.relative_to(ROOT)}")
    for k, v in filled.items():
        print(f"  {k:32s} numbers {v['numbers']}/{v['of']}  words-only {v['published_words_only']}  empty {v['empty']}")


if __name__ == "__main__":
    main()

# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Rock type and permafrost for every place of the search.

Writes data/derived/rock_frozen_cells.json (the Moon part: the areas of data/derived/grazing_cells.json)
and data/derived/mars_rock_frozen.json (the Mars part: the squares of data/derived/mars_cells.json).

Rock type: the Global Lithological Map (GLiM) of Hartmann and Moosdorf (2012), gridded to half a degree
(PANGAEA, doi 10.1594/PANGAEA.788537, CC BY 3.0). Each half-degree box carries ONE class: the main rock of a
box about 55 km across. The map has no class for anorthosite (the Moon's highland rock).
  - Mars squares are the same half-degree boxes (both grids have their edges on multiples of 0.5 degree).
  - A Moon area (about 11 km) gets the class of the half-degree box that holds its centre: coarse.
  - Where that box is sea, lake or 'no data' in the map, the most common rock class of the 8 boxes around it
    is used and the record says box = "neighbour".

Permafrost: the Northern Hemisphere permafrost map of Obu and others (2019), permafrost probability on a
1 km grid, 2000-2016 (PANGAEA, doi 10.1594/PANGAEA.888600, CC BY 3.0). It is a model (ground temperature
driven by satellite land-surface temperature and reanalysis), not a measurement in the ground. It covers
exposed land from 25 N northward; glaciers, ice sheets and water have no value.
  - Moon areas in the north: mean of the 1 km pixels at a ~1 km lattice of points inside the area.
  - Mars squares whose south edge is at or north of 25 N: mean of nine points (a 3 x 3 lattice) in the square.
  - Antarctica: not in our data; the literature says ice-free ground there is permafrost throughout.
The zone (continuous, discontinuous, sporadic, isolated, none) is the zone of the MEAN, using Obu and
others' limits: >= 90 % continuous, 50-90 % discontinuous, 10-50 % sporadic, under 10 % isolated patches.

Run it again (no network needed once the raw files are on disk, a minute or two):

    uv run python scripts/build_rock_frozen.py --offline --report

Without --offline any raw file that is missing is downloaded once (User-Agent twinfinder/0.1) into
data/raw/glim/ and data/raw/permafrost/ and kept. Results are written beside the old file and renamed in.
"""
from __future__ import annotations

import argparse
import datetime
import json
import math
import os
import sys
import zipfile
from collections import Counter
from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import transform as warp_transform
from rasterio.windows import Window

from twinfinder import fetch

MOON_CELLS = Path("data/derived/grazing_cells.json")
MARS_CELLS = Path("data/derived/mars_cells.json")
OUT_MOON = Path("data/derived/rock_frozen_cells.json")
OUT_MARS = Path("data/derived/mars_rock_frozen.json")

RAW_GLIM = Path("data/raw/glim")
GLIM_URL = "https://epic.awi.de/id/eprint/31092/1/hartmann-moosdorf_2012.zip"   # PANGAEA 788537's download
GLIM_ZIP = RAW_GLIM / "glim_0.5deg.zip"
GLIM_ASC = RAW_GLIM / "extracted" / "glim_wgs84_0point5deg.txt.asc"
GLIM_NAMES = RAW_GLIM / "extracted" / "Classnames.txt"

RAW_PF = Path("data/raw/permafrost")
PF_URL = "https://store.pangaea.de/Publications/ObuJ-etal_2018/UiO_PEX_PERPROB_5.0_20181128_2000_2016_NH.zip"
PF_ZIP = RAW_PF / "UiO_PEX_PERPROB_5.0_20181128_2000_2016_NH.zip"
PF_TIF = RAW_PF / "nh" / "UiO_PEX_PERPROB_5.0_20181128_2000_2016_NH.tif"
PF_MEMBERS = ("UiO_PEX_PERPROB_5.0_20181128_2000_2016_NH.tif", "UiO_PEX_PERPROB_5.0_20181128_2000_2016_NH.tif.ovr",
              "UiO_PEX_PERPROB_5.0_20181128_2000_2016_NH.tif.aux.xml", "UiO_PEX_PERPROB_5.0_20181128_2000_2016_NH.tfw",
              "UiO_PEX_PERPROBLegend_5.0_20181128.lyr")
PF_SOUTH_LIMIT = 25.0      # the map's processing extent: land from 25 N northward
BLOCK = 1024               # pixels per side of the windows read from the 1 km raster

# GLiM first-level classes (Classnames.txt: value -> two-letter code), in plain words.
GLIM_CLASSES = {
    1: ("su", "loose sediment (unconsolidated sand, gravel, silt, clay)"),
    2: ("vb", "basic volcanic rock (basalt and the like)"),
    3: ("ss", "siliciclastic sedimentary rock (sandstone, siltstone, shale)"),
    4: ("pb", "basic plutonic rock (gabbro and the like)"),
    5: ("sm", "mixed sedimentary rock"),
    6: ("sc", "carbonate sedimentary rock (limestone, dolomite)"),
    7: ("va", "acid volcanic rock (rhyolite, dacite and the like)"),
    8: ("mt", "metamorphic rock (gneiss, schist and the like)"),
    9: ("pa", "acid plutonic rock (granite and the like)"),
    10: ("vi", "intermediate volcanic rock (andesite and the like)"),
    11: ("wb", "water body"),
    12: ("py", "pyroclastic rock (volcanic ash, tuff)"),
    13: ("pi", "intermediate plutonic rock (diorite and the like)"),
    14: ("ev", "evaporite (rock salt, gypsum)"),
    15: ("nd", "no data in the map"),
    16: ("ig", "ice and glaciers"),
}
VOLCANIC = {"vb", "va", "vi", "py"}
NOT_ROCK = {"wb", "nd", "ig"}        # the rock underneath is unknown: the yes-or-no fields are null
NO_BOX = {"wb", "nd"}                # these boxes fall back to the neighbours (ice does not: ice is the answer)

ANTARCTIC_NOTE = "ice-free ground there is permafrost throughout, by the literature; not in our data"

SOURCES = {
    "glim": {
        "name": "Global Lithological Map Database v1.0 (GLiM), gridded to 0.5 degree",
        "citation": ("Hartmann, Jens; Moosdorf, Nils (2012): Global Lithological Map Database v1.0 (gridded to 0.5 "
                     "deg spatial resolution) [dataset]. PANGAEA, https://doi.org/10.1594/PANGAEA.788537. Supplement "
                     "to: Hartmann, J.; Moosdorf, N. (2012): The new global lithological map database GLiM: A "
                     "representation of rock properties at the Earth surface. Geochemistry, Geophysics, Geosystems "
                     "13, Q12004, https://doi.org/10.1029/2012GC004370"),
        "licence": "Creative Commons Attribution 3.0 Unported (CC BY 3.0)",
        "credit": "Rock type: GLiM, Hartmann & Moosdorf (2012), PANGAEA, CC BY 3.0",
        "landing": "https://doi.org/10.1594/PANGAEA.788537",
        "downloaded_from": GLIM_URL,
        "login": "none needed",
        "raw_files": [str(GLIM_ZIP), str(GLIM_ASC), str(GLIM_NAMES)],
    },
    "permafrost": {
        "name": "Ground Temperature Map, 2000-2016, Northern Hemisphere Permafrost: permafrost probability (PERPROB)",
        "citation": ("Obu, Jaroslav; Westermann, Sebastian; Kaab, Andreas; Bartsch, Annett (2018): Ground Temperature "
                     "Map, 2000-2016, Northern Hemisphere Permafrost [dataset]. Alfred Wegener Institute, Helmholtz "
                     "Centre for Polar and Marine Research, Bremerhaven, PANGAEA, https://doi.org/10.1594/PANGAEA.888600. "
                     "Method: Obu, J. et al. (2019): Northern Hemisphere permafrost map based on TTOP modelling for "
                     "2000-2016 at 1 km2 scale. Earth-Science Reviews 193, 299-316, "
                     "https://doi.org/10.1016/j.earscirev.2019.04.023"),
        "licence": "Creative Commons Attribution 3.0 Unported (CC BY 3.0)",
        "credit": "Permafrost: Obu et al. (2019), ESA GlobPermafrost, PANGAEA, CC BY 3.0",
        "landing": "https://doi.org/10.1594/PANGAEA.888600",
        "downloaded_from": PF_URL,
        "login": "none needed",
        "file_taken": "PERPROB only (zip 103,591 kB on the PANGAEA list; the GeoTIFF inside is 1.9 GB, float32, "
                      "22425 x 21141 pixels of 926.6 m, EPSG:3995). MAGTM (369,567 kB) and MAGTSTD (345,148 kB) not taken.",
        "raw_files": [str(PF_ZIP), str(PF_TIF)],
    },
}


# ---------------------------------------------------------------- raw files

def _fetch_to(url: str, dest: Path) -> None:
    """Download url to dest once (retries inside twinfinder.fetch); a file on disk is never asked for again."""
    if dest.exists():
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(dest.suffix + ".part")
    print(f"downloading {url}", file=sys.stderr)
    fetch._download(url, part)
    part.rename(dest)


def _extract(zip_path: Path, members: tuple[str, ...], out_dir: Path) -> None:
    """Extract the named members only, by bare file name (an archive path is never trusted)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as archive:
        by_name = {Path(info.filename).name: info for info in archive.infolist() if not info.is_dir()}
        for name in members:
            target = out_dir / name
            if target.exists() or name not in by_name:
                continue
            part = target.with_suffix(target.suffix + ".part")
            with archive.open(by_name[name]) as src, open(part, "wb") as dst:
                while chunk := src.read(1 << 22):
                    dst.write(chunk)
            part.rename(target)


def ensure_raw(offline: bool) -> None:
    if not GLIM_ASC.exists():
        if not GLIM_ZIP.exists():
            if offline:
                sys.exit(f"missing {GLIM_ZIP}; run without --offline once")
            _fetch_to(GLIM_URL, GLIM_ZIP)
        _extract(GLIM_ZIP, (GLIM_ASC.name, GLIM_NAMES.name), GLIM_ASC.parent)
    if not PF_TIF.exists():
        if not PF_ZIP.exists():
            if offline:
                sys.exit(f"missing {PF_ZIP}; run without --offline once")
            _fetch_to(PF_URL, PF_ZIP)
        _extract(PF_ZIP, PF_MEMBERS, PF_TIF.parent)


# ---------------------------------------------------------------- rock type

class Glim:
    def __init__(self) -> None:
        with rasterio.open(GLIM_ASC) as src:
            t = src.transform
            if (src.width, src.height) != (720, 360) or not (
                    math.isclose(t.a, 0.5) and math.isclose(t.e, -0.5) and math.isclose(t.c, -180.0)
                    and math.isclose(t.f, 90.0)):
                sys.exit(f"GLiM grid is not the expected global half-degree grid: {src.width}x{src.height} {t}")
            self.grid = src.read(1).astype(np.int32)
            nodata = src.nodata
        if nodata is not None:
            self.grid[self.grid == int(nodata)] = -1
        # The legend in the archive must match the codes this script names.
        legend = {}
        for line in GLIM_NAMES.read_text().splitlines()[1:]:
            parts = [p.strip().strip('"') for p in line.split(";")]
            if len(parts) >= 4 and parts[1].isdigit():
                legend[int(parts[1])] = parts[3]
        if {k: v[0] for k, v in GLIM_CLASSES.items()} != legend:
            sys.exit(f"GLiM legend differs from the one this script knows: {legend}")

    @staticmethod
    def box_of(lat: float, lon: float) -> tuple[int, int]:
        row = min(359, max(0, int(math.floor((90.0 - lat) / 0.5))))
        col = int(math.floor((lon + 180.0) / 0.5)) % 720
        return row, col

    def _code(self, row: int, col: int) -> str | None:
        v = int(self.grid[row, col % 720])
        return GLIM_CLASSES[v][0] if v in GLIM_CLASSES else None

    def rock(self, lat: float, lon: float, coarse: bool) -> dict:
        row, col = self.box_of(lat, lon)
        box_sw = (90.0 - 0.5 * (row + 1), -180.0 + 0.5 * col)
        code = self._code(row, col)
        used = "own"
        if code is None or code in NO_BOX:
            around = Counter()
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if (dr or dc) and 0 <= row + dr < 360:
                        c = self._code(row + dr, col + dc)
                        if c is not None and c not in NO_BOX:
                            around[c] += 1
            if around:
                # most common; ties broken by the class order of the legend, so a rerun gives the same answer
                order = {v[0]: k for k, v in GLIM_CLASSES.items()}
                code = sorted(around.items(), key=lambda kv: (-kv[1], order[kv[0]]))[0][0]
                used = "neighbour"
            else:
                used = "own"
        if code is None:
            return {"class_code": None, "class": None, "volcanic": None, "basic_volcanic": None,
                    "loose_sediment": None, "box": None, "box_sw": [box_sw[0], box_sw[1]], "coarse": coarse,
                    "note": "the half-degree box and the eight around it are sea or no data in the map"}
        name = next(v[1] for v in GLIM_CLASSES.values() if v[0] == code)
        rock_known = code not in NOT_ROCK
        out = {
            "class_code": code,
            "class": name,
            "volcanic": (code in VOLCANIC) if rock_known else None,
            "basic_volcanic": (code == "vb") if rock_known else None,
            "loose_sediment": (code == "su") if rock_known else None,
            "box": used,
            "box_sw": [box_sw[0], box_sw[1]],
            "coarse": coarse,
        }
        if code == "ig":
            out["note"] = "the map's main cover of the box is ice; the rock of any bare ground there is not given"
        elif code == "wb" or code == "nd":
            out["note"] = "the box and its neighbours give no rock class"
        return out


# ---------------------------------------------------------------- permafrost

def zone_of(p: float | None) -> str | None:
    if p is None:
        return None
    if p >= 0.9:
        return "continuous"
    if p >= 0.5:
        return "discontinuous"
    if p >= 0.1:
        return "sporadic"
    if p > 0.0:
        return "isolated patches"
    return "none"


def sample_probability(lats: np.ndarray, lons: np.ndarray) -> np.ndarray:
    """Permafrost probability (0-1) of the 1 km pixel under each point; NaN where the map has no value."""
    out = np.full(lats.shape, np.nan, dtype=np.float64)
    with rasterio.open(PF_TIF) as src:
        xs, ys = warp_transform("EPSG:4326", src.crs, lons.tolist(), lats.tolist())
        cols_f, rows_f = ~src.transform * (np.asarray(xs), np.asarray(ys))
        rows = np.floor(rows_f).astype(np.int64)
        cols = np.floor(cols_f).astype(np.int64)
        inside = (rows >= 0) & (rows < src.height) & (cols >= 0) & (cols < src.width)
        idx = np.nonzero(inside)[0]
        block_id = (rows[idx] // BLOCK) * 100000 + (cols[idx] // BLOCK)
        order = np.argsort(block_id, kind="stable")
        idx, block_id = idx[order], block_id[order]
        starts = np.r_[0, np.nonzero(np.diff(block_id))[0] + 1, len(idx)]
        for a, b in zip(starts[:-1], starts[1:]):
            sel = idx[a:b]
            r0 = int(rows[sel[0]] // BLOCK) * BLOCK
            c0 = int(cols[sel[0]] // BLOCK) * BLOCK
            h = min(BLOCK, src.height - r0)
            w = min(BLOCK, src.width - c0)
            block = src.read(1, window=Window(c0, r0, w, h))
            out[sel] = block[rows[sel] - r0, cols[sel] - c0]
    bad = ~np.isfinite(out) | (out < 0.0) | (out > 1.0)
    out[bad] = np.nan
    return out


def summarise(values: np.ndarray, group: np.ndarray, n_groups: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    ok = np.isfinite(values)
    n_all = np.bincount(group, minlength=n_groups)
    n_ok = np.bincount(group[ok], minlength=n_groups)
    s = np.bincount(group[ok], weights=values[ok], minlength=n_groups)
    n_half = np.bincount(group[ok], weights=(values[ok] >= 0.5).astype(float), minlength=n_groups)
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = np.where(n_ok > 0, s / np.maximum(n_ok, 1), np.nan)
        half = np.where(n_ok > 0, n_half / np.maximum(n_ok, 1), np.nan)
    return n_all, n_ok, mean, half


def pf_record(n_all: int, n_ok: int, mean: float, half: float | None) -> dict:
    if n_ok == 0:
        return {"prob_mean": None, "zone": None, "points": int(n_all), "points_with_value": 0,
                "share_points_ge_half": None,
                "note": ("no map value at any sample point: sea, lake, glacier or ice sheet, or a gap of the map "
                         "(it leaves most of the Sahara and much of Arabia between 25 and 30 N empty)")}
    rec = {"prob_mean": round(float(mean), 3), "zone": zone_of(float(mean)), "points": int(n_all),
           "points_with_value": int(n_ok)}
    if half is not None:
        rec["share_points_ge_half"] = round(float(half), 3)
    return rec


# ---------------------------------------------------------------- places

def moon_area_points(cell: dict) -> tuple[np.ndarray, np.ndarray]:
    """A lattice of points about 1 km apart filling the area (id = SW corner, 0.1 degree tall)."""
    lat0_s, lon0_s = cell["id"].split("_")
    lat0, lon0 = float(lat0_s), float(lon0_s)
    height = 0.1
    width = 2.0 * (cell["lon"] - lon0)
    n_lat = max(2, round(height * 111.2))
    n_lon = max(2, round(width * 111.32 * math.cos(math.radians(cell["lat"]))))
    la = lat0 + (np.arange(n_lat) + 0.5) * height / n_lat
    lo = lon0 + (np.arange(n_lon) + 0.5) * width / n_lon
    g_la, g_lo = np.meshgrid(la, lo, indexing="ij")
    g_lo = (g_lo + 180.0) % 360.0 - 180.0
    return g_la.ravel(), g_lo.ravel()


def mars_square_points(lat: float, lon: float) -> tuple[np.ndarray, np.ndarray]:
    off = np.array([-1.0, 0.0, 1.0]) * (0.5 / 3.0)
    g_la, g_lo = np.meshgrid(lat + off, lon + off, indexing="ij")
    return g_la.ravel(), ((g_lo.ravel() + 180.0) % 360.0 - 180.0)


def permafrost_for(places: list[tuple[str, np.ndarray, np.ndarray]]) -> dict[str, dict]:
    if not places:
        return {}
    lats = np.concatenate([p[1] for p in places])
    lons = np.concatenate([p[2] for p in places])
    group = np.concatenate([np.full(len(p[1]), i, dtype=np.int64) for i, p in enumerate(places)])
    values = sample_probability(lats, lons)
    n_all, n_ok, mean, half = summarise(values, group, len(places))
    return {p[0]: pf_record(int(n_all[i]), int(n_ok[i]), mean[i], None if np.isnan(half[i]) else half[i])
            for i, p in enumerate(places)}


def antarctic(lat: float) -> bool:
    return lat <= -60.0


def outside_record(lat: float) -> dict:
    if antarctic(lat):
        return {"prob_mean": None, "zone": None, "note": ANTARCTIC_NOTE}
    if lat < 0:
        return {"prob_mean": None, "zone": None,
                "note": "southern hemisphere outside Antarctica: not in our data (the map covers the north only); "
                        "mountain permafrost can exist there at high altitude"}
    return {"prob_mean": None, "zone": None,
            "note": "south of 25 N: outside the map, which covers land from 25 N northward"}


# ---------------------------------------------------------------- meta

def what_is() -> tuple[dict, dict]:
    is_ = {
        "rock.class": ("The main rock class (GLiM first level, 16 classes) of a half-degree box, about 55 km north-south, "
                       "in plain words. It is the class a geological map compilation gives most of that box."),
        "rock.volcanic": "yes when the class is basic, intermediate or acid volcanic rock, or pyroclastic rock",
        "rock.basic_volcanic": "yes when the class is basic volcanic rock (basalt and the like)",
        "rock.loose_sediment": "yes when the class is unconsolidated sediment (loose sand, gravel, silt, clay)",
        "rock.box": "'own' = the box that holds the place; 'neighbour' = that box is sea or no data, so the most common "
                    "rock class of the 8 boxes around it is given",
        "rock.box_sw": "south-west corner (lat, lon, degrees) of the half-degree box the class belongs to",
        "permafrost.prob_mean": ("Mean modelled permafrost probability (fraction 0-1) of the 1 km pixels under the sample "
                                 "points that have a map value. Obu et al. model mean annual ground temperature at the top "
                                 "of the permafrost for 2000-2016; the probability is the share of their model runs with "
                                 "it below 0 C."),
        "permafrost.zone": ("Zone of the MEAN, by Obu et al.'s limits: continuous >= 0.9, discontinuous 0.5-0.9, sporadic "
                            "0.1-0.5, isolated patches above 0 and under 0.1, none = 0."),
        "permafrost.points / points_with_value": ("sample points in the place / those on a pixel with a value; the rest "
                                                  "fall on sea, lakes, glaciers or ice sheets, which the map leaves empty, "
                                                  "or in its gaps (most of the Sahara and much of Arabia between 25 and "
                                                  "30 N have no value although they are land)"),
        "permafrost.share_points_ge_half": "share of the points with a value whose probability is 0.5 or more",
    }
    is_not = {
        "rock": ("Not the rock at the place. One class per 55 km box; small outcrops, a single hill or the ground of an "
                 "11 km area can be another rock. There is NO class for anorthosite (the bright rock of the Moon's "
                 "highlands and of the south-pole landing regions): anorthosite bodies on Earth are inside the plutonic "
                 "or metamorphic classes. 'Basic volcanic' is the closest the map comes to the Moon's mare basalts, "
                 "which are not at the candidate regions. 'Ice and glaciers' means the map does not say what rock lies "
                 "under or between the ice; the three yes-or-no fields are then null, not no."),
        "permafrost": ("Not a measurement in the ground: a 1 km model, validated against boreholes with an error of about "
                       "2 C in ground temperature. Not the depth of thaw in summer (the active layer) and not ice content. "
                       "The zone is the zone of the area's mean, not of every pixel; an 'isolated patches' area can hold "
                       "no permafrost at all on the ground. Glaciers, ice sheets and water have no value; a place mostly "
                       "under ice gets few points or none."),
        "mars_permafrost": "nine points in a 55 km square: a thin sample of nine 1 km pixels, not an area mean",
        "antarctica": ("Not in our data. The Obu et al. Northern Hemisphere map covers land from 25 N northward only "
                       "and does not cover Antarctica; the literature says ice-free ground in Antarctica is permafrost "
                       "throughout. The fields are null with that note."),
    }
    return is_, is_not


def write_json(path: Path, obj: dict) -> None:
    side = path.with_suffix(path.suffix + ".tmp")
    with open(side, "w") as f:
        json.dump(obj, f, separators=(",", ":"), allow_nan=False)
    os.replace(side, path)


# ---------------------------------------------------------------- main

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--offline", action="store_true", help="never download; stop if a raw file is missing")
    ap.add_argument("--report", action="store_true", help="print the sanity look at known places")
    args = ap.parse_args()

    ensure_raw(args.offline)
    glim = Glim()
    now = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    is_, is_not = what_is()

    # ---- Moon part
    moon = json.loads(MOON_CELLS.read_text())["cells"]
    moon_pts = [(c["id"], *moon_area_points(c)) for c in moon if c["lat"] > 0]
    moon_pf = permafrost_for(moon_pts)
    moon_out = {}
    for c in moon:
        pf = moon_pf.get(c["id"]) or outside_record(c["lat"])
        moon_out[c["id"]] = {"rock": glim.rock(c["lat"], c["lon"], coarse=True), "permafrost": pf}

    # ---- Mars part
    mars = json.loads(MARS_CELLS.read_text())["cells"]
    misaligned = [k for k, c in mars.items()
                  if not (math.isclose((c["lat"] - 0.25) % 0.5, 0.0, abs_tol=1e-9)
                          and math.isclose((c["lon"] - 0.25) % 0.5, 0.0, abs_tol=1e-9))]
    if misaligned:
        sys.exit(f"{len(misaligned)} Mars squares are not on the half-degree grid, e.g. {misaligned[:3]}")
    mars_pts = [(k, *mars_square_points(c["lat"], c["lon"])) for k, c in mars.items()
                if c["lat"] - 0.25 >= PF_SOUTH_LIMIT]
    mars_pf = permafrost_for(mars_pts)
    mars_out = {}
    for k, c in mars.items():
        pf = mars_pf.get(k) or outside_record(c["lat"])
        mars_out[k] = {"rock": glim.rock(c["lat"], c["lon"], coarse=False), "permafrost": pf}

    def counts(out: dict) -> dict:
        rk = Counter(v["rock"]["class_code"] for v in out.values())
        zn = Counter(v["permafrost"]["zone"] if v["permafrost"]["zone"] else
                     ("no value" if "points" in v["permafrost"] else "outside the map") for v in out.values())
        return {
            "places": len(out),
            "rock_classes": dict(rk.most_common()),
            "volcanic_yes": sum(1 for v in out.values() if v["rock"]["volcanic"] is True),
            "basic_volcanic_yes": sum(1 for v in out.values() if v["rock"]["basic_volcanic"] is True),
            "loose_sediment_yes": sum(1 for v in out.values() if v["rock"]["loose_sediment"] is True),
            "rock_from_neighbour_box": sum(1 for v in out.values() if v["rock"]["box"] == "neighbour"),
            "rock_unknown": sum(1 for v in out.values() if v["rock"]["volcanic"] is None),
            "permafrost_zones": dict(zn.most_common()),
            "antarctic_note": sum(1 for v in out.values() if v["permafrost"].get("note") == ANTARCTIC_NOTE),
        }

    common_meta = {
        "written": now,
        "made_by": "agent ROCK-AND-FROZEN-GROUND, scripts/build_rock_frozen.py",
        "what_this_is": ("For every place: the main rock class of the half-degree box around it (GLiM) and the modelled "
                         "permafrost probability and zone (Obu et al. 2019, north of 25 N only). Context beside the light "
                         "ranking, not part of it."),
        "what_it_is": is_,
        "what_it_is_not": is_not,
        "sources": SOURCES,
        "credit_line": SOURCES["glim"]["credit"] + "; " + SOURCES["permafrost"]["credit"],
        "rock_classes": {v[0]: v[1] for v in GLIM_CLASSES.values()},
        "volcanic_codes": sorted(VOLCANIC),
        "permafrost_zone_limits": {"continuous": ">= 0.9", "discontinuous": "0.5 to < 0.9", "sporadic": "0.1 to < 0.5",
                                   "isolated patches": "> 0 to < 0.1", "none": "0"},
        "unknown_is": "null, never 0",
    }
    moon_meta = dict(common_meta, part="moon", places_from=str(MOON_CELLS),
                     rock_grid=("each Moon area (about 11 km) gets the class of the half-degree GLiM box holding its "
                                "centre: coarse (flag rock.coarse = true); a box is about 55 km north-south"),
                     permafrost_sampling=("northern areas: a lattice of points about 1 km apart filling the area (id = "
                                          "south-west corner, 0.1 degree tall), each read from the 1 km pixel under it; "
                                          "southern areas are all in Antarctica (south of 60 S): note only"),
                     counts=counts(moon_out))
    mars_meta = dict(common_meta, part="mars", places_from=str(MARS_CELLS),
                     rock_grid=(f"the Mars squares and the GLiM boxes are the same half-degree boxes: both have their "
                                f"edges on multiples of 0.5 degree (checked for all {len(mars)} squares; GLiM origin "
                                f"-180, 90, cell 0.5 degree); rock.coarse = false, but the class is still the main rock "
                                f"of the whole 55 km square"),
                     permafrost_sampling=("squares whose south edge is at or north of 25 N: nine points, a 3 x 3 lattice "
                                          "at the square's centre and 1/6 degree (about 18 km) from it, each read from "
                                          "the 1 km pixel under it"),
                     counts=counts(mars_out))
    write_json(OUT_MOON, {"meta": moon_meta, "cells": moon_out})
    write_json(OUT_MARS, {"meta": mars_meta, "cells": mars_out})
    print(f"wrote {OUT_MOON} ({len(moon_out)} areas) and {OUT_MARS} ({len(mars_out)} squares)", file=sys.stderr)

    if args.report:
        report(moon, moon_out, mars, mars_out, moon_meta, mars_meta)


def report(moon, moon_out, mars, mars_out, moon_meta, mars_meta) -> None:
    places = [
        ("Haughton crater, Devon Island", 75.38, -89.68),
        ("south-west Iceland (Reykjanes)", 63.90, -22.30),
        ("south-west Iceland (Hengill)", 64.05, -21.30),
        ("Pechora Sea coast (Varandey)", 68.80, 58.00),
        ("Longyearbyen, Svalbard", 78.22, 15.65),
        ("Atacama near Yungay", -24.10, -70.02),
        ("Tibetan Plateau (Changtang)", 34.0, 88.0),
        ("Qaidam Basin", 37.5, 93.5),
    ]
    lat_m = np.array([c["lat"] for c in moon])
    lon_m = np.array([c["lon"] for c in moon])
    for name, la, lo in places:
        print(f"\n== {name} ({la}, {lo})")
        d = np.hypot(lat_m - la, (lon_m - lo) * math.cos(math.radians(la))) * 111.2
        i = int(np.argmin(d))
        if d[i] < 30:
            r = moon_out[moon[i]["id"]]
            print(f"  Moon area {moon[i]['id']} ({d[i]:.0f} km): rock {r['rock']['class']} [{r['rock']['box']}] "
                  f"volc={r['rock']['volcanic']} basalt={r['rock']['basic_volcanic']} loose={r['rock']['loose_sediment']}; "
                  f"permafrost {r['permafrost']}")
        else:
            print(f"  no Moon area within 30 km (nearest {d[i]:.0f} km)")
        key = f"m_{math.floor(la / 0.5) * 0.5 + 0.25:.2f}_{math.floor(lo / 0.5) * 0.5 + 0.25:.2f}"
        if key in mars_out:
            r = mars_out[key]
            print(f"  Mars square {key}: rock {r['rock']['class']} [{r['rock']['box']}] volc={r['rock']['volcanic']} "
                  f"basalt={r['rock']['basic_volcanic']} loose={r['rock']['loose_sediment']}; permafrost {r['permafrost']}")
        else:
            row, col = Glim.box_of(la, lo)
            print(f"  {key} is not a ranked Mars square")
    for label, meta in (("MOON", moon_meta), ("MARS", mars_meta)):
        print(f"\n{label} counts: {json.dumps(meta['counts'])}")
    by_group = Counter()
    for k, c in mars.items():
        r = mars_out[k]["rock"]
        by_group[(c["region_group"], "volcanic" if r["volcanic"] else ("basalt" if r["basic_volcanic"] else "-"))] += 1
    print("Mars squares by region group, volcanic:", {g: (by_group[(g, 'volcanic')], sum(v for (gg, _), v in by_group.items() if gg == g))
                                                     for g in sorted({c['region_group'] for c in mars.values()})})


if __name__ == "__main__":
    main()

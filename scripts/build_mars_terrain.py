"""Landscape slopes of the Mars sites and of every half-degree Earth square with land. Writes data/derived/mars_terrain.json.

Plan: docs/superpowers/plans/2026-11-14-mars-part.md. Both planets are read at a pixel of about 1.85 km
from north to south and worked out with the same functions (twinfinder/mars_terrain.py):

  Mars   MOLA MEGDR topography at 32 pixels per degree (data/raw/mola/megt90n000fb.img, layout from its
         PDS3 label); each site of data/derived/mars_sites_base.json is the 2 x 2 degree box centred on it.
  Earth  ETOPO 2022 surface elevation at 60 arc-seconds (data/raw/etopo/ETOPO_2022_v1_60s_N90W180_surface.tif),
         land from the Natural Earth 1:50m land outline (data/raw/naturalearth/ne_50m_land.geojson)
         rasterised onto the same grid (a pixel is land when its centre lies inside the outline).
         Squares of 0.5 x 0.5 degree from 85 S to 84 N, worked through in bands of 5 degrees of latitude;
         a square is written when at least 20 percent of its pixels are land.

    uv run python scripts/build_mars_terrain.py

Asks no server for anything. The file is written beside the old one and renamed into place.
"""
import hashlib
import json
import math
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import rasterio
from rasterio.features import rasterize
from rasterio.transform import from_origin
from rasterio.windows import Window

from twinfinder import mars_terrain as mt

MOLA_IMG = Path("data/raw/mola/megt90n000fb.img")
MOLA_LBL = Path("data/raw/mola/megt90n000fb.lbl")
ETOPO = Path("data/raw/etopo/ETOPO_2022_v1_60s_N90W180_surface.tif")
LAND = Path("data/raw/naturalearth/ne_50m_land.geojson")
SITES = Path("data/derived/mars_sites_base.json")
OUT = Path("data/derived/mars_terrain.json")

SOUTH, NORTH = -85.0, 84.0      # the plan's Earth grid
BAND_SQUARES = 10               # square rows per band: 5 degrees, 302 x 21600 pixels read at a time
PX = 30                         # ETOPO pixels per half-degree square side
WIDTH = 21600                   # ETOPO pixels around the Earth


def band_plan(south: float = SOUTH, north: float = NORTH, per_band: int = BAND_SQUARES) -> list[tuple[float, int]]:
    """(northern edge, number of square rows) of each band, from north to south."""
    total = int(round((north - south) / mt.SQUARE_DEG))
    bands, done = [], 0
    while done < total:
        n = min(per_band, total - done)
        bands.append((north - done * mt.SQUARE_DEG, n))
        done += n
    return bands


def window_rows(top_lat: float, n_rows: int, px: int = PX, pixel_deg: float = mt.EARTH_PIXEL_DEG,
                map_top: float = 90.0) -> tuple[int, int]:
    """First and one-past-last map row of a band, with one rim row above and one below."""
    first = int(round((map_top - top_lat) / pixel_deg))
    return first - 1, first + n_rows * px + 1


def land_mask(shapes: list, row_start: int, rows: int, width: int = WIDTH, pixel_deg: float = mt.EARTH_PIXEL_DEG,
              west_lon: float = -180.0, top_lat: float = 90.0) -> np.ndarray:
    """Land pixels of map rows row_start .. row_start + rows: those whose centre lies inside an outline."""
    transform = from_origin(west_lon, top_lat - row_start * pixel_deg, pixel_deg, pixel_deg)
    burned = rasterize(((g, 1) for g in shapes), out_shape=(rows, width), transform=transform,
                       fill=0, dtype="uint8", all_touched=False)
    return burned.astype(bool)


def coast_counts(z: np.ndarray, land: np.ndarray) -> dict:
    """Land pixels of a band (rim rows left out) and those that touch water, so have no slope.

    Counts too how many of them lie below sea level in ETOPO: near the shore these are mostly sea
    floor inside the generalised land outline."""
    lw = np.concatenate([land[:, -1:], land, land[:, :1]], axis=1)
    inner = lw[1:-1, 1:-1]
    touching = inner & ~(lw[:-2, 1:-1] & lw[2:, 1:-1] & lw[1:-1, :-2] & lw[1:-1, 2:])
    zi = z[1:-1]
    return {
        "land_pixels": int(inner.sum()),
        "land_pixels_touching_water": int(touching.sum()),
        "of_them_below_0_m": int((touching & (zi < 0)).sum()),
        "of_them_below_minus_50_m": int((touching & (zi < -50)).sum()),
        "land_pixels_below_0_m": int((inner & (zi < 0)).sum()),
    }


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, value) -> None:
    side = path.with_name(path.name + ".part")
    side.write_text(json.dumps(value, separators=(",", ":"), allow_nan=False))
    os.replace(side, path)


def mars_sites() -> tuple[dict, dict]:
    z, info = mt.read_megdr(MOLA_IMG, MOLA_LBL)
    if (info["ppd"], info["top_lat"], info["west_lon"], info["unit"]) != (32.0, 90.0, 0.0, "METER"):
        raise SystemExit(f"MOLA layout is not the expected one: {info}")
    sites = json.loads(SITES.read_text())["sites"]
    out, boxes = {}, {}
    for site in sites:
        rec = mt.site_record(z, site["lat"], site["lon_east"], ppd=info["ppd"], radius_m=mt.MARS_RADIUS_M)
        out[site["id"]] = mt.rounded(rec)
        box, lats, lons = mt.site_box(z, site["lat"], site["lon_east"], ppd=info["ppd"])
        boxes[site["id"]] = {
            "lat_from": round(float(lats[-2] - 0.5 / info["ppd"]), 5),
            "lat_to": round(float(lats[1] + 0.5 / info["ppd"]), 5),
            "lon_east_from": round(float(np.mod(lons[1] - 0.5 / info["ppd"], 360)), 5),
            "lon_east_to": round(float(np.mod(lons[-2] + 0.5 / info["ppd"], 360)), 5),
            "pixels_per_side": int(box.shape[0] - 2),
            "elev_mean_m": round(float(box[1:-1, 1:-1].mean()), 1),
            "east_west_pixel_km": round(mt.MARS_RADIUS_M * math.radians(1 / info["ppd"])
                                        * math.cos(math.radians(site["lat"])) / 1000, 3),
        }
        print(f"  {site['id']:22s} median {rec['median_slope_deg']:.3f} deg, p90 {rec['p90_slope_deg']:.3f} deg, "
              f"relief {rec['relief_m']:.0f} m, self-overlap {rec['self_overlap']:.3f}", flush=True)
    return out, {"info": info, "boxes": boxes}


def earth_squares() -> tuple[dict, dict]:
    shapes = [f["geometry"] for f in json.loads(LAND.read_text())["features"]]
    cells: dict = {}
    coast: dict = {}
    counts = {"squares_in_grid": 0, "squares_with_any_land": 0, "squares_written": 0,
              "squares_written_without_any_slope": 0, "land_pixels_without_etopo_height": 0}
    with rasterio.open(ETOPO) as src:
        t = src.transform
        expected = (mt.EARTH_PIXEL_DEG, -mt.EARTH_PIXEL_DEG, -180.0, 90.0)
        if (src.width, src.height) != (WIDTH, WIDTH // 2) or not np.allclose((t.a, t.e, t.c, t.f), expected):
            raise SystemExit(f"ETOPO grid is not the expected one: {src.width} x {src.height}, {t}")
        nodata = src.nodata
        for top, n in band_plan():
            t0 = time.time()
            start, stop = window_rows(top, n)
            z = src.read(1, window=Window(0, start, WIDTH, stop - start)).astype(float)
            land = land_mask(shapes, start, stop - start)
            missing = land & ((z == nodata) | ~np.isfinite(z))
            counts["land_pixels_without_etopo_height"] += int(missing[1:-1].sum())
            z[(z == nodata) | ~np.isfinite(z)] = np.nan
            land &= np.isfinite(z)
            for key, value in coast_counts(z, land).items():
                coast[key] = coast.get(key, 0) + value
            band = mt.band_squares(z, land, top_lat=top, pixel_deg=mt.EARTH_PIXEL_DEG, px=PX,
                                   radius_m=mt.EARTH_RADIUS_M, west_lon=-180.0)
            any_land = land[1:-1].reshape(n, PX, WIDTH // PX, PX).any(axis=(1, 3)).sum()
            counts["squares_in_grid"] += n * (WIDTH // PX)
            counts["squares_with_any_land"] += int(any_land)
            for cid, rec in band.items():
                cells[cid] = mt.rounded(rec)
                counts["squares_written"] += 1
                counts["squares_written_without_any_slope"] += rec["pixels"] == 0
            print(f"  band {top:+6.1f} to {top - n * 0.5:+6.1f}: {len(band):5d} squares kept, "
                  f"{time.time() - t0:.1f} s", flush=True)
    counts["squares_written_without_any_slope"] = int(counts["squares_written_without_any_slope"])
    counts["squares_written_with_some_water"] = sum(1 for c in cells.values() if c["land_share"] < 1)
    counts["pixels_85S_to_84N"] = coast
    return cells, counts


def main() -> int:
    t0 = time.time()
    for p in (MOLA_IMG, MOLA_LBL, ETOPO, LAND, SITES):
        if not p.exists():
            raise SystemExit(f"missing input {p}")
    print("Mars sites", flush=True)
    sites, mars = mars_sites()
    print("Earth squares", flush=True)
    cells, counts = earth_squares()
    meta = {
        "what": "Landscape slopes of the Mars sites and of every half-degree Earth square with at least 20 percent "
                "land, worked out the same way on both planets over a baseline of about 1.85 km (plan "
                "docs/superpowers/plans/2026-11-14-mars-part.md). A first pass: coarse, and blind to anything "
                "smaller than a few kilometres.",
        "made": datetime.now().astimezone().isoformat(timespec="seconds"),
        "made_by": "agent MARS-TERRAIN, scripts/build_mars_terrain.py (functions in twinfinder/mars_terrain.py)",
        "inputs": {
            str(MOLA_IMG): {"sha256": sha256(MOLA_IMG), "what": "MGS MOLA MEGDR median topography, 32 pixels per "
                            "degree, PDS Geosciences Node", "url": "https://pds-geosciences.wustl.edu/mgs/"
                            "urn-nasa-pds-mgs_mola_topography_derived/meg032/megt90n000fb.img"},
            str(MOLA_LBL): {"what": "its PDS3 label (layout, units)", "url": "https://pds-geosciences.wustl.edu/mgs/"
                            "urn-nasa-pds-mgs_mola_topography_derived/meg032/megt90n000fb.lbl"},
            str(ETOPO): {"sha256": sha256(ETOPO), "what": "NOAA NCEI ETOPO 2022 v1, 60 arc-second surface elevation "
                         "(ice surface on ice sheets), metres above the EGM2008 geoid",
                         "url": "https://www.ngdc.noaa.gov/mgg/global/relief/ETOPO2022/data/60s/60s_surface_elev_gtif/"
                                "ETOPO_2022_v1_60s_N90W180_surface.tif"},
            str(LAND): {"what": "Natural Earth 1:50m land outline (already in the project)"},
            str(SITES): {"what": "the Mars sites (agent MARS-SITES)"},
        },
        "definitions": {
            "slope": "arctan of the gradient from central differences over a pixel's four neighbours (a two-pixel "
                     "baseline), with metric spacing on a sphere: north-south spacing R x pixel, east-west spacing "
                     "that times cos(latitude). Mars R = 3,396.19 km, pixel 1/32 degree = 1.852 km; Earth R = "
                     "6,371.0088 km (mean radius), pixel 1/60 degree = 1.853 km.",
            "slope_hist": "share of the pixels with a slope in each bin of SLOPE_EDGES_DEG (a slope on an edge goes in "
                          "the bin above; 14 bins; sums to 1 before rounding)",
            "slope_edges_deg": mt.SLOPE_EDGES_DEG,
            "median_slope_deg / p90_slope_deg": "median and 90th percentile of the pixel slopes",
            "relief_m": "95th minus 5th percentile of the pixel heights (as in the Moon part); on Earth land pixels only",
            "elev_mean_m": "mean height of the land pixels, metres above the EGM2008 geoid",
            "land_share": "share of the square's 900 pixels whose centre lies inside the Natural Earth land outline",
            "pixels": "pixels with a slope: on Earth, land pixels whose four neighbours are land as well",
            "site box": "the 2 x 2 degree box centred on the site: the 64 x 64 MOLA pixels whose centres lie in "
                        "[lat - 1, lat + 1) and [lon - 1, lon + 1); slopes at its edge use the pixels just outside",
            "self_overlap": "median overlap between the site's slope histogram and those of its sixteen half-degree "
                            "sub-boxes (16 x 16 MOLA pixels, about 30 km on Mars)",
            "overlap": "sum over the bins of the smaller of the two shares: 1 for identical histograms, 0 for disjoint",
            "square id": "m_<lat>_<lon> of the square's centre, two decimals; squares of 0.5 degree from 85 S to 84 N",
            "rounding": "shares, slopes and overlaps to four decimals, metres to 0.1 m",
        },
        "mars": {"label": mars["info"], "site_boxes": mars["boxes"]},
        "earth": counts,
        "limits": [
            "Baseline about 1.85 km north-south on both planets (a slope is a height difference over two pixels, "
            "3.7 km). Nothing a rover, a vehicle or a person would feel is seen: boulders, rock fields, dunes, "
            "gullies, crater rims and channels narrower than a few kilometres, and any slope over less than "
            "a few kilometres, are averaged away. Slopes at this baseline are much gentler than at metre scale.",
            "The east-west pixel shrinks with cos(latitude) on both planets (Phoenix at 68 N: 0.69 km; Earth at "
            "75 N: 0.48 km), so at high latitude the east-west part of a slope is taken over a shorter baseline "
            "than the north-south part. The rule is the same on both planets, but a high-latitude place and a "
            "low-latitude place are not measured over quite the same baseline.",
            "MOLA MEGDR: 'Where no observations lie within the area, an interpolated value is supplied'; near the "
            "equator about 55 percent of 1/32-degree bins hold at least one laser shot and the tracks are up to "
            "12 km apart (PDS3 label). Interpolated pixels make slopes smoother than the ground; Gale (4.6 S) and "
            "Jezero (18.4 N) are the most affected, Phoenix (68 N) the least. The shot-count file was not read.",
            "ETOPO 2022 at 60 arc-seconds is itself resampled from finer sources of mixed quality; on ice sheets "
            "it gives the ice surface.",
            "Earth is treated as a sphere of mean radius: the true north-south and east-west spacings differ from "
            "it by at most 0.6 percent (WGS84), which changes no slope by more than 0.6 percent of its tangent.",
            "Coasts: the 1:50m land outline is generalised (its shore lies up to a few kilometres off the true one) "
            "and is not the shoreline ETOPO saw. A land pixel that touches a water pixel has no slope, so no slope "
            "is taken across a shore, and a strip one pixel (about 1.85 km) wide along every sea coast, the Caspian "
            "shore and every ice-shelf edge is left out of the slopes (earth.pixels_85S_to_84N."
            "land_pixels_touching_water). Where the outline lies seaward of the true shore, near-shore sea floor "
            "is counted as land (of_them_below_0_m counts the shore pixels below sea level; land_pixels_below_0_m "
            "also holds real depressions such as the Dead Sea and the lake beds below); where it lies landward, "
            "coastal land is lost; islands too small for the outline are missing. land_share counts pixels inside "
            "the outline.",
            "Natural Earth 1:50m land leaves out the Caspian Sea and the large Antarctic ice shelves (Ross, Ronne, "
            "Amery and Larsen C checked), so these are water here; it counts other lakes as land (Superior, "
            "Victoria, Baikal, Aral, Ladoga, Great Salt Lake checked), and ETOPO's surface there is the lake bed "
            "(Lake Superior reads 29 m against a water surface near 183 m, Baikal -258 m against about 456 m). "
            "Squares in big lakes therefore carry lake-bed slopes. No lake mask was applied.",
            "Squares shrink east-west with cos(latitude) (55 km by 14 km at 75 N) and always hold 900 pixels; "
            "the Mars site box is about 118 km by 118 x cos(latitude) km and its sub-boxes about 30 km, smaller "
            "than an Earth square.",
            "Heights on Mars are above the MOLA areoid, on Earth above the EGM2008 geoid; only differences within "
            "one planet are used (slopes, relief), never a Mars height against an Earth height.",
        ],
        "seconds": None,
    }
    meta["seconds"] = round(time.time() - t0, 1)
    write_json(OUT, {"meta": meta, "sites": sites, "cells": cells})
    print(f"wrote {OUT}: {len(sites)} sites, {len(cells)} squares, {OUT.stat().st_size / 1e6:.1f} MB, "
          f"{meta['seconds']} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())

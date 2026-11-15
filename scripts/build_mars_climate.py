"""Mars part, climate side. Writes data/derived/mars_climate.json.

Three steps, each safe to run again (nothing on disk is asked for twice):

    uv run python scripts/build_mars_climate.py fetch-power        # NASA POWER climatology, land boxes only
    uv run python scripts/build_mars_climate.py fetch-worldcover   # ESA WorldCover 2021 tiles, overview reads
    uv run python scripts/build_mars_climate.py build              # no network; writes the JSON

fetch-power asks the POWER regional climatology for T2M, TS, PRECTOTCORR and PS, one
parameter and one 10 degree box per request, one request at a time with a pause, only for
boxes that hold land by the Natural Earth outline. Raw answers go to data/raw/power_global/
(T2M and TS answers already fetched by the Moon part are copied from data/raw/power_temperature/).

fetch-worldcover reads every WorldCover tile with land between 60 S and 57 N (north of 57 N
they are already cached) as 360 x 360 samples, eight at a time, into data/raw/worldcover/.

build reads only files on disk. See twinfinder/mars_climate.py for the definitions.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

from twinfinder import cloud, landcover, temperature
from twinfinder import mars_climate as mc

NE = Path("data/raw/naturalearth/ne_50m_land.geojson")
POWER_RAW = Path("data/raw/power_global")
POWER_LOG = POWER_RAW / "fetch_log.jsonl"
POWER_OLD = Path("data/raw/power_temperature")
WC_RAW = Path("data/raw/worldcover")
WC_LOG = Path("data/raw/mars_climate/worldcover_fetch_log.jsonl")
MARS_RAW = Path("data/raw/mars_climate")
SOUTH = Path("data/derived/landcover_cells_south.json")
SITES = Path("data/derived/mars_sites_base.json")
SITE_CLIMATE = MARS_RAW / "site_climate.json"
CANNOT_MATCH = MARS_RAW / "cannot_match.json"
OUT = Path("data/derived/mars_climate.json")
WC_SOUTH_EDGE = -60      # WorldCover has no cover south of 60 S
WC_NORTH_CACHED = 57     # tiles from 57 N northwards were cached by the Moon part


def now_utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    side = path.with_name(path.name + ".part")
    side.write_text(json.dumps(value, separators=(",", ":"), allow_nan=False))
    os.replace(side, path)


def land_fraction() -> np.ndarray:
    return mc.land_fraction_grid(json.loads(NE.read_text()))


def land_squares(frac: np.ndarray, minimum: float = 0.0) -> list[dict]:
    lats, lons = mc.row_centres(), mc.column_centres()
    rows, cols = np.nonzero(frac > minimum)
    return [{"id": mc.square_id(lats[r], lons[c]), "lat": lats[r], "lon": lons[c], "ne_land": float(frac[r, c])}
            for r, c in zip(rows, cols)]


# ---- POWER -----------------------------------------------------------------------------------------

def power_tiles(squares) -> list[tuple[int, int, int, int]]:
    return temperature.tiles_for_cells(squares)


def fetch_power(pause_s: float) -> None:
    frac = land_fraction()
    squares = land_squares(frac)
    try:                                   # squares WorldCover finds land in, where Natural Earth has none
        known = {q["id"] for q in squares}
        squares += [s for s in earth_squares(frac)[0] if s["id"] not in known]
    except FileNotFoundError:
        pass
    tiles = power_tiles(squares)
    POWER_RAW.mkdir(parents=True, exist_ok=True)
    wanted = [(p, t) for p in mc.POWER_PARAMETERS for t in tiles]
    print(f"{now_utc()} {len(squares)} squares with Natural Earth land; {len(tiles)} boxes x "
          f"{len(mc.POWER_PARAMETERS)} parameters = {len(wanted)} answers", flush=True)
    copied = asked = 0
    started = time.time()
    for n, (parameter, tile) in enumerate(wanted, 1):
        name = cloud.raw_name(parameter, tile)
        dest = POWER_RAW / name
        if dest.exists():
            continue
        old = POWER_OLD / name
        if old.exists():
            mc.read_power(old.read_bytes(), parameter)          # must read as an answer
            shutil.copy2(old, dest)
            copied += 1
            with open(POWER_LOG, "a") as log:
                log.write(json.dumps({"time": now_utc(), "file": name, "copied_from": str(old),
                                      "bytes": dest.stat().st_size}) + "\n")
            continue
        url = cloud.regional_url(parameter, tile)
        for round_ in range(1, 4):                                  # whole rounds after a dropped network
            try:
                temperature._fetch(url, dest, lambda body, p=parameter: mc.read_power(body, p))
                break
            except Exception as error:                              # noqa: BLE001 - logged and retried
                print(f"{now_utc()} {name}: {type(error).__name__}: {error} (round {round_})", flush=True)
                if round_ == 3:
                    raise
                time.sleep(30 * round_)
        asked += 1
        with open(POWER_LOG, "a") as log:
            log.write(json.dumps({"time": now_utc(), "url": url, "file": name, "bytes": dest.stat().st_size}) + "\n")
        if asked % 25 == 0:
            rate = (time.time() - started) / asked
            print(f"{now_utc()} asked {asked}, copied {copied} (at {n} of {len(wanted)}); {rate:.1f} s a request",
                  flush=True)
        time.sleep(pause_s)
    print(f"{now_utc()} done: asked {asked}, copied {copied}, on disk "
          f"{sum((POWER_RAW / cloud.raw_name(p, t)).exists() for p, t in wanted)} of {len(wanted)}", flush=True)


# ---- WorldCover --------------------------------------------------------------------------------------

GDAL_OPTIONS = {
    "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
    "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif",
    "GDAL_HTTP_USERAGENT": "twinfinder/0.1",
    "GDAL_HTTP_MAX_RETRY": "3",
    "GDAL_HTTP_RETRY_DELAY": "2",
}


def wc_origins(frac: np.ndarray, south: int = WC_SOUTH_EDGE, north: int = 84) -> list[tuple[int, int]]:
    """3 degree tiles (south-west corners) whose box, widened by one square, holds Natural Earth land."""
    lats, lons = np.array(mc.row_centres()), np.array(mc.column_centres())
    out = []
    for lat0 in range(south, north, 3):
        rows = np.nonzero((lats > lat0 - 0.5) & (lats < lat0 + 3.5))[0]
        for lon0 in range(-180, 180, 3):
            cols = np.nonzero((lons > lon0 - 0.5) & (lons < lon0 + 3.5))[0]
            if rows.size and cols.size and frac[np.ix_(rows, cols)].max() > 0:
                out.append((lat0, lon0))
    return out


def read_wc_tile(origin: tuple[int, int]):
    """(origin, status, seconds): status 'cached', 'missing' (404, open sea), 'read' or an error text."""
    import rasterio
    from twinfinder.fetch import exists_on_server

    lat0, lon0 = origin
    cached, missing = WC_RAW / f"{lat0}_{lon0}.npy", WC_RAW / f"{lat0}_{lon0}.missing"
    if cached.exists():
        return origin, "cached", 0.0
    if missing.exists():
        return origin, "missing", 0.0
    url = landcover.tile_url(lat0, lon0)
    start = time.time()
    try:
        if not exists_on_server(url):
            missing.touch()
            return origin, "missing", time.time() - start
        with rasterio.Env(**GDAL_OPTIONS), rasterio.open("/vsicurl/" + url) as ds:
            classes = ds.read(1, out_shape=(landcover.READ_PX, landcover.READ_PX))
    except Exception as error:  # noqa: BLE001 - reported; never treated as sea
        return origin, f"{type(error).__name__}: {error}", time.time() - start
    side = WC_RAW / f"{lat0}_{lon0}.part.npy"
    np.save(side, classes)
    os.replace(side, cached)
    return origin, "read", time.time() - start


def fetch_worldcover(workers: int) -> None:
    frac = land_fraction()
    origins = wc_origins(frac, WC_SOUTH_EDGE, WC_NORTH_CACHED)
    WC_LOG.parent.mkdir(parents=True, exist_ok=True)
    todo = [o for o in origins if not (WC_RAW / f"{o[0]}_{o[1]}.npy").exists()
            and not (WC_RAW / f"{o[0]}_{o[1]}.missing").exists()]
    print(f"{now_utc()} {len(origins)} tiles with Natural Earth land from {WC_SOUTH_EDGE} to {WC_NORTH_CACHED} N; "
          f"{len(todo)} not on disk", flush=True)
    started, done, failed = time.time(), 0, []
    with ThreadPoolExecutor(max_workers=workers) as pool, open(WC_LOG, "a") as log:
        for origin, status, seconds in pool.map(read_wc_tile, todo):
            done += 1
            log.write(json.dumps({"time": now_utc(), "tile": f"{origin[0]}_{origin[1]}", "status": status,
                                  "seconds": round(seconds, 1),
                                  "url": landcover.tile_url(*origin)}) + "\n")
            log.flush()
            if status not in ("read", "missing", "cached"):
                failed.append((origin, status))
            if done % 50 == 0 or done == len(todo):
                elapsed = time.time() - started
                print(f"{now_utc()} {done} of {len(todo)} in {elapsed:.0f} s; projected total "
                      f"{elapsed / done * len(todo) / 60:.1f} min; failed {len(failed)}", flush=True)
    print(f"{now_utc()} done; failed {len(failed)}", flush=True)
    for origin, status in failed[:30]:
        print(f"  FAILED {origin}: {status}")
    if failed:
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("step", choices=["fetch-power", "fetch-worldcover", "build"])
    parser.add_argument("--pause", type=float, default=0.5)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    if args.step == "fetch-power":
        fetch_power(args.pause)
    elif args.step == "fetch-worldcover":
        fetch_worldcover(args.workers)
    else:
        build()


# ---- the Earth squares: land share and bare ground ----------------------------------------------------

WC_SOURCE = ("ESA WorldCover 10 m 2021 v200, class 60 (bare / sparse vegetation) as a share of the land samples; "
             "each 3 degree tile read as 360 x 360 samples from its overviews (60 x 60 samples a square)")
SOUTH_SOURCE = ("Antarctic rock-outcrop squares of the project (data/derived/landcover_cells_south.json, the larger "
                "of its two rock layers), summed into the half-degree square and divided by the square's land "
                "area from Natural Earth 1:50m; cells under 5 % rock are not in that file, so this is a lower bound")


def earth_squares(frac: np.ndarray) -> tuple[list[dict], dict]:
    """Squares kept for the Mars part (land share >= 0.2), with land share and bare share; and counts.

    North of 60 S both come from WorldCover; south of 60 S the land share is the Natural Earth
    outline's and bare ground comes from the rock-outcrop cells. A square with Natural Earth land
    of at least 0.2 where no WorldCover tile exists is kept with bare unknown.
    """
    lats, lons = mc.row_centres(), mc.column_centres()
    wc: dict[str, dict] = {}
    tiles_read = tiles_sea = 0
    for lat0 in range(WC_SOUTH_EDGE, 84, 3):
        for lon0 in range(-180, 180, 3):
            path = WC_RAW / f"{lat0}_{lon0}.npy"
            if path.exists():
                tiles_read += 1
                for s in mc.worldcover_squares(np.load(path), lat0, lon0):
                    if mc.LAT_SOUTH < s["lat"] < mc.LAT_NORTH:
                        wc[s["id"]] = s
            elif (WC_RAW / f"{lat0}_{lon0}.missing").exists():
                tiles_sea += 1
    if not tiles_read:
        raise FileNotFoundError("no WorldCover tile on disk")
    rock = mc.south_rock_km2(json.loads(SOUTH.read_text()))
    kept, no_tile, ne_only_dropped = [], 0, 0
    south_land = {}
    for r, lat in enumerate(lats):
        for c, lon in enumerate(lons):
            sid = mc.square_id(lat, lon)
            ne = float(frac[r, c])
            if lat < WC_SOUTH_EDGE:
                if ne >= mc.MIN_LAND_SHARE:
                    south_land[(lat, lon)] = ne * mc.square_km2(lat)
                continue
            s = wc.get(sid)
            if s is not None:
                if s["land_share"] >= mc.MIN_LAND_SHARE:
                    kept.append({"id": sid, "lat": lat, "lon": lon, "land_share": s["land_share"],
                                 "land_source": "worldcover", "ne_land": ne, "bare": s["bare"],
                                 "bare_source": "worldcover"})
                elif ne >= mc.MIN_LAND_SHARE:
                    ne_only_dropped += 1
            elif ne >= mc.MIN_LAND_SHARE:
                no_tile += 1
                kept.append({"id": sid, "lat": lat, "lon": lon, "land_share": ne, "land_source": "natural earth",
                             "ne_land": ne, "bare": None, "bare_source": None})
    bare_south = mc.south_bare(rock, south_land)
    for (lat, lon), land_km2 in south_land.items():
        kept.append({"id": mc.square_id(lat, lon), "lat": lat, "lon": lon,
                     "land_share": land_km2 / mc.square_km2(lat), "land_source": "natural earth",
                     "ne_land": land_km2 / mc.square_km2(lat), "bare": bare_south.get((lat, lon), 0.0),
                     "bare_source": "antarctic rock"})
    rock_outside = sum(v for k, v in rock.items() if k not in south_land)
    counts = {"worldcover_tiles_read": tiles_read, "worldcover_tiles_not_on_server_open_sea": tiles_sea,
              "squares_kept": len(kept),
              "squares_kept_north_of_60s_worldcover": sum(1 for s in kept if s["bare_source"] == "worldcover"),
              "squares_kept_south_of_60s": len(south_land),
              "squares_with_natural_earth_land_but_no_worldcover_tile": no_tile,
              "squares_natural_earth_land_0.2_but_worldcover_under_0.2_dropped": ne_only_dropped,
              "antarctic_rock_km2_in_squares_with_under_0.2_land_left_out": round(rock_outside, 1)}
    return kept, counts


# ---- the Mars sites -------------------------------------------------------------------------------------

MCD_URL = "https://www-mars.lmd.jussieu.fr/mcd_python/"
MCD_SOURCE = ("model (Mars Climate Database v6.2, LMD with ESA and CNES; web interface, climatology average solar "
              "scenario, 2 m above the surface, Ls and local time in steps of 15 degrees and 1 hour)")
MCD_TERMS = ("Mars Climate Database (c) LMD/LATMOS/OU/IAA/ESA/CNES. Used through the web interface, which is "
             "'intended for moderate use only' (12 requests here, one a site); scientific use is allowed if the "
             "origin of the data is quoted and the authors are kept informed (telling them is for the user to "
             "decide); no commercial use without permission. LMD warns the online database understates extremes "
             "such as daily ranges.")
REMS_URL = "https://mars.nasa.gov/rss/api/?feed=weather&category=msl&feedtype=json"
REMS_SOURCE = ("measured by a lander (Curiosity REMS, daily minimum and maximum air temperature and daily pressure, "
               "sols 1 to 4995, from NASA's weather feed, which carries the CAB note 'for outreach purposes only'; "
               "the scientific record is the REMS data in PDS, not read here)")
PHX_URL = "https://atmos.nmsu.edu/data_and_services/atmospheres_data/phoenix/met.html"
PHX_SOURCE = ("measured by a lander (Phoenix MET, PDS low-rate reduced files, 1000 mm mast sensor; sols 0 to 151, "
              "Ls 77 to 148, northern summer only)")
MEDA_NOTE = ("Perseverance MEDA, Rodriguez-Manfredi et al. 2023, Nature Geoscience (saved: "
             "data/raw/mars_sites/rodriguezmanfredi2023_natgeo.pdf): daily mean pressure from 735 Pa on sols 15-20 "
             "(Ls 13-16) to 761 Pa on sols 99-110 (Ls 52-57), falling to 650 Pa by sol 250 (paper text). "
             "Temperatures are only in its figures and are not used.")
CLIMATE_HOW = (
    "annual_mean_c: air temperature 2 m above the ground, mean over all hours of the mean day of each Ls step, "
    "weighted by the time Mars spends in that step (Kepler's second law, eccentricity 0.0934, perihelion at Ls "
    "251). warm_season_daily_max_c: the highest daily maximum of any season (lander: highest mean of the daily "
    "maxima in any 15 degree Ls bin with at least 5 sols; model: highest hourly value of the mean day of any Ls "
    "step). cold_season_daily_min_c: the same for the lowest daily minimum. pressure_pa: surface pressure, mean "
    "over the year (lander: 15 degree Ls bin means weighted by time; model: as for annual_mean_c). A measured "
    "value is used where a lander measured that season; otherwise the model value."
)


def mcd_site(site_id: str) -> dict:
    tables = mc.read_mcd_table((MARS_RAW / "mcd" / f"{site_id}_2d.txt").read_text())
    t = mc.mcd_summary(tables["Temperature (K)"])
    ts = mc.mcd_summary(tables["Surface temperature (K)"])
    ps = mc.mcd_summary(tables["Surface pressure (Pa)"])
    return {"annual_mean_c": round(t["annual_mean"] - 273.15, 1),
            "warm_season_daily_max_c": round(t["warm_season_daily_max"] - 273.15, 1), "warmest_ls": t["warmest_ls"],
            "cold_season_daily_min_c": round(t["cold_season_daily_min"] - 273.15, 1), "coldest_ls": t["coldest_ls"],
            "surface_annual_mean_c": round(ts["annual_mean"] - 273.15, 1),
            "pressure_pa": round(ps["annual_mean"]), "pressure_lowest_pa": round(ps["cold_season_daily_min"]),
            "pressure_highest_pa": round(ps["warm_season_daily_max"]),
            "file": str(MARS_RAW / "mcd" / f"{site_id}_2d.txt"), "tables": tables}


def ls_bin_pressure(pairs) -> float | None:
    """Time-weighted yearly mean of 15 degree Ls bin means; None unless all 24 bins have values."""
    bins: dict[int, list[float]] = {}
    for ls, p in pairs:
        bins.setdefault(int(ls // 15) % 24, []).append(p)
    if len(bins) < 24:
        return None
    w = mc.ls_weights([k * 15 + 7.5 for k in range(24)])
    return sum(w[k] * sum(bins[k]) / len(bins[k]) for k in range(24))


def gale_measured() -> dict:
    feed = json.loads((Path("data/raw/mars_sites/msl_weather_feed.json")).read_text())

    def num(x):
        try:
            return float(x)
        except (TypeError, ValueError):
            return None
    rows = [r for r in feed["soles"] if num(r.get("ls")) is not None]
    ext = mc.seasonal_extremes([(num(r["ls"]), num(r["min_temp"]), num(r["max_temp"])) for r in rows])
    pressure = ls_bin_pressure([(num(r["ls"]), num(r["pressure"])) for r in rows if num(r["pressure"]) is not None])
    return {"warm_season_daily_max_c": round(ext["warm_season_daily_max"], 1),
            "cold_season_daily_min_c": round(ext["cold_season_daily_min"], 1),
            "pressure_pa": round(pressure) if pressure is not None else None,
            "ls_covered": ext["ls_covered"], "sols": len(rows),
            "sols_with_temperatures": sum(1 for r in rows if num(r["max_temp"]) is not None),
            "file": "data/raw/mars_sites/msl_weather_feed.json", "source": REMS_SOURCE, "url": REMS_URL}


def phoenix_measured() -> dict:
    import csv
    raw = Path("data/raw/mars_sites")
    ls = {r["FILE_NAME"].upper(): float(r["Ls"]) for r in csv.DictReader(open(raw / "pds_phoenix_met_data_reduced.csv"))}
    sols, pressures, files = [], [], 0
    for path in sorted(raw.glob("phx_met_MS*RML*.TAB")):
        files += 1
        name = path.name[len("phx_met_"):].upper()
        o = mc.phoenix_sol(path.read_text())
        if name not in ls:
            continue
        k = lambda v: None if v is None else v - 273.15   # noqa: E731
        sols.append((ls[name], k(o["min_k"]), k(o["max_k"])))
        if o["pressure_pa"] is not None:
            pressures.append(o["pressure_pa"])
    ext = mc.seasonal_extremes(sols)
    return {"warm_season_daily_max_c": round(ext["warm_season_daily_max"], 1),
            "lowest_daily_min_of_the_mission_c": round(ext["cold_season_daily_min"], 1),
            "pressure_mean_of_the_mission_pa": round(sum(pressures) / len(pressures)),
            "ls_covered": ext["ls_covered"], "files": files,
            "sols_with_daily_extremes": sum(1 for s in sols if s[2] is not None),
            "file": "data/raw/mars_sites/phx_met_MS*RML*.TAB with pds_phoenix_met_data_reduced.csv",
            "source": PHX_SOURCE, "url": PHX_URL}


def mcd_band_mean(table: dict, ls_low: float, ls_high: float) -> float:
    """Mean of the MCD mean day over the Ls steps inside [ls_low, ls_high] (for checks against a lander)."""
    rows = [i for i, ls in enumerate(table["ls"][:-1]) if ls_low <= ls <= ls_high]
    return float(np.asarray(table["values"])[rows, :-1].mean())


def mcd_band_max(table: dict, ls_low: float, ls_high: float) -> float:
    rows = [i for i, ls in enumerate(table["ls"][:-1]) if ls_low <= ls <= ls_high]
    return float(np.asarray(table["values"])[rows, :-1].max())


def site_climate(site: dict) -> dict:
    model = mcd_site(site["id"])
    tables = model.pop("tables")
    fields = ("annual_mean_c", "warm_season_daily_max_c", "cold_season_daily_min_c", "pressure_pa")
    values = {f: model[f] for f in fields}
    kinds = {f: "model" for f in fields}
    sources = {f: MCD_SOURCE for f in fields}
    measured, check = None, None
    if site["id"] == "gale":
        measured = gale_measured()
        for f in ("warm_season_daily_max_c", "cold_season_daily_min_c", "pressure_pa"):
            if measured[f] is not None:
                values[f], kinds[f], sources[f] = measured[f], "measured by a lander", REMS_SOURCE
        check = {"pressure_pa_model_vs_measured": [model["pressure_pa"], measured["pressure_pa"]],
                 "warm_season_daily_max_c_model_vs_measured": [model["warm_season_daily_max_c"],
                                                              measured["warm_season_daily_max_c"]],
                 "cold_season_daily_min_c_model_vs_measured": [model["cold_season_daily_min_c"],
                                                              measured["cold_season_daily_min_c"]]}
    elif site["id"] == "phoenix":
        measured = phoenix_measured()
        values["warm_season_daily_max_c"] = measured["warm_season_daily_max_c"]
        kinds["warm_season_daily_max_c"] = "measured by a lander"
        sources["warm_season_daily_max_c"] = PHX_SOURCE
        lo, hi = measured["ls_covered"][0][0], measured["ls_covered"][-1][1]
        check = {"over_ls": [lo, hi],
                 "pressure_pa_model_vs_measured_over_the_mission": [
                     round(mcd_band_mean(tables["Surface pressure (Pa)"], lo, hi)),
                     measured["pressure_mean_of_the_mission_pa"]],
                 "highest_hourly_air_temperature_c_model_vs_highest_bin_mean_of_daily_maxima_measured": [
                     round(mcd_band_max(tables["Temperature (K)"], lo, hi) - 273.15, 1),
                     measured["warm_season_daily_max_c"]],
                 "note": ("Phoenix worked only in northern summer, so its yearly mean, winter minimum and yearly "
                          "pressure are model values")}
    elif site["id"] == "jezero":
        p = tables["Surface pressure (Pa)"]
        check = {"meda_paper_daily_mean_pressure_pa": {"Ls 13-16": 735, "Ls 52-57": 761},
                 "model_mean_day_pressure_pa": {"Ls 15": round(mcd_band_mean(p, 15, 15)),
                                                "Ls 45-60": round(mcd_band_mean(p, 45, 60))},
                 "note": MEDA_NOTE}
    all_measured = all(k == "measured by a lander" for k in kinds.values())
    main = REMS_URL if site["id"] == "gale" else (PHX_URL if site["id"] == "phoenix" else MCD_URL)
    return {**values,
            "kind": "measured by a lander" if all_measured else "model",
            "source": ("; ".join(sorted(set(sources.values())))),
            "url": main if all_measured else MCD_URL,
            "kind_by_field": kinds, "source_by_field": sources,
            "urls": sorted({MCD_URL} | ({REMS_URL} if site["id"] == "gale" else set())
                           | ({PHX_URL} if site["id"] == "phoenix" else set())),
            "model": model, "measured": measured, "model_against_measured": check,
            "how": CLIMATE_HOW}


# ---- what no place on Earth matches ------------------------------------------------------------------------

FACTS = "NASA NSSDCA Mars Fact Sheet and Earth Fact Sheet (saved: data/raw/mars_climate/factsheets/)"
FACTS_URL = "https://nssdc.gsfc.nasa.gov/planetary/factsheet/marsfact.html"
MARS_PERIHELION_MKM, MARS_APHELION_MKM, MARS_A_MKM = 206.650, 249.261, 227.956


def cannot_match(site: dict, climate: dict, earth_lowest_ps_kpa: float | None, earth_lowest_where: str | None) -> list[dict]:
    p = climate["pressure_pa"]
    irr = 586.2
    irr_peri, irr_aph = irr * (MARS_A_MKM / MARS_PERIHELION_MKM) ** 2, irr * (MARS_A_MKM / MARS_APHELION_MKM) ** 2
    low_pa = None if earth_lowest_ps_kpa is None else earth_lowest_ps_kpa * 1000.0
    return [
        {"what": "surface air pressure", "mars": p, "earth": 101325, "unit": "Pa",
         "number": round(p / 101325, 4), "number_is": "Mars site / Earth sea level",
         "earth_lowest_land_square_pa": None if low_pa is None else round(low_pa),
         "earth_lowest_land_square_where": earth_lowest_where,
         "mars_site_over_earth_lowest_land_square": None if low_pa is None else round(p / low_pa, 4),
         "source": (f"Mars: this site's yearly mean, {climate['kind_by_field']['pressure_pa']} "
                    f"({climate['source_by_field']['pressure_pa'][:60]}...); Earth: standard sea-level pressure; "
                    "lowest land square: yearly mean surface pressure (PS) of NASA POWER in this file"),
         "note": "Mars-wide 6.36 mb (636 Pa) at the mean radius, 400 to 870 Pa by place and season (Mars Fact Sheet)"},
        {"what": "gravity", "mars": 3.73, "earth": 9.82, "unit": "m/s2", "number": 0.380,
         "number_is": "Mars / Earth", "source": FACTS, "url": FACTS_URL},
        {"what": "sunlight at the top of the atmosphere", "mars": 586.2, "earth": 1361.0, "unit": "W/m2",
         "number": 0.431, "number_is": "Mars / Earth (mean distance)",
         "mars_range": [round(irr_aph, 1), round(irr_peri, 1)],
         "mars_range_how": "586.2 W/m2 times (227.956 / distance)^2 at aphelion 249.261 and perihelion 206.650 million km",
         "source": FACTS, "url": FACTS_URL},
        {"what": "the air itself (oxygen)", "mars": 0.16, "earth": 20.95, "unit": "% O2 by volume",
         "number": round(0.16 / 20.95, 4), "number_is": "Mars / Earth",
         "note": ("Mars air is 95.1 % CO2, 2.59 % N2, 1.94 % Ar, 0.16 % O2, 210 ppm water; Earth's is 78.08 % N2, "
                  "20.95 % O2, 420 ppm CO2; mean molecular weight 43.49 against 28.97"),
         "source": FACTS, "url": FACTS_URL},
        {"what": "ultraviolet light at the ground", "mars": 190, "earth": 290, "unit": "nm, shortest wavelength of "
         "sunlight reaching the ground", "number": 100, "number_is": "nm shorter on Mars",
         "note": ("Mars has almost no ozone, so UV-C (200-280 nm), which never reaches Earth's ground, reaches the "
                  "Mars surface; only CO2 stops light shorter than about 190-200 nm"),
         "source": ("literature, not checked against a saved file in this run: Cockell et al. 2000, Icarus 146, "
                    "343-359 (Mars); the ozone cut-off near 290 nm (Earth)")},
        {"what": "ionising radiation at the ground", "mars": 0.64, "earth": 0.0066, "unit": "mSv per day",
         "number": round(0.64 / 0.0066), "number_is": "Mars / Earth",
         "note": ("Mars: dose equivalent measured by Curiosity RAD at Gale, 0.64 +/- 0.12 mSv/day (absorbed dose "
                  "0.21 mGy/day); Earth: world mean natural background about 2.4 mSv/year"),
         "source": ("literature, not checked against a saved file in this run: Hassler et al. 2014, Science 343, "
                    "1244797 (RAD); UNSCEAR 2008 (Earth)")},
        {"what": "the dusty sky", "mars": 3, "earth": 0.13, "unit": "aerosol optical depth",
         "number": None, "number_is": "no single ratio: see note",
         "note": ("Mars: optical depth generally below 1 in the aphelion season (Ls 0-180) and above 3 at the peak "
                  "of global dust storms (in-situ record of 7 landers); dust is in the sky all year. Earth: global "
                  "mean optical depth at 550 nm about 0.1-0.2 (Earth figure from memory, not checked)"),
         "source": ("Mars: Martinez et al. 2017, Space Science Reviews, section 3.1 (saved: "
                    "data/raw/mars_sites/martinez2017_ssr_review.pdf)")},
        {"what": "length of the year", "mars": 686.98, "earth": 365.256, "unit": "Earth days",
         "number": 1.881, "number_is": "Mars / Earth",
         "note": ("668.6 sols of 24.66 h; seasons nearly twice as long and unequal (orbit eccentricity 0.0935 "
                  "against 0.0167), so an Earth month stands for about two Mars months"),
         "source": FACTS, "url": FACTS_URL},
    ]


# ---- build ------------------------------------------------------------------------------------------------

def r1(v):
    return None if v is None else round(v, 1)


def r2(v):
    return None if v is None else round(v, 2)


def power_header(tiles) -> dict:
    heads = {}
    for p in mc.POWER_PARAMETERS:
        named = set()
        for t in tiles:
            h = cloud.answer_header((POWER_RAW / cloud.raw_name(p, t)).read_bytes())
            named.add((h["version"], h["start"], h["end"], tuple(h["sources"] or []), h["fill_value"]))
        if len(named) != 1:
            raise ValueError(f"POWER answers of {p} disagree: {sorted(named)!r}")
        version, start, end, sources, fill = named.pop()
        heads[p] = {"version": version, "start": start, "end": end, "sources": list(sources), "fill_value": fill}
    return heads


def build() -> None:
    frac = land_fraction()
    squares, counts = earth_squares(frac)
    tiles = power_tiles(squares)
    missing = [cloud.raw_name(p, t) for p in mc.POWER_PARAMETERS for t in tiles
               if not (POWER_RAW / cloud.raw_name(p, t)).exists()]
    if missing:
        raise SystemExit(f"{len(missing)} POWER answers missing (run fetch-power), first {missing[:3]}")
    by_point = {}
    for p in mc.POWER_PARAMETERS:
        rows: dict = {}
        for t in tiles:
            rows.update(mc.read_power((POWER_RAW / cloud.raw_name(p, t)).read_bytes(), p))
        by_point[p] = rows
    heads = power_header(tiles)

    cells, no_point = {}, 0
    for s in squares:
        point = temperature.grid_point(s["lat"], s["lon"])
        t2m, ts, pr, ps = (by_point[p].get(point) for p in mc.POWER_PARAMETERS)
        no_point += any(v is None for v in (t2m, ts, pr, ps))
        months = lambda row: None if row is None or all(v is None for v in row[0]) else [r1(v) for v in row[0]]  # noqa: E731
        precip = mc.precip_mm_month(pr[0]) if pr else None
        cells[s["id"]] = {
            "bare": None if s["bare"] is None else round(s["bare"], 4),
            "bare_source": {"worldcover": "ESA WorldCover 2021", "antarctic rock": "Antarctic rock outcrop",
                            None: None}[s["bare_source"]],
            "land_share": round(s["land_share"], 4),
            "t2m_c": months(t2m), "ts_c": months(ts),
            "precip_mm": None if precip is None or all(v is None for v in precip) else [r1(v) for v in precip],
            "precip_mm_year": r1(mc.precip_mm_year(precip)),
            "pressure_kpa": r2(ps[1]) if ps else None,
            "t2m_year_c": r1(t2m[1]) if t2m else None,
            "cloud_pct": None,
            "grid": [point[0], point[1]],
        }

    # the lowest yearly surface pressure of any kept land square, for the pressure gap
    known_ps = [(c["pressure_kpa"], cid) for cid, c in cells.items() if c["pressure_kpa"] is not None]
    lowest_ps, lowest_id = min(known_ps) if known_ps else (None, None)

    sites_base = json.loads(SITES.read_text())
    sites = {}
    for site in sites_base["sites"]:
        climate = site_climate(site)
        sites[site["id"]] = {"sun": mc.site_sun(site["lat"]), "climate": climate,
                             "cannot_match": cannot_match(site, climate, lowest_ps, lowest_id)}

    bare_known = [c for c in cells.values() if c["bare"] is not None]
    stats = {
        **counts,
        "squares_with_land": len(cells),
        "squares_with_all_four_climate_fields": sum(1 for c in cells.values() if c["t2m_c"] and c["ts_c"]
                                                     and c["precip_mm"] and c["pressure_kpa"] is not None),
        "squares_with_a_grid_point_missing_in_some_field": no_point,
        "squares_with_bare_known": len(bare_known),
        "squares_with_bare_at_least_0.15": sum(1 for c in bare_known if c["bare"] >= mc.MIN_BARE),
        "squares_with_bare_at_least_0.15_by_source": {
            src: sum(1 for c in bare_known if c["bare"] >= mc.MIN_BARE and c["bare_source"] == src)
            for src in ("ESA WorldCover 2021", "Antarctic rock outcrop")},
        "power_boxes": len(tiles), "power_answers": len(tiles) * len(mc.POWER_PARAMETERS),
        "grid_points_used": len({tuple(c["grid"]) for c in cells.values()}),
    }
    first = heads["T2M"]
    meta = {
        "what": ("Mars part, climate side (plan docs/superpowers/plans/2026-11-14-mars-part.md): the Sun and climate of "
                 "each Mars site, what no place on Earth matches, and climate and bare ground of every half-degree "
                 "square of Earth with at least 20 % land. A first pass, coarser than the Moon part: squares of "
                 "0.5 degree (about 55 km)."),
        "written": now_utc(), "written_by": "agent MARS-CLIMATE, scripts/build_mars_climate.py build",
        "grid": {"square_deg": 0.5, "centres": "at .25 and .75", "from": "85 S", "to": "84 N",
                 "id": "m_<lat>_<lon>, two decimals, centre of the square", "kept_if": "land share >= 0.2"},
        "fields": {
            "bare": "share of the square's land that is bare ground (0 to 1); null if unknown",
            "bare_source": "'ESA WorldCover 2021' north of 60 S, 'Antarctic rock outcrop' south of 60 S, null if none",
            "land_share": ("share of the whole square that is land: WorldCover land samples over all samples "
                           "north of 60 S (no data counts as sea, as WorldCover leaves open sea unmapped); Natural "
                           "Earth 1:50m outline south of 60 S (the grounded ice sheet counts as land; ice shelves do not: a Ross "
                           "Ice Shelf square, m_-81.25_-175.25, is not kept)"),
            "t2m_c": "NASA POWER T2M: mean air temperature 2 m above the ground, all hours, by calendar month, C",
            "ts_c": "NASA POWER TS: mean temperature of the surface itself (skin), all hours, by month, C",
            "precip_mm": ("NASA POWER PRECTOTCORR (bias-corrected precipitation, rain and snow as water) by "
                          "month in mm: the service's mm/day times the days of the month (February 28.25)"),
            "precip_mm_year": "sum of the 12 months, mm; null if any month is unknown",
            "pressure_kpa": "NASA POWER PS: surface pressure, the service's annual value, kPa",
            "t2m_year_c": "NASA POWER T2M annual value, C (added for the cold score; not in the plan's layout)",
            "cloud_pct": "not fetched in this pass: always null",
            "grid": "[lat, lon] of the MERRA-2 grid point the climate was read at (nearest to the square centre)",
        },
        "bare_sources": {"ESA WorldCover 2021": WC_SOURCE, "Antarctic rock outcrop": SOUTH_SOURCE},
        "climate_source": (f"NASA POWER {first['version']} climatology, regional endpoint, source named by the "
                           f"service: {', '.join(first['sources'])} (NASA's MERRA-2 reanalysis), native grid 0.5 x "
                           f"0.625 degrees; one parameter and one 10 degree box a request; no key, no login"),
        "climate_url_pattern": cloud.URL_PATTERN,
        "climate_period_named": f"{first['start'][:4]}-{first['start'][4:6]}-{first['start'][6:]} to "
                                f"{first['end'][:4]}-{first['end'][4:6]}-{first['end'][6:]}",
        "climate_period_caution": (
            "The service names 2001 to 2025, but the Moon part found on 14 November 2026 "
            "(data/derived/temperature_cells.json meta.years_fit) that at six grid points the climatology's monthly "
            "T2M extremes equal the daily record of 2001 to 2020 in 144 of 144 months and of 2001 to 2025 in only "
            "113, and its monthly means agree with 2001-2020 within 0.03 C. The same pre-computed table serves "
            "these values, so read them as 2001 to 2020 most likely; not re-checked for PRECTOTCORR and PS."),
        "climate_what_it_is_not": (
            "Model values (a reanalysis) for a grid box about 55 km tall at its own mean height, not measurements "
            "at the square; many squares share one grid point (each square takes the nearest point; a centre "
            "half-way between two rows goes to the row to the north). Precipitation in the driest deserts is "
            "a model value near zero and can differ from gauges by several mm a year; the service gives "
            "mm/day to two decimals, so a month under 0.005 mm/day reads 0 and a yearly 0.0 means under about "
            "2 mm. Near ice sheets and in deep valleys the grid box can lie far above the square (see pressure_kpa)."),
        "power_headers": heads,
        "raw": {"power": str(POWER_RAW), "worldcover": str(WC_RAW), "mars": str(MARS_RAW),
                "natural_earth": str(NE), "south_rock": str(SOUTH), "sites": str(SITES)},
        "null_rule": "unknown is null, never 0; a month without a value is null inside its list",
        "counts": stats,
        "sites_meta": {
            "sun_how": mc.SUN_HOW, "climate_how": CLIMATE_HOW, "mcd_terms": MCD_TERMS,
            "mcd_requests": ("one web request per site (ls=all, localtime=all, variables t, tsurf, ps, 2 m above "
                             "the surface, dust scenario 1 'climatology ave solar', high-resolution topography on); "
                             "answers kept in data/raw/mars_climate/mcd/; longitudes sent as -180..180 east"),
            "rems_caveat": ("NASA's REMS weather feed carries the note of Centro de Astrobiologia that it is 'for "
                            "outreach purposes only'; the figures from it are labelled as such"),
            "kind_rule": ("climate.kind is 'measured by a lander' only if all four values are measured; otherwise "
                          "'model', and climate.kind_by_field says which value is which"),
        },
        "plan_departures": [
            "cells carry land_share, t2m_year_c and grid besides the plan's fields",
            "site climate carries kind_by_field, source_by_field, urls, model, measured and model_against_measured "
            "besides the plan's fields, because at Gale and Phoenix some values are measured and some modelled",
            "cannot_match items carry number_is and note (and some carry more) besides the plan's fields",
            "cloud_pct is null for every square: the job named four POWER parameters and cloud was not fetched",
        ],
    }
    write_json(OUT, {"meta": meta, "sites": sites, "cells": cells})
    print(json.dumps(stats, indent=1))
    print(f"lowest yearly surface pressure of a kept square: {lowest_ps} kPa at {lowest_id}")
    for sid, s in sites.items():
        c = s["climate"]
        print(f"{sid}: sun {s['sun']['noon_elev_min_deg']}..{s['sun']['noon_elev_max_deg']} deg, day "
              f"{s['sun']['day_length_min_h']}..{s['sun']['day_length_max_h']} h; climate mean {c['annual_mean_c']} C, "
              f"warm max {c['warm_season_daily_max_c']} C, cold min {c['cold_season_daily_min_c']} C, "
              f"{c['pressure_pa']} Pa; {c['kind_by_field']}")
        if c["model_against_measured"]:
            print(f"   check: {json.dumps(c['model_against_measured'])[:400]}")
    print(f"wrote {OUT} ({OUT.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()

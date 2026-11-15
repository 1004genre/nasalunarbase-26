# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Second opinion on the IMS snow layer from weather reanalysis, at the places that carried the first ranking.

For each site and lunar target: the share of all-day low-Sun calendar days (the old measure) from
1 Oct 2015 to 31 Mar 2025 on which each source shows snow-free ground. Every source is scored on
the same days of year: all days of the window, whatever the month. At these sites every window day
falls between 1 October and 31 March (the output counts the days that do not).

The IMS odds are the project's 36 calendar ten-day bins (bin 0 = 1 to 10 January), built from maps
up to 28 September 2025; the reanalysis series in the cache stop on 31 March 2025. A window day
from April to September would therefore rest on nine years of reanalysis against ten of IMS.

Sources (no login):
  MERRA-2 through the NASA POWER daily point API: SNODP (cm) and FRSNO (land snow-cover fraction).
  ERA5-Land (0.1 degree) through the Open-Meteo archive API: snow_depth daily mean (m).
  CERRA (5.5 km, Europe, ends June 2021) through the same API, where the site is inside its domain.
Open-Meteo serves no snow depth for plain ERA5 (0.25 degree) or for ECMWF IFS.

Raw API responses are cached under data/raw/reanalysis/; delete a file there to fetch it again.
Run from the project root: uv run python scripts/second_opinion_snow.py [--offline]
--offline never downloads: a response that is not in the cache is listed under sources_failed.
"""
import argparse
import csv
import gzip
import json
import re
import time
import urllib.error
import urllib.request
from datetime import date, timedelta
from pathlib import Path

import numpy as np

from twinfinder import reference, snow, stations, sun

CACHE = Path("data/raw/reanalysis")
OUT = Path("data/derived/second_opinion_snow.json")
TARGETS = Path("data/derived/moon_targets.json")
SNOW = Path("data/derived/snow_free_dekads.npz")
STATION_CHECK = Path("data/derived/snow_validation.json")
IMS_DIR = Path("data/raw/ims")
GHCN_DIR = Path("data/raw/ghcn")
USER_AGENT = "twinfinder/0.1"

START, END = date(2015, 10, 1), date(2025, 3, 31)   # what the cached reanalysis series cover
CERRA_END = date(2021, 6, 30)   # Open-Meteo's CERRA archive stops here
WINTERS = list(range(2015, 2025))  # snow years (1 October to 30 September), named by their October
OFFLINE = False                 # set by --offline: use the cache only
THRESHOLDS_CM = (1.0, 5.0)
PERENNIAL_CM = 10.0             # a summer minimum above this means the model never melts its snow here

# name, lat, lon, kind of place, GHCN station to compare with (or None)
SITES = [
    ("Bear Island cell", 74.45, 19.25, "small island", "NO000099710"),
    ("Bear Island station", 74.5167, 19.0167, "small island", "NO000099710"),
    ("Jan Mayen cell", 70.85, -8.85, "small island", "JNM00001001"),
    ("Jan Mayen station", 70.9331, -8.6667, "small island", "JNM00001001"),
    ("Svalbard Airport", 78.25, 15.4667, "fjord coast", "SV000001008"),
    ("Ny-Alesund", 78.923, 11.9331, "fjord coast", "NOE00134778"),
    ("Svalbard north cell", 79.55, 15.30, "fjord coast", None),
    ("Iceland Vik cell", 63.45, -18.90, "open coast", None),
    ("Iceland sandur cell", 63.95, -17.50, "open coast", None),
    ("Reykjavik", 64.1269, -21.9025, "open coast", "IC000004030"),
    ("Reykjanes", 63.88, -22.45, "open coast", None),
    ("Baffin Island cell", 63.15, -64.90, "fjord coast", None),
    ("Novaya Zemlya cell", 75.35, 57.75, "open coast", None),
    ("Qaqortorsuaq anorthosite", 66.5833, -52.2, "inland", None),
    ("Fiskenaesset", 63.25, -50.0, "fjord coast", None),
    ("Lofoten Nusfjord", 68.04, 13.35, "fjord coast", None),
    ("Kangerlussuaq", 67.01, -50.70, "inland", None),
    # Not in the original site list: the best Iceland cell for the connecting ridge in the first ranking,
    # added because "no cell reaches 10 days for the connecting ridge" rested on it.
    ("Iceland northeast cell", 66.25, -15.75, "open coast", None),
]
ADDED_SITES = {"Iceland northeast cell"}
# Stations whose GHCN file lists snow depth only on days with snow: a missing report is read as bare.
REPORTS_ONLY_SNOW_DAYS = {"IC000004030"}

POWER_URL = ("https://power.larc.nasa.gov/api/temporal/daily/point?parameters=SNODP,FRSNO,T2M"
             "&community=AG&longitude={lon}&latitude={lat}&start={start}&end={end}&format=JSON")
OPEN_METEO_URL = ("https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}"
                  "&start_date={start}&end_date={end}"
                  "&daily=snow_depth_mean,snow_depth_min,snow_depth_max&models={model}&timezone=GMT")
PAUSE_S = {"power": 1.5, "openmeteo": 10.0}  # Open-Meteo weighs a ten-year call as about 75 calls; limit 600 a minute


# ---------------------------------------------------------------- downloads

def cached_json(url: str, name: str, host: str) -> dict:
    """The JSON body for url, from the cache or the network. An API error body is cached too."""
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / name
    if path.exists():
        return json.loads(path.read_text())
    if OFFLINE:
        raise FileNotFoundError(f"{name} is not in the cache and this is an offline run")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(1, 5):
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                body = response.read()
            break
        except urllib.error.HTTPError as error:
            body = error.read()
            if error.code == 429 and attempt < 4:   # rate limit: wait a minute and try again
                time.sleep(65)
                continue
            if error.code == 400 and body.startswith(b"{"):
                break                                # "no data for this location" and the like
            raise
        except (urllib.error.URLError, ConnectionError, TimeoutError):
            if attempt == 4:
                raise
            time.sleep(3 * attempt)
    part = path.with_suffix(".part")
    part.write_bytes(body)
    part.rename(path)
    time.sleep(PAUSE_S[host])
    return json.loads(body)


def tag(lat: float, lon: float) -> str:
    return f"{lat:.4f}_{lon:.4f}"


def all_dates() -> list[date]:
    return [START + timedelta(days=i) for i in range((END - START).days + 1)]


def fetch_power(lat: float, lon: float) -> dict:
    """MERRA-2 daily series: depth_cm (within the snow-covered part), cover (0 to 1), by date."""
    url = POWER_URL.format(lat=lat, lon=lon, start=START.strftime("%Y%m%d"), end=END.strftime("%Y%m%d"))
    body = cached_json(url, f"power_merra2_{tag(lat, lon)}.json", "power")
    params = body["properties"]["parameter"]
    fill = body["header"]["fill_value"]

    def series(key: str) -> np.ndarray:
        values = [params[key].get(d.strftime("%Y%m%d"), fill) for d in all_dates()]
        out = np.array(values, dtype=float)
        out[out == fill] = np.nan
        return out

    return {
        "depth_cm": series("SNODP"), "cover": series("FRSNO"), "t2m_c": series("T2M"),
        "units": {k: v["units"] for k, v in body["parameters"].items()},
        "cell_mean_elevation_m": body["geometry"]["coordinates"][2],
        "source": body["header"]["sources"], "time_standard": body["header"]["time_standard"],
    }


def fetch_open_meteo(lat: float, lon: float, model: str, end: date) -> dict | None:
    """Daily mean, min and max snow depth in cm by date, or None where the model has no data."""
    url = OPEN_METEO_URL.format(lat=lat, lon=lon, start=START.isoformat(), end=end.isoformat(), model=model)
    body = cached_json(url, f"openmeteo_{model}_{tag(lat, lon)}.json", "openmeteo")
    if body.get("error"):
        return None
    if body["daily_units"]["snow_depth_mean"] != "m":
        raise SystemExit(f"Open-Meteo unit changed: {body['daily_units']}")
    by_day = {d: i for i, d in enumerate(body["daily"]["time"])}

    def series(key: str) -> np.ndarray:
        values = body["daily"][key]
        out = np.full(len(all_dates()), np.nan)
        for j, d in enumerate(all_dates()):
            i = by_day.get(d.isoformat())
            if i is not None and values[i] is not None:
                out[j] = values[i] * 100.0
        return out

    mean = series("snow_depth_mean")
    if not np.isfinite(mean).any():
        return None
    return {
        "mean_cm": mean, "min_cm": series("snow_depth_min"), "max_cm": series("snow_depth_max"),
        "grid_lat": body["latitude"], "grid_lon": body["longitude"],
        "point_elevation_m": body.get("elevation"),
    }


# ---------------------------------------------------------------- calendar helpers

def project_doy(d: date) -> int:
    """Day of year as the project counts it (31 December of a leap year is day 365)."""
    return min(d.timetuple().tm_yday, 365)


def outside_october_to_march(day_of_year: int) -> bool:
    """Whether a day of year (common year) falls from 1 April to 30 September."""
    return stations.winter_half_of(date(2027, 1, 1) + timedelta(days=day_of_year - 1)) is None


def window_label(days: list[int]) -> str:
    return ", ".join(f"{sun.doy_to_label(a)}-{sun.doy_to_label(b)}" for a, b in sun.windows(days))


def share(values: np.ndarray, mask: np.ndarray, below: float) -> float | None:
    """Share of the masked days with a value under the limit; None when no day has data."""
    use = mask & np.isfinite(values)
    return float((values[use] < below).mean()) if use.any() else None


def mean_of(values: np.ndarray, mask: np.ndarray) -> float | None:
    use = mask & np.isfinite(values)
    return float(values[use].mean()) if use.any() else None


def by_winter(values: np.ndarray, mask: np.ndarray, snow_years: np.ndarray, below: float) -> list:
    """The share for each snow year (1 October to 30 September) on its own."""
    return [share(values, mask & (snow_years == w), below) for w in WINTERS]


def summer_minimum(values: np.ndarray, dates: list[date]) -> float | None:
    """Median over the summers of the lowest July-to-September value: above zero means perennial snow."""
    lows = []
    for year in range(START.year + 1, END.year):
        pick = np.array([d.year == year and 7 <= d.month <= 9 for d in dates]) & np.isfinite(values)
        if pick.any():
            lows.append(float(values[pick].min()))
    return float(np.median(lows)) if lows else None


def rounded(value, digits: int = 3):
    if isinstance(value, list):
        return [rounded(v, digits) for v in value]
    return None if value is None else round(float(value), digits)


# ---------------------------------------------------------------- the project's own layer

def ims_land_share(probabilities, row0, col0, lat_c, lon_c, half_lat, half_lon) -> float | None:
    """Share of a lat/lon box that the IMS grid ever saw as land (a 4 km estimate of land fraction)."""
    lats = np.linspace(lat_c - half_lat, lat_c + half_lat, 41)[1:-1]
    lons = np.linspace(lon_c - half_lon, lon_c + half_lon, 41)[1:-1]
    grid_lat, grid_lon = np.meshgrid(lats, lons)
    rows, cols = snow.ims_rowcol(grid_lat.ravel(), grid_lon.ravel())
    r, c = rows.astype(int) - row0, cols.astype(int) - col0
    n = probabilities.shape[1]
    inside = (r >= 0) & (r < n) & (c >= 0) & (c < n)
    if not inside.any():
        return None
    land = np.isfinite(probabilities[:, r[inside], c[inside]]).any(axis=0)
    return float(land.mean())


def ims_daily_blocks(sites) -> tuple[list[date], dict[str, np.ndarray]] | None:
    """Per cached IMS map: the share of land pixels in each site's 3 x 3 block that are snow-free."""
    from rasterio.io import MemoryFile

    files = sorted(IMS_DIR.glob("ims*_4km_GIS_v1.3.tif.gz"))
    if not files:
        return None
    pixels = []
    for _, lat, lon, _, _ in sites:
        rows, cols = snow.ims_rowcol([lat], [lon])
        pixels.append((int(rows[0]), int(cols[0])))
    r0, r1 = min(p[0] for p in pixels) - 1, max(p[0] for p in pixels) + 2
    c0, c1 = min(p[1] for p in pixels) - 1, max(p[1] for p in pixels) + 2
    days, shares = [], {name: [] for name, *_ in sites}
    for path in files:
        year, doy = map(int, re.match(r"ims(\d{4})(\d{3})_", path.name).groups())
        with gzip.open(path, "rb") as zipped, MemoryFile(zipped.read()) as memory, memory.open() as ds:
            day = ds.read(1, window=((r0, r1), (c0, c1)))
        days.append(date(year, 1, 1) + timedelta(days=doy - 1))
        for (name, *_), (r, c) in zip(sites, pixels):
            block = day[r - 1 - r0:r + 2 - r0, c - 1 - c0:c + 2 - c0]
            free, snowy = (block == snow.SNOW_FREE_LAND).sum(), (block == snow.SNOW_LAND).sum()
            shares[name].append(free / (free + snowy) if free + snowy else np.nan)
    return days, {name: np.array(v) for name, v in shares.items()}


def ims_persistence(days: list[date], block_share: np.ndarray) -> dict:
    """How often the IMS state around a site changes: a stuck analysis shows whole winters in one state.

    A winter here is the one of the snow layer's stale-flag rule, 1 October to 20 March
    (snow.winter_of), so the counts can be set beside the layer's stuck winters.
    """
    def rule_winter(d: date) -> int:
        winter = snow.winter_of(d.year, d.timetuple().tm_yday)
        return -1 if winter is None else winter

    winters = np.array([rule_winter(d) for d in days])
    all_free, all_snow, changes = [], [], []
    for w in WINTERS:
        v = block_share[(winters == w) & np.isfinite(block_share)]
        if not len(v):
            continue
        if (v == 1.0).all():
            all_free.append(w)
        if (v == 0.0).all():
            all_snow.append(w)
        changes.append(int((np.diff(v) != 0).sum()))
    return {
        "maps_per_winter": int(np.median([(winters == w).sum() for w in WINTERS])),
        "winters_snow_free_on_every_map": all_free,
        "winters_snow_on_every_map": all_snow,
        "state_changes_per_winter": changes,
    }


# ---------------------------------------------------------------- stations

def station_bins() -> tuple[dict[str, np.ndarray], list[str]]:
    """Station snow-free share per calendar ten-day bin from the project's own station check (validate_snow.py).

    Also returns the stations whose entry is stale: written before the bins became
    calendar bins (18 values from 1 October). Those are left out rather than misread.
    """
    if not STATION_CHECK.exists():
        return {}, []
    out, stale = {}, []
    for entry in json.loads(STATION_CHECK.read_text()):
        if len(entry["station_share"]) != snow.N_BINS:
            stale.append(entry["station"])
            continue
        out[entry["station"]] = np.array([np.nan if v is None else v for v in entry["station_share"]])
    return out, stale


def station_no_report_is_bare(station_id: str, days: set[int]) -> float | None:
    """Share of window days without a positive snow depth report (for stations that report only snow)."""
    path = GHCN_DIR / f"{station_id}.csv"
    if not path.exists():
        return None
    snowy = set()
    with open(path, newline="") as handle:
        for row in csv.DictReader(handle):
            value = (row.get("SNWD") or "").strip()
            if value and int(value) > 0:
                snowy.add(row["DATE"])
    window = [d for d in all_dates() if project_doy(d) in days]
    return 1.0 - sum(d.isoformat() in snowy for d in window) / len(window) if window else None


# ---------------------------------------------------------------- main

def main() -> None:
    global OFFLINE
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--offline", action="store_true", help="use the cache only; never download")
    OFFLINE = parser.parse_args().offline
    targets = json.loads(TARGETS.read_text())
    archive = np.load(SNOW)
    probabilities, row0, col0 = archive["probabilities"], int(archive["row0"]), int(archive["col0"])
    as_mapped_crop = archive["probabilities_as_mapped"] if "probabilities_as_mapped" in archive.files else None
    dates = all_dates()
    doys = np.array([project_doy(d) for d in dates])
    snow_years = np.array([stations.snow_year_of(d) for d in dates])
    in_winter = np.array([stations.winter_half_of(d) is not None for d in dates])   # 1 October to 31 March
    station_shares, stale_stations = station_bins()
    ims_maps = ims_daily_blocks(SITES)
    failed, site_records, rows = [], [], []

    for name, lat, lon, kind, station_id in SITES:
        print(f"{name} ({lat}, {lon})", flush=True)
        record = {"site": name, "lat": lat, "lon": lon, "kind": kind, "added_to_site_list": name in ADDED_SITES,
                  "ims_land_pixels_of_9": snow.cell_land_pixels(probabilities, row0, col0, lat, lon)}
        local = snow.cell_probabilities(probabilities, row0, col0, lat, lon)
        as_mapped = (np.full(snow.N_BINS, np.nan) if as_mapped_crop is None
                     else snow.cell_probabilities(as_mapped_crop, row0, col0, lat, lon))
        record["ims_snow_free_by_bin"] = rounded([None if np.isnan(v) else v for v in local])
        record["ims_snow_free_as_mapped_by_bin"] = rounded([None if np.isnan(v) else v for v in as_mapped])
        record["ims_stuck_winters"] = snow.cell_stuck_winters(archive["stuck_winters"], row0, col0, lat, lon)

        try:
            merra = fetch_power(lat, lon)
        except Exception as error:  # noqa: BLE001 - one bad site must not stop the rest
            merra = None
            failed.append(f"NASA POWER (MERRA-2) at {name}: {error}")
        if merra:
            if merra["units"]["SNODP"] != "cm":
                raise SystemExit(f"NASA POWER unit changed: {merra['units']}")
            # SNODP is the depth inside the snow-covered part of the land tile; times FRSNO it is the tile mean.
            merra["tile_mean_cm"] = merra["depth_cm"] * merra["cover"]
            cell_lat = round(lat / 0.5) * 0.5
            cell_lon = round((lon + 180.0) / 0.625) * 0.625 - 180.0
            record["merra2"] = {
                "grid": "0.5 x 0.625 degree", "nominal_cell_centre": [cell_lat, round(cell_lon, 3)],
                "cell_mean_elevation_m": merra["cell_mean_elevation_m"],
                "cell_land_share_ims_mask": rounded(ims_land_share(
                    probabilities, row0, col0, cell_lat, cell_lon, 0.25, 0.3125), 2),
                "days_with_data": int(np.isfinite(merra["depth_cm"]).sum()),
                "summer_minimum_depth_cm": rounded(summer_minimum(merra["depth_cm"], dates), 1),
                "smallest_nonzero_depth_cm": rounded(float(np.nanmin(
                    np.where(merra["depth_cm"] > 0, merra["depth_cm"], np.nan))), 2)
                if (merra["depth_cm"] > 0).any() else None,
            }

        grids = {}
        for model, end in (("era5_land", END), ("cerra", CERRA_END)):
            try:
                grids[model] = fetch_open_meteo(lat, lon, model, end)
            except Exception as error:  # noqa: BLE001
                grids[model] = None
                failed.append(f"Open-Meteo {model} at {name}: {error}")
            data = grids[model]
            if data is None:
                record[model] = None
                continue
            low = summer_minimum(data["mean_cm"], dates)
            data["perennial"] = low is not None and low >= PERENNIAL_CM
            half = 0.05 if model == "era5_land" else None
            record[model] = {
                "grid": "0.1 degree" if model == "era5_land" else "5.5 km",
                "grid_cell": [round(data["grid_lat"], 3), round(data["grid_lon"], 3)],
                "grid_cell_distance_km": rounded(reference.haversine_km(
                    lat, lon, data["grid_lat"], data["grid_lon"]), 1),
                "cell_land_share_ims_mask": rounded(ims_land_share(
                    probabilities, row0, col0, data["grid_lat"], data["grid_lon"], half, half), 2) if half else None,
                "point_elevation_m": data["point_elevation_m"],
                "days_with_data": int(np.isfinite(data["mean_cm"]).sum()),
                "summer_minimum_depth_cm": rounded(low, 1),
                "perennial_snow_cell": data["perennial"],
                "winter_median_depth_cm": rounded(float(np.nanmedian(data["mean_cm"][in_winter])), 1),
            }

        if ims_maps:
            record["ims_persistence"] = ims_persistence(ims_maps[0], ims_maps[1][name])
        site_records.append(record)

        for target in targets:
            limit = target["sun_max_elev_deg"]
            days = sun.low_sun_days(lat, limit)
            if not days:
                continue
            day_set = set(days)
            # Every source is scored on the same days of year: all window days, whatever the month.
            mask = np.array([d in day_set for d in doys])
            ims_share = snow.snow_free_share(local, days)
            row = {
                "site": name, "lat": lat, "lon": lon, "kind": kind,
                "target": target["id"], "sun_limit_deg": round(limit, 2),
                "window": window_label(days), "light_days": len(days),
                "window_days_outside_october_to_march": sum(outside_october_to_march(d) for d in days),
                "window_days_without_ims_odds": sum(not np.isfinite(local[snow.bin_index(d)]) for d in days),
                "dates_scored": int(mask.sum()),
                "ims": {"snow_free": rounded(ims_share),
                        "snow_free_as_mapped": rounded(snow.snow_free_share(as_mapped, days)),
                        "usable_days": rounded(None if ims_share is None else ims_share * len(days), 1)},
            }
            if ims_maps:
                map_days, block = ims_maps[0], ims_maps[1][name]
                per_winter = []
                for w in WINTERS:
                    pick = np.array([stations.snow_year_of(d) == w and project_doy(d) in day_set for d in map_days])
                    pick &= np.isfinite(block)
                    per_winter.append(float(block[pick].mean()) if pick.any() else None)
                row["ims"]["by_winter"] = rounded(per_winter, 2)
            if merra:
                under = {f"lt_{int(t)}cm": rounded(share(merra["depth_cm"], mask, t)) for t in THRESHOLDS_CM}
                tile = {f"tile_mean_lt_{int(t)}cm": rounded(share(merra["tile_mean_cm"], mask, t))
                        for t in THRESHOLDS_CM}
                bare = mean_of(1.0 - merra["cover"], mask)
                row["merra2"] = {
                    **under, **tile,
                    "mean_bare_land_fraction": rounded(bare),
                    "cover_under_half": rounded(share(merra["cover"], mask, 0.5)),
                    "median_depth_cm": rounded(float(np.nanmedian(merra["depth_cm"][mask])), 1),
                    "mean_t2m_c": rounded(mean_of(merra["t2m_c"], mask), 1),
                    "usable_days_lt_1cm": rounded(
                        None if under["lt_1cm"] is None else under["lt_1cm"] * len(days), 1),
                    "usable_days_tile_mean_lt_1cm": rounded(
                        None if tile["tile_mean_lt_1cm"] is None else tile["tile_mean_lt_1cm"] * len(days), 1),
                    "by_winter_lt_1cm": rounded(by_winter(merra["depth_cm"], mask, snow_years, 1.0), 2),
                    "by_winter_tile_mean_lt_1cm": rounded(by_winter(merra["tile_mean_cm"], mask, snow_years, 1.0), 2),
                }
            for model in ("era5_land", "cerra"):
                data = grids[model]
                if data is None:
                    row[model] = None
                    continue
                under = {f"lt_{int(t)}cm": rounded(share(data["mean_cm"], mask, t)) for t in THRESHOLDS_CM}
                valid = mask & np.isfinite(data["mean_cm"])
                row[model] = {
                    **under,
                    "daily_max_lt_1cm": rounded(share(data["max_cm"], mask, 1.0)),
                    "daily_min_lt_1cm": rounded(share(data["min_cm"], mask, 1.0)),
                    "median_depth_cm": rounded(float(np.nanmedian(data["mean_cm"][valid])), 1) if valid.any() else None,
                    "dates_scored": int(valid.sum()),
                    "usable_days_lt_1cm": rounded(None if under["lt_1cm"] is None else under["lt_1cm"] * len(days), 1),
                    "by_winter_lt_1cm": rounded(by_winter(data["mean_cm"], mask, snow_years, 1.0), 2),
                    "perennial_snow_cell": data["perennial"],
                }
            # The same shares for each run of days on its own: autumn and late-winter windows differ a lot.
            runs = []
            for first, last in sun.windows(days):
                run_days = [d for d in days if (first <= d <= last if first <= last else d >= first or d <= last)]
                run_mask = np.isin(doys, run_days)
                run = {"window": f"{sun.doy_to_label(first)}-{sun.doy_to_label(last)}", "light_days": len(run_days),
                       "ims": rounded(snow.snow_free_share(local, run_days), 2)}
                if merra:
                    run["merra2_tile_mean_lt_1cm"] = rounded(share(merra["tile_mean_cm"], run_mask, 1.0), 2)
                    run["merra2_mean_bare_land_fraction"] = rounded(mean_of(1.0 - merra["cover"], run_mask), 2)
                for model in ("era5_land", "cerra"):
                    if grids[model] is not None and not grids[model]["perennial"]:
                        for t in THRESHOLDS_CM:
                            run[f"{model}_lt_{int(t)}cm"] = rounded(share(grids[model]["mean_cm"], run_mask, t), 2)
                runs.append(run)
            row["by_run"] = runs
            if station_id and station_id in station_shares:
                value = snow.snow_free_share(station_shares[station_id], days)
                row["station"] = {"id": station_id, "snow_free_from_ten_day_bins": rounded(value)}
                if station_id in REPORTS_ONLY_SNOW_DAYS:
                    row["station"]["snow_free_if_no_report_means_bare"] = rounded(
                        station_no_report_is_bare(station_id, day_set))
            rows.append(row)

    # One line per site: each measure averaged over the targets that have a window there.
    def averaged(site: str, pick) -> float | None:
        values = [pick(r) for r in rows if r["site"] == site]
        values = [v for v in values if v is not None]
        return round(sum(values) / len(values), 2) if values else None

    def grid_value(model: str, key: str):
        return lambda r: None if r.get(model) is None or r[model]["perennial_snow_cell"] else r[model][key]

    site_summary = []
    for name, _, _, kind, _ in SITES:
        site_summary.append({
            "site": name, "kind": kind,
            "ims": averaged(name, lambda r: r["ims"]["snow_free"]),
            "merra2_snodp_lt_1cm": averaged(name, lambda r: (r.get("merra2") or {}).get("lt_1cm")),
            "merra2_tile_mean_lt_1cm": averaged(name, lambda r: (r.get("merra2") or {}).get("tile_mean_lt_1cm")),
            "merra2_tile_mean_lt_5cm": averaged(name, lambda r: (r.get("merra2") or {}).get("tile_mean_lt_5cm")),
            "merra2_mean_bare_land_fraction": averaged(
                name, lambda r: (r.get("merra2") or {}).get("mean_bare_land_fraction")),
            "era5_land_lt_1cm": averaged(name, grid_value("era5_land", "lt_1cm")),
            "era5_land_lt_5cm": averaged(name, grid_value("era5_land", "lt_5cm")),
            "cerra_lt_1cm": averaged(name, grid_value("cerra", "lt_1cm")),
            "cerra_lt_5cm": averaged(name, grid_value("cerra", "lt_5cm")),
            "station": averaged(name, lambda r: r.get("station", {}).get(
                "snow_free_if_no_report_means_bare", r.get("station", {}).get("snow_free_from_ten_day_bins"))),
        })

    side = OUT.with_suffix(".part.json")
    side.write_text(json.dumps({
        "written_by": "scripts/second_opinion_snow.py",
        "offline_run": OFFLINE,
        "period": [START.isoformat(), END.isoformat()],
        "winters": WINTERS,
        "ims_maps": None if not ims_maps else {"files": len(ims_maps[0]), "first": min(ims_maps[0]).isoformat(),
                                               "last": max(ims_maps[0]).isoformat()},
        "station_check_entries_left_out_as_stale": stale_stations,
        "definition": {
            "window": "days of year from twinfinder.sun.low_sun_days(lat, target Sun limit): the all-day low-Sun "
                      "days, with refraction; every such calendar date in the period is scored, by every source",
            "bins": "36 calendar ten-day bins; bin 0 is 1 to 10 January, bin 35 is 17 to 31 December",
            "winters": "lists named by_winter hold one value per snow year (1 October to 30 September, named by "
                       "its October); ims_persistence alone uses the winter of the stale-flag rule, 1 October "
                       "to 20 March",
            "periods": "reanalysis: the period above; IMS odds: maps from 1 October 2015 to 28 September 2025",
            "snow_free": "daily snow depth under 1 cm (also given at 5 cm)",
            "merra2": "NASA POWER SNODP in cm (daily mean, MERRA-2 land tiles, local solar day). SNODP is the "
                      "depth inside the snow-covered part of the tile, so tile_mean = SNODP x FRSNO is also given, "
                      "with the mean bare-land fraction 1 - FRSNO and the share of days with FRSNO under 0.5",
            "era5_land": "Open-Meteo snow_depth_mean in m, served to 0.01 m: 'under 1 cm' means it reads 0.00",
            "cerra": "as ERA5-Land, six winters only (archive ends June 2021), Europe and nearby only",
            "ims": "the project's value: twinfinder.snow.cell_probabilities then snow_free_share, with the "
                   "stale-flag rule; snow_free_as_mapped is the same without the rule",
            "station": "snow_validation.json ten-day-bin shares (every bin with any report) averaged over the "
                       "window days",
            "perennial_snow_cell": f"median July-September minimum depth of {PERENNIAL_CM:.0f} cm or more: "
                                   "the model never melts its snow there, so its winter value says nothing",
        },
        "sources_failed": failed,
        "site_summary": site_summary,
        "sites": site_records,
        "rows": rows,
    }, indent=1))
    side.rename(OUT)

    print("\nShare of low-Sun days with snow-free ground, ten winters (- = no data, P = perennial-snow cell)")
    print(f"{'site':26s}{'target':17s}{'days':>4s} {'IMS':>5s} | {'MERRA-2':^29s} | {'ERA5-Land':^11s} | "
          f"{'CERRA':^11s} | station")
    print(f"{'':52s} | {'<1cm':>5s} {'<5cm':>5s} {'tm<1':>5s} {'bare':>5s} {'c<.5':>5s} | "
          f"{'<1cm':>5s} {'<5cm':>5s} | {'<1cm':>5s} {'<5cm':>5s} |")

    def cell(value) -> str:
        return "    -" if value is None else f"{value:5.2f}"

    for row in rows:
        merra = row.get("merra2") or {}
        parts = [cell(merra.get(k)) for k in
                 ("lt_1cm", "lt_5cm", "tile_mean_lt_1cm", "mean_bare_land_fraction", "cover_under_half")]
        grids_text = []
        for model in ("era5_land", "cerra"):
            data = row.get(model)
            if data is None:
                grids_text.append("    -     -")
            elif data["perennial_snow_cell"]:
                grids_text.append("    P     P")
            else:
                grids_text.append(f"{cell(data['lt_1cm'])} {cell(data['lt_5cm'])}")
        station = row.get("station", {})
        station_text = cell(station.get("snow_free_from_ten_day_bins")) if station else ""
        if "snow_free_if_no_report_means_bare" in station:
            station_text += f" (no report = bare: {station['snow_free_if_no_report_means_bare']:.2f})"
        print(f"{row['site']:26s}{row['target']:17s}{row['light_days']:4d} {cell(row['ims']['snow_free'])} | "
              f"{' '.join(parts)} | {grids_text[0]} | {grids_text[1]} | {station_text}")
    print("\nPer site, averaged over its targets (MERRA-2 tile mean = SNODP x FRSNO; station for Reykjavik reads "
          "a missing report as bare)")
    print(f"{'site':26s}{'kind':13s}{'IMS':>5s} | {'M2<1':>5s} {'M2<5':>5s} {'bare':>5s} | {'E5L<1':>5s} {'E5L<5':>5s} | "
          f"{'CER<1':>5s} {'CER<5':>5s} | {'stn':>5s}")
    for line in site_summary:
        print(f"{line['site']:26s}{line['kind']:13s}{cell(line['ims'])} | {cell(line['merra2_tile_mean_lt_1cm'])} "
              f"{cell(line['merra2_tile_mean_lt_5cm'])} {cell(line['merra2_mean_bare_land_fraction'])} | "
              f"{cell(line['era5_land_lt_1cm'])} {cell(line['era5_land_lt_5cm'])} | "
              f"{cell(line['cerra_lt_1cm'])} {cell(line['cerra_lt_5cm'])} | {cell(line['station'])}")
    if failed:
        print("\nFailed requests:")
        for line in failed:
            print("  " + line)
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()

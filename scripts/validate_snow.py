# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Check the satellite snow layer against weather-station snow depth at sites that matter to the ranking.

Year-round, in the 36 calendar ten-day bins of the snow layer (bin 0 = 1 to 10 January).
Station shares are given twice: over every bin with any report, and only over bins the
station reported on 80% of their days (these five stations report unevenly; Reykjavik
writes snow depth down on snow days only, so its share from reports alone is not a
snow-free share). The satellite odds are given with the stale-flag rule (the project's
odds) and as mapped (without it).
"""
import json
from pathlib import Path

import numpy as np

from twinfinder import snow, stations
from twinfinder import station_select as sel
from twinfinder.fetch import fetch

SNOW = Path("data/derived/snow_free_dekads.npz")
OUT = Path("data/derived/snow_validation.json")
GHCN_DIR = Path("data/raw/ghcn")
FIRST_YEAR, LAST_YEAR = 2015, 2024  # snow years (1 October to 30 September): the same ten as the satellite maps
STATIONS = [
    ("NO000099710", "Bear Island (Bjornoya)", 74.5167, 19.0167),
    ("JNM00001001", "Jan Mayen", 70.9331, -8.6667),
    ("SV000001008", "Svalbard Airport", 78.25, 15.4667),
    ("NOE00134778", "Ny-Alesund, Svalbard", 78.923, 11.9331),
    ("IC000004030", "Reykjavik, Iceland", 64.1269, -21.9025),
]
HALF_YEARS = {"winter_half": stations.WINTER_HALF_BINS, "summer_half": stations.SUMMER_HALF_BINS}
BLOCK = snow.N_BINS // 2   # bins per printed block


def row(values) -> str:
    return " ".join("    -" if np.isnan(v) else f"{v:5.2f}" for v in values)


def nullable(values) -> list:
    return [None if np.isnan(v) else round(float(v), 3) for v in values]


def print_station(name: str, lat: float, lon: float, reports, series: dict) -> None:
    """One station's rows in two blocks of 18 bins, each bin named by its first day."""
    print(f"\n{name} ({lat:.2f}, {lon:.2f}); station reports in those snow years: {int(reports.sum())}")
    for start in range(0, snow.N_BINS, BLOCK):
        bins = range(start, start + BLOCK)
        print(" " * 24 + " ".join(f"{stations.bin_label(index):>5s}" for index in bins))
        for label, values in series.items():
            print(f"  {label:21s} {row(values[start:start + BLOCK])}")
        print(f"  {'station reports':21s} " + " ".join(f"{int(n):5d}" for n in reports[start:start + BLOCK]))


def main() -> None:
    archive = np.load(SNOW)
    probabilities, row0, col0 = archive["probabilities"], int(archive["row0"]), int(archive["col0"])
    as_mapped_crop = archive["probabilities_as_mapped"] if "probabilities_as_mapped" in archive.files else None
    possible = stations.days_per_bin(range(FIRST_YEAR, LAST_YEAR + 1))
    results = []
    for station_id, name, lat, lon in STATIONS:
        text = fetch(stations.station_url(station_id), GHCN_DIR).read_text()
        records = stations.parse_snow_depth(text)
        station_share, reports = stations.snow_free_by_bin(records, FIRST_YEAR, LAST_YEAR)
        complete = np.where(sel.complete_bins(reports, possible), station_share, np.nan)
        satellite = snow.cell_probabilities(probabilities, row0, col0, lat, lon)
        as_mapped = (np.full(snow.N_BINS, np.nan) if as_mapped_crop is None
                     else snow.cell_probabilities(as_mapped_crop, row0, col0, lat, lon))
        print_station(name, lat, lon, reports, {"satellite": satellite, "satellite as mapped": as_mapped,
                                                "station, any report": station_share,
                                                "station, complete bins": complete})
        result = {"station": station_id, "name": name, "lat": lat, "lon": lon, "reports": int(reports.sum()),
                  "bins": "36 calendar ten-day bins; bin 0 is 1 to 10 January, bin 35 is 17 to 31 December",
                  "satellite": nullable(satellite), "satellite_as_mapped": nullable(as_mapped),
                  "station_share": nullable(station_share), "station_share_complete_bins": nullable(complete),
                  "reports_by_bin": [int(n) for n in reports],
                  "stuck_winters": snow.cell_stuck_winters(archive["stuck_winters"], row0, col0, lat, lon)}
        for label, share in (("", station_share), ("_complete_bins", complete)):
            whole = sel.summarise(satellite, share)
            result.update({f"mean_bias{label}": whole["mean_bias"],
                           f"mean_abs_difference{label}": whole["mean_abs_difference"]})
            for half, bins in HALF_YEARS.items():
                result[f"{half}{label}"] = {
                    "bins": stations.bin_span(bins),
                    **sel.summarise(satellite[bins], share[bins]),
                    "mean_bias_as_mapped": sel.summarise(as_mapped[bins], share[bins])["mean_bias"]}
        if result["mean_bias"] is None:
            print("  no overlapping bins")
        else:
            print(f"  satellite minus station (any report): mean {result['mean_bias']:+.2f}, "
                  f"mean absolute {result['mean_abs_difference']:.2f}")
            for half in HALF_YEARS:
                part, strict = result[half], result[f"{half}_complete_bins"]
                if part["n"]:
                    line = f"    {half.replace('_', ' ')}: {part['n']} bins, mean {part['mean_bias']:+.2f}"
                    if part["mean_bias_as_mapped"] is not None:
                        line += f" (as mapped {part['mean_bias_as_mapped']:+.2f})"
                    if strict["n"]:
                        line += f"; complete bins only: {strict['n']} bins, mean {strict['mean_bias']:+.2f}"
                    print(line)
        results.append(result)
    side = OUT.with_suffix(".part.json")
    side.write_text(json.dumps(results, indent=1))
    side.rename(OUT)
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()

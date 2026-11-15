# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Download the lunar files and write data/derived/moon_targets.json."""
import json
from pathlib import Path

import rasterio

from twinfinder import moon
from twinfinder.fetch import fetch

OUT = Path("data/derived/moon_targets.json")


def main() -> None:
    illum = fetch(moon.ILLUMINATION_URL)
    psr = fetch(moon.PSR_URL)
    for path in (illum, psr):
        with rasterio.open(path) as ds:
            print(f"{path.name}: {ds.width}x{ds.height} px at {ds.res[0]} m, CRS {ds.crs.to_string()[:90]}")
    results = []
    for target in moon.TARGETS:
        if not target.has_model:
            fp = moon.fingerprint_without_model(target, illum, psr)
            results.append(fp)
            shadow = "unknown" if fp["permanent_shadow_fraction"] is None else f"{fp['permanent_shadow_fraction']:.1%}"
            print(f"{target.id}: no NASA 5 m terrain model; centre {fp['centre_lat']:.2f}, {fp['centre_lon']:.1f}E "
                  f"({fp['position_how_sure']}) | Sun max {fp['sun_max_elev_deg']:.2f} deg | shadow {shadow}"
                  f" | slope figures unknown")
            continue
        dem = fetch(target.dem_url)
        with rasterio.open(dem) as ds:
            print(f"{target.pgda_site}: {ds.width}x{ds.height} px at {ds.res[0]} m, CRS {ds.crs.to_string()[:90]}")
        fp = moon.fingerprint(target, dem, illum, psr)
        results.append(fp)
        t90 = fp["terrain"]["90m"]
        print(f"  centre {fp['centre_lat']:.2f}, {fp['centre_lon']:.1f}E | Sun max {fp['sun_max_elev_deg']:.1f} deg"
              f" | median slope {t90['median_slope_deg']:.1f} deg | p90 {t90['p90_slope_deg']:.1f} deg"
              f" | relief {t90['relief_m']:.0f} m | shadow {fp['permanent_shadow_fraction']:.1%}"
              f" | sunlit share of time: mean {fp['illumination_mean']:.0%}, best spot {fp['illumination_max']:.0%}")
        own = t90["self_overlap_10km"]
        if own["median"] is None:
            print("  the site is smaller than one 10 km piece: no slope overlap with itself")
        else:
            print(f"  10 km pieces of the site against the whole site (slope overlap): "
                  f"p10 {own['p10']:.3f}, median {own['median']:.3f}, p90 {own['p90']:.3f}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, indent=1))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()

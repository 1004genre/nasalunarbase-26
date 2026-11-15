# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Time the no-login terrain route and compare four Earth cells with the lunar targets."""
import json
import time
from pathlib import Path

import numpy as np

from twinfinder import earth, terrain

CELLS = [
    ("Qaqortorsuaq, Greenland (approx.)", 66.5, -52.1),
    ("Reykjanes, Iceland", 63.88, -22.45),
    ("Lofoten, Norway", 68.2, 14.0),
    ("Mistastin, Labrador", 55.89, -63.31),
]


def main() -> None:
    targets = json.loads(Path("data/derived/moon_targets.json").read_text())
    for name, lat, lon in CELLS:
        start = time.perf_counter()
        z = earth.elevation_window(lat, lon)
        z = np.where(z <= 0.0, np.nan, z)  # drop sea surface
        summary = terrain.terrain_summary(z, 90.0)
        seconds = time.perf_counter() - start
        land = float(np.isfinite(z).mean())
        print(f"\n{name}: {seconds:.1f} s, land {land:.0%}, median slope "
              f"{summary['median_slope_deg']:.1f} deg, relief {summary['relief_m']:.0f} m")
        for t in targets:
            overlap = terrain.histogram_overlap(
                np.array(summary["slope_hist"]), np.array(t["terrain"]["90m"]["slope_hist"]))
            print(f"  terrain overlap with {t['name']:42s} {overlap:.2f}")


if __name__ == "__main__":
    main()

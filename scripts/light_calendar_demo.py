# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Print when named Earth places get lunar-south-pole Sun angles."""
import json
from pathlib import Path

from twinfinder import sun

PLACES = [
    ("Qaqortorsuaq anorthosite, Greenland (approx.)", 66.5),
    ("Fiskenaesset anorthosite, Greenland", 63.2),
    ("Reykjanes lava fields, Iceland", 63.9),
    ("Lofoten anorthosite, Norway", 68.2),
    ("Longyearbyen, Svalbard", 78.2),
    ("Haughton crater, Devon Island", 75.4),
    ("Mistastin crater, Labrador", 55.9),
    ("McMurdo Dry Valleys, Antarctica", -77.5),
    ("Lake Untersee / Eliseev massif, Antarctica", -71.3),
]


def describe(lat: float, max_elev: float) -> str:
    days = sun.low_sun_days(lat, max_elev)
    spans = ", ".join(f"{sun.doy_to_label(a)} to {sun.doy_to_label(b)}" for a, b in sun.windows(days))
    return f"{len(days):3d} days  {spans or 'never'}"


def main() -> None:
    targets = json.loads(Path("data/derived/moon_targets.json").read_text())
    for t in targets:
        limit = t["sun_max_elev_deg"]
        print(f"\n{t['name']}: Sun never above {limit:.1f} deg")
        for name, lat in PLACES:
            print(f"  {name:48s} {describe(lat, limit)}")


if __name__ == "__main__":
    main()

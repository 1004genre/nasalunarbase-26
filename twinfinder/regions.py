# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Rough region names for a point north of 59N or south of 59S, from latitude and longitude boxes.

These are reading aids for ranked tables, not authoritative geography: boxes
overlap at coasts and straits, and the first match wins. A southern point in
no box is "Antarctica".
"""
from __future__ import annotations

from twinfinder.grid import SOUTH_MAX_LAT

# (name, south, north, west, east)
BOXES = [
    ("Jan Mayen", 70.7, 71.3, -9.2, -7.8),
    ("Bear Island (Bjornoya)", 74.3, 74.6, 18.6, 19.5),
    ("Iceland", 63.0, 67.0, -25.0, -13.0),
    ("Faroe Islands", 61.3, 62.5, -7.8, -6.2),
    ("Shetland and Orkney", 58.6, 61.0, -3.6, 0.0),
    ("Svalbard", 76.0, 81.0, 10.0, 35.0),
    ("Franz Josef Land", 79.5, 82.0, 44.0, 66.0),
    ("Novaya Zemlya", 70.0, 77.5, 50.0, 70.0),
    ("Severnaya Zemlya", 78.0, 81.5, 90.0, 107.0),
    ("Norway, Sweden or Finland", 59.0, 71.5, 4.0, 32.0),
    ("Kola and north-west Russia", 59.0, 70.5, 32.0, 60.0),
    ("Siberia and the Russian Far East", 59.0, 78.0, 60.0, 180.0),
    ("Chukotka", 59.0, 72.0, -180.0, -168.5),
    ("Alaska", 59.0, 71.5, -168.5, -141.0),
    ("North-west Greenland or Ellesmere", 76.0, 84.0, -73.0, -61.0),
    ("Arctic Canada", 59.0, 84.0, -141.0, -61.0),
    ("Greenland", 59.0, 84.0, -61.0, -10.0),
    ("South Sandwich Islands", -59.6, -56.0, -28.5, -26.0),
    ("South Orkney Islands", -61.1, -60.3, -47.5, -44.0),
    ("Antarctic Peninsula and South Shetlands", -75.0, -60.5, -80.0, -53.0),
    ("Dronning Maud Land", -78.0, -65.0, -20.0, 45.0),
    ("Enderby and Mac.Robertson Land", -77.0, -65.0, 45.0, 73.0),
    ("Princess Elizabeth Land", -77.0, -65.0, 73.0, 88.0),            # Vestfold and Larsemann Hills
    ("Wilkes Land", -78.0, -64.0, 99.0, 136.0),                       # Bunger Hills, Windmill Islands
    ("Victoria Land", -78.5, -70.0, 154.0, 172.0),                    # Dry Valleys, Terra Nova Bay
    ("Transantarctic Mountains", -90.0, -78.5, 150.0, 180.0),         # Britannia to Queen Alexandra Range
    ("Transantarctic Mountains", -90.0, -83.0, -180.0, -85.0),        # Queen Maud, Horlick and Thiel Mountains
    ("Transantarctic Mountains", -86.0, -82.0, -70.0, -40.0),         # Pensacola Mountains
    ("Ellsworth Mountains", -81.0, -77.0, -92.0, -78.0),
]


def region(lat: float, lon: float) -> str:
    for name, south, north, west, east in BOXES:
        if south <= lat <= north and west <= lon <= east:
            return name
    return "Antarctica" if lat <= SOUTH_MAX_LAT else "Unnamed region"

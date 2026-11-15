# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
import pytest
from twinfinder.regions import region


@pytest.mark.parametrize("lat, lon, expected", [
    (64.1, -21.9, "Iceland"),                               # Reykjavik
    (78.2, 15.6, "Svalbard"),                               # Longyearbyen
    (64.2, -51.7, "Greenland"),                             # Nuuk
    (69.6, 18.9, "Norway, Sweden or Finland"),              # Tromso
    (64.8, -147.7, "Alaska"),                               # Fairbanks
    (63.7, -68.5, "Arctic Canada"),                         # Iqaluit
    (62.0, -6.8, "Faroe Islands"),                          # Torshavn
    (68.9, 33.1, "Kola and north-west Russia"),             # Murmansk
    (62.0, 129.7, "Siberia and the Russian Far East"),      # Yakutsk
    (71.0, -8.5, "Jan Mayen"),
    (74.45, 19.25, "Bear Island (Bjornoya)"),
])
def test_region_names(lat, lon, expected):
    assert region(lat, lon) == expected


def test_point_outside_every_box():
    assert region(40.0, 0.0) == "Unnamed region"


@pytest.mark.parametrize("lat, lon, expected", [
    (-62.2, -58.95, "Antarctic Peninsula and South Shetlands"),    # Fildes Peninsula
    (-62.95, -60.6, "Antarctic Peninsula and South Shetlands"),    # Deception Island
    (-63.85, -57.9, "Antarctic Peninsula and South Shetlands"),    # James Ross Island
    (-64.25, -56.65, "Antarctic Peninsula and South Shetlands"),   # Seymour Island
    (-67.57, -68.13, "Antarctic Peninsula and South Shetlands"),   # Rothera
    (-71.0, -68.5, "Antarctic Peninsula and South Shetlands"),     # Alexander Island
    (-60.7, -45.6, "South Orkney Islands"),                        # Signy Island
    (-72.01, 2.53, "Dronning Maud Land"),                          # Troll
    (-70.76, 11.65, "Dronning Maud Land"),                         # Schirmacher Oasis
    (-71.34, 13.45, "Dronning Maud Land"),                         # Lake Untersee
    (-69.0, 39.58, "Dronning Maud Land"),                          # Syowa
    (-67.67, 45.85, "Enderby and Mac.Robertson Land"),             # Molodezhnaya
    (-67.6, 62.87, "Enderby and Mac.Robertson Land"),              # Mawson
    (-70.75, 68.0, "Enderby and Mac.Robertson Land"),              # Amery Oasis
    (-69.4, 76.25, "Princess Elizabeth Land"),                     # Larsemann Hills
    (-68.55, 78.25, "Princess Elizabeth Land"),                    # Vestfold Hills
    (-66.27, 100.75, "Wilkes Land"),                               # Bunger Hills
    (-66.25, 100.35, "Wilkes Land"),                               # westernmost Bunger Hills cell
    (-66.3, 110.52, "Wilkes Land"),                                # Windmill Islands
    (-77.52, 161.6, "Victoria Land"),                              # McMurdo Dry Valleys
    (-74.75, 164.0, "Victoria Land"),                              # Terra Nova Bay
    (-71.3, 170.2, "Victoria Land"),                               # Cape Adare
    (-84.0, 168.0, "Transantarctic Mountains"),                    # Queen Alexandra Range
    (-85.5, -150.0, "Transantarctic Mountains"),                   # Queen Maud Mountains
    (-85.3, -91.0, "Transantarctic Mountains"),                    # Thiel Mountains
    (-83.5, -56.0, "Transantarctic Mountains"),                    # Pensacola Mountains
    (-66.25, 99.75, "Wilkes Land"),                                # ground just west of the Bunger Hills
    (-78.5, -85.5, "Ellsworth Mountains"),                         # Vinson Massif
    (-80.3, -81.5, "Ellsworth Mountains"),                         # Heritage Range
    (-76.0, -135.0, "Antarctica"),                                 # Marie Byrd Land
    (-80.5, -25.0, "Antarctica"),                                  # Shackleton Range
    (-66.8, 89.2, "Antarctica"),                                   # Gaussberg
    (-66.7, 140.0, "Antarctica"),                                  # Dumont d'Urville
    (-87.0, 0.0, "Antarctica"),
    (-59.4, -27.3, "South Sandwich Islands"),
])
def test_southern_region_names(lat, lon, expected):
    assert region(lat, lon) == expected


def test_southern_fallback_starts_at_the_edge_of_the_search_band():
    assert region(-59.0, 100.0) == "Antarctica"
    assert region(-58.9, 100.0) == "Unnamed region"

# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""One fact card per lunar target: what the site is, where each number comes from, what Earth cannot match.

Reads data/derived/moon_targets.json (never changes it) and the LRO Diviner Polar
Resource Product table in data/raw/diviner, and writes data/derived/moon_cards.json.
The Diviner figures are model-based values from NASA's Planetary Data System; the
names, lists and picture links were read from NASA, PGDA, NTRS and LROC pages on
14 November 2026 and are kept in PROVENANCE below, with the saved pages in
data/raw/moon_provenance. Safe to run again: the file is written beside the old
one and renamed into place.

    uv run python scripts/build_moon_cards.py
"""
from __future__ import annotations

import argparse
import html
import json
import math
import os
import re
import shutil
import urllib.request
from datetime import date
from pathlib import Path

import numpy as np

from twinfinder import moon, sun

TARGETS = Path("data/derived/moon_targets.json")
OUT = Path("data/derived/moon_cards.json")
DIVINER_DIR = Path("data/raw/diviner")
PROVENANCE_DIR = Path("data/raw/moon_provenance")
PROVENANCE_DIR_2024 = Path("data/raw/lunar_regions_provenance")   # pages saved on 15 November 2026 for the six regions
REGION_LIST = Path("data/reference/lunar_candidate_regions.json")
DEM_DIR = Path("data/raw")
USER_AGENT = "twinfinder/0.1"

PRP_FOLDER = "https://pds-geosciences.wustl.edu/lro/urn-nasa-pds-lro_diviner_derived1/data_derived_prp"
PRP_TABLE = "dlre_prp_south.tab"
PRP_BYTES = 604_800_210            # 2,880,001 records of 210 bytes (label: FILE_RECORDS = 2880000 plus the heading)
RECORD_BYTES = 210
# Name: (first byte counted from 1, number of bytes), from label/dlre_prp.fmt of the PDS bundle.
PRP_COLUMNS = {
    "tri1_x": (1, 12), "tri1_y": (15, 12), "tri1_z": (29, 12),
    "tri2_x": (43, 12), "tri2_y": (57, 12), "tri2_z": (71, 12),
    "tri3_x": (85, 12), "tri3_y": (99, 12), "tri3_z": (113, 12),
    "tri_clon": (127, 15), "tri_clat": (144, 15), "tri_calt": (161, 15),
    "temp_avg": (178, 8), "temp_max": (188, 8), "ice_depth": (198, 11),
}
ICE_NOT_STABLE = -999.0            # label: written when the depth would be more than 2.8738 m. Not "missing".
ICE_REACH_M = 2.8738
# The table also holds -1.0, which the label does not describe. Every such record is among the coldest in the
# table (yearly maximum at most 101.3 K), so we read it as "ice stable on the surface itself" and say so.
ICE_SURFACE_TRAP = -1.0

MOON_FACTS = "https://nssdc.gsfc.nasa.gov/planetary/factsheet/moonfact.html"
MOON_GRAVITY = 1.62                # m/s2 (Earth 9.80; ratio 0.165), NASA Moon fact sheet
EARTH_GRAVITY = 9.80
MOON_PRESSURE_BAR = 3e-15          # surface pressure at night, NASA Moon fact sheet
SYNODIC_DAYS = 29.53               # NASA Moon fact sheet
PGDA_78 = "https://pgda.gsfc.nasa.gov/products/78"
PGDA_69 = "https://pgda.gsfc.nasa.gov/products/69"
NASA_2022 = "https://www.nasa.gov/news-release/nasa-identifies-candidate-regions-for-landing-next-americans-on-moon/"
NASA_2022_SVS = "https://svs.gsfc.nasa.gov/5013/"
NASA_2024 = "https://www.nasa.gov/news-release/nasa-provides-update-on-artemis-iii-moon-landing-regions/"
NTRS_NINE = "https://ntrs.nasa.gov/citations/20250011660"
NTRS_SIX_PLUS_THREE = "https://ntrs.nasa.gov/citations/20250002110"
SVS_MOUTON = "https://svs.gsfc.nasa.gov/5074/"
NASA_2024_MAP = "https://www.nasa.gov/wp-content/uploads/2024/10/artemis-iii-landing-region-candidates.jpg"
USGS_GRIDS = "https://www.sciencebase.gov/catalog/item/67168797d34ebf903f48b6fc"
NTRS_PLATEAU = "https://ntrs.nasa.gov/citations/20260002598"
LROC_VIEW = "https://data.lroc.im-ldi.com/lroc/view_rdr"
LROC_CREDIT = "NASA/GSFC/Arizona State University"
LROC_TERMS = "https://lroc.im-ldi.com/about/terms"
LROC_CITATION = ("Henriksen, M. R., et al. (2023), Optimized Illuminated Terrain Coverage of the Candidate Artemis III "
                 "Landing Sites with LROC NAC Controlled Mosaics, European Lunar Symposium")

LIST_2022 = ("NASA's 13 candidate regions for Artemis III, announced 19 August 2022 (release 22-089). "
             "Each region is about 15 by 15 km.")
LIST_2024 = ("NASA's nine candidate regions for Artemis III, announced 28 October 2024 and listed in the NASA "
             "abstract NTRS 20250011660: Peak near Cabeus B, Haworth, Malapert Massif, Mons Mouton Plateau, "
             "Mons Mouton, Nobile Rim 1, Nobile Rim 2, de Gerlache Rim 2 and Slater Plain.")

# Read from primary pages on 14 November 2026. "official_name" is the name on the newest NASA list the area is on.
PROVENANCE = {
    "connecting-ridge": {
        "official_name": "Connecting Ridge",
        "name_note": ("NASA's 2022 list calls the region 'Connecting Ridge' and PGDA calls the 5 m model 'Connecting "
                      "ridge'. 'Shackleton - de Gerlache Connecting Ridge' is how the LRO camera team titles a terrain "
                      "model of the ridge, so the longer name is in use and says where the ridge is, but it is not "
                      "the name on a NASA list of candidate regions."),
        "nasa_list": {
            "on_2022_list_of_13": True, "name_2022": "Connecting Ridge",
            "on_2024_list_of_9": False, "name_2024": None,
            "summary": ("On the 2022 list of 13 as 'Connecting Ridge'. Not among the nine regions kept in October "
                        "2024. The NASA abstract says the cut 'does not imply that removed regions are unsuitable "
                        "for future exploration'."),
            "links": [NASA_2022, NASA_2022_SVS, NTRS_NINE],
        },
        "why_check": {
            "confirmed": True,
            "note": ("The stored reason is the wording this check proposed from the three sources listed: \"One of "
                     "NASA's 13 candidate Artemis III regions of 2022 ('Connecting Ridge'); not among the nine kept in "
                     "2024. NASA Goddard's lighting study of the 5 m models found it has the most area lit more than "
                     "70 % of the time.\" It replaced (14 Nov 2026) an earlier reason about a robotic precursor "
                     "mission, which no NASA page that could be read confirmed."),
            "proposed_wording": None,
            "proposed_wording_sources": [NASA_2022, NTRS_NINE, PGDA_78],
        },
        "pgda_model": {"site": "Site01", "pgda_name": "Connecting ridge", "page": PGDA_78},
        "picture": {
            "page": None, "title": None, "product": None,
            "note": ("No LROC low-Sun controlled NAC mosaic is named for Connecting Ridge. The product search at the "
                     "model centre returned no mosaic of the ridge; within one degree it lists 'de Gerlache Rim' "
                     "and 'Peak near Shackleton' mosaics, which do not cover the centre."),
            "nearby": [f"{LROC_VIEW}/NAC_ROI_DEGERRIMLO1", f"{LROC_VIEW}/NAC_ROI_SHKLTNPKLO1"],
            "alternative": {
                "page": f"{LROC_VIEW}/NAC_DTM_SHACKRDGE02",
                "title": "Shackleton - de Gerlache Connecting Ridge DTM",
                "what": ("An LROC NAC stereo terrain model with orthorectified images, not a low-Sun mosaic. "
                         "Whether it covers our model centre was not checked."),
                "credit": LROC_CREDIT, "credit_source": LROC_TERMS,
            },
        },
    },
    "malapert": {
        "official_name": "Malapert Massif",
        "name_note": "Same name on both NASA lists; PGDA calls the 5 m model 'Malapert massif'.",
        "nasa_list": {
            "on_2022_list_of_13": True, "name_2022": "Malapert Massif",
            "on_2024_list_of_9": True, "name_2024": "Malapert Massif",
            "summary": "On the 2022 list of 13 and among the nine regions kept in October 2024.",
            "links": [NASA_2022, NASA_2022_SVS, NTRS_NINE],
        },
        "why_check": {"confirmed": True, "note": "'One of NASA's nine candidate regions' agrees with NTRS 20250011660.",
                      "proposed_wording": None, "proposed_wording_sources": [NTRS_NINE]},
        "pgda_model": {"site": "Site23", "pgda_name": "Malapert massif", "page": PGDA_78},
        "picture": {
            "page": f"{LROC_VIEW}/NAC_ROI_MALAPERTLO1",
            "title": "Malapert Massif low-Sun controlled NAC mosaic (Combined mosaic #1)",
            "product": "NAC_ROI_MALAPERTLO1_P860S0003",
            "saved_page": "lroc_NAC_ROI_MALAPERTLO1.html",
            "note": "1 m per pixel; 184 NAC images, 2009 to 2017; latitude -86.33 to -85.63, longitude -5.66 to 5.15.",
        },
    },
    "mons-mouton": {
        "official_name": "Mons Mouton",
        "name_note": ("The 5 m model is PGDA 'Site20v2: Leibnitz beta plateau, extended boundaries'. NASA's list of "
                      "2022 calls the region 'Leibnitz Beta Plateau'. On the NASA map of 2024, the box of 'Mons "
                      "Mouton' has the place and the size of the USGS box of 'Leibnitz Beta Plateau'. The two centres "
                      "agree to 0.02 km. Thus this region is 'Mons Mouton'. 'Mons Mouton Plateau' is a different, "
                      "larger region to the north, and the page shows it separately. No NASA text says 'renamed'."),
        "nasa_list": {
            "on_2022_list_of_13": True, "name_2022": "Leibnitz Beta Plateau",
            "on_2024_list_of_9": True, "name_2024": "Mons Mouton",
            "name_2024_certainty": ("high: the USGS grid release of 2024 and the NASA map of 2024 show the same box "
                                    "with the two names; no NASA text says 'renamed'"),
            "summary": ("It is on the list of 13 of 2022, as 'Leibnitz Beta Plateau'. The NASA map of the nine "
                        "regions of 28 October 2024 (release 24-136) has the box 'Mons Mouton' at the place of the "
                        "2022 box 'Leibnitz Beta Plateau' (USGS grid release of 2 November 2024). The two centres "
                        "agree to 0.02 km. No NASA text uses the word 'renamed'."),
            "links": [NASA_2022, NASA_2022_SVS, NTRS_NINE, NTRS_SIX_PLUS_THREE, SVS_MOUTON, NASA_2024_MAP, USGS_GRIDS],
        },
        "why_check": {"confirmed": None,
                      "note": ("'Candidate region' agrees with the NASA lists. 'Chang'e-8 also targets it' was not "
                               "checked: no NASA page says so and no other source was read."),
                      "proposed_wording": None, "proposed_wording_sources": []},
        "pgda_model": {"site": "Site20v2", "pgda_name": "Leibnitz beta plateau, extended boundaries", "page": PGDA_78},
        "picture": {
            "page": f"{LROC_VIEW}/NAC_ROI_MTMOUTONLO1",
            "title": ("Nobile Rim 1 and Mons Mouton (Leibnitz Beta Plateau) low-Sun controlled NAC mosaic "
                      "(Combined mosaic #1)"),
            "product": "NAC_ROI_MTMOUTONLO1_P854S0353",
            "saved_page": "lroc_NAC_ROI_MTMOUTONLO1.html",
            "note": ("1 m per pixel; 256 NAC images, 2009 to 2022; latitude -86.07 to -84.82, longitude 27.29 to "
                     "43.23. A different mosaic, 'Mons Mouton Plateau' (NAC_ROI_MOUTNPLTLO1), is centred at 84.3 S, "
                     "30.6 E and does not cover our model centre in LROC's product search."),
            "nearby": [f"{LROC_VIEW}/NAC_ROI_MOUTNPLTLO1"],
        },
    },
    "nobile-rim-2": {
        "official_name": "Nobile Rim 2",
        "name_note": "Same name on both NASA lists; PGDA calls the 5 m model 'DM2: Nobile rim 2'.",
        "nasa_list": {
            "on_2022_list_of_13": True, "name_2022": "Nobile Rim 2",
            "on_2024_list_of_9": True, "name_2024": "Nobile Rim 2",
            "summary": "On the 2022 list of 13 and among the nine regions kept in October 2024.",
            "links": [NASA_2022, NASA_2022_SVS, NTRS_NINE],
        },
        "why_check": {"confirmed": None,
                      "note": ("'Candidate region' agrees with both NASA lists. 'Most top-ranked landing points in "
                               "one study' refers to a non-NASA paper (arXiv 2406.19863) that was not re-read here."),
                      "proposed_wording": None, "proposed_wording_sources": []},
        "pgda_model": {"site": "DM2", "pgda_name": "Nobile rim 2", "page": PGDA_78},
        "picture": {
            "page": f"{LROC_VIEW}/NAC_ROI_NOBILE02LO1",
            "title": "Nobile Rim 2 low-Sun controlled NAC mosaic (Combined mosaic #1)",
            "product": "NAC_ROI_NOBILE02LO1_P839S0587",
            "saved_page": "lroc_NAC_ROI_NOBILE02LO1.html",
            "note": "1 m per pixel; 103 NAC images, 2009 to 2022; latitude -84.40 to -83.50, longitude 54.46 to 63.02.",
        },
    },
}

ON_BOTH = "On the list of 13 of 2022 and on the list of nine of 2024."
NEW_2024 = "On the list of nine of 2024 only. It is one of the three new regions of that list (NTRS 20250002110)."
NO_PICTURE_SAVED = None
NO_MODEL_NOTE = "PGDA product 78 has no 5 m terrain model of this region."

PROVENANCE.update({
    "de-gerlache-rim-2": {
        "official_name": "de Gerlache Rim 2",
        "name_note": ("The name is the same on the two NASA lists. PGDA calls the 5 m model 'SL2: de Gerlache rim'. "
                      "The USGS box of 'de Gerlache Rim 2' has the same corners as the model SL2."),
        "nasa_list": {
            "on_2022_list_of_13": True, "name_2022": "de Gerlache Rim 2",
            "on_2024_list_of_9": True, "name_2024": "de Gerlache Rim 2",
            "summary": ON_BOTH, "links": [NASA_2022, NASA_2022_SVS, NTRS_NINE, NASA_2024_MAP],
        },
        "why_check": {"confirmed": True, "note": "The stored reason agrees with NTRS 20250011660 and the 2022 release.",
                      "proposed_wording": None, "proposed_wording_sources": [NTRS_NINE, NASA_2022]},
        "pgda_model": {"site": "SL2", "pgda_name": "de Gerlache rim", "page": PGDA_78},
        "picture": {
            "page": f"{LROC_VIEW}/NAC_ROI_DEGERRIMLO1",
            "title": "de Gerlache Rim low-Sun controlled NAC mosaic",
            "product": "NAC_ROI_DEGERRIMLO1",
            "saved_page": "lroc_NAC_ROI_DEGERRIMLO1.html",
            "note": ("LROC has no mosaic with the name 'de Gerlache Rim 2'. This mosaic covers the two de Gerlache rim "
                     "regions: latitude -89.02 to -87.79, longitude -83.18 to -41.31."),
        },
    },
    "slater-plain": {
        "official_name": "Slater Plain",
        "name_note": ("The name is the name on the NASA list of 2024. The region is not at the centre of the crater "
                      "Slater: the centre of the box is approximately 33 km from it."),
        "nasa_list": {
            "on_2022_list_of_13": False, "name_2022": None,
            "on_2024_list_of_9": True, "name_2024": "Slater Plain",
            "summary": NEW_2024, "links": [NTRS_NINE, NTRS_SIX_PLUS_THREE, NASA_2024_MAP],
        },
        "why_check": {"confirmed": True, "note": "The stored reason agrees with NTRS 20250011660 and NTRS 20250002110.",
                      "proposed_wording": None, "proposed_wording_sources": [NTRS_NINE, NTRS_SIX_PLUS_THREE]},
        "pgda_model": None,
        "picture": {
            "page": None, "title": None, "product": None,
            "note": ("LROC has no mosaic of this region. A search for 'Slater' gives only a mosaic of a permanently "
                     "shadowed region in the crater Slater (NAC_ROI_PSRSLATRLOA)."),
        },
    },
    "haworth": {
        "official_name": "Haworth",
        "name_note": ("The name is the same on the two NASA lists. PGDA calls the 5 m model 'Haworth'. The region is "
                      "on the west side of the crater Haworth, not at the centre of the crater."),
        "nasa_list": {
            "on_2022_list_of_13": True, "name_2022": "Haworth",
            "on_2024_list_of_9": True, "name_2024": "Haworth",
            "summary": ON_BOTH, "links": [NASA_2022, NASA_2022_SVS, NTRS_NINE, NASA_2024_MAP],
        },
        "why_check": {"confirmed": True, "note": "The stored reason agrees with NTRS 20250011660 and the 2022 release.",
                      "proposed_wording": None, "proposed_wording_sources": [NTRS_NINE, NASA_2022]},
        "pgda_model": {"site": "Haworth", "pgda_name": "Haworth", "page": PGDA_78},
        "picture": {
            "page": f"{LROC_VIEW}/NAC_ROI_HAWORTH_LO1",
            "title": "Haworth low-Sun controlled NAC mosaic",
            "product": "NAC_ROI_HAWORTH_LO1",
            "saved_page": "lroc_NAC_ROI_HAWORTH_LO1.html",
            "note": "Latitude -87.39 to -86.11, longitude -34.98 to -12.36.",
        },
    },
    "nobile-rim-1": {
        "official_name": "Nobile Rim 1",
        "name_note": ("The name is the same on the two NASA lists. PGDA calls the 5 m model 'Site06: Nobile rim 1'. "
                      "The models of Nobile Rim 1 and Mons Mouton overlap by approximately 12 km by 15 km."),
        "nasa_list": {
            "on_2022_list_of_13": True, "name_2022": "Nobile Rim 1",
            "on_2024_list_of_9": True, "name_2024": "Nobile Rim 1",
            "summary": ON_BOTH, "links": [NASA_2022, NASA_2022_SVS, NTRS_NINE, NASA_2024_MAP],
        },
        "why_check": {"confirmed": True, "note": "The stored reason agrees with NTRS 20250011660 and the 2022 release.",
                      "proposed_wording": None, "proposed_wording_sources": [NTRS_NINE, NASA_2022]},
        "pgda_model": {"site": "Site06", "pgda_name": "Nobile rim 1", "page": PGDA_78},
        "picture": {
            "page": f"{LROC_VIEW}/NAC_ROI_MTMOUTONLO1",
            "title": "Nobile Rim 1 and Mons Mouton (Leibnitz Beta Plateau) low-Sun controlled NAC mosaic",
            "product": "NAC_ROI_MTMOUTONLO1_P854S0353",
            "saved_page": "lroc_NAC_ROI_MTMOUTONLO1.html",
            "note": "One mosaic covers Nobile Rim 1 and Mons Mouton: latitude -86.07 to -84.82, longitude 27.29 to 43.23.",
        },
    },
    "mons-mouton-plateau": {
        "official_name": "Mons Mouton Plateau",
        "name_note": ("The name is the name on the NASA list of 2024. This region is not the 2022 region 'Leibnitz "
                      "Beta Plateau': that region is now 'Mons Mouton'. The box of this region on the NASA map is "
                      "approximately 77 km by 58 km, north of Mons Mouton."),
        "nasa_list": {
            "on_2022_list_of_13": False, "name_2022": None,
            "on_2024_list_of_9": True, "name_2024": "Mons Mouton Plateau",
            "summary": NEW_2024, "links": [NTRS_NINE, NTRS_SIX_PLUS_THREE, NASA_2024_MAP, NTRS_PLATEAU],
        },
        "why_check": {"confirmed": True, "note": "The stored reason agrees with NTRS 20250011660 and the NASA map of 2024.",
                      "proposed_wording": None, "proposed_wording_sources": [NTRS_NINE, NASA_2024_MAP]},
        "pgda_model": None,
        "picture": {
            "page": f"{LROC_VIEW}/NAC_ROI_MOUTNPLTLO1",
            "title": "Mons Mouton Plateau low-Sun controlled NAC mosaic",
            "product": "NAC_ROI_MOUTNPLTLO1",
            "saved_page": "lroc_NAC_ROI_MOUTNPLTLO1.html",
            "note": "Latitude -85.76 to -82.85, longitude 15.49 to 46.61.",
        },
    },
    "peak-near-cabeus-b": {
        "official_name": "Peak near Cabeus B",
        "name_note": ("The name is the name on the NASA list of 2024. LROC writes 'Peak Near Cabeus B'. The PGDA "
                      "model 'Cabeus exterior wall 1' is a different place, approximately 100 km from this region."),
        "nasa_list": {
            "on_2022_list_of_13": False, "name_2022": None,
            "on_2024_list_of_9": True, "name_2024": "Peak near Cabeus B",
            "summary": NEW_2024, "links": [NTRS_NINE, NTRS_SIX_PLUS_THREE, NASA_2024_MAP],
        },
        "why_check": {"confirmed": True, "note": "The stored reason agrees with NTRS 20250011660 and NTRS 20250002110.",
                      "proposed_wording": None, "proposed_wording_sources": [NTRS_NINE, NTRS_SIX_PLUS_THREE]},
        "pgda_model": None,
        "picture": {
            "page": f"{LROC_VIEW}/NAC_ROI_CABEUSPKLO1",
            "title": "Peak Near Cabeus B low-Sun controlled NAC mosaic",
            "product": "NAC_ROI_CABEUSPKLO1",
            "saved_page": "lroc_NAC_ROI_CABEUSPKLO1.html",
            "note": "Latitude -84.06 to -83.21, longitude -72.47 to -64.80.",
        },
    },
})

# The six regions of the list of 2022 that are not on the list of 2024. Each has a NASA 5 m terrain model
# (PGDA product 78); the USGS box of each region has the same corners as its model
# (data/reference/lunar_candidate_regions.json, read 15 November 2026).
ONLY_2022_SUMMARY = ("On the list of 13 of 2022 only. It is not on the list of nine of 2024. The NASA abstract NTRS "
                     "20250011660 says that the cut 'does not imply that removed regions are unsuitable for future "
                     "exploration'.")
ONLY_2022_LINKS = [NASA_2022, NASA_2022_SVS, NTRS_NINE, USGS_GRIDS]
ONLY_2022_CHECK = {"confirmed": True, "note": "The stored reason agrees with the 2022 release and NTRS 20250011660.",
                   "proposed_wording": None, "proposed_wording_sources": [NASA_2022, NTRS_NINE]}


def _only_2022(name: str, name_note: str, site: str, pgda_name: str, picture: dict) -> dict:
    return {
        "official_name": name,
        "name_note": name_note,
        "nasa_list": {"on_2022_list_of_13": True, "name_2022": name, "on_2024_list_of_9": False, "name_2024": None,
                      "summary": ONLY_2022_SUMMARY, "links": list(ONLY_2022_LINKS)},
        "why_check": dict(ONLY_2022_CHECK),
        "pgda_model": {"site": site, "pgda_name": pgda_name, "page": PGDA_78},
        "picture": picture,
    }


PROVENANCE.update({
    "connecting-ridge-extension": _only_2022(
        "Connecting Ridge Extension",
        "The name is the name on the NASA list of 2022. PGDA calls the 5 m model 'SL3: Connecting ridge extension'.",
        "SL3", "Connecting ridge extension",
        {"page": None, "title": None, "product": None,
         "note": "LROC has no low-Sun controlled NAC mosaic with the name 'Connecting Ridge Extension'."}),
    "peak-near-shackleton": _only_2022(
        "Peak Near Shackleton",
        "The name is the name on the NASA list of 2022. PGDA calls the 5 m model 'Site07: Peak near Shackleton'.",
        "Site07", "Peak near Shackleton",
        {"page": f"{LROC_VIEW}/NAC_ROI_SHKLTNPKLO1", "title": "Peak near Shackleton low-Sun controlled NAC mosaic",
         "product": "NAC_ROI_SHKLTNPKLO1", "saved_page": "lroc_NAC_ROI_SHKLTNPKLO1.html",
         "note": "Latitude -89.17 to -88.44, longitude 107.53 to 141.84."}),
    "de-gerlache-rim-1": _only_2022(
        "de Gerlache Rim 1",
        ("The name is the name on the NASA list of 2022. The USGS release and LROC write 'de Gerlache Rim'. PGDA "
         "calls the 5 m model 'Site11: de Gerlache rim'. The USGS box of 'de Gerlache Rim' has the same corners as "
         "the model Site11."),
        "Site11", "de Gerlache rim",
        {"page": f"{LROC_VIEW}/NAC_ROI_DEGERRIMLO1", "title": "de Gerlache Rim low-Sun controlled NAC mosaic",
         "product": "NAC_ROI_DEGERRIMLO1", "saved_page": "lroc_NAC_ROI_DEGERRIMLO1.html",
         "note": ("This mosaic covers the two de Gerlache rim regions: latitude -89.02 to -87.79, longitude -83.18 "
                  "to -41.31.")}),
    "faustini-rim-a": _only_2022(
        "Faustini Rim A",
        "The name is the name on the NASA list of 2022. PGDA calls the 5 m model 'LM7: Faustini Rim A'.",
        "LM7", "Faustini Rim A",
        {"page": f"{LROC_VIEW}/NAC_ROI_FAUSTINILO1", "title": "Faustini Rim A low-Sun controlled NAC mosaic",
         "product": "NAC_ROI_FAUSTINILO1", "saved_page": "lroc_NAC_ROI_FAUSTINILO1.html",
         "note": "Latitude -88.19 to -87.54, longitude 79.51 to 100.49."}),
    "de-gerlache-kocher-massif": _only_2022(
        "de Gerlache-Kocher Massif",
        ("The name is the name on the NASA list of 2022. LROC writes 'de Gerlache Kocher Massif'. PGDA calls the "
         "5 m model 'Site42: de Gerlache-Kocher massif'."),
        "Site42", "de Gerlache-Kocher massif",
        {"page": f"{LROC_VIEW}/NAC_ROI_DEGERKCHLO1",
         "title": "de Gerlache Kocher Massif low-Sun controlled NAC mosaic",
         "product": "NAC_ROI_DEGERKCHLO1", "saved_page": "lroc_NAC_ROI_DEGERKCHLO1.html",
         "note": "Latitude -86.27 to -85.39, longitude -122.59 to -110.48."}),
    "amundsen-rim": _only_2022(
        "Amundsen Rim",
        "The name is the name on the NASA list of 2022. PGDA calls the 5 m model 'DM1: Amundsen rim'.",
        "DM1", "Amundsen rim",
        {"page": f"{LROC_VIEW}/NAC_ROI_AMUNDRIMLO1", "title": "Amundsen Rim low-Sun controlled NAC mosaic",
         "product": "NAC_ROI_AMUNDRIMLO1", "saved_page": "lroc_NAC_ROI_AMUNDRIMLO1.html",
         "note": "Latitude -84.65 to -83.80, longitude 65.10 to 73.51."}),
})

EMPTY_STATS = {"mean": None, "min": None, "max": None}
EMPTY_ICE = {"stable_within_reach_share": None, "stable_at_surface_share": None, "surface_cold_trap_share": None,
             "stable_within_1m_share": None, "not_stable_within_reach_share": None,
             "stable_within_reach_share_without_undocumented_value": None,
             "shallowest_m": None, "deepest_stable_m": None}
EMPTY_DIVINER = {
    "model_based": True, "triangles": 0, "triangles_without_temperature": 0,
    "area_covered_km2": None, "target_area_km2": None,
    "annual_mean_temp_2cm_K": dict(EMPTY_STATS), "annual_max_temp_surface_K": dict(EMPTY_STATS),
    "annual_mean_temp_2cm_C": dict(EMPTY_STATS), "annual_max_temp_surface_C": dict(EMPTY_STATS),
    "ice": dict(EMPTY_ICE), "altitude_check": None,
}


# ---- geometry ----

def shadow_length_m(height_m: float, sun_elev_deg: float | None) -> float | None:
    """Length on level ground of the shadow of an upright object. None without a Sun above the horizon."""
    if sun_elev_deg is None or not sun_elev_deg > 0.0:
        return None
    return height_m / math.tan(math.radians(sun_elev_deg))


def latlon_to_polar_xy(lat_deg, lon_deg):
    """Latitude and east longitude to south polar stereographic metres: the inverse of moon.polar_xy_to_latlon."""
    r = 2.0 * moon.MOON_RADIUS_M * np.tan(np.radians(90.0 + np.asarray(lat_deg, dtype="float64")) / 2.0)
    lon = np.radians(np.asarray(lon_deg, dtype="float64"))
    return r * np.sin(lon), r * np.cos(lon)


def target_size_km(target: dict) -> list | None:
    """Width and height of the target's box in km: the 5 m model, else the sourced box (box_km), else None."""
    return target.get("extent_km") or target.get("box_km")


def target_bounds(target: dict) -> tuple[float, float, float, float] | None:
    """Left, bottom, right, top of the target's 5 m model (or sourced box) in map metres; None without a box."""
    size = target_size_km(target)
    if size is None:
        return None
    cx, cy = latlon_to_polar_xy(target["centre_lat"], target["centre_lon"])
    half_w, half_h = size[0] * 500.0, size[1] * 500.0
    return float(cx - half_w), float(cy - half_h), float(cx + half_w), float(cy + half_h)


def triangle_map_area_km2(corners_km: np.ndarray) -> np.ndarray:
    """Map area of triangles given as [n, 3 corners, Moon-centred x y z in km], in the 5 m models' projection."""
    x, y, z = corners_km[..., 0], corners_km[..., 1], corners_km[..., 2]
    lat = np.degrees(np.arctan2(z, np.hypot(x, y)))
    lon = np.degrees(np.arctan2(y, x))
    mx, my = latlon_to_polar_xy(lat, lon)
    mx, my = mx / 1000.0, my / 1000.0
    return 0.5 * np.abs((mx[:, 1] - mx[:, 0]) * (my[:, 2] - my[:, 0]) - (mx[:, 2] - mx[:, 0]) * (my[:, 1] - my[:, 0]))


# ---- the Diviner table ----

def open_prp(path: Path) -> np.ndarray:
    """The table's data records as bytes [rows, 210], read from disk only where used. Checks the layout first."""
    size = path.stat().st_size
    if size < RECORD_BYTES or size % RECORD_BYTES:
        raise ValueError(f"{path} is {size} bytes, not a whole number of {RECORD_BYTES}-byte records")
    with open(path, "rb") as handle:
        heading = handle.read(RECORD_BYTES).decode("ascii", errors="replace")
    names = [name.strip() for name in heading.split(",")]
    if names != list(PRP_COLUMNS):
        raise ValueError(f"{path}: unexpected column headings {names}")
    rows = size // RECORD_BYTES - 1
    if rows == 0:
        return np.empty((0, RECORD_BYTES), dtype=np.uint8)
    return np.memmap(path, dtype=np.uint8, mode="r", offset=RECORD_BYTES, shape=(rows, RECORD_BYTES))


def prp_column(table: np.ndarray, name: str, rows: np.ndarray | None = None) -> np.ndarray:
    """One column as numbers, for all records or for the chosen ones."""
    start, length = PRP_COLUMNS[name]
    block = table[:, start - 1:start - 1 + length] if rows is None else table[rows, start - 1:start - 1 + length]
    return np.ascontiguousarray(block).view(f"S{length}").ravel().astype(np.float64)


def triangle_centres_xy(table: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Map metres of every triangle centre, from the table's own centre longitude and latitude."""
    return latlon_to_polar_xy(prp_column(table, "tri_clat"), prp_column(table, "tri_clon"))


# ---- statistics ----

def _known(value: float, digits: int) -> float | None:
    return None if value is None or not math.isfinite(value) else round(float(value), digits)


def area_stats(values: np.ndarray, weights: np.ndarray) -> dict:
    """Area-weighted mean, and the lowest and highest value. All None when there is nothing to average."""
    if values.size == 0 or not weights.sum() > 0.0:
        return dict(EMPTY_STATS)
    return {"mean": _known((values * weights).sum() / weights.sum(), 3),
            "min": _known(values.min(), 3), "max": _known(values.max(), 3)}


def ice_shares(ice_depth_m: np.ndarray, weights: np.ndarray) -> dict:
    """Shares of the area by ice stability.

    -999 means 'not stable within 2.87 m' and counts as area. A depth of 0 to 2.8738 m is where ice becomes
    stable. -1, which the label does not describe, is read as a surface cold trap (see ICE_SURFACE_TRAP) and
    counted as depth 0; the share without it is given too. Any other value is refused.
    """
    total = weights.sum() if ice_depth_m.size else 0.0
    if not total > 0.0:
        return dict(EMPTY_ICE)
    deeper = ice_depth_m == ICE_NOT_STABLE
    trap = ice_depth_m == ICE_SURFACE_TRAP
    has_depth = (ice_depth_m >= 0.0) & (ice_depth_m <= ICE_REACH_M + 1e-6)
    if not np.all(deeper | trap | has_depth):
        raise ValueError("ice depth that is neither 0 to 2.8738 m nor one of the special values -999 and -1")
    depth = np.where(trap, 0.0, ice_depth_m)
    stable = trap | has_depth
    share = lambda mask: _known(weights[mask].sum() / total, 5)
    return {
        "stable_within_reach_share": share(stable),
        "stable_at_surface_share": share(stable & (depth == 0.0)),
        "surface_cold_trap_share": share(trap),
        "stable_within_1m_share": share(stable & (depth <= 1.0)),
        "not_stable_within_reach_share": share(deeper),
        "stable_within_reach_share_without_undocumented_value": share(has_depth),
        "shallowest_m": _known(depth[stable].min(), 4) if stable.any() else None,
        "deepest_stable_m": _known(depth[stable].max(), 4) if stable.any() else None,
    }


def undocumented_value_check(table: np.ndarray) -> dict:
    """What the records holding -1 in ice_depth look like, over the whole table: the grounds for our reading."""
    depth, temp_max = prp_column(table, "ice_depth"), prp_column(table, "temp_max")
    trap = depth == ICE_SURFACE_TRAP
    return {
        "value": ICE_SURFACE_TRAP, "column": "ice_depth", "in_label": False,
        "records": int(trap.sum()), "of_records": int(depth.size),
        "highest_yearly_maximum_K_among_them": _known(temp_max[trap].max(), 3) if trap.any() else None,
        "lowest_yearly_maximum_K_among_all_other_records": _known(temp_max[~trap].min(), 3) if (~trap).any() else None,
        "records_with_depth_0": int((depth == 0.0).sum()),
        "records_with_minus_999": int((depth == ICE_NOT_STABLE).sum()),
        "our_reading": ("Ice stable on the surface itself (a surface cold trap), counted as depth 0. The label "
                        "describes only 0 and -999; this reading rests on the temperatures of these records."),
    }


def _celsius(stats: dict) -> dict:
    return {key: None if value is None else round(value - 273.15, 2) for key, value in stats.items()}


def altitude_check(target: dict, x_m: np.ndarray, y_m: np.ndarray, alt_km: np.ndarray, dem_dir: Path) -> dict | None:
    """Do the table's triangle heights agree with our 5 m model at the same map positions? None without the model.

    A high correlation says the triangles were placed on the right ground; the table's mesh was built on Kaguya
    altimetry, so a difference of some tens of metres is expected.
    """
    if not target.get("source"):
        return None
    dem = Path(dem_dir) / target["source"].rsplit("/", 1)[-1]
    if not dem.exists() or x_m.size < 3:
        return None
    import rasterio
    from rasterio.enums import Resampling

    with rasterio.open(dem) as ds:
        step = max(1, round(100.0 / ds.res[0]))                       # about 100 m pixels
        rows, cols = ds.height // step, ds.width // step
        z = ds.read(1, out_shape=(rows, cols), resampling=Resampling.average, masked=True)
        z = z.astype("float64").filled(np.nan)
        b = ds.bounds
    col = np.floor((x_m - b.left) / (b.right - b.left) * cols).astype(int)
    row = np.floor((b.top - y_m) / (b.top - b.bottom) * rows).astype(int)
    inside = (col >= 0) & (col < cols) & (row >= 0) & (row < rows)
    ours, theirs = z[row[inside], col[inside]], alt_km[inside] * 1000.0
    ok = np.isfinite(ours) & np.isfinite(theirs)
    if ok.sum() < 3:
        return None
    diff = ours[ok] - theirs[ok]
    return {"triangles_compared": int(ok.sum()),
            "correlation": _known(np.corrcoef(ours[ok], theirs[ok])[0, 1], 4),
            "median_difference_m": _known(np.median(diff), 1),
            "median_abs_difference_m": _known(np.median(np.abs(diff)), 1),
            "how": ("Height of our 5 m model (averaged to about 100 m) minus the table's triangle-centre altitude, "
                    "at the same map position; both are relative to a 1737.4 km sphere.")}


def diviner_for_target(table: np.ndarray, x_m: np.ndarray, y_m: np.ndarray, target: dict,
                       dem_dir: Path | None = None) -> dict:
    """Temperature and ice figures over the target's 5 m model area, from the triangles whose centre lies in it."""
    out = json.loads(json.dumps(EMPTY_DIVINER))
    bounds = target_bounds(target)
    if bounds is None:
        return out
    left, bottom, right, top = bounds
    rows = np.flatnonzero((x_m >= left) & (x_m <= right) & (y_m >= bottom) & (y_m <= top))
    size = target_size_km(target)
    out["target_area_km2"] = _known(size[0] * size[1], 2)
    if rows.size == 0:
        return out
    corners = np.stack([np.stack([prp_column(table, f"tri{k}_{axis}", rows) for axis in "xyz"], axis=1)
                        for k in (1, 2, 3)], axis=1)
    weights = triangle_map_area_km2(corners)
    temp_avg, temp_max = prp_column(table, "temp_avg", rows), prp_column(table, "temp_max", rows)
    has_temp = np.isfinite(temp_avg) & np.isfinite(temp_max) & (temp_avg > 0.0) & (temp_max > 0.0)
    out.update({
        "triangles": int(rows.size),
        "triangles_without_temperature": int((~has_temp).sum()),
        "area_covered_km2": _known(weights.sum(), 3),
        "annual_mean_temp_2cm_K": area_stats(temp_avg[has_temp], weights[has_temp]),
        "annual_max_temp_surface_K": area_stats(temp_max[has_temp], weights[has_temp]),
        "ice": ice_shares(prp_column(table, "ice_depth", rows), weights),
    })
    out["annual_mean_temp_2cm_C"] = _celsius(out["annual_mean_temp_2cm_K"])
    out["annual_max_temp_surface_C"] = _celsius(out["annual_max_temp_surface_K"])
    if dem_dir is not None:
        out["altitude_check"] = altitude_check(target, x_m[rows], y_m[rows], prp_column(table, "tri_calt", rows),
                                               dem_dir)
    return out


# ---- the saved LROC pages ----

def mosaic_images(page_html: str) -> list[dict]:
    """The images of an LROC mosaic page: id, centre latitude and longitude, incidence angle in whole degrees."""
    text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", page_html)))
    found = re.findall(r"(M\d{6,}[LR]) (-?\d+\.\d+) (-?\d+\.\d+) (\d+)° ", text)
    return [{"id": i, "lat": float(lat), "lon": float(lon), "incidence_deg": int(inc)} for i, lat, lon, inc in found]


def mosaic_sun_heights(page_html: str) -> dict | None:
    """Range of Sun height (90 minus incidence) over a mosaic's images, and how many exceed the flat-horizon ceiling.

    Incidence is printed in whole degrees, so an image counts as above the ceiling only when it is more than
    half a degree above 90 - |image latitude| + 1.54.
    """
    images = mosaic_images(page_html)
    if not images:
        return None
    heights = [90 - image["incidence_deg"] for image in images]
    above = sum(1 for image, h in zip(images, heights)
                if h > sun.lunar_max_sun_elevation_deg(image["lat"]) + 0.5)
    return {"images_listed": len(images), "sun_height_min_deg": min(heights), "sun_height_max_deg": max(heights),
            "images_above_flat_ceiling_at_their_latitude": above}


# ---- the card ----

def earth_cannot_match(target: dict, diviner: dict) -> list[dict]:
    """The seven things no place on Earth reproduces, each with a number where we have one (else null)."""
    ceiling = target["sun_max_elev_deg"]
    shadow = shadow_length_m(1.0, ceiling)
    mean_k, mean_c = diviner["annual_mean_temp_2cm_K"], diviner["annual_mean_temp_2cm_C"]
    max_k = diviner["annual_max_temp_surface_K"]
    if mean_k["mean"] is None:
        moon_temp = "Not known: no Diviner figure for this area."
    else:
        moon_temp = (f"Model-based (Diviner): the annual mean 2 cm under the surface is {mean_k['mean']:.0f} K "
                     f"({mean_c['mean']:.0f} °C) averaged over the area, {mean_k['min']:.0f} K in the coldest place; "
                     f"the yearly maximum at the surface ranges from {max_k['min']:.0f} K to {max_k['max']:.0f} K.")
    shadow_share = target.get("permanent_shadow_fraction")
    moon_shadow = "No air scatters light into shadows; they are lit only by light bounced off nearby ground."
    if shadow is not None:
        moon_shadow += f" At the Sun ceiling of {ceiling:.2f}° a 1 m object throws a {shadow:.1f} m shadow."
    if shadow_share is not None:
        moon_shadow += f" {shadow_share:.1%} of the area never sees the Sun."
    rate_moon = 360.0 / (SYNODIC_DAYS * 24.0)
    return [
        {"what": "vacuum", "number": MOON_PRESSURE_BAR, "unit": "bar",
         "moon": "Surface pressure at night about 3 x 10^-15 bar: no air, no wind, no sound, no weather.",
         "earth": "About 1 bar at sea level.", "source": MOON_FACTS},
        {"what": "gravity", "number": MOON_GRAVITY, "unit": "m/s2",
         "moon": f"{MOON_GRAVITY} m/s2 at the surface, about one sixth of Earth's.",
         "earth": f"{EARTH_GRAVITY:.2f} m/s2 (ratio {MOON_GRAVITY / EARTH_GRAVITY:.3f}).", "source": MOON_FACTS},
        {"what": "dust", "number": None, "unit": None,
         "moon": "Dry, sharp-grained regolith that no water or air has ever rounded; it clings to suits and gear.",
         "earth": "Soil and rock shaped by water, air and life.", "source": None,
         "note": "No number: we read no dust dataset."},
        {"what": "temperature", "number": mean_k["mean"], "unit": "K",
         "moon": moon_temp,
         "earth": "Not computed here; compare with the NASA POWER temperature of each Earth place.",
         "source": f"{PRP_FOLDER}/", "note": "Diviner Polar Resource Product: model values, not measurements."},
        {"what": "radiation", "number": None, "unit": None,
         "moon": "No air and no global magnetic field to stop solar particles and cosmic rays.",
         "earth": "Shielded by the atmosphere and the magnetic field.", "source": None,
         "note": "No number: we read no radiation dataset."},
        {"what": "black shadows", "number": _known(shadow, 2), "unit": "m of shadow per 1 m object at the Sun ceiling",
         "moon": moon_shadow,
         "earth": ("The same shadow length at the same Sun height, but the sky lights the shadow and the low Sun is "
                   "dimmed and reddened by air. We have no number for that difference."),
         "source": PGDA_69},
        {"what": "slow Sun", "number": SYNODIC_DAYS, "unit": "days for the Sun to go round once",
         "moon": (f"One turn of the Sun around the horizon takes {SYNODIC_DAYS} days, about {rate_moon:.2f}° per hour; "
                  "a shadow stays put for hours."),
         "earth": f"24 hours, 15° per hour: about {15.0 / rate_moon:.1f} times faster.", "source": MOON_FACTS},
    ]


CEILING_HOW_NO_MODEL = ("90 - |latitude| + 1.54 degrees, at the latitude of the centre of the box of the region on "
                       "the NASA map of 2024. NASA gives no 5 m terrain model of this region. The range uses the same "
                       "formula at the corners, the edge centres and the centre of the box.")
LIT_HOW_NO_MODEL = ("Mean and highest 240 m pixel of the NASA Goddard map AVGVISIB_65S_240M_201608, inside the box of "
                    "the region on the NASA map of 2024.")
SHADOW_HOW_NO_MODEL = ("Share of the 240 m pixels inside the same box that the NASA Goddard map LPSR_65S_240M_201608 "
                       "marks as permanently shadowed (value above 0.5).")
DIVINER_HOW_NO_MODEL = ("LRO Diviner Polar Resource Product (LRO-L-DLRE-5-PRP-V2.0): fits of a thermal model to the "
                        "first year of Diviner polar data, on triangles of approximately 500 m. The figures use the "
                        "triangles with a centre inside the box of the region on the NASA map of 2024. The area of "
                        "each triangle gives its weight.")


def build_card(target: dict, diviner: dict, picture_extra: dict | None = None) -> dict:
    """One card. Refuses a target we hold no provenance for. A target without a 5 m model has pgda_model None."""
    facts = PROVENANCE[target["id"]]
    has_model = bool(target.get("has_model", target.get("source") is not None))
    ceiling = target.get("sun_max_elev_deg")
    picture = dict(facts["picture"])
    picture.pop("saved_page", None)
    picture.update({
        "credit": LROC_CREDIT if picture["page"] else None,
        "credit_source": LROC_TERMS if picture["page"] else None,
        "citation": LROC_CITATION if picture["page"] else None,
        "sun_heights_of_images": picture_extra,
        "image_downloaded": False,
    })
    pgda_model = None
    if facts["pgda_model"] is not None:
        pgda_model = {
            **facts["pgda_model"], "dem_url": target.get("source"), "pixel_m": 5,
            "what": "NASA Goddard LOLA 5 m elevation model of the site (PGDA product 78)",
            "citation": ("Barker, M. K., et al. (2021), Improved LOLA Elevation Maps for South Pole Landing Sites, "
                         "Planetary and Space Science 203, 105119, doi:10.1016/j.pss.2020.105119"),
        }
    return {
        "id": target["id"],
        "has_model": has_model,
        "model_note": None if has_model else NO_MODEL_NOTE,
        "position": {"how_sure": target.get("position_how_sure"), "source": target.get("position_source"),
                     "note": target.get("position_note")},
        "official_name": facts["official_name"],
        "name_in_project": target.get("name"),
        "name_note": facts["name_note"],
        "nasa_list": facts["nasa_list"],
        "why_stored": target.get("why"),
        "why_check": facts["why_check"],
        "pgda_model": pgda_model,
        "centre": {"lat": target.get("centre_lat"), "lon_east": target.get("centre_lon")},
        "extent_km": target.get("extent_km"),
        "box_km": target.get("box_km"),
        "sun_ceiling": {
            "deg": ceiling,
            "range_deg": target.get("sun_max_elev_range_deg"),
            "how": ("90 - |latitude| + 1.54 degrees, at the latitude of the middle of the 5 m model: the highest the "
                    "Sun's centre climbs over a flat horizon, 1.54 degrees being the tilt of the Moon's axis to the "
                    "ecliptic (twinfinder/sun.py, lunar_max_sun_elevation_deg). The range is the same formula at the "
                    "model's most and least poleward corner, edge midpoint or centre. No terrain, no ephemeris and "
                    "no allowance for the Sun's disc enter.") if has_model else CEILING_HOW_NO_MODEL,
            "kind": "derived from latitude",
            "source": target.get("source") or target.get("position_source"),
        },
        "shadow_of_1m_object_at_ceiling_m": _known(shadow_length_m(1.0, ceiling), 2),
        "shadow_how": "1 m divided by the tangent of the Sun ceiling, on level ground.",
        "lit": {
            "mean_share": target.get("illumination_mean"),
            "best_point_share": target.get("illumination_max"),
            "how": ("Mean and highest 240 m pixel, inside the bounding box of the 5 m model, of NASA Goddard's "
                    "average solar illumination map AVGVISIB_65S_240M_201608 (hourly steps over 18.6 years, LOLA "
                    "terrain), read with the file's own scale and offset (twinfinder/moon.py, fingerprint).")
                   if has_model else LIT_HOW_NO_MODEL,
            "kind": "measured terrain, modelled Sun",
            "source": PGDA_69,
            "file": moon.ILLUMINATION_URL,
        },
        "permanent_shadow": {
            "share": target.get("permanent_shadow_fraction"),
            "how": ("Share of the 240 m pixels inside the same box that NASA Goddard's map LPSR_65S_240M_201608 "
                    "marks as permanently shadowed (value above 0.5).") if has_model else SHADOW_HOW_NO_MODEL,
            "kind": "measured terrain, modelled Sun",
            "source": PGDA_69,
            "file": moon.PSR_URL,
        },
        "diviner": {
            **diviner,
            "kind": "model-based",
            "how": ("LRO Diviner Polar Resource Product (LRO-L-DLRE-5-PRP-V2.0): thermal-model fits to the first "
                    "year of Diviner polar observations on a mesh of about 500 m triangles. Figures are over the "
                    "triangles whose centre lies inside the 5 m model's bounding box, weighted by triangle area. "
                    "Ice is 'stable' where the table gives a depth (0 to 2.87 m) at which ice would be lost more "
                    "slowly than 1 kg per m2 per billion years; -999 means deeper than 2.87 m, not missing. "
                    "The table's undocumented value -1 is read as stable on the surface; see meta.diviner.")
                   if has_model else DIVINER_HOW_NO_MODEL,
            "source": f"{PRP_FOLDER}/",
            "citation": "Paige et al., LRO DLRE Level 5 PRP V2.0, NASA Planetary Data System, 2018",
        },
        "picture": picture,
        "earth_cannot_match": earth_cannot_match(target, diviner),
    }


# ---- files ----

def write_json(path: Path, value) -> None:
    """Write beside the old file and rename into place. Refuses NaN: unknown must be null."""
    side = path.with_name(path.name + ".part")
    try:
        text = json.dumps(value, indent=1, allow_nan=False)
        side.write_text(text + "\n")
        os.replace(side, path)
    finally:
        side.unlink(missing_ok=True)


def fetch_table(folder: Path) -> Path:
    """The Diviner south table, downloaded once (605 MB, no login) with its label files."""
    folder.mkdir(parents=True, exist_ok=True)
    wanted = {"dlre_prp_south.lbl": f"{PRP_FOLDER}/dlre_prp_south.lbl", "dlre_prp_south.xml": f"{PRP_FOLDER}/dlre_prp_south.xml",
              PRP_TABLE: f"{PRP_FOLDER}/{PRP_TABLE}"}
    for name, url in wanted.items():
        dest = folder / name
        if dest.exists():
            continue
        print(f"downloading {url}")
        side = dest.with_name(dest.name + ".part")
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=300) as response, open(side, "wb") as out:
            shutil.copyfileobj(response, out)
        if name == PRP_TABLE and side.stat().st_size != PRP_BYTES:
            side.unlink()
            raise ConnectionError(f"{url}: the download is not {PRP_BYTES} bytes")
        os.replace(side, dest)
    return folder / PRP_TABLE


def meta(targets_path: Path, table_path: Path, rows: int, undocumented: dict) -> dict:
    return {
        "generated": date.today().isoformat(),
        "script": "scripts/build_moon_cards.py",
        "how_to_rerun": "uv run python scripts/build_moon_cards.py",
        "inputs": {"targets": str(targets_path), "diviner_table": str(table_path), "diviner_rows": rows,
                   "saved_pages": str(PROVENANCE_DIR)},
        "pages_read_on": "2026-11-14",
        "lists": {"2022": {"what": LIST_2022, "links": [NASA_2022, NASA_2022_SVS]},
                  "2024": {"what": LIST_2024, "links": [NTRS_NINE, NASA_2024],
                           "note": ("The NASA release of 28 October 2024 answered 'too many requests' on all ten "
                                    "tries over 15 minutes; the nine names are from the NTRS abstract.")}},
        "diviner": {
            "product": "LRO Diviner Polar Resource Product, south (dlre_prp_south.tab), PDS data set LRO-L-DLRE-5-PRP-V2.0",
            "folder": f"{PRP_FOLDER}/",
            "model_based": True,
            "columns_used": {"temp_avg": "annual average temperature, K, 2 cm below the surface",
                             "temp_max": "annual maximum temperature, K, at the surface",
                             "ice_depth": "depth in m at which water ice would be lost at 1 kg per m2 per billion years"},
            "special_value": {"value": ICE_NOT_STABLE, "column": "ice_depth",
                              "meaning": (f"the depth would be more than {ICE_REACH_M} m: ice is not stable within "
                                          "the depth the product covers. It is counted as area, not left out. "
                                          "0 means stable at the surface.")},
            "undocumented_value": undocumented,
            "mesh": "2,880,000 triangles of about 0.5 km on a Kaguya laser-altimeter terrain model, pole to 80 S",
            "not_checked": ("How well the Kaguya-based mesh lines up with the LOLA 5 m models beyond the "
                            "altitude_check on each card; the product's own uncertainty, which the label does not give."),
        },
        "pgda_78_cross_check": {
            "done": False,
            "why": ("PGDA product 78 publishes elevation, slope, uncertainty and clone files only. Its lighting "
                    "study (1 January 2024 to 1 January 2026, at 1 m and 5 m above ground) is described in words "
                    "for Sites 1, 4, 7 and 11 and gives no highest Sun elevation, so our ceilings cannot be compared "
                    "with it from the page."),
            "what_it_says": ("'Site 1 has the most area with average illumination > 70% at 1 m above the surface' "
                             "and 'longer continuous illumination periods than the other sites' at 5 m."),
            "link": PGDA_78,
        },
        "picture_credit": {"credit": LROC_CREDIT, "source": LROC_TERMS,
                           "note": "Links and credits only; no image was downloaded."},
        "units": {"temperature": "K (and °C = K - 273.15)", "shares": "0 to 1", "angles": "degrees", "lengths": "m"},
        "unknown_is": "null",
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--targets", type=Path, default=TARGETS)
    parser.add_argument("--table", type=Path, default=None, help="Diviner south table; downloaded if absent")
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--dem-dir", type=Path, default=DEM_DIR, help="folder with the 5 m models (optional check)")
    parser.add_argument("--pages", type=Path, default=PROVENANCE_DIR, help="folder with the saved LROC pages")
    args = parser.parse_args(argv)

    targets = json.loads(args.targets.read_text())
    table_path = args.table if args.table is not None else fetch_table(DIVINER_DIR)
    table = open_prp(table_path)
    x_m, y_m = triangle_centres_xy(table)
    result = {"meta": meta(args.targets, table_path, int(table.shape[0]), undocumented_value_check(table)),
              "cards": []}
    for target in targets:
        diviner = diviner_for_target(table, x_m, y_m, target, args.dem_dir)
        saved = PROVENANCE[target["id"]]["picture"].get("saved_page")
        page = next((folder / saved for folder in (args.pages, PROVENANCE_DIR_2024) if (folder / saved).exists()),
                    None) if saved else None
        extra = mosaic_sun_heights(page.read_text(encoding="utf-8", errors="replace")) if page and page.exists() else None
        card = build_card(target, diviner, extra)
        result["cards"].append(card)
        t, ice = diviner["annual_mean_temp_2cm_K"], diviner["ice"]
        print(f"{card['id']}: {diviner['triangles']} triangles | annual mean {t['mean']} K "
              f"({t['min']} to {t['max']}) | annual max {diviner['annual_max_temp_surface_K']} | "
              f"ice stable within {ICE_REACH_M} m on {ice['stable_within_reach_share']} of the area, "
              f"at the surface on {ice['stable_at_surface_share']} (value -1: {ice['surface_cold_trap_share']}) | "
              f"altitude check {diviner['altitude_check']}")
    write_json(args.out, result)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()

# Data sources, licences and credit lines

Earth Twin Finder, NASA Space Apps 2026. Written Saturday 14 November 2026. Rows 3 to 5 corrected and rows 19
to 21, credits O and P and the Copernicus liability sentence added the same day by the late check of the
additions; every licence page that decides whether a file may be public was opened a second time then
(copies in `data/raw/additions_check_links/`) and said what this file says. Row 22 and credit Q (OurAirports, for the distance to airfields) were added
the same evening. Section 1b (rows 23 to 41) and credits R to AD were added late that night (Pacific time). They cover the
Mars part, the factor layers, the power section and the "steady influences" section. Rows 42 to 45 and credits AE
to AH were added on 15 November 2026 at about 01:10 Pacific time. They cover the three globe images and the globe library.
Rows 61 and 62 and credits AW and AX were added on 15 November 2026 in the afternoon (Pacific time). They cover
NASA's map of 2024 and the USGS grid release, from which `data/reference/lunar_candidate_regions.json` takes
positions and boxes of lunar regions. No page was fetched for them: they rest on the copies of
`data/raw/lunar_regions_provenance/`.

How this list was made: every URL in `twinfinder/`, `scripts/` and `site/` was listed, every folder under
`data/raw` and every file in `data/reference` was opened, and the `meta` blocks of `data/derived` were read.
For each source its own licence or terms page was fetched today with the header `User-Agent: twinfinder/0.1`
and no login. Where a page was not opened, the row says so.

Group: **NASA**, **Partner** (one of the 17 Space Agency Partners on
https://www.spaceappschallenge.org/2026/space-agency-partners/ : Angola GGPEN, Argentina CONAE, Bahrain BSA,
Brazil AEB, Canada CSA, ESA, India ISRO, Italy ASI, Japan JAXA, South Korea KASA, Nigeria NASRDA, Paraguay AEP,
Senegal ASES, Spain AEE, Turkey TUA, UAE MBRSC, UK Space Agency), or **Other**. NOAA, the European Union's
Copernicus services, the British Antarctic Survey and COMNAP are not on that list.

No source needs a login. "Raw" means the files as downloaded; "derived" means numbers we computed from them
(the files in `data/derived` and `site/data`).

## 1. The sources

| # | Full name | Provider | Group | What we use it for | Link we fetch from | Licence or terms | Credit the provider asks for | Raw files in a public repository? | Derived products in a public repository? |
|---|---|---|---|---|---|---|---|---|---|
| 1 | LRO LOLA 5 m terrain models of lunar south-pole sites (PGDA product 78): Site01, SL3, Site07, Site11, SL2, LM7, Haworth, Site23, Site42, Site06, Site20v2, DM1, DM2 | NASA Goddard Space Flight Center, Planetary Geodesy Data Archive (PGDA) | NASA | The lunar regions with a model: how high the Sun climbs, slopes | `https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/<site>/<site>_final_adj_5mpp_surf.tif` | "Data Usage Policy" on https://pgda.gsfc.nasa.gov/products/78 : cite the paper. No licence text on the page; NASA material is not copyrighted in the US (general NASA policy, not opened for this product) | Credit A | Allowed as far as we can tell, but 40 to 103 MB each: do not commit | Yes, with the citation |
| 2 | LOLA polar illumination and permanent-shadow maps, 240 m (PGDA product 69): `AVGVISIB_65S_240M_201608.TIF`, `LPSR_65S_240M_201608.TIF` | NASA Goddard PGDA (same products are on the NASA Planetary Data System) | NASA | Average sunlight and permanent shadow at the lunar sites | `https://pgda.gsfc.nasa.gov/data/MoonIllumination/` | "Citation" on https://pgda.gsfc.nasa.gov/products/69 : cite the paper | Credit B | Allowed as far as we can tell; 58 MB: do not commit | Yes, with the citation |
| 3 | JPL Horizons ephemeris system (DE441) | NASA Jet Propulsion Laboratory, Solar System Dynamics | NASA | Two uses. A check: 12 reference Sun declinations typed into `tests/test_sun.py`. And the Sun-path picture: the hourly direction of the Sun seen from two lunar sites, December 2025 to February 2027 (`sunpath_demo.json`), fetched by `scripts/build_sunpath_demo.py` into `data/raw/horizons_sunpath/` | `https://ssd.jpl.nasa.gov/api/horizons.api` (about the system: https://ssd.jpl.nasa.gov/horizons/) | Acknowledgement text on https://ssd.jpl.nasa.gov/about/ (opened; it asks for a citation and states no licence) | Credit C | Not needed: 1.4 MB of text that the script fetches again | Yes, with the credit |
| 4 | NASA POWER, Climatology API v2.10.1, parameters `CLOUD_AMT`, `CLOUD_AMT_DAY`, `CLOUD_AMT_NIGHT` (CERES SYN1deg) and `T2M`, `T2M_MAX`, `T2M_MIN`, `TS` (MERRA-2, reanalysis by NASA GMAO) | NASA Langley Research Center, POWER project | NASA | Typical cloud by month for every cell (`cloud_cells.json`); temperature by month for every cell (`temperature_cells.json`). The answers name January 2001 to December 2025 as the period; the temperature values fit 2001 to 2020 (`temperature_cells.json`, `meta.years_fit`); the cloud values were not checked that way | `https://power.larc.nasa.gov/api/temporal/climatology/regional` | https://power.larc.nasa.gov/docs/referencing/ ; NASA Earth science data are CC0 unless marked (https://www.earthdata.nasa.gov/engage/open-data-services-software-policies/data-use-guidance) | Credit D | Yes (12 MB of cloud and 54 MB of temperature JSON), but the folders are git-ignored and can be fetched again | Yes |
| 5 | NASA POWER, daily point API, parameters `T2M`, `T2M_MAX`, `T2M_MIN`, `TS`, `SNODP`, `FRSNO` (MERRA-2) | NASA Langley POWER; reanalysis by NASA GMAO | NASA | Daily temperature at six named places, for ten-day means and mean daily maximum and minimum (`temperature_cells.json`, `meta.named_places`); a second opinion on snow at 18 places | `https://power.larc.nasa.gov/api/temporal/daily/point` | Same as row 4 | Credit D | Yes | Yes |
| 6 | Copernicus DEM GLO-90 (elevation `DEM` and water mask `WBM` tiles, 1 degree) | European Union and ESA under the Copernicus programme; made by Airbus Defence and Space from DLR's TanDEM-X; hosted in the AWS open-data bucket by Sinergise | Partner (ESA) | Terrain horizon and slopes of every cell; land share of Antarctic cells | `https://copernicus-dem-90m.s3.amazonaws.com` | "Licence for COP-DEM-GLO-90-F Global 90m Full, Free & Open", inside https://dataspace.copernicus.eu/sites/default/files/media/files/2025-06/copernicus_contributing_mission_data_access_v2_cop_dem_licenses.pdf (opened; it grants reproduction, distribution, communication to the public, adaptation and combination, free of charge, with a notice). Summary page: https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM | Credit E (two wordings: one for the data as it is, one for anything made from it) | Allowed with the notice, but 2.8 GB in 4,373 files: do not commit | Yes, with the "produced using" notice |
| 7 | ESA WorldCover 10 m 2021 v200 | ESA WorldCover consortium (VITO and partners) | Partner (ESA) | Share of bare ground in each northern cell | `https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map` | CC BY 4.0, stated on https://esa-worldcover.org/en/data-access | Credit F | Allowed with credit; we keep 761 reduced tiles (95 MB): do not commit, they can be rebuilt | Yes, with credit |
| 8 | IMS Daily Northern Hemisphere Snow and Ice Analysis, 4 km, version 1 (NSIDC G02156) | U.S. National Ice Center (NOAA); distributed by the National Snow and Ice Data Center | Other (NOAA) | Odds of snow-free ground in each ten-day period, October 2015 to September 2025 | `https://noaadata.apps.nsidc.org/NOAA/G02156/GIS/4km/` | https://nsidc.org/data/g02156/versions/1 says: "As a condition of using these data, you must cite the use of this data set." General terms: https://nsidc.org/about/data-use-and-copyright | Credit G | A U.S. government product, free to share with the citation, but 308 MB (740 maps): do not commit | Yes, with the citation |
| 9 | Global Historical Climatology Network - Daily (GHCN-Daily), version 3 | NOAA National Centers for Environmental Information | Other (NOAA) | Snow depth at weather stations, to check the satellite snow odds | `https://www.ncei.noaa.gov/data/global-historical-climatology-network-daily/access/<ID>.csv` | Use constraints on https://www.ncei.noaa.gov/metadata/geoportal/rest/metadata/item/gov.noaa.ncdc:C00861/html : cite the dataset and the paper; no other limit listed | Credit H | No limit found, but the files come from many national weather services and total 1.4 GB: do not commit | Yes, with the citation |
| 10 | Open-Meteo Historical Weather API, models ERA5-Land and CERRA | Open-Meteo (API); data from the Copernicus Climate Change Service, made by ECMWF | Other | A second opinion on snow at 18 places (`second_opinion_snow.json`). Not in any score | `https://archive-api.open-meteo.com/v1/archive` | API data CC BY 4.0 (https://open-meteo.com/en/licence); the free API is for non-commercial use, under 10,000 calls a day (https://open-meteo.com/en/terms). The Copernicus licence PDF linked there was not opened | Credit I | Yes with credit (5.4 MB, 54 files) | Yes, with credit |
| 11 | SCAR Antarctic Digital Database: "Automatically extracted rock outcrop dataset for Antarctica", version 7.3 | Laura Gerrish, British Antarctic Survey; UK Polar Data Centre (NERC) for SCAR | Other | Bare rock in each Antarctic cell (first layer) | https://ramadda.data.bas.ac.uk/repository/entry/show?entryid=178ec50d-1ffb-42a4-a4a3-1145419da2bb | **CC BY 4.0. Settled:** the DataCite record of doi:10.5285/178ec50d-1ffb-42a4-a4a3-1145419da2bb lists "Creative Commons Attribution 4.0 International" (https://api.datacite.org/dois/10.5285/178ec50d-1ffb-42a4-a4a3-1145419da2bb). The map-service abstract says the underlying paper is CC BY 3.0 | Credit J | Allowed with credit; 39 MB zip: do not commit | Yes, with credit |
| 12 | SCAR Antarctic Digital Database: "Medium resolution vector polygons of Antarctic rock outcrop", version 7.11 | Skachkova, Gerrish, Fretwell and Cooper, British Antarctic Survey; UK Polar Data Centre | Other | Bare rock in each Antarctic cell (second layer, to compare) | https://ramadda.data.bas.ac.uk/repository/entry/show?entryid=3f0c400f-04b9-4819-98cb-f6b53716aca5 | **CC BY 4.0. Settled:** stated on the entry page itself and in the DataCite record of doi:10.5285/3f0c400f-04b9-4819-98cb-f6b53716aca5 | Credit K | Allowed with credit; 7 MB zip | Yes, with credit |
| 13 | COMNAP Antarctic Facilities list, version 3.2.0 (13 May 2019), read through the Antarctic Digital Database map service | Council of Managers of National Antarctic Programs (COMNAP); copy hosted by the Polar Geospatial Center and served by BAS | Other | Nearest station to each Antarctic site (`antarctic_sites.json`, `known_analogs_check.json`) | `https://add.data.bas.ac.uk/geoserver/add/wfs` layer `add:antarctic_facilities` | **Not open. Settled:** "The COMNAP facilities list is copyright to COMNAP ... Data may be freely used for educational and non-commercial purposes only. Reference for the use of the material is COMNAP 2024" (https://github.com/PolarGeospatialCenter/comnap-antarctic-facilities, marked deprecated; the same sentence with "COMNAP 2025" is on https://www.comnap.aq/antarctic-facilities-information). The copy we read is the 2019 one | Credit L | **No.** Keep `data/raw/antarctica/comnap_facilities/` out of the repository | Station names, status and distances only, with the credit and the words "educational and non-commercial use only". These fields are not covered by the Apache 2.0 or CC licences of the rest. Our files (`antarctic_sites.json`, `known_analogs_check.json`) hold COMNAP station names, seasonality, status and distances, and no COMNAP coordinates |
| 14 | Natural Earth 1:50m land | Natural Earth (Tom Patterson, Nathaniel Vaughn Kelso and contributors) | Other | Land outline on the map (`site/data/land.json`) | Not recorded in the code; the raw file is `data/raw/naturalearth/ne_50m_land.geojson` | Public domain: https://www.naturalearthdata.com/about/terms-of-use/ ("No permission is needed ... Crediting the authors is unnecessary") | Credit M (optional) | Yes (1.6 MB) | Yes |
| 15 | Our list of known analog sites, `data/reference/known_analogs.json` (85 sites) | Compiled by the team from the pages linked in each entry: 57 Wikipedia pages (20 of them the table of "Terrestrial analogue site"), 28 papers and agency pages | Other | Marks cells near an already used site as "known" | Hand-compiled; `source_url` in each entry | **Settled:** names and coordinates are facts; the descriptions are our own words (a check found no run of six words shared with the Wikipedia article). Wikipedia text is CC BY-SA 4.0. To be safe the list is offered under **CC BY-SA 4.0** with credit to Wikipedia contributors, not under Apache 2.0 | Credit N | Yes, under CC BY-SA 4.0 | Yes |
| 16 | Our list of anorthosite bodies, `data/reference/anorthosite_bodies.json` (28 bodies) | Compiled by the team from GEUS Bulletin (11 entries), NGU Bulletin (4), Wikipedia (5), journal papers and NASA and ESA pages (8) | Other | Rock match for each cell | Hand-compiled; `source_url` in each entry | Facts with links; no text copied (not machine-checked). The licences of the individual papers were not opened. Offer it under CC BY-SA 4.0 like row 15, since 5 entries rest on Wikipedia | Cite each `source_url`; Credit N for the Wikipedia entries | Yes | Yes |
| 17 | The Catalogue of Planetary Analogues (2012) | The Open University for ESA (contract 4000104716/11/NL/AF); the copy we read is on a third-party host | Other (ESA-funded literature, not ESA data) | A check of our known-site list (`known_analogs_check.json`) | https://freight.cargo.site/m/D1821053255089660420449933921929/The-Catalogue-of-Planetary-Analogues.pdf | No licence in the document. We keep coordinates and one-line paraphrases only | Cite as: Preston, L., Grady, M. and Barber, S. (2012), The Catalogue of Planetary Analogues, The Open University, under ESA contract 4000104716/11/NL/AF | **No** (12.8 MB PDF, no licence) | Yes (facts with the citation) |
| 18 | Wikipedia, "Terrestrial analogue site" (wikitext read 14 November 2026) | Wikipedia contributors | Other | The same check | `https://en.wikipedia.org/w/index.php?title=Terrestrial_analogue_site&action=raw` | CC BY-SA 4.0 | Credit N | Allowed under CC BY-SA 4.0; simpler to leave it out | Yes, with credit |
| 19 | LRO Diviner Polar Resource Product, south (`dlre_prp_south.tab`), PDS data set LRO-L-DLRE-5-PRP-V2.0 | Diviner team (D. Paige and others); archived by the NASA Planetary Data System, Geosciences Node (Washington University in St. Louis) | NASA | Model-based temperature and ice stability at the lunar regions (`moon_cards.json`) | `https://pds-geosciences.wustl.edu/lro/urn-nasa-pds-lro_diviner_derived1/data_derived_prp/` | The catalogue file in the bundle (`prpds.cat`) asks for a citation and names no licence; the words "licence" and "copyright" do not occur in the labels on disk. The Planetary Data System's general data-use page was not opened | Credit O | Allowed as far as we can tell, but 605 MB (over GitHub's 100 MB limit): do not commit | Yes, with the citation and the words "model values" |
| 20 | LROC low-Sun NAC mosaic pages for the lunar regions | Lunar Reconnaissance Orbiter Camera team, Arizona State University | NASA | Links and a credit line on the lunar cards. No image is downloaded or shown | `https://data.lroc.im-ldi.com/lroc/view_rdr/<product>` | https://lroc.im-ldi.com/about/terms (opened): credit images "NASA/GSFC/Arizona State University" | Credit P | The saved HTML pages in `data/raw/moon_provenance/` are copies of web pages: keep them out | Links and credit only |
| 21 | NASA Moon Fact Sheet, the NASA release of 19 August 2022, NASA abstracts NTRS 20250011660 and 20250002110, NASA SVS 5013 and 5074 | NASA (the fact sheet is on nssdc.gsfc.nasa.gov; the abstracts are from Johnson Space Center) | NASA | Text sources for the lunar cards: gravity, night pressure and synodic period; the names of the 13 regions of 2022 and the nine of 2024 | https://nssdc.gsfc.nasa.gov/planetary/factsheet/moonfact.html , https://ntrs.nasa.gov/citations/20250011660 and the links on each card | NASA pages; no licence page was opened for them. We quote numbers and names, not text | Name NASA and link the page | The saved copies in `data/raw/moon_provenance/` stay out | Yes (facts with links) |
| 22 | OurAirports airports table, `airports.csv` (86,363 rows; 48,078 fixed-wing airfields used, 4,134 of them with scheduled service) | OurAirports (David Megginson and volunteer contributors); published from the GitHub repository davidmegginson/ourairports-data | Other | Straight-line distance from each cell to the nearest runway and to the nearest runway with scheduled service (`access_cells.json`; section (m) of `RESULTS.md`). Not in any score | `https://davidmegginson.github.io/ourairports-data/airports.csv` (fallback: the same file on raw.githubusercontent.com) | Public domain: The Unlicense, first line of the repository's LICENSE file (copy in `data/raw/ourairports/LICENSE`). The site's own data dictionary and licence wording on ourairports.com could not be read: its certificate had expired on 6 November 2026 and the check was not switched off | Credit Q | Allowed (public domain), 12.8 MB | Yes |

Downloaded while scouting Antarctica and **used by nothing** in the pipeline (all under `data/raw/antarctica/`):
Quantarctica 3 base map (Norwegian Polar Institute), NOAA GMASI 2 km snow and ice maps, MODIS MOD10A1 v6.1
snow crops read through the Microsoft Planetary Computer, and two sample extracts of the rock layers. Their
terms were not opened today. Keep them out of the repository and do not credit them as sources.

Links only, no data taken: OpenStreetMap (the place card opens the coordinates there), Carnegie Mellon's
page on the 2001 Sun-following rover test.

## 1b. Sources added for the Mars part, the factor layers, the power section and the steady influences

Found the same way as section 1: the `meta` block of each new file in `data/derived`, every URL in `scripts/` and
`twinfinder/`, and the new folders of `data/raw`. Where our files did not record the terms, the provider's own page
was opened on 14 November 2026 at about 23:10 Pacific time. The header was `User-Agent: twinfinder/0.1`.

| # | Full name | Provider | Group | What we use it for | Link we fetch from | Licence or terms | Credit the provider asks for | Raw files in a public repository? | Derived products in a public repository? |
|---|---|---|---|---|---|---|---|---|---|
| 23 | MGS MOLA Mission Experiment Gridded Data Record (MEGDR), median topography, 32 pixels per degree, `megt90n000fb` (PDS data set MGS-M-MOLA-5-MEGDR-L3-V1.0) | Mars Global Surveyor MOLA team; NASA Planetary Data System, Geosciences Node (Washington University in St. Louis) | NASA | Mars: slopes and relief of the 57 Mars sites (`mars_terrain.json`, `mars_ground.json`) | `https://pds-geosciences.wustl.edu/mgs/urn-nasa-pds-mgs_mola_topography_derived/meg032/megt90n000fb.img` (and `.lbl`) | No licence page opened. Our file says: NASA archive data; NASA material is not copyrighted in the US (general NASA policy, not opened for this product) | Credit R | Allowed as far as we can tell, but 127 MB (over GitHub's 100 MB limit): do not commit | Yes, with the citation |
| 24 | ETOPO 2022 Global Relief Model v1, 60 arc-second surface elevation (ice surface on ice sheets) | NOAA National Centers for Environmental Information (NCEI) | Other (NOAA) | Mars: slopes of every half-degree Earth square, set beside the Mars sites (`mars_terrain.json`, `mars_ground.json`) | `https://www.ngdc.noaa.gov/mgg/global/relief/ETOPO2022/data/60s/60s_surface_elev_gtif/ETOPO_2022_v1_60s_N90W180_surface.tif` | **Confirmed.** The NCEI metadata record says "Not subject to copyright protection within the United States". It asks for a citation and says "Not to be used for navigation". Opened: https://www.ncei.noaa.gov/metadata/geoportal/rest/metadata/item/gov.noaa.ngdc.mgg.dem:etopo_2022/html | Credit S | Allowed, but 444 MB: do not commit | Yes, with the citation |
| 25 | NASA POWER, Climatology API v2.10.1, more parameters. Mars climate: `T2M`, `TS`, `PRECTOTCORR`, `PS` (MERRA-2). Sun, UV and haze: `ALLSKY_SFC_UV_INDEX`, `ALLSKY_SFC_UVA`, `ALLSKY_SFC_UVB`, `ALLSKY_SFC_SW_DWN`, `CLRSKY_SFC_SW_DWN`, `ALLSKY_KT`, `CLRSKY_DAYS`, `AOD_55`, `AOD_55_ADJ`, `TOA_SW_DWN`, `ALLSKY_SFC_UV_INDEX_HR` (CERES SYN1deg). Ground and wind: `T2M_RANGE`, `GWETTOP`, `WS10M`, `WS50M` (MERRA-2), `ALLSKY_SRF_ALB` (CERES SYN1deg) | NASA Langley Research Center, POWER project | NASA | Mars: climate of every half-degree land square (`mars_climate.json`). Factors: sunlight, UV, haze, albedo, daily swing, soil wetness, wind (`environment_cells.json`, `mars_environment.json`, `power_extra_cells.json`, `mars_power_extra.json`). Power: sunlight and 50 m wind (`power_cells.json`, `mars_power.json`) | `https://power.larc.nasa.gov/api/temporal/climatology/regional`; parameter list from `https://power.larc.nasa.gov/api/system/manager/parameters?community=RE&temporal=climatology`; checks at the `hourly/point`, `monthly/point` and `climatology/point` endpoints | Same as row 4. POWER also asks users to tell the project about published uses ("Publication Notification" on https://power.larc.nasa.gov/docs/referencing/). The answers name 2001 to 2025; the Moon part found the values fit 2001 to 2020 | Credit T | Allowed, but about 480 MB in `data/raw/power_global/`, `power_global_environment/`, `power_environment/`, `power_extra/`, `power_wind/`: do not commit; they can be fetched again | Yes, with the credit |
| 26 | Mars Climate Database (MCD) v6.2, web interface; climatology average solar scenario, 2 m above the surface | Laboratoire de Météorologie Dynamique (LMD), with LATMOS, the Open University, IAA, ESA and CNES | Other (ESA and CNES are named owners, but it is LMD's product) | Mars: model climate of the 57 sites, where no lander value replaces it (`mars_climate.json`, `mars_sites.json`); daily temperature swing (`planet_factors.json`) | `https://www-mars.lmd.jussieu.fr/mcd_python/` (one request a site: five on 15 November 2026 at about 03:30 UTC, seven more at about 16:30 UTC, 45 more from 17:28 to 17:39 UTC; logs `data/raw/mars_climate/mcd/_downloads.tsv`, `_downloads_2026-11-15_new_sites.tsv` and `_downloads_2026-11-15_second_pass.tsv`) | **Restricted.** Words on https://www-mars.lmd.jussieu.fr/mars/access.html (copy: `data/raw/mars_sites/mcd_access.html`): "Scientific use of the database is freely allowed provided that the origin of the data is correctly quoted in all publications and that we are kept informed of usage and developments. This database may not be put to any commercial use without specific authorization." The web interface is "intented for moderate use only". **Open point:** the authors must be kept informed of our use; the team decides how and when to tell them | Credit U | **No.** Keep `data/raw/mars_climate/mcd/` out | MCD values only with Credit U and the words "scientific, non-commercial use". They are not covered by CC BY 4.0, because CC BY allows commercial use |
| 27 | Phoenix Meteorological (MET) data, PDS4 bundle, reduced files (RDR) and the node's reduced table `Phoenix_met_data_reduced.csv` | Phoenix MET team; NASA Planetary Data System, Atmospheres Node (New Mexico State University) | NASA | Mars: measured air temperature and pressure at the Phoenix site (`mars_climate.json`, `mars_sites.json`) | `https://atmos.nmsu.edu/PDS/data/PDS4/PHX/met_bundle/data_reduced/RDR/` and `https://atmos.nmsu.edu/data_and_services/atmospheres_data/phoenix/Phoenix_met_data_reduced.csv` | The node's page (copy: `data/raw/mars_sites/pds_atmos_phoenix_met.html`) gives a citation and no licence. The Planetary Data System's general data-use page was not opened | Credit V | Allowed as far as we can tell (a few MB) | Yes, with the citation |
| 28 | Curiosity REMS daily weather, NASA's public Mars weather feed (category `msl`) | NASA/JPL-Caltech; REMS instrument team at Centro de Astrobiología (CAB) | NASA | Mars: measured daily highs, lows and pressure at Gale (`mars_climate.json`, `mars_sites.json`) | `https://mars.nasa.gov/rss/api/?feed=weather&category=msl&feedtype=json` | No licence found. The feed carries CAB's note that it is "for outreach purposes only" (`mars_climate.json`, `meta.sites_meta.rems_caveat`). NASA's page terms were not opened | Credit W | Keep the saved feed out (1.7 MB copy of a web feed) | Figures only, labelled as outreach figures, not archive data |
| 29 | Texts that give the Mars site positions and some site figures: HiRISE page ESP_068360_1985; PDS Analyst's Notebook pages for MSL and Phoenix; the program and abstracts 1002, 1011, 1033, 1034 and 1044 of the 2015 First Landing Site/Exploration Zone Workshop; NASA NTRS 20160001040; NASA's release of 8 February 2021 on the SWIM ice maps; Rodriguez-Manfredi et al. 2023 (Nature Geoscience); Martinez et al. 2017 (Space Science Reviews); USGS Gazetteer of Planetary Nomenclature feature pages | University of Arizona (HiRISE); Washington University in St. Louis; Lunar and Planetary Institute (USRA); NASA; the journals' publishers; USGS Astrogeology for the IAU | NASA and Other | Mars: where the first five sites are and what kind they are (`mars_sites_base.json`; the other sites: rows 57 to 60); some measured figures for Jezero and Gale (`mars_climate.json`) | Each URL and time is in `data/raw/mars_sites/_downloads.tsv` | Not opened page by page. We copy coordinates and numbers only; `mars_sites_base.json` (`meta.coordinates`) names the file and exact text. USGS's Copyrights and Credits page says USGS-authored data are U.S. public domain (copy: `data/raw/usgs_quakes/usgs_copyrights_and_credits.html`) | Cite each text as `mars_sites_base.json` and `mars_climate.json` name it | **No.** 59 MB of saved papers and pages, some under publisher copyright | Yes (facts with their citations) |
| 30 | NASA Mars Fact Sheet and Earth Fact Sheet | NASA Goddard, NSSDCA | NASA | Mars and power: gravity, air pressure, day length and the like (`mars_climate.json`, `power_cells.json`, `mars_power.json`) | https://nssdc.gsfc.nasa.gov/planetary/factsheet/marsfact.html and `earthfact.html` | As row 21: NASA pages; no licence page opened. We quote numbers, not text | Name NASA and link the page | Keep the copies in `data/raw/mars_climate/factsheets/` out | Yes (facts with links) |
| 31 | NASA PDS Geosciences Node maps read at the Moon and Mars sites: MGS TES night-time thermal inertia (MGS-M-TES-5-TIMAP-V1.0, Putzig and Mellon 2007); Mars Odyssey GRS H2O, 5 x 5 degree smoothed (ODY-M-GRS-5-ELEMENTS-V1.0); Lunar Prospector neutron spectrometer "Hydrogen_halfdeg" (Feldman et al. 2001) | NASA Planetary Data System, Geosciences Node (Washington University in St. Louis), and the instrument teams | NASA | Factors: thermal inertia at the Mars sites; hydrogen at the Moon and Mars sites (`planet_factors.json`) | `https://pds-geosciences.wustl.edu/` (exact files in `planet_factors.json` and `data/raw/planet_factors/*/_downloads.tsv`) | Our file says: "Public NASA archive data; no login; no copyright restriction stated on the PDS Geosciences Node pages". No licence page opened | Credit X | Allowed as far as we can tell; `data/raw/planet_factors/` is 127 MB in all: do not commit | Yes, with the credit |
| 32 | MGS TES global bolometric albedo mosaic, 7410 m (Christensen et al. 2001) | Arizona State University (originator); published by the USGS Astrogeology Science Center | NASA (mission data published by USGS) | Factors: albedo at the Mars sites (`planet_factors.json`) | `https://planetarymaps.usgs.gov/mosaic/Mars_MGS_TES_Albedo_mosaic_global_7410m.tif` | USGS product page (copy: `data/raw/planet_factors/usgs_tes_albedo_page.html`): access constraints public domain; "Please cite authors" | Credit X | Allowed | Yes, with the citation |
| 33 | NASA pages and papers quoted for single planet-side figures: NASA release of 25 January 2024 on moonquakes; NASA APOD of 19 January 2016; NASA's InSight release of 21 December 2022; Arvidson et al. 2009 (J. Geophys. Res. 114, E00E02); Morgan et al. 2021 (Nature Astronomy 5, 230-236). Also named in `site/data/mars.json`, not checked against a saved file: Science 343, 1244797 (2014); Icarus 146, 343-359 (2000); UNSCEAR 2008 | NASA; American Geophysical Union (copy on the JPL robotics site); Nature Astronomy (manuscript on NTRS 20205008958); the other journals | NASA and Other | Factors: ice depth, surface activity and quakes at the sites (`planet_factors.json`); radiation and UV notes on the Mars cards | URLs in `planet_factors.json` and `data/raw/planet_factors/pages/_downloads.tsv` | Short phrases and numbers only. Arvidson et al.: copyright 2009 AGU. Morgan et al.: author manuscript. The NASA pages were not opened for terms | Cite each as `planet_factors.json` names it | **No** (saved papers and pages) | Yes (facts and short phrases with citations) |
| 34 | Global Lithological Map Database v1.0 (GLiM), gridded to 0.5 degree | Jens Hartmann and Nils Moosdorf; published on PANGAEA; file served by AWI's ePIC repository | Other | Factors: main rock class of each place (`rock_frozen_cells.json`, `mars_rock_frozen.json`, `estimates_cells.json`, `mars_estimates.json`) | `https://epic.awi.de/id/eprint/31092/1/hartmann-moosdorf_2012.zip` (landing page https://doi.org/10.1594/PANGAEA.788537) | **CC BY 3.0. Confirmed:** PANGAEA's own metadata record names "Creative Commons Attribution 3.0 Unported" (CC-BY-3.0, https://creativecommons.org/licenses/by/3.0/). Opened: https://doi.pangaea.de/10.1594/PANGAEA.788537?format=metainfo_xml | Credit Y | Allowed with credit (38 KB zip) | Yes, with credit |
| 35 | Ground Temperature Map, 2000-2016, Northern Hemisphere Permafrost: permafrost probability (PERPROB), version 5.0 | Obu, Westermann, Kääb and Bartsch (University of Oslo), made in ESA's GlobPermafrost project; published on PANGAEA by AWI | Other (made in an ESA project; published by PANGAEA, not by ESA) | Factors: permafrost probability and zone north of 25 N (`rock_frozen_cells.json`, `mars_rock_frozen.json`, `estimates_cells.json`, `mars_estimates.json`) | `https://store.pangaea.de/Publications/ObuJ-etal_2018/UiO_PEX_PERPROB_5.0_20181128_2000_2016_NH.zip` (landing page https://doi.org/10.1594/PANGAEA.888600) | **CC BY 3.0. Confirmed:** the PANGAEA file list saved with the download (`data/raw/permafrost/PANGAEA_888600_filelist.tab`) says "License: Creative Commons Attribution 3.0 Unported (CC-BY-3.0)" | Credit Z | Allowed with credit, but 106 MB zip and a 1.9 GB GeoTIFF: do not commit | Yes, with credit |
| 36 | Pages read for the words of the frozen-ground estimate: three NSIDC "Frozen Ground & Permafrost" pages; the CALM program page (George Washington University); Rossi et al. 2022 (Frontiers in Earth Science) | NSIDC; George Washington University; Frontiers | Other | Factors: wording only; no figure was taken (`estimates_cells.json`, `meta.frozen_ground_depth_sources`) | URLs in `estimates_cells.json` | Our file says: NSIDC asks for credit ("Courtesy of the National Snow and Ice Data Center"); CALM read only; Rossi et al. CC BY 4.0. Only facts taken, no text copied | NSIDC's credit only if NSIDC text or images are ever shown | **No** (saved pages in `data/raw/estimates/`) | Yes (no text from them) |
| 37 | USGS ANSS Comprehensive Earthquake Catalog (ComCat), FDSN event web service | U.S. Geological Survey | Other (USGS) | Factors and steady influences: earthquakes of magnitude 5 and over, 1990 to 2025 (`hazards_people_cells.json`, `mars_hazards_people.json`); small quakes of magnitude 1 to 5, 2010 to 2025 (`tremors_cells.json`, `mars_tremors.json`) | `https://earthquake.usgs.gov/fdsnws/event/1/query` | **Public domain.** "USGS-authored or produced data and information are considered to be in the U.S. Public Domain." (usgs.gov Copyrights and Credits; copy: `data/raw/usgs_quakes/usgs_copyrights_and_credits.html`) | Credit AA | Allowed; 152 MB in `data/raw/usgs_quakes/` and `usgs_small_quakes/`: do not commit | Yes, with the credit |
| 38 | Volcanoes of the World v. 5.4.0 (7 August 2026): Holocene volcano list and Holocene eruption list (GeoServer layers `GVP-VOTW:Smithsonian_VOTW_Holocene_Volcanoes` and `..._Holocene_Eruptions`) | Smithsonian Institution, Global Volcanism Program (GVP) | Other | Factors: nearest volcano (`hazards_people_cells.json`). Steady influences: volcanoes active since 1990 (`steady_effects_cells.json`). Power: geothermal class (`power_cells.json`); and the Mars copies of each | `https://webservices.volcano.si.edu/geoserver/GVP-VOTW/wfs` | Smithsonian terms of use, read in a browser on 14 November 2026 (https://volcano.si.edu/gvp_termsofuse.cfm). Personal, educational and other non-commercial use is allowed. The source must be cited and linked, and notices kept. Commercial use needs prior written permission. The terms call the database compilation a product of United States employees. The service's capabilities say "Fees: NONE" and "AccessConstraints: NONE" | Credit AB (read from the saved GVP pages) | Not needed: keep `data/raw/gvp_volcanoes/` and `gvp_eruptions/` out and point to the provider | Volcano names, years and distances with Credit AB and a link to https://volcano.si.edu/; non-commercial use only |
| 39 | GeoNames gazetteer, `cities1000` (populated places) | GeoNames | Other | Factors and steady influences: people and towns near each place (`hazards_people_cells.json`, `steady_effects_cells.json` and the Mars copies) | `https://download.geonames.org/export/dump/cities1000.zip` | **CC BY 4.0.** First lines of the readme (copy: `data/raw/geonames/readme.txt`): "This work is licensed under a Creative Commons Attribution 4.0 License" | Credit AC | Allowed with credit (11 MB) | Yes, with credit |
| 40 | Natural Earth 1:10m Cultural Vectors: roads (`ne_10m_roads`) and railroads (`ne_10m_railroads`), version 5.2.0-pre, GeoJSON | Natural Earth; GitHub repository nvkelso/natural-earth-vector | Other | Steady influences: distance to the nearest main road and railway (`steady_effects_cells.json`, `mars_steady_effects.json`) | `https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/` | **Public domain.** The repository's LICENSE.md: "Everything here is public domain." Credit is not required (copy: `data/raw/naturalearth_roads/LICENSE.md`) | Credit M (optional) | Allowed, but 86 MB: do not commit | Yes |
| 41 | Global Power Plant Database v1.3.0 (`global_power_plant_database.csv`) | World Resources Institute (WRI) with Global Energy Observatory, Google, KTH and Enipedia | Other | Power: geothermal plants near each place (`power_cells.json`, `mars_power.json`) | `https://raw.githubusercontent.com/wri/global-power-plant-database/master/output_database/global_power_plant_database.csv` (`DATABASE_VERSION` 1.3.0) | **CC BY 4.0.** The repository README (copy: `data/raw/power_plants/README.md`) says the v1.3.0 release on datasets.wri.org is "under a Creative Commons-Attribution 4.0 (CC BY 4.0) license". WRI's dataset page gives "Creative Commons Attribution" without a version (opened: https://datasets.wri.org/datasets/global-power-plant-database). We took the repository's `output_database` copy, not the release file. The README says WRI stopped maintaining it in early 2022 | Credit AD (WRI's own wording) | Allowed with credit (12 MB) | Yes, with credit |
| 42 | Blue Marble: Next Generation with topography and bathymetry, July 2004, 5400 x 2700 JPEG (`world.topo.bathy.200407.3x5400x2700.jpg`) | NASA Earth Observatory (NASA Goddard Space Flight Center) | NASA | The surface image of the Earth globe (`site/vendor/textures/earth.jpg`) | `https://assets.science.nasa.gov/content/dam/science/esd/eo/images/bmng/bmng-topography-bathymetry/july/world.topo.bathy.200407.3x5400x2700.jpg` (page: https://science.nasa.gov/earth/earth-observatory/blue-marble-next-generation/base-topography-bathymetry/) | No licence text on the product pages. The overview page asks: "Anyone using or republishing Blue Marble: Next Generation please credit “NASA Earth Observatory.”" (opened: https://science.nasa.gov/earth/earth-observatory/blue-marble-next-generation/). NASA's media usage page answered HTTP 429 to our client and was not read. NASA material is not copyrighted in the US (general NASA policy, not opened) | Credit AE | Not kept in the project (2.3 MB download) | Yes: `earth.jpg`, 4096 x 2048, 1.6 MB, with the credit |
| 43 | CGI Moon Kit, LROC colour map with the poles filled, 2019 version, 4096 x 2048 TIFF (`lroc_color_poles_4k.tif`) | NASA's Scientific Visualization Studio (NASA Goddard); colour from the LROC Wide Angle Camera mosaic (Arizona State University); polar fill from LOLA albedo | NASA | The surface image of the Moon globe (`site/vendor/textures/moon.jpg`). North of 70 N and south of 70 S the map is grey albedo, so our lunar regions show no colour detail | `https://svs.gsfc.nasa.gov/vis/a000000/a004700/a004720/lroc_color_poles_4k.tif` (page: https://svs.gsfc.nasa.gov/4720/) | **Public domain.** The SVS help page says: "All of our content is in the public domain (unless otherwise noted), meaning that it is free to download, use, and redistribute for whatever purposes you see fit." (opened: https://svs.gsfc.nasa.gov/help/). Page 4720 notes no exception | Credit AF | Not kept in the project (13 MB TIFF) | Yes: `moon.jpg`, 4096 x 2048, 2.6 MB, with the credit |
| 44 | Mars Viking Colorized Global Mosaic 232m (MDIM 2.1): the 1 km per pixel JPEG from the product's ancillary data (`Mars_Viking_MDIM21_ClrMosaic_1km.jpg`, 21339 x 10670) | USGS Astrogeology Science Center (publisher); NASA Ames (colourised mosaic); NASA Viking Orbiter images | NASA (mission data published by USGS) | The surface image of the Mars globe (`site/vendor/textures/mars.jpg`) | `https://astrogeology.usgs.gov/ckan/dataset/7131d503-cdc9-45a5-8f83-5126c0fd397e/resource/5ea881c6-01b3-41fa-a7af-42d2131b54f1/download/mars_viking_mdim21_clrmosaic_1km.jpg` (page: https://astrogeology.usgs.gov/search/map/mars_viking_colorized_global_mosaic_232m) | **Public domain.** The product page (opened) says "Access Constraints: Public domain" and "Use Constraints: None". It calls the colour "artistically colorized": natural-looking, not true colour | Credit AG | Not kept in the project (37 MB download) | Yes: `mars.jpg`, 4096 x 2048, 2.9 MB, with the credit |
| 45 | globe.gl 2.46.2, JavaScript library (`site/vendor/globe.gl.min.js`). It bundles three.js revision 185, h3-js (Apache 2.0) and the Helvetiker typeface (MgOpen licence) | The globe.gl project (https://github.com/vasturiano/globe.gl); the three.js authors (https://github.com/mrdoob/three.js) | Other | Draws the Earth, Moon and Mars globes on the page | `https://cdn.jsdelivr.net/npm/globe.gl@2.46.2/dist/globe.gl.min.js` | **MIT** for globe.gl (text in `site/vendor/globe.gl.LICENSE.txt`). **MIT** for three.js: the LICENSE file at tag r185 of the three.js repository (opened; text in `site/vendor/three.LICENSE.txt`). The h3-js and typeface notices stay inside the bundled file | Credit AH | Yes (1.9 MB), with both licence files | Not applicable |
| 46 | Natural Earth 1:10m Cultural Vectors: Admin 0 - Countries (`ne_10m_admin_0_countries`) and Admin 1 - States, Provinces (`ne_10m_admin_1_states_provinces`), GeoJSON | Natural Earth; GitHub repository nvkelso/natural-earth-vector | Other | Land status and permits: the territory that holds the centre of each area and Mars square, and the Greenland national park unit "Nationalparken" (`land_status_cells.json`, `mars_land_status.json`). Fetched 15 November 2026 | `https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/` | **Public domain**, the same terms as row 40 (copy: `data/raw/naturalearth_roads/LICENSE.md`). Credit is not required | Credit AI (optional) | Allowed, but 54 MB: do not commit (`data/raw/land_status/`) | Yes |
| 47 | Official pages for the territory rules of the land status factor, read on 15 November 2026: Secretariat of the Antarctic Treaty (https://www.ats.aq/e/antarctictreaty.html); Australian Antarctic Division (environmental approvals; protecting and managing special areas); Crown-Indigenous Relations and Northern Affairs Canada (Nunavut land and resource management); Nunavut Research Institute (research licensing); Government of the Northwest Territories (research licences); Sysselmesteren på Svalbard (research and educational activity); U.S. Bureau of Land Management (Alaska Land Transfer Program); Stjórnarráð Íslands (þjóðlendur). The full URLs are in the meta block of `land_status_cells.json` | The governments and the treaty secretariat named | Other | Short statements of fact in our own words: who owns the land in general and whom to ask for a permit | The pages themselves | Read for facts only. No text or image of these pages is copied or kept in the project | Credit AJ | Not applicable (nothing kept) | Yes: our own sentences |
| 48 | Antarctic Treaty Secretariat, ASMA and ASPA shapefile, 2024 version (`apa_shape_2024.zip`), converted from EPSG:3031 to WGS 84 and cut to the 11 ASPA polygons and 4 ASMA polygons whose box holds an area centre (`ats_aspa_2024.geojson`, `ats_asma_2024.geojson`) | Secretariat of the Antarctic Treaty | Other | Land status: the name, type and entry rule of an Antarctic Specially Protected Area or Specially Managed Area at the centre (`land_status_cells.json`, `mars_land_status.json`). Fetched 15 November 2026 | `https://documents.ats.aq/gis/apa_shape_2024.zip`, linked from https://www.ats.aq/e/protected.html | **CC BY 4.0**: the copyright page https://www.ats.aq/e/copyright.html says that ATS material can be used if the source is given, under CC BY 4.0. The metadata file in the zip states the same licence | Credit AK | Yes (1.3 MB for the cut files) | Yes |
| 49 | Canadian Protected and Conserved Areas Database (CPCAD), layer "Protected and conserved area", record modified 2025-12-31, cut to the 61 features with a polygon that holds an area centre (`cpcad_north.geojson`) | Environment and Climate Change Canada | Other | Land status: the name, type and owner type of a protected area at the centre of Canadian areas. Fetched 15 November 2026 | `https://maps-cartes.ec.gc.ca/arcgis/rest/services/CWS_SCF/CPCAD/MapServer/0` (record https://open.canada.ca/data/en/dataset/6c343726-1e92-451a-876a-76e17d398a1c) | **Open Government Licence - Canada**, https://open.canada.ca/en/open-government-licence-canada , as the open.canada.ca record states (checked again on 15 November 2026) | Credit AL | Yes (1.0 MB) | Yes |
| 50 | Aboriginal Lands of Canada Legislative Boundaries, layer 0 of CLSS_Administrative_Boundaries, cut to the 28 land claim features that hold an area centre (`aboriginal_lands_north.geojson`) | Natural Resources Canada, Canada Lands Survey System | Other | Land status: Inuit Owned Land, Yukon First Nations Settlement Land, Sahtu Land and Inuvialuit Land at the centre. Fetched 15 November 2026 | `https://proxyinternet.nrcan-rncan.gc.ca/arcgis/rest/services/CLSS-SATC/CLSS_Administrative_Boundaries/MapServer/0` (record https://open.canada.ca/data/en/dataset/522b07b9-78e2-4819-b736-ad9208eb1067) | **Open Government Licence - Canada**, https://open.canada.ca/en/open-government-licence-canada , as the open.canada.ca record states (checked again on 15 November 2026) | Credit AL | Yes (2.2 MB) | Yes |
| 51 | Friðlýst svæði á Íslandi, WFS layer fridlyst_svaedi:fridlyst_svaedi, 141 features (`iceland_protected_areas.geojson`) | Umhverfis- og orkustofnun; Náttúruverndarstofnun manages most protected areas | Other | Land status: the name and type of a protected area at the centre of Icelandic areas and Mars squares. Fetched 15 November 2026 | `https://gis.ust.is/geoserver/wfs` (record https://gatt.natt.is/geonetwork/srv/api/records/%7B6D940937-15DB-4D50-833B-37D2F2AB1207%7D) | No use limitations; cite the source; do not change the area boundaries. Stated in the metadata record (checked again on 15 November 2026). We did not change any boundary | Credit AM | Yes (5.6 MB) | Yes |
| 52 | Naturvernområder, layer naturvern_omrade: 32 features for Svalbard, Jan Mayen and mainland Norway (`norway_protected_areas_miljodirektoratet.geojson`) and record VV00003010, Jan Mayen naturreservat (`jan_mayen_naturvernomrade.geojson`) | Miljødirektoratet (Norwegian Environment Agency) | Other | Land status: the name, type and management authority of a protected area at the centre. Fetched 15 November 2026 | `https://kart.miljodirektoratet.no/arcgis/rest/services/vern/FeatureServer/0` (metadata https://kartkatalog.geonorge.no/api/getdata/5857ec0a-8d2c-4cd8-baa2-0dc54ae213b4) | **Norsk lisens for offentlige data (NLOD) 2.0**, https://data.norge.no/nlod/en/2.0 , as the Geonorge metadata states (checked again on 15 November 2026) | Credit AN | Yes (1.8 MB) | Yes |
| 53 | Skyddade områden, Naturvårdsregistret WFS layer Naturvardsregistret_WFS:SkyddadeOmraden, the two national parks that hold an area centre (`sweden_protected_areas_naturvardsverket.geojson`) | Naturvårdsverket (Swedish Environmental Protection Agency) | Other | Land status: the national park name and manager at the centre of Swedish areas. Fetched 15 November 2026 | `https://geodata.naturvardsverket.se/naturvardsregistret/wfs` | **CC0**, stated in https://geodata.naturvardsverket.se/nedladdning/naturvardsregistret/Naturvardsregistret_beskrivning_av_oppna_data.pdf | Credit AO | Yes (0.1 MB) | Yes |
| 54 | Protected Areas Database of the United States (PAD-US) 4.1, layer PAD-US Fee Managers, Fee features at the Alaska centres, 29 features (`padus41_fee_managers_alaska.geojson`) | U.S. Geological Survey (USGS), Gap Analysis Project | Other | Land status: the protected unit name, GAP status and public access at the centre of Alaska areas. Fetched 15 November 2026 | `https://services.arcgis.com/v01gqwM5QqNysAAi/arcgis/rest/services/Fee_Managers_PADUS/FeatureServer/0`, a USGS item listed on https://www.usgs.gov/programs/gap-analysis-project/science/pad-us-web-services | **Public domain**: the FGDC metadata says "These data are in the public domain." (https://www.sciencebase.gov/catalog/item/652d4fc5d34e44db0e2ee45e) | Credit AP | Yes (9.2 MB) | Yes |
| 55 | BLM AK Administered Lands (SMA), data of 31 August 2026, the 112 features that hold an Alaska centre (`blm_ak_administered_lands_sma_alaska.geojson`); the BLM AK Land Status Conveyed Lands service, asked about 11 centres as a check only | U.S. Bureau of Land Management, Alaska State Office | Other | Land status: the surface management agency or the owner type at the centre of Alaska areas. Fetched 15 November 2026 | `https://gis.blm.gov/akarcgis/rest/services/lands/BLM_AK_Administered_Lands_SMA/FeatureServer` | **Public domain**: the service metadata says "None, these data are considered public domain." The BLM asks users to cite it and to describe changes | Credit AQ | Yes (2.8 MB) | Yes |
| 56 | Official pages for the territory rules and entry rules added by the regional pass of the land status factor, read on 15 November 2026: Secretariat of the Antarctic Treaty (National Competent Authorities; Annex V; protected areas; environmental impact assessment); Crown-Indigenous Relations and Northern Affairs Canada (Sahtu agreement; Umbrella Final Agreement); Avannaata Kommunia (area allotments); Expedition Office of the Government of Greenland (expedition permits); Stjórnarráð Íslands (friðlýsingar); Náttúruverndarstofnun (permits in protected areas); Lovdata (Jan Mayen naturreservat; finnmarksloven; friluftsloven; Svalbard Environmental Protection Act); Sysselmesteren på Svalbard (protected areas); Finnmarkseiendommen; Statskog; Sveriges riksdag (Miljöbalk); Naturvårdsverket (right of public access); President of Russia, kremlin.ru (Land Code); U.S. Bureau of Land Management; National Park Service; U.S. Fish and Wildlife Service; Alaska Department of Natural Resources; Ahtna, Incorporated; Eklutna, Inc.; Cook Inlet Region, Inc. The full URLs are in the meta block of `land_status_cells.json` | The governments, agencies, landowners and the treaty secretariat named | Other | Short statements of fact in our own words: who owns the land in general, entry rules and whom to ask for a permit | The pages themselves | Read for facts only. No text or image of these pages is copied into the results | Credit AR | Not applicable (text copies of the Antarctic pages are kept with the raw files only) | Yes: our own sentences |
| 57 | Texts that give the positions of the seven Mars sites added on 15 November 2026: NASA NSSDCA spacecraft pages of Viking 1 Lander (1975-075C), Viking 2 Lander (1975-083C), Mars Pathfinder (1996-068A), Spirit (2003-027A), Opportunity (2003-032A) and InSight (2018-042A), and the NSSDCA project pages of Viking and Mars Pathfinder; the PDS Analyst's Notebook MER mission overview; Golombek et al. 2020, Geology of the InSight landing site on Mars (Nature Communications 11, 1014, open access); Golombek et al. 2021, SpaceX Starship landing sites on Mars (52nd LPSC, abstract 2420); USGS Gazetteer of Planetary Nomenclature, Phlegra Montes (feature 4701) | NASA Space Science Data Coordinated Archive (Goddard); Washington University in St. Louis (PDS Geosciences Node); Springer Nature; Lunar and Planetary Institute (USRA); USGS Astrogeology for the IAU | NASA and Other | Mars: where the seven new sites are, what kind they are and what the missions found at the surface (`mars_sites_base.json`) | Each URL and time is in `data/raw/mars_sites/_downloads_2026-11-15_new_sites.tsv` | Not opened page by page. We copy coordinates and short facts only; `mars_sites_base.json` (`meta.coordinates`) names the file and exact text. NASA material is not copyrighted in the US (general NASA policy, not opened for these pages). The InSight paper is open access under CC BY 4.0 (stated on the paper). The LPSC abstract is published by the Lunar and Planetary Institute | Credit AS | **No.** Approximately 34 MB of saved papers and pages (with five copies of the gazetteer search page, approximately 5 MB each, that do not filter by name and that nothing uses) | Yes (facts with their citations) |
| 58 | Abstracts of the First Landing Site/Exploration Zone Workshop for Human Missions to the Surface of Mars (Lunar and Planetary Institute, Houston, 27-30 October 2015): 45 abstracts give the 39 exploration zones added on 15 November 2026 and the zones at the place of a present site (Gale, Jezero, Spirit, Viking 1, Arcadia Planitia, Deuteronilus Mensae). Positions as each abstract wrote them, collected in `data/reference/mars_exploration_zones_2015.json`; also NASA's compiled abstract set (abstracts 1031 and 1056) and the program | The authors of each abstract; Lunar and Planetary Institute (USRA), publisher; NASA (compiled abstract set) | NASA and Other | Mars: where the exploration zones are, their names, and one sentence of our own words on each zone (`mars_sites_base.json`, `mars_sites.json`, `site/data/mars.json`) | `https://www.hou.usra.edu/meetings/explorationzone2015/pdf/<number>.pdf`; `https://www.nasa.gov/wp-content/uploads/2015/06/mars-c-abstracts_in_order_of_presentation10242015_0.pdf` | The abstracts are (c) their authors, published by the Lunar and Planetary Institute. No licence page opened. We take only names, positions and one sentence of our own words for each zone; no text or figure of an abstract is copied | Credit AT | **No.** The saved PDFs in `data/raw/mars_sites/ezworkshop2015/` (approximately 60 MB with the NASA files of row 59) are (c) their authors | Yes (names, positions and our own sentences, with citations) |
| 59 | Potential Exploration Zones for Human Missions to the Surface of Mars (NASA's map of the proposed zones): version 10, vector PDF; version 12 (16 October 2015), JPG | NASA Mars Program Office | NASA | Mars: the position of zone 1051 (Hypanis), which its abstract does not give in words (the centre of its circle, 11.98 N, 313.94 E); the list file also uses the map to check the stated positions of the other zones | `https://www3.nasa.gov/sites/default/files/atoms/files/exploration-zone-map-v10.pdf`; `https://www3.nasa.gov/sites/default/files/thumbnails/image/map-of-proposed-exploration-zones.jpg` | No licence page opened. NASA material is not copyrighted in the US (general NASA policy, not opened for this map) | Credit AU | Allowed as far as we can tell (1.0 MB and 2.7 MB); not necessary | Yes (one position, with the citation) |
| 60 | Golombek, M., et al. (2021), SpaceX Starship landing sites on Mars, 52nd Lunar and Planetary Science Conference, abstract 2420 (LPI Contrib. No. 2548), Table 1: the other six sites, AP-1, AP-9, EM-16, AP-8, EM-15 and PM-7 (PM-1 is in row 57) | The authors (JPL, SpaceX and university authors); Lunar and Planetary Institute (USRA), publisher | Other | Mars: where the six sites of the 2021 shortlist are, and short facts on each from the text (`mars_sites_base.json`) | `https://www.hou.usra.edu/meetings/lpsc2021/pdf/2420.pdf` (saved on 15 November 2026 at 16:22 UTC, `data/raw/mars_sites/_downloads_2026-11-15_new_sites.tsv`) | The abstract is (c) its authors, published by the Lunar and Planetary Institute. No licence page opened. We copy positions and short facts only | Credit AV | **No.** (c) its authors | Yes (facts with their citations) |
| 61 | NASA's map of the nine candidate landing regions for Artemis III, the image of NASA release 24-136 of 28 October 2024 (`artemis-iii-landing-region-candidates.jpg`). Its background is a mosaic of LRO Wide Angle Camera images | NASA | NASA | The Moon: the centres of the three lunar regions without a terrain model (Peak near Cabeus B, Mons Mouton Plateau and Slater Plain), and a check of the other six boxes. We fitted the map to lunar coordinates with the six boxes that have a terrain model; the largest error at those boxes is less than 0.2 km. `data/reference/lunar_candidate_regions.json` (`meta.how_sure_values`, `meta.sources`) says how. `twinfinder/moon.py` holds a copy of the three centres and boxes | `https://www.nasa.gov/wp-content/uploads/2024/10/artemis-iii-landing-region-candidates.jpg` (page: https://www.nasa.gov/news-release/nasa-provides-update-on-artemis-iii-moon-landing-regions/), read on 15 November 2026 | The release gives "Credit: NASA" under the map (copy: `data/raw/lunar_regions_provenance/nasa_2024-10-28_nine_regions.html`). No licence page opened. NASA material is not copyrighted in the US (general NASA policy, not opened for this map) | Credit AW | Allowed as far as we can tell (0.6 MB); not necessary. The saved copy stays in `data/raw/lunar_regions_provenance/` | Yes (three positions, with the credit) |
| 62 | Lunar Grid Reference System (LGRS) Artemis III Candidate Landing Site Navigational Grids in Artemis Condensed Coordinate (ACC) Format, USGS data release, doi:10.5066/P13FD9ZD: the file `LGRS_A3CLR_Grid_Generation.sh` | U.S. Geological Survey, Astrogeology Science Center | Other (USGS) | The Moon: the corners of the box of each of the 13 regions of 2022. They are a check of each NASA 5 m terrain model (the corners agree to less than 1 m) and of the 2022 name "Leibnitz Beta Plateau" for the box "Mons Mouton" (`data/reference/lunar_candidate_regions.json`, `meta.sources`) | `https://www.sciencebase.gov/catalog/item/67168797d34ebf903f48b6fc`, read as text on 15 November 2026; the script was not run | **CC0.** The ScienceBase record says: "This work is marked with Creative Commons Zero v1.0 Universal" (copy: `data/raw/lunar_regions_provenance/usgs_lgrs_sciencebase_item.json`). The metadata gives "None" as the use constraints. The record gives 5 November 2024 as the publication date; our other files say 2 November 2024 | Credit AX | Allowed (CC0; the script is 6 KB); not necessary | Yes |

Row 22 (OurAirports) is now also read by the steady influences (`steady_effects_cells.json`): credit Q. ESA WorldCover (row 7)
now also gives the bare share of every half-degree square for the Mars part (`mars_climate.json`): credit F. JPL Horizons
(row 3) has a third use: `scripts/check_against_horizons.py` checks our Sun positions at nine Earth places
(`data/raw/horizons_check/`): credit C.

Downloaded or read for the new parts and **used by nothing** in the results: the Antarctic permafrost map (PANGAEA
902576, CC BY 4.0, in `data/raw/permafrost/ant/`); the Mars cave catalogue pages and the LROC pit atlas pages (dropped);
the Viking IRTM rock abundance page, the Diviner rock-abundance label and the Diviner polar temperature index (read, no
figure kept); the Mars 2020 weather
feed; NTRS 20150013826; workshop abstract 1020; the USGS news page on the Mars 2020 landing; the PDS LEND page.
Keep them out of the repository and do not credit them as sources.

Links only, no data taken (the site planner): NASA's D-RATS 2022 test report (NTRS 20230017073), the Johnson Space
Center lighting study (NTRS 20240011393) and the USGS page on the JETT5 Artemis III tests.

## 2. Must not be committed to a public repository

`data/raw/` is already in `.gitignore`. Keep it that way. The reasons, by folder:

Terms forbid it or give no permission:
- `data/raw/antarctica/comnap_facilities/` (COMNAP: educational and non-commercial use only, copyright COMNAP).
- `data/raw/analog_catalogues/The-Catalogue-of-Planetary-Analogues.pdf` (no licence; a third-party copy).
- `data/raw/antarctica/quantarctica3_basemap/`, `gmasi_2km/`, `modis_samples/`, `arcgis_samples/`, `wfs_samples/`
  (terms not checked; not used).
- `data/raw/mars_climate/mcd/` (Mars Climate Database answers: scientific use only, no commercial use without permission).
- `data/raw/gvp_volcanoes/` and `data/raw/gvp_eruptions/` (Smithsonian terms: non-commercial use with the citation; the provider serves the lists itself).
- `data/raw/mars_sites/` and `data/raw/planet_factors/pages/` (papers, abstracts and pages; some under publisher
  copyright). Also the saved Curiosity weather feed in `data/raw/mars_sites/`.
- `data/raw/estimates/` (copies of NSIDC, CALM and Frontiers pages).

Allowed, but too large (anyone can fetch them again with the scripts):
- `data/raw/glo90/` 2.8 GB; `data/raw/ghcn/` 1.4 GB; `data/raw/ims/` 308 MB; `data/raw/antarctica/` 140 MB in all.
- The 13 lunar terrain files (approximately 41 to 142 MB each, approximately 892 MB in all; Site20v2 and Haworth
  are over GitHub's limit of 100 MiB) and
  `AVGVISIB_65S_240M_201608.TIF` (58 MB).
- `data/raw/diviner/` 593 MB on disk (the table alone is 605 million bytes, over GitHub's 100 MB limit).
- `data/raw/worldcover/` 95 MB; `data/raw/power_temperature/` 54 MB; `data/raw/power/` 12 MB;
  `data/raw/reanalysis/` 5 MB; `data/raw/horizons_sunpath/` 1.4 MB.
- Added for the new parts: `data/raw/permafrost/` 2.8 GB; `data/raw/etopo/` 444 MB; `data/raw/power_global_environment/`
  192 MB; `data/raw/power_global/` 167 MB; `data/raw/usgs_small_quakes/` 142 MB; `data/raw/mola/` 127 MB (one file over
  GitHub's 100 MB limit); `data/raw/planet_factors/` 127 MB; `data/raw/naturalearth_roads/` 86 MB;
  `data/raw/power_extra/` 69 MB; `data/raw/power_environment/` 34 MB; `data/raw/power_wind/` 21 MB;
  `data/raw/power_plants/`, `geonames/` and `usgs_quakes/` about 10 MB each; `data/raw/horizons_check/` 8 MB.

Saved copies of web pages (kept as evidence of what was read; not ours to republish):
- `data/raw/moon_provenance/` (NASA, NTRS, PGDA and LROC pages, 1.7 MB) and `data/raw/additions_check_links/`
  (the licence pages opened again in the late check, 2.2 MB).

Also check before the first push: on 15 November 2026, `data/derived/` holds approximately 1.2 GB. Four of its
files are larger than 50 MB, and three of them are larger than GitHub's limit of 100 MiB. `docs/PUBLIC-COPY.md` gives the files of
the public copy, their sizes and what to do with each large file.

## 3. Credit lines to print on the page and in the README

Print these as written. Dates in brackets are the day we fetched the data.

- **A. LOLA 5 m terrain (PGDA 78):** Barker, M.K., et al. (2021), Improved LOLA Elevation Maps for South Pole
  Landing Sites: Error Estimates and Their Impact on Illumination Conditions, Planetary & Space Science,
  Volume 203, 105119, doi:10.1016/j.pss.2020.105119. Data: NASA Goddard Planetary Geodesy Data Archive,
  https://pgda.gsfc.nasa.gov/products/78
- **B. LOLA illumination maps (PGDA 69):** Mazarico, E., et al. (2011), Illumination conditions of the lunar
  polar regions using LOLA topography, Icarus, Volume 211, Issue 2, 1066-1081, doi:10.1016/j.icarus.2010.10.030.
- **C. JPL Horizons:** NASA/JPL Solar System Dynamics. Data retrieved on 2026, November, 14. Horizons System.
  https://ssd.jpl.nasa.gov (the two lunar Sun tables were fetched on 15 November 2026 at 00:01 UTC, which is
  14 November in the Pacific time zone; the retrieval day of the reference values in `tests/test_sun.py` is
  not recorded in the code).
- **D. NASA POWER:** The data was obtained from National Aeronautics and Space Administration (NASA) Langley
  Research Center's Prediction Of Worldwide Energy Resources (POWER) project funded through the NASA Earth
  Science Division. The data was obtained from the POWER Project's Climatology and Daily 2.10.1 version on
  2026/11/14. (Cloud amount: CERES SYN1deg. Temperature and snow: MERRA-2.) The temperature requests ran
  from 23:55 UTC on 14 November to 00:04 UTC on 15 November 2026.
- **E. Copernicus DEM GLO-90.** Beside anything we computed from it (horizons, slopes, the map):
  "produced using Copernicus WorldDEM-90 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018
  provided under COPERNICUS by the European Union and ESA; all rights reserved".
  If the tiles themselves were ever shared: "© DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH
  2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved". The licence (Article 6 c) also
  prescribes this sentence in any notice that covers sharing the data, changed or not: "The organisations in
  charge of the Copernicus programme by law or by delegation do not incur any liability for any use of the
  Copernicus WorldDEM-90". And (Article 6 d) we must not give the impression that our work is endorsed by them.
- **F. ESA WorldCover:** © ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021)
  processed by ESA WorldCover consortium. Citation: Zanaga, D., Van De Kerchove, R., Daems, D., De Keersmaecker,
  W., Brockmann, C., Kirches, G., Wevers, J., Cartus, O., Santoro, M., Fritz, S., Lesiv, M., Herold, M.,
  Tsendbazar, N.E., Xu, P., Ramoino, F., Arino, O., 2022. ESA WorldCover 10 m 2021 v200.
  https://doi.org/10.5281/zenodo.7254221 (CC BY 4.0).
- **G. IMS snow maps:** U.S. National Ice Center. (2008). IMS Daily Northern Hemisphere Snow and Ice Analysis
  at 1 km, 4 km, and 24 km Resolutions. (G02156, Version 1). [Data Set]. Boulder, Colorado USA. National Snow
  and Ice Data Center. https://doi.org/10.7265/N52R3PMC. 4 km GeoTIFF maps, every fifth day, 1 October 2015 to
  28 September 2025 (740 maps). Date Accessed 11-14-2026.
- **H. GHCN-Daily:** Menne, M.J., I. Durre, B. Korzeniewski, S. McNeill, K. Thomas, X. Yin, S. Anthony, R. Ray,
  R.S. Vose, B.E. Gleason, and T.G. Houston, 2012: Global Historical Climatology Network - Daily (GHCN-Daily),
  Version 3. NOAA National Climatic Data Center. http://doi.org/10.7289/V5D21VHZ [14 November 2026]. And:
  Menne, M.J., I. Durre, R.S. Vose, B.E. Gleason, and T.G. Houston, 2012: An overview of the Global Historical
  Climatology Network-Daily Database. Journal of Atmospheric and Oceanic Technology, 29, 897-910,
  doi:10.1175/JTECH-D-11-00103.1.
- **I. Open-Meteo:** "Weather data by Open-Meteo.com" as a link to https://open-meteo.com/ , licence CC BY 4.0
  (https://creativecommons.org/licenses/by/4.0/). Add: "Contains modified Copernicus Climate Change Service
  information 2026 (ERA5-Land, CERRA)". The second sentence is the usual Copernicus wording; the Copernicus
  licence itself was not opened today.
- **J. Antarctic rock outcrop, Landsat:** Gerrish, L. (2020). Automatically extracted rock outcrop dataset for
  Antarctica (Version 7.3) [Data set]. UK Polar Data Centre, Natural Environment Research Council, UK Research
  & Innovation. https://doi.org/10.5285/178EC50D-1FFB-42A4-A4A3-1145419DA2BB (CC BY 4.0). Method:
  Burton-Johnson, A., et al. (2016), The Cryosphere, 10, 1665-1677, doi:10.5194/tc-10-1665-2016.
- **K. Antarctic rock outcrop, medium resolution:** Skachkova, A., Gerrish, L., Fretwell, P., & Cooper, P. (2025).
  Medium resolution vector polygons of Antarctic rock outcrop - VERSION 7.11 (Version 7.11) [Data set]. NERC EDS
  UK Polar Data Centre. https://doi.org/10.5285/3f0c400f-04b9-4819-98cb-f6b53716aca5 (CC BY 4.0).
- **L. COMNAP:** Station names, status and distances: COMNAP Antarctic Facilities list, version 3.2.0
  (COMNAP 2019), copyright COMNAP, used here for educational and non-commercial purposes only.
- **M. Natural Earth (optional):** Made with Natural Earth. Free vector and raster map data @ naturalearthdata.com.
- **O. Diviner (lunar temperature and ice):** Paige et al., LRO DLRE LEVEL 5 PRP V2.0, NASA Planetary Data
  System, LRO-L-DLRE-5-PRP-V2.0, 2018. Model values, not measurements.
- **P. LROC (links to lunar mosaics):** NASA/GSFC/Arizona State University.
- **N. Wikipedia:** Site names and coordinates in the known-site list come in part from Wikipedia
  (https://en.wikipedia.org/wiki/Terrestrial_analogue_site and the pages linked in each entry), by Wikipedia
  contributors, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/). The list is shared under the
  same licence.
- **Q. OurAirports (distance to airfields):** Airfield data from OurAirports (https://ourairports.com/),
  public domain (The Unlicense), https://github.com/davidmegginson/ourairports-data . `airports.csv`
  downloaded on 15 November 2026 at 01:54 UTC (14 November in the Pacific time zone; server date of the
  file 14 November 2026, 02:54 GMT; sha256 5b3b48a4...574e8b). No credit is required; we give it anyway.

Credit lines for section 1b. Quoted text is word for word from our files or the provider's page.

- **R. MOLA MEGDR (Mars heights):** Smith, D. E., et al., Mars Global Surveyor Laser Altimeter Mission Experiment
  Gridded Data Record, MGS-M-MOLA-5-MEGDR-L3-V1.0, NASA Planetary Data System.
- **S. ETOPO 2022 (Earth heights for the Mars part):** NOAA National Centers for Environmental Information. 2022:
  ETOPO 2022 15 Arc-Second Global Relief Model. NOAA National Centers for Environmental Information. DOI:
  10.25921/fd45-gt74 . Accessed 14 November 2026. (NCEI asks for this one citation for every ETOPO 2022 resolution;
  we used the 60 arc-second surface file.)
- **T. NASA POWER (Mars climate, factors, power):** The data was obtained from National Aeronautics and Space
  Administration (NASA) Langley Research Center's Prediction Of Worldwide Energy Resources (POWER) project funded
  through the NASA Earth Science Division. The data was obtained from the POWER Project's Climatology API v2.10.1 on
  2026/11/15. (Daily temperature range, top-soil wetness and 10 m wind speed: MERRA-2. Surface albedo: CERES SYN1deg.)
  The date is in UTC. The same wording covers the climate, sunlight, UV, haze and 50 m wind parameters of row 25;
  their sources are MERRA-2 and CERES SYN1deg as the row says. `power_cells.json` and `mars_power.json` carry an
  older POWER wording ("... (LaRC) Prediction of Worldwide Energy Resource (POWER) Project funded through the NASA
  Earth Science/Applied Science Program"); the referencing page today gives the wording above.
- **U. Mars Climate Database:** Mars Climate Database (c) LMD/LATMOS/OU/IAA/ESA/CNES. Version 6.2, web interface,
  climatology average solar scenario, read 14 November 2026 (Pacific time). Scientific, non-commercial use; the origin
  is quoted as the MCD terms ask. (These are the words of the MCD credit page; the page prints the same names.)
- **V. Phoenix MET:** Dickinson, C.D., PHX METEOROLOGICAL DATA V1.0, NASA Planetary Data System, 2008. (The citation
  the PDS Atmospheres Node gives for the data set.)
- **W. Curiosity REMS:** "Curiosity's weather figures are from NASA's public weather feed, which says it is for
  outreach; they are not archive data." Feed: NASA/JPL-Caltech, REMS by Centro de Astrobiología (CAB).
- **X. Planet-side maps:** NASA Planetary Data System, Geosciences Node (Washington University in St. Louis), with the
  instrument teams named per factor (MGS TES thermal inertia, Putzig and Mellon 2007; Mars Odyssey GRS; Lunar
  Prospector neutron spectrometer, Feldman et al. 2001). TES albedo: Christensen, P., et al. (2001), MGS TES;
  originator Arizona State University; publisher USGS Astrogeology Science Center.
- **Y. GLiM (rock type):** Rock type: GLiM, Hartmann & Moosdorf (2012), PANGAEA, CC BY 3.0. Full citation: Hartmann,
  Jens; Moosdorf, Nils (2012): Global Lithological Map Database v1.0 (gridded to 0.5 deg spatial resolution)
  [dataset]. PANGAEA, https://doi.org/10.1594/PANGAEA.788537. Supplement to: Hartmann, J.; Moosdorf, N. (2012): The
  new global lithological map database GLiM: A representation of rock properties at the Earth surface. Geochemistry,
  Geophysics, Geosystems 13, Q12004, https://doi.org/10.1029/2012GC004370. Licence:
  https://creativecommons.org/licenses/by/3.0/
- **Z. Permafrost map:** Permafrost: Obu et al. (2019), ESA GlobPermafrost, PANGAEA, CC BY 3.0. Full citation: Obu,
  Jaroslav; Westermann, Sebastian; Kääb, Andreas; Bartsch, Annett (2018): Ground Temperature Map, 2000-2016, Northern
  Hemisphere Permafrost [dataset]. Alfred Wegener Institute, Helmholtz Centre for Polar and Marine Research,
  Bremerhaven, PANGAEA, https://doi.org/10.1594/PANGAEA.888600. Method: Obu, J. et al. (2019): Northern Hemisphere
  permafrost map based on TTOP modelling for 2000-2016 at 1 km2 scale. Earth-Science Reviews 193, 299-316,
  https://doi.org/10.1016/j.earscirev.2019.04.023. Licence: https://creativecommons.org/licenses/by/3.0/
- **AA. USGS earthquakes:** Credit: U.S. Geological Survey. Data: USGS ANSS Comprehensive Earthquake Catalog
  (ComCat), https://earthquake.usgs.gov/fdsnws/event/1/ , read 14 November 2026 (Pacific time).
- **AB. Smithsonian volcanoes:** Global Volcanism Program, 2026. [Database] Volcanoes of the World (v. 5.4.0; 7 Aug
  2026). Distributed by Smithsonian Institution, compiled by Venzke, E. https://doi.org/10.5479/si.GVP.VOTW5-2026.5.4
  (the "General Database Citation" on the GVP pages saved the same night). `hazards_people_cells.json` still says the
  version is "to be filled in"; it is the version above. The terms of use are in row 38.
- **AC. GeoNames:** GeoNames (geonames.org), CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/).
  `cities1000.zip` read 14 November 2026 (Pacific time).
- **AD. Global Power Plant Database:** Global Energy Observatory, Google, KTH Royal Institute of Technology in
  Stockholm, Enipedia, World Resources Institute. 2021. Global Power Plant Database version 1.3.0. Accessed through
  https://datasets.wri.org/datasets/global-power-plant-database on 14 November 2026. Licence CC BY 4.0. (This is WRI's
  wording on its dataset page. Our copy came from the GitHub repository wri/global-power-plant-database.
  `power_cells.json` and the page print an older wording that ends "Published on Resource Watch and Google Earth
  Engine".)
- **AE. Blue Marble (Earth globe):** NASA Earth Observatory. (Blue Marble: Next Generation, July 2004, with
  topography and bathymetry; fetched 15 November 2026.)
- **AF. CGI Moon Kit (Moon globe):** NASA's Scientific Visualization Studio. (CGI Moon Kit,
  https://svs.gsfc.nasa.gov/4720/ ; colour from the LROC Wide Angle Camera mosaic; fetched 15 November 2026.)
- **AG. Viking colour mosaic (Mars globe):** Mars Viking Colorized Global Mosaic (MDIM 2.1): USGS Astrogeology
  Science Center and NASA Ames; Viking Orbiter images, NASA. (Our wording; the product page asks for no credit line.
  Fetched 15 November 2026.)
- **AH. globe.gl and three.js (the globes):** globe.gl 2.46.2, https://github.com/vasturiano/globe.gl , MIT License.
  It bundles three.js, https://github.com/mrdoob/three.js , MIT License, Copyright © 2010-2026 three.js authors.
- **AI. Natural Earth boundaries (land status, optional):** Made with Natural Earth. Free vector and raster map data @ naturalearthdata.com.
- **AJ. Territory rules (land status):** Our own short statements from official pages of the Secretariat of the Antarctic
  Treaty, the Australian Antarctic Division, Crown-Indigenous Relations and Northern Affairs Canada, the Nunavut Research
  Institute, the Government of the Northwest Territories, Sysselmesteren på Svalbard, the U.S. Bureau of Land Management
  and Stjórnarráð Íslands, read on 15 November 2026. Not legal advice.
- **AK. Antarctic protected areas (land status):** Source: Antarctic Treaty Secretariat, ASMA and ASPA shapefile
  (2024 version), https://www.ats.aq/e/protected.html , CC BY 4.0. Converted to WGS 84 and cut to the areas of
  this project. (Our wording; the Secretariat asks only that the source is given. Fetched 15 November 2026.)
- **AL. Canadian maps (land status):** Contains information licensed under the Open Government Licence – Canada.
  (Canadian Protected and Conserved Areas Database, Environment and Climate Change Canada; Aboriginal Lands of
  Canada Legislative Boundaries, Natural Resources Canada; fetched 15 November 2026.)
- **AM. Iceland protected areas (land status):** Friðlýst svæði á Íslandi, Umhverfis- og orkustofnun. (Fetched
  15 November 2026; the provider asks that the source is cited.)
- **AN. Norway protected areas (land status):** Som referanse til kartet oppgis Miljødirektoratet. (Naturvernområder,
  NLOD 2.0; fetched 15 November 2026.)
- **AO. Sweden protected areas (land status):** Källa: Naturvårdsverket. (Skyddade områden, Naturvårdsregistret,
  CC0; fetched 15 November 2026.)
- **AP. PAD-US (land status):** U.S. Geological Survey (USGS) Gap Analysis Project (GAP), 2024, Protected Areas
  Database of the United States (PAD-US) 4.1: U.S. Geological Survey data release, https://doi.org/10.5066/P96WBCHS.
- **AQ. BLM Alaska (land status):** Bureau of Land Management, Alaska. BLM AK Administered Lands (SMA), data of
  31 August 2026. Our changes: we kept only the polygons that hold an area centre, the BLM server simplified the
  outlines by approximately 55 m, and we added the property agency_unit. (Fetched 15 November 2026.)
- **AR. Territory and entry rules, regional pass (land status):** Our own short statements from official pages of
  the Secretariat of the Antarctic Treaty, Crown-Indigenous Relations and Northern Affairs Canada, Avannaata
  Kommunia, the Expedition Office of the Government of Greenland, Stjórnarráð Íslands, Náttúruverndarstofnun,
  Lovdata, Sysselmesteren på Svalbard, Finnmarkseiendommen, Statskog, Sveriges riksdag, Naturvårdsverket, the
  President of Russia, the U.S. Bureau of Land Management, the National Park Service, the U.S. Fish and Wildlife
  Service, the Alaska Department of Natural Resources, Ahtna, Eklutna and Cook Inlet Region, read on
  15 November 2026. Not legal advice.
- **AS. The seven Mars sites added on 15 November 2026 (positions and short facts):** NASA Space Science Data
  Coordinated Archive (NSSDCA), spacecraft pages of Viking 1 Lander, Viking 2 Lander, Mars Pathfinder, Spirit,
  Opportunity and InSight, https://nssdc.gsfc.nasa.gov/ ; PDS Geosciences Node, Analyst's Notebook, MER mission
  overview; Golombek, M., et al. (2020), Geology of the InSight landing site on Mars, Nature Communications 11, 1014,
  doi:10.1038/s41467-020-14679-1 (CC BY 4.0); Golombek, M., et al. (2021), SpaceX Starship landing sites on Mars,
  52nd Lunar and Planetary Science Conference, abstract 2420 (LPI Contrib. No. 2548); USGS Gazetteer of Planetary
  Nomenclature, Phlegra Montes. (Fetched 15 November 2026.)
- **AT. The exploration zones of 2015 (positions and names):** Abstracts of the First Landing Site/Exploration Zone
  Workshop for Human Missions to the Surface of Mars, Lunar and Planetary Institute, Houston, 27-30 October 2015,
  https://www.hou.usra.edu/meetings/explorationzone2015/ ; (c) their authors, published by the Lunar and Planetary
  Institute. Only names, positions and one sentence of our own words are taken. Abstracts 1031 and 1056 from NASA's
  compiled abstract set. (Fetched 15 November 2026.)
- **AU. NASA's map of the proposed zones:** NASA Mars Program Office, Potential Exploration Zones for Human Missions
  to the Surface of Mars, version 10 (PDF) and version 12 (16 October 2015). (Fetched 15 November 2026.)
- **AV. The 2021 shortlist for human landings:** Golombek, M., et al. (2021), SpaceX Starship landing sites on Mars,
  52nd Lunar and Planetary Science Conference, abstract 2420 (LPI Contrib. No. 2548), Table 1; (c) its authors,
  published by the Lunar and Planetary Institute. (Fetched 15 November 2026.)
- **AW. NASA's map of the nine lunar regions of 2024 (positions of three lunar regions):** NASA. (Map of the
  nine candidate landing regions for Artemis III, NASA release 24-136 of 28 October 2024; its background is a
  mosaic of LRO Wide Angle Camera images. Fetched 15 November 2026.)
- **AX. USGS grid release (the boxes of the 13 regions of 2022):** McClernan, M.T., 2024, Lunar Grid Reference
  System (LGRS) Artemis III Candidate Landing Site Navigational Grids in Artemis Condensed Coordinate (ACC)
  Format: U.S. Geological Survey data release, https://doi.org/10.5066/P13FD9ZD. (The citation of the ScienceBase
  record; CC0. Read 15 November 2026.)
- Natural Earth roads and railroads: credit M (optional). OurAirports in the steady influences: credit Q.

One line for the page footer and the README licence section: "Code: Apache License 2.0. Our result files:
CC BY 4.0, except `data/reference/known_analogs.json` and `anorthosite_bodies.json` (CC BY-SA 4.0), the station fields taken from COMNAP, values from the Mars Climate Database, and volcano names, years and distances from the Smithsonian Global Volcanism Program (non-commercial use only, under each provider's terms). Source data keep their own
licences, listed in data/SOURCES.md. Not a NASA product; no endorsement by NASA, ESA, the European Union,
NOAA or any other provider is implied."

The line above is the one the page prints.

The page's source list (`site/data/meta.json`, written by `scripts/export_site.py`) today names 8 sources and
calls the Copernicus DEM "ESA, open licence". It lacks the credit lines above, the "produced using Copernicus
WorldDEM-90" notice, COMNAP, Open-Meteo, the lunar illumination maps and Wikipedia.

## 4. What to put in the submission form

**NASA Data field:**
- NASA LRO LOLA 5 m south-pole terrain models, NASA Goddard PGDA product 78 (Barker et al. 2021):
  https://pgda.gsfc.nasa.gov/products/78
- NASA LRO LOLA polar illumination and permanent-shadow maps, PGDA product 69, also on the NASA Planetary Data
  System (Mazarico et al. 2011): https://pgda.gsfc.nasa.gov/products/69
- NASA POWER: cloud amount from CERES SYN1deg, temperature and snow from MERRA-2 (NASA's reanalysis):
  https://power.larc.nasa.gov/
- NASA LRO Diviner Polar Resource Product (model-based temperature and ice stability at the lunar regions), NASA
  Planetary Data System: https://pds-geosciences.wustl.edu/lro/urn-nasa-pds-lro_diviner_derived1/data_derived_prp/
- NASA JPL Horizons, used to check our Sun positions and for the Sun's path at two lunar sites:
  https://ssd.jpl.nasa.gov/horizons/
- NASA's map of the nine candidate landing regions for Artemis III (28 October 2024), for the positions of three
  lunar regions (row 61): https://www.nasa.gov/wp-content/uploads/2024/10/artemis-iii-landing-region-candidates.jpg
- NASA Worldview, only if the page really links to it: https://worldview.earthdata.nasa.gov/ (it is in the
  challenge's own resource list; our pipeline does not read it).
- Added for the Mars part and the factors:
  - NASA MGS MOLA gridded heights of Mars (MEGDR), NASA Planetary Data System:
    https://pds-geosciences.wustl.edu/mgs/urn-nasa-pds-mgs_mola_topography_derived/meg032/
  - NASA POWER, further parameters for climate, sunlight, UV, haze, albedo, soil wetness and wind:
    https://power.larc.nasa.gov/
  - NASA Phoenix lander weather data (MET), NASA Planetary Data System Atmospheres Node:
    https://atmos.nmsu.edu/data_and_services/atmospheres_data/phoenix/met.html
  - NASA Curiosity rover weather (REMS), NASA's public Mars weather feed (outreach figures):
    https://mars.nasa.gov/rss/api/?feed=weather&category=msl&feedtype=json
  - NASA Planetary Data System maps: MGS TES thermal inertia, Mars Odyssey GRS water, Lunar Prospector hydrogen:
    https://pds-geosciences.wustl.edu/
  - NASA MGS TES albedo mosaic, published by USGS Astrogeology:
    https://planetarymaps.usgs.gov/mosaic/Mars_MGS_TES_Albedo_mosaic_global_7410m.tif
  - NASA Mars and Earth fact sheets: https://nssdc.gsfc.nasa.gov/planetary/factsheet/marsfact.html

**Space Agency Partner Data field** (ESA is a 2026 partner, and the challenge lists ESA's Copernicus Data Space
Ecosystem as a partner resource):
- ESA WorldCover 10 m 2021 v200: https://esa-worldcover.org/
- Copernicus DEM GLO-90, provided under Copernicus by the European Union and ESA:
  https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM

**Other open data (not NASA, not a partner agency; name them in the project text, not in the two fields):**
NOAA / U.S. National Ice Center IMS snow maps through NSIDC; NOAA GHCN-Daily; SCAR Antarctic Digital Database
rock outcrop (British Antarctic Survey); COMNAP facilities list; Copernicus Climate Change Service ERA5-Land
and CERRA through Open-Meteo; Natural Earth; OurAirports (public domain); Wikipedia and the literature behind
the two reference lists. Added for the new parts: NOAA ETOPO 2022; the Mars Climate Database (LMD, with ESA and CNES
among its owners); GLiM rock map and the Obu et al. permafrost map (both on PANGAEA); USGS earthquake catalogue;
Smithsonian Global Volcanism Program; GeoNames; WRI Global Power Plant Database. Added for the lunar regions:
the USGS grid release of the 13 regions of 2022 (row 62, CC0).
The permafrost map was made in ESA's GlobPermafrost project, and the MCD names ESA as an owner. Whether either
counts as partner data is for the team to decide; neither is published by ESA.
The UK Space Agency is a partner, but the British Antarctic Survey is a different body, so the rock layers are
not partner data.

## 5. Not checked

- The Planetary Data System's general data-use page (the Diviner bundle asks for a citation and names no
  licence), and the licence of the NASA pages the lunar cards quote numbers and names from.
- Whether the POWER cloud climatology covers the 2001 to 2025 its answers name: the temperature values of the
  same service fit 2001 to 2020.
- NASA's general media and data-use page for the PGDA products (the product pages ask for a citation and state
  no licence).
- The Copernicus Climate Change Service licence (for ERA5-Land and CERRA) and the licences of the individual
  papers behind the anorthosite list.
- Whether GHCN-Daily rows from non-U.S. weather services carry limits of their own (the NCEI record lists none).
- Where `ne_50m_land.geojson` was downloaded from (not in the code).
- The terms of the scouting downloads that the pipeline does not use.
- The BAS data catalogue pages (https://data.bas.ac.uk/...) answered "403" to our client; the licence of the
  two rock layers was read from the RAMADDA entry page and the DataCite records instead.

Not checked for section 1b:
- (The Smithsonian Global Volcanism Program's terms of use answered 403 to our scripts. They were read later that
  night in a browser; see row 38.)
- **Telling the Mars Climate Database authors.** Their terms ask to be kept informed of use. The team decides.
- The Planetary Data System's general data-use page, for the MOLA, Phoenix MET, TES, GRS and Lunar Prospector rows.
- Any terms on NASA's Mars weather feed beyond CAB's "outreach" note.
- The terms of the HiRISE, Analyst's Notebook, LPI and USGS Gazetteer pages, and of the papers in rows 29 and 33.
  Only coordinates, numbers and short phrases are taken from them.
- The three literature figures named in `site/data/mars.json` were not checked against a saved file.
- Whether WRI's "Creative Commons Attribution" on its dataset page means version 4.0 (the README says 4.0).
- Whether the GPPD copy in the repository's `output_database` folder is the same file as the v1.3.0 release.

Not checked for rows 42 to 45:
- NASA's media usage guidelines (https://www.nasa.gov/nasa-brand-center/images-and-media/). The page answered HTTP 429
  to our client twice. We did not try to get round it. Rows 42 and 43 rest on the providers' own pages instead.
- A licence for the Blue Marble image. Its pages ask for a credit and state no licence.

Not checked for rows 58 to 60:
- The terms of the Lunar and Planetary Institute for its meeting abstracts. Only names, positions and one sentence
  of our own words for each zone are taken from them.
- The individual workshop presentations (one PDF for each talk on NASA's page). They were not downloaded.
- NASA's media usage guidelines for the map of the proposed zones (see rows 42 to 45: the page answered HTTP 429).
- **Telling the Mars Climate Database authors.** 45 more requests were made for the second pass. The team decides.

Not checked for rows 61 and 62:
- NASA's media usage guidelines for the map of 2024 (see rows 42 to 45: the page answered HTTP 429).
- The publication date of the USGS release. The ScienceBase record gives 5 November 2024. `lunar_candidate_regions.json`,
  `moon_cards.json` and the page say 2 November 2024.
- The USGS script `LGRS_A3CLR_Grid_Generation.sh` was read as text only. We did not run it.

# Earth Twin Finder: results of the joined build

This page gives the results of the build of 15 November 2026: 16 lunar regions and 57 Mars sites. Each figure comes from the files in `data/derived` and `site/data`. The Moon part reads `grazing_cells.json` and `site/data/meta.json`. The Mars part reads `mars_sites.json` and `mars_cells.json`.

## The Moon: 16 lunar regions

The lunar regions are the candidate regions of the two NASA lists for Artemis III. The list of 28 October 2024 has 9 regions. Seven more regions are only on the list of 19 August 2022. NASA studied these regions as candidate regions.

For each region, the build finds places on Earth where the Sun stays low for spells of 2 hours or more. Low means between the horizon and the Sun ceiling of the region. Then the build removes the hours with snow on the ground and the hours that hills hide.

| Lunar region | NASA lists | Sun ceiling | 5 m terrain model (NASA PGDA) | Spells of 2 hours start at | Areas with 100 hours or more in the summer half, after snow and hills | Best ranked area: hours after snow and hills | Hours after hills |
|---|---|---|---|---|---|---|---|
| Connecting Ridge | 2022 only | 2.08° | Site01 | 64.80° N | 0 | 67.05 N, 158.85 W (Alaska): 76 h a year, 76 h in the summer half | full method |
| Connecting Ridge Extension | 2022 only | 2.51° | SL3 | 64.35° N | 3 | 68.05 N, 103.95 W (Arctic Canada): 101 h a year, 101 h in the summer half | full method |
| Peak Near Shackleton | 2022 only | 2.73° | Site07 | 64.10° N | 6 | 68.05 N, 103.95 W (Arctic Canada): 110 h a year, 110 h in the summer half | lower bound |
| de Gerlache Rim 1 | 2022 only | 2.86° | Site11 | 64.00° N | 9 | 68.05 N, 103.95 W (Arctic Canada): 116 h a year, 116 h in the summer half | lower bound |
| de Gerlache Rim 2 | 2024 and 2022 | 3.31° | SL2 | 63.50° N | 63 | 68.05 N, 103.95 W (Arctic Canada): 134 h a year, 134 h in the summer half | lower bound |
| Faustini Rim A | 2022 only | 3.65° | LM7 | 63.10° N | 140 | 68.05 N, 103.95 W (Arctic Canada): 147 h a year, 147 h in the summer half | lower bound |
| Slater Plain | 2024 only | 4.38° | none | 62.20° N | 489 | 68.95 N, 54.45 E (Kola and north-west Russia): 180 h a year, 180 h in the summer half | lower bound |
| Haworth | 2024 and 2022 | 4.78° | Haworth | 61.70° N | 1,336 | 80.35 N, 18.30 E (Svalbard): 200 h a year, 169 h in the summer half | lower bound |
| Malapert Massif | 2024 and 2022 | 5.55° | Site23 | 60.65° N | 3,145 | 80.35 N, 18.30 E (Svalbard): 239 h a year, 204 h in the summer half | lower bound |
| de Gerlache-Kocher Massif | 2022 only | 5.71° | Site42 | 60.45° N | 3,436 | 80.35 N, 18.30 E (Svalbard): 247 h a year, 212 h in the summer half | lower bound |
| Nobile Rim 1 | 2024 and 2022 | 6.10° | Site06 | 59.90° N | 4,014 | 70.85 N, 29.25 E (Norway, Sweden or Finland): 273 h a year, 269 h in the summer half | lower bound |
| Mons Mouton | 2024 and 2022 | 6.11° | Site20v2 | 59.90° N | 4,028 | 70.85 N, 29.25 E (Norway, Sweden or Finland): 274 h a year, 270 h in the summer half | lower bound |
| Mons Mouton Plateau | 2024 only | 7.21° | none | 58.25° N | 5,591 | 75.35 N, 82.25 E (Siberia and the Russian Far East): 385 h a year, 318 h in the summer half | lower bound |
| Amundsen Rim | 2022 only | 7.31° | DM1 | 58.10° N | 5,733 | 75.35 N, 82.25 E (Siberia and the Russian Far East): 391 h a year, 323 h in the summer half | lower bound |
| Nobile Rim 2 | 2024 and 2022 | 7.59° | DM2 | 57.65° N | 6,114 | 75.35 N, 82.25 E (Siberia and the Russian Far East): 409 h a year, 338 h in the summer half | lower bound |
| Peak near Cabeus B | 2024 only | 7.90° | none | 57.15° N | 6,539 | 75.35 N, 82.25 E (Siberia and the Russian Far East): 428 h a year, 355 h in the summer half | lower bound |

How to read the table:
- The Sun ceiling is the highest elevation of the centre of the Sun at the region: 90 degrees minus the latitude, plus 1.54 degrees.
- "Spells of 2 hours start at" is the lowest northern latitude with such a spell on one day of the year or more.
- The counts include only the northern areas with measured snow and a figure of hours after hills. The summer half is 1 April to 27 September.
- The files give three counts of measured northern areas. Each count has a different filter (see "Three counts of measured areas" below). Each count of areas with 100 hours or more is the same with each filter.
- A ranked area has a bare share of 0.25 or more. The best ranked area has the most hours a year. The table rounds the hours to the nearest hour.
- The NASA map of 2024 has the box "Mons Mouton" at the place of the 2022 box "Leibnitz Beta Plateau". No NASA text uses the word "renamed". Mons Mouton Plateau is a different region.

Three cautions:
1. **No terrain model for three regions.** NASA gives no 5 m terrain model of Slater Plain, Mons Mouton Plateau and Peak near Cabeus B. Their hours are complete, because the hours need only the Sun ceiling. Their slope likeness, roughness and landform are unknown, and the page shows "unknown", not 0. Their position comes from the box of the region on the NASA map of 2024.
2. **The hours after hills are a lower bound for 14 regions.** The project has the horizons of the areas on nine bins of Sun height only (lower edges 0 to 6.11 degrees). A new bin at a Sun ceiling takes the open share of the old bin below it. Thus a new run of the horizon step at each ceiling can increase these hours. That run needs approximately 90 minutes of computer time. The project did not do it. For Connecting Ridge and Connecting Ridge Extension, these hours use the full method of the first build. That method is also an approximation, because it uses bins of Sun height and 36 directions.
3. **A strip south of 59 degrees north is outside the search for four regions.** For Mons Mouton Plateau, Amundsen Rim, Nobile Rim 2 and Peak near Cabeus B, spells of 2 hours start south of 59 degrees north. The grid of areas starts at 59 degrees. Thus their counts do not include that strip of Earth.

Some terrain models overlap: Nobile Rim 1 and Mons Mouton, de Gerlache Rim 1 and de Gerlache Rim 2, Connecting Ridge and Connecting Ridge Extension. The NASA lists keep these regions apart, thus the table keeps each of them.

### Three counts of measured areas

Each count comes from `grazing_cells.json`. The submission text, the README and `docs/METHOD.md` use only the first count, with its sentence.

- **14,833 areas with measured snow and a terrain horizon.** These are northern areas of the grid (bare share 0.15 or more) with measured snow odds and a stored horizon. `scripts/validate.py` (`big_picture`) writes this count into `validation.json` (`big_picture_north.cells_with_a_horizon`).
- **14,830 areas with measured snow, a terrain horizon and a figure of hours after hills.** Three of the 14,833 areas have no figure of snow-free hours, thus no figure of hours after hills. `validation.json` gives 14,830 as `cells_counted` of each count after hills. `RESULTS-all-regions.md` gives this count.
- **14,834 areas with measured snow and a figure of hours after hills, with the areas of named sites.** These are the 14,830 areas and 4 areas of named sites that the bare-ground screen leaves out. The recount of this page (`docs/final-join-log.md`, 11:40) did not use the test of the grid.

A fourth count has no test of the horizon: 14,863 northern areas of the grid have measured snow (`validation.json`, `big_picture_north.measured_cells`). The counts over a flat horizon use them.

## Mars: 57 sites on three lists

The Mars part is a first pass on Earth squares of approximately 55 km. For each Mars site, it finds the Earth squares that come nearest on five factors: landscape slopes, dryness, cold, bare ground and noon Sun height. It ranks the 12,984 Earth squares with a bare share of 0.15 or more. A site can be on more than one list.

| List | Sites on the list | Sites of their own | Position from | Yearly mean air temperature (model) | Air pressure (model; at Gale, measured) | Nearest Earth region on all five factors (first place of each site) | Score of the first place |
|---|---|---|---|---|---|---|---|
| NASA landing sites | 9: Viking 1, Viking 2, Pathfinder, Spirit, Opportunity, Phoenix, Curiosity (Gale), InSight, Perseverance (Jezero) | 9 | the landing position on the NASA and PDS pages of each mission | -94.7 to -54.5 °C | 641 to 870 Pa | Qaidam Basin 6, Tibetan Plateau 2, Altiplano and Puna 1 | 0.592 to 0.752 |
| 2021 shortlist for human landings (52nd Lunar and Planetary Science Conference, abstract 2420) | 7: PM-1 and PM-7 (Phlegra Montes), AP-1, AP-8 and AP-9 (Arcadia Planitia), EM-15 and EM-16 (Erebus Montes) | 7 | Table 1 of the abstract | -75.4 to -71.7 °C | 697 to 823 Pa | Qaidam Basin 5, Tibetan Plateau 2 | 0.710 to 0.767 |
| Exploration zones proposed in 2015 (First Landing Site/Exploration Zone Workshop) | 45 | 39 | the position that each abstract gives; for zone 1051 (Hypanis), the centre of its circle on NASA's map | -82.5 to -53.4 °C | 480 to 896 Pa | Tibetan Plateau 33, Qaidam Basin 6, Altiplano and Puna 5, Atacama Desert 1 | 0.652 to 0.770 |

Six sites of the 2015 list are also sites of another kind. Four are NASA landing sites: Jezero, Gale, Spirit and Viking 1. Two are among the first five Mars sites of the project: Arcadia Planitia and Deuteronilus Mensae. Thus the page has 9 + 7 + 39 + 2 = 57 sites. Each score is from 0 to 1. The full table of each site is in `MARS-RESULTS.md`.

Zones of 2015 that are not sites of their own:
- **Left out: 1030**, south-western Meridiani Planum (Endeavour crater area). The abstract gives no position. The circle on NASA's map is approximately 5 to 6 degrees east of the craters that the abstract names. Thus the circle is not a usable stand-in.
- **Left out: 1049**, Holden crater. The text gives no position, and the zone is not on NASA's map. Its only position comes from a small figure, not from the text.
- **At the place of a site that the page has already.** The rule of the list file is: centres less than 50 km apart. These zones go with the present site:
  - 1008 Gusev crater: Spirit, 6 km;
  - 1011a Erebus Montes: Arcadia Planitia, 0 km;
  - 1019 Chryse Planitia: Viking 1, 19 km;
  - 1020 and 1022 Gale crater: Gale, 2 km and 26 km;
  - 1033 Deuteronilus Mensae: Deuteronilus Mensae, 0 km;
  - 1034 Jezero crater watershed: Jezero, 47 km;
  - 1040 Gale crater: Gale. The abstract gives a latitude only, thus no distance.
- Zone 1044, the debris apron of Deuteronilus Mensae, is 124 km from the Deuteronilus Mensae site. That is not the same place, thus it is a site of its own.

Cautions:
- This is a first pass. The squares are approximately 55 km wide, thus a score describes a large region.
- It is not a climate match. A score gives a place on the scale of each factor, not a share of likeness to Mars.
- The slopes come from heights every 1.85 km on both planets. At this scale the data does not show rocks, dunes or small craters.
- The yearly mean air temperature of each site is a model (Mars Climate Database v6.2). Some values at Gale and Phoenix are measurements of the missions there. The terms of the Mars Climate Database permit scientific use with credit. Commercial use needs permission.
- Each Mars site has a yearly mean 15.1 to 56.4 °C colder than the coldest ranked Earth square. The air pressure at the sites is 0.47 to 0.88 % of the pressure at sea level on Earth. No place on Earth matches these two factors.
- The positions of the 2015 zones are as each abstract gives them. Some zones overlap: their centres are less than 200 km apart. Each zone is a proposal of a workshop abstract.
- The Mars part does not measure soil chemistry, minerals, ground ice, lava tubes, impact features or life.

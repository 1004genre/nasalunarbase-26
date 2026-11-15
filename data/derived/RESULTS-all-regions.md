# Results: 16 lunar regions

This table gives the results of the run of 15 November 2026 with 16 lunar regions. They are all the candidate regions of the two NASA lists: the nine regions of the list of 28 October 2024 and the seven regions that are only on the list of 19 August 2022. NASA studied these regions as candidates for Artemis III. NASA did not select a landing site in them. The figures come from the files in this folder (`moon_targets.json`, `grazing_cells.json`, `latitude_profile.json`, `cells_scored.json`) and from `site/data/meta.json`.

| Lunar region | NASA lists | 5 m terrain model | Sun ceiling | Two-hour spells start at (north) | Hours after hills | Arctic areas with 100 hours or more in the summer half, after snow and hills | Best ranked Arctic area: hours a year after snow and hills |
|---|---|---|---|---|---|---|---|
| Connecting Ridge | 2022 list only | yes | 2.08° | 64.80° | full method | 0 | 67.05 N, 158.85 W (Alaska): 76 hours a year, 76 in the summer half |
| Connecting Ridge Extension | 2022 list only | yes | 2.51° | 64.35° | full method | 3 | 68.05 N, 103.95 W (Arctic Canada): 101 hours a year, 101 in the summer half |
| Peak Near Shackleton | 2022 list only | yes | 2.73° | 64.10° | lower bound | 6 | 68.05 N, 103.95 W (Arctic Canada): 110 hours a year, 110 in the summer half |
| de Gerlache Rim 1 | 2022 list only | yes | 2.86° | 64.00° | lower bound | 9 | 68.05 N, 103.95 W (Arctic Canada): 116 hours a year, 116 in the summer half |
| de Gerlache Rim 2 | 2024 and 2022 lists | yes | 3.31° | 63.50° | lower bound | 63 | 68.05 N, 103.95 W (Arctic Canada): 134 hours a year, 134 in the summer half |
| Faustini Rim A | 2022 list only | yes | 3.65° | 63.10° | lower bound | 140 | 68.05 N, 103.95 W (Arctic Canada): 147 hours a year, 147 in the summer half |
| Slater Plain | 2024 list only | no | 4.38° | 62.20° | lower bound | 489 | 68.95 N, 54.45 E (Kola and north-west Russia): 180 hours a year, 180 in the summer half |
| Haworth | 2024 and 2022 lists | yes | 4.78° | 61.70° | lower bound | 1,336 | 80.35 N, 18.30 E (Svalbard): 200 hours a year, 169 in the summer half |
| Malapert Massif | 2024 and 2022 lists | yes | 5.55° | 60.65° | lower bound | 3,145 | 80.35 N, 18.30 E (Svalbard): 239 hours a year, 204 in the summer half |
| de Gerlache-Kocher Massif | 2022 list only | yes | 5.71° | 60.45° | lower bound | 3,436 | 80.35 N, 18.30 E (Svalbard): 247 hours a year, 212 in the summer half |
| Nobile Rim 1 | 2024 and 2022 lists | yes | 6.10° | 59.90° | lower bound | 4,014 | 70.85 N, 29.25 E (Norway, Sweden or Finland): 273 hours a year, 269 in the summer half |
| Mons Mouton | 2024 and 2022 lists | yes | 6.11° | 59.90° | lower bound | 4,028 | 70.85 N, 29.25 E (Norway, Sweden or Finland): 274 hours a year, 270 in the summer half |
| Mons Mouton Plateau | 2024 list only | no | 7.21° | 58.25° | lower bound | 5,591 | 75.35 N, 82.25 E (Siberia and the Russian Far East): 385 hours a year, 318 in the summer half |
| Amundsen Rim | 2022 list only | yes | 7.31° | 58.10° | lower bound | 5,733 | 75.35 N, 82.25 E (Siberia and the Russian Far East): 391 hours a year, 323 in the summer half |
| Nobile Rim 2 | 2024 and 2022 lists | yes | 7.59° | 57.65° | lower bound | 6,114 | 75.35 N, 82.25 E (Siberia and the Russian Far East): 409 hours a year, 338 in the summer half |
| Peak near Cabeus B | 2024 list only | no | 7.90° | 57.15° | lower bound | 6,539 | 75.35 N, 82.25 E (Siberia and the Russian Far East): 428 hours a year, 355 in the summer half |

How to read the table:

- The Sun ceiling is the highest that the centre of the Sun can climb at the lunar region: 90 degrees minus the latitude, plus 1.54 degrees.
- "Two-hour spells start at" is the lowest northern latitude where the Sun stays between the horizon and the ceiling for 2 hours or more without a break, on at least one day of the year. The search grid starts at 59 degrees. If the value is less than 59 degrees, a strip of the Earth that has such spells is outside the search.
- "Hours after hills" says if the hours after hills of the region use the full method of the first build ("full method") or are a lower bound (see the cautions). The page data gives the same in `meta.targets[].hills_exact` (true: the full method).
- The areas count only measured Arctic areas with a terrain figure (14,830 areas). The summer half is 1 April to 27 September.
- The best area is the ranked Arctic area with the most hours a year in two-hour spells, on snow-free ground and after the hills.

Cautions:

- Three lunar regions have no NASA 5 m terrain model: Slater Plain, Mons Mouton Plateau and Peak near Cabeus B. Their light hours are complete, because the hours need only the Sun ceiling. Their slope likeness, roughness and landform are unknown, and the page shows "unknown", not 0. Their position comes from the box of the region on the NASA map of 2024 (approximately 1 km accurate). The box of Mons Mouton Plateau is approximately 77 km by 58 km, thus its Sun ceiling changes by approximately 2.9 degrees across the region.
- The hills use the horizons that the project stored at the old nine bins of Sun height (lower edges 0, 0.5, 1.0, 1.5, 2.08, 3.0, 4.0, 5.55 and 6.11 degrees). The run has 21 bins, with an edge at each of the 16 Sun ceilings. Each new bin takes the open share of the old bin that holds its lower edge. Thus the four regions of the first build (Connecting Ridge, Malapert Massif, Mons Mouton and Nobile Rim 2) keep the hours after hills of the main project.
- For Connecting Ridge and Connecting Ridge Extension, these hours use the full method of the first build: each bin of their band starts at an old edge. The full method is also an approximation, because it uses bins of Sun height and 36 directions. For the other 14 regions, the hours after hills are a lower bound. This includes Malapert Massif, Mons Mouton and Nobile Rim 2: a horizon run at the new edges can increase their hours above the figures of the main project.
- A run of `scripts/build_horizon_cells.py` at all 21 bins needs approximately 90 minutes on this computer (timed on 300 areas with 10 processes). It was not run. On those 300 areas, the new shares at the old edges are the same as the stored shares.
- For Mons Mouton Plateau, Amundsen Rim, Nobile Rim 2 and Peak near Cabeus B, two-hour spells start south of 59 degrees. The search starts at 59 degrees, thus the counts of these regions do not include a strip of Earth that also has such spells.
- Some terrain models overlap: Nobile Rim 1 and Mons Mouton by approximately 12 km by 15 km, de Gerlache Rim 1 and de Gerlache Rim 2 by approximately 6.5 km by 10 km, Connecting Ridge and Connecting Ridge Extension by approximately 0.3 km by 12 km. The regions are separate on the NASA lists, thus the table keeps each of them.
- Nobile Rim 1 (6.10 degrees) and Mons Mouton (6.11 degrees) have almost the same ceiling.
- Seven regions are only on the list of 2022. A NASA abstract (NTRS 20250011660) says that the cut to nine regions does not make the other regions unsuitable for future exploration.
- The 2022 region "Leibnitz Beta Plateau" has the name "Mons Mouton" on the list of 2024: the NASA map of 2024 has the box "Mons Mouton" at the place of the 2022 box "Leibnitz Beta Plateau" (USGS grid release of 2 November 2024). No NASA text uses the word "renamed". "Mons Mouton Plateau" is a different, new region to the north.

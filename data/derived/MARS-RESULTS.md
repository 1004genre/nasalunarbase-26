# LuniMartian Atlas: the Mars part, a first pass

Generated Sunday 15 November 2026, 09:49 PST by `scripts/build_mars_cells.py`. It reads `mars_sites_base.json`, `mars_terrain.json` and `mars_climate.json` in `data/derived/`. Every number below was read from those files or computed from them in this run. Each table names its file and field. Unknown values are written `n/a`, never 0.

## What this is, and what it is not

- This is a first pass, and it is coarser than the Moon part.
- Earth is cut into squares of half a degree, about 55 km across. The Moon part used cells of about 11 km.
- The slope baseline is the same on both planets: heights every 1.85 km, slopes across about 3.7 km, which is two pixels. Rocks, dunes, small craters, gullies and anything a rover would feel are not seen.
- For each Mars site it asks where on Earth, and in which months, five factors come closest. The factors are landscape slopes, dryness, cold, bare ground and noon Sun height.
- Each factor is kept apart, and each shortfall is given in plain numbers.
- Some things have no match anywhere on Earth. Section 6 lists them with numbers.
- It does not measure soil chemistry, minerals, ground ice, lava tubes, impact features or life. Many known analog sites were chosen for exactly those things.
- Earth climate is a model (NASA POWER, MERRA-2) for a grid box, not a measurement at the square.
- It is not a climate match.
- The coldest ranked square, `m_-80.25_155.75` (Transantarctic Mountains), has a yearly mean of -38.3 °C. Each Mars site is 15.1 to 56.4 °C colder.
- Mars air pressure at the sites is 0.47 to 0.88 % of Earth's at sea level. That is 0.93 to 1.74 % of the lowest yearly mean of any Earth land square.

## 1. How the scores work

Every score lies between 0 and 1. The formulas are also stored in `mars_cells.json` → `meta.formulas`.
It is not a climate match. A score is a place on each factor's own scale between two set end points, not a share of likeness to Mars.
For example, cold 0.5 means a yearly mean half-way between +30 °C and the Mars site's.
+30 °C is about the warmest yearly mean on Earth, so the cold scale spans Earth's whole range.
The warmest ranked square, `m_13.25_40.75` (Danakil Depression), has a yearly mean of 33.6 °C.
The first pass put the zero point at +15 °C. That gave the hyperarid Atacama, the Mojave, Dhofar and the Pilbara a cold score of 0.

| Score | In words | Field |
|---|---|---|
| terrain | min(1, overlap of the square's and the site's slope histograms / the site's self-overlap) | `cells.<id>.sites.<site>.terrain` |
| dry | 1 at 25 mm of rain and snow a year or less, 0 at 500 mm or more, a straight line on a log scale between | `cells.<id>.sites.<site>.dry` |
| cold | 1 where the square's yearly mean air temperature equals the site's (or is colder), 0 at +30 C or warmer, a straight line between | `cells.<id>.sites.<site>.cold` |
| bare | the bare share of the square's land | `cells.<id>.sites.<site>.bare` |
| sun | the share of the site's yearly range of noon Sun height that the square's own yearly range covers (absolute latitude on both planets; tilt 25.19 degrees on Mars, 23.44 on Earth) | `cells.<id>.sites.<site>.sun` |
| landscape | geometric mean of terrain and bare | `cells.<id>.sites.<site>.landscape` |
| environment | geometric mean of dry, cold and bare | `cells.<id>.sites.<site>.environment` |
| full | geometric mean of terrain, dry, cold, bare and sun | `cells.<id>.sites.<site>.full` |
| months | a score per month, below | `best_places.<site>.<goal>[].month_scores` |
| best months | the three months with the highest month score above 0, best first; ties keep calendar order | `cells.<id>.sites.<site>.best_months` |

Each month gets a score of its own: the geometric mean of three parts. The first is cold, from that month's mean air temperature against the site's yearly mean. It uses the same scale, 0 at +30 °C or warmer. The second is dry, from that month's precipitation times 12. The third is 1 if the noon Sun on the 15th lies inside the site's yearly range, and 0 if not.

A goal is unknown when any of its factors is unknown. A factor of 0 makes its goals 0.
Only squares with at least 15 % bare ground are ranked, as in the Moon part.

## 2. The Mars sites

From `mars_sites.json` → `sites[]` (fields `sun`, `climate`, `landscape`). Latitudes are planetocentric; longitudes run east from 0 to 360.

| Site | Kind | Lat | Lon E | Noon Sun, lowest to highest | Yearly mean air temp. | Pressure | Median slope / 90th pct. | Relief | Self-overlap |
|---|---|---|---|---|---|---|---|---|---|
| Jezero | visited by a NASA mission | 18.442 | 77.452 | 46.37° to 90.00° | -56.6 °C (model) | 721 Pa (model) | 1.76° / 5.06° | 1,386 m | 0.820 |
| Gale | visited by a NASA mission | -4.5895 | 137.4417 | 60.22° to 90.00° | -57.8 °C (model) | 818 Pa (measured) | 3.95° / 12.30° | 3,416 m | 0.771 |
| Phoenix | visited by a NASA mission | 68.22 | 234.25 | -3.41° to 46.97° | -94.7 °C (model) | 834 Pa (model) | 0.51° / 1.72° | 274 m | 0.779 |
| Arcadia Planitia | studied for a human landing | 39.0 | 192.1 | 25.81° to 76.19° | -75.4 °C (model) | 825 Pa (model) | 0.19° / 1.14° | 205 m | 0.831 |
| Deuteronilus Mensae | studied for a human landing | 39.11 | 23.199 | 25.70° to 76.08° | -71.5 °C (model) | 791 Pa (model) | 1.13° / 8.21° | 1,827 m | 0.693 |
| Viking 1 | visited by a NASA mission | 22.27 | 312.05 | 42.54° to 90.00° | -59.0 °C (model) | 793 Pa (model) | 0.22° / 0.68° | 142 m | 0.866 |
| Viking 2 | visited by a NASA mission | 47.6673 | 134.2809 | 17.14° to 67.52° | -80.0 °C (model) | 870 Pa (model) | 0.30° / 0.67° | 152 m | 0.926 |
| Pathfinder | visited by a NASA mission | 19.33 | 326.45 | 45.48° to 90.00° | -55.8 °C (model) | 799 Pa (model) | 0.22° / 0.95° | 219 m | 0.746 |
| Spirit | visited by a NASA mission | -14.5692 | 175.4729 | 50.24° to 90.00° | -63.6 °C (model) | 680 Pa (model) | 0.33° / 3.31° | 549 m | 0.727 |
| Opportunity | visited by a NASA mission | -1.9462 | 354.4734 | 62.86° to 90.00° | -54.5 °C (model) | 641 Pa (model) | 0.29° / 0.98° | 228 m | 0.773 |
| InSight | visited by a NASA mission | 4.502 | 135.623 | 60.31° to 90.00° | -58.2 °C (model) | 720 Pa (model) | 0.19° / 0.82° | 137 m | 0.796 |
| Phlegra Montes | studied for a human landing | 35.23 | 163.95 | 29.58° to 79.96° | -71.7 °C (model) | 764 Pa (model) | 1.88° / 9.89° | 1,926 m | 0.645 |
| AP-1 (Arcadia Planitia) | studied for a human landing | 39.8 | 202.1 | 25.01° to 75.39° | -74.5 °C (model) | 821 Pa (model) | 0.17° / 0.42° | 56 m | 0.887 |
| AP-9 (Arcadia Planitia) | studied for a human landing | 40.02 | 203.35 | 24.79° to 75.17° | -75.4 °C (model) | 820 Pa (model) | 0.17° / 0.47° | 53 m | 0.826 |
| EM-16 (Erebus Montes) | studied for a human landing | 39.89 | 192.03 | 24.92° to 75.30° | -75.4 °C (model) | 818 Pa (model) | 0.23° / 2.05° | 271 m | 0.805 |
| AP-8 (Arcadia Planitia) | studied for a human landing | 40.75 | 201.3 | 24.06° to 74.44° | -74.7 °C (model) | 823 Pa (model) | 0.14° / 0.41° | 70 m | 0.890 |
| EM-15 (Erebus Montes) | studied for a human landing | 39.75 | 195.62 | 25.06° to 75.44° | -74.5 °C (model) | 817 Pa (model) | 0.20° / 1.52° | 148 m | 0.743 |
| PM-7 (Phlegra Montes) | studied for a human landing | 36.43 | 162.16 | 28.38° to 78.76° | -72.9 °C (model) | 697 Pa (model) | 1.00° / 5.24° | 1,128 m | 0.745 |
| Phlegra Dorsa, Arcadia Planitia | proposed as an exploration zone in 2015 | 39.0 | 172.0 | 25.81° to 76.19° | -72.1 °C (model) | 823 Pa (model) | 0.23° / 1.18° | 171 m | 0.753 |
| Southern Nectaris Fossae | proposed as an exploration zone in 2015 | -28.88 | 300.29 | 35.93° to 86.31° | -62.4 °C (model) | 480 Pa (model) | 1.05° / 3.20° | 1,099 m | 0.773 |
| Valles Marineris mouth (southern Acidalia Planitia, as named in the abstract) | proposed as an exploration zone in 2015 | 20.0 | 320.0 | 44.81° to 90.00° | -56.7 °C (model) | 798 Pa (model) | 0.34° / 1.53° | 260 m | 0.781 |
| East Melas Chasma | proposed as an exploration zone in 2015 | -11.7 | 290.0 | 53.11° to 90.00° | -54.2 °C (model) | 868 Pa (model) | 2.72° / 8.76° | 3,080 m | 0.769 |
| Mawrth Vallis | proposed as an exploration zone in 2015 | 24.3 | 340.8 | 40.51° to 90.00° | -59.8 °C (model) | 703 Pa (model) | 1.69° / 5.36° | 1,719 m | 0.773 |
| Nili Fossae | proposed as an exploration zone in 2015 | 22.05 | 76.95 | 42.76° to 90.00° | -57.6 °C (model) | 604 Pa (model) | 2.54° / 7.74° | 2,038 m | 0.790 |
| Acheron Fossae | proposed as an exploration zone in 2015 | 39.8 | 220.6 | 25.01° to 75.39° | -78.5 °C (model) | 759 Pa (model) | 0.77° / 4.99° | 2,024 m | 0.551 |
| Hebrus Valles | proposed as an exploration zone in 2015 | 20.0833 | 126.6333 | 44.73° to 90.00° | -60.4 °C (model) | 789 Pa (model) | 0.20° / 1.43° | 163 m | 0.799 |
| Newton crater | proposed as an exploration zone in 2015 | -40.6 | 200.0 | 24.21° to 74.59° | -73.2 °C (model) | 643 Pa (model) | 1.30° / 3.80° | 1,614 m | 0.735 |
| Zephyria Planum hills ('Sea Urchins') | proposed as an exploration zone in 2015 | -1.3717 | 157.1417 | 63.44° to 90.00° | -67.4 °C (model) | 728 Pa (model) | 0.25° / 0.99° | 214 m | 0.808 |
| Cerberus (west of Zunil crater) | proposed as an exploration zone in 2015 | 10.0 | 162.0 | 54.81° to 90.00° | -62.3 °C (model) | 728 Pa (model) | 0.67° / 5.38° | 640 m | 0.646 |
| Amazonis Planitia mid-latitude ice | proposed as an exploration zone in 2015 | 46.16 | 188.8 | 18.65° to 69.03° | -78.4 °C (model) | 833 Pa (model) | 0.17° / 0.37° | 38 m | 0.922 |
| Western Noachis Terra chloride deposits | proposed as an exploration zone in 2015 | -37.2 | 350.5 | 27.61° to 77.99° | -72.8 °C (model) | 512 Pa (model) | 0.67° / 2.53° | 388 m | 0.808 |
| South of Valles Marineris (equatorial site) | proposed as an exploration zone in 2015 | -18.83 | 310.79 | 45.98° to 90.00° | -56.8 °C (model) | 513 Pa (model) | 0.87° / 2.79° | 713 m | 0.759 |
| McLaughlin crater | proposed as an exploration zone in 2015 | 21.9 | 337.6 | 42.91° to 90.00° | -57.7 °C (model) | 896 Pa (model) | 2.68° / 9.38° | 2,589 m | 0.732 |
| South of Firsoff crater, Arabia Terra | proposed as an exploration zone in 2015 | 0.3911 | 351.6375 | 64.42° to 90.00° | -53.9 °C (model) | 671 Pa (model) | 0.59° / 2.53° | 674 m | 0.757 |
| Ismenius Cavus | proposed as an exploration zone in 2015 | 33.8167 | 17.1667 | 30.99° to 81.37° | -73.3 °C (model) | 780 Pa (model) | 1.34° / 8.58° | 1,727 m | 0.784 |
| Hale crater | proposed as an exploration zone in 2015 | -35.3 | 323.14 | 29.51° to 79.89° | -71.6 °C (model) | 682 Pa (model) | 3.07° / 10.00° | 4,264 m | 0.749 |
| Copernicus crater | proposed as an exploration zone in 2015 | -49.2 | 190.8 | 15.61° to 65.99° | -81.4 °C (model) | 566 Pa (model) | 0.49° / 1.30° | 427 m | 0.836 |
| Huygens crater | proposed as an exploration zone in 2015 | -13.5 | 55.5 | 51.31° to 90.00° | -59.2 °C (model) | 511 Pa (model) | 0.53° / 1.70° | 590 m | 0.855 |
| Mesopotamia (east rim of Hellas) | proposed as an exploration zone in 2015 | -35.352 | 94.02 | 29.46° to 79.84° | -68.2 °C (model) | 746 Pa (model) | 0.63° / 3.04° | 1,557 m | 0.805 |
| Western Coprates Chasma | proposed as an exploration zone in 2015 | -11.684 | 293.367 | 53.13° to 90.00° | -54.7 °C (model) | 793 Pa (model) | 5.34° / 22.56° | 9,833 m | 0.681 |
| Hellas Rim | proposed as an exploration zone in 2015 | -39.05 | 101.91 | 25.76° to 76.14° | -73.3 °C (model) | 584 Pa (model) | 1.11° / 6.61° | 1,007 m | 0.685 |
| Eastern rim of Hellas impact basin | proposed as an exploration zone in 2015 | -40.0 | 104.0 | 24.81° to 75.19° | -74.7 °C (model) | 607 Pa (model) | 0.87° / 9.18° | 2,276 m | 0.662 |
| Columbus crater | proposed as an exploration zone in 2015 | -29.0 | 194.0 | 35.81° to 86.19° | -65.7 °C (model) | 526 Pa (model) | 1.83° / 8.55° | 2,175 m | 0.756 |
| South-west Sinus Meridiani | proposed as an exploration zone in 2015 | -2.2526 | 353.5665 | 62.56° to 90.00° | -54.6 °C (model) | 646 Pa (model) | 0.38° / 1.54° | 417 m | 0.697 |
| Apollinaris Sulci | proposed as an exploration zone in 2015 | -12.6667 | 176.6667 | 52.14° to 90.00° | -67.1 °C (model) | 691 Pa (model) | 1.50° / 6.39° | 1,416 m | 0.733 |
| Deuteronilus Mensae (debris apron zone) | proposed as an exploration zone in 2015 | 41.0 | 22.0 | 23.81° to 74.19° | -72.7 °C (model) | 708 Pa (model) | 0.89° / 6.19° | 1,655 m | 0.692 |
| Ausonia Cavus | proposed as an exploration zone in 2015 | -32.0 | 96.5 | 32.81° to 83.19° | -67.2 °C (model) | 754 Pa (model) | 0.75° / 3.38° | 1,044 m | 0.729 |
| Kasei Valles | proposed as an exploration zone in 2015 | 24.81 | 287.37 | 40.00° to 90.00° | -75.4 °C (model) | 664 Pa (model) | 1.55° / 10.48° | 2,180 m | 0.709 |
| Gusev crater - Apollinaris Sulci | proposed as an exploration zone in 2015 | -13.0 | 175.0 | 51.81° to 90.00° | -66.7 °C (model) | 646 Pa (model) | 1.32° / 7.01° | 1,244 m | 0.680 |
| Aram Chaos | proposed as an exploration zone in 2015 | 2.4167 | 339.9667 | 62.39° to 90.00° | -53.4 °C (model) | 705 Pa (model) | 2.47° / 7.34° | 1,184 m | 0.795 |
| Noctis Landing | proposed as an exploration zone in 2015 | -6.494 | 267.5466 | 58.32° to 90.00° | -64.9 °C (model) | 581 Pa (model) | 4.24° / 19.57° | 4,364 m | 0.718 |
| Hypanis (Hypanis and Sabrina deltas) | proposed as an exploration zone in 2015 | 11.98 | 313.94 | 52.83° to 90.00° | -56.6 °C (model) | 718 Pa (model) | 0.77° / 2.46° | 670 m | 0.822 |
| Hadriacus Palus and Cavi | proposed as an exploration zone in 2015 | -26.84 | 77.47 | 37.97° to 88.35° | -64.9 °C (model) | 747 Pa (model) | 1.55° / 5.99° | 1,970 m | 0.746 |
| Protonilus Mensae | proposed as an exploration zone in 2015 | 42.187 | 48.062 | 22.62° to 73.00° | -73.7 °C (model) | 583 Pa (model) | 3.42° / 13.12° | 2,392 m | 0.805 |
| Eastern outlet of Valles Marineris | proposed as an exploration zone in 2015 | -4.1 | 324.8 | 60.71° to 90.00° | -54.2 °C (model) | 805 Pa (model) | 2.25° / 13.13° | 3,515 m | 0.699 |
| Tempe Terra | proposed as an exploration zone in 2015 | 42.266 | 270.82 | 22.54° to 72.92° | -82.5 °C (model) | 538 Pa (model) | 1.16° / 4.71° | 787 m | 0.779 |
| Southern edge of Meridiani Planum (Endeavour crater area) | proposed as an exploration zone in 2015 | -3.174 | 355.4827 | 61.64° to 90.00° | -54.7 °C (model) | 647 Pa (model) | 0.62° / 2.66° | 428 m | 0.737 |


**The sites by list**

From `mars_sites.json` → `sites[].lists`. A site can be on more than one list.
A study or a proposal is not a NASA decision. NASA has not made a decision on a human landing site on Mars.

| List | What it is | Sites | Names |
|---|---|---|---|
| NASA landing site | A NASA lander or rover landed and worked there. | 9 | Jezero; Gale; Phoenix; Viking 1; Viking 2; Pathfinder; Spirit; Opportunity; InSight |
| 2021 shortlist for human landings | Table 1 of Golombek et al. 2021 (LPSC abstract 2420), a study of Starship landing sites. | 7 | Phlegra Montes; AP-1 (Arcadia Planitia); AP-9 (Arcadia Planitia); EM-16 (Erebus Montes); AP-8 (Arcadia Planitia); EM-15 (Erebus Montes); PM-7 (Phlegra Montes) |
| 2015 exploration zone | A zone proposed in an abstract of NASA's 2015 workshop on human landing sites and exploration zones. | 45 | Jezero (1034); Gale (1020, 1022, 1040); Arcadia Planitia (1011); Deuteronilus Mensae (1033); Viking 1 (1019); Spirit (1008); Phlegra Dorsa, Arcadia Planitia (1002); Southern Nectaris Fossae (1005); Valles Marineris mouth (southern Acidalia Planitia, as named in the abstract) (1006); East Melas Chasma (1007); Mawrth Vallis (1009); Nili Fossae (1010); Acheron Fossae (1011); Hebrus Valles (1012); Newton crater (1015); Zephyria Planum hills ('Sea Urchins') (1016); Cerberus (west of Zunil crater) (1017); Amazonis Planitia mid-latitude ice (1018); Western Noachis Terra chloride deposits (1021); South of Valles Marineris (equatorial site) (1023); McLaughlin crater (1025); South of Firsoff crater, Arabia Terra (1026); Ismenius Cavus (1027); Hale crater (1028); Copernicus crater (1029); Huygens crater (1032); Mesopotamia (east rim of Hellas) (1035); Western Coprates Chasma (1036); Hellas Rim (1037); Eastern rim of Hellas impact basin (1038); Columbus crater (1041); South-west Sinus Meridiani (1042); Apollinaris Sulci (1043); Deuteronilus Mensae (debris apron zone) (1044); Ausonia Cavus (1045); Kasei Valles (1045); Gusev crater - Apollinaris Sulci (1046); Aram Chaos (1048); Noctis Landing (1050); Hypanis (Hypanis and Sabrina deltas) (1051); Hadriacus Palus and Cavi (1052); Protonilus Mensae (1053); Eastern outlet of Valles Marineris (1054); Tempe Terra (1056); Southern edge of Meridiani Planum (Endeavour crater area) (1057) |

The numbers in brackets are the numbers of the 2015 abstracts.
Kinds of site: visited by a NASA mission, 9; studied for a human landing, 9; proposed as an exploration zone in 2015, 39.
All 57 yearly mean temperatures are model values (Mars Climate Database, LMD with ESA and CNES). So the cold score compares like with like across the sites.
Relief is the 95th minus the 5th percentile height in the 2 x 2 degree box around the site.
The measured figures at Gale (warm-season daily maximum, cold-season daily minimum, pressure) are Curiosity's. Curiosity's weather figures are from NASA's public weather feed, which says it is for outreach; they are not archive data.
A lowest noon Sun below 0° means the Sun stays below the horizon all day at midwinter (Phoenix).

## 3. What was searched

| What | Count | Source |
|---|---|---|
| Squares with slopes | 81,776 | `mars_terrain.json` → `cells` |
| Squares with climate | 81,736 | `mars_climate.json` → `cells` |
| In both files | 81,503 | joined by `id` |
| In the slope file only / the climate file only | 273 / 233 | joined by `id` |
| Squares with bare ground unknown | 89 | `mars_climate.json` → `cells.<id>.bare` null |
| Ranked squares (bare ≥ 0.15) | 12,984 | `mars_cells.json` → `cells` |
| of them without slopes (landscape and full unknown) | 91 | `mars_cells.json` → `cells.<id>.sites.<site>.terrain` null |
| of them with a yearly mean of +30 °C or more (cold, environment and full are 0) | 52 | `mars_cells.json` → `cells.<id>.t2m_year_c` |
| of them with a yearly mean of +15 °C or more (cold was 0 there in the first pass) | 6,724 | `mars_cells.json` → `cells.<id>.t2m_year_c` |
| of them with 25 mm of precipitation a year or less (dry is 1) | 1,581 | `mars_cells.json` → `cells.<id>.precip_mm_year` |
| Ranked squares in a box of the kind 'great desert' | 7,275 | `mars_cells.json` → `cells.<id>.region_group` |
| Ranked squares in a box of the kind 'high plateau' | 1,051 | `mars_cells.json` → `cells.<id>.region_group` |
| Ranked squares in a box of the kind 'polar desert' | 1,815 | `mars_cells.json` → `cells.<id>.region_group` |
| Ranked squares in a box of the kind 'other' | 2,843 | `mars_cells.json` → `cells.<id>.region_group` |

## 4. Where on Earth comes closest, and when

Ten places per site and goal, at least 300 km apart, best first. From `mars_cells.json` → `best_places.<site>.<goal>`. The months are the three best of the calendar score. Region names come from rough boxes in the script, not from a map.
Caveats: it is not a climate match, and a score is a position on each factor's own scale, not a share of likeness.
By landscape, 0 to 1,102 squares per site reach 1.000. So the landscape lists are ten of many equal places, not a ranking.
In the landscape lists, equal scores are ordered by bare area (`bare_km2`), then by environment score, then by id.
In the other lists, equal scores are ordered by the slope overlap before the cap (`scores.slope_overlap`), then by id.
Each place carries `squares_with_this_score`, the number of ranked squares with exactly its score.
A month with a mean of +30 °C or more scores 0, so warm squares can have fewer than three best months.
Closest means the highest score among Earth squares, not close to Mars. Sections 5 and 6 give the gaps.
The environment lists hold the same squares in the same order for every site, because only the scale of cold changes.

### In short: the nearest Earth regions on all five factors

From `mars_cells.json` → `best_places.<site>.full`, places 1 to 3. Each place is a square of approximately 55 km.
This is a first pass on squares of approximately 55 km, thus a score describes a large region.
Caveats: it is not a climate match, and a score is a position on each factor's own scale, not a share of likeness.

| Site | Lists | 1st: region, square | Score | 2nd: region | Score | 3rd: region | Score |
|---|---|---|---|---|---|---|---|
| Jezero | NASA landing site, 2015 exploration zone | Tibetan Plateau, `m_36.25_86.75` | 0.752 | Tibetan Plateau | 0.732 | Atacama Desert | 0.723 |
| Gale | NASA landing site, 2015 exploration zone | Altiplano and Puna, `m_-22.25_-68.25` | 0.736 | Altiplano and Puna | 0.711 | Tibetan Plateau | 0.694 |
| Phoenix | NASA landing site | Qaidam Basin, `m_38.25_93.25` | 0.592 | Tibetan Plateau | 0.588 | Greenland | 0.585 |
| Arcadia Planitia | 2015 exploration zone | Qaidam Basin, `m_38.25_92.25` | 0.726 | Gobi Desert | 0.666 | Tibetan Plateau | 0.664 |
| Deuteronilus Mensae | 2015 exploration zone | Tibetan Plateau, `m_36.75_86.25` | 0.768 | Qaidam Basin | 0.746 | Tibetan Plateau | 0.740 |
| Viking 1 | NASA landing site, 2015 exploration zone | Qaidam Basin, `m_38.25_92.25` | 0.712 | Tibetan Plateau | 0.668 | Tibetan Plateau | 0.655 |
| Viking 2 | NASA landing site | Qaidam Basin, `m_38.25_92.25` | 0.690 | Gobi Desert | 0.649 | Taklamakan and Tarim Basin | 0.645 |
| Pathfinder | NASA landing site | Qaidam Basin, `m_38.25_93.25` | 0.717 | Tibetan Plateau | 0.693 | Atacama Desert | 0.683 |
| Spirit | NASA landing site, 2015 exploration zone | Tibetan Plateau, `m_35.25_84.75` | 0.700 | Qaidam Basin | 0.698 | Tibetan Plateau | 0.697 |
| Opportunity | NASA landing site | Qaidam Basin, `m_38.25_93.25` | 0.665 | Atacama Desert | 0.664 | Tibetan Plateau | 0.662 |
| InSight | NASA landing site | Qaidam Basin, `m_38.25_92.25` | 0.670 | Atacama Desert | 0.666 | Tibetan Plateau | 0.636 |
| Phlegra Montes | 2021 shortlist for human landings | Tibetan Plateau, `m_37.25_88.25` | 0.764 | Tibetan Plateau | 0.749 | Tibetan Plateau | 0.746 |
| AP-1 (Arcadia Planitia) | 2021 shortlist for human landings | Qaidam Basin, `m_38.25_92.25` | 0.725 | Gobi Desert | 0.671 | Taklamakan and Tarim Basin | 0.662 |
| AP-9 (Arcadia Planitia) | 2021 shortlist for human landings | Qaidam Basin, `m_38.25_92.25` | 0.732 | Gobi Desert | 0.671 | Taklamakan and Tarim Basin | 0.662 |
| EM-16 (Erebus Montes) | 2021 shortlist for human landings | Qaidam Basin, `m_38.75_92.75` | 0.733 | Tibetan Plateau | 0.690 | Tibetan Plateau | 0.688 |
| AP-8 (Arcadia Planitia) | 2021 shortlist for human landings | Qaidam Basin, `m_38.25_92.75` | 0.710 | Gobi Desert | 0.666 | Taklamakan and Tarim Basin | 0.659 |
| EM-15 (Erebus Montes) | 2021 shortlist for human landings | Qaidam Basin, `m_38.75_92.75` | 0.742 | Tibetan Plateau | 0.687 | Tibetan Plateau | 0.684 |
| PM-7 (Phlegra Montes) | 2021 shortlist for human landings | Tibetan Plateau, `m_36.25_86.25` | 0.767 | Tibetan Plateau | 0.744 | Qaidam Basin | 0.731 |
| Phlegra Dorsa, Arcadia Planitia | 2015 exploration zone | Qaidam Basin, `m_38.75_93.25` | 0.750 | Tibetan Plateau | 0.713 | Tibetan Plateau | 0.709 |
| Southern Nectaris Fossae | 2015 exploration zone | Tibetan Plateau, `m_36.25_86.25` | 0.767 | Tibetan Plateau | 0.743 | Tibetan Plateau | 0.726 |
| Valles Marineris mouth (southern Acidalia Planitia, as named in the abstract) | 2015 exploration zone | Tibetan Plateau, `m_35.75_86.25` | 0.717 | Qaidam Basin | 0.717 | Tibetan Plateau | 0.712 |
| East Melas Chasma | 2015 exploration zone | Altiplano and Puna, `m_-22.25_-68.25` | 0.744 | Altiplano and Puna | 0.738 | Tibetan Plateau | 0.730 |
| Mawrth Vallis | 2015 exploration zone | Tibetan Plateau, `m_36.25_86.75` | 0.754 | Tibetan Plateau | 0.735 | Tibetan Plateau | 0.732 |
| Nili Fossae | 2015 exploration zone | Tibetan Plateau, `m_36.75_86.75` | 0.744 | Tibetan Plateau | 0.734 | Atacama Desert | 0.734 |
| Acheron Fossae | 2015 exploration zone | Tibetan Plateau, `m_36.25_86.25` | 0.756 | Qaidam Basin | 0.742 | Tibetan Plateau | 0.728 |
| Hebrus Valles | 2015 exploration zone | Qaidam Basin, `m_38.75_92.75` | 0.712 | Atacama Desert | 0.689 | Tibetan Plateau | 0.678 |
| Newton crater | 2015 exploration zone | Tibetan Plateau, `m_36.25_86.25` | 0.761 | Qaidam Basin | 0.735 | Tibetan Plateau | 0.728 |
| Zephyria Planum hills ('Sea Urchins') | 2015 exploration zone | Atacama Desert, `m_-23.25_-68.25` | 0.652 | Qaidam Basin | 0.641 | Tibetan Plateau | 0.636 |
| Cerberus (west of Zunil crater) | 2015 exploration zone | Tibetan Plateau, `m_37.25_88.25` | 0.715 | Tibetan Plateau | 0.711 | Atacama Desert | 0.702 |
| Amazonis Planitia mid-latitude ice | 2015 exploration zone | Qaidam Basin, `m_38.25_92.25` | 0.684 | Gobi Desert | 0.647 | Taklamakan and Tarim Basin | 0.642 |
| Western Noachis Terra chloride deposits | 2015 exploration zone | Tibetan Plateau, `m_36.25_86.25` | 0.762 | Tibetan Plateau | 0.742 | Tibetan Plateau | 0.730 |
| South of Valles Marineris (equatorial site) | 2015 exploration zone | Tibetan Plateau, `m_36.25_86.25` | 0.754 | Tibetan Plateau | 0.732 | Tibetan Plateau | 0.716 |
| McLaughlin crater | 2015 exploration zone | Tibetan Plateau, `m_37.25_88.25` | 0.738 | Tibetan Plateau | 0.736 | Altiplano and Puna | 0.733 |
| South of Firsoff crater, Arabia Terra | 2015 exploration zone | Tibetan Plateau, `m_35.75_85.25` | 0.702 | Atacama Desert | 0.689 | Tibetan Plateau | 0.676 |
| Ismenius Cavus | 2015 exploration zone | Tibetan Plateau, `m_36.25_87.75` | 0.755 | Tibetan Plateau | 0.734 | Tibetan Plateau | 0.733 |
| Hale crater | 2015 exploration zone | Tibetan Plateau, `m_36.75_86.75` | 0.756 | Qaidam Basin | 0.746 | Tibetan Plateau | 0.737 |
| Copernicus crater | 2015 exploration zone | Qaidam Basin, `m_38.25_93.25` | 0.693 | Tibetan Plateau | 0.687 | Tibetan Plateau | 0.682 |
| Huygens crater | 2015 exploration zone | Tibetan Plateau, `m_35.25_85.25` | 0.718 | Qaidam Basin | 0.697 | Tibetan Plateau | 0.695 |
| Mesopotamia (east rim of Hellas) | 2015 exploration zone | Tibetan Plateau, `m_35.75_85.25` | 0.764 | Tibetan Plateau | 0.731 | Qaidam Basin | 0.725 |
| Western Coprates Chasma | 2015 exploration zone | Tibetan Plateau, `m_35.75_85.75` | 0.703 | Altiplano and Puna | 0.694 | Tibetan Plateau | 0.691 |
| Hellas Rim | 2015 exploration zone | Tibetan Plateau, `m_36.75_86.25` | 0.764 | Qaidam Basin | 0.746 | Tibetan Plateau | 0.737 |
| Eastern rim of Hellas impact basin | 2015 exploration zone | Tibetan Plateau, `m_36.25_87.75` | 0.741 | Qaidam Basin | 0.739 | Tibetan Plateau | 0.732 |
| Columbus crater | 2015 exploration zone | Tibetan Plateau, `m_35.25_79.75` | 0.740 | Tibetan Plateau | 0.740 | Qaidam Basin | 0.723 |
| South-west Sinus Meridiani | 2015 exploration zone | Tibetan Plateau, `m_35.75_86.25` | 0.702 | Tibetan Plateau | 0.699 | Atacama Desert | 0.688 |
| Apollinaris Sulci | 2015 exploration zone | Tibetan Plateau, `m_36.75_86.25` | 0.723 | Tibetan Plateau | 0.709 | Altiplano and Puna | 0.708 |
| Deuteronilus Mensae (debris apron zone) | 2015 exploration zone | Tibetan Plateau, `m_36.25_86.25` | 0.760 | Qaidam Basin | 0.743 | Tibetan Plateau | 0.732 |
| Ausonia Cavus | 2015 exploration zone | Tibetan Plateau, `m_36.25_86.25` | 0.770 | Tibetan Plateau | 0.747 | Qaidam Basin | 0.733 |
| Kasei Valles | 2015 exploration zone | Tibetan Plateau, `m_36.75_86.25` | 0.729 | Tibetan Plateau | 0.712 | Tibetan Plateau | 0.707 |
| Gusev crater - Apollinaris Sulci | 2015 exploration zone | Tibetan Plateau, `m_35.75_85.75` | 0.716 | Tibetan Plateau | 0.710 | Altiplano and Puna | 0.706 |
| Aram Chaos | 2015 exploration zone | Altiplano and Puna, `m_-22.25_-68.25` | 0.745 | Altiplano and Puna | 0.735 | Tibetan Plateau | 0.704 |
| Noctis Landing | 2015 exploration zone | Altiplano and Puna, `m_-22.25_-68.25` | 0.726 | Altiplano and Puna | 0.711 | Tibetan Plateau | 0.690 |
| Hypanis (Hypanis and Sabrina deltas) | 2015 exploration zone | Tibetan Plateau, `m_36.25_86.25` | 0.743 | Tibetan Plateau | 0.723 | Tibetan Plateau | 0.699 |
| Hadriacus Palus and Cavi | 2015 exploration zone | Tibetan Plateau, `m_36.75_86.25` | 0.751 | Tibetan Plateau | 0.734 | Qaidam Basin | 0.725 |
| Protonilus Mensae | 2015 exploration zone | Tibetan Plateau, `m_37.25_86.75` | 0.738 | Qaidam Basin | 0.731 | Tibetan Plateau | 0.702 |
| Eastern outlet of Valles Marineris | 2015 exploration zone | Altiplano and Puna, `m_-22.25_-68.25` | 0.738 | Altiplano and Puna | 0.714 | Tibetan Plateau | 0.709 |
| Tempe Terra | 2015 exploration zone | Tibetan Plateau, `m_36.25_86.25` | 0.742 | Qaidam Basin | 0.716 | Tibetan Plateau | 0.713 |
| Southern edge of Meridiani Planum (Endeavour crater area) | 2015 exploration zone | Tibetan Plateau, `m_36.25_86.25` | 0.717 | Tibetan Plateau | 0.704 | Tibetan Plateau | 0.689 |

### Jezero

Caveats: it is not a climate match, and a score is a position on each factor's own scale, not a share of likeness.

**Closest by landscape (slopes and bare ground)**

75 ranked squares tie at the top score of 1.000, so their order here is not a ranking. Tied squares are listed by bare area, then by environment score.

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_15.75_51.25` | Arabian Desert | 1.000 | 1.00 | 0.75 | 0.04 | 1.00 | 0.90 | Jan, Dec, Feb | 26.1 °C | 53 mm |
| 2 | `m_16.75_44.75` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.06 | 1.00 | 0.92 | Dec, Jan, Nov | 24.9 °C | 19 mm |
| 3 | `m_-18.75_12.75` | Namib Desert | 1.000 | 1.00 | 0.30 | 0.11 | 1.00 | 0.97 | Aug, Sep, Jul | 20.8 °C | 204 mm |
| 4 | `m_19.25_36.75` | Sahara | 1.000 | 1.00 | 0.80 | 0.02 | 1.00 | 0.98 | Feb, Jan, Mar | 27.9 °C | 46 mm |
| 5 | `m_19.75_18.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.09 | 1.00 | 0.99 | Jan, Dec, Feb | 21.9 °C | 14 mm |
| 6 | `m_21.25_16.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.08 | 1.00 | 1.00 | Jan, Feb, Nov | 23.5 °C | 18 mm |
| 7 | `m_-21.75_-69.25` | Atacama Desert | 1.000 | 1.00 | 1.00 | 0.14 | 1.00 | 1.00 | Jul, Aug, May | 17.7 °C | 21 mm |
| 8 | `m_23.75_6.25` | Sahara | 1.000 | 1.00 | 0.62 | 0.09 | 1.00 | 0.99 | Feb, Nov, Mar | 21.9 °C | 77 mm |
| 9 | `m_-24.75_-69.75` | Atacama Desert | 1.000 | 1.00 | 1.00 | 0.17 | 1.00 | 0.97 | Aug, Sep, Apr | 15.5 °C | 9 mm |
| 10 | `m_25.75_8.25` | Sahara | 1.000 | 1.00 | 0.97 | 0.08 | 1.00 | 0.95 | Feb, Mar, Apr | 22.8 °C | 28 mm |

**Closest by environment (dry, cold and bare)**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.702 | 0.85 | 0.80 | 0.43 | 1.00 | 0.71 | Mar, Apr, Sep | -7.3 °C | 45 mm |
| 2 | `m_38.75_93.75` | Qaidam Basin | 0.671 | 1.00 | 0.90 | 0.34 | 1.00 | 0.65 | Mar, Apr, May | 0.9 °C | 34 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.663 | 0.90 | 0.65 | 0.45 | 1.00 | 0.73 | Mar, Apr, Sep | -9.3 °C | 72 mm |
| 4 | `m_-77.75_164.25` | McMurdo Dry Valleys | 0.658 | 0.45 | 0.61 | 0.56 | 0.83 | 0.00 | none | -18.9 °C | 80 mm |
| 5 | `m_37.75_89.25` | Tibetan Plateau | 0.651 | 0.83 | 0.75 | 0.37 | 0.99 | 0.67 | Mar, Apr, Sep | -2.0 °C | 52 mm |
| 6 | `m_34.75_83.25` | Tibetan Plateau | 0.640 | 1.00 | 0.64 | 0.41 | 0.99 | 0.74 | Mar, Oct, Apr | -5.8 °C | 73 mm |
| 7 | `m_38.25_74.25` | Pamir and Karakoram | 0.628 | 0.70 | 0.66 | 0.39 | 0.97 | 0.66 | Mar, Sep, Apr | -3.7 °C | 70 mm |
| 8 | `m_81.25_-72.25` | Ellesmere or north-west Greenland | 0.610 | 0.77 | 0.45 | 0.55 | 0.92 | 0.00 | none | -17.4 °C | 129 mm |
| 9 | `m_-25.25_-69.25` | Altiplano and Puna | 0.607 | 0.89 | 1.00 | 0.22 | 1.00 | 0.96 | Aug, Sep, Apr | 10.6 °C | 19 mm |
| 10 | `m_-72.25_68.75` | Antarctica | 0.606 | 0.46 | 0.73 | 0.59 | 0.52 | 0.00 | none | -21.3 °C | 57 mm |

**Closest on all five factors**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.75` | Tibetan Plateau | 0.752 | 1.00 | 0.79 | 0.43 | 0.99 | 0.71 | Mar, Apr, Sep | -7.5 °C | 47 mm |
| 2 | `m_34.75_81.25` | Tibetan Plateau | 0.732 | 1.00 | 0.64 | 0.45 | 0.98 | 0.74 | Mar, Oct, Apr | -8.7 °C | 73 mm |
| 3 | `m_-23.25_-68.75` | Atacama Desert | 0.723 | 1.00 | 0.99 | 0.20 | 0.98 | 1.00 | Aug, May, Sep | 12.4 °C | 26 mm |
| 4 | `m_38.75_93.75` | Qaidam Basin | 0.722 | 1.00 | 0.90 | 0.34 | 1.00 | 0.65 | Mar, Apr, May | 0.9 °C | 34 mm |
| 5 | `m_37.75_89.75` | Tibetan Plateau | 0.694 | 0.96 | 0.74 | 0.35 | 0.96 | 0.67 | Mar, Apr, Sep | -0.5 °C | 55 mm |
| 6 | `m_-26.25_-69.25` | Atacama Desert | 0.683 | 0.79 | 0.87 | 0.23 | 1.00 | 0.94 | Aug, Sep, Oct | 9.9 °C | 37 mm |
| 7 | `m_-18.75_-70.25` | Atacama Desert | 0.674 | 1.00 | 0.98 | 0.15 | 0.99 | 0.97 | Jun, Aug, Sep | 17.2 °C | 26 mm |
| 8 | `m_31.75_79.75` | Tibetan Plateau | 0.658 | 0.89 | 0.50 | 0.38 | 0.90 | 0.81 | Oct, Apr, Mar | -3.3 °C | 113 mm |
| 9 | `m_37.75_74.25` | Pamir and Karakoram | 0.656 | 0.76 | 0.67 | 0.38 | 0.92 | 0.67 | Mar, Apr, Sep | -3.1 °C | 68 mm |
| 10 | `m_28.75_33.75` | Sinai, Negev and Wadi Rum | 0.650 | 1.00 | 0.99 | 0.13 | 1.00 | 0.88 | Mar, Feb, Apr | 18.4 °C | 26 mm |

The closest square on all factors is `m_36.25_86.75` (Tibetan Plateau), with a score of 0.752.
There, Mars is 49.1 °C colder in the yearly mean.
The square gets 1.87 times 25 mm of precipitation a year.
Mars air pressure is 1.32 % of the square's.

### Gale

Caveats: it is not a climate match, and a score is a position on each factor's own scale, not a share of likeness.

**Closest by landscape (slopes and bare ground)**

8 ranked squares tie at the top score of 1.000, so their order here is not a ranking. Tied squares are listed by bare area, then by environment score.

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_20.25_18.25` | Sahara | 1.000 | 1.00 | 0.86 | 0.09 | 1.00 | 1.00 | Mar, Oct, Apr | 22.4 °C | 38 mm |
| 2 | `m_-21.75_-69.25` | Atacama Desert | 1.000 | 1.00 | 1.00 | 0.14 | 1.00 | 1.00 | Sep, Oct, Nov | 17.7 °C | 21 mm |
| 3 | `m_-25.25_-68.75` | Altiplano and Puna | 1.000 | 1.00 | 0.44 | 0.30 | 1.00 | 0.94 | Sep, Oct, Nov | 3.3 °C | 134 mm |
| 4 | `m_27.75_35.75` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.07 | 1.00 | 0.86 | Apr, May | 23.8 °C | 20 mm |
| 5 | `m_38.75_88.75` | Taklamakan and Tarim Basin | 1.000 | 1.00 | 0.84 | 0.23 | 1.00 | 0.49 | Apr, May, Aug | 10.0 °C | 41 mm |
| 6 | `m_28.25_61.75` | other | 1.000 | 1.00 | 0.61 | 0.09 | 1.00 | 0.84 | Apr, Sep, May | 22.2 °C | 79 mm |
| 7 | `m_23.75_39.25` | Arabian Desert | 0.999 | 1.00 | 1.00 | 0.04 | 1.00 | 0.99 | Mar, Apr | 26.1 °C | 19 mm |
| 8 | `m_14.75_48.75` | Arabian Desert | 0.998 | 1.00 | 1.00 | 0.08 | 1.00 | 1.00 | Feb, Mar, Oct | 23.0 °C | 9 mm |
| 9 | `m_22.75_59.25` | Arabian Desert | 0.997 | 1.00 | 0.57 | 0.03 | 0.99 | 1.00 | Mar, Apr | 27.4 °C | 91 mm |
| 10 | `m_36.25_83.25` | Tibetan Plateau | 0.995 | 1.00 | 0.68 | 0.35 | 0.99 | 0.57 | Apr, May, Aug | -0.6 °C | 66 mm |

**Closest by environment (dry, cold and bare)**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.699 | 0.57 | 0.80 | 0.42 | 1.00 | 0.57 | Apr, May, Aug | -7.3 °C | 45 mm |
| 2 | `m_38.75_93.75` | Qaidam Basin | 0.668 | 0.92 | 0.90 | 0.33 | 1.00 | 0.49 | Apr, May, Aug | 0.9 °C | 34 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.660 | 0.84 | 0.65 | 0.45 | 1.00 | 0.60 | Apr, May, Jul | -9.3 °C | 72 mm |
| 4 | `m_-77.75_164.25` | McMurdo Dry Valleys | 0.655 | 0.87 | 0.61 | 0.56 | 0.83 | 0.00 | none | -18.9 °C | 80 mm |
| 5 | `m_37.75_89.25` | Tibetan Plateau | 0.648 | 1.00 | 0.75 | 0.36 | 0.99 | 0.52 | Apr, May, Aug | -2.0 °C | 52 mm |
| 6 | `m_34.75_83.25` | Tibetan Plateau | 0.638 | 0.70 | 0.64 | 0.41 | 0.99 | 0.62 | Apr, May, Jun | -5.8 °C | 73 mm |
| 7 | `m_38.25_74.25` | Pamir and Karakoram | 0.625 | 1.00 | 0.66 | 0.38 | 0.97 | 0.50 | Apr, May, Aug | -3.7 °C | 70 mm |
| 8 | `m_81.25_-72.25` | Ellesmere or north-west Greenland | 0.608 | 0.92 | 0.45 | 0.54 | 0.92 | 0.00 | none | -17.4 °C | 129 mm |
| 9 | `m_-25.25_-69.25` | Altiplano and Puna | 0.604 | 0.88 | 1.00 | 0.22 | 1.00 | 0.94 | Sep, Oct, Nov | 10.6 °C | 19 mm |
| 10 | `m_-72.25_68.75` | Antarctica | 0.603 | 0.83 | 0.73 | 0.58 | 0.52 | 0.00 | none | -21.3 °C | 57 mm |

**Closest on all five factors**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_-22.25_-68.25` | Altiplano and Puna | 0.736 | 0.99 | 0.83 | 0.29 | 0.90 | 1.00 | Sep, Oct, Nov | 4.4 °C | 42 mm |
| 2 | `m_-25.25_-69.25` | Altiplano and Puna | 0.711 | 0.88 | 1.00 | 0.22 | 1.00 | 0.94 | Sep, Oct, Nov | 10.6 °C | 19 mm |
| 3 | `m_37.25_86.75` | Tibetan Plateau | 0.694 | 1.00 | 0.81 | 0.37 | 1.00 | 0.54 | Apr, May, Aug | -2.4 °C | 44 mm |
| 4 | `m_33.75_80.75` | Tibetan Plateau | 0.692 | 1.00 | 0.61 | 0.40 | 0.99 | 0.65 | Apr, May, Jun | -5.4 °C | 81 mm |
| 5 | `m_-29.75_-69.75` | Altiplano and Puna | 0.677 | 0.89 | 0.61 | 0.34 | 0.99 | 0.79 | Oct, Nov, Mar | 0.5 °C | 81 mm |
| 6 | `m_-19.25_-70.25` | Atacama Desert | 0.673 | 1.00 | 1.00 | 0.14 | 0.99 | 1.00 | Sep, Oct, Nov | 17.8 °C | 20 mm |
| 7 | `m_36.25_83.25` | Tibetan Plateau | 0.668 | 1.00 | 0.68 | 0.35 | 0.99 | 0.57 | Apr, May, Aug | -0.6 °C | 66 mm |
| 8 | `m_38.75_93.75` | Qaidam Basin | 0.668 | 0.92 | 0.90 | 0.33 | 1.00 | 0.49 | Apr, May, Aug | 0.9 °C | 34 mm |
| 9 | `m_35.75_78.25` | Tibetan Plateau | 0.667 | 0.97 | 0.55 | 0.44 | 0.96 | 0.59 | Apr, Aug, May | -8.3 °C | 95 mm |
| 10 | `m_37.75_90.25` | Tibetan Plateau | 0.661 | 0.99 | 0.74 | 0.35 | 0.95 | 0.52 | Apr, May, Aug | -0.5 °C | 55 mm |

The closest square on all factors is `m_-22.25_-68.25` (Altiplano and Puna), with a score of 0.736.
There, Mars is 62.2 °C colder in the yearly mean.
The square gets 1.66 times 25 mm of precipitation a year.
Mars air pressure is 1.35 % of the square's.

### Phoenix

Caveats: it is not a climate match, and a score is a position on each factor's own scale, not a share of likeness.

**Closest by landscape (slopes and bare ground)**

410 ranked squares tie at the top score of 1.000, so their order here is not a ranking. Tied squares are listed by bare area, then by environment score.

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_15.75_27.25` | Sahara | 1.000 | 1.00 | 0.78 | 0.04 | 1.00 | 0.00 | none | 24.8 °C | 48 mm |
| 2 | `m_16.25_47.75` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.03 | 1.00 | 0.00 | none | 25.7 °C | 21 mm |
| 3 | `m_16.25_51.75` | Arabian Desert | 1.000 | 1.00 | 0.57 | 0.03 | 1.00 | 0.00 | none | 26.2 °C | 90 mm |
| 4 | `m_16.75_30.25` | Sahara | 1.000 | 1.00 | 0.84 | 0.02 | 1.00 | 0.00 | none | 27.1 °C | 40 mm |
| 5 | `m_17.25_23.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.06 | 1.00 | 0.00 | none | 22.8 °C | 17 mm |
| 6 | `m_17.25_44.75` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.03 | 1.00 | 0.00 | none | 25.7 °C | 18 mm |
| 7 | `m_17.75_54.75` | Arabian Desert | 1.000 | 1.00 | 0.37 | 0.03 | 1.00 | 0.00 | none | 26.5 °C | 163 mm |
| 8 | `m_18.25_9.75` | Sahara | 1.000 | 1.00 | 0.90 | 0.03 | 1.00 | 0.00 | none | 26.3 °C | 34 mm |
| 9 | `m_18.25_32.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.01 | 1.00 | 0.00 | none | 28.6 °C | 13 mm |
| 10 | `m_18.75_21.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.03 | 1.00 | 0.00 | none | 25.8 °C | 7 mm |

**Closest by environment (dry, cold and bare)**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.621 | 0.89 | 0.80 | 0.30 | 1.00 | 0.33 | Jan, Dec, Feb | -7.3 °C | 45 mm |
| 2 | `m_38.75_93.75` | Qaidam Basin | 0.594 | 0.55 | 0.90 | 0.23 | 1.00 | 0.38 | Jan, Dec, Feb | 0.9 °C | 34 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.587 | 0.75 | 0.65 | 0.32 | 1.00 | 0.31 | Dec, Jan, Nov | -9.3 °C | 72 mm |
| 4 | `m_-77.75_164.25` | McMurdo Dry Valleys | 0.583 | 0.17 | 0.61 | 0.39 | 0.83 | 0.78 | Sep, Aug, Apr | -18.9 °C | 80 mm |
| 5 | `m_37.75_89.25` | Tibetan Plateau | 0.576 | 0.52 | 0.75 | 0.26 | 0.99 | 0.36 | Jan, Dec, Feb | -2.0 °C | 52 mm |
| 6 | `m_34.75_83.25` | Tibetan Plateau | 0.567 | 0.72 | 0.64 | 0.29 | 0.99 | 0.30 | Jan, Dec, Feb | -5.8 °C | 73 mm |
| 7 | `m_38.25_74.25` | Pamir and Karakoram | 0.556 | 0.40 | 0.66 | 0.27 | 0.97 | 0.37 | Dec, Jan, Nov | -3.7 °C | 70 mm |
| 8 | `m_81.25_-72.25` | Ellesmere or north-west Greenland | 0.540 | 0.31 | 0.45 | 0.38 | 0.92 | 0.71 | Mar, Apr, May | -17.4 °C | 129 mm |
| 9 | `m_-25.25_-69.25` | Altiplano and Puna | 0.537 | 0.41 | 1.00 | 0.16 | 1.00 | 0.11 | Jul, Jun, May | 10.6 °C | 19 mm |
| 10 | `m_-72.25_68.75` | Antarctica | 0.536 | 0.20 | 0.73 | 0.41 | 0.52 | 0.89 | Apr, Aug, Mar | -21.3 °C | 57 mm |

**Closest on all five factors**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_38.25_93.25` | Qaidam Basin | 0.592 | 1.00 | 0.94 | 0.21 | 1.00 | 0.37 | Jan, Dec, Feb | 4.0 °C | 30 mm |
| 2 | `m_36.25_86.25` | Tibetan Plateau | 0.588 | 0.89 | 0.80 | 0.30 | 1.00 | 0.33 | Jan, Dec, Feb | -7.3 °C | 45 mm |
| 3 | `m_81.75_-60.75` | Greenland | 0.585 | 0.83 | 0.34 | 0.36 | 0.97 | 0.70 | Mar, Apr, May | -15.3 °C | 182 mm |
| 4 | `m_-84.25_161.75` | Transantarctic Mountains | 0.579 | 1.00 | 0.88 | 0.54 | 0.21 | 0.65 | Sep, Oct, Nov | -37.6 °C | 36 mm |
| 5 | `m_37.25_89.75` | Tibetan Plateau | 0.578 | 1.00 | 0.71 | 0.26 | 1.00 | 0.35 | Jan, Dec, Feb | -2.3 °C | 59 mm |
| 6 | `m_44.25_96.75` | Gobi Desert | 0.576 | 0.95 | 0.72 | 0.19 | 1.00 | 0.49 | Jan, Dec, Feb | 6.5 °C | 58 mm |
| 7 | `m_35.25_82.75` | Tibetan Plateau | 0.574 | 1.00 | 0.66 | 0.31 | 0.98 | 0.31 | Jan, Dec, Nov | -8.5 °C | 69 mm |
| 8 | `m_77.75_-93.75` | Canadian High Arctic | 0.572 | 0.94 | 0.27 | 0.35 | 0.88 | 0.78 | Feb, Mar, Apr | -14.1 °C | 222 mm |
| 9 | `m_41.25_90.75` | Taklamakan and Tarim Basin | 0.572 | 1.00 | 0.93 | 0.15 | 1.00 | 0.43 | Jan, Dec, Feb | 11.0 °C | 30 mm |
| 10 | `m_-77.75_160.75` | McMurdo Dry Valleys | 0.567 | 0.45 | 0.58 | 0.49 | 0.58 | 0.78 | Sep, Mar, Apr | -31.6 °C | 88 mm |

The closest square on all factors is `m_38.25_93.25` (Qaidam Basin), with a score of 0.592.
There, Mars is 98.7 °C colder in the yearly mean.
The square gets 1.20 times 25 mm of precipitation a year.
Mars air pressure is 1.15 % of the square's.

### Arcadia Planitia

Caveats: it is not a climate match, and a score is a position on each factor's own scale, not a share of likeness.

**Closest by landscape (slopes and bare ground)**

360 ranked squares tie at the top score of 1.000, so their order here is not a ranking. Tied squares are listed by bare area, then by environment score.

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_15.75_46.25` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.03 | 1.00 | 0.50 | Jan, Dec, Feb | 26.6 °C | 21 mm |
| 2 | `m_16.25_9.75` | Sahara | 1.000 | 1.00 | 0.57 | 0.03 | 1.00 | 0.51 | Jan, Dec, Feb | 26.4 °C | 91 mm |
| 3 | `m_16.75_29.75` | Sahara | 1.000 | 1.00 | 0.84 | 0.03 | 1.00 | 0.52 | Jan, Dec, Feb | 27.1 °C | 40 mm |
| 4 | `m_17.25_26.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.04 | 1.00 | 0.53 | Jan, Dec, Feb | 25.7 °C | 12 mm |
| 5 | `m_17.75_20.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.03 | 1.00 | 0.54 | Jan, Dec, Feb | 26.9 °C | 15 mm |
| 6 | `m_17.75_48.25` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.02 | 1.00 | 0.54 | Jan, Dec, Feb | 27.8 °C | 21 mm |
| 7 | `m_18.25_23.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.06 | 1.00 | 0.55 | Jan, Dec, Feb | 23.4 °C | 4 mm |
| 8 | `m_18.75_56.25` | Arabian Desert | 1.000 | 1.00 | 0.45 | 0.03 | 1.00 | 0.56 | Dec, Jan, Nov | 27.3 °C | 131 mm |
| 9 | `m_18.75_-1.25` | Sahara | 1.000 | 1.00 | 0.61 | 0.01 | 1.00 | 0.56 | Jan, Dec, Feb | 28.6 °C | 80 mm |
| 10 | `m_18.75_53.25` | Arabian Desert | 1.000 | 1.00 | 0.75 | 0.01 | 1.00 | 0.56 | Jan, Dec, Feb | 29.0 °C | 53 mm |

**Closest by environment (dry, cold and bare)**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.657 | 0.41 | 0.80 | 0.35 | 1.00 | 0.91 | Jan, Dec, Feb | -7.3 °C | 45 mm |
| 2 | `m_38.75_93.75` | Qaidam Basin | 0.628 | 0.31 | 0.90 | 0.28 | 1.00 | 0.93 | Jan, Dec, Feb | 0.9 °C | 34 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.621 | 0.56 | 0.65 | 0.37 | 1.00 | 0.89 | Dec, Jan, Nov | -9.3 °C | 72 mm |
| 4 | `m_-77.75_164.25` | McMurdo Dry Valleys | 0.616 | 0.13 | 0.61 | 0.46 | 0.83 | 0.20 | Nov, Dec, Jan | -18.9 °C | 80 mm |
| 5 | `m_37.75_89.25` | Tibetan Plateau | 0.610 | 0.45 | 0.75 | 0.30 | 0.99 | 0.93 | Jan, Dec, Feb | -2.0 °C | 52 mm |
| 6 | `m_34.75_83.25` | Tibetan Plateau | 0.600 | 0.33 | 0.64 | 0.34 | 0.99 | 0.88 | Jan, Dec, Feb | -5.8 °C | 73 mm |
| 7 | `m_38.25_74.25` | Pamir and Karakoram | 0.588 | 0.29 | 0.66 | 0.32 | 0.97 | 0.93 | Dec, Jan, Nov | -3.7 °C | 70 mm |
| 8 | `m_81.25_-72.25` | Ellesmere or north-west Greenland | 0.572 | 0.18 | 0.45 | 0.45 | 0.92 | 0.13 | May, Jun, Jul | -17.4 °C | 129 mm |
| 9 | `m_-25.25_-69.25` | Altiplano and Puna | 0.568 | 0.23 | 1.00 | 0.18 | 1.00 | 0.69 | Jul, Jun, Aug | 10.6 °C | 19 mm |
| 10 | `m_-72.25_68.75` | Antarctica | 0.567 | 0.13 | 0.73 | 0.49 | 0.52 | 0.31 | Oct, Feb, Jan | -21.3 °C | 57 mm |

**Closest on all five factors**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_38.25_92.25` | Qaidam Basin | 0.726 | 0.96 | 0.92 | 0.24 | 1.00 | 0.93 | Jan, Dec, Feb | 4.2 °C | 32 mm |
| 2 | `m_41.75_101.75` | Gobi Desert | 0.666 | 0.98 | 0.77 | 0.19 | 1.00 | 0.91 | Jan, Feb, Nov | 9.8 °C | 50 mm |
| 3 | `m_35.25_84.75` | Tibetan Plateau | 0.664 | 0.62 | 0.69 | 0.34 | 1.00 | 0.89 | Jan, Dec, Feb | -5.9 °C | 63 mm |
| 4 | `m_39.25_86.25` | Taklamakan and Tarim Basin | 0.661 | 1.00 | 0.84 | 0.16 | 1.00 | 0.93 | Jan, Dec, Feb | 13.1 °C | 40 mm |
| 5 | `m_35.25_79.75` | Tibetan Plateau | 0.654 | 0.56 | 0.65 | 0.37 | 1.00 | 0.89 | Dec, Jan, Nov | -9.3 °C | 72 mm |
| 6 | `m_37.75_82.75` | Taklamakan and Tarim Basin | 0.637 | 1.00 | 0.72 | 0.16 | 0.98 | 0.93 | Jan, Dec, Feb | 13.2 °C | 58 mm |
| 7 | `m_38.75_79.25` | Taklamakan and Tarim Basin | 0.623 | 1.00 | 0.64 | 0.16 | 1.00 | 0.93 | Jan, Dec, Feb | 13.4 °C | 73 mm |
| 8 | `m_41.25_81.25` | Taklamakan and Tarim Basin | 0.623 | 0.99 | 0.55 | 0.19 | 0.99 | 0.92 | Jan, Feb, Mar | 10.1 °C | 95 mm |
| 9 | `m_41.75_62.25` | Karakum and Kyzylkum | 0.623 | 1.00 | 0.68 | 0.15 | 1.00 | 0.91 | Jan, Nov, Oct | 14.0 °C | 66 mm |
| 10 | `m_41.25_91.25` | Taklamakan and Tarim Basin | 0.623 | 0.63 | 0.92 | 0.17 | 1.00 | 0.92 | Jan, Feb, Nov | 11.6 °C | 32 mm |

The closest square on all factors is `m_38.25_92.25` (Qaidam Basin), with a score of 0.726.
There, Mars is 79.6 °C colder in the yearly mean.
The square gets 1.27 times 25 mm of precipitation a year.
Mars air pressure is 1.13 % of the square's.

### Deuteronilus Mensae

Caveats: it is not a climate match, and a score is a position on each factor's own scale, not a share of likeness.

**Closest by landscape (slopes and bare ground)**

161 ranked squares tie at the top score of 1.000, so their order here is not a ranking. Tied squares are listed by bare area, then by environment score.

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_12.75_41.25` | Danakil Depression | 1.000 | 1.00 | 0.21 | 0.00 | 1.00 | 0.44 | Jan, Dec, Feb | 33.1 °C | 266 mm |
| 2 | `m_15.75_50.75` | Arabian Desert | 1.000 | 1.00 | 0.94 | 0.04 | 1.00 | 0.50 | Jan, Dec, Feb | 25.8 °C | 30 mm |
| 3 | `m_17.75_23.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.05 | 1.00 | 0.54 | Jan, Dec, Feb | 24.6 °C | 10 mm |
| 4 | `m_17.75_36.75` | Sahara | 1.000 | 1.00 | 0.68 | 0.04 | 1.00 | 0.54 | Feb, Jan, Mar | 26.3 °C | 65 mm |
| 5 | `m_18.75_43.75` | Arabian Desert | 1.000 | 1.00 | 0.85 | 0.06 | 1.00 | 0.56 | Dec, Jan, Nov | 24.4 °C | 39 mm |
| 6 | `m_18.75_9.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.04 | 1.00 | 0.56 | Jan, Dec, Feb | 26.0 °C | 22 mm |
| 7 | `m_19.75_19.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.05 | 1.00 | 0.58 | Jan, Dec, Feb | 24.7 °C | 5 mm |
| 8 | `m_20.25_-13.25` | Sahara | 1.000 | 1.00 | 0.30 | 0.02 | 1.00 | 0.59 | Jan, Dec, Feb | 27.5 °C | 204 mm |
| 9 | `m_20.75_16.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.06 | 1.00 | 0.60 | Jan, Dec, Feb | 24.4 °C | 22 mm |
| 10 | `m_20.75_36.75` | Sahara | 1.000 | 1.00 | 0.90 | 0.02 | 1.00 | 0.60 | Feb, Jan, Mar | 28.0 °C | 34 mm |

**Closest by environment (dry, cold and bare)**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.666 | 0.97 | 0.80 | 0.37 | 1.00 | 0.91 | Jan, Dec, Feb | -7.3 °C | 45 mm |
| 2 | `m_38.75_93.75` | Qaidam Basin | 0.636 | 0.96 | 0.90 | 0.29 | 1.00 | 0.93 | Jan, Dec, Feb | 0.9 °C | 34 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.629 | 1.00 | 0.65 | 0.39 | 1.00 | 0.89 | Dec, Jan, Nov | -9.3 °C | 72 mm |
| 4 | `m_-77.75_164.25` | McMurdo Dry Valleys | 0.624 | 0.45 | 0.61 | 0.48 | 0.83 | 0.20 | Nov, Dec, Jan | -18.9 °C | 80 mm |
| 5 | `m_37.75_89.25` | Tibetan Plateau | 0.617 | 0.88 | 0.75 | 0.32 | 0.99 | 0.93 | Jan, Dec, Feb | -2.0 °C | 52 mm |
| 6 | `m_34.75_83.25` | Tibetan Plateau | 0.608 | 0.99 | 0.64 | 0.35 | 0.99 | 0.88 | Jan, Dec, Feb | -5.8 °C | 73 mm |
| 7 | `m_38.25_74.25` | Pamir and Karakoram | 0.595 | 0.72 | 0.66 | 0.33 | 0.97 | 0.93 | Dec, Jan, Nov | -3.7 °C | 70 mm |
| 8 | `m_81.25_-72.25` | Ellesmere or north-west Greenland | 0.579 | 0.63 | 0.45 | 0.47 | 0.92 | 0.13 | May, Jun, Jul | -17.4 °C | 129 mm |
| 9 | `m_-25.25_-69.25` | Altiplano and Puna | 0.575 | 0.74 | 1.00 | 0.19 | 1.00 | 0.69 | Jul, Jun, Aug | 10.6 °C | 19 mm |
| 10 | `m_-72.25_68.75` | Antarctica | 0.574 | 0.53 | 0.73 | 0.51 | 0.52 | 0.31 | Oct, Feb, Jan | -21.3 °C | 57 mm |

**Closest on all five factors**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.75_86.25` | Tibetan Plateau | 0.768 | 1.00 | 0.81 | 0.36 | 1.00 | 0.92 | Jan, Dec, Feb | -6.4 °C | 44 mm |
| 2 | `m_38.75_92.25` | Qaidam Basin | 0.746 | 1.00 | 0.91 | 0.27 | 1.00 | 0.93 | Jan, Dec, Feb | 2.4 °C | 32 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.740 | 1.00 | 0.65 | 0.39 | 1.00 | 0.89 | Dec, Jan, Nov | -9.3 °C | 72 mm |
| 4 | `m_35.25_83.25` | Tibetan Plateau | 0.736 | 1.00 | 0.66 | 0.36 | 1.00 | 0.89 | Jan, Dec, Feb | -7.0 °C | 68 mm |
| 5 | `m_41.25_89.25` | Taklamakan and Tarim Basin | 0.696 | 1.00 | 0.89 | 0.20 | 1.00 | 0.92 | Jan, Feb, Nov | 9.8 °C | 35 mm |
| 6 | `m_36.25_89.75` | Tibetan Plateau | 0.689 | 1.00 | 0.53 | 0.35 | 0.90 | 0.91 | Jan, Dec, Feb | -6.0 °C | 101 mm |
| 7 | `m_38.25_74.25` | Pamir and Karakoram | 0.676 | 0.72 | 0.66 | 0.33 | 0.97 | 0.93 | Dec, Jan, Nov | -3.7 °C | 70 mm |
| 8 | `m_44.25_97.25` | Gobi Desert | 0.676 | 0.98 | 0.70 | 0.24 | 1.00 | 0.86 | Feb, Nov, Mar | 6.1 °C | 60 mm |
| 9 | `m_41.25_96.25` | Gobi Desert | 0.671 | 0.93 | 0.64 | 0.25 | 1.00 | 0.92 | Jan, Feb, Nov | 4.8 °C | 74 mm |
| 10 | `m_37.25_95.25` | Qaidam Basin | 0.671 | 1.00 | 0.59 | 0.25 | 1.00 | 0.93 | Jan, Dec, Feb | 4.6 °C | 86 mm |

The closest square on all factors is `m_36.75_86.25` (Tibetan Plateau), with a score of 0.768.
There, Mars is 65.1 °C colder in the yearly mean.
The square gets 1.76 times 25 mm of precipitation a year.
Mars air pressure is 1.39 % of the square's.

### Viking 1

Caveats: it is not a climate match, and a score is a position on each factor's own scale, not a share of likeness.

**Closest by landscape (slopes and bare ground)**

340 ranked squares tie at the top score of 1.000, so their order here is not a ranking. Tied squares are listed by bare area, then by environment score.

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_15.75_47.25` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.04 | 1.00 | 0.83 | Jan, Dec, Feb | 26.6 °C | 17 mm |
| 2 | `m_16.75_29.75` | Sahara | 1.000 | 1.00 | 0.84 | 0.03 | 1.00 | 0.85 | Jan, Dec, Feb | 27.1 °C | 40 mm |
| 3 | `m_17.75_24.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.07 | 1.00 | 0.87 | Jan, Dec, Feb | 23.4 °C | 5 mm |
| 4 | `m_17.75_9.75` | Sahara | 1.000 | 1.00 | 0.78 | 0.04 | 1.00 | 0.87 | Jan, Dec, Feb | 26.5 °C | 48 mm |
| 5 | `m_17.75_18.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.03 | 1.00 | 0.87 | Jan, Dec, Feb | 27.7 °C | 7 mm |
| 6 | `m_18.25_45.25` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.05 | 1.00 | 0.88 | Jan, Dec, Feb | 25.7 °C | 17 mm |
| 7 | `m_18.25_51.25` | Arabian Desert | 1.000 | 1.00 | 0.90 | 0.02 | 1.00 | 0.88 | Jan, Dec, Feb | 28.6 °C | 34 mm |
| 8 | `m_19.25_26.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.07 | 1.00 | 0.90 | Jan, Dec, Feb | 23.5 °C | 2 mm |
| 9 | `m_19.25_15.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.04 | 1.00 | 0.90 | Jan, Dec, Feb | 26.8 °C | 12 mm |
| 10 | `m_19.75_21.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.07 | 1.00 | 0.91 | Jan, Dec, Feb | 24.1 °C | 5 mm |

**Closest by environment (dry, cold and bare)**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.695 | 0.42 | 0.80 | 0.42 | 1.00 | 0.73 | Mar, Oct, Apr | -7.3 °C | 45 mm |
| 2 | `m_38.75_93.75` | Qaidam Basin | 0.665 | 0.26 | 0.90 | 0.33 | 1.00 | 0.68 | Mar, Oct, Apr | 0.9 °C | 34 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.657 | 0.53 | 0.65 | 0.44 | 1.00 | 0.75 | Mar, Oct, Apr | -9.3 °C | 72 mm |
| 4 | `m_-77.75_164.25` | McMurdo Dry Valleys | 0.652 | 0.05 | 0.61 | 0.55 | 0.83 | 0.00 | none | -18.9 °C | 80 mm |
| 5 | `m_37.75_89.25` | Tibetan Plateau | 0.645 | 0.39 | 0.75 | 0.36 | 0.99 | 0.70 | Mar, Oct, Apr | -2.0 °C | 52 mm |
| 6 | `m_34.75_83.25` | Tibetan Plateau | 0.635 | 0.33 | 0.64 | 0.40 | 0.99 | 0.76 | Feb, Mar, Oct | -5.8 °C | 73 mm |
| 7 | `m_38.25_74.25` | Pamir and Karakoram | 0.622 | 0.20 | 0.66 | 0.38 | 0.97 | 0.69 | Oct, Mar, Sep | -3.7 °C | 70 mm |
| 8 | `m_81.25_-72.25` | Ellesmere or north-west Greenland | 0.605 | 0.10 | 0.45 | 0.53 | 0.92 | 0.00 | none | -17.4 °C | 129 mm |
| 9 | `m_-25.25_-69.25` | Altiplano and Puna | 0.601 | 0.17 | 1.00 | 0.22 | 1.00 | 0.96 | Jul, Aug, May | 10.6 °C | 19 mm |
| 10 | `m_-72.25_68.75` | Antarctica | 0.600 | 0.05 | 0.73 | 0.58 | 0.52 | 0.00 | none | -21.3 °C | 57 mm |

**Closest on all five factors**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_38.25_92.25` | Qaidam Basin | 0.712 | 1.00 | 0.92 | 0.29 | 1.00 | 0.69 | Mar, Oct, Apr | 4.2 °C | 32 mm |
| 2 | `m_35.25_85.25` | Tibetan Plateau | 0.668 | 0.63 | 0.69 | 0.40 | 0.99 | 0.75 | Mar, Oct, Apr | -5.9 °C | 63 mm |
| 3 | `m_34.75_79.25` | Tibetan Plateau | 0.655 | 0.64 | 0.58 | 0.43 | 1.00 | 0.76 | Feb, Oct, Mar | -7.9 °C | 88 mm |
| 4 | `m_-23.25_-68.25` | Atacama Desert | 0.642 | 0.64 | 0.94 | 0.18 | 1.00 | 0.98 | Jul, Jun, Aug | 13.6 °C | 30 mm |
| 5 | `m_39.25_86.75` | Taklamakan and Tarim Basin | 0.640 | 1.00 | 0.86 | 0.19 | 1.00 | 0.67 | Mar, Apr, Sep | 13.3 °C | 38 mm |
| 6 | `m_41.75_101.75` | Gobi Desert | 0.634 | 0.96 | 0.77 | 0.23 | 1.00 | 0.61 | Mar, Apr, May | 9.8 °C | 50 mm |
| 7 | `m_24.75_26.75` | Sahara | 0.627 | 0.96 | 1.00 | 0.10 | 1.00 | 0.97 | Jan, Feb, Nov | 20.7 °C | 4 mm |
| 8 | `m_27.75_39.75` | Arabian Desert | 0.623 | 0.99 | 0.99 | 0.11 | 1.00 | 0.91 | Feb, Mar, Nov | 20.6 °C | 26 mm |
| 9 | `m_37.75_82.75` | Taklamakan and Tarim Basin | 0.622 | 1.00 | 0.72 | 0.19 | 0.98 | 0.70 | Mar, Oct, Apr | 13.2 °C | 58 mm |
| 10 | `m_31.25_38.75` | Arabian Desert | 0.620 | 1.00 | 0.94 | 0.12 | 1.00 | 0.84 | Feb, Mar, Apr | 19.6 °C | 30 mm |

The closest square on all factors is `m_38.25_92.25` (Qaidam Basin), with a score of 0.712.
There, Mars is 63.2 °C colder in the yearly mean.
The square gets 1.27 times 25 mm of precipitation a year.
Mars air pressure is 1.09 % of the square's.

### Viking 2

Caveats: it is not a climate match, and a score is a position on each factor's own scale, not a share of likeness.

**Closest by landscape (slopes and bare ground)**

103 ranked squares tie at the top score of 1.000, so their order here is not a ranking. Tied squares are listed by bare area, then by environment score.

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_15.75_27.75` | Sahara | 1.000 | 1.00 | 0.78 | 0.05 | 1.00 | 0.33 | Jan, Dec, Feb | 24.8 °C | 48 mm |
| 2 | `m_17.25_30.25` | Sahara | 1.000 | 1.00 | 0.94 | 0.03 | 1.00 | 0.36 | Jan, Dec, Feb | 27.0 °C | 30 mm |
| 3 | `m_18.25_44.75` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.04 | 1.00 | 0.38 | Jan, Dec, Feb | 25.7 °C | 17 mm |
| 4 | `m_18.25_20.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.03 | 1.00 | 0.38 | Jan, Dec, Feb | 26.2 °C | 9 mm |
| 5 | `m_19.25_16.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.03 | 1.00 | 0.40 | Jan, Dec, Feb | 26.9 °C | 14 mm |
| 6 | `m_19.25_-11.25` | Sahara | 1.000 | 1.00 | 0.56 | 0.03 | 1.00 | 0.40 | Jan, Dec, Feb | 26.8 °C | 94 mm |
| 7 | `m_19.75_23.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.06 | 1.00 | 0.41 | Jan, Dec, Feb | 23.1 °C | 5 mm |
| 8 | `m_20.25_5.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.03 | 1.00 | 0.42 | Jan, Dec, Feb | 26.7 °C | 23 mm |
| 9 | `m_20.75_8.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.04 | 1.00 | 0.43 | Jan, Dec, Feb | 25.3 °C | 15 mm |
| 10 | `m_20.75_32.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.04 | 1.00 | 0.43 | Jan, Dec, Feb | 26.0 °C | 2 mm |

**Closest by environment (dry, cold and bare)**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.648 | 0.42 | 0.80 | 0.34 | 1.00 | 0.74 | Jan, Dec, Feb | -7.3 °C | 45 mm |
| 2 | `m_38.75_93.75` | Qaidam Basin | 0.619 | 0.23 | 0.90 | 0.26 | 1.00 | 0.79 | Jan, Dec, Feb | 0.9 °C | 34 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.613 | 0.47 | 0.65 | 0.36 | 1.00 | 0.72 | Dec, Jan, Nov | -9.3 °C | 72 mm |
| 4 | `m_-77.75_164.25` | McMurdo Dry Valleys | 0.607 | 0.03 | 0.61 | 0.44 | 0.83 | 0.37 | Oct, Nov, Dec | -18.9 °C | 80 mm |
| 5 | `m_37.75_89.25` | Tibetan Plateau | 0.601 | 0.28 | 0.75 | 0.29 | 0.99 | 0.77 | Jan, Dec, Feb | -2.0 °C | 52 mm |
| 6 | `m_34.75_83.25` | Tibetan Plateau | 0.592 | 0.34 | 0.64 | 0.33 | 0.99 | 0.71 | Jan, Dec, Feb | -5.8 °C | 73 mm |
| 7 | `m_38.25_74.25` | Pamir and Karakoram | 0.580 | 0.18 | 0.66 | 0.31 | 0.97 | 0.78 | Dec, Jan, Nov | -3.7 °C | 70 mm |
| 8 | `m_81.25_-72.25` | Ellesmere or north-west Greenland | 0.564 | 0.08 | 0.45 | 0.43 | 0.92 | 0.30 | Apr, May, Jun | -17.4 °C | 129 mm |
| 9 | `m_-25.25_-69.25` | Altiplano and Puna | 0.560 | 0.14 | 1.00 | 0.18 | 1.00 | 0.52 | Jul, Jun, Aug | 10.6 °C | 19 mm |
| 10 | `m_-72.25_68.75` | Antarctica | 0.559 | 0.03 | 0.73 | 0.47 | 0.52 | 0.48 | Mar, Oct, Feb | -21.3 °C | 57 mm |

**Closest on all five factors**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_38.25_92.25` | Qaidam Basin | 0.690 | 0.93 | 0.92 | 0.23 | 1.00 | 0.78 | Jan, Dec, Feb | 4.2 °C | 32 mm |
| 2 | `m_41.25_101.75` | Gobi Desert | 0.649 | 1.00 | 0.77 | 0.18 | 1.00 | 0.84 | Jan, Dec, Feb | 10.3 °C | 50 mm |
| 3 | `m_41.75_91.75` | Taklamakan and Tarim Basin | 0.645 | 0.88 | 0.88 | 0.17 | 1.00 | 0.85 | Jan, Dec, Feb | 11.4 °C | 36 mm |
| 4 | `m_35.25_85.25` | Tibetan Plateau | 0.633 | 0.63 | 0.69 | 0.33 | 0.99 | 0.72 | Jan, Dec, Feb | -5.9 °C | 63 mm |
| 5 | `m_45.25_107.75` | Gobi Desert | 0.631 | 1.00 | 0.46 | 0.24 | 1.00 | 0.92 | Jan, Dec, Feb | 3.8 °C | 127 mm |
| 6 | `m_38.75_84.75` | Taklamakan and Tarim Basin | 0.627 | 0.98 | 0.80 | 0.16 | 1.00 | 0.79 | Jan, Dec, Feb | 12.7 °C | 46 mm |
| 7 | `m_43.75_97.25` | Gobi Desert | 0.624 | 0.74 | 0.72 | 0.20 | 1.00 | 0.89 | Jan, Dec, Feb | 7.8 °C | 58 mm |
| 8 | `m_34.75_79.25` | Tibetan Plateau | 0.617 | 0.63 | 0.58 | 0.34 | 1.00 | 0.71 | Dec, Jan, Nov | -7.9 °C | 88 mm |
| 9 | `m_42.75_57.25` | Karakum and Kyzylkum | 0.607 | 0.95 | 0.62 | 0.16 | 1.00 | 0.87 | Feb, Jan, Dec | 12.2 °C | 78 mm |
| 10 | `m_44.75_103.75` | Gobi Desert | 0.606 | 0.86 | 0.46 | 0.23 | 0.99 | 0.91 | Jan, Dec, Feb | 4.7 °C | 126 mm |

The closest square on all factors is `m_38.25_92.25` (Qaidam Basin), with a score of 0.690.
There, Mars is 84.2 °C colder in the yearly mean.
The square gets 1.27 times 25 mm of precipitation a year.
Mars air pressure is 1.19 % of the square's.

### Pathfinder

Caveats: it is not a climate match, and a score is a position on each factor's own scale, not a share of likeness.

**Closest by landscape (slopes and bare ground)**

1,087 ranked squares tie at the top score of 1.000, so their order here is not a ranking. Tied squares are listed by bare area, then by environment score.

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_15.75_46.25` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.04 | 1.00 | 0.88 | Jan, Dec, Feb | 26.6 °C | 21 mm |
| 2 | `m_15.75_28.25` | Sahara | 1.000 | 1.00 | 0.76 | 0.05 | 1.00 | 0.88 | Jan, Dec, Feb | 25.9 °C | 52 mm |
| 3 | `m_15.75_11.25` | Sahara | 1.000 | 1.00 | 0.56 | 0.03 | 1.00 | 0.88 | Jan, Dec, Feb | 27.3 °C | 94 mm |
| 4 | `m_16.25_24.25` | Sahara | 1.000 | 1.00 | 0.96 | 0.07 | 1.00 | 0.89 | Jan, Dec, Feb | 24.0 °C | 28 mm |
| 5 | `m_17.25_31.25` | Sahara | 1.000 | 1.00 | 0.96 | 0.02 | 1.00 | 0.91 | Jan, Dec, Feb | 28.3 °C | 28 mm |
| 6 | `m_17.75_20.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.04 | 1.00 | 0.93 | Jan, Dec, Feb | 26.9 °C | 15 mm |
| 7 | `m_17.75_48.25` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.03 | 1.00 | 0.93 | Jan, Dec, Feb | 27.8 °C | 21 mm |
| 8 | `m_18.25_26.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.06 | 1.00 | 0.94 | Jan, Dec, Feb | 24.6 °C | 4 mm |
| 9 | `m_18.25_9.75` | Sahara | 1.000 | 1.00 | 0.90 | 0.04 | 1.00 | 0.94 | Jan, Dec, Feb | 26.3 °C | 34 mm |
| 10 | `m_18.25_17.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.03 | 1.00 | 0.94 | Jan, Dec, Feb | 27.5 °C | 9 mm |

**Closest by environment (dry, cold and bare)**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.704 | 0.51 | 0.80 | 0.43 | 1.00 | 0.71 | Mar, Apr, Sep | -7.3 °C | 45 mm |
| 2 | `m_38.75_93.75` | Qaidam Basin | 0.673 | 0.38 | 0.90 | 0.34 | 1.00 | 0.66 | Mar, Apr, May | 0.9 °C | 34 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.665 | 0.67 | 0.65 | 0.46 | 1.00 | 0.73 | Mar, Oct, Apr | -9.3 °C | 72 mm |
| 4 | `m_-77.75_164.25` | McMurdo Dry Valleys | 0.660 | 0.10 | 0.61 | 0.57 | 0.83 | 0.00 | none | -18.9 °C | 80 mm |
| 5 | `m_37.75_89.25` | Tibetan Plateau | 0.653 | 0.53 | 0.75 | 0.37 | 0.99 | 0.68 | Mar, Apr, Sep | -2.0 °C | 52 mm |
| 6 | `m_34.75_83.25` | Tibetan Plateau | 0.642 | 0.41 | 0.64 | 0.42 | 0.99 | 0.75 | Mar, Oct, Apr | -5.8 °C | 73 mm |
| 7 | `m_38.25_74.25` | Pamir and Karakoram | 0.630 | 0.31 | 0.66 | 0.39 | 0.97 | 0.67 | Mar, Sep, Apr | -3.7 °C | 70 mm |
| 8 | `m_81.25_-72.25` | Ellesmere or north-west Greenland | 0.612 | 0.19 | 0.45 | 0.55 | 0.92 | 0.00 | none | -17.4 °C | 129 mm |
| 9 | `m_-25.25_-69.25` | Altiplano and Puna | 0.608 | 0.26 | 1.00 | 0.23 | 1.00 | 0.96 | Aug, May, Sep | 10.6 °C | 19 mm |
| 10 | `m_-72.25_68.75` | Antarctica | 0.607 | 0.11 | 0.73 | 0.60 | 0.52 | 0.00 | none | -21.3 °C | 57 mm |

**Closest on all five factors**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_38.25_93.25` | Qaidam Basin | 0.717 | 1.00 | 0.94 | 0.30 | 1.00 | 0.67 | Mar, Apr, May | 4.0 °C | 30 mm |
| 2 | `m_35.25_85.25` | Tibetan Plateau | 0.693 | 0.75 | 0.69 | 0.42 | 0.99 | 0.73 | Mar, Oct, Apr | -5.9 °C | 63 mm |
| 3 | `m_-23.25_-68.25` | Atacama Desert | 0.683 | 0.83 | 0.94 | 0.19 | 1.00 | 1.00 | Aug, May, Sep | 13.6 °C | 30 mm |
| 4 | `m_34.75_79.25` | Tibetan Plateau | 0.682 | 0.77 | 0.58 | 0.44 | 1.00 | 0.75 | Oct, Mar, Apr | -7.9 °C | 88 mm |
| 5 | `m_37.25_89.75` | Tibetan Plateau | 0.681 | 0.80 | 0.71 | 0.38 | 1.00 | 0.69 | Mar, Apr, Sep | -2.3 °C | 59 mm |
| 6 | `m_-20.25_-69.75` | Atacama Desert | 0.646 | 0.83 | 1.00 | 0.14 | 0.97 | 0.98 | Jul, Aug, Jun | 17.9 °C | 11 mm |
| 7 | `m_38.75_86.75` | Taklamakan and Tarim Basin | 0.644 | 1.00 | 0.87 | 0.20 | 0.98 | 0.66 | Mar, Apr, Sep | 13.1 °C | 37 mm |
| 8 | `m_41.75_101.75` | Gobi Desert | 0.638 | 1.00 | 0.77 | 0.24 | 1.00 | 0.59 | Mar, Apr, May | 9.8 °C | 50 mm |
| 9 | `m_24.75_26.75` | Sahara | 0.637 | 1.00 | 1.00 | 0.11 | 1.00 | 0.97 | Feb, Nov, Mar | 20.7 °C | 4 mm |
| 10 | `m_23.25_12.25` | Sahara | 0.630 | 1.00 | 1.00 | 0.10 | 1.00 | 1.00 | Jan, Feb, Nov | 21.5 °C | 20 mm |

The closest square on all factors is `m_38.25_93.25` (Qaidam Basin), with a score of 0.717.
There, Mars is 59.8 °C colder in the yearly mean.
The square gets 1.20 times 25 mm of precipitation a year.
Mars air pressure is 1.10 % of the square's.

### Spirit

Caveats: it is not a climate match, and a score is a position on each factor's own scale, not a share of likeness.

**Closest by landscape (slopes and bare ground)**

595 ranked squares tie at the top score of 1.000, so their order here is not a ranking. Tied squares are listed by bare area, then by environment score.

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_15.75_47.25` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.04 | 1.00 | 0.99 | Jan, Dec, Feb | 26.6 °C | 17 mm |
| 2 | `m_16.25_24.25` | Sahara | 1.000 | 1.00 | 0.96 | 0.06 | 1.00 | 1.00 | Jan, Dec, Feb | 24.0 °C | 28 mm |
| 3 | `m_16.25_27.25` | Sahara | 1.000 | 1.00 | 0.87 | 0.05 | 1.00 | 1.00 | Jan, Dec, Feb | 25.0 °C | 37 mm |
| 4 | `m_16.75_30.25` | Sahara | 1.000 | 1.00 | 0.84 | 0.03 | 1.00 | 1.00 | Jan, Feb, Nov | 27.1 °C | 40 mm |
| 5 | `m_17.25_44.75` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.05 | 1.00 | 1.00 | Jan, Feb, Nov | 25.7 °C | 18 mm |
| 6 | `m_17.75_21.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.04 | 1.00 | 1.00 | Jan, Feb, Nov | 26.4 °C | 19 mm |
| 7 | `m_17.75_9.75` | Sahara | 1.000 | 1.00 | 0.78 | 0.04 | 1.00 | 1.00 | Jan, Feb, Nov | 26.5 °C | 48 mm |
| 8 | `m_17.75_18.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.02 | 1.00 | 1.00 | Jan, Feb, Nov | 27.7 °C | 7 mm |
| 9 | `m_18.25_32.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.01 | 1.00 | 1.00 | Jan, Feb, Nov | 28.6 °C | 13 mm |
| 10 | `m_18.25_-8.25` | Sahara | 1.000 | 1.00 | 0.48 | 0.03 | 1.00 | 1.00 | Jan, Feb, Nov | 27.3 °C | 117 mm |

**Closest by environment (dry, cold and bare)**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.684 | 0.66 | 0.80 | 0.40 | 1.00 | 0.68 | Mar, Apr, Sep | -7.3 °C | 45 mm |
| 2 | `m_38.75_93.75` | Qaidam Basin | 0.654 | 0.57 | 0.90 | 0.31 | 1.00 | 0.61 | Apr, May, Sep | 0.9 °C | 34 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.646 | 0.87 | 0.65 | 0.42 | 1.00 | 0.70 | Mar, Apr, Sep | -9.3 °C | 72 mm |
| 4 | `m_-77.75_164.25` | McMurdo Dry Valleys | 0.641 | 0.28 | 0.61 | 0.52 | 0.83 | 0.00 | none | -18.9 °C | 80 mm |
| 5 | `m_37.75_89.25` | Tibetan Plateau | 0.634 | 0.68 | 0.75 | 0.34 | 0.99 | 0.64 | Apr, Sep, May | -2.0 °C | 52 mm |
| 6 | `m_34.75_83.25` | Tibetan Plateau | 0.624 | 0.62 | 0.64 | 0.38 | 0.99 | 0.72 | Mar, Apr, May | -5.8 °C | 73 mm |
| 7 | `m_38.25_74.25` | Pamir and Karakoram | 0.612 | 0.50 | 0.66 | 0.36 | 0.97 | 0.63 | Sep, Apr, May | -3.7 °C | 70 mm |
| 8 | `m_81.25_-72.25` | Ellesmere or north-west Greenland | 0.595 | 0.38 | 0.45 | 0.51 | 0.92 | 0.00 | none | -17.4 °C | 129 mm |
| 9 | `m_-25.25_-69.25` | Altiplano and Puna | 0.591 | 0.46 | 1.00 | 0.21 | 1.00 | 0.95 | Aug, Sep, Apr | 10.6 °C | 19 mm |
| 10 | `m_-72.25_68.75` | Antarctica | 0.590 | 0.30 | 0.73 | 0.55 | 0.52 | 0.00 | none | -21.3 °C | 57 mm |

**Closest on all five factors**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_35.25_84.75` | Tibetan Plateau | 0.700 | 0.90 | 0.69 | 0.38 | 1.00 | 0.70 | Mar, Apr, Sep | -5.9 °C | 63 mm |
| 2 | `m_38.75_92.75` | Qaidam Basin | 0.698 | 1.00 | 0.91 | 0.29 | 1.00 | 0.61 | Apr, May, Sep | 2.4 °C | 32 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.697 | 0.87 | 0.65 | 0.42 | 1.00 | 0.70 | Mar, Apr, Sep | -9.3 °C | 72 mm |
| 4 | `m_37.25_88.25` | Tibetan Plateau | 0.690 | 0.78 | 0.79 | 0.39 | 0.99 | 0.65 | Mar, Apr, Sep | -6.7 °C | 47 mm |
| 5 | `m_-23.25_-68.25` | Atacama Desert | 0.684 | 0.91 | 0.94 | 0.18 | 1.00 | 1.00 | Aug, Sep, Apr | 13.6 °C | 30 mm |
| 6 | `m_-20.25_-69.75` | Atacama Desert | 0.661 | 1.00 | 1.00 | 0.13 | 0.97 | 1.00 | Aug, Sep, Oct | 17.9 °C | 11 mm |
| 7 | `m_32.75_82.75` | Tibetan Plateau | 0.634 | 0.72 | 0.56 | 0.33 | 0.99 | 0.77 | Mar, Apr, May | -1.0 °C | 93 mm |
| 8 | `m_23.25_26.25` | Sahara | 0.631 | 0.96 | 1.00 | 0.10 | 1.00 | 1.00 | Feb, Mar, Oct | 20.2 °C | 2 mm |
| 9 | `m_23.75_11.75` | Sahara | 0.625 | 1.00 | 1.00 | 0.10 | 1.00 | 0.99 | Feb, Mar, Oct | 21.0 °C | 20 mm |
| 10 | `m_-26.25_-69.25` | Atacama Desert | 0.625 | 0.55 | 0.87 | 0.21 | 1.00 | 0.93 | Sep, Oct, Apr | 9.9 °C | 37 mm |

The closest square on all factors is `m_35.25_84.75` (Tibetan Plateau), with a score of 0.700.
There, Mars is 57.7 °C colder in the yearly mean.
The square gets 2.50 times 25 mm of precipitation a year.
Mars air pressure is 1.23 % of the square's.

### Opportunity

Caveats: it is not a climate match, and a score is a position on each factor's own scale, not a share of likeness.

**Closest by landscape (slopes and bare ground)**

889 ranked squares tie at the top score of 1.000, so their order here is not a ranking. Tied squares are listed by bare area, then by environment score.

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_15.75_27.75` | Sahara | 1.000 | 1.00 | 0.78 | 0.06 | 1.00 | 1.00 | Mar, Apr, Oct | 24.8 °C | 48 mm |
| 2 | `m_15.75_47.25` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.04 | 1.00 | 1.00 | Oct, Mar, Apr | 26.6 °C | 17 mm |
| 3 | `m_16.25_24.25` | Sahara | 1.000 | 1.00 | 0.96 | 0.07 | 1.00 | 1.00 | Mar, Oct, Apr | 24.0 °C | 28 mm |
| 4 | `m_16.25_9.25` | Sahara | 1.000 | 1.00 | 0.48 | 0.04 | 1.00 | 1.00 | Mar, Oct, Apr | 26.4 °C | 119 mm |
| 5 | `m_16.25_31.25` | Sahara | 1.000 | 1.00 | 0.73 | 0.02 | 1.00 | 1.00 | Mar, Apr | 28.1 °C | 55 mm |
| 6 | `m_17.25_44.75` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.05 | 1.00 | 1.00 | Oct, Mar, Apr | 25.7 °C | 18 mm |
| 7 | `m_17.75_20.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.04 | 1.00 | 1.00 | Mar, Oct, Apr | 26.8 °C | 18 mm |
| 8 | `m_17.75_53.25` | Arabian Desert | 1.000 | 1.00 | 0.59 | 0.03 | 1.00 | 1.00 | Mar, Oct, Apr | 27.7 °C | 86 mm |
| 9 | `m_17.75_49.25` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.02 | 1.00 | 1.00 | Mar, Oct | 28.7 °C | 14 mm |
| 10 | `m_18.25_29.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.04 | 1.00 | 1.00 | Mar, Apr, Oct | 26.8 °C | 6 mm |

**Closest by environment (dry, cold and bare)**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.708 | 0.54 | 0.80 | 0.44 | 1.00 | 0.53 | Apr, May, Aug | -7.3 °C | 45 mm |
| 2 | `m_38.75_93.75` | Qaidam Basin | 0.676 | 0.36 | 0.90 | 0.34 | 1.00 | 0.44 | May, Aug, Jun | 0.9 °C | 34 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.669 | 0.65 | 0.65 | 0.47 | 1.00 | 0.56 | Apr, May, Jul | -9.3 °C | 72 mm |
| 4 | `m_-77.75_164.25` | McMurdo Dry Valleys | 0.663 | 0.12 | 0.61 | 0.58 | 0.83 | 0.00 | none | -18.9 °C | 80 mm |
| 5 | `m_37.75_89.25` | Tibetan Plateau | 0.656 | 0.45 | 0.75 | 0.38 | 0.99 | 0.47 | May, Aug, Jun | -2.0 °C | 52 mm |
| 6 | `m_34.75_83.25` | Tibetan Plateau | 0.646 | 0.45 | 0.64 | 0.42 | 0.99 | 0.58 | Apr, May, Jun | -5.8 °C | 73 mm |
| 7 | `m_38.25_74.25` | Pamir and Karakoram | 0.633 | 0.30 | 0.66 | 0.40 | 0.97 | 0.45 | May, Aug, Jun | -3.7 °C | 70 mm |
| 8 | `m_81.25_-72.25` | Ellesmere or north-west Greenland | 0.615 | 0.18 | 0.45 | 0.56 | 0.92 | 0.00 | none | -17.4 °C | 129 mm |
| 9 | `m_-25.25_-69.25` | Altiplano and Puna | 0.612 | 0.25 | 1.00 | 0.23 | 1.00 | 0.93 | Oct, Nov, Mar | 10.6 °C | 19 mm |
| 10 | `m_-72.25_68.75` | Antarctica | 0.611 | 0.13 | 0.73 | 0.61 | 0.52 | 0.00 | none | -21.3 °C | 57 mm |

**Closest on all five factors**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_38.25_93.25` | Qaidam Basin | 0.665 | 0.99 | 0.94 | 0.31 | 1.00 | 0.45 | May, Aug, Jun | 4.0 °C | 30 mm |
| 2 | `m_-23.25_-68.25` | Atacama Desert | 0.664 | 0.71 | 0.94 | 0.19 | 1.00 | 1.00 | Sep, Oct, Nov | 13.6 °C | 30 mm |
| 3 | `m_35.25_85.25` | Tibetan Plateau | 0.662 | 0.77 | 0.69 | 0.42 | 0.99 | 0.56 | Apr, May, Aug | -5.9 °C | 63 mm |
| 4 | `m_34.75_79.25` | Tibetan Plateau | 0.655 | 0.80 | 0.58 | 0.45 | 1.00 | 0.58 | Apr, May, Jun | -7.9 °C | 88 mm |
| 5 | `m_37.25_89.75` | Tibetan Plateau | 0.651 | 0.87 | 0.71 | 0.38 | 1.00 | 0.49 | May, Aug, Jun | -2.3 °C | 59 mm |
| 6 | `m_-20.25_-69.75` | Atacama Desert | 0.648 | 0.82 | 1.00 | 0.14 | 0.97 | 1.00 | Sep, Oct, Nov | 17.9 °C | 11 mm |
| 7 | `m_24.25_26.75` | Sahara | 0.642 | 1.00 | 1.00 | 0.11 | 1.00 | 0.97 | Mar, Apr, May | 20.5 °C | 3 mm |
| 8 | `m_23.75_11.75` | Sahara | 0.637 | 1.00 | 1.00 | 0.11 | 1.00 | 0.99 | Mar, Apr, Sep | 21.0 °C | 20 mm |
| 9 | `m_23.75_21.75` | Sahara | 0.626 | 1.00 | 1.00 | 0.10 | 1.00 | 0.99 | Mar, Apr, May | 21.8 °C | 2 mm |
| 10 | `m_27.75_40.25` | Arabian Desert | 0.622 | 1.00 | 0.99 | 0.11 | 1.00 | 0.84 | Apr, May, Sep | 20.6 °C | 26 mm |

The closest square on all factors is `m_38.25_93.25` (Qaidam Basin), with a score of 0.665.
There, Mars is 58.5 °C colder in the yearly mean.
The square gets 1.20 times 25 mm of precipitation a year.
Mars air pressure is 0.88 % of the square's.

### InSight

Caveats: it is not a climate match, and a score is a position on each factor's own scale, not a share of likeness.

**Closest by landscape (slopes and bare ground)**

711 ranked squares tie at the top score of 1.000, so their order here is not a ranking. Tied squares are listed by bare area, then by environment score.

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_15.75_46.25` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.04 | 1.00 | 1.00 | Feb, Oct, Mar | 26.6 °C | 21 mm |
| 2 | `m_16.25_23.75` | Sahara | 1.000 | 1.00 | 0.86 | 0.07 | 1.00 | 1.00 | Feb, Mar, Oct | 23.7 °C | 38 mm |
| 3 | `m_16.25_9.75` | Sahara | 1.000 | 1.00 | 0.57 | 0.04 | 1.00 | 1.00 | Feb, Mar, Oct | 26.4 °C | 91 mm |
| 4 | `m_16.25_18.75` | Sahara | 1.000 | 1.00 | 0.75 | 0.02 | 1.00 | 1.00 | Feb, Mar, Oct | 28.0 °C | 53 mm |
| 5 | `m_16.75_29.75` | Sahara | 1.000 | 1.00 | 0.84 | 0.03 | 1.00 | 1.00 | Feb, Mar, Apr | 27.1 °C | 40 mm |
| 6 | `m_17.25_26.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.05 | 1.00 | 1.00 | Mar, Apr, Oct | 25.7 °C | 12 mm |
| 7 | `m_17.25_32.75` | Sahara | 1.000 | 1.00 | 0.85 | 0.01 | 1.00 | 1.00 | Mar | 29.0 °C | 39 mm |
| 8 | `m_17.75_48.25` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.02 | 1.00 | 1.00 | Oct, Mar, Apr | 27.8 °C | 21 mm |
| 9 | `m_18.25_21.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.05 | 1.00 | 1.00 | Mar, Oct, Apr | 25.8 °C | 10 mm |
| 10 | `m_18.25_12.75` | Sahara | 1.000 | 1.00 | 0.94 | 0.04 | 1.00 | 1.00 | Mar, Oct, Apr | 26.9 °C | 30 mm |

**Closest by environment (dry, cold and bare)**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.698 | 0.40 | 0.80 | 0.42 | 1.00 | 0.57 | Apr, May, Aug | -7.3 °C | 45 mm |
| 2 | `m_38.75_93.75` | Qaidam Basin | 0.667 | 0.31 | 0.90 | 0.33 | 1.00 | 0.48 | Apr, May, Aug | 0.9 °C | 34 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.659 | 0.56 | 0.65 | 0.45 | 1.00 | 0.60 | Apr, May, Jul | -9.3 °C | 72 mm |
| 4 | `m_-77.75_164.25` | McMurdo Dry Valleys | 0.654 | 0.10 | 0.61 | 0.55 | 0.83 | 0.00 | none | -18.9 °C | 80 mm |
| 5 | `m_37.75_89.25` | Tibetan Plateau | 0.647 | 0.46 | 0.75 | 0.36 | 0.99 | 0.52 | Apr, May, Aug | -2.0 °C | 52 mm |
| 6 | `m_34.75_83.25` | Tibetan Plateau | 0.637 | 0.32 | 0.64 | 0.41 | 0.99 | 0.62 | Apr, May, Jun | -5.8 °C | 73 mm |
| 7 | `m_38.25_74.25` | Pamir and Karakoram | 0.624 | 0.28 | 0.66 | 0.38 | 0.97 | 0.50 | Apr, May, Aug | -3.7 °C | 70 mm |
| 8 | `m_81.25_-72.25` | Ellesmere or north-west Greenland | 0.607 | 0.16 | 0.45 | 0.54 | 0.92 | 0.00 | none | -17.4 °C | 129 mm |
| 9 | `m_-25.25_-69.25` | Altiplano and Puna | 0.603 | 0.23 | 1.00 | 0.22 | 1.00 | 0.94 | Sep, Oct, Nov | 10.6 °C | 19 mm |
| 10 | `m_-72.25_68.75` | Antarctica | 0.602 | 0.11 | 0.73 | 0.58 | 0.52 | 0.00 | none | -21.3 °C | 57 mm |

**Closest on all five factors**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_38.25_92.25` | Qaidam Basin | 0.670 | 1.00 | 0.92 | 0.29 | 1.00 | 0.50 | Apr, May, Aug | 4.2 °C | 32 mm |
| 2 | `m_-23.25_-68.25` | Atacama Desert | 0.666 | 0.75 | 0.94 | 0.19 | 1.00 | 1.00 | Sep, Oct, Nov | 13.6 °C | 30 mm |
| 3 | `m_35.25_84.75` | Tibetan Plateau | 0.636 | 0.61 | 0.69 | 0.41 | 1.00 | 0.60 | Apr, May, Aug | -5.9 °C | 63 mm |
| 4 | `m_34.75_79.25` | Tibetan Plateau | 0.632 | 0.66 | 0.58 | 0.43 | 1.00 | 0.62 | Apr, May, Jun | -7.9 °C | 88 mm |
| 5 | `m_25.25_26.25` | Sahara | 0.627 | 1.00 | 1.00 | 0.10 | 1.00 | 0.94 | Mar, Apr, May | 20.9 °C | 4 mm |
| 6 | `m_24.25_12.75` | Sahara | 0.626 | 0.98 | 1.00 | 0.10 | 1.00 | 0.97 | Mar, Apr, Sep | 21.1 °C | 24 mm |
| 7 | `m_-20.25_-69.75` | Atacama Desert | 0.625 | 0.71 | 1.00 | 0.14 | 0.97 | 1.00 | Sep, Oct, Nov | 17.9 °C | 11 mm |
| 8 | `m_23.75_21.75` | Sahara | 0.621 | 1.00 | 1.00 | 0.09 | 1.00 | 0.99 | Mar, Apr, May | 21.8 °C | 2 mm |
| 9 | `m_27.75_39.75` | Arabian Desert | 0.618 | 1.00 | 0.99 | 0.11 | 1.00 | 0.85 | Apr, May, Sep | 20.6 °C | 26 mm |
| 10 | `m_23.75_9.75` | Sahara | 0.616 | 1.00 | 1.00 | 0.09 | 1.00 | 0.99 | Mar, Apr, Sep | 22.1 °C | 24 mm |

The closest square on all factors is `m_38.25_92.25` (Qaidam Basin), with a score of 0.670.
There, Mars is 62.4 °C colder in the yearly mean.
The square gets 1.27 times 25 mm of precipitation a year.
Mars air pressure is 0.99 % of the square's.

### Phlegra Montes

Caveats: it is not a climate match, and a score is a position on each factor's own scale, not a share of likeness.

**Closest by landscape (slopes and bare ground)**

102 ranked squares tie at the top score of 1.000, so their order here is not a ranking. Tied squares are listed by bare area, then by environment score.

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_12.75_41.25` | Danakil Depression | 1.000 | 1.00 | 0.21 | 0.00 | 1.00 | 0.52 | Jan, Dec, Feb | 33.1 °C | 266 mm |
| 2 | `m_15.75_50.75` | Arabian Desert | 1.000 | 1.00 | 0.94 | 0.04 | 1.00 | 0.58 | Jan, Dec, Feb | 25.8 °C | 30 mm |
| 3 | `m_15.75_47.75` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.03 | 1.00 | 0.58 | Jan, Dec, Feb | 26.6 °C | 17 mm |
| 4 | `m_19.25_8.75` | Sahara | 1.000 | 1.00 | 0.89 | 0.06 | 1.00 | 0.65 | Jan, Dec, Feb | 24.1 °C | 34 mm |
| 5 | `m_19.75_18.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.08 | 1.00 | 0.66 | Jan, Dec, Feb | 21.9 °C | 14 mm |
| 6 | `m_20.25_36.75` | Sahara | 1.000 | 1.00 | 0.83 | 0.03 | 1.00 | 0.67 | Feb, Jan, Mar | 27.4 °C | 42 mm |
| 7 | `m_20.25_-13.25` | Sahara | 1.000 | 1.00 | 0.30 | 0.02 | 1.00 | 0.67 | Jan, Dec, Feb | 27.5 °C | 204 mm |
| 8 | `m_-21.25_-69.75` | Atacama Desert | 1.000 | 1.00 | 1.00 | 0.12 | 1.00 | 0.69 | Jul, Aug, Sep | 17.8 °C | 9 mm |
| 9 | `m_21.75_12.75` | Sahara | 1.000 | 1.00 | 0.89 | 0.05 | 1.00 | 0.70 | Jan, Dec, Feb | 24.7 °C | 35 mm |
| 10 | `m_-24.25_-69.75` | Atacama Desert | 1.000 | 1.00 | 1.00 | 0.13 | 1.00 | 0.75 | Jul, Jun, Aug | 17.1 °C | 8 mm |

**Closest by environment (dry, cold and bare)**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.665 | 0.84 | 0.80 | 0.37 | 1.00 | 0.93 | Jan, Dec, Feb | -7.3 °C | 45 mm |
| 2 | `m_38.75_93.75` | Qaidam Basin | 0.636 | 1.00 | 0.90 | 0.29 | 1.00 | 0.90 | Jan, Feb, Nov | 0.9 °C | 34 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.629 | 1.00 | 0.65 | 0.39 | 1.00 | 0.93 | Dec, Jan, Nov | -9.3 °C | 72 mm |
| 4 | `m_-77.75_164.25` | McMurdo Dry Valleys | 0.624 | 0.77 | 0.61 | 0.48 | 0.83 | 0.12 | Nov, Dec, Jan | -18.9 °C | 80 mm |
| 5 | `m_37.75_89.25` | Tibetan Plateau | 0.617 | 1.00 | 0.75 | 0.31 | 0.99 | 0.92 | Jan, Feb, Nov | -2.0 °C | 52 mm |
| 6 | `m_34.75_83.25` | Tibetan Plateau | 0.607 | 0.94 | 0.64 | 0.35 | 0.99 | 0.93 | Jan, Dec, Feb | -5.8 °C | 73 mm |
| 7 | `m_38.25_74.25` | Pamir and Karakoram | 0.595 | 1.00 | 0.66 | 0.33 | 0.97 | 0.91 | Jan, Nov, Feb | -3.7 °C | 70 mm |
| 8 | `m_81.25_-72.25` | Ellesmere or north-west Greenland | 0.579 | 0.93 | 0.45 | 0.47 | 0.92 | 0.05 | Jun, Jul | -17.4 °C | 129 mm |
| 9 | `m_-25.25_-69.25` | Altiplano and Puna | 0.575 | 0.96 | 1.00 | 0.19 | 1.00 | 0.77 | Jul, Jun, Aug | 10.6 °C | 19 mm |
| 10 | `m_-72.25_68.75` | Antarctica | 0.574 | 0.79 | 0.73 | 0.50 | 0.52 | 0.23 | Feb, Jan, Dec | -21.3 °C | 57 mm |

**Closest on all five factors**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_37.25_88.25` | Tibetan Plateau | 0.764 | 1.00 | 0.79 | 0.36 | 0.99 | 0.93 | Jan, Feb, Nov | -6.7 °C | 47 mm |
| 2 | `m_36.25_84.25` | Tibetan Plateau | 0.749 | 1.00 | 0.72 | 0.35 | 1.00 | 0.93 | Jan, Dec, Feb | -5.5 °C | 57 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.746 | 1.00 | 0.65 | 0.39 | 1.00 | 0.93 | Dec, Jan, Nov | -9.3 °C | 72 mm |
| 4 | `m_38.75_93.75` | Qaidam Basin | 0.745 | 1.00 | 0.90 | 0.29 | 1.00 | 0.90 | Jan, Feb, Nov | 0.9 °C | 34 mm |
| 5 | `m_38.25_74.25` | Pamir and Karakoram | 0.718 | 1.00 | 0.66 | 0.33 | 0.97 | 0.91 | Jan, Nov, Feb | -3.7 °C | 70 mm |
| 6 | `m_33.25_82.75` | Tibetan Plateau | 0.713 | 1.00 | 0.59 | 0.34 | 0.99 | 0.93 | Dec, Jan, Nov | -4.6 °C | 86 mm |
| 7 | `m_41.25_89.25` | Taklamakan and Tarim Basin | 0.675 | 0.94 | 0.89 | 0.20 | 1.00 | 0.85 | Feb, Nov, Mar | 9.8 °C | 35 mm |
| 8 | `m_-25.25_-69.25` | Altiplano and Puna | 0.674 | 0.96 | 1.00 | 0.19 | 1.00 | 0.77 | Jul, Jun, Aug | 10.6 °C | 19 mm |
| 9 | `m_32.25_79.75` | Tibetan Plateau | 0.670 | 1.00 | 0.57 | 0.33 | 0.80 | 0.91 | Dec, Nov, Jan | -3.2 °C | 91 mm |
| 10 | `m_-22.25_-68.25` | Altiplano and Puna | 0.668 | 1.00 | 0.83 | 0.25 | 0.90 | 0.71 | Jul, Jun, Aug | 4.4 °C | 42 mm |

The closest square on all factors is `m_37.25_88.25` (Tibetan Plateau), with a score of 0.764.
There, Mars is 65.0 °C colder in the yearly mean.
The square gets 1.88 times 25 mm of precipitation a year.
Mars air pressure is 1.34 % of the square's.

### AP-1 (Arcadia Planitia)

Caveats: it is not a climate match, and a score is a position on each factor's own scale, not a share of likeness.

**Closest by landscape (slopes and bare ground)**

250 ranked squares tie at the top score of 1.000, so their order here is not a ranking. Tied squares are listed by bare area, then by environment score.

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_16.25_9.75` | Sahara | 1.000 | 1.00 | 0.57 | 0.03 | 1.00 | 0.50 | Jan, Dec, Feb | 26.4 °C | 91 mm |
| 2 | `m_17.25_26.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.04 | 1.00 | 0.52 | Jan, Dec, Feb | 25.7 °C | 12 mm |
| 3 | `m_17.75_20.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.03 | 1.00 | 0.53 | Jan, Dec, Feb | 26.9 °C | 15 mm |
| 4 | `m_17.75_29.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.02 | 1.00 | 0.53 | Jan, Dec, Feb | 27.4 °C | 11 mm |
| 5 | `m_18.75_-0.25` | Sahara | 1.000 | 1.00 | 0.52 | 0.02 | 1.00 | 0.55 | Jan, Dec, Feb | 28.4 °C | 104 mm |
| 6 | `m_18.75_53.25` | Arabian Desert | 1.000 | 1.00 | 0.75 | 0.01 | 1.00 | 0.55 | Jan, Dec, Feb | 29.0 °C | 53 mm |
| 7 | `m_19.25_15.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.03 | 1.00 | 0.56 | Jan, Dec, Feb | 26.9 °C | 12 mm |
| 8 | `m_19.25_-13.25` | Sahara | 1.000 | 1.00 | 0.41 | 0.01 | 1.00 | 0.56 | Jan, Dec, Feb | 28.9 °C | 147 mm |
| 9 | `m_19.75_24.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.07 | 1.00 | 0.57 | Jan, Dec, Feb | 23.0 °C | 7 mm |
| 10 | `m_20.25_6.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.03 | 1.00 | 0.58 | Jan, Dec, Feb | 27.3 °C | 22 mm |

**Closest by environment (dry, cold and bare)**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.659 | 0.28 | 0.80 | 0.36 | 1.00 | 0.89 | Jan, Dec, Feb | -7.3 °C | 45 mm |
| 2 | `m_38.75_93.75` | Qaidam Basin | 0.630 | 0.16 | 0.90 | 0.28 | 1.00 | 0.93 | Jan, Dec, Feb | 0.9 °C | 34 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.623 | 0.40 | 0.65 | 0.38 | 1.00 | 0.88 | Dec, Jan, Nov | -9.3 °C | 72 mm |
| 4 | `m_-77.75_164.25` | McMurdo Dry Valleys | 0.618 | 0.01 | 0.61 | 0.47 | 0.83 | 0.21 | Nov, Dec, Jan | -18.9 °C | 80 mm |
| 5 | `m_37.75_89.25` | Tibetan Plateau | 0.611 | 0.29 | 0.75 | 0.31 | 0.99 | 0.92 | Jan, Dec, Feb | -2.0 °C | 52 mm |
| 6 | `m_34.75_83.25` | Tibetan Plateau | 0.602 | 0.19 | 0.64 | 0.34 | 0.99 | 0.86 | Jan, Dec, Feb | -5.8 °C | 73 mm |
| 7 | `m_38.25_74.25` | Pamir and Karakoram | 0.590 | 0.15 | 0.66 | 0.32 | 0.97 | 0.93 | Dec, Jan, Nov | -3.7 °C | 70 mm |
| 8 | `m_81.25_-72.25` | Ellesmere or north-west Greenland | 0.573 | 0.05 | 0.45 | 0.45 | 0.92 | 0.14 | May, Jun, Jul | -17.4 °C | 129 mm |
| 9 | `m_-25.25_-69.25` | Altiplano and Puna | 0.570 | 0.09 | 1.00 | 0.19 | 1.00 | 0.68 | Jul, Jun, Aug | 10.6 °C | 19 mm |
| 10 | `m_-72.25_68.75` | Antarctica | 0.569 | 0.00 | 0.73 | 0.49 | 0.52 | 0.32 | Oct, Feb, Jan | -21.3 °C | 57 mm |

**Closest on all five factors**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_38.25_92.25` | Qaidam Basin | 0.725 | 0.95 | 0.92 | 0.25 | 1.00 | 0.93 | Jan, Dec, Feb | 4.2 °C | 32 mm |
| 2 | `m_41.75_101.75` | Gobi Desert | 0.671 | 0.99 | 0.77 | 0.19 | 1.00 | 0.93 | Jan, Feb, Nov | 9.8 °C | 50 mm |
| 3 | `m_39.25_86.25` | Taklamakan and Tarim Basin | 0.662 | 1.00 | 0.84 | 0.16 | 1.00 | 0.93 | Jan, Dec, Feb | 13.1 °C | 40 mm |
| 4 | `m_37.75_82.75` | Taklamakan and Tarim Basin | 0.634 | 0.98 | 0.72 | 0.16 | 0.98 | 0.92 | Jan, Dec, Feb | 13.2 °C | 58 mm |
| 5 | `m_35.25_85.25` | Tibetan Plateau | 0.634 | 0.49 | 0.69 | 0.34 | 0.99 | 0.88 | Jan, Dec, Feb | -5.9 °C | 63 mm |
| 6 | `m_38.75_79.25` | Taklamakan and Tarim Basin | 0.624 | 1.00 | 0.64 | 0.16 | 1.00 | 0.93 | Jan, Dec, Feb | 13.4 °C | 73 mm |
| 7 | `m_41.25_91.25` | Taklamakan and Tarim Basin | 0.624 | 0.62 | 0.92 | 0.18 | 1.00 | 0.93 | Jan, Dec, Feb | 11.6 °C | 32 mm |
| 8 | `m_41.75_62.25` | Karakum and Kyzylkum | 0.621 | 0.96 | 0.68 | 0.15 | 1.00 | 0.93 | Jan, Nov, Oct | 14.0 °C | 66 mm |
| 9 | `m_34.75_79.25` | Tibetan Plateau | 0.617 | 0.49 | 0.58 | 0.36 | 1.00 | 0.86 | Dec, Jan, Nov | -7.9 °C | 88 mm |
| 10 | `m_42.75_57.25` | Karakum and Kyzylkum | 0.617 | 0.93 | 0.62 | 0.17 | 1.00 | 0.91 | Feb, Jan, Nov | 12.2 °C | 78 mm |

The closest square on all factors is `m_38.25_92.25` (Qaidam Basin), with a score of 0.725.
There, Mars is 78.7 °C colder in the yearly mean.
The square gets 1.27 times 25 mm of precipitation a year.
Mars air pressure is 1.12 % of the square's.

### AP-9 (Arcadia Planitia)

Caveats: it is not a climate match, and a score is a position on each factor's own scale, not a share of likeness.

**Closest by landscape (slopes and bare ground)**

599 ranked squares tie at the top score of 1.000, so their order here is not a ranking. Tied squares are listed by bare area, then by environment score.

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_15.75_46.25` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.03 | 1.00 | 0.48 | Jan, Dec, Feb | 26.6 °C | 21 mm |
| 2 | `m_15.75_28.25` | Sahara | 1.000 | 1.00 | 0.76 | 0.04 | 1.00 | 0.48 | Jan, Dec, Feb | 25.9 °C | 52 mm |
| 3 | `m_16.25_24.25` | Sahara | 1.000 | 1.00 | 0.96 | 0.06 | 1.00 | 0.49 | Jan, Dec, Feb | 24.0 °C | 28 mm |
| 4 | `m_16.25_9.75` | Sahara | 1.000 | 1.00 | 0.57 | 0.03 | 1.00 | 0.49 | Jan, Dec, Feb | 26.4 °C | 91 mm |
| 5 | `m_16.25_18.75` | Sahara | 1.000 | 1.00 | 0.75 | 0.02 | 1.00 | 0.49 | Jan, Dec, Feb | 28.0 °C | 53 mm |
| 6 | `m_17.25_32.25` | Sahara | 1.000 | 1.00 | 0.85 | 0.01 | 1.00 | 0.51 | Jan, Dec, Feb | 29.0 °C | 39 mm |
| 7 | `m_17.75_48.25` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.02 | 1.00 | 0.52 | Jan, Dec, Feb | 27.8 °C | 21 mm |
| 8 | `m_18.25_22.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.04 | 1.00 | 0.53 | Jan, Dec, Feb | 25.5 °C | 8 mm |
| 9 | `m_18.25_-8.25` | Sahara | 1.000 | 1.00 | 0.48 | 0.03 | 1.00 | 0.53 | Jan, Dec, Feb | 27.3 °C | 117 mm |
| 10 | `m_18.75_26.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.06 | 1.00 | 0.54 | Jan, Dec, Feb | 24.1 °C | 2 mm |

**Closest by environment (dry, cold and bare)**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.657 | 0.33 | 0.80 | 0.35 | 1.00 | 0.89 | Jan, Dec, Feb | -7.3 °C | 45 mm |
| 2 | `m_38.75_93.75` | Qaidam Basin | 0.628 | 0.21 | 0.90 | 0.28 | 1.00 | 0.93 | Jan, Dec, Feb | 0.9 °C | 34 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.621 | 0.47 | 0.65 | 0.37 | 1.00 | 0.87 | Dec, Jan, Nov | -9.3 °C | 72 mm |
| 4 | `m_-77.75_164.25` | McMurdo Dry Valleys | 0.616 | 0.01 | 0.61 | 0.46 | 0.83 | 0.22 | Nov, Dec, Jan | -18.9 °C | 80 mm |
| 5 | `m_37.75_89.25` | Tibetan Plateau | 0.610 | 0.35 | 0.75 | 0.30 | 0.99 | 0.92 | Jan, Dec, Feb | -2.0 °C | 52 mm |
| 6 | `m_34.75_83.25` | Tibetan Plateau | 0.600 | 0.24 | 0.64 | 0.34 | 0.99 | 0.86 | Jan, Dec, Feb | -5.8 °C | 73 mm |
| 7 | `m_38.25_74.25` | Pamir and Karakoram | 0.588 | 0.17 | 0.66 | 0.32 | 0.97 | 0.93 | Dec, Jan, Nov | -3.7 °C | 70 mm |
| 8 | `m_81.25_-72.25` | Ellesmere or north-west Greenland | 0.572 | 0.06 | 0.45 | 0.45 | 0.92 | 0.15 | May, Jun, Jul | -17.4 °C | 129 mm |
| 9 | `m_-25.25_-69.25` | Altiplano and Puna | 0.568 | 0.13 | 1.00 | 0.18 | 1.00 | 0.67 | Jul, Jun, Aug | 10.6 °C | 19 mm |
| 10 | `m_-72.25_68.75` | Antarctica | 0.567 | 0.01 | 0.73 | 0.49 | 0.52 | 0.33 | Oct, Feb, Jan | -21.3 °C | 57 mm |

**Closest on all five factors**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_38.25_92.25` | Qaidam Basin | 0.732 | 1.00 | 0.92 | 0.24 | 1.00 | 0.93 | Jan, Dec, Feb | 4.2 °C | 32 mm |
| 2 | `m_41.75_101.75` | Gobi Desert | 0.671 | 1.00 | 0.77 | 0.19 | 1.00 | 0.93 | Jan, Dec, Feb | 9.8 °C | 50 mm |
| 3 | `m_39.25_86.75` | Taklamakan and Tarim Basin | 0.662 | 1.00 | 0.86 | 0.16 | 1.00 | 0.93 | Jan, Dec, Feb | 13.3 °C | 38 mm |
| 4 | `m_35.25_85.25` | Tibetan Plateau | 0.650 | 0.57 | 0.69 | 0.34 | 0.99 | 0.87 | Jan, Dec, Feb | -5.9 °C | 63 mm |
| 5 | `m_38.25_83.25` | Taklamakan and Tarim Basin | 0.642 | 1.00 | 0.73 | 0.16 | 1.00 | 0.93 | Jan, Dec, Feb | 13.0 °C | 56 mm |
| 6 | `m_41.25_91.25` | Taklamakan and Tarim Basin | 0.635 | 0.69 | 0.92 | 0.17 | 1.00 | 0.93 | Jan, Dec, Feb | 11.6 °C | 32 mm |
| 7 | `m_34.75_79.25` | Tibetan Plateau | 0.633 | 0.57 | 0.58 | 0.36 | 1.00 | 0.86 | Dec, Jan, Nov | -7.9 °C | 88 mm |
| 8 | `m_42.75_57.25` | Karakum and Kyzylkum | 0.625 | 1.00 | 0.62 | 0.17 | 1.00 | 0.91 | Feb, Jan, Nov | 12.2 °C | 78 mm |
| 9 | `m_41.75_62.25` | Karakum and Kyzylkum | 0.625 | 1.00 | 0.68 | 0.15 | 1.00 | 0.93 | Jan, Dec, Nov | 14.0 °C | 66 mm |
| 10 | `m_38.75_79.25` | Taklamakan and Tarim Basin | 0.623 | 1.00 | 0.64 | 0.16 | 1.00 | 0.93 | Jan, Dec, Feb | 13.4 °C | 73 mm |

The closest square on all factors is `m_38.25_92.25` (Qaidam Basin), with a score of 0.732.
There, Mars is 79.6 °C colder in the yearly mean.
The square gets 1.27 times 25 mm of precipitation a year.
Mars air pressure is 1.12 % of the square's.

### EM-16 (Erebus Montes)

Caveats: it is not a climate match, and a score is a position on each factor's own scale, not a share of likeness.

**Closest by landscape (slopes and bare ground)**

262 ranked squares tie at the top score of 1.000, so their order here is not a ranking. Tied squares are listed by bare area, then by environment score.

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_15.75_47.25` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.03 | 1.00 | 0.49 | Jan, Dec, Feb | 26.6 °C | 17 mm |
| 2 | `m_16.75_29.25` | Sahara | 1.000 | 1.00 | 0.90 | 0.03 | 1.00 | 0.51 | Jan, Dec, Feb | 26.6 °C | 34 mm |
| 3 | `m_17.75_9.75` | Sahara | 1.000 | 1.00 | 0.78 | 0.03 | 1.00 | 0.53 | Jan, Dec, Feb | 26.5 °C | 48 mm |
| 4 | `m_17.75_18.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.02 | 1.00 | 0.53 | Jan, Dec, Feb | 27.7 °C | 7 mm |
| 5 | `m_18.25_23.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.06 | 1.00 | 0.54 | Jan, Dec, Feb | 23.4 °C | 4 mm |
| 6 | `m_18.25_-8.25` | Sahara | 1.000 | 1.00 | 0.48 | 0.03 | 1.00 | 0.54 | Jan, Dec, Feb | 27.3 °C | 117 mm |
| 7 | `m_19.25_26.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.06 | 1.00 | 0.56 | Jan, Dec, Feb | 23.5 °C | 2 mm |
| 8 | `m_19.25_45.75` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.03 | 1.00 | 0.56 | Jan, Dec, Feb | 26.6 °C | 12 mm |
| 9 | `m_19.25_15.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.03 | 1.00 | 0.56 | Jan, Dec, Feb | 26.8 °C | 12 mm |
| 10 | `m_19.75_21.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.05 | 1.00 | 0.57 | Jan, Dec, Feb | 24.5 °C | 5 mm |

**Closest by environment (dry, cold and bare)**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.657 | 0.53 | 0.80 | 0.35 | 1.00 | 0.89 | Jan, Dec, Feb | -7.3 °C | 45 mm |
| 2 | `m_38.75_93.75` | Qaidam Basin | 0.628 | 0.45 | 0.90 | 0.28 | 1.00 | 0.93 | Jan, Dec, Feb | 0.9 °C | 34 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.621 | 0.71 | 0.65 | 0.37 | 1.00 | 0.87 | Dec, Jan, Nov | -9.3 °C | 72 mm |
| 4 | `m_-77.75_164.25` | McMurdo Dry Valleys | 0.616 | 0.19 | 0.61 | 0.46 | 0.83 | 0.21 | Nov, Dec, Jan | -18.9 °C | 80 mm |
| 5 | `m_37.75_89.25` | Tibetan Plateau | 0.610 | 0.59 | 0.75 | 0.30 | 0.99 | 0.92 | Jan, Dec, Feb | -2.0 °C | 52 mm |
| 6 | `m_34.75_83.25` | Tibetan Plateau | 0.600 | 0.47 | 0.64 | 0.34 | 0.99 | 0.86 | Jan, Dec, Feb | -5.8 °C | 73 mm |
| 7 | `m_38.25_74.25` | Pamir and Karakoram | 0.588 | 0.38 | 0.66 | 0.32 | 0.97 | 0.93 | Dec, Jan, Nov | -3.7 °C | 70 mm |
| 8 | `m_81.25_-72.25` | Ellesmere or north-west Greenland | 0.572 | 0.27 | 0.45 | 0.45 | 0.92 | 0.14 | May, Jun, Jul | -17.4 °C | 129 mm |
| 9 | `m_-25.25_-69.25` | Altiplano and Puna | 0.568 | 0.34 | 1.00 | 0.18 | 1.00 | 0.67 | Jul, Jun, Aug | 10.6 °C | 19 mm |
| 10 | `m_-72.25_68.75` | Antarctica | 0.567 | 0.20 | 0.73 | 0.49 | 0.52 | 0.32 | Oct, Feb, Jan | -21.3 °C | 57 mm |

**Closest on all five factors**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_38.75_92.75` | Qaidam Basin | 0.733 | 0.95 | 0.91 | 0.26 | 1.00 | 0.93 | Jan, Dec, Feb | 2.4 °C | 32 mm |
| 2 | `m_37.25_88.25` | Tibetan Plateau | 0.690 | 0.63 | 0.79 | 0.35 | 0.99 | 0.91 | Jan, Dec, Feb | -6.7 °C | 47 mm |
| 3 | `m_35.25_84.75` | Tibetan Plateau | 0.688 | 0.75 | 0.69 | 0.34 | 1.00 | 0.87 | Jan, Dec, Feb | -5.9 °C | 63 mm |
| 4 | `m_35.25_79.75` | Tibetan Plateau | 0.683 | 0.71 | 0.65 | 0.37 | 1.00 | 0.87 | Dec, Jan, Nov | -9.3 °C | 72 mm |
| 5 | `m_41.75_101.75` | Gobi Desert | 0.669 | 0.99 | 0.77 | 0.19 | 1.00 | 0.93 | Jan, Dec, Feb | 9.8 °C | 50 mm |
| 6 | `m_38.75_85.25` | Taklamakan and Tarim Basin | 0.656 | 0.99 | 0.80 | 0.16 | 1.00 | 0.93 | Jan, Dec, Feb | 12.7 °C | 46 mm |
| 7 | `m_41.25_91.25` | Taklamakan and Tarim Basin | 0.642 | 0.73 | 0.92 | 0.17 | 1.00 | 0.93 | Jan, Dec, Feb | 11.6 °C | 32 mm |
| 8 | `m_37.75_81.75` | Taklamakan and Tarim Basin | 0.630 | 0.95 | 0.72 | 0.16 | 1.00 | 0.92 | Jan, Dec, Feb | 13.4 °C | 58 mm |
| 9 | `m_41.25_81.25` | Taklamakan and Tarim Basin | 0.626 | 1.00 | 0.55 | 0.19 | 0.99 | 0.93 | Dec, Jan, Feb | 10.1 °C | 95 mm |
| 10 | `m_45.75_91.75` | other | 0.625 | 0.98 | 0.48 | 0.25 | 0.97 | 0.85 | Feb, Mar, Nov | 3.8 °C | 119 mm |

The closest square on all factors is `m_38.75_92.75` (Qaidam Basin), with a score of 0.733.
There, Mars is 77.8 °C colder in the yearly mean.
The square gets 1.30 times 25 mm of precipitation a year.
Mars air pressure is 1.14 % of the square's.

### AP-8 (Arcadia Planitia)

Caveats: it is not a climate match, and a score is a position on each factor's own scale, not a share of likeness.

**Closest by landscape (slopes and bare ground)**

233 ranked squares tie at the top score of 1.000, so their order here is not a ranking. Tied squares are listed by bare area, then by environment score.

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_15.75_46.25` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.03 | 1.00 | 0.47 | Jan, Dec, Feb | 26.6 °C | 21 mm |
| 2 | `m_16.25_9.75` | Sahara | 1.000 | 1.00 | 0.57 | 0.03 | 1.00 | 0.48 | Jan, Dec, Feb | 26.4 °C | 91 mm |
| 3 | `m_16.25_18.75` | Sahara | 1.000 | 1.00 | 0.75 | 0.02 | 1.00 | 0.48 | Jan, Dec, Feb | 28.0 °C | 53 mm |
| 4 | `m_17.25_26.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.05 | 1.00 | 0.50 | Jan, Dec, Feb | 25.1 °C | 12 mm |
| 5 | `m_17.75_29.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.03 | 1.00 | 0.51 | Jan, Dec, Feb | 26.6 °C | 10 mm |
| 6 | `m_18.25_22.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.04 | 1.00 | 0.52 | Jan, Dec, Feb | 25.5 °C | 8 mm |
| 7 | `m_18.25_12.75` | Sahara | 1.000 | 1.00 | 0.94 | 0.03 | 1.00 | 0.52 | Jan, Dec, Feb | 26.9 °C | 30 mm |
| 8 | `m_18.25_48.25` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.02 | 1.00 | 0.52 | Jan, Dec, Feb | 28.0 °C | 19 mm |
| 9 | `m_18.25_55.75` | Arabian Desert | 1.000 | 1.00 | 0.37 | 0.03 | 1.00 | 0.52 | Dec, Jan, Nov | 26.9 °C | 165 mm |
| 10 | `m_18.75_-1.25` | Sahara | 1.000 | 1.00 | 0.61 | 0.01 | 1.00 | 0.53 | Jan, Dec, Feb | 28.6 °C | 80 mm |

**Closest by environment (dry, cold and bare)**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.659 | 0.29 | 0.80 | 0.36 | 1.00 | 0.88 | Jan, Dec, Feb | -7.3 °C | 45 mm |
| 2 | `m_38.75_93.75` | Qaidam Basin | 0.630 | 0.18 | 0.90 | 0.28 | 1.00 | 0.93 | Jan, Dec, Feb | 0.9 °C | 34 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.623 | 0.42 | 0.65 | 0.38 | 1.00 | 0.86 | Dec, Jan, Nov | -9.3 °C | 72 mm |
| 4 | `m_-77.75_164.25` | McMurdo Dry Valleys | 0.618 | 0.04 | 0.61 | 0.47 | 0.83 | 0.23 | Nov, Dec, Jan | -18.9 °C | 80 mm |
| 5 | `m_37.75_89.25` | Tibetan Plateau | 0.611 | 0.31 | 0.75 | 0.31 | 0.99 | 0.91 | Jan, Dec, Feb | -2.0 °C | 52 mm |
| 6 | `m_34.75_83.25` | Tibetan Plateau | 0.601 | 0.21 | 0.64 | 0.34 | 0.99 | 0.85 | Jan, Dec, Feb | -5.8 °C | 73 mm |
| 7 | `m_38.25_74.25` | Pamir and Karakoram | 0.589 | 0.16 | 0.66 | 0.32 | 0.97 | 0.92 | Dec, Jan, Nov | -3.7 °C | 70 mm |
| 8 | `m_81.25_-72.25` | Ellesmere or north-west Greenland | 0.573 | 0.08 | 0.45 | 0.45 | 0.92 | 0.16 | May, Jun, Jul | -17.4 °C | 129 mm |
| 9 | `m_-25.25_-69.25` | Altiplano and Puna | 0.569 | 0.11 | 1.00 | 0.19 | 1.00 | 0.66 | Jul, Jun, Aug | 10.6 °C | 19 mm |
| 10 | `m_-72.25_68.75` | Antarctica | 0.568 | 0.03 | 0.73 | 0.49 | 0.52 | 0.34 | Oct, Feb, Jan | -21.3 °C | 57 mm |

**Closest on all five factors**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_38.25_92.75` | Qaidam Basin | 0.710 | 0.87 | 0.92 | 0.25 | 1.00 | 0.92 | Jan, Dec, Feb | 4.2 °C | 32 mm |
| 2 | `m_41.75_101.75` | Gobi Desert | 0.666 | 0.95 | 0.77 | 0.19 | 1.00 | 0.93 | Jan, Dec, Feb | 9.8 °C | 50 mm |
| 3 | `m_39.25_86.25` | Taklamakan and Tarim Basin | 0.659 | 0.98 | 0.84 | 0.16 | 1.00 | 0.93 | Jan, Dec, Feb | 13.1 °C | 40 mm |
| 4 | `m_40.75_91.25` | Taklamakan and Tarim Basin | 0.635 | 0.76 | 0.91 | 0.16 | 1.00 | 0.93 | Jan, Dec, Feb | 13.1 °C | 33 mm |
| 5 | `m_37.75_83.25` | Taklamakan and Tarim Basin | 0.632 | 0.94 | 0.73 | 0.16 | 1.00 | 0.91 | Jan, Dec, Feb | 13.1 °C | 56 mm |
| 6 | `m_41.75_62.75` | Karakum and Kyzylkum | 0.626 | 1.00 | 0.68 | 0.15 | 1.00 | 0.93 | Jan, Dec, Nov | 14.0 °C | 66 mm |
| 7 | `m_38.75_79.25` | Taklamakan and Tarim Basin | 0.623 | 1.00 | 0.64 | 0.16 | 1.00 | 0.93 | Jan, Dec, Feb | 13.4 °C | 73 mm |
| 8 | `m_34.75_79.25` | Tibetan Plateau | 0.619 | 0.51 | 0.58 | 0.36 | 1.00 | 0.85 | Dec, Jan, Nov | -7.9 °C | 88 mm |
| 9 | `m_35.25_84.75` | Tibetan Plateau | 0.617 | 0.44 | 0.69 | 0.34 | 1.00 | 0.86 | Jan, Dec, Feb | -5.9 °C | 63 mm |
| 10 | `m_43.25_57.25` | Karakum and Kyzylkum | 0.616 | 1.00 | 0.57 | 0.17 | 1.00 | 0.92 | Feb, Jan, Nov | 12.0 °C | 92 mm |

The closest square on all factors is `m_38.25_92.75` (Qaidam Basin), with a score of 0.710.
There, Mars is 78.9 °C colder in the yearly mean.
The square gets 1.27 times 25 mm of precipitation a year.
Mars air pressure is 1.13 % of the square's.

### EM-15 (Erebus Montes)

Caveats: it is not a climate match, and a score is a position on each factor's own scale, not a share of likeness.

**Closest by landscape (slopes and bare ground)**

942 ranked squares tie at the top score of 1.000, so their order here is not a ranking. Tied squares are listed by bare area, then by environment score.

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_15.75_46.25` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.03 | 1.00 | 0.49 | Jan, Dec, Feb | 26.6 °C | 21 mm |
| 2 | `m_15.75_28.25` | Sahara | 1.000 | 1.00 | 0.76 | 0.04 | 1.00 | 0.49 | Jan, Dec, Feb | 25.9 °C | 52 mm |
| 3 | `m_15.75_11.25` | Sahara | 1.000 | 1.00 | 0.56 | 0.03 | 1.00 | 0.49 | Jan, Dec, Feb | 27.3 °C | 94 mm |
| 4 | `m_16.25_24.25` | Sahara | 1.000 | 1.00 | 0.96 | 0.06 | 1.00 | 0.50 | Jan, Dec, Feb | 24.0 °C | 28 mm |
| 5 | `m_16.25_18.75` | Sahara | 1.000 | 1.00 | 0.75 | 0.02 | 1.00 | 0.50 | Jan, Dec, Feb | 28.0 °C | 53 mm |
| 6 | `m_17.25_31.25` | Sahara | 1.000 | 1.00 | 0.96 | 0.02 | 1.00 | 0.52 | Jan, Dec, Feb | 28.3 °C | 28 mm |
| 7 | `m_17.75_48.25` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.02 | 1.00 | 0.53 | Jan, Dec, Feb | 27.8 °C | 21 mm |
| 8 | `m_18.25_26.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.05 | 1.00 | 0.54 | Jan, Dec, Feb | 24.6 °C | 4 mm |
| 9 | `m_18.25_22.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.04 | 1.00 | 0.54 | Jan, Dec, Feb | 25.5 °C | 8 mm |
| 10 | `m_18.25_9.75` | Sahara | 1.000 | 1.00 | 0.90 | 0.04 | 1.00 | 0.54 | Jan, Dec, Feb | 26.3 °C | 34 mm |

**Closest by environment (dry, cold and bare)**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.659 | 0.51 | 0.80 | 0.36 | 1.00 | 0.90 | Jan, Dec, Feb | -7.3 °C | 45 mm |
| 2 | `m_38.75_93.75` | Qaidam Basin | 0.630 | 0.40 | 0.90 | 0.28 | 1.00 | 0.93 | Jan, Dec, Feb | 0.9 °C | 34 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.623 | 0.69 | 0.65 | 0.38 | 1.00 | 0.88 | Dec, Jan, Nov | -9.3 °C | 72 mm |
| 4 | `m_-77.75_164.25` | McMurdo Dry Valleys | 0.618 | 0.17 | 0.61 | 0.47 | 0.83 | 0.21 | Nov, Dec, Jan | -18.9 °C | 80 mm |
| 5 | `m_37.75_89.25` | Tibetan Plateau | 0.611 | 0.56 | 0.75 | 0.31 | 0.99 | 0.93 | Jan, Dec, Feb | -2.0 °C | 52 mm |
| 6 | `m_34.75_83.25` | Tibetan Plateau | 0.602 | 0.43 | 0.64 | 0.34 | 0.99 | 0.87 | Jan, Dec, Feb | -5.8 °C | 73 mm |
| 7 | `m_38.25_74.25` | Pamir and Karakoram | 0.590 | 0.37 | 0.66 | 0.32 | 0.97 | 0.93 | Dec, Jan, Nov | -3.7 °C | 70 mm |
| 8 | `m_81.25_-72.25` | Ellesmere or north-west Greenland | 0.573 | 0.25 | 0.45 | 0.45 | 0.92 | 0.14 | May, Jun, Jul | -17.4 °C | 129 mm |
| 9 | `m_-25.25_-69.25` | Altiplano and Puna | 0.570 | 0.32 | 1.00 | 0.19 | 1.00 | 0.68 | Jul, Jun, Aug | 10.6 °C | 19 mm |
| 10 | `m_-72.25_68.75` | Antarctica | 0.569 | 0.18 | 0.73 | 0.49 | 0.52 | 0.32 | Oct, Feb, Jan | -21.3 °C | 57 mm |

**Closest on all five factors**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_38.75_92.75` | Qaidam Basin | 0.742 | 1.00 | 0.91 | 0.26 | 1.00 | 0.93 | Jan, Dec, Feb | 2.4 °C | 32 mm |
| 2 | `m_35.25_84.75` | Tibetan Plateau | 0.687 | 0.74 | 0.69 | 0.34 | 1.00 | 0.88 | Jan, Dec, Feb | -5.9 °C | 63 mm |
| 3 | `m_37.25_89.75` | Tibetan Plateau | 0.684 | 0.75 | 0.71 | 0.31 | 1.00 | 0.92 | Jan, Dec, Feb | -2.3 °C | 59 mm |
| 4 | `m_35.25_79.75` | Tibetan Plateau | 0.681 | 0.69 | 0.65 | 0.38 | 1.00 | 0.88 | Dec, Jan, Nov | -9.3 °C | 72 mm |
| 5 | `m_41.75_101.75` | Gobi Desert | 0.672 | 1.00 | 0.77 | 0.19 | 1.00 | 0.93 | Jan, Feb, Nov | 9.8 °C | 50 mm |
| 6 | `m_39.25_86.75` | Taklamakan and Tarim Basin | 0.663 | 1.00 | 0.86 | 0.16 | 1.00 | 0.93 | Jan, Dec, Feb | 13.3 °C | 38 mm |
| 7 | `m_41.25_91.25` | Taklamakan and Tarim Basin | 0.645 | 0.74 | 0.92 | 0.18 | 1.00 | 0.93 | Jan, Dec, Feb | 11.6 °C | 32 mm |
| 8 | `m_38.25_83.25` | Taklamakan and Tarim Basin | 0.644 | 1.00 | 0.73 | 0.16 | 1.00 | 0.93 | Jan, Dec, Feb | 13.0 °C | 56 mm |
| 9 | `m_44.75_104.25` | Gobi Desert | 0.628 | 0.98 | 0.47 | 0.24 | 1.00 | 0.87 | Feb, Nov, Mar | 4.4 °C | 121 mm |
| 10 | `m_41.25_81.25` | Taklamakan and Tarim Basin | 0.627 | 1.00 | 0.55 | 0.19 | 0.99 | 0.93 | Dec, Jan, Feb | 10.1 °C | 95 mm |

The closest square on all factors is `m_38.75_92.75` (Qaidam Basin), with a score of 0.742.
There, Mars is 76.9 °C colder in the yearly mean.
The square gets 1.30 times 25 mm of precipitation a year.
Mars air pressure is 1.14 % of the square's.

### PM-7 (Phlegra Montes)

Caveats: it is not a climate match, and a score is a position on each factor's own scale, not a share of likeness.

**Closest by landscape (slopes and bare ground)**

150 ranked squares tie at the top score of 1.000, so their order here is not a ranking. Tied squares are listed by bare area, then by environment score.

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_12.75_41.25` | Danakil Depression | 1.000 | 1.00 | 0.21 | 0.00 | 1.00 | 0.50 | Jan, Dec, Feb | 33.1 °C | 266 mm |
| 2 | `m_15.75_50.75` | Arabian Desert | 1.000 | 1.00 | 0.94 | 0.04 | 1.00 | 0.55 | Jan, Dec, Feb | 25.8 °C | 30 mm |
| 3 | `m_17.75_23.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.05 | 1.00 | 0.59 | Jan, Dec, Feb | 24.6 °C | 10 mm |
| 4 | `m_17.75_36.75` | Sahara | 1.000 | 1.00 | 0.68 | 0.04 | 1.00 | 0.59 | Feb, Jan, Mar | 26.3 °C | 65 mm |
| 5 | `m_18.75_43.75` | Arabian Desert | 1.000 | 1.00 | 0.85 | 0.05 | 1.00 | 0.61 | Dec, Jan, Nov | 24.4 °C | 39 mm |
| 6 | `m_18.75_9.25` | Sahara | 1.000 | 1.00 | 0.75 | 0.05 | 1.00 | 0.61 | Jan, Dec, Feb | 25.0 °C | 54 mm |
| 7 | `m_19.75_19.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.05 | 1.00 | 0.63 | Jan, Dec, Feb | 24.7 °C | 5 mm |
| 8 | `m_20.25_-13.25` | Sahara | 1.000 | 1.00 | 0.30 | 0.02 | 1.00 | 0.64 | Jan, Dec, Feb | 27.5 °C | 204 mm |
| 9 | `m_20.75_16.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.05 | 1.00 | 0.65 | Jan, Dec, Feb | 24.4 °C | 22 mm |
| 10 | `m_20.75_36.75` | Sahara | 1.000 | 1.00 | 0.90 | 0.02 | 1.00 | 0.65 | Feb, Jan, Mar | 28.0 °C | 34 mm |

**Closest by environment (dry, cold and bare)**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.662 | 0.98 | 0.80 | 0.36 | 1.00 | 0.93 | Jan, Dec, Feb | -7.3 °C | 45 mm |
| 2 | `m_38.75_93.75` | Qaidam Basin | 0.633 | 0.89 | 0.90 | 0.28 | 1.00 | 0.92 | Jan, Feb, Nov | 0.9 °C | 34 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.626 | 1.00 | 0.65 | 0.38 | 1.00 | 0.93 | Dec, Jan, Nov | -9.3 °C | 72 mm |
| 4 | `m_-77.75_164.25` | McMurdo Dry Valleys | 0.621 | 0.40 | 0.61 | 0.48 | 0.83 | 0.15 | Nov, Dec, Jan | -18.9 °C | 80 mm |
| 5 | `m_37.75_89.25` | Tibetan Plateau | 0.615 | 0.85 | 0.75 | 0.31 | 0.99 | 0.93 | Jan, Dec, Feb | -2.0 °C | 52 mm |
| 6 | `m_34.75_83.25` | Tibetan Plateau | 0.605 | 0.97 | 0.64 | 0.35 | 0.99 | 0.93 | Jan, Dec, Feb | -5.8 °C | 73 mm |
| 7 | `m_38.25_74.25` | Pamir and Karakoram | 0.593 | 0.68 | 0.66 | 0.33 | 0.97 | 0.93 | Dec, Jan, Nov | -3.7 °C | 70 mm |
| 8 | `m_81.25_-72.25` | Ellesmere or north-west Greenland | 0.576 | 0.60 | 0.45 | 0.46 | 0.92 | 0.08 | Jun, Jul | -17.4 °C | 129 mm |
| 9 | `m_-25.25_-69.25` | Altiplano and Puna | 0.573 | 0.69 | 1.00 | 0.19 | 1.00 | 0.74 | Jul, Jun, Aug | 10.6 °C | 19 mm |
| 10 | `m_-72.25_68.75` | Antarctica | 0.572 | 0.45 | 0.73 | 0.50 | 0.52 | 0.25 | Feb, Jan, Dec | -21.3 °C | 57 mm |

**Closest on all five factors**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.767 | 0.98 | 0.80 | 0.36 | 1.00 | 0.93 | Jan, Dec, Feb | -7.3 °C | 45 mm |
| 2 | `m_35.25_79.75` | Tibetan Plateau | 0.744 | 1.00 | 0.65 | 0.38 | 1.00 | 0.93 | Dec, Jan, Nov | -9.3 °C | 72 mm |
| 3 | `m_38.75_93.75` | Qaidam Basin | 0.731 | 0.89 | 0.90 | 0.28 | 1.00 | 0.92 | Jan, Feb, Nov | 0.9 °C | 34 mm |
| 4 | `m_37.25_89.75` | Tibetan Plateau | 0.730 | 1.00 | 0.71 | 0.31 | 1.00 | 0.93 | Jan, Dec, Feb | -2.3 °C | 59 mm |
| 5 | `m_34.75_83.25` | Tibetan Plateau | 0.725 | 0.97 | 0.64 | 0.35 | 0.99 | 0.93 | Jan, Dec, Feb | -5.8 °C | 73 mm |
| 6 | `m_41.25_89.75` | Taklamakan and Tarim Basin | 0.689 | 0.99 | 0.95 | 0.19 | 1.00 | 0.87 | Feb, Nov, Mar | 10.4 °C | 29 mm |
| 7 | `m_44.25_97.25` | Gobi Desert | 0.668 | 1.00 | 0.70 | 0.23 | 1.00 | 0.81 | Feb, Mar, Oct | 6.1 °C | 60 mm |
| 8 | `m_38.25_74.25` | Pamir and Karakoram | 0.667 | 0.68 | 0.66 | 0.33 | 0.97 | 0.93 | Dec, Jan, Nov | -3.7 °C | 70 mm |
| 9 | `m_41.25_96.25` | Gobi Desert | 0.664 | 0.95 | 0.64 | 0.24 | 1.00 | 0.87 | Feb, Nov, Mar | 4.8 °C | 74 mm |
| 10 | `m_36.25_95.75` | Qaidam Basin | 0.654 | 0.96 | 0.59 | 0.24 | 0.97 | 0.93 | Jan, Dec, Feb | 5.8 °C | 86 mm |

The closest square on all factors is `m_36.25_86.25` (Tibetan Plateau), with a score of 0.767.
There, Mars is 65.6 °C colder in the yearly mean.
The square gets 1.81 times 25 mm of precipitation a year.
Mars air pressure is 1.27 % of the square's.

### Phlegra Dorsa, Arcadia Planitia

Caveats: it is not a climate match, and a score is a position on each factor's own scale, not a share of likeness.

**Closest by landscape (slopes and bare ground)**

506 ranked squares tie at the top score of 1.000, so their order here is not a ranking. Tied squares are listed by bare area, then by environment score.

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_15.75_11.25` | Sahara | 1.000 | 1.00 | 0.56 | 0.03 | 1.00 | 0.50 | Jan, Dec, Feb | 27.3 °C | 94 mm |
| 2 | `m_16.25_24.25` | Sahara | 1.000 | 1.00 | 0.96 | 0.06 | 1.00 | 0.51 | Jan, Dec, Feb | 24.0 °C | 28 mm |
| 3 | `m_16.75_29.25` | Sahara | 1.000 | 1.00 | 0.90 | 0.03 | 1.00 | 0.52 | Jan, Dec, Feb | 26.6 °C | 34 mm |
| 4 | `m_17.75_21.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.04 | 1.00 | 0.54 | Jan, Dec, Feb | 26.4 °C | 19 mm |
| 5 | `m_17.75_18.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.02 | 1.00 | 0.54 | Jan, Dec, Feb | 27.7 °C | 7 mm |
| 6 | `m_17.75_49.25` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.01 | 1.00 | 0.54 | Jan, Dec, Feb | 28.7 °C | 14 mm |
| 7 | `m_18.25_9.75` | Sahara | 1.000 | 1.00 | 0.90 | 0.04 | 1.00 | 0.55 | Jan, Dec, Feb | 26.3 °C | 34 mm |
| 8 | `m_18.25_13.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.03 | 1.00 | 0.55 | Jan, Dec, Feb | 26.7 °C | 22 mm |
| 9 | `m_18.25_32.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.01 | 1.00 | 0.55 | Jan, Dec, Feb | 28.6 °C | 13 mm |
| 10 | `m_18.25_-8.25` | Sahara | 1.000 | 1.00 | 0.48 | 0.03 | 1.00 | 0.55 | Jan, Dec, Feb | 27.3 °C | 117 mm |

**Closest by environment (dry, cold and bare)**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.664 | 0.62 | 0.80 | 0.37 | 1.00 | 0.91 | Jan, Dec, Feb | -7.3 °C | 45 mm |
| 2 | `m_38.75_93.75` | Qaidam Basin | 0.635 | 0.41 | 0.90 | 0.28 | 1.00 | 0.93 | Jan, Dec, Feb | 0.9 °C | 34 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.628 | 0.72 | 0.65 | 0.38 | 1.00 | 0.89 | Dec, Jan, Nov | -9.3 °C | 72 mm |
| 4 | `m_-77.75_164.25` | McMurdo Dry Valleys | 0.623 | 0.12 | 0.61 | 0.48 | 0.83 | 0.20 | Nov, Dec, Jan | -18.9 °C | 80 mm |
| 5 | `m_37.75_89.25` | Tibetan Plateau | 0.616 | 0.56 | 0.75 | 0.31 | 0.99 | 0.93 | Jan, Dec, Feb | -2.0 °C | 52 mm |
| 6 | `m_34.75_83.25` | Tibetan Plateau | 0.606 | 0.52 | 0.64 | 0.35 | 0.99 | 0.88 | Jan, Dec, Feb | -5.8 °C | 73 mm |
| 7 | `m_38.25_74.25` | Pamir and Karakoram | 0.594 | 0.34 | 0.66 | 0.33 | 0.97 | 0.93 | Dec, Jan, Nov | -3.7 °C | 70 mm |
| 8 | `m_81.25_-72.25` | Ellesmere or north-west Greenland | 0.578 | 0.22 | 0.45 | 0.46 | 0.92 | 0.13 | May, Jun, Jul | -17.4 °C | 129 mm |
| 9 | `m_-25.25_-69.25` | Altiplano and Puna | 0.574 | 0.30 | 1.00 | 0.19 | 1.00 | 0.69 | Jul, Jun, Aug | 10.6 °C | 19 mm |
| 10 | `m_-72.25_68.75` | Antarctica | 0.573 | 0.13 | 0.73 | 0.50 | 0.52 | 0.31 | Oct, Feb, Jan | -21.3 °C | 57 mm |

**Closest on all five factors**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_38.75_93.25` | Qaidam Basin | 0.750 | 1.00 | 0.94 | 0.27 | 1.00 | 0.93 | Jan, Dec, Feb | 2.3 °C | 30 mm |
| 2 | `m_35.75_86.25` | Tibetan Plateau | 0.713 | 0.79 | 0.77 | 0.36 | 0.95 | 0.90 | Jan, Dec, Feb | -6.5 °C | 50 mm |
| 3 | `m_37.25_89.75` | Tibetan Plateau | 0.709 | 0.85 | 0.71 | 0.32 | 1.00 | 0.93 | Jan, Dec, Feb | -2.3 °C | 59 mm |
| 4 | `m_35.25_82.75` | Tibetan Plateau | 0.700 | 0.77 | 0.66 | 0.38 | 0.98 | 0.89 | Jan, Dec, Nov | -8.5 °C | 69 mm |
| 5 | `m_34.75_79.25` | Tibetan Plateau | 0.698 | 0.88 | 0.58 | 0.37 | 1.00 | 0.88 | Dec, Jan, Nov | -7.9 °C | 88 mm |
| 6 | `m_40.75_89.25` | Taklamakan and Tarim Basin | 0.674 | 0.95 | 0.88 | 0.18 | 1.00 | 0.93 | Jan, Dec, Feb | 11.9 °C | 35 mm |
| 7 | `m_41.75_101.75` | Gobi Desert | 0.672 | 1.00 | 0.77 | 0.20 | 1.00 | 0.91 | Jan, Feb, Nov | 9.8 °C | 50 mm |
| 8 | `m_38.75_85.75` | Taklamakan and Tarim Basin | 0.664 | 1.00 | 0.83 | 0.17 | 0.98 | 0.93 | Jan, Dec, Feb | 12.7 °C | 42 mm |
| 9 | `m_41.75_96.25` | Gobi Desert | 0.634 | 0.69 | 0.66 | 0.24 | 1.00 | 0.91 | Jan, Feb, Nov | 5.0 °C | 69 mm |
| 10 | `m_38.75_80.25` | Taklamakan and Tarim Basin | 0.632 | 1.00 | 0.66 | 0.16 | 1.00 | 0.93 | Jan, Dec, Feb | 13.3 °C | 69 mm |

The closest square on all factors is `m_38.75_93.25` (Qaidam Basin), with a score of 0.750.
There, Mars is 74.4 °C colder in the yearly mean.
The square gets 1.19 times 25 mm of precipitation a year.
Mars air pressure is 1.16 % of the square's.

### Southern Nectaris Fossae

Caveats: it is not a climate match, and a score is a position on each factor's own scale, not a share of likeness.

**Closest by landscape (slopes and bare ground)**

232 ranked squares tie at the top score of 1.000, so their order here is not a ranking. Tied squares are listed by bare area, then by environment score.

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_12.75_41.25` | Danakil Depression | 1.000 | 1.00 | 0.21 | 0.00 | 1.00 | 0.65 | Jan, Dec, Feb | 33.1 °C | 266 mm |
| 2 | `m_15.75_50.75` | Arabian Desert | 1.000 | 1.00 | 0.94 | 0.05 | 1.00 | 0.70 | Jan, Dec, Feb | 25.8 °C | 30 mm |
| 3 | `m_16.75_44.75` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.06 | 1.00 | 0.72 | Dec, Jan, Nov | 24.9 °C | 19 mm |
| 4 | `m_17.75_22.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.05 | 1.00 | 0.74 | Jan, Dec, Feb | 25.8 °C | 17 mm |
| 5 | `m_17.75_36.75` | Sahara | 1.000 | 1.00 | 0.68 | 0.04 | 1.00 | 0.74 | Feb, Jan, Mar | 26.3 °C | 65 mm |
| 6 | `m_18.25_9.25` | Sahara | 1.000 | 1.00 | 0.64 | 0.05 | 1.00 | 0.75 | Jan, Dec, Feb | 25.5 °C | 73 mm |
| 7 | `m_19.25_43.25` | Arabian Desert | 1.000 | 1.00 | 0.91 | 0.05 | 1.00 | 0.77 | Jan, Dec, Feb | 25.2 °C | 33 mm |
| 8 | `m_19.75_-12.75` | Sahara | 1.000 | 1.00 | 0.41 | 0.03 | 1.00 | 0.78 | Jan, Dec, Feb | 26.8 °C | 146 mm |
| 9 | `m_20.25_19.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.07 | 1.00 | 0.79 | Jan, Dec, Feb | 23.8 °C | 4 mm |
| 10 | `m_20.75_16.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.06 | 1.00 | 0.80 | Jan, Dec, Feb | 24.4 °C | 22 mm |

**Closest by environment (dry, cold and bare)**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.687 | 1.00 | 0.80 | 0.40 | 1.00 | 0.82 | Feb, Mar, Oct | -7.3 °C | 45 mm |
| 2 | `m_38.75_93.75` | Qaidam Basin | 0.656 | 0.84 | 0.90 | 0.31 | 1.00 | 0.77 | Feb, Mar, Oct | 0.9 °C | 34 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.649 | 0.91 | 0.65 | 0.43 | 1.00 | 0.84 | Nov, Feb, Mar | -9.3 °C | 72 mm |
| 4 | `m_-77.75_164.25` | McMurdo Dry Valleys | 0.644 | 0.31 | 0.61 | 0.53 | 0.83 | 0.00 | none | -18.9 °C | 80 mm |
| 5 | `m_37.75_89.25` | Tibetan Plateau | 0.637 | 0.72 | 0.75 | 0.35 | 0.99 | 0.79 | Feb, Mar, Oct | -2.0 °C | 52 mm |
| 6 | `m_34.75_83.25` | Tibetan Plateau | 0.627 | 1.00 | 0.64 | 0.39 | 0.99 | 0.85 | Feb, Nov, Mar | -5.8 °C | 73 mm |
| 7 | `m_38.25_74.25` | Pamir and Karakoram | 0.614 | 0.61 | 0.66 | 0.36 | 0.97 | 0.78 | Feb, Oct, Mar | -3.7 °C | 70 mm |
| 8 | `m_81.25_-72.25` | Ellesmere or north-west Greenland | 0.597 | 0.57 | 0.45 | 0.51 | 0.92 | 0.00 | none | -17.4 °C | 129 mm |
| 9 | `m_-25.25_-69.25` | Altiplano and Puna | 0.594 | 0.69 | 1.00 | 0.21 | 1.00 | 0.89 | Jul, Jun, Aug | 10.6 °C | 19 mm |
| 10 | `m_-72.25_68.75` | Antarctica | 0.593 | 0.36 | 0.73 | 0.56 | 0.52 | 0.10 | Jan, Dec, Nov | -21.3 °C | 57 mm |

**Closest on all five factors**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.767 | 1.00 | 0.80 | 0.40 | 1.00 | 0.82 | Feb, Mar, Oct | -7.3 °C | 45 mm |
| 2 | `m_35.25_82.75` | Tibetan Plateau | 0.743 | 1.00 | 0.66 | 0.42 | 0.98 | 0.84 | Nov, Feb, Mar | -8.5 °C | 69 mm |
| 3 | `m_34.75_79.25` | Tibetan Plateau | 0.726 | 1.00 | 0.58 | 0.41 | 1.00 | 0.85 | Nov, Feb, Oct | -7.9 °C | 88 mm |
| 4 | `m_37.75_92.25` | Qaidam Basin | 0.715 | 1.00 | 0.86 | 0.28 | 1.00 | 0.79 | Feb, Mar, Oct | 4.4 °C | 38 mm |
| 5 | `m_41.25_89.75` | Taklamakan and Tarim Basin | 0.679 | 1.00 | 0.95 | 0.21 | 1.00 | 0.72 | Feb, Mar, Oct | 10.4 °C | 29 mm |
| 6 | `m_-24.75_-69.75` | Atacama Desert | 0.673 | 1.00 | 1.00 | 0.16 | 1.00 | 0.88 | Jul, Jun, Aug | 15.5 °C | 9 mm |
| 7 | `m_41.25_96.25` | Gobi Desert | 0.660 | 1.00 | 0.64 | 0.27 | 1.00 | 0.72 | Feb, Mar, Oct | 4.8 °C | 74 mm |
| 8 | `m_37.25_95.75` | Qaidam Basin | 0.655 | 1.00 | 0.50 | 0.30 | 1.00 | 0.80 | Feb, Mar, Oct | 2.0 °C | 112 mm |
| 9 | `m_44.25_97.25` | Gobi Desert | 0.655 | 1.00 | 0.70 | 0.26 | 1.00 | 0.66 | Mar, Oct, Apr | 6.1 °C | 60 mm |
| 10 | `m_-27.75_-70.75` | Atacama Desert | 0.652 | 1.00 | 0.86 | 0.15 | 1.00 | 0.93 | Sep, Oct, Apr | 16.3 °C | 38 mm |

The closest square on all factors is `m_36.25_86.25` (Tibetan Plateau), with a score of 0.767.
There, Mars is 55.1 °C colder in the yearly mean.
The square gets 1.81 times 25 mm of precipitation a year.
Mars air pressure is 0.87 % of the square's.

### Valles Marineris mouth (southern Acidalia Planitia, as named in the abstract)

Caveats: it is not a climate match, and a score is a position on each factor's own scale, not a share of likeness.

**Closest by landscape (slopes and bare ground)**

484 ranked squares tie at the top score of 1.000, so their order here is not a ranking. Tied squares are listed by bare area, then by environment score.

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_15.75_47.25` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.04 | 1.00 | 0.87 | Jan, Dec, Feb | 26.6 °C | 17 mm |
| 2 | `m_16.25_27.25` | Sahara | 1.000 | 1.00 | 0.87 | 0.06 | 1.00 | 0.88 | Jan, Dec, Feb | 25.0 °C | 37 mm |
| 3 | `m_16.75_30.25` | Sahara | 1.000 | 1.00 | 0.84 | 0.03 | 1.00 | 0.89 | Jan, Dec, Feb | 27.1 °C | 40 mm |
| 4 | `m_17.25_44.75` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.05 | 1.00 | 0.90 | Dec, Jan, Feb | 25.7 °C | 18 mm |
| 5 | `m_17.75_23.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.06 | 1.00 | 0.91 | Jan, Dec, Feb | 24.6 °C | 10 mm |
| 6 | `m_17.75_54.75` | Arabian Desert | 1.000 | 1.00 | 0.37 | 0.04 | 1.00 | 0.91 | Dec, Jan, Nov | 26.5 °C | 163 mm |
| 7 | `m_18.25_20.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.04 | 1.00 | 0.92 | Jan, Dec, Feb | 26.4 °C | 7 mm |
| 8 | `m_18.25_9.75` | Sahara | 1.000 | 1.00 | 0.90 | 0.04 | 1.00 | 0.92 | Jan, Dec, Feb | 26.3 °C | 34 mm |
| 9 | `m_18.25_32.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.02 | 1.00 | 0.92 | Jan, Dec, Feb | 28.6 °C | 13 mm |
| 10 | `m_18.75_-12.25` | Sahara | 1.000 | 1.00 | 0.49 | 0.02 | 1.00 | 0.93 | Jan, Dec, Feb | 28.5 °C | 115 mm |

**Closest by environment (dry, cold and bare)**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.702 | 0.68 | 0.80 | 0.43 | 1.00 | 0.72 | Mar, Oct, Apr | -7.3 °C | 45 mm |
| 2 | `m_38.75_93.75` | Qaidam Basin | 0.670 | 0.44 | 0.90 | 0.34 | 1.00 | 0.66 | Mar, Apr, May | 0.9 °C | 34 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.663 | 0.73 | 0.65 | 0.45 | 1.00 | 0.74 | Mar, Oct, Apr | -9.3 °C | 72 mm |
| 4 | `m_-77.75_164.25` | McMurdo Dry Valleys | 0.658 | 0.16 | 0.61 | 0.56 | 0.83 | 0.00 | none | -18.9 °C | 80 mm |
| 5 | `m_37.75_89.25` | Tibetan Plateau | 0.651 | 0.54 | 0.75 | 0.37 | 0.99 | 0.68 | Mar, Apr, Sep | -2.0 °C | 52 mm |
| 6 | `m_34.75_83.25` | Tibetan Plateau | 0.640 | 0.59 | 0.64 | 0.41 | 0.99 | 0.75 | Mar, Oct, Apr | -5.8 °C | 73 mm |
| 7 | `m_38.25_74.25` | Pamir and Karakoram | 0.627 | 0.37 | 0.66 | 0.39 | 0.97 | 0.67 | Mar, Sep, Apr | -3.7 °C | 70 mm |
| 8 | `m_81.25_-72.25` | Ellesmere or north-west Greenland | 0.610 | 0.27 | 0.45 | 0.55 | 0.92 | 0.00 | none | -17.4 °C | 129 mm |
| 9 | `m_-25.25_-69.25` | Altiplano and Puna | 0.606 | 0.34 | 1.00 | 0.22 | 1.00 | 0.96 | Aug, May, Sep | 10.6 °C | 19 mm |
| 10 | `m_-72.25_68.75` | Antarctica | 0.605 | 0.17 | 0.73 | 0.59 | 0.52 | 0.00 | none | -21.3 °C | 57 mm |

**Closest on all five factors**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_35.75_86.25` | Tibetan Plateau | 0.717 | 0.85 | 0.77 | 0.42 | 0.95 | 0.73 | Mar, Oct, Apr | -6.5 °C | 50 mm |
| 2 | `m_38.25_93.25` | Qaidam Basin | 0.717 | 1.00 | 0.94 | 0.30 | 1.00 | 0.67 | Mar, Apr, May | 4.0 °C | 30 mm |
| 3 | `m_35.25_82.75` | Tibetan Plateau | 0.712 | 0.86 | 0.66 | 0.44 | 0.98 | 0.74 | Mar, Oct, Apr | -8.5 °C | 69 mm |
| 4 | `m_37.25_89.75` | Tibetan Plateau | 0.709 | 0.98 | 0.71 | 0.37 | 1.00 | 0.69 | Mar, Apr, Sep | -2.3 °C | 59 mm |
| 5 | `m_34.75_79.25` | Tibetan Plateau | 0.706 | 0.92 | 0.58 | 0.44 | 1.00 | 0.75 | Oct, Mar, Apr | -7.9 °C | 88 mm |
| 6 | `m_-23.25_-68.25` | Atacama Desert | 0.675 | 0.79 | 0.94 | 0.19 | 1.00 | 1.00 | Jul, Aug, May | 13.6 °C | 30 mm |
| 7 | `m_-20.25_-69.75` | Atacama Desert | 0.652 | 0.90 | 1.00 | 0.14 | 0.97 | 0.97 | Jul, Aug, Jun | 17.9 °C | 11 mm |
| 8 | `m_41.25_91.25` | Taklamakan and Tarim Basin | 0.648 | 0.96 | 0.92 | 0.21 | 1.00 | 0.61 | Mar, Apr, Sep | 11.6 °C | 32 mm |
| 9 | `m_23.25_26.25` | Sahara | 0.641 | 0.96 | 1.00 | 0.11 | 1.00 | 1.00 | Jan, Feb, Nov | 20.2 °C | 2 mm |
| 10 | `m_39.25_86.75` | Taklamakan and Tarim Basin | 0.640 | 1.00 | 0.86 | 0.19 | 1.00 | 0.65 | Mar, Apr, Sep | 13.3 °C | 38 mm |

The closest square on all factors is `m_35.75_86.25` (Tibetan Plateau), with a score of 0.717.
There, Mars is 50.2 °C colder in the yearly mean.
The square gets 2.02 times 25 mm of precipitation a year.
Mars air pressure is 1.46 % of the square's.

### East Melas Chasma

Caveats: it is not a climate match, and a score is a position on each factor's own scale, not a share of likeness.

**Closest by landscape (slopes and bare ground)**

33 ranked squares tie at the top score of 1.000, so their order here is not a ranking. Tied squares are listed by bare area, then by environment score.

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_19.25_8.75` | Sahara | 1.000 | 1.00 | 0.89 | 0.07 | 1.00 | 1.00 | Feb, Mar, Oct | 24.1 °C | 34 mm |
| 2 | `m_19.75_18.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.10 | 1.00 | 1.00 | Feb, Mar, Oct | 21.9 °C | 14 mm |
| 3 | `m_20.25_36.75` | Sahara | 1.000 | 1.00 | 0.83 | 0.03 | 1.00 | 1.00 | Feb, Mar, Apr | 27.4 °C | 42 mm |
| 4 | `m_-21.75_-69.25` | Atacama Desert | 1.000 | 1.00 | 1.00 | 0.15 | 1.00 | 1.00 | Aug, Sep, Oct | 17.7 °C | 21 mm |
| 5 | `m_-24.75_-69.25` | Atacama Desert | 1.000 | 1.00 | 1.00 | 0.18 | 1.00 | 0.96 | Sep, Apr, Oct | 14.5 °C | 12 mm |
| 6 | `m_26.25_37.25` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.08 | 1.00 | 0.92 | Mar, Apr, Oct | 23.0 °C | 16 mm |
| 7 | `m_26.25_7.25` | Sahara | 1.000 | 1.00 | 0.96 | 0.07 | 1.00 | 0.92 | Mar, Apr, Oct | 24.2 °C | 28 mm |
| 8 | `m_26.25_58.25` | Arabian Desert | 1.000 | 1.00 | 0.57 | 0.06 | 1.00 | 0.92 | Oct, Mar, Apr | 24.8 °C | 92 mm |
| 9 | `m_27.25_33.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.09 | 1.00 | 0.90 | Mar, Apr, Oct | 22.7 °C | 8 mm |
| 10 | `m_27.75_62.25` | other | 1.000 | 1.00 | 0.59 | 0.08 | 1.00 | 0.88 | Oct, Mar, Apr | 23.1 °C | 85 mm |

**Closest by environment (dry, cold and bare)**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.708 | 0.67 | 0.80 | 0.44 | 1.00 | 0.65 | Apr, Sep, May | -7.3 °C | 45 mm |
| 2 | `m_38.75_93.75` | Qaidam Basin | 0.677 | 1.00 | 0.90 | 0.35 | 1.00 | 0.58 | Apr, May, Sep | 0.9 °C | 34 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.670 | 0.99 | 0.65 | 0.47 | 1.00 | 0.68 | Apr, Sep, May | -9.3 °C | 72 mm |
| 4 | `m_-77.75_164.25` | McMurdo Dry Valleys | 0.664 | 0.71 | 0.61 | 0.58 | 0.83 | 0.00 | none | -18.9 °C | 80 mm |
| 5 | `m_37.75_89.25` | Tibetan Plateau | 0.657 | 1.00 | 0.75 | 0.38 | 0.99 | 0.61 | Apr, Sep, May | -2.0 °C | 52 mm |
| 6 | `m_34.75_83.25` | Tibetan Plateau | 0.647 | 0.87 | 0.64 | 0.43 | 0.99 | 0.69 | Mar, Apr, May | -5.8 °C | 73 mm |
| 7 | `m_38.25_74.25` | Pamir and Karakoram | 0.633 | 0.97 | 0.66 | 0.40 | 0.97 | 0.60 | Sep, Apr, May | -3.7 °C | 70 mm |
| 8 | `m_81.25_-72.25` | Ellesmere or north-west Greenland | 0.616 | 1.00 | 0.45 | 0.56 | 0.92 | 0.00 | none | -17.4 °C | 129 mm |
| 9 | `m_-25.25_-69.25` | Altiplano and Puna | 0.612 | 1.00 | 1.00 | 0.23 | 1.00 | 0.95 | Sep, Apr, Oct | 10.6 °C | 19 mm |
| 10 | `m_-72.25_68.75` | Antarctica | 0.611 | 0.66 | 0.73 | 0.61 | 0.52 | 0.00 | none | -21.3 °C | 57 mm |

**Closest on all five factors**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_-22.25_-68.25` | Altiplano and Puna | 0.744 | 1.00 | 0.83 | 0.30 | 0.90 | 1.00 | Aug, Sep, Apr | 4.4 °C | 42 mm |
| 2 | `m_-25.25_-69.25` | Altiplano and Puna | 0.738 | 1.00 | 1.00 | 0.23 | 1.00 | 0.95 | Sep, Apr, Oct | 10.6 °C | 19 mm |
| 3 | `m_36.75_86.75` | Tibetan Plateau | 0.730 | 0.98 | 0.80 | 0.42 | 0.98 | 0.64 | Apr, Sep, May | -5.5 °C | 45 mm |
| 4 | `m_34.75_81.25` | Tibetan Plateau | 0.726 | 1.00 | 0.64 | 0.46 | 0.98 | 0.69 | Mar, Apr, Sep | -8.7 °C | 73 mm |
| 5 | `m_38.75_93.75` | Qaidam Basin | 0.711 | 1.00 | 0.90 | 0.35 | 1.00 | 0.58 | Apr, May, Sep | 0.9 °C | 34 mm |
| 6 | `m_37.75_90.25` | Tibetan Plateau | 0.690 | 1.00 | 0.74 | 0.36 | 0.95 | 0.61 | Apr, Sep, May | -0.5 °C | 55 mm |
| 7 | `m_-28.25_-69.25` | Altiplano and Puna | 0.683 | 1.00 | 0.52 | 0.34 | 0.98 | 0.87 | Sep, Oct, Nov | 1.4 °C | 106 mm |
| 8 | `m_-18.75_-70.25` | Atacama Desert | 0.682 | 1.00 | 0.98 | 0.15 | 0.99 | 1.00 | Aug, Sep, Oct | 17.2 °C | 26 mm |
| 9 | `m_38.25_74.25` | Pamir and Karakoram | 0.681 | 0.97 | 0.66 | 0.40 | 0.97 | 0.60 | Sep, Apr, May | -3.7 °C | 70 mm |
| 10 | `m_31.75_79.75` | Tibetan Plateau | 0.672 | 1.00 | 0.50 | 0.40 | 0.90 | 0.77 | Apr, Mar, May | -3.3 °C | 113 mm |

The closest square on all factors is `m_-22.25_-68.25` (Altiplano and Puna), with a score of 0.744.
There, Mars is 58.6 °C colder in the yearly mean.
The square gets 1.66 times 25 mm of precipitation a year.
Mars air pressure is 1.43 % of the square's.

### Mawrth Vallis

Caveats: it is not a climate match, and a score is a position on each factor's own scale, not a share of likeness.

**Closest by landscape (slopes and bare ground)**

119 ranked squares tie at the top score of 1.000, so their order here is not a ranking. Tied squares are listed by bare area, then by environment score.

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_12.75_41.25` | Danakil Depression | 1.000 | 1.00 | 0.21 | 0.00 | 1.00 | 0.73 | Jan, Dec, Feb | 33.1 °C | 266 mm |
| 2 | `m_15.75_50.75` | Arabian Desert | 1.000 | 1.00 | 0.94 | 0.05 | 1.00 | 0.79 | Jan, Dec, Feb | 25.8 °C | 30 mm |
| 3 | `m_16.75_44.75` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.06 | 1.00 | 0.81 | Dec, Jan, Nov | 24.9 °C | 19 mm |
| 4 | `m_18.75_9.25` | Sahara | 1.000 | 1.00 | 0.75 | 0.06 | 1.00 | 0.85 | Jan, Dec, Feb | 25.0 °C | 54 mm |
| 5 | `m_-18.75_12.75` | Namib Desert | 1.000 | 1.00 | 0.30 | 0.10 | 1.00 | 0.85 | Aug, Sep, Jul | 20.8 °C | 204 mm |
| 6 | `m_19.25_36.75` | Sahara | 1.000 | 1.00 | 0.80 | 0.02 | 1.00 | 0.86 | Feb, Jan, Mar | 27.9 °C | 46 mm |
| 7 | `m_19.75_18.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.09 | 1.00 | 0.87 | Jan, Dec, Feb | 21.9 °C | 14 mm |
| 8 | `m_-21.25_-69.75` | Atacama Desert | 1.000 | 1.00 | 1.00 | 0.14 | 1.00 | 0.90 | Jul, Aug, Sep | 17.8 °C | 9 mm |
| 9 | `m_21.25_16.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.07 | 1.00 | 0.90 | Jan, Dec, Feb | 23.5 °C | 18 mm |
| 10 | `m_22.25_35.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.04 | 1.00 | 0.92 | Jan, Dec, Feb | 26.0 °C | 14 mm |

**Closest by environment (dry, cold and bare)**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.693 | 0.90 | 0.80 | 0.42 | 1.00 | 0.74 | Feb, Mar, Oct | -7.3 °C | 45 mm |
| 2 | `m_38.75_93.75` | Qaidam Basin | 0.663 | 1.00 | 0.90 | 0.32 | 1.00 | 0.69 | Mar, Oct, Apr | 0.9 °C | 34 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.655 | 1.00 | 0.65 | 0.44 | 1.00 | 0.76 | Feb, Mar, Oct | -9.3 °C | 72 mm |
| 4 | `m_-77.75_164.25` | McMurdo Dry Valleys | 0.650 | 0.50 | 0.61 | 0.54 | 0.83 | 0.00 | none | -18.9 °C | 80 mm |
| 5 | `m_37.75_89.25` | Tibetan Plateau | 0.643 | 0.90 | 0.75 | 0.36 | 0.99 | 0.71 | Mar, Oct, Apr | -2.0 °C | 52 mm |
| 6 | `m_34.75_83.25` | Tibetan Plateau | 0.633 | 1.00 | 0.64 | 0.40 | 0.99 | 0.77 | Feb, Mar, Oct | -5.8 °C | 73 mm |
| 7 | `m_38.25_74.25` | Pamir and Karakoram | 0.620 | 0.77 | 0.66 | 0.38 | 0.97 | 0.70 | Oct, Mar, Sep | -3.7 °C | 70 mm |
| 8 | `m_81.25_-72.25` | Ellesmere or north-west Greenland | 0.603 | 0.81 | 0.45 | 0.53 | 0.92 | 0.00 | none | -17.4 °C | 129 mm |
| 9 | `m_-25.25_-69.25` | Altiplano and Puna | 0.599 | 0.95 | 1.00 | 0.22 | 1.00 | 0.95 | Jul, Jun, Aug | 10.6 °C | 19 mm |
| 10 | `m_-72.25_68.75` | Antarctica | 0.598 | 0.49 | 0.73 | 0.57 | 0.52 | 0.01 | Dec | -21.3 °C | 57 mm |

**Closest on all five factors**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.75` | Tibetan Plateau | 0.754 | 1.00 | 0.79 | 0.42 | 0.99 | 0.74 | Feb, Mar, Oct | -7.5 °C | 47 mm |
| 2 | `m_35.25_79.75` | Tibetan Plateau | 0.735 | 1.00 | 0.65 | 0.44 | 1.00 | 0.76 | Feb, Mar, Oct | -9.3 °C | 72 mm |
| 3 | `m_35.75_83.25` | Tibetan Plateau | 0.732 | 1.00 | 0.66 | 0.42 | 1.00 | 0.75 | Feb, Mar, Oct | -7.9 °C | 69 mm |
| 4 | `m_38.75_93.75` | Qaidam Basin | 0.726 | 1.00 | 0.90 | 0.32 | 1.00 | 0.69 | Mar, Oct, Apr | 0.9 °C | 34 mm |
| 5 | `m_-25.25_-69.25` | Altiplano and Puna | 0.720 | 0.95 | 1.00 | 0.22 | 1.00 | 0.95 | Jul, Jun, Aug | 10.6 °C | 19 mm |
| 6 | `m_-22.25_-68.25` | Altiplano and Puna | 0.710 | 0.92 | 0.83 | 0.29 | 0.90 | 0.92 | Jul, Jun, Aug | 4.4 °C | 42 mm |
| 7 | `m_37.75_89.75` | Tibetan Plateau | 0.701 | 0.99 | 0.74 | 0.34 | 0.96 | 0.71 | Mar, Oct, Apr | -0.5 °C | 55 mm |
| 8 | `m_32.75_82.75` | Tibetan Plateau | 0.690 | 1.00 | 0.56 | 0.35 | 0.99 | 0.81 | Oct, Feb, Mar | -1.0 °C | 93 mm |
| 9 | `m_37.75_74.25` | Pamir and Karakoram | 0.666 | 0.81 | 0.67 | 0.37 | 0.92 | 0.71 | Oct, Mar, Apr | -3.1 °C | 68 mm |
| 10 | `m_31.75_79.75` | Tibetan Plateau | 0.664 | 0.93 | 0.50 | 0.37 | 0.90 | 0.83 | Oct, Feb, Apr | -3.3 °C | 113 mm |

The closest square on all factors is `m_36.25_86.75` (Tibetan Plateau), with a score of 0.754.
There, Mars is 52.3 °C colder in the yearly mean.
The square gets 1.87 times 25 mm of precipitation a year.
Mars air pressure is 1.29 % of the square's.

### Nili Fossae

Caveats: it is not a climate match, and a score is a position on each factor's own scale, not a share of likeness.

**Closest by landscape (slopes and bare ground)**

37 ranked squares tie at the top score of 1.000, so their order here is not a ranking. Tied squares are listed by bare area, then by environment score.

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_19.75_18.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.09 | 1.00 | 0.91 | Jan, Dec, Feb | 21.9 °C | 14 mm |
| 2 | `m_20.25_36.75` | Sahara | 1.000 | 1.00 | 0.83 | 0.03 | 1.00 | 0.92 | Feb, Jan, Mar | 27.4 °C | 42 mm |
| 3 | `m_-21.75_-69.25` | Atacama Desert | 1.000 | 1.00 | 1.00 | 0.14 | 1.00 | 0.96 | Jul, Jun, Aug | 17.7 °C | 21 mm |
| 4 | `m_-24.75_-69.25` | Atacama Desert | 1.000 | 1.00 | 1.00 | 0.18 | 1.00 | 0.97 | Jul, Aug, May | 14.5 °C | 12 mm |
| 5 | `m_25.75_37.75` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.05 | 1.00 | 0.95 | Feb, Jan, Mar | 25.7 °C | 16 mm |
| 6 | `m_25.75_4.75` | Sahara | 1.000 | 1.00 | 0.76 | 0.06 | 1.00 | 0.95 | Jan, Feb, Nov | 24.5 °C | 52 mm |
| 7 | `m_26.25_58.25` | Arabian Desert | 1.000 | 1.00 | 0.57 | 0.06 | 1.00 | 0.94 | Feb, Nov, Oct | 24.8 °C | 92 mm |
| 8 | `m_27.25_33.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.08 | 1.00 | 0.92 | Feb, Mar, Nov | 22.7 °C | 8 mm |
| 9 | `m_27.75_62.25` | other | 1.000 | 1.00 | 0.59 | 0.08 | 1.00 | 0.91 | Feb, Oct, Nov | 23.1 °C | 85 mm |
| 10 | `m_32.75_55.75` | Iranian deserts (Lut, Kavir) | 1.000 | 1.00 | 0.71 | 0.12 | 1.00 | 0.80 | Feb, Oct, Mar | 19.2 °C | 59 mm |

**Closest by environment (dry, cold and bare)**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.699 | 0.66 | 0.80 | 0.43 | 1.00 | 0.73 | Mar, Oct, Apr | -7.3 °C | 45 mm |
| 2 | `m_38.75_93.75` | Qaidam Basin | 0.668 | 1.00 | 0.90 | 0.33 | 1.00 | 0.68 | Mar, Apr, May | 0.9 °C | 34 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.661 | 0.95 | 0.65 | 0.45 | 1.00 | 0.75 | Mar, Oct, Apr | -9.3 °C | 72 mm |
| 4 | `m_-77.75_164.25` | McMurdo Dry Valleys | 0.655 | 0.66 | 0.61 | 0.56 | 0.83 | 0.00 | none | -18.9 °C | 80 mm |
| 5 | `m_37.75_89.25` | Tibetan Plateau | 0.648 | 1.00 | 0.75 | 0.37 | 0.99 | 0.70 | Mar, Oct, Apr | -2.0 °C | 52 mm |
| 6 | `m_34.75_83.25` | Tibetan Plateau | 0.638 | 0.89 | 0.64 | 0.41 | 0.99 | 0.76 | Mar, Oct, Apr | -5.8 °C | 73 mm |
| 7 | `m_38.25_74.25` | Pamir and Karakoram | 0.625 | 0.92 | 0.66 | 0.38 | 0.97 | 0.69 | Oct, Mar, Sep | -3.7 °C | 70 mm |
| 8 | `m_81.25_-72.25` | Ellesmere or north-west Greenland | 0.608 | 0.98 | 0.45 | 0.54 | 0.92 | 0.00 | none | -17.4 °C | 129 mm |
| 9 | `m_-25.25_-69.25` | Altiplano and Puna | 0.604 | 1.00 | 1.00 | 0.22 | 1.00 | 0.96 | Jul, Aug, May | 10.6 °C | 19 mm |
| 10 | `m_-72.25_68.75` | Antarctica | 0.603 | 0.59 | 0.73 | 0.59 | 0.52 | 0.00 | none | -21.3 °C | 57 mm |

**Closest on all five factors**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.75_86.75` | Tibetan Plateau | 0.744 | 1.00 | 0.80 | 0.41 | 0.98 | 0.72 | Mar, Oct, Apr | -5.5 °C | 45 mm |
| 2 | `m_34.75_81.25` | Tibetan Plateau | 0.734 | 1.00 | 0.64 | 0.44 | 0.98 | 0.76 | Mar, Oct, Apr | -8.7 °C | 73 mm |
| 3 | `m_-22.75_-68.25` | Atacama Desert | 0.734 | 1.00 | 0.85 | 0.27 | 0.96 | 0.98 | Jul, Jun, Aug | 6.6 °C | 40 mm |
| 4 | `m_38.75_93.75` | Qaidam Basin | 0.726 | 1.00 | 0.90 | 0.33 | 1.00 | 0.68 | Mar, Apr, May | 0.9 °C | 34 mm |
| 5 | `m_-26.25_-69.25` | Atacama Desert | 0.715 | 1.00 | 0.87 | 0.23 | 1.00 | 0.94 | Aug, May, Sep | 9.9 °C | 37 mm |
| 6 | `m_37.75_90.25` | Tibetan Plateau | 0.702 | 1.00 | 0.74 | 0.35 | 0.95 | 0.70 | Mar, Oct, Apr | -0.5 °C | 55 mm |
| 7 | `m_37.75_74.25` | Pamir and Karakoram | 0.692 | 0.98 | 0.67 | 0.38 | 0.92 | 0.70 | Oct, Mar, Apr | -3.1 °C | 68 mm |
| 8 | `m_31.75_79.75` | Tibetan Plateau | 0.675 | 1.00 | 0.50 | 0.38 | 0.90 | 0.82 | Oct, Feb, Apr | -3.3 °C | 113 mm |
| 9 | `m_34.25_85.25` | Tibetan Plateau | 0.673 | 1.00 | 0.44 | 0.41 | 0.97 | 0.77 | Feb, Mar, Oct | -6.3 °C | 133 mm |
| 10 | `m_-19.75_-70.25` | Atacama Desert | 0.662 | 1.00 | 1.00 | 0.14 | 1.00 | 0.91 | Aug, Jun, Sep | 17.8 °C | 15 mm |

The closest square on all factors is `m_36.75_86.75` (Tibetan Plateau), with a score of 0.744.
There, Mars is 52.1 °C colder in the yearly mean.
The square gets 1.81 times 25 mm of precipitation a year.
Mars air pressure is 1.05 % of the square's.

### Acheron Fossae

Caveats: it is not a climate match, and a score is a position on each factor's own scale, not a share of likeness.

**Closest by landscape (slopes and bare ground)**

1,046 ranked squares tie at the top score of 1.000, so their order here is not a ranking. Tied squares are listed by bare area, then by environment score.

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_12.75_41.25` | Danakil Depression | 1.000 | 1.00 | 0.21 | 0.00 | 1.00 | 0.43 | Jan, Dec, Feb | 33.1 °C | 266 mm |
| 2 | `m_15.25_27.75` | Sahara | 1.000 | 1.00 | 0.66 | 0.05 | 1.00 | 0.48 | Jan, Dec, Feb | 24.8 °C | 70 mm |
| 3 | `m_15.75_24.75` | Sahara | 1.000 | 1.00 | 0.85 | 0.05 | 1.00 | 0.49 | Jan, Dec, Feb | 24.5 °C | 39 mm |
| 4 | `m_15.75_50.75` | Arabian Desert | 1.000 | 1.00 | 0.94 | 0.04 | 1.00 | 0.49 | Jan, Dec, Feb | 25.8 °C | 30 mm |
| 5 | `m_15.75_47.75` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.03 | 1.00 | 0.49 | Jan, Dec, Feb | 26.6 °C | 17 mm |
| 6 | `m_16.75_44.75` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.05 | 1.00 | 0.51 | Dec, Jan, Nov | 24.9 °C | 19 mm |
| 7 | `m_16.75_30.25` | Sahara | 1.000 | 1.00 | 0.84 | 0.03 | 1.00 | 0.51 | Jan, Dec, Feb | 27.1 °C | 40 mm |
| 8 | `m_17.25_53.25` | Arabian Desert | 1.000 | 1.00 | 0.51 | 0.03 | 1.00 | 0.52 | Jan, Dec, Feb | 26.3 °C | 110 mm |
| 9 | `m_17.75_22.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.04 | 1.00 | 0.53 | Jan, Dec, Feb | 25.8 °C | 17 mm |
| 10 | `m_17.75_36.75` | Sahara | 1.000 | 1.00 | 0.68 | 0.03 | 1.00 | 0.53 | Feb, Jan, Mar | 26.3 °C | 65 mm |

**Closest by environment (dry, cold and bare)**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.651 | 1.00 | 0.80 | 0.34 | 1.00 | 0.89 | Jan, Dec, Feb | -7.3 °C | 45 mm |
| 2 | `m_38.75_93.75` | Qaidam Basin | 0.622 | 1.00 | 0.90 | 0.27 | 1.00 | 0.93 | Jan, Dec, Feb | 0.9 °C | 34 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.615 | 1.00 | 0.65 | 0.36 | 1.00 | 0.88 | Dec, Jan, Nov | -9.3 °C | 72 mm |
| 4 | `m_-77.75_164.25` | McMurdo Dry Valleys | 0.610 | 0.62 | 0.61 | 0.45 | 0.83 | 0.21 | Nov, Dec, Jan | -18.9 °C | 80 mm |
| 5 | `m_37.75_89.25` | Tibetan Plateau | 0.604 | 1.00 | 0.75 | 0.29 | 0.99 | 0.92 | Jan, Dec, Feb | -2.0 °C | 52 mm |
| 6 | `m_34.75_83.25` | Tibetan Plateau | 0.594 | 1.00 | 0.64 | 0.33 | 0.99 | 0.86 | Jan, Dec, Feb | -5.8 °C | 73 mm |
| 7 | `m_38.25_74.25` | Pamir and Karakoram | 0.582 | 1.00 | 0.66 | 0.31 | 0.97 | 0.93 | Dec, Jan, Nov | -3.7 °C | 70 mm |
| 8 | `m_81.25_-72.25` | Ellesmere or north-west Greenland | 0.566 | 0.89 | 0.45 | 0.44 | 0.92 | 0.14 | May, Jun, Jul | -17.4 °C | 129 mm |
| 9 | `m_-25.25_-69.25` | Altiplano and Puna | 0.563 | 0.99 | 1.00 | 0.18 | 1.00 | 0.68 | Jul, Jun, Aug | 10.6 °C | 19 mm |
| 10 | `m_-72.25_68.75` | Antarctica | 0.562 | 0.66 | 0.73 | 0.47 | 0.52 | 0.32 | Oct, Feb, Jan | -21.3 °C | 57 mm |

**Closest on all five factors**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.756 | 1.00 | 0.80 | 0.34 | 1.00 | 0.89 | Jan, Dec, Feb | -7.3 °C | 45 mm |
| 2 | `m_38.75_93.75` | Qaidam Basin | 0.742 | 1.00 | 0.90 | 0.27 | 1.00 | 0.93 | Jan, Dec, Feb | 0.9 °C | 34 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.728 | 1.00 | 0.65 | 0.36 | 1.00 | 0.88 | Dec, Jan, Nov | -9.3 °C | 72 mm |
| 4 | `m_37.75_89.25` | Tibetan Plateau | 0.727 | 1.00 | 0.75 | 0.29 | 0.99 | 0.92 | Jan, Dec, Feb | -2.0 °C | 52 mm |
| 5 | `m_38.25_74.25` | Pamir and Karakoram | 0.713 | 1.00 | 0.66 | 0.31 | 0.97 | 0.93 | Dec, Jan, Nov | -3.7 °C | 70 mm |
| 6 | `m_34.75_83.25` | Tibetan Plateau | 0.711 | 1.00 | 0.64 | 0.33 | 0.99 | 0.86 | Jan, Dec, Feb | -5.8 °C | 73 mm |
| 7 | `m_41.25_90.25` | Taklamakan and Tarim Basin | 0.692 | 1.00 | 0.95 | 0.18 | 1.00 | 0.93 | Jan, Dec, Feb | 10.4 °C | 29 mm |
| 8 | `m_41.75_96.25` | Gobi Desert | 0.676 | 1.00 | 0.66 | 0.23 | 1.00 | 0.93 | Jan, Feb, Nov | 5.0 °C | 69 mm |
| 9 | `m_32.25_80.75` | Tibetan Plateau | 0.672 | 1.00 | 0.58 | 0.31 | 0.94 | 0.82 | Dec, Nov, Jan | -3.4 °C | 87 mm |
| 10 | `m_41.75_102.25` | Gobi Desert | 0.665 | 1.00 | 0.72 | 0.20 | 1.00 | 0.93 | Jan, Feb, Nov | 8.8 °C | 58 mm |

The closest square on all factors is `m_36.25_86.25` (Tibetan Plateau), with a score of 0.756.
There, Mars is 71.2 °C colder in the yearly mean.
The square gets 1.81 times 25 mm of precipitation a year.
Mars air pressure is 1.38 % of the square's.

### Hebrus Valles

Caveats: it is not a climate match, and a score is a position on each factor's own scale, not a share of likeness.

**Closest by landscape (slopes and bare ground)**

221 ranked squares tie at the top score of 1.000, so their order here is not a ranking. Tied squares are listed by bare area, then by environment score.

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_15.75_28.25` | Sahara | 1.000 | 1.00 | 0.76 | 0.05 | 1.00 | 0.87 | Jan, Dec, Feb | 25.9 °C | 52 mm |
| 2 | `m_15.75_11.25` | Sahara | 1.000 | 1.00 | 0.56 | 0.03 | 1.00 | 0.87 | Jan, Dec, Feb | 27.3 °C | 94 mm |
| 3 | `m_16.25_24.25` | Sahara | 1.000 | 1.00 | 0.96 | 0.07 | 1.00 | 0.88 | Jan, Dec, Feb | 24.0 °C | 28 mm |
| 4 | `m_18.25_22.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.05 | 1.00 | 0.92 | Jan, Dec, Feb | 25.5 °C | 8 mm |
| 5 | `m_18.25_9.75` | Sahara | 1.000 | 1.00 | 0.90 | 0.04 | 1.00 | 0.92 | Jan, Dec, Feb | 26.3 °C | 34 mm |
| 6 | `m_18.25_19.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.04 | 1.00 | 0.92 | Jan, Dec, Feb | 26.8 °C | 6 mm |
| 7 | `m_18.25_-8.25` | Sahara | 1.000 | 1.00 | 0.48 | 0.03 | 1.00 | 0.92 | Jan, Dec, Feb | 27.3 °C | 117 mm |
| 8 | `m_18.75_56.25` | Arabian Desert | 1.000 | 1.00 | 0.45 | 0.03 | 1.00 | 0.93 | Dec, Jan, Nov | 27.3 °C | 131 mm |
| 9 | `m_19.25_26.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.07 | 1.00 | 0.94 | Jan, Dec, Feb | 23.5 °C | 2 mm |
| 10 | `m_19.25_-13.25` | Sahara | 1.000 | 1.00 | 0.41 | 0.01 | 1.00 | 0.94 | Jan, Dec, Feb | 28.9 °C | 147 mm |

**Closest by environment (dry, cold and bare)**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.692 | 0.54 | 0.80 | 0.41 | 1.00 | 0.72 | Mar, Oct, Apr | -7.3 °C | 45 mm |
| 2 | `m_38.75_93.75` | Qaidam Basin | 0.661 | 0.42 | 0.90 | 0.32 | 1.00 | 0.66 | Mar, Apr, May | 0.9 °C | 34 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.654 | 0.69 | 0.65 | 0.43 | 1.00 | 0.74 | Mar, Oct, Apr | -9.3 °C | 72 mm |
| 4 | `m_-77.75_164.25` | McMurdo Dry Valleys | 0.648 | 0.14 | 0.61 | 0.54 | 0.83 | 0.00 | none | -18.9 °C | 80 mm |
| 5 | `m_37.75_89.25` | Tibetan Plateau | 0.642 | 0.57 | 0.75 | 0.35 | 0.99 | 0.68 | Mar, Apr, Sep | -2.0 °C | 52 mm |
| 6 | `m_34.75_83.25` | Tibetan Plateau | 0.631 | 0.45 | 0.64 | 0.40 | 0.99 | 0.75 | Mar, Oct, Apr | -5.8 °C | 73 mm |
| 7 | `m_38.25_74.25` | Pamir and Karakoram | 0.619 | 0.35 | 0.66 | 0.37 | 0.97 | 0.67 | Mar, Sep, Apr | -3.7 °C | 70 mm |
| 8 | `m_81.25_-72.25` | Ellesmere or north-west Greenland | 0.602 | 0.25 | 0.45 | 0.52 | 0.92 | 0.00 | none | -17.4 °C | 129 mm |
| 9 | `m_-25.25_-69.25` | Altiplano and Puna | 0.598 | 0.32 | 1.00 | 0.21 | 1.00 | 0.96 | Aug, May, Sep | 10.6 °C | 19 mm |
| 10 | `m_-72.25_68.75` | Antarctica | 0.597 | 0.16 | 0.73 | 0.57 | 0.52 | 0.00 | none | -21.3 °C | 57 mm |

**Closest on all five factors**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_38.75_92.75` | Qaidam Basin | 0.712 | 0.99 | 0.91 | 0.31 | 1.00 | 0.66 | Mar, Apr, May | 2.4 °C | 32 mm |
| 2 | `m_-23.25_-68.25` | Atacama Desert | 0.689 | 0.92 | 0.94 | 0.18 | 1.00 | 1.00 | Jul, Aug, May | 13.6 °C | 30 mm |
| 3 | `m_34.75_79.25` | Tibetan Plateau | 0.678 | 0.79 | 0.58 | 0.42 | 1.00 | 0.75 | Oct, Mar, Apr | -7.9 °C | 88 mm |
| 4 | `m_35.25_84.75` | Tibetan Plateau | 0.677 | 0.70 | 0.69 | 0.40 | 1.00 | 0.74 | Mar, Oct, Apr | -5.9 °C | 63 mm |
| 5 | `m_37.25_88.25` | Tibetan Plateau | 0.670 | 0.61 | 0.79 | 0.41 | 0.99 | 0.69 | Mar, Apr, Sep | -6.7 °C | 47 mm |
| 6 | `m_-20.25_-69.75` | Atacama Desert | 0.639 | 0.84 | 1.00 | 0.13 | 0.97 | 0.97 | Jul, Aug, Jun | 17.9 °C | 11 mm |
| 7 | `m_41.75_101.75` | Gobi Desert | 0.633 | 1.00 | 0.77 | 0.22 | 1.00 | 0.60 | Mar, Apr, May | 9.8 °C | 50 mm |
| 8 | `m_40.25_87.75` | Taklamakan and Tarim Basin | 0.626 | 1.00 | 0.83 | 0.18 | 1.00 | 0.63 | Mar, Apr, Sep | 13.4 °C | 41 mm |
| 9 | `m_27.75_40.25` | Arabian Desert | 0.622 | 1.00 | 0.99 | 0.10 | 1.00 | 0.90 | Feb, Mar, Apr | 20.6 °C | 26 mm |
| 10 | `m_25.25_25.75` | Sahara | 0.622 | 1.00 | 1.00 | 0.10 | 1.00 | 0.96 | Feb, Nov, Mar | 21.2 °C | 3 mm |

The closest square on all factors is `m_38.75_92.75` (Qaidam Basin), with a score of 0.712.
There, Mars is 62.8 °C colder in the yearly mean.
The square gets 1.30 times 25 mm of precipitation a year.
Mars air pressure is 1.10 % of the square's.

### Newton crater

Caveats: it is not a climate match, and a score is a position on each factor's own scale, not a share of likeness.

**Closest by landscape (slopes and bare ground)**

122 ranked squares tie at the top score of 1.000, so their order here is not a ranking. Tied squares are listed by bare area, then by environment score.

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_15.75_50.75` | Arabian Desert | 1.000 | 1.00 | 0.94 | 0.04 | 1.00 | 0.47 | Jan, Dec, Feb | 25.8 °C | 30 mm |
| 2 | `m_16.75_44.75` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.05 | 1.00 | 0.49 | Dec, Jan, Nov | 24.9 °C | 19 mm |
| 3 | `m_17.75_36.75` | Sahara | 1.000 | 1.00 | 0.68 | 0.04 | 1.00 | 0.51 | Feb, Jan, Mar | 26.3 °C | 65 mm |
| 4 | `m_18.75_9.25` | Sahara | 1.000 | 1.00 | 0.75 | 0.05 | 1.00 | 0.53 | Jan, Dec, Feb | 25.0 °C | 54 mm |
| 5 | `m_-18.75_12.75` | Namib Desert | 1.000 | 1.00 | 0.30 | 0.09 | 1.00 | 0.53 | Aug, Sep, Jul | 20.8 °C | 204 mm |
| 6 | `m_20.25_19.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.06 | 1.00 | 0.56 | Jan, Dec, Feb | 23.8 °C | 4 mm |
| 7 | `m_21.25_16.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.06 | 1.00 | 0.58 | Jan, Dec, Feb | 23.5 °C | 18 mm |
| 8 | `m_21.25_36.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.02 | 1.00 | 0.58 | Jan, Feb, Dec | 27.5 °C | 20 mm |
| 9 | `m_22.75_6.25` | Sahara | 1.000 | 1.00 | 0.51 | 0.08 | 1.00 | 0.61 | Jan, Dec, Feb | 21.7 °C | 107 mm |
| 10 | `m_-22.75_-69.25` | Atacama Desert | 1.000 | 1.00 | 1.00 | 0.12 | 1.00 | 0.61 | Jul, Jun, Aug | 17.7 °C | 13 mm |

**Closest by environment (dry, cold and bare)**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.662 | 1.00 | 0.80 | 0.36 | 1.00 | 0.88 | Jan, Dec, Feb | -7.3 °C | 45 mm |
| 2 | `m_38.75_93.75` | Qaidam Basin | 0.633 | 0.91 | 0.90 | 0.28 | 1.00 | 0.93 | Jan, Dec, Feb | 0.9 °C | 34 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.626 | 0.75 | 0.65 | 0.38 | 1.00 | 0.86 | Dec, Jan, Nov | -9.3 °C | 72 mm |
| 4 | `m_-77.75_164.25` | McMurdo Dry Valleys | 0.621 | 0.35 | 0.61 | 0.47 | 0.83 | 0.23 | Nov, Dec, Jan | -18.9 °C | 80 mm |
| 5 | `m_37.75_89.25` | Tibetan Plateau | 0.614 | 0.73 | 0.75 | 0.31 | 0.99 | 0.91 | Jan, Dec, Feb | -2.0 °C | 52 mm |
| 6 | `m_34.75_83.25` | Tibetan Plateau | 0.604 | 1.00 | 0.64 | 0.35 | 0.99 | 0.85 | Jan, Dec, Feb | -5.8 °C | 73 mm |
| 7 | `m_38.25_74.25` | Pamir and Karakoram | 0.592 | 0.60 | 0.66 | 0.33 | 0.97 | 0.92 | Dec, Jan, Nov | -3.7 °C | 70 mm |
| 8 | `m_81.25_-72.25` | Ellesmere or north-west Greenland | 0.576 | 0.56 | 0.45 | 0.46 | 0.92 | 0.16 | May, Jun, Jul | -17.4 °C | 129 mm |
| 9 | `m_-25.25_-69.25` | Altiplano and Puna | 0.572 | 0.71 | 1.00 | 0.19 | 1.00 | 0.66 | Jul, Jun, Aug | 10.6 °C | 19 mm |
| 10 | `m_-72.25_68.75` | Antarctica | 0.571 | 0.40 | 0.73 | 0.50 | 0.52 | 0.34 | Oct, Feb, Jan | -21.3 °C | 57 mm |

**Closest on all five factors**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.761 | 1.00 | 0.80 | 0.36 | 1.00 | 0.88 | Jan, Dec, Feb | -7.3 °C | 45 mm |
| 2 | `m_38.75_93.75` | Qaidam Basin | 0.735 | 0.91 | 0.90 | 0.28 | 1.00 | 0.93 | Jan, Dec, Feb | 0.9 °C | 34 mm |
| 3 | `m_35.75_82.75` | Tibetan Plateau | 0.728 | 1.00 | 0.66 | 0.36 | 0.99 | 0.87 | Jan, Dec, Nov | -7.1 °C | 69 mm |
| 4 | `m_37.25_90.25` | Tibetan Plateau | 0.698 | 0.87 | 0.71 | 0.31 | 0.95 | 0.90 | Jan, Dec, Feb | -2.3 °C | 59 mm |
| 5 | `m_41.25_89.75` | Taklamakan and Tarim Basin | 0.695 | 0.97 | 0.95 | 0.19 | 1.00 | 0.93 | Jan, Dec, Feb | 10.4 °C | 29 mm |
| 6 | `m_34.75_79.25` | Tibetan Plateau | 0.688 | 0.85 | 0.58 | 0.37 | 1.00 | 0.85 | Dec, Jan, Nov | -7.9 °C | 88 mm |
| 7 | `m_44.25_97.75` | Gobi Desert | 0.680 | 1.00 | 0.70 | 0.23 | 1.00 | 0.89 | Jan, Feb, Nov | 6.1 °C | 60 mm |
| 8 | `m_41.25_96.25` | Gobi Desert | 0.672 | 0.94 | 0.64 | 0.24 | 1.00 | 0.93 | Jan, Dec, Feb | 4.8 °C | 74 mm |
| 9 | `m_32.75_82.75` | Tibetan Plateau | 0.671 | 1.00 | 0.56 | 0.30 | 0.99 | 0.81 | Dec, Nov, Jan | -1.0 °C | 93 mm |
| 10 | `m_43.25_101.75` | Gobi Desert | 0.662 | 1.00 | 0.60 | 0.24 | 0.96 | 0.91 | Jan, Feb, Nov | 5.1 °C | 84 mm |

The closest square on all factors is `m_36.25_86.25` (Tibetan Plateau), with a score of 0.761.
There, Mars is 65.9 °C colder in the yearly mean.
The square gets 1.81 times 25 mm of precipitation a year.
Mars air pressure is 1.17 % of the square's.

### Zephyria Planum hills ('Sea Urchins')

Caveats: it is not a climate match, and a score is a position on each factor's own scale, not a share of likeness.

**Closest by landscape (slopes and bare ground)**

560 ranked squares tie at the top score of 1.000, so their order here is not a ranking. Tied squares are listed by bare area, then by environment score.

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_15.75_47.25` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.03 | 1.00 | 1.00 | Oct, Mar, Apr | 26.6 °C | 17 mm |
| 2 | `m_16.25_24.25` | Sahara | 1.000 | 1.00 | 0.96 | 0.06 | 1.00 | 1.00 | Mar, Oct, Apr | 24.0 °C | 28 mm |
| 3 | `m_16.25_27.25` | Sahara | 1.000 | 1.00 | 0.87 | 0.05 | 1.00 | 1.00 | Mar, Apr, Oct | 25.0 °C | 37 mm |
| 4 | `m_17.25_31.25` | Sahara | 1.000 | 1.00 | 0.96 | 0.02 | 1.00 | 1.00 | Mar, Apr | 28.3 °C | 28 mm |
| 5 | `m_17.75_9.75` | Sahara | 1.000 | 1.00 | 0.78 | 0.04 | 1.00 | 1.00 | Mar, Oct, Apr | 26.5 °C | 48 mm |
| 6 | `m_17.75_18.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.02 | 1.00 | 1.00 | Mar, Oct, Apr | 27.7 °C | 7 mm |
| 7 | `m_18.25_45.25` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.04 | 1.00 | 1.00 | Mar, Apr, Sep | 25.7 °C | 17 mm |
| 8 | `m_18.25_21.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.04 | 1.00 | 1.00 | Mar, Apr | 25.8 °C | 10 mm |
| 9 | `m_18.25_-8.25` | Sahara | 1.000 | 1.00 | 0.48 | 0.03 | 1.00 | 1.00 | Mar, Apr | 27.3 °C | 117 mm |
| 10 | `m_18.25_51.25` | Arabian Desert | 1.000 | 1.00 | 0.90 | 0.01 | 1.00 | 1.00 | Mar | 28.6 °C | 34 mm |

**Closest by environment (dry, cold and bare)**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.675 | 0.52 | 0.80 | 0.38 | 1.00 | 0.52 | Apr, May, Aug | -7.3 °C | 45 mm |
| 2 | `m_38.75_93.75` | Qaidam Basin | 0.645 | 0.35 | 0.90 | 0.30 | 1.00 | 0.42 | May, Aug, Jun | 0.9 °C | 34 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.638 | 0.63 | 0.65 | 0.40 | 1.00 | 0.56 | Apr, May, Jul | -9.3 °C | 72 mm |
| 4 | `m_-77.75_164.25` | McMurdo Dry Valleys | 0.633 | 0.10 | 0.61 | 0.50 | 0.83 | 0.00 | none | -18.9 °C | 80 mm |
| 5 | `m_37.75_89.25` | Tibetan Plateau | 0.626 | 0.49 | 0.75 | 0.33 | 0.99 | 0.46 | May, Aug, Jun | -2.0 °C | 52 mm |
| 6 | `m_34.75_83.25` | Tibetan Plateau | 0.616 | 0.44 | 0.64 | 0.37 | 0.99 | 0.57 | Apr, May, Jun | -5.8 °C | 73 mm |
| 7 | `m_38.25_74.25` | Pamir and Karakoram | 0.604 | 0.29 | 0.66 | 0.35 | 0.97 | 0.44 | May, Aug, Jun | -3.7 °C | 70 mm |
| 8 | `m_81.25_-72.25` | Ellesmere or north-west Greenland | 0.587 | 0.18 | 0.45 | 0.49 | 0.92 | 0.00 | none | -17.4 °C | 129 mm |
| 9 | `m_-25.25_-69.25` | Altiplano and Puna | 0.583 | 0.25 | 1.00 | 0.20 | 1.00 | 0.93 | Oct, Nov, Mar | 10.6 °C | 19 mm |
| 10 | `m_-72.25_68.75` | Antarctica | 0.582 | 0.11 | 0.73 | 0.53 | 0.52 | 0.00 | none | -21.3 °C | 57 mm |

**Closest on all five factors**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_-23.25_-68.25` | Atacama Desert | 0.652 | 0.75 | 0.94 | 0.17 | 1.00 | 1.00 | Sep, Oct, Nov | 13.6 °C | 30 mm |
| 2 | `m_38.25_93.25` | Qaidam Basin | 0.641 | 0.98 | 0.94 | 0.27 | 1.00 | 0.44 | May, Aug, Jun | 4.0 °C | 30 mm |
| 3 | `m_35.25_85.25` | Tibetan Plateau | 0.636 | 0.73 | 0.69 | 0.37 | 0.99 | 0.56 | Apr, May, Aug | -5.9 °C | 63 mm |
| 4 | `m_34.75_79.25` | Tibetan Plateau | 0.630 | 0.77 | 0.58 | 0.39 | 1.00 | 0.57 | Apr, May, Jun | -7.9 °C | 88 mm |
| 5 | `m_-20.25_-69.75` | Atacama Desert | 0.626 | 0.80 | 1.00 | 0.12 | 0.97 | 1.00 | Sep, Oct, Nov | 17.9 °C | 11 mm |
| 6 | `m_37.25_89.75` | Tibetan Plateau | 0.619 | 0.80 | 0.71 | 0.33 | 1.00 | 0.48 | May, Aug, Jun | -2.3 °C | 59 mm |
| 7 | `m_24.25_26.75` | Sahara | 0.617 | 0.95 | 1.00 | 0.10 | 1.00 | 0.97 | Mar, Apr, May | 20.5 °C | 3 mm |
| 8 | `m_23.25_12.25` | Sahara | 0.614 | 1.00 | 1.00 | 0.09 | 1.00 | 1.00 | Mar, Apr, Sep | 21.5 °C | 20 mm |
| 9 | `m_23.75_21.75` | Sahara | 0.608 | 1.00 | 1.00 | 0.08 | 1.00 | 0.99 | Mar, Apr, May | 21.8 °C | 2 mm |
| 10 | `m_27.75_40.25` | Arabian Desert | 0.604 | 1.00 | 0.99 | 0.10 | 1.00 | 0.84 | Apr, May, Sep | 20.6 °C | 26 mm |

The closest square on all factors is `m_-23.25_-68.25` (Atacama Desert), with a score of 0.652.
There, Mars is 81.0 °C colder in the yearly mean.
The square gets 1.19 times 25 mm of precipitation a year.
Mars air pressure is 1.01 % of the square's.

### Cerberus (west of Zunil crater)

Caveats: it is not a climate match, and a score is a position on each factor's own scale, not a share of likeness.

**Closest by landscape (slopes and bare ground)**

28 ranked squares tie at the top score of 1.000, so their order here is not a ranking. Tied squares are listed by bare area, then by environment score.

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_14.25_40.25` | Danakil Depression | 1.000 | 1.00 | 0.14 | 0.01 | 1.00 | 1.00 | Feb, Nov, Mar | 29.2 °C | 331 mm |
| 2 | `m_21.75_-10.75` | Sahara | 1.000 | 1.00 | 0.89 | 0.05 | 1.00 | 1.00 | Feb, Mar, Apr | 25.5 °C | 35 mm |
| 3 | `m_23.25_18.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.07 | 1.00 | 1.00 | Mar, Oct, Apr | 24.0 °C | 6 mm |
| 4 | `m_24.75_6.25` | Sahara | 1.000 | 1.00 | 0.74 | 0.08 | 1.00 | 0.96 | Mar, Apr, Oct | 22.7 °C | 54 mm |
| 5 | `m_-24.75_-67.75` | Altiplano and Puna | 1.000 | 1.00 | 0.01 | 0.26 | 1.00 | 0.96 | Sep, Oct, Apr | 6.4 °C | 484 mm |
| 6 | `m_27.75_64.25` | other | 1.000 | 1.00 | 0.62 | 0.06 | 1.00 | 0.88 | Mar, Apr, Sep | 24.9 °C | 79 mm |
| 7 | `m_28.75_-7.75` | Sahara | 1.000 | 1.00 | 0.70 | 0.07 | 1.00 | 0.85 | Mar, Apr, May | 23.7 °C | 62 mm |
| 8 | `m_30.25_27.75` | Sahara | 1.000 | 1.00 | 0.70 | 0.11 | 1.00 | 0.81 | Mar, Apr, May | 19.9 °C | 62 mm |
| 9 | `m_30.75_62.25` | other | 1.000 | 1.00 | 0.79 | 0.08 | 1.00 | 0.79 | Mar, Apr, Sep | 22.6 °C | 47 mm |
| 10 | `m_31.25_57.25` | Iranian deserts (Lut, Kavir) | 1.000 | 1.00 | 0.54 | 0.07 | 1.00 | 0.78 | Mar, Apr, Sep | 23.4 °C | 98 mm |

**Closest by environment (dry, cold and bare)**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.687 | 0.63 | 0.80 | 0.40 | 1.00 | 0.64 | Apr, Sep, May | -7.3 °C | 45 mm |
| 2 | `m_38.75_93.75` | Qaidam Basin | 0.657 | 0.97 | 0.90 | 0.32 | 1.00 | 0.56 | Apr, May, Aug | 0.9 °C | 34 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.649 | 1.00 | 0.65 | 0.43 | 1.00 | 0.66 | Apr, Sep, May | -9.3 °C | 72 mm |
| 4 | `m_-77.75_164.25` | McMurdo Dry Valleys | 0.644 | 0.56 | 0.61 | 0.53 | 0.83 | 0.00 | none | -18.9 °C | 80 mm |
| 5 | `m_37.75_89.25` | Tibetan Plateau | 0.637 | 1.00 | 0.75 | 0.35 | 0.99 | 0.59 | Apr, Sep, May | -2.0 °C | 52 mm |
| 6 | `m_34.75_83.25` | Tibetan Plateau | 0.627 | 0.73 | 0.64 | 0.39 | 0.99 | 0.68 | Apr, May, Sep | -5.8 °C | 73 mm |
| 7 | `m_38.25_74.25` | Pamir and Karakoram | 0.614 | 0.88 | 0.66 | 0.37 | 0.97 | 0.58 | Apr, May, Aug | -3.7 °C | 70 mm |
| 8 | `m_81.25_-72.25` | Ellesmere or north-west Greenland | 0.598 | 0.76 | 0.45 | 0.51 | 0.92 | 0.00 | none | -17.4 °C | 129 mm |
| 9 | `m_-25.25_-69.25` | Altiplano and Puna | 0.594 | 0.85 | 1.00 | 0.21 | 1.00 | 0.95 | Sep, Apr, Oct | 10.6 °C | 19 mm |
| 10 | `m_-72.25_68.75` | Antarctica | 0.593 | 0.58 | 0.73 | 0.56 | 0.52 | 0.00 | none | -21.3 °C | 57 mm |

**Closest on all five factors**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_37.25_88.25` | Tibetan Plateau | 0.715 | 0.99 | 0.79 | 0.40 | 0.99 | 0.61 | Apr, Sep, May | -6.7 °C | 47 mm |
| 2 | `m_35.25_79.75` | Tibetan Plateau | 0.711 | 1.00 | 0.65 | 0.43 | 1.00 | 0.66 | Apr, Sep, May | -9.3 °C | 72 mm |
| 3 | `m_-22.75_-68.25` | Atacama Desert | 0.702 | 0.82 | 0.85 | 0.25 | 0.96 | 1.00 | Sep, Apr, Oct | 6.6 °C | 40 mm |
| 4 | `m_-26.25_-69.25` | Atacama Desert | 0.699 | 0.96 | 0.87 | 0.22 | 1.00 | 0.92 | Sep, Oct, Nov | 9.9 °C | 37 mm |
| 5 | `m_38.75_93.25` | Qaidam Basin | 0.689 | 0.97 | 0.94 | 0.30 | 1.00 | 0.56 | Apr, May, Aug | 2.3 °C | 30 mm |
| 6 | `m_36.25_83.75` | Tibetan Plateau | 0.678 | 0.90 | 0.69 | 0.36 | 1.00 | 0.64 | Apr, Sep, May | -3.6 °C | 64 mm |
| 7 | `m_33.25_82.25` | Tibetan Plateau | 0.677 | 0.90 | 0.59 | 0.37 | 0.99 | 0.72 | Apr, May, Sep | -4.6 °C | 86 mm |
| 8 | `m_-19.25_-70.25` | Atacama Desert | 0.652 | 0.89 | 1.00 | 0.13 | 0.99 | 1.00 | Aug, Sep, Oct | 17.8 °C | 20 mm |
| 9 | `m_38.25_74.25` | Pamir and Karakoram | 0.652 | 0.88 | 0.66 | 0.37 | 0.97 | 0.58 | Apr, May, Aug | -3.7 °C | 70 mm |
| 10 | `m_28.75_33.75` | Sinai, Negev and Wadi Rum | 0.624 | 0.90 | 0.99 | 0.13 | 1.00 | 0.85 | Mar, Apr, May | 18.4 °C | 26 mm |

The closest square on all factors is `m_37.25_88.25` (Tibetan Plateau), with a score of 0.715.
There, Mars is 55.6 °C colder in the yearly mean.
The square gets 1.88 times 25 mm of precipitation a year.
Mars air pressure is 1.27 % of the square's.

### Amazonis Planitia mid-latitude ice

Caveats: it is not a climate match, and a score is a position on each factor's own scale, not a share of likeness.

**Closest by landscape (slopes and bare ground)**

157 ranked squares tie at the top score of 1.000, so their order here is not a ranking. Tied squares are listed by bare area, then by environment score.

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_16.75_11.25` | Sahara | 1.000 | 1.00 | 0.72 | 0.03 | 1.00 | 0.38 | Jan, Dec, Feb | 26.6 °C | 58 mm |
| 2 | `m_17.25_27.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.04 | 1.00 | 0.39 | Jan, Dec, Feb | 25.9 °C | 14 mm |
| 3 | `m_17.75_20.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.03 | 1.00 | 0.40 | Jan, Dec, Feb | 26.9 °C | 15 mm |
| 4 | `m_17.75_48.25` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.02 | 1.00 | 0.40 | Jan, Dec, Feb | 27.8 °C | 21 mm |
| 5 | `m_18.75_31.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.01 | 1.00 | 0.42 | Jan, Dec, Feb | 28.4 °C | 5 mm |
| 6 | `m_18.75_52.25` | Arabian Desert | 1.000 | 1.00 | 0.80 | 0.01 | 1.00 | 0.42 | Jan, Dec, Feb | 29.0 °C | 45 mm |
| 7 | `m_19.25_-1.25` | Sahara | 1.000 | 1.00 | 0.65 | 0.01 | 1.00 | 0.43 | Jan, Dec, Feb | 28.6 °C | 70 mm |
| 8 | `m_19.75_45.75` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.02 | 1.00 | 0.44 | Jan, Dec, Feb | 27.3 °C | 10 mm |
| 9 | `m_19.75_15.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.02 | 1.00 | 0.44 | Jan, Dec, Feb | 27.4 °C | 15 mm |
| 10 | `m_19.75_34.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.01 | 1.00 | 0.44 | Jan, Dec, Feb | 29.0 °C | 13 mm |

**Closest by environment (dry, cold and bare)**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.651 | 0.24 | 0.80 | 0.34 | 1.00 | 0.77 | Jan, Dec, Feb | -7.3 °C | 45 mm |
| 2 | `m_38.75_93.75` | Qaidam Basin | 0.623 | 0.13 | 0.90 | 0.27 | 1.00 | 0.82 | Jan, Dec, Feb | 0.9 °C | 34 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.616 | 0.36 | 0.65 | 0.36 | 1.00 | 0.75 | Dec, Jan, Nov | -9.3 °C | 72 mm |
| 4 | `m_-77.75_164.25` | McMurdo Dry Valleys | 0.610 | 0.01 | 0.61 | 0.45 | 0.83 | 0.34 | Oct, Nov, Dec | -18.9 °C | 80 mm |
| 5 | `m_37.75_89.25` | Tibetan Plateau | 0.604 | 0.26 | 0.75 | 0.30 | 0.99 | 0.80 | Jan, Dec, Feb | -2.0 °C | 52 mm |
| 6 | `m_34.75_83.25` | Tibetan Plateau | 0.594 | 0.16 | 0.64 | 0.33 | 0.99 | 0.74 | Jan, Dec, Feb | -5.8 °C | 73 mm |
| 7 | `m_38.25_74.25` | Pamir and Karakoram | 0.582 | 0.12 | 0.66 | 0.31 | 0.97 | 0.81 | Dec, Jan, Nov | -3.7 °C | 70 mm |
| 8 | `m_81.25_-72.25` | Ellesmere or north-west Greenland | 0.566 | 0.04 | 0.45 | 0.44 | 0.92 | 0.27 | May, Jun, Jul | -17.4 °C | 129 mm |
| 9 | `m_-25.25_-69.25` | Altiplano and Puna | 0.563 | 0.06 | 1.00 | 0.18 | 1.00 | 0.55 | Jul, Jun, Aug | 10.6 °C | 19 mm |
| 10 | `m_-72.25_68.75` | Antarctica | 0.562 | 0.00 | 0.73 | 0.47 | 0.52 | 0.45 | Mar, Oct, Feb | -21.3 °C | 57 mm |

**Closest on all five factors**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_38.25_92.25` | Qaidam Basin | 0.684 | 0.84 | 0.92 | 0.24 | 1.00 | 0.81 | Jan, Dec, Feb | 4.2 °C | 32 mm |
| 2 | `m_41.75_101.75` | Gobi Desert | 0.647 | 0.91 | 0.77 | 0.19 | 1.00 | 0.88 | Jan, Dec, Feb | 9.8 °C | 50 mm |
| 3 | `m_39.25_86.25` | Taklamakan and Tarim Basin | 0.642 | 1.00 | 0.84 | 0.16 | 1.00 | 0.83 | Jan, Dec, Feb | 13.1 °C | 40 mm |
| 4 | `m_43.25_57.25` | Karakum and Kyzylkum | 0.611 | 1.00 | 0.57 | 0.17 | 1.00 | 0.91 | Feb, Jan, Dec | 12.0 °C | 92 mm |
| 5 | `m_41.75_62.75` | Karakum and Kyzylkum | 0.609 | 0.96 | 0.68 | 0.15 | 1.00 | 0.88 | Jan, Dec, Nov | 14.0 °C | 66 mm |
| 6 | `m_37.25_81.75` | Taklamakan and Tarim Basin | 0.609 | 0.98 | 0.72 | 0.15 | 0.97 | 0.79 | Jan, Dec, Feb | 13.2 °C | 58 mm |
| 7 | `m_44.75_104.25` | Gobi Desert | 0.602 | 0.76 | 0.47 | 0.24 | 1.00 | 0.93 | Jan, Dec, Feb | 4.4 °C | 121 mm |
| 8 | `m_35.25_85.25` | Tibetan Plateau | 0.598 | 0.45 | 0.69 | 0.33 | 0.99 | 0.75 | Jan, Dec, Feb | -5.9 °C | 63 mm |
| 9 | `m_43.25_107.75` | Gobi Desert | 0.594 | 0.86 | 0.46 | 0.21 | 1.00 | 0.91 | Jan, Dec, Feb | 7.3 °C | 127 mm |
| 10 | `m_39.75_105.75` | Gobi Desert | 0.593 | 0.98 | 0.45 | 0.20 | 1.00 | 0.84 | Jan, Dec, Feb | 8.6 °C | 129 mm |

The closest square on all factors is `m_38.25_92.25` (Qaidam Basin), with a score of 0.684.
There, Mars is 82.6 °C colder in the yearly mean.
The square gets 1.27 times 25 mm of precipitation a year.
Mars air pressure is 1.14 % of the square's.

### Western Noachis Terra chloride deposits

Caveats: it is not a climate match, and a score is a position on each factor's own scale, not a share of likeness.

**Closest by landscape (slopes and bare ground)**

208 ranked squares tie at the top score of 1.000, so their order here is not a ranking. Tied squares are listed by bare area, then by environment score.

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_16.25_47.75` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.04 | 1.00 | 0.55 | Jan, Dec, Feb | 25.7 °C | 21 mm |
| 2 | `m_16.25_51.25` | Arabian Desert | 1.000 | 1.00 | 0.74 | 0.04 | 1.00 | 0.55 | Jan, Dec, Feb | 26.3 °C | 55 mm |
| 3 | `m_17.75_23.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.05 | 1.00 | 0.58 | Jan, Dec, Feb | 24.6 °C | 10 mm |
| 4 | `m_18.75_43.75` | Arabian Desert | 1.000 | 1.00 | 0.85 | 0.05 | 1.00 | 0.60 | Dec, Jan, Nov | 24.4 °C | 39 mm |
| 5 | `m_18.75_36.25` | Sahara | 1.000 | 1.00 | 0.79 | 0.03 | 1.00 | 0.60 | Jan, Feb, Mar | 27.2 °C | 46 mm |
| 6 | `m_19.25_19.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.04 | 1.00 | 0.61 | Jan, Dec, Feb | 25.8 °C | 5 mm |
| 7 | `m_19.25_-12.75` | Sahara | 1.000 | 1.00 | 0.49 | 0.02 | 1.00 | 0.61 | Jan, Dec, Feb | 28.1 °C | 114 mm |
| 8 | `m_19.75_8.75` | Sahara | 1.000 | 1.00 | 0.99 | 0.06 | 1.00 | 0.62 | Jan, Dec, Feb | 23.9 °C | 26 mm |
| 9 | `m_20.25_16.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.04 | 1.00 | 0.63 | Jan, Dec, Feb | 26.4 °C | 19 mm |
| 10 | `m_13.25_40.75` | Danakil Depression | 1.000 | 1.00 | 0.17 | 0.00 | 1.00 | 0.49 | Jan, Dec | 33.6 °C | 296 mm |

**Closest by environment (dry, cold and bare)**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.663 | 0.95 | 0.80 | 0.36 | 1.00 | 0.93 | Jan, Dec, Feb | -7.3 °C | 45 mm |
| 2 | `m_38.75_93.75` | Qaidam Basin | 0.634 | 0.63 | 0.90 | 0.28 | 1.00 | 0.93 | Jan, Dec, Feb | 0.9 °C | 34 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.626 | 0.78 | 0.65 | 0.38 | 1.00 | 0.93 | Dec, Jan, Nov | -9.3 °C | 72 mm |
| 4 | `m_-77.75_164.25` | McMurdo Dry Valleys | 0.621 | 0.23 | 0.61 | 0.48 | 0.83 | 0.16 | Nov, Dec, Jan | -18.9 °C | 80 mm |
| 5 | `m_37.75_89.25` | Tibetan Plateau | 0.615 | 0.56 | 0.75 | 0.31 | 0.99 | 0.93 | Jan, Dec, Feb | -2.0 °C | 52 mm |
| 6 | `m_34.75_83.25` | Tibetan Plateau | 0.605 | 0.78 | 0.64 | 0.35 | 0.99 | 0.92 | Jan, Dec, Feb | -5.8 °C | 73 mm |
| 7 | `m_38.25_74.25` | Pamir and Karakoram | 0.593 | 0.48 | 0.66 | 0.33 | 0.97 | 0.93 | Dec, Jan, Nov | -3.7 °C | 70 mm |
| 8 | `m_81.25_-72.25` | Ellesmere or north-west Greenland | 0.576 | 0.40 | 0.45 | 0.46 | 0.92 | 0.09 | May, Jun, Jul | -17.4 °C | 129 mm |
| 9 | `m_-25.25_-69.25` | Altiplano and Puna | 0.573 | 0.49 | 1.00 | 0.19 | 1.00 | 0.73 | Jul, Jun, Aug | 10.6 °C | 19 mm |
| 10 | `m_-72.25_68.75` | Antarctica | 0.572 | 0.27 | 0.73 | 0.50 | 0.52 | 0.27 | Feb, Jan, Dec | -21.3 °C | 57 mm |

**Closest on all five factors**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.762 | 0.95 | 0.80 | 0.36 | 1.00 | 0.93 | Jan, Dec, Feb | -7.3 °C | 45 mm |
| 2 | `m_35.25_82.75` | Tibetan Plateau | 0.742 | 1.00 | 0.66 | 0.37 | 0.98 | 0.93 | Jan, Dec, Nov | -8.5 °C | 69 mm |
| 3 | `m_37.25_89.75` | Tibetan Plateau | 0.730 | 1.00 | 0.71 | 0.31 | 1.00 | 0.93 | Jan, Dec, Feb | -2.3 °C | 59 mm |
| 4 | `m_38.25_93.25` | Qaidam Basin | 0.730 | 0.94 | 0.94 | 0.25 | 1.00 | 0.93 | Jan, Dec, Feb | 4.0 °C | 30 mm |
| 5 | `m_34.75_79.25` | Tibetan Plateau | 0.712 | 0.93 | 0.58 | 0.37 | 1.00 | 0.92 | Dec, Jan, Nov | -7.9 °C | 88 mm |
| 6 | `m_41.25_90.25` | Taklamakan and Tarim Basin | 0.689 | 0.97 | 0.95 | 0.19 | 1.00 | 0.88 | Jan, Feb, Nov | 10.4 °C | 29 mm |
| 7 | `m_41.75_95.75` | Gobi Desert | 0.674 | 1.00 | 0.68 | 0.23 | 1.00 | 0.88 | Feb, Mar, Nov | 5.9 °C | 66 mm |
| 8 | `m_44.25_97.25` | Gobi Desert | 0.670 | 0.99 | 0.70 | 0.23 | 1.00 | 0.83 | Feb, Mar, Oct | 6.1 °C | 60 mm |
| 9 | `m_39.75_86.75` | Taklamakan and Tarim Basin | 0.660 | 1.00 | 0.84 | 0.16 | 1.00 | 0.91 | Jan, Feb, Nov | 13.2 °C | 40 mm |
| 10 | `m_40.75_102.25` | Gobi Desert | 0.657 | 0.98 | 0.69 | 0.20 | 1.00 | 0.89 | Jan, Feb, Nov | 9.2 °C | 64 mm |

The closest square on all factors is `m_36.25_86.25` (Tibetan Plateau), with a score of 0.762.
There, Mars is 65.5 °C colder in the yearly mean.
The square gets 1.81 times 25 mm of precipitation a year.
Mars air pressure is 0.93 % of the square's.

### South of Valles Marineris (equatorial site)

Caveats: it is not a climate match, and a score is a position on each factor's own scale, not a share of likeness.

**Closest by landscape (slopes and bare ground)**

305 ranked squares tie at the top score of 1.000, so their order here is not a ranking. Tied squares are listed by bare area, then by environment score.

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_12.75_41.25` | Danakil Depression | 1.000 | 1.00 | 0.21 | 0.00 | 1.00 | 0.82 | Jan, Dec, Feb | 33.1 °C | 266 mm |
| 2 | `m_15.75_25.25` | Sahara | 1.000 | 1.00 | 0.85 | 0.06 | 1.00 | 0.89 | Jan, Dec, Feb | 24.5 °C | 39 mm |
| 3 | `m_15.75_50.75` | Arabian Desert | 1.000 | 1.00 | 0.94 | 0.05 | 1.00 | 0.89 | Jan, Dec, Feb | 25.8 °C | 30 mm |
| 4 | `m_16.25_47.75` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.05 | 1.00 | 0.90 | Jan, Dec, Feb | 25.7 °C | 21 mm |
| 5 | `m_17.75_23.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.06 | 1.00 | 0.94 | Jan, Dec, Feb | 24.6 °C | 10 mm |
| 6 | `m_17.75_36.75` | Sahara | 1.000 | 1.00 | 0.68 | 0.04 | 1.00 | 0.94 | Feb, Jan, Mar | 26.3 °C | 65 mm |
| 7 | `m_18.25_44.25` | Arabian Desert | 1.000 | 1.00 | 0.99 | 0.06 | 1.00 | 0.95 | Dec, Jan, Feb | 25.0 °C | 26 mm |
| 8 | `m_18.25_9.25` | Sahara | 1.000 | 1.00 | 0.64 | 0.05 | 1.00 | 0.95 | Jan, Dec, Feb | 25.5 °C | 73 mm |
| 9 | `m_19.75_19.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.06 | 1.00 | 0.98 | Jan, Dec, Feb | 24.7 °C | 5 mm |
| 10 | `m_19.75_-12.75` | Sahara | 1.000 | 1.00 | 0.41 | 0.04 | 1.00 | 0.98 | Jan, Dec, Feb | 26.8 °C | 146 mm |

**Closest by environment (dry, cold and bare)**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.701 | 1.00 | 0.80 | 0.43 | 1.00 | 0.71 | Mar, Apr, Sep | -7.3 °C | 45 mm |
| 2 | `m_38.75_93.75` | Qaidam Basin | 0.670 | 0.77 | 0.90 | 0.34 | 1.00 | 0.65 | Mar, Apr, May | 0.9 °C | 34 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.663 | 0.87 | 0.65 | 0.45 | 1.00 | 0.73 | Mar, Oct, Apr | -9.3 °C | 72 mm |
| 4 | `m_-77.75_164.25` | McMurdo Dry Valleys | 0.657 | 0.27 | 0.61 | 0.56 | 0.83 | 0.00 | none | -18.9 °C | 80 mm |
| 5 | `m_37.75_89.25` | Tibetan Plateau | 0.650 | 0.66 | 0.75 | 0.37 | 0.99 | 0.67 | Mar, Apr, Sep | -2.0 °C | 52 mm |
| 6 | `m_34.75_83.25` | Tibetan Plateau | 0.640 | 0.96 | 0.64 | 0.41 | 0.99 | 0.74 | Mar, Oct, Apr | -5.8 °C | 73 mm |
| 7 | `m_38.25_74.25` | Pamir and Karakoram | 0.627 | 0.56 | 0.66 | 0.39 | 0.97 | 0.66 | Mar, Sep, Apr | -3.7 °C | 70 mm |
| 8 | `m_81.25_-72.25` | Ellesmere or north-west Greenland | 0.610 | 0.49 | 0.45 | 0.55 | 0.92 | 0.00 | none | -17.4 °C | 129 mm |
| 9 | `m_-25.25_-69.25` | Altiplano and Puna | 0.606 | 0.61 | 1.00 | 0.22 | 1.00 | 0.96 | Aug, Sep, Apr | 10.6 °C | 19 mm |
| 10 | `m_-72.25_68.75` | Antarctica | 0.605 | 0.32 | 0.73 | 0.59 | 0.52 | 0.00 | none | -21.3 °C | 57 mm |

**Closest on all five factors**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.754 | 1.00 | 0.80 | 0.43 | 1.00 | 0.71 | Mar, Apr, Sep | -7.3 °C | 45 mm |
| 2 | `m_35.25_82.75` | Tibetan Plateau | 0.732 | 1.00 | 0.66 | 0.44 | 0.98 | 0.73 | Mar, Oct, Apr | -8.5 °C | 69 mm |
| 3 | `m_34.75_79.25` | Tibetan Plateau | 0.716 | 1.00 | 0.58 | 0.44 | 1.00 | 0.74 | Oct, Mar, Apr | -7.9 °C | 88 mm |
| 4 | `m_37.25_89.75` | Tibetan Plateau | 0.711 | 1.00 | 0.71 | 0.37 | 1.00 | 0.69 | Mar, Apr, Sep | -2.3 °C | 59 mm |
| 5 | `m_38.25_93.25` | Qaidam Basin | 0.703 | 0.92 | 0.94 | 0.30 | 1.00 | 0.66 | Mar, Apr, May | 4.0 °C | 30 mm |
| 6 | `m_-22.25_-68.75` | Atacama Desert | 0.699 | 0.96 | 0.80 | 0.22 | 0.99 | 1.00 | Jul, Aug, May | 10.9 °C | 46 mm |
| 7 | `m_-25.25_-69.25` | Altiplano and Puna | 0.664 | 0.61 | 1.00 | 0.22 | 1.00 | 0.96 | Aug, Sep, Apr | 10.6 °C | 19 mm |
| 8 | `m_41.25_90.25` | Taklamakan and Tarim Basin | 0.662 | 1.00 | 0.95 | 0.23 | 1.00 | 0.60 | Mar, Apr, Sep | 10.4 °C | 29 mm |
| 9 | `m_23.75_26.25` | Sahara | 0.651 | 1.00 | 1.00 | 0.12 | 1.00 | 0.99 | Feb, Nov, Mar | 19.8 °C | 2 mm |
| 10 | `m_-27.75_-70.75` | Atacama Desert | 0.647 | 0.93 | 0.86 | 0.16 | 1.00 | 0.90 | Sep, Oct, Apr | 16.3 °C | 38 mm |

The closest square on all factors is `m_36.25_86.25` (Tibetan Plateau), with a score of 0.754.
There, Mars is 49.5 °C colder in the yearly mean.
The square gets 1.81 times 25 mm of precipitation a year.
Mars air pressure is 0.93 % of the square's.

### McLaughlin crater

Caveats: it is not a climate match, and a score is a position on each factor's own scale, not a share of likeness.

**Closest by landscape (slopes and bare ground)**

38 ranked squares tie at the top score of 1.000, so their order here is not a ranking. Tied squares are listed by bare area, then by environment score.

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_19.25_8.75` | Sahara | 1.000 | 1.00 | 0.89 | 0.07 | 1.00 | 0.91 | Jan, Dec, Feb | 24.1 °C | 34 mm |
| 2 | `m_19.75_18.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.09 | 1.00 | 0.92 | Jan, Dec, Feb | 21.9 °C | 14 mm |
| 3 | `m_20.25_36.75` | Sahara | 1.000 | 1.00 | 0.83 | 0.03 | 1.00 | 0.93 | Feb, Jan, Mar | 27.4 °C | 42 mm |
| 4 | `m_-21.75_-69.25` | Atacama Desert | 1.000 | 1.00 | 1.00 | 0.14 | 1.00 | 0.96 | Jul, Jun, Aug | 17.7 °C | 21 mm |
| 5 | `m_24.25_5.75` | Sahara | 1.000 | 1.00 | 0.74 | 0.09 | 1.00 | 0.98 | Jan, Feb, Nov | 22.1 °C | 55 mm |
| 6 | `m_-25.25_-67.75` | Altiplano and Puna | 1.000 | 1.00 | 0.00 | 0.28 | 1.00 | 0.96 | Jul, Aug, Sep | 5.3 °C | 569 mm |
| 7 | `m_26.25_37.25` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.08 | 1.00 | 0.94 | Feb, Mar, Nov | 23.0 °C | 16 mm |
| 8 | `m_26.25_58.25` | Arabian Desert | 1.000 | 1.00 | 0.57 | 0.06 | 1.00 | 0.94 | Feb, Nov, Oct | 24.8 °C | 92 mm |
| 9 | `m_27.25_33.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.08 | 1.00 | 0.92 | Feb, Mar, Nov | 22.7 °C | 8 mm |
| 10 | `m_27.75_62.25` | other | 1.000 | 1.00 | 0.59 | 0.08 | 1.00 | 0.91 | Feb, Oct, Nov | 23.1 °C | 85 mm |

**Closest by environment (dry, cold and bare)**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.699 | 0.73 | 0.80 | 0.43 | 1.00 | 0.73 | Mar, Oct, Apr | -7.3 °C | 45 mm |
| 2 | `m_38.75_93.75` | Qaidam Basin | 0.668 | 1.00 | 0.90 | 0.33 | 1.00 | 0.67 | Mar, Apr, May | 0.9 °C | 34 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.660 | 1.00 | 0.65 | 0.45 | 1.00 | 0.75 | Mar, Oct, Apr | -9.3 °C | 72 mm |
| 4 | `m_-77.75_164.25` | McMurdo Dry Valleys | 0.655 | 0.80 | 0.61 | 0.56 | 0.83 | 0.00 | none | -18.9 °C | 80 mm |
| 5 | `m_37.75_89.25` | Tibetan Plateau | 0.648 | 1.00 | 0.75 | 0.36 | 0.99 | 0.70 | Mar, Oct, Apr | -2.0 °C | 52 mm |
| 6 | `m_34.75_83.25` | Tibetan Plateau | 0.638 | 0.87 | 0.64 | 0.41 | 0.99 | 0.76 | Mar, Oct, Apr | -5.8 °C | 73 mm |
| 7 | `m_38.25_74.25` | Pamir and Karakoram | 0.625 | 1.00 | 0.66 | 0.38 | 0.97 | 0.69 | Oct, Mar, Sep | -3.7 °C | 70 mm |
| 8 | `m_81.25_-72.25` | Ellesmere or north-west Greenland | 0.608 | 0.97 | 0.45 | 0.54 | 0.92 | 0.00 | none | -17.4 °C | 129 mm |
| 9 | `m_-25.25_-69.25` | Altiplano and Puna | 0.604 | 0.96 | 1.00 | 0.22 | 1.00 | 0.96 | Jul, Aug, May | 10.6 °C | 19 mm |
| 10 | `m_-72.25_68.75` | Antarctica | 0.603 | 0.74 | 0.73 | 0.58 | 0.52 | 0.00 | none | -21.3 °C | 57 mm |

**Closest on all five factors**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_37.25_88.25` | Tibetan Plateau | 0.738 | 0.94 | 0.79 | 0.42 | 0.99 | 0.71 | Mar, Oct, Apr | -6.7 °C | 47 mm |
| 2 | `m_35.25_79.75` | Tibetan Plateau | 0.736 | 1.00 | 0.65 | 0.45 | 1.00 | 0.75 | Mar, Oct, Apr | -9.3 °C | 72 mm |
| 3 | `m_-22.25_-68.25` | Altiplano and Puna | 0.733 | 1.00 | 0.83 | 0.29 | 0.90 | 0.97 | Jul, Jun, Aug | 4.4 °C | 42 mm |
| 4 | `m_-25.25_-69.25` | Altiplano and Puna | 0.727 | 0.96 | 1.00 | 0.22 | 1.00 | 0.96 | Jul, Aug, May | 10.6 °C | 19 mm |
| 5 | `m_38.75_93.75` | Qaidam Basin | 0.726 | 1.00 | 0.90 | 0.33 | 1.00 | 0.67 | Mar, Apr, May | 0.9 °C | 34 mm |
| 6 | `m_36.25_84.25` | Tibetan Plateau | 0.723 | 0.92 | 0.72 | 0.40 | 1.00 | 0.73 | Mar, Oct, Apr | -5.5 °C | 57 mm |
| 7 | `m_33.25_82.75` | Tibetan Plateau | 0.712 | 1.00 | 0.59 | 0.39 | 0.99 | 0.79 | Feb, Mar, Oct | -4.6 °C | 86 mm |
| 8 | `m_38.25_74.25` | Pamir and Karakoram | 0.699 | 1.00 | 0.66 | 0.38 | 0.97 | 0.69 | Oct, Mar, Sep | -3.7 °C | 70 mm |
| 9 | `m_-28.25_-69.25` | Altiplano and Puna | 0.682 | 1.00 | 0.52 | 0.33 | 0.98 | 0.90 | Aug, Sep, Oct | 1.4 °C | 106 mm |
| 10 | `m_32.25_79.75` | Tibetan Plateau | 0.675 | 1.00 | 0.57 | 0.38 | 0.80 | 0.81 | Feb, Oct, Mar | -3.2 °C | 91 mm |

The closest square on all factors is `m_37.25_88.25` (Tibetan Plateau), with a score of 0.738.
There, Mars is 51.0 °C colder in the yearly mean.
The square gets 1.88 times 25 mm of precipitation a year.
Mars air pressure is 1.57 % of the square's.

### South of Firsoff crater, Arabia Terra

Caveats: it is not a climate match, and a score is a position on each factor's own scale, not a share of likeness.

**Closest by landscape (slopes and bare ground)**

435 ranked squares tie at the top score of 1.000, so their order here is not a ranking. Tied squares are listed by bare area, then by environment score.

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_13.75_40.75` | Danakil Depression | 1.000 | 1.00 | 0.20 | 0.00 | 1.00 | 1.00 | none | 33.0 °C | 272 mm |
| 2 | `m_15.75_27.25` | Sahara | 1.000 | 1.00 | 0.78 | 0.06 | 1.00 | 1.00 | Mar, Apr, Oct | 24.8 °C | 48 mm |
| 3 | `m_16.25_45.25` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.08 | 1.00 | 1.00 | Oct, Mar, Apr | 23.7 °C | 22 mm |
| 4 | `m_16.25_50.25` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.05 | 1.00 | 1.00 | Mar, Oct, Apr | 25.6 °C | 24 mm |
| 5 | `m_16.75_30.25` | Sahara | 1.000 | 1.00 | 0.84 | 0.03 | 1.00 | 1.00 | Mar, Apr, Oct | 27.1 °C | 40 mm |
| 6 | `m_17.25_23.25` | Sahara | 1.000 | 1.00 | 0.98 | 0.08 | 1.00 | 1.00 | Mar, Apr, May | 23.4 °C | 27 mm |
| 7 | `m_17.75_9.25` | Sahara | 1.000 | 1.00 | 0.53 | 0.05 | 1.00 | 1.00 | Mar, Apr | 25.9 °C | 102 mm |
| 8 | `m_17.75_54.75` | Arabian Desert | 1.000 | 1.00 | 0.37 | 0.04 | 1.00 | 1.00 | Apr | 26.5 °C | 163 mm |
| 9 | `m_18.25_32.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.02 | 1.00 | 1.00 | Mar, Apr | 28.6 °C | 13 mm |
| 10 | `m_18.75_43.75` | Arabian Desert | 1.000 | 1.00 | 0.85 | 0.07 | 1.00 | 1.00 | Mar, Sep, Apr | 24.4 °C | 39 mm |

**Closest by environment (dry, cold and bare)**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.709 | 0.93 | 0.80 | 0.44 | 1.00 | 0.50 | May, Aug, Jun | -7.3 °C | 45 mm |
| 2 | `m_38.75_93.75` | Qaidam Basin | 0.678 | 0.62 | 0.90 | 0.35 | 1.00 | 0.40 | May, Aug, Jun | 0.9 °C | 34 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.670 | 0.79 | 0.65 | 0.47 | 1.00 | 0.54 | Apr, May, Jul | -9.3 °C | 72 mm |
| 4 | `m_-77.75_164.25` | McMurdo Dry Valleys | 0.665 | 0.25 | 0.61 | 0.58 | 0.83 | 0.00 | none | -18.9 °C | 80 mm |
| 5 | `m_37.75_89.25` | Tibetan Plateau | 0.658 | 0.58 | 0.75 | 0.38 | 0.99 | 0.44 | May, Aug, Jun | -2.0 °C | 52 mm |
| 6 | `m_34.75_83.25` | Tibetan Plateau | 0.647 | 0.76 | 0.64 | 0.43 | 0.99 | 0.56 | Apr, May, Jun | -5.8 °C | 73 mm |
| 7 | `m_38.25_74.25` | Pamir and Karakoram | 0.634 | 0.49 | 0.66 | 0.40 | 0.97 | 0.42 | May, Aug, Jun | -3.7 °C | 70 mm |
| 8 | `m_81.25_-72.25` | Ellesmere or north-west Greenland | 0.617 | 0.39 | 0.45 | 0.56 | 0.92 | 0.00 | none | -17.4 °C | 129 mm |
| 9 | `m_-25.25_-69.25` | Altiplano and Puna | 0.613 | 0.49 | 1.00 | 0.23 | 1.00 | 0.93 | Oct, Nov, Mar | 10.6 °C | 19 mm |
| 10 | `m_-72.25_68.75` | Antarctica | 0.612 | 0.28 | 0.73 | 0.61 | 0.52 | 0.00 | none | -21.3 °C | 57 mm |

**Closest on all five factors**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_35.75_85.25` | Tibetan Plateau | 0.702 | 1.00 | 0.74 | 0.44 | 1.00 | 0.52 | May, Aug, Jun | -7.0 °C | 54 mm |
| 2 | `m_-22.75_-69.75` | Atacama Desert | 0.689 | 1.00 | 1.00 | 0.15 | 1.00 | 1.00 | Oct, Nov, Dec | 17.0 °C | 8 mm |
| 3 | `m_34.75_79.25` | Tibetan Plateau | 0.676 | 0.97 | 0.58 | 0.45 | 1.00 | 0.56 | Apr, May, Jun | -7.9 °C | 88 mm |
| 4 | `m_37.25_89.75` | Tibetan Plateau | 0.661 | 1.00 | 0.71 | 0.39 | 1.00 | 0.46 | May, Aug, Jun | -2.3 °C | 59 mm |
| 5 | `m_38.25_93.25` | Qaidam Basin | 0.657 | 1.00 | 0.94 | 0.31 | 1.00 | 0.42 | May, Aug, Jun | 4.0 °C | 30 mm |
| 6 | `m_23.75_26.25` | Sahara | 0.654 | 1.00 | 1.00 | 0.12 | 1.00 | 0.99 | Apr, May, Sep | 19.8 °C | 2 mm |
| 7 | `m_-19.75_-69.75` | Atacama Desert | 0.654 | 0.82 | 1.00 | 0.15 | 1.00 | 1.00 | Sep, Oct, Nov | 17.8 °C | 15 mm |
| 8 | `m_33.25_82.75` | Tibetan Plateau | 0.649 | 0.78 | 0.59 | 0.41 | 0.99 | 0.62 | Apr, May, Jun | -4.6 °C | 86 mm |
| 9 | `m_23.75_11.75` | Sahara | 0.637 | 0.99 | 1.00 | 0.11 | 1.00 | 0.99 | Apr, Sep, May | 21.0 °C | 20 mm |
| 10 | `m_-26.25_15.25` | Namib Desert | 0.636 | 1.00 | 0.80 | 0.15 | 1.00 | 0.89 | Oct, Nov, Dec | 17.7 °C | 45 mm |

The closest square on all factors is `m_35.75_85.25` (Tibetan Plateau), with a score of 0.702.
There, Mars is 46.9 °C colder in the yearly mean.
The square gets 2.15 times 25 mm of precipitation a year.
Mars air pressure is 1.22 % of the square's.

### Ismenius Cavus

Caveats: it is not a climate match, and a score is a position on each factor's own scale, not a share of likeness.

**Closest by landscape (slopes and bare ground)**

45 ranked squares tie at the top score of 1.000, so their order here is not a ranking. Tied squares are listed by bare area, then by environment score.

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_12.75_41.25` | Danakil Depression | 1.000 | 1.00 | 0.21 | 0.00 | 1.00 | 0.55 | Jan, Dec, Feb | 33.1 °C | 266 mm |
| 2 | `m_19.25_8.75` | Sahara | 1.000 | 1.00 | 0.89 | 0.06 | 1.00 | 0.68 | Jan, Dec, Feb | 24.1 °C | 34 mm |
| 3 | `m_19.75_18.25` | Sahara | 1.000 | 1.00 | 0.99 | 0.06 | 1.00 | 0.69 | Jan, Dec, Feb | 24.1 °C | 26 mm |
| 4 | `m_20.25_36.75` | Sahara | 1.000 | 1.00 | 0.83 | 0.03 | 1.00 | 0.70 | Feb, Jan, Mar | 27.4 °C | 42 mm |
| 5 | `m_23.25_34.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.03 | 1.00 | 0.76 | Jan, Dec, Feb | 27.0 °C | 8 mm |
| 6 | `m_23.25_39.25` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.03 | 1.00 | 0.76 | Feb, Jan, Dec | 27.2 °C | 21 mm |
| 7 | `m_24.25_9.75` | Sahara | 1.000 | 1.00 | 0.87 | 0.09 | 1.00 | 0.78 | Jan, Feb, Dec | 21.0 °C | 37 mm |
| 8 | `m_24.25_5.75` | Sahara | 1.000 | 1.00 | 0.74 | 0.08 | 1.00 | 0.78 | Jan, Dec, Feb | 22.1 °C | 55 mm |
| 9 | `m_24.75_2.75` | Sahara | 1.000 | 1.00 | 0.90 | 0.02 | 1.00 | 0.79 | Jan, Dec, Feb | 27.7 °C | 34 mm |
| 10 | `m_25.75_30.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.08 | 1.00 | 0.81 | Jan, Dec, Feb | 21.5 °C | 1 mm |

**Closest by environment (dry, cold and bare)**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.662 | 0.91 | 0.80 | 0.36 | 1.00 | 0.92 | Jan, Feb, Nov | -7.3 °C | 45 mm |
| 2 | `m_38.75_93.75` | Qaidam Basin | 0.632 | 0.87 | 0.90 | 0.28 | 1.00 | 0.87 | Feb, Nov, Mar | 0.9 °C | 34 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.625 | 0.93 | 0.65 | 0.38 | 1.00 | 0.93 | Dec, Jan, Nov | -9.3 °C | 72 mm |
| 4 | `m_-77.75_164.25` | McMurdo Dry Valleys | 0.620 | 0.52 | 0.61 | 0.47 | 0.83 | 0.09 | Dec, Jan | -18.9 °C | 80 mm |
| 5 | `m_37.75_89.25` | Tibetan Plateau | 0.614 | 0.84 | 0.75 | 0.31 | 0.99 | 0.89 | Jan, Feb, Nov | -2.0 °C | 52 mm |
| 6 | `m_34.75_83.25` | Tibetan Plateau | 0.604 | 0.91 | 0.64 | 0.35 | 0.99 | 0.93 | Jan, Dec, Feb | -5.8 °C | 73 mm |
| 7 | `m_38.25_74.25` | Pamir and Karakoram | 0.592 | 0.77 | 0.66 | 0.33 | 0.97 | 0.88 | Nov, Feb, Oct | -3.7 °C | 70 mm |
| 8 | `m_81.25_-72.25` | Ellesmere or north-west Greenland | 0.576 | 0.68 | 0.45 | 0.46 | 0.92 | 0.02 | Jun | -17.4 °C | 129 mm |
| 9 | `m_-25.25_-69.25` | Altiplano and Puna | 0.572 | 0.74 | 1.00 | 0.19 | 1.00 | 0.80 | Jul, Jun, Aug | 10.6 °C | 19 mm |
| 10 | `m_-72.25_68.75` | Antarctica | 0.571 | 0.56 | 0.73 | 0.50 | 0.52 | 0.20 | Jan, Dec, Nov | -21.3 °C | 57 mm |

**Closest on all five factors**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_87.75` | Tibetan Plateau | 0.755 | 0.98 | 0.76 | 0.36 | 0.98 | 0.92 | Jan, Feb, Nov | -7.7 °C | 51 mm |
| 2 | `m_35.25_79.75` | Tibetan Plateau | 0.734 | 0.93 | 0.65 | 0.38 | 1.00 | 0.93 | Dec, Jan, Nov | -9.3 °C | 72 mm |
| 3 | `m_36.25_84.25` | Tibetan Plateau | 0.733 | 0.93 | 0.72 | 0.34 | 1.00 | 0.92 | Jan, Feb, Nov | -5.5 °C | 57 mm |
| 4 | `m_38.75_93.75` | Qaidam Basin | 0.717 | 0.87 | 0.90 | 0.28 | 1.00 | 0.87 | Feb, Nov, Mar | 0.9 °C | 34 mm |
| 5 | `m_33.25_82.75` | Tibetan Plateau | 0.709 | 0.98 | 0.59 | 0.33 | 0.99 | 0.93 | Dec, Jan, Nov | -4.6 °C | 86 mm |
| 6 | `m_38.25_90.25` | Qaidam Basin | 0.708 | 1.00 | 0.75 | 0.28 | 0.95 | 0.88 | Feb, Nov, Mar | 0.8 °C | 53 mm |
| 7 | `m_41.25_89.25` | Taklamakan and Tarim Basin | 0.675 | 0.98 | 0.89 | 0.20 | 1.00 | 0.82 | Feb, Mar, Oct | 9.8 °C | 35 mm |
| 8 | `m_38.25_74.25` | Pamir and Karakoram | 0.674 | 0.77 | 0.66 | 0.33 | 0.97 | 0.88 | Nov, Feb, Oct | -3.7 °C | 70 mm |
| 9 | `m_36.25_95.75` | Qaidam Basin | 0.657 | 1.00 | 0.59 | 0.23 | 0.97 | 0.92 | Jan, Feb, Nov | 5.8 °C | 86 mm |
| 10 | `m_44.25_97.25` | Gobi Desert | 0.649 | 0.93 | 0.70 | 0.23 | 1.00 | 0.76 | Feb, Mar, Oct | 6.1 °C | 60 mm |

The closest square on all factors is `m_36.25_87.75` (Tibetan Plateau), with a score of 0.755.
There, Mars is 65.6 °C colder in the yearly mean.
The square gets 2.03 times 25 mm of precipitation a year.
Mars air pressure is 1.43 % of the square's.

### Hale crater

Caveats: it is not a climate match, and a score is a position on each factor's own scale, not a share of likeness.

**Closest by landscape (slopes and bare ground)**

29 ranked squares tie at the top score of 1.000, so their order here is not a ranking. Tied squares are listed by bare area, then by environment score.

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_19.75_18.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.08 | 1.00 | 0.66 | Jan, Dec, Feb | 21.9 °C | 14 mm |
| 2 | `m_20.25_36.75` | Sahara | 1.000 | 1.00 | 0.83 | 0.03 | 1.00 | 0.67 | Feb, Jan, Mar | 27.4 °C | 42 mm |
| 3 | `m_-21.75_-69.25` | Atacama Desert | 1.000 | 1.00 | 1.00 | 0.12 | 1.00 | 0.70 | Jul, Jun, Aug | 17.7 °C | 21 mm |
| 4 | `m_-24.75_-69.25` | Atacama Desert | 1.000 | 1.00 | 1.00 | 0.15 | 1.00 | 0.76 | Jul, Jun, Aug | 14.5 °C | 12 mm |
| 5 | `m_26.25_37.25` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.07 | 1.00 | 0.79 | Feb, Dec, Jan | 23.0 °C | 16 mm |
| 6 | `m_26.25_58.25` | Arabian Desert | 1.000 | 1.00 | 0.57 | 0.05 | 1.00 | 0.79 | Dec, Feb, Nov | 24.8 °C | 92 mm |
| 7 | `m_27.25_33.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.07 | 1.00 | 0.81 | Jan, Dec, Feb | 22.7 °C | 8 mm |
| 8 | `m_27.75_62.25` | other | 1.000 | 1.00 | 0.59 | 0.07 | 1.00 | 0.82 | Dec, Feb, Jan | 23.1 °C | 85 mm |
| 9 | `m_32.75_55.75` | Iranian deserts (Lut, Kavir) | 1.000 | 1.00 | 0.71 | 0.11 | 1.00 | 0.91 | Dec, Jan, Feb | 19.2 °C | 59 mm |
| 10 | `m_38.75_90.25` | Qaidam Basin | 1.000 | 1.00 | 0.77 | 0.25 | 1.00 | 0.90 | Jan, Feb, Nov | 5.0 °C | 50 mm |

**Closest by environment (dry, cold and bare)**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.665 | 0.65 | 0.80 | 0.37 | 1.00 | 0.93 | Jan, Dec, Feb | -7.3 °C | 45 mm |
| 2 | `m_38.75_93.75` | Qaidam Basin | 0.636 | 1.00 | 0.90 | 0.29 | 1.00 | 0.90 | Jan, Feb, Nov | 0.9 °C | 34 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.629 | 0.93 | 0.65 | 0.39 | 1.00 | 0.93 | Dec, Jan, Nov | -9.3 °C | 72 mm |
| 4 | `m_-77.75_164.25` | McMurdo Dry Valleys | 0.624 | 0.84 | 0.61 | 0.48 | 0.83 | 0.12 | Nov, Dec, Jan | -18.9 °C | 80 mm |
| 5 | `m_37.75_89.25` | Tibetan Plateau | 0.617 | 1.00 | 0.75 | 0.32 | 0.99 | 0.92 | Jan, Feb, Nov | -2.0 °C | 52 mm |
| 6 | `m_34.75_83.25` | Tibetan Plateau | 0.607 | 0.82 | 0.64 | 0.35 | 0.99 | 0.93 | Jan, Dec, Feb | -5.8 °C | 73 mm |
| 7 | `m_38.25_74.25` | Pamir and Karakoram | 0.595 | 1.00 | 0.66 | 0.33 | 0.97 | 0.91 | Jan, Nov, Feb | -3.7 °C | 70 mm |
| 8 | `m_81.25_-72.25` | Ellesmere or north-west Greenland | 0.579 | 0.98 | 0.45 | 0.47 | 0.92 | 0.05 | Jun, Jul | -17.4 °C | 129 mm |
| 9 | `m_-25.25_-69.25` | Altiplano and Puna | 0.575 | 0.98 | 1.00 | 0.19 | 1.00 | 0.77 | Jul, Jun, Aug | 10.6 °C | 19 mm |
| 10 | `m_-72.25_68.75` | Antarctica | 0.574 | 0.76 | 0.73 | 0.50 | 0.52 | 0.23 | Feb, Jan, Dec | -21.3 °C | 57 mm |

**Closest on all five factors**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.75_86.75` | Tibetan Plateau | 0.756 | 0.97 | 0.80 | 0.35 | 0.98 | 0.93 | Jan, Dec, Feb | -5.5 °C | 45 mm |
| 2 | `m_38.75_93.75` | Qaidam Basin | 0.746 | 1.00 | 0.90 | 0.29 | 1.00 | 0.90 | Jan, Feb, Nov | 0.9 °C | 34 mm |
| 3 | `m_35.25_79.25` | Tibetan Plateau | 0.737 | 1.00 | 0.63 | 0.37 | 1.00 | 0.93 | Dec, Jan, Nov | -7.9 °C | 76 mm |
| 4 | `m_35.75_82.75` | Tibetan Plateau | 0.724 | 0.90 | 0.66 | 0.37 | 0.99 | 0.93 | Jan, Dec, Nov | -7.1 °C | 69 mm |
| 5 | `m_37.75_90.25` | Tibetan Plateau | 0.720 | 1.00 | 0.74 | 0.30 | 0.95 | 0.92 | Jan, Feb, Nov | -0.5 °C | 55 mm |
| 6 | `m_38.25_74.25` | Pamir and Karakoram | 0.718 | 1.00 | 0.66 | 0.33 | 0.97 | 0.91 | Jan, Nov, Feb | -3.7 °C | 70 mm |
| 7 | `m_32.25_80.75` | Tibetan Plateau | 0.696 | 1.00 | 0.58 | 0.33 | 0.94 | 0.90 | Dec, Nov, Jan | -3.4 °C | 87 mm |
| 8 | `m_-25.25_-69.25` | Altiplano and Puna | 0.677 | 0.98 | 1.00 | 0.19 | 1.00 | 0.77 | Jul, Jun, Aug | 10.6 °C | 19 mm |
| 9 | `m_-22.25_-68.25` | Altiplano and Puna | 0.668 | 1.00 | 0.83 | 0.25 | 0.90 | 0.71 | Jul, Jun, Aug | 4.4 °C | 42 mm |
| 10 | `m_-29.75_-69.75` | Altiplano and Puna | 0.664 | 0.86 | 0.61 | 0.29 | 0.99 | 0.86 | Sep, Apr, Oct | 0.5 °C | 81 mm |

The closest square on all factors is `m_36.75_86.75` (Tibetan Plateau), with a score of 0.756.
There, Mars is 66.1 °C colder in the yearly mean.
The square gets 1.81 times 25 mm of precipitation a year.
Mars air pressure is 1.18 % of the square's.

### Copernicus crater

Caveats: it is not a climate match, and a score is a position on each factor's own scale, not a share of likeness.

**Closest by landscape (slopes and bare ground)**

251 ranked squares tie at the top score of 1.000, so their order here is not a ranking. Tied squares are listed by bare area, then by environment score.

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_15.75_27.25` | Sahara | 1.000 | 1.00 | 0.78 | 0.05 | 1.00 | 0.30 | Jan, Dec, Feb | 24.8 °C | 48 mm |
| 2 | `m_16.25_47.75` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.04 | 1.00 | 0.31 | Jan, Dec, Feb | 25.7 °C | 21 mm |
| 3 | `m_16.25_51.75` | Arabian Desert | 1.000 | 1.00 | 0.57 | 0.03 | 1.00 | 0.31 | Jan, Dec, Feb | 26.2 °C | 90 mm |
| 4 | `m_16.75_30.25` | Sahara | 1.000 | 1.00 | 0.84 | 0.03 | 1.00 | 0.32 | Jan, Dec, Feb | 27.1 °C | 40 mm |
| 5 | `m_17.25_23.25` | Sahara | 1.000 | 1.00 | 0.98 | 0.06 | 1.00 | 0.33 | Jan, Dec, Feb | 23.4 °C | 27 mm |
| 6 | `m_17.75_54.75` | Arabian Desert | 1.000 | 1.00 | 0.37 | 0.03 | 1.00 | 0.34 | Dec, Jan, Nov | 26.5 °C | 163 mm |
| 7 | `m_18.75_36.25` | Sahara | 1.000 | 1.00 | 0.79 | 0.03 | 1.00 | 0.36 | Jan, Feb, Dec | 27.2 °C | 46 mm |
| 8 | `m_18.75_-11.75` | Sahara | 1.000 | 1.00 | 0.47 | 0.02 | 1.00 | 0.36 | Jan, Dec, Feb | 27.9 °C | 122 mm |
| 9 | `m_19.25_21.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.05 | 1.00 | 0.37 | Jan, Dec, Feb | 24.8 °C | 5 mm |
| 10 | `m_19.25_9.25` | Sahara | 1.000 | 1.00 | 0.87 | 0.04 | 1.00 | 0.37 | Jan, Dec, Feb | 25.0 °C | 37 mm |

**Closest by environment (dry, cold and bare)**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.645 | 0.80 | 0.80 | 0.33 | 1.00 | 0.71 | Jan, Dec, Feb | -7.3 °C | 45 mm |
| 2 | `m_38.75_93.75` | Qaidam Basin | 0.617 | 0.44 | 0.90 | 0.26 | 1.00 | 0.76 | Jan, Dec, Feb | 0.9 °C | 34 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.610 | 0.62 | 0.65 | 0.35 | 1.00 | 0.69 | Dec, Jan, Nov | -9.3 °C | 72 mm |
| 4 | `m_-77.75_164.25` | McMurdo Dry Valleys | 0.605 | 0.10 | 0.61 | 0.44 | 0.83 | 0.40 | Oct, Nov, Dec | -18.9 °C | 80 mm |
| 5 | `m_37.75_89.25` | Tibetan Plateau | 0.599 | 0.40 | 0.75 | 0.29 | 0.99 | 0.74 | Jan, Dec, Feb | -2.0 °C | 52 mm |
| 6 | `m_34.75_83.25` | Tibetan Plateau | 0.589 | 0.59 | 0.64 | 0.32 | 0.99 | 0.68 | Jan, Dec, Feb | -5.8 °C | 73 mm |
| 7 | `m_38.25_74.25` | Pamir and Karakoram | 0.577 | 0.30 | 0.66 | 0.30 | 0.97 | 0.75 | Dec, Jan, Nov | -3.7 °C | 70 mm |
| 8 | `m_81.25_-72.25` | Ellesmere or north-west Greenland | 0.561 | 0.22 | 0.45 | 0.43 | 0.92 | 0.33 | Apr, May, Jun | -17.4 °C | 129 mm |
| 9 | `m_-25.25_-69.25` | Altiplano and Puna | 0.558 | 0.31 | 1.00 | 0.17 | 1.00 | 0.49 | Jul, Jun, Aug | 10.6 °C | 19 mm |
| 10 | `m_-72.25_68.75` | Antarctica | 0.557 | 0.12 | 0.73 | 0.46 | 0.52 | 0.51 | Mar, Oct, Feb | -21.3 °C | 57 mm |

**Closest on all five factors**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_38.25_93.25` | Qaidam Basin | 0.693 | 0.98 | 0.94 | 0.23 | 1.00 | 0.75 | Jan, Dec, Feb | 4.0 °C | 30 mm |
| 2 | `m_35.25_85.25` | Tibetan Plateau | 0.687 | 1.00 | 0.69 | 0.32 | 0.99 | 0.69 | Jan, Dec, Feb | -5.9 °C | 63 mm |
| 3 | `m_37.25_89.75` | Tibetan Plateau | 0.682 | 0.98 | 0.71 | 0.29 | 1.00 | 0.73 | Jan, Dec, Feb | -2.3 °C | 59 mm |
| 4 | `m_44.25_96.75` | Gobi Desert | 0.664 | 0.98 | 0.72 | 0.21 | 1.00 | 0.87 | Jan, Dec, Feb | 6.5 °C | 58 mm |
| 5 | `m_41.75_91.25` | Taklamakan and Tarim Basin | 0.658 | 0.96 | 0.92 | 0.17 | 1.00 | 0.82 | Jan, Dec, Feb | 11.0 °C | 32 mm |
| 6 | `m_34.75_79.25` | Tibetan Plateau | 0.648 | 0.86 | 0.58 | 0.34 | 1.00 | 0.68 | Dec, Jan, Nov | -7.9 °C | 88 mm |
| 7 | `m_42.25_101.75` | Gobi Desert | 0.647 | 1.00 | 0.72 | 0.19 | 1.00 | 0.83 | Jan, Dec, Feb | 8.7 °C | 59 mm |
| 8 | `m_41.25_95.25` | Gobi Desert | 0.639 | 0.93 | 0.72 | 0.20 | 1.00 | 0.81 | Jan, Dec, Feb | 8.0 °C | 59 mm |
| 9 | `m_44.75_106.25` | Gobi Desert | 0.631 | 1.00 | 0.49 | 0.23 | 1.00 | 0.88 | Jan, Dec, Feb | 4.0 °C | 115 mm |
| 10 | `m_47.25_94.25` | other | 0.630 | 1.00 | 0.45 | 0.24 | 1.00 | 0.93 | Jan, Feb, Dec | 3.3 °C | 131 mm |

The closest square on all factors is `m_38.25_93.25` (Qaidam Basin), with a score of 0.693.
There, Mars is 85.4 °C colder in the yearly mean.
The square gets 1.20 times 25 mm of precipitation a year.
Mars air pressure is 0.78 % of the square's.

### Huygens crater

Caveats: it is not a climate match, and a score is a position on each factor's own scale, not a share of likeness.

**Closest by landscape (slopes and bare ground)**

132 ranked squares tie at the top score of 1.000, so their order here is not a ranking. Tied squares are listed by bare area, then by environment score.

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_16.25_47.75` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.05 | 1.00 | 1.00 | Jan, Feb, Nov | 25.7 °C | 21 mm |
| 2 | `m_17.75_23.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.06 | 1.00 | 1.00 | Feb, Nov, Mar | 24.6 °C | 10 mm |
| 3 | `m_18.75_36.25` | Sahara | 1.000 | 1.00 | 0.79 | 0.03 | 1.00 | 1.00 | Feb, Mar, Nov | 27.2 °C | 46 mm |
| 4 | `m_19.25_19.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.05 | 1.00 | 1.00 | Feb, Nov, Mar | 25.8 °C | 5 mm |
| 5 | `m_19.25_-12.75` | Sahara | 1.000 | 1.00 | 0.49 | 0.02 | 1.00 | 1.00 | Feb, Nov, Mar | 28.1 °C | 114 mm |
| 6 | `m_19.75_44.25` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.04 | 1.00 | 1.00 | Feb, Nov, Mar | 26.6 °C | 13 mm |
| 7 | `m_19.75_8.25` | Sahara | 1.000 | 1.00 | 0.77 | 0.04 | 1.00 | 1.00 | Feb, Nov, Mar | 26.7 °C | 49 mm |
| 8 | `m_21.25_12.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.05 | 1.00 | 1.00 | Feb, Mar, Oct | 25.5 °C | 20 mm |
| 9 | `m_21.25_32.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.05 | 1.00 | 1.00 | Feb, Mar, Apr | 25.5 °C | 2 mm |
| 10 | `m_21.25_15.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.05 | 1.00 | 1.00 | Feb, Mar, Oct | 25.8 °C | 9 mm |

**Closest by environment (dry, cold and bare)**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.695 | 0.82 | 0.80 | 0.42 | 1.00 | 0.67 | Mar, Apr, Sep | -7.3 °C | 45 mm |
| 2 | `m_38.75_93.75` | Qaidam Basin | 0.664 | 0.48 | 0.90 | 0.33 | 1.00 | 0.60 | Apr, May, Sep | 0.9 °C | 34 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.657 | 0.65 | 0.65 | 0.44 | 1.00 | 0.69 | Mar, Apr, Sep | -9.3 °C | 72 mm |
| 4 | `m_-77.75_164.25` | McMurdo Dry Valleys | 0.651 | 0.16 | 0.61 | 0.55 | 0.83 | 0.00 | none | -18.9 °C | 80 mm |
| 5 | `m_37.75_89.25` | Tibetan Plateau | 0.644 | 0.45 | 0.75 | 0.36 | 0.99 | 0.63 | Apr, Sep, May | -2.0 °C | 52 mm |
| 6 | `m_34.75_83.25` | Tibetan Plateau | 0.634 | 0.62 | 0.64 | 0.40 | 0.99 | 0.71 | Mar, Apr, May | -5.8 °C | 73 mm |
| 7 | `m_38.25_74.25` | Pamir and Karakoram | 0.622 | 0.36 | 0.66 | 0.38 | 0.97 | 0.62 | Sep, Apr, May | -3.7 °C | 70 mm |
| 8 | `m_81.25_-72.25` | Ellesmere or north-west Greenland | 0.604 | 0.28 | 0.45 | 0.53 | 0.92 | 0.00 | none | -17.4 °C | 129 mm |
| 9 | `m_-25.25_-69.25` | Altiplano and Puna | 0.601 | 0.36 | 1.00 | 0.22 | 1.00 | 0.95 | Sep, Apr, Oct | 10.6 °C | 19 mm |
| 10 | `m_-72.25_68.75` | Antarctica | 0.600 | 0.18 | 0.73 | 0.58 | 0.52 | 0.00 | none | -21.3 °C | 57 mm |

**Closest on all five factors**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_35.25_85.25` | Tibetan Plateau | 0.718 | 0.99 | 0.69 | 0.40 | 0.99 | 0.69 | Mar, Apr, Sep | -5.9 °C | 63 mm |
| 2 | `m_38.25_93.25` | Qaidam Basin | 0.697 | 0.98 | 0.94 | 0.29 | 1.00 | 0.62 | Apr, May, Sep | 4.0 °C | 30 mm |
| 3 | `m_37.25_89.75` | Tibetan Plateau | 0.695 | 0.98 | 0.71 | 0.36 | 1.00 | 0.64 | Apr, Sep, May | -2.3 °C | 59 mm |
| 4 | `m_34.75_79.25` | Tibetan Plateau | 0.687 | 0.88 | 0.58 | 0.42 | 1.00 | 0.71 | Mar, Apr, Sep | -7.9 °C | 88 mm |
| 5 | `m_-22.75_-69.75` | Atacama Desert | 0.680 | 1.00 | 1.00 | 0.15 | 1.00 | 1.00 | Aug, Sep, Oct | 17.0 °C | 8 mm |
| 6 | `m_23.75_26.25` | Sahara | 0.647 | 1.00 | 1.00 | 0.11 | 1.00 | 0.99 | Feb, Mar, Oct | 19.8 °C | 2 mm |
| 7 | `m_33.25_82.75` | Tibetan Plateau | 0.637 | 0.62 | 0.59 | 0.39 | 0.99 | 0.75 | Mar, Apr, May | -4.6 °C | 86 mm |
| 8 | `m_41.25_91.25` | Taklamakan and Tarim Basin | 0.634 | 1.00 | 0.92 | 0.21 | 1.00 | 0.54 | Apr, Sep, May | 11.6 °C | 32 mm |
| 9 | `m_38.25_86.25` | Taklamakan and Tarim Basin | 0.630 | 1.00 | 0.86 | 0.19 | 1.00 | 0.62 | Apr, Sep, May | 13.2 °C | 38 mm |
| 10 | `m_24.25_12.25` | Sahara | 0.626 | 0.98 | 1.00 | 0.10 | 1.00 | 0.98 | Feb, Mar, Apr | 21.1 °C | 24 mm |

The closest square on all factors is `m_35.25_85.25` (Tibetan Plateau), with a score of 0.718.
There, Mars is 53.3 °C colder in the yearly mean.
The square gets 2.50 times 25 mm of precipitation a year.
Mars air pressure is 0.93 % of the square's.

### Mesopotamia (east rim of Hellas)

Caveats: it is not a climate match, and a score is a position on each factor's own scale, not a share of likeness.

**Closest by landscape (slopes and bare ground)**

203 ranked squares tie at the top score of 1.000, so their order here is not a ranking. Tied squares are listed by bare area, then by environment score.

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_15.75_24.75` | Sahara | 1.000 | 1.00 | 0.85 | 0.06 | 1.00 | 0.58 | Jan, Dec, Feb | 24.5 °C | 39 mm |
| 2 | `m_16.25_50.25` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.04 | 1.00 | 0.59 | Jan, Dec, Feb | 25.6 °C | 24 mm |
| 3 | `m_17.25_53.25` | Arabian Desert | 1.000 | 1.00 | 0.51 | 0.04 | 1.00 | 0.61 | Jan, Dec, Feb | 26.3 °C | 110 mm |
| 4 | `m_17.75_21.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.04 | 1.00 | 0.62 | Jan, Dec, Feb | 26.4 °C | 18 mm |
| 5 | `m_17.75_9.25` | Sahara | 1.000 | 1.00 | 0.53 | 0.04 | 1.00 | 0.62 | Jan, Dec, Feb | 25.9 °C | 102 mm |
| 6 | `m_18.75_36.25` | Sahara | 1.000 | 1.00 | 0.79 | 0.03 | 1.00 | 0.64 | Jan, Feb, Mar | 27.2 °C | 46 mm |
| 7 | `m_19.25_42.75` | Arabian Desert | 1.000 | 1.00 | 0.87 | 0.06 | 1.00 | 0.65 | Jan, Dec, Feb | 23.7 °C | 37 mm |
| 8 | `m_19.25_18.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.04 | 1.00 | 0.65 | Jan, Dec, Feb | 26.0 °C | 7 mm |
| 9 | `m_19.25_-12.75` | Sahara | 1.000 | 1.00 | 0.49 | 0.02 | 1.00 | 0.65 | Jan, Dec, Feb | 28.1 °C | 114 mm |
| 10 | `m_21.25_32.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.05 | 1.00 | 0.69 | Jan, Dec, Feb | 25.5 °C | 2 mm |

**Closest by environment (dry, cold and bare)**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.673 | 0.84 | 0.80 | 0.38 | 1.00 | 0.93 | Jan, Dec, Feb | -7.3 °C | 45 mm |
| 2 | `m_38.75_93.75` | Qaidam Basin | 0.643 | 0.50 | 0.90 | 0.30 | 1.00 | 0.90 | Jan, Feb, Nov | 0.9 °C | 34 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.636 | 0.65 | 0.65 | 0.40 | 1.00 | 0.93 | Dec, Jan, Nov | -9.3 °C | 72 mm |
| 4 | `m_-77.75_164.25` | McMurdo Dry Valleys | 0.631 | 0.22 | 0.61 | 0.50 | 0.83 | 0.12 | Nov, Dec, Jan | -18.9 °C | 80 mm |
| 5 | `m_37.75_89.25` | Tibetan Plateau | 0.624 | 0.48 | 0.75 | 0.33 | 0.99 | 0.92 | Jan, Feb, Nov | -2.0 °C | 52 mm |
| 6 | `m_34.75_83.25` | Tibetan Plateau | 0.614 | 0.65 | 0.64 | 0.36 | 0.99 | 0.93 | Jan, Dec, Feb | -5.8 °C | 73 mm |
| 7 | `m_38.25_74.25` | Pamir and Karakoram | 0.602 | 0.42 | 0.66 | 0.34 | 0.97 | 0.91 | Jan, Nov, Feb | -3.7 °C | 70 mm |
| 8 | `m_81.25_-72.25` | Ellesmere or north-west Greenland | 0.585 | 0.32 | 0.45 | 0.48 | 0.92 | 0.05 | Jun, Jul | -17.4 °C | 129 mm |
| 9 | `m_-25.25_-69.25` | Altiplano and Puna | 0.582 | 0.41 | 1.00 | 0.20 | 1.00 | 0.76 | Jul, Jun, Aug | 10.6 °C | 19 mm |
| 10 | `m_-72.25_68.75` | Antarctica | 0.581 | 0.23 | 0.73 | 0.52 | 0.52 | 0.23 | Feb, Jan, Dec | -21.3 °C | 57 mm |

**Closest on all five factors**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_35.75_85.25` | Tibetan Plateau | 0.764 | 1.00 | 0.74 | 0.38 | 1.00 | 0.93 | Jan, Dec, Feb | -7.0 °C | 54 mm |
| 2 | `m_37.25_89.25` | Tibetan Plateau | 0.731 | 0.97 | 0.73 | 0.32 | 0.98 | 0.93 | Jan, Dec, Feb | -1.9 °C | 55 mm |
| 3 | `m_38.25_93.25` | Qaidam Basin | 0.725 | 0.89 | 0.94 | 0.26 | 1.00 | 0.91 | Jan, Feb, Nov | 4.0 °C | 30 mm |
| 4 | `m_34.75_79.25` | Tibetan Plateau | 0.691 | 0.76 | 0.58 | 0.39 | 1.00 | 0.93 | Dec, Jan, Nov | -7.9 °C | 88 mm |
| 5 | `m_41.25_90.25` | Taklamakan and Tarim Basin | 0.689 | 0.97 | 0.95 | 0.20 | 1.00 | 0.85 | Feb, Nov, Mar | 10.4 °C | 29 mm |
| 6 | `m_41.75_96.25` | Gobi Desert | 0.676 | 1.00 | 0.66 | 0.25 | 1.00 | 0.84 | Feb, Nov, Mar | 5.0 °C | 69 mm |
| 7 | `m_41.75_102.25` | Gobi Desert | 0.665 | 1.00 | 0.72 | 0.22 | 1.00 | 0.84 | Feb, Nov, Mar | 8.8 °C | 58 mm |
| 8 | `m_39.75_86.75` | Taklamakan and Tarim Basin | 0.661 | 1.00 | 0.84 | 0.17 | 1.00 | 0.88 | Feb, Nov, Mar | 13.2 °C | 40 mm |
| 9 | `m_33.25_82.75` | Tibetan Plateau | 0.661 | 0.66 | 0.59 | 0.35 | 0.99 | 0.92 | Dec, Jan, Nov | -4.6 °C | 86 mm |
| 10 | `m_44.25_98.75` | Gobi Desert | 0.660 | 1.00 | 0.60 | 0.26 | 1.00 | 0.79 | Feb, Mar, Oct | 4.1 °C | 82 mm |

The closest square on all factors is `m_35.75_85.25` (Tibetan Plateau), with a score of 0.764.
There, Mars is 61.2 °C colder in the yearly mean.
The square gets 2.15 times 25 mm of precipitation a year.
Mars air pressure is 1.36 % of the square's.

### Western Coprates Chasma

Caveats: it is not a climate match, and a score is a position on each factor's own scale, not a share of likeness.

**Closest by landscape (slopes and bare ground)**

Only one ranked square has the top score of 0.974.

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_27.75_35.75` | Arabian Desert | 0.974 | 0.95 | 1.00 | 0.07 | 1.00 | 0.88 | Mar, Apr, Oct | 23.8 °C | 20 mm |
| 2 | `m_36.25_83.25` | Tibetan Plateau | 0.972 | 0.95 | 0.68 | 0.36 | 0.99 | 0.65 | Apr, Sep, May | -0.6 °C | 66 mm |
| 3 | `m_38.25_86.75` | Taklamakan and Tarim Basin | 0.961 | 0.93 | 0.86 | 0.20 | 1.00 | 0.60 | Apr, Sep, May | 13.4 °C | 38 mm |
| 4 | `m_23.25_57.75` | Arabian Desert | 0.954 | 0.96 | 0.44 | 0.03 | 0.95 | 1.00 | Feb, Mar, Oct | 27.8 °C | 133 mm |
| 5 | `m_27.25_55.75` | Arabian Desert | 0.951 | 0.92 | 0.48 | 0.05 | 0.99 | 0.90 | Apr, Oct, Mar | 26.1 °C | 117 mm |
| 6 | `m_30.25_57.75` | Iranian deserts (Lut, Kavir) | 0.949 | 0.92 | 0.54 | 0.11 | 0.98 | 0.82 | Mar, Sep, Apr | 20.3 °C | 98 mm |
| 7 | `m_40.25_78.75` | Taklamakan and Tarim Basin | 0.946 | 0.91 | 0.34 | 0.24 | 0.99 | 0.54 | Apr, May, Jun | 9.7 °C | 178 mm |
| 8 | `m_-19.25_-70.25` | Atacama Desert | 0.936 | 0.88 | 1.00 | 0.14 | 0.99 | 1.00 | Aug, Sep, Oct | 17.8 °C | 20 mm |
| 9 | `m_19.25_8.75` | Sahara | 0.936 | 0.88 | 0.89 | 0.07 | 1.00 | 1.00 | Feb, Mar, Oct | 24.1 °C | 34 mm |
| 10 | `m_21.75_36.25` | Sahara | 0.935 | 0.88 | 1.00 | 0.04 | 1.00 | 1.00 | Feb, Mar, Apr | 27.0 °C | 23 mm |

**Closest by environment (dry, cold and bare)**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.707 | 0.66 | 0.80 | 0.44 | 1.00 | 0.65 | Apr, Sep, May | -7.3 °C | 45 mm |
| 2 | `m_38.75_93.75` | Qaidam Basin | 0.676 | 0.75 | 0.90 | 0.34 | 1.00 | 0.58 | Apr, May, Sep | 0.9 °C | 34 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.668 | 0.78 | 0.65 | 0.46 | 1.00 | 0.68 | Apr, Sep, May | -9.3 °C | 72 mm |
| 4 | `m_-77.75_164.25` | McMurdo Dry Valleys | 0.663 | 0.59 | 0.61 | 0.58 | 0.83 | 0.00 | none | -18.9 °C | 80 mm |
| 5 | `m_37.75_89.25` | Tibetan Plateau | 0.656 | 0.79 | 0.75 | 0.38 | 0.99 | 0.61 | Apr, Sep, May | -2.0 °C | 52 mm |
| 6 | `m_34.75_83.25` | Tibetan Plateau | 0.645 | 0.74 | 0.64 | 0.42 | 0.99 | 0.69 | Mar, Apr, May | -5.8 °C | 73 mm |
| 7 | `m_38.25_74.25` | Pamir and Karakoram | 0.632 | 0.71 | 0.66 | 0.40 | 0.97 | 0.60 | Sep, Apr, May | -3.7 °C | 70 mm |
| 8 | `m_81.25_-72.25` | Ellesmere or north-west Greenland | 0.615 | 0.63 | 0.45 | 0.56 | 0.92 | 0.00 | none | -17.4 °C | 129 mm |
| 9 | `m_-25.25_-69.25` | Altiplano and Puna | 0.611 | 0.67 | 1.00 | 0.23 | 1.00 | 0.95 | Sep, Apr, Oct | 10.6 °C | 19 mm |
| 10 | `m_-72.25_68.75` | Antarctica | 0.610 | 1.00 | 0.73 | 0.61 | 0.52 | 0.00 | none | -21.3 °C | 57 mm |

**Closest on all five factors**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_35.75_85.75` | Tibetan Plateau | 0.703 | 0.80 | 0.76 | 0.44 | 0.95 | 0.67 | Apr, Sep, May | -7.1 °C | 51 mm |
| 2 | `m_-22.25_-68.25` | Altiplano and Puna | 0.694 | 0.71 | 0.83 | 0.30 | 0.90 | 1.00 | Aug, Sep, Apr | 4.4 °C | 42 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.691 | 0.78 | 0.65 | 0.46 | 1.00 | 0.68 | Apr, Sep, May | -9.3 °C | 72 mm |
| 4 | `m_37.25_88.75` | Tibetan Plateau | 0.681 | 0.75 | 0.76 | 0.41 | 1.00 | 0.63 | Apr, Sep, May | -4.8 °C | 51 mm |
| 5 | `m_-25.25_-69.25` | Altiplano and Puna | 0.679 | 0.67 | 1.00 | 0.23 | 1.00 | 0.95 | Sep, Apr, Oct | 10.6 °C | 19 mm |
| 6 | `m_33.25_82.75` | Tibetan Plateau | 0.675 | 0.80 | 0.59 | 0.41 | 0.99 | 0.73 | Mar, Apr, May | -4.6 °C | 86 mm |
| 7 | `m_38.75_93.75` | Qaidam Basin | 0.670 | 0.75 | 0.90 | 0.34 | 1.00 | 0.58 | Apr, May, Sep | 0.9 °C | 34 mm |
| 8 | `m_-19.25_-70.25` | Atacama Desert | 0.661 | 0.88 | 1.00 | 0.14 | 0.99 | 1.00 | Aug, Sep, Oct | 17.8 °C | 20 mm |
| 9 | `m_-29.75_-70.25` | Altiplano and Puna | 0.645 | 0.70 | 0.61 | 0.35 | 0.91 | 0.83 | Sep, Oct, Nov | 0.5 °C | 81 mm |
| 10 | `m_38.25_74.25` | Pamir and Karakoram | 0.640 | 0.71 | 0.66 | 0.40 | 0.97 | 0.60 | Sep, Apr, May | -3.7 °C | 70 mm |

The closest square on all factors is `m_35.75_85.75` (Tibetan Plateau), with a score of 0.703.
There, Mars is 47.6 °C colder in the yearly mean.
The square gets 2.03 times 25 mm of precipitation a year.
Mars air pressure is 1.46 % of the square's.

### Hellas Rim

Caveats: it is not a climate match, and a score is a position on each factor's own scale, not a share of likeness.

**Closest by landscape (slopes and bare ground)**

187 ranked squares tie at the top score of 1.000, so their order here is not a ranking. Tied squares are listed by bare area, then by environment score.

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_12.75_41.25` | Danakil Depression | 1.000 | 1.00 | 0.21 | 0.00 | 1.00 | 0.44 | Jan, Dec, Feb | 33.1 °C | 266 mm |
| 2 | `m_15.75_50.75` | Arabian Desert | 1.000 | 1.00 | 0.94 | 0.04 | 1.00 | 0.50 | Jan, Dec, Feb | 25.8 °C | 30 mm |
| 3 | `m_15.75_47.75` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.03 | 1.00 | 0.50 | Jan, Dec, Feb | 26.6 °C | 17 mm |
| 4 | `m_17.75_23.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.05 | 1.00 | 0.54 | Jan, Dec, Feb | 24.6 °C | 10 mm |
| 5 | `m_17.75_36.75` | Sahara | 1.000 | 1.00 | 0.68 | 0.04 | 1.00 | 0.54 | Feb, Jan, Mar | 26.3 °C | 65 mm |
| 6 | `m_18.75_43.75` | Arabian Desert | 1.000 | 1.00 | 0.85 | 0.05 | 1.00 | 0.56 | Dec, Jan, Nov | 24.4 °C | 39 mm |
| 7 | `m_18.75_9.25` | Sahara | 1.000 | 1.00 | 0.75 | 0.05 | 1.00 | 0.56 | Jan, Dec, Feb | 25.0 °C | 54 mm |
| 8 | `m_19.75_18.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.08 | 1.00 | 0.58 | Jan, Dec, Feb | 21.9 °C | 14 mm |
| 9 | `m_20.25_-13.25` | Sahara | 1.000 | 1.00 | 0.30 | 0.02 | 1.00 | 0.59 | Jan, Dec, Feb | 27.5 °C | 204 mm |
| 10 | `m_20.75_36.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.02 | 1.00 | 0.60 | Jan, Feb, Dec | 27.6 °C | 25 mm |

**Closest by environment (dry, cold and bare)**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.662 | 0.96 | 0.80 | 0.36 | 1.00 | 0.91 | Jan, Dec, Feb | -7.3 °C | 45 mm |
| 2 | `m_38.75_93.75` | Qaidam Basin | 0.632 | 0.98 | 0.90 | 0.28 | 1.00 | 0.93 | Jan, Dec, Feb | 0.9 °C | 34 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.625 | 1.00 | 0.65 | 0.38 | 1.00 | 0.89 | Dec, Jan, Nov | -9.3 °C | 72 mm |
| 4 | `m_-77.75_164.25` | McMurdo Dry Valleys | 0.620 | 0.57 | 0.61 | 0.47 | 0.83 | 0.20 | Nov, Dec, Jan | -18.9 °C | 80 mm |
| 5 | `m_37.75_89.25` | Tibetan Plateau | 0.614 | 0.98 | 0.75 | 0.31 | 0.99 | 0.93 | Jan, Dec, Feb | -2.0 °C | 52 mm |
| 6 | `m_34.75_83.25` | Tibetan Plateau | 0.604 | 0.97 | 0.64 | 0.35 | 0.99 | 0.88 | Jan, Dec, Feb | -5.8 °C | 73 mm |
| 7 | `m_38.25_74.25` | Pamir and Karakoram | 0.592 | 0.89 | 0.66 | 0.33 | 0.97 | 0.93 | Dec, Jan, Nov | -3.7 °C | 70 mm |
| 8 | `m_81.25_-72.25` | Ellesmere or north-west Greenland | 0.576 | 0.79 | 0.45 | 0.46 | 0.92 | 0.13 | May, Jun, Jul | -17.4 °C | 129 mm |
| 9 | `m_-25.25_-69.25` | Altiplano and Puna | 0.572 | 0.86 | 1.00 | 0.19 | 1.00 | 0.69 | Jul, Jun, Aug | 10.6 °C | 19 mm |
| 10 | `m_-72.25_68.75` | Antarctica | 0.571 | 0.58 | 0.73 | 0.50 | 0.52 | 0.31 | Oct, Feb, Jan | -21.3 °C | 57 mm |

**Closest on all five factors**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.75_86.25` | Tibetan Plateau | 0.764 | 0.99 | 0.81 | 0.35 | 1.00 | 0.92 | Jan, Dec, Feb | -6.4 °C | 44 mm |
| 2 | `m_38.75_93.75` | Qaidam Basin | 0.746 | 0.98 | 0.90 | 0.28 | 1.00 | 0.93 | Jan, Dec, Feb | 0.9 °C | 34 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.737 | 1.00 | 0.65 | 0.38 | 1.00 | 0.89 | Dec, Jan, Nov | -9.3 °C | 72 mm |
| 4 | `m_35.25_83.25` | Tibetan Plateau | 0.733 | 1.00 | 0.66 | 0.36 | 1.00 | 0.89 | Jan, Dec, Feb | -7.0 °C | 68 mm |
| 5 | `m_37.25_89.75` | Tibetan Plateau | 0.730 | 1.00 | 0.71 | 0.31 | 1.00 | 0.93 | Jan, Dec, Feb | -2.3 °C | 59 mm |
| 6 | `m_38.25_74.25` | Pamir and Karakoram | 0.703 | 0.89 | 0.66 | 0.33 | 0.97 | 0.93 | Dec, Jan, Nov | -3.7 °C | 70 mm |
| 7 | `m_41.25_89.25` | Taklamakan and Tarim Basin | 0.693 | 1.00 | 0.89 | 0.20 | 1.00 | 0.92 | Jan, Feb, Nov | 9.8 °C | 35 mm |
| 8 | `m_44.25_97.25` | Gobi Desert | 0.675 | 1.00 | 0.70 | 0.23 | 1.00 | 0.86 | Feb, Nov, Mar | 6.1 °C | 60 mm |
| 9 | `m_32.75_81.75` | Tibetan Plateau | 0.670 | 0.95 | 0.58 | 0.31 | 0.94 | 0.84 | Dec, Nov, Jan | -1.7 °C | 88 mm |
| 10 | `m_41.75_95.25` | Gobi Desert | 0.666 | 1.00 | 0.72 | 0.20 | 1.00 | 0.91 | Jan, Feb, Nov | 9.4 °C | 58 mm |

The closest square on all factors is `m_36.75_86.25` (Tibetan Plateau), with a score of 0.764.
There, Mars is 66.9 °C colder in the yearly mean.
The square gets 1.76 times 25 mm of precipitation a year.
Mars air pressure is 1.03 % of the square's.

### Eastern rim of Hellas impact basin

Caveats: it is not a climate match, and a score is a position on each factor's own scale, not a share of likeness.

**Closest by landscape (slopes and bare ground)**

163 ranked squares tie at the top score of 1.000, so their order here is not a ranking. Tied squares are listed by bare area, then by environment score.

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_12.75_41.25` | Danakil Depression | 1.000 | 1.00 | 0.21 | 0.00 | 1.00 | 0.42 | Jan, Dec, Feb | 33.1 °C | 266 mm |
| 2 | `m_15.75_47.75` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.03 | 1.00 | 0.48 | Jan, Dec, Feb | 26.6 °C | 17 mm |
| 3 | `m_17.25_44.75` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.04 | 1.00 | 0.51 | Dec, Jan, Feb | 25.7 °C | 18 mm |
| 4 | `m_17.75_23.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.05 | 1.00 | 0.52 | Jan, Dec, Feb | 24.6 °C | 10 mm |
| 5 | `m_18.75_36.25` | Sahara | 1.000 | 1.00 | 0.79 | 0.03 | 1.00 | 0.54 | Jan, Feb, Mar | 27.2 °C | 46 mm |
| 6 | `m_19.25_8.75` | Sahara | 1.000 | 1.00 | 0.89 | 0.06 | 1.00 | 0.55 | Jan, Dec, Feb | 24.1 °C | 34 mm |
| 7 | `m_19.25_19.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.04 | 1.00 | 0.55 | Jan, Dec, Feb | 25.8 °C | 5 mm |
| 8 | `m_20.25_16.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.03 | 1.00 | 0.57 | Jan, Dec, Feb | 26.4 °C | 19 mm |
| 9 | `m_20.25_-13.25` | Sahara | 1.000 | 1.00 | 0.30 | 0.02 | 1.00 | 0.57 | Jan, Dec, Feb | 27.5 °C | 204 mm |
| 10 | `m_20.75_34.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.02 | 1.00 | 0.58 | Jan, Dec, Feb | 28.0 °C | 8 mm |

**Closest by environment (dry, cold and bare)**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.659 | 0.84 | 0.80 | 0.36 | 1.00 | 0.89 | Jan, Dec, Feb | -7.3 °C | 45 mm |
| 2 | `m_38.75_93.75` | Qaidam Basin | 0.630 | 0.85 | 0.90 | 0.28 | 1.00 | 0.93 | Jan, Dec, Feb | 0.9 °C | 34 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.623 | 1.00 | 0.65 | 0.38 | 1.00 | 0.87 | Dec, Jan, Nov | -9.3 °C | 72 mm |
| 4 | `m_-77.75_164.25` | McMurdo Dry Valleys | 0.618 | 0.61 | 0.61 | 0.47 | 0.83 | 0.22 | Nov, Dec, Jan | -18.9 °C | 80 mm |
| 5 | `m_37.75_89.25` | Tibetan Plateau | 0.611 | 0.88 | 0.75 | 0.31 | 0.99 | 0.92 | Jan, Dec, Feb | -2.0 °C | 52 mm |
| 6 | `m_34.75_83.25` | Tibetan Plateau | 0.601 | 0.83 | 0.64 | 0.34 | 0.99 | 0.86 | Jan, Dec, Feb | -5.8 °C | 73 mm |
| 7 | `m_38.25_74.25` | Pamir and Karakoram | 0.589 | 0.83 | 0.66 | 0.32 | 0.97 | 0.93 | Dec, Jan, Nov | -3.7 °C | 70 mm |
| 8 | `m_81.25_-72.25` | Ellesmere or north-west Greenland | 0.573 | 0.69 | 0.45 | 0.45 | 0.92 | 0.15 | May, Jun, Jul | -17.4 °C | 129 mm |
| 9 | `m_-25.25_-69.25` | Altiplano and Puna | 0.569 | 0.73 | 1.00 | 0.19 | 1.00 | 0.67 | Jul, Jun, Aug | 10.6 °C | 19 mm |
| 10 | `m_-72.25_68.75` | Antarctica | 0.568 | 0.65 | 0.73 | 0.49 | 0.52 | 0.33 | Oct, Feb, Jan | -21.3 °C | 57 mm |

**Closest on all five factors**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_87.75` | Tibetan Plateau | 0.741 | 0.93 | 0.76 | 0.36 | 0.98 | 0.89 | Jan, Dec, Feb | -7.7 °C | 51 mm |
| 2 | `m_38.75_92.75` | Qaidam Basin | 0.739 | 0.98 | 0.91 | 0.26 | 1.00 | 0.93 | Jan, Dec, Feb | 2.4 °C | 32 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.732 | 1.00 | 0.65 | 0.38 | 1.00 | 0.87 | Dec, Jan, Nov | -9.3 °C | 72 mm |
| 4 | `m_35.25_84.25` | Tibetan Plateau | 0.723 | 0.99 | 0.68 | 0.34 | 0.99 | 0.87 | Jan, Dec, Feb | -5.7 °C | 66 mm |
| 5 | `m_38.25_74.25` | Pamir and Karakoram | 0.692 | 0.83 | 0.66 | 0.32 | 0.97 | 0.93 | Dec, Jan, Nov | -3.7 °C | 70 mm |
| 6 | `m_41.25_89.25` | Taklamakan and Tarim Basin | 0.686 | 0.95 | 0.89 | 0.19 | 1.00 | 0.93 | Jan, Dec, Feb | 9.8 °C | 35 mm |
| 7 | `m_32.75_82.75` | Tibetan Plateau | 0.668 | 0.98 | 0.56 | 0.30 | 0.99 | 0.82 | Dec, Nov, Jan | -1.0 °C | 93 mm |
| 8 | `m_44.25_97.25` | Gobi Desert | 0.665 | 0.92 | 0.70 | 0.23 | 1.00 | 0.88 | Feb, Nov, Mar | 6.1 °C | 60 mm |
| 9 | `m_41.75_95.75` | Gobi Desert | 0.663 | 0.88 | 0.68 | 0.23 | 1.00 | 0.93 | Jan, Dec, Feb | 5.9 °C | 66 mm |
| 10 | `m_42.25_101.75` | Gobi Desert | 0.657 | 0.91 | 0.72 | 0.20 | 1.00 | 0.92 | Jan, Feb, Nov | 8.7 °C | 59 mm |

The closest square on all factors is `m_36.25_87.75` (Tibetan Plateau), with a score of 0.741.
There, Mars is 67.0 °C colder in the yearly mean.
The square gets 2.03 times 25 mm of precipitation a year.
Mars air pressure is 1.11 % of the square's.

### Columbus crater

Caveats: it is not a climate match, and a score is a position on each factor's own scale, not a share of likeness.

**Closest by landscape (slopes and bare ground)**

25 ranked squares tie at the top score of 1.000, so their order here is not a ranking. Tied squares are listed by bare area, then by environment score.

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_12.75_41.25` | Danakil Depression | 1.000 | 1.00 | 0.21 | 0.00 | 1.00 | 0.64 | Jan, Dec, Feb | 33.1 °C | 266 mm |
| 2 | `m_19.25_8.75` | Sahara | 1.000 | 1.00 | 0.89 | 0.06 | 1.00 | 0.77 | Jan, Dec, Feb | 24.1 °C | 34 mm |
| 3 | `m_19.75_18.25` | Sahara | 1.000 | 1.00 | 0.99 | 0.06 | 1.00 | 0.78 | Jan, Dec, Feb | 24.1 °C | 26 mm |
| 4 | `m_20.75_36.75` | Sahara | 1.000 | 1.00 | 0.90 | 0.02 | 1.00 | 0.80 | Feb, Jan, Mar | 28.0 °C | 34 mm |
| 5 | `m_-21.75_-69.25` | Atacama Desert | 1.000 | 1.00 | 1.00 | 0.13 | 1.00 | 0.82 | Jul, Jun, Aug | 17.7 °C | 21 mm |
| 6 | `m_24.25_5.75` | Sahara | 1.000 | 1.00 | 0.74 | 0.08 | 1.00 | 0.87 | Jan, Dec, Feb | 22.1 °C | 55 mm |
| 7 | `m_24.25_34.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.04 | 1.00 | 0.87 | Jan, Feb, Dec | 25.8 °C | 7 mm |
| 8 | `m_-25.25_-68.75` | Altiplano and Puna | 1.000 | 1.00 | 0.44 | 0.28 | 1.00 | 0.89 | Jul, Jun, Aug | 3.3 °C | 134 mm |
| 9 | `m_25.75_65.25` | other | 1.000 | 1.00 | 0.59 | 0.04 | 1.00 | 0.90 | Jan, Dec, Feb | 26.4 °C | 86 mm |
| 10 | `m_26.25_37.25` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.07 | 1.00 | 0.91 | Feb, Dec, Jan | 23.0 °C | 16 mm |

**Closest by environment (dry, cold and bare)**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.679 | 0.79 | 0.80 | 0.39 | 1.00 | 0.82 | Feb, Mar, Oct | -7.3 °C | 45 mm |
| 2 | `m_38.75_93.75` | Qaidam Basin | 0.649 | 0.93 | 0.90 | 0.30 | 1.00 | 0.77 | Feb, Mar, Oct | 0.9 °C | 34 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.642 | 1.00 | 0.65 | 0.41 | 1.00 | 0.84 | Nov, Feb, Mar | -9.3 °C | 72 mm |
| 4 | `m_-77.75_164.25` | McMurdo Dry Valleys | 0.636 | 0.66 | 0.61 | 0.51 | 0.83 | 0.00 | none | -18.9 °C | 80 mm |
| 5 | `m_37.75_89.25` | Tibetan Plateau | 0.629 | 0.98 | 0.75 | 0.33 | 0.99 | 0.79 | Feb, Mar, Oct | -2.0 °C | 52 mm |
| 6 | `m_34.75_83.25` | Tibetan Plateau | 0.620 | 0.85 | 0.64 | 0.37 | 0.99 | 0.85 | Feb, Nov, Mar | -5.8 °C | 73 mm |
| 7 | `m_38.25_74.25` | Pamir and Karakoram | 0.607 | 0.94 | 0.66 | 0.35 | 0.97 | 0.78 | Feb, Oct, Mar | -3.7 °C | 70 mm |
| 8 | `m_81.25_-72.25` | Ellesmere or north-west Greenland | 0.590 | 0.81 | 0.45 | 0.50 | 0.92 | 0.00 | none | -17.4 °C | 129 mm |
| 9 | `m_-25.25_-69.25` | Altiplano and Puna | 0.587 | 0.82 | 1.00 | 0.20 | 1.00 | 0.89 | Jul, Jun, Aug | 10.6 °C | 19 mm |
| 10 | `m_-72.25_68.75` | Antarctica | 0.586 | 0.65 | 0.73 | 0.54 | 0.52 | 0.11 | Jan, Dec, Nov | -21.3 °C | 57 mm |

**Closest on all five factors**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_35.25_79.75` | Tibetan Plateau | 0.740 | 1.00 | 0.65 | 0.41 | 1.00 | 0.84 | Nov, Feb, Mar | -9.3 °C | 72 mm |
| 2 | `m_36.75_86.25` | Tibetan Plateau | 0.740 | 0.89 | 0.81 | 0.38 | 1.00 | 0.81 | Feb, Mar, Oct | -6.4 °C | 44 mm |
| 3 | `m_38.75_93.75` | Qaidam Basin | 0.723 | 0.93 | 0.90 | 0.30 | 1.00 | 0.77 | Feb, Mar, Oct | 0.9 °C | 34 mm |
| 4 | `m_37.25_90.25` | Tibetan Plateau | 0.712 | 1.00 | 0.71 | 0.34 | 0.95 | 0.80 | Feb, Mar, Oct | -2.3 °C | 59 mm |
| 5 | `m_35.25_83.25` | Tibetan Plateau | 0.711 | 0.84 | 0.66 | 0.39 | 1.00 | 0.84 | Feb, Nov, Mar | -7.0 °C | 68 mm |
| 6 | `m_38.25_74.25` | Pamir and Karakoram | 0.697 | 0.94 | 0.66 | 0.35 | 0.97 | 0.78 | Feb, Oct, Mar | -3.7 °C | 70 mm |
| 7 | `m_32.25_80.75` | Tibetan Plateau | 0.696 | 0.95 | 0.58 | 0.35 | 0.94 | 0.90 | Nov, Jan, Mar | -3.4 °C | 87 mm |
| 8 | `m_-22.25_-68.25` | Altiplano and Puna | 0.688 | 0.92 | 0.83 | 0.27 | 0.90 | 0.83 | Jul, Jun, Aug | 4.4 °C | 42 mm |
| 9 | `m_-26.25_-69.25` | Atacama Desert | 0.686 | 0.92 | 0.87 | 0.21 | 1.00 | 0.91 | Jul, Jun, Aug | 9.9 °C | 37 mm |
| 10 | `m_36.25_95.25` | Tibetan Plateau | 0.654 | 1.00 | 0.66 | 0.24 | 0.91 | 0.82 | Feb, Mar, Oct | 6.7 °C | 69 mm |

The closest square on all factors is `m_35.25_79.75` (Tibetan Plateau), with a score of 0.740.
There, Mars is 56.4 °C colder in the yearly mean.
The square gets 2.89 times 25 mm of precipitation a year.
Mars air pressure is 1.00 % of the square's.

### South-west Sinus Meridiani

Caveats: it is not a climate match, and a score is a position on each factor's own scale, not a share of likeness.

**Closest by landscape (slopes and bare ground)**

1,102 ranked squares tie at the top score of 1.000, so their order here is not a ranking. Tied squares are listed by bare area, then by environment score.

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_15.25_27.75` | Sahara | 1.000 | 1.00 | 0.66 | 0.06 | 1.00 | 1.00 | Mar, Apr, Oct | 24.8 °C | 70 mm |
| 2 | `m_15.75_47.25` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.04 | 1.00 | 1.00 | Oct, Mar, Apr | 26.6 °C | 17 mm |
| 3 | `m_16.25_23.25` | Sahara | 1.000 | 1.00 | 0.74 | 0.08 | 1.00 | 1.00 | Mar, Oct, Apr | 23.3 °C | 55 mm |
| 4 | `m_16.25_50.25` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.05 | 1.00 | 1.00 | Mar, Oct, Apr | 25.6 °C | 24 mm |
| 5 | `m_16.25_30.75` | Sahara | 1.000 | 1.00 | 0.74 | 0.03 | 1.00 | 1.00 | Mar, Apr, Oct | 27.3 °C | 55 mm |
| 6 | `m_17.25_44.75` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.05 | 1.00 | 1.00 | Oct, Mar, Apr | 25.7 °C | 18 mm |
| 7 | `m_17.75_20.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.04 | 1.00 | 1.00 | Mar, Oct, Apr | 26.8 °C | 18 mm |
| 8 | `m_17.75_9.75` | Sahara | 1.000 | 1.00 | 0.78 | 0.04 | 1.00 | 1.00 | Mar, Oct, Apr | 26.5 °C | 48 mm |
| 9 | `m_17.75_54.75` | Arabian Desert | 1.000 | 1.00 | 0.37 | 0.04 | 1.00 | 1.00 | Oct, Apr | 26.5 °C | 163 mm |
| 10 | `m_18.25_26.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.06 | 1.00 | 1.00 | Mar, Apr, Oct | 24.6 °C | 4 mm |

**Closest by environment (dry, cold and bare)**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.707 | 0.79 | 0.80 | 0.44 | 1.00 | 0.53 | Apr, May, Aug | -7.3 °C | 45 mm |
| 2 | `m_38.75_93.75` | Qaidam Basin | 0.676 | 0.48 | 0.90 | 0.34 | 1.00 | 0.44 | May, Aug, Jun | 0.9 °C | 34 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.668 | 0.76 | 0.65 | 0.46 | 1.00 | 0.57 | Apr, May, Jul | -9.3 °C | 72 mm |
| 4 | `m_-77.75_164.25` | McMurdo Dry Valleys | 0.663 | 0.17 | 0.61 | 0.58 | 0.83 | 0.00 | none | -18.9 °C | 80 mm |
| 5 | `m_37.75_89.25` | Tibetan Plateau | 0.656 | 0.53 | 0.75 | 0.38 | 0.99 | 0.48 | May, Aug, Jun | -2.0 °C | 52 mm |
| 6 | `m_34.75_83.25` | Tibetan Plateau | 0.645 | 0.66 | 0.64 | 0.42 | 0.99 | 0.59 | Apr, May, Jun | -5.8 °C | 73 mm |
| 7 | `m_38.25_74.25` | Pamir and Karakoram | 0.632 | 0.41 | 0.66 | 0.40 | 0.97 | 0.46 | May, Aug, Jun | -3.7 °C | 70 mm |
| 8 | `m_81.25_-72.25` | Ellesmere or north-west Greenland | 0.615 | 0.28 | 0.45 | 0.56 | 0.92 | 0.00 | none | -17.4 °C | 129 mm |
| 9 | `m_-25.25_-69.25` | Altiplano and Puna | 0.611 | 0.36 | 1.00 | 0.23 | 1.00 | 0.93 | Oct, Nov, Mar | 10.6 °C | 19 mm |
| 10 | `m_-72.25_68.75` | Antarctica | 0.610 | 0.19 | 0.73 | 0.61 | 0.52 | 0.00 | none | -21.3 °C | 57 mm |

**Closest on all five factors**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_35.75_86.25` | Tibetan Plateau | 0.702 | 0.99 | 0.77 | 0.43 | 0.95 | 0.55 | Apr, May, Aug | -6.5 °C | 50 mm |
| 2 | `m_35.25_82.75` | Tibetan Plateau | 0.699 | 0.99 | 0.66 | 0.46 | 0.98 | 0.57 | Apr, May, Aug | -8.5 °C | 69 mm |
| 3 | `m_-22.75_-69.75` | Atacama Desert | 0.688 | 1.00 | 1.00 | 0.15 | 1.00 | 1.00 | Sep, Oct, Nov | 17.0 °C | 8 mm |
| 4 | `m_34.75_79.25` | Tibetan Plateau | 0.686 | 1.00 | 0.58 | 0.45 | 1.00 | 0.59 | Apr, May, Jun | -7.9 °C | 88 mm |
| 5 | `m_37.25_89.75` | Tibetan Plateau | 0.670 | 1.00 | 0.71 | 0.38 | 1.00 | 0.50 | Apr, May, Aug | -2.3 °C | 59 mm |
| 6 | `m_38.25_93.25` | Qaidam Basin | 0.668 | 1.00 | 0.94 | 0.31 | 1.00 | 0.46 | May, Aug, Jun | 4.0 °C | 30 mm |
| 7 | `m_23.75_26.25` | Sahara | 0.654 | 1.00 | 1.00 | 0.12 | 1.00 | 0.99 | Mar, Apr, May | 19.8 °C | 2 mm |
| 8 | `m_-19.75_-69.75` | Atacama Desert | 0.641 | 0.75 | 1.00 | 0.14 | 1.00 | 1.00 | Sep, Oct, Nov | 17.8 °C | 15 mm |
| 9 | `m_23.75_11.75` | Sahara | 0.637 | 1.00 | 1.00 | 0.11 | 1.00 | 0.99 | Mar, Apr, Sep | 21.0 °C | 20 mm |
| 10 | `m_23.75_21.75` | Sahara | 0.626 | 1.00 | 1.00 | 0.10 | 1.00 | 0.99 | Mar, Apr, May | 21.8 °C | 2 mm |

The closest square on all factors is `m_35.75_86.25` (Tibetan Plateau), with a score of 0.702.
There, Mars is 48.1 °C colder in the yearly mean.
The square gets 2.02 times 25 mm of precipitation a year.
Mars air pressure is 1.18 % of the square's.

### Apollinaris Sulci

Caveats: it is not a climate match, and a score is a position on each factor's own scale, not a share of likeness.

**Closest by landscape (slopes and bare ground)**

149 ranked squares tie at the top score of 1.000, so their order here is not a ranking. Tied squares are listed by bare area, then by environment score.

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_12.75_41.25` | Danakil Depression | 1.000 | 1.00 | 0.21 | 0.00 | 1.00 | 0.96 | Jan, Dec, Feb | 33.1 °C | 266 mm |
| 2 | `m_15.75_50.75` | Arabian Desert | 1.000 | 1.00 | 0.94 | 0.04 | 1.00 | 1.00 | Jan, Feb, Nov | 25.8 °C | 30 mm |
| 3 | `m_16.75_44.75` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.05 | 1.00 | 1.00 | Jan, Nov, Feb | 24.9 °C | 19 mm |
| 4 | `m_17.75_36.75` | Sahara | 1.000 | 1.00 | 0.68 | 0.04 | 1.00 | 1.00 | Feb, Mar, Nov | 26.3 °C | 65 mm |
| 5 | `m_18.75_9.25` | Sahara | 1.000 | 1.00 | 0.75 | 0.05 | 1.00 | 1.00 | Feb, Nov, Mar | 25.0 °C | 54 mm |
| 6 | `m_19.25_43.25` | Arabian Desert | 1.000 | 1.00 | 0.91 | 0.05 | 1.00 | 1.00 | Feb, Nov, Mar | 25.2 °C | 33 mm |
| 7 | `m_19.75_18.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.08 | 1.00 | 1.00 | Feb, Mar, Oct | 21.9 °C | 14 mm |
| 8 | `m_20.75_36.75` | Sahara | 1.000 | 1.00 | 0.90 | 0.02 | 1.00 | 1.00 | Feb, Mar, Apr | 28.0 °C | 34 mm |
| 9 | `m_-21.25_-69.75` | Atacama Desert | 1.000 | 1.00 | 1.00 | 0.13 | 1.00 | 1.00 | Aug, Sep, Oct | 17.8 °C | 9 mm |
| 10 | `m_21.75_16.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.07 | 1.00 | 1.00 | Feb, Mar, Oct | 23.2 °C | 11 mm |

**Closest by environment (dry, cold and bare)**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.675 | 0.96 | 0.80 | 0.38 | 1.00 | 0.66 | Apr, Sep, May | -7.3 °C | 45 mm |
| 2 | `m_38.75_93.75` | Qaidam Basin | 0.646 | 1.00 | 0.90 | 0.30 | 1.00 | 0.60 | Apr, May, Sep | 0.9 °C | 34 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.638 | 1.00 | 0.65 | 0.40 | 1.00 | 0.69 | Mar, Apr, Sep | -9.3 °C | 72 mm |
| 4 | `m_-77.75_164.25` | McMurdo Dry Valleys | 0.633 | 0.53 | 0.61 | 0.50 | 0.83 | 0.00 | none | -18.9 °C | 80 mm |
| 5 | `m_37.75_89.25` | Tibetan Plateau | 0.626 | 0.96 | 0.75 | 0.33 | 0.99 | 0.62 | Apr, Sep, May | -2.0 °C | 52 mm |
| 6 | `m_34.75_83.25` | Tibetan Plateau | 0.617 | 1.00 | 0.64 | 0.37 | 0.99 | 0.70 | Mar, Apr, May | -5.8 °C | 73 mm |
| 7 | `m_38.25_74.25` | Pamir and Karakoram | 0.604 | 0.85 | 0.66 | 0.35 | 0.97 | 0.61 | Sep, Apr, May | -3.7 °C | 70 mm |
| 8 | `m_81.25_-72.25` | Ellesmere or north-west Greenland | 0.588 | 0.81 | 0.45 | 0.49 | 0.92 | 0.00 | none | -17.4 °C | 129 mm |
| 9 | `m_-25.25_-69.25` | Altiplano and Puna | 0.584 | 0.89 | 1.00 | 0.20 | 1.00 | 0.95 | Sep, Apr, Oct | 10.6 °C | 19 mm |
| 10 | `m_-72.25_68.75` | Antarctica | 0.583 | 0.56 | 0.73 | 0.53 | 0.52 | 0.00 | none | -21.3 °C | 57 mm |

**Closest on all five factors**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.75_86.25` | Tibetan Plateau | 0.723 | 1.00 | 0.81 | 0.37 | 1.00 | 0.65 | Apr, Sep, May | -6.4 °C | 44 mm |
| 2 | `m_35.25_79.75` | Tibetan Plateau | 0.709 | 1.00 | 0.65 | 0.40 | 1.00 | 0.69 | Mar, Apr, Sep | -9.3 °C | 72 mm |
| 3 | `m_-22.25_-68.25` | Altiplano and Puna | 0.708 | 0.90 | 0.83 | 0.26 | 0.90 | 1.00 | Aug, Sep, Apr | 4.4 °C | 42 mm |
| 4 | `m_35.25_83.25` | Tibetan Plateau | 0.705 | 1.00 | 0.66 | 0.38 | 1.00 | 0.69 | Mar, Apr, Sep | -7.0 °C | 68 mm |
| 5 | `m_-25.25_-69.25` | Altiplano and Puna | 0.701 | 0.89 | 1.00 | 0.20 | 1.00 | 0.95 | Sep, Apr, Oct | 10.6 °C | 19 mm |
| 6 | `m_38.75_93.75` | Qaidam Basin | 0.693 | 1.00 | 0.90 | 0.30 | 1.00 | 0.60 | Apr, May, Sep | 0.9 °C | 34 mm |
| 7 | `m_37.25_90.25` | Tibetan Plateau | 0.677 | 1.00 | 0.71 | 0.33 | 0.95 | 0.64 | Apr, Sep, May | -2.3 °C | 59 mm |
| 8 | `m_32.75_81.75` | Tibetan Plateau | 0.666 | 0.98 | 0.58 | 0.33 | 0.94 | 0.75 | Mar, Apr, May | -1.7 °C | 88 mm |
| 9 | `m_-18.75_-70.25` | Atacama Desert | 0.662 | 0.99 | 0.98 | 0.13 | 0.99 | 1.00 | Aug, Sep, May | 17.2 °C | 26 mm |
| 10 | `m_38.25_74.25` | Pamir and Karakoram | 0.647 | 0.85 | 0.66 | 0.35 | 0.97 | 0.61 | Sep, Apr, May | -3.7 °C | 70 mm |

The closest square on all factors is `m_36.75_86.25` (Tibetan Plateau), with a score of 0.723.
There, Mars is 60.7 °C colder in the yearly mean.
The square gets 1.76 times 25 mm of precipitation a year.
Mars air pressure is 1.21 % of the square's.

### Deuteronilus Mensae (debris apron zone)

Caveats: it is not a climate match, and a score is a position on each factor's own scale, not a share of likeness.

**Closest by landscape (slopes and bare ground)**

264 ranked squares tie at the top score of 1.000, so their order here is not a ranking. Tied squares are listed by bare area, then by environment score.

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_12.75_41.25` | Danakil Depression | 1.000 | 1.00 | 0.21 | 0.00 | 1.00 | 0.40 | Jan, Dec, Feb | 33.1 °C | 266 mm |
| 2 | `m_15.75_50.75` | Arabian Desert | 1.000 | 1.00 | 0.94 | 0.04 | 1.00 | 0.46 | Jan, Dec, Feb | 25.8 °C | 30 mm |
| 3 | `m_16.25_47.75` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.04 | 1.00 | 0.47 | Jan, Dec, Feb | 25.7 °C | 21 mm |
| 4 | `m_17.25_44.75` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.04 | 1.00 | 0.49 | Dec, Jan, Feb | 25.7 °C | 18 mm |
| 5 | `m_17.75_23.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.05 | 1.00 | 0.50 | Jan, Dec, Feb | 24.6 °C | 10 mm |
| 6 | `m_17.75_36.75` | Sahara | 1.000 | 1.00 | 0.68 | 0.04 | 1.00 | 0.50 | Feb, Jan, Mar | 26.3 °C | 65 mm |
| 7 | `m_18.25_9.25` | Sahara | 1.000 | 1.00 | 0.64 | 0.04 | 1.00 | 0.51 | Jan, Dec, Feb | 25.5 °C | 73 mm |
| 8 | `m_18.25_32.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.01 | 1.00 | 0.51 | Jan, Dec, Feb | 28.6 °C | 13 mm |
| 9 | `m_19.25_19.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.04 | 1.00 | 0.53 | Jan, Dec, Feb | 25.8 °C | 5 mm |
| 10 | `m_19.25_-12.75` | Sahara | 1.000 | 1.00 | 0.49 | 0.02 | 1.00 | 0.53 | Jan, Dec, Feb | 28.1 °C | 114 mm |

**Closest by environment (dry, cold and bare)**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.663 | 1.00 | 0.80 | 0.36 | 1.00 | 0.87 | Jan, Dec, Feb | -7.3 °C | 45 mm |
| 2 | `m_38.75_93.75` | Qaidam Basin | 0.634 | 0.86 | 0.90 | 0.28 | 1.00 | 0.92 | Jan, Dec, Feb | 0.9 °C | 34 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.627 | 1.00 | 0.65 | 0.38 | 1.00 | 0.85 | Dec, Jan, Nov | -9.3 °C | 72 mm |
| 4 | `m_-77.75_164.25` | McMurdo Dry Valleys | 0.622 | 0.42 | 0.61 | 0.48 | 0.83 | 0.24 | Nov, Dec, Jan | -18.9 °C | 80 mm |
| 5 | `m_37.75_89.25` | Tibetan Plateau | 0.615 | 0.83 | 0.75 | 0.31 | 0.99 | 0.90 | Jan, Dec, Feb | -2.0 °C | 52 mm |
| 6 | `m_34.75_83.25` | Tibetan Plateau | 0.605 | 0.98 | 0.64 | 0.35 | 0.99 | 0.84 | Jan, Dec, Feb | -5.8 °C | 73 mm |
| 7 | `m_38.25_74.25` | Pamir and Karakoram | 0.593 | 0.70 | 0.66 | 0.33 | 0.97 | 0.91 | Dec, Jan, Nov | -3.7 °C | 70 mm |
| 8 | `m_81.25_-72.25` | Ellesmere or north-west Greenland | 0.577 | 0.60 | 0.45 | 0.46 | 0.92 | 0.17 | May, Jun, Jul | -17.4 °C | 129 mm |
| 9 | `m_-25.25_-69.25` | Altiplano and Puna | 0.573 | 0.70 | 1.00 | 0.19 | 1.00 | 0.65 | Jul, Jun, Aug | 10.6 °C | 19 mm |
| 10 | `m_-72.25_68.75` | Antarctica | 0.572 | 0.49 | 0.73 | 0.50 | 0.52 | 0.34 | Oct, Feb, Jan | -21.3 °C | 57 mm |

**Closest on all five factors**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.760 | 1.00 | 0.80 | 0.36 | 1.00 | 0.87 | Jan, Dec, Feb | -7.3 °C | 45 mm |
| 2 | `m_38.75_92.75` | Qaidam Basin | 0.743 | 1.00 | 0.91 | 0.27 | 1.00 | 0.92 | Jan, Dec, Feb | 2.4 °C | 32 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.732 | 1.00 | 0.65 | 0.38 | 1.00 | 0.85 | Dec, Jan, Nov | -9.3 °C | 72 mm |
| 4 | `m_37.25_89.75` | Tibetan Plateau | 0.724 | 1.00 | 0.71 | 0.31 | 1.00 | 0.89 | Jan, Dec, Feb | -2.3 °C | 59 mm |
| 5 | `m_34.75_83.25` | Tibetan Plateau | 0.711 | 0.98 | 0.64 | 0.35 | 0.99 | 0.84 | Jan, Dec, Feb | -5.8 °C | 73 mm |
| 6 | `m_41.25_89.25` | Taklamakan and Tarim Basin | 0.696 | 1.00 | 0.89 | 0.20 | 1.00 | 0.93 | Jan, Dec, Feb | 9.8 °C | 35 mm |
| 7 | `m_44.25_97.25` | Gobi Desert | 0.682 | 1.00 | 0.70 | 0.23 | 1.00 | 0.90 | Jan, Feb, Nov | 6.1 °C | 60 mm |
| 8 | `m_41.25_96.25` | Gobi Desert | 0.672 | 0.94 | 0.64 | 0.25 | 1.00 | 0.93 | Jan, Dec, Feb | 4.8 °C | 74 mm |
| 9 | `m_38.25_74.25` | Pamir and Karakoram | 0.668 | 0.70 | 0.66 | 0.33 | 0.97 | 0.91 | Dec, Jan, Nov | -3.7 °C | 70 mm |
| 10 | `m_43.25_91.75` | other | 0.663 | 0.84 | 0.75 | 0.22 | 1.00 | 0.92 | Jan, Feb, Mar | 7.5 °C | 52 mm |

The closest square on all factors is `m_36.25_86.25` (Tibetan Plateau), with a score of 0.760.
There, Mars is 65.4 °C colder in the yearly mean.
The square gets 1.81 times 25 mm of precipitation a year.
Mars air pressure is 1.29 % of the square's.

### Ausonia Cavus

Caveats: it is not a climate match, and a score is a position on each factor's own scale, not a share of likeness.

**Closest by landscape (slopes and bare ground)**

435 ranked squares tie at the top score of 1.000, so their order here is not a ranking. Tied squares are listed by bare area, then by environment score.

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_12.75_41.25` | Danakil Depression | 1.000 | 1.00 | 0.21 | 0.00 | 1.00 | 0.58 | Jan, Dec, Feb | 33.1 °C | 266 mm |
| 2 | `m_15.75_25.25` | Sahara | 1.000 | 1.00 | 0.85 | 0.06 | 1.00 | 0.64 | Jan, Dec, Feb | 24.5 °C | 39 mm |
| 3 | `m_15.75_50.75` | Arabian Desert | 1.000 | 1.00 | 0.94 | 0.04 | 1.00 | 0.64 | Jan, Dec, Feb | 25.8 °C | 30 mm |
| 4 | `m_16.25_45.25` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.06 | 1.00 | 0.65 | Dec, Jan, Nov | 23.7 °C | 22 mm |
| 5 | `m_17.75_23.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.06 | 1.00 | 0.68 | Jan, Dec, Feb | 24.6 °C | 10 mm |
| 6 | `m_17.75_36.75` | Sahara | 1.000 | 1.00 | 0.68 | 0.04 | 1.00 | 0.68 | Feb, Jan, Mar | 26.3 °C | 65 mm |
| 7 | `m_18.25_9.25` | Sahara | 1.000 | 1.00 | 0.64 | 0.05 | 1.00 | 0.69 | Jan, Dec, Feb | 25.5 °C | 73 mm |
| 8 | `m_18.75_43.75` | Arabian Desert | 1.000 | 1.00 | 0.85 | 0.06 | 1.00 | 0.70 | Dec, Jan, Nov | 24.4 °C | 39 mm |
| 9 | `m_19.25_19.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.04 | 1.00 | 0.71 | Jan, Dec, Feb | 25.8 °C | 5 mm |
| 10 | `m_19.25_-12.75` | Sahara | 1.000 | 1.00 | 0.49 | 0.02 | 1.00 | 0.71 | Jan, Dec, Feb | 28.1 °C | 114 mm |

**Closest by environment (dry, cold and bare)**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.675 | 1.00 | 0.80 | 0.38 | 1.00 | 0.88 | Feb, Nov, Mar | -7.3 °C | 45 mm |
| 2 | `m_38.75_93.75` | Qaidam Basin | 0.645 | 0.74 | 0.90 | 0.30 | 1.00 | 0.83 | Feb, Mar, Oct | 0.9 °C | 34 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.638 | 0.88 | 0.65 | 0.40 | 1.00 | 0.90 | Jan, Nov, Feb | -9.3 °C | 72 mm |
| 4 | `m_-77.75_164.25` | McMurdo Dry Valleys | 0.633 | 0.32 | 0.61 | 0.50 | 0.83 | 0.06 | Dec, Jan | -18.9 °C | 80 mm |
| 5 | `m_37.75_89.25` | Tibetan Plateau | 0.626 | 0.66 | 0.75 | 0.33 | 0.99 | 0.85 | Feb, Nov, Mar | -2.0 °C | 52 mm |
| 6 | `m_34.75_83.25` | Tibetan Plateau | 0.616 | 0.90 | 0.64 | 0.37 | 0.99 | 0.91 | Jan, Feb, Nov | -5.8 °C | 73 mm |
| 7 | `m_38.25_74.25` | Pamir and Karakoram | 0.604 | 0.58 | 0.66 | 0.35 | 0.97 | 0.84 | Nov, Feb, Oct | -3.7 °C | 70 mm |
| 8 | `m_81.25_-72.25` | Ellesmere or north-west Greenland | 0.587 | 0.48 | 0.45 | 0.49 | 0.92 | 0.00 | none | -17.4 °C | 129 mm |
| 9 | `m_-25.25_-69.25` | Altiplano and Puna | 0.584 | 0.58 | 1.00 | 0.20 | 1.00 | 0.83 | Jul, Jun, Aug | 10.6 °C | 19 mm |
| 10 | `m_-72.25_68.75` | Antarctica | 0.583 | 0.36 | 0.73 | 0.53 | 0.52 | 0.17 | Jan, Dec, Nov | -21.3 °C | 57 mm |

**Closest on all five factors**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.770 | 1.00 | 0.80 | 0.38 | 1.00 | 0.88 | Feb, Nov, Mar | -7.3 °C | 45 mm |
| 2 | `m_35.25_82.75` | Tibetan Plateau | 0.747 | 1.00 | 0.66 | 0.40 | 0.98 | 0.90 | Jan, Nov, Feb | -8.5 °C | 69 mm |
| 3 | `m_38.25_93.25` | Qaidam Basin | 0.733 | 1.00 | 0.94 | 0.27 | 1.00 | 0.84 | Feb, Nov, Mar | 4.0 °C | 30 mm |
| 4 | `m_34.75_79.25` | Tibetan Plateau | 0.729 | 1.00 | 0.58 | 0.39 | 1.00 | 0.91 | Jan, Nov, Feb | -7.9 °C | 88 mm |
| 5 | `m_37.25_89.75` | Tibetan Plateau | 0.727 | 1.00 | 0.71 | 0.33 | 1.00 | 0.86 | Feb, Nov, Mar | -2.3 °C | 59 mm |
| 6 | `m_41.25_90.25` | Taklamakan and Tarim Basin | 0.684 | 1.00 | 0.95 | 0.20 | 1.00 | 0.78 | Feb, Mar, Oct | 10.4 °C | 29 mm |
| 7 | `m_41.75_96.25` | Gobi Desert | 0.666 | 1.00 | 0.66 | 0.26 | 1.00 | 0.77 | Feb, Mar, Oct | 5.0 °C | 69 mm |
| 8 | `m_39.75_86.75` | Taklamakan and Tarim Basin | 0.652 | 1.00 | 0.84 | 0.17 | 1.00 | 0.81 | Feb, Mar, Oct | 13.2 °C | 40 mm |
| 9 | `m_44.25_98.25` | Gobi Desert | 0.652 | 0.96 | 0.67 | 0.25 | 1.00 | 0.72 | Feb, Mar, Oct | 5.5 °C | 67 mm |
| 10 | `m_42.25_101.75` | Gobi Desert | 0.650 | 0.97 | 0.72 | 0.22 | 1.00 | 0.76 | Feb, Mar, Oct | 8.7 °C | 59 mm |

The closest square on all factors is `m_36.25_86.25` (Tibetan Plateau), with a score of 0.770.
There, Mars is 59.9 °C colder in the yearly mean.
The square gets 1.81 times 25 mm of precipitation a year.
Mars air pressure is 1.37 % of the square's.

### Kasei Valles

Caveats: it is not a climate match, and a score is a position on each factor's own scale, not a share of likeness.

**Closest by landscape (slopes and bare ground)**

121 ranked squares tie at the top score of 1.000, so their order here is not a ranking. Tied squares are listed by bare area, then by environment score.

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_12.75_41.25` | Danakil Depression | 1.000 | 1.00 | 0.21 | 0.00 | 1.00 | 0.72 | Jan, Dec, Feb | 33.1 °C | 266 mm |
| 2 | `m_15.75_50.75` | Arabian Desert | 1.000 | 1.00 | 0.94 | 0.04 | 1.00 | 0.78 | Jan, Dec, Feb | 25.8 °C | 30 mm |
| 3 | `m_17.75_36.75` | Sahara | 1.000 | 1.00 | 0.68 | 0.04 | 1.00 | 0.82 | Feb, Jan, Mar | 26.3 °C | 65 mm |
| 4 | `m_18.75_9.25` | Sahara | 1.000 | 1.00 | 0.75 | 0.05 | 1.00 | 0.84 | Jan, Dec, Feb | 25.0 °C | 54 mm |
| 5 | `m_19.75_18.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.08 | 1.00 | 0.86 | Jan, Dec, Feb | 21.9 °C | 14 mm |
| 6 | `m_20.75_36.75` | Sahara | 1.000 | 1.00 | 0.90 | 0.02 | 1.00 | 0.88 | Feb, Jan, Mar | 28.0 °C | 34 mm |
| 7 | `m_-21.25_-69.75` | Atacama Desert | 1.000 | 1.00 | 1.00 | 0.12 | 1.00 | 0.89 | Jul, Aug, Sep | 17.8 °C | 9 mm |
| 8 | `m_21.75_12.75` | Sahara | 1.000 | 1.00 | 0.89 | 0.05 | 1.00 | 0.90 | Jan, Dec, Feb | 24.7 °C | 35 mm |
| 9 | `m_22.75_18.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.06 | 1.00 | 0.92 | Jan, Dec, Feb | 23.8 °C | 6 mm |
| 10 | `m_22.75_6.25` | Sahara | 1.000 | 1.00 | 0.51 | 0.08 | 1.00 | 0.92 | Jan, Dec, Feb | 21.7 °C | 107 mm |

**Closest by environment (dry, cold and bare)**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.657 | 0.95 | 0.80 | 0.35 | 1.00 | 0.74 | Feb, Mar, Oct | -7.3 °C | 45 mm |
| 2 | `m_38.75_93.75` | Qaidam Basin | 0.628 | 0.99 | 0.90 | 0.28 | 1.00 | 0.69 | Mar, Oct, Apr | 0.9 °C | 34 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.621 | 1.00 | 0.65 | 0.37 | 1.00 | 0.76 | Feb, Mar, Oct | -9.3 °C | 72 mm |
| 4 | `m_-77.75_164.25` | McMurdo Dry Valleys | 0.616 | 0.62 | 0.61 | 0.46 | 0.83 | 0.00 | none | -18.9 °C | 80 mm |
| 5 | `m_37.75_89.25` | Tibetan Plateau | 0.610 | 0.95 | 0.75 | 0.30 | 0.99 | 0.71 | Mar, Oct, Apr | -2.0 °C | 52 mm |
| 6 | `m_34.75_83.25` | Tibetan Plateau | 0.600 | 1.00 | 0.64 | 0.34 | 0.99 | 0.77 | Feb, Mar, Oct | -5.8 °C | 73 mm |
| 7 | `m_38.25_74.25` | Pamir and Karakoram | 0.588 | 0.88 | 0.66 | 0.32 | 0.97 | 0.70 | Oct, Mar, Sep | -3.7 °C | 70 mm |
| 8 | `m_81.25_-72.25` | Ellesmere or north-west Greenland | 0.572 | 0.78 | 0.45 | 0.45 | 0.92 | 0.00 | none | -17.4 °C | 129 mm |
| 9 | `m_-25.25_-69.25` | Altiplano and Puna | 0.568 | 0.83 | 1.00 | 0.18 | 1.00 | 0.94 | Jul, Jun, Aug | 10.6 °C | 19 mm |
| 10 | `m_-72.25_68.75` | Antarctica | 0.567 | 0.67 | 0.73 | 0.49 | 0.52 | 0.02 | Dec | -21.3 °C | 57 mm |

**Closest on all five factors**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.75_86.25` | Tibetan Plateau | 0.729 | 1.00 | 0.81 | 0.35 | 1.00 | 0.73 | Feb, Mar, Oct | -6.4 °C | 44 mm |
| 2 | `m_35.25_79.75` | Tibetan Plateau | 0.712 | 1.00 | 0.65 | 0.37 | 1.00 | 0.76 | Feb, Mar, Oct | -9.3 °C | 72 mm |
| 3 | `m_35.25_83.25` | Tibetan Plateau | 0.707 | 0.99 | 0.66 | 0.35 | 1.00 | 0.76 | Feb, Mar, Oct | -7.0 °C | 68 mm |
| 4 | `m_38.75_93.75` | Qaidam Basin | 0.702 | 0.99 | 0.90 | 0.28 | 1.00 | 0.69 | Mar, Oct, Apr | 0.9 °C | 34 mm |
| 5 | `m_-22.25_-68.25` | Altiplano and Puna | 0.684 | 0.90 | 0.83 | 0.24 | 0.90 | 0.91 | Jul, Jun, Aug | 4.4 °C | 42 mm |
| 6 | `m_37.25_90.25` | Tibetan Plateau | 0.684 | 1.00 | 0.71 | 0.31 | 0.95 | 0.72 | Feb, Mar, Oct | -2.3 °C | 59 mm |
| 7 | `m_-25.25_-69.25` | Altiplano and Puna | 0.677 | 0.83 | 1.00 | 0.18 | 1.00 | 0.94 | Jul, Jun, Aug | 10.6 °C | 19 mm |
| 8 | `m_32.75_81.75` | Tibetan Plateau | 0.663 | 0.96 | 0.58 | 0.30 | 0.94 | 0.81 | Feb, Mar, Oct | -1.7 °C | 88 mm |
| 9 | `m_38.25_74.25` | Pamir and Karakoram | 0.660 | 0.88 | 0.66 | 0.32 | 0.97 | 0.70 | Oct, Mar, Sep | -3.7 °C | 70 mm |
| 10 | `m_41.25_89.25` | Taklamakan and Tarim Basin | 0.643 | 1.00 | 0.89 | 0.19 | 1.00 | 0.64 | Mar, Oct, Apr | 9.8 °C | 35 mm |

The closest square on all factors is `m_36.75_86.25` (Tibetan Plateau), with a score of 0.729.
There, Mars is 69.0 °C colder in the yearly mean.
The square gets 1.76 times 25 mm of precipitation a year.
Mars air pressure is 1.17 % of the square's.

### Gusev crater - Apollinaris Sulci

Caveats: it is not a climate match, and a score is a position on each factor's own scale, not a share of likeness.

**Closest by landscape (slopes and bare ground)**

104 ranked squares tie at the top score of 1.000, so their order here is not a ranking. Tied squares are listed by bare area, then by environment score.

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_12.75_41.25` | Danakil Depression | 1.000 | 1.00 | 0.21 | 0.00 | 1.00 | 0.95 | Jan, Dec, Feb | 33.1 °C | 266 mm |
| 2 | `m_15.75_47.75` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.04 | 1.00 | 1.00 | Jan, Feb, Nov | 26.6 °C | 17 mm |
| 3 | `m_17.75_23.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.06 | 1.00 | 1.00 | Feb, Nov, Mar | 24.6 °C | 10 mm |
| 4 | `m_18.75_36.25` | Sahara | 1.000 | 1.00 | 0.79 | 0.03 | 1.00 | 1.00 | Feb, Mar, Nov | 27.2 °C | 46 mm |
| 5 | `m_19.25_8.75` | Sahara | 1.000 | 1.00 | 0.89 | 0.06 | 1.00 | 1.00 | Feb, Nov, Mar | 24.1 °C | 34 mm |
| 6 | `m_19.75_18.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.08 | 1.00 | 1.00 | Feb, Mar, Oct | 21.9 °C | 14 mm |
| 7 | `m_20.25_-13.25` | Sahara | 1.000 | 1.00 | 0.30 | 0.03 | 1.00 | 1.00 | Feb, Mar, Apr | 27.5 °C | 204 mm |
| 8 | `m_-21.25_-69.75` | Atacama Desert | 1.000 | 1.00 | 1.00 | 0.13 | 1.00 | 1.00 | Aug, Sep, Oct | 17.8 °C | 9 mm |
| 9 | `m_21.25_13.25` | Sahara | 1.000 | 1.00 | 0.98 | 0.05 | 1.00 | 1.00 | Feb, Mar, Oct | 24.9 °C | 26 mm |
| 10 | `m_21.25_43.75` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.04 | 1.00 | 1.00 | Feb, Mar, Oct | 26.4 °C | 15 mm |

**Closest by environment (dry, cold and bare)**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.676 | 0.87 | 0.80 | 0.39 | 1.00 | 0.66 | Apr, Sep, May | -7.3 °C | 45 mm |
| 2 | `m_38.75_93.75` | Qaidam Basin | 0.647 | 1.00 | 0.90 | 0.30 | 1.00 | 0.60 | Apr, May, Sep | 0.9 °C | 34 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.639 | 1.00 | 0.65 | 0.41 | 1.00 | 0.69 | Mar, Apr, Sep | -9.3 °C | 72 mm |
| 4 | `m_-77.75_164.25` | McMurdo Dry Valleys | 0.634 | 0.64 | 0.61 | 0.51 | 0.83 | 0.00 | none | -18.9 °C | 80 mm |
| 5 | `m_37.75_89.25` | Tibetan Plateau | 0.627 | 1.00 | 0.75 | 0.33 | 0.99 | 0.63 | Apr, Sep, May | -2.0 °C | 52 mm |
| 6 | `m_34.75_83.25` | Tibetan Plateau | 0.617 | 0.90 | 0.64 | 0.37 | 0.99 | 0.70 | Mar, Apr, May | -5.8 °C | 73 mm |
| 7 | `m_38.25_74.25` | Pamir and Karakoram | 0.605 | 0.95 | 0.66 | 0.35 | 0.97 | 0.61 | Sep, Apr, May | -3.7 °C | 70 mm |
| 8 | `m_81.25_-72.25` | Ellesmere or north-west Greenland | 0.588 | 0.83 | 0.45 | 0.49 | 0.92 | 0.00 | none | -17.4 °C | 129 mm |
| 9 | `m_-25.25_-69.25` | Altiplano and Puna | 0.585 | 0.88 | 1.00 | 0.20 | 1.00 | 0.95 | Sep, Apr, Oct | 10.6 °C | 19 mm |
| 10 | `m_-72.25_68.75` | Antarctica | 0.584 | 0.64 | 0.73 | 0.53 | 0.52 | 0.00 | none | -21.3 °C | 57 mm |

**Closest on all five factors**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_35.75_85.75` | Tibetan Plateau | 0.716 | 0.99 | 0.76 | 0.38 | 0.95 | 0.68 | Mar, Apr, Sep | -7.1 °C | 51 mm |
| 2 | `m_35.25_79.75` | Tibetan Plateau | 0.710 | 1.00 | 0.65 | 0.41 | 1.00 | 0.69 | Mar, Apr, Sep | -9.3 °C | 72 mm |
| 3 | `m_-22.25_-68.25` | Altiplano and Puna | 0.706 | 0.89 | 0.83 | 0.26 | 0.90 | 1.00 | Aug, Sep, Apr | 4.4 °C | 42 mm |
| 4 | `m_-25.25_-69.25` | Altiplano and Puna | 0.700 | 0.88 | 1.00 | 0.20 | 1.00 | 0.95 | Sep, Apr, Oct | 10.6 °C | 19 mm |
| 5 | `m_38.75_93.75` | Qaidam Basin | 0.695 | 1.00 | 0.90 | 0.30 | 1.00 | 0.60 | Apr, May, Sep | 0.9 °C | 34 mm |
| 6 | `m_37.25_88.75` | Tibetan Plateau | 0.694 | 0.92 | 0.76 | 0.36 | 1.00 | 0.64 | Apr, Sep, May | -4.8 °C | 51 mm |
| 7 | `m_33.25_82.75` | Tibetan Plateau | 0.689 | 1.00 | 0.59 | 0.36 | 0.99 | 0.74 | Mar, Apr, May | -4.6 °C | 86 mm |
| 8 | `m_38.25_74.25` | Pamir and Karakoram | 0.664 | 0.95 | 0.66 | 0.35 | 0.97 | 0.61 | Sep, Apr, May | -3.7 °C | 70 mm |
| 9 | `m_-19.25_-70.25` | Atacama Desert | 0.660 | 1.00 | 1.00 | 0.13 | 0.99 | 1.00 | Aug, Sep, May | 17.8 °C | 20 mm |
| 10 | `m_-28.25_-69.25` | Altiplano and Puna | 0.648 | 0.88 | 0.52 | 0.30 | 0.98 | 0.87 | Sep, Oct, Apr | 1.4 °C | 106 mm |

The closest square on all factors is `m_35.75_85.75` (Tibetan Plateau), with a score of 0.716.
There, Mars is 59.6 °C colder in the yearly mean.
The square gets 2.03 times 25 mm of precipitation a year.
Mars air pressure is 1.19 % of the square's.

### Aram Chaos

Caveats: it is not a climate match, and a score is a position on each factor's own scale, not a share of likeness.

**Closest by landscape (slopes and bare ground)**

34 ranked squares tie at the top score of 1.000, so their order here is not a ranking. Tied squares are listed by bare area, then by environment score.

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_19.25_8.75` | Sahara | 1.000 | 1.00 | 0.89 | 0.07 | 1.00 | 1.00 | Mar, Apr, Sep | 24.1 °C | 34 mm |
| 2 | `m_19.75_18.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.10 | 1.00 | 1.00 | Mar, Apr, Sep | 21.9 °C | 14 mm |
| 3 | `m_20.25_36.75` | Sahara | 1.000 | 1.00 | 0.83 | 0.03 | 1.00 | 1.00 | Mar, Apr | 27.4 °C | 42 mm |
| 4 | `m_-21.75_-69.25` | Atacama Desert | 1.000 | 1.00 | 1.00 | 0.15 | 1.00 | 1.00 | Sep, Oct, Nov | 17.7 °C | 21 mm |
| 5 | `m_-24.75_-69.25` | Atacama Desert | 1.000 | 1.00 | 1.00 | 0.19 | 1.00 | 0.95 | Oct, Nov, Mar | 14.5 °C | 12 mm |
| 6 | `m_25.75_37.75` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.05 | 1.00 | 0.92 | Apr, May | 25.7 °C | 16 mm |
| 7 | `m_26.25_7.25` | Sahara | 1.000 | 1.00 | 0.96 | 0.07 | 1.00 | 0.90 | Apr, May | 24.2 °C | 28 mm |
| 8 | `m_26.25_58.25` | Arabian Desert | 1.000 | 1.00 | 0.57 | 0.06 | 1.00 | 0.90 | Apr | 24.8 °C | 92 mm |
| 9 | `m_27.25_33.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.09 | 1.00 | 0.86 | Apr, May, Sep | 22.7 °C | 8 mm |
| 10 | `m_27.75_62.25` | other | 1.000 | 1.00 | 0.59 | 0.08 | 1.00 | 0.84 | Apr, Sep | 23.1 °C | 85 mm |

**Closest by environment (dry, cold and bare)**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.711 | 0.69 | 0.80 | 0.45 | 1.00 | 0.54 | Apr, May, Aug | -7.3 °C | 45 mm |
| 2 | `m_38.75_93.75` | Qaidam Basin | 0.679 | 1.00 | 0.90 | 0.35 | 1.00 | 0.45 | May, Aug, Jun | 0.9 °C | 34 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.672 | 0.95 | 0.65 | 0.47 | 1.00 | 0.57 | Apr, May, Jul | -9.3 °C | 72 mm |
| 4 | `m_-77.75_164.25` | McMurdo Dry Valleys | 0.666 | 0.65 | 0.61 | 0.59 | 0.83 | 0.00 | none | -18.9 °C | 80 mm |
| 5 | `m_37.75_89.25` | Tibetan Plateau | 0.659 | 1.00 | 0.75 | 0.38 | 0.99 | 0.48 | May, Aug, Jun | -2.0 °C | 52 mm |
| 6 | `m_34.75_83.25` | Tibetan Plateau | 0.649 | 0.88 | 0.64 | 0.43 | 0.99 | 0.59 | Apr, May, Jun | -5.8 °C | 73 mm |
| 7 | `m_38.25_74.25` | Pamir and Karakoram | 0.636 | 0.92 | 0.66 | 0.40 | 0.97 | 0.46 | May, Aug, Jun | -3.7 °C | 70 mm |
| 8 | `m_81.25_-72.25` | Ellesmere or north-west Greenland | 0.618 | 0.96 | 0.45 | 0.57 | 0.92 | 0.00 | none | -17.4 °C | 129 mm |
| 9 | `m_-25.25_-69.25` | Altiplano and Puna | 0.614 | 0.99 | 1.00 | 0.23 | 1.00 | 0.93 | Oct, Nov, Mar | 10.6 °C | 19 mm |
| 10 | `m_-72.25_68.75` | Antarctica | 0.613 | 0.58 | 0.73 | 0.62 | 0.52 | 0.00 | none | -21.3 °C | 57 mm |

**Closest on all five factors**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_-22.25_-68.25` | Altiplano and Puna | 0.745 | 1.00 | 0.83 | 0.31 | 0.90 | 1.00 | Sep, Oct, Nov | 4.4 °C | 42 mm |
| 2 | `m_-25.25_-69.25` | Altiplano and Puna | 0.735 | 0.99 | 1.00 | 0.23 | 1.00 | 0.93 | Oct, Nov, Mar | 10.6 °C | 19 mm |
| 3 | `m_34.75_81.25` | Tibetan Plateau | 0.704 | 1.00 | 0.64 | 0.46 | 0.98 | 0.59 | Apr, May, Jun | -8.7 °C | 73 mm |
| 4 | `m_36.75_86.75` | Tibetan Plateau | 0.703 | 0.99 | 0.80 | 0.43 | 0.98 | 0.52 | Apr, May, Aug | -5.5 °C | 45 mm |
| 5 | `m_-18.75_-70.25` | Atacama Desert | 0.684 | 1.00 | 0.98 | 0.15 | 0.99 | 1.00 | Sep, Oct, Nov | 17.2 °C | 26 mm |
| 6 | `m_-28.25_-69.25` | Altiplano and Puna | 0.675 | 0.98 | 0.52 | 0.34 | 0.98 | 0.83 | Oct, Nov, Mar | 1.4 °C | 106 mm |
| 7 | `m_38.75_93.75` | Qaidam Basin | 0.674 | 1.00 | 0.90 | 0.35 | 1.00 | 0.45 | May, Aug, Jun | 0.9 °C | 34 mm |
| 8 | `m_31.75_79.75` | Tibetan Plateau | 0.659 | 1.00 | 0.50 | 0.40 | 0.90 | 0.70 | Apr, May, Jun | -3.3 °C | 113 mm |
| 9 | `m_37.75_90.25` | Tibetan Plateau | 0.658 | 1.00 | 0.74 | 0.37 | 0.95 | 0.48 | May, Aug, Jun | -0.5 °C | 55 mm |
| 10 | `m_20.75_18.75` | Sahara | 0.650 | 1.00 | 1.00 | 0.12 | 1.00 | 1.00 | Mar, Apr, Sep | 20.3 °C | 10 mm |

The closest square on all factors is `m_-22.25_-68.25` (Altiplano and Puna), with a score of 0.745.
There, Mars is 57.8 °C colder in the yearly mean.
The square gets 1.66 times 25 mm of precipitation a year.
Mars air pressure is 1.16 % of the square's.

### Noctis Landing

Caveats: it is not a climate match, and a score is a position on each factor's own scale, not a share of likeness.

**Closest by landscape (slopes and bare ground)**

11 ranked squares tie at the top score of 1.000, so their order here is not a ranking. Tied squares are listed by bare area, then by environment score.

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_20.25_18.25` | Sahara | 1.000 | 1.00 | 0.86 | 0.08 | 1.00 | 1.00 | Mar, Oct, Apr | 22.4 °C | 38 mm |
| 2 | `m_-21.75_-69.25` | Atacama Desert | 1.000 | 1.00 | 1.00 | 0.13 | 1.00 | 1.00 | Sep, Oct, Apr | 17.7 °C | 21 mm |
| 3 | `m_-25.25_-68.75` | Altiplano and Puna | 1.000 | 1.00 | 0.44 | 0.28 | 1.00 | 0.94 | Sep, Oct, Nov | 3.3 °C | 134 mm |
| 4 | `m_26.25_37.25` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.07 | 1.00 | 0.91 | Mar, Apr, May | 23.0 °C | 16 mm |
| 5 | `m_28.75_33.75` | Sinai, Negev and Wadi Rum | 1.000 | 1.00 | 0.99 | 0.12 | 1.00 | 0.83 | Mar, Apr, May | 18.4 °C | 26 mm |
| 6 | `m_38.75_88.75` | Taklamakan and Tarim Basin | 1.000 | 1.00 | 0.84 | 0.21 | 1.00 | 0.52 | Apr, May, Aug | 10.0 °C | 41 mm |
| 7 | `m_28.25_61.75` | other | 1.000 | 1.00 | 0.61 | 0.08 | 1.00 | 0.85 | Mar, Apr, Sep | 22.2 °C | 79 mm |
| 8 | `m_26.25_57.75` | Arabian Desert | 0.999 | 1.00 | 0.55 | 0.04 | 1.00 | 0.91 | Mar, Apr | 26.1 °C | 97 mm |
| 9 | `m_23.75_39.25` | Arabian Desert | 0.999 | 1.00 | 1.00 | 0.04 | 1.00 | 0.99 | Mar, Apr | 26.1 °C | 19 mm |
| 10 | `m_14.75_48.75` | Arabian Desert | 0.998 | 1.00 | 1.00 | 0.07 | 1.00 | 1.00 | Feb, Mar, Oct | 23.0 °C | 9 mm |

**Closest by environment (dry, cold and bare)**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.681 | 0.53 | 0.80 | 0.39 | 1.00 | 0.60 | Apr, May, Aug | -7.3 °C | 45 mm |
| 2 | `m_38.75_93.75` | Qaidam Basin | 0.651 | 0.94 | 0.90 | 0.31 | 1.00 | 0.52 | Apr, May, Aug | 0.9 °C | 34 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.643 | 0.87 | 0.65 | 0.41 | 1.00 | 0.63 | Apr, May, Jul | -9.3 °C | 72 mm |
| 4 | `m_-77.75_164.25` | McMurdo Dry Valleys | 0.638 | 0.82 | 0.61 | 0.52 | 0.83 | 0.00 | none | -18.9 °C | 80 mm |
| 5 | `m_37.75_89.25` | Tibetan Plateau | 0.631 | 1.00 | 0.75 | 0.34 | 0.99 | 0.55 | Apr, May, Aug | -2.0 °C | 52 mm |
| 6 | `m_34.75_83.25` | Tibetan Plateau | 0.621 | 0.71 | 0.64 | 0.38 | 0.99 | 0.64 | Apr, May, Jun | -5.8 °C | 73 mm |
| 7 | `m_38.25_74.25` | Pamir and Karakoram | 0.609 | 0.97 | 0.66 | 0.36 | 0.97 | 0.53 | Apr, May, Aug | -3.7 °C | 70 mm |
| 8 | `m_81.25_-72.25` | Ellesmere or north-west Greenland | 0.592 | 0.96 | 0.45 | 0.50 | 0.92 | 0.00 | none | -17.4 °C | 129 mm |
| 9 | `m_-25.25_-69.25` | Altiplano and Puna | 0.588 | 0.95 | 1.00 | 0.20 | 1.00 | 0.94 | Sep, Oct, Nov | 10.6 °C | 19 mm |
| 10 | `m_-72.25_68.75` | Antarctica | 0.587 | 0.98 | 0.73 | 0.54 | 0.52 | 0.00 | none | -21.3 °C | 57 mm |

**Closest on all five factors**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_-22.25_-68.25` | Altiplano and Puna | 0.726 | 1.00 | 0.83 | 0.27 | 0.90 | 1.00 | Sep, Oct, Nov | 4.4 °C | 42 mm |
| 2 | `m_-25.25_-69.25` | Altiplano and Puna | 0.711 | 0.95 | 1.00 | 0.20 | 1.00 | 0.94 | Sep, Oct, Nov | 10.6 °C | 19 mm |
| 3 | `m_37.25_86.75` | Tibetan Plateau | 0.690 | 1.00 | 0.81 | 0.34 | 1.00 | 0.56 | Apr, May, Aug | -2.4 °C | 44 mm |
| 4 | `m_33.75_80.75` | Tibetan Plateau | 0.685 | 1.00 | 0.61 | 0.37 | 0.99 | 0.67 | Apr, May, Sep | -5.4 °C | 81 mm |
| 5 | `m_38.75_93.75` | Qaidam Basin | 0.668 | 0.94 | 0.90 | 0.31 | 1.00 | 0.52 | Apr, May, Aug | 0.9 °C | 34 mm |
| 6 | `m_35.75_78.25` | Tibetan Plateau | 0.666 | 1.00 | 0.55 | 0.40 | 0.96 | 0.61 | Apr, Aug, May | -8.3 °C | 95 mm |
| 7 | `m_-28.25_-69.25` | Altiplano and Puna | 0.664 | 1.00 | 0.52 | 0.30 | 0.98 | 0.85 | Sep, Oct, Nov | 1.4 °C | 106 mm |
| 8 | `m_-18.75_-70.25` | Atacama Desert | 0.664 | 0.98 | 0.98 | 0.13 | 0.99 | 1.00 | Sep, Oct, Nov | 17.2 °C | 26 mm |
| 9 | `m_36.25_83.25` | Tibetan Plateau | 0.663 | 1.00 | 0.68 | 0.32 | 0.99 | 0.60 | Apr, May, Aug | -0.6 °C | 66 mm |
| 10 | `m_37.75_90.25` | Tibetan Plateau | 0.659 | 1.00 | 0.74 | 0.32 | 0.95 | 0.55 | Apr, May, Aug | -0.5 °C | 55 mm |

The closest square on all factors is `m_-22.25_-68.25` (Altiplano and Puna), with a score of 0.726.
There, Mars is 69.3 °C colder in the yearly mean.
The square gets 1.66 times 25 mm of precipitation a year.
Mars air pressure is 0.96 % of the square's.

### Hypanis (Hypanis and Sabrina deltas)

Caveats: it is not a climate match, and a score is a position on each factor's own scale, not a share of likeness.

**Closest by landscape (slopes and bare ground)**

174 ranked squares tie at the top score of 1.000, so their order here is not a ranking. Tied squares are listed by bare area, then by environment score.

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_12.75_41.25` | Danakil Depression | 1.000 | 1.00 | 0.21 | 0.00 | 1.00 | 0.97 | Jan, Dec, Feb | 33.1 °C | 266 mm |
| 2 | `m_15.75_25.25` | Sahara | 1.000 | 1.00 | 0.85 | 0.06 | 1.00 | 1.00 | Jan, Feb, Nov | 24.5 °C | 39 mm |
| 3 | `m_16.25_47.75` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.05 | 1.00 | 1.00 | Feb, Nov, Oct | 25.7 °C | 21 mm |
| 4 | `m_16.25_51.25` | Arabian Desert | 1.000 | 1.00 | 0.74 | 0.04 | 1.00 | 1.00 | Feb, Nov, Mar | 26.3 °C | 55 mm |
| 5 | `m_17.75_23.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.06 | 1.00 | 1.00 | Feb, Nov, Mar | 24.6 °C | 10 mm |
| 6 | `m_17.75_36.75` | Sahara | 1.000 | 1.00 | 0.68 | 0.04 | 1.00 | 1.00 | Feb, Mar, Nov | 26.3 °C | 65 mm |
| 7 | `m_18.25_44.25` | Arabian Desert | 1.000 | 1.00 | 0.99 | 0.06 | 1.00 | 1.00 | Feb, Nov, Mar | 25.0 °C | 26 mm |
| 8 | `m_18.25_9.25` | Sahara | 1.000 | 1.00 | 0.64 | 0.05 | 1.00 | 1.00 | Feb, Nov, Mar | 25.5 °C | 73 mm |
| 9 | `m_19.75_19.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.06 | 1.00 | 1.00 | Feb, Mar, Oct | 24.7 °C | 5 mm |
| 10 | `m_19.75_-12.75` | Sahara | 1.000 | 1.00 | 0.41 | 0.04 | 1.00 | 1.00 | Feb, Mar, Apr | 26.8 °C | 146 mm |

**Closest by environment (dry, cold and bare)**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.702 | 1.00 | 0.80 | 0.43 | 1.00 | 0.66 | Apr, Sep, May | -7.3 °C | 45 mm |
| 2 | `m_38.75_93.75` | Qaidam Basin | 0.671 | 0.66 | 0.90 | 0.34 | 1.00 | 0.59 | Apr, May, Sep | 0.9 °C | 34 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.663 | 0.79 | 0.65 | 0.45 | 1.00 | 0.68 | Apr, Sep, May | -9.3 °C | 72 mm |
| 4 | `m_-77.75_164.25` | McMurdo Dry Valleys | 0.658 | 0.23 | 0.61 | 0.56 | 0.83 | 0.00 | none | -18.9 °C | 80 mm |
| 5 | `m_37.75_89.25` | Tibetan Plateau | 0.651 | 0.57 | 0.75 | 0.37 | 0.99 | 0.61 | Apr, Sep, May | -2.0 °C | 52 mm |
| 6 | `m_34.75_83.25` | Tibetan Plateau | 0.640 | 0.82 | 0.64 | 0.41 | 0.99 | 0.70 | Mar, Apr, May | -5.8 °C | 73 mm |
| 7 | `m_38.25_74.25` | Pamir and Karakoram | 0.628 | 0.48 | 0.66 | 0.39 | 0.97 | 0.60 | Sep, Apr, May | -3.7 °C | 70 mm |
| 8 | `m_81.25_-72.25` | Ellesmere or north-west Greenland | 0.610 | 0.41 | 0.45 | 0.55 | 0.92 | 0.00 | none | -17.4 °C | 129 mm |
| 9 | `m_-25.25_-69.25` | Altiplano and Puna | 0.607 | 0.50 | 1.00 | 0.22 | 1.00 | 0.95 | Sep, Apr, Oct | 10.6 °C | 19 mm |
| 10 | `m_-72.25_68.75` | Antarctica | 0.606 | 0.27 | 0.73 | 0.59 | 0.52 | 0.00 | none | -21.3 °C | 57 mm |

**Closest on all five factors**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.743 | 1.00 | 0.80 | 0.43 | 1.00 | 0.66 | Apr, Sep, May | -7.3 °C | 45 mm |
| 2 | `m_35.25_82.75` | Tibetan Plateau | 0.723 | 1.00 | 0.66 | 0.44 | 0.98 | 0.68 | Apr, Sep, May | -8.5 °C | 69 mm |
| 3 | `m_37.25_89.75` | Tibetan Plateau | 0.699 | 1.00 | 0.71 | 0.37 | 1.00 | 0.63 | Apr, Sep, May | -2.3 °C | 59 mm |
| 4 | `m_34.75_79.25` | Tibetan Plateau | 0.698 | 0.94 | 0.58 | 0.44 | 1.00 | 0.70 | Mar, Apr, Sep | -7.9 °C | 88 mm |
| 5 | `m_38.25_93.25` | Qaidam Basin | 0.688 | 0.91 | 0.94 | 0.30 | 1.00 | 0.60 | Apr, May, Sep | 4.0 °C | 30 mm |
| 6 | `m_-22.75_-69.75` | Atacama Desert | 0.684 | 1.00 | 1.00 | 0.15 | 1.00 | 1.00 | Aug, Sep, Oct | 17.0 °C | 8 mm |
| 7 | `m_-19.75_-69.75` | Atacama Desert | 0.657 | 0.87 | 1.00 | 0.14 | 1.00 | 1.00 | Aug, Sep, Oct | 17.8 °C | 15 mm |
| 8 | `m_23.75_26.25` | Sahara | 0.651 | 1.00 | 1.00 | 0.12 | 1.00 | 0.99 | Feb, Mar, Oct | 19.8 °C | 2 mm |
| 9 | `m_41.25_90.25` | Taklamakan and Tarim Basin | 0.645 | 1.00 | 0.95 | 0.23 | 1.00 | 0.52 | Apr, May, Jun | 10.4 °C | 29 mm |
| 10 | `m_-26.25_15.25` | Namib Desert | 0.637 | 1.00 | 0.80 | 0.14 | 1.00 | 0.92 | Sep, Oct, Nov | 17.7 °C | 45 mm |

The closest square on all factors is `m_36.25_86.25` (Tibetan Plateau), with a score of 0.743.
There, Mars is 49.3 °C colder in the yearly mean.
The square gets 1.81 times 25 mm of precipitation a year.
Mars air pressure is 1.31 % of the square's.

### Hadriacus Palus and Cavi

Caveats: it is not a climate match, and a score is a position on each factor's own scale, not a share of likeness.

**Closest by landscape (slopes and bare ground)**

101 ranked squares tie at the top score of 1.000, so their order here is not a ranking. Tied squares are listed by bare area, then by environment score.

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_12.75_41.25` | Danakil Depression | 1.000 | 1.00 | 0.21 | 0.00 | 1.00 | 0.69 | Jan, Dec, Feb | 33.1 °C | 266 mm |
| 2 | `m_18.75_9.25` | Sahara | 1.000 | 1.00 | 0.75 | 0.05 | 1.00 | 0.80 | Jan, Dec, Feb | 25.0 °C | 54 mm |
| 3 | `m_19.25_36.75` | Sahara | 1.000 | 1.00 | 0.80 | 0.02 | 1.00 | 0.81 | Feb, Jan, Mar | 27.9 °C | 46 mm |
| 4 | `m_19.75_18.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.09 | 1.00 | 0.82 | Jan, Dec, Feb | 21.9 °C | 14 mm |
| 5 | `m_-21.25_-69.75` | Atacama Desert | 1.000 | 1.00 | 1.00 | 0.13 | 1.00 | 0.85 | Jul, Aug, Sep | 17.8 °C | 9 mm |
| 6 | `m_21.75_12.75` | Sahara | 1.000 | 1.00 | 0.89 | 0.06 | 1.00 | 0.86 | Jan, Dec, Feb | 24.7 °C | 35 mm |
| 7 | `m_21.75_35.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.04 | 1.00 | 0.86 | Jan, Dec, Feb | 26.6 °C | 12 mm |
| 8 | `m_22.75_18.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.07 | 1.00 | 0.88 | Jan, Dec, Feb | 23.8 °C | 6 mm |
| 9 | `m_23.25_5.25` | Sahara | 1.000 | 1.00 | 0.58 | 0.05 | 1.00 | 0.89 | Jan, Dec, Feb | 24.9 °C | 88 mm |
| 10 | `m_23.25_39.25` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.03 | 1.00 | 0.89 | Feb, Jan, Dec | 27.2 °C | 21 mm |

**Closest by environment (dry, cold and bare)**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.681 | 0.89 | 0.80 | 0.39 | 1.00 | 0.78 | Feb, Mar, Oct | -7.3 °C | 45 mm |
| 2 | `m_38.75_93.75` | Qaidam Basin | 0.651 | 1.00 | 0.90 | 0.31 | 1.00 | 0.73 | Feb, Mar, Oct | 0.9 °C | 34 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.643 | 1.00 | 0.65 | 0.41 | 1.00 | 0.80 | Feb, Mar, Oct | -9.3 °C | 72 mm |
| 4 | `m_-77.75_164.25` | McMurdo Dry Valleys | 0.638 | 0.53 | 0.61 | 0.52 | 0.83 | 0.00 | none | -18.9 °C | 80 mm |
| 5 | `m_37.75_89.25` | Tibetan Plateau | 0.631 | 0.95 | 0.75 | 0.34 | 0.99 | 0.75 | Feb, Mar, Oct | -2.0 °C | 52 mm |
| 6 | `m_34.75_83.25` | Tibetan Plateau | 0.621 | 1.00 | 0.64 | 0.38 | 0.99 | 0.81 | Feb, Mar, Oct | -5.8 °C | 73 mm |
| 7 | `m_38.25_74.25` | Pamir and Karakoram | 0.609 | 0.83 | 0.66 | 0.36 | 0.97 | 0.74 | Feb, Oct, Mar | -3.7 °C | 70 mm |
| 8 | `m_81.25_-72.25` | Ellesmere or north-west Greenland | 0.592 | 0.81 | 0.45 | 0.50 | 0.92 | 0.00 | none | -17.4 °C | 129 mm |
| 9 | `m_-25.25_-69.25` | Altiplano and Puna | 0.588 | 0.90 | 1.00 | 0.20 | 1.00 | 0.93 | Jul, Jun, Aug | 10.6 °C | 19 mm |
| 10 | `m_-72.25_68.75` | Antarctica | 0.587 | 0.54 | 0.73 | 0.54 | 0.52 | 0.06 | Jan, Dec | -21.3 °C | 57 mm |

**Closest on all five factors**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.75_86.25` | Tibetan Plateau | 0.751 | 1.00 | 0.81 | 0.38 | 1.00 | 0.77 | Feb, Mar, Oct | -6.4 °C | 44 mm |
| 2 | `m_35.25_79.75` | Tibetan Plateau | 0.734 | 1.00 | 0.65 | 0.41 | 1.00 | 0.80 | Feb, Mar, Oct | -9.3 °C | 72 mm |
| 3 | `m_38.75_93.75` | Qaidam Basin | 0.725 | 1.00 | 0.90 | 0.31 | 1.00 | 0.73 | Feb, Mar, Oct | 0.9 °C | 34 mm |
| 4 | `m_34.75_83.25` | Tibetan Plateau | 0.720 | 1.00 | 0.64 | 0.38 | 0.99 | 0.81 | Feb, Mar, Oct | -5.8 °C | 73 mm |
| 5 | `m_37.25_90.25` | Tibetan Plateau | 0.705 | 1.00 | 0.71 | 0.34 | 0.95 | 0.76 | Feb, Mar, Oct | -2.3 °C | 59 mm |
| 6 | `m_-25.25_-69.25` | Altiplano and Puna | 0.703 | 0.90 | 1.00 | 0.20 | 1.00 | 0.93 | Jul, Jun, Aug | 10.6 °C | 19 mm |
| 7 | `m_-22.25_-68.25` | Altiplano and Puna | 0.693 | 0.90 | 0.83 | 0.27 | 0.90 | 0.87 | Jul, Jun, Aug | 4.4 °C | 42 mm |
| 8 | `m_32.25_81.75` | Tibetan Plateau | 0.676 | 0.96 | 0.54 | 0.33 | 0.97 | 0.86 | Nov, Oct, Mar | -1.4 °C | 100 mm |
| 9 | `m_38.25_74.25` | Pamir and Karakoram | 0.673 | 0.83 | 0.66 | 0.36 | 0.97 | 0.74 | Feb, Oct, Mar | -3.7 °C | 70 mm |
| 10 | `m_41.25_89.25` | Taklamakan and Tarim Basin | 0.659 | 0.97 | 0.89 | 0.21 | 1.00 | 0.68 | Mar, Oct, Apr | 9.8 °C | 35 mm |

The closest square on all factors is `m_36.75_86.25` (Tibetan Plateau), with a score of 0.751.
There, Mars is 58.5 °C colder in the yearly mean.
The square gets 1.76 times 25 mm of precipitation a year.
Mars air pressure is 1.31 % of the square's.

### Protonilus Mensae

Caveats: it is not a climate match, and a score is a position on each factor's own scale, not a share of likeness.

**Closest by landscape (slopes and bare ground)**

4 ranked squares tie at the top score of 1.000, so their order here is not a ranking. Tied squares are listed by bare area, then by environment score.

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_21.25_18.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.09 | 1.00 | 0.55 | Jan, Dec, Feb | 20.6 °C | 9 mm |
| 2 | `m_-25.25_-68.75` | Altiplano and Puna | 1.000 | 1.00 | 0.44 | 0.26 | 1.00 | 0.63 | Jul, Jun, Aug | 3.3 °C | 134 mm |
| 3 | `m_27.75_35.75` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.06 | 1.00 | 0.68 | Dec, Feb, Mar | 23.8 °C | 20 mm |
| 4 | `m_-21.75_-70.25` | Atacama Desert | 1.000 | 1.00 | 1.00 | 0.12 | 1.00 | 0.56 | Jul, Aug, Sep | 17.7 °C | 11 mm |
| 5 | `m_38.75_88.75` | Taklamakan and Tarim Basin | 1.000 | 1.00 | 0.84 | 0.19 | 1.00 | 0.90 | Jan, Dec, Feb | 10.0 °C | 41 mm |
| 6 | `m_23.75_39.25` | Arabian Desert | 0.999 | 1.00 | 1.00 | 0.04 | 1.00 | 0.60 | Feb, Jan, Dec | 26.1 °C | 19 mm |
| 7 | `m_14.75_48.75` | Arabian Desert | 0.998 | 1.00 | 1.00 | 0.07 | 1.00 | 0.42 | Jan, Dec, Feb | 23.0 °C | 9 mm |
| 8 | `m_23.25_58.75` | Arabian Desert | 0.996 | 1.00 | 0.49 | 0.02 | 0.99 | 0.59 | Dec, Jan, Feb | 28.3 °C | 114 mm |
| 9 | `m_36.25_83.25` | Tibetan Plateau | 0.995 | 1.00 | 0.68 | 0.30 | 0.99 | 0.85 | Jan, Dec, Feb | -0.6 °C | 66 mm |
| 10 | `m_74.75_-90.75` | Canadian High Arctic | 0.995 | 1.00 | 0.07 | 0.43 | 0.99 | 0.32 | Apr, May | -14.7 °C | 401 mm |

**Closest by environment (dry, cold and bare)**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.661 | 0.57 | 0.80 | 0.36 | 1.00 | 0.85 | Jan, Dec, Feb | -7.3 °C | 45 mm |
| 2 | `m_38.75_93.75` | Qaidam Basin | 0.632 | 0.92 | 0.90 | 0.28 | 1.00 | 0.90 | Jan, Dec, Feb | 0.9 °C | 34 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.625 | 0.85 | 0.65 | 0.38 | 1.00 | 0.83 | Dec, Jan, Nov | -9.3 °C | 72 mm |
| 4 | `m_-77.75_164.25` | McMurdo Dry Valleys | 0.620 | 0.78 | 0.61 | 0.47 | 0.83 | 0.26 | Nov, Dec, Jan | -18.9 °C | 80 mm |
| 5 | `m_37.75_89.25` | Tibetan Plateau | 0.613 | 0.97 | 0.75 | 0.31 | 0.99 | 0.88 | Jan, Dec, Feb | -2.0 °C | 52 mm |
| 6 | `m_34.75_83.25` | Tibetan Plateau | 0.603 | 0.72 | 0.64 | 0.35 | 0.99 | 0.82 | Jan, Dec, Feb | -5.8 °C | 73 mm |
| 7 | `m_38.25_74.25` | Pamir and Karakoram | 0.591 | 0.92 | 0.66 | 0.33 | 0.97 | 0.89 | Dec, Jan, Nov | -3.7 °C | 70 mm |
| 8 | `m_81.25_-72.25` | Ellesmere or north-west Greenland | 0.575 | 0.86 | 0.45 | 0.46 | 0.92 | 0.19 | May, Jun, Jul | -17.4 °C | 129 mm |
| 9 | `m_-25.25_-69.25` | Altiplano and Puna | 0.571 | 0.86 | 1.00 | 0.19 | 1.00 | 0.63 | Jul, Jun, Aug | 10.6 °C | 19 mm |
| 10 | `m_-72.25_68.75` | Antarctica | 0.570 | 0.80 | 0.73 | 0.49 | 0.52 | 0.37 | Oct, Feb, Jan | -21.3 °C | 57 mm |

**Closest on all five factors**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_37.25_86.75` | Tibetan Plateau | 0.738 | 1.00 | 0.81 | 0.31 | 1.00 | 0.87 | Jan, Dec, Feb | -2.4 °C | 44 mm |
| 2 | `m_38.75_93.75` | Qaidam Basin | 0.731 | 0.92 | 0.90 | 0.28 | 1.00 | 0.90 | Jan, Dec, Feb | 0.9 °C | 34 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.702 | 0.85 | 0.65 | 0.38 | 1.00 | 0.83 | Dec, Jan, Nov | -9.3 °C | 72 mm |
| 4 | `m_37.75_90.25` | Tibetan Plateau | 0.700 | 0.93 | 0.74 | 0.29 | 0.95 | 0.88 | Jan, Dec, Feb | -0.5 °C | 55 mm |
| 5 | `m_38.25_74.25` | Pamir and Karakoram | 0.700 | 0.92 | 0.66 | 0.33 | 0.97 | 0.89 | Dec, Jan, Nov | -3.7 °C | 70 mm |
| 6 | `m_36.25_83.25` | Tibetan Plateau | 0.700 | 1.00 | 0.68 | 0.30 | 0.99 | 0.85 | Jan, Dec, Feb | -0.6 °C | 66 mm |
| 7 | `m_33.25_82.25` | Tibetan Plateau | 0.672 | 0.90 | 0.59 | 0.33 | 0.99 | 0.79 | Dec, Jan, Nov | -4.6 °C | 86 mm |
| 8 | `m_41.25_87.75` | Taklamakan and Tarim Basin | 0.645 | 0.90 | 0.70 | 0.20 | 0.96 | 0.93 | Jan, Dec, Feb | 9.2 °C | 62 mm |
| 9 | `m_35.75_95.25` | Tibetan Plateau | 0.641 | 1.00 | 0.54 | 0.31 | 0.78 | 0.84 | Jan, Dec, Feb | -1.7 °C | 100 mm |
| 10 | `m_43.25_91.25` | other | 0.640 | 0.81 | 0.64 | 0.23 | 0.97 | 0.93 | Jan, Feb, Dec | 6.4 °C | 73 mm |

The closest square on all factors is `m_37.25_86.75` (Tibetan Plateau), with a score of 0.738.
There, Mars is 71.3 °C colder in the yearly mean.
The square gets 1.76 times 25 mm of precipitation a year.
Mars air pressure is 0.94 % of the square's.

### Eastern outlet of Valles Marineris

Caveats: it is not a climate match, and a score is a position on each factor's own scale, not a share of likeness.

**Closest by landscape (slopes and bare ground)**

37 ranked squares tie at the top score of 1.000, so their order here is not a ranking. Tied squares are listed by bare area, then by environment score.

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_12.75_41.25` | Danakil Depression | 1.000 | 1.00 | 0.21 | 0.00 | 1.00 | 1.00 | Feb | 33.1 °C | 266 mm |
| 2 | `m_19.25_8.75` | Sahara | 1.000 | 1.00 | 0.89 | 0.07 | 1.00 | 1.00 | Mar, Oct, Apr | 24.1 °C | 34 mm |
| 3 | `m_19.75_18.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.10 | 1.00 | 1.00 | Mar, Oct, Apr | 21.9 °C | 14 mm |
| 4 | `m_20.25_36.75` | Sahara | 1.000 | 1.00 | 0.83 | 0.03 | 1.00 | 1.00 | Mar, Apr, Oct | 27.4 °C | 42 mm |
| 5 | `m_-21.75_-69.25` | Atacama Desert | 1.000 | 1.00 | 1.00 | 0.15 | 1.00 | 1.00 | Sep, Oct, Nov | 17.7 °C | 21 mm |
| 6 | `m_24.25_5.75` | Sahara | 1.000 | 1.00 | 0.74 | 0.09 | 1.00 | 0.97 | Mar, Apr, May | 22.1 °C | 55 mm |
| 7 | `m_24.25_34.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.05 | 1.00 | 0.97 | Mar, Apr, May | 25.8 °C | 7 mm |
| 8 | `m_24.75_2.75` | Sahara | 1.000 | 1.00 | 0.90 | 0.03 | 1.00 | 0.96 | Mar, Apr | 27.7 °C | 34 mm |
| 9 | `m_-25.25_-68.75` | Altiplano and Puna | 1.000 | 1.00 | 0.44 | 0.32 | 1.00 | 0.94 | Sep, Oct, Nov | 3.3 °C | 134 mm |
| 10 | `m_25.75_8.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.08 | 1.00 | 0.92 | Mar, Apr, May | 23.4 °C | 21 mm |

**Closest by environment (dry, cold and bare)**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.708 | 0.80 | 0.80 | 0.44 | 1.00 | 0.56 | Apr, May, Aug | -7.3 °C | 45 mm |
| 2 | `m_38.75_93.75` | Qaidam Basin | 0.677 | 0.99 | 0.90 | 0.35 | 1.00 | 0.48 | Apr, May, Aug | 0.9 °C | 34 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.670 | 1.00 | 0.65 | 0.47 | 1.00 | 0.60 | Apr, May, Jul | -9.3 °C | 72 mm |
| 4 | `m_-77.75_164.25` | McMurdo Dry Valleys | 0.664 | 0.72 | 0.61 | 0.58 | 0.83 | 0.00 | none | -18.9 °C | 80 mm |
| 5 | `m_37.75_89.25` | Tibetan Plateau | 0.657 | 1.00 | 0.75 | 0.38 | 0.99 | 0.51 | Apr, May, Aug | -2.0 °C | 52 mm |
| 6 | `m_34.75_83.25` | Tibetan Plateau | 0.647 | 0.89 | 0.64 | 0.43 | 0.99 | 0.61 | Apr, May, Jun | -5.8 °C | 73 mm |
| 7 | `m_38.25_74.25` | Pamir and Karakoram | 0.633 | 0.97 | 0.66 | 0.40 | 0.97 | 0.49 | Apr, May, Aug | -3.7 °C | 70 mm |
| 8 | `m_81.25_-72.25` | Ellesmere or north-west Greenland | 0.616 | 0.84 | 0.45 | 0.56 | 0.92 | 0.00 | none | -17.4 °C | 129 mm |
| 9 | `m_-25.25_-69.25` | Altiplano and Puna | 0.612 | 0.86 | 1.00 | 0.23 | 1.00 | 0.94 | Sep, Oct, Nov | 10.6 °C | 19 mm |
| 10 | `m_-72.25_68.75` | Antarctica | 0.611 | 0.79 | 0.73 | 0.61 | 0.52 | 0.00 | none | -21.3 °C | 57 mm |

**Closest on all five factors**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_-22.25_-68.25` | Altiplano and Puna | 0.738 | 0.96 | 0.83 | 0.30 | 0.90 | 1.00 | Sep, Oct, Nov | 4.4 °C | 42 mm |
| 2 | `m_-25.25_-69.25` | Altiplano and Puna | 0.714 | 0.86 | 1.00 | 0.23 | 1.00 | 0.94 | Sep, Oct, Nov | 10.6 °C | 19 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.709 | 1.00 | 0.65 | 0.47 | 1.00 | 0.60 | Apr, May, Jul | -9.3 °C | 72 mm |
| 4 | `m_35.75_85.75` | Tibetan Plateau | 0.709 | 0.96 | 0.76 | 0.44 | 0.95 | 0.58 | Apr, May, Aug | -7.1 °C | 51 mm |
| 5 | `m_33.25_82.75` | Tibetan Plateau | 0.693 | 1.00 | 0.59 | 0.41 | 0.99 | 0.67 | Apr, May, Jun | -4.6 °C | 86 mm |
| 6 | `m_37.25_88.75` | Tibetan Plateau | 0.685 | 0.90 | 0.76 | 0.41 | 1.00 | 0.53 | Apr, May, Aug | -4.8 °C | 51 mm |
| 7 | `m_38.75_93.75` | Qaidam Basin | 0.681 | 0.99 | 0.90 | 0.35 | 1.00 | 0.48 | Apr, May, Aug | 0.9 °C | 34 mm |
| 8 | `m_-19.25_-70.25` | Atacama Desert | 0.679 | 1.00 | 1.00 | 0.14 | 0.99 | 1.00 | Sep, Oct, Nov | 17.8 °C | 20 mm |
| 9 | `m_-28.25_-69.25` | Altiplano and Puna | 0.664 | 0.90 | 0.52 | 0.34 | 0.98 | 0.84 | Oct, Nov, Mar | 1.4 °C | 106 mm |
| 10 | `m_32.25_79.75` | Tibetan Plateau | 0.661 | 1.00 | 0.57 | 0.39 | 0.80 | 0.70 | Apr, May, Sep | -3.2 °C | 91 mm |

The closest square on all factors is `m_-22.25_-68.25` (Altiplano and Puna), with a score of 0.738.
There, Mars is 58.6 °C colder in the yearly mean.
The square gets 1.66 times 25 mm of precipitation a year.
Mars air pressure is 1.32 % of the square's.

### Tempe Terra

Caveats: it is not a climate match, and a score is a position on each factor's own scale, not a share of likeness.

**Closest by landscape (slopes and bare ground)**

126 ranked squares tie at the top score of 1.000, so their order here is not a ranking. Tied squares are listed by bare area, then by environment score.

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_12.75_41.25` | Danakil Depression | 1.000 | 1.00 | 0.21 | 0.00 | 1.00 | 0.38 | Jan, Dec, Feb | 33.1 °C | 266 mm |
| 2 | `m_15.75_50.75` | Arabian Desert | 1.000 | 1.00 | 0.94 | 0.04 | 1.00 | 0.44 | Jan, Dec, Feb | 25.8 °C | 30 mm |
| 3 | `m_17.75_22.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.04 | 1.00 | 0.48 | Jan, Dec, Feb | 25.8 °C | 17 mm |
| 4 | `m_17.75_36.75` | Sahara | 1.000 | 1.00 | 0.68 | 0.03 | 1.00 | 0.48 | Feb, Jan, Mar | 26.3 °C | 65 mm |
| 5 | `m_18.25_9.25` | Sahara | 1.000 | 1.00 | 0.64 | 0.04 | 1.00 | 0.49 | Jan, Dec, Feb | 25.5 °C | 73 mm |
| 6 | `m_18.75_43.75` | Arabian Desert | 1.000 | 1.00 | 0.85 | 0.05 | 1.00 | 0.50 | Dec, Jan, Nov | 24.4 °C | 39 mm |
| 7 | `m_19.75_18.25` | Sahara | 1.000 | 1.00 | 0.99 | 0.05 | 1.00 | 0.52 | Jan, Dec, Feb | 24.1 °C | 26 mm |
| 8 | `m_20.75_36.75` | Sahara | 1.000 | 1.00 | 0.90 | 0.02 | 1.00 | 0.54 | Feb, Jan, Mar | 28.0 °C | 34 mm |
| 9 | `m_-21.25_-69.75` | Atacama Desert | 1.000 | 1.00 | 1.00 | 0.11 | 1.00 | 0.55 | Jul, Aug, Sep | 17.8 °C | 9 mm |
| 10 | `m_21.25_12.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.04 | 1.00 | 0.55 | Jan, Dec, Feb | 25.5 °C | 20 mm |

**Closest by environment (dry, cold and bare)**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.643 | 1.00 | 0.80 | 0.33 | 1.00 | 0.85 | Jan, Dec, Feb | -7.3 °C | 45 mm |
| 2 | `m_38.75_93.75` | Qaidam Basin | 0.615 | 0.91 | 0.90 | 0.26 | 1.00 | 0.90 | Jan, Dec, Feb | 0.9 °C | 34 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.608 | 0.99 | 0.65 | 0.35 | 1.00 | 0.83 | Dec, Jan, Nov | -9.3 °C | 72 mm |
| 4 | `m_-77.75_164.25` | McMurdo Dry Valleys | 0.603 | 0.40 | 0.61 | 0.43 | 0.83 | 0.26 | Nov, Dec, Jan | -18.9 °C | 80 mm |
| 5 | `m_37.75_89.25` | Tibetan Plateau | 0.596 | 0.81 | 0.75 | 0.28 | 0.99 | 0.88 | Jan, Dec, Feb | -2.0 °C | 52 mm |
| 6 | `m_34.75_83.25` | Tibetan Plateau | 0.587 | 1.00 | 0.64 | 0.32 | 0.99 | 0.82 | Jan, Dec, Feb | -5.8 °C | 73 mm |
| 7 | `m_38.25_74.25` | Pamir and Karakoram | 0.575 | 0.70 | 0.66 | 0.30 | 0.97 | 0.89 | Dec, Jan, Nov | -3.7 °C | 70 mm |
| 8 | `m_81.25_-72.25` | Ellesmere or north-west Greenland | 0.559 | 0.64 | 0.45 | 0.42 | 0.92 | 0.19 | May, Jun, Jul | -17.4 °C | 129 mm |
| 9 | `m_-25.25_-69.25` | Altiplano and Puna | 0.556 | 0.75 | 1.00 | 0.17 | 1.00 | 0.63 | Jul, Jun, Aug | 10.6 °C | 19 mm |
| 10 | `m_-72.25_68.75` | Antarctica | 0.555 | 0.45 | 0.73 | 0.46 | 0.52 | 0.37 | Oct, Feb, Jan | -21.3 °C | 57 mm |

**Closest on all five factors**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.742 | 1.00 | 0.80 | 0.33 | 1.00 | 0.85 | Jan, Dec, Feb | -7.3 °C | 45 mm |
| 2 | `m_38.75_93.75` | Qaidam Basin | 0.716 | 0.91 | 0.90 | 0.26 | 1.00 | 0.90 | Jan, Dec, Feb | 0.9 °C | 34 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.713 | 0.99 | 0.65 | 0.35 | 1.00 | 0.83 | Dec, Jan, Nov | -9.3 °C | 72 mm |
| 4 | `m_37.25_89.75` | Tibetan Plateau | 0.702 | 0.96 | 0.71 | 0.29 | 1.00 | 0.87 | Jan, Dec, Feb | -2.3 °C | 59 mm |
| 5 | `m_34.75_83.25` | Tibetan Plateau | 0.698 | 1.00 | 0.64 | 0.32 | 0.99 | 0.82 | Jan, Dec, Feb | -5.8 °C | 73 mm |
| 6 | `m_41.25_89.25` | Taklamakan and Tarim Basin | 0.683 | 1.00 | 0.89 | 0.18 | 1.00 | 0.93 | Jan, Dec, Feb | 9.8 °C | 35 mm |
| 7 | `m_44.25_97.25` | Gobi Desert | 0.674 | 1.00 | 0.70 | 0.21 | 1.00 | 0.93 | Jan, Feb, Nov | 6.1 °C | 60 mm |
| 8 | `m_41.25_96.25` | Gobi Desert | 0.661 | 0.94 | 0.64 | 0.22 | 1.00 | 0.93 | Jan, Dec, Feb | 4.8 °C | 74 mm |
| 9 | `m_43.25_91.75` | other | 0.655 | 0.86 | 0.75 | 0.20 | 1.00 | 0.93 | Jan, Dec, Feb | 7.5 °C | 52 mm |
| 10 | `m_38.25_74.25` | Pamir and Karakoram | 0.651 | 0.70 | 0.66 | 0.30 | 0.97 | 0.89 | Dec, Jan, Nov | -3.7 °C | 70 mm |

The closest square on all factors is `m_36.25_86.25` (Tibetan Plateau), with a score of 0.742.
There, Mars is 75.2 °C colder in the yearly mean.
The square gets 1.81 times 25 mm of precipitation a year.
Mars air pressure is 0.98 % of the square's.

### Southern edge of Meridiani Planum (Endeavour crater area)

Caveats: it is not a climate match, and a score is a position on each factor's own scale, not a share of likeness.

**Closest by landscape (slopes and bare ground)**

485 ranked squares tie at the top score of 1.000, so their order here is not a ranking. Tied squares are listed by bare area, then by environment score.

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_12.75_41.25` | Danakil Depression | 1.000 | 1.00 | 0.21 | 0.00 | 1.00 | 1.00 | Feb | 33.1 °C | 266 mm |
| 2 | `m_15.75_25.25` | Sahara | 1.000 | 1.00 | 0.85 | 0.06 | 1.00 | 1.00 | Mar, Oct, Apr | 24.5 °C | 39 mm |
| 3 | `m_16.25_45.25` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.07 | 1.00 | 1.00 | Oct, Mar, Apr | 23.7 °C | 22 mm |
| 4 | `m_16.25_50.25` | Arabian Desert | 1.000 | 1.00 | 1.00 | 0.05 | 1.00 | 1.00 | Mar, Oct, Apr | 25.6 °C | 24 mm |
| 5 | `m_16.75_30.25` | Sahara | 1.000 | 1.00 | 0.84 | 0.03 | 1.00 | 1.00 | Mar, Apr, Oct | 27.1 °C | 40 mm |
| 6 | `m_17.75_23.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.06 | 1.00 | 1.00 | Mar, Oct, Apr | 24.6 °C | 10 mm |
| 7 | `m_17.75_54.75` | Arabian Desert | 1.000 | 1.00 | 0.37 | 0.04 | 1.00 | 1.00 | Oct, Apr | 26.5 °C | 163 mm |
| 8 | `m_18.25_27.25` | Sahara | 1.000 | 1.00 | 1.00 | 0.06 | 1.00 | 1.00 | Mar, Apr, Oct | 24.6 °C | 4 mm |
| 9 | `m_18.25_9.25` | Sahara | 1.000 | 1.00 | 0.64 | 0.05 | 1.00 | 1.00 | Mar, Oct, Apr | 25.5 °C | 73 mm |
| 10 | `m_18.25_32.75` | Sahara | 1.000 | 1.00 | 1.00 | 0.02 | 1.00 | 1.00 | Mar, Apr | 28.6 °C | 13 mm |

**Closest by environment (dry, cold and bare)**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.707 | 0.97 | 0.80 | 0.44 | 1.00 | 0.55 | Apr, May, Aug | -7.3 °C | 45 mm |
| 2 | `m_38.75_93.75` | Qaidam Basin | 0.676 | 0.66 | 0.90 | 0.34 | 1.00 | 0.46 | May, Aug, Jun | 0.9 °C | 34 mm |
| 3 | `m_35.25_79.75` | Tibetan Plateau | 0.668 | 0.83 | 0.65 | 0.46 | 1.00 | 0.58 | Apr, May, Jul | -9.3 °C | 72 mm |
| 4 | `m_-77.75_164.25` | McMurdo Dry Valleys | 0.663 | 0.26 | 0.61 | 0.58 | 0.83 | 0.00 | none | -18.9 °C | 80 mm |
| 5 | `m_37.75_89.25` | Tibetan Plateau | 0.656 | 0.62 | 0.75 | 0.38 | 0.99 | 0.50 | Apr, May, Aug | -2.0 °C | 52 mm |
| 6 | `m_34.75_83.25` | Tibetan Plateau | 0.645 | 0.81 | 0.64 | 0.42 | 0.99 | 0.60 | Apr, May, Jun | -5.8 °C | 73 mm |
| 7 | `m_38.25_74.25` | Pamir and Karakoram | 0.632 | 0.52 | 0.66 | 0.40 | 0.97 | 0.48 | May, Aug, Jun | -3.7 °C | 70 mm |
| 8 | `m_81.25_-72.25` | Ellesmere or north-west Greenland | 0.615 | 0.42 | 0.45 | 0.56 | 0.92 | 0.00 | none | -17.4 °C | 129 mm |
| 9 | `m_-25.25_-69.25` | Altiplano and Puna | 0.611 | 0.52 | 1.00 | 0.23 | 1.00 | 0.94 | Sep, Oct, Nov | 10.6 °C | 19 mm |
| 10 | `m_-72.25_68.75` | Antarctica | 0.610 | 0.30 | 0.73 | 0.61 | 0.52 | 0.00 | none | -21.3 °C | 57 mm |

**Closest on all five factors**

| # | Square | Region | Score | Terrain | Dry | Cold | Bare | Sun | Best months | Yearly temp. | Precip. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `m_36.25_86.25` | Tibetan Plateau | 0.717 | 0.97 | 0.80 | 0.44 | 1.00 | 0.55 | Apr, May, Aug | -7.3 °C | 45 mm |
| 2 | `m_35.25_82.75` | Tibetan Plateau | 0.704 | 1.00 | 0.66 | 0.45 | 0.98 | 0.58 | Apr, May, Aug | -8.5 °C | 69 mm |
| 3 | `m_34.75_79.25` | Tibetan Plateau | 0.689 | 1.00 | 0.58 | 0.45 | 1.00 | 0.60 | Apr, May, Jun | -7.9 °C | 88 mm |
| 4 | `m_-22.25_-68.75` | Atacama Desert | 0.688 | 0.86 | 0.80 | 0.23 | 0.99 | 1.00 | Sep, Oct, Nov | 10.9 °C | 46 mm |
| 5 | `m_37.25_89.75` | Tibetan Plateau | 0.674 | 1.00 | 0.71 | 0.38 | 1.00 | 0.51 | Apr, May, Aug | -2.3 °C | 59 mm |
| 6 | `m_38.25_93.25` | Qaidam Basin | 0.673 | 1.00 | 0.94 | 0.31 | 1.00 | 0.48 | May, Aug, Jun | 4.0 °C | 30 mm |
| 7 | `m_23.75_26.25` | Sahara | 0.653 | 1.00 | 1.00 | 0.12 | 1.00 | 0.99 | Mar, Apr, May | 19.8 °C | 2 mm |
| 8 | `m_-18.25_-70.75` | Atacama Desert | 0.644 | 1.00 | 0.89 | 0.13 | 0.94 | 1.00 | Sep, Oct, Nov | 18.8 °C | 34 mm |
| 9 | `m_-25.25_-69.25` | Altiplano and Puna | 0.643 | 0.52 | 1.00 | 0.23 | 1.00 | 0.94 | Sep, Oct, Nov | 10.6 °C | 19 mm |
| 10 | `m_23.75_11.75` | Sahara | 0.637 | 1.00 | 1.00 | 0.11 | 1.00 | 0.99 | Mar, Apr, Sep | 21.0 °C | 20 mm |

The closest square on all factors is `m_36.25_86.25` (Tibetan Plateau), with a score of 0.717.
There, Mars is 47.4 °C colder in the yearly mean.
The square gets 1.81 times 25 mm of precipitation a year.
Mars air pressure is 1.18 % of the square's.

## 5. What falls short, and by how much

From `mars_cells.json` → `meta.factor_summary.<site>`: the highest value of each factor among the ranked squares, and how many ranked squares reach 1.
Caveats: it is not a climate match, and a score is a position on each factor's own scale, not a share of likeness.

| Site | Highest cold | Coldest ranked square | Its yearly temp. | Mars colder by | Squares at dry 1 | Squares at terrain 1 | Squares at sun 1 | Highest full |
|---|---|---|---|---|---|---|---|---|
| Jezero | 0.789 | `m_-80.25_155.75` (Transantarctic Mountains) | -38.3 °C | 18.3 °C | 1,581 | 1,119 | 1,173 | 0.752 |
| Gale | 0.778 | `m_-80.25_155.75` (Transantarctic Mountains) | -38.3 °C | 19.5 °C | 1,581 | 1,142 | 2,868 | 0.736 |
| Phoenix | 0.548 | `m_-80.25_155.75` (Transantarctic Mountains) | -38.3 °C | 56.4 °C | 1,581 | 1,385 | 0 | 0.592 |
| Arcadia Planitia | 0.648 | `m_-80.25_155.75` (Transantarctic Mountains) | -38.3 °C | 37.1 °C | 1,581 | 704 | 0 | 0.726 |
| Deuteronilus Mensae | 0.673 | `m_-80.25_155.75` (Transantarctic Mountains) | -38.3 °C | 33.2 °C | 1,581 | 1,437 | 0 | 0.768 |
| Viking 1 | 0.767 | `m_-80.25_155.75` (Transantarctic Mountains) | -38.3 °C | 20.7 °C | 1,581 | 610 | 0 | 0.712 |
| Viking 2 | 0.621 | `m_-80.25_155.75` (Transantarctic Mountains) | -38.3 °C | 41.7 °C | 1,581 | 184 | 0 | 0.690 |
| Pathfinder | 0.796 | `m_-80.25_155.75` (Transantarctic Mountains) | -38.3 °C | 17.5 °C | 1,581 | 2,236 | 847 | 0.717 |
| Spirit | 0.730 | `m_-80.25_155.75` (Transantarctic Mountains) | -38.3 °C | 25.3 °C | 1,581 | 1,442 | 2,222 | 0.700 |
| Opportunity | 0.808 | `m_-80.25_155.75` (Transantarctic Mountains) | -38.3 °C | 16.2 °C | 1,581 | 1,819 | 2,894 | 0.665 |
| InSight | 0.774 | `m_-80.25_155.75` (Transantarctic Mountains) | -38.3 °C | 19.9 °C | 1,581 | 1,406 | 2,871 | 0.670 |
| Phlegra Montes | 0.672 | `m_-80.25_155.75` (Transantarctic Mountains) | -38.3 °C | 33.4 °C | 1,581 | 2,445 | 0 | 0.764 |
| AP-1 (Arcadia Planitia) | 0.654 | `m_-80.25_155.75` (Transantarctic Mountains) | -38.3 °C | 36.2 °C | 1,581 | 461 | 0 | 0.725 |
| AP-9 (Arcadia Planitia) | 0.648 | `m_-80.25_155.75` (Transantarctic Mountains) | -38.3 °C | 37.1 °C | 1,581 | 1,132 | 0 | 0.732 |
| EM-16 (Erebus Montes) | 0.648 | `m_-80.25_155.75` (Transantarctic Mountains) | -38.3 °C | 37.1 °C | 1,581 | 554 | 0 | 0.733 |
| AP-8 (Arcadia Planitia) | 0.652 | `m_-80.25_155.75` (Transantarctic Mountains) | -38.3 °C | 36.4 °C | 1,581 | 431 | 0 | 0.710 |
| EM-15 (Erebus Montes) | 0.654 | `m_-80.25_155.75` (Transantarctic Mountains) | -38.3 °C | 36.2 °C | 1,581 | 1,910 | 0 | 0.742 |
| PM-7 (Phlegra Montes) | 0.664 | `m_-80.25_155.75` (Transantarctic Mountains) | -38.3 °C | 34.6 °C | 1,581 | 1,291 | 0 | 0.767 |
| Phlegra Dorsa, Arcadia Planitia | 0.669 | `m_-80.25_155.75` (Transantarctic Mountains) | -38.3 °C | 33.8 °C | 1,581 | 1,207 | 0 | 0.750 |
| Southern Nectaris Fossae | 0.739 | `m_-80.25_155.75` (Transantarctic Mountains) | -38.3 °C | 24.1 °C | 1,581 | 1,659 | 0 | 0.767 |
| Valles Marineris mouth (southern Acidalia Planitia, as named in the abstract) | 0.788 | `m_-80.25_155.75` (Transantarctic Mountains) | -38.3 °C | 18.4 °C | 1,581 | 1,204 | 680 | 0.717 |
| East Melas Chasma | 0.811 | `m_-80.25_155.75` (Transantarctic Mountains) | -38.3 °C | 15.9 °C | 1,581 | 1,627 | 2,692 | 0.744 |
| Mawrth Vallis | 0.761 | `m_-80.25_155.75` (Transantarctic Mountains) | -38.3 °C | 21.5 °C | 1,581 | 1,742 | 0 | 0.754 |
| Nili Fossae | 0.780 | `m_-80.25_155.75` (Transantarctic Mountains) | -38.3 °C | 19.3 °C | 1,581 | 1,510 | 0 | 0.744 |
| Acheron Fossae | 0.629 | `m_-80.25_155.75` (Transantarctic Mountains) | -38.3 °C | 40.2 °C | 1,581 | 5,385 | 0 | 0.756 |
| Hebrus Valles | 0.755 | `m_-80.25_155.75` (Transantarctic Mountains) | -38.3 °C | 22.1 °C | 1,581 | 517 | 515 | 0.712 |
| Newton crater | 0.662 | `m_-80.25_155.75` (Transantarctic Mountains) | -38.3 °C | 34.9 °C | 1,581 | 994 | 0 | 0.761 |
| Zephyria Planum hills ('Sea Urchins') | 0.701 | `m_-80.25_155.75` (Transantarctic Mountains) | -38.3 °C | 29.1 °C | 1,581 | 1,129 | 2,898 | 0.652 |
| Cerberus (west of Zunil crater) | 0.740 | `m_-80.25_155.75` (Transantarctic Mountains) | -38.3 °C | 24.0 °C | 1,581 | 296 | 2,748 | 0.715 |
| Amazonis Planitia mid-latitude ice | 0.630 | `m_-80.25_155.75` (Transantarctic Mountains) | -38.3 °C | 40.1 °C | 1,581 | 308 | 0 | 0.684 |
| Western Noachis Terra chloride deposits | 0.664 | `m_-80.25_155.75` (Transantarctic Mountains) | -38.3 °C | 34.5 °C | 1,581 | 905 | 0 | 0.762 |
| South of Valles Marineris (equatorial site) | 0.787 | `m_-80.25_155.75` (Transantarctic Mountains) | -38.3 °C | 18.5 °C | 1,581 | 1,764 | 1,013 | 0.754 |
| McLaughlin crater | 0.779 | `m_-80.25_155.75` (Transantarctic Mountains) | -38.3 °C | 19.4 °C | 1,581 | 1,862 | 0 | 0.738 |
| South of Firsoff crater, Arabia Terra | 0.814 | `m_-80.25_155.75` (Transantarctic Mountains) | -38.3 °C | 15.6 °C | 1,581 | 1,555 | 2,908 | 0.702 |
| Ismenius Cavus | 0.661 | `m_-80.25_155.75` (Transantarctic Mountains) | -38.3 °C | 35.0 °C | 1,581 | 545 | 0 | 0.755 |
| Hale crater | 0.672 | `m_-80.25_155.75` (Transantarctic Mountains) | -38.3 °C | 33.3 °C | 1,581 | 1,777 | 0 | 0.756 |
| Copernicus crater | 0.613 | `m_-80.25_155.75` (Transantarctic Mountains) | -38.3 °C | 43.1 °C | 1,581 | 794 | 0 | 0.693 |
| Huygens crater | 0.766 | `m_-80.25_155.75` (Transantarctic Mountains) | -38.3 °C | 20.9 °C | 1,581 | 481 | 2,551 | 0.718 |
| Mesopotamia (east rim of Hellas) | 0.696 | `m_-80.25_155.75` (Transantarctic Mountains) | -38.3 °C | 29.9 °C | 1,581 | 772 | 0 | 0.764 |
| Western Coprates Chasma | 0.806 | `m_-80.25_155.75` (Transantarctic Mountains) | -38.3 °C | 16.4 °C | 1,581 | 42 | 2,692 | 0.703 |
| Hellas Rim | 0.661 | `m_-80.25_155.75` (Transantarctic Mountains) | -38.3 °C | 35.0 °C | 1,581 | 1,855 | 0 | 0.764 |
| Eastern rim of Hellas impact basin | 0.652 | `m_-80.25_155.75` (Transantarctic Mountains) | -38.3 °C | 36.4 °C | 1,581 | 1,078 | 0 | 0.741 |
| Columbus crater | 0.714 | `m_-80.25_155.75` (Transantarctic Mountains) | -38.3 °C | 27.4 °C | 1,581 | 679 | 0 | 0.740 |
| South-west Sinus Meridiani | 0.807 | `m_-80.25_155.75` (Transantarctic Mountains) | -38.3 °C | 16.3 °C | 1,581 | 2,730 | 2,891 | 0.702 |
| Apollinaris Sulci | 0.703 | `m_-80.25_155.75` (Transantarctic Mountains) | -38.3 °C | 28.8 °C | 1,581 | 2,006 | 2,630 | 0.723 |
| Deuteronilus Mensae (debris apron zone) | 0.665 | `m_-80.25_155.75` (Transantarctic Mountains) | -38.3 °C | 34.4 °C | 1,581 | 1,738 | 0 | 0.760 |
| Ausonia Cavus | 0.703 | `m_-80.25_155.75` (Transantarctic Mountains) | -38.3 °C | 28.9 °C | 1,581 | 2,014 | 0 | 0.770 |
| Kasei Valles | 0.648 | `m_-80.25_155.75` (Transantarctic Mountains) | -38.3 °C | 37.1 °C | 1,581 | 1,607 | 0 | 0.729 |
| Gusev crater - Apollinaris Sulci | 0.706 | `m_-80.25_155.75` (Transantarctic Mountains) | -38.3 °C | 28.4 °C | 1,581 | 1,419 | 2,630 | 0.716 |
| Aram Chaos | 0.819 | `m_-80.25_155.75` (Transantarctic Mountains) | -38.3 °C | 15.1 °C | 1,581 | 1,373 | 2,891 | 0.745 |
| Noctis Landing | 0.720 | `m_-80.25_155.75` (Transantarctic Mountains) | -38.3 °C | 26.6 °C | 1,581 | 1,201 | 2,858 | 0.726 |
| Hypanis (Hypanis and Sabrina deltas) | 0.789 | `m_-80.25_155.75` (Transantarctic Mountains) | -38.3 °C | 18.3 °C | 1,581 | 883 | 2,692 | 0.743 |
| Hadriacus Palus and Cavi | 0.720 | `m_-80.25_155.75` (Transantarctic Mountains) | -38.3 °C | 26.6 °C | 1,581 | 1,657 | 0 | 0.751 |
| Protonilus Mensae | 0.659 | `m_-80.25_155.75` (Transantarctic Mountains) | -38.3 °C | 35.4 °C | 1,581 | 472 | 0 | 0.738 |
| Eastern outlet of Valles Marineris | 0.811 | `m_-80.25_155.75` (Transantarctic Mountains) | -38.3 °C | 15.9 °C | 1,581 | 1,194 | 2,871 | 0.738 |
| Tempe Terra | 0.607 | `m_-80.25_155.75` (Transantarctic Mountains) | -38.3 °C | 44.2 °C | 1,581 | 1,221 | 0 | 0.742 |
| Southern edge of Meridiani Planum (Endeavour crater area) | 0.806 | `m_-80.25_155.75` (Transantarctic Mountains) | -38.3 °C | 16.4 °C | 1,581 | 1,867 | 2,879 | 0.717 |

No ranked square reaches a cold score of 1 for any site; the highest is 0.819.
The coldest ranked square is `m_-80.25_155.75` (Transantarctic Mountains), at -38.3 °C a year. Each Mars site is 15.1 to 56.4 °C colder than that.
Slopes alone pick out little: terrain reaches 1 in 42 to 5,385 of the 12,984 ranked squares.
Dryness is matched in many places too: 1,581 ranked squares get 25 mm a year or less.
Cold is 0 in 52 of the 12,984 ranked squares, those at +30 °C or warmer, so their environment and full scores are 0.
For the 31 sites more than 23.44 degrees from the equator, no square reaches sun 1; the best is 0.947. The tilt of Mars is 1.75 degrees larger, so its yearly range of noon Sun is wider.

## 6. What no place on Earth matches

From `mars_sites.json` → `sites[].cannot_match` (written by MARS-CLIMATE). Pressure differs by site; the other rows are the same for all 57.

| What | Mars | Earth | Unit | Number | Number is |
|---|---|---|---|---|---|
| gravity | 3.73 | 9.82 | m/s2 | 0.38 | Mars / Earth |
| sunlight at the top of the atmosphere | 586.2 | 1361.0 | W/m2 | 0.431 | Mars / Earth (mean distance) |
| the air itself (oxygen) | 0.16 | 20.95 | % O2 by volume | 0.0076 | Mars / Earth |
| ultraviolet light at the ground | 190 | 290 | nm, shortest wavelength of sunlight reaching the ground | 100 | nm shorter on Mars |
| ionising radiation at the ground | 0.64 | 0.0066 | mSv per day | 97 | Mars / Earth |
| the dusty sky | below 1 in the clear season, above 3 in global dust storms | about 0.13 (from memory) | aerosol optical depth | n/a | no single ratio: see note |
| length of the year | 686.98 | 365.256 | Earth days | 1.881 | Mars / Earth |

| Site | Yearly mean pressure, Pa | Share of sea level | Share of the lowest land square |
|---|---|---|---|
| Jezero | 721 | 0.71 % | 1.40 % (`m_35.25_77.25`) |
| Gale | 818 | 0.81 % | 1.59 % (`m_35.25_77.25`) |
| Phoenix | 834 | 0.82 % | 1.62 % (`m_35.25_77.25`) |
| Arcadia Planitia | 825 | 0.81 % | 1.60 % (`m_35.25_77.25`) |
| Deuteronilus Mensae | 791 | 0.78 % | 1.54 % (`m_35.25_77.25`) |
| Viking 1 | 793 | 0.78 % | 1.54 % (`m_35.25_77.25`) |
| Viking 2 | 870 | 0.86 % | 1.69 % (`m_35.25_77.25`) |
| Pathfinder | 799 | 0.79 % | 1.55 % (`m_35.25_77.25`) |
| Spirit | 680 | 0.67 % | 1.32 % (`m_35.25_77.25`) |
| Opportunity | 641 | 0.63 % | 1.25 % (`m_35.25_77.25`) |
| InSight | 720 | 0.71 % | 1.40 % (`m_35.25_77.25`) |
| Phlegra Montes | 764 | 0.75 % | 1.49 % (`m_35.25_77.25`) |
| AP-1 (Arcadia Planitia) | 821 | 0.81 % | 1.60 % (`m_35.25_77.25`) |
| AP-9 (Arcadia Planitia) | 820 | 0.81 % | 1.59 % (`m_35.25_77.25`) |
| EM-16 (Erebus Montes) | 818 | 0.81 % | 1.59 % (`m_35.25_77.25`) |
| AP-8 (Arcadia Planitia) | 823 | 0.81 % | 1.60 % (`m_35.25_77.25`) |
| EM-15 (Erebus Montes) | 817 | 0.81 % | 1.59 % (`m_35.25_77.25`) |
| PM-7 (Phlegra Montes) | 697 | 0.69 % | 1.35 % (`m_35.25_77.25`) |
| Phlegra Dorsa, Arcadia Planitia | 823 | 0.81 % | 1.60 % (`m_35.25_77.25`) |
| Southern Nectaris Fossae | 480 | 0.47 % | 0.93 % (`m_35.25_77.25`) |
| Valles Marineris mouth (southern Acidalia Planitia, as named in the abstract) | 798 | 0.79 % | 1.55 % (`m_35.25_77.25`) |
| East Melas Chasma | 868 | 0.86 % | 1.69 % (`m_35.25_77.25`) |
| Mawrth Vallis | 703 | 0.69 % | 1.37 % (`m_35.25_77.25`) |
| Nili Fossae | 604 | 0.60 % | 1.17 % (`m_35.25_77.25`) |
| Acheron Fossae | 759 | 0.75 % | 1.48 % (`m_35.25_77.25`) |
| Hebrus Valles | 789 | 0.78 % | 1.53 % (`m_35.25_77.25`) |
| Newton crater | 643 | 0.63 % | 1.25 % (`m_35.25_77.25`) |
| Zephyria Planum hills ('Sea Urchins') | 728 | 0.72 % | 1.42 % (`m_35.25_77.25`) |
| Cerberus (west of Zunil crater) | 728 | 0.72 % | 1.42 % (`m_35.25_77.25`) |
| Amazonis Planitia mid-latitude ice | 833 | 0.82 % | 1.62 % (`m_35.25_77.25`) |
| Western Noachis Terra chloride deposits | 512 | 0.51 % | 1.00 % (`m_35.25_77.25`) |
| South of Valles Marineris (equatorial site) | 513 | 0.51 % | 1.00 % (`m_35.25_77.25`) |
| McLaughlin crater | 896 | 0.88 % | 1.74 % (`m_35.25_77.25`) |
| South of Firsoff crater, Arabia Terra | 671 | 0.66 % | 1.30 % (`m_35.25_77.25`) |
| Ismenius Cavus | 780 | 0.77 % | 1.52 % (`m_35.25_77.25`) |
| Hale crater | 682 | 0.67 % | 1.33 % (`m_35.25_77.25`) |
| Copernicus crater | 566 | 0.56 % | 1.10 % (`m_35.25_77.25`) |
| Huygens crater | 511 | 0.50 % | 0.99 % (`m_35.25_77.25`) |
| Mesopotamia (east rim of Hellas) | 746 | 0.74 % | 1.45 % (`m_35.25_77.25`) |
| Western Coprates Chasma | 793 | 0.78 % | 1.54 % (`m_35.25_77.25`) |
| Hellas Rim | 584 | 0.58 % | 1.14 % (`m_35.25_77.25`) |
| Eastern rim of Hellas impact basin | 607 | 0.60 % | 1.18 % (`m_35.25_77.25`) |
| Columbus crater | 526 | 0.52 % | 1.02 % (`m_35.25_77.25`) |
| South-west Sinus Meridiani | 646 | 0.64 % | 1.26 % (`m_35.25_77.25`) |
| Apollinaris Sulci | 691 | 0.68 % | 1.34 % (`m_35.25_77.25`) |
| Deuteronilus Mensae (debris apron zone) | 708 | 0.70 % | 1.38 % (`m_35.25_77.25`) |
| Ausonia Cavus | 754 | 0.74 % | 1.47 % (`m_35.25_77.25`) |
| Kasei Valles | 664 | 0.66 % | 1.29 % (`m_35.25_77.25`) |
| Gusev crater - Apollinaris Sulci | 646 | 0.64 % | 1.26 % (`m_35.25_77.25`) |
| Aram Chaos | 705 | 0.70 % | 1.37 % (`m_35.25_77.25`) |
| Noctis Landing | 581 | 0.57 % | 1.13 % (`m_35.25_77.25`) |
| Hypanis (Hypanis and Sabrina deltas) | 718 | 0.71 % | 1.40 % (`m_35.25_77.25`) |
| Hadriacus Palus and Cavi | 747 | 0.74 % | 1.45 % (`m_35.25_77.25`) |
| Protonilus Mensae | 583 | 0.58 % | 1.13 % (`m_35.25_77.25`) |
| Eastern outlet of Valles Marineris | 805 | 0.79 % | 1.56 % (`m_35.25_77.25`) |
| Tempe Terra | 538 | 0.53 % | 1.05 % (`m_35.25_77.25`) |
| Southern edge of Meridiani Planum (Endeavour crater area) | 647 | 0.64 % | 1.26 % (`m_35.25_77.25`) |

The measured figures at Gale (warm-season daily maximum, cold-season daily minimum, pressure) are Curiosity's. Curiosity's weather figures are from NASA's public weather feed, which says it is for outreach; they are not archive data.

Three of these rows are literature figures typed from memory by MARS-CLIMATE and not checked against a saved file. They are the UV cut-off, the radiation dose and the Earth dust optical depth.

## 7. Where the known analog sites come out

From `mars_validation.json` → `sites[]`. Each entry is placed in the square that holds its point. The percentile is the share of ranked squares that score lower, so 100 is the top.
The known sites are places that analog programmes and field studies have used, from `data/reference/known_analogs.json`. They test the ranking and are not an input to it.
Caveats: it is not a climate match, and a score is a position on each factor's own scale, not a share of likeness.

| Site | Square | Region | Bare | Yearly temp. | Precip. | Ranked |
|---|---|---|---|---|---|---|
| Atacama near Yungay | `m_-24.25_-69.75` (point on a square edge) | Atacama Desert | 1.00 | 17.1 °C | 8 mm | yes |
| McMurdo Dry Valleys | `m_-77.25_162.75` | McMurdo Dry Valleys | 0.26 | -21.9 °C | 123 mm | yes |
| Haughton crater | `m_75.25_-89.75` | Canadian High Arctic | 0.18 | -14.8 °C | 321 mm | yes |
| Mojave | `m_35.25_-115.25` (point on a square edge) | North American deserts | 0.15 | 17.3 °C | 164 mm | yes |
| Utah desert station near Hanksville | `m_38.25_-110.75` | Colorado Plateau | 0.81 | 11.8 °C | 242 mm | yes |
| Iceland's highlands | `m_65.25_-16.75` | Iceland | 0.92 | -1.0 °C | 992 mm | yes |
| Rio Tinto | `m_37.25_-6.25` | other | 0.03 | 18.0 °C | 468 mm | no |
| Qaidam Basin | `m_38.25_92.75` (point on a square edge) | Qaidam Basin | 1.00 | 4.2 °C | 32 mm | yes |
| Pilbara | `m_-21.25_119.25` | Australian deserts | 0.00 | 27.5 °C | 404 mm | no |
| Dhofar in Oman | `m_18.75_54.75` (point on a square edge) | Arabian Desert | 1.00 | 27.7 °C | 149 mm | yes |
| Lanzarote | `m_29.25_-13.75` (point on a square edge) | Canary Islands | n/a | n/a °C | n/a mm | no |
| Svalbard | `m_78.25_16.25` (point on a square edge) | Svalbard | 0.38 | -7.7 °C | 740 mm | yes |

**landscape: score (percentile among ranked squares)**

| Site | Jezero | Gale | Phoenix | Arcadia Planitia | Deuteronilus Mensae | Viking 1 | Viking 2 | Pathfinder | Spirit | Opportunity | InSight | Phlegra Montes | AP-1 (Arcadia Planitia) | AP-9 (Arcadia Planitia) | EM-16 (Erebus Montes) | AP-8 (Arcadia Planitia) | EM-15 (Erebus Montes) | PM-7 (Phlegra Montes) | Phlegra Dorsa, Arcadia Planitia | Southern Nectaris Fossae | Valles Marineris mouth (southern Acidalia Planitia, as named in the abstract) | East Melas Chasma | Mawrth Vallis | Nili Fossae | Acheron Fossae | Hebrus Valles | Newton crater | Zephyria Planum hills ('Sea Urchins') | Cerberus (west of Zunil crater) | Amazonis Planitia mid-latitude ice | Western Noachis Terra chloride deposits | South of Valles Marineris (equatorial site) | McLaughlin crater | South of Firsoff crater, Arabia Terra | Ismenius Cavus | Hale crater | Copernicus crater | Huygens crater | Mesopotamia (east rim of Hellas) | Western Coprates Chasma | Hellas Rim | Eastern rim of Hellas impact basin | Columbus crater | South-west Sinus Meridiani | Apollinaris Sulci | Deuteronilus Mensae (debris apron zone) | Ausonia Cavus | Kasei Valles | Gusev crater - Apollinaris Sulci | Aram Chaos | Noctis Landing | Hypanis (Hypanis and Sabrina deltas) | Hadriacus Palus and Cavi | Protonilus Mensae | Eastern outlet of Valles Marineris | Tempe Terra | Southern edge of Meridiani Planum (Endeavour crater area) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Atacama near Yungay | 1.000 (99.7) | 0.869 (93.9) | 0.882 (80.5) | 0.562 (49.8) | 0.998 (97.8) | 0.560 (51.1) | 0.567 (54.0) | 0.627 (52.0) | 0.790 (62.8) | 0.660 (55.2) | 0.554 (49.0) | 1.000 (99.6) | 0.414 (41.6) | 0.471 (43.5) | 0.673 (55.9) | 0.435 (43.3) | 0.642 (52.8) | 1.000 (99.4) | 0.703 (54.3) | 1.000 (99.1) | 0.752 (61.6) | 0.951 (96.2) | 1.000 (99.5) | 0.947 (96.1) | 1.000 (95.9) | 0.659 (53.8) | 1.000 (99.5) | 0.648 (54.5) | 0.896 (93.3) | 0.376 (40.6) | 0.939 (91.0) | 1.000 (98.8) | 0.960 (96.3) | 0.933 (87.0) | 0.985 (98.5) | 0.939 (96.0) | 0.821 (77.0) | 0.840 (80.9) | 0.867 (85.6) | 0.875 (97.3) | 1.000 (99.3) | 0.944 (90.7) | 0.950 (96.6) | 0.814 (66.6) | 1.000 (99.4) | 0.990 (95.2) | 1.000 (98.3) | 1.000 (99.5) | 0.974 (95.9) | 0.959 (96.7) | 0.877 (94.1) | 0.954 (93.4) | 1.000 (99.6) | 0.877 (94.8) | 0.972 (97.3) | 1.000 (99.5) | 0.948 (87.6) |
| McMurdo Dry Valleys | 0.444 (44.4) | 0.514 (57.2) | 0.309 (15.3) | 0.225 (9.0) | 0.439 (21.6) | 0.168 (9.1) | 0.149 (9.5) | 0.227 (9.2) | 0.320 (10.5) | 0.224 (8.7) | 0.213 (8.8) | 0.514 (29.9) | 0.123 (10.5) | 0.134 (9.9) | 0.271 (9.8) | 0.152 (10.1) | 0.259 (9.4) | 0.411 (20.2) | 0.247 (9.8) | 0.395 (27.6) | 0.270 (10.6) | 0.514 (52.6) | 0.464 (42.3) | 0.514 (57.1) | 0.492 (28.0) | 0.261 (10.2) | 0.395 (38.2) | 0.220 (9.0) | 0.452 (20.2) | 0.110 (10.4) | 0.339 (17.9) | 0.368 (22.4) | 0.514 (46.5) | 0.342 (16.8) | 0.452 (31.9) | 0.514 (56.4) | 0.264 (15.2) | 0.291 (15.3) | 0.319 (17.8) | 0.443 (38.6) | 0.469 (26.9) | 0.449 (21.5) | 0.490 (33.8) | 0.281 (10.8) | 0.472 (32.9) | 0.430 (21.0) | 0.377 (19.0) | 0.486 (33.6) | 0.483 (25.0) | 0.512 (53.3) | 0.514 (61.7) | 0.339 (18.3) | 0.474 (32.3) | 0.514 (59.3) | 0.511 (38.4) | 0.422 (27.9) | 0.355 (17.3) |
| Haughton crater | 0.384 (33.8) | 0.319 (22.3) | 0.401 (26.0) | 0.274 (15.5) | 0.426 (20.1) | 0.274 (20.7) | 0.276 (23.1) | 0.303 (18.0) | 0.349 (13.9) | 0.311 (18.8) | 0.269 (16.1) | 0.395 (11.1) | 0.223 (22.1) | 0.245 (21.4) | 0.312 (14.9) | 0.230 (20.6) | 0.304 (14.8) | 0.426 (22.5) | 0.334 (18.3) | 0.426 (32.5) | 0.349 (19.2) | 0.345 (23.8) | 0.403 (30.8) | 0.344 (28.0) | 0.426 (18.8) | 0.312 (16.2) | 0.426 (43.5) | 0.305 (18.5) | 0.339 (5.2) | 0.208 (23.4) | 0.417 (29.4) | 0.426 (31.2) | 0.362 (17.4) | 0.412 (25.8) | 0.406 (25.3) | 0.341 (26.2) | 0.382 (28.1) | 0.384 (26.9) | 0.398 (31.3) | 0.351 (18.7) | 0.416 (18.2) | 0.393 (13.7) | 0.384 (17.4) | 0.376 (22.1) | 0.420 (25.8) | 0.426 (20.5) | 0.426 (27.2) | 0.418 (24.1) | 0.395 (13.8) | 0.351 (27.4) | 0.307 (27.3) | 0.426 (32.3) | 0.405 (22.3) | 0.318 (23.6) | 0.388 (17.7) | 0.424 (28.2) | 0.421 (25.7) |
| Mojave | 0.388 (34.5) | 0.345 (25.7) | 0.281 (12.3) | 0.184 (3.8) | 0.364 (11.9) | 0.184 (10.7) | 0.176 (12.7) | 0.210 (7.4) | 0.282 (6.4) | 0.223 (8.6) | 0.181 (4.8) | 0.381 (9.4) | 0.112 (9.0) | 0.139 (10.5) | 0.233 (5.6) | 0.124 (5.6) | 0.215 (4.4) | 0.352 (12.7) | 0.239 (9.0) | 0.361 (23.3) | 0.249 (8.5) | 0.384 (30.4) | 0.388 (26.8) | 0.388 (34.9) | 0.388 (11.0) | 0.227 (6.8) | 0.374 (34.5) | 0.220 (9.0) | 0.347 (6.3) | 0.093 (7.7) | 0.304 (13.6) | 0.343 (18.7) | 0.375 (19.1) | 0.297 (11.8) | 0.349 (16.4) | 0.373 (30.3) | 0.249 (13.6) | 0.261 (11.9) | 0.270 (11.7) | 0.324 (15.2) | 0.367 (11.2) | 0.338 (7.1) | 0.358 (13.0) | 0.259 (8.8) | 0.388 (20.5) | 0.345 (10.2) | 0.327 (13.2) | 0.371 (16.7) | 0.371 (10.3) | 0.388 (33.5) | 0.363 (36.8) | 0.312 (15.1) | 0.388 (19.2) | 0.350 (28.0) | 0.368 (14.8) | 0.363 (18.8) | 0.305 (11.6) |
| Utah desert station near Hanksville | 0.902 (92.6) | 0.835 (91.5) | 0.777 (66.6) | 0.485 (40.3) | 0.902 (86.6) | 0.485 (43.1) | 0.490 (46.5) | 0.546 (43.8) | 0.708 (52.5) | 0.578 (47.4) | 0.486 (40.6) | 0.902 (88.6) | 0.342 (34.5) | 0.396 (36.0) | 0.590 (46.9) | 0.363 (35.7) | 0.556 (43.3) | 0.902 (87.3) | 0.613 (45.7) | 0.902 (88.2) | 0.666 (51.8) | 0.881 (91.7) | 0.902 (90.6) | 0.878 (91.8) | 0.902 (71.5) | 0.580 (45.1) | 0.902 (91.6) | 0.564 (46.3) | 0.843 (84.3) | 0.306 (33.7) | 0.820 (77.8) | 0.902 (85.7) | 0.896 (91.7) | 0.819 (73.6) | 0.902 (91.0) | 0.879 (92.0) | 0.708 (64.3) | 0.729 (66.5) | 0.769 (75.1) | 0.836 (93.4) | 0.902 (84.0) | 0.889 (80.3) | 0.889 (91.3) | 0.721 (56.4) | 0.902 (88.3) | 0.902 (82.7) | 0.888 (81.5) | 0.902 (88.2) | 0.902 (87.2) | 0.888 (92.0) | 0.828 (90.9) | 0.833 (81.1) | 0.902 (89.5) | 0.826 (91.3) | 0.902 (91.4) | 0.902 (88.6) | 0.843 (75.4) |
| Iceland's highlands | 0.957 (95.9) | 0.913 (96.5) | 0.800 (69.2) | 0.577 (51.7) | 0.957 (92.7) | 0.575 (52.6) | 0.569 (54.1) | 0.642 (53.4) | 0.802 (64.4) | 0.673 (56.4) | 0.581 (51.8) | 0.957 (93.6) | 0.443 (44.3) | 0.495 (45.7) | 0.680 (56.5) | 0.461 (45.7) | 0.652 (53.7) | 0.957 (93.1) | 0.706 (54.6) | 0.950 (91.9) | 0.738 (59.6) | 0.957 (96.6) | 0.957 (94.3) | 0.957 (96.7) | 0.957 (78.6) | 0.673 (55.2) | 0.909 (92.1) | 0.655 (55.1) | 0.928 (96.5) | 0.409 (43.6) | 0.842 (80.1) | 0.910 (86.6) | 0.957 (96.1) | 0.846 (76.9) | 0.957 (96.5) | 0.957 (97.0) | 0.726 (66.1) | 0.750 (68.8) | 0.796 (78.1) | 0.889 (98.5) | 0.957 (91.6) | 0.957 (93.1) | 0.957 (97.3) | 0.774 (61.8) | 0.957 (92.9) | 0.957 (90.7) | 0.909 (83.8) | 0.957 (93.6) | 0.957 (94.1) | 0.957 (96.6) | 0.930 (96.9) | 0.844 (81.9) | 0.957 (94.1) | 0.919 (97.4) | 0.957 (96.1) | 0.957 (93.6) | 0.873 (78.7) |
| Rio Tinto | 0.105 (2.6) | 0.092 (1.8) | 0.158 (1.0) | 0.150 (0.6) | 0.146 (0.2) | 0.150 (6.9) | 0.140 (8.4) | 0.163 (2.8) | 0.163 (0.0) | 0.156 (1.3) | 0.152 (1.7) | 0.135 (0.0) | 0.148 (13.7) | 0.158 (12.7) | 0.152 (0.2) | 0.146 (9.1) | 0.160 (0.4) | 0.143 (0.1) | 0.166 (2.4) | 0.126 (2.1) | 0.163 (0.8) | 0.100 (2.4) | 0.115 (2.4) | 0.094 (2.5) | 0.166 (2.2) | 0.159 (1.1) | 0.112 (1.9) | 0.158 (2.3) | 0.159 (0.0) | 0.140 (15.0) | 0.146 (0.7) | 0.139 (0.8) | 0.108 (1.7) | 0.154 (0.6) | 0.128 (1.0) | 0.092 (2.4) | 0.151 (2.8) | 0.149 (0.9) | 0.142 (2.1) | 0.111 (2.1) | 0.149 (0.7) | 0.158 (0.7) | 0.126 (0.6) | 0.166 (0.8) | 0.129 (0.8) | 0.155 (0.3) | 0.150 (0.8) | 0.131 (0.8) | 0.146 (0.5) | 0.100 (2.6) | 0.080 (2.6) | 0.140 (0.7) | 0.127 (0.5) | 0.088 (1.8) | 0.124 (0.5) | 0.133 (0.7) | 0.156 (0.5) |
| Qaidam Basin | 0.624 (69.7) | 0.542 (61.2) | 0.937 (87.1) | 0.970 (92.2) | 0.876 (83.1) | 0.954 (90.2) | 0.892 (87.4) | 1.000 (95.8) | 1.000 (97.7) | 1.000 (96.6) | 0.987 (91.0) | 0.802 (78.1) | 0.938 (89.1) | 0.999 (94.8) | 0.981 (94.8) | 0.933 (88.6) | 1.000 (96.3) | 0.837 (79.4) | 1.000 (98.0) | 0.734 (72.6) | 1.000 (98.1) | 0.591 (64.9) | 0.677 (71.0) | 0.554 (63.0) | 0.992 (85.0) | 1.000 (99.1) | 0.644 (69.9) | 1.000 (97.8) | 0.915 (95.3) | 0.895 (85.4) | 0.850 (80.9) | 0.818 (77.6) | 0.644 (67.3) | 0.897 (83.0) | 0.748 (73.8) | 0.545 (60.8) | 0.888 (85.2) | 0.880 (85.7) | 0.823 (81.2) | 0.655 (72.0) | 0.877 (80.5) | 0.946 (91.0) | 0.752 (75.3) | 1.000 (95.7) | 0.760 (74.4) | 0.915 (84.5) | 0.884 (81.2) | 0.761 (73.6) | 0.876 (82.8) | 0.590 (65.5) | 0.466 (54.6) | 0.824 (79.9) | 0.760 (75.3) | 0.521 (60.4) | 0.741 (73.6) | 0.776 (75.0) | 0.911 (83.4) |
| Pilbara | 0.051 (0.6) | 0.041 (0.1) | 0.069 (0.0) | 0.051 (0.0) | 0.064 (0.0) | 0.056 (0.0) | 0.057 (0.3) | 0.059 (0.0) | 0.062 (0.0) | 0.062 (0.0) | 0.052 (0.0) | 0.055 (0.0) | 0.050 (1.2) | 0.052 (0.5) | 0.056 (0.0) | 0.044 (0.0) | 0.055 (0.0) | 0.064 (0.0) | 0.060 (0.0) | 0.064 (0.2) | 0.064 (0.0) | 0.046 (0.2) | 0.055 (0.3) | 0.045 (0.3) | 0.069 (0.2) | 0.055 (0.0) | 0.055 (0.1) | 0.059 (0.0) | 0.045 (0.0) | 0.046 (1.3) | 0.069 (0.0) | 0.069 (0.0) | 0.049 (0.1) | 0.069 (0.0) | 0.059 (0.0) | 0.043 (0.3) | 0.069 (0.0) | 0.069 (0.0) | 0.069 (0.2) | 0.049 (0.1) | 0.064 (0.0) | 0.066 (0.0) | 0.055 (0.0) | 0.069 (0.0) | 0.059 (0.0) | 0.067 (0.0) | 0.069 (0.0) | 0.059 (0.0) | 0.062 (0.0) | 0.047 (0.3) | 0.037 (0.3) | 0.068 (0.0) | 0.058 (0.0) | 0.041 (0.1) | 0.055 (0.0) | 0.062 (0.0) | 0.069 (0.0) |
| Dhofar in Oman | 0.190 (8.4) | 0.208 (9.4) | 0.552 (42.3) | 0.850 (76.4) | 0.544 (34.7) | 0.790 (70.3) | 0.653 (62.2) | 0.861 (71.6) | 0.750 (57.1) | 0.754 (63.6) | 0.858 (75.4) | 0.493 (26.6) | 0.855 (78.1) | 0.895 (78.4) | 0.814 (70.7) | 0.880 (82.8) | 0.891 (75.5) | 0.484 (30.7) | 0.846 (68.7) | 0.283 (13.4) | 0.713 (56.2) | 0.187 (8.3) | 0.224 (8.7) | 0.171 (8.5) | 0.415 (17.0) | 0.860 (75.2) | 0.234 (10.5) | 0.797 (67.5) | 0.820 (79.3) | 0.826 (79.0) | 0.412 (28.7) | 0.349 (19.7) | 0.269 (9.8) | 0.464 (33.1) | 0.303 (10.7) | 0.174 (8.6) | 0.515 (42.7) | 0.501 (40.7) | 0.349 (23.4) | 0.230 (8.7) | 0.439 (22.6) | 0.484 (27.0) | 0.368 (14.6) | 0.680 (52.0) | 0.324 (12.2) | 0.538 (34.4) | 0.420 (26.2) | 0.318 (10.5) | 0.500 (28.2) | 0.169 (8.2) | 0.147 (9.0) | 0.391 (26.4) | 0.368 (16.2) | 0.205 (9.6) | 0.339 (11.1) | 0.343 (16.1) | 0.473 (33.1) |
| Lanzarote | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) |
| Svalbard | 0.423 (41.0) | 0.592 (68.7) | 0.272 (11.4) | 0.240 (11.0) | 0.444 (22.2) | 0.159 (7.9) | 0.135 (7.8) | 0.218 (8.3) | 0.342 (13.1) | 0.231 (9.6) | 0.219 (9.6) | 0.561 (36.6) | 0.085 (5.8) | 0.100 (6.0) | 0.284 (11.4) | 0.137 (7.6) | 0.270 (10.7) | 0.410 (20.1) | 0.234 (8.6) | 0.366 (23.8) | 0.263 (9.8) | 0.526 (54.9) | 0.446 (39.0) | 0.500 (54.8) | 0.508 (30.0) | 0.252 (9.4) | 0.385 (36.5) | 0.217 (8.7) | 0.482 (23.9) | 0.081 (5.8) | 0.315 (14.9) | 0.347 (19.3) | 0.557 (52.5) | 0.324 (14.7) | 0.468 (34.1) | 0.569 (63.9) | 0.219 (9.4) | 0.263 (12.2) | 0.306 (16.1) | 0.525 (51.5) | 0.486 (29.5) | 0.511 (31.2) | 0.519 (38.5) | 0.278 (10.5) | 0.465 (31.9) | 0.430 (21.0) | 0.363 (17.2) | 0.514 (40.1) | 0.508 (29.3) | 0.496 (50.4) | 0.589 (70.9) | 0.317 (15.7) | 0.462 (30.5) | 0.569 (66.9) | 0.565 (47.9) | 0.412 (26.4) | 0.332 (14.7) |

**environment: score (percentile among ranked squares)**

| Site | Jezero | Gale | Phoenix | Arcadia Planitia | Deuteronilus Mensae | Viking 1 | Viking 2 | Pathfinder | Spirit | Opportunity | InSight | Phlegra Montes | AP-1 (Arcadia Planitia) | AP-9 (Arcadia Planitia) | EM-16 (Erebus Montes) | AP-8 (Arcadia Planitia) | EM-15 (Erebus Montes) | PM-7 (Phlegra Montes) | Phlegra Dorsa, Arcadia Planitia | Southern Nectaris Fossae | Valles Marineris mouth (southern Acidalia Planitia, as named in the abstract) | East Melas Chasma | Mawrth Vallis | Nili Fossae | Acheron Fossae | Hebrus Valles | Newton crater | Zephyria Planum hills ('Sea Urchins') | Cerberus (west of Zunil crater) | Amazonis Planitia mid-latitude ice | Western Noachis Terra chloride deposits | South of Valles Marineris (equatorial site) | McLaughlin crater | South of Firsoff crater, Arabia Terra | Ismenius Cavus | Hale crater | Copernicus crater | Huygens crater | Mesopotamia (east rim of Hellas) | Western Coprates Chasma | Hellas Rim | Eastern rim of Hellas impact basin | Columbus crater | South-west Sinus Meridiani | Apollinaris Sulci | Deuteronilus Mensae (debris apron zone) | Ausonia Cavus | Kasei Valles | Gusev crater - Apollinaris Sulci | Aram Chaos | Noctis Landing | Hypanis (Hypanis and Sabrina deltas) | Hadriacus Palus and Cavi | Protonilus Mensae | Eastern outlet of Valles Marineris | Tempe Terra | Southern edge of Meridiani Planum (Endeavour crater area) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Atacama near Yungay | 0.530 (95.1) | 0.528 (95.1) | 0.469 (95.1) | 0.496 (95.1) | 0.503 (95.1) | 0.525 (95.1) | 0.489 (95.1) | 0.532 (95.1) | 0.516 (95.1) | 0.534 (95.1) | 0.527 (95.1) | 0.502 (95.1) | 0.498 (95.1) | 0.496 (95.1) | 0.496 (95.1) | 0.498 (95.1) | 0.498 (95.1) | 0.500 (95.1) | 0.502 (95.1) | 0.519 (95.1) | 0.530 (95.1) | 0.535 (95.1) | 0.524 (95.1) | 0.528 (95.1) | 0.492 (95.1) | 0.523 (95.1) | 0.500 (95.1) | 0.510 (95.1) | 0.519 (95.1) | 0.492 (95.1) | 0.501 (95.1) | 0.530 (95.1) | 0.528 (95.1) | 0.536 (95.1) | 0.500 (95.1) | 0.503 (95.1) | 0.487 (95.1) | 0.525 (95.1) | 0.508 (95.1) | 0.534 (95.1) | 0.500 (95.1) | 0.498 (95.1) | 0.513 (95.1) | 0.534 (95.1) | 0.510 (95.1) | 0.501 (95.1) | 0.510 (95.1) | 0.496 (95.1) | 0.511 (95.1) | 0.537 (95.1) | 0.514 (95.1) | 0.530 (95.1) | 0.514 (95.1) | 0.499 (95.1) | 0.535 (95.1) | 0.486 (95.1) | 0.534 (95.1) |
| McMurdo Dry Valleys | 0.420 (77.0) | 0.418 (77.0) | 0.372 (77.0) | 0.394 (77.0) | 0.399 (77.0) | 0.416 (77.0) | 0.388 (77.0) | 0.422 (77.0) | 0.410 (77.0) | 0.424 (77.0) | 0.418 (77.0) | 0.398 (77.0) | 0.395 (77.0) | 0.394 (77.0) | 0.394 (77.0) | 0.395 (77.0) | 0.395 (77.0) | 0.397 (77.0) | 0.398 (77.0) | 0.411 (77.0) | 0.420 (77.0) | 0.424 (77.0) | 0.415 (77.0) | 0.419 (77.0) | 0.390 (77.0) | 0.414 (77.0) | 0.397 (77.0) | 0.404 (77.0) | 0.411 (77.0) | 0.390 (77.0) | 0.397 (77.0) | 0.420 (77.0) | 0.419 (77.0) | 0.425 (77.0) | 0.396 (77.0) | 0.399 (77.0) | 0.387 (77.0) | 0.416 (77.0) | 0.403 (77.0) | 0.423 (77.0) | 0.396 (77.0) | 0.395 (77.0) | 0.407 (77.0) | 0.424 (77.0) | 0.405 (77.0) | 0.397 (77.0) | 0.405 (77.0) | 0.394 (77.0) | 0.405 (77.0) | 0.426 (77.0) | 0.408 (77.0) | 0.420 (77.0) | 0.408 (77.0) | 0.396 (77.0) | 0.424 (77.0) | 0.385 (77.0) | 0.423 (77.0) |
| Haughton crater | 0.240 (29.3) | 0.239 (29.3) | 0.213 (29.3) | 0.225 (29.3) | 0.228 (29.3) | 0.238 (29.3) | 0.222 (29.3) | 0.241 (29.3) | 0.234 (29.3) | 0.242 (29.3) | 0.239 (29.3) | 0.228 (29.3) | 0.226 (29.3) | 0.225 (29.3) | 0.225 (29.3) | 0.225 (29.3) | 0.226 (29.3) | 0.227 (29.3) | 0.227 (29.3) | 0.235 (29.3) | 0.240 (29.3) | 0.242 (29.3) | 0.237 (29.3) | 0.239 (29.3) | 0.223 (29.3) | 0.237 (29.3) | 0.227 (29.3) | 0.231 (29.3) | 0.235 (29.3) | 0.223 (29.3) | 0.227 (29.3) | 0.240 (29.3) | 0.239 (29.3) | 0.243 (29.3) | 0.226 (29.3) | 0.228 (29.3) | 0.221 (29.3) | 0.238 (29.3) | 0.230 (29.3) | 0.242 (29.3) | 0.226 (29.3) | 0.225 (29.3) | 0.232 (29.3) | 0.242 (29.3) | 0.231 (29.3) | 0.227 (29.3) | 0.231 (29.3) | 0.225 (29.3) | 0.232 (29.3) | 0.243 (29.3) | 0.233 (29.3) | 0.240 (29.3) | 0.233 (29.3) | 0.226 (29.2) | 0.242 (29.3) | 0.220 (29.3) | 0.242 (29.3) |
| Mojave | 0.202 (22.4) | 0.201 (22.5) | 0.179 (22.4) | 0.189 (22.5) | 0.191 (22.5) | 0.200 (22.4) | 0.186 (22.4) | 0.202 (22.4) | 0.197 (22.4) | 0.203 (22.4) | 0.201 (22.4) | 0.191 (22.4) | 0.189 (22.4) | 0.189 (22.5) | 0.189 (22.5) | 0.189 (22.4) | 0.189 (22.4) | 0.190 (22.4) | 0.191 (22.4) | 0.197 (22.4) | 0.202 (22.4) | 0.204 (22.4) | 0.199 (22.5) | 0.201 (22.4) | 0.187 (22.5) | 0.199 (22.4) | 0.190 (22.5) | 0.194 (22.4) | 0.198 (22.4) | 0.187 (22.5) | 0.191 (22.4) | 0.202 (22.4) | 0.201 (22.5) | 0.204 (22.4) | 0.190 (22.5) | 0.191 (22.4) | 0.185 (22.4) | 0.200 (22.4) | 0.193 (22.4) | 0.203 (22.4) | 0.190 (22.5) | 0.189 (22.4) | 0.195 (22.4) | 0.203 (22.4) | 0.194 (22.5) | 0.191 (22.5) | 0.194 (22.4) | 0.189 (22.5) | 0.194 (22.4) | 0.204 (22.4) | 0.196 (22.4) | 0.202 (22.4) | 0.196 (22.4) | 0.190 (22.5) | 0.204 (22.4) | 0.185 (22.5) | 0.203 (22.4) |
| Utah desert station near Hanksville | 0.346 (54.8) | 0.345 (54.8) | 0.307 (54.8) | 0.324 (54.8) | 0.328 (54.8) | 0.343 (55.0) | 0.320 (54.8) | 0.347 (54.8) | 0.337 (54.8) | 0.349 (54.8) | 0.344 (54.8) | 0.328 (54.8) | 0.325 (54.9) | 0.324 (54.8) | 0.324 (54.8) | 0.325 (54.8) | 0.325 (54.9) | 0.327 (54.8) | 0.328 (54.8) | 0.339 (54.8) | 0.346 (54.8) | 0.349 (54.8) | 0.342 (54.8) | 0.345 (54.8) | 0.321 (54.8) | 0.341 (54.8) | 0.327 (54.8) | 0.333 (54.8) | 0.339 (54.8) | 0.321 (54.8) | 0.327 (54.8) | 0.346 (54.8) | 0.345 (54.8) | 0.350 (54.8) | 0.327 (55.0) | 0.328 (54.8) | 0.318 (54.8) | 0.343 (54.8) | 0.332 (54.8) | 0.349 (54.8) | 0.327 (55.0) | 0.325 (54.8) | 0.335 (54.8) | 0.349 (54.8) | 0.333 (54.8) | 0.327 (54.8) | 0.333 (54.8) | 0.324 (54.8) | 0.334 (54.8) | 0.351 (54.8) | 0.336 (54.8) | 0.346 (54.8) | 0.336 (54.8) | 0.326 (54.8) | 0.349 (54.8) | 0.317 (54.8) | 0.349 (54.8) |
| Iceland's highlands | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) |
| Rio Tinto | 0.044 (10.3) | 0.043 (10.3) | 0.039 (10.3) | 0.041 (10.3) | 0.041 (10.3) | 0.043 (10.3) | 0.040 (10.3) | 0.044 (10.3) | 0.043 (10.3) | 0.044 (10.3) | 0.043 (10.3) | 0.041 (10.3) | 0.041 (10.3) | 0.041 (10.3) | 0.041 (10.3) | 0.041 (10.3) | 0.041 (10.3) | 0.041 (10.3) | 0.041 (10.3) | 0.043 (10.3) | 0.044 (10.3) | 0.044 (10.3) | 0.043 (10.3) | 0.043 (10.3) | 0.041 (10.3) | 0.043 (10.3) | 0.041 (10.3) | 0.042 (10.3) | 0.043 (10.3) | 0.041 (10.3) | 0.041 (10.3) | 0.044 (10.3) | 0.043 (10.3) | 0.044 (10.3) | 0.041 (10.3) | 0.041 (10.3) | 0.040 (10.3) | 0.043 (10.3) | 0.042 (10.3) | 0.044 (10.3) | 0.041 (10.3) | 0.041 (10.3) | 0.042 (10.3) | 0.044 (10.3) | 0.042 (10.3) | 0.041 (10.3) | 0.042 (10.3) | 0.041 (10.3) | 0.042 (10.3) | 0.044 (10.3) | 0.042 (10.3) | 0.044 (10.3) | 0.042 (10.3) | 0.041 (10.3) | 0.044 (10.3) | 0.040 (10.3) | 0.044 (10.3) |
| Qaidam Basin | 0.649 (99.6) | 0.646 (99.6) | 0.575 (99.6) | 0.608 (99.6) | 0.616 (99.6) | 0.644 (99.6) | 0.600 (99.6) | 0.651 (99.6) | 0.633 (99.6) | 0.655 (99.6) | 0.645 (99.6) | 0.616 (99.6) | 0.610 (99.6) | 0.608 (99.6) | 0.608 (99.6) | 0.610 (99.6) | 0.610 (99.6) | 0.613 (99.6) | 0.615 (99.6) | 0.636 (99.6) | 0.649 (99.6) | 0.656 (99.6) | 0.642 (99.6) | 0.647 (99.6) | 0.603 (99.6) | 0.640 (99.6) | 0.613 (99.6) | 0.625 (99.6) | 0.636 (99.6) | 0.603 (99.6) | 0.613 (99.6) | 0.649 (99.6) | 0.647 (99.6) | 0.656 (99.6) | 0.613 (99.6) | 0.616 (99.6) | 0.597 (99.6) | 0.643 (99.6) | 0.623 (99.6) | 0.654 (99.6) | 0.613 (99.6) | 0.610 (99.6) | 0.628 (99.6) | 0.655 (99.6) | 0.625 (99.6) | 0.614 (99.6) | 0.625 (99.6) | 0.608 (99.6) | 0.626 (99.6) | 0.658 (99.6) | 0.630 (99.6) | 0.649 (99.6) | 0.630 (99.6) | 0.612 (99.6) | 0.656 (99.6) | 0.595 (99.6) | 0.654 (99.6) |
| Pilbara | 0.021 (10.1) | 0.021 (10.1) | 0.019 (10.1) | 0.020 (10.1) | 0.020 (10.1) | 0.021 (10.1) | 0.020 (10.1) | 0.021 (10.1) | 0.021 (10.1) | 0.021 (10.1) | 0.021 (10.1) | 0.020 (10.1) | 0.020 (10.1) | 0.020 (10.1) | 0.020 (10.1) | 0.020 (10.1) | 0.020 (10.1) | 0.020 (10.1) | 0.020 (10.1) | 0.021 (10.1) | 0.021 (10.1) | 0.021 (10.1) | 0.021 (10.1) | 0.021 (10.1) | 0.020 (10.1) | 0.021 (10.1) | 0.020 (10.1) | 0.021 (10.1) | 0.021 (10.1) | 0.020 (10.1) | 0.020 (10.1) | 0.021 (10.1) | 0.021 (10.1) | 0.021 (10.1) | 0.020 (10.1) | 0.020 (10.1) | 0.019 (10.1) | 0.021 (10.1) | 0.020 (10.1) | 0.021 (10.1) | 0.020 (10.1) | 0.020 (10.1) | 0.021 (10.1) | 0.021 (10.1) | 0.021 (10.1) | 0.020 (10.1) | 0.021 (10.1) | 0.020 (10.1) | 0.021 (10.1) | 0.021 (10.1) | 0.021 (10.1) | 0.021 (10.1) | 0.021 (10.1) | 0.020 (10.1) | 0.021 (10.1) | 0.019 (10.1) | 0.021 (10.1) |
| Dhofar in Oman | 0.221 (25.7) | 0.220 (25.7) | 0.195 (25.7) | 0.206 (25.7) | 0.209 (25.7) | 0.218 (25.7) | 0.204 (25.7) | 0.221 (25.7) | 0.215 (25.7) | 0.222 (25.7) | 0.219 (25.7) | 0.209 (25.7) | 0.207 (25.7) | 0.206 (25.7) | 0.206 (25.7) | 0.207 (25.7) | 0.207 (25.7) | 0.208 (25.7) | 0.209 (25.7) | 0.216 (25.7) | 0.220 (25.7) | 0.223 (25.7) | 0.218 (25.7) | 0.220 (25.7) | 0.205 (25.7) | 0.217 (25.7) | 0.208 (25.7) | 0.212 (25.7) | 0.216 (25.7) | 0.205 (25.7) | 0.208 (25.7) | 0.220 (25.7) | 0.220 (25.7) | 0.223 (25.7) | 0.208 (25.7) | 0.209 (25.7) | 0.203 (25.7) | 0.218 (25.7) | 0.211 (25.7) | 0.222 (25.7) | 0.208 (25.7) | 0.207 (25.7) | 0.213 (25.7) | 0.222 (25.7) | 0.212 (25.7) | 0.208 (25.7) | 0.212 (25.7) | 0.206 (25.7) | 0.213 (25.7) | 0.223 (25.7) | 0.214 (25.7) | 0.221 (25.7) | 0.214 (25.7) | 0.208 (25.7) | 0.223 (25.7) | 0.202 (25.7) | 0.222 (25.7) |
| Lanzarote | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) |
| Svalbard | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) | 0.000 (5.1) |

**full: score (percentile among ranked squares)**

| Site | Jezero | Gale | Phoenix | Arcadia Planitia | Deuteronilus Mensae | Viking 1 | Viking 2 | Pathfinder | Spirit | Opportunity | InSight | Phlegra Montes | AP-1 (Arcadia Planitia) | AP-9 (Arcadia Planitia) | EM-16 (Erebus Montes) | AP-8 (Arcadia Planitia) | EM-15 (Erebus Montes) | PM-7 (Phlegra Montes) | Phlegra Dorsa, Arcadia Planitia | Southern Nectaris Fossae | Valles Marineris mouth (southern Acidalia Planitia, as named in the abstract) | East Melas Chasma | Mawrth Vallis | Nili Fossae | Acheron Fossae | Hebrus Valles | Newton crater | Zephyria Planum hills ('Sea Urchins') | Cerberus (west of Zunil crater) | Amazonis Planitia mid-latitude ice | Western Noachis Terra chloride deposits | South of Valles Marineris (equatorial site) | McLaughlin crater | South of Firsoff crater, Arabia Terra | Ismenius Cavus | Hale crater | Copernicus crater | Huygens crater | Mesopotamia (east rim of Hellas) | Western Coprates Chasma | Hellas Rim | Eastern rim of Hellas impact basin | Columbus crater | South-west Sinus Meridiani | Apollinaris Sulci | Deuteronilus Mensae (debris apron zone) | Ausonia Cavus | Kasei Valles | Gusev crater - Apollinaris Sulci | Aram Chaos | Noctis Landing | Hypanis (Hypanis and Sabrina deltas) | Hadriacus Palus and Cavi | Protonilus Mensae | Eastern outlet of Valles Marineris | Tempe Terra | Southern edge of Meridiani Planum (Endeavour crater area) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Atacama near Yungay | 0.681 (99.1) | 0.641 (98.6) | 0.375 (74.6) | 0.482 (78.1) | 0.611 (95.8) | 0.537 (86.1) | 0.452 (80.3) | 0.566 (89.0) | 0.610 (98.6) | 0.578 (94.5) | 0.535 (88.2) | 0.624 (97.1) | 0.425 (67.3) | 0.446 (70.4) | 0.515 (84.9) | 0.431 (69.7) | 0.507 (81.3) | 0.619 (96.7) | 0.530 (85.5) | 0.656 (98.7) | 0.607 (97.1) | 0.670 (98.7) | 0.671 (98.8) | 0.665 (98.5) | 0.601 (93.8) | 0.571 (93.1) | 0.604 (96.4) | 0.558 (94.1) | 0.643 (98.8) | 0.389 (64.4) | 0.601 (95.8) | 0.680 (99.3) | 0.668 (98.4) | 0.664 (99.7) | 0.623 (97.7) | 0.609 (96.8) | 0.516 (92.4) | 0.631 (99.3) | 0.594 (95.5) | 0.648 (99.0) | 0.609 (95.4) | 0.590 (94.1) | 0.638 (98.0) | 0.629 (99.3) | 0.665 (99.0) | 0.600 (94.7) | 0.640 (97.9) | 0.649 (98.8) | 0.658 (98.8) | 0.673 (99.2) | 0.633 (98.4) | 0.668 (99.4) | 0.659 (98.6) | 0.566 (95.5) | 0.675 (99.2) | 0.587 (95.3) | 0.668 (99.7) |
| McMurdo Dry Valleys | 0.000 (12.4) | 0.000 (12.6) | 0.429 (86.7) | 0.299 (32.1) | 0.395 (50.0) | 0.000 (11.4) | 0.284 (34.4) | 0.000 (12.2) | 0.000 (12.6) | 0.000 (12.7) | 0.000 (12.6) | 0.384 (48.6) | 0.239 (26.1) | 0.248 (25.8) | 0.328 (36.0) | 0.264 (29.1) | 0.322 (34.2) | 0.362 (43.8) | 0.313 (31.7) | 0.184 (21.5) | 0.000 (12.2) | 0.000 (12.6) | 0.000 (10.6) | 0.000 (11.6) | 0.413 (55.0) | 0.000 (12.2) | 0.388 (63.1) | 0.000 (12.7) | 0.000 (12.6) | 0.248 (29.6) | 0.341 (41.5) | 0.000 (12.3) | 0.000 (11.6) | 0.000 (12.8) | 0.346 (45.6) | 0.384 (64.6) | 0.362 (50.5) | 0.000 (12.6) | 0.320 (38.6) | 0.000 (12.6) | 0.404 (54.0) | 0.403 (52.4) | 0.215 (22.9) | 0.000 (12.6) | 0.000 (12.6) | 0.404 (52.1) | 0.299 (33.2) | 0.000 (10.3) | 0.000 (12.6) | 0.000 (12.6) | 0.000 (12.6) | 0.000 (12.6) | 0.000 (9.5) | 0.441 (80.6) | 0.000 (12.6) | 0.402 (60.4) | 0.000 (12.6) |
| Haughton crater | 0.000 (12.4) | 0.000 (12.6) | 0.371 (73.3) | 0.259 (22.8) | 0.311 (28.7) | 0.000 (11.4) | 0.286 (34.8) | 0.000 (12.2) | 0.000 (12.6) | 0.000 (12.7) | 0.000 (12.6) | 0.280 (23.8) | 0.241 (26.5) | 0.251 (26.3) | 0.276 (23.8) | 0.248 (25.4) | 0.273 (23.1) | 0.296 (28.2) | 0.282 (25.2) | 0.226 (25.9) | 0.000 (12.2) | 0.000 (12.6) | 0.000 (10.6) | 0.000 (11.6) | 0.311 (28.5) | 0.000 (12.2) | 0.318 (41.3) | 0.000 (12.7) | 0.000 (12.6) | 0.253 (30.6) | 0.298 (31.5) | 0.000 (12.3) | 0.000 (11.6) | 0.000 (12.8) | 0.273 (29.1) | 0.265 (30.6) | 0.329 (41.1) | 0.000 (12.6) | 0.284 (31.1) | 0.000 (12.6) | 0.307 (28.6) | 0.304 (26.8) | 0.217 (23.2) | 0.000 (12.6) | 0.000 (12.6) | 0.320 (29.8) | 0.265 (27.1) | 0.000 (10.3) | 0.000 (12.6) | 0.000 (12.6) | 0.000 (12.6) | 0.000 (12.6) | 0.138 (19.8) | 0.288 (34.4) | 0.000 (12.6) | 0.319 (35.2) | 0.000 (12.6) |
| Mojave | 0.359 (54.2) | 0.329 (50.9) | 0.247 (37.2) | 0.267 (24.6) | 0.353 (38.5) | 0.267 (32.2) | 0.249 (25.9) | 0.282 (31.7) | 0.309 (34.4) | 0.275 (33.0) | 0.254 (30.4) | 0.363 (43.3) | 0.218 (22.5) | 0.237 (23.8) | 0.292 (27.5) | 0.226 (21.2) | 0.284 (25.4) | 0.351 (40.9) | 0.298 (28.4) | 0.354 (48.5) | 0.302 (33.9) | 0.355 (53.1) | 0.360 (51.7) | 0.360 (57.1) | 0.356 (39.2) | 0.288 (32.2) | 0.353 (52.7) | 0.265 (32.9) | 0.333 (36.5) | 0.195 (18.7) | 0.330 (38.6) | 0.342 (43.4) | 0.355 (49.3) | 0.306 (38.7) | 0.349 (46.4) | 0.360 (57.8) | 0.283 (29.7) | 0.302 (36.6) | 0.318 (38.1) | 0.331 (46.1) | 0.353 (39.5) | 0.339 (35.2) | 0.351 (45.3) | 0.292 (34.5) | 0.347 (46.3) | 0.342 (35.3) | 0.342 (41.7) | 0.343 (46.0) | 0.342 (41.0) | 0.345 (54.4) | 0.333 (58.5) | 0.325 (40.8) | 0.359 (46.9) | 0.341 (50.8) | 0.340 (44.5) | 0.341 (41.0) | 0.314 (38.4) |
| Utah desert station near Hanksville | 0.487 (82.3) | 0.446 (80.1) | 0.380 (75.8) | 0.391 (53.9) | 0.505 (81.7) | 0.381 (49.7) | 0.376 (58.5) | 0.400 (49.3) | 0.431 (54.7) | 0.380 (49.8) | 0.358 (45.6) | 0.502 (81.4) | 0.341 (48.0) | 0.361 (50.1) | 0.423 (59.7) | 0.348 (49.1) | 0.414 (56.2) | 0.504 (81.8) | 0.432 (59.3) | 0.497 (79.9) | 0.433 (55.6) | 0.476 (81.5) | 0.489 (80.7) | 0.484 (83.7) | 0.499 (77.5) | 0.406 (50.6) | 0.502 (87.8) | 0.364 (48.8) | 0.456 (63.9) | 0.315 (45.9) | 0.485 (78.1) | 0.487 (73.6) | 0.488 (80.8) | 0.431 (61.3) | 0.498 (82.5) | 0.497 (87.2) | 0.431 (72.5) | 0.439 (61.7) | 0.475 (75.5) | 0.465 (77.0) | 0.503 (81.3) | 0.499 (79.5) | 0.491 (78.7) | 0.416 (54.5) | 0.468 (74.5) | 0.502 (81.0) | 0.496 (76.0) | 0.474 (76.7) | 0.469 (67.6) | 0.454 (79.3) | 0.443 (83.0) | 0.463 (68.9) | 0.489 (77.7) | 0.481 (87.4) | 0.462 (72.6) | 0.490 (84.8) | 0.446 (62.9) |
| Iceland's highlands | 0.000 (12.4) | 0.000 (12.6) | 0.000 (10.8) | 0.000 (5.0) | 0.000 (5.0) | 0.000 (11.4) | 0.000 (5.0) | 0.000 (12.2) | 0.000 (12.6) | 0.000 (12.7) | 0.000 (12.6) | 0.000 (5.1) | 0.000 (5.0) | 0.000 (5.0) | 0.000 (5.0) | 0.000 (5.0) | 0.000 (5.0) | 0.000 (5.0) | 0.000 (5.0) | 0.000 (8.5) | 0.000 (12.2) | 0.000 (12.6) | 0.000 (10.6) | 0.000 (11.6) | 0.000 (5.0) | 0.000 (12.2) | 0.000 (5.0) | 0.000 (12.7) | 0.000 (12.6) | 0.000 (5.0) | 0.000 (5.0) | 0.000 (12.3) | 0.000 (11.6) | 0.000 (12.8) | 0.000 (5.5) | 0.000 (5.1) | 0.000 (5.0) | 0.000 (12.6) | 0.000 (5.1) | 0.000 (12.6) | 0.000 (5.0) | 0.000 (5.0) | 0.000 (8.5) | 0.000 (12.6) | 0.000 (12.6) | 0.000 (5.0) | 0.000 (7.0) | 0.000 (10.3) | 0.000 (12.6) | 0.000 (12.6) | 0.000 (12.6) | 0.000 (12.6) | 0.000 (9.5) | 0.000 (5.0) | 0.000 (12.6) | 0.000 (5.0) | 0.000 (12.6) |
| Rio Tinto | 0.118 (25.5) | 0.106 (25.4) | 0.113 (22.6) | 0.139 (10.6) | 0.139 (10.5) | 0.136 (24.0) | 0.129 (11.0) | 0.141 (25.0) | 0.137 (25.4) | 0.130 (25.5) | 0.130 (25.4) | 0.134 (10.6) | 0.138 (11.9) | 0.141 (11.6) | 0.139 (10.5) | 0.137 (11.0) | 0.143 (10.6) | 0.137 (10.5) | 0.146 (10.7) | 0.129 (17.7) | 0.141 (24.9) | 0.114 (25.5) | 0.123 (21.9) | 0.113 (23.9) | 0.143 (10.9) | 0.139 (24.9) | 0.123 (11.0) | 0.127 (25.5) | 0.134 (25.4) | 0.130 (11.6) | 0.138 (10.7) | 0.132 (25.1) | 0.120 (23.6) | 0.128 (25.8) | 0.130 (11.6) | 0.115 (11.3) | 0.132 (10.9) | 0.133 (25.4) | 0.138 (11.1) | 0.119 (25.4) | 0.140 (10.7) | 0.142 (10.7) | 0.129 (17.4) | 0.133 (25.4) | 0.123 (25.4) | 0.141 (10.6) | 0.139 (14.7) | 0.125 (21.2) | 0.130 (25.4) | 0.109 (25.6) | 0.100 (25.7) | 0.130 (25.4) | 0.128 (19.5) | 0.111 (10.9) | 0.121 (25.4) | 0.129 (10.8) | 0.131 (25.4) |
| Qaidam Basin | 0.588 (95.8) | 0.525 (93.4) | 0.573 (99.8) | 0.723 (100.0) | 0.699 (99.3) | 0.699 (100.0) | 0.669 (100.0) | 0.713 (100.0) | 0.692 (99.9) | 0.662 (100.0) | 0.666 (100.0) | 0.671 (98.5) | 0.714 (100.0) | 0.731 (100.0) | 0.726 (100.0) | 0.710 (100.0) | 0.733 (100.0) | 0.684 (99.2) | 0.736 (100.0) | 0.640 (98.1) | 0.713 (100.0) | 0.568 (94.6) | 0.611 (96.7) | 0.564 (94.2) | 0.725 (99.7) | 0.707 (100.0) | 0.615 (96.9) | 0.640 (100.0) | 0.659 (99.3) | 0.677 (100.0) | 0.689 (99.4) | 0.656 (98.9) | 0.599 (96.1) | 0.626 (99.1) | 0.646 (98.5) | 0.575 (95.0) | 0.660 (99.8) | 0.662 (99.7) | 0.683 (99.5) | 0.591 (97.1) | 0.697 (99.2) | 0.716 (99.7) | 0.643 (98.1) | 0.664 (99.8) | 0.612 (97.5) | 0.707 (99.5) | 0.694 (99.3) | 0.620 (97.9) | 0.649 (98.5) | 0.540 (93.5) | 0.492 (90.7) | 0.645 (99.1) | 0.639 (98.1) | 0.560 (95.0) | 0.598 (96.6) | 0.646 (98.7) | 0.644 (99.3) |
| Pilbara | 0.088 (24.9) | 0.081 (25.3) | 0.047 (21.6) | 0.077 (10.1) | 0.085 (10.1) | 0.090 (23.2) | 0.074 (10.1) | 0.093 (24.6) | 0.094 (25.3) | 0.096 (25.3) | 0.089 (25.3) | 0.082 (10.3) | 0.076 (10.1) | 0.077 (10.1) | 0.079 (10.1) | 0.072 (10.1) | 0.079 (10.1) | 0.086 (10.1) | 0.083 (10.1) | 0.092 (17.0) | 0.097 (24.5) | 0.085 (25.3) | 0.088 (21.2) | 0.083 (23.3) | 0.086 (10.1) | 0.090 (24.5) | 0.079 (10.1) | 0.091 (25.4) | 0.083 (25.3) | 0.069 (10.1) | 0.088 (10.1) | 0.099 (24.7) | 0.086 (23.3) | 0.100 (25.7) | 0.084 (11.0) | 0.074 (10.3) | 0.079 (10.1) | 0.099 (25.3) | 0.090 (10.3) | 0.087 (25.3) | 0.085 (10.0) | 0.085 (10.0) | 0.086 (17.0) | 0.100 (25.3) | 0.091 (25.3) | 0.085 (10.1) | 0.092 (14.0) | 0.088 (20.7) | 0.093 (25.3) | 0.086 (25.3) | 0.076 (25.3) | 0.099 (25.3) | 0.088 (19.1) | 0.069 (10.1) | 0.091 (25.3) | 0.080 (10.1) | 0.100 (25.3) |
| Dhofar in Oman | 0.206 (31.3) | 0.215 (32.2) | 0.000 (10.8) | 0.324 (37.9) | 0.273 (20.8) | 0.357 (45.4) | 0.269 (30.7) | 0.377 (45.2) | 0.354 (41.2) | 0.362 (46.7) | 0.378 (49.3) | 0.269 (21.6) | 0.324 (44.1) | 0.329 (42.6) | 0.317 (33.2) | 0.325 (43.4) | 0.329 (36.0) | 0.265 (21.9) | 0.326 (34.4) | 0.228 (26.3) | 0.348 (40.7) | 0.207 (31.1) | 0.213 (29.7) | 0.194 (30.7) | 0.241 (17.5) | 0.371 (44.3) | 0.192 (16.2) | 0.360 (48.1) | 0.368 (42.4) | 0.301 (42.3) | 0.247 (21.0) | 0.263 (32.6) | 0.233 (31.8) | 0.299 (37.9) | 0.223 (20.2) | 0.178 (16.1) | 0.240 (21.0) | 0.304 (37.1) | 0.236 (21.4) | 0.225 (31.6) | 0.250 (18.5) | 0.257 (19.0) | 0.251 (28.2) | 0.348 (43.3) | 0.251 (32.4) | 0.268 (19.7) | 0.260 (26.2) | 0.237 (30.8) | 0.299 (35.0) | 0.200 (31.5) | 0.184 (31.9) | 0.277 (34.1) | 0.255 (30.4) | 0.180 (16.0) | 0.263 (33.0) | 0.217 (16.9) | 0.301 (36.5) |
| Lanzarote | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) |
| Svalbard | 0.000 (12.4) | 0.000 (12.6) | 0.000 (10.8) | 0.000 (5.0) | 0.000 (5.0) | 0.000 (11.4) | 0.000 (5.0) | 0.000 (12.2) | 0.000 (12.6) | 0.000 (12.7) | 0.000 (12.6) | 0.000 (5.1) | 0.000 (5.0) | 0.000 (5.0) | 0.000 (5.0) | 0.000 (5.0) | 0.000 (5.0) | 0.000 (5.0) | 0.000 (5.0) | 0.000 (8.5) | 0.000 (12.2) | 0.000 (12.6) | 0.000 (10.6) | 0.000 (11.6) | 0.000 (5.0) | 0.000 (12.2) | 0.000 (5.0) | 0.000 (12.7) | 0.000 (12.6) | 0.000 (5.0) | 0.000 (5.0) | 0.000 (12.3) | 0.000 (11.6) | 0.000 (12.8) | 0.000 (5.5) | 0.000 (5.1) | 0.000 (5.0) | 0.000 (12.6) | 0.000 (5.1) | 0.000 (12.6) | 0.000 (5.0) | 0.000 (5.0) | 0.000 (8.5) | 0.000 (12.6) | 0.000 (12.6) | 0.000 (5.0) | 0.000 (7.0) | 0.000 (10.3) | 0.000 (12.6) | 0.000 (12.6) | 0.000 (12.6) | 0.000 (12.6) | 0.000 (9.5) | 0.000 (5.0) | 0.000 (12.6) | 0.000 (5.0) | 0.000 (12.6) |

**Points on a square edge, and points whose square has no data: the other squares nearby**

From `mars_validation.json` → `sites[].other_squares_at_the_point` and `sites[].neighbours_with_data`. These squares are not used in section 8.

| Site | Square used | Its highest full over the 57 sites | Other square | Ranked | Bare | Its highest full |
|---|---|---|---|---|---|---|
| Atacama near Yungay | `m_-24.25_-69.75` | 0.681 | `m_-24.25_-70.25` | yes | 1.00 | 0.677 |
| Mojave | `m_35.25_-115.25` | 0.363 | `m_34.75_-115.75` | yes | 0.87 | 0.523 |
| Mojave | `m_35.25_-115.25` | 0.363 | `m_34.75_-115.25` | yes | 0.82 | 0.499 |
| Mojave | `m_35.25_-115.25` | 0.363 | `m_35.25_-115.75` | yes | 0.55 | 0.467 |
| Qaidam Basin | `m_38.25_92.75` | 0.736 | `m_37.75_92.25` | yes | 1.00 | 0.725 |
| Qaidam Basin | `m_38.25_92.75` | 0.736 | `m_37.75_92.75` | yes | 1.00 | 0.725 |
| Qaidam Basin | `m_38.25_92.75` | 0.736 | `m_38.25_92.25` | yes | 1.00 | 0.736 |
| Dhofar in Oman | `m_18.75_54.75` | 0.378 | `m_18.25_54.25` | yes | 1.00 | 0.399 |
| Dhofar in Oman | `m_18.75_54.75` | 0.378 | `m_18.25_54.75` | yes | 1.00 | 0.402 |
| Dhofar in Oman | `m_18.75_54.75` | 0.378 | `m_18.75_54.25` | yes | 1.00 | 0.374 |
| Lanzarote | `m_29.25_-13.75` | n/a | `m_28.75_-13.75` | yes | 0.81 | 0.528 |
| Svalbard | `m_78.25_16.25` | 0.000 | `m_77.75_15.75` | yes | 0.51 | 0.000 |
| Svalbard | `m_78.25_16.25` | 0.000 | `m_77.75_16.25` | yes | 0.47 | 0.000 |
| Svalbard | `m_78.25_16.25` | 0.000 | `m_78.25_15.75` | yes | 0.47 | 0.000 |

No climate square holds these points, so their scores are unknown: Lanzarote.

These squares have under 15 % bare ground and are not ranked: Rio Tinto, Pilbara. They are scored all the same.

On environment these known sites still score 0, because one factor is 0: Iceland's highlands (dry 0), Svalbard (dry 0).

## 8. A test of the ranking

Known squares: 67 distinct squares of the 71 Mars entries. Of them, 38 have at least 15 % bare ground.
Controls: 2,000 squares drawn by the sha1 of their id from all squares with land. A second set of 2,000 is drawn the same way from the ranked squares only.
The number is the area under the curve (AUC). It is the chance that a known square outranks a control, ties counting one half. 0.5 is chance; 1 means every known square wins.

**Against all squares with land** (`mars_validation.json` → `test_against_all_land.<site>.<score>.auc`)

| Site | landscape | environment | full | bare | dry | cold | terrain | sun |
|---|---|---|---|---|---|---|---|---|
| Jezero | 0.821 | 0.678 | 0.648 | 0.803 | 0.537 | 0.394 | 0.679 | 0.641 |
| Gale | 0.825 | 0.678 | 0.651 | 0.803 | 0.537 | 0.394 | 0.724 | 0.605 |
| Phoenix | 0.802 | 0.677 | 0.671 | 0.803 | 0.537 | 0.394 | 0.425 | 0.406 |
| Arcadia Planitia | 0.795 | 0.678 | 0.672 | 0.803 | 0.537 | 0.394 | 0.301 | 0.679 |
| Deuteronilus Mensae | 0.812 | 0.678 | 0.680 | 0.803 | 0.537 | 0.394 | 0.612 | 0.678 |
| Viking 1 | 0.792 | 0.678 | 0.644 | 0.803 | 0.537 | 0.394 | 0.301 | 0.646 |
| Viking 2 | 0.791 | 0.678 | 0.672 | 0.803 | 0.537 | 0.394 | 0.317 | 0.609 |
| Pathfinder | 0.795 | 0.677 | 0.647 | 0.803 | 0.537 | 0.394 | 0.307 | 0.645 |
| Spirit | 0.800 | 0.677 | 0.644 | 0.803 | 0.537 | 0.394 | 0.378 | 0.621 |
| Opportunity | 0.795 | 0.678 | 0.647 | 0.803 | 0.537 | 0.394 | 0.327 | 0.602 |
| InSight | 0.794 | 0.678 | 0.644 | 0.803 | 0.537 | 0.394 | 0.299 | 0.605 |
| Phlegra Montes | 0.817 | 0.678 | 0.682 | 0.803 | 0.537 | 0.394 | 0.704 | 0.683 |
| AP-1 (Arcadia Planitia) | 0.784 | 0.678 | 0.669 | 0.803 | 0.537 | 0.394 | 0.285 | 0.676 |
| AP-9 (Arcadia Planitia) | 0.787 | 0.678 | 0.670 | 0.803 | 0.537 | 0.394 | 0.290 | 0.675 |
| EM-16 (Erebus Montes) | 0.798 | 0.678 | 0.674 | 0.803 | 0.537 | 0.394 | 0.330 | 0.676 |
| AP-8 (Arcadia Planitia) | 0.789 | 0.678 | 0.670 | 0.803 | 0.537 | 0.394 | 0.287 | 0.672 |
| EM-15 (Erebus Montes) | 0.797 | 0.678 | 0.673 | 0.803 | 0.537 | 0.394 | 0.312 | 0.676 |
| PM-7 (Phlegra Montes) | 0.811 | 0.678 | 0.680 | 0.803 | 0.537 | 0.394 | 0.597 | 0.684 |
| Phlegra Dorsa, Arcadia Planitia | 0.796 | 0.678 | 0.673 | 0.803 | 0.537 | 0.394 | 0.323 | 0.679 |
| Southern Nectaris Fossae | 0.814 | 0.678 | 0.655 | 0.803 | 0.537 | 0.394 | 0.597 | 0.660 |
| Valles Marineris mouth (southern Acidalia Planitia, as named in the abstract) | 0.798 | 0.677 | 0.648 | 0.803 | 0.537 | 0.394 | 0.361 | 0.645 |
| East Melas Chasma | 0.824 | 0.678 | 0.650 | 0.803 | 0.537 | 0.394 | 0.710 | 0.617 |
| Mawrth Vallis | 0.820 | 0.678 | 0.648 | 0.803 | 0.537 | 0.394 | 0.674 | 0.647 |
| Nili Fossae | 0.825 | 0.677 | 0.652 | 0.803 | 0.537 | 0.394 | 0.706 | 0.647 |
| Acheron Fossae | 0.811 | 0.678 | 0.680 | 0.803 | 0.537 | 0.394 | 0.577 | 0.676 |
| Hebrus Valles | 0.797 | 0.678 | 0.647 | 0.803 | 0.537 | 0.394 | 0.322 | 0.645 |
| Newton crater | 0.818 | 0.678 | 0.683 | 0.803 | 0.537 | 0.394 | 0.637 | 0.673 |
| Zephyria Planum hills ('Sea Urchins') | 0.795 | 0.678 | 0.647 | 0.803 | 0.537 | 0.394 | 0.318 | 0.603 |
| Cerberus (west of Zunil crater) | 0.813 | 0.678 | 0.647 | 0.803 | 0.537 | 0.394 | 0.649 | 0.616 |
| Amazonis Planitia mid-latitude ice | 0.783 | 0.678 | 0.668 | 0.803 | 0.537 | 0.394 | 0.280 | 0.627 |
| Western Noachis Terra chloride deposits | 0.806 | 0.677 | 0.678 | 0.803 | 0.537 | 0.394 | 0.497 | 0.683 |
| South of Valles Marineris (equatorial site) | 0.810 | 0.677 | 0.652 | 0.803 | 0.537 | 0.394 | 0.550 | 0.645 |
| McLaughlin crater | 0.822 | 0.677 | 0.651 | 0.803 | 0.537 | 0.394 | 0.710 | 0.647 |
| South of Firsoff crater, Arabia Terra | 0.805 | 0.678 | 0.650 | 0.803 | 0.537 | 0.394 | 0.469 | 0.594 |
| Ismenius Cavus | 0.816 | 0.678 | 0.683 | 0.803 | 0.537 | 0.394 | 0.659 | 0.682 |
| Hale crater | 0.825 | 0.678 | 0.685 | 0.803 | 0.537 | 0.394 | 0.718 | 0.683 |
| Copernicus crater | 0.800 | 0.678 | 0.676 | 0.803 | 0.537 | 0.394 | 0.404 | 0.588 |
| Huygens crater | 0.802 | 0.678 | 0.646 | 0.803 | 0.537 | 0.394 | 0.427 | 0.620 |
| Mesopotamia (east rim of Hellas) | 0.805 | 0.678 | 0.678 | 0.803 | 0.537 | 0.394 | 0.482 | 0.683 |
| Western Coprates Chasma | 0.821 | 0.678 | 0.649 | 0.803 | 0.537 | 0.394 | 0.719 | 0.617 |
| Hellas Rim | 0.814 | 0.678 | 0.681 | 0.803 | 0.537 | 0.394 | 0.641 | 0.678 |
| Eastern rim of Hellas impact basin | 0.811 | 0.678 | 0.679 | 0.803 | 0.537 | 0.394 | 0.606 | 0.676 |
| Columbus crater | 0.818 | 0.678 | 0.655 | 0.803 | 0.537 | 0.394 | 0.700 | 0.661 |
| South-west Sinus Meridiani | 0.798 | 0.678 | 0.647 | 0.803 | 0.537 | 0.394 | 0.372 | 0.605 |
| Apollinaris Sulci | 0.817 | 0.677 | 0.648 | 0.803 | 0.537 | 0.394 | 0.665 | 0.618 |
| Deuteronilus Mensae (debris apron zone) | 0.810 | 0.678 | 0.679 | 0.803 | 0.537 | 0.394 | 0.572 | 0.671 |
| Ausonia Cavus | 0.807 | 0.677 | 0.681 | 0.803 | 0.537 | 0.394 | 0.521 | 0.677 |
| Kasei Valles | 0.818 | 0.678 | 0.646 | 0.803 | 0.537 | 0.394 | 0.682 | 0.648 |
| Gusev crater - Apollinaris Sulci | 0.814 | 0.678 | 0.647 | 0.803 | 0.537 | 0.394 | 0.662 | 0.619 |
| Aram Chaos | 0.824 | 0.678 | 0.652 | 0.803 | 0.537 | 0.394 | 0.706 | 0.606 |
| Noctis Landing | 0.827 | 0.678 | 0.651 | 0.803 | 0.537 | 0.394 | 0.725 | 0.612 |
| Hypanis (Hypanis and Sabrina deltas) | 0.807 | 0.678 | 0.647 | 0.803 | 0.537 | 0.394 | 0.518 | 0.618 |
| Hadriacus Palus and Cavi | 0.816 | 0.678 | 0.650 | 0.803 | 0.537 | 0.394 | 0.667 | 0.655 |
| Protonilus Mensae | 0.825 | 0.678 | 0.684 | 0.803 | 0.537 | 0.394 | 0.724 | 0.664 |
| Eastern outlet of Valles Marineris | 0.819 | 0.678 | 0.650 | 0.803 | 0.537 | 0.394 | 0.712 | 0.605 |
| Tempe Terra | 0.814 | 0.677 | 0.681 | 0.803 | 0.537 | 0.394 | 0.622 | 0.662 |
| Southern edge of Meridiani Planum (Endeavour crater area) | 0.805 | 0.678 | 0.648 | 0.803 | 0.537 | 0.394 | 0.476 | 0.605 |

Pairs for `full`: 67 known squares against 1,997 controls.

**Against ranked squares only (bare ≥ 0.15)** (`mars_validation.json` → `test_against_bare_squares.<site>.<score>.auc`)

| Site | landscape | environment | full | bare | dry | cold | terrain | sun |
|---|---|---|---|---|---|---|---|---|
| Jezero | 0.612 | 0.458 | 0.464 | 0.430 | 0.397 | 0.582 | 0.665 | 0.484 |
| Gale | 0.648 | 0.458 | 0.464 | 0.430 | 0.397 | 0.582 | 0.680 | 0.460 |
| Phoenix | 0.436 | 0.458 | 0.468 | 0.430 | 0.397 | 0.582 | 0.440 | 0.536 |
| Arcadia Planitia | 0.370 | 0.458 | 0.387 | 0.430 | 0.397 | 0.582 | 0.335 | 0.455 |
| Deuteronilus Mensae | 0.525 | 0.458 | 0.468 | 0.430 | 0.397 | 0.582 | 0.600 | 0.454 |
| Viking 1 | 0.359 | 0.458 | 0.383 | 0.430 | 0.397 | 0.582 | 0.328 | 0.489 |
| Viking 2 | 0.361 | 0.458 | 0.387 | 0.430 | 0.397 | 0.582 | 0.336 | 0.469 |
| Pathfinder | 0.368 | 0.458 | 0.392 | 0.430 | 0.397 | 0.582 | 0.336 | 0.485 |
| Spirit | 0.406 | 0.458 | 0.412 | 0.430 | 0.397 | 0.582 | 0.377 | 0.467 |
| Opportunity | 0.374 | 0.458 | 0.406 | 0.430 | 0.397 | 0.582 | 0.345 | 0.461 |
| InSight | 0.365 | 0.458 | 0.393 | 0.430 | 0.397 | 0.582 | 0.332 | 0.460 |
| Phlegra Montes | 0.571 | 0.458 | 0.475 | 0.430 | 0.397 | 0.582 | 0.675 | 0.478 |
| AP-1 (Arcadia Planitia) | 0.345 | 0.458 | 0.358 | 0.430 | 0.397 | 0.582 | 0.319 | 0.450 |
| AP-9 (Arcadia Planitia) | 0.351 | 0.458 | 0.365 | 0.430 | 0.397 | 0.582 | 0.323 | 0.448 |
| EM-16 (Erebus Montes) | 0.386 | 0.458 | 0.405 | 0.430 | 0.397 | 0.582 | 0.352 | 0.450 |
| AP-8 (Arcadia Planitia) | 0.354 | 0.458 | 0.366 | 0.430 | 0.397 | 0.582 | 0.326 | 0.447 |
| EM-15 (Erebus Montes) | 0.378 | 0.458 | 0.395 | 0.430 | 0.397 | 0.582 | 0.342 | 0.451 |
| PM-7 (Phlegra Montes) | 0.523 | 0.458 | 0.464 | 0.430 | 0.397 | 0.582 | 0.594 | 0.472 |
| Phlegra Dorsa, Arcadia Planitia | 0.378 | 0.458 | 0.397 | 0.430 | 0.397 | 0.582 | 0.339 | 0.455 |
| Southern Nectaris Fossae | 0.544 | 0.458 | 0.440 | 0.430 | 0.397 | 0.582 | 0.602 | 0.478 |
| Valles Marineris mouth (southern Acidalia Planitia, as named in the abstract) | 0.392 | 0.458 | 0.406 | 0.430 | 0.397 | 0.582 | 0.368 | 0.486 |
| East Melas Chasma | 0.632 | 0.458 | 0.464 | 0.430 | 0.397 | 0.582 | 0.671 | 0.466 |
| Mawrth Vallis | 0.602 | 0.458 | 0.451 | 0.430 | 0.397 | 0.582 | 0.660 | 0.487 |
| Nili Fossae | 0.639 | 0.458 | 0.463 | 0.430 | 0.397 | 0.582 | 0.675 | 0.489 |
| Acheron Fossae | 0.514 | 0.458 | 0.467 | 0.430 | 0.397 | 0.582 | 0.560 | 0.450 |
| Hebrus Valles | 0.383 | 0.458 | 0.398 | 0.430 | 0.397 | 0.582 | 0.348 | 0.486 |
| Newton crater | 0.597 | 0.458 | 0.503 | 0.430 | 0.397 | 0.582 | 0.638 | 0.447 |
| Zephyria Planum hills ('Sea Urchins') | 0.370 | 0.458 | 0.406 | 0.430 | 0.397 | 0.582 | 0.339 | 0.461 |
| Cerberus (west of Zunil crater) | 0.539 | 0.458 | 0.431 | 0.430 | 0.397 | 0.582 | 0.641 | 0.465 |
| Amazonis Planitia mid-latitude ice | 0.342 | 0.458 | 0.354 | 0.430 | 0.397 | 0.582 | 0.316 | 0.459 |
| Western Noachis Terra chloride deposits | 0.476 | 0.458 | 0.452 | 0.430 | 0.397 | 0.582 | 0.505 | 0.468 |
| South of Valles Marineris (equatorial site) | 0.513 | 0.458 | 0.443 | 0.430 | 0.397 | 0.582 | 0.559 | 0.486 |
| McLaughlin crater | 0.618 | 0.458 | 0.454 | 0.430 | 0.397 | 0.582 | 0.670 | 0.489 |
| South of Firsoff crater, Arabia Terra | 0.460 | 0.458 | 0.437 | 0.430 | 0.397 | 0.582 | 0.479 | 0.461 |
| Ismenius Cavus | 0.571 | 0.458 | 0.479 | 0.430 | 0.397 | 0.582 | 0.649 | 0.484 |
| Hale crater | 0.648 | 0.458 | 0.513 | 0.430 | 0.397 | 0.582 | 0.677 | 0.477 |
| Copernicus crater | 0.420 | 0.458 | 0.438 | 0.430 | 0.397 | 0.582 | 0.418 | 0.479 |
| Huygens crater | 0.435 | 0.458 | 0.423 | 0.430 | 0.397 | 0.582 | 0.439 | 0.464 |
| Mesopotamia (east rim of Hellas) | 0.471 | 0.458 | 0.448 | 0.430 | 0.397 | 0.582 | 0.495 | 0.477 |
| Western Coprates Chasma | 0.613 | 0.458 | 0.457 | 0.430 | 0.397 | 0.582 | 0.683 | 0.466 |
| Hellas Rim | 0.544 | 0.458 | 0.474 | 0.430 | 0.397 | 0.582 | 0.626 | 0.454 |
| Eastern rim of Hellas impact basin | 0.521 | 0.458 | 0.466 | 0.430 | 0.397 | 0.582 | 0.586 | 0.450 |
| Columbus crater | 0.581 | 0.458 | 0.436 | 0.430 | 0.397 | 0.582 | 0.675 | 0.479 |
| South-west Sinus Meridiani | 0.401 | 0.458 | 0.417 | 0.430 | 0.397 | 0.582 | 0.384 | 0.461 |
| Apollinaris Sulci | 0.575 | 0.458 | 0.452 | 0.430 | 0.397 | 0.582 | 0.652 | 0.464 |
| Deuteronilus Mensae (debris apron zone) | 0.508 | 0.458 | 0.466 | 0.430 | 0.397 | 0.582 | 0.568 | 0.447 |
| Ausonia Cavus | 0.492 | 0.458 | 0.452 | 0.430 | 0.397 | 0.582 | 0.530 | 0.487 |
| Kasei Valles | 0.583 | 0.458 | 0.442 | 0.430 | 0.397 | 0.582 | 0.665 | 0.485 |
| Gusev crater - Apollinaris Sulci | 0.543 | 0.458 | 0.439 | 0.430 | 0.397 | 0.582 | 0.635 | 0.464 |
| Aram Chaos | 0.631 | 0.458 | 0.467 | 0.430 | 0.397 | 0.582 | 0.675 | 0.461 |
| Noctis Landing | 0.663 | 0.458 | 0.474 | 0.430 | 0.397 | 0.582 | 0.675 | 0.463 |
| Hypanis (Hypanis and Sabrina deltas) | 0.490 | 0.458 | 0.439 | 0.430 | 0.397 | 0.582 | 0.528 | 0.466 |
| Hadriacus Palus and Cavi | 0.568 | 0.458 | 0.437 | 0.430 | 0.397 | 0.582 | 0.651 | 0.481 |
| Protonilus Mensae | 0.650 | 0.458 | 0.516 | 0.430 | 0.397 | 0.582 | 0.680 | 0.448 |
| Eastern outlet of Valles Marineris | 0.595 | 0.458 | 0.452 | 0.430 | 0.397 | 0.582 | 0.682 | 0.460 |
| Tempe Terra | 0.550 | 0.458 | 0.484 | 0.430 | 0.397 | 0.582 | 0.620 | 0.449 |
| Southern edge of Meridiani Planum (Endeavour crater area) | 0.465 | 0.458 | 0.434 | 0.430 | 0.397 | 0.582 | 0.486 | 0.460 |

Pairs for `full`: 38 known squares against 1,985 controls.

Against all land, known squares outrank controls on landscape in 0.78 to 0.83 of pairs. Bare ground alone gives 0.80.
On environment the figure is 0.68, and on all five factors 0.64 to 0.69.
Environment puts the squares in the same order for every site, because only the scale of cold changes.
Cold alone gives 0.39, below chance. The controls include the Antarctic ice sheet, which is colder than any known site.
Against bare squares only, the 38 bare known squares win 0.35 to 0.52 of pairs on all factors and 0.34 to 0.66 on landscape.
So among bare ground, the scores do not pick out the places scientists chose.
The bare known squares are less bare (AUC 0.43) and wetter (AUC 0.40) than a typical bare square.

**What moving the cold zero point from +15 °C to +30 °C did** (`mars_validation.json` → `previous_cold_zero`)

Against all land, on environment, known squares won 0.570 of pairs with the zero point at +15 °C. At +30 °C they win 0.677 to 0.678, so agreement with the known sites is better.
Against all land, on full, known squares won 0.538 to 0.575 of pairs with the zero point at +15 °C. At +30 °C they win 0.644 to 0.685, so agreement with the known sites is better.
Against bare squares only, on environment, known squares won 0.486 of pairs with the zero point at +15 °C. At +30 °C they win 0.458, so agreement with the known sites is worse.
Against bare squares only, on full, known squares won 0.451 to 0.493 of pairs with the zero point at +15 °C. At +30 °C they win 0.354 to 0.516, so agreement with the known sites is mixed: better for 4 sites, worse for 52.
Landscape does not use cold, so its figures are the same as before.

What it does not show: that a top square is a better analog than a known site. Known sites were picked partly for being bare and dry, so the test against all land is partly circular.
It also says nothing about chemistry, minerals, ice or life, which these factors do not measure. The known list comes from encyclopedia and project pages, and many of its points are estimated.

## 9. Limits

- Squares are half a degree, about 55 km. A small site such as a crater or a valley fills a fraction of one.
- The slope baseline is the same on both planets: heights every 1.85 km, slopes across about 3.7 km, which is two pixels. So slopes are much gentler than at rover scale.
- East-west spacing shrinks with latitude, so high-latitude squares mix a shorter baseline into their slopes.
- Slopes alone saturate: they reach the full terrain score in thousands of squares.
- Earth temperature, precipitation and pressure are NASA POWER (MERRA-2) values for a grid box.
- The model gives the 15 ranked squares labelled McMurdo Dry Valleys 56 to 130 mm a year. Measured snowfall there is usually put at under about 50 mm of water a year (from memory, not checked). So the model is likely too wet in polar deserts.
- Model precipitation decides some known sites. The model gives Svalbard 740 mm and Iceland's highlands 992 mm a year, so dry is 0 there.
- MARS-CLIMATE judged the Iceland figure too wet against general knowledge; the Svalbard figure was not checked.
- A square is placed by the analog list's point, and many of those points are estimated or sit on a square edge.
- POWER names 2001 to 2025, but its values most likely fit 2001 to 2020 (see `mars_climate.json` → `meta.climate_period_caution`).
- Bare ground is ESA WorldCover 2021 north of 60 S. In Antarctica it is the project's rock-outcrop layer, a lower bound.
- Bare ground is WorldCover class 60, bare or sparse vegetation. Ground mapped as moss and lichen does not count, so polar deserts read as less bare. Haughton crater's square gets 0.18.
- Lakes inside the land outline count as land, and their slopes are lake-bed slopes (`mars_terrain.json` notes).
- The Mars yearly means are model values; the model understates daily extremes, by its makers' own warning.
- The cold score uses the yearly mean only. Daily and seasonal swings on Mars are far larger than on Earth.
- The month score uses the noon Sun on the 15th of each month and the monthly means.
- Cloud cover is not used: `cloud_pct` is null for every square in this pass.
- Region names are rough rectangles in the script, not a map.
- Nothing here was checked in the field.

## 10. Files

| File | What |
|---|---|
| `data/derived/mars_sites.json` | One card per Mars site: name, kind, why, sources, Sun, landscape, climate, cannot-match list, best places |
| `data/derived/mars_cells.json` | Every ranked square with its scores per site, best months and shortfalls; the best places |
| `data/derived/mars_validation.json` | The known analog sites per site and goal, and the AUC test |
| `data/derived/MARS-RESULTS.md` | This summary |

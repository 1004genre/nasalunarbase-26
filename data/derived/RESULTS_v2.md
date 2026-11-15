# Earth Twin Finder: results of the grazing-hours method

Written Saturday 14 November 2026, 14:49 Pacific by the last step of the build (FINAL), from the files in `data/derived/` as they stood after the whole chain was run again. Every number below was read from those files or computed from them in that run; each table names the file and field it comes from. Unknown values are written `n/a`, never 0.

## How to read this

- **Grazing hour**: an hour with the Sun's apparent centre above the horizon and at or below a lunar site's highest Sun. The four lunar targets and their limits (`grazing_cells.json` → `meta.targets[].limit_deg`): Shackleton-de Gerlache connecting ridge 2.08°; Malapert Massif 5.55°; Mons Mouton plateau 6.11°; Nobile Rim 2 7.59°.
- **Long window**: a ten-day bin whose median longest unbroken spell in the band is at least 2 h over a flat horizon (`meta.stretch_min_h`). "Long-window hours" are the hours in those bins only.
- Three versions are kept apart: **flat** (Sun geometry only), **snow-free** (times the odds that the ground is snow-free in that ten-day bin, NOAA IMS 4 km maps of October 2015 to September 2025), **open** (snow-free, and the terrain does not hide the Sun; only for the cells that have a computed horizon).
- Winter half = 28 September to 31 March; summer half = 1 April to 27 September (`meta.winter_bins_north`, `meta.summer_bins_north`). Southern rock season = 27 November to 1 March (`meta.summer_bins_south`).
- A cell is about 11 km across. Bare ground is the share of the cell's land that is bare (`bare`).

### What was searched

| What | Count | Source |
|---|---|---|
| Cell records | 16,184 | `grazing_cells.json` → `cells` |
| Northern cells in the search (bare ≥ 0.15, 59 to 84 N) | 14,933 | `gridded` true, `hemisphere` N |
| of them with measured snow odds | 14,863 | `snow.status` = measured |
| of them doubtful / no snow data (listed, not ranked) | 36 / 34 | `snow.status` |
| Southern cells (bare ≥ 0.15, land share ≥ 0.2, 59 to 87.5 S); snow not measured | 1,241 | `gridded` true, `hemisphere` S |
| Named-site cells outside those screens (reported apart) | 10 | `gridded` false |
| Candidate cells that got a terrain horizon and slope statistics | 1,690 (north 1,241, south 449) | `candidates.json` |
| of them with a horizon / skipped at the antimeridian | 1,682 / 8 | `horizon_cells.json` |
| of them with slope statistics | 1,690 | `terrain_cells.json` → `overlap` |
| Ranked cells, north / south | 1,085 / 334 | `cells_scored.json` → `ranked`, `ranking` |

## (a) Where on Earth the Sun grazes the horizon for hours

Pure Sun geometry: flat horizon, standard refraction, no snow, no terrain. Hours per year.

| Latitude | Connecting ridge (≤ 2.08°): all hours / long-window hours / longest spell, h | Malapert (≤ 5.55°): all hours / long-window hours / longest spell, h | Mons Mouton (≤ 6.11°): all hours / long-window hours / longest spell, h | Nobile Rim 2 (≤ 7.59°): all hours / long-window hours / longest spell, h |
|---|---|---|---|---|
| 0 N | 120 / 0 / 0.17 | 303 / 0 / 0.43 | 332 / 0 / 0.47 | 409 / 0 / 0.57 |
| 30 N | 140 / 0 / 0.23 | 356 / 0 / 0.53 | 390 / 0 / 0.60 | 480 / 0 / 0.73 |
| 45 N | 178 / 0 / 0.27 | 452 / 0 / 0.73 | 496 / 0 / 0.80 | 611 / 0 / 1.00 |
| 50 N | 201 / 0 / 0.30 | 511 / 0 / 0.83 | 560 / 0 / 0.93 | 692 / 0 / 1.17 |
| 55 N | 234 / 0 / 0.38 | 599 / 0 / 1.07 | 658 / 0 / 1.17 | 816 / 0 / 1.53 |
| 57.5 N | 258 / 0 / 0.47 | 664 / 0 / 1.27 | 731 / 0 / 1.43 | 914 / 0 / 1.97 |
| 59 N | 276 / 0 / 0.50 | 716 / 0 / 1.50 | 790 / 0 / 1.70 | 1,009 / 210 / 2.63 |
| 60 N | 291 / 0 / 0.53 | 760 / 0 / 1.73 | 844 / 61 / 2.03 | 1,089 / 291 / 5.92 |
| 62.5 N | 341 / 0 / 0.73 | 931 / 220 / 5.15 | 1,013 / 273 / 5.37 | 1,214 / 391 / 5.92 |
| 65 N | 461 / 50 / 3.40 | 1,041 / 316 / 5.12 | 1,120 / 409 / 5.33 | 1,316 / 663 / 6.02 |
| 66.5 N | 549 / 150 / 3.37 | 1,122 / 488 / 5.73 | 1,201 / 549 / 6.02 | 1,400 / 784 / 6.75 |
| 67.5 N | 518 / 165 / 3.27 | 1,107 / 556 / 5.73 | 1,188 / 585 / 6.03 | 1,391 / 831 / 6.78 |
| 70 N | 398 / 80 / 3.17 | 1,078 / 553 / 5.87 | 1,167 / 678 / 6.20 | 1,388 / 922 / 7.02 |
| 72.5 N | 355 / 61 / 3.08 | 948 / 476 / 6.08 | 1,073 / 647 / 6.43 | 1,353 / 1,073 / 7.33 |
| 75 N | 330 / 72 / 3.23 | 860 / 511 / 6.53 | 949 / 684 / 6.92 | 1,200 / 1,185 / 7.87 |
| 80 N | 305 / 91 / 3.30 | 782 / 773 / 7.65 | 861 / 845 / 8.18 | 1,069 / 1,045 / 9.45 |
| 85 N | 293 / 221 / 3.90 | 748 / 714 / 10.90 | 821 / 778 / 11.78 | 1,018 / 986 / 14.13 |
| 89.5 N | 289 / 220 / 19.52 | 740 / 614 / 24.00 | 813 / 732 / 24.00 | 1,005 / 940 / 24.00 |
| 59 S | 277 / 0 / 0.50 | 719 / 0 / 1.50 | 795 / 0 / 1.70 | 1,017 / 193 / 2.65 |
| 66.5 S | 548 / 160 / 3.43 | 1,118 / 530 / 5.75 | 1,197 / 595 / 6.05 | 1,394 / 827 / 6.78 |
| 70 S | 396 / 102 / 3.02 | 1,061 / 592 / 5.78 | 1,149 / 676 / 6.12 | 1,365 / 915 / 6.95 |
| 77.5 S | 315 / 64 / 3.10 | 806 / 642 / 6.90 | 886 / 868 / 7.35 | 1,103 / 1,082 / 8.43 |
| 85 S | 291 / 195 / 4.33 | 743 / 724 / 11.10 | 816 / 788 / 12.00 | 1,009 / 983 / 15.68 |

Source: `latitude_profile.json` → `profile[].targets.<target>.flat_hours`, `.long_flat_hours["2"]`, `.longest_stretch_h` (the best ten-day median of the longest daily spell).

- Grazing hours exist at every latitude, but below the latitudes in the next table they come in spells of under an hour at sunrise and sunset. At the equator the yearly total is 120 h (Connecting ridge), 303 h (Malapert), 332 h (Mons Mouton), 409 h (Nobile Rim 2), and the longest spell is 0.17 h, 0.43 h, 0.47 h, 0.57 h.
- The yearly total is largest near the polar circle: Connecting ridge 549 h at 66.5° N; Malapert 1,124 h at 67° N; Mons Mouton 1,204 h at 67° N; Nobile Rim 2 1,405 h at 67° N (4.6, 3.7, 3.6, 3.4 times the equator's total).
- Long-window hours in the northern half are largest at Connecting ridge 277 h at 86.5° N; Malapert 784 h at 78.5° N; Mons Mouton 874 h at 78° N; Nobile Rim 2 1,205 h at 74.5° N.

### Lowest latitude with spells of 1, 2 and 3 hours

| Target | 1 h spell | 2 h spell | 3 h spell | Sun under the limit all day (the old measure) |
|---|---|---|---|---|
| Shackleton-de Gerlache connecting ridge (≤ 2.08°) | 63.95 N / 63.95 S | 64.85 N / 64.85 S | 64.85 N / 64.85 S | 64.80 N / 64.80 S |
| Malapert Massif (≤ 5.55°) | 53.55 N / 53.50 S | 60.70 N / 60.70 S | 61.25 N / 61.20 S | 61.20 N / 61.20 S |
| Mons Mouton plateau (≤ 6.11°) | 51.40 N / 51.35 S | 59.90 N / 59.90 S | 60.65 N / 60.65 S | 60.60 N / 60.60 S |
| Nobile Rim 2 (≤ 7.59°) | 45.00 N / 45.00 S | 57.65 N / 57.65 S | 59.15 N / 59.15 S | 59.10 N / 59.10 S |

Source: `latitude_profile.json` → `thresholds.<target>.<N|S>.lowest_lat_with_long_window["1"|"2"|"3"]` and `.lowest_lat_with_all_day_low_sun`; found at steps of 0.05°, a spell being the median longest daily spell of a ten-day bin.

### What the search band does not cover

The search looked at land from 59 to 84 N and from 59 to 87.5 S (`twinfinder/grid.py`: `MIN_LAT`, `MAX_LAT`, `SOUTH_MIN_LAT`, `SOUTH_MAX_LAT`). Degrees of latitude between the first long window and the band edge, in each hemisphere:

| Target | 1 h spells | 2 h spells (the rule used) | 3 h spells |
|---|---|---|---|
| Connecting ridge | none (starts at 63.95) | none (starts at 64.85) | none (starts at 64.85) |
| Malapert | 5.45° (53.55 to 59) | none (starts at 60.70) | none (starts at 61.25) |
| Mons Mouton | 7.60° (51.40 to 59) | none (starts at 59.90) | none (starts at 60.65) |
| Nobile Rim 2 | 14.00° (45.00 to 59) | 1.35° (57.65 to 59) | none (starts at 59.15) |

- With the 2 h rule used for the ranking, only Nobile Rim 2 loses ground: its long windows begin at 57.65°, so a strip of 1.35° on each side of the Earth was not looked at. Flat-horizon long-window hours there: 102 h a year at 58.0 N, 152 h at 58.5 N, 210 h at 59.0 N (`profile[].targets.nobile-rim-2.long_flat_hours["2"]`).
- With a 1 h rule the belt would reach much further toward the equator (first column); none of that ground was searched.
- With a 3 h rule every target's belt starts inside the band.

## (b) The north in the winter half (28 September to 31 March)

Long-window hours on snow-free ground, flat horizon, over the 14,863 measured northern cells (695,227 km² of bare ground; 3 of the cells have unknown hours and are counted in no column).

| Target | ≥ 50 h | ≥ 100 h | ≥ 200 h | with the real horizon, among the 1,192 measured cells that have one: cells ≥ 50 / 100 / 200 h |
|---|---|---|---|---|
| Connecting ridge | 0 cells, 0 km² | 0 cells, 0 km² | 0 cells, 0 km² | 0 / 0 / 0 |
| Malapert | 74 cells, 2,850 km² | 10 cells, 617 km² | 0 cells, 0 km² | 36 / 9 / 0 |
| Mons Mouton | 105 cells, 4,428 km² | 27 cells, 1,220 km² | 0 cells, 0 km² | 44 / 23 / 0 |
| Nobile Rim 2 | 214 cells, 8,160 km² | 40 cells, 1,776 km² | 3 cells, 54 km² | 59 / 33 / 2 |

Source: `validation.json` → `big_picture_north.targets.<target>.long_snow_free_hours.winter_half.<50|100|200>.cells` and `.bare_km2`; last column `...long_open_hours_among_cells_with_a_horizon.winter_half` (those cells are the candidates, chosen mostly for their hours, so that column is not a census). The same counts were made again from `grazing_cells.json` (`targets.<target>.long_snow_free_hours_winter`, `long_open_hours_winter`, `bare_km2`) and agree.

- Share of all long-window snow-free hours × bare km² that falls in the winter half: Connecting ridge 0.4%; Malapert 1.6%; Mons Mouton 1.8%; Nobile Rim 2 2.1% (`big_picture_north.targets.<target>.calendar_hours_times_bare_km2`, winter bins over all bins).
- Regions of the cells with at least 100 winter-half hours: Connecting ridge: no cell; Malapert: Iceland 10; Mons Mouton: Iceland 27; Nobile Rim 2: Iceland 38, Novaya Zemlya 1, Svalbard 1 (`validation.json` → `regions.<target>.measured_cells_100_long_snow_free_hours_winter_half`).

The measured cell with the most winter-half hours per target:

| Target | Cell centre | Region | Bare | Winter-half hours, snow-free | the same with the real horizon | Share of the year's long-window hours with the Sun on the poleward side |
|---|---|---|---|---|---|---|
| Connecting ridge | 66.25, -15.75 | Iceland | 0.19 | 19.6 | 2.8 | 0.36 |
| Malapert | 63.85, -22.70 | Iceland | 0.68 | 135.9 | 121.3 | 0.00 |
| Mons Mouton | 63.75, -20.70 | Iceland | 0.22 | 147.3 | 141.4 | 0.00 |
| Nobile Rim 2 | 63.75, -20.70 | Iceland | 0.22 | 210.3 | 202.9 | 0.16 |

Source: `grazing_cells.json` → `targets.<target>.long_snow_free_hours_winter`, `long_open_hours_winter`, `poleward_share`. A poleward share near 0 means the low Sun stands in the south: dawn, dusk and low noon, not midnight Sun.

## (c) The north in the summer half (1 April to 27 September): the midnight-Sun side

| Target | ≥ 50 h | ≥ 100 h | ≥ 200 h | with the real horizon, among the 1,192 measured cells that have one: cells ≥ 50 / 100 / 200 h |
|---|---|---|---|---|
| Connecting ridge | 476 cells, 19,352 km² | 6 cells, 221 km² | 0 cells, 0 km² | 1 / 0 / 0 |
| Malapert | 9,605 cells, 486,114 km² | 7,324 cells, 384,204 km² | 545 cells, 20,086 km² | 791 / 509 / 17 |
| Mons Mouton | 10,048 cells, 508,309 km² | 8,207 cells, 426,432 km² | 1,562 cells, 61,519 km² | 855 / 637 / 68 |
| Nobile Rim 2 | 11,234 cells, 559,673 km² | 9,897 cells, 504,540 km² | 6,244 cells, 325,592 km² | 952 / 806 / 497 |

Source: as in (b), with `summer_half` (`long_snow_free_hours_summer`, `long_open_hours_summer` in `grazing_cells.json`).

- Connecting ridge: 99.6% of the long-window snow-free hours × bare km² fall in the summer half; the three ten-day bins with the most are 9 Aug-18 Aug (20%), 30 Jul-8 Aug (16%), 19 Aug-28 Aug (13%).
- Malapert: 98.4% of the long-window snow-free hours × bare km² fall in the summer half; the three ten-day bins with the most are 9 Aug-18 Aug (17%), 19 Aug-28 Aug (16%), 30 Jul-8 Aug (15%).
- Mons Mouton: 98.2% of the long-window snow-free hours × bare km² fall in the summer half; the three ten-day bins with the most are 9 Aug-18 Aug (16%), 19 Aug-28 Aug (15%), 30 Jul-8 Aug (15%).
- Nobile Rim 2: 97.9% of the long-window snow-free hours × bare km² fall in the summer half; the three ten-day bins with the most are 9 Aug-18 Aug (16%), 19 Aug-28 Aug (14%), 30 Jul-8 Aug (14%).

| Target | Cells with ≥ 100 summer-half hours | Regions (cells) |
|---|---|---|
| Connecting ridge | 6 | Siberia and the Russian Far East 2, Greenland 1, Arctic Canada 1, Alaska 1, Norway, Sweden or Finland 1 |
| Malapert | 7,324 | Arctic Canada 4,648, Greenland 761, Siberia and the Russian Far East 708, North-west Greenland or Ellesmere 336, Alaska 246, Svalbard 190; other regions 435 |
| Mons Mouton | 8,207 | Arctic Canada 5,088, Greenland 989, Siberia and the Russian Far East 752, North-west Greenland or Ellesmere 373, Alaska 250, Svalbard 230; other regions 525 |
| Nobile Rim 2 | 9,897 | Arctic Canada 5,961, Greenland 1,369, Siberia and the Russian Far East 858, North-west Greenland or Ellesmere 424, Svalbard 265, Novaya Zemlya 258; other regions 762 |

Source: `validation.json` → `regions.<target>.measured_cells_100_long_snow_free_hours_summer_half`.

| Target | Cells with ≥ 100 summer-half hours | Median share of long-window hours with the Sun within 90° of north | 10th to 90th percentile | Latitudes, 10th to 90th percentile |
|---|---|---|---|---|
| Connecting ridge | 6 | 0.69 | 0.67 to 0.69 | 66.8 to 67.3 N |
| Malapert | 7,324 | 0.57 | 0.52 to 0.65 | 68.0 to 80.5 N |
| Mons Mouton | 8,207 | 0.57 | 0.52 to 0.65 | 67.8 to 80.8 N |
| Nobile Rim 2 | 9,897 | 0.56 | 0.49 to 0.63 | 66.8 to 81.0 N |

Source: `grazing_cells.json` → `targets.<target>.poleward_share` (whole year, flat horizon), `long_snow_free_hours_summer`, `lat`. A share above 0.5 means most of the long-window hours come with the Sun in the northern half of the sky, around local midnight.

## (d) What real terrain takes away

A sample of 300 measured northern cells and 150 southern cells was drawn without looking at any score (`candidates.json` → `why` contains `sample`); 299 and 148 of them have a horizon. The table gives the share of long-window hours that stays once the terrain horizon is applied, over the sample cells that have any such hours.

| Target | North: cells | North: share left, 10th / 25th / median / 75th / 90th percentile | South: cells | South: share left, 10th / 25th / median / 75th / 90th percentile |
|---|---|---|---|---|
| Connecting ridge | 192 | 0.04 / 0.13 / 0.34 / 0.57 / 0.85 | 82 | 0.01 / 0.05 / 0.14 / 0.33 / 0.50 |
| Malapert | 238 | 0.15 / 0.27 / 0.54 / 0.80 / 0.91 | 133 | 0.13 / 0.23 / 0.39 / 0.55 / 0.67 |
| Mons Mouton | 245 | 0.16 / 0.29 / 0.56 / 0.81 / 0.92 | 138 | 0.16 / 0.26 / 0.43 / 0.57 / 0.69 |
| Nobile Rim 2 | 263 | 0.18 / 0.31 / 0.59 / 0.82 / 0.93 | 144 | 0.22 / 0.32 / 0.49 / 0.61 / 0.73 |

Source: `grazing_cells.json` → `targets.<target>.long_open_hours` ÷ `long_snow_free_hours` (north), `long_summer_rock_open_hours` ÷ `long_summer_rock_hours` (south), for the cells that `candidates.json` marks as `sample`.

- The lower the Sun limit, the more the terrain takes: the median northern sample cell keeps 34% (Connecting ridge), 54% (Malapert), 56% (Mons Mouton), 59% (Nobile Rim 2).
- Median terrain horizon of the northern sample: 2.43° looking north, 2.45° looking south. The 869 northern cells chosen for their hours (top lists) sit on flatter ground: 0.92° and 0.87° (`grazing_cells.json` → `horizon.north_deg`, `horizon.south_deg`, the median over the cell's land of the horizon in the due-north and due-south sectors).

Named examples (the cell that holds the site; hours are for Malapert, long windows, whole year):

| Site | Cell | Horizon north / south | Flat | Snow-free | Open | Share of snow-free hours left |
|---|---|---|---|---|---|---|
| Qaqortorsuaq anorthosite, Greenland | 66.5_-52.2 | 5.96° / 5.91° | 488.0 | 157.7 | 40.0 | 25% |
| Lofoten anorthosite (Nusfjord), Norway | 68.0_13.2 | 10.10° / 5.30° | 527.2 | 334.2 | 66.9 | 20% |
| Longyearbyen, Svalbard | 78.2_15.6 | 12.89° / 7.51° | 783.5 | 81.0 | 15.9 | 20% |
| Myrdalssandur sand plain, Iceland | 63.4_-18.6 | 0.34° / -0.12° | 258.5 | 92.2 | 91.6 | 99% |

Source: `validation.json` → `named_sites.sites[].targets.malapert.<flat|snow_free|open>.long.year` and `.horizon`.

## (e) The top sites per target

Scores: light = min(1, long-window open hours ÷ 200); "lighting" = √(light × bare); "full" = fourth root of light × terrain × rock × bare (`cells_scored.json` → `meta.full_hours`, `meta.goals`). Only measured northern cells with a horizon and bare ≥ 0.25 are ranked (1,085 cells), one site per 50 km. Cells with equal scores are ordered by their long-window open hours.

### Shackleton-de Gerlache connecting ridge (Sun at or below 2.08°)

**Lighting goal (low Sun on bare ground), top 5 of the north:**

| # | Cell centre (lat, lon) | Region | Bare | Long-window hours a year: open (flat horizon) | Score | When to go: best ten-day bins | Time of day | Known or little known |
|---|---|---|---|---|---|---|---|---|
| 1 | 68.25, -96.15 | Arctic Canada | 0.96 | 50 (52) | 0.488 | 10 Jul-19 Jul (29 h), 30 Jun-9 Jul (20 h) | 65% of the hours with the Sun in the north (around midnight) | little known |
| 2 | 68.35, -88.05 | Arctic Canada | 0.81 | 45 (50) | 0.425 | 10 Jul-19 Jul (27 h), 30 Jun-9 Jul (18 h) | 65% of the hours with the Sun in the north (around midnight) | little known |
| 3 | 67.75, -76.65 | Arctic Canada | 0.79 | 45 (53) | 0.422 | 10 Jul-19 Jul (22 h), 30 Jun-9 Jul (21 h), 10 Jun-19 Jun (2 h) | 67% of the hours with the Sun in the north (around midnight) | little known |
| 4 | 68.35, -98.55 | Arctic Canada | 0.75 | 45 (51) | 0.409 | 10 Jul-19 Jul (26 h), 30 Jun-9 Jul (19 h) | 65% of the hours with the Sun in the north (around midnight) | little known |
| 5 | 75.25, 140.75 | Siberia and the Russian Far East | 1.00 | 32 (32) | 0.401 | 9 Aug-18 Aug (32 h) | 60% of the hours with the Sun in the north (around midnight) | little known |

1 ranked cell(s) hold the top score 0.488; 0 of the 1,085 ranked cells have full light marks (≥ 200 open hours).

**Full match (light, terrain, rock, bare), north: 2 ranked cell(s) score above zero, 1 site(s):**

| # | Cell centre (lat, lon) | Region | Bare | Long-window hours a year: open (flat horizon) | Score | When to go: best ten-day bins | Time of day | Known or little known |
|---|---|---|---|---|---|---|---|---|
| 1 | 70.15, -51.15 | Greenland | 0.38 | 1 (20) | 0.158 (light 0.00, terrain 0.86, rock 0.42: Tunulik anorthosite (with Boye So)) | 20 Jul-29 Jul (0.9 h) | 62% of the hours with the Sun in the north (around midnight) | little known |

### Malapert Massif (Sun at or below 5.55°)

**Lighting goal (low Sun on bare ground), top 5 of the north:**

| # | Cell centre (lat, lon) | Region | Bare | Long-window hours a year: open (flat horizon) | Score | When to go: best ten-day bins | Time of day | Known or little known |
|---|---|---|---|---|---|---|---|---|
| 1 | 68.95, 54.45 | Kola and north-west Russia | 1.00 | 243 (243) | 1.000 | 10 Jul-19 Jul (56 h), 30 Jun-9 Jul (48 h), 20 Jul-29 Jul (46 h) | 64% of the hours with the Sun in the north (around midnight) | little known |
| 2 | 80.15, 18.30 | Svalbard | 0.99 | 203 (239) | 0.995 | 19 Aug-28 Aug (66 h), 29 Aug-7 Sep (43 h), 9 Aug-18 Aug (27 h) | 52% of the hours with the Sun in the north (around midnight) | known: Svalbard |
| 3 | 70.15, -116.85 | Arctic Canada | 0.98 | 184 (203) | 0.950 | 20 Jul-29 Jul (52 h), 10 Jul-19 Jul (47 h), 30 Jun-9 Jul (38 h) | 67% of the hours with the Sun in the north (around midnight) | little known |
| 4 | 70.25, -115.35 | Arctic Canada | 0.98 | 182 (190) | 0.946 | 20 Jul-29 Jul (53 h), 10 Jul-19 Jul (47 h), 30 Jun-9 Jul (39 h) | 67% of the hours with the Sun in the north (around midnight) | little known |
| 5 | 75.05, 141.25 | Siberia and the Russian Far East | 1.00 | 174 (174) | 0.933 | 9 Aug-18 Aug (61 h), 30 Jul-8 Aug (51 h), 19 Aug-28 Aug (40 h) | 57% of the hours with the Sun in the north (around midnight) | little known |

1 ranked cell(s) hold the top score 1.000; 20 of the 1,085 ranked cells have full light marks (≥ 200 open hours).

**Full match (light, terrain, rock, bare), north: 4 ranked cell(s) score above zero, 3 site(s):**

| # | Cell centre (lat, lon) | Region | Bare | Long-window hours a year: open (flat horizon) | Score | When to go: best ten-day bins | Time of day | Known or little known |
|---|---|---|---|---|---|---|---|---|
| 1 | 70.15, -51.15 | Greenland | 0.38 | 14 (82) | 0.307 (light 0.07, terrain 0.77, rock 0.42: Tunulik anorthosite (with Boye So)) | 20 Jul-29 Jul (5 h), 10 Jul-19 Jul (4 h), 30 Jun-9 Jul (3 h) | 67% of the hours with the Sun in the north (around midnight) | little known |
| 2 | 64.45, -52.10 | Greenland | 0.26 | 18 (22) | 0.209 (light 0.09, terrain 0.12, rock 0.67: Akia anorthosite (Godthabsfjord)) | 17 Nov-26 Nov (8 h), 27 Nov-6 Dec (4 h), 7 Dec-16 Dec (3 h) | 100% of the hours with the Sun in the south (dawn, dusk, low noon) | little known |
| 3 | 63.35, -50.30 | Greenland | 0.36 | 1 (4) | 0.189 (light 0.01, terrain 0.71, rock 0.82: Fiskenaesset anorthosite complex) | 27 Nov-6 Dec (0.5 h), 7 Dec-16 Dec (0.4 h), 17 Dec-31 Dec (0.4 h) | 100% of the hours with the Sun in the south (dawn, dusk, low noon) | little known |

### Mons Mouton plateau (Sun at or below 6.11°)

**Lighting goal (low Sun on bare ground), top 5 of the north:**

| # | Cell centre (lat, lon) | Region | Bare | Long-window hours a year: open (flat horizon) | Score | When to go: best ten-day bins | Time of day | Known or little known |
|---|---|---|---|---|---|---|---|---|
| 1 | 68.95, 54.45 | Kola and north-west Russia | 1.00 | 260 (261) | 1.000 | 10 Jul-19 Jul (59 h), 30 Jun-9 Jul (52 h), 20 Jul-29 Jul (49 h) | 64% of the hours with the Sun in the north (around midnight) | little known |
| 2 | 77.55, 22.75 | Svalbard | 1.00 | 231 (324) | 1.000 | 9 Aug-18 Aug (54 h), 19 Aug-28 Aug (36 h), 30 Jul-8 Aug (29 h) | 54% of the hours with the Sun in the north (around midnight) | known: Svalbard |
| 3 | 74.95, 141.25 | Siberia and the Russian Far East | 1.00 | 199 (201) | 0.998 | 9 Aug-18 Aug (63 h), 30 Jul-8 Aug (56 h), 19 Aug-28 Aug (42 h) | 58% of the hours with the Sun in the north (around midnight) | little known |
| 4 | 70.05, -124.35 | Arctic Canada | 0.99 | 218 (259) | 0.996 | 10 Jul-19 Jul (48 h), 30 Jun-9 Jul (43 h), 20 Jul-29 Jul (42 h) | 65% of the hours with the Sun in the north (around midnight) | little known |
| 5 | 80.15, 18.30 | Svalbard | 0.99 | 231 (268) | 0.995 | 19 Aug-28 Aug (72 h), 29 Aug-7 Sep (47 h), 9 Aug-18 Aug (38 h) | 52% of the hours with the Sun in the north (around midnight) | known: Svalbard |

2 ranked cell(s) hold the top score 1.000; 81 of the 1,085 ranked cells have full light marks (≥ 200 open hours).

**Full match (light, terrain, rock, bare), north: 4 ranked cell(s) score above zero, 3 site(s):**

| # | Cell centre (lat, lon) | Region | Bare | Long-window hours a year: open (flat horizon) | Score | When to go: best ten-day bins | Time of day | Known or little known |
|---|---|---|---|---|---|---|---|---|
| 1 | 70.15, -51.15 | Greenland | 0.38 | 22 (116) | 0.365 (light 0.11, terrain 1.00, rock 0.42: Tunulik anorthosite (with Boye So)) | 20 Jul-29 Jul (6 h), 30 Jul-8 Aug (5 h), 10 Jul-19 Jul (5 h) | 65% of the hours with the Sun in the north (around midnight) | little known |
| 2 | 64.45, -52.10 | Greenland | 0.26 | 18 (23) | 0.241 (light 0.09, terrain 0.21, rock 0.67: Akia anorthosite (Godthabsfjord)) | 17 Nov-26 Nov (9 h), 27 Nov-6 Dec (4 h), 7 Dec-16 Dec (3 h) | 100% of the hours with the Sun in the south (dawn, dusk, low noon) | little known |
| 3 | 63.35, -50.30 | Greenland | 0.36 | 2 (5) | 0.224 (light 0.01, terrain 0.90, rock 0.82: Fiskenaesset anorthosite complex) | 17 Nov-26 Nov (0.6 h), 27 Nov-6 Dec (0.5 h), 7 Dec-16 Dec (0.4 h) | 100% of the hours with the Sun in the south (dawn, dusk, low noon) | little known |

### Nobile Rim 2 (Sun at or below 7.59°)

**Lighting goal (low Sun on bare ground), top 5 of the north:**

| # | Cell centre (lat, lon) | Region | Bare | Long-window hours a year: open (flat horizon) | Score | When to go: best ten-day bins | Time of day | Known or little known |
|---|---|---|---|---|---|---|---|---|
| 1 | 74.95, 143.25 | Siberia and the Russian Far East | 1.00 | 405 (409) | 1.000 | 9 Aug-18 Aug (71 h), 30 Jul-8 Aug (67 h), 19 Aug-28 Aug (50 h) | 56% of the hours with the Sun in the north (around midnight) | little known |
| 2 | 74.95, 141.25 | Siberia and the Russian Far East | 1.00 | 401 (403) | 1.000 | 9 Aug-18 Aug (72 h), 30 Jul-8 Aug (67 h), 19 Aug-28 Aug (50 h) | 56% of the hours with the Sun in the north (around midnight) | little known |
| 3 | 75.35, 142.25 | Siberia and the Russian Far East | 1.00 | 388 (392) | 1.000 | 9 Aug-18 Aug (76 h), 30 Jul-8 Aug (65 h), 19 Aug-28 Aug (53 h) | 56% of the hours with the Sun in the north (around midnight) | little known |
| 4 | 68.95, 54.45 | Kola and north-west Russia | 1.00 | 361 (362) | 1.000 | 10 Jul-19 Jul (67 h), 30 Jun-9 Jul (61 h), 20 Jul-29 Jul (56 h) | 62% of the hours with the Sun in the north (around midnight) | little known |
| 5 | 77.55, 22.75 | Svalbard | 1.00 | 310 (404) | 1.000 | 9 Aug-18 Aug (66 h), 30 Jul-8 Aug (49 h), 19 Aug-28 Aug (47 h) | 55% of the hours with the Sun in the north (around midnight) | known: Svalbard |

45 ranked cell(s) hold the top score 1.000; 528 of the 1,085 ranked cells have full light marks (≥ 200 open hours).

**Full match (light, terrain, rock, bare), north: 7 ranked cell(s) score above zero, 4 site(s):**

| # | Cell centre (lat, lon) | Region | Bare | Long-window hours a year: open (flat horizon) | Score | When to go: best ten-day bins | Time of day | Known or little known |
|---|---|---|---|---|---|---|---|---|
| 1 | 70.15, -51.15 | Greenland | 0.38 | 31 (137) | 0.398 (light 0.16, terrain 1.00, rock 0.42: Tunulik anorthosite (with Boye So)) | 20 Jul-29 Jul (8 h), 30 Jul-8 Aug (7 h), 10 Jul-19 Jul (7 h) | 62% of the hours with the Sun in the north (around midnight) | little known |
| 2 | 64.45, -52.10 | Greenland | 0.26 | 105 (133) | 0.396 (light 0.53, terrain 0.27, rock 0.67: Akia anorthosite (Godthabsfjord)) | 30 Jun-9 Jul (31 h), 20 Jun-29 Jun (26 h), 10 Jun-19 Jun (12 h) | 73% of the hours with the Sun in the south (dawn, dusk, low noon) | little known |
| 3 | 64.35, -50.90 | Greenland | 0.27 | 15 (66) | 0.311 (light 0.07, terrain 0.67, rock 0.71: Storo anorthosite (Godthabsfjord)) | 30 Jun-9 Jul (5 h), 20 Jun-29 Jun (4 h), 10 Jun-19 Jun (3 h) | 73% of the hours with the Sun in the south (dawn, dusk, low noon) | little known |
| 4 | 63.35, -50.30 | Greenland | 0.36 | 3 (7) | 0.248 (light 0.01, terrain 0.91, rock 0.82: Fiskenaesset anorthosite complex) | 17 Nov-26 Nov (0.9 h), 7 Nov-16 Nov (0.7 h), 27 Nov-6 Dec (0.5 h) | 100% of the hours with the Sun in the south (dawn, dusk, low noon) | little known |

Source: `cells_scored.json` → `cells[].targets.<target>.goals.lighting`, `.goals.full`, `.long_open_hours`, `.long_snow_free_hours`, `.top_bins`, `.poleward_share`, `.light`, `.terrain`, `.rock`; `cells[].known`, `.known_region`, `.little_known`. The same tables, ten rows each, are in `ranking.txt`; all 32 north and south tables there were rebuilt here from `cells_scored.json` and 32 agree row for row.

What decides the tables, and how firm they are:

- The full-match goal needs a listed anorthosite body: 17 of the 1,085 ranked northern cells have a rock score above 0 (`cells[].rock.score`), so those tables are short. The highest full-match score is 0.40; the factor scores are in the tables.

| Target (lighting, north) | Sites in the top list | kept: full marks at 100 h | kept: full marks at 400 h | kept: stretch minimum 1 h | kept: stretch minimum 3 h | kept: snow land pixels >= 4 | kept: snow land pixels >= 7 | kept: flat horizon instead of real | kept: bare screen 0.15 | kept: bare screen 0.35 |
|---|---|---|---|---|---|---|---|---|---|---|
| Connecting ridge | 10 | 10 | 10 | 5 | 5 | 7 | 6 | 2 | 10 | 10 |
| Malapert | 10 | 2 | 10 | 2 | 7 | 7 | 3 | 8 | 10 | 10 |
| Mons Mouton | 10 | 4 | 8 | 4 | 6 | 7 | 7 | 6 | 10 | 10 |
| Nobile Rim 2 | 10 | 10 | 5 | 10 | 3 | 7 | 6 | 8 | 10 | 10 |

Source: `validation.json` → `stability.north.<target>.lighting`: how many of the top-10 sites still have a site within 50 km when one choice is changed. The check can only draw on the candidate cells.

| Target | Measured cells with bare ≥ 0.25 that already have 200 long-window snow-free hours over a flat horizon | of them with a horizon candidate record |
|---|---|---|
| Connecting ridge | 0 | 0 |
| Malapert | 384 | 126 |
| Mons Mouton | 1,206 | 309 |
| Nobile Rim 2 | 4,962 | 859 |

Source: `validation.json` → `regions.<target>.measured_cells_with_full_flat_light_and_enough_bare`. The ranking can only choose among cells that have a horizon; for the three higher targets most cells that would earn full light marks over a flat horizon were never given one, so other cells may be as good as those listed.

## (f) The named sites

Each named place is reported on the cell that holds it, whatever the screens say, and is not in any count above. Hours are long-window hours a year: flat / snow-free / open. Horizons are for the cell's 10 km square, not the site's exact point.

| Site (north) | Cell | Bare | Snow odds | Horizon N / S | Connecting ridge | Malapert | Mons Mouton | Nobile Rim 2 | Rock match |
|---|---|---|---|---|---|---|---|---|---|
| Qaqortorsuaq anorthosite, Greenland | 66.5_-52.2 | 0.12 | measured, outside the screen | 6.0° / 5.9° | 180 / 80 / 15 | 488 / 158 / 40 | 550 / 207 / 55 | 785 / 293 / 88 | 0.74 |
| Fiskenaesset anorthosite, Greenland | 63.2_-50.0 | 0.26 | measured | 6.0° / 6.2° | 0 / 0 / 0 | 260 / 0 / 0 | 312 / 0 / 0 | 427 / 0 / 0 | 0.82 |
| Lofoten anorthosite (Nusfjord), Norway | 68.0_13.2 | 0.01 | doubtful, outside the screen | 10.1° / 5.3° | 111 / 80 / 9 | 527 / 334 / 67 | 638 / 409 / 87 | 852 / 521 / 124 | 0.12 |
| Bergen Arcs anorthosite, Norway | 60.5_5.2 | 0.00 | measured, outside the screen | 3.3° / 3.2° | 0 / 0 / 0 | 0 / 0 / 0 | 116 / 66 / 30 | 300 / 167 / 83 | 0.50 |
| Bear Island, Norway | 74.4_19.0 | 0.62 | doubtful | -0.1° / 3.3° | 53 / 12 / 2 | 527 / 191 / 127 | 629 / 243 / 169 | 1,207 / 448 / 328 | 0.00 |
| Jan Mayen, Norway | 70.9_-8.7 | 0.53 | doubtful | 4.9° / -0.1° | 107 / 32 / 12 | 588 / 206 / 81 | 724 / 233 / 97 | 1,028 / 340 / 150 | 0.00 |
| Reykjanes, Iceland | 63.8_-22.6 | 0.00 | measured, outside the screen | 0.7° / -0.1° | 0 / 0 / 0 | 295 / 135 / 117 | 306 / 142 / 124 | 503 / 286 / 243 | 0.00 |
| Skeidararsandur, Iceland | 63.9_-17.6 | 0.74 | measured | 3.7° / -0.2° | 0 / 0 / 0 | 294 / 84 / 76 | 305 / 88 / 81 | 502 / 206 / 144 | 0.00 |
| Myrdalssandur sand plain, Iceland | 63.4_-18.6 | 0.90 | measured | 0.3° / -0.1° | 0 / 0 / 0 | 258 / 92 / 92 | 311 / 127 / 126 | 426 / 187 / 185 | 0.00 |
| Haughton crater, Devon Island, Canada | 75.3_-90.0 | 0.53 | measured | 0.8° / 1.8° | 83 / 31 / 13 | 524 / 150 / 100 | 677 / 188 / 134 | 1,178 / 328 / 243 | 0.00 |
| Longyearbyen, Svalbard | 78.2_15.6 | 0.48 | measured | 12.9° / 7.5° | 62 / 14 / 1 | 784 / 81 / 16 | 874 / 93 / 20 | 1,071 / 118 / 29 | 0.00 |
| Kangerlussuaq, Greenland | 67.0_-50.7 | 0.07 | measured, outside the screen | 7.0° / 5.0° | 176 / 103 / 5 | 502 / 230 / 32 | 610 / 266 / 44 | 849 / 359 / 82 | 0.00 |

Source: `validation.json` → `named_sites.sites[]`: `.cell`, `.bare`, `.snow.status`, `.gridded`, `.horizon`, `.targets.<target>.<flat|snow_free|open>.long.year`, `.rock.score`.

- Qaqortorsuaq (the simulant mine): its cell has 76 all-day low-Sun days for Malapert but 0.0 usable days, because the snow odds are 0 on those days; its long-window snow-free hours (157.7 h) are all in the summer half (winter half 0.0 h), and the terrain leaves 40.0 h (`named_sites.sites[].targets.malapert.all_day_days`, `.usable_days`, `.snow_free.long`, `.open.long`).

### Haughton crater, Devon Island, in July

A NASA-funded rover test used the 24-hour Sun at Haughton crater in July 2001; the hours below are what this method gives for the same place and month. Cell 75.3_-90.0; horizon 0.77° north, 1.79° south; snow-free odds in the three ten-day bins 30 Jun-9 Jul, 10 Jul-19 Jul, 20 Jul-29 Jul: 0.45, 0.88, 1.00.

| Target | Flat hours in the three bins | July flat | July snow-free | July open | Median longest spell in each bin, h |
|---|---|---|---|---|---|
| Connecting ridge | 0.0 / 0.0 / 0.0 | 0.0 | 0.0 | 0.0 | 0.00 / 0.00 / 0.00 |
| Malapert | 0.0 / 0.0 / 15.3 | 15.3 | 15.3 | 13.2 | 0.00 / 0.00 / 1.92 |
| Mons Mouton | 0.0 / 0.0 / 25.9 | 25.9 | 25.9 | 22.8 | 0.00 / 0.00 / 2.93 |
| Nobile Rim 2 | 0.0 / 19.8 / 45.8 | 65.5 | 63.2 | 57.1 | 0.00 / 2.33 / 4.70 |

Source: `validation.json` → `haughton_july.targets.<target>.flat_hours`, `.flat_hours_july`, `.snow_free_hours_july`, `.open_hours_july`, `.median_longest_stretch_h`; `haughton_july.snow_free_odds`.

- At 75.4 N the July Sun stays above the limits for most of the month. Flat-horizon hours in the band in July: 0.0 h (Connecting ridge; none in July), 15.3 h (Malapert; first in the bin 20 Jul-29 Jul), 25.9 h (Mons Mouton; first in the bin 20 Jul-29 Jul), 65.5 h (Nobile Rim 2; first in the bin 10 Jul-19 Jul). The 2001 test used 24-hour daylight, which is not the same as Sun inside a lunar band.
- Over the whole year the Haughton cell has long-window open hours of 13.4 h (Connecting ridge), 100.3 h (Malapert), 134.0 h (Mons Mouton), 242.9 h (Nobile Rim 2); best bins for Nobile Rim 2: 30 Jul-8 Aug (55 h), 9 Aug-18 Aug (48 h), 20 Jul-29 Jul (41 h) (`named_sites.sites[].targets.<target>.open.long.year`, `.top_bins`).

## (g) Antarctica: snow not measured

No open product measures winter snow on Antarctic rock, so the 1,241 southern cells have no snow-free hours (`snow.status` = unmeasured, `snow_free_hours` null). Their light counts the rock season only, 27 November to 1 March, when the rock maps were made from snow-free scenes; they are ranked apart from the north.

| Target | Flat horizon ≥ 50 h | ≥ 100 h | ≥ 200 h | with the real horizon, among the 437 southern cells that have one: cells ≥ 50 / 100 / 200 h |
|---|---|---|---|---|
| Connecting ridge | 80 cells, 2,387 km² | 35 cells, 921 km² | 0 cells, 0 km² | 5 / 0 / 0 |
| Malapert | 954 cells, 35,336 km² | 768 cells, 29,940 km² | 281 cells, 8,714 km² | 182 / 74 / 9 |
| Mons Mouton | 1,035 cells, 38,282 km² | 823 cells, 31,342 km² | 405 cells, 13,011 km² | 222 / 120 / 17 |
| Nobile Rim 2 | 1,211 cells, 43,211 km² | 980 cells, 35,606 km² | 746 cells, 29,411 km² | 327 / 204 / 86 |

Source: `grazing_cells.json` → southern gridded cells, `targets.<target>.long_summer_rock_hours`, `long_summer_rock_open_hours`, `bare_km2`.

- The 1,241 cells hold 43,684 km² of mapped rock; regions: Transantarctic Mountains 445, Victoria Land 291, Antarctic Peninsula and South Shetlands 182, Enderby and Mac.Robertson Land 121, Dronning Maud Land 113, Ellsworth Mountains 54, Antarctica 13, Princess Elizabeth Land 9, Wilkes Land 8, South Orkney Islands 5 (`region`, `bare_km2`).
- In 616 of them the two rock-outcrop layers differ by more than a factor of 2 (`layers_disagree`).
- 334 southern cells are ranked (a horizon and bare ≥ 0.25). See (d) for what terrain takes away in the southern sample.

**Shackleton-de Gerlache connecting ridge: lighting goal, top 3 of the south (rock season only):**

| # | Cell centre (lat, lon) | Region | Bare | Long-window hours a year: open (flat horizon) | Score | When to go: best ten-day bins | Time of day | Known or little known |
|---|---|---|---|---|---|---|---|---|
| 1 | -68.45, 78.15 | Princess Elizabeth Land | 0.89 | 33 (81) | 0.385 | 27 Nov-6 Dec (12 h), 1 Jan-10 Jan (12 h), 11 Jan-20 Jan (9 h) | 100% of the hours with the Sun in the south (around midnight) | little known |
| 2 | -67.75, -68.55 | Antarctic Peninsula and South Shetlands | 0.37 | 71 (116) | 0.361 | 17 Dec-31 Dec (19 h), 27 Nov-6 Dec (18 h), 1 Jan-10 Jan (18 h) | 100% of the hours with the Sun in the south (around midnight) | little known |
| 3 | -66.45, 110.55 | Wilkes Land | 0.62 | 26 (82) | 0.287 | 17 Dec-31 Dec (17 h), 7 Dec-16 Dec (10 h) | 100% of the hours with the Sun in the south (around midnight) | little known |

**Malapert Massif: lighting goal, top 3 of the south (rock season only):**

| # | Cell centre (lat, lon) | Region | Bare | Long-window hours a year: open (flat horizon) | Score | When to go: best ten-day bins | Time of day | Known or little known |
|---|---|---|---|---|---|---|---|---|
| 1 | -68.45, 78.15 | Princess Elizabeth Land | 0.89 | 198 (283) | 0.939 | 17 Dec-31 Dec (58 h), 7 Dec-16 Dec (38 h), 1 Jan-10 Jan (38 h) | 100% of the hours with the Sun in the south (around midnight) | little known |
| 2 | -70.75, 67.95 | Enderby and Mac.Robertson Land | 0.79 | 148 (265) | 0.763 | 17 Dec-31 Dec (29 h), 11 Jan-20 Jan (26 h), 27 Nov-6 Dec (25 h) | 100% of the hours with the Sun in the south (around midnight) | little known |
| 3 | -71.25, 67.35 | Enderby and Mac.Robertson Land | 0.50 | 206 (241) | 0.710 | 11 Jan-20 Jan (41 h), 21 Jan-30 Jan (37 h), 27 Nov-6 Dec (36 h) | 100% of the hours with the Sun in the south (around midnight) | little known |

**Mons Mouton plateau: lighting goal, top 3 of the south (rock season only):**

| # | Cell centre (lat, lon) | Region | Bare | Long-window hours a year: open (flat horizon) | Score | When to go: best ten-day bins | Time of day | Known or little known |
|---|---|---|---|---|---|---|---|---|
| 1 | -68.45, 78.15 | Princess Elizabeth Land | 0.89 | 216 (302) | 0.943 | 17 Dec-31 Dec (63 h), 7 Dec-16 Dec (42 h), 1 Jan-10 Jan (41 h) | 100% of the hours with the Sun in the south (around midnight) | little known |
| 2 | -70.75, 67.95 | Enderby and Mac.Robertson Land | 0.79 | 174 (296) | 0.828 | 17 Dec-31 Dec (37 h), 11 Jan-20 Jan (30 h), 27 Nov-6 Dec (28 h) | 100% of the hours with the Sun in the south (around midnight) | little known |
| 3 | -71.35, 170.25 | Victoria Land | 0.88 | 140 (315) | 0.786 | 21 Jan-30 Jan (23 h), 17 Dec-31 Dec (22 h), 11 Jan-20 Jan (22 h) | 100% of the hours with the Sun in the south (around midnight) | little known |

**Nobile Rim 2: lighting goal, top 3 of the south (rock season only):**

| # | Cell centre (lat, lon) | Region | Bare | Long-window hours a year: open (flat horizon) | Score | When to go: best ten-day bins | Time of day | Known or little known |
|---|---|---|---|---|---|---|---|---|
| 1 | -73.45, 61.75 | Enderby and Mac.Robertson Land | 0.92 | 212 (411) | 0.957 | 21 Jan-30 Jan (34 h), 31 Jan-9 Feb (34 h), 11 Jan-20 Jan (27 h) | 100% of the hours with the Sun in the south (around midnight) | little known |
| 2 | -68.55, 78.15 | Princess Elizabeth Land | 0.91 | 234 (392) | 0.954 | 17 Dec-31 Dec (62 h), 7 Dec-16 Dec (41 h), 1 Jan-10 Jan (39 h) | 100% of the hours with the Sun in the south (around midnight) | little known |
| 3 | -71.35, 170.25 | Victoria Land | 0.88 | 202 (440) | 0.939 | 17 Dec-31 Dec (33 h), 21 Jan-30 Jan (27 h), 11 Jan-20 Jan (27 h) | 100% of the hours with the Sun in the south (around midnight) | little known |

Source: `cells_scored.json` → southern records: `targets.<target>.goals.lighting`, `.long_summer_rock_open_hours`, `.long_summer_rock_hours`, `.top_bins_summer_rock`, `.poleward_share_summer_rock`.

The named southern sites, with what is known about their winter snow:

| Site (south) | Cell | Bare / land share | In the screen | Winter-snow evidence | Horizon N / S | Malapert: rock-season long-window hours flat / open | Nobile Rim 2: the same |
|---|---|---|---|---|---|---|---|
| Bunger Hills | -66.3_100.5 | 0.60 / 0.88 | yes | literature: no continuous winter cover | 1.0° / 1.9° | 181 / 67 | 307 / 148 |
| Vestfold Hills | -68.6_78.0 | 0.91 / 0.74 | yes | one qualitative report | 1.2° / 1.8° | 281 / 151 | 392 / 234 |
| Larsemann Hills | -69.4_76.2 | 0.81 / 0.14 | no | station shows snow | 0.0° / 3.3° | 305 / 115 | 427 / 194 |
| Schirmacher Oasis | -70.8_11.4 | 0.18 / 1.00 | yes | literature: no continuous winter cover | -0.0° / 3.8° | 265 / 98 | 411 / 199 |
| Lake Untersee and the Eliseev anorthosite massif | -71.4_13.2 | 0.65 / 1.00 | yes | no evidence | 1.8° / 15.4° | 236 / 10 | 440 / 38 |
| McMurdo Dry Valleys | -77.6_161.5 | 0.89 / 1.00 | yes | measured mostly bare | 9.8° / 15.1° | 156 / 8 | 238 / 26 |
| Windmill Islands | -66.3_110.4 | 0.14 / 0.39 | no | station shows snow | -0.2° / 1.3° | 181 / 84 | 307 / 175 |
| Syowa and the Soya Coast | -69.1_39.3 | 0.52 / 0.10 | no | station shows snow | 0.5° / 0.4° | 271 / 222 | 390 / 326 |
| Fildes Peninsula | -62.2_-59.0 | 0.40 / 0.47 | yes | station shows snow | -0.1° / 1.6° | 0 / 0 | 0 / 0 |
| Deception Island | -63.0_-60.6 | 0.42 / 0.35 | yes | no evidence | 1.9° / -0.0° | 0 / 0 | 0 / 0 |
| Ulu Peninsula, James Ross Island | -63.9_-58.0 | 1.00 / 0.84 | yes | no evidence | 2.6° / 4.4° | 0 / 0 | 101 / 31 |
| Seymour Island | -64.3_-56.8 | 1.00 / 0.46 | yes | station shows snow | 1.1° / 2.3° | 0 / 0 | 146 / 79 |
| Rothera Point | -67.6_-68.4 | 0.11 / 0.44 | no | station shows snow | 4.3° / 0.7° | 285 / 160 | 386 / 222 |
| Jutulsessen at Troll | -72.1_2.4 | 0.31 / 1.00 | yes | one qualitative report | 0.3° / 3.2° | 200 / 69 | 424 / 205 |
| Northern Foothills, Terra Nova Bay | -74.8_164.0 | 0.90 / 0.15 | no | no evidence | 2.8° / 0.2° | 146 / 92 | 300 / 209 |

Source: `validation.json` → `named_sites.sites[]` (`.winter_snow_evidence` is copied from `data/reference/antarctic_sites.json`; `.targets.<target>.long_summer_rock_hours`, `.long_summer_rock_open_hours`).

- Evidence labels of the 15 sites: "station shows snow" 6, "no evidence" 4, "literature: no continuous winter cover" 2, "one qualitative report" 2, "measured mostly bare" 1. "Measured mostly bare": McMurdo Dry Valleys.

## (h) The old measure against the new

The first method counted days on which the Sun stays under the limit even at noon, times the snow-free odds ("usable days"). The new files keep that column with the corrected Sun and snow (`usable_days`).

| Target | Old file: cells with ≥ 10 usable days | New: measured cells with ≥ 10 | New: doubtful cells with ≥ 10 (not counted) | Regions of the new measured cells | Where the old cells are now | For scale: measured cells with ≥ 100 long-window snow-free hours |
|---|---|---|---|---|---|---|
| Connecting ridge | 0 | 0 | 0 | none | none | 6 |
| Malapert | 49 | 41 | 2 | Iceland 41 | still ≥ 10: 40; doubtful: 7; measured, now under 10: 2 | 7,430 |
| Mons Mouton | 52 | 45 | 2 | Iceland 45 | still ≥ 10: 44; doubtful: 7; measured, now under 10: 1 | 8,301 |
| Nobile Rim 2 | 57 | 50 | 2 | Iceland 49, Svalbard 1 | still ≥ 10: 48; doubtful: 8; measured, now under 10: 1 | 9,982 |

Source: `validation.json` → `old_against_new.targets.<target>.old`, `.new_measured`, `.new_doubtful`, `.new_measured_regions`; "where the old cells are now" was worked out here from `light_cells_v1.json` (`<cell>.<target>.usable_days`) and `grazing_cells.json` (`snow.status`, `usable_days`); last column `big_picture_north.targets.<target>.long_snow_free_hours.year.100.cells`.

| Target | Top lighting sites (new measure) | of them with ≥ 10 usable days (old measure) | of them with 0 usable days | Most usable days among them |
|---|---|---|---|---|
| Connecting ridge | 10 | 0 | 10 | 0.0 |
| Malapert | 10 | 0 | 6 | 3.4 |
| Mons Mouton | 10 | 0 | 4 | 3.9 |
| Nobile Rim 2 | 10 | 1 | 4 | 28.2 |

Source: `cells_scored.json` → `targets.<target>.usable_days` of the top-10 lighting sites.

- The old measure counts winter noon light only. The new one adds the dawn, dusk and midnight-Sun hours; of the long-window snow-free hours × bare km² 99.6%, 98.4%, 98.2%, 97.9% fall in the summer half for the four targets (see (b) and (c)).
- The first row of the old ranking (`ranking_v1.txt`) was: `0.36 74.45 19.25 Bear Island (Bjornoya) ...`. In the new files the cell of Bear Island is "doubtful" (3 stuck winters) and the cell of Jan Mayen is "doubtful" (5 stuck winters), so neither is ranked; see (i).

## (i) What is doubtful or not covered

### Doubtful and no-data cells

- 36 gridded northern cells are **doubtful**: at least one winter in which a snow pixel read "snow-free" on every map at or north of 67.4 N, or three such winters anywhere (regions: Svalbard 18, Arctic Canada 6, Jan Mayen 6, Bear Island (Bjornoya) 2, North-west Greenland or Ellesmere 2, Greenland 1, Novaya Zemlya 1). 34 have **no snow data**: no land pixel of the 4 km snow grid within the 5 × 5 block (regions: Greenland 24, Arctic Canada 4, North-west Greenland or Ellesmere 4, Chukotka 1, Novaya Zemlya 1). Neither group is ranked or counted; all 70 are listed with both versions of their hours in `ranking.txt` under "DOUBTFUL SNOW OR NO SNOW DATA" (`grazing_cells.json` → `snow.status`, `snow.stuck_winters`, `region`).
- 13 of the doubtful and 30 of the no-data gridded cells are candidates and have a horizon record (`candidates.json`, `snow.status`). The scored file holds 14 doubtful records because one named-site cell outside the screen is doubtful too.
- For a doubtful cell the hours with the stale-flag rule are the lower figure and the hours as the maps read are the upper one. The rule leaves out a pixel's whole spring and summer after a stuck winter if the pixel never reads snow before 30 September, so it lowers summer odds too:

| Site | Cell | Status | Stuck winters | Snow land pixels (of 9) | Malapert: with the rule / as mapped / open (with the rule and terrain) | Nobile Rim 2: the same |
|---|---|---|---|---|---|---|
| Bear Island, Norway | 74.4_19.0 | doubtful | 3 | 5 | 191.2 / 291.9 / 126.6 | 447.5 / 674.5 / 328.1 |
| Jan Mayen, Norway | 70.9_-8.7 | doubtful | 5 | 3 | 205.8 / 396.9 / 81.0 | 340.3 / 683.9 / 150.2 |
| Lofoten anorthosite (Nusfjord), Norway | 68.0_13.2 | doubtful | 1 | 2 | 334.2 / 352.2 / 66.9 | 520.8 / 551.3 / 124.1 |

Source: `grazing_cells.json` → `snow.status`, `snow.stuck_winters`, `snow.land_pixels`, `targets.<target>.long_snow_free_hours`, `long_snow_free_hours_as_mapped`, `long_open_hours`.

- 43 measured cells also have one or two stuck winters (south of 67.4 N, so not doubtful). The rule lowers their odds in the same way, and they are ranked: their snow-free hours are a lower bound too (`snow.stuck_winters`).
- 3 measured cells (72.7_-117.9, 72.9_-117.3, 74.4_-123.5) have snow odds in only some ten-day bins; their snow-free hours are `null` and they appear as "unknown" in every count.

### Antimeridian cells

- A 30 km horizon window that crosses the 180° meridian is not computed. That holds for 30 northern and 21 southern gridded cells (counted here by asking `earth.tiles_for_window` for every gridded cell). 8 of them are candidates (-84.9_-177.6, -84.9_177.6, -85.0_176.4, -85.3_-177.6, -85.3_-178.8, -85.6_-177.6, -85.6_-178.8, 66.1_-180.0); their open hours are `null` and they are not ranked (`horizon_cells.json` → `skipped`).

### Snow odds: what they rest on

- **4 km snow pixels.** A cell's odds are the mean of the land pixels in a 3 × 3 block (12 km), so a coastal cell can rest on few pixels: 3,784 of the 14,863 measured cells have fewer than 7 of 9 pixels on land, and 158 take their odds from the wider 5 × 5 block because the 3 × 3 block has none. Among the 1,085 ranked northern cells 503 have fewer than 7 (`snow.land_pixels`, `snow.source`). The stability table in (e) shows what a pixel screen does to the top lists.
- **Checked against weather stations.** Against 139 trusted stations the satellite odds of snow-free ground are lower than the station record on average: -0.051 in the winter half, -0.094 in the summer half, -0.128 for May to August at the 50 stations at or north of 66 N (411 station-bins). So the snow-free hours here err on the low side where they can be tested. With station-calibrated odds the number of measured cells reaching 200 long-window snow-free hours would rise from 617 to 2,497 (Malapert), 1,721 to 6,220 (Mons Mouton) and 6,402 to 9,439 (Nobile Rim 2). North of 66 N there are 56 kept stations and none in Finland, Iceland, Greenland; Russia has 1. (`snow_validation_many.json` → `overall.stations`, `periods.<period>.with_stale_flag_rule.mean_bias`, `headline.counts.as_is` and `.calibrated`, `north_of_66`; read from that file, not recomputed here. That file counts from unrounded hours, which is why its starting figures are 617, 1,721 and 6,402 where section (c)'s yearly counts from the rounded file are 618, 1,723 and 6,403.)
- **Stale snow flags in summer on small Arctic islands.** The reverse fault is on record too: the build contract (decision 11) notes that Bear Island reads "snow" through the whole summer of 2024. No rule corrects it and it was not measured again here, so summer hours on such islands are understated by an unknown amount. Together with the point above, a doubtful cell's with-rule hours are a lower bound.

### Sun and terrain geometry

- **Standard refraction.** The Sun's apparent height uses refraction at standard pressure and temperature (0.48° at a true elevation of 0°, `sun.refraction_deg`). That value alone is 23% of the 2.08° band and 6% of the 7.59° band; real polar air can bend light more or less than the standard value, and nothing here measures by how much.
- **One ray per ten-degree sector.** The terrain horizon is taken along one ray at the centre of each of 36 azimuth sectors, on a 60 m grid, out to 25 km. At 25 km a sector is 4.4 km wide, so a peak or gap narrower than that can fall between rays.
- **The 2-hour rule is all or nothing**, and spells are counted in 2-minute steps. Gridded cells with a ten-day bin exactly at 2.00 h / with a bin between 1.96 and 2.00 h (at most about one step short): Connecting ridge 478 / 412; Malapert 1,552 / 2,828; Mons Mouton 1,240 / 2,872; Nobile Rim 2 2,248 / 4,486 (`grazing_bins.npz` → `stretch`). For those cells one bin's hours enter or leave the long-window total on a difference of about 2 minutes.
- **The 59-degree band edge.** See (a): with the 2 h rule Nobile Rim 2's belt begins at 57.65°, 1.35° outside the band in each hemisphere; the other three targets start inside it.
- **Known or little known.** A cell counts as known when it lies within 50 km of one of the 85 sites of `data/reference/known_analogs.json`, in Iceland or Svalbard, inside hand-drawn boxes for Devon Island and the McMurdo Dry Valleys, within 50 km of a southern site with analog use, or on an anorthosite body the rock list marks as already used. 869 of the 1,085 ranked northern cells and 279 of the 334 ranked southern cells are little known (`cells_scored.json` → `little_known`). The boxes were not checked against a coastline file.
- **Light score.** It stops at 200 hours, so cells with 200 and 400 open hours score the same; the tables in (e) order such ties by hours. Only candidate cells have a horizon (see the last table of (e)).

### What this match is and is not

- These sites match the **geometry** of low Sun: its height, its compass direction through the day, and the length of shadows. At the four limits a 1 m rock throws a shadow of at least 27.5 m (Connecting ridge), 10.3 m (Malapert), 9.3 m (Mons Mouton), 7.5 m (Nobile Rim 2) (1 ÷ tan of the limit).
- They do not match lunar **contrast**. Earth's air scatters light into shadows and dims and reddens a Sun this low; on the Moon shadows are black and the Sun is at full strength. No number in this file measures that difference.

## Files

| File | Written | What |
|---|---|---|
| `latitude_profile.json` | 14:35:05 | Sun geometry by latitude (a) |
| `grazing_cells.json`, `grazing_bins.npz` | 14:37:07 | hours per cell and target; per ten-day bin |
| `candidates.json` | 14:36:40 | the cells that got a horizon |
| `horizon_cells.json`, `terrain_cells.json` | 14:36:50, 14:36:50 | terrain horizon; slope statistics |
| `cells_scored.json`, `ranking.txt` | 14:39:06 | scores and the ranking tables |
| `validation.json` | 14:39:09 | named sites, counts, old against new, stability, regions, Haughton |
| `snow_free_dekads.npz` | 13:28:39 | snow-free odds per ten-day bin (input) |
| `snow_validation_many.json` | 14:10:54 | the station check of the snow odds |


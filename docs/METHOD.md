# How the method works

The method is the one of the first build of 14 November 2026. The passes of 15 November took it to 16 lunar regions and 57 Mars sites (`docs/all-regions-log.md`, `docs/mars-sites-log.md`, `docs/final-join-log.md`).
Figures of all regions and sites: `data/derived/RESULTS-FINAL.md`. Figures marked with a letter in brackets, such as (a), come from a section of `data/derived/RESULTS.md`, the report of the first build, for its four regions.
The two checks: `data/derived/checks.json` (four regions of the first build). Mars: `data/derived/MARS-RESULTS.md`. Factors: `data/derived/factor_matrix.json`.
Where this text describes a method, it describes what the code in `twinfinder/` and `scripts/` does.

## 1. The question

Where and when on Earth does the Sun stay as low as at the Moon's south pole, for hours, over bare, snow-free ground?
We match one thing only: the Sun's height, with its direction and the shadows it throws.

## 2. The 16 lunar regions

Near the Moon's pole the Sun circles the horizon and never climbs high. Its highest point at a place is 90° minus the latitude, plus 1.54° for the tilt of the Moon's axis.
We call that the **Sun ceiling** (`twinfinder/sun.py`, `lunar_max_sun_elevation_deg`).

We use all candidate landing regions of NASA's two lists for Artemis III: the 13 regions of 19 August 2022 and the nine regions of 28 October 2024. The lists share six regions, thus there are 16.
NASA studied these regions as candidates. They are candidate regions, not landing sites. `data/derived/RESULTS-FINAL.md` gives the table of all 16, and `moon_cards.json` gives each card.

- The Sun ceilings go from 2.08° (Connecting Ridge) to 7.90° (Peak near Cabeus B). A 1 m rock at the ceiling casts a shadow of approximately 28 m to 7 m.
- **13 regions have a NASA 5 m terrain model** (NASA Goddard, LRO LOLA, PGDA product 78). Their position is the centre of the model. The ceiling is for the middle of each model, over a smooth Moon (`moon_cards.json` → `sun_ceiling.range_deg` gives the range across the model).
- **Three regions have no such model:** Slater Plain, Mons Mouton Plateau and Peak near Cabeus B. Their position is the centre of the region box on NASA's map of 2024 (approximately 1 km accurate; `data/reference/lunar_candidate_regions.json`). Their hours are complete, because the hours need only the ceiling. Their slope likeness, roughness and landform are unknown, and the page shows "unknown", not 0.
- NASA's map of 2024 has the box "Mons Mouton" at the place of the 2022 box "Leibnitz Beta Plateau". No NASA text uses the word "renamed". Mons Mouton Plateau is a different region.
- Some terrain models overlap: Nobile Rim 1 and Mons Mouton, de Gerlache Rim 1 and de Gerlache Rim 2, Connecting Ridge and Connecting Ridge Extension. The NASA lists keep them apart, thus we keep each of them.

**The 16 Sun ceilings and where spells of 2 hours start.** The figures come from `data/derived/moon_targets.json` (`sun_max_elev_deg`, `sun_max_elev_range_deg`) and `data/derived/latitude_profile.json` (`thresholds.<region>.N.lowest_lat_with_long_window`, key `"2"`).

| Lunar region | NASA 5 m terrain model | Sun ceiling | Range of the ceiling across the model or the box | Spells of 2 hours start at | In the search band (from 59° N)? |
|---|---|---|---|---|---|
| Connecting Ridge | yes | 2.08° | 1.70° to 2.45° | 64.80° | yes |
| Connecting Ridge Extension | yes | 2.51° | 2.17° to 2.92° | 64.35° | yes |
| Peak Near Shackleton | yes | 2.73° | 2.37° to 3.10° | 64.10° | yes |
| de Gerlache Rim 1 | yes | 2.86° | 2.52° to 3.21° | 64.00° | yes |
| de Gerlache Rim 2 | yes | 3.31° | 2.88° to 3.75° | 63.50° | yes |
| Faustini Rim A | yes | 3.65° | 3.32° to 4.00° | 63.10° | yes |
| Slater Plain | no (box on NASA's map of 2024) | 4.38° | 3.92° to 4.84° | 62.20° | yes |
| Haworth | yes | 4.78° | 4.15° to 5.43° | 61.70° | yes |
| Malapert Massif | yes | 5.55° | 5.20° to 5.91° | 60.65° | yes |
| de Gerlache-Kocher Massif | yes | 5.71° | 5.27° to 6.15° | 60.45° | yes |
| Nobile Rim 1 | yes | 6.10° | 5.64° to 6.56° | 59.90° | yes |
| Mons Mouton | yes | 6.11° | 5.53° to 6.70° | 59.90° | yes |
| Mons Mouton Plateau | no (box on NASA's map of 2024) | 7.21° | 5.78° to 8.70° | 58.25° | no: 58.25° to 59° is outside |
| Amundsen Rim | yes | 7.31° | 6.89° to 7.74° | 58.10° | no: 58.10° to 59° is outside |
| Nobile Rim 2 | yes | 7.59° | 7.14° to 8.04° | 57.65° | no: 57.65° to 59° is outside |
| Peak near Cabeus B | no (box on NASA's map of 2024) | 7.90° | 7.48° to 8.33° | 57.15° | no: 57.15° to 59° is outside |

- The Sun ceiling is for the centre of the model or the box. The range uses nine points of the model or the box (corners, edge centres, centre).
- "Spells of 2 hours start at" is the lowest latitude with such a spell on one day of the year or more, over a flat horizon with standard refraction. The same latitude applies south of the equator.

## 3. Low-Sun spells, counted day by day

*Worked example: if a sentence of this section does not name the 16 regions, its figures are from the first build, for its four lunar regions.*

A **low-Sun spell** is an unbroken time with the Sun's apparent centre above the horizon and at or below a region's ceiling.
The code follows the Sun minute by minute through a whole year (`sun.long_band_minutes_table`). It includes the bending of light by the air at standard conditions, which lifts a Sun on the horizon by about 0.48°.

**The per-day count.** Each day, the code finds every unbroken spell. A spell that runs through midnight is one spell.
A spell counts when it lasts two hours or more. Each of its minutes is put in the day and ten-day period in which it falls.
A Sun that stays in the band for more than a day counts in full. **Hours** are hours a year inside such spells.
The two-hour test is made over a flat horizon. The hills then remove the minutes when the land hides the Sun (section 4).

**Why two hours.** The Sun is this low everywhere at sunrise and sunset, but only for minutes. At the equator the longest spell of the year lasts 10 to 35 minutes (a).
Two hours is **our choice**. No source gave us a needed length. We wanted a whole work session in steady light.

| Rule (four regions of the first build) | Lowest latitude with such a spell (Nobile Rim 2 to Connecting Ridge) | Hours a year at 70° N, Malapert Massif | The same, Nobile Rim 2 |
|---|---|---|---|
| 1 hour | 45.85° to 63.95° | 1,077 | 1,387 |
| 2 hours (used) | 57.65° to 64.80° | 590 | 949 |
| 3 hours | 59.10° to 64.80° | 474 | 690 |

Source: (a) and (i). With a one-hour rule the belt would begin up to 13° outside our search band. We did not search that ground.
For the 16 regions, two-hour spells start at 57.15° (Peak near Cabeus B) to 64.80° (Connecting Ridge). For Mons Mouton Plateau, Amundsen Rim, Nobile Rim 2 and Peak near Cabeus B they start south of 59°, thus a strip of their belt is outside the search.
A review found that moving the cut by one minute changes an area's yearly hours by 6 to 8 at the median latitude (i).
Changing the rule to one or three hours keeps between 1 and 9 of each top-ten list (e).

**The leap-cycle average.** Where noon falls against the seasons moves by a quarter of a day each year, and jumps back in a leap year. It also moves with longitude.
With a sharp two-hour rule, one fixed calendar would move a latitude's hours by up to 9 hours a year.
So every Sun table is the mean over **eight calendars**, an eighth of a day apart (`sun.YEAR_PHASES = 8`).
They are centred on the middle of the 2024 to 2028 leap cycle: day 0 is 2026, moved 0.14 day earlier (`DAY_ZERO_FROM_J2000 = 9495.86`).
A spell that reaches two hours in one calendar of eight counts one eighth.
What remains: the worst move of the calendar changes a latitude's yearly hours by at most 1.5 hours (i). Read the hours as about ±1 hour.

## 4. The four steps

*Worked example: the figures of one lunar region in this section are from the first build, for its four lunar regions; the passes of 15 November kept them.*

We cut polar land into **areas**, each about 11 km across. We searched 16,184 of them.
That is 14,933 in the north (59° to 84°), 1,241 in Antarctica (59° to 87.5° S), and 10 named sites outside the screens.
The year is cut into 36 **ten-day periods**. Each step removes hours. The page shows the same four steps.

| Step | What the code does | Data | Weakness |
|---|---|---|---|
| 1. Sun alone | Hours in spells of two hours or more, per area and ten-day period, over a flat horizon | Our own Sun code (`twinfinder/sun.py`), checked against NASA JPL Horizons | A typical year, not a real date. Standard refraction; cold polar air can bend light more. |
| 2. Snow-free ground | Multiply each period's hours by the odds that the ground is snow-free then | IMS daily snow maps, 4 km, October 2015 to September 2025 (U.S. National Ice Center) | Measured only north of the equator. A coastal area can rest on few pixels. 36 areas are doubtful and 34 have no data; neither is ranked. |
| 3. Hills | Find the real horizon in 36 directions, out to 25 km. Keep only the hours when the land sees the Sun | Copernicus DEM GLO-90 (European Union and ESA) | One ray per 10° on a 60 m grid: a narrow peak can be missed. Horizons are missing for 51 areas at the antimeridian. |
| 4. Typical cloud | Multiply by the clear share of the sky in that month | NASA POWER monthly cloud amount (CERES SYN1deg), 1° grid, 2001 to 2025 | A climatology of a 1° box over the whole day, not the cloud at the low-Sun hours. Not the chance of seeing a low Sun. |

**Bare ground.** Only areas at least 15 percent bare are searched; only those at least 25 percent bare are ranked.
In the north, bare ground is ESA WorldCover 2021. In Antarctica it is two rock-outcrop maps of the British Antarctic Survey.
The two maps differ by more than a factor of two in 616 of 1,241 areas.
"Bare" takes in sand bars and tidal flats. Small bare patches under the screen are measured apart, in `winter_leads.json` (l).

**Antarctica.** Its winter snow is not measured by any open product we found. Its hours count only the rock season, 27 November to 1 March, and assume the rock is bare then.

**Rock.** Areas on a body of anorthosite, the rock of the Moon's highlands, get a rock score. The list holds 28 bodies, compiled from the literature. Only 17 ranked areas have any rock score.

What the steps do, for Malapert Massif in the summer half (c, d; `validation_extras.json`):

- 7,361 of the 14,863 northern areas with measured snow reach 100 hours on snow-free ground over a flat horizon.
- Of the 14,833 northern areas with measured snow and a terrain horizon, 3,145 still do once hills are counted. `data/derived/RESULTS-FINAL.md` gives this filter and the filters of two other counts (14,830 and 14,834).
- The median area keeps 51.3 percent of its hours after hills (28.6 percent for Connecting Ridge). A blind sample of 300 areas gave 53.5 percent.
- Cloud then keeps about 23 percent of the hours, and no area keeps 100 hours under a typically clear sky.

**The hills at 16 Sun ceilings.** The stored skylines (`horizon_cells.json`) give the open share at nine bins of Sun height, with lower edges at 0, 0.5, 1.0, 1.5, 2.08, 3.0, 4.0, 5.55 and 6.11°.
The run of 16 regions has 21 bins, with an edge at each Sun ceiling. Each new bin takes the open share of the stored bin that holds its lower edge (`horizon.share_on_edges`).
Thus the hours after hills are a lower bound for 14 of the 16 regions. Only Connecting Ridge and Connecting Ridge Extension use the full method of the first build, because each bin of their band starts at a stored edge. That method is also an approximation (bins of Sun height, 36 directions).
A run of the horizon step at all 21 bins needs approximately 90 minutes. It was not done. `grazing_cells.json` → `meta.horizon_bins` records which regions are a lower bound.

Temperature is shown, not scored: NASA POWER (MERRA-2) for Earth, and Diviner model values for the Moon.

## 5. How areas are ranked, and what the ranking is not

*Worked example: this section describes the rules of the first build; the counts of ranked areas do not change with the number of lunar regions.*

The code scores each factor between 0 and 1 (`twinfinder/score.py`):

- **Light** = hours after snow and hills ÷ 200, capped at 1. In Antarctica: rock-season hours after hills.
- **Terrain** = how alike the area's slopes are to the lunar region's, against how alike the region is to itself.
- **Rock** = the anorthosite score. **Bare** = the bare share.

Four goals take the geometric mean of their factors. A factor of 0 makes the goal 0; an unknown factor makes it unknown.

- **Lighting** = light and bare. This is the main list.
- **Shadows** = light, terrain and bare. **Geology** = rock, terrain and bare. **Full match** = all four.

Only measured northern areas with a horizon and enough bare ground are ranked: 10,837 areas. Antarctica is ranked apart: 617 areas. Lists show one site per 50 km.

The scores in `cells_scored.json` do not use cloud, and do not use access, permits, protection or cost.
They favour flat bare ground. The first places are remote coastal flats in the Russian Arctic; we did not check on images what that ground is.
Areas with 200 and with 400 hours score the same; ties are ordered by hours.
It is a ranking by light. It is not a shortlist of field sites.

## 6. The checks

*Worked example: if a sentence of this section does not name the 16 regions, its figures are from the first build, for its four lunar regions.*

**Counted twice** (`scripts/independent_recount.py`; `checks.json` → `independent_recount`).
A separate program that imports nothing from `twinfinder` recounted every area. It has its own Sun position, its own eight calendars, its own spell finding and its own reading of the snow grid.
It compared 1,359,456 figures for 16,184 areas and the 4 lunar regions of the first build. It was not run again for the 16 regions. Tolerance: the larger of 2 percent and 1 hour a year.
None was outside it. The largest difference was 0.065 hour a year, and 0.007 hour in a ten-day period. No snow summary differed.
With every calendar moved 0.14 day later, no area moved by more than the tolerance either. The largest move was 1.22 hours a year (Connecting Ridge); 0.76 hour for the other three.
*What it does not check:* it takes our terrain horizons and the same published Sun series (the Astronomical Almanac's low-precision formula) as given. So it checks the counting, not those inputs.

**Sun against NASA JPL Horizons** (`scripts/check_against_horizons.py`; `checks.json` → `jpl_horizons`).
Horizons gave the refracted Sun every 5 minutes at 9 places, for 4 ten-day periods each, for the dates of 2026. The answers are saved in `data/raw/horizons_check/`.
For each place, period and lunar region, our hours were set beside the Horizons hours: 144 rows.

| Hours compared | Median difference | Largest difference |
|---|---|---|
| All hours in the band | 0.11 percent (0.009 hour) | 6.3 percent (0.63 hour) |
| Hours in spells of two hours or more | 0.26 percent | 8.0 percent (1.60 hours in ten days) |

The 5 rows that differ by more than 5 percent or 1 hour are all for Connecting Ridge.
Four come from the eight-calendar mean set against Horizons' single year. In one, a day's longest spell is within 15 minutes of the two-hour cut.
The program ran on the Sun code of the first build (same sha256). Both checks ran on 14 November 2026 at about 20:00 Pacific, for the four regions of the first build; `checks.json` gives the time in UTC, so its date is 15 November. The passes of 15 November did not run them again.

**Snow against stations** (i). Against 139 trusted weather stations, the maps' odds of snow-free ground are lower than the station record on average.
The difference is −0.049 in the winter half and −0.094 in the summer half. So the maps err toward more snow.
With odds calibrated to the stations, the winter counts after hills would rise. For Nobile Rim 2 they go from 34 to 45 areas, some in Novaya Zemlya and Siberia.
That figure is the last review's recount; `RESULTS.md` does not report it.

**Hills on a blind sample** (d). 300 northern and 150 southern areas were drawn without looking at any score. Their medians agree with the census within 3 percentage points in the north.

**Known sites** (`validation_extras.json` → `known_sites`). For the 16 regions, known and named northern sites have a median percentile of 32 to 59 by hours after hills. Haughton crater is at 75 to 87.
These sites are known for their geology, not for their light, thus this is a simple check, not a test of the ranking.

## 7. The Mars first pass

This is a first pass, coarser than the Moon part. Earth is cut into **squares** of half a degree, about 55 km across (`twinfinder/mars_climate.py`, `mars_score.py`).
81,503 squares have both slopes and climate. The 12,984 with at least 15 percent bare ground are scored.

**The 57 Mars sites** (`mars_sites.json`, written by `scripts/add_mars_site_lists.py` and `scripts/build_mars_cells.py`). A site can be on more than one list:

- the nine NASA landing sites: Viking 1, Viking 2, Mars Pathfinder, Spirit, Opportunity, Phoenix, Curiosity (Gale), InSight and Perseverance (Jezero);
- the seven sites of the 2021 shortlist for human landings, Table 1 of Golombek and others (2021), a study of Starship landing sites: PM-1, PM-7, AP-1, AP-8, AP-9, EM-15 and EM-16;
- the exploration zones that were proposed at NASA's 2015 workshop on human landing sites and that state a position (`data/reference/mars_exploration_zones_2015.json`): 39 sites of their own. Eight more zones lie less than 50 km from a site that we use already, and that site gets the list;
- Arcadia Planitia and Deuteronilus Mensae, two regions that were studied for a human landing.

The workshop papers give 49 zones. Two are left out because no usable position exists: zone 1030 (south-western Meridiani Planum) and zone 1049 (Holden crater). A proposed zone is not a NASA decision. NASA did not name a human landing site on Mars.
The Mars Climate Database gave the model climate of the sites. At Gale and Phoenix, some values are measurements of the missions there.

**The five factor scores**, each between 0 and 1 (`twinfinder/mars_score.py`):

- **Terrain.** Slopes are worked out the same way on both planets, from heights every 1.85 km, across about 3.7 km. Mars uses MOLA topography; Earth uses ETOPO 2022.
  The score is the overlap of the square's and the site's slope histograms, divided by the site's overlap with itself, capped at 1. The site is the 2 × 2 degree box around it.
- **Dry.** 1 at 25 mm of rain and snow a year or less, and 0 at 500 mm or more. Between, a straight line on a log scale.
- **Cold.** 1 where the square's yearly mean air temperature is the site's or colder. 0 at +30 °C or warmer, a straight line between.
  +30 °C is about the warmest yearly mean on Earth, so the scale spans Earth's whole range. The first draft used +15 °C, which gave the hyperarid Atacama a cold score of 0.
- **Bare.** The bare share of the square's land: ESA WorldCover north of 60° S, the rock-outcrop maps in Antarctica.
- **Sun.** The share of the site's yearly range of noon Sun height that the square's own range covers.

**The three goals** are geometric means: **landscape** = terrain and bare; **environment** = dry, cold and bare; **all factors** = all five.
Each square also gets a score per month, from that month's temperature and rain and whether the noon Sun is in the site's range. The three best months are shown.

**What it found** (MARS-RESULTS.md, sections 4 and 5):

- By landscape, 1 to 1,102 squares per site tie at the top score. So the landscape lists are ten of many equal places, not a ranking. Ties are ordered by bare area, then environment score.
- The environment lists hold the same squares in the same order for every site, because only the end point of the cold scale changes.
- On all five factors the highest scores are 0.59 to 0.77, by site. The first places of the 57 sites lie on the Tibetan Plateau (35), in the Qaidam Basin (16), on the Altiplano and Puna (5) and in the Atacama Desert (1).
- No square reaches a cold score of 1 for any site; the highest is 0.82.

**The test** (MARS-RESULTS.md, section 8). Known Mars analog sites were set against 2,000 control squares.
Against all land they win 78 to 83 percent of pairs on landscape, but bare ground alone wins 80 percent. Among bare squares only, they win 35 to 52 percent on all factors, and a random order gives 50 percent.
Thus, among bare ground, the scores do not find the known analog sites much better than a random order.

**Two cautions that go with every Mars figure.**
It is not a climate match: the coldest ranked square, −38.3 °C a year, is still 15.1 to 56.4 °C warmer than the Mars sites.
And a score is a position on each factor's own scale between two set end points, not a share of likeness to Mars.

Other limits: slopes cannot see rocks, dunes, small craters or gullies. Earth climate is a model value (NASA POWER, MERRA-2) for a grid box. Mars temperatures are model values (Mars Climate Database).
Soil chemistry, minerals, ground ice and life are not measured. Section 9 of MARS-RESULTS.md lists the rest.

## 8. The factor table and the rough estimates

`data/derived/factor_matrix.json` (made by `scripts/build_factor_matrix.py`) has one row for each of 38 factors. Each row's status is read from what the files on disk hold.

| Status | What it means | Factors |
|---|---|---|
| Measured and used in the ranking | Measured, or worked out from measured data, and part of a score that orders the lists | 6 |
| Measured and shown | Read from a measured map, a catalogue or a model grid, and shown for each place; not in any score | 19 |
| Rough estimate by our own rule | A word set by a stated rule of ours from other layers | 11 |
| Not built | No figure; the row gives the reason (spectral match) | 1 |
| Planet side only | Figures exist for the lunar regions or Mars sites, but none for places on Earth (surface activity) | 1 |

Pits, caves and skylights were dropped by the team lead and have no row.
Cloud is measured and shown: step 4 of the map takes typical cloud out of the hours, and no score uses it.

**Rough estimates.** Each is a rough estimate by our own rule of thumb; not a measurement. The rules are written in the files' `meta` blocks and on the page.
The seven rules of `twinfinder/estimates.py` cover rockiness, how fast the ground heats and cools, mineral family, and water in the top soil.
They also cover depth to frozen ground, moving sand and dust, and possible ilmenite-bearing rock.
"Power and steady influences" uses rules of the same kind (`scripts/build_power_cells.py`, `build_steady_effects.py`):

- **Solar, wind and geothermal classes.** Solar from NASA POWER sunlight; wind from NASA POWER wind speed; geothermal from distance to geothermal plants and recently active volcanoes.
- **A panel under a low Sun.** A textbook clear-air estimate of sunlight at the lunar ceilings, set beside what the same low Sun gives a panel on the Moon.
- **Steady volcanic and human influences.** From the Smithsonian volcano and eruption lists, GeoNames settlements, Natural Earth roads and railways, and OurAirports.
- **Small tremors.** Catalogued events of magnitude 1 to under 5 within 50 and 100 km, 2010 to 2025 (USGS ComCat). Where the catalogue cannot see small tremors, the count is unknown, not 0.

**Rehearsal verdicts** in the planner are our rule of thumb, not an agency standard (`site/data/rehearsal_rules.json`).
The inputs are read over the best three ten-day periods in a row. H30 is the hours after snow and hills; S, the snow-free odds; C, the clear share of the sky.
K is the share of hours the hills leave; P90 the slope 90 percent of the ground is below; B the bare share.
T is the mean air temperature; D the distance to an airfield with scheduled flights.

| Activity | Pass | Near (nearly passes) |
|---|---|---|
| Rover driving in long shadows | H30 ≥ 40 h, B ≥ 0.25, P90 ≤ 15°, S ≥ 0.8 | H30 ≥ 20 h, B ≥ 0.15, P90 ≤ 20°, S ≥ 0.5 |
| Camera and navigation tests | H30 × C ≥ 10 h and K ≥ 0.6 | H30 × C ≥ 5 h |
| Crew work on foot | H30 ≥ 40 h, D ≤ 100 km, T ≥ −10 °C, S ≥ 0.8 | H30 ≥ 20 h, D ≤ 200 km, T ≥ −20 °C |
| Checking a lamp simulator | H30 × C ≥ 5 h and D ≤ 100 km | H30 ≥ 10 h |

Anything else does not pass. An unknown input gives "cannot tell".

## 9. The limits

- Earth cannot copy the Moon's contrast: our air lights the shadows and dims a low Sun.
- On the Moon the Sun's bearing moves about 0.51° an hour. On Earth it moves 26 to 29 times faster (i).
- Nothing on Earth copies vacuum, one-sixth gravity, lunar dust, radiation or the cold.
- Snow is measured only north of the equator. Antarctica uses the mapped rock outcrops, for its rock season only.
- For four regions (Mons Mouton Plateau, Amundsen Rim, Nobile Rim 2 and Peak near Cabeus B), the belt begins south of 59°, outside our search band.
- The hours after hills are a lower bound for 14 of the 16 regions (section 4).
- Three regions have no NASA terrain model; their slope figures are unknown (section 2).
- The recount and the Horizons check ran for the four regions of the first build only.
- Horizons are missing for 51 areas at the antimeridian; counts "with hills" leave them out.
- Typical cloud is a climatology of a 1° box, not the cloud at the low-Sun hours.
- The Mars part is a first pass on squares of approximately 55 km. It is not a climate match, and a score is not a share of likeness. The Mars Climate Database gave the model climate of the sites.
- Two exploration zones of 2015 (1030 and 1049) are not in the Mars part, because no usable position exists.

The full lists of what is doubtful or not covered are in `RESULTS-FINAL.md`, `RESULTS.md`, section (i), and `MARS-RESULTS.md`, section 9.

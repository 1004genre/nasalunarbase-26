# How to rebuild the results

**For the team lead to fill in**

- `[LINK TO THE LARGE RESULT FILES]`: where the files of section 2 can be fetched (the files of `data/derived/` that the repository does not hold, and the saved JPL Horizons answers).
- Nobody has run the whole chain from an empty `data/raw` folder. Sections 4 to 7 were worked out by reading the scripts. If someone does run it, correct the sizes and times here.
- Section 9 gives the order of the passes of 15 November 2026 (16 lunar regions, 57 Mars sites) as their logs give it: `docs/all-regions-log.md`, `docs/mars-sites-log.md` and `docs/final-join-log.md`.

This file gives the commands, in order, to rebuild every result. It says what each command downloads and roughly how large that is.
No download needs an account, a key or a login. The project's download helper sends the header `User-Agent: twinfinder/0.1`.
Sizes are what the folders of `data/raw/` held on 14 November 2026. "Not timed" means we have no measurement.

## 1. What you need

- Python 3.12 and [uv](https://docs.astral.sh/uv/). Run every command from the top folder of the project.
- For the tests only: approximately 1.2 GB of result files (section 2; measured on 15 November 2026, with 16 lunar regions and 57 Mars sites).
- For a rebuild from nothing: about 13 GB of free disk space. `data/raw/` held about 12 GB on 14 November 2026.

## 2. Before the tests: files a fresh copy lacks

Two sets of files are kept out of the repository (`.gitignore`), and some tests read them:

| Files | Put them at | Size | How to get them |
|---|---|---|---|
| 46 of the 71 files of `data/derived/`: each file that `.gitignore` keeps out (`docs/PUBLIC-COPY.md`, section 4, names them). The largest are `cells_scored.json`, `mars_cells.json` and `grazing_cells.json` | `data/derived/` | approximately 1.2 GB (approximately 164 MB as gzip) | From [LINK TO THE LARGE RESULT FILES], or rebuild them (sections 4 to 8; that downloads approximately 12 GB in all, mostly elevation tiles) |
| 36 saved JPL Horizons answers (`*.txt`) | `data/raw/horizons_check/` | 7.8 MB | From [LINK TO THE LARGE RESULT FILES]. No project script fetches them again. |

Then:

    uv sync
    uv run pytest -q

Without those files, a review of a copy saw failures in `tests/test_check_against_horizons.py`, `test_winter_leads.py`, `test_export_site_tools.py` and `test_export_site_planner.py`.
The same review saw Mars test failures that were not explained. Nobody has run the tests on a fresh copy since.

## 3. What no command rebuilds

**Kept files from earlier versions.** No script here can make them again. `scripts/make_results.py` and `scripts/validate.py` read them.

- `data/derived/light_cells_v1.json`, `cells_scored_v1.json`, `ranking_v1.txt`, `validation_v1.json` (the first method)
- `data/derived/cells_scored_v2.json`, `validation_v2.json`, `ranking_v2.txt`, `RESULTS_v2.md` (version 2)
- `data/derived/count_check_v3.json` (an earlier recount; `checks.json` now holds the current one)

**The Mars site list.** The twelve earlier records of `data/derived/mars_sites_base.json` were written by a script outside the project, from the saved pages in `data/raw/mars_sites/`.
`scripts/add_mars_site_lists.py` then adds the six other sites of the 2021 shortlist and the exploration zones of 2015, and gives each site its lists. It starts again from the twelve earlier records each time, thus a second run gives the same file. It reads `data/reference/mars_exploration_zones_2015.json` and the saved abstracts in `data/raw/mars_sites/ezworkshop2015/`. It adds a site only if its Mars Climate Database answer is on disk.

**The reference lists.** The files in `data/reference/` were compiled by hand from the pages linked in each entry.

**The saved JPL Horizons answers** of section 2.

**Inputs to place by hand.** No script downloads them.

| File | Put it at | From | Size |
|---|---|---|---|
| Antarctic rock outcrop, Landsat, version 7.3 (zip) | `data/raw/antarctica/add_rockoutcrop_landsat_v7.3/add_rockoutcrop_landsat_v7.3.zip` | https://ramadda.data.bas.ac.uk/repository/entry/show?entryid=178ec50d-1ffb-42a4-a4a3-1145419da2bb | 39 MB |
| Antarctic rock outcrop, medium resolution, version 7.11 (zip) | `data/raw/antarctica/add_rock_outcrop_medium_res_v7_11/add_rock_outcrop_medium_res_polygon_v7_11.shp.zip` | https://ramadda.data.bas.ac.uk/repository/entry/show?entryid=3f0c400f-04b9-4819-98cb-f6b53716aca5 | 7 MB |
| Natural Earth 1:50m land (GeoJSON) | `data/raw/naturalearth/ne_50m_land.geojson` | https://www.naturalearthdata.com/ (the exact address is not recorded in the code) | 1.6 MB |
| MOLA MEGDR topography, 32 pixels a degree, and its label | `data/raw/mola/megt90n000fb.img`, `.lbl` | https://pds-geosciences.wustl.edu/mgs/urn-nasa-pds-mgs_mola_topography_derived/meg032/ | about 127 MB |
| ETOPO 2022 v1, 60 arc-second surface elevation | `data/raw/etopo/ETOPO_2022_v1_60s_N90W180_surface.tif` | https://www.ngdc.noaa.gov/mgg/global/relief/ETOPO2022/data/60s/60s_surface_elev_gtif/ | 466 MB |
| Mars Climate Database answers, one per Mars site | `data/raw/mars_climate/mcd/<site>_2d.txt` | the web interface, https://www-mars.lmd.jussieu.fr/mcd_python/ (57 requests in all: 5, then 7, then 45 on 15 November 2026; moderate use only; the logs are `_downloads*.tsv` in that folder) | a few MB |

The station check also reads `ghcnd-stations.txt` and `ghcnd-inventory.txt` in `data/raw/ghcn/`. The code does not record their address. NOAA's usual one is https://www.ncei.noaa.gov/pub/data/ghcn/daily/.

**The COMNAP station file is optional and must stay private.** `scripts/check_known_analogs.py` works without it and then writes "unknown" for Antarctic stations. Its terms allow educational and non-commercial use only.

## 4. The Moon part: inputs that `rebuild_all.py` does not make

Run these first, in order, on a new machine. Each script is safe to run again: it keeps what it has downloaded.

| Step | Command (after `uv run python`) | Writes (in `data/derived/`) | Downloads | Time |
|---|---|---|---|---|
| 1 | `scripts/build_moon_fingerprints.py` | `moon_targets.json` (16 regions) | NASA Goddard PGDA: 13 5 m lunar terrain models (approximately 41 to 142 MB each, approximately 892 MB in all) and two illumination maps (58 MB and 0.6 MB). The three regions without a model take their position from `twinfinder/moon.py` | 3 to 4 s once the files are on disk |
| 2 | `scripts/build_landcover_cells.py` | `landcover_cells.json` | ESA WorldCover 2021, read at low resolution; the Moon part's share of the 323 MB now on disk | Not timed |
| 3 | `scripts/build_south_cells.py` | `landcover_cells_south.json` | Copernicus GLO-90 water-mask tiles; needs the two rock zips of section 3 | Not timed |
| 4 | `scripts/build_snow_climatology.py --download` | `snow_free_dekads.npz` | IMS 4 km snow maps from NSIDC: 740 maps, 308 MB | Not timed |
| 5 | `scripts/build_grazing_cells.py` | `grazing_cells.json`, `grazing_bins.npz` (no hills yet) | Nothing | 17 to 59 s |
| 6 | `scripts/build_candidates.py` | `candidates.json` | Nothing | 1 s |
| 7 | `scripts/build_horizon_cells.py` | `horizon_cells.json` | Copernicus GLO-90 elevation and water-mask tiles from the AWS open-data store; `data/raw/glo90/` now holds 4.6 GB | The largest step: about 0.35 s an area on eight workers, plus the downloads |
| 8 | `scripts/build_terrain_cells.py --cached-only` | `terrain_cells.json` | The same tiles; nothing new after step 7 | 620 to 1,125 s for 16,181 areas (15 November 2026, a busy computer) |
| 9 | `scripts/build_cloud_cells.py` | `cloud_cells.json` | NASA POWER climatology, 12 MB | 5.5 minutes |
| 10 | `scripts/build_temperature_cells.py` | `temperature_cells.json` | NASA POWER climatology and 6 daily series, 54 MB | 8.5 minutes |
| 11 | `scripts/build_moon_cards.py` | `moon_cards.json` | LRO Diviner Polar Resource Product table, NASA Planetary Data System: 605 MB | Not timed |
| 12 | `scripts/build_sunpath_demo.py` | `sunpath_demo.json` | NASA JPL Horizons, only if the answers are not on disk: the Sun's path at two lunar regions, 1.4 MB | Not timed |
| 13 | `scripts/validate_snow_many.py` | `snow_validation_many.json` | NOAA GHCN-Daily station files: 1.3 GB | Not timed |
| 14 | `scripts/validate_snow.py` then `scripts/second_opinion_snow.py` | `snow_validation.json`, `second_opinion_snow.json` | NASA POWER daily points and Open-Meteo: 5.4 MB | Not timed |
| 15 | `scripts/build_winter_leads.py` | `winter_leads.json` | Up to about 200 more GLO-90 tiles | Not timed |
| 16 | `scripts/build_access_cells.py` | `access_cells.json` | OurAirports airports table: 12.8 MB | About 10 s once the table is on disk |

Steps 1 to 4 and 7 to 8 feed the hours. Step 5 must come before steps 6 to 8, because they read the list of areas. The rebuild of section 5 then adds the hills to the hours.
To stop a script from asking any server: `--cached-only` (steps 7, 8, 15) or `--offline` (steps 9, 10, 13, 14, 16).
`scripts/earth_route_test.py` and `scripts/light_calendar_demo.py` are small demonstrations. No result depends on them.

## 5. The Moon part in one command

With the inputs of section 4 on disk:

    uv run python scripts/rebuild_all.py

`uv run python scripts/rebuild_all.py --list` prints its 18 steps:

1. `build_candidates`
2. `build_grazing_cells`
3. `build_latitude_profile` (slow; `--skip-profile` leaves it out and saves about 19 minutes)
4. `build_cloud_cells --offline`
5. `score_cells`
6. `build_temperature_cells --offline`
7. `validate`
8. `validate_snow_many --offline`
9. `build_moon_cards`
10. `build_validation_extras`
11. `check_known_analogs`
12. `build_sunpath_demo`
13. `build_winter_leads --cached-only`
14. `build_access_cells --offline --report`
15. `make_results` (writes `RESULTS.md`)
16. `export_site` (page data)
17. `export_site_extras` (page data)
18. `build_submission` (writes `SUBMISSION.md`)

It downloads nothing: every step runs offline, with its web proxy pointed at a closed local port. It took 38 minutes (2,259 s) on 14 November 2026.
The first step that fails stops the run and names the step. `--from <step>` starts again there.
It does not run `validate_snow.py`, `second_opinion_snow.py`, the Mars part, the factor files or the two checks.

## 6. The two checks

Run them after section 5 whenever the Sun code or the areas change. They write `data/derived/checks.json`.

    uv run python scripts/independent_recount.py --shift 0.14
    uv run python scripts/check_against_horizons.py

The recount asks no server and imports nothing from `twinfinder`. It took 415 s for all 16,184 areas. `--shift 0.14` also measures how far the hours move with the calendar.
The Horizons check reads only the saved answers in `data/raw/horizons_check/` (section 2). It makes no request.
Then run `scripts/make_results.py` again, so that `RESULTS.md` quotes the new `checks.json`.

## 7. The Mars first pass

Run after section 4, step 2, because it reuses the WorldCover tiles and the Antarctic rock file. In order:

| Step | Command (after `uv run python`) | Writes (in `data/derived/`) | Downloads |
|---|---|---|---|
| M1 | `scripts/build_mars_terrain.py` | `mars_terrain.json` | Nothing; needs MOLA, ETOPO and Natural Earth (section 3) |
| M2 | `scripts/build_mars_climate.py fetch-power` | raw answers in `data/raw/power_global/` | NASA POWER climatology for land boxes: 167 MB |
| M3 | `scripts/build_mars_climate.py fetch-worldcover` | tiles in `data/raw/worldcover/` | ESA WorldCover tiles from 60° S to 57° N, read at low resolution |
| M4 | `scripts/build_mars_climate.py build` | `mars_climate.json` | Nothing; needs the Mars Climate Database answers (section 3) |
| M5 | `scripts/build_mars_cells.py` | `mars_sites.json`, `mars_cells.json`, `mars_validation.json`, `MARS-RESULTS.md` | Nothing |

## 8. The factor files and the page sections

Run after sections 5 and 7. The first group reads only `grazing_cells.json`, `mars_cells.json` and earlier files.
Each fetching script keeps its raw answers and asks only for what is missing. Most have an `--offline` switch or a separate `build` step.

| Step | Command (after `uv run python`) | Writes (in `data/derived/`) | Downloads, now on disk |
|---|---|---|---|
| F1 | `scripts/build_environment_cells.py` | `environment_cells.json` | NASA POWER climatology: 34 MB |
| F2 | `scripts/build_mars_environment.py fetch`, `fetch-uv-hours`, `check-years`, then `build` | `mars_environment.json` | NASA POWER climatology: 192 MB |
| F3 | `scripts/build_power_extra.py fetch`, then `build` | `power_extra_cells.json`, `mars_power_extra.json` | NASA POWER climatology: 69 MB |
| F4 | `scripts/build_tremors.py` | `tremors_cells.json`, `mars_tremors.json` | USGS ComCat, small events: 142 MB |
| F5 | `scripts/build_hazards_people.py --report` | `hazards_people_cells.json`, `mars_hazards_people.json` | USGS ComCat, magnitude 5 and up (10 MB); Smithsonian volcano list (2.6 MB); GeoNames cities1000 (11 MB) |
| F6 | `scripts/build_rock_frozen.py --report` | `rock_frozen_cells.json`, `mars_rock_frozen.json` | GLiM rock map and the permafrost map from PANGAEA: `data/raw/permafrost/` holds 2.8 GB |
| F7 | `scripts/build_ground_cells.py` | `ground_moon.json`, `ground_cells.json`, `mars_ground.json` | Nothing; reads the GLO-90 tiles, the LOLA models and `mars_terrain.json` |
| F8 | `scripts/build_planet_factors.py` | `planet_factors.json` | Small public files and pages: `data/raw/planet_factors/` holds 127 MB |
| F9 | `scripts/build_estimates.py fetch`, then `scripts/build_estimates.py` | `estimates_cells.json`, `mars_estimates.json` | A few pages: 1.7 MB. Needs F3, F6 and F7 |
| F10 | `scripts/build_steady_effects.py --report` | `steady_effects_cells.json`, `mars_steady_effects.json` | Smithsonian eruption list (8.6 MB); Natural Earth roads and railways (86 MB). Needs F4, F5 and F6 |
| F11 | `scripts/build_power_cells.py fetch-sources`, `fetch-power`, then `build` | `power_cells.json`, `mars_power.json` | WRI power plant list (11 MB); NASA POWER wind at 50 m (21 MB). Needs F1 to F3 and F10 |
| F12 | `scripts/build_factor_matrix.py` | `factor_matrix.json` | Nothing. Reads all of the above |

`build_power_cells.py fetch-power` is slow; its docstring says to run it in the background.

**The page data.** `export_site.py` comes first, because it fixes the order of the areas. The rest can follow in any order. Each writes into `site/data/`.

    uv run python scripts/export_site.py
    uv run python scripts/export_site_extras.py
    uv run python scripts/export_site_tools.py
    uv run python scripts/export_site_planner.py      # about five minutes
    uv run python scripts/export_site_factors.py
    uv run python scripts/export_site_environment.py
    uv run python scripts/export_site_extra.py
    uv run python scripts/export_site_mars.py
    uv run python scripts/export_site_mars_extra.py

None of them asks a server. `export_site.py` needs the Natural Earth file of section 3.

## 9. The passes of 15 November 2026: 16 lunar regions and 57 Mars sites

`scripts/rebuild_all.py` runs the Moon chain of section 5. For the 16 regions and the 57 sites, the logs give this order. Each command runs with `uv run python` from the top folder. Times are from the logs, on a computer that other work shared.

**The lunar regions** (`docs/all-regions-log.md`, second pass):

1. `scripts/build_moon_fingerprints.py` (4 s; the PGDA models must be on disk, section 4).
2. `scripts/build_latitude_profile.py` in the background (2,613 s). It reads no output of the other steps.
3. `scripts/build_terrain_cells.py --cached-only --processes 6` (1,125 s).
4. `scripts/build_moon_cards.py` (22 s), then `scripts/build_planet_factors.py --offline` (2 s).
5. `scripts/build_grazing_cells.py` (1,396 s), then `build_candidates` and `build_cloud_cells --offline`.
6. `scripts/score_cells.py` (748 s). In the background: `scripts/build_ground_cells.py` (661 s), then `scripts/build_power_cells.py build` (57 s).
7. `build_temperature_cells --offline`, then `scripts/validate.py` (2,517 s). In the background: `build_validation_extras` (2,420 s) and `build_winter_leads --cached-only` (942 s).
8. `check_known_analogs`, `build_sunpath_demo`, `build_access_cells --offline --report`.
9. `validate_snow_many --offline`, `build_moon_cards`.
10. `make_results`, `export_site`, `export_site_extras`.

The pass did not run `scripts/build_horizon_cells.py` at the 21 bins of Sun height (approximately 90 minutes). Thus the hours after hills are a lower bound for 14 of the 16 regions. It did not run the two checks of section 6 again.

**The Mars sites** (`docs/mars-sites-log.md`):

1. The Mars Climate Database answers of the new sites go into `data/raw/mars_climate/mcd/` (section 3).
2. `scripts/add_mars_site_lists.py` (57 sites).
3. `scripts/build_mars_terrain.py` (123 s), `scripts/build_mars_climate.py build` (39 s).
4. `scripts/build_mars_cells.py` (5 to 18 minutes). It stops if a sentence of its report is too long.
5. `scripts/build_ground_cells.py`, `scripts/build_mars_environment.py build`.

**The joined build** (`docs/final-join-log.md`). With both parts on disk, in this order:

    uv run python scripts/build_planet_factors.py --offline
    uv run python scripts/build_power_cells.py build
    uv run python scripts/build_factor_matrix.py
    uv run python scripts/build_estimates.py
    uv run python scripts/export_site.py
    uv run python scripts/export_site_planner.py         # approximately 5 minutes
    uv run python scripts/export_site_extras.py
    uv run python scripts/export_site_tools.py
    uv run python scripts/export_site_mars.py
    uv run python scripts/export_site_mars_extra.py
    uv run python scripts/export_site_factors.py
    uv run python scripts/export_site_environment.py
    uv run python scripts/export_site_extra.py
    uv run python scripts/apply_ste_text.py --check
    uv run python scripts/apply_ste_text.py
    uv run python scripts/split_mars_squares.py
    uv run python scripts/compress_site_data.py
    uv run python scripts/build_submission.py
    uv run python scripts/write_readme_credits.py

The order of the last steps matters:

- `apply_ste_text.py` comes after the last exporter. Each exporter writes the old wording again. `--check` says what would change and counts the map entries that match nothing. If an entry matches nothing because a figure changed, bring the map in `data/reference/ste/` up to date.
- `split_mars_squares.py` comes after `export_site_mars.py`. It divides `mars_squares.bin` into a shared file and one file for each Mars site, and writes the new places of the columns into `mars.json`. It does nothing if the file is divided already, thus run `export_site_mars.py` again before it.
- `compress_site_data.py` comes last of the page steps. It writes a gzip copy of each page file of 64 KiB or more, and writes again each copy that is older than its plain file.
- `build_submission.py` reads `data/derived` and `site/data/meta.json`. It stops if a sentence has more than 25 words, if the summary is too long, or if the data no longer support a sentence of `docs/submission_template.md`.
- `build_submission.py` and `write_readme_credits.py` copy the credit lines of `data/SOURCES.md`, section 3: into section 8c of `SUBMISSION.md` and between the marks `CREDITS-START` and `CREDITS-END` of `README.md`. Run both after a change to `data/SOURCES.md`. Run `export_site_extras.py` also, because `site/data/sources.json` comes from the same file.

## 10. Check the result

    uv run pytest -q

`tests/test_make_results.py` and `tests/test_results_recount.py` read the real files in `data/derived/`. They fail if the chain is left half run, and skip if the files are absent.
The same inputs should give the same files. We checked that only for single steps, not for the whole chain.
Downloaded sources can change. The IMS maps, the POWER answers, the catalogues and the OurAirports table may differ on a later day.

## 11. Numbers quoted in README.md, docs/METHOD.md and SUBMISSION.md

Check these after any rebuild. `SUBMISSION.md` takes its figures from the files when `scripts/build_submission.py` runs.

| Number as quoted | Where to read it again |
|---|---|
| 16 lunar regions: 13 on the list of 2022, 9 on the list of 2024, 6 on both; 13 with a terrain model | `moon_cards.json` → `cards[].nasa_list`, `cards[].has_model` |
| Sun ceilings 2.08° to 7.90° | `moon_cards.json` → `cards[].sun_ceiling.deg`; `RESULTS-FINAL.md` |
| Two-hour spells begin at 57.15° to 64.80°; four regions south of 59° | `latitude_profile.json` → `thresholds`; `site/data/meta.json` → `targets[].spells_start_south_of_search` |
| Hours after hills a lower bound for 14 regions | `site/data/meta.json` → `targets[].hills_exact`; `grazing_cells.json` → `meta.horizon_bins` |
| Per region: areas with 100 summer hours after snow and hills; best ranked area | `RESULTS-FINAL.md`, first table |
| Hills leave 29 to 58 percent (census median), by region | `validation.json` → `terrain_share_left.north.all_measured` |
| Winter, Malapert Massif: approximately 14,000 by Sun alone, 15 after snow, 12 after hills | `validation_extras.json` → `latitude_against_full_method`; `validation.json` |
| First place by light: 13 of 16 regions in the Russian Arctic | `cells_scored.json` (the lighting goal); `SUBMISSION.md`, finding 8 |
| Known northern sites: median percentile 32 to 59; Haughton 75 to 87 | `validation_extras.json` → `known_sites` |
| Recount and Horizons check: four regions of the first build | `checks.json` |
| 57 Mars sites: 9 NASA landing sites, 7 of the 2021 shortlist, 39 zones of their own, 2 other studied sites; 2 zones left out | `mars_sites.json` → `sites[].lists`, `sites[].kind`; `mars_sites_base.json` → `meta.left_out` |
| Mars: 12,984 ranked squares; ties 1 to 1,102; first places on all factors 0.59 to 0.77; −38.3 °C; 15.1 to 56.4 °C | `mars_cells.json` → `meta`; `MARS-RESULTS.md`, sections 1 to 5 |
| Mars test: 78 to 83 percent on landscape; 35 to 52 percent among bare squares | `mars_validation.json` |
| Factor table: 39 rows; 6, 19, 12, 1, 1 by status | `factor_matrix.json` → `meta.counts_by_status` |

## 12. What was not tried

- The whole chain from an empty `data/raw` folder.
- The tests on a fresh copy with the files of section 2 in place.
- The horizon step at the 21 bins of Sun height of the 16 regions.
- The two checks of section 6 for the 16 regions.
- Whether the hand-placed files of section 3 are still at the addresses given.
- A second machine. Every time above comes from one computer that other work was sharing.

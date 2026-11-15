# Log: ten lunar regions (15 November 2026)

The run of docs/all-regions-plan.md in this copy. Times are local (Pacific). Each command ran from the project folder with `uv run python`.

## Code changes before the run

- `twinfinder/moon.py`: `Target` takes an optional model. Six regions added to `TARGETS`, in order of the Sun ceiling. `fingerprint_without_model` gives the same keys as `fingerprint`, with `terrain: null`. Both write `has_model`, `position_source`, `position_how_sure` and `position_note`.
- `twinfinder/sun.py`: `ELEV_EDGES_DEG` has an edge at each of the ten ceilings (15 bins); `OLD_ELEV_EDGES_DEG` keeps the old nine bins. The four Sun tables run over the latitudes in worker processes. The result is the same, number for number, as one process gives (checked on 9 latitudes, all four tables).
- `twinfinder/horizon.py`: `ELEV_EDGES_DEG` is the Sun table's list. `STORED_EDGES_DEG` and `share_on_edges` move the stored shares (nine bins) to the new bins.
- `twinfinder/grazing.py`: `horizons_of_cells` moves the stored shares to the new bins. `load_targets` stops if a ceiling is not a bin edge, and gives `has_model`.
- Scripts: `build_moon_fingerprints`, `build_terrain_cells`, `score_cells`, `validate`, `build_ground_cells`, `build_moon_cards`, `make_results`, `export_site`, `export_site_extras`, `export_site_tools`, `build_winter_leads`, `build_factor_matrix`. Page: `site/app.js`, `site/style.css`, `site/index.html`.

## Steps

| Start | Step | Time | Result |
|---|---|---|---|
| 07:28 | download of three 5 m models from PGDA (Site06, SL2, Haworth), with `twinfinder.fetch` as for the other models | 54 s, 63 s, 123 s | sizes as the HEAD requests of the region list: 64,025,603, 64,025,605 and 142,123,767 bytes |
| 07:33 | `scripts/build_moon_fingerprints.py` | 3 s | ten regions; the four old records are the same as in the main project, key by key |
| 07:33 | `scripts/build_latitude_profile.py` (background) | 1,193 s | ten regions; the four old regions are the same as in the main project (0 differences in rows and thresholds) |
| 07:34 | `scripts/build_terrain_cells.py --cached-only` | 620 s | 16,181 areas again (the overlap lacked the three new modelled regions); no tile asked for; 0 differences in the old figures |
| 07:37 | `scripts/build_moon_cards.py` | 11 s | ten cards |
| 07:38 | `scripts/build_grazing_cells.py` | 635 s | ten regions; old four: largest difference 0.000015 h in `grazing_bins.npz` (float32 rounding), 0.1 h in two rounded fields of one area of `grazing_cells.json` |
| 07:50 | meta of `grazing_cells.json`: `horizon_bins` added in place by `grazing.horizon_bins_note()` (the code that `build_grazing_cells.py` now uses); no figure changed | seconds | |
| 07:49 | `build_candidates` | 6 s | |
| 07:49 | `build_cloud_cells --offline` | 5 s | no request |
| 07:49 | `score_cells` | 203 s | old four: largest difference 0.1 h (one area, rounding), light factor 0.0005 |
| 07:53 | `build_temperature_cells --offline` | 11 s | |
| 07:53 | `validate` | 364 s | all four checks pass (old usable-day counts 0, 49, 52, 57); old four: 0 differences in regions, named sites, stability, terrain share, Haughton; 0.1 in three calendar sums (hours times km²) |
| 07:59 | `validate_snow_many --offline` | 56 s | no request |
| 08:00 | `build_moon_cards` | 10 s | ten cards; old cards unchanged except the Mons Mouton name note (now from the sourced list) and the new keys `has_model`, `model_note`, `position`, `box_km` |
| 07:54 | `build_ground_cells` (background) | 56 s | ten regions; the three without a model have null figures and `why_null` |
| 08:00 | `rebuild_all.py --skip-profile --from build_validation_extras` | 768 s | `build_validation_extras` 569 s, `check_known_analogs` 1 s, `build_sunpath_demo` 4 s, `build_winter_leads --cached-only` 167 s (10 new horizons from tiles on disk, 2 held back for want of a tile), `build_access_cells` 7 s, `make_results` 9 s, `export_site` 7 s, `export_site_extras` 1 s, `build_submission` 2 s |
| 08:13 | `build_factor_matrix`, `export_site_tools`, `export_site_planner`, `export_site_factors`, `export_site_environment`, `export_site_extra` | 8 s, 3 s, 309 s, 4 s, 2 s, 5 s | file sizes follow the new count: `open.bin` and `snowfree.bin` 5,826,240 bytes, `yearly.bin` 3,884,160, `rose.bin` 5,988,080, `rehearsal.bin` 1,132,880, `factors.bin` 2,508,520 |
| 08:15 | `scripts/export_site_mars.py` | 13 s | the Moon globe of the page takes its lunar points from this file: ten points now |
| 08:20 | `scripts/apply_ste_text.py --check`, five map entries brought up to date, then `apply_ste_text.py` | seconds | 542 sentences changed; 42 entries of `famous.json` match nothing, because `export_site_tools.py` now writes those sentences in STE at the source |
| 08:21 | `export_site_environment` again (sunlight sentence in STE at the source), then `apply_ste_text.py` | seconds | |
| 08:21 | page served locally and looked at, desktop and 375 px | | ten chips; one select menu for the regions at 760 px or less; no horizontal scroll; the card of Peak near Cabeus B shows "Slopes and roughness: unknown" and the source of its position; no console error |

## The four old regions against the main project

| File | Largest difference |
|---|---|
| `moon_targets.json` | none |
| `terrain_cells.json` | none |
| `latitude_profile.json` | none (rows and thresholds) |
| `grazing_bins.npz` | 0.000015 h (float32 rounding of the split bins) |
| `grazing_cells.json` | 0.1 h in `long_open_hours` and `long_open_hours_summer` of one area (70.1_129.0, Nobile Rim 2: 93.6 against 93.7), a rounding at the last digit |
| `cells_scored.json` | the same area: 0.1 h, and its light factor 0.468 against 0.4685 |
| `validation.json` | 0.1 in three calendar sums of hours times km² (values of millions) |
| `site/data/meta.json` | headline of each old region identical; colour scale identical (400 h, 80 h) |

## Not run

- `scripts/build_horizon_cells.py` with exact shares at the new edges (plan step 8): not run. The hours after hills of the six new regions are a lower bound; `grazing_cells.json` `meta.horizon_bins` and the page say so.
- `scripts/independent_recount.py` and `scripts/check_against_horizons.py`: not run (they check the Sun code and the snow maps, which did not change; `independent_recount.py` still has the old edge list).
- `build_power_cells`, `build_planet_factors`: not run. The power figures (`extra.bin`) and the planet factors stay at the four old regions; the six new regions show no figure there.
- `scripts/build_submission.py` ran in the chain, but its text still names four regions (plan step 18).

## Second pass (15 November 2026): 16 regions

The six regions that are only on the NASA list of 2022 come in: Connecting Ridge Extension, Peak Near Shackleton, de Gerlache Rim 1, Faustini Rim A, de Gerlache-Kocher Massif and Amundsen Rim. Each has a NASA 5 m terrain model. Times are local (Pacific). Each command ran from the project folder with `uv run python`. Before the run, a copy of `data/derived` (JSON, NPZ, TXT) and of `site/data` went to a scratch folder outside the project, for the comparisons below.

### Code changes

- `twinfinder/moon.py`: six `Target` records with their PGDA model (SL3, Site07, Site11, LM7, Site42, DM1), in the order of the Sun ceiling. One reason text (`ONLY_2022`) for the six.
- `twinfinder/sun.py`: `ELEV_EDGES_DEG` has an edge at each of the 16 ceilings: 21 bins. The six new edges are 2.51, 2.73, 2.86, 3.65, 5.71 and 7.31 degrees. `OLD_ELEV_EDGES_DEG` (the nine stored bins) does not change.
- `twinfinder/grazing.py`: `stored_on_old_bins`, `hills_exact` and `horizon_bins_note(targets)`. The note gives `hills_exact` for each region: true only if each bin of the band of the region starts at a stored edge, or if no record of `horizon_cells.json` is on the old bins.
- `scripts/build_grazing_cells.py`: passes the targets to `horizon_bins_note`.
- `scripts/build_moon_cards.py`: six `PROVENANCE` entries (names, lists, PGDA models, saved LROC pages). The summary of Mons Mouton now says what the NASA map of 2024 shows, with the source, and keeps "No NASA text uses the word 'renamed'" (point d).
- `scripts/export_site.py`: `meta.targets[]` gets `lists` (point f), `hills_exact` (point b), `spells_start_deg_north`, `spells_start_south_of_search` and `outside_search_text` (point e). `meta.horizon_bins.page_text` and `meta.search_edge.text` are sentences made from the data. `list_line` of Mons Mouton says what the map shows, not "most likely".
- `scripts/build_planet_factors.py`, `scripts/build_power_cells.py`, `scripts/build_factor_matrix.py`: no typed count of regions or ceilings in their sentences; the coverage of the factor matrix counts the cards.
- `scripts/split_mars_squares.py`, `scripts/compress_site_data.py`: copied from the main project without change.

### Steps

| Start | Step | Time | Result |
|---|---|---|---|
| 09:10 | download of six 5 m models from PGDA (curl, User-Agent `twinfinder/0.1`, one at a time): DM1, LM7, SL3, Site07, Site11, Site42 | 49 s, 47 s, 45 s, 32 s, 35 s, 53 s | each size is the same as the HEAD request of the region list: 64,033,681, 64,033,675, 64,025,611, 40,980,808, 40,980,806 and 64,025,611 bytes |
| 09:13 | timing of `build_horizon_cells.compute` on 300 random areas with a horizon, 10 processes, tiles on disk only (a scratch script; nothing written to the project) | 100.7 s | 0.336 s an area (3.30 s inside a worker); thus approximately 90 minutes for the 16,133 areas with a horizon. More than 40 minutes: not run. At the nine old lower edges, the new shares of the 300 areas are the same as the stored shares, value for value |
| 09:16 | `scripts/build_moon_fingerprints.py` | 4 s | 16 regions; the ten earlier records are the same, key by key; the four oldest differ from the main project only by the keys of the first pass |
| 09:17 | `scripts/build_latitude_profile.py` (background) | 2,613 s | 16 regions, 359 rows; the ten earlier regions: 0 differences in rows and thresholds against the copy before the run; the four oldest: 0 differences against the main project |
| 09:17 | `scripts/build_terrain_cells.py --cached-only --processes 6` | 1,125 s (slow: three steps and other work shared the computer) | 16,181 areas again (the overlap lacked the six new modelled regions); no tile asked for; 0 differences in the old figures against the copy before the run and against the main project; 13 modelled regions in the overlap |
| 09:22 | `scripts/build_moon_cards.py` | 22 s | 16 cards; the ten earlier cards are the same except the summary of Mons Mouton (point d) |
| 09:24 | `scripts/build_planet_factors.py --offline` | 2 s | 16 lunar regions; the figures of the four earlier regions are the same; the twelve others have a figure (hydrogen) or null with the reason (the same reasons as the four) |
| 09:25 | `scripts/build_grazing_cells.py` | 1,396 s | 16 regions; the ten earlier regions against the copy before the run: largest difference 0.000015 h in `grazing_bins.npz` (float32 rounding), 0.1 h in two rounded fields of one area in `grazing_cells.json`; the four oldest against the main project: the same 0.000015 h and 0.1 h in three rounded fields of one area (as in the first pass). `meta.horizon_bins.hills_exact` is true for Connecting Ridge and Connecting Ridge Extension only |
| 09:48 | `build_candidates`, `build_cloud_cells --offline` | 16 s, 7 s | `candidates.json` has the same 16,184 areas in the same order; only the fields `why` and `top_position` change, because the six new regions have top lists; no request |
| 09:49 | `score_cells` | 748 s | ten earlier regions: 0.1 h in two rounded fields of one area; four oldest against the main project: the same area, 0.1 h, and its light factor 0.0005 (as in the first pass) |
| 09:49 | `build_ground_cells` (background) | 661 s | 16 regions; the three without a model have null figures and `why_null` |
| 10:00 | `build_power_cells.py build` (background, after the ground step) | 57 s | 16,184 places; low-Sun records for the 16 regions; no request (`build` uses no network) |
| 10:01 | `build_temperature_cells --offline` | 8 s | no request |
| 10:01 | `validate` | 2,517 s (slow: the computer had a load of approximately 40 to 90) | all four checks pass (old usable-day counts 0, 49, 52, 57); the ten earlier regions: 0.1 in five calendar sums of hours times km² (values of millions), else 0 differences |
| 10:02 | `build_validation_extras` (background; it reads no output of `validate`) | 2,420 s | 16 regions |
| 10:02 | `build_winter_leads --cached-only` (background) | 854 s | FAILED: `ValueError: all input arrays must have the same shape`. `winter_leads.json` holds 303 stored horizons: 293 on the nine old bins and 10 on the 15 bins of the first pass. `grazing.horizons_of_cells` moved only the records on nine bins |
| 10:27 | fix: `sun.TEN_REGION_ELEV_EDGES_DEG` (the 15 bins of the first pass); `grazing.edges_by_bins`; `grazing.horizons_of_cells` moves each record from its own edges (`elev_edges` of the record, else the edges that its number of bins gives) to the 21 bins. `build_horizon_cells.record` now writes `elev_edges`. The records on nine bins give the same shares as before the fix (checked on 300 areas) | | |
| 10:27 | `build_winter_leads --cached-only` again | 942 s | 16 regions; 303 horizons used again, 0 computed, 2 held back for want of a tile (as in the first pass); no request |
| 10:28 | `check_known_analogs`, `build_sunpath_demo`, `build_access_cells --offline --report` | 26 s, 56 s, 631 s | no request |
| 10:44 | `validate_snow_many --offline`, `build_moon_cards` | 56 s, 4 s | no request; 16 cards |
| 10:44 | `make_results`, `export_site`, `export_site_extras`, `build_submission` | 14 s, 9 s, 1 s, 2 s | `meta.json`: the headline of each of the ten earlier regions is the same as before the run, and the headline of each of the four oldest is the same as in the main project; colour scale the same (400 h, 80 h). `SUBMISSION.md` still names four regions (plan step 18) |
| 10:45 | `build_factor_matrix`, `export_site_tools`, `export_site_factors`, `export_site_environment`, `export_site_extra`, `export_site_mars` | 15 s, 9 s, 17 s, 4 s, 29 s, 10 s | `extra.bin` now has the power figures of the 16 regions |
| 10:45 | `export_site_planner` | 341 s | rose against `grazing_bins.npz`: largest difference 0.0 h; `skyline.bin` is still 582,624 bytes (its codes count 21 bins) |
| 10:51 | `apply_ste_text.py --check`, then `apply_ste_text.py` | seconds | 536 sentences changed; 44 entries match nothing: the 42 of `famous.json` (as in the first pass) and the two entries with "most likely" for Mons Mouton, because the scripts now write that text in STE at the source |
| 10:52 | `data/SOURCES.md`: five rows without the typed count "four lunar sites"; row 1 names the 13 models. Then `export_site_extras` and `apply_ste_text.py` again | seconds | 64 sentences changed; 47 entries match nothing (the three more are the old "four lunar sites" entries of `zz-reader.json`) |
| 10:52 | `scripts/split_mars_squares.py`, then `scripts/compress_site_data.py` | 0.1 s, 7 s | five Mars site files of 337,584 bytes; 41 compressed copies; 65.5 MB of large files are 15.7 MB compressed. Each `.gz` file opens to the same bytes as its plain file |
| 10:53 | `data/derived/RESULTS-all-regions.md` (16 rows) and `data/reference/lunar_candidate_regions.json` (`status`, `for_the_pipeline`, `not_confirmed`, `on_page_now`) | | the rows of the ten earlier regions are the same as in the table of the first pass |

### The earlier regions against the earlier files

| File | Ten regions of the first pass (copy before the run) | Four oldest regions (main project) |
|---|---|---|
| `moon_targets.json` | none | only the keys that the first pass added |
| `terrain_cells.json` | none | none |
| `latitude_profile.json` | none (rows and thresholds) | none |
| `grazing_bins.npz` | 0.000015 h (float32) | 0.000015 h (float32) |
| `grazing_cells.json` | 0.1 h in two rounded fields of one area | 0.1 h in three rounded fields of one area (as in the first pass) |
| `cells_scored.json` | 0.1 h in two rounded fields of one area | the same area: 0.1 h, light factor 0.0005 (as in the first pass) |
| `validation.json` | 0.1 in five calendar sums of hours times km² | not compared again (the first pass found 0.1) |
| `power_cells.json` | the first pass had the four oldest only: 0 differences | 0 differences |
| `planet_factors.json` | the first pass had the four oldest only: 0 differences | 0 differences |
| `site/data/meta.json` | each headline the same; colour scale the same (400 h, 80 h) | each headline the same |

### Not run, or not done

- `scripts/build_horizon_cells.py` at the 21 bins: approximately 90 minutes, more than the limit of 40 minutes. Thus the hours after hills are a lower bound for 14 of the 16 regions (`hills_exact` false). A run at the 21 bins would also increase the hours after hills of Malapert Massif, Mons Mouton and Nobile Rim 2, thus their figures would then differ from the main project. To run it, the script needs a switch that works out again the cells already stored on the nine old bins (it skips them now); `record()` now writes `elev_edges`.
- `scripts/independent_recount.py`, `scripts/check_against_horizons.py`: not run (the Sun code and the snow maps did not change).
- `site/data/mars_extra.json` (from `scripts/build_estimates.py` and `scripts/export_site_mars_extra.py`, not in the plan): its sentence "Lunar Prospector's hydrogen at the four lunar regions, 107 to 145 ppm" and its copy of the planet-factor meta still give four regions. Not run again.
- `SUBMISSION.md` (`build_submission.py`) still names four regions (plan step 18).
- The page code was not changed, and the page was not looked at in a browser in this pass.

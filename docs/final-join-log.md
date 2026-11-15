# Log: the join of the lunar copy and the Mars copy (15 November 2026)

This folder joins two copies of the project:
- the lunar copy (`variants/all-regions`): 16 lunar regions of the NASA lists of 2022 and 2024;
- the Mars copy (`variants/mars-sites`): 57 Mars sites.

Times are local (Pacific). Each command ran from this folder with `uv run python`, with no network request. `data/raw` is a link to the downloads of the main project; no file there changed.

## Steps

| Time | Step | Result |
|---|---|---|
| 11:10 | copy of the lunar copy into this folder (rsync, without `.venv` and `.pytest_cache`) | 2 s; `data/raw` is the same link as in the lunar copy |
| 11:12 | file comparison: each copy against the main project (`scripts`, `twinfinder`, `docs`, `data/reference`, `data/derived`, `data/SOURCES.md`, `NOTICE`) | 44 files changed only in the lunar copy, 16 only in the Mars copy, 12 in both |
| 11:12 | copy of the 16 files that only the Mars copy changed: `NOTICE`, `MARS-RESULTS.md`, `mars_cells.json`, `mars_climate.json`, `mars_environment.json`, `mars_sites.json`, `mars_sites_base.json`, `mars_terrain.json`, `mars_validation.json`, `data/reference/ste/mars.json`, `data/reference/mars_exploration_zones_2015.json` (absent from the lunar copy), `docs/mars-sites-log.md`, `scripts/add_mars_site_lists.py`, `build_mars_cells.py`, `build_mars_climate.py`, `export_site_mars.py`; also `mars_ground.json` (the lunar copy changed only its time stamp) | |
| 11:13 | join by hand of the files that both copies changed (see "Files joined by hand") | |
| 11:14 | Python environment made from the local uv cache (`UV_OFFLINE=1`) | 6 s, no download |
| 11:15 | `scripts/build_planet_factors.py --offline` | 1 s; 16 lunar regions, each the same as in the lunar copy; 57 Mars sites, each the same as in the Mars copy |
| 11:15 | `scripts/build_power_cells.py build` (as in both passes) | 12 s; `cells` of `power_cells.json` the same as in the lunar copy; `cells` of `mars_power.json` the same as in both copies; each entry of `meta.moon_and_mars` is the same as in one copy (lunar entries: lunar copy; the Mars pressure and wind entries: Mars copy) |
| 11:16 | `scripts/build_factor_matrix.py` | 8 s; 39 rows; coverage of the lunar regions as in the lunar copy (of 16), coverage of the Mars sites as in the Mars copy (of 57) |
| 11:20 | code repairs (a), (b), (c): see "Repairs" | |
| 11:22 | `scripts/build_estimates.py` (fault c: the sentence on lunar hydrogen) | 10 s; `cells` of both output files the same as before; only `meta.made`, `meta.inputs` (times of the input files) and `meta.water_sentence` change |
| 11:24 | `data/derived/grazing_cells.json`: `meta.horizon_bins.note` written again in place from `grazing.horizon_bins_note()` (fault b); the other fields of the note are the same as the code gives; no figure changed | 3 s |
| 11:25 | `scripts/export_site.py` | 11 s; `meta.horizon_bins.page_text` and `note` have the new words of fault (b) |
| 11:25 | `scripts/export_site_planner.py` (background) | 302 s; rose against `grazing_bins.npz`: largest difference 0.0 h; `skyline.bin` (codes 0 to 9 on the nine old bins) has the same bytes as `skyline.bin` of the main project |
| 11:25 | `scripts/export_site_extras.py`, again at 11:26 after one line of `data/SOURCES.md` (the 13 lunar terrain files) | 1 s each |
| 11:26 | `scripts/export_site_mars.py` | 65 s; `mars.json` 3,896,439 bytes, `mars_squares.bin` 19,411,080 bytes, `mars_world.json` 287,549 bytes |
| 11:27 | `scripts/export_site_mars_extra.py` | STOPPED at its limit of 5,000,000 bytes (5,041,570 bytes: the planet factors of 16 lunar regions are in the file now). Limit raised to 5,500,000 bytes, with a comment; run again: 11 s, `mars_extra.bin` the same bytes as in both copies |
| 11:28 | `scripts/export_site_factors.py`, `export_site_environment.py` | 24 s, 14 s |
| 11:29 | `scripts/export_site_extra.py` | STOPPED: "Extra data would exceed the limit: 7,379,820 bytes". The limit (6,000,000 bytes) counts each file `extra*` of `site/data`, also the gzip copies `extra.bin.gz` and `extra.json.gz` that the lunar copy made last. A gzip copy replaces its plain file on the page. The script now does not count `.gz` files (comment in the script); run again: 9 s, 5,916,255 bytes |
| 11:30 | `site/data/extra-prose.json` (written by hand, no script) copied from the Mars copy: its two pressure sentences name the 57 Mars sites | |
| 11:31 | `scripts/apply_ste_text.py --check` | 754 sentences would change; 47 map entries match nothing: the same 47 as at the end of the lunar copy (42 of `famous.json`, two "most likely" sentences of Mons Mouton, three "four lunar sites" rows of `sources.json`) |
| 11:32 | sentences of the page that changed in the join, found by a comparison of each page JSON file with the same file of both copies: only the three new credit lines (AT, AU, AV) in `factors.json` (credit lines: exempt), the new sentence on lunar hydrogen, the hills text of fault (b) and the skyline text of fault (a), each written in STE at the source. No map entry matches a sentence with other numbers | |
| 11:32 | `scripts/apply_ste_text.py` | 754 sentences changed |
| 11:33 | wording maps: the 47 entries for sentences that no longer exist removed (57 lines: some old sentences were in two maps; `moon.json` 34, `zz-reader.json` 23) | |
| 11:34 | `scripts/apply_ste_text.py` again (one sentence of `mars_extra.json` takes two map steps: "A rough guide by our own rule of thumb" to "A rough estimate by our own rule" to "This is a rough estimate by our own rule", as in both copies), then `--check` | 1 sentence changed; then 0 would change, 0 entries match nothing |
| 11:36 | `scripts/split_mars_squares.py` | 0.1 s; 7 shared and 6 new columns in `mars_squares.bin` (285,648 bytes); 57 site files of 337,584 bytes |
| 11:36 | `scripts/compress_site_data.py` | 8 s; 89 copies written (4 were up to date); 87.0 MB of large files are 25.9 MB compressed; each of the 93 `.gz` files opens to the same bytes as its plain file |
| 11:37 | comparison of the page data with both copies, byte for byte and key by key (see "Page data against the copies") | |
| 11:40 | lunar table recounted from `grazing_cells.json` (measured northern areas with a terrain figure; ranked: bare share 0.25 or more): each count and each best area is the same as in `RESULTS-all-regions.md` | |
| 11:44 | `data/derived/RESULTS-FINAL.md` written; each figure of its two tables made by a script from `grazing_cells.json`, `site/data/meta.json`, `mars_sites.json` and `mars_cells.json` | |

## Files joined by hand

Each copy changed these files after the same state of the main project. The join keeps both sets of changes.

| File | Lunar copy | Mars copy | Join |
|---|---|---|---|
| `data/SOURCES.md` | rows 1, 19, 20 and 43: no typed count "four"; row 1 names the 13 models | rows 23, 26, 29 and 32 name the 57 sites; new rows 57 to 60; credit lines AS to AV; the list "Not checked for rows 58 to 60" | both. The lunar copy added no row and no credit line, thus the Mars rows keep their numbers (57 to 60) and their letters (AS to AV). Also one line of the list of large files: "The four lunar terrain files" is now "The 13 lunar terrain files" with their sizes from `data/raw` |
| `NOTICE` | no change | credit lines AS to AV | the Mars copy's file |
| `scripts/build_factor_matrix.py` | no typed "four"; coverage of the lunar regions from the cards | coverage of the Mars sites from `mars_sites.json` | both (the changes are on other lines) |
| `scripts/build_ground_cells.py` | regions without a model; no typed "four" | the Mars meta says "the Mars sites", not "the five Mars sites" | both |
| `scripts/build_planet_factors.py` | the count of lunar regions in `meta.what` | the Mars sites added on 15 November 2026 (ice depth, surface activity, InSight), the MCD credit with LATMOS, the count of Mars sites in `meta.what` | both; the first line and `meta.what` give both counts from the data |
| `data/reference/ste/factors.json` | the Diviner sentence without "four" | the two pressure sentences of `extra-prose.json` with the 57 sites | both |
| `data/derived/ground_cells.json`, `ground_moon.json` | 16 regions | only the time stamp | the lunar copy's files |
| `data/derived/mars_ground.json` | only the time stamp | 57 sites | the Mars copy's file |
| `data/derived/planet_factors.json`, `power_cells.json`, `mars_power.json`, `factor_matrix.json` | 16 regions | 57 sites | built again here (11:15 and 11:16) |

## Repairs

- (a) `scripts/export_site_planner.py`: `skyline.bin` is now written on the nine old bins (`horizon.STORED_EDGES_DEG`), the only edges where the stored horizons give the open share. The layout text in `planner.json` gives the ten old edges and a sentence (`edges`) that says why. The new `skyline.bin` has the same bytes as the file of the main project, which the first build wrote on these nine bins.
- (b) `twinfinder/grazing.py` (`HORIZON_BINS_NOTE`, the docstrings of `hills_exact` and `horizon_bins_note`), `scripts/export_site.py` (`hills_page_text`), `data/derived/RESULTS-all-regions.md` and the note in `grazing_cells.json`: "are exact" is now "these hours use the full method of the first build". The note also says that the method is an approximation. The key `hills_exact` keeps its name, because the page reads it.
- (c) `twinfinder/estimates.py` (`water_sentence`, new), `scripts/build_estimates.py` and `scripts/export_site_mars_extra.py`: the sentence on lunar hydrogen takes the count of lunar regions and the range from `planet_factors.json` (now: 16 lunar regions, approximately 107 to 158 ppm), in STE. The Mars extra exporter makes the sentence again at export if `mars_estimates.json` is older. Its copy of the planet factors now has 16 lunar regions and 57 Mars sites.
- Also: `scripts/export_site_extra.py` does not count the gzip copies in its size limit; `scripts/export_site_mars_extra.py` has a limit of 5,500,000 bytes (comment in the script).

## Page data against the copies

Byte for byte, after the last step (gzip copies not compared):
- The same as the lunar copy: `cells.json`, `yearly.bin`, `open.bin`, `snowfree.bin`, `snowodds.bin`, `cloud.bin`, `flat.json`, `calendar.json`, `profile.json`, `sites.json`, `land.json`, `copy.json`, `rehearsal.bin`, `rose.bin`, `extra.bin`, `factors.bin`, `environment.bin`, `temperature.bin`, `temperature_surface.bin`, `access.bin`, `search.json`, `famous.json`, `winter_leads.json`, `airfields.json`, `tools.json`, `tour.json`, `glossary.json`, `basis.json`, `mars_world.json`, `mars_factors.bin`, `mars_environment.bin`, `mars_extra.bin`.
- The same as the Mars copy: `mars_squares.bin`, the 57 files `mars_site_<id>.bin`, `extra-prose.json`, `mars_world.json`, `mars_factors.bin`, `mars_environment.bin`, `mars_extra.bin`.
- Only the time stamp (`generated` or `written`) differs from the lunar copy: `cloud_regions.json`, `environment.json`, `moon.json`, `places.json`, `sunpath.json`, `validation.json`, `rehearsal_rules.json`, `yearplan.json`.
- `meta.json`: the time stamp and `horizon_bins.page_text` and `horizon_bins.note` (repair b).
- `planner.json`: the skyline layout (repair a), the time stamp and the sizes and times of its input files. `skyline.bin`: repair a.
- `extras.json`: the time stamp and the sizes and times of its input files.
- `mars.json`: against the Mars copy, only `locators.moon` differs (16 lunar points, the same as in the lunar copy).
- `mars_environment.json`: against the Mars copy, only `written`.
- `extra.json`: against the lunar copy, only `meta.power.moon_and_mars` (the Mars entries of the Mars copy).
- `factors.json`: each value is the same as in one copy (lunar values: lunar copy; Mars values: Mars copy), except the time stamps and three new credit lines (AT, AU, AV: the Mars copy wrote its file before it added them to `data/SOURCES.md`). It has 16 lunar regions and 57 Mars sites.
- `sources.json`: rows 1 to 56 as in the lunar copy, rows 57 to 60 and credits AS to AV as in the Mars copy.
- `mars_extra.json`: the planet factors of 16 lunar regions (the Mars copy had four), the joined `moon_and_mars` list of the power meta, the new hydrogen sentence (repair c) and time stamps.

## Sizes of site/data

- 110 plain files: 87,335,209 bytes. 93 gzip copies: 25,852,070 bytes. The folder: 113,187,279 bytes.
- The 93 files of 64 KiB or more: 87,004,710 bytes plain, 25,852,070 bytes compressed. With a gzip copy in place of each such file: 26,182,569 bytes.
- First screen (the files of the table "Files in data/" of `site/README.md`: `meta.json`, `cells.json`, `yearly.bin`, `open.bin`, `snowfree.bin`, `snowodds.bin`, `cloud.bin`, `flat.json`, `calendar.json`, `profile.json`, `sites.json`, `land.json`, `copy.json`): 28,391,024 bytes plain, 5,684,862 bytes compressed.
- `site/app.js` also asks at the start for `extras.json`, `moon.json`, `places.json`, `mars.json`, `sources.json`, `tools.json`, `airfields.json`, `access.bin` and `yearplan.json`: 606,422 bytes more, compressed (4,728,565 plain).

## Afternoon: the gaps of the texts

The agents that refreshed and checked the texts listed seven gaps. These steps closed them. No page code and no figure of a data file changed.

| Time | Step | Result |
|---|---|---|
| 13:05 | `data/SOURCES.md`: rows 61 (NASA's map of the nine lunar regions of 2024) and 62 (the USGS grid release of the 13 regions of 2022), credits AW and AX, the list "Not checked for rows 61 and 62", one line in each field of section 4. `NOTICE`: credits AW and AX | The two rows rest on the copies of `data/raw/lunar_regions_provenance/`. The USGS record gives 5 November 2024 as the publication date; our other files say 2 November 2024 |
| 13:06 | `scripts/export_site_extras.py` | `sources.json`: 62 rows and 50 credit lines; rows 1 to 60 the same as before; no problem reported |
| 13:06 | `scripts/apply_ste_text.py`, then `--check` | 88 sentences changed (the files that the exporter wrote again); then 0 would change, 0 entries match nothing |
| 13:06 | `scripts/compress_site_data.py` | 9 copies written |
| 13:08 | `scripts/build_submission.py` writes section 8c from `data/SOURCES.md`, section 3 (new function `credit_lines`). New script `scripts/write_readme_credits.py` writes the same lines between the marks of `README.md` | 50 credit lines, A to AX, in the order of the file |
| 13:10 | The three counts of measured northern areas (14,833, 14,830 and 14,834): one sentence for each in `RESULTS-FINAL.md`. The submission text, `README.md` and `docs/METHOD.md` use 14,833 with its sentence | The counts of areas with 100 hours are the same with each filter |
| 13:12 | `docs/METHOD.md`: one sentence at the start of sections 3 to 6, and a table of the 16 Sun ceilings and where spells of 2 hours start (section 2) | From `moon_targets.json` and `latitude_profile.json` |
| 13:15 | `docs/PUBLIC-COPY.md` and a new `.gitignore`; the scan of the public copy | See that file |

## For the page's README

`site/README.md` (table "Files in data/") still gives the layout of the first build with four lunar regions: `yearly.bin` "[cells, 4 targets, 12]" and `snowfree.bin`, `open.bin` "[cells, 4, 36]". The other coders replace that file later, thus this log does not change it. These rows give the layout that the page data of this build state:

| File | What |
|---|---|
| `yearly.bin` | uint16, little-endian, `[cells, 16 lunar regions, 12 fields]`, shape `[16184, 16, 12]` (`cells.json` → `yearly`). The field names are in `cells.json` under `yearly.fields`. Hours of the year, the winter half and the summer half are in tenths of an hour; scores are in thousandths; 65535 = unknown |
| `snowfree.bin`, `open.bin` | uint8 `[cells, 16 lunar regions, 36 ten-day periods]`, shape `[16184, 16, 36]` (`meta.json` → `encoding.bin_shape`). Hours in each ten-day period in half hours (`encoding.unit_h` 0.5), at most 254 (`encoding.cap`); 255 = unknown (`encoding.unknown`) |

- The lunar regions have the order of `meta.json` → `targets`: Connecting Ridge first, Peak near Cabeus B last, in the order of the Sun ceiling.
- `meta.json` → `encoding.capped_cell_periods` gives the count of values at the cap: 0 in `snowfree.bin` and 45 in `open.bin`.
- The file sizes agree: `yearly.bin` is 6,214,656 bytes (16,184 × 16 × 12 × 2), and `snowfree.bin` and `open.bin` are 9,321,984 bytes each (16,184 × 16 × 36).

## Not done

- No long lunar step ran again (hours, terrain, scores, validation, horizon step at 21 bins).
- `scripts/build_ground_cells.py` did not run: its three outputs come from the copy that changed them (see the table above).
- At 11:44, `SUBMISSION.md`, `README.md` and `scripts/build_submission.py` still named four lunar regions and five Mars sites. A later refresh brought them to 16 lunar regions and 57 Mars sites.
- The page code (`site/*.js`, `*.css`, `*.html`) did not change. The page was not looked at in a browser.

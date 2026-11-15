# Mars sites, second pass: work log

Times are Pacific time (PST), Sunday 15 November 2026.

- 09:25 Start. Read the heading of `data/derived/MARS-RESULTS.md`, the meta block of `data/derived/mars_sites_base.json` and the two first-pass download logs (`data/raw/mars_sites/_downloads_2026-11-15_new_sites.tsv`, `data/raw/mars_climate/mcd/_downloads_2026-11-15_new_sites.tsv`).
- 09:26 Read Table 1 of `data/raw/mars_sites/golombek2021_lpsc_2420.pdf` (pdftotext). Six new sites: AP-1, AP-9, EM-16, AP-8, EM-15, PM-7.
- 09:27 Copied `data/reference/mars_exploration_zones_2015.json` from the main project. 49 zones, 45 with `use: true`.
- 09:27 Distances from each zone to the 12 present sites (great circle, radius 3389.5 km). Zones at the same place (less than 50 km, the list file's own rule) as a present site are not added as a second site:
  - from `same_as`: 1011a (Erebus Montes) to `arcadia-planitia`, 1020 and 1022 to `gale`, 1033 to `deuteronilus-mensae`, 1034 to `jezero`;
  - not in `same_as`, because the list file was made before the first pass added these sites: 1008 (Gusev crater, 6 km) to `spirit`, 1019 (Chryse, Viking 1, 19 km) to `viking-1`.
  - 1044 (Deuteronilus Mensae debris apron) lies 124 km from `deuteronilus-mensae`. That is not the same place, so it is added.
- 09:27 The four zones with `use: false`: 1030 left out (the list file says the map circle is not a usable stand-in); 1040 goes to `gale` (latitude only; its map circle is the shared Gale circle '20, 22, 40'); 1049 left out (not on NASA's map); 1051 added with the centre of its circle on NASA's map (11.98 N, 313.94 E), which the list file does not mark as doubtful.
- 09:28 Kept copies of `mars_cells.json`, `mars_sites.json`, `mars_sites_base.json`, `mars_climate.json`, `mars_terrain.json`, `planet_factors.json`, `factor_matrix.json` and `MARS-RESULTS.md` in a scratch folder, for the comparison after the run.
- 09:28 Started the climate requests for 45 new sites: two workers, one request open per worker, a pause of 6 s between requests, three tries per site. Request as in the first pass (variables t, tsurf, ps; all Ls; all local times; 2 m; climatology dust scenario). Log: `data/raw/mars_climate/mcd/_downloads_2026-11-15_second_pass.tsv`.
- 09:39 All 45 climate requests answered on the first try (17 to 27 s each, not 70 to 90 s). Each table header gives the latitude and longitude that the request sent (checked for all 45). 90 lines in the log.
- 09:39 Wrote the records with the new script `scripts/add_mars_site_lists.py` (the first pass wrote the base file with a script outside the project). It starts again from the twelve earlier records each time. 57 sites: 12 earlier, 6 of the 2021 shortlist, 39 exploration zones (38 with `use: true`, and 1051 from NASA's map).
  - Earlier records: only the new fields `lists`, `exploration_zone_abstracts`, and a source line for abstracts 1020, 1022, 1040 (Gale), 1019 (Viking 1) and 1008 (Spirit). Names, positions, kinds and `why` are unchanged (checked against the kept copy).
  - The `why` of each zone is the list file's sentence with the changes that `handoff/ste-rules.md` asks for ("can" for "may" and "could", "thus" for "so", "give" for "supply", no "chosen", two short sentences for one long one).
- 09:40 `build_mars_terrain.py`: 57 sites, 81,776 squares, 123 s. The Earth squares and the twelve earlier sites are the same as in the kept copy.
- 09:42 `build_mars_climate.py build`: 39 s. The Earth squares and the twelve earlier sites are the same as in the kept copy.
- 09:43 `build_mars_cells.py`: 5 min 18 s, then it stopped at its own check of the report: one sentence of 141 words (the list of sites more than 23.44 degrees from the equator). Changed the sentence to give a count when more than six sites are in it, and gave the six 2021 sites short names (AP-1 and so on).
- 09:49 `build_mars_cells.py` again.
- 10:07 `build_mars_cells.py` finished (17 min 52 s: the computer was very busy, load average more than 250). Compared with the kept copy:
  - the same 12,984 squares; in each square the scores of the twelve earlier sites are the same, and the other fields of each square are the same;
  - `best_places`, `factor_summary`, `best_places_tied_at_top` and `counts` of the twelve earlier sites are the same;
  - in `mars_sites.json` the twelve earlier cards differ only in `lists`, `exploration_zone_abstracts` and (Gale, Viking 1, Spirit) `sources`.
- 10:08 `build_ground_cells.py` (133 s; it writes `mars_ground.json` with 57 sites), `build_mars_environment.py build` (86 s).
- 10:10 `build_planet_factors.py --offline` (5 s). The values of the twelve earlier sites are the same; only the counts in `meta.filled` differ.
- 10:10 `build_power_cells.py build` (97 s), then `build_factor_matrix.py` (117 s). The rows differ from the kept copy only in the site counts (12 to 57).
- 10:14 Page data. `export_site_mars.py`: size limit raised from 6,000,000 to 26,000,000 bytes, with a comment (the next step divides the file). mars.json 3,895,165 bytes, mars_squares.bin 19,411,080 bytes, mars_world.json 287,549 bytes; no warnings. `export_site_mars_extra.py`: 4,983,002 bytes in all (its own limit is 5,000,000). `export_site_factors.py`.
  - `export_site_mars.py` changed: a site with no summary of its `why` gives no warning (the page shows the warnings); `display_status` is the kind for an exploration zone; each card has `lists`.
- 10:17 `apply_ste_text.py` (602 sentences changed, 0 map entries matched nothing), then `split_mars_squares.py` (copied from the main project: 7 shared columns and 6 new ones, 285,648 bytes; 57 site files of 337,584 bytes each), then `compress_site_data.py` (copied from the main project: 90 files written; 55.1 MB of large files are 18.7 MB compressed).
- 10:18 The 187 columns of the twelve earlier sites and of the shared part in the new files are byte for byte the same as in the kept `mars_squares.bin` of the first pass.
- 10:20 `data/SOURCES.md`: rows 58 (workshop abstracts), 59 (NASA's map of the proposed zones), 60 (the 2021 abstract, the other six sites); credit lines AT, AU, AV; rows 23, 26 and 32 now name the 57 sites and the new climate log; a list "Not checked for rows 58 to 60". `NOTICE`: credit lines AT, AU, AV.

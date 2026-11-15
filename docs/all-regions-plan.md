# Plan: ten lunar regions (the nine of 2024 plus Connecting Ridge)

For the agent that adds the six missing regions. Written from the code of this copy on 15 November 2026. No code was changed.
Marks: **must** (the run fails or gives a wrong figure without it), **can wait** (the page works, a part stays at four regions or is less exact), **leave** (no change).
Paths are relative to the project folder. Work only in this copy. `data/raw` is shared with the main project: add files there, never change or delete one.

## 0. What the plan rests on

The six missing regions, by their names on the 2024 list (NTRS 20250011660, saved in `data/raw/moon_provenance/`):

| id (proposed) | Name | 5 m model on PGDA product 78 (from the saved page `pgda_product_78.html`) | Position: what the notes hold (NOT a source) | Ceiling, estimate only |
|---|---|---|---|---|
| `peak-near-cabeus-b` | Peak near Cabeus B | none of that name (`NPA: Cabeus exterior wall 1` is a different name) | no coordinate; "about 200 km from the pole" | approx. 8.1° (above the top edge 7.59°) |
| `haworth` | Haworth | `Haworth` | crater centre 86.9 S (search summary; the region is not the crater centre) | approx. 4.6° |
| `mons-mouton-plateau` | Mons Mouton Plateau | `Site20` or `Site20v2`: see the conflict below | LROC mosaic centre 84.3 S | approx. 7.2° |
| `nobile-rim-1` | Nobile Rim 1 | `Site06: Nobile rim 1` | LROC mosaic centre 85.4 S | approx. 6.1° (near the edge 6.11°) |
| `de-gerlache-rim-2` | de Gerlache Rim 2 | unclear: `Site11` and `SL2` are both named "de Gerlache rim" | approx. 88.3 to 88.5 S | approx. 3.0 to 3.2° |
| `slater-plain` | Slater Plain | none | 88.1 S from a low-reliability page | approx. 3.4° |

- Every ceiling above is 90 − |lat| + 1.54 at an unverified latitude. The real ceiling comes from the model centre (`moon.fingerprint`) or from a sourced position. Each position needs a source URL and a certainty note in the code and on the card.
- **Conflict to settle first.** The card text in `scripts/build_moon_cards.py` (`PROVENANCE["mons-mouton"]["name_note"]`) says the `Site20v2` area is most likely "Mons Mouton". The research note `target_sites.md` (section 2, inferences) says Leibnitz Beta Plateau was renamed "Mons Mouton Plateau". Both are inferences. The `Site20v2` centre (85.43 S, 31.74 E) lies inside both saved LROC footprints (`NAC_ROI_MTMOUTONLO1`: −86.07 to −84.82; `NAC_ROI_MOUTNPLTLO1`: −85.76 to −82.85), so the footprints do not settle it. Do not give one model to two regions.
- Use "candidate" and "studied" for the regions, never "selected" or "chosen".

## 1. Region definition (`twinfinder/moon.py`, `scripts/build_moon_fingerprints.py`)

1. **must** `twinfinder/moon.py` `Target`: make `pgda_site` optional (`None`); add `lat`, `lon_east`, `position_source`, `position_note` (how sure), and an optional sourced `box` (lat and lon ranges). `dem_url` returns `None` without a model. Append the six to `TARGETS`. Keep the list in order of ceiling, low to high: every array index follows this order. Write each `why` in STE (`handoff/ste-rules.md`), with "candidate".
2. **must** `twinfinder/moon.py`: add `fingerprint_without_model(target, illum_path, psr_path)` with the same keys as `fingerprint`: `source: None`, `terrain: None`, `extent_km: None`, `centre_lat/lon` from the sourced position, `sun_max_elev_deg` from it, `sun_max_elev_range_deg` from the box (else `[ceiling, ceiling]` with a note), `illumination_*` and `permanent_shadow_fraction` read with `read_scaled_window` inside the box (else `None`). Add `has_model: true/false` to both functions.
3. **must** `scripts/build_moon_fingerprints.py` `main()`: call `fingerprint` when `target.pgda_site` is set, else `fingerprint_without_model`. It fetches the new 5 m models from PGDA (approx. 40 to 100 MB each) into `data/raw`. The four present fingerprints come out the same.

## 2. Elevation edges (`twinfinder/sun.py`, `twinfinder/horizon.py`, `twinfinder/grazing.py`)

The edge list is typed three times: `twinfinder/sun.py:15`, `twinfinder/horizon.py:12`, `scripts/independent_recount.py:50` (`EDGES`). `grazing.check_shared_bins()` stops the build if the first two differ. A region uses the bins whose upper edge is at most its limit + 0.005 (`grazing.elev_bins`, `sun.bins_up_to`): a ceiling that is not an edge silently cuts the band at the edge below it.

4. **must** `twinfinder/sun.py` `ELEV_EDGES_DEG`: insert `round(ceiling, 2)` of each new region (`grazing.target_limit`). If a ceiling is above 7.59, it becomes the new top edge. Up to 15 bins.
5. **must** `twinfinder/grazing.py` `load_targets()`: stop with a clear message if a limit is not an edge (within `LIMIT_SLACK_DEG`).
6. **must** `twinfinder/horizon.py`: set `ELEV_EDGES_DEG = sun.ELEV_EDGES_DEG`; keep the old ten edges as `STORED_EDGES_DEG` (the edges of every record in `data/derived/horizon_cells.json`); add `share_on_edges(share, from_edges, to_edges)`: each new bin takes the open share of the stored bin that holds its lower edge.
   - Why this is safe: the stored share of a bin is the share of land pixels whose skyline is below the bin's LOWER edge (`horizon.open_share`). A split bin [a, c] keeps lower edge a: exact. The upper part [c, b] gets the share at a, as the whole bin [a, b] has now. Thus the four present regions keep exactly their present open hours, and a new region is exact if the bin under its ceiling starts at an old edge.
   - Not exact (a lower bound): a new region whose top bin starts at another new ceiling (probably Slater Plain above de Gerlache Rim 2, both in [3.0, 4.0]); and any bin above 7.59 (probably Peak near Cabeus B), which gets the share of [6.11, 7.59]. Write this into `grazing_cells.json` `meta` and on the page.
   - The per-pixel skyline is not stored (only `open_share` [36, 9], `north_deg`, `south_deg`, `valid_share`, `pixel_m`). Exact shares at new lower edges need the elevation tiles again (step 8).
7. **must** `twinfinder/grazing.py` `horizons_of_cells()`: apply `share_on_edges` when `share.shape[1] == len(STORED_EDGES_DEG) - 1`. Every reader goes through it: `build_grazing_cells`, `cell_inputs` / `long_window_hours_by_bin` (`validate`, `build_ground_cells`, `export_site_planner`), `build_validation_extras`, `build_winter_leads`. `export_site_planner.skyline_bytes()` checks the shape against the new edge count and writes all 255 without this step.
8. **can wait** `scripts/build_horizon_cells.py`: exact shares at the new edges. The GLO-90 tiles are on disk (`data/raw/glo90`, 7,368 files, 4.6 GB): use `--cached-only`. `record()` must store `elev_edges`; cells already stored are skipped, so add a switch to redo them. `build_winter_leads` and `build_sunpath_demo` also call `horizon.cell_open_share` and get the new edges. Time not measured: approx. 12 to 95 minutes (`docs/REPRODUCE.md` gives "about 0.35 s an area on eight workers", which can be per worker or per area).
9. **can wait** `scripts/independent_recount.py` (`EDGES`, `one_calendar`, `recompute`): the same edges and the same `share_on_edges`, or it compares wrong bins.

## 3. Slope likeness and ground shape: only with a model

10. **must** `scripts/build_terrain_cells.py` `main()` (l.149): build `target_hists` only for targets with `terrain`. `needs_terrain()` must also be true when the stored `overlap` lacks a modelled target id. The Earth slope histograms are not stored, thus the overlap needs the tiles again (`--cached-only`). Not timed; estimate 3 to 6 minutes.
11. **must** `scripts/score_cells.py` `main()` (l.492) and `scripts/validate.py` `main()` (l.507): read `self_overlap_10km` with `.get`, so a region without a model gives `None`. `score.terrain_score` then gives `None`, and the goals "shadows", "geology", "full" are `None` for that region (`score.goal_scores`): its lists for those goals are empty, never zero. "lighting" works in full.
12. **must** `scripts/build_ground_cells.py` `lunar_regions()` (l.147): skip a target without a model; write a record with null figures and the reason. `roughness_vs_region` is then null for it. The terrain-shadow shares need only the hours and run for all ten.
13. **must** `scripts/build_moon_cards.py`: add six `PROVENANCE` entries (`official_name`, `name_note`, `nasa_list` with `on_2022_list_of_13`/`on_2024_list_of_9`, `why_check`, `pgda_model` or `None`, `picture`); `build_card()` must accept `pgda_model: None`; `diviner_for_target()` uses `target_bounds()` (centre and `extent_km`): give it the sourced box, else return `EMPTY_DIVINER`. `export_site_extras.moon_cards()` raises if a card is missing.

**A region without a 5 m model.** Counted in full: the Sun ceiling (latitude only), the hours over a flat horizon, on snow-free ground, after the Earth hills and under cloud (they need only the ceiling), the latitude profile, the calendar, the planner and the "lighting" lists. Need only a position box (no model), because the maps cover the pole: sunlight share and permanent shadow (`AVGVISIB_65S_240M`, `LPSR_65S_240M`, 65 to 90 S) and the Diviner figures (`dlre_prp_south.tab`, pole to 80 S); without a sourced box they are null. Need the model: slope likeness, the self-overlap, roughness and landform (`ground_moon.json`), the Diviner `altitude_check`, the card line "our terrain model is X km across". PGDA product 90 (polar slope maps at 20 to 80 m) is a different product and baseline: do not use it for slope likeness tonight. Every field the model gives is `null` / "unknown" on the page, never 0.

## 4. Typed lists of four and typed text

14. **must** `scripts/make_results.py`: `SHORT` (l.179) from the target names (it raises `KeyError` for a new id at l.588); the comparisons with the kept v1 and v2 files (`light_cells_v1.json`, `validation_v2.json`, `cells_scored_v2.json`) only for ids in those files; the Nobile Rim 2 text at l.655 to 663 and l.1305 for each region whose two-hour belt starts south of 59°.
15. **must** `scripts/validate.py` `old_against_new()` (l.414): `OLD_EXPECTED` and `old_usable_counts()` only for the four ids in `light_cells_v1.json`.
16. **must** `scripts/export_site.py`: `SHORT_NAMES` (l.46) as fallback only; `SOURCES` text "the four lunar sites, and their slopes" (l.54) and the scale text (l.943) without a typed count; add `has_model`, `position_source` and `position_note` to `meta.targets` (built at l.886 to 900).
17. **must** typed "four" in sentences: `scripts/build_factor_matrix.py:258`, `scripts/build_ground_cells.py:170`, `site/index.html:357`. Write the count from the data, or no count.
18. **can wait** `scripts/build_submission.py`: `TARGETS`, `HIGHER` (l.68 to 69) and the short-name tuples (l.282, 315, 365, 397). It runs, but `SUBMISSION.md` stays a four-region text.
19. **can wait** `scripts/check_against_horizons.py` `TARGETS` (l.42): the check reads saved answers only.
20. **leave** `scripts/build_sunpath_demo.py` (`LUNAR_IDS`, Malapert and Connecting Ridge), `scripts/export_site_extras.py` `LUNAR_SITE`, `scripts/build_environment_cells.py` `TARGET = "malapert"`, the fallback list in `scripts/export_site_factors.py:699`, `scripts/export_site_tools.py:816`, the defaults in `site/*-dev.html`.

## 5. Stored files with a dimension of regions (all in `data/derived`)

| File | Region dimension | Written by | Ten regions |
|---|---|---|---|
| `moon_targets.json` | list of 4 | `build_moon_fingerprints` | must |
| `grazing_bins.npz` | `flat`, `snow_free`, `open`, `stretch`, `long_*`: [16184, 4, 36]; `targets` [4] | `build_grazing_cells` | must |
| `grazing_cells.json` | `cells[].targets{}`, `meta.targets` | `build_grazing_cells` | must |
| `candidates.json` | top cells per target | `build_candidates` | must (run it AFTER `build_grazing_cells`: step 1 of `rebuild_all` reads the old cells file) |
| `terrain_cells.json` | `overlap{}` | `build_terrain_cells` | must (modelled regions) |
| `cells_scored.json`, `ranking.txt` | `cells[].targets{}`, `terrain.overlap{}`, `meta.targets` | `score_cells` | must |
| `latitude_profile.json` | `meta.targets`, `profile[].targets{}`, `thresholds{}` | `build_latitude_profile` | must |
| `temperature_cells.json` | `meta.named_places.places[].best_bins_by_target{}` | `build_temperature_cells` | must |
| `validation.json` | `regions`, `stability`, `named_sites`, `haughton_july`, `big_picture_north`, `old_against_new` | `validate` | must |
| `snow_validation_many.json` | `headline.counts.*{}` | `validate_snow_many` | must |
| `moon_cards.json` | `cards[4]` | `build_moon_cards` | must |
| `validation_extras.json` | `known_sites`, `latitude_against_full_method` | `build_validation_extras` | must |
| `winter_leads.json` | `meta.targets`, `targets{}`, `floors.*.targets{}` | `build_winter_leads` | must |
| `ground_moon.json`, `ground_cells.json` | `regions{}`; `roughness_vs_region{}`, `shadow.*{}` | `build_ground_cells` | must for the factor module |
| `power_cells.json` | `cells.*.low_sun{}` | `build_power_cells build` | can wait (the power fields of the six stay unknown) |
| `planet_factors.json` | `factors[].moon{}` | `build_planet_factors` | can wait |
| `checks.json` | `independent_recount.calendar_moved.targets{}` | `independent_recount`, `check_against_horizons` | can wait |
| `sunpath_demo.json` | two typed ids | `build_sunpath_demo` | leave |
| `*_v1*`, `*_v2*`, `count_check_v3.json`, `light_cells_v1.json` | kept old versions | no script | leave (never rewrite) |
| `horizon_cells.json` | no region axis; [36, 9] elevation bins of the OLD edges | `build_horizon_cells` | leave (step 7), or step 8 |

## 6. Run order and times

Times of the run of 14 November 2026. No log was kept: each time is the gap between the write times of successive output files in the main project's `data/derived`; the total, 2,259 s, is in the docstring of `scripts/rebuild_all.py`. Estimates for ten regions: approximately 2.5 times the work in each step that loops over the regions, and up to 1.6 times more for 15 elevation bins instead of 9 (`sun._add_minutes` loops over the bins).

| # | Step | 14 Nov | Ten regions | Again? |
|---|---|---|---|---|
| pre | `build_moon_fingerprints` | not timed | 2 to 5 min + downloads | must |
| pre | `build_terrain_cells --cached-only` | not timed | 3 to 6 min (estimate) | must |
| 1 | `build_candidates` | approx. 2 s | under 1 min | must, after step 2 |
| 2 | `build_grazing_cells` | 357 s | 15 to 24 min | must |
| 3 | `build_latitude_profile` | 1,139 s | 47 to 76 min | must; inputs: Sun and `moon_targets.json` only |
| 4 | `build_cloud_cells --offline` | approx. 1 s | approx. 1 s | leave (no region axis); it is in the chain anyway |
| 5 | `score_cells` | 86 s | 4 to 6 min | must |
| 6 | `build_temperature_cells --offline` | 5 s | under 1 min | must |
| 7 | `validate` | 363 s | 15 to 24 min | must |
| 8 | `validate_snow_many --offline` | 46 s | approx. 2 min | must |
| 9 | `build_moon_cards` | 2 s | seconds | must |
| 10 | `build_validation_extras` | 131 s | 5 to 9 min | must (reads the profile) |
| 11 | `check_known_analogs` | 1 s | seconds | must |
| 12 | `build_sunpath_demo` | 3 s | seconds | leave (in the chain anyway) |
| 13 | `build_winter_leads --cached-only` | 114 s | 5 to 8 min | must |
| 14 | `build_access_cells --offline --report` | 1 s | seconds | must (report per region) |
| 15-18 | `make_results`, `export_site`, `export_site_extras`, `build_submission` | approx. 8 s together (least sure: those files were written again later) | 1 to 3 min | must, must, must, can wait |
| post | `build_ground_cells` | 222 s (`ground_cells.json` meta) | 4 to 8 min | must |
| post | `build_power_cells build`, `build_factor_matrix` | not timed | 2 to 6 min (estimate) | can wait, must |
| post | `export_site_tools`, `export_site_factors`, `export_site_environment`, `export_site_extra` | not timed | 1 to 3 min each (estimate) | must |
| post | `export_site_planner` | approx. 5 min (`docs/REPRODUCE.md`) | 12 to 20 min | must |
| post | `apply_ste_text` | seconds | seconds | must, LAST |
| check | `independent_recount --shift 0.14` | 415.5 s (`checks.json`) | 17 to 28 min | can wait |
| check | `check_against_horizons` | not timed | not known | can wait |

Order (each from the project folder with `uv run python`):
1. The code changes of sections 1 to 4. Then `scripts/build_moon_fingerprints.py` and `scripts/build_terrain_cells.py --cached-only`.
2. Start `scripts/build_latitude_profile.py` in the background (it reads no other step's file).
3. In the foreground: `build_grazing_cells`, `build_candidates`, `build_cloud_cells --offline`, `score_cells`, `build_temperature_cells --offline`, `validate`, `validate_snow_many --offline`, `build_moon_cards`.
4. When the profile is done: `scripts/rebuild_all.py --skip-profile --from build_validation_extras`.
5. `build_ground_cells`, `build_factor_matrix`, then `export_site_tools`, `export_site_planner`, `export_site_factors`, `export_site_environment`, `export_site_extra`, then `scripts/apply_ste_text.py`.

Expected total: approximately 1.5 to 2.5 hours of computer time with the profile in parallel (approximately 2.5 to 3.5 hours one after the other), plus the code work. Step 8 of section 2 adds 12 to 95 minutes. Memory: the long-spell tables of the profile grow from approximately 0.2 GB to approximately 0.85 GB.

## 7. The page (`site/`)

The page and its modules read the region list, the count and the order from the data: `D.meta.targets`, `D.nt`, `api.targets`, `index.targets` (planner), `manifest.targets` (sky), `planner.targets` (ask), `meta.region_names` (factors), `elevation_bin_edges_deg` in `planner.json` (sky). The order of every per-region array is the order of `meta.targets`.

21. **must** context bar: `site/app.js` `renderBar()` (l.758) makes one button per region; `site/style.css` l.104 to 106 (`flex-wrap: nowrap`, `white-space: nowrap`), l.298 to 302 (bottom bar, `flex: 1 1 0`) and l.767 to 773. Ten buttons do not fit on one row; at 375 px each button is approx. 30 px wide. Let the buttons wrap on two rows, or use one select menu at 560 px or less.
22. **must** `site/app.js` l.984 to 986: the calendar comparison names `connecting-ridge` (hardest) and `nobile-rim-2` (easiest). Find the easiest from the highest `limit_deg`, as `hardest()` (l.64) does.
23. **must** `site/app.js` `moonCardHtml()` (l.1963 to 2003): "our terrain model is X km across" only when the card has a model; else give the source of the position and how sure it is. Slope rows say "unknown".
24. **must** `site/app.js` `answerLunarRows()` (l.2078, "The best places on Earth"): the row "Most Moon-like ground" disappears when `top.north_full` is empty. Add a note row, for example: "Most Moon-like ground: no slope figure. NASA gives no 5 m terrain model of this lunar region."
25. **can wait** destination picker `renderShell()` (l.2792, `#picker-moon`): ten chips; examine at phone width; possibly two groups, "nine candidate regions of 2024" and "2022 list".
26. **can wait** `#sun-cards` (l.839 to 860, two columns in `style.css` l.142): ten cards. The short lists (`renderTabs()`, l.2178): data-driven; the lists "With rock that also matches" are empty for a region without a model.
27. **can wait** colour scale: `export_site.py` l.929 to 945 takes the 0.99 quantile over all regions. Higher ceilings raise its top, thus the maps of the four present regions become paler. Decide: keep, or a scale per region.
28. **leave** `globes.js`, `planner.js`, `tools.js`, `sky.js`, `ask.js`, `extra.js`, `factors.js`, `env.js`. Examine only that a region without slope figures shows "unknown".

Files that grow (n = 16,184 areas, T regions; 4 now, 10 after):

| File | Layout | 4 regions | 10 regions |
|---|---|---|---|
| `snowfree.bin`, `open.bin` | uint8 [n, T, 36] | 2,330,496 each | 5,826,240 each |
| `yearly.bin` | uint16 [n, T, 12] | 1,553,664 | 3,884,160 |
| `rehearsal.bin` | n·T·(2 + 1 + 4) | 453,152 | 1,132,880 |
| `rose.bin` | uint8 [n, T, 37] | 2,395,232 | 5,988,080 |
| `factors.bin` | 5 bytes per area and region (shadow share u8, low-Sun hours u16, roughness ratio u16) | 2,023,000 | approx. 2,508,520 |
| `extra.bin` | `power.low_sun.<region>.*`: 7 bytes per area and region | 3,269,168 | approx. 3,948,896 |
| `skyline.bin` | uint8 [n, 36]: no region axis, but its codes count the elevation bins | 582,624 | 582,624 (codes up to 15) |

The JSON files with a block per region grow approximately 2.5 times: `meta.json`, `calendar.json`, `flat.json` (209 KB), `sites.json`, `moon.json`, `yearplan.json`, `famous.json`, `validation.json`, `profile.json`, `winter_leads.json`, `extras.json`. `site/data` grows from approximately 32 MB to approximately 48 MB. `search.json` has a limit of 300,000 bytes but no region axis.

## 8. Wording maps (`data/reference/ste/`)

29. **must** run `uv run python scripts/apply_ste_text.py --check`, then without `--check`, AFTER the last export. `rebuild_all.py` does not run it, thus after its export steps the page holds the build scripts' wording again. Today `--check` reports 0 changes and 0 stale entries.
30. **must** sentences with a count or a number of regions ("four", hours, ceilings) stop matching after the rebuild; `--check` counts them as "matched nothing". Bring those entries up to date in `moon.json`, `zz-reader.json` and `factors.json` of that folder.
31. **must** write every new sentence in STE at its source (`moon.TARGETS` `why`, `PROVENANCE` in `build_moon_cards.py`, the notes of `fingerprint_without_model`), so that no map entry is necessary for it.

## 9. Not in the plan

The grid of areas stays as it is (59° and more). The two-hour spells of a ceiling near 8° start south of 57.65° (the start for Nobile Rim 2), thus a larger part of that region's Earth band is outside the search; the page and `RESULTS.md` must say so.

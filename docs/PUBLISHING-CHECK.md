# What may go public: a check before the first push

Updated late on Saturday 14 November 2026, after the final Moon run, the Mars first pass and the factor files.
Updated again on Sunday 15 November 2026 for the joined build: 16 lunar regions and 57 Mars sites (`docs/final-join-log.md`). The open points stay open.
Updated in the afternoon of 15 November 2026: `docs/PUBLIC-COPY.md` now gives the files of the public copy, their sizes and the scan. Where this file and that file give a different list of files, `docs/PUBLIC-COPY.md` and `.gitignore` are correct.
Nothing is published yet. There is no public repository yet, and the folder is not a git repository.
This check changed no code, no data and no page. Sizes are those of the check; files may change after it.

## For the team lead to decide or do

1. **The Local Event cut-off.** The form closes on Sunday 15 November 2026 at 23:59 local event time, but a Local Event may close earlier.
   Check the Local Event page, or ask the Local Lead, tonight. Save an eligible draft early on Sunday and keep overwriting it.
2. **The "all work is original" tick box.** The form asks the team to confirm that all work is original and that every outside resource is listed.
   - `data/SOURCES.md` now lists the sources of the Mars part, the new factors and the new Mars sites (rows 23 to 60, credit lines R to AV). Rows 61 and 62 (credit lines AW and AX) list NASA's map of the nine lunar regions of 2024, the source of the position of three regions, and the USGS grid release of the 13 regions of 2022.
   - No code, wording or image may be copied from another team.
   - AI use must be acknowledged: see item 3.
3. **The rule on AI and the idea.** The 2026 guide says AI ("SI") should not be used to come up with the idea of how to solve the challenge.
   The "How AI was used" section of `README.md` says the assistant proposed directions. Write truthfully, in your own words, which parts of the idea the team decided. Do not remove what the assistant did.
4. **The Smithsonian volcano list.** Its terms were read on 14 November 2026. They allow non-commercial use with the citation and a link (section 4).
5. **The Mars Climate Database** asks that its authors be kept informed. The project now has its values for 57 sites (57 requests in all, the last 45 on 15 November 2026). Decide whether and how to tell them (section 4).
6. **The COMNAP station fields.** Keep them on the page with the credit and the non-commercial wording, or strip the station names. Still open.
7. **The result files that the repository does not hold, and the saved Horizons answers.** Decide how to offer them (`docs/PUBLIC-COPY.md`, section 4, advises one archive on a release). Then fill in `[LINK TO THE LARGE RESULT FILES]` in `README.md` and `docs/REPRODUCE.md`.
8. **Two new folders:** `handoff/` and `candidates/`. `.gitignore` now keeps them out (`docs/PUBLIC-COPY.md`, section 2).
9. **Names.** Fill in the team and member names where the texts leave blanks. Then search every file for each member's name.
10. **No NASA logo**, insignia or mission patch in the repository, the page or the slides.
11. **The abstracts of NASA's 2015 workshop** on human landing sites on Mars are (c) their authors. We take only names, positions and one sentence of our own words for each zone. The saved PDFs stay in `data/raw/`, which is never published (section 4).

## 1. What must never be published

| Folder or file | Size | Why |
|---|---|---|
| `data/raw/` (all of it) | about 12 GB | Too large, and parts are not ours to share. `.gitignore` keeps it out. Keep it that way. |
| `data/raw/antarctica/comnap_facilities/` (the raw COMNAP station file) | small | COMNAP's terms allow educational and non-commercial use only, and COMNAP holds its copyright. |
| Saved papers and web pages: `data/raw/mars_sites/` (with the 2015 workshop abstracts in `ezworkshop2015/`, approximately 60 MB, (c) their authors), `planet_factors/`, `moon_provenance/`, `lunar_regions_provenance/`, `additions_check_links/`, `estimates/` | more than 190 MB | Copies of other people's pages and papers, kept as evidence of what was read. |
| The 13 lunar terrain models in `data/raw/` | approximately 892 MB | Site20v2 and Haworth are over GitHub's limit of 100 MiB. NASA material, but too large to commit. |
| `data/raw/mars_climate/mcd/` (Mars Climate Database answers of the 57 sites) | a few MB | Scientific, non-commercial use only. |
| `data/raw/analog_catalogues/` | 12 MB | A third-party copy of a PDF with no licence. |
| Scouting downloads under `data/raw/antarctica/` that no script uses | part of 134 MB | Their terms were not checked. |
| `data/derived/horizon_cells_partial.json`, `terrain_cells_partial.json`, `snow_free_dekads_v1.npz`, `terrain_cells_v1.json` | about 33 MB | Half-finished or superseded; no script reads them. `.gitignore` leaves them out. |
| `.venv/`, `__pycache__/`, `.pytest_cache/`, `.claude/` | large | Local environment, caches and settings. |

One part of `data/raw/` may be worth publishing on purpose: `data/raw/horizons_check/` (7.8 MB, 36 JPL Horizons answers).
Without it the Horizons check cannot be rerun, and one test fails. To publish it, change the `data/raw/` line of `.gitignore` to `data/raw/*` and add `!data/raw/horizons_check/`. Credit line C covers it.

## 2. The working notes stay private

| Folder | Decision | Why |
|---|---|---|
| `research_notes/` | **Keep private** (in `.gitignore`) | Early notes with claims later corrected, and a survey of other teams with links to their unfinished work. |
| `reports/` | **Keep private** (in `.gitignore`) | The first morning's research, overturned in parts, and our judgments of other teams. |
| `docs/superpowers/` | **Keep private** (in `.gitignore`) | Plans and a design file written by the AI assistant to the team lead. |
| `handoff/` (76 KB) | **Keep private** (in `.gitignore` since 15 November 2026) | Written task sheets, apparently those the second AI tool worked from. They are working notes. |
| `candidates/` (62 MB) | **Keep private** (in `.gitignore` since 15 November 2026) | A working folder of the main project. Not read by this check. |
| `SUBMISSION.md`, `docs/submission_template.md`, `demo/` | **Team decides** | Notes to the team stand beside the form text. Read them before publishing. |

To publish a private folder after cleaning it, delete its line in `.gitignore`.

## 3. What the repository should hold

| Folder or file | Size | Decision | Why |
|---|---|---|---|
| `twinfinder/`, `scripts/`, `tests/` | about 3.5 MB | Publish | The code and its tests. Apache 2.0. |
| `site/` | approximately 123 MB on 15 November 2026 (`site/data`: 87 MB of plain files and 26 MB of gzip copies) | Publish, after items 4 to 6 above | The page and its data. It asks no other host for anything, except the optional AI models on the visitor's own computer (localhost). |
| `README.md`, `LICENSE`, `NOTICE`, `.gitignore`, `pyproject.toml`, `uv.lock` | small | Publish | The Space Apps terms ask for licence documents. |
| `docs/METHOD.md`, `docs/REPRODUCE.md`, `docs/PUBLISHING-CHECK.md` | small | Publish | This file may also be left out; it holds no secret. |
| `data/SOURCES.md` | 28 KB | Publish, after it gains the new sources | Sources, licences and credit lines. |
| `data/reference/` | 120 KB | Publish, after item 6 | Two lists are CC BY-SA 4.0; two files hold COMNAP fields. |
| `data/derived/`, 25 result files | approximately 25 MB on 15 November 2026 | Publish, after items 4 and 5 | `docs/PUBLIC-COPY.md`, section 4, names them. `.gitignore` lets only these files in. |
| `data/derived/`, the other 46 files | approximately 1.2 GB on 15 November 2026 | Not in the repository; one archive (item 7) | `cells_scored.json` (approximately 271 MB), `mars_cells.json` (approximately 235 MB) and `grazing_cells.json` (approximately 160 MB) are over GitHub's limit of 100 MiB. The scripts make 42 of them again; the other 4 are half-finished or old. |

**The files that the repository does not hold.** `RESULTS.md` names `cells_scored.json` and `grazing_cells.json` as the source of most numbers, and the tests read them. Thus a reader must be able to get them.
`docs/PUBLIC-COPY.md`, section 4, gives the advice: one archive of all of `data/derived/` (approximately 164 MB as gzip) and the Horizons answers, on a release of the repository.
The other two ways stay possible: gzip copies in the repository (each is less than 25 MB, but the scripts read the plain files), or no copy at all (then `README.md` must say that the files must be rebuilt).

**The Mars files** are in `data/derived/` (with 57 sites, `mars_cells.json` alone is approximately 235 MB). They depend on items 4, 5 and 11. Only `mars_sites.json` and `mars_sites_base.json` go in the repository.

**The AI note in data files.** The guide asks that AI-made code and data say so in their text and metadata. Code files carry a header.
Only 2 of the 60 JSON and Markdown files in `data/derived/` carry an AI note, and 4 of the 34 JSON files in `site/data/`. `RESULTS.md`, `MARS-RESULTS.md` and `site/data/meta.json` do not.
Add the note at their next build. Do not edit `grazing_cells.json` or `grazing_bins.npz` by hand: `checks.json` records their sha256.

## 4. Terms a person must settle

| Source | Used in | What is open |
|---|---|---|
| Smithsonian Global Volcanism Program, volcano and eruption lists | `hazards_people_cells.json`, `steady_effects_cells.json`, `power_cells.json` and their Mars twins; the page's volcano and geothermal figures | **Terms read in a browser on 14 November 2026.** They allow personal, educational and other non-commercial use. The source must be cited and linked. Commercial use needs written permission. The citation is credit AB in `data/SOURCES.md`. |
| Mars Climate Database v6.2 (LMD, with LATMOS, the Open University, IAA, ESA and CNES) | `mars_climate.json`, `mars_sites.json`, `planet_factors.json`; the Mars section; now the model climate of 57 sites | Scientific use is allowed if the origin is quoted **and the authors are kept informed**. No commercial use without permission. The web interface is for moderate use only. Telling the authors is the team lead's decision. |
| Abstracts of the First Landing Site/Exploration Zone Workshop for Human Missions to the Surface of Mars (2015) | `data/reference/mars_exploration_zones_2015.json`, `mars_sites_base.json`, `mars_sites.json`, `site/data/mars.json` | (c) their authors, published by the Lunar and Planetary Institute. No licence page opened. We take only names, positions and one sentence of our own words for each zone. Credit AT. |
| Golombek and others (2021), LPSC abstract 2420 | the six other sites of the 2021 shortlist | (c) its authors. We copy positions and short facts only. Credit AV. |
| COMNAP Antarctic Facilities list | `data/reference/antarctic_sites.json`, `known_analogs_check.json`, `site/data/places.json` | Educational and non-commercial use only. The Space Apps terms ask that outside material be free of restriction or open-source. Item 6. |
| Curiosity weather feed (NASA) | the measured figures at Gale crater | NASA's feed says it is for outreach, not archive data. Say so where the figures appear. |
| NOAA NCEI ETOPO 2022 | `mars_terrain.json` | The terms were not recorded. Check them and add a credit line. |
| Open-Meteo | `second_opinion_snow.json` | Data CC BY 4.0; the free service is for non-commercial use. |
| GeoNames (CC BY 4.0); GLiM and the permafrost map of Obu and others (CC BY 3.0); WRI Global Power Plant Database (CC BY 4.0) | the new factor files | Open, but each needs its credit line in `data/SOURCES.md`, `NOTICE` and the page. |
| USGS ComCat; Natural Earth roads and railways | the new factor files | Public domain. A credit line is still good practice. |
| MOLA MEGDR (NASA Planetary Data System) | `mars_terrain.json` | Cite the data set. |

`data/SOURCES.md` now lists these sources (section 1b and rows 57 to 60). Their terms are also recorded in the `meta` block of each file named.

## 5. The event's rules

- **The Local Event cut-off** may be earlier than 23:59 on Sunday. See item 1.
- **"All work is original."** Every outside resource listed; no other team's code, words or images. See item 2.
- **AI.** Acknowledge AI-made code and data in text and in metadata. Word the idea's origin truthfully. See item 3.
- **No NASA logo**, insignia or mission patch anywhere. No wording that suggests NASA, ESA, the European Union or any provider endorses the work.

## 6. The scan

Done at the time of this check, over every file outside `data/raw/`, `.venv/`, the caches and `.claude/`, with `.npz` and `.bin` files left out.

- **Computer paths** (`/Users/`, `/private/tmp`, `/home/`, `/var/folders`): none found.
- **The user name of this computer's home folder:** none found in the files of the public copy. The scan of 15 November 2026 (`docs/PUBLIC-COPY.md`, section 5) found it in nine files of the working notes, in computer paths.
- **Email addresses:** none found (`uv.lock` left out).
- **Names of team members:** not searched; this check does not know them. Item 9.
- **Keys, tokens and passwords:** not searched again in this round. The earlier round found none.

## 7. Before the first push

1. Fill in every placeholder in square brackets. To list them: `grep -rn "\[[A-Z][A-Z ,:'-]*\]" README.md NOTICE docs/*.md`.
2. Run the path search again from the top folder. It must print nothing for files that will be published:
   `grep -rnE "/Users/|/private/tmp|/home/[a-z]" --exclude-dir=.venv --exclude-dir=raw --exclude-dir=__pycache__ --exclude-dir=.pytest_cache --exclude-dir=research_notes --exclude-dir=reports --exclude-dir=superpowers --exclude=PUBLISHING-CHECK.md --exclude="test_*.py" .`
3. Run the email search the same way, with the pattern `[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.[A-Za-z]{2,}`. Skip the `.npz` and `.bin` files, which give chance matches.
4. Search for each team member's name.
5. After `git add`, read the list of files to be committed. Check that nothing under `data/raw/` is in it (except `horizons_check/`, if item 7 chose it) and that no file is over 50 MB.
6. Open the page and the repository in a private browser window, logged out.
7. Check that no NASA logo, insignia or mission patch is in the repository, the page or the slides.

## 8. What this check did not do

- It did not read the working notes, `handoff/`, `candidates/`, `SUBMISSION.md` or `demo/` line by line. It searched them by pattern.
- It did not open any licence page or make any web request. The terms above are as the files' `meta` blocks record them.
- It did not run the tests or open the page.
- It did not look inside `data/raw/`, because that folder is never published.
- It did not change `.gitignore`, `data/SOURCES.md`, `NOTICE` or any code.

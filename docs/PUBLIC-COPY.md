# The public copy: what goes in, what stays out

Written on Sunday 15 November 2026 for the joined build (16 lunar regions, 57 Mars sites).
The team lead published this copy on 15 November 2026: https://github.com/1004genre/nasalunarbase-26. The text below is the plan that the team used. This file prepares the public copy, so that it takes approximately five minutes when the team decides.
`.gitignore` agrees with this file. `docs/PUBLISHING-CHECK.md` gives the terms of the sources and the open decisions.
The sizes are in bytes, measured on 15 November 2026 in this folder. A later build changes them.

## 1. What the public repository holds

| Folder or file | Files | Size | What it is |
|---|---|---|---|
| `site/` | 261 | 123,244,455 | The page: the HTML, CSS and JavaScript files, `site/README.md`, the page data in `site/data/` and the vendor folder `site/vendor/` |
| `site/data/` (part of `site/`) | 219 | 113,307,369 | The page data: 110 plain files and 109 gzip copies (25,945,986 bytes). The page reads a gzip copy in place of its plain file |
| `site/vendor/` (part of `site/`) | 8 | 9,006,057 | globe.gl with three.js, their two licence files, the three globe images and two notes |
| `data/derived/` (25 files only) | 25 | 24,549,570 | The result files that the documents link to, and the files that no script can make again (section 4) |
| `scripts/` | 59 | approximately 1.9 MB | The pipeline scripts. Apache 2.0 |
| `tests/` | 51 | approximately 1.1 MB | The tests. Apache 2.0 |
| `data/reference/` | 10 | 766,016 | The hand-made lists, the list of lunar regions and the wording maps of the page (`ste/`) |
| `twinfinder/` | 26 | approximately 0.3 MB | The Python package of the pipeline. Apache 2.0 |
| `docs/` (without `docs/superpowers/`) | 9 | approximately 0.2 MB | `METHOD.md`, `REPRODUCE.md`, `PUBLISHING-CHECK.md`, this file, the three logs of 15 November, `all-regions-plan.md` and `submission_template.md` |
| `data/SOURCES.md` | 1 | approximately 0.09 MB | Each source, its licence and its credit line |
| `README.md`, `LICENSE`, `NOTICE` | 3 | approximately 0.08 MB | The front page and the licence files |
| `SUBMISSION.md`, `demo/` | 3 | approximately 0.17 MB | The text of the form and the outline of the demo. The team decides (section 2) |
| `.gitignore`, `pyproject.toml`, `uv.lock` | 3 | approximately 0.02 MB | The rules of this file, and the Python project with its fixed package versions |

## 2. What must not be in it, and why

| Folder or file | Why |
|---|---|
| `data/raw/` (approximately 12 GB) | Too large, and parts are not ours to share: copies of papers and web pages, the Mars Climate Database answers, the Smithsonian lists. In this copy, `data/raw` is a link to the downloads of the main project, and the link holds a computer path with a user name. Git does not match a link with `data/raw/`, thus `.gitignore` has two lines: `data/raw` and `data/raw/` |
| The raw file of the COMNAP list (`data/raw/antarctica/comnap_facilities/`) | COMNAP holds the copyright. Its terms permit educational and non-commercial use only. Our files keep only the station names, status and distances, with credit L |
| `research_notes/` | Early notes with claims that we corrected later, and a survey of other teams with links to their unfinished work. Eight of its files hold a computer path with a user name |
| `reports/` | The research of the first morning, wrong in parts, and our judgments of other teams. This copy does not have the folder; the main project has it |
| `docs/superpowers/` | Plans and a design file that the AI assistant wrote for the team lead. One plan holds a computer path with a user name. Some code comments name a plan in this folder (`scripts/build_mars_*.py`, `twinfinder/mars_*.py`); a comment does not need the file |
| `handoff/` | The task sheets for the second AI tool, and the writing rules. They are working notes, not part of the product |
| `variants/`, `candidates/`, `test-data/` | Working copies and working folders of the main project. `variants/` holds whole copies of the project, with their own data. This copy does not have these folders |
| `.venv/` (approximately 100 MB) | The local Python environment. `uv sync` makes it again from `uv.lock` |
| Caches and local files: `__pycache__/`, `.pytest_cache/`, `.claude/`, `.DS_Store` | The tools on this computer make them |
| The other 46 files of `data/derived/` (1,168,631,340 bytes) | Too large, and the scripts make 42 of them again (section 4) |

The team decides on two items. My advice is to publish both, after the team fills in its gaps:

- `SUBMISSION.md` and `docs/submission_template.md`. They hold notes to the team beside the text of the form. `scripts/build_submission.py` reads the template, thus the template must stay with the script. To leave out `SUBMISSION.md`, add it to `.gitignore`.
- `demo/` (the outline and the text of the demo). To leave it out, add `demo/` to `.gitignore`.

## 3. The size of the public copy

With the rules of `.gitignore`, the public copy has 451 files and approximately 152.5 MB. The page data are most of it: 113 MB.

The largest files:

| File | Size |
|---|---|
| `site/data/rose.bin` | 9,580,928 |
| `site/data/open.bin` | 9,321,984 |
| `site/data/snowfree.bin` | 9,321,984 |
| `data/derived/light_cells_v1.json` | 7,173,882 |
| `data/derived/cells_scored_v2.json` | 6,822,076 |
| `site/data/yearly.bin` | 6,214,656 |
| `site/data/extra.bin` | 4,515,336 |
| `site/data/mars.json` | 3,972,049 |
| `site/data/mars_extra.bin` | 3,440,760 |
| `site/data/factors.bin` | 2,994,040 |

**No file of the public copy is larger than 50 MB.** GitHub warns at 50 MiB and refuses a file larger than 100 MiB.

Four files of the project are larger than 50 MB. All four are in `data/derived/`, and `.gitignore` keeps them out:

| File | Size | Compressed (gzip) | What to do |
|---|---|---|---|
| `cells_scored.json` | 271,252,552 (258.7 MiB) | 21,019,980 | Keep it out: GitHub refuses it. `scripts/rebuild_all.py` makes it again (step `score_cells`). Put it in the archive of section 4 |
| `mars_cells.json` | 235,183,416 (224.3 MiB) | 23,638,178 | Keep it out: GitHub refuses it. `scripts/build_mars_cells.py` makes it again. Put it in the archive |
| `grazing_cells.json` | 159,678,112 (152.3 MiB) | 10,414,662 | Keep it out: GitHub refuses it. `scripts/rebuild_all.py` makes it again (step `build_grazing_cells`). Put it in the archive |
| `power_cells.json` | 51,169,653 (48.8 MiB) | 2,578,072 | Keep it out. It is less than the warning line of 50 MiB, but a later build can increase it. `scripts/build_power_cells.py build` makes it again. Put it in the archive |

The old `.gitignore` did not keep out `mars_cells.json` and `power_cells.json`. A push with the old rules would stop at `mars_cells.json`.

## 4. `data/derived/`: advice

`data/derived/` holds 71 files and 1,193,180,910 bytes (approximately 1.2 GB). With gzip, it is approximately 164 MB.

**Advice: put only 25 files in the repository (approximately 25 MB). Offer the other files as one archive.** `.gitignore` does this now.

These files go in, because the documents link to them or name them for a figure:

- `RESULTS-FINAL.md`, `RESULTS.md` and `MARS-RESULTS.md`: `README.md` links to each of them.
- `RESULTS-all-regions.md`, `checks.json`, `factor_matrix.json`, `moon_cards.json`, `moon_targets.json`, `latitude_profile.json`, `planet_factors.json`, `mars_sites.json`, `validation.json`, `validation_extras.json`, `winter_leads.json` and `AI-NOTE.txt`: `README.md`, `docs/METHOD.md`, `SUBMISSION.md` or `RESULTS-FINAL.md` give them as the source of a figure.

These files go in, because no script can make them again (`docs/REPRODUCE.md`, section 3):

- `light_cells_v1.json`, `cells_scored_v1.json`, `ranking_v1.txt` and `validation_v1.json` (the first method);
- `cells_scored_v2.json`, `validation_v2.json`, `ranking_v2.txt` and `RESULTS_v2.md` (version 2);
- `count_check_v3.json` (an earlier recount) and `mars_sites_base.json` (the twelve earlier Mars sites, from a script outside the project).

The other 46 files stay out. If the raw data are on the disk, the scripts make 42 of them again:

- `scripts/rebuild_all.py` makes the files of the Moon part: `candidates.json`, `grazing_cells.json`, `grazing_bins.npz`, `cloud_cells.json`, `cells_scored.json`, `ranking.txt`, `temperature_cells.json`, `snow_validation_many.json`, `sunpath_demo.json` and `access_cells.json`. It also makes again six files that go in: `latitude_profile.json`, `validation.json`, `moon_cards.json`, `validation_extras.json`, `winter_leads.json` and `RESULTS.md`.
- `scripts/rebuild_all.py` does not make its own inputs: `moon_targets.json`, `landcover_cells.json`, `landcover_cells_south.json`, `snow_free_dekads.npz`, `horizon_cells.json` and `terrain_cells.json`. Their scripts are in `docs/REPRODUCE.md`, section 4.
- It does not make the Mars files, the factor files, the power files, the two snow checks or the two checks of section 6. Their scripts are in `docs/REPRODUCE.md`, sections 6 to 8.
- Four files are half-finished or old: `horizon_cells_partial.json`, `terrain_cells_partial.json`, `snow_free_dekads_v1.npz` and `terrain_cells_v1.json`. No script reads them, and no script makes them. Do not publish them.

Why not all of `data/derived/`:

- Three files are larger than the limit of GitHub. A gzip copy of each is less than 25 MB, but each script reads the plain file.
- The other files can go in, but they add approximately 650 MB to each copy of the repository. A visitor of the page does not need them: the page uses only `site/data/`.
- In all cases, a rebuild needs the raw data of approximately 12 GB.

The archive: put all 71 files of `data/derived/`, and the 36 saved JPL Horizons answers of `data/raw/horizons_check/` (7.8 MB), in one compressed file. Attach it to a release of the repository (GitHub permits files of up to 2 GiB there). Then write its link where `README.md` and `docs/REPRODUCE.md` say `[LINK TO THE LARGE RESULT FILES]`. Some tests read these files. Without the archive, they fail or stop.

To put one more file in the repository, add a line `!data/derived/<name>` to `.gitignore`. Do not add a file larger than 50 MB.

## 5. The scan of the public copy

On 15 November 2026, a script read each file of the public copy (the 451 files of section 3). It searched for:

- a path that starts with `/Users/`, `/private/`, `/home/` or `/var/folders`;
- an email address;
- the user name of the home folder of this computer, and its two parts.

The script searched the `.bin`, `.npz`, `.gz` and image files as bytes, for the paths and the name only.

The hits:

| File and line | What | Done |
|---|---|---|
| `docs/PUBLISHING-CHECK.md`, line 110 | The words `/Users/` and `/private/tmp` in the text of the earlier scan | Not a path. No change |
| `docs/PUBLISHING-CHECK.md`, line 120 | The same words in its search command | Not a path. No change |
| `tests/test_build_submission.py`, line 338 | A test that makes sure that `SUBMISSION.md` holds no such path | Not a path. No change |
| `tests/test_make_results.py`, line 122 | The same kind of test for `RESULTS.md` | Not a path. No change |
| `docs/PUBLIC-COPY.md` (this file), section 5 | The words of the search and of this table | Not a path. No change |

- The scan found no email address. The credit line of Natural Earth has "data @ naturalearthdata.com", with spaces: it is not an address.
- The scan found the user name of the home folder in no file of the public copy.
- The names of persons in the credit lines and in the citations are the names of authors. Their owners give them, thus they stay.
- **The scan did not search for the names of the team members.** This file does not know them. Search for each name before the push.
- Outside the public copy, nine files hold a path with the user name: eight in `research_notes/` and one in `docs/superpowers/`. `.gitignore` keeps both folders out. The link `data/raw` also holds such a path (section 2).

Thus no hit needed a repair.

## 6. The five minutes, when the team decides

1. Fill in the gaps in square brackets: `[TEAM NAME]`, `[TEAM MEMBER NAMES]` and the links, in `README.md`, `NOTICE`, `docs/REPRODUCE.md` and `docs/submission_template.md`. Then run `uv run python scripts/build_submission.py`.
2. Search each file for the name of each team member (section 5).
3. In the top folder of the project, run `git init` and `git add .`. Git reads `.gitignore`.
4. Run `git status --short` and read the list of files. Make sure that it holds no `data/raw`, no file larger than 50 MB and none of the folders of section 2. The list must hold the 25 files of `data/derived/` of section 4.
5. Commit, make the repository on GitHub, and push.
6. Make the archive of section 4, attach it to a release, and put its link in `README.md` and `docs/REPRODUCE.md`.
7. Open the repository and the page in a private browser window, without a login.

## 7. What this file did not do

- It did not run git, publish anything or make a network request.
- It did not read each line of each file. The scan of section 5 searched by pattern.
- It did not make the archive of section 4.
- It did not run the tests.

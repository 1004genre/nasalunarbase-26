# LuniMartian Atlas: the map page

The page uses `index.html`, `app.js` (a plain ES module), `style.css`, and the files in `data/`.
It has no build step or framework. The optional globes use the local MIT library in `vendor/`.
The page makes no request to another host. Serve the folder from a static host, including under a sub-path:

    python3 -m http.server 8765 --directory site

## Update the numbers

Each data figure on the page comes from `data/*`. After the pipeline completes, export the files:

    uv run python scripts/export_site.py

`data/copy.json` retains the earlier headline, purpose, and subline for compatibility.
The page shell follows `handoff/condense-and-builder.md`, with the earlier design and writing rules where they still apply.
The export writes `copy.json` only if it is missing.

## Words and layout

Dark is the default. `theme=light` or the top-bar switch gives the light look.
The root has `data-dest="moon"` or `data-dest="mars"`, and `data-theme="dark"` or `data-theme="light"`.
Gold marks Moon choices, rust marks Mars choices, and cyan marks controls and links.
The still star field uses CSS only. Reduced-motion settings stop motion.

The page starts with a compact info strip and the experiment board.
The strip gives the destination and counts from the data: lunar regions, Mars sites, Earth areas, and factors.
The factor count is the number of rows in `factors.json > matrix`, including rows with unknown figures.
The destination control filters names, list tags, and Mars regions as the reader types.
Lunar groups are NASA 2024 list and NASA 2022 list only, ordered by Sun ceiling.
Mars groups follow the stored landing-site, human-shortlist, and exploration-zone lists.
Each group shows its count. Missing list metadata adds no tag. The list scrolls within
60 percent of the viewport height and becomes a bottom sheet on phones.
Enter or Down opens the list; arrows, Home, and End move between visible rows.
Enter selects and Escape closes it. The active destination is in view when the list opens.
The context bar repeats this control beside the short calculation steps or Mars goals.

The first part has three roots for the Ask module:

- **Make your experiment:** `#ask-root`, the board above the places.
- **Tell the AI about your experiment:** `#ask-words`, the bubble below the board.
- **Places:** `#ask-results`, beside the globes on desktop and below them on a phone.

The three workspace tabs are removed. Old `tab2` values still open the page; they do not hide the board or bubble.
When `api.setMatches(null)` clears the experiment, **Best places** shows the five rows from the page's answer rules.
A valid experiment with no matching areas shows its empty results, not the default rows.
The bottom results bar uses the match label, count, first place name from the page's data, and match percentage.
It shows while the board or bubble is in view, and hides when Places is in view or a place drawer is open.
**Show on the globe** selects the globe and moves to Places. Page-bottom space and focus scrolling keep controls accessible.
Ask, Globes, and Tools load after the first screen renders.
Tools registers the top-bar tour actions at that point. Each tour button stays hidden until
its action is registered: `tour` shows **Tour (60 s)** and `demo` shows **Demo (30 s)**.
A module that registers only `tour` shows only that tour button. Removing an action hides its button.
The page owns `.tabs`, `.tab`, and `.tab-panel`. Left, Right, Home, and End select page tabs.
The compact shared variables are `--pad-section: 24px`, `--pad-card: 16px`,
`--text: 15px`, and `--row: 36px`. The board also has `--tile: 72px`; the bubble uses `--bubble`.

Below Places, **Look closer** pairs the flat map and short-list tabs. Lists show five rows
with Show all; secondary lists and explanations fold. The calendar and **Watch a day of low Sun**
share a row. **Plan** has Rehearse, Compare places, Year plan, and Tools tabs.
**Go deeper** keeps the evidence-card grid. Each caveat remains beside its figure or inside a named fold.
Wide tables scroll inside their own container. They do not widen the page.

The Moon rail reads Experiment, Places, When, Plan, Go deeper.
The Mars rail reads Experiment, Places, A square, Take it away, Go deeper.
Moon-only sections are hidden in Mars mode. Mars retains its own square cards and evidence.
Old `go` and `only` links still reveal their sections and select the necessary tab.
Without an explicit `tab2`, `go=ask` and `only=ask` still open the words root.
An isolated Planner view retains all three Planner parts.

- Moon map squares are “areas”; Mars map squares are “squares”. The data files still use “cells”.
  The Moon area size comes from `meta.json > scoring.cell_km`.
- One colour scale covers the lunar regions, calculation steps, and both poles.
  `meta.json > scale` supplies `year_h` and `period_h`.
- The calendar keeps the same axis across the calculation steps for a lunar region.
  Its folded explanation states the terrain coverage and the set of areas counted.
- Guided map links keep the old `tab2` value for compatibility. The hardest lunar region comes from the lowest stored Sun ceiling.
- The first ten experiment matches have numbered rings on the polar map and the still stage.
  On the detailed Mars map, the page adds a result canvas with its own camera while matches are active.
  Drag, pinch, zoom, keyboard movement, and square selection work in that view. Clearing matches restores the module's normal map.
  Destination changes clear the old marks before new results arrive.

## Cards

- **Place card.** It opens over the page in a right-side drawer. On a phone, it opens as a bottom sheet.
  Focus moves into the drawer. Esc and Close close it and restore focus to its opener.
  The page keeps its scroll position. The card leads with a short verdict, then answers the challenge's three questions:
  "What is the same", "How much" (each value tagged measured, worked out or unknown) and "What is
  different". Only "What is the same" and "How much" stay expanded beneath the verdict. Other parts, including
  charts and module additions, fold to a title and finding. Press the title to open them. Rules select the suggestions in `rehearse()` in `app.js`; the rules read only
  the area's own figures (hours left, typical slope against the median of all areas, rock, slope
  likeness, time of day, a station within `places.json` > `radius_km`).
- **Earlier use.** An area that `places.json` lists under `not_little_known` is never called little
  known: its badge reads "published analog work here", the lists say "yes", and "Hide known analog
  sites" hides it. Areas are matched by id, not by position.
- **NASA Worldview link.** `worldview()` in `app.js` builds it. The format was read from Worldview's
  own configuration and from the address it writes back:
  `?v=minx,miny,maxx,maxy&p=arctic|antarctic&l=<layers, top first>&t=YYYY-MM-DD-T12:00:00Z`.
  `v` is in metres of the view's map projection (EPSG:3413 for `arctic`, EPSG:3031 for `antarctic`);
  `polarXY()` does that arithmetic. The view is 220 km wide, centred on the area. The day is the
  middle of the area's best ten-day period in the last full year. Layers: coastlines, MODIS Terra
  snow cover, MODIS Terra true colour.
- **Lunar region cards.** One per site, from `moon.json`, in a dialog. They open from "About this site"
  in the bar, from each drawing in "The light that we copy", and from a place card. A stored
  reason to select a site is printed only when `why.sourced` is true. The shadow length is the one
  in `meta.json`, as everywhere else on the page.
- **Long stored texts.** `fit()` prints only the sentences of a stored text that have at most 25
  words. It cuts a longer one at its semicolons first.

## The best places on Earth

The left column of the first screen shows the active destination only.
The lunar answer always uses calculation step 3, regardless of the context bar's step or period.
For `has_model: false`, light and Earth-terrain hours remain available. Lunar slope comparisons
and combined ground scores say "unknown: NASA has no 5 m terrain model of this region".
The best-ground row, ground list, place drawer, and lunar region card retain that explanation.
If the field is absent, the page treats the region as one with a terrain model.
Names use the same helper as the short lists. List filters and list order do not change the answer rules.
Five roles remain visible, including on phones. A role can show a clear note if its result is unknown or below the limit.

- **Best light score:** the first `sites.json > top[target].north_lighting` row.
  This list ranks scores. Its first row can have fewer hours than another area.
- **Easiest to reach:** the greatest known annual hours at step 3 among areas that pass the Tools access rule.
  `tools.json` lists the access files and binary layout. The area count, binary size, and available ID hash must agree.
  `access.bin` gives distances and indices into `airfields.json`.
  Northern areas use scheduled flights. Antarctic areas use any listed airfield.
  `yearplan.json > reach_km` gives the distance limit. Missing data or a missing limit gives a note, never zero.
- **Winter:** the first winter-list row, with winter hours at step 3.
  If the row is absent or below `meta.scoring.full_hours / 2`, the answer states the result.
- **Antarctica:** the first `south_lighting` row, with terrain hours during the stored rock season. Antarctic snow is not measured.
- **Most Moon-like ground:** the first `north_full` row. This score combines light, terrain, rock, and bare ground.

Each role keeps its own row, even if another role gives the same place.
Each place opens its drawer and supplies the globe with its position.
Each compact row shows hours and season. The open row also shows best periods and any known airfield distance.
The distance follows the Tools rule. It is a straight-line distance and does not establish a route or permit.
Best dates use step 3. The winter role uses winter periods only.

The Mars answer reads the first five rows of `mars.json > best_places[msite][mgoal]`.
It shows the selected Mars site, the stored square size, scores, positions, and best months.
“First pass” and both metadata cautions remain visible. The answer also states that this is not a climate match.
A row sets `msquare` and opens that square in the Mars section.
If Mars data is absent, the answer gives a plain note.

`go=answer` opens this answer. `only=answer` shows it alone for an isolated screenshot.

## Evidence and files to save

- **The Sun-path picture** (in "The light that we copy") is an SVG drawn by `renderSunPath()` from
  `sunpath.json`: the Sun's path at the lunar region and at the Earth place on the same axes, the band
  shaded, the Earth ground in grey. Dots show time: a day apart on the Moon, an hour apart on Earth.
  The sideways axis is centred on the direction the file names (`axis_centre`). The three cautions
  marked `main` are printed under the picture; the others sit behind "More cautions".
- **What Earth cannot copy** keeps its three paragraphs from `meta.json` and adds the list
  `earth_cannot_match` of the selected lunar region from `moon.json` (the same list as on the site card).
- **How accurate are the results** is drawn by `renderSure()` from `validation.json`, for the selected lunar region.
  Five checks, each with a one-line finding worked out from the figures it shows: lower-latitude
  places, latitude alone against the full method, known sites, sensitivity, and the snow maps against
  weather stations (`snow_station_check`). While `flags.terrain_step_is_a_census` is not true, the
  terrain step is worded "areas that had a terrain figure when this check ran". A count of areas
  after cloud is never shown without the share of hours kept. On a desktop the first check is open and the
  others are folded to their finding; on a phone all five are folded. Check 5 shows the comparison
  for the snow odds the measured areas use (`meta.json` > `snow.measured_cells_rule`).
- **Closing sections** (the Moon/Mars relation, audience, earlier work, sources, licence, and AI use) are
  `<details class="fold">` in `index.html`: a heading and one line until opened. The sources, the
  credit lines and the licence line are filled from `sources.json` by `renderClosing()`; the credit
  lines are printed exactly as written there. The Copernicus notice of that file is also printed
  under the map and under the Sun-path picture.
- **Take the data away.** "Save this list" builds a CSV or a GeoJSON file in the browser from the
  short list on screen (`listRows()`, `TAKE_COLUMNS` in `app.js`). Units are in the column names,
  unknown is left empty (null in GeoJSON), and the source and licence lines are inside the file: as
  lines that begin with `#` at the top of the CSV (read it with `comment="#"`), and as members of
  the GeoJSON collection. "Copy the link to this view" copies the address with the present state.

## Extra files, read when necessary

`scripts/export_site_extras.py` writes them; run it after every run of `export_site.py`. The page
reads `extras.json` first and then only the files it lists (a per-area file only when
`areas.count` equals the number of areas in `cells.json`). If a file is missing, the part that
wanted it says so in one line and the rest of the page works.

| File | Read when | Used for |
|---|---|---|
| `extras.json` | with the first extra file | the list of files; temperature caveats |
| `places.json` | just after the first screen is drawn | not-little-known areas, practical notes |
| `moon.json` | a place card or a lunar region card opens | lunar region cards; the lunar temperature |
| `temperature.bin` | a place card opens | int8 `[cells, 12]`, mean air temperature by month in whole °C; -128 = unknown |
| `cloud_regions.json` | a place card opens | median cloud of the area's region |
| `sunpath.json` | the reader comes near "The light that we copy" | the Sun-path picture |
| `moon.json` | also when the reader comes near "What Earth cannot copy" | what no place on Earth has |
| `validation.json` | the reader comes near "How accurate are the results", or opens "Famous places checked" | the five checks; how many known analog sites come out high, middling and low |
| `sources.json` | the reader comes near the map, the lists or the closing sections | credit lines, licence line, the Copernicus notice, the lines inside a saved file |

`watchSections()` in `app.js` notes when the reader comes within 800 px of a section, and only then
asks for its file. `temperature_surface.bin` is written too; the page does not read it.

## Links to a state

The page keeps its state in the URL fragment, so any view can be shared or opened directly:

The `tour=60` and `tour=30` links, playback controls, and timing are described in [Tours and the recorded demo](TOURS.md).

    #dest=moon|mars            destination mode; default: moon
    &msite=<site-id>            Mars site; default: first site in mars.json
    &mgoal=full|landscape|environment    Mars goal; default: full
    &msquare=<square-id>        open Mars square; default: empty
    &stage=globe|flat           first-screen view; default: globe
    &view=arctic|antarctic      which pole
    &target=<region-id>         any id from meta.json targets
    &step=1..4                  Sun only, snow-free ground, terrain, typical cloud
    &period=year|winter|summer|rock|0..35    whole year, a half-year, the Antarctic rock season, or one ten-day period
    &place=68.9_54.3            opens the place card of that area
    &moon=malapert              opens the lunar region card of that site
    &tab=winter|belt|summer|famous|antarctica
    &tab2=best|make|words        accepted from old links; all experiment roots share one page
    &little=1                   hides the areas in or near known analog sites
    &z=6&x=-87&y=406            zoom and map centre (written by the page)
    &theme=dark|light           dark is the default, regardless of the system setting
    &go=map                     open a section or a Mars anchor
    &only=map                   show one section alone (for slides and screenshots)
    &filters=reachable          enabled module filters, separated by commas
    &order=rehearse              module list order; an empty value means the page's order

The default lunar region is the first NASA 2024 list entry by Sun ceiling.
Without that group, the page uses `malapert` if present, then the first stored region.

The earlier keys retain their meaning. Old links without `dest` open Moon mode; a direct Mars link opens the Mars section.
The main section names include `destination`, `answer`, `map`, `lists`, `when`, `place`, `plan`, `sky`, `tools`, and `planner`.
Evidence names include `deeper`, `factors`, `extra`, `env`, `light`, `where`, `limits`, `sure`, and `more`.
The Mars anchors are `mars-site`, `mars-goal`, `mars-map`, `mars-square`, `mars-list`, and `mars-evidence`.
A direct link to a deeper section opens that section. `only` retains the isolated-section view.
The `flat` stage moves to the exact flat map for the active mode.

For a screenshot from the command line (`chrome --headless --screenshot`), use `&only=map`, not
`&go=map`: that command pictures the page from its top after it has scrolled, so everything above
the scrolled-to section comes out blank. In a real window `&go=map` is correct.

## Files in data/

| File | What |
|---|---|
| `meta.json` | targets, the 36 ten-day periods, counts, headline figures, sources |
| `cells.json` | one column per fact for every cell; `-1` means unknown |
| `yearly.bin` | uint16 `[cells, targets, fields]` (the field names are in `cells.json` under `yearly.fields`): hours of the year, the winter half and the summer half in tenths, and scores in thousandths; 65535 = unknown |
| `snowfree.bin`, `open.bin` | uint8 `[cells, targets, 36]`: hours per ten-day period in half hours, at most 254; 255 = unknown |
| `snowodds.bin` | uint8 `[cells, 36]`: snow-free odds in percent; 255 = unknown |
| `cloud.bin` | uint8 `[cells, 12]`: mean cloud in percent by month; 255 = unknown (absent without cloud data) |
| `flat.json` | Sun-only hours per ten-day period for each latitude row |
| `calendar.json`, `profile.json`, `sites.json`, `land.json`, `copy.json` | the charts, the short lists, the land outline, the headline |

Unknown is never written or drawn as zero.

## Page module API, version 1

The page owns the state and data. Modules receive an `api` object after the core data is ready.
Tools, Planner, Factors, Extra, Sky, Env, Cross, and Globes export `mount(root, api)`.
Mars exports `mountMars(root, { theme, api })`.
Each mount can return a promise and an object with `destroy()`.

The mount points use the module name and `-root`, including `#globes-root` on the first screen.
Visible sections keep their headings after a mount. Cross has a permanently hidden root without a heading.
Sky belongs to “A place”. Planner and Tools belong to “Plan”.
Factors, Extra, and Env belong to “Go deeper”. Mars supplies its own steps in Mars mode.

Except for Globes, Ask, and Tools, module code loads when its section enters the viewport, with no advance margin.
Its matching stylesheet loads at the same time: `tools.css`, `planner.css`, `factors.css`, `extra.css`, `sky.css`, `env.css`, `cross.css`, or `mars.css`.
The first place card also loads Tools, Planner, Factors, Extra, Sky, Env and Cross. Each module mounts only once.
Cross only adds a card part, so its hidden root never triggers viewport loading.
Env reads `environment.json` and `environment.bin`, checking their area count, endpoint IDs and binary size.
An existing Tools button also waits for its module before running its action.
The Tools row remains hidden until a module registers a button.
A failed Tools, Planner, or Mars mount leaves a plain status line in that section.
A missing or failed optional Factors, Extra, Sky, Env or Cross module hides its section without a page error.
The page catches module errors and continues working.
Chrome still records its own network diagnostic when a module file returns a missing-file response.

Use `#go=tools`, `#go=planner`, or `#go=mars` to open a module section directly.
Use `only=tools`, `only=planner`, or `only=mars` for a section screenshot.
Sky supports `go=sky` and `only=sky`; Env supports `go=env` and `only=env`.
Cross has no standalone view or address key.
The optional Globes module loads `globes.js` and `globes.css` immediately after the first paint.
Ask loads `ask.js` and `ask.css` at the same point, without waiting for its tab to open.
The stage retains a still map while it loads, or if WebGL or the module fails.
The destination buttons and answer rows remain usable without WebGL.
The “Flat maps” switch opens the exact maps for the current mode.

The card keeps its verdict, “What is the same” and “How much” open before all folded parts.
`orderCardSections()` orders direct-child folds by stable IDs, with title fallbacks for new modules:
rehearsal verdicts; where the low Sun stands; watch a day here; power here; steady influences here;
this place as a Mars stand-in; sunlight, UV, clear days and haze; more about this place; take it away; anything else.
Other folds retain their relative order. Nested folds remain inside their parent, and open state and keyboard focus survive redraws.
Existing `addCardSection` calls need no changes.

### State

| Member | Meaning |
|---|---|
| `version` | `1`. |
| `getState()` | A detached copy of the current state. |
| `setState(partial)` | Merge values, normalize core fields, update the fragment, and redraw the page. |
| `onState(fn)` | Call `fn(state)` after a change; return a function that removes the listener. |
| `readyAt` | The core-ready timestamp in `performance.now()` units, or `null` before readiness. |
| `captureView()` | Return an opaque token for the current state, open evidence sections, Plan tab, and expanded short lists. Retain the token directly. |
| `restoreView(token, state?)` | Restore the token's view with the supplied state, or the captured state when omitted. Return `false` for an invalid token. |

View restoration replaces state: absent extension keys and extension keys set to `null` are removed.
It cancels pending section navigation and scroll holds, and does not follow the saved `go` value.
Subscribers redraw once; their synchronous state writes are suppressed during restoration.
The caller restores DOM folds, scroll positions, focus, and module-local state separately.

Core keys appear in the state-link list above.
`period` is `year`, `winter`, `summer`, `rock`, or `bin`; `bin` holds the selected period index.
`setState` also accepts a numeric period index, including a numeric string.
Map coordinates `x` and `y` use projection units in the API and thousandths in the fragment.
Zoom is `z`. A place link without `x` and `y` centres the map on that area.
`go` scrolls to the requested section and stays in the shared link.

Modules can add their own keys, such as `rehearse` and `compare`.
Plain strings stay readable in the fragment.
Other JSON-compatible values use a `~` prefix followed by JSON; strings that start with `~` use the same encoding.
Set an extra key to `null` to omit it from the link.
Listeners receive fresh copies after reader controls, map movement, fragment navigation, or module changes.
The theme switch updates state and notifies listeners. System theme changes do not override the default dark theme.
Subscriptions do not call the listener immediately; use `getState()` for the initial draw.

### Data and map

| Member | Meaning |
|---|---|
| `answer(targetId)` | Lunar answer rows as `{ label, area }`; `area` is an index in `cells.json`. Roles without a known area are omitted. |
| `setMatches(matches)` | Publish `null` or `{ label, areas, scores, mode }`. Area indices and scores have equal lengths; scores are fractions from zero to one. |
| `onMatches(fn)` | Call `fn(matches)` immediately and after each change. Return a function that removes the listener. |
| `targets` | Frozen array of `{ id, name, limitDeg }`, in page order, with official lunar region names. |
| `periods` | Frozen array of `{ index, label, firstDay, lastDay, month }`, from the period data. Month runs from one to twelve. |
| `areaCount` | Number of areas in `cells.json`. |
| `areaIndex(id)` | Area index in that file, or `-1` for an unknown ID. |
| `area(i)` | `{ id, lat, lon, hemisphere, region, bare, snowStatus, named, littleKnown }`, or `null` for an invalid index. |
| `hours(i, targetId, step, period)` | The same hours used by the map, or `null` when unknown. |
| `periodHours(i, targetId, step)` | A new `Float32Array(36)`; unknown periods contain `NaN`. |
| `openPlace(id)` | Open the area's drawer and centre its map. Keep the page scroll position. |
| `flyTo(lat, lon, zoom)` | Move the map and select the coordinate's hemisphere. Omitted zoom keeps the current zoom. |

Match arrays use Moon area indices or Mars square indices from `mars.json`, according to `mode`.
The page copies the arrays, rejects invalid entries, and clears them when the destination changes.
Match callbacks cannot stop other page subscribers.

Area coordinates have the same precision as the page.
`hemisphere` is `N` or `S`; `bare` is a fraction from zero to one, or `null`.
`named` is the stored place name or `null`.
`littleKnown` is false for known analog use, true for no listed use, and null when unassessed or still loading.
It uses the same earlier-use rules as the place card.

Hours use the existing yearly, seasonal, and period values, with the page's rounding and Antarctic rock-season rule.
The `period` argument accepts a period index, a numeric string, or a core period name.
`bin` means the currently selected period.
Omitted target, step, or period arguments use the current state.
Unknown values never become zero; known zero remains zero.

### Files and words

| Member | Meaning |
|---|---|
| `loadJSON(name)` | Promise for parsed `data/<name>`. |
| `loadBin(name)` | Promise for an `ArrayBuffer` from `data/<name>`. |
| `fmtHours(x)` | The page's rounded hours plus ` h`, or `unknown`. |
| `fmtNumber(x, digits = 0)` | A grouped number with the requested decimal places, or `unknown`. |
| `theme()` | The effective `light` or `dark` theme. |
| `announce(text)` | Set the page's polite screen-reader announcement. |

The page and modules share one file cache, including requests already in progress and failed requests.
Each file has one cached load, even when requested as both JSON and binary.
If the browser supports `DecompressionStream`, a load first requests `data/<name>.gz`.
If that response is not OK, the load requests the plain file.
The page checks the first two bytes: `1f 8b` means gzip, which the page decodes with `DecompressionStream('gzip')`.
Other bytes pass through unchanged, including bytes that the host's `Content-Encoding: gzip` already caused the browser to decode.
Without `DecompressionStream`, the page requests the plain file directly.
JSON loads parse the decoded bytes. The cache includes the request, any plain-file fallback, and decompression.
Names can include subfolders inside `data`; external URLs and parent paths are rejected.
Redirects are rejected. Treat cached objects and buffers as read-only.

The Task 19 check used a fresh 1440 × 900 browser page with `moon-many`, with no interaction.
The browser read a separate local copy. Its network list supplied the response-body byte counts.
At the first usable render, successful data responses decreased from 18,689,268 to 4,010,694 bytes.
After the first screen's automatic module loads ended, data responses decreased from 37,229,697 to 9,648,890 bytes (74%).
The latter count includes 198 bytes from nine expected missing-gzip responses.
These data counts exclude HTML, code, styles, textures, and HTTP headers.
The check covered raw gzip, already-decoded bytes, plain-file fallback, and a browser without `DecompressionStream`.
Concurrent binary and JSON calls shared the same load; failed loads also stayed in the cache.
The check did not use a deployed host's `Content-Encoding` settings.

### Extension points

| Function | Meaning |
|---|---|
| `registerAction(name, fn)` | Register `tour`, `demo`, or `search` for the top bar. Return a function that removes the action. |
| `addToolsButton(id, label, onPress)` | Add a keyboard-accessible button under the first calendar. Reusing an ID replaces the button. |
| `addCardSection(id, title, render, summary?)` | Append a folded section after the page's own card content. `render(i, targetId)` returns an element or `null`. Optional `summary(i, targetId)` returns a short finding. Older calls use the first paragraph. |
| `addListNote(fn)` | Append escaped text from `fn(i, targetId)` to each row; `null` adds nothing. |
| `addListFilter(id, label, test)` | Add an unchecked switch above the lists. `test(i, targetId)` keeps a row when true. |
| `setListOrder(id, label, score)` | Register a descending order. `score(i, targetId)` returns a number or `null`; unknown scores sort last. |

If a top-bar action is absent, the page loads Tools before it calls the action.
Registration returns a function that removes the extension.
Reusing a card, filter, or order ID replaces its callback.
Card sections redraw with the place or lunar region and survive ordinary page redraws.
List extensions apply to every short list, including named places, rock matches, and Antarctica.
The belt list passes its own lunar region ID to callbacks.
Filters and orders also apply to saved CSV and GeoJSON rows.
Scores with equal values retain their original order.

Enabled filters are stored in `filters`, as comma-separated IDs.
The selected order is stored in `order`; select “Page order” to restore the original order.
The first registered order becomes selected when the link has no saved order.
Later registrations preserve the saved selection.
Modules can select their order with `setState({ order: id })`.
Passing a non-function score removes an order.
Selections survive redraws and reloads, and take effect when the owning module mounts.
Registration alone does not load a module on the first screen.
While a saved setting awaits its module, the lists show links to Tools and Planner instead of misleading unfiltered rows.
Open the relevant section to restore those settings; downloads wait for them too.


## Page polish

- Factors and Extra follow `export async function mount(root, api)`.
  Their evidence sections sit below “Go deeper”, headed “Every factor” and “Power and steady influences”.
  Their JavaScript and matching CSS load on entry into view, or when the first place card opens.
  Missing optional modules hide their sections silently. A browser can still log its own missing-file diagnostic.
- Open these sections with `#go=factors` or `#go=extra`.
  Use `#only=factors` or `#only=extra` for isolated screenshots.
- Place cards also load Tools and Planner, so their card additions are available without visiting those sections.
  Only the verdict, “What is the same”, and “How much” stay expanded by default.
  Other parts show a title and a brief finding. Native details controls work with Enter or Space.
  Open parts and keyboard focus survive card redraws.
- Planner marks entries below 20 hours or 25 percent snow-free odds as “Poor month”.
  Both limits live together at the top of `planner.js` and appear in the section note.
  Phone months stack in one column, folded to a month name and finding.
- `api.exportList()` resolves to `{ notes, rows }`, using the same visible rows as CSV and GeoJSON.
  Property names include units; unknown values are null. KML uses this snapshot and leaves unknown values empty.
  All three formats carry source and licence lines. The lunar name field is `lunar_region`.


## Earlier local review notes

These notes describe the page before the shell redesign. They do not establish checks of the current shell.

The page was reviewed in headless Chrome at 1440 by 900 and 390 by 844, in both themes.
The review covered the first screen, map controls, short lists, each tool, Planner, and Mars.
Haughton, south-west Iceland, and McMurdo Dry Valleys cards were checked with every part open.
Factors and Extra were checked after their files became available.

The timed tour completed all eight steps and restored the original view, scroll position, and open card parts.
A key press stopped it and restored the same view.
CSV, GeoJSON, and KML were opened and compared with the visible Antarctic list.
All three contained the same rows, units, empty unknown fields, and licence text.
A copied summary and a printed PDF were read and visually checked.

The review fixed hidden-section CSS, phone map wrapping, evidence-table overflow, search navigation,
Planner labels, tour framing and restoration, and KML row differences.
Iceland's verdict now distinguishes snow-free ground from mapped bare ground.
Antarctic practical notes separate field evidence from the missing area snow odds.

Exact provider credit and licence wording remains unchanged, including long sentences.
Factors and Mars belonged to separate tasks during that review. Mars uses “squares”; the lunar page uses “areas”.
External links, live screen-reader output, and physical devices were not checked.


## Shell review (round 4)

Headless Chrome opened the local page at 1440 by 900 and 390 by 844, in both themes and both modes.
The review covered the first screen, the complete page, the place drawer, and Go deeper.
The browser reported no page errors and no requests to another host. The page also fit at 360 px.

The drawer kept the scroll position. Escape closed it and returned focus to the place row.
The search action focused its input. The tour started. The Mars step link waited for its module,
opened a square, and marked step 3. Deeper cards opened their evidence and updated their state.
The review also checked isolated answer and Tools views, picker focus, and the rail on a phone.

This Chrome setup could not run WebGL. The still map, destination buttons, and flat maps remained usable.
Globe motion with a working GPU was not checked. External links, live screen-reader output,
and physical devices were not checked. No test files were written or test suite run.

The command-line phone capture used a wider Chrome layout and cropped its right side.
The final phone review used Chrome's device metrics to set the actual viewport to 390 px.


## Compact workspace review (round 5)

The complete Moon page measured 3,595 px at a 1440 by 900 viewport, with Go deeper closed.
This includes the loaded calendar, Sky, and Planner, in both looks. The desktop workspace ends
at the first screen edge at both 1440 by 900 and 1280 by 720. Its left panel scrolls internally.
The context bar measures 50 px, including its borders and padding.

Local headless Chrome screenshots covered all three workspace tabs, Moon and Mars, both looks,
and viewports of 1440 by 900, 1280 by 720, and 390 by 844. The review also covered the destination
list, complete pages, and place drawers. Device metrics set the real phone width.
Keyboard review covered destination selection, all page tab groups, and drawer focus and Escape.
Legacy go and only views, numbered result marks, zoom, and clearing results were reviewed.
The browser reported no page errors or page requests to another host.

This browser used the still maps because WebGL was unavailable. GPU globe motion, physical
touch devices, live screen-reader speech, external links, and local AI model calls were not checked.
The available metadata had four lunar regions; the picker reads its length from the files.
No test files were written, no test suite ran, and no packages were installed.

## Page tasks 17, 19A, and 21A

The Task 17 copies held 10 lunar regions and 12 Mars sites.
Both looks were checked at 1440 × 900, 1280 × 720, and 390 × 844.
The list filtered names and tags, kept its selected row in view, and stayed within 60% of the viewport height.
Keyboard checks covered arrows, Home, End, Enter, and Escape. The phone list opened from the bottom.
The three regions without terrain models kept their known light figures and showed the explicit unknown-ground sentence.
The page, ground lists, place drawer, and lunar card showed that distinction.

The fixed destination IDs in the initial/default state and calendar comparison were replaced with data rules.
The calendar now finds the lowest and highest Sun ceilings. The default uses the first 2024 region, then Malapert if present.
No fixed destination-column count remained in the core binary readers.
A local present-data load reached the first usable core screen in 649 ms after navigation started.
This is one unthrottled local browser sample, not a network-speed estimate.
The initial core still reads all-target files such as `yearly.bin`, `open.bin`, and `snowfree.bin`.
It also starts the Mars metadata, world, and shared score file in Moon mode. There is no separate per-destination core file to defer.
Task 19A reduced these response sizes with gzip; the byte measurements appear in the file-loading section above.

Task 21A puts the info strip, board, and bubble before Places.
The stage and results share two columns on desktop and stack on a phone.
The info strip measured 110 px at both desktop widths. The page fit at 360 px also.
The first shell check, before the Task 21B match changes, showed 33 areas, Arctic Canada, and a 100% match in the bottom bar.
The bar disappeared at Places; keyboard activation moved focus to the Places heading.
An empty experiment result kept the results view. Clearing it restored Best places.
Area index zero and a zero match stayed valid. The Mars bar used the square's region from the data.
Old `tab2=best`, `make`, and `words` links showed the board and bubble together; an isolated words link also worked.

With the final Task 21B board, present data, no options set, and Go deeper closed, the complete Moon page measured:

| Viewport | Dark page height | Light page height |
|---|---:|---:|
| 1440 × 900 | 5,344 px | 5,344 px |
| 1280 × 720 | 5,496 px | 5,496 px |
| 390 × 844 | 10,154 px | 10,154 px |

Each measurement used a fresh browser process and explicitly loaded Sky and Planner before the page height was read.
The board itself measured approximately 1,037 px at 1440 px, 1,215 px at 1280 px, and 659 px with phone categories folded.
The module's final tiles and bubble replaced the earlier accordion used in the first shell check.
Tools now moves its stage steps to Places. The shell suppresses focus adjustment during `.tl-touring` and `.tl-tour-restoring`.
It checks both before it queues a frame and when that frame runs.
Browser checks covered a frame queued before the tour, a frame requested during restoration, and ordinary focus protection.
The guarded cases kept the scroll at 409 px. An actual Demo cancellation also restored that scroll, the URL, criteria, draft, and focus.
Full timed tours were not rerun in this shell follow-up; the Tools owner checks their duration.
Live AI calls, physical devices, live screen-reader speech, and deployed server headers were not checked.
The local browser checks reported no page exceptions, external requests, or horizontal page overflow.

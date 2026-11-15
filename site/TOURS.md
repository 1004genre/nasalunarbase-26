# Tours

Use **Tour (60 s)** for eight steps or **Demo (30 s)** for five steps.
The demo gives each step a 6-second slot. The final slot reserves 2.5 seconds
to restore and paint the original page before the recording limit.
Module waits use the same slots. A late module cannot extend the demo.

## Links

The state key `tour` accepts the string `60` or `30`:

- `index.html#tour=60`
- `index.html#tour=30`
- `index.html#theme=light&tour=30`

The tour starts 2 seconds after the core page is ready, once Tools is ready.
The demo hides the top bar's buttons while it runs. It restores them at the end.
The caption sits in a separate strip above the content. It shows progress.
A key, press, touch or wheel movement stops the tour. Next and Stop remain usable.
With reduced motion, the tour waits for Next before its first step and each later step.
The low-Sun animation stays still with reduced motion.

The page restores the prior state, criteria, open parts, text draft, scroll positions
and focus at the end or on stop. The Sky module also restores prior playback.
The Globes module restores camera positions and expanded place lists.

## Implementation

`tools.js` builds the steps from the page state and current data.
It does not read or change `data/tour.json`.
The Tools module registers `tour` and `demo` through `api.registerAction`.
The shell loads Tools with the first screen and records `readyAt` in milliseconds
from the page's performance clock. Tools uses that time for linked starts.
The shell supplies `api.captureView()` and `api.restoreView(savedView, savedState)`
for page-owned open sections and navigation. Tools preserves module and DOM state.

Ask, Sky and Globes expose `root.tourActions` after they are ready. Ask supplies the
existing rover preset, the destination table, and local snapshot/restore methods.
Sky supplies play, stop, and local snapshot/restore methods. Globes supplies camera
and control snapshot/restore methods. These hooks use no AI model.

The page emits `earth-twin:tour` events for start, step and stop. A stop event
includes the mode, completion flag and measured elapsed milliseconds, including
restoration and a painted frame.
Its `restoreTiming` object records the shell, module and total restoration times.
The caption strip also keeps `data-elapsed-ms` after the tour ends.

The experiment-board step first shows `#ask-root`, then the numbered results at
`#places-section`. Globe steps use that Places section in the board layout.
The body keeps `tl-touring` during the steps and `tl-tour-restoring` during
restoration. The shell defers results-bar focus scrolling while either is present.

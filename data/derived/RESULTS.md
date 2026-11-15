# Earth Twin Finder: results, version 3

Generated Sunday 15 November 2026, 10:44 Pacific by `scripts/make_results.py` from the files in `data/derived/` as they stood after the chain was run again on the version 3 inputs. Every number below was read from those files or computed from them in that run; each table names the file and field it comes from. Unknown values are written `n/a`, never 0. Version 2 of this file is kept as `RESULTS_v2.md`; section (k) sets the two side by side.

**What this is.** A measured search for places and dates on Earth where the Sun sits as low as it does at 16 candidate landing regions near the Moon's south pole, for hours at a time, on bare and snow-free ground, with the surrounding terrain taken into account.

## How to read this

- **Grazing hour**: an hour with the Sun's apparent centre above the horizon and at or below a lunar site's highest Sun. The 16 lunar targets and their limits (`grazing_cells.json` → `meta.targets[].limit_deg`): Connecting Ridge 2.08°; Connecting Ridge Extension 2.51°; Peak Near Shackleton 2.73°; de Gerlache Rim 1 2.86°; de Gerlache Rim 2 3.31°; Faustini Rim A 3.65°; Slater Plain 4.38°; Haworth 4.78°; Malapert Massif 5.55°; de Gerlache-Kocher Massif 5.71°; Nobile Rim 1 6.10°; Mons Mouton 6.11°; Mons Mouton Plateau 7.21°; Amundsen Rim 7.31°; Nobile Rim 2 7.59°; Peak near Cabeus B 7.90°.
- **Long window (the per-day rule of version 3)**: an unbroken spell of at least 2 h with the Sun in that band, over a flat horizon, followed day by day at 1-minute steps. A spell that runs through midnight is one spell; each of its minutes is counted in the day and ten-day bin in which it falls; a Sun that stays in the band for more than 24 h counts in full (`meta.long_rule` = "per-day spells", `meta.stretch_min_h`). "Long-window hours" are the hours inside such spells. Version 2 instead took or dropped a whole ten-day bin by its median longest spell.
- Three versions are kept apart: **flat** (Sun geometry only), **snow-free** (times the odds that the ground is snow-free in that ten-day bin, NOAA IMS 4 km maps of October 2015 to September 2025), **open** (snow-free, and the terrain does not hide the Sun; only for the 16,133 of 16,184 cells that have a computed terrain horizon).
- **Which snow odds a cell uses** (`snow.odds_used`): a cell with status "measured" uses the snow maps as they read (14,863 northern cells); a "doubtful" cell uses the stale-flag rule, which gives the lower figure (36 cells); "no data" cells have no odds; southern cells are "unmeasured". Both figures are stored for every northern cell with odds (`long_snow_free_hours_as_mapped`, `long_snow_free_hours_with_rule`).
- **Typical clear-sky hours**: open hours times the share of the sky that is clear in a typical month (section (j)). A displayed column only; it enters no score, and it is not the chance that a low Sun is visible.
- Winter half = 28 September to 31 March; summer half = 1 April to 27 September (`meta.winter_bins_north`, `meta.summer_bins_north`). Southern rock season = 27 November to 1 March (`meta.summer_bins_south`).
- A cell is about 11 km across. Bare ground is the share of the cell's land that is bare (`bare`). On the web page a cell is called an "area"; the data files and this file keep the word cell.

### What was searched

| What | Count | Source |
|---|---|---|
| Cell records | 16,184 | `grazing_cells.json` → `cells` |
| Northern cells in the search (bare ≥ 0.15, 59 to 84 N) | 14,933 | `gridded` true, `hemisphere` N |
| of them with measured snow odds | 14,863 | `snow.status` = measured |
| of them doubtful / no snow data (listed, not ranked) | 36 / 34 | `snow.status` |
| Southern cells (bare ≥ 0.15, land share ≥ 0.2, 59 to 87.5 S); snow not measured | 1,241 | `gridded` true, `hemisphere` S |
| Named-site cells outside those screens (reported apart) | 10 | `gridded` false |
| Cells with a terrain horizon | 16,133 of 16,184 | `horizon` with `north_deg` |
| Cells without one: elevation tiles not fetched / window across the antimeridian | 0 / 51 | `horizon.skipped` |
| Measured northern cells with a horizon / without | 14,833 / 30 | `validation.json` → `big_picture_north.cells_with_a_horizon`, `.cells_without_a_horizon` |
| Southern cells with a horizon / without | 1,220 / 21 | `horizon`, `hemisphere` S, `gridded` |
| Cells with slope statistics | 16,181 | `cells_scored.json` → `terrain` |
| Ranked cells, north / south | 10,837 / 617 | `cells_scored.json` → `ranked`, `ranking` |
| Measured northern cells with bare ≥ 0.25 that cannot be ranked because they have no horizon | 15 of 10,852 | `bare`, `snow.status`, `horizon` |

The 51 cells without a horizon (0 without an elevation tile on disk, 51 across the antimeridian) keep complete flat and snow-free hours; their open hours, clear-sky hours and light scores are `n/a`, and they are in no ranking.

## (a) Where on Earth the Sun grazes the horizon for hours

Pure Sun geometry: flat horizon, standard refraction, no snow, no terrain. Hours per year.

| Latitude | Connecting ridge (≤ 2.08°): all hours / hours inside spells of 2 h or more / longest single spell of the year, h | Connecting Ridge Extension (≤ 2.51°): all hours / hours inside spells of 2 h or more / longest single spell of the year, h | Peak Near Shackleton (≤ 2.73°): all hours / hours inside spells of 2 h or more / longest single spell of the year, h | de Gerlache Rim 1 (≤ 2.86°): all hours / hours inside spells of 2 h or more / longest single spell of the year, h | de Gerlache Rim 2 (≤ 3.31°): all hours / hours inside spells of 2 h or more / longest single spell of the year, h | Faustini Rim A (≤ 3.65°): all hours / hours inside spells of 2 h or more / longest single spell of the year, h | Slater Plain (≤ 4.38°): all hours / hours inside spells of 2 h or more / longest single spell of the year, h | Haworth (≤ 4.78°): all hours / hours inside spells of 2 h or more / longest single spell of the year, h | Malapert (≤ 5.55°): all hours / hours inside spells of 2 h or more / longest single spell of the year, h | de Gerlache-Kocher Massif (≤ 5.71°): all hours / hours inside spells of 2 h or more / longest single spell of the year, h | Nobile Rim 1 (≤ 6.10°): all hours / hours inside spells of 2 h or more / longest single spell of the year, h | Mons Mouton (≤ 6.11°): all hours / hours inside spells of 2 h or more / longest single spell of the year, h | Mons Mouton Plateau (≤ 7.21°): all hours / hours inside spells of 2 h or more / longest single spell of the year, h | Amundsen Rim (≤ 7.31°): all hours / hours inside spells of 2 h or more / longest single spell of the year, h | Nobile Rim 2 (≤ 7.59°): all hours / hours inside spells of 2 h or more / longest single spell of the year, h | Peak near Cabeus B (≤ 7.90°): all hours / hours inside spells of 2 h or more / longest single spell of the year, h |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 N | 120 / 0 / 0.2 | 143 / 0 / 0.2 | 155 / 0 / 0.2 | 162 / 0 / 0.2 | 186 / 0 / 0.3 | 204 / 0 / 0.3 | 242 / 0 / 0.3 | 263 / 0 / 0.4 | 303 / 0 / 0.4 | 312 / 0 / 0.5 | 332 / 0 / 0.5 | 332 / 0 / 0.5 | 389 / 0 / 0.6 | 394 / 0 / 0.6 | 409 / 0 / 0.6 | 425 / 0 / 0.6 |
| 30 N | 140 / 0 / 0.2 | 168 / 0 / 0.2 | 182 / 0 / 0.3 | 190 / 0 / 0.3 | 218 / 0 / 0.3 | 239 / 0 / 0.3 | 284 / 0 / 0.4 | 309 / 0 / 0.5 | 356 / 0 / 0.5 | 366 / 0 / 0.5 | 390 / 0 / 0.6 | 390 / 0 / 0.6 | 457 / 0 / 0.7 | 463 / 0 / 0.7 | 480 / 0 / 0.7 | 499 / 0 / 0.7 |
| 45 N | 178 / 0 / 0.3 | 213 / 0 / 0.3 | 230 / 0 / 0.3 | 241 / 0 / 0.4 | 277 / 0 / 0.4 | 303 / 0 / 0.5 | 361 / 0 / 0.6 | 392 / 0 / 0.6 | 452 / 0 / 0.7 | 465 / 0 / 0.7 | 495 / 0 / 0.8 | 496 / 0 / 0.8 | 581 / 0 / 0.9 | 589 / 0 / 0.9 | 611 / 0 / 1.0 | 635 / 0 / 1.0 |
| 50 N | 201 / 0 / 0.3 | 240 / 0 / 0.4 | 260 / 0 / 0.4 | 272 / 0 / 0.4 | 312 / 0 / 0.5 | 342 / 0 / 0.6 | 407 / 0 / 0.7 | 442 / 0 / 0.7 | 511 / 0 / 0.8 | 525 / 0 / 0.9 | 559 / 0 / 0.9 | 560 / 0 / 0.9 | 658 / 0 / 1.1 | 667 / 0 / 1.1 | 692 / 0 / 1.2 | 719 / 0 / 1.2 |
| 55 N | 234 / 0 / 0.4 | 280 / 0 / 0.5 | 303 / 0 / 0.5 | 317 / 0 / 0.5 | 364 / 0 / 0.6 | 400 / 0 / 0.7 | 476 / 0 / 0.8 | 518 / 0 / 0.9 | 599 / 0 / 1.1 | 616 / 0 / 1.1 | 657 / 0 / 1.2 | 658 / 0 / 1.2 | 775 / 0 / 1.4 | 786 / 0 / 1.5 | 816 / 0 / 1.5 | 850 / 0 / 1.6 |
| 57.5 N | 258 / 0 / 0.5 | 309 / 0 / 0.5 | 334 / 0 / 0.6 | 350 / 0 / 0.6 | 402 / 0 / 0.7 | 442 / 0 / 0.8 | 526 / 0 / 1.0 | 573 / 0 / 1.1 | 664 / 0 / 1.3 | 683 / 0 / 1.3 | 729 / 0 / 1.4 | 731 / 0 / 1.4 | 866 / 0 / 1.8 | 878 / 0 / 1.9 | 914 / 0 / 2.0 | 955 / 83 / 2.1 |
| 59 N | 276 / 0 / 0.5 | 331 / 0 / 0.6 | 358 / 0 / 0.7 | 374 / 0 / 0.7 | 431 / 0 / 0.8 | 474 / 0 / 0.9 | 565 / 0 / 1.1 | 616 / 0 / 1.2 | 716 / 0 / 1.5 | 737 / 0 / 1.6 | 789 / 0 / 1.7 | 790 / 0 / 1.7 | 947 / 129 / 2.3 | 962 / 144 / 2.4 | 1,009 / 188 / 2.7 | 1,066 / 239 / 6.2 |
| 60 N | 291 / 0 / 0.5 | 348 / 0 / 0.7 | 377 / 0 / 0.7 | 394 / 0 / 0.8 | 454 / 0 / 0.9 | 499 / 0 / 1.0 | 597 / 0 / 1.2 | 652 / 0 / 1.4 | 760 / 0 / 1.7 | 784 / 0 / 1.8 | 842 / 48 / 2.1 | 844 / 51 / 2.1 | 1,032 / 235 / 6.0 | 1,048 / 247 / 6.0 | 1,089 / 280 / 6.1 | 1,133 / 314 / 6.2 |
| 62.5 N | 341 / 0 / 0.7 | 409 / 0 / 0.9 | 444 / 0 / 1.0 | 465 / 0 / 1.1 | 538 / 0 / 1.3 | 595 / 0 / 1.5 | 736 / 84 / 4.9 | 808 / 141 / 5.1 | 931 / 221 / 5.4 | 955 / 236 / 5.5 | 1,012 / 271 / 5.7 | 1,013 / 272 / 5.7 | 1,164 / 366 / 6.1 | 1,178 / 375 / 6.2 | 1,214 / 398 / 6.3 | 1,254 / 425 / 6.4 |
| 65 N | 461 / 52 / 3.5 | 549 / 93 / 3.9 | 591 / 110 / 4.0 | 615 / 119 / 4.1 | 694 / 150 / 4.4 | 751 / 173 / 4.6 | 868 / 221 / 5.0 | 929 / 247 / 5.2 | 1,041 / 300 / 5.6 | 1,064 / 316 / 5.7 | 1,118 / 413 / 5.9 | 1,120 / 414 / 5.9 | 1,267 / 593 / 6.4 | 1,280 / 610 / 6.4 | 1,316 / 655 / 6.5 | 1,356 / 706 / 6.7 |
| 66.5 N | 549 / 172 / 3.6 | 631 / 202 / 4.0 | 672 / 218 / 4.1 | 695 / 228 / 4.2 | 773 / 264 / 4.5 | 830 / 294 / 4.8 | 947 / 367 / 5.2 | 1,008 / 412 / 5.5 | 1,122 / 504 / 5.9 | 1,145 / 525 / 6.0 | 1,200 / 576 / 6.2 | 1,201 / 578 / 6.2 | 1,351 / 737 / 6.7 | 1,364 / 753 / 6.8 | 1,400 / 797 / 6.9 | 1,440 / 848 / 7.0 |
| 67.5 N | 518 / 176 / 3.7 | 604 / 213 / 4.0 | 646 / 231 / 4.2 | 670 / 243 / 4.3 | 751 / 283 / 4.6 | 810 / 316 / 4.9 | 929 / 392 / 5.3 | 992 / 436 / 5.5 | 1,108 / 530 / 6.0 | 1,131 / 552 / 6.1 | 1,187 / 604 / 6.3 | 1,188 / 606 / 6.3 | 1,341 / 770 / 6.8 | 1,354 / 785 / 6.9 | 1,391 / 832 / 7.0 | 1,432 / 885 / 7.2 |
| 70 N | 397 / 96 / 3.9 | 479 / 132 / 4.2 | 521 / 154 / 4.4 | 546 / 168 / 4.5 | 638 / 220 / 4.8 | 718 / 267 / 5.1 | 874 / 414 / 5.6 | 947 / 473 / 5.8 | 1,078 / 590 / 6.3 | 1,104 / 614 / 6.4 | 1,166 / 678 / 6.6 | 1,168 / 679 / 6.6 | 1,333 / 874 / 7.2 | 1,348 / 893 / 7.2 | 1,388 / 949 / 7.4 | 1,432 / 1,015 / 7.5 |
| 72.5 N | 354 / 84 / 4.1 | 425 / 116 / 4.5 | 461 / 134 / 4.7 | 482 / 145 / 4.8 | 556 / 190 / 5.1 | 612 / 228 / 5.4 | 736 / 323 / 5.9 | 806 / 384 / 6.2 | 948 / 521 / 6.7 | 980 / 554 / 6.8 | 1,070 / 642 / 7.0 | 1,073 / 645 / 7.0 | 1,288 / 956 / 7.6 | 1,306 / 983 / 7.7 | 1,353 / 1,064 / 7.8 | 1,404 / 1,164 / 8.0 |
| 75 N | 331 / 83 / 4.4 | 396 / 114 / 4.8 | 429 / 133 / 5.0 | 449 / 145 / 5.1 | 516 / 190 / 5.5 | 568 / 228 / 5.8 | 678 / 325 / 6.4 | 740 / 388 / 6.7 | 860 / 529 / 7.2 | 885 / 563 / 7.3 | 947 / 653 / 7.5 | 949 / 655 / 7.5 | 1,133 / 1,086 / 8.2 | 1,150 / 1,137 / 8.3 | 1,200 / 1,187 / 8.4 | 1,258 / 1,243 / 8.6 |
| 80 N | 305 / 100 / 5.3 | 364 / 143 / 5.9 | 395 / 168 / 6.1 | 413 / 185 / 6.3 | 475 / 249 / 6.7 | 521 / 306 / 7.1 | 621 / 474 / 7.8 | 676 / 666 / 8.2 | 782 / 777 / 8.8 | 804 / 799 / 9.0 | 858 / 853 / 9.3 | 860 / 854 / 9.3 | 1,014 / 1,009 / 10.2 | 1,029 / 1,023 / 10.3 | 1,069 / 1,063 / 10.5 | 1,113 / 1,108 / 10.8 |
| 85 N | 293 / 214 / 7.6 | 350 / 348 / 8.4 | 379 / 377 / 8.8 | 396 / 394 / 9.1 | 456 / 453 / 9.8 | 500 / 498 / 10.4 | 596 / 593 / 11.6 | 648 / 645 / 12.2 | 749 / 746 / 13.4 | 770 / 767 / 13.6 | 821 / 819 / 14.2 | 822 / 820 / 14.3 | 968 / 966 / 16.1 | 981 / 979 / 16.3 | 1,019 / 1,016 / 16.8 | 1,060 / 1,058 / 17.5 |
| 89.5 N | 289 / 289 / 102.3 | 346 / 345 / 132.2 | 374 / 374 / 144.5 | 391 / 391 / 153.6 | 450 / 450 / 186.0 | 494 / 494 / 207.1 | 588 / 588 / 252.5 | 640 / 639 / 281.7 | 739 / 738 / 330.1 | 760 / 759 / 339.2 | 810 / 810 / 363.4 | 812 / 811 / 366.0 | 955 / 955 / 435.6 | 968 / 968 / 444.1 | 1,005 / 1,004 / 462.2 | 1,046 / 1,045 / 483.1 |
| 59 S | 276 / 0 / 0.5 | 331 / 0 / 0.6 | 359 / 0 / 0.7 | 375 / 0 / 0.7 | 432 / 0 / 0.8 | 475 / 0 / 0.9 | 567 / 0 / 1.1 | 619 / 0 / 1.2 | 719 / 0 / 1.5 | 740 / 0 / 1.6 | 793 / 0 / 1.7 | 795 / 0 / 1.7 | 954 / 138 / 2.3 | 970 / 155 / 2.4 | 1,017 / 201 / 2.7 | 1,076 / 256 / 6.2 |
| 66.5 S | 549 / 172 / 3.6 | 631 / 203 / 4.0 | 671 / 219 / 4.1 | 694 / 229 / 4.2 | 772 / 264 / 4.5 | 829 / 296 / 4.8 | 945 / 369 / 5.2 | 1,006 / 413 / 5.5 | 1,118 / 506 / 5.9 | 1,141 / 526 / 6.0 | 1,196 / 578 / 6.2 | 1,197 / 579 / 6.2 | 1,345 / 737 / 6.7 | 1,358 / 752 / 6.8 | 1,394 / 796 / 6.9 | 1,434 / 847 / 7.0 |
| 70 S | 396 / 96 / 3.9 | 476 / 132 / 4.2 | 518 / 152 / 4.4 | 543 / 166 / 4.5 | 632 / 218 / 4.8 | 710 / 264 / 5.1 | 861 / 404 / 5.6 | 933 / 462 / 5.8 | 1,061 / 576 / 6.3 | 1,087 / 601 / 6.4 | 1,148 / 663 / 6.6 | 1,149 / 665 / 6.6 | 1,311 / 856 / 7.2 | 1,326 / 876 / 7.2 | 1,365 / 930 / 7.4 | 1,408 / 995 / 7.5 |
| 77.5 S | 314 / 87 / 4.8 | 376 / 123 / 5.2 | 407 / 143 / 5.5 | 426 / 156 / 5.6 | 489 / 206 / 6.0 | 537 / 250 / 6.3 | 640 / 361 / 7.0 | 696 / 436 / 7.3 | 806 / 626 / 7.8 | 829 / 680 / 8.0 | 885 / 877 / 8.2 | 886 / 878 / 8.2 | 1,046 / 1,039 / 9.0 | 1,061 / 1,053 / 9.1 | 1,103 / 1,095 / 9.3 | 1,150 / 1,142 / 9.5 |
| 85 S | 292 / 214 / 7.7 | 349 / 347 / 8.4 | 378 / 376 / 8.9 | 395 / 393 / 9.1 | 454 / 451 / 9.8 | 498 / 496 / 10.4 | 592 / 590 / 11.6 | 644 / 642 / 12.2 | 743 / 741 / 13.4 | 764 / 762 / 13.7 | 814 / 812 / 14.3 | 816 / 813 / 14.3 | 959 / 956 / 16.2 | 972 / 969 / 16.4 | 1,008 / 1,006 / 16.9 | 1,049 / 1,047 / 17.5 |

Source: `latitude_profile.json` → `profile[].targets.<target>.flat_hours`, `.long_flat_hours["2"]`, `.longest_spell_h` (the longest single unbroken spell of the year; near the poles it runs for days).

- Grazing hours exist at every latitude, but below the latitudes in the next table they come in spells of under an hour at sunrise and sunset. At the equator the yearly total is 120 h (Connecting ridge), 143 h (Connecting Ridge Extension), 155 h (Peak Near Shackleton), 162 h (de Gerlache Rim 1), 186 h (de Gerlache Rim 2), 204 h (Faustini Rim A), 242 h (Slater Plain), 263 h (Haworth), 303 h (Malapert), 312 h (de Gerlache-Kocher Massif), 332 h (Nobile Rim 1), 332 h (Mons Mouton), 389 h (Mons Mouton Plateau), 394 h (Amundsen Rim), 409 h (Nobile Rim 2), 425 h (Peak near Cabeus B), and the longest spell is 0.17 h, 0.20 h, 0.22 h, 0.23 h, 0.27 h, 0.29 h, 0.35 h, 0.38 h, 0.43 h, 0.45 h, 0.47 h, 0.48 h, 0.56 h, 0.56 h, 0.59 h, 0.61 h.
- The yearly total is largest near the polar circle: Connecting ridge 549 h at 66.5° N; Connecting Ridge Extension 631 h at 66.5° N; Peak Near Shackleton 672 h at 66.5° N; de Gerlache Rim 1 695 h at 66.5° N; de Gerlache Rim 2 773 h at 66.5° N; Faustini Rim A 830 h at 66.5° N; Slater Plain 948 h at 67° N; Haworth 1,010 h at 67° N; Malapert 1,124 h at 67° N; de Gerlache-Kocher Massif 1,147 h at 67° N; Nobile Rim 1 1,203 h at 67° N; Mons Mouton 1,204 h at 67° N; Mons Mouton Plateau 1,355 h at 67° N; Amundsen Rim 1,368 h at 67° N; Nobile Rim 2 1,405 h at 67° N; Peak near Cabeus B 1,445 h at 67° N (4.6, 4.4, 4.3, 4.3, 4.2, 4.1, 3.9, 3.8, 3.7, 3.7, 3.6, 3.6, 3.5, 3.5, 3.4, 3.4 times the equator's total).
- Long-window hours in the northern half are largest at Connecting ridge 289 h at 86° N; Connecting Ridge Extension 348 h at 85° N; Peak Near Shackleton 378 h at 84.5° N; de Gerlache Rim 1 396 h at 84° N; de Gerlache Rim 2 458 h at 83° N; Faustini Rim A 505 h at 82.5° N; Slater Plain 609 h at 81° N; Haworth 667 h at 80.5° N; Malapert 792 h at 78.5° N; de Gerlache-Kocher Massif 815 h at 78.5° N; Nobile Rim 1 885 h at 77.5° N; Mons Mouton 887 h at 77.5° N; Mons Mouton Plateau 1,102 h at 75.5° N; Amundsen Rim 1,137 h at 75° N; Nobile Rim 2 1,211 h at 74.5° N; Peak near Cabeus B 1,315 h at 74° N.

### Lowest latitude with spells of 1, 2 and 3 hours

| Target | 1 h spell | 2 h spell | 3 h spell | Sun under the limit all day (the old measure) |
|---|---|---|---|---|
| Connecting Ridge (≤ 2.08°) | 63.95 N / 63.95 S | 64.80 N / 64.80 S | 64.80 N / 64.80 S | 64.80 N / 64.80 S |
| Connecting Ridge Extension (≤ 2.51°) | 63.00 N / 63.00 S | 64.35 N / 64.35 S | 64.35 N / 64.35 S | 64.35 N / 64.35 S |
| Peak Near Shackleton (≤ 2.73°) | 62.45 N / 62.45 S | 64.10 N / 64.10 S | 64.10 N / 64.10 S | 64.10 N / 64.10 S |
| de Gerlache Rim 1 (≤ 2.86°) | 62.15 N / 62.15 S | 64.00 N / 64.00 S | 64.00 N / 64.00 S | 64.00 N / 64.00 S |
| de Gerlache Rim 2 (≤ 3.31°) | 60.95 N / 60.95 S | 63.50 N / 63.50 S | 63.50 N / 63.50 S | 63.50 N / 63.50 S |
| Faustini Rim A (≤ 3.65°) | 60.00 N / 60.00 S | 63.10 N / 63.10 S | 63.15 N / 63.15 S | 63.15 N / 63.15 S |
| Slater Plain (≤ 4.38°) | 57.80 N / 57.80 S | 62.20 N / 62.20 S | 62.40 N / 62.40 S | 62.40 N / 62.40 S |
| Haworth (≤ 4.78°) | 56.50 N / 56.50 S | 61.70 N / 61.70 S | 62.00 N / 62.00 S | 62.00 N / 62.00 S |
| Malapert Massif (≤ 5.55°) | 53.85 N / 53.85 S | 60.65 N / 60.65 S | 61.20 N / 61.20 S | 61.20 N / 61.20 S |
| de Gerlache-Kocher Massif (≤ 5.71°) | 53.30 N / 53.30 S | 60.45 N / 60.45 S | 61.05 N / 61.05 S | 61.05 N / 61.05 S |
| Nobile Rim 1 (≤ 6.10°) | 51.85 N / 51.85 S | 59.90 N / 59.90 S | 60.65 N / 60.65 S | 60.65 N / 60.65 S |
| Mons Mouton (≤ 6.11°) | 51.80 N / 51.80 S | 59.90 N / 59.90 S | 60.60 N / 60.60 S | 60.60 N / 60.60 S |
| Mons Mouton Plateau (≤ 7.21°) | 47.45 N / 47.45 S | 58.25 N / 58.25 S | 59.50 N / 59.50 S | 59.50 N / 59.50 S |
| Amundsen Rim (≤ 7.31°) | 47.00 N / 47.00 S | 58.10 N / 58.10 S | 59.40 N / 59.40 S | 59.40 N / 59.40 S |
| Nobile Rim 2 (≤ 7.59°) | 45.85 N / 45.85 S | 57.65 N / 57.65 S | 59.10 N / 59.10 S | 59.10 N / 59.10 S |
| Peak near Cabeus B (≤ 7.90°) | 44.45 N / 44.45 S | 57.15 N / 57.15 S | 58.80 N / 58.80 S | 58.80 N / 58.80 S |

Source: `latitude_profile.json` → `thresholds.<target>.<N|S>.lowest_lat_with_long_window["1"|"2"|"3"]` and `.lowest_lat_with_all_day_low_sun`; found at steps of 0.05°. **Per-day rule (version 3):** the lowest latitude at which at least one day of the year has an unbroken spell that long.

The same thresholds under the version 2 rule, kept for comparison (the lowest latitude with a ten-day bin whose median longest daily spell, at two-minute steps, reaches the minimum):

| Target | 1 h spell | 2 h spell | 3 h spell |
|---|---|---|---|
| Connecting Ridge (≤ 2.08°) | 63.95 N / 63.95 S | 64.85 N / 64.85 S | 64.85 N / 64.85 S |
| Connecting Ridge Extension (≤ 2.51°) | 62.95 N / 62.95 S | 64.40 N / 64.40 S | 64.40 N / 64.40 S |
| Peak Near Shackleton (≤ 2.73°) | 62.40 N / 62.40 S | 64.15 N / 64.15 S | 64.15 N / 64.15 S |
| de Gerlache Rim 1 (≤ 2.86°) | 62.10 N / 62.10 S | 64.00 N / 64.00 S | 64.00 N / 64.05 S |
| de Gerlache Rim 2 (≤ 3.31°) | 60.90 N / 60.85 S | 63.50 N / 63.50 S | 63.55 N / 63.55 S |
| Faustini Rim A (≤ 3.65°) | 59.95 N / 59.90 S | 63.15 N / 63.15 S | 63.20 N / 63.20 S |
| Slater Plain (≤ 4.38°) | 57.65 N / 57.65 S | 62.25 N / 62.25 S | 62.45 N / 62.40 S |
| Haworth (≤ 4.78°) | 56.30 N / 56.30 S | 61.75 N / 61.70 S | 62.05 N / 62.00 S |
| Malapert Massif (≤ 5.55°) | 53.55 N / 53.50 S | 60.70 N / 60.70 S | 61.25 N / 61.20 S |
| de Gerlache-Kocher Massif (≤ 5.71°) | 52.90 N / 52.85 S | 60.45 N / 60.45 S | 61.10 N / 61.05 S |
| Nobile Rim 1 (≤ 6.10°) | 51.40 N / 51.35 S | 59.90 N / 59.90 S | 60.70 N / 60.65 S |
| Mons Mouton (≤ 6.11°) | 51.40 N / 51.35 S | 59.90 N / 59.90 S | 60.65 N / 60.65 S |
| Mons Mouton Plateau (≤ 7.21°) | 46.90 N / 46.90 S | 58.20 N / 58.20 S | 59.55 N / 59.55 S |
| Amundsen Rim (≤ 7.31°) | 46.45 N / 46.50 S | 58.10 N / 58.10 S | 59.45 N / 59.45 S |
| Nobile Rim 2 (≤ 7.59°) | 45.00 N / 45.00 S | 57.65 N / 57.65 S | 59.15 N / 59.15 S |
| Peak near Cabeus B (≤ 7.90°) | 43.80 N / 43.80 S | 57.15 N / 57.15 S | 58.85 N / 58.85 S |

Source: `latitude_profile.json` → `thresholds.<target>.<N|S>.lowest_lat_with_long_window_bin_median["1"|"2"|"3"]`.

### What the search band does not cover

The search looked at land from 59 to 84 N and from 59 to 87.5 S (`twinfinder/grid.py`: `MIN_LAT`, `MAX_LAT`, `SOUTH_MIN_LAT`, `SOUTH_MAX_LAT`). Degrees of latitude between the first long window and the band edge, in each hemisphere:

| Target | 1 h spells | 2 h spells (the rule used) | 3 h spells |
|---|---|---|---|
| Connecting ridge | none (starts at 63.95) | none (starts at 64.80) | none (starts at 64.80) |
| Connecting Ridge Extension | none (starts at 63.00) | none (starts at 64.35) | none (starts at 64.35) |
| Peak Near Shackleton | none (starts at 62.45) | none (starts at 64.10) | none (starts at 64.10) |
| de Gerlache Rim 1 | none (starts at 62.15) | none (starts at 64.00) | none (starts at 64.00) |
| de Gerlache Rim 2 | none (starts at 60.95) | none (starts at 63.50) | none (starts at 63.50) |
| Faustini Rim A | none (starts at 60.00) | none (starts at 63.10) | none (starts at 63.15) |
| Slater Plain | 1.20° (57.80 to 59) | none (starts at 62.20) | none (starts at 62.40) |
| Haworth | 2.50° (56.50 to 59) | none (starts at 61.70) | none (starts at 62.00) |
| Malapert | 5.15° (53.85 to 59) | none (starts at 60.65) | none (starts at 61.20) |
| de Gerlache-Kocher Massif | 5.70° (53.30 to 59) | none (starts at 60.45) | none (starts at 61.05) |
| Nobile Rim 1 | 7.15° (51.85 to 59) | none (starts at 59.90) | none (starts at 60.65) |
| Mons Mouton | 7.20° (51.80 to 59) | none (starts at 59.90) | none (starts at 60.60) |
| Mons Mouton Plateau | 11.55° (47.45 to 59) | 0.75° (58.25 to 59) | none (starts at 59.50) |
| Amundsen Rim | 12.00° (47.00 to 59) | 0.90° (58.10 to 59) | none (starts at 59.40) |
| Nobile Rim 2 | 13.15° (45.85 to 59) | 1.35° (57.65 to 59) | none (starts at 59.10) |
| Peak near Cabeus B | 14.55° (44.45 to 59) | 1.85° (57.15 to 59) | 0.20° (58.80 to 59) |

Source: 59.0 minus `latitude_profile.json` → `thresholds.<target>.N.lowest_lat_with_long_window["1"|"2"|"3"]` (the table above; the southern values are the same to 0.05°).

- With the 2 h rule used for the ranking, Mons Mouton Plateau loses ground: its long windows begin at 58.25°, so a strip of 0.75° on each side of the Earth was not looked at. Flat-horizon long-window hours there: 0 h a year at 58.0 N, 72 h at 58.5 N, 129 h at 59.0 N (`profile[].targets.mons-mouton-plateau.long_flat_hours["2"]`).
- With the 2 h rule used for the ranking, Amundsen Rim loses ground: its long windows begin at 58.10°, so a strip of 0.90° on each side of the Earth was not looked at. Flat-horizon long-window hours there: 0 h a year at 58.0 N, 91 h at 58.5 N, 144 h at 59.0 N (`profile[].targets.amundsen-rim.long_flat_hours["2"]`).
- With the 2 h rule used for the ranking, Nobile Rim 2 loses ground: its long windows begin at 57.65°, so a strip of 1.35° on each side of the Earth was not looked at. Flat-horizon long-window hours there: 83 h a year at 58.0 N, 136 h at 58.5 N, 188 h at 59.0 N (`profile[].targets.nobile-rim-2.long_flat_hours["2"]`).
- With the 2 h rule used for the ranking, Peak near Cabeus B loses ground: its long windows begin at 57.15°, so a strip of 1.85° on each side of the Earth was not looked at. Flat-horizon long-window hours there: 135 h a year at 58.0 N, 182 h at 58.5 N, 239 h at 59.0 N (`profile[].targets.peak-near-cabeus-b.long_flat_hours["2"]`).
- With a 1 h rule the belt would reach much further toward the equator (first column); none of that ground was searched.
- With a 3 h rule every target's belt starts inside the band.

## (b) The north in the winter half (28 September to 31 March)

Long-window hours on snow-free ground, flat horizon, over the 14,863 measured northern cells (695,227 km² of bare ground; 3 of the cells have unknown hours and are counted in no column).

| Target | ≥ 50 h | ≥ 100 h | ≥ 200 h | with the real horizon, over the 14,833 measured cells that have one (30 have none): cells ≥ 50 / 100 / 200 h |
|---|---|---|---|---|
| Connecting ridge | 0 cells, 0 km² | 0 cells, 0 km² | 0 cells, 0 km² | 0 / 0 / 0 |
| Connecting Ridge Extension | 0 cells, 0 km² | 0 cells, 0 km² | 0 cells, 0 km² | 0 / 0 / 0 |
| Peak Near Shackleton | 0 cells, 0 km² | 0 cells, 0 km² | 0 cells, 0 km² | 0 / 0 / 0 |
| de Gerlache Rim 1 | 0 cells, 0 km² | 0 cells, 0 km² | 0 cells, 0 km² | 0 / 0 / 0 |
| de Gerlache Rim 2 | 0 cells, 0 km² | 0 cells, 0 km² | 0 cells, 0 km² | 0 / 0 / 0 |
| Faustini Rim A | 1 cells, 39 km² | 0 cells, 0 km² | 0 cells, 0 km² | 0 / 0 / 0 |
| Slater Plain | 25 cells, 1,180 km² | 0 cells, 0 km² | 0 cells, 0 km² | 24 / 0 / 0 |
| Haworth | 43 cells, 1,924 km² | 1 cells, 39 km² | 0 cells, 0 km² | 31 / 0 / 0 |
| Malapert | 71 cells, 2,768 km² | 15 cells, 706 km² | 0 cells, 0 km² | 36 / 12 / 0 |
| de Gerlache-Kocher Massif | 79 cells, 3,074 km² | 22 cells, 1,018 km² | 0 cells, 0 km² | 39 / 20 / 0 |
| Nobile Rim 1 | 102 cells, 4,274 km² | 28 cells, 1,270 km² | 0 cells, 0 km² | 47 / 25 / 0 |
| Mons Mouton | 102 cells, 4,274 km² | 28 cells, 1,270 km² | 0 cells, 0 km² | 47 / 25 / 0 |
| Mons Mouton Plateau | 160 cells, 6,703 km² | 35 cells, 1,672 km² | 1 cells, 39 km² | 64 / 33 / 0 |
| Amundsen Rim | 172 cells, 6,989 km² | 35 cells, 1,672 km² | 1 cells, 39 km² | 67 / 34 / 0 |
| Nobile Rim 2 | 193 cells, 7,550 km² | 40 cells, 1,768 km² | 4 cells, 65 km² | 75 / 34 / 3 |
| Peak near Cabeus B | 230 cells, 8,760 km² | 49 cells, 1,929 km² | 11 cells, 293 km² | 91 / 36 / 11 |

Source: `validation.json` → `big_picture_north.targets.<target>.long_snow_free_hours.winter_half.<50|100|200>.cells` and `.bare_km2`; last column `...long_open_hours_among_cells_with_a_horizon.winter_half` (every measured cell that has a terrain horizon; the cells without one are described in (i), so that column is a lower bound on the true count). The cell counts and areas of this table and of the one in (c), with their real-horizon columns, were made again in this run from `grazing_cells.json` (`targets.<target>.long_snow_free_hours_winter`, `_summer`, `long_open_hours_winter`, `_summer`, `bare_km2`): 384 counts, 0 differ.

- Share of all long-window snow-free hours × bare km² that falls in the winter half: Connecting ridge 0.6%; Connecting Ridge Extension 0.6%; Peak Near Shackleton 0.7%; de Gerlache Rim 1 0.7%; de Gerlache Rim 2 0.9%; Faustini Rim A 1.1%; Slater Plain 1.3%; Haworth 1.4%; Malapert 1.6%; de Gerlache-Kocher Massif 1.7%; Nobile Rim 1 1.8%; Mons Mouton 1.8%; Mons Mouton Plateau 2.1%; Amundsen Rim 2.1%; Nobile Rim 2 2.2%; Peak near Cabeus B 2.2% (`big_picture_north.targets.<target>.calendar_hours_times_bare_km2`, winter bins over all bins).
- Regions of the cells with at least 100 winter-half hours: Connecting ridge: no cell; Connecting Ridge Extension: no cell; Peak Near Shackleton: no cell; de Gerlache Rim 1: no cell; de Gerlache Rim 2: no cell; Faustini Rim A: no cell; Slater Plain: no cell; Haworth: Iceland 1; Malapert: Iceland 15; de Gerlache-Kocher Massif: Iceland 22; Nobile Rim 1: Iceland 28; Mons Mouton: Iceland 28; Mons Mouton Plateau: Iceland 35; Amundsen Rim: Iceland 35; Nobile Rim 2: Iceland 39, Svalbard 1; Peak near Cabeus B: Iceland 46, Svalbard 2, Novaya Zemlya 1 (`validation.json` → `regions.<target>.measured_cells_100_long_snow_free_hours_winter_half`).

The measured cell with the most winter-half hours per target:

| Target | Cell centre | Region | Bare | Winter-half hours, snow-free | the same with the real horizon | Share of the year's long-window hours with the Sun on the poleward side |
|---|---|---|---|---|---|---|
| Connecting ridge | 66.25, -15.75 | Iceland | 0.19 | 15.2 | 1.9 | 0.36 |
| Connecting Ridge Extension | 66.25, -15.75 | Iceland | 0.19 | 19.6 | 3.2 | 0.34 |
| Peak Near Shackleton | 66.25, -15.75 | Iceland | 0.19 | 21.9 | 4.0 | 0.34 |
| de Gerlache Rim 1 | 66.05, -18.45 | Iceland | 0.22 | 23.3 | 1.5 | 0.21 |
| de Gerlache Rim 2 | 63.85, -22.70 | Iceland | 0.68 | 35.9 | 31.0 | 0.00 |
| Faustini Rim A | 63.85, -22.70 | Iceland | 0.68 | 50.4 | 43.8 | 0.00 |
| Slater Plain | 63.85, -22.70 | Iceland | 0.68 | 84.0 | 73.8 | 0.00 |
| Haworth | 63.85, -22.70 | Iceland | 0.68 | 101.5 | 89.7 | 0.00 |
| Malapert | 63.85, -22.70 | Iceland | 0.68 | 135.9 | 121.2 | 0.00 |
| de Gerlache-Kocher Massif | 63.85, -22.70 | Iceland | 0.68 | 143.2 | 128.0 | 0.00 |
| Nobile Rim 1 | 63.85, -22.70 | Iceland | 0.68 | 160.3 | 143.8 | 0.00 |
| Mons Mouton | 63.85, -22.70 | Iceland | 0.68 | 161.0 | 144.5 | 0.00 |
| Mons Mouton Plateau | 63.85, -22.70 | Iceland | 0.68 | 211.0 | 191.2 | 0.00 |
| Amundsen Rim | 63.85, -22.70 | Iceland | 0.68 | 215.7 | 195.6 | 0.08 |
| Nobile Rim 2 | 63.85, -22.70 | Iceland | 0.68 | 228.2 | 207.4 | 0.16 |
| Peak near Cabeus B | 63.85, -22.70 | Iceland | 0.68 | 243.3 | 221.5 | 0.21 |

Source: `grazing_cells.json` → `targets.<target>.long_snow_free_hours_winter`, `long_open_hours_winter`, `poleward_share`. A poleward share near 0 means the low Sun stands in the south: dawn, dusk and low noon, not midnight Sun.

## (c) The north in the summer half (1 April to 27 September): the midnight-Sun side

| Target | ≥ 50 h | ≥ 100 h | ≥ 200 h | with the real horizon, over the 14,833 measured cells that have one (30 have none): cells ≥ 50 / 100 / 200 h |
|---|---|---|---|---|
| Connecting ridge | 285 cells, 11,719 km² | 2 cells, 74 km² | 0 cells, 0 km² | 15 / 0 / 0 |
| Connecting Ridge Extension | 791 cells, 33,403 km² | 44 cells, 1,358 km² | 0 cells, 0 km² | 75 / 3 / 0 |
| Peak Near Shackleton | 1,174 cells, 50,457 km² | 114 cells, 3,647 km² | 0 cells, 0 km² | 174 / 6 / 0 |
| de Gerlache Rim 1 | 1,498 cells, 63,533 km² | 152 cells, 4,921 km² | 0 cells, 0 km² | 266 / 9 / 0 |
| de Gerlache Rim 2 | 5,464 cells, 280,087 km² | 429 cells, 16,464 km² | 0 cells, 0 km² | 872 / 63 / 0 |
| Faustini Rim A | 7,040 cells, 370,565 km² | 706 cells, 27,651 km² | 0 cells, 0 km² | 1,985 / 140 / 0 |
| Slater Plain | 8,466 cells, 437,671 km² | 2,275 cells, 95,297 km² | 13 cells, 280 km² | 3,937 / 489 / 2 |
| Haworth | 8,928 cells, 456,533 km² | 5,467 cells, 283,546 km² | 60 cells, 1,527 km² | 4,706 / 1,336 / 6 |
| Malapert | 9,584 cells, 485,371 km² | 7,361 cells, 385,751 km² | 503 cells, 18,464 km² | 5,909 / 3,145 / 57 |
| de Gerlache-Kocher Massif | 9,706 cells, 490,992 km² | 7,630 cells, 399,180 km² | 649 cells, 24,031 km² | 6,173 / 3,436 / 86 |
| Nobile Rim 1 | 9,976 cells, 504,295 km² | 8,179 cells, 425,568 km² | 1,315 cells, 51,223 km² | 6,783 / 4,014 / 218 |
| Mons Mouton | 9,984 cells, 505,024 km² | 8,192 cells, 426,173 km² | 1,339 cells, 52,379 km² | 6,797 / 4,028 / 222 |
| Mons Mouton Plateau | 10,828 cells, 543,202 km² | 9,466 cells, 485,128 km² | 5,541 cells, 289,624 km² | 8,138 / 5,591 / 2,384 |
| Amundsen Rim | 10,932 cells, 547,441 km² | 9,556 cells, 489,384 km² | 5,708 cells, 298,177 km² | 8,241 / 5,733 / 2,561 |
| Nobile Rim 2 | 11,190 cells, 558,401 km² | 9,849 cells, 503,036 km² | 6,231 cells, 325,977 km² | 8,550 / 6,114 / 2,936 |
| Peak near Cabeus B | 11,480 cells, 570,191 km² | 10,130 cells, 515,592 km² | 6,773 cells, 354,385 km² | 8,925 / 6,539 / 3,264 |

Source: as in (b), with `summer_half` (`long_snow_free_hours_summer`, `long_open_hours_summer` in `grazing_cells.json`).

- Connecting ridge: 99.4% of the long-window snow-free hours × bare km² fall in the summer half; the three ten-day bins with the most are 9 Aug-18 Aug (19%), 30 Jul-8 Aug (15%), 19 Aug-28 Aug (15%).
- Connecting Ridge Extension: 99.4% of the long-window snow-free hours × bare km² fall in the summer half; the three ten-day bins with the most are 9 Aug-18 Aug (19%), 19 Aug-28 Aug (15%), 30 Jul-8 Aug (15%).
- Peak Near Shackleton: 99.3% of the long-window snow-free hours × bare km² fall in the summer half; the three ten-day bins with the most are 9 Aug-18 Aug (19%), 19 Aug-28 Aug (15%), 30 Jul-8 Aug (15%).
- de Gerlache Rim 1: 99.3% of the long-window snow-free hours × bare km² fall in the summer half; the three ten-day bins with the most are 9 Aug-18 Aug (19%), 19 Aug-28 Aug (15%), 30 Jul-8 Aug (15%).
- de Gerlache Rim 2: 99.1% of the long-window snow-free hours × bare km² fall in the summer half; the three ten-day bins with the most are 9 Aug-18 Aug (18%), 19 Aug-28 Aug (15%), 30 Jul-8 Aug (15%).
- Faustini Rim A: 98.9% of the long-window snow-free hours × bare km² fall in the summer half; the three ten-day bins with the most are 9 Aug-18 Aug (18%), 19 Aug-28 Aug (16%), 30 Jul-8 Aug (15%).
- Slater Plain: 98.7% of the long-window snow-free hours × bare km² fall in the summer half; the three ten-day bins with the most are 9 Aug-18 Aug (18%), 19 Aug-28 Aug (16%), 30 Jul-8 Aug (15%).
- Haworth: 98.6% of the long-window snow-free hours × bare km² fall in the summer half; the three ten-day bins with the most are 9 Aug-18 Aug (17%), 19 Aug-28 Aug (16%), 30 Jul-8 Aug (15%).
- Malapert: 98.4% of the long-window snow-free hours × bare km² fall in the summer half; the three ten-day bins with the most are 9 Aug-18 Aug (17%), 19 Aug-28 Aug (16%), 30 Jul-8 Aug (15%).
- de Gerlache-Kocher Massif: 98.3% of the long-window snow-free hours × bare km² fall in the summer half; the three ten-day bins with the most are 9 Aug-18 Aug (17%), 19 Aug-28 Aug (15%), 30 Jul-8 Aug (15%).
- Nobile Rim 1: 98.2% of the long-window snow-free hours × bare km² fall in the summer half; the three ten-day bins with the most are 9 Aug-18 Aug (17%), 19 Aug-28 Aug (15%), 30 Jul-8 Aug (15%).
- Mons Mouton: 98.2% of the long-window snow-free hours × bare km² fall in the summer half; the three ten-day bins with the most are 9 Aug-18 Aug (17%), 19 Aug-28 Aug (15%), 30 Jul-8 Aug (15%).
- Mons Mouton Plateau: 97.9% of the long-window snow-free hours × bare km² fall in the summer half; the three ten-day bins with the most are 9 Aug-18 Aug (16%), 19 Aug-28 Aug (14%), 30 Jul-8 Aug (14%).
- Amundsen Rim: 97.9% of the long-window snow-free hours × bare km² fall in the summer half; the three ten-day bins with the most are 9 Aug-18 Aug (16%), 30 Jul-8 Aug (14%), 19 Aug-28 Aug (14%).
- Nobile Rim 2: 97.8% of the long-window snow-free hours × bare km² fall in the summer half; the three ten-day bins with the most are 9 Aug-18 Aug (16%), 30 Jul-8 Aug (14%), 19 Aug-28 Aug (14%).
- Peak near Cabeus B: 97.8% of the long-window snow-free hours × bare km² fall in the summer half; the three ten-day bins with the most are 9 Aug-18 Aug (16%), 30 Jul-8 Aug (14%), 19 Aug-28 Aug (14%).

| Target | Cells with ≥ 100 summer-half hours | Regions (cells) |
|---|---|---|
| Connecting ridge | 2 | Alaska 1, Norway, Sweden or Finland 1 |
| Connecting Ridge Extension | 44 | Siberia and the Russian Far East 16, Alaska 13, Arctic Canada 8, Greenland 3, Kola and north-west Russia 3, Norway, Sweden or Finland 1 |
| Peak Near Shackleton | 114 | Siberia and the Russian Far East 49, Alaska 33, Arctic Canada 22, Kola and north-west Russia 5, Greenland 4, Norway, Sweden or Finland 1 |
| de Gerlache Rim 1 | 152 | Siberia and the Russian Far East 63, Alaska 45, Arctic Canada 32, Greenland 6, Kola and north-west Russia 5, Norway, Sweden or Finland 1 |
| de Gerlache Rim 2 | 429 | Siberia and the Russian Far East 166, Alaska 148, Arctic Canada 96, Kola and north-west Russia 11, Greenland 7, Norway, Sweden or Finland 1 |
| Faustini Rim A | 706 | Siberia and the Russian Far East 255, Arctic Canada 222, Alaska 195, Greenland 14, Kola and north-west Russia 12, Norway, Sweden or Finland 8 |
| Slater Plain | 2,275 | Arctic Canada 1,139, Siberia and the Russian Far East 383, Greenland 248, Alaska 237, North-west Greenland or Ellesmere 77, Norway, Sweden or Finland 67; other regions 124 |
| Haworth | 5,467 | Arctic Canada 3,630, Siberia and the Russian Far East 628, Greenland 404, Alaska 243, North-west Greenland or Ellesmere 202, Svalbard 102; other regions 258 |
| Malapert | 7,361 | Arctic Canada 4,687, Greenland 771, Siberia and the Russian Far East 701, North-west Greenland or Ellesmere 340, Alaska 246, Svalbard 190; other regions 426 |
| de Gerlache-Kocher Massif | 7,630 | Arctic Canada 4,800, Greenland 853, Siberia and the Russian Far East 714, North-west Greenland or Ellesmere 351, Alaska 246, Svalbard 212; other regions 454 |
| Nobile Rim 1 | 8,179 | Arctic Canada 5,071, Greenland 990, Siberia and the Russian Far East 746, North-west Greenland or Ellesmere 374, Alaska 250, Svalbard 232; other regions 516 |
| Mons Mouton | 8,192 | Arctic Canada 5,079, Greenland 994, Siberia and the Russian Far East 746, North-west Greenland or Ellesmere 374, Alaska 250, Svalbard 232; other regions 517 |
| Mons Mouton Plateau | 9,466 | Arctic Canada 5,723, Greenland 1,300, Siberia and the Russian Far East 829, North-west Greenland or Ellesmere 418, Svalbard 257, Alaska 252; other regions 687 |
| Amundsen Rim | 9,556 | Arctic Canada 5,768, Greenland 1,313, Siberia and the Russian Far East 835, North-west Greenland or Ellesmere 420, Svalbard 260, Alaska 252; other regions 708 |
| Nobile Rim 2 | 9,849 | Arctic Canada 5,932, Greenland 1,366, Siberia and the Russian Far East 855, North-west Greenland or Ellesmere 424, Svalbard 266, Novaya Zemlya 258; other regions 748 |
| Peak near Cabeus B | 10,130 | Arctic Canada 6,085, Greenland 1,412, Siberia and the Russian Far East 876, North-west Greenland or Ellesmere 427, Svalbard 267, Novaya Zemlya 262; other regions 801 |

Source: `validation.json` → `regions.<target>.measured_cells_100_long_snow_free_hours_summer_half`.

| Target | Cells with ≥ 100 summer-half hours | Median share of long-window hours with the Sun within 90° of north | 10th to 90th percentile | Latitudes, 10th to 90th percentile |
|---|---|---|---|---|
| Connecting ridge | 2 | 0.64 | 0.62 to 0.66 | 67.1 to 67.5 N |
| Connecting Ridge Extension | 44 | 0.65 | 0.63 to 0.67 | 67.3 to 68.0 N |
| Peak Near Shackleton | 114 | 0.66 | 0.61 to 0.67 | 67.3 to 68.2 N |
| de Gerlache Rim 1 | 152 | 0.65 | 0.61 to 0.67 | 67.3 to 68.3 N |
| de Gerlache Rim 2 | 429 | 0.65 | 0.60 to 0.67 | 67.5 to 69.0 N |
| Faustini Rim A | 706 | 0.65 | 0.59 to 0.67 | 67.5 to 69.3 N |
| Slater Plain | 2,275 | 0.62 | 0.51 to 0.66 | 67.8 to 81.2 N |
| Haworth | 5,467 | 0.57 | 0.52 to 0.65 | 68.3 to 80.2 N |
| Malapert | 7,361 | 0.56 | 0.52 to 0.65 | 68.0 to 80.7 N |
| de Gerlache-Kocher Massif | 7,630 | 0.56 | 0.52 to 0.64 | 68.0 to 80.7 N |
| Nobile Rim 1 | 8,179 | 0.56 | 0.52 to 0.64 | 67.8 to 80.8 N |
| Mons Mouton | 8,192 | 0.56 | 0.52 to 0.64 | 67.8 to 80.8 N |
| Mons Mouton Plateau | 9,466 | 0.55 | 0.52 to 0.63 | 67.2 to 81.0 N |
| Amundsen Rim | 9,556 | 0.55 | 0.52 to 0.63 | 67.2 to 81.0 N |
| Nobile Rim 2 | 9,849 | 0.56 | 0.50 to 0.62 | 66.8 to 81.0 N |
| Peak near Cabeus B | 10,130 | 0.56 | 0.46 to 0.62 | 66.5 to 81.0 N |

Source: `grazing_cells.json` → `targets.<target>.poleward_share` (whole year, flat horizon), `long_snow_free_hours_summer`, `lat`. A share above 0.5 means most of the long-window hours come with the Sun in the northern half of the sky, around local midnight.

## (d) What real terrain takes away

Version 2 could measure this only on a blind sample: 300 measured northern and 150 southern cells drawn without looking at any score (`candidates.json` → `why` contains `sample`). Version 3 has a terrain horizon for 14,833 of the 14,863 measured northern cells and 1,220 of the 1,241 southern cells, so the same statistic is given for all of them beside the sample's. The share is long-window open hours ÷ long-window flat-horizon hours per cell (north: snow-free hours; south: rock-season hours), over the cells that have a horizon and any such hours.

| Target | North, blind sample: cells | share left, 10th / 25th / median / 75th / 90th percentile | North, every measured cell with a horizon: cells | share left | South, blind sample: cells | share left | South, every cell with a horizon: cells | share left |
|---|---|---|---|---|---|---|---|---|
| Connecting ridge | 220 | 0.047 / 0.115 / 0.292 / 0.588 / 0.847 | 10,427 | 0.047 / 0.114 / 0.286 / 0.547 / 0.787 | 104 | 0.012 / 0.051 / 0.147 / 0.366 / 0.548 | 885 | 0.012 / 0.050 / 0.148 / 0.337 / 0.540 |
| Connecting Ridge Extension | 220 | 0.055 / 0.131 / 0.325 / 0.658 / 0.884 | 10,454 | 0.063 / 0.143 / 0.333 / 0.601 / 0.826 | 111 | 0.020 / 0.083 / 0.188 / 0.402 / 0.596 | 926 | 0.019 / 0.068 / 0.183 / 0.382 / 0.578 |
| Peak Near Shackleton | 220 | 0.063 / 0.142 / 0.346 / 0.686 / 0.890 | 10,469 | 0.070 / 0.153 / 0.352 / 0.624 / 0.841 | 114 | 0.023 / 0.101 / 0.211 / 0.411 / 0.604 | 946 | 0.020 / 0.075 / 0.195 / 0.393 / 0.581 |
| de Gerlache Rim 1 | 220 | 0.068 / 0.146 / 0.356 / 0.703 / 0.890 | 10,480 | 0.074 / 0.158 / 0.361 / 0.634 / 0.848 | 116 | 0.025 / 0.100 / 0.214 / 0.420 / 0.603 | 961 | 0.023 / 0.079 / 0.201 / 0.402 / 0.599 |
| de Gerlache Rim 2 | 221 | 0.081 / 0.160 / 0.395 / 0.729 / 0.901 | 10,586 | 0.089 / 0.180 / 0.396 / 0.670 / 0.868 | 122 | 0.033 / 0.122 / 0.251 / 0.442 / 0.621 | 1,000 | 0.033 / 0.097 / 0.233 / 0.427 / 0.624 |
| Faustini Rim A | 221 | 0.095 / 0.185 / 0.424 / 0.748 / 0.907 | 10,646 | 0.099 / 0.197 / 0.421 / 0.691 / 0.876 | 130 | 0.047 / 0.148 / 0.268 / 0.470 / 0.638 | 1,050 | 0.042 / 0.114 / 0.256 / 0.453 / 0.645 |
| Slater Plain | 225 | 0.116 / 0.227 / 0.473 / 0.780 / 0.908 | 10,838 | 0.121 / 0.229 / 0.465 / 0.725 / 0.889 | 133 | 0.085 / 0.190 / 0.320 / 0.509 / 0.664 | 1,101 | 0.069 / 0.159 / 0.304 / 0.503 / 0.667 |
| Haworth | 231 | 0.119 / 0.243 / 0.497 / 0.780 / 0.908 | 11,012 | 0.132 / 0.244 / 0.485 / 0.741 / 0.896 | 136 | 0.101 / 0.206 / 0.344 / 0.526 / 0.677 | 1,107 | 0.084 / 0.180 / 0.327 / 0.520 / 0.680 |
| Malapert | 239 | 0.145 / 0.271 / 0.535 / 0.808 / 0.912 | 11,330 | 0.146 / 0.266 / 0.513 / 0.763 / 0.906 | 136 | 0.133 / 0.235 / 0.397 / 0.554 / 0.678 | 1,118 | 0.105 / 0.210 / 0.361 / 0.547 / 0.692 |
| de Gerlache-Kocher Massif | 241 | 0.148 / 0.271 / 0.543 / 0.809 / 0.913 | 11,418 | 0.152 / 0.272 / 0.520 / 0.768 / 0.908 | 137 | 0.143 / 0.232 / 0.407 / 0.563 / 0.682 | 1,122 | 0.113 / 0.216 / 0.374 / 0.558 / 0.698 |
| Nobile Rim 1 | 248 | 0.159 / 0.291 / 0.561 / 0.817 / 0.919 | 11,715 | 0.160 / 0.284 / 0.535 / 0.780 / 0.912 | 139 | 0.163 / 0.261 / 0.437 / 0.576 / 0.693 | 1,130 | 0.134 / 0.237 / 0.400 / 0.578 / 0.708 |
| Mons Mouton | 248 | 0.159 / 0.292 / 0.561 / 0.818 / 0.920 | 11,719 | 0.160 / 0.285 / 0.535 / 0.780 / 0.912 | 139 | 0.163 / 0.263 / 0.437 / 0.576 / 0.694 | 1,130 | 0.135 / 0.238 / 0.400 / 0.579 / 0.708 |
| Mons Mouton Plateau | 261 | 0.176 / 0.303 / 0.585 / 0.811 / 0.930 | 12,500 | 0.182 / 0.315 / 0.571 / 0.801 / 0.919 | 143 | 0.206 / 0.312 / 0.487 / 0.609 / 0.728 | 1,175 | 0.181 / 0.297 / 0.445 / 0.617 / 0.730 |
| Amundsen Rim | 262 | 0.178 / 0.305 / 0.584 / 0.813 / 0.930 | 12,588 | 0.183 / 0.318 / 0.573 / 0.804 / 0.919 | 144 | 0.210 / 0.312 / 0.484 / 0.609 / 0.730 | 1,183 | 0.184 / 0.300 / 0.447 / 0.619 / 0.730 |
| Nobile Rim 2 | 263 | 0.184 / 0.310 / 0.593 / 0.817 / 0.933 | 12,814 | 0.188 / 0.324 / 0.582 / 0.809 / 0.921 | 144 | 0.217 / 0.321 / 0.491 / 0.612 / 0.735 | 1,190 | 0.192 / 0.310 / 0.459 / 0.626 / 0.733 |
| Peak near Cabeus B | 267 | 0.191 / 0.318 / 0.585 / 0.819 / 0.934 | 13,047 | 0.191 / 0.327 / 0.585 / 0.813 / 0.922 | 144 | 0.227 / 0.328 / 0.496 / 0.613 / 0.743 | 1,192 | 0.200 / 0.319 / 0.469 / 0.632 / 0.741 |

Source: `validation.json` → `terrain_share_left.<north|south>.<blind_sample|all_measured|all>.<target>` (`cells`, `p10`, `p25`, `median`, `p75`, `p90`), computed from `grazing_cells.json` → `targets.<target>.long_open_hours` ÷ `long_snow_free_hours` (north), `long_summer_rock_open_hours` ÷ `long_summer_rock_hours` (south).

- The lower the Sun limit, the more the terrain takes. The median measured northern cell with a horizon keeps 28.6% (Connecting ridge), 33.3% (Connecting Ridge Extension), 35.2% (Peak Near Shackleton), 36.1% (de Gerlache Rim 1), 39.6% (de Gerlache Rim 2), 42.1% (Faustini Rim A), 46.5% (Slater Plain), 48.5% (Haworth), 51.3% (Malapert), 52.0% (de Gerlache-Kocher Massif), 53.5% (Nobile Rim 1), 53.5% (Mons Mouton), 57.1% (Mons Mouton Plateau), 57.3% (Amundsen Rim), 58.2% (Nobile Rim 2), 58.5% (Peak near Cabeus B); the blind sample said 29.2%, 32.5%, 34.6%, 35.6%, 39.5%, 42.4%, 47.3%, 49.7%, 53.5%, 54.3%, 56.1%, 56.1%, 58.5%, 58.4%, 59.3%, 58.5%.
- Median terrain horizon: blind sample 2.43° looking north and 2.45° looking south; all 14,833 measured cells with a horizon 2.42° and 2.39° (`terrain_share_left.north.<group>.horizon`; the median over the cell's land of the horizon in the due-north and due-south sectors).
- **The census covers every measured cell but those across the 180° meridian.** 30 measured northern cells have no horizon (window across the antimeridian: 30); every other measured cell has one, so the census figures no longer rest on the cells whose elevation tiles happened to be on disk. The blind sample was drawn over all measured cells without looking at any score, and 299 of its 300 northern cells and 148 of its 150 southern cells have a horizon (without one: north window across the antimeridian: 1; south window across the antimeridian: 2). The two are two estimates of a typical cell and differ as the table shows.

Named examples (the cell that holds the site; hours are for Malapert, long windows, whole year):

| Site | Cell | Horizon north / south | Flat | Snow-free | Open | Share of snow-free hours left |
|---|---|---|---|---|---|---|
| Qaqortorsuaq anorthosite, Greenland | 66.5_-52.2 | 5.96° / 5.91° | 503.7 | 170.9 | 43.4 | 25% |
| Lofoten anorthosite (Nusfjord), Norway | 68.0_13.2 | 10.10° / 5.30° | 548.9 | 351.0 | 70.6 | 20% |
| Longyearbyen, Svalbard | 78.2_15.6 | 12.89° / 7.51° | 726.6 | 75.3 | 14.0 | 19% |
| Myrdalssandur sand plain, Iceland | 63.4_-18.6 | 0.34° / -0.12° | 263.0 | 98.4 | 97.7 | 99% |

Source: `validation.json` → `named_sites.sites[].targets.malapert.<flat|snow_free|open>.long.year` and `.horizon`.

## (e) The top sites per target

Scores: light = min(1, long-window open hours ÷ 200); "lighting" = √(light × bare); "full" = fourth root of light × terrain × rock × bare (`cells_scored.json` → `meta.full_hours`, `meta.goals`). Only measured northern cells with a horizon and bare ≥ 0.25 are ranked (10,837 cells, though 3 of them have unknown snow-free hours, so no score, and are in no table; 15 more measured cells with enough bare ground have no horizon and could not compete), one site per 50 km. Cells with equal scores are ordered by their long-window open hours. The clear-sky column is for information (see (j)); it enters no score.

### Connecting Ridge (Sun at or below 2.08°)

**Lighting goal (low Sun on bare ground), top 5 of the north:**

| # | Cell centre (lat, lon) | Region | Bare | Long-window hours a year: open (snow-free over a flat horizon) | Typical clear-sky hours a year | Score | When to go: best ten-day bins | Time of day | Known or little known |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 68.95, 54.45 | Kola and north-west Russia | 1.00 | 36 (36) | 9 | 0.421 | 10 Jul-19 Jul (26 h), 20 Jul-29 Jul (5 h), 21 May-30 May (2 h) | 56% of the hours with the Sun in the north (around midnight) | little known |
| 2 | 68.25, -96.15 | Arctic Canada | 0.96 | 36 (37) | 11 | 0.412 | 10 Jul-19 Jul (22 h), 30 Jun-9 Jul (13 h) | 59% of the hours with the Sun in the north (around midnight) | little known |
| 3 | 67.65, -76.65 | Arctic Canada | 0.88 | 37 (42) | 11 | 0.402 | 30 Jun-9 Jul (22 h), 10 Jul-19 Jul (9 h), 20 Jun-29 Jun (3 h) | 67% of the hours with the Sun in the north (around midnight) | little known |
| 4 | 67.05, -158.85 | Alaska | 0.36 | 76 (105) | 25 | 0.372 | 10 Jun-19 Jun (23 h), 20 Jun-29 Jun (22 h), 30 Jun-9 Jul (20 h) | 62% of the hours with the Sun in the north (around midnight) | little known |
| 5 | 80.35, 18.30 | Svalbard | 0.93 | 29 (31) | 4 | 0.368 | 19 Aug-28 Aug (17 h), 29 Aug-7 Sep (7 h), 8 Oct-17 Oct (5 h) | 51% of the hours with the Sun in the north (around midnight) | known: Svalbard |

1 ranked cell(s) hold the top score 0.421; 0 of the 10,837 ranked cells have full light marks (≥ 200 open hours).

**Full match (light, terrain, rock, bare), north: 2 ranked cell(s) score above zero, 1 site(s):**

| # | Cell centre (lat, lon) | Region | Bare | Long-window hours a year: open (snow-free over a flat horizon) | Typical clear-sky hours a year | Score | When to go: best ten-day bins | Time of day | Known or little known |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 70.15, -51.15 | Greenland | 0.38 | 1 (16) | 0 | 0.153 (light 0.00, terrain 0.86, rock 0.42: Tunulik anorthosite (with Boye So)) | 20 Jul-29 Jul (0.7 h), 10 Jul-19 Jul (0.1 h) | 55% of the hours with the Sun in the north (around midnight) | little known |

### Connecting Ridge Extension (Sun at or below 2.51°)

**Lighting goal (low Sun on bare ground), top 5 of the north:**

| # | Cell centre (lat, lon) | Region | Bare | Long-window hours a year: open (snow-free over a flat horizon) | Typical clear-sky hours a year | Score | When to go: best ten-day bins | Time of day | Known or little known |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 68.25, -96.15 | Arctic Canada | 0.96 | 59 (61) | 17 | 0.533 | 30 Jun-9 Jul (26 h), 10 Jul-19 Jul (26 h), 20 Jun-29 Jun (4 h) | 64% of the hours with the Sun in the north (around midnight) | little known |
| 2 | 68.95, 54.45 | Kola and north-west Russia | 1.00 | 54 (54) | 14 | 0.521 | 10 Jul-19 Jul (33 h), 30 Jun-9 Jul (7 h), 31 May-9 Jun (6 h) | 59% of the hours with the Sun in the north (around midnight) | little known |
| 3 | 68.35, -88.05 | Arctic Canada | 0.81 | 51 (55) | 14 | 0.455 | 10 Jul-19 Jul (26 h), 30 Jun-9 Jul (24 h), 10 Jun-19 Jun (0.8 h) | 63% of the hours with the Sun in the north (around midnight) | little known |
| 4 | 68.35, -98.55 | Arctic Canada | 0.75 | 53 (58) | 15 | 0.447 | 30 Jun-9 Jul (25 h), 10 Jul-19 Jul (25 h), 10 Jun-19 Jun (2 h) | 63% of the hours with the Sun in the north (around midnight) | little known |
| 5 | 80.35, 18.30 | Svalbard | 0.93 | 42 (45) | 6 | 0.443 | 19 Aug-28 Aug (24 h), 29 Aug-7 Sep (11 h), 8 Oct-17 Oct (7 h) | 52% of the hours with the Sun in the north (around midnight) | known: Svalbard |

1 ranked cell(s) hold the top score 0.533; 0 of the 10,837 ranked cells have full light marks (≥ 200 open hours).

**Full match (light, terrain, rock, bare), north: 3 ranked cell(s) score above zero, 2 site(s):**

| # | Cell centre (lat, lon) | Region | Bare | Long-window hours a year: open (snow-free over a flat horizon) | Typical clear-sky hours a year | Score | When to go: best ten-day bins | Time of day | Known or little known |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 70.15, -51.15 | Greenland | 0.38 | 2 (21) | 1 | 0.172 (light 0.01, terrain 0.72, rock 0.42: Tunulik anorthosite (with Boye So)) | 20 Jul-29 Jul (1 h), 10 Jul-19 Jul (0.5 h) | 56% of the hours with the Sun in the north (around midnight) | little known |
| 2 | 64.45, -52.10 | Greenland | 0.26 | 2 (3) | 0 | 0.122 (light 0.01, terrain 0.12, rock 0.67: Akia anorthosite (Godthabsfjord)) | 17 Dec-31 Dec (2 h), 7 Dec-16 Dec (0.2 h) | 100% of the hours with the Sun in the south (dawn, dusk, low noon) | little known |

### Peak Near Shackleton (Sun at or below 2.73°)

**Lighting goal (low Sun on bare ground), top 5 of the north:**

| # | Cell centre (lat, lon) | Region | Bare | Long-window hours a year: open (snow-free over a flat horizon) | Typical clear-sky hours a year | Score | When to go: best ten-day bins | Time of day | Known or little known |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 68.25, -96.15 | Arctic Canada | 0.96 | 76 (78) | 21 | 0.604 | 30 Jun-9 Jul (29 h), 10 Jul-19 Jul (28 h), 20 Jun-29 Jun (14 h) | 67% of the hours with the Sun in the north (around midnight) | little known |
| 2 | 68.95, 54.45 | Kola and north-west Russia | 1.00 | 66 (67) | 17 | 0.577 | 10 Jul-19 Jul (35 h), 30 Jun-9 Jul (14 h), 31 May-9 Jun (9 h) | 60% of the hours with the Sun in the north (around midnight) | little known |
| 3 | 68.35, -98.55 | Arctic Canada | 0.75 | 76 (80) | 20 | 0.532 | 30 Jun-9 Jul (28 h), 10 Jul-19 Jul (27 h), 20 Jun-29 Jun (14 h) | 67% of the hours with the Sun in the north (around midnight) | little known |
| 4 | 68.35, -88.05 | Arctic Canada | 0.81 | 66 (70) | 18 | 0.515 | 10 Jul-19 Jul (28 h), 30 Jun-9 Jul (27 h), 20 Jun-29 Jun (9 h) | 67% of the hours with the Sun in the north (around midnight) | little known |
| 5 | 68.95, -115.35 | Arctic Canada | 0.83 | 57 (57) | 18 | 0.486 | 10 Jul-19 Jul (35 h), 30 Jun-9 Jul (14 h), 20 Jul-29 Jul (6 h) | 60% of the hours with the Sun in the north (around midnight) | little known |

1 ranked cell(s) hold the top score 0.604; 0 of the 10,837 ranked cells have full light marks (≥ 200 open hours).

**Full match (light, terrain, rock, bare), north: 3 ranked cell(s) score above zero, 2 site(s):**

| # | Cell centre (lat, lon) | Region | Bare | Long-window hours a year: open (snow-free over a flat horizon) | Typical clear-sky hours a year | Score | When to go: best ten-day bins | Time of day | Known or little known |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 70.15, -51.15 | Greenland | 0.38 | 2 (25) | 1 | 0.184 (light 0.01, terrain 0.76, rock 0.42: Tunulik anorthosite (with Boye So)) | 20 Jul-29 Jul (1 h), 10 Jul-19 Jul (0.8 h) | 57% of the hours with the Sun in the north (around midnight) | little known |
| 2 | 64.45, -52.10 | Greenland | 0.26 | 4 (6) | 1 | 0.163 (light 0.02, terrain 0.21, rock 0.67: Akia anorthosite (Godthabsfjord)) | 17 Dec-31 Dec (3 h), 7 Dec-16 Dec (1 h) | 100% of the hours with the Sun in the south (dawn, dusk, low noon) | little known |

### de Gerlache Rim 1 (Sun at or below 2.86°)

**Lighting goal (low Sun on bare ground), top 5 of the north:**

| # | Cell centre (lat, lon) | Region | Bare | Long-window hours a year: open (snow-free over a flat horizon) | Typical clear-sky hours a year | Score | When to go: best ten-day bins | Time of day | Known or little known |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 68.25, -96.15 | Arctic Canada | 0.96 | 80 (82) | 22 | 0.621 | 30 Jun-9 Jul (30 h), 10 Jul-19 Jul (29 h), 20 Jun-29 Jun (15 h) | 67% of the hours with the Sun in the north (around midnight) | little known |
| 2 | 68.95, 54.45 | Kola and north-west Russia | 1.00 | 76 (76) | 19 | 0.614 | 10 Jul-19 Jul (36 h), 30 Jun-9 Jul (18 h), 31 May-9 Jun (11 h) | 62% of the hours with the Sun in the north (around midnight) | little known |
| 3 | 68.35, -98.55 | Arctic Canada | 0.75 | 80 (84) | 22 | 0.546 | 30 Jun-9 Jul (29 h), 10 Jul-19 Jul (28 h), 20 Jun-29 Jun (16 h) | 67% of the hours with the Sun in the north (around midnight) | little known |
| 4 | 68.35, -88.05 | Arctic Canada | 0.81 | 69 (73) | 19 | 0.528 | 10 Jul-19 Jul (28 h), 30 Jun-9 Jul (28 h), 20 Jun-29 Jun (10 h) | 67% of the hours with the Sun in the north (around midnight) | little known |
| 5 | 68.45, -114.75 | Arctic Canada | 0.62 | 87 (98) | 28 | 0.519 | 30 Jun-9 Jul (27 h), 10 Jul-19 Jul (26 h), 20 Jun-29 Jun (19 h) | 67% of the hours with the Sun in the north (around midnight) | little known |

1 ranked cell(s) hold the top score 0.621; 0 of the 10,837 ranked cells have full light marks (≥ 200 open hours).

**Full match (light, terrain, rock, bare), north: 3 ranked cell(s) score above zero, 2 site(s):**

| # | Cell centre (lat, lon) | Region | Bare | Long-window hours a year: open (snow-free over a flat horizon) | Typical clear-sky hours a year | Score | When to go: best ten-day bins | Time of day | Known or little known |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 70.15, -51.15 | Greenland | 0.38 | 2 (26) | 1 | 0.188 (light 0.01, terrain 0.72, rock 0.42: Tunulik anorthosite (with Boye So)) | 20 Jul-29 Jul (1 h), 10 Jul-19 Jul (1 h) | 57% of the hours with the Sun in the north (around midnight) | little known |
| 2 | 64.45, -52.10 | Greenland | 0.26 | 4 (6) | 1 | 0.147 (light 0.02, terrain 0.12, rock 0.67: Akia anorthosite (Godthabsfjord)) | 17 Dec-31 Dec (3 h), 7 Dec-16 Dec (2 h) | 100% of the hours with the Sun in the south (dawn, dusk, low noon) | little known |

### de Gerlache Rim 2 (Sun at or below 3.31°)

**Lighting goal (low Sun on bare ground), top 5 of the north:**

| # | Cell centre (lat, lon) | Region | Bare | Long-window hours a year: open (snow-free over a flat horizon) | Typical clear-sky hours a year | Score | When to go: best ten-day bins | Time of day | Known or little known |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 68.95, 54.45 | Kola and north-west Russia | 1.00 | 128 (128) | 30 | 0.799 | 10 Jul-19 Jul (40 h), 30 Jun-9 Jul (29 h), 20 Jun-29 Jun (19 h) | 67% of the hours with the Sun in the north (around midnight) | little known |
| 2 | 68.95, -115.65 | Arctic Canada | 0.87 | 109 (112) | 35 | 0.686 | 10 Jul-19 Jul (39 h), 30 Jun-9 Jul (29 h), 20 Jun-29 Jun (20 h) | 67% of the hours with the Sun in the north (around midnight) | little known |
| 3 | 68.25, -96.15 | Arctic Canada | 0.96 | 94 (95) | 25 | 0.669 | 30 Jun-9 Jul (34 h), 10 Jul-19 Jul (33 h), 20 Jun-29 Jun (19 h) | 65% of the hours with the Sun in the north (around midnight) | little known |
| 4 | 68.95, -100.65 | Arctic Canada | 0.93 | 85 (89) | 26 | 0.627 | 10 Jul-19 Jul (38 h), 30 Jun-9 Jul (28 h), 20 Jun-29 Jun (11 h) | 67% of the hours with the Sun in the north (around midnight) | little known |
| 5 | 68.35, -98.55 | Arctic Canada | 0.75 | 94 (99) | 25 | 0.593 | 30 Jun-9 Jul (34 h), 10 Jul-19 Jul (32 h), 20 Jun-29 Jun (19 h) | 66% of the hours with the Sun in the north (around midnight) | little known |

1 ranked cell(s) hold the top score 0.799; 0 of the 10,837 ranked cells have full light marks (≥ 200 open hours).

**Full match (light, terrain, rock, bare), north: 3 ranked cell(s) score above zero, 2 site(s):**

| # | Cell centre (lat, lon) | Region | Bare | Long-window hours a year: open (snow-free over a flat horizon) | Typical clear-sky hours a year | Score | When to go: best ten-day bins | Time of day | Known or little known |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 70.15, -51.15 | Greenland | 0.38 | 4 (35) | 2 | 0.223 (light 0.02, terrain 0.88, rock 0.42: Tunulik anorthosite (with Boye So)) | 10 Jul-19 Jul (2 h), 20 Jul-29 Jul (2 h) | 59% of the hours with the Sun in the north (around midnight) | little known |
| 2 | 64.45, -52.10 | Greenland | 0.26 | 6 (8) | 1 | 0.182 (light 0.03, terrain 0.21, rock 0.67: Akia anorthosite (Godthabsfjord)) | 7 Dec-16 Dec (3 h), 17 Dec-31 Dec (3 h), 27 Nov-6 Dec (0.4 h) | 100% of the hours with the Sun in the south (dawn, dusk, low noon) | little known |

### Faustini Rim A (Sun at or below 3.65°)

**Lighting goal (low Sun on bare ground), top 5 of the north:**

| # | Cell centre (lat, lon) | Region | Bare | Long-window hours a year: open (snow-free over a flat horizon) | Typical clear-sky hours a year | Score | When to go: best ten-day bins | Time of day | Known or little known |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 68.95, 54.45 | Kola and north-west Russia | 1.00 | 145 (145) | 34 | 0.851 | 10 Jul-19 Jul (43 h), 30 Jun-9 Jul (32 h), 20 Jun-29 Jun (22 h) | 66% of the hours with the Sun in the north (around midnight) | little known |
| 2 | 68.95, -115.65 | Arctic Canada | 0.87 | 124 (127) | 40 | 0.733 | 10 Jul-19 Jul (41 h), 30 Jun-9 Jul (32 h), 20 Jun-29 Jun (25 h) | 66% of the hours with the Sun in the north (around midnight) | little known |
| 3 | 68.25, -96.15 | Arctic Canada | 0.96 | 103 (105) | 28 | 0.704 | 30 Jun-9 Jul (37 h), 10 Jul-19 Jul (37 h), 20 Jun-29 Jun (21 h) | 64% of the hours with the Sun in the north (around midnight) | little known |
| 4 | 68.95, -100.65 | Arctic Canada | 0.93 | 96 (100) | 29 | 0.666 | 10 Jul-19 Jul (41 h), 30 Jun-9 Jul (32 h), 20 Jun-29 Jun (13 h) | 66% of the hours with the Sun in the north (around midnight) | little known |
| 5 | 80.35, 18.30 | Svalbard | 0.93 | 93 (98) | 12 | 0.660 | 19 Aug-28 Aug (46 h), 29 Aug-7 Sep (29 h), 8 Oct-17 Oct (12 h) | 52% of the hours with the Sun in the north (around midnight) | known: Svalbard |

1 ranked cell(s) hold the top score 0.851; 0 of the 10,837 ranked cells have full light marks (≥ 200 open hours).

**Full match (light, terrain, rock, bare), north: 4 ranked cell(s) score above zero, 3 site(s):**

| # | Cell centre (lat, lon) | Region | Bare | Long-window hours a year: open (snow-free over a flat horizon) | Typical clear-sky hours a year | Score | When to go: best ten-day bins | Time of day | Known or little known |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 70.15, -51.15 | Greenland | 0.38 | 5 (41) | 2 | 0.247 (light 0.02, terrain 0.99, rock 0.42: Tunulik anorthosite (with Boye So)) | 10 Jul-19 Jul (2 h), 20 Jul-29 Jul (2 h), 30 Jun-9 Jul (0.5 h) | 60% of the hours with the Sun in the north (around midnight) | little known |
| 2 | 64.45, -52.10 | Greenland | 0.26 | 7 (10) | 1 | 0.210 (light 0.04, terrain 0.31, rock 0.67: Akia anorthosite (Godthabsfjord)) | 7 Dec-16 Dec (3 h), 17 Dec-31 Dec (3 h), 27 Nov-6 Dec (1 h) | 100% of the hours with the Sun in the south (dawn, dusk, low noon) | little known |
| 3 | 63.35, -50.30 | Greenland | 0.36 | 0 (1) | 0 | 0.160 (light 0.00, terrain 0.88, rock 0.82: Fiskenaesset anorthosite complex) | 17 Dec-31 Dec (0.3 h), 7 Dec-16 Dec (0.1 h) | 100% of the hours with the Sun in the south (dawn, dusk, low noon) | little known |

### Slater Plain (Sun at or below 4.38°)

**Lighting goal (low Sun on bare ground), top 5 of the north:**

| # | Cell centre (lat, lon) | Region | Bare | Long-window hours a year: open (snow-free over a flat horizon) | Typical clear-sky hours a year | Score | When to go: best ten-day bins | Time of day | Known or little known |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 68.95, 54.45 | Kola and north-west Russia | 1.00 | 180 (180) | 42 | 0.947 | 10 Jul-19 Jul (48 h), 30 Jun-9 Jul (39 h), 20 Jun-29 Jun (29 h) | 65% of the hours with the Sun in the north (around midnight) | little known |
| 2 | 80.35, 18.30 | Svalbard | 0.93 | 150 (159) | 19 | 0.837 | 19 Aug-28 Aug (57 h), 29 Aug-7 Sep (44 h), 28 Sep-7 Oct (16 h) | 52% of the hours with the Sun in the north (around midnight) | known: Svalbard |
| 3 | 70.15, -116.85 | Arctic Canada | 0.98 | 137 (153) | 46 | 0.820 | 20 Jul-29 Jul (43 h), 10 Jul-19 Jul (38 h), 30 Jun-9 Jul (27 h) | 66% of the hours with the Sun in the north (around midnight) | little known |
| 4 | 68.95, -115.65 | Arctic Canada | 0.87 | 155 (158) | 49 | 0.818 | 10 Jul-19 Jul (47 h), 30 Jun-9 Jul (39 h), 20 Jun-29 Jun (32 h) | 65% of the hours with the Sun in the north (around midnight) | little known |
| 5 | 70.05, -124.35 | Arctic Canada | 0.99 | 124 (152) | 41 | 0.785 | 10 Jul-19 Jul (35 h), 20 Jul-29 Jul (30 h), 30 Jun-9 Jul (27 h) | 66% of the hours with the Sun in the north (around midnight) | little known |

1 ranked cell(s) hold the top score 0.947; 0 of the 10,837 ranked cells have full light marks (≥ 200 open hours).

**Full match (light, terrain, rock, bare), north: 0 ranked cell(s) score above zero, 0 site(s):**

No ranked cell scores above zero.

### Haworth (Sun at or below 4.78°)

**Lighting goal (low Sun on bare ground), top 5 of the north:**

| # | Cell centre (lat, lon) | Region | Bare | Long-window hours a year: open (snow-free over a flat horizon) | Typical clear-sky hours a year | Score | When to go: best ten-day bins | Time of day | Known or little known |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 68.95, 54.45 | Kola and north-west Russia | 1.00 | 198 (198) | 46 | 0.995 | 10 Jul-19 Jul (51 h), 30 Jun-9 Jul (42 h), 20 Jun-29 Jun (32 h) | 64% of the hours with the Sun in the north (around midnight) | little known |
| 2 | 80.25, 18.30 | Svalbard | 0.97 | 194 (213) | 25 | 0.970 | 19 Aug-28 Aug (61 h), 29 Aug-7 Sep (43 h), 8 Sep-17 Sep (26 h) | 52% of the hours with the Sun in the north (around midnight) | known: Svalbard |
| 3 | 70.25, -115.35 | Arctic Canada | 0.98 | 158 (166) | 42 | 0.882 | 20 Jul-29 Jul (48 h), 10 Jul-19 Jul (42 h), 30 Jun-9 Jul (32 h) | 66% of the hours with the Sun in the north (around midnight) | little known |
| 4 | 70.15, -116.85 | Arctic Canada | 0.98 | 158 (176) | 53 | 0.880 | 20 Jul-29 Jul (47 h), 10 Jul-19 Jul (41 h), 30 Jun-9 Jul (32 h) | 66% of the hours with the Sun in the north (around midnight) | little known |
| 5 | 68.95, -115.65 | Arctic Canada | 0.87 | 171 (175) | 54 | 0.861 | 10 Jul-19 Jul (50 h), 30 Jun-9 Jul (42 h), 20 Jun-29 Jun (36 h) | 64% of the hours with the Sun in the north (around midnight) | little known |

1 ranked cell(s) hold the top score 0.995; 0 of the 10,837 ranked cells have full light marks (≥ 200 open hours).

**Full match (light, terrain, rock, bare), north: 4 ranked cell(s) score above zero, 3 site(s):**

| # | Cell centre (lat, lon) | Region | Bare | Long-window hours a year: open (snow-free over a flat horizon) | Typical clear-sky hours a year | Score | When to go: best ten-day bins | Time of day | Known or little known |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 70.15, -51.15 | Greenland | 0.38 | 12 (73) | 5 | 0.308 (light 0.06, terrain 0.96, rock 0.42: Tunulik anorthosite (with Boye So)) | 20 Jul-29 Jul (4 h), 10 Jul-19 Jul (3 h), 30 Jun-9 Jul (2 h) | 66% of the hours with the Sun in the north (around midnight) | little known |
| 2 | 64.45, -52.10 | Greenland | 0.26 | 11 (15) | 2 | 0.229 (light 0.06, terrain 0.28, rock 0.67: Akia anorthosite (Godthabsfjord)) | 27 Nov-6 Dec (4 h), 7 Dec-16 Dec (3 h), 17 Dec-31 Dec (3 h) | 100% of the hours with the Sun in the south (dawn, dusk, low noon) | little known |
| 3 | 63.35, -50.30 | Greenland | 0.36 | 1 (3) | 0 | 0.189 (light 0.01, terrain 0.85, rock 0.82: Fiskenaesset anorthosite complex) | 7 Dec-16 Dec (0.4 h), 17 Dec-31 Dec (0.4 h), 27 Nov-6 Dec (0.3 h) | 100% of the hours with the Sun in the south (dawn, dusk, low noon) | little known |

### Malapert Massif (Sun at or below 5.55°)

**Lighting goal (low Sun on bare ground), top 5 of the north:**

| # | Cell centre (lat, lon) | Region | Bare | Long-window hours a year: open (snow-free over a flat horizon) | Typical clear-sky hours a year | Score | When to go: best ten-day bins | Time of day | Known or little known |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 68.95, 54.45 | Kola and north-west Russia | 1.00 | 234 (234) | 55 | 1.000 | 10 Jul-19 Jul (56 h), 30 Jun-9 Jul (48 h), 20 Jun-29 Jun (38 h) | 62% of the hours with the Sun in the north (around midnight) | little known |
| 2 | 80.15, 18.30 | Svalbard | 0.99 | 202 (238) | 26 | 0.995 | 19 Aug-28 Aug (66 h), 29 Aug-7 Sep (43 h), 9 Aug-18 Aug (25 h) | 52% of the hours with the Sun in the north (around midnight) | known: Svalbard |
| 3 | 70.25, -115.35 | Arctic Canada | 0.98 | 198 (207) | 52 | 0.985 | 20 Jul-29 Jul (53 h), 10 Jul-19 Jul (47 h), 30 Jun-9 Jul (39 h) | 65% of the hours with the Sun in the north (around midnight) | little known |
| 4 | 70.15, -116.85 | Arctic Canada | 0.98 | 197 (218) | 65 | 0.982 | 20 Jul-29 Jul (52 h), 10 Jul-19 Jul (47 h), 30 Jun-9 Jul (38 h) | 65% of the hours with the Sun in the north (around midnight) | little known |
| 5 | 70.05, -124.35 | Arctic Canada | 0.99 | 179 (212) | 58 | 0.941 | 10 Jul-19 Jul (44 h), 20 Jul-29 Jul (39 h), 30 Jun-9 Jul (38 h) | 64% of the hours with the Sun in the north (around midnight) | little known |

1 ranked cell(s) hold the top score 1.000; 38 of the 10,837 ranked cells have full light marks (≥ 200 open hours).

**Full match (light, terrain, rock, bare), north: 4 ranked cell(s) score above zero, 3 site(s):**

| # | Cell centre (lat, lon) | Region | Bare | Long-window hours a year: open (snow-free over a flat horizon) | Typical clear-sky hours a year | Score | When to go: best ten-day bins | Time of day | Known or little known |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 70.15, -51.15 | Greenland | 0.38 | 16 (91) | 7 | 0.315 (light 0.08, terrain 0.77, rock 0.42: Tunulik anorthosite (with Boye So)) | 20 Jul-29 Jul (5 h), 10 Jul-19 Jul (4 h), 30 Jun-9 Jul (3 h) | 65% of the hours with the Sun in the north (around midnight) | little known |
| 2 | 64.45, -52.10 | Greenland | 0.26 | 16 (20) | 3 | 0.205 (light 0.08, terrain 0.12, rock 0.67: Akia anorthosite (Godthabsfjord)) | 17 Nov-26 Nov (7 h), 27 Nov-6 Dec (4 h), 7 Dec-16 Dec (3 h) | 100% of the hours with the Sun in the south (dawn, dusk, low noon) | little known |
| 3 | 63.35, -50.30 | Greenland | 0.36 | 1 (4) | 0 | 0.196 (light 0.01, terrain 0.71, rock 0.82: Fiskenaesset anorthosite complex) | 27 Nov-6 Dec (0.5 h), 7 Dec-16 Dec (0.4 h), 17 Dec-31 Dec (0.4 h) | 100% of the hours with the Sun in the south (dawn, dusk, low noon) | little known |

### de Gerlache-Kocher Massif (Sun at or below 5.71°)

**Lighting goal (low Sun on bare ground), top 5 of the north:**

| # | Cell centre (lat, lon) | Region | Bare | Long-window hours a year: open (snow-free over a flat horizon) | Typical clear-sky hours a year | Score | When to go: best ten-day bins | Time of day | Known or little known |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 68.95, 54.45 | Kola and north-west Russia | 1.00 | 241 (241) | 57 | 1.000 | 10 Jul-19 Jul (57 h), 30 Jun-9 Jul (49 h), 20 Jul-29 Jul (40 h) | 62% of the hours with the Sun in the north (around midnight) | little known |
| 2 | 80.15, 18.30 | Svalbard | 0.99 | 210 (246) | 28 | 0.995 | 19 Aug-28 Aug (68 h), 29 Aug-7 Sep (44 h), 9 Aug-18 Aug (28 h) | 52% of the hours with the Sun in the north (around midnight) | known: Svalbard |
| 3 | 70.25, -115.35 | Arctic Canada | 0.98 | 206 (216) | 55 | 0.991 | 20 Jul-29 Jul (54 h), 10 Jul-19 Jul (48 h), 30 Jun-9 Jul (40 h) | 64% of the hours with the Sun in the north (around midnight) | little known |
| 4 | 70.15, -116.85 | Arctic Canada | 0.98 | 205 (228) | 67 | 0.990 | 20 Jul-29 Jul (53 h), 10 Jul-19 Jul (48 h), 30 Jun-9 Jul (40 h) | 64% of the hours with the Sun in the north (around midnight) | little known |
| 5 | 70.05, -124.35 | Arctic Canada | 0.99 | 186 (221) | 60 | 0.961 | 10 Jul-19 Jul (45 h), 20 Jul-29 Jul (40 h), 30 Jun-9 Jul (39 h) | 64% of the hours with the Sun in the north (around midnight) | little known |

1 ranked cell(s) hold the top score 1.000; 59 of the 10,837 ranked cells have full light marks (≥ 200 open hours).

**Full match (light, terrain, rock, bare), north: 4 ranked cell(s) score above zero, 3 site(s):**

| # | Cell centre (lat, lon) | Region | Bare | Long-window hours a year: open (snow-free over a flat horizon) | Typical clear-sky hours a year | Score | When to go: best ten-day bins | Time of day | Known or little known |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 70.15, -51.15 | Greenland | 0.38 | 17 (95) | 7 | 0.317 (light 0.09, terrain 0.73, rock 0.42: Tunulik anorthosite (with Boye So)) | 20 Jul-29 Jul (5 h), 10 Jul-19 Jul (4 h), 30 Jun-9 Jul (3 h) | 64% of the hours with the Sun in the north (around midnight) | little known |
| 2 | 64.45, -52.10 | Greenland | 0.26 | 17 (22) | 3 | 0.214 (light 0.09, terrain 0.14, rock 0.67: Akia anorthosite (Godthabsfjord)) | 17 Nov-26 Nov (8 h), 27 Nov-6 Dec (4 h), 7 Dec-16 Dec (3 h) | 100% of the hours with the Sun in the south (dawn, dusk, low noon) | little known |
| 3 | 63.35, -50.30 | Greenland | 0.36 | 2 (4) | 0 | 0.196 (light 0.01, terrain 0.66, rock 0.82: Fiskenaesset anorthosite complex) | 27 Nov-6 Dec (0.5 h), 7 Dec-16 Dec (0.4 h), 17 Dec-31 Dec (0.4 h) | 100% of the hours with the Sun in the south (dawn, dusk, low noon) | little known |

### Nobile Rim 1 (Sun at or below 6.10°)

**Lighting goal (low Sun on bare ground), top 5 of the north:**

| # | Cell centre (lat, lon) | Region | Bare | Long-window hours a year: open (snow-free over a flat horizon) | Typical clear-sky hours a year | Score | When to go: best ten-day bins | Time of day | Known or little known |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 68.95, 54.45 | Kola and north-west Russia | 1.00 | 260 (260) | 61 | 1.000 | 10 Jul-19 Jul (59 h), 30 Jun-9 Jul (52 h), 20 Jul-29 Jul (48 h) | 61% of the hours with the Sun in the north (around midnight) | little known |
| 2 | 77.55, 22.75 | Svalbard | 1.00 | 228 (320) | 37 | 1.000 | 9 Aug-18 Aug (54 h), 19 Aug-28 Aug (36 h), 30 Jul-8 Aug (26 h) | 53% of the hours with the Sun in the north (around midnight) | known: Svalbard |
| 3 | 75.95, 141.25 | Siberia and the Russian Far East | 1.00 | 202 (203) | 27 | 0.998 | 9 Aug-18 Aug (69 h), 30 Jul-8 Aug (49 h), 19 Aug-28 Aug (48 h) | 55% of the hours with the Sun in the north (around midnight) | little known |
| 4 | 70.05, -124.35 | Arctic Canada | 0.99 | 205 (241) | 65 | 0.996 | 10 Jul-19 Jul (48 h), 30 Jun-9 Jul (42 h), 20 Jul-29 Jul (42 h) | 64% of the hours with the Sun in the north (around midnight) | little known |
| 5 | 80.15, 18.30 | Svalbard | 0.99 | 229 (266) | 30 | 0.995 | 19 Aug-28 Aug (72 h), 29 Aug-7 Sep (47 h), 9 Aug-18 Aug (36 h) | 52% of the hours with the Sun in the north (around midnight) | known: Svalbard |

2 ranked cell(s) hold the top score 1.000; 185 of the 10,837 ranked cells have full light marks (≥ 200 open hours).

**Full match (light, terrain, rock, bare), north: 4 ranked cell(s) score above zero, 3 site(s):**

| # | Cell centre (lat, lon) | Region | Bare | Long-window hours a year: open (snow-free over a flat horizon) | Typical clear-sky hours a year | Score | When to go: best ten-day bins | Time of day | Known or little known |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 70.15, -51.15 | Greenland | 0.38 | 20 (105) | 8 | 0.343 (light 0.10, terrain 0.86, rock 0.42: Tunulik anorthosite (with Boye So)) | 20 Jul-29 Jul (6 h), 10 Jul-19 Jul (5 h), 30 Jun-9 Jul (3 h) | 64% of the hours with the Sun in the north (around midnight) | little known |
| 2 | 64.45, -52.10 | Greenland | 0.26 | 20 (24) | 4 | 0.237 (light 0.10, terrain 0.18, rock 0.67: Akia anorthosite (Godthabsfjord)) | 17 Nov-26 Nov (9 h), 27 Nov-6 Dec (4 h), 7 Dec-16 Dec (3 h) | 100% of the hours with the Sun in the south (dawn, dusk, low noon) | little known |
| 3 | 63.35, -50.30 | Greenland | 0.36 | 2 (5) | 0 | 0.212 (light 0.01, terrain 0.81, rock 0.82: Fiskenaesset anorthosite complex) | 27 Nov-6 Dec (0.5 h), 17 Nov-26 Nov (0.5 h), 7 Dec-16 Dec (0.4 h) | 100% of the hours with the Sun in the south (dawn, dusk, low noon) | little known |

### Mons Mouton (Sun at or below 6.11°)

**Lighting goal (low Sun on bare ground), top 5 of the north:**

| # | Cell centre (lat, lon) | Region | Bare | Long-window hours a year: open (snow-free over a flat horizon) | Typical clear-sky hours a year | Score | When to go: best ten-day bins | Time of day | Known or little known |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 68.95, 54.45 | Kola and north-west Russia | 1.00 | 260 (260) | 61 | 1.000 | 10 Jul-19 Jul (59 h), 30 Jun-9 Jul (52 h), 20 Jul-29 Jul (48 h) | 61% of the hours with the Sun in the north (around midnight) | little known |
| 2 | 77.55, 22.75 | Svalbard | 1.00 | 228 (321) | 37 | 1.000 | 9 Aug-18 Aug (54 h), 19 Aug-28 Aug (36 h), 30 Jul-8 Aug (27 h) | 53% of the hours with the Sun in the north (around midnight) | known: Svalbard |
| 3 | 75.85, 141.25 | Siberia and the Russian Far East | 1.00 | 200 (200) | 27 | 0.999 | 9 Aug-18 Aug (69 h), 30 Jul-8 Aug (48 h), 19 Aug-28 Aug (48 h) | 55% of the hours with the Sun in the north (around midnight) | little known |
| 4 | 70.05, -124.35 | Arctic Canada | 0.99 | 205 (242) | 65 | 0.996 | 10 Jul-19 Jul (48 h), 30 Jun-9 Jul (42 h), 20 Jul-29 Jul (42 h) | 64% of the hours with the Sun in the north (around midnight) | little known |
| 5 | 80.15, 18.30 | Svalbard | 0.99 | 230 (267) | 30 | 0.995 | 19 Aug-28 Aug (72 h), 29 Aug-7 Sep (47 h), 9 Aug-18 Aug (36 h) | 52% of the hours with the Sun in the north (around midnight) | known: Svalbard |

2 ranked cell(s) hold the top score 1.000; 188 of the 10,837 ranked cells have full light marks (≥ 200 open hours).

**Full match (light, terrain, rock, bare), north: 4 ranked cell(s) score above zero, 3 site(s):**

| # | Cell centre (lat, lon) | Region | Bare | Long-window hours a year: open (snow-free over a flat horizon) | Typical clear-sky hours a year | Score | When to go: best ten-day bins | Time of day | Known or little known |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 70.15, -51.15 | Greenland | 0.38 | 20 (105) | 8 | 0.356 (light 0.10, terrain 1.00, rock 0.42: Tunulik anorthosite (with Boye So)) | 20 Jul-29 Jul (6 h), 10 Jul-19 Jul (5 h), 30 Jun-9 Jul (3 h) | 64% of the hours with the Sun in the north (around midnight) | little known |
| 2 | 64.45, -52.10 | Greenland | 0.26 | 20 (24) | 4 | 0.245 (light 0.10, terrain 0.21, rock 0.67: Akia anorthosite (Godthabsfjord)) | 17 Nov-26 Nov (9 h), 27 Nov-6 Dec (4 h), 7 Dec-16 Dec (3 h) | 100% of the hours with the Sun in the south (dawn, dusk, low noon) | little known |
| 3 | 63.35, -50.30 | Greenland | 0.36 | 2 (5) | 0 | 0.218 (light 0.01, terrain 0.90, rock 0.82: Fiskenaesset anorthosite complex) | 27 Nov-6 Dec (0.5 h), 17 Nov-26 Nov (0.5 h), 7 Dec-16 Dec (0.4 h) | 100% of the hours with the Sun in the south (dawn, dusk, low noon) | little known |

### Mons Mouton Plateau (Sun at or below 7.21°)

**Lighting goal (low Sun on bare ground), top 5 of the north:**

| # | Cell centre (lat, lon) | Region | Bare | Long-window hours a year: open (snow-free over a flat horizon) | Typical clear-sky hours a year | Score | When to go: best ten-day bins | Time of day | Known or little known |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 75.15, 141.75 | Siberia and the Russian Far East | 1.00 | 365 (365) | 47 | 1.000 | 9 Aug-18 Aug (72 h), 30 Jul-8 Aug (64 h), 19 Aug-28 Aug (50 h) | 56% of the hours with the Sun in the north (around midnight) | little known |
| 2 | 75.75, 141.75 | Siberia and the Russian Far East | 1.00 | 354 (358) | 46 | 1.000 | 9 Aug-18 Aug (75 h), 30 Jul-8 Aug (57 h), 19 Aug-28 Aug (52 h) | 55% of the hours with the Sun in the north (around midnight) | little known |
| 3 | 74.95, 143.75 | Siberia and the Russian Far East | 1.00 | 343 (349) | 55 | 1.000 | 9 Aug-18 Aug (66 h), 30 Jul-8 Aug (65 h), 19 Aug-28 Aug (48 h) | 56% of the hours with the Sun in the north (around midnight) | little known |
| 4 | 68.95, 54.45 | Kola and north-west Russia | 1.00 | 326 (326) | 74 | 1.000 | 10 Jul-19 Jul (65 h), 30 Jun-9 Jul (59 h), 20 Jul-29 Jul (54 h) | 60% of the hours with the Sun in the north (around midnight) | little known |
| 5 | 77.55, 22.75 | Svalbard | 1.00 | 296 (390) | 48 | 1.000 | 9 Aug-18 Aug (63 h), 30 Jul-8 Aug (45 h), 19 Aug-28 Aug (44 h) | 54% of the hours with the Sun in the north (around midnight) | known: Svalbard |

37 ranked cell(s) hold the top score 1.000; 1,952 of the 10,837 ranked cells have full light marks (≥ 200 open hours).

**Full match (light, terrain, rock, bare), north: 0 ranked cell(s) score above zero, 0 site(s):**

No ranked cell scores above zero.

### Amundsen Rim (Sun at or below 7.31°)

**Lighting goal (low Sun on bare ground), top 5 of the north:**

| # | Cell centre (lat, lon) | Region | Bare | Long-window hours a year: open (snow-free over a flat horizon) | Typical clear-sky hours a year | Score | When to go: best ten-day bins | Time of day | Known or little known |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 74.95, 143.25 | Siberia and the Russian Far East | 1.00 | 383 (387) | 60 | 1.000 | 9 Aug-18 Aug (69 h), 30 Jul-8 Aug (65 h), 19 Aug-28 Aug (49 h) | 56% of the hours with the Sun in the north (around midnight) | little known |
| 2 | 74.95, 141.25 | Siberia and the Russian Far East | 1.00 | 379 (381) | 60 | 1.000 | 9 Aug-18 Aug (70 h), 30 Jul-8 Aug (65 h), 19 Aug-28 Aug (49 h) | 56% of the hours with the Sun in the north (around midnight) | little known |
| 3 | 75.35, 142.25 | Siberia and the Russian Far East | 1.00 | 365 (370) | 47 | 1.000 | 9 Aug-18 Aug (74 h), 30 Jul-8 Aug (63 h), 19 Aug-28 Aug (52 h) | 56% of the hours with the Sun in the north (around midnight) | little known |
| 4 | 68.95, 54.45 | Kola and north-west Russia | 1.00 | 332 (333) | 75 | 1.000 | 10 Jul-19 Jul (66 h), 30 Jun-9 Jul (59 h), 20 Jul-29 Jul (55 h) | 60% of the hours with the Sun in the north (around midnight) | little known |
| 5 | 77.55, 22.75 | Svalbard | 1.00 | 303 (396) | 49 | 1.000 | 9 Aug-18 Aug (64 h), 30 Jul-8 Aug (46 h), 19 Aug-28 Aug (45 h) | 54% of the hours with the Sun in the north (around midnight) | known: Svalbard |

38 ranked cell(s) hold the top score 1.000; 2,094 of the 10,837 ranked cells have full light marks (≥ 200 open hours).

**Full match (light, terrain, rock, bare), north: 7 ranked cell(s) score above zero, 4 site(s):**

| # | Cell centre (lat, lon) | Region | Bare | Long-window hours a year: open (snow-free over a flat horizon) | Typical clear-sky hours a year | Score | When to go: best ten-day bins | Time of day | Known or little known |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 70.15, -51.15 | Greenland | 0.38 | 31 (139) | 13 | 0.382 (light 0.16, terrain 0.85, rock 0.42: Tunulik anorthosite (with Boye So)) | 20 Jul-29 Jul (7 h), 30 Jul-8 Aug (7 h), 10 Jul-19 Jul (6 h) | 62% of the hours with the Sun in the north (around midnight) | little known |
| 2 | 64.45, -52.10 | Greenland | 0.26 | 86 (110) | 16 | 0.355 (light 0.43, terrain 0.21, rock 0.67: Akia anorthosite (Godthabsfjord)) | 20 Jun-29 Jun (25 h), 30 Jun-9 Jul (20 h), 10 Jun-19 Jun (12 h) | 77% of the hours with the Sun in the south (dawn, dusk, low noon) | little known |
| 3 | 64.35, -50.90 | Greenland | 0.27 | 10 (45) | 3 | 0.276 (light 0.05, terrain 0.62, rock 0.71: Storo anorthosite (Godthabsfjord)) | 20 Jun-29 Jun (4 h), 10 Jun-19 Jun (3 h), 30 Jun-9 Jul (2 h) | 78% of the hours with the Sun in the south (dawn, dusk, low noon) | little known |
| 4 | 63.35, -50.30 | Greenland | 0.36 | 2 (7) | 1 | 0.232 (light 0.01, terrain 0.78, rock 0.82: Fiskenaesset anorthosite complex) | 17 Nov-26 Nov (0.9 h), 27 Nov-6 Dec (0.5 h), 7 Dec-16 Dec (0.4 h) | 100% of the hours with the Sun in the south (dawn, dusk, low noon) | little known |

### Nobile Rim 2 (Sun at or below 7.59°)

**Lighting goal (low Sun on bare ground), top 5 of the north:**

| # | Cell centre (lat, lon) | Region | Bare | Long-window hours a year: open (snow-free over a flat horizon) | Typical clear-sky hours a year | Score | When to go: best ten-day bins | Time of day | Known or little known |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 74.95, 143.25 | Siberia and the Russian Far East | 1.00 | 403 (406) | 64 | 1.000 | 9 Aug-18 Aug (71 h), 30 Jul-8 Aug (67 h), 19 Aug-28 Aug (50 h) | 56% of the hours with the Sun in the north (around midnight) | little known |
| 2 | 74.95, 141.25 | Siberia and the Russian Far East | 1.00 | 398 (400) | 63 | 1.000 | 9 Aug-18 Aug (72 h), 30 Jul-8 Aug (67 h), 19 Aug-28 Aug (50 h) | 56% of the hours with the Sun in the north (around midnight) | little known |
| 3 | 75.35, 142.25 | Siberia and the Russian Far East | 1.00 | 384 (388) | 50 | 1.000 | 9 Aug-18 Aug (76 h), 30 Jul-8 Aug (65 h), 19 Aug-28 Aug (53 h) | 56% of the hours with the Sun in the north (around midnight) | little known |
| 4 | 68.95, 54.45 | Kola and north-west Russia | 1.00 | 351 (352) | 78 | 1.000 | 10 Jul-19 Jul (67 h), 30 Jun-9 Jul (61 h), 20 Jul-29 Jul (56 h) | 59% of the hours with the Sun in the north (around midnight) | little known |
| 5 | 77.55, 22.75 | Svalbard | 1.00 | 321 (414) | 52 | 1.000 | 9 Aug-18 Aug (66 h), 30 Jul-8 Aug (49 h), 19 Aug-28 Aug (47 h) | 54% of the hours with the Sun in the north (around midnight) | known: Svalbard |

46 ranked cell(s) hold the top score 1.000; 2,400 of the 10,837 ranked cells have full light marks (≥ 200 open hours).

**Full match (light, terrain, rock, bare), north: 7 ranked cell(s) score above zero, 4 site(s):**

| # | Cell centre (lat, lon) | Region | Bare | Long-window hours a year: open (snow-free over a flat horizon) | Typical clear-sky hours a year | Score | When to go: best ten-day bins | Time of day | Known or little known |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 70.15, -51.15 | Greenland | 0.38 | 34 (147) | 14 | 0.406 (light 0.17, terrain 1.00, rock 0.42: Tunulik anorthosite (with Boye So)) | 20 Jul-29 Jul (8 h), 30 Jul-8 Aug (7 h), 10 Jul-19 Jul (7 h) | 62% of the hours with the Sun in the north (around midnight) | little known |
| 2 | 64.45, -52.10 | Greenland | 0.26 | 103 (129) | 19 | 0.394 (light 0.51, terrain 0.27, rock 0.67: Akia anorthosite (Godthabsfjord)) | 30 Jun-9 Jul (29 h), 20 Jun-29 Jun (26 h), 10 Jun-19 Jun (12 h) | 74% of the hours with the Sun in the south (dawn, dusk, low noon) | little known |
| 3 | 64.35, -50.90 | Greenland | 0.27 | 13 (57) | 4 | 0.300 (light 0.06, terrain 0.67, rock 0.71: Storo anorthosite (Godthabsfjord)) | 30 Jun-9 Jul (4 h), 20 Jun-29 Jun (4 h), 10 Jun-19 Jun (3 h) | 76% of the hours with the Sun in the south (dawn, dusk, low noon) | little known |
| 4 | 63.35, -50.30 | Greenland | 0.36 | 3 (7) | 1 | 0.246 (light 0.01, terrain 0.91, rock 0.82: Fiskenaesset anorthosite complex) | 17 Nov-26 Nov (0.9 h), 7 Nov-16 Nov (0.5 h), 27 Nov-6 Dec (0.5 h) | 100% of the hours with the Sun in the south (dawn, dusk, low noon) | little known |

### Peak near Cabeus B (Sun at or below 7.90°)

**Lighting goal (low Sun on bare ground), top 5 of the north:**

| # | Cell centre (lat, lon) | Region | Bare | Long-window hours a year: open (snow-free over a flat horizon) | Typical clear-sky hours a year | Score | When to go: best ten-day bins | Time of day | Known or little known |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 74.95, 143.25 | Siberia and the Russian Far East | 1.00 | 425 (429) | 67 | 1.000 | 9 Aug-18 Aug (72 h), 30 Jul-8 Aug (70 h), 19 Aug-28 Aug (52 h) | 57% of the hours with the Sun in the north (around midnight) | little known |
| 2 | 74.95, 141.25 | Siberia and the Russian Far East | 1.00 | 420 (422) | 67 | 1.000 | 9 Aug-18 Aug (74 h), 30 Jul-8 Aug (70 h), 19 Aug-28 Aug (52 h) | 57% of the hours with the Sun in the north (around midnight) | little known |
| 3 | 75.35, 142.25 | Siberia and the Russian Far East | 1.00 | 405 (409) | 53 | 1.000 | 9 Aug-18 Aug (78 h), 30 Jul-8 Aug (68 h), 19 Aug-28 Aug (55 h) | 56% of the hours with the Sun in the north (around midnight) | little known |
| 4 | 68.95, 54.45 | Kola and north-west Russia | 1.00 | 376 (377) | 83 | 1.000 | 10 Jul-19 Jul (69 h), 30 Jun-9 Jul (63 h), 20 Jul-29 Jul (58 h) | 59% of the hours with the Sun in the north (around midnight) | little known |
| 5 | 77.55, 22.75 | Svalbard | 1.00 | 341 (435) | 56 | 1.000 | 9 Aug-18 Aug (68 h), 30 Jul-8 Aug (52 h), 19 Aug-28 Aug (49 h) | 55% of the hours with the Sun in the north (around midnight) | known: Svalbard |

48 ranked cell(s) hold the top score 1.000; 2,672 of the 10,837 ranked cells have full light marks (≥ 200 open hours).

**Full match (light, terrain, rock, bare), north: 0 ranked cell(s) score above zero, 0 site(s):**

No ranked cell scores above zero.

Source: `cells_scored.json` → `cells[].targets.<target>.goals.lighting`, `.goals.full`, `.long_open_hours`, `.long_snow_free_hours`, `.top_bins`, `.poleward_share`, `.long_open_hours_clear`, `.light`, `.terrain`, `.rock`; `cells[].known`, `.known_region`, `.little_known`. The same tables, ten rows each, are in `ranking.txt`; all 128 north and south tables there were rebuilt here from `cells_scored.json` and 128 agree row for row.

What decides the tables, and how firm they are:

- The full-match goal needs a listed anorthosite body: 17 of the 10,837 ranked northern cells have a rock score above 0 (`cells[].rock.score`), so those tables are short. The highest full-match score is 0.41; the factor scores are in the tables.

| Target (lighting, north) | Sites in the top list | kept: full marks at 100 h | kept: full marks at 400 h | kept: stretch minimum 1 h | kept: stretch minimum 3 h | kept: snow land pixels >= 4 | kept: snow land pixels >= 7 | kept: flat horizon instead of real | kept: bare screen 0.15 | kept: bare screen 0.35 |
|---|---|---|---|---|---|---|---|---|---|---|
| Connecting ridge | 10 | 10 | 10 | 7 | 3 | 9 | 7 | 1 | 10 | 10 |
| Connecting Ridge Extension | 10 | 10 | 10 | 8 | 7 | 7 | 4 | 3 | 10 | 10 |
| Peak Near Shackleton | 10 | 10 | 10 | 7 | 8 | 8 | 5 | 4 | 10 | 10 |
| de Gerlache Rim 1 | 10 | 10 | 10 | 6 | 6 | 8 | 4 | 5 | 10 | 10 |
| de Gerlache Rim 2 | 10 | 10 | 10 | 4 | 8 | 9 | 5 | 5 | 10 | 10 |
| Faustini Rim A | 10 | 10 | 10 | 4 | 7 | 7 | 5 | 6 | 10 | 10 |
| Slater Plain | 10 | 7 | 10 | 4 | 4 | 8 | 6 | 6 | 10 | 10 |
| Haworth | 10 | 1 | 10 | 4 | 6 | 7 | 5 | 6 | 10 | 10 |
| Malapert | 10 | 1 | 10 | 1 | 7 | 8 | 2 | 7 | 10 | 10 |
| de Gerlache-Kocher Massif | 10 | 1 | 10 | 1 | 7 | 8 | 2 | 7 | 10 | 10 |
| Nobile Rim 1 | 10 | 2 | 8 | 2 | 5 | 7 | 6 | 6 | 10 | 10 |
| Mons Mouton | 10 | 4 | 8 | 3 | 5 | 7 | 6 | 6 | 10 | 10 |
| Mons Mouton Plateau | 10 | 10 | 5 | 7 | 1 | 6 | 5 | 7 | 10 | 10 |
| Amundsen Rim | 10 | 10 | 5 | 7 | 1 | 7 | 6 | 8 | 10 | 10 |
| Nobile Rim 2 | 10 | 10 | 5 | 9 | 4 | 7 | 6 | 8 | 10 | 10 |
| Peak near Cabeus B | 10 | 10 | 5 | 9 | 7 | 7 | 6 | 8 | 10 | 10 |

Source: `validation.json` → `stability.north.<target>.lighting`: how many of the top-10 sites still have a site within 50 km when one choice is changed. The check draws on every scored cell (16,184 records); the 1 h and 3 h columns are per-day spells worked out again by `grazing.long_window_hours_by_bin`.

| Target | Measured cells with bare ≥ 0.25 that already have 200 long-window snow-free hours over a flat horizon | of them with a terrain horizon |
|---|---|---|
| Connecting ridge | 0 | 0 |
| Connecting Ridge Extension | 0 | 0 |
| Peak Near Shackleton | 0 | 0 |
| de Gerlache Rim 1 | 0 | 0 |
| de Gerlache Rim 2 | 0 | 0 |
| Faustini Rim A | 0 | 0 |
| Slater Plain | 3 | 3 |
| Haworth | 24 | 24 |
| Malapert | 363 | 363 |
| de Gerlache-Kocher Massif | 473 | 473 |
| Nobile Rim 1 | 1,008 | 1,008 |
| Mons Mouton | 1,031 | 1,031 |
| Mons Mouton Plateau | 4,430 | 4,427 |
| Amundsen Rim | 4,550 | 4,547 |
| Nobile Rim 2 | 4,977 | 4,973 |
| Peak near Cabeus B | 5,391 | 5,385 |

Source: `validation.json` → `regions.<target>.measured_cells_with_full_flat_light_and_enough_bare`. The ranking can only choose among cells that have a horizon; the cells in the second column but not the third have no horizon, so some of them may be as good as the sites listed.

## (f) The named sites

Each named place is reported on the cell that holds it, whatever the screens say; the 10 cells outside the screens are in no count above. Hours are long-window hours a year: flat / snow-free / open. Horizons are for the cell's 10 km square, not the site's exact point.

| Site (north) | Cell | Bare | Snow odds | Horizon N / S | Connecting ridge | Connecting Ridge Extension | Peak Near Shackleton | de Gerlache Rim 1 | de Gerlache Rim 2 | Faustini Rim A | Slater Plain | Haworth | Malapert | de Gerlache-Kocher Massif | Nobile Rim 1 | Mons Mouton | Mons Mouton Plateau | Amundsen Rim | Nobile Rim 2 | Peak near Cabeus B | Rock match |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Qaqortorsuaq anorthosite, Greenland | 66.5_-52.2 | 0.12 | measured, outside the screen | 6.0° / 5.9° | 171 / 67 / 13 | 201 / 74 / 15 | 218 / 79 / 16 | 226 / 81 / 17 | 263 / 91 / 20 | 293 / 100 / 22 | 367 / 124 / 29 | 411 / 139 / 34 | 504 / 171 / 43 | 524 / 178 / 46 | 576 / 196 / 52 | 577 / 197 / 52 | 736 / 254 / 74 | 752 / 259 / 76 | 796 / 274 / 82 | 848 / 292 / 89 | 0.74 |
| Fiskenaesset anorthosite, Greenland | 63.2_-50.0 | 0.26 | measured | 6.0° / 6.2° | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 | 61 / 0 / 0 | 153 / 0 / 0 | 190 / 0 / 0 | 256 / 0 / 0 | 268 / 0 / 0 | 300 / 0 / 0 | 301 / 0 / 0 | 389 / 0 / 0 | 397 / 0 / 0 | 420 / 0 / 0 | 459 / 3 / 1 | 0.82 |
| Lofoten anorthosite (Nusfjord), Norway | 68.0_13.2 | 0.01 | doubtful, outside the screen | 10.1° / 5.3° | 135 / 84 / 11 | 212 / 148 / 20 | 233 / 162 / 23 | 246 / 170 / 24 | 291 / 198 / 31 | 325 / 220 / 36 | 405 / 268 / 48 | 451 / 295 / 56 | 549 / 351 / 71 | 570 / 363 / 74 | 624 / 392 / 83 | 626 / 393 / 83 | 794 / 485 / 112 | 810 / 495 / 115 | 858 / 523 / 124 | 913 / 556 / 134 | 0.12 |
| Bergen Arcs anorthosite, Norway | 60.5_5.2 | 0.00 | measured, outside the screen | 3.3° / 3.2° | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 | 48 / 28 / 12 | 124 / 72 / 32 | 126 / 73 / 33 | 274 / 163 / 80 | 285 / 170 / 84 | 314 / 189 / 94 | 345 / 210 / 105 | 0.50 |
| Bear Island, Norway | 74.4_19.0 | 0.62 | doubtful | -0.1° / 3.3° | 81 / 29 / 15 | 114 / 40 / 22 | 132 / 47 / 26 | 143 / 51 / 29 | 188 / 67 / 39 | 226 / 80 / 48 | 321 / 112 / 71 | 382 / 133 / 86 | 520 / 184 / 124 | 552 / 197 / 133 | 639 / 228 / 157 | 641 / 229 / 158 | 980 / 357 / 258 | 1,029 / 376 / 272 | 1,213 / 450 / 330 | 1,275 / 470 / 348 | 0.00 |
| Jan Mayen, Norway | 70.9_-8.7 | 0.53 | doubtful | 4.9° / -0.1° | 89 / 29 / 10 | 123 / 41 / 14 | 142 / 48 / 17 | 155 / 53 / 19 | 202 / 70 / 26 | 244 / 86 / 32 | 349 / 123 / 47 | 422 / 148 / 58 | 592 / 197 / 80 | 620 / 206 / 84 | 691 / 227 / 94 | 692 / 228 / 94 | 908 / 298 / 130 | 930 / 306 / 133 | 992 / 328 / 145 | 1,066 / 354 / 159 | 0.00 |
| Reykjanes, Iceland | 63.8_-22.6 | 0.00 | measured, outside the screen | 0.7° / -0.1° | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 | 84 / 36 / 30 | 120 / 50 / 43 | 185 / 84 / 72 | 217 / 102 / 88 | 276 / 135 / 118 | 288 / 142 / 124 | 317 / 159 / 139 | 318 / 160 / 140 | 403 / 209 / 185 | 446 / 249 / 215 | 518 / 312 / 265 | 580 / 364 / 308 | 0.00 |
| Skeidararsandur, Iceland | 63.9_-17.6 | 0.74 | measured | 3.7° / -0.2° | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 | 92 / 22 / 20 | 128 / 29 / 26 | 189 / 46 / 42 | 220 / 54 / 50 | 279 / 76 / 69 | 290 / 80 / 73 | 320 / 90 / 82 | 321 / 90 / 83 | 444 / 155 / 121 | 472 / 177 / 130 | 533 / 223 / 151 | 593 / 267 / 173 | 0.00 |
| Myrdalssandur sand plain, Iceland | 63.4_-18.6 | 0.90 | measured | 0.3° / -0.1° | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 | 88 / 28 / 28 | 165 / 54 / 53 | 200 / 68 / 68 | 263 / 98 / 98 | 276 / 105 / 104 | 306 / 121 / 120 | 307 / 121 / 120 | 394 / 166 / 165 | 402 / 170 / 169 | 424 / 182 / 181 | 519 / 264 / 255 | 0.00 |
| Haughton crater, Devon Island, Canada | 75.3_-90.0 | 0.53 | measured | 0.8° / 1.8° | 83 / 21 / 10 | 115 / 29 / 16 | 134 / 34 / 19 | 145 / 37 / 21 | 191 / 50 / 30 | 230 / 60 / 38 | 328 / 88 / 58 | 391 / 106 / 71 | 536 / 147 / 102 | 570 / 157 / 110 | 664 / 185 / 131 | 668 / 186 / 132 | 1,107 / 302 / 220 | 1,124 / 308 / 225 | 1,172 / 324 / 240 | 1,226 / 342 / 256 | 0.00 |
| Longyearbyen, Svalbard | 78.2_15.6 | 0.48 | measured | 12.9° / 7.5° | 90 / 9 / 1 | 127 / 13 / 1 | 149 / 15 / 1 | 163 / 16 / 2 | 216 / 22 / 2 | 263 / 27 / 3 | 385 / 39 / 5 | 469 / 48 / 7 | 727 / 75 / 14 | 818 / 86 / 17 | 874 / 92 / 19 | 875 / 92 / 19 | 1,036 / 112 / 27 | 1,051 / 114 / 27 | 1,092 / 118 / 29 | 1,139 / 124 / 31 | 0.00 |
| Kangerlussuaq, Greenland | 67.0_-50.7 | 0.07 | measured, outside the screen | 7.0° / 5.0° | 175 / 94 / 4 | 209 / 106 / 6 | 226 / 113 / 7 | 236 / 116 / 8 | 274 / 131 / 10 | 305 / 143 / 12 | 379 / 171 / 18 | 423 / 189 / 22 | 516 / 226 / 32 | 536 / 235 / 34 | 589 / 256 / 42 | 589 / 256 / 42 | 750 / 319 / 67 | 767 / 325 / 69 | 812 / 342 / 77 | 864 / 362 / 85 | 0.00 |

Source: `validation.json` → `named_sites.sites[]`: `.cell`, `.bare`, `.snow.status`, `.gridded`, `.horizon`, `.targets.<target>.<flat|snow_free|open>.long.year`, `.rock.score`.

- Qaqortorsuaq (the simulant mine): its cell has 76 all-day low-Sun days for Malapert but 0.0 usable days, because the snow odds are 0 on those days; its long-window snow-free hours (170.9 h) are all in the summer half (winter half 0.0 h), and the terrain leaves 43.4 h (`named_sites.sites[].targets.malapert.all_day_days`, `.usable_days`, `.snow_free.long`, `.open.long`).

### Haughton crater, Devon Island, in July

A NASA-funded rover test used the 24-hour Sun at Haughton crater in July 2001; the hours below are what this method gives for the same place and month. Cell 75.3_-90.0; horizon 0.77° north, 1.79° south; snow-free odds in the three ten-day bins 30 Jun-9 Jul, 10 Jul-19 Jul, 20 Jul-29 Jul: 0.45, 0.88, 1.00.

| Target | All hours in the band (any spell length), flat horizon, in the three bins | July, all hours: flat | snow-free | open | July, long-window hours only (spells of 2 h or more): flat / snow-free / open | Median longest daily spell in each bin, h (for information; it gates nothing now) |
|---|---|---|---|---|---|---|
| Connecting ridge | 0.0 / 0.0 / 0.0 | 0.0 | 0.0 | 0.0 | 0.0 / 0.0 / 0.0 | 0.00 / 0.00 / 0.00 |
| Connecting Ridge Extension | 0.0 / 0.0 / 0.0 | 0.0 | 0.0 | 0.0 | 0.0 / 0.0 / 0.0 | 0.00 / 0.00 / 0.00 |
| Peak Near Shackleton | 0.0 / 0.0 / 0.0 | 0.0 | 0.0 | 0.0 | 0.0 / 0.0 / 0.0 | 0.00 / 0.00 / 0.00 |
| de Gerlache Rim 1 | 0.0 / 0.0 / 0.0 | 0.0 | 0.0 | 0.0 | 0.0 / 0.0 / 0.0 | 0.00 / 0.00 / 0.00 |
| de Gerlache Rim 2 | 0.0 / 0.0 / 0.0 | 0.0 | 0.0 | 0.0 | 0.0 / 0.0 / 0.0 | 0.00 / 0.00 / 0.00 |
| Faustini Rim A | 0.0 / 0.0 / 0.0 | 0.0 | 0.0 | 0.0 | 0.0 / 0.0 / 0.0 | 0.00 / 0.00 / 0.00 |
| Slater Plain | 0.0 / 0.0 / 1.2 | 1.2 | 1.2 | 1.0 | 0.0 / 0.0 / 0.0 | 0.00 / 0.00 / 0.00 |
| Haworth | 0.0 / 0.0 / 4.6 | 4.6 | 4.6 | 4.0 | 2.0 / 2.0 / 1.7 | 0.00 / 0.00 / 0.00 |
| Malapert | 0.0 / 0.0 / 15.3 | 15.3 | 15.3 | 13.2 | 12.4 / 12.4 / 10.7 | 0.00 / 0.00 / 1.91 |
| de Gerlache-Kocher Massif | 0.0 / 0.0 / 18.1 | 18.1 | 18.1 | 15.7 | 15.1 / 15.1 / 13.1 | 0.00 / 0.00 / 2.26 |
| Nobile Rim 1 | 0.0 / 0.0 / 25.6 | 25.6 | 25.6 | 22.5 | 22.4 / 22.4 / 19.6 | 0.00 / 0.00 / 2.93 |
| Mons Mouton | 0.0 / 0.0 / 25.8 | 25.8 | 25.8 | 22.7 | 22.8 / 22.8 / 19.9 | 0.00 / 0.00 / 2.94 |
| Mons Mouton Plateau | 0.0 / 11.8 / 41.7 | 53.5 | 52.2 | 46.9 | 49.6 / 48.7 / 43.7 | 0.00 / 1.43 / 4.31 |
| Amundsen Rim | 0.0 / 13.8 / 42.8 | 56.6 | 55.0 | 49.5 | 52.6 / 51.4 / 46.3 | 0.00 / 1.72 / 4.41 |
| Nobile Rim 2 | 0.0 / 19.9 / 45.8 | 65.6 | 63.3 | 57.2 | 61.4 / 59.6 / 53.8 | 0.00 / 2.34 / 4.70 |
| Peak near Cabeus B | 1.2 / 26.8 / 48.8 | 76.8 | 73.0 | 66.1 | 72.0 / 69.3 / 62.7 | 0.00 / 2.87 / 4.99 |

Source: `validation.json` → `haughton_july.targets.<target>.flat_hours`, `.flat_hours_july`, `.snow_free_hours_july`, `.open_hours_july`, `.long_flat_hours_july`, `.long_snow_free_hours_july`, `.long_open_hours_july`, `.median_longest_stretch_h`; `haughton_july.snow_free_odds`. Unlike the other tables of this file, the first four columns count every hour in the band, whatever the length of the spell.

- At 75.4 N the July Sun stays above the limits for most of the month. Flat-horizon hours in the band in July, any spell length: 0.0 h (Connecting ridge; none in July), 0.0 h (Connecting Ridge Extension; none in July), 0.0 h (Peak Near Shackleton; none in July), 0.0 h (de Gerlache Rim 1; none in July), 0.0 h (de Gerlache Rim 2; none in July), 0.0 h (Faustini Rim A; none in July), 1.2 h (Slater Plain; first in the bin 20 Jul-29 Jul), 4.6 h (Haworth; first in the bin 20 Jul-29 Jul), 15.3 h (Malapert; first in the bin 20 Jul-29 Jul), 18.1 h (de Gerlache-Kocher Massif; first in the bin 20 Jul-29 Jul), 25.6 h (Nobile Rim 1; first in the bin 20 Jul-29 Jul), 25.8 h (Mons Mouton; first in the bin 20 Jul-29 Jul), 53.5 h (Mons Mouton Plateau; first in the bin 10 Jul-19 Jul), 56.6 h (Amundsen Rim; first in the bin 10 Jul-19 Jul), 65.6 h (Nobile Rim 2; first in the bin 10 Jul-19 Jul), 76.8 h (Peak near Cabeus B; first in the bin 30 Jun-9 Jul). The 2001 test used 24-hour daylight, which is not the same as Sun inside a lunar band.
- Over the whole year the Haughton cell has long-window open hours of 10.0 h (Connecting ridge), 15.7 h (Connecting Ridge Extension), 19.2 h (Peak Near Shackleton), 21.3 h (de Gerlache Rim 1), 29.9 h (de Gerlache Rim 2), 37.6 h (Faustini Rim A), 57.7 h (Slater Plain), 71.1 h (Haworth), 102.0 h (Malapert), 109.7 h (de Gerlache-Kocher Massif), 131.0 h (Nobile Rim 1), 131.8 h (Mons Mouton), 219.7 h (Mons Mouton Plateau), 224.8 h (Amundsen Rim), 239.6 h (Nobile Rim 2), 256.4 h (Peak near Cabeus B); best bins for Nobile Rim 2: 30 Jul-8 Aug (55 h), 9 Aug-18 Aug (48 h), 20 Jul-29 Jul (41 h) (`named_sites.sites[].targets.<target>.open.long.year`, `.top_bins`).

## (g) Antarctica: snow not measured

No open product measures winter snow on Antarctic rock, so the 1,241 southern cells have no snow-free hours (`snow.status` = unmeasured, `snow_free_hours` null). Their light counts the rock season only, 27 November to 1 March, when the rock maps were made from snow-free scenes; they are ranked apart from the north.

| Target | Flat horizon ≥ 50 h | ≥ 100 h | ≥ 200 h | with the real horizon, over the 1,220 southern cells that have one (21 have none): cells ≥ 50 / 100 / 200 h |
|---|---|---|---|---|
| Connecting ridge | 76 cells, 2,295 km² | 27 cells, 688 km² | 0 cells, 0 km² | 4 / 0 / 0 |
| Connecting Ridge Extension | 86 cells, 2,514 km² | 56 cells, 1,453 km² | 0 cells, 0 km² | 11 / 0 / 0 |
| Peak Near Shackleton | 96 cells, 2,803 km² | 66 cells, 1,899 km² | 0 cells, 0 km² | 16 / 0 / 0 |
| de Gerlache Rim 1 | 99 cells, 2,898 km² | 67 cells, 1,934 km² | 0 cells, 0 km² | 20 / 0 / 0 |
| de Gerlache Rim 2 | 594 cells, 23,119 km² | 80 cells, 2,250 km² | 0 cells, 0 km² | 39 / 4 / 0 |
| Faustini Rim A | 755 cells, 29,501 km² | 93 cells, 2,592 km² | 0 cells, 0 km² | 77 / 13 / 0 |
| Slater Plain | 828 cells, 31,264 km² | 294 cells, 9,360 km² | 64 cells, 1,745 km² | 189 / 33 / 0 |
| Haworth | 869 cells, 32,187 km² | 733 cells, 28,946 km² | 98 cells, 2,892 km² | 293 / 55 / 1 |
| Malapert | 950 cells, 35,229 km² | 762 cells, 29,716 km² | 220 cells, 6,822 km² | 476 / 154 / 15 |
| de Gerlache-Kocher Massif | 980 cells, 36,279 km² | 775 cells, 30,004 km² | 302 cells, 9,434 km² | 517 / 185 / 20 |
| Nobile Rim 1 | 1,027 cells, 38,133 km² | 825 cells, 31,386 km² | 387 cells, 11,962 km² | 614 / 282 / 34 |
| Mons Mouton | 1,027 cells, 38,133 km² | 825 cells, 31,386 km² | 387 cells, 11,962 km² | 615 / 283 / 35 |
| Mons Mouton Plateau | 1,189 cells, 42,594 km² | 958 cells, 35,090 km² | 672 cells, 26,572 km² | 854 / 484 / 159 |
| Amundsen Rim | 1,195 cells, 42,809 km² | 984 cells, 35,919 km² | 685 cells, 27,020 km² | 873 / 498 / 168 |
| Nobile Rim 2 | 1,205 cells, 43,111 km² | 1,056 cells, 38,515 km² | 738 cells, 29,240 km² | 926 / 552 / 209 |
| Peak near Cabeus B | 1,213 cells, 43,237 km² | 1,122 cells, 40,547 km² | 763 cells, 29,827 km² | 994 / 608 / 248 |

Source: `grazing_cells.json` → southern gridded cells, `targets.<target>.long_summer_rock_hours`, `long_summer_rock_open_hours`, `bare_km2`.

- The 1,241 cells hold 43,684 km² of mapped rock; regions: Transantarctic Mountains 445, Victoria Land 291, Antarctic Peninsula and South Shetlands 182, Enderby and Mac.Robertson Land 121, Dronning Maud Land 113, Ellsworth Mountains 54, Antarctica 13, Princess Elizabeth Land 9, Wilkes Land 8, South Orkney Islands 5 (`region`, `bare_km2`).
- In 616 of them the two rock-outcrop layers differ by more than a factor of 2 (`layers_disagree`).
- 617 southern cells are ranked (a horizon and bare ≥ 0.25). See (d) for what terrain takes away in the south.

**Connecting Ridge: lighting goal, top 3 of the south (rock season only):**

| # | Cell centre (lat, lon) | Region | Bare | Long-window hours in the rock season: open (flat horizon) | Typical clear-sky hours in the rock season | Score | When to go: best ten-day bins | Time of day | Known or little known |
|---|---|---|---|---|---|---|---|---|---|
| 1 | -68.45, 78.15 | Princess Elizabeth Land | 0.89 | 27 (64) | 10 | 0.345 | 27 Nov-6 Dec (12 h), 1 Jan-10 Jan (8 h), 11 Jan-20 Jan (6 h) | 100% of the hours with the Sun in the south (around midnight) | little known |
| 2 | -67.75, -68.55 | Antarctic Peninsula and South Shetlands | 0.37 | 57 (93) | 9 | 0.323 | 1 Jan-10 Jan (18 h), 7 Dec-16 Dec (15 h), 27 Nov-6 Dec (13 h) | 100% of the hours with the Sun in the south (around midnight) | little known |
| 3 | -66.45, 110.55 | Wilkes Land | 0.62 | 24 (73) | 7 | 0.270 | 17 Dec-31 Dec (17 h), 7 Dec-16 Dec (6 h), 1 Jan-10 Jan (0.6 h) | 100% of the hours with the Sun in the south (around midnight) | little known |

**Connecting Ridge Extension: lighting goal, top 3 of the south (rock season only):**

| # | Cell centre (lat, lon) | Region | Bare | Long-window hours in the rock season: open (flat horizon) | Typical clear-sky hours in the rock season | Score | When to go: best ten-day bins | Time of day | Known or little known |
|---|---|---|---|---|---|---|---|---|---|
| 1 | -68.45, 78.15 | Princess Elizabeth Land | 0.89 | 50 (98) | 18 | 0.474 | 1 Jan-10 Jan (16 h), 27 Nov-6 Dec (16 h), 7 Dec-16 Dec (10 h) | 100% of the hours with the Sun in the south (around midnight) | little known |
| 2 | -67.75, -68.55 | Antarctic Peninsula and South Shetlands | 0.37 | 81 (131) | 13 | 0.386 | 17 Dec-31 Dec (25 h), 1 Jan-10 Jan (21 h), 7 Dec-16 Dec (18 h) | 100% of the hours with the Sun in the south (around midnight) | little known |
| 3 | -67.85, -67.35 | Antarctic Peninsula and South Shetlands | 0.55 | 34 (132) | 6 | 0.308 | 17 Dec-31 Dec (10 h), 1 Jan-10 Jan (9 h), 7 Dec-16 Dec (8 h) | 100% of the hours with the Sun in the south (around midnight) | little known |

**Peak Near Shackleton: lighting goal, top 3 of the south (rock season only):**

| # | Cell centre (lat, lon) | Region | Bare | Long-window hours in the rock season: open (flat horizon) | Typical clear-sky hours in the rock season | Score | When to go: best ten-day bins | Time of day | Known or little known |
|---|---|---|---|---|---|---|---|---|---|
| 1 | -68.45, 78.15 | Princess Elizabeth Land | 0.89 | 71 (126) | 26 | 0.561 | 1 Jan-10 Jan (18 h), 27 Nov-6 Dec (17 h), 7 Dec-16 Dec (17 h) | 100% of the hours with the Sun in the south (around midnight) | little known |
| 2 | -67.75, -68.55 | Antarctic Peninsula and South Shetlands | 0.37 | 88 (142) | 14 | 0.401 | 17 Dec-31 Dec (27 h), 1 Jan-10 Jan (22 h), 7 Dec-16 Dec (20 h) | 100% of the hours with the Sun in the south (around midnight) | little known |
| 3 | -67.85, -67.35 | Antarctic Peninsula and South Shetlands | 0.55 | 38 (143) | 7 | 0.323 | 17 Dec-31 Dec (12 h), 1 Jan-10 Jan (9 h), 7 Dec-16 Dec (8 h) | 100% of the hours with the Sun in the south (around midnight) | little known |

**de Gerlache Rim 1: lighting goal, top 3 of the south (rock season only):**

| # | Cell centre (lat, lon) | Region | Bare | Long-window hours in the rock season: open (flat horizon) | Typical clear-sky hours in the rock season | Score | When to go: best ten-day bins | Time of day | Known or little known |
|---|---|---|---|---|---|---|---|---|---|
| 1 | -68.45, 78.15 | Princess Elizabeth Land | 0.89 | 88 (150) | 33 | 0.627 | 17 Dec-31 Dec (25 h), 1 Jan-10 Jan (19 h), 7 Dec-16 Dec (18 h) | 100% of the hours with the Sun in the south (around midnight) | little known |
| 2 | -67.75, -68.55 | Antarctic Peninsula and South Shetlands | 0.37 | 91 (147) | 15 | 0.408 | 17 Dec-31 Dec (29 h), 1 Jan-10 Jan (23 h), 7 Dec-16 Dec (21 h) | 100% of the hours with the Sun in the south (around midnight) | little known |
| 3 | -67.85, -67.35 | Antarctic Peninsula and South Shetlands | 0.55 | 40 (149) | 7 | 0.331 | 17 Dec-31 Dec (12 h), 1 Jan-10 Jan (10 h), 7 Dec-16 Dec (9 h) | 100% of the hours with the Sun in the south (around midnight) | little known |

**de Gerlache Rim 2: lighting goal, top 3 of the south (rock season only):**

| # | Cell centre (lat, lon) | Region | Bare | Long-window hours in the rock season: open (flat horizon) | Typical clear-sky hours in the rock season | Score | When to go: best ten-day bins | Time of day | Known or little known |
|---|---|---|---|---|---|---|---|---|---|
| 1 | -68.45, 78.15 | Princess Elizabeth Land | 0.89 | 109 (176) | 41 | 0.696 | 17 Dec-31 Dec (32 h), 1 Jan-10 Jan (23 h), 7 Dec-16 Dec (22 h) | 100% of the hours with the Sun in the south (around midnight) | little known |
| 2 | -67.75, -68.55 | Antarctic Peninsula and South Shetlands | 0.37 | 104 (168) | 17 | 0.436 | 17 Dec-31 Dec (33 h), 1 Jan-10 Jan (25 h), 7 Dec-16 Dec (23 h) | 100% of the hours with the Sun in the south (around midnight) | little known |
| 3 | -70.55, 68.25 | Enderby and Mac.Robertson Land | 0.51 | 59 (71) | 30 | 0.390 | 11 Jan-20 Jan (29 h), 21 Jan-30 Jan (16 h), 27 Nov-6 Dec (13 h) | 100% of the hours with the Sun in the south (around midnight) | little known |

**Faustini Rim A: lighting goal, top 3 of the south (rock season only):**

| # | Cell centre (lat, lon) | Region | Bare | Long-window hours in the rock season: open (flat horizon) | Typical clear-sky hours in the rock season | Score | When to go: best ten-day bins | Time of day | Known or little known |
|---|---|---|---|---|---|---|---|---|---|
| 1 | -68.45, 78.15 | Princess Elizabeth Land | 0.89 | 123 (193) | 46 | 0.740 | 17 Dec-31 Dec (36 h), 1 Jan-10 Jan (26 h), 7 Dec-16 Dec (25 h) | 100% of the hours with the Sun in the south (around midnight) | little known |
| 2 | -67.75, -68.55 | Antarctic Peninsula and South Shetlands | 0.37 | 114 (184) | 19 | 0.457 | 17 Dec-31 Dec (36 h), 1 Jan-10 Jan (27 h), 7 Dec-16 Dec (25 h) | 100% of the hours with the Sun in the south (around midnight) | little known |
| 3 | -70.55, 68.25 | Enderby and Mac.Robertson Land | 0.51 | 79 (92) | 40 | 0.450 | 11 Jan-20 Jan (33 h), 27 Nov-6 Dec (21 h), 21 Jan-30 Jan (19 h) | 100% of the hours with the Sun in the south (around midnight) | little known |

**Slater Plain: lighting goal, top 3 of the south (rock season only):**

| # | Cell centre (lat, lon) | Region | Bare | Long-window hours in the rock season: open (flat horizon) | Typical clear-sky hours in the rock season | Score | When to go: best ten-day bins | Time of day | Known or little known |
|---|---|---|---|---|---|---|---|---|---|
| 1 | -68.45, 78.15 | Princess Elizabeth Land | 0.89 | 153 (230) | 57 | 0.825 | 17 Dec-31 Dec (46 h), 7 Dec-16 Dec (31 h), 1 Jan-10 Jan (31 h) | 100% of the hours with the Sun in the south (around midnight) | little known |
| 2 | -70.55, 68.25 | Enderby and Mac.Robertson Land | 0.51 | 136 (152) | 69 | 0.590 | 11 Jan-20 Jan (39 h), 27 Nov-6 Dec (33 h), 1 Jan-10 Jan (26 h) | 100% of the hours with the Sun in the south (around midnight) | little known |
| 3 | -69.45, 39.75 | Dronning Maud Land | 0.61 | 94 (219) | 41 | 0.534 | 17 Dec-31 Dec (24 h), 1 Jan-10 Jan (17 h), 27 Nov-6 Dec (17 h) | 100% of the hours with the Sun in the south (around midnight) | little known |

**Haworth: lighting goal, top 3 of the south (rock season only):**

| # | Cell centre (lat, lon) | Region | Bare | Long-window hours in the rock season: open (flat horizon) | Typical clear-sky hours in the rock season | Score | When to go: best ten-day bins | Time of day | Known or little known |
|---|---|---|---|---|---|---|---|---|---|
| 1 | -68.45, 78.15 | Princess Elizabeth Land | 0.89 | 169 (249) | 63 | 0.868 | 17 Dec-31 Dec (50 h), 7 Dec-16 Dec (34 h), 1 Jan-10 Jan (33 h) | 100% of the hours with the Sun in the south (around midnight) | little known |
| 2 | -70.55, 68.25 | Enderby and Mac.Robertson Land | 0.51 | 199 (218) | 101 | 0.714 | 11 Jan-20 Jan (42 h), 27 Nov-6 Dec (37 h), 17 Dec-31 Dec (32 h) | 100% of the hours with the Sun in the south (around midnight) | little known |
| 3 | -69.45, 39.75 | Dronning Maud Land | 0.61 | 108 (243) | 47 | 0.573 | 17 Dec-31 Dec (28 h), 1 Jan-10 Jan (20 h), 27 Nov-6 Dec (19 h) | 100% of the hours with the Sun in the south (around midnight) | little known |

**Malapert Massif: lighting goal, top 3 of the south (rock season only):**

| # | Cell centre (lat, lon) | Region | Bare | Long-window hours in the rock season: open (flat horizon) | Typical clear-sky hours in the rock season | Score | When to go: best ten-day bins | Time of day | Known or little known |
|---|---|---|---|---|---|---|---|---|---|
| 1 | -68.45, 78.15 | Princess Elizabeth Land | 0.89 | 201 (287) | 75 | 0.943 | 17 Dec-31 Dec (58 h), 7 Dec-16 Dec (38 h), 1 Jan-10 Jan (38 h) | 100% of the hours with the Sun in the south (around midnight) | little known |
| 2 | -70.75, 67.95 | Enderby and Mac.Robertson Land | 0.79 | 152 (272) | 74 | 0.772 | 17 Dec-31 Dec (29 h), 11 Jan-20 Jan (26 h), 27 Nov-6 Dec (25 h) | 100% of the hours with the Sun in the south (around midnight) | little known |
| 3 | -71.25, 67.35 | Enderby and Mac.Robertson Land | 0.50 | 215 (257) | 116 | 0.710 | 11 Jan-20 Jan (41 h), 21 Jan-30 Jan (37 h), 27 Nov-6 Dec (36 h) | 100% of the hours with the Sun in the south (around midnight) | little known |

**de Gerlache-Kocher Massif: lighting goal, top 3 of the south (rock season only):**

| # | Cell centre (lat, lon) | Region | Bare | Long-window hours in the rock season: open (flat horizon) | Typical clear-sky hours in the rock season | Score | When to go: best ten-day bins | Time of day | Known or little known |
|---|---|---|---|---|---|---|---|---|---|
| 1 | -68.45, 78.15 | Princess Elizabeth Land | 0.89 | 208 (296) | 77 | 0.943 | 17 Dec-31 Dec (59 h), 7 Dec-16 Dec (40 h), 1 Jan-10 Jan (39 h) | 100% of the hours with the Sun in the south (around midnight) | little known |
| 2 | -70.75, 67.95 | Enderby and Mac.Robertson Land | 0.79 | 160 (283) | 79 | 0.794 | 17 Dec-31 Dec (31 h), 11 Jan-20 Jan (27 h), 27 Nov-6 Dec (26 h) | 100% of the hours with the Sun in the south (around midnight) | little known |
| 3 | -71.35, 170.25 | Victoria Land | 0.88 | 117 (268) | 32 | 0.719 | 21 Jan-30 Jan (22 h), 11 Jan-20 Jan (20 h), 17 Dec-31 Dec (18 h) | 100% of the hours with the Sun in the south (around midnight) | little known |

**Nobile Rim 1: lighting goal, top 3 of the south (rock season only):**

| # | Cell centre (lat, lon) | Region | Bare | Long-window hours in the rock season: open (flat horizon) | Typical clear-sky hours in the rock season | Score | When to go: best ten-day bins | Time of day | Known or little known |
|---|---|---|---|---|---|---|---|---|---|
| 1 | -68.45, 78.15 | Princess Elizabeth Land | 0.89 | 225 (316) | 83 | 0.943 | 17 Dec-31 Dec (63 h), 7 Dec-16 Dec (42 h), 1 Jan-10 Jan (41 h) | 100% of the hours with the Sun in the south (around midnight) | little known |
| 2 | -70.75, 67.95 | Enderby and Mac.Robertson Land | 0.79 | 182 (311) | 89 | 0.844 | 17 Dec-31 Dec (36 h), 11 Jan-20 Jan (30 h), 27 Nov-6 Dec (28 h) | 100% of the hours with the Sun in the south (around midnight) | little known |
| 3 | -71.35, 170.25 | Victoria Land | 0.88 | 133 (300) | 36 | 0.766 | 21 Jan-30 Jan (23 h), 17 Dec-31 Dec (22 h), 11 Jan-20 Jan (22 h) | 100% of the hours with the Sun in the south (around midnight) | little known |

**Mons Mouton: lighting goal, top 3 of the south (rock season only):**

| # | Cell centre (lat, lon) | Region | Bare | Long-window hours in the rock season: open (flat horizon) | Typical clear-sky hours in the rock season | Score | When to go: best ten-day bins | Time of day | Known or little known |
|---|---|---|---|---|---|---|---|---|---|
| 1 | -68.45, 78.15 | Princess Elizabeth Land | 0.89 | 225 (316) | 83 | 0.943 | 17 Dec-31 Dec (63 h), 7 Dec-16 Dec (42 h), 1 Jan-10 Jan (41 h) | 100% of the hours with the Sun in the south (around midnight) | little known |
| 2 | -70.75, 67.95 | Enderby and Mac.Robertson Land | 0.79 | 182 (312) | 89 | 0.846 | 17 Dec-31 Dec (37 h), 11 Jan-20 Jan (30 h), 27 Nov-6 Dec (28 h) | 100% of the hours with the Sun in the south (around midnight) | little known |
| 3 | -71.35, 170.25 | Victoria Land | 0.88 | 134 (301) | 36 | 0.767 | 21 Jan-30 Jan (23 h), 17 Dec-31 Dec (22 h), 11 Jan-20 Jan (22 h) | 100% of the hours with the Sun in the south (around midnight) | little known |

**Mons Mouton Plateau: lighting goal, top 3 of the south (rock season only):**

| # | Cell centre (lat, lon) | Region | Bare | Long-window hours in the rock season: open (flat horizon) | Typical clear-sky hours in the rock season | Score | When to go: best ten-day bins | Time of day | Known or little known |
|---|---|---|---|---|---|---|---|---|---|
| 1 | -68.55, 78.15 | Princess Elizabeth Land | 0.91 | 220 (376) | 81 | 0.954 | 17 Dec-31 Dec (59 h), 7 Dec-16 Dec (39 h), 1 Jan-10 Jan (38 h) | 100% of the hours with the Sun in the south (around midnight) | little known |
| 2 | -70.75, 67.95 | Enderby and Mac.Robertson Land | 0.79 | 242 (391) | 118 | 0.886 | 17 Dec-31 Dec (49 h), 11 Jan-20 Jan (36 h), 27 Nov-6 Dec (35 h) | 100% of the hours with the Sun in the south (around midnight) | little known |
| 3 | -71.35, 170.25 | Victoria Land | 0.88 | 177 (389) | 47 | 0.882 | 17 Dec-31 Dec (31 h), 21 Jan-30 Jan (26 h), 11 Jan-20 Jan (26 h) | 100% of the hours with the Sun in the south (around midnight) | little known |

**Amundsen Rim: lighting goal, top 3 of the south (rock season only):**

| # | Cell centre (lat, lon) | Region | Bare | Long-window hours in the rock season: open (flat horizon) | Typical clear-sky hours in the rock season | Score | When to go: best ten-day bins | Time of day | Known or little known |
|---|---|---|---|---|---|---|---|---|---|
| 1 | -68.55, 78.15 | Princess Elizabeth Land | 0.91 | 224 (382) | 83 | 0.954 | 17 Dec-31 Dec (60 h), 7 Dec-16 Dec (39 h), 1 Jan-10 Jan (38 h) | 100% of the hours with the Sun in the south (around midnight) | little known |
| 2 | -71.35, 170.25 | Victoria Land | 0.88 | 181 (398) | 48 | 0.892 | 17 Dec-31 Dec (31 h), 21 Jan-30 Jan (27 h), 11 Jan-20 Jan (26 h) | 100% of the hours with the Sun in the south (around midnight) | little known |
| 3 | -73.45, 61.75 | Enderby and Mac.Robertson Land | 0.92 | 173 (336) | 92 | 0.890 | 31 Jan-9 Feb (33 h), 21 Jan-30 Jan (33 h), 11 Jan-20 Jan (25 h) | 100% of the hours with the Sun in the south (around midnight) | little known |

**Nobile Rim 2: lighting goal, top 3 of the south (rock season only):**

| # | Cell centre (lat, lon) | Region | Bare | Long-window hours in the rock season: open (flat horizon) | Typical clear-sky hours in the rock season | Score | When to go: best ten-day bins | Time of day | Known or little known |
|---|---|---|---|---|---|---|---|---|---|
| 1 | -73.45, 61.75 | Enderby and Mac.Robertson Land | 0.92 | 208 (402) | 111 | 0.957 | 21 Jan-30 Jan (34 h), 31 Jan-9 Feb (34 h), 11 Jan-20 Jan (27 h) | 100% of the hours with the Sun in the south (around midnight) | little known |
| 2 | -68.55, 78.15 | Princess Elizabeth Land | 0.91 | 236 (398) | 87 | 0.954 | 17 Dec-31 Dec (62 h), 7 Dec-16 Dec (41 h), 1 Jan-10 Jan (39 h) | 100% of the hours with the Sun in the south (around midnight) | little known |
| 3 | -71.35, 170.25 | Victoria Land | 0.88 | 192 (421) | 50 | 0.920 | 17 Dec-31 Dec (33 h), 21 Jan-30 Jan (27 h), 11 Jan-20 Jan (27 h) | 100% of the hours with the Sun in the south (around midnight) | little known |

**Peak near Cabeus B: lighting goal, top 3 of the south (rock season only):**

| # | Cell centre (lat, lon) | Region | Bare | Long-window hours in the rock season: open (flat horizon) | Typical clear-sky hours in the rock season | Score | When to go: best ten-day bins | Time of day | Known or little known |
|---|---|---|---|---|---|---|---|---|---|
| 1 | -73.45, 61.75 | Enderby and Mac.Robertson Land | 0.92 | 227 (438) | 122 | 0.957 | 21 Jan-30 Jan (35 h), 31 Jan-9 Feb (35 h), 11 Jan-20 Jan (28 h) | 100% of the hours with the Sun in the south (around midnight) | little known |
| 2 | -68.55, 78.15 | Princess Elizabeth Land | 0.91 | 250 (416) | 91 | 0.954 | 17 Dec-31 Dec (64 h), 7 Dec-16 Dec (42 h), 1 Jan-10 Jan (41 h) | 100% of the hours with the Sun in the south (around midnight) | little known |
| 3 | -71.35, 170.25 | Victoria Land | 0.88 | 205 (447) | 54 | 0.939 | 17 Dec-31 Dec (35 h), 21 Jan-30 Jan (28 h), 11 Jan-20 Jan (28 h) | 100% of the hours with the Sun in the south (around midnight) | little known |

Source: `cells_scored.json` → southern records: `targets.<target>.goals.lighting`, `.long_summer_rock_open_hours`, `.long_summer_rock_hours`, `.long_summer_rock_open_hours_clear`, `.top_bins_summer_rock`, `.poleward_share_summer_rock`.

The named southern sites, with what is known about their winter snow:

| Site (south) | Cell | Bare / land share | In the screen | Winter-snow evidence | Horizon N / S | Malapert: rock-season long-window hours flat / open | Nobile Rim 2: the same |
|---|---|---|---|---|---|---|---|
| Bunger Hills | -66.3_100.5 | 0.60 / 0.88 | yes | literature: no continuous winter cover | 1.0° / 1.9° | 185 / 69 | 304 / 146 |
| Vestfold Hills | -68.6_78.0 | 0.91 / 0.74 | yes | one qualitative report | 1.2° / 1.8° | 288 / 154 | 398 / 236 |
| Larsemann Hills | -69.4_76.2 | 0.81 / 0.14 | no | station shows snow | 0.0° / 3.3° | 289 / 110 | 409 / 186 |
| Schirmacher Oasis | -70.8_11.4 | 0.18 / 1.00 | yes | literature: no continuous winter cover | 0.0° / 3.8° | 272 / 100 | 419 / 203 |
| Lake Untersee and the Eliseev anorthosite massif | -71.4_13.2 | 0.65 / 1.00 | yes | no evidence | 1.8° / 15.4° | 254 / 11 | 421 / 35 |
| McMurdo Dry Valleys | -77.6_161.5 | 0.89 / 1.00 | yes | measured mostly bare | 9.8° / 15.1° | 156 / 8 | 236 / 26 |
| Windmill Islands | -66.3_110.4 | 0.14 / 0.39 | no | station shows snow | -0.2° / 1.3° | 185 / 86 | 304 / 172 |
| Syowa and the Soya Coast | -69.1_39.3 | 0.52 / 0.10 | no | station shows snow | 0.5° / 0.4° | 289 / 233 | 405 / 338 |
| Fildes Peninsula | -62.2_-59.0 | 0.40 / 0.47 | yes | station shows snow | -0.1° / 1.6° | 0 / 0 | 0 / 0 |
| Deception Island | -63.0_-60.6 | 0.42 / 0.35 | yes | no evidence | 1.9° / 0.0° | 0 / 0 | 0 / 0 |
| Ulu Peninsula, James Ross Island | -63.9_-58.0 | 1.00 / 0.84 | yes | no evidence | 2.6° / 4.4° | 0 / 0 | 79 / 24 |
| Seymour Island | -64.3_-56.8 | 1.00 / 0.46 | yes | station shows snow | 1.1° / 2.3° | 0 / 0 | 124 / 67 |
| Rothera Point | -67.6_-68.4 | 0.11 / 0.44 | no | station shows snow | 4.3° / 0.7° | 271 / 154 | 371 / 215 |
| Jutulsessen at Troll | -72.1_2.4 | 0.31 / 1.00 | yes | one qualitative report | 0.3° / 3.2° | 189 / 66 | 419 / 203 |
| Northern Foothills, Terra Nova Bay | -74.8_164.0 | 0.90 / 0.15 | no | no evidence | 2.8° / 0.2° | 139 / 90 | 302 / 211 |

Source: `validation.json` → `named_sites.sites[]` (`.winter_snow_evidence` is copied from `data/reference/antarctic_sites.json`; `.targets.<target>.long_summer_rock_hours`, `.long_summer_rock_open_hours`).

- Evidence labels of the 15 sites: "station shows snow" 6, "no evidence" 4, "literature: no continuous winter cover" 2, "one qualitative report" 2, "measured mostly bare" 1. "Measured mostly bare": McMurdo Dry Valleys.

## (h) The old measure against the new

The first method counted days on which the Sun stays under the limit even at noon, times the snow-free odds ("usable days"). The new files keep that column with the corrected Sun and snow (`usable_days`).

| Target | Old file: cells with ≥ 10 usable days | New: measured cells with ≥ 10 | New: doubtful cells with ≥ 10 (not counted) | Regions of the new measured cells | Where the old cells are now | For scale: measured cells with ≥ 100 long-window snow-free hours |
|---|---|---|---|---|---|---|
| Connecting ridge | 0 | 0 | 0 | none | none | 2 |
| Malapert | 49 | 41 | 2 | Iceland 41 | still ≥ 10: 40; doubtful: 7; measured, now under 10: 2 | 7,481 |
| Mons Mouton | 52 | 45 | 2 | Iceland 45 | still ≥ 10: 44; doubtful: 7; measured, now under 10: 1 | 8,289 |
| Nobile Rim 2 | 57 | 50 | 2 | Iceland 49, Svalbard 1 | still ≥ 10: 48; doubtful: 8; measured, now under 10: 1 | 9,936 |

Source: `validation.json` → `old_against_new.targets.<target>.old`, `.new_measured`, `.new_doubtful`, `.new_measured_regions`; "where the old cells are now" was worked out here from `light_cells_v1.json` (`<cell>.<target>.usable_days`) and `grazing_cells.json` (`snow.status`, `usable_days`); last column `big_picture_north.targets.<target>.long_snow_free_hours.year.100.cells`.

| Target | Top lighting sites (new measure) | of them with ≥ 10 usable days (old measure) | of them with 0 usable days | Most usable days among them |
|---|---|---|---|---|
| Connecting ridge | 10 | 0 | 9 | 1.3 |
| Connecting Ridge Extension | 10 | 0 | 9 | 1.8 |
| Peak Near Shackleton | 10 | 0 | 9 | 1.8 |
| de Gerlache Rim 1 | 10 | 0 | 9 | 2.1 |
| de Gerlache Rim 2 | 10 | 0 | 9 | 2.3 |
| Faustini Rim A | 10 | 0 | 8 | 2.6 |
| Slater Plain | 10 | 0 | 7 | 3.1 |
| Haworth | 10 | 0 | 7 | 3.5 |
| Malapert | 10 | 0 | 5 | 3.4 |
| de Gerlache-Kocher Massif | 10 | 0 | 5 | 3.4 |
| Nobile Rim 1 | 10 | 0 | 5 | 3.9 |
| Mons Mouton | 10 | 0 | 4 | 3.9 |
| Mons Mouton Plateau | 10 | 0 | 5 | 5.1 |
| Amundsen Rim | 10 | 0 | 5 | 5.1 |
| Nobile Rim 2 | 10 | 1 | 4 | 28.2 |
| Peak near Cabeus B | 10 | 1 | 4 | 30.1 |

Source: `cells_scored.json` → `targets.<target>.usable_days` of the top-10 lighting sites.

- The old measure counts winter noon light only. The new one adds the dawn, dusk and midnight-Sun hours; of the long-window snow-free hours × bare km² 99.4%, 99.4%, 99.3%, 99.3%, 99.1%, 98.9%, 98.7%, 98.6%, 98.4%, 98.3%, 98.2%, 98.2%, 97.9%, 97.9%, 97.8%, 97.8% fall in the summer half for the four targets (see (b) and (c)).
- The first row of the old ranking (`ranking_v1.txt`) was: `0.36 74.45 19.25 Bear Island (Bjornoya) ...`. In the new files the cell of Bear Island is "doubtful" (3 stuck winters) and the cell of Jan Mayen is "doubtful" (5 stuck winters), so neither is ranked; see (i).

## (i) What is doubtful or not covered

### Cells without a terrain horizon

- 16,133 of the 16,184 cell records have a terrain horizon. 0 are stored as "tile not fetched": their elevation tiles were not on disk when the horizons were computed. 51 are refused because their 30 km window crosses the 180° meridian (`grazing_cells.json` → `horizon.skipped`).
- Among the 14,863 measured northern cells 30 have no horizon; among the 10,852 of them with bare ≥ 0.25, 15. Among the 1,241 southern cells 21 have none. Regions of the measured northern cells without a horizon: Siberia and the Russian Far East 17, Chukotka 13.
- For those cells the open hours, the clear-sky hours and every score that uses light are `n/a`; they are in no ranking; and every "with the real horizon" count in (b), (c), (g) and (j) is a count over the cells that have a horizon, so it is a lower bound. The flat-horizon counts in (b) and (c) cover every measured cell.

### Doubtful and no-data cells

- 36 gridded northern cells are **doubtful**: at least one winter in which a snow pixel read "snow-free" on every map at or north of 67.4 N, or three such winters anywhere (regions: Svalbard 18, Arctic Canada 6, Jan Mayen 6, Bear Island (Bjornoya) 2, North-west Greenland or Ellesmere 2, Greenland 1, Novaya Zemlya 1). 34 have **no snow data**: no land pixel of the 4 km snow grid within the 5 × 5 block (regions: Greenland 24, Arctic Canada 4, North-west Greenland or Ellesmere 4, Chukotka 1, Novaya Zemlya 1). Neither group is ranked or counted; all 70 are listed with both versions of their hours in `ranking.txt` under "DOUBTFUL SNOW OR NO SNOW DATA" (`grazing_cells.json` → `snow.status`, `snow.stuck_winters`, `region`).
- For a doubtful cell the main figure uses the stale-flag rule and is the lower one; the hours as the maps read are the upper one. The rule leaves out a pixel's whole spring and summer after a stuck winter if the pixel never reads snow before 30 September, so it lowers summer odds too:

| Site | Cell | Status | Stuck winters | Snow land pixels (of the block used) | Malapert: with the rule / as mapped / open (with the rule and terrain) | Nobile Rim 2: the same |
|---|---|---|---|---|---|---|
| Bear Island, Norway | 74.4_19.0 | doubtful | 3 | 5 of 9 | 184.5 / 285.1 / 123.7 | 449.6 / 677.9 / 329.7 |
| Jan Mayen, Norway | 70.9_-8.7 | doubtful | 5 | 3 of 9 | 197.0 / 394.3 / 79.5 | 327.9 / 660.2 / 144.8 |
| Lofoten anorthosite (Nusfjord), Norway | 68.0_13.2 | doubtful | 1 | 2 of 9 | 351.0 / 369.5 / 70.6 | 523.4 / 554.2 / 123.8 |

Source: `grazing_cells.json` → `snow.status`, `snow.stuck_winters`, `snow.land_pixels`, `snow.block_pixels`, `targets.<target>.long_snow_free_hours_with_rule`, `long_snow_free_hours_as_mapped`, `long_open_hours`.

### Measured cells with a stuck winter: the maps as they read

- 43 measured cells have one or two stuck winters (south of 67.4 N, so not doubtful). Since version 3 every measured cell uses the maps as they read, because at 8 of the 9 trusted stations with a stuck pixel nearby the odds as the maps read are closer to the station record than the odds with the stale-flag rule (at 1 the rule is closer, at 0 they are the same; mean absolute difference over the ten-day bins compared, worked out here from `snow_validation_many.json` → `stations[].satellite_as_mapped`, `.satellite`, `.station_share`; those stations lie at 59.3 to 67.9 N). For these cells the figure the rule would give is kept beside the main one:

| Target | Measured cells whose figure differs from the rule's | Largest rise | Cells with 0.0 h under the rule and more as mapped | their largest figure, h | of them with all those hours in the winter half |
|---|---|---|---|---|---|
| Connecting ridge | 5 | +5.1 h (52.1 to 57.2) at 66.35, 13.35, Norway, Sweden or Finland | 2 | 3.4 | 2 |
| Connecting Ridge Extension | 8 | +6.0 h (58.1 to 64.1) at 66.35, 13.35, Norway, Sweden or Finland | 3 | 4.2 | 3 |
| Peak Near Shackleton | 8 | +6.6 h (60.9 to 67.5) at 66.35, 13.35, Norway, Sweden or Finland | 3 | 4.6 | 3 |
| de Gerlache Rim 1 | 9 | +6.8 h (63.3 to 70.1) at 66.35, 13.35, Norway, Sweden or Finland | 4 | 4.8 | 4 |
| de Gerlache Rim 2 | 17 | +7.8 h (74.0 to 81.8) at 66.35, 13.35, Norway, Sweden or Finland | 6 | 6.1 | 6 |
| Faustini Rim A | 25 | +8.6 h (83.8 to 92.4) at 66.35, 13.35, Norway, Sweden or Finland | 14 | 7.5 | 14 |
| Slater Plain | 40 | +11.7 h (0.0 to 11.7) at 63.15, -64.90, Arctic Canada | 29 | 11.7 | 29 |
| Haworth | 42 | +15.2 h (0.0 to 15.2) at 62.65, -66.70, Arctic Canada | 30 | 15.2 | 30 |
| Malapert | 43 | +22.9 h (0.0 to 22.9) at 62.65, -66.70, Arctic Canada | 31 | 22.9 | 31 |
| de Gerlache-Kocher Massif | 43 | +24.3 h (0.0 to 24.3) at 62.65, -66.70, Arctic Canada | 31 | 24.3 | 31 |
| Nobile Rim 1 | 43 | +27.7 h (0.0 to 27.7) at 62.65, -66.70, Arctic Canada | 31 | 27.7 | 31 |
| Mons Mouton | 43 | +27.8 h (0.0 to 27.8) at 62.65, -66.70, Arctic Canada | 31 | 27.8 | 31 |
| Mons Mouton Plateau | 43 | +37.1 h (0.0 to 37.1) at 62.65, -66.70, Arctic Canada | 26 | 37.1 | 26 |
| Amundsen Rim | 43 | +38.0 h (0.0 to 38.0) at 62.65, -66.70, Arctic Canada | 26 | 38.0 | 26 |
| Nobile Rim 2 | 43 | +40.3 h (0.0 to 40.3) at 62.65, -66.70, Arctic Canada | 23 | 40.3 | 23 |
| Peak near Cabeus B | 43 | +42.9 h (0.0 to 42.9) at 62.65, -66.70, Arctic Canada | 19 | 42.9 | 19 |

Source: `grazing_cells.json` → measured gridded cells, `targets.<target>.long_snow_free_hours` (as mapped) against `long_snow_free_hours_with_rule`, `long_snow_free_hours_summer`.

- The 33 cells that rise from 0.0 h for at least one target do so on maps that read "snow-free" through a stuck winter (the last column says for how many of them all those hours are in the winter half), at 61.55 to 65.95 N (cell centres; Arctic Canada 31, Chukotka 1, Siberia and the Russian Far East 1). Whether a midwinter snow-free reading there is believable was not checked against any station; treat those winter hours as an upper figure. They move no count in (b) by more than one cell (the build's own before-and-after comparison; not recomputed here).
- 3 measured cells (72.7_-117.9, 72.9_-117.3, 74.4_-123.5) have snow odds in only some ten-day bins; their snow-free hours are `null` and they appear as "unknown" in every count.

### Snow odds: what they rest on

- **4 km snow pixels.** A cell's odds are the mean of the land pixels in a 3 × 3 block (12 km), so a coastal cell can rest on few pixels: 3,767 of the 14,863 measured cells have fewer than 7 pixels on land, and 158 take their odds from the wider 5 × 5 block because the 3 × 3 block has none (`snow.land_pixels` now counts the block that was used, `snow.block_pixels` = 9 or 25). Among the 10,837 ranked northern cells 3,089 have fewer than 7 (`snow.land_pixels`, `snow.source`). The stability table in (e) shows what a pixel screen does to the top lists.
- **Checked against weather stations (read from the station file of version 2, not recomputed).** Against 139 trusted stations the satellite odds of snow-free ground as the maps read, which are the odds every measured cell uses, are lower than the station record on average: -0.049 in the winter half, -0.094 in the summer half, -0.127 for May to August at the 50 stations at or north of 66 N that have such a bin (411 station-bins); with the stale-flag rule the same three figures are -0.051, -0.094 and -0.128. So, on average over these stations, the snow-free odds err on the low side where they can be tested; single stations differ either way. North of 66 N there are 56 kept stations (50 with a May-to-August bin) and none in Finland, Iceland, Greenland; Russia has 1. (`snow_validation_many.json` → `overall.stations`, `periods.<period>.as_mapped.mean_bias`, `.with_stale_flag_rule.mean_bias`, `north_of_66`. That file's own cell counts under calibrated odds were made with the version 2 long-window rule and the stale-flag rule for every cell, so they are not quoted here.)
- **Stale snow flags in summer on small Arctic islands.** The reverse fault is on record too: the build contract (decision 11) notes that Bear Island reads "snow" through the whole summer of 2024. No rule corrects it and it was not measured again here, so summer hours on such islands are understated by an unknown amount.

### Sun and terrain geometry

- **Standard refraction.** The Sun's apparent height uses refraction at standard pressure and temperature (0.48° at a true elevation of 0°, `sun.refraction_deg`). That value alone is 23% of the 2.08° band and 6% of the 7.59° band; real polar air can bend light more or less than the standard value, and nothing here measures by how much.
- **One ray per ten-degree sector.** The terrain horizon is taken along one ray at the centre of each of 36 azimuth sectors, on a 60 m grid, out to 25 km. At 25 km a sector is 4.4 km wide, so a peak or gap narrower than that can fall between rays.
- **The two-hour cut is sharp.** Version 3 follows each spell day by day, so a cell's total no longer hangs on whether a whole ten-day bin's median reaches 2.00 h. The minimum itself still matters, most where the Sun takes close to two hours to cross the band at sunrise and sunset. Flat-horizon hours a year inside spells of at least 1, 2 and 3 hours:

| Latitude | Malapert: 1 h / 2 h / 3 h minimum | Nobile Rim 2: 1 h / 2 h / 3 h minimum |
|---|---|---|
| 62 N | 622 / 190 / 149 | 1,192 / 381 / 302 |
| 66 N | 1,005 / 469 / 232 | 1,373 / 763 / 400 |
| 70 N | 1,077 / 590 / 474 | 1,387 / 949 / 690 |
| 74.5 N | 871 / 521 / 357 | 1,226 / 1,211 / 669 |
| 78 N | 804 / 682 / 396 | 1,104 / 1,097 / 782 |

Source: `latitude_profile.json` → `profile[].targets.<target>.long_flat_hours["1"|"2"|"3"]`.

- The reviewer of the per-day rule measured, by an independent route, that moving the minimum by one minute either way (1 h 59 min to 2 h 01 min) changes a cell's yearly long-window flat hours by 6 to 8 h at the median latitude and by up to 84 h (7%) near 74 to 78 degrees (reported by that review; not recomputed here). So these hours should not be read to the last hour; the 1 h and 3 h columns of the stability table in (e) bracket the choice.
- **Counted again from first principles.** A separate program that uses none of the project's code (`scripts/independent_recount.py`: its own Sun position at 1-minute steps, the mean of eight calendars 1/8 day apart written in its own code, its own finding of the spells, its own reading of the snow grid; the Sun series and the terrain's open share are the project's) worked out the hours of all 16,184 cells for the 4 targets again on 2026-11-15: 1,359,456 figures, 0 outside a tolerance of the larger of 2 percent and 1 hour a year; or known in one and unknown in the other; the largest difference is 0.07 h a year and 0.007 h in a ten-day bin; 0 snow summaries differ. It was run on earlier files (`grazing_cells.json` or `grazing_bins.npz` has changed since), so its agreement with this run is not established. With every calendar moved 0.14 day later, the yearly long-window flat hours move by more than that tolerance in 0 of the 12,559 cells with such hours for Connecting ridge (up to 1.2 h), 0 of the 15,691 cells with such hours for Malapert (up to 0.8 h), 0 of the 15,999 cells with such hours for Mons Mouton (up to 0.8 h), 0 of the 16,184 cells with such hours for Nobile Rim 2 (up to 0.8 h). (`checks.json` → `independent_recount`.)
- **Sun geometry against NASA JPL Horizons.** At 9 places and 4 ten-day periods each, the Sun tables (an earlier version of the Sun code than this run, mean of 8 calendars) were set beside Horizons' refracted Sun for the dates of 2026, read from saved answers (2026-11-15). All hours in each band differ by a median of 0.11 percent (largest 6.3 percent, 0.63 h, over 144 rows); hours in spells of 2 h or more by a median of 0.26 percent (largest 8.0 percent, 1.60 h). 5 rows differ by more than 5 percent or 1 hour: vestfold, midsummer period, Connecting ridge, all hours, +0.24 h (+6.3 percent; the average over calendars: the project's single calendar of day 0 gives 3.96 h, within the flag rule of Horizons' 3.83 h; the mean of the calendars a fraction of a day apart gives 4.07 h); lofoten, best period, Connecting ridge, hours in spells of 2 h or more, -1.60 h (-7.2 percent; the average over calendars: the project's single calendar of day 0 gives 21.93 h, within the flag rule of Horizons' 22.12 h; the mean of the calendars a fraction of a day apart gives 20.52 h (at the two-hour cut, the day on which spells first or last reach 2 h differs between calendars)); haughton, best period, Connecting ridge, hours in spells of 2 h or more, -1.22 h (-5.4 percent; on 1 of the 10 days the longest Horizons spell is within 15 minutes of the 2-hour cut (2.05 h), so a small shift of the calendar decides whether the day counts; the project's single calendar gives 21.05 h); pechora, best period, Connecting ridge, hours in spells of 2 h or more, -1.51 h (-5.6 percent; the average over calendars: the project's single calendar of day 0 gives 26.95 h, within the flag rule of Horizons' 27.01 h; the mean of the calendars a fraction of a day apart gives 25.50 h (at the two-hour cut, the day on which spells first or last reach 2 h differs between calendars)); vestfold, best period, Connecting ridge, hours in spells of 2 h or more, -1.50 h (-8.0 percent; the average over calendars: the project's single calendar of day 0 gives 18.78 h, within the flag rule of Horizons' 18.85 h; the mean of the calendars a fraction of a day apart gives 17.35 h (at the two-hour cut, the day on which spells first or last reach 2 h differs between calendars)). (`checks.json` → `jpl_horizons`; the raw answers are in `data/raw/horizons_check/`.)
- **The leap-cycle average.** Where noon falls against the seasons moves by a quarter of a day from one year to the next (and back in a leap year), and it moves with longitude too, so a sharp two-hour rule makes a single calendar's long-window hours depend on where that calendar sits. So every Sun table behind the hours of this file is the mean over eight calendars, 1/8 day apart and centred on the middle of the 2024 to 2028 leap cycle (`grazing_cells.json` → `meta.year_phases` = 8). What remains: the worst move of the calendar (1/16 day) changes a latitude's yearly long-window hours by at most 1.5 h over all 468 cell latitudes, never by more than the larger of 2% and 1 h; at 65, 67, 70, 75 and 80° north and south by at most 1.0 h, within 1% or half an hour (a move of 0.14 day: at most 0.75 h). Read long-window hours as about ±1 h, not to the hour; all-hours figures move by far less. (Measured with the project's Sun code by the leap-cycle step; not recomputed here.)
- **The 59-degree band edge.** See (a): with the 2 h rule Mons Mouton Plateau's belt begins at 58.25°, 0.75° outside the band; Amundsen Rim's belt begins at 58.10°, 0.90° outside the band; Nobile Rim 2's belt begins at 57.65°, 1.35° outside the band; Peak near Cabeus B's belt begins at 57.15°, 1.85° outside the band; the other 12 targets start inside it.
- **Known or little known.** A cell counts as known when it lies within 50 km of one of the 85 sites of `data/reference/known_analogs.json`, in Iceland or Svalbard, inside hand-drawn boxes for Devon Island and the McMurdo Dry Valleys, within 50 km of a southern site with analog use, or on an anorthosite body the rock list marks as already used. 10,000 of the 10,837 ranked northern cells and 528 of the 617 ranked southern cells are little known (`cells_scored.json` → `little_known`). The boxes were not checked against a coastline file.
- **Light score.** It stops at 200 hours, so cells with 200 and 400 open hours score the same; the tables in (e) order such ties by hours.

### What this match is and is not

- These sites match the **height of the Sun and the length of shadows**, for hours at a time. At the four limits a 1 m rock throws a shadow of at least 27.5 m (Connecting ridge), 22.8 m (Connecting Ridge Extension), 21.0 m (Peak Near Shackleton), 20.0 m (de Gerlache Rim 1), 17.3 m (de Gerlache Rim 2), 15.7 m (Faustini Rim A), 13.1 m (Slater Plain), 12.0 m (Haworth), 10.3 m (Malapert), 10.0 m (de Gerlache-Kocher Massif), 9.4 m (Nobile Rim 1), 9.3 m (Mons Mouton), 7.9 m (Mons Mouton Plateau), 7.8 m (Amundsen Rim), 7.5 m (Nobile Rim 2), 7.2 m (Peak near Cabeus B) (1 ÷ tan of the limit).
- They do not match **how fast the Sun's compass direction moves**. Near the horizon it moves about 15° × sin(latitude) per hour on Earth: 13.0° per hour at 60°, 14.1° per hour at 70°, 14.8° per hour at 80°. At the Moon's south pole the Sun goes once round the horizon in a synodic month, 0.508° per hour (about 0.51). The ratio is 25.6 at 60°, 27.7 at 70°, 29.1 at 80°. In a two-hour low-Sun spell on Earth the shadows swing through 26° to 30°; on the Moon through 1.0°. A test that needs the lunar pace of the shadows cannot get it at any of these sites (15 × sin φ and 360 ÷ 29.53 days; computed here, not read from a file).
- They do not match lunar **contrast**. Earth's air scatters light into shadows and dims and reddens a Sun this low; on the Moon shadows are black and the Sun is at full strength. No number in this file measures that difference.
- They do not promise a **visible Sun**. Section (j) gives typical clear-sky hours from monthly mean cloud; that is a coarse guide, not a forecast.
- What no site on Earth matches at all: vacuum, lunar dust, one-sixth gravity, the Moon's temperature swings, and its radiation.

## (j) Cloud: typical clear-sky hours

**What the column is.** Monthly mean share of the sky covered by cloud, in percent, averaged over all hours of the day and night and over the years of the period, for the 1 degree grid box that holds the cell centre (CERES SYN1deg cloud amount as served by NASA POWER). Many cells share one box. Source: NASA POWER, POWER Climatology API v2.10.1, regional endpoint; data source named by the service: SYN1DEG (CERES SYN1deg); parameter `CLOUD_AMT`; period 2001-01-01 to 2025-12-31. A cell's typical clear-sky hours are its long-window open hours in each ten-day bin times (1 − cloud percent ÷ 100) of the bin's month, summed (`cells_scored.json` → `cloud.pct_by_month`, `targets.<target>.long_open_hours_clear`, `long_open_hours_clear_winter`, `long_open_hours_clear_summer`; southern cells `long_summer_rock_open_hours_clear`).

**What it is not.** Not the chance that a low Sun is visible. A Sun a few degrees above the horizon shines through a long slanted path, so the same share of cloud hides it more often than it hides a high Sun. The figure is a mean over the whole day and over a box about 111 km tall, not over the hours of low Sun at the cell, and it says nothing about fog or local weather. It enters no score. The grid is coarse (the service answers on a 1 degree grid, but polewards of 45 degrees neighbouring boxes along a latitude carry the same or nearly the same value in groups (CERES nested grid: about 2 degrees of longitude from 45 to 70, 4 from 70 to 80, 8 from 80 to 89)), so coast, sea and inland share one value. Winter values in the polar night may be too low, because satellites see cloud poorly over snow in the dark (a known weakness, not tested here); winter clear-sky hours are the least sure. No station cloud record was compared.

16,184 of the 16,184 scored records have a cloud figure (`cells_scored.json` → `cloud.pct_by_month`).

### Median clear share of the sky by month, where the summer hours are

| Target | Measured northern cells with ≥ 100 summer-half open hours | Jan | Feb | Mar | Apr | May | Jun | Jul | Aug | Sep | Oct | Nov | Dec |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Connecting ridge | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| Connecting Ridge Extension | 3 | 0.23 | 0.20 | 0.23 | 0.21 | 0.23 | 0.24 | 0.30 | 0.24 | 0.18 | 0.14 | 0.17 | 0.19 |
| Peak Near Shackleton | 6 | 0.45 | 0.33 | 0.31 | 0.25 | 0.24 | 0.24 | 0.30 | 0.26 | 0.18 | 0.14 | 0.35 | 0.47 |
| de Gerlache Rim 1 | 9 | 0.45 | 0.33 | 0.31 | 0.25 | 0.24 | 0.24 | 0.30 | 0.26 | 0.18 | 0.14 | 0.35 | 0.47 |
| de Gerlache Rim 2 | 63 | 0.47 | 0.40 | 0.36 | 0.32 | 0.28 | 0.30 | 0.32 | 0.29 | 0.20 | 0.14 | 0.31 | 0.49 |
| Faustini Rim A | 140 | 0.47 | 0.40 | 0.36 | 0.32 | 0.28 | 0.26 | 0.32 | 0.28 | 0.20 | 0.15 | 0.32 | 0.49 |
| Slater Plain | 489 | 0.48 | 0.40 | 0.36 | 0.32 | 0.27 | 0.23 | 0.30 | 0.27 | 0.18 | 0.16 | 0.36 | 0.48 |
| Haworth | 1,336 | 0.53 | 0.48 | 0.37 | 0.36 | 0.28 | 0.23 | 0.28 | 0.24 | 0.17 | 0.20 | 0.37 | 0.50 |
| Malapert | 3,145 | 0.55 | 0.49 | 0.38 | 0.38 | 0.29 | 0.22 | 0.27 | 0.22 | 0.17 | 0.22 | 0.40 | 0.51 |
| de Gerlache-Kocher Massif | 3,436 | 0.55 | 0.49 | 0.38 | 0.38 | 0.29 | 0.23 | 0.27 | 0.22 | 0.17 | 0.22 | 0.40 | 0.51 |
| Nobile Rim 1 | 4,014 | 0.55 | 0.50 | 0.39 | 0.39 | 0.29 | 0.23 | 0.27 | 0.22 | 0.17 | 0.23 | 0.40 | 0.51 |
| Mons Mouton | 4,028 | 0.55 | 0.50 | 0.39 | 0.39 | 0.29 | 0.23 | 0.27 | 0.22 | 0.17 | 0.23 | 0.40 | 0.51 |
| Mons Mouton Plateau | 5,591 | 0.55 | 0.50 | 0.40 | 0.40 | 0.29 | 0.23 | 0.27 | 0.24 | 0.18 | 0.23 | 0.40 | 0.51 |
| Amundsen Rim | 5,733 | 0.55 | 0.50 | 0.40 | 0.40 | 0.29 | 0.23 | 0.27 | 0.24 | 0.18 | 0.23 | 0.40 | 0.51 |
| Nobile Rim 2 | 6,114 | 0.55 | 0.50 | 0.40 | 0.40 | 0.29 | 0.23 | 0.27 | 0.24 | 0.18 | 0.23 | 0.40 | 0.51 |
| Peak near Cabeus B | 6,539 | 0.55 | 0.50 | 0.41 | 0.40 | 0.29 | 0.23 | 0.27 | 0.24 | 0.19 | 0.23 | 0.40 | 0.51 |

Source: `cloud_cells.json` → `cells.<id>.cloud_pct` (clear share = 1 − percent ÷ 100) for the measured northern cells whose `grazing_cells.json` → `targets.<target>.long_open_hours_summer` is at least 100; the median over those cells, month by month.

### The big-picture counts with and without the clear-sky factor

Measured northern cells with a horizon (14,833; 30 measured cells have none and are not counted): cells reaching 50 / 100 / 200 long-window hours.

| Target and period | Open hours: cells ≥ 50 / 100 / 200 h | Typical clear-sky hours: cells ≥ 50 / 100 / 200 h | Cells with unknown hours: open / clear-sky |
|---|---|---|---|
| Connecting ridge, winter half | 0 / 0 / 0 | 0 / 0 / 0 | 3 / 3 |
| Connecting ridge, summer half | 15 / 0 / 0 | 0 / 0 / 0 | 3 / 3 |
| Connecting ridge, year | 15 / 0 / 0 | 0 / 0 / 0 | 3 / 3 |
| Connecting Ridge Extension, winter half | 0 / 0 / 0 | 0 / 0 / 0 | 3 / 3 |
| Connecting Ridge Extension, summer half | 75 / 3 / 0 | 0 / 0 / 0 | 3 / 3 |
| Connecting Ridge Extension, year | 75 / 3 / 0 | 0 / 0 / 0 | 3 / 3 |
| Peak Near Shackleton, winter half | 0 / 0 / 0 | 0 / 0 / 0 | 3 / 3 |
| Peak Near Shackleton, summer half | 174 / 6 / 0 | 0 / 0 / 0 | 3 / 3 |
| Peak Near Shackleton, year | 174 / 6 / 0 | 0 / 0 / 0 | 3 / 3 |
| de Gerlache Rim 1, winter half | 0 / 0 / 0 | 0 / 0 / 0 | 3 / 3 |
| de Gerlache Rim 1, summer half | 266 / 9 / 0 | 0 / 0 / 0 | 3 / 3 |
| de Gerlache Rim 1, year | 270 / 9 / 0 | 0 / 0 / 0 | 3 / 3 |
| de Gerlache Rim 2, winter half | 0 / 0 / 0 | 0 / 0 / 0 | 3 / 3 |
| de Gerlache Rim 2, summer half | 872 / 63 / 0 | 0 / 0 / 0 | 3 / 3 |
| de Gerlache Rim 2, year | 885 / 63 / 0 | 0 / 0 / 0 | 3 / 3 |
| Faustini Rim A, winter half | 0 / 0 / 0 | 0 / 0 / 0 | 3 / 3 |
| Faustini Rim A, summer half | 1,985 / 140 / 0 | 1 / 0 / 0 | 3 / 3 |
| Faustini Rim A, year | 2,000 / 140 / 0 | 1 / 0 / 0 | 3 / 3 |
| Slater Plain, winter half | 24 / 0 / 0 | 0 / 0 / 0 | 3 / 3 |
| Slater Plain, summer half | 3,937 / 489 / 2 | 24 / 0 / 0 | 3 / 3 |
| Slater Plain, year | 4,001 / 504 / 2 | 24 / 0 / 0 | 3 / 3 |
| Haworth, winter half | 31 / 0 / 0 | 0 / 0 / 0 | 3 / 3 |
| Haworth, summer half | 4,706 / 1,336 / 6 | 62 / 0 / 0 | 3 / 3 |
| Haworth, year | 4,797 / 1,365 / 6 | 63 / 0 / 0 | 3 / 3 |
| Malapert, winter half | 36 / 12 / 0 | 0 / 0 / 0 | 3 / 3 |
| Malapert, summer half | 5,909 / 3,145 / 57 | 238 / 0 / 0 | 3 / 3 |
| Malapert, year | 6,016 / 3,201 / 64 | 240 / 0 / 0 | 3 / 3 |
| de Gerlache-Kocher Massif, winter half | 39 / 20 / 0 | 0 / 0 / 0 | 3 / 3 |
| de Gerlache-Kocher Massif, summer half | 6,173 / 3,436 / 86 | 292 / 0 / 0 | 3 / 3 |
| de Gerlache-Kocher Massif, year | 6,285 / 3,511 / 97 | 296 / 0 / 0 | 3 / 3 |
| Nobile Rim 1, winter half | 47 / 25 / 0 | 0 / 0 / 0 | 3 / 3 |
| Nobile Rim 1, summer half | 6,783 / 4,014 / 218 | 501 / 0 / 0 | 3 / 3 |
| Nobile Rim 1, year | 6,901 / 4,111 / 257 | 512 / 0 / 0 | 3 / 3 |
| Mons Mouton, winter half | 47 / 25 / 0 | 0 / 0 / 0 | 3 / 3 |
| Mons Mouton, summer half | 6,797 / 4,028 / 222 | 509 / 0 / 0 | 3 / 3 |
| Mons Mouton, year | 6,913 / 4,123 / 261 | 520 / 0 / 0 | 3 / 3 |
| Mons Mouton Plateau, winter half | 64 / 33 / 0 | 0 / 0 / 0 | 3 / 3 |
| Mons Mouton Plateau, summer half | 8,138 / 5,591 / 2,384 | 1,808 / 11 / 0 | 3 / 3 |
| Mons Mouton Plateau, year | 8,249 / 5,714 / 2,475 | 1,888 / 11 / 0 | 3 / 3 |
| Amundsen Rim, winter half | 67 / 34 / 0 | 0 / 0 / 0 | 3 / 3 |
| Amundsen Rim, summer half | 8,241 / 5,733 / 2,561 | 1,948 / 13 / 0 | 3 / 3 |
| Amundsen Rim, year | 8,353 / 5,846 / 2,651 | 2,014 / 13 / 0 | 3 / 3 |
| Nobile Rim 2, winter half | 75 / 34 / 3 | 0 / 0 / 0 | 3 / 3 |
| Nobile Rim 2, summer half | 8,550 / 6,114 / 2,936 | 2,270 / 17 / 0 | 3 / 3 |
| Nobile Rim 2, year | 8,649 / 6,255 / 3,048 | 2,343 / 20 / 0 | 3 / 3 |
| Peak near Cabeus B, winter half | 91 / 36 / 11 | 0 / 0 / 0 | 3 / 3 |
| Peak near Cabeus B, summer half | 8,925 / 6,539 / 3,264 | 2,649 / 32 / 0 | 3 / 3 |
| Peak near Cabeus B, year | 8,998 / 6,672 / 3,373 | 2,786 / 38 / 0 | 3 / 3 |

Source: `validation.json` → `big_picture_north.targets.<target>.long_open_hours_among_cells_with_a_horizon.<period>.<50|100|200>.cells` and `.long_open_hours_clear_among_cells_with_a_horizon.<period>`; the clear-sky figures per cell are `cells_scored.json` → `targets.<target>.long_open_hours_clear` and its `_winter` and `_summer` splits.

| Target | Share of open hours × bare km² left by the clear-sky factor: year | winter half | summer half | Cell-bins left out as unknown (open hours unknown, or hours without a cloud figure) |
|---|---|---|---|---|
| Connecting ridge | 23% | 18% | 23% | 20 |
| Connecting Ridge Extension | 23% | 19% | 23% | 21 |
| Peak Near Shackleton | 23% | 19% | 23% | 22 |
| de Gerlache Rim 1 | 23% | 19% | 23% | 23 |
| de Gerlache Rim 2 | 23% | 20% | 23% | 25 |
| Faustini Rim A | 23% | 20% | 23% | 28 |
| Slater Plain | 23% | 20% | 24% | 33 |
| Haworth | 23% | 20% | 23% | 34 |
| Malapert | 23% | 20% | 23% | 42 |
| de Gerlache-Kocher Massif | 23% | 20% | 23% | 45 |
| Nobile Rim 1 | 23% | 20% | 23% | 46 |
| Mons Mouton | 23% | 20% | 23% | 46 |
| Mons Mouton Plateau | 23% | 20% | 23% | 60 |
| Amundsen Rim | 23% | 20% | 23% | 60 |
| Nobile Rim 2 | 23% | 21% | 23% | 65 |
| Peak near Cabeus B | 23% | 21% | 23% | 69 |

Source: `validation.json` → `big_picture_north.targets.<target>.calendar_clear_hours_times_bare_km2` ÷ `.calendar_open_hours_times_bare_km2` (sums over the measured cells with a horizon).

### The top lighting sites with their typical clear-sky hours

The ranking does not use cloud. These are the top five lighting sites of (e) with the clear-sky column beside their hours, and then, for information, the three ranked sites with the most clear-sky hours (one per 50 km).

**Connecting Ridge:**

| Site | Cell centre (lat, lon) | Region | Bare | Long-window open hours a year | Typical clear-sky hours | Clear-sky ÷ open | Lighting score |
|---|---|---|---|---|---|---|---|
| lighting #1 | 68.95, 54.45 | Kola and north-west Russia | 1.00 | 36 | 9 | 25% | 0.421 |
| lighting #2 | 68.25, -96.15 | Arctic Canada | 0.96 | 36 | 11 | 30% | 0.412 |
| lighting #3 | 67.65, -76.65 | Arctic Canada | 0.88 | 37 | 11 | 30% | 0.402 |
| lighting #4 | 67.05, -158.85 | Alaska | 0.36 | 76 | 25 | 32% | 0.372 |
| lighting #5 | 80.35, 18.30 | Svalbard | 0.93 | 29 | 4 | 13% | 0.368 |
| most clear-sky hours #1 | 67.05, -158.85 | Alaska | 0.36 | 76 | 25 | 32% | 0.372 |
| most clear-sky hours #2 | 67.75, -112.05 | Arctic Canada | 0.30 | 62 | 19 | 31% | 0.305 |
| most clear-sky hours #3 | 67.75, -101.25 | Arctic Canada | 0.31 | 55 | 16 | 30% | 0.294 |

**Connecting Ridge Extension:**

| Site | Cell centre (lat, lon) | Region | Bare | Long-window open hours a year | Typical clear-sky hours | Clear-sky ÷ open | Lighting score |
|---|---|---|---|---|---|---|---|
| lighting #1 | 68.25, -96.15 | Arctic Canada | 0.96 | 59 | 17 | 29% | 0.533 |
| lighting #2 | 68.95, 54.45 | Kola and north-west Russia | 1.00 | 54 | 14 | 25% | 0.521 |
| lighting #3 | 68.35, -88.05 | Arctic Canada | 0.81 | 51 | 14 | 28% | 0.455 |
| lighting #4 | 68.35, -98.55 | Arctic Canada | 0.75 | 53 | 15 | 29% | 0.447 |
| lighting #5 | 80.35, 18.30 | Svalbard | 0.93 | 42 | 6 | 13% | 0.443 |
| most clear-sky hours #1 | 67.05, -158.85 | Alaska | 0.36 | 89 | 29 | 32% | 0.403 |
| most clear-sky hours #2 | 68.05, -103.95 | Arctic Canada | 0.32 | 101 | 28 | 27% | 0.401 |
| most clear-sky hours #3 | 67.75, -112.05 | Arctic Canada | 0.30 | 90 | 27 | 30% | 0.367 |

**Peak Near Shackleton:**

| Site | Cell centre (lat, lon) | Region | Bare | Long-window open hours a year | Typical clear-sky hours | Clear-sky ÷ open | Lighting score |
|---|---|---|---|---|---|---|---|
| lighting #1 | 68.25, -96.15 | Arctic Canada | 0.96 | 76 | 21 | 27% | 0.604 |
| lighting #2 | 68.95, 54.45 | Kola and north-west Russia | 1.00 | 66 | 17 | 25% | 0.577 |
| lighting #3 | 68.35, -98.55 | Arctic Canada | 0.75 | 76 | 20 | 27% | 0.532 |
| lighting #4 | 68.35, -88.05 | Arctic Canada | 0.81 | 66 | 18 | 27% | 0.515 |
| lighting #5 | 68.95, -115.35 | Arctic Canada | 0.83 | 57 | 18 | 33% | 0.486 |
| most clear-sky hours #1 | 67.05, -158.85 | Alaska | 0.36 | 96 | 31 | 32% | 0.417 |
| most clear-sky hours #2 | 68.05, -103.95 | Arctic Canada | 0.32 | 110 | 30 | 27% | 0.418 |
| most clear-sky hours #3 | 67.75, -112.05 | Arctic Canada | 0.30 | 97 | 29 | 30% | 0.381 |

**de Gerlache Rim 1:**

| Site | Cell centre (lat, lon) | Region | Bare | Long-window open hours a year | Typical clear-sky hours | Clear-sky ÷ open | Lighting score |
|---|---|---|---|---|---|---|---|
| lighting #1 | 68.25, -96.15 | Arctic Canada | 0.96 | 80 | 22 | 27% | 0.621 |
| lighting #2 | 68.95, 54.45 | Kola and north-west Russia | 1.00 | 76 | 19 | 25% | 0.614 |
| lighting #3 | 68.35, -98.55 | Arctic Canada | 0.75 | 80 | 22 | 27% | 0.546 |
| lighting #4 | 68.35, -88.05 | Arctic Canada | 0.81 | 69 | 19 | 27% | 0.528 |
| lighting #5 | 68.45, -114.75 | Arctic Canada | 0.62 | 87 | 28 | 32% | 0.519 |
| most clear-sky hours #1 | 67.05, -158.85 | Alaska | 0.36 | 100 | 32 | 33% | 0.425 |
| most clear-sky hours #2 | 68.05, -103.95 | Arctic Canada | 0.32 | 116 | 31 | 27% | 0.429 |
| most clear-sky hours #3 | 67.75, -112.05 | Arctic Canada | 0.30 | 101 | 30 | 30% | 0.389 |

**de Gerlache Rim 2:**

| Site | Cell centre (lat, lon) | Region | Bare | Long-window open hours a year | Typical clear-sky hours | Clear-sky ÷ open | Lighting score |
|---|---|---|---|---|---|---|---|
| lighting #1 | 68.95, 54.45 | Kola and north-west Russia | 1.00 | 128 | 30 | 24% | 0.799 |
| lighting #2 | 68.95, -115.65 | Arctic Canada | 0.87 | 109 | 35 | 32% | 0.686 |
| lighting #3 | 68.25, -96.15 | Arctic Canada | 0.96 | 94 | 25 | 27% | 0.669 |
| lighting #4 | 68.95, -100.65 | Arctic Canada | 0.93 | 85 | 26 | 31% | 0.627 |
| lighting #5 | 68.35, -98.55 | Arctic Canada | 0.75 | 94 | 25 | 27% | 0.593 |
| most clear-sky hours #1 | 67.05, -158.85 | Alaska | 0.36 | 114 | 37 | 32% | 0.455 |
| most clear-sky hours #2 | 68.85, -116.85 | Arctic Canada | 0.56 | 116 | 37 | 32% | 0.569 |
| most clear-sky hours #3 | 68.05, -103.95 | Arctic Canada | 0.32 | 134 | 36 | 27% | 0.461 |

**Faustini Rim A:**

| Site | Cell centre (lat, lon) | Region | Bare | Long-window open hours a year | Typical clear-sky hours | Clear-sky ÷ open | Lighting score |
|---|---|---|---|---|---|---|---|
| lighting #1 | 68.95, 54.45 | Kola and north-west Russia | 1.00 | 145 | 34 | 24% | 0.851 |
| lighting #2 | 68.95, -115.65 | Arctic Canada | 0.87 | 124 | 40 | 32% | 0.733 |
| lighting #3 | 68.25, -96.15 | Arctic Canada | 0.96 | 103 | 28 | 27% | 0.704 |
| lighting #4 | 68.95, -100.65 | Arctic Canada | 0.93 | 96 | 29 | 31% | 0.666 |
| lighting #5 | 80.35, 18.30 | Svalbard | 0.93 | 93 | 12 | 13% | 0.660 |
| most clear-sky hours #1 | 69.35, -119.85 | Arctic Canada | 0.39 | 125 | 43 | 34% | 0.493 |
| most clear-sky hours #2 | 68.85, -116.85 | Arctic Canada | 0.56 | 132 | 42 | 32% | 0.605 |
| most clear-sky hours #3 | 67.05, -158.85 | Alaska | 0.36 | 125 | 41 | 32% | 0.477 |

**Slater Plain:**

| Site | Cell centre (lat, lon) | Region | Bare | Long-window open hours a year | Typical clear-sky hours | Clear-sky ÷ open | Lighting score |
|---|---|---|---|---|---|---|---|
| lighting #1 | 68.95, 54.45 | Kola and north-west Russia | 1.00 | 180 | 42 | 23% | 0.947 |
| lighting #2 | 80.35, 18.30 | Svalbard | 0.93 | 150 | 19 | 13% | 0.837 |
| lighting #3 | 70.15, -116.85 | Arctic Canada | 0.98 | 137 | 46 | 34% | 0.820 |
| lighting #4 | 68.95, -115.65 | Arctic Canada | 0.87 | 155 | 49 | 32% | 0.818 |
| lighting #5 | 70.05, -124.35 | Arctic Canada | 0.99 | 124 | 41 | 33% | 0.785 |
| most clear-sky hours #1 | 69.65, -121.05 | Arctic Canada | 0.30 | 174 | 57 | 33% | 0.512 |
| most clear-sky hours #2 | 69.35, -119.85 | Arctic Canada | 0.39 | 163 | 56 | 34% | 0.561 |
| most clear-sky hours #3 | 69.95, 168.75 | Siberia and the Russian Far East | 0.66 | 168 | 55 | 33% | 0.745 |

**Haworth:**

| Site | Cell centre (lat, lon) | Region | Bare | Long-window open hours a year | Typical clear-sky hours | Clear-sky ÷ open | Lighting score |
|---|---|---|---|---|---|---|---|
| lighting #1 | 68.95, 54.45 | Kola and north-west Russia | 1.00 | 198 | 46 | 23% | 0.995 |
| lighting #2 | 80.25, 18.30 | Svalbard | 0.97 | 194 | 25 | 13% | 0.970 |
| lighting #3 | 70.25, -115.35 | Arctic Canada | 0.98 | 158 | 42 | 27% | 0.882 |
| lighting #4 | 70.15, -116.85 | Arctic Canada | 0.98 | 158 | 53 | 33% | 0.880 |
| lighting #5 | 68.95, -115.65 | Arctic Canada | 0.87 | 171 | 54 | 32% | 0.861 |
| most clear-sky hours #1 | 69.65, -121.05 | Arctic Canada | 0.30 | 197 | 64 | 33% | 0.544 |
| most clear-sky hours #2 | 69.95, 168.75 | Siberia and the Russian Far East | 0.66 | 191 | 63 | 33% | 0.796 |
| most clear-sky hours #3 | 69.35, -119.85 | Arctic Canada | 0.39 | 182 | 62 | 34% | 0.593 |

**Malapert Massif:**

| Site | Cell centre (lat, lon) | Region | Bare | Long-window open hours a year | Typical clear-sky hours | Clear-sky ÷ open | Lighting score |
|---|---|---|---|---|---|---|---|
| lighting #1 | 68.95, 54.45 | Kola and north-west Russia | 1.00 | 234 | 55 | 24% | 1.000 |
| lighting #2 | 80.15, 18.30 | Svalbard | 0.99 | 202 | 26 | 13% | 0.995 |
| lighting #3 | 70.25, -115.35 | Arctic Canada | 0.98 | 198 | 52 | 27% | 0.985 |
| lighting #4 | 70.15, -116.85 | Arctic Canada | 0.98 | 197 | 65 | 33% | 0.982 |
| lighting #5 | 70.05, -124.35 | Arctic Canada | 0.99 | 179 | 58 | 32% | 0.941 |
| most clear-sky hours #1 | 69.65, -121.05 | Arctic Canada | 0.30 | 238 | 77 | 32% | 0.548 |
| most clear-sky hours #2 | 69.95, 168.75 | Siberia and the Russian Far East | 0.66 | 234 | 77 | 33% | 0.814 |
| most clear-sky hours #3 | 69.35, -119.85 | Arctic Canada | 0.39 | 218 | 75 | 34% | 0.622 |

**de Gerlache-Kocher Massif:**

| Site | Cell centre (lat, lon) | Region | Bare | Long-window open hours a year | Typical clear-sky hours | Clear-sky ÷ open | Lighting score |
|---|---|---|---|---|---|---|---|
| lighting #1 | 68.95, 54.45 | Kola and north-west Russia | 1.00 | 241 | 57 | 24% | 1.000 |
| lighting #2 | 80.15, 18.30 | Svalbard | 0.99 | 210 | 28 | 13% | 0.995 |
| lighting #3 | 70.25, -115.35 | Arctic Canada | 0.98 | 206 | 55 | 27% | 0.991 |
| lighting #4 | 70.15, -116.85 | Arctic Canada | 0.98 | 205 | 67 | 33% | 0.990 |
| lighting #5 | 70.05, -124.35 | Arctic Canada | 0.99 | 186 | 60 | 32% | 0.961 |
| most clear-sky hours #1 | 69.65, -121.05 | Arctic Canada | 0.30 | 246 | 80 | 32% | 0.548 |
| most clear-sky hours #2 | 69.95, 168.75 | Siberia and the Russian Far East | 0.66 | 243 | 80 | 33% | 0.814 |
| most clear-sky hours #3 | 69.35, -119.85 | Arctic Canada | 0.39 | 226 | 77 | 34% | 0.622 |

**Nobile Rim 1:**

| Site | Cell centre (lat, lon) | Region | Bare | Long-window open hours a year | Typical clear-sky hours | Clear-sky ÷ open | Lighting score |
|---|---|---|---|---|---|---|---|
| lighting #1 | 68.95, 54.45 | Kola and north-west Russia | 1.00 | 260 | 61 | 24% | 1.000 |
| lighting #2 | 77.55, 22.75 | Svalbard | 1.00 | 228 | 37 | 16% | 1.000 |
| lighting #3 | 75.95, 141.25 | Siberia and the Russian Far East | 1.00 | 202 | 27 | 13% | 0.998 |
| lighting #4 | 70.05, -124.35 | Arctic Canada | 0.99 | 205 | 65 | 32% | 0.996 |
| lighting #5 | 80.15, 18.30 | Svalbard | 0.99 | 229 | 30 | 13% | 0.995 |
| most clear-sky hours #1 | 69.95, 168.75 | Siberia and the Russian Far East | 0.66 | 264 | 86 | 33% | 0.814 |
| most clear-sky hours #2 | 69.65, -121.05 | Arctic Canada | 0.30 | 268 | 86 | 32% | 0.548 |
| most clear-sky hours #3 | 69.35, -119.85 | Arctic Canada | 0.39 | 244 | 83 | 34% | 0.622 |

**Mons Mouton:**

| Site | Cell centre (lat, lon) | Region | Bare | Long-window open hours a year | Typical clear-sky hours | Clear-sky ÷ open | Lighting score |
|---|---|---|---|---|---|---|---|
| lighting #1 | 68.95, 54.45 | Kola and north-west Russia | 1.00 | 260 | 61 | 24% | 1.000 |
| lighting #2 | 77.55, 22.75 | Svalbard | 1.00 | 228 | 37 | 16% | 1.000 |
| lighting #3 | 75.85, 141.25 | Siberia and the Russian Far East | 1.00 | 200 | 27 | 13% | 0.999 |
| lighting #4 | 70.05, -124.35 | Arctic Canada | 0.99 | 205 | 65 | 32% | 0.996 |
| lighting #5 | 80.15, 18.30 | Svalbard | 0.99 | 230 | 30 | 13% | 0.995 |
| most clear-sky hours #1 | 69.65, -121.05 | Arctic Canada | 0.30 | 268 | 86 | 32% | 0.548 |
| most clear-sky hours #2 | 69.95, 168.75 | Siberia and the Russian Far East | 0.66 | 265 | 86 | 33% | 0.814 |
| most clear-sky hours #3 | 69.35, -119.85 | Arctic Canada | 0.39 | 245 | 83 | 34% | 0.622 |

**Mons Mouton Plateau:**

| Site | Cell centre (lat, lon) | Region | Bare | Long-window open hours a year | Typical clear-sky hours | Clear-sky ÷ open | Lighting score |
|---|---|---|---|---|---|---|---|
| lighting #1 | 75.15, 141.75 | Siberia and the Russian Far East | 1.00 | 365 | 47 | 13% | 1.000 |
| lighting #2 | 75.75, 141.75 | Siberia and the Russian Far East | 1.00 | 354 | 46 | 13% | 1.000 |
| lighting #3 | 74.95, 143.75 | Siberia and the Russian Far East | 1.00 | 343 | 55 | 16% | 1.000 |
| lighting #4 | 68.95, 54.45 | Kola and north-west Russia | 1.00 | 326 | 74 | 23% | 1.000 |
| lighting #5 | 77.55, 22.75 | Svalbard | 1.00 | 296 | 48 | 16% | 1.000 |
| most clear-sky hours #1 | 69.95, 168.75 | Siberia and the Russian Far East | 0.66 | 328 | 106 | 32% | 0.814 |
| most clear-sky hours #2 | 69.65, -121.05 | Arctic Canada | 0.30 | 330 | 105 | 32% | 0.548 |
| most clear-sky hours #3 | 69.35, -119.85 | Arctic Canada | 0.39 | 301 | 100 | 33% | 0.622 |

**Amundsen Rim:**

| Site | Cell centre (lat, lon) | Region | Bare | Long-window open hours a year | Typical clear-sky hours | Clear-sky ÷ open | Lighting score |
|---|---|---|---|---|---|---|---|
| lighting #1 | 74.95, 143.25 | Siberia and the Russian Far East | 1.00 | 383 | 60 | 16% | 1.000 |
| lighting #2 | 74.95, 141.25 | Siberia and the Russian Far East | 1.00 | 379 | 60 | 16% | 1.000 |
| lighting #3 | 75.35, 142.25 | Siberia and the Russian Far East | 1.00 | 365 | 47 | 13% | 1.000 |
| lighting #4 | 68.95, 54.45 | Kola and north-west Russia | 1.00 | 332 | 75 | 23% | 1.000 |
| lighting #5 | 77.55, 22.75 | Svalbard | 1.00 | 303 | 49 | 16% | 1.000 |
| most clear-sky hours #1 | 69.95, 168.75 | Siberia and the Russian Far East | 0.66 | 334 | 108 | 32% | 0.814 |
| most clear-sky hours #2 | 69.65, -121.05 | Arctic Canada | 0.30 | 336 | 106 | 32% | 0.548 |
| most clear-sky hours #3 | 69.35, -119.85 | Arctic Canada | 0.39 | 307 | 102 | 33% | 0.622 |

**Nobile Rim 2:**

| Site | Cell centre (lat, lon) | Region | Bare | Long-window open hours a year | Typical clear-sky hours | Clear-sky ÷ open | Lighting score |
|---|---|---|---|---|---|---|---|
| lighting #1 | 74.95, 143.25 | Siberia and the Russian Far East | 1.00 | 403 | 64 | 16% | 1.000 |
| lighting #2 | 74.95, 141.25 | Siberia and the Russian Far East | 1.00 | 398 | 63 | 16% | 1.000 |
| lighting #3 | 75.35, 142.25 | Siberia and the Russian Far East | 1.00 | 384 | 50 | 13% | 1.000 |
| lighting #4 | 68.95, 54.45 | Kola and north-west Russia | 1.00 | 351 | 78 | 22% | 1.000 |
| lighting #5 | 77.55, 22.75 | Svalbard | 1.00 | 321 | 52 | 16% | 1.000 |
| most clear-sky hours #1 | 69.95, 168.75 | Siberia and the Russian Far East | 0.66 | 353 | 114 | 32% | 0.814 |
| most clear-sky hours #2 | 69.65, -121.05 | Arctic Canada | 0.30 | 353 | 111 | 32% | 0.548 |
| most clear-sky hours #3 | 69.35, -119.85 | Arctic Canada | 0.39 | 322 | 106 | 33% | 0.622 |

**Peak near Cabeus B:**

| Site | Cell centre (lat, lon) | Region | Bare | Long-window open hours a year | Typical clear-sky hours | Clear-sky ÷ open | Lighting score |
|---|---|---|---|---|---|---|---|
| lighting #1 | 74.95, 143.25 | Siberia and the Russian Far East | 1.00 | 425 | 67 | 16% | 1.000 |
| lighting #2 | 74.95, 141.25 | Siberia and the Russian Far East | 1.00 | 420 | 67 | 16% | 1.000 |
| lighting #3 | 75.35, 142.25 | Siberia and the Russian Far East | 1.00 | 405 | 53 | 13% | 1.000 |
| lighting #4 | 68.95, 54.45 | Kola and north-west Russia | 1.00 | 376 | 83 | 22% | 1.000 |
| lighting #5 | 77.55, 22.75 | Svalbard | 1.00 | 341 | 56 | 16% | 1.000 |
| most clear-sky hours #1 | 69.95, 168.75 | Siberia and the Russian Far East | 0.66 | 375 | 120 | 32% | 0.814 |
| most clear-sky hours #2 | 69.65, -121.05 | Arctic Canada | 0.30 | 373 | 117 | 31% | 0.548 |
| most clear-sky hours #3 | 69.35, -119.85 | Arctic Canada | 0.39 | 341 | 111 | 33% | 0.622 |

Source: `cells_scored.json` → ranked northern records, `targets.<target>.long_open_hours`, `.long_open_hours_clear`, `.goals.lighting`.

## (k) Version 2 against version 3

Version 2 values are read from the kept files `validation_v2.json`, `cells_scored_v2.json` and the `_bin_median` thresholds of `latitude_profile.json`; version 3 values from the present files. The decisions are those of the version 3 plan: **12** long spells counted per day instead of per ten-day bin; **13** measured cells use the snow maps as they read; **15** a terrain horizon for every cell that has elevation tiles on disk, not only for 1,690 candidates; **17** the cloud column (moves no figure below).

### Lowest latitude with a 2 h spell

| Target and hemisphere | Version 2 (bin median) | Version 3 (per day) | Change | Decision |
|---|---|---|---|---|
| Connecting ridge, north | 64.85° | 64.80° | -0.05 | 12 |
| Connecting ridge, south | 64.85° | 64.80° | -0.05 | 12 |
| Connecting Ridge Extension, north | 64.40° | 64.35° | -0.05 | 12 |
| Connecting Ridge Extension, south | 64.40° | 64.35° | -0.05 | 12 |
| Peak Near Shackleton, north | 64.15° | 64.10° | -0.05 | 12 |
| Peak Near Shackleton, south | 64.15° | 64.10° | -0.05 | 12 |
| de Gerlache Rim 1, north | 64.00° | 64.00° | same | 12 |
| de Gerlache Rim 1, south | 64.00° | 64.00° | same | 12 |
| de Gerlache Rim 2, north | 63.50° | 63.50° | same | 12 |
| de Gerlache Rim 2, south | 63.50° | 63.50° | same | 12 |
| Faustini Rim A, north | 63.15° | 63.10° | -0.05 | 12 |
| Faustini Rim A, south | 63.15° | 63.10° | -0.05 | 12 |
| Slater Plain, north | 62.25° | 62.20° | -0.05 | 12 |
| Slater Plain, south | 62.25° | 62.20° | -0.05 | 12 |
| Haworth, north | 61.75° | 61.70° | -0.05 | 12 |
| Haworth, south | 61.70° | 61.70° | same | 12 |
| Malapert, north | 60.70° | 60.65° | -0.05 | 12 |
| Malapert, south | 60.70° | 60.65° | -0.05 | 12 |
| de Gerlache-Kocher Massif, north | 60.45° | 60.45° | same | 12 |
| de Gerlache-Kocher Massif, south | 60.45° | 60.45° | same | 12 |
| Nobile Rim 1, north | 59.90° | 59.90° | same | 12 |
| Nobile Rim 1, south | 59.90° | 59.90° | same | 12 |
| Mons Mouton, north | 59.90° | 59.90° | same | 12 |
| Mons Mouton, south | 59.90° | 59.90° | same | 12 |
| Mons Mouton Plateau, north | 58.20° | 58.25° | +0.05 | 12 |
| Mons Mouton Plateau, south | 58.20° | 58.25° | +0.05 | 12 |
| Amundsen Rim, north | 58.10° | 58.10° | same | 12 |
| Amundsen Rim, south | 58.10° | 58.10° | same | 12 |
| Nobile Rim 2, north | 57.65° | 57.65° | same | 12 |
| Nobile Rim 2, south | 57.65° | 57.65° | same | 12 |
| Peak near Cabeus B, north | 57.15° | 57.15° | same | 12 |
| Peak near Cabeus B, south | 57.15° | 57.15° | same | 12 |

Source: `latitude_profile.json` → `thresholds.<target>.<N|S>.lowest_lat_with_long_window_bin_median["2"]` and `.lowest_lat_with_long_window["2"]`.

### Measured northern cells reaching 50, 100 and 200 long-window snow-free hours (flat horizon)

| Target, period and level | Version 2 | Version 3 | Change | Decision |
|---|---|---|---|---|
| Connecting ridge, winter half, ≥ 50 h | 0 | 0 | same | 12 (13 moves a count by at most 1) |
| Connecting ridge, winter half, ≥ 100 h | 0 | 0 | same | 12 (13 moves a count by at most 1) |
| Connecting ridge, winter half, ≥ 200 h | 0 | 0 | same | 12 (13 moves a count by at most 1) |
| Connecting ridge, summer half, ≥ 50 h | 476 | 285 | -191 | 12 (13 moves a count by at most 1) |
| Connecting ridge, summer half, ≥ 100 h | 6 | 2 | -4 | 12 (13 moves a count by at most 1) |
| Connecting ridge, summer half, ≥ 200 h | 0 | 0 | same | 12 (13 moves a count by at most 1) |
| Malapert, winter half, ≥ 50 h | 74 | 71 | -3 | 12 (13 moves a count by at most 1) |
| Malapert, winter half, ≥ 100 h | 10 | 15 | +5 | 12 (13 moves a count by at most 1) |
| Malapert, winter half, ≥ 200 h | 0 | 0 | same | 12 (13 moves a count by at most 1) |
| Malapert, summer half, ≥ 50 h | 9,605 | 9,584 | -21 | 12 (13 moves a count by at most 1) |
| Malapert, summer half, ≥ 100 h | 7,324 | 7,361 | +37 | 12 (13 moves a count by at most 1) |
| Malapert, summer half, ≥ 200 h | 545 | 503 | -42 | 12 (13 moves a count by at most 1) |
| Mons Mouton, winter half, ≥ 50 h | 105 | 102 | -3 | 12 (13 moves a count by at most 1) |
| Mons Mouton, winter half, ≥ 100 h | 27 | 28 | +1 | 12 (13 moves a count by at most 1) |
| Mons Mouton, winter half, ≥ 200 h | 0 | 0 | same | 12 (13 moves a count by at most 1) |
| Mons Mouton, summer half, ≥ 50 h | 10,048 | 9,984 | -64 | 12 (13 moves a count by at most 1) |
| Mons Mouton, summer half, ≥ 100 h | 8,207 | 8,192 | -15 | 12 (13 moves a count by at most 1) |
| Mons Mouton, summer half, ≥ 200 h | 1,562 | 1,339 | -223 | 12 (13 moves a count by at most 1) |
| Nobile Rim 2, winter half, ≥ 50 h | 214 | 193 | -21 | 12 (13 moves a count by at most 1) |
| Nobile Rim 2, winter half, ≥ 100 h | 40 | 40 | same | 12 (13 moves a count by at most 1) |
| Nobile Rim 2, winter half, ≥ 200 h | 3 | 4 | +1 | 12 (13 moves a count by at most 1) |
| Nobile Rim 2, summer half, ≥ 50 h | 11,234 | 11,190 | -44 | 12 (13 moves a count by at most 1) |
| Nobile Rim 2, summer half, ≥ 100 h | 9,897 | 9,849 | -48 | 12 (13 moves a count by at most 1) |
| Nobile Rim 2, summer half, ≥ 200 h | 6,244 | 6,231 | -13 | 12 (13 moves a count by at most 1) |

Source: `validation_v2.json` and `validation.json` → `big_picture_north.targets.<target>.long_snow_free_hours.<winter_half|summer_half>.<50|100|200>.cells`. That decision 13 moves a half-year count by at most one cell is from the build's own three-way comparison (before / decision 12 only / after); it was not recomputed here.

### Winter-half share of the long-window snow-free hours × bare km²

| Target | Version 2 | Version 3 | Change | Decision |
|---|---|---|---|---|
| Connecting ridge | 0.36% | 0.56% | +0.20 points | 12 and 13 |
| Malapert | 1.57% | 1.64% | +0.07 points | 12 and 13 |
| Mons Mouton | 1.76% | 1.81% | +0.05 points | 12 and 13 |
| Nobile Rim 2 | 2.13% | 2.16% | +0.03 points | 12 and 13 |

Source: `validation_v2.json` and `validation.json` → `big_picture_north.targets.<target>.calendar_hours_times_bare_km2`, winter bins over all bins.

### Share of long-window hours the terrain leaves (median)

| Target and side | Version 2: blind sample | Version 3: the same blind sample | Version 3: every cell with a horizon | Decision |
|---|---|---|---|---|
| Connecting ridge, north | 0.339 (n 192) | 0.292 (n 220) | 0.286 (n 10,427) | 12 (sample); 15 (all cells) |
| Connecting ridge, south | 0.138 (n 82) | 0.147 (n 104) | 0.148 (n 885) | 12 (sample); 15 (all cells) |
| Malapert, north | 0.537 (n 238) | 0.535 (n 239) | 0.513 (n 11,330) | 12 (sample); 15 (all cells) |
| Malapert, south | 0.393 (n 133) | 0.397 (n 136) | 0.361 (n 1,118) | 12 (sample); 15 (all cells) |
| Mons Mouton, north | 0.561 (n 245) | 0.561 (n 248) | 0.535 (n 11,719) | 12 (sample); 15 (all cells) |
| Mons Mouton, south | 0.435 (n 138) | 0.437 (n 139) | 0.400 (n 1,130) | 12 (sample); 15 (all cells) |
| Nobile Rim 2, north | 0.593 (n 263) | 0.593 (n 263) | 0.582 (n 12,814) | 12 (sample); 15 (all cells) |
| Nobile Rim 2, south | 0.488 (n 144) | 0.491 (n 144) | 0.459 (n 1,190) | 12 (sample); 15 (all cells) |

Source: version 2 from `cells_scored_v2.json` (the sample cells of `candidates.json`: `long_open_hours` ÷ `long_snow_free_hours`, south `long_summer_rock_open_hours` ÷ `long_summer_rock_hours`); version 3 from `validation.json` → `terrain_share_left`. The sample is the same 300 + 150 cells in both versions; n is the number of them with a horizon and such hours.

### The named sites, Malapert, long-window hours a year

| Site | Snow odds | Version 2: flat / snow-free / open | Version 3: flat / snow-free / open | Decision |
|---|---|---|---|---|
| Qaqortorsuaq anorthosite, Greenland | measured | 488.0 / 157.7 / 40.0 | 503.7 / 170.9 / 43.4 | 12 |
| Fiskenaesset anorthosite, Greenland | measured | 259.7 / 0.0 / 0.0 | 255.6 / 0.0 / 0.0 | 12 |
| Lofoten anorthosite (Nusfjord), Norway | doubtful | 527.2 / 334.2 / 66.9 | 548.9 / 351.0 / 70.6 | 12 |
| Bergen Arcs anorthosite, Norway | measured | 0.0 / 0.0 / 0.0 | 0.0 / 0.0 / 0.0 | no change |
| Bear Island, Norway | doubtful | 527.1 / 191.2 / 126.6 | 520.0 / 184.5 / 123.7 | 12 |
| Jan Mayen, Norway | doubtful | 588.0 / 205.8 / 81.0 | 591.6 / 197.0 / 79.5 | 12 |
| Reykjanes, Iceland | measured | 295.0 / 135.0 / 117.3 | 275.7 / 135.3 / 117.5 | 12 and 13 |
| Skeidararsandur, Iceland | measured | 294.1 / 83.5 / 76.5 | 278.6 / 75.7 / 69.4 | 12 |
| Myrdalssandur sand plain, Iceland | measured | 258.5 / 92.2 / 91.6 | 263.0 / 98.4 / 97.7 | 12 |
| Haughton crater, Devon Island, Canada | measured | 523.5 / 149.9 / 100.3 | 535.9 / 146.7 / 102.0 | 12 |
| Longyearbyen, Svalbard | measured | 783.5 / 81.0 / 15.9 | 726.6 / 75.3 / 14.0 | 12 |
| Kangerlussuaq, Greenland | measured | 502.3 / 230.3 / 32.5 | 516.5 / 226.4 / 31.8 | 12 |
| Bunger Hills | unmeasured | 180.9 / n/a / 67.3 | 185.3 / n/a / 69.1 | 12 |
| Vestfold Hills | unmeasured | 281.1 / n/a / 151.4 | 287.9 / n/a / 154.3 | 12 |
| Larsemann Hills | unmeasured | 305.2 / n/a / 115.4 | 288.6 / n/a / 110.2 | 12 |
| Schirmacher Oasis | unmeasured | 264.7 / n/a / 98.4 | 271.5 / n/a / 100.3 | 12 |
| Lake Untersee and the Eliseev anorthosite massif | unmeasured | 235.7 / n/a / 10.0 | 253.6 / n/a / 11.1 | 12 |
| McMurdo Dry Valleys | unmeasured | 156.3 / n/a / 7.6 | 156.3 / n/a / 7.6 | no change |
| Windmill Islands | unmeasured | 180.9 / n/a / 83.7 | 185.3 / n/a / 85.9 | 12 |
| Syowa and the Soya Coast | unmeasured | 271.4 / n/a / 221.8 | 289.0 / n/a / 233.3 | 12 |
| Fildes Peninsula | unmeasured | 0.0 / n/a / 0.0 | 0.0 / n/a / 0.0 | no change |
| Deception Island | unmeasured | 0.0 / n/a / 0.0 | 0.0 / n/a / 0.0 | no change |
| Ulu Peninsula, James Ross Island | unmeasured | 0.0 / n/a / 0.0 | 0.0 / n/a / 0.0 | no change |
| Seymour Island | unmeasured | 0.0 / n/a / 0.0 | 0.0 / n/a / 0.0 | no change |
| Rothera Point | unmeasured | 285.2 / n/a / 160.1 | 271.4 / n/a / 153.8 | 12 |
| Jutulsessen at Troll | unmeasured | 200.5 / n/a / 68.6 | 188.6 / n/a / 65.7 | 12 |
| Northern Foothills, Terra Nova Bay | unmeasured | 146.0 / n/a / 91.8 | 139.4 / n/a / 90.2 | 12 |

Source: `validation_v2.json` and `validation.json` → `named_sites.sites[].targets.malapert.<flat|snow_free|open>.long.year`; southern sites `long_summer_rock_hours` and `long_summer_rock_open_hours` (rock season; snow not measured). The horizons of these cells are the same in both versions.

### The first three lighting sites per target (north)

| Target and place | Version 2: cell centre (region); open hours; score | Version 3 | What moved it |
|---|---|---|---|
| Connecting ridge #1 | 68.25, -96.15 (Arctic Canada); 50 h; score 0.488 | 68.95, 54.45 (Kola and north-west Russia); 36 h; score 0.421 | 12, 13: both cells had a horizon in version 2 |
| Connecting ridge #2 | 68.35, -88.05 (Arctic Canada); 45 h; score 0.425 | 68.25, -96.15 (Arctic Canada); 36 h; score 0.412 | 12, 13: both cells had a horizon in version 2 |
| Connecting ridge #3 | 67.75, -76.65 (Arctic Canada); 45 h; score 0.422 | 67.65, -76.65 (Arctic Canada); 37 h; score 0.402 | 12, 13: both cells had a horizon in version 2 |
| Malapert #1 | 68.95, 54.45 (Kola and north-west Russia); 243 h; score 1.000 | 68.95, 54.45 (Kola and north-west Russia); 234 h; score 1.000 | same cell (12, 13 move its hours) |
| Malapert #2 | 80.15, 18.30 (Svalbard); 203 h; score 0.995 | 80.15, 18.30 (Svalbard); 202 h; score 0.995 | same cell (12, 13 move its hours) |
| Malapert #3 | 70.15, -116.85 (Arctic Canada); 184 h; score 0.950 | 70.25, -115.35 (Arctic Canada); 198 h; score 0.985 | 12, 13: both cells had a horizon in version 2 |
| Mons Mouton #1 | 68.95, 54.45 (Kola and north-west Russia); 260 h; score 1.000 | 68.95, 54.45 (Kola and north-west Russia); 260 h; score 1.000 | same cell (12, 13 move its hours) |
| Mons Mouton #2 | 77.55, 22.75 (Svalbard); 231 h; score 1.000 | 77.55, 22.75 (Svalbard); 228 h; score 1.000 | same cell (12, 13 move its hours) |
| Mons Mouton #3 | 74.95, 141.25 (Siberia and the Russian Far East); 199 h; score 0.998 | 75.85, 141.25 (Siberia and the Russian Far East); 200 h; score 0.999 | 12, 13: both cells had a horizon in version 2 |
| Nobile Rim 2 #1 | 74.95, 143.25 (Siberia and the Russian Far East); 405 h; score 1.000 | 74.95, 143.25 (Siberia and the Russian Far East); 403 h; score 1.000 | same cell (12, 13 move its hours) |
| Nobile Rim 2 #2 | 74.95, 141.25 (Siberia and the Russian Far East); 401 h; score 1.000 | 74.95, 141.25 (Siberia and the Russian Far East); 398 h; score 1.000 | same cell (12, 13 move its hours) |
| Nobile Rim 2 #3 | 75.35, 142.25 (Siberia and the Russian Far East); 388 h; score 1.000 | 75.35, 142.25 (Siberia and the Russian Far East); 384 h; score 1.000 | same cell (12, 13 move its hours) |

Source: `cells_scored_v2.json` (1,690 records, 1,085 ranked in the north) and `cells_scored.json` (16,184 records, 10,837 ranked in the north), each ranked here by lighting score, then hours, one site per 50 km. The last column is by elimination (which of the decisions could act on the two cells: a cell that had no horizon in version 2 can only have entered through 15; otherwise 12 and 13 are left), not from running the chain with one decision at a time.

## (l) Winter on small bare patches

The search keeps only cells whose land is at least 15% bare. Of the 146,561 northern land squares of the land-cover file, 131,628 are below that screen; 24,067 of them still hold some bare ground, and 16,013 hold at least 1 km² of it. Their long-window hours in the winter half (28 September to 31 March) on snow-free ground were worked out with the pipeline's own functions, and a terrain horizon for the squares with the most hours. These squares are in no other section and in no ranking.

| Target | Hidden by the screen: squares with ≥ 100 winter-half hours, flat horizon (regions) | the same after terrain | Cells that pass the screen, flat horizon | the same after terrain |
|---|---|---|---|---|
| Connecting Ridge | 0 | 0 | 0 | 0 |
| Connecting Ridge Extension | 0 | 0 | 0 | 0 |
| Peak Near Shackleton | 0 | 0 | 0 | 0 |
| de Gerlache Rim 1 | 0 | 0 | 0 | 0 |
| de Gerlache Rim 2 | 0 | 0 | 0 | 0 |
| Faustini Rim A | 0 | 0 | 0 | 0 |
| Slater Plain | 0 | 0 | 0 | 0 |
| Haworth | 2 (Iceland 2) | 0 | 1 (Iceland 1) | 0 |
| Malapert Massif | 15 (Iceland 13, Faroe Islands 1, Norway: More og Romsdal 1) | 8 (Iceland 8) | 15 (Iceland 15) | 12 (Iceland 12) |
| de Gerlache-Kocher Massif | 17 (Iceland 15, Faroe Islands 1, Norway: More og Romsdal 1) | 8 (Iceland 8) | 22 (Iceland 22) | 20 (Iceland 20) |
| Nobile Rim 1 | 21 (Iceland 19, Faroe Islands 1, Norway: More og Romsdal 1) | 11 (Iceland 11) | 28 (Iceland 28) | 25 (Iceland 25) |
| Mons Mouton | 21 (Iceland 19, Faroe Islands 1, Norway: More og Romsdal 1) | 11 (Iceland 11) | 28 (Iceland 28) | 25 (Iceland 25) |
| Mons Mouton Plateau | 52 (Iceland 42, Norway: More og Romsdal 5, Norway: Vestland 3, Faroe Islands 1, Norway: Trondelag 1) | 18 (Iceland 18) | 35 (Iceland 35) | 33 (Iceland 33) |
| Amundsen Rim | 54 (Iceland 44, Norway: More og Romsdal 5, Norway: Vestland 3, Faroe Islands 1, Norway: Trondelag 1) | 20 (Iceland 20) | 35 (Iceland 35) | 34 (Iceland 34) |
| Nobile Rim 2 | 64 (Iceland 50, Norway: More og Romsdal 6, Norway: Vestland 5, Faroe Islands 1, Norway: Oslofjord and the south-east 1, Norway: Trondelag 1) | 24 (Iceland 24) | 40 (Iceland 39, Svalbard 1) | 34 (Iceland 34) |
| Peak near Cabeus B | 83 (Iceland 62, Norway: More og Romsdal 9, Norway: Vestland 5, Norway: Nordland 2, Faroe Islands 1, Norway: Oslofjord and the south-east 1, Norway: Rogaland 1, Norway: Trondelag 1, Novaya Zemlya 1) | 30 (Iceland 29, Norway: Oslofjord and the south-east 1) | 49 (Iceland 46, Svalbard 2, Novaya Zemlya 1) | 36 (Iceland 36) |

Source: `winter_leads.json` → `targets.<target>.counts_by_region["100"]`, `counts_by_region_after_terrain`, `screened_counts_by_region`, `screened_counts_by_region_after_terrain` (measured snow odds; squares with at least 1 km² of bare ground; after terrain only squares that have a horizon).

The ten best leads for Peak near Cabeus B (the highest limit), by winter-half hours after terrain:

| # | Centre (lat, lon) | Region | Winter-half hours after terrain | on snow-free ground, flat horizon | Bare km² (samples) | Snow land pixels | Best ten-day periods |
|---|---|---|---|---|---|---|---|
| 1 | 63.95, -22.70 | Iceland | 229.2 | 245.3 | 4.93 (13) | 4 of 9 | 17 Nov (52 h), 7 Nov (48 h), 27 Nov (39 h) |
| 2 | 63.65, -20.30 | Iceland | 224.9 | 226.9 | 1.53 (4) | 6 of 9 | 17 Nov (48 h), 7 Nov (42 h), 27 Nov (38 h) |
| 3 | 63.85, -20.90 | Iceland | 218.0 | 218.7 | 1.14 (3) | 8 of 9 | 17 Nov (47 h), 7 Nov (43 h), 27 Nov (37 h) |
| 4 | 63.75, -20.50 | Iceland | 215.0 | 217.0 | 1.53 (4) | 5 of 9 | 17 Nov (50 h), 7 Nov (43 h), 27 Nov (38 h) |
| 5 | 63.95, -22.50 | Iceland | 214.9 | 246.6 | 2.28 (6) | 6 of 9 | 17 Nov (51 h), 7 Nov (48 h), 27 Nov (40 h) |
| 6 | 63.65, -20.10 | Iceland | 203.9 | 213.3 | 1.15 (3) | 9 of 9 | 17 Nov (44 h), 7 Nov (41 h), 27 Nov (36 h) |
| 7 | 63.85, -20.70 | Iceland | 194.2 | 199.3 | 1.14 (3) | 6 of 9 | 17 Nov (46 h), 7 Nov (41 h), 27 Nov (34 h) |
| 8 | 64.65, -22.35 | Iceland | 181.4 | 189.1 | 1.11 (3) | 2 of 9 | 7 Nov (49 h), 17 Nov (47 h), 27 Nov (35 h) |
| 9 | 64.75, -22.35 | Iceland | 170.2 | 178.4 | 2.21 (6) | 5 of 9 | 7 Nov (52 h), 17 Nov (46 h), 27 Nov (29 h) |
| 10 | 63.65, -18.30 | Iceland | 170.1 | 173.8 | 13.42 (35) | 9 of 9 | 17 Nov (38 h), 7 Nov (36 h), 27 Nov (22 h) |

Source: `winter_leads.json` → `targets.peak-near-cabeus-b.leads` with `at_main_floor` true and `snow.status` measured (`winter_hours_after_terrain`, `winter_hours_snow_free`, `bare_km2`, `bare_samples`, `snow.land_pixels`, `best_ten_day_periods`).

Cautions the file carries (`meta.warnings`):

- Snow-free odds at a coast rest on few land pixels of the 4 km snow maps: see snow.land_pixels of snow.block_pixels for each lead. Squares with snow status 'doubtful' use the lower odds of the stale-flag rule and are counted apart.
- No cloud is taken into account. The Atlantic rim is very cloudy in winter; these are hours of Sun geometry on ground that is probably free of snow, not hours of visible Sun.
- WorldCover's bare class at a coast can be beach, tidal flat, rock, a quarry or other worked ground. What the bare ground of a lead is was not looked at.
- The land-cover file is a sample: one 10 m pixel about every 900 m (12 samples per 0.1 degree). South of 64.5 N one bare sample stands for about 0.4 km2, so the 0.25 km2 floor means one bare sample, 1 km2 means three or more and 3 km2 seven or more; bare_km2 of a lead with few samples (bare_samples) is uncertain by about its own size, and a square with bare ground between the samples reads as having none.
- Squares with less than 20 percent land were left out when the land-cover file was built, so small islands and skerries are not here at all.
- The terrain horizon was computed only for the squares named in meta.horizon; winter_hours_after_terrain is null elsewhere and the counts after terrain cover only squares that have a horizon.
- Hours after terrain are an average over all the land of a square (the share of its land that sees the Sun), not over its bare ground. A bare summit or headland can see more of a low southern Sun than that average, a quarry or beach under a hill less.
- The winter half runs from 28 September to 31 March. North of about 67 N the hours counted here fall in October and March, not in midwinter.
- Region names come from rough latitude and longitude boxes (first match wins); a square near a border can carry its neighbour's name.
- Hours are for a 365-day year with standard refraction, a 2 h minimum spell and 1-minute steps, as in the pipeline; the limits listed in section (i) of RESULTS.md apply here too.
- Not computed for these squares: cloud, what the bare ground is (beach, tidal flat, rock, quarry), access, ownership, permits, terrain for squares outside meta.horizon, squares with less than 20 percent land, slope and the other scores of cells_scored.json (`meta.not_computed`).

## (m) How reachable the best areas are

The straight-line distance from the centre of each area to the nearest runway with scheduled flights (`access_cells.json`, from OurAirports, airports.csv, downloaded 2026-11-15T01:54:18Z, public domain). Counted over the ranked northern areas with at least 100 long-window open hours a year.

| Target | Ranked northern areas with ≥ 100 h | of them within 50 km / 100 km / 200 km of a scheduled-service airfield | Most long-window open hours of any ranked area |
|---|---|---|---|
| Connecting Ridge | 0 | 0 / 0 / 0 | 76 |
| Connecting Ridge Extension | 1 | 0 / 0 / 1 | 101 |
| Peak Near Shackleton | 2 | 0 / 0 / 2 | 110 |
| de Gerlache Rim 1 | 4 | 0 / 0 / 4 | 116 |
| de Gerlache Rim 2 | 40 | 1 / 12 / 38 | 134 |
| Faustini Rim A | 88 | 7 / 32 / 86 | 147 |
| Slater Plain | 350 | 29 / 118 / 296 | 180 |
| Haworth | 1,040 | 52 / 161 / 460 | 200 |
| Malapert Massif | 2,528 | 107 / 324 / 1,066 | 239 |
| de Gerlache-Kocher Massif | 2,777 | 114 / 356 / 1,176 | 247 |
| Nobile Rim 1 | 3,255 | 131 / 418 / 1,383 | 273 |
| Mons Mouton | 3,265 | 133 / 421 / 1,388 | 274 |
| Mons Mouton Plateau | 4,549 | 190 / 623 / 1,936 | 385 |
| Amundsen Rim | 4,656 | 198 / 646 / 1,979 | 391 |
| Nobile Rim 2 | 4,966 | 213 / 711 / 2,111 | 409 |
| Peak near Cabeus B | 5,294 | 235 / 764 / 2,280 | 428 |

Source: `cells_scored.json` → `ranked`, `ranking`, `targets.<target>.long_open_hours`; `access_cells.json` → `cells.<id>.nearest_scheduled.km`. The southern areas are left out: no listed Antarctic runway has scheduled service.

Best reachable areas: the three best lighting areas per target within 100 km of a scheduled-service airfield, one per 50 km:

| Target | # | Centre (lat, lon) | Region | Lighting score | Long-window open hours a year | Nearest scheduled-service airfield |
|---|---|---|---|---|---|---|
| de Gerlache Rim 2 | 1 | 68.45, -114.75 | Arctic Canada | 0.568 | 104 | Kugluktuk Airport (72.3 km) |
| de Gerlache Rim 2 | 2 | 67.05, -158.85 | Alaska | 0.455 | 114 | Ambler Airport (43.5 km) |
| Faustini Rim A | 1 | 68.25, -96.15 | Arctic Canada | 0.704 | 103 | Gjoa Haven Airport (44.6 km) |
| Faustini Rim A | 2 | 69.25, -88.95 | Arctic Canada | 0.613 | 101 | Kugaaruk Airport (86.5 km) |
| Faustini Rim A | 3 | 68.45, -114.75 | Arctic Canada | 0.601 | 117 | Kugluktuk Airport (72.3 km) |
| Slater Plain | 1 | 70.15, -116.85 | Arctic Canada | 0.820 | 137 | Ulukhaktok Holman Airport (76.9 km) |
| Slater Plain | 2 | 70.05, -124.35 | Arctic Canada | 0.785 | 124 | Paulatuk (Nora Aliqatchialuk Ruben) Airport (77.4 km) |
| Slater Plain | 3 | 68.25, -96.15 | Arctic Canada | 0.774 | 125 | Gjoa Haven Airport (44.6 km) |
| Haworth | 1 | 70.15, -116.85 | Arctic Canada | 0.880 | 158 | Ulukhaktok Holman Airport (76.9 km) |
| Haworth | 2 | 70.05, -124.35 | Arctic Canada | 0.844 | 144 | Paulatuk (Nora Aliqatchialuk Ruben) Airport (77.4 km) |
| Haworth | 3 | 68.25, -96.15 | Arctic Canada | 0.812 | 138 | Gjoa Haven Airport (44.6 km) |
| Malapert Massif | 1 | 70.15, -116.85 | Arctic Canada | 0.982 | 197 | Ulukhaktok Holman Airport (76.9 km) |
| Malapert Massif | 2 | 70.05, -124.35 | Arctic Canada | 0.941 | 179 | Paulatuk (Nora Aliqatchialuk Ruben) Airport (77.4 km) |
| Malapert Massif | 3 | 70.65, 30.15 | Norway, Sweden or Finland | 0.928 | 205 | Båtsfjord Airport (17.8 km) |
| de Gerlache-Kocher Massif | 1 | 70.15, -116.85 | Arctic Canada | 0.990 | 205 | Ulukhaktok Holman Airport (76.9 km) |
| de Gerlache-Kocher Massif | 2 | 70.05, -124.35 | Arctic Canada | 0.961 | 186 | Paulatuk (Nora Aliqatchialuk Ruben) Airport (77.4 km) |
| de Gerlache-Kocher Massif | 3 | 70.65, 30.15 | Norway, Sweden or Finland | 0.928 | 214 | Båtsfjord Airport (17.8 km) |
| Nobile Rim 1 | 1 | 70.05, -124.35 | Arctic Canada | 0.996 | 205 | Paulatuk (Nora Aliqatchialuk Ruben) Airport (77.4 km) |
| Nobile Rim 1 | 2 | 70.15, -116.85 | Arctic Canada | 0.990 | 226 | Ulukhaktok Holman Airport (76.9 km) |
| Nobile Rim 1 | 3 | 68.25, -96.15 | Arctic Canada | 0.936 | 183 | Gjoa Haven Airport (44.6 km) |
| Mons Mouton | 1 | 70.05, -124.35 | Arctic Canada | 0.996 | 205 | Paulatuk (Nora Aliqatchialuk Ruben) Airport (77.4 km) |
| Mons Mouton | 2 | 70.15, -116.85 | Arctic Canada | 0.990 | 226 | Ulukhaktok Holman Airport (76.9 km) |
| Mons Mouton | 3 | 68.25, -96.15 | Arctic Canada | 0.938 | 184 | Gjoa Haven Airport (44.6 km) |
| Mons Mouton Plateau | 1 | 74.65, -95.75 | Arctic Canada | 1.000 | 246 | Resolute Bay Airport (24.1 km) |
| Mons Mouton Plateau | 2 | 74.85, -91.75 | Arctic Canada | 0.999 | 240 | Resolute Bay Airport (95.1 km) |
| Mons Mouton Plateau | 3 | 70.05, -124.35 | Arctic Canada | 0.996 | 261 | Paulatuk (Nora Aliqatchialuk Ruben) Airport (77.4 km) |
| Amundsen Rim | 1 | 74.65, -95.75 | Arctic Canada | 1.000 | 260 | Resolute Bay Airport (24.1 km) |
| Amundsen Rim | 2 | 74.75, -91.75 | Arctic Canada | 1.000 | 209 | Resolute Bay Airport (94.3 km) |
| Amundsen Rim | 3 | 70.05, -124.35 | Arctic Canada | 0.996 | 266 | Paulatuk (Nora Aliqatchialuk Ruben) Airport (77.4 km) |
| Nobile Rim 2 | 1 | 74.65, -95.75 | Arctic Canada | 1.000 | 293 | Resolute Bay Airport (24.1 km) |
| Nobile Rim 2 | 2 | 74.75, -91.75 | Arctic Canada | 1.000 | 232 | Resolute Bay Airport (94.3 km) |
| Nobile Rim 2 | 3 | 70.05, -124.35 | Arctic Canada | 0.996 | 282 | Paulatuk (Nora Aliqatchialuk Ruben) Airport (77.4 km) |
| Peak near Cabeus B | 1 | 74.65, -95.75 | Arctic Canada | 1.000 | 312 | Resolute Bay Airport (24.1 km) |
| Peak near Cabeus B | 2 | 74.75, -91.75 | Arctic Canada | 1.000 | 247 | Resolute Bay Airport (94.3 km) |
| Peak near Cabeus B | 3 | 74.65, -93.75 | Arctic Canada | 0.997 | 201 | Resolute Bay Airport (36.6 km) |

Source: `cells_scored.json` → `targets.<target>.goals.lighting`, `long_open_hours` (ties by hours); `access_cells.json` → `nearest_scheduled.name`, `.km`.

Share of the top 50 lighting areas by country (areas, not thinned to one per 50 km):

| Target | Areas | Countries (two-letter codes of the airports table; NO includes Svalbard and Jan Mayen) |
|---|---|---|
| Connecting Ridge | 50 | CA 52%, RU 32%, NO 10%, GL 4%, US 2% |
| Connecting Ridge Extension | 50 | CA 60%, RU 24%, NO 10%, GL 4%, US 2% |
| Peak Near Shackleton | 50 | CA 68%, RU 18%, NO 10%, GL 4% |
| de Gerlache Rim 1 | 50 | CA 72%, RU 14%, NO 10%, GL 4% |
| de Gerlache Rim 2 | 50 | CA 76%, NO 10%, RU 10%, GL 4% |
| Faustini Rim A | 50 | CA 70%, GL 10%, NO 10%, RU 10% |
| Slater Plain | 50 | CA 68%, RU 14%, NO 12%, GL 6% |
| Haworth | 50 | CA 70%, NO 14%, RU 14%, GL 2% |
| Malapert Massif | 50 | CA 58%, RU 24%, NO 18% |
| de Gerlache-Kocher Massif | 50 | CA 50%, RU 30%, NO 20% |
| Nobile Rim 1 | 50 | RU 56%, CA 30%, NO 12%, unknown 2% |
| Mons Mouton | 50 | RU 56%, CA 30%, NO 12%, unknown 2% |
| Mons Mouton Plateau | 50 | RU 60%, CA 36%, GL 2%, NO 2% |
| Amundsen Rim | 50 | RU 60%, CA 36%, GL 2%, NO 2% |
| Nobile Rim 2 | 50 | RU 60%, CA 30%, GL 4%, IS 4%, NO 2% |
| Peak near Cabeus B | 50 | RU 58%, CA 32%, GL 4%, IS 4%, NO 2% |

Source: `cells_scored.json` → `goals.lighting`; `access_cells.json` → `cells.<id>.country` (a guess from the nearest table record within 300 km, not a border test; unknown where it is null).

What the distance is not: Not a road or a port, not a permit, not a cost: a straight-line distance to a runway. It does not say that a road, a track or a boat links the airfield to the cell, that the runway is open, long enough or has fuel, that anyone flies there on the day, that the land may be entered, or what the trip costs. Water, ice caps, mountains and borders between the cell and the runway are ignored. "Scheduled service" is the table's own yes/no flag, entered by volunteers; it was not checked against any timetable. (`access_cells.json` → `meta.what_this_is_not`)

## Files

| File | Written | What |
|---|---|---|
| `latitude_profile.json` | 10:01:01 | Sun geometry by latitude (a); both sets of thresholds |
| `grazing_cells.json`, `grazing_bins.npz` | 09:48:11 | hours per cell and target; per ten-day bin (per-day long spells) |
| `candidates.json` | 09:48:49 | every cell, with the reasons of version 2 and the blind sample |
| `horizon_cells.json`, `terrain_cells.json` | 17:54:17, 09:36:25 | terrain horizon; slope statistics |
| `cloud_cells.json` | 09:48:57 | monthly mean cloud amount per cell (NASA POWER) |
| `cells_scored.json`, `ranking.txt` | 10:01:30 | scores, clear-sky hours and the ranking tables, every cell |
| `validation.json` | 10:43:40 | named sites, counts, terrain share, old against new, stability, regions, Haughton |
| `snow_free_dekads.npz` | 13:28:39 | snow-free odds per ten-day bin (input) |
| `snow_validation_many.json` | 10:44:34 | the station check of the snow odds (version 2 figures) |
| `winter_leads.json` | 10:43:23 | squares the bare-ground screen hides, winter half (l) |
| `access_cells.json` | 10:31:34 | distance to the nearest airfield (m) |
| `checks.json` | 20:03:49 | the independent recount and the comparison with JPL Horizons (i) |
| `RESULTS_v2.md`, `validation_v2.json`, `ranking_v2.txt`, `cells_scored_v2.json` | 14:39:09 | version 2, kept for section (k) |

Source: the time each file in `data/derived/` was last written, read from the file system when this file was generated (local time).


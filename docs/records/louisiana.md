# Louisiana: the record

Built 2026-11-19, for the 2026 general election only, and **county-only**: bar view by parish and dot view, with no By precinct view or precinct menu. This has the shape of `docs/PIPELINE.md`, Part 7.

**Parishes are counties.** Louisiana's 64 parishes have county codes in the Census files, and the pages and files call them counties, as the site's other states do. The page and Sources say so; the dot text says "parish".

**One race.** U.S. Senate is the only statewide race between candidates. The six U.S. House races are by district, and Districts 5 and 6 go to a runoff on Dec. 12, 2026.

**Official results.** The owner asked on 2026-11-19 to check Louisiana, then to build it. When the results were saved that day, the results site's header for the Nov. 3 election read "Official Results" (it reads "Unofficial Results" for the Dec. 12 runoff). So `state.js` sets `official: true`, and there's no "unofficial until" wording.

## Raw files, under `data/raw/la/` (not committed)

| What | Path | SHA-256 (first 16) |
|---|---|---|
| U.S. Senate by parish, from the [results site](https://voterportal.sos.la.gov/graphical)'s Download Results dialog (election "Tues Nov 3 2026", race "U. S. Senator", type "Parish", "Download Race"). The page builds the file itself, with no request to the server, so it was saved by Chrome as `ByParish_67997.csv` and moved here | `results/senate-by-parish.csv` | `66947eb67880e352` |
| The race's statewide figures, reporting and "Official Results" header, read off the page by hand. Its `note` says how | `results/page-figures.json` | see the file |
| 2020 Census redistricting file ([zip](https://www2.census.gov/programs-surveys/decennial/2020/data/01-Redistricting_File--PL_94-171/Louisiana/la2020.pl.zip)) | `census/la2020.pl.zip` | `d8d9ea96195f2b84` |
| 2020 census block shapes ([zip](https://www2.census.gov/geo/tiger/TIGER2020/TABBLOCK20/tl_2020_22_tabblock20.zip)) | `census/tl_2020_22_tabblock20.zip` | `cd051604d53f3cf2` |

The owner approved each download by name on 2026-11-19. The race data file behind the page (`Data?blob=20261103/RacesCandidates_Multiparish.htm`) had `WriteTime` 2026-11-19T20:58:46.527.

## Terms of use, read 2026-11-19

This is a reading of the published pages, not legal advice. Nobody at the Secretary of State's office has been asked.

| Source | What it says | What it asks of us |
|---|---|---|
| [Secretary of State: Disclaimer](https://www.sos.la.gov/disclaimer), read in full | Information on the site "is collected, maintained and provided for the convenience of our customers". It disclaims certifying information from third parties and any liability for reliance on it. Nothing on copying, republishing or altering. | Nothing for reuse |
| [Secretary of State: Security & Privacy](https://www.sos.la.gov/security-privacy), read in full | Visitor statistics, and a warning that attempts to tamper with the site may be prosecuted. Nothing on reuse. | Nothing |
| Secretary of State site footer | "© 2026 Louisiana Department of State" | See below |
| Results site, [voterportal.sos.la.gov/graphical](https://voterportal.sos.la.gov/graphical) | No terms of its own. Footer: "Copyright © 2026 Louisiana Department of State" | Nothing stated |
| [louisiana.gov privacy policy](https://www.louisiana.gov/privacy-policy/), the only policy page the state portal's footer links to | Searched for copying, reuse, license and similar words: only security monitoring. Whether it reaches the Secretary of State's site is unclear in any case | Nothing found |
| Census files, us-atlas | As in `docs/PIPELINE.md`, Part 8 | Credit in Sources, and the TIGER/Line note |

**The reading:** the terms are **silent** on reusing results: no license, and no limit beyond an accuracy disclaimer and bare copyright footers. That's the same standing as Vermont and West Virginia. The owner chose Louisiana on 2026-11-19 after being told this.

**Gap in the record:** the Secretary of State's other pages weren't searched for terms beyond the two its footer links.

## Build, from the repo root

| # | Command | Writes to `data/la/` | SHA-256 (first 16) |
|---|---|---|---|
| 1 | `python scripts/build_la_results.py` | `results-2026.json` | `8a36578e303c3e3d` |
| 2 | `python scripts/build_cities.py la` | `cities.json` | `d1e9eafbf655d738` |
| 3 | `python scripts/build_precincts.py la` (reads #1) | `blocks.json.gz` | `729faeca86b87089` |
| 4 | `python scripts/build_landmask.py la` | `landmask.bin.gz` | `edac31cb1997f72a` |

## Numbers to expect

- 1 race on 64 parishes; 3,722 precincts, all reporting
- 236 places, the largest New Orleans
- 142,874 blocks, 90,765 with adults, 3,570,548 adults
- A 5,159 × 4,671 land grid; 93,206 blocks drawn
- U.S. Senate: Julia Letlow (Republican) 746,466, "Jamie" Davis (Democrat) 720,516; 1,466,982 in all, no other candidates and no write-ins listed. Letlow carried 49 parishes, covering 83% of the land, and won 50.9% to 49.1%. Fewest votes: Tensas, 1,807; most: East Baton Rouge, 152,173.

Checks that stop the build: the page says "Official Results" and every parish and precinct reported; 64 parishes, once each, matching the Census names; the CSV's candidates match the page's; the parishes add up to the page's statewide figures, candidate by candidate; one Democrat and one Republican; and every parish has at least 10 votes.

## What differs from earlier states

- **Projection:** parallels 29.6° and 32.3°, centered on 91.4° W.
- **Parish names:** the results site writes "Lasalle", "De Soto" and "St. John The Baptist"; the build matches names ignoring case, spaces and periods, and the pages use the Census's names.
- **No incumbent:** Bill Cassidy held the seat and wasn't on the November ballot.
- **"Jamie" Davis** keeps the quotation marks the state prints.

## Gaps

- The statewide figures were read off the page by hand, as in `page-figures.json`.
- No precinct view: precinct shapes weren't looked for. The results site has precinct results.
- No By district view: Louisiana's 2026 U.S. House lines weren't looked into, and two seats aren't decided until Dec. 12.
- Hand-picked text: no tour, flights or history.

## How this was checked (2026-11-19)

- In the browser at desktop width: the page opens on U.S. Senate, by county, flat and in 3D; the headline reads "Letlow won 49 of 64 counties, which cover 83% of Louisiana's land area"; the dot view counts 1,466,982 voters, matching the race; the home page and Sources list Louisiana. No console errors.
- **Not checked:** phone width, and the land grid in close-ups.

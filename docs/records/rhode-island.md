# Rhode Island: the record

Built 2026-11-09, for the 2026 general election only, and **county-only**: bar view by county and dot view, with no By precinct view or precinct menu. This has the shape of `docs/PIPELINE.md`, Part 7.

**Results are unofficial and partial.** All 39 cities and towns show as reported, but the site marks 90 of 456 precincts "Partially Reported", which likely means ballots such as provisionals are still to be added. So the pages say "led". The build stops if that count changes. The Board of Elections certifies the results; its date wasn't looked up. Save the export again after certification, rebuild, and compare.

## Counties from towns

Rhode Island reports by city and town, and its counties have no government of their own. Every town lies in one county, so the build adds towns up by county, using the Census file's county subdivision records for which county each town is in. All 39 towns matched.

**Federal-only ballots:** the export lists a "Federal" entry beside the towns, with 776 U.S. Senate votes on ballots for federal offices only (Reed 751, McKay 13, Bahry 8, write-ins 4). They belong to no town, so they aren't on the map, and the map's Senate totals are the state's minus those votes. Sources and Method say so.

## Raw files, under `data/raw/ri/` (not committed)

| What | Path | SHA-256 (first 16) |
|---|---|---|
| [Media Export](https://electionresults.ri.gov/cdn/results/RhodeIsland/export-2026StatewideGeneralElection.json) from the [results site](https://electionresults.ri.gov/results/public/rhodeisland/elections/2026StatewideGeneralElection), plain `curl`; Last-Modified Nov. 9, 2026, 19:31:31 GMT | `results/export-2026StatewideGeneralElection.json` | `8ebd086538e8e3b4` |
| Its response headers, and when it was saved (2026-11-09T23:03:37Z) | `results/export.headers.txt`, `results/saved-at.txt` | not recorded |
| 2020 Census redistricting file ([zip](https://www2.census.gov/programs-surveys/decennial/2020/data/01-Redistricting_File--PL_94-171/Rhode_Island/ri2020.pl.zip)) | `census/ri2020.pl.zip` | `a2a6de20d0bac0df` |
| 2020 census block shapes ([zip](https://www2.census.gov/geo/tiger/TIGER2020/TABBLOCK20/tl_2020_44_tabblock20.zip)) | `census/tl_2020_44_tabblock20.zip` | `79d10c9dfec1e3e0` |

**Access:** the results site's list of elections was opened in Chrome to find the election's id. The export's address follows the same pattern as Georgia's, from the same vendor; the export itself came by plain `curl`. `elections.ri.gov` returns 403 to plain requests and wasn't used for data.

## Terms of use, read 2026-11-09

This is a reading of the published pages, not legal advice. Nobody at the Board has been asked.

| Source | What it says | What it asks of us |
|---|---|---|
| RI.gov [Copyright policy](https://www.ri.gov/policies/copyright/), read in full | "The compiled information presented on this WWW site is considered public information and may be distributed or copied. However, use of appropriate byline/photo/image credits is requested." It also says the State makes no warranty that its materials are free of others' claims. | Credit the source. Done, in Sources. |
| Results site | No terms or copyright wording and no policy links on the pages read. It says "UNOFFICIAL RESULTS". | Say unofficial. Done. |
| Census files, us-atlas | As in `docs/PIPELINE.md`, Part 8 | Credit in Sources, and the TIGER/Line note |

**The reading:** RI.gov's policy allows distributing and copying compiled information, which covers this use more plainly than most states. Applying the RI.gov portal's policy to the Board of Elections' results site is inferred: the results site names no terms of its own.

## Build, from the repo root

| # | Command | Writes to `data/ri/` | SHA-256 (first 16) |
|---|---|---|---|
| 1 | `python scripts/build_ri_results.py` | `results-2026.json` | `57fa96ea8513c7a4` |
| 2 | `python scripts/build_cities.py ri` | `cities.json` | `58c1c08ef60f7c7c` |
| 3 | `python scripts/build_precincts.py ri` (reads #1) | `blocks.json.gz` | `051917e74cdd2d82` |
| 4 | `python scripts/build_landmask.py ri` | `landmask.bin.gz` | `287af9abdca2542a` |

## Numbers to expect

- 4 races on 5 counties from 39 towns; 456 precincts, 90 partly reported
- 11 places, the largest Providence
- 25,649 blocks, 21,287 with adults, 887,594 adults
- A 697 × 1,038 land grid; 21,469 blocks drawn

| Race | Democrat | Republican | All votes on the map |
|---|---|---|---:|
| U.S. Senate | John F. Reed 239,817 | Raymond T. McKay 105,418 | 359,475 |
| Lieutenant Governor | Sabina Matos 211,496 | John J. Loughlin, II 143,849 | 356,413 |
| Attorney General | Kimberly Ahern 234,068 | Alan Leonard Gordon 117,832 | 352,812 |
| General Treasurer | James A. Diossa 228,968 | Micholas A. Credle 121,311 | 350,997 |

Senate's other: Michael Bahry (independent) and write-ins. The Senate figures leave out the 776 federal-only votes.

**Left out:**

- **Governor:** Helena Buonanno Foulkes (Democrat) 207,473, Kenneth Block (independent) 99,817, Aaron C. Guckian (Republican) 47,382, and two more independents. With the Republican third, a map of a Democrat against a Republican would mislead, as with Montana in Part 8.
- **Secretary of State:** one candidate.
- **U.S. House:** two districts, so not statewide. Ballot questions and local races.

Checks that stop the build: the export is this election; all 39 towns and the Federal entry are there and match the Census; every town's status is reported; precincts add up to each town; towns plus the Federal entry add up to each statewide figure; the partly reported count is still 90; and the left-out races still don't have a Democrat and a Republican on top.

## What differs from earlier states

- **Projection:** parallels 41.3° and 41.9°, centered on 71.5° W.
- **Base race:** U.S. Senate.
- **Wording:** `state.js` calls the authority "the Rhode Island elections board", because the pages add "'s" and the Board's name ends in "Elections".
- **Party codes:** independents are `IND`, so the pages say Independent.

## Gaps

- Certification date not looked up.
- What "Partially Reported" means wasn't confirmed with the Board.
- Method's general sentence that county figures add up to the state's totals isn't exact for U.S. Senate; the sentence before it explains the 776 votes.
- Hand-picked text: no tour, flights or history.

## How this was checked (2026-11-09)

- In the browser at desktop width: the results page opens on U.S. Senate with "led" wording and the partial and federal-only notes in Method; the dot view counts 359,475 voters, matching the race. No console errors.
- **Not checked:** phone width, the 3D view, whether the homepage label fits the small state, and the land grid in close-ups.

## U.S. House, added 2026-11-12

`results-2026.json` now also has the U.S. House as one race: every district added up by county, with each district's own result, built by the same script through `scripts/chamber.py`. Both districts are in the export. As for the statewide races, towns add up to counties and the Federal entry's votes, which belong to no town, are left out of the counties and the districts alike. The results page draws the districts (By district) on Census outlines, which the build checks against the results. The record for all the states is in [`../PIPELINE.md`](../PIPELINE.md), Part 10.

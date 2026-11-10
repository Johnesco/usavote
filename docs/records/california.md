# California: the record

Built 2026-11-09, for the 2026 general election only, and **county-only**: bar view by county and dot view, with no By precinct view or precinct menu. This has the shape of `docs/PIPELINE.md`, Part 7.

**Results are unofficial and partial.** Every precinct shows as reporting, but California counts mail ballots for weeks. The state's Unprocessed Ballots Report estimated **3,002,342 ballots still to process** as of Nov. 8, 2026, 5:00 p.m., beside 10,622,926 processed. Counties report final results by Dec. 4, 2026, and the Secretary of State certifies them by Dec. 11, 2026. So the pages say "led", not "won", and give the outstanding count. Save the files again after Dec. 11, rebuild, and compare. The map will change noticeably before then: about 22% of ballots weren't in these totals.

## Raw files, under `data/raw/ca/` (not committed)

| What | Path | SHA-256 (first 16) |
|---|---|---|
| The results API behind [the results site](https://electionresults.sos.ca.gov/), `https://api.sos.ca.gov/returns/<race>` and `.../<race>/county/<county>`: one statewide file and 58 county files per race, plus ballot measures and the API's `status` feed. Saved by `scripts/ca_results_save.py` with plain `curl`, 474 files. | `results/<race>/*.json`, `results/status.json` | each in `results/SAVED.json` (`37feb4ad994f6a88`) |
| Statewide row of the [Unprocessed Ballots Report](https://electionresults.sos.ca.gov/unprocessed-ballots-status), read in Chrome | `results/unprocessed-extract.json` | `358199ca6cacf57a` |
| 2020 Census redistricting file ([zip](https://www2.census.gov/programs-surveys/decennial/2020/data/01-Redistricting_File--PL_94-171/California/ca2020.pl.zip)) | `census/ca2020.pl.zip` | `e02c83c85a9a5d69` |
| 2020 census block shapes ([zip](https://www2.census.gov/geo/tiger/TIGER2020/TABBLOCK20/tl_2020_06_tabblock20.zip)) | `census/tl_2020_06_tabblock20.zip` | `154ffb979e4d1f8c` |

**Access:** the API answered plain `curl`. `www.sos.ca.gov` returns a bot check to plain requests, so its pages were only read in Chrome; no data came from them. The API's `status` feed carries a 2024 timestamp and isn't read by the build.

## Terms of use, read 2026-11-09

This is a reading of the published pages, not legal advice. Nobody at these offices has been asked.

| Source | What it says | What it asks of us |
|---|---|---|
| State of California [Conditions of Use](https://www.ca.gov/use/) (redirects to `/legal/conditions-of-use/`), read in full | Under "Ownership": "In general, information presented on this website, unless otherwise indicated, is considered in the public domain. It may be distributed or copied as permitted by law." It adds that the State uses some copyrighted material, such as photographs, which may need permission. | Nothing for the results, if this covers them |
| Secretary of State's [privacy policy](https://www.sos.ca.gov/administration/privacy-policy/) | About personal information. The `sos.ca.gov` home page links no other terms. | Nothing |
| Results site footer | "© California Secretary of State", with no terms link | See below |
| Census files, us-atlas | As in `docs/PIPELINE.md`, Part 8 | Credit in Sources, and the TIGER/Line note |

**The reading:** the Conditions of Use are the clearest grant in this survey. Two things weaken it. The page is ca.gov's, and applying it to the Secretary of State's results site is inferred, since the results site links no terms of its own. And the results site's footer says "© California Secretary of State", which might count as "otherwise indicated". A bare copyright footer on a page of vote counts is common and may only be boilerplate, but the owner should know about it before publishing.

## Build, from the repo root

| # | Command | Writes to `data/ca/` | SHA-256 (first 16) |
|---|---|---|---|
| 0 | `python scripts/ca_results_save.py` | `data/raw/ca/results/*` | as above |
| 1 | `python scripts/build_ca_results.py` | `results-2026.json` | `cf87ad49d8c55733` |
| 2 | `python scripts/build_cities.py ca` | `cities.json` | `f3ce3b48083b62e7` |
| 3 | `python scripts/build_precincts.py ca` (reads #1) | `blocks.json.gz` | `7600ef232e57b6df` |
| 4 | `python scripts/build_landmask.py ca` | `landmask.bin.gz` | `594d5e79e1290c35` |

## Numbers to expect

- 6 races on 58 counties; the API's stamp "November 9, 2026, 2:21 p.m."
- 595 places, the largest Los Angeles
- 519,723 blocks, 375,569 with adults, 30,827,105 adults
- A 9,727 × 10,674 land grid; 379,736 blocks drawn

| Race | Democrat | Republican | All votes |
|---|---|---|---:|
| Governor | Xavier Becerra 6,914,755 | Steve Hilton 3,625,315 | 10,540,070 |
| Lieutenant Governor | Fiona Ma 6,807,332 | Gloria Romero 3,587,831 | 10,395,163 |
| Secretary of State | Shirley N. Weber 6,900,173 | Donald P. (Don) Wagner 3,483,456 | 10,383,629 |
| Controller | Malia M. Cohen 6,764,570 | Herb W Morgan 3,566,574 | 10,331,144 |
| Treasurer | Eleni Kounalakis 6,780,782 | Jennifer Hawks 3,546,702 | 10,327,484 |
| Attorney General | Rob Bonta 6,792,333 | Michael E. Gates 3,583,716 | 10,376,049 |

**Left out:** Insurance Commissioner (two Democrats, Jane Kim and Ben Allen, under the top-two system), Superintendent of Public Instruction (nonpartisan), ballot measures, and races not on the ballot statewide. There's no U.S. Senate race in California in 2026.

Checks that stop the build: every race and county file says all precincts reported; each county file's statewide block equals the race's statewide file; all 58 counties match the Census names; each candidate's counties add up to the statewide figure; the left-out races still aren't a Democrat against a Republican; and every county has at least 10 Governor votes (fewest: 560, Alpine).

## What differs from earlier states

- **Projection:** parallels 34.1° and 40.4°, centered on 119.3° W.
- **Base race:** Governor.
- **Partial count:** pinned in `unprocessed-extract.json` and shown in Method; `state.js` uses "led".
- **Incumbents:** the API marks them, and the build keeps the marks.
- **Size:** about 10.5 million dots, a little more than Texas's 9.9 million. The dot view loaded in about 10 seconds at desktop width.

## Gaps

- The ballots-left figure is from Nov. 8, a day before the results' stamp.
- Whether the Conditions of Use reach the results site, as above.
- Hand-picked text: no tour, flights or history.

## How this was checked (2026-11-09)

- In the browser at desktop width: the homepage shows California; the results page opens on Governor with "led" wording and the outstanding count in Method; the dot view counts 10,540,070 voters, matching the race. No console errors.
- **Not checked:** phone width, the 3D view, every race by eye, and the land grid in close-ups.

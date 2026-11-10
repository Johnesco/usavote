# Vermont: the record

Built 2026-11-09, for the 2026 general election only, and **county-only**: bar view by county and dot view, with no By precinct view or precinct menu. This has the shape of `docs/PIPELINE.md`, Part 7.

**Results are unofficial.** The results site says "UNOFFICIAL" with all 247 towns reporting. The state canvassing committee certifies them; its date wasn't looked up. Save the files again after that, rebuild, and compare.

## Counties from towns

Vermont reports by town, some towns by more than one district. Every town lies in one county, so the build adds towns up by county, using the results site's own town list for each town's county. Each office's rows also include a "STATE WIDE" row, and the town rows must add up to it, candidate by candidate.

## Raw files, under `data/raw/vt/results/` (not committed)

Saved 2026-11-09T23:05:33Z with plain `curl`, from `https://static.electionresults.vermont.gov/elections/`, the files [Election Night Results](https://electionresults.vermont.gov/) loads. The paths were found by opening the site in Chrome. The site's stamp read "11/09/2026 06:03 PM".

| What | Path | SHA-256 (first 16) |
|---|---|---|
| List of elections | `elections.json` | `70fce037d93b4d10` |
| This election: settings, towns, each town's county and districts | `election.json` | `4245d95fa8144d77` |
| Statewide offices by town | `s-20261109180316.json` | `bb5c5ba6fe6b9e9e` |
| Federal offices (U.S. House) by town; Last-Modified Nov. 9, 2026, 23:03:21 GMT | `feed-20261109180316.json` | `144361738949a56b` |
| Town offices, not read | `t-20261109180316.json` | `c41a7d7096df7da0` |
| Turnout by town | `turnout-20261109180316.json` | `2812878b52513859` |
| 2020 Census redistricting file ([zip](https://www2.census.gov/programs-surveys/decennial/2020/data/01-Redistricting_File--PL_94-171/Vermont/vt2020.pl.zip)) | `../census/vt2020.pl.zip` | `6a18a3364dff5e04` |
| 2020 census block shapes ([zip](https://www2.census.gov/geo/tiger/TIGER2020/TABBLOCK20/tl_2020_50_tabblock20.zip)) | `../census/tl_2020_50_tabblock20.zip` | `7ffc06ba34d211ac` |

## Terms of use, read 2026-11-09

This is a reading of the published pages, not legal advice. Nobody at the Secretary of State's office has been asked.

| Source | What it says | What it asks of us |
|---|---|---|
| [Vermont.gov policies](https://www.vermont.gov/policies), read in Chrome | Limits apply to photos: they're copyrighted by the photographer and allowed only for personal, non-commercial use. Nothing found on reusing other content. Copyright complaints go to Tyler Technologies, the portal's vendor. | Nothing for the results |
| Results site footer | "© 2026 Copyright", with no terms link | See below |
| Census files, us-atlas | As in `docs/PIPELINE.md`, Part 8 | Credit in Sources, and the TIGER/Line note |

**The reading:** the terms are **silent** on reusing results: no license, and no limit. The owner chose Vermont on 2026-11-09 after being told this, the same treatment as Texas, Oklahoma, New Mexico, Idaho and Georgia. The results site carries a bare copyright footer.

## Build, from the repo root

| # | Command | Writes to `data/vt/` | SHA-256 (first 16) |
|---|---|---|---|
| 1 | `python scripts/build_vt_results.py` | `results-2026.json` | `08b5dfe5a4a3d0f2` |
| 2 | `python scripts/build_cities.py vt` | `cities.json` | `46a0de29eeb2b54e` |
| 3 | `python scripts/build_precincts.py vt` (reads #1) | `blocks.json.gz` | `972a7fad832e169c` |
| 4 | `python scripts/build_landmask.py vt` | `landmask.bin.gz` | `28a9d736d8a90a4f` |

## Numbers to expect

- 7 races on 14 counties from 247 towns; 311,510 ballots; 506,830 registered
- 28 places, the largest Burlington
- 24,611 blocks, 17,531 with adults, 524,482 adults
- A 1,622 × 2,562 land grid; 18,469 blocks drawn

| Race | Democrat | Republican | All votes |
|---|---|---|---:|
| Governor | Amanda Janoo 141,631 | Phil Scott 162,048 | 309,055 |
| U.S. House | Becca Balint 198,758 | Gerald Malloy 94,078 | 304,675 |
| Lieutenant Governor | Molly Gray 190,988 | John S. Rodgers 112,754 | 304,298 |
| State Treasurer | Mike Pieciak 185,802 | Lynn Lafleur 92,846 | 298,280 |
| Secretary of State | Sarah Copeland Hanzas 174,741 | H. Brooke Paige 96,149 | 295,130 |
| Auditor of Accounts | Tim Ashe 203,377 | Ivar Kronick 90,689 | 294,362 |
| Attorney General | Charity R. Clark 200,480 | Edwin Howell Kemon 94,949 | 295,956 |

U.S. House matches the results page read in Chrome: Balint 198,758, Malloy 94,078 and 246 write-ins.

**Left out:** U.S. Senate isn't on the ballot in 2026. Constitutional amendments are on a separate page and aren't candidates. Legislative, county and town races aren't statewide.

Checks that stop the build: the site says unofficial and 100% of towns reporting; the saved files are the ones the election file points to; every town is in one county, and the counties match the Census; every district row is fully reported; town rows add up to the STATE WIDE row; each mapped office has one Democrat and one Republican; no race has more votes than ballots; and every county has at least 10 Governor votes (fewest: 2,580, Essex).

## What differs from earlier states

- **Projection:** parallels 43.1° and 44.6°, centered on 72.5° W.
- **Base race:** Governor.
- **Fusion:** Governor's Democrat ran as "DEM/PROG", the nominee of the Democrats and Progressives, and is shown as the Democrat. Sources says so.
- **Write-ins:** listed by name. A write-in for someone already on the ballot counts as a write-in, as the site counts it. All write-ins are "other". Blank votes and overvotes aren't counted.
- **Names:** the site writes names in capitals; the build writes them in title case.

## Gaps

- Certification date not looked up.
- Hand-picked text: no tour, flights or history.

## How this was checked (2026-11-09)

- In the browser at desktop width: the results page opens on Governor (Scott won, 52.4% to 45.8%); the dot view counts 309,055 voters, matching the race. No console errors.
- **Not checked:** phone width, the 3D view, every race by eye, and the land grid in close-ups.

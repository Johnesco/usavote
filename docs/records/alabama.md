# Alabama: the record

Built 2026-11-19, for the 2026 general election only, and **county-only**: bar view by county and dot view, with no By precinct or By district view. This has the shape of `docs/PIPELINE.md`, Part 7.

**Added up from precincts, with nothing to check against.** The Secretary of State posts a workbook per county with a column per polling place, plus absentee and provisional ballots. The build adds the columns up. The files have no statewide or district totals, so, unlike every other state here, the sums couldn't be checked against the State's own figures. The pages say so in place of "add up exactly to the statewide totals" (`statewideTotals` and `chamberTotals` in `state.js`).

**Twelve races.** U.S. Senate, Governor and nine more statewide races between a Democrat and a Republican, and U.S. House, the 7 district races added up by county (`scripts/chamber.py`). Amendments, appeals court races, the state board of education and legislative races aren't here.

**Unofficial results.** The owner asked on 2026-11-19 to check Alabama, then chose to build it with Virginia, knowing its terms are silent (below). Whether the files are official wasn't found; the 2026 information page listed no certification for Nov. 3. They're treated as unofficial until the State Canvassing Board certifies them (date not looked up).

## Raw files, under `data/raw/al/` (not committed)

| What | Path | SHA-256 (first 16) |
|---|---|---|
| "2026 General Election Results - Precinct Level", from [Elections Data Downloads](https://www.sos.alabama.gov/alabama-votes/voter/election-data) ([zip](https://www.sos.alabama.gov/sites/default/files/election-data/2026-11/2026GeneralElectionPrecinctResults.zip), 1,032,122 bytes, Last-Modified Nov. 16, 2026, 22:53:11 GMT): 67 Excel 97 workbooks, `2026_GENERAL_ELECTION-<COUNTY>.xls` | `results/2026GeneralElectionPrecinctResults.zip` | `fd67927fa84cafb0` |
| Its response headers | `results/zip.headers.txt` | `c85ae67ba326b219` |
| When it was saved (UTC) | `results/saved-at.txt` | see the file |
| The 67 workbooks saved as CSV (UTF-8) by Excel, with macros disabled (`AutomationSecurity` 3), since Python here can't read `.xls`. The build checks the CSVs' names against the zip's | `results/csv/*.csv` | not hashed |
| 2020 Census redistricting file ([zip](https://www2.census.gov/programs-surveys/decennial/2020/data/01-Redistricting_File--PL_94-171/Alabama/al2020.pl.zip)) | `census/al2020.pl.zip` | `bd3fbbf22615b166` |
| 2020 census block shapes ([zip](https://www2.census.gov/geo/tiger/TIGER2020/TABBLOCK20/tl_2020_01_tabblock20.zip)) | `census/tl_2020_01_tabblock20.zip` | `5d228872ccc68037` |

The owner approved the zip and the two Census files on 2026-11-19 ("Build both VA and AL", after being told what would be downloaded).

## Terms of use, read 2026-11-19

This is a reading of the published pages, not legal advice. Nobody at the Secretary of State's office has been asked.

| Source | What it says | What it asks of us |
|---|---|---|
| Secretary of State site ([sos.alabama.gov](https://www.sos.alabama.gov/)) | No copyright line found. Its footer's "Statements & Policies" link (`isd.alabama.gov/isd/statements.aspx`) doesn't load. | Nothing found |
| [Alabama.gov: Terms of Use](https://www.alabama.gov/terms-of-use), read in full | Accessibility, linking and security policies. "Copyright Issues": documents "contributed or licensed by private individuals, companies, or organizations" may be copyrighted, and reproducing those beyond fair use needs their owners' permission; it asks readers to contact each agency for its own policies. "Disclaimers": accuracy only. "Legal Notices": copyright complaints go to Tyler Technologies under the DMCA. Nothing limits reusing the State's own information. | Nothing for reuse of state results |
| Footer | "Copyright 2020 Alabama.gov" | See below |
| Census files, us-atlas | As in `docs/PIPELINE.md`, Part 8 | Credit in Sources, and the TIGER/Line note |

**The reading:** **silent**, the same standing as Vermont and West Virginia: no license, and no limit on the State's own information. Election results aren't contributed by private parties. The owner chose to build Alabama on 2026-11-19 after being told this. **Gap:** the Secretary of State's own policy page, which Alabama.gov tells readers to consult, couldn't be read.

## Build, from the repo root

| # | Command | Writes to `data/al/` | SHA-256 (first 16) |
|---|---|---|---|
| 1 | `python scripts/build_al_results.py` | `results-2026.json` | `9d01d13358a1bdee` |
| 2 | `python scripts/build_cities.py al` | `cities.json` | `ee9a662785a72c24` |
| 3 | `python scripts/build_precincts.py al` (reads #1) | `blocks.json.gz` | `0ac290b17e2ac2da` |
| 4 | `python scripts/build_landmask.py al` | `landmask.bin.gz` | `02b445f82764795b` |

## Numbers to expect

- 12 races on 67 counties; 1,927 polling-place columns, plus absentee and provisional
- 333 places, the largest Huntsville
- 185,976 blocks, 125,569 with adults, 3,917,166 adults
- A 3,459 × 5,433 land grid; 130,688 blocks drawn
- U.S. Senate: Barry Moore (Republican) 918,207, Everett Wess (Democrat) 759,018, write-ins 2,042; 1,679,267 in all. Moore carried 49 counties, covering 69% of the land, and won 54.7% to 45.2%. Fewest votes: Greene, 3,546; most: Jefferson, 243,449.
- Governor: Tommy Tuberville (Republican) 872,910, Doug Jones (Democrat) 806,868, write-ins 5,924. Every other statewide race went Republican, with the Democrat carrying 18 or 19 counties.
- U.S. House: 7 of 7 districts, 1,681,194 votes, seats 5 Republican and 2 Democratic.

Checks that stop the build: the CSVs are the zip's 67 workbooks; 67 counties, once each, matching the Census names; every county has every race with the same candidates and parties; no votes under a blank column and no totals column; every count a whole number; each county's votes in a race no more than its ballots cast; one Democrat and one Republican per race, and a majority winner; each House district has the same candidates in every county; every county has at least 10 votes.

## What differs from earlier states

- **Projection:** parallels 31.0° and 34.2°, centered on 86.7° W.
- **Columns:** most files end with ABSENTEE and PROVISIONAL; three spell it "PROVSIONAL", two add "PROVISIONAL ABSENTEE", and every file has blank trailing columns. The build sums every column with a header.
- **Straight-party votes** are already in each candidate's rows: each county's Governor rows, with over and under votes, come within a few votes of its ballots cast (Dale is furthest, 279). Over and under votes aren't counted.
- **No incumbents marked:** neither statewide headline race had one on the ballot (from general knowledge: Senator Tuberville ran for Governor instead of re-election, and Governor Ivey was term-limited). House incumbents aren't marked.
- **Homepage label:** "AL", since "Alabama" ran into Georgia.

## Gaps

- **No statewide totals to check against.** The election-night site (`www2.alabamavotes.gov/electionNight/`) loaded blank, and the files have none.
- Unofficial: rebuild after the State Canvassing Board certifies (date not looked up).
- The CSVs were made by Excel from the workbooks; they aren't hashed.
- No precinct view: precinct shapes weren't looked for, though the files have precinct results.
- No By district view: Alabama's 2026 U.S. House lines weren't looked into.
- Hand-picked text: no tour, flights or history.

## How this was checked (2026-11-19)

- In the browser at desktop width: the page opens on U.S. Senate, flat; U.S. House and the Governor dot view load; the headline reads "Moore won 49 of 67 counties, which cover 69% of Alabama's land area"; the Governor dot view counts 1,685,702 voters, matching the race; the method note says there are no statewide totals to check against; the home page and Sources list Alabama. No console errors.
- **Not checked:** Alabama in 3D (Virginia's 3D was), phone width, and the land grid in close-ups.

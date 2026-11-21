# New Hampshire: the record

Built 2026-11-20, for the 2026 general election only, and **county-only**: bar view by county and dot view, with no By precinct or By district view. This has the shape of `docs/PIPELINE.md`, Part 7.

**Towns and wards added up by county.** New Hampshire reports by town, and by ward in its cities: 320 in all. The Secretary of State's file for each county lists its towns and wards with a TOTALS row, and its summary lists the counties; the build adds up the towns and checks both.

**Three races.** U.S. Senate, Governor, and U.S. House, the 2 district races added up by county (`scripts/chamber.py`). The House files have no county column, so each town is placed in its county by the Governor and Senate files. Executive Council, State Senate and the other races aren't here.

**Not marked official.** The files and page don't say "unofficial", but the page says the tallies "accurately reflect the returns of votes reported by clerks but are subject to change if clerks submit amendments", and a recount schedule is posted. The site calls them unofficial until any recounts are done.

**Copyright notice only.** The owner asked on 2026-11-20 to check New Hampshire, then chose to build it with Connecticut, knowing the footer says "All rights reserved" with no terms (below).

## Raw files, under `data/raw/nh/` (not committed)

Saved 2026-11-20 through Chrome from the [2026 General Election Results](https://www.sos.nh.gov/2026-general-election-results) page, because the server answers scripts with 403 Forbidden; no User-Agent was faked. The owner allowed Chrome's multiple-download prompt for sos.nh.gov. Duplicate copies Chrome made (" (1)", " (2)") were checked identical and deleted. The workbooks' own `modified` dates run to Nov. 19, 2026.

| What | Path | SHA-256 (first 16) |
|---|---|---|
| U.S. Senator, Belknap County by town and ward | `results/2026-ge-us-senator-belknap.xlsx` | `f3ae25b336b00ed8` |
| U.S. Senator, Carroll County by town and ward | `results/2026-ge-us-senator-carroll.xlsx` | `774b6939eecb9257` |
| U.S. Senator, Cheshire County by town and ward | `results/2026-ge-us-senator-cheshire.xlsx` | `6b402e1353ac8604` |
| U.S. Senator, Coos County by town and ward | `results/2026-ge-us-senator-coos.xlsx` | `1443e3ba022b7cb9` |
| U.S. Senator, Grafton County by town and ward | `results/2026-ge-us-senator-grafton.xlsx` | `dae7c95685118e17` |
| U.S. Senator, Hillsborough County by town and ward | `results/2026-ge-us-senator-hillsborough.xlsx` | `746c55884068b897` |
| U.S. Senator, Merrimack County by town and ward | `results/2026-ge-us-senator-merrimack.xlsx` | `688f9088c4db33f6` |
| U.S. Senator, Rockingham County by town and ward | `results/2026-ge-us-senator-rockingham.xlsx` | `bd02d35cec02920e` |
| U.S. Senator, Strafford County by town and ward | `results/2026-ge-us-senator-strafford.xlsx` | `01e6acc92c406723` |
| U.S. Senator, Sullivan County by town and ward | `results/2026-ge-us-senator-sullivan.xlsx` | `b9357cd5b26b1940` |
| U.S. Senator, statewide summary by county | `results/2026-ge-us-senator-summary.xlsx` | `76a2c1fa69239c16` |
| Governor, Belknap County by town and ward | `results/2026-ge-governor-belknap.xlsx` | `c8a79bb4f79a203a` |
| Governor, Carroll County by town and ward | `results/2026-ge-governor-carroll.xlsx` | `124c87f05cc25360` |
| Governor, Cheshire County by town and ward | `results/2026-ge-governor-cheshire.xlsx` | `1b2293b320395374` |
| Governor, Coos County by town and ward | `results/2026-ge-governor-coos.xlsx` | `8845b532b77f1d2c` |
| Governor, Grafton County by town and ward | `results/2026-ge-governor-grafton.xlsx` | `ba14a1b9fe5e5693` |
| Governor, Hillsborough County by town and ward | `results/2026-ge-governor-hillsborough.xlsx` | `d59d7310cce7c3f4` |
| Governor, Merrimack County by town and ward | `results/2026-ge-governor-merrimack.xlsx` | `d0b0139dcf341d89` |
| Governor, Rockingham County by town and ward | `results/2026-ge-governor-rockingham.xlsx` | `96824bf1f0c0f780` |
| Governor, Strafford County by town and ward | `results/2026-ge-governor-strafford.xlsx` | `53da53943ff0577d` |
| Governor, Sullivan County by town and ward | `results/2026-ge-governor-sullivan.xlsx` | `371cb3e1dfbee671` |
| Governor, statewide summary by county | `results/2026-ge-governor-summary.xlsx` | `847bd28331973ad4` |
| U.S. House, District 1, by town and ward | `results/2026-ge-congressional-district-1.xlsx` | `3fd062a9033a86bf` |
| U.S. House, District 2, by town and ward | `results/2026-ge-congressional-district-2.xlsx` | `56cf7747354537b5` |
| When they were saved (UTC) | `results/saved-at.txt` | see the file |
| 2020 Census redistricting file ([zip](https://www2.census.gov/programs-surveys/decennial/2020/data/01-Redistricting_File--PL_94-171/New_Hampshire/nh2020.pl.zip)) | `census/nh2020.pl.zip` | `31852c0cfa871ea8` |
| 2020 census block shapes ([zip](https://www2.census.gov/geo/tiger/TIGER2020/TABBLOCK20/tl_2020_33_tabblock20.zip)) | `census/tl_2020_33_tabblock20.zip` | `253ef035968da264` |

The owner approved these downloads by name on 2026-11-20 ("Yes, download all").

## Terms of use, read 2026-11-20

This is a reading of the published pages, not legal advice. Nobody at the Secretary of State's office has been asked.

| Source | What it says | What it asks of us |
|---|---|---|
| Secretary of State site footer ([sos.nh.gov](https://www.sos.nh.gov/)) | "© 2026 State of New Hampshire • All rights reserved", linking NH.gov's Accessibility and Privacy policies | See below |
| [NH.gov: Privacy Policy](https://www.nh.gov/policies/privacy-policy), read in full | Collection and disclosure of personal information, cookies, security, and a disclaimer: no warranty, and "Relying on information contained on these sites is done at one's own risk". It says some agencies "may have policies specific to their agency". Nothing on reusing state information. | Nothing for reuse |

**The reading:** **copyright notice only**: "All rights reserved" with no terms, the same standing as Virginia, Ohio and South Carolina, which the owner accepted. No Secretary of State terms of its own were found.

## Results, as read before building, 2026-11-20

- The [2026 General Election Results](https://www.sos.nh.gov/2026-general-election-results) page has Excel files: ballots cast, names on checklist, and for **Governor** and **U.S. Senator** a statewide summary and one file per county (all 10), plus U.S. House (2 districts), Executive Council, State Senate and others. The page says tallies "accurately reflect the returns of votes reported by clerks but are subject to change if clerks submit amendments". A general election recount schedule is posted. No figures were read; the files weren't opened.
- Whether the results are final wasn't found. The county files are presumably by town, as New Hampshire reports.
- **Scripts are refused:** a plain `curl -I` of a summary file got 403 Forbidden, so the files would have to be saved through a browser.

## Build, from the repo root

| # | Command | Writes to `data/nh/` | SHA-256 (first 16) |
|---|---|---|---|
| 1 | `python scripts/build_nh_results.py` | `results-2026.json` | `33322d23bdf5064b` |
| 2 | `python scripts/build_cities.py nh` | `cities.json` | `857ca698f88fecfc` |
| 3 | `python scripts/build_precincts.py nh` (reads #1) | `blocks.json.gz` | `dcde972f151a8a51` |
| 4 | `python scripts/build_landmask.py nh` | `landmask.bin.gz` | `d45c357c65bfe464` |

The workbooks are read as XML (an .xlsx is a zip), since this Python has no Excel library.

## Numbers to expect

- 3 races on 10 counties; 320 towns and wards
- 17 places, the largest Manchester
- 31,948 blocks, 24,995 with adults, 1,120,680 adults
- A 1,630 × 2,916 land grid; 25,736 blocks with people or housing
- U.S. Senate: Chris Pappas (Democratic) 356,425, John E. Sununu (Republican) 268,682, Edmond Laplante (Constitution) 12,081, write-ins 792; 637,980 in all. Pappas carried 8 of 10 counties, covering 75% of the land, and won 55.9% to 42.1%. Fewest votes: Coos, 12,971; most: Hillsborough, 177,664.
- Governor: Kelly Ayotte (Republican, incumbent) 324,734, Cinde Warmington (Democratic) 296,834, Stephen Villee (Libertarian) 9,630, write-ins 745. Ayotte carried 6 of 10 counties, covering 59% of the land, and won 51.4% to 47.0%.
- U.S. House: 2 of 2 districts, 633,671 votes, both seats Democratic. District 1: Stefany Shaheen against Anthony DiLorenzo; District 2: Maggie Goodlander, Lily Tang Williams and Robbie Mahrou (independent).

Checks that stop the build: 10 counties matching the Census names, once each; each county file has the summary's candidates; each county's towns add up to its TOTALS row, which matches the summary's row for it; the counties add up to the summary's TOTALS; the same towns in every race; every House row is a town or ward from the county files, in one district only, and the two districts reach them all; each district's rows add up to its TOTALS; one Democrat and one Republican in each statewide race, a majority winner, and at least 10 votes in every county.

## What differs from earlier states

- **Projection:** parallels 43.2° and 44.8°, centered on 71.6° W.
- **Excel files read without a library**, and saved through a browser.
- **Parties:** the files mark them with a letter after the name ("d", "r", "l", "c", "i"), mapped to the site's codes.
- **Incumbent:** Ayotte is marked by hand; the files mark none. House incumbents aren't marked.
- **Home map:** labeled "NH", and nudged down so it clears Vermont's "VT", which is nudged up (`mapLabelNudge` in `state.js`, read by `home.js`).

## Gaps

- Not certified: rebuild if recounts or clerks' amendments change the files. The recount schedule wasn't read.
- No precinct view: New Hampshire's towns and wards weren't matched to shapes.
- No By district view: New Hampshire's U.S. House lines weren't looked into.
- Hand-picked text: no tour, flights or history.

## How this was checked (2026-11-20)

- In the browser at desktop width: the page opens on U.S. Senate; the race line reads "won 8 of 10 counties (75% of land) · won the state 55.9–42.1"; the dot view counts 637,980 voters, matching the race; Governor reads "won 6 of 10 counties (59% of land) · won the state 51.4–47.0"; the home page and Sources list New Hampshire, and no home map labels overlap in New England. No console errors.
- **Not checked:** phone width, and the land grid in close-ups.

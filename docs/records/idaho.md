# Idaho: the record

Built 2026-11-08, for the 2026 general election only, and **county-only**: bar view by county and dot view, with no By precinct view or precinct menu. This has the shape of `docs/PIPELINE.md`, Part 7.

**Results are unofficial.** The state's [election calendar](https://voteidaho.gov/event/state-canvass-2/) lists Nov. 24 as the "Deadline for the state board of canvassers to meet and conduct the canvass" (Idaho Code 34-1211). A search summary of Idaho Capital Sun coverage gives the same date, but that article refused a plain request (403), so it wasn't read in full. County boards canvass within nine days of the election (Idaho Code 34-1205, read 2026-11-08), so by Nov. 12. Save the files again after the state canvass, rebuild, and compare.

## Reporting status

**44 of 44 counties and 986 of 986 precincts are reporting**, all marked "Fully Reported". The election's `isOfficialResults` is false, statewide and in every county. The site's data stamp is Nov. 8, 2026, 17:47 UTC, which the summary PDF prints as "Last Updated: 11/08/2026 10:47:11"; the pages say 10:47 AM MT. Nothing in these files counts ballots still outstanding, so the pages use the usual "won" and "with all precincts reporting" wording, as Iowa's do. No statewide race is close.

## Raw files, under `data/raw/id/` (not committed)

Saved 2026-11-08, 10:27 to 10:30 PM Mountain, with plain `curl` and its own user agent.

| What | Path | SHA-256 (first 16) |
|---|---|---|
| [Media Export JSON](https://results.voteidaho.gov/cdn/results/id/export-nov2026.json): read for the map | `results/export-nov2026.json` | `559e402eff2c49c3` |
| Download Reports: Summary and Precinct Results Excel | `results/report-results.xlsx` | `f75ec14780b0205b` |
| Download Reports: Summary Results by Contest | `results/report-summary.pdf` | `58c849a785f7d8ee` |
| The same PDF as text, by `pdftotext -layout` | `results/report-summary.txt` | `f3fbe9fcedc6cf7a` |
| Download Reports: Ballots Cast by Precinct, not read by the build | `results/report-ballots-cast.xlsx` | `bc40a8967ba0e633` |
| The page's data: results and reporting (`api/elections/id/nov2026/data`) | `results/data.json` | `f041fb9eb2ae2b45` |
| Election settings and the official flag (`.../nov2026`) | `results/election.json` | `c2532e8222955f24` |
| County reporting status (`.../nov2026/localities`) | `results/localities.json` | `c7eaed40fb3451d3` |
| Registered voters (`.../nov2026/vr`) | `results/vr.json` | `cdc314537d29a188` |
| Site settings, with the footer's fields (`api/jurisdictions/id`) | `results/jurisdiction.json` | `a34266ab379fd50d` |
| URLs, save time and full hashes, by `scripts/id_results_record.py` | `results/SAVED.json` | not recorded |
| 2020 Census redistricting file ([zip](https://www2.census.gov/programs-surveys/decennial/2020/data/01-Redistricting_File--PL_94-171/Idaho/id2020.pl.zip)) | `census/id2020.pl.zip` | `89345b6d5d12ccde` |
| 2020 census block shapes ([zip](https://www2.census.gov/geo/tiger/TIGER2020/TABBLOCK20/tl_2020_16_tabblock20.zip)) | `census/tl_2020_16_tabblock20.zip` | `b3a9aaf37fff8851` |
| The terms pages below, as saved, and the results app's code | `terms/` | `2bc617dcd36b4124` (legal notices), `1799c59be517b279` (SOS privacy), `1b18271cd9cd84ca` (election results page) |

**Access:** a first script using Python's `urllib` got a 403 from the results site, after these files were saved by `curl`. That wasn't worked around: no user agent was changed, nothing was fetched again, and that script was deleted. `scripts/id_results_record.py` only records and hashes what's saved. **For the rebuild:** try plain `curl` again, and if it's refused, save the files from a browser. No browser was used for this build.

## Why county-only

The owner chose county-only for this state. No precinct shapes were looked for or used, nor anything from the Redistricting Data Hub, the University of Florida Election Lab or the Voting and Election Science Team. The results files do have precinct votes, which are used only as a check.

What this costs: dots use one mix of parties across a county, so they don't show which neighborhoods lean which way.

## Terms of use, read 2026-11-08

This is a reading of the published pages, not legal advice. Nobody at these offices has been asked.

| Source | What it says | What it asks of us |
|---|---|---|
| [SOS privacy policy](https://sos.idaho.gov/privacy-policy/) | No copyright or license wording. The office "maintains this web site as a public service", and business with it "is governed by Idaho's Public Records Law". | Nothing stated |
| [Election results page](https://voteidaho.gov/election-results/), [voteidaho.gov](https://voteidaho.gov/), [sos.idaho.gov](https://sos.idaho.gov/) | No copyright, license or terms wording in the text, and no terms link. The only "Copyright" in the source is a code comment, "Copyright 2024 Element.How". They link to `www.idaho.gov` only as "State of Idaho". | Nothing stated |
| Results site footer | Read from the app's code and settings, not on screen: the state's name, "Election Night Reporting", "powered by" and "enhanced voting" (a link to the vendor). `footerLinkUrl` and `footerLinkText` are null, so there's no terms link. The site says "UNOFFICIAL RESULTS". | Say unofficial, and credit the source. Done. |
| [idaho.gov](https://idaho.gov/) | Footer: "Copyright © 2026. All rights reserved. Idaho.gov" | See the reading below |
| [idaho.gov legal notices](https://idaho.gov/legal-notices/) | "Any trademarks that appear on this site are the property of their respective owners who may or may not be affiliated with, connected to, or sponsored by Idaho.gov." The rest is a copyright agent notice under 17 U.S.C. 512, for people whose own work was infringed. | See the reading below |
| [idaho.gov privacy](https://idaho.gov/privacy-policy/) | Repeats the legal notice. "When you access another site, you are no longer on Idaho.gov, and this Idaho.Gov Portal Privacy Notice will not apply". [Security policy](https://idaho.gov/security-policy/): only the same footer on reuse. | Nothing for the results |
| [Enhanced Voting](https://www.enhancedvoting.com/), the results vendor | Its own site's footer says "© 2026 Enhanced Voting". Its [privacy policy](https://www.enhancedvoting.com/privacy-policy/) doesn't address reusing results. `/terms/`, `/terms-of-service/` and `/terms-of-use/` return 404, and the home page links to no terms. | Nothing found |
| Report spreadsheets' file properties | "This workbook was created with the EPPlus library, licensed to Enhanced Voting under the Polyform Noncommercial license" | See the reading below |
| Census files | Per `docs/PIPELINE.md`, Part 8: no copyright, and cite the Census Bureau. TIGER/Line is a registered trademark, and the homepage carries the statement. | Credit in Sources, with one short TIGER/Line note there |
| us-atlas | ISC license, per npm (`docs/PIPELINE.md`). | Nothing while the site loads it from a CDN |

**Does idaho.gov's notice reach the results site? In this reading, no.** Its words are about "this site" and "Idaho.gov", and its privacy page says leaving Idaho.gov ends its notice. The results are on `results.voteidaho.gov`, published by the Secretary of State, whose sites don't carry that footer or link to those notices, and they name a different site and office. Even on idaho.gov the notice reserves rights without saying anything about election results.

**The spreadsheet's Polyform wording** describes the vendor's license for the software library that made the file, not the state's results, so it wasn't read as a limit on them. It's flagged for the owner because the word "noncommercial" appears in a file saved here. No spreadsheet or EPPlus code is published; it's read only to check the numbers.

**No wording limiting reuse of the results was found**, so the build went ahead.

**Gap in the record:** the results footer wasn't seen on screen, since plain requests get only the app's code. The Idaho Public Records Law manual and the Enhanced Voting pages other than those named weren't read.

## Build, from the repo root

| # | Command | Writes to `data/id/` | SHA-256 (first 16) |
|---|---|---|---|
| 0 | `python scripts/id_results_record.py` (needs `pdftotext`) | `data/raw/id/results/SAVED.json`, `report-summary.txt` | as above |
| 1 | `python scripts/build_id_results.py` | `results-2026.json` | `cda357a85e31d040` |
| 2 | `python scripts/build_cities.py id` | `cities.json` | `5b44a8b833752c2e` |
| 3 | `python scripts/build_precincts.py id` (reads #1) | `blocks.json.gz` | `730e9d930281b7fb` |
| 4 | `python scripts/build_landmask.py id` | `landmask.bin.gz` | `8531a88aa6263da4` |

## Numbers to expect

- 7 races on 44 counties; 986 precincts; 731,511 ballots in the Governor race; 1,063,720 registered voters
- 126 places, the largest Boise City
- 81,879 blocks, 44,980 with adults, 1,376,400 adults
- A 5,138 × 7,855 land grid; 47,751 blocks drawn

| Race | Democrat | Republican | All votes |
|---|---|---|---:|
| Governor | Terri Pickens 230,760 | Brad Little 407,253 | 715,182 |
| Lieutenant Governor | Eric Myricks 256,078 | Scott Bedke 445,955 | 702,033 |
| Secretary of State | Shawn Keenan 228,585 | Phil McGrane 472,356 | 700,941 |
| State Controller | Rakesh Mohan 235,599 | Brandon D Woolf 461,772 | 697,371 |
| State Treasurer | Kevin A Jones 240,215 | Julie A. Ellsworth 455,649 | 695,864 |
| Attorney General | Lori Hickman 283,183 | Raul R. Labrador 421,962 | 705,145 |
| Superintendent of Public Instruction | Becky Sundin Mitchell 243,137 | Debbie Critchfield 429,605 | 697,526 |

Governor's others: John R. Stegner (Independent) 54,210; Paul Sand (Libertarian) 11,543; Pro-Life (Constitution) 9,488, which is that candidate's name on the ballot; uncertified write-ins 1,643; Jacob Burnett (a write-in candidate) 285. Superintendent's other: Teresa Roundy (Constitution) 24,784. The other five races list only two candidates, with no write-in line.

**Left out of the 145 contests:**

- **U.S. Senate has no Democrat:** Jim Risch (Republican) 401,778, Todd Achilles (Independent) 238,342, Natalie M Fleming (Independent) 49,928, Matt Loesby (Libertarian) 20,676. The pages and Sources say so, and the build stops if a Democrat appears.
- House Joint Resolutions 4 and 6, Proposition 1 and the advisory question on House Bill 932 are on every county's ballot, but they're questions rather than contests between candidates.
- The other 133 aren't on every county's ballot: U.S. House, the legislature, judges, and local races and levies.

Checks that stop the build:

- The state calls results unofficial, and every county and all 986 precincts are fully reported, in `localities.json`, `jurisdiction.json`, `data.json` and each race in the export
- County codes and names match the Census file
- In each county and race, candidates plus over votes and under votes equal ballots cast, apart from the rows named below
- Each county's candidates match the spreadsheet's county row, and the spreadsheet's precincts add up to it
- Counties add up to the export's statewide row and `data.json`, candidate by candidate and in total, and each figure appears in the summary PDF's lines for that race
- Each party's counties add up to its candidate, and each county has at least 10 Governor votes and has adults; adults match the Census file's state record

## Exceptions

**1. Ballots cast don't add up in four Governor rows.** `BALLOT_GAPS` in `build_id_results.py` names exactly these, and the build stops if any other row has a gap or one of these changes. They're ballots cast minus over votes, under votes and every candidate's votes:

| County | Gap | Governor write-ins shown |
|---|---:|---|
| Elmore | +16 | 0 and 0 |
| Gooding | +12 | 0 and 0 |
| Caribou | +3 | 0 and 0 |
| Shoshone | −1 | 5 uncertified, 0 Burnett |

Why an exception: these are the state's own figures, and its statewide summary has the same 30-vote gap (715,182 votes + 686 over + 15,613 under = 731,481, against 731,511 ballots). The candidate figures match in the export, the spreadsheet and its precincts, so nothing on the map was changed. Uncounted write-ins in the first three would fit, but that isn't known, and the state wasn't asked. Sources says so for those three. Ballot gaps also appear outside mapped races (Kootenai, Bonneville, Ada and Canyon, in measures and local races), which nothing reads.

**2. The export's precinct lists add up short in two counties.** In Bingham and Blaine, in every mapped race, the Republican's precinct rows in the export add up 2 to 4 votes short of that candidate's county figure. Other candidates' rows add up, and the spreadsheet's precincts match its county figures exactly. The map reads only county figures. `EXPORT_PRECINCT_GAP_COUNTIES` names the two, and the build stops if the list changes.

**Corrected along the way:** counties in the export spell party names their own ways, so the first build put many Democratic and Republican votes in "other" while every check then in place passed. Parties now come from the statewide row, and a check that each party's counties add up to its candidate was added.

## What differs from Iowa

- **Projection:** parallels 43.2° and 47.8°, centered on 114.1° W. The blocks' bounding box is 41.988° to 49.001° and 117.243° to 111.043° W, so the rule of thumb gives 43.157°, 47.832° and 114.143°. `state.js` and `build_landmask.py` use the same values. `middle` and `radiusScaleAt` are both [−114.1, 45.5].
- **Fit:** Idaho is tall, about 0.64 as wide as high. `fitExtent` fills ±500 up and down and about ±320 across, and the pages size the camera to ±510 and ±520 in both directions, so the state fits and leaves room at its sides, the same at any screen shape. This was worked out, not seen.
- **Base race:** Governor, since U.S. Senate isn't mapped. `STATE.defaultRace: 'governor'` opens both pages on it, and `build_precincts.py` puts Governor votes in `blocks.json.gz`. An old `?race=u-s-senate` link falls back to Governor.
- **Party codes:** `DEM`, `REP`, `IND`, `CON`, and `L` and `W` as Texas and Iowa use them. All have names in `app.js`, so none are needed. Burnett counts as `W`, since the site flags him as a write-in. The file doesn't say who is an incumbent, so none are marked.
- **Pages:** `idaho.html` and `idaho-voters.html` are Iowa's pages with their own wording, and they say U.S. Senate isn't mapped. The TIGER/Line note is in Sources only, as the homepage now carries the statement. `STATE.otherVotes` names independents.
- **Time zone:** `meta.resultsUpdated` says MT. Part of northern Idaho is on Pacific time.

## Shared-code changes

- `app.js`: `DEFAULT_RACE = STATE.defaultRace ?? 'u-s-senate'`
- `voters.js`: the base race is `STATE.defaultRace ?? 'u-s-senate'`. Without this, both pages would fail on a state with no U.S. Senate race.
- `scripts/build_precincts.py`: Idaho entries, and `BASE_ID`, `BASE_NAME` and `BASE_OFFICE` in place of the typed U.S. Senate race, the same for other states
- `scripts/build_cities.py`, `scripts/build_landmask.py`, `state.js`: entries only

## Gaps

- **Priest Lake isn't kept empty.** Block 160179506001060 covers nearly all of it, with about 85 square km of water, 0.47 of land, no people and one housing unit, so the grid counts the whole block as lived on. This comes from the method, which draws any block with people or housing. That block has no adults, so no dots are assigned to it, but a dot near its shore could land on the water.
- **Census name:** the largest place shows as "Boise City", the Census's name for Boise, in the labels and the Go to menu. It wasn't changed.
- **Ballots cast in Bear Lake County** vary from 2,442 to 2,444 across statewide races. Unexplained, and it doesn't touch votes.
- **Registered voters:** `vr.json`'s active count is 0 for Bonneville, Elmore and Latah. Only its total column is used, and only in `meta`.
- **Why the two exceptions occur isn't known.** Nobody at the Secretary of State's office was asked.
- **Hand-picked text:** there's no tour, no county flight and no history.

## How this was checked (2026-11-08)

- All four builds were run from the raw files. `results-2026.json`'s shape was checked against Part 6's: 44 rows per race, each adding up, and each party's counties adding up to its candidate.
- All 44 county codes match us-atlas 3.0.1 (`counties-10m.json`), with no differences in name. That agrees with `STATE.countyCount`.
- Every county has adults (fewest: 580, Clark County, FIPS 16033) and at least 10 Governor votes (fewest: 249, Clark County).
- The land grid was decoded and looked at as a whole and in close-ups. **Lake Pend Oreille** and **American Falls Reservoir** are empty in their right shapes, as are spot checks in Lake Coeur d'Alene, Palisades Reservoir, Dworshak Reservoir and Bear Lake. Boise, Sandpoint, Idaho Falls, Pocatello, American Falls and Twin Falls are lived on. A first point for American Falls Reservoir, at 42.85° N, turned out to be on land southeast of the lake in the picture, so the point was off rather than the grid. Priest Lake is the gap above.
- With the changed scripts, Iowa's `blocks.json.gz`, `cities.json` and `landmask.bin.gz`, Oklahoma's `blocks.json.gz` and Texas's `cities.json` were rebuilt into a scratch folder from the main checkout's raw files, and all five match the committed files byte for byte. Other files weren't rebuilt.
- **Not checked:** no page was opened. Browser checking is due after the merge, including the default race, the homepage label and the fit. The whole sequence hasn't been run on a new machine.

## U.S. House, added 2026-11-12

`results-2026.json` now also has the U.S. House as one race: every district added up by county, with each district's own result, built by the same script through `scripts/chamber.py`. Both districts are in the export; counties add up to its statewide rows. The results page draws the districts (By district) on Census outlines, which the build checks against the results. The record for all the states is in [`../PIPELINE.md`](../PIPELINE.md), Part 10.

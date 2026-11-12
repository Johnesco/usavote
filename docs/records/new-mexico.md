# New Mexico: the record

Built 2026-11-08, for the 2026 general election only, and **county-only**: bar view by county and dot view, with no By precinct view or precinct menu. This has the shape of `docs/PIPELINE.md`, Part 7.

**Results are unofficial.** The results site's Election Terminology page says statewide and multi-county results "are declared on the third Tuesday after the election by the state canvassing board", which is Nov. 24, 2026 (computed from that wording), and that this may be delayed by an automatic recount. Save the files again after that, rebuild, and compare.

## Reporting status

**33 of 33 counties and 2,204 of 2,204 precincts are fully reported, with none partial; 731,209 ballots cast of 1,469,718 eligible voters.** The site's stamp reads "Results last updated: 11/6/2026 9:55 AM MT", and its Possible Recounts page reads "No Possible Recounts at This Time." The site doesn't say whether any ballots remain to be counted, so the pages say who won, as Iowa's do, and say the results are unofficial. The `IsReported` field in the county rows is false everywhere, against every other reporting figure; nothing reads it.

## Raw files, under `data/raw/nm/` (not committed)

Saved 2026-11-08, 10:29 PM Mountain, by `scripts/nm_results_save.py`, with plain GET requests and Python's own user agent. Nothing refused, so no browser was used. `results/SAVED.json` lists all 31 files with URLs, sizes and full hashes.

| What | Path | SHA-256 (first 16) |
|---|---|---|
| [Statewide export](https://electionresults.sos.nm.gov/resultsCSV.aspx?text=All&type=SW&map=CTY): totals and precincts reporting | `results/statewide.csv` | `ecadf6329655d0d6` |
| [Federal export](https://electionresults.sos.nm.gov/resultsCSV.aspx?text=All&type=FED&map=CTY): the same | `results/federal.csv` | `0e041d7667e0a1b2` |
| County rows, U.S. Senate (race id 11185) | `results/county-11185.json` | `1d23671772c61773` |
| County rows, Governor and Lt. Governor (11530) | `results/county-11530.json` | `24afdd8053252c03` |
| County rows, Secretary of State (11191) | `results/county-11191.json` | `71b6439a2a95cb9c` |
| County rows, Attorney General (11194) | `results/county-11194.json` | `65d17548b79f3358` |
| County rows, State Auditor (11192) | `results/county-11192.json` | `ce821269cfdd5821` |
| County rows, State Treasurer (11193) | `results/county-11193.json` | `de497572b885b8ef` |
| County rows, Commissioner of Public Lands (11195) | `results/county-11195.json` | `f37f4b63b1e10aec` |
| [Media/Results Exports page](https://electionresults.sos.nm.gov/ResultsMedia.aspx): the stamp and ballots | `results/media.html` | `344560547ed1fc04` |
| [County last updated page](https://electionresults.sos.nm.gov/resultsCountyLastUpdated.aspx) | `results/county-updated.html` | `7144844c13fd5184` |
| [Voter turnout page](https://electionresults.sos.nm.gov/VoterTurnoutDetails.aspx?map=TURN) | `results/turnout.html` | `24efd4cb3527c1be` |
| [Possible Recounts page](https://electionresults.sos.nm.gov/ResultsSW.aspx?type=RECOUNT) | `results/recounts.html` | `0df30dbabec94ae0` |
| [Election Terminology page](https://electionresults.sos.nm.gov/resultsElectionTerminology.aspx), not read by the build | `results/terminology.html` | `1a89c4e075eaea05` |
| [Statewide](https://electionresults.sos.nm.gov/resultsSW.aspx?type=SW&map=CTY) and [Federal](https://electionresults.sos.nm.gov/resultsSW.aspx?type=FED&map=CTY) results pages, for each contest's ids | `results/statewide.html`, `results/federal.html` | `85b6115282fe2841`, `53fcf641a066a1f0` |
| [Secretary of State's disclaimer](https://www.sos.nm.gov/disclaimer/) | `results/disclaimer.html` | `6b2bf1f3386fca88` |
| 2020 Census redistricting file ([zip](https://www2.census.gov/programs-surveys/decennial/2020/data/01-Redistricting_File--PL_94-171/New_Mexico/nm2020.pl.zip)) | `census/nm2020.pl.zip` | `77133ba4bb2fb2c2` |
| 2020 census block shapes ([zip](https://www2.census.gov/geo/tiger/TIGER2020/TABBLOCK20/tl_2020_35_tabblock20.zip)) | `census/tl_2020_35_tabblock20.zip` | `cf3a71e48ec3bcbd` |

The other 12 saved files are county rows for contests that aren't mapped (U.S. House, the Court of Appeals, retention votes, amendments and bond questions).

**Where the county rows come from:** the survey's question is answered: the CSV exports have **no county rows**, only statewide totals (`AreaNum` is blank, and changing `map=` returns the same file). Each contest's "County Level" export button is a form postback, which wasn't used. The rows were read instead from the JSON service each contest's "County Results" button reads, as `https://nmresultswebservice.azurewebsites.us/NMResultsAjax.svc/GetMapData?type=<SW or FED>&category=CTY&raceID=<race id>&osn=<office number>&county=0&party=0`, named in `maps/static/js/BuildCountyMap.js` on the results site. The service's root returns a 403, but this address returned 200 to a plain request. The `azurewebsites.net` address the survey couldn't reach appears only in the page's share links.

## Why county-only

Per the owner's instruction for this state. The results site has precinct-level votes, but no statewide precinct shapes were looked for or used, and nothing was taken from the Redistricting Data Hub, the University of Florida Election Lab or the Voting and Election Science Team.

What this costs: dots use one mix of parties across a county, so they don't show which neighborhoods lean which way.

## Terms of use, read 2026-11-08

This is a reading of the published pages, not legal advice. **No wording limiting reuse of results was found,** so the build went ahead.

| Source | What it says | What it asks of us |
|---|---|---|
| Results pages (`electionresults.sos.nm.gov`): home, statewide, federal, exports, terminology, county updated, recounts, turnout | No copyright notice, license or terms on any of them. They say "Unofficial Results", and the terminology page says "All election results are unofficial until the appropriate canvassing board has completed its duties". | Nothing stated. The site credits the Secretary of State and says results are unofficial. |
| [Disclaimer](https://www.sos.nm.gov/disclaimer/) (Secretary of State's main site) | A warning about accuracy: "these pages and our databases may contain inadvertent errors". The footer reads "@ 2012 – 2026 New Mexico Secretary of State", with no reuse limits. | Nothing on reuse |
| Census files and TIGER/Line | As in `docs/PIPELINE.md`, Part 8: U.S. Government works have no copyright. The Bureau asks to be cited, and the trademark statement is on the homepage. | Credit and one short TIGER/Line note, both in Sources |
| us-atlas | ISC license, per npm (`docs/PIPELINE.md`). It redistributes Census boundaries. | Nothing while the site loads it from a CDN |

**Gap in the record:** not read were the rest of the Secretary of State's main site, New Mexico's public records law, or any terms from the results site's vendor. None appeared on the pages read.

## Build, from the repo root

| # | Command | Writes to `data/nm/` | SHA-256 (first 16) |
|---|---|---|---|
| 0 | `python scripts/nm_results_save.py` | (the raw results; the site's files may have changed since) | |
| 1 | `python scripts/build_nm_results.py` | `results-2026.json` | `d7d56d1acec62178` |
| 2 | `python scripts/build_cities.py nm` | `cities.json` | `29ffcc00cad00be2` |
| 3 | `python scripts/build_precincts.py nm` (reads #1) | `blocks.json.gz` | `38a2012b4787b710` |
| 4 | `python scripts/build_landmask.py nm` | `landmask.bin.gz` | `0aebcc190f32e3f7` |

## Numbers to expect

- 7 races on 33 counties; 2,204 precincts; 731,209 ballots; 1,469,718 eligible voters
- 81 places, the largest Albuquerque
- 107,215 blocks, 55,448 with adults, 1,638,989 adults
- A 5,758 × 6,355 land grid; 58,300 blocks drawn

| Race | Democrat | Republican | All votes |
|---|---|---:|---:|
| U.S. Senate | Ben R Lujan 458,756 | Larry E Marker 266,434 | 725,190 |
| Governor and Lt. Governor | Deb Haaland and Stephanie Garcia Richard 416,176 | Greggory D Hull and David M Gallegos 309,436 | 725,612 |
| Secretary of State | Amanda López Askin 436,638 | Ramona L Goolsby 279,965 | 716,603 |
| Attorney General | Raul Torrez 453,938 | Samuel Isaiah Kane Sr 266,392 | 720,330 |
| State Auditor | Joseph M Maestas 431,376 | Joshua James Ryan Lawrence 281,348 | 712,724 |
| State Treasurer | Laura M Montoya 426,792 | James F Ellison 286,964 | 713,756 |
| Commissioner of Public Lands | Juan De Jesus Sanchez III 433,889 | Michael Jack Perry 281,007 | 714,896 |

Every mapped race has only these two candidates, so "other" is 0 everywhere.

**Left out, on the ballot statewide:** Court of Appeals Position 1 (Kris Houghton, a Democrat, with no Republican), three retention votes, four constitutional amendments and three bond questions. U.S. House, in the federal export, isn't statewide.

Checks that stop the build:

- All 33 counties are fully reported with none partial, by the county rows and the county page, and each mapped race reads 2,204 of 2,204 in the export; the page says "Unofficial Results" and lists no possible recounts
- Counties on the site match the Census names, with accents and punctuation ignored: the site writes "Dona Ana" and the Census "Doña Ana"
- In each county and race, the candidates are the export's, votes are whole numbers rather than hidden, each candidate's votes agree with the site's percentage of the candidates' sum, and votes don't exceed ballots
- Counties add up to the export, candidate by candidate
- Precinct ballots on the turnout page add up to the page's 731,209; each county has at least 10 U.S. Senate votes and has adults; adults match the Census file's state record

The county rows carry no county total of their own, so the percentage is the only check of a candidate sum against the site's figure.

## What differs from Iowa

- **Projection:** parallels 32.3° and 36.1°, centered on 106° W, with `middle` and `radiusScaleAt` at [-106, 34.2]. The blocks' bounding box is 31.332° to 37.000° and 109.050° to 103.002° W, so the rule of thumb gives 32.277°, 36.055° and 106.026°. `state.js` and `build_landmask.py` use the same values.
- **Results source:** JSON county rows checked against CSV statewide exports, as above.
- **Candidates:** the file is in capitals, so names are title-cased by rule and keep the file's spelling, without accents it doesn't have ("Ben R Lujan", "Juan De Jesus Sanchez III"). One surname is set by hand, López Askin, because the rule would have cut it to Askin. The file doesn't say who is an incumbent, so none are marked. Party codes are `DEM` and `REP` only.
- **Pages:** `new-mexico.html` and `new-mexico-voters.html` are Iowa's pages with their own wording. Per the owner's rule for this build, the TIGER/Line statement is in Sources only, not near the top or in the How? box.
- **Write-ins:** `STATE.votesCounted` says these results list no write-ins. Per the terminology page, New Mexico counts them only for declared write-in candidates.
- **No `mapLabel`:** estimated by width, "New Mexico" fits inside the state on the homepage map. That wasn't seen in a browser.
- **Time zone:** `meta.resultsUpdated` says MT.

## Gaps

- **The land grid check over water partly failed.** Navajo Lake, Conchas, Ute and Heron or El Vado appear empty in their right shapes. **Most of Elephant Butte Lake doesn't:** its main block (350519624011160, 108 sq km of water, 0.53 of land) has 5 people and 4 housing units in the Census file, so 99.6% of its cells are drawn as lived on. So is part of Caballo Lake (350519624021187, 16.9 sq km of water, 8 people, 1 housing unit); the other part of Caballo is empty. Dots from nearby blocks can land on those waters. It's a result of the method, so no exception was written; a fix would be a change to shared code, such as skipping blocks that are nearly all water.
- **The grid is coarse in rural areas,** where one block can be very large: 1,219 lived-on blocks are over 25 sq km, 85,705 sq km in all, and 538 of them have fewer than 5 people. The largest is 1,052 sq km. White Sands shows as a large empty area. Such blocks hold few adults, so few dots spread there.
- **Vote suppression:** the site shows an asterisk where "fewer than 5 voters" cast a ballot for a race in a precinct. None appears in a mapped race's county rows, one appears in U.S. House District 2's, and the build stops if one reaches a mapped race. Whether suppressed precinct votes are in the county and state totals wasn't tested, though the two agree.
- **Hand-picked text:** there's no tour, no county flight and no history.

## How this was checked (2026-11-08)

- All builds were run from the raw files. `results-2026.json`'s shape was checked against Part 6's: 33 rows per race, each adding up.
- All 33 county codes match us-atlas 3.0.1 (`counties-10m.json`), with no differences in name, including Doña Ana. That agrees with `STATE.countyCount`.
- Every county has adults (fewest: 561) and at least 10 U.S. Senate votes (fewest: 375). "Española" kept its accent in `cities.json`.
- The land grid was decoded and looked at as a whole, around Elephant Butte and Caballo, around Navajo Lake and around Conchas, with the water blocks' outlines drawn over two of them, and each block's internal point was tested. 58,284 of 58,300 lived-on blocks' points are on lived-on cells. Empty blocks read 11,435 of 48,915, and the outlines show why for the lakes tested: neighbors' edges light the cells along a shoreline, so narrow arms read 25% to 35% lit.
- With the changed scripts, Iowa's `cities.json`, `blocks.json.gz` and `landmask.bin.gz`, Oklahoma's `cities.json` and Texas's `cities.json` were rebuilt in a scratch folder from the main checkout's raw files, and all five match the committed files byte for byte. Other states' files weren't rebuilt; the changes to the scripts only add New Mexico's entries.
- **Not checked:** no page was opened. Browser checking is due after the merge. The whole sequence hasn't been run on a new machine.

## U.S. House, added 2026-11-12

`results-2026.json` now also has the U.S. House as one race: every district added up by county, with each district's own result, built by the same script through `scripts/chamber.py`. The 3 districts' totals are in `federal.csv` and their county rows in `county-11186.json` to `county-11188.json`. **One hidden figure:** the site shows an asterisk for Gabriel Vasquez in Chaves County's part of District 2, where fewer than 5 voters cast a ballot. That figure is left out of Chaves County's row and still counted in District 2's total, which the state publishes; the build stops if more than one figure per candidate or 5 or more votes are missing. The state's own total and percentage give the figure away, so this follows its intent, not a guarantee. The results page draws the districts (By district) on Census outlines, which the build checks against the results. The record for all the states is in [`../PIPELINE.md`](../PIPELINE.md), Part 10.

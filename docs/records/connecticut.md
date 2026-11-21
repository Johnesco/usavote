# Connecticut: the record

Built 2026-11-20, for the 2026 general election only, and **county-only**: bar view by county and dot view, with no By precinct or By district view. This has the shape of `docs/PIPELINE.md`, Part 7.

**Towns added up by county.** Connecticut reports by town. The State's results list each town's county, and the 2020 Census files still have the 8 counties (the state switched to planning regions in 2022), so they match us-atlas's 2017 county shapes. Connecticut has had no county government since 1960; the counties are used here only as map areas.

**Six races.** Governor and Lieutenant Governor, Secretary of the State, Treasurer, Comptroller and Attorney General, each between a Democrat and a Republican, and U.S. House, the 5 district races added up by county (`scripts/chamber.py`). There's no U.S. Senate race this year, so the page opens on Governor. Five towns are split between House districts (Glastonbury, Middletown, Shelton, Torrington, Waterbury); the State reports each part, so each district's votes stay in the right county.

**Cross-endorsement.** A candidate nominated by more than one party appears on each party's line. The build adds a person's lines together and gives them the major party among them: Lamont's Democratic 742,276 and Working Families 29,813 make 772,089, and Fazio's Republican 496,444 and Independent Party 27,761 make 524,205, which match the State's own combined totals.

**Unofficial results.** The owner asked on 2026-11-20 to check Connecticut, then to build it with New Hampshire. Every town reads "Unofficial Results".

## Raw files, under `data/raw/ct/` (not committed)

Saved 2026-11-20 from the Election Night Reporting site's data files, `https://ctemspublic.tgstg.net/ng-app/data/election/108/55775/<name>.json` (election 108, data version 55775). The version went from 55774 to 55775 while they were being saved, so all were saved again from 55775.

| What | Path | SHA-256 (first 16) |
|---|---|---|
| Data version (`{"Version":55775}`) | `results/Version.json` | `d0f1df24c9018558` |
| Towns, counties, offices, parties, candidates; Last-Modified Nov. 20, 2026, 20:00:00 GMT | `results/Lookupdata.json` | `1166e746d9c2391e` |
| Each town's votes by office and ballot line; Last-Modified Nov. 20, 2026, 23:18:11 GMT (as are the next three) | `results/townVotes_Electiondata.json` | `3a4d29736402b856` |
| Statewide totals by ballot line | `results/stateVotes_Electiondata.json` | `c573690c20e32eec` |
| Combined totals for candidates on more than one line | `results/candidateGrouping_Electiondata.json` | `22710106263ff2e3` |
| Each town's reporting status | `results/townStatus_Electiondata.json` | `054333b7f8b04656` |
| Each file's response headers | `results/*.headers.txt` | see the files |
| When they were saved (UTC) | `results/saved-at.txt` | see the file |
| 2020 Census redistricting file ([zip](https://www2.census.gov/programs-surveys/decennial/2020/data/01-Redistricting_File--PL_94-171/Connecticut/ct2020.pl.zip)) | `census/ct2020.pl.zip` | `c4a2d42a79c52de1` |
| 2020 census block shapes ([zip](https://www2.census.gov/geo/tiger/TIGER2020/TABBLOCK20/tl_2020_09_tabblock20.zip)) | `census/tl_2020_09_tabblock20.zip` | `a935a5a85717389d` |

The owner approved these downloads by name on 2026-11-20 ("Yes, download all").

## Terms of use, read 2026-11-20

This is a reading of the published pages, not legal advice. Nobody at the Secretary of the State's office has been asked.

| Source | What it says | What it asks of us |
|---|---|---|
| Secretary of the State site ([portal.ct.gov/sots](https://portal.ct.gov/sots)) | Footer: "© 2026 CT.gov \| Connecticut's Official State Website", linking the portal's Disclaimer and Policies | See below |
| [CT.gov: Disclaimer](https://portal.ct.gov/policies/disclaimer), read in full | No warranty for documents on the server. "Data Distribution and Statement of Liability": the State isn't liable for "improper or incorrect use of the data", and "It is the responsibility of the data user to use the data appropriately"; the disclaimer "applies both to individual use of the data and aggregate use with other data". Reproducing the State Arms and Seal needs the Secretary of the State's permission (C.G.S. 3-106a). The CT.gov logo is copyrighted and may not be reproduced without permission. | **Don't use the State Seal or the CT.gov logo.** Otherwise nothing limits reuse |
| [CT.gov: State Privacy Policy](https://portal.ct.gov/Policies/State-Privacy-Policy), read in full | Privacy, cookies and security. It notes agencies may adopt their own policies. Nothing on reuse. | Nothing for reuse |
| Results site, [ctemspublic.tgstg.net](https://ctemspublic.tgstg.net/#/home) ("Connecticut Secretary of the State, Election Night Reporting") | No terms or copyright line | Nothing stated |

**The reading:** **silent**, the same standing as Vermont and West Virginia, and leaning toward use: the portal's disclaimer is written for people using the State's data, and limits only the seal and the portal's logo. No Secretary of the State terms of its own were found.

## Results, as read before building, 2026-11-20

- **Complete, unofficial.** "UNOFFICIAL RESULTS", last updated Nov. 20, 2026, 5:11 PM; 169 of 169 towns completely reported; 774 of 774 precincts. Certification date not looked up.
- Statewide races: Governor and Lieutenant Governor, Secretary of the State, Treasurer, Comptroller, Attorney General. No U.S. Senate race. **Governor**, read off the summary: Ned Lamont and Susan Bysiewicz 742,276 (Democratic line) and 29,813 (Working Families line); Ryan Fazio and Matt Corey 496,444 (Republican) and 27,761 (Independent Party); write-ins.
- U.S. House: 5 districts.
- **Cross-endorsement:** candidates appear on more than one party's line. A build would add each candidate's lines together, and say so.
- **By town.** Results are by town; a build adds them up by county, as Vermont's and Rhode Island's did. The 2020 Census files still have Connecticut's 8 counties (the state switched to planning regions in 2022), so they match us-atlas's 2017 county shapes. The site has "Select Town" and "Reports" tabs; downloads weren't looked at.

## Build, from the repo root

| # | Command | Writes to `data/ct/` | SHA-256 (first 16) |
|---|---|---|---|
| 1 | `python scripts/build_ct_results.py` | `results-2026.json` | `6997e59fda57da4f` |
| 2 | `python scripts/build_cities.py ct` | `cities.json` | `0aaf2fcc37a5f66a` |
| 3 | `python scripts/build_precincts.py ct` (reads #1) | `blocks.json.gz` | `6db2b73580d72c77` |
| 4 | `python scripts/build_landmask.py ct` | `landmask.bin.gz` | `1f19fc20bd5ea6a2` |

## Numbers to expect

- 6 races on 8 counties; 169 of 169 towns, every one "1 of 1 (100.00%)" and "Unofficial Results"
- 43 places, the largest Bridgeport
- 49,926 blocks, 41,854 with adults, 2,869,227 adults
- A 1,640 × 1,238 land grid; 42,078 blocks with people or housing
- Governor: Ned Lamont / Susan Bysiewicz (Democratic, Working Families) 772,089, Ryan Fazio / Matt Corey (Republican, Independent Party) 524,205, write-ins 64. Lamont carried 6 of 8 counties, covering 70% of the land, and won 59.6% to 40.4%. Fewest votes: Windham, 40,907.
- Secretary of the State: Stephanie Thomas 807,882 (three lines), Peter Lumaj 465,617, write-ins 19. Treasurer: Erick Russell 766,994, Fred Wilms 505,561. Comptroller: Sean Scanlon 800,401, Jennifer S. Tooker 470,795. Attorney General: William Tong 806,504, John Bolton 469,518. Treasurer, Comptroller and Attorney General had no write-ins.
- U.S. House: 5 of 5 districts, 1,283,816 votes, all 5 seats Democratic.

Checks that stop the build: 8 counties matching the Census names, once each; all 169 towns in a county, every one fully reported; for every office, the towns add up to the State's totals, line by line; candidates on more than one line add up to the State's combined totals, and every candidate with more than one line is in the State's grouping; every line's party is a known one; one Democrat and one Republican in each statewide race, a majority winner, and at least 10 votes in every county; every town votes in at least one House district.

## What differs from earlier states

- **Projection:** parallels 41.2° and 41.9°, centered on 72.7° W.
- **Ballot lines merged:** the first state where one person is on several lines. The State's combined totals were used as a check, not as the source.
- **Tickets:** Governor and Lieutenant Governor run together; names are written "Ned Lamont / Susan Bysiewicz", as South Carolina's are. Last names come from the State's own field.
- **Incumbents:** marked by hand (the files mark none): the five statewide officers, elected in 2022, and Representatives Courtney, DeLauro, Himes and Hayes. District 1 has no incumbent on the ballot.
- **Base race for dots:** Governor (`scripts/build_precincts.py`), as for states with no U.S. Senate race.
- **Home map:** labeled "CT".

## Gaps

- Unofficial: rebuild after the state canvass (date not looked up).
- No precinct view: the site has town and precinct reports, not looked at for shapes.
- No By district view: Connecticut's U.S. House lines weren't looked into.
- Hand-picked text: no tour, flights or history.

## How this was checked (2026-11-20)

- In the browser at desktop width: the page opens on Governor; the race line reads "won 6 of 8 counties (70% of land) · won the state 59.6–40.4"; the dot view counts 1,296,358 voters, matching the race; U.S. House in 3D says "5 districts, every one added up by county"; the home page and Sources list Connecticut. No console errors.
- **Not checked:** phone width, and the land grid in close-ups.

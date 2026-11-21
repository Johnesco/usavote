# Delaware: the record

Built 2026-11-21, for the 2026 general election only, and **county-only**: bar view by county and dot view, with no By precinct or By district view. This has the shape of `docs/PIPELINE.md`, Part 7.

**Only three counties.** New Castle, Kent and Sussex. Every race went Democratic in all three, so the flat map is one color; the 3D and dot views carry more. The results page also reports Wilmington and the rest of New Castle separately; the build checks that they add up to New Castle and uses the county.

**Five races.** U.S. Senate, U.S. House (one at-large seat, so it's a statewide race, as in Vermont), Attorney General, Auditor of Accounts and State Treasurer. Legislative, county and other local races aren't here.

**Official results.** The results page reads "OFFICIAL RESULTS", data as of Nov. 10, 2026, with all 530 election districts reporting, so `state.js` sets `official: true` and no rebuild is due. The owner asked on 2026-11-21 to build it.

**Write-ins aren't counted.** The Department posts them in a separate "Official Write-In Votes Report", which wasn't saved. The pages say so (`twoCandidates` and `votesCounted` in `state.js`).

## Raw files, under `data/raw/de/` (not committed)

Saved 2026-11-21 with `curl`; the site serves them to scripts. The results page builds its tables from these JSON files (found in `results/enr/js/results.js`).

| What | Path | SHA-256 (first 16) |
|---|---|---|
| The results page's "By County" data ([JSON](https://elections.delaware.gov/results/enr/Election_ByCountyWithWilmington_ID_GE2026.json), 45 KB), Last-Modified Nov. 10, 2026, 19:16:32 GMT | `results/Election_ByCountyWithWilmington_ID_GE2026.json` | `0cb6da959b70aa85` |
| The results page's statewide totals ([JSON](https://elections.delaware.gov/results/enr/Election_StatewideResults_ID_GE2026.json), 65 KB), Last-Modified Nov. 10, 2026, 19:16:30 GMT | `results/Election_StatewideResults_ID_GE2026.json` | `367f31e3cefd0735` |
| Delaware Open Data Portal, Official Election Results by Office ([CSV](https://data.delaware.gov/api/views/4hbv-7brf/rows.csv?accessType=DOWNLOAD), License: Public Domain), every election since 2023, Last-Modified Nov. 10, 2026, 20:22:48 GMT | `results/official-results-4hbv-7brf.csv` | `4973b475d7fab55f` |
| Their response headers | `results/*.headers.txt` | see the files |
| When they were saved (UTC) | `results/saved-at.txt` | see the file |
| 2020 Census redistricting file ([zip](https://www2.census.gov/programs-surveys/decennial/2020/data/01-Redistricting_File--PL_94-171/Delaware/de2020.pl.zip)) | `census/de2020.pl.zip` | `2d7743cc442574dc` |
| 2020 census block shapes ([zip](https://www2.census.gov/geo/tiger/TIGER2020/TABBLOCK20/tl_2020_10_tabblock20.zip)) | `census/tl_2020_10_tabblock20.zip` | `de20500a99debb0d` |

The owner approved these five downloads by name on 2026-11-21 ("Yes, download all").

## Terms of use, read 2026-11-20

This is a reading of the published pages, not legal advice. Nobody at the Department of Elections has been asked.

| Source | What it says | What it asks of us |
|---|---|---|
| Department of Elections site ([elections.delaware.gov](https://elections.delaware.gov/)) | No copyright line found. Its footer's "Help", "Privacy", "Cookies" and "Accessibility" links go nowhere (`#`). | Nothing found |
| [Delaware.gov: Privacy Policy](https://delaware.gov/privacy-policy/), read in full, the portal's only policy link | Privacy, cookies, a "Terms of Service" section about sharing visitors' information, and third-party add-ins. Nothing on reusing state information. Footer: "©MMXVIII Delaware.gov" | Nothing for reuse |
| [Delaware Open Data Portal: Official Election Results by Office](https://data.delaware.gov/d/4hbv-7brf), its "About this Dataset" | "Data Provided by Department of Elections"; updated Nov. 10, 2026; **"License: Public Domain"**; source link `https://elections.delaware.gov/results`. One row per candidate per race: statewide totals by vote type, **no county column**. The results page's "Download CSV Report" button is this dataset. | Nothing: public domain |
| Results page, [GE2026](https://elections.delaware.gov/results/enr/GE2026.html) | No terms | Nothing stated |

**The reading:** **public domain for the statewide totals, silent for the county figures.** The State publishes its official results by office under a public-domain license. The county figures appear only on the results page's "By County" view, which states no terms. That's at least the standing of Vermont and West Virginia, and the closest to permission of any state read so far after New Jersey.

## Results, as read before building, 2026-11-20

- **Official.** The results page reads "OFFICIAL RESULTS", data as of Nov. 10, 2026, 12:49 PM; 530 of 530 election districts reporting; each county's absentee tabulation done. 384,862 votes cast.
- Statewide races between a Democrat and a Republican, read off the page: **U.S. Senate**, Chris Coons (Democratic) 240,587, Michael "Dr. Mike" Katz (Republican) 137,837; **U.S. House** (one at-large seat), Sarah McBride 243,687, Joseph "Dr. Joe" Arminio 135,016; **Attorney General**, Kathy Jennings 240,626, David C. "Dave" Graham 137,516; **Auditor of Accounts**, Lydia York 227,685, April Callaway 130,928, and an Independent; **State Treasurer** (not read).
- **By county** (three: New Castle, Kent, Sussex): U.S. Senate, Coons 144,910 / 36,437 / 59,240, Katz 54,919 / 27,023 / 55,895. Coons carried all three.
- The page also has "By Election District" results, Delaware's precincts. Whether they match the Census's 2020 voting districts wasn't looked at.

## Build, from the repo root

| # | Command | Writes to `data/de/` | SHA-256 (first 16) |
|---|---|---|---|
| 1 | `python scripts/build_de_results.py` | `results-2026.json` | `ed74cb07eb4639c9` |
| 2 | `python scripts/build_cities.py de` | `cities.json` | `0550aa194dd7b250` |
| 3 | `python scripts/build_precincts.py de` (reads #1) | `blocks.json.gz` | `3043c80ecee2c50e` |
| 4 | `python scripts/build_landmask.py de` | `landmask.bin.gz` | `9bb572756d548728` |

## Numbers to expect

- 5 races on 3 counties; 530 of 530 election districts, official, data as of Nov. 10, 2026; 124 rows for the 2026 general election in the public-domain file
- 41 places, the largest Wilmington
- 20,198 blocks, 15,222 with adults, 783,543 adults
- A 711 × 1,555 land grid; 15,399 blocks with people or housing
- U.S. Senate: Chris Coons (Democratic, incumbent) 240,587, Michael "Dr. Mike" Katz (Republican) 137,837. By county, Coons 144,910 / 36,437 / 59,240 and Katz 54,919 / 27,023 / 55,895 in New Castle, Kent and Sussex.
- U.S. House: Sarah McBride (incumbent) 243,687, Joseph "Dr. Joe" Arminio 135,016. Attorney General: Kathy Jennings (incumbent) 240,626, David C. "Dave" Graham 137,516. Auditor of Accounts: Lydia York (incumbent) 227,685, April Callaway 130,928, Austin Cassidy (Independent Party of Delaware) 18,380. State Treasurer: Ted Lauzen 235,779, Michael Ramone 141,812.
- Democrats carried all 3 counties in every race.

Checks that stop the build: the Census's 3 counties are Kent, New Castle and Sussex; each race's candidates are the same in the county file, the statewide file and the public-domain CSV, with the same parties; for every candidate, New Castle, Kent and Sussex add up to the county file's State figure, which equals both the statewide file's total and the CSV's; Wilmington plus the rest of New Castle equal New Castle; the statewide file says "OFFICIAL RESULTS" with every election district reported; one Democrat and one Republican per race, and a majority winner.

## What differs from earlier states

- **Projection:** parallels 38.7° and 39.6°, centered on 75.4° W.
- **Checked against a public-domain file:** the open-data portal's results, which the State licenses as public domain, confirm every statewide total.
- **Names:** the files write names in capitals; the build writes them in ordinary case (`MICHAEL "DR. MIKE" KATZ` becomes `Michael "Dr. Mike" Katz`, `MCBRIDE` becomes `McBride`).
- **Authority wording:** "the Delaware elections department", since the pages add "'s" and the department's name ends in "Elections".
- **Incumbents:** marked by hand (the files mark none): Coons, McBride, Jennings and York.
- **Home map:** labeled "DE".

## Gaps

- Write-ins aren't counted: they're in a separate report.
- No precinct view: the results page has "By Election District" results (`Election_ByElectionDistrict_ID_GE2026.json`, not saved), Delaware's precincts. Whether they match the Census's 2020 voting districts wasn't looked at. With only three counties, this is the view that would show the most.
- Hand-picked text: no tour, flights or history.

## How this was checked (2026-11-21)

- In the browser at desktop width: the page opens on U.S. Senate, official, "Coons won 3 of 3 counties"; the two-candidate note reads "Two candidates on the ballot. Write-in votes are in a separate report and aren't counted here."; the Auditor dot view counts 376,993 voters, matching the race; U.S. House and 3D load; the home page lists Delaware and its "DE" label overlaps nothing. No console errors.
- **Not checked:** phone width, and the land grid in close-ups.

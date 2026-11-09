# Iowa: the record

Built 2026-11-08, for the 2026 general election only, and **county-only**: bar view by county and dot view, with no By precinct view or precinct menu. This has the shape of `docs/PIPELINE.md`, Part 7.

**Results are unofficial.** Iowa Code 50.24 has county supervisors canvass on the first Tuesday after the election (Nov. 10, 2026), and 50.38 has the state canvass no later than 27 days after it (Nov. 30, 2026). Both sections were read on 2026-11-08. The county canvass can add late absentee ballots and write-ins, so save the files again after the state canvass, rebuild, and compare.

## Reporting status

**99 of 99 counties and 1,659 of 1,659 precincts are reporting.** No county is marked certified yet.

One fetched copy of `summary.json` showed 95 of 99, and the saved copy does too. That field is out of step with everything else, and the votes aren't:

| File | Says |
|---|---|
| `status.json` | All 99 counties "completely reported" (code 4); precincts processed equal total in every county; 1,659 in all |
| `summary-summary.csv` | 99 of 99 for all 11 statewide contests |
| `sum.json` | 99 of 99 for all 11 statewide contests |
| `details.json` | 1,659 of 1,659 for all 11 statewide contests, county by county |
| The results page | 99/99 and 1659/1659, read in the browser on the save date |
| `summary.json` | **95 of 99** for all 11 statewide contests, and lower counts in some district contests, with votes identical to `sum.json` in all 274 contests |

Why `summary.json` says 95 isn't known, and nobody at the Secretary of State's office was asked. The build ignores that one field, and stops if that file's votes ever differ from `sum.json`.

## Raw files, under `data/raw/ia/` (not committed)

Saved 2026-11-08, 10:26 PM Central. Results site stamp: Nov. 4, 2026, 12:25:40 PM CST; data version 385624; marked "Unofficial Results".

| What | Path | SHA-256 (first 16) |
|---|---|---|
| [Results site](https://electionresults.iowa.gov/IA/127077/web.345435/#/reporting): everything below, as saved from the browser | `results/browser/ia-385624-bundle.json` | `a83bf50e05682b9d` |
| Detail TXT report, as downloaded (`/IA/127077/385624/reports/detailtxt.zip`) | `results/detailtxt.zip` | `84385a403ee38b74` |
| The same, unzipped: read for the map | `results/detailtxt-detail.txt` | `d22ae7d258f3e0c2` |
| Summary CSV report, as downloaded (`reports/summary.zip`) | `results/summary.zip` | `12289554f5ff85e9` |
| The same, unzipped: statewide totals | `results/summary-summary.csv` | `b9b5d95a8a451fcd` |
| Statewide contests, as the site's JSON (`json/sum.json`) | `results/sum.json` | `de0b66e1b43c249b` |
| The same again (`json/en/summary.json`) | `results/summary.json` | `cc6254e740744989` |
| Contest by county (`json/details.json`) | `results/details.json` | `ca6893054be059b3` |
| County by contest (`json/ALL.json`) | `results/ALL.json` | `5335ecf52c37d0c2` |
| County reporting status (`json/status.json`) | `results/status.json` | `78ffefe721382a06` |
| Page settings, with the "last updated" stamp (`json/en/electionsettings.json`) | `results/electionsettings.json` | `a7a3a589e1d91ebb` |
| Contest menu (`json/en/nav.json`), not read by the build | `results/nav.json` | `a4a1cea482c2b6d6` |
| What was saved and when, written by the unpacker | `results/SAVED.json` | not recorded |
| 2020 Census redistricting file ([zip](https://www2.census.gov/programs-surveys/decennial/2020/data/01-Redistricting_File--PL_94-171/Iowa/ia2020.pl.zip)) | `census/ia2020.pl.zip` | `c55e8276080b6844` |
| 2020 census block shapes ([zip](https://www2.census.gov/geo/tiger/TIGER2020/TABBLOCK20/tl_2020_19_tabblock20.zip)) | `census/tl_2020_19_tabblock20.zip` | `8c63755fc5b6c825` |

**How the results were saved:** plain scripts get a 403 from this site, and that wasn't worked around. `scripts/ia_results_save.js` ran inside a normal tab of the owner's Chrome, through Claude in Chrome, with no change of user agent, and read the files the page itself reads. Chrome let through only the first of several separate downloads in a tab, and clicks on the page's own Download links saved nothing after that, so the script puts all the files in one JSON bundle (base64, with each file's SHA-256) and saves that once from a new tab. `scripts/ia_results_unpack.py` writes them out and checks each hash. The zip hashes match those the script printed for the separate downloads.

## Why county-only

Per the owner's review: the Secretary of State's precinct shapes carry no license, and the Voting and Election Science Team's 2020 layer has clear terms but is old. Neither was downloaded or used, nor anything from the Redistricting Data Hub, the University of Florida Election Lab or behind a login.

What this costs: dots use one mix of parties across a county, so they don't show which neighborhoods lean which way.

## Terms of use, read 2026-11-08

This is a reading of the published pages, not legal advice.

| Source | What it says | What it asks of us |
|---|---|---|
| Results (Iowa Secretary of State) | No license found. The owner chose to treat them like Texas's and Oklahoma's. | Nothing stated. The site credits the Secretary of State and says results are unofficial. |
| Census files | [TIGER2020PL technical documentation](https://www2.census.gov/geo/pdfs/maps-data/data/tiger/tgrshp2020pl/TGRSHP2020PL_TechDoc.pdf), section 1.2: copyright protection isn't available for U.S. Government work (17 U.S.C. 105), so census materials may be reproduced freely. | Section 1.2 asks that the Census Bureau be cited as the source. Done in Sources. |
| TIGER/Line files | Same documentation, section 1.1: TIGER/Line is a registered trademark that can't be used in product names. The Bureau asks that repackaged data carry a conspicuous statement to that effect on the cover, the site's first page or somewhere as visible, and that its trademarks carry the &reg; symbol. Boundaries are for statistics, not legal descriptions, and come with no warranty. | A statement near the top of `iowa.html`, in `iowa-voters.html`'s How? box, and in Sources, with the &reg; symbol |
| us-atlas | ISC license, per npm (`docs/PIPELINE.md`). It redistributes Census boundaries. | Nothing while the site loads it from a CDN |

**Gap in the record:** not read were the Secretary of State's site policies, or any terms from the results site's vendor. None appeared on the page saved.

## Build, from the repo root

| # | Command | Writes to `data/ia/` | SHA-256 (first 16) |
|---|---|---|---|
| 1 | `python scripts/build_ia_results.py` | `results-2026.json` | `c42eebcfad4b1680` |
| 2 | `python scripts/build_cities.py ia` | `cities.json` | `a091fc6b1b442654` |
| 3 | `python scripts/build_precincts.py ia` (reads #1) | `blocks.json.gz` | `93be075ac2e3056a` |
| 4 | `python scripts/build_landmask.py ia` | `landmask.bin.gz` | `d2c054961dedbff5` |

## Numbers to expect

- 7 races on 99 counties; 1,659 precincts; 1,380,528 ballots; 2,178,374 registered voters
- 442 places, the largest Des Moines
- 175,199 blocks, 119,228 with adults, 2,450,103 adults
- A 5,516 × 3,536 land grid; 131,754 blocks drawn

| Race | Democrat | Republican | All votes |
|---|---|---|---:|
| U.S. Senate | Josh Turek 686,486 | Ashley Hinson 630,615 | 1,360,839 |
| Governor and Lt. Governor | Rob Sand and Dave Muhlbauer 757,326 | Zach Lahn and Derek Wulf 607,415 | 1,366,516 |
| Secretary of State | Ryan Peterman 625,867 | Paul D. Pate 711,766 | 1,338,890 |
| Auditor of State | Taylor Wettach 666,632 | Chris Cournoyer 660,159 | 1,328,166 |
| Treasurer of State | John Norwood 655,763 | Roby Smith 664,948 | 1,322,032 |
| Secretary of Agriculture | Chris Jones 629,249 | Mike Naig 701,882 | 1,332,316 |
| Attorney General | Nate Willems 681,097 | Brenna Bird 657,405 | 1,340,029 |

The U.S. Senate's "all votes" includes Thomas Laehn (Libertarian) with 42,052. Every other race's other votes are write-ins.

**Left out of the 274 contests:** Constitutional Amendment 1 and three Court of Appeals retention votes (John M. Sandy, Julie A. Schumacher, Sharon Soorholtz Greer) are statewide but yes-or-no, so they have no candidates to map. The other 263 aren't statewide: U.S. House, the legislature, district judges, and county races.

Checks that stop the build:

- Every county is completely reported, with all its precincts in, by `status.json`; every mapped race reads 99 of 99 in the Summary CSV and `sum.json`, and all precincts in `details.json`
- Counties on the site match the Census names
- In each county and race, election day plus absentee equals each candidate's total, candidates add up to the county's total, votes don't exceed ballots, and registered voters match the first table
- Counties add up to the report's own totals, the Summary CSV and `sum.json`, candidate by candidate; each county matches `details.json` and `ALL.json`; and `summary.json`'s votes match `sum.json` in all 274 contests
- Each county has at least 10 U.S. Senate votes and has adults; adults match the Census file's state record

## What differs from Oklahoma

- **Projection:** parallels 40.9° and 43°, centered on 93.4° W. The blocks' bounding box is 40.375° to 43.501° and 96.639° to 90.140° W, so the rule of thumb gives 40.896°, 42.980° and 93.390°. `state.js` and `build_landmask.py` use the same values.
- **Joint ticket:** Governor and Lt. Governor run together, so the race is labeled that way, with both names on the ticket. Short text uses the governor candidate's last name.
- **Results source:** one fixed-width county report, cross-checked against the site's other files, rather than county and precinct exports. There's no precinct file to add up here.
- **Party codes:** `L` and `W`, Texas's codes, so the shared page text can say "Libertarian" and "write-ins". The file doesn't say who is an incumbent, so none are marked.
- **Pages:** `iowa.html` and `iowa-voters.html` are Oklahoma's pages with their own wording, and they say "unofficial" and carry the TIGER/Line statement near the top. They leave out the "(of 77)" that Oklahoma's page types by hand, since no figure in the copy is typed. There's no change to `app.js`: its shared sentence "with all precincts reporting in all 99 counties" is true for Iowa on this data.
- **Time zone:** `meta.resultsUpdated` says CST.

## Gaps

- **Pottawattamie County's write-ins are blank**, in all 11 of its rows that have a write-in line, including all 7 mapped races. They're blank by vote type with a total of 0 in the Detail TXT, null in `ALL.json` and 0 in `details.json`. The map counts them as 0, and the state's own totals add up only that way, so write-ins aren't all counted in this data. It's the only such county, and the build stops if another appears. The Sources note says so.
- **The site's Summary CSV has an odd ballots figure:** 4,022 ballots on Christina Bohannan's row in U.S. House District 1, against 351,361 on the same contest's other rows. It's not in a mapped race and nothing reads it.
- **The TIGER/Line statement is on Iowa's pages only.** The Bureau asks for the site's first page or somewhere as visible. `index.html` was out of scope for this work, and neither it nor the Texas and Oklahoma pages carry the statement, though those pages use TIGER/Line files too. The owner may want to add one to the homepage.
- **The 95-of-99 field in `summary.json` is unexplained**, as above.
- **Hand-picked text:** there's no tour, no county flight and no history.

## How this was checked (2026-11-08)

- All four builds were run from the raw files. `results-2026.json`'s shape was checked against Part 6's: 99 rows per race, each adding up.
- All 99 county codes match us-atlas 3.0.1 (`counties-10m.json`), with no differences in name, including O'Brien, the only name with punctuation. That agrees with `STATE.countyCount`.
- Every county has adults (fewest: 2,891) and at least 10 U.S. Senate votes (fewest: 1,614).
- The land grid was decoded and looked at as a whole and at eight places. Saylorville Lake, Lake Red Rock, Rathbun Lake and the Okoboji lakes appear empty in their right shapes, Carter Lake's lived-on patch shows west of the Missouri at Council Bluffs, and the Mississippi and Missouri edges follow the rivers. Of nine spot checks, eight came out as expected; the ninth, a point meant for Rathbun Lake, was on land just south of the lake in the picture, so the point was off rather than the grid.
- `scripts/build_precincts.py`, `build_cities.py` and `build_landmask.py` gained Iowa entries and otherwise behave as before. With the changed scripts, Oklahoma's four files and Texas's `cities.json`, `landmask.bin.gz`, `precincts.json.gz` and `precinct-shapes.json.gz` were rebuilt into a scratch folder from the main checkout's raw files, and all eight match the committed files byte for byte. `build_data.py` and `build_history.py` weren't changed or rerun.
- **Not checked:** no page was opened. Browser checking is due after the merge. The whole sequence hasn't been run on a new machine.

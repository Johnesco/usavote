# South Carolina: the record

Built 2026-11-08, for the 2026 general election only, with bar view by county and by precinct, and dot view. **Results are unofficial:** the [State Election Commission's public notices](https://scvotes.gov/about-the-sec/public-notices/) list the State Board of Canvassers' certification meeting for Nov. 10, 2026, so save the files again after that, rebuild, and compare.

**What the By precinct view is:** 2026 votes on 2020 lines. The state's own precinct layer can't be used (see Terms), so the shapes are the Census Bureau's 2020 voting districts (VTDs), matched by name to the 2026 precincts. Some are combined, and some votes are shared out by rule. A district's number is exact only where no votes were moved to it.

## Raw files, under `data/raw/sc/` (not committed)

Results, saved 2026-11-08 (times in `results/manifest.json`):

| What | Path | SHA-256 (first 16) |
|---|---|---|
| Statewide file, version 386034 (`/SC/127300/386034/reports/detailxml.zip` on [Election Night Reporting](https://www.enr-scvotes.org/SC/127300/web.345435/#/summary)); stamped 11/6/2026 6:25:28 PM EST | `results/detailxml.zip` | `df77df4b734fe117` |
| Current version number | `results/current_ver.txt` | `fbf8ae824a7fcaa2` |
| Statewide settings: 2,312 of 2,312 precincts reporting, and the list of county ids and versions | `results/electionsettings.json` | `17d23d7b37d2c981` |
| All 46 county precinct files and settings (`/SC/{County}/{id}/{ver}/...`); each file's address, Last-Modified time, size and full SHA-256 are in the manifest | `results/counties/<County>.detailxml.zip`, `.settings.json` | manifest |
| The manifest | `results/manifest.json` | `946073af8f20ef34` |
| The browser's save of all of the above, base64-encoded, unpacked with its hashes checked | `results/sc-results-bundle-20261108.json` | `97f567e2b09e78f2` |

Census, by plain `curl`, 2026-11-08:

| What | Path | SHA-256 (first 16) |
|---|---|---|
| 2020 Census redistricting file ([zip](https://www2.census.gov/programs-surveys/decennial/2020/data/01-Redistricting_File--PL_94-171/South_Carolina/sc2020.pl.zip)) | `census/sc2020.pl.zip` | `e8996f6873405d6c` |
| 2020 census block shapes ([zip](https://www2.census.gov/geo/tiger/TIGER2020/TABBLOCK20/tl_2020_45_tabblock20.zip)) | `census/tl_2020_45_tabblock20.zip` | `87ac54c63173ad2e` |
| 2020 voting districts ([zip](https://www2.census.gov/geo/tiger/TIGER2020PL/STATE/45_SOUTH_CAROLINA/45/tl_2020_45_vtd20.zip)) | `census/tl_2020_45_vtd20.zip` | `5e6ddc3aebba1000` |

**How the results were saved:** a plain `curl` request for `current_ver.txt`, with no browser user agent, got a 403 from CloudFront ("Request blocked"). It wasn't tried another way. The files were saved through Claude in Chrome instead, in its own tab, closed afterward: this code, run on the results site's page, fetched each file one at a time, 300 ms apart per county, recorded its SHA-256, and downloaded one JSON bundle.

```js
for (const [county, id, ver] of settings.electiondetails.participatingcounties.map(x => x.split('|'))) {
  await get(`counties/${county}.settings.json`, `/SC/${county}/${id}/${ver}/json/en/electionsettings.json`);
  await get(`counties/${county}.detailxml.zip`, `/SC/${county}/${id}/${ver}/reports/detailxml.zip`);
}
```

**Not used:** the state RFA `Voter_Precincts` layer or zip, Redistricting Data Hub copies, UF Election Lab, or anything behind a login. No voter files.

## Terms of use, read 2026-11-08

This is a reading of the published pages, not legal advice. Nobody at these agencies has been asked about the site.

| Source | What it says | What it asks of us |
|---|---|---|
| Results (State Election Commission) | No license or reuse terms found for results. The [scvotes.gov](https://scvotes.gov/) footer has a general notice: "© 2026 South Carolina State Election Commission. All Rights Reserved." The [privacy statement](https://scvotes.gov/about-the-sec/sec-website-privacy-statement/) limits commercial solicitation with personal information, which doesn't apply: no personal information is used. | Nothing stated about reuse. The site credits the Commission, links to it, and says results are unofficial. |
| Census TIGER/Line, voting districts and blocks | [Technical documentation](https://www2.census.gov/geo/pdfs/maps-data/data/tiger/tgrshp2020pl/TGRSHP2020PL_TechDoc.pdf), Chapter 1: "TIGER/Line" is a registered trademark that may be used only to refer to a product's nature; the Bureau requests that repackaged files carry a conspicuous statement to this effect on the "cover, the first page of the website, or elsewhere of comparable visibility", and asks that the ® be used where convenient. Section 1.2: no copyright, but cite the Bureau as the source. Boundaries are for statistical purposes and aren't legal land descriptions. | The statement, near the top of both pages and in Sources. **Open:** the site's first page, `index.html`, doesn't carry it, because this work wasn't to edit that file. |
| Census redistricting file | No license found for these files. | Credit |
| us-atlas | ISC license, per npm. It redistributes Census boundaries. | Nothing while the site loads it from a CDN |
| State RFA `Voter_Precincts` | Terms grant no reuse, as checked before this work; not read again. | Not used, for shapes or for deciding the crosswalk |

**Gap in the record:** not read were any terms from the company behind the results site (the results page shows none in its text as saved here), or the rest of the Census technical documentation.

## Build, from the repo root

| # | Command | Writes | SHA-256 (first 16) |
|---|---|---|---|
| 1 | `python scripts/build_sc_results.py` (reads the table `data/sc/precinct-crosswalk.csv`, `5ebd2b06a91b9d77`) | `data/sc/results-2026.json` | `fe4ad07fa0253315` |
|   | | `data/raw/sc/derived/precinct-votes.json` (not committed: it holds any precinct under 10 votes) | not recorded |
| 2 | `python scripts/build_cities.py sc` | `data/sc/cities.json` | `29261ac6915b6d76` |
| 3 | `python scripts/build_precincts.py sc` (reads #1) | `data/sc/precincts.json.gz` | `d784da9786eb5ff7` |
|   | | `data/sc/precinct-shapes.json.gz` | `3431210757852e8b` |
| 4 | `python scripts/build_landmask.py sc` | `data/sc/landmask.bin.gz` | `220af1fcb0721e72` |

Each ran more than once from the raw files, with the same hashes.

The crosswalk table is the reviewed input. It was drafted once by a throwaway script, name matching plus the hand decisions in the next section, and that script isn't kept: change the table itself. The adapter stops unless the table has every result row and every voting district.

## Numbers to expect

8 races on 46 counties, with every statewide candidate race: U.S. Senate, Governor and Lieutenant Governor (one ticket), Secretary of State, State Treasurer, Attorney General, Comptroller General, State Superintendent of Education, Commissioner of Agriculture.

| Race | Democrat | Republican | Others | Total |
|---|---|---|---:|---:|
| U.S. Senate | Annie Andrews 1,043,712 | Darline Graham 951,896 | 45,287 | 2,040,895 |
| Governor and Lt. Governor | Johnson / Skardon 960,269 | Wilson / Reichenbach 1,051,010 | 26,343 | 2,037,622 |
| Secretary of State | Jason Belton 952,186 | Mark Hammond 1,073,652 | 961 | 2,026,799 |
| State Treasurer | Vincent Coe 959,539 | Curtis Loftis 1,062,666 | 1,107 | 2,023,312 |
| Attorney General | Richard Hricik 964,921 | David Stumbo 1,059,358 | 1,135 | 2,025,414 |
| Comptroller General | Tiffany Boozer 965,075 | Mike Burkhold 1,048,553 | 730 | 2,014,358 |
| Superintendent of Education | Sylvia Wright 976,406 | Ellen Weaver 1,032,516 | 16,769 | 2,025,691 |
| Commissioner of Agriculture | DeShawn Blanding 922,961 | Cody Simpson 1,042,601 | 55,635 | 2,021,197 |

Precincts: 2,252 on the map, from 2,268 voting districts; 12 precincts hold several districts; 107 say "(est.)"; 4 districts left off; 0 merged for being under 10 votes (the smallest has 32). 2,252 outlines, 100,103 points. 209 places; 146,844 blocks, 103,772 with adults, 4,014,460 adults; a 4,589 × 3,617 land grid.

Checks that stop the build:
- All precincts reporting, in the state file and each county's. All 46 counties in every race.
- For every mapped race and candidate: precincts add up to the county file, vote types add up to the county file's total, the county file equals the state file's county figure, and counties add up to the state total. Candidates are matched across files by party, since spellings differ ("Addison/ Candace" and "Addison / Candace"); each statewide race has one candidate per party.
- The table has every result row once and every district once, and every "exact" row really matches by name.
- After placing, every county's Senate votes equal its result, party by party. Merging keeps every vote. Adults match the Census file's state record.

## How 2026 precincts reach 2020 districts

Base race: 2026 U.S. Senate, all 2,450 rows, of which 2,312 are named precincts and 138 are countywide failsafe, provisional and failsafe-provisional rows (three per county).

| Method in the table | What happens | Rows | Senate votes |
|---|---|---:|---:|
| `exact` | Same name, ignoring case and punctuation | 2,160 | 1,912,372 (93.70%) |
| `fix` | Hand-checked: a misspelling, a different form of the name, or a split whose one parent the name makes plain (Burton 3A and 3B on Burton 3) | 68 | 51,598 |
| `combine` | One 2026 row covers several districts, which become one precinct (Kershaw; Cowpens; Monarch) | 3 | 3,164 |
| **As counted, in total** | | 2,231 | **1,967,134 (96.39%)** |
| `family` | New since 2020; the name points to a group but not one district (Hilton Head 2D among Hilton Head 2A to 2C). Shared by each party's votes in the group | 31 | 18,983 |
| `county`, new precinct | New since 2020 with no clear parent (Margaritaville; Field Day; Riverbend 1). Shared across the county by each party's votes | 13 | 11,219 |
| `county`, countywide row | Failsafe and provisional rows. Shared the same way | 138 | 3,510 |
| `pooled` | Lancaster and Spartanburg: rows whose names don't pair with the 2020 districts, shared by adults among the county's districts no row names. No district has its own count | 37 | 40,049 |
| **Moved, in total** | | 219 | **73,761 (3.61%)** |

Districts with no 2026 row: 7 joined the nearest district in the county by internal point (Kershaw 2, Saluda 5), 2 joined by name (Lando, East Buffalo), and 4 with under 10 adults stay off the map, 9 adults in all (two Savannah River Site districts, Pomflant, Pine Grove).

Shares use whole votes, by largest remainder, party by party, in this order: pooled, then family, then county. A precinct gets "(est.)" in its name once at least 5% of its votes were moved there, so it shows in the menu, the tooltip and the line about the place. Smaller shares aren't marked, but nearly every precinct in a county with failsafe or provisional votes has a few, and the on-screen note says so.

Moved votes are concentrated: Spartanburg 30,515 (25.5% of its votes), Beaufort 19,204 (22.3%), Lancaster 12,273 (28.7%), Jasper 3,665 (21.0%), Aiken 3,138 (4.6%), York 2,057 (1.8%). The rest are under 0.5% each, except Clarendon at 3.2%.

**Decisions worth a second look:**
- Charleston "Johns Island 2" goes on the Census district named "James Island 2": its internal point (32.755, -80.038) is on Johns Island, and there is no James Island 2 row. Likely a mistake in the Census name.
- Fairfield "GLADDEN GROVE" goes on the Census district "Garden Grove", the only unclaimed district with a similar name.
- The first check found a name match of 93.9%; this one finds 93.70%, using Census county codes and only the normalization in the script. The earlier method wasn't saved, so the difference wasn't explained.
- A same-name match doesn't prove the lines are the same. 14 of 2,252 precincts have more than 1.2 votes per 2020 adult, such as Berkeley's Wildcat Trail and North Creek, which may be growth, changed lines or both.

**Early and mail votes, county by county:** all 46 counties report them in home precinct rows. No row is named for early or mail voting, and all the failsafe and provisional vote types are on the countywide rows and nowhere else, so those rows hold no early or mail votes. Abbeville and Richland both follow this: Richland's 3,752 mail votes for U.S. Senate are on its precincts, which differs from the earlier check's "no absentee rows": it has no separate ones. So countywide rows don't weaken placement here, unlike the concern in PIPELINE Part 6. In the file, straight-party ballots appear to be already in candidate totals: a separate straight-party contest is in the county files and isn't mapped.

## What differs from Texas

- **Projection:** parallels 32.5° and 34.7°, centered on 80.9° W. The state runs from 31.996° to 35.215° N (with its coastal water) and 83.354° to 78.499° W; the rule of thumb gives 32.53°, 34.68° and 80.93°.
- **Shapes:** Census 2020 voting districts, already in longitude and latitude, not the state's current lines.
- **Base race:** 2026 on the site's own race list, so `raceId` is `u-s-senate`, and it shows on the same year as the others.
- **Other races:** each party's county total is shared among districts by that party's 2026 Senate share, as in Texas.
- **Land area:** the 2020 Census file's `AREALAND`, as in Oklahoma, not the 2024 Gazetteer.
- **Pages:** the Texas markup with `<html data-state="south-carolina">`, with Oklahoma's wording, and the By precinct buttons and precinct menu kept. No tour or history: `STATE.tour: false`, `STATE.flights: []`, `STATE.data.history: null`. The pages' line about the counties drops "(of 77)", since numbers aren't typed in copy.
- **Candidates:** the file doesn't say who is an incumbent, so none are marked, and it doesn't say how anyone came to be on the ballot. Governor and Lieutenant Governor is one ticket, labeled so, and named for its first person (`last`), so the page says "Wilson". The file's party codes `LIB` and `GRN` are written the way the pages spell them; `CON` and `UNC` aren't explained in the file and show as they are. Write-ins are in "other". Copy doesn't say how Darline Graham came to be the Republican, or anything about write-in campaigns for any named person.
- **Shared code:** nothing in `app.js`, `voters.js`, `places.js` or `dots.js` needed changing. A multi-word name and slug work through `STATE.name` and `STATE.slug`. `state.js` and the three build scripts gained South Carolina entries and blocks only.

## Gaps

- **Unofficial:** rebuild after certification, Nov. 10, 2026.
- **Pooled counties:** in Lancaster and Spartanburg, 40,049 votes are on districts with no count of their own, so one party mix covers those districts. This is the weakest part of the map. A public, reusable list of precinct changes since 2020 would fix it; none was looked for beyond the sources named here.
- **Margaritaville** (3,655 votes, Jasper) has no clear parent by name, so it's spread across the county. It's likely in one part of the county, but nothing used here says which.
- **The new precincts' shapes aren't on the map:** Bluffton, Burton and the others show as the older, larger districts.
- **Trademark statement:** the first page of the site doesn't carry it. Texas and Oklahoma pages also use TIGER/Line blocks in their land grids and don't carry it either, which the owner may want to look at.
- **Results site terms:** see Terms above.

## How this was checked (2026-11-08)

- All four builds ran more than once from the raw files, with matching hashes.
- `results-2026.json` has the same keys as Oklahoma's file, plus `meta.precinctPlacement`.
- us-atlas 3.0.1 `counties-10m.json` (SHA-256 `145aaf5d1433352a`, the hash in Part 2): 46 South Carolina counties, with the same codes and names as `results-2026.json`.
- Precinct file: every county has entries, with as many shapes as entries; party totals match the Senate by county; 2,040,895 votes in all. Dots: the worker draws each county's race total exactly, and every precinct has adults to place them on, so a race's dots equal its total. The code wasn't run in a browser.
- Adults in each map precinct, from block containment, equal the Census file's own voting district records for all 2,252 precincts, and no block fell back to the nearest district. 4,014,451 of 4,014,460 adults are placed; the other 9 are in the districts left off.
- Land grid, viewed as a picture: Lakes Marion, Moultrie, Hartwell and Murray are empty where marked, the Atlantic is empty, and the coast and sea islands line up; Myrtle Beach and Columbia are lived on.
- Texas and Oklahoma: with the edited scripts, in a scratch copy reading the main checkout's `data/raw/` (read-only; these raw files aren't in this worktree), all seven rebuilt files match the hashes in PIPELINE Parts 3 and 7: `cities.json`, `landmask.bin.gz`, `precincts.json.gz`, `precinct-shapes.json.gz`, and Oklahoma's `cities.json`, `blocks.json.gz`, `landmask.bin.gz`. `build_data.py`, `build_history.py` and `build_ok_results.py` weren't changed, so they weren't rerun.
- **Not checked:** the pages in a browser. That's planned after the merge.

## U.S. House, added 2026-11-12

`results-2026.json` now also has the U.S. House as one race: every district added up by county, with each district's own result, built by the same script through `scripts/chamber.py`. All 7 districts are in the statewide file, with each one's counties; counties add up to its totals. The results page draws the districts (By district) on Census outlines, which the build checks against the results. The record for all the states is in [`../PIPELINE.md`](../PIPELINE.md), Part 10.

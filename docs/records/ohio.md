# Ohio: the record

Built 2026-11-08, for the 2026 general election only, and **county-only**: bar view by county and dot view, with no By precinct view or precinct menu. It follows the shape of `docs/PIPELINE.md`, Part 7.

**Results are unofficial and partial.** The file's status is `UnofficialPartial`, and its counties list 102,148 ballots outstanding (3,779 UOCAVA absentee, 98,369 provisional). The results site says the official canvass finishes about three weeks after the election, so save the file again after that, rebuild, and compare.

## Raw files, under `data/raw/oh/` (not committed)

| What | Path | SHA-256 (first 16) |
|---|---|---|
| Results, all races, NIST 1500-100 XML ([file](https://liveresults.ohiosos.gov/Api/v1/download?filename=VSSC1622XmlFileBlob)), saved by plain curl on 2026-11-08 | `results/VSSC1622-2026-11-08.xml` | `d1ba1c4eb9a3cf0f` |
| 2020 Census redistricting file ([zip](https://www2.census.gov/programs-surveys/decennial/2020/data/01-Redistricting_File--PL_94-171/Ohio/oh2020.pl.zip)) | `census/oh2020.pl.zip` | `ceef338247ad2dcc` |
| 2020 census block shapes ([zip](https://www2.census.gov/geo/tiger/TIGER2020/TABBLOCK20/tl_2020_39_tabblock20.zip)) | `census/tl_2020_39_tabblock20.zip` | `8075876e141b74db` |

The results file's full SHA-256 is `d1ba1c4eb9a3cf0f1f47b48df804ad3d35401d45c118eda036883846a8bb3833`. `results/headers.txt` holds the response headers. The file says `GeneratedDate="2026-11-04T09:06:14Z"`, the same stamp as an earlier check that day, so nothing differed from that check. Its HTTP `Last-Modified` header changes on every request and says nothing about the data.

The county check also used us-atlas 3.0.1, `data/raw/us-atlas/counties-10m.json` (SHA-256 `145aaf5d1433352a`, the hash in Part 2).

## Why county-only

The owner chose this for Ohio in the approved plan, like Oklahoma. No precinct shapes were downloaded, and neither the Redistricting Data Hub nor the UF Election Lab was used. So precinct results and shapes weren't evaluated here.

What this costs: dots use one mix of parties across a county, so they don't show which neighborhoods lean which way.

## Terms of use, read 2026-11-08

This is a reading of the published pages, not legal advice. Nobody at these agencies has been asked about the site.

| Source | What it says | What it asks of us |
|---|---|---|
| Results (Ohio Secretary of State) | No license found. The results site's footer reads "© 2026 Ohio Secretary of State. All Rights Reserved." **The owner chose to treat these results like Texas's and Oklahoma's.** | Nothing stated. The site credits the Secretary of State and repeats the notice, and says the results are unofficial and partial. |
| Census files | The TIGER2020PL technical documentation, Chapter 1.2, cites 17 U.S.C. 105: no copyright in U.S. government works. It asks that users cite the Census Bureau as the source. | The credit, in Sources. |
| TIGER/Line Shapefiles | Chapter 1.1: TIGER/Line is a registered trademark, can't be used in proprietary product names, and may only be used to refer to the nature of a product. It requests that repackaged data carry a statement "to this effect" that is conspicuously placed on the product's cover, the website's first page, or somewhere of comparable visibility. | See below. |
| us-atlas | ISC license, per npm. It redistributes Census boundaries. | Nothing while the site loads it from a CDN |

**The TIGER request differs from how it was first described.** It's about the trademark, not only about saying the data isn't the Census Bureau's. The wording used covers both: "TIGER/Line® is a registered trademark of the U.S. Census Bureau. This site's land grid is reworked from TIGER/Line® Shapefiles and isn't a Census Bureau product; the name is used here only to say what the source was."

It appears near the top of `ohio.html`'s sidebar, in `ohio-voters.html`'s **How?**, in shorter form in that page's always-visible note, and in the results file's Sources. The land grid's own header carries a short form too.

**Open for the owner:** the request names "the first page of the website". This build was told not to edit `index.html`, so the statement isn't on the homepage. The Texas and Oklahoma land grids come from the same kind of file and have no such statement.

**Gap in the record:** not read were the Ohio Secretary of State's other site policies (privacy, disclosure and text message pages were listed in the footer) and the disclaimer page that "Understanding Unofficial Results" links to on ohiosos.gov. Only the copy of that text inside the results site was read.

## Build, from the repo root

| # | Command | Writes to `data/oh/` | SHA-256 (first 16) |
|---|---|---|---|
| 1 | `python scripts/build_oh_results.py` | `results-2026.json` | `f5e31823ae9e7f21` |
| 2 | `python scripts/build_cities.py oh` | `cities.json` | `85fde05a80f9c215` |
| 3 | `python scripts/build_precincts.py oh` (reads #1) | `blocks.json.gz` | `73f9bfe05fca4dd0` |
| 4 | `python scripts/build_landmask.py oh` | `landmask.bin.gz` | `3416d00d8f8b9f84` |

Numbers to expect: 8 races on 88 counties; 8,834 precincts, all reporting; 677 places, Columbus largest; 276,428 blocks, 216,562 with adults, 9,207,562 adults; 222,262 blocks with people or housing, 2,681 of them with holes; a 3,759 × 4,396 land grid.

Checks that stop the build: the file's status is still `UnofficialPartial`, because the page's wording was written for it; all precincts are reporting; all 88 counties are there and match the Census file one to one; every candidate has one count for the state and one for each county; each candidate's counties add up to the file's state figure; a county's votes in a race don't exceed its ballots cast, apart from the one exception below; adults match the Census file's state record; and every county has adults and at least 10 U.S. Senate votes.

The file gives no separate total for a race in a county, so "candidates add up by county" is only checked by building each total from its candidates and holding it against the county's ballots cast.

### Races

| Race (id) | Democrat | Republican | Others |
|---|---|---|---|
| U.S. Senate, unexpired term to Jan. 3, 2029 (`u-s-senate`) | Sherrod Brown 2,301,042 | Jon Husted 2,077,748 | 223,135 |
| Governor and Lieutenant Governor (`governor`) | Amy Acton and David Pepper 2,404,178 | Vivek Ramaswamy and Robert McColley 2,039,730 | 153,362 |
| Attorney General (`attorney-general`) | John Kulewicz 2,285,117 | Keith Faber 2,256,710 | 0 |
| Auditor of State (`auditor`) | Annette Blackwell 2,237,955 | Frank LaRose 2,310,105 | 0 |
| Secretary of State (`secretary-of-state`) | Allison Russo 2,287,160 | Robert Sprague 2,129,981 | 134,179 |
| Treasurer of State (`treasurer`) | Seth Walsh 2,282,546 | Jay Edwards 2,232,758 | 0 |
| Supreme Court, term from Jan. 1, 2027 (`supreme-court-jan-1`) | Marilyn Zayas 2,307,346 | Daniel Hawkins 2,215,728 | 0 |
| Supreme Court, term from Jan. 2, 2027 (`supreme-court-jan-2`) | Jennifer Brunner 2,324,212 | Colleen O'Donnell 2,200,021 | 0 |

**Left out:** State Issue 3, which is yes or no with no candidates; and races below statewide, which don't cover the state: U.S. House (15), State Senate (17), State House (99) and Courts of Appeals (22 contests). No statewide candidate race was dropped for its shape.

## What differs from Oklahoma

- **Projection:** parallels 39° and 41.4°, centered on 82.7° W. The shapefile's box runs north to 42.33° because it includes Ohio's part of Lake Erie, so the rule of thumb in Part 6 uses the land's range instead: 38.40° to about 41.97°, the northernmost block with adults, and 84.82° W to 80.52° W.
- **Wording, through `state.js`:** two new settings, both optional, so Texas's and Oklahoma's text doesn't change. `reporting` replaces "with all precincts reporting in all N counties" and quotes the outstanding counts from the results file. `wonState` replaces "won the state" with "led the count so far".
- **Why "won the state" had to change:** in four races the leader's margin is smaller than the ballots outstanding, so the file can't say who won: Attorney General (28,407), Auditor (72,150), Treasurer (49,788) and the Supreme Court seat from Jan. 1 (91,618).
- **Still says "won":** the county counts and legends, and the table's "winner", use shared wording. `ohio.html` adds a line saying winners here are leaders in a partial count. County results could flip too.
- **Tickets:** Governor is the feed's ticket race, so the label is the feed's and names are "Acton and Pepper" style. `last` is the top of the ticket.
- **Supreme Court seats:** both have the same name in the feed, and only their term dates tell them apart, so labels use those. The feed lists party labels for candidates but marks the office non-partisan.
- **Parties:** Libertarians use the code the pages already know (`L`). Greg Levy's party is written "Other party", which is all the file says. Write-ins are `W`.
- **Candidates:** the file doesn't say who is an incumbent, so none are marked.
- **Tour and history:** none, as in Oklahoma.

## Differences found

- **The U.S. Senate term:** the plan described the seat as running through January 2028. The file says `UnexpiredTerm`, ending 2029-01-03, and the label uses that. The file doesn't use the word "special", so the label doesn't either.
- **Outstanding ballots:** the file calls them `Absentee`; the results site's column for the same figures is "Outstanding UOCAVA Absentees". The site says these were requested but not yet returned, so not all will arrive, and provisional ballots count only if they qualify. So the page says outstanding, not "to be counted".
- **Wyandot County doesn't add up, and this wasn't resolved.** Its ballots cast in the file (8,739) is below its votes in all eight mapped races (8,860 to 9,975). In the other 87 counties, votes in every race are below ballots cast. The file can't say which figure is wrong. The county's own results page returned 403, and it wasn't read another way. The votes are used as published, because they add up to the state totals, and ballots cast isn't published. The build names this one county with this one figure, and stops if that changes.
- **A field not to trust:** each county's `Absentee` `BallotsCast` is several times its total ballots (Adams: 62,074 of 9,169). It isn't used.

## Gaps

- **Texas and Oklahoma weren't rebuilt.** Their raw files aren't in this worktree. Their committed data files still match the hashes in Part 3 and Part 7, and their paths through the changed scripts were read in the diff. Oklahoma's two meta strings, now in dict entries, were compared to its committed `blocks.json.gz`. The first build there after the merge should confirm byte-identical output.
- **Pages haven't been opened.** Browser checking comes after the merge, including how long the always-visible note on `ohio-voters.html` sits on small screens. `state.js` and `app.js` passed a syntax check only.
- **Precincts:** the file's `SubUnitsReported` and `TotalSubUnits` are read as precincts. The file doesn't say so outright.
- **Time zone:** `resultsUpdated` is written in UTC, as the file gives it, not converted to Ohio time.

## How this was checked (2026-11-08)

- All four builds ran from the raw files. Each stops on the checks above.
- The results file matched the adapter shape in Part 6: every race has 88 rows, each row adds up, and each column adds up to its candidates.
- us-atlas has 88 Ohio counties, and their codes and names match exactly. `STATE.countyCount` is 88, and `state.js` and `build_landmask.py` use the same projection.
- Every county has adults (fewest: Vinton, 9,981) and at least 10 U.S. Senate votes (fewest: Vinton, 3,903).
- The land grid was checked as pictures of the state, the Lake Erie shore, Grand Lake St. Marys and Indian Lake. The shore, Sandusky Bay, the islands and both lakes look right, and sample points on open water are empty: five in Lake Erie and one each in the two lakes. Sample points in Columbus, Cleveland, Cincinnati, Toledo, Celina and Russells Point are lived on. Airports weren't looked at one by one.
- The two lakes' sample points fall in blocks with no people or housing, per the block file. A first sample near Grand Lake's north shore picked up the shoreline, so the sample was moved to open water. A block just east of the lake's straight edge is land, with almost no water on record.

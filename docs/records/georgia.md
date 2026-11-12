# Georgia: the record

Built 2026-11-08, for the 2026 general election only, and **county-only**: bar view by county and dot view, with no By precinct view or precinct menu. This has the shape of `docs/PIPELINE.md`, Part 7.

**Results are unofficial and partial.** The results page says "UNOFFICIAL RESULTS". Per the survey for this work, counties certify on Nov. 9, 2026 and the state deadline is Nov. 20; those two dates weren't read at a state source here. Save the export again after certification, rebuild, and compare.

## Reporting status

From the file, as of its stamp (`createdAt` 2026-11-08T00:23:59Z, Nov. 7, 7:23 PM EST):

- 2,581 of 2,581 precincts reporting, in all 159 counties, in every mapped race
- **Provisional ballots "Not Reported" in 7 counties:** Columbia, Decatur, Fannin, Fulton, Gilmer, Gordon and Union
- **Absentee by mail "Partially Reported" in Fulton County**
- Every other vote type in every county reads "Election Night Complete" (105 counties) or "Fully Reported" (54)

So the pages use `STATE.reporting`, and `won: 'led'`, `winner: 'leader'` and `wonState`, as Ohio's do. The file doesn't say how many ballots are outstanding. The statewide block's own status says "Not Reported" for all four vote types beside complete totals, so it isn't read; each county's is.

**Runoffs:** none. Each mapped race has two candidates and a majority, and the build stops if one doesn't.

## Raw files, under `data/raw/ga/` (not committed)

Saved 2026-11-08, 11:27 PM Central (`results/saved-at.txt`), by plain `curl`, with no browser user agent.

| What | Path | SHA-256 (first 16) |
|---|---|---|
| [Media Export](https://results.sos.ga.gov/cdn/results/Georgia/export-11032026GeneralAndSpecialElection.json) from the [results site](https://results.sos.ga.gov/results/public/Georgia/elections/11032026GeneralAndSpecialElection) | `results/export-11032026GeneralAndSpecialElection.json` | `82485ad3757500df` |
| Its response headers: Last-Modified Nov. 8, 2026, 00:24:01 GMT | `results/export.headers.txt` | `9b7a439a091b5aa3` |
| The results page's shell, with no results in it; not read by the build | `results/public-page.html` | `374f0fa3e64f82fa` |
| When they were saved | `results/saved-at.txt` | `531f9867881c2993` |
| 2020 Census redistricting file ([zip](https://www2.census.gov/programs-surveys/decennial/2020/data/01-Redistricting_File--PL_94-171/Georgia/ga2020.pl.zip)) | `census/ga2020.pl.zip` | `26434588ceab435f` |
| 2020 census block shapes ([zip](https://www2.census.gov/geo/tiger/TIGER2020/TABBLOCK20/tl_2020_13_tabblock20.zip)) | `census/tl_2020_13_tabblock20.zip` | `089bf2763209a553` |
| 2020 voting districts ([zip](https://www2.census.gov/geo/tiger/TIGER2020PL/STATE/13_GEORGIA/13/tl_2020_13_vtd20.zip)), read only by `scripts/ga_precinct_match.py` | `census/tl_2020_13_vtd20.zip` | `9ff0a518d962f9b5` |

**Access:** sos.ga.gov returned a 403 to plain `curl`, so its pages were only read, through Claude in Chrome, and no data came from it. The results site and export needed no browser. The results page's own stamp, read in the browser, was "Last Updated Saturday, November 7, 2026 at 2:05:49 PM", with no time zone; the pages use the export's stamp.

**Not used:** the site's Download Reports (the export has statewide, county and precinct figures in one file), Redistricting Data Hub, University of Florida Election Lab, Voting and Election Science Team files, anything behind a login, or voter files. The state seal isn't used anywhere.

## Terms of use, read 2026-11-08

This is a reading of the published pages, not legal advice. Nobody at these agencies has been asked about the site. **No wording limiting reuse of results was found.**

| Source | What it says | What it asks of us |
|---|---|---|
| Results site footer | "Georgia Election Night Reporting", a link to the Media Export, and "POWERED BY ENHANCED VOTING". No terms, license or copyright line. | Nothing stated |
| [sos.ga.gov](https://sos.ga.gov/) footer | "© 2026 Georgia Secretary of State", with links to the Privacy Policy, Security and Contact Us. No terms-of-use link. | Nothing stated beyond the notice. The site credits the office and links to it. |
| [Privacy policy](https://sos.ga.gov/page/privacy-policy) | Covers online transactions, cookies and outside links, and says nothing about reusing results. Its one limit is on the state seal, which is restricted by law and "may be used only with the express written permission" of the State, as authorized by the Governor. | Don't use the seal. It isn't used. |
| Census files | [TIGER2020PL technical documentation](https://www2.census.gov/geo/pdfs/maps-data/data/tiger/tgrshp2020pl/TGRSHP2020PL_TechDoc_Ch1.pdf), Chapter 1, as read for `docs/PIPELINE.md`, Part 8: no copyright, cite the Bureau; repackaged TIGER/Line data carries a trademark statement on the site's first page, which `index.html` has. | Credit, and one short TIGER/Line note in Sources |
| us-atlas | ISC license, per npm. It redistributes Census boundaries. | Nothing while the site loads it from a CDN |

**Gap in the record:** the [Security page](https://sos.ga.gov/page/georgia-secretary-state-agency-security) linked from the footer was read only in part (its first screen, on election and website security). Enhanced Voting, the vendor, was not checked for terms beyond the results page's footer.

## Why county-only

The condition for a precinct view was exact-plus-clear-fix matches reaching at least 90% of U.S. Senate votes on Census 2020 voting districts, with early and mail votes in home precincts. **The match reaches 85.80%, so it wasn't built.** `python scripts/ga_precinct_match.py` gives these numbers from the raw files, and its header defines each row:

| Match | Rows | Votes | Share |
|---|---:|---:|---:|
| `exact`, same name | 1,674 | 2,505,275 | 59.95% |
| `whole`, one row for the county | 10 | 37,200 | 0.89% |
| `form`, same name in another form | 315 | 638,750 | 15.28% |
| `code=name`, the name is its code | 111 | 163,997 | 3.92% |
| `code+sim`, same code and similar name | 84 | 131,101 | 3.14% |
| `name~`, a name one district clearly shares | 32 | 58,314 | 1.40% |
| `split`, one parent by code | 44 | 46,209 | 1.11% |
| `combine`, several children by code | 2 | 5,166 | 0.12% |
| **Exact or a clear fix** | **2,272** | **3,586,012** | **85.80%** |
| `code-only`, same code and an unlike name | 89 | 158,932 | 3.80% |
| `none`, nothing to go on | 221 | 434,335 | 10.39% |

Counting every same-code row, which isn't sound, still gives only 89.61%. Codes get reused: Lowndes's "Hahira Community Center" has the code of the district named Northside. The most votes without a clear match are in Paulding (62,846), Forsyth (53,854), Cobb (39,152), Glynn (33,483), Muscogee (32,445), Fulton (32,096), Spalding (25,573), Cherokee (23,382), Oconee (19,519) and Lowndes (19,472). Several have redrawn since 2020: Paulding has 20 rows on 12 districts, Forsyth 29 on 16, and Spalding 8 on 18.

**The second condition is partly met.** No row is named for early or mail voting, no row is marked virtual, and precinct rows add up to each county's total (but for Fulton's 3 votes, below), so those votes are on precinct rows. But in 54 counties, with 1,734,878 Senate votes, the precinct rows' vote types add up to less than the county's own, so vote types there can't confirm it row by row.

What this costs: dots use one mix of parties across a county, so they don't show which neighborhoods lean which way, and the export's 2026 precinct results aren't on the map.

## Build, from the repo root

| # | Command | Writes to `data/ga/` | SHA-256 (first 16) |
|---|---|---|---|
| 1 | `python scripts/build_ga_results.py` | `results-2026.json` | `f35da56a2fdac02a` |
| 2 | `python scripts/build_cities.py ga` | `cities.json` | `ce599a02e698dd0c` |
| 3 | `python scripts/build_precincts.py ga` (reads #1) | `blocks.json.gz` | `9ed6639dba8083ce` |
| 4 | `python scripts/build_landmask.py ga` | `landmask.bin.gz` | `d79dfdc72bf51fa0` |

Each ran more than once from the raw files, with the same hashes.

## Numbers to expect

- 11 races on 159 counties
- 403 places, the largest Atlanta
- 232,717 blocks, 162,754 with adults, 8,220,274 adults
- A 4,639 × 5,202 land grid; 167,326 blocks drawn

| Race | Democrat | Republican | All votes |
|---|---|---|---:|
| U.S. Senate | Jon Ossoff (incumbent) 2,466,695 | Mike Collins 1,712,587 | 4,179,282 |
| Governor | Keisha Lance Bottoms 2,271,816 | Rick Jackson 1,909,727 | 4,181,543 |
| Lieutenant Governor | Josh McLaurin 2,330,629 | Greg Dolezal 1,834,070 | 4,164,699 |
| Secretary of State | Penny Brown Reynolds 2,321,803 | Tim Fleming 1,847,873 | 4,169,676 |
| Attorney General | Tanya Miller 2,320,270 | Brian Strickland 1,856,944 | 4,177,214 |
| Commissioner of Agriculture | Katherine E. Juhan-Arnold 2,242,271 | Tyler Harper (incumbent) 1,922,235 | 4,164,506 |
| Commissioner of Insurance | Keisha Sean Waites 2,258,833 | John King (incumbent) 1,901,067 | 4,159,900 |
| State School Superintendent | Lydia Powell 2,275,969 | Richard Woods (incumbent) 1,890,782 | 4,166,751 |
| Commissioner of Labor | Nikki Porcher 2,269,849 | Bárbara Rivera Holmes (incumbent) 1,884,575 | 4,154,424 |
| Public Service Commission, District 3 | Peter Hubbard (incumbent) 2,338,775 | Fitz Johnson 1,808,461 | 4,147,236 |
| Public Service Commission, District 5 | Shelia Edwards 2,297,894 | Josh Tolbert 1,855,409 | 4,153,303 |

Both Public Service Commission seats are on the ballot in all 159 counties, so they're voted statewide and mapped. Every race has only these two candidates in the file, so "other" is 0.

**Left out of the 273 contests:** Constitutional Amendments 1, 2 and 3 are in all 159 counties but yes-or-no. The other 259 aren't in all counties.

Checks that stop the build:

- All 159 counties match the Census names and have every mapped race; a county's candidates are the state's, by option id and name
- All precincts report in every mapped race; only provisional and absentee ballots may be unfinished
- In each county, vote types add up to each candidate's total, and precinct rows to the county's
- Each candidate's counties add up to the statewide figure, and the statewide vote types to the same figure
- Every mapped race has a majority; any other candidate stops it for a wording review; each county has at least 10 U.S. Senate votes and adults; adults match the Census file's state record

**Exceptions, both named in the script, which stops if either changes:**

- **Miller and Glascock counties have null vote types** for every candidate in every mapped race, though their totals are there. Their vote-type check can't run; the script checks instead that the statewide vote types equal the other counties' plus these two counties' totals. Needed because the source is blank there.
- **Fulton's precinct rows come to 3 fewer than its total for the Democrat**, in all 11 mapped races. County totals are what the map uses, and they add up to the statewide figures, so no number on the site is affected. Why isn't known, and nobody at the office was asked.

## What differs from Iowa

- **Projection:** parallels 31.1° and 34.2°, centered on 83.2° W. The blocks' bounding box is 30.356° to 35.001° and 85.605° to 80.783° W, so the rule of thumb gives 31.13°, 34.23° and 83.19°. `middle` and `radiusScaleAt` are both [-83.2, 32.7]. `state.js` and `build_landmask.py` use the same values.
- **Results source:** one JSON export with statewide, county and precinct figures, rather than several files. Candidates are matched across its blocks by option id: a county's party field can be blank or spelled differently (Evans, Stewart), and spacing differs ("(I)(Rep)" and "(I) (Rep)"). Gwinnett's contest names carry Spanish, and Bacon's Insurance contest reads "Commissioner of Insurance - Rep"; both are the same contest by id.
- **Incumbents:** marked, from the file's "(I)".
- **Party codes:** only `DEM` and `REP`.
- **Cities:** five consolidated city-counties get the names people use: Augusta, Athens, Macon, Cusseta and Georgetown. `build_cities.py` has a small Georgia block for this.
- **Sources:** per this work's rules, the TIGER/Line note is only in Sources, not near the top of the pages.
- **Shared code:** nothing in `app.js`, `voters.js`, `places.js` or `dots.js` changed. `state.js`, `build_precincts.py`, `build_cities.py` and `build_landmask.py` gained Georgia entries only.

## Gaps

- **Unofficial and partial:** rebuild after certification. The outstanding ballots aren't counted in the file.
- **Certification dates** are from the survey, not read here at a state source.
- **The 54 counties' precinct vote types and Fulton's 3 votes** are unexplained. Neither affects county figures.
- **A precinct view could be tried again** with a public list of precinct changes since 2020, or with lines from a source whose terms allow it. None was looked for here.
- **Land grid:** a refuge block in Okefenokee, drawn whole because the Census counted people or housing in it, reads as lived on. Few adults are in it, so few dots land there.
- **Hand-picked text:** there's no tour, no county flight and no history.

## How this was checked (2026-11-08)

- All four builds ran from the raw files, with matching hashes on the rerun.
- `results-2026.json` has the same keys as Iowa's at each level; each of its 11 races has 159 rows, each adding up, and each party's column adds up to its candidate.
- us-atlas 3.0.1 `counties-10m.json` (SHA-256 `145aaf5d1433352a`): 159 Georgia counties, with the same codes and names as `results-2026.json`, which agrees with `STATE.countyCount`.
- `blocks.json.gz`: 159 counties, one entry each, with 2,466,695 D and 1,712,587 R and matching each county's Senate row; every county has adults (fewest: 1,289) and at least 10 Senate votes (fewest: Taliaferro, 799).
- Land grid, decoded and viewed whole and at four places: Lake Lanier, Lake Oconee, Lake Sinclair, West Point Lake, Lake Seminole and Thurmond Lake appear empty in their right shapes, the Atlantic and Fort Stewart are empty, and St. Simons, Tybee, Savannah and Atlanta are lived on. Of 30 spot checks, the ones reading wrong were points that missed narrow water, confirmed in the pictures, plus the Okefenokee block above.
- With the edited scripts, in a scratch copy using the main checkout's raw files: `cities.json` for Oklahoma, Kansas, South Carolina, Ohio and Iowa, and Iowa's `blocks.json.gz` and `landmask.bin.gz`, match the committed files byte for byte. Texas and the other precinct and land builds weren't rerun; the only changes there are new dictionary entries and adding `ga` to the county-only tuples.
- **Not checked:** no page was opened. Browser checking is due after the merge. The whole sequence hasn't been run on a new machine.

## U.S. House, added 2026-11-12

`results-2026.json` now also has the U.S. House as one race: every district added up by county, with each district's own result, built by the same script through `scripts/chamber.py`. All 14 districts are in the export; District 14's item is named `USH14R` there. Counties add up to its statewide rows. Georgia needs a majority to win, and every district's leader has one in this file. The results page draws the districts (By district) on Census outlines, which the build checks against the results. The record for all the states is in [`../PIPELINE.md`](../PIPELINE.md), Part 10.

# Virginia: the record

Built 2026-11-19, for the 2026 general election only, and **county-only**: bar view by county and independent city, and dot view, with no By precinct or By district view. This has the shape of `docs/PIPELINE.md`, Part 7.

**Independent cities are counties here.** Virginia's 133 localities are 95 counties and 38 independent cities, which belong to no county; the Census Bureau and us-atlas count all 133 as county equivalents, and so does the site. Their names say which they are ("Fairfax County", "Fairfax City"), so `state.js` sets `countyWord: ''` and the pages use the names as they are. Menus and headlines still say "counties"; the page says the cities are shown on their own.

**Two races.** U.S. Senate is the only statewide race between candidates. U.S. House is the 11 district races added up by locality (`scripts/chamber.py`), with each district's own result. Constitutional amendments aren't here.

**Unofficial results.** The owner asked on 2026-11-19 to check Virginia, then chose to build it with Alabama, knowing the footer says "All rights reserved" (below). The results site read "UNOFFICIAL RESULTS"; they become official when the State Board of Elections certifies them (date not looked up).

## Raw files, under `data/raw/va/` (not committed)

| What | Path | SHA-256 (first 16) |
|---|---|---|
| The results site's media export ([JSON](https://enr.elections.virginia.gov/cdn/results/virginia/export-2026-November-General.json), 26.7 MB), `createdAt` 2026-11-19T19:20:41Z, Last-Modified Nov. 19, 2026, 19:20:42 GMT | `results/export-2026-November-General.json` | `dfbe266b6b0517c6` |
| Its response headers | `results/export.headers.txt` | `059833a9c3c03854` |
| When it was saved (UTC) | `results/saved-at.txt` | see the file |
| 2020 Census redistricting file ([zip](https://www2.census.gov/programs-surveys/decennial/2020/data/01-Redistricting_File--PL_94-171/Virginia/va2020.pl.zip)) | `census/va2020.pl.zip` | `e33c7c1ac0aa84b5` |
| 2020 census block shapes ([zip](https://www2.census.gov/geo/tiger/TIGER2020/TABBLOCK20/tl_2020_51_tabblock20.zip)) | `census/tl_2020_51_tabblock20.zip` | `5722c3a80c66acb0` |

The owner approved the export and the two Census files on 2026-11-19 ("Build both VA and AL", after being told what would be downloaded).

## Terms of use, read 2026-11-19

This is a reading of the published pages, not legal advice. Nobody at the Department of Elections has been asked.

| Source | What it says | What it asks of us |
|---|---|---|
| Department of Elections site footer ([elections.virginia.gov](https://www.elections.virginia.gov/)) | "Copyright ©2026 Virginia Department of Elections. All rights reserved", linking only to its privacy policy | See below |
| [Department of Elections: Privacy Policy](https://www.elections.virginia.gov/privacy-policy/), read in full | Privacy practices, website security, public disclosure under the Code of Virginia, and a "Disclaimer" about translations and links. Nothing on reuse. | Nothing for reuse |
| Results site, [enr.elections.virginia.gov](https://enr.elections.virginia.gov/results/public/virginia/elections/2026-November-General) | No terms; a map disclaimer about district boundaries | Nothing stated |
| [Virginia.gov: Privacy Policy](https://www.virginia.gov/privacy-policy/), searched; its "Copyright" paragraph read in full | "The copyright to the virginia.gov website is owned by the Commonwealth of Virginia... Permission is granted to website visitors to make fair use of the contents", and asks anyone in doubt to request permission. It also says "this policy only applies to pages on the virginia.gov website." | Fair use only, **but for virginia.gov pages**, which the results aren't on |
| Census files, us-atlas | As in `docs/PIPELINE.md`, Part 8 | Credit in Sources, and the TIGER/Line note |

**The reading:** **copyright notice only** for the results: the Department of Elections says "All rights reserved" with no terms, the same standing as Ohio and South Carolina, whose footers the owner accepted on 2026-11-08. The portal's fair-use-only wording is closer to Massachusetts's, which kept that state out, but it says it covers virginia.gov pages only. The owner chose to build Virginia on 2026-11-19 after being told this.

## Build, from the repo root

| # | Command | Writes to `data/va/` | SHA-256 (first 16) |
|---|---|---|---|
| 1 | `python scripts/build_va_results.py` | `results-2026.json` | `bdfbf76d17c34639` |
| 2 | `python scripts/build_cities.py va` | `cities.json` | `c60b6bae2a967a2b` |
| 3 | `python scripts/build_precincts.py va` (reads #1) | `blocks.json.gz` | `67dab4a27fa91805` |
| 4 | `python scripts/build_landmask.py va` | `landmask.bin.gz` | `453fecb89f0b8dbd` |

## Numbers to expect

- 2 races on 133 localities; 2,529 precincts, all reporting, and every vote type "Fully Reported" in every locality
- 257 places, the largest Virginia Beach
- 163,491 blocks, 115,996 with adults, 6,745,054 adults
- A 7,611 × 3,348 land grid; 118,440 blocks drawn
- U.S. Senate: Mark R. Warner (Democratic) 2,251,628, Bert Mizusawa (Republican) 1,393,710, write-ins 9,800; 3,655,138 in all. Mizusawa carried 79 localities, covering 76% of the land; Warner won 61.6% to 38.1%. Fewest votes: Norton City, 1,064; most: Fairfax County, 487,016.
- U.S. House: 11 of 11 districts, 3,654,176 votes, seats 8 Democratic and 3 Republican. Independent, Libertarian and Green candidates and write-ins are gray.

Checks that stop the build: 133 localities, once each, matching the Census names; every locality's vote types "Fully Reported" and every precinct reporting; each locality has the state's candidates; in each locality, vote types and precinct rows each add up to every candidate's total; each candidate's localities add up to the statewide figure; each House district's localities add up to its total; one Democrat and one Republican for Senate, and a majority winner; every locality has at least 10 votes.

## What differs from earlier states

- **Projection:** parallels 37.0° and 39.0°, centered on 79.4° W.
- **Names:** the export writes "KING and QUEEN COUNTY" and the like; the build matches the Census's full names, uppercased. Census names end in "city", which the pages write as "City".
- **`countyWord`:** a new setting in `state.js`, read by `countyLabel()`. Pages used to add " County" after every name; now a state can set its own word (Louisiana: "Parish") or none (Virginia).
- **Authority wording:** `authority` is "the Virginia elections department", since the pages add "'s" and the department's name ends in "Elections" (as Rhode Island's does).
- **Incumbent:** Warner is marked by hand; the export marks no incumbents. House incumbents aren't marked.
- **Parties:** the export spells them out ("Democratic", "Independent", "Libertarian", "Green"); the build maps them to the site's codes.

## Gaps

- Unofficial: rebuild after the State Board of Elections certifies (date not looked up).
- No precinct view: precinct shapes weren't looked for. The export has precinct results.
- No By district view: Virginia's 2026 U.S. House lines weren't looked into.
- Hand-picked text: no tour, flights or history.

## How this was checked (2026-11-19)

- In the browser at desktop width: the page opens on U.S. Senate, flat, in 3D and in dots; the headline reads "Mizusawa won 79 of 133 counties, which cover 76% of Virginia's land area"; the dot view counts 3,655,138 voters, matching the race; U.S. House reads "Gray: Independents (I) + Libertarians (L) + Greens (G) + write-ins, 1.7%"; the county menu lists "Fairfax City" and "Fairfax County"; the home page and Sources list Virginia. No console errors.
- **Not checked:** phone width, and the land grid in close-ups.

# West Virginia: the record

Built 2026-11-09, for the 2026 general election only, and **county-only**: bar view by county and dot view, with no By precinct view or precinct menu. This has the shape of `docs/PIPELINE.md`, Part 7.

**One race.** U.S. Senate is the only contest between candidates on the ballot statewide. U.S. House has two districts; the rest are legislative, county or amendments.

**Results are unofficial.** The results site says "Unofficial Results", with 55 of 55 counties and 1,642 of 1,642 precincts reporting, and "Last updated Monday, November 9, 2026, 4:36:26 PM". Its reporting chart counts 3 counties "Completely Reported" and 52 "Declared Results". County canvasses come next, then state certification; the dates weren't looked up. Save the figures again after that, rebuild, and compare.

## Raw files, under `data/raw/wv/` (not committed)

| What | Path | SHA-256 (first 16) |
|---|---|---|
| U.S. Senate by county, read in Chrome from the [results site](https://results.enr.clarityelections.com/WV/127496/web.345435/#/summary)'s own files (`json/en/summary.json` for candidates and parties, `json/ALL.json` for county votes; Last-Modified Nov. 9, 2026, 22:36:26 GMT) and written out by hand. Its `note` says how. | `results/senate-extract.json` | `3e9d941a3106473b` |
| 2020 Census redistricting file ([zip](https://www2.census.gov/programs-surveys/decennial/2020/data/01-Redistricting_File--PL_94-171/West_Virginia/wv2020.pl.zip)) | `census/wv2020.pl.zip` | `8356c49f300e9c18` |
| 2020 census block shapes ([zip](https://www2.census.gov/geo/tiger/TIGER2020/TABBLOCK20/tl_2020_54_tabblock20.zip)) | `census/tl_2020_54_tabblock20.zip` | `04e931a5d288ed62` |

**Access:** the results site returns 403 to plain `curl`, so the figures were read in a browser, as Texas's hand-read extracts were (`docs/PIPELINE.md`, Part 2.5). The site's Detail XML and XLS reports weren't downloaded. **Gap:** the page code that read the files wasn't saved as a file; the extract's note describes it, and the build checks that the counties add up to the statewide row.

## Terms of use, read 2026-11-09

This is a reading of the published pages, not legal advice. Nobody at the Secretary of State's office has been asked.

| Source | What it says | What it asks of us |
|---|---|---|
| WV.gov [Content Disclaimer](https://www.wv.gov/policies/disclaimer), read in full | About accuracy: the State doesn't warrant the information, and anyone relying on it does so at their own risk. | Nothing for reuse |
| WV.gov [Legal Notices](https://www.wv.gov/policies/legal-notices) | Copyright complaints go to Tyler Technologies, the portal's vendor. No limit on reusing State content found. | Nothing |
| Results site footer | "© 2026 Copyright: SOE Software", the results vendor, with no terms link | See below |
| Census files, us-atlas | As in `docs/PIPELINE.md`, Part 8 | Credit in Sources, and the TIGER/Line note |

**The reading:** the terms are **silent** on reusing results. The owner chose West Virginia on 2026-11-09 after being told this. The results site's footer claims copyright for its vendor, presumably in the site itself; the vote counts are the state's.

## Build, from the repo root

| # | Command | Writes to `data/wv/` | SHA-256 (first 16) |
|---|---|---|---|
| 1 | `python scripts/build_wv_results.py` | `results-2026.json` | `338d28cb967af827` |
| 2 | `python scripts/build_cities.py wv` | `cities.json` | `1b110227c76f7379` |
| 3 | `python scripts/build_precincts.py wv` (reads #1) | `blocks.json.gz` | `5a7113d9372b4901` |
| 4 | `python scripts/build_landmask.py wv` | `landmask.bin.gz` | `9ca8e901e1bd4d26` |

## Numbers to expect

- 1 race on 55 counties; 465,388 ballots; 1,210,385 registered
- 151 places, the largest Charleston
- 72,558 blocks, 50,577 with adults, 1,432,932 adults
- A 4,373 × 3,861 land grid; 53,077 blocks drawn
- U.S. Senate: Shelley Moore Capito (Republican) 266,746, Rachel Fetty Anderson (Democrat) 173,647, S. Marshall Wilson (Constitution) 17,182; 457,575 in all. Capito carried 52 counties.

Checks that stop the build: all precincts reporting; 55 counties, once each, matching the Census; each county's candidates add up to its total; counties add up to the statewide row; one Democrat and one Republican; and every county has at least 10 votes (fewest: 1,564, Doddridge).

## What differs from earlier states

- **Projection:** parallels 37.8° and 40.1°, centered on 80.2° W.
- **Party codes:** the site's `CST` is written `CON`, so the pages say Constitution. Capito is marked as the incumbent by hand in the build.
- **No write-ins** are listed.

## Gaps

- The extract was made by hand in the browser, as above.
- Canvass and certification dates not looked up.
- Hand-picked text: no tour, flights or history.

## How this was checked (2026-11-09)

- In the browser at desktop width: the results page opens on U.S. Senate; the dot view counts 457,575 voters, matching the race. No console errors.
- **Not checked:** phone width, the 3D view, and the land grid in close-ups.

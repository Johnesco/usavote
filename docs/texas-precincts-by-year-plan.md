# Plan: Texas precincts by year, 2010–2024

Written 2026-11-18. Steps 1 to 3 done 2026-11-18; the owner took every recommended choice in step 3. Steps 4 and 5 built
2026-11-19 (`scripts/build_tx_precinct_years.py`, `data/tx-years/`); steps 6 to 8 in progress.

## Why

Texas's By precinct view and Dots use one set of precinct lines (2024, `VTDs_24PG`) and one race's precinct votes (2024 U.S.
Senate) for every race and year. Every other race is an estimate: each party's county total is shared among the 2024 precincts by
that party's 2024 Senate vote there. County totals come out right, but inside a county the estimate is wrong in three ways, and
more so the further a year is from 2024:

1. **Votes where people didn't live yet:** a 2010 race is drawn on 2024 precincts, so new suburbs get votes and older
   neighborhoods too few.
2. **The 2024 voting pattern applied to earlier years:** suburbs moved toward Democrats and many Hispanic areas toward
   Republicans between 2008 and 2024; the estimate shows the 2024 lean in earlier years.
3. **Precinct names from the wrong year:** hover cards and Go to give 2024 precinct numbers.

The Texas Legislative Council posts each general election's own precinct lines and precinct votes from 2010 to 2024. Using them
replaces the estimate with real counts on the right lines for 8 of the site's 10 years.

## What's available

| Election | Precinct lines (VTDs) | Precinct votes | Census geography |
|---|---|---|---|
| 2008 | no 2008 lines; use 2010's | in the 2010 to 2018 results zips, re-tallied by the Council onto later lines (found in step 2) | 2010 |
| 2010 | [`archived_vtds_2010s`](https://data.capitol.texas.gov/dataset/archived_vtds_2010s): 2010 General | [`historical_elections_2010s`](https://data.capitol.texas.gov/dataset/historical_elections_2010s): 2010 General zip | 2010 |
| 2012, 2014, 2016, 2018 | `archived_vtds_2010s` | `historical_elections_2010s` zips; also the TED API, race by race | 2010 |
| 2020 | `archived_vtds_2010s` (2010 Census) **and** [`vtds`](https://data.capitol.texas.gov/dataset/vtds): `VTDs20G_2020` (2020 Census) | both archives | 2010 and 2020 |
| 2022 | `vtds`: `VTDs_22G` | [`comprehensive-election-datasets-compressed-format`](https://data.capitol.texas.gov/dataset/comprehensive-election-datasets-compressed-format): 2022 General | 2020 |
| 2024 | `vtds`: `VTDs_24PG` (in use now) | same: 2024 General | 2020 |
| 2026 | not posted yet | not posted yet | – |

All of these are listed in the portal's catalog as Creative Commons Attribution, with the same unversioned license link as
`VTDs_24PG`. That is the catalog, not a reading of each page: see step 1.

**Format test (2026-11-18):** the TED API's 2018 U.S. Senate file (`/api/Offices/456/2/vtd`) has the same columns as the 2024
file the build reads now (`CNTYVTD, VTDKEY, <Last><Party>_<YY>G_<Office>, …`), with 9,712 precincts. So the current reader works
for older years with only the column suffix changed.

**Caveats from the Council:** VTDs are the census-block version of county precincts and "can differ from actual election
precincts". Its election data "may be small differences" from official results.

## Steps

Work on a new branch from `main`. Everything downloaded goes in `data/raw/` (git-ignored). Nothing built from the new data is
committed until step 1 is done and recorded.

### 1. Read the terms in full (before anything is published)

Read each dataset page and its catalog record in a browser, in full, and the license page they link to:

- `vtds` (2020, 2022, 2024 lines)
- `archived_vtds_2010s` (2010–2020 lines)
- `historical_elections_2010s` (2010–2020 votes)
- `comprehensive-election-datasets-compressed-format` (2020–2024 votes)
- the per-election datasets, if the TED API is used (`2012_general` … `2024_general`)
- `planc2193` (U.S. House lines for 2022 and 2024, step 7)
- the portal's About page, again, for anything new

Confirm they allow redrawing, simplifying and republishing. Record the reading under Texas in `docs/PIPELINE.md`, Part 5, as
was done for `VTDs_24PG`. If any page is silent, unclear or limiting, keep that year local and ask the owner.

**Done 2026-11-18:** all of them, PLANC2193 included, are licensed Creative Commons Attribution. Recorded in `docs/PIPELINE.md`,
Part 5, "Texas precincts by year and PLANC2193 terms". Still to read: any readme inside the zips, in step 2.

Also found: the Council's comprehensive files re-tally earlier elections (back to 2012) onto newer precinct lines. That could
serve as a check on the per-year build, or as a way to compare years on the same lines.

### 2. Download and measure, locally

For each year, download the lines and the votes. Then, before building anything, measure and write down:

- **Totals:** each race's precinct votes added up by county, against the Secretary of State's county totals the site already
  shows (`results-history.json`, `results-2026.json`). How many counties differ, and by how much.
- **Coverage:** every precinct with votes has a shape, and the reverse.
- **Blocks:** what share of 2020 Census blocks fall inside a precinct for each year. The 2010–2018 lines are drawn on 2010
  Census blocks, so some 2020 blocks may land just outside; give those to the nearest precinct in their county.
- **Chamber races:** whether each year's file has U.S. House, Texas House and Texas Senate votes by precinct, and in what form.

Stop here and bring the numbers to the owner for the decisions below.

**Done 2026-11-18.** Downloaded into `data/raw/census-dl/tlc/years/` (git-ignored): `lines-<year>.zip` for 2010 to 2022 (2010s
archive for 2010–2018, `VTDs20G_2020` for 2020, `VTDs_22G` for 2022) and `votes-<year>.zip` for 2010 to 2024 (2010s archive
through 2018; the comprehensive zips for 2020, 2022, 2024), with their URLs in `urls.txt`. 730 MB.

What's in the zips: each results zip re-tallies every general, primary and runoff from the 1990s (2012 in the 2020s zips) onto
that year's precincts, one CSV per election (`County, FIPS, VTD, cntyvtd, [vtdkeyvalue,] Office, Name, Party, Incumbent, Votes`)
and one of registration and turnout. Each zip but 2024's has a readme. The readmes have no terms; they describe the data, give the
precinct counts (8,337 in 2010, 8,936 in 2018, 9,586 in 2022), and say that from 2008 every third-party and independent candidate
is included, with write-ins summed. **2008 is in the 2010 to 2018 zips,** re-tallied by the Council onto later lines.

**Totals, statewide races** (each race's precinct votes added up by county, D / R / other, against the site's county rows):

| Year | Races | Share of votes in a county gap | Counties with any gap |
|---|---|---|---|
| 2008 (on 2010 lines) | President, U.S. Senate | 0.11%, 0.01% | 143, 47 |
| 2010 | Governor, Lt. Governor, Attorney General | 0.05%, 0.04%, 0.29% | 65, 39, 30 |
| 2012 | President, U.S. Senate | 0.09%, 0.02% | 124, 36 |
| 2014 | U.S. Senate, Governor, Lt. Governor, Attorney General | 0.02% or less | 25 to 51 |
| 2016 | President | 0.29% | 120 |
| 2018 | U.S. Senate, Governor, Lt. Governor, Attorney General | 0.05% or less | 43 to 45 |
| 2020 | President, U.S. Senate | 0.12%, 0.04% | 116, 120 |
| 2022 | Governor, Lt. Governor, Attorney General | 0.06% or less | 26 to 129 |
| 2024 | President, U.S. Senate | 0.15%, 0.02% | 113, 77 |

Most gaps are a few votes. Thirteen are 5% and 100 votes or more, and some of those look like mistakes on the Secretary of
State's pages, which the site copies faithfully (checked against the saved pages in `data/raw/sos-*.htm`):

| Race | County | Site (Secretary of State) D / R / other | Council | Note |
|---|---|---|---|---|
| 2010 Attorney General | Kaufman | 4,653 / **1,470** / 415 | 4,653 / 14,790 / 415 | The SOS page gives 6,538 votes in all, against 19,936 for Governor on the same ballot |
| 2010 Governor | Haskell | 117 / 262 / 12 | 578 / 911 / 48 | SOS: 391 votes (10.7% turnout), against 1,459 for Attorney General |
| 2010 Lt. Governor | Haskell | 89 / 277 / 11 | 420 / 1,012 / 44 | Same |
| 2010 Governor, Lt. Gov., Attorney General | La Salle | 744 / 534 / 23 … | 462 / 374 / 18 … | Site higher in all three |
| 2018 Attorney General | Somervell | **363** / 2,938 / 74 | 636 / 2,937 / 74 | Digits swapped on one side |
| 2022 Attorney General | Brooks | 1,198 / **818** / 40 | 1,198 / 618 / 40 | One digit |
| 2008 President, U.S. Senate | Sutton; Garza; Wheeler | | | 100 to 160 votes |
| 2016 President | Presidio | 1,458 / 652 / 98 | 1,458 / 474 / 88 | |

Found in step 6 (2026-11-19), by county in district races, where the Council's precinct counts and the site's county total differ
by more than 10%: 2020 Texas House in Presidio (site 1,475 votes, Council 2,085), 2010 U.S. House in Hardin (12,265 and 14,265)
and La Salle (1,288 and 843). They are shown as counted, as chosen in step 3. Dots takes each county's number of dots from the site's
total, so there they change only where dots sit.

**District races:** the Council includes every contested district by precinct. It leaves out nearly every race with one
candidate: 40 to 81 Texas House districts a year, a few Texas Senate and 0 to 5 U.S. House. Only two left out had more than one
candidate (one Texas House race each in 2012 and 2018). The districts it does include match the site within 2%, except 2022 U.S.
House District 14 (2.3%).

**Coverage:** every precinct with votes has lines and every precinct with lines has votes, in every year. In 2022, 456 precinct
names differ only in letter case between the two files (`0010a` and `0010A`); match them case-blind.

**Blocks:** of 442,628 Census blocks with adults, 81 (1,821 adults, 0.01%) fall outside every precinct of their county on the
2010–2018 lines, and none on the 2020–2024 lines. 211 to 328 precincts a year have no block's center inside; their votes would go
in one circle at their center, as now.

**2024 U.S. Senate:** the TED API copy the site uses and the portal's licensed zip agree in all 9,712 precincts.

### 3. Decisions for the owner

| Decision | Options | Recommended, after step 2 |
|---|---|---|
| Totals that don't match | Show the Council's counts as counted, so a county's precincts may not quite match its column; or scale each precinct so its county matches | As counted: gaps are 0.3% of votes or less, and scaling would also carry the Secretary of State's mistakes into the precincts. Say so in Method |
| The Secretary of State's apparent mistakes (table above) | Leave the county view as the Secretary of State publishes it; or correct those counties from the Council, saying so; or ask the Secretary of State | Leave as published and note them in the record for now; ask the owner before changing the "every total must match the source" rule |
| Precinct column height | One scale for every year (biggest precinct in any year), or one per year | One scale, as the district views do |
| 2008 | Keep the 2024 estimate; or use the Council's 2008 votes re-tallied onto 2010 precincts | The Council's re-tally, on 2010 lines, labeled as such |
| 2026 | Keep the 2024 estimate until the Council posts 2026, then rebuild | Yes; add it to the rebuild-after-certification list |
| District races by precinct | Real counts for contested districts; districts with one candidate have no precinct votes | Real counts where the Council has them; one-candidate districts' precincts show no column, as their district does |
| Dots | Real votes for every year; or By precinct only, with Dots left on 2024 | Real votes for every year: the blocks fit every year's lines (step 2) |
| 2020 lines | 2010 Census version or 2020 Census version | 2020 Census (`VTDs20G_2020`): it fits the 2020 blocks with no misses |

### 4. Build

Extend `scripts/build_precincts.py` (or add `scripts/build_tx_precinct_years.py`), keeping today's 2024 output byte-identical:

- **Per year:** read the lines (Lambert → lon/lat, as now), read every mapped race's precinct votes, merge any precinct under 10
  votes into its nearest neighbor in its county (privacy, as now), simplify the outlines along shared borders (as now).
- **Files, per year:** `data/tx-precincts/<year>-shapes.json.gz` (about 1 MB each, as now) and `<year>-votes.json.gz`
  (each race's `[dem, rep, other]` by precinct, in the shapes' order, with precinct codes for Go to).
- **Dots:** keep one blocks file. Per year, add only which precinct each block falls in, which should be far smaller than
  repeating the blocks. Check the size before choosing this.
- **Checks that stop the build:** the totals and coverage checks from step 2, every vote kept through merging, and statewide
  totals within the agreed tolerance of the Secretary of State's.
- Expect roughly 10–15 MB of new data files for 8 years, each loaded only when its year is on screen.
- **As built (2026-11-19):** `scripts/build_tx_precinct_years.py` writes `data/tx-years/blocks.json.gz` once, and per year
  `<year>.json.gz` (votes, and which runs of the county's blocks each precinct holds) and `<year>-shapes.json.gz`. See
  `docs/PIPELINE.md` Part 3, #6.

### 5. On the page

- `state.js`: replace the single `base` with a list of years that have real precinct votes, and the estimate source for the
  others (2008, 2026).
- `app.js`: load the year's lines and votes when By precinct is on and the year changes; swap the columns; Go to's precinct
  menu from that year's codes. Use "as counted" wording for every race with real votes, and "estimated from …" only for 2026,
  naming the race and year the estimate comes from.
- The estimate strip along the map's bottom (`estimateNote`, `docs/PIPELINE.md` Part 5) has to follow the new cases: none for
  a counted year by precinct; for 2026, estimated from the 2024 pattern; for 2008, that the votes are the Council's re-tally
  onto 2010 lines, so precincts whose lines changed hold votes the Council shared out; and for Dots in every year, that each
  dot's spot is estimated from where adults live.
- Chamber races by precinct: real counts where the files have them.
- `dots.js` / `dots-worker.js`: the year's precinct votes and block assignments.
- Method and Sources: one paragraph on which years are counted and which estimated, and credit, license link and note of
  changes for each Council dataset.
- Run `node scripts/stamp.mjs`.

### 6. Check in the browser

For one year from each kind (2010, 2016, 2020, 2024, 2026): By precinct flat and 3D, hover, Go to a precinct, Dots, switching
years with By precinct on. Compare a county or two known to have shifted, such as Hidalgo and Collin, between 2012 and 2024.
Make sure Kansas and South Carolina's precinct views still load.

### 7. U.S. House districts for 2022 and 2024

If PLANC2193's terms allow it (step 1), add it to `scripts/build_districts.py` for 2022 and 2024, and use the per-year precinct
votes to check that every district's results reach the counties its lines do. Run the same check for the 2022 and 2024 Texas
House and Senate results, which has never been done.

### 8. Record and publish

Update `docs/PIPELINE.md` (sources, hashes, build, checks, what's estimated), then open one PR. Pushing the branch publishes
it, so only after step 1's reading is recorded.

## Not covered

- District views before 2022 (older plans; some list no license).
- 2008 on its own precinct lines. The Council has 2008's votes only re-tallied onto 2010 and later lines.
- Correcting the county view where the Secretary of State's pages look wrong (step 2's table): a separate decision.

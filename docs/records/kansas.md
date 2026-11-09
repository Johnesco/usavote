# Kansas: the record

Built 2026-11-08, for the 2026 general election only, **with a By precinct view**: bar view by county and by precinct, and dot view. Pages: `kansas.html`, `kansas-voters.html`. Shape of this record: `docs/PIPELINE.md`, Part 7.

**Results are unofficial** and will change. The Secretary of State's site leaves out provisional ballots and votes for write-in candidates. Counties count provisionals in their canvass by Nov. 16, 2026, and the State Board of Canvassers certifies by Dec. 1, 2026. Save the pages again after each, rebuild, and compare. The Governor and Secretary of State margins are under 1% (0.70% and 0.81%), so the pages say who **led**, not who won.

## Raw files, under `data/raw/ks/` (not committed)

All saved 2026-11-08, Central time.

| What | Path | How | SHA-256 |
|---|---|---|---|
| 2026 results: statewide page and 105 county pages of [Unofficial Kansas Election Results](https://ent.sos.ks.gov/kssos_ent.html), six statewide races as printed on screen | `results/ks-results-extract.json` | Chrome, with `scripts/ks_extract_results.js` | `c79364afe93bd8170755bba1a2bd620f53b4cbe648b3bd1c0a7dc743720ea643` |
| 2020 Census redistricting file ([zip](https://www2.census.gov/programs-surveys/decennial/2020/data/01-Redistricting_File--PL_94-171/Kansas/ks2020.pl.zip)) | `census/ks2020.pl.zip` | curl | `ac6b4ae5e2af4c8d639b46748d55927ee7821756f6073cc4f8238c1fb00498ee` |
| 2020 census block shapes ([zip](https://www2.census.gov/geo/tiger/TIGER2020/TABBLOCK20/tl_2020_20_tabblock20.zip)) | `census/tl_2020_20_tabblock20.zip` | curl | `a0ccda5300d1994008b51bf345c77bc1b04adc8df6219b226c64b80d3a611198` |
| IKE Lab, [Precinct Result Shapefiles](https://ike-lab.com/electionresults.html), 2024 General (`files/ks_2024g.zip`; server date Sept. 9, 2025) | `shapes/ks_2024g.zip` | Chrome, link clicked | `51dbf1ad2616222aaef55b8f79f5db5847f9a86f0556eaf726ae2d7c727e17de` |
| IKE Lab, 2022 General (`files/ks_2022g.zip`). Opened, not used | `shapes/ks_2022g.zip` | Chrome, link clicked | `e252b2ad989ba2e8e4e4da2fa5df19d5f3ec6255717cd25e145dec8d6b1c77d7` |
| Kansas Secretary of State, [2024 official vote totals](https://sos.ks.gov/elections/24elec/2024-General-Election-Official-Vote-Totals.pdf). Cross-check | `sos/2024-General-Election-Official-Vote-Totals.pdf` | curl | `0f0d5cdf0f6a03dbc2557cf2cb820fbd729cadc1ef484e85986fe41771cc2813` |
| [2024 Presidential Results](https://sos.ks.gov/elections/24elec/2024-Presidential-Results.xlsx), by precinct. Cross-check | `sos/2024-Presidential-Results.xlsx` | curl | `f83ad5a1db33e2bdc7c3139b85ed7973a186854cae3b675667c4fedb0f545239` |
| [2024 President precinct-level results](https://sos.ks.gov/elections/24elec/2024-General-Election-President-Precinct-Level-Results.xlsx). Saved, not read by a build | `sos/2024-General-Election-President-Precinct-Level-Results.xlsx` | curl | `54bb06a9a34a3b1a672e9007b8884a18f1862b516cad13772c05c28dc361053e` |

Site stamps when read: every page "Last Updated" Nov. 8, 2026, 9:14 or 9:15 PM; the latest "County Last Reported" Nov. 6, 2026, 6:32 PM, which is the "as of" time shown on the pages. The site says it updates through Nov. 6. The extract's own stamp is `2026-11-09T04:29:07Z`.

**How the results site was read.** Plain scripts get a Cloudflare 403, and so did `fetch()` from inside its own page. That wasn't worked around: each page was opened in a Chrome tab and read from the screen, as the comments in `scripts/ks_extract_results.js` describe. County page HTML wasn't saved, only what the script read.

**How the zips were saved.** IKE Lab's server gave curl a 406 before this work, so curl wasn't retried. Links clicked by script didn't produce a file; a real click on each link, one per new tab, did.

## Base race: 2024 President

Harris against Trump, from `ks_2024g.zip`. It's the most recent statewide contest with one Democrat and one Republican, and it's the only one in the zip; the file has no 2024 U.S. Senate race because Kansas had none.

- **Shapes:** 4,193 polygons, none empty, on the Kansas North state plane (U.S. survey feet). Every one of the 104,252 census blocks with adults fell inside a precinct of its own county by containment, so the projection and county names are sound.
- **Votes:** statewide and in all 105 counties, candidate by candidate, they equal the Secretary of State's 2024 file, and statewide they equal the official totals PDF: Harris 544,853, Trump 758,802, Kennedy 16,322, Oliver 7,614. `build_ks_results.py` stops otherwise.
- **By precinct:** the state's file has 44 Shawnee County votes on a line labeled `KSA 25-2701(a)(2)`, with no shape. IKE Lab's file has none there and instead has those 44 votes in eight Shawnee precincts the state's file shows at 0 (17 Croco, 21 Urban Hills, 83 Ichabod Washburn, Ward Pct 0107, 0109, 1217, 1301, 1308). Those eight are IKE Lab's placement, not the state's count. Every other precinct named in both files has the same votes. What the label means wasn't looked into.
- **No license note in either zip.** The 2024 zip has no documentation file, and its metadata has no license or credit text. Its field names (`G24PREDHAR` and so on) were read from their pattern and confirmed by the totals. The 2022 zip's `documentation_2022g.txt` says where its data came from and has no license terms, so nothing conflicts with CC-BY. It says the 2022 shapes are based on Census 2020 redistricting data, county files and a 2020 VEST file; the 2024 zip doesn't say. Those upstream terms weren't read.

## Terms of use, read 2026-11-08

This is a reading of the published pages, not legal advice. Nobody at these agencies or IKE Lab has been asked about the site.

| Source | What it says | What it asks of us | Done |
|---|---|---|---|
| IKE Lab precinct files | [About page](https://ike-lab.com/about_ike.html): "released on a CC-BY license", credit to IKE Lab; links to [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The data are provided as is. | Credit, a license link, a note of changes | In the Sources text of `kansas.html` |
| 2026 results and 2024 files (Secretary of State) | No license found on the results pages or the [election results page](https://sos.ks.gov/elections/election-results.html). The [KORA policy statement](https://sos.ks.gov/general-services/kora-policy-statement.html) describes public records requests. | Nothing stated. Named as source, and results called unofficial | Yes |
| Census redistricting file | No license found for these files. The technical documentation (below) says copyright protection isn't available for U.S. government works. | Cite | Yes |
| TIGER/Line blocks | [TIGER2020PL technical documentation](https://www2.census.gov/geo/pdfs/maps-data/data/tiger/tgrshp2020pl/TGRSHP2020PL_TechDoc.pdf), Chapter 1: TIGER/Line is a registered trademark, usable only to refer to the nature of a product. Repackaged data should carry a "conspicuously placed statement" to that effect on the cover, the site's first page, or somewhere as visible; marks should carry the ® symbol where convenient. It also disclaims accuracy and says boundaries are for statistical use. | A prominent statement | **Partly: see Gaps** |
| us-atlas | ISC license, per npm (Part 5 of the pipeline doc). Not re-read here. | Nothing while the site loads it from a CDN | Yes |

Chapter 1 frames the request around the trademark. The Sources wording: TIGER/Line® is a registered trademark of the Census Bureau, and the site and its data files aren't Census Bureau products and haven't been reviewed by the Bureau.

**Gap in the record:** not read were any Cloudflare or hosting terms for `ent.sos.ks.gov`, the Kansas Open Records Act itself, the whole KORA statement, and VEST's terms.

## Build, from the repo root

| # | Command | Time | Writes to `data/ks/` | SHA-256 (first 16) |
|---|---|---:|---|---|
| 1 | `python scripts/build_ks_results.py` | 1 s | `results-2026.json` | `e2d4257e9464a9b6` |
| 2 | `python scripts/build_cities.py ks` | 1 s | `cities.json` | `b11c3bce33537979` |
| 3 | `python scripts/build_precincts.py ks` (reads #1) | 12 s | `precincts.json.gz` | `2ef5be4675c3b09c` |
|   | (same script) | | `precinct-shapes.json.gz` | `e24e49e1b26dbe71` |
| 4 | `python scripts/build_landmask.py ks` | 5 s | `landmask.bin.gz` | `8830ef7a302168ad` |

Numbers to expect:

- **Results:** 6 races on 105 counties, 4,168 precincts reporting of 4,168.

| Race | Democrat | Republican | Others | Total | D-led counties |
|---|---|---|---|---:|---:|
| U.S. Senate | Hamilton 561,143 | Marshall 505,558 | Graham (L) 33,195 | 1,099,896 | 11 |
| Governor | Holscher 551,243 | Masterson 543,599 | none | 1,094,842 | 9 |
| Attorney General | Mann 552,753 | Kobach 539,297 | none | 1,092,050 | 10 |
| Secretary of State | Day 515,738 | Proctor 524,555 | Morgan (United Kansas) 46,036 | 1,086,329 | 9 |
| State Treasurer | Luengo 479,827 | Johnson 554,383 | Lund (L) 49,091 | 1,083,301 | 6 |
| Insurance Commissioner | Sykes 513,291 | Hawkins 530,494 | Koehn (L) 38,773 | 1,082,558 | 6 |

- **Left out:** U.S. House and legislature (by district, not this pass), the constitutional amendment, judicial retention, State Board of Education.
- **Cities:** 270 places; largest Wichita.
- **Precincts:** 4,193 shapes; 3,746 with votes and 447 with none (left out, as in Texas); 189 merged under 10 votes (692 votes); 3,557 precinct entries, each with at least 10 votes; 2024 votes all kept (544,853 / 758,802 / 23,936). 172,529 blocks, 104,252 with adults, 2,229,316 adults. 3,557 outlines, 62,976 points, 0.16 MB; 0 blocks matched by nearest instead of containment; 7 precincts with votes but no adults on record, each placed as one circle. 634 adults are in zero-vote precincts, so no dots are placed there.
- **Land grid:** 6,638 × 3,423 cells of 100 m; 117,503 blocks drawn; 0.27 MB.

Checks that stop the build: see the docstring of `build_ks_results.py` (all precincts reporting; counties add up to the statewide page, candidate by candidate; county pages' state figures and percentages agree; IKE Lab's votes match the state's), plus the adult total against the Census file's state record and "merging must keep every vote" in `build_precincts.py`.

## What differs from Texas

- **Projection:** parallels 37.5° and 39.5°, centered on 98.3° W, from the TIGER file's bounds (36.993° to 40.003° N, 102.052° to 94.588° W) by the one-sixth rule. `build_landmask.py` uses the same values.
- **Precinct adapter:** one file holds both votes and shapes, in another projection and with polygon-Z records; a separate `if ST == "ks":` block reads it. Precinct names are IKE Lab's, without the county prefix.
- **Base race isn't a race on the pages.** There's no history file, so `STATE.base.raceId` is null: every race's precinct columns are labeled estimates, and the 2024 presidential counts show only on a chosen precinct's line.
- **Land area:** the Census file's `AREALAND`, as for Oklahoma.
- **Candidates:** the site doesn't say who is an incumbent, so none are marked. Governor is shown without running mates, as on the site.
- **No tour or flights.** `tour: false`, `flights: []`.

### Changes to shared files (all through `STATE` settings or `if ST == "ks"`)

- `state.js`: `KANSAS` const and list entry.
- `app.js`: `STATE.won`, `winner`, `otherVotes`, `votesCounted`, `twoCandidates`. The Texas wording said "won", "counting every candidate including write-ins" and "reports no third-party or write-in votes", which Kansas's data can't support. With the settings absent, `app.js` reduces to its old text exactly (compared by script).
- `dots.js`: `STATE.radiusScaleAt`. It measured block radii at a hard-coded spot in Texas, far outside Kansas's parallels. Absent means the old spot, so Texas and Oklahoma don't change. **Oklahoma still measures at that Texas spot**, which looks like the same bug; left alone as asked.
- `build_cities.py`, `build_landmask.py`: dict entries. `build_precincts.py`: dict entries, the Kansas block, a `meta` block, and three conditions widened (`ST in ("tx", "ks")`, file name, early exit).

## Gaps

- **TIGER statement placement.** Chapter 1 asks for it on the first page of the website or somewhere as visible. It's in the Sources on `kansas.html`; `index.html` wasn't to be edited here, so the homepage doesn't carry it. The coordinator should decide.
- **Not checked in a browser.** No page has been opened: browser checking is after the merge. Dots inside county lines and the pages' wording are unverified on screen.
- **Holes on the By precinct map.** The 447 precincts with no 2024 votes aren't drawn, as in Texas. They total 161 of the shapes' 82,301 square miles; the largest is 60 square miles in Riley County (`NV4819`). Check how this looks.
- **Land grid.** Empty cells are correct over Milford and Tuttle Creek (picture and spot check), and spot checks at Perry, Cheney and El Dorado lakes were empty. A spot check at a rough Wilson Lake coordinate came back lived on; the coordinate wasn't confirmed, so that's unresolved. Kansas's large rural blocks mean 64.5% of the grid's box counts as lived on, so the mask is coarse in the country.
- **2024 pattern on 2026 votes:** a precinct's estimate assumes each party's voters are spread as in 2024, and the 2024 lines may have changed.
- **Eight Shawnee precincts** carry IKE Lab's placement of 44 votes (above).
- **Extraction script:** the run read the `step1` note from the page with one extra line of console code, since folded into the saved script. The saved script as a whole hasn't been rerun.
- **County page text wasn't compared to the statewide map or detail pages**, only to the statewide page's figures.

## How this was checked (2026-11-08)

- All Kansas builds run from raw files; rerunning gives the same hashes.
- `data/ks/results-2026.json` validated against the results-adapter shape: 105 counties, 6 races, `[dem, rep, other, total]` rows that add up, candidates matching county sums.
- us-atlas 3.0.1 has 105 county codes starting with 20, the same set as the results file, and `STATE.countyCount` is 105.
- Every county has entries in `precincts.json.gz` (fewest: 3, Greeley) and the same number of outlines in `precinct-shapes.json.gz`. None under 10 votes.
- Dot totals: the worker draws one dot per vote and each county adds up exactly by its rounding, so each race's dots equal its total above. This was checked from the code and the file totals, not by running the worker.
- Land grid decoded and viewed over the whole state and over Milford and Tuttle Creek.
- Texas and Oklahoma: this branch's edited scripts were run in a throwaway folder against the main checkout's raw files (this worktree has none), and all eight outputs came out byte-identical to the committed ones: `data/cities.json` `f20625af55f659e7`, `data/precincts.json.gz` `32ee28870ca8fcc9`, `data/precinct-shapes.json.gz` `06539cd799cf987e`, `data/landmask.bin.gz` `44544362e7852d66`, `data/ok/results-2026.json` `23414a8bb3514866`, `data/ok/cities.json` `03e595d5154fc24e`, `data/ok/blocks.json.gz` `cc635054c09e4a3b`, `data/ok/landmask.bin.gz` `3c08d559b02e7cb8`. `build_data.py` and `build_history.py` weren't changed or rerun.
- Texas and Oklahoma pages: the `app.js` and `dots.js` changes fall back to the old text and values when a state has no such setting. Neither page was opened.

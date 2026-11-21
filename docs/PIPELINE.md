# From raw data to the map: record and template

This is how the Texas 2026 site goes from public source files to what appears on screen, written so someone can repeat it for
Texas or adapt it for another state. It covers only what the site does now. Parts 1 to 5 are the record for Texas. Part 6 is the
template for other states, and Part 7 is the record of its first use, on Oklahoma.

**How this was checked (2026-11-08):**

- All the data builds were rerun from the local raw files. All five published data files then on the site came out byte-identical to the hashes in Part 3; `data/precinct-shapes.json.gz` was added later the same day and its hash is from its first build.
- Five source files were downloaded again and compared. The results feed, the precinct results, the precinct shapes, the county
  shapes and the land-area file all matched exactly.
- The two big Census files were compared by size only (they match). They were not downloaded again.
- The whole sequence has not been run on a new machine from an empty folder.
- Published pages were checked by eye in a browser. There are no automated tests of the pages.

## 1. What it takes

- Python 3.13 (this run: 3.13.14). `numpy` 2.4.2 and `Pillow` 12.1.1 are needed by `build_landmask.py` and `build_infographic.py` only. The other scripts use just the standard library.
- About 1 GB of disk space for raw files. They stay local (`data/raw/` is in `.gitignore`), except the hand-read extracts in step 2.5.
- The pages have no build step. They load three.js r160, d3-geo 3.1.1, topojson-client 3.1.0 and us-atlas 3.0.1 from a CDN at those exact versions.

## 2. Get the raw data

Save every file at the path shown, because the scripts read from those paths. Record the date and a hash when you do: election feeds can change after you download them.

### 2.1 Files you can download directly

| What | Local path under `data/raw/` | SHA-256 (first 16) |
|---|---|---|
| 2026 results by county, all races ([feed](https://goelect.txelections.civixapps.com/api-ivis-system/api/s3/enr/election/countyInfo/53815)) | `sos-countyInfo-53815.json` | `9c95edda76f5bfcb` |
| 2024 U.S. Senate votes by precinct ([Texas Legislative Council](https://ted.capitol.texas.gov/api/Offices/510/2/vtd)) | `census-dl/tlc/sen24_vtd.json` | `03464ba753587d2e` |
| 2024 precinct shapes, `VTDs_24PG` ([zip](https://data.capitol.texas.gov/dataset/4d8298d0-d176-4c19-b174-42837027b73e/resource/906f47e4-4e39-4156-b1bd-4969be0b2780/download/vtds_24pg.zip)) | `census-dl/tlc/vtds_24pg.zip` | `4adf61b5d97bdc7b` |
| 2020 Census redistricting file, P.L. 94-171 ([zip](https://www2.census.gov/programs-surveys/decennial/2020/data/01-Redistricting_File--PL_94-171/Texas/tx2020.pl.zip), 100 MB) | `census-dl/pl/tx2020.pl.zip` | `6fee8ca5759eb494` |
| 2020 census block shapes, TIGER/Line ([zip](https://www2.census.gov/geo/tiger/TIGER2020/TABBLOCK20/tl_2020_48_tabblock20.zip), 746 MB) | `census-dl/tiger/tl_2020_48_tabblock20.zip` | `c0e71f4bf463c212` |
| County shapes, us-atlas 3.0.1 ([json](https://cdn.jsdelivr.net/npm/us-atlas@3.0.1/counties-10m.json)); only the infographic reads this copy, the pages load it from the CDN | `us-atlas/counties-10m.json` | `145aaf5d1433352a` |

The county results feed is one JSON object whose `upload` field is base64-encoded JSON. It's labeled unofficial until the state canvass, and it still matched the saved copy on 2026-11-08.

**Scripted access may fail for the feed:** later on 2026-11-08 it returned a 403 to a plain script, and its results site runs a browser security check. Don't work around the block: save the feed from a browser or use the state's official files, and record the date and hash as usual.

```bash
mkdir -p data/raw/census-dl/pl data/raw/census-dl/tlc data/raw/census-dl/tiger data/raw/us-atlas
```

Then download each URL to its path, for example:

```bash
curl -L -o data/raw/census-dl/pl/tx2020.pl.zip https://www2.census.gov/programs-surveys/decennial/2020/data/01-Redistricting_File--PL_94-171/Texas/tx2020.pl.zip
```

### 2.2 Land area

Download the [2024 Gazetteer counties file](https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2024_Gazetteer/2024_Gaz_counties_national.zip) and keep the header line plus the lines starting with `TX`. Save it as `data/raw/census-2024-gazetteer-tx-counties.txt` (255 lines; SHA-256 `4abe6f4d7f8c21bc`). Filtering the national file this way reproduces the saved copy.

### 2.3 Statewide results page, as a cross-check

Save [the Secretary of State's statewide page](https://electionresults.sos.state.tx.us/results.html) as `data/raw/sos-results-statewide.html` (SHA-256 `f9aff35afa2063a6`). The saved copy says "Updated 11/04/2026 04:59 PM". This page changes over time, so the saved copy is the record.

### 2.4 Earlier elections, for the history page (optional)

Save each race's page from the Secretary of State's [Election History](https://elections.sos.state.tx.us/index.htm) as `data/raw/sos-<year>-<race>.htm` (2008 to 2018, 16 pages). **Gap in the record:** the pages don't contain their own URLs, and the election and race ids used weren't written down. Only the URL pattern is known: `elchist<election id>_race<race id>.htm`.

### 2.5 Hand-read extracts (committed, because they can't be fetched by script)

These are in the repo under `data/raw/`. The results site blocks scripted downloads, so they were read in a browser and checked there.

- `sos-enr-2020-extract.json`, `sos-enr-2022-extract.json`, `sos-enr-2024-extract.json`: major statewide races from `static/data/election/<id>/<version>/County.json` on [results.texas-election.com](https://results.texas-election.com/races) (election ids 44144, 47009, 49664)
- `sos-house-2008-2018.json`, `sos-house-2020-2024.json`, `sos-senate-2008-2018.json`, `sos-senate-2020-2024.json`: every legislative and congressional district by county

**Gap in the record:** the browser code that did this extraction wasn't saved. Each file's `note` field says what was checked, and `build_history.py` checks the files again.

## 3. Build the data files

Run these in order from the repo root. Each script stops with an error if a check fails.

| # | Command | Time | Writes | SHA-256 (first 16) |
|---|---|---:|---|---|
| 1 | `python scripts/build_data.py` | 1 s | `data/results-2026.json` | `7f34c02bb451acb7` |
| 2 | `python scripts/build_history.py` (needs #1) | 1 s | `data/results-history.json` | `a2188f1957d6e3b6` |
| 3 | `python scripts/build_cities.py` | 4 s | `data/cities.json` | `f20625af55f659e7` |
| 4 | `python scripts/build_precincts.py` | 3 min | `data/precincts.json.gz` | `32ee28870ca8fcc9` |
|   | (same script as #4) | | `data/precinct-shapes.json.gz` | `06539cd799cf987e` |
| 5 | `python scripts/build_landmask.py` | 1 min | `data/landmask.bin.gz` | `44544362e7852d66` |
| 6 | `python scripts/build_tx_precinct_years.py` | 30 min | `data/tx-years/blocks.json.gz` | `c09127178a073062` |
|   | (same script as #6), one pair per year from 2008 to 2024 | | `data/tx-years/<year>.json.gz`, `<year>-shapes.json.gz` | below |

`build_blockgroups.py` isn't needed if you downloaded the Census file in step 2.1. Its output was used by an earlier placement method and the site no longer reads it.

What each one does, and the numbers to expect for Texas:

**#1 Results.** Takes every race that's on the ballot in all 254 counties, plus U.S. House, Texas House and Texas Senate added up by county.
- Stops unless every county's candidates add up to its total, all precincts are reporting, every county matches a Census code, and each candidate's total matches the statewide page.
- Maps only races with exactly one Democrat and one Republican. Expect 18 statewide races and 3 chambers.

**#2 History.** Builds 50 races, 2008 to 2024, on 254 counties each, with the same kinds of checks.

**#3 City names.** Reads the Census file's place records (summary level 160). Keeps incorporated places with at least 500 people and unincorporated census-designated places with at least 10,000. Expect 994 places.

**#4 Where voters are placed.** Expect 9,712 precincts, 668,757 blocks, and 442,628 blocks with adults.
1. Reads 2024 Senate votes by precinct and each precinct's shape, converting the shapes to longitude and latitude.
2. Reads each block's center point, land area and adults (Census table `P3_001N`). Stops unless adults add up to 21,866,700.
3. Assigns each block to the precinct containing its center point. All matched by containment here.
4. Merges any precinct under 10 votes into the nearest precinct in its county, for voter privacy (143 merged, 550 votes). Stops unless every vote is still there.
5. Finds each county's most crowded spot: the most adults within half a mile of a block.
6. Writes a compact gzipped file, with each precinct's code for the "go to a precinct" menu (a merged precinct lists every code in it).
7. Writes the precincts' outlines to `data/precinct-shapes.json.gz`, in the same order, simplifying to about 55 m along shared borders so neighbors still meet. A merged precinct keeps all its pieces. Expect 9,206 outlines, 377,785 points and a 0.94 MB file.

**#5 Where dots can't go.** Draws every block with people or housing units onto a 100 m grid in the map's projection. Everything else is empty, such as lakes, bays, airports and big parks. Expect 455,943 blocks drawn on a 13,180 × 12,083 grid, and a 1.03 MB file.

**#6 Precincts by year.** Each general election from 2008 to 2024 on its own precinct lines with its precinct votes as counted, from the Texas Legislative Council (CC BY; the terms are in Part 5, the plan in [`texas-precincts-by-year-plan.md`](texas-precincts-by-year-plan.md)). The raw zips go under `data/raw/census-dl/tlc/years/`, which isn't committed; their URLs are in `urls.txt` there. 2008 has no lines of its own, so it uses the Council's re-tally of the 2008 votes onto the 2010 lines.
1. Writes one blocks file shared by every year: the 442,628 blocks with adults, by county, and each county's most crowded spot from #4.
2. For each year, reads the lines and every race the site has for that year, matched by county and precinct code. Stops if a precinct with votes has no lines.
3. Gives each block to the precinct containing its center point, as #4 does.
4. Merges any precinct with under 10 votes in a statewide race into the nearest precinct in its county. Stops unless every vote is still there.
5. Stops unless each statewide race is within 0.5% of the Secretary of State's total (`data/results-history.json`). The votes are shown as the Council counted them, not scaled to match. The chambers' totals come out lower than the site's in most years, by up to 46% for the Texas House: the Council's files leave out districts with one candidate, and the site's totals count them. Those districts' precincts stand empty by precinct.
6. Writes the year's votes and outlines (simplified as in #4).
7. Stops unless `precinctYears.tallest` in `state.js` equals the tallest precinct of any year and race, so every year shares one height scale. This check runs only when every year is built.

Expect, per year:

| Year | Lines | Precincts | Merged | Largest statewide gap | `<year>.json.gz` | `<year>-shapes.json.gz` |
|---|---|---:|---:|---:|---|---|
| 2008 | the 2010 lines (VTD10G), the Council's re-tally | 8,400 | 132 | 0.10% | `8ef7a036c61082ad` | `4051146803485f45` |
| 2010 | VTD10G | 8,400 | 166 | 0.27% | `b726163eea915da4` | `b6de1ac108a087d5` |
| 2012 | 2012 general VTDs | 8,952 | 222 | 0.08% | `3a7e36f9b4435134` | `c5e44e19a1d8cf41` |
| 2014 | 2014G_VTD | 8,996 | 287 | 0.01% | `17a3edd00969d9d0` | `dd1d9bece8f9f839` |
| 2016 | VTDs_2016G | 8,941 | 195 | 0.16% | `0f593c4cec12d1fa` | `ed32531edc7702d9` |
| 2018 | VTDs_2018G | 9,082 | 196 | 0.04% | `be5bdd0bd31f0628` | `1fe6545c9d4d89aa` |
| 2020 | VTDs20G_2020 (2020 Census blocks) | 9,157 | 151 | 0.07% | `eba35e68c2f55989` | `dd40769fb970d11b` |
| 2022 | VTDs_22G | 9,634 | 164 | 0.05% | `d9f47545d9ec4c2c` | `2ecd15e9bab4cf37` |
| 2024 | VTDs_24PG | 9,712 | 145 | 0.15% | `13958ad5cf1e47e2` | `235a4c5196a3ab20` |

Each votes file is 0.24 to 0.36 MB and each shapes file 0.91 to 0.94 MB, so about 13.8 MB in all with the 2.01 MB blocks file; a page loads only the years it shows. On the 2010s lines (2008 to 2018), 81 blocks have their center in no precinct of their county and go to the nearest; on the 2020s lines, none. Between 2 and 10 precincts a year have no block's center inside them, so their dots go in one circle. The tallest precinct of any year and race is 13,511 votes.

**Optional images:**

```bash
python scripts/build_infographic.py
python scripts/build_infographic.py 4
```

These write the 4K and 16K images, which aren't committed. `scripts/panels.html` draws the share image; the command is in the README.

## 4. From data files to the screen

Nothing is computed on a server. Each page fetches its files and works everything out in the browser.

**Pages:** `index.html` is the U.S. homepage (`home.js`). Bar view and dot view share the go-to menus (`places.js`). `texas.html` runs `app.js` and shows every race and year (`history.html` only forwards old links there), `story.html` runs `story.js`, and `voters.html` runs `voters.js`.

**The map:**
- Projection: d3 equal-area conic, parallels 27.5° and 35°, centered on 99.5° W, fitted to ±500 map units.
- Color: the county winner's share of all votes, in 10-point bands.
- Height: total votes on a linear scale shared by all races, with the tallest column at 420 map units.
- Stacking: by votes, the most on top and the fewest at the bottom (usually the winner on top). The guided flights' columns (`map3d.js`) keep the fixed order: runner-up, others, winner.
- City names (`cities.js`): about 100,000 people and up when the whole state shows, and smaller places as you zoom in. At most 30 show at once.
- Controls: **Flat** or **3D**. In 3D the map turns slowly (0.08 radians a second, the County Flythrough's closing pace) in every bar view, until the reader takes hold of it or switches **Rotation** off; then drag moves, right-drag or two fingers turn, and scroll zooms.
- Bar view and dot view hand each other the camera in the link (`?at=x,y,distance,tilt,heading`), so switching keeps the place and zoom. The dot view always settles flat and north up, so it hands a 3D bar view's tilt and heading back unchanged.

**Bar view by precinct** (`precinct-columns.js`), on the results page's **By precinct** toggle: one mesh holds every precinct's column, stacked in the shader. Height is on one scale at every zoom and in every year: 70 map units for the largest precinct of any race and year (`precinctYears.tallest` in `state.js`). In Texas, a race from 2008 to 2024 stands on its own year's precincts with its votes as counted (#6 in Part 3, `data/tx-years/`; 2008 on the 2010 lines), and 2026 on the 2024 lines, estimated by step 1 below. The page loads each year's set when it's first shown (`app.js`, `loadSet`). U.S. House, Texas House and Texas Senate districts with one candidate have no precinct counts, so their precincts stand empty. Estimates are labeled on screen (Part 5).

**Dot view: one dot per voter** (`dots.js`, `dots-worker.js`), on `voters.html`, which the **Dot view** button in bar view opens for the race on screen (`?race=`). It shows any race and year, always on the flat map:
1. **Share by precinct:** each party's county total is split among precincts by that party's share of its 2024 county vote there. In Texas, a race from 2008 to 2024 is split by its own year's precincts and their counted votes instead (`dots.js`, `loadPrecinctYear`, `countedVotes`); in a district race, voters in districts with one candidate, which have no precinct counts, are split among those precincts by the year's first statewide race.
2. **Share by block:** each precinct's share is split among its blocks by adults.
3. **Whole dots:** systematic rounding turns those shares into whole dots, so every county adds up exactly to its 2026 result.
4. **Place each dot:** a random spot around its block, on a bell curve whose standard deviation is 0.75 of the block's radius, cut off at 2.5 standard deviations.
5. **Keep it off empty land:** a dot on an empty grid cell tries again, up to 16 tries in all, then sits at the block's center. In Texas about 183,000 of 9,889,704 dots get a new spot and 31 end at the center.

The random numbers are seeded, so a given race draws the same dots each time (seed 2026 + the race's position in the list; the U.S. Senate race is first, so 2026). If the precinct file fails to load, dots spread evenly over each county; if the grid fails, dots skip step 5.

**Keeping it fast:** the worker sorts the dots into a 256 × 256 grid of tiles, and each frame draws only the tiles on screen, so a close-up doesn't process every dot in the state. Within that sort are four levels for far-off views, nested so that coming closer only adds dots: a level cuts each tile into cells (4, 8, 16 or 32 per side) and keeps at most 4, 4, 8 or 16 dots a cell, sampled evenly through the tile, so only dots stacked on others are left out and sparse places keep all of theirs. A level is used only while its cells are at most half a pixel across at the nearest ground on screen; closer than the last level, while dots are appearing, and while one county's dots are enlarged, every dot is drawn. The dots are held only on the graphics card once uploaded, so a lost graphics context places them again. Nothing is drawn while the picture isn't changing.

**The voter tour** (`voters.js`), the Texas Population Density Tour, offered in that page's top bar for the U.S. Senate race: the counties to visit are chosen by hand and the numbers are computed from the data. Each visit shows a metro from high up, then one county, then its most crowded spot. Close-ups zoom until the typical gap between voters is drawn 16 pixels wide. Camera moves use a smooth zoom-and-pan path (van Wijk and Nuij, 2003) that favors zooming out over panning.

**Publishing:** GitHub Pages serves the `main` branch as it is. Only what's in the repo goes out, so keep raw data out.

**Version stamps:** after changing any `.js` or `.css` file, run `node scripts/stamp.mjs` before committing (`--check` only reports). GitHub Pages lets a browser keep a file for about 10 minutes, so without stamps a returning reader could get a new page with an old script and see a broken map (this happened on 2026-11-14: the Shade by Votes page came up black because a cached script looked for the slider the new page no longer had). The script adds `?v=<hash of the file>` to every page's script and stylesheet links, and gives each page an import map from `./x.js` to `./x.js?v=…` for every script and style, so imports between scripts, the dot worker and `dotlook.css` (both loaded by `import.meta.resolve`) are stamped too. Only files git tracks go in the maps. Pages in `scripts/` are left alone. It can't help a reader whose browser kept an old page whose scripts it has since dropped; that clears within the 10 minutes.

## 5. Rules to keep

These came out of decisions made along the way. Keep them in any state.

- **Check publishing rights before publishing anything.** Before any data, page, doc, commit message, pull request or issue text goes online, read the source's terms of use and confirm they cover this use: redrawing, simplifying and republishing. If they're silent or unclear, keep that data and anything built from it local and git-ignored, and ask the source or the owner first. Pushing to any branch publishes, because the repository is public: a pull request that's never merged is still online. Taking something down afterward doesn't reliably remove it. In 2026, Oregon's results reached a pushed branch before its terms were settled, and the only way to remove them was to delete and recreate the repository.
- **No voter files.** Ballots are secret, so a person's vote can't be known. Voter lists are also restricted in how they can be used, and putting names at home locations would be a privacy problem.
- **Label estimates.** A dot's spot and color are estimates, and every close view has to say so. Current wording: "Spots and colors are estimated."
- **Say so at the bottom whenever the map shows estimates.** Anything estimated rather than counted gets a strip along the map's bottom edge, starting with **Estimated:** (or **Partly estimated:**) and saying how it was estimated. On a phone the strip sits just below the map. It's `estimateNote` in `app.js`, and it shows for: precinct columns shared out from county totals (every race but a state's `base` race), every dot (spots always; colors too, unless the precinct votes are counted), and a `base` race whose precincts are partly estimated (`base.partEstimated`, South Carolina). County and district views are counts and show none. Unofficial results aren't estimates and say so elsewhere. Asked for by the owner on 2026-11-18. Any new estimate must add its case there.
- **Hide very small precincts.** Merge anything under 10 votes before publishing, even if the source publishes it.
- **Don't go down to households.** Stop at blocks and a coarse land grid, and don't use building locations in a way that points to individual homes.
- **Every total must match the source.** County totals have to match exactly, and the scripts should stop if they don't.
- **Say when results are unofficial,** and rebuild after the canvass. Once a state's own results site marks them official, set `official: true` and `returns: 'official results'` in `state.js`: the pages then say "official results" and drop "unofficial until". Don't name a certification date that wasn't read at a state source.

### Texas terms of use, read 2026-11-08

This is a reading of the published pages, not legal advice. Nobody at these agencies has been asked about the site.

| Source | What it says | What it asks of us |
|---|---|---|
| `VTDs_24PG` shapes (Texas Legislative Council) | The [dataset](https://data.capitol.texas.gov/dataset/vtds) is listed as Creative Commons Attribution, linking to a general [license page](http://www.opendefinition.org/licenses/cc-by) with no version named. | Credit, a license link and a note of changes, all in the page's Sources |
| 2024 U.S. Senate votes by precinct (Texas Legislative Council) | The API used shows no license. The portal's [2024 General](https://data.capitol.texas.gov/dataset/2024_general) dataset, which has a U.S. Senator file, is listed as Creative Commons Attribution. | The same credit |
| Results, 2008 to 2026 (Secretary of State) | No license found. The [records policy](https://www.sos.state.tx.us/records.shtml) presumes government information is available to the public, and the [disclaimer](https://www.sos.state.tx.us/disclaimer.shtml) provides the site "as is". The [link policy](https://www.sos.state.tx.us/linkpolicy.shtml) bars framing its pages, presenting its content as your own, or misrepresenting that content or its origin. | Name the source, link rather than frame, and keep estimates labeled |
| Census files | No license found. The [Census API terms](https://www.census.gov/data/developers/about/terms-of-service.html) cover the API, which wasn't used. | Nothing found |
| us-atlas | ISC license, per npm. It redistributes Census boundaries. | Nothing while the site loads it from a CDN |

**Gap in the record:** not read were the state's website linking policy (a search summary says public information may be copied if it doesn't suggest state endorsement, but the full conditions weren't seen), any terms from Civix, the vendor behind the results feed (both results sites' footers point to the Secretary of State's policies), and the rest of the link policy. The two copies of the 2024 U.S. Senate votes weren't compared.

### Texas terms for commercial use, read 2026-11-17

The owner asked whether the Texas views could be sold, for example printed on merchandise. Every page below was read in full in a browser, looking for anything about commercial use. This is a reading of the published pages, not legal advice, and no agency was asked.

| Source | What it says | For selling |
|---|---|---|
| Secretary of State: [Disclaimer](https://www.sos.state.tx.us/disclaimer.shtml), [Link Policy](https://www.sos.state.tx.us/linkpolicy.shtml), [Open Records Policy](https://www.sos.state.tx.us/records.shtml), [Privacy Policy](https://www.sos.state.tx.us/privacy.shtml), all listed on its [Website Policies](https://www.sos.state.tx.us/policies.shtml) page | The Disclaimer says using the site means agreeing to its terms, but those terms only disclaim warranties and liability. The Link Policy says not to frame its pages, "present Secretary of State content as its own, or otherwise misrepresent" it, or "misinform users about the origin or ownership" of it; protected marks must be used lawfully. The Open Records Policy says "All government information is presumed to be available to the public", which is about access. Nothing grants a license, and nothing mentions commercial use. | **Silent.** No grant and no limit. Conditions: name the Secretary of State as the source, don't present the results as your own, and keep estimates labeled so nothing misrepresents the counts |
| Both results sites, [Civix's election-night site](https://goelect.txelections.civixapps.com/ivis-enr-ui/races) and [results.texas-election.com](https://results.texas-election.com/races) | Their footers link only to the Secretary of State's policies above (checked on the second site's links). Neither shows terms or a copyright line of its own. Civix wasn't checked further | Same as the Secretary of State |
| State of Texas: [Site Policies](https://www.texas.gov/about/site-policies), Linking and Legal notices tabs | The Linking policy repeats the Secretary of State's and adds "or in any way attempt to modify the content and present it as the content of Texas.gov". Legal notices cover trademarks, a DMCA procedure and warranty disclaimers, and say references to commercial products "shall not be used for advertising or product endorsement purposes". Footer: "Copyright © 2026 State of Texas. All rights reserved." These cover Texas.gov; whether they reach the Secretary of State's sites is inferred. The state policy the Secretary of State's Link Policy links to, on `dir.texas.gov`, returns "Page Not Found". | No limit on selling. Don't present altered maps as the state's, and don't suggest the state endorses a product |
| `VTDs_24PG` shapes and the [2024 General](https://data.capitol.texas.gov/dataset/2024_general) votes (Texas Legislative Council) | Both dataset pages list "Creative Commons Attribution" and link to the Open Definition's [cc-by page](https://opendefinition.org/licenses/cc-by/), which names versions 1.0 to 4.0 and points to [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). That deed allows adapting "for any purpose, even commercially". | **Allowed,** with credit, a license link and a note of changes on the product or its listing. The 2024 votes the site uses came from the TED API, which shows no license; the portal's copy is the licensed one, and the two weren't compared |
| [Texas Legislative Council](https://tlc.texas.gov/) site | Footer links: training, HUB and wireless policies, and public information requests. No terms of use, copyright policy or reuse wording found. [TED](https://ted.capitol.texas.gov/), where the 2024 votes came from, rendered a blank page and wasn't read | Nothing found |
| PLANC2333 (U.S. House lines) | Read again: the dataset page still has no License section | **Silent,** as recorded in Part 9. The 2026-11-12 choice covered the website only |
| Census files | Part 8: U.S. Government works have no copyright | **Allowed.** Cite the Bureau; don't use "TIGER/Line" in a product's name |

**The reading:** for selling, Texas's shapes, the 2024 precinct votes and the Census files are licensed, and the Secretary of State's results are silent: no license, nothing against commercial use, and conditions only about crediting the source and not misrepresenting it. So a view drawn only from the 2024 U.S. Senate precinct votes, the `VTDs_24PG` shapes and Census files rests entirely on licensed or public-domain sources, once the 2024 votes are confirmed to match the portal's licensed copy. Views using other years' results, or the U.S. House lines, rest on silence.

**Gap in the record:** Civix's own terms, the TED app's pages and the Texas Public Information Act weren't read. Only the CC BY 4.0 deed was read, not the legal code or earlier versions; the dataset pages name no version.

### Texas precincts by year and PLANC2193 terms, read 2026-11-18

For the plan in [`texas-precincts-by-year-plan.md`](texas-precincts-by-year-plan.md): each election's own precinct lines and votes, 2010 to 2024, and the U.S. House lines for 2022 and 2024. Every page below was read in full in a browser, including the License box beside each dataset, which the page's main text leaves out. This is a reading of the published pages, not legal advice, and the Council wasn't asked.

| Source | What it says | What it asks of us |
|---|---|---|
| [VTDs](https://data.capitol.texas.gov/dataset/vtds): `VTDs_24PG` (in use), `VTDs_22G`, `VTDs_22P`, `VTDs20G_2020` | License: "Creative Commons Attribution", "This dataset satisfies the Open Definition." VTDs "can differ from actual election precincts because precincts do not always follow census geography"; a precinct with no census match is merged into a neighbor's VTD. Join field `VTDKEY`. | Credit, license link, note of changes |
| [2010s Archived VTD & Precinct Geography](https://data.capitol.texas.gov/dataset/archived_vtds_2010s): VTDs for the 2010 to 2020 primaries and generals, on 2010 Census geography, and actual precinct shapes for the same elections | License: Creative Commons Attribution. "The boundaries included in this directory are for informational purposes only and may be approximate." That is a caution, not a limit on use. | The same, and keep calling precinct shapes approximate |
| [2010s Archived Election Data](https://data.capitol.texas.gov/dataset/historical_elections_2010s): one zip per general election, 2010 to 2020, each on that election's VTDs | License: Creative Commons Attribution. Compiled by the Council's Research Division "for redistricting purposes" from county and Secretary of State returns. "There may be small differences between the data presented here and official election results." | The same. Measure the differences against the Secretary of State's county totals before choosing how to show them |
| [Comprehensive Election Datasets](https://data.capitol.texas.gov/dataset/comprehensive-election-datasets-compressed-format): 2020 General, 2022 Primary and General, 2024 Primary and General | License: Creative Commons Attribution. Each zip has "2012 - 20xx election data" reported by that year's VTDs: the Council re-tallies earlier elections onto newer lines, as well as giving that year's own. | The same |
| Per-election datasets, such as [2018 General](https://data.capitol.texas.gov/dataset/2018_general), one TED API link per race | The 2018 page was read: License: Creative Commons Attribution. The catalog records of 2012, 2014, 2016, 2020, 2022 and 2024 General list the same license; their pages weren't each opened. There is no 2008 or 2010 dataset of this kind. | The same, if the TED API is used |
| [PLANC2193](https://data.capitol.texas.gov/dataset/planc2193), "TEXAS CONGRESSIONAL DISTRICTS, 2023-2026", tagged for 2022 elections on | License: Creative Commons Attribution. Unlike PLANC2333, which has none. | Credit, license link and note of changes, in the page's Sources and the file's `meta` |
| Portal [About](https://data.capitol.texas.gov/about) page | Describes the portal and gives the mapping and redistricting section's phone number. No terms. | Nothing |
| Open Definition [cc-by page](https://opendefinition.org/licenses/cc-by/), where every License link goes | Read again: points to CC BY 4.0 and lists versions 1.0 to 4.0; "allows re-distribution and re-use of a licensed work on the condition that the creator is appropriately credited." | Credit |
| [TED](https://ted.capitol.texas.gov/) | Still renders no text, so its terms, if any, weren't read | Nothing found |

**The reading:** every Council source the plan needs is licensed Creative Commons Attribution, which covers redrawing, simplifying and republishing, commercially or not, with credit, a license link and a note of changes. So the per-year precinct lines and votes for 2010 to 2024, and PLANC2193, can be published once built, with that credit on each page that uses them.

**Gap in the record:** the dataset pages name no license version, as before. The TED API shows no license itself; the per-election datasets that link to it are licensed. Of the per-election pages, only 2018's was opened. Nothing in the zips themselves (readme files, if any) has been read, since nothing was downloaded; read them when step 2 downloads them.

## 6. Template for another state

**Status:** used for Oklahoma (Part 7) and for the states in Part 8. `build_precincts.py`, `build_cities.py` and `build_landmask.py` take a state (`ok`, `ks`, `sc`, `oh`, `ia`, `nm`, `id`, `or`, `ga`, `sd`, `ca`, `ri`, `vt`, `wv`, `la`, `va`, `al`; no argument means Texas), so the table below shows where another state plugs in. Results and precinct readers are still written per state.

### Reusable as is

- **Census sources.** The same pattern exists for every state. Ohio's two files returned HTTP 200 when checked; other states weren't tried.
  - `.../01-Redistricting_File--PL_94-171/<State>/<st>2020.pl.zip`, which contains `<st>geo2020.pl` and `<st>000022020.pl`
  - `.../TABBLOCK20/tl_2020_<fips>_tabblock20.zip`
- **Other national sources:** the Gazetteer file and us-atlas county shapes.
- **Methods:** block assignment, the precinct merge, the land grid, dot placement, the map and the camera.

### Texas-specific code to make configurable

| Where | What to change |
|---|---|
| `state.js` | Name, state code, county count, projection, data file paths and where the state's results are and its county flights. Adding a state to `STATES` opens it on the homepage |
| `build_precincts.py` | Census file names, adult total (`TX_ADULTS`), precinct shape reader (fields `VTDKEY`, `CNTY`, `Shape_area`; the Lambert parameters), results reader (columns `AllredD`, `CruzR`) |
| `build_landmask.py` | Download URL and the projection constants, which must match the pages |
| `build_cities.py` | Census file names and the `Houston` sanity check |
| `build_data.py` | The whole script: feed format, `RACES` table, name fixes, chamber names, county count |
| `build_history.py` | The whole script, if you want a history page |
| `app.js`, `story.js`, `voters.js`, HTML | Written copy and sources still name Texas in places, plus hand-picked counties and metro groups. `FEATURED` and `MAJOR` in `app.js` list race ids |
| `build_infographic.py` | Copy, sources and projection |

### Choosing the projection

Texas's parallels sit about one-sixth and five-sixths of the way up its latitude range, and its center is the state's middle longitude. Use the same rule of thumb elsewhere. The grid in `build_landmask.py` must use the same parallels and center as the pages, or dots will be kept off the wrong land.

### The two adapters each state needs

Everything after these two is the same code, so write them first.

**Results adapter** writes `results-<year>.json`:
- `counties[]`: `{ fips, name, landSqMi }`
- `races[]`: `{ id, label, group, candidates: [{ name, last, party, incumbent, votes }], counties: [[dem, rep, other, total], ...] }`, in the same order as `counties`

**Precinct adapter** gives `build_precincts.py` two things:
- Shapes: `{ key, fips, rings (lon/lat), areaM2 }` per precinct
- Votes: `key -> (dem, rep, other)` for one recent statewide race, ideally the same office

Every precinct with votes must have a shape. The Texas script stops if one is missing.

### Steps for a new state

1. **Check what exists.** Find county results, precinct results with matching shapes, and the terms of use for each. Save the URLs. If there are no precinct votes or usable shapes, stop and decide on a fallback, because the party mix inside counties depends on them. Oklahoma's fallback, in Part 7, is county-only.
2. **Save the raw files** with dates and hashes, as in Part 2. Save any browser extraction code too, to avoid the gaps noted in Part 2.
3. **Write the results adapter.** Make it stop unless candidates add up in each county and counties add up to the state's published totals.
4. **Write the precinct adapter** and run the precinct build. Check that the state's adult total matches, that nearly all blocks fall inside a precinct, and that no votes are lost in merging.
5. **Run the city and land-grid builds.** Look at a picture of the grid over known lakes and airports, as was done for Texas, before trusting it.
6. **Set the projection and open the map.** Check that the dots sit inside county lines, that coastlines line up, and that the dot count equals the vote total.
7. **Pick the tour by hand:** the biggest metros, the most crowded county and the emptiest one. Order the stops to keep flights short.
8. **Rewrite the copy and sources.** Every figure should be computed from the data, not typed in.
9. **Review it** against Part 5, then publish.

### Things likely to differ by state

These are from general knowledge and haven't been checked state by state.

- **Results not reported by county:** Alaska has no ordinary counties, and New England states often report by town. Connecticut switched to planning regions in 2022, but the 2020 Census files still have its 8 counties, which match the 2017 county shapes in us-atlas; its towns are added up by county.
- **County look-alikes:** Louisiana parishes, Virginia's independent cities and similar units affect name matching, and Texas's "County" suffix handling won't cover them. The pages add a state's `countyWord` after each name (`countyLabel()` in `state.js`): "County" unless set, "Parish" for Louisiana, nothing for Virginia, whose names already say "County" or "City".
- **Precinct data:** other states may have no equivalent of the Texas Legislative Council's portal. The Voting and Election Science Team (Harvard Dataverse) and the Redistricting Data Hub are places to look, and the Census file includes 2020 voting districts for shapes, though they can be out of date (Part 7). Check each one's license.
- **Vote-by-mail and countywide votes** may be reported apart from home precincts, which would weaken the placement. Check this first in each state.
- **Other race shapes:** runoffs, ranked-choice voting, top-two primaries and races without exactly one Democrat and one Republican. `build_data.py` skips those races.
- **Scale limits:**
  - The dot format stores a county index in 8 bits (at most 256 counties), so each state gets its own map; all U.S. counties can't share one map this way.
  - Each dot takes 8 bytes, so a state with 15 million voters needs about 120 MB for dots alone.
  - The precinct files and land grid grow with the state. Texas's are 2.1 MB, 0.94 MB and 1.03 MB, and larger files make the site slower to load.
- **Census age:** the 2020 counts get less accurate where growth is fast. A new census means new block files and new hashes.

## 7. Oklahoma: the record

Built 2026-11-08, for the 2026 general election only, and **county-only**: bar view by county and dot view, with no By precinct view or precinct menu. **Results are official:** checked against the results site on 2026-11-19, unchanged (below).

### Raw files, under `data/raw/ok/` (not committed)

| What | Path | SHA-256 (first 16) |
|---|---|---|
| State results: **Export → Race Level Results - CSV** on [OK Election Results](https://results.okelections.gov/OKER/?elecDate=20261103) | `results/20261103_StateResults.csv` | `9e5251e74513d208` |
| County results: **County Level Results - CSV (Zipped)**, unzipped | `results/20261103_CountyResults.csv` | `e905301876340ad7` |
| Precinct results, used only to check the county file: **Precinct Level Results - CSV (Zipped)**, unzipped | `results/20261103_PrecinctResults.csv` | `50728dafc181a2d8` |
| 2020 Census redistricting file ([zip](https://www2.census.gov/programs-surveys/decennial/2020/data/01-Redistricting_File--PL_94-171/Oklahoma/ok2020.pl.zip)) | `census/ok2020.pl.zip` | `e95c99e6385f4ed3` |
| 2020 census block shapes ([zip](https://www2.census.gov/geo/tiger/TIGER2020/TABBLOCK20/tl_2020_40_tabblock20.zip)) | `census/tl_2020_40_tabblock20.zip` | `7b0445a7d613eab0` |

The exports were saved with the buttons on the results site, whose stamp read "Server TLU: 11/06/2026 06:26:09 PM". The site's own data calls need a login, and the Election Data Warehouse needs a registered account; neither was used.

### Why county-only

The first build used a statewide precinct layer from OU's Center for Spatial Analysis and the State Election Board, [hosted by INCOG](https://map11.incog.org/arcgis11wa/rest/services/PCT_OK_State/FeatureServer/0). Its terms, like those of the Center's [own 2020 item](https://www.arcgis.com/home/item.html?id=8c2c841e2eb54007bd1872c4274d6e07), say only "This Data is for Public use to be used as a spatial location tool." That may not cover republishing simplified outlines or using them to place votes, so the layer was dropped rather than the question left open. The Center wasn't asked.

Census 2020 voting districts didn't work as a replacement. Their codes match 1,345 of the 1,986 precinct codes in the 2026 results, covering 59% of U.S. Senate votes (663,650 of 1,118,730), and only 43% of adults fell in a district with the same code as their precinct on the layer. Using 2020 results on 2020 districts wasn't tried: no 2020 precinct file was found on the Election Board's results page.

What this costs: dots use one mix of parties across a county, so they don't show which neighborhoods lean which way, and the 2026 precinct results aren't on the map.

### Terms of use, read 2026-11-08

This is a reading of the published pages, not legal advice.

| Source | What it says | What it asks of us |
|---|---|---|
| Results | No license for the results. The [Election Board](https://oklahoma.gov/elections/about-us/information-and-records-requests.html) says historical results are on its website and need no records request, and the results page offers exports. | Nothing stated. The site credits the Board and says results are unofficial. |
| Census files | No license found for these files. The [Census API terms](https://www.census.gov/data/developers/about/terms-of-service.html) and their notice cover the API, which wasn't used. | Nothing found |
| us-atlas | ISC license, per npm. It redistributes Census boundaries. | Nothing while the site loads it from a CDN |

**Gap in the record:** not read were any results-site terms (none found), the Open Records Act itself, the Tyler Technologies terms and most of the Census open data page.

### Build, from the repo root

| # | Command | Writes to `data/ok/` | SHA-256 (first 16) |
|---|---|---|---|
| 1 | `python scripts/build_ok_results.py` | `results-2026.json` | `89da83b444e5a794` |
| 2 | `python scripts/build_cities.py ok` | `cities.json` | `03e595d5154fc24e` |
| 3 | `python scripts/build_precincts.py ok` (reads #1) | `blocks.json.gz` | `cc635054c09e4a3b` |
| 4 | `python scripts/build_landmask.py ok` | `landmask.bin.gz` | `3c08d559b02e7cb8` |

Numbers to expect: 8 statewide races and the U.S. House (Part 10) on 77 counties; 297 places; 180,154 blocks, 118,191 with adults, 3,010,698 adults; a 7,947 × 3,859 land grid.

Checks that stop the build: all precincts reporting; counties add up to the state file and precincts to the county file, candidate by candidate, in every mapped race; adults match the Census file's state record; and every county has adults and at least 10 U.S. Senate votes.

### What differs from Texas

- **Projection:** parallels 34.2° and 36.4°, centered on 98.7° W.
- **Dots:** `blocks.json.gz` has Texas's format, with one entry per county holding all its census blocks and its 2026 U.S. Senate votes. With one entry, a county's votes in any race are shared among its blocks by adults alone. A block goes to its county by its own Census code.
- **Pages:** `oklahoma.html` and `oklahoma-voters.html` are the Texas pages' markup with `<html data-state="oklahoma">` and their own wording, and without the By precinct buttons and precinct menu. `STATE.data.precinctShapes: null` and `STATE.base: null` turn those features off, and `?by=precinct` is ignored. Hand-written tours and history are left out through `STATE.tour`, `STATE.flights` and `STATE.data.history`.
- **Land area:** the 2020 Census file's `AREALAND`, not the 2024 Gazetteer.
- **County numbers:** precinct codes start with the state's county number, which is alphabetical except that Mc sorts before Ma. `build_ok_results.py` works this out from the Census names; it matched the layer's numbering for all 77 counties when the layer was dropped.
- **Candidates:** the file doesn't say who is an incumbent, so none are marked.

### How this was checked (2026-11-08)

- `data/precincts.json.gz` and `data/precinct-shapes.json.gz` were rebuilt after the script change and match the hashes in Part 3. Texas's by-precinct view, precinct menu and dot view were opened again.
- Oklahoma's pages were opened in a browser: bar view by county in 3D with `?by=precinct` ignored, no precinct controls, the go-to menus, and dot view with 1,118,730 Senate dots (the state's total), down to Tulsa County.
- Not checked: other screen sizes, or every race by eye.

### Official results, checked 2026-11-19

The results site's header now reads "Official Results". Its "Server TLU" stamp is still 11/06/2026 06:26:09 PM, the stamp the exports were saved under, and every race on the site's state page matched `results-2026.json` exactly: the eight statewide races and the five U.S. House districts (1,118,012 votes in all). So the exports weren't saved again. `build_ok_results.py` now calls these official results, with the date they were checked, so `results-2026.json` changed only in that wording; `blocks.json.gz` and both district files rebuilt byte for byte the same. The pages say "official results" (`official: true` in `state.js`). No certification date is given, since none was read at a state source.

## 8. States after Oklahoma: where the records are

Built 2026-11-08 and 2026-11-09, for the 2026 general election only. Each state's record has the shape of Part 7: sources and hashes, terms, build commands, expected numbers, differences from Texas, and gaps. Raw files are under `data/raw/<code>/`, not committed.

| State | Record | View | Precinct source | Rebuild after |
|---|---|---|---|---|
| Kansas | [`records/kansas.md`](records/kansas.md) | County and precinct | IKE Lab 2024 votes and shapes (CC-BY) | Nov. 16 county canvass and Dec. 1 certification deadline |
| South Carolina | [`records/south-carolina.md`](records/south-carolina.md) | County and precinct | 2026 U.S. Senate votes on Census 2020 voting districts | Done: rebuilt with official results 2026-11-19 |
| Ohio | [`records/ohio.md`](records/ohio.md) | County | None | The official canvass, about Nov. 24 |
| Iowa | [`records/iowa.md`](records/iowa.md) | County | None | The state canvass, about Nov. 30 |
| New Mexico | [`records/new-mexico.md`](records/new-mexico.md) | County | None | State canvassing board, Nov. 24 |
| Idaho | [`records/idaho.md`](records/idaho.md) | County | None | Nov. 24 canvass deadline |
| Georgia | [`records/georgia.md`](records/georgia.md) | County | None: 85.8% of Senate votes matched Census 2020 districts, under the 90% required | State certification, about Nov. 20 (from the survey, not read at a state source) |
| South Dakota | [`records/south-dakota.md`](records/south-dakota.md) | County | None | The state canvass; date not confirmed, so check from about Nov. 17 |
| California | [`records/california.md`](records/california.md) | County | None | Dec. 11 certification; about 3 million ballots were still to count |
| Rhode Island | [`records/rhode-island.md`](records/rhode-island.md) | County, from towns | None | Board of Elections certification; date not looked up |
| Vermont | [`records/vermont.md`](records/vermont.md) | County, from towns | None | State canvassing committee; date not looked up |
| West Virginia | [`records/west-virginia.md`](records/west-virginia.md) | County | None | County canvasses and state certification; dates not looked up |
| Louisiana | [`records/louisiana.md`](records/louisiana.md) | County (parishes) | None | None: built 2026-11-19 from results the site marks official |
| Virginia | [`records/virginia.md`](records/virginia.md) | County and independent city | None | State Board of Elections certification; date not looked up |
| Alabama | [`records/alabama.md`](records/alabama.md) | County, from precinct files | None | State Canvassing Board certification; date not looked up |
| New Hampshire | [`records/new-hampshire.md`](records/new-hampshire.md) | County, from towns and wards | None | Recounts or clerks' amendments; the recount schedule wasn't read |
| Connecticut | [`records/connecticut.md`](records/connecticut.md) | County, from towns | None | The state canvass; date not looked up |
| Delaware | [`records/delaware.md`](records/delaware.md) | County | None | None: built 2026-11-21 from results the site marks official |

**Census terms:** Parts 5 and 7 say no license was found for the Census files. The [TIGER/Line 2020 technical documentation](https://www2.census.gov/geo/pdfs/maps-data/data/tiger/tgrshp2020pl/TGRSHP2020PL_TechDoc_Ch1.pdf), Chapter 1, read 2026-11-09, covers this: U.S. Government works have no copyright, so "you are free to reproduce census materials as you see fit". It asks that the Census Bureau be cited, and that repackaged TIGER/Line data carry a conspicuous trademark statement on the first page of the website, which `index.html` now has.

**Results terms:** Kansas, South Carolina, Ohio and Iowa grant no license for their results, and Ohio's and South Carolina's sites carry an "All Rights Reserved" footer. The owner chose on 2026-11-08 to treat them as Texas and Oklahoma were treated: use the published results and credit the source.

**North Carolina is on hold.** The [state's terms](https://www.nc.gov/disclaimer-terms-use) say "for non-commercial use" and "without alteration", which doesn't clearly cover county totals, simplified outlines or dots. Its election board hasn't been asked.

**A stricter bar for the second batch.** On 2026-11-08 the owner asked for more states that run into no publishing rules. Eighteen more states were surveyed, reading what each says about reuse. These are readings of published pages, not legal advice, and no agency was asked.

| Outcome | States | Why |
|---|---|---|
| Built | New Mexico, Idaho, Georgia | No wording limiting reuse found. No license either, so this is silence, not permission, the same standing as Texas and Oklahoma |
| Limiting wording | Minnesota, Michigan, Colorado, Wisconsin, Pennsylvania, Nebraska, Arizona, Arkansas, Wyoming | Such as bans on copying or publishing, "All Rights Reserved", or fees or permission for commercial use. Whether some state-level terms reach the results sites is inferred |
| Asks you to check first | Washington | Its [policy](https://www.sos.wa.gov/web-sites-privacy-policy) lets people use most information, then recommends contacting the office for permission. Also has no statewide Democrat-against-Republican race. Could come back if the owner accepts the wording |
| Purpose limit, built by the owner's choice | South Dakota | State terms allow copying "for personal or informational use", so it doesn't meet this bar. The owner was told and chose it on 2026-11-09 as the fifth state. Its record has the reading |
| Poor fit | Montana | The only statewide race has the Democrat in third, and the Secretary of State's policy pages were unread |
| Site blocked | Nevada, Tennessee | Results and most terms couldn't be read. Nevada's state site also says "All Rights Reserved" |

**Oregon is kept local.** It has no license, and its terms say anyone using its sites agrees "to hold harmless and indemnify" the Secretary of State. The owner decided on 2026-11-09 that this isn't clear enough to publish. Its results, what's built from them, its pages, its scripts and its record are git-ignored, and it isn't in `STATES`. Its settings are in `data/raw/or/state-block.js`.

**A third survey, 2026-11-09.** The 25 states not yet surveyed were read the same way and ranked from the least restrictive terms to the most. The owner then chose five. These are readings of published pages, not legal advice, and no agency was asked.

| Outcome | States | Why |
|---|---|---|
| Built: terms say information may be copied | California, Rhode Island | California's [Conditions of Use](https://www.ca.gov/use/) call site information public domain "unless otherwise indicated"; its results site's footer says "© California Secretary of State". Rhode Island's [copyright policy](https://www.ri.gov/policies/copyright/) says compiled information "may be distributed or copied" and asks for credit. In both, applying portal terms to the results site is inferred |
| Built: silent, by the owner's choice | Vermont, West Virginia | No license and no limit found. The owner chose them knowing this. Their results sites carry bare copyright footers |
| Chosen, not built | Maine | No November 2026 results were posted on the Secretary of State's results page when checked on 2026-11-09, only June primary files. Its Census files are saved under `data/raw/me/` |
| Silent, not chosen | Alaska, North Dakota, New York; Louisiana was here until read again (below) | Accuracy or link disclaimers only. Alaska reports by House district, not county; North Dakota had no Governor or U.S. Senate race |
| Copyright notice only, or not fully read | None left: Florida, Illinois, Mississippi, Kentucky, Virginia, Alabama, New Jersey, Maryland, Missouri, New Hampshire, Connecticut and Delaware were all read again (below) | "All rights reserved" or a bare copyright line with no reuse terms found, or pages that wouldn't load |
| Limiting wording | Utah, Hawaii, Indiana, Massachusetts | Utah allows copying only if "not modified in any respect"; Hawaii bars commercial use; Indiana allows personal use only, with no republishing or derivative works; Massachusetts allows only fair use without permission |

**Florida and Illinois, read again on 2026-11-12.** The owner asked why these two weren't built, so their terms were read in full in a browser. This is a reading of the published pages, not legal advice, and neither agency was asked.

| State | What it says | Outcome |
|---|---|---|
| Florida | The Department of State's [Copyright and Terms of Use](https://dos.fl.gov/copyright/) say no material from the site, or from any site owned or operated by the State of Florida or the department, "may be copied, reproduced, republished, uploaded, posted, transmitted, or distributed in any way", except a download to a single computer "for your personal, non-commercial use only". Modifying the materials, or using them on any other website, is prohibited. The results site, [Florida Election Watch](https://floridaelectionwatch.gov/), has no terms of its own; its footer links to the department. | Limiting wording. Not built |
| Illinois | The State Board of Elections' [site](https://www.elections.il.gov/) shows no terms, copyright line or reuse policy on its homepage or its [results page](https://www.elections.il.gov/ElectionOperations/ElectionVoteTotals.aspx), which has "Download Vote Totals" buttons. The [State of Illinois legal notices](https://www.illinois.gov/about/privacy.html) disclaim liability, accuracy and endorsement and don't restrict copying; they recommend contacting "the originator of the data" with questions about appropriate use. That these notices reach the Board's site is inferred. | Silent, the same standing as Vermont and West Virginia, so the owner's to choose. Can't be built yet: the results list stopped at the 2026 General Primary, with no November 2026 results |

**Gap in the record:** Illinois's county clerks' sites, which may post election-night results under their own terms, weren't read, and precinct data wasn't looked for in either state. The Board's inner pages weren't searched for terms beyond the two named.

**Mississippi, read again on 2026-11-13.** The owner asked why it wasn't built. Its terms are silent: a disclaimer and "All rights reserved" footers, with no license and no limit on reuse, the same standing as Vermont and West Virginia. It isn't built, because the state posts no results table: only each county's certified precinct sheets, as scanned PDFs with no text, and 24 of 82 counties had posted. `docs/records/mississippi.md` has the reading and what building it would take.

**Louisiana and New York, read again on 2026-11-19.** The owner asked which states were ready, then to check these two. Both are silent, the same standing as Vermont and West Virginia. Louisiana's results were complete and marked official, and the owner chose to build it that day (`docs/records/louisiana.md`). New York isn't built: its election-night results were still short of Westchester, Chautauqua and Fulton counties, its certified results weren't posted, and its results site is behind a browser check (`docs/records/new-york.md`).

**Kentucky, Alabama, Virginia and New Jersey, read again on 2026-11-19.** The owner asked which other states could go ahead, then to check these four. This is a reading of published pages, not legal advice, and no agency was asked.

| State | Reading | Outcome |
|---|---|---|
| Virginia | Copyright notice only: "All rights reserved" from the Department of Elections, no terms. The portal's fair-use wording covers virginia.gov pages only | Built by the owner's choice, 2026-11-19 (`docs/records/virginia.md`) |
| Alabama | Silent: Alabama.gov's terms limit only material contributed by private parties | Built by the owner's choice, 2026-11-19 (`docs/records/alabama.md`) |
| New Jersey | **Permission given:** the state's Conditions of Use say anyone may "view, copy or distribute State information" | Not built: no general election results posted yet (`docs/records/new-jersey.md`) |
| Kentucky | Unclear: Kentucky.gov's legal notice points to Tyler Technologies' terms, which forbid copying data and commercial reuse of Tyler's services | Not built: ask first (`docs/records/kentucky.md`) |

**Delaware, Connecticut, New Hampshire, Missouri and Maryland, read again on 2026-11-20.** The owner asked which states were left, then to check these five. This is a reading of published pages, not legal advice, and no agency was asked.

| State | Reading | Results, 2026-11-20 |
|---|---|---|
| Delaware | **Public domain** for the official statewide totals (the open-data portal's "Official Election Results by Office", License: Public Domain); silent for the county figures on the results page | Built 2026-11-21 by the owner's choice: official, U.S. Senate, U.S. House (at large) and three more statewide races, checked against the public-domain file; only 3 counties (`docs/records/delaware.md`) |
| Connecticut | Silent: the portal's disclaimer is written for data users and limits only the State Seal and the CT.gov logo | Built by the owner's choice, 2026-11-20: Governor, four more statewide races and U.S. House, towns added up by county, each candidate's party lines added together (`docs/records/connecticut.md`) |
| New Hampshire | Copyright notice only: "All rights reserved", no terms | Built by the owner's choice, 2026-11-20: U.S. Senate, Governor and U.S. House, towns and wards added up by county; the files were saved through a browser, since scripts get 403 (`docs/records/new-hampshire.md`) |
| Missouri | Conditional, if MO.gov's Data Policy reaches the results: show its set disclaimer, and stop if the State asks | Complete, unofficial; State Auditor is the only statewide race between candidates (`docs/records/missouri.md`) |
| Maryland | Copyright notice only; the portal's terms are a linking policy (don't frame pages or present content as your own) | Unofficial and partial: two big counties still canvassing; Governor, Comptroller, Attorney General (`docs/records/maryland.md`) |

**Read terms directly.** An early survey quoted Washington's policy through a summarizing tool, which dropped the sentence recommending permission. Read the whole page.

**Build method:** the states were built in parallel on separate branches and merged, then all states were rebuilt from the merged scripts and compared with the committed files.

## 9. Texas district lines: the record

Built 2026-11-12, for the **By district** view on `texas.html`: one column for each U.S. House, Texas House or Texas Senate district, in place of the county columns. It's offered for a chamber's races in the years held on the lines below, and its button is off for every other race.

### Raw files, under `data/raw/census-dl/tlc/districts/` (not committed)

All four are shapefiles from the Texas Legislative Council's [Capitol Data Portal](https://data.capitol.texas.gov/): three downloaded 2026-11-12, and PLANC2193 on 2026-11-19.

| What | Local file | SHA-256 (first 16) |
|---|---|---|
| [PLANC2333](https://data.capitol.texas.gov/dataset/planc2333), U.S. House, "enacted by 89th Legislature, 2nd C.S., 2025" ([zip](https://data.capitol.texas.gov/dataset/748c952b-e926-4f44-8d01-a738884b3ec8/resource/5712ebe1-d777-4d4a-b836-0534e17bca01/download/planc2333.zip)) | `planc2333.zip` | `6797d6e39f76224f` |
| [PLANC2193](https://data.capitol.texas.gov/dataset/planc2193), U.S. House, "TEXAS CONGRESSIONAL DISTRICTS, 2023-2026" ([zip](https://data.capitol.texas.gov/dataset/b806b39a-4bab-4103-a66a-9c99bcaba490/resource/086a8045-7d52-4758-9d7d-6b57fe1b8de4/download/planc2193.zip)) | `planc2193.zip` | `5a84fe6064d47d76` |
| [PLANH2316](https://data.capitol.texas.gov/dataset/planh2316), "State House districts, 2023-2026" ([zip](https://data.capitol.texas.gov/dataset/71af633c-21bf-42cf-ad48-4fe95593a897/resource/a4d3230f-47f2-4253-85f3-51a6c3c9ad0a/download/planh2316.zip)) | `planh2316.zip` | `82d2a0aeb31e714c` |
| [PLANS2168](https://data.capitol.texas.gov/dataset/plans2168), "State Senate districts, 2023-2026" ([zip](https://data.capitol.texas.gov/dataset/70836384-f10c-423d-a36e-748d7e000872/resource/8247dbc6-b942-4a29-813c-1ebc603a7236/download/plans2168.zip)) | `plans2168.zip` | `7bf496e41cfc6ddc` |

**Which elections:** the portal tags PLANC2333, PLANH2316 and PLANS2168 "districts for 2026 elections", and the House and Senate plans also "districts for 2022-2026 elections". It tags PLANC2193 "districts for 2022-2024 elections" (its title's "2023-2026" is the term of the Congress it was drawn for; PLANC2333 replaced it for 2026). So the House and Senate views cover 2022, 2024 and 2026, and the U.S. House view covers 2022 and 2024 on PLANC2193 and 2026 on PLANC2333. The checks below confirm the tags against each year's precinct votes. No plan before 2022 was fetched.

### Terms of use, read 2026-11-12

This is a reading of the published pages, not legal advice. Each dataset page and its record in the portal's catalog were read in a browser.

| Source | What it says | What it asks of us |
|---|---|---|
| PLANH2316, PLANS2168 | Listed as Creative Commons Attribution, linking to the same general [license page](http://www.opendefinition.org/licenses/cc-by) as `VTDs_24PG`, with no version named. | Credit, a license link and a note of changes: in the page's Sources and in each file's `meta` |
| PLANC2333 | **No license.** The page shows none and its catalog record has an empty license field. The portal's [About page](https://data.capitol.texas.gov/about) describes the portal and has no terms. | Nothing stated. This is silence, not permission, the same standing as the Secretary of State's results. The owner was told and chose on 2026-11-12 to publish the outlines with credit, in the page's Sources and the file's `meta`. |

**Gap in the record:** the Council wasn't asked about PLANC2333. PLANC2193 was read on 2026-11-18 and is licensed Creative Commons Attribution: see "Texas precincts by year and PLANC2193 terms" in Part 5.

### Build

`python scripts/build_districts.py` (after `build_data.py`, and with the 2022 and 2024 files of `build_tx_precinct_years.py` in `data/raw/census-dl/tlc/`; about 5 minutes, nearly all of it the 2022 and 2024 checks) writes one file per plan to `data/districts/`:

| File | Districts | Points, raw to simplified | Size | SHA-256 (first 16) |
|---|---:|---|---:|---|
| `texas-house.json.gz` | 150 | 615,053 to 49,235 | 119 KB | `5383ed86378e8f0f` |
| `texas-senate.json.gz` | 31 | 386,881 to 31,215 | 76 KB | `322cddd96a64811f` |
| `u-s-house.json.gz` (2026, PLANC2333) | 38 | 411,204 to 35,578 | 85 KB | `b1d159bcf0e412f7` |
| `u-s-house-2022-2024.json.gz` (PLANC2193) | 38 | 400,436 to 31,319 | 76 KB | `3a55e7f79150e561` |

Outlines are converted from the Council's Lambert projection and simplified to about 55 m along the borders neighbors share, the way the precinct outlines are.

Checks that stop the build:
- Each file has exactly the chamber's districts, numbered 1 to its size in `results-2026.json` (for PLANC2193, in the 2022 results of `results-history.json`).
- **The lines match the results.** Each district's counties are worked out from the 2024 precincts whose centers fall inside it. Every district on the 2026 ballot must reach every county the Secretary of State's feed reports results from for it: all 38, 150 and 16 do.
- A district may also reach one county with no results for it, where its piece has no voters or a precinct's center falls just over the line (4, 9 and 3 districts do). More than one stops the build.

- **The 2022 and 2024 results match the lines** (added 2026-11-19). The Council's own precinct votes for those years (`votes-2022.zip`, `votes-2024.zip`, on `VTDs_22G` and `VTDs_24PG`, the files of Part 3 #6) give each precinct's votes for each district. A precinct with votes for district N must lie at least partly inside N's lines: its center is inside, or a point of its outline pulled 2% toward its center is. A precinct wholly outside may hold at most 0.01% of the year's votes, and must be within 10 km of the district; more stops the build. The Council leaves out districts with one candidate, so those have nothing to check.

| Plan | Year | Votes checked | Center inside | Wholly outside |
|---|---|---:|---:|---|
| PLANC2193 (U.S. House) | 2022 | 7,089,460 in 34 districts | 99.46% | 25 votes: Freestone County precinct 0004B for District 17, 3.1 km away |
| PLANC2193 | 2024 | 9,622,652 in 33 districts | 99.42% | 304 votes, all in Freestone County: 0004A (269) and 0006B (17) for District 6, 0006A (14) and 0004B (4) for District 17, within 4.7 km |
| PLANH2316 (Texas House) | 2022 | 5,054,610 in 92 districts | 99.28% | none |
| PLANH2316 | 2024 | 7,511,571 in 96 districts | 99.50% | none |
| PLANS2168 (Texas Senate) | 2022 | 5,471,731 in 21 districts | 99.56% | none |
| PLANS2168 | 2024 | 3,764,398 in 10 districts | 99.57% | none |

The Freestone precincts sit where Districts 6 and 17 meet, and their votes went to the neighboring district. Why isn't known: the county's precinct lines may be drawn a little apart from the Council's district lines there, or some voters assigned across the line. It isn't a wrong plan: the rest of both districts match. It changes no district's map.

### On the page

- `STATE.data.districts` in `state.js` lists each chamber's file and years, or several files when the lines changed, as the U.S. House's did for 2026; `districtEntry` in `app.js` picks the one whose years hold the race's year. The page checks that a file is there before offering its view, so removing a file removes that chamber's button. `app.js` draws them with the precinct view's column code (`precinct-columns.js`).
- **Color:** the winner's share of all votes cast in the district, in the same 10-point bands. **Height:** votes cast, on a scale of the chamber's own: its district with the most votes in any year on the page stands as tall as the tallest county column (420 map units). The first build used the county columns' scale, on which Texas's largest districts stood 7% to 23% as tall as Harris County, so every district was a low slab; the owner chose the change on 2026-11-12.
- A district with a single candidate is left off the ballot in Texas, so it has its winner's color at full strength and no height. Senate districts not up that year are gray.
- The sidebar's headline and bars still describe counties. Only the race line, "What you're seeing", the legend titles and a Method paragraph change.
- Checked in a browser on 2026-11-12: all three chambers flat and in 3D, hover, 2022 Texas House, switching among county, precinct and district, and that Kansas and Oklahoma still load. Not checked: other screen sizes, or the Go to menus while by district.
- Checked in a browser on 2026-11-19: the U.S. House by district in 2022 (25 of 38 seats Republican) and 2024 on PLANC2193, then 2026 on PLANC2333 with the view staying on, and 2020 with its button off ("No district lines here"). No errors in the console.

### Other states

Part 10 is the record of the U.S. House in seven more states. Legislatures aren't done in any state but Texas.

## 10. U.S. House districts in other states: the record

Built 2026-11-12. Seven more states have the **By district** view, for the 2026 U.S. House: Oklahoma, Iowa, Idaho, Georgia, Rhode Island, South Carolina and New Mexico. The owner chose U.S. House first; legislatures are a later pass.

### Which states, and why not the rest

| States | U.S. House |
|---|---|
| Oklahoma, Iowa, Idaho, Georgia, Rhode Island, South Carolina, New Mexico | District results were already in the saved raw files. Built |
| Ohio | Results are in the saved file and now on its county map, but its 2026 districts aren't in the Census file (below). No By district view |
| Kansas, California, West Virginia | No district results were saved, so their sites would have to be read again |
| Vermont, South Dakota | One district, the whole state, already mapped as a statewide race |

### Results

Each state's results script now adds a `u-s-house` race through `scripts/chamber.py`, in the shape `build_data.py` gives Texas's chambers: every district added up by county, plus each district's own candidates and the rows of the counties its results came from (`where`). Each script stops unless a district's counties add up to the source's own total for it. What's particular to a state is in its record under `records/`; Oklahoma's is here: all 5 districts are in the state and county exports, which agree.

| State | Districts | Seats | `results-2026.json` SHA-256 (first 16) |
|---|---:|---|---|
| Oklahoma | 5 | 5 R | `029131a254b22b9c` |
| Iowa | 4 | 3 D, 1 R | `4551da147af142f3` |
| Idaho | 2 | 2 R | `cda357a85e31d040` |
| Georgia | 14 | 9 R, 5 D | `f35da56a2fdac02a` |
| Rhode Island | 2 | 2 D | `57fa96ea8513c7a4` |
| South Carolina | 7 | 5 R, 2 D | `fe4ad07fa0253315` |
| New Mexico | 3 | 3 D | `d7d56d1acec62178` |
| Ohio (county map only) | 15 | 8 D, 7 R | `a64e40d3a784a7c4` |

These are unofficial, like each state's other results, and in a state still counting the page says "led", not "won".

### Outlines

Two Census Bureau files of the 119th Congress's districts, downloaded 2026-11-12 (not committed). Terms: Part 8's reading of the TIGER/Line documentation covers both, with the credit and trademark statement in each page's Sources and each file's `meta`.

- **Drawn:** the national 2024 Cartographic Boundary File, [`cb_2024_us_cd119_500k.zip`](https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_us_cd119_500k.zip), saved to `data/raw/census-dl/cb/` (SHA-256 `2b4238aed7e865df`). It stops at the shoreline, as the page's county shapes do. The owner approved this download after seeing the first build, whose TIGER/Line outlines filled in Narragansett Bay and ran out to sea.
- **Checked against:** each state's 2024 TIGER/Line file, `tl_2024_<code>_cd119.zip`, saved to `data/raw/<state>/census/`. It is exact, and includes the water the Bureau assigns to a district.

| State | TIGER/Line file, `tl_2024_<code>_cd119.zip` | SHA-256 (first 16) | `data/<state>/districts/u-s-house.json.gz` | SHA-256 (first 16) |
|---|---|---|---:|---|
| Oklahoma | `40` | `b33fd53f5a0e9fef` | 9 KB | `0abf183e113bca52` |
| Iowa | `19` | `6f2a45cfa1ec1e3f` | 5 KB | `f2984903e285ff64` |
| Idaho | `16` | `6b6a96d8597620be` | 13 KB | `594250407fc951dc` |
| Georgia | `13` | `42055d2deb7f2faa` | 28 KB | `1389748df8c9eabb` |
| Rhode Island | `44` | `07408bf88c39c2d2` | 3 KB | `1395670a5da6345d` |
| South Carolina | `45` | `c224e2d4662775c5` | 24 KB | `7db63a8aa2bea3df` |
| New Mexico | `35` | `1dcb982600be0eba` | 5 KB | `50489907fd55a807` |
| Ohio | `39` | `11c6b089975f310f` | not built | |

`python scripts/build_districts.py ok` (or several codes, or `all`) builds them, after the state's results script. It needs numpy.

**The check that these are the lines the results were counted on** is exact here. Every census block with people is placed in a district by its inside point, on the TIGER/Line outlines as published, which gives each district's people in each county. The build stops unless:
- every county a district's results came from is one where its people live, and
- a district has fewer than 100 people in any county with no results for it.

All seven pass. Three districts have a few people in a county that reports nothing for them: South Carolina's 3rd (36 people in Lexington), Georgia's 6th (17 in DeKalb) and 7th (7 in DeKalb).

**Ohio fails it,** as expected: the state redrew its U.S. House districts for 2026. Its results for District 1 come from Clinton County, which the 2024 file's District 1 doesn't reach. So no outlines were written for Ohio.

**Not compared:** the cartographic file's outlines against the TIGER/Line ones, beyond both having the same districts. The cartographic file is generalized to 1:500,000, so a drawn border can sit a little off the exact one.

### On the page

- A state lists its file under `STATE.data.districts` in `state.js`. `app.js` adds the By district button to a page that doesn't have it in its markup.
- The Method text names each state's own authority, and uses `STATE.chamberTotals` where county figures don't simply add up to the published district totals (New Mexico, Rhode Island).

### Gaps

- Not checked: that each state's 2026 U.S. House election was held on the 119th Congress's lines other than by the check above, which would miss a change that moved no county in or out of a district.
- Georgia's majority rule and any runoff weren't looked into beyond every leader having a majority in this file.

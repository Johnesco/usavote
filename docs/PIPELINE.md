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
- Stacking: runner-up at the bottom, others in the middle, winner on top.
- City names (`cities.js`): about 100,000 people and up when the whole state shows, and smaller places as you zoom in. At most 30 show at once.

**Bar view by precinct** (`precinct-columns.js`), on the results page's **By precinct** toggle: one mesh holds every precinct's column, stacked in the shader. Height is on one scale at every zoom: 70 map units for the 2024 Senate race's largest precinct. Votes are as counted for the 2024 U.S. Senate race and otherwise estimated by step 1 below, and labeled so on screen.

**Dot view: one dot per voter** (`dots.js`, `dots-worker.js`), on `voters.html`, which the **Dot view** button in bar view opens for the race on screen (`?race=`). It shows any race and year, always on the flat map:
1. **Share by precinct:** each party's 2026 county total is split among precincts by that party's share of its 2024 county vote there.
2. **Share by block:** each precinct's share is split among its blocks by adults.
3. **Whole dots:** systematic rounding turns those shares into whole dots, so every county adds up exactly to its 2026 result.
4. **Place each dot:** a random spot around its block, on a bell curve whose standard deviation is 0.75 of the block's radius, cut off at 2.5 standard deviations.
5. **Keep it off empty land:** a dot on an empty grid cell tries again, up to 16 tries in all, then sits at the block's center. In Texas about 183,000 of 9,889,704 dots get a new spot and 31 end at the center.

The random numbers are seeded, so a given race draws the same dots each time (seed 2026 + the race's position in the list; the U.S. Senate race is first, so 2026). If the precinct file fails to load, dots spread evenly over each county; if the grid fails, dots skip step 5.

**Keeping it fast:** the worker sorts the dots into a 256 × 256 grid of tiles, and each frame draws only the tiles on screen, so a close-up doesn't process every dot in the state. Within that sort are four levels for far-off views, nested so that coming closer only adds dots: a level cuts each tile into cells (4, 8, 16 or 32 per side) and keeps at most 4, 4, 8 or 16 dots a cell, sampled evenly through the tile, so only dots stacked on others are left out and sparse places keep all of theirs. A level is used only while its cells are at most half a pixel across at the nearest ground on screen; closer than the last level, while dots are appearing, and while one county's dots are enlarged, every dot is drawn. The dots are held only on the graphics card once uploaded, so a lost graphics context places them again. Nothing is drawn while the picture isn't changing.

**The voter tour** (`voters.js`), the Texas Population Density Tour, offered in that page's top bar for the U.S. Senate race: the counties to visit are chosen by hand and the numbers are computed from the data. Each visit shows a metro from high up, then one county, then its most crowded spot. Close-ups zoom until the typical gap between voters is drawn 16 pixels wide. Camera moves use a smooth zoom-and-pan path (van Wijk and Nuij, 2003) that favors zooming out over panning.

**Publishing:** GitHub Pages serves the `main` branch as it is. Only what's in the repo goes out, so keep raw data out.

## 5. Rules to keep

These came out of decisions made along the way. Keep them in any state.

- **Check publishing rights before publishing anything.** Before any data, page, doc, commit message, pull request or issue text goes online, read the source's terms of use and confirm they cover this use: redrawing, simplifying and republishing. If they're silent or unclear, keep that data and anything built from it local and git-ignored, and ask the source or the owner first. Pushing to any branch publishes, because the repository is public: a pull request that's never merged is still online. Taking something down afterward doesn't reliably remove it. In 2026, Oregon's results reached a pushed branch before its terms were settled, and the only way to remove them was to delete and recreate the repository.
- **No voter files.** Ballots are secret, so a person's vote can't be known. Voter lists are also restricted in how they can be used, and putting names at home locations would be a privacy problem.
- **Label estimates.** A dot's spot and color are estimates, and every close view has to say so. Current wording: "Spots and colors are estimated."
- **Hide very small precincts.** Merge anything under 10 votes before publishing, even if the source publishes it.
- **Don't go down to households.** Stop at blocks and a coarse land grid, and don't use building locations in a way that points to individual homes.
- **Every total must match the source.** County totals have to match exactly, and the scripts should stop if they don't.
- **Say when results are unofficial,** and rebuild after the canvass.

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

## 6. Template for another state

**Status:** used for Oklahoma (Part 7) and for the states in Part 8. `build_precincts.py`, `build_cities.py` and `build_landmask.py` take a state (`ok`, `ks`, `sc`, `oh`, `ia`; no argument means Texas), so the table below shows where another state plugs in. Results and precinct readers are still written per state.

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

- **Results not reported by county:** Alaska has no ordinary counties, and New England states often report by town. Connecticut's Census geography also changed to planning regions in 2022, which won't match the 2017 county shapes in us-atlas.
- **County look-alikes:** Louisiana parishes, Virginia's independent cities and similar units affect name matching, and Texas's "County" suffix handling won't cover them.
- **Precinct data:** other states may have no equivalent of the Texas Legislative Council's portal. The Voting and Election Science Team (Harvard Dataverse) and the Redistricting Data Hub are places to look, and the Census file includes 2020 voting districts for shapes, though they can be out of date (Part 7). Check each one's license.
- **Vote-by-mail and countywide votes** may be reported apart from home precincts, which would weaken the placement. Check this first in each state.
- **Other race shapes:** runoffs, ranked-choice voting, top-two primaries and races without exactly one Democrat and one Republican. `build_data.py` skips those races.
- **Scale limits:**
  - The dot format stores a county index in 8 bits (at most 256 counties), so each state gets its own map; all U.S. counties can't share one map this way.
  - Each dot takes 8 bytes, so a state with 15 million voters needs about 120 MB for dots alone.
  - The precinct files and land grid grow with the state. Texas's are 2.1 MB, 0.94 MB and 1.03 MB, and larger files make the site slower to load.
- **Census age:** the 2020 counts get less accurate where growth is fast. A new census means new block files and new hashes.

## 7. Oklahoma: the record

Built 2026-11-08, for the 2026 general election only, and **county-only**: bar view by county and dot view, with no By precinct view or precinct menu. **Results are unofficial:** the state certifies them on Nov. 10, 2026, so save the exports again after that, rebuild, and compare.

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
| 1 | `python scripts/build_ok_results.py` | `results-2026.json` | `23414a8bb3514866` |
| 2 | `python scripts/build_cities.py ok` | `cities.json` | `03e595d5154fc24e` |
| 3 | `python scripts/build_precincts.py ok` (reads #1) | `blocks.json.gz` | `cc635054c09e4a3b` |
| 4 | `python scripts/build_landmask.py ok` | `landmask.bin.gz` | `3c08d559b02e7cb8` |

Numbers to expect: 8 races on 77 counties; 297 places; 180,154 blocks, 118,191 with adults, 3,010,698 adults; a 7,947 × 3,859 land grid.

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

## 8. Kansas, South Carolina, Ohio and Iowa: where the records are

Built 2026-11-08 and 2026-11-09, for the 2026 general election only. Each state's record has the shape of Part 7: sources and hashes, terms, build commands, expected numbers, differences from Texas, and gaps. Raw files are under `data/raw/<code>/`, not committed.

| State | Record | View | Precinct source | Rebuild after |
|---|---|---|---|---|
| Kansas | [`records/kansas.md`](records/kansas.md) | County and precinct | IKE Lab 2024 votes and shapes (CC-BY) | Nov. 16 county canvass and Dec. 1 certification deadline |
| South Carolina | [`records/south-carolina.md`](records/south-carolina.md) | County and precinct | 2026 U.S. Senate votes on Census 2020 voting districts | Nov. 10 certification |
| Ohio | [`records/ohio.md`](records/ohio.md) | County | None | The official canvass, about Nov. 24 |
| Iowa | [`records/iowa.md`](records/iowa.md) | County | None | The state canvass, about Nov. 30 |

**Census terms:** Parts 5 and 7 say no license was found for the Census files. The [TIGER/Line 2020 technical documentation](https://www2.census.gov/geo/pdfs/maps-data/data/tiger/tgrshp2020pl/TGRSHP2020PL_TechDoc_Ch1.pdf), Chapter 1, read 2026-11-09, covers this: U.S. Government works have no copyright, so "you are free to reproduce census materials as you see fit". It asks that the Census Bureau be cited, and that repackaged TIGER/Line data carry a conspicuous trademark statement on the first page of the website, which `index.html` now has.

**Results terms:** Kansas, South Carolina, Ohio and Iowa grant no license for their results, and Ohio's and South Carolina's sites carry an "All Rights Reserved" footer. The owner chose on 2026-11-08 to treat them as Texas and Oklahoma were treated: use the published results and credit the source.

**North Carolina is on hold.** The [state's terms](https://www.nc.gov/disclaimer-terms-use) say "for non-commercial use" and "without alteration", which doesn't clearly cover county totals, simplified outlines or dots. Its election board hasn't been asked.

**Build method:** the states were built in parallel on separate branches and merged, then all six were rebuilt from the merged scripts and compared with the committed files.

# From raw data to the map: record and template

This is how the Texas 2026 site goes from public source files to what appears on screen, written so someone can repeat it for
Texas or adapt it for another state. It covers only what the site does now. Parts 1 to 5 are the record for Texas. Part 6 is the
template for other states; it has not been tried on another state yet.

**How this was checked (2026-11-08):**

- All the data builds were rerun from the local raw files. All five published data files came out byte-identical to the hashes in Part 3.
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

### 2.1 Files you can download by script

| What | Local path under `data/raw/` | SHA-256 (first 16) |
|---|---|---|
| 2026 results by county, all races ([feed](https://goelect.txelections.civixapps.com/api-ivis-system/api/s3/enr/election/countyInfo/53815)) | `sos-countyInfo-53815.json` | `9c95edda76f5bfcb` |
| 2024 U.S. Senate votes by precinct ([Texas Legislative Council](https://ted.capitol.texas.gov/api/Offices/510/2/vtd)) | `census-dl/tlc/sen24_vtd.json` | `03464ba753587d2e` |
| 2024 precinct shapes, `VTDs_24PG` ([zip](https://data.capitol.texas.gov/dataset/4d8298d0-d176-4c19-b174-42837027b73e/resource/906f47e4-4e39-4156-b1bd-4969be0b2780/download/vtds_24pg.zip)) | `census-dl/tlc/vtds_24pg.zip` | `4adf61b5d97bdc7b` |
| 2020 Census redistricting file, P.L. 94-171 ([zip](https://www2.census.gov/programs-surveys/decennial/2020/data/01-Redistricting_File--PL_94-171/Texas/tx2020.pl.zip), 100 MB) | `census-dl/pl/tx2020.pl.zip` | `6fee8ca5759eb494` |
| 2020 census block shapes, TIGER/Line ([zip](https://www2.census.gov/geo/tiger/TIGER2020/TABBLOCK20/tl_2020_48_tabblock20.zip), 746 MB) | `census-dl/tiger/tl_2020_48_tabblock20.zip` | `c0e71f4bf463c212` |
| County shapes, us-atlas 3.0.1 ([json](https://cdn.jsdelivr.net/npm/us-atlas@3.0.1/counties-10m.json)); only the infographic reads this copy, the pages load it from the CDN | `us-atlas/counties-10m.json` | `145aaf5d1433352a` |

The county results feed is one JSON object whose `upload` field is base64-encoded JSON. It's labeled unofficial until the state canvass, and it still matched the saved copy on 2026-11-08.

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
| 4 | `python scripts/build_precincts.py` | 3 min | `data/precincts.json.gz` | `5fdeeed11e825648` |
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
6. Writes a compact gzipped file.

**#5 Where dots can't go.** Draws every block with people or housing units onto a 100 m grid in the map's projection. Everything else is empty, such as lakes, bays, airports and big parks. Expect 455,943 blocks drawn on a 13,180 × 12,083 grid, and a 1.03 MB file.

**Optional images:**

```bash
python scripts/build_infographic.py
python scripts/build_infographic.py 4
```

These write the 4K and 16K images, which aren't committed. `scripts/panels.html` draws the share image; the command is in the README.

## 4. From data files to the screen

Nothing is computed on a server. Each page fetches its files and works everything out in the browser.

**Pages:** `index.html` and `history.html` run `app.js`, `story.html` runs `story.js`, and `voters.html` runs `voters.js`.

**The map:**
- Projection: d3 equal-area conic, parallels 27.5° and 35°, centered on 99.5° W, fitted to ±500 map units.
- Color: the county winner's share of all votes, in 10-point bands.
- Height: total votes on a linear scale shared by all races, with the tallest column at 420 map units.
- Stacking: runner-up at the bottom, others in the middle, winner on top.
- City names (`cities.js`): about 100,000 people and up when the whole state shows, and smaller places as you zoom in. At most 30 show at once.

**One dot per voter** (`dots.js`, `dots-worker.js`), on `voters.html` and the map pages with `?voters=1`:
1. **Share by precinct:** each party's 2026 county total is split among precincts by that party's share of its 2024 county vote there.
2. **Share by block:** each precinct's share is split among its blocks by adults.
3. **Whole dots:** systematic rounding turns those shares into whole dots, so every county adds up exactly to its 2026 result.
4. **Place each dot:** a random spot around its block, on a bell curve whose standard deviation is 0.75 of the block's radius, cut off at 2.5 standard deviations.
5. **Keep it off empty land:** a dot on an empty grid cell tries again, up to 16 tries in all, then sits at the block's center. In Texas about 183,000 of 9,889,704 dots get a new spot and 31 end at the center.

The random numbers are seeded, so a given race draws the same dots each time (seed 2026 on `voters.html`, 1 + the race's position on the map pages). Phones and tablets on the map pages get one dot per 10 voters. If the precinct file fails to load, dots spread evenly over each county; if the grid fails, dots skip step 5.

**The voter tour** (`voters.js`): the counties to visit are chosen by hand and the numbers are computed from the data. Each visit shows a metro from high up, then one county, then its most crowded spot. Close-ups zoom until the typical gap between voters is drawn 16 pixels wide. Camera moves use a smooth zoom-and-pan path (van Wijk and Nuij, 2003) that favors zooming out over panning.

**Publishing:** GitHub Pages serves the `main` branch as it is. Only what's in the repo goes out, so keep raw data out.

## 5. Rules to keep

These came out of decisions made along the way. Keep them in any state.

- **No voter files.** Ballots are secret, so a person's vote can't be known. Voter lists are also restricted in how they can be used, and putting names at home locations would be a privacy problem.
- **Label estimates.** A dot's spot and color are estimates, and every close view has to say so. Current wording: "Spots and colors are estimated, not real people or real votes."
- **Hide very small precincts.** Merge anything under 10 votes before publishing, even if the source publishes it.
- **Don't go down to households.** Stop at blocks and a coarse land grid, and don't use building locations in a way that points to individual homes.
- **Every total must match the source.** County totals have to match exactly, and the scripts should stop if they don't.
- **Say when results are unofficial,** and rebuild after the canvass.

## 6. Template for another state

**Status:** a plan. Nothing here has been run for another state. The scripts are written for Texas and need the changes below first.

### Reusable as is

- **Census sources.** The same pattern exists for every state. Ohio's two files returned HTTP 200 when checked; other states weren't tried.
  - `.../01-Redistricting_File--PL_94-171/<State>/<st>2020.pl.zip`, which contains `<st>geo2020.pl` and `<st>000022020.pl`
  - `.../TABBLOCK20/tl_2020_<fips>_tabblock20.zip`
- **Other national sources:** the Gazetteer file and us-atlas county shapes.
- **Methods:** block assignment, the precinct merge, the land grid, dot placement, the map and the camera.

### Texas-specific code to make configurable

| Where | What to change |
|---|---|
| `app.js`, `map3d.js`, `voters.js` | State code `'48'`, county count `254`, and the projection's parallels and center |
| `build_precincts.py` | Census file names, adult total (`TX_ADULTS`), precinct shape reader (fields `VTDKEY`, `CNTY`, `Shape_area`; the Lambert parameters), results reader (columns `AllredD`, `CruzR`) |
| `build_landmask.py` | Download URL and the projection constants, which must match the pages |
| `build_cities.py` | Census file names and the `Houston` sanity check |
| `build_data.py` | The whole script: feed format, `RACES` table, name fixes, chamber names, county count |
| `build_history.py` | The whole script, if you want a history page |
| `app.js`, `story.js`, `voters.js`, HTML | Written copy, sources, and hand-picked counties and metro groups |
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

1. **Check what exists.** Find county results, precinct results with matching shapes, and the terms of use for each. Save the URLs. If there are no precinct votes, stop and decide on a fallback, because the party mix inside counties depends on them.
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
- **Precinct data:** other states may have no equivalent of the Texas Legislative Council's portal. The Voting and Election Science Team (Harvard Dataverse) and the Redistricting Data Hub are places to look, and the Census file includes 2020 voting districts for shapes. Check each one's license.
- **Vote-by-mail and countywide votes** may be reported apart from home precincts, which would weaken the placement. Check this first in each state.
- **Other race shapes:** runoffs, ranked-choice voting, top-two primaries and races without exactly one Democrat and one Republican. `build_data.py` skips those races.
- **Scale limits:**
  - The dot format stores a county index in 8 bits (at most 256 counties), so each state gets its own map; all U.S. counties can't share one map this way.
  - Each dot takes 8 bytes, so a state with 15 million voters needs about 120 MB for dots alone.
  - The precinct file and land grid grow with the state. Texas's are 2.1 MB and 1.03 MB, and larger files make the site slower to load.
- **Census age:** the 2020 counts get less accurate where growth is fast. A new census means new block files and new hashes.

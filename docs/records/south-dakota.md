# South Dakota: the record

Built 2026-11-09, for the 2026 general election only, and **county-only**: bar view by county and dot view, with no By precinct view or precinct menu. This has the shape of `docs/PIPELINE.md`, Part 7.

**Results are unofficial.** The results site says the results are unofficial until "the 66 County Canvass Boards and the State Canvass Board canvass and certify" them. **The canvass dates weren't confirmed.** The survey's Nov. 10 is possible but unverified. A search turned up a legislative bill draft with a county canvass on the first Tuesday after the election and a state canvass tied to seven days after it, or the second Tuesday (Nov. 17), but whether that's the law wasn't checked. So the pages give no date. Look for the certified results from about Nov. 17, save the files again, rebuild, and compare.

## Reporting status

**671 of 671 precincts are fully reported**, in all 66 counties. The site's stamp is "Results last updated: 11/6/2026 8:00 PM CT". It lists 310,298 ballots cast and 628,563 registered voters (49.37%).

**91 provisional ballots** were cast statewide. The site says they aren't counted on election night and, if accepted, are counted one hour before the county canvass, so they may not be in these totals. No mapped race is close enough for them to matter (the closest margin is 59,344 votes), so the pages use the usual "won" wording and name the provisional ballots under Method. The site's Possible Recounts page lists only legislative and county races.

## Raw files, under `data/raw/sd/` (not committed)

Saved 2026-11-09 by `scripts/sd_results_save.py`, with plain `curl` and its own user agent. No browser was used for data. `results/SAVED.json` has the full hashes.

| What | Path | SHA-256 (first 16) |
|---|---|---|
| Statewide Export, a form post on the [Exports page](https://electionresults.sd.gov/ResultsExport.aspx): read for the map | `results/statewide-export.xlsx` | `4800376f7f132684` |
| [Media file](https://electionresults.sd.gov/resultsCSV.aspx?text=All&type=SWR&map=CTY): statewide totals and parties | `results/results-sw-cty.csv` | `91291608aac4b340` |
| [Home page](https://electionresults.sd.gov/): status and the stamp | `results/home.html` | `f42fc5c81ff48a00` |
| [Statewide races page](https://electionresults.sd.gov/resultsSW.aspx?type=SWR&map=CTY) | `results/resultsSW.html` | `b428be68905f3dc3` |
| [Provisional ballots](https://electionresults.sd.gov/ProvisionalBallots.aspx) | `results/provisional.html` | `9056bdda2d3fe219` |
| Possible recounts, terminology, media and exports pages | `results/recounts.html`, `terminology.html`, `media.html`, `export.html` | `c7dfdc43efcdb78f`, `56abe97e166970b1`, `7f90b46ffcac1499`, `ce21b9232ed581f6` |
| 2020 Census redistricting file ([zip](https://www2.census.gov/programs-surveys/decennial/2020/data/01-Redistricting_File--PL_94-171/South_Dakota/sd2020.pl.zip)), saved by hand | `census/sd2020.pl.zip` | not recorded |
| 2020 census block shapes ([zip](https://www2.census.gov/geo/tiger/TIGER2020/TABBLOCK20/tl_2020_46_tabblock20.zip)), saved by hand | `census/tl_2020_46_tabblock20.zip` | not recorded |

## Why county-only

The results export is by county, and this state was added last in its batch with the same treatment as Idaho. No precinct shapes were looked for.

What this costs: dots use one mix of parties across a county, so they don't show which neighborhoods lean which way.

## Terms of use, read 2026-11-09

This is a reading of the published pages, not legal advice. Nobody at these offices has been asked.

| Source | What it says | What it asks of us |
|---|---|---|
| [South Dakota Online Disclaimer](https://www.sd.gov/cs?id=kb_article_view&sysparm_article=KB0010221), read in full in Chrome | "Anyone may view, copy or distribute information found on the State's website for personal or informational use without owing an obligation to the State." It also says the State "makes no warranty that the materials contained within this information are free from copyright claims or other restrictions", and that a user "assumes the risk". | See the reading below |
| [State privacy notice](https://www.sd.gov/cs?id=kb_article_view&sysparm_article=KB0010220), linked from `public.sd.gov/privacy.aspx` | About the Citizen Portal. It mentions "the State's Terms of Use Agreement", which wasn't found. | Nothing for the results |
| `sdsos.gov` footer | Links to `sd.gov/privacy.aspx`, `disclaim.aspx` and `accpolicy.aspx`. No copyright wording in its home page text. | See the reading below |
| Results site | No terms link, and no copyright, license or terms wording on the pages saved. It says "Unofficial Results". | Say unofficial, and credit the source. Done. |
| Census files | Per `docs/PIPELINE.md`, Part 8: no copyright, and cite the Census Bureau. TIGER/Line is a registered trademark, and the homepage carries the statement. | Credit in Sources, with one short TIGER/Line note there |
| us-atlas | ISC license, per npm (`docs/PIPELINE.md`). | Nothing while the site loads it from a CDN |

**This state does not meet the batch's "no wording limiting reuse" bar.** The wording allows "personal or informational use", which is a limit on purpose. The owner was told this and chose South Dakota on 2026-11-09. This is the reading it was built on:

- A free, ad-free public map of election results is plausibly "informational use". The wording doesn't define the phrase, and nobody at the state was asked.
- Nothing asks for permission, and nothing bars alteration. That's unlike North Carolina's "without alteration".
- Commercial use wasn't considered. If the site ever carries ads or charges, read this again.
- Applying this text to the results site is inferred, from `sdsos.gov`'s footer link. The results site itself says nothing.

**Gaps in the record:** `sd.gov/disclaim.aspx` redirects to a sign-in page, which was left without signing in, so the text above comes from the knowledge-base article of the same title. `accpolicy.aspx` and the "Terms of Use Agreement" weren't read.

## Build, from the repo root

| # | Command | Writes to `data/sd/` | SHA-256 (first 16) |
|---|---|---|---|
| 0 | `python scripts/sd_results_save.py` | `data/raw/sd/results/*` | as above |
| 1 | `python scripts/build_sd_results.py` | `results-2026.json` | `91301c901f7bc6cf` |
| 2 | `python scripts/build_cities.py sd` | `cities.json` | `4e418f8c24d5d2fb` |
| 3 | `python scripts/build_precincts.py sd` (reads #1) | `blocks.json.gz` | `778aba66eb39e3f0` |
| 4 | `python scripts/build_landmask.py sd` | `landmask.bin.gz` | `1e548a0eb8831c03` |

## Numbers to expect

- 7 races on 66 counties; 671 precincts; 310,298 ballots; 628,563 registered voters
- 114 places, the largest Sioux Falls
- 71,383 blocks, 38,361 with adults, 669,255 adults
- A 6,260 × 3,934 land grid; 45,018 blocks drawn

| Race | Democrat | Republican | All votes |
|---|---|---|---:|
| Governor and Lt. Governor | Dan Ahlers and Steven McCleerey 111,161 | Larry Rhoden and Tony Venhuizen 193,334 | 304,495 |
| U.S. House | Nicole "Nikki" Gronli 109,997 | Marty Jackley 195,588 | 305,585 |
| Secretary of State | Terrence Davis 106,561 | Heather Baxter 172,365 | 295,187 |
| State Auditor | Tom Cool 109,392 | Catherine Barranco 182,694 | 292,086 |
| State Treasurer | Margaret Kuipers 109,756 | Melissa Hull 182,362 | 292,118 |
| School and Public Lands | Raeann Mettler 111,022 | Brock Greenfield 179,745 | 290,767 |
| Public Utilities | Frank Kloucek 115,224 | Don Haggar 174,568 | 289,792 |

Secretary of State's other: Tamara J. Lesnar (Libertarian) 16,261.

**Left out:**

- **U.S. Senate has no Democrat:** Mike Rounds (Republican) 184,589, Brian L Bengs (Independent) 120,513. The pages and Sources say so, and the build stops if a Democrat appears.
- **Attorney General** had one candidate: Lance Russell (Republican) 193,278.
- Constitutional Amendments I, J, K and L are questions rather than contests between candidates.
- Legislative, county and local races aren't statewide.

Checks that stop the build:

- The site says unofficial, in its home page and in each sheet's heading, and all 671 precincts are fully reported in the home page, each sheet and the media file
- Ballots cast and provisional ballots are still 310,298 and 91
- Each race's rows are exactly the Census's 66 county names, once each
- Each candidate's counties add up to the export's totals row and match the media file and the results page, in every mapped race
- Each party's and county's figures add up, no race has more votes than ballots, and each county has at least 10 Governor votes (fewest: 379, Buffalo County)

## What differs from Idaho

- **Projection:** parallels 43.1° and 45.4°, centered on 100.2° W, from the state's extent by the same rule of thumb. `state.js` and `build_landmask.py` use the same values.
- **Base race:** Governor, as in Idaho, for the same reason.
- **Tickets:** Governor's candidates are tickets. A ticket goes by the name at its head, so the pages say Ahlers and Rhoden.
- **County names:** the export writes "Yankton (Vote Center)" and the like; the suffix is removed to match the Census.
- **Party codes:** `DEM`, `REP` and `L` come from the media file, as the export has no parties. It lists no write-in votes and doesn't say who is an incumbent, so none are marked.
- **Time zone:** `meta.resultsUpdated` says CT, as the site does. Western South Dakota is on Mountain time.

## Shared-code changes

- `scripts/build_precincts.py`: South Dakota entries, and `BASE_ID` is Governor for `sd` too
- `scripts/build_cities.py`, `scripts/build_landmask.py`, `state.js`: entries only

## Gaps

- **Canvass dates** aren't confirmed, as above.
- **Provisional ballots:** whether the 91 are in these totals isn't known.
- **Lakes:** Lake Oahe and the other Missouri River reservoirs look empty in the dot view at whole-state scale. The land grid wasn't checked in close-ups.
- **Hand-picked text:** there's no tour, no county flight and no history.

## How this was checked (2026-11-09)

- All builds were run from the raw files. All 66 county codes are in us-atlas 3.0.1, including Oglala Lakota as 46102.
- In the browser at desktop width: the homepage label fits, both pages open on Governor, Secretary of State shows its Libertarian as other, and the dot view counts 304,495 voters, matching the race. No new console errors.
- `build_cities.py` and `build_precincts.py` for Idaho, Georgia and Kansas, and `build_landmask.py` for Iowa, were rerun after the script changes, and `git status` shows those files unchanged.
- **Not checked:** phone width, the 3D view, and the city and county menus. The whole sequence hasn't been run on a new machine.

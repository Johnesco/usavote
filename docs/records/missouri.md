# Missouri: the record

**Not built.** The owner asked on 2026-11-20 to check Missouri, which the third survey had left under "Copyright notice only, or not fully read" (`docs/PIPELINE.md`, Part 8). Its terms were read in Chrome that day. Nothing has been saved under `data/raw/`.

## Terms of use, read 2026-11-20

This is a reading of the published pages, not legal advice. Nobody at the Secretary of State's office has been asked.

| Source | What it says | What it asks of us |
|---|---|---|
| Secretary of State site ([sos.mo.gov/elections](https://www.sos.mo.gov/elections)) | No copyright line found; the footer links its Internet Privacy Policy and "Missouri State Government" | Nothing found |
| [Secretary of State: Internet Privacy Policy Statement](https://www.sos.mo.gov/ipolicy), read in full | Information collected, cookies, web forms, links, the Sunshine Law, passwords, viruses. Nothing on reuse. | Nothing for reuse |
| Results site, [enr.sos.mo.gov](https://enr.sos.mo.gov/) | No terms; same footer as the Secretary of State's site | Nothing stated |
| [MO.gov](https://mo.gov/) footer | "© 2026 State of Missouri. All rights reserved." | See below |
| [MO.gov: Data Policy](https://mo.gov/data-policy), read in full | "By using data made available through this site, the user agrees" to its conditions: no warranty; "Applications using data supplied by this site must include the following disclaimers on their sites", a set paragraph beginning "The data made available here has been modified for use from its original source, which is the State of Missouri" and disclaiming warranties; and the State may "require the termination of any and all displaying, distributing or otherwise using any or all of the data for any reason". | **If it applies:** show its disclaimer word for word, and stop if the State asks |

**The reading:** **conditional permission, if MO.gov's Data Policy reaches the results.** The Secretary of State's own pages say nothing on reuse. MO.gov's Data Policy assumes data will be used and modified, asks for a fixed disclaimer, and keeps a right to end any use. It speaks of data "made available through this site", meaning MO.gov; whether that covers the Secretary of State's results is inferred. The owner's call; a build would carry the disclaimer either way.

## Results, checked 2026-11-20

- **Complete, unofficial.** "Unofficial Results as of 11/20/2026 5:12 PM". Certification date not looked up.
- **One statewide race between candidates: State Auditor.** Scott Fitzpatrick (Republican) 1,062,203 (50.979%), Quentin Wilson (Democratic) 967,727 (46.445%), Dustin Coffell (Libertarian) 53,671; 3,214 of 3,214 precincts. No U.S. Senate or Governor race this year.
- U.S. House: 8 districts, each with a Libertarian.
- By county through "Pick a County": 114 counties and St. Louis City, which the Census counts as a county equivalent. No download was looked for.

## What building it would take

1. The owner decides on the Data Policy, then chooses it and approves the files by name.
2. A State Auditor page, plus U.S. House added up by county. St. Louis City and St. Louis County are separate (`countyWord` would need thought: the city's Census name is "St. Louis city").
3. The Data Policy's disclaimer on the page and in Sources. Rebuild after certification.

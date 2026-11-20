# Delaware: the record

**Not built.** The owner asked on 2026-11-20 to check Delaware, which the third survey had left under "Copyright notice only, or not fully read" (`docs/PIPELINE.md`, Part 8). Its terms were read in Chrome that day. Nothing has been saved under `data/raw/`.

## Terms of use, read 2026-11-20

This is a reading of the published pages, not legal advice. Nobody at the Department of Elections has been asked.

| Source | What it says | What it asks of us |
|---|---|---|
| Department of Elections site ([elections.delaware.gov](https://elections.delaware.gov/)) | No copyright line found. Its footer's "Help", "Privacy", "Cookies" and "Accessibility" links go nowhere (`#`). | Nothing found |
| [Delaware.gov: Privacy Policy](https://delaware.gov/privacy-policy/), read in full, the portal's only policy link | Privacy, cookies, a "Terms of Service" section about sharing visitors' information, and third-party add-ins. Nothing on reusing state information. Footer: "©MMXVIII Delaware.gov" | Nothing for reuse |
| [Delaware Open Data Portal: Official Election Results by Office](https://data.delaware.gov/d/4hbv-7brf), its "About this Dataset" | "Data Provided by Department of Elections"; updated Nov. 10, 2026; **"License: Public Domain"**; source link `https://elections.delaware.gov/results`. One row per candidate per race: statewide totals by vote type, **no county column**. The results page's "Download CSV Report" button is this dataset. | Nothing: public domain |
| Results page, [GE2026](https://elections.delaware.gov/results/enr/GE2026.html) | No terms | Nothing stated |

**The reading:** **public domain for the statewide totals, silent for the county figures.** The State publishes its official results by office under a public-domain license. The county figures appear only on the results page's "By County" view, which states no terms. That's at least the standing of Vermont and West Virginia, and the closest to permission of any state read so far after New Jersey.

## Results, checked 2026-11-20

- **Official.** The results page reads "OFFICIAL RESULTS", data as of Nov. 10, 2026, 12:49 PM; 530 of 530 election districts reporting; each county's absentee tabulation done. 384,862 votes cast.
- Statewide races between a Democrat and a Republican, read off the page: **U.S. Senate**, Chris Coons (Democratic) 240,587, Michael "Dr. Mike" Katz (Republican) 137,837; **U.S. House** (one at-large seat), Sarah McBride 243,687, Joseph "Dr. Joe" Arminio 135,016; **Attorney General**, Kathy Jennings 240,626, David C. "Dave" Graham 137,516; **Auditor of Accounts**, Lydia York 227,685, April Callaway 130,928, and an Independent; **State Treasurer** (not read).
- **By county** (three: New Castle, Kent, Sussex): U.S. Senate, Coons 144,910 / 36,437 / 59,240, Katz 54,919 / 27,023 / 55,895. Coons carried all three.
- The page also has "By Election District" results, Delaware's precincts. Whether they match the Census's 2020 voting districts wasn't looked at.

## What building it would take

1. The owner chooses it and approves the files by name: the county figures (the page builds its tables in the browser; how to save them wasn't looked at), the public-domain CSV for statewide totals to check against, and the two Census files.
2. County-only, like West Virginia. **Three counties make a thin map**, and every one went the same way in U.S. Senate. A precinct view from the election-district results would show far more; it would need the district shapes.
3. Official, so no rebuild needed.

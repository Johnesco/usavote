# Kentucky: the record

**Not built.** The owner asked on 2026-11-19 to check Kentucky, which the third survey had left under "Copyright notice only, or not fully read" (`docs/PIPELINE.md`, Part 8). Its terms were read in Chrome that day. Nothing has been saved under `data/raw/`.

## Terms of use, read 2026-11-19

This is a reading of the published pages, not legal advice. Nobody at the State Board of Elections has been asked.

| Source | What it says | What it asks of us |
|---|---|---|
| State Board of Elections site footer ([elect.ky.gov](https://elect.ky.gov/)) | "©2026 Commonwealth of Kentucky. All rights reserved." Its policy links go to Kentucky.gov. | See below |
| [Kentucky.gov: Disclaimer](https://kentucky.gov/policies/Pages/disclaimer.aspx), read in full | About links and accuracy only: "All critical information should be independently verified." | Nothing for reuse |
| [Kentucky.gov: Policies](https://kentucky.gov/policies/Pages/default.aspx) (privacy and security) | Searched, and its "Legal Notice" read in full: trademarks, a copyright-infringement procedure with notices sent to Tyler Technologies, the portal's vendor, and "The full Notices and Procedures language can be found in Terms of Use", linking to [tylertech.com/terms](https://www.tylertech.com/terms). | See below |
| [Tyler Technologies: Terms of Use](https://www.tylertech.com/terms), searched for use of content | Apply to "online services ... developed, operated and made available" by Tyler. Users may not "display, distribute, license, perform, publish, reproduce, duplicate, copy, create derivative works from, modify ... for any commercial purposes, all or any portion of the Services" without Tyler's permission, nor use any automatic device or "any manual process, to monitor or copy any of the Web pages, data or content" of the Services. | **Limits copying and commercial reuse,** if they reach the results |

**The reading:** **unclear.** Kentucky's own pages say nothing on reuse beyond "All rights reserved", like Ohio's. But its policy page points to the vendor's terms, which forbid copying data from Tyler's services and commercial reuse, and the link sits next to the copyright-notice procedure. Whether those terms govern the State Board of Elections' results isn't clear. Under `CLAUDE.md` that means: don't publish, and ask first.

**Worth knowing:** West Virginia's record says WV.gov's Legal Notices also send copyright complaints to Tyler Technologies. Its reading didn't follow on to Tyler's terms; whether WV.gov links them wasn't checked again.

## Results, checked 2026-11-19

- The [2026 results page](https://elect.ky.gov/results/2020-2029/Pages/2026.aspx) has "Unofficial General Election Results": a statewide summary CSV (`Ky_2026g_summary`, 61 KB) and results by county for all 120 counties. Not downloaded.
- 2026 race between a Democrat and a Republican statewide: U.S. Senate (open seat), from general knowledge; not read off the results.

## What building it would take

1. The owner decides whether the Tyler terms matter here, or asks the State Board of Elections, before anything is published.
2. Then the usual county-level build from the summary CSV.

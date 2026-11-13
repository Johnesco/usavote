# Mississippi: the record

**Not built.** The owner asked on 2026-11-13 why Mississippi wasn't built. It had been left in the third survey's group "Copyright notice only, or not fully read" (`docs/PIPELINE.md`, Part 5), so its terms were read in full in Chrome that day. Nothing has been saved under `data/raw/`, and no data or anything built from it is in the repository.

## Terms of use, read 2026-11-13

This is a reading of the published pages, not legal advice. Nobody at the Secretary of State's office has been asked.

| Source | What it says | What it asks of us |
|---|---|---|
| [Secretary of State: Disclaimer](https://www.sos.ms.gov/disclaimer), the only terms page the site's footer links to, read in full | The site is "a service to the public", and use of its information "is governed by the following disclaimers and limitations on use". What follows disclaims accuracy and liability, says copies of documents should be requested under the Mississippi Public Records Act of 1983, and says users must make "their own determination as to its suitability for their purposes". It prohibits "unauthorized attempts to modify any information stored on this site" and using the site "for other than its intended purposes". Nothing on copying, republishing or altering what's downloaded. | Nothing for reuse. "Modify any information stored on this site" reads as tampering with the site itself, next to defeating security features, not as a limit on redrawing downloaded results; that is a reading |
| Secretary of State site footer | "© 2026 Mississippi Secretary of State. All rights reserved." | See below |
| Results pages: [2026 General Election Results](https://www.sos.ms.gov/elections-voting/election-results/2026/2026-general-election-results), its framed page and the [County Recapitulation Report](https://www.sos.ms.gov/elections/electionresults_aspx/elections_results_2026_county.aspx) | No terms, copyright line or license on the framed pages themselves; the outer page carries the site footer above | Nothing stated |
| ms.gov, the state portal: [Linking](https://www.ms.gov/linking-policy), [Privacy](https://www.ms.gov/privacy-policy), [Social Media](https://www.ms.gov/social-media-policy), [Accessibility](https://www.ms.gov/accessibility-policy) and [AI Terms & Conditions](https://www.ms.gov/ai-terms-conditions) | Linking and Privacy read in full; Social Media, Accessibility and AI terms searched for copying, reuse, license and similar words. None says anything about reusing state information. The AI terms cover only the portal's chatbot. The footer says "© 2026 ms.gov \| All Rights Reserved". The privacy policy mentions "the ms.gov Terms of Use Agreement", but no such page is linked, and `/terms-of-use`, `/terms`, `/terms-and-conditions`, `/legal`, `/disclaimer` and `/copyright` all return 404. Whether portal terms reach the Secretary of State's site is unclear in any case | Nothing found |
| Census files, us-atlas | As in `docs/PIPELINE.md`, Part 8 | Credit in Sources, and the TIGER/Line note |

**The reading:** the terms are **silent** on reusing results: no license, and no limit beyond a disclaimer and "All rights reserved" footers. That's the same standing as Vermont and West Virginia, and close to Ohio and South Carolina, whose "All Rights Reserved" footers the owner accepted on 2026-11-08. Building it is the owner's choice.

**Gaps in the record:** the Mississippi Public Records Act, which the disclaimer points to, wasn't read. The "ms.gov Terms of Use Agreement" the privacy policy names couldn't be found. County election commissions' own sites weren't looked at.

## Results, checked 2026-11-13

- **No statewide results file.** The Secretary of State posts no county-by-county table or download for the 2026 general election: no election-night results site, no spreadsheet, no statewide totals page. The 2026 results list has only the two March primaries and this election.
- **Precinct results, as scanned PDFs, county by county.** The page is headed "OFFICIAL 2026 GENERAL ELECTION RESULTS" and holds each county's certified recapitulation sheet, "results by precinct". **24 of 82 counties** were posted when checked: Bolivar, Carroll, Coahoma, Covington, Franklin, George, Greene, Hinds, Jasper, Jefferson, Lafayette, Lamar, Leake, Lowndes, Marion, Marshall, Newton, Noxubee, Pearl River, Scott, Sunflower, Tippah, Yalobusha and Yazoo.
- **The PDFs are pictures of paper.** Three were opened (Hinds: 51 pages, 1.3 MB; Greene: 5 pages; Lamar: 7 pages). Each page is an image, with no text layer, made by three different scanners or printers. Getting numbers out means reading them by OCR or by hand, then checking every county against its own totals.

## What building it would take

1. The owner chooses it, knowing the terms are silent.
2. Wait for all 82 counties' sheets, or for the state's certified statewide totals, which give each candidate's statewide total to check the counties against.
3. Read the numbers off every county's scanned sheets: by far the biggest job, and one no other state has needed.
4. Then the usual build: county results, Census land and adults, the state's settings in `state.js`, and its pages. Precincts would need precinct shapes too, which the state doesn't publish here.

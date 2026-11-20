# New York: the record

**Not built.** The owner asked on 2026-11-19 to check New York. It had been left in the third survey's group "Silent, not chosen" (`docs/PIPELINE.md`, Part 8), so its terms were read in Chrome that day and its results looked at. Nothing has been saved under `data/raw/`, and no data or anything built from it is in the repository.

## Terms of use, read 2026-11-19

This is a reading of the published pages, not legal advice. Nobody at the State Board of Elections has been asked.

| Source | What it says | What it asks of us |
|---|---|---|
| [Board of Elections: Privacy Policy](https://elections.ny.gov/privacy-policy), the only policy page its footer links to | Read in full: privacy practices, then a "General Disclaimer", a "Links Disclaimer" and an "Information Disclaimer". The last says information is provided "to allow the public immediate access to public information", and makes no representations as to its accuracy, completeness, currency or suitability. Nothing on copying, republishing or altering. | Nothing for reuse |
| Results site, [nyenr.elections.ny.gov](https://nyenr.elections.ny.gov/) | No terms, no copyright line and no license. Its footer links only to ny.gov pages. | Nothing stated |
| [ny.gov Website Disclaimer](https://www.ny.gov/website-disclaimer), read in full | Only about links to other sites. | Nothing |
| [ny.gov Privacy Policy](https://www.ny.gov/privacy-policy) | Searched for copying, reuse, license and similar words: only cookies, email and statistics. | Nothing found |

**The reading:** the terms are **silent** on reusing results: no license, no limit and not even a copyright footer, only accuracy and link disclaimers. That's the same standing as Vermont and West Virginia. Building it is the owner's choice.

**Gap in the record:** the Board's other pages weren't searched for terms beyond its footer's privacy page. County boards of elections' sites weren't looked at.

## Results, checked 2026-11-19

- **Unofficial and incomplete.** Election-night results, last updated 11/19/2026 3:40 PM: 12,076 of 13,187 election districts statewide. Counties still short: **Westchester 0 of 906**, Chautauqua 0 of 91, Fulton 0 of 32, Nassau 1,006 of 1,083, Suffolk 1,067 of 1,070, Broome 125 of 126 and Wyoming 39 of 40. The page warns that Westchester's emergency Election Day ballots are unscanned and the results "incomplete and subject to change".
- **Governor:** Kathy C. Hochul / Adrienne E. Adams 3,631,374 (59.32%; Democratic and Working Families lines), Bruce A. Blakeman / Todd Hood 2,414,240 (39.44%; Republican and Conservative lines). No U.S. Senate race this year. Other contests: Comptroller, Attorney General, U.S. Congress, State Senate, State Assembly, Supreme Court.
- **By county:** a "County Breakdown" option shows all 62 counties. There's no download button.
- **Certified results:** the Board's [results page](https://elections.ny.gov/election-results) has only the certified June 23, 2026 primary.
- **Fetching:** the results site sits behind a browser check. A plain request gets 403 ("Just a moment..."), and Chrome froze on it once before loading. A build script can't fetch it; don't try to get around the check.

## What building it would take

1. The owner chooses it, knowing the terms are silent.
2. Wait for the certified general election results on the Board's results page (December, from past years; the date wasn't looked up), which are files a build can read. Building from the election-night pages would mean saving them by hand, with Westchester missing for now.
3. **Fusion voting:** candidates run on several party lines. Add each candidate's lines together (the page's "by candidate" column does this), and color by the candidate's party, not the line.
4. The usual county-level build, from Census land and adults. Precinct data wasn't looked for.

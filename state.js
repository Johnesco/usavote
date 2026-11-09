// Everything the pages need to know about which state they're showing. A new state gets its own values here and its own
// pages, which name it with <html data-state="...">; joining STATES opens it on the U.S. homepage (home.js).
const TEXAS = {
  slug: 'texas',
  name: 'Texas',
  fips: '48',            // Census state code: the first two digits of its county codes
  countyCount: 254,
  // d3.geoConicEqualArea: standard parallels about 1/6 and 5/6 of the way up the state, centered on its middle longitude.
  // scripts/build_landmask.py and scripts/build_infographic.py must use the same values.
  parallels: [27.5, 35],
  rotate: [99.5, 0],
  middle: [-99.5, 31],   // a spot near the middle, for measuring miles on the map
  summary: 'Every general election from 2008 to 2026, county by county.',
  data: {
    results: 'data/results-2026.json',
    history: 'data/results-history.json',
    precincts: 'data/precincts.json.gz',
    precinctShapes: 'data/precinct-shapes.json.gz',
    land: 'data/landmask.bin.gz',
    cities: 'data/cities.json',
  },
  // where the state opens: any race in any year
  results: { href: 'texas.html', title: 'See the results', text: 'Any race in any year, 2008 to 2026. Bar view, by county or by precinct, or dot view, with one dot per voter.' },
  dots: 'voters.html',
  // the guided flights over the county map, offered on the results page (the voter dot tour is offered on its own page, voters.html)
  flights: [
    { href: 'story.html', title: 'County Flythrough', about: '2026 U.S. Senate', how: 'Plays on its own, about 4 minutes' },
  ],
  tour: true,            // voters.js has a written tour of this state
  // who publishes the results, and until when they're unofficial
  authority: 'the Secretary of State',
  returns: 'election-night returns',
  unofficialUntil: 'the state canvass',
  // the one race whose votes by precinct are on the site; every other race's precinct votes are estimated from its pattern
  base: {
    raceId: '2024-u-s-senate', label: '2024 U.S. Senate', dem: 'Allred', rep: 'Cruz',
    asCounted: '2024 U.S. Senate votes as counted in each precinct.',
    method: `<p><b>By precinct:</b> one column for each voting precinct, on 2024 precinct lines, stacked and colored like the county columns. Precinct votes are on this site for one race, the 2024 U.S. Senate (Texas Legislative Council), and that race shows them as counted. Every other race is an estimate: each party's county total is shared among the county's precincts by that party's share of its 2024 U.S. Senate vote there, so each county still adds up to its result, but a precinct's own number is not a real count. Precincts with fewer than 10 votes are merged into the nearest one in their county. All columns share one height scale, which stays the same at every zoom.</p>`,
  },
};

const OKLAHOMA = {
  slug: 'oklahoma',
  name: 'Oklahoma',
  fips: '40',
  countyCount: 77,
  parallels: [34.2, 36.4], // scripts/build_landmask.py must use the same values
  rotate: [98.7, 0],
  middle: [-97.5, 35.5],
  summary: 'The Nov. 3, 2026 general election, by county.',
  data: {
    results: 'data/ok/results-2026.json',
    history: null,
    precincts: 'data/ok/blocks.json.gz', // one entry per county, for placing dots: same format as Texas's file
    precinctShapes: null,                // county only: no By precinct view or precinct menu
    land: 'data/ok/landmask.bin.gz',
    cities: 'data/ok/cities.json',
  },
  results: { href: 'oklahoma.html', title: 'See the results', text: 'U.S. Senate and seven statewide races in 2026. Bar view by county, or dot view, with one dot per voter.' },
  dots: 'oklahoma-voters.html',
  flights: [],
  tour: false,
  authority: 'the Oklahoma State Election Board',
  returns: 'returns',
  unofficialUntil: 'the state certifies them',
  base: null,            // no precinct results or shapes here (docs/PIPELINE.md, Part 7)
};

const KANSAS = {
  slug: 'kansas',
  name: 'Kansas',
  fips: '20',
  countyCount: 105,
  parallels: [37.5, 39.5], // scripts/build_landmask.py must use the same values
  rotate: [98.3, 0],
  middle: [-98.3, 38.5],
  radiusScaleAt: [-98.3, 38.5], // where dots.js measures a block's radius; the default is a spot in Texas, far outside this state's parallels
  summary: 'The Nov. 3, 2026 general election, by county and by precinct. Unofficial results.',
  data: {
    results: 'data/ks/results-2026.json',
    history: null,
    precincts: 'data/ks/precincts.json.gz',
    precinctShapes: 'data/ks/precinct-shapes.json.gz',
    land: 'data/ks/landmask.bin.gz',
    cities: 'data/ks/cities.json',
  },
  results: { href: 'kansas.html', title: 'See the results', text: 'U.S. Senate and the other statewide races in 2026. Bar view, by county or by precinct, or dot view, with one dot per voter.' },
  dots: 'kansas-voters.html',
  flights: [],
  tour: false,
  authority: 'the Kansas Secretary of State',
  returns: 'unofficial results',
  unofficialUntil: 'the State Board of Canvassers certifies them, due by Dec. 1, 2026',
  // Provisional ballots aren't counted yet and some margins are under 1%, so the pages say who leads, not who won (docs/records/kansas.md)
  won: 'led',
  winner: 'leader',
  votesCounted: "the votes reported in the selected race in each county, for every candidate on the ballot. Per the Secretary of State, they don't include provisional ballots, which counties count in their canvass by Nov. 16, 2026, or votes for write-in candidates, so totals can change.",
  otherVotes: 'third-party votes',
  twoCandidates: "Two candidates on the ballot. Write-ins aren't in these results.",
  // The precinct votes here are for a race that isn't on these pages, so no race's precinct columns are as counted; raceId matches nothing
  base: {
    raceId: null, label: '2024 President', dem: 'Harris', rep: 'Trump',
    asCounted: '',
    method: `<p><b>By precinct:</b> one column for each voting precinct, on 2024 precinct lines (IKE Lab), stacked and colored like the county columns. Every column is an estimate: each party's 2026 county total is shared among the county's precincts by that party's share of its 2024 presidential vote there, so each county still adds up to its result, but a precinct's own number is not a real count. The 2024 presidential votes shown for a chosen precinct are as counted, and they match the Secretary of State's 2024 figures in every county. Precincts with fewer than 10 votes are merged into the nearest one in their county, and precincts with no 2024 votes aren't drawn. All columns share one height scale, which stays the same at every zoom.</p>`,
  },
};

export const STATES = [TEXAS, OKLAHOMA, KANSAS];
export const STATE = STATES.find(s => s.slug === document.documentElement.dataset.state) ?? TEXAS;

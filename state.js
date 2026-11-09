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

const OHIO = {
  slug: 'ohio',
  name: 'Ohio',
  fips: '39',
  countyCount: 88,
  parallels: [39, 41.4], // scripts/build_landmask.py must use the same values
  rotate: [82.7, 0],
  middle: [-82.7, 40.2],
  summary: 'The Nov. 3, 2026 general election, by county. Unofficial and partial, with ballots still outstanding.',
  data: {
    results: 'data/oh/results-2026.json',
    history: null,
    precincts: 'data/oh/blocks.json.gz', // one entry per county, for placing dots: same format as Texas's file
    precinctShapes: null,                // county only: no By precinct view or precinct menu
    land: 'data/oh/landmask.bin.gz',
    cities: 'data/oh/cities.json',
  },
  results: { href: 'ohio.html', title: 'See the results', text: 'U.S. Senate, governor and the other statewide races in 2026, unofficial and partial. Bar view by county, or dot view, with one dot per voter.' },
  dots: 'ohio-voters.html',
  flights: [],
  tour: false,
  authority: 'the Ohio Secretary of State',
  returns: 'unofficial, partial returns',
  unofficialUntil: 'the Secretary of State certifies them',
  // Ballots are outstanding, so a lead isn't yet a win, and "all precincts reporting" alone would mislead (app.js has the wording for other states)
  wonState: 'led the count so far',
  reporting: (meta, fmt) => `with all precincts reporting but ${fmt(meta.ballotsOutstanding)} ballots outstanding (${fmt(meta.uocavaOutstanding)} UOCAVA absentee, ${fmt(meta.provisionalOutstanding)} provisional). County boards count those during the official canvass if they arrive in time and qualify, so these totals will change`,
  base: null,            // no precinct results or shapes here (docs/records/ohio.md)
};

export const STATES = [TEXAS, OKLAHOMA, OHIO];
export const STATE = STATES.find(s => s.slug === document.documentElement.dataset.state) ?? TEXAS;

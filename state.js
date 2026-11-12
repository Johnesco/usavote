// The source of the U.S. House district outlines every state but Texas uses (scripts/build_districts.py), for a page's Sources.
const CD119_SOURCE = `U.S. Census Bureau, <a href="https://www.census.gov/geographies/mapping-files/time-series/geo/cartographic-boundary.html" target="_blank" rel="noopener">2024 Cartographic Boundary Files</a>, 119th Congressional Districts: the U.S. House district outlines, simplified here, for the by-district columns; checked against the Bureau's 2024 TIGER/Line Shapefiles. TIGER/Line is a registered trademark of the Census Bureau; this site is not a Census Bureau product.`;

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
    // By district: each chamber's district outlines and the general elections held on them (scripts/build_districts.py;
    // docs/PIPELINE.md, Part 9). A file that isn't there leaves its chamber without the view.
    districts: {
      'u-s-house': { url: 'data/districts/u-s-house.json.gz', years: [2026] },
      'texas-house': { url: 'data/districts/texas-house.json.gz', years: [2022, 2024, 2026] },
      'texas-senate': { url: 'data/districts/texas-senate.json.gz', years: [2022, 2024, 2026] },
    },
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
    districts: { 'u-s-house': { url: 'data/ok/districts/u-s-house.json.gz', years: [2026] } }, // By district (docs/PIPELINE.md, Part 10)
    districtSource: CD119_SOURCE,
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

const SOUTH_CAROLINA = {
  slug: 'south-carolina',
  name: 'South Carolina',
  mapLabel: 'S.C.',      // the full name doesn't fit inside the state on the homepage map
  fips: '45',
  countyCount: 46,
  parallels: [32.5, 34.7], // scripts/build_landmask.py must use the same values
  rotate: [80.9, 0],
  middle: [-80.9, 33.6],
  radiusScaleAt: [-80.9, 33.6], // where dots.js measures a block's radius
  summary: 'The Nov. 3, 2026 general election, by county and by precinct.',
  data: {
    results: 'data/sc/results-2026.json',
    history: null,
    precincts: 'data/sc/precincts.json.gz',
    precinctShapes: 'data/sc/precinct-shapes.json.gz',
    land: 'data/sc/landmask.bin.gz',
    cities: 'data/sc/cities.json',
    districts: { 'u-s-house': { url: 'data/sc/districts/u-s-house.json.gz', years: [2026] } }, // By district (docs/PIPELINE.md, Part 10)
    districtSource: CD119_SOURCE,
  },
  results: { href: 'south-carolina.html', title: 'See the results', text: 'U.S. Senate and the statewide races in 2026. Bar view, by county or by precinct, or dot view, with one dot per voter.' },
  dots: 'south-carolina-voters.html',
  flights: [],
  tour: false,
  authority: 'the South Carolina State Election Commission',
  returns: 'returns',
  unofficialUntil: 'the state certifies them',
  // 2026 votes on 2020 lines, on the Census Bureau's 2020 voting districts (docs/records/south-carolina.md)
  base: {
    raceId: 'u-s-senate', label: '2026 U.S. Senate', dem: 'Andrews', rep: 'Graham',
    asCounted: '2026 U.S. Senate votes, placed on 2020 voting districts. Most are as counted in that precinct; some precincts are combined, and precincts marked (est.) include votes shared out by rule.',
    method: `<p><b>By precinct:</b> one column for each voting precinct, stacked and colored like the county columns. These are 2026 votes on 2020 lines: the Census Bureau's 2020 voting districts, matched to each 2026 precinct by name, because precinct lines have changed since 2020. Where one 2026 precinct covers several 2020 districts, they are combined into one. Where a 2026 precinct is new since 2020, or the row names no precinct (countywide failsafe and provisional votes), its votes are shared among districts by a written rule, so those districts' numbers are not exact counts, and a precinct where this is a noticeable part of its votes says (est.). The Sources below give the numbers. In the U.S. Senate race, early and mail votes are in their home precincts, as the State Election Commission reports them. Every other race is an estimate: each party's county total is shared among the county's precincts by that party's share of its 2026 U.S. Senate vote there, so each county still adds up to its result, but a precinct's own number is not a real count. Precincts with fewer than 10 votes are merged into the nearest one in their county. All columns share one height scale, which stays the same at every zoom.</p>`,
  },
};

const OHIO = {
  slug: 'ohio',
  name: 'Ohio',
  fips: '39',
  countyCount: 88,
  parallels: [39, 41.4], // scripts/build_landmask.py must use the same values
  rotate: [82.7, 0],
  middle: [-82.7, 40.2],
  radiusScaleAt: [-82.7, 40.2], // where dots.js measures a block's radius
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
  won: 'led',
  winner: 'leader',
  wonState: 'led the count so far',
  reporting: (meta, fmt) => `with all precincts reporting but ${fmt(meta.ballotsOutstanding)} ballots outstanding (${fmt(meta.uocavaOutstanding)} UOCAVA absentee, ${fmt(meta.provisionalOutstanding)} provisional). County boards count those during the official canvass if they arrive in time and qualify, so these totals will change`,
  base: null,            // no precinct results or shapes here (docs/records/ohio.md)
};

const IOWA = {
  slug: 'iowa',
  name: 'Iowa',
  fips: '19',
  countyCount: 99,
  parallels: [40.9, 43], // scripts/build_landmask.py must use the same values
  rotate: [93.4, 0],
  middle: [-93.4, 42],
  radiusScaleAt: [-93.4, 42], // where dots.js measures a block's radius
  summary: 'The Nov. 3, 2026 general election, by county. Results are unofficial.',
  data: {
    results: 'data/ia/results-2026.json',
    history: null,
    precincts: 'data/ia/blocks.json.gz', // one entry per county, for placing dots: same format as Texas's file
    precinctShapes: null,                // county only: no By precinct view or precinct menu
    land: 'data/ia/landmask.bin.gz',
    cities: 'data/ia/cities.json',
    districts: { 'u-s-house': { url: 'data/ia/districts/u-s-house.json.gz', years: [2026] } }, // By district (docs/PIPELINE.md, Part 10)
    districtSource: CD119_SOURCE,
  },
  results: { href: 'iowa.html', title: 'See the results', text: 'U.S. Senate, Governor and the other statewide races in 2026. Bar view by county, or dot view, with one dot per voter.' },
  dots: 'iowa-voters.html',
  flights: [],
  tour: false,
  authority: 'the Iowa Secretary of State',
  returns: 'unofficial returns',
  unofficialUntil: 'the state canvass',
  base: null,            // no precinct results or shapes here (docs/records/iowa.md)
};

const NEW_MEXICO = {
  slug: 'new-mexico',
  name: 'New Mexico',
  fips: '35',
  countyCount: 33,
  parallels: [32.3, 36.1], // scripts/build_landmask.py must use the same values
  rotate: [106, 0],
  middle: [-106, 34.2],
  radiusScaleAt: [-106, 34.2], // where dots.js measures a block's radius
  summary: 'The Nov. 3, 2026 general election, by county. Results are unofficial.',
  data: {
    results: 'data/nm/results-2026.json',
    history: null,
    precincts: 'data/nm/blocks.json.gz', // one entry per county, for placing dots: same format as Texas's file
    precinctShapes: null,                // county only: no By precinct view or precinct menu
    land: 'data/nm/landmask.bin.gz',
    cities: 'data/nm/cities.json',
    districts: { 'u-s-house': { url: 'data/nm/districts/u-s-house.json.gz', years: [2026] } }, // By district (docs/PIPELINE.md, Part 10)
    districtSource: CD119_SOURCE,
  },
  results: { href: 'new-mexico.html', title: 'See the results', text: 'U.S. Senate, Governor and the other statewide races in 2026. Bar view by county, or dot view, with one dot per voter.' },
  dots: 'new-mexico-voters.html',
  flights: [],
  tour: false,
  authority: 'the New Mexico Secretary of State',
  returns: 'unofficial returns',
  unofficialUntil: 'the State Canvassing Board declares them, due Nov. 24, 2026',
  votesCounted: 'the total votes cast in the selected race in each county, counting every candidate on the ballot. New Mexico counts write-ins only for declared write-in candidates, and these results list none in these races.',
  // U.S. House: the site hides a county's figure where fewer than 5 voters cast a ballot (docs/records/new-mexico.md)
  chamberTotals: `County figures add up to the district totals the Secretary of State publishes, except where the state hides a county's figure because fewer than 5 voters cast a ballot there: that figure is left out of its county here and still counted in its district's total.`,
  base: null,            // no precinct results or shapes here (docs/records/new-mexico.md)
};

const IDAHO = {
  slug: 'idaho',
  name: 'Idaho',
  mapLabel: 'ID',        // the full name doesn't fit inside the state on the homepage map
  fips: '16',
  countyCount: 44,
  parallels: [43.2, 47.8], // scripts/build_landmask.py must use the same values
  rotate: [114.1, 0],
  middle: [-114.1, 45.5],
  radiusScaleAt: [-114.1, 45.5], // where dots.js measures a block's radius
  summary: 'The Nov. 3, 2026 general election, by county. Results are unofficial.',
  defaultRace: 'governor', // no Democrat ran for U.S. Senate here, so that race isn't on these pages (docs/records/idaho.md)
  data: {
    results: 'data/id/results-2026.json',
    history: null,
    precincts: 'data/id/blocks.json.gz', // one entry per county, for placing dots: same format as Texas's file
    precinctShapes: null,                // county only: no By precinct view or precinct menu
    land: 'data/id/landmask.bin.gz',
    cities: 'data/id/cities.json',
    districts: { 'u-s-house': { url: 'data/id/districts/u-s-house.json.gz', years: [2026] } }, // By district (docs/PIPELINE.md, Part 10)
    districtSource: CD119_SOURCE,
  },
  results: { href: 'idaho.html', title: 'See the results', text: "Governor and the other statewide races between a Democrat and a Republican in 2026. Bar view by county, or dot view, with one dot per voter." },
  dots: 'idaho-voters.html',
  flights: [],
  tour: false,
  authority: 'the Idaho Secretary of State',
  returns: 'unofficial returns',
  unofficialUntil: 'the State Board of Canvassers certifies them, due by Nov. 24, 2026',
  otherVotes: 'independent, third-party and write-in votes',
  base: null,            // no precinct results or shapes here (docs/records/idaho.md)
};

const SOUTH_DAKOTA = {
  slug: 'south-dakota',
  name: 'South Dakota',
  fips: '46',
  countyCount: 66,
  parallels: [43.1, 45.4], // scripts/build_landmask.py must use the same values
  rotate: [100.2, 0],
  middle: [-100.2, 44.2],
  radiusScaleAt: [-100.2, 44.2], // where dots.js measures a block's radius
  summary: 'The Nov. 3, 2026 general election, by county. Results are unofficial.',
  defaultRace: 'governor', // no Democrat ran for U.S. Senate here, so that race isn't on these pages (docs/records/south-dakota.md)
  data: {
    results: 'data/sd/results-2026.json',
    history: null,
    precincts: 'data/sd/blocks.json.gz', // one entry per county, for placing dots: same format as Texas's file
    precinctShapes: null,                // county only: no By precinct view or precinct menu
    land: 'data/sd/landmask.bin.gz',
    cities: 'data/sd/cities.json',
  },
  results: { href: 'south-dakota.html', title: 'See the results', text: 'Governor, U.S. House and the other statewide races between a Democrat and a Republican in 2026. Bar view by county, or dot view, with one dot per voter.' },
  dots: 'south-dakota-voters.html',
  flights: [],
  tour: false,
  authority: 'the South Dakota Secretary of State',
  returns: 'unofficial returns',
  unofficialUntil: 'the State Canvass Board certifies them',
  votesCounted: "the votes reported in the selected race in each county, for every candidate on the ballot. The state lists 91 provisional ballots cast, counted if accepted just before each county's canvass, so they may not be in these totals. These results list no write-in votes.",
  otherVotes: 'third-party votes',
  twoCandidates: "Two candidates on the ballot. These results list no write-in votes.",
  base: null,            // no precinct results or shapes here (docs/records/south-dakota.md)
};

const GEORGIA = {
  slug: 'georgia',
  name: 'Georgia',
  fips: '13',
  countyCount: 159,
  parallels: [31.1, 34.2], // scripts/build_landmask.py must use the same values
  rotate: [83.2, 0],
  middle: [-83.2, 32.7],
  radiusScaleAt: [-83.2, 32.7], // where dots.js measures a block's radius
  summary: 'The Nov. 3, 2026 general election, by county. Unofficial and partial, with some ballots still to report.',
  data: {
    results: 'data/ga/results-2026.json',
    history: null,
    precincts: 'data/ga/blocks.json.gz', // one entry per county, for placing dots: same format as Texas's file
    precinctShapes: null,                // county only: no By precinct view or precinct menu
    land: 'data/ga/landmask.bin.gz',
    cities: 'data/ga/cities.json',
    districts: { 'u-s-house': { url: 'data/ga/districts/u-s-house.json.gz', years: [2026] } }, // By district (docs/PIPELINE.md, Part 10)
    districtSource: CD119_SOURCE,
  },
  results: { href: 'georgia.html', title: 'See the results', text: 'U.S. Senate, Governor and the other statewide races in 2026, unofficial and partial. Bar view by county, or dot view, with one dot per voter.' },
  dots: 'georgia-voters.html',
  flights: [],
  tour: false,
  authority: 'the Georgia Secretary of State',
  returns: 'unofficial, partial returns',
  unofficialUntil: 'the state certifies them',
  // Some counties' provisional ballots and part of Fulton's absentee ballots aren't reported yet, so a lead isn't yet a win (docs/records/georgia.md)
  won: 'led',
  winner: 'leader',
  wonState: 'led the count so far',
  reporting: (meta, fmt) => `with ${fmt(meta.reporting.precinctsReporting)} of ${fmt(meta.reporting.precincts)} precincts reporting in all ${fmt(meta.reporting.counties)} counties. The state's file doesn't yet have provisional ballots from ${meta.reporting.provisionalNames} counties, and has only part of ${meta.reporting.absenteeNames} County's absentee ballots, so these totals can change`,
  votesCounted: "the votes reported in the selected race in each county, for the two candidates on the ballot. The Secretary of State's file lists no write-in votes in these races.",
  twoCandidates: "Two candidates on the ballot. The Secretary of State's file lists no write-in votes in these races.",
  base: null,            // county only: too few 2026 precincts reach a 2020 voting district clearly (docs/records/georgia.md)
};

const CALIFORNIA = {
  slug: 'california',
  name: 'California',
  fips: '06',
  countyCount: 58,
  parallels: [34.1, 40.4], // scripts/build_landmask.py must use the same values
  rotate: [119.3, 0],
  middle: [-119.3, 37.2],
  radiusScaleAt: [-119.3, 37.2], // where dots.js measures a block's radius
  summary: 'The Nov. 3, 2026 general election, by county. Unofficial and partial: about 3 million ballots were still to be counted.',
  defaultRace: 'governor', // no U.S. Senate race in California in 2026 (docs/records/california.md)
  data: {
    results: 'data/ca/results-2026.json',
    history: null,
    precincts: 'data/ca/blocks.json.gz', // one entry per county, for placing dots: same format as Texas's file
    precinctShapes: null,                // county only: no By precinct view or precinct menu
    land: 'data/ca/landmask.bin.gz',
    cities: 'data/ca/cities.json',
  },
  results: { href: 'california.html', title: 'See the results', text: 'Governor and the other statewide races between a Democrat and a Republican in 2026, unofficial and partial. Bar view by county, or dot view, with one dot per voter.' },
  dots: 'california-voters.html',
  flights: [],
  tour: false,
  authority: 'the California Secretary of State',
  returns: 'unofficial, partial returns',
  unofficialUntil: 'the Secretary of State certifies them, by Dec. 11, 2026',
  // Counting goes on for weeks here, so a lead isn't yet a win (docs/records/california.md)
  won: 'led',
  winner: 'leader',
  wonState: 'led the count so far',
  reporting: (meta, fmt) => `with every precinct reporting, but counties estimated ${fmt(meta.reporting.ballotsRemaining)} ballots still to process as of ${meta.reporting.remainingAsOf} (beside ${fmt(meta.reporting.ballotsProcessed)} processed), so these totals will change`,
  votesCounted: "the votes reported in the selected race in each county, for the two candidates on the ballot. The state's results list no write-in votes.",
  twoCandidates: "Two candidates on the ballot. The state's results list no write-in votes.",
  base: null,            // no precinct results or shapes here (docs/records/california.md)
};

const RHODE_ISLAND = {
  slug: 'rhode-island',
  name: 'Rhode Island',
  mapLabel: 'RI',        // the full name doesn't fit inside the state on the homepage map
  fips: '44',
  countyCount: 5,
  parallels: [41.3, 41.9], // scripts/build_landmask.py must use the same values
  rotate: [71.5, 0],
  middle: [-71.5, 41.6],
  radiusScaleAt: [-71.5, 41.6], // where dots.js measures a block's radius
  summary: 'The Nov. 3, 2026 general election, with cities and towns added up by county. Unofficial and partial.',
  data: {
    results: 'data/ri/results-2026.json',
    history: null,
    precincts: 'data/ri/blocks.json.gz', // one entry per county, for placing dots: same format as Texas's file
    precinctShapes: null,                // county only: no By precinct view or precinct menu
    land: 'data/ri/landmask.bin.gz',
    cities: 'data/ri/cities.json',
    districts: { 'u-s-house': { url: 'data/ri/districts/u-s-house.json.gz', years: [2026] } }, // By district (docs/PIPELINE.md, Part 10)
    districtSource: CD119_SOURCE,
  },
  results: { href: 'rhode-island.html', title: 'See the results', text: 'U.S. Senate and the other statewide races between a Democrat and a Republican in 2026, unofficial and partial. Bar view by county, or dot view, with one dot per voter.' },
  dots: 'rhode-island-voters.html',
  flights: [],
  tour: false,
  authority: 'the Rhode Island elections board', // the pages add 's; the board's own name ends in "Elections"
  returns: 'unofficial, partial returns',
  unofficialUntil: 'the Board of Elections certifies them',
  // Some precincts are marked partly reported, so a lead isn't yet a win (docs/records/rhode-island.md)
  won: 'led',
  winner: 'leader',
  wonState: 'led the count so far',
  reporting: (meta, fmt) => `with all ${meta.reporting.towns} cities and towns reporting, added up here by county, though the Board marks ${meta.reporting.precinctsPartlyReported} of ${meta.reporting.precincts} precincts as partly reported, so these totals can change. The Board's U.S. Senate totals also include ${fmt(meta.reporting.federalOnlySenateVotes)} votes on federal-only ballots, which belong to no town and aren't on this map`,
  otherVotes: 'independent and write-in votes',
  chamberTotals: `Each district's figures are its cities and towns added up. Ballots cast for federal offices only belong to no town, so they are left out of the counties and the districts alike, as in the statewide races.`,
  base: null,            // no precinct results or shapes here (docs/records/rhode-island.md)
};

const VERMONT = {
  slug: 'vermont',
  name: 'Vermont',
  mapLabel: 'VT',        // the full name doesn't fit inside the state on the homepage map
  fips: '50',
  countyCount: 14,
  parallels: [43.1, 44.6], // scripts/build_landmask.py must use the same values
  rotate: [72.5, 0],
  middle: [-72.5, 43.9],
  radiusScaleAt: [-72.5, 43.9], // where dots.js measures a block's radius
  summary: 'The Nov. 3, 2026 general election, with towns added up by county. Results are unofficial.',
  defaultRace: 'governor', // no U.S. Senate race in Vermont in 2026 (docs/records/vermont.md)
  data: {
    results: 'data/vt/results-2026.json',
    history: null,
    precincts: 'data/vt/blocks.json.gz', // one entry per county, for placing dots: same format as Texas's file
    precinctShapes: null,                // county only: no By precinct view or precinct menu
    land: 'data/vt/landmask.bin.gz',
    cities: 'data/vt/cities.json',
  },
  results: { href: 'vermont.html', title: 'See the results', text: 'Governor, U.S. House and the other statewide races in 2026. Bar view by county, or dot view, with one dot per voter.' },
  dots: 'vermont-voters.html',
  flights: [],
  tour: false,
  authority: 'the Vermont Secretary of State',
  returns: 'unofficial returns',
  unofficialUntil: 'the state canvassing committee certifies them',
  reporting: (meta, fmt) => `with all ${meta.reporting.towns} towns reporting, added up here by county`,
  votesCounted: 'the votes reported in the selected race in each county, for every candidate on the ballot and write-ins. Blank votes and overvotes aren\'t counted.',
  base: null,            // no precinct results or shapes here (docs/records/vermont.md)
};

const WEST_VIRGINIA = {
  slug: 'west-virginia',
  name: 'West Virginia',
  mapLabel: 'WV',        // the full name doesn't fit inside the state on the homepage map
  fips: '54',
  countyCount: 55,
  parallels: [37.8, 40.1], // scripts/build_landmask.py must use the same values
  rotate: [80.2, 0],
  middle: [-80.2, 38.9],
  radiusScaleAt: [-80.2, 38.9], // where dots.js measures a block's radius
  summary: 'The Nov. 3, 2026 U.S. Senate race, by county. Results are unofficial.',
  data: {
    results: 'data/wv/results-2026.json',
    history: null,
    precincts: 'data/wv/blocks.json.gz', // one entry per county, for placing dots: same format as Texas's file
    precinctShapes: null,                // county only: no By precinct view or precinct menu
    land: 'data/wv/landmask.bin.gz',
    cities: 'data/wv/cities.json',
  },
  results: { href: 'west-virginia.html', title: 'See the results', text: 'U.S. Senate in 2026, the one statewide race between candidates. Bar view by county, or dot view, with one dot per voter.' },
  dots: 'west-virginia-voters.html',
  flights: [],
  tour: false,
  authority: 'the West Virginia Secretary of State',
  returns: 'unofficial returns',
  unofficialUntil: 'the counties canvass them and the state certifies them',
  votesCounted: 'the votes reported in the selected race in each county, for every candidate on the ballot. These results list no write-in votes.',
  otherVotes: 'third-party votes',
  base: null,            // no precinct results or shapes here (docs/records/west-virginia.md)
};

export const STATES = [TEXAS, OKLAHOMA, KANSAS, SOUTH_CAROLINA, OHIO, IOWA, NEW_MEXICO, IDAHO, GEORGIA, SOUTH_DAKOTA, CALIFORNIA, RHODE_ISLAND, VERMONT, WEST_VIRGINIA];
export const STATE = STATES.find(s => s.slug === document.documentElement.dataset.state) ?? TEXAS;

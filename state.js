// Everything the pages need to know about which state they're showing. A new state gets its own values here, and joins
// STATES at the bottom so the U.S. homepage (home.js) opens it up.
export const STATE = {
  name: 'Texas',
  fips: '48',            // Census state code: the first two digits of its county codes
  countyCount: 254,
  // d3.geoConicEqualArea: standard parallels about 1/6 and 5/6 of the way up the state, centered on its middle longitude.
  // scripts/build_landmask.py and scripts/build_infographic.py must use the same values.
  parallels: [27.5, 35],
  rotate: [99.5, 0],
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
  // the guided flights over the county map, offered on the results page (the voter dot tour is offered on its own page, voters.html)
  flights: [
    { href: 'story.html', title: 'County Flythrough', about: '2026 U.S. Senate', how: 'Scroll at your own pace' },
  ],
};

export const STATES = [STATE];

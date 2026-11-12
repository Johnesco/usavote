// A state's list of sources, as HTML strings: shown under Sources on its results page (app.js) and on the site's
// Sources page (sources.js). Every state but Texas keeps its list in its results file (meta.sources, written by its
// build script), with the source of its district outlines in state.js. Texas's is written here.
const a = (href, text) => `<a href="${href}" target="_blank" rel="noopener">${text}</a>`;
const CC_BY = a('http://www.opendefinition.org/licenses/cc-by', 'Creative Commons Attribution');

// state: an entry of STATES. meta: its results file's meta. histMeta: its history file's meta, if it has one.
export function sourceItems(state, meta, histMeta) {
  if (meta.sources) return [...meta.sources.slice(0, -1), state.data.districtSource, meta.sources.at(-1)].filter(Boolean);
  const histRetrieved = histMeta ? `, retrieved ${histMeta.retrieved}` : '';
  return [
    `Texas Secretary of State, ${a('https://elections.sos.state.tx.us/index.htm', 'Election History')},
      official canvassed county results for the 2008, 2010, 2012, 2014, 2016 and 2018 general elections${histRetrieved}.`,
    `Texas Secretary of State, ${a('https://results.texas-election.com/races', 'election results site')},
      final county results for the 2020, 2022 and 2024 general elections${histRetrieved}.`,
    `U.S. House, Texas House and Texas Senate: the same two sources, read district by district (2008–2018: each district's county-by-county canvass page,
      checked against the Statewide Race Summary; 2020–2024: the county file, checked against the district totals). Districts with a single
      candidate that were left off the November ballot (3 in 2010, 72 in 2022) are counted for the party that nominated a candidate, from the
      same sources' party primary results. Texas Senate terms are staggered: the districts up each year are the ones in that year's primaries.`,
    `Texas Secretary of State, ${a(meta.resultsUrl, 'Election Night Returns, 2026 November General Election')}, county results for statewide races
      (${a(meta.resultsApi, 'data feed')}), as of ${meta.resultsUpdated}, retrieved ${meta.retrieved}. Unofficial until the state canvass.`,
    `Texas Legislative Council, ${a('https://data.capitol.texas.gov/dataset/vtds', 'VTDs_24PG')} (2024 precinct boundaries, listed by the Council under a ${CC_BY} license; simplified here, with precincts under 10 votes merged) and
      ${a('https://ted.capitol.texas.gov/api/Offices/510/2/vtd', '2024 U.S. Senate results by precinct')}, for the by-precinct columns and for placing dots within a county.`,
    `Texas Legislative Council, ${a('https://data.capitol.texas.gov/dataset/planh2316', 'PLANH2316')} (Texas House districts) and
      ${a('https://data.capitol.texas.gov/dataset/plans2168', 'PLANS2168')} (Texas Senate districts), the lines used for the 2022, 2024 and 2026 elections, both listed by the Council under a
      ${CC_BY} license, and
      ${a('https://data.capitol.texas.gov/dataset/planc2333', 'PLANC2333')} (U.S. House districts for the 2026 elections), which the Council lists with no license; all simplified here, for the by-district columns.`,
    `Texas Secretary of State, ${a('https://electionresults.sos.state.tx.us/results.html', 'Election Results, Tuesday, November 3, 2026')} (statewide totals, used as a cross-check).`,
    `U.S. Census Bureau, ${a(meta.landUrl, '2024 Gazetteer Files')}, counties: land area (ALAND_SQMI) and FIPS codes.`,
    `U.S. Census Bureau, ${a('https://www.census.gov/programs-surveys/decennial-census/about/rdo/summary-files.html', '2020 Census Redistricting Data')} (P.L. 94-171):
      cities, and each block's location and adults, for placing dots within a precinct.`,
    `U.S. Census Bureau, ${a('https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html', '2020 TIGER/Line® Shapefiles')}, tabulation blocks:
      where people were counted, for keeping dots off empty land. TIGER/Line® is a registered trademark of the Census Bureau; the land grid here isn't a Census Bureau product.`,
    `U.S. Census Bureau, ${a('https://www.census.gov/geographies/mapping-files/time-series/geo/carto-boundary-file.html', 'Cartographic Boundary Files')}, 2017 counties,
      via ${a('https://github.com/topojson/us-atlas', 'us-atlas')} v3.0.1 (counties-10m.json).`,
    `Software: ${a('https://threejs.org', 'three.js')} r160, ${a('https://github.com/d3/d3-geo', 'd3-geo')} 3.1.1,
      ${a('https://github.com/topojson/topojson-client', 'topojson-client')} 3.1.0.`,
  ];
}

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { geoConicEqualArea, geoCentroid } from 'd3-geo';
import { feature } from 'topojson-client';
import { createCityLabels } from './cities.js';
import { loadPrecincts, precinctVotes } from './dots.js';
import { createPrecinctColumns, loadPrecinctShapes } from './precinct-columns.js';
import { createPlaceMenus, describePlace } from './places.js';
import { STATE } from './state.js';
import { createBusy } from './busy.js';

const GEO_URL = 'https://cdn.jsdelivr.net/npm/us-atlas@3.0.1/counties-10m.json';

// The results page (texas.html, oklahoma.html): any race in any general election the state has here, county by county. ?race= names one.

// ---------- data ----------
const getJSON = url => fetch(url).then(r => { if (!r.ok) throw new Error(r.status); return r.json(); });
let res, us, hist;
try {
  [res, us, hist] = await Promise.all([
    getJSON(STATE.data.results),
    getJSON(GEO_URL),
    STATE.data.history ? getJSON(STATE.data.history) : { races: [], meta: {} },
  ]);
} catch (e) {
  document.getElementById('loading').textContent = 'Could not load the map data. Please reload the page.';
  document.getElementById('loading').classList.add('failed');
  throw e;
}
const meta = res.meta;
const counties = res.counties; // {fips, name, landSqMi}; the selected race's vote fields are filled in by setRace()
const byFips = new Map(counties.map(c => [c.fips, c]));
const geo = feature(us, us.objects.counties);
const stateGeo = { type: 'FeatureCollection', features: geo.features.filter(f => String(f.id).startsWith(STATE.fips)) };
if (stateGeo.features.length !== STATE.countyCount || !stateGeo.features.every(f => byFips.has(String(f.id))))
  console.error('County geometry and results do not line up', stateGeo.features.length);

// Every race of every year. MAJOR: the offices that get a button of their own, in this order.
// A state whose results are still open says so through these (state.js); the defaults are the wording every other state gets.
const WON = STATE.won ?? 'won', WINNER = STATE.winner ?? 'winner', OTHER_VOTES = STATE.otherVotes ?? 'third-party and write-in votes';
const MAJOR = ['president', 'u-s-senate', 'governor', 'lieutenant-governor', 'attorney-general', 'u-s-house', 'texas-house', 'texas-senate'];
const races = [
  ...res.races.map(r => ({ ...r, year: 2026, date: 'Nov. 3, 2026', unofficial: true })),
  ...hist.races,
];
const DEFAULT_RACE = 'u-s-senate';
const YEARS = [...new Set(races.map(r => r.year))].sort((a, b) => b - a); // newest first
// one height scale for all races, so switching races compares like with like
const maxTotal = Math.max(...races.flatMap(r => r.counties.map(row => row[3])));

// Colors: winner's share of the county vote, in 10-point bands (same convention as the reference map)
const BINS = [40, 50, 60, 70, 80, 90];
const REP_C = ['#ffb2b2', '#e27f7f', '#d75d5d', '#d72f30', '#c21b18', '#a80000'];
const DEM_C = ['#a5b0ff', '#7996e2', '#6674de', '#584cde', '#3933e5', '#0d0596'];
const shareOfWinner = c => 100 * Math.max(c.dem, c.rep) / c.total;
// House races only: a county where no district race had votes reported (every race there was unopposed) is gray
const NO_RACE_C = '#3b4352';
function colorFor(c) {
  if (!c.total) return NO_RACE_C;
  const i = Math.max(0, BINS.findLastIndex(b => shareOfWinner(c) >= b));
  return (c.dem > c.rep ? DEM_C : REP_C)[i];
}
const fmt = n => n.toLocaleString('en-US');
const pct = (a, b, d = 1) => (100 * a / b).toFixed(d) + '%';
const short = n => n >= 1e6 ? (n / 1e6).toFixed(2) + 'M' : n >= 1e3 ? Math.round(n / 1e3) + 'K' : String(n);
const $ = id => document.getElementById(id);
const land = counties.reduce((s, c) => s + c.landSqMi, 0);

function bar(label, parts, note = '') {
  return `<div><div class="bar-label">${label}</div><div class="bar">` +
    parts.map(([cls, v, txt]) => `<span class="${cls}" style="width:${v}%">${v >= 9 ? txt : ''}</span>`).join('') +
    `</div>${note ? `<div class="bar-note">${note}</div>` : ''}</div>`;
}
const legLabels = ['<50%', '50–60', '60–70', '70–80', '80–90', '90+'];
for (const [id, cols] of [['legR', REP_C], ['legD', DEM_C]])
  $(id).innerHTML = cols.map((c, i) => `<div><i style="background:${c}"></i>${legLabels[i]}</div>`).join('');

// what the Go to menus last chose (places.js)
let place = null;
let byPrecinct = false, columns = null; // bar view by precinct: columns draws them once they have loaded
let precinctRows = [], precinctOf = new Map(); // one row per precinct on the map, for the race on screen; which row a precinct from the menus is
const HAS_PRECINCTS = !!STATE.data.precinctShapes, BASE = STATE.base, ACTUAL_PRECINCTS = BASE?.raceId; // the one race with results by precinct here; the rest are estimated from it
const renderPlace = () => {
  let line = describePlace(place, race, c => [c.dem, c.rep, c.total]);
  if (byPrecinct && columns) {
    if (place?.kind === 'precinct') {
      const row = precinctRows[precinctOf.get(place.v)], v = place.v;
      line = `<b>Precinct ${v.name}, ${place.c.name} County</b>: ${race.year} ${race.label}, ${votesLine(row)}` +
        (race.id === ACTUAL_PRECINCTS ? '' : `. ${BASE.label}: ${BASE.dem} ${fmt(v.d)}, ${BASE.rep} ${fmt(v.r)}, others ${fmt(v.o)}`);
    }
    line += `<span class="place-note">${race.id === ACTUAL_PRECINCTS ? BASE.asCounted : `Precinct votes are estimated from the ${BASE.label} pattern.`}</span>`;
  }
  $('placeInfo').innerHTML = line;
};
const votesLine = row => { // a precinct's votes in the race on screen, in words
  const who = party => race.chamber ? (party === 'DEM' ? 'Democrats' : 'Republicans') : race.candidates.find(k => k.party === party).last;
  const est = race.id === ACTUAL_PRECINCTS ? '' : 'estimated ';
  return row.total ? `${est}${who('DEM')} ${fmt(Math.round(row.dem))}, ${who('REP')} ${fmt(Math.round(row.rep))}, others ${fmt(Math.round(row.other))}` : 'no votes reported';
};

// ---------- race selection: every number and name on the page comes from the selected race ----------
// SOS party codes
const PARTY_SHORT = { DEM: 'D', REP: 'R', L: 'L', GRE: 'G' };
const PARTY_LONG = { DEM: 'D', REP: 'R', L: 'Libertarian', GRE: 'Green' };
let race, S, D, R, otherLabel, desc;
function setRace(id) {
  id = String(id).replace(/^2026-/, ''); // older links wrote 2026 races this way
  race = races.find(r => r.id === id) || races.find(r => r.id === DEFAULT_RACE);
  // House races add [districts in the county, of those with no Democrat, with no Republican] to each row
  race.counties.forEach(([dem, rep, other, total, districts = 0, noD = 0, noR = 0], i) =>
    Object.assign(counties[i], { dem, rep, other, total, districts, noD, noR }));
  D = race.candidates.find(c => c.party === 'DEM');
  R = race.candidates.find(c => c.party === 'REP');
  const nm = c => D.last === R.last ? c.name : c.last;
  const minor = race.candidates.filter(c => c.party !== 'DEM' && c.party !== 'REP');
  const named = minor.filter(c => c.party !== 'W' && c.votes > 0).map(c => `${c.last} (${PARTY_SHORT[c.party] || c.party})`);
  const hasWrite = minor.some(c => c.party === 'W' && c.votes > 0);
  // null when the race had only the two major-party candidates and no write-in votes
  otherLabel = [...named, hasWrite ? 'write-ins' : null].filter(Boolean).join(' + ') || null;
  if (otherLabel) otherLabel = otherLabel[0].toUpperCase() + otherLabel.slice(1);

  S = { dem: 0, rep: 0, oth: 0, tot: 0, landD: 0, landR: 0, votesInD: 0, votesInR: 0, cntD: 0, cntR: 0, cntNone: 0, landNone: 0 };
  for (const c of counties) {
    S.dem += c.dem; S.rep += c.rep; S.oth += c.other; S.tot += c.total;
    if (!c.total) { S.cntNone++; S.landNone += c.landSqMi; continue; }
    if (c.dem > c.rep) { S.landD += c.landSqMi; S.votesInD += c.total; S.cntD++; }
    else { S.landR += c.landSqMi; S.votesInR += c.total; S.cntR++; }
  }
  desc = [...counties].sort((a, b) => b.total - a.total);

  renderPicker();
  $('kicker').textContent = `${STATE.name} general election`;
  $('title').textContent = `${race.year} ${race.label === 'President' ? 'Presidential Election' : race.label}`;
  document.title = `${$('title').textContent}: ${STATE.name} Election Results`;
  if (race.chamber) { renderChamber(nm); finishRace(); return; }
  if (race.year !== 2026) { renderHistory(minor, nm); finishRace(); return; }
  $('raceLine').textContent = `2026 ${race.label} election in ${STATE.name} · ` +
    [D, R, ...minor.filter(c => c.party !== 'W')].map(c => `${c.name} (${PARTY_LONG[c.party] || c.party})`).join(', ');

  const dWonState = S.dem > S.rep, rMoreLand = S.landR > S.landD;
  const [mapName, mapCnt, mapLand] = rMoreLand ? [nm(R), S.cntR, S.landR] : [nm(D), S.cntD, S.landD];
  const [winName, a, b] = dWonState ? [nm(D), S.dem, S.rep] : [nm(R), S.rep, S.dem];
  $('headline').innerHTML =
    `${mapName} ${WON} <b class="hl">${mapCnt} of ${counties.length}</b> counties, which cover <b class="hl">${pct(mapLand, land, 0)}</b> of ${STATE.name}'s land area. ` +
    `${(dWonState === rMoreLand) ? 'But' : 'And'} ${winName} ${STATE.wonState ?? `${WON} the state`} <b class="hl">${pct(a, S.tot)} to ${pct(b, S.tot)}</b>, a lead of ${fmt(a - b)} votes.`;

  const lD = 100 * S.landD / land, vD = 100 * S.votesInD / S.tot;
  const sD = 100 * S.dem / S.tot, sR = 100 * S.rep / S.tot, sO = 100 - sD - sR;
  $('bars').innerHTML =
    bar(`Land area, split by which candidate ${WON} each county`, [['d', lD, lD.toFixed(0) + '% D'], ['r', 100 - lD, (100 - lD).toFixed(0) + '% R']]) +
    bar(`Votes cast, split by which candidate ${WON} each county`, [['d', vD, vD.toFixed(0) + '% D'], ['r', 100 - vD, (100 - vD).toFixed(0) + '% R']]) +
    bar('Actual statewide vote', [['d', sD, sD.toFixed(1) + '% D'], ['o', sO, ''], ['r', sR, sR.toFixed(1) + '% R']],
      otherLabel ? `Gray: ${otherLabel}, ${sO.toFixed(1)}%` : (STATE.twoCandidates ?? `Two-candidate race: ${STATE.authority} reports no third-party or write-in votes.`));

  const asc = [...desc].reverse(), big = desc[0], small = asc[0];
  $('scale').textContent =
    `The flat map colors each county by who ${WON} it, no matter how many people voted there. A county where ${fmt(small.total)} votes were cast ` +
    `(${small.name}) is painted just as boldly as one where ${(big.total / 1e6).toFixed(2)} million were cast (${big.name}).`;
  $('raiseText').innerHTML =
    `Press <b>See in 3D</b> and each county becomes a column whose height is the number of votes cast there in the ${race.label} race. ` +
    `Most of the red area is land where few people vote, and the tallest columns are in the cities.`;
  let acc = 0, n = 0, accLand = 0;
  while (n < asc.length && acc + asc[n].total < big.total) { acc += asc[n].total; accLand += asc[n].landSqMi; n++; }
  const big5 = desc.slice(0, 5), big5v = big5.reduce((s, c) => s + c.total, 0);
  $('harris').innerHTML =
    `${big.name} County alone cast <b class="hl">${fmt(big.total)}</b> votes, more than the <b class="hl">${n} smallest counties combined</b> ` +
    `(${fmt(acc)}), which together cover ${pct(accLand, land, 0)} of ${STATE.name}'s land area. ` +
    `The five largest counties by votes cast (${big5.map(c => c.name).join(', ')}) cast ${pct(big5v, S.tot, 0)} of all votes.`;
  $('legRTitle').textContent = `${nm(R)} (R) ${WON} the county`;
  $('legDTitle').textContent = `${nm(D)} (D) ${WON} the county`;
  $('method').innerHTML = `
    <p><b>Votes:</b> ${STATE.votesCounted ?? 'the total votes cast in the selected race in each county, counting every candidate including write-ins.'}
    These are ${STATE.authority}'s ${STATE.returns} as of ${meta.resultsUpdated}, ${STATE.reporting?.(meta, fmt) ?? `with all precincts reporting in all ${counties.length} counties`}.
    They are unofficial until ${STATE.unofficialUntil}. For every candidate, the county figures add up exactly to the statewide totals ${STATE.authority} publishes.</p>
    <p><b>Column height</b> is proportional to votes cast (linear scale, the same scale for every race). Counties with very few votes get a thin minimum height so they stay visible. Each raised column is stacked by how the county voted: the runner-up's votes at the bottom in that party's color, ${OTHER_VOTES} in gray, and the ${WINNER}'s votes on top in the county's color. Columns under about 1% of the tallest are too short to read as a stack and are drawn in one color.</p>
    <p><b>Color</b> shows the county ${WINNER}'s share of all votes cast there, in 10-point bands. Percentages are of all votes cast in the race, including ${OTHER_VOTES}.</p>
    <p><b>Land area</b> is the Census Bureau's land area for each county (water excluded). The shapes are drawn from the Census Bureau's 2017 simplified county boundaries.</p>
    <p>The data file and the script that builds it are <a href="https://github.com/johnesco/usavote">on GitHub</a>.</p>`;
  finishRace();
}
function finishRace() {
  renderTable();
  try { history.replaceState(null, '', `?race=${race.id}${byPrecinct ? '&by=precinct' : ''}`); } catch {}
  $('dotLink').href = `${STATE.dots}?race=${race.id}`;
  if (BASE) $('method').insertAdjacentHTML('beforeend', BASE.method);
  if (meshes.length) { if (byPrecinct && columns) setPrecinctRows(); restyle(); }
  renderPlace();
}
// Legislative races (U.S. House, Texas House, Texas Senate): every district of the chamber, added up by county. Seats are won district by
// district, so the text compares the seats each party won with its share of the chamber's vote.
function renderChamber(nm) {
  const n = race.districts.length, seatD = race.seats.DEM || 0, seatR = race.seats.REP || 0;
  const noD = race.districts.filter(d => !d.candidates.some(c => c.party === 'DEM')).length;
  const noR = race.districts.filter(d => !d.candidates.some(c => c.party === 'REP')).length;
  const offBallot = race.districts.filter(d => d.unopposed).length;
  // Texas Senate: staggered terms, so only some of its seats are up in a given year, and many counties have no race at all
  const staggered = race.size > n;
  const noneTxt = staggered ? `no ${race.label} race this year, or only one with a single candidate` : `a single candidate in every ${race.label} race`;
  const yr = `${race.year} `;
  $('raceLine').textContent = `${yr}${race.label} elections in ${STATE.name}${race.date ? `, ${race.date}` : ''}${race.unofficial ? ' (unofficial results)' : ''} · ` +
    (staggered ? `${n} of ${race.size} districts up this year, ` : `${n} districts, `) + `every one added up by county`;
  const dVotes = S.dem > S.rep, dSeats = seatD > seatR;
  const [vW, va, vb] = dVotes ? [nm(D), S.dem, S.rep] : [nm(R), S.rep, S.dem];
  const [sW, sa] = dSeats ? [nm(D), seatD] : [nm(R), seatR];
  const mapR = S.landR > S.landD, [mapName, mapCnt, mapLand] = mapR ? [nm(R), S.cntR, S.landR] : [nm(D), S.cntD, S.landD];
  $('headline').innerHTML =
    `Adding up every ${race.label} district, ${mapName} got more votes in <b class="hl">${mapCnt} of ${counties.length}</b> counties, which cover ` +
    `<b class="hl">${pct(mapLand, land, 0)}</b> of the land${S.cntNone ? ` (${S.cntNone} counties had ${staggered ? `no ${race.label} race this year or no contested one` : 'no contested race'})` : ''}. ${vW} won the ${race.label} vote ${staggered ? 'in the districts that were up' : 'statewide'}, <b class="hl">${pct(va, S.tot)} to ${pct(vb, S.tot)}</b>, ` +
    (dVotes === dSeats ? `and` : `but ${sW} won`) + ` <b class="hl">${sa} of the ${n} seats</b>${staggered ? ` that were up (the Senate has ${race.size})` : ''}.`;
  const lD = 100 * S.landD / land, vD = 100 * S.votesInD / S.tot;
  const sD = 100 * S.dem / S.tot, sR = 100 * S.rep / S.tot, sO = 100 - sD - sR;
  const kD = 100 * seatD / n;
  $('bars').innerHTML =
    bar(`Land area, split by which party got more ${race.label} votes in each county`,
      [['d', lD, lD.toFixed(0) + '% D'], ['o', 100 * S.landNone / land, ''], ['r', 100 * S.landR / land, (100 * S.landR / land).toFixed(0) + '% R']],
      S.cntNone ? `Gray: ${S.cntNone} counties with ${noneTxt}, so no votes were reported.` : '') +
    bar('Votes cast, split the same way', [['d', vD, vD.toFixed(0) + '% D'], ['r', 100 - vD, (100 - vD).toFixed(0) + '% R']]) +
    bar(staggered ? `${race.label} vote, all districts that were up` : `Statewide ${race.label} vote`, [['d', sD, sD.toFixed(1) + '% D'], ['o', sO, ''], ['r', sR, sR.toFixed(1) + '% R']],
      otherLabel ? `Gray: ${otherLabel}, ${sO.toFixed(1)}%` : '') +
    bar(staggered ? `Seats won (${n} of ${race.size} were up)` : 'Seats won', [['d', kD, `${seatD} D`], ['o', 100 * (n - seatD - seatR) / n, ''], ['r', 100 * seatR / n, `${seatR} R`]],
      (noD || noR ? [noD ? `${noD} district${noD > 1 ? 's' : ''} had no Democratic candidate` : '', noR ? `${noR} district${noR > 1 ? 's' : ''} had no Republican candidate` : '']
        .filter(Boolean).join(' and ') + `. Their votes all count for the other party, so the vote shares above lean that way.`
        : 'Every district had both a Democratic and a Republican candidate.') +
      (offBallot ? ` ${offBallot} of them had a single candidate and were not on the ballot, so they add a seat but no votes.` : ''));
  const asc = [...desc].reverse().filter(c => c.total), big = desc[0], small = asc[0];
  const wide = race.districts.reduce((a, d) => d.counties > a.counties ? d : a);
  $('scale').textContent =
    `${race.label} seats are won district by district, and districts don't follow county lines: ${big.name} County had ` +
    `${big.districts} ${race.label} district races on its ballot, while District ${wide.district} spans ${wide.counties} counties. This map adds up every district's votes within each county.`;
  $('raiseText').innerHTML =
    `Press <b>See in 3D</b> and each county becomes a column whose height is the number of ${race.label} votes cast there. ` +
    `${small.name} County cast ${fmt(small.total)}; ${big.name} County cast ${fmt(big.total)}.`;
  const close = [...race.districts].map(d => {
    const [a, b] = d.candidates; return { d, m: b ? (a.votes - b.votes) / d.total : 1, w: a };
  }).sort((x, y) => x.m - y.m).slice(0, 3);
  $('harris').innerHTML = `Closest districts: ` + close.map(({ d, m, w }) =>
    `District ${d.district} (${w.name}, ${PARTY_SHORT[w.party] || w.party}, by ${(100 * m).toFixed(1)} points)`).join('; ') + '.';
  $('legRTitle').textContent = `${nm(R)} got more ${race.label} votes in the county`;
  $('legDTitle').textContent = `${nm(D)} got more ${race.label} votes in the county`;
  $('method').innerHTML = `
    <p><b>Votes:</b> for each county, the votes cast in every ${race.label} district that reaches into it, added up by party. Where a district
    crosses county lines, only the part of its vote cast in that county is counted. A district with no candidate from one party adds
    nothing to that party's total, so counties in uncontested districts lean further toward the other party than its voters may.</p>
    <p><b>Seats:</b> each district's winner, from the same results. ${race.year !== 2026 ? `Source for this race: <a href="${race.sourceUrl}" target="_blank" rel="noopener">${race.source}</a>.` :
      `These are the Secretary of State's election-night returns as of ${meta.resultsUpdated}, unofficial until the state canvass. Every candidate's
      county figures add up exactly to the district totals the Secretary of State publishes.`}</p>
    <p><b>Column height</b> is proportional to votes cast, on the same scale as every other race. Each raised column is stacked by party, and
    <b>color</b> shows the leading party's share of all ${race.label} votes cast in the county, in 10-point bands.</p>
    <p><b>Land area</b> is the Census Bureau's land area for each county (water excluded).</p>
    <p>The data file and the script that builds it are <a href="https://github.com/johnesco/usavote">on GitHub</a>.</p>`;
}

// Earlier years: the facts of the selected race, stated the same way for every year and both parties.
const raceName = r => r.label === 'President' ? 'presidential' : r.label;
const PARTY_WORD = { DEM: 'Democrat', REP: 'Republican' };
function renderHistory(minor, nm) {
  const [W, L] = S.dem > S.rep ? [D, R] : [R, D];
  $('raceLine').textContent = `${race.year} ${raceName(race)} election in ${STATE.name}, ${race.date}${race.unofficial ? ' (unofficial results)' : ''} · ` +
    [D, R, ...minor.filter(c => c.party !== 'W')].map(c => `${c.name} (${PARTY_LONG[c.party] || c.party})`).join(', ');
  const share = c => pct(c.votes, S.tot);
  $('headline').innerHTML =
    `${W.name} (${PARTY_WORD[W.party]}) won with <b class="hl">${share(W)}</b> of the vote to ${share(L)} for ${L.name}, ` +
    `a margin of ${fmt(W.votes - L.votes)} votes out of ${fmt(S.tot)} cast. ` +
    `${nm(R)} carried <b class="hl">${S.cntR}</b> of ${counties.length} counties (${pct(S.landR, land, 0)} of the land area); ` +
    `${nm(D)} carried <b class="hl">${S.cntD}</b> (${pct(S.landD, land, 0)}).`;
  const lD = 100 * S.landD / land, vD = 100 * S.votesInD / S.tot;
  const sD = 100 * S.dem / S.tot, sR = 100 * S.rep / S.tot, sO = 100 - sD - sR;
  $('bars').innerHTML =
    bar('Land area, split by which candidate carried each county', [['d', lD, lD.toFixed(0) + '% D'], ['r', 100 - lD, (100 - lD).toFixed(0) + '% R']]) +
    bar('Votes cast, split by which candidate carried each county', [['d', vD, vD.toFixed(0) + '% D'], ['r', 100 - vD, (100 - vD).toFixed(0) + '% R']]) +
    bar('Statewide vote', [['d', sD, sD.toFixed(1) + '% D'], ['o', sO, ''], ['r', sR, sR.toFixed(1) + '% R']],
      otherLabel ? `Gray: ${otherLabel}, ${sO.toFixed(1)}%` : `Two-candidate race: no third-party or write-in votes were reported.`);
  const asc = [...desc].reverse(), big = desc[0], small = asc[0];
  $('scale').textContent =
    `On the flat map every county is one block of color, whatever its size in votes: ${small.name} County cast ${fmt(small.total)} votes in this race ` +
    `and ${big.name} County cast ${fmt(big.total)}.`;
  $('raiseText').innerHTML =
    `Press <b>See in 3D</b> and each county becomes a column whose height is the number of votes cast there in this race. ` +
    `Every year on this page uses the same height scale, so the columns also show how turnout has changed.`;
  const big5 = desc.slice(0, 5), big5v = big5.reduce((s, c) => s + c.total, 0);
  let acc = 0, n = 0, accLand = 0;
  while (n < asc.length && acc + asc[n].total < big.total) { acc += asc[n].total; accLand += asc[n].landSqMi; n++; }
  $('harris').innerHTML =
    `The five counties that cast the most votes (${big5.map(c => c.name).join(', ')}) cast ${pct(big5v, S.tot, 0)} of the total. ` +
    `${big.name} County alone cast more votes than the ${n} smallest counties combined, which cover ${pct(accLand, land, 0)} of the land area.`;
  $('legRTitle').textContent = `${nm(R)} (R) carried the county`;
  $('legDTitle').textContent = `${nm(D)} (D) carried the county`;
  $('method').innerHTML = `
    <p><b>Votes:</b> the total votes cast in the selected race in each county, counting every candidate including write-ins.
    Source for this race: <a href="${race.sourceUrl}" target="_blank" rel="noopener">${race.source}</a>.
    ${race.unofficial ? `These 2026 figures are election-night returns as of ${meta.resultsUpdated}, unofficial until the state canvass.` : ''}
    For every race, each county's candidate votes add up to its total, and the counties add up to the statewide totals the Secretary of State published.</p>
    <p><b>Column height</b> is proportional to votes cast (linear scale, the same scale for every race and year). Counties with very few votes get a thin minimum height so they stay visible. Each raised column is stacked by how the county voted: the runner-up's votes at the bottom in that party's color, third-party and write-in votes in gray, and the winner's votes on top in the county's color. Columns under about 1% of the tallest are too short to read as a stack and are drawn in one color.</p>
    <p><b>Color</b> shows which candidate carried the county and their share of all votes cast there, in 10-point bands. Percentages are of all votes cast in the race, including third-party and write-in votes.</p>
    <p><b>Land area</b> is the Census Bureau's 2024 land area for each county (water excluded). The shapes are the Census Bureau's 2017 simplified county boundaries; the same 254 counties are used for every year.</p>
    <p>The data files and the scripts that build them are <a href="https://github.com/johnesco/usavote">on GitHub</a>.</p>`;
}

// The tables: every race in the year shown, and the office shown in every year. Each row opens that race on the map.
const SHORT_LABEL = { 'U.S. House': 'U.S. House', 'Texas House': 'Texas House', 'Texas Senate': 'Texas Senate', 'U.S. Senate': 'Senate', 'Lieutenant Governor': 'Lt. Gov.', 'Attorney General': 'Atty. Gen.', 'Governor': 'Governor' };
const tableRows = YEARS.flatMap(y => races.filter(r => r.year === y)).map(r => {
  let dem = 0, rep = 0, tot = 0, cntD = 0;
  r.counties.forEach(([d, p, , t]) => { dem += d; rep += p; tot += t; if (d > p) cntD++; });
  if (r.chamber) { // House: the party that won more seats, its share of the chamber's vote, and its seats
    const n = r.districts.length, sW = (r.seats.DEM || 0) > (r.seats.REP || 0) ? 'DEM' : 'REP';
    const wv = sW === 'DEM' ? dem : rep, lv = sW === 'DEM' ? rep : dem;
    const cnt = r.counties.filter(([d, p, , t]) => t && (sW === 'DEM' ? d > p : p >= d)).length;
    return { r, W: r.candidates.find(c => c.party === sW), seats: `${r.seats[sW]} of ${n} seats`, share: 100 * wv / tot, margin: 100 * (wv - lv) / tot, cnt, tot };
  }
  const dW = dem > rep, W = r.candidates.find(c => c.party === (dW ? 'DEM' : 'REP'));
  return { r, W, share: 100 * Math.max(dem, rep) / tot, margin: 100 * Math.abs(dem - rep) / tot, cnt: dW ? cntD : r.counties.length - cntD, tot };
});
const tableHTML = rows => `<tr><th>Race</th><th>${WINNER[0].toUpperCase() + WINNER.slice(1)}</th><th class="n">Share</th><th class="n">Margin</th><th class="n">Counties</th><th class="n">Votes</th></tr>` +
  rows.map(({ r, W, seats, share, margin, cnt, tot }) =>
    `<tr class="${r.id === race.id ? 'cur' : ''}">` +
    `<td><a href="?race=${r.id}" data-go="${r.id}">${r.year} ${SHORT_LABEL[r.label] || r.label}</a></td>` +
    `<td>${seats ? `${PARTY_SHORT[W.party]}, ${seats}` : `${W.last} (${PARTY_SHORT[W.party]})`}</td><td class="n">${share.toFixed(1)}%</td>` +
    `<td class="n">${margin < 0 ? '−' : ''}${Math.abs(margin).toFixed(1)}</td>` +
    `<td class="n">${cnt}</td><td class="n">${(tot / 1e6).toFixed(2)}M</td></tr>`).join('');
function renderTable() {
  const sameOffice = tableRows.filter(x => x.r.label === race.label);
  $('yearTitle').textContent = `Every ${race.year} race`;
  $('yearTable').innerHTML = tableHTML(tableRows.filter(x => x.r.year === race.year));
  $('officeBlock').hidden = sameOffice.length < 2; // the courts and most 2026 offices are only here for 2026
  $('officeTitle').textContent = `${race.label} in every year`;
  $('officeTable').innerHTML = tableHTML(sameOffice);
}

// ---------- the picker: a year, then a race in that year ----------
const office = r => r.id.replace(/^\d{4}-/, '');
const raceOption = r => `<option value="${r.id}">${r.label}</option>`;
const optionGroup = (label, list) => `<optgroup label="${label}">${list.map(raceOption).join('')}</optgroup>`;
$('yearSelect').innerHTML = YEARS.map(y => `<option value="${y}">${y}</option>`).join('');
let pickerYear = null;
function renderPicker() {
  if (pickerYear !== race.year) { // the main offices first, then whatever else that year had
    pickerYear = race.year;
    const inYear = races.filter(r => r.year === race.year);
    const main = MAJOR.map(k => inYear.find(r => office(r) === k)).filter(Boolean), more = inYear.filter(r => !main.includes(r));
    const groups = [...new Set(more.map(r => r.group))];
    $('raceSelect').innerHTML = (more.length ? optionGroup('Main races', main) : main.map(raceOption).join('')) +
      (groups.length > 1 ? groups.map(g => optionGroup(g, more.filter(r => r.group === g))).join('') : more.length ? optionGroup('More races', more) : '');
  }
  $('yearSelect').value = race.year;
  $('raceSelect').value = race.id;
}
// a new year keeps the same office if that year had it, otherwise opens its first race
function chooseYear(y) {
  if (y === race.year) return;
  const inYear = races.filter(r => r.year === y);
  chooseRace((inYear.find(r => r.label === race.label) || inYear[0]).id);
}
// Visit counting (GoatCounter, no cookies): page views are counted by its script; race choices are sent as events.
function gcEvent(path, title) {
  const send = () => { try { window.goatcounter.count({ path, title, event: true }); } catch {} };
  if (window.goatcounter && window.goatcounter.count) send();
  else document.getElementById('gc')?.addEventListener('load', send, { once: true });
}
function chooseRace(id) { setRace(id); gcEvent(`race/${race.id}`, `${race.year} ${race.label}`); }
$('picker').addEventListener('change', e => {
  if (e.target.id === 'yearSelect') chooseYear(+e.target.value);
  else if (e.target.value !== race.id) chooseRace(e.target.value);
});
document.querySelector('aside').addEventListener('click', e => {
  const a = e.target.closest('a[data-go]'); if (!a) return;
  e.preventDefault(); if (a.dataset.go !== race.id) chooseRace(a.dataset.go);
});
// back to the U.S. homepage, and the guided flights over the county map
$('views').innerHTML = `<a class="back" href="./">← All states</a>`;
if (STATE.flights.length) $('flights').innerHTML = `<h2>Guided flights</h2><p class="flights-note">A guided trip over the county map of the ${STATE.flights[0].about} race, separate from the results here.</p>` +
  STATE.flights.map(f => `<a class="flight" href="${f.href}"><b>▶ ${f.title}</b><span>${f.how}</span></a>`).join('');

$('sources').innerHTML = meta.sources ? `<ol>${meta.sources.map(s => `<li>${s}</li>`).join('')}</ol>` : `<ol>
  <li>Texas Secretary of State, <a href="https://elections.sos.state.tx.us/index.htm" target="_blank" rel="noopener">Election History</a>,
    official canvassed county results for the 2008, 2010, 2012, 2014, 2016 and 2018 general elections, retrieved ${hist.meta.retrieved}.</li>
  <li>Texas Secretary of State, <a href="https://results.texas-election.com/races" target="_blank" rel="noopener">election results site</a>,
    final county results for the 2020, 2022 and 2024 general elections, retrieved ${hist.meta.retrieved}.</li>
  <li>U.S. House, Texas House and Texas Senate: the same two sources, read district by district (2008–2018: each district's county-by-county canvass page,
    checked against the Statewide Race Summary; 2020–2024: the county file, checked against the district totals). Districts with a single
    candidate that were left off the November ballot (3 in 2010, 72 in 2022) are counted for the party that nominated a candidate, from the
    same sources' party primary results. Texas Senate terms are staggered: the districts up each year are the ones in that year's primaries.</li>
  <li>Texas Secretary of State, <a href="${meta.resultsUrl}" target="_blank" rel="noopener">Election Night Returns, 2026 November General Election</a>, county results for statewide races
    (<a href="${meta.resultsApi}" target="_blank" rel="noopener">data feed</a>), as of ${meta.resultsUpdated}, retrieved ${meta.retrieved}.</li>
  <li>Texas Legislative Council, <a href="https://data.capitol.texas.gov/dataset/vtds" target="_blank" rel="noopener">VTDs_24PG</a> (2024 precinct boundaries, listed by the Council under a <a href="http://www.opendefinition.org/licenses/cc-by" target="_blank" rel="noopener">Creative Commons Attribution</a> license; simplified here, with precincts under 10 votes merged) and
    <a href="https://ted.capitol.texas.gov/api/Offices/510/2/vtd" target="_blank" rel="noopener">2024 U.S. Senate results by precinct</a>, for the by-precinct columns.</li>
  <li>Texas Secretary of State, <a href="https://electionresults.sos.state.tx.us/results.html" target="_blank" rel="noopener">Election Results, Tuesday, November 3, 2026</a> (statewide totals, used as a cross-check).</li>
  <li>U.S. Census Bureau, <a href="${meta.landUrl}" target="_blank" rel="noopener">2024 Gazetteer Files</a>, counties: land area (ALAND_SQMI) and FIPS codes.</li>
  <li>U.S. Census Bureau, <a href="https://www.census.gov/geographies/mapping-files/time-series/geo/carto-boundary-file.html" target="_blank" rel="noopener">Cartographic Boundary Files</a>, 2017 counties,
    via <a href="https://github.com/topojson/us-atlas" target="_blank" rel="noopener">us-atlas</a> v3.0.1 (counties-10m.json).</li>
  <li>Software: <a href="https://threejs.org" target="_blank" rel="noopener">three.js</a> r160, <a href="https://github.com/d3/d3-geo" target="_blank" rel="noopener">d3-geo</a> 3.1.1,
    <a href="https://github.com/topojson/topojson-client" target="_blank" rel="noopener">topojson-client</a> 3.1.0.</li>
</ol>`;

// ---------- three.js scene ----------
const stage = document.getElementById('stage');
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
stage.appendChild(renderer.domElement);
const scene = new THREE.Scene();
scene.background = new THREE.Color('#0e1116');
const camera = new THREE.PerspectiveCamera(30, 1, 10, 20000);
scene.add(new THREE.HemisphereLight(0xffffff, 0x334455, 1.1));
const sun = new THREE.DirectionalLight(0xffffff, 1.6); sun.position.set(-600, 900, 700); scene.add(sun);

const projection = geoConicEqualArea().parallels(STATE.parallels).rotate(STATE.rotate)
  .fitExtent([[-500, -500], [500, 500]], stateGeo);
const P = ([lon, lat]) => { const [x, y] = projection([lon, lat]); return new THREE.Vector2(x, -y); };
const ringPts = ring => { const pts = ring.map(P); pts.pop(); return pts; }; // drop closing duplicate point

const mapGroup = new THREE.Group();
mapGroup.rotation.x = -Math.PI / 2; // shapes are drawn in XY and extruded along +Z, which becomes world "up"
scene.add(mapGroup);

const H_MAX = 420, H_FLAT = 0.8;
// A raised column is stacked by how the county voted: the runner-up's votes at the bottom, third-party and write-in
// votes (gray) in the middle, and the winner's votes on top in the county's color. Columns shorter than SPLIT_MIN
// (map units; the tallest column is H_MAX) are too short to read as stacks, so they stay one solid color.
const SPLIT_MIN = 4;
const LOSER_C = { dem: '#584cde', rep: '#d72f30' }, OTHER_C = '#5d6c82';
const meshes = [];   // one per county: the winner's (top) segment, which is also the whole column when not stacked
const pickables = []; // every segment of every county, for hover and label visibility tests
// White county outlines. Each line's own opacity (the 4th color component) is multiplied by this material's.
const edgeMat = new THREE.LineBasicMaterial({ vertexColors: true, transparent: true, opacity: 0.55 });
// Outline of an extruded county (height 1): the border at the bottom and top, plus a vertical line at each corner.
// How strong a corner line is depends on how sharply the border turns there: a turn of 90 degrees or more (a square
// corner or sharper) is drawn fully, gentler turns fade quickly, and turns under 10 degrees get no line at all, so a
// wiggly border such as a river doesn't streak the column with lines.
const CORNER_MIN = 10, CORNER_FULL = 90;
function outlineGeometry(shapes) {
  const pos = [], col = [];
  const line = (a, b, za, zb, alpha) => { pos.push(a.x, a.y, za, b.x, b.y, zb); col.push(1, 1, 1, alpha, 1, 1, 1, alpha); };
  for (const shape of shapes) {
    for (const ring of [shape.getPoints(), ...shape.holes.map(h => h.getPoints())]) {
      const pts = ring.filter((q, i) => i === 0 || !q.equals(ring[i - 1]));
      if (pts.length > 2 && pts[0].equals(pts.at(-1))) pts.pop();
      const n = pts.length;
      for (let i = 0; i < n; i++) {
        const prev = pts[(i + n - 1) % n], cur = pts[i], next = pts[(i + 1) % n];
        line(cur, next, 0, 0, 1); line(cur, next, 1, 1, 1);
        const a = cur.clone().sub(prev).normalize(), b = next.clone().sub(cur).normalize();
        const turn = THREE.MathUtils.radToDeg(Math.acos(THREE.MathUtils.clamp(a.dot(b), -1, 1)));
        if (turn < CORNER_MIN) continue;
        line(cur, cur, 0, 1, turn >= CORNER_FULL ? 1 : ((turn - CORNER_MIN) / (CORNER_FULL - CORNER_MIN)) ** 2);
      }
    }
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  geo.setAttribute('color', new THREE.Float32BufferAttribute(col, 4));
  return geo;
}
const labelsEl = document.getElementById('labels');
// town names for reference on the flat map, clear of the controls
const cityLabels = await createCityLabels(labelsEl, P, { url: STATE.data.cities, avoid: () => [document.querySelector('main .controls')] });
let labeled = [], ready = false; // ready: camera + hover code below has been set up

const params = new URLSearchParams(location.search);
setRace(params.get('race') || DEFAULT_RACE);
if (params.get('race') && params.get('race') === race.id) gcEvent(`link/${race.id}`, `Arrived via link: ${race.year} ${race.label}`);

for (const f of stateGeo.features) {
  const c = byFips.get(String(f.id)); if (!c) continue;
  const polys = f.geometry.type === 'Polygon' ? [f.geometry.coordinates] : f.geometry.coordinates;
  const shapes = polys.map(([outer, ...holes]) => {
    const s = new THREE.Shape(ringPts(outer));
    for (const h of holes) s.holes.push(new THREE.Path(ringPts(h)));
    return s;
  });
  const g = new THREE.ExtrudeGeometry(shapes, { depth: 1, bevelEnabled: false });
  const edges = outlineGeometry(shapes);
  // for the Go to menus: the county's border as line segments, and its extent
  c.lines = [];
  let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
  for (const s of shapes) for (const ring of [s.getPoints(), ...s.holes.map(h => h.getPoints())])
    ring.forEach((a, i) => {
      const b = ring[(i + 1) % ring.length];
      c.lines.push(a.x, a.y, 0, b.x, b.y, 0);
      x0 = Math.min(x0, a.x); x1 = Math.max(x1, a.x); y0 = Math.min(y0, a.y); y1 = Math.max(y1, a.y);
    });
  c.box = { x0, y0, x1, y1 };
  const seg = () => { // segments share the county's shape; each is scaled to its height and lifted into place
    const m = new THREE.Mesh(g, [new THREE.MeshBasicMaterial(), new THREE.MeshLambertMaterial()]);
    m.add(new THREE.LineSegments(edges, edgeMat));
    m.userData = c; mapGroup.add(m); pickables.push(m);
    return m;
  };
  const cen = P(geoCentroid(f));
  c.cx = cen.x; c.cy = cen.y;
  c.lower = seg(); c.middle = seg(); c.mesh = seg();
  meshes.push(c.mesh);
  layout(c, H_FLAT);
}

// place a county's segments for a column of height h
function layout(c, h) {
  c.h = h;
  if (!c.split) {
    c.lower.visible = c.middle.visible = false;
    c.mesh.position.z = 0; c.mesh.scale.z = h;
    return;
  }
  const a = h * c.fLower, b = h * c.fMiddle;
  c.lower.visible = a > 0; c.lower.scale.z = Math.max(a, 1e-4);
  c.middle.visible = b > 0; c.middle.position.z = a; c.middle.scale.z = Math.max(b, 1e-4);
  c.mesh.position.z = a + b; c.mesh.scale.z = Math.max(h - a - b, 1e-4);
}
const paint = (m, color) => { m.material[0].color.copy(color); m.material[1].color.copy(color).multiplyScalar(0.8); };

// apply the selected race to the 3D map: colors, column heights, rise order and labels
function restyle() {
  if (ready) setHover(null);
  const plain = byPrecinct && columns; // by precinct, the counties underneath are a plain floor, in the gaps between precincts
  for (const m of meshes) {
    const c = m.userData;
    c.target = Math.max(H_FLAT, H_MAX * c.total / maxTotal);
    c.baseColor = new THREE.Color(plain ? NO_RACE_C : colorFor(c));
    paint(m, c.baseColor);
    const dWon = c.dem > c.rep;
    c.split = c.target >= SPLIT_MIN;
    c.fLower = (dWon ? c.rep : c.dem) / c.total;
    c.fMiddle = c.other / c.total;
    paint(c.lower, new THREE.Color(plain ? NO_RACE_C : dWon ? LOSER_C.rep : LOSER_C.dem));
    paint(c.middle, new THREE.Color(plain ? NO_RACE_C : OTHER_C));
    layout(c, c.h);
  }
  // rise order: smaller counties start a touch earlier, so the big cities rise last
  [...meshes].sort((a, b) => a.userData.total - b.userData.total)
    .forEach((m, i, arr) => m.userData.delay = 0.25 * i / arr.length);
  labelsEl.innerHTML = '';
  labeled = desc.slice(0, 8).map(c => {
    const el = document.createElement('div'); el.className = 'label';
    el.innerHTML = `${c.name}<small>${short(c.total)} votes</small>`;
    labelsEl.appendChild(el); return { c, el };
  });
  if (ready && !anim) applyProgress(progress, currentPose());
}
restyle();
document.getElementById('loading').remove();

// ---------- camera / animation ----------
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true; controls.maxPolarAngle = Math.PI / 2.05; controls.enabled = false;
controls.minDistance = 2.5; controls.maxDistance = 6000; // close enough for one precinct
controls.screenSpacePanning = false; // moving the map slides along the ground, even when tilted
let dragRotates = false; // in 3D, what a plain drag does; a right-drag does the other
let fitDist = 2000, flatOffZ = 0;
const TOP = { phi: 0.0001, theta: 0 };
const DEFAULT_TILT = { phi: 0.98, theta: -0.22, r: 1.08 };
const RAISED_SHIFT = 0.6; // tilted, the ground is foreshortened, so centering in the clear part of the screen takes a longer shift
// screen space kept clear of the map in the flat view: a margin at the top, the See in 3D controls at the bottom
const PAD = { top: 16, bottom: 84, side: 16 };
const ease = t => t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
const clamp01 = x => Math.min(1, Math.max(0, x));
const playBtn = document.getElementById('play'), scrub = document.getElementById('scrub');
const hintEl = document.getElementById('hint');

// A camera pose is a spherical offset (r, phi, theta) around a target point.
function canonicalPose(p) { // the default camera for animation progress p (0 = flat, top-down; 1 = tilted 3D)
  const ct = ease(clamp01(p / 0.45));
  if (focus) { // the place the Go to menus chose
    const { r, shift } = viewOf(focus.view);
    return { r: r * (1 + 0.25 * ct), phi: TOP.phi + (DEFAULT_TILT.phi - TOP.phi) * ct, theta: TOP.theta + (DEFAULT_TILT.theta - TOP.theta) * ct,
      target: new THREE.Vector3(focus.view.x, focusLift() * ct, -focus.view.y + shift * (1 + RAISED_SHIFT * ct)) };
  }
  return {
    r: fitDist * (1 + (DEFAULT_TILT.r - 1) * ct),
    phi: TOP.phi + (DEFAULT_TILT.phi - TOP.phi) * ct,
    theta: TOP.theta + (DEFAULT_TILT.theta - TOP.theta) * ct,
    target: new THREE.Vector3(0, 110 * ct, flatOffZ * (1 + RAISED_SHIFT * ct)),
  };
}
function currentPose() {
  const s = new THREE.Spherical().setFromVector3(camera.position.clone().sub(controls.target));
  return { r: s.radius, phi: s.phi, theta: s.theta, target: controls.target.clone() };
}
function mixPose(a, b, w) {
  const dt = Math.atan2(Math.sin(b.theta - a.theta), Math.cos(b.theta - a.theta)); // shortest way round
  return { r: a.r + (b.r - a.r) * w, phi: a.phi + (b.phi - a.phi) * w, theta: a.theta + dt * w,
    target: a.target.clone().lerp(b.target, w) };
}
function setPose(o) {
  camera.position.setFromSpherical(new THREE.Spherical(o.r, o.phi, o.theta)).add(o.target);
  camera.lookAt(o.target); controls.target.copy(o.target);
}

let progress = 0, anim = null, going = null; // going: a flight to the place the Go to menus chose
let focus = null; // a county or precinct from the Go to menus, which See in 3D and Flatten stay on: { view, kind, c, v }
let precinctMix = 0; // 0 = county columns up, 1 = precinct columns up
function layoutCounties() {
  const up = 1 - ease(precinctMix);
  for (const m of meshes) {
    const u = m.userData;
    const k = ease(clamp01((progress - 0.3 - u.delay) / 0.45));
    layout(u, H_FLAT + (u.target - H_FLAT) * k * up);
  }
}
function applyProgress(p, pose = null) {
  progress = p;
  setPose(pose || canonicalPose(p));
  layoutCounties();
  scrub.value = Math.round(p * 1000);
  playBtn.textContent = p > 0.5 ? 'Flatten' : 'See in 3D';
}
// Drag moves the map. In 3D the Move / Rotate switch can make it rotate instead, and a right-drag does the other. Scroll or pinch zooms.
function updateMode() {
  const flat = progress === 0, raised = progress === 1;
  controls.enabled = !anim && !going && (flat || raised);
  controls.enableRotate = raised;
  const rotating = raised && dragRotates;
  controls.mouseButtons.LEFT = rotating ? THREE.MOUSE.ROTATE : THREE.MOUSE.PAN;
  controls.mouseButtons.RIGHT = raised && !rotating ? THREE.MOUSE.ROTATE : THREE.MOUSE.PAN;
  controls.touches.ONE = rotating ? THREE.TOUCH.ROTATE : THREE.TOUCH.PAN;
  $('dragMode').hidden = !raised;
  $('dragMove').setAttribute('aria-pressed', String(!rotating));
  $('dragRotate').setAttribute('aria-pressed', String(rotating));
  const what = byPrecinct ? 'precinct' : 'county';
  hintEl.textContent = anim ? `Hover over a ${what}`
    : raised ? `Drag to ${rotating ? 'rotate' : 'move'} · right-drag to ${rotating ? 'move' : 'rotate'} · scroll to zoom · hover over a ${what}`
    : flat ? `Drag to pan · scroll to zoom · hover over a ${what}`
    : `Hover over a ${what}`;
}
function resize() {
  const w = stage.clientWidth, h = stage.clientHeight;
  renderer.setSize(w, h); camera.aspect = w / h; camera.updateProjectionMatrix();
  const t = Math.tan(THREE.MathUtils.degToRad(camera.fov / 2));
  // map spans about ±500 units; fit it inside the padded area of the flat, top-down view
  const usableH = Math.max(100, h - PAD.top - PAD.bottom), usableW = Math.max(100, w - 2 * PAD.side);
  fitDist = 510 * h / (t * Math.min(usableH, usableW));
  // move the target south so the map is centered in the padded area (screen up = north = -z)
  flatOffZ = ((PAD.bottom - PAD.top) / 2) * (2 * fitDist * t / h);
  if (!controls.enabled && !anim && !going) applyProgress(progress);
}
function startAnim(goal, dur) {
  anim = { from: progress, to: goal, start: performance.now(), dur, pose: currentPose() };
  updateMode();
}
playBtn.onclick = () => { if (!focus) clearPlace(); going = null; const goal = progress > 0.5 ? 0 : 1; startAnim(goal, 4200 * Math.abs(goal - progress) + 1); };
scrub.oninput = () => { if (!focus) clearPlace(); going = null; anim = null; applyProgress(scrub.value / 1000); updateMode(); };
$('dragMove').onclick = () => { dragRotates = false; updateMode(); };
$('dragRotate').onclick = () => { dragRotates = true; updateMode(); };
document.getElementById('reset').onclick = () => { clearPlace(); startAnim(progress, 700); };

// ---------- go to a city, county or precinct ----------
// The camera keeps its angle: flat stays flat, and raised keeps its tilt, looking at the top of whatever is there. The
// precinct list is only needed once someone picks a county, so that's when it loads.
const UPM = P(STATE.middle).distanceTo(P([STATE.middle[0], STATE.middle[1] + 0.1])) / 6.905; // map units per mile
const REDUCED = matchMedia('(prefers-reduced-motion: reduce)').matches;
const placeLine = new THREE.LineSegments(new THREE.BufferGeometry(), new THREE.LineBasicMaterial({ color: 0xffffff, depthTest: false }));
placeLine.renderOrder = 5; mapGroup.add(placeLine);
const groundRay = new THREE.Raycaster(), DOWN = new THREE.Vector3(0, -1, 0);
function groundAt(x, y) {
  groundRay.set(new THREE.Vector3(x, 5000, -y), DOWN);
  return groundRay.intersectObjects(pickables, false)[0]?.point.y ?? H_FLAT;
}
// how far back to stand to see an area on the flat map, and how far to shift to center it in the part of the screen the controls leave clear
function viewOf({ halfW, halfH }) {
  const w = stage.clientWidth, h = stage.clientHeight, t = Math.tan(THREE.MathUtils.degToRad(camera.fov / 2));
  const usableH = Math.max(100, h - PAD.top - PAD.bottom), usableW = Math.max(100, w - 2 * PAD.side);
  const r = Math.max(2.5, halfW * h / (t * usableW), halfH * h / (t * usableH));
  return { r, shift: ((PAD.bottom - PAD.top) / 2) * (2 * r * t / h) };
}
// how high to look on the place in focus, when fully raised
function focusLift() {
  if (!focus) return 0;
  if (!byPrecinct || !columns) return focus.c.target;
  return focus.kind === 'precinct' ? columns.height(precinctOf.get(focus.v)) : (focus.c.tallest || 0) * 0.5;
}
const riseK = () => ease(clamp01((progress - 0.3) / 0.45));
function flyTo(view) {
  const { x, y } = view, from = currentPose(), flat = progress === 0, fit = viewOf(view);
  // raised, stand far enough back to see the top of a precinct's column along with its neighbors
  const r = flat || !focus ? fit.r : focus.kind === 'precinct' ? Math.max(fit.r * 2, focusLift() * 1.6) : fit.r * 1.25;
  const lift = focus ? focusLift() * riseK() : groundAt(x, y);
  const to = { r, phi: flat ? TOP.phi : from.phi, theta: flat ? TOP.theta : from.theta, target: new THREE.Vector3(x, lift, -y + fit.shift * (flat ? 1 : 1 + RAISED_SHIFT)) };
  anim = null;
  going = { from, to, start: performance.now(), dur: REDUCED ? 1 : Math.min(3000, Math.max(1200, 500 * Math.abs(Math.log(r / from.r)))) };
  updateMode();
}
function outlinePlace(p) {
  placeLine.geometry.dispose();
  const lines = p?.c ? [...p.c.lines, ...(p.boxEdges && !(byPrecinct && columns) ? p.boxEdges : [])] : null;
  placeLine.geometry = new THREE.BufferGeometry();
  if (lines) placeLine.geometry.setAttribute('position', new THREE.Float32BufferAttribute(lines, 3));
}
let precincts = null;
const menus = createPlaceMenus({ counties: meshes.map(m => m.userData), P, upm: UPM, cityUrl: STATE.data.cities,
  getVtds: !HAS_PRECINCTS ? null : async c => {
    precincts ??= loadPrecincts(P, STATE.data.precincts, null).catch(e => { console.error('Precincts did not load', e); return null; });
    busy.show('precincts', 'Loading precincts…');
    const list = await precincts;
    busy.hide('precincts');
    return list?.byFips.get(c.fips)?.vtds || [];
  },
  onChoose: async p => {
    place = p; focus = p?.c ? { view: p.view, kind: p.kind, c: p.c, v: p.v } : null;
    if (p?.kind === 'precinct' && !byPrecinct) await setBy(true); // a precinct is best seen by precinct
    if (place !== p) return;
    showChosen(); renderPlace(); outlinePlace(p);
    if (p) flyTo(p.view);
  } });
// the camera is going back to the whole state
function clearPlace() { going = null; focus = null; menus.clear(); place = null; showChosen(); renderPlace(); outlinePlace(null); }

// ---------- bar view, by county or by precinct ----------
// Every precinct stands at once, on one height scale that never changes: the tallest in the state's precinct-level race is PRECINCT_H
// map units. Precincts are small, so this is short enough to walk among them close up, unlike the county columns' scale.
const PRECINCT_H = 70;
const PALETTE = [...REP_C, ...DEM_C, LOSER_C.rep, LOSER_C.dem, NO_RACE_C].map(h => new THREE.Color(h));
const PAL_DEM = REP_C.length, PAL_LOSER_R = PAL_DEM + DEM_C.length, PAL_LOSER_D = PAL_LOSER_R + 1, PAL_NONE = PAL_LOSER_D + 1;
const countyFloor = new THREE.LineSegments(new THREE.BufferGeometry(), new THREE.LineBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.6 }));
countyFloor.visible = false; mapGroup.add(countyFloor);
let precinctUnit = 1, precinctCounties = [], loadingColumns = null;
const busy = createBusy(document.querySelector('.map-area'));
function showChosen() { columns?.setChosen(place?.kind === 'precinct' && byPrecinct ? precinctOf.get(place.v) : -1); }
function setPrecinctRows() {
  const actual = race.id === ACTUAL_PRECINCTS, values = [];
  let i = 0;
  for (const c of precinctCounties) {
    const est = actual ? null : precinctVotes(c.list, c);
    c.tallest = 0;
    c.list.vtds.forEach((v, k) => {
      const { d, r, o } = est ? est[k] : v, total = d + r + o, dWon = d > r;
      Object.assign(precinctRows[i++], { dem: d, rep: r, other: o, total });
      const h = total ? Math.max(0.02, total * precinctUnit) : 0;
      c.tallest = Math.max(c.tallest, h);
      const band = total ? Math.max(0, BINS.findLastIndex(b => 100 * Math.max(d, r) / total >= b)) : 0;
      values.push({ h, top: !total ? PAL_NONE : (dWon ? PAL_DEM : 0) + band, low: dWon ? PAL_LOSER_R : PAL_LOSER_D,
        fLow: total ? (dWon ? r : d) / total : 0, fMid: total ? o / total : 0 });
    });
  }
  columns.setValues(values);
}
function loadColumns() {
  loadingColumns ??= (async () => {
    precincts ??= loadPrecincts(P, STATE.data.precincts, null).catch(e => { precincts = null; throw e; });
    const [list, shapes] = await Promise.all([precincts, loadPrecinctShapes(STATE.data.precinctShapes)]);
    if (!list) throw new Error('no precincts');
    const polygons = [];
    let tallest = 0;
    for (const c of counties) {
      c.list = list.byFips.get(c.fips);
      if (!c.list) continue;
      precinctCounties.push(c);
      c.list.vtds.forEach((v, k) => {
        polygons.push(shapes.counties[c.fips][k]);
        precinctOf.set(v, precinctRows.length);
        precinctRows.push({ c, v });
        tallest = Math.max(tallest, v.d + v.r + v.o);
      });
    }
    precinctUnit = PRECINCT_H / tallest;
    columns = createPrecinctColumns(mapGroup, P, polygons, PALETTE, new THREE.Color(OTHER_C));
    columns.group.visible = false;
    countyFloor.geometry.setAttribute('position', new THREE.Float32BufferAttribute(counties.flatMap(c => c.lines), 3));
  })();
  return loadingColumns;
}
function showBy() {
  $('byCounty').setAttribute('aria-pressed', String(!byPrecinct));
  $('byPrecinct').setAttribute('aria-pressed', String(byPrecinct));
}
async function setBy(on) {
  if (on === byPrecinct) return;
  byPrecinct = on; showBy();
  try { history.replaceState(null, '', `?race=${race.id}${on ? '&by=precinct' : ''}`); } catch {}
  if (on && !columns) {
    $('placeInfo').textContent = 'Loading precincts…';
    try { await busy.showNow('columns', 'Loading precincts…'); await loadColumns(); }
    catch (e) {
      busy.hide('columns');
      console.error('The precinct shapes did not load', e);
      $('placeInfo').textContent = 'The precinct map did not load. Please reload the page to try again.';
      byPrecinct = false; showBy(); loadingColumns = null; return;
    }
    if (!byPrecinct) { busy.hide('columns'); return; } // changed back while it was loading
  }
  if (on) setPrecinctRows();
  else columns?.setHover(-1);
  restyle(); showChosen(); renderPlace(); outlinePlace(place); updateMode();
  if (focus && progress > 0) flyTo(focus.view); // the top of what's there has moved
  busy.hide('columns');
}
if (HAS_PRECINCTS) {
  $('byCounty').onclick = () => setBy(false);
  $('byPrecinct').onclick = () => setBy(true);
}

// ---------- hover ----------
const tip = document.getElementById('tip'), ray = new THREE.Raycaster(), mouse = new THREE.Vector2();
const HILITE = new THREE.Color('#ffffff');
let hovered = null;
function setHover(m) {
  if (m === hovered) return;
  if (hovered) hovered.material[0].color.copy(hovered.userData.baseColor);
  hovered = m;
  if (m) m.material[0].color.copy(m.userData.baseColor).lerp(HILITE, 0.35);
}
function onPointer(e) {
  const r = renderer.domElement.getBoundingClientRect();
  mouse.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
  ray.setFromCamera(mouse, camera);
  if (byPrecinct && columns) {
    const o = ray.ray.origin, d = ray.ray.direction; // from the world's axes to the map's: world (x, z, -y)
    const i = columns.pick({ x: o.x, y: -o.z, z: o.y }, { x: d.x, y: -d.z, z: d.y });
    columns.setHover(i);
    if (i >= 0) {
      setHover(null);
      const row = precinctRows[i], { dem, rep, other, total } = row, dWon = dem > rep, actual = race.id === ACTUAL_PRECINCTS;
      const rnd = x => fmt(Math.round(x));
      tip.innerHTML = `<div class="n">Precinct ${row.v.name}</div><div class="row m"><span>${row.c.name} County</span><span></span></div>
        <div class="row m"><span>${race.year} ${race.label}</span><span></span></div>` + (!total ? `<div class="row m"><span>No votes reported</span><span></span></div>` : `
        <div class="row"><span>${D.name} (D)</span><span>${rnd(dem)} · ${pct(dem, total)}</span></div>
        <div class="row"><span>${R.name} (R)</span><span>${rnd(rep)} · ${pct(rep, total)}</span></div>
        ${otherLabel ? `<div class="row m"><span>${otherLabel}</span><span>${rnd(other)} · ${pct(other, total)}</span></div>` : ''}
        <div class="row m"><span>${actual ? 'Total votes' : 'Estimated total'}</span><span>${rnd(total)}</span></div>
        <div class="row m"><span>Margin</span><span style="color:${dWon ? '#8fa8ff' : '#ff8b8b'}">${dWon ? 'D' : 'R'}+${(100 * Math.abs(dem - rep) / total).toFixed(1)}</span></div>
        ${actual ? '' : `<div class="row m"><span>Estimated from ${BASE.label} votes</span><span></span></div>`}`);
      placeTip(e, r);
      return;
    }
  }
  const hit = ray.intersectObjects(pickables, false)[0];
  setHover(hit ? hit.object.userData.mesh : null); // any segment selects its county
  if (!hovered) { tip.style.display = 'none'; return; }
  const c = hovered.userData, dWon = c.dem > c.rep;
  tip.innerHTML = !c.total
    ? `<div class="n">${c.name} County</div><div class="row m"><span>${race.year} ${race.label}</span><span></span></div>
      <div class="row m"><span>No votes reported: ${race.size > race.districts.length ? `no ${race.label} race here this year, or only one with a single candidate` : `every ${race.label} race here had a single candidate`}</span><span></span></div>`
    : `<div class="n">${c.name} County</div>
    <div class="row m"><span>${race.year} ${race.label}</span><span></span></div>
    <div class="row"><span>${D.name} (D)</span><span>${fmt(c.dem)} · ${pct(c.dem, c.total)}</span></div>
    <div class="row"><span>${R.name} (R)</span><span>${fmt(c.rep)} · ${pct(c.rep, c.total)}</span></div>
    ${otherLabel ? `<div class="row m"><span>${otherLabel}</span><span>${fmt(c.other)} · ${pct(c.other, c.total)}</span></div>` : ''}
    <div class="row m"><span>Total votes</span><span>${fmt(c.total)}</span></div>
    <div class="row m"><span>Share of all ${STATE.name} votes</span><span>${pct(c.total, S.tot, 2)}</span></div>
    <div class="row m"><span>Land area</span><span>${fmt(Math.round(c.landSqMi))} sq mi</span></div>
    ${race.chamber ? `<div class="row m"><span>${race.label} districts here</span><span>${c.districts}</span></div>` +
      (c.noD || c.noR ? `<div class="row m"><span>Uncontested</span><span>${[c.noD ? `${c.noD} with no D` : '', c.noR ? `${c.noR} with no R` : ''].filter(Boolean).join(', ')}</span></div>` : '') : ''}
    <div class="row m"><span>Margin</span><span style="color:${dWon ? '#8fa8ff' : '#ff8b8b'}">${dWon ? 'D' : 'R'}+${(100 * Math.abs(c.dem - c.rep) / c.total).toFixed(1)} (${fmt(Math.abs(c.dem - c.rep))} votes)</span></div>`;
  placeTip(e, r);
}
function placeTip(e, r) {
  tip.style.display = 'block';
  const x = e.clientX - r.left, y = e.clientY - r.top;
  tip.style.left = Math.max(8, Math.min(x + 14, r.width - tip.offsetWidth - 8)) + 'px';
  tip.style.top = Math.max(8, Math.min(y + 14, r.height - tip.offsetHeight - 8)) + 'px';
}
// taking hold of the map ends a flight
const stopGoing = () => { if (going) { going = null; updateMode(); } };
renderer.domElement.addEventListener('pointerdown', stopGoing);
renderer.domElement.addEventListener('wheel', stopGoing, { passive: true });
renderer.domElement.addEventListener('pointermove', onPointer);
renderer.domElement.addEventListener('pointerdown', onPointer);
renderer.domElement.addEventListener('pointerleave', () => { tip.style.display = 'none'; setHover(null); columns?.setHover(-1); });

// ---------- loop ----------
const v = new THREE.Vector3(), labelRay = new THREE.Raycaster();
// A label is shown only if the top of its own column is visible (not hidden behind a taller one),
// so a label can never appear to belong to a different county's column.
function anchorVisible(c, world) {
  labelRay.set(camera.position, world.clone().sub(camera.position).normalize());
  const hit = labelRay.intersectObjects(pickables, false)[0];
  return !!hit && hit.object.userData === c;
}
let lastFrame = 0;
function frame(now) {
  // by county or by precinct: one set of columns goes down as the other comes up
  const goal = byPrecinct && columns ? 1 : 0, dt = now - lastFrame; lastFrame = now;
  if (precinctMix !== goal) {
    const step = REDUCED ? 1 : Math.min(dt, 100) / 900;
    precinctMix = goal > precinctMix ? Math.min(goal, precinctMix + step) : Math.max(goal, precinctMix - step);
    layoutCounties();
  }
  if (anim) {
    // glide from wherever the user left the camera onto the default path, then follow it
    const t = clamp01((now - anim.start) / anim.dur), p = anim.from + (anim.to - anim.from) * t;
    applyProgress(p, mixPose(anim.pose, canonicalPose(p), ease(clamp01(t / 0.6))));
    if (t === 1) { anim = null; updateMode(); }
  }
  if (going) {
    // zoom evenly, and rise a little to cross from one place to another
    const t = clamp01((now - going.start) / going.dur), e = ease(t), { from, to } = going;
    const across = from.target.distanceTo(to.target);
    const r = Math.exp(Math.log(from.r) + (Math.log(to.r) - Math.log(from.r)) * e) + Math.sin(Math.PI * e) * across * 0.4;
    setPose({ ...mixPose(from, to, e), r });
    if (t === 1) { going = null; updateMode(); }
  }
  if (controls.enabled) controls.update();
  // close enough for one precinct without cutting off anything near the camera
  camera.near = Math.min(10, Math.max(0.3, camera.position.distanceTo(controls.target) * 0.1));
  camera.updateProjectionMatrix();
  placeLine.position.z = (place?.c?.h ?? H_FLAT) + 0.05; // on top of the county's column
  const showing = columns && precinctMix > 0;
  placeLine.material.depthTest = !!showing && progress > 0.02; // by precinct, the county's border is on the ground, among the columns
  if (columns) {
    columns.group.visible = countyFloor.visible = showing;
    if (showing) {
      const dist = camera.position.distanceTo(controls.target);
      const lift = H_FLAT + Math.max(0.02, dist * 0.0006); // above the floor, by enough to stay clear of it from any distance
      columns.group.position.z = lift;
      columns.group.scale.z = Math.max(1e-5, riseK() * ease(precinctMix));
      countyFloor.position.z = lift + 0.02;
      placeLine.position.z = lift + 0.04;
      columns.lineMat.opacity = 0.5 * clamp01((fitDist * 0.35 - dist) / (fitDist * 0.3)); // too fine to see from far out
      columns.lineMat.visible = columns.lineMat.opacity > 0.01;
    }
  }
  renderer.render(scene, camera);
  const w = stage.clientWidth, h = stage.clientHeight, k = clamp01((progress - 0.7) / 0.3) * (1 - ease(precinctMix));
  cityLabels.update(camera, mapGroup, w, h, 1 - clamp01(progress / 0.2)); // hidden once columns rise: they'd float over the wrong ones
  const placed = [];
  for (const { c, el } of labeled) { // largest first; hide a label that would overlap one already shown
    v.set(c.cx, c.cy, c.h).applyMatrix4(mapGroup.matrixWorld);
    const hidden = k > 0 && !anchorVisible(c, v);
    v.project(camera);
    const x = (v.x + 1) / 2 * w, y = (1 - v.y) / 2 * h, bw = el.offsetWidth, bh = el.offsetHeight;
    const box = [x - bw / 2, y - bh * 1.2, x + bw / 2, y - bh * 0.2];
    const clash = hidden || placed.some(b => box[0] < b[2] && box[2] > b[0] && box[1] < b[3] && box[3] > b[1]);
    if (!clash && k > 0) placed.push(box);
    el.style.opacity = (clash || v.z >= 1) ? 0 : k;
    el.style.left = x + 'px';
    el.style.top = y + 'px';
  }
  requestAnimationFrame(frame);
}
const fit = new ResizeObserver(resize);
fit.observe(stage);
resize();
updateMode();
ready = true;
if (HAS_PRECINCTS && params.get('by') === 'precinct') setBy(true);
requestAnimationFrame(frame);

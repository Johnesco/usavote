// Misreading the Map: a guided flight over the dot view's map of the 2026 U.S. Senate race in Texas, one misreading of the
// flat county map at a time. It opens on that flat map, every county painted for whoever won it, and takes apart three ways
// it's misread. Then it puts the same votes on the map as dots, one per voter, and refines where they go in three steps:
// spread evenly over each county (all the flat map knew), then by precinct, then by census block, to take apart two more.
//
// The three placements are three sets of dots (dots.js), placed at load in the background, each by its own worker; the
// flight switches between them by dissolving one into the next. It runs on a clock: everything on screen, captions
// included, is worked out from the time alone, so window.misread.seek(seconds) draws any moment exactly, for recording a
// video frame by frame (?record=1 hides the controls and leaves the clock to seek).
import * as THREE from 'three';
import { geoConicEqualArea, geoCentroid } from 'd3-geo';
import { feature } from 'topojson-client';
import { createDots, countyTris, loadPrecincts, precinctUnits, precinctVotes, DOT_C } from './dots.js';
import { createBusy } from './busy.js';
import { STATE } from './state.js';
import { createCityLabels } from './cities.js';

const GEO_URL = 'https://cdn.jsdelivr.net/npm/us-atlas@3.0.1/counties-10m.json';
const $ = id => document.getElementById(id);
const fmt = n => n.toLocaleString('en-US');
const short = n => n >= 1e6 ? (n / 1e6).toFixed(2) + ' million' : fmt(n);
const pct = (a, b, d = 0) => (100 * a / b).toFixed(d) + '%';
const getJSON = url => fetch(url).then(r => { if (!r.ok) throw new Error(r.status); return r.json(); });
const query = new URLSearchParams(location.search);
const RECORD = query.get('record') === '1';
const page = document.querySelector('.misread');
if (RECORD) page.classList.add('recording');

let res, us;
try { [res, us] = await Promise.all([getJSON(STATE.data.results), getJSON(GEO_URL)]); }
catch (e) { $('loading').textContent = 'Could not load the map data. Please reload the page.'; $('loading').classList.add('failed'); throw e; }

// ---------- data: the 2026 U.S. Senate race, by county ----------
const race = res.races.find(r => r.id === 'u-s-senate');
const counties = res.counties.map((c, i) => {
  const [dem, rep, other, total] = race.counties[i];
  return { ...c, dem, rep, other, total, density: total / c.landSqMi };
});
const byFips = new Map(counties.map(c => [c.fips, c]));
const byName = name => counties.find(c => c.name === name);
const D = race.candidates.find(c => c.party === 'DEM'), R = race.candidates.find(c => c.party === 'REP');
const sum = (list, f) => list.reduce((s, c) => s + f(c), 0);
const TOT = sum(counties, c => c.total), LAND = sum(counties, c => c.landSqMi);
const dWon = c => c.dem > c.rep;
const RWON = counties.filter(c => !dWon(c)), DWON = counties.filter(dWon);
const HIDDEN_D = sum(RWON, c => c.dem), HIDDEN_R = sum(DWON, c => c.rep);
const SPARSE_PER = 5; // voters per square mile: the counties below it are "nearly empty"
const SPARSE = counties.filter(c => c.density < SPARSE_PER);
const margin = c => Math.abs(c.dem - c.rep);
const CLOSEST = [...counties].sort((a, b) => margin(a) / a.total - margin(b) / b.total)[0];
const BIGGEST = [...counties].sort((a, b) => b.total - a.total)[0];
const FEWEST = [...counties].sort((a, b) => a.total - b.total)[0];
// a big county the winner of the state lost: its hidden voters are the closest-up example
const RED_CITY = byName('Lubbock');
const HARRIS = byName('Harris'), BREWSTER = byName('Brewster');
// the emptiest corner of the state, for misreading 4
const FAR_WEST = ['Hudspeth', 'Culberson', 'Jeff Davis', 'Presidio', 'Brewster', 'Pecos', 'Terrell', 'Reeves', 'Loving'].map(byName);

// ---------- map geometry (same projection as the other pages) ----------
const geo = feature(us, us.objects.counties);
const tx = { type: 'FeatureCollection', features: geo.features.filter(f => String(f.id).startsWith(STATE.fips)) };
const projection = geoConicEqualArea().parallels(STATE.parallels).rotate(STATE.rotate).fitExtent([[-500, -500], [500, 500]], tx);
const P = ([lon, lat]) => { const [x, y] = projection([lon, lat]); return new THREE.Vector2(x, -y); };
const ringPts = ring => { const pts = ring.map(P); pts.pop(); return pts; };
const UPM = P(STATE.middle).distanceTo(P([STATE.middle[0], STATE.middle[1] + 0.1])) / 6.905; // map units per mile

const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: RECORD });
renderer.setPixelRatio(RECORD ? 1 : Math.min(devicePixelRatio, 2));
$('stage').appendChild(renderer.domElement);
const scene = new THREE.Scene();
scene.background = new THREE.Color('#0e1116');
const FOV = 30, TAN = Math.tan(THREE.MathUtils.degToRad(FOV / 2));
const camera = new THREE.PerspectiveCamera(FOV, 1, 1, 10000);
const mapGroup = new THREE.Group();
mapGroup.rotation.x = -Math.PI / 2;
scene.add(mapGroup);

const ordered = [], allEdges = [];
for (const f of tx.features) {
  const c = byFips.get(String(f.id)); if (!c) continue;
  const polys = f.geometry.type === 'Polygon' ? [f.geometry.coordinates] : f.geometry.coordinates;
  const shapes = polys.map(([outer, ...holes]) => {
    const s = new THREE.Shape(ringPts(outer));
    for (const h of holes) s.holes.push(new THREE.Path(ringPts(h)));
    return s;
  });
  c.tris = countyTris(shapes);
  const edges = [];
  for (const s of shapes) for (const ring of [s.getPoints(), ...s.holes.map(h => h.getPoints())])
    for (let i = 0; i < ring.length; i++) { const a = ring[i], b = ring[(i + 1) % ring.length]; edges.push(a.x, a.y, 0, b.x, b.y, 0); }
  c.edges = edges; allEdges.push(...edges);
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (let i = 0; i < c.tris.length; i += 2) {
    x0 = Math.min(x0, c.tris[i]); x1 = Math.max(x1, c.tris[i]); y0 = Math.min(y0, c.tris[i + 1]); y1 = Math.max(y1, c.tris[i + 1]);
  }
  c.box = { x0, y0, x1, y1 };
  const cen = P(geoCentroid(f)); c.cx = cen.x; c.cy = cen.y;
  c.hot = { x: c.cx, y: c.cy, voters: c.density };
  ordered.push(c);
}
// the closest county's nearest big neighbor of the same color, won by a landslide: the flat map paints both the same
const SAME_SIDE = ordered.filter(c => dWon(c) === dWon(CLOSEST) && c !== CLOSEST && c.total > 100000)
  .sort((a, b) => Math.hypot(a.cx - CLOSEST.cx, a.cy - CLOSEST.cy) - Math.hypot(b.cx - CLOSEST.cx, b.cy - CLOSEST.cy))[0];
const lineGeo = pts => { const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(pts, 3)); return g; };

// ---------- the flat map: every county one solid color, for whoever won it ----------
const WIN_C = { dem: '#3933e5', rep: '#c21b18' }; // the bar view's colors for a county won by 60% to 70%
const fillPos = [], fillCol = [];
for (const c of ordered) {
  const col = new THREE.Color(dWon(c) ? WIN_C.dem : WIN_C.rep);
  for (let i = 0; i < c.tris.length; i += 2) { fillPos.push(c.tris[i], c.tris[i + 1], 0); fillCol.push(col.r, col.g, col.b); }
}
const fillGeo = new THREE.BufferGeometry();
fillGeo.setAttribute('position', new THREE.Float32BufferAttribute(fillPos, 3));
fillGeo.setAttribute('color', new THREE.Float32BufferAttribute(fillCol, 3));
const fillMat = new THREE.MeshBasicMaterial({ vertexColors: true, transparent: true, opacity: 1, depthTest: false, side: THREE.DoubleSide });
const fillMesh = new THREE.Mesh(fillGeo, fillMat);
fillMesh.renderOrder = -1; mapGroup.add(fillMesh);
// county lines: dark over the flat map, faint white over the dots
const borderMat = new THREE.LineBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.13, depthTest: false });
const borders = new THREE.LineSegments(lineGeo(allEdges), borderMat);
borders.renderOrder = 1; mapGroup.add(borders);
const focusMat = new THREE.LineBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0, depthTest: false });
const focusLine = new THREE.LineSegments(new THREE.BufferGeometry(), focusMat);
focusLine.renderOrder = 2; mapGroup.add(focusLine);

// ---------- three ways to place the same voters ----------
// county: spread evenly over each county, each county's dots mixed in its own proportions: all the flat map knows
// precinct: each party's county total shared among its precincts by that party's 2024 Senate vote there, spread evenly over
//           each precinct's land (its blocks weighted by area, not people, and no land mask)
// block:    the dot view's own placement, by precinct and then by where adults live (dots.js precinctUnits)
$('loading').textContent = 'Loading precincts…';
let PC = null;
try { PC = await loadPrecincts(P, STATE.data.precincts, STATE.data.land); } catch (e) { console.error('Precincts did not load', e); }
const HOT_R = 0.5;
function precinctEvenUnits(county, votes) {
  const { vtds } = county, n = vtds.reduce((s, v) => s + v.pts.length / 4, 0);
  const units = new Float32Array(n * 6), est = precinctVotes(county, votes);
  let j = 0;
  vtds.forEach((v, k) => {
    const { d, r, o } = est[k];
    let area = 0;
    for (let i = 0; i < v.pts.length; i += 4) area += v.pts[i + 2] ** 2;
    for (let i = 0; i < v.pts.length; i += 4) {
      const s = area > 0 ? v.pts[i + 2] ** 2 / area : 0;
      units.set([v.pts[i], v.pts[i + 1], v.pts[i + 2], d * s, r * s, o * s], j); j += 6;
    }
  });
  return units;
}
if (PC) for (const c of ordered) {
  const pc = PC.byFips.get(c.fips); if (!pc) continue;
  c.units = precinctUnits(pc, c);
  c.evenUnits = precinctEvenUnits(pc, c);
  c.precincts = pc.vtds.length;
  const spot = PC.hot?.[c.fips]; if (!spot) continue;
  const h = P([spot[0], spot[1]]), r2 = (HOT_R * UPM) ** 2, u = c.units;
  let n = 0;
  for (let i = 0; i < u.length; i += 6) if ((u[i] - h.x) ** 2 + (u[i + 1] - h.y) ** 2 <= r2) n += u[i + 3] + u[i + 4] + u[i + 5];
  c.hot = { x: h.x, y: h.y, voters: n / (Math.PI * HOT_R ** 2) };
}
const SETS = ['county', 'precinct', 'block'];
const sets = {}, ready = {};
const placing = [];
for (const name of SETS) {
  const dots = createDots({ depthTest: false });
  dots.uniforms.uP.value = 0; dots.uniforms.uReveal.value = 0;
  dots.group.visible = false;
  mapGroup.add(dots.group);
  if (name === 'block') dots.setLand(PC?.land);
  sets[name] = dots;
  const list = ordered.map(c => {
    const { tris, dem, rep, other } = c;
    if (name === 'block' && c.units) return { tris, units: c.units, dem, rep, other };
    if (name === 'precinct' && c.evenUnits) return { tris, units: c.evenUnits, dem, rep, other };
    return { tris, dem, rep, other };
  });
  placing.push(dots.place(list, { seed: 2026 }).then(() => { ready[name] = true; needsDraw = true; }));
}
const allPlaced = Promise.all(placing);

// ---------- layout ----------
let W = 1, H = 1, area = { w: 1, h: 1, ox: 0, oy: 0 }, needsDraw = true;
function resize() {
  W = $('stage').clientWidth; H = $('stage').clientHeight;
  renderer.setSize(W, H);
  camera.aspect = W / H;
  const wide = W > 760, bar = $('topnav').offsetHeight;
  page.style.setProperty('--bar', `${bar}px`);
  // wide: the caption on the left and the list of misreadings on the right, the map between them; narrow: above the caption
  // (the list hides below 1100 pixels wide: misread.css)
  area = W > 1100 ? { w: W - 700, h: H - 90 - bar, ox: -90, oy: -bar / 2 }
    : wide ? { w: W - 440, h: H - 90 - bar, ox: -220, oy: -bar / 2 } : { w: W, h: H * 0.55, oy: H * 0.15, ox: 0 };
  camera.setViewOffset(W, H, area.ox, area.oy, W, H);
  camera.updateProjectionMatrix();
  for (const d of Object.values(sets)) d.uniforms.uViewH.value = H * renderer.getPixelRatio();
  needsDraw = true;
}
const fitDist = (halfW, halfH) => Math.max(halfW * H / (TAN * area.w), halfH * H / (TAN * area.h));
const stateView = (tilt = 0.0001, heading = 0) => ({ x: 0, y: 0, d: fitDist(520, 520), tilt, heading });
const boxView = (cs, tilt = 0.0001, heading = 0, pad = 1.3) => {
  const x0 = Math.min(...cs.map(c => c.box.x0)), x1 = Math.max(...cs.map(c => c.box.x1));
  const y0 = Math.min(...cs.map(c => c.box.y0)), y1 = Math.max(...cs.map(c => c.box.y1));
  return { x: (x0 + x1) / 2, y: (y0 + y1) / 2, d: fitDist(pad * (x1 - x0) / 2, pad * (y1 - y0) / 2), tilt, heading };
};
const milesView = (p, miles, tilt = 0.0001, heading = 0) => ({ x: p.x, y: p.y, d: (miles * UPM / 2) * H / (TAN * area.h), tilt, heading });
const viewMiles = v => 2 * v.d * TAN * area.h / H / UPM;
const SEP_PX = 16;
const gapMiles = c => 1 / Math.sqrt(Math.max(c.hot.voters, 1));
const closeMiles = c => Math.min(3, Math.max(0.15, area.h * gapMiles(c) / SEP_PX));

// ---------- the scenes ----------
// Each scene flies from where the last one ended, then holds `hold` seconds. fill: how solid the flat map is (0 to 1).
// dots: which placement is shown ('county', 'precinct', 'block' or none), dissolving from the last scene's over `mix`
// seconds (the flight's length unless set). dot: a voter's dot width in miles. step: which misreading the scene is about.
// focus: counties outlined; labels: [county, html] pinned to counties.
const DOT_FAR = 0.005;
const MISREADINGS = [
  'Bigger counties have more voters',
  'A county’s color shows how it voted',
  'A red county has no Democrats',
  'Most voters live in the red',
  'Everyone in a county votes alike',
];
const label = (c, line) => [c, `${c.name}<small>${line}</small>`];
const splitTxt = c => `${D.last} ${pct(c.dem, c.total)}, ${R.last} ${pct(c.rep, c.total)}`;
const myth = n => `<div class="kicker">Misreading ${n} of ${MISREADINGS.length}</div><p class="myth">“${MISREADINGS[n - 1]}.”</p>`;
const flatArea = pct(sum(RWON, c => c.landSqMi), LAND);
const midHarris = () => HARRIS.hot; // the precinct and block steps zoom straight down toward the county's most crowded spot

const scenes = [
  { fly: 0, hold: 13, fill: 1, view: () => stateView(), html: () => `
      <div class="kicker">Texas · U.S. Senate · Nov. 3, 2026</div>
      <h1>Misreading the Map</h1>
      <p>This is the map most people saw on election night: each of ${STATE.countyCount} counties painted for whoever won it.
      It is <b class="hl">${flatArea} red</b>.</p>
      <p>But <span class="d">${D.name}</span>, the Democrat, won, ${pct(D.votes, TOT, 1)} to ${pct(R.votes, TOT, 1)}: by
      <b class="hl">${fmt(D.votes - R.votes)}</b> votes.</p>
      <p>Nothing on the map is wrong. It's just easy to misread. Here are five ways, one at a time.</p>` },

  { step: 1, fly: 2, hold: 14, fill: 1, view: () => stateView(0.15), focus: [FEWEST, BIGGEST],
    labels: [label(FEWEST, `${fmt(FEWEST.total)} voters`), label(BIGGEST, `${short(BIGGEST.total)} voters`)], html: () => `
      ${myth(1)}
      <p>On this map, a county counts for as much as its land. ${FEWEST.name} County, where <b>${fmt(FEWEST.total)}</b> people voted,
      covers ${fmt(Math.round(FEWEST.landSqMi))} square miles. ${BIGGEST.name} County, where <b>${fmt(BIGGEST.total)}</b> did, covers
      ${fmt(Math.round(BIGGEST.landSqMi))}.</p>
      <div class="vs"><div><b>${(BIGGEST.landSqMi / FEWEST.landSqMi).toFixed(1)}×</b>as much land in ${BIGGEST.name}</div>
      <div><b>${fmt(Math.round(BIGGEST.total / FEWEST.total))}×</b>as many voters</div></div>
      <p>Land doesn't vote. People do.</p>` },

  { step: 2, fly: 3, hold: 14, fill: 1, view: () => boxView([CLOSEST, SAME_SIDE], 0.12, 0, 1.6), focus: [CLOSEST, SAME_SIDE],
    labels: [label(CLOSEST, splitTxt(CLOSEST)), label(SAME_SIDE, splitTxt(SAME_SIDE))], html: () => `
      ${myth(2)}
      <p>${CLOSEST.name} County, the closest in the state, went to ${dWon(CLOSEST) ? D.last : R.last} by <b>${fmt(margin(CLOSEST))} votes</b>
      out of ${fmt(CLOSEST.total)}.</p>
      <p>Next door, ${SAME_SIDE.name} County went ${dWon(SAME_SIDE) ? D.last : R.last}'s way by a landslide: ${splitTxt(SAME_SIDE)}.</p>
      <p>The flat map paints them the same solid color. A county won by a hair and one won by a landslide look identical.</p>` },

  { step: 3, fly: 3, hold: 14, fill: 1, view: () => stateView(0.1), html: () => `
      ${myth(3)}
      <p><span class="d">${short(HIDDEN_D)}</span> Texans voted for ${D.last} in counties ${R.last} won. On this map, they're painted red.</p>
      <p><span class="r">${short(HIDDEN_R)}</span> voted for ${R.last} in counties ${D.last} won. They're painted blue.</p>
      <p>That's <b class="hl">${pct(HIDDEN_D + HIDDEN_R, TOT)}</b> of everyone who voted, ${short(HIDDEN_D + HIDDEN_R)} people, shown as the
      opposite of how they voted.</p>` },

  { fly: 2, hold: 14, mix: 7, fill: 0, dots: 'county', view: () => stateView(), html: () => `
      <div class="kicker">Count people instead</div>
      <h2>One dot for each voter</h2>
      <p>Same race, same counties, same numbers: <b class="hl">${fmt(TOT)}</b> dots, one per voter, <span class="d">blue</span> for
      ${D.last}, <span class="r">red</span> for ${R.last}, <span class="o">gray</span> for everyone else.</p>
      <p>For now, each county's voters are scattered evenly across the county, mixed in its own proportions. That's all the
      flat map knew: a total and a split for each county. Only this time, every voter gets the same amount of ink.</p>` },

  { step: 4, fly: 3, hold: 15, fill: 0, dots: 'county', focus: SPARSE, view: () => boxView(FAR_WEST, 0.3, -0.1, 1.15),
    labels: [label(BREWSTER, `${fmt(BREWSTER.total)} voters`)], html: () => `
      ${myth(4)}
      <p>Outlined: the <b>${SPARSE.length}</b> counties with fewer than ${SPARSE_PER} voters per square mile.</p>
      <div class="vs"><div><b>${pct(sum(SPARSE, c => c.landSqMi), LAND)}</b>of the state's land</div>
      <div><b>${pct(sum(SPARSE, c => c.total), TOT, 1)}</b>of its voters</div></div>
      <p>Much of the flat map's red is out here, where the dots barely cover the ground. ${BREWSTER.name} County, larger than
      Connecticut, cast ${fmt(BREWSTER.total)} votes.</p>` },

  { step: 5, fly: 3, hold: 13, fill: 0, dots: 'county', focus: [HARRIS], view: () => boxView([HARRIS], 0.0001, 0, 1.15), html: () => `
      ${myth(5)}
      <h2>${HARRIS.name} County, by county</h2>
      <div class="big">${fmt(HARRIS.total)} voters<small>${splitTxt(HARRIS)}</small></div>
      <p>Placed the flat map's way, every corner of the county gets the same mix: an even purple haze, over neighborhoods, the
      Ship Channel, the airports and the lakes alike.</p>` },

  { step: 5, fly: 3, hold: 13, mix: 4, fill: 0, dots: 'precinct', focus: [HARRIS], dot: 0.012, view: () => milesView(midHarris(), 24), html: () => `
      <div class="kicker">Refine: by precinct</div>
      <h2>${fmt(HARRIS.precincts || 0)} precincts</h2>
      <p>Now each party's ${HARRIS.name} County votes are shared among its precincts by how each one voted in 2024, and spread
      evenly over each precinct.</p>
      <p>The haze splits apart. The county's ${pct(HARRIS.dem, HARRIS.total)} blue was never one color: it's
      bluer neighborhoods next to redder ones.</p>` },

  { step: 5, fly: 3, hold: 13, mix: 4, fill: 0, dots: 'block', focus: [HARRIS], dot: 0.022, view: () => milesView(midHarris(), 10), html: () => `
      <div class="kicker">Refine: by census block</div>
      <h2>Where people live</h2>
      <p>Inside each precinct, voters now go where the 2020 Census counted adults, block by block, and stay off land where it
      counted no one.</p>
      <p>Parks, rail yards, the bayous and the freeways open up. The dots follow the streets.</p>` },

  { step: 5, fly: 3, hold: 12, fill: 0, dots: 'block', focus: [HARRIS], dot: gapMiles(HARRIS) / 3,
    view: () => milesView(HARRIS.hot, closeMiles(HARRIS)), html: v => `
      <div class="kicker">Up close</div>
      <h2>Every single voter</h2>
      <p>This view is ${viewMiles(v) >= 1 ? `${viewMiles(v).toFixed(1)} miles` : `${fmt(Math.round(viewMiles(v) * 1760 / 10) * 10)} yards`}
      tall, in ${HARRIS.name} County's most crowded spot. Each dot is one person who voted.</p>
      <p>On the flat map, this whole neighborhood, and everyone in the county around it, is one flat patch of blue.</p>
      <p class="note">Spots and colors are estimated: ballots are secret.</p>` },

  { step: 5, fly: 4, hold: 11, mix: 3, fill: 0, dots: 'county', focus: [RED_CITY], view: () => boxView([RED_CITY], 0.0001, 0, 1.2),
    html: () => `
      <div class="kicker">The other way round</div>
      <h2>${RED_CITY.name} County, by county</h2>
      <div class="big">${fmt(RED_CITY.total)} voters<small>${splitTxt(RED_CITY)}</small></div>
      <p>Solid red on the flat map. Spread evenly, a pinkish haze. But <span class="d">${fmt(RED_CITY.dem)}</span> people here voted
      for ${D.last}.</p>` },

  { step: 5, fly: 3, hold: 12, mix: 4, fill: 0, dots: 'block', focus: [RED_CITY], dot: 0.022, view: () => milesView(RED_CITY.hot, 12),
    html: () => `
      <div class="kicker">${RED_CITY.name} County · by census block</div>
      <h2>Not one color either</h2>
      <p>Placed by precinct and block, ${RED_CITY.name}'s ${D.last} voters gather in parts of the city, and ${R.last}'s fill the
      rest of it and the farms around it.</p>
      <p>A red county is a place where one side got more votes, not a place where everyone voted one way.</p>
      <p class="note">Spots and colors are estimated.</p>` },

  { fly: 8, hold: 15, fill: 0, dots: 'block', view: () => stateView(), html: v => {
      const px = (H / (2 * v.d * TAN) * UPM) ** 2; // screen pixels per square mile, from this high up
      return `
      <div class="kicker">One last catch</div>
      <h2>Even dots mislead from far away</h2>
      <p>From this high up, about <b>${fmt(Math.round(HARRIS.density / px))}</b> ${HARRIS.name} County voters share each pixel, and a
      pixel can only show one dot. Out west, a voter can have a pixel or more to themselves.</p>
      <p>So the crowded, bluer cities shrink to small bright points, and the thinly spread, redder countryside covers more of the
      screen. It's the flat map's mistake again, in a smaller dose. That's why the dot view is made for zooming in.</p>`; } },

  { fly: 0, hold: Infinity, fill: 0, dots: 'block', view: () => stateView(), html: () => `
      <div class="kicker">Same election, two maps</div>
      <div class="vs"><div><b>${flatArea}</b>of the flat map is red</div><div><b>${pct(D.votes, TOT, 1)}</b>of the voters chose ${D.last}</div></div>
      <ol class="recap">${MISREADINGS.map(m => `<li>${m}? No.</li>`).join('')}</ol>
      <p>The flat map answers “who won each piece of land?” The dots answer “where are the voters, and how did they vote?”</p>
      <div class="links"><a href="#" id="again">↺ Watch again</a><a href="voters.html">Explore the dot view →</a>
      <a href="why.html">Same election, three maps →</a></div>
      <p class="note">Results: ${res.meta.resultsSource}. Dots are placed by 2024 precinct votes (Texas Legislative Council) and 2020
      census blocks (U.S. Census Bureau). <a href="sources.html#texas">Sources</a></p>` },
];
const REDUCED = matchMedia('(prefers-reduced-motion: reduce)').matches && !RECORD;
for (const s of scenes) { s.dot ??= DOT_FAR; s.labels ??= []; s.focus ??= []; }

// the list of misreadings, down the right side
$('steps').innerHTML = MISREADINGS.map((m, i) => `<li><b>${i + 1}</b><span>${m}</span></li>`).join('');

// ---------- camera: van Wijk and Nuij's smooth zoom-and-pan path, as in voters.js ----------
const smooth = t => t * t * (3 - 2 * t);
const ease = t => t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
const clamp01 = x => Math.min(1, Math.max(0, x));
const RHO = 1.7, SPEED = 0.4;
const viewW = d => 2 * d * TAN * Math.min(area.w, area.h) / H;
const viewD = w => w * H / (2 * TAN * Math.min(area.w, area.h));
function zoomPath(a, b) {
  const w0 = viewW(a.d), w1 = viewW(b.d), dx = b.x - a.x, dy = b.y - a.y, u1 = Math.hypot(dx, dy);
  if (u1 < 1e-4 * Math.min(w0, w1)) {
    const S = Math.abs(Math.log(w1 / w0)) / RHO;
    return { S, dx, dy, u1, at: s => ({ u: 0, w: w0 * (w1 / w0) ** (S ? s / S : 1) }) };
  }
  const r2 = RHO * RHO, r4 = r2 * r2;
  const b0 = (w1 * w1 - w0 * w0 + r4 * u1 * u1) / (2 * w0 * r2 * u1);
  const b1 = (w1 * w1 - w0 * w0 - r4 * u1 * u1) / (2 * w1 * r2 * u1);
  const r0 = -Math.asinh(b0), r1 = -Math.asinh(b1);
  return { S: (r1 - r0) / RHO, dx, dy, u1, at: s => ({
    u: w0 / r2 * (Math.cosh(r0) * Math.tanh(RHO * s + r0) - Math.sinh(r0)),
    w: w0 * Math.cosh(r0) / Math.cosh(RHO * s + r0) }) };
}
function flight(a, b, t) {
  const p = zoomPath(a, b), e = smooth(t), { u, w } = p.at(p.S * e), f = p.u1 ? u / p.u1 : 0;
  const dh = Math.atan2(Math.sin(b.heading - a.heading), Math.cos(b.heading - a.heading));
  return { x: a.x + p.dx * f, y: a.y + p.dy * f, d: viewD(w), tilt: a.tilt + (b.tilt - a.tilt) * e, heading: a.heading + dh * e };
}
function setView(v) {
  const target = new THREE.Vector3(v.x, 0, -v.y), s = Math.sin(v.tilt) * v.d;
  camera.position.set(target.x + s * Math.sin(v.heading), Math.cos(v.tilt) * v.d, target.z + s * Math.cos(v.heading));
  camera.near = v.d * 0.02; camera.far = v.d * 10 + 2000; camera.updateProjectionMatrix();
  camera.lookAt(target);
}
const NICE_FT = [50, 100, 200, 500, 1000, 2000], NICE_MI = [1, 2, 5, 10, 20, 50, 100, 200];
function scaleBar(v) {
  const pxPerMile = H / (2 * v.d * TAN) * UPM, max = 130;
  let text, px;
  for (const m of [...NICE_MI].reverse()) if (m * pxPerMile <= max) { text = `${m} mile${m > 1 ? 's' : ''}`; px = m * pxPerMile; break; }
  if (!text) for (const ft of [...NICE_FT].reverse()) if (ft / 5280 * pxPerMile <= max) { text = `${fmt(ft)} feet`; px = ft / 5280 * pxPerMile; break; }
  $('scalebar').querySelector('i').style.width = `${px}px`;
  $('scalebar').querySelector('span').textContent = text;
  $('scalebar').style.opacity = v.tilt < 0.35 ? 1 : 0;
}

// the timeline: each flight takes as long as its path needs at SPEED (a scene's `fly` is the shortest it may take)
const MAX_FLY = 8; // seconds: a longer path is flown faster
let END = 0;
function timeline() {
  let acc = 0;
  scenes.forEach((s, i) => {
    s.minFly ??= s.fly;
    const S = i ? zoomPath(scenes[i - 1].view(), s.view()).S : 0;
    s.fly = REDUCED ? Math.min(s.minFly, 0.6) : Math.max(s.minFly, Math.min(MAX_FLY, S / SPEED));
    s.start = acc; acc += s.fly + (isFinite(s.hold) ? s.hold : 0);
  });
  END = scenes.at(-1).start + scenes.at(-1).fly;
}

// ---------- labels pinned to counties ----------
const labelsEl = $('labels'), labelEls = new Map(), lv = new THREE.Vector3();
const cityLabels = await createCityLabels(labelsEl, P, { url: STATE.data.cities, avoid: () => [$('topnav'), $('scalebar'), $('caption'), $('player'), $('steps')] });
function placeLabels(s, alpha) {
  const show = new Map(s.labels);
  for (const [c, el] of labelEls) if (!show.has(c)) el.style.opacity = 0;
  const placed = [];
  for (const [c, html] of show) {
    let el = labelEls.get(c);
    if (!el) { el = document.createElement('div'); el.className = 'label'; labelsEl.appendChild(el); labelEls.set(c, el); }
    if (el.dataset.html !== html) { el.innerHTML = html; el.dataset.html = html; }
    lv.set(c.cx, c.cy, 0).applyMatrix4(mapGroup.matrixWorld).project(camera);
    const x = (lv.x + 1) / 2 * W, y = (1 - lv.y) / 2 * H, bw = el.offsetWidth, bh = el.offsetHeight;
    el.style.left = x + 'px'; el.style.top = y + 'px'; el.style.opacity = alpha;
    placed.push([x - bw / 2, y - bh * 1.2, x + bw / 2, y - bh * 0.2]);
  }
  return placed;
}
function legend(fill) {
  const items = fill > 0.5
    ? [[WIN_C.dem, `County won by ${D.last}`, 'sq'], [WIN_C.rep, `County won by ${R.last}`, 'sq']]
    : [[DOT_C.dem, `${D.last} (D)`], [DOT_C.rep, `${R.last} (R)`], [DOT_C.other, 'Other']];
  const html = items.map(([c, n, k]) => `<span><i class="${k || ''}" style="background:${c}"></i>${n}</span>`).join('');
  if ($('legend').dataset.html !== html) { $('legend').innerHTML = html; $('legend').dataset.html = html; }
}

// ---------- the clock ----------
let t = 0, playing = !RECORD, cur = -1, last = performance.now();
const sceneAt = time => { let i = 0; while (i + 1 < scenes.length && scenes[i + 1].start <= time) i++; return i; };
const busy = createBusy($('stage').parentElement);
function showScene(i) {
  const s = scenes[i];
  $('caption').innerHTML = s.html(s.view());
  $('again')?.addEventListener('click', e => { e.preventDefault(); jump(0); });
  focusLine.geometry.dispose();
  focusLine.geometry = s.focus.length ? lineGeo(s.focus.flatMap(c => c.edges)) : new THREE.BufferGeometry();
  const n = s.step || 0, steps = [...$('steps').children];
  steps.forEach((li, k) => { li.className = k + 1 === n ? 'now' : k + 1 < n || i === scenes.length - 1 ? 'done' : ''; });
  $('steps').style.opacity = i === 0 ? 0 : 1;
  cur = i;
}
function jump(time) { t = Math.max(0, Math.min(time, END)); playing = true; updateButton(); }
function updateButton() {
  const text = t >= END ? 'Watch again' : playing ? 'Pause' : 'Play';
  $('pause').textContent = text; $('pause').setAttribute('aria-label', text);
}
$('pause').onclick = () => { if (t >= END) jump(0); else { playing = !playing; updateButton(); } };
$('prev').onclick = () => { const i = sceneAt(t); jump(scenes[t - scenes[i].start < 1.5 && i > 0 ? i - 1 : i].start); };
$('next').onclick = () => { const i = sceneAt(t); if (i + 1 < scenes.length) jump(scenes[i + 1].start); };
addEventListener('keydown', e => {
  if (RECORD) return;
  if (e.key === ' ') { e.preventDefault(); $('pause').click(); }
  if (e.key === 'ArrowRight') $('next').click();
  if (e.key === 'ArrowLeft') $('prev').click();
});

// Everything on screen at time t. Returns false while the dots it needs are still being placed.
const lerpLog = (a, b, w) => Math.exp(Math.log(a) + (Math.log(b) - Math.log(a)) * w);
function draw(time) {
  const i = sceneAt(time), s = scenes[i], prev = scenes[Math.max(0, i - 1)], local = time - s.start;
  if (i !== cur) showScene(i);
  const k = s.fly ? clamp01(local / s.fly) : 1;
  const v = k < 1 ? flight(prev.view(), s.view(), k) : s.view();
  const mix = i === 0 ? 1 : smooth(clamp01(local / (s.mix ?? Math.max(s.fly, 1.5))));
  // the flat map, and the county lines over it
  const fill = prev.fill + (s.fill - prev.fill) * mix;
  fillMat.opacity = fill; fillMesh.visible = fill > 0.002;
  borderMat.color.set(fill > 0.5 ? 0x0e1116 : 0xffffff); borderMat.opacity = fill > 0.5 ? 0.35 : 0.13;
  // the dots: the last scene's set dissolving into this one's
  let waiting = false;
  for (const name of SETS) {
    const w = (s.dots === name ? mix : 0) + (prev.dots === name && i > 0 ? 1 - mix : 0);
    const dots = sets[name];
    if (w > 0 && !ready[name]) waiting = true;
    dots.uniforms.uReveal.value = Math.min(1, w);
    dots.group.visible = w > 0.001 && !!ready[name];
    dots.uniforms.uWorld.value = lerpLog(prev.dot, s.dot, ease(k)) * UPM;
    dots.uniforms.uMinSize.value = renderer.getPixelRatio();
  }
  focusMat.opacity = clamp01(local / 0.4) * 0.9;
  // the caption: in over the first half second of its scene, out over the last 0.4 seconds
  const out = isFinite(s.hold) && i + 1 < scenes.length ? clamp01((scenes[i + 1].start - time) / 0.4) : 1;
  $('caption').style.opacity = Math.min(i === 0 ? 1 : clamp01(local / 0.5), out);
  legend(fill);
  setView(v); scaleBar(v);
  for (const name of SETS) if (sets[name].group.visible) sets[name].showVisible(camera);
  renderer.render(scene, camera);
  cityLabels.update(camera, mapGroup, W, H, fill > 0.5 ? 0.85 : 1, placeLabels(s, clamp01((local - s.fly + 0.5) / 0.6)));
  $('fill').style.width = `${100 * time / END}%`;
  return !waiting;
}
function frame(now) {
  const dt = Math.min(0.25, (now - last) / 1000); last = now;
  if (RECORD) { if (document.body.classList.contains('ready')) draw(t); } // the moment last sought, kept on screen
  else {
    const ok = draw(t);
    if (ok) busy.hide('dots'); else busy.show('dots', `Placing ${fmt(TOT)} voters…`);
    if (playing && ok && t < END) { t = Math.min(END, t + dt); if (t >= END) updateButton(); }
  }
  requestAnimationFrame(frame);
}

const fit = new ResizeObserver(resize);
fit.observe($('stage')); fit.observe($('topnav'));
resize();
timeline();
const startAt = +query.get('scene');
if (startAt >= 1 && startAt <= scenes.length) t = scenes[startAt - 1].start + scenes[startAt - 1].fly;
$('loading').remove();
updateButton();

// For recording: seek(seconds) draws that moment, once every set of dots is placed, and resolves when it's on screen.
// A recorder sets the window size first (say 1920 x 1080), then steps through 0 .. duration at its frame rate.
window.misread = {
  get duration() { return END; },
  scenes: () => scenes.map(s => ({ start: s.start, fly: s.fly, hold: s.hold })),
  ready: allPlaced,
  async seek(time) {
    await allPlaced;
    t = Math.max(0, Math.min(time, END)); playing = false; updateButton();
    draw(t);
    // (a hidden tab gets no animation frames: the drawing is done by now, so don't wait forever for them)
    await Promise.race([new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))), new Promise(r => setTimeout(r, 300))]);
    return t;
  },
};
if (RECORD) allPlaced.then(() => { draw(t); document.body.classList.add('ready'); });
last = performance.now();
requestAnimationFrame(frame);

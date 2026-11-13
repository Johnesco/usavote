// Dot view: a flat map of Texas with one dot for each person who voted in any race, for the reader to move around.
// It opens that way, with all the navigation in a bar across the top: the year and race, menus that go to a city, county or
// precinct, and the guided flight, the Texas Population Density Tour of the 2026 U.S. Senate race. That plays on its own,
// scene by scene (?tour=1 or ?scene=N open on it). After the whole state, the tour visits one place at a time, in an order that keeps the flights short: the metro from high up, then one county, then down to its most crowded
// spot until single voters stand apart. Houston, the border, Austin and San Antonio (ending in the most crowded neighborhood
// in Texas), then at that same zoom the emptiest county, El Paso, Lubbock and Dallas-Fort Worth.
import * as THREE from 'three';
import { geoConicEqualArea, geoCentroid } from 'd3-geo';
import { feature } from 'topojson-client';
import { createDots, countyTris, loadPrecincts, precinctUnits, DOT_C } from './dots.js';
import { createBusy } from './busy.js';
import { createSiteNav } from './sitenav.js';
import { STATE } from './state.js';
import { createCityLabels } from './cities.js';
import { createPlaceMenus, describePlace } from './places.js';
import { viewBarGroups } from './viewbar.js';
import { createPanelToggle, panelParam, flightsHtml, FRAMED, compareHref, followCamera } from './panel.js';
import { sourceItems } from './sourcelist.js';

const GEO_URL = 'https://cdn.jsdelivr.net/npm/us-atlas@3.0.1/counties-10m.json';
const $ = id => document.getElementById(id);
// the way home and to the other states, first in the bar
document.querySelector('.nav-row').prepend(createSiteNav('dots'));
// the control bar along the bottom, the same as the bar view's (viewbar.js): Look, with Flat and 3D as links back to the bar view,
// By and Color, which are for Flat and 3D, then Whole state. It takes the place of the old Bar view link in the top bar.
{
  const bar = document.createElement('div');
  bar.className = 'controls viewbar';
  bar.innerHTML = viewBarGroups('dots');
  bar.append($('goHome'));
  document.querySelector('main.voters').append(bar);
  $('back')?.remove();
}
// the details panel down the left (panel.js), as in the bar view: the race and its count, the key, how the dots are placed, the
// guided flights and the sources. It takes the guided flights, the count and How? from the top strip, which keeps the menus.
{
  const panel = document.createElement('aside');
  panel.id = 'panel';
  panel.innerHTML = `<a class="back" href="./">← All states</a>
    <div class="kicker">${STATE.name} · one dot for each voter</div>
    <h1 id="panelTitle">${STATE.name} voters</h1>
    <p class="sub" id="raceCount">Loading…</p>
    <div class="legend-dots side" id="legendSide"></div>
    <h2>How the dots are placed</h2>
    ${[...document.querySelectorAll('.how p')].map(p => p.outerHTML).join('')}
    <div class="flights">${flightsHtml(true)}</div>
    <h2>Sources</h2>
    <div class="sources" id="sources"></div>
    <p class="sources">This page counts visits with <a href="https://www.goatcounter.com" target="_blank" rel="noopener">GoatCounter</a>, which uses no cookies and does not collect personal data.</p>`;
  document.body.prepend(panel);
  document.querySelectorAll('.how, .nav-flight, #raceCount:not(#panel *)').forEach(el => el.remove());
  document.querySelector('.nav-row').prepend(createPanelToggle(panel, () => saveUrl()));
}
const fmt = n => n.toLocaleString('en-US');
const short = n => n >= 1e6 ? (n / 1e6).toFixed(2) + 'M' : n >= 1e3 ? Math.round(n / 1e3) + 'K' : String(n);
const pct = (a, b) => (100 * a / b).toFixed(0) + '%';
const getJSON = url => fetch(url).then(r => { if (!r.ok) throw new Error(r.status); return r.json(); });

let res, us;
try { [res, us] = await Promise.all([getJSON(STATE.data.results), getJSON(GEO_URL)]); }
catch (e) { $('loading').textContent = 'Could not load the map data. Please reload the page.'; $('loading').classList.add('failed'); throw e; }
const showSources = histMeta => { $('sources').innerHTML = `<ol>${sourceItems(STATE, res.meta, histMeta).map(s => `<li>${s}</li>`).join('')}</ol>
  <p><a href="sources.html#${STATE.slug}">Sources and credits for every state →</a></p>`; };
showSources();

// ---------- data: the 2026 U.S. Senate race, by county (the tour is written around it) ----------
const race = res.races.find(r => r.id === (STATE.defaultRace ?? 'u-s-senate'));
const counties = res.counties.map((c, i) => {
  const [dem, rep, other, total] = race.counties[i];
  return { ...c, dem, rep, other, total, density: total / c.landSqMi };
});
const byFips = new Map(counties.map(c => [c.fips, c]));
const byName = name => counties.find(c => c.name === name);
const D = race.candidates.find(c => c.party === 'DEM'), R = race.candidates.find(c => c.party === 'REP');
const TOT = counties.reduce((s, c) => s + c.total, 0), OTH = TOT - D.votes - R.votes;
const byDensity = [...counties].sort((a, b) => a.density - b.density);
const EMPTY = byDensity[0], CROWDED = byDensity.at(-1);
const BIGGEST = [...counties].sort((a, b) => b.total - a.total)[0];

// ---------- map geometry (same projection as the other pages) ----------
const geo = feature(us, us.objects.counties);
const tx = { type: 'FeatureCollection', features: geo.features.filter(f => String(f.id).startsWith(STATE.fips)) };
const projection = geoConicEqualArea().parallels(STATE.parallels).rotate(STATE.rotate).fitExtent([[-500, -500], [500, 500]], tx);
const P = ([lon, lat]) => { const [x, y] = projection([lon, lat]); return new THREE.Vector2(x, -y); };
const ringPts = ring => { const pts = ring.map(P); pts.pop(); return pts; };
// map units per mile, from 0.1 degree of latitude (about 6.9 miles) in the middle of the state
const UPM = P(STATE.middle).distanceTo(P([STATE.middle[0], STATE.middle[1] + 0.1])) / 6.905;

const renderer = new THREE.WebGLRenderer({ antialias: false });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
$('stage').appendChild(renderer.domElement);
const scene = new THREE.Scene();
scene.background = new THREE.Color('#0e1116');
const FOV = 30, TAN = Math.tan(THREE.MathUtils.degToRad(FOV / 2));
const camera = new THREE.PerspectiveCamera(FOV, 1, 1, 10000);
const mapGroup = new THREE.Group();
mapGroup.rotation.x = -Math.PI / 2; // map x/y in the ground plane; map y becomes world -z (north)
scene.add(mapGroup);

const allEdges = [];
const ordered = []; // counties in the order the dots are placed
for (const f of tx.features) {
  const c = byFips.get(String(f.id)); if (!c) continue;
  const polys = f.geometry.type === 'Polygon' ? [f.geometry.coordinates] : f.geometry.coordinates;
  const shapes = polys.map(([outer, ...holes]) => {
    const s = new THREE.Shape(ringPts(outer));
    for (const h of holes) s.holes.push(new THREE.Path(ringPts(h)));
    return s;
  });
  c.tris = countyTris(shapes); // the county's outline, used if the precincts don't load
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
const lineGeo = pts => { const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(pts, 3)); return g; };
// faint county lines over the dots, and a bright white outline for the counties a scene is about, from the moment it starts
const borders = new THREE.LineSegments(lineGeo(allEdges),
  new THREE.LineBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.13, depthTest: false }));
borders.renderOrder = 1; mapGroup.add(borders);
const focusMat = new THREE.LineBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0, depthTest: false });
const focusLine = new THREE.LineSegments(new THREE.BufferGeometry(), focusMat);
focusLine.renderOrder = 2; mapGroup.add(focusLine);

const dots = createDots({ depthTest: false }); // one flat layer: no need for depth
dots.uniforms.uP.value = 0; dots.uniforms.uReveal.value = 0;
mapGroup.add(dots.group);

// Where to put each county's voters. The 2026 results are by county, so each party's county total is placed by precinct
// the way that party's voters were spread in the 2024 Senate race, then on census blocks by adults (dots.js). If that file
// fails to load, the dots are spread evenly over each county instead.
const HOT_R = 0.5; // miles: a county's "most crowded spot" is the most voters within this distance
$('loading').textContent = STATE.data.precinctShapes ? 'Loading precincts…' : 'Loading…';
let PC = null;
try { PC = await loadPrecincts(P, STATE.data.precincts, STATE.data.land); } catch (e) { console.error('Precincts did not load; dots spread evenly', e); }
if (PC) for (const c of ordered) {
  const pc = PC.byFips.get(c.fips); if (!pc) continue;
  c.units = precinctUnits(pc, c);
  const spot = PC.hot?.[c.fips]; if (!spot) continue;
  // voters per square mile within HOT_R of the spot, as the dots will be placed
  const h = P([spot[0], spot[1]]), r2 = (HOT_R * UPM) ** 2, u = c.units;
  let n = 0;
  for (let i = 0; i < u.length; i += 6) if ((u[i] - h.x) ** 2 + (u[i + 1] - h.y) ** 2 <= r2) n += u[i + 3] + u[i + 4] + u[i + 5];
  c.hot = { x: h.x, y: h.y, voters: n / (Math.PI * HOT_R ** 2) };
}
// the most crowded neighborhood in the state
const DENSE = [...ordered].sort((a, b) => b.hot.voters - a.hot.voters)[0];

// ---------- layout: the part of the screen not covered by the bar and the caption card ----------
const page = document.querySelector('.voters');
let explore = null;   // the camera while exploring
let needsDraw = true; // something changed that the camera can't show: see the end of frame()
// area: on the tour, beside or above its caption. free: while exploring, everything under the top bar.
let W = 1, H = 1, area = { w: 1, h: 1, ox: 0, oy: 0 }, free = { w: 1, h: 1, ox: 0, oy: 0 };
const off = { x: 0, y: 0 }; // the camera's current shift, easing between those two
function resize() {
  W = $('stage').clientWidth; H = $('stage').clientHeight;
  renderer.setSize(W, H);
  camera.aspect = W / H;
  const wide = W > 760, bar = $('topnav').offsetHeight;
  page.style.setProperty('--bar', `${bar}px`);
  // wide screens: the caption sits on the left, so the map is centered in what's to its right; narrow: above the caption
  area = wide ? { w: W - 440, h: H - 90 - bar, ox: -220, oy: -bar / 2 } : { w: W, h: H * 0.55, oy: H * 0.15, ox: 0 };
  free = { w: W - 24, h: H - bar - 24, ox: 0, oy: -bar / 2 };
  if (explore?.home) Object.assign(explore, homeView());
  camera.updateProjectionMatrix();
  dots.uniforms.uViewH.value = H * renderer.getPixelRatio();
  needsDraw = true;
}
// A view: the camera looks at map point (x, y) from distance d, tilted `tilt` radians from straight down, from the
// direction `heading` (0 = from the south, looking north).
// camera distance that shows halfW x halfH map units (looking straight down) inside the free area
const fitDist = (halfW, halfH) => Math.max(halfW * H / (TAN * area.w), halfH * H / (TAN * area.h));
const stateView = (tilt = 0.0001, heading = 0) => ({ x: 0, y: 0, d: fitDist(520, 520), tilt, heading });
const boxView = (cs, tilt = 0.0001, heading = 0, pad = 1.3) => {
  const x0 = Math.min(...cs.map(c => c.box.x0)), x1 = Math.max(...cs.map(c => c.box.x1));
  const y0 = Math.min(...cs.map(c => c.box.y0)), y1 = Math.max(...cs.map(c => c.box.y1));
  return { x: (x0 + x1) / 2, y: (y0 + y1) / 2, d: fitDist(pad * (x1 - x0) / 2, pad * (y1 - y0) / 2), tilt, heading };
};
const countyView = (c, tilt, heading, pad) => boxView([c], tilt, heading, pad);
// a view of `miles` (top to bottom of the free area) around a point, looking straight down
const milesView = (p, miles, tilt = 0.0001, heading = 0) => ({ x: p.x, y: p.y, d: (miles * UPM / 2) * H / (TAN * area.h), tilt, heading });
const viewMiles = v => 2 * v.d * TAN * area.h / H / UPM; // inverse: miles from top to bottom of the free area
const viewSqMi = v => { const m = viewMiles(v); return m * m * area.w / area.h; };
// Close-ups come down until single voters stand apart: the typical gap between voters at a county's most crowded spot
// (1 / sqrt(voters per square mile)) is drawn SEP_PX pixels wide, and each dot about a third of that gap across.
const SEP_PX = 16;
const gapMiles = c => 1 / Math.sqrt(Math.max(c.hot.voters, 1));
const closeMiles = c => Math.min(3, Math.max(0.15, area.h * gapMiles(c) / SEP_PX));
const closeView = (c, at = c) => milesView(at.hot, closeMiles(c));

// ---------- the scenes ----------
// Each scene flies `fly` seconds from where the last one ended, then holds `hold` seconds (drifting round by `drift`
// radians a second, if set). glide: fly straight, without zooming out on the way. dot: how wide a voter's dot is, in
// miles, so dots grow as the camera comes down (they're never drawn smaller than a pixel).
const ZOOM_MID = 5; // miles from top to bottom of the free area
const DOT_FAR = 0.005; // miles, for scenes without their own
const perSqMi = c => c.density >= 10 ? fmt(Math.round(c.density)) : c.density.toFixed(1);
const round2 = n => { if (n < 10) return Math.round(n); const p = 10 ** Math.max(0, Math.floor(Math.log10(n)) - 1); return Math.round(n / p) * p; };
const acresTxt = a => a >= 100 ? fmt(round2(a)) : a >= 10 ? Math.round(a) : a.toFixed(1);
const split = c => `${D.last} ${pct(c.dem, c.total)}, ${R.last} ${pct(c.rep, c.total)}`;
const tall = v => viewMiles(v) >= 1 ? `${viewMiles(v).toFixed(1)} miles` : `${fmt(round2(viewMiles(v) * 1760))} yards`;
const named = (...names) => names.map(byName).filter(Boolean);
const sumVoters = cs => cs.reduce((s, c) => s + c.total, 0);
const inView = (c, v) => round2(c.hot.voters * viewSqMi(v));
const HOUSTON = named('Harris', 'Fort Bend', 'Montgomery', 'Galveston', 'Brazoria');
const DFW = named('Dallas', 'Tarrant', 'Collin', 'Denton');
const I35 = named('Travis', 'Bexar', 'Williamson', 'Hays');
const BORDER = named('Hidalgo', 'Cameron', 'Webb');
const HARRIS = byName('Harris'), HIDALGO = byName('Hidalgo'), ELPASO = byName('El Paso'), LUBBOCK = byName('Lubbock');
// the I-35 visit's county: the one with the most crowded neighborhood in the state, if it's there
const MID35 = I35.includes(DENSE) ? DENSE : byName('Travis');

// ---- the three distances of a visit ----
// far: a metro from high up, a little tilted, drifting round; its counties labeled
const far = (cs, heading, html) => ({ fly: 3, hold: 8, drift: 0.006 * Math.sign(heading || 1), labels: cs,
  view: () => boxView(cs, 0.3, heading, 1.1), html });
// medium: one county, outlined
const county = (c, kicker, more = '') => ({ fly: 3, hold: 8, focus: c, view: () => countyView(c, 0.12), html: () => `
      <div class="kicker">${kicker}</div>
      <h2>${c.name} County</h2>
      <div class="big">${fmt(c.total)} voters<small>${perSqMi(c)} per square mile · ${split(c)}</small></div>${more}` });
// close: the county's most crowded spot, close enough that single voters stand apart
const close = (c, kicker) => ({ fly: 3, hold: 8, focus: c, dot: gapMiles(c) / 3, view: () => closeView(c), html: v => `
      <div class="kicker">${kicker} · up close</div>
      <h2>${c.name} County's most crowded spot</h2>
      <div class="big">About ${fmt(round2(c.hot.voters))} voters per square mile<small>this view is ${tall(v)} tall and holds about ${fmt(inView(c, v))}</small></div>
      <p>That's ${fmt(round2(c.hot.voters / c.density))} times the county's average. Each dot stands for one voter.</p>
      <p class="note">Spots and colors are estimated.</p>` });
const lineup = cs => cs.map(c => `${c.name}: ${short(c.total)}, ${split(c)}`).join('; ');

// Only a state with a written tour gets one; the others stay on the whole state, for exploring (STATE.tour).
const scenes = !STATE.tour ? [{ fly: 0, hold: Infinity, view: () => stateView(), html: () => '' }] : [
  { fly: 0, hold: 10, reveal: 7, view: () => stateView(), html: () => `
      <div class="kicker">Texas · U.S. Senate · Nov. 3, 2026</div>
      <h1>${TOUR}</h1>
      <p><b class="hl">${fmt(TOT)}</b> Texans voted for U.S. Senate. Each of them is about to become one dot on this map.</p>` },
  { fly: 3, hold: 12, view: () => stateView(0.2), html: () => `
      <h2>One dot, one voter</h2>
      <p>The dots are voters, not residents. More than 31 million people live in Texas, but children, people who aren't citizens,
      and adults who didn't vote aren't on this map. Only the ${fmt(TOT)} who cast a ballot for U.S. Senate are.</p>
      ${PC ? `<p class="note">The 2026 results are by county; precinct results aren't out yet. So each county's voters for each
      party are placed by precinct the way that party's voters were spread in the 2024 Senate race, then on census blocks by
      how many adults live there, scattered at random around each block and kept off land where the Census counted no one, like
      lakes and airports. Each county still adds up exactly to its 2026 result.</p>`
      : `<p class="note">The results say how many people voted in each county, not where they live. So each county's voters are
      placed where its adults live, by census block group, at random within each one. The colors are mixed across the whole
      county: a dot's color shows how its county voted, not its neighborhood.</p>`}` },
  { fly: 2.5, hold: 10, view: () => stateView(0.25, 0.1), html: () => `
      <h2>Blue, red and gray</h2>
      <p><span class="d">Blue</span>: voted for ${D.name} (D), ${fmt(D.votes)}.<br><span class="r">Red</span>: ${R.name} (R), ${fmt(R.votes)}.<br>
      <span class="o">Gray</span>: everyone else, ${fmt(OTH)}.</p>
      <p>From up here, the dots pile on top of each other: in the cities, hundreds of thousands of voters share a few pixels.
      Out west, there's mostly black. Let's visit a few places, one at a time.</p>` },

  // ---- Houston ----
  far(HOUSTON, -0.15, () => `
      <div class="kicker">Houston</div>
      <h2>${fmt(sumVoters(HOUSTON))} voters</h2>
      <p>${HOUSTON.map(c => c.name).join(', ')}: ${pct(sumVoters(HOUSTON), TOT)} of the state's vote in five counties.
      ${PC ? 'The blue core and the redder suburbs follow how each neighborhood voted in 2024.' : ''}</p>`),
  county(HARRIS, HARRIS === BIGGEST ? 'Houston · the most voters' : 'Houston', `
      <p>${pct(HARRIS.total, TOT)} of every Senate vote in Texas. From this high up, they blur together. The empty patches are where
      few people live: the Ship Channel, parks, the airports.</p>`),
  close(HARRIS, 'Houston'),

  // ---- the border ----
  far(BORDER, 0.1, () => `
      <div class="kicker">The border</div>
      <h2>${fmt(sumVoters(BORDER))} voters</h2>
      <p>${lineup(BORDER)}. Between the cities, the map is nearly empty.</p>`),
  county(HIDALGO, 'The Rio Grande Valley'),
  close(HIDALGO, 'The Rio Grande Valley'),

  // ---- Austin and San Antonio, down to the most crowded neighborhood in Texas ----
  far(I35, -0.1, () => `
      <div class="kicker">Down I-35: Austin and San Antonio</div>
      <h2>${fmt(sumVoters(I35))} voters</h2>
      <p>${lineup(I35)}.</p>`),
  county(MID35, 'Austin and San Antonio', MID35 === DENSE ? `
      <p>Somewhere in here is the most crowded neighborhood in Texas. Let's go down into it, until the blur breaks apart.</p>` : ''),
  { fly: 3, hold: 6, focus: DENSE, view: () => milesView(DENSE.hot, ZOOM_MID), html: v => `
      <h2>Closer…</h2>
      <p>This view is about ${Math.round(viewMiles(v))} miles from top to bottom, around the most crowded part of ${DENSE.name} County.</p>` },
  { fly: 3, hold: 11, focus: DENSE, dot: gapMiles(DENSE) / 3, view: () => closeView(DENSE), html: v => `
      <h2>Every single voter</h2>
      <p>Now each dot stands for one person: about <b class="hl">${fmt(inView(DENSE, v))}</b> voters in a patch of land ${tall(v)} tall,
      in the most crowded neighborhood in Texas (${DENSE.name} County).</p>
      <p>Across the whole county, each ${DENSE.name} County voter has about ${acresTxt(640 / DENSE.density)} of an acre to themselves.</p>
      <p class="note">Spots and colors are estimated.</p>` },

  // ---- from the most crowded to the emptiest, at the same zoom ----
  { fly: 3, hold: 11, size: 4, focus: EMPTY, dot: gapMiles(DENSE) / 3, view: () => closeView(DENSE, EMPTY), html: v => {
      const n = EMPTY.density * viewSqMi(v);
      return `
      <div class="kicker">Same zoom, ${EMPTY.name} County</div>
      <h2>Nobody here</h2>
      <p>This patch of ${EMPTY.name} County, the emptiest in Texas, is the same size as the last one, which held about
      ${fmt(inView(DENSE, v))} voters. On average, a patch this size here holds ${n < 0.1 ? 'less than a tenth' : n.toFixed(1)} of one.</p>
      <div class="vs"><div><b>${fmt(round2(DENSE.hot.voters))}</b>voters per square mile in that ${DENSE.name} County neighborhood</div>
      <div><b>1 per ${Math.round(1 / EMPTY.density)}</b>square miles in ${EMPTY.name} County</div></div>`;
    } },
  { fly: 3, hold: 10, size: 4, focus: EMPTY, view: () => countyView(EMPTY, 0.12), html: () => `
      <div class="kicker">The emptiest county</div>
      <h2>${EMPTY.name} County</h2>
      <div class="big">${fmt(EMPTY.total)} voters<small>on ${fmt(Math.round(EMPTY.landSqMi))} square miles of land</small></div>
      <p>Pull back, and that's the whole county: one voter for every ${Math.round(1 / EMPTY.density)} square miles. Each dot you can
      see stands for one person who voted (drawn larger, so you can find them).</p>
      <p class="note">Spots and colors are estimated.</p>` },

  // ---- out west ----
  county(ELPASO, 'Out west', `
      <p>The flight here crossed West Texas, where whole counties cast a few hundred or a few thousand votes.</p>`),
  close(ELPASO, 'El Paso'),
  county(LUBBOCK, 'The South Plains'),
  close(LUBBOCK, 'Lubbock'),

  // ---- Dallas-Fort Worth, and the most crowded county ----
  far(DFW, 0.15, () => `
      <div class="kicker">Dallas–Fort Worth</div>
      <h2>${fmt(sumVoters(DFW))} voters</h2>
      <p>${lineup(DFW)}.</p>`),
  county(CROWDED, 'Dallas–Fort Worth · the most crowded county', `
      <p>About ${fmt(round2(CROWDED.density / EMPTY.density))} times as crowded as ${EMPTY.name} County.</p>`),
  close(CROWDED, 'Dallas–Fort Worth'),

  { fly: 9, hold: Infinity, view: () => stateView(), html: () => `
      <h2>Same state, same election, one vote each</h2>
      <p>${EMPTY.name} County's ${fmt(EMPTY.total)} voters and ${CROWDED.name} County's ${fmt(CROWDED.total)} each cast a vote that counted the
      same. Statewide, ${D.last} won by <b class="hl">${fmt(D.votes - R.votes)}</b> votes, ${(100 * D.votes / TOT).toFixed(1)}% to ${(100 * R.votes / TOT).toFixed(1)}%.</p>
      <div class="links"><a href="#" id="again">↺ Watch again</a><a href="#" id="toMap">Explore the dot view →</a><a href="texas.html?race=u-s-senate">Bar view →</a></div>` },
];
const TOUR = `${STATE.name} Population Density Tour`;
const REDUCED = matchMedia('(prefers-reduced-motion: reduce)').matches;
for (const s of scenes) { s.dot ??= DOT_FAR; if (REDUCED) s.drift = 0; }
// where a scene's camera ends up, after its drift
const endView = s => { const v = s.view(); return s.drift && isFinite(s.hold) ? { ...v, heading: v.heading + s.drift * s.hold } : v; };
// The timeline: each flight takes as long as its path needs at SPEED (a scene's `fly` is only the shortest it may take).
// Views depend on the screen's shape, so this runs once the layout is known.
let END = 0;
function timeline() {
  let acc = 0;
  scenes.forEach((s, i) => {
    s.minFly ??= s.fly;
    const S = i ? zoomPath(endView(scenes[i - 1]), s.view()).S : 0;
    s.fly = REDUCED ? Math.min(s.minFly, 0.6) : Math.max(s.minFly, S / SPEED);
    s.start = acc; acc += s.fly + (isFinite(s.hold) ? s.hold : 0);
  });
  END = scenes.at(-1).start + scenes.at(-1).fly;
}

// ---------- camera ----------
const ease = t => t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
const smooth = t => t * t * (3 - 2 * t);
const clamp01 = x => Math.min(1, Math.max(0, x));
// Flights follow van Wijk and Nuij's smooth zoom-and-pan path ("Smooth and efficient zooming and panning", 2003): rather
// than sliding across the map up close, the camera zooms out, crosses while high, and zooms back in. The path's length S
// counts both panning (in screen widths) and zooming (in factors of e), and the flight moves along it at about SPEED a
// second, so neither the scrolling nor the zooming ever gets fast.
const RHO = 1.7;    // how much the path favors zooming out over panning (√2 is the textbook balance)
const SPEED = 0.4;  // path length a second, on average: zooming about 2x a second, or panning about a fifth of the screen
const viewW = d => 2 * d * TAN * Math.min(area.w, area.h) / H; // map units across the free area's shorter side
const viewD = w => w * H / (2 * TAN * Math.min(area.w, area.h));
function zoomPath(a, b) {
  const w0 = viewW(a.d), w1 = viewW(b.d), dx = b.x - a.x, dy = b.y - a.y, u1 = Math.hypot(dx, dy);
  if (u1 < 1e-4 * Math.min(w0, w1)) { // (nearly) straight in or out
    const S = Math.abs(Math.log(w1 / w0)) / RHO;
    return { S, dx, dy, u1, at: s => ({ u: 0, w: w0 * (w1 / w0) ** (S ? s / S : 1) }) };
  }
  const r2 = RHO * RHO, r4 = r2 * r2;
  const b0 = (w1 * w1 - w0 * w0 + r4 * u1 * u1) / (2 * w0 * r2 * u1);
  const b1 = (w1 * w1 - w0 * w0 - r4 * u1 * u1) / (2 * w1 * r2 * u1);
  const r0 = -Math.asinh(b0), r1 = -Math.asinh(b1); // ln(-b + sqrt(b² + 1)), without losing precision for large b
  return { S: (r1 - r0) / RHO, dx, dy, u1, at: s => ({
    u: w0 / r2 * (Math.cosh(r0) * Math.tanh(RHO * s + r0) - Math.sinh(r0)),
    w: w0 * Math.cosh(r0) / Math.cosh(RHO * s + r0) }) };
}
function flight(a, b, t) {
  const p = zoomPath(a, b), e = smooth(t), { u, w } = p.at(p.S * e), f = p.u1 ? u / p.u1 : 0;
  const dh = Math.atan2(Math.sin(b.heading - a.heading), Math.cos(b.heading - a.heading)); // shortest way round
  return { x: a.x + p.dx * f, y: a.y + p.dy * f, d: viewD(w), tilt: a.tilt + (b.tilt - a.tilt) * e, heading: a.heading + dh * e };
}
function setView(v) {
  const target = new THREE.Vector3(v.x, 0, -v.y);
  const s = Math.sin(v.tilt) * v.d;
  camera.position.set(target.x + s * Math.sin(v.heading), Math.cos(v.tilt) * v.d, target.z + s * Math.cos(v.heading));
  camera.near = v.d * 0.02; camera.far = v.d * 10 + 2000; camera.updateProjectionMatrix();
  camera.lookAt(target);
}
const NICE_FT = [50, 100, 200, 500, 1000, 2000], NICE_MI = [1, 2, 5, 10, 20, 50, 100, 200];
function scaleBar(v) {
  const pxPerMile = H / (2 * v.d * TAN) * UPM, max = 130;
  let label, px;
  for (const m of [...NICE_MI].reverse()) if (m * pxPerMile <= max) { label = `${m} mile${m > 1 ? 's' : ''}`; px = m * pxPerMile; break; }
  if (!label) for (const ft of [...NICE_FT].reverse()) if (ft / 5280 * pxPerMile <= max) { label = `${fmt(ft)} feet`; px = ft / 5280 * pxPerMile; break; }
  $('scalebar').querySelector('i').style.width = `${px}px`;
  $('scalebar').querySelector('span').textContent = label;
  $('scalebar').style.opacity = v.tilt < 0.35 ? 1 : 0; // only meaningful looking (nearly) straight down
}

// ---------- county labels (metro scenes), on the ground at each county's center ----------
const labelsEl = $('labels'), labelEls = new Map(), lv = new THREE.Vector3();
// town names for reference, more as the camera comes down; clear of the county labels and everything over the map
const cityLabels = await createCityLabels(labelsEl, P, { url: STATE.data.cities, avoid: () => [$('topnav'), $('scalebar'), $('caption'), $('player')] });
function labelFor(c) {
  if (!labelEls.has(c)) {
    const el = document.createElement('div'); el.className = 'label';
    el.innerHTML = `${c.name}<small>${short(c.total)} voters</small>`;
    labelsEl.appendChild(el); labelEls.set(c, el);
  }
  return labelEls.get(c);
}
function placeLabels(s, local) {
  const show = new Set(s.labels || []);
  for (const [c, el] of labelEls) if (!show.has(c)) el.style.opacity = 0;
  const placed = [];
  for (const c of [...show].sort((a, b) => b.total - a.total)) { // largest first; skip a label that would overlap one shown
    const el = labelFor(c);
    lv.set(c.cx, c.cy, 0).applyMatrix4(mapGroup.matrixWorld).project(camera);
    const x = (lv.x + 1) / 2 * W, y = (1 - lv.y) / 2 * H, bw = el.offsetWidth, bh = el.offsetHeight;
    const box = [x - bw / 2, y - bh * 1.2, x + bw / 2, y - bh * 0.2];
    const ok = lv.z < 1 && x > 0 && x < W && y > 0 && y < H && !placed.some(b => box[0] < b[2] && box[2] > b[0] && box[1] < b[3] && box[3] > b[1]);
    if (ok) placed.push(box);
    el.style.left = x + 'px'; el.style.top = y + 'px';
    el.style.opacity = ok ? clamp01((local - s.fly + 1) / 1) : 0;
  }
  return placed; // so the city names keep clear of them
}

// ---------- the clock ----------
let t = 0, playing = false, toured = false, cur = -1, last = performance.now();
const sceneAt = time => { let i = 0; while (i + 1 < scenes.length && scenes[i + 1].start <= time) i++; return i; };
function showCaption(i) {
  const s = scenes[i], cap = $('caption');
  cap.classList.add('fade');
  setTimeout(() => {
    cap.innerHTML = s.html(s.view());
    cap.classList.remove('fade');
    $('again')?.addEventListener('click', e => { e.preventDefault(); jump(0); });
    $('toMap')?.addEventListener('click', e => { e.preventDefault(); enterExplore(); });
  }, cur === -1 ? 0 : 350);
  focusLine.geometry.dispose();
  // the scene's county, or the counties it names
  const outlined = s.focus ? [s.focus] : s.labels || [];
  focusLine.geometry = outlined.length ? lineGeo(outlined.flatMap(c => c.edges)) : new THREE.BufferGeometry();
  needsDraw = true;
}
function jump(time) { leaveExplore(); resume = null; t = Math.max(0, Math.min(time, END)); playing = true; updateButton(); }
function updateButton() {
  const label = t >= END ? 'Watch again' : playing ? 'Pause' : 'Play';
  $('pause').textContent = label; $('pause').setAttribute('aria-label', label);
  // a tour left part way can be picked up again from the top bar
  const partWay = toured && t < END;
  if (!$('tourPlay')) return;
  $('tourName').textContent = partWay ? '▶ Back to the tour' : `▶ ${TOUR}`;
  $('tourRestart').hidden = !partWay;
}
$('pause').onclick = () => { if (t >= END) jump(0); else { playing = !playing; updateButton(); } };
$('prev').onclick = () => { const i = sceneAt(t); jump(scenes[t - scenes[i].start < 1.5 && i > 0 ? i - 1 : i].start); };
$('next').onclick = () => { const i = sceneAt(t); if (i + 1 < scenes.length) jump(scenes[i + 1].start); };
addEventListener('keydown', e => {
  if (e.target.matches?.('select, input, textarea')) return;
  if (explore) { // arrows move the map, + and - zoom, Esc goes back to a tour under way
    const move = { ArrowLeft: [90, 0], ArrowRight: [-90, 0], ArrowUp: [0, 90], ArrowDown: [0, -90] }[e.key];
    if (move) { e.preventDefault(); panBy(...move); }
    if (e.key === '+' || e.key === '=') zoomAt(...screenCenter(), 0.7);
    if (e.key === '-') zoomAt(...screenCenter(), 1.4);
    if (e.key === 'Escape' && toured) resumeShow();
    return;
  }
  if (e.key === ' ' && e.target === document.body) { e.preventDefault(); $('pause').click(); }
  if (e.key === 'ArrowRight') $('next').click();
  if (e.key === 'ArrowLeft') $('prev').click();
});

// ---------- explore: drag, scroll or pinch to move around the map yourself ----------
// The page opens this way. During the tour, any of these pauses it, and the bar's "Back to the tour" flies from wherever
// you are back into the scene you left.
const stage = renderer.domElement;
let resume = null;    // { from, k, dur }: the flight from the reader's view into the tour
let lastV = null;     // the view drawn last frame
function enterExplore() {
  if (explore || !lastV) return;
  explore = { ...lastV }; resume = null; playing = false; going = null;
  page.classList.add('exploring'); updateButton(); needsDraw = true;
}
function leaveExplore() { if (explore) { explore = null; page.classList.remove('exploring'); updateButton(); needsDraw = true; } }
// Fly from the reader's view into scene i of the tour. The tour is about the Senate race, so those dots come back first.
let starting = false;
async function playFrom(i) {
  if (!explore || starting) return;
  starting = true; $('race').disabled = $('year').disabled = $('per').disabled = true;
  if (shown !== SENATE || chosen !== SENATE || shownPer !== 1) { per = 1; $('per').value = 1; await showRace(SENATE); }
  starting = false; $('race').disabled = $('year').disabled = $('per').disabled = false;
  const s = scenes[i], from = explore;
  going = null;
  leaveExplore();
  t = Math.min(END, s.start + s.fly); // arrived, so the scene's hold plays out after the flight
  resume = { from, k: 0, dur: Math.max(1.5, zoomPath(from, s.view()).S / SPEED) };
  playing = true; toured = true; updateButton();
}
const resumeShow = () => playFrom(sceneAt(t));
$('explore').onclick = enterExplore;
// the screen point the camera looks at, and the map directions of screen right and screen up
const screenCenter = () => [W / 2 - off.x, H / 2 - off.y];
const axes = h => [[Math.cos(h), Math.sin(h)], [-Math.sin(h), Math.cos(h)]];
const unitsPerPx = v => 2 * v.d * TAN / H;
function panBy(dx, dy) { // move the map with the pointer, dx/dy in screen pixels
  const [r, f] = axes(explore.heading), u = unitsPerPx(explore);
  explore.home = false; going = null;
  explore.x -= (r[0] * dx - f[0] * dy) * u; explore.y -= (r[1] * dx - f[1] * dy) * u;
  explore.x = Math.max(-650, Math.min(650, explore.x)); explore.y = Math.max(-650, Math.min(650, explore.y));
}
function zoomAt(sx, sy, factor) { // zoom by factor (> 1 = out), keeping the map point under (sx, sy) in place
  const [cx, cy] = screenCenter(), [r, f] = axes(explore.heading), u = unitsPerPx(explore);
  const ox = (r[0] * (sx - cx) - f[0] * (sy - cy)) * u, oy = (r[1] * (sx - cx) - f[1] * (sy - cy)) * u;
  explore.home = false; going = null;
  const d = Math.max(milesView({ x: 0, y: 0 }, 0.08).d, Math.min(homeView().d * 1.6, explore.d * factor));
  const g = d / explore.d;
  explore.x += ox * (1 - g); explore.y += oy * (1 - g); explore.d = d;
}
const pointers = new Map();
const pointerXY = e => { const b = stage.getBoundingClientRect(); return [e.clientX - b.left, e.clientY - b.top]; };
stage.addEventListener('pointerdown', e => {
  enterExplore(); if (!explore) return;
  stage.setPointerCapture(e.pointerId); pointers.set(e.pointerId, pointerXY(e)); stage.classList.add('dragging');
});
stage.addEventListener('pointermove', e => {
  if (!explore || !pointers.has(e.pointerId)) return;
  const before = [...pointers.values()];
  pointers.set(e.pointerId, pointerXY(e));
  const after = [...pointers.values()];
  if (after.length === 1) panBy(after[0][0] - before[0][0], after[0][1] - before[0][1]);
  else if (after.length >= 2) { // pinch: zoom around the two fingers' midpoint, and follow it
    const mid = ps => [(ps[0][0] + ps[1][0]) / 2, (ps[0][1] + ps[1][1]) / 2];
    const dist = ps => Math.hypot(ps[0][0] - ps[1][0], ps[0][1] - ps[1][1]) || 1;
    const m0 = mid(before), m1 = mid(after);
    zoomAt(m0[0], m0[1], dist(before) / dist(after));
    panBy(m1[0] - m0[0], m1[1] - m0[1]);
  }
});
const lift = e => { pointers.delete(e.pointerId); if (!pointers.size) stage.classList.remove('dragging'); };
stage.addEventListener('pointerup', lift); stage.addEventListener('pointercancel', lift);
stage.addEventListener('wheel', e => {
  e.preventDefault(); enterExplore(); if (!explore) return;
  const [sx, sy] = pointerXY(e), px = e.deltaY * (e.deltaMode === 1 ? 33 : e.deltaMode === 2 ? 400 : 1);
  zoomAt(sx, sy, Math.exp(Math.max(-1, Math.min(1, px * 0.0018))));
}, { passive: false });
stage.addEventListener('dblclick', e => { enterExplore(); if (explore) { const [sx, sy] = pointerXY(e); zoomAt(sx, sy, 0.4); } });
// ---------- the top bar: which race the dots show ----------
const SENATE = { ...race, year: 2026 };
const RACES = res.races.map(r => r === race ? SENATE : { ...r, year: 2026 });
const rowOf = new Map(res.counties.map((c, i) => [c.fips, i]));
let chosen = SENATE; // the race asked for
let BAR_BY = '';     // the bar view's ?by=, for the way back to it
let BAR_ANGLE = [0, 0]; // and its tilt and heading if it was in 3D: this map settles flat and north up, so it hands them back unchanged
let BAR_COLOR = '';  // and its ?color=lead, if vote-lead color was on
// the Flat and 3D links back to the bar view: the same race, place and zoom, and Flat looking straight down or 3D at the angle it
// came with (or the bar view's usual tilt)
function barLinks(r = chosen) {
  const v = explore || lastV, base = `${STATE.results.href}?race=${r.id}${BAR_BY}${BAR_COLOR}${panelParam()}`;
  const at = angle => v ? `&at=${[v.x, v.y, v.d, ...angle].map(n => +n.toFixed(3)).join(',')}` : '';
  $('viewFlat').href = base + at([0, 0]);
  $('view3d').href = `${base}&look=3d` + at(BAR_ANGLE[0] > 0.05 ? BAR_ANGLE : [0.98, -0.22]);
}
// How many voters one dot stands for (?per=100). With one dot each, a far-off view is too crowded to read; fewer, bigger dots show
// the same pattern from afar. The tour's text is about single voters, so it always plays with one dot each.
const PERS = [1, 10, 100, 1000];
let per = 1, shownPer = 1;
// in the control bar under the map, before Whole state
$('goHome').insertAdjacentHTML('beforebegin', `<div class="vb-group"><label class="vb-label keep" for="per">1 dot =</label>
  <select id="per" title="How many voters each dot stands for">${PERS.map(n => `<option value="${n}">${fmt(n)} voter${n > 1 ? 's' : ''}</option>`).join('')}</select></div>`);
$('per').onchange = e => { per = +e.target.value; showRace(chosen); };
let shown = null;    // the race the dots show (they stay up until the next race's dots are ready)
function fillRaces() {
  const years = [...new Set(RACES.map(r => r.year))].sort((a, b) => b - a), inYear = RACES.filter(r => r.year === chosen.year);
  const option = r => `<option value="${r.id}">${r.label}</option>`, groups = [...new Set(inYear.map(r => r.group))];
  $('year').innerHTML = years.map(y => `<option value="${y}">${y}</option>`).join('');
  $('year').value = chosen.year;
  $('race').innerHTML = groups.length > 1
    ? groups.map(g => `<optgroup label="${g}">${inYear.filter(r => r.group === g).map(option).join('')}</optgroup>`).join('') : inYear.map(option).join('');
  $('race').value = chosen.id;
}
let historyLoad = null;
const loadHistory = () => historyLoad ??= !STATE.data.history ? Promise.resolve() : getJSON(STATE.data.history)
  .then(h => { RACES.push(...h.races); fillRaces(); showSources(h.meta); })
  .catch(e => console.error('Earlier years did not load', e));
const raceWithId = id => RACES.find(r => r.id === id) || RACES.find(r => r.year === 2026 && `2026-${r.id}` === id);
// this race's votes in each county, placed the same way as the Senate race's
function votersOf(r) {
  if (r === SENATE) return ordered;
  return ordered.map(c => {
    const [dem, rep, other, total] = r.counties[rowOf.get(c.fips)], v = { ...c, dem, rep, other, total };
    if (c.units) v.units = precinctUnits(PC.byFips.get(c.fips), v);
    return v;
  });
}
const busy = createBusy($('stage').parentElement);
let landed = false; // new dots are waiting for the next drawing, which sends them to the graphics card
async function showRace(r) {
  chosen = r; fillRaces();
  const placing = `Placing ${fmt(r.counties.reduce((s, row) => s + row[3], 0))} voters…`;
  if ($('loading')) $('loading').textContent = placing; else busy.show('race', placing);
  // (if another race is asked for before this one is ready, this one never finishes)
  const asked = per, { n } = await dots.place(votersOf(r), { per: asked, seed: 2026 + RACES.indexOf(r) });
  shown = r; shownPer = asked; needsDraw = landed = true;
  const [dem, rep, tot] = r.counties.reduce((s, row) => [s[0] + row[0], s[1] + row[1], s[2] + row[3]], [0, 0, 0]);
  const d = r.candidates.find(c => c.party === 'DEM'), e = r.candidates.find(c => c.party === 'REP');
  const dName = r.chamber ? 'Democrats' : d.last, rName = r.chamber ? 'Republicans' : e.last;
  $('raceCount').innerHTML = `<b>${fmt(tot)} voters</b>, ${asked === 1 ? 'one dot each' : `one dot per ${fmt(asked)} (${fmt(n)} dots)`} · ${dName} ${(100 * dem / tot).toFixed(1)}%, ${rName} ${(100 * rep / tot).toFixed(1)}%`;
  $('legend').innerHTML = [[DOT_C.dem, r.chamber ? dName : `${dName} (D)`], [DOT_C.rep, r.chamber ? rName : `${rName} (R)`], [DOT_C.other, 'Other']]
    .map(([c, n]) => `<span><i style="background:${c}"></i>${n}</span>`).join('');
  // back to the map, on the same race
  barLinks(r);
  if ($('tourPlay')) $('tourPlay').title = `A guided flight, about ${Math.round(END / 60)} minutes, on the 2026 U.S. Senate race${r === SENATE ? '' : ', so the dots change to that race'}`;
  renderPlace();
  $('panelTitle').textContent = `${r.year} ${r.label}`;
  $('legendSide').innerHTML = $('legend').innerHTML;
  saveUrl();
}
// what's on screen, in the address (only once the reader is exploring: a link's own address stays as it opened)
function saveUrl() {
  if (explore) try { history.replaceState(null, '', `?race=${chosen.id}${shownPer > 1 ? `&per=${shownPer}` : ''}${panelParam()}`); } catch {}
}
$('race').onchange = e => { const r = raceWithId(e.target.value); if (r) showRace(r); };
// a new year keeps the same office if that year had it, otherwise opens its first race
$('year').onchange = e => {
  const inYear = RACES.filter(r => r.year === +e.target.value);
  showRace(inYear.find(r => r.label === chosen.label) || inYear[0]);
};
if ($('tourPlay')) $('tourPlay').onclick = () => playFrom(toured && t < END ? sceneAt(t) : 0);
if ($('tourRestart')) $('tourRestart').onclick = () => playFrom(0);

// ---------- go to a city, county or precinct ----------
// A flight here is quicker than the tour's: the reader asked for this place, and is waiting for it.
let going = null;  // { from, to, k, dur }
let place = null;  // what the menus last chose (places.js)
const placeMat = new THREE.LineBasicMaterial({ color: 0xffffff, depthTest: false });
const placeLine = new THREE.LineSegments(new THREE.BufferGeometry(), placeMat);
placeLine.renderOrder = 2; mapGroup.add(placeLine);
function goTo(view) {
  if (!explore) enterExplore();
  if (!explore) return;
  explore.home = false;
  const dur = REDUCED ? 0.01 : Math.min(4, Math.max(1.2, zoomPath(explore, view).S));
  going = { from: { ...explore }, to: view, k: 0, dur };
}
const mapView = (x, y, halfW, halfH) => ({ x, y, d: Math.max(halfW * H / (TAN * free.w), halfH * H / (TAN * free.h)), tilt: 0.0001, heading: 0 });
function homeView() { return { ...mapView(0, 0, 520, 520), home: true }; }
// the line under the menus: facts about the place, for the race on screen where we have them by place
function renderPlace() {
  $('placeInfo').innerHTML = describePlace(place, chosen, c => {
    const [dem, rep, , tot] = chosen.counties[rowOf.get(c.fips)];
    return [dem, rep, tot];
  });
}
function outline(edges) {
  placeLine.geometry.dispose();
  placeLine.geometry = edges ? lineGeo(edges) : new THREE.BufferGeometry();
  needsDraw = true;
}
const menus = createPlaceMenus({ counties: ordered, P, upm: UPM, cityUrl: STATE.data.cities,
  getVtds: !STATE.data.precinctShapes ? null : c => PC?.byFips.get(c.fips)?.vtds || [],
  onChoose: p => {
    place = p; renderPlace();
    outline(p?.c ? [...p.c.edges, ...(p.boxEdges || [])] : null);
    if (p) goTo(mapView(p.view.x, p.view.y, p.view.halfW, p.view.halfH));
  } });
$('goHome').onclick = () => {
  menus.clear(); outline(null); place = null; renderPlace();
  goTo(homeView());
};

// while exploring, dots grow as you come down: about 4 pixels across from half a mile up, down to a single pixel by 8 miles
const exploreDot = v => {
  const m = viewMiles(v), px = 4 * clamp01((Math.log(8) - Math.log(m)) / Math.log(16));
  return Math.max(1e-5, px * m / area.h);
};

// what the picture was last drawn from, so an unchanged picture isn't drawn again
let drawn = null;
const sameView = (a, b, eps) => !!b && a.every((x, i) => Math.abs(x - b[i]) <= eps[i]);
function frame(now) {
  const dt = Math.min(0.25, (now - last) / 1000); last = now;
  if (playing && !resume && t < END) { t = Math.min(END, t + dt); if (t >= END) updateButton(); }
  const i = sceneAt(t), s = scenes[i], local = t - s.start;
  if (i !== cur) { showCaption(i); cur = i; }
  const prev = scenes[Math.max(0, i - 1)];
  const k = s.fly ? clamp01(local / s.fly) : 1;
  let v = k < 1 ? flight(endView(prev), s.view(), k) : s.view();
  if (k >= 1 && s.drift) v = { ...v, heading: v.heading + s.drift * Math.min(local - s.fly, isFinite(s.hold) ? s.hold : 0) };
  // dot size in map units, changing smoothly (on a log scale) from the last scene's to this one's
  const e = ease(k), lerpLog = (a, b, w) => Math.exp(Math.log(a) + (Math.log(b) - Math.log(a)) * w);
  let dot = lerpLog(prev.dot, s.dot, e);
  if (going) { // a flight to the place the menus chose
    going.k = Math.min(1, going.k + dt / going.dur);
    const home = going.to.home;
    Object.assign(explore, flight(going.from, going.to, going.k));
    if (going.k >= 1) { explore.home = !!home; going = null; }
  }
  // the camera eases between the tour's framing and the explorer's
  const aim = explore ? free : area, ease1 = REDUCED ? 1 : Math.min(1, dt * 4);
  off.x += (aim.ox - off.x) * ease1; off.y += (aim.oy - off.y) * ease1;
  camera.setViewOffset(W, H, off.x, off.y, W, H);
  placeLine.visible = !!explore;
  if (explore) { // the reader's own view, leveling out to look straight down
    explore.tilt += (0.0001 - explore.tilt) * Math.min(1, dt * 3);
    explore.heading += -explore.heading * Math.min(1, dt * 3); // north up again, so the arrow keys and the drag feel right
    v = explore; dot = exploreDot(v) * Math.sqrt(shownPer); // a dot for more voters is wider, as their land would be
  } else if (resume) { // flying back into the show
    resume.k = Math.min(1, resume.k + dt / resume.dur);
    v = flight(resume.from, v, resume.k);
    dot = lerpLog(exploreDot(resume.from), s.dot, ease(resume.k));
    if (resume.k >= 1) resume = null;
  }
  lastV = v;
  setView(v); scaleBar(v);
  dots.uniforms.uWorld.value = dot * UPM;
  // a scene's `size` enlarges the dots of its county only, so a few voters can be found without slowing the whole map
  const dpr = renderer.getPixelRatio();
  dots.uniforms.uMinSize.value = dpr * (1 + Math.log10(shownPer)); // 1, 2, 3 or 4 pixels: fewer dots, each easier to see
  dots.uniforms.uFocus.value = s.size && s.focus && !explore ? ordered.indexOf(s.focus) : -1;
  dots.uniforms.uFocusSize.value = dpr * (1 + ((s.size || 1) - 1) * e);
  // the tour opens by building the map up from nothing; flying into it from the reader's map, the dots clear first
  const rs = resume && resume.k < 1 ? 1 - ease(resume.k) : null; // (resume ends just above, on its last frame)
  dots.uniforms.uReveal.value = i !== 0 || explore ? 1 : rs ?? clamp01(local / s.reveal) ** 1.6;
  focusMat.opacity = explore ? 0 : clamp01(local / 0.4); // fades in over the first moment of the scene
  $('fill').style.width = `${100 * t / END}%`;
  // Ten million dots are a lot of work, so nothing is drawn while nothing moves: not during a tour under way or a flight, and only once
  // the camera has settled, to within what could be seen (differences are measured from the last picture drawn, so slow drifts add up).
  const uW = dots.uniforms.uWorld.value;
  const state = [v.x, v.y, v.d, v.tilt, v.heading, off.x, off.y, uW, dots.uniforms.uReveal.value, dots.uniforms.uFocus.value, dots.uniforms.uFocusSize.value, focusMat.opacity];
  const eps = [v.d * 1e-5, v.d * 1e-5, v.d * 1e-5, 1e-4, 1e-4, 0.02, 0.02, uW * 1e-3, 1e-3, 0, 1e-3, 1e-3];
  const moving = (playing && t < END) || resume || going;
  if (moving || needsDraw || !sameView(state, drawn, eps)) {
    dots.showVisible(camera);
    renderer.render(scene, camera);
    cityLabels.update(camera, mapGroup, W, H, 1, placeLabels(explore ? {} : s, local));
    drawn = state; needsDraw = false;
    if (landed) { landed = false; busy.hide('race'); }
  }
  requestAnimationFrame(frame);
}

// A lost graphics context takes the dots with it, and there's no copy here to send again, so they're placed again.
stage.addEventListener('webglcontextlost', () => dots.clear());
stage.addEventListener('webglcontextrestored', () => { showRace(chosen); });
document.addEventListener('visibilitychange', () => { needsDraw = true; });
const fit = new ResizeObserver(resize);
fit.observe($('stage')); fit.observe($('topnav'));
resize();
timeline();
dots.setLand(PC?.land);
const query = new URLSearchParams(location.search), asked = query.get('race') || '';
// From the bar view and back to it (app.js): ?by= is the bar view's by precinct or by district, kept for the way back, and ?at= is
// the camera, x,y,distance,tilt,heading, which the Bar view link also carries back, so changing views keeps the view. The place and
// zoom go back as they are now; the tilt and heading go back as they came.
BAR_BY = ['precinct', 'district'].includes(query.get('by')) ? `&by=${query.get('by')}` : '';
BAR_COLOR = query.get('color') === 'lead' ? '&color=lead' : '';
for (const id of ['viewFlat', 'view3d'])
  for (const type of ['pointerdown', 'keydown', 'click', 'contextmenu']) $(id).addEventListener(type, () => barLinks());
// ?scene=N (1-based) starts the tour at that scene, already arrived; ?tour=1 starts it from the beginning
const startAt = +query.get('scene'), onTour = STATE.tour && ((startAt >= 1 && startAt <= scenes.length) || query.get('tour') === '1');
// a race from an earlier year needs that file first; otherwise it comes in behind the map, for the race menu
if (!onTour && /^\d{4}-/.test(asked) && !asked.startsWith('2026-')) await loadHistory();
fillRaces();
const firstRace = onTour ? SENATE : raceWithId(asked) || SENATE;
if (!onTour && PERS.includes(+query.get('per'))) $('per').value = per = +query.get('per');
await showRace(firstRace);
$('loading').remove();
if (onTour) {
  page.classList.remove('exploring');
  if (startAt > 1) t = scenes[startAt - 1].start + scenes[startAt - 1].fly;
  playing = toured = true;
} else {
  explore = homeView();
  const at = (query.get('at') || '').split(',').map(Number);
  if (at.length === 5 && at.every(Number.isFinite)) {
    const [x, y, d, tilt, heading] = at, near = milesView({ x: 0, y: 0 }, 0.08).d, far = explore.d * 1.6; // zoomAt's limits
    explore = { x: Math.max(-650, Math.min(650, x)), y: Math.max(-650, Math.min(650, y)), d: Math.max(near, Math.min(far, d)),
      tilt: Math.max(0.0001, Math.min(1.5, tilt)), heading };
    BAR_ANGLE = [tilt, heading];
  }
  off.x = free.ox; off.y = free.oy;
}
updateButton();
// ---------- compare: two views side by side (compare.html, panel.js) ----------
// The Compare link opens this map beside the flat bar view, both where this camera is now. In a frame there, the camera follows the other side's.
if (!FRAMED) {
  const cmp = document.createElement('a');
  cmp.className = 'compare-link'; cmp.textContent = 'Compare ⇆';
  cmp.title = 'This map beside the flat county map, moving together. Each side keeps its own look, race and color';
  document.querySelector('.nav-row').append(cmp);
  for (const type of ['pointerdown', 'keydown', 'click', 'contextmenu']) cmp.addEventListener(type, () => {
    const v = explore || lastV;
    barLinks();
    cmp.href = compareHref(`${STATE.dots}?race=${chosen.id}${shownPer > 1 ? `&per=${shownPer}` : ''}${v ? `&at=${[v.x, v.y, v.d, v.tilt, v.heading].map(n => +n.toFixed(3)).join(',')}` : ''}`,
      $('viewFlat').getAttribute('href'));
  });
}
followCamera(() => explore && { x: explore.x, y: explore.y, d: explore.d }, c => {
  if (!explore) return;
  explore.home = false; going = null;
  explore.x = Math.max(-650, Math.min(650, c.x)); explore.y = Math.max(-650, Math.min(650, c.y));
  explore.d = Math.max(milesView({ x: 0, y: 0 }, 0.08).d, Math.min(homeView().d * 1.6, c.d));
  needsDraw = true;
}, () => H);
// the panel shown or hidden while the dots were loading, before the address could be saved
if (explore && panelParam() !== (query.get('panel') === '0' ? '&panel=0' : '')) saveUrl();
last = performance.now();
requestAnimationFrame(frame);
loadHistory();

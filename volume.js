// volume.html: Texas counties, in three steps, on their own page (not linked from the rest of the site).
//   Flat             each county colored by who won it, however many people voted there
//   Height = votes   each county raised by the votes cast there, as on the results page (texas.html)
//   Volume = votes   each county raised by its votes per square mile, so a column's volume (area × height) is its votes
// The map is equal-area (geoConicEqualArea), so a county's footprint on screen is in proportion to its real area, and the height
// is taken over that same area (the county's shape, geoArea), which makes the volume on screen exactly in proportion to votes.
// Each column is split by party and ranked, the most votes on top: the winner in the county's color, the runner-up in that party's
// color, and third-party and write-in votes in gray. All the parts share the county's footprint, so by volume each part's space is
// that party's votes there.
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { geoConicEqualArea, geoArea } from 'd3-geo';
import { feature } from 'topojson-client';
import { BINS, BAND_LABELS, REP_C, DEM_C } from './colors.js';

const $ = id => document.getElementById(id);
const fmt = n => Math.round(n).toLocaleString('en-US');
const pct = (a, b) => b ? (100 * a / b).toFixed(1) + '%' : '–';
const getJSON = url => fetch(url).then(r => { if (!r.ok) throw new Error(r.status); return r.json(); });
const EARTH_MI = 3958.8; // the earth's radius in miles: geoArea is in steradians
const H_MAX = 260, H_FLAT = 0.8; // the tallest column in either 3D step, and a flat county (map units; the map spans about ±500)
const TILT = { phi: 0.95, theta: -0.22 }; // the 3D camera's angle down from overhead, and its turn

// ---------- data: the 2026 results (statewide races) and the county shapes ----------
let res, us;
try {
  [res, us] = await Promise.all([getJSON('data/results-2026.json'), getJSON('https://cdn.jsdelivr.net/npm/us-atlas@3.0.1/counties-10m.json')]);
} catch (e) { $('loading').textContent = 'Could not load the map data. Please reload the page.'; throw e; }
const races = res.races.filter(r => !r.chamber && r.id !== 'u-s-house');
const geo = feature(us, us.objects.counties).features.filter(f => String(f.id).startsWith('48'));
const rowOf = new Map(res.counties.map((c, i) => [c.fips, i]));
const P = geoConicEqualArea().parallels([28, 34]).rotate([100, 0]).fitExtent([[-500, -500], [500, 500]], { type: 'FeatureCollection', features: geo });

// ---------- the scene ----------
const stage = $('stage');
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(2, devicePixelRatio));
stage.append(renderer.domElement);
const scene = new THREE.Scene();
scene.background = new THREE.Color('#0e1116');
scene.add(new THREE.AmbientLight(0xffffff, 0.55));
const sun = new THREE.DirectionalLight(0xffffff, 1.6); sun.position.set(-300, 600, 400); scene.add(sun);
const camera = new THREE.PerspectiveCamera(35, 1, 1, 20000);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true; controls.screenSpacePanning = true; controls.maxPolarAngle = 1.35;
const map = new THREE.Group(); map.rotation.x = -Math.PI / 2; scene.add(map); // the map's x, y (north up) and z (up) in the world

const edgeMat = new THREE.LineBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.35 });
const counties = geo.map(f => {
  const i = rowOf.get(String(f.id)), info = res.counties[i];
  const polys = f.geometry.type === 'Polygon' ? [f.geometry.coordinates] : f.geometry.coordinates;
  const shapes = polys.map(([outer, ...holes]) => {
    const ring = r => r.map(p => { const [x, y] = P(p); return new THREE.Vector2(x, -y); });
    const s = new THREE.Shape(ring(outer));
    s.holes = holes.map(h => new THREE.Path(ring(h)));
    return s;
  });
  const g = new THREE.ExtrudeGeometry(shapes, { depth: 1, bevelEnabled: false }), edges = new THREE.EdgesGeometry(g, 30);
  const part = () => { // one part of the stack: the county's shape, scaled to its height and lifted into place
    const m = new THREE.Mesh(g, [new THREE.MeshBasicMaterial(), new THREE.MeshLambertMaterial()]); // tops unlit, walls lit
    m.add(new THREE.LineSegments(edges, edgeMat));
    map.add(m);
    return m;
  };
  const mesh = part(), lose = part(), oth = part(); // the winner's, the runner-up's and the others'
  const c = { i, name: info.name, landSqMi: info.landSqMi, sqMi: geoArea(f) * EARTH_MI ** 2, mesh, lose, oth, h: H_FLAT, from: H_FLAT, to: H_FLAT };
  for (const m of [mesh, lose, oth]) m.userData = c;
  stack(c);
  return c;
});
$('loading').remove();

// a county's parts for a column of height c.h: each stands on the parts with fewer votes
// (ties: runner-up, then others, then winner, from the bottom)
function stack(c) {
  const h = c.h, t = c.total || 1, wv = Math.max(c.dem ?? 0, c.rep ?? 0), lv = Math.min(c.dem ?? 0, c.rep ?? 0);
  const a = h * lv / t, b = h * (c.other ?? 0) / t, w = c.total ? h - a - b : h;
  const set = (m, z, len) => { m.visible = len > 1e-3; m.position.z = z; m.scale.z = Math.max(len, 1e-4); };
  set(c.lose, (b < a ? b : 0) + (w < a ? w : 0), a);
  set(c.oth, (a <= b ? a : 0) + (w < b ? w : 0), b);
  set(c.mesh, (a <= w ? a : 0) + (b <= w ? b : 0), w);
}
const LOSER_C = { dem: '#584cde', rep: '#d72f30' }, OTHER_C = '#5d6c82';
const paint = (m, hex) => { const col = new THREE.Color(hex); m.material[0].color.copy(col); m.material[1].color.copy(col).multiplyScalar(0.85); };

// ---------- the race, the colors and the three steps ----------
let race = null, step = 'flat', grow = null; // grow: the columns on their way, { start, dur }
function colorOf(c) {
  if (!c.total) return '#3b4352';
  const share = 100 * Math.max(c.dem, c.rep) / c.total, k = Math.max(0, BINS.findLastIndex(b => share >= b));
  return (c.dem > c.rep ? DEM_C : REP_C)[k];
}
const heightOf = (c, s) => s === 'flat' || !c.total ? H_FLAT
  : Math.max(H_FLAT, H_MAX * (s === 'votes' ? c.total / race.maxTotal : c.total / c.sqMi / race.maxDensity));
function setRace(id) {
  race = races.find(r => r.id === id) || races[0];
  race.D = race.candidates.find(k => k.party === 'DEM'); race.R = race.candidates.find(k => k.party === 'REP');
  for (const c of counties) {
    const [dem, rep, other, total] = race.counties[c.i];
    Object.assign(c, { dem, rep, other, total });
    paint(c.mesh, colorOf(c)); paint(c.lose, dem > rep ? LOSER_C.rep : LOSER_C.dem); paint(c.oth, OTHER_C);
    stack(c);
  }
  race.maxTotal = Math.max(...counties.map(c => c.total));
  race.maxDensity = Math.max(...counties.map(c => c.total / c.sqMi));
  $('race').value = race.id;
  setStep(step, true);
  try { history.replaceState(null, '', `?race=${race.id}${step === 'flat' ? '' : `&step=${step}`}`); } catch {}
}
function setStep(s, keepCamera = false) {
  const was = step; step = s;
  for (const id of ['flat', 'votes', 'volume']) $(id).setAttribute('aria-pressed', String(id === s));
  for (const c of counties) { c.from = c.h; c.to = heightOf(c, s); }
  grow = { start: performance.now(), dur: matchMedia('(prefers-reduced-motion: reduce)').matches ? 1 : 1800 };
  if (!keepCamera && (was === 'flat') !== (s === 'flat')) turnCamera(s === 'flat' ? { phi: 0.0001, theta: 0 } : TILT);
  controls.enableRotate = s !== 'flat';
  writeNote();
  try { history.replaceState(null, '', `?race=${race.id}${s === 'flat' ? '' : `&step=${s}`}`); } catch {}
}
function writeNote() {
  const tall = [...counties].sort((a, b) => heightOf(b, step) - heightOf(a, step))[0];
  const tallVotes = [...counties].sort((a, b) => b.total - a.total)[0];
  const total = counties.reduce((n, c) => n + c.total, 0);
  const D = race.D?.last, R = race.R?.last;
  const head = `<b>2026 ${race.label}</b>, ${fmt(total)} votes${D && R ? ` · ${D} (D) ${pct(race.D.votes, total)}, ${R} (R) ${pct(race.R.votes, total)}` : ''}. `;
  $('note').innerHTML = head + (step === 'flat'
    ? 'Each county is colored by who won it, however many people voted there. Raise the counties: first by votes, then by volume.'
    : step === 'votes'
    ? `<b>Height = votes.</b> Each column is as tall as its county's vote count (tallest: ${tall.name}, ${fmt(tall.total)}). ` +
      `But a wide county fills more space than a small one with the same votes, so the space a column takes up isn't its votes.`
    : `<b>Volume = votes.</b> Each column's height is its votes per square mile, so its volume (area × height) is in proportion to its votes, ` +
      `and each party's part of it to that party's votes: ` +
      `twice the voters, twice the space. Tallest: ${tall.name}, ${fmt(tall.total / tall.sqMi)} votes per square mile` +
      (tall !== tallVotes ? `; ${tallVotes.name}, tallest by votes, spreads its ${fmt(tallVotes.total)} over ${fmt(tallVotes.sqMi)} square miles.` : '.') +
      ` Wide counties come down; small, crowded ones go up.`);
}
$('race').innerHTML = races.map(r => `<option value="${r.id}">2026 ${r.label}</option>`).join('');
$('race').onchange = e => setRace(e.target.value);
for (const id of ['flat', 'votes', 'volume']) $(id).onclick = () => { if (step !== id) setStep(id); };
$('legend').innerHTML = [['R', REP_C], ['D', DEM_C]].map(([p, cols]) =>
  `<div>${cols.map(c => `<i style="background:${c}"></i>`).join('')}<span>${p} won the county</span></div>`).join('') +
  `<div><span style="margin:0">winner's share: ${BAND_LABELS[0]} to ${BAND_LABELS.at(-1)}</span></div>` +
  `<div style="margin-top:4px"><i style="background:${LOSER_C.rep};width:9px"></i><i style="background:${LOSER_C.dem};width:9px"></i><span>runner-up</span>` +
  `<i style="background:${OTHER_C};width:9px;margin-left:10px"></i><span>others · stacked by votes, most on top</span></div>`;

// ---------- the camera: overhead when flat, tilted in 3D ----------
let turn = null; // { from: {phi, theta}, to, start }
function fitDistance() {
  const w = stage.clientWidth, h = stage.clientHeight, t = Math.tan(THREE.MathUtils.degToRad(camera.fov / 2));
  return 560 / (t * Math.min(1, w / h));
}
function place(phi, theta, r = camera.position.distanceTo(controls.target)) {
  const s = new THREE.Spherical(r, phi, theta);
  camera.position.copy(controls.target).add(new THREE.Vector3().setFromSpherical(s));
  camera.lookAt(controls.target);
}
function turnCamera(to) {
  const s = new THREE.Spherical().setFromVector3(camera.position.clone().sub(controls.target));
  // tilted, the map is foreshortened, so the camera comes closer; flat, the map's center sits a little south, clear of the buttons
  turn = { from: { phi: s.phi, theta: s.theta }, to, r0: s.radius, r1: to.phi > 0.1 ? fitDistance() * (stage.clientWidth < 600 ? 0.95 : 0.72) : fitDistance(), start: performance.now() };
  controls.target.set(0, to.phi > 0.1 ? 30 : 0, to.phi > 0.1 ? 0 : 35);
}
function resize() {
  const w = stage.clientWidth, h = stage.clientHeight;
  renderer.setSize(w, h); camera.aspect = w / h; camera.updateProjectionMatrix();
}
new ResizeObserver(resize).observe(stage); resize();
controls.target.set(0, 0, 35); place(0.0001, 0, fitDistance());

// ---------- hover ----------
const ray = new THREE.Raycaster(), mouse = new THREE.Vector2(), tip = $('tip');
let hovered = null;
function hover(e) {
  const r = renderer.domElement.getBoundingClientRect();
  mouse.set((e.clientX - r.left) / r.width * 2 - 1, -(e.clientY - r.top) / r.height * 2 + 1);
  ray.setFromCamera(mouse, camera);
  const hit = ray.intersectObjects(counties.flatMap(c => [c.mesh, c.lose, c.oth]), false)[0], c = hit?.object.userData;
  if (hovered && hovered !== c) hovered.mesh.material[0].color.set(colorOf(hovered));
  hovered = c || null;
  if (!c) { tip.style.display = 'none'; return; }
  c.mesh.material[0].color.set(colorOf(c)).lerp(new THREE.Color('#fff'), 0.3);
  const row = (a, b, m = true) => `<div class="r${m ? ' m' : ''}"><span>${a}</span><span>${b}</span></div>`;
  tip.innerHTML = `<div class="n">${c.name} County</div>` + (!c.total ? row('No votes reported', '') :
    row(`${race.D?.name ?? 'Democrat'} (D)`, `${fmt(c.dem)} · ${pct(c.dem, c.total)}`, false) +
    row(`${race.R?.name ?? 'Republican'} (R)`, `${fmt(c.rep)} · ${pct(c.rep, c.total)}`, false) +
    (c.other ? row('Others', `${fmt(c.other)} · ${pct(c.other, c.total)}`) : '') +
    row('Total votes', fmt(c.total)) +
    row('Area as drawn', `${fmt(c.sqMi)} sq mi`) +
    row('Votes per square mile', (c.total / c.sqMi).toFixed(c.total / c.sqMi < 10 ? 1 : 0)));
  tip.style.display = 'block';
  const x = e.clientX - r.left, y = e.clientY - r.top;
  tip.style.left = Math.max(8, Math.min(x + 14, r.width - tip.offsetWidth - 8)) + 'px';
  tip.style.top = Math.max(8, Math.min(y + 14, r.height - tip.offsetHeight - 8)) + 'px';
}
renderer.domElement.addEventListener('pointermove', hover);
renderer.domElement.addEventListener('pointerdown', hover);
renderer.domElement.addEventListener('pointerleave', () => { tip.style.display = 'none'; if (hovered) hovered.mesh.material[0].color.set(colorOf(hovered)); hovered = null; });

// ---------- loop ----------
const ease = t => t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2;
function frame(now) {
  if (grow) {
    const t = Math.min(1, (now - grow.start) / grow.dur), k = ease(t);
    for (const c of counties) { c.h = c.from + (c.to - c.from) * k; stack(c); }
    if (t === 1) grow = null;
  }
  if (turn) {
    const t = Math.min(1, (now - turn.start) / 1400), k = ease(t);
    controls.enabled = false;
    place(turn.from.phi + (turn.to.phi - turn.from.phi) * k, turn.from.theta + (turn.to.theta - turn.from.theta) * k, turn.r0 + (turn.r1 - turn.r0) * k);
    if (t === 1) { turn = null; controls.enabled = true; }
  } else controls.update();
  renderer.render(scene, camera);
  requestAnimationFrame(frame);
}
const q = new URLSearchParams(location.search);
setRace(q.get('race') || 'u-s-senate');
if (['votes', 'volume'].includes(q.get('step'))) setStep(q.get('step'));
requestAnimationFrame(frame);

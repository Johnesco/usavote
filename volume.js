// volume.html: Texas counties, in three steps, on their own page (not linked from the rest of the site).
//   Flat             each county colored by who won it, however many people voted there
//   Height = votes   each county raised by the votes cast there, as on the results page (texas.html)
//   Volume = votes   each county raised by its votes per square mile, so a column's volume (area × height) is its votes
// The map is equal-area (geoConicEqualArea), so a county's footprint on screen is in proportion to its real area, and the height
// is taken over that same area (the county's shape, geoArea), which makes the volume on screen exactly in proportion to votes.
// Each column is split by party and ranked, the most votes on top: the winner in the county's color, the runner-up in that party's
// color, and third-party and write-in votes in gray. All the parts share the county's footprint, so by volume each part's space is
// that party's votes there.
//   Fill             the counties flat, then three pitchers, one a side, pour each county's column of liquid, as by volume, into an
//                    unseen glass, one pitcher at a time: a layer at a time, stopping at each part of 50,000 votes or more
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
// Fill: a part's top can tilt, as a liquid's surface sloshes. uTilt is the slope in x and y (map units of height per unit across),
// about the county's middle uC; uScale is the part's height, since the tilt is added before the part is stretched to it.
function sloshable(m, ox, oy) {
  m.slosh = { uTilt: { value: new THREE.Vector2() }, uC: { value: new THREE.Vector2(ox, oy) }, uScale: { value: 1 } };
  for (const mat of m.material) {
    mat.onBeforeCompile = sh => {
      Object.assign(sh.uniforms, m.slosh);
      sh.vertexShader = sh.vertexShader.replace('void main() {', 'uniform vec2 uTilt; uniform vec2 uC; uniform float uScale;\nvoid main() {')
        .replace('#include <begin_vertex>', '#include <begin_vertex>\n  if (position.z > 0.5) transformed.z += dot(uTilt, position.xy - uC) / max(uScale, 0.001);');
    };
    mat.customProgramCacheKey = () => 'slosh';
  }
}
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
  g.computeBoundingBox();
  const ox = (g.boundingBox.min.x + g.boundingBox.max.x) / 2, oy = (g.boundingBox.min.y + g.boundingBox.max.y) / 2;
  const part = () => { // one part of the stack: the county's shape, scaled to its height and lifted into place
    const m = new THREE.Mesh(g, [new THREE.MeshBasicMaterial(), new THREE.MeshLambertMaterial()]); // tops unlit, walls lit
    m.add(new THREE.LineSegments(edges, edgeMat));
    sloshable(m, ox, oy);
    map.add(m);
    return m;
  };
  const mesh = part(), lose = part(), oth = part(); // the winner's, the runner-up's and the others'
  const c = { i, name: info.name, landSqMi: info.landSqMi, sqMi: geoArea(f) * EARTH_MI ** 2, mesh, lose, oth, ox, oy, box: g.boundingBox, h: H_FLAT, from: H_FLAT, to: H_FLAT };
  for (const m of [mesh, lose, oth]) m.userData = c;
  stack(c);
  return c;
});
$('loading').remove();

// a county's parts for a column of height c.h: each stands on the parts with fewer votes
// (ties: runner-up, then others, then winner, from the bottom)
// The parts in order from the bottom: by votes, fewest first (ties: runner-up, then others, then winner), each with its party.
function ranked(c) {
  const dWin = (c.dem ?? 0) > (c.rep ?? 0);
  return [
    { m: c.lose, party: dWin ? 'R' : 'D', v: dWin ? c.rep ?? 0 : c.dem ?? 0 },
    { m: c.oth, party: 'O', v: c.other ?? 0 },
    { m: c.mesh, party: dWin ? 'D' : 'R', v: dWin ? c.dem ?? 0 : c.rep ?? 0 },
  ].sort((a, b) => a.v - b.v); // (a stable sort: ties keep that order)
}
// c.pour, while Fill pours: how much of each party's part is in so far ({ D, R, O }, in map units of height), and c.extra, how far
// the surface is over that as it settles. Each part stands on the ones below it, so a party poured later slips in at its own
// place in the stack, as a heavier liquid would, lifting what's above it.
function stack(c) {
  const t = c.total || 1, parts = ranked(c);
  let z = 0, top = null;
  for (const p of parts) {
    const len = !c.total ? (p.m === c.mesh ? c.h : 0) : c.pour ? c.pour[p.party] : c.h * p.v / t;
    p.m.visible = len > 1e-3; p.m.position.z = z; p.m.scale.z = Math.max(len, 1e-4);
    if (p.m.visible) top = p.m;
    z += len;
  }
  if (top && c.pour && c.extra) top.scale.z = Math.max(1e-4, top.scale.z + c.extra);
  for (const p of parts) p.m.slosh.uScale.value = p.m.scale.z;
  return top;
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
const REDUCED = matchMedia('(prefers-reduced-motion: reduce)').matches;
function setStep(s, keepCamera = false) {
  const was = step; step = s;
  pour.stop(false); // (a pour under way stops where it is; Fill starts its own)
  for (const id of ['flat', 'votes', 'volume', 'fill']) $(id).setAttribute('aria-pressed', String(id === s));
  for (const c of counties) { c.from = c.h; c.to = s === 'fill' ? H_FLAT : heightOf(c, s); }
  grow = { start: performance.now(), dur: REDUCED ? 1 : s === 'fill' ? 700 : 1800 };
  if (s === 'fill') pour.start(performance.now() + (REDUCED ? 0 : 800));
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
  $('note').innerHTML = head + (step === 'fill'
    ? `<b>Fill.</b> Three pitchers hold each side's votes across the state, written on them in thousands. One at a time, they pour ` +
      `each county's votes into an unseen glass the shape of the county, to its height by volume: the space the liquid fills is the votes. ` +
      `Each county fills in order: the side with the fewest votes goes in first and the winner last, on top. Each pitcher stops ` +
      `to pour each part of 50,000 votes or more in full, and pours smaller ones on the way past. ${pour.running ? 'Press <b>Fill</b> again to finish at once.' : 'Press <b>Fill</b> to pour again.'}`
    : step === 'flat'
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
$('fill').onclick = () => { if (pour.running) { pour.stop(true); writeNote(); } else setStep('fill'); }; // again: finish, or pour again
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
  pour.update(now);
  if (turn) {
    const t = Math.min(1, (now - turn.start) / 1400), k = ease(t);
    controls.enabled = false;
    place(turn.from.phi + (turn.to.phi - turn.from.phi) * k, turn.from.theta + (turn.to.theta - turn.from.theta) * k, turn.r0 + (turn.r1 - turn.r0) * k);
    if (t === 1) { turn = null; controls.enabled = true; }
  } else controls.update();
  renderer.render(scene, camera);
  requestAnimationFrame(frame);
}
// ---------- Fill: three pitchers pour each county's column ----------
// One pitcher for each party (Democrats, Republicans, others), each holding that party's votes across the state, written on its side
// in thousands and counting down as it pours. They wait on a shelf north of Texas and go out one at a time, over the counties in
// rows, a layer at a time, so every county fills fewest votes first and its winner last: a quick pour on the way past a small part,
// a stop and a full pour at a big one (see plan). A part poured later settles into its place in the stack (see stack). The liquid
// is imitated, not simulated: a stream from the spout, drops that splash up and fall back, rings spreading on the surface, a level that overshoots and settles, and a surface that tilts back and forth and calms down.
const pour = (() => {
  const FULL = 50000, SWEEP = 5, HOVER = 34, TRAVEL = 0.9; // votes for a full pour; seconds to pass every county; spout over the top; a flight
  const PARTY = ['D', 'O', 'R'], up = new THREE.Vector3(), tmp = new THREE.Vector3(), hit = new THREE.Vector3();
  const world = (x, y, z) => map.localToWorld(tmp.set(x, y, z)).clone();
  const SHELF = { D: { x: -95, y: 610, z: 70 }, O: { x: 0, y: 610, z: 70 }, R: { x: 95, y: 610, z: 70 } }; // north of the panhandle
  const PARTY_C = { D: LOSER_C.dem, R: LOSER_C.rep, O: OTHER_C };

  // a pitcher: glass, with its party's liquid inside, a spout on its +x side, a handle opposite, and its votes on a label
  const glass = new THREE.MeshStandardMaterial({ color: 0xe4eeff, transparent: true, opacity: 0.28, roughness: 0.1, metalness: 0.1, side: THREE.DoubleSide, depthWrite: false });
  const rim = new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.55 });
  const lathe = pts => new THREE.LatheGeometry(pts.map(([x, y]) => new THREE.Vector2(x, y)), 36);
  const TIP = new THREE.Vector3(14.2, 27.6, 0); // the spout's mouth, in the pitcher's own units
  const flatQ = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), -Math.PI / 2);
  function makePitcher(party) {
    const g = new THREE.Group(); g.scale.setScalar(2.6); g.visible = false; scene.add(g);
    g.add(new THREE.Mesh(lathe([[0, 0], [8, 0], [9.5, 1.5], [10, 8], [9, 16], [9.8, 22], [10.6, 26]]), glass));
    const lip = new THREE.Mesh(new THREE.TorusGeometry(10.6, 0.35, 6, 40), rim); lip.rotation.x = Math.PI / 2; lip.position.y = 26; g.add(lip);
    const spout = new THREE.Mesh(new THREE.CylinderGeometry(1.4, 3.4, 6, 14, 1, true), glass); spout.position.set(11.2, 25.6, 0); spout.rotation.z = -1.05; g.add(spout);
    const handle = new THREE.Mesh(new THREE.TorusGeometry(6.5, 1.2, 8, 24, Math.PI), glass); handle.rotation.z = Math.PI / 2; handle.position.set(-9.6, 14, 0); g.add(handle);
    const mat = new THREE.MeshStandardMaterial({ color: PARTY_C[party], transparent: true, opacity: 0.9, roughness: 0.35 });
    const liquid = new THREE.Mesh(lathe([[0, 0], [7.6, 0], [9, 1.4], [9.5, 7.4], [8.8, 14.4]]), mat); liquid.position.y = 0.6; g.add(liquid);
    const surface = new THREE.Mesh(new THREE.CircleGeometry(8.8, 36), mat); g.add(surface);
    const canvas = document.createElement('canvas'); canvas.width = 320; canvas.height = 128;
    const tex = new THREE.CanvasTexture(canvas); tex.colorSpace = THREE.SRGBColorSpace;
    const label = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, depthTest: false, transparent: true }));
    label.scale.set(25, 10, 1); label.position.set(0, 9, 0); label.renderOrder = 10; g.add(label);
    return { party, g, liquid, surface, canvas, tex, text: '', tilt: 0, lift: null, pos: null };
  }
  const pitchers = Object.fromEntries(PARTY.map(p => [p, makePitcher(p)]));
  function writeLabel(pi, name, left) {
    const text = `${name}|${fmt(left / 1000)}K`;
    if (text === pi.text) return;
    pi.text = text;
    const x = pi.canvas.getContext('2d'), W = pi.canvas.width, Hh = pi.canvas.height;
    x.clearRect(0, 0, W, Hh);
    x.fillStyle = 'rgba(14,17,22,.82)'; x.strokeStyle = PARTY_C[pi.party]; x.lineWidth = 6;
    x.beginPath(); x.roundRect(4, 4, W - 8, Hh - 8, 22); x.fill(); x.stroke();
    x.textAlign = 'center'; x.fillStyle = '#e8ecf2';
    x.font = '600 30px system-ui, sans-serif'; x.fillText(name, W / 2, 46);
    x.font = '700 46px system-ui, sans-serif'; x.fillText(`${fmt(left / 1000)}K votes`, W / 2, 98);
    pi.tex.needsUpdate = true;
  }

  // the stream, the drops and the rings (one pitcher pours at a time, so one of each will do)
  const streamMat = new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.92 });
  const stream = new THREE.Mesh(new THREE.CylinderGeometry(1, 0.8, 1, 12, 1, true), streamMat); stream.visible = false; scene.add(stream);
  const N = 260, drops = new THREE.InstancedMesh(new THREE.SphereGeometry(0.8, 6, 4), new THREE.MeshBasicMaterial({ color: 0xffffff }), N);
  drops.instanceMatrix.setUsage(THREE.DynamicDrawUsage); drops.frustumCulled = false; scene.add(drops);
  const dropList = Array.from({ length: N }, () => ({ live: false, p: new THREE.Vector3(), v: new THREE.Vector3(), age: 0, floor: 0, size: 1 }));
  const dm = new THREE.Matrix4(), dq = new THREE.Quaternion(), ds = new THREE.Vector3();
  const rings = Array.from({ length: 12 }, () => {
    const m = new THREE.Mesh(new THREE.RingGeometry(0.8, 1.35, 40), new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0, depthWrite: false, side: THREE.DoubleSide }));
    m.rotation.x = -Math.PI / 2; m.visible = false; scene.add(m); return { m, age: 9 };
  });
  let nextDrop = 0, nextRing = 0, ringClock = 0;
  function splash(at, color, flow, dt) {
    const n = Math.round((40 + 90 * flow) * dt + Math.random()); // drops a second
    for (let k = 0; k < n; k++) {
      const d = dropList[nextDrop = (nextDrop + 1) % N], a = Math.random() * Math.PI * 2, out = 12 + Math.random() * 40;
      d.live = true; d.age = 0; d.size = 0.5 + Math.random() * 0.9; d.floor = at.y;
      d.p.copy(at); d.v.set(Math.cos(a) * out, 30 + Math.random() * 60 * flow, Math.sin(a) * out);
      drops.setColorAt(nextDrop, color);
    }
    if (drops.instanceColor) drops.instanceColor.needsUpdate = true;
    if ((ringClock += dt) > 0.22) {
      ringClock = 0;
      const r = rings[nextRing = (nextRing + 1) % rings.length];
      r.age = 0; r.m.visible = true; r.m.position.copy(at).add(up.set(0, 1.5, 0)); // (above the sloshing surface)
    }
  }
  function stepDrops(dt) {
    dropList.forEach((d, k) => {
      if (d.live) {
        d.age += dt; d.v.y -= 170 * dt; d.p.addScaledVector(d.v, dt);
        if ((d.v.y < 0 && d.p.y < d.floor) || d.age > 1.6) d.live = false;
      }
      ds.setScalar(d.live ? d.size * 5 * (1 - 0.5 * d.age) : 0); // (a map unit is under a pixel across the whole state)
      drops.setMatrixAt(k, dm.compose(d.p, dq, ds));
    });
    drops.instanceMatrix.needsUpdate = true;
    for (const r of rings) {
      if (!r.m.visible) continue;
      r.age += dt;
      r.m.scale.setScalar(3 + r.age * 34); r.m.material.opacity = Math.max(0, 0.75 * (1 - r.age / 1.1));
      if (r.age > 1.1) r.m.visible = false;
    }
  }

  // the plan: each pour (a party into a county) and where each pitcher is meanwhile, one flight at a time
  let job = null;
  const votesOf = (c, P) => P === 'D' ? c.dem : P === 'R' ? c.rep : c.other;
  function plan(t0) {
    const H = c => heightOf(c, 'volume');
    const rest = counties.filter(c => c.total);
    const row = c => Math.floor((600 - c.oy) / 80); // rows of the map, north (larger y) first
    rest.sort((a, b) => row(a) - row(b) || (row(a) % 2 ? b.ox - a.ox : a.ox - b.ox));
    const keys = { D: [], R: [], O: [] }, pours = [];
    const shelf = (P, t) => keys[P].push({ t, ...SHELF[P], tilt: 0 });
    for (const P of PARTY) shelf(P, 0);
    let t = 0;
    // A layer at a time, so that every county fills in order, fewest votes first and the winner last: each county's bottom part,
    // then its middle, then its top. Within a layer each pitcher sweeps, in rows, the counties whose part there is its party's:
    // others first, then the party with fewer votes statewide, then the one with more. It pours a small part on the way past; at a
    // part of FULL votes or more it stops and pours it in full, for longer the more votes there are.
    const total = P => counties.reduce((n, c) => n + votesOf(c, P), 0);
    const sweepOrder = ['O', ...(total('D') < total('R') ? ['D', 'R'] : ['R', 'D'])];
    const pathLen = list => list.reduce((n, c, k) => k ? n + Math.hypot(c.ox - list[k - 1].ox, c.oy - list[k - 1].oy) : 0, 0);
    const speed = Math.max(1, pathLen(rest)) / SWEEP;
    const vMax = Math.max(...rest.flatMap(c => PARTY.map(P => votesOf(c, P) ?? 0)));
    for (let layer = 0; layer < 3; layer++) for (const P of sweepOrder) {
      const list = rest.filter(c => { const part = ranked(c)[layer]; return part.party === P && part.v > 0; });
      if (!list.length) continue;
      shelf(P, t); t += TRAVEL;
      list.forEach((c, k) => {
        if (k) t += Math.hypot(c.ox - list[k - 1].ox, c.oy - list[k - 1].oy) / speed;
        const v = votesOf(c, P), h = H(c) * v / c.total;
        if (v >= FULL) { // stop, tip, pour it all, and go on
          const dur = 0.4 + 1.4 * Math.sqrt(v / vMax), z = H(c) + HOVER;
          t += 0.2; keys[P].push({ t, x: c.ox, y: c.oy, z, tilt: 1.15 });
          pours.push({ c, P, h, votes: v, start: t + 0.1, dur });
          t += dur + 0.2; keys[P].push({ t, x: c.ox, y: c.oy, z, tilt: 1.15 });
          t += 0.2;
        } else {
          keys[P].push({ t, x: c.ox, y: c.oy, z: Math.max(30, H(c)) + HOVER, tilt: 1.05 });
          pours.push({ c, P, h, votes: v, start: t, dur: 0.6, sweep: true });
        }
      });
      t += 0.7; shelf(P, t + TRAVEL); t += TRAVEL;
    }
    const lastPour = new Map();
    for (const p of pours) lastPour.set(p.c, Math.max(lastPour.get(p.c) ?? 0, p.start + p.dur));
    return { t0, keys, pours, end: t, done: t + 0.5, H, lastPour, totals: Object.fromEntries(PARTY.map(P => [P, total(P)])) };
  }
  function at(keys, t) { // where a pitcher is at time t, between its keys
    const k = keys.findIndex(q => q.t > t);
    if (k < 0) return keys.at(-1);
    if (k === 0) return keys[0];
    const a = keys[k - 1], b = keys[k], u = (t - a.t) / Math.max(1e-6, b.t - a.t), e = u * u * (3 - 2 * u);
    return { x: a.x + (b.x - a.x) * e, y: a.y + (b.y - a.y) * e, z: a.z + (b.z - a.z) * e, tilt: a.tilt + (b.tilt - a.tilt) * e };
  }
  // how high a pitcher must be to clear the columns around it: their tops within its reach, but not the column it pours into
  // (the one under the spout, which the stream reaches down to). Tipped, a pitcher hangs about 75 map units below its spout.
  const REACH = 55, BELOW = 80;
  function clearance(x, y) {
    let top = 0;
    for (const c of counties) {
      const b = c.box;
      if (x < b.min.x - REACH || x > b.max.x + REACH || y < b.min.y - REACH || y > b.max.y + REACH) continue;
      if (Math.hypot(x - c.ox, y - c.oy) < 25 && x >= b.min.x && x <= b.max.x && y >= b.min.y && y <= b.max.y) continue; // the one under it
      top = Math.max(top, c.h + (c.extra || 0));
    }
    return top + BELOW;
  }
  function settle(c, H) { // poured: the whole column, still
    c.pour = undefined; c.extra = 0; c.h = H;
    for (const m of [c.lose, c.oth, c.mesh]) m.slosh.uTilt.value.set(0, 0);
    stack(c);
  }
  const names = () => ({ D: race.D ? `${race.D.last} (D)` : 'Democrats', R: race.R ? `${race.R.last} (R)` : 'Republicans', O: 'Others' });

  let last = 0;
  const yaw = new THREE.Quaternion(), tipQ = new THREE.Quaternion(), col = new THREE.Color(), tip = new THREE.Vector3();
  return {
    get running() { return !!job; },
    start(when) {
      job = plan(when); last = when;
      for (const c of counties) { c.pour = undefined; c.extra = 0; c.settled = false; }
      for (const pi of Object.values(pitchers)) { pi.lift = null; pi.tilt = 0; pi.text = ''; }
      if (REDUCED) this.stop(true);
    },
    // finish: every column poured at once; otherwise each stays at what's in it (for the next step to rise from)
    stop(finish) {
      if (!job) return;
      for (const c of counties) {
        if (finish) settle(c, job.H(c));
        else if (c.pour) {
          const sum = c.pour.D + c.pour.R + c.pour.O;
          c.pour = undefined; c.extra = 0; c.h = Math.max(H_FLAT, sum);
          for (const m of [c.lose, c.oth, c.mesh]) m.slosh.uTilt.value.set(0, 0);
          stack(c);
        }
      }
      job = null; stream.visible = false;
      for (const pi of Object.values(pitchers)) pi.g.visible = false;
      dropList.forEach(d => d.live = false); stepDrops(0); for (const r of rings) r.m.visible = false;
    },
    update(now) {
      if (!job) return;
      const dt = Math.min(0.05, Math.max(0, (now - last) / 1000)); last = now;
      const t = (now - job.t0) / 1000;
      if (t < 0) return; // the counties are going flat first
      // each county's liquid: what each party has poured in so far, the surface overshooting and settling, and sloshing
      const left = { ...job.totals }, touched = new Set();
      let pouring = null;
      for (const p of job.pours) {
        const s = t - p.start, c = p.c;
        if (s < 0) continue;
        const u = Math.min(1, s / p.dur);
        left[p.P] -= p.votes * u;
        if (c.settled) continue;
        if (t > job.lastPour.get(c) + 1.6) { settle(c, job.H(c)); c.settled = true; continue; }
        if (!touched.has(c)) {
          touched.add(c);
          c.h = job.H(c); c.pour = { D: 0, R: 0, O: 0 }; c.extra = 0; c.slosh = 0;
        }
        c.pour[p.P] = p.h * (u < 0.08 ? u * u / 0.16 : u - 0.04) / 0.96;
        if (u < 1) { c.slosh = Math.max(c.slosh, 0.035); if (!pouring || p.start > pouring.start) pouring = p; }
        else {
          const done = s - p.dur, A = Math.min(3, 0.05 * p.h + 0.6);
          c.extra += A * Math.exp(-3.2 * done) * Math.sin(15 * done);
          c.slosh = Math.max(c.slosh, 0.09 * Math.exp(-2.4 * done));
        }
      }
      for (const c of touched) {
        const top = stack(c), w = c.i * 1.7;
        for (const m of [c.lose, c.oth, c.mesh]) if (m !== top) m.slosh.uTilt.value.set(0, 0);
        top?.slosh.uTilt.value.set(c.slosh * Math.sin(9 * t + w), c.slosh * Math.cos(7.3 * t + w));
      }
      // the pitchers: where each is, facing across the screen so its stream and label are seen, tipped to pour
      const view = new THREE.Spherical().setFromVector3(camera.position.clone().sub(controls.target));
      yaw.setFromAxisAngle(up.set(0, 1, 0), view.theta);
      const nm = names();
      for (const P of PARTY) {
        const pi = pitchers[P], k = at(job.keys[P], t), parked = Math.hypot(k.x - SHELF[P].x, k.y - SHELF[P].y) < 1;
        pi.tilt += ((pouring?.P === P ? k.tilt : Math.min(k.tilt, 0.35)) - pi.tilt) * Math.min(1, dt * 6);
        tipQ.setFromAxisAngle(up.set(0, 0, 1), -pi.tilt);
        pi.g.quaternion.copy(yaw).multiply(tipQ);
        pi.g.position.set(0, 0, 0); pi.g.updateMatrixWorld(true);
        tip.copy(TIP).applyMatrix4(pi.g.matrixWorld);
        const goal = parked ? k.z : Math.max(k.z, clearance(k.x, k.y)); // up and over a taller column, rather than through it
        pi.lift = pi.lift === null ? goal : pi.lift + (goal - pi.lift) * Math.min(1, dt * (goal > pi.lift ? 8 : 2.5));
        pi.g.position.copy(world(k.x, k.y, pi.lift)).sub(tip); pi.g.updateMatrixWorld(true);
        pi.pos = { x: k.x, y: k.y };
        // what's left in it: the liquid inside, level as the pitcher tips, and the label
        const frac = Math.max(0, left[P] / Math.max(1, job.totals[P]));
        pi.liquid.scale.y = Math.max(0.001, frac); pi.liquid.visible = pi.surface.visible = frac > 0.002;
        pi.surface.position.y = 0.6 + 14.4 * frac; pi.surface.quaternion.copy(pi.g.quaternion).invert().multiply(flatQ);
        writeLabel(pi, nm[P], Math.max(0, left[P]));
        pi.g.visible = job.totals[P] > 0;
      }
      // the stream: from the pouring pitcher's spout straight down to the surface, as thick as the pour is strong
      if (pouring) {
        const c = pouring.c, s = t - pouring.start, flow = Math.min(1, s / 0.25, (pouring.dur - s) / 0.2 + 0.15);
        const pi = pitchers[pouring.P], part = ranked(c).find(q => q.party === pouring.P).m;
        tip.copy(TIP).applyMatrix4(pi.g.matrixWorld);
        col.copy(part.material[0].color); streamMat.color.copy(col);
        hit.copy(world(pi.pos.x, pi.pos.y, c.pour.D + c.pour.R + c.pour.O)); hit.x = tip.x; hit.z = tip.z;
        const len = Math.max(0.1, tip.y - hit.y), r = (pouring.sweep ? 1.8 : 3.2) * flow * (1 + 0.12 * Math.sin(t * 47));
        stream.visible = flow > 0.02;
        stream.position.set(tip.x, (tip.y + hit.y) / 2, tip.z); stream.scale.set(r, len, r);
        splash(hit, col, flow * (pouring.sweep ? 0.5 : 1), dt);
      } else stream.visible = false;
      stepDrops(dt);
      if (t > job.done && [...job.lastPour.values()].every(e => t > e + 1.6)) { this.stop(true); writeNote(); }
    },
  };
})();

const q = new URLSearchParams(location.search);
setRace(q.get('race') || 'u-s-senate');
if (['votes', 'volume', 'fill'].includes(q.get('step'))) setStep(q.get('step'));
requestAnimationFrame(frame);

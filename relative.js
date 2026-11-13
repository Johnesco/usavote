// Relative color: the 2026 U.S. Senate race in Texas, county by county, in two color scales, and a fade between them.
//
// Percentage color is the usual one, the same as the bar view's (app.js): the winner's color, shaded by the winner's share
// of the county's vote in 10-point bands. Relative color keeps the winner's color but shades by the county's lead in
// votes (winner minus runner-up), on a square-root scale up to the biggest lead in the state, so counties where few
// people voted fade to pale whatever their percentage. The page fades each county's color from one to the other.
//
// Each step in the text names how far the map has faded (data-mix, 0 = percentage, 1 = relative) and which counties to
// point at (data-focus); the numbers in the text are worked out here from the results, so they can't drift from the data.
import { geoConicEqualArea, geoPath } from 'd3-geo';
import { feature } from 'topojson-client';
import { STATE } from './state.js';

const GEO_URL = 'https://cdn.jsdelivr.net/npm/us-atlas@3.0.1/counties-10m.json';
const $ = id => document.getElementById(id);
const num = n => n.toLocaleString('en-US');
const short = n => n >= 1e6 ? (n / 1e6).toFixed(2) + ' million' : num(n);
const pct = (a, b, d = 0) => (100 * a / b).toFixed(d) + '%';
const sum = (list, f) => list.reduce((s, c) => s + f(c), 0);
const getJSON = url => fetch(url).then(r => { if (!r.ok) throw new Error(r.status); return r.json(); });

const [res, us] = await Promise.all([getJSON(STATE.data.results), getJSON(GEO_URL)]);
const race = res.races.find(r => r.id === 'u-s-senate');
const D = race.candidates.find(c => c.party === 'DEM'), R = race.candidates.find(c => c.party === 'REP');
const counties = res.counties.map((c, i) => {
  const [dem, rep, , total] = race.counties[i];
  const dWon = dem > rep;
  return { ...c, dem, rep, total, dWon, lead: Math.abs(dem - rep), share: 100 * Math.max(dem, rep) / total };
});
const byFips = new Map(counties.map(c => [c.fips, c]));
const TOT = sum(counties, c => c.total), LAND = sum(counties, c => c.landSqMi);
const W = D.votes > R.votes ? D : R, L = W === D ? R : D;      // the state's winner and runner-up
const wonBy = (c, cand) => (c.dWon ? D : R) === cand;
const party = cand => cand === D ? 'd' : 'r';
const name = cand => `<span class="${party(cand)}">${cand.last}</span>`;

// ---------- the two color scales ----------
const BINS = [40, 50, 60, 70, 80, 90];
const BAND_LABELS = ['<50%', '50–60', '60–70', '70–80', '80–90', '90+'];
const REP_C = ['#ffb2b2', '#e27f7f', '#d75d5d', '#d72f30', '#c21b18', '#a80000'];
const DEM_C = ['#a5b0ff', '#7996e2', '#6674de', '#584cde', '#3933e5', '#0d0596'];
const PALE = '#ece7e1';
const band = c => Math.max(0, BINS.findLastIndex(b => c.share >= b));
const rgb = hex => [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16));
const ramp = c => c.dWon ? DEM_C : REP_C;
const pctColor = c => rgb(ramp(c)[band(c)]);
const MAX_LEAD = Math.max(...counties.map(c => c.lead));
const relT = lead => Math.sqrt(lead / MAX_LEAD);               // 0 to 1: how dark, by the county's lead in votes
// relative ramp: pale, then the same six shades as the percentage scale, evenly spaced
function relColorAt(t, cols) {
  const stops = [PALE, ...cols].map(rgb), x = Math.min(1, t) * (stops.length - 1), i = Math.min(stops.length - 2, Math.floor(x)), f = x - i;
  return stops[i].map((v, k) => v + (stops[i + 1][k] - v) * f);
}
const relColor = c => relColorAt(relT(c.lead), ramp(c));
for (const c of counties) { c.colA = pctColor(c); c.colB = relColor(c); }
const mixColor = (c, m) => `rgb(${c.colA.map((v, k) => Math.round(v + (c.colB[k] - v) * m)).join(',')})`;

// ---------- the counties the text points at ----------
const BIG = [...counties].sort((a, b) => b.total - a.total)[0];
const TINY = counties.filter(c => band(c) === 5).sort((a, b) => a.total - b.total)[0] ?? [...counties].sort((a, b) => b.share - a.share)[0];
const DARK = counties.filter(c => wonBy(c, L) && c.share >= 70);   // the runner-up's three darkest shades
const DARKEST = counties.filter(c => wonBy(c, L) && c.share >= 80);
const CLOSE_BIG = counties.filter(c => c.share < 60).sort((a, b) => b.lead - a.lead)[0];
const SMALL_LEAD = 5000, SMALL = counties.filter(c => c.lead < SMALL_LEAD);
const FOCUS = { tiny: [TINY], big: [BIG], dark: DARK, close: [CLOSE_BIG] };
const compare = (a, b) => a >= b ? `more than` : a >= 0.9 * b ? `almost as many as` : `${pct(a, b)} as many as`;
const bandName = c => c.share < 50 ? 'under 50%' : BAND_LABELS[band(c)].replace('–', ' to ').replace('90+', '90% or more') + (band(c) < 5 ? '%' : '');

// ---------- the text ----------
const lWon = counties.filter(c => wonBy(c, L));
const fill = (id, html) => { const el = $(id); if (el) el.innerHTML = html; };
fill('s1', `${W.name} won the state, ${pct(W.votes, TOT, 1)} to ${pct(L.votes, TOT, 1)}, a lead of <b>${num(W.votes - L.votes)} votes</b>. ` +
  `But ${name(L)} won ${lWon.length} of ${counties.length} counties, covering ${pct(sum(lWon, c => c.landSqMi), LAND)} of the land, many of them by a lot. ` +
  `Each county is colored for whoever won it, and shaded by the winner's share: light for a close race, dark for a landslide.`);
fill('s2', `<b>${TINY.name} County</b>: ${num(TINY.total)} voters, ${pct(Math.max(TINY.dem, TINY.rep), TINY.total)} for ${name(TINY.dWon ? D : R)}, ` +
  `a lead of <b>${num(TINY.lead)} votes</b>. It gets the darkest shade on the map.` +
  `<span class="big">${num(TINY.lead)} vs. ${num(BIG.lead)}</span>` +
  `<b>${BIG.name} County</b>: ${short(BIG.total)} voters, ${pct(Math.max(BIG.dem, BIG.rep), BIG.total)} for ${name(BIG.dWon ? D : R)}, ` +
  `a lead of <b>${num(BIG.lead)} votes</b>, ${num(Math.round(BIG.lead / TINY.lead))} times as many. It gets a lighter shade.`);
const darkLead = sum(DARK, c => c.lead);
fill('s3', `<b>${DARK.length} counties</b> gave ${name(L)} 70% or more, the three darkest reds. They cover <b>${pct(sum(DARK, c => c.landSqMi), LAND)} of Texas</b>, ` +
  `but cast just ${pct(sum(DARK, c => c.total), TOT)} of its votes. Together, their lead for ${name(L)} was ${num(darkLead)} votes.` +
  `<span class="big">${num(BIG.lead)}</span>${BIG.name} County's lead alone for ${name(BIG.dWon ? D : R)}: ${compare(BIG.lead, darkLead)} all ${DARK.length} of them put together.`);
fill('s4', `<b>${CLOSE_BIG.name} County</b> went ${pct(Math.max(CLOSE_BIG.dem, CLOSE_BIG.rep), CLOSE_BIG.total)} for ${name(CLOSE_BIG.dWon ? D : R)}, ` +
  `so it gets one of the lightest shades. But ${short(CLOSE_BIG.total)} people voted there, so that narrow win was a lead of <b>${num(CLOSE_BIG.lead)} votes</b>: ` +
  `${compare(CLOSE_BIG.lead, sum(DARKEST, c => c.lead))} the ${DARKEST.length} counties that gave ${name(L)} 80% or more, put together.`);
fill('s5', `Now each county is shaded by its <b>lead in votes</b>: the winner's votes minus the runner-up's. The darkest is ${BIG.name} County, ` +
  `with a lead of ${num(MAX_LEAD)}. The more votes a county added to its winner's statewide total, the darker it is, and a county where few people voted fades to pale, whatever its percentage.`);
fill('s6', `${TINY.name} County's lead of ${num(TINY.lead)} is ${pct(TINY.lead, BIG.lead, 2)} of ${BIG.name} County's, so it all but disappears. ` +
  `${BIG.name} County is now the darkest on the map.`);
fill('s7', `The ${DARK.length} counties that were the darkest red now barely show. In all, <b>${SMALL.length} counties</b> had a lead under ${num(SMALL_LEAD)} votes. ` +
  `They cover <b>${pct(sum(SMALL, c => c.landSqMi), LAND)} of Texas</b>, and they all look pale.`);
fill('s8b', `${CLOSE_BIG.name} County, at ${pct(Math.max(CLOSE_BIG.dem, CLOSE_BIG.rep), CLOSE_BIG.total)}, now shows clearly, because a modest win among ${short(CLOSE_BIG.total)} voters is a lead of ${num(CLOSE_BIG.lead)}.`);
$('src').textContent = `Results: ${res.meta.resultsSource}, as of ${res.meta.resultsUpdated}.`;

// ---------- legends ----------
const legRow = (cand, inner) => `<div class="row"><span class="${party(cand)}">${cand.last}</span>${inner}</div>`;
$('legPct').innerHTML = `<div class="t">Winner's share of the county's vote</div>` +
  [W, L].map(cand => legRow(cand, `<div class="bands">${(cand === D ? DEM_C : REP_C).map(col => `<i style="background:${col}"></i>`).join('')}</div>`)).join('') +
  `<div class="ticks"><span></span><div class="bandlabels">${BAND_LABELS.map(l => `<span>${l}</span>`).join('')}</div></div>`;
const gradient = cols => `linear-gradient(90deg, ${[PALE, ...cols].map((c, i, a) => `${c} ${(100 * i / (a.length - 1)).toFixed(1)}%`).join(', ')})`;
const TICKS = [0, 10000, 50000, 150000, MAX_LEAD].filter((v, i, a) => i === a.length - 1 || v < MAX_LEAD * 0.8);
const tickLabel = v => v === 0 ? '0' : v >= 1000 ? Math.round(v / 1000) + 'K' : String(v);
$('legRel').innerHTML = `<div class="t">County's lead in votes</div>` +
  [W, L].map(cand => legRow(cand, `<div class="ramp" style="background:${gradient(cand === D ? DEM_C : REP_C)}"></div>`)).join('') +
  `<div class="ticks"><span></span><div class="pos">${TICKS.map(v => `<span style="left:${(100 * relT(v)).toFixed(1)}%">${tickLabel(v)}</span>`).join('')}</div></div>`;

// ---------- the map ----------
const VW = 1000, VH = 900;
const svg = $('map');
svg.setAttribute('viewBox', `0 0 ${VW} ${VH}`);
const geo = feature(us, us.objects.counties);
const tx = { type: 'FeatureCollection', features: geo.features.filter(f => String(f.id).startsWith(STATE.fips) && byFips.has(String(f.id))) };
const projection = geoConicEqualArea().parallels(STATE.parallels).rotate(STATE.rotate).fitExtent([[10, 10], [VW - 10, VH - 10]], tx);
const path = geoPath(projection);
const NS = 'http://www.w3.org/2000/svg';
const el = (tag, attrs = {}, parent = svg) => { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); parent.appendChild(e); return e; };
const gCounties = el('g'), gFocus = el('g'), gTags = el('g');
const shapes = tx.features.map(f => {
  const c = byFips.get(String(f.id));
  c.d = path(f); c.centroid = path.centroid(f);
  c.node = el('path', { d: c.d, class: 'county' }, gCounties);
  return c;
});

// ---------- drawing: the fade, and the counties in focus ----------
let mix = 0, focus = [];
function drawColors() {
  for (const c of shapes) c.node.style.fill = mixColor(c, mix);
  $('legPct').style.opacity = String(1 - mix);
  $('legRel').style.opacity = String(mix);
  $('modeName').textContent = mix < 0.02 ? 'Percentage color' : mix > 0.98 ? 'Relative color' : 'Fading…';
  $('mix').value = String(Math.round(mix * 1000));
}
function drawFocus() {
  const set = new Set(focus);
  for (const c of shapes) c.node.style.opacity = set.size && !set.has(c) ? '0.28' : '1';
  gFocus.replaceChildren(); gTags.replaceChildren();
  if (focus.length > 6) return; // a big group is shown by dimming the rest, without outlines or names
  for (const c of focus) {
    el('path', { d: c.d, class: 'focus' }, gFocus);
    const [x, y] = c.centroid, right = x < VW - 330;
    const t = el('text', { class: 'tag', x: right ? x + 18 : x - 18, y: y - 6, 'text-anchor': right ? 'start' : 'end' }, gTags);
    el('tspan', {}, t).textContent = `${c.name}`;
    el('tspan', { class: 'sub', x: right ? x + 18 : x - 18, dy: 24 }, t).textContent = `${num(c.total)} voters · lead ${num(c.lead)}`;
  }
}
function draw() { drawColors(); }

// one animation at a time, from wherever the map is now
let anim = null;
const ease = x => x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2;
function fadeTo(target, seconds) {
  if (anim) cancelAnimationFrame(anim.id);
  const from = mix, dist = Math.abs(target - from);
  if (dist < 0.001) { anim = null; mix = target; draw(); updateButton(); return; }
  const dur = seconds * 1000 * Math.max(0.35, dist), start = performance.now();
  const step = now => {
    const k = Math.min(1, (now - start) / dur);
    mix = from + (target - from) * ease(k); draw();
    if (k < 1) anim.id = requestAnimationFrame(step); else { anim = null; updateButton(); }
  };
  anim = { id: requestAnimationFrame(step), target };
  updateButton();
}
const updateButton = () => { const goingTo = anim ? anim.target : mix; $('fade').textContent = goingTo > 0.5 ? '◀ Fade back' : 'Fade ▶'; };

$('mix').addEventListener('input', e => { if (anim) { cancelAnimationFrame(anim.id); anim = null; } mix = e.target.value / 1000; draw(); updateButton(); });
$('fade').addEventListener('click', () => fadeTo((anim ? anim.target : mix) > 0.5 ? 0 : 1, 3));

// ---------- the steps: whichever crosses the reading line sets the map ----------
const steps = [...document.querySelectorAll('.rel-step')];
const phone = matchMedia('(max-width: 860px)');
let current = -1;
function onScroll() {
  const line = innerHeight * (phone.matches ? 0.72 : 0.5);
  let i = 0;
  steps.forEach((s, k) => { if (s.getBoundingClientRect().top < line) i = k; });
  if (i === current) return;
  current = i;
  steps.forEach((s, k) => s.classList.toggle('now', k === i));
  const s = steps[i];
  focus = (s.dataset.focus ?? '').split(',').flatMap(k => FOCUS[k] ?? []);
  drawFocus();
  fadeTo(Number(s.dataset.mix), 2.4);
}
addEventListener('scroll', onScroll, { passive: true });
addEventListener('resize', onScroll);

// ---------- the tooltip ----------
const tip = $('tip'), fig = $('figure');
gCounties.addEventListener('pointermove', e => {
  const c = shapes.find(s => s.node === e.target); if (!c) return;
  const winner = c.dWon ? D : R;
  tip.innerHTML = `<b>${c.name} County</b>${pct(Math.max(c.dem, c.rep), c.total)} for ${name(winner)}<br>Lead: ${num(c.lead)} votes<br>${num(c.total)} voters`;
  tip.hidden = false;
  const box = fig.getBoundingClientRect(), x = e.clientX - box.left, y = e.clientY - box.top;
  tip.style.left = Math.min(x + 14, box.width - tip.offsetWidth - 4) + 'px';
  tip.style.top = Math.max(0, y - tip.offsetHeight - 10) + 'px';
});
gCounties.addEventListener('pointerleave', () => { tip.hidden = true; });

draw();
onScroll();

// The U.S. homepage: a map of the states and the ways to see each state that's ready (state.js). Every other state shows
// as not available yet. The list of states needs no download, so it still works if the map's shapes don't load.
import { geoAlbersUsa, geoPath } from 'd3-geo';
import { feature } from 'topojson-client';
import { STATES } from './state.js';

const US_STATES = [['01','Alabama'],['02','Alaska'],['04','Arizona'],['05','Arkansas'],['06','California'],['08','Colorado'],
  ['09','Connecticut'],['10','Delaware'],['11','District of Columbia'],['12','Florida'],['13','Georgia'],['15','Hawaii'],
  ['16','Idaho'],['17','Illinois'],['18','Indiana'],['19','Iowa'],['20','Kansas'],['21','Kentucky'],['22','Louisiana'],
  ['23','Maine'],['24','Maryland'],['25','Massachusetts'],['26','Michigan'],['27','Minnesota'],['28','Mississippi'],
  ['29','Missouri'],['30','Montana'],['31','Nebraska'],['32','Nevada'],['33','New Hampshire'],['34','New Jersey'],
  ['35','New Mexico'],['36','New York'],['37','North Carolina'],['38','North Dakota'],['39','Ohio'],['40','Oklahoma'],
  ['41','Oregon'],['42','Pennsylvania'],['44','Rhode Island'],['45','South Carolina'],['46','South Dakota'],['47','Tennessee'],
  ['48','Texas'],['49','Utah'],['50','Vermont'],['51','Virginia'],['53','Washington'],['54','West Virginia'],['55','Wisconsin'],['56','Wyoming']];
const NAME = new Map(US_STATES);
const READY = new Map(STATES.map(s => [s.fips, s]));
const $ = id => document.getElementById(id);
const opens = s => s.results.href;

// the panel for each state that's ready
$('ready').innerHTML = STATES.map(s => `
  <section class="state-card" aria-labelledby="st-${s.fips}">
    <div class="kicker">Available now</div>
    <h2 id="st-${s.fips}">${s.name}</h2>
    <p class="summary">${s.summary}</p>
    <a class="view first" href="${s.results.href}"><b>${s.results.title} →</b><span>${s.results.text}</span></a>
  </section>`).join('');

// every state, for finding one by name
$('list').innerHTML = US_STATES.map(([f, n]) => READY.has(f)
  ? `<li><a class="on" href="${opens(READY.get(f))}">${n}</a></li>`
  : `<li><span>${n}</span></li>`).join('');

// the map
const status = $('status');
const idle = `${STATES.map(s => s.name).join(', ')} ${STATES.length > 1 ? 'are' : 'is'} ready. Other states aren't available yet.`;
status.textContent = idle;
try {
  const r = await fetch('https://cdn.jsdelivr.net/npm/us-atlas@3.0.1/states-10m.json');
  if (!r.ok) throw new Error(r.status);
  const us = await r.json();
  const all = feature(us, us.objects.states).features.filter(f => NAME.has(String(f.id)));
  const W = 960, H = 600;
  const path = geoPath(geoAlbersUsa().fitSize([W, H], { type: 'FeatureCollection', features: all }));
  $('map').innerHTML = `<svg viewBox="0 0 ${W} ${H}" role="group" aria-label="Map of the United States">` +
    all.filter(f => !READY.has(String(f.id))).map(f =>
      `<path class="st" data-f="${f.id}" d="${path(f)}"><title>${NAME.get(String(f.id))}: not available yet</title></path>`).join('') +
    // ready states last, so their outlines sit on top
    all.filter(f => READY.has(String(f.id))).map(f => { const s = READY.get(String(f.id)); return `
      <a href="${opens(s)}" aria-label="${s.name}: see the results"><path class="st on" data-f="${f.id}" d="${path(f)}"><title>${s.name}</title></path>` +
      `<text class="st-name" x="${path.centroid(f)[0]}" y="${path.centroid(f)[1]}">${s.name}</text></a>`; }).join('') +
    `</svg>`;
  const say = e => {
    const f = e.target.closest?.('[data-f]')?.dataset.f;
    status.textContent = !f ? idle : READY.has(f) ? `${NAME.get(f)}: see the results` : `${NAME.get(f)}: not available yet`;
  };
  $('map').addEventListener('pointermove', say);
  $('map').addEventListener('pointerdown', say);
  $('map').addEventListener('pointerleave', () => { status.textContent = idle; });
} catch (e) {
  console.error('The map of the states did not load', e);
  $('map').hidden = true;
}

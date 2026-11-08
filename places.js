// The "go to a city, county or precinct" menus, shared by the results page (app.js) and the voter dot page (voters.js).
// The page has <select id="goCity">, <select id="goCounty"> and <select id="goPrecinct">. This fills them and says what was
// chosen; the page moves its own camera, draws its own outline and shows describePlace() where it likes.
//
// onChoose gets null (nothing chosen) or { kind: 'city' | 'county' | 'precinct', view: { x, y, halfW, halfH } in map units:
// the area to show, and for each kind: city: name, people; county: c; precinct: c, v (from loadPrecincts), boxEdges: a box
// around its census blocks, for a line drawing (the pages don't have precinct boundaries) }.
const fmt = n => n.toLocaleString('en-US');
const pct = (a, b) => (100 * a / b).toFixed(0) + '%';

// counties: [{ fips, name, box: { x0, y0, x1, y1 } }]; upm: map units per mile; getVtds: county -> its precincts, maybe later
export function createPlaceMenus({ counties, P, upm, cityUrl, getVtds, onChoose }) {
  const $ = id => document.getElementById(id);
  const byFips = new Map(counties.map(c => [c.fips, c]));
  let cities = [], vtds = [], job = 0;

  function fillPrecincts(c, list, waiting) {
    vtds = list;
    $('goPrecinct').disabled = !list.length;
    $('goPrecinct').title = list.length ? `Go to a precinct in ${c.name} County` : 'Pick a county first';
    $('goPrecinct').innerHTML = `<option value="">${waiting ? 'Loading…' : 'Precinct…'}</option>` +
      list.map((v, i) => [v.name, i]).sort((a, b) => a[0].localeCompare(b[0], 'en', { numeric: true }))
        .map(([n, i]) => `<option value="${i}">${n}</option>`).join('');
  }
  const countyPlace = c => ({ kind: 'county', c, view: {
    x: (c.box.x0 + c.box.x1) / 2, y: (c.box.y0 + c.box.y1) / 2,
    halfW: 0.6 * (c.box.x1 - c.box.x0), halfH: 0.6 * (c.box.y1 - c.box.y0) } });

  $('goCounty').innerHTML += [...counties].sort((a, b) => a.name.localeCompare(b.name))
    .map(c => `<option value="${c.fips}">${c.name}</option>`).join('');
  $('goCounty').addEventListener('change', async e => {
    $('goCity').value = '';
    const c = byFips.get(e.target.value), mine = ++job;
    fillPrecincts(c, [], !!c);
    onChoose(c ? countyPlace(c) : null);
    if (!c) return;
    const list = await getVtds(c);
    if (mine === job) fillPrecincts(c, list || [], false);
  });
  $('goPrecinct').addEventListener('change', e => {
    const c = byFips.get($('goCounty').value), v = vtds[e.target.value];
    if (!v) { onChoose(c ? countyPlace(c) : null); return; }
    // its extent: every block in it, each with its radius
    let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
    for (let i = 0; i < v.pts.length; i += 4) {
      const x = v.pts[i], y = v.pts[i + 1], r = v.pts[i + 2];
      x0 = Math.min(x0, x - r); x1 = Math.max(x1, x + r); y0 = Math.min(y0, y - r); y1 = Math.max(y1, y + r);
    }
    onChoose({ kind: 'precinct', c, v, boxEdges: [x0, y0, 0, x1, y0, 0, x1, y0, 0, x1, y1, 0, x1, y1, 0, x0, y1, 0, x0, y1, 0, x0, y0, 0], view: {
      x: (x0 + x1) / 2, y: (y0 + y1) / 2, halfW: Math.max(0.7 * (x1 - x0), 0.25 * upm), halfH: Math.max(0.7 * (y1 - y0), 0.25 * upm) } });
  });
  fetch(cityUrl).then(r => r.ok ? r.json() : Promise.reject(r.status)).then(data => {
    cities = [...data.cities].sort((a, b) => a[0].localeCompare(b[0]));
    $('goCity').innerHTML += cities.map(([n], i) => `<option value="${i}">${n}</option>`).join('');
  }).catch(e => { console.error('The list of cities did not load', e); $('goCity').hidden = true; });
  $('goCity').addEventListener('change', e => {
    job++; $('goCounty').value = ''; fillPrecincts(null, [], false);
    const city = cities[e.target.value];
    if (!city) { onChoose(null); return; }
    const [name, lon, lat, people] = city, p = P([lon, lat]);
    // about the size a city that many people would cover, at 2,500 people per square mile
    const miles = Math.max(3, 1.7 * Math.sqrt(people / 2500));
    onChoose({ kind: 'city', name, people, view: { x: p.x, y: p.y, halfW: 0, halfH: miles * upm / 2 } });
  });
  return { clear() { job++; $('goCity').value = $('goCounty').value = ''; fillPrecincts(null, [], false); } };
}

// A line about the place. race: the race on screen; votesOf: county -> [dem, rep, total] in that race.
export function describePlace(p, race, votesOf) {
  if (!p) return '';
  if (p.kind === 'city') return `<b>${p.name}</b>: ${fmt(p.people)} people in the 2020 Census`;
  if (p.kind === 'precinct') return `<b>Precinct ${p.v.name}, ${p.c.name} County</b> (box shows its rough extent): ` +
    `2024 U.S. Senate, Allred ${fmt(p.v.d)}, Cruz ${fmt(p.v.r)}, others ${fmt(p.v.o)}`;
  const [dem, rep, tot] = votesOf(p.c), who = party => race.candidates.find(k => k.party === party).last;
  const d = race.chamber ? 'Democrats' : who('DEM'), r = race.chamber ? 'Republicans' : who('REP');
  return `<b>${p.c.name} County</b>: ${fmt(tot)} voters · ` + (tot ? `${d} ${pct(dem, tot)}, ${r} ${pct(rep, tot)}` : 'no votes reported in this race');
}

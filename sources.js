// The Sources page: every state's list of sources, read from the same place its results page reads it (sourcelist.js).
import { STATES } from './state.js';
import { sourceItems } from './sourcelist.js';

const $ = id => document.getElementById(id);
const getJSON = url => fetch(url).then(r => { if (!r.ok) throw new Error(`${url}: ${r.status}`); return r.json(); });
const states = [...STATES].sort((a, b) => a.name.localeCompare(b.name));
const cap = s => s[0].toUpperCase() + s.slice(1);

$('jump').innerHTML = states.map(s => `<a href="#${s.slug}">${s.name}</a>`).join('');

const blocks = await Promise.all(states.map(async s => {
  const head = `<section class="state" id="${s.slug}"><h3>${s.name}</h3>`;
  const links = `<p class="open"><a href="${s.results.href}">Bar view →</a><a href="${s.dots}">Dot view →</a></p>`;
  try {
    const [res, hist] = await Promise.all([getJSON(s.data.results), s.data.history ? getJSON(s.data.history) : null]);
    const m = res.meta;
    return `${head}
      <p class="as-of">${cap(s.authority.includes(s.name) ? s.authority : s.authority.replace(/^the /, `the ${s.name} `))}'s 2026 ${s.returns}, as of ${m.resultsUpdated}. Unofficial until ${s.unofficialUntil}.</p>
      <ol>${sourceItems(s, m, hist?.meta).map(x => `<li>${x}</li>`).join('')}</ol>${links}</section>`;
  } catch (e) {
    console.error(`${s.name}'s sources did not load`, e);
    return `${head}<p class="as-of">This list didn't load. It's also under Sources on the state's results page.</p>${links}</section>`;
  }
}));
$('states').innerHTML = blocks.join('');

// a link straight to a state arrives before its section exists
if (location.hash) document.getElementById(decodeURIComponent(location.hash.slice(1)))?.scrollIntoView();

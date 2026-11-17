// The site's own header, the same on every page: the site's name, which opens the U.S. homepage; a menu of every state that's
// ready; and an Explainers menu of the pages that explain the maps. On a state page it starts the top bar (app.js), and the
// state menu opens the same view of the state chosen. Elsewhere (why.html, shade-by-votes.html, sources.html, the guided
// flights) mountSiteHeader puts it at the top of the page.
import { STATE, STATES } from './state.js';

// The pages that explain the maps, in the order to read them: the idea first, then every state's guided flights and dot tour
// (state.js). The homepage's Start here row (home.js) and the Explainers menu both come from this one list.
export const EXPLAINERS = [
  { href: 'why.html', about: 'Why these maps', title: 'Same election, three maps',
    how: "Flat, 3D and Dots, side by side: why a red county map can still mean a Democratic win" },
  ...STATES.flatMap(s => s.flights.map(f => ({ ...f, about: `${s.name} · ${f.about}` }))),
  ...STATES.filter(s => s.tour).map(s => ({ href: `${s.dots}&tour=1`, about: `${s.name} · 2026 U.S. Senate`,
    title: `${s.name} Population Density Tour`, how: 'One dot for each voter, from the whole state down to single voters. Plays on its own' })),
];

// view: 'results' (a state's map page: Flat, 3D or Dots) or 'page' (any other page, which has no state of its own)
export function createSiteNav(view = 'results') {
  const here = view === 'page' ? null : STATE;
  const nav = document.createElement('div');
  nav.className = 'site-nav';
  const home = document.createElement('a');
  home.className = 'site-home'; home.href = './'; home.textContent = 'How America Votes';
  home.title = 'All states: the U.S. homepage';
  const pick = document.createElement('select');
  pick.id = 'goState'; pick.setAttribute('aria-label', here ? 'Go to another state' : 'Go to a state'); pick.title = pick.getAttribute('aria-label');
  if (!here) pick.add(new Option('Pick a state…', '', true, true));
  for (const s of [...STATES].sort((a, b) => a.name.localeCompare(b.name)))
    pick.add(new Option(s.name, s.slug, s === here, s === here));
  pick.onchange = () => {
    const s = STATES.find(x => x.slug === pick.value);
    if (!s || s === here) return;
    pick.value = here?.slug ?? ''; // so coming back with the browser's Back button finds this page's own choice
    if (!here) { location.href = s.results.href; return; }
    // the same view there: Look, color, By, panel, dot size and race (a race it doesn't have falls back to its default),
    // but not the camera or the tour, which belong to this state's map
    const params = new URLSearchParams(location.search), keep = new URLSearchParams();
    for (const k of ['race', 'by', 'look', 'per', 'color', 'panel']) if (params.get(k)) keep.set(k, params.get(k));
    if (document.body.classList.contains('look-dots') && !keep.has('look')) keep.set('look', 'dots');
    location.href = s.results.href + (`${keep}` ? `?${keep}` : '');
  };
  nav.append(home, pick, explainersMenu());
  return nav;
}

// the Explainers menu: a button that opens a list of links, closed again by a click elsewhere or Escape
function explainersMenu() {
  const menu = document.createElement('details');
  menu.className = 'site-menu';
  const page = location.pathname.split('/').pop() || 'index.html', tour = new URLSearchParams(location.search).has('tour');
  const current = e => e.href.includes('tour=1') ? tour && e.href.startsWith(page) : e.href === page;
  menu.innerHTML = `<summary title="Pages that explain the maps">Explainers</summary><ul>` +
    EXPLAINERS.map(e => `<li><a href="${e.href}"${current(e) ? ' aria-current="page"' : ''}><b>${e.title}</b><span>${e.about}</span></a></li>`).join('') +
    `<li class="sep"><a href="sources.html"${page === 'sources.html' ? ' aria-current="page"' : ''}><b>Sources and credits</b><span>Where every number and shape comes from</span></a></li></ul>`;
  document.addEventListener('pointerdown', e => { if (menu.open && !menu.contains(e.target)) menu.open = false; });
  menu.addEventListener('keydown', e => { if (e.key === 'Escape' && menu.open) { menu.open = false; menu.querySelector('summary').focus(); } });
  return menu;
}

// At the top of a page that isn't a state's map: the header, with the page's own way back (if it has one) after it.
export function mountSiteHeader(target = document.body.firstElementChild) {
  const bar = document.createElement('nav');
  bar.className = 'site-header'; bar.setAttribute('aria-label', 'How America Votes');
  bar.append(createSiteNav('page'));
  target.prepend(bar);
  return bar;
}

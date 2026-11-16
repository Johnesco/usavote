// The way home and to the other states, at the start of a state page's top bar (bar view: app.js; dot view: voters.js): the site's
// name, which opens the U.S. homepage, and a menu of every state that's ready, which opens the same view of the one chosen.
import { STATE, STATES } from './state.js';

// view: 'results' (bar view) or 'dots' (dot view)
export function createSiteNav(view) {
  const nav = document.createElement('div');
  nav.className = 'site-nav';
  const home = document.createElement('a');
  home.className = 'site-home'; home.href = './'; home.textContent = 'How America Votes';
  home.title = 'All states: the U.S. homepage';
  const pick = document.createElement('select');
  pick.id = 'goState'; pick.setAttribute('aria-label', 'Go to another state'); pick.title = 'Go to another state';
  for (const s of [...STATES].sort((a, b) => a.name.localeCompare(b.name)))
    pick.add(new Option(s.name, s.slug, s === STATE, s === STATE));
  pick.onchange = () => {
    const s = STATES.find(x => x.slug === pick.value);
    if (!s || s === STATE) return;
    pick.value = STATE.slug; // so coming back with the browser's Back button finds this page's own state chosen
    // the same view there: Look, color, By, panel, dot size and race (a race it doesn't have falls back to its default),
    // but not the camera or the tour, which belong to this state's map
    const here = new URLSearchParams(location.search), keep = new URLSearchParams();
    for (const k of ['race', 'by', 'look', 'per', 'color', 'panel']) if (here.get(k)) keep.set(k, here.get(k));
    if ((view === 'dots' || document.body.classList.contains('look-dots')) && !keep.has('look')) keep.set('look', 'dots');
    location.href = s.results.href + (`${keep}` ? `?${keep}` : '');
  };
  nav.append(home, pick);
  return nav;
}

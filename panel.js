// The details panel down the left of every state map, the same in the bar view (app.js, the page's <aside>) and the dot view
// (voters.js builds its own). It's for reading: the race, the key, guided flights and sources; the controls are in the bar under
// the map. Both views open with it. Its Hide button gives the map the whole width, Details in the top strip brings it back, and
// ?panel=0 keeps it hidden in the address and across views. On phones the panel sits below the map and stays.
// The guided flights in it are the same list in both views: the state's flights over the county map, then its dot tour.
import { STATE } from './state.js';

// Inside compare.html each view is in a frame: no panel, and the page is marked .framed for style.css.
export const FRAMED = window.parent !== window;
if (FRAMED) document.documentElement.classList.add('framed');

export const panelShown = () => !document.body.classList.contains('panel-hidden');
export const panelParam = () => panelShown() || FRAMED ? '' : '&panel=0';

// The panel's own Hide button, at its top, and the Details button that brings it back, first in the top strip and shown only
// while the panel is hidden. Set from the address; onChange runs after each press (to save the address). Returns the Details button.
export function createPanelToggle(aside, onChange) {
  const hide = document.createElement('button');
  hide.type = 'button'; hide.className = 'panel-close'; hide.textContent = '‹ Hide';
  hide.title = 'Hide this panel, for a wider map';
  aside.prepend(hide);
  const btn = document.createElement('button');
  btn.type = 'button'; btn.id = 'panelToggle'; btn.className = 'panel-toggle'; btn.textContent = 'Details ›';
  btn.title = 'Show the details panel: the race, the key, guided flights and sources';
  const show = on => document.body.classList.toggle('panel-hidden', !on);
  show(!FRAMED && new URLSearchParams(location.search).get('panel') !== '0');
  hide.onclick = () => { show(false); btn.focus(); onChange?.(); };
  btn.onclick = () => { show(true); hide.focus(); onChange?.(); };
  return btn;
}

// The guided flights, as HTML. In the dot view the tour's card is a button that plays it there (tourPlay, with tourRestart
// under it); everywhere else it's a link to the dot view's tour.
export function flightsHtml(tourHere = false) {
  const tour = STATE.tour && { title: `${STATE.name} Population Density Tour`, about: '2026 U.S. Senate',
    how: 'One dot for each voter, from the whole state down to single voters. Plays on its own' };
  const count = STATE.flights.length + (tour ? 1 : 0);
  if (!count) return '';
  const card = f => `<a class="flight" href="${f.href}"><b>▶ ${f.title}</b><span>${f.how}</span></a>`;
  return `<h2>Guided flights</h2><p class="flights-note">${count > 1 ? 'Guided trips' : 'A guided trip'} over the ${(STATE.flights[0] || tour).about} race, separate from the results here.</p>` +
    STATE.flights.map(card).join('') +
    (!tour ? '' : tourHere
      ? `<button type="button" class="flight" id="tourPlay"><b id="tourName">▶ ${tour.title}</b><span>${tour.how}</span></button>` +
        `<button type="button" class="ghost" id="tourRestart" hidden>Start the tour over</button>`
      : card({ ...tour, href: `${STATE.dots}?tour=1` }));
}

// ---------- compare (compare.html) ----------
// The page that shows two views side by side, each in a frame: a link to it with this view and the other as they are now.
export const compareHref = (a, b) => `compare.html?a=${encodeURIComponent(a)}&b=${encodeURIComponent(b)}`;
// In a frame, tell compare.html where this view's camera is, and follow where it says the other one went: get() and set() use
// { x, y, d }, the map point in the middle and the camera's distance, in the units both views share (as ?at= carries them).
// Both views have the same lens, but their maps aren't the same height on screen, so the distance goes between them per pixel
// of height (height(): the map's height in pixels), to show the same miles per pixel on both sides.
// After following, the camera's new place isn't sent back, so the two don't echo each other.
export function followCamera(get, set, height) {
  if (!FRAMED) return;
  const key = c => c && [c.x / c.d * 300, c.y / c.d * 300, Math.log(c.d) * 300].map(Math.round).join();
  let last = '';
  const tick = () => {
    const c = get(), k = key(c);
    if (c && k !== last) { last = k; parent.postMessage({ type: 'cam', x: c.x, y: c.y, d: c.d / height() }, location.origin); }
    requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
  addEventListener('message', e => {
    if (e.origin !== location.origin || e.source !== parent || e.data?.type !== 'setCam') return;
    const { x, y, d } = e.data;
    if (![x, y, d].every(Number.isFinite) || d <= 0) return;
    set({ x, y, d: d * height() }); last = key(get());
  });
}

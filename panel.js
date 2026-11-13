// The details panel down the left of every state map, the same in the bar view (app.js, the page's <aside>) and the dot view
// (voters.js builds its own). It's for reading: the race, the key, guided flights and sources; the controls are in the bar under
// the map. Both views open with it. Its Hide button gives the map the whole width, Details in the top strip brings it back, and
// ?panel=0 keeps it hidden in the address and across views. On phones the panel sits below the map and stays.
// The guided flights in it are the same list in both views: the state's flights over the county map, then its dot tour.
import { STATE } from './state.js';

export const panelShown = () => !document.body.classList.contains('panel-hidden');
export const panelParam = () => panelShown() ? '' : '&panel=0';

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
  show(new URLSearchParams(location.search).get('panel') !== '0');
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

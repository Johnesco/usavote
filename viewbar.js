// The control bar along the bottom of every state map (app.js). It says what the map is in three choices:
//   Look   Flat · 3D · Dots     Flat and 3D are the bars; Dots is one dot for each voter (dotlook.js), on the same page
//   By     County · Precinct · District, whichever the state has
//   Color  Vote share · Vote lead · Vote mix, with a ? link to the page that explains all three. Flat (and Dots, turned off) only
//   Shape  County shape · Square, in Color's place in 3D: each column in its county's shape, or every one the same small square
// then, with Dots, "1 dot =", and Whole state. A choice that doesn't fit what's on screen is turned off, and pressing it says why (app.js).
import { STATE } from './state.js';
import { LEAD_PAGE } from './colors.js';

export const HAS_PRECINCTS = !!STATE.data.precinctShapes;
export const HAS_DISTRICTS = Object.keys(STATE.data.districts || {}).length > 0;
export const NOT_DOTS_BY = 'Dots are placed down to census blocks. Precinct and District are for Flat and 3D';
export const NOT_DOTS_COLOR = 'Dots are colored by party. Vote share, Vote lead and Vote mix are for the county map';
export const PERS = [1, 10, 100, 1000]; // voters a dot can stand for
export const SHAPE_TITLES = { county: "Each county's column has the county's own shape, so a big county makes a big column",
  square: 'Every column is the same small square, standing on its county, so only votes make a column stand out' };

const fmt = n => n.toLocaleString('en-US');
// The ? link says which map it came from (?from=texas.html?race=...), so that page can lead back to it. The address changes as
// the reader picks a race, Look or color, so it's read again just before the link is followed.
const helpHref = () => `${LEAD_PAGE}?from=${encodeURIComponent(location.pathname.split('/').pop() + location.search)}`;
for (const ev of ['pointerdown', 'click', 'keydown', 'contextmenu'])
  document.addEventListener(ev, e => { const a = e.target.closest?.('#leadHelp'); if (a) a.href = helpHref(); }, true);

// The bar's groups, to put in a .controls box.
export function viewBarGroups() {
  const group = (label, inner, cls = '', id = '') =>
    `<div class="vb-group${cls}"${id ? ` id="${id}"` : ''}><span class="vb-label">${label}</span><div class="seg" role="group" aria-label="${label}">${inner}</div></div>`;
  const look = `<button type="button" id="viewFlat" aria-pressed="true" title="The flat map, seen from above">Flat</button>` +
    `<button type="button" id="view3d" aria-pressed="false" title="Columns raised by votes cast">3D</button>` +
    `<button type="button" id="dotLink" aria-pressed="false" title="One dot for each voter">Dots</button>`;
  const by = `<button type="button" id="byCounty" aria-pressed="true">County</button>` +
    (HAS_PRECINCTS ? `<button type="button" id="byPrecinct" aria-pressed="false">Precinct</button>` : '') +
    (HAS_DISTRICTS ? `<button type="button" id="byDistrict" aria-pressed="false" aria-disabled="true" title="Checking for district lines…">District</button>` : '');
  const color = `<button type="button" id="colorShare" aria-pressed="true">Vote share</button>` +
    `<button type="button" id="leadColor" aria-pressed="false">Vote lead</button>` +
    `<button type="button" id="mixColor" aria-pressed="false">Vote mix</button>` +
    `<a href="${helpHref()}" id="leadHelp" title="What do the three colors show?" aria-label="What do the three colors show?">?</a>`;
  const per = `<div class="vb-group dots-only"><label class="vb-label keep" for="per">1 dot =</label>
    <select id="per" title="How many voters each dot stands for">${PERS.map(n => `<option value="${n}">${fmt(n)} voter${n > 1 ? 's' : ''}</option>`).join('')}</select></div>`;
  const shape = `<button type="button" id="shapeCounty" aria-pressed="true" title="${SHAPE_TITLES.county}">County shape</button>` +
    `<button type="button" id="shapeSquare" aria-pressed="false" title="${SHAPE_TITLES.square}">Square</button>`;
  // (Color or Shape shows, by the Look: app.js's updateMode)
  return group('Look', look) + group('By', by) + group('Color', color, '', 'gColor') + group('Shape', shape, '', 'gShape').replace('>', ' hidden>') + per;
}

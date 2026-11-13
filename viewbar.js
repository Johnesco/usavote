// The control bar along the bottom of every state map (app.js). It says what the map is in three choices:
//   Look   Flat · 3D · Dots     Flat and 3D are the bars; Dots is one dot for each voter (dotlook.js), on the same page
//   By     County · Precinct · District, whichever the state has
//   Color  Share · Vote lead, with a ? link to the page that explains vote-lead color
// then, with Dots, "1 dot =", and Whole state. A choice that doesn't fit what's on screen is turned off, with the reason as its title.
import { STATE } from './state.js';
import { LEAD_PAGE } from './colors.js';

export const HAS_PRECINCTS = !!STATE.data.precinctShapes;
export const HAS_DISTRICTS = Object.keys(STATE.data.districts || {}).length > 0;
export const NOT_DOTS_BY = 'Dots are placed down to census blocks. Precinct and District are for Flat and 3D';
export const NOT_DOTS_COLOR = 'Dots are colored by party. Share and Vote lead are for Flat and 3D';
export const PERS = [1, 10, 100, 1000]; // voters a dot can stand for

const fmt = n => n.toLocaleString('en-US');

// The bar's groups, to put in a .controls box.
export function viewBarGroups() {
  const group = (label, inner, cls = '') =>
    `<div class="vb-group${cls}"><span class="vb-label">${label}</span><div class="seg" role="group" aria-label="${label}">${inner}</div></div>`;
  const look = `<button type="button" id="viewFlat" aria-pressed="true" title="The flat map, seen from above">Flat</button>` +
    `<button type="button" id="view3d" aria-pressed="false" title="Columns raised by votes cast">3D</button>` +
    `<button type="button" id="dotLink" aria-pressed="false" title="One dot for each voter">Dots</button>`;
  const by = `<button type="button" id="byCounty" aria-pressed="true">County</button>` +
    (HAS_PRECINCTS ? `<button type="button" id="byPrecinct" aria-pressed="false">Precinct</button>` : '') +
    (HAS_DISTRICTS ? `<button type="button" id="byDistrict" aria-pressed="false" disabled>District</button>` : '');
  const color = `<button type="button" id="colorShare" aria-pressed="true">Share</button>` +
    `<button type="button" id="leadColor" aria-pressed="false">Vote lead</button>` +
    `<a href="${LEAD_PAGE}" id="leadHelp" title="What is vote-lead color?" aria-label="What is vote-lead color?">?</a>`;
  const per = `<div class="vb-group dots-only"><label class="vb-label keep" for="per">1 dot =</label>
    <select id="per" title="How many voters each dot stands for">${PERS.map(n => `<option value="${n}">${fmt(n)} voter${n > 1 ? 's' : ''}</option>`).join('')}</select></div>`;
  return group('Look', look) + group('By', by) + group('Color', color) + per;
}

// The control bar along the bottom of every map, the same in the bar view (app.js) and the dot view (voters.js). It says what
// the map is in three choices:
//   Look   Flat · 3D · Dots     Flat and 3D are the bar view; Dots is the dot view, its own page
//   By     County · Precinct · District, whichever the state has
//   Color  Share · Vote lead, with a ? link to the page that explains vote-lead color
// then Whole state. A choice that doesn't fit what's on screen is turned off, with the reason as its title.
//
// The buttons keep the ids the two views already use (viewFlat, view3d, dotLink, byCounty, byPrecinct, byDistrict, leadColor),
// so each view wires them up as before. In the dot view, Flat and 3D are links back to the bar view, which voters.js fills in.
import { STATE } from './state.js';
import { LEAD_PAGE } from './colors.js';

export const HAS_PRECINCTS = !!STATE.data.precinctShapes;
export const HAS_DISTRICTS = Object.keys(STATE.data.districts || {}).length > 0;

const NOT_DOTS_BY = 'Dots are placed down to census blocks. Precinct and District are for Flat and 3D';
const NOT_DOTS_COLOR = 'Dots are colored by party. Share and Vote lead are for Flat and 3D';

// view: 'bar' or 'dots'. Returns the bar's groups, to put in a .controls box.
export function viewBarGroups(view) {
  const dots = view === 'dots';
  const off = reason => dots ? ` disabled title="${reason}"` : '';
  const group = (label, inner) =>
    `<div class="vb-group"><span class="vb-label">${label}</span><div class="seg" role="group" aria-label="${label}">${inner}</div></div>`;
  const look = dots
    ? `<a id="viewFlat" href="${STATE.results.href}" title="The flat map, colored by county">Flat</a>` +
      `<a id="view3d" href="${STATE.results.href}" title="Columns raised by votes cast">3D</a>` +
      `<button type="button" id="dotLink" aria-pressed="true" title="One dot for each voter">Dots</button>`
    : `<button type="button" id="viewFlat" aria-pressed="true" title="The flat map, seen from above">Flat</button>` +
      `<button type="button" id="view3d" aria-pressed="false" title="Columns raised by votes cast">3D</button>` +
      `<a id="dotLink" href="${STATE.dots}" title="One dot for each voter, on its own page">Dots</a>`;
  const by = `<button type="button" id="byCounty" aria-pressed="true"${off(NOT_DOTS_BY)}>County</button>` +
    (HAS_PRECINCTS ? `<button type="button" id="byPrecinct" aria-pressed="false"${off(NOT_DOTS_BY)}>Precinct</button>` : '') +
    (HAS_DISTRICTS ? `<button type="button" id="byDistrict" aria-pressed="false" disabled${dots ? ` title="${NOT_DOTS_BY}"` : ''}>District</button>` : '');
  const color = `<button type="button" id="colorShare" aria-pressed="true"${off(NOT_DOTS_COLOR)}>Share</button>` +
    `<button type="button" id="leadColor" aria-pressed="false"${off(NOT_DOTS_COLOR)}>Vote lead</button>` +
    `<a href="${LEAD_PAGE}" id="leadHelp" title="What is vote-lead color?" aria-label="What is vote-lead color?">?</a>`;
  return group('Look', look) + group('By', by) + group('Color', color);
}

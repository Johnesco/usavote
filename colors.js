// The county map's color scales, shared by the bar view (app.js, map3d.js), the Shade by Votes page
// (shade-by-votes.js) and its image (scripts/shade-by-votes-panels.html).
//
// Percentage color, the usual one: the winner's color, shaded by the winner's share of the county's vote in 10-point bands.
// Vote-lead color: the winner's color, shaded by the county's lead in votes (winner minus runner-up), from pale up to the
// biggest lead in the race, on a square-root scale (as a circle's area is on a bubble map), so places where few people
// voted fade out whatever their percentage.
export const BINS = [40, 50, 60, 70, 80, 90];
export const BAND_LABELS = ['<50%', '50–60', '60–70', '70–80', '80–90', '90+'];
export const REP_C = ['#ffb2b2', '#e27f7f', '#d75d5d', '#d72f30', '#c21b18', '#a80000'];
export const DEM_C = ['#a5b0ff', '#7996e2', '#6674de', '#584cde', '#3933e5', '#0d0596'];
export const PALE = '#ece7e1';
export const LEAD_PAGE = 'shade-by-votes.html'; // where the three colors are explained

const rgb = hex => [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16));
const hex = c => '#' + c.map(v => Math.round(v).toString(16).padStart(2, '0')).join('');

// 0 to 1: how dark a lead is, against the biggest lead in the race
export const leadT = (lead, maxLead) => maxLead > 0 ? Math.sqrt(Math.min(1, lead / maxLead)) : 0;
// the vote-lead color, as [r, g, b] 0 to 255: pale, then the six shades of the percentage scale, evenly spaced
export function leadRGB(dWon, lead, maxLead) {
  const stops = [PALE, ...(dWon ? DEM_C : REP_C)].map(rgb), x = leadT(lead, maxLead) * (stops.length - 1);
  const i = Math.min(stops.length - 2, Math.floor(x)), f = x - i;
  return stops[i].map((v, k) => v + (stops[i + 1][k] - v) * f);
}
export const leadHex = (dWon, lead, maxLead) => hex(leadRGB(dWon, lead, maxLead));
// the key: a CSS gradient for each party, and round numbers to mark on it
export const leadGradient = cols => `linear-gradient(90deg, ${[PALE, ...cols].map((c, i, a) => `${c} ${(100 * i / (a.length - 1)).toFixed(1)}%`).join(', ')})`;
export function leadTicks(maxLead) {
  const nice = [100, 1000, 10000, 50000, 150000, 500000, 1500000].filter(v => v < maxLead * 0.75);
  const pick = nice.slice(-3); // the three biggest that fit, so the marks don't crowd near zero
  return [0, ...pick, maxLead];
}
// Share + size color (value by alpha): two things, each in a channel of its own.
//   The split is the hue: the Democratic and Republican votes mixed, from blue through purple to red, by the Democrat's
//   share of the two (others left out). The mix runs along a circle of hues in OKLCH, a color space made to match how
//   people see, at one lightness and one strength all the way, so an even county is a clear purple, not a muddy one, and
//   no split looks darker or louder than another.
//   The size is how solid the color is: a county is drawn see-through over the map's dark background, the more so the fewer
//   votes it cast, against the race's biggest county, on the same square-root scale as Vote lead. Since every split has
//   the same lightness, dim only ever means few votes; and never fully see-through, so even the smallest shows its hue.
export const MAP_BG = '#0e1116';            // the map's background (style.css --bg, app.js scene.background)
const MIX_L = 0.6, MIX_C = 0.215;           // lightness and strength: the most that stays inside sRGB at every hue below
const H_DEM = 265, H_REP = 27 + 360;        // blue, and red, going the short way round through purple (about 326)
export const MIX_FLOOR = 0.4;               // how solid the smallest county is: dim, but its hue still shows
export const mixT = (total, maxTotal) => MIX_FLOOR + (1 - MIX_FLOOR) * (maxTotal > 0 ? Math.sqrt(Math.min(1, total / maxTotal)) : 0);
// the hue for a Democratic share of the two-party vote, 0 to 1, as [r, g, b] 0 to 255
export function splitRGB(dShare) {
  const h = (H_REP + (H_DEM - H_REP) * dShare) * Math.PI / 180, a = MIX_C * Math.cos(h), b = MIX_C * Math.sin(h);
  const l = (MIX_L + 0.3963377774 * a + 0.2158037573 * b) ** 3, m = (MIX_L - 0.1055613458 * a - 0.0638541728 * b) ** 3,
    s = (MIX_L - 0.0894841775 * a - 1.2914855480 * b) ** 3;
  const lin = [4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s, -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
    -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s];
  return lin.map(v => { v = Math.min(1, Math.max(0, v)); return 255 * (v <= 0.0031308 ? 12.92 * v : 1.055 * v ** (1 / 2.4) - 0.055); });
}
// a county's color: its split's hue, laid over the map's background as solid as its votes make it
export function mixRGB(dem, rep, total, maxTotal) {
  const c = splitRGB(dem + rep > 0 ? dem / (dem + rep) : 0.5), bg = rgb(MAP_BG), t = mixT(total, maxTotal);
  return c.map((v, k) => bg[k] + (v - bg[k]) * t);
}
export const mixHex = (dem, rep, total, maxTotal) => hex(mixRGB(dem, rep, total, maxTotal));
// the key's columns: the Democrat's share of the two-party vote, all Republican to all Democratic
export const MIX_SPLITS = [0, 0.2, 0.4, 0.5, 0.6, 0.8, 1];
export const MIX_SPLIT_LABELS = ['100 R', '80 R', '60 R', 'Even', '60 D', '80 D', '100 D'];
// the key's rows: votes cast at evenly spaced steps of solidness, biggest first
export const mixRows = maxTotal => [1, 4 / 9, 1 / 9, 0].map(f => f * maxTotal);
export const tickLabel = v => v === 0 ? '0' : v >= 1e6 ? (v / 1e6).toFixed(1).replace(/\.0$/, '') + 'M' : v >= 1000 ? Math.round(v / 1000) + 'K' : String(v);

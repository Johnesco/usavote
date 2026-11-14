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
// Share + size color (value by alpha): the percentage color, faded toward a neutral gray by how few votes the county cast,
// against the race's biggest county, on the same square-root scale. It fades toward gray, not the dark page, so a small
// county never turns dark and reads as a landslide; and never all the way, so even the smallest still shows who won it.
export const FADE_GRAY = '#7c7f87';
export const MIX_FLOOR = 0.22; // how much color the smallest county keeps
export const mixT = (total, maxTotal) => MIX_FLOOR + (1 - MIX_FLOOR) * (maxTotal > 0 ? Math.sqrt(Math.min(1, total / maxTotal)) : 0);
export function mixRGB(pctHex, total, maxTotal) {
  const g = rgb(FADE_GRAY), t = mixT(total, maxTotal);
  return rgb(pctHex).map((v, k) => g[k] + (v - g[k]) * t);
}
export const mixHex = (pctHex, total, maxTotal) => hex(mixRGB(pctHex, total, maxTotal));
// the key's rows: votes cast at evenly spaced fades, biggest first, as round-ish numbers
export const mixRows = maxTotal => [1, 4 / 9, 1 / 9, 0].map(f => f * maxTotal);
export const tickLabel = v => v === 0 ? '0' : v >= 1e6 ? (v / 1e6).toFixed(1).replace(/\.0$/, '') + 'M' : v >= 1000 ? Math.round(v / 1000) + 'K' : String(v);

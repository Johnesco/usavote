// Places one dot per voter (or per `per` voters) for dots.js. Each county's dots are scattered at random inside the
// county's shape, and each dot also gets a height inside the county's raised column: the runner-up's voters at the
// bottom, third-party and write-in voters in the middle, the winner's on top, as the stacked columns are drawn.
// The dots are written in random party order, so on a flat map no party is always drawn over the others.
//
// In:  { counties: [{ tris: Float32Array (x0,y0,x1,y1,x2,y2 per triangle, map units), w: Float32Array (optional weight per
//        triangle: dots land in a triangle in proportion to it; without it, in proportion to area), dem, rep, other, target, delay }],
//        per, seed, job }
//      or, instead of tris/w, units: Float32Array, 6 per place (x, y, radius in map units, expected Democratic, Republican and
//        other votes there). Each party's dots are shared among the places in proportion to that party's expected votes, and
//        scattered around each place with a soft spread about its size, so a place's dots carry its own party mix.
//      A separate { land } message (dots.js, loadLand) gives the grid of where the Census counted anyone; a dot placed by
//        units that lands on an empty cell gets a new spot around the same place.
// Out: { buf: Int16Array, 4 per dot: x, y (fixed point around the county's center), height * Z, party * 256 + county index;
//        table: Float32Array, 4 per county: center x, center y, map units per x/y step, rise delay;
//        counts: [dem, rep, other] dots; job;
//        tiles: { n, x0, y0, size, sides, starts }: the dots are sorted into layers (see intoTiles), one per entry of `sides` and a
//        last one for the rest, and each layer into an n x n grid of square tiles, row by row. In layer l, with w = n * n + 1, a tile's
//        dots are starts[l * w + row * n + col] up to starts[l * w + row * n + col + 1]. }
// party: 0 = Democratic, 1 = Republican, 2 = everyone else.
const Z = 64; // the tallest column is 420 map units
const STEPS = 32000; // x/y steps from a county's center to its farthest edge (Int16 holds ±32767)
const SPREAD = 0.75; // a place's spread (one standard deviation), as a share of its radius
const TRIES = 16; // spots tried for a dot before settling on its place's center, which is in the block itself
const GRID = 256; // tiles along each side of the map: about 4 map units, or 3 miles, across in Texas
// For leaving out dots from far away, level by level (intoTiles): cells along each side of a tile, and the most dots kept in a cell.
// The caps rise as well as the cells shrinking, so each step closer is truer to the whole than the last.
const SIDES = [4, 8, 16, 32], CAPS = [4, 4, 8, 16];

let land = null;
const lived = (x, y) => {
  const gx = Math.floor(land.ox + x * land.sx), gy = Math.floor(land.oy + y * land.sy);
  if (gx < 0 || gy < 0 || gx >= land.w || gy >= land.h) return false;
  const i = gy * land.w + gx;
  return (land.bits[i >> 3] >> (i & 7) & 1) === 1;
};

// small fast seeded random (mulberry32), so a race always draws the same dots
function rng(seed) {
  return () => {
    seed |= 0; seed = seed + 0x6D2B79F5 | 0;
    let t = Math.imul(seed ^ seed >>> 15, 1 | seed);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}

// Sort the dots for drawing. First into tiles, row by row, so the page can draw only the ones on screen. Then, inside the buffer, into
// layers, so a far-off view can leave out dots that couldn't be seen anyway: a pixel shows only the last dot drawn on it, and with the
// whole state on screen about 99 land on each. Each level cuts a tile into cells and keeps at most so many dots a cell, so crowded
// places lose only dots piled on others, and an empty county keeps all of its own. Each level holds all of the one before it, so coming
// closer only ever adds dots; past the last level, every dot is drawn. The dots are looked at in big even steps through the tile, not
// in the order placed, so what's kept in a cell is a fair sample of the places and parties there.
// (A dot among the first few in a big cell is among the first few in the smaller cell it's in, which is why the levels nest.)
function intoTiles(buf, table) {
  const N = buf.length / 4, cell = new Uint16Array(N); // GRID * GRID cells fit in 16 bits
  // the grid covers every county's reach (a county with nothing to place has no center, and fails these comparisons)
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (let c = 0; c < table.length; c += 4) {
    const r = table[c + 2] * (STEPS + 1);
    if (table[c] - r < x0) x0 = table[c] - r; if (table[c] + r > x1) x1 = table[c] + r;
    if (table[c + 1] - r < y0) y0 = table[c + 1] - r; if (table[c + 1] + r > y1) y1 = table[c + 1] + r;
  }
  const size = Math.max(x1 - x0, y1 - y0, 1e-6) / GRID, tile = new Uint32Array(GRID * GRID + 1), last = GRID - 1;
  for (let i = 0, j = 0; i < N; i++, j += 4) {
    const c = (buf[j + 3] & 255) * 4, step = table[c + 2];
    let col = (table[c] + buf[j] * step - x0) / size | 0, row = (table[c + 1] + buf[j + 1] * step - y0) / size | 0;
    col = col < 0 ? 0 : col > last ? last : col; row = row < 0 ? 0 : row > last ? last : row;
    const k = cell[i] = row * GRID + col;
    tile[k + 1]++;
  }
  let biggest = 0;
  for (let i = 0; i < GRID * GRID; i++) { biggest = Math.max(biggest, tile[i + 1]); tile[i + 1] += tile[i]; }
  const next = tile.slice(), out = new Int16Array(buf.length);
  for (let i = 0, j = 0; i < N; i++, j += 4) {
    const o = next[cell[i]]++ * 4;
    out[o] = buf[j]; out[o + 1] = buf[j + 1]; out[o + 2] = buf[j + 2]; out[o + 3] = buf[j + 3];
  }
  // which layer each dot belongs to: the first level that keeps it, or the last layer if none does
  const L = SIDES.length, layer = new Uint8Array(N);
  const top = SIDES[L - 1], fine = new Uint16Array(biggest); // each of a tile's dots' smallest cell
  const gcd = (x, y) => { while (y) [x, y] = [y, x % y]; return x; };
  const firstCell = [];
  let cells = 0;
  for (const s of SIDES) { firstCell.push(cells); cells += s * s; }
  const seen = new Uint8Array(cells), row = GRID * GRID + 1, starts = new Uint32Array((L + 1) * row);
  for (let t = 0; t < GRID * GRID; t++) {
    const a = tile[t], n = tile[t + 1] - a;
    if (!n) continue;
    if (n <= CAPS[0]) { starts[t + 1] += n; continue; } // too few to reach any cap: all in the first layer
    const tx = x0 + (t % GRID) * size, ty = y0 + (t / GRID | 0) * size;
    seen.fill(0);
    for (let q = 0, j = a * 4; q < n; q++, j += 4) {
      const c = (out[j + 3] & 255) * 4, step = table[c + 2];
      let fx = (table[c] + out[j] * step - tx) / size * top | 0, fy = (table[c + 1] + out[j + 1] * step - ty) / size * top | 0;
      fx = fx < 0 ? 0 : fx >= top ? top - 1 : fx; fy = fy < 0 ? 0 : fy >= top ? top - 1 : fy;
      fine[q] = fy * top + fx;
    }
    let by = Math.round(n * 0.618034) || 1, i = 0, got = 0; // the golden ratio's steps never bunch up, and visit every dot once
    while (gcd(by, n) !== 1) by++;
    for (let q = 0; q < n; q++, i = (i + by) % n) {
      const f = fine[i], fx = f % top, fy = (f - fx) / top;
      // from the smallest cells up: once one is full, so are the bigger ones around it
      got = L;
      for (let l = L - 1; l >= 0; l--) {
        const s = SIDES[l], d = top / s, k = firstCell[l] + (fy / d | 0) * s + (fx / d | 0);
        if (seen[k] >= CAPS[l]) break;
        seen[k]++; got = l;
      }
      layer[a + i] = got; starts[got * row + t + 1]++;
    }
  }
  // counts to positions in the buffer: layer by layer, and in each layer tile by tile
  let at = 0;
  for (let l = 0; l <= L; l++) {
    const o = l * row;
    starts[o] = at;
    for (let t = 0; t < GRID * GRID; t++) starts[o + t + 1] += starts[o + t];
    at = starts[o + GRID * GRID];
  }
  const place = starts.slice();
  for (let t = 0; t < GRID * GRID; t++) for (let i = tile[t]; i < tile[t + 1]; i++) {
    const o = place[layer[i] * row + t]++ * 4, j = i * 4;
    buf[o] = out[j]; buf[o + 1] = out[j + 1]; buf[o + 2] = out[j + 2]; buf[o + 3] = out[j + 3];
  }
  return { tiles: { n: GRID, x0, y0, size, sides: SIDES, starts } };
}

onmessage = ({ data }) => {
  if (data.land) { land = data.land; return; }
  const { counties, per, seed, job } = data;
  const n = c => [Math.round(c.dem / per), Math.round(c.rep / per), Math.round(c.other / per)];
  let total = 0;
  for (const c of counties) total += n(c).reduce((a, b) => a + b, 0);
  const buf = new Int16Array(total * 4), table = new Float32Array(counties.length * 4), counts = [0, 0, 0];
  const rand = rng(seed);
  let o = 0;
  counties.forEach((c, ci) => {
    const t = c.tris || [], T = t.length / 6, u = c.units, U = u ? u.length / 6 : 0;
    // center and reach of the county, for its fixed-point coordinates
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    if (u) for (let i = 0; i < u.length; i += 6) { // as far as a place's spread can reach
      const reach = 2.5 * SPREAD * u[i + 2];
      x0 = Math.min(x0, u[i] - reach); x1 = Math.max(x1, u[i] + reach);
      y0 = Math.min(y0, u[i + 1] - reach); y1 = Math.max(y1, u[i + 1] + reach);
    }
    else for (let i = 0; i < t.length; i += 2) {
      x0 = Math.min(x0, t[i]); x1 = Math.max(x1, t[i]); y0 = Math.min(y0, t[i + 1]); y1 = Math.max(y1, t[i + 1]);
    }
    const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2, step = Math.max(x1 - x0, y1 - y0, 1e-6) / 2 / STEPS;
    table.set([cx, cy, step, c.delay || 0], ci * 4);
    const left = n(c);
    let all = left[0] + left[1] + left[2];
    if (!all || !(T || U)) return;
    // where each party's layer starts in the column, bottom to top: runner-up, others, winner
    const base = c.dem > c.rep ? [left[1] + left[2], 0, left[1]] : [0, left[0] + left[2], left[0]];
    const used = [0, 0, 0], size = all;
    const put = (x, y, party) => {
      const z = c.target * (base[party] + used[party]++ + rand()) / size;
      buf[o++] = Math.round((x - cx) / step); buf[o++] = Math.round((y - cy) / step); buf[o++] = Math.round(z * Z);
      buf[o++] = party * 256 + ci;
    };
    if (u) {
      // whole dots per place for each party, by systematic rounding: in proportion to the expected votes, and adding up
      // exactly to the county's total for that party
      const k = new Int32Array(U * 3);
      for (let p = 0; p < 3; p++) {
        if (!left[p]) continue;
        let sum = 0;
        for (let i = 0; i < U; i++) sum += u[i * 6 + 3 + p];
        // no expected votes anywhere for this party: share by all expected votes instead
        const e = sum > 0 ? i => u[i * 6 + 3 + p] : i => u[i * 6 + 3] + u[i * 6 + 4] + u[i * 6 + 5];
        if (!(sum > 0)) for (let i = 0; i < U; i++) sum += e(i);
        let acc = rand(), prev = Math.floor(acc), given = 0;
        for (let i = 0; i < U; i++) {
          acc += e(i) * left[p] / sum;
          const f = Math.floor(acc);
          // the last place takes whatever rounding left over, so the total is exact
          k[i * 3 + p] = i === U - 1 ? Math.max(0, left[p] - given) : Math.min(f - prev, left[p] - given);
          given += k[i * 3 + p]; prev = f;
        }
      }
      for (let p = 0; p < 3; p++) counts[p] += left[p];
      for (let i = 0; i < U; i++) {
        const kk = [k[i * 3], k[i * 3 + 1], k[i * 3 + 2]];
        let m = kk[0] + kk[1] + kk[2];
        const px = u[i * 6], py = u[i * 6 + 1], pr = u[i * 6 + 2];
        while (m) { // random party order within the place, then a uniform point in its circle
          const r0 = rand() * m;
          const party = r0 < kk[0] ? 0 : r0 < kk[0] + kk[1] ? 1 : 2;
          kk[party]--; m--;
          // a soft spread around the place (a bell curve, cut off at 2.5 spreads) rather than a hard-edged circle, so
          // neighboring places blend into each other instead of showing as separate discs
          let x, y, tries = 0, ok;
          do {
            let g;
            do g = Math.sqrt(-2 * Math.log(1 - rand())); while (g > 2.5);
            const rr = SPREAD * pr * g, a = 2 * Math.PI * rand();
            x = px + rr * Math.cos(a); y = py + rr * Math.sin(a);
            ok = !land || lived(x, y);
          } while (!ok && ++tries < TRIES);
          if (!ok) { x = px; y = py; }
          put(x, y, party);
        }
      }
      return;
    }
    // cumulative triangle weights (or areas), so a dot lands in a triangle in proportion to its weight
    const cum = new Float64Array(T), w = c.w;
    let acc = 0;
    for (let i = 0; i < T; i++) {
      const j = i * 6;
      acc += w ? w[i] : Math.abs((t[j + 2] - t[j]) * (t[j + 5] - t[j + 1]) - (t[j + 4] - t[j]) * (t[j + 3] - t[j + 1])) / 2;
      cum[i] = acc;
    }
    if (!(acc > 0)) return;
    for (let p = 0; p < 3; p++) counts[p] += left[p];
    while (all) {
      // draw a party at random from the voters still to place (without replacement)
      const r0 = rand() * all;
      const party = r0 < left[0] ? 0 : r0 < left[0] + left[1] ? 1 : 2;
      left[party]--; all--;
      // pick a triangle (binary search on the cumulative areas), then a uniform point in it
      const r = rand() * acc;
      let lo = 0, hi = T - 1;
      while (lo < hi) { const m = (lo + hi) >> 1; if (cum[m] < r) lo = m + 1; else hi = m; }
      const j = lo * 6;
      let a = rand(), b = rand();
      if (a + b > 1) { a = 1 - a; b = 1 - b; }
      const x = t[j] + a * (t[j + 2] - t[j]) + b * (t[j + 4] - t[j]);
      const y = t[j + 1] + a * (t[j + 3] - t[j + 1]) + b * (t[j + 5] - t[j + 1]);
      put(x, y, party);
    }
  });
  const { tiles } = intoTiles(buf, table);
  postMessage({ buf, table, counts, job, tiles }, [buf.buffer, table.buffer, tiles.starts.buffer]);
};

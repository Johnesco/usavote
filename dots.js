// One dot per voter, for the dot view (voters.js).
// dots-worker.js places the dots; this module turns them into one THREE.Points drawn by a small shader.
//
// We only know how many people voted in each county, not where they live, so each county's voters are placed by precinct
// and census block (loadPrecincts, precinctUnits), and kept off land where the 2020 Census counted no one (loadLand).
// Each dot also knows its place in a raised column (uniforms.uP: 0 = flat map, 1 = raised). No page raises them today:
// the dots stay flat, and only the county map (app.js) has 3D columns.
import * as THREE from 'three';

export const DOT_C = { dem: '#6c7dff', rep: '#ff3b3b', other: '#9aa6b8' };

// A county's area as a flat list of triangles (x0,y0,x1,y1,x2,y2 ...), in map units, from its THREE.Shapes.
export function countyTris(shapes) {
  const tris = [];
  for (const s of shapes) {
    const { shape, holes } = s.extractPoints(1);
    const faces = THREE.ShapeUtils.triangulateShape(shape, holes); // drops repeated end points in place
    const pts = [...shape, ...holes.flat()];
    for (const [a, b, d] of faces) tris.push(pts[a].x, pts[a].y, pts[b].x, pts[b].y, pts[d].x, pts[d].y);
  }
  return new Float32Array(tris);
}

// Where each county's voters live and how each neighborhood votes, from data/precincts.json.gz (scripts/build_precincts.py):
// every 2024 voting district (VTD) with its 2024 U.S. Senate votes and the census blocks inside it, each with its adults
// and a circle the size of its land area. Returns Map(fips -> { vtds: [{ d, r, o, name (its code or codes), adults, pts: Float32Array (x, y,
// radius in map units, adults per block) }], D, R, O (county totals, 2024), adults }), and hot: each county's most
// crowded spot, [lon, lat, adults per square mile within half a mile].
// The file is stored gzipped to keep the site small; it's unzipped here unless the server already did (as when it's sent
// with Content-Encoding: gzip).
export async function fetchJsonGz(url) {
  const res = await fetch(url); if (!res.ok) throw new Error(res.status);
  const buf = new Uint8Array(await res.arrayBuffer());
  const zipped = buf[0] === 0x1f && buf[1] === 0x8b;
  const text = zipped ? await new Response(new Blob([buf]).stream().pipeThrough(new DecompressionStream('gzip'))).text()
    : new TextDecoder().decode(buf);
  return JSON.parse(text);
}
export async function loadPrecincts(P, url = 'data/precincts.json.gz', landUrl = 'data/landmask.bin.gz') {
  const data = await fetchJsonGz(url);
  // map units per meter, from 0.1 degree of latitude (about 11.1 km) in the middle of the state
  const upm = P([-99.5, 31]).distanceTo(P([-99.5, 31.1])) / 11113;
  const out = new Map();
  for (const [fips, vtds] of Object.entries(data.counties)) {
    let D = 0, R = 0, O = 0;
    const list = vtds.map(([d, r, o, flat, name]) => {
      D += d; R += r; O += o;
      const pts = new Float32Array(flat.length);
      let x = 0, y = 0, adults = 0;
      for (let i = 0; i < flat.length; i += 4) {
        x += flat[i]; y += flat[i + 1];
        const p = P([x / 1e4, y / 1e4]);
        pts[i] = p.x; pts[i + 1] = p.y; pts[i + 2] = flat[i + 2] * 10 * upm; pts[i + 3] = flat[i + 3];
        adults += flat[i + 3];
      }
      return { d, r, o, adults, pts, name };
    });
    out.set(fips, { vtds: list, D, R, O, adults: list.reduce((s, v) => s + v.adults, 0) });
  }
  return { byFips: out, hot: data.hot, meta: data.meta, land: landUrl ? await loadLand(P, landUrl) : null };
}

// Where the 2020 Census counted anyone, from data/landmask.bin.gz (scripts/build_landmask.py), so that dots stay off lakes,
// bays, airports and the like: { bits (one per cell, row by row), w, h, sx, ox, sy, oy }, where a map point (x, y) is in
// grid cell (ox + x * sx, oy + y * sy). Dots are placed without it (null) if it doesn't load.
async function loadLand(P, url) {
  try {
    const res = await fetch(url); if (!res.ok) throw new Error(res.status);
    const gz = new Uint8Array(await res.arrayBuffer());
    const zipped = gz[0] === 0x1f && gz[1] === 0x8b;
    const b = zipped ? new Uint8Array(await new Response(new Blob([gz]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer()) : gz;
    const n = new DataView(b.buffer, b.byteOffset).getUint32(0, true);
    const { w, h, a, b: e } = JSON.parse(new TextDecoder().decode(b.subarray(4, 4 + n)));
    const bits = new Uint8Array(Math.ceil(w * h / 8));
    let p = 4 + n, cell = 0;
    for (let y = 0; y < h; y++) { // each row: run lengths in cells, empty first, then lived on, taking turns
      const end = (y + 1) * w;
      for (let on = false; cell < end; on = !on) {
        let run = 0, shift = 0, c;
        do { c = b[p++]; run += (c & 127) * 2 ** shift; shift += 7; } while (c > 127);
        if (on) for (let i = cell; i < cell + run; i++) bits[i >> 3] |= 1 << (i & 7);
        cell += run;
      }
    }
    const pa = P([a[0], a[1]]), pe = P([e[0], e[1]]);
    const sx = (e[2] - a[2]) / (pe.x - pa.x), sy = (e[3] - a[3]) / (pe.y - pa.y);
    return { bits, w, h, sx, ox: a[2] - pa.x * sx, sy, oy: a[3] - pa.y * sy };
  } catch (err) { console.error('The land grid did not load; dots may land on empty land', err); return null; }
}

// The places for one county's dots (dots-worker.js `units`): each census block with the votes it is expected to hold.
// Each party's county total (dem, rep, other: the race being shown) is shared among the VTDs in proportion to that party's
// 2024 Senate votes there, then among each VTD's blocks by adults. A party with no 2024 votes in the county is shared by
// all 2024 votes instead.
export function precinctUnits(county, votes) {
  const { vtds } = county, n = vtds.reduce((s, v) => s + v.pts.length / 4, 0);
  const units = new Float32Array(n * 6), est = precinctVotes(county, votes);
  let j = 0;
  vtds.forEach((v, k) => {
    const { d, r, o } = est[k];
    for (let i = 0; i < v.pts.length; i += 4) {
      const s = v.adults > 0 ? v.pts[i + 3] / v.adults : 0;
      units.set([v.pts[i], v.pts[i + 1], v.pts[i + 2], d * s, r * s, o * s], j); j += 6;
    }
  });
  return units;
}

// Each precinct's expected votes in a race known only by county: { d, r, o }, adding up to the county's result.
export function precinctVotes({ vtds, D, R, O }, { dem, rep, other }) {
  const T = D + R + O;
  // this VTD's share of a party's county votes: its share of that party's 2024 votes (or of all 2024 votes)
  const share = (v, own, countyOwn) => countyOwn > 0 ? own / countyOwn : (v.d + v.r + v.o) / T;
  return vtds.map(v => ({ d: dem * share(v, v.d, D), r: rep * share(v, v.r, R), o: other * share(v, v.o, O) }));
}

const glslColor = h => { const c = new THREE.Color(h); return `vec3(${c.r.toFixed(4)}, ${c.g.toFixed(4)}, ${c.b.toFixed(4)})`; };

// uniforms (all sizes in device pixels):
//   uP       rise progress, same timing as the main map's columns (0 = flat)
//   uReveal  share of dots shown (0..1), in a fixed random order, to let the dots appear gradually
//   uMinSize smallest dot size; uFocus, uFocusSize: index of one county (in the order given to place()) whose dots get
//            a different smallest size, -1 for none; uWorld: dot diameter in map units, so dots grow as the camera comes close
//   uViewH   drawing buffer height, to turn uWorld into pixels
export function createDots({ depthTest = true } = {}) {
  const uniforms = {
    uP: { value: 0 }, uReveal: { value: 1 }, uMinSize: { value: 1 }, uWorld: { value: 0.012 }, uViewH: { value: 800 },
    uCounties: { value: null }, uFocus: { value: -1 }, uFocusSize: { value: 1 },
  };
  const material = new THREE.RawShaderMaterial({
    glslVersion: THREE.GLSL3, uniforms, depthTest, depthWrite: depthTest,
    vertexShader: `precision highp float; precision highp int; precision highp sampler2D;
      uniform mat4 modelViewMatrix, projectionMatrix;
      uniform float uP, uReveal, uMinSize, uWorld, uViewH, uFocus, uFocusSize;
      uniform sampler2D uCounties; // per county: center x, center y, map units per step, rise delay
      in ivec4 position;           // from dots-worker.js: x, y steps from the county center, height * 64, party * 256 + county
      out vec3 vColor; out float vSize;
      float ease(float t) { return t < .5 ? 4. * t * t * t : 1. - pow(-2. * t + 2., 3.) / 2.; }
      void main() {
        uint h = uint(gl_VertexID) * 2654435761u; h ^= h >> 16; h *= 2246822519u; h ^= h >> 13;
        if (float(h & 16777215u) / 16777216. >= uReveal) { gl_Position = vec4(2., 2., 2., 1.); gl_PointSize = 1.; return; }
        float party = float(position.w >> 8);
        int cix = position.w & 255;
        float ci = float(cix);
        vec4 C = texelFetch(uCounties, ivec2(cix, 0), 0);
        vec3 q = vec3(position.xyz);
        float k = ease(clamp((uP - 0.3 - C.w) / 0.45, 0., 1.));
        vec4 mv = modelViewMatrix * vec4(C.x + q.x * C.z, C.y + q.y * C.z, 0.2 + q.z / 64. * k, 1.);
        gl_Position = projectionMatrix * mv;
        vSize = max(abs(ci - uFocus) < .5 ? uFocusSize : uMinSize, uWorld * projectionMatrix[1][1] * uViewH * 0.5 / max(-mv.z, 1e-3));
        gl_PointSize = vSize;
        vColor = party < .5 ? ${glslColor(DOT_C.dem)} : party < 1.5 ? ${glslColor(DOT_C.rep)} : ${glslColor(DOT_C.other)};
      }`,
    fragmentShader: `precision highp float;
      in vec3 vColor; in float vSize; out vec4 outColor;
      void main() {
        vec2 d = gl_PointCoord - .5;
        if (vSize > 2.5 && dot(d, d) > .25) discard; // round dots once they are big enough to see a shape
        outColor = vec4(vColor, 1.);
      }`,
  });
  const points = new THREE.Points(new THREE.BufferGeometry(), material);
  points.frustumCulled = false; // the bounding sphere would be computed from the fixed-point values
  const worker = new Worker(new URL('./dots-worker.js', import.meta.url));
  let job = 0, done = null;
  worker.onmessage = ({ data: { buf, table, counts, job: j } }) => {
    if (j !== job) return; // a newer request came in while this one was being placed
    points.geometry.dispose();
    const g = new THREE.BufferGeometry();
    // read as integers (ivec4): Direct3D, behind WebGL on Windows, can't turn 16-bit integers into floats itself, and
    // converting ten million dots on the CPU every frame is far too slow
    const attr = new THREE.Int16BufferAttribute(buf, 4);
    attr.gpuType = THREE.IntType;
    g.setAttribute('position', attr);
    points.geometry = g;
    uniforms.uCounties.value?.dispose();
    const tex = new THREE.DataTexture(table, table.length / 4, 1, THREE.RGBAFormat, THREE.FloatType);
    tex.needsUpdate = true;
    uniforms.uCounties.value = tex;
    done({ n: counts[0] + counts[1] + counts[2], counts });
  };
  // land: from loadPrecincts, once, before place(): where dots placed by `units` may land
  const setLand = land => { if (land) worker.postMessage({ land }, [land.bits.buffer]); };
  // counties: [{ tris, w (optional triangle weights) or units (places, from precinctUnits), dem, rep, other, target (raised
  // height, map units), delay (rise delay, 0..0.25) }]
  function place(counties, { per = 1, seed = 1 } = {}) {
    return new Promise(resolve => {
      done = resolve;
      worker.postMessage({ per, seed, job: ++job,
        counties: counties.map(({ tris, w, units, dem, rep, other, target = 0, delay = 0 }) => ({ tris, w, units, dem, rep, other, target, delay })) });
    });
  }
  return { points, uniforms, place, setLand };
}

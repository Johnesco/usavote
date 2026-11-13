// Bar view, by precinct (app.js): one column per precinct across the whole state, drawn as a single mesh so that 9,000 of them
// stay fast. Each column is stacked the way a county's is, by votes: the most on top and the fewest at the bottom. The
// stack is colored in the shader, from how far up the wall a pixel is, so each wall needs only one piece of geometry.
//
// Shapes come from data/precinct-shapes.json.gz (scripts/build_precincts.py), in map units once projected by P. Heights are set
// with setValues and all stretched together by setScale, so columns always keep the same proportions to each other.
import * as THREE from 'three';
import { fetchJsonGz } from './dots.js';

export const loadPrecinctShapes = url => fetchJsonGz(url);

// A ring as map points, counterclockwise for land and clockwise for a hole.
function ringPoints(flat, P, hole) {
  const pts = [];
  let x = 0, y = 0;
  for (let i = 0; i < flat.length; i += 2) {
    x += flat[i]; y += flat[i + 1];
    pts.push(P([x / 1e4, y / 1e4]));
  }
  if (THREE.ShapeUtils.isClockWise(pts) !== hole) pts.reverse();
  return pts;
}

// precincts: [polygons from the shapes file, ...]; palette: [THREE.Color, ...], the colors setValues refers to by number;
// other: the middle of the stack. Returns the object described at the end.
export function createPrecinctColumns(parent, P, precincts, palette, other) {
  const list = [];
  let nEdges = 0, nCap = 0, nCapIdx = 0;
  for (const polygons of precincts) {
    const p = { polys: [], x0: Infinity, y0: Infinity, x1: -Infinity, y1: -Infinity, h: 0 };
    for (const [outer, ...holes] of polygons) {
      const contour = ringPoints(outer, P, false), hs = holes.map(h => ringPoints(h, P, true));
      const faces = THREE.ShapeUtils.triangulateShape(contour, hs);
      const rings = [contour, ...hs];
      p.polys.push({ rings, faces });
      for (const r of rings) {
        nEdges += r.length; nCap += r.length;
        for (const q of r) { p.x0 = Math.min(p.x0, q.x); p.x1 = Math.max(p.x1, q.x); p.y0 = Math.min(p.y0, q.y); p.y1 = Math.max(p.y1, q.y); }
      }
      nCapIdx += faces.length * 3;
    }
    list.push(p);
  }

  // walls: 4 corners an edge; caps: 1 per ring point; lines: the top of each edge
  const nV = nEdges * 4 + nCap;
  const pos = new Float32Array(nV * 3), normal = new Int8Array(nV * 4), code = new Uint8Array(nV * 4);
  const index = new Uint32Array(nEdges * 6 + nCapIdx), line = new Float32Array(nEdges * 6);
  let v = 0, ix = 0, ln = 0;
  for (const p of list) {
    p.v0 = v; p.line0 = ln; p.edges = [];
    for (const { rings } of p.polys) for (const r of rings) r.forEach((a, i) => {
      const b = r[(i + 1) % r.length];
      const dx = b.x - a.x, dy = b.y - a.y, len = Math.hypot(dx, dy) || 1, nx = Math.round(127 * dy / len), ny = Math.round(-127 * dx / len);
      [[a, 0], [b, 0], [b, 127], [a, 127]].forEach(([q, up], k) => {
        pos[(v + k) * 3] = q.x; pos[(v + k) * 3 + 1] = q.y;
        normal.set([nx, ny, 0, up], (v + k) * 4);
      });
      index.set([v, v + 1, v + 2, v, v + 2, v + 3], ix); ix += 6; v += 4;
      line[ln] = a.x; line[ln + 1] = a.y; line[ln + 3] = b.x; line[ln + 4] = b.y; ln += 6;
      p.edges.push(a.x, a.y, b.x, b.y);
    });
    p.wallEnd = v; p.lineEnd = ln;
    for (const { rings, faces } of p.polys) {
      const base = v;
      for (const r of rings) for (const q of r) { pos[v * 3] = q.x; pos[v * 3 + 1] = q.y; normal.set([0, 0, 127, 127], v * 4); v++; }
      for (const f of faces) { index.set([base + f[0], base + f[1], base + f[2]], ix); ix += 3; }
    }
    p.v1 = v;
  }

  const geo = new THREE.BufferGeometry();
  const posAttr = new THREE.BufferAttribute(pos, 3), codeAttr = new THREE.BufferAttribute(code, 4, true);
  geo.setAttribute('position', posAttr);
  geo.setAttribute('aN', new THREE.BufferAttribute(normal, 4, true));
  geo.setAttribute('aCode', codeAttr);
  geo.setIndex(new THREE.BufferAttribute(index, 1));
  const material = new THREE.ShaderMaterial({
    side: THREE.DoubleSide,
    uniforms: { uPal: { value: palette }, uOther: { value: other } },
    vertexShader: `
      attribute vec4 aN, aCode; // normal + height up the wall; winner's color, runner-up's color, runner-up's share, others' share
      uniform vec3 uPal[${palette.length}];
      varying vec3 vTop, vLow; varying vec3 vShares; varying float vLight;
      void main() {
        vTop = uPal[int(aCode.x * 255. + .5)]; vLow = uPal[int(aCode.y * 255. + .5)];
        vShares = vec3(aN.w, aCode.z, aCode.w);
        // what the county columns get from the scene's lights, on their walls; tops are unlit
        vec3 n = normalize(mat3(modelMatrix) * vec3(aN.xy, 0.0001));
        vLight = aN.z > .5 ? 1. : .8 * (.57 + 1.6 * max(0., dot(n, vec3(-.467, .7, .545)))) / 3.14159;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.);
      }`,
    fragmentShader: `
      uniform vec3 uOther; varying vec3 vTop, vLow; varying vec3 vShares; varying float vLight;
      void main() {
        // ranked: each part stands on the parts with fewer votes (ties: runner-up, then others, then winner, from the bottom)
        float y = vShares.x, lo = vShares.y, ot = vShares.z, w = 1. - lo - ot;
        float sLo = (ot < lo ? ot : 0.) + (w < lo ? w : 0.), sOt = (lo <= ot ? lo : 0.) + (w < ot ? w : 0.);
        vec3 c = y >= sLo && y < sLo + lo ? vLow : y >= sOt && y < sOt + ot ? uOther : vTop;
        gl_FragColor = vec4(c * vLight, 1.);
        #include <colorspace_fragment>
      }`,
  });
  const group = new THREE.Group();
  const mesh = new THREE.Mesh(geo, material);
  mesh.frustumCulled = false;
  const lineGeo = new THREE.BufferGeometry();
  const lineAttr = new THREE.BufferAttribute(line, 3);
  lineGeo.setAttribute('position', lineAttr);
  const lineMat = new THREE.LineBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.5 });
  const lines = new THREE.LineSegments(lineGeo, lineMat);
  lines.frustumCulled = false;
  const mark = color => {
    const l = new THREE.LineSegments(new THREE.BufferGeometry(), new THREE.LineBasicMaterial({ color, depthTest: false }));
    l.renderOrder = 6; l.frustumCulled = false; return l;
  };
  const hoverLine = mark(0xffffff), chosenLine = mark(0xf2c14e);
  group.add(mesh, lines, hoverLine, chosenLine);
  parent.add(group);

  function outline(l, i) {
    l.geometry.dispose();
    l.geometry = new THREE.BufferGeometry();
    const p = list[i];
    if (!p) return;
    const out = new Float32Array(p.edges.length / 4 * 6);
    for (let e = 0, o = 0; e < p.edges.length; e += 4, o += 6) out.set([p.edges[e], p.edges[e + 1], p.h, p.edges[e + 2], p.edges[e + 3], p.h], o);
    l.geometry.setAttribute('position', new THREE.BufferAttribute(out, 3));
  }
  let hovered = -1, chosen = -1;

  return {
    group, lineMat,
    // values[i]: { h: height, top, low: palette numbers for the winner and runner-up, fLow, fMid: shares of the column }
    setValues(values) {
      values.forEach(({ h, top, low, fLow, fMid }, i) => {
        const p = list[i]; p.h = h;
        const a = Math.round(fLow * 255), b = Math.round(fMid * 255);
        for (let k = p.v0; k < p.wallEnd; k += 4) { pos[(k + 2) * 3 + 2] = h; pos[(k + 3) * 3 + 2] = h; }
        for (let k = p.wallEnd; k < p.v1; k++) pos[k * 3 + 2] = h;
        for (let k = p.line0 + 2; k < p.lineEnd; k += 3) line[k] = h;
        for (let k = p.v0; k < p.v1; k++) { code[k * 4] = top; code[k * 4 + 1] = low; code[k * 4 + 2] = a; code[k * 4 + 3] = b; }
      });
      posAttr.needsUpdate = codeAttr.needsUpdate = lineAttr.needsUpdate = true;
      outline(hoverLine, hovered); outline(chosenLine, chosen);
    },
    height: i => list[i]?.h ?? 0,
    setHover(i) { if (i !== hovered) { hovered = i; outline(hoverLine, i); } },
    setChosen(i) { chosen = i; outline(chosenLine, i); },
    // which precinct a ray hits first, or -1. origin, dir: in the map's axes, not yet allowing for this group's position and stretch.
    pick(origin, dir) {
      const s = group.scale.z, zo = (origin.z - group.position.z) / s, zd = dir.z / s, ox = origin.x, oy = origin.y, dx = dir.x, dy = dir.y;
      const hits = [];
      list.forEach((p, i) => { // first whichever boxes the ray passes through
        let a = 0, b = Infinity;
        for (const [o, d, lo, hi] of [[ox, dx, p.x0, p.x1], [oy, dy, p.y0, p.y1], [zo, zd, 0, Math.max(p.h, 1e-6)]]) {
          if (Math.abs(d) < 1e-12) { if (o < lo || o > hi) return; continue; }
          const t0 = (lo - o) / d, t1 = (hi - o) / d;
          a = Math.max(a, Math.min(t0, t1)); b = Math.min(b, Math.max(t0, t1));
          if (a > b) return;
        }
        hits.push([a, i]);
      });
      hits.sort((x, y) => x[0] - y[0]);
      let best = Infinity, who = -1;
      for (const [a, i] of hits) {
        if (a >= best) break;
        const p = list[i], e = p.edges;
        if (zd < 0) { // down through its top?
          const t = (p.h - zo) / zd, x = ox + dx * t, y = oy + dy * t;
          let inside = false;
          for (let k = 0; k < e.length; k += 4)
            if ((e[k + 1] > y) !== (e[k + 3] > y) && x < (e[k + 2] - e[k]) * (y - e[k + 1]) / (e[k + 3] - e[k + 1]) + e[k]) inside = !inside;
          if (inside && t < best) { best = t; who = i; }
        }
        for (let k = 0; k < e.length; k += 4) { // in through a wall?
          const ex = e[k + 2] - e[k], ey = e[k + 3] - e[k + 1], den = dx * ey - dy * ex;
          if (Math.abs(den) < 1e-12) continue;
          const t = ((e[k] - ox) * ey - (e[k + 1] - oy) * ex) / den, u = ((e[k] - ox) * dy - (e[k + 1] - oy) * dx) / den;
          if (t < 0 || t >= best || u < 0 || u > 1) continue;
          const z = zo + zd * t;
          if (z >= 0 && z <= p.h) { best = t; who = i; }
        }
      }
      return who;
    },
  };
}

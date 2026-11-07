// City and town names for reference on every map (index/history, story, voters), from data/cities.json
// (scripts/build_cities.py: 2020 Census places). Which names show depends on the zoom: with the whole state on screen,
// only cities of about MIN_STATE people or more; zoomed in, smaller towns too, down to the smallest in the file. Larger
// places win when two labels would overlap, and at most MAX are shown at once. Names also keep clear of the page's own
// labels and controls drawn over the map.
//
//   const cities = await createCityLabels(beforeEl, P, { avoid: () => [elements] });
//       beforeEl: the county-label layer, so those stay on top; avoid: elements (buttons, cards, legends) names keep clear of
//   cities.update(camera, mapGroup, W, H, opacity, boxes);
//       every frame, after rendering. W, H: the canvas size in CSS px. boxes: more screen boxes to keep clear of, such as
//       the county labels placed this frame, as [left, top, right, bottom]
import * as THREE from 'three';

const MIN_STATE = 100000; // smallest city named when the whole state (about 1,000 map units) fills the screen's short side
const ZOOM_POW = 1.6;     // zooming in by 2x lowers that by 2^1.6 (about 3x)
const MAX = 30;
const GAP = 3;            // pixels kept clear around each name

export async function createCityLabels(beforeEl, P, { avoid = () => [], url = 'data/cities.json' } = {}) {
  let list = [];
  try {
    const r = await fetch(url); if (!r.ok) throw new Error(r.status);
    list = (await r.json()).cities.map(([name, lon, lat, pop]) => { const p = P([lon, lat]); return { name, pop, x: p.x, y: p.y }; });
  } catch (e) { console.error('City names did not load', e); }
  const smallest = list.length ? list.at(-1).pop : 0;
  const layer = document.createElement('div');
  layer.className = 'city-layer';
  layer.setAttribute('aria-hidden', 'true');
  // positioning set here too, so a cached older style.css can't leave the labels stacked in the page's flow
  Object.assign(layer.style, { position: 'absolute', inset: '0', pointerEvents: 'none', overflow: 'hidden' });
  beforeEl.parentNode.insertBefore(layer, beforeEl);

  const make = c => { // the label element, made the first time it's needed
    c.el = document.createElement('div');
    c.el.className = 'city' + (c.pop >= 500000 ? ' city-big' : c.pop >= 100000 ? ' city-mid' : '');
    c.el.textContent = c.name;
    Object.assign(c.el.style, { position: 'absolute', left: '0', top: '0', whiteSpace: 'nowrap', boxSizing: 'border-box' });
    layer.appendChild(c.el);
    c.w = c.el.offsetWidth; c.h = c.el.offsetHeight;
  };
  const v = new THREE.Vector3(), w = new THREE.Vector3(), ray = new THREE.Ray(), ground = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);
  // map point (x, y) on the ground -> screen pixels in out (out.z >= 1: behind the camera)
  const toScreen = (mapGroup, camera, x, y, out, W, H) => {
    out.set(x, y, 0).applyMatrix4(mapGroup.matrixWorld).project(camera);
    out.x = (out.x + 1) / 2 * W; out.y = (1 - out.y) / 2 * H;
    return out;
  };
  let shown = new Set();
  function update(camera, mapGroup, W, H, opacity = 1, boxes = []) {
    layer.style.opacity = opacity;
    const next = new Set();
    if (opacity > 0.01 && list.length) {
      // zoom: screen pixels per map unit where the camera is looking (its view ray meets the ground)
      camera.getWorldPosition(ray.origin); camera.getWorldDirection(ray.direction);
      let cx = 0, cy = 0;
      if (ray.intersectPlane(ground, w)) { mapGroup.worldToLocal(w); cx = w.x; cy = w.y; }
      const a = toScreen(mapGroup, camera, cx, cy, new THREE.Vector3(), W, H), b = toScreen(mapGroup, camera, cx + 10, cy, v, W, H);
      const pxPerUnit = Math.hypot(b.x - a.x, b.y - a.y) / 10;
      const statePx = Math.min(W, H) / 1000;
      // the smallest place to name: MIN_STATE at the whole-state zoom, fewer people as the camera comes down
      const minPop = Math.max(smallest, MIN_STATE * (statePx / Math.max(pxPerUnit, 1e-9)) ** ZOOM_POW);
      // keep clear of the page's own labels and of its controls over the map (in this layer's coordinates)
      const L = layer.getBoundingClientRect(), placed = [...boxes];
      for (const el of avoid()) {
        const r = el?.getBoundingClientRect();
        if (r && r.width && getComputedStyle(el).opacity > 0.05) placed.push([r.left - L.left, r.top - L.top, r.right - L.left, r.bottom - L.top]);
      }
      for (const c of list) { // largest first
        if (c.pop < minPop || next.size >= MAX) break;
        toScreen(mapGroup, camera, c.x, c.y, v, W, H);
        if (v.z >= 1 || v.x < -40 || v.x > W + 40 || v.y < -20 || v.y > H + 20) continue;
        if (!c.el) make(c);
        // the name to the right of the dot, else to its left, above or below: the first spot that's free. Each option is
        // [class, element top-left x, y, then its box]; the 6 px dot is centered on the place in every case.
        const { x, y } = v, w = c.w, h = c.h, tw = w - 10; // tw: the name's own width, without the dot's room
        const spot = [
          ['r', x - 3, y - h / 2, [x - 4, y - h / 2 - 1, x + w - 2, y + h / 2 + 1]],
          ['l', x - w + 3, y - h / 2, [x - w + 2, y - h / 2 - 1, x + 4, y + h / 2 + 1]],
          ['a', x - tw / 2, y + 3 - h - 8, [x - tw / 2 - 1, y + 4 - h - 8, x + tw / 2 + 1, y + 4]],
          ['b', x - tw / 2, y - 3, [x - tw / 2 - 1, y - 4, x + tw / 2 + 1, y - 3 + h + 9]],
        ].find(([, , , box]) => box[0] >= 0 && box[2] <= W && box[1] >= 0 && box[3] <= H && !placed.some(q => box[0] - GAP < q[2] && box[2] + GAP > q[0] && box[1] - GAP < q[3] && box[3] + GAP > q[1]));
        if (!spot) continue;
        const [side, ex, ey, box] = spot;
        placed.push(box); next.add(c);
        if (c.side !== side) { c.el.classList.remove('l', 'a', 'b'); if (side !== 'r') c.el.classList.add(side); c.side = side; }
        c.el.style.transform = `translate(${ex.toFixed(1)}px, ${ey.toFixed(1)}px)`;
      }
    }
    for (const c of shown) if (!next.has(c)) c.el.classList.remove('on');
    for (const c of next) if (!shown.has(c)) c.el.classList.add('on');
    shown = next;
  }
  return { update };
}

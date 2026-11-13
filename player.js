// The player along the bottom of every guided flight, the same in each: the County Flythrough (story.js), Misreading the Map
// (misread.js) and the dot view's Density Tour (voters.js). Each page keeps its own clock and draws itself from it; this is the
// controls around that clock:
//   ‹  Play/Pause  ›   back a scene (or to the start of this one), play or pause, on a scene; at the end, Watch again
//   the timeline        a mark for each scene; click or drag anywhere on it to go there (it's a slider for the keyboard too)
//   3 / 12              which scene of how many
// Keys, while the guide has the screen: Space plays or pauses, ← and → go back and on a scene, Home and End go to the first and
// last. The scene goes in the address as ?scene=N, which every guide opens on, so a link shares the scene you're on.
// The page's markup has #player with #prev, #pause, #next and #track holding #fill; anything else in #player stays as it is.
//
// The page gives its clock: time() and playing() read it; seek(t) puts it at t and plays from there, doing whatever else
// jumping means on that page; setPlaying(on) pauses or plays. starts() and end() are the scenes' start times and the length,
// read when needed, since a page can work them out after making the player. active() says when the guide has the screen
// (in the dot view, not while exploring). saveScene: false leaves the address alone.
// It returns { update, jump, sceneAt }: the page calls update() on every frame and whenever its clock changes.
export function createPlayer({ time, playing, seek, setPlaying, starts, end, active = () => true, saveScene = true }) {
  const $ = id => document.getElementById(id);
  const track = $('track'), fill = $('fill'), pause = $('pause');
  const sceneAt = (t, s = starts()) => { let i = 0; while (i + 1 < s.length && s[i + 1] <= t) i++; return i; };
  const jump = t => seek(Math.max(0, Math.min(t, end())));

  // the timeline: marks for the scenes, a slider for the keyboard, and room around the thin line to aim at
  track.removeAttribute('aria-hidden');
  Object.assign(track, { tabIndex: 0, title: 'Click or drag to go anywhere in the flight' });
  track.setAttribute('role', 'slider');
  track.setAttribute('aria-label', 'Scene');
  track.setAttribute('aria-valuemin', '1');
  const marks = document.createElement('span');
  marks.className = 'marks'; marks.setAttribute('aria-hidden', 'true');
  track.append(marks);
  const count = document.createElement('span');
  count.className = 'scene-count'; count.setAttribute('aria-hidden', 'true');
  track.after(count);

  const at = e => { const r = track.getBoundingClientRect(); return Math.max(0, Math.min(1, (e.clientX - r.left) / r.width)) * end(); };
  track.addEventListener('pointerdown', e => {
    if (e.button !== 0) return;
    e.preventDefault(); track.focus({ preventScroll: true });
    track.setPointerCapture(e.pointerId);
    jump(at(e));
  });
  track.addEventListener('pointermove', e => { if (track.hasPointerCapture(e.pointerId)) jump(at(e)); });

  const back = () => { const s = starts(), t = time(), i = sceneAt(t, s); jump(s[t - s[i] < 1.5 && i > 0 ? i - 1 : i]); };
  const on = () => { const s = starts(), i = sceneAt(time(), s); if (i + 1 < s.length) jump(s[i + 1]); };
  pause.onclick = () => { if (time() >= end()) jump(0); else { setPlaying(!playing()); update(); } };
  $('prev').onclick = back;
  $('next').onclick = on;
  addEventListener('keydown', e => {
    if (!active() || e.altKey || e.ctrlKey || e.metaKey || e.target.matches?.('select, input, textarea')) return;
    const key = { ' ': () => pause.click(), ArrowRight: on, ArrowLeft: back, Home: () => jump(0), End: () => jump(starts().at(-1)) }[e.key];
    // (Space on a focused button is that button's own click)
    if (!key || (e.key === ' ' && e.target !== document.body && e.target !== track)) return;
    e.preventDefault(); key();
  });

  let drawnEnd = -1, shown = -1, wasActive = null, label = '';
  function update() {
    const s = starts(), total = end(), t = time(), i = sceneAt(t, s);
    if (total !== drawnEnd) { // the scene marks, once the page knows its times
      drawnEnd = total;
      marks.innerHTML = total > 0 ? s.slice(1).map(x => `<b style="left:${(100 * x / total).toFixed(2)}%"></b>`).join('') : '';
      track.setAttribute('aria-valuemax', String(s.length));
      shown = -1;
    }
    fill.style.width = `${total > 0 ? 100 * t / total : 0}%`;
    const text = t >= total ? 'Watch again' : playing() ? 'Pause' : 'Play';
    if (text !== label) { label = text; pause.textContent = text; pause.setAttribute('aria-label', text); }
    const act = active();
    if (i === shown && act === wasActive) return;
    shown = i; wasActive = act;
    count.textContent = `${i + 1} / ${s.length}`;
    track.setAttribute('aria-valuenow', String(i + 1));
    track.setAttribute('aria-valuetext', `Scene ${i + 1} of ${s.length}`);
    if (saveScene && act) {
      const q = new URLSearchParams(location.search);
      q.delete('tour'); q.set('scene', String(i + 1));
      try { history.replaceState(null, '', `?${q}`); } catch {}
    }
  }
  return { update, jump, sceneAt: t => sceneAt(t) };
}

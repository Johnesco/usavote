// Compare (compare.html): two view pages side by side, each in a frame. ?a= and ?b= are their addresses, pages on this site only.
// Each view sends where its camera is (panel.js, followCamera); with Move together on, the other side is sent there too.
// The address keeps both sides as they are now, so a link opens the same pair.
const $ = id => document.getElementById(id);
const q = new URLSearchParams(location.search);
// a page of this site and its settings, nothing else: no other site, no script
const PAGE = /^[a-z0-9-]+\.html(\?[^#]*)?$/;
const ok = u => typeof u === 'string' && PAGE.test(u);
const panes = [$('paneA'), $('paneB')];
const start = [q.get('a'), q.get('b')];
if (!start.every(ok)) {
  $('error').hidden = false;
  document.querySelector('.panes').hidden = true;
} else {
  panes.forEach((f, i) => { f.src = start[i]; });
  // where each side is now, as an address relative to this page
  const here = f => { try { const l = f.contentWindow.location; return l.pathname.split('/').pop() + l.search; } catch { return null; } };
  let swapped = false;
  const save = () => {
    const [a, b] = (swapped ? [...panes].reverse() : panes).map(here);
    if (!ok(a) || !ok(b)) return;
    $('keepA').href = a; $('keepB').href = b;
    const url = `?a=${encodeURIComponent(a)}&b=${encodeURIComponent(b)}`;
    if (url !== location.search) try { history.replaceState(null, '', url); } catch {}
  };
  setInterval(save, 1000);
  panes.forEach(f => f.addEventListener('load', save));
  const heard = new WeakSet(), last = new WeakMap(); // the sides' windows that have sent their camera, and where each was last
  addEventListener('message', e => {
    if (e.origin !== location.origin || e.data?.type !== 'cam') return;
    const from = panes.findIndex(f => f.contentWindow === e.source);
    if (from < 0) return;
    const { x, y, d } = e.data, other = panes[1 - from];
    // a side that has just opened (or loaded a new look) goes to where the other side is, rather than pulling it back
    if (!heard.has(e.source) && last.has(other.contentWindow) && $('sync').checked) {
      heard.add(e.source);
      const c = last.get(other.contentWindow);
      e.source.postMessage({ type: 'setCam', ...c }, location.origin);
      return;
    }
    heard.add(e.source); last.set(e.source, { x, y, d });
    if (!$('sync').checked) return;
    last.set(other.contentWindow, { x, y, d }); // (it doesn't say where it went, so as not to echo)
    other.contentWindow.postMessage({ type: 'setCam', x, y, d }, location.origin);
  });
  // swapping moves the frames, not what's in them, so neither map starts over
  $('swap').onclick = () => { swapped = !swapped; document.querySelector('.panes').classList.toggle('swapped', swapped); save(); };
}

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
  // what a side shows, from its address and its page's race title: '3D · 2026 U.S. Senate'
  const LOOKS = { '3d': '3D', dots: 'Dots' };
  const shows = (f, u) => {
    const p = new URLSearchParams(u.split('?')[1] || '');
    let race = '';
    try { race = f.contentDocument.getElementById('title')?.textContent.trim() || ''; } catch {}
    if (/election results$/i.test(race)) race = ''; // (the page's own heading, before its race is set)
    return [LOOKS[p.get('look')] || 'Flat', race || p.get('race')].filter(Boolean).join(' · ');
  };
  let swapped = false;
  const save = () => {
    const order = swapped ? [...panes].reverse() : panes, [a, b] = order.map(here);
    if (!ok(a) || !ok(b)) return;
    $('keepA').href = a; $('keepB').href = b;
    // the links and frames say what each side shows, so they read right side by side, stacked or swapped
    [a, b].forEach((u, i) => {
      const s = shows(order[i], u), keep = $(i ? 'keepB' : 'keepA');
      if (keep.textContent !== `Keep ${s}`) keep.textContent = `Keep ${s}`; // (only on a change: this runs every second)
      if (order[i].title !== `Map: ${s}`) order[i].title = `Map: ${s}`;
    });
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

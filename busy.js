// A small "working on it" sign over the map, for a change that can take a moment. A quick change never shows it: the sign waits a
// moment before appearing, and once up it stays long enough to read rather than flicker. Its spinner is turned by the browser's
// compositor, so it keeps going while the page itself is busy.
const WAIT = 150, LEAST = 350; // milliseconds

export function createBusy(parent) {
  const el = document.createElement('div'), label = document.createElement('span');
  el.className = 'busy'; el.setAttribute('role', 'status'); el.hidden = true;
  const spin = document.createElement('span');
  spin.className = 'busy-spin'; spin.setAttribute('aria-hidden', 'true');
  el.append(spin, label);
  parent.append(el);
  const jobs = new Map(); // what's under way, by name; a job asked for again replaces itself
  let waiting = null, leaving = null, shownAt = 0;
  const reveal = () => {
    waiting = null;
    if (!jobs.size) return;
    if (el.hidden) { el.hidden = false; shownAt = performance.now(); }
  };
  const refresh = () => { if (jobs.size) label.textContent = [...jobs.values()].at(-1); };
  function show(job, text) {
    jobs.delete(job); jobs.set(job, text); refresh();
    clearTimeout(leaving); leaving = null;
    if (el.hidden && !waiting) waiting = setTimeout(reveal, WAIT);
  }
  function hide(job) {
    if (!jobs.delete(job)) return;
    refresh();
    if (jobs.size) return;
    clearTimeout(waiting); waiting = null;
    if (!el.hidden) leaving = setTimeout(() => { el.hidden = true; leaving = null; }, Math.max(0, LEAST - (performance.now() - shownAt)));
  }
  // For work that holds up the page itself, when a timer couldn't fire: the sign goes up at once, and this finishes once it's on
  // screen, so the work can start then. (A hidden tab never paints, so that wait is cut short.)
  function showNow(job, text) {
    show(job, text); clearTimeout(waiting); reveal();
    return new Promise(done => {
      const t = setTimeout(done, 100);
      requestAnimationFrame(() => requestAnimationFrame(() => { clearTimeout(t); done(); }));
    });
  }
  return { show, showNow, hide };
}

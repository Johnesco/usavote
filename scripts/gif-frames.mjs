// Screenshots scripts/gif.html frame by frame in one headless browser, for scripts/build_gif.py, which runs this:
//   node scripts/gif-frames.mjs <browser> <page url> <folder> <width> <height> <frame> [<frame> ...]
// It writes <folder>/<frame as 3 digits>.png. Needs Node 22 or later (for its built-in WebSocket); no packages.
import { spawn } from 'node:child_process';
import { mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const [exe, url, dir, w, h, ...frames] = process.argv.slice(2);
const profile = mkdtempSync(join(tmpdir(), 'gif-profile-')); // its own profile, so a browser that's already open isn't handed the job
const chrome = spawn(exe, ['--headless=new', '--hide-scrollbars', '--remote-debugging-port=0', `--user-data-dir=${profile}`,
  `--window-size=${w},${h}`, 'about:blank'], { stdio: ['ignore', 'ignore', 'pipe'] });
const sleep = ms => new Promise(r => setTimeout(r, ms));
try {
  // the browser prints the address to talk to it on
  const browserWs = await new Promise((done, fail) => {
    let err = '';
    chrome.stderr.on('data', d => { err += d; const m = err.match(/DevTools listening on (ws:\/\/\S+)/); if (m) done(m[1]); });
    chrome.on('exit', () => fail(new Error('the browser closed before it was ready')));
    setTimeout(() => fail(new Error('the browser did not start in 30 seconds')), 30000);
  });
  const port = new URL(browserWs).port;
  const page = (await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()).find(t => t.type === 'page');
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((done, fail) => { ws.onopen = done; ws.onerror = () => fail(new Error('could not reach the page')); });
  let next = 0;
  const waiting = new Map();
  ws.onmessage = e => { const m = JSON.parse(e.data); if (waiting.has(m.id)) { waiting.get(m.id)(m); waiting.delete(m.id); } };
  const send = (method, params = {}) => new Promise((done, fail) => {
    const id = ++next;
    waiting.set(id, m => m.error ? fail(new Error(`${method}: ${m.error.message}`)) : done(m.result));
    ws.send(JSON.stringify({ id, method, params }));
  });
  await send('Page.enable');
  await send('Emulation.setDeviceMetricsOverride', { width: +w, height: +h, deviceScaleFactor: 1, mobile: false });
  for (const f of frames) {
    await send('Page.navigate', { url: `${url}?f=${f}` });
    let ready = false;
    for (let i = 0; i < 300 && !ready; i++) { // the page marks itself once its frame is drawn
      await sleep(100);
      ready = (await send('Runtime.evaluate', { expression: `location.search === '?f=${f}' && document.body.classList.contains('ready')` })).result.value;
    }
    if (!ready) throw new Error(`frame ${f} was not drawn in 30 seconds`);
    const shot = await send('Page.captureScreenshot', { format: 'png' });
    writeFileSync(join(dir, String(f).padStart(3, '0') + '.png'), Buffer.from(shot.data, 'base64'));
  }
  ws.close();
} finally {
  chrome.kill();
  await sleep(300);
  try { rmSync(profile, { recursive: true, force: true }); } catch {}
}

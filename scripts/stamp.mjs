// Version stamps: every page asks for this site's scripts and styles with ?v=<hash of the file>, so a browser that kept an
// older copy (GitHub Pages lets it keep files about 10 minutes) can't run an old script against a new page, or the reverse.
//
//   node scripts/stamp.mjs           stamp every page (run it after changing any .js or .css, before committing)
//   node scripts/stamp.mjs --check   change nothing; exit 1 and name the pages that are out of date
//
// Each page gets:
//   - its <script type="module" src="x.js"> and <link rel="stylesheet" href="x.css"> as x.js?v=… and x.css?v=…
//   - an import map (one is added if the page has none) mapping every script and style of this site, "./x.js", to
//     "./x.js?v=…", so the scripts' imports of each other (import … from './x.js'), their import()s, and anything a script
//     loads by import.meta.resolve (dots.js, the dot worker; app.js, dotlook.css) get the stamped address without the
//     scripts themselves changing.
// A page's own entries in the map (three, d3-geo, …) stay as they are. Pages in scripts/ are tools for making images, not
// pages people visit, and are left alone.
import { createHash } from 'node:crypto';
import { execSync } from 'node:child_process';
import { readFileSync, writeFileSync, readdirSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const check = process.argv.includes('--check');
const files = readdirSync(ROOT);
const hash = f => createHash('sha1').update(readFileSync(join(ROOT, f))).digest('hex').slice(0, 10);
// only files git tracks go in the maps, so a page never names a local, git-ignored file (CLAUDE.md: keep unclear data local)
const tracked = new Set(execSync('git ls-files', { cwd: ROOT, encoding: 'utf8' }).split('\n'));
const scripts = files.filter(f => f.endsWith('.js') && tracked.has(f)).sort();
const styles = files.filter(f => f.endsWith('.css') && tracked.has(f)).sort();
const v = new Map([...scripts, ...styles].map(f => [f, hash(f)]));
const esc = s => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

const stale = [];
for (const page of files.filter(f => f.endsWith('.html')).sort()) {
  const before = readFileSync(join(ROOT, page), 'utf8');
  const nl = before.includes('\r\n') ? '\r\n' : '\n';
  let html = before;
  // script and stylesheet addresses
  for (const f of scripts) html = html.replace(new RegExp(`(<script[^>]*\\bsrc=")${esc(f)}(?:\\?v=[0-9a-f]*)?(")`, 'g'), `$1${f}?v=${v.get(f)}$2`);
  for (const f of styles) html = html.replace(new RegExp(`(<link[^>]*\\bhref=")${esc(f)}(?:\\?v=[0-9a-f]*)?(")`, 'g'), `$1${f}?v=${v.get(f)}$2`);
  // the import map, for pages that load a script of this site as a module
  if (/<script type="module"[^>]*\bsrc="(?!https?:)/.test(html)) {
    const ours = Object.fromEntries([...scripts, ...styles].map(f => [`./${f}`, `./${f}?v=${v.get(f)}`]));
    const m = html.match(/<script type="importmap">([\s\S]*?)<\/script>/);
    const theirs = m ? Object.fromEntries(Object.entries(JSON.parse(m[1]).imports || {}).filter(([k]) => !k.startsWith('./'))) : {};
    const lines = Object.entries({ ...theirs, ...ours }).map(([k, val]) => `  ${JSON.stringify(k)}: ${JSON.stringify(val)}`);
    const map = `<script type="importmap">${nl}{ "imports": {${nl}${lines.join(`,${nl}`)}${nl}} }${nl}</script>`;
    html = m ? html.replace(m[0], () => map) : html.replace(/<script type="module"/, () => `${map}${nl}<script type="module"`);
  }
  if (html === before) continue;
  stale.push(page);
  if (!check) writeFileSync(join(ROOT, page), html);
}
if (check) {
  if (stale.length) { console.error(`Out of date: ${stale.join(', ')}. Run: node scripts/stamp.mjs`); process.exit(1); }
  console.log('Every page is stamped.');
} else console.log(stale.length ? `Stamped ${stale.length} pages: ${stale.join(', ')}` : 'Every page was already stamped.');

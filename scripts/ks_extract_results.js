// Browser extraction for Kansas's 2026 results (docs/records/kansas.md). ent.sos.ks.gov answers plain scripts and in-page fetch()
// with a Cloudflare 403, so its pages are read the way a person reads them: open each page in a normal Chrome tab, one at a
// time, and read what's on screen. No browser user agent on scripts, no way around the block.
//
// How it was run (Claude in Chrome, 2026-11-08; any browser's console works the same):
//   1. Open https://ent.sos.ks.gov/kssos_ent.html and paste this whole file into the console. It keeps itself in sessionStorage,
//      which lasts as long as the tab, and reads the page.
//   2. For each county page listed in the page's county menu (allen.html, anderson.html, ...): open it in the same tab and run
//      eval(sessionStorage.ksExtract)
//   3. Back on any page of the site, run
//      eval(sessionStorage.ksExtract); ksSave()
//      which downloads ks-results-extract.json. Save it as data/raw/ks/results/ks-results-extract.json. It holds the six statewide
//      races and the site's own notes, as printed on screen. scripts/build_ks_results.py makes every check.
var ksSource = String.raw`
(() => {
  const OFFICES = ['United States Senate', 'Governor / Lt. Governor', 'Secretary of State', 'Attorney General', 'State Treasurer', 'Commissioner of Insurance'];
  const num = s => { if (!/^[\d,]+$/.test(s)) throw new Error('not a number: ' + s); return +s.replace(/,/g, ''); };
  const lines = el => el.innerText.split('\n').map(s => s.trim()).filter(Boolean);
  const page = location.pathname.split('/').pop();
  const text = document.body.innerText;
  const stamp = re => (text.match(re) || [])[1] || null;
  const rec = { page, heading: stamp(/Results - ([^\n]+)/), lastUpdated: stamp(/Last Updated: ([^\n]+)/), countyLastReported: stamp(/County Last Reported: ([^\n]+)/), races: {} };
  if (page === 'kssos_ent.html') {
    // The statewide page's races share a pane: each one's lines start at its heading.
    const all = lines(document.querySelector('.tab-content'));
    for (const office of OFFICES) {
      const at = all.indexOf(office), prec = all[at + 1].match(/^Precincts Reporting: (\d+) of (\d+)$/);
      if (at < 0 || !prec) throw new Error('no statewide race ' + office);
      const cands = [];
      let i = at + 2;
      while (all[i] !== 'Total Votes') {
        if (/^(Votes|%)$/.test(all[i])) { i++; continue; }
        cands.push({ name: all[i], votes: num(all[i + 1]), pct: all[i + 2] }); i += 3;
      }
      rec.races[office] = { reporting: +prec[1], precincts: +prec[2], candidates: cands, totalVotes: num(all[i + 1]) };
    }
    rec.notes = (text.match(/Please note the following[\s\S]*?deeming the results official\./) || [null])[0];
    rec.schedule = (text.match(/This page will be updated[^\n]*/) || [null])[0];
    rec.step1 = (document.body.textContent.match(/Election night results are unofficial results[^\n]*/) || [null])[0];
    rec.counties = [...document.querySelectorAll('select option')].map(o => o.value).filter(v => v.endsWith('.html') && v !== page && !v.includes('#'));
  } else {
    for (const race of document.querySelectorAll('#party-county-all .race')) {
      const office = race.querySelector('h3')?.innerText.trim();
      if (!OFFICES.includes(office)) continue;
      const all = lines(race), prec = all[1].match(/^County Precincts Reporting: (\d+) of (\d+)$/);
      if (!prec) throw new Error('no precinct line in ' + office);
      const cands = [];
      let i = all.indexOf('State %') + 1;
      while (i + 4 < all.length && !/^(View Detailed Map|Back to Top)$/.test(all[i])) {
        cands.push({ name: all[i], votes: num(all[i + 1]), pct: all[i + 2], stateVotes: num(all[i + 3]), statePct: all[i + 4] }); i += 5;
      }
      rec.races[office] = { reporting: +prec[1], precincts: +prec[2], candidates: cands };
    }
  }
  sessionStorage.setItem('ks:' + page, JSON.stringify(rec));
  return page + ' ' + rec.heading + ' ' + rec.lastUpdated + ' races=' + Object.keys(rec.races).length;
})()`;
try { sessionStorage.ksExtract = ksSource + ';'; } catch {}
function ksSave() {
  const pages = Object.keys(sessionStorage).filter(k => k.startsWith('ks:')).sort().map(k => JSON.parse(sessionStorage[k]));
  const out = { source: 'https://ent.sos.ks.gov/kssos_ent.html', extractedBy: 'scripts/ks_extract_results.js', retrieved: new Date().toISOString(), pages };
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([JSON.stringify(out, null, 1)], { type: 'application/json' }));
  a.download = 'ks-results-extract.json';
  a.click();
  return pages.length + ' pages saved';
}
eval(ksSource);

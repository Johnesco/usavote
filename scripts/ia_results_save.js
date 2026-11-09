// Saves Iowa's Nov. 3, 2026 results files, byte for byte, from a browser tab that has the results site open:
//   https://electionresults.iowa.gov/IA/127077/web.345435/#/reporting
// The site answers plain scripts with a 403 and that isn't to be worked around, so this runs in the page (browser console or
// Claude in Chrome). Chrome lets one such download through per tab, so every file goes into one JSON bundle, as base64
// with its SHA-256. Then unpack it, which checks each hash:
//   python scripts/ia_results_unpack.py <Downloads>/ia-<version>-bundle.json
const SAVE = ['reports/summary.zip', 'reports/detailtxt.zip', 'json/en/summary.json', 'json/en/electionsettings.json',
  'json/status.json', 'json/sum.json', 'json/ALL.json', 'json/details.json', 'json/en/nav.json'];
const ver = (await (await fetch('/IA/127077/current_ver.txt')).text()).trim();
const bundle = { source: location.origin, election: '/IA/127077/', version: ver, savedAt: new Date().toISOString(), files: {} };
for (const path of SAVE) {
  const res = await fetch(`/IA/127077/${ver}/${path}`);
  if (!res.ok) throw new Error(`${path}: HTTP ${res.status}`);
  const bytes = new Uint8Array(await res.arrayBuffer());
  const sha256 = [...new Uint8Array(await crypto.subtle.digest('SHA-256', bytes))].map(b => b.toString(16).padStart(2, '0')).join('');
  let bin = '';
  for (let i = 0; i < bytes.length; i += 8192) bin += String.fromCharCode(...bytes.subarray(i, i + 8192));
  bundle.files[path] = { sha256, size: bytes.length, base64: btoa(bin) };
}
const a = document.createElement('a');
a.href = URL.createObjectURL(new Blob([JSON.stringify(bundle)], { type: 'application/json' }));
a.download = `ia-${ver}-bundle.json`;
a.click();
Object.entries(bundle.files).map(([p, f]) => `${p} ${f.size} ${f.sha256.slice(0, 16)}`).join(' | ');

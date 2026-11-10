"""Record what's saved in data/raw/id/results/ (git-ignored): when, from where, and each file's SHA-256, in SAVED.json. It also turns the
summary PDF into report-summary.txt with pdftotext (Poppler), for scripts/build_id_results.py. It downloads nothing.

The files were saved on 2026-11-08 (Mountain) by curl with no options other than following redirects, from the URLs in FILES. A request from
Python's urllib to the same site got HTTP 403 that evening, so this isn't a download script: that refusal wasn't worked around. If curl is
refused later too, save the files from a browser instead, and say so in docs/records/idaho.md.

Run, after saving:  python scripts/id_results_record.py
"""
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

RAW = Path(__file__).resolve().parent.parent / "data" / "raw" / "id" / "results"
SITE = "https://results.voteidaho.gov"
API = f"{SITE}/results/public/api"
J = f"{SITE}/cdn/results/8c9d6490-6c2e-460e-8e42-0d1c8609ce42"  # the state's id on the site; election.json lists each report's file name
FILES = {
    "export-nov2026.json": f"{SITE}/cdn/results/id/export-nov2026.json",
    "election.json": f"{API}/elections/id/nov2026",
    "data.json": f"{API}/elections/id/nov2026/data",
    "localities.json": f"{API}/elections/id/nov2026/localities",
    "vr.json": f"{API}/elections/id/nov2026/vr",
    "jurisdiction.json": f"{API}/jurisdictions/id",
    "report-results.xlsx": f"{J}/Results_de904bcd-2e23-44f8-93f2-7b88eeca9079.xlsx",
    "report-ballots-cast.xlsx": f"{J}/Ballots%20Cast%20by%20Precinct_f3bf6f17-fead-4a91-85b9-62e50d6128d6.xlsx",
    "report-summary.pdf": f"{J}/Summary%20Results%20with%20Contest-Level%20Details_07f6ba47-02cd-451f-970c-7b5f0b8eac1d.PDF",
}
subprocess.run(["pdftotext", "-layout", str(RAW / "report-summary.pdf"), str(RAW / "report-summary.txt")], check=True)
files = {}
for name, url in [*FILES.items(), ("report-summary.txt", "made from report-summary.pdf by pdftotext -layout")]:
    body = (RAW / name).read_bytes()
    files[name] = dict(url=url, bytes=len(body), sha256=hashlib.sha256(body).hexdigest())
    print(f"{name}: {len(body):,} bytes, {files[name]['sha256'][:16]}")
when = datetime.fromtimestamp((RAW / "export-nov2026.json").stat().st_mtime, timezone.utc)  # the file's own save time
(RAW / "SAVED.json").write_text(json.dumps(dict(savedAt=when.isoformat(timespec="seconds"), files=files), indent=1), encoding="utf-8")
print("saved at", when.isoformat(timespec="seconds"))

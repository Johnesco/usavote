"""Save South Dakota's Nov. 3, 2026 results pages and files into data/raw/sd/results/, and record what was saved (docs/records/south-dakota.md).

Uses plain curl with its own user agent. The Statewide Export is a form post on the site's Exports page, sent once, as the page's link does.
Census files are saved by hand; see the record.

Run:  python scripts/sd_results_save.py
"""
import hashlib
import html
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "sd" / "results"
BASE = "https://electionresults.sd.gov/"
PAGES = {
    "home.html": "",
    "resultsSW.html": "resultsSW.aspx?type=SWR&map=CTY",
    "results-sw-cty.csv": "resultsCSV.aspx?text=All&type=SWR&map=CTY",
    "provisional.html": "ProvisionalBallots.aspx",
    "recounts.html": "ResultsSW.aspx?type=RECOUNT",
    "terminology.html": "ElectionTerminology.aspx",
    "media.html": "ResultsMedia.aspx",
}
EXPORT_PAGE = BASE + "ResultsExport.aspx"
COOKIES = RAW / "cookies.tmp"

RAW.mkdir(parents=True, exist_ok=True)
for name, path in PAGES.items():
    subprocess.run(["curl", "-sS", "-f", "-m", "90", "-o", str(RAW / name), BASE + path], check=True)

# the Statewide Export: the Exports page's own form fields, with its link's target
subprocess.run(["curl", "-sS", "-f", "-m", "90", "-c", str(COOKIES), "-o", str(RAW / "export.html"), EXPORT_PAGE], check=True)
page = (RAW / "export.html").read_text(encoding="utf-8", errors="replace")
fields = {n: html.unescape(v) for n, v in re.findall(r'<input type="hidden" name="([^"]+)"[^>]*?value="([^"]*)"', page)}
fields.update({"__EVENTTARGET": "ctl00$MainContent$Statewide", "__EVENTARGUMENT": ""})
post = [a for n, v in fields.items() for a in ("--data-urlencode", f"{n}={v}")]
subprocess.run(["curl", "-sS", "-f", "-m", "120", "-b", str(COOKIES), "-o", str(RAW / "statewide-export.xlsx"), *post, EXPORT_PAGE], check=True)
COOKIES.unlink()

names = [*PAGES, "export.html", "statewide-export.xlsx"]
record = dict(savedAt=datetime.now(timezone.utc).isoformat(), site=BASE, sha256={n: hashlib.sha256((RAW / n).read_bytes()).hexdigest() for n in names})
(RAW / "SAVED.json").write_text(json.dumps(record, indent=1), encoding="utf-8")
for n in names:
    print(n, record["sha256"][n][:16])

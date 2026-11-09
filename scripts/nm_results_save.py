"""Save New Mexico's Nov. 3, 2026 results into data/raw/nm/results/, with plain GET requests and Python's own user agent.

Saves the results site's pages and statewide CSV exports, and each federal and statewide contest's county rows as the site's own
pages read them (the JSON service behind each contest's "County Results" button). The site's "County Level" export buttons are
form postbacks, so they weren't used. SAVED.json lists every file with its URL, size and SHA-256. See docs/records/new-mexico.md.

Run:  python scripts/nm_results_save.py
"""
import hashlib
import json
import re
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "raw" / "nm" / "results"
SITE = "https://electionresults.sos.nm.gov/"
SERVICE = "https://nmresultswebservice.azurewebsites.us/NMResultsAjax.svc/GetMapData"
TERMS = "https://www.sos.nm.gov/disclaimer/"

saved = []


def get(url, name):
    with urllib.request.urlopen(url, timeout=120) as r:
        body = r.read()
    (OUT / name).write_bytes(body)
    saved.append(dict(file=name, url=url, bytes=len(body), sha256=hashlib.sha256(body).hexdigest()))
    time.sleep(0.5)
    return body


OUT.mkdir(parents=True, exist_ok=True)
when = datetime.now(timezone.utc).isoformat(timespec="seconds")
for name, path in {
    "media.html": "ResultsMedia.aspx",
    "terminology.html": "resultsElectionTerminology.aspx",
    "county-updated.html": "resultsCountyLastUpdated.aspx",
    "recounts.html": "ResultsSW.aspx?type=RECOUNT",
    "turnout.html": "VoterTurnoutDetails.aspx?map=TURN",
    "statewide.csv": "resultsCSV.aspx?text=All&type=SW&map=CTY",
    "federal.csv": "resultsCSV.aspx?text=All&type=FED&map=CTY",
}.items():
    get(SITE + path, name)
get(TERMS, "disclaimer.html")

for kind, name in (("SW", "statewide.html"), ("FED", "federal.html")):
    page = get(f"{SITE}resultsSW.aspx?type={kind}&map=CTY", name).decode("utf-8")
    races = dict(re.findall(r'value="County Level" raceid="(\d+)" party="[^"]*" officeseqno="(\d+)"', page))
    assert races, kind
    for race, osn in races.items():
        get(f"{SERVICE}?type={kind}&category=CTY&raceID={race}&osn={osn}&county=0&party=0", f"county-{race}.json")

(OUT / "SAVED.json").write_text(json.dumps(dict(savedAt=when, files=saved), indent=1), encoding="utf-8")
print(f"saved {len(saved)} files at {when}")

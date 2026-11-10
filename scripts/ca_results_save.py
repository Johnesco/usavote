"""Save California's Nov. 3, 2026 results from the Secretary of State's results API into data/raw/ca/results/, and record what was
saved (docs/records/california.md).

The API (api.sos.ca.gov/returns) feeds the state's results site, electionresults.sos.ca.gov. Each statewide race has a statewide
file, and a file per county that holds that county's results and the statewide results. Uses plain curl, one request at a time.

Run:  python scripts/ca_results_save.py
"""
import hashlib
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "ca" / "results"
API = "https://api.sos.ca.gov/returns/"
RACES = ["governor", "lieutenant-governor", "attorney-general", "secretary-of-state", "controller", "treasurer",
         "insurance-commissioner", "superintendent-of-public-instruction", "ballot-measures"]


def get(path, out):
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["curl", "-sS", "-f", "-m", "60", "-o", str(out), API + path], check=True)
    json.loads(out.read_text(encoding="utf-8"))  # stops on anything that isn't JSON
    time.sleep(0.2)


get("status", RAW / "status.json")
counties = [k for k in json.loads((RAW / "status.json").read_text(encoding="utf-8")) if k != "statewide"]
assert len(counties) == 58, len(counties)
for race in RACES:
    get(race, RAW / race / "statewide.json")
    if race == "ballot-measures":
        continue
    for c in counties:
        get(f"{race}/county/{c}", RAW / race / f"{c}.json")

files = sorted(p for p in RAW.rglob("*.json") if p.name != "SAVED.json")
record = dict(savedAt=datetime.now(timezone.utc).isoformat(), api=API,
              sha256={p.relative_to(RAW).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
(RAW / "SAVED.json").write_text(json.dumps(record, indent=1), encoding="utf-8")
print(len(files), "files saved")

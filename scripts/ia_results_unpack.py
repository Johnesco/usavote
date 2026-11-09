"""Unpack the bundle scripts/ia_results_save.js saves into data/raw/ia/results/, stopping if a file's SHA-256 doesn't match.

Run:  python scripts/ia_results_unpack.py <path to ia-<version>-bundle.json>
"""
import base64
import hashlib
import json
import sys
import zipfile
from pathlib import Path

RAW = Path(__file__).resolve().parent.parent / "data" / "raw" / "ia" / "results"
RAW.mkdir(parents=True, exist_ok=True)
source = Path(sys.argv[1])
bundle = json.loads(source.read_text(encoding="utf-8"))
for path, f in bundle["files"].items():
    data = base64.b64decode(f["base64"])
    assert hashlib.sha256(data).hexdigest() == f["sha256"] and len(data) == f["size"], path
    out = RAW / path.split("/")[-1]
    out.write_bytes(data)
    print(f"{out.name:26} {len(data):8,} {f['sha256']}")
    if out.suffix == ".zip":
        with zipfile.ZipFile(out) as z:
            for n in z.namelist():
                print(f"  contains {n} ({z.getinfo(n).file_size:,} bytes)")
                (RAW / f"{out.stem}-{n}").write_bytes(z.read(n))
(RAW / "SAVED.json").write_text(json.dumps({
    "source": bundle["source"], "election": bundle["election"], "version": bundle["version"], "savedAt": bundle["savedAt"],
    "files": {p: f["sha256"] for p, f in bundle["files"].items()},
}, indent=1), encoding="utf-8")
print("saved at", bundle["savedAt"], "version", bundle["version"])

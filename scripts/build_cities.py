"""Build data/cities.json: Texas cities and towns for the reference labels on the maps (cities.js).

Source: the 2020 Census Redistricting Data (P.L. 94-171) geographic header for Texas, the same file
scripts/build_blockgroups.py downloads into data/raw/census-dl/pl/. Each place (summary level 160) has its name, 2020
population (POP100) and an internal point. Kept: every incorporated city, town and village with at least MIN_CITY
people, and census-designated places (unincorporated communities such as The Woodlands or Atascocita) with at least
MIN_CDP, since those are big enough that readers know them by name.

Output: { meta, cities: [[name, lon, lat, population], ...] } sorted by population, largest first.
Run:  python scripts/build_cities.py [ok|ks|sc|oh]    (each state's file goes into its own folder, such as data/ok/)
"""
import io
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ST = sys.argv[1] if len(sys.argv) > 1 else "tx"
PL_ZIP = ROOT / {"tx": "data/raw/census-dl/pl/tx2020.pl.zip", "ok": "data/raw/ok/census/ok2020.pl.zip", "ks": "data/raw/ks/census/ks2020.pl.zip", "sc": "data/raw/sc/census/sc2020.pl.zip", "oh": "data/raw/oh/census/oh2020.pl.zip"}[ST]
PL_URL = "https://www2.census.gov/programs-surveys/decennial/2020/data/01-Redistricting_File--PL_94-171/" + {"tx": "Texas/tx2020.pl.zip", "ok": "Oklahoma/ok2020.pl.zip", "ks": "Kansas/ks2020.pl.zip", "sc": "South_Carolina/sc2020.pl.zip", "oh": "Ohio/oh2020.pl.zip"}[ST]
LARGEST = {"tx": "Houston", "ok": "Oklahoma City", "ks": "Wichita", "sc": "Charleston", "oh": "Columbus"}[ST]
OUT = ROOT / {"tx": "data/cities.json", "ok": "data/ok/cities.json", "ks": "data/ks/cities.json", "sc": "data/sc/cities.json", "oh": "data/oh/cities.json"}[ST]
MIN_CITY, MIN_CDP = 500, 10000

if not PL_ZIP.exists():
    raise SystemExit(f"{PL_ZIP} is missing: run scripts/build_blockgroups.py first (it downloads {PL_URL})")

cities = []
with zipfile.ZipFile(PL_ZIP).open(f"{ST}geo2020.pl") as f:
    for line in io.TextIOWrapper(f, encoding="latin-1"):
        r = line.rstrip("\n").split("|")
        # place totals only (summary level 160, no geographic component or variant)
        if r[2] != "160" or r[3] != "00" or r[4] != "00":
            continue
        name, funcstat, pop, lat, lon = r[86], r[88], int(r[90]), float(r[92]), float(r[93])
        incorporated = funcstat == "A"
        if pop >= (MIN_CITY if incorporated else MIN_CDP):
            cities.append([name, round(lon, 4), round(lat, 4), pop])
cities.sort(key=lambda c: -c[3])
print(f"{len(cities)} places; largest: {cities[:3]}")
assert cities[0][0] == LARGEST

out = {
    "meta": {
        "source": "U.S. Census Bureau, 2020 Census Redistricting Data (P.L. 94-171), geographic header, places (summary level 160)",
        "sourceUrl": PL_URL,
        "kept": f"incorporated places with at least {MIN_CITY} people; census-designated places with at least {MIN_CDP}",
        "row": "[name, lon, lat (internal point), 2020 population]",
    },
    "cities": cities,
}
path = OUT
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(out, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
print(f"wrote {path} ({path.stat().st_size / 1e3:.0f} KB)")

"""Build data/cities.json: Texas cities and towns for the reference labels on the maps (cities.js).

Source: the 2020 Census Redistricting Data (P.L. 94-171) geographic header for Texas, the same file
scripts/build_blockgroups.py downloads into data/raw/census-dl/pl/. Each place (summary level 160) has its name, 2020
population (POP100) and an internal point. Kept: every incorporated city, town and village with at least MIN_CITY
people, and census-designated places (unincorporated communities such as The Woodlands or Atascocita) with at least
MIN_CDP, since those are big enough that readers know them by name.

Output: { meta, cities: [[name, lon, lat, population], ...] } sorted by population, largest first.
Run:  python scripts/build_cities.py
"""
import io
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PL_ZIP = ROOT / "data/raw/census-dl/pl/tx2020.pl.zip"
PL_URL = "https://www2.census.gov/programs-surveys/decennial/2020/data/01-Redistricting_File--PL_94-171/Texas/tx2020.pl.zip"
MIN_CITY, MIN_CDP = 500, 10000

if not PL_ZIP.exists():
    raise SystemExit(f"{PL_ZIP} is missing: run scripts/build_blockgroups.py first (it downloads {PL_URL})")

cities = []
with zipfile.ZipFile(PL_ZIP).open("txgeo2020.pl") as f:
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
assert cities[0][0] == "Houston"

out = {
    "meta": {
        "source": "U.S. Census Bureau, 2020 Census Redistricting Data (P.L. 94-171), geographic header, places (summary level 160)",
        "sourceUrl": PL_URL,
        "kept": f"incorporated places with at least {MIN_CITY} people; census-designated places with at least {MIN_CDP}",
        "row": "[name, lon, lat (internal point), 2020 population]",
    },
    "cities": cities,
}
path = ROOT / "data" / "cities.json"
path.write_text(json.dumps(out, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
print(f"wrote {path} ({path.stat().st_size / 1e3:.0f} KB)")

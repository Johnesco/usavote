"""Build data/wv/results-2026.json: West Virginia's Nov. 3, 2026 U.S. Senate race, by county. The results adapter for West Virginia
(docs/PIPELINE.md, Part 6; record in docs/records/west-virginia.md).

U.S. Senate is the only contest on the ballot statewide between candidates (the rest are district, county or ballot questions).

Source: data/raw/wv/results/senate-extract.json (not committed), the race's county figures read in Chrome from the results site's own
files, because the site returns 403 to plain scripts; its note says how. Land area and county codes: the 2020 Census redistricting
file's county records (data/raw/wv/census/wv2020.pl.zip).

Stops unless: all 55 counties are there once and match the Census names; each county's candidates add up to its total; the counties
add up to the statewide row, candidate by candidate; every precinct has reported; and there's exactly one Democrat and one Republican.

Run:  python scripts/build_wv_results.py
"""
import io
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "wv"
OUT = ROOT / "data" / "wv" / "results-2026.json"
SITE_URL = "https://results.enr.clarityelections.com/WV/127496/web.345435/#/summary"
SQ_M_PER_SQ_MI = 2_589_988.110336
COUNTIES = 55
PARTY = {"DEM": "DEM", "REP": "REP", "CST": "CON"}  # CON: the pages call it Constitution


def title(name):
    return " ".join(w.capitalize() if not w.endswith(".") else w[0] + "." for w in name.split())


counties = []
with zipfile.ZipFile(RAW / "census" / "wv2020.pl.zip").open("wvgeo2020.pl") as f:
    for line in io.TextIOWrapper(f, encoding="latin-1"):
        r = line.rstrip("\n").split("|")
        if r[2] == "050" and r[3] == "00" and r[4] == "00":
            counties.append(dict(fips=r[8].split("US")[1], name=r[86].removesuffix(" County"), landSqMi=round(float(r[-13]) / SQ_M_PER_SQ_MI, 3)))
counties.sort(key=lambda c: c["fips"])
assert len(counties) == COUNTIES
index = {c["name"]: i for i, c in enumerate(counties)}

x = json.loads((RAW / "results" / "senate-extract.json").read_text(encoding="utf-8"))
assert x["contest"] == "U.S. SENATOR" and x["precincts"][0] == x["precincts"][1], x["precincts"]
parties = [PARTY[p] for _, p in x["candidates"]]
assert parties.count("DEM") == 1 and parties.count("REP") == 1
table = [None] * COUNTIES
sums = [0] * len(parties)
for name, *vals in x["rows"]:
    *votes, total = vals
    assert name in index and table[index[name]] is None, name
    assert sum(votes) == total and len(votes) == len(parties), name
    row = [0, 0, 0, total]
    for k, (p, v) in enumerate(zip(parties, votes)):
        row[{"DEM": 0, "REP": 1}.get(p, 2)] += v
        sums[k] += v
    table[index[name]] = row
assert all(table), "a county is missing"
assert sums + [sum(sums)] == x["statewide"], "counties don't add up to the statewide figures"
assert sum(r[3] for r in table) <= x["ballotsCast"]
assert all(r[3] >= 10 for r in table)

cs = sorted((dict(name=title(n), last=title(n).split()[-1], party=PARTY[p], incumbent=(n == "SHELLEY MOORE CAPITO"), votes=v)
             for (n, p), v in zip(x["candidates"], sums)), key=lambda c: -c["votes"])
link = lambda url, text: f'<a href="{url}" target="_blank" rel="noopener">{text}</a>'
UPDATED = "Nov. 9, 2026, 4:36 PM ET"
RETRIEVED = "2026-11-09"
out = dict(
    meta=dict(
        election="2026 General Election (Nov. 3, 2026)",
        resultsSource="West Virginia Secretary of State, Election Night Reporting (unofficial)",
        resultsUrl=SITE_URL,
        resultsUpdated=UPDATED, retrieved=RETRIEVED,
        reporting=dict(counties=COUNTIES, countiesReporting=COUNTIES, precincts=x["precincts"][1], precinctsReporting=x["precincts"][0], ballotsCast=x["ballotsCast"], registered=x["registered"]),
        landSource="U.S. Census Bureau, 2020 Census Redistricting Data (P.L. 94-171), county land area (AREALAND)",
        countyRow="counties[i] = [Democratic votes, Republican votes, all other votes, total votes] for meta.counties[i]",
        sources=[
            f"West Virginia Secretary of State, {link(SITE_URL, 'Election Night Reporting')}, Nov. 3, 2026 general election: unofficial results by county, as of {UPDATED}, retrieved {RETRIEVED}, with all {x['precincts'][1]:,} precincts reporting. The figures were read from the results site's own data files in a browser.",
            "Only U.S. Senate is here: it's the one contest between candidates on the ballot statewide. U.S. House has two districts. Constitutional amendments, and district and county races, aren't here either.",
            f"U.S. Census Bureau, {link('https://www.census.gov/programs-surveys/decennial-census/about/rdo/summary-files.html', '2020 Census Redistricting Data')} (P.L. 94-171): county land area and codes, cities, and each block's location and adults, for placing dots within a county.",
            f"U.S. Census Bureau, {link('https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html', '2020 TIGER/Line&reg; Shapefiles')}, tabulation blocks: where people were counted, for keeping dots off empty land. TIGER/Line&reg; is a registered trademark of the Census Bureau; the land grid here isn't a Census Bureau product.",
            f"U.S. Census Bureau, {link('https://www.census.gov/geographies/mapping-files/time-series/geo/carto-boundary-file.html', 'Cartographic Boundary Files')}, 2017 counties, via {link('https://github.com/topojson/us-atlas', 'us-atlas')} v3.0.1 (counties-10m.json).",
            f"Software: {link('https://threejs.org', 'three.js')} r160, {link('https://github.com/d3/d3-geo', 'd3-geo')} 3.1.1, {link('https://github.com/topojson/topojson-client', 'topojson-client')} 3.1.0.",
        ],
    ),
    counties=counties,
    races=[dict(id="u-s-senate", office="U.S. Senator", label="U.S. Senate", group="Statewide", candidates=cs, counties=table)],
)
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(out, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
print(f"OK: U.S. Senate on {COUNTIES} counties; {[(c['name'], c['party'], c['votes']) for c in cs]}; D carried {sum(r[0] > r[1] for r in table)} counties; fewest votes {min((r[3], counties[i]['name']) for i, r in enumerate(table))}")

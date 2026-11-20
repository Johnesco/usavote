"""Build data/la/results-2026.json: Louisiana's Nov. 3, 2026 U.S. Senate race, by parish. The results adapter for Louisiana
(docs/PIPELINE.md, Part 6; record in docs/records/louisiana.md).

U.S. Senate is the only statewide race between candidates; the U.S. House races are by district, and two go to a Dec. 12 runoff.
Louisiana's parishes are its counties: the Census gives them county codes, and the files here call them counties.

Source: data/raw/la/results/senate-by-parish.csv (not committed), from the results site's Download Results dialog, and
page-figures.json beside it, the race's statewide figures read off the page. Land area and parish codes: the 2020 Census
redistricting file's county records (data/raw/la/census/la2020.pl.zip).

Stops unless: all 64 parishes are there once and match the Census names; the parishes add up to the statewide figures,
candidate by candidate; every parish and precinct has reported; there's exactly one Democrat and one Republican; and every
parish has at least 10 votes.

Run:  python scripts/build_la_results.py
"""
import csv
import io
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "la"
OUT = ROOT / "data" / "la" / "results-2026.json"
SITE_URL = "https://voterportal.sos.la.gov/graphical"
SQ_M_PER_SQ_MI = 2_589_988.110336
COUNTIES = 64
RETRIEVED = "2026-11-19"


def key(name):  # the results site writes "Lasalle" and "St. John The Baptist"; the Census "LaSalle" and "St. John the Baptist"
    return name.casefold().replace(" ", "").replace(".", "")


counties = []
with zipfile.ZipFile(RAW / "census" / "la2020.pl.zip").open("lageo2020.pl") as f:
    for line in io.TextIOWrapper(f, encoding="latin-1"):
        r = line.rstrip("\n").split("|")
        if r[2] == "050" and r[3] == "00" and r[4] == "00":
            counties.append(dict(fips=r[8].split("US")[1], name=r[86].removesuffix(" Parish"), landSqMi=round(float(r[-13]) / SQ_M_PER_SQ_MI, 3)))
counties.sort(key=lambda c: c["fips"])
assert len(counties) == COUNTIES
index = {key(c["name"]): i for i, c in enumerate(counties)}

page = json.loads((RAW / "results" / "page-figures.json").read_text(encoding="utf-8"))
assert page["status"] == "Official Results" and page["race"] == "U. S. Senator"
assert page["parishes"] == [COUNTIES, COUNTIES] and page["precincts"][0] == page["precincts"][1], "not every parish and precinct has reported"

with open(RAW / "results" / "senate-by-parish.csv", encoding="utf-8-sig", newline="") as f:
    rows = list(csv.reader(f))
head, rows = rows[0], rows[1:]
assert head[:2] == ["Office", "Parish"], head
names = head[2:]  # '"Jamie" Davis (DEM)', 'Julia Letlow (REP)'
parties = [n.rsplit("(", 1)[1].rstrip(")") for n in names]
assert parties.count("DEM") == 1 and parties.count("REP") == 1 and set(parties) <= {"DEM", "REP"}, parties
assert [(n.rsplit(" (", 1)[0], p) for n, p in zip(names, parties)] == [(c[0], c[1]) for c in page["candidates"]], "candidates differ from the page"

table = [None] * COUNTIES
sums = [0] * len(parties)
for office, parish, *vals in rows:
    assert office == page["race"], office
    i = index.get(key(parish))
    assert i is not None and table[i] is None, parish
    votes = [int(v) for v in vals]
    assert len(votes) == len(parties), parish
    row = [0, 0, 0, sum(votes)]
    for k, (p, v) in enumerate(zip(parties, votes)):
        row[{"DEM": 0, "REP": 1}[p]] += v
        sums[k] += v
    table[i] = row
assert all(table), "a parish is missing"
assert sums == [c[2] for c in page["candidates"]] and sum(sums) == page["total"], "parishes don't add up to the statewide figures"
assert all(r[3] >= 10 for r in table)

cs = sorted((dict(name=n.rsplit(" (", 1)[0], last=n.rsplit(" (", 1)[0].split()[-1], party=p, incumbent=False, votes=v)  # Bill Cassidy held the seat
             for n, p, v in zip(names, parties, sums)), key=lambda c: -c["votes"])
link = lambda url, text: f'<a href="{url}" target="_blank" rel="noopener">{text}</a>'
out = dict(
    meta=dict(
        election="2026 General Election (Nov. 3, 2026)",
        resultsSource="Louisiana Secretary of State, Election Results (official results)",
        resultsUrl=SITE_URL,
        resultsUpdated="Nov. 19, 2026", retrieved=RETRIEVED,
        reporting=dict(counties=COUNTIES, countiesReporting=COUNTIES, precincts=page["precincts"][1], precinctsReporting=page["precincts"][0]),
        landSource="U.S. Census Bureau, 2020 Census Redistricting Data (P.L. 94-171), parish land area (AREALAND)",
        countyRow="counties[i] = [Democratic votes, Republican votes, all other votes, total votes] for meta.counties[i]; Louisiana's parishes are its counties",
        sources=[
            f"Louisiana Secretary of State, {link(SITE_URL, 'Election Results')}, Nov. 3, 2026 general election: official results by parish, retrieved {RETRIEVED}, with all {COUNTIES} parishes and {page['precincts'][1]:,} precincts reporting, from the site's own download.",
            "Only U.S. Senate is here: it's the one race between candidates on the ballot statewide. The U.S. House races are by district, and Districts 5 and 6 go to a runoff on Dec. 12, 2026. Legislative, local and ballot-question races aren't here either.",
            "Louisiana's parishes are its counties. Some of this site's menus and labels say county, as the Census Bureau's files do.",
            f"U.S. Census Bureau, {link('https://www.census.gov/programs-surveys/decennial-census/about/rdo/summary-files.html', '2020 Census Redistricting Data')} (P.L. 94-171): parish land area and codes, cities, and each block's location and adults, for placing dots within a parish.",
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
print(f"OK: U.S. Senate on {COUNTIES} parishes; {[(c['name'], c['party'], c['votes']) for c in cs]}; D carried {sum(r[0] > r[1] for r in table)} parishes; "
      f"fewest votes {min((r[3], counties[i]['name']) for i, r in enumerate(table))}; most {max((r[3], counties[i]['name']) for i, r in enumerate(table))}")

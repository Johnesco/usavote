"""Build data/ok/results-2026.json: Oklahoma's Nov. 3, 2026 statewide races, by county. The results adapter for Oklahoma
(docs/PIPELINE.md, Part 6).

Sources, saved by hand from the Export menu at https://results.okelections.gov/OKER/?elecDate=20261103 into data/raw/ok/results/:
  20261103_StateResults.csv, 20261103_CountyResults.csv, 20261103_PrecinctResults.csv
Land area and county codes: the 2020 Census redistricting file's county records (data/raw/ok/census/ok2020.pl.zip).

Maps only races with exactly one Democrat and one Republican. State Treasurer (Republican against Libertarian), the judicial
retention votes and the state questions don't have that shape, and U.S. House and the legislature aren't in this first pass.

Stops unless, for every race: all precincts are reporting, all 77 counties are there, each candidate's counties add up to the
state file, and each candidate's precincts add up to the county file, county by county.

Run:  python scripts/build_ok_results.py
"""
import csv
import io
import json
import re
import zipfile
from collections import defaultdict
from pathlib import Path

from chamber import chamber_race, summary

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "ok"
OUT = ROOT / "data" / "ok" / "results-2026.json"
EXPORT_URL = "https://results.okelections.gov/OKER/?elecDate=20261103"
UPDATED = "Nov. 6, 2026, 6:26 PM"  # the results site's own "Server TLU" stamp when the exports were saved
RETRIEVED = "2026-11-08"
SQ_M_PER_SQ_MI = 2_589_988.110336
COUNTIES = 77

# the file's name for a race: (our id, label, menu group)
RACES = {
    "FOR UNITED STATES SENATOR": ("u-s-senate", "U.S. Senate", "Federal"),
    "FOR GOVERNOR": ("governor", "Governor", "Statewide"),
    "FOR LIEUTENANT GOVERNOR": ("lieutenant-governor", "Lieutenant Governor", "Statewide"),
    "FOR ATTORNEY GENERAL": ("attorney-general", "Attorney General", "Statewide"),
    "FOR SUPERINTENDENT OF PUBLIC INSTRUCTION": ("superintendent", "Superintendent of Public Instruction", "Statewide"),
    "FOR COMMISSIONER OF LABOR": ("labor-commissioner", "Commissioner of Labor", "Statewide"),
    "FOR INSURANCE COMMISSIONER": ("insurance-commissioner", "Insurance Commissioner", "Statewide"),
    "FOR CORPORATION COMMISSIONER": ("corporation-commissioner", "Corporation Commissioner", "Statewide"),
}
SUFFIX = {"SR", "JR", "II", "III", "IV"}


def rows(name):
    with open(RAW / "results" / name, encoding="utf-8", errors="replace", newline="") as f:
        return list(csv.DictReader(f))


def norm(s):
    return re.sub(r"[^A-Z]", "", s.upper())


def word(w):
    """MIKE -> Mike, N'KIYLA -> N'Kiyla, T. -> T.; a word the file already writes in mixed case (MacINTYRE) keeps that."""
    if any(c.islower() for c in w) or w in SUFFIX: return w
    return re.sub(r"[A-Z]+", lambda m: m.group()[0] + m.group()[1:].lower(), w)


def person(name):
    words = name.split()
    last = next(w for w in reversed(words) if w.upper().strip(".") not in SUFFIX)
    return " ".join(map(word, words)), word(last)


# ---------- counties: code, name and land area from the Census file ----------
counties, by_name = [], {}
with zipfile.ZipFile(RAW / "census" / "ok2020.pl.zip").open("okgeo2020.pl") as f:
    for line in io.TextIOWrapper(f, encoding="latin-1"):
        r = line.rstrip("\n").split("|")
        if r[2] == "050" and r[3] == "00" and r[4] == "00":
            name = r[86].removesuffix(" County")
            c = dict(fips=r[8].split("US")[1], name=name, landSqMi=round(float(r[-13]) / SQ_M_PER_SQ_MI, 3))
            counties.append(c); by_name[norm(name)] = c
counties.sort(key=lambda c: c["fips"])
assert len(counties) == COUNTIES, len(counties)
index = {c["fips"]: i for i, c in enumerate(counties)}

state_rows, county_rows, precinct_rows = (rows(f"20261103_{k}Results.csv") for k in ("State", "County", "Precinct"))
# Precinct codes start with the state's two-digit county number: alphabetical, except that Mc sorts before Ma. The check that
# precincts add up to the county file, candidate by candidate, stops the build if this is ever wrong.
code_of = {f"{i + 1:02d}": n for i, n in enumerate(sorted(by_name, key=lambda n: "M0" + n[2:] if n.startswith("MC") else n))}

races, skipped = [], []
for office in dict.fromkeys(r["race_description"] for r in state_rows):
    rows_s = [r for r in state_rows if r["race_description"] == office]
    if not rows_s or rows_s[0]["tot_race_prec"] != "1984" or " COUNTY" in office: continue
    if office not in RACES:
        skipped.append(office); continue
    rid, label, group = RACES[office]
    parties = [r["cand_party"] for r in rows_s]
    assert parties.count("DEM") == 1 and parties.count("REP") == 1, (office, parties)
    assert all(r["race_prec_reporting"] == r["tot_race_prec"] for r in rows_s), (office, "precincts not all reporting")
    state_total = {r["cand_name"]: int(r["cand_tot_votes"]) for r in rows_s}
    party_of = {r["cand_name"]: r["cand_party"] for r in rows_s}

    table = [[0, 0, 0, 0] for _ in counties]
    county_cand = defaultdict(int)  # (county, candidate) -> votes
    cand_sum = defaultdict(int)
    seen = set()
    for r in county_rows:
        if r["race_description"] != office: continue
        assert r["race_prec_reporting"] == r["tot_race_prec"], (office, r["county"], "precincts not all reporting")
        c = by_name[norm(r["county"])]; seen.add(c["fips"])
        v = int(r["cand_tot_votes"])
        row = table[index[c["fips"]]]
        k = {"DEM": 0, "REP": 1}.get(r["cand_party"], 2)
        row[k] += v; row[3] += v
        county_cand[(norm(r["county"]), r["cand_name"])] += v
        cand_sum[r["cand_name"]] += v
    assert len(seen) == COUNTIES, (office, len(seen))
    assert dict(cand_sum) == state_total, (office, "counties don't add up to the state file")

    precinct_cand = defaultdict(int)
    for r in precinct_rows:
        if r["race_description"] != office: continue
        precinct_cand[(code_of[r["precinct"][:2]], r["cand_name"])] += int(r["cand_tot_votes"])
    assert dict(precinct_cand) == dict(county_cand), (office, "precincts don't add up to the county file")

    cands = []
    for n, v in sorted(state_total.items(), key=lambda kv: -kv[1]):
        nm, last = person(n)
        cands.append(dict(name=nm, last=last, party=party_of[n], incumbent=False, votes=v))
    races.append(dict(id=rid, office=office, label=label, group=group, candidates=cands, counties=table))

assert sorted(r["office"] for r in races) == sorted(RACES), "statewide races differ from the RACES table"
order = list(RACES)
races.sort(key=lambda r: order.index(r["office"]))
print("left out, not one Democrat against one Republican or not a candidate race:", skipped)

# ---------- U.S. House: every district, added up by county, with each district's own result (scripts/chamber.py) ----------
HOUSE = "FOR UNITED STATES REPRESENTATIVE DISTRICT "
cand_key = lambda r: (person(r["cand_name"])[0], r["cand_party"])
house_votes, house_expect = defaultdict(lambda: defaultdict(dict)), defaultdict(dict)
for r in state_rows:
    if r["race_description"].startswith(HOUSE):
        assert r["race_prec_reporting"] == r["tot_race_prec"], (r["race_description"], "precincts not all reporting")
        house_expect[int(r["race_description"][len(HOUSE):])][cand_key(r)] = int(r["cand_tot_votes"])
for r in county_rows:
    if r["race_description"].startswith(HOUSE):
        assert r["race_prec_reporting"] == r["tot_race_prec"], (r["race_description"], r["county"], "precincts not all reporting")
        house_votes[int(r["race_description"][len(HOUSE):])][index[by_name[norm(r["county"])]["fips"]]][cand_key(r)] = int(r["cand_tot_votes"])
house = chamber_race("u-s-house", "U.S. House", "Federal", HOUSE.strip(), 5, house_votes, COUNTIES, expect=house_expect)
races.append(house)

link = lambda url, text: f'<a href="{url}" target="_blank" rel="noopener">{text}</a>'
out = dict(
    meta=dict(
        election="2026 November General Election (Nov. 3, 2026)",
        resultsSource="Oklahoma State Election Board, OK Election Results (unofficial results; state certification pending)",
        resultsUrl=EXPORT_URL,
        resultsUpdated=UPDATED, retrieved=RETRIEVED,
        landSource="U.S. Census Bureau, 2020 Census Redistricting Data (P.L. 94-171), county land area (AREALAND)",
        countyRow="counties[i] = [Democratic votes, Republican votes, all other votes, total votes] for meta.counties[i]",
        sources=[
            f"Oklahoma State Election Board, {link(EXPORT_URL, 'OK Election Results')}, Nov. 3, 2026 general election: state and county files from the site's Export menu (its precinct file only as a cross-check), as last updated {UPDATED}, retrieved {RETRIEVED}.",
            f"U.S. Census Bureau, {link('https://www.census.gov/programs-surveys/decennial-census/about/rdo/summary-files.html', '2020 Census Redistricting Data')} (P.L. 94-171): county land area and codes, cities, and each block's location and adults, for placing dots within a county; {link('https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html', '2020 TIGER/Line')} blocks for where people were counted.",
            f"U.S. Census Bureau, {link('https://www.census.gov/geographies/mapping-files/time-series/geo/carto-boundary-file.html', 'Cartographic Boundary Files')}, 2017 counties, via {link('https://github.com/topojson/us-atlas', 'us-atlas')} v3.0.1 (counties-10m.json).",
            f"Software: {link('https://threejs.org', 'three.js')} r160, {link('https://github.com/d3/d3-geo', 'd3-geo')} 3.1.1, {link('https://github.com/topojson/topojson-client', 'topojson-client')} 3.1.0.",
        ],
    ),
    counties=counties,
    races=races,
)
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
print(f"OK: {len(races)} races, {COUNTIES} counties, all precincts reporting; counties match the state file and precincts match the counties.")
print(summary(house))
for r in races[:-1]:
    d = next(c for c in r["candidates"] if c["party"] == "DEM"); p = next(c for c in r["candidates"] if c["party"] == "REP")
    print(f"  {r['id']:26} {d['name']} {d['votes']:,} vs {p['name']} {p['votes']:,}; D carried {sum(row[0] > row[1] for row in r['counties'])} counties")

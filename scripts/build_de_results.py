"""Build data/de/results-2026.json: Delaware's Nov. 3, 2026 statewide races by county: U.S. Senate, U.S. House (one at-large
seat), Attorney General, Auditor of Accounts and State Treasurer. The results adapter for Delaware (docs/PIPELINE.md, Part 6;
record in docs/records/delaware.md).

Sources, under data/raw/de/ (not committed):
  results/Election_ByCountyWithWilmington_ID_GE2026.json: Delaware Department of Elections, the results page's "By County" data:
    one row per candidate per contest, with New Castle (and its two parts, Wilmington and the rest), Kent, Sussex and State
  results/Election_StatewideResults_ID_GE2026.json: the results page's statewide totals, with "Results Type" and report time
  results/official-results-4hbv-7brf.csv: Delaware Open Data Portal, "Official Election Results by Office" (License: Public
    Domain), every election since 2023; statewide totals per candidate
  results/*.headers.txt, saved-at.txt: response headers, and when they were saved (UTC)
  census/de2020.pl.zip: county codes, names and land area

Write-in votes are in the Department's separate write-in report, not in these files, so they aren't counted here.

Stops unless: the 3 counties match the Census names; every race's candidates are the same in all three files; each candidate's
counties add up to the county file's State figure, which matches the statewide file and the public-domain CSV; Wilmington plus
the rest of New Castle make New Castle; the statewide file says "OFFICIAL RESULTS" with every election district reported; one
Democrat and one Republican per race, and a majority winner.

Run:  python scripts/build_de_results.py
"""
import csv
import io
import json
import re
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "de"
RES = RAW / "results"
OUT = ROOT / "data" / "de" / "results-2026.json"
PAGE_URL = "https://elections.delaware.gov/results/enr/GE2026.html"
CSV_URL = "https://data.delaware.gov/d/4hbv-7brf"
SQ_M_PER_SQ_MI = 2_589_988.110336
COUNTIES = 3
PARTY = {"Democratic Party": "DEM", "Republican Party": "REP", "Independent Party of Delaware": "IND"}
SUFFIX = {"SR", "JR", "II", "III", "IV"}
# contest title -> id, label, group; in the order the State lists them
RACES = {
    "U.S. Senator": ("u-s-senate", "U.S. Senate", "Federal"),
    "Representative In Congress": ("u-s-house", "U.S. House", "Federal"),
    "Attorney General": ("attorney-general", "Attorney General", "Statewide"),
    "Auditor of Accounts": ("auditor", "Auditor of Accounts", "Statewide"),
    "State Treasurer": ("treasurer", "State Treasurer", "Statewide"),
}
# the files mark no incumbents; these four were elected in 2020 (Coons), 2022 (Jennings, York) and 2024 (McBride)
INCUMBENTS = {"Chris Coons", "Sarah McBride", "Kathy Jennings", "Lydia York"}


def num(v):
    return int(str(v).replace(",", ""))


def nice(name):
    """CHRIS COONS -> Chris Coons; MICHAEL "DR. MIKE" KATZ -> Michael "Dr. Mike" Katz; DAVID C. "DAVE" GRAHAM -> David C. "Dave" Graham"""
    out = []
    for w in name.split():
        core = w.strip('"')
        t = core if core in SUFFIX else "-".join(p[:1] + p[1:].lower() for p in core.split("-"))
        t = re.sub(r"^(Mc)([a-z])", lambda m: m.group(1) + m.group(2).upper(), t)
        out.append(w.replace(core, t))
    return " ".join(out)


def last_name(name):
    return next(w for w in reversed(re.sub(r'"[^"]*"', "", name).split()) if w.upper().strip(".,") not in SUFFIX).strip(",")


load = lambda n: json.loads((RES / n).read_text(encoding="utf-8-sig"))
by_county, statewide = load("Election_ByCountyWithWilmington_ID_GE2026.json"), load("Election_StatewideResults_ID_GE2026.json")
pd = [r for r in csv.DictReader((RES / "official-results-4hbv-7brf.csv").open(encoding="utf-8-sig"))
      if r["ElectionName"] == "2026 General Election"]
assert pd, "no 2026 General Election rows in the public-domain file"
assert {r["Results Type"] for r in statewide} == {"OFFICIAL RESULTS"}
assert all(r["Precincts Reported"] == r["Total Precincts"] for r in statewide)
precincts = statewide[0]["Total Precincts"]

# ---------- counties: code, name and land area from the Census file ----------
counties = []
with zipfile.ZipFile(RAW / "census" / "de2020.pl.zip").open("degeo2020.pl") as f:
    for line in io.TextIOWrapper(f, encoding="latin-1"):
        r = line.rstrip("\n").split("|")
        if r[2] == "050" and r[3] == "00" and r[4] == "00":
            counties.append(dict(fips=r[8].split("US")[1], name=r[86].removesuffix(" County"), landSqMi=round(float(r[-13]) / SQ_M_PER_SQ_MI, 3)))
counties.sort(key=lambda c: c["fips"])
assert [c["name"] for c in counties] == ["Kent", "New Castle", "Sussex"], counties

# ---------- races ----------
races = []
for title, (rid, label, group) in RACES.items():
    rows = [r for r in by_county if r["Contest Title"] == title]
    srows = {r["Candidate Name"]: r for r in statewide if r["Contest Title"] == title}
    prows = {r["CandidateName"]: r for r in pd if r["Office"] == title}
    assert {r["Candidate Name"] for r in rows} == set(srows) == set(prows), (title, "candidates differ between the files")
    tab = [[0, 0, 0, 0] for _ in counties]
    cl = []
    for r in rows:
        assert r["Wilmington"] + r["Rest of New Castle"] == r["New Castle"], (title, r["Candidate Name"])
        assert r["New Castle"] + r["Kent"] + r["Sussex"] == r["State"], (title, r["Candidate Name"], "counties don't add up")
        assert r["State"] == num(srows[r["Candidate Name"]]["Total Votes"]) == num(prows[r["Candidate Name"]]["TotalVotesSum"]), (title, r["Candidate Name"])
        assert r["Party Name"] == srows[r["Candidate Name"]]["Party Name"] == prows[r["Candidate Name"]]["PartyName"]
        p = PARTY[r["Party Name"]]
        for i, c in enumerate(counties):
            v = r[c["name"]]
            tab[i][{"DEM": 0, "REP": 1}.get(p, 2)] += v
            tab[i][3] += v
        n = nice(r["Candidate Name"])
        cl.append(dict(name=n, last=last_name(n), party=p, incumbent=n in INCUMBENTS, votes=r["State"]))
    parties = [c["party"] for c in cl]
    assert parties.count("DEM") == 1 and parties.count("REP") == 1, (title, parties)
    cl.sort(key=lambda c: -c["votes"])
    total = sum(r[3] for r in tab)
    assert 2 * cl[0]["votes"] > total, (title, "no majority")
    races.append(dict(id=rid, office=title, label=label, group=group, candidates=cl, counties=tab))

# ---------- dates ----------
report = datetime.fromisoformat(max(r["ReportTime"] for r in statewide))
UPDATED = f"{report:%b}. {report.day}, {report.year}"
saved = datetime.fromisoformat((RES / "saved-at.txt").read_text().split()[0].replace("Z", "+00:00"))
RETRIEVED = (saved - timedelta(hours=6)).date().isoformat()  # Central

link = lambda url, text: f'<a href="{url}" target="_blank" rel="noopener">{text}</a>'
out = dict(
    meta=dict(
        election="2026 General Election (Nov. 3, 2026)",
        resultsSource="Delaware Department of Elections, 2026 General Election results by county (official)",
        resultsUrl=PAGE_URL,
        resultsUpdated=UPDATED, retrieved=RETRIEVED,
        reporting=dict(counties=COUNTIES, countiesReporting=COUNTIES, precincts=precincts, precinctsReporting=precincts),
        landSource="U.S. Census Bureau, 2020 Census Redistricting Data (P.L. 94-171), county land area (AREALAND)",
        countyRow="counties[i] = [Democratic votes, Republican votes, all other votes, total votes] for meta.counties[i]",
        sources=[
            f"Delaware Department of Elections, {link(PAGE_URL, '2026 General Election results')}, by county: official results, data as of {UPDATED}, with all {precincts} election districts reporting; retrieved {RETRIEVED}.",
            f"Delaware Open Data Portal, {link(CSV_URL, 'Official Election Results by Office')} (provided by the Department of Elections; License: Public Domain): the statewide totals, which the county figures add up to exactly for every candidate.",
            "Write-in votes are in the Department's separate write-in report and aren't counted here. Wilmington is counted in New Castle County. Legislative, county and other local races aren't here.",
            f"U.S. Census Bureau, {link('https://www.census.gov/programs-surveys/decennial-census/about/rdo/summary-files.html', '2020 Census Redistricting Data')} (P.L. 94-171): county land area and codes, cities, and each block's location and adults, for placing dots within a county.",
            f"U.S. Census Bureau, {link('https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html', '2020 TIGER/Line&reg; Shapefiles')}, tabulation blocks: where people were counted, for keeping dots off empty land. TIGER/Line&reg; is a registered trademark of the Census Bureau; the land grid here isn't a Census Bureau product.",
            f"U.S. Census Bureau, {link('https://www.census.gov/geographies/mapping-files/time-series/geo/carto-boundary-file.html', 'Cartographic Boundary Files')}, 2017 counties, via {link('https://github.com/topojson/us-atlas', 'us-atlas')} v3.0.1 (counties-10m.json).",
            f"Software: {link('https://threejs.org', 'three.js')} r160, {link('https://github.com/d3/d3-geo', 'd3-geo')} 3.1.1, {link('https://github.com/topojson/topojson-client', 'topojson-client')} 3.1.0.",
        ],
    ),
    counties=counties,
    races=races,
)
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(out, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
for r in races:
    print(f"  {r['id']:18} " + ", ".join(f"{c['name']} ({c['party']}{', inc.' if c['incumbent'] else ''}) {c['votes']:,}" for c in r["candidates"])
          + f"; D carried {sum(x[0] > x[1] for x in r['counties'])} of 3")
print(f"OK: {len(races)} races on {COUNTIES} counties, {precincts} election districts, official, data as of {UPDATED}; "
      f"{len(pd)} public-domain rows for 2026 checked")

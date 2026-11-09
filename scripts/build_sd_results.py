"""Build data/sd/results-2026.json: South Dakota's Nov. 3, 2026 statewide races, by county. The results adapter for South Dakota
(docs/PIPELINE.md, Part 6; record in docs/records/south-dakota.md).

Sources, saved by scripts/sd_results_save.py into data/raw/sd/results/:
  statewide-export.xlsx  the site's Statewide Export: one sheet per contest, with one row per county (read for the map)
  results-sw-cty.csv     its media file: statewide totals and each candidate's party
  home.html, resultsSW.html, provisional.html   its pages: reporting status, statewide totals and provisional ballots
Land area and county codes: the 2020 Census redistricting file's county records (data/raw/sd/census/sd2020.pl.zip).

Maps every contest with exactly one Democrat and one Republican. Everyone else in those contests counts as "other". U.S. Senate has no
Democrat, so it isn't mapped, and Governor is South Dakota's first race; the script stops if that changes, and lists what it left out.

Stops unless: the state still calls the results unofficial; all 671 precincts are fully reported; all 66 counties are in every mapped race
and match the Census's names; each candidate's counties add up to the export's totals, the media file and the results page.

Run:  python scripts/build_sd_results.py
"""
import csv
import html
import io
import json
import re
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "sd"
OUT = ROOT / "data" / "sd" / "results-2026.json"
SITE_URL = "https://electionresults.sd.gov/resultsSW.aspx?type=SWR&map=CTY"
SQ_M_PER_SQ_MI = 2_589_988.110336
COUNTIES = 66
PRECINCTS = 671
BALLOTS_EXPECTED = 310_298  # in the pages' header; the script stops if the state's figure changes, so these notes get read again
PROVISIONAL_EXPECTED = 91
CT = timezone(timedelta(hours=-6))

# the export's contest name: (our id, label, menu group). Governor first: it's the race this state opens on (STATE.defaultRace).
RACES = {
    "Governor and Lieutenant Governor": ("governor", "Governor and Lt. Governor", "Statewide"),
    "United States Representative": ("u-s-house", "U.S. House", "Statewide"),
    "Secretary of State": ("secretary-of-state", "Secretary of State", "Statewide"),
    "State Auditor": ("auditor", "State Auditor", "Statewide"),
    "State Treasurer": ("treasurer", "State Treasurer", "Statewide"),
    "Commissioner of School and Public Lands": ("school-public-lands", "School and Public Lands", "Statewide"),
    "Public Utilities Commissioner": ("public-utilities", "Public Utilities", "Statewide"),
}
PARTY = {"DEM": "DEM", "REP": "REP", "LIB": "L"}  # L: as Texas and Iowa, so the page text names it
SUFFIX = {"SR", "JR", "II", "III", "IV"}


def clean(name):
    return re.sub(r"\s+", " ", name).strip()


def match_key(name):
    return re.sub(r"[^a-z ]", "", clean(name).lower())  # the files quote nicknames differently


def last_name(name):
    first = name.split(" and ")[0]  # a ticket goes by the name of the person at its head
    return next(w for w in reversed(first.split()) if w.upper().strip(".") not in SUFFIX)


def page_text(name):
    t = (RAW / "results" / name).read_text(encoding="utf-8", errors="replace")
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"(?s)<(script|style).*?</\1>", "", t))))


# ---------- counties: code, name and land area from the Census file ----------
counties = []
with zipfile.ZipFile(RAW / "census" / "sd2020.pl.zip").open("sdgeo2020.pl") as f:
    for line in io.TextIOWrapper(f, encoding="latin-1"):
        r = line.rstrip("\n").split("|")
        if r[2] == "050" and r[3] == "00" and r[4] == "00":
            counties.append(dict(fips=r[8].split("US")[1], name=r[86].removesuffix(" County"), landSqMi=round(float(r[-13]) / SQ_M_PER_SQ_MI, 3)))
counties.sort(key=lambda c: c["fips"])
assert len(counties) == COUNTIES, len(counties)
index = {c["name"]: i for i, c in enumerate(counties)}

# ---------- is everyone in? ----------
home = page_text("home.html")
assert "Unofficial Results" in home, "the state no longer calls results unofficial: change the pages' wording"
m = re.search(r"Results last updated: (\d+)/(\d+)/(\d{4}) (\d+):(\d\d) (AM|PM) CT", home)
assert m, "no update stamp on the home page"
stamp = datetime.strptime(" ".join(m.groups()), "%m %d %Y %I %M %p")
UPDATED = f"{stamp:%b}. {stamp.day}, {stamp.year}, {stamp.hour % 12 or 12}:{stamp:%M} {stamp:%p} CT"
m = re.search(r"Ballots Cast ([\d,]+) Registered Voters ([\d,]+) Precincts Fully Reported 100 % 100 % Partially 0 Fully (\d+) Total (\d+)", home)
assert m, "the home page doesn't show every precinct fully reported"
BALLOTS, REGISTERED = int(m[1].replace(",", "")), int(m[2].replace(",", ""))
assert (int(m[3]), int(m[4])) == (PRECINCTS, PRECINCTS), m.groups()
assert BALLOTS == BALLOTS_EXPECTED, (BALLOTS, "ballots cast changed")
m = re.search(r"Provisionals Cast (\d+) Totals (\d+)", page_text("provisional.html"))
assert m and int(m[2]) == PROVISIONAL_EXPECTED, (m and m.groups(), "provisional ballots changed: see the record")
saved_at = datetime.fromisoformat(json.loads((RAW / "results" / "SAVED.json").read_text(encoding="utf-8"))["savedAt"]).astimezone(CT)
RETRIEVED = saved_at.date().isoformat()

# ---------- the media file: statewide totals and parties ----------
media = {}
with open(RAW / "results" / "results-sw-cty.csv", encoding="utf-8-sig", newline="") as f:
    for row in csv.DictReader(f):
        assert row["PrecinctsReporting"] == f'="{PRECINCTS}/{PRECINCTS}"', row
        media.setdefault(clean(row["RaceName"]), {})[match_key(row["CandidateName"])] = (row["PartyCode"], int(row["CandidateVotes"]), clean(row["CandidateName"]))

# ---------- the Statewide Export: one sheet per contest ----------
xlsx = zipfile.ZipFile(RAW / "results" / "statewide-export.xlsx")
M = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
shared = ["".join(t.text or "" for t in si.iter(M + "t")) for si in ET.fromstring(xlsx.read("xl/sharedStrings.xml"))]


def sheet(n):
    for row in ET.fromstring(xlsx.read(f"xl/worksheets/sheet{n}.xml")).iter(M + "row"):
        yield [shared[int(c.find(M + "v").text)] if c.get("t") == "s" else c.find(M + "v").text for c in row if c.find(M + "v") is not None]


page_sw = page_text("resultsSW.html")
sheets = sum(1 for n in xlsx.namelist() if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", n))
races, left_out = [], []
for n in range(1, sheets + 1):
    rows = list(sheet(n))
    assert rows[0][0] == "2026 Unofficial General Election Results", rows[0]
    assert rows[2][0].startswith(f"Precincts {PRECINCTS} of {PRECINCTS} Reporting (Precincts Partially Reported: 0/{PRECINCTS})"), rows[2]
    office, column = rows[4][0], rows[4][1]
    assert column == "County", rows[4]
    names = rows[4][2:]
    if office not in media:
        left_out.append((office, None))  # a question, not in the candidates' file
        continue
    assert len(rows) == 5 + COUNTIES + 1 and rows[-1][0] == "TOTALS", (office, len(rows))
    by_key = media[office]
    assert {match_key(x) for x in names} == set(by_key), (office, names, "candidates differ between the export and the media file")
    parties = [by_key[match_key(x)][0] for x in names]
    if parties.count("DEM") != 1 or parties.count("REP") != 1:
        left_out.append((office, [(clean(x), p, by_key[match_key(x)][1]) for x, p in zip(names, parties)]))
        continue
    assert office in RACES, (office, "a contest between a Democrat and a Republican that isn't in RACES")
    rid, label, group = RACES[office]
    table = [[0, 0, 0, 0] for _ in counties]
    seen = set()
    sums = [0] * len(names)
    for row in rows[5:-1]:
        name = row[0].removesuffix(" (Vote Center)")
        assert name in index and name not in seen, (office, row[0], "not a Census county, or listed twice")
        seen.add(name)
        assert len(row) == len(names) + 1, (office, row, "a county row is missing a figure")
        votes = [int(v) for v in row[1:]]
        out = table[index[name]]
        for k, (party, v) in enumerate(zip(parties, votes)):
            out[{"DEM": 0, "REP": 1}.get(party, 2)] += v
            out[3] += v
            sums[k] += v
    assert seen == set(index), (office, "counties differ from the Census's")
    assert all(r[0] + r[1] + r[2] == r[3] for r in table), office
    totals = [int(v) for v in rows[-1][1:]]
    assert sums == totals, (office, "counties don't add up to the export's totals")
    assert totals == [by_key[match_key(x)][1] for x in names], (office, "the export differs from the media file")
    assert re.search(re.escape(office) + r" Follow This Contest", page_sw), (office, "not on the results page")
    at = page_sw.index(office + " Follow This Contest")
    assert f"total votes {sum(totals):,} " in page_sw[at:at + 500], (office, "counties don't add up to the results page's total")
    for x, v in zip(names, totals):
        assert f"{v:,}" in page_sw[at:at + 500], (office, x, "not on the results page")
    cs = []
    for x, party, v in sorted(zip(names, parties, totals), key=lambda t: -t[2]):
        nm = clean(x)
        cs.append(dict(name=nm, last=last_name(nm), party=PARTY[party], incumbent=False, votes=v))
    races.append(dict(id=rid, office=office, label=label, group=group, candidates=cs, counties=table))

assert sorted(r["id"] for r in races) == sorted(v[0] for v in RACES.values()), "statewide races differ from the RACES table"
order = [v[0] for v in RACES.values()]
races.sort(key=lambda r: order.index(r["id"]))
assert races[0]["id"] == "governor"
left = dict(left_out)
senate = left.get("United States Senator")
assert senate and "DEM" not in {p for _, p, _ in senate}, "U.S. Senate now has a Democrat: map it, and change the pages"
for row in races[0]["counties"]:
    assert row[3] >= 10, "a county with under 10 Governor votes"
for r in races:
    assert sum(row[3] for row in r["counties"]) <= BALLOTS, (r["id"], "more votes than ballots")

link = lambda url, text: f'<a href="{url}" target="_blank" rel="noopener">{text}</a>'
word = {"REP": "Republican", "IND": "Independent"}
senate_text = ", ".join(f"{x} ({word[p]})" for x, p, _ in sorted(senate, key=lambda t: -t[2]))
one_party = [o for o, v in left_out if v and len(v) == 1]
questions = [o.split(":")[0] for o, v in left_out if v is None]
out = dict(
    meta=dict(
        election="2026 General Election (Nov. 3, 2026)",
        resultsSource="South Dakota Secretary of State, Election Results (unofficial results; canvass pending)",
        resultsUrl=SITE_URL,
        resultsUpdated=UPDATED, retrieved=RETRIEVED,
        reporting=dict(counties=COUNTIES, countiesReporting=COUNTIES, precincts=PRECINCTS, precinctsReporting=PRECINCTS, ballotsCast=BALLOTS, registered=REGISTERED, provisionalCast=PROVISIONAL_EXPECTED),
        landSource="U.S. Census Bureau, 2020 Census Redistricting Data (P.L. 94-171), county land area (AREALAND)",
        countyRow="counties[i] = [Democratic votes, Republican votes, all other votes, total votes] for meta.counties[i]",
        sources=[
            f"South Dakota Secretary of State, {link(SITE_URL, 'Election Results')}, Nov. 3, 2026 general election: unofficial results by county from the site's Statewide Export, checked against its media file and results page, as of {UPDATED}, retrieved {RETRIEVED}. The state offers its information for \"personal or informational use\" and makes no warranty that it is free of others' claims.",
            f"The site lists {PROVISIONAL_EXPECTED} provisional ballots cast statewide. They are counted, if accepted, just before the county canvass, so they may not be in these totals.",
            f"Left out: U.S. Senate, because no Democrat was on the ballot: {senate_text}. It can't be shown as a Democrat against a Republican. {' and '.join(one_party)} had one candidate. Also left out, as questions rather than contests between candidates: {', '.join(questions)}. Races not on the ballot statewide aren't here either.",
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
print("left out:", [o.split(":")[0] for o, _ in left_out])
print(f"OK: {len(races)} races; {COUNTIES} counties, {PRECINCTS} precincts, all reporting; unofficial; {BALLOTS:,} ballots; {REGISTERED:,} registered; as of {UPDATED}, retrieved {RETRIEVED}.")
for r in races:
    d = next(c for c in r["candidates"] if c["party"] == "DEM"); p = next(c for c in r["candidates"] if c["party"] == "REP")
    print(f"  {r['id']:20} {d['name']} {d['votes']:,} vs {p['name']} {p['votes']:,}; total {sum(row[3] for row in r['counties']):,}; D carried {sum(row[0] > row[1] for row in r['counties'])} counties")
print("fewest Governor votes:", min((row[3], counties[i]["name"]) for i, row in enumerate(races[0]["counties"])))

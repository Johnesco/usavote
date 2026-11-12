"""Build data/oh/results-2026.json: Ohio's Nov. 3, 2026 statewide races, by county. The results adapter for Ohio
(docs/PIPELINE.md, Part 6; record in docs/records/ohio.md).

Source, a NIST 1500-100 XML file from the Ohio Secretary of State, saved by plain curl into data/raw/oh/results/:
  https://liveresults.ohiosos.gov/Api/v1/download?filename=VSSC1622XmlFileBlob
Land area and county codes: the 2020 Census redistricting file's county records (data/raw/oh/census/oh2020.pl.zip).

These results are UNOFFICIAL AND PARTIAL: the file's own Status is "UnofficialPartial", and its counties list UOCAVA absentee and
provisional ballots still outstanding. The outstanding counts are carried into the file's meta for the page to quote.

Maps only statewide candidate races with exactly one Democrat and one Republican; everyone else, Libertarians and write-ins
included, goes in "other". State Issue 3 (yes or no) and the races below statewide aren't mapped.

Stops unless: the file's status is the one the page's wording was written for, all precincts are reporting, all 88 counties are
there and match the Census file one to one, every candidate has one count for the state and one for each county, each candidate's
counties add up to the file's state figure, and no county's votes in a race exceed its ballots cast. The file gives no separate
county total for a race, so that last check is the only outside one a county's candidates can be held to. One county fails it
(BALLOTS_TOO_LOW, below): that's named here and in docs/records/ohio.md, not fixed, and any change to it stops the build.

Run:  python scripts/build_oh_results.py
"""
import hashlib
import io
import json
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from chamber import chamber_race, summary as chamber_summary

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "oh"
FEED = RAW / "results" / "VSSC1622-2026-11-08.xml"
OUT = ROOT / "data" / "oh" / "results-2026.json"
SITE_URL = "https://liveresults.ohiosos.gov/"
FEED_URL = "https://liveresults.ohiosos.gov/Api/v1/download?filename=VSSC1622XmlFileBlob"
RETRIEVED = "2026-11-08"
STATUS = "UnofficialPartial"  # if this changes, state.js's wording has to be read again before the page can say anything new
SQ_M_PER_SQ_MI = 2_589_988.110336
COUNTIES = 88
MONTHS = "Jan. Feb. March April May June July Aug. Sept. Oct. Nov. Dec.".split()
XSI_TYPE = "{http://www.w3.org/2001/XMLSchema-instance}type"
# Wyandot's ballots cast in the file (8,739) is below its votes in all eight mapped races (8,860 to 9,975), and every other county's
# is above them. The file can't say which is wrong. The votes are used as published and ballots cast isn't shown.
BALLOTS_TOO_LOW = {"Wyandot": 8739}
# the file's party code -> ours (the code the pages already know, or words a reader can follow)
PARTY = {"DEM": "DEM", "REP": "REP", "LIB": "L", "Other-part": "Other party", "Write-in": "W"}


def norm(s):
    return re.sub(r"[^A-Z]", "", s.upper())


def day(iso):
    y, m, d = iso.split("-")
    return f"{MONTHS[int(m) - 1]} {int(d)}, {y}"


# the file's name for a race and its term's first day (two Supreme Court seats share a name): (our id, label, menu group), in menu order.
# A label's date comes from the file.
RACES = {
    ("U.S. Senator", None): ("u-s-senate", lambda term: f"U.S. Senate (unexpired term to {day(term['EndDate'])})", "Federal"),
    ("Governor and Lieutenant Governor", None): ("governor", lambda term: "Governor and Lieutenant Governor", "Statewide"),
    ("Attorney General", None): ("attorney-general", lambda term: "Attorney General", "Statewide"),
    ("Auditor of State", None): ("auditor", lambda term: "Auditor of State", "Statewide"),
    ("Secretary of State", None): ("secretary-of-state", lambda term: "Secretary of State", "Statewide"),
    ("Treasurer of State", None): ("treasurer", lambda term: "Treasurer of State", "Statewide"),
    ("Justice of the Supreme Court", "2027-01-01"): ("supreme-court-jan-1", lambda term: f"Supreme Court (term from {day(term['StartDate'])})", "Supreme Court"),
    ("Justice of the Supreme Court", "2027-01-02"): ("supreme-court-jan-2", lambda term: f"Supreme Court (term from {day(term['StartDate'])})", "Supreme Court"),
}

raw = FEED.read_bytes()
print(f"{FEED.name}: SHA-256 {hashlib.sha256(raw).hexdigest()}")
root = ET.fromstring(raw)
assert root.get("Status") == STATUS, ("the file's status changed: read state.js's wording again", root.get("Status"))
generated = root.get("GeneratedDate")
m = re.fullmatch(r"(\d{4}-\d\d-\d\d)T(\d\d:\d\d):\d\dZ", generated)
assert m, generated
UPDATED = f"{day(m[1])}, {m[2]} UTC"  # the file's own stamp, as it writes it

election = root.find("{*}Election")
gp = list(root.find("{*}GpUnitCollection"))
state_id = next(g.get("ObjectId") for g in gp if g.get("Type") == "State")
parties = {p.get("ObjectId"): p.get("Abbreviation") for p in root.find("{*}PartyCollection")}
persons = {p.get("ObjectId"): p for p in root.find("{*}PersonCollection")}
offices = {o.get("ObjectId"): o for o in root.find("{*}OfficeCollection")}
candidates = {c.get("ObjectId"): c for c in election.find("{*}CandidateCollection")}

# ---------- counties: code, name and land area from the Census file ----------
counties, by_name = [], {}
with zipfile.ZipFile(RAW / "census" / "oh2020.pl.zip").open("ohgeo2020.pl") as f:
    for line in io.TextIOWrapper(f, encoding="latin-1"):
        r = line.rstrip("\n").split("|")
        if r[2] == "050" and r[3] == "00" and r[4] == "00":
            name = r[86].removesuffix(" County")
            c = dict(fips=r[8].split("US")[1], name=name, landSqMi=round(float(r[-13]) / SQ_M_PER_SQ_MI, 3))
            counties.append(c); by_name[norm(name)] = c
counties.sort(key=lambda c: c["fips"])
assert len(counties) == COUNTIES, len(counties)
index = {c["fips"]: i for i, c in enumerate(counties)}

# ---------- the file's counties, and how far each has reported ----------
row_of, ballots = {}, [0] * COUNTIES  # the file's id for a county -> its row; each row's ballots cast
uocava = provisional = precincts = 0
units = [g for g in gp if g.get("Type") == "County" and g.get("IsElectoralDistrict") == "false"]
assert len(units) == COUNTIES, len(units)
for g in units:
    c = by_name[norm(g.get("Name"))]  # a KeyError here is a county the Census file doesn't know
    i = index[c["fips"]]
    assert g.get("ObjectId") not in row_of and i not in row_of.values(), ("county listed twice", g.get("Name"))
    row_of[g.get("ObjectId")] = i
    assert g.get("SubUnitsReported") == g.get("TotalSubUnits"), (g.get("Name"), "precincts not all reporting")
    precincts += int(g.get("TotalSubUnits"))
    summary = {s.get("Type"): s for s in g.findall("{*}SummaryCounts")}
    assert summary["Total"].get("BallotsCast") == g.get("VotersParticipated"), g.get("Name")
    ballots[i] = int(g.get("VotersParticipated"))
    uocava += int(summary["Absentee"].get("BallotsOutstanding", 0))  # the file's "Absentee"; the results site calls this column Outstanding UOCAVA Absentees
    provisional += int(summary["Provisional"].get("BallotsOutstanding", 0))
assert len(row_of) == COUNTIES


def counts(selection, what):
    """A selection's votes: (the file's state figure, its count in each county's row). Stops on a county missing or doubled."""
    state, by_row = None, [None] * COUNTIES
    for v in selection.findall(".//{*}VoteCounts"):
        unit, n = v.findtext("{*}GpUnitId"), int(v.get("Count"))
        if unit == state_id:
            assert state is None, what
            state = n
        else:
            assert by_row[row_of[unit]] is None, what
            by_row[row_of[unit]] = n
    assert state is not None and None not in by_row, (what, "a county or the state is missing")
    return state, by_row


races, left_out, over = [], {}, set()
for contest in election.find("{*}ContestCollection"):
    name = contest.get("Name").strip()
    if contest.findtext("{*}JurisdictionalScopeId") != state_id:
        kind = re.sub(r"\s*-\s*District \d+$", "", name)
        left_out[kind] = left_out.get(kind, 0) + 1
        continue
    if contest.get(XSI_TYPE) != "CandidateContest":
        left_out[name] = "yes or no, no candidates"
        continue
    term = offices[contest.findtext("{*}OfficeId")].find("{*}Term").attrib
    key = (name, term.get("StartDate"))
    assert key in RACES, ("a statewide race isn't in the RACES table", key)
    rid, label, group = RACES[key]
    assert (term.get("Type") == "UnexpiredTerm") == (rid == "u-s-senate"), (rid, term)

    table = [[0, 0, 0, 0] for _ in counties]
    cands = []
    for s in contest.findall("{*}BallotSelection"):
        people = [candidates[i.text] for i in s.findall("{*}CandidateId")]
        code = parties[people[0].findtext("{*}PartyId")]
        assert code in PARTY, (name, "a party with no code here", code)
        party = PARTY[code]
        assert (s.get("IsWriteIn") == "true") == (party == "W"), (name, code)
        assert len(people) == 1 or (rid == "governor" and len(people) == 2 and people[0].get("IsTopTicket") == "true"), (name, "ticket shape")
        names = [" ".join(p.findtext("{*}BallotName/{*}LanguageString").split()) for p in people]
        state_votes, by_row = counts(s, (name, names))
        assert sum(by_row) == state_votes, (name, names, "counties don't add up to the state figure", sum(by_row), state_votes)
        for i, v in enumerate(by_row):
            k = {"DEM": 0, "REP": 1}.get(party, 2)
            table[i][k] += v; table[i][3] += v
        last = persons[people[0].findtext("{*}PersonId")].findtext("{*}LastName").strip()
        cands.append(dict(name=" and ".join(names), last=last, party=party, incumbent=False, votes=state_votes))
    found = [c["party"] for c in cands]
    assert found.count("DEM") == 1 and found.count("REP") == 1, (name, found)
    cands.sort(key=lambda c: -c["votes"])
    for row, cast, c in zip(table, ballots, counties):
        assert row[0] + row[1] + row[2] == row[3], (name, c["name"])
        assert row[3] <= cast or BALLOTS_TOO_LOW.get(c["name"]) == cast, (name, c["name"], "more votes than ballots cast", row[3], cast)
        if row[3] > cast: over.add(c["name"])
    assert sum(row[3] for row in table) == sum(c["votes"] for c in cands), name
    races.append(dict(id=rid, office=name, label=label(term), group=group, candidates=cands, counties=table))

assert len(races) == len(RACES), "statewide races differ from the RACES table"
assert over == set(BALLOTS_TOO_LOW), ("the counties with more votes than ballots cast changed", over)
print("WARNING, more votes than ballots cast in the file, votes used as published:", BALLOTS_TOO_LOW)
order = [v[0] for v in RACES.values()]
races.sort(key=lambda r: order.index(r["id"]))
print("left out:", left_out)
assert all(sum(row[3] for row in r["counties"]) for r in races)

# ---------- U.S. House: every district, added up by county, with each district's own result (scripts/chamber.py) ----------
HOUSE_PARTY = {**PARTY, "Indep": "IND", "Nonprtycan": "NP"}  # codes the statewide races don't have: independent, nonparty candidate
house_votes, house_expect = {}, {}
for contest in election.find("{*}ContestCollection"):
    m = re.fullmatch(r"Representative to Congress - District (\d+)", contest.get("Name").strip())
    if not m: continue
    assert contest.get(XSI_TYPE) == "CandidateContest" and contest.get("VotesAllowed") == "1", contest.get("Name")
    num, scope = int(m.group(1)), contest.findtext("{*}JurisdictionalScopeId")
    house_votes[num], house_expect[num] = {}, {}
    for s in contest.findall("{*}BallotSelection"):
        people = [candidates[i.text] for i in s.findall("{*}CandidateId")]
        code = parties[people[0].findtext("{*}PartyId")]
        assert len(people) == 1 and code in HOUSE_PARTY, (contest.get("Name"), "ticket shape or a party with no code here", code)
        k = (" ".join(people[0].findtext("{*}BallotName/{*}LanguageString").split()), HOUSE_PARTY[code])
        assert k not in house_expect[num], (contest.get("Name"), k)
        for v in s.findall(".//{*}VoteCounts"):
            unit, n = v.findtext("{*}GpUnitId"), int(v.get("Count"))
            if unit == scope:
                assert k not in house_expect[num], (contest.get("Name"), k); house_expect[num][k] = n
            else:
                here = house_votes[num].setdefault(row_of[unit], {})  # a KeyError is a unit that's neither the district nor a county
                assert k not in here, (contest.get("Name"), k, unit); here[k] = n
        assert k in house_expect[num], (contest.get("Name"), k, "no district total")
house = chamber_race("u-s-house", "U.S. House", "Federal", "Representative to Congress", 15, house_votes, COUNTIES, expect=house_expect)
races.append(house)
print(chamber_summary(house))

link = lambda url, text: f'<a href="{url}" target="_blank" rel="noopener">{text}</a>'
TIGER = ("TIGER/Line&reg; is a registered trademark of the U.S. Census Bureau. This site's land grid is reworked from TIGER/Line&reg; "
         "Shapefiles and isn't a Census Bureau product; the name is used here only to say what the source was.")
out = dict(
    meta=dict(
        election="2026 November General Election (Nov. 3, 2026)",
        resultsSource=f"Ohio Secretary of State, Ohio Decides results file (unofficial and partial: file status {STATUS}; official canvass pending)",
        resultsUrl=SITE_URL, resultsFile=FEED_URL,
        resultsUpdated=UPDATED, retrieved=RETRIEVED,
        status=STATUS,
        precincts=precincts,
        ballotsOutstanding=uocava + provisional,
        uocavaOutstanding=uocava,
        provisionalOutstanding=provisional,
        landSource="U.S. Census Bureau, 2020 Census Redistricting Data (P.L. 94-171), county land area (AREALAND)",
        countyRow="counties[i] = [Democratic votes, Republican votes, all other votes, total votes] for meta.counties[i]",
        sources=[
            f"Ohio Secretary of State, {link(SITE_URL, 'Ohio Decides')}, Nov. 3, 2026 general election: {link(FEED_URL, 'results file')}, generated {UPDATED}, retrieved {RETRIEVED}. Unofficial and partial; the file's status is &ldquo;{STATUS}&rdquo;. &copy; 2026 Ohio Secretary of State. All Rights Reserved, per the results site's footer.",
            f"U.S. Census Bureau, {link('https://www.census.gov/programs-surveys/decennial-census/about/rdo/summary-files.html', '2020 Census Redistricting Data')} (P.L. 94-171): county land area and codes, cities, and each block's location and adults, for placing dots within a county; {link('https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html', '2020 TIGER/Line&reg; Shapefiles')}, blocks, for where people were counted. <b>{TIGER}</b>",
            f"U.S. Census Bureau, {link('https://www.census.gov/geographies/mapping-files/time-series/geo/carto-boundary-file.html', 'Cartographic Boundary Files')}, 2017 counties, via {link('https://github.com/topojson/us-atlas', 'us-atlas')} v3.0.1 (counties-10m.json).",
            f"Software: {link('https://threejs.org', 'three.js')} r160, {link('https://github.com/d3/d3-geo', 'd3-geo')} 3.1.1, {link('https://github.com/topojson/topojson-client', 'topojson-client')} 3.1.0.",
        ],
    ),
    counties=counties,
    races=races,
)
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
print(f"OK: {len(races)} races, {COUNTIES} counties, status {STATUS}, {precincts:,} precincts all reporting; counties match the state figures.")
print(f"outstanding {uocava + provisional:,} ({uocava:,} UOCAVA absentee, {provisional:,} provisional); generated {UPDATED}")
for r in races:
    d = next(c for c in r["candidates"] if c["party"] == "DEM"); p = next(c for c in r["candidates"] if c["party"] == "REP")
    print(f"  {r['id']:22} {r['label']:45} {d['name']} {d['votes']:,} vs {p['name']} {p['votes']:,}; other {sum(c['votes'] for c in r['candidates']) - d['votes'] - p['votes']:,}; D carried {sum(row[0] > row[1] for row in r['counties'])} counties")

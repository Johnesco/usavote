"""Build data/id/results-2026.json: Idaho's Nov. 3, 2026 statewide races, by county. The results adapter for Idaho
(docs/PIPELINE.md, Part 6; record in docs/records/idaho.md).

Sources, saved by scripts/id_results_save.py into data/raw/id/results/:
  export-nov2026.json    the site's Media Export: every contest, statewide and by county (read for the map)
  report-results.xlsx    its Download Reports spreadsheet: county and precinct results, with ballots cast, over votes and under votes
  report-summary.txt     its summary PDF as text: statewide totals
  data.json, localities.json, election.json   the same results and their reporting status, as the site's pages read them
Land area and county codes: the 2020 Census redistricting file's county records (data/raw/id/census/id2020.pl.zip).

Maps every candidate contest on the ballot in all 44 counties with exactly one Democrat and one Republican. Everyone else in those
contests counts as "other". U.S. Senate has no Democrat, so it isn't mapped, and Governor is Idaho's first race; the script stops if
that changes, and lists what it left out.

Stops unless: the state still calls the results unofficial; every county and precinct is reporting; all 44 counties are in every
mapped race and match the Census's codes and names; in each county, candidates plus over and under votes equal ballots cast, apart
from the four rows in BALLOT_GAPS; each candidate's counties add up to the statewide figures in all the files; each county matches
the spreadsheet; and the spreadsheet's precincts add up to its counties.

Run:  python scripts/build_id_results.py
"""
import io
import json
import re
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

from chamber import chamber_race, summary as chamber_summary

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "id"
OUT = ROOT / "data" / "id" / "results-2026.json"
SITE_URL = "https://results.voteidaho.gov/results/public/id/elections/nov2026"
SQ_M_PER_SQ_MI = 2_589_988.110336
COUNTIES = 44
PRECINCTS = 986
MT = timezone(timedelta(hours=-7))  # Mountain Standard Time; the summary PDF's stamp reads the same as the file's time here

# the file's id for a contest: (our id, label, menu group). Governor first: it's the race this state opens on (STATE.defaultRace).
RACES = {
    "gov": ("governor", "Governor", "Statewide"),
    "ltgov": ("lieutenant-governor", "Lieutenant Governor", "Statewide"),
    "sos": ("secretary-of-state", "Secretary of State", "Statewide"),
    "sco": ("controller", "State Controller", "Statewide"),
    "sto": ("treasurer", "State Treasurer", "Statewide"),
    "ag": ("attorney-general", "Attorney General", "Statewide"),
    "spi": ("superintendent", "Superintendent of Public Instruction", "Statewide"),
}
PARTY = {"Democratic": "DEM", "Republican": "REP", "Independent": "IND", "Libertarian": "L", "Constitution": "CON"}  # L: as Texas and Iowa, so the page text names it
SUFFIX = {"SR", "JR", "II", "III", "IV"}
# Ballots cast minus over votes, under votes and every candidate's votes, where that isn't 0 in a mapped race. The state's own summary
# has the same 30-vote gap (docs/records/idaho.md). None of these changes a candidate's votes; three of these counties show no
# write-ins at all. The script stops if any other row has a gap, or these change.
BALLOT_GAPS = {("Caribou", "gov"): 3, ("Elmore", "gov"): 16, ("Gooding", "gov"): 12, ("Shoshone", "gov"): -1}
# Candidates' precinct lists in the export add up short of their county figure here, in the Republican's row only. The spreadsheet's
# precincts do add up, and the map doesn't read precincts. The script stops if another county shows this.
EXPORT_PRECINCT_GAP_COUNTIES = {"Bingham", "Blaine"}


def load(name):
    return json.loads((RAW / "results" / name).read_text(encoding="utf-8"))


def last_name(name):
    return next(w for w in reversed(name.split()) if w.upper().strip(".") not in SUFFIX)


# ---------- counties: code, name and land area from the Census file ----------
counties = []
with zipfile.ZipFile(RAW / "census" / "id2020.pl.zip").open("idgeo2020.pl") as f:
    for line in io.TextIOWrapper(f, encoding="latin-1"):
        r = line.rstrip("\n").split("|")
        if r[2] == "050" and r[3] == "00" and r[4] == "00":
            counties.append(dict(fips=r[8].split("US")[1], name=r[86].removesuffix(" County"), landSqMi=round(float(r[-13]) / SQ_M_PER_SQ_MI, 3)))
counties.sort(key=lambda c: c["fips"])
assert len(counties) == COUNTIES, len(counties)
index = {c["fips"]: i for i, c in enumerate(counties)}
by_name = {c["name"]: c for c in counties}

# ---------- the Media Export, and is everyone in? ----------
export = load("export-nov2026.json")
election, data, localities = load("election.json"), load("data.json"), load("localities.json")
assert export["electionDate"] == "2026-11-03"
assert election["isOfficialResults"] is False and not any(l["isOfficialResults"] for l in localities), "the state now calls results official: change the pages' wording"
local = {}
for l in export["localResults"]:
    name = l["name"].removesuffix(" County")
    assert by_name[name]["fips"] == "16" + l["id"], (l["name"], l["id"], "the county's code differs from the Census's")
    local[name] = {b["id"]: b for b in l["ballotItems"]}
assert set(local) == set(by_name), "the results site's counties differ from the Census's"
assert all(c["percentReporting"] == 1 and c["precinctsReporting"] == 1 for c in load("jurisdiction.json")["childLocalities"]), "a county isn't fully reported"
status = Counter()
for l in localities:
    for g in l["precinctReportingStatus"]:
        status[g["groupName"][0]["text"]] += g["value"]
assert status == {"Fully Reported": PRECINCTS, "Partially Reported": 0, "Not Reported": 0}, status
as_of = datetime.fromisoformat(election["asOf"][:19]).replace(tzinfo=timezone.utc).astimezone(MT)
UPDATED = f"{as_of:%b}. {as_of.day}, {as_of.year}, {as_of.hour % 12 or 12}:{as_of:%M} {as_of:%p} MT"
saved_at = datetime.fromisoformat(load("SAVED.json")["savedAt"]).astimezone(MT)
RETRIEVED = saved_at.date().isoformat()
summary_pdf = (RAW / "results" / "report-summary.txt").read_text(encoding="utf-8", errors="replace")
assert as_of.strftime("%m/%d/%Y %H:%M") in summary_pdf, "the summary PDF is from a different publish than the export"

# ---------- the spreadsheet: one row per county (or precinct), contest and line ----------
xlsx = zipfile.ZipFile(RAW / "results" / "report-results.xlsx")
M = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
shared = ["".join(t.text or "" for t in si.iter(M + "t")) for si in ET.fromstring(xlsx.read("xl/sharedStrings.xml"))]


def sheet(name, want):
    rows = ET.fromstring(xlsx.read(name)).iter(M + "row")
    head = {}
    for n, row in enumerate(rows):
        cells = {}
        for c in row:
            v = c.find(M + "v")
            cells[re.match(r"[A-Z]+", c.get("r")).group()] = None if v is None else shared[int(v.text)] if c.get("t") == "s" else v.text
        if n == 0:
            head = {v: k for k, v in cells.items() if v}
            continue
        yield [cells.get(head[w]) for w in want]


county_sheet = defaultdict(dict)
for county, contest, line, total in sheet("xl/worksheets/sheet1.xml", ["County", "Contest ID", "Ballot Name", "Total"]):
    county_sheet[(county.removesuffix(" County"), contest)][line] = int(total or 0)
precinct_sheet = defaultdict(Counter)
for county, contest, line, total in sheet("xl/worksheets/sheet2.xml", ["County", "Contest ID", "Ballot Name", "Total"]):
    precinct_sheet[(county.removesuffix(" County"), contest)][line] += int(total or 0)
NOT_CANDIDATES = ("Ballots Cast", "Over Votes", "Under Votes")

# ---------- each contest on the ballot statewide ----------
state_items = {b["id"]: b for b in export["results"]["ballotItems"]}
site_items = {b["name"][0]["text"]: b for b in data["ballotItems"]}
everywhere = [i for i in state_items if all(i in items for items in local.values())]
races, left_out, gaps, precinct_gaps = [], [], {}, set()
for item in everywhere:
    b = state_items[item]
    parties = [o["politicalParty"] for o in b["ballotOptions"]]
    if b["contestType"] != "Candidate" or parties.count("Democratic") != 1 or parties.count("Republican") != 1:
        left_out.append(item); continue
    assert item in RACES, (item, b["name"], "a statewide contest between a Democrat and a Republican that isn't in RACES")
    assert b["voteFor"] == 1, item
    rid, label, group = RACES[item]
    table = [[0, 0, 0, 0] for _ in counties]
    sums = Counter()
    precincts = 0
    party_of = {o["name"]: o["politicalParty"] for o in b["ballotOptions"]}
    for name, items in local.items():
        here = items[item]
        assert here["precinctsReporting"] == here["precinctsParticipating"] > 0, (item, name, "precincts not all reporting")
        precincts += here["precinctsReporting"]
        votes = {o["name"]: o["voteCount"] for o in here["ballotOptions"]}
        assert set(votes) == {o["name"] for o in b["ballotOptions"]}, (item, name, "candidates differ")
        row = table[index[by_name[name]["fips"]]]
        for o in here["ballotOptions"]:
            row[{"Democratic": 0, "Republican": 1}.get(party_of[o["name"]], 2)] += o["voteCount"]  # counties spell parties their own ways, so the statewide row says
            row[3] += o["voteCount"]
            sums[o["name"]] += o["voteCount"]
            if sum(p["voteCount"] for p in o["precinctResults"]) != o["voteCount"]:
                precinct_gaps.add(name)
        x = county_sheet[(name, item)]
        assert {k: v for k, v in x.items() if k not in NOT_CANDIDATES} == votes, (item, name, "the spreadsheet's county row differs from the export")
        assert {k: v for k, v in precinct_sheet[(name, item)].items() if k not in NOT_CANDIDATES} == votes, (item, name, "the spreadsheet's precincts don't add up to its county")
        gap = x["Ballots Cast"] - x["Over Votes"] - x["Under Votes"] - sum(votes.values())
        if gap: gaps[(name, item)] = gap
        assert row[3] == sum(votes.values()) <= x["Ballots Cast"], (item, name, "more votes than ballots")
    assert precincts == PRECINCTS, (item, precincts)
    # counties against the statewide figures: the export's own, the site's pages, and the summary PDF
    assert sums == {o["name"]: o["voteCount"] for o in b["ballotOptions"]}, (item, "counties don't add up to the export's statewide row")
    for k, party in enumerate(("Democratic", "Republican")):
        assert sum(row[k] for row in table) == next(o["voteCount"] for o in b["ballotOptions"] if o["politicalParty"] == party), (item, party, "the party's counties don't add up")
    assert all(row[0] + row[1] + row[2] == row[3] for row in table), item
    site = site_items[b["name"]]
    assert site["reportingStatus"]["reportingUnits"] == site["reportingStatus"]["totalUnits"] == COUNTIES, (item, "the site shows counties not reporting")
    assert site["voteTotal"] == sum(sums.values()), (item, "counties don't add up to the site's total")
    assert {o["name"][0]["text"]: o["voteCount"] for o in site["summaryResults"]["ballotOptions"]} == sums, (item, "counties don't add up to the site's candidates")
    pdf_lines = summary_pdf.split("\n")
    at = next(i for i, s in enumerate(pdf_lines) if re.match(re.escape(b["name"]) + r"(\s|$)", s))  # the columns of figures start a few lines above the name
    block = "\n".join(pdf_lines[at - 6: at + 16])
    for v in [*sums.values(), sum(sums.values())]:
        assert re.search(rf"(?<![\d,]){v:,}(?![\d,])", block), (item, v, "not in the summary PDF")

    write_in = {o["name"]: o["politicalParty"] is None or o["name"].endswith("(Write-in)") for o in b["ballotOptions"]}
    flags = {o["name"][0]["text"]: o["isWriteIn"] for o in site["summaryResults"]["ballotOptions"]}
    assert write_in == flags, (item, "write-in flags differ")
    cs = []
    for o in sorted(b["ballotOptions"], key=lambda o: -o["voteCount"]):
        nm = o["name"].strip()
        code = "W" if write_in[o["name"]] else PARTY[o["politicalParty"]]
        cs.append(dict(name=nm, last=nm if code == "W" else last_name(nm), party=code, incumbent=False, votes=o["voteCount"]))
    races.append(dict(id=rid, office=b["name"], label=label, group=group, candidates=cs, counties=table))
assert sorted(r["id"] for r in races) == sorted(v[0] for v in RACES.values()), "statewide races differ from the RACES table"
order = [v[0] for v in RACES.values()]
races.sort(key=lambda r: order.index(r["id"]))
assert races[0]["id"] == "governor"
assert "ussen" in left_out and "Democratic" not in {o["politicalParty"] for o in state_items["ussen"]["ballotOptions"]}, "U.S. Senate now has a Democrat: map it, and change the pages"
assert gaps == BALLOT_GAPS, ("ballots cast don't add up, other than the named rows", gaps)
assert precinct_gaps == EXPORT_PRECINCT_GAP_COUNTIES, ("the export's precinct lists don't add up in", precinct_gaps)
for row in races[0]["counties"]:
    assert row[3] >= 10, "a county with under 10 Governor votes"
BALLOTS = sum(county_sheet[(n, "gov")]["Ballots Cast"] for n in by_name)
REGISTERED = sum(v["total"] for v in load("vr.json")["data"])

# ---------- U.S. House: every district, added up by county, with each district's own result (scripts/chamber.py) ----------
house_votes, house_expect = {}, {}
for item, num in (("usrep1", 1), ("usrep2", 2)):
    b = state_items[item]
    assert b["contestType"] == "Candidate" and b["voteFor"] == 1, item
    key = {o["name"]: (o["name"].strip(), "W" if o["politicalParty"] is None or o["name"].endswith("(Write-in)") else PARTY[o["politicalParty"]]) for o in b["ballotOptions"]}
    house_expect[num] = {key[o["name"]]: o["voteCount"] for o in b["ballotOptions"]}
    house_votes[num] = {}
    for name, items in local.items():
        if item not in items: continue
        here = items[item]
        assert here["precinctsReporting"] == here["precinctsParticipating"] > 0, (item, name, "precincts not all reporting")
        house_votes[num][index[by_name[name]["fips"]]] = {key[o["name"]]: o["voteCount"] for o in here["ballotOptions"]}
house = chamber_race("u-s-house", "U.S. House", "Federal", "United States Representative", 2, house_votes, COUNTIES, expect=house_expect)
races.append(house)
print(chamber_summary(house))

link = lambda url, text: f'<a href="{url}" target="_blank" rel="noopener">{text}</a>'
senate = sorted(state_items["ussen"]["ballotOptions"], key=lambda o: -o["voteCount"])
party_word = {"Republican": "Republican", "Independent": "Independent", "Libertarian": "Libertarian"}
senate_text = ", ".join(f"{o['name']} ({party_word[o['politicalParty']]})" for o in senate)
others_left = [state_items[i]["name"].removeprefix("Idaho Constitutional Amendment: ") for i in left_out if i != "ussen"]
gap_text = " and ".join(sorted(n for (n, _), g in gaps.items() if g > 0)).replace(" and ", ", ", len([g for g in gaps.values() if g > 0]) - 2)
out = dict(
    meta=dict(
        election="2026 General Election (Nov. 3, 2026)",
        resultsSource="Idaho Secretary of State, Election Results (unofficial results; state canvass pending)",
        resultsUrl=SITE_URL,
        resultsUpdated=UPDATED, retrieved=RETRIEVED,
        reporting=dict(counties=COUNTIES, countiesReporting=COUNTIES, precincts=PRECINCTS, precinctsReporting=status["Fully Reported"], ballotsCastGovernor=BALLOTS, registered=REGISTERED),
        landSource="U.S. Census Bureau, 2020 Census Redistricting Data (P.L. 94-171), county land area (AREALAND)",
        countyRow="counties[i] = [Democratic votes, Republican votes, all other votes, total votes] for meta.counties[i]",
        sources=[
            f"Idaho Secretary of State, {link(SITE_URL, 'Election Results')}, Nov. 3, 2026 general election: unofficial results by county from the site's Media Export, checked against its Download Reports, as of {UPDATED}, retrieved {RETRIEVED}.",
            f"Left out: U.S. Senate, because no Democrat was on the ballot: {senate_text}. It can't be shown as a Democrat against a Republican. Also left out, as questions rather than contests between candidates: {', '.join(others_left)}. Races not on the ballot statewide aren't here either.",
            f"In the Governor race, ballots cast in the state's own report exceed the votes, over votes and under votes by {sum(g for g in gaps.values() if g > 0)} in {gap_text} Counties, which show no write-ins. The county figures here are as the state reports them.",
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
print("left out, on the ballot in every county but not one Democrat against one Republican:", [state_items[i]["name"] for i in left_out])
print(f"not in every county, left out: {len(state_items) - len(everywhere)} contests")
print("rows where ballots cast don't add up, as named in BALLOT_GAPS:", gaps)
print("counties whose precinct lists in the export add up short:", sorted(precinct_gaps))
print(f"OK: {len(races)} races; {COUNTIES} counties, {PRECINCTS} precincts, all reporting; unofficial; {BALLOTS:,} ballots in the Governor race; {REGISTERED:,} registered; as of {UPDATED}, retrieved {RETRIEVED}.")
for r in races:
    d = next(c for c in r["candidates"] if c["party"] == "DEM"); p = next(c for c in r["candidates"] if c["party"] == "REP")
    print(f"  {r['id']:20} {d['name']} {d['votes']:,} vs {p['name']} {p['votes']:,}; total {sum(row[3] for row in r['counties']):,}; D carried {sum(row[0] > row[1] for row in r['counties'])} counties")

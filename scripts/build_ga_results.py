"""Build data/ga/results-2026.json: Georgia's Nov. 3, 2026 statewide races, by county. The results adapter for Georgia
(docs/PIPELINE.md, Part 6; record in docs/records/georgia.md). Georgia is county-only: scripts/ga_precinct_match.py shows why.

Sources, under data/raw/ga/ (not committed):
  results/export-11032026GeneralAndSpecialElection.json: Georgia Secretary of State, the results site's Media Export
  results/saved-at.txt: when it was saved
  census/ga2020.pl.zip: county codes, names and land area

Maps every contest on the ballot in all 159 counties with exactly one Democrat and one Republican. Each has only those two
candidates in the file, so "other" is 0 throughout; the build would count anyone else as other. The yes-or-no constitutional
amendments and statewide referendums have no candidates to map. The script lists what it left out.

Stops unless: all 159 counties match the Census names and have every mapped race; a county's candidates are the state's, by option
id; every precinct reports; in each county, vote types add up to each candidate's total; each candidate's counties add up to the
statewide figure, and the statewide vote types to the same figure; precinct rows add up to the county; and no mapped race lacks a
majority, which would mean a runoff. Two named exceptions, both the same in every mapped race, stop the build if they change:
  Miller and Glascock counties: all vote types are null, though each candidate's total is there. The statewide vote types include
    those votes, which the script checks.
  Fulton County: the Democrat's precinct rows come to 3 fewer than the county's total. Only the county's total is used.

A county's own party field isn't read, since some are blank or spelled differently (Evans, Stewart); parties come from the statewide
block. Nor is the statewide block's status, which says "Not Reported" for every vote type beside complete totals; each county's is.

Run:  python scripts/build_ga_results.py
"""
import io
import json
import re
import zipfile
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "ga"
OUT = ROOT / "data" / "ga" / "results-2026.json"
SITE_URL = "https://results.sos.ga.gov/results/public/Georgia/elections/11032026GeneralAndSpecialElection"
SQ_M_PER_SQ_MI = 2_589_988.110336
COUNTIES = 159
NO_VOTE_TYPES = {"Miller", "Glascock"}
FULTON_DEM_GAP = 3
DONE = ("Election Night Complete", "Fully Reported")  # the file's words for a vote type a county has finished

# the file's id for a contest: (our id, label, menu group)
RACES = {
    "US2": ("u-s-senate", "U.S. Senate", "Federal"),
    "S1": ("governor", "Governor", "Statewide"),
    "S2": ("lieutenant-governor", "Lieutenant Governor", "Statewide"),
    "S3": ("secretary-of-state", "Secretary of State", "Statewide"),
    "S4": ("attorney-general", "Attorney General", "Statewide"),
    "S5": ("agriculture", "Commissioner of Agriculture", "Statewide"),
    "S6": ("insurance", "Commissioner of Insurance", "Statewide"),
    "S7": ("superintendent", "State School Superintendent", "Statewide"),
    "S8": ("labor", "Commissioner of Labor", "Statewide"),
    "S11": ("psc-3", "Public Service Commission, District 3", "Statewide"),
    "S13": ("psc-5", "Public Service Commission, District 5", "Statewide"),
}
PARTY = {"Dem": "DEM", "Rep": "REP"}
SUFFIX = {"SR", "JR", "II", "III", "IV"}


def norm(s):
    return re.sub(r"[^A-Z]", "", s.upper())


def person(text):
    """'Jon Ossoff (I) (Dem)' -> name, last name, incumbent. The file writes both '(I) (Rep)' and '(I)(Rep)'."""
    m = re.fullmatch(r"(.+?)\s*(\(I\))?\s*\((Dem|Rep)\)", text)
    assert m, text
    name = m.group(1)
    return name, next(w for w in reversed(name.split()) if w.upper().strip(".") not in SUFFIX), bool(m.group(2))


# ---------- counties: code, name and land area from the Census file ----------
counties, by_name = [], {}
with zipfile.ZipFile(RAW / "census" / "ga2020.pl.zip").open("gageo2020.pl") as f:
    for line in io.TextIOWrapper(f, encoding="latin-1"):
        r = line.rstrip("\n").split("|")
        if r[2] == "050" and r[3] == "00" and r[4] == "00":
            name = r[86].removesuffix(" County")
            c = dict(fips=r[8].split("US")[1], name=name, landSqMi=round(float(r[-13]) / SQ_M_PER_SQ_MI, 3))
            counties.append(c); by_name[norm(name)] = c
counties.sort(key=lambda c: c["fips"])
assert len(counties) == COUNTIES, len(counties)
index = {c["fips"]: i for i, c in enumerate(counties)}

# ---------- the export: one statewide block, and one block per county ----------
export = json.loads((RAW / "results" / "export-11032026GeneralAndSpecialElection.json").read_text(encoding="utf-8-sig"))
state = {b["id"]: b for b in export["results"]["ballotItems"]}
local = {}
for block in export["localResults"]:
    local[by_name[norm(block["name"].removesuffix(" County"))]["fips"]] = block
assert len(local) == COUNTIES, "the results site's counties differ from the Census's"
made = datetime.fromisoformat(export["createdAt"][:19]).replace(tzinfo=timezone.utc) - timedelta(hours=5)
UPDATED = f"{made:%b}. {made.day}, {made.year}, {made.hour % 12 or 12}:{made:%M} {made:%p} EST"
saved = datetime.fromisoformat((RAW / "results" / "saved-at.txt").read_text().strip().replace("Z", "+00:00"))
RETRIEVED = (saved - timedelta(hours=6)).date().isoformat()  # Central

# ---------- who has reported what, from each county's own status ----------
status = {fips: {s["groupName"]: s["status"] for s in b["reportingStatuses"]} for fips, b in local.items()}
open_by_type = {}
for fips, st in sorted(status.items(), key=lambda kv: by_name[norm(local[kv[0]]["name"].removesuffix(" County"))]["name"]):
    for kind, word in st.items():
        if word not in DONE:
            open_by_type.setdefault(kind, {}).setdefault(word, []).append(local[fips]["name"].removesuffix(" County"))
print("vote types a county hasn't finished:", open_by_type)
assert set(open_by_type) <= {"Provisional", "Absentee by Mail"}, "a county hasn't finished election day or advance voting: look at it"

# ---------- every statewide contest ----------
in_all = [i for i in state if sum(any(b["id"] == i for b in c["ballotItems"]) for c in local.values()) == COUNTIES]
races, left_out, precincts, reporting, not_participating = [], [], 0, 0, 0
for cid in in_all:
    item = state[cid]
    parties = [o["politicalParty"] for o in item["ballotOptions"]]
    if parties.count("Dem") != 1 or parties.count("Rep") != 1:
        left_out.append(item["name"]); continue
    assert cid in RACES, (cid, item["name"], "a statewide contest between a Democrat and a Republican that isn't in RACES")
    rid, label, group = RACES[cid]
    table = [[0, 0, 0, 0] for _ in counties]
    sums = Counter()
    for fips, block in local.items():
        place = block["name"].removesuffix(" County")
        here = [b for b in block["ballotItems"] if b["id"] == cid]
        assert len(here) == 1, (cid, place)
        here = here[0]
        assert here["precinctsParticipating"] == here["precinctsReporting"], (cid, place, "precincts not all reporting")
        if cid == "US2":
            precincts += here["precinctsParticipating"]; reporting += here["precinctsReporting"]
        assert {o["id"] for o in here["ballotOptions"]} == {o["id"] for o in item["ballotOptions"]}, (cid, place, "candidates differ")
        row = table[index[fips]]
        for option in here["ballotOptions"]:
            st = next(o for o in item["ballotOptions"] if o["id"] == option["id"])
            assert person(option["name"])[0] == person(st["name"])[0], (cid, place, option["name"], st["name"])
            votes = option["voteCount"]
            types = [g["voteCount"] for g in option["groupResults"]]
            if place in NO_VOTE_TYPES:
                assert all(t is None for t in types), (cid, place, "vote types have appeared: drop the exception")
            else:
                assert sum(types) == votes, (cid, place, option["name"], "vote types don't add up")
            rows = sum(p["voteCount"] or 0 for p in option["precinctResults"])
            not_participating += cid == "US2" and sum(p["reportingStatus"] == "Not Participating" for p in option["precinctResults"])
            gap = FULTON_DEM_GAP if place == "Fulton" and st["politicalParty"] == "Dem" else 0
            assert rows + gap == votes, (cid, place, option["name"], "precincts don't add up to the county", rows, votes)
            sums[option["id"]] += votes
            row[{"Dem": 0, "Rep": 1}.get(st["politicalParty"], 2)] += votes
            row[3] += votes
    cands = []
    for option in sorted(item["ballotOptions"], key=lambda o: -o["voteCount"]):
        assert sums[option["id"]] == option["voteCount"], (cid, option["name"], "counties don't add up to the statewide figure")
        assert sum(g["voteCount"] for g in option["groupResults"]) == option["voteCount"], (cid, option["name"], "statewide vote types don't add up")
        typed = sum(g["voteCount"] or 0 for c in local.values() for b in c["ballotItems"] if b["id"] == cid for o in b["ballotOptions"] if o["id"] == option["id"] for g in o["groupResults"])
        missing = sum(o["voteCount"] for fips, c in local.items() if c["name"].removesuffix(" County") in NO_VOTE_TYPES for b in c["ballotItems"] if b["id"] == cid for o in b["ballotOptions"] if o["id"] == option["id"])
        assert typed + missing == option["voteCount"], (cid, option["name"], "the statewide vote types don't include the counties with none")
        nm, last, inc = person(option["name"])
        cands.append(dict(name=nm, last=last, party=PARTY[option["politicalParty"]], incumbent=inc, votes=option["voteCount"]))
    assert 2 * cands[0]["votes"] > sum(c["votes"] for c in cands), (cid, "no majority: a runoff, which the page has to say")
    races.append(dict(id=rid, office=item["name"], label=label, group=group, candidates=cands, counties=table))

assert sorted(r["id"] for r in races) == sorted(v[0] for v in RACES.values()), "statewide races differ from the RACES table"
order = [v[0] for v in RACES.values()]
races.sort(key=lambda r: order.index(r["id"]))
for row in races[0]["counties"]:
    assert row[3] >= 10, "a county with under 10 U.S. Senate votes"
assert not any(row[2] for r in races for row in r["counties"]), "another candidate has appeared: review the page's two-candidate wording"

provisional = open_by_type.get("Provisional", {}).get("Not Reported", [])
absentee = open_by_type.get("Absentee by Mail", {}).get("Partially Reported", [])
assert sum(map(len, (w for t in open_by_type.values() for w in t.values()))) == len(provisional) + len(absentee), open_by_type
names = lambda xs: ", ".join(xs[:-1]) + " and " + xs[-1] if len(xs) > 1 else xs[0]
link = lambda url, text: f'<a href="{url}" target="_blank" rel="noopener">{text}</a>'
out = dict(
    meta=dict(
        election=export["electionName"],
        resultsSource="Georgia Secretary of State, Election Results, Media Export (unofficial results; certification pending)",
        resultsUrl=SITE_URL,
        resultsUpdated=UPDATED, retrieved=RETRIEVED,
        reporting=dict(counties=COUNTIES, precincts=precincts, precinctsReporting=reporting,
                       provisionalNotReported=provisional, absenteePartlyReported=absentee,
                       provisionalNames=names(provisional), absenteeNames=names(absentee)),
        landSource="U.S. Census Bureau, 2020 Census Redistricting Data (P.L. 94-171), county land area (AREALAND)",
        countyRow="counties[i] = [Democratic votes, Republican votes, all other votes, total votes] for meta.counties[i]",
        sources=[
            f"Georgia Secretary of State, {link(SITE_URL, 'Election Results')}, Nov. 3, 2026 general election: unofficial results by county from the site's Media Export, made {UPDATED}, retrieved {RETRIEVED}. In that file, {names(provisional)} counties' provisional ballots aren't reported yet, and {names(absentee)} County's absentee ballots are partly reported. The file lists no write-in votes in these races.",
            f"U.S. Census Bureau, {link('https://www.census.gov/programs-surveys/decennial-census/about/rdo/summary-files.html', '2020 Census Redistricting Data')} (P.L. 94-171): county land area and codes, cities, and each block's location and adults, for placing dots within a county.",
            f"U.S. Census Bureau, {link('https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html', '2020 TIGER/Line&reg; Shapefiles')}, tabulation blocks: where people were counted, for keeping dots off empty land. TIGER/Line&reg; is a registered trademark of the Census Bureau. The land grid here is derived from those files and isn't a Census Bureau product.",
            f"U.S. Census Bureau, {link('https://www.census.gov/geographies/mapping-files/time-series/geo/carto-boundary-file.html', 'Cartographic Boundary Files')}, 2017 counties, via {link('https://github.com/topojson/us-atlas', 'us-atlas')} v3.0.1 (counties-10m.json).",
            f"Software: {link('https://threejs.org', 'three.js')} r160, {link('https://github.com/d3/d3-geo', 'd3-geo')} 3.1.1, {link('https://github.com/topojson/topojson-client', 'topojson-client')} 3.1.0.",
        ],
    ),
    counties=counties,
    races=races,
)
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(out, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
print("left out, on the ballot statewide but not one Democrat against one Republican:", left_out)
print(f"not statewide, left out: {len(state) - len(in_all)} contests")
print(f"OK: {len(races)} races; {COUNTIES} counties; {reporting:,} of {precincts:,} precincts reporting (precinct rows marked not participating: {not_participating // 2}); file made {UPDATED}, retrieved {RETRIEVED}.")
for r in races:
    d = next(c for c in r["candidates"] if c["party"] == "DEM"); p = next(c for c in r["candidates"] if c["party"] == "REP")
    print(f"  {r['id']:20} {d['name']}{' (I)' if d['incumbent'] else ''} {d['votes']:,} vs {p['name']}{' (I)' if p['incumbent'] else ''} {p['votes']:,}; total {sum(row[3] for row in r['counties']):,}; D carried {sum(row[0] > row[1] for row in r['counties'])} counties")

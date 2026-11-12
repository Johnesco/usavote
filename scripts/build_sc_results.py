"""Build data/sc/results-2026.json: South Carolina's Nov. 3, 2026 statewide races, by county. The results adapter for South
Carolina (docs/PIPELINE.md, Part 6; docs/records/south-carolina.md). It also places the 2026 U.S. Senate votes on Census 2020
voting districts (VTDs), for scripts/build_precincts.py sc.

Sources, under data/raw/sc/ (not committed):
  results/detailxml.zip, results/counties/<County>.detailxml.zip: South Carolina State Election Commission, Election Night
    Reporting, https://www.enr-scvotes.org/SC/127300/ (results/manifest.json lists each file's address, date and hash)
  census/sc2020.pl.zip: county codes, land area and adults by voting district
  census/tl_2020_45_vtd20.zip: voting district names
The hand-reviewed table data/sc/precinct-crosswalk.csv says which voting districts each result row goes on.

Maps only statewide races with exactly one Democrat and one Republican. Everyone else, write-ins included, is "other".

Stops unless, for every mapped race and candidate: all precincts are reporting, all 46 counties are there, precincts add up to
each county's file, vote types add up to the candidate's county total, each county's file matches the statewide file, and the
counties add up to the statewide total. Also stops unless the table has every result row and every voting district exactly
once, and every Senate vote is still there by county and party after placing them.

How result rows reach voting districts, by the table's method column:
  exact, fix    the row's votes go on that district, as counted (several rows may share one: splits since 2020)
  combine       one row covers several districts, which become one precinct on the map
  no-row-join   a district with no 2026 row joins the district named in join_to, with no votes of its own
  no-row-empty  a district with no 2026 row and under 10 adults stays off the map
  pooled        no clear match: all such votes in the county are shared by adults among the districts no row names
  family        split from one of the listed districts, not clear which: shared by each party's votes there
  county        countywide failsafe and provisional rows, and splits with no clear parent: shared across the county the same way
Shares use whole votes, by largest remainder, party by party, so each county's totals stay exact. The last three are estimates,
and a precinct with at least EST_SHARE of its votes moved there says "(est.)" in its name.

Writes data/raw/sc/derived/precinct-votes.json (not committed: it holds precincts under 10 votes, which build_precincts.py merges).

Run:  python scripts/build_sc_results.py
"""
import csv
import io
import json
import re
import struct
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from chamber import chamber_race, summary as chamber_summary

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "sc"
OUT = ROOT / "data" / "sc" / "results-2026.json"
TABLE = ROOT / "data" / "sc" / "precinct-crosswalk.csv"
UNITS = RAW / "derived" / "precinct-votes.json"
RESULTS_URL = "https://www.enr-scvotes.org/SC/127300/web.345435/#/summary"
RETRIEVED = "2026-11-08"
SQ_M_PER_SQ_MI = 2_589_988.110336
COUNTIES = 46
PRECINCTS = 2312
EST_SHARE = 0.05

# the contest's name, ignoring case, spaces and punctuation: (our id, label, menu group)
RACES = {
    "USSENATE": ("u-s-senate", "U.S. Senate", "Federal"),
    "GOVERNORANDLIEUTENANTGOVERNOR": ("governor", "Governor and Lieutenant Governor", "Statewide"),
    "SECRETARYOFSTATE": ("secretary-of-state", "Secretary of State", "Statewide"),
    "STATETREASURER": ("treasurer", "State Treasurer", "Statewide"),
    "ATTORNEYGENERAL": ("attorney-general", "Attorney General", "Statewide"),
    "COMPTROLLERGENERAL": ("comptroller-general", "Comptroller General", "Statewide"),
    "STATESUPERINTENDENTOFEDUCATION": ("superintendent", "State Superintendent of Education", "Statewide"),
    "COMMISSIONEROFAGRICULTURE": ("agriculture-commissioner", "Commissioner of Agriculture", "Statewide"),
}
# the file's party codes, as the pages spell them (app.js); codes the file doesn't explain stay as they are
PARTY = {"NON": "W", "LIB": "L", "GRN": "GRE"}
SUFFIX = {"SR", "JR", "II", "III", "IV"}


def norm(s):
    return re.sub(r"[^A-Z0-9]", "", s.upper())


def read_xml(path):
    z = zipfile.ZipFile(path)
    return ET.fromstring(z.read("detail.xml"))


def person(text):
    """'REP Darline Graham' -> full name, last name; a ticket 'A / B' is named for its first person."""
    name = re.sub(r"\s+", " ", re.sub(r"^[A-Z]{3} ", "", text)).strip()
    if name == "Write-In": return "Write-ins", "Write-ins"
    words = name.split(" / ")[0].split()
    return name, next(w for w in reversed(words) if w.upper().strip(".") not in SUFFIX)


def by_party_share(total, weights):
    """Split a whole number by weights, by largest remainder; ties go to the earlier entry."""
    sum_w = sum(weights)
    assert sum_w > 0
    exact = [total * w / sum_w for w in weights]
    out = [int(x) for x in exact]
    for i in sorted(range(len(weights)), key=lambda i: (out[i] - exact[i], i))[:total - sum(out)]:
        out[i] += 1
    assert sum(out) == total
    return out


# ---------- counties: code, name and land area from the Census file; adults by voting district ----------
pl = zipfile.ZipFile(RAW / "census" / "sc2020.pl.zip")
counties, by_name, vtd_rec = [], {}, {}
with pl.open("scgeo2020.pl") as f:
    for line in io.TextIOWrapper(f, encoding="latin-1"):
        r = line.rstrip("\n").split("|")
        if r[2] == "050" and r[3] == "00" and r[4] == "00":
            name = r[86].removesuffix(" County")
            c = dict(fips=r[8].split("US")[1], name=name, landSqMi=round(float(r[-13]) / SQ_M_PER_SQ_MI, 3))
            counties.append(c); by_name[norm(name)] = c
        elif r[2] == "700" and r[3] == "00":
            vtd_rec[r[7]] = r[8].split("US")[1]
counties.sort(key=lambda c: c["fips"])
assert len(counties) == COUNTIES, len(counties)
index = {c["fips"]: i for i, c in enumerate(counties)}
adults = {}
with pl.open("sc000022020.pl") as f:
    for line in io.TextIOWrapper(f, encoding="latin-1"):
        r = line.split("|", 6)
        if r[4] in vtd_rec: adults[vtd_rec[r[4]]] = int(r[5])

# ---------- the statewide file and each county's file ----------
state = read_xml(RAW / "results" / "detailxml.zip")
stamp = datetime.strptime(state.findtext("Timestamp").removesuffix(" EST"), "%m/%d/%Y %I:%M:%S %p")
UPDATED = f"{stamp:%b}. {stamp.day}, {stamp:%Y}, {stamp.hour % 12 or 12}:{stamp:%M %p}".replace("May.", "May")
county_xml = {}
for p in sorted((RAW / "results" / "counties").glob("*.detailxml.zip")):
    c = by_name[norm(p.name.split(".")[0])]
    county_xml[c["fips"]] = read_xml(p)
assert len(county_xml) == COUNTIES, len(county_xml)

races, skipped, senate_rows = [], [], {}
for contest in state.findall("Contest"):
    key = norm(contest.get("text"))
    if contest.get("isQuestion") == "true" or int(contest.get("precinctsParticipating")) != PRECINCTS:
        continue
    if key not in RACES:
        skipped.append(contest.get("text")); continue
    assert contest.get("precinctsReported") == contest.get("precinctsParticipating"), (key, "precincts not all reporting")
    rid, label, group = RACES[key]
    choices = contest.findall("Choice")
    parties = [ch.get("party") for ch in choices]
    assert parties.count("DEM") == 1 and parties.count("REP") == 1 and len(set(parties)) == len(parties), (key, parties)

    table = [[0, 0, 0, 0] for _ in counties]
    cands = []
    for ch in choices:
        total = int(ch.get("totalVotes"))
        by_county = Counter()
        for vt in ch.findall("VoteType"):
            for e in vt.findall("County"):
                by_county[by_name[norm(e.get("name"))]["fips"]] += int(e.get("votes"))
        assert len(by_county) == COUNTIES, (key, ch.get("text"), len(by_county))
        assert sum(by_county.values()) == total, (key, ch.get("text"), "counties don't add up to the state total")
        k = {"DEM": 0, "REP": 1}.get(ch.get("party"), 2)
        for fips, v in by_county.items():
            row = table[index[fips]]
            row[k] += v; row[3] += v
        nm, last = person(ch.get("text"))
        cands.append(dict(name=nm, last=last, party=PARTY.get(ch.get("party"), ch.get("party")), incumbent=False, votes=total))
        ch.set("_byCounty", json.dumps(by_county))

    # each county's own file: every candidate, precinct by precinct
    for fips, root in county_xml.items():
        here = [x for x in root.findall("Contest") if norm(x.get("text")) == key]
        assert len(here) == 1, (key, fips, len(here))
        assert here[0].get("precinctsReported") == here[0].get("precinctsReporting"), (key, fips, "precincts not all reporting")
        wanted = {ch.get("party"): json.loads(ch.get("_byCounty"))[fips] for ch in choices}  # one candidate per party: spellings vary between files
        got = {}
        for ch in here[0].findall("Choice"):
            nm = ch.get("party")
            got[nm] = int(ch.get("totalVotes"))
            rows, by_type = Counter(), 0
            for vt in ch.findall("VoteType"):
                by_type += int(vt.get("votes"))
                for e in vt.findall("Precinct"):
                    rows[e.get("name")] += int(e.get("votes"))
            assert by_type == got[nm], (key, fips, nm, "vote types don't add up")
            assert sum(rows.values()) == got[nm], (key, fips, nm, "precincts don't add up to the county file")
            if key == "USSENATE":
                k = {"DEM": 0, "REP": 1}.get(ch.get("party"), 2)
                sink = senate_rows.setdefault(fips, defaultdict(lambda: [0, 0, 0]))
                for name, v in rows.items():
                    sink[name][k] += v
        assert got == wanted, (key, fips, "county file doesn't match the state file", got, wanted)

    cands.sort(key=lambda c: -c["votes"])
    races.append(dict(id=rid, office=contest.get("text"), label=label, group=group, candidates=cands, counties=table))

assert sorted(norm(r["office"]) for r in races) == sorted(RACES), "statewide races differ from the RACES table"
order = list(RACES)
races.sort(key=lambda r: order.index(norm(r["office"])))
print("left out, not on the RACES table:", skipped)

# ---------- 2026 U.S. Senate votes onto 2020 voting districts ----------
z = zipfile.ZipFile(RAW / "census" / "tl_2020_45_vtd20.zip")
dbf = z.read("tl_2020_45_vtd20.dbf")
n, hlen, rlen = struct.unpack("<IHH", dbf[4:12])
fields, off, s = {}, 32, 1
while dbf[off] != 0x0D:
    name, ln = dbf[off:off + 11].split(b"\0")[0].decode(), dbf[off + 16]
    fields[name] = (s, ln); s += ln; off += 32
fld = lambda i, name: dbf[hlen + i * rlen + fields[name][0]: hlen + i * rlen + fields[name][0] + fields[name][1]].decode("utf-8").strip()
vtd_name = {fld(i, "GEOID20"): fld(i, "NAME20") for i in range(n)}

with open(TABLE, encoding="utf-8", newline="") as f:
    table = list(csv.DictReader(f))
seen_rows, seen_vtds, direct = set(), Counter(), []
for t in table:
    if t["result_row"]:
        assert (t["fips"], t["result_row"]) not in seen_rows, t
        seen_rows.add((t["fips"], t["result_row"]))
    t["vtds"] = [] if t["vtd_geoids"] == "*" else t["vtd_geoids"].split("|")
    assert all(g in vtd_name and g[:5] == t["fips"] for g in t["vtds"]), t
    if t["method"] in ("exact", "fix", "combine", "no-row-join", "no-row-empty"):
        seen_vtds.update(t["vtds"])
    if t["method"] == "exact":
        assert norm(t["result_row"]) == norm(vtd_name[t["vtds"][0]]), t
pooled = {g for t in table if t["method"] == "pooled" for g in t["vtds"]}
assert seen_rows == {(f, name) for f, rows in senate_rows.items() for name in rows}, "the table and the results have different rows"
assert not (pooled & set(seen_vtds)), "a pooled district is also named by a row"
assert set(seen_vtds) | pooled == set(vtd_name), "a voting district isn't in the table"

# units: districts that end up as one precinct on the map
parent = {g: g for g in vtd_name}
def find(g):
    while parent[g] != g:
        parent[g] = parent[parent[g]]; g = parent[g]
    return g
for t in table:
    if t["method"] in ("exact", "fix", "combine"):
        for g in t["vtds"][1:]:
            parent[find(g)] = find(t["vtds"][0])
    elif t["method"] == "no-row-join":
        parent[find(t["vtds"][0])] = find(t["join_to"])
empty = {t["vtds"][0] for t in table if t["method"] == "no-row-empty"}
members = defaultdict(list)
for g in sorted(vtd_name):
    if g not in empty: members[find(g)].append(g)
units = {}
for root, gs in sorted(members.items()):
    units[root] = dict(key=int(root), fips=root[:5], vtds=gs, rows=[], names=[], votes=[0, 0, 0], moved=[0, 0, 0])
for t in sorted(table, key=lambda t: t["result_row"]):
    if t["method"] in ("exact", "fix", "combine"):
        u = units[find(t["vtds"][0])]
        votes = senate_rows[t["fips"]][t["result_row"]]
        u["rows"].append(t["result_row"]); u["names"].append(t["unit_name"] or t["result_row"])
        u["votes"] = [a + b for a, b in zip(u["votes"], votes)]
unit_of = {g: u for u in units.values() for g in u["vtds"]}

tally = Counter()
def place(rows_votes, targets, weight_of):
    """rows_votes: [d, r, o] to share; targets: units; weight_of(unit, party)."""
    for k in range(3):
        if not rows_votes[k]: continue
        weights = [weight_of(u, k) for u in targets]
        if not sum(weights): weights = [sum(u["votes"]) for u in targets]  # a party with none of its own votes here
        for u, v in zip(targets, by_party_share(rows_votes[k], weights)):
            u["votes"][k] += v; u["moved"][k] += v

def pool(method):
    """Rows of one method, added up by county and target list, so rounding happens once."""
    groups = defaultdict(lambda: [0, 0, 0])
    for t in table:
        if t["method"] != method: continue
        votes = senate_rows[t["fips"]][t["result_row"]]
        groups[(t["fips"], t["vtd_geoids"])] = [a + b for a, b in zip(groups[(t["fips"], t["vtd_geoids"])], votes)]
        tally[method] += sum(votes)
        tally[method + " rows"] += 1
    return groups

for (fips, geoids), votes in sorted(pool("pooled").items()):
    targets = [unit_of[g] for g in geoids.split("|")]
    assert all(not sum(u["votes"]) for u in targets)
    weights = {id(u): sum(adults[g] for g in u["vtds"]) for u in targets}
    place(votes, targets, lambda u, k: weights[id(u)])
    for g in geoids.split("|"): unit_of[g]["names"] = [vtd_name[g]]
snapshot = {id(u): list(u["votes"]) for u in units.values()}
for (fips, geoids), votes in sorted(pool("family").items()):
    targets = list({id(unit_of[g]): unit_of[g] for g in geoids.split("|")}.values())
    place(votes, targets, lambda u, k: snapshot[id(u)][k])
snapshot = {id(u): list(u["votes"]) for u in units.values()}
for (fips, _), votes in sorted(pool("county").items()):
    targets = [u for u in units.values() if u["fips"] == fips and sum(u["votes"])]
    place(votes, targets, lambda u, k: snapshot[id(u)][k])

# ---------- nothing lost: each county's and party's Senate votes ----------
senate = next(r for r in races if r["id"] == "u-s-senate")
for c, row in zip(counties, senate["counties"]):
    got = [sum(u["votes"][k] for u in units.values() if u["fips"] == "45" + c["fips"][2:]) for k in range(3)]
    assert got == row[:3], (c["name"], got, row)
assert all(u["names"] for u in units.values() if sum(u["votes"])), "a precinct with votes but no name"

as_counted, by_method = 0, Counter()
for t in table:
    if t["method"] in ("exact", "fix", "combine"):
        by_method[t["method"]] += sum(senate_rows[t["fips"]][t["result_row"]])
as_counted = sum(by_method.values())
total_senate = sum(c["votes"] for c in senate["candidates"])
moved = tally["pooled"] + tally["family"] + tally["county"]
assert as_counted + moved == total_senate
special = sum(sum(senate_rows[t["fips"]][t["result_row"]]) for t in table if t["method"] == "county" and t["vtd_geoids"] == "*" and norm(t["result_row"]).startswith(("FAILSAFE", "PROVISIONAL")))
est = 0
for u in units.values():
    if sum(u["votes"]) and sum(u["moved"]) >= EST_SHARE * sum(u["votes"]):
        u["names"] = [u["names"][0] + " (est.)"] + u["names"][1:]
        est += 1
        u["est"] = True

UNITS.parent.mkdir(parents=True, exist_ok=True)
UNITS.write_text(json.dumps(dict(
    units=[dict(key=u["key"], fips=u["fips"], name=", ".join(u["names"]), vtds=u["vtds"], votes=u["votes"], moved=sum(u["moved"])) for u in units.values()],
    empty=sorted(empty),
), separators=(",", ":")), encoding="utf-8")

# ---------- write ----------
fmt = lambda x: f"{x:,}"
# ---------- U.S. House: every district, added up by county, with each district's own result (scripts/chamber.py) ----------
house_votes, house_expect = {}, {}
for contest in state.findall("Contest"):
    m = re.fullmatch(r"U\.S\.\s+House of Representatives, District\s+(\d+)", contest.get("text").strip())
    if not m: continue
    num = int(m.group(1))
    assert contest.get("precinctsReported") == contest.get("precinctsParticipating"), (contest.get("text"), "precincts not all reporting")
    taking_part = {by_name[norm(e.get("name"))]["fips"] for e in contest.find("ParticipatingCounties")}
    house_votes[num], house_expect[num] = {index[f]: {} for f in taking_part}, {}
    for ch in contest.findall("Choice"):
        k = (person(ch.get("text"))[0], PARTY.get(ch.get("party"), ch.get("party")))
        assert k not in house_expect[num], (contest.get("text"), k)
        house_expect[num][k] = int(ch.get("totalVotes"))
        for vt in ch.findall("VoteType"):
            for e in vt.findall("County"):
                here = house_votes[num][index[by_name[norm(e.get("name"))]["fips"]]]  # a KeyError is a county the contest doesn't list as taking part
                here[k] = here.get(k, 0) + int(e.get("votes"))
house = chamber_race("u-s-house", "U.S. House", "Federal", "U.S. House of Representatives", 7, house_votes, COUNTIES, expect=house_expect)
races.append(house)
print(chamber_summary(house))

link = lambda url, text: f'<a href="{url}" target="_blank" rel="noopener">{text}</a>'
tiger = link("https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html", "2020 TIGER/Line®")
out = dict(
    meta=dict(
        election="2026 Statewide General Election (Nov. 3, 2026)",
        resultsSource="South Carolina State Election Commission, Election Night Reporting (unofficial results; certification pending)",
        resultsUrl=RESULTS_URL,
        resultsUpdated=UPDATED, retrieved=RETRIEVED,
        landSource="U.S. Census Bureau, 2020 Census Redistricting Data (P.L. 94-171), county land area (AREALAND)",
        countyRow="counties[i] = [Democratic votes, Republican votes, all other votes, total votes] for meta.counties[i]",
        precinctPlacement=dict(senateVotes=total_senate, asCounted=as_counted, exact=by_method["exact"], fixed=by_method["fix"], combined=by_method["combine"],
                               moved=moved, pooled=tally["pooled"], family=tally["family"], county=tally["county"], failsafeProvisional=special, precinctsMarkedEstimated=est),
        sources=[
            f"South Carolina State Election Commission, {link(RESULTS_URL, 'Election Night Reporting')}, Nov. 3, 2026 general election: the statewide file and all {COUNTIES} county precinct files, as of {UPDATED}, retrieved {RETRIEVED}. These results are unofficial until the state certifies them.",
            f"Where the precinct votes come from: {fmt(as_counted)} of {fmt(total_senate)} U.S. Senate votes ({100 * as_counted / total_senate:.1f}%) were placed on a 2020 voting district by the name of their 2026 precinct, in a {link('data/sc/precinct-crosswalk.csv', 'table you can read')}. The other {fmt(moved)} were shared out by rule, because the precinct is new since 2020 or the row names no precinct: {fmt(special)} countywide failsafe and provisional votes, {fmt(tally['county'] - special)} in new precincts with no clear parent, {fmt(tally['family'])} among a group of districts the name points to, and {fmt(tally['pooled'])} in {fmt(tally['pooled rows'])} rows in Lancaster and Spartanburg counties whose names don't match the 2020 districts. Precincts marked (est.) have at least {EST_SHARE:.0%} of their votes placed this way.",
            f"U.S. Census Bureau, {link('https://www.census.gov/programs-surveys/decennial-census/about/rdo/summary-files.html', '2020 Census Redistricting Data')} (P.L. 94-171): county land area and codes, cities, and each block's location and adults; {tiger} Shapefiles: voting districts for the precinct outlines (simplified here, with districts combined where the 2026 results combine them, and those under 10 votes merged) and blocks for where people were counted. <b>TIGER/Line® is a registered trademark of the Census Bureau, used here only to describe the data. This site repackages that data and is not a Census Bureau product.</b> Census boundaries are for statistical purposes and are not legal land descriptions.",
            f"U.S. Census Bureau, {link('https://www.census.gov/geographies/mapping-files/time-series/geo/carto-boundary-file.html', 'Cartographic Boundary Files')}, 2017 counties, via {link('https://github.com/topojson/us-atlas', 'us-atlas')} v3.0.1 (counties-10m.json).",
            f"Software: {link('https://threejs.org', 'three.js')} r160, {link('https://github.com/d3/d3-geo', 'd3-geo')} 3.1.1, {link('https://github.com/topojson/topojson-client', 'topojson-client')} 3.1.0.",
        ],
    ),
    counties=counties,
    races=races,
)
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(out, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
print(f"OK: {len(races)} races, {COUNTIES} counties, all precincts reporting; precincts match counties and counties match the state file.")
for r in races:
    d = next(c for c in r["candidates"] if c["party"] == "DEM"); p = next(c for c in r["candidates"] if c["party"] == "REP")
    print(f"  {r['id']:26} {d['name']} {d['votes']:,} vs {p['name']} {p['votes']:,}; total {sum(c['votes'] for c in r['candidates']):,}; D carried {sum(row[0] > row[1] for row in r['counties'])} counties")
print(f"Senate votes {total_senate:,}: as counted {as_counted:,} ({100 * as_counted / total_senate:.2f}%: exact {by_method['exact']:,}, fixed {by_method['fix']:,}, combined {by_method['combine']:,}); "
      f"moved {moved:,} (pooled {tally['pooled']:,} in {tally['pooled rows']} rows, family {tally['family']:,} in {tally['family rows']}, county {tally['county']:,} in {tally['county rows']}, of which failsafe and provisional {special:,})")
live = [u for u in units.values() if sum(u["votes"])]
print(f"{len(units)} units, {len(live)} with votes; {sum(len(u['vtds']) > 1 for u in units.values())} hold several districts; {est} marked estimated; {len(empty)} districts left off")
print(f"wrote {UNITS} and {OUT}")

"""Build data/ri/results-2026.json: Rhode Island's Nov. 3, 2026 statewide races, by county. The results adapter for Rhode Island
(docs/PIPELINE.md, Part 6; record in docs/records/rhode-island.md).

Rhode Island reports by city and town, and its five counties have no government of their own, but every town lies in one county, so
towns are added up by county. Which county each town is in comes from the Census file's county subdivision records.

Sources, under data/raw/ri/ (not committed):
  results/export-2026StatewideGeneralElection.json: the Board of Elections results site's Media Export
  results/saved-at.txt and export.headers.txt: when it was saved, and its Last-Modified time
  census/ri2020.pl.zip: county and town codes, names and land area

Maps every statewide contest whose Democrat and Republican finished first and second, with everyone else as "other". Governor isn't
mapped: an independent finished second and the Republican third, which a Democrat-against-Republican map can't show. The script
lists what it left out.

The export also lists a "Federal" entry, ballots for federal offices only (such as from voters overseas). They belong to no town, so
they aren't on the map; the script checks that towns plus that entry make the statewide figure, and Sources gives the count.

Partial: about 90 precincts are marked "Partially Reported" (the count is pinned below), so the pages say "led", not "won".

Stops unless: all 39 towns and the Federal entry are there and every town matches the Census; every town says it has reported, and
the number of partly reported precincts is still the one written down; each candidate's
towns plus the Federal entry add up to the statewide figure; and town results add up within each county.

Run:  python scripts/build_ri_results.py
"""
import io
import json
import re
import zipfile
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

from chamber import chamber_race, summary as chamber_summary

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "ri"
OUT = ROOT / "data" / "ri" / "results-2026.json"
SITE_URL = "https://electionresults.ri.gov/results/public/rhodeisland/elections/2026StatewideGeneralElection"
SQ_M_PER_SQ_MI = 2_589_988.110336
COUNTIES, TOWNS = 5, 39
ET = timezone(timedelta(hours=-5))
PARTIAL_EXPECTED = 90  # precincts the site marks "Partially Reported"; the script stops if this changes, so the pages' wording gets read again

# the export's contest name: (our id, label). U.S. Senate first: the race this state opens on.
RACES = {
    "Senator in Congress": ("u-s-senate", "U.S. Senate"),
    "Lieutenant Governor": ("lieutenant-governor", "Lieutenant Governor"),
    "Attorney General": ("attorney-general", "Attorney General"),
    "General Treasurer": ("treasurer", "General Treasurer"),
}
CHECKED_OUT = {"Governor", "Secretary of State"}  # statewide, but not a Democrat against a Republican: listed in Sources
PARTY = {"DEMOCRAT": "DEM", "REPUBLICAN": "REP", "Independent": "IND", None: "W"}
SUFFIX = {"SR", "JR", "II", "III", "IV"}


def clean(name):
    return re.sub(r"\s*\((DEM|REP|Ind)\)$", "", name).strip()


def last_name(name):
    words = [w.strip(",") for w in name.split() if w.upper().strip(".,") not in SUFFIX]
    return words[-1]


# ---------- counties and towns from the Census file ----------
counties, town_county = [], {}
with zipfile.ZipFile(RAW / "census" / "ri2020.pl.zip").open("rigeo2020.pl") as f:
    for line in io.TextIOWrapper(f, encoding="latin-1"):
        r = line.rstrip("\n").split("|")
        if r[3] != "00" or r[4] != "00":
            continue
        if r[2] == "050":
            counties.append(dict(fips=r[8].split("US")[1], name=r[86].removesuffix(" County"), landSqMi=round(float(r[-13]) / SQ_M_PER_SQ_MI, 3)))
        elif r[2] == "060" and r[86] != "County subdivisions not defined":
            town_county[r[86]] = r[8].split("US")[1][:5]
counties.sort(key=lambda c: c["fips"])
assert len(counties) == COUNTIES and len(town_county) == TOWNS, (len(counties), len(town_county))
index = {c["fips"]: i for i, c in enumerate(counties)}

# ---------- the export ----------
d = json.loads((RAW / "results" / "export-2026StatewideGeneralElection.json").read_text(encoding="utf-8-sig"))
assert d["electionDate"] == "2026-11-03" and d["electionName"] == "Statewide General Election"
modified = parsedate_to_datetime(re.search(r"(?im)^last-modified: (.+)$", (RAW / "results" / "export.headers.txt").read_text())[1].strip()).astimezone(ET)
UPDATED = f"{modified:%b}. {modified.day}, {modified.year}, {modified.hour % 12 or 12}:{modified:%M} {modified:%p} ET"
RETRIEVED = datetime.fromisoformat((RAW / "results" / "saved-at.txt").read_text().strip().replace("Z", "+00:00")).astimezone(ET).date().isoformat()

locals_ = {l["name"]: l for l in d["localResults"]}
assert set(locals_) == set(town_county) | {"Federal"}, set(locals_) ^ (set(town_county) | {"Federal"})
for name, l in locals_.items():
    if name == "Federal":
        continue
    statuses = {s["groupName"]: s["status"] for s in l["reportingStatuses"]}
    assert set(statuses.values()) <= {"Election Night Complete", "Fully Reported"}, (name, statuses)

state_items = {b["name"]: b for b in d["results"]["ballotItems"] if b["type"] == "State"}
races, left_out, federal_only = [], [], {}
precincts = {}  # U.S. Senate precinct id -> status
for office, item in state_items.items():
    if item["contestType"] != "Candidate":
        continue
    in_towns = [n for n, l in locals_.items() if n != "Federal" and any(b["id"] == item["id"] for b in l["ballotItems"])]
    if len(in_towns) != TOWNS:
        continue  # not on the ballot statewide
    opts = sorted(item["ballotOptions"], key=lambda o: -o["voteCount"])
    parties = [o["politicalParty"] for o in opts]
    top_two = sorted(parties[:2], key=str)
    if office not in RACES:
        assert office in CHECKED_OUT, (office, parties, "a statewide contest that isn't in RACES or CHECKED_OUT")
        assert top_two != ["DEMOCRAT", "REPUBLICAN"], (office, "now has a Democrat and a Republican on top: map it")
        left_out.append((office, [(clean(o["name"]), o["politicalParty"], o["voteCount"]) for o in opts if o["politicalParty"]]))
        continue
    assert top_two == ["DEMOCRAT", "REPUBLICAN"] and parties.count("DEMOCRAT") == 1 and parties.count("REPUBLICAN") == 1, (office, parties)
    rid, label = RACES[office]
    ids = [o["id"] for o in opts]
    table = [[0, 0, 0, 0] for _ in counties]
    sums = dict.fromkeys(ids, 0)
    for name, l in locals_.items():
        b = next((b for b in l["ballotItems"] if b["id"] == item["id"]), None)
        if b is None:
            assert name == "Federal"
            continue
        assert b["name"] == office and {o["id"] for o in b["ballotOptions"]} == set(ids), (office, name)
        for o in b["ballotOptions"]:
            sums[o["id"]] += o["voteCount"]
            assert o["voteCount"] == sum(p["voteCount"] for p in o["precinctResults"]), (office, name, "precincts don't add up to the town")
            for p in o["precinctResults"]:
                assert p["reportingStatus"] in ("Election Night Complete", "Fully Reported", "Partially Reported"), (office, name, p["reportingStatus"])
                if office == "Senator in Congress":
                    precincts[p["id"]] = p["reportingStatus"]
        if name == "Federal":
            federal_only[office] = sum(o["voteCount"] for o in b["ballotOptions"])
            continue
        row = table[index[town_county[name]]]
        for o in b["ballotOptions"]:
            row[{"DEMOCRAT": 0, "REPUBLICAN": 1}.get(o["politicalParty"], 2)] += o["voteCount"]
            row[3] += o["voteCount"]
    assert all(sums[o["id"]] == o["voteCount"] for o in opts), (office, "towns and the Federal entry don't add up to the statewide figure")
    assert all(r[0] + r[1] + r[2] == r[3] for r in table)
    cs = []
    for o in opts:
        nm = clean(o["name"])
        cs.append(dict(name=nm, last=last_name(nm) if o["politicalParty"] else nm, party=PARTY[o["politicalParty"]], incumbent=False, votes=o["voteCount"] - (0 if o["politicalParty"] is None else 0)))
    races.append(dict(id=rid, office=office, label=label, group="Statewide", candidates=cs, counties=table))

order = [v[0] for v in RACES.values()]
assert sorted(r["id"] for r in races) == sorted(order), [r["id"] for r in races]
races.sort(key=lambda r: order.index(r["id"]))
fed = federal_only.get("Senator in Congress", 0)
for r in races:  # the map's statewide figures are the towns' sums, so take the Federal-only votes off the candidates' totals too
    item = state_items[r["office"]]
    if r["office"] in federal_only:
        b = next(b for b in locals_["Federal"]["ballotItems"] if b["id"] == item["id"])
        by_name = {clean(o["name"]): o["voteCount"] for o in b["ballotOptions"]}
        for c in r["candidates"]:
            c["votes"] -= by_name[c["name"]]
    assert sum(c["votes"] for c in r["candidates"]) == sum(row[3] for row in r["counties"]), r["id"]
    for k, party in ((0, "DEM"), (1, "REP")):
        assert sum(row[k] for row in r["counties"]) == next(c["votes"] for c in r["candidates"] if c["party"] == party), r["id"]
for row in races[0]["counties"]:
    assert row[3] >= 10
PARTIAL = sum(s == "Partially Reported" for s in precincts.values())
assert PARTIAL == PARTIAL_EXPECTED, (PARTIAL, "partly reported precincts changed: read the record again")

# ---------- U.S. House: every district, added up by county, with each district's own result (scripts/chamber.py) ----------
# Towns add up to counties, as for the statewide races, and the Federal entry's votes belong to no town, so they are left out.
house_votes, house_expect = {}, {}
for num in (1, 2):
    item = state_items[f"Representative in Congress District {num}"]
    assert item["contestType"] == "Candidate" and item["voteFor"] == 1
    key = {o["id"]: (clean(o["name"]), PARTY[o["politicalParty"]]) for o in item["ballotOptions"]}
    house_expect[num] = {key[o["id"]]: o["voteCount"] for o in item["ballotOptions"]}
    house_votes[num] = {}
    for name, l in locals_.items():
        b = next((b for b in l["ballotItems"] if b["id"] == item["id"]), None)
        if b is None: continue
        if name == "Federal":
            for o in b["ballotOptions"]: house_expect[num][key[o["id"]]] -= o["voteCount"]
            continue
        here = house_votes[num].setdefault(index[town_county[name]], {})
        for o in b["ballotOptions"]: here[key[o["id"]]] = here.get(key[o["id"]], 0) + o["voteCount"]
house = chamber_race("u-s-house", "U.S. House", "Federal", "Representative in Congress", 2, house_votes, COUNTIES, expect=house_expect)
races.append(house)
print(chamber_summary(house))

link = lambda url, text: f'<a href="{url}" target="_blank" rel="noopener">{text}</a>'
word = {"DEMOCRAT": "Democrat", "REPUBLICAN": "Republican", "Independent": "independent"}
left_text = "; ".join(f"{office}, " + ", ".join(f"{n} ({word[p]}) {v:,}" for n, p, v in c) for office, c in left_out)
out = dict(
    meta=dict(
        election="2026 General Election (Nov. 3, 2026)",
        resultsSource="Rhode Island Board of Elections, Election Results (unofficial and partial), towns added up by county",
        resultsUrl=SITE_URL,
        resultsUpdated=UPDATED, retrieved=RETRIEVED,
        reporting=dict(counties=COUNTIES, towns=TOWNS, townsReporting=TOWNS, precincts=len(precincts), precinctsPartlyReported=PARTIAL, federalOnlySenateVotes=fed),
        landSource="U.S. Census Bureau, 2020 Census Redistricting Data (P.L. 94-171), county land area (AREALAND)",
        countyRow="counties[i] = [Democratic votes, Republican votes, all other votes, total votes] for meta.counties[i]",
        sources=[
            f"Rhode Island Board of Elections, {link(SITE_URL, 'Election Results')}, Nov. 3, 2026 general election: unofficial results by city and town from the site's Media Export, as of {UPDATED}, retrieved {RETRIEVED}, added up by county here. The State of Rhode Island's {link('https://www.ri.gov/policies/copyright/', 'copyright policy')} says compiled information on its site is public information and may be distributed or copied, and asks for credit.",
            f"Partial: the site marks {PARTIAL} of its {len(precincts):,} precincts \"Partially Reported\", so some ballots, such as provisional ballots, may still be added before the Board of Elections certifies the results.",
            f"Not on the map: {fed:,} U.S. Senate votes on federal-only ballots, which the results list apart from any town. They are in the state's totals but in no county.",
            f"Left out: {left_text}. In the Governor's race an independent finished second, which a map of a Democrat against a Republican can't show. U.S. House has two districts, so it isn't statewide. Ballot questions and local races aren't here either.",
            f"U.S. Census Bureau, {link('https://www.census.gov/programs-surveys/decennial-census/about/rdo/summary-files.html', '2020 Census Redistricting Data')} (P.L. 94-171): county land area and codes, which county each town is in, cities, and each block's location and adults, for placing dots within a county.",
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
print("left out:", [o for o, _ in left_out], "; federal-only Senate votes:", fed)
print(f"OK: {len(races)} races on {COUNTIES} counties from {TOWNS} towns; {PARTIAL} of {len(precincts)} precincts partly reported; unofficial; as of {UPDATED}, retrieved {RETRIEVED}.")
for r in races:
    dm = next(c for c in r["candidates"] if c["party"] == "DEM"); rp = next(c for c in r["candidates"] if c["party"] == "REP")
    print(f"  {r['id']:20} {dm['name']} {dm['votes']:,} vs {rp['name']} {rp['votes']:,}; total {sum(row[3] for row in r['counties']):,}; D carried {sum(row[0] > row[1] for row in r['counties'])} counties")

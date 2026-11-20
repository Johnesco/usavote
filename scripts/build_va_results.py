"""Build data/va/results-2026.json: Virginia's Nov. 3, 2026 U.S. Senate race, and its U.S. House races added up, by county and
independent city. The results adapter for Virginia (docs/PIPELINE.md, Part 6; record in docs/records/virginia.md).

Virginia's 133 localities are 95 counties and 38 independent cities, which the Census counts as county equivalents. Their names here
say which they are ("Fairfax County", "Fairfax City"), so state.js sets countyWord to '' and the pages use the names as they are.

Sources, under data/raw/va/ (not committed):
  results/export-2026-November-General.json: Virginia Department of Elections, the results site's media export
  results/saved-at.txt: when it was saved (UTC)
  census/va2020.pl.zip: locality codes, names and land area

U.S. Senate is the only statewide race between candidates; the rest are district races and constitutional amendments. Write-ins
count as other votes.

Stops unless: all 133 localities match the Census names, once each; every locality has the race with all precincts reporting and
every vote type "Fully Reported"; a locality's candidates are the state's; in each locality, vote types add up to each candidate's
total and precinct rows add up to it too; each candidate's localities add up to the statewide figure; and the winner has a majority.

Run:  python scripts/build_va_results.py
"""
import io
import json
import re
import zipfile
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

from chamber import chamber_race, summary as chamber_summary

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "va"
OUT = ROOT / "data" / "va" / "results-2026.json"
SITE_URL = "https://enr.elections.virginia.gov/results/public/virginia/elections/2026-November-General"
SQ_M_PER_SQ_MI = 2_589_988.110336
COUNTIES = 133
SENATE = "cc142"
PARTY = {"Democratic": "DEM", "Republican": "REP"}
MINOR = {"Independent": "IND", "Libertarian": "LIB", "Green": "GRE"}  # U.S. House candidates' parties as the export spells them
INCUMBENTS = {"Mark R. Warner"}  # the export marks no incumbents
SUFFIX = {"SR", "JR", "II", "III", "IV"}


def last_name(name):
    return next(w for w in reversed(re.sub(r'"[^"]*"', "", name).split()) if w.upper().strip(".,") not in SUFFIX).strip(",")


def display(full):  # "Fairfax County", "Danville city" -> "Fairfax County", "Danville City"
    return full[:-4] + "City" if full.endswith(" city") else full


# ---------- localities: code, name and land area from the Census file ----------
counties, by_name = [], {}
with zipfile.ZipFile(RAW / "census" / "va2020.pl.zip").open("vageo2020.pl") as f:
    for line in io.TextIOWrapper(f, encoding="latin-1"):
        r = line.rstrip("\n").split("|")
        if r[2] == "050" and r[3] == "00" and r[4] == "00":
            c = dict(fips=r[8].split("US")[1], name=display(r[87]), landSqMi=round(float(r[-13]) / SQ_M_PER_SQ_MI, 3))
            counties.append(c)
            by_name[r[87].upper()] = c
counties.sort(key=lambda c: c["fips"])
assert len(counties) == COUNTIES and len(by_name) == COUNTIES
index = {c["fips"]: i for i, c in enumerate(counties)}

# ---------- the export: one statewide block, and one block per locality ----------
export = json.loads((RAW / "results" / "export-2026-November-General.json").read_text(encoding="utf-8-sig"))
state = {b["id"]: b for b in export["results"]["ballotItems"]}
local = {}
for block in export["localResults"]:
    c = by_name[block["name"].upper()]  # "KING and QUEEN COUNTY"
    assert c["fips"] not in local, block["name"]
    local[c["fips"]] = block
assert len(local) == COUNTIES, "the results site's localities differ from the Census's"
for fips, block in local.items():
    st = {s["groupName"]: s["status"] for s in block["reportingStatuses"]}
    assert all(v == "Fully Reported" for v in st.values()), (block["name"], st)
made = datetime.fromisoformat(export["createdAt"][:19]).replace(tzinfo=timezone.utc) - timedelta(hours=5)
UPDATED = f"{made:%b}. {made.day}, {made.year}, {made.hour % 12 or 12}:{made:%M} {made:%p} EST"
saved = datetime.fromisoformat((RAW / "results" / "saved-at.txt").read_text().strip().replace("Z", "+00:00"))
RETRIEVED = (saved - timedelta(hours=6)).date().isoformat()  # Central

# ---------- U.S. Senate ----------
item = state[SENATE]
assert item["name"] == "Member, United States Senate" and item["voteFor"] == 1
parties = [o["politicalParty"] for o in item["ballotOptions"]]
assert parties.count("Democratic") == 1 and parties.count("Republican") == 1, parties
table = [[0, 0, 0, 0] for _ in counties]
sums, precincts = Counter(), 0
for fips, block in local.items():
    here = [b for b in block["ballotItems"] if b["id"] == SENATE]
    assert len(here) == 1, block["name"]
    here = here[0]
    assert here["precinctsParticipating"] == here["precinctsReporting"], (block["name"], "precincts not all reporting")
    precincts += here["precinctsParticipating"]
    assert {o["id"] for o in here["ballotOptions"]} == {o["id"] for o in item["ballotOptions"]}, (block["name"], "candidates differ")
    row = table[index[fips]]
    for o in here["ballotOptions"]:
        st = next(x for x in item["ballotOptions"] if x["id"] == o["id"])
        assert sum(g["voteCount"] for g in o["groupResults"]) == o["voteCount"], (block["name"], o["name"], "vote types don't add up")
        assert sum(p["voteCount"] for p in o["precinctResults"] or []) == o["voteCount"], (block["name"], o["name"], "precincts don't add up")
        row[{"Democratic": 0, "Republican": 1}.get(st["politicalParty"], 2)] += o["voteCount"]
        row[3] += o["voteCount"]
        sums[o["id"]] += o["voteCount"]
cands = []
for o in sorted(item["ballotOptions"], key=lambda o: -o["voteCount"]):
    assert sums[o["id"]] == o["voteCount"], (o["name"], "localities don't add up to the statewide figure")
    if o["politicalParty"] not in PARTY:
        assert o["name"] == "Write-In", o["name"]
        cands.append(dict(name="Write-ins", last="Write-ins", party="W", incumbent=False, votes=o["voteCount"]))
        continue
    cands.append(dict(name=o["name"], last=last_name(o["name"]), party=PARTY[o["politicalParty"]], incumbent=o["name"] in INCUMBENTS, votes=o["voteCount"]))
total = sum(r[3] for r in table)
assert 2 * cands[0]["votes"] > total, "no majority"
assert all(r[3] >= 10 for r in table)
races = [dict(id="u-s-senate", office=item["name"], label="U.S. Senate", group="Federal", candidates=cands, counties=table)]

# ---------- U.S. House: every district, added up by locality, with each district's own result (scripts/chamber.py) ----------
house_votes, house_expect = {}, {}
for cid, it in state.items():
    m = re.fullmatch(r"Member, House of Representatives \((\d+)(st|nd|rd|th) District\)", it["name"])
    if not m: continue
    num = int(m.group(1))
    key = {o["id"]: (o["name"], "W" if o["name"] == "Write-In" else {**PARTY, **MINOR}[o["politicalParty"]]) for o in it["ballotOptions"]}
    house_expect[num] = {key[o["id"]]: o["voteCount"] for o in it["ballotOptions"]}
    house_votes[num] = {}
    for fips, block in local.items():
        here = [b for b in block["ballotItems"] if b["id"] == cid]
        if not here: continue
        assert len(here) == 1 and here[0]["precinctsParticipating"] == here[0]["precinctsReporting"], (cid, block["name"])
        house_votes[num][index[fips]] = {key[o["id"]]: o["voteCount"] for o in here[0]["ballotOptions"]}
assert sorted(house_votes) == list(range(1, 12)), sorted(house_votes)
house = chamber_race("u-s-house", "U.S. House", "Federal", "Member, House of Representatives", 11, house_votes, COUNTIES, expect=house_expect)
races.append(house)
print(chamber_summary(house))

link = lambda url, text: f'<a href="{url}" target="_blank" rel="noopener">{text}</a>'
out = dict(
    meta=dict(
        election="2026 General Election (Nov. 3, 2026)",
        resultsSource="Virginia Department of Elections, Election Results, media export (unofficial results; certification pending)",
        resultsUrl=SITE_URL,
        resultsUpdated=UPDATED, retrieved=RETRIEVED,
        reporting=dict(counties=COUNTIES, countiesReporting=COUNTIES, precincts=precincts, precinctsReporting=precincts),
        landSource="U.S. Census Bureau, 2020 Census Redistricting Data (P.L. 94-171), county and independent city land area (AREALAND)",
        countyRow="counties[i] = [Democratic votes, Republican votes, all other votes, total votes] for meta.counties[i], a county or independent city",
        sources=[
            f"Virginia Department of Elections, {link(SITE_URL, 'Election Results')}, Nov. 3, 2026 general election: unofficial results by county and independent city, as of {UPDATED}, retrieved {RETRIEVED}, from the site's media export, with all {COUNTIES} localities and {precincts:,} precincts reporting. Results become official when the State Board of Elections certifies them.",
            "U.S. Senate is the one statewide race between candidates; write-ins count as other votes. U.S. House is the 11 district races added up by locality. Constitutional amendments and other district races aren't here.",
            "Virginia's 38 independent cities belong to no county; the Census Bureau counts them as county equivalents, as this site does.",
            f"U.S. Census Bureau, {link('https://www.census.gov/programs-surveys/decennial-census/about/rdo/summary-files.html', '2020 Census Redistricting Data')} (P.L. 94-171): county and city land area and codes, cities, and each block's location and adults, for placing dots within a locality.",
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
print(f"OK: U.S. Senate on {COUNTIES} localities, {precincts:,} precincts; {[(c['name'], c['party'], c['votes']) for c in cands]}; other {sum(r[2] for r in table):,}; "
      f"D carried {sum(r[0] > r[1] for r in table)}; fewest {min((r[3], counties[i]['name']) for i, r in enumerate(table))}; most {max((r[3], counties[i]['name']) for i, r in enumerate(table))}")

"""Build data/vt/results-2026.json: Vermont's Nov. 3, 2026 statewide races, by county. The results adapter for Vermont
(docs/PIPELINE.md, Part 6; record in docs/records/vermont.md).

Vermont reports by town (some towns by more than one district), and its counties have little government of their own, but every town
lies in one county, so towns are added up by county. A write-in for a candidate already on the ballot counts as a write-in, as the
site counts it. Which county each town is in comes from the results site's own town list.

Sources, under data/raw/vt/results/ (not committed), the Election Night Results site's files, saved with plain curl:
  election.json                 the election's settings, its towns and each town's county
  s-20261109180316.json         statewide offices, by town and district
  feed-20261109180316.json      federal offices (U.S. House), by town and district
  turnout-20261109180316.json   turnout by town
  feed.headers.txt, saved-at.txt
Land area and county codes: the 2020 Census redistricting file's county records (data/raw/vt/census/vt2020.pl.zip).

Each office's rows include one "STATE WIDE" row; the town rows must add up to it, candidate by candidate. Write-ins, listed by the
site with the candidates, count as "other". Governor's Democrat ran as the nominee of the Democrats and the Progressives (DEM/PROG on
the site) and counts as the Democrat. U.S. Senate isn't on the ballot here in 2026.

Stops unless: the site still calls the results unofficial and all 247 towns have reported; every town is in the site's town list
and its county matches a Census county; every district row is fully reported; town rows add up to the STATE WIDE row; and each mapped
office has exactly one Democrat and one Republican.

Run:  python scripts/build_vt_results.py
"""
import io
import json
import re
import zipfile
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "vt"
OUT = ROOT / "data" / "vt" / "results-2026.json"
SITE_URL = "https://electionresults.vermont.gov/"
STAMP = "20261109180316"
SQ_M_PER_SQ_MI = 2_589_988.110336
COUNTIES, TOWNS = 14, 247
ET = timezone(timedelta(hours=-5))

# the site's office name: (our id, label). Governor first: the race this state opens on.
RACES = {
    "GOVERNOR": ("governor", "Governor"),
    "REPRESENTATIVE TO CONGRESS": ("u-s-house", "U.S. House"),
    "LIEUTENANT GOVERNOR": ("lieutenant-governor", "Lieutenant Governor"),
    "STATE TREASURER": ("treasurer", "State Treasurer"),
    "SECRETARY OF STATE": ("secretary-of-state", "Secretary of State"),
    "AUDITOR OF ACCOUNTS": ("auditor", "Auditor of Accounts"),
    "ATTORNEY GENERAL": ("attorney-general", "Attorney General"),
}
PARTY = {"DEMOCRATIC": "DEM", "DEM/PROG": "DEM", "REPUBLICAN": "REP", "INDEPENDENT": "IND"}
SUFFIX = {"SR", "JR", "II", "III", "IV"}


def title(name):
    t = " ".join(w.capitalize() if w.isalpha() or w.endswith(".") else w.title() for w in name.split())
    return re.sub(r"\bMc(\w)", lambda m: "Mc" + m[1].upper(), t)


def last_name(name):
    return next(w for w in reversed(name.split()) if w.upper().strip(".,") not in SUFFIX).strip(",")


def load(name):
    return json.loads((RAW / "results" / name).read_text(encoding="utf-8-sig"))


# ---------- counties from the Census file ----------
counties = []
with zipfile.ZipFile(RAW / "census" / "vt2020.pl.zip").open("vtgeo2020.pl") as f:
    for line in io.TextIOWrapper(f, encoding="latin-1"):
        r = line.rstrip("\n").split("|")
        if r[2] == "050" and r[3] == "00" and r[4] == "00":
            counties.append(dict(fips=r[8].split("US")[1], name=r[86].removesuffix(" County"), landSqMi=round(float(r[-13]) / SQ_M_PER_SQ_MI, 3)))
counties.sort(key=lambda c: c["fips"])
assert len(counties) == COUNTIES
index = {c["name"].upper(): i for i, c in enumerate(counties)}

# ---------- the election, its towns and their counties ----------
election = load("election.json")
details = election["electionDetails"]
assert details["electionName"] == "2026 GENERAL ELECTION" and details["isOfficial"] is False, details
assert election["townReportingPercent"] == 100, "not every town has reported"
assert election["stateWide"]["path"].endswith(f"-s-{STAMP}.json") and election["federal"]["path"].endswith(f"-f-{STAMP}.json"), "a newer file: save again"
town_county = {}
for t in election["townDistricts"]:
    assert town_county.setdefault(t["townId"], t["countyName"]) == t["countyName"], (t["townName"], "in two counties")
assert len(town_county) == TOWNS and len(election["towns"]) == TOWNS
assert set(town_county.values()) == set(index), set(town_county.values()) ^ set(index)
m = re.fullmatch(r"(\d\d)/(\d\d)/(\d{4}) (\d\d):(\d\d) (AM|PM)", election["lastUpdatedDate"])
stamp = datetime.strptime(" ".join(m.groups()), "%m %d %Y %I %M %p")
UPDATED = f"{stamp:%b}. {stamp.day}, {stamp.year}, {stamp.hour % 12 or 12}:{stamp:%M} {stamp:%p} ET"
RETRIEVED = datetime.fromisoformat((RAW / "results" / "saved-at.txt").read_text().strip().replace("Z", "+00:00")).astimezone(ET).date().isoformat()
turnout = load(f"turnout-{STAMP}.json")["d"]
assert len(turnout) == TOWNS and all(t["tdis"] == t["tdisr"] for t in turnout), "a town's districts aren't all reported"
BALLOTS = sum(t["tvc"] for t in turnout)
REGISTERED = sum(t["tvr"] for t in turnout)

offices = {o["on"]: o for f in (f"s-{STAMP}.json", f"feed-{STAMP}.json") for o in load(f)["d"][0]["o"]}
races = []
for office, (rid, label) in RACES.items():
    o = offices[office]
    table = [[0, 0, 0, 0] for _ in counties]
    towns, state, info = Counter(), None, {}
    seen = set()
    for row in o["cs"]:
        votes = [(r["cn"], r["pn"], r["vc"]) for r in row["rc"]] + [("write-in: " + r["cn"], "W", r["vc"]) for r in row["wc"]]
        for name, party, v in votes:
            prev = info.setdefault(name, party)
            assert prev == party, (office, name, prev, party)
        if row["tn"] == "STATE WIDE":
            assert state is None
            state = Counter()
            for name, _, v in votes:
                state[name] += v
            continue
        done, of = row["distReported"].split("/")
        assert done == of and int(of) > 0, (office, row["tn"], row["distReported"])
        seen.add(row["tid"])
        out = table[index[town_county[row["tid"]]]]
        for name, party, v in votes:
            towns[name] += v
            k = 2 if party == "W" else {"DEM": 0, "REP": 1}.get(PARTY.get(party), 2)
            out[k] += v
            out[3] += v
    assert seen == set(town_county), (office, "towns differ from the site's town list")
    assert state is not None and +towns == +state, (office, "towns don't add up to the STATE WIDE row")
    named = {n: p for n, p in info.items() if p != "W"}
    codes = [PARTY.get(p) for p in named.values()]
    assert codes.count("DEM") == 1 and codes.count("REP") == 1, (office, named)
    cs = []
    for name, party in named.items():
        nm = title(name)
        cs.append(dict(name=nm, last=last_name(nm), party=PARTY.get(party) or title(party).replace(" And ", " and "), incumbent=False, votes=state[name]))
    write_ins = sum(v for n, v in state.items() if n not in named)
    if write_ins:
        cs.append(dict(name="Write-ins", last="Write-ins", party="W", incumbent=False, votes=write_ins))
    cs.sort(key=lambda c: -c["votes"])
    assert sum(c["votes"] for c in cs) == sum(r[3] for r in table)
    races.append(dict(id=rid, office=title(office), label=label, group="Statewide", candidates=cs, counties=table))

for row in races[0]["counties"]:
    assert row[3] >= 10
for r in races:
    assert sum(row[3] for row in r["counties"]) <= BALLOTS, r["id"]

link = lambda url, text: f'<a href="{url}" target="_blank" rel="noopener">{text}</a>'
gov_d = next(c for c in races[0]["candidates"] if c["party"] == "DEM")
out = dict(
    meta=dict(
        election="2026 General Election (Nov. 3, 2026)",
        resultsSource="Vermont Secretary of State, Election Night Results (unofficial), towns added up by county",
        resultsUrl=SITE_URL,
        resultsUpdated=UPDATED, retrieved=RETRIEVED,
        reporting=dict(counties=COUNTIES, towns=TOWNS, townsReporting=TOWNS, ballotsCast=BALLOTS, registered=REGISTERED),
        landSource="U.S. Census Bureau, 2020 Census Redistricting Data (P.L. 94-171), county land area (AREALAND)",
        countyRow="counties[i] = [Democratic votes, Republican votes, all other votes, total votes] for meta.counties[i]",
        sources=[
            f"Vermont Secretary of State, {link(SITE_URL, 'Election Night Results')}, Nov. 3, 2026 general election: unofficial results by town from the site's data files, as of {UPDATED}, retrieved {RETRIEVED}, with all {TOWNS} towns reporting, added up by county here. Write-ins count as other votes; blank votes and overvotes aren't counted.",
            f"Governor: {gov_d['name']} was the nominee of both the Democratic and Progressive parties (\"DEM/PROG\" on the results) and is shown as the Democrat.",
            "Left out: U.S. Senate, which isn't on Vermont's ballot in 2026. Ballot questions, and races not on the ballot statewide, aren't here either. Vermont's constitutional amendments are reported on a separate page.",
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
print(f"OK: {len(races)} races on {COUNTIES} counties from {TOWNS} towns, all reporting; unofficial; {BALLOTS:,} ballots; {REGISTERED:,} registered; as of {UPDATED}, retrieved {RETRIEVED}.")
for r in races:
    d = next(c for c in r["candidates"] if c["party"] == "DEM"); p = next(c for c in r["candidates"] if c["party"] == "REP")
    print(f"  {r['id']:20} {d['name']} {d['votes']:,} vs {p['name']} {p['votes']:,}; total {sum(row[3] for row in r['counties']):,}; D carried {sum(row[0] > row[1] for row in r['counties'])} counties; others {[(c['name'], c['party']) for c in r['candidates'] if c['party'] not in ('DEM', 'REP')][:4]}")
print("fewest Governor votes:", min((row[3], counties[i]["name"]) for i, row in enumerate(races[0]["counties"])))

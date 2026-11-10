"""Build data/ca/results-2026.json: California's Nov. 3, 2026 statewide races, by county. The results adapter for California
(docs/PIPELINE.md, Part 6; record in docs/records/california.md).

Sources, under data/raw/ca/ (not committed):
  results/<race>/<county>.json, results/<race>/statewide.json: the Secretary of State's results API, saved by scripts/ca_results_save.py
  results/unprocessed-extract.json: the statewide row of the Unprocessed Ballots Report, read in a browser
  census/ca2020.pl.zip: county codes, names and land area

Maps every statewide contest with exactly one Democrat and one Republican. California's top-two system can put two candidates of one
party in November (Insurance Commissioner had two Democrats), and Superintendent of Public Instruction is nonpartisan; those are left
out and listed. There's no U.S. Senate race in California in 2026.

Counting goes on for weeks here: about 3 million ballots were left to count when these files were saved, so the pages call the
results partial and say "led", not "won".

Stops unless: every race has all 58 counties, matching the Census names; each county file's statewide block matches the race's
statewide file; each candidate's counties add up to the statewide figure; and the API still says every precinct has reported.

Run:  python scripts/build_ca_results.py
"""
import io
import json
import re
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "ca"
OUT = ROOT / "data" / "ca" / "results-2026.json"
SITE_URL = "https://electionresults.sos.ca.gov/"
UNPROCESSED_URL = "https://electionresults.sos.ca.gov/unprocessed-ballots-status"
SQ_M_PER_SQ_MI = 2_589_988.110336
COUNTIES = 58
PT = timezone(timedelta(hours=-8))

# the API's race name: (our id, label). Governor first: the race this state opens on.
RACES = {
    "governor": ("governor", "Governor"),
    "lieutenant-governor": ("lieutenant-governor", "Lieutenant Governor"),
    "secretary-of-state": ("secretary-of-state", "Secretary of State"),
    "controller": ("controller", "Controller"),
    "treasurer": ("treasurer", "Treasurer"),
    "attorney-general": ("attorney-general", "Attorney General"),
}
OTHER_RACES = ["insurance-commissioner", "superintendent-of-public-instruction"]
PARTY = {"Dem": "DEM", "Rep": "REP", "Lib": "L", "Grn": "G", "PF": "PF", "AI": "AI", "Non": "NP"}
SUFFIX = {"SR", "JR", "II", "III", "IV"}


def num(s):
    return int(str(s).replace(",", ""))


def last_name(name):
    words = [w for w in re.sub(r"\(.*?\)", "", name).split() if w.upper().strip(".,") not in SUFFIX]
    return words[-1].strip(",")


def load(p):
    return json.loads(p.read_text(encoding="utf-8"))


# ---------- counties: code, name and land area from the Census file ----------
counties = []
with zipfile.ZipFile(RAW / "census" / "ca2020.pl.zip").open("cageo2020.pl") as f:
    for line in io.TextIOWrapper(f, encoding="latin-1"):
        r = line.rstrip("\n").split("|")
        if r[2] == "050" and r[3] == "00" and r[4] == "00":
            counties.append(dict(fips=r[8].split("US")[1], name=r[86].removesuffix(" County"), landSqMi=round(float(r[-13]) / SQ_M_PER_SQ_MI, 3)))
counties.sort(key=lambda c: c["fips"])
assert len(counties) == COUNTIES, len(counties)
slug = lambda name: name.lower().replace(" ", "-")
index = {slug(c["name"]): i for i, c in enumerate(counties)}

saved = load(RAW / "results" / "SAVED.json")
RETRIEVED = datetime.fromisoformat(saved["savedAt"]).astimezone(PT).date().isoformat()
unproc = load(RAW / "results" / "unprocessed-extract.json")


def stamp(text):
    m = re.fullmatch(r"(\w+) (\d+), (\d{4}), (\d+):(\d\d) ([ap])\.m\.", text)
    assert m, text
    return f"{m[1][:3]}. {m[2]}, {m[3]}, {m[4]}:{m[5]} {m[6].upper()}M PT"


races, left_out = [], []
updated = set()
for api, (rid, label) in list(RACES.items()) + [(o, (None, None)) for o in OTHER_RACES]:
    state = load(RAW / "results" / api / "statewide.json")
    assert re.fullmatch(r"100% \(([\d,]+) of \1\) precincts reporting", state["Reporting"]), (api, state["Reporting"])
    updated.add(state["ReportingTime"])
    cands = [(c["Name"], c["Party"], num(c["Votes"]), c["incumbent"]) for c in state["candidates"]]
    parties = [p for _, p, _, _ in cands]
    if rid is None:
        assert parties.count("Dem") != 1 or parties.count("Rep") != 1, (api, "now a Democrat against a Republican: map it")
        left_out.append((state["raceTitle"].split(" - ")[0], cands))
        continue
    assert parties.count("Dem") == 1 and parties.count("Rep") == 1, (api, parties)
    table = [[0, 0, 0, 0] for _ in counties]
    sums = [0] * len(cands)
    seen = set()
    for p in sorted((RAW / "results" / api).glob("*.json")):
        if p.name == "statewide.json":
            continue
        county_block, state_block = load(p)
        assert state_block == state, (api, p.name, "a county file's statewide block differs from the statewide file")
        assert county_block["raceTitle"] == f"{state['raceTitle'].split(' - ')[0]} - {county_block['raceTitle'].split(' - ')[1]}", p
        assert re.fullmatch(r"100% \(([\d,]+) of \1\) precincts reporting", county_block["Reporting"]), (api, p.name, county_block["Reporting"])
        i = index[p.stem]
        assert county_block["raceTitle"].endswith(f" - {counties[i]['name']} County Results"), (p, counties[i]["name"])
        seen.add(p.stem)
        names = [c["Name"] for c in county_block["candidates"]]
        assert sorted(names) == sorted(n for n, *_ in cands), (api, p.name, "candidates differ from the state's")
        votes = {c["Name"]: num(c["Votes"]) for c in county_block["candidates"]}
        row = table[i]
        for k, (n, party, _, _) in enumerate(cands):
            v = votes[n]
            row[{"Dem": 0, "Rep": 1}.get(party, 2)] += v
            row[3] += v
            sums[k] += v
    assert seen == set(index), (api, "counties differ from the Census's")
    assert sums == [v for _, _, v, _ in cands], (api, "counties don't add up to the statewide figures")
    cs = [dict(name=n, last=last_name(n), party=PARTY[party], incumbent=bool(inc), votes=v) for n, party, v, inc in sorted(cands, key=lambda t: -t[2])]
    races.append(dict(id=rid, office=state["raceTitle"].split(" - ")[0], label=label, group="Statewide", candidates=cs, counties=table))

assert len(updated) == 1, updated
UPDATED = stamp(updated.pop())
for row in races[0]["counties"]:
    assert row[3] >= 10, "a county with under 10 Governor votes"

link = lambda url, text: f'<a href="{url}" target="_blank" rel="noopener">{text}</a>'
word = {"Dem": "Democrat", "Rep": "Republican", "Non": "nonpartisan"}
left_text = "; ".join(f"{office}, " + " and ".join(f"{n} ({word.get(p, p)})" for n, p, _, _ in sorted(c, key=lambda t: -t[2])) for office, c in left_out)
out = dict(
    meta=dict(
        election="2026 General Election (Nov. 3, 2026)",
        resultsSource="California Secretary of State, Election Results (unofficial and partial; counting continues)",
        resultsUrl=SITE_URL,
        resultsUpdated=UPDATED, retrieved=RETRIEVED,
        reporting=dict(counties=COUNTIES, countiesReporting=COUNTIES, ballotsProcessed=unproc["processed"], ballotsRemaining=unproc["remaining"], remainingAsOf=unproc["asOf"]),
        landSource="U.S. Census Bureau, 2020 Census Redistricting Data (P.L. 94-171), county land area (AREALAND)",
        countyRow="counties[i] = [Democratic votes, Republican votes, all other votes, total votes] for meta.counties[i]",
        sources=[
            f"California Secretary of State, {link(SITE_URL, 'Election Results')}, Nov. 3, 2026 general election: unofficial results by county from the site's results feed, as of {UPDATED}, retrieved {RETRIEVED}. The State of California's {link('https://www.ca.gov/use/', 'Conditions of Use')} say information on its websites is, unless otherwise indicated, in the public domain.",
            f"Counting continues: the state's {link(UNPROCESSED_URL, 'Unprocessed Ballots Report')} estimated {unproc['remaining']:,} ballots still to process statewide as of {unproc['asOf']}, beside {unproc['processed']:,} processed. Counties report final results by {unproc['countiesFinalBy']}, and the Secretary of State certifies by {unproc['certifyBy']}.",
            f"Left out, because they aren't a Democrat against a Republican: {left_text}. There's no U.S. Senate race in California in 2026. Ballot measures, and races not on the ballot statewide, aren't here either.",
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
print("left out:", [o for o, _ in left_out])
print(f"OK: {len(races)} races on {COUNTIES} counties; unofficial and partial, {unproc['remaining']:,} ballots left as of {unproc['asOf']}; as of {UPDATED}, retrieved {RETRIEVED}.")
for r in races:
    d = next(c for c in r["candidates"] if c["party"] == "DEM"); p = next(c for c in r["candidates"] if c["party"] == "REP")
    print(f"  {r['id']:20} {d['name']} {d['votes']:,} vs {p['name']} {p['votes']:,}; total {sum(row[3] for row in r['counties']):,}; D carried {sum(row[0] > row[1] for row in r['counties'])} counties")
print("fewest Governor votes:", min((row[3], counties[i]["name"]) for i, row in enumerate(races[0]["counties"])))

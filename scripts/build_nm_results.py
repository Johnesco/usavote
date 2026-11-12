"""Build data/nm/results-2026.json: New Mexico's Nov. 3, 2026 statewide races, by county. The results adapter for New Mexico
(docs/PIPELINE.md, Part 6; record in docs/records/new-mexico.md).

Sources, saved by scripts/nm_results_save.py into data/raw/nm/results/:
  county-<race id>.json     each contest's votes by county, as the site's "County Results" button reads them (read for the map)
  statewide.csv, federal.csv   the site's exports: statewide totals and precincts reporting
  turnout.html, county-updated.html, media.html   ballots cast, precincts reporting by county, and the "last updated" stamp
Land area and county codes: the 2020 Census redistricting file's county records (data/raw/nm/census/nm2020.pl.zip).

Maps every statewide contest with exactly one Democrat and one Republican. Anyone else in such a contest would count as "other";
as saved, none has anyone else. Contests with no such pair (a one-candidate judge's race, retention votes, amendments and bond
questions) are listed as left out.

Stops unless: all 33 counties are in and match the Census names; every precinct is reported and none is partial, by the county
rows, the county page and the exports; each county's candidates add up to the total behind the site's own percentages and don't
exceed its ballots; and each candidate's counties add up to the state's export.

Run:  python scripts/build_nm_results.py
"""
import csv
import io
import json
import re
import unicodedata
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from chamber import chamber_race, summary as chamber_summary

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "nm" / "results"
OUT = ROOT / "data" / "nm" / "results-2026.json"
SITE_URL = "https://electionresults.sos.nm.gov/resultsSW.aspx?type=SW&map=CTY"
SQ_M_PER_SQ_MI = 2_589_988.110336
COUNTIES = 33

# the file's name for a contest: (our id, label, menu group). The governor's contest is a joint ticket, and says so.
RACES = {
    "United States Senator": ("u-s-senate", "U.S. Senate", "Federal"),
    "Governor and Lieutenant Governor": ("governor", "Governor and Lt. Governor", "Statewide"),
    "Secretary of State": ("secretary-of-state", "Secretary of State", "Statewide"),
    "Attorney General": ("attorney-general", "Attorney General", "Statewide"),
    "State Auditor": ("auditor", "State Auditor", "Statewide"),
    "State Treasurer": ("treasurer", "State Treasurer", "Statewide"),
    "Commissioner of Public Lands": ("land-commissioner", "Commissioner of Public Lands", "Statewide"),
}
KEEP_UPPER = {"II", "III", "IV"}
TWO_WORD_LAST = {"AMANDA LÓPEZ ASKIN": "López Askin"}  # a two-word surname, which the last word alone would cut short


def norm(s):
    """Compare names without case, accents or punctuation: the site writes 'Dona Ana' where the Census writes 'Doña Ana'."""
    return re.sub(r"[^A-Z]", "", unicodedata.normalize("NFKD", s).upper())


def nice(name):
    """The file is in capitals: 'DEB HAALAND AND STEPHANIE GARCIA RICHARD' -> 'Deb Haaland and Stephanie Garcia Richard'."""
    return " ".join("and" if w == "AND" else w if w in KEEP_UPPER else w.capitalize() for w in name.split())


def last_name(name):
    """A joint ticket goes by its first person, the governor."""
    first = name.split(" AND ")[0]
    return TWO_WORD_LAST.get(first) or next(w.capitalize() for w in reversed(first.split()) if w not in KEEP_UPPER | {"SR", "JR"})


def text(name):
    return (RAW / name).read_text(encoding="utf-8")


# ---------- counties: code, name and land area from the Census file ----------
counties, by_name = [], {}
with zipfile.ZipFile(ROOT / "data" / "raw" / "nm" / "census" / "nm2020.pl.zip").open("nmgeo2020.pl") as f:
    for line in io.TextIOWrapper(f, encoding="latin-1"):
        r = line.rstrip("\n").split("|")
        if r[2] == "050" and r[3] == "00" and r[4] == "00":
            name = r[86].removesuffix(" County")
            c = dict(fips=r[8].split("US")[1], name=name, landSqMi=round(float(r[-13]) / SQ_M_PER_SQ_MI, 3))
            counties.append(c); by_name[norm(name)] = c
counties.sort(key=lambda c: c["fips"])
assert len(counties) == COUNTIES, len(counties)
index = {c["fips"]: i for i, c in enumerate(counties)}

# ---------- is everything in? ----------
media = text("media.html")
stamp = re.search(r"Results last updated:</span><span>([^<]+?) MT<", media).group(1)
when = datetime.strptime(stamp, "%m/%d/%Y %I:%M %p")
UPDATED = f"{when:%b}. {when.day}, {when.year}, {when.hour % 12 or 12}:{when:%M} {when:%p} MT"
saved = json.loads(text("SAVED.json"))
RETRIEVED = (datetime.fromisoformat(saved["savedAt"]) + timedelta(hours=-7)).date().isoformat()  # Mountain standard time
head_ballots = int(re.search(r'header-ballot-number">([\d,]+)<', media).group(1).replace(",", ""))
assert "<h1>Unofficial Results</h1>" in media, "the site no longer says Unofficial Results: look at it, and update the wording"
assert "No Possible Recounts at This Time." in text("recounts.html"), "the site lists a possible recount: look at it"

# the county page: "698/698 (100.00%)" reported and "0/698 (0.00%)" partial, per county
page = re.sub(r"(\s*<[^>]+>\s*)+", "\n", text("county-updated.html"))
updated_rows = re.findall(r"\n([A-Z][A-Za-z .]+)\n([A-Z][a-z]{2} +\d+ \d{4} +\d+:\d\d[AP]M)\n(\d+)/(\d+) \([\d.]+%\)\n(\d+)/(\d+) \([\d.]+%\)", page)
assert len(updated_rows) == COUNTIES, len(updated_rows)
precincts_by_county = {}
for nm, _, fully, total, partial, total2 in updated_rows:
    assert fully == total == total2 and partial == "0", (nm, "precincts not all reporting")
    precincts_by_county[norm(nm)] = int(total)
assert set(precincts_by_county) == set(by_name), "the results site's counties differ from the Census's"
PRECINCTS = sum(precincts_by_county.values())

# the turnout page: ballots and eligible voters by precinct, under each county
parts = re.split(r'turnout-results-box-a">\s*<h1>([^<]+)</h1>', text("turnout.html"))
ballots, eligible, hidden = {}, {}, 0
for nm, body in zip(parts[1::2], parts[2::2]):
    cast = re.findall(r'county-cast">\s*<span>([^<]*)</span>', body)
    elig = re.findall(r'county-counted">\s*<span>([^<]*)</span>', body)
    assert len(cast) == len(elig) == precincts_by_county[norm(nm)], (nm, len(cast), len(elig))
    hidden += sum(not v.replace(",", "").isdigit() for v in cast)
    ballots[norm(nm)] = sum(int(v.replace(",", "")) for v in cast if v.replace(",", "").isdigit())
    eligible[norm(nm)] = sum(int(v.replace(",", "")) for v in elig if v.replace(",", "").isdigit())
assert set(ballots) == set(by_name), "the turnout page's counties differ from the Census's"
BALLOTS = sum(ballots.values())
assert BALLOTS == head_ballots and not hidden, ("the turnout page's precincts don't add up to its ballots", BALLOTS, head_ballots, hidden)

# ---------- the state's exports: one row per candidate ----------
state = {}
for name in ("federal.csv", "statewide.csv"):
    for r in csv.DictReader(io.StringIO((RAW / name).read_text(encoding="utf-8-sig"))):
        if not r["AreaNum"]:  # a filled-in area is a district: U.S. House
            state.setdefault(r["RaceName"], []).append(r)

races, left_out = [], []
for office, rs in state.items():
    parties = [r["PartyCode"] for r in rs]
    if parties.count("DEM") != 1 or parties.count("REP") != 1:
        left_out.append(office[:60]); continue
    assert office in RACES, (office, "a statewide contest between a Democrat and a Republican that isn't in RACES")
    assert all(r["PrecinctsReporting"] == f"{PRECINCTS}/{PRECINCTS}" for r in rs), (office, "precincts not all reporting in the export")
    rid, label, group = RACES[office]
    rows = json.loads(text(f"county-{rs[0]['RaceID']}.json"))
    ids = {r["CandidateID"] for r in rs}
    assert all(c["RaceName"] == office and c["CandidateID"] in ids for c in rows), (office, "county rows differ from the export")

    table = [[0, 0, 0, 0] for _ in counties]
    sums = dict.fromkeys(ids, 0)
    seen = {}
    for c in rows:
        key = norm(c["CountyName"])
        assert c["PrecinctsReporting"] == c["TotalPrecincts"] == precincts_by_county[key] and c["PrecinctsPartial"] == 0, (office, key, "precincts not all reporting")
        assert c["calcCandidateVotes"].isdigit(), (office, key, c["calcCandidateVotes"], "votes hidden or missing")
        seen.setdefault(key, []).append(c)
    assert set(seen) == set(by_name), (office, "a county is missing")
    for key, cs in seen.items():
        assert sorted(c["CandidateID"] for c in cs) == sorted(ids), (office, key, "candidates differ")
        total = sum(int(c["calcCandidateVotes"]) for c in cs)
        assert total <= ballots[key], (office, key, "more votes than ballots")
        row = table[index[by_name[key]["fips"]]]
        for c in cs:
            v = int(c["calcCandidateVotes"])
            # the site's percentage is votes over its own county total, so this checks that candidates add up to that total
            assert abs(c["calcCandidatePercentage"] * total - v) < 1e-6, (office, key, c["CandidateID"], "candidates don't add up to the county's total")
            row[{"DEM": 0, "REP": 1}.get(c["PartyCode"], 2)] += v
            row[3] += v
            sums[c["CandidateID"]] += v
    for r in rs:
        assert sums[r["CandidateID"]] == int(r["CandidateVotes"]), (office, r["CandidateName"], "counties don't add up to the state's export")
    assert sum(row[3] for row in table) == sum(int(r["CandidateVotes"]) for r in rs)

    cs = [dict(name=nice(r["CandidateName"]), last=last_name(r["CandidateName"]), party=r["PartyCode"], incumbent=False, votes=int(r["CandidateVotes"]))
          for r in sorted(rs, key=lambda r: -int(r["CandidateVotes"]))]
    races.append(dict(id=rid, office=office, label=label, group=group, candidates=cs, counties=table))

assert sorted(r["office"] for r in races) == sorted(RACES), "statewide races differ from the RACES table"
order = list(RACES)
races.sort(key=lambda r: order.index(r["office"]))
for row in races[0]["counties"]:
    assert row[3] >= 10, "a county with under 10 U.S. Senate votes"

# ---------- U.S. House: every district, added up by county, with each district's own result (scripts/chamber.py) ----------
# The site hides a county figure where fewer than 5 voters cast a ballot (an asterisk). A hidden figure stays out of its county's
# row here, and the district's total, which the state publishes, still counts it. The build stops if more than a few votes or more
# than one figure per candidate are hidden.
house_rows = {}
for r in csv.DictReader(io.StringIO((RAW / "federal.csv").read_text(encoding="utf-8-sig"))):
    if r["RaceName"] == "United States Representative": house_rows.setdefault(r["AreaNum"], []).append(r)
assert sorted(house_rows) == ["DISTRICT 1", "DISTRICT 2", "DISTRICT 3"], sorted(house_rows)
house_votes, house_expect, house_withheld, house_hidden = {}, {}, {}, []
for area, rs in house_rows.items():
    num = int(area.split()[1])
    assert len({r["PrecinctsReporting"] for r in rs}) == 1 and len(set(rs[0]["PrecinctsReporting"].split("/"))) == 1, (area, "precincts not all reporting")
    key = {r["CandidateID"]: (nice(r["CandidateName"]), r["PartyCode"]) for r in rs}
    house_expect[num] = {key[r["CandidateID"]]: int(r["CandidateVotes"]) for r in rs}
    house_votes[num], placed = {}, dict.fromkeys(key.values(), 0)
    for c in json.loads(text(f"county-{rs[0]['RaceID']}.json")):
        assert c["AreaNum"] == area and c["PrecinctsPartial"] == 0, (area, c["CountyName"])
        here = house_votes[num].setdefault(index[by_name[norm(c["CountyName"])]["fips"]], {})
        if c["calcCandidateVotes"].isdigit():
            here[key[c["CandidateID"]]] = int(c["calcCandidateVotes"]); placed[key[c["CandidateID"]]] += int(c["calcCandidateVotes"])
        else:
            assert c["calcCandidateVotes"] == "*", (area, c["CountyName"], c["calcCandidateVotes"])
            here[key[c["CandidateID"]]] = 0; house_hidden.append((num, c["CountyName"], key[c["CandidateID"]]))
    gap = {k: house_expect[num][k] - v for k, v in placed.items() if house_expect[num][k] != v}
    if gap: house_withheld[num] = gap
for num, gap in house_withheld.items():
    for k, v in gap.items():
        assert 0 < v < 5 and sum(1 for h in house_hidden if h[0] == num and h[2] == k) == 1, (num, k, "votes missing from the county rows that one hidden figure doesn't explain")
assert len(house_hidden) == sum(map(len, house_withheld.values())), ("a hidden county figure with no votes behind it", house_hidden)
house = chamber_race("u-s-house", "U.S. House", "Federal", "United States Representative", 3, house_votes, COUNTIES, expect=house_expect, withheld=house_withheld)
races.append(house)
print(chamber_summary(house) + f"; county figures the site hides (fewer than 5 voters), left out of the county's row: {[(n, c) for n, c, _ in house_hidden]}")

link = lambda url, text: f'<a href="{url}" target="_blank" rel="noopener">{text}</a>'
out = dict(
    meta=dict(
        election="2026 General Election (Nov. 3, 2026)",
        resultsSource="New Mexico Secretary of State, Election Results (unofficial results; state canvass pending)",
        resultsUrl=SITE_URL,
        resultsUpdated=UPDATED, retrieved=RETRIEVED,
        reporting=dict(counties=COUNTIES, countiesReporting=COUNTIES, precincts=PRECINCTS, precinctsReporting=PRECINCTS,
                       ballotsCast=BALLOTS, eligibleVoters=sum(eligible.values())),
        landSource="U.S. Census Bureau, 2020 Census Redistricting Data (P.L. 94-171), county land area (AREALAND)",
        countyRow="counties[i] = [Democratic votes, Republican votes, all other votes, total votes] for meta.counties[i]",
        sources=[
            f"New Mexico Secretary of State, {link(SITE_URL, 'Election Results')}, Nov. 3, 2026 general election: unofficial results by county, as the site's county results read them, checked against its statewide exports, as last updated {UPDATED}, retrieved {RETRIEVED}.",
            f"U.S. Census Bureau, {link('https://www.census.gov/programs-surveys/decennial-census/about/rdo/summary-files.html', '2020 Census Redistricting Data')} (P.L. 94-171): county land area and codes, cities, and each block's location and adults, for placing dots within a county.",
            f"U.S. Census Bureau, {link('https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html', '2020 TIGER/Line&reg; Shapefiles')}, tabulation blocks: where people were counted, for keeping dots off empty land. TIGER/Line&reg; is a registered trademark of the Census Bureau; this site and its land grid aren't Census Bureau or TIGER/Line&reg; products.",
            f"U.S. Census Bureau, {link('https://www.census.gov/geographies/mapping-files/time-series/geo/carto-boundary-file.html', 'Cartographic Boundary Files')}, 2017 counties, via {link('https://github.com/topojson/us-atlas', 'us-atlas')} v3.0.1 (counties-10m.json).",
            f"Software: {link('https://threejs.org', 'three.js')} r160, {link('https://github.com/d3/d3-geo', 'd3-geo')} 3.1.1, {link('https://github.com/topojson/topojson-client', 'topojson-client')} 3.1.0.",
        ],
    ),
    counties=counties,
    races=races,
)
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
print("left out, on the ballot statewide but not one Democrat against one Republican:", left_out)
print(f"OK: {len(races)} races; {COUNTIES} counties, {PRECINCTS:,} precincts, all reporting; {BALLOTS:,} ballots, {sum(eligible.values()):,} eligible; updated {UPDATED}, retrieved {RETRIEVED}.")
for r in races:
    d = next(c for c in r["candidates"] if c["party"] == "DEM"); p = next(c for c in r["candidates"] if c["party"] == "REP")
    print(f"  {r['id']:20} {d['name']} ({d['last']}) {d['votes']:,} vs {p['name']} ({p['last']}) {p['votes']:,}; total {sum(row[3] for row in r['counties']):,}; other {sum(row[2] for row in r['counties'])}; D carried {sum(row[0] > row[1] for row in r['counties'])} counties")
print("fewest ballots:", min(ballots.items(), key=lambda kv: kv[1]), "fewest U.S. Senate votes:", min(row[3] for row in races[0]["counties"]))

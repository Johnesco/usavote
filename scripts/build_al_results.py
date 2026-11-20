"""Build data/al/results-2026.json: Alabama's Nov. 3, 2026 statewide races, and its U.S. House races added up, by county. The results
adapter for Alabama (docs/PIPELINE.md, Part 6; record in docs/records/alabama.md).

Sources, under data/raw/al/ (not committed):
  results/2026GeneralElectionPrecinctResults.zip: Alabama Secretary of State, Elections Data Downloads, "2026 General Election
    Results - Precinct Level": one Excel 97 workbook per county, a row per candidate and a column per precinct
  results/csv/: those 67 workbooks saved as CSV by Excel, unchanged otherwise (Python here can't read .xls files)
  results/saved-at.txt: when the zip was saved (UTC)
  census/al2020.pl.zip: county codes, names and land area

Each county's file has a column per polling place, then ABSENTEE and PROVISIONAL (a few spell it PROVSIONAL, and two add
PROVISIONAL ABSENTEE); a county's vote for a candidate is the sum of every column. Straight-party votes are already in each
candidate's rows. Over and under votes aren't votes for anyone and are left out; write-ins count as other votes.

The files have no statewide totals to check against, so the checks are within the files: all 67 counties match the Census names,
once each; every county has every race here with the same candidates and parties; every count is a whole number; each county's
ballots cast are at least its votes in each race; and each race's winner has a majority.

Run:  python scripts/build_al_results.py
"""
import csv
import io
import re
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json

from chamber import chamber_race, summary as chamber_summary

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "al"
OUT = ROOT / "data" / "al" / "results-2026.json"
PAGE_URL = "https://www.sos.alabama.gov/alabama-votes/voter/election-data"
SQ_M_PER_SQ_MI = 2_589_988.110336
COUNTIES = 67
PARTY = {"DEM": "DEM", "REP": "REP", "NON": "W"}
SUFFIX = {"SR", "JR", "II", "III", "IV"}
# contest title in the files -> id, label, group; in the order the page lists them
RACES = {
    "UNITED STATES SENATOR": ("u-s-senate", "U.S. Senate", "Federal"),
    "GOVERNOR": ("governor", "Governor", "Statewide"),
    "LIEUTENANT GOVERNOR": ("lieutenant-governor", "Lieutenant Governor", "Statewide"),
    "ATTORNEY GENERAL": ("attorney-general", "Attorney General", "Statewide"),
    "SECRETARY OF STATE": ("secretary-of-state", "Secretary of State", "Statewide"),
    "STATE TREASURER": ("treasurer", "State Treasurer", "Statewide"),
    "STATE AUDITOR": ("auditor", "State Auditor", "Statewide"),
    "COMMISSIONER OF AGRICULTURE AND INDUSTRIES": ("agriculture", "Commissioner of Agriculture and Industries", "Statewide"),
    "PUBLIC SERVICE COMMISSION, PLACE 1": ("psc-1", "Public Service Commission, Place 1", "Statewide"),
    "PUBLIC SERVICE COMMISSION, PLACE 2": ("psc-2", "Public Service Commission, Place 2", "Statewide"),
    "ASSOCIATE JUSTICE OF THE SUPREME COURT, PLACE 8": ("supreme-court-8", "Supreme Court, Place 8", "Judicial"),
}
NOT_VOTES = {"Over Votes", "Under Votes"}


def norm(s):
    return re.sub(r"[^A-Z]", "", s.upper())


def last_name(name):
    return next(w for w in reversed(re.sub(r'"[^"]*"', "", name).split()) if w.upper().strip(".,") not in SUFFIX).strip(",")


# ---------- counties: code, name and land area from the Census file ----------
counties, by_name = [], {}
with zipfile.ZipFile(RAW / "census" / "al2020.pl.zip").open("algeo2020.pl") as f:
    for line in io.TextIOWrapper(f, encoding="latin-1"):
        r = line.rstrip("\n").split("|")
        if r[2] == "050" and r[3] == "00" and r[4] == "00":
            name = r[86].removesuffix(" County")
            c = dict(fips=r[8].split("US")[1], name=name, landSqMi=round(float(r[-13]) / SQ_M_PER_SQ_MI, 3))
            counties.append(c); by_name[norm(name)] = c
counties.sort(key=lambda c: c["fips"])
assert len(counties) == COUNTIES and len(by_name) == COUNTIES
index = {c["fips"]: i for i, c in enumerate(counties)}

# ---------- the zip's workbooks, as CSV: every contest's rows, summed across columns ----------
with zipfile.ZipFile(RAW / "results" / "2026GeneralElectionPrecinctResults.zip") as z:
    in_zip = sorted(Path(n).stem for n in z.namelist() if n.lower().endswith(".xls"))
csvs = sorted((RAW / "results" / "csv").glob("*.csv"))
assert [p.stem for p in csvs] == in_zip, "the CSVs aren't the zip's workbooks"
files, precincts = {}, 0
for p in csvs:
    c = by_name[norm(p.stem.removeprefix("2026_GENERAL_ELECTION-"))]
    assert c["fips"] not in files, p.stem
    rows = list(csv.reader(p.open(encoding="utf-8-sig", newline="")))
    head = rows[0]
    assert [h.strip() for h in head[:3]] == ["Contest Title", "Party", "Candidate"], (p.stem, head[:3])
    cols = [i for i, h in enumerate(head) if i >= 3 and h.strip()]
    assert not any("TOTAL" in head[i].upper() for i in cols), (p.stem, "a totals column would count twice")
    assert all(not v.strip() for r in rows for i, v in enumerate(r) if i >= 3 and i not in cols), (p.stem, "votes under a blank header")
    precincts += sum(not re.match(r"PROV|ABSENTEE", head[i].strip()) for i in cols)
    contests = {}
    for r in rows[1:]:
        if not r or not r[0].strip(): continue
        title = " ".join(r[0].split())
        vals = [r[i].strip() for i in cols if i < len(r)]
        assert all(re.fullmatch(r"\d*", v) for v in vals), (p.stem, title, r[2])
        contests.setdefault(title, []).append((r[1].strip(), r[2].strip(), sum(int(v or 0) for v in vals)))
    files[c["fips"]] = contests
assert len(files) == COUNTIES
saved = datetime.fromisoformat((RAW / "results" / "saved-at.txt").read_text().strip().replace("Z", "+00:00"))
RETRIEVED = (saved - timedelta(hours=6)).date().isoformat()  # Central
modified = re.search(r"^Last-Modified: (.+)$", (RAW / "results" / "zip.headers.txt").read_text(), re.M).group(1).strip()
mod = datetime.strptime(modified, "%a, %d %b %Y %H:%M:%S GMT").replace(tzinfo=timezone.utc) - timedelta(hours=6)
UPDATED = f"{mod:%b}. {mod.day}, {mod.year}"


def ballots(fips):
    (row,) = files[fips]["BALLOTS CAST - TOTAL"]
    return row[2]


# ---------- the statewide races ----------
races = []
for title, (rid, label, group) in RACES.items():
    table = [[0, 0, 0, 0] for _ in counties]
    shape, sums = None, {}
    for fips, contests in files.items():
        assert title in contests, (title, counties[index[fips]]["name"])
        rows = [r for r in contests[title] if r[1] not in NOT_VOTES]
        here = sorted((party, name) for party, name, _ in rows)
        assert shape is None or here == shape, (title, counties[index[fips]]["name"], "candidates differ", here, shape)
        shape = here
        row = table[index[fips]]
        for party, name, v in rows:
            row[{"DEM": 0, "REP": 1}.get(party, 2)] += v
            row[3] += v
            sums[(party, name)] = sums.get((party, name), 0) + v
        assert row[3] <= ballots(fips), (title, counties[index[fips]]["name"], "more votes than ballots")
    assert [p for p, _ in shape].count("DEM") == 1 and [p for p, _ in shape].count("REP") == 1, (title, shape)
    assert all(p in PARTY for p, _ in shape), (title, shape)
    cands = [dict(name=n, last=last_name(n), party=p, incumbent=False, votes=v) if p in ("DEM", "REP") else
             dict(name="Write-ins", last="Write-ins", party=PARTY[p], incumbent=False, votes=v)
             for (p, n), v in sorted(sums.items(), key=lambda kv: -kv[1])]
    total = sum(r[3] for r in table)
    assert 2 * cands[0]["votes"] > total, (title, "no majority")
    assert all(r[3] >= 10 for r in table), title
    races.append(dict(id=rid, office=title.title().replace(" Of ", " of ").replace(" And ", " and ").replace(" The ", " the "),
                      label=label, group=group, candidates=cands, counties=table))

# ---------- U.S. House: every district, added up by county, with each district's own result (scripts/chamber.py) ----------
house_votes = {}
for fips, contests in files.items():
    for title, rows in contests.items():
        m = re.fullmatch(r"UNITED STATES REPRESENTATIVE, (\d+)(ST|ND|RD|TH) CONGRESSIONAL DISTRICT", title)
        if not m: continue
        house_votes.setdefault(int(m.group(1)), {})[index[fips]] = {(n, PARTY[p]): v for p, n, v in rows if n not in NOT_VOTES}
assert sorted(house_votes) == list(range(1, 8)), sorted(house_votes)
for num, by_county in house_votes.items():  # each district's candidates are the same in every county it reaches
    assert len({frozenset(v) for v in by_county.values()}) == 1, num
house = chamber_race("u-s-house", "U.S. House", "Federal", "United States Representative", 7, house_votes, COUNTIES)
races.append(house)
print(chamber_summary(house))

senate = races[0]
link = lambda url, text: f'<a href="{url}" target="_blank" rel="noopener">{text}</a>'
out = dict(
    meta=dict(
        election="2026 General Election (Nov. 3, 2026)",
        resultsSource="Alabama Secretary of State, Elections Data Downloads, 2026 General Election Results - Precinct Level (certification pending)",
        resultsUrl=PAGE_URL,
        resultsUpdated=UPDATED, retrieved=RETRIEVED,
        reporting=dict(counties=COUNTIES, countiesReporting=COUNTIES, precincts=precincts, precinctsReporting=precincts),
        landSource="U.S. Census Bureau, 2020 Census Redistricting Data (P.L. 94-171), county land area (AREALAND)",
        countyRow="counties[i] = [Democratic votes, Republican votes, all other votes, total votes] for meta.counties[i]",
        sources=[
            f"Alabama Secretary of State, {link(PAGE_URL, 'Elections Data Downloads')}, 2026 General Election Results - Precinct Level: a workbook for each of the {COUNTIES} counties, with a column for each of {precincts:,} polling places and for absentee and provisional ballots, posted {UPDATED}, retrieved {RETRIEVED}. Each county's votes here are the sum of its columns; straight-party votes are already in each candidate's rows. Results become official when the State Canvassing Board certifies them.",
            "The files have no statewide totals, so these sums couldn't be checked against the State's own. Write-ins count as other votes; over and under votes aren't counted. U.S. House is the 7 district races added up by county. Amendments, judicial races other than the Supreme Court, and state board and legislative races aren't here.",
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
for r in races[:-1]:
    print(f"  {r['id']:26} " + ", ".join(f"{c['name']} ({c['party']}) {c['votes']:,}" for c in r["candidates"]) + f"; other {sum(x[2] for x in r['counties']):,}; D carried {sum(x[0] > x[1] for x in r['counties'])}")
print(f"OK: {len(races)} races on {COUNTIES} counties, {precincts:,} polling places; most U.S. Senate votes {max((x[3], counties[i]['name']) for i, x in enumerate(senate['counties']))}")

"""Build data/nh/results-2026.json: New Hampshire's Nov. 3, 2026 U.S. Senate and Governor races, and its U.S. House races added up,
by county. The results adapter for New Hampshire (docs/PIPELINE.md, Part 6; record in docs/records/new-hampshire.md).

Sources, under data/raw/nh/ (not committed):
  results/2026-ge-<race>-<county>.xlsx: New Hampshire Secretary of State, 2026 General Election Results: for Governor and U.S.
    Senator, a file per county with a row per town or ward, and a summary with a row per county; for U.S. House, a file per
    district with a row per town or ward. Saved by Chrome: the server refuses scripts.
  results/saved-at.txt: when they were saved (UTC)
  census/nh2020.pl.zip: county codes, names and land area

The files are Excel workbooks; Python here has no Excel library, so this reads their XML directly (an .xlsx is a zip).

Stops unless: all 10 counties match the Census names, once each; every county file has the summary's candidates; each county's
towns add up to its TOTALS row, which matches the summary's row for that county; the counties add up to the summary's TOTALS;
every House district row is a town or ward found in the county files, each once across the two districts, and the districts
reach every one; each district's rows add up to its TOTALS; and each statewide race's winner has a majority.

Run:  python scripts/build_nh_results.py
"""
import io
import json
import re
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path

from chamber import chamber_race, summary as chamber_summary

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "nh"
RES = RAW / "results"
OUT = ROOT / "data" / "nh" / "results-2026.json"
PAGE_URL = "https://www.sos.nh.gov/2026-general-election-results"
SQ_M_PER_SQ_MI = 2_589_988.110336
COUNTIES = 10
PARTY = {"d": "DEM", "r": "REP", "l": "LIB", "c": "CON", "i": "IND"}
SUFFIX = {"SR", "JR", "II", "III", "IV"}
# file name part -> id, label, group, office; in the order the page lists them
RACES = {
    "us-senator": ("u-s-senate", "U.S. Senate", "Federal", "United States Senator"),
    "governor": ("governor", "Governor", "Statewide", "Governor"),
}
INCUMBENTS = {("Kelly Ayotte", "REP")}  # the files mark no incumbents; Ayotte was elected Governor in 2024
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def sheet_rows(path):
    """The first sheet's rows, as lists of cell text by column letter, read from the workbook's XML."""
    z = zipfile.ZipFile(path)
    sheets = sorted(n for n in z.namelist() if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", n))
    assert sheets == ["xl/worksheets/sheet1.xml"], (path.name, sheets)
    shared = []
    if "xl/sharedStrings.xml" in z.namelist():
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")).iter(NS + "si"):
            shared.append("".join(t.text or "" for t in si.iter(NS + "t")))
    rows = []
    for r in ET.fromstring(z.read(sheets[0])).iter(NS + "row"):
        row = {}
        for c in r.iter(NS + "c"):
            col = re.match(r"[A-Z]+", c.get("r")).group(0)
            v = c.find(NS + "v")
            if c.get("t") == "s": row[col] = shared[int(v.text)]
            elif c.get("t") == "inlineStr": row[col] = "".join(t.text or "" for t in c.iter(NS + "t"))
            else: row[col] = v.text if v is not None else ""
        rows.append(row)
    return rows


def table(path):
    """-> candidates [(column, name, party)], {place: {column: votes}}, TOTALS {column: votes}. Row 3 names the candidates."""
    rows = sheet_rows(path)
    head = rows[2]
    cands = []
    for col, text in sorted(head.items()):
        if col == "A" or not text.strip(): continue
        if text.strip() == "Write-Ins": cands.append((col, "Write-ins", "W")); continue
        m = re.fullmatch(r"(.+), ([a-z])", text.strip())
        assert m and m.group(2) in PARTY, (path.name, text)
        cands.append((col, m.group(1), PARTY[m.group(2)]))
    places, totals = {}, None
    for row in rows[3:]:
        name = (row.get("A") or "").strip()
        if not name: continue
        votes = {}
        for col, _, _ in cands:
            v = (row.get(col) or "0").strip()
            assert re.fullmatch(r"\d+(\.0)?", v), (path.name, name, col, v)
            votes[col] = int(float(v))
        for col, v in row.items():  # nothing in a column without a candidate
            if col != "A" and col not in {c for c, _, _ in cands}: assert not (v or "").strip() or v.strip() == "0", (path.name, name, col, v)
        if name == "TOTALS": totals = votes; continue
        assert totals is None, (path.name, "rows after TOTALS")
        assert name not in places, (path.name, name)
        places[name] = votes
    assert totals is not None, path.name
    for col, _, _ in cands:
        assert sum(p[col] for p in places.values()) == totals[col], (path.name, col, "rows don't add up to TOTALS")
    return cands, places, totals


def last_name(name):
    return next(w for w in reversed(re.sub(r'"[^"]*"', "", name).split()) if w.upper().strip(".,") not in SUFFIX).strip(",")


# ---------- counties: code, name and land area from the Census file ----------
counties, by_name = [], {}
with zipfile.ZipFile(RAW / "census" / "nh2020.pl.zip").open("nhgeo2020.pl") as f:
    for line in io.TextIOWrapper(f, encoding="latin-1"):
        r = line.rstrip("\n").split("|")
        if r[2] == "050" and r[3] == "00" and r[4] == "00":
            name = r[86].removesuffix(" County")
            c = dict(fips=r[8].split("US")[1], name=name, landSqMi=round(float(r[-13]) / SQ_M_PER_SQ_MI, 3))
            counties.append(c); by_name[name.upper()] = c
counties.sort(key=lambda c: c["fips"])
assert len(counties) == COUNTIES and len(by_name) == COUNTIES
index = {c["fips"]: i for i, c in enumerate(counties)}
slug = lambda c: c["name"].lower().replace(" ", "-")

# ---------- Governor and U.S. Senate: each county's towns, checked against the county's TOTALS and the summary ----------
races, town_county = [], {}
for part, (rid, label, group, office) in RACES.items():
    cands, summary_rows, summary_totals = table(RES / f"2026-ge-{part}-summary.xlsx")
    assert {k.upper() for k in summary_rows} == set(by_name), (part, sorted(summary_rows))
    tab = [[0, 0, 0, 0] for _ in counties]
    towns_here = {}
    for c in counties:
        cc, towns, totals = table(RES / f"2026-ge-{part}-{slug(c)}.xlsx")
        assert cc == cands, (part, c["name"], "candidates differ from the summary's")
        assert totals == summary_rows[next(k for k in summary_rows if k.upper() == c["name"].upper())], (part, c["name"], "county TOTALS differ from the summary")
        row = tab[index[c["fips"]]]
        for col, _, party in cands:
            v = totals[col]
            row[{"DEM": 0, "REP": 1}.get(party, 2)] += v
            row[3] += v
        for t in towns: towns_here[t] = c["fips"]
    if town_county: assert towns_here == town_county, (part, "a race's towns differ from another's")
    town_county = towns_here
    for col, _, _ in cands:
        assert sum(totals[col] for totals in summary_rows.values()) == summary_totals[col], (part, col, "counties don't add up to the summary")
    parties = [p for _, _, p in cands]
    assert parties.count("DEM") == 1 and parties.count("REP") == 1, (part, parties)
    cl = [dict(name=n, last=n if p == "W" else last_name(n), party=p, incumbent=(n, p) in INCUMBENTS, votes=summary_totals[col])
          for col, n, p in cands]
    cl.sort(key=lambda c: -c["votes"])
    total = sum(r[3] for r in tab)
    assert total == sum(summary_totals.values())
    assert 2 * cl[0]["votes"] > total, (part, "no majority")
    assert all(r[3] >= 10 for r in tab), part
    races.append(dict(id=rid, office=office, label=label, group=group, candidates=cl, counties=tab))

# ---------- U.S. House: each district's towns, placed in their counties by the county files (scripts/chamber.py) ----------
house_votes, seen = {}, {}
for num in (1, 2):
    cands, towns, totals = table(RES / f"2026-ge-congressional-district-{num}.xlsx")
    votes = {}
    for t, v in towns.items():
        assert t in town_county, (num, t, "not a town in the county files")
        assert t not in seen, (t, "in both districts")
        seen[t] = num
        i = index[town_county[t]]
        here = votes.setdefault(i, {})
        for col, n, p in cands: here[(n, p)] = here.get((n, p), 0) + v[col]
    house_votes[num] = votes
assert set(seen) == set(town_county), sorted(set(town_county) - set(seen))[:10]
house = chamber_race("u-s-house", "U.S. House", "Federal", "Representative in Congress", 2, house_votes, COUNTIES)
races.append(house)
print(chamber_summary(house))

# ---------- dates ----------
modified = max(re.search(r"<dcterms:modified[^>]*>([^<]+)<", zipfile.ZipFile(p).read("docProps/core.xml").decode()).group(1)
               for p in RES.glob("2026-ge-*.xlsx"))
mod = datetime.fromisoformat(modified.replace("Z", "+00:00")) - timedelta(hours=5)
UPDATED = f"{mod:%b}. {mod.day}, {mod.year}"
saved = datetime.fromisoformat((RES / "saved-at.txt").read_text().split()[0].replace("Z", "+00:00"))
RETRIEVED = (saved - timedelta(hours=6)).date().isoformat()  # Central
n_towns = len(town_county)

link = lambda url, text: f'<a href="{url}" target="_blank" rel="noopener">{text}</a>'
out = dict(
    meta=dict(
        election="2026 General Election (Nov. 3, 2026)",
        resultsSource="New Hampshire Secretary of State, 2026 General Election Results, town results added up by county",
        resultsUrl=PAGE_URL,
        resultsUpdated=UPDATED, retrieved=RETRIEVED,
        reporting=dict(counties=COUNTIES, countiesReporting=COUNTIES, precincts=n_towns, precinctsReporting=n_towns),
        landSource="U.S. Census Bureau, 2020 Census Redistricting Data (P.L. 94-171), county land area (AREALAND)",
        countyRow="counties[i] = [Democratic votes, Republican votes, all other votes, total votes] for meta.counties[i]",
        sources=[
            f"New Hampshire Secretary of State, {link(PAGE_URL, '2026 General Election Results')}: the results by town and ward for Governor, U.S. Senator and each U.S. House district, {n_towns} towns and wards in all; files last changed {UPDATED}, retrieved {RETRIEVED}. The Secretary of State says the tallies reflect the town clerks' returns and may change if clerks amend them.",
            "Each county's figures are its towns and wards added up; they match the Secretary of State's own county and statewide totals. Write-ins count as other votes. U.S. House is the 2 district races added up by county.",
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
    print(f"  {r['id']:26} " + ", ".join(f"{c['name']} ({c['party']}) {c['votes']:,}" for c in r["candidates"]) + f"; D carried {sum(x[0] > x[1] for x in r['counties'])}; "
          f"fewest {min((x[3], counties[i]['name']) for i, x in enumerate(r['counties']))}; most {max((x[3], counties[i]['name']) for i, x in enumerate(r['counties']))}")
print(f"OK: {len(races)} races on {COUNTIES} counties, {n_towns} towns and wards; files last changed {UPDATED}")

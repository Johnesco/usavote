"""Build data/ks/results-2026.json: Kansas's Nov. 3, 2026 statewide races, by county. The results adapter for Kansas
(docs/PIPELINE.md, Part 6; record in docs/records/kansas.md).

Sources, under data/raw/ks/ (not committed):
  results/ks-results-extract.json: the statewide page and all 105 county pages of https://ent.sos.ks.gov/kssos_ent.html, read in a
    browser with scripts/ks_extract_results.js, because the site answers plain scripts with a 403.
  census/ks2020.pl.zip: land area and county codes, from the 2020 Census redistricting file's county records.
  shapes/ks_2024g.zip and sos/*: checked here, because build_precincts.py ks relies on them (below).

Maps every statewide race with exactly one Democrat and one Republican; third parties go in "other". The site's results leave out
provisional ballots and write-ins, and they're unofficial until the state certifies them.

Stops unless, for every race: all precincts are reporting in every county; all 105 counties are there, with the same candidates; the
county pages show the same state figures as the statewide page; candidates add up to the statewide page's total; each candidate's
counties add up to the statewide figure; and each county's percentages on the site agree with its candidates' votes (county pages
print no county total, so that's the check that a county's row is whole).

Also stops unless IKE Lab's 2024 President votes match the Secretary of State's official figures, candidate by candidate, in every
county and statewide; 2024-Presidential-Results.xlsx for counties, the official totals PDF (read by hand, OFFICIAL_2024) statewide.

Run:  python scripts/build_ks_results.py
"""
import io
import json
import re
import struct
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "ks"
OUT = ROOT / "data" / "ks" / "results-2026.json"
SITE = "https://ent.sos.ks.gov/kssos_ent.html"
IKE_PAGE = "https://ike-lab.com/electionresults.html"
IKE_ZIP = "https://ike-lab.com/files/ks_2024g.zip"
IKE_ABOUT = "https://ike-lab.com/about_ike.html"
CC_BY = "https://creativecommons.org/licenses/by/4.0/"
SOS_2024 = "https://sos.ks.gov/elections/24elec/2024-General-Election-Official-Vote-Totals.pdf"
TIGER_DOC = "https://www2.census.gov/geo/pdfs/maps-data/data/tiger/tgrshp2020pl/TGRSHP2020PL_TechDoc.pdf"
SQ_M_PER_SQ_MI = 2_589_988.110336
COUNTIES = 105
STATEWIDE_PAGE = "kssos_ent.html"
RETRIEVED = "2026-11-08"  # in Central time; the extract's own stamp is UTC

# the site's name for a race: (our id, label, menu group)
RACES = {
    "United States Senate": ("u-s-senate", "U.S. Senate", "Federal"),
    "Governor / Lt. Governor": ("governor", "Governor", "Statewide"),
    "Attorney General": ("attorney-general", "Attorney General", "Statewide"),
    "Secretary of State": ("secretary-of-state", "Secretary of State", "Statewide"),
    "State Treasurer": ("state-treasurer", "State Treasurer", "Statewide"),
    "Commissioner of Insurance": ("insurance-commissioner", "Commissioner of Insurance", "Statewide"),
}
# the prefix on a candidate's name, in the site's own key; the pages show these as is, and spell out what L and D don't say
PARTY = {"D": "DEM", "R": "REP", "L": "L", "UK": "United Kansas", "i": "Independent"}
SUFFIX = {"SR", "JR", "II", "III", "IV"}
# 2024-General-Election-Official-Vote-Totals.pdf, first page, read by hand
OFFICIAL_2024 = {"D": 544_853, "R": 758_802, "L": 7_614, "K": 16_322}
IKE_FIELDS = {"G24PREDHAR": "D", "G24PRERTRU": "R", "G24PRELOLI": "L", "G24PREIKEN": "K"}


def norm(s):
    return re.sub(r"[^A-Z]", "", s.upper())


def person(cell):
    code, name = cell.split("-", 1)
    last = next(w for w in reversed(name.split()) if w.upper().strip(".") not in SUFFIX)
    return dict(name=name, last=last, party=PARTY[code], incumbent=False)  # the site doesn't say who is an incumbent


def stamp(s):
    return datetime.strptime(s, "%m/%d/%Y %I:%M %p")


def words(t):
    return f"{t:%b}. {t.day}, {t.year}, {t.hour % 12 or 12}:{t:%M %p}"


# ---------- counties: code, name and land area from the Census file ----------
counties, by_name = [], {}
with zipfile.ZipFile(RAW / "census" / "ks2020.pl.zip").open("ksgeo2020.pl") as f:
    for line in io.TextIOWrapper(f, encoding="latin-1"):
        r = line.rstrip("\n").split("|")
        if r[2] == "050" and r[3] == "00" and r[4] == "00":
            name = r[86].removesuffix(" County")
            c = dict(fips=r[8].split("US")[1], name=name, landSqMi=round(float(r[-13]) / SQ_M_PER_SQ_MI, 3))
            counties.append(c); by_name[norm(name)] = c
counties.sort(key=lambda c: c["fips"])
assert len(counties) == COUNTIES, len(counties)
index = {c["fips"]: i for i, c in enumerate(counties)}

# ---------- the extract: the statewide page and one page per county ----------
extract = json.loads((RAW / "results" / "ks-results-extract.json").read_text(encoding="utf-8"))
pages = {p["page"]: p for p in extract["pages"]}
state = pages.pop(STATEWIDE_PAGE)
assert sorted(pages) == sorted(state["counties"]) and len(pages) == COUNTIES, "the county pages read differ from the site's county menu"
notes = state["notes"]
for needle in ("do not include provisional ballots", "no later than November 16, 2026", "on December 1, 2026"):
    assert needle in notes, needle
assert "votes from write-in candidates" in state["step1"]

county_of = {}
for page, p in pages.items():
    assert p["heading"].endswith(" County"), p["heading"]
    county_of[page] = by_name[norm(p["heading"].removesuffix(" County"))]
assert len({c["fips"] for c in county_of.values()}) == COUNTIES, "two pages name one county"
latest = max(stamp(p["countyLastReported"]) for p in pages.values())

races = []
for office, (rid, label, group) in RACES.items():
    s = state["races"][office]
    assert s["reporting"] == s["precincts"], (office, "not all precincts reporting")
    names = [c["name"] for c in s["candidates"]]
    codes = [n.split("-", 1)[0] for n in names]
    assert codes.count("D") == 1 and codes.count("R") == 1, (office, names)
    state_votes = {c["name"]: c["votes"] for c in s["candidates"]}
    assert sum(state_votes.values()) == s["totalVotes"], (office, "candidates don't add up to the site's total")

    table = [[0, 0, 0, 0] for _ in counties]
    summed, precincts = Counter(), 0
    for page, p in pages.items():
        race = p["races"][office]
        assert race["reporting"] == race["precincts"], (office, page, "not all precincts reporting")
        precincts += race["precincts"]
        assert [c["name"] for c in race["candidates"]] == names, (office, page, "different candidates")
        total = sum(c["votes"] for c in race["candidates"])
        row = table[index[county_of[page]["fips"]]]
        for c in race["candidates"]:
            assert c["stateVotes"] == state_votes[c["name"]], (office, page, "state figure differs from the statewide page")
            # the site's percentages are rounded; a mismatch of more than rounding means a row was misread
            assert total and abs(100 * c["votes"] / total - int(c["pct"].rstrip("%"))) <= 1, (office, page, c, total)
            k = {"D": 0, "R": 1}.get(c["name"].split("-", 1)[0], 2)
            row[k] += c["votes"]; row[3] += c["votes"]
            summed[c["name"]] += c["votes"]
    assert dict(summed) == state_votes, (office, "counties don't add up to the statewide page")
    assert precincts == s["precincts"], (office, precincts, s["precincts"])
    assert sum(r[3] for r in table) == s["totalVotes"]

    cands = [dict(person(n), votes=v) for n, v in sorted(state_votes.items(), key=lambda kv: -kv[1])]
    races.append(dict(id=rid, office=office, label=label, group=group, candidates=cands, counties=table))


# ---------- the base race: IKE Lab's 2024 votes against the Secretary of State's ----------
def workbook_rows(path, sheet):
    z = zipfile.ZipFile(path)
    m = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    strings = ["".join(t.text or "" for t in si.iter(m + "t")) for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall(m + "si")]
    for row in ET.fromstring(z.read(f"xl/worksheets/sheet{sheet}.xml")).find(m + "sheetData"):
        cells = {}
        for c in row:
            v = c.find(m + "v")
            if v is not None: cells[re.match("[A-Z]+", c.get("r")).group()] = strings[int(v.text)] if c.get("t") == "s" else v.text
        yield cells


sos_county, sos_precinct, sos_all = defaultdict(Counter), defaultdict(Counter), Counter()
who = {"Kamala": "D", "Donald": "R", "Chase": "L", "Robert": "K"}
for i, c in enumerate(workbook_rows(RAW / "sos" / "2024-Presidential-Results.xlsx", 1)):
    if not i: continue  # the header row
    k, v, cn = who[c["H"].split()[0]], int(c["J"]), c["E"].strip()
    sos_county[norm(cn)][k] += v; sos_precinct[f"{cn}-{c['F'].strip()}"][k] += v; sos_all[k] += v
assert sos_all == Counter(OFFICIAL_2024), ("the workbook differs from the official totals", sos_all)

z = zipfile.ZipFile(RAW / "shapes" / "ks_2024g.zip")
dbf = z.read("ks_2024g.dbf")
n, hlen, rlen = struct.unpack("<IHH", dbf[4:12])
fields, off, pos = {}, 32, 1
while dbf[off] != 0x0D:
    fields[dbf[off:off + 11].split(b"\0")[0].decode()] = (pos, dbf[off + 16]); pos += dbf[off + 16]; off += 32
fld = lambda i, name: dbf[hlen + i * rlen + fields[name][0]: hlen + i * rlen + fields[name][0] + fields[name][1]].decode("latin-1").strip()
ike_county, ike_precinct, ike_all = defaultdict(Counter), {}, Counter()
for i in range(n):
    cn, votes = fld(i, "coname"), Counter({k: int(fld(i, f) or 0) for f, k in IKE_FIELDS.items()})
    ike_county[norm(cn)].update(votes); ike_all.update(votes); ike_precinct[fld(i, "precinct")] = votes
assert ike_all == Counter(OFFICIAL_2024), ("IKE Lab's 2024 votes differ from the official totals", ike_all)
assert set(ike_county) == set(by_name) == set(sos_county), "county names differ"
assert all(ike_county[c] == sos_county[c] for c in ike_county), "IKE Lab's 2024 votes differ from the state's in a county"
differs = {k: (dict(+v), dict(+ike_precinct[k])) for k, v in sos_precinct.items() if k in ike_precinct and +v != +ike_precinct[k]}
only_sos = {k: sum(v.values()) for k, v in sos_precinct.items() if k not in ike_precinct and sum(v.values())}
only_ike = {k: sum(v.values()) for k, v in ike_precinct.items() if k not in sos_precinct and sum(v.values())}
print(f"2024 President: IKE Lab matches the official totals statewide and in all {COUNTIES} counties; D {ike_all['D']:,}, R {ike_all['R']:,}, others {ike_all['L'] + ike_all['K']:,}")
print(f"  by precinct: {len(ike_precinct):,} shapes, {len(sos_precinct):,} rows in the state's file, {len(differs)} named in both with different votes, votes only in the state's file {only_sos}, only in IKE Lab's {only_ike}")
for k, (a, b) in differs.items(): print(f"    {k}: state {a}, IKE Lab {b}")

# ---------- write ----------
link = lambda url, text: f'<a href="{url}" target="_blank" rel="noopener">{text}</a>'
updated = words(latest)
out = dict(
    meta=dict(
        election="2026 General Election (Nov. 3, 2026)",
        resultsSource="Kansas Secretary of State, Unofficial Kansas Election Results (unofficial; provisional ballots and write-ins not included; state certification due Dec. 1, 2026)",
        resultsUrl=SITE,
        resultsUpdated=updated, retrieved=RETRIEVED,
        sitePageStamp=state["lastUpdated"],
        landSource="U.S. Census Bureau, 2020 Census Redistricting Data (P.L. 94-171), county land area (AREALAND)",
        countyRow="counties[i] = [Democratic votes, Republican votes, all other votes, total votes] for meta.counties[i]",
        sources=[
            f"Kansas Secretary of State, {link(SITE, 'Unofficial Kansas Election Results')}, Nov. 3, 2026 general election: county results as the counties last reported them, the latest on {updated}, read from the site's pages on {RETRIEVED}. Per the site, these leave out provisional ballots, which counties count in their canvass by Nov. 16, 2026, and votes for write-in candidates, and they're unofficial until the State Board of Canvassers certifies them, by Dec. 1, 2026.",
            f"IKE Lab, Wichita State University, {link(IKE_PAGE, 'Precinct Result Shapefiles')}, {link(IKE_ZIP, '2024 General')}: 2024 President votes and precinct outlines, for the by-precinct columns and for placing dots, released under a {link(CC_BY, 'CC-BY')} license ({link(IKE_ABOUT, 'IKE Lab')}). Changes made here: outlines converted to longitude and latitude and simplified, precincts under 10 votes merged into the nearest one in their county, precincts with no votes left out, and third-party votes added into one figure.",
            f"Kansas Secretary of State, {link(SOS_2024, '2024 General Election Official Vote Totals')} and 2024 Presidential Results, by precinct: a cross-check on IKE Lab's 2024 votes, which match in every county.",
            f"U.S. Census Bureau, {link('https://www.census.gov/programs-surveys/decennial-census/about/rdo/summary-files.html', '2020 Census Redistricting Data')} (P.L. 94-171): county land area and codes, cities, and each block's location and adults. {link('https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html', '2020 TIGER/Line&reg;')} blocks: where people were counted, for the grid that keeps dots off empty land. TIGER/Line&reg; is a registered trademark of the Census Bureau. This site and its data files aren't Census Bureau products, and the Bureau hasn't reviewed them ({link(TIGER_DOC, 'technical documentation')}, Chapter 1).",
            f"U.S. Census Bureau, {link('https://www.census.gov/geographies/mapping-files/time-series/geo/carto-boundary-file.html', 'Cartographic Boundary Files')}, 2017 counties, via {link('https://github.com/topojson/us-atlas', 'us-atlas')} v3.0.1 (counties-10m.json).",
            f"Software: {link('https://threejs.org', 'three.js')} r160, {link('https://github.com/d3/d3-geo', 'd3-geo')} 3.1.1, {link('https://github.com/topojson/topojson-client', 'topojson-client')} 3.1.0.",
        ],
    ),
    counties=counties,
    races=races,
)
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
print(f"OK: {len(races)} races, {COUNTIES} counties, all {state['races']['United States Senate']['precincts']:,} precincts reporting, latest county report {updated}; counties match the statewide page.")
for r in races:
    d = next(c for c in r["candidates"] if c["party"] == "DEM"); p = next(c for c in r["candidates"] if c["party"] == "REP")
    total = sum(row[3] for row in r["counties"])
    print(f"  {r['id']:24} {d['name']} {d['votes']:,} vs {p['name']} {p['votes']:,}; total {total:,}, margin {abs(d['votes'] - p['votes']):,} ({100 * abs(d['votes'] - p['votes']) / total:.2f}%); D carried {sum(row[0] > row[1] for row in r['counties'])} counties")

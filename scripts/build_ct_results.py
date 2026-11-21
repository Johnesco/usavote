"""Build data/ct/results-2026.json: Connecticut's Nov. 3, 2026 races for Governor and the four other statewide offices, and
its U.S. House races added up, by county. The results adapter for Connecticut (docs/PIPELINE.md, Part 6; record in
docs/records/connecticut.md).

Sources, under data/raw/ct/ (not committed):
  results/*.json: the Secretary of the State's Election Night Reporting site (ctemspublic.tgstg.net), election 108, data
    version in Version.json: Lookupdata (towns, counties, offices, parties, candidates), townVotes (each town's votes by
    office and ballot line), stateVotes (statewide totals by ballot line), candidateGrouping (statewide totals for candidates
    on more than one line), townStatus (each town's reporting status). *.headers.txt hold each file's HTTP headers.
  results/saved-at.txt: when they were saved (UTC)
  census/ct2020.pl.zip: county codes, names and land area

Connecticut counts a candidate nominated by more than one party on each party's line (cross-endorsement); a person's votes
here are their lines added together, and their party is the major party among their lines.

Stops unless: all 8 counties match the Census names, once each; all 169 towns are in a county and reported in full; every
office's towns add up to the State's totals, line by line; candidates on more than one line add up to the State's combined
totals; every town votes for U.S. House (a few towns are split between districts); every line belongs to a known party; each statewide race has one Democrat and one Republican, and its winner a
majority.

Run:  python scripts/build_ct_results.py
"""
import io
import json
import re
import zipfile
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path

from chamber import chamber_race, summary as chamber_summary

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "ct"
RES = RAW / "results"
OUT = ROOT / "data" / "ct" / "results-2026.json"
ENR_URL = "https://ctemspublic.tgstg.net/"
SQ_M_PER_SQ_MI = 2_589_988.110336
COUNTIES, TOWNS = 8, 169
# the State's party codes -> the site's; Write In lines become one "Write-ins" candidate
PARTY = {"D": "DEM", "R": "REP", "WF": "WF", "IND": "IND", "G": "GRE", "LI": "LIB", "PC": "IND", "WI": "W"}
# office name -> id, label, group; in the order the State lists them
RACES = {
    "Governor and Lieutenant Governor": ("governor", "Governor and Lieutenant Governor", "Statewide"),
    "Secretary of the State": ("secretary-of-the-state", "Secretary of the State", "Statewide"),
    "Treasurer": ("treasurer", "State Treasurer", "Statewide"),
    "Comptroller": ("comptroller", "State Comptroller", "Statewide"),
    "Attorney General": ("attorney-general", "Attorney General", "Statewide"),
}
# the files mark no incumbents; all five statewide officers were elected in 2022, and these four House members in 2024
INCUMBENTS = {"Ned Lamont / Susan Bysiewicz", "Stephanie Thomas", "Erick Russell", "Sean Scanlon", "William Tong",
              "Joe Courtney", "Rosa L. DeLauro", "Jim Himes", "Jahana Hayes"}


def load(name):
    return json.loads((RES / f"{name}.json").read_text(encoding="utf-8-sig"))


def rows(entries):
    """[{candidate id: {V, TO}}, ...] -> {candidate id: votes}"""
    out = {}
    for e in entries:
        for cid, x in e.items():
            assert cid not in out and re.fullmatch(r"\d+", x["V"]), (cid, x)
            out[cid] = int(x["V"])
    return out


L = load("Lookupdata")
version = load("Version")["Version"]
town_votes, state_votes, grouping, status = (load(n) for n in ("townVotes_Electiondata", "stateVotes_Electiondata",
                                                                 "candidateGrouping_Electiondata", "townStatus_Electiondata"))
offices = {k: v for d in L["officeList"] for k, v in d.items()}
cand, party = L["candidateIds"], L["partyIds"]

# ---------- counties: code, name and land area from the Census file; towns placed by the State's county list ----------
counties, by_name = [], {}
with zipfile.ZipFile(RAW / "census" / "ct2020.pl.zip").open("ctgeo2020.pl") as f:
    for line in io.TextIOWrapper(f, encoding="latin-1"):
        r = line.rstrip("\n").split("|")
        if r[2] == "050" and r[3] == "00" and r[4] == "00":
            name = r[86].removesuffix(" County")
            c = dict(fips=r[8].split("US")[1], name=name, landSqMi=round(float(r[-13]) / SQ_M_PER_SQ_MI, 3))
            counties.append(c); by_name[name] = c
counties.sort(key=lambda c: c["fips"])
assert len(counties) == COUNTIES and len(by_name) == COUNTIES
assert set(L["counties"].values()) == set(by_name), L["counties"]
index = {c["fips"]: i for i, c in enumerate(counties)}
town_county = {}
for t in L["countyTowns"]:
    assert t["TownID"] not in town_county and t["TownName"] == L["townIds"][t["TownID"]], t
    town_county[t["TownID"]] = index[by_name[L["counties"][t["CountyID"]]]["fips"]]
assert len(town_county) == TOWNS and set(town_county) == set(L["townIds"]) == set(town_votes) == set(status)
for tid, s in status.items():
    m = re.fullmatch(r"(\d+) of (\d+) \(100\.00%\)", s["PR"])
    assert m and m.group(1) == m.group(2) and s["TS"] == "( *Unofficial Results )", (tid, s)


def person(cid):
    """A ballot line's candidate -> their name as shown here (a ticket as "A / B"), and last name."""
    c = cand[cid]
    return c["NM"].replace(" and ", " / ") if " and " in c["NM"] else c["NM"], c["LN"]


def office_votes(oid):
    """-> {candidate id: {county index: votes}}, checked: towns add up to the State's totals, line by line."""
    by_line, total = {}, {}
    for tid, offs in town_votes.items():
        if oid not in offs: continue
        for cid, v in rows(offs[oid]).items():
            by_line.setdefault(cid, {})
            i = town_county[tid]
            by_line[cid][i] = by_line[cid].get(i, 0) + v
            total[cid] = total.get(cid, 0) + v
    assert total == rows(state_votes[oid]), (offices[oid]["NM"], "towns don't add up to the State's totals")
    return by_line


def people(oid, by_line):
    """Lines merged by candidate -> {(name, party): {county index: votes}}, with {(name, party): last name}."""
    merged, lines, last = {}, {}, {}
    for cid, cv in by_line.items():
        code = party[cand[cid]["P"]]["CD"]
        assert code in PARTY, (offices[oid]["NM"], cand[cid]["NM"], code)
        name, ln = ("Write-ins", "Write-ins") if code == "WI" else person(cid)
        lines.setdefault(name, []).append((cid, code))
        last[name] = ln
        for i, v in cv.items():
            merged.setdefault(name, {})
            merged[name][i] = merged[name].get(i, 0) + v
    out, lasts = {}, {}
    for name, ls in lines.items():
        codes = [c for _, c in ls]
        p = "DEM" if "D" in codes else "REP" if "R" in codes else PARTY[codes[0]]
        assert name == "Write-ins" or len(set(codes)) == len(codes), (name, codes)
        assert not ("D" in codes and "R" in codes), name
        if p not in ("DEM", "REP", "W"): assert len(codes) == 1, (name, codes)
        out[(name, p)] = merged[name]; lasts[(name, p)] = last[name]
    # the State's combined totals for candidates on more than one line
    combined = rows(grouping.get(oid, []))
    for cid, v in combined.items():
        name = person(cid)[0]
        assert sum(v for (n, _), cv in out.items() if n == name for v in cv.values()) == v, (offices[oid]["NM"], name)
    for (name, _), cv in out.items():
        if name != "Write-ins" and len(lines[name]) > 1:
            assert any(person(c)[0] == name for c in combined), (offices[oid]["NM"], name, "on more than one line, but not in the State's grouping")
    return out, lasts


# ---------- statewide races ----------
races = []
for nm, (rid, label, group) in RACES.items():
    oid = next(k for k, v in offices.items() if v["NM"] == nm and v["OT"] == "SW")
    votes, lasts = people(oid, office_votes(oid))
    tab = [[0, 0, 0, 0] for _ in counties]
    for (name, p), cv in votes.items():
        for i, v in cv.items():
            tab[i][{"DEM": 0, "REP": 1}.get(p, 2)] += v
            tab[i][3] += v
    parties = [p for _, p in votes]
    assert parties.count("DEM") == 1 and parties.count("REP") == 1, (nm, parties)
    cl = [dict(name=n, last=lasts[(n, p)], party=p, incumbent=n in INCUMBENTS, votes=sum(cv.values())) for (n, p), cv in votes.items()]
    cl.sort(key=lambda c: -c["votes"])
    total = sum(r[3] for r in tab)
    assert total == sum(rows(state_votes[oid]).values())
    assert 2 * cl[0]["votes"] > total, (nm, "no majority")
    assert all(r[3] >= 10 for r in tab), nm
    races.append(dict(id=rid, office=nm, label=label, group=group, candidates=cl, counties=tab))
assert sum(v["OT"] == "SW" for v in offices.values()) == len(RACES), "a statewide office isn't built"

# ---------- U.S. House: each district's towns, already placed in their counties (scripts/chamber.py) ----------
house_votes = {}
for oid, o in offices.items():
    if o["OT"] != "C": continue
    votes, _ = people(oid, office_votes(oid))
    d = house_votes.setdefault(int(o["D"]), {})
    for key, cv in votes.items():
        for i, v in cv.items():
            d.setdefault(i, {})[key] = d.get(i, {}).get(key, 0) + v
assert sorted(house_votes) == [1, 2, 3, 4, 5], sorted(house_votes)
split = sorted(L["townIds"][t] for t, offs in town_votes.items() if sum(offices[o]["OT"] == "C" for o in offs) > 1)
assert all(any(offices[o]["OT"] == "C" for o in offs) for offs in town_votes.values()), "a town votes in no district"
print("towns in two districts:", ", ".join(split))
house = chamber_race("u-s-house", "U.S. House", "Federal", "Representative in Congress", 5, house_votes, COUNTIES,
                     incumbents={(n, "DEM") for n in INCUMBENTS})
races.append(house)
print(chamber_summary(house))

# ---------- dates ----------
modified = max(parsedate_to_datetime(re.search(r"(?im)^last-modified:\s*(.+)$", p.read_text()).group(1).strip())
               for p in RES.glob("*_Electiondata.headers.txt"))
mod = modified - timedelta(hours=5)  # Eastern
UPDATED = f"{mod:%b}. {mod.day}, {mod.year}"
saved = datetime.fromisoformat((RES / "saved-at.txt").read_text().split()[0].replace("Z", "+00:00"))
RETRIEVED = (saved - timedelta(hours=6)).date().isoformat()  # Central

link = lambda url, text: f'<a href="{url}" target="_blank" rel="noopener">{text}</a>'
out = dict(
    meta=dict(
        election="2026 General Election (Nov. 3, 2026)",
        resultsSource="Connecticut Secretary of the State, Election Night Reporting, town results added up by county",
        resultsUrl=ENR_URL,
        resultsUpdated=UPDATED, retrieved=RETRIEVED,
        reporting=dict(counties=COUNTIES, countiesReporting=COUNTIES, precincts=TOWNS, precinctsReporting=TOWNS),
        landSource="U.S. Census Bureau, 2020 Census Redistricting Data (P.L. 94-171), county land area (AREALAND)",
        countyRow="counties[i] = [Democratic votes, Republican votes, all other votes, total votes] for meta.counties[i]",
        sources=[
            f"Connecticut Secretary of the State, {link(ENR_URL, 'Election Night Reporting')}: the results by town for each statewide office and U.S. House district, all {TOWNS} towns reporting, marked unofficial; data version {version}, last changed {UPDATED}, retrieved {RETRIEVED}.",
            "Connecticut lists a candidate nominated by more than one party on each party's line; their votes here are their lines added together, under the major party among them, and match the State's own combined totals. Each county's figures are its towns added up, and the towns add up exactly to the State's totals. Connecticut has no county government, but its 8 counties are still the Census Bureau's. Write-ins count as other votes. U.S. House is the 5 district races added up by county.",
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
    print(f"  {r['id']:24} " + ", ".join(f"{c['name']} ({c['party']}) {c['votes']:,}" for c in r["candidates"]) + f"; D carried {sum(x[0] > x[1] for x in r['counties'])}; "
          f"fewest {min((x[3], counties[i]['name']) for i, x in enumerate(r['counties']))}")
print(f"OK: {len(races)} races on {COUNTIES} counties, {TOWNS} towns; data version {version}, last changed {UPDATED}")

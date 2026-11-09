"""Build data/ia/results-2026.json: Iowa's Nov. 3, 2026 statewide races, by county. The results adapter for Iowa
(docs/PIPELINE.md, Part 6; record in docs/records/iowa.md).

Sources, saved from a browser by scripts/ia_results_save.js and unpacked by scripts/ia_results_unpack.py into data/raw/ia/results/:
  detailtxt-detail.txt   the site's Detail TXT report: each contest's votes by county (read for the map)
  summary-summary.csv    its Summary CSV report: statewide totals and counties reporting
  ALL.json, sum.json, summary.json, details.json, status.json, electionsettings.json   the same results as the site's pages read them
Land area and county codes: the 2020 Census redistricting file's county records (data/raw/ia/census/ia2020.pl.zip).

Maps every contest on the ballot in all 99 counties with exactly one Democrat and one Republican. Libertarians and write-ins
count as "other". The rest of the statewide ballot (Constitutional Amendment 1, the Court of Appeals retention votes) isn't a
contest between candidates; the script lists what it left out.

Stops unless: every county has reported every precinct; all 99 counties are in every mapped race and match the Census names;
each county's candidates add up to its total; each candidate's counties add up to the Summary CSV and the site's other files.

summary.json's "PR" field reads 95 of 99 for the statewide contests, against 99 of 99 in the Summary CSV, sum.json and status.json, with
identical votes in every contest in all of them. That one field isn't trusted, but the script stops if its votes ever differ.

Run:  python scripts/build_ia_results.py
"""
import csv
import io
import json
import re
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "ia"
OUT = ROOT / "data" / "ia" / "results-2026.json"
SITE_URL = "https://electionresults.iowa.gov/IA/127077/web.345435/#/reporting"
SQ_M_PER_SQ_MI = 2_589_988.110336
COUNTIES = 99
COMPLETE = 4  # status.json's code for a county shown as "Completely Reported"

# the file's name for a contest: (our id, label, menu group). The governor's contest is a joint ticket, and says so.
RACES = {
    "United States Senator": ("u-s-senate", "U.S. Senate", "Federal"),
    "Governor and Lt. Governor": ("governor", "Governor and Lt. Governor", "Statewide"),
    "Secretary of State": ("secretary-of-state", "Secretary of State", "Statewide"),
    "Auditor of State": ("auditor", "Auditor of State", "Statewide"),
    "Treasurer of State": ("treasurer", "Treasurer of State", "Statewide"),
    "Secretary of Agriculture": ("agriculture", "Secretary of Agriculture", "Statewide"),
    "Attorney General": ("attorney-general", "Attorney General", "Statewide"),
}
PARTY = {"DEM": "DEM", "REP": "REP", "LIB": "L"}  # the site's Texas codes, so the shared page text can name them
SUFFIX = {"SR", "JR", "II", "III", "IV"}


def load(name):
    return json.loads((RAW / "results" / name).read_text(encoding="utf-8"))


def norm(s):
    return re.sub(r"[^A-Z]", "", s.upper())


def last_name(name):
    """A joint ticket goes by its first person, the governor: 'Rob Sand and Dave Muhlbauer' -> Sand."""
    return next(w for w in reversed(name.split(" and ")[0].split()) if w.upper().strip(".") not in SUFFIX)


# ---------- counties: code, name and land area from the Census file ----------
counties, by_name = [], {}
with zipfile.ZipFile(RAW / "census" / "ia2020.pl.zip").open("iageo2020.pl") as f:
    for line in io.TextIOWrapper(f, encoding="latin-1"):
        r = line.rstrip("\n").split("|")
        if r[2] == "050" and r[3] == "00" and r[4] == "00":
            name = r[86].removesuffix(" County")
            c = dict(fips=r[8].split("US")[1], name=name, landSqMi=round(float(r[-13]) / SQ_M_PER_SQ_MI, 3))
            counties.append(c); by_name[norm(name)] = c
counties.sort(key=lambda c: c["fips"])
assert len(counties) == COUNTIES, len(counties)
index = {c["fips"]: i for i, c in enumerate(counties)}

# ---------- are all the counties in? ----------
status = load("status.json")
saved = load("SAVED.json")
assert len(status["P"]) == COUNTIES and {norm(p) for p in status["P"]} == set(by_name), "the results site's counties differ from the Census's"
assert status["S"] == [COMPLETE] * COUNTIES, "a county isn't shown as completely reported"
assert status["PX"] == status["PY"], "a county has precincts not reporting"
assert all(status["C"]) or not any(status["C"]), "only some counties are marked certified"
CERTIFIED = sum(1 for c in status["C"] if c)
PRECINCTS, BALLOTS = sum(status["PY"]), sum(status["B"])

stamp = re.search(r'"websiteupdatedat"\s*:\s*"([^"]+)"', (RAW / "results" / "electionsettings.json").read_text(encoding="latin-1")).group(1)
when = datetime.strptime(stamp.removesuffix(" CST"), "%m/%d/%Y %I:%M:%S %p")
UPDATED = f"{when:%b}. {when.day}, {when.year}, {when.hour % 12 or 12}:{when:%M} {when:%p} CST"
RETRIEVED = (datetime.fromisoformat(saved["savedAt"].replace("Z", "+00:00")) + timedelta(hours=-6)).date().isoformat()  # Central

# ---------- the Detail TXT report: one block per contest ----------
lines = (RAW / "results" / "detailtxt-detail.txt").read_text(encoding="latin-1").split("\n")
cells = lambda s: re.split(r"\s{2,}", s.strip())
detail = {}
i = 0
while i < len(lines):
    if not lines[i].lstrip().startswith("County"):
        i += 1; continue
    head = cells(lines[i])
    if "Election Day" not in head:  # the first table: registered voters and ballots by county
        table, i = {}, i + 1
        while not lines[i].startswith("Total"):
            n, reg, ballots, _ = cells(lines[i]); table[norm(n)] = (int(reg), int(ballots)); i += 1
        turnout = table
        continue
    title = re.sub(r"\s*\(\s*\d+\s*\)\s*$", "", lines[i - 2].strip())
    cands = cells(lines[i - 1])
    assert head[:2] == ["County", "Registered Voters"] and head[2:] == ["Election Day", "Absentee", "Total"] * len(cands) + ["Total"], (title, head)
    rows, i = {}, i + 1
    while not lines[i].startswith("Total"):
        rows[norm(lines[i][:30])] = list(map(int, lines[i][30:].split())); i += 1
    totals = list(map(int, lines[i][30:].split()))
    detail[title] = (cands, rows, totals)
    i += 1
assert set(turnout) == set(by_name), "the report's counties differ from the Census's"
assert [turnout[norm(p)][1] for p in status["P"]] == status["B"], "ballots cast differ between the report and status.json"
assert sum(b for _, b in turnout.values()) == BALLOTS

# ---------- the site's other copies of the same results ----------
summary = {}
for r in csv.DictReader(io.StringIO((RAW / "results" / "summary-summary.csv").read_text(encoding="utf-8"))):
    summary.setdefault(r["contest name"].removesuffix(" (Vote For 1)"), []).append(r)
sum_json = {c["C"]: c for c in load("sum.json")["Contests"]}
summary_json = {c["C"]: c for c in load("summary.json")}
details_json = {c["K"]: c for c in load("details.json")["Contests"]}
all_json = {c["A"]: c for c in load("ALL.json")["Contests"]}
assert {c["K"]: c["V"] for c in sum_json.values()} == {c["K"]: c["V"] for c in summary_json.values()}, "summary.json and sum.json disagree on votes"

statewide = [t for t, rs in summary.items() if rs[0]["num Area total"] == str(COUNTIES)]
races, left_out, blank_write_ins = [], [], set()
for office in statewide:
    rs = summary[office]
    parties = [r["party name"] for r in rs]
    if parties.count("DEM") != 1 or parties.count("REP") != 1:
        left_out.append(office); continue
    assert office in RACES, (office, "a statewide contest between a Democrat and a Republican that isn't in RACES")
    assert all(r["num Area total"] == r["num Area rptg"] for r in rs), (office, "counties not all reporting")
    rid, label, group = RACES[office]
    cands, rows, totals = detail[office]
    assert cands == [r["choice name"] for r in rs], (office, "candidates differ between the two reports")
    assert set(rows) == set(by_name), (office, "a county is missing")
    n = len(cands)
    table = [[0, 0, 0, 0] for _ in counties]
    sums = [0] * n
    for key, nums in rows.items():
        if len(nums) == 3 * n and cands[-1] == "Write-in" and nums[-2] == 0:
            # Pottawattamie's write-in columns are blank, with a total of 0, here and as null in ALL.json. It counts as 0 write-ins;
            # the statewide write-in totals check below agrees with that. See docs/records/iowa.md.
            nums[-2:-1] = [0, 0, 0]
            blank_write_ins.add(by_name[key]["name"])
        assert len(nums) == 2 + 3 * n, (office, key, n, nums, cands)
        votes = [nums[1 + 3 * k + 2] for k in range(n)]
        for k in range(n):
            assert nums[1 + 3 * k] + nums[2 + 3 * k] == votes[k], (office, key, cands[k], "election day and absentee don't add up")
        assert sum(votes) == nums[-1], (office, key, "candidates don't add up to the county's total")
        assert nums[-1] <= turnout[key][1], (office, key, "more votes than ballots")
        assert nums[0] == turnout[key][0], (office, key, "registered voters differ")
        row = table[index[by_name[key]["fips"]]]
        for k, v in enumerate(votes):
            row[{"DEM": 0, "REP": 1}.get(parties[k], 2)] += v
            row[3] += v
            sums[k] += v
    assert sums == [int(r["total votes"]) for r in rs], (office, "counties don't add up to the Summary CSV")
    assert sums == [totals[3 + 3 * k] for k in range(n)] and sum(sums) == totals[-1], (office, "counties don't add up to the report's own totals")

    sj = sum_json[office]
    assert sj["TP"] == sj["PR"] == COUNTIES, (office, "sum.json: counties not all reporting")
    assert sj["CH"] == cands and sj["V"] == sums and sj["T"] == [sum(sums)], (office, "sum.json differs")
    dj = details_json[sj["K"]]
    assert dj["PX"] == dj["PY"] and sum(dj["PY"]) == PRECINCTS, (office, "details.json: precincts not all reporting")
    for pos, place in enumerate(dj["P"]):
        here = rows[norm(place)]
        want = [here[3 + 3 * k] for k in range(n)]
        assert [v or 0 for v in dj["V"][pos]] == want, (office, place, "details.json differs")
        cnty = all_json[place]; at = cnty["C"].index(sj["K"])
        assert [v or 0 for v in cnty["V"][at]] == want and cnty["T"][at] == here[-1], (office, place, "ALL.json differs")

    cs = []
    for k, r in sorted(enumerate(rs), key=lambda kr: -sums[kr[0]]):
        nm = r["choice name"]
        code = PARTY.get(r["party name"], "W" if nm == "Write-in" else r["party name"])
        assert code, (office, nm, "no party and not a write-in")
        cs.append(dict(name=nm, last=nm if code == "W" else last_name(nm), party=code, incumbent=False, votes=sums[k]))
    races.append(dict(id=rid, office=office, label=label, group=group, candidates=cs, counties=table))

assert sorted(r["office"] for r in races) == sorted(RACES), "statewide races differ from the RACES table"
order = list(RACES)
races.sort(key=lambda r: order.index(r["office"]))
for row in races[0]["counties"]:
    assert row[3] >= 10, "a county with under 10 U.S. Senate votes"
stale = sum(summary_json[t]["PR"] != summary_json[t]["TP"] for t in statewide)

link = lambda url, text: f'<a href="{url}" target="_blank" rel="noopener">{text}</a>'
out = dict(
    meta=dict(
        election="2026 General Election (Nov. 3, 2026)",
        resultsSource="Iowa Secretary of State, Election Results (unofficial results; state canvass pending)",
        resultsUrl=SITE_URL,
        resultsUpdated=UPDATED, retrieved=RETRIEVED,
        reporting=dict(counties=COUNTIES, countiesReporting=sum(s == COMPLETE for s in status["S"]), countiesCertified=CERTIFIED,
                       precincts=PRECINCTS, precinctsReporting=sum(status["PX"]), ballotsCast=BALLOTS),
        landSource="U.S. Census Bureau, 2020 Census Redistricting Data (P.L. 94-171), county land area (AREALAND)",
        countyRow="counties[i] = [Democratic votes, Republican votes, all other votes, total votes] for meta.counties[i]",
        sources=[
            f"Iowa Secretary of State, {link(SITE_URL, 'Election Results')}, Nov. 3, 2026 general election: unofficial results by county from the site's Detail TXT report, checked against its Summary CSV, as last updated {UPDATED}, retrieved {RETRIEVED}. {' and '.join(sorted(blank_write_ins))} County's write-in columns are blank in that report, so it counts here as no write-ins, as it does in the state's own totals.",
            f"U.S. Census Bureau, {link('https://www.census.gov/programs-surveys/decennial-census/about/rdo/summary-files.html', '2020 Census Redistricting Data')} (P.L. 94-171): county land area and codes, cities, and each block's location and adults, for placing dots within a county.",
            f"U.S. Census Bureau, {link('https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html', '2020 TIGER/Line&reg; Shapefiles')}, tabulation blocks: where people were counted, for keeping dots off empty land. TIGER/Line&reg; is a registered trademark of the Census Bureau. The land grid on this site is derived from those files, and it isn't a Census Bureau product or a TIGER/Line&reg; product.",
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
print(f"not statewide, left out: {len(summary) - len(statewide)} contests (U.S. House, legislature, county and district races)")
print(f"summary.json fields reading fewer counties than the Summary CSV: {stale} of {len(statewide)} statewide contests, with the same votes")
print("counties whose write-in columns are blank, counted as 0:", sorted(blank_write_ins))
assert blank_write_ins <= {"Pottawattamie"}, "a new county with blank write-in columns: look at it"
print(f"OK: {len(races)} races; {COUNTIES} counties, {PRECINCTS:,} precincts, all reporting; {CERTIFIED} counties marked certified; {BALLOTS:,} ballots; updated {UPDATED}, retrieved {RETRIEVED}.")
for r in races:
    d = next(c for c in r["candidates"] if c["party"] == "DEM"); p = next(c for c in r["candidates"] if c["party"] == "REP")
    print(f"  {r['id']:20} {d['name']} {d['votes']:,} vs {p['name']} {p['votes']:,}; total {sum(row[3] for row in r['counties']):,}; D carried {sum(row[0] > row[1] for row in r['counties'])} counties")

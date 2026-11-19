"""Build Texas's precincts by year, 2008 to 2024: each general election's own precinct lines and real precinct votes, from the
Texas Legislative Council, for the By precinct view and Dots (docs/texas-precincts-by-year-plan.md).

Sources (downloaded into data/raw/census-dl/tlc/years/, which is not committed; the URLs are in urls.txt there):
  * precinct lines (VTDs), Lambert conformal conic: lines-2010.zip to lines-2018.zip from archived_vtds_2010s,
    lines-2020.zip (VTDs20G_2020, on 2020 Census blocks) and lines-2022.zip (VTDs_22G) from vtds; 2024's is VTDs_24PG
    (data/raw/census-dl/tlc/vtds_24pg.zip, as in build_precincts.py)
  * precinct votes: votes-2010.zip to votes-2018.zip from historical_elections_2010s, votes-2020.zip to votes-2024.zip from
    comprehensive-election-datasets-compressed-format; each zip holds every general election re-tallied onto that year's lines
  * 2008 has no lines of its own: its votes are the Council's re-tally onto the 2010 lines, from votes-2010.zip
  * 2020 Census blocks (P.L. 94-171), as in build_precincts.py
All the Council's datasets are licensed Creative Commons Attribution (docs/PIPELINE.md, Part 5).

Writes, into data/tx-years/:
  * blocks.json.gz: every 2020 Census block with adults, by county, in GEOID order: { meta, counties: { fips: [dlon, dlat,
    radius, adults, ...] }, hot }; lon/lat in 1e-4 degrees, delta-encoded within the county; radius in 10 m units. hot is each
    county's most crowded spot, copied from data/precincts.json.gz (the same blocks, so the same answer).
  * <year>.json.gz: { meta, races: [race ids], counties: { fips: [[name, runs, votes, circle?], ...] } }, one entry per precinct
    with votes. name: its VTD code, or codes once merged. runs: which of the county's blocks are in it, as [gap, length, ...]
    (gap counted from the end of the run before). votes: [dem, rep, other] for each race in races, as counted. circle: only for
    a precinct with no block's center inside it, [lon, lat, radius] in the units above, where its dots go.
  * <year>-shapes.json.gz: the precincts' outlines, in the same order, in the format of data/precinct-shapes.json.gz.

The same rules as build_precincts.py: a block goes to the precinct of its county that contains its internal point (else the
nearest by center); a precinct with fewer than 10 votes in any statewide race is merged into the nearest precinct in its county,
smallest first; outlines are simplified along shared borders, so neighbors still meet. Votes are shown as the Council counted
them, not scaled to the Secretary of State's county totals (the owner's choice, 2026-11-19).

Checks that stop the build: every precinct with votes has lines; every vote is kept through merging; each statewide race's total
is within 0.5% of the Secretary of State's (data/results-history.json); TALLEST in state.js matches the tallest precinct here.

Run:  python scripts/build_tx_precinct_years.py [year ...]   (blocks.json.gz is written every time; years default to all)
"""
import csv
import gzip
import io
import json
import math
import re
import struct
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TLC = ROOT / "data" / "raw" / "census-dl" / "tlc"
Y = TLC / "years"
OUT = ROOT / "data" / "tx-years"
YEARS = [2008, 2010, 2012, 2014, 2016, 2018, 2020, 2022, 2024]
LINES = {2008: Y / "lines-2010.zip", 2010: Y / "lines-2010.zip", 2012: Y / "lines-2012.zip", 2014: Y / "lines-2014.zip",
         2016: Y / "lines-2016.zip", 2018: Y / "lines-2018.zip", 2020: Y / "lines-2020.zip", 2022: Y / "lines-2022.zip",
         2024: TLC / "vtds_24pg.zip"}
VOTES = {y: Y / f"votes-{2010 if y == 2008 else y}.zip" for y in YEARS}
LINES_NAME = {2008: "the 2010 general election's VTDs (VTD10G, archived_vtds_2010s)", 2010: "VTD10G (archived_vtds_2010s)",
              2012: "VTDs, 2012 general (archived_vtds_2010s)", 2014: "2014G_VTD (archived_vtds_2010s)",
              2016: "VTDs_2016G (archived_vtds_2010s)", 2018: "VTDs_2018G (archived_vtds_2010s)",
              2020: "VTDs20G_2020 (vtds, on 2020 Census blocks)", 2022: "VTDs_22G (vtds)", 2024: "VTDs_24PG (vtds)"}
VOTES_NAME = {y: ("historical_elections_2010s" if y <= 2018 else "comprehensive-election-datasets-compressed-format") for y in YEARS}
MIN_VOTES = 10
Q = 1e4
TOLERANCE = 5.0  # outline simplification, in 1e-4 degree steps (about 55 m), as in build_precincts.py
KX = math.cos(math.radians(31))

OFFICE = {"President": "president", "U.S. Sen": "u-s-senate", "Governor": "governor", "Lt. Governor": "lieutenant-governor",
          "Attorney Gen": "attorney-general"}
CHAMBER = [(re.compile(r"U\.S\. Rep \d+$"), "u-s-house"), (re.compile(r"State Rep \d+$"), "texas-house"),
           (re.compile(r"State Sen \d+$"), "texas-senate")]


def race_of(office):
    if office in OFFICE: return OFFICE[office]
    for rx, slug in CHAMBER:
        if rx.match(office): return slug
    return None


# ---------- the Lambert conformal conic of every Council line file, to lon/lat (as build_precincts.py) ----------
A, F_ = 6378137.0, 1 / 298.257222101
E = math.sqrt(2 * F_ - F_ * F_)
L0, P1, P2, PO = map(math.radians, (-100.0, 27.41666666666667, 34.91666666666666, 31.16666666666667))
FE, FN = 1_000_000.0, 1_000_000.0
m_ = lambda p: math.cos(p) / math.sqrt(1 - (E * math.sin(p)) ** 2)
t_ = lambda p: math.tan(math.pi / 4 - p / 2) / ((1 - E * math.sin(p)) / (1 + E * math.sin(p))) ** (E / 2)
N = (math.log(m_(P1)) - math.log(m_(P2))) / (math.log(t_(P1)) - math.log(t_(P2)))
FF = m_(P1) / (N * t_(P1) ** N)
RHO0 = A * FF * t_(PO) ** N


def inv(x, y):
    x, y = x - FE, RHO0 - (y - FN)
    rho = math.copysign(math.hypot(x, y), N)
    tt = (rho / (A * FF)) ** (1 / N)
    lam = math.atan2(x, y) / N + L0
    phi = math.pi / 2 - 2 * math.atan(tt)
    for _ in range(6):
        phi = math.pi / 2 - 2 * math.atan(tt * ((1 - E * math.sin(phi)) / (1 + E * math.sin(phi))) ** (E / 2))
    return math.degrees(lam), math.degrees(phi)


def inside(x, y, rings):
    c = False
    for r in rings:  # even-odd over every ring handles holes and multipart shapes
        j = len(r) - 1
        for k in range(len(r)):
            xi, yi = r[k]; xj, yj = r[j]
            if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi: c = not c
            j = k
    return c


def read_lines(path):
    """Each precinct's county, code and rings (lon/lat), and its area in square meters (in the projection, which keeps area close)."""
    z = zipfile.ZipFile(path)
    dbf = z.read(next(n for n in z.namelist() if n.lower().endswith(".dbf")))
    n, hlen, rlen = struct.unpack("<IHH", dbf[4:12])
    fields, off, s = {}, 32, 1
    while dbf[off] != 0x0D:
        name, ln = dbf[off:off + 11].split(b"\0")[0].decode(), dbf[off + 16]; fields[name] = (s, ln); s += ln; off += 32
    fld = lambda i, k: dbf[hlen + i * rlen + fields[k][0]: hlen + i * rlen + fields[k][0] + fields[k][1]].decode("latin-1").strip()
    shp = z.read(next(n for n in z.namelist() if n.lower().endswith(".shp")))
    out, pos, i = [], 100, 0
    while pos < len(shp):
        _, clen = struct.unpack(">II", shp[pos:pos + 8]); rec = shp[pos + 8: pos + 8 + clen * 2]; pos += 8 + clen * 2
        rings, area = [], 0.0
        if struct.unpack("<i", rec[:4])[0] == 5:
            nparts, npts = struct.unpack("<ii", rec[36:44])
            parts = struct.unpack(f"<{nparts}i", rec[44:44 + 4 * nparts])
            pts = struct.unpack(f"<{2 * npts}d", rec[44 + 4 * nparts: 44 + 4 * nparts + 16 * npts])
            for p in range(nparts):
                a, b = parts[p], parts[p + 1] if p + 1 < nparts else npts
                ring = [(pts[2 * k], pts[2 * k + 1]) for k in range(a, b)]
                area -= sum(ring[k - 1][0] * q[1] - q[0] * ring[k - 1][1] for k, q in enumerate(ring)) / 2  # clockwise = land
                rings.append([inv(x, y) for x, y in ring])
        out.append({"cnty": int(float(fld(i, "CNTY"))), "name": fld(i, "VTD"), "rings": rings, "areaM2": max(area, 1.0)})
        i += 1
    return out


def read_votes(year, races):
    """{(county, VTD code in capitals): {race id: [dem, rep, other]}} for the site's races of that year."""
    z = zipfile.ZipFile(VOTES[year])
    rows = csv.reader(io.TextIOWrapper(z.open(next(n for n in z.namelist() if n.endswith(f"{year}_General_Election_Returns.csv"))), encoding="latin-1"))
    head = [h.lower() for h in next(rows)]
    iF, iV, iO, iP, iN = head.index("fips"), head.index("vtd"), head.index("office"), head.index("party"), head.index("votes")
    out = defaultdict(lambda: defaultdict(lambda: [0, 0, 0]))
    for r in rows:
        if len(r) < len(head): continue
        slug = race_of(r[iO])
        rid = f"{year}-{slug}"
        if rid not in races: continue
        out[(int(r[iF]), r[iV].strip().upper())][rid][0 if r[iP] == "D" else 1 if r[iP] == "R" else 2] += int(r[iN])
    return out


# ---------- blocks: every 2020 Census block with adults, by county, in GEOID order ----------
pl = zipfile.ZipFile(TLC.parent / "pl" / "tx2020.pl.zip")
blk = {}
with pl.open("txgeo2020.pl") as f:
    for line in io.TextIOWrapper(f, encoding="latin-1"):
        r = line.rstrip("\n").split("|")
        if r[2] == "750": blk[r[7]] = [r[8].split("US")[1], float(r[-4]), float(r[-5]), float(r[-13]), 0]
with pl.open("tx000022020.pl") as f:
    for line in io.TextIOWrapper(f, encoding="latin-1"):
        r = line.split("|", 6); b = blk.get(r[4])
        if b: b[4] = int(r[5])
assert sum(b[4] for b in blk.values()) == 21_866_700
blocks_of = defaultdict(list)  # fips -> [(lon, lat, area, adults)], in GEOID order
for geoid, lon, lat, area, adults in sorted(b for b in blk.values() if b[4] > 0):
    blocks_of[geoid[:5]].append((lon, lat, area, adults))
print(f"{sum(map(len, blocks_of.values())):,} blocks with adults in {len(blocks_of)} counties")
OUT.mkdir(exist_ok=True)


def write(path, obj):
    path.write_bytes(gzip.compress(json.dumps(obj, separators=(",", ":")).encode("utf-8"), 9, mtime=0))
    print(f"  wrote {path.relative_to(ROOT)} ({path.stat().st_size / 1e6:.2f} MB)")


flat_blocks = {}
for fips, bs in blocks_of.items():
    flat, px, py = [], 0, 0
    for lon, lat, area, adults in bs:
        qx, qy = round(lon * Q), round(lat * Q)
        flat += [qx - px, qy - py, max(1, round(math.sqrt(area / math.pi) / 10)), adults]; px, py = qx, qy
    flat_blocks[fips] = flat
base = json.loads(gzip.decompress((ROOT / "data" / "precincts.json.gz").read_bytes()))
write(OUT / "blocks.json.gz", {
    "meta": {"source": "U.S. Census Bureau, 2020 Census Redistricting Data (P.L. 94-171): block internal points, land area, P3_001N (population 18 and over)",
             "format": "counties[fips] = [dlon, dlat, radius, adults, ...], every block with adults in GEOID order; lon/lat in 1e-4 degrees, "
                       "delta-encoded within the county (the first is absolute); radius in 10 m units. hot[fips] = [lon, lat, adults per "
                       "square mile within half a mile]: the county's most crowded spot."},
    "counties": flat_blocks, "hot": base["hot"]})
TALLEST_BASE = max(d + r + o for vs in base["counties"].values() for d, r, o, *_ in vs)

history = json.loads((ROOT / "data" / "results-history.json").read_text(encoding="utf-8"))
fips_order = [c["fips"] for c in json.loads((ROOT / "data" / "results-2026.json").read_text(encoding="utf-8"))["counties"]]
tallest = TALLEST_BASE


# ---------- outlines, simplified along shared borders (as build_precincts.py) ----------
def outlines(entries):
    def quantized(ring):
        pts = []
        for x, y in ring:
            p = (round(x * Q), round(y * Q))
            if not pts or pts[-1] != p: pts.append(p)
        if len(pts) > 1 and pts[0] == pts[-1]: pts.pop()
        return pts

    def peucker(arc):
        keep = [False] * len(arc); keep[0] = keep[-1] = True
        stack = [(0, len(arc) - 1)]
        while stack:
            a, b = stack.pop()
            if b - a < 2: continue
            ax, ay = arc[a][0] * KX, arc[a][1]
            dx, dy = arc[b][0] * KX - ax, arc[b][1] - ay
            len2 = dx * dx + dy * dy or 1
            far, at = -1, None
            for i in range(a + 1, b):
                px, py = arc[i][0] * KX - ax, arc[i][1] - ay
                s = max(0, min(1, (px * dx + py * dy) / len2))
                d = (px - s * dx) ** 2 + (py - s * dy) ** 2
                if d > far: far, at = d, i
            if far > TOLERANCE * TOLERANCE: keep[at] = True; stack += [(a, at), (at, b)]
        return [p for p, k in zip(arc, keep) if k]

    def simplify_arc(arc):
        if arc[0] != arc[-1]: return peucker(arc)
        far = max(range(len(arc)), key=lambda i: (arc[i][0] - arc[0][0]) ** 2 + (arc[i][1] - arc[0][1]) ** 2)
        if far == 0: return arc
        return peucker(arc[:far + 1])[:-1] + peucker(arc[far:])

    rings_of = {id(v): [r for r in map(quantized, v["rings"]) if len(r) >= 3] for vs in entries.values() for v in vs}
    neighbors = defaultdict(set)
    for rings in rings_of.values():
        for r in rings:
            for i, p in enumerate(r): neighbors[p].add(r[i - 1]); neighbors[r[i - 1]].add(p)
    junctions = {p for p, ns in neighbors.items() if len(ns) > 2}
    arcs = {}

    def simplified(arc):
        key = min(tuple(arc), tuple(reversed(arc)))
        if key not in arcs: arcs[key] = simplify_arc(list(key))
        return arcs[key] if tuple(arc) == key else arcs[key][::-1]

    def signed_area(r): return sum(r[i - 1][0] * p[1] - p[0] * r[i - 1][1] for i, p in enumerate(r)) / 2

    def simplify_ring(r):
        at = [i for i, p in enumerate(r) if p in junctions]
        if not at:
            k = r.index(min(r)); return simplified(r[k:] + r[:k] + [r[k]])[:-1]
        r = r[at[0]:] + r[:at[0]]
        at = [i - at[0] for i in at] + [len(r)]
        out, closed = [], r + [r[0]]
        for a, b in zip(at, at[1:]): out += simplified(closed[a:b + 1])[:-1]
        return out

    def to_polygons(rings):
        outers = [r for r in rings if signed_area(r) < 0]
        holes = [r for r in rings if signed_area(r) > 0]
        if not outers: outers, holes = holes, []
        polys = [[o] for o in outers]
        for h in holes:
            around = [p for p in polys if inside(h[0][0], h[0][1], [p[0]])]
            if around: min(around, key=lambda p: abs(signed_area(p[0]))).append(h)
        return polys

    def encode(r):
        out, px, py = [], 0, 0
        for x, y in r: out += [x - px, y - py]; px, py = x, y
        return out

    shapes = defaultdict(list)
    for fips, vs in entries.items():
        for v in vs:
            rings = rings_of[id(v)]
            small = [s for s in map(simplify_ring, rings) if len(s) >= 3 and signed_area(s) != 0] or rings
            shapes[fips].append([[encode(r) for r in poly] for poly in to_polygons(small)])
    return shapes


years = [int(a) for a in sys.argv[1:]] or YEARS
for year in years:
    print(f"\n== {year}: lines {LINES_NAME[year]}, votes {VOTES_NAME[year]}")
    site = {r["id"]: r for r in history["races"] if r["year"] == year}
    statewide = [rid for rid, r in site.items() if not r.get("chamber")]
    votes = read_votes(year, site)
    races = [rid for rid in site if any(rid in v for v in votes.values())]
    assert set(statewide) <= set(races), f"statewide races missing from the Council's file: {set(statewide) - set(races)}"
    vtds = read_lines(LINES[year])
    keys = [(v["cnty"], v["name"].upper()) for v in vtds]
    assert len(set(keys)) == len(keys), "two precincts with the same code, ignoring case"
    no_lines = set(votes) - set(keys)
    assert not no_lines, f"precincts with votes but no lines: {sorted(no_lines)[:10]}"
    for v, k in zip(vtds, keys):
        v["fips"] = f"48{v['cnty']:03d}"
        v["votes"] = {rid: list(votes[k][rid]) if k in votes and rid in votes[k] else [0, 0, 0] for rid in races}
    before = {rid: [sum(v["votes"][rid][j] for v in vtds) for j in range(3)] for rid in races}

    # each block to the precinct of its county that contains its internal point
    CELL = 0.05
    by_cnty = defaultdict(list)
    for v in vtds:
        xs = [p[0] for r in v["rings"] for p in r]; ys = [p[1] for r in v["rings"] for p in r]
        v["box"] = (min(xs), min(ys), max(xs), max(ys)) if xs else (0, 0, 0, 0)
        v["c"] = ((v["box"][0] + v["box"][2]) / 2, (v["box"][1] + v["box"][3]) / 2)
        v["blocks"] = []
        by_cnty[v["fips"]].append(v)
    nearest = 0
    for fips, bs in blocks_of.items():
        g = defaultdict(list)
        for v in by_cnty[fips]:
            x0, y0, x1, y1 = v["box"]
            for gx in range(int(x0 // CELL), int(x1 // CELL) + 1):
                for gy in range(int(y0 // CELL), int(y1 // CELL) + 1): g[(gx, gy)].append(v)
        for idx, (x, y, area, adults) in enumerate(bs):
            hit = next((v for v in g.get((int(x // CELL), int(y // CELL)), []) if v["box"][0] <= x <= v["box"][2]
                        and v["box"][1] <= y <= v["box"][3] and inside(x, y, v["rings"])), None)
            if hit is None:
                nearest += 1
                hit = min(by_cnty[fips], key=lambda v: (v["c"][0] - x) ** 2 + (v["c"][1] - y) ** 2)
            hit["blocks"].append(idx)
    print(f"  {len(vtds):,} precincts; blocks given to the nearest precinct instead of the one around them: {nearest}")

    # merge precincts with fewer than MIN_VOTES votes in any statewide race into the nearest in their county, smallest first
    size = lambda v: min(sum(v["votes"][rid]) for rid in statewide)
    alive = lambda v: any(sum(x) for x in v["votes"].values())
    merged = 0
    for fips, vs in by_cnty.items():
        live = [v for v in vs if alive(v)]
        for rid in statewide: assert sum(sum(v["votes"][rid]) for v in live) >= MIN_VOTES, (fips, rid)
        while True:
            small = min(live, key=size)
            if size(small) >= MIN_VOTES: break
            to = min((v for v in live if v is not small), key=lambda v: (v["c"][0] - small["c"][0]) ** 2 + (v["c"][1] - small["c"][1]) ** 2)
            merged += 1
            for rid in races: to["votes"][rid] = [a + b for a, b in zip(to["votes"][rid], small["votes"][rid])]
            to["blocks"] += small["blocks"]; to["name"] += ", " + small["name"]; to["rings"] = to["rings"] + small["rings"]
            to["areaM2"] += small["areaM2"]
            live.remove(small); small["votes"] = {rid: [0, 0, 0] for rid in races}
    after = {rid: [sum(v["votes"][rid][j] for v in vtds) for j in range(3)] for rid in races}
    assert after == before, "merging must keep every vote"
    print(f"  merged {merged} precincts under {MIN_VOTES} votes in a statewide race")

    # against the Secretary of State's totals on the site
    for rid in races:
        sos = [sum(row[j] for row in site[rid]["counties"]) for j in range(3)]
        gap = sum(abs(a - b) for a, b in zip(after[rid], sos)) / sum(sos)
        print(f"  {rid:28} Council {sum(after[rid]):>10,}  site {sum(sos):>10,}  gap {gap:.3%}")
        if rid in statewide: assert gap <= 0.005, f"{rid}: the Council's total is {gap:.2%} from the Secretary of State's"

    # write
    counties, entries = defaultdict(list), defaultdict(list)
    for v in vtds:
        if not alive(v): continue
        idx = sorted(v["blocks"])
        runs, prev, k = [], 0, 0
        while k < len(idx):
            start = idx[k]
            while k + 1 < len(idx) and idx[k + 1] == idx[k] + 1: k += 1
            runs += [start - prev, idx[k] - start + 1]; prev = idx[k] + 1; k += 1
        e = [v["name"], runs, [n for rid in races for n in v["votes"][rid]]]
        if not idx: e.append([round(v["c"][0] * Q), round(v["c"][1] * Q), max(1, round(math.sqrt(v["areaM2"] / math.pi) / 10))])
        counties[v["fips"]].append(e)
        entries[v["fips"]].append(v)
        tallest = max(tallest, *(sum(x) for x in v["votes"].values()))
    assert len(counties) == 254, len(counties)
    print(f"  precincts with no block's center inside (their dots go in one circle): {sum(1 for es in counties.values() for e in es if len(e) > 3)}")
    note = (" 2008 has no precinct lines of its own: these are the Council's re-tally of the 2008 votes onto the 2010 lines." if year == 2008 else "")
    write(OUT / f"{year}.json.gz", {
        "meta": {"election": f"{year} general election", "races": "each race's votes as counted by precinct: Democrat, Republican, all others (write-ins summed); "
                 "U.S. House, Texas House and Texas Senate add up each district's candidates by party, and leave out districts with one candidate" + note,
                 "votesSource": f"Texas Legislative Council, Capitol Data Portal, {VOTES_NAME[year]} ({VOTES[year].name}: {year}_General_Election_Returns.csv), Creative Commons Attribution",
                 "linesSource": f"Texas Legislative Council, {LINES_NAME[year]}, Creative Commons Attribution",
                 "merged": f"precincts with fewer than {MIN_VOTES} votes in any statewide race are merged into the nearest precinct in their county",
                 "format": "counties[fips] = [[name, runs, votes, circle?], ...]: runs = [gap, length, ...] into blocks.json.gz's list for the county; "
                           "votes = [dem, rep, other] for each race in races; circle = [lon, lat, radius] (1e-4 degrees, 10 m) only when no block is inside"},
        "races": races, "counties": counties})
    write(OUT / f"{year}-shapes.json.gz", {
        "meta": {"source": f"Texas Legislative Council, {LINES_NAME[year]}, Creative Commons Attribution; simplified along shared borders, merged precincts as in {year}.json.gz",
                 "format": "counties[fips] = one entry per precinct, in the order of <year>.json.gz: [[outer, hole...], ...]; a ring is [lon, lat, dlon, dlat, ...] in 1e-4 degrees, not closed."},
        "counties": outlines(entries)})

# one height scale for every year: the tallest precinct of any year and race, and of the 2024 Senate file the 2026 estimates use
if years == YEARS:
    print(f"\ntallest precinct, any year or race: {tallest:,} votes")
    found = re.search(r"tallest: (\d+)", (ROOT / "state.js").read_text(encoding="utf-8"))
    assert found and int(found.group(1)) == tallest, f"set precinctYears.tallest in state.js to {tallest}"

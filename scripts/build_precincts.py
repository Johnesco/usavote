"""Build data/precincts.json.gz: where each county's voters live and how each neighborhood votes, for the voter dot page;
and data/precinct-shapes.json.gz: the same precincts' outlines, for the precinct columns on the results page.

Results for 2026 are known by county only. Precinct (VTD) results for 2026 aren't published yet, so this uses the
pattern of the 2024 U.S. Senate race (Allred vs. Cruz) inside each county:

  * each county's 2026 votes for each party are shared among its 2024 voting districts (VTDs) in proportion to that
    party's 2024 votes there (done in the browser, so each county still adds up exactly to its 2026 result);
  * inside a VTD, its voters are shared among its census blocks in proportion to their population 18 and over, and
    placed at random within a circle the size of the block's land area;
  * a VTD with fewer than MIN_VOTES 2024 votes is merged into the nearest VTD in its county, votes and blocks together, so
    this file can't show how a handful of identifiable people voted.

Sources (downloaded into data/raw/census-dl/, which is not committed):
  * Texas Legislative Council, Capitol Data Portal, 2024 General Election, U.S. Senator, results by VTD:
    https://ted.capitol.texas.gov/api/Offices/510/2/vtd
  * Texas Legislative Council, VTDs_24PG (2024 primary and general election VTD boundaries):
    https://data.capitol.texas.gov/dataset/vtds
  * U.S. Census Bureau, 2020 Census Redistricting Data (P.L. 94-171), Texas: each block's internal point, land area and
    population 18 and over (P3_001N). Downloaded by scripts/build_blockgroups.py.

Output: { meta, counties: { fips: [[dem24, rep24, other24, blocks, name], ...] }, hot } with one entry per VTD; blocks is a flat
list [lon, lat, radius, adults, ...]: lon/lat in 1e-4 degree steps, delta-encoded within the VTD; radius in units of 10 m.
name: the VTD's code, for the "go to a precinct" menu; a merged VTD lists every code in it.
hot: each county's most crowded spot (adults per square mile within half a mile of a census block), for the close-ups.

precinct-shapes.json.gz: { meta, counties: { fips: [polygons, ...] } }, in the same order as precincts.json.gz. polygons is
[[outer, hole, ...], ...]; a ring is [lon, lat, dlon, dlat, ...] in 1e-4 degree steps, not closed. Neighbors share their
simplified borders exactly, so columns meet without gaps.

Oklahoma (python scripts/build_precincts.py ok) is county-only and writes one file, data/ok/blocks.json.gz, in the same
format. Each county is one unit holding all its census blocks, with its 2026 U.S. Senate votes from data/ok/results-2026.json
(run scripts/build_ok_results.py first). So its dots follow where adults live, with one party mix across the county. It uses
no precinct shapes: see docs/PIPELINE.md, Part 7.

Kansas (python scripts/build_precincts.py ks) writes both files into data/ks/, Texas's way, from IKE Lab's 2024 precinct file: its
2024 President votes and shapes. Run scripts/build_ks_results.py first. See docs/records/kansas.md.

South Carolina (python scripts/build_precincts.py sc) has precincts, like Texas, but 2026 votes on 2020 lines: Census 2020 voting
districts, with each district's 2026 U.S. Senate votes from data/raw/sc/derived/precinct-votes.json (run scripts/build_sc_results.py
first; docs/records/south-carolina.md). Writes data/sc/precincts.json.gz and data/sc/precinct-shapes.json.gz.

Run:  python scripts/build_precincts.py [ok|ks|sc]
"""
import csv
import io
import json
import math
import struct
import sys
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ST = sys.argv[1] if len(sys.argv) > 1 else "tx"
DL = ROOT / "data" / "raw" / "census-dl"
SEN_URL = "https://ted.capitol.texas.gov/api/Offices/510/2/vtd"
VTD_URL = ("https://data.capitol.texas.gov/dataset/4d8298d0-d176-4c19-b174-42837027b73e/resource/"
           "906f47e4-4e39-4156-b1bd-4969be0b2780/download/vtds_24pg.zip")
PL_ZIP = {"tx": DL / "pl" / "tx2020.pl.zip", "ok": ROOT / "data" / "raw" / "ok" / "census" / "ok2020.pl.zip", "ks": ROOT / "data" / "raw" / "ks" / "census" / "ks2020.pl.zip", "sc": ROOT / "data" / "raw" / "sc" / "census" / "sc2020.pl.zip"}[ST]
COUNTY_COUNT = {"tx": 254, "ok": 77, "ks": 105, "sc": 46}[ST]
MID_LAT = {"tx": 31, "ok": 35.5, "ks": 38.5, "sc": 33.6}[ST]  # for how much shorter a step of longitude is than a step of latitude
OUT_DIR = {"tx": ROOT / "data", "ok": ROOT / "data" / "ok", "ks": ROOT / "data" / "ks", "sc": ROOT / "data" / "sc"}[ST]
TX_ADULTS = 21_866_700
MIN_VOTES = 10  # a VTD with fewer 2024 votes than this is merged into its nearest neighbor
Q = 1e4


def fetch(url, path):
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        print("downloading", url)
        urllib.request.urlretrieve(url, path)
    return path


if ST == "ok":
    results = json.loads((OUT_DIR / "results-2026.json").read_text(encoding="utf-8"))
    senate = next(r for r in results["races"] if r["id"] == "u-s-senate")
    vtds = [{"fips": c["fips"], "name": c["name"], "votes": row[:3], "blocks": []} for c, row in zip(results["counties"], senate["counties"])]
    tot = [sum(v["votes"][k] for v in vtds) for k in range(3)]
    assert all(sum(v["votes"]) >= MIN_VOTES for v in vtds)
    print(f"{len(vtds)} counties; 2026 U.S. Senate: D {tot[0]:,}, R {tot[1]:,}, others {tot[2]:,}")
if ST == "sc":
    # ---------- 2026 U.S. Senate votes placed on 2020 VTDs (build_sc_results.py) and the VTDs' shapes (already lon/lat) ----------
    placed = json.loads((ROOT / "data" / "raw" / "sc" / "derived" / "precinct-votes.json").read_text(encoding="utf-8"))
    sen = {u["key"]: (u["name"], *u["votes"]) for u in placed["units"]}
    tot = [sum(v[k] for v in sen.values()) for k in (1, 2, 3)]
    print(f"{len(sen):,} units; 2026 Senate: D {tot[0]:,}, R {tot[1]:,}, others {tot[2]:,}")
    z = zipfile.ZipFile(ROOT / "data" / "raw" / "sc" / "census" / "tl_2020_45_vtd20.zip")
    dbf = z.read("tl_2020_45_vtd20.dbf")
    n, hlen, rlen = struct.unpack("<IHH", dbf[4:12])
    fields, off, s = {}, 32, 1
    while dbf[off] != 0x0D:
        name, ln = dbf[off:off + 11].split(b"\0")[0].decode(), dbf[off + 16]
        fields[name] = (s, ln); s += ln; off += 32
    fld = lambda i, name: dbf[hlen + i * rlen + fields[name][0]: hlen + i * rlen + fields[name][0] + fields[name][1]].decode("utf-8").strip()
    shp = z.read("tl_2020_45_vtd20.shp")
    shape_of, pos, i = {}, 100, 0
    while pos < len(shp):
        _, clen = struct.unpack(">II", shp[pos:pos + 8])
        rec = shp[pos + 8: pos + 8 + clen * 2]; pos += 8 + clen * 2
        assert struct.unpack("<i", rec[:4])[0] == 5
        nparts, npts = struct.unpack("<ii", rec[36:44])
        parts = struct.unpack(f"<{nparts}i", rec[44:44 + 4 * nparts])
        pts = struct.unpack(f"<{2 * npts}d", rec[44 + 4 * nparts: 44 + 4 * nparts + 16 * npts])
        rings = [[(pts[2 * k], pts[2 * k + 1]) for k in range(a, b)] for a, b in zip(parts, list(parts[1:]) + [npts])]
        shape_of[fld(i, "GEOID20")] = (rings, float(fld(i, "ALAND20")) + float(fld(i, "AWATER20")))
        i += 1
    # one entry per precinct, with all its districts; districts left off the map (under 10 adults, no 2026 row) keep their own, with no votes
    groups = [(u["key"], u["fips"], u["name"], u["vtds"]) for u in placed["units"]] + [(int(g), g[:5], "", [g]) for g in placed["empty"]]
    vtds = [{"key": k, "fips": f, "name": nm, "rings": [r for g in gs for r in shape_of[g][0]], "areaM2": sum(shape_of[g][1] for g in gs)} for k, f, nm, gs in groups]
    assert sum(len(g[3]) for g in groups) == len(shape_of), "every voting district goes on the map or is listed as left off"
    print(f"{len(vtds):,} VTD groups from {len(shape_of):,} VTD shapes")
if ST == "tx":
    # ---------- 2024 U.S. Senate votes by VTD ----------
    sen = {}
    with open(fetch(SEN_URL, DL / "tlc" / "sen24_vtd.json"), encoding="utf-8") as f:
        rows = csv.reader(f)
        head = next(rows)
        iD = next(i for i, h in enumerate(head) if h.startswith("AllredD"))
        iR = next(i for i, h in enumerate(head) if h.startswith("CruzR"))
        others = [i for i, h in enumerate(head) if "_24G_" in h and i not in (iD, iR)]
        for r in rows:
            key = int(r[1])
            sen[key] = (r[0], int(r[iD]), int(r[iR]), sum(int(r[i]) for i in others))
    tot = [sum(v[k] for v in sen.values()) for k in (1, 2, 3)]
    print(f"{len(sen):,} VTDs; 2024 Senate: Allred {tot[0]:,}, Cruz {tot[1]:,}, others {tot[2]:,}")

    # ---------- VTD shapes (Lambert conformal conic, meters) -> lon/lat ----------
    A, F_ = 6378137.0, 1 / 298.257222101
    E = math.sqrt(2 * F_ - F_ * F_)
    L0, P1, P2, PO, FE, FN = map(math.radians, (-100.0, 27.41666666666667, 34.91666666666666, 31.16666666666667, 0, 0))
    FE, FN = 1_000_000.0, 1_000_000.0
    m = lambda p: math.cos(p) / math.sqrt(1 - (E * math.sin(p)) ** 2)
    t = lambda p: math.tan(math.pi / 4 - p / 2) / ((1 - E * math.sin(p)) / (1 + E * math.sin(p))) ** (E / 2)
    N = (math.log(m(P1)) - math.log(m(P2))) / (math.log(t(P1)) - math.log(t(P2)))
    FF = m(P1) / (N * t(P1) ** N)
    RHO0 = A * FF * t(PO) ** N


    def inv(x, y):
        x, y = x - FE, RHO0 - (y - FN)
        rho = math.copysign(math.hypot(x, y), N)
        tt = (rho / (A * FF)) ** (1 / N)
        lam = math.atan2(x, y) / N + L0
        phi = math.pi / 2 - 2 * math.atan(tt)
        for _ in range(6):
            phi = math.pi / 2 - 2 * math.atan(tt * ((1 - E * math.sin(phi)) / (1 + E * math.sin(phi))) ** (E / 2))
        return math.degrees(lam), math.degrees(phi)


    z = zipfile.ZipFile(fetch(VTD_URL, DL / "tlc" / "vtds_24pg.zip"))
    dbf = z.read("VTDs_24PG.dbf")
    n, hlen, rlen = struct.unpack("<IHH", dbf[4:12])
    fields, off, s = {}, 32, 1
    while dbf[off] != 0x0D:
        name, ln = dbf[off:off + 11].split(b"\0")[0].decode(), dbf[off + 16]
        fields[name] = (s, ln); s += ln; off += 32
    fld = lambda i, name: dbf[hlen + i * rlen + fields[name][0]: hlen + i * rlen + fields[name][0] + fields[name][1]].decode().strip()
    shp = z.read("VTDs_24PG.shp")
    vtds, pos, i = [], 100, 0
    while pos < len(shp):
        _, clen = struct.unpack(">II", shp[pos:pos + 8])
        rec = shp[pos + 8: pos + 8 + clen * 2]; pos += 8 + clen * 2
        rings = []
        if struct.unpack("<i", rec[:4])[0] == 5:
            nparts, npts = struct.unpack("<ii", rec[36:44])
            parts = struct.unpack(f"<{nparts}i", rec[44:44 + 4 * nparts])
            pts = struct.unpack(f"<{2 * npts}d", rec[44 + 4 * nparts: 44 + 4 * nparts + 16 * npts])
            for p in range(nparts):
                a, b = parts[p], parts[p + 1] if p + 1 < nparts else npts
                rings.append([inv(pts[2 * k], pts[2 * k + 1]) for k in range(a, b)])
        key = int(float(fld(i, "VTDKEY")))
        cnty = int(fld(i, "CNTY"))
        vtds.append({"key": key, "fips": f"48{cnty:03d}", "rings": rings, "name": fld(i, "VTD"),
                     "areaM2": float(fld(i, "Shape_area"))})
        i += 1
    print(f"{len(vtds):,} VTD shapes")
    missing = set(sen) - {v["key"] for v in vtds}
    assert not missing, f"VTDs with votes but no shape: {sorted(missing)[:10]}"
if ST == "ks":
    # ---------- 2024 President by precinct and its shapes, from one file (IKE Lab), read like Texas's above ----------
    # scripts/build_ks_results.py checks these votes against the state's; run it first. Coordinates are Kansas North state plane:
    # Lambert conformal conic in U.S. survey feet.
    fips_of = {c["name"]: c["fips"] for c in json.loads((OUT_DIR / "results-2026.json").read_text(encoding="utf-8"))["counties"]}
    A, F_, FOOT = 6378137.0, 1 / 298.257222101, 0.3048006096012192
    E = math.sqrt(2 * F_ - F_ * F_)
    L0, P1, P2, PO = map(math.radians, (-98.0, 38.71666666666667, 39.78333333333333, 38.33333333333334))
    FE, FN = 1312333.333333333, 0.0
    m = lambda p: math.cos(p) / math.sqrt(1 - (E * math.sin(p)) ** 2)
    t = lambda p: math.tan(math.pi / 4 - p / 2) / ((1 - E * math.sin(p)) / (1 + E * math.sin(p))) ** (E / 2)
    N = (math.log(m(P1)) - math.log(m(P2))) / (math.log(t(P1)) - math.log(t(P2)))
    FF = m(P1) / (N * t(P1) ** N)
    RHO0 = A * FF * t(PO) ** N


    def inv(x, y):
        x, y = (x - FE) * FOOT, RHO0 - (y - FN) * FOOT
        rho = math.copysign(math.hypot(x, y), N)
        tt = (rho / (A * FF)) ** (1 / N)
        lam = math.atan2(x, y) / N + L0
        phi = math.pi / 2 - 2 * math.atan(tt)
        for _ in range(6):
            phi = math.pi / 2 - 2 * math.atan(tt * ((1 - E * math.sin(phi)) / (1 + E * math.sin(phi))) ** (E / 2))
        return math.degrees(lam), math.degrees(phi)


    z = zipfile.ZipFile(ROOT / "data" / "raw" / "ks" / "shapes" / "ks_2024g.zip")
    dbf = z.read("ks_2024g.dbf")
    n, hlen, rlen = struct.unpack("<IHH", dbf[4:12])
    fields, off, s = {}, 32, 1
    while dbf[off] != 0x0D:
        name, ln = dbf[off:off + 11].split(b"\0")[0].decode(), dbf[off + 16]
        fields[name] = (s, ln); s += ln; off += 32
    fld = lambda i, name: dbf[hlen + i * rlen + fields[name][0]: hlen + i * rlen + fields[name][0] + fields[name][1]].decode("latin-1").strip()
    shp = z.read("ks_2024g.shp")
    vtds, sen, pos, i = [], {}, 100, 0
    while pos < len(shp):
        _, clen = struct.unpack(">II", shp[pos:pos + 8])
        rec = shp[pos + 8: pos + 8 + clen * 2]; pos += 8 + clen * 2
        assert struct.unpack("<i", rec[:4])[0] == 15, "expected only polygons"  # with heights, which are after the points and unused
        nparts, npts = struct.unpack("<ii", rec[36:44])
        parts = struct.unpack(f"<{nparts}i", rec[44:44 + 4 * nparts])
        pts = struct.unpack(f"<{2 * npts}d", rec[44 + 4 * nparts: 44 + 4 * nparts + 16 * npts])
        rings = []
        area = 0.0
        for p in range(nparts):
            a, b = parts[p], parts[p + 1] if p + 1 < nparts else npts
            rings.append([inv(pts[2 * k], pts[2 * k + 1]) for k in range(a, b)])
            area -= sum(pts[2 * k] * pts[2 * k + 3] - pts[2 * k + 2] * pts[2 * k + 1] for k in range(a, b - 1)) / 2  # outer rings run clockwise
        county = fld(i, "coname")
        vtds.append({"key": i, "fips": fips_of[county], "rings": rings, "name": fld(i, "precinct").removeprefix(county + "-"), "areaM2": abs(area) * FOOT * FOOT})
        d, r, others = int(fld(i, "G24PREDHAR")), int(fld(i, "G24PRERTRU")), int(fld(i, "G24PRELOLI")) + int(fld(i, "G24PREIKEN"))
        sen[i] = (county, d, r, others)
        i += 1
    tot = [sum(v[k] for v in sen.values()) for k in (1, 2, 3)]
    print(f"{len(vtds):,} precinct shapes; 2024 President: Harris {tot[0]:,}, Trump {tot[1]:,}, others {tot[2]:,}")

# ---------- census blocks: internal point, land area, adults ----------
pl = zipfile.ZipFile(PL_ZIP)
blk = {}
state_rec, state_adults = None, None
with pl.open(f"{ST}geo2020.pl") as f:
    for line in io.TextIOWrapper(f, encoding="latin-1"):
        r = line.rstrip("\n").split("|")
        if r[2] == "750":
            # from the end: AREALAND, AREAWATR, BASENAME, NAME, FUNCSTAT, GCUNI, POP100, HU100, INTPTLAT, INTPTLON, LSADC, PARTFLAG, UGA
            blk[r[7]] = [r[8].split("US")[1][:5], float(r[-4]), float(r[-5]), float(r[-13]), 0]
        elif r[2] == "040" and r[3] == "00" and r[4] == "00":
            state_rec = r[7]
with pl.open(f"{ST}000022020.pl") as f:
    for line in io.TextIOWrapper(f, encoding="latin-1"):
        r = line.split("|", 6)
        b = blk.get(r[4])
        if b: b[4] = int(r[5])
        elif r[4] == state_rec: state_adults = int(r[5])
blocks = [b for b in blk.values() if b[4] > 0]
# the file's own count for the whole state; Texas's was also written down when it was first built
assert sum(b[4] for b in blk.values()) == state_adults, (sum(b[4] for b in blk.values()), state_adults)
assert ST != "tx" or state_adults == TX_ADULTS
print(f"{len(blk):,} blocks, {len(blocks):,} with adults; {state_adults:,} adults in the state")
if ST == "ok":  # each block to its county, from its own code
    of_county = {v["fips"]: v for v in vtds}
    for b in blocks: of_county[b[0]]["blocks"].append(b)
    assert all(v["blocks"] for v in vtds), "a county with no adults"


# ---------- each block to the VTD that contains its internal point ----------
def inside(x, y, rings):
    c = False
    for r in rings:  # even-odd over every ring handles holes and multipart shapes
        j = len(r) - 1
        for k in range(len(r)):
            xi, yi = r[k]; xj, yj = r[j]
            if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
                c = not c
            j = k
    return c


if ST in ("tx", "ks", "sc"):
    CELL = 0.05
    by_cnty = defaultdict(list)
    for v in vtds:
        xs = [p[0] for r in v["rings"] for p in r]; ys = [p[1] for r in v["rings"] for p in r]
        if not xs: continue
        v["box"] = (min(xs), min(ys), max(xs), max(ys))
        v["c"] = ((v["box"][0] + v["box"][2]) / 2, (v["box"][1] + v["box"][3]) / 2)
        v["blocks"] = []
        by_cnty[v["fips"]].append(v)
    grid = {}
    for fips, vs in by_cnty.items():
        g = defaultdict(list)
        for v in vs:
            x0, y0, x1, y1 = v["box"]
            for gx in range(int(x0 // CELL), int(x1 // CELL) + 1):
                for gy in range(int(y0 // CELL), int(y1 // CELL) + 1):
                    g[(gx, gy)].append(v)
        grid[fips] = g
    unplaced = 0
    for b in blocks:
        fips, x, y = b[0], b[1], b[2]
        cand = grid.get(fips, {}).get((int(x // CELL), int(y // CELL)), [])
        hit = next((v for v in cand if v["box"][0] <= x <= v["box"][2] and v["box"][1] <= y <= v["box"][3] and inside(x, y, v["rings"])), None)
        if hit is None:  # on an edge or a sliver gap: the VTD in the same county with the nearest center
            unplaced += 1
            hit = min(by_cnty[fips], key=lambda v: (v["c"][0] - x) ** 2 + (v["c"][1] - y) ** 2)
        hit["blocks"].append(b)
    print(f"blocks matched by nearest VTD instead of containment: {unplaced:,}")

    # ---------- merge VTDs with very few votes into the nearest VTD in the county, smallest first ----------
    for v in vtds:
        v["votes"] = list(sen[v["key"]][1:]) if v["key"] in sen and "blocks" in v else [0, 0, 0]
    merged = merged_votes = moved_adults = 0
    for fips, vs in by_cnty.items():
        live = [v for v in vs if sum(v["votes"]) > 0]
        assert sum(sum(v["votes"]) for v in live) >= MIN_VOTES, fips
        while True:
            small = min(live, key=lambda v: sum(v["votes"]))
            if sum(small["votes"]) >= MIN_VOTES: break
            to = min((v for v in live if v is not small), key=lambda v: (v["c"][0] - small["c"][0]) ** 2 + (v["c"][1] - small["c"][1]) ** 2)
            merged += 1; merged_votes += sum(small["votes"]); moved_adults += sum(b[4] for b in small["blocks"])
            to["votes"] = [a + b for a, b in zip(to["votes"], small["votes"])]
            to["blocks"] += small["blocks"]
            to["name"] += ", " + small["name"]
            to["rings"] = to["rings"] + small["rings"]
            live.remove(small); small["votes"] = [0, 0, 0]
    print(f"merged {merged} VTDs under {MIN_VOTES} votes ({merged_votes:,} votes, {moved_adults:,} adults in their blocks)")
    assert [sum(v["votes"][k] for v in vtds) for k in range(3)] == tot, "merging must keep every vote"

# ---------- write ----------
counties, no_blocks = defaultdict(list), 0
entries = defaultdict(list)  # the VTDs written, in file order, for the shapes file
for v in vtds:
    d, r, o = v["votes"]
    if d + r + o == 0: continue
    bl = v["blocks"]
    if not bl:  # votes but no adults on record: one circle the size of the VTD at its center
        no_blocks += 1
        bl = [[v["fips"], v["c"][0], v["c"][1], v["areaM2"], 1]]
    flat, px, py = [], 0, 0
    for _, x, y, area, adults in bl:
        qx, qy = round(x * Q), round(y * Q)
        flat += [qx - px, qy - py, max(1, round(math.sqrt(area / math.pi) / 10)), adults]
        px, py = qx, qy
    counties[v["fips"]].append([d, r, o, flat, v["name"]])
    entries[v["fips"]].append(v)
assert len(counties) == COUNTY_COUNT, len(counties)
print(f"VTDs with votes but no adults on record (placed as one circle): {no_blocks}")

# ---------- each county's most crowded spot: adults per square mile within HOT_R miles of a block ----------
HOT_R, HC = 0.5, 0.01  # radius (miles); grid cell (degrees, about 0.6-0.7 miles)
hot = {}
blocks_by_cnty = defaultdict(list)
for b in blocks: blocks_by_cnty[b[0]].append(b)
for fips, bs in blocks_by_cnty.items():
    g = defaultdict(list)
    for b in bs: g[(int(b[1] // HC), int(b[2] // HC))].append(b)
    best = None
    for b in bs:
        x, y, kx = b[1], b[2], 69.05 * math.cos(math.radians(b[2]))
        gx, gy, s = int(x // HC), int(y // HC), 0
        for i in (-1, 0, 1):
            for j in (-1, 0, 1):
                for o in g.get((gx + i, gy + j), ()):
                    if ((o[1] - x) * kx) ** 2 + ((o[2] - y) * 69.05) ** 2 <= HOT_R ** 2: s += o[4]
        if best is None or s > best[2]: best = (x, y, s)
    hot[fips] = [round(best[0], 4), round(best[1], 4), round(best[2] / (math.pi * HOT_R ** 2))]
FORMAT = ("counties[fips] = [[dem24, rep24, other24, blocks, name]...], one per VTD (name: its VTD code or codes); blocks = [dlon, dlat, radius, adults, ...]: "
          "lon/lat in 1e-4 degrees, delta-encoded within the VTD (the first is absolute); radius in 10 m units. "
          "hot[fips] = [lon, lat, adults per square mile within half a mile]: the county's most crowded spot.")
out = {
    "meta": {
        "race": "2024 general election, U.S. Senator (Allred D, Cruz R; others = all other candidates), by VTD",
        "resultsSource": "Texas Legislative Council, Capitol Data Portal, 2024 General Election, U.S. Senator by VTD",
        "resultsUrl": SEN_URL,
        "shapesSource": "Texas Legislative Council, VTDs_24PG (2024 VTD boundaries)",
        "shapesUrl": "https://data.capitol.texas.gov/dataset/vtds",
        "blocksSource": "U.S. Census Bureau, 2020 Census Redistricting Data (P.L. 94-171): block internal points, land area, P3_001N",
        "merged": f"VTDs with fewer than {MIN_VOTES} votes are merged into the nearest VTD in their county",
        "format": FORMAT,
        "totals2024": {"dem": tot[0], "rep": tot[1], "other": tot[2]},
    } if ST == "tx" else {
        "race": "2026 general election, U.S. Senator (others = all other candidates), on 2020 voting districts; some precincts combined and some votes shared out by rule (docs/records/south-carolina.md)",
        "resultsSource": "South Carolina State Election Commission, Election Night Reporting, county precinct files",
        "resultsUrl": "https://www.enr-scvotes.org/SC/127300/web.345435/#/summary",
        "shapesSource": "U.S. Census Bureau, 2020 TIGER/Line Shapefiles, voting districts. TIGER/Line is a registered trademark of the Census Bureau; this file is not a Census Bureau product.",
        "shapesUrl": "https://www2.census.gov/geo/tiger/TIGER2020PL/STATE/45_SOUTH_CAROLINA/45/tl_2020_45_vtd20.zip",
        "blocksSource": "U.S. Census Bureau, 2020 Census Redistricting Data (P.L. 94-171): block internal points, land area, P3_001N",
        "merged": f"Districts with fewer than {MIN_VOTES} votes are merged into the nearest district in their county",
        "format": FORMAT.replace("dem24, rep24, other24", "dem, rep, other").replace("its VTD code or codes", "its 2026 precinct name or names"),
        "totals": {"dem": tot[0], "rep": tot[1], "other": tot[2]},
    } if ST == "sc" else {
        "race": "2026 general election, U.S. Senator (others = all other candidates), by county",
        "resultsSource": "Oklahoma State Election Board, OK Election Results, county file",
        "resultsUrl": "https://results.okelections.gov/OKER/?elecDate=20261103",
        "blocksSource": "U.S. Census Bureau, 2020 Census Redistricting Data (P.L. 94-171): block internal points, land area, P3_001N",
        "format": FORMAT.replace("dem24, rep24, other24", "dem, rep, other").replace("one per VTD (name: its VTD code or codes)", "one entry, the whole county (name: the county)").replace("within the VTD", "within the county"),
        "totals": {"dem": tot[0], "rep": tot[1], "other": tot[2]},
    },
    "counties": counties,
    "hot": hot,
}
if ST == "ks":
    out["meta"] = {
        "race": "2024 general election, President (Harris D, Trump R; others = Oliver, Kennedy), by precinct",
        "resultsSource": "IKE Lab, Wichita State University, Precinct Result Shapefiles, 2024 General (checked against the Kansas Secretary of State's 2024 totals)",
        "resultsUrl": "https://ike-lab.com/files/ks_2024g.zip",
        "shapesSource": "IKE Lab, ks_2024g (2024 precincts), CC-BY: https://creativecommons.org/licenses/by/4.0/",
        "shapesUrl": "https://ike-lab.com/electionresults.html",
        "blocksSource": "U.S. Census Bureau, 2020 Census Redistricting Data (P.L. 94-171): block internal points, land area, P3_001N",
        "merged": f"Precincts with fewer than {MIN_VOTES} votes are merged into the nearest precinct in their county; precincts with no votes are left out",
        "format": FORMAT,
        "totals2024": {"dem": tot[0], "rep": tot[1], "other": tot[2]},
    }
# gzipped (mtime 0, so a rebuild with the same data gives the same file); dots.js unzips it in the browser
import gzip
path = OUT_DIR / ("blocks.json.gz" if ST == "ok" else "precincts.json.gz")
path.write_bytes(gzip.compress(json.dumps(out, separators=(",", ":")).encode("utf-8"), 9, mtime=0))
print(f"wrote {path} ({path.stat().st_size / 1e6:.1f} MB)")
if ST == "ok": sys.exit()  # no precinct outlines


# ---------- precinct outlines: simplified along shared borders, so neighbors still meet ----------
TOLERANCE = 5.0  # simplification, in 1e-4 degree steps (about 55 m)
KX = math.cos(math.radians(MID_LAT))  # a step of longitude is shorter than a step of latitude


def quantized(ring):
    pts = []
    for x, y in ring:
        p = (round(x * Q), round(y * Q))
        if not pts or pts[-1] != p: pts.append(p)
    if len(pts) > 1 and pts[0] == pts[-1]: pts.pop()
    return pts


def peucker(arc):
    """Douglas-Peucker, for an arc whose two ends differ."""
    keep = [False] * len(arc)
    keep[0] = keep[-1] = True
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
        if far > TOLERANCE * TOLERANCE:
            keep[at] = True
            stack += [(a, at), (at, b)]
    return [p for p, k in zip(arc, keep) if k]


def simplify_arc(arc):
    if arc[0] != arc[-1]: return peucker(arc)
    # a loop: split at the point farthest from its start
    far = max(range(len(arc)), key=lambda i: (arc[i][0] - arc[0][0]) ** 2 + (arc[i][1] - arc[0][1]) ** 2)
    if far == 0: return arc
    return peucker(arc[:far + 1])[:-1] + peucker(arc[far:])


rings_of = {id(v): [r for r in map(quantized, v["rings"]) if len(r) >= 3] for vs in entries.values() for v in vs}
neighbors = defaultdict(set)
for rings in rings_of.values():
    for r in rings:
        for i, p in enumerate(r):
            neighbors[p].add(r[i - 1]); neighbors[r[i - 1]].add(p)
junctions = {p for p, ns in neighbors.items() if len(ns) > 2}
arcs = {}


def simplified(arc):
    key = min(tuple(arc), tuple(reversed(arc)))
    if key not in arcs: arcs[key] = simplify_arc(list(key))
    return arcs[key] if tuple(arc) == key else arcs[key][::-1]


def signed_area(r):
    return sum(r[i - 1][0] * p[1] - p[0] * r[i - 1][1] for i, p in enumerate(r)) / 2


def simplify_ring(r):
    at = [i for i, p in enumerate(r) if p in junctions]
    if not at:  # no neighbor changes along it: start where anyone drawing this loop would start
        k = r.index(min(r))
        return simplified(r[k:] + r[:k] + [r[k]])[:-1]
    r = r[at[0]:] + r[:at[0]]
    at = [i - at[0] for i in at] + [len(r)]
    out, closed = [], r + [r[0]]
    for a, b in zip(at, at[1:]):
        out += simplified(closed[a:b + 1])[:-1]
    return out


def to_polygons(rings):
    """Rings run clockwise around land and counterclockwise around holes; each hole goes with the smallest ring around it."""
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
    for x, y in r:
        out += [x - px, y - py]
        px, py = x, y
    return out


shapes, n_points, kept_whole = defaultdict(list), 0, 0
for fips, vs in entries.items():
    for v in vs:
        rings = rings_of[id(v)]
        small = [s for s in map(simplify_ring, rings) if len(s) >= 3 and signed_area(s) != 0]
        if not small:  # too small to survive simplifying: keep it as drawn
            small = rings; kept_whole += 1
        n_points += sum(len(s) for s in small)
        shapes[fips].append([[encode(r) for r in poly] for poly in to_polygons(small)])
assert {f: len(s) for f, s in shapes.items()} == {f: len(c) for f, c in counties.items()}, "shapes must line up with precincts"
print(f"{sum(map(len, shapes.values())):,} precinct outlines, {n_points:,} points, {len(arcs):,} border pieces; kept as drawn: {kept_whole}")
path = OUT_DIR / "precinct-shapes.json.gz"
path.write_bytes(gzip.compress(json.dumps({
    "meta": {
        "source": "U.S. Census Bureau, 2020 TIGER/Line Shapefiles, voting districts, simplified along shared borders; combined and merged precincts as in precincts.json.gz. TIGER/Line is a registered trademark of the Census Bureau; this file is not a Census Bureau product.",
        "url": "https://www2.census.gov/geo/tiger/TIGER2020PL/STATE/45_SOUTH_CAROLINA/45/tl_2020_45_vtd20.zip",
        "format": "counties[fips] = one entry per precinct, in the order of precincts.json.gz: [[outer, hole...], ...]; a ring is [lon, lat, dlon, dlat, ...] in 1e-4 degrees, not closed.",
    } if ST == "sc" else {
        "source": "Texas Legislative Council, VTDs_24PG (2024 VTD boundaries), simplified along shared borders; merged precincts as in precincts.json.gz" if ST == "tx" else "IKE Lab, ks_2024g (2024 precincts, CC-BY), simplified along shared borders; merged precincts as in precincts.json.gz",
        "url": "https://data.capitol.texas.gov/dataset/vtds" if ST == "tx" else "https://ike-lab.com/electionresults.html",
        "format": "counties[fips] = one entry per precinct, in the order of precincts.json.gz: [[outer, hole...], ...]; a ring is [lon, lat, dlon, dlat, ...] in 1e-4 degrees, not closed.",
    },
    "counties": shapes,
}, separators=(",", ":")).encode("utf-8"), 9, mtime=0))
print(f"wrote {path} ({path.stat().st_size / 1e6:.2f} MB)")

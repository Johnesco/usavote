"""Build data/districts/<race>.json.gz: the outlines of Texas's U.S. House, Texas House and Texas Senate districts, for the
By district view on the results page (app.js).

Sources (saved under data/raw/census-dl/tlc/districts/, which is not committed), all from the Texas Legislative Council's
Capitol Data Portal:
  * PLANC2333, U.S. House districts for the 2026 elections:  https://data.capitol.texas.gov/dataset/planc2333
  * PLANH2316, Texas House districts for 2022 to 2026:       https://data.capitol.texas.gov/dataset/planh2316
  * PLANS2168, Texas Senate districts for 2022 to 2026:      https://data.capitol.texas.gov/dataset/plans2168
The House and Senate datasets are listed as Creative Commons Attribution. PLANC2333 shows no license; the owner chose on
2026-11-12 to publish its outlines with credit (docs/PIPELINE.md, Part 9).

Output, one file per chamber: { meta, districts: { "1": [[outer, hole, ...], ...], ... } }. A ring is
[lon, lat, dlon, dlat, ...] in 1e-4 degree steps, not closed: the format of precinct-shapes.json.gz. Borders are simplified to
about 55 m along the pieces neighbors share, so districts still meet without gaps.

Checks that stop the build: each file has exactly the chamber's districts, numbered 1 to its size in data/results-2026.json;
and no district loses all its shape in simplifying. As a check that these are the lines the results were counted on, each
district's counties are worked out from the 2024 precincts whose centers fall inside it, and the build stops unless every
district reaches every county the 2026 county feed reports results from. A district may also reach a county that reports
nothing for it, where its piece of the county has no voters or a precinct's center falls just across the line; the build prints
how many do and stops if any district has more than one such county.

Run:  python scripts/build_districts.py   (after scripts/build_data.py)

Other states (python scripts/build_districts.py ok, or several codes, or "all") get data/<state>/districts/u-s-house.json.gz, in
the same format, from two Census Bureau files of the 119th Congress's districts. The outlines drawn are from the national 2024
Cartographic Boundary File (data/raw/census-dl/cb/cb_2024_us_cd119_500k.zip), which stops at the shoreline. The check uses the
state's 2024 TIGER/Line file (data/raw/<state>/census/tl_2024_<code>_cd119.zip), which is exact but runs out over water. Run the
state's results script first. The check: every census block with people is placed in a district by its inside point, and the
build stops unless each district's results came only from counties where its people live, and unless it has no more than a few
people in any other county. This needs numpy. Ohio isn't here: its 2026 districts are newer than these files, and the check
says so (district 1 has results from Clinton County, which the Census file's district 1 doesn't reach).
"""
import base64
import gzip
import json
import math
import re
import struct
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "census-dl" / "tlc"
OUT_DIR = ROOT / "data" / "districts"
PORTAL = "https://data.capitol.texas.gov/dataset/"
CC_BY = {"license": "Creative Commons Attribution, as listed by the Council", "licenseUrl": "http://www.opendefinition.org/licenses/cc-by"}
PLANS = [  # race id in the results files, plan, what the Council calls it, the general elections held on it, license
    ("u-s-house", "PLANC2333", "U.S. House districts for the 2026 elections", [2026], {"license": None, "licenseUrl": None}),
    ("texas-house", "PLANH2316", "Texas House districts for the 2022 to 2026 elections", [2022, 2024, 2026], CC_BY),
    ("texas-senate", "PLANS2168", "Texas Senate districts for the 2022 to 2026 elections", [2022, 2024, 2026], CC_BY),
]
Q = 1e4
TOLERANCE = 5.0  # simplification, in 1e-4 degree steps (about 55 m)
KX = math.cos(math.radians(31))  # a step of longitude is shorter than a step of latitude

# ---------- Lambert conformal conic, meters (the same projection as VTDs_24PG) -> lon/lat ----------
A, F_ = 6378137.0, 1 / 298.257222101
E = math.sqrt(2 * F_ - F_ * F_)
L0, P1, P2, PO = map(math.radians, (-100.0, 27.41666666666667, 34.91666666666666, 31.16666666666667))
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


def read_shapes(z, stem, want):
    """[(the wanted fields, rings in the file's own coordinates)] for each polygon record."""
    dbf = z.read(stem + ".dbf")
    n, hlen, rlen = struct.unpack("<IHH", dbf[4:12])
    fields, off, s = {}, 32, 1
    while dbf[off] != 0x0D:
        name, ln = dbf[off:off + 11].split(b"\0")[0].decode(), dbf[off + 16]
        fields[name] = (s, ln); s += ln; off += 32
    fld = lambda i, name: dbf[hlen + i * rlen + fields[name][0]: hlen + i * rlen + fields[name][0] + fields[name][1]].decode().strip()
    shp = z.read(stem + ".shp")
    out, pos, i = [], 100, 0
    while pos < len(shp):
        _, clen = struct.unpack(">II", shp[pos:pos + 8])
        rec = shp[pos + 8: pos + 8 + clen * 2]; pos += 8 + clen * 2
        rings = []
        if struct.unpack("<i", rec[:4])[0] == 5:
            nparts, npts = struct.unpack("<ii", rec[36:44])
            parts = struct.unpack(f"<{nparts}i", rec[44:44 + 4 * nparts])
            pts = struct.unpack(f"<{2 * npts}d", rec[44 + 4 * nparts: 44 + 4 * nparts + 16 * npts])
            rings = [[(pts[2 * k], pts[2 * k + 1]) for k in range(a, b)] for a, b in zip(parts, list(parts[1:]) + [npts])]
        out.append(([fld(i, w) for w in want], rings))
        i += 1
    assert i == n, (stem, i, n)
    return out


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


def signed_area(r):
    return sum(r[i - 1][0] * p[1] - p[0] * r[i - 1][1] for i, p in enumerate(r)) / 2


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


def simplify_all(rings_of):
    """rings_of: {district: [ring, ...]} in 1e-4 degree steps. The same, simplified along the pieces neighbors share."""
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

    out = {}
    for d, rings in rings_of.items():
        out[d] = [s for s in map(simplify_ring, rings) if len(s) >= 3 and signed_area(s) != 0]
        assert out[d], f"district {d} lost its shape"
    return out, len(arcs)


# ---------- another state: U.S. House districts from the Census Bureau, checked against the state's census blocks ----------
STATES = {  # state: (Census code, a middle latitude, size of its U.S. House delegation)
    "ok": ("40", 35.5, 5), "oh": ("39", 40.2, 15), "ia": ("19", 42, 4), "id": ("16", 45.5, 2), "ga": ("13", 32.7, 14),
    "ri": ("44", 41.6, 2), "sc": ("45", 33.6, 7), "nm": ("35", 34.2, 3),
}
CB_STEM = "cb_2024_us_cd119_500k"  # the national file, clipped to the shoreline; a state's TIGER/Line file runs out over water
CB = "U.S. Census Bureau, 2024 Cartographic Boundary Files, 119th Congressional Districts (1:500,000)"
TRADEMARK = "Checked against the Bureau's 2024 TIGER/Line Shapefiles. TIGER/Line is a registered trademark of the Census Bureau; this file is not a Census Bureau product."
_cb = []


def cb_shapes(fips):
    """The state's districts in the national cartographic file: {number: [ring, ...]}."""
    if not _cb: _cb.extend(read_shapes(zipfile.ZipFile(ROOT / "data" / "raw" / "census-dl" / "cb" / f"{CB_STEM}.zip"), CB_STEM, ["STATEFP", "CD119FP"]))
    out = {}
    for (state, num), rings in _cb:
        if state != fips or num == "ZZ": continue
        assert int(num) not in out, f"{fips}: district {num} twice in the cartographic file"
        out[int(num)] = [q for q in map(quantized, rings) if len(q) >= 3]
    return out


def census_state(st):
    import numpy as np
    global KX
    fips, mid_lat, size = STATES[st]
    KX = math.cos(math.radians(mid_lat))
    results = json.loads((ROOT / "data" / st / "results-2026.json").read_text(encoding="utf-8"))
    race = next(r for r in results["races"] if r["id"] == "u-s-house")
    assert race["size"] == size, (st, race["size"])
    stem = f"tl_2024_{fips}_cd119"
    raw_points, rings_of = 0, {}
    for (num,), rings in read_shapes(zipfile.ZipFile(ROOT / "data" / "raw" / st / "census" / f"{stem}.zip"), stem, ["CD119FP"]):
        if num == "ZZ": continue  # water that belongs to no district
        raw_points += sum(map(len, rings))
        assert int(num) not in rings_of, f"{st}: district {num} twice"
        rings_of[int(num)] = [q for q in map(quantized, rings) if len(q) >= 3]
    assert sorted(rings_of) == list(range(1, size + 1)), f"{st}: districts {sorted(rings_of)} for a delegation of {size}"
    # what's drawn: the same districts from the cartographic file, which stops at the shoreline as the page's county shapes do
    drawn = cb_shapes(fips)
    assert sorted(drawn) == sorted(rings_of), f"{st}: the cartographic file has districts {sorted(drawn)}"
    drawn_points = sum(len(r) for rs in drawn.values() for r in rs)
    small, n_arcs = simplify_all(drawn)
    polys = {d: to_polygons(rings) for d, rings in small.items()}

    # Each census block with people, by its inside point: its county and the district it falls in (on the outlines as published by
    # the Census Bureau, before simplifying). Blocks nest inside districts, so this is each district's counties, with their people.
    cnty, xs, ys, pop = [], [], [], []
    with zipfile.ZipFile(ROOT / "data" / "raw" / st / "census" / f"{st}2020.pl.zip").open(f"{st}geo2020.pl") as f:
        for line in f:
            r = line.decode("latin-1").rstrip("\n").split("|")
            if r[2] == "750" and int(r[-7]) > 0:  # from the end: ... POP100, HU100, INTPTLAT, INTPTLON, LSADC, PARTFLAG, UGA
                cnty.append(r[8].split("US")[1][:5]); xs.append(float(r[-4]) * Q); ys.append(float(r[-5]) * Q); pop.append(int(r[-7]))
    xs, ys, pop = np.array(xs), np.array(ys), np.array(pop)
    row_of = {c["fips"]: i for i, c in enumerate(results["counties"])}
    rows = np.array([row_of[c] for c in cnty])
    people, placed = {}, np.zeros(len(xs), bool)
    for d, rings in rings_of.items():
        ring_x = np.array([p[0] for r in rings for p in r]); ring_y = np.array([p[1] for r in rings for p in r])
        near = np.flatnonzero((xs >= ring_x.min()) & (xs <= ring_x.max()) & (ys >= ring_y.min()) & (ys <= ring_y.max()))
        near = near[np.argsort(ys[near], kind="stable")]  # by latitude, so each edge looks only at the blocks level with it
        x, y, odd = xs[near], ys[near], np.zeros(len(near), bool)
        for r in rings:  # even-odd over every ring handles holes and multipart shapes
            for (xi, yi), (xj, yj) in zip(r, r[1:] + r[:1]):
                if yi == yj: continue
                a, b = np.searchsorted(y, (min(yi, yj), max(yi, yj)))  # the blocks with min <= y < max: those the edge passes beside
                if a < b: odd[a:b] ^= x[a:b] < (xj - xi) * (y[a:b] - yi) / (yj - yi) + xi
        assert not placed[near[odd]].any(), f"{st}: a block falls in two districts"
        placed[near[odd]] = True
        people[d] = {int(i): int(pop[near[odd]][rows[near[odd]] == i].sum()) for i in set(rows[near[odd]].tolist())}
    assert placed.sum() >= 0.999 * len(xs), f"{st}: {len(xs) - placed.sum():,} blocks with people fall in no district"

    # every county a district's results came from must be one where its people live; the other way round, a county with a few
    # people and no results for the district is printed, and one with many stops the build
    name = [c["name"] for c in results["counties"]]
    notes = []
    for d in race["districts"]:
        here = people[d["district"]]
        missing = set(d["where"]) - set(here)
        assert not missing, f"{st}: district {d['district']} has results from counties its shape doesn't reach: {[name[i] for i in missing]}"
        for i in sorted(set(here) - set(d["where"])):
            assert here[i] < 100, f"{st}: district {d['district']}'s shape holds {here[i]:,} people in {name[i]} County, which has no results for it"
            notes.append(f"district {d['district']}: {here[i]} people in {name[i]}")
    assert {d["district"] for d in race["districts"]} == set(rings_of), f"{st}: the results don't have every district"
    print(f"{st}: {size} districts, {drawn_points:,} points -> {sum(len(r) for rs in small.values() for r in rs):,} in {n_arcs:,} border pieces ({raw_points:,} in the TIGER/Line file used for the check); "
          f"{int(placed.sum()):,} of {len(xs):,} blocks with people placed; every district's people live in exactly the counties its results came from"
          + (f", but for: {'; '.join(notes)}" if notes else ""))

    path = ROOT / "data" / st / "districts" / "u-s-house.json.gz"
    path.parent.mkdir(exist_ok=True)
    path.write_bytes(gzip.compress(json.dumps({
        "meta": {
            "plan": "CD119", "what": "U.S. House districts of the 119th Congress", "years": [2026],
            "source": f"{CB}, simplified along shared borders. {TRADEMARK}",
            "url": f"https://www2.census.gov/geo/tiger/GENZ2024/shp/{CB_STEM}.zip", "license": None, "licenseUrl": None,
            "checkedAgainst": f"https://www2.census.gov/geo/tiger/TIGER2024/CD/{stem}.zip",
            "format": "districts[number] = [[outer, hole...], ...]; a ring is [lon, lat, dlon, dlat, ...] in 1e-4 degrees, not closed.",
        },
        "districts": {str(d): [[encode(r) for r in poly] for poly in polys[d]] for d in sorted(polys)},
    }, separators=(",", ":")).encode("utf-8"), 9, mtime=0))
    print(f"wrote {path} ({path.stat().st_size / 1e3:.0f} KB)")


if len(sys.argv) > 1:
    for st in (list(STATES) if sys.argv[1] == "all" else sys.argv[1:]): census_state(st)
    sys.exit()

# ---------- the 2026 county feed (which counties each district's results came from) and the 2024 precincts (each one's
# county and center), to check that these are the lines the results were counted on ----------
results = json.loads((ROOT / "data" / "results-2026.json").read_text(encoding="utf-8"))
norm = lambda s: re.sub(r"[^A-Z]", "", s.upper())
sos = json.loads(base64.b64decode(json.loads((ROOT / "data" / "raw" / "sos-countyInfo-53815.json").read_text())["upload"]))
county_code = {norm(c["name"]): int(c["fips"][2:]) for c in results["counties"]}
OFFICE = {"u-s-house": "U. S. REPRESENTATIVE DISTRICT ", "texas-house": "STATE REPRESENTATIVE DISTRICT ", "texas-senate": "STATE SENATOR, DISTRICT "}
vtd_at = []
for (cnty,), rings in read_shapes(zipfile.ZipFile(RAW / "vtds_24pg.zip"), "VTDs_24PG", ["CNTY"]):
    big = max(rings, key=len, default=None)
    if not big: continue
    lon, lat = inv(sum(p[0] for p in big) / len(big), sum(p[1] for p in big) / len(big))
    vtd_at.append((int(cnty), lon * Q, lat * Q))
print(f"{len(vtd_at):,} precinct centers")

OUT_DIR.mkdir(exist_ok=True)
for race_id, plan, what, years, lic in PLANS:
    race = next(r for r in results["races"] if r["id"] == race_id)
    z = zipfile.ZipFile(RAW / "districts" / f"{plan.lower()}.zip")
    raw_points, rings_of = 0, {}
    for (num,), rings in read_shapes(z, f"{plan}/{plan}", ["District"]):
        raw_points += sum(map(len, rings))
        assert int(num) not in rings_of, f"{plan}: district {num} twice"
        rings_of[int(num)] = [q for q in (quantized([inv(x, y) for x, y in r]) for r in rings) if len(q) >= 3]
    assert sorted(rings_of) == list(range(1, race["size"] + 1)), f"{plan}: districts {sorted(rings_of)} for a chamber of {race['size']}"
    small, n_arcs = simplify_all(rings_of)
    polys = {d: to_polygons(rings) for d, rings in small.items()}

    # the counties each district reaches, from the precincts whose centers are inside it, against its 2026 results
    boxes = {d: (min(p[0] for r in rs for p in r), min(p[1] for r in rs for p in r), max(p[0] for r in rs for p in r), max(p[1] for r in rs for p in r))
             for d, rs in small.items()}
    reach, unplaced = defaultdict(set), 0
    for cnty, x, y in vtd_at:
        for d, (x0, y0, x1, y1) in boxes.items():
            if x0 <= x <= x1 and y0 <= y <= y1 and inside(x, y, small[d]):
                reach[d].add(cnty); break
        else: unplaced += 1
    extra, n_checked = [], 0
    for d in race["districts"]:
        office = OFFICE[race_id] + str(d["district"])
        counted = {county_code[norm(c["N"])] for c in sos.values() if any(r["N"].strip() == office for r in c["Races"].values())}
        if not counted: continue  # a single candidate, so not on the ballot
        n_checked += 1
        missing = counted - reach[d["district"]]
        assert not missing, f"{plan}: district {d['district']} has results from counties its shape doesn't reach: {sorted(missing)}"
        more = reach[d["district"]] - counted
        assert len(more) <= 1, f"{plan}: district {d['district']} reaches {len(more)} counties with no results for it"
        if more: extra.append(d["district"])
    print(f"{plan}: {len(rings_of)} districts, {raw_points:,} points -> {sum(len(r) for rs in small.values() for r in rs):,} in {n_arcs:,} border pieces; "
          f"all {n_checked} districts on the 2026 ballot reach every county their results came from; "
          f"{len(extra)} also hold the center of a precinct in one more county; precinct centers in no district: {unplaced}")

    path = OUT_DIR / f"{race_id}.json.gz"
    path.write_bytes(gzip.compress(json.dumps({
        "meta": {
            "plan": plan, "what": what, "years": years,
            "source": f"Texas Legislative Council, {plan} ({what}), simplified along shared borders",
            "url": PORTAL + plan.lower(), **lic,
            "format": "districts[number] = [[outer, hole...], ...]; a ring is [lon, lat, dlon, dlat, ...] in 1e-4 degrees, not closed.",
        },
        "districts": {str(d): [[encode(r) for r in poly] for poly in polys[d]] for d in sorted(polys)},
    }, separators=(",", ":")).encode("utf-8"), 9, mtime=0))
    print(f"wrote {path} ({path.stat().st_size / 1e3:.0f} KB)")

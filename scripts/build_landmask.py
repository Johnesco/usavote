"""Build data/landmask.bin.gz: a grid over Texas of where the 2020 Census counted anyone, so the voter dots stay off empty land.

A cell is "lived on" if any part of it falls in a census block with people or housing units. Everything else (blocks the
Census counted no one in, such as lakes, bays, airports, big parks and rail yards, and everywhere outside Texas) is empty.
dots-worker.js gives a dot a new spot in its own block's neighborhood when it lands on an empty cell. It's a coarse grid of
land, not of homes: it says nothing about where any person lives inside a block.

The grid is in the site's own projection (d3.geoConicEqualArea, parallels 27.5 and 35, rotated 99.5, unscaled), so
a straight scale and shift turns map units into grid cells; the two anchors in the header give dots.js that scale and shift.

Source (downloaded into data/raw/census-dl/tiger/, which is not committed; about 750 MB):
  U.S. Census Bureau, 2020 TIGER/Line Shapefiles, 2020 Census tabulation blocks, Texas (POP20, HOUSING20):
  https://www2.census.gov/geo/tiger/TIGER2020/TABBLOCK20/tl_2020_48_tabblock20.zip

Output, gzipped: uint32 (little-endian) header length, JSON header { w, h, cellMeters, a, b, source }, where a and b are
[lon, lat, grid x, grid y], then for each row a list of LEB128 run lengths, in cells, adding up to w: first empty, then lived
on, taking turns. Runs compress far better than one bit per cell.

Oklahoma (python scripts/build_landmask.py ok) gets the same grid in its own projection, written to data/ok/, and South Carolina
(sc) to data/sc/. The values here must match state.js.

Kansas: python scripts/build_landmask.py ks, into data/ks/.

Ohio (oh) likewise, written to data/oh/.

Oklahoma (python scripts/build_landmask.py ok) and Iowa (ia) get the same grid in their own projections, written to data/ok/
and data/ia/. The values here must match state.js.

Run:  python scripts/build_landmask.py [ok|ks|sc|oh|ia]
"""
import gzip
import io
import json
import math
import struct
import sys
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

Image.MAX_IMAGE_PIXELS = None

ROOT = Path(__file__).resolve().parent.parent
ST = sys.argv[1] if len(sys.argv) > 1 else "tx"
NAME, FIPS, FOLDER, OUT, P1, P2, ROT = {
    "tx": ("Texas", "48", "census-dl/tiger", "data/landmask.bin.gz", 27.5, 35, 99.5),
    "ok": ("Oklahoma", "40", "ok/census", "data/ok/landmask.bin.gz", 34.2, 36.4, 98.7),
    "ks": ("Kansas", "20", "ks/census", "data/ks/landmask.bin.gz", 37.5, 39.5, 98.3),
    "sc": ("South Carolina", "45", "sc/census", "data/sc/landmask.bin.gz", 32.5, 34.7, 80.9),
    "oh": ("Ohio", "39", "oh/census", "data/oh/landmask.bin.gz", 39, 41.4, 82.7),
    "ia": ("Iowa", "19", "ia/census", "data/ia/landmask.bin.gz", 40.9, 43, 93.4),
}[ST]
ZIP = ROOT / "data" / "raw" / FOLDER / f"tl_2020_{FIPS}_tabblock20.zip"
URL = f"https://www2.census.gov/geo/tiger/TIGER2020/TABBLOCK20/tl_2020_{FIPS}_tabblock20.zip"
CELL_M = 100          # meters per cell
R = 6371008.8         # sphere radius behind "meters" here; only the cell size depends on it
CELL = CELL_M / R     # cell size in the unscaled projection's units

# d3.geoConicEqualArea, unscaled, y up
s0 = math.sin(math.radians(P1))
N = (s0 + math.sin(math.radians(P2))) / 2
C = 1 + s0 * (2 * N - s0)
R0 = math.sqrt(C) / N


def project(lon, lat):
    lam, phi = np.radians(np.asarray(lon) + ROT), np.radians(np.asarray(lat))
    r = np.sqrt(C - 2 * N * np.sin(phi)) / N
    return r * np.sin(lam * N), R0 - r * np.cos(lam * N)


if not ZIP.exists():
    ZIP.parent.mkdir(parents=True, exist_ok=True)
    print("downloading", URL)
    urllib.request.urlretrieve(URL, ZIP)
z = zipfile.ZipFile(ZIP)
shp_name = next(n for n in z.namelist() if n.endswith(".shp"))
dbf_name = next(n for n in z.namelist() if n.endswith(".dbf"))

# the grid: Texas's bounding box from the shapefile's header, projected along its edges, with a margin
with z.open(shp_name) as f:
    head = f.read(100)
lon0, lat0, lon1, lat1 = struct.unpack("<4d", head[36:68])
edge = np.linspace(0, 1, 200)
ex = np.concatenate([lon0 + (lon1 - lon0) * edge, lon0 + (lon1 - lon0) * edge, np.full(200, lon0), np.full(200, lon1)])
ey = np.concatenate([np.full(200, lat0), np.full(200, lat1), lat0 + (lat1 - lat0) * edge, lat0 + (lat1 - lat0) * edge])
px, py = project(ex, ey)
X0, X1, Y0, Y1 = px.min() - 5 * CELL, px.max() + 5 * CELL, py.min() - 5 * CELL, py.max() + 5 * CELL
W, H = math.ceil((X1 - X0) / CELL), math.ceil((Y1 - Y0) / CELL)
print(f"grid {W:,} x {H:,} cells of {CELL_M} m")

simple = Image.new("1", (W, H), 0)
draw = ImageDraw.Draw(simple)
holed = []  # blocks with holes: another block sits inside them, so these are drawn apart, biggest first


def signed_area(x, y):
    return 0.5 * float(np.dot(x[:-1], y[1:]) - np.dot(x[1:], y[:-1]))


blocks = lived = 0
with z.open(dbf_name) as d, z.open(shp_name) as s:
    d = io.BufferedReader(d, 1 << 20)
    s = io.BufferedReader(s, 1 << 20)
    h = d.read(32)
    count, hlen, rlen = struct.unpack("<IHH", h[4:12])
    rest = d.read(hlen - 32)
    fields, off, pos = {}, 0, 1
    while rest[off] != 0x0D:
        name, ln = rest[off:off + 11].split(b"\0")[0].decode(), rest[off + 16]
        fields[name] = (pos, ln); pos += ln; off += 32
    fp, fh = fields["POP20"], fields["HOUSING20"]
    s.read(100)
    for _ in range(count):
        row = d.read(rlen)
        _, clen = struct.unpack(">II", s.read(8))
        rec = s.read(clen * 2)
        blocks += 1
        if not (int(row[fp[0]:fp[0] + fp[1]]) > 0 or int(row[fh[0]:fh[0] + fh[1]]) > 0):
            continue
        if struct.unpack("<i", rec[:4])[0] != 5:
            continue
        lived += 1
        nparts, npts = struct.unpack("<ii", rec[36:44])
        parts = np.frombuffer(rec, "<i4", nparts, 44)
        pts = np.frombuffer(rec, "<f8", npts * 2, 44 + 4 * nparts).reshape(-1, 2)
        x, y = project(pts[:, 0], pts[:, 1])
        gx, gy = (x - X0) / CELL, (Y1 - y) / CELL
        rings = [(gx[a:b], gy[a:b]) for a, b in zip(parts, list(parts[1:]) + [npts])]
        areas = [signed_area(*r) for r in rings]
        # one direction is an outer ring and the other a hole (the outer ring is the largest)
        sign = math.copysign(1, areas[int(np.argmax(np.abs(areas)))])
        if all(a * sign > 0 for a in areas):
            for rx, ry in rings:
                draw.polygon(np.column_stack([rx, ry]).ravel().tolist(), fill=1, outline=1)
        else:
            holed.append((abs(sum(areas)), [(a * sign > 0, np.column_stack(r).ravel().tolist()) for a, r in zip(areas, rings)]))
print(f"{blocks:,} blocks, {lived:,} with people or housing, {len(holed):,} of those with holes")

over = Image.new("1", (W, H), 0)
draw = ImageDraw.Draw(over)
for _, rings in sorted(holed, key=lambda b: -b[0]):
    for outer, xy in sorted(rings, key=lambda r: not r[0]):  # outer rings, then holes
        draw.polygon(xy, fill=1 if outer else 0, outline=1 if outer else None)
grid = np.asarray(simple, dtype=bool) | np.asarray(over, dtype=bool)
print(f"{grid.mean():.1%} of the grid's box is lived on: {grid.sum() * (CELL_M / 1000) ** 2:,.0f} square km")


def varint(n, out):
    while n >= 128:
        out.append(n & 127 | 128); n >>= 7
    out.append(n)


def encode(g):
    out = bytearray()
    for row in g:
        change = np.flatnonzero(row[1:] != row[:-1]) + 1
        ends = np.concatenate([change, [len(row)]])
        runs = np.diff(np.concatenate([[0], ends]))
        if row[0]:
            varint(0, out)  # rows start with an empty run
        for r in runs.tolist():
            varint(r, out)
    return bytes(out)


def header():
    # two points well apart, in lon/lat and in the grid, by inverting the projection
    def inv(x, y):
        rho = math.hypot(x, R0 - y)
        lam = math.atan2(x, R0 - y) / N
        return math.degrees(lam) - ROT, math.degrees(math.asin((C - (rho * N) ** 2) / (2 * N)))
    anchor = lambda gx, gy: [*inv(X0 + gx * CELL, Y1 - gy * CELL), gx, gy]
    return {"w": W, "h": H, "cellMeters": CELL_M, "a": anchor(W * 0.1, H * 0.1), "b": anchor(W * 0.9, H * 0.9),
            "source": f"U.S. Census Bureau, 2020 TIGER/Line tabulation blocks, {NAME} (POP20, HOUSING20)"
            + ("; reworked into this grid, which isn't a Census Bureau product. TIGER/Line is a registered trademark of the Census Bureau." if ST == "oh" else "")}


path = ROOT / OUT
path.parent.mkdir(parents=True, exist_ok=True)
head = json.dumps(header(), separators=(",", ":")).encode()
path.write_bytes(gzip.compress(struct.pack("<I", len(head)) + head + encode(grid), 9, mtime=0))
print(f"wrote {path}: {W:,} x {H:,}, {path.stat().st_size / 1e6:.2f} MB")



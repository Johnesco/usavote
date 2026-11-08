"""Build a 4K (3840 x 2160) infographic of the 2026 U.S. Senate race: the main page's county-by-county map side by side
with the one-dot-per-voter map, with legends and sources.

The dots are placed the way the site places them (dots-worker.js): each party's 2026 county total is shared among the 2024
voting districts in proportion to that party's 2024 Senate votes there, then among each district's census blocks by
adults, by systematic rounding so every county adds up exactly; each dot is then scattered around its block with a bell
curve (one standard deviation = 0.75 of the block's radius, cut off at 2.5), and kept off land where the 2020 Census
counted no one (data/landmask.bin.gz). Where several voters share a pixel, the pixel
takes their average party color, brighter the more voters there are.

Inputs: data/results-2026.json, data/precincts.json.gz, data/landmask.bin.gz, and the us-atlas county boundaries the site draws
(downloaded into data/raw/us-atlas/, not committed).
Run:  python scripts/build_infographic.py [scale]   (scale 1 = 4K, the default; 2 = 8K; 4 = 16K)
      writes texas-senate-2026-two-maps-4k.png (or -8k, -16k)
The layout is designed at 3840 x 2160 and every coordinate, line and font is multiplied by the scale; the maps are drawn
at the full output resolution, so a larger scale shows finer detail, not just bigger pixels.
"""
import gzip
import json
import math
import sys
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
K = int(sys.argv[1]) if len(sys.argv) > 1 else 1  # output scale
OUT = ROOT / f"texas-senate-2026-two-maps-{4 * K}k.png"
W, H = 3840, 2160
BG = (14, 17, 22)
SEED = 2026

# ---------- data ----------
res = json.loads((ROOT / "data/results-2026.json").read_text(encoding="utf-8"))
race = next(r for r in res["races"] if r["id"] == "u-s-senate")
counties = []
for meta, (dem, rep, other, total) in zip(res["counties"], race["counties"]):
    counties.append({**meta, "dem": dem, "rep": rep, "other": other, "total": total})
by_fips = {c["fips"]: c for c in counties}
cand = {c["party"]: c for c in race["candidates"]}
D, R = cand["DEM"], cand["REP"]
TOT = sum(c["total"] for c in counties)
OTH = TOT - D["votes"] - R["votes"]
pc = json.loads(gzip.decompress((ROOT / "data/precincts.json.gz").read_bytes()))

atlas_path = ROOT / "data/raw/us-atlas/counties-10m.json"
if not atlas_path.exists():
    atlas_path.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve("https://cdn.jsdelivr.net/npm/us-atlas@3.0.1/counties-10m.json", atlas_path)
topo = json.loads(atlas_path.read_text(encoding="utf-8"))

# ---------- projection: spherical Albers equal-area conic, as the site's d3.geoConicEqualArea ----------
P1, P2, LON0 = math.radians(27.5), math.radians(35), -99.5
N = (math.sin(P1) + math.sin(P2)) / 2
C = math.cos(P1) ** 2 + 2 * N * math.sin(P1)
RE = 6371008.8  # meters


def project(lon, lat):
    """lon/lat in degrees (arrays) -> x east, y north, in meters."""
    lam = np.radians(np.asarray(lon, float) - LON0)
    phi = np.radians(np.asarray(lat, float))
    rho = np.sqrt(C - 2 * N * np.sin(phi)) / N
    return RE * rho * np.sin(N * lam), RE * (math.sqrt(C) / N - rho * np.cos(N * lam))


# ---------- where the Census counted anyone (scripts/build_landmask.py), one True per lived-on cell ----------
_b = gzip.decompress((ROOT / "data/landmask.bin.gz").read_bytes())
_n = int.from_bytes(_b[:4], "little")
_h = json.loads(_b[4:4 + _n])
LW, LH = _h["w"], _h["h"]
land = np.zeros((LH, LW), bool)
_p = 4 + _n
for _y in range(LH):
    _x, _on = 0, False
    while _x < LW:
        _v, _s = 0, 0
        while True:
            _c = _b[_p]; _p += 1
            _v |= (_c & 127) << _s; _s += 7
            if _c < 128:
                break
        if _on:
            land[_y, _x:_x + _v] = True
        _x += _v; _on = not _on
_ax, _ay = project(_h["a"][0], _h["a"][1])
_bx, _by = project(_h["b"][0], _h["b"][1])
_sx, _sy = (_h["b"][2] - _h["a"][2]) / (_bx - _ax), (_h["b"][3] - _h["a"][3]) / (_by - _ay)


def lived(x, y):
    """x, y in meters (arrays) -> True where the land grid says the Census counted anyone."""
    gx = np.floor(_h["a"][2] + (x - _ax) * _sx).astype(np.int64)
    gy = np.floor(_h["a"][3] + (y - _ay) * _sy).astype(np.int64)
    ok = (gx >= 0) & (gx < LW) & (gy >= 0) & (gy < LH)
    out = np.zeros(len(x), bool)
    out[ok] = land[gy[ok], gx[ok]]
    return out


# ---------- county shapes from TopoJSON ----------
tf = topo["transform"]
arcs = []
for arc in topo["arcs"]:
    a = np.cumsum(np.array(arc, float), axis=0)
    arcs.append(a * tf["scale"] + tf["translate"])


def ring(idx):
    pts = []
    for i in idx:
        a = arcs[i] if i >= 0 else arcs[~i][::-1]
        pts.extend(a[1:] if pts else a)
    return np.array(pts)


shapes = {}  # fips -> list of polygons, each a list of rings (lon/lat arrays)
for g in topo["objects"]["counties"]["geometries"]:
    fips = str(g.get("id", ""))
    if not fips.startswith("48") or fips not in by_fips:
        continue
    polys = [g["arcs"]] if g["type"] == "Polygon" else g["arcs"]
    shapes[fips] = [[ring(r) for r in p] for p in polys]
assert len(shapes) == 254, len(shapes)

# ---------- layout ----------
MAP_W, MAP_H = 1760, 1500
LEFT_X, RIGHT_X, MAP_Y = 120, 1960, 360
allx, ally = [], []
for polys in shapes.values():
    for p in polys:
        x, y = project(p[0][:, 0], p[0][:, 1]); allx.append(x); ally.append(y)
allx, ally = np.concatenate(allx), np.concatenate(ally)
X0, X1, Y0, Y1 = allx.min(), allx.max(), ally.min(), ally.max()
SCALE = min(MAP_W / (X1 - X0), MAP_H / (Y1 - Y0))  # pixels per meter
OFF_X = (MAP_W - (X1 - X0) * SCALE) / 2
OFF_Y = (MAP_H - (Y1 - Y0) * SCALE) / 2


def to_px(x, y, ss=1):
    """projected meters -> pixel coordinates inside a map panel, at ss times the resolution"""
    return (OFF_X + (x - X0) * SCALE) * ss * K, (OFF_Y + (Y1 - y) * SCALE) * ss * K


# ---------- left: county by county (the main page's colors) ----------
BINS = [40, 50, 60, 70, 80, 90]
REP_C = ['#ffb2b2', '#e27f7f', '#d75d5d', '#d72f30', '#c21b18', '#a80000']
DEM_C = ['#a5b0ff', '#7996e2', '#6674de', '#584cde', '#3933e5', '#0d0596']


def county_color(c):
    share = 100 * max(c["dem"], c["rep"]) / c["total"]
    i = max([0] + [k for k, b in enumerate(BINS) if share >= b])
    return (DEM_C if c["dem"] > c["rep"] else REP_C)[i]


PW, PH = MAP_W * K, MAP_H * K  # a map panel's size in output pixels
SS = max(1, round(3 / K))  # supersampling for smooth edges (less needed, and too big, at large scales)
LINE = max(1, round(SS * K / 2))  # county outline width at the supersampled size
left = Image.new("RGB", (PW * SS, PH * SS), BG)
ld = ImageDraw.Draw(left)
for fips, polys in shapes.items():
    col = county_color(by_fips[fips])
    for p in polys:
        for k, r in enumerate(p):
            x, y = to_px(*project(r[:, 0], r[:, 1]), SS)
            ld.polygon(list(zip(x, y)), fill=col if k == 0 else BG)
for polys in shapes.values():  # thin outlines on top, as on the site
    for p in polys:
        for r in p:
            x, y = to_px(*project(r[:, 0], r[:, 1]), SS)
            ld.line(list(zip(x, y)) + [(x[0], y[0])], fill=(14, 17, 22), width=LINE)
if SS > 1:
    left = left.resize((PW, PH), Image.LANCZOS)

# ---------- right: one dot per voter ----------
rng = np.random.default_rng(SEED)
xs, ys, parties = [], [], []
for fips, vtds in pc["counties"].items():
    c = by_fips[fips]
    bx, by, brad, bad, vid = [], [], [], [], []
    vd, vr, vo, vad = [], [], [], []
    for j, (d, r, o, flat) in enumerate(vtds):
        f = np.array(flat, float).reshape(-1, 4)
        lon, lat = np.cumsum(f[:, 0]) / 1e4, np.cumsum(f[:, 1]) / 1e4
        bx.append(lon); by.append(lat); brad.append(f[:, 2] * 10); bad.append(f[:, 3]); vid.append(np.full(len(f), j))
        vd.append(d); vr.append(r); vo.append(o); vad.append(f[:, 3].sum())
    lon, lat, rad, ad, vid = map(np.concatenate, (bx, by, brad, bad, vid))
    vd, vr, vo, vad = map(np.array, (vd, vr, vo, vad))
    tot24 = vd + vr + vo
    bshare = np.where(vad[vid] > 0, ad / np.maximum(vad[vid], 1), 0)
    px, py = project(lon, lat)
    for p, (n26, v24) in enumerate([(c["dem"], vd), (c["rep"], vr), (c["other"], vo)]):
        if not n26:
            continue
        w = (v24 if v24.sum() > 0 else tot24)[vid] * bshare  # expected share of the party's county votes, per block
        if w.sum() <= 0:
            w = np.ones_like(w)
        start = rng.random()
        k = np.diff(np.floor(np.concatenate([[start], start + np.cumsum(w) * n26 / w.sum()]))).astype(np.int64)
        k[-1] += n26 - k.sum()  # the last block takes any rounding left over, so the county total is exact
        k = np.maximum(k, 0)
        idx = np.repeat(np.arange(len(k)), k)
        # bell-curve spread around each block, cut off at 2.5 standard deviations; a dot on empty land gets a new spot, and
        # after 16 tries settles on the block's own center
        dx, dy = px[idx].copy(), py[idx].copy()
        todo = np.arange(len(idx))
        for _ in range(16):
            u = rng.random(len(todo)) * (1 - math.exp(-2.5 ** 2 / 2))
            g = np.sqrt(-2 * np.log(1 - u))
            a = rng.random(len(todo)) * 2 * math.pi
            rr = 0.75 * rad[idx[todo]] * g
            nx, ny = px[idx[todo]] + rr * np.cos(a), py[idx[todo]] + rr * np.sin(a)
            good = lived(nx, ny)
            dx[todo[good]], dy[todo[good]] = nx[good], ny[good]
            todo = todo[~good]
            if not len(todo):
                break
        xs.append(dx); ys.append(dy); parties.append(np.full(len(idx), p, np.int8))
xs, ys, parties = np.concatenate(xs), np.concatenate(ys), np.concatenate(parties)
print(f"placed {len(xs):,} dots (expected {TOT:,})")
assert len(xs) == TOT

DOT_C = np.array([[0x6c, 0x7d, 0xff], [0xff, 0x3b, 0x3b], [0x9a, 0xa6, 0xb8]], float)
ix, iy = to_px(xs, ys)
ix, iy = np.floor(ix).astype(np.int64), np.floor(iy).astype(np.int64)
ok = (ix >= 0) & (ix < PW) & (iy >= 0) & (iy < PH)
flat, par = iy[ok] * PW + ix[ok], parties[ok]
del xs, ys, ix, iy, ok, parties
# voters per pixel, and the sum of their colors (float32, one party at a time, to keep memory down at large scales)
n = np.zeros(PW * PH, np.float32)
rgb = np.zeros((PW * PH, 3), np.float32)
for p in range(3):
    cnt = np.bincount(flat[par == p], minlength=PW * PH).astype(np.float32)
    n += cnt
    rgb += cnt[:, None] * DOT_C[p].astype(np.float32)
del flat, par
rgb /= np.maximum(n, 1)[:, None]  # the average color of the voters there
glow = 1 - np.exp(-n / 1.2)  # one voter: a dim speck; several: full color
bg = np.array(BG, np.float32)
rgb -= bg; rgb *= glow[:, None]; rgb += bg
right = Image.fromarray(rgb.reshape(PH, PW, 3).clip(0, 255).astype(np.uint8))
del rgb, n, glow
# faint county lines over the dots
lines = Image.new("L", (PW * SS, PH * SS), 0)
lw = ImageDraw.Draw(lines)
for polys in shapes.values():
    for p in polys:
        for r in p:
            x, y = to_px(*project(r[:, 0], r[:, 1]), SS)
            lw.line(list(zip(x, y)) + [(x[0], y[0])], fill=255, width=LINE)
if SS > 1:
    lines = lines.resize((PW, PH), Image.LANCZOS)
lines = lines.point(lambda v: int(v * 0.16))
right.paste(Image.new("RGB", right.size, (255, 255, 255)), (0, 0), lines)

# ---------- the poster ----------
FONTS = Path("C:/Windows/Fonts")


def font(name, size):
    for f in [name, "arial.ttf"]:
        try:
            return ImageFont.truetype(str(FONTS / f), size * K)
        except OSError:
            continue
    return ImageFont.load_default(size * K)


class Scaled:
    """ImageDraw that takes 4K design coordinates and draws at K times the size"""
    def __init__(self, im):
        self.d = ImageDraw.Draw(im)

    def text(self, xy, txt, **kw):
        self.d.text((xy[0] * K, xy[1] * K), txt, **kw)

    def textlength(self, txt, **kw):
        return self.d.textlength(txt, **kw) / K

    def line(self, pts, width=1, **kw):
        self.d.line([(x * K, y * K) for x, y in pts], width=round(width * K), **kw)

    def rectangle(self, box, **kw):
        self.d.rectangle([v * K for v in box], **kw)

    def ellipse(self, box, **kw):
        self.d.ellipse([v * K for v in box], **kw)


F_KICK, F_TITLE, F_SUB = font("seguisb.ttf", 34), font("segoeuib.ttf", 92), font("segoeui.ttf", 40)
F_HEAD, F_BODY, F_SMALL, F_LEG = font("segoeuib.ttf", 54), font("segoeui.ttf", 32), font("segoeui.ttf", 24), font("segoeui.ttf", 28)
F_BIG = font("segoeuib.ttf", 40)
GOLD, WHITE, MUTED, DIM = (242, 193, 78), (238, 241, 246), (168, 177, 192), (120, 129, 145)
BLUE, RED, GRAY = tuple(DOT_C[0].astype(int)), tuple(DOT_C[1].astype(int)), tuple(DOT_C[2].astype(int))

img = Image.new("RGB", (W * K, H * K), BG)
img.paste(left, (LEFT_X * K, MAP_Y * K))
img.paste(right, (RIGHT_X * K, MAP_Y * K))
del left, right
dr = Scaled(img)
fmt = lambda v: f"{v:,}"
pct = lambda a, b: f"{100 * a / b:.1f}%"

# title
dr.text((LEFT_X, 70), "TEXAS  ·  U.S. SENATE  ·  NOVEMBER 3, 2026", font=F_KICK, fill=GOLD)
dr.text((LEFT_X, 112), "Same election, two maps", font=F_TITLE, fill=WHITE)
x = LEFT_X
for txt, col in [(f"{D['name']} (D) {pct(D['votes'], TOT)}", BLUE), ("   ·   ", DIM), (f"{R['name']} (R) {pct(R['votes'], TOT)}", RED),
                 ("   ·   ", DIM), (f"others {pct(OTH, TOT)}", MUTED),
                 (f"      {D['last']} won by {fmt(D['votes'] - R['votes'])} votes out of {fmt(TOT)}", MUTED)]:
    dr.text((x, 236), txt, font=F_SUB, fill=col); x += dr.textlength(txt, font=F_SUB)
dr.line([(LEFT_X, 318), (W - 120, 318)], fill=(40, 46, 58), width=2)

# panel headings, inside each map's empty top-right corner (north of the Red River, east of the Panhandle)
d_won = sum(1 for c in counties if c["dem"] > c["rep"])
r_won = len(counties) - d_won


def heading(x0, title, lines):
    dr.text((x0 + MAP_W - 40, MAP_Y + 20), title, font=F_HEAD, fill=WHITE, anchor="ra")
    y = MAP_Y + 96
    for txt in lines:
        dr.text((x0 + MAP_W - 40, y), txt, font=F_BODY, fill=MUTED, anchor="ra"); y += 44
    return y


heading(LEFT_X, "County by county", ["Each county colored by who won it,", "no matter how many people voted there."])
y = MAP_Y + 210
dr.text((LEFT_X + MAP_W - 40, y), f"{R['last']} carried {r_won} of 254 counties", font=F_BIG, fill=RED, anchor="ra")
dr.text((LEFT_X + MAP_W - 40, y + 52), f"{D['last']} carried {d_won}", font=F_BIG, fill=BLUE, anchor="ra")
heading(RIGHT_X, "One dot per voter", [f"{fmt(TOT)} dots: every Senate vote,", "placed where voters live."])
dr.text((RIGHT_X + MAP_W - 40, y), f"{D['last']} won {fmt(D['votes'])} votes", font=F_BIG, fill=BLUE, anchor="ra")
dr.text((RIGHT_X + MAP_W - 40, y + 52), f"{R['last']} won {fmt(R['votes'])}", font=F_BIG, fill=RED, anchor="ra")

# legends, in each map's empty lower-left corner (south of Big Bend, west of the Rio Grande valley)
lx, ly = LEFT_X + 40, MAP_Y + MAP_H - 400
dr.text((lx, ly), "Winner's share of the county vote", font=F_LEG, fill=WHITE)
labels = ["<50", "50–60", "60–70", "70–80", "80–90", "90+"]
sw = 72
for row, (ramp, who) in enumerate([(DEM_C, D["last"]), (REP_C, R["last"])]):
    yy = ly + 48 + row * 62
    for i, col in enumerate(ramp):
        dr.rectangle([lx + 140 + i * sw, yy, lx + 140 + (i + 1) * sw - 4, yy + 40], fill=col)
    dr.text((lx, yy + 20), who, font=F_LEG, fill=MUTED, anchor="lm")
for i, t in enumerate(labels):
    dr.text((lx + 140 + i * sw + sw / 2 - 2, ly + 48 + 124 + 8), t, font=F_SMALL, fill=DIM, anchor="ma")
dr.text((lx + 140 + 6 * sw - 4, ly + 48 + 124 + 40), "percent of all votes cast", font=F_SMALL, fill=DIM, anchor="ra")

lx, ly = RIGHT_X + 40, MAP_Y + MAP_H - 400
dr.text((lx, ly), "Each dot is one voter", font=F_LEG, fill=WHITE)
for i, (col, t) in enumerate([(BLUE, f"{D['name']} (D)"), (RED, f"{R['name']} (R)"), (GRAY, "Everyone else")]):
    yy = ly + 62 + i * 50
    dr.ellipse([lx, yy - 11, lx + 22, yy + 11], fill=col)
    dr.text((lx + 40, yy), t, font=F_LEG, fill=MUTED, anchor="lm")
dr.text((lx, ly + 62 + 3 * 50 - 6), "Where voters overlap, colors mix.", font=F_SMALL, fill=DIM)

# scale bar (same scale on both maps)
for x0 in (LEFT_X, RIGHT_X):
    px100 = 100 * 1609.344 * SCALE
    bx, byy = x0 + 40, MAP_Y + MAP_H - 40
    dr.line([(bx, byy), (bx + px100, byy)], fill=MUTED, width=3)
    for t in (bx, bx + px100):
        dr.line([(t, byy - 10), (t, byy + 2)], fill=MUTED, width=3)
    dr.text((bx + px100 + 14, byy), "100 miles", font=F_SMALL, fill=MUTED, anchor="lm")

# sources
sy = MAP_Y + MAP_H + 60
dr.line([(LEFT_X, sy - 24), (W - 120, sy - 24)], fill=(40, 46, 58), width=2)
src = [
    ("Results: ", "Texas Secretary of State, election night returns, U.S. Senate by county (unofficial; official canvass pending), as of "
     f"{res['meta']['resultsUpdated']}. Percentages are of all votes cast, including third-party and write-in votes."),
    ("Dot placement: ", "An estimate, not a record of any person's vote; ballots are secret and 2026 precinct results aren't out yet. Each party's 2026 "
     "county total is shared among 2024 voting districts by that party's 2024 U.S. Senate votes there (Texas Legislative Council, "
     "Capitol Data Portal), then among 2020 census blocks by population 18 and over (U.S. Census Bureau, 2020 P.L. 94-171), off land where the Census counted no one (2020 TIGER/Line blocks). "
     "Every county adds up exactly to its 2026 result."),
    ("Boundaries: ", "U.S. Census Bureau county boundaries via us-atlas (1:10m). Equal-area conic projection; both maps at the same scale."),
]
for label, body in src:
    words, line, first = body.split(), "", True
    x0 = LEFT_X + dr.textlength(label, font=font("seguisb.ttf", 26))
    dr.text((LEFT_X, sy), label, font=font("seguisb.ttf", 26), fill=WHITE)
    for wd in words:
        trial = (line + " " + wd).strip()
        if dr.textlength(trial, font=F_SMALL) > (W - 120 - x0):
            dr.text((x0, sy + 1), line, font=F_SMALL, fill=MUTED); sy += 34; line = wd
        else:
            line = trial
    dr.text((x0, sy + 1), line, font=F_SMALL, fill=MUTED); sy += 46
dr.text((W - 120, H - 50), "johnesco.github.io/texas", font=F_LEG, fill=GOLD, anchor="rs")

img.save(OUT, optimize=True)
print(f"wrote {OUT} ({OUT.stat().st_size / 1e6:.1f} MB)")

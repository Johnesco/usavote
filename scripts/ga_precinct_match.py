"""Why Georgia is county-only: how many 2026 U.S. Senate votes reach a Census 2020 voting district by exact name or a clear fix.
Writes nothing for the site; it prints the figures in docs/records/georgia.md and, with a file path, every row's bucket for review.

Each 2026 precinct row, in this order, within its county:
  exact      same name, ignoring case and punctuation
  whole      the county has one row, so it covers all the county's districts
  form       same name after dropping code prefixes, "(ATL)" tags and common abbreviations (Mt/Mount, Elementary/Elem)
  code=name  the row's name is only its code, and a district has that code (Chatham "1-01C", whose districts are named for polling places)
  code+sim   same code and a similar name
  name~      not the same code, but a letters-only name that one district's name contains or closely resembles
  split      a code that a district has, less one last letter or digit (Fulton "06D1" on "06D"): the name gives its one parent
  combine    the other way round: districts have this code plus one letter or digit (Fulton "ML04" over "ML04A", "ML04B", "ML04C")
These count as exact or a clear fix. The next two don't:
  code-only  same code, unlike name. Counties have renumbered: Lowndes's "Hahira Community Center" has the code of the district named
             Northside (967 votes, 35,040 adults), and Cherokee's "Bells" points at one district by name and another by code.
  none       nothing to go on: new precincts, or a county that redrew its lines (Spalding's P1 to P8 from 18 districts)

Run:  python scripts/ga_precinct_match.py [review-file]
"""
import difflib
import io
import json
import re
import struct
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "ga"
NEED = 0.90
CLEAR = ("exact", "whole", "form", "code=name", "code+sim", "name~", "split", "combine")
WORDS = [(r"\bMT\b", "MOUNT"), (r"\bST\b", "SAINT"), (r"\bELEMENTARY\b", "ELEM"), (r"\bSCHOOL\b", "SCH"), (r"\bCHURCH\b", "CH"), (r"\bBAPTIST\b", "BAPT"),
         (r"\bROAD\b", "RD"), (r"\bCOMMUNITY\b", "COMM"), (r"\bCENTER\b", "CTR"), (r"\bCENTRE\b", "CTR"), (r"\bRECREATION\b", "REC")]


def norm(s):
    return re.sub(r"[^A-Z0-9]", "", s.upper())


def code(s):
    return norm(s).lstrip("0")


def words(s):
    s = re.sub(r"\([^)]*\)", "", s.upper())
    s = re.sub(r"^\s*[0-9]+\s*-\s*", "", s)         # "0110011 - POPLAR SPRINGS", "03-Almon"
    s = re.sub(r"^\s*[0-9]{1,4}\s+(?=[A-Z])", "", s)  # "001 Harbins A"
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    for a, b in WORDS: s = re.sub(a, b, s)
    return s.split()


def clean(s):
    return "".join(words(s))


def named(s):
    """A real name: letters only, long enough to mean something. Fulton's "RW12A" is one character from "RW22A" and isn't the same place."""
    w = clean(s)
    return len(w) >= 4 and not re.search(r"[0-9]", w) and len(set(w)) > 2


export = json.loads((RAW / "results" / "export-11032026GeneralAndSpecialElection.json").read_text(encoding="utf-8-sig"))
z = zipfile.ZipFile(RAW / "census" / "tl_2020_13_vtd20.zip")
dbf = z.read("tl_2020_13_vtd20.dbf")
n, hlen, rlen = struct.unpack("<IHH", dbf[4:12])
fields, off, s = {}, 32, 1
while dbf[off] != 0x0D:
    name, ln = dbf[off:off + 11].split(b"\0")[0].decode(), dbf[off + 16]
    fields[name] = (s, ln); s += ln; off += 32
fld = lambda i, name: dbf[hlen + i * rlen + fields[name][0]: hlen + i * rlen + fields[name][0] + fields[name][1]].decode("utf-8").strip()
districts = defaultdict(list)
for i in range(n):
    districts[fld(i, "COUNTYFP20")].append((fld(i, "GEOID20"), fld(i, "VTDST20"), fld(i, "NAME20")))
fips, rec, adults = {}, {}, {}
pl = zipfile.ZipFile(RAW / "census" / "ga2020.pl.zip")
with pl.open("gageo2020.pl") as f:
    for line in io.TextIOWrapper(f, encoding="latin-1"):
        r = line.rstrip("\n").split("|")
        if r[2] == "050" and r[3] == "00" and r[4] == "00": fips[r[86].removesuffix(" County")] = r[8].split("US")[1][2:]
        elif r[2] == "700" and r[3] == "00": rec[r[7]] = r[8].split("US")[1]
with pl.open("ga000022020.pl") as f:
    for line in io.TextIOWrapper(f, encoding="latin-1"):
        r = line.split("|", 6)
        if r[4] in rec: adults[rec[r[4]]] = int(r[5])

votes, count, by_county, lines = Counter(), Counter(), defaultdict(Counter), []
for county in sorted(export["localResults"], key=lambda c: c["name"]):
    senate = next(b for b in county["ballotItems"] if b["id"] == "US2")
    rows, names = Counter(), {}
    for o in senate["ballotOptions"]:
        for p in o["precinctResults"]:
            rows[p["id"]] += p["voteCount"] or 0; names[p["id"]] = p["name"]
    vs = districts[fips[county["name"].removesuffix(" County")]]
    name_of = {g: nm for g, _, nm in vs}
    by_norm, by_code, by_clean = {}, {}, defaultdict(list)
    for g, c, nm in vs:
        by_norm.setdefault(norm(nm), g); by_code.setdefault(code(c), g); by_clean[clean(nm)].append(g)
    got, taken = {}, set()
    for pid in rows:
        if norm(names[pid]) in by_norm:
            got[pid] = ("exact", by_norm[norm(names[pid])]); taken.add(got[pid][1])
    if len(rows) == 1 and not got: got[next(iter(rows))] = ("whole", None)
    for pid in rows:
        if pid in got: continue
        free = [g for g in by_clean.get(clean(names[pid]), []) if g not in taken]
        if len(free) == 1: got[pid] = ("form", free[0]); taken.add(free[0])
    for pid in rows:
        g = by_code.get(code(pid))
        if pid in got or not g or g in taken: continue
        a, b = clean(names[pid]), clean(name_of[g])
        if code(names[pid]) == code(pid): got[pid] = ("code=name", g); taken.add(g)
        elif difflib.SequenceMatcher(None, a, b).ratio() >= 0.7 or (b and (b in a or a in b)): got[pid] = ("code+sim", g); taken.add(g)
    for pid in sorted(rows, key=lambda p: -rows[p]):
        if pid in got or not named(names[pid]): continue
        a = words(names[pid])
        scored = []
        for g, _, nm in vs:
            if g in taken or not named(nm): continue
            b = words(nm)
            inside = len(b) <= len(a) and a[:len(b)] == b or len(a) <= len(b) and b[:len(a)] == a
            scored.append((1.0 if inside else difflib.SequenceMatcher(None, "".join(a), "".join(b)).ratio(), g))
        scored.sort(reverse=True)
        if scored and scored[0][0] >= 0.8 and (len(scored) == 1 or scored[0][0] - scored[1][0] >= 0.1):
            got[pid] = ("name~", scored[0][1]); taken.add(scored[0][1])
    for pid in rows:
        if pid in got: continue
        parent = by_code.get(code(pid)[:-1])
        children = [g for c, g in by_code.items() if c[:-1] == code(pid) and g not in taken]
        if code(names[pid]) == code(pid) and len(code(pid)) >= 3:
            if parent: got[pid] = ("split", parent)
            elif len(children) >= 2: got[pid] = ("combine", children[0]); taken.update(children)
    for pid in rows:
        if pid in got: continue
        g = by_code.get(code(pid))
        if g and g not in taken: got[pid] = ("code-only", g); taken.add(g)
        else: got[pid] = ("none", None)
    for pid, v in sorted(rows.items(), key=lambda kv: -kv[1]):
        kind, g = got[pid]
        votes[kind] += v; count[kind] += 1; by_county[county["name"]][kind] += v
        lines.append(f"{county['name']}\t{kind}\t{pid}\t{names[pid]}\t{v}\t{name_of.get(g, '')}\t{adults.get(g, '')}")

total = sum(votes.values())
clear = sum(votes[k] for k in CLEAR)
for k in (*CLEAR, "code-only", "none"):
    print(f"{k:10} {count[k]:5,} rows {votes[k]:10,} votes {100 * votes[k] / total:6.2f}%")
print(f"exact or a clear fix: {clear:,} of {total:,} U.S. Senate votes in precinct rows = {100 * clear / total:.2f}% (needs {NEED:.0%})")
print(f"even counting every same-code row as a match: {100 * (clear + votes['code-only']) / total:.2f}%")
worst = sorted(by_county.items(), key=lambda kv: -(kv[1]["none"] + kv[1]["code-only"]))[:12]
print("most votes without a clear match:", [(c.removesuffix(" County"), k["none"] + k["code-only"]) for c, k in worst])
if len(sys.argv) > 1:
    Path(sys.argv[1]).write_text("\n".join(lines), encoding="utf-8")

"""A chamber's district races as one race for the results page, the way scripts/build_data.py does it for Texas: every district
added up by county, with each district's own result kept for the By district view.

A state's results script gathers votes[district][county index][(candidate name, party)] = votes and calls chamber_race(). Parties
are "DEM" and "REP" for the two major parties and anything else for the rest ("W" for write-ins, "NP" for a candidate the source
lists with no party).
"""

PARTY_WORD = {"DEM": "Democrats", "REP": "Republicans", "LIB": "Libertarians", "L": "Libertarians", "GRE": "Greens", "IND": "Independents",
              "W": "Write-ins", "NP": "No-party candidates", "CON": "Constitution Party candidates", "Other party": "Other parties"}


def chamber_race(rid, label, group, office, size, votes, n_counties, incumbents=(), expect=None, withheld=None):
    """votes: {district: {county index: {(name, party): votes}}}. incumbents: the (name, party) pairs marked as incumbents.
    expect: {district: {(name, party): votes}}, the source's own district totals, checked if given.
    withheld: {district: {(name, party): votes}}, votes the source counts in a district's total but shows in no county (a figure
    it hides to protect a handful of voters): they count toward the district and are left out of every county's row.
    Returns the race: counties[i] = [dem, rep, other, total, districts here, of those with no Democrat, with no Republican]."""
    rows = [[0] * 7 for _ in range(n_counties)]
    districts = []
    for num in sorted(votes):
        totals = {}
        for by_cand in votes[num].values():
            for k, v in by_cand.items(): totals[k] = totals.get(k, 0) + v
        for k, v in (withheld or {}).get(num, {}).items(): totals[k] = totals.get(k, 0) + v
        if expect is not None:
            assert totals == expect[num], (label, num, "counties don't add up to the district's total", totals, expect[num])
        has = {p for _, p in totals}
        for i, by_cand in votes[num].items():
            dem = sum(v for (_, p), v in by_cand.items() if p == "DEM")
            rep = sum(v for (_, p), v in by_cand.items() if p == "REP")
            tot = sum(by_cand.values())
            row = rows[i]
            row[0] += dem; row[1] += rep; row[2] += tot - dem - rep; row[3] += tot
            row[4] += 1; row[5] += "DEM" not in has; row[6] += "REP" not in has
        cands = [dict(name=n, party=p, incumbent=(n, p) in incumbents, votes=v) for (n, p), v in sorted(totals.items(), key=lambda kv: -kv[1])]
        # where: the rows of the counties its results came from, which scripts/build_districts.py checks its outline against
        districts.append(dict(district=num, total=sum(totals.values()), counties=len(votes[num]), where=sorted(votes[num]), candidates=cands))
    assert all(1 <= d["district"] <= size for d in districts), (label, [d["district"] for d in districts], size)
    party_votes = {}
    for d in districts:
        for c in d["candidates"]: party_votes[c["party"]] = party_votes.get(c["party"], 0) + c["votes"]
    assert party_votes.get("DEM") and party_votes.get("REP"), (label, "the page needs votes for both major parties", party_votes)
    word = lambda p: PARTY_WORD.get(p, f"{p} candidates")
    cands = [dict(name=word(p), last=word(p), party=p, incumbent=False, votes=v)
             for p, v in sorted(party_votes.items(), key=lambda kv: -kv[1]) if v]
    seats = {}
    for d in districts:
        w = d["candidates"][0]["party"]
        seats[w] = seats.get(w, 0) + 1
    assert sum(r[3] for r in rows) == sum(d["total"] for d in districts) - sum(v for w in (withheld or {}).values() for v in w.values())
    return dict(id=rid, office=office, label=label, group=group, chamber=True, seats=seats, size=size, candidates=cands,
                districts=districts, counties=rows)


def summary(race):
    """One line for a build's printout."""
    missing = sorted(set(range(1, race["size"] + 1)) - {d["district"] for d in race["districts"]})
    return (f"  {race['id']:26} {len(race['districts'])} of {race['size']} districts, seats {race['seats']}, "
            f"{sum(d['total'] for d in race['districts']):,} votes" + (f"; not in the results: districts {missing}" if missing else ""))

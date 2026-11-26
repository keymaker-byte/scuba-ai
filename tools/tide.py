#!/usr/bin/env python3
"""Tide predictions at any station of any tide source the tool reads, in metres above the
station's datum (MLLW at a NOAA station, CHS Chart Datum at a CHS station), read on this machine.

  tide.py stations --near LAT LON [--datum K]           tide stations near a site, from every source
  tide.py predict STATION --tz Z [--date D]             high/low water for the day
  tide.py at STATION --tz Z --time "D HH:MM"            tide height at a moment
  tide.py range STATION --tz Z [--year Y]               median/max/min daily range and year span
  tide.py project STATION --tz Z --file F [--date D]    a site's datum depth to depth below surface, all day
  tide.py project STATION --tz Z --datum-depth X --datum K [--date D]   the same for any datum depth
  tide.py normalize STATION --tz Z --time T --depth D   observed depth to depth below the datum

Every station command also takes --file F, a site JSON, and --datum K, a datum name from
lib/datums.py (MLLW, CHS, LAKE, NONE): the run stops when the station is on another datum than
the site's depths. On LAKE and NONE there is no tide, the height is 0, and no station is named.
  tide.py fetch [STATION ...] [--near LAT LON --km R] [--all] [--source KEY]   cache stations ahead of time
  tide.py verify STATION [--date D] [--days N]          compare with the source's live predictions
  tide.py verify --all [--source KEY]                   compare every cached station

STATION is the source's own station ID, or KEY:ID where two sources share an ID.
"""
import argparse
import json
import os
import sys
import time as _time
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import datums  # noqa: E402
from lib.tide import Refused, Station, label, near, owner, sources, station  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def zone_of(name):
    """The zone every time prints in: the site's own, passed as --tz."""
    try:
        return ZoneInfo(name)
    except Exception:
        sys.exit(f"{name} is not an IANA time zone name. Pass the site's `tz` from its JSON, e.g. America/Los_Angeles.")


def zone_name(tz):
    return getattr(tz, "key", None) or tz.tzname(None)


def load(name):
    try:
        return station(name)
    except Refused as e:
        sys.exit(str(e))


# --- commands ----------------------------------------------------------------------------

class NoTide:
    """The tide on a datum that carries none, LAKE or NONE: height 0 at every moment, by definition."""

    def __init__(self, datum):
        self.datum = datum
        self.id = self.name = None

    def height(self, t):
        return 0.0

    def extremes(self, start, end):
        return []


def header(st, what, tz):
    if isinstance(st, NoTide):
        print(f"No tide on {st.datum}  {what}  ({zone_name(tz)})")
        print(f"  {st.datum}: {datums.MEANING[st.datum]}. The tide height is 0 by definition, so the depth below the "
              "datum is the depth below the surface.")
        if st.datum == datums.LAKE:
            print("  A lake's level moves with the seasons; its depths hold to the water on the day it was surveyed, "
                  "usually within a metre.")
        print()
        return
    print(f"{label(st.source, st.id)}  {st.name}  {what}  ({zone_name(tz)})")
    print(f"  {st.source.name}: {st.provenance()}\n")


def site(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        sys.exit(f"{path}: cannot read it as JSON ({e}).")


def resolve(a):
    """The station a command reads, checked against the site's datum: (station or NoTide, the
    site JSON or None). The datum comes from --file's seabed_datum, or --datum; a station on
    another datum stops the run, and LAKE and NONE take no station."""
    doc = site(a.file) if a.file else None
    datum = datums.of_site(doc, a.file) if doc else None
    if a.datum:
        datums.check(a.datum)
        if datum and a.datum != datum:
            sys.exit(f"--datum {a.datum} disagrees with {a.file}'s seabed_datum, {datum}.")
        datum = a.datum
    if datum in datums.NO_TIDE:
        if a.station:
            sys.exit(f"The site's depths are on {datum} ({datums.MEANING[datum]}), which has no tide; a tide station "
                     f"would put a tide on them that the water does not have. Drop {a.station}.")
        return NoTide(datum), doc
    if not a.station:
        sys.exit("name a station" + (f" on {datum}" if datum else "") + ". Find one with `stations --near LAT LON"
                 + (f" --datum {datum}`." if datum else "`."))
    st = load(a.station)
    if datum and st.datum != datum:
        where = f"{doc['lat']} {doc['lon']}" if doc else "LAT LON"
        sys.exit(f"{label(st.source, st.id)} {st.name} is a {st.source.name} station, its heights above {st.datum}; the "
                 f"site's depths are on {datum}. The two are different surfaces, about a metre apart in the Salish "
                 f"Sea, so a depth on one plus a tide on the other is wrong by that much. Choose a station on {datum}: "
                 f"`stations --near {where} --datum {datum}`.")
    return st, doc


def local_day(day, tz):
    start = datetime.combine(day, time(0), tz).astimezone(timezone.utc)
    end = datetime.combine(day + timedelta(days=1), time(0), tz).astimezone(timezone.utc)
    return start, end


def _round(t, tz):
    return (t + timedelta(seconds=30)).astimezone(tz).replace(second=0, microsecond=0)


def day_extremes(ex, day, tz):
    """The day's highs and lows. A day holding only one kind (a single extreme, or two of the
    same kind either side of midnight) also takes the extreme just before and just after it, so
    its range always spans a low to a high."""
    idx = [i for i, e in enumerate(ex) if _round(e[0], tz).date() == day]
    if not idx:
        return []
    if len({ex[i][1] for i in idx}) < 2:
        idx = [i for i in (idx[0] - 1, *idx, idx[-1] + 1) if 0 <= i < len(ex)]
    return [ex[i] for i in idx]


KIND = {"reference": "reference", "fitted": "fitted constants"}


def cmd_stations(a):
    lat, lon = a.near
    if a.datum:
        datums.check(a.datum)
        if a.datum in datums.NO_TIDE:
            sys.exit(f"{a.datum} has no tide, so no station is needed: run the station commands with --file or "
                     f"--datum {a.datum} and no station, and the tide height is 0.")
    try:
        every = [s for s in sources(a.source) if not a.datum or s.datum == a.datum]
        if not every:
            sys.exit(f"No tide source{' named ' + a.source if a.source else ''} has its heights above {a.datum}.")
        rows = [r for s in every for r in near(lat, lon, n=a.n, key=s.key)]
        rows = sorted(rows, key=lambda r: r[0])[:a.n]
        lists = {s.key: s.listing()["fetched"] for s in every}
    except Refused as e:
        sys.exit(str(e))
    print(f"Tide prediction stations near {lat:.4f}, {lon:.4f} ("
          + "; ".join(f"{s.name} list as fetched {lists[s.key]}" for s in every) + "):\n")
    for km, src, sid, e in rows:
        kind = KIND.get(e["kind"]) or f"subordinate to {label(src, e['ref'])}"
        print(f"  {label(src, sid):<10} {km:5.1f} km  {e['name']}   ({kind}, {src.name}, datum {src.datum})")
    print("\nNearest is usually right for tide height — unlike currents, water level varies")
    print("smoothly. But a station across a constriction can lag; prefer one on the same shore.")


def cmd_predict(a):
    st, _ = resolve(a)
    tz = zone_of(a.tz)
    if isinstance(st, NoTide):
        header(st, f"{a.date}  high/low water", tz)
        print("  no highs or lows: the height is 0 all day.")
        return
    start, end = local_day(a.date, tz)
    ex = st.extremes(start - timedelta(days=1), end + timedelta(days=1))
    pts = day_extremes(ex, a.date, tz)
    header(st, f"{a.date}  high/low water, m above {st.datum}, local time", tz)
    for t, kind, v in pts:
        lt = _round(t, tz)
        when = f"{lt:%H:%M}" if lt.date() == a.date else f"{lt:%Y-%m-%d %H:%M}"
        print(f"  {when}  {'HIGH' if kind == 'H' else 'LOW '}  {v:+.2f} m")
    lo, hi = min(p[2] for p in pts), max(p[2] for p in pts)
    print(f"\n  range {hi - lo:.2f} m — a fixed seabed feature reads {hi - lo:.2f} m deeper at the high than the low.")


def cmd_range(a):
    st, _ = resolve(a)
    tz = zone_of(a.tz)
    if isinstance(st, NoTide):
        header(st, f"{a.year}  range across the year", tz)
        print("  median daily range   0.00 m\n  max daily range      0.00 m\n  year span            +0.00 m to +0.00 m")
        return
    start = local_day(date(a.year, 1, 1), tz)[0]
    end = local_day(date(a.year, 12, 31), tz)[1]
    ex = st.extremes(start - timedelta(days=1), end + timedelta(days=1))
    daily = []
    day = date(a.year, 1, 1)
    while day.year == a.year:
        vs = [e[2] for e in day_extremes(ex, day, tz)]
        if vs:
            daily.append((day.isoformat(), max(vs) - min(vs)))
        day += timedelta(days=1)
    daily.sort(key=lambda x: x[1])
    inyear = [e for e in ex if _round(e[0], tz).year == a.year]
    n = len(daily)
    median = daily[n // 2][1] if n % 2 else (daily[n // 2 - 1][1] + daily[n // 2][1]) / 2
    lo_day, hi_day = daily[0], daily[-1]
    header(st, f"{a.year}  high/low range across the year, m {st.datum}", tz)
    print(f"  {n} days, {len(inyear)} highs and lows\n")
    print(f"  median daily range   {median:.2f} m")
    print(f"  max daily range      {hi_day[1]:.2f} m  on {hi_day[0]}")
    print(f"  min daily range      {lo_day[1]:.2f} m  on {lo_day[0]}")
    print(f"  year span            {min(e[2] for e in inyear):+.2f} m to {max(e[2] for e in inyear):+.2f} m")
    print("\n  Use these for a site file's \"Typical range\" row: median as \"typical,\"")
    print("  max daily range as \"up to,\" year span as printed.")


def _moment(a):
    tz = zone_of(a.tz)
    return tz, a.time.replace(tzinfo=tz).astimezone(timezone.utc)


def cmd_at(a):
    st, _ = resolve(a)
    tz, t = _moment(a)
    h = st.height(t)
    header(st, f"{a.time:%Y-%m-%d %H:%M}  tide {h:+.2f} m {st.datum}", tz)
    print(f"  A feature X m below {st.datum} datum reads {h:+.2f} m {'deeper' if h >= 0 else 'shallower'} than X on the computer.")


def cmd_normalize(a):
    st, _ = resolve(a)
    tz, t = _moment(a)
    h = st.height(t)
    datum = a.depth - h
    header(st, f"{a.time:%Y-%m-%d %H:%M}  tide {h:+.2f} m {st.datum}", tz)
    print(f"  observed depth      {a.depth:6.1f} m  (below the surface, as the computer read it)")
    print(f"  tide height        {h:+7.2f} m")
    print("  ---")
    print(f"  depth below {st.datum:<6}  {datum:6.1f} m  <-- the comparable number. Log this.")
    if not isinstance(st, NoTide):
        print(f"\n  This is what to carry between dives. The {a.depth:.1f} m is only true at that tide.")


def cmd_project(a):
    if not a.file and not a.datum:
        sys.exit("project needs the datum its depth is on: --file with the site JSON (its seabed_m and seabed_datum), "
                 "or --datum-depth X with --datum K.")
    st, doc = resolve(a)
    depth = a.datum_depth if a.datum_depth is not None else (doc or {}).get("seabed_m")
    if not isinstance(depth, (int, float)):
        sys.exit("give --datum-depth, or a site JSON whose seabed_m is a number.")
    a.datum_depth = depth
    tz = zone_of(a.tz)
    if isinstance(st, NoTide):
        header(st, f"{a.date}  a feature {depth:.1f} m below {st.datum}", tz)
        print(f"  It reads {depth:.1f} m below the surface all day.")
        return
    start, end = local_day(a.date, tz)
    ex = [e for e in st.extremes(start - timedelta(hours=1), end + timedelta(hours=1)) if _round(e[0], tz).date() == a.date]
    header(st, f"{a.date}  a feature {a.datum_depth:.1f} m below {st.datum} datum", tz)
    for t, kind, h in ex:
        print(f"  {_round(t, tz):%H:%M}  {'HIGH' if kind == 'H' else 'LOW '}  tide {h:+.2f} m   ->  reads {a.datum_depth + h:5.1f} m below surface")
    hs = [e[2] for e in ex]
    print(f"\n  Across the day it swings {a.datum_depth + min(hs):.1f} m – {a.datum_depth + max(hs):.1f} m below the surface.")
    print("  Plan gas and ppO2 against the deepest, not the average.")


def cmd_fetch(a):
    try:
        if a.all:
            want = [(s, sid) for s in sources(a.source) for sid in sorted(s.listing()["stations"])]
        elif a.near:
            want = [(s, sid) for _, s, sid, _ in near(*a.near, radius_km=a.km, key=a.source)]
        elif a.station:
            want = [owner(n) for n in a.station]
        else:
            sys.exit("name stations, or pass --near LAT LON [--km R], or --all.")
    except Refused as e:
        sys.exit(str(e))
    # a subordinate station needs its reference too
    for s, sid in list(want):
        ref = s.listing()["stations"].get(sid, {}).get("ref")
        if ref and ref in s.listing()["stations"]:
            want.append((s, ref))
    want = sorted({(s.key, sid): (s, sid) for s, sid in want}.values(), key=lambda w: (w[0].key, w[1]))
    todo = [(s, sid) for s, sid in want if not s.cached(sid)]
    print(f"{len(want) - len(todo)} of {len(want)} already cached; downloading {len(todo)}.", flush=True)
    for k, (s, sid) in enumerate(todo, 1):
        doc = s.load(sid, quiet=True)
        note = ""
        if hasattr(s, "offline"):
            try:
                why = s.offline(doc)
            except SystemExit as e:
                if str(e).startswith(s.failed):  # a failed request stops the run, to be resumed later
                    raise
                why = str(e)
            note = f"  (answers nothing: {why})" if why else ""
        print(f"  {k}/{len(todo)}  {label(s, sid)}  {doc['name']}{note}", flush=True)
        _time.sleep(a.pause)
    for s, sid in want:
        if (s, sid) not in todo and hasattr(s, "offline"):
            doc = s.load(sid, quiet=True)
            why = s.offline(doc)
            if why:
                print(f"  cached  {label(s, sid)}  {doc['name']}  (answers nothing: {why})", flush=True)
    print("done.")


def cmd_verify(a):
    """Compare with the source's own predictions, read live from its service."""
    if a.all:
        return verify_all(a)
    if not a.station:
        sys.exit("name a station, or pass --all.")
    st = load(a.station)
    print(f"{label(st.source, st.id)}  {st.name}  {a.date} for {a.days} days, against {st.source.name}'s live predictions\n")
    r = st.compare(a.date, a.days, a.height_tol, a.time_tol)
    print("\n".join(f"  {line}" for line in st.report(r)))
    print("\n  PASS" if r["ok"] else f"\n  FAIL: limits are {a.height_tol} m and {a.time_tol} min. The cached data "
          f"may be older than {st.source.name}'s; delete the station's files, {os.path.relpath(st.source.db, ROOT)}/"
          f"{st.id}*.json, to fetch them again.")
    sys.exit(0 if r["ok"] else 1)


def verify_all(a):
    """Every cached station of each source, one result per line in the source's own
    _verify.jsonl. A station already in that file is skipped, so a stopped run picks up where it
    left off; delete the file to start over."""
    try:
        every = sources(a.source)
    except Refused as e:
        sys.exit(str(e))
    for src in every:
        report = os.path.join(src.db, "_verify.jsonl")
        done = {}
        if os.path.exists(report):
            with open(report) as f:
                for line in f:
                    r = json.loads(line)
                    done[r["station"]] = r
        todo = [sid for sid in sorted(src.listing()["stations"]) if src.cached(sid) and sid not in done]
        print(f"== {src.name}: {len(done)} stations already verified; {len(todo)} to go, {a.days} days from {a.date}.",
              flush=True)
        for k, sid in enumerate(todo, 1):
            st = Station(src, src.load(sid))
            try:
                r = st.compare(a.date, a.days, a.height_tol, a.time_tol)
            except SystemExit as e:
                if str(e).startswith(src.failed):  # a failed request stops the run, to be resumed later
                    raise
                r = {"station": sid, "ok": False, "error": str(e)}
            r.update(name=st.name, date=a.date.isoformat(), days=a.days)
            with open(report, "a") as f:
                f.write(json.dumps(r) + "\n")
            done[sid] = r
            if k % 25 == 0 or not r["ok"]:
                print(f"  {k}/{len(todo)}  {label(src, sid)}  {'ok' if r['ok'] else 'FAIL'}", flush=True)
            _time.sleep(a.pause)
        kinds = {sid: e["kind"] for sid, e in src.listing()["stations"].items()}
        print()
        for kind in ("reference", "subordinate", "fitted"):
            rs = [r for sid, r in done.items() if kinds.get(sid) == kind]
            if not rs:
                continue
            bad = [r for r in rs if not r["ok"]]
            print(f"  {kind}: {len(rs) - len(bad)} of {len(rs)} stations within {a.height_tol} m and {a.time_tol} min")
        print(f"  results: {os.path.relpath(report, ROOT)}\n")


def when(s):
    return datetime.strptime(s, "%Y-%m-%d %H:%M")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    def zoned(sp):
        sp.add_argument("station", nargs="?", help="the source's station ID, or KEY:ID; none on LAKE or NONE")
        sp.add_argument("--tz", required=True, metavar="IANA_ZONE", help="the site's time zone, the `tz` in its JSON")
        sp.add_argument("--file", help="a site JSON: the station must be on its seabed_datum")
        sp.add_argument("--datum", metavar="K", help="the datum the site's depths are on: " + ", ".join(datums.MEANING))

    s = sub.add_parser("stations", help="find tide stations near a site")
    s.add_argument("--near", nargs=2, type=float, metavar=("LAT", "LON"), required=True)
    s.add_argument("-n", type=int, default=6)
    s.add_argument("--source", help="one source's stations only, by its key")
    s.add_argument("--datum", metavar="K", help="only stations whose heights are above this datum")
    s.set_defaults(fn=cmd_stations)

    s = sub.add_parser("predict", help="high/low water for the day")
    zoned(s)
    s.add_argument("--date", type=date.fromisoformat, default=date.today())
    s.set_defaults(fn=cmd_predict)

    s = sub.add_parser("range", help="median/max/min daily range and span across a year")
    zoned(s)
    s.add_argument("--year", type=int, default=date.today().year)
    s.set_defaults(fn=cmd_range)

    s = sub.add_parser("at", help="tide height at a moment")
    zoned(s)
    s.add_argument("--time", type=when, required=True, metavar='"YYYY-MM-DD HH:MM"')
    s.set_defaults(fn=cmd_at)

    s = sub.add_parser("normalize", help="observed depth -> depth below the station's datum")
    zoned(s)
    s.add_argument("--time", type=when, required=True, metavar='"YYYY-MM-DD HH:MM"')
    s.add_argument("--depth", type=float, required=True, help="metres, as the computer read it")
    s.set_defaults(fn=cmd_normalize)

    s = sub.add_parser("project", help="datum depth -> depth below surface through the day")
    zoned(s)
    s.add_argument("--datum-depth", type=float, help="metres below the datum; default the site JSON's seabed_m")
    s.add_argument("--date", type=date.fromisoformat, default=date.today())
    s.set_defaults(fn=cmd_project)

    s = sub.add_parser("fetch", help="cache stations ahead of time")
    s.add_argument("station", nargs="*")
    s.add_argument("--near", nargs=2, type=float, metavar=("LAT", "LON"))
    s.add_argument("--km", type=float, default=50.0, help="radius for --near, default 50")
    s.add_argument("--all", action="store_true", help="every station each source lists")
    s.add_argument("--source", help="one source only, by its key")
    s.add_argument("--pause", type=float, default=0.3, help="seconds between stations, default 0.3")
    s.set_defaults(fn=cmd_fetch)

    s = sub.add_parser("verify", help="compare with the source's live predictions")
    s.add_argument("station", nargs="?")
    s.add_argument("--all", action="store_true", help="every cached station")
    s.add_argument("--source", help="with --all, one source only, by its key")
    s.add_argument("--date", type=date.fromisoformat, default=date.today())
    s.add_argument("--days", type=int, default=30)
    s.add_argument("--height-tol", type=float, default=0.02, help="metres, default 0.02")
    s.add_argument("--time-tol", type=float, default=3.0, help="minutes, default 3")
    s.add_argument("--pause", type=float, default=0.2, help="seconds between stations with --all, default 0.2")
    s.set_defaults(fn=cmd_verify)

    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()

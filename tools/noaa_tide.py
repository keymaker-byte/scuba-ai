#!/usr/bin/env python3
"""NOAA CO-OPS tide predictions, in metres against MLLW, computed on this machine.

  noaa_tide.py stations --near LAT LON                       tide stations near a site
  noaa_tide.py predict STATION [--date D]                    high/low water for the day
  noaa_tide.py at STATION --time "D HH:MM"                   tide height at a moment
  noaa_tide.py range STATION [--year Y]                      median/max/min daily range and year span
  noaa_tide.py project STATION --datum-depth X [--date D]    datum depth to depth below surface, all day
  noaa_tide.py normalize STATION --time T --depth D          observed depth to depth below MLLW
  noaa_tide.py fetch [STATION ...] [--near LAT LON --km R] [--all]   cache stations ahead of time
  noaa_tide.py verify STATION [--date D] [--days N]          compare with NOAA's live API
  noaa_tide.py verify --all                                  compare every cached station
"""
import argparse
import json
import math
import os
import sys
import time as _time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.tides import DB, DG, extremes, get, height, height_at, reference, station, station_list  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT = os.path.join(DB, "_verify.jsonl")


# --- the cache: station list, then one file per station ----------------------------------


def zone_of(name):
    """The zone every time prints in: the site's own, passed as --tz."""
    try:
        return ZoneInfo(name)
    except Exception:
        sys.exit(f"{name} is not an IANA time zone name. Pass the site's `tz` from its JSON, e.g. America/Los_Angeles.")


def zone_name(tz):
    return getattr(tz, "key", None) or tz.tzname(None)


# --- commands ----------------------------------------------------------------------------

def header(doc, what, tz):
    print(f"{doc['id']}  {doc['name']}  {what}  ({zone_name(tz)})")
    if doc["type"] == "S":
        ref = reference(doc)
        print(f"  subordinate to {ref['id']} {ref['name']}; computed locally from NOAA's corrections as fetched "
              f"{doc['fetched']} and constants as fetched {ref['fetched']}\n")
    else:
        print(f"  computed locally from NOAA's constants as fetched {doc['fetched']}\n")


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


def cmd_stations(a):
    st = station_list()
    lat, lon = a.near
    scale = math.cos(math.radians(lat))
    rows = sorted(((math.hypot((s["lat"] - lat) * 60.0, (s["lon"] - lon) * 60.0 * scale) * 1.852, sid, s)
                   for sid, s in st["stations"].items()), key=lambda r: r[0])[: a.n]
    print(f"Tide prediction stations near {lat:.4f}, {lon:.4f} (NOAA's list as fetched {st['fetched']}):\n")
    for km, sid, s in rows:
        kind = "reference" if s["type"] != "S" else f"subordinate to {s['ref']}"
        print(f"  {sid:<10} {km:5.1f} km  {s['name']}   ({kind})")
    print("\nNearest is usually right for tide height — unlike currents, water level varies")
    print("smoothly. But a station across a constriction can lag; prefer one on the same shore.")


def cmd_predict(a):
    doc = station(a.station)
    tz = zone_of(a.tz)
    start, end = local_day(a.date, tz)
    ex = extremes(doc, start - timedelta(days=1), end + timedelta(days=1))
    pts = day_extremes(ex, a.date, tz)
    header(doc, f"{a.date}  high/low water, m above MLLW, local time", tz)
    for t, kind, v in pts:
        lt = _round(t, tz)
        when = f"{lt:%H:%M}" if lt.date() == a.date else f"{lt:%Y-%m-%d %H:%M}"
        print(f"  {when}  {'HIGH' if kind == 'H' else 'LOW '}  {v:+.2f} m")
    lo, hi = min(p[2] for p in pts), max(p[2] for p in pts)
    print(f"\n  range {hi - lo:.2f} m — a fixed seabed feature reads {hi - lo:.2f} m deeper at the high than the low.")


def cmd_range(a):
    doc = station(a.station)
    tz = zone_of(a.tz)
    start = local_day(date(a.year, 1, 1), tz)[0]
    end = local_day(date(a.year, 12, 31), tz)[1]
    ex = extremes(doc, start - timedelta(days=1), end + timedelta(days=1))
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
    header(doc, f"{a.year}  high/low range across the year, m MLLW", tz)
    print(f"  {n} days, {len(inyear)} highs and lows\n")
    print(f"  median daily range   {median:.2f} m")
    print(f"  max daily range      {hi_day[1]:.2f} m  on {hi_day[0]}")
    print(f"  min daily range      {lo_day[1]:.2f} m  on {lo_day[0]}")
    print(f"  year span            {min(e[2] for e in inyear):+.2f} m to {max(e[2] for e in inyear):+.2f} m")
    print("\n  Use these for a site file's \"Typical range\" row: median as \"typical,\"")
    print("  max daily range as \"up to,\" year span as printed.")


def _moment(a, doc):
    tz = zone_of(a.tz)
    return tz, a.time.replace(tzinfo=tz).astimezone(timezone.utc)


def cmd_at(a):
    doc = station(a.station)
    tz, t = _moment(a, doc)
    h = height_at(doc, t)
    header(doc, f"{a.time:%Y-%m-%d %H:%M}  tide {h:+.2f} m MLLW", tz)
    print(f"  A feature X m below MLLW datum reads {h:+.2f} m {'deeper' if h >= 0 else 'shallower'} than X on the computer.")


def cmd_normalize(a):
    doc = station(a.station)
    tz, t = _moment(a, doc)
    h = height_at(doc, t)
    datum = a.depth - h
    header(doc, f"{a.time:%Y-%m-%d %H:%M}  tide {h:+.2f} m MLLW", tz)
    print(f"  observed depth      {a.depth:6.1f} m  (below the surface, as the computer read it)")
    print(f"  tide height        {h:+7.2f} m")
    print("  ---")
    print(f"  depth below MLLW    {datum:6.1f} m  <-- the comparable number. Log this.")
    print(f"\n  This is what to carry between dives. The {a.depth:.1f} m is only true at that tide.")


def cmd_project(a):
    doc = station(a.station)
    tz = zone_of(a.tz)
    start, end = local_day(a.date, tz)
    ex = [e for e in extremes(doc, start - timedelta(hours=1), end + timedelta(hours=1)) if _round(e[0], tz).date() == a.date]
    header(doc, f"{a.date}  a feature {a.datum_depth:.1f} m below MLLW datum", tz)
    for t, kind, h in ex:
        print(f"  {_round(t, tz):%H:%M}  {'HIGH' if kind == 'H' else 'LOW '}  tide {h:+.2f} m   ->  reads {a.datum_depth + h:5.1f} m below surface")
    hs = [e[2] for e in ex]
    print(f"\n  Across the day it swings {a.datum_depth + min(hs):.1f} m – {a.datum_depth + max(hs):.1f} m below the surface.")
    print("  Plan gas and ppO2 against the deepest, not the average.")


def cmd_fetch(a):
    st = station_list()["stations"]
    if a.all:
        want = sorted(st)
    elif a.near:
        lat, lon = a.near
        scale = math.cos(math.radians(lat))
        want = [sid for sid, s in sorted(st.items())
                if math.hypot((s["lat"] - lat) * 60.0, (s["lon"] - lon) * 60.0 * scale) * 1.852 <= a.km]
    elif a.station:
        want = a.station
    else:
        sys.exit("name stations, or pass --near LAT LON [--km R], or --all.")
    want += [st[s]["ref"] for s in want if s in st and st[s]["ref"] and st[s]["ref"] in st]
    todo = sorted({s for s in want if not os.path.exists(os.path.join(DB, f"{s}.json"))})
    print(f"{len(set(want)) - len(todo)} of {len(set(want))} already cached; downloading {len(todo)}.", flush=True)
    for k, sid in enumerate(todo, 1):
        doc = station(sid, quiet=True)
        print(f"  {k}/{len(todo)}  {sid}  {doc['name']}", flush=True)
        _time.sleep(a.pause)
    print("done.")


def compare(doc, day0, days, height_tol, time_tol):
    """One station against NOAA's live API over `days` from `day0`: the height every six
    minutes at a reference station, and every high and low at any station."""
    utc = timezone.utc
    q = {"product": "predictions", "application": "NOS.COOPS.TAC.WL", "station": doc["id"], "datum": "MLLW",
         "time_zone": "gmt", "units": "metric", "format": "json",
         "begin_date": day0.strftime("%Y%m%d"), "end_date": (day0 + timedelta(days=days - 1)).strftime("%Y%m%d")}

    def api(**extra):
        d = get(f"{DG}?{urllib.parse.urlencode({**q, **extra})}")
        rows = d.get("predictions")
        if not isinstance(rows, list) or not rows:
            return (d.get("error") or {}).get("message") or str(rows)
        return [(datetime.strptime(p["t"], "%Y-%m-%d %H:%M").replace(tzinfo=utc), p.get("type"), float(p["v"]))
                for p in rows]

    r = {"station": doc["id"], "type": doc["type"], "ok": True}
    ref = reference(doc)
    if doc["type"] != "S":
        rows = api()
        if isinstance(rows, str):
            return {**r, "ok": False, "error": rows.strip()}
        worst = tot = 0.0
        for t, _, v in rows:
            d = height(ref, t) - v
            worst = max(worst, abs(d))
            tot += d * d
        r.update(height_n=len(rows), height_worst=round(worst, 4), height_rms=round(math.sqrt(tot / len(rows)), 4))
        r["ok"] &= worst <= height_tol
    theirs = api(interval="hilo")
    if isinstance(theirs, str):
        return {**r, "ok": False, "error": theirs.strip()}
    start = datetime.combine(day0, time(0), utc)
    mine = extremes(doc, start - timedelta(hours=6), start + timedelta(days=days, hours=6))
    dt_worst = dv_worst = 0.0
    missed = skipped = 0
    o = doc.get("offsets") or {}
    near = timedelta(minutes=60 + max(abs(o.get("timeOffsetHighTide") or 0), abs(o.get("timeOffsetLowTide") or 0)))
    for t, kind, v in theirs:
        # The node factors change at the first hour of the UTC year, a small step in the curve;
        # a high or low sitting on the step is left out and counted.
        if abs(t - datetime(t.year + (t.month == 12), 1, 1, tzinfo=utc)) <= near:
            skipped += 1
            continue
        cands = [(abs((m[0] - t).total_seconds()) / 60, m) for m in mine if m[1] == kind[0]]
        if not cands or min(cands, key=lambda c: c[0])[0] > 90:
            missed += 1
            continue
        dt, m = min(cands, key=lambda c: c[0])
        # An extreme on a flat top moves minutes for a hair of height; judge it on the height.
        if dt > time_tol and doc["type"] != "S" and abs(height(ref, t) - m[2]) <= 0.003:
            dt = 0.0
        dt_worst = max(dt_worst, dt)
        dv_worst = max(dv_worst, abs(m[2] - v))
    r.update(events_n=len(theirs), time_worst=round(dt_worst, 1), event_worst=round(dv_worst, 4), unmatched=missed, new_year=skipped)
    r["ok"] &= dt_worst <= time_tol and dv_worst <= height_tol and missed == 0
    return r


def _line(r):
    if "error" in r:
        return [f"  NOAA: no predictions to compare with ({r['error']})"]
    out = []
    if "height_n" in r:
        out.append(f"  height, {r['height_n']} six-minute values: worst difference {r['height_worst']:.3f} m, "
                   f"rms {r['height_rms']:.3f} m")
    out.append(f"  events, {r['events_n']} highs and lows: worst time difference {r['time_worst']:.1f} min, "
               f"worst height difference {r['event_worst']:.3f} m, {r['unmatched']} unmatched")
    if r.get("new_year"):
        out.append(f"  {r['new_year']} at the turn of the UTC year left out")
    return out


def cmd_verify(a):
    """Compare with NOAA's own predictions, read live from its API."""
    if a.all:
        return verify_all(a)
    if not a.station:
        sys.exit("name a station, or pass --all.")
    doc = station(a.station)
    print(f"{doc['id']}  {doc['name']}  {a.date} for {a.days} days, against NOAA's API\n")
    r = compare(doc, a.date, a.days, a.height_tol, a.time_tol)
    print("\n".join(_line(r)))
    print("\n  PASS" if r["ok"] else f"\n  FAIL: limits are {a.height_tol} m and {a.time_tol} min. The cached constants "
          "may be older than NOAA's; delete the station's file to fetch them again.")
    sys.exit(0 if r["ok"] else 1)


def verify_all(a):
    """Every cached station, one result per line in the cache folder's _verify.jsonl. A
    station already in that file is skipped, so a stopped run picks up where it left off;
    delete the file to start over."""
    done = {}
    if os.path.exists(REPORT):
        with open(REPORT) as f:
            for line in f:
                r = json.loads(line)
                done[r["station"]] = r
    todo = [sid for sid in sorted(station_list()["stations"])
            if os.path.exists(os.path.join(DB, f"{sid}.json")) and sid not in done]
    print(f"{len(done)} stations already verified; {len(todo)} to go, {a.days} days from {a.date}.", flush=True)
    for k, sid in enumerate(todo, 1):
        doc = station(sid)
        try:
            r = compare(doc, a.date, a.days, a.height_tol, a.time_tol)
        except SystemExit as e:
            if str(e).startswith("NOAA:"):  # a failed request stops the run, to be resumed later
                raise
            r = {"station": sid, "type": doc["type"], "ok": False, "error": str(e)}
        r.update(name=doc["name"], date=a.date.isoformat(), days=a.days)
        with open(REPORT, "a") as f:
            f.write(json.dumps(r) + "\n")
        done[sid] = r
        if k % 25 == 0 or not r["ok"]:
            print(f"  {k}/{len(todo)}  {sid} {doc['type']}  {'ok' if r['ok'] else 'FAIL'}", flush=True)
        _time.sleep(a.pause)
    print()
    for kind, label in (("R", "reference"), ("S", "subordinate")):
        rs = [r for r in done.values() if r["type"] == kind]
        bad = [r for r in rs if not r["ok"]]
        print(f"  {label}: {len(rs) - len(bad)} of {len(rs)} stations within {a.height_tol} m and {a.time_tol} min")
    print(f"  results: {os.path.relpath(REPORT, ROOT)}")


def when(s):
    return datetime.strptime(s, "%Y-%m-%d %H:%M")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    def zoned(sp):
        sp.add_argument("station")
        sp.add_argument("--tz", required=True, metavar="IANA_ZONE", help="the site's time zone, the `tz` in its JSON")

    s = sub.add_parser("stations", help="find tide stations near a site")
    s.add_argument("--near", nargs=2, type=float, metavar=("LAT", "LON"), required=True)
    s.add_argument("-n", type=int, default=6)
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

    s = sub.add_parser("normalize", help="observed depth -> depth below MLLW datum")
    zoned(s)
    s.add_argument("--time", type=when, required=True, metavar='"YYYY-MM-DD HH:MM"')
    s.add_argument("--depth", type=float, required=True, help="metres, as the computer read it")
    s.set_defaults(fn=cmd_normalize)

    s = sub.add_parser("project", help="datum depth -> depth below surface through the day")
    zoned(s)
    s.add_argument("--datum-depth", type=float, required=True, help="metres below MLLW")
    s.add_argument("--date", type=date.fromisoformat, default=date.today())
    s.set_defaults(fn=cmd_project)

    s = sub.add_parser("fetch", help="cache stations ahead of time")
    s.add_argument("station", nargs="*")
    s.add_argument("--near", nargs=2, type=float, metavar=("LAT", "LON"))
    s.add_argument("--km", type=float, default=50.0, help="radius for --near, default 50")
    s.add_argument("--all", action="store_true", help="every station NOAA lists")
    s.add_argument("--pause", type=float, default=0.3, help="seconds between stations, default 0.3")
    s.set_defaults(fn=cmd_fetch)

    s = sub.add_parser("verify", help="compare with NOAA's live API")
    s.add_argument("station", nargs="?")
    s.add_argument("--all", action="store_true", help="every cached station")
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

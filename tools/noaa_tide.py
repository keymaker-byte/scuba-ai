#!/usr/bin/env python3
"""NOAA CO-OPS tide predictions, in metres against MLLW.

  noaa_tide.py stations --near LAT LON                       tide stations near a site
  noaa_tide.py predict STATION [--date D]                    high/low water for the day
  noaa_tide.py at STATION --time "D HH:MM"                   tide height at a moment
  noaa_tide.py range STATION [--year Y]                      median/max/min daily range and year span
  noaa_tide.py project STATION --datum-depth X [--date D]    datum depth to depth below surface, all day
  noaa_tide.py normalize STATION --time T --depth D          observed depth to depth below MLLW

"""
import argparse
import json
import math
import sys
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta

MD = "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations"
DG = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"


def get(url):
    # NOAA returns its JSON error body with a 400 status, so read it rather than raise.
    try:
        with urllib.request.urlopen(url, timeout=45) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read())
        except Exception:
            raise e


def predictions(station, day, interval=None, end=None, strict=True):
    q = {
        "product": "predictions",
        "application": "NOS.COOPS.TAC.WL",
        "begin_date": day.strftime("%Y%m%d"),
        "end_date": (end or day).strftime("%Y%m%d"),
        "station": station,
        "datum": "MLLW",
        "time_zone": "lst_ldt",
        "units": "metric",
        "format": "json",
    }
    if interval:
        q["interval"] = interval
    d = get(f"{DG}?{urllib.parse.urlencode(q)}")
    if "error" in d:
        if strict:
            sys.exit(f"NOAA: {d['error']['message'].strip()}")
        return None
    return d["predictions"]


def height_at(station, when):
    """Tide height (m, MLLW) at a moment.

    Reference stations publish a 6-minute series — interpolate that linearly. Subordinate
    stations (Mukilteo among them) publish only high/low water, so fall back to the harmonic
    approximation between successive extremes: the tide swings as a half-cosine from one
    extreme to the next. That is the smooth form of the rule of twelfths, and it is good to a
    few centimetres in the Sound — well inside the precision a dive computer's depth deserves.
    """
    day = when.date()
    span = (day - timedelta(days=1), day + timedelta(days=1))

    fine = predictions(station, span[0], end=span[1], strict=False)
    if fine:
        series = [(datetime.strptime(p["t"], "%Y-%m-%d %H:%M"), float(p["v"])) for p in fine]
        before = [p for p in series if p[0] <= when]
        after = [p for p in series if p[0] >= when]
        if before and after:
            (t0, v0), (t1, v1) = before[-1], after[0]
            if t0 == t1:
                return v0
            frac = (when - t0).total_seconds() / (t1 - t0).total_seconds()
            return v0 + frac * (v1 - v0)

    hilo = predictions(station, span[0], interval="hilo", end=span[1])
    series = [(datetime.strptime(p["t"], "%Y-%m-%d %H:%M"), float(p["v"])) for p in hilo]
    before = [p for p in series if p[0] <= when]
    after = [p for p in series if p[0] >= when]
    if not before or not after:
        sys.exit(f"{when:%Y-%m-%d %H:%M} is not bracketed by predicted extremes at {station}.")
    (t0, v0), (t1, v1) = before[-1], after[0]
    if t0 == t1:
        return v0
    frac = (when - t0).total_seconds() / (t1 - t0).total_seconds()
    return (v0 + v1) / 2 + (v0 - v1) / 2 * math.cos(math.pi * frac)


def when(s):
    return datetime.strptime(s, "%Y-%m-%d %H:%M")


def cmd_stations(a):
    all_st = get(f"{MD}.json?type=tidepredictions")["stations"]
    lat, lon = a.near
    scale = math.cos(math.radians(lat))
    uniq = {}
    for s in all_st:
        if s["id"] in uniq:
            continue
        dy = (s["lat"] - lat) * 60.0
        dx = (s["lng"] - lon) * 60.0 * scale
        s["_nm"] = math.hypot(dx, dy)
        uniq[s["id"]] = s
    near = sorted(uniq.values(), key=lambda s: s["_nm"])[: a.n]
    print(f"Tide-prediction stations near {lat:.4f}, {lon:.4f}:\n")
    for s in near:
        print(f"  {s['id']:<10} {s['_nm'] * 1.852:5.1f} km  {s['name']}")
    print("\nNearest is usually right for tide height — unlike currents, water level varies")
    print("smoothly. But a station across a constriction can lag; prefer one on the same shore.")


def day_extremes(hilo, day):
    """The day's highs and lows. A day holding only one kind (a single extreme, or two of the
    same kind either side of midnight) also takes the extreme just before and just after it, so
    its range always spans a low to a high."""
    idx = [i for i, p in enumerate(hilo) if p["t"][:10] == day]
    if not idx:
        return []
    if len({hilo[i]["type"] for i in idx}) < 2:
        idx = [i for i in (idx[0] - 1, *idx, idx[-1] + 1) if 0 <= i < len(hilo)]
    return [hilo[i] for i in idx]


def cmd_predict(a):
    hilo = predictions(a.station, a.date - timedelta(days=1), "hilo", end=a.date + timedelta(days=1))
    day = a.date.isoformat()
    pts = day_extremes(hilo, day)
    print(f"{a.station}  {a.date}  high/low water, m above MLLW, local time\n")
    for p in pts:
        kind = "HIGH" if p["type"] == "H" else "LOW "
        when = p["t"][11:] if p["t"][:10] == day else p["t"]
        print(f"  {when}  {kind}  {float(p['v']):+.2f} m")
    lo = min(float(p["v"]) for p in pts)
    hi = max(float(p["v"]) for p in pts)
    print(f"\n  range {hi - lo:.2f} m — a fixed seabed feature reads {hi - lo:.2f} m deeper at the high than the low.")


def cmd_range(a):
    year_start = date(a.year, 1, 1)
    year_end = date(a.year, 12, 31)
    hilo = predictions(a.station, year_start - timedelta(days=1), "hilo", end=year_end + timedelta(days=1))
    days = sorted({p["t"][:10] for p in hilo if p["t"][:4] == str(a.year)})
    daily = []
    for d in days:
        vs = [float(p["v"]) for p in day_extremes(hilo, d)]
        daily.append((d, max(vs) - min(vs)))
    daily.sort(key=lambda x: x[1])
    hilo = [p for p in hilo if p["t"][:4] == str(a.year)]
    n = len(daily)
    median = daily[n // 2][1] if n % 2 else (daily[n // 2 - 1][1] + daily[n // 2][1]) / 2
    lo_day, hi_day = daily[0], daily[-1]

    all_vals = [float(p["v"]) for p in hilo]
    print(f"{a.station}  {a.year}  high/low range across the year, m MLLW\n")
    print(f"  {n} days, {len(hilo)} highs and lows, one API call\n")
    print(f"  median daily range   {median:.2f} m")
    print(f"  max daily range      {hi_day[1]:.2f} m  on {hi_day[0]}")
    print(f"  min daily range      {lo_day[1]:.2f} m  on {lo_day[0]}")
    print(f"  year span            {min(all_vals):+.2f} m to {max(all_vals):+.2f} m")
    print("\n  Use these for a site file's \"Typical range\" row: median as \"typical,\"")
    print("  max daily range as \"up to,\" year span as printed.")


def cmd_at(a):
    h = height_at(a.station, a.time)
    print(f"{a.station}  {a.time:%Y-%m-%d %H:%M}  tide {h:+.2f} m MLLW")
    print(f"\n  A feature X m below MLLW datum reads {h:+.2f} m {'deeper' if h >= 0 else 'shallower'} than X on the computer.")


def cmd_normalize(a):
    h = height_at(a.station, a.time)
    datum = a.depth - h
    print(f"{a.station}  {a.time:%Y-%m-%d %H:%M}  tide {h:+.2f} m MLLW\n")
    print(f"  observed depth      {a.depth:6.1f} m  (below the surface, as the computer read it)")
    print(f"  tide height        {h:+7.2f} m")
    print(f"  ---")
    print(f"  depth below MLLW    {datum:6.1f} m  <-- the comparable number. Log this.")
    print(f"\n  This is what to carry between dives. The {a.depth:.1f} m is only true at that tide.")


def cmd_project(a):
    hilo = predictions(a.station, a.date, "hilo")
    print(f"{a.station}  {a.date}  a feature {a.datum_depth:.1f} m below MLLW datum\n")
    for p in hilo:
        kind = "HIGH" if p["type"] == "H" else "LOW "
        h = float(p["v"])
        print(f"  {p['t'][11:]}  {kind}  tide {h:+.2f} m   ->  reads {a.datum_depth + h:5.1f} m below surface")
    hs = [float(p["v"]) for p in hilo]
    print(f"\n  Across the day it swings {a.datum_depth + min(hs):.1f} m – {a.datum_depth + max(hs):.1f} m below the surface.")
    print("  Plan gas and ppO2 against the deepest, not the average.")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("stations", help="find tide stations near a site")
    s.add_argument("--near", nargs=2, type=float, metavar=("LAT", "LON"), required=True)
    s.add_argument("-n", type=int, default=6)
    s.set_defaults(fn=cmd_stations)

    s = sub.add_parser("predict", help="high/low water for the day")
    s.add_argument("station")
    s.add_argument("--date", type=date.fromisoformat, default=date.today())
    s.set_defaults(fn=cmd_predict)

    s = sub.add_parser("range", help="exact median/max/min daily range and span, whole year in one call")
    s.add_argument("station")
    s.add_argument("--year", type=int, default=date.today().year)
    s.set_defaults(fn=cmd_range)

    s = sub.add_parser("at", help="tide height at a moment")
    s.add_argument("station")
    s.add_argument("--time", type=when, required=True, metavar='"YYYY-MM-DD HH:MM"')
    s.set_defaults(fn=cmd_at)

    s = sub.add_parser("normalize", help="observed depth -> depth below MLLW datum")
    s.add_argument("station")
    s.add_argument("--time", type=when, required=True, metavar='"YYYY-MM-DD HH:MM"')
    s.add_argument("--depth", type=float, required=True, help="metres, as the computer read it")
    s.set_defaults(fn=cmd_normalize)

    s = sub.add_parser("project", help="datum depth -> depth below surface through the day")
    s.add_argument("station")
    s.add_argument("--datum-depth", type=float, required=True, help="metres below MLLW")
    s.add_argument("--date", type=date.fromisoformat, default=date.today())
    s.set_defaults(fn=cmd_project)

    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()

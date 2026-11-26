#!/usr/bin/env python3
"""Seabed depth at any point the workspace dives, from whichever bathymetry covers it, below the
datum of the water there: MLLW in US tidal water, CHS Chart Datum in Canadian, a lake's own surface in a lake,
and none on Bonaire's reef, where it is a plain observed depth.

  depth.py at LAT LON [--datum K] [--verify]   the depth at a point, and the source and datum that gave it
  depth.py at --file F [--verify]              the same at a site JSON's lat and lon, on its seabed_datum,
                                               checked against its seabed_m and seabed_datum
  depth.py transect LAT1 LON1 LAT2 LON2 [--step M] [--datum K]   the depth every few metres along a line
  depth.py fetch S W N E [S W N E ...]    download every source's data touching the boxes, ahead of time
  depth.py selftest                       each source's own checks
"""
import argparse
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import datums  # noqa: E402
from lib.depth import Refused, answer_on, sources  # noqa: E402


def cmd_at(a):
    seabed = datum = None
    if a.file:
        try:
            with open(a.file) as f:
                doc = json.load(f)
        except (OSError, ValueError) as e:
            sys.exit(f"{a.file}: cannot read it as JSON ({e}).")
        if not all(isinstance(doc.get(k), (int, float)) for k in ("lat", "lon")):
            sys.exit(f"{a.file}: needs numeric lat and lon.")
        lat, lon, seabed = doc["lat"], doc["lon"], doc.get("seabed_m")
        if doc.get("seabed_datum") is not None:
            datum = datums.check(doc["seabed_datum"], f"{a.file}: seabed_datum")
    elif a.lat is None or a.lon is None:
        sys.exit("give LAT LON, or --file with a site JSON")
    else:
        lat, lon = a.lat, a.lon
    if a.datum:
        datums.check(a.datum)
        if datum and a.datum != datum:
            sys.exit(f"--datum {a.datum} disagrees with {a.file}'s seabed_datum, {datum}.")
        datum = a.datum
    try:
        src, r = answer_on(lat, lon, datum)
    except Refused as e:
        sys.exit(str(e))
    print(f"{lat}, {lon}")
    if r["depth"] is None:
        print(f"  no depth: {r['why']}.")
    else:
        print(f"  {'lake bed' if r['water'] == 'lake' else 'seabed'} {r['depth']:.1f} m below {r['datum']}  "
              f"[datum {r['key']}]")
        print(f"  ({r['detail']})")
    print(f"  source {r['source']}, read from this machine")
    ok = True
    if a.file:
        if seabed is not None:
            if r["depth"] is None:
                print(f"  the site JSON's seabed_m is {seabed:g} m, and the tool gives no depth here")
                ok = False
            elif round(seabed, 1) != round(r["depth"], 1):  # seabed_m is written to 0.1 m
                print(f"  the site JSON's seabed_m is {seabed:g} m, and the tool gives {r['depth']:.1f} m")
                ok = False
            else:
                print(f"  the site JSON's seabed_m, {seabed:g} m, agrees")
        if datum is None:
            print(f"  the site JSON has no seabed_datum; this depth is on {r['key']}. Add \"seabed_datum\": \"{r['key']}\".")
            ok = False
        else:
            print(f"  the site JSON's seabed_datum, {datum}, agrees")
    if a.verify:
        ok = src.verify(lat, lon, r) and ok
    sys.exit(0 if ok else 1)


def cmd_transect(a):
    """The depth every --step metres along a straight line, each point answered as `at` answers it."""
    if a.datum:
        datums.check(a.datum)
    dy = (a.lat2 - a.lat1) * 111320
    dx = (a.lon2 - a.lon1) * 111320 * math.cos(math.radians((a.lat1 + a.lat2) / 2))
    length = math.hypot(dx, dy)
    n = max(1, round(length / a.step))
    print(f"{a.lat1}, {a.lon1} to {a.lat2}, {a.lon2}: {length:.0f} m toward {math.degrees(math.atan2(dx, dy)) % 360:.0f}°")
    sources_seen = []
    for i in range(n + 1):
        t = i / n
        lat, lon = round(a.lat1 + t * (a.lat2 - a.lat1), 6), round(a.lon1 + t * (a.lon2 - a.lon1), 6)
        try:
            src, r = answer_on(lat, lon, a.datum)
        except Refused as e:
            shown = f"no depth: {e}"
        else:
            if r["depth"] is None:
                shown = f"no depth: {r['why']}"
            else:
                shown = f"{r['depth']:5.1f} m below {r['datum']}  [datum {r['key']}]"
            if r["source"] not in sources_seen:
                sources_seen.append(r["source"])
        print(f"  {t * length:5.0f} m  {lat:10.6f}  {lon:11.6f}  {shown}")
    for s in sources_seen:
        print(f"  source {s}, read from this machine")


def cmd_fetch(a):
    if not a.box or len(a.box) % 4:
        sys.exit("give one or more boxes as S W N E")
    boxes = [tuple(a.box[i:i + 4]) for i in range(0, len(a.box), 4)]
    failed = 0
    for s in sources():
        print(f"== {s.name}")
        failed += s.fetch(boxes, a.workers)
    sys.exit(1 if failed else 0)


def cmd_selftest(a):
    ok = True
    for s in sources():
        ok = s.selftest() and ok
    sys.exit(0 if ok else 1)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    at = sub.add_parser("at", help="the depth at a point")
    at.add_argument("lat", type=float, nargs="?")
    at.add_argument("lon", type=float, nargs="?")
    at.add_argument("--file", help="a site JSON: read its lat, lon and seabed_datum, and check its seabed_m")
    at.add_argument("--datum", metavar="K", help="answer only on this datum: " + ", ".join(datums.MEANING))
    at.add_argument("--verify", action="store_true", help="compare the source's data with its live service")
    at.set_defaults(fn=cmd_at)
    tr = sub.add_parser("transect", help="the depth every few metres along a straight line")
    for k in ("lat1", "lon1", "lat2", "lon2"):
        tr.add_argument(k, type=float)
    tr.add_argument("--step", type=float, default=10, help="metres between points, default 10")
    tr.add_argument("--datum", metavar="K", help="answer only on this datum: " + ", ".join(datums.MEANING))
    tr.set_defaults(fn=cmd_transect)
    fe = sub.add_parser("fetch", help="download every source's data touching one or more boxes")
    fe.add_argument("box", type=float, nargs="+", metavar="S W N E")
    fe.add_argument("--workers", type=int, default=6, help="downloads at once, default 6")
    fe.set_defaults(fn=cmd_fetch)
    st = sub.add_parser("selftest", help="each source's own checks")
    st.set_defaults(fn=cmd_selftest)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Seabed depth at any point the workspace dives, from whichever bathymetry covers it, below the
datum of the water there: MLLW in US tidal water, CHS Chart Datum in Canadian, a lake's own surface in a lake.

  depth.py at LAT LON [--verify]          the depth at a point, and the source that gave it
  depth.py at --file F [--verify]         the same at a site JSON's lat and lon, checked against its seabed_m
  depth.py fetch S W N E [S W N E ...]    download every source's data touching the boxes, ahead of time
  depth.py selftest                       each source's own checks
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.depth import Refused, source_for, sources  # noqa: E402


def cmd_at(a):
    seabed = None
    if a.file:
        try:
            with open(a.file) as f:
                doc = json.load(f)
        except (OSError, ValueError) as e:
            sys.exit(f"{a.file}: cannot read it as JSON ({e}).")
        if not all(isinstance(doc.get(k), (int, float)) for k in ("lat", "lon")):
            sys.exit(f"{a.file}: needs numeric lat and lon.")
        lat, lon, seabed = doc["lat"], doc["lon"], doc.get("seabed_m")
    elif a.lat is None or a.lon is None:
        sys.exit("give LAT LON, or --file with a site JSON")
    else:
        lat, lon = a.lat, a.lon
    try:
        src = source_for(lat, lon)
    except Refused as e:
        sys.exit(str(e))
    r = src.answer(lat, lon)
    print(f"{lat}, {lon}")
    if r["depth"] is None:
        print(f"  no depth: {r['why']}.")
    else:
        print(f"  {'lake bed' if r['water'] == 'lake' else 'seabed'} {r['depth']:.1f} m below {r['datum']}")
        print(f"  ({r['detail']})")
    print(f"  source {r['source']}, read from this machine")
    ok = True
    if seabed is not None:
        if r["depth"] is None:
            print(f"  the site JSON's seabed_m is {seabed:g} m, and the tool gives no depth here")
            ok = False
        elif round(seabed, 1) != round(r["depth"], 1):  # seabed_m is written to 0.1 m
            print(f"  the site JSON's seabed_m is {seabed:g} m, and the tool gives {r['depth']:.1f} m")
            ok = False
        else:
            print(f"  the site JSON's seabed_m, {seabed:g} m, agrees")
    if a.verify:
        ok = src.verify(lat, lon, r) and ok
    sys.exit(0 if ok else 1)


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
    at.add_argument("--file", help="a site JSON: read its lat and lon, and check its seabed_m")
    at.add_argument("--verify", action="store_true", help="compare the source's data with its live service")
    at.set_defaults(fn=cmd_at)
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

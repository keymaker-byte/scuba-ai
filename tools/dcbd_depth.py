#!/usr/bin/env python3
"""Seabed depth on Bonaire's coastal reef from the 2 m coastal bathymetry (Meesters 2020, DCBD).

  dcbd_depth.py at LAT LON [--radius M]                     depth at a point, and the spread around it
  dcbd_depth.py transect LAT1 LON1 LAT2 LON2 [--step M]     depth every few metres along a line
"""
import argparse
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from lib.dcbd import grid, nearest_data, utm  # noqa: E402

ROOT = os.path.dirname(HERE)


def _cfg(key, default):
    """Read this tool's section of tool-config.json; missing file or key -> default."""
    try:
        with open(os.path.join(ROOT, "tool-config.json")) as f:
            return json.load(f).get("dcbd_depth", {}).get(key, default)
    except (OSError, ValueError):
        return default


# --- queries ------------------------------------------------------------------------------

COMPASS = "N NNE NE ENE E ESE SE SSE S SSW SW WSW W WNW NW NNW".split()


def _bearing(dx, dy):
    b = math.degrees(math.atan2(dx, dy)) % 360
    return f"{b:.0f}° ({COMPASS[round(b / 22.5) % 16]})"


def _depth(v):
    return f"+{v:.1f} m, ABOVE WATER" if v > 0 else f"{-v:.1f} m"


def cmd_at(a):
    g = grid()
    x, y = utm(a.lat, a.lon)
    print(f"{a.lat}, {a.lon}")
    p = g.pixel(x, y)
    if p is None:
        sys.exit("  outside the Bonaire coastal grid: no data here. Use emodnet_depth for open water.")
    r, c = p
    v = g.value(r, c)
    if v is not None:
        print(f"  seabed {_depth(v)}  [DCBD coastal bathymetry, 2 m grid]")
    else:
        print("  no data at this pixel: land, water deeper than the survey reached, or unsurveyed")
        near = nearest_data(g, x, y, r, c, a.search)
        if near:
            d, dx, dy, nv = near
            print(f"  nearest data {d:.0f} m away toward {_bearing(dx, dy)}, seabed {_depth(nv)}")
        else:
            print(f"  no data within {a.search:.0f} m: inland, open water past the reef, or unsurveyed")
    k = int(a.radius / g.sx)
    vals = []
    for rr in range(max(0, r - k), min(g.height, r + k + 1)):
        for cc in range(max(0, c - k), min(g.width, c + k + 1)):
            px, py = g.centre(rr, cc)
            if math.hypot(px - x, py - y) <= a.radius:
                vals.append(g.value(rr, cc))
    have = [w for w in vals if w is not None]
    if have:
        line = f"  within {a.radius:.0f} m: {-max(have):.1f} to {-min(have):.1f} m"
        if len(have) < len(vals):
            line += f", {100 * (len(vals) - len(have)) / len(vals):.0f}% of it without data (land, deeper, or unsurveyed)"
        print(line)


def cmd_transect(a):
    g = grid()
    x1, y1 = utm(a.lat1, a.lon1)
    x2, y2 = utm(a.lat2, a.lon2)
    length = math.hypot(x2 - x1, y2 - y1)
    n = max(1, round(length / a.step))
    print(f"{a.lat1}, {a.lon1} to {a.lat2}, {a.lon2}: {length:.0f} m toward {_bearing(x2 - x1, y2 - y1)}")
    print(f"  {'dist':>6}  {'lat':>10}  {'lon':>11}  seabed")
    for i in range(n + 1):
        t = i / n
        lat, lon = a.lat1 + t * (a.lat2 - a.lat1), a.lon1 + t * (a.lon2 - a.lon1)
        p = g.pixel(*utm(lat, lon))
        v = g.value(*p) if p else None
        shown = _depth(v) if v is not None else ("outside grid" if p is None else "no data (land, deeper, or unsurveyed)")
        print(f"  {t * length:5.0f}m  {lat:10.6f}  {lon:11.6f}  {shown}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("at", help="depth at a point, and the spread around it")
    s.add_argument("lat", type=float)
    s.add_argument("lon", type=float)
    s.add_argument("--radius", type=float, default=_cfg("radius_m", 10),
                   help="metres around the point to report the shallowest and deepest pixel (default 10)")
    s.add_argument("--search", type=float, default=_cfg("search_m", 100),
                   help="on a pixel with no data, metres to search for the nearest one with data (default 100)")
    s.set_defaults(fn=cmd_at)
    s = sub.add_parser("transect", help="depth every few metres along a straight line")
    for k in ("lat1", "lon1", "lat2", "lon2"):
        s.add_argument(k, type=float)
    s.add_argument("--step", type=float, default=_cfg("step_m", 10), help="metres between samples (default 10)")
    s.set_defaults(fn=cmd_transect)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()

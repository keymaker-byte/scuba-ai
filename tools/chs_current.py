#!/usr/bin/env python3
"""Canadian Hydrographic Service current predictions: slack, max flood/ebb, and diveable windows.

  chs_current.py stations --near LAT LON            CHS current stations near a site
  chs_current.py predict STATION [--date D]         slack / max flood / max ebb
  chs_current.py window STATION [--date D]          diveable windows under a speed threshold

STATION is the CHS five-digit station code, e.g. 07100.
"""
import argparse
import json
import math
import os
import sys
import urllib.parse
import urllib.request
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

API = "https://api-iwls.dfo-mpo.gc.ca/api/v1"
KN = 0.514444  # m/s per knot; CHS publishes current speed in knots


def _cfg(key, default):
    """Read this tool's section of tool-config.json; missing file or key -> default."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        with open(os.path.join(root, "tool-config.json")) as f:
            return json.load(f).get("chs_current", {}).get(key, default)
    except (OSError, ValueError):
        return default


def get(path, **q):
    url = f"{API}/{path}" + (f"?{urllib.parse.urlencode(q)}" if q else "")
    try:
        with urllib.request.urlopen(url, timeout=45) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"CHS: HTTP {e.code} for {url}")
    except urllib.error.URLError as e:
        sys.exit(f"CHS: unreachable ({e.reason})")


def current_stations():
    return get("stations", **{"time-series-code": "wcsp1"})


def station(code):
    for s in current_stations():
        if s["code"] == code:
            return get(f"stations/{s['id']}/metadata")
    sys.exit(f"CHS: no current-prediction station with code {code}; list them with `stations --near`.")


def zone(meta, override):
    return ZoneInfo(override or meta.get("timeZoneCode") or _cfg("default_tz", "America/Vancouver"))


def series(meta, code, day, tz):
    """One local day of a time series, as (local datetime, entry) pairs."""
    ts = next((t for t in meta["timeSeries"] if t["code"] == code), None)
    if not ts:
        sys.exit(f"CHS: station {meta['code']} publishes no {code} series.")
    start = datetime.combine(day, time(0), tz)
    end = start + timedelta(days=1)
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    d = get(f"stations/{meta['id']}/data", **{
        "time-series-code": code,
        "from": start.astimezone(timezone.utc).strftime(fmt),
        "to": end.astimezone(timezone.utc).strftime(fmt),
    })
    out = []
    for e in d:
        t = datetime.strptime(e["eventDate"], fmt).replace(tzinfo=timezone.utc).astimezone(tz)
        if start <= t < end:
            out.append((t, e))
    if not out:
        sys.exit(f"CHS: no {code} predictions for {meta['code']} on {day}.")
    return out


def header(meta, day, tz):
    print(f"{meta['code']}  {meta['officialName']}  {day}  ({tz.key})")
    print(f"  {meta['latitude']:.4f}, {meta['longitude']:.4f}   "
          f"flood {meta.get('floodDirection', '?')}°   ebb {meta.get('ebbDirection', '?')}°\n")


def cmd_stations(a):
    lat, lon = a.near
    scale = math.cos(math.radians(lat))
    rows = []
    for s in current_stations():
        dy = (s["latitude"] - lat) * 60.0
        dx = (s["longitude"] - lon) * 60.0 * scale
        rows.append((math.hypot(dx, dy) * 1.852, s))
    rows.sort(key=lambda r: r[0])
    print(f"CHS current-prediction stations near {lat:.4f}, {lon:.4f}:\n")
    for km, s in rows[: a.n]:
        print(f"  {s['code']:<7} {km:6.1f} km  {s['officialName']}")
    print("\nNearest is not automatically the governing station — pick the one whose water is")
    print("hydraulically connected to the site, then verify the offset in the water.")


def cmd_predict(a):
    meta = station(a.station)
    tz = zone(meta, a.tz)
    header(meta, a.date, tz)
    for t, e in series(meta, "wcp1-events", a.date, tz):
        q = e["qualifier"]
        if q == "SLACK":
            print(f"  {t:%H:%M}  SLACK")
        else:
            kind = "flood" if q == "EXTREMA_FLOOD" else "ebb"
            v = e["value"] * KN * (1 if kind == "flood" else -1)
            print(f"  {t:%H:%M}  {kind:<5} {v:+.2f} m/s")


def cmd_window(a):
    meta = station(a.station)
    tz = zone(meta, a.tz)
    pts = [(t, e["value"] * KN) for t, e in series(meta, "wcsp1", a.date, tz)]
    lim = a.max_speed
    header(meta, a.date, tz)
    print(f"  windows with current <= {lim:.2f} m/s\n")

    def cross(p, q):
        """Time the speed crosses the limit between two samples, by linear interpolation."""
        (t0, v0), (t1, v1) = p, q
        f = (lim - v0) / (v1 - v0) if v1 != v0 else 0.0
        return t0 + (t1 - t0) * f

    runs, start, peak = [], None, 0.0
    for i, (t, v) in enumerate(pts):
        if v <= lim:
            if start is None:
                start = pts[0][0] if i == 0 else cross(pts[i - 1], pts[i])
                peak = 0.0
            peak = max(peak, v)
        elif start is not None:
            runs.append((start, cross(pts[i - 1], pts[i]), peak))
            start = None
    if start is not None:
        runs.append((start, pts[-1][0], peak))

    if not runs:
        print(f"  none — current never drops below {lim:.2f} m/s. Not a dive day here.")
        return
    for t0, t1, pk in runs:
        mins = int((t1 - t0).total_seconds() // 60)
        flag = "  <-- tight" if mins < 40 else ""
        print(f"  {t0:%H:%M} - {t1:%H:%M}   {mins:>3} min   peak {pk:.2f} m/s{flag}")
    print("\n  Times are AT THE STATION. Apply the site offset, and pad it until observed.")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("stations", help="find CHS current stations near a site")
    s.add_argument("--near", nargs=2, type=float, metavar=("LAT", "LON"), required=True)
    s.add_argument("-n", type=int, default=6)
    s.set_defaults(fn=cmd_stations)

    def dated(sp):
        sp.add_argument("station", help="CHS five-digit station code, e.g. 07100")
        sp.add_argument("--date", type=date.fromisoformat, default=date.today())
        sp.add_argument("--tz", help="IANA zone for the output; default is the station's own zone")

    s = sub.add_parser("predict", help="slack / max flood / max ebb")
    dated(s)
    s.set_defaults(fn=cmd_predict)

    s = sub.add_parser("window", help="diveable slack windows")
    dated(s)
    _ms = _cfg("max_speed_ms", 0.25)
    s.add_argument("--max-speed", type=float, default=_ms, help=f"m/s, default {_ms}")
    s.set_defaults(fn=cmd_window)

    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()

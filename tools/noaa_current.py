#!/usr/bin/env python3
"""NOAA current predictions, for any station in its network. Metric (m/s, metres).

  stations --near LAT LON        find live current-prediction stations near a dive site
  bins STATION                   which bins actually publish predictions, and at what depth
  predict STATION [--date D]     slack / max flood / max ebb
  window  STATION [--date D]     diveable slack windows under a speed threshold

Currents are only published for a few bins per station, and the default bin is usually
near-surface. Water at your depth can turn at a different time. Pass --bin explicitly,
choosing the published bin nearest YOUR working depth — not the deepest one, which may be
water you will never dive.
"""
import argparse
import json
import math
import os
import sys
import urllib.parse
import urllib.request
from datetime import date, datetime

MD = "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations"
DG = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
KN = 51.44  # cm/s per knot


def _cfg(key, default):
    """Read this tool's section of tool-config.json; missing file or key -> default."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        with open(os.path.join(root, "tool-config.json")) as f:
            return json.load(f).get("noaa_current", {}).get(key, default)
    except (OSError, ValueError):
        return default


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


def predictions(station, day, bin_=None, interval=None):
    q = {
        "product": "currents_predictions",
        "application": "NOS.COOPS.TAC.CUR",
        "begin_date": day.strftime("%Y%m%d"),
        "end_date": day.strftime("%Y%m%d"),
        "station": station,
        "time_zone": "lst_ldt",
        "units": "metric",
        "format": "json",
    }
    if interval:
        q["interval"] = interval
    if bin_:
        q["bin"] = str(bin_)
    d = get(f"{DG}?{urllib.parse.urlencode(q)}")
    if "error" in d:
        sys.exit(f"NOAA: {d['error']['message'].strip()}")
    return d["current_predictions"]["cp"]


def speed(c):
    """Signed along-channel speed, m/s. Positive = flood."""
    return float(c["Velocity_Major"]) / 100.0


def cmd_stations(a):
    all_st = get(f"{MD}.json?type=currentpredictions")["stations"]
    lat, lon = a.near
    scale = math.cos(math.radians(lat))
    uniq = {}  # stations are listed once per bin; collapse to one entry per station
    for s in all_st:
        if s["id"] in uniq:
            continue
        dy = (s["lat"] - lat) * 60.0
        dx = (s["lng"] - lon) * 60.0 * scale
        s["_nm"] = math.hypot(dx, dy)
        uniq[s["id"]] = s
    near = sorted(uniq.values(), key=lambda s: s["_nm"])[: a.n]
    print(f"Live current-prediction stations near {lat:.4f}, {lon:.4f}:\n")
    for s in near:
        print(f"  {s['id']:<10} {s['_nm'] * 1.852:5.1f} km  {s['name']}")
    print("\nNearest is not automatically the governing station — pick the one whose water is")
    print("hydraulically connected to the site, then verify the offset in the water.")


def cmd_bins(a):
    meta = get(f"{MD}/{a.station}.json?type=currentpredictions")["stations"][0]
    bins = get(f"{MD}/{a.station}/bins.json")
    print(f"{a.station}  {meta['name']}   {meta['lat']:.4f}, {meta['lng']:.4f}")
    print(f"  project: {meta.get('project')}  ({meta.get('project_type')})")
    if meta.get("deployed"):
        print(f"  deployed {meta['deployed'][:10]}  retrieved {str(meta.get('retrieved'))[:10]}")
    print(f"  {bins['nbr_of_bins']} bins, {bins['bin_size']} m each\n")

    # Only some bins publish predictions; NOAA reports which in an error message.
    pub = []
    try:
        predictions(a.station, date.today(), bin_=999)
    except SystemExit as e:
        for tok in str(e).split(":")[-1].split(","):
            if tok.strip().isdigit():
                pub.append(int(tok.strip()))
    depths = {b["num"]: b["depth"] for b in bins["bins"]}
    print("  bins with published predictions:")
    for b in sorted(pub):
        print(f"    bin {b:<3} depth {depths.get(b, '?')} m")
    print("\n  Pick the bin nearest YOUR working depth — not automatically the deepest.")
    print("  A station in a deep channel publishes bins you will never dive, and deeper")
    print("  water turns later: at PUG1609 the 82.9 m bin slacks ~40 min after the 18.9 m one.")


def cmd_predict(a):
    cp = predictions(a.station, a.date, a.bin, "MAX_SLACK")
    h = cp[0]
    print(f"{a.station}  {a.date}  bin {h['Bin']} @ {h['Depth']} m")
    print(f"  flood {h['meanFloodDir']}°   ebb {h['meanEbbDir']}°\n")
    for c in cp:
        v = speed(c)
        extra = f"  {v / (KN / 100):+.2f} kn" if a.knots else ""
        if c["Type"] == "slack":
            print(f"  {c['Time'][11:]}  SLACK")
        else:
            print(f"  {c['Time'][11:]}  {c['Type']:<5} {v:+.2f} m/s{extra}")


def cmd_window(a):
    cp = predictions(a.station, a.date, a.bin)  # 6-minute series
    h = cp[0]
    lim = a.max_speed
    print(f"{a.station}  {a.date}  bin {h['Bin']} @ {h['Depth']} m")
    print(f"  windows with |current| <= {lim:.2f} m/s\n")

    runs, cur = [], []
    for c in cp:
        if abs(speed(c)) <= lim:
            cur.append(c)
        else:
            if cur:
                runs.append(cur)
            cur = []
    if cur:
        runs.append(cur)

    if not runs:
        print(f"  none — current never drops below {lim:.2f} m/s. Not a dive day here.")
        return
    for r in runs:
        t0 = datetime.strptime(r[0]["Time"], "%Y-%m-%d %H:%M")
        t1 = datetime.strptime(r[-1]["Time"], "%Y-%m-%d %H:%M")
        mins = int((t1 - t0).total_seconds() // 60) + 6
        peak = max(abs(speed(c)) for c in r)
        flag = "  <-- tight" if mins < 40 else ""
        print(f"  {t0:%H:%M} - {t1:%H:%M}   {mins:>3} min   peak {peak:.2f} m/s{flag}")
    print("\n  Times are AT THE STATION. Apply the site offset, and pad it until observed.")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("stations", help="find live stations near a site")
    s.add_argument("--near", nargs=2, type=float, metavar=("LAT", "LON"), required=True)
    s.add_argument("-n", type=int, default=6)
    s.set_defaults(fn=cmd_stations)

    s = sub.add_parser("bins", help="published bins and their depths")
    s.add_argument("station")
    s.set_defaults(fn=cmd_bins)

    def dated(sp):
        sp.add_argument("station")
        sp.add_argument("--date", type=date.fromisoformat, default=date.today())
        sp.add_argument("--bin", type=int, help="default is near-surface; pass the bin nearest your working depth")

    s = sub.add_parser("predict", help="slack / max flood / max ebb")
    dated(s)
    s.add_argument("--knots", action="store_true", help="also show knots")
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

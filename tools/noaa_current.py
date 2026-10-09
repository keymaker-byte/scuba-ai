#!/usr/bin/env python3
"""NOAA CO-OPS current predictions: slack, max flood/ebb, and diveable windows.

  noaa_current.py stations --near LAT LON                    live current stations near a site
  noaa_current.py bins STATION                               published bins and their depths
  noaa_current.py predict STATION --bin B [--date D]         slack / max flood / max ebb
  noaa_current.py window STATION --bin B [--date D]          diveable windows under a speed threshold

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
    """Fetch NOAA JSON. NOAA returns its JSON error body with a 400 or 404 status, so read
    it rather than raise; anything else that isn't JSON (a 403 from rate limiting, an HTML
    error page, an empty body, a dropped connection) stops the run with what failed."""
    try:
        with urllib.request.urlopen(url, timeout=45) as r:
            body = r.read()
    except urllib.error.HTTPError as e:
        body = e.read()
        try:
            return json.loads(body)
        except ValueError:
            sys.exit(f"NOAA: HTTP {e.code} {e.reason}. The API refused or failed the request; "
                     f"no data was read. Retry later.\n  {url}")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        sys.exit(f"NOAA: unreachable ({getattr(e, 'reason', e)}). No data was read.\n  {url}")
    try:
        return json.loads(body)
    except ValueError:
        what = "an empty response" if not body.strip() else "a response that is not JSON"
        sys.exit(f"NOAA: {what}. No data was read. Retry later.\n  {url}")


def station_meta(station):
    """The station's metadata, or stop: a retired or unknown ID has none."""
    d = get(f"{MD}/{station}.json?type=currentpredictions")
    st = d.get("stations") or []
    if not st:
        sys.exit(f"NOAA: {d.get('errorMsg') or 'no live station ' + station}. A retired "
                 "reference station is read with noaa_legacy_current.")
    return st[0]


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
    cp = (d.get("current_predictions") or {}).get("cp")
    where = f"{station} bin {bin_}" if bin_ else f"{station} default bin"
    if isinstance(cp, str):
        # A bin NOAA judged too weak to predict: an answer, but no slack or speed to plan on.
        sys.exit(f"NOAA: {where}: {cp.strip()}. No predictions are published for it.")
    if not cp:
        sys.exit(f"NOAA: no predictions returned for {where} on {day}. No data was read. Retry later.")
    return cp


def speed(c):
    """Signed along-channel speed, m/s. Positive = flood."""
    return float(c["Velocity_Major"]) / 100.0


def cmd_stations(a):
    all_st = get(f"{MD}.json?type=currentpredictions").get("stations")
    if not all_st:
        sys.exit("NOAA: the station list came back empty. No data was read. Retry later.")
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
        print(f"  {s['id']:<10} {s.get('type') or '?'}  {s['_nm'] * 1.852:5.1f} km  {s['name']}")
    print("\nType: H harmonic (its own constants, usually with depth bins), S subordinate (corrections")
    print("to a reference station), W weak and variable (no predictions).")
    print("Nearest is not automatically the governing station — pick the one whose water is")
    print("hydraulically connected to the site, then verify the offset in the water.")


def cmd_bins(a):
    meta = station_meta(a.station)
    bins = get(f"{MD}/{a.station}/bins.json")
    print(f"{a.station}  {meta['name']}   {meta['lat']:.4f}, {meta['lng']:.4f}")
    print(f"  project: {meta.get('project')}  ({meta.get('project_type')})")
    if meta.get("deployed"):
        print(f"  deployed {meta['deployed'][:10]}  retrieved {str(meta.get('retrieved'))[:10]}")
    if not bins.get("bins"):
        sys.exit(
            f"{a.station} publishes 0 depth bins: a subordinate station (corrections to a "
            "reference station) or one with no instrument record behind it. It has no "
            "working-depth bin to pick; use a type H station with published bins."
        )
    print(f"  {bins['nbr_of_bins']} bins, {bins['bin_size']} m each\n")

    # Only some bins publish predictions; NOAA reports which in an error message.
    q = {"product": "currents_predictions", "application": "NOS.COOPS.TAC.CUR",
         "date": "today", "station": a.station, "bin": "999", "time_zone": "lst_ldt", "units": "metric", "format": "json"}
    msg = (get(f"{DG}?{urllib.parse.urlencode(q)}").get("error") or {}).get("message", "")
    pub = [int(t) for t in msg.split(":")[-1].replace(" ", "").split(",") if t.isdigit()]
    if not pub:
        sys.exit(f"NOAA: could not read which bins publish predictions ({msg.strip() or 'no answer'}).")
    depths = {b["num"]: b["depth"] for b in bins["bins"]}
    print("  bins with published predictions:")
    for b in sorted(pub):
        print(f"    bin {b:<3} depth {depths.get(b, '?')} m")
    print("\n  The site's Recommended bin is the one nearest the dive area's seabed depth.")
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
        if mins >= 1440:
            print(f"  all day          peak {peak:.2f} m/s")
            continue
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
        sp.add_argument("--bin", type=int, help="default is near-surface; pass the site file's Recommended bin")

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

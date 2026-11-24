#!/usr/bin/env python3
"""Retired NOAA current reference stations: slack, max flood/ebb, and diveable windows,
predicted from their archived pre-2016 harmonic constants.

  noaa_legacy_current.py stations --near LAT LON          legacy reference stations near a site
  noaa_legacy_current.py predict STATION [--date D]       slack / max flood / max ebb
  noaa_legacy_current.py window STATION [--date D]        diveable windows under a speed threshold
  noaa_legacy_current.py selftest                         check against NOAA's printed 2013 tables
"""
import argparse
import bz2
import io
import json
import math
import os
import re
import sys
import tarfile
import urllib.request
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.tcd import Harmonics, velocity  # noqa: E402,F401

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "tools", "db")
TCD = os.path.join(DB, "harmonics-dwf-20100529-free.tcd")
IDX = os.path.join(DB, "noaa_legacy_current_index.json")
# XTide's 2010-05-29 harmonics, as archived by Debian (source package xtide-data 20100529).
TCD_URL = "https://snapshot.debian.org/file/7f9edc4c9ea71a5a8f221bbb533943dbbaf9655a"
# XTide's 2018-01-01 release: the first to carry NOAA station IDs, still listing the retired stations.
SQL_URL = "https://flaterco.com/files/xtide/harmonics-dwf-20180101-SQL.tar.bz2"
KN = 0.514444  # m/s per knot
# Reference stations the 2018 listing had already expired, so they carry no NOAA ID there.
# The Narrows: XTide's 2018 ChangeLog, "PCT1766 was superseded by PUG1524".
EXPIRED = {"The Narrows, north end (midstream), Washington Current": "PCT1766"}


def _cfg(key, default):
    """Read this tool's section of tool-config.json; missing file or key -> default."""
    try:
        with open(os.path.join(ROOT, "tool-config.json")) as f:
            return json.load(f).get("noaa_legacy_current", {}).get(key, default)
    except (OSError, ValueError):
        return default


def _fetch(url):
    print(f"downloading {url} ...", file=sys.stderr)
    try:
        with urllib.request.urlopen(url, timeout=120) as r:
            return r.read()
    except OSError as e:
        sys.exit(f"download failed ({e}); the legacy harmonics are needed before any prediction.")


# --- TCD reader and reference prediction: lib/tcd.py -------------------------------------


# --- station index: legacy NOAA IDs to the reference stations in the 2010 harmonics ------

def _ensure():
    os.makedirs(DB, exist_ok=True)
    if not os.path.exists(TCD):
        with tarfile.open(fileobj=io.BytesIO(_fetch(TCD_URL)), mode="r:bz2") as t:
            m = next(x for x in t.getmembers() if x.name.endswith(".tcd"))
            with open(TCD, "wb") as f:
                f.write(t.extractfile(m).read())
    if not os.path.exists(IDX):
        ids = {}
        with tarfile.open(fileobj=io.BytesIO(_fetch(SQL_URL)), mode="r:bz2") as t:
            m = next(x for x in t.getmembers() if x.name.endswith(".sql"))
            for line in t.extractfile(m).read().decode("utf-8", "replace").splitlines():
                f = line.split("\t")
                if len(f) > 4 and f[2] == "NOS" and re.fullmatch(r"(?:PCT|ACT)\d+(_\d+)?", f[3]) and f[1].endswith("Current"):
                    ids.setdefault(f[1], f[3].split("_")[0])
        for name, sid in EXPIRED.items():
            ids.setdefault(name, sid)
        h = Harmonics(TCD)
        index = {}
        for k, r in enumerate(h.records()):
            if r["type"] == 1 and r["name"] in ids:
                index[ids[r["name"]]] = {"record": k, "name": r["name"], "lat": r["lat"], "lon": r["lon"]}
        with open(IDX, "w") as f:
            json.dump(index, f, indent=1)


def index():
    _ensure()
    with open(IDX) as f:
        idx = json.load(f)
    if not set(EXPIRED.values()) <= set(idx):
        # An index built before an expired station was added: rebuild it once.
        os.remove(IDX)
        _ensure()
        with open(IDX) as f:
            idx = json.load(f)
    return idx


def station(sid):
    idx = index()
    if sid not in idx:
        sys.exit(f"{sid} is not a reference current station in the legacy harmonics; "
                 "list them with `stations --near`. A live station is read through the Blend Model.")
    h = Harmonics(TCD)
    for k, r in enumerate(h.records()):
        if k == idx[sid]["record"]:
            return h, r



def day_series(h, r, day, tz):
    start = datetime.combine(day, time(0), tz).astimezone(timezone.utc)
    return [(start + timedelta(minutes=m), velocity(h, r, start + timedelta(minutes=m))) for m in range(1441)]


def events(series, tz):
    out, ext = [], None
    for (t0, v0), (t1, v1) in zip(series, series[1:]):
        if (v0 < 0) != (v1 < 0):
            if ext:
                out.append(ext)
                ext = None
            f = v0 / (v0 - v1)
            out.append(((t0 + (t1 - t0) * f).astimezone(tz), "SLACK", 0.0))
        if ext is None or abs(v1) > abs(ext[2]):
            ext = (t1.astimezone(tz), "flood" if v1 > 0 else "ebb", v1)
    # Keep only extrema that sit between two slacks (a full exchange inside the day).
    keep = []
    for k, e in enumerate(out):
        if e[1] != "SLACK" and 0 < k < len(out) - 1:
            keep.append(e)
        elif e[1] == "SLACK":
            keep.append(e)
    return keep


def header(sid, r, day, tz):
    print(f"{sid}  {r['name']}  {day}  ({tz.key})")
    print(f"  {r['lat']:.4f}, {r['lon']:.4f}   flood {r['flood_dir']}°   ebb {r['ebb_dir']}°   "
          "legacy pre-2016 harmonic constants\n")


def cmd_stations(a):
    lat, lon = a.near
    scale = math.cos(math.radians(lat))
    rows = []
    for sid, s in index().items():
        dy, dx = (s["lat"] - lat) * 60.0, (s["lon"] - lon) * 60.0 * scale
        rows.append((math.hypot(dx, dy) * 1.852, sid, s["name"]))
    rows.sort()
    print(f"Legacy NOAA reference current stations near {lat:.4f}, {lon:.4f}:\n")
    for km, sid, name in rows[: a.n]:
        print(f"  {sid:<9} {km:6.1f} km  {name}")


def cmd_predict(a):
    h, r = station(a.station)
    tz = ZoneInfo(a.tz)
    header(a.station, r, a.date, tz)
    for t, kind, v in events(day_series(h, r, a.date, tz), tz):
        if t.date() != a.date:
            continue
        if kind == "SLACK":
            print(f"  {t:%H:%M}  SLACK")
        else:
            print(f"  {t:%H:%M}  {kind:<5} {v:+.2f} m/s")


def cmd_window(a):
    h, r = station(a.station)
    tz = ZoneInfo(a.tz)
    lim = a.max_speed
    header(a.station, r, a.date, tz)
    print(f"  windows with |current| <= {lim:.2f} m/s\n")
    runs, cur = [], []
    for t, v in day_series(h, r, a.date, tz)[:-1]:
        if abs(v) <= lim:
            cur.append((t, v))
        elif cur:
            runs.append(cur)
            cur = []
    if cur:
        runs.append(cur)
    if not runs:
        print(f"  none — current never drops below {lim:.2f} m/s. Not a dive day here.")
        return
    for run in runs:
        t0, t1 = run[0][0].astimezone(tz), run[-1][0].astimezone(tz)
        mins = len(run)
        peak = max(abs(v) for _, v in run)
        flag = "  <-- tight" if mins < 40 else ""
        print(f"  {t0:%H:%M} - {t1:%H:%M}   {mins:>3} min   peak {peak:.2f} m/s{flag}")
    print("\n  Times are AT THE STATION. Apply the site offset, and pad it until observed.")


# Slack times printed in NOAA's 2013 Tidal Current Tables, Pacific Coast of North America and Asia
# (local standard time, UTC-8): https://tidesandcurrents.noaa.gov/tidetables/2013/pcct2013book.pdf
CHECKS = [
    ("PCT1341", "2013-02-01", ["02:36", "07:15", "15:57", "19:48"]),
    ("PCT1541", "2013-01-01", ["01:36", "08:02"]),
    ("PCT1766", "2013-01-01", ["01:56", "08:45", "14:59", "19:45"]),  # The Narrows (north end), p. 52
]


def cmd_selftest(a):
    pst = timezone(timedelta(hours=-8))
    worst = 0
    for sid, day, printed in CHECKS:
        h, r = station(sid)
        got = [t for t, k, _ in events(day_series(h, r, date.fromisoformat(day), pst), pst) if k == "SLACK"]
        for p in printed:
            ref = datetime.combine(date.fromisoformat(day), time.fromisoformat(p), pst)
            err = min(abs((g - ref).total_seconds()) / 60 for g in got)
            worst = max(worst, err)
            print(f"  {sid} {day} printed {p}  predicted within {err:.0f} min")
    print("\n  PASS" if worst <= 2 else f"\n  FAIL: worst {worst:.0f} min")
    sys.exit(0 if worst <= 2 else 1)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("stations", help="legacy reference current stations near a site")
    s.add_argument("--near", nargs=2, type=float, metavar=("LAT", "LON"), required=True)
    s.add_argument("-n", type=int, default=6)
    s.set_defaults(fn=cmd_stations)

    def dated(sp):
        sp.add_argument("station", help="legacy NOAA ID, e.g. PCT1341 or an ACT ID")
        sp.add_argument("--date", type=date.fromisoformat, default=date.today())
        sp.add_argument("--tz", required=True, metavar="IANA_ZONE", help="the site's time zone, the `tz` in its JSON")

    s = sub.add_parser("predict", help="slack / max flood / max ebb")
    dated(s)
    s.set_defaults(fn=cmd_predict)

    s = sub.add_parser("window", help="diveable slack windows")
    dated(s)
    _ms = _cfg("max_speed_ms", 0.25)
    s.add_argument("--max-speed", type=float, default=_ms, help=f"m/s, default {_ms}")
    s.set_defaults(fn=cmd_window)

    s = sub.add_parser("selftest", help="check against NOAA's printed 2013 tables")
    s.set_defaults(fn=cmd_selftest)

    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()

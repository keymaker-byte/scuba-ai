#!/usr/bin/env python3
"""Retired NOAA current reference stations: slack, max flood/ebb, and diveable windows,
predicted from their archived pre-2016 harmonic constants.

  noaa_legacy_current.py stations --near LAT LON          legacy reference stations near a site
  noaa_legacy_current.py predict STATION [--date D]       slack / max flood / max ebb
  noaa_legacy_current.py window STATION [--date D]        diveable windows under a speed threshold
  noaa_legacy_current.py selftest                         check against NOAA's printed 2013 tables

STATION is the legacy NOAA ID, e.g. PCT1341 on the Pacific or an ACT ID on the Atlantic.
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

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "tools", "db")
TCD = os.path.join(DB, "harmonics-dwf-20100529-free.tcd")
IDX = os.path.join(DB, "noaa_legacy_current_index.json")
# XTide's 2010-05-29 harmonics, as archived by Debian (source package xtide-data 20100529).
TCD_URL = "https://snapshot.debian.org/file/7f9edc4c9ea71a5a8f221bbb533943dbbaf9655a"
# XTide's 2018-01-01 release: the first to carry NOAA station IDs, still listing the retired stations.
SQL_URL = "https://flaterco.com/files/xtide/harmonics-dwf-20180101-SQL.tar.bz2"
KN = 0.514444  # m/s per knot


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


# --- TCD reader (libtcd format, major revision 2) ---------------------------------------

def _unpack(buf, start, n):
    sb, eb = start >> 3, (start + n - 1) >> 3
    v = int.from_bytes(buf[sb:eb + 1], "big")
    return (v >> ((eb + 1) * 8 - (start + n))) & ((1 << n) - 1)


def _sunpack(buf, start, n):
    v = _unpack(buf, start, n)
    return v - (1 << n) if v & (1 << (n - 1)) else v


class Harmonics:
    def __init__(self, path):
        d = open(path, "rb").read()
        end = d.index(b"[END OF ASCII HEADER DATA]")
        self.h = {}
        for line in d[:end].decode("latin-1").splitlines():
            k, _, v = line.partition("=")
            self.h[k.strip().strip("[]")] = v.strip()
        I = self.i
        if I("MAJOR REV") != 2:
            sys.exit("legacy harmonics: unexpected TCD revision.")
        p = I("HEADER SIZE") + 4

        def strings(n, size):
            nonlocal p
            out = [d[p + k * size:p + (k + 1) * size].split(b"\0")[0].decode("latin-1") for k in range(n)]
            p += n * size
            return out

        self.level_units = strings(I("LEVEL UNIT TYPES"), I("LEVEL UNIT SIZE"))
        strings(I("DIRECTION UNIT TYPES"), I("DIRECTION UNIT SIZE"))
        strings(2 ** I("RESTRICTION BITS"), I("RESTRICTION SIZE"))
        strings(2 ** I("TZFILE BITS"), I("TZFILE SIZE"))
        strings(2 ** I("COUNTRY BITS"), I("COUNTRY SIZE"))
        strings(2 ** I("DATUM BITS"), I("DATUM SIZE"))
        strings(2 ** I("LEGALESE BITS"), I("LEGALESE SIZE"))
        nc = I("CONSTITUENTS")
        strings(nc, I("CONSTITUENT SIZE"))
        sb = I("SPEED BITS")
        n = (nc * sb + 7) // 8
        buf = d[p:p + n]
        p += n
        self.speed = [(_unpack(buf, k * sb, sb) + I("SPEED OFFSET")) / I("SPEED SCALE") for k in range(nc)]
        ny, self.y0 = I("NUMBER OF YEARS"), I("START YEAR")

        def table(bits, off, scale):
            nonlocal p
            b = I(bits)
            n = (nc * ny * b + 7) // 8
            buf = d[p:p + n]
            p += n
            return [[(_unpack(buf, (k * ny + j) * b, b) + I(off)) / I(scale) for j in range(ny)] for k in range(nc)]

        self.equ = table("EQUILIBRIUM BITS", "EQUILIBRIUM OFFSET", "EQUILIBRIUM SCALE")
        self.node = table("NODE BITS", "NODE OFFSET", "NODE SCALE")
        self.ny = ny
        self.d, self.rec0 = d, p

    def i(self, key):
        return int(self.h[key])

    def records(self):
        p = self.rec0
        for _ in range(self.i("NUMBER OF RECORDS")):
            size = _unpack(self.d[p:p + 4], 0, self.i("RECORD SIZE BITS"))
            yield self._parse(self.d[p:p + size])
            p += size

    def _parse(self, buf):
        I = self.i
        pos = 0
        r = {}

        def u(k):
            nonlocal pos
            v = _unpack(buf, pos, I(k))
            pos += I(k)
            return v

        def s(k):
            nonlocal pos
            v = _sunpack(buf, pos, I(k))
            pos += I(k)
            return v

        def text():
            nonlocal pos
            out = bytearray()
            while True:
                c = _unpack(buf, pos, 8)
                pos += 8
                if not c:
                    return out.decode("latin-1")
                out.append(c)

        u("RECORD SIZE BITS")
        r["type"] = u("RECORD TYPE BITS")
        r["lat"] = s("LATITUDE BITS") / I("LATITUDE SCALE")
        r["lon"] = s("LONGITUDE BITS") / I("LONGITUDE SCALE")
        u("TZFILE BITS")
        r["name"] = text()
        r["ref"] = s("STATION BITS")
        u("COUNTRY BITS")
        text()  # source
        u("RESTRICTION BITS")
        text()  # comments
        text()  # notes
        u("LEGALESE BITS")
        text()  # station id context
        text()  # station id
        u("DATE BITS")
        text()  # xfields
        u("DIRECTION UNIT BITS")
        r["ebb_dir"] = u("DIRECTION BITS")
        r["flood_dir"] = u("DIRECTION BITS")
        r["units"] = self.level_units[u("LEVEL UNIT BITS")]
        if r["type"] == 1:
            r["datum"] = s("DATUM OFFSET BITS") / I("DATUM OFFSET SCALE")
            u("DATUM BITS")
            zone = s("TIME BITS")  # hhmm
            r["zone_h"] = int(zone / 100) + (zone % 100 if zone >= 0 else -((-zone) % 100)) / 60
            u("DATE BITS")
            u("MONTHS ON STATION BITS")
            u("DATE BITS")
            u("CONFIDENCE VALUE BITS")
            r["cons"] = []
            for _ in range(u("CONSTITUENT BITS")):
                k = u("CONSTITUENT BITS")
                a = u("AMPLITUDE BITS") / I("AMPLITUDE SCALE")
                e = u("EPOCH BITS") / I("EPOCH SCALE")
                r["cons"].append((k, a, e))
        return r


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
        return json.load(f)


def station(sid):
    idx = index()
    if sid not in idx:
        sys.exit(f"{sid} is not a reference current station in the legacy harmonics; "
                 "list them with `stations --near`. A live station is read with noaa_current.")
    h = Harmonics(TCD)
    for k, r in enumerate(h.records()):
        if k == idx[sid]["record"]:
            return h, r


# --- prediction --------------------------------------------------------------------------

def velocity(h, r, t):
    """Signed current at UTC datetime t, m/s. Positive = flood."""
    j = t.year - h.y0
    if not 0 <= j < h.ny:
        sys.exit(f"legacy harmonics cover {h.y0} to {h.y0 + h.ny - 1} only.")
    hrs = (t - datetime(t.year, 1, 1, tzinfo=timezone.utc)).total_seconds() / 3600
    v = r["datum"]
    for k, a, e in r["cons"]:
        # Epochs are referenced to the station's own time meridian; shift them to Greenwich.
        g = e - h.speed[k] * r["zone_h"]
        v += a * h.node[k][j] * math.cos(math.radians(h.speed[k] * hrs + h.equ[k][j] - g))
    if r["units"].endswith("^2"):
        v = math.copysign(math.sqrt(abs(v)), v)
    return v * KN


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


# Slack times printed in NOAA's 2013 Tidal Current Tables (local standard time, UTC-8).
CHECKS = [
    ("PCT1341", "2013-02-01", ["02:36", "07:15", "15:57", "19:48"]),
    ("PCT1541", "2013-01-01", ["01:36", "08:02"]),
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
        sp.add_argument("--tz", default=_cfg("default_tz", "America/Los_Angeles"),
                        help="IANA zone for the output; default from tool-config.json")

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

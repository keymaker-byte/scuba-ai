#!/usr/bin/env python3
"""Wind forecast from Open-Meteo: ECMWF IFS, with GFS as a cross-check.

  open_meteo_wind.py at --near LAT LON --time "D HH:MM" --tz ZONE --bad S --short S   planning: the call at the entry or exit time
  open_meteo_wind.py forecast --near LAT LON --date D --tz ZONE --bad S --short S     planning: the call for every hour of the day
  open_meteo_wind.py forecast --near LAT LON --date D --tz ZONE                       wind alone, no call

  S is a sector from the site's Wind section, compass points clockwise (SW-WNW).

"""
import argparse
import json
import math
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

BASE = "https://api.open-meteo.com/v1/forecast"
DISAGREE_SPEED_MS = 3.0
DISAGREE_DIR_DEG = 30.0
COMPASS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
           "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]


def _cfg(key, default):
    """Read this tool's section of tool-config.json; missing file or key -> default."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        with open(os.path.join(root, "tool-config.json")) as f:
            return json.load(f).get("open_meteo_wind", {}).get(key, default)
    except (OSError, ValueError):
        return default


PRIMARY_MODEL = _cfg("primary_model", "ecmwf_ifs")
CHECK_MODEL = _cfg("cross_check_model", "gfs_seamless")


# ---------------------------------------------------------------- the go / no go call
# The limits live in this tool's section of tool-config.json. The site's own Wind section names
# its Bad and short fetch sectors; every other direction counts as Fine, checked against the
# offshore limit alone.

LIMITS = {
    "go_below_ms": _cfg("go_below_ms", 5.0),
    "nogo_above_ms": _cfg("nogo_above_ms", 8.0),
    "short_fetch_shift_ms": _cfg("short_fetch_shift_ms", 3.0),
    "gust_margin_ms": _cfg("gust_margin_ms", 3.0),
    "offshore_marginal_ms": _cfg("offshore_marginal_ms", 8.0),
}
BANDS = ["go", "marginal", "no go"]


def sectors(specs):
    """'SW-WNW' (clockwise from the first point to the second) or 'N' -> the set of compass indices."""
    out = set()
    for spec in specs or []:
        for part in spec.upper().split(","):
            ends = part.strip().split("-")
            if len(ends) > 2 or any(e not in COMPASS for e in ends):
                sys.exit(f"bad sector '{part.strip()}': use compass points, e.g. SW-WNW or N")
            i, j = COMPASS.index(ends[0]), COMPASS.index(ends[-1])
            out.add(i)
            while i != j:
                i = (i + 1) % 16
                out.add(i)
    return out


def call(speed, gust, deg, bad, short):
    """(sector kind, band) for one reading, or None where a value is missing."""
    if speed is None or deg is None:
        return None
    i = round((deg % 360) / 22.5) % 16
    kind = "short" if i in short else "bad" if i in bad else "fine"
    if kind == "fine":
        # Offshore, the risk is surface drift: the sustained speed alone sets the call, and gusts don't count.
        return kind, BANDS[1 if speed > LIMITS["offshore_marginal_ms"] else 0]
    shift = LIMITS["short_fetch_shift_ms"] if kind == "short" else 0.0
    go, nogo = LIMITS["go_below_ms"] + shift, LIMITS["nogo_above_ms"] + shift
    band = 0 if speed < go else 1 if speed <= nogo else 2
    if gust is not None and gust > speed + LIMITS["gust_margin_ms"]:
        band = min(band + 1, 2)  # gusts onto the entry steepen the chop
    return kind, BANDS[band]


def call_text(c):
    return "" if c is None else f"{c[1]} ({c[0]})"


def get(url):
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read())
        except Exception:
            raise e
        raise SystemExit(f"open-meteo error: {body.get('reason', body)}")


def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi, dlmb = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def compass(deg):
    return COMPASS[round((deg % 360) / 22.5) % 16]


def fetch(lat, lon, tz, start, end, models):
    q = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "wind_speed_10m,wind_direction_10m,wind_gusts_10m",
        "wind_speed_unit": "ms",
        "models": ",".join(models),
        "timezone": tz,
        "start_date": start,
        "end_date": end,
    }
    doc = get(BASE + "?" + urllib.parse.urlencode(q))
    doc["_models"] = models
    doc["_dist_km"] = haversine_km(lat, lon, doc["latitude"], doc["longitude"])
    return doc


def series(doc, model, field):
    suffix = field if len(doc["_models"]) == 1 else f"{field}_{model}"
    return doc["hourly"][suffix]


def print_header(doc, lat, lon):
    print(f"  requested   {lat:.4f}, {lon:.4f}")
    print(f"  grid point  {doc['latitude']:.4f}, {doc['longitude']:.4f}"
          f"  ({doc['_dist_km']:.1f} km away, elevation {doc['elevation']:.0f} m)")
    print(f"  models      {doc['_models'][0]} (primary), {doc['_models'][1]} (cross-check)"
          if len(doc["_models"]) > 1 else f"  model       {doc['_models'][0]}")
    print()


def disagrees(s1, d1, s2, d2):
    ddir = abs(d1 - d2)
    ddir = min(ddir, 360 - ddir)
    return abs(s1 - s2) > DISAGREE_SPEED_MS or ddir > DISAGREE_DIR_DEG


def cmd_forecast(a):
    lat, lon = a.near
    models = a.models.split(",") if a.models else [PRIMARY_MODEL, CHECK_MODEL]
    doc = fetch(lat, lon, a.tz, a.date, a.date, models)
    print_header(doc, lat, lon)

    times = doc["hourly"]["time"]
    bad, short = sectors(a.bad), sectors(a.short)
    judged = bool(bad or short)
    sp1 = series(doc, models[0], "wind_speed_10m")
    dr1 = series(doc, models[0], "wind_direction_10m")
    gu1 = series(doc, models[0], "wind_gusts_10m")
    if len(models) > 1:
        sp2 = series(doc, models[1], "wind_speed_10m")
        dr2 = series(doc, models[1], "wind_direction_10m")
        gu2 = series(doc, models[1], "wind_gusts_10m")
        head = f"  {'time':5}  {'primary speed/dir/gust':26}  {'cross-check speed/dir/gust':26}"
        print(head + (f"  {'primary call':20}  {'cross-check call':20}" if judged else ""))
        for i, t in enumerate(times):
            hhmm = t[-5:]
            p = f"{sp1[i]:4.1f} m/s {compass(dr1[i]):>3} ({dr1[i]:3.0f}°)  {gu1[i]:4.1f}"
            c = f"{sp2[i]:4.1f} m/s {compass(dr2[i]):>3} ({dr2[i]:3.0f}°)  {gu2[i]:4.1f}"
            calls = ""
            if judged:
                c1, c2 = call(sp1[i], gu1[i], dr1[i], bad, short), call(sp2[i], gu2[i], dr2[i], bad, short)
                calls = f"  {call_text(c1):20}  {call_text(c2):20}"
                if c1 and c2 and c1[1] != c2[1]:
                    calls += "  <-- calls differ"
            flag = "  <-- models disagree" if disagrees(sp1[i], dr1[i], sp2[i], dr2[i]) else ""
            print(f"  {hhmm}  {p:26}  {c:26}{calls}{flag}")
    else:
        print(f"  {'time':5}  speed/dir/gust" + ("                      call" if judged else ""))
        for i, t in enumerate(times):
            verdict = f"  {call_text(call(sp1[i], gu1[i], dr1[i], bad, short))}" if judged else ""
            print(f"  {t[-5:]}  {sp1[i]:4.1f} m/s {compass(dr1[i]):>3} "
                  f"({dr1[i]:3.0f}°)  gust {gu1[i]:4.1f} m/s{verdict}")


def circular_mean_deg(d1, d2, frac):
    x1, y1 = math.sin(math.radians(d1)), math.cos(math.radians(d1))
    x2, y2 = math.sin(math.radians(d2)), math.cos(math.radians(d2))
    x, y = x1 + (x2 - x1) * frac, y1 + (y2 - y1) * frac
    return math.degrees(math.atan2(x, y)) % 360


def interpolate(times, values, target, circular=False):
    for i in range(len(times) - 1):
        t0, t1 = datetime.fromisoformat(times[i]), datetime.fromisoformat(times[i + 1])
        if t0 <= target <= t1:
            frac = (target - t0).total_seconds() / (t1 - t0).total_seconds()
            if circular:
                return circular_mean_deg(values[i], values[i + 1], frac)
            return values[i] + (values[i + 1] - values[i]) * frac
    raise SystemExit(f"{target} falls outside the fetched hourly series "
                      f"({times[0]} to {times[-1]})")


def cmd_at(a):
    lat, lon = a.near
    target = datetime.strptime(a.time, "%Y-%m-%d %H:%M")
    models = a.models.split(",") if a.models else [PRIMARY_MODEL, CHECK_MODEL]
    start = target.date().isoformat()
    end = (target.date() + timedelta(days=1)).isoformat()
    doc = fetch(lat, lon, a.tz, start, end, models)
    print_header(doc, lat, lon)

    times = doc["hourly"]["time"]
    bad, short = sectors(a.bad), sectors(a.short)
    judged = bool(bad or short)
    results = []
    for m in models:
        sp = interpolate(times, series(doc, m, "wind_speed_10m"), target)
        dr = interpolate(times, series(doc, m, "wind_direction_10m"), target, circular=True)
        gu = interpolate(times, series(doc, m, "wind_gusts_10m"), target)
        results.append((m, sp, dr, gu))

    label = "primary" if len(models) > 1 else "model"
    for i, (m, sp, dr, gu) in enumerate(results):
        tag = f"({label})" if i == 0 else "(cross-check)"
        verdict = f"  {call_text(call(sp, gu, dr, bad, short))}" if judged else ""
        print(f"  {m:16} {tag:15} {sp:4.1f} m/s  {compass(dr):>3} ({dr:3.0f}°)  "
              f"gust {gu:4.1f} m/s{verdict}")
    if len(results) > 1 and disagrees(results[0][1], results[0][2], results[1][1], results[1][2]):
        print("  <-- models disagree by more than "
              f"{DISAGREE_SPEED_MS} m/s or {DISAGREE_DIR_DEG}°, treat this figure with care")


def _call_args(s):
    s.add_argument("--bad", action="append", metavar="SECTOR",
                   help="the site's Bad sector(s), compass points clockwise, e.g. SW-WNW")
    s.add_argument("--short", action="append", metavar="SECTOR",
                   help="the site's short fetch and Mixed sector(s); their bands move up by short_fetch_shift_ms")


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    models_help = (f"comma separated Open-Meteo model ids, first is primary "
                    f"(default: {PRIMARY_MODEL},{CHECK_MODEL})")

    s = sub.add_parser("forecast", help="hourly wind for one local calendar day")
    s.add_argument("--near", nargs=2, type=float, metavar=("LAT", "LON"), required=True)
    s.add_argument("--date", required=True, metavar="YYYY-MM-DD")
    s.add_argument("--tz", required=True, metavar="IANA_ZONE",
                   help="the dive site's own timezone, e.g. Continent/City")
    s.add_argument("--models", help=models_help)
    _call_args(s)
    s.set_defaults(fn=cmd_forecast)

    s = sub.add_parser("at", help="wind at one local moment, interpolated between hours")
    s.add_argument("--near", nargs=2, type=float, metavar=("LAT", "LON"), required=True)
    s.add_argument("--time", required=True, metavar="YYYY-MM-DD HH:MM")
    s.add_argument("--tz", required=True, metavar="IANA_ZONE",
                   help="the dive site's own timezone, e.g. Continent/City")
    s.add_argument("--models", help=models_help)
    _call_args(s)
    s.set_defaults(fn=cmd_at)

    a = p.parse_args()
    sectors(a.bad), sectors(a.short)  # reject a malformed sector before any request
    a.fn(a)


if __name__ == "__main__":
    main()

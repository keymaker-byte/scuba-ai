#!/usr/bin/env python3
"""NWS point forecast: wind, gusts, waves, air temperature and rain at a US coordinate.

  nws_forecast.py at --near LAT LON --time "D HH:MM" --bad S --short S     planning: the call at the entry or exit time
  nws_forecast.py forecast --near LAT LON --date D --bad S --short S       planning: the call for every hour of the day
  nws_forecast.py forecast --near LAT LON --date D                         conditions alone, no call

  S is a sector from the site's Wind section, compass points clockwise (SW-WNW).

"""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

BASE = "https://api.weather.gov"
KMH = 1 / 3.6
COMPASS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
           "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
DURATION = re.compile(r"P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?)?$")


def _cfg(key, default):
    """Read this tool's section of tool-config.json; missing file or key -> default."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        with open(os.path.join(root, "tool-config.json")) as f:
            return json.load(f).get("nws_forecast", {}).get(key, default)
    except (OSError, ValueError):
        return default


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


def get(url, what="NWS"):
    email = _cfg("user_agent_email", None)
    if not email or email.startswith("<"):
        sys.exit("nws_forecast.user_agent_email not set in tool-config.json")
    req = urllib.request.Request(url, headers={"User-Agent": f"dive-planning ({email})",
                                               "Accept": "application/geo+json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        try:
            detail = json.loads(e.read()).get("detail", "")
        except ValueError:
            detail = ""
        sys.exit(f"{what} error: HTTP {e.code} {detail}".rstrip())
    except urllib.error.URLError as e:
        sys.exit(f"NWS unreachable: {e.reason}")
    except (OSError, ValueError) as e:
        sys.exit(f"NWS read failed: {e}")


def compass(deg):
    return COMPASS[round((deg % 360) / 22.5) % 16]


def intervals(layer, tz):
    """A gridpoint layer as (start, end, value) in local time; values are constant over each span."""
    out = []
    for v in (layer or {}).get("values", []):
        start, dur = v["validTime"].split("/")
        d, h, m = (int(x or 0) for x in DURATION.match(dur).groups())
        t0 = datetime.fromisoformat(start).astimezone(tz)
        out.append((t0, t0 + timedelta(days=d, hours=h, minutes=m), v["value"]))
    return out


def value_at(spans, t):
    for t0, t1, v in spans:
        if t0 <= t < t1:
            return v
    return None


def fetch(lat, lon):
    pt = get(f"{BASE}/points/{lat:.4f},{lon:.4f}",
             "NWS point lookup (NWS covers US coordinates only)")["properties"]
    tz = ZoneInfo(pt["timeZone"])
    grid = get(pt["forecastGridData"])["properties"]
    hourly = get(pt["forecastHourly"] + "?units=si")["properties"]["periods"]
    layers = {k: intervals(grid.get(k), tz) for k in
              ("windSpeed", "windDirection", "windGust", "waveHeight", "temperature",
               "probabilityOfPrecipitation")}
    sky = [(datetime.fromisoformat(p["startTime"]).astimezone(tz),
            datetime.fromisoformat(p["endTime"]).astimezone(tz), p["shortForecast"]) for p in hourly]
    covered = layers["windSpeed"]
    return {"point": pt, "tz": tz, "grid": grid, "layers": layers, "sky": sky,
            "first": covered[0][0] if covered else None, "last": covered[-1][1] if covered else None}


def print_header(doc, lat, lon):
    pt, grid, tz = doc["point"], doc["grid"], doc["tz"]
    rel = pt.get("relativeLocation", {}).get("properties", {})
    updated = datetime.fromisoformat(grid["updateTime"]).astimezone(tz)
    print(f"  requested   {lat:.4f}, {lon:.4f}")
    print(f"  gridpoint   {pt['gridId']} {pt['gridX']},{pt['gridY']}  (2.5 km cell, elevation "
          f"{grid['elevation']['value']:.0f} m, near {rel.get('city', '?')}, {rel.get('state', '?')})")
    print(f"  zone        {tz.key}")
    print(f"  updated     {updated:%Y-%m-%d %H:%M}")
    print()


def conditions(doc, t):
    L = doc["layers"]
    spd, dr, gu = value_at(L["windSpeed"], t), value_at(L["windDirection"], t), value_at(L["windGust"], t)
    wave, air, pop = value_at(L["waveHeight"], t), value_at(L["temperature"], t), value_at(
        L["probabilityOfPrecipitation"], t)
    return {
        "wind": f"{spd * KMH:4.1f} m/s" if spd is not None else "   - m/s",
        "dir": f"{compass(dr):>3} ({dr:3.0f}°)" if dr is not None else "  -       ",
        "gust": f"{gu * KMH:4.1f} m/s" if gu is not None else "   - m/s",
        "wave": f"{wave:3.1f} m" if wave is not None else "  - m",
        "air": f"{air:4.1f} °C" if air is not None else "   - °C",
        "rain": f"{pop:3.0f}%" if pop is not None else "  -%",
        "sky": value_at(doc["sky"], t) or "",
        "raw": (spd * KMH if spd is not None else None, dr, gu * KMH if gu is not None else None),
    }


def check_covered(doc, t0, t1):
    if doc["first"] is None or t1 <= doc["first"] or t0 >= doc["last"]:
        span = (f"{doc['first']:%Y-%m-%d %H:%M} to {doc['last']:%Y-%m-%d %H:%M}"
                if doc["first"] else "nothing")
        sys.exit(f"outside the NWS forecast window (it covers {span}, local)")


def _reorder(raw):
    """(speed, direction, gust) -> the (speed, gust, direction) order call() takes."""
    return raw[0], raw[2], raw[1]


def cmd_forecast(a):
    lat, lon = a.near
    doc = fetch(lat, lon)
    day = datetime.strptime(a.date, "%Y-%m-%d").replace(tzinfo=doc["tz"])
    check_covered(doc, day, day + timedelta(days=1))
    print_header(doc, lat, lon)
    bad, short = sectors(a.bad), sectors(a.short)
    judged = bool(bad or short)
    head = f"  {'time':5}  {'wind':8}  {'from':10}  {'gust':8}  {'wave':5}  {'air':7}  {'rain':4}  "
    print(head + (f"{'call':20}  " if judged else "") + "sky")
    for h in range(24):
        t = day + timedelta(hours=h)
        if not doc["first"] <= t < doc["last"]:
            continue
        c = conditions(doc, t)
        verdict = f"{call_text(call(*_reorder(c['raw']), bad, short)):20}  " if judged else ""
        print(f"  {t:%H:%M}  {c['wind']}  {c['dir']}  {c['gust']}  {c['wave']}  {c['air']}  "
              f"{c['rain']}  {verdict}{c['sky']}")


def cmd_at(a):
    lat, lon = a.near
    doc = fetch(lat, lon)
    t = datetime.strptime(a.time, "%Y-%m-%d %H:%M").replace(tzinfo=doc["tz"])
    check_covered(doc, t, t + timedelta(minutes=1))
    print_header(doc, lat, lon)
    c = conditions(doc, t)
    print(f"  {t:%Y-%m-%d %H:%M}")
    print(f"  wind   {c['wind'].strip()}  from {' '.join(c['dir'].split())}  gust {c['gust'].strip()}")
    print(f"  waves  {c['wave'].strip()}")
    print(f"  air    {c['air'].strip()}  rain {c['rain'].strip()}  {c['sky']}")
    bad, short = sectors(a.bad), sectors(a.short)
    if bad or short:
        print(f"  call   {call_text(call(*_reorder(c['raw']), bad, short)) or 'no reading'}")


def _call_args(s):
    s.add_argument("--bad", action="append", metavar="SECTOR",
                   help="the site's Bad sector(s), compass points clockwise, e.g. SW-WNW")
    s.add_argument("--short", action="append", metavar="SECTOR",
                   help="the site's short fetch and Mixed sector(s); their bands move up by short_fetch_shift_ms")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("forecast", help="hourly conditions for one local calendar day")
    s.add_argument("--near", nargs=2, type=float, metavar=("LAT", "LON"), required=True)
    s.add_argument("--date", required=True, metavar="YYYY-MM-DD")
    _call_args(s)
    s.set_defaults(fn=cmd_forecast)

    s = sub.add_parser("at", help="conditions at one local moment")
    s.add_argument("--near", nargs=2, type=float, metavar=("LAT", "LON"), required=True)
    s.add_argument("--time", required=True, metavar="YYYY-MM-DD HH:MM")
    _call_args(s)
    s.set_defaults(fn=cmd_at)

    a = p.parse_args()
    sectors(a.bad), sectors(a.short)  # reject a malformed sector before any request
    a.fn(a)


if __name__ == "__main__":
    main()

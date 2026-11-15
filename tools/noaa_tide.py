#!/usr/bin/env python3
"""NOAA CO-OPS tide predictions, in metres against MLLW, computed on this machine.

  noaa_tide.py stations --near LAT LON                       tide stations near a site
  noaa_tide.py predict STATION [--date D]                    high/low water for the day
  noaa_tide.py at STATION --time "D HH:MM"                   tide height at a moment
  noaa_tide.py range STATION [--year Y]                      median/max/min daily range and year span
  noaa_tide.py project STATION --datum-depth X [--date D]    datum depth to depth below surface, all day
  noaa_tide.py normalize STATION --time T --depth D          observed depth to depth below MLLW
  noaa_tide.py fetch [STATION ...] [--near LAT LON --km R] [--all]   cache stations ahead of time
  noaa_tide.py verify STATION [--date D] [--days N]          compare with NOAA's live API
  noaa_tide.py verify --all                                  compare every cached station

The data lives in tools/db/noaa_tide/: the station list, and one file per station, each
downloaded from NOAA the first time it is needed. A reference station's file holds its harmonic
constants and its datums; a subordinate station's holds NOAA's corrections to its reference
station. Delete a file, or the folder, to fetch NOAA's current values again.

The astronomy is noaa_current.py's (Schureman, with NOAA's conventions).
"""
import argparse
import itertools
import json
import math
import os
import sys
import time as _time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import noaa_current as nc  # noqa: E402  the shared astronomy

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "tools", "db", "noaa_tide")
LIST = os.path.join(DB, "stations.json")
REPORT = os.path.join(DB, "_verify.jsonl")
MD = "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations"
DG = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"

# NOAA gives each station a standard offset from UTC. These are the US zones at each offset;
# any other offset prints as a fixed offset. `--tz` overrides with the site's own zone.
ZONES = {-4: "America/Puerto_Rico", -5: "America/New_York", -6: "America/Chicago", -7: "America/Denver",
         -8: "America/Los_Angeles", -9: "America/Anchorage", -10: "Pacific/Honolulu",
         -11: "Pacific/Pago_Pago", 10: "Pacific/Guam"}


def get(url, missing_ok=False):
    """Fetch NOAA JSON, or stop the run with what failed. NOAA sends its JSON error body with
    a 400 or 404 status, so read it rather than raise."""
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            body = r.read()
    except urllib.error.HTTPError as e:
        body = e.read()
        if e.code == 404 and missing_ok:
            return None
        try:
            return json.loads(body)
        except ValueError:
            sys.exit(f"NOAA: HTTP {e.code} {e.reason}. The API refused or failed the request; "
                     f"nothing was cached from it. Retry later.\n  {url}")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        sys.exit(f"NOAA: unreachable ({getattr(e, 'reason', e)}). Nothing was cached.\n  {url}")
    try:
        return json.loads(body)
    except ValueError:
        what = "an empty response" if not body.strip() else "a response that is not JSON"
        sys.exit(f"NOAA: {what}. Nothing was cached. Retry later.\n  {url}")


def _save(path, doc):
    os.makedirs(DB, exist_ok=True)
    tmp = path + ".part"
    with open(tmp, "w") as f:
        json.dump(doc, f, separators=(",", ":"))
    os.replace(tmp, path)


# --- the cache: station list, then one file per station ----------------------------------

def station_list():
    """Every tide prediction station NOAA lists, keyed by ID."""
    if os.path.exists(LIST):
        with open(LIST) as f:
            return json.load(f)
    print("downloading NOAA's tide station list ...", file=sys.stderr)
    rows = (get(f"{MD}.json?type=tidepredictions&units=metric") or {}).get("stations")
    if not rows:
        sys.exit("NOAA: the station list came back empty. Nothing was cached. Retry later.")
    st = {s["id"]: {"name": s["name"], "lat": s["lat"], "lon": s["lng"], "type": s.get("type"),
                    "ref": s.get("reference_id") or None, "tz_offset": s.get("timezonecorr")} for s in rows}
    doc = {"fetched": date.today().isoformat(), "stations": st}
    _save(LIST, doc)
    return doc


def station(sid, quiet=False):
    """One station's cached file. Downloaded on first use."""
    path = os.path.join(DB, f"{sid}.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    st = station_list()
    e = st["stations"].get(sid)
    if e is None:
        sys.exit(f"{sid} is not in NOAA's tide prediction station list (fetched {st['fetched']}). List "
                 "stations with `stations --near`. Delete tools/db/noaa_tide/stations.json to list again.")
    if not quiet:
        print(f"downloading {sid} {e['name']} ...", file=sys.stderr)
    doc = {"id": sid, "fetched": date.today().isoformat(), "name": e["name"], "lat": e["lat"], "lon": e["lon"],
           "type": e["type"], "tz_offset": e["tz_offset"]}
    if e["type"] == "S":
        off = get(f"{MD}/{sid}/tidepredoffsets.json?units=metric") or {}
        if "refStationId" not in off:
            sys.exit(f"NOAA: no subordinate corrections answer for {sid}. Nothing was cached.")
        doc["offsets"] = {k: off.get(k) for k in ("refStationId", "heightOffsetHighTide", "heightOffsetLowTide",
                                                  "timeOffsetHighTide", "timeOffsetLowTide", "heightAdjustedType")}
    else:
        meta = (get(f"{MD}/{sid}.json?units=metric") or {}).get("stations") or [{}]
        doc["observes_dst"] = meta[0].get("observedst")
        har = get(f"{MD}/{sid}/harcon.json?units=metric") or {}
        if "HarmonicConstituents" not in har:
            sys.exit(f"NOAA: no harmonic constants answer for {sid}. Nothing was cached. Retry later.")
        doc["cons"] = [[c["name"], c["amplitude"], c["phase_GMT"], c["speed"]] for c in har["HarmonicConstituents"]]
        dat = get(f"{MD}/{sid}/datums.json?units=metric") or {}
        if "datums" not in dat:
            sys.exit(f"NOAA: no datums answer for {sid}. Nothing was cached. Retry later.")
        d = {x["name"]: x["value"] for x in dat.get("datums") or []}
        doc["msl"], doc["mllw"], doc["epoch"] = d.get("MSL"), d.get("MLLW"), dat.get("epoch")
    _save(path, doc)
    return doc


def reference(doc):
    """The station whose constants predict this one: itself, or a subordinate's reference."""
    if doc["type"] != "S":
        ref = doc
    else:
        ref = station(doc["offsets"]["refStationId"])
        if ref["type"] == "S":
            sys.exit(f"{doc['id']}'s reference {ref['id']} is itself subordinate; nothing to correct.")
    if not ref.get("cons"):
        sys.exit(f"{ref['id']} {ref['name']}: NOAA lists the station and publishes no harmonic constants "
                 "for it, so there is nothing to predict from.")
    if ref.get("msl") is None or ref.get("mllw") is None:
        sys.exit(f"{ref['id']} {ref['name']}: NOAA publishes no MSL or MLLW datum for it, so its "
                 "predictions cannot be placed on MLLW.")
    return ref


def zone_of(doc, override=None):
    """The station's local zone, from NOAA's standard offset for it and its position. Alaska
    north of 50° keeps Alaska time east of 169°30'W and Aleutian time west of it, whatever
    older offset NOAA still lists; Bermuda is the one station group at UTC-4 with daylight time."""
    if override:
        return ZoneInfo(override)
    off, lat, lon = int(doc["tz_offset"]), doc["lat"], doc["lon"]
    if lat >= 50 and off in (-9, -10, -11):
        return ZoneInfo("America/Adak" if lon < -169.5 or lon > 0 else "America/Anchorage")
    if off == -4 and lat > 30:
        return ZoneInfo("Atlantic/Bermuda")
    if off in ZONES:
        return ZoneInfo(ZONES[off])
    return timezone(timedelta(hours=off), f"UTC{off:+d}")


def zone_name(tz):
    return getattr(tz, "key", None) or tz.tzname(None)


# --- constituents ------------------------------------------------------------------------

# Degrees per hour of T, s, h, p, p1: what a constituent's argument coefficients add up to.
RATE = (15.0, 0.54901653, 0.04106864, 0.00464183, 0.00000196)

# Constituents beyond noaa_current's 37: (T, s, h, p, p1) coefficients, constant, nodal parts.
EXTRA = {
    "SIGMA1": ((1, -4, 3, 0, 0), 90, [("O1", 2)]),
    # NOAA's names for pi1, psi1 and phi1, each with no nodal part.
    "TK1": ((1, 0, -2, 0, 1), 90, []),
    "RP1": ((1, 0, 2, 0, -1), -90, []),
    "KP1": ((1, 0, 3, 0, 0), -90, []),
    "CHI1": ((1, -1, 3, -1, 0), -90, [("J1", 1)]),
    "THETA1": ((1, 1, -1, 1, 0), -90, [("J1", 1)]),
}
# A compound's letters, each one of these constituents; K is K1 or K2, whichever fits.
LETTER = {"M": ["M2"], "S": ["S2"], "N": ["N2"], "L": ["L2"], "O": ["O1"], "P": ["P1"], "Q": ["Q1"],
          "J": ["J1"], "T": ["T2"], "R": ["R2"], "K": ["K1", "K2"]}
# Compounds whose name alone does not spell their parts.
NAMED = {"OO2": {"O1": 1, "Q1": 1}, "3KM5": {"K2": 1, "K1": 1, "M2": 1}}


def _base(name):
    key = nc.ALIAS.get(name.upper(), name.upper())
    return nc.CONS.get(key) or EXTRA.get(key)


def _rate(coef):
    return sum(c * r for c, r in zip(coef, RATE))


def _combine(parts):
    """A compound constituent from {base: count}: arguments, constants and nodal parts add."""
    coef, const, nodal = [0] * 5, 0, []
    for name, n in parts.items():
        c, k, nd = _base(name)
        coef = [a + n * b for a, b in zip(coef, c)]
        const += n * k
        nodal += [(b, p * n) for b, p in nd]
    return tuple(coef), const, nodal


_SOLVED = {}


def constituent(name, speed):
    """(coefficients, constant, nodal parts) for a constituent NOAA names, checked against the
    speed NOAA publishes for it. A compound tide is worked out from its name: 2MK5 is twice
    M2 plus K1, MSN2 is M2 plus S2 less N2, the signs being the ones that give its speed."""
    key = name.upper()
    if key in _SOLVED:
        return _SOLVED[key]
    found = _base(key)
    if found is None and key in NAMED:
        found = _combine(NAMED[key])
    if found is None:
        found = _spell(key, speed)
    if found is None or abs(_rate(found[0]) - speed) > 2e-4:
        sys.exit(f"constituent {name} ({speed}°/h) is not one this tool can predict. Report it rather "
                 "than predicting without it.")
    _SOLVED[key] = found
    return found


def _spell(key, speed):
    body = key.rstrip("0123456789")
    if not body or any(not (ch.isdigit() or ch in LETTER) for ch in body) or body[-1].isdigit():
        return None
    if len(body) == 1:  # N4 is twice N2, M10 five times M2
        for base in LETTER[body]:
            for n in range(1, 8):
                combo = _combine({base: n})
                if abs(_rate(combo[0]) - speed) <= 2e-4:
                    return combo
        return None
    # A count belongs to the letter after it (2MS6 is 2M + S); failing that, to every letter up
    # to the next count (2MS8 is 2M + 2S, M2KS2 is M + 2K - 2S).
    for carry in (False, True):
        letters, count = [], 1
        for k, ch in enumerate(body):
            if ch.isdigit():
                continue
            if k and body[k - 1].isdigit():
                d = k - 1
                while d and body[d - 1].isdigit():
                    d -= 1
                count = int(body[d:k])
            elif not carry:
                count = 1
            letters.append((ch, count))
        for choice in itertools.product(*(LETTER[ch] for ch, _ in letters)):
            for signs in itertools.product((1, -1), repeat=len(letters)):
                parts = {}
                for base, (_, n), sg in zip(choice, letters, signs):
                    parts[base] = parts.get(base, 0) + sg * n
                combo = _combine(parts)
                if abs(_rate(combo[0]) - speed) <= 2e-4:
                    return combo
    return None


def prepare(cons, year):
    nd = nc.nodal(year)
    out = []
    for name, amp, phase, speed in cons:
        if not amp:
            continue
        coef, const, parts = constituent(name, speed)
        f, u = 1.0, 0.0
        for base, power in parts:
            f *= nd[base][0] ** abs(power)
            u += nd[base][1] * power
        out.append((coef, const + u - phase, f * amp))
    return out


_PREP = {}


def height(ref, t):
    """Tide height at a reference station at UTC datetime t, metres above MLLW: mean sea level
    above MLLW plus the sum of the constituents."""
    key = (ref["id"], t.year)
    if key not in _PREP:
        _PREP[key] = prepare(ref["cons"], t.year)
    s, h, p, _, p1 = nc.longitudes(t)
    T = 15.0 * (t.hour + t.minute / 60 + t.second / 3600 + t.microsecond / 3.6e9) + 180.0
    z = ref["msl"] - ref["mllw"]
    rad = math.radians
    for (cT, cs, ch, cp, cp1), const, amp in _PREP[key]:
        z += amp * math.cos(rad(cT * T + cs * s + ch * h + cp * p + cp1 * p1 + const))
    return z


def extremes(doc, start, end, step=6):
    """Highs and lows between two UTC datetimes: [(utc datetime, "H" or "L", metres)]. A
    subordinate station's are its reference's, each moved and scaled by NOAA's corrections."""
    ref = reference(doc)
    o = doc.get("offsets")
    pad = timedelta(minutes=(max(abs(o["timeOffsetHighTide"] or 0), abs(o["timeOffsetLowTide"] or 0)) if o else 0) + 3 * step)
    n = int((end - start + 2 * pad).total_seconds() // 60 // step) + 1
    ts = [start - pad + timedelta(minutes=k * step) for k in range(n)]
    vs = [height(ref, t) for t in ts]
    out = []
    for k in range(1, n - 1):
        v0, v1, v2 = vs[k - 1], vs[k], vs[k + 1]
        if (v1 - v0) * (v2 - v1) < 0 or (v1 == v2 and v1 != v0):
            den = v0 - 2 * v1 + v2
            x = 0.5 * (v0 - v2) / den if den else 0.0
            t = ts[k] + timedelta(minutes=step * x)
            kind = "H" if v1 > v0 else "L"
            v = height(ref, t)
            if o:
                t, v = _correct(o, t, kind, v)
            out.append((t, kind, v))
    out.sort()
    return [e for e in out if start <= e[0] < end]


def _correct(o, t, kind, v):
    """A reference station's high or low moved to its subordinate by NOAA's corrections."""
    hi = kind == "H"
    t += timedelta(minutes=(o["timeOffsetHighTide"] if hi else o["timeOffsetLowTide"]) or 0)
    adj = o["heightOffsetHighTide"] if hi else o["heightOffsetLowTide"]
    return t, (v * adj if o["heightAdjustedType"] == "R" else v + adj)


def height_at(doc, t):
    """Tide height at any station at UTC datetime t. A reference station's comes straight from
    its constants. NOAA defines a subordinate station by its highs and lows alone; between two
    of them the height follows the reference station's own curve between the same two extremes,
    stretched in time and height to fit the subordinate's."""
    ref = reference(doc)
    if doc["type"] != "S":
        return height(ref, t)
    o = doc["offsets"]
    pairs = sorted((_correct(o, *e), e) for e in extremes(ref, t - timedelta(hours=36), t + timedelta(hours=36)))
    before = [p for p in pairs if p[0][0] <= t]
    after = [p for p in pairs if p[0][0] > t]
    if not before or not after:
        sys.exit(f"{t:%Y-%m-%d %H:%M} UTC is not bracketed by predicted extremes at {doc['id']}.")
    ((t0, v0), (r0, _, w0)), ((t1, v1), (r1, _, w1)) = before[-1], after[0]
    frac = (t - t0).total_seconds() / (t1 - t0).total_seconds()
    if r1 <= r0 or w1 == w0:
        return (v0 + v1) / 2 + (v0 - v1) / 2 * math.cos(math.pi * frac)
    return v0 + (height(ref, r0 + (r1 - r0) * frac) - w0) * (v1 - v0) / (w1 - w0)


# --- commands ----------------------------------------------------------------------------

def header(doc, what, tz):
    print(f"{doc['id']}  {doc['name']}  {what}  ({zone_name(tz)})")
    if doc["type"] == "S":
        ref = reference(doc)
        print(f"  subordinate to {ref['id']} {ref['name']}; computed locally from NOAA's corrections as fetched "
              f"{doc['fetched']} and constants as fetched {ref['fetched']}\n")
    else:
        print(f"  computed locally from NOAA's constants as fetched {doc['fetched']}\n")


def local_day(day, tz):
    start = datetime.combine(day, time(0), tz).astimezone(timezone.utc)
    end = datetime.combine(day + timedelta(days=1), time(0), tz).astimezone(timezone.utc)
    return start, end


def _round(t, tz):
    return (t + timedelta(seconds=30)).astimezone(tz).replace(second=0, microsecond=0)


def day_extremes(ex, day, tz):
    """The day's highs and lows. A day holding only one kind (a single extreme, or two of the
    same kind either side of midnight) also takes the extreme just before and just after it, so
    its range always spans a low to a high."""
    idx = [i for i, e in enumerate(ex) if _round(e[0], tz).date() == day]
    if not idx:
        return []
    if len({ex[i][1] for i in idx}) < 2:
        idx = [i for i in (idx[0] - 1, *idx, idx[-1] + 1) if 0 <= i < len(ex)]
    return [ex[i] for i in idx]


def cmd_stations(a):
    st = station_list()
    lat, lon = a.near
    scale = math.cos(math.radians(lat))
    rows = sorted(((math.hypot((s["lat"] - lat) * 60.0, (s["lon"] - lon) * 60.0 * scale) * 1.852, sid, s)
                   for sid, s in st["stations"].items()), key=lambda r: r[0])[: a.n]
    print(f"Tide prediction stations near {lat:.4f}, {lon:.4f} (NOAA's list as fetched {st['fetched']}):\n")
    for km, sid, s in rows:
        kind = "reference" if s["type"] != "S" else f"subordinate to {s['ref']}"
        print(f"  {sid:<10} {km:5.1f} km  {s['name']}   ({kind})")
    print("\nNearest is usually right for tide height — unlike currents, water level varies")
    print("smoothly. But a station across a constriction can lag; prefer one on the same shore.")


def cmd_predict(a):
    doc = station(a.station)
    tz = zone_of(doc, a.tz)
    start, end = local_day(a.date, tz)
    ex = extremes(doc, start - timedelta(days=1), end + timedelta(days=1))
    pts = day_extremes(ex, a.date, tz)
    header(doc, f"{a.date}  high/low water, m above MLLW, local time", tz)
    for t, kind, v in pts:
        lt = _round(t, tz)
        when = f"{lt:%H:%M}" if lt.date() == a.date else f"{lt:%Y-%m-%d %H:%M}"
        print(f"  {when}  {'HIGH' if kind == 'H' else 'LOW '}  {v:+.2f} m")
    lo, hi = min(p[2] for p in pts), max(p[2] for p in pts)
    print(f"\n  range {hi - lo:.2f} m — a fixed seabed feature reads {hi - lo:.2f} m deeper at the high than the low.")


def cmd_range(a):
    doc = station(a.station)
    tz = zone_of(doc, a.tz)
    start = local_day(date(a.year, 1, 1), tz)[0]
    end = local_day(date(a.year, 12, 31), tz)[1]
    ex = extremes(doc, start - timedelta(days=1), end + timedelta(days=1))
    daily = []
    day = date(a.year, 1, 1)
    while day.year == a.year:
        vs = [e[2] for e in day_extremes(ex, day, tz)]
        if vs:
            daily.append((day.isoformat(), max(vs) - min(vs)))
        day += timedelta(days=1)
    daily.sort(key=lambda x: x[1])
    inyear = [e for e in ex if _round(e[0], tz).year == a.year]
    n = len(daily)
    median = daily[n // 2][1] if n % 2 else (daily[n // 2 - 1][1] + daily[n // 2][1]) / 2
    lo_day, hi_day = daily[0], daily[-1]
    header(doc, f"{a.year}  high/low range across the year, m MLLW", tz)
    print(f"  {n} days, {len(inyear)} highs and lows\n")
    print(f"  median daily range   {median:.2f} m")
    print(f"  max daily range      {hi_day[1]:.2f} m  on {hi_day[0]}")
    print(f"  min daily range      {lo_day[1]:.2f} m  on {lo_day[0]}")
    print(f"  year span            {min(e[2] for e in inyear):+.2f} m to {max(e[2] for e in inyear):+.2f} m")
    print("\n  Use these for a site file's \"Typical range\" row: median as \"typical,\"")
    print("  max daily range as \"up to,\" year span as printed.")


def _moment(a, doc):
    tz = zone_of(doc, a.tz)
    return tz, a.time.replace(tzinfo=tz).astimezone(timezone.utc)


def cmd_at(a):
    doc = station(a.station)
    tz, t = _moment(a, doc)
    h = height_at(doc, t)
    header(doc, f"{a.time:%Y-%m-%d %H:%M}  tide {h:+.2f} m MLLW", tz)
    print(f"  A feature X m below MLLW datum reads {h:+.2f} m {'deeper' if h >= 0 else 'shallower'} than X on the computer.")


def cmd_normalize(a):
    doc = station(a.station)
    tz, t = _moment(a, doc)
    h = height_at(doc, t)
    datum = a.depth - h
    header(doc, f"{a.time:%Y-%m-%d %H:%M}  tide {h:+.2f} m MLLW", tz)
    print(f"  observed depth      {a.depth:6.1f} m  (below the surface, as the computer read it)")
    print(f"  tide height        {h:+7.2f} m")
    print("  ---")
    print(f"  depth below MLLW    {datum:6.1f} m  <-- the comparable number. Log this.")
    print(f"\n  This is what to carry between dives. The {a.depth:.1f} m is only true at that tide.")


def cmd_project(a):
    doc = station(a.station)
    tz = zone_of(doc, a.tz)
    start, end = local_day(a.date, tz)
    ex = [e for e in extremes(doc, start - timedelta(hours=1), end + timedelta(hours=1)) if _round(e[0], tz).date() == a.date]
    header(doc, f"{a.date}  a feature {a.datum_depth:.1f} m below MLLW datum", tz)
    for t, kind, h in ex:
        print(f"  {_round(t, tz):%H:%M}  {'HIGH' if kind == 'H' else 'LOW '}  tide {h:+.2f} m   ->  reads {a.datum_depth + h:5.1f} m below surface")
    hs = [e[2] for e in ex]
    print(f"\n  Across the day it swings {a.datum_depth + min(hs):.1f} m – {a.datum_depth + max(hs):.1f} m below the surface.")
    print("  Plan gas and ppO2 against the deepest, not the average.")


def cmd_fetch(a):
    st = station_list()["stations"]
    if a.all:
        want = sorted(st)
    elif a.near:
        lat, lon = a.near
        scale = math.cos(math.radians(lat))
        want = [sid for sid, s in sorted(st.items())
                if math.hypot((s["lat"] - lat) * 60.0, (s["lon"] - lon) * 60.0 * scale) * 1.852 <= a.km]
    elif a.station:
        want = a.station
    else:
        sys.exit("name stations, or pass --near LAT LON [--km R], or --all.")
    want += [st[s]["ref"] for s in want if s in st and st[s]["ref"] and st[s]["ref"] in st]
    todo = sorted({s for s in want if not os.path.exists(os.path.join(DB, f"{s}.json"))})
    print(f"{len(set(want)) - len(todo)} of {len(set(want))} already cached; downloading {len(todo)}.", flush=True)
    for k, sid in enumerate(todo, 1):
        doc = station(sid, quiet=True)
        print(f"  {k}/{len(todo)}  {sid}  {doc['name']}", flush=True)
        _time.sleep(a.pause)
    print("done.")


def compare(doc, day0, days, height_tol, time_tol):
    """One station against NOAA's live API over `days` from `day0`: the height every six
    minutes at a reference station, and every high and low at any station."""
    utc = timezone.utc
    q = {"product": "predictions", "application": "NOS.COOPS.TAC.WL", "station": doc["id"], "datum": "MLLW",
         "time_zone": "gmt", "units": "metric", "format": "json",
         "begin_date": day0.strftime("%Y%m%d"), "end_date": (day0 + timedelta(days=days - 1)).strftime("%Y%m%d")}

    def api(**extra):
        d = get(f"{DG}?{urllib.parse.urlencode({**q, **extra})}")
        rows = d.get("predictions")
        if not isinstance(rows, list) or not rows:
            return (d.get("error") or {}).get("message") or str(rows)
        return [(datetime.strptime(p["t"], "%Y-%m-%d %H:%M").replace(tzinfo=utc), p.get("type"), float(p["v"]))
                for p in rows]

    r = {"station": doc["id"], "type": doc["type"], "ok": True}
    ref = reference(doc)
    if doc["type"] != "S":
        rows = api()
        if isinstance(rows, str):
            return {**r, "ok": False, "error": rows.strip()}
        worst = tot = 0.0
        for t, _, v in rows:
            d = height(ref, t) - v
            worst = max(worst, abs(d))
            tot += d * d
        r.update(height_n=len(rows), height_worst=round(worst, 4), height_rms=round(math.sqrt(tot / len(rows)), 4))
        r["ok"] &= worst <= height_tol
    theirs = api(interval="hilo")
    if isinstance(theirs, str):
        return {**r, "ok": False, "error": theirs.strip()}
    start = datetime.combine(day0, time(0), utc)
    mine = extremes(doc, start - timedelta(hours=6), start + timedelta(days=days, hours=6))
    dt_worst = dv_worst = 0.0
    missed = skipped = 0
    o = doc.get("offsets") or {}
    near = timedelta(minutes=60 + max(abs(o.get("timeOffsetHighTide") or 0), abs(o.get("timeOffsetLowTide") or 0)))
    for t, kind, v in theirs:
        # The node factors change at the first hour of the UTC year, a small step in the curve;
        # a high or low sitting on the step is left out and counted.
        if abs(t - datetime(t.year + (t.month == 12), 1, 1, tzinfo=utc)) <= near:
            skipped += 1
            continue
        cands = [(abs((m[0] - t).total_seconds()) / 60, m) for m in mine if m[1] == kind[0]]
        if not cands or min(cands, key=lambda c: c[0])[0] > 90:
            missed += 1
            continue
        dt, m = min(cands, key=lambda c: c[0])
        # An extreme on a flat top moves minutes for a hair of height; judge it on the height.
        if dt > time_tol and doc["type"] != "S" and abs(height(ref, t) - m[2]) <= 0.003:
            dt = 0.0
        dt_worst = max(dt_worst, dt)
        dv_worst = max(dv_worst, abs(m[2] - v))
    r.update(events_n=len(theirs), time_worst=round(dt_worst, 1), event_worst=round(dv_worst, 4), unmatched=missed, new_year=skipped)
    r["ok"] &= dt_worst <= time_tol and dv_worst <= height_tol and missed == 0
    return r


def _line(r):
    if "error" in r:
        return [f"  NOAA: no predictions to compare with ({r['error']})"]
    out = []
    if "height_n" in r:
        out.append(f"  height, {r['height_n']} six-minute values: worst difference {r['height_worst']:.3f} m, "
                   f"rms {r['height_rms']:.3f} m")
    out.append(f"  events, {r['events_n']} highs and lows: worst time difference {r['time_worst']:.1f} min, "
               f"worst height difference {r['event_worst']:.3f} m, {r['unmatched']} unmatched")
    if r.get("new_year"):
        out.append(f"  {r['new_year']} at the turn of the UTC year left out")
    return out


def cmd_verify(a):
    """Compare with NOAA's own predictions, read live from its API."""
    if a.all:
        return verify_all(a)
    if not a.station:
        sys.exit("name a station, or pass --all.")
    doc = station(a.station)
    print(f"{doc['id']}  {doc['name']}  {a.date} for {a.days} days, against NOAA's API\n")
    r = compare(doc, a.date, a.days, a.height_tol, a.time_tol)
    print("\n".join(_line(r)))
    print("\n  PASS" if r["ok"] else f"\n  FAIL: limits are {a.height_tol} m and {a.time_tol} min. The cached constants "
          "may be older than NOAA's; delete the station's file to fetch them again.")
    sys.exit(0 if r["ok"] else 1)


def verify_all(a):
    """Every cached station, one result per line in the cache folder's _verify.jsonl. A
    station already in that file is skipped, so a stopped run picks up where it left off;
    delete the file to start over."""
    done = {}
    if os.path.exists(REPORT):
        with open(REPORT) as f:
            for line in f:
                r = json.loads(line)
                done[r["station"]] = r
    todo = [sid for sid in sorted(station_list()["stations"])
            if os.path.exists(os.path.join(DB, f"{sid}.json")) and sid not in done]
    print(f"{len(done)} stations already verified; {len(todo)} to go, {a.days} days from {a.date}.", flush=True)
    for k, sid in enumerate(todo, 1):
        doc = station(sid)
        try:
            r = compare(doc, a.date, a.days, a.height_tol, a.time_tol)
        except SystemExit as e:
            if str(e).startswith("NOAA:"):  # a failed request stops the run, to be resumed later
                raise
            r = {"station": sid, "type": doc["type"], "ok": False, "error": str(e)}
        r.update(name=doc["name"], date=a.date.isoformat(), days=a.days)
        with open(REPORT, "a") as f:
            f.write(json.dumps(r) + "\n")
        done[sid] = r
        if k % 25 == 0 or not r["ok"]:
            print(f"  {k}/{len(todo)}  {sid} {doc['type']}  {'ok' if r['ok'] else 'FAIL'}", flush=True)
        _time.sleep(a.pause)
    print()
    for kind, label in (("R", "reference"), ("S", "subordinate")):
        rs = [r for r in done.values() if r["type"] == kind]
        bad = [r for r in rs if not r["ok"]]
        print(f"  {label}: {len(rs) - len(bad)} of {len(rs)} stations within {a.height_tol} m and {a.time_tol} min")
    print(f"  results: {os.path.relpath(REPORT, ROOT)}")


def when(s):
    return datetime.strptime(s, "%Y-%m-%d %H:%M")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    def zoned(sp):
        sp.add_argument("station")
        sp.add_argument("--tz", help="IANA zone for the times; default is the station's own zone")

    s = sub.add_parser("stations", help="find tide stations near a site")
    s.add_argument("--near", nargs=2, type=float, metavar=("LAT", "LON"), required=True)
    s.add_argument("-n", type=int, default=6)
    s.set_defaults(fn=cmd_stations)

    s = sub.add_parser("predict", help="high/low water for the day")
    zoned(s)
    s.add_argument("--date", type=date.fromisoformat, default=date.today())
    s.set_defaults(fn=cmd_predict)

    s = sub.add_parser("range", help="median/max/min daily range and span across a year")
    zoned(s)
    s.add_argument("--year", type=int, default=date.today().year)
    s.set_defaults(fn=cmd_range)

    s = sub.add_parser("at", help="tide height at a moment")
    zoned(s)
    s.add_argument("--time", type=when, required=True, metavar='"YYYY-MM-DD HH:MM"')
    s.set_defaults(fn=cmd_at)

    s = sub.add_parser("normalize", help="observed depth -> depth below MLLW datum")
    zoned(s)
    s.add_argument("--time", type=when, required=True, metavar='"YYYY-MM-DD HH:MM"')
    s.add_argument("--depth", type=float, required=True, help="metres, as the computer read it")
    s.set_defaults(fn=cmd_normalize)

    s = sub.add_parser("project", help="datum depth -> depth below surface through the day")
    zoned(s)
    s.add_argument("--datum-depth", type=float, required=True, help="metres below MLLW")
    s.add_argument("--date", type=date.fromisoformat, default=date.today())
    s.set_defaults(fn=cmd_project)

    s = sub.add_parser("fetch", help="cache stations ahead of time")
    s.add_argument("station", nargs="*")
    s.add_argument("--near", nargs=2, type=float, metavar=("LAT", "LON"))
    s.add_argument("--km", type=float, default=50.0, help="radius for --near, default 50")
    s.add_argument("--all", action="store_true", help="every station NOAA lists")
    s.add_argument("--pause", type=float, default=0.3, help="seconds between stations, default 0.3")
    s.set_defaults(fn=cmd_fetch)

    s = sub.add_parser("verify", help="compare with NOAA's live API")
    s.add_argument("station", nargs="?")
    s.add_argument("--all", action="store_true", help="every cached station")
    s.add_argument("--date", type=date.fromisoformat, default=date.today())
    s.add_argument("--days", type=int, default=30)
    s.add_argument("--height-tol", type=float, default=0.02, help="metres, default 0.02")
    s.add_argument("--time-tol", type=float, default=3.0, help="minutes, default 3")
    s.add_argument("--pause", type=float, default=0.2, help="seconds between stations with --all, default 0.2")
    s.set_defaults(fn=cmd_verify)

    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()

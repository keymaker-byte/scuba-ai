"""NOAA CO-OPS tide predictions computed on this machine, shared by noaa_tide.py and
map_export.py: NOAA's station list and each station's constants and datums, downloaded when
missing, and the height of the tide at any moment, in metres above MLLW."""
import itertools
import json
import math
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta

import lib.tidal_astronomy as astro

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


DB = os.path.join(ROOT, "tools", "db", "noaa_tide")


LIST = os.path.join(DB, "stations.json")


VDATUM_FILE = os.path.join(ROOT, "tools", "db", "ncei_depth", "vdatum.json")  # ncei_depth --mllw keeps it


MD = "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations"


DG = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"


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
        doc["navd88"] = d.get("NAVD88")
    _save(path, doc)
    return doc


def navd88(doc):
    """NAVD 88's height above MLLW at a reference station, metres, or None where NOAA ties
    the station to no NAVD 88. A station file cached before this was kept has its datums
    downloaded again once, and the answer saved with it."""
    if "navd88" not in doc:
        dat = get(f"{MD}/{doc['id']}/datums.json?units=metric") or {}
        if "datums" not in dat:
            sys.exit(f"NOAA: no datums answer for {doc['id']}. Nothing was changed. Retry later.")
        doc["navd88"] = {x["name"]: x["value"] for x in dat.get("datums") or []}.get("NAVD88")
        _save(os.path.join(DB, f"{doc['id']}.json"), doc)
    if doc["navd88"] is None or doc.get("mllw") is None:
        return None
    return doc["navd88"] - doc["mllw"]


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


# Degrees per hour of T, s, h, p, p1: what a constituent's argument coefficients add up to.
RATE = (15.0, 0.54901653, 0.04106864, 0.00464183, 0.00000196)


# Constituents beyond lib/tidal_astronomy.py's 37: (T, s, h, p, p1) coefficients, constant, nodal parts.
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
    key = astro.ALIAS.get(name.upper(), name.upper())
    return astro.CONS.get(key) or EXTRA.get(key)


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
    nd = astro.nodal(year)
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
    s, h, p, _, p1 = astro.longitudes(t)
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

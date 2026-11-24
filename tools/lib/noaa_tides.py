"""NOAA CO-OPS tide prediction stations as the tide tool keeps them on this machine: NOAA's station
list and one file per station, downloaded from NOAA's metadata API when missing; a reference
station's height from its harmonic constants, a subordinate station's from its reference moved
by NOAA's corrections; and the comparison of either with NOAA's own live predictions. Heights
are metres above MLLW. `lib/tide.py` reads it as the NOAA source."""
import json
import math
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, time, timedelta, timezone

from lib.tide_harmonics import extremes as find_extremes, height as harmonic_height

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(TOOLS, "db", "tide", "noaa")
LIST = os.path.join(DB, "stations.json")
MD = "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations"
DG = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
UTC = timezone.utc


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


def cached(sid):
    return os.path.exists(os.path.join(DB, f"{sid}.json"))


# --- the cache: station list, then one file per station ----------------------------------

def station_list():
    """Every tide prediction station NOAA lists, keyed by ID: name, lat, lon, type ("R" or "S")
    and, for a subordinate station, its reference."""
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
                 "stations with `stations --near`. Delete tools/db/tide/noaa/stations.json to list again.")
    if not quiet:
        print(f"downloading NOAA {sid} {e['name']} ...", file=sys.stderr)
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


def unusable(doc):
    """Why a reference station's file cannot predict, or None when it can."""
    if not doc.get("cons"):
        return "NOAA lists the station and publishes no harmonic constants for it, so there is nothing to predict from"
    if doc.get("msl") is None or doc.get("mllw") is None:
        return "NOAA publishes no MSL or MLLW datum for it, so its predictions cannot be placed on MLLW"
    return None


def reference(doc):
    """The station whose constants predict this one: itself, or a subordinate's reference."""
    if doc["type"] != "S":
        ref = doc
    else:
        ref = station(doc["offsets"]["refStationId"])
        if ref["type"] == "S":
            sys.exit(f"{doc['id']}'s reference {ref['id']} is itself subordinate; nothing to correct.")
    why = unusable(ref)
    if why:
        sys.exit(f"{ref['id']} {ref['name']}: {why}.")
    return ref


def constants(ref):
    """A reference station's constants in the form lib/tide_harmonics.py sums."""
    return {"key": f"noaa:{ref['id']}", "cons": ref["cons"], "z0": ref["msl"] - ref["mllw"]}


def height(ref, t):
    """Tide height at a reference station at UTC datetime t, metres above MLLW."""
    return harmonic_height(constants(ref), t)


# --- prediction at any station -------------------------------------------------------------

def extremes(doc, start, end, step=6):
    """Highs and lows between two UTC datetimes: [(utc datetime, "H" or "L", metres)]. A
    subordinate station's are its reference's, each moved and scaled by NOAA's corrections."""
    ref = reference(doc)
    o = doc.get("offsets")
    pad = timedelta(minutes=(max(abs(o["timeOffsetHighTide"] or 0), abs(o["timeOffsetLowTide"] or 0)) if o else 0) + 3 * step)
    out = find_extremes(lambda t: height(ref, t), start - pad, end + pad, step)
    if o:
        out = [(tc, kind, vc) for t, kind, v in out for tc, vc in [_correct(o, t, kind, v)]]
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


# --- the check against NOAA's live predictions ---------------------------------------------

def compare(doc, day0, days, height_tol, time_tol):
    """One station against NOAA's live API over `days` from `day0`: the height every six
    minutes at a reference station, and every high and low at any station."""
    q = {"product": "predictions", "application": "NOS.COOPS.TAC.WL", "station": doc["id"], "datum": "MLLW",
         "time_zone": "gmt", "units": "metric", "format": "json",
         "begin_date": day0.strftime("%Y%m%d"), "end_date": (day0 + timedelta(days=days - 1)).strftime("%Y%m%d")}

    def api(**extra):
        d = get(f"{DG}?{urllib.parse.urlencode({**q, **extra})}")
        rows = d.get("predictions")
        if not isinstance(rows, list) or not rows:
            return (d.get("error") or {}).get("message") or str(rows)
        return [(datetime.strptime(p["t"], "%Y-%m-%d %H:%M").replace(tzinfo=UTC), p.get("type"), float(p["v"]))
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
    start = datetime.combine(day0, time(0), UTC)
    mine = extremes(doc, start - timedelta(hours=6), start + timedelta(days=days, hours=6))
    dt_worst = dv_worst = 0.0
    missed = skipped = 0
    o = doc.get("offsets") or {}
    near = timedelta(minutes=60 + max(abs(o.get("timeOffsetHighTide") or 0), abs(o.get("timeOffsetLowTide") or 0)))
    for t, kind, v in theirs:
        # The node factors change at the first hour of the UTC year, a small step in the curve;
        # a high or low sitting on the step is left out and counted.
        if abs(t - datetime(t.year + (t.month == 12), 1, 1, tzinfo=UTC)) <= near:
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

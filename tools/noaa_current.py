#!/usr/bin/env python3
"""NOAA current predictions computed locally from NOAA's published harmonic constants:
slack, max flood/ebb, and diveable windows, with no request once a station is cached.

  noaa_current.py stations --near LAT LON                 current stations near a site
  noaa_current.py bins STATION                            bins, their depths and types
  noaa_current.py predict STATION --bin B [--date D]      slack / max flood / max ebb
  noaa_current.py window STATION --bin B [--date D]       diveable windows under a speed threshold
  noaa_current.py fetch [STATION ...] [--near LAT LON --km R] [--all]   cache stations ahead of time
  noaa_current.py verify STATION --bin B [--date D] [--days N]          compare with NOAA's live API
"""
import argparse
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
from lib.tidal_astronomy import ALIAS, CONS, EPOCH, longitudes, nodal  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "tools", "db", "noaa_current")
LIST = os.path.join(DB, "stations.json")
REPORT = os.path.join(DB, "_verify.jsonl")
MD = "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations"
DG = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
KN = 0.514444  # m/s per knot


def _cfg(key, default):
    """Read this tool's section of tool-config.json; missing file or key -> default."""
    try:
        with open(os.path.join(ROOT, "tool-config.json")) as f:
            return json.load(f).get("noaa_current", {}).get(key, default)
    except (OSError, ValueError):
        return default


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
    """Every current station NOAA lists, keyed by ID, each with its bins (number, type, depth)."""
    if os.path.exists(LIST):
        with open(LIST) as f:
            return json.load(f)
    print("downloading NOAA's current station list ...", file=sys.stderr)
    rows = (get(f"{MD}.json?type=currentpredictions&units=metric") or {}).get("stations")
    if not rows:
        sys.exit("NOAA: the station list came back empty. Nothing was cached. Retry later.")
    st = {}
    for s in rows:  # one row per station bin
        e = st.setdefault(s["id"], {"name": s["name"], "lat": s["lat"], "lon": s["lng"],
                                    "tz_offset": s.get("timezone_offset") or None, "bins": {}})
        e["bins"][str(s["currbin"])] = {"type": s.get("type"), "depth": s.get("depth")}
    doc = {"fetched": date.today().isoformat(), "stations": st}
    _save(LIST, doc)
    return doc


def _entry(sid):
    st = station_list()["stations"]
    if sid not in st:
        sys.exit(f"{sid} is not in NOAA's current station list (fetched {station_list()['fetched']}). "
                 "List stations with `stations --near`; a retired reference station is read with "
                 "noaa_legacy_current. Delete tools/db/noaa_current/stations.json to list again.")
    return st[sid]


def station(sid, quiet=False):
    """One station's cached file: its metadata, every bin's constants, and any bin's
    subordinate offsets. Downloaded on first use."""
    path = os.path.join(DB, f"{sid}.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    e = _entry(sid)
    if not quiet:
        print(f"downloading {sid} {e['name']} ...", file=sys.stderr)
    meta = (get(f"{MD}/{sid}.json?type=currentpredictions&units=metric") or {}).get("stations") or [{}]
    doc = {"id": sid, "fetched": date.today().isoformat(), "name": e["name"], "lat": e["lat"], "lon": e["lon"],
           "tz_offset": meta[0].get("timezone_offset") or e["tz_offset"],
           "observes_dst": meta[0].get("observedst"),
           "project": meta[0].get("project"), "bins": {}}
    depths = {}
    if any(b["type"] != "S" for b in e["bins"].values()):
        har = get(f"{MD}/{sid}/harcon.json?units=metric") or {}
        if "HarmonicConstituents" not in har:
            sys.exit(f"NOAA: no harmonic constants answer for {sid}. Nothing was cached. Retry later.")
        for c in har["HarmonicConstituents"]:
            b = doc["bins"].setdefault(str(c["binNbr"]), {
                "depth": c.get("binDepth"), "azimuth": c.get("azi"),
                "mean_major": c.get("majorMeanSpeed"), "mean_minor": c.get("minorMeanSpeed"), "cons": []})
            b["cons"].append([c["constituentName"], c["majorAmplitude"], c["majorPhaseGMT"],
                              c["minorAmplitude"], c["minorPhaseGMT"]])
        bins = get(f"{MD}/{sid}/bins.json?units=metric", missing_ok=True) or {}
        depths = {str(b["num"]): b.get("depth") for b in bins.get("bins") or []}
    for num, b in doc["bins"].items():
        if b["depth"] is None:
            b["depth"] = depths.get(num)
    for num, pb in e["bins"].items():  # the bins NOAA publishes predictions for
        b = doc["bins"].setdefault(num, {"depth": pb["depth"], "cons": []})
        b["type"] = pb["type"]
        if pb["depth"] is not None:
            b["depth"] = pb["depth"]
        if pb["type"] == "S":
            off = get(f"{MD}/{sid}_{num}/currentpredictionoffsets.json?units=metric")
            if "refStationId" not in (off or {}):
                sys.exit(f"NOAA: no subordinate offsets answer for {sid} bin {num}. Nothing was cached.")
            b["offsets"] = {k: off.get(k) for k in (
                "refStationId", "refStationBin", "meanFloodDir", "meanEbbDir", "sbfTimeAdjMin",
                "mfcTimeAdjMin", "sbeTimeAdjMin", "mecTimeAdjMin", "mfcAmpAdj", "mecAmpAdj")}
        elif pb["type"] == "H":
            dirs = get(f"{MD}/{sid}_{num}/currentpredictionoffsets.json?units=metric", missing_ok=True) or {}
            b["flood_dir"], b["ebb_dir"] = dirs.get("meanFloodDir"), dirs.get("meanEbbDir")
    _save(path, doc)
    return doc


def pick_bin(doc, num):
    """The bin asked for, or stop: every multi-bin station needs one named."""
    bins = doc["bins"]
    if num is None:
        if len(bins) == 1:
            num = next(iter(bins))
        else:
            sys.exit(f"{doc['id']} has {len(bins)} bins; pass --bin with the site file's Recommended bin. "
                     f"List them with `bins {doc['id']}`.")
    b = bins.get(str(num))
    if b is None:
        sys.exit(f"{doc['id']} has no bin {num}. List its bins with `bins {doc['id']}`.")
    if b.get("type") == "W":
        sys.exit(f"NOAA: {doc['id']} bin {num}: Currents are weak and variable. No predictions are "
                 "published for it.")
    if b.get("type") != "S" and not b.get("cons"):
        sys.exit(f"{doc['id']} bin {num}: NOAA lists the bin and publishes no constants for it, so there "
                 f"is nothing to predict from. List the station's bins with `bins {doc['id']}`.")
    return str(num), b


def zone_of(name):
    """The zone every time prints in: the site's own, passed as --tz."""
    try:
        return ZoneInfo(name)
    except Exception:
        sys.exit(f"{name} is not an IANA time zone name. Pass the site's `tz` from its JSON, e.g. America/Los_Angeles.")


# --- astronomy: lib/tidal_astronomy.py ---------------------------------------------------


def prepare(cons, year):
    """Constants ready to sum for one year: per constituent, the argument coefficients, and
    the node factor and phase of that year."""
    nd = nodal(year)
    out = []
    for name, amaj, gmaj, amin, gmin in cons:
        key = ALIAS.get(name.upper(), name.upper())
        if key not in CONS:
            sys.exit(f"constituent {name} is not one this tool can predict; the station's constants "
                     "changed shape. Report it rather than predicting without it.")
        coef, const, parts = CONS[key]
        f, u = 1.0, 0.0
        for base, power in parts:
            f *= nd[base][0] ** abs(power)
            u += nd[base][1] * power
        out.append((coef, const + u, f * amaj, gmaj, f * amin, gmin))
    return out


_PREP = {}


def speed(b, t):
    """Signed speed along the bin's major axis at UTC datetime t, m/s, flood positive: the
    bin's mean current plus the sum of its constituents."""
    key = (id(b), t.year)
    if key not in _PREP:  # the entry holds b itself, so its id stays this bin's for the whole run
        _PREP[key] = (b, prepare(b["cons"], t.year))
    s, h, p, _, p1 = longitudes(t)
    T = 15.0 * (t.hour + t.minute / 60 + t.second / 3600 + t.microsecond / 3.6e9) + 180.0
    major = b.get("mean_major") or 0.0
    for (cT, cs, ch, cp, cp1), const, amaj, gmaj, _, _ in _PREP[key][1]:
        major += amaj * math.cos(math.radians(cT * T + cs * s + ch * h + cp * p + cp1 * p1 + const - gmaj))
    return major / 100.0


def series(b, start, minutes, step=1):
    """[(utc datetime, speed)] every `step` minutes from `start`."""
    return [(start + timedelta(minutes=m), speed(b, start + timedelta(minutes=m)))
            for m in range(0, minutes + 1, step)]


def events(ser):
    """Slacks, and the maximum flood and ebb between them: [(utc datetime, kind, speed)]."""
    out = []
    for k in range(1, len(ser)):
        (t0, v0), (t1, v1) = ser[k - 1], ser[k]
        if (v0 < 0) != (v1 < 0):
            out.append((t0 + (t1 - t0) * (v0 / (v0 - v1)), "slack", 0.0))
        if k + 1 < len(ser):
            v2 = ser[k + 1][1]
            if (v1 - v0) * (v2 - v1) < 0 or (v1 == v2 and v1 != v0):
                den = v0 - 2 * v1 + v2
                x = 0.5 * (v0 - v2) / den if den else 0.0
                peak = v1 - 0.25 * (v0 - v2) * x
                top = v1 > v0
                kind = ("flood" if top else "min flood") if peak > 0 else ("min ebb" if top else "ebb")
                out.append((t1 + (ser[k + 1][0] - t1) * x, kind, peak))
    return out


def day_span(day, tz, pad=0):
    start = datetime.combine(day, time(0), tz).astimezone(timezone.utc)
    end = datetime.combine(day + timedelta(days=1), time(0), tz).astimezone(timezone.utc)
    return start - timedelta(minutes=pad), int((end - start).total_seconds() // 60) + 2 * pad


# --- subordinate bins: NOAA's corrections applied to the reference station's events --------

def reference(b):
    o = b["offsets"]
    rdoc = station(o["refStationId"])
    rnum, rb = pick_bin(rdoc, o["refStationBin"])
    if rb.get("type") == "S" or not rb.get("cons"):
        sys.exit(f"reference {rdoc['id']} bin {rnum} carries no harmonic constants; nothing to correct.")
    return rdoc, rnum, rb


def subordinate_events(b, day, tz):
    """The reference's events, each moved by its own time correction and each maximum scaled
    by its speed ratio. NOAA publishes a subordinate station as these events alone."""
    o = b["offsets"]
    _, _, rb = reference(b)
    start, minutes = day_span(day, tz, pad=720)
    ref = events(series(rb, start, minutes))
    out = []
    for k, (t, kind, v) in enumerate(ref):
        base = kind.replace("min ", "")
        if kind == "slack":
            # A slack before flood is the one the flood follows.
            after = next((x[1].replace("min ", "") for x in ref[k + 1:] if x[1] != "slack"), None)
            before = next((x[1].replace("min ", "") for x in reversed(ref[:k]) if x[1] != "slack"), None)
            to_flood = after == "flood" if after else before == "ebb"
            adj, ratio = o["sbfTimeAdjMin"] if to_flood else o["sbeTimeAdjMin"], 0.0
        elif base == "flood":
            adj, ratio = o["mfcTimeAdjMin"], o["mfcAmpAdj"]
        else:
            adj, ratio = o["mecTimeAdjMin"], o["mecAmpAdj"]
        out.append((t + timedelta(minutes=adj or 0), kind, v * (ratio or 0)))
    return sorted(out)


# --- commands ----------------------------------------------------------------------------

def header(doc, num, b, day, tz):
    depth = f" @ {b['depth']} m" if b.get("depth") is not None else ""
    print(f"{doc['id']}  {doc['name']}  {day}  bin {num}{depth}  ({getattr(tz, 'key', None) or tz.tzname(None)})")
    if b.get("type") == "S":
        o = b["offsets"]
        print(f"  flood {o['meanFloodDir']:.0f}°   ebb {o['meanEbbDir']:.0f}°   subordinate to {o['refStationId']} "
              f"bin {o['refStationBin']}")
        if len(doc["bins"]) > 1:
            print("  A subordinate bin of a multi-bin station: these are the bin's own published corrections. "
                  "NOAA's API answers every bin of such a station with its first bin's, so the two can "
                  "differ. `verify` says which.")
    else:
        if b.get("flood_dir") is not None:
            print(f"  flood {b['flood_dir']:.0f}°   ebb {b['ebb_dir']:.0f}°")
        else:
            print(f"  major axis {b['azimuth']}°, flood positive along it")
        if b.get("type") is None:
            print("  NOAA publishes no predictions for this bin; this one is computed from its constants alone.")
    print(f"  computed locally from NOAA's constants as fetched {doc['fetched']}\n")


def cmd_stations(a):
    doc = station_list()
    lat, lon = a.near
    scale = math.cos(math.radians(lat))
    rows = []
    for sid, s in doc["stations"].items():
        km = math.hypot((s["lat"] - lat) * 60.0, (s["lon"] - lon) * 60.0 * scale) * 1.852
        rows.append((km, sid, s))
    rows.sort(key=lambda x: x[0])
    print(f"NOAA current stations near {lat:.4f}, {lon:.4f} (list fetched {doc['fetched']}):\n")
    for km, sid, s in rows[: a.n]:
        types = "".join(sorted({b["type"] or "?" for b in s["bins"].values()}))
        cached = "cached" if os.path.exists(os.path.join(DB, f"{sid}.json")) else ""
        print(f"  {sid:<10} {types:<3} {km:6.1f} km  {s['name']}  {cached}")
    print("\nType: H harmonic (its own constants, usually with depth bins), S subordinate (corrections")
    print("to a reference station), W weak and variable (no predictions).")


def cmd_bins(a):
    doc = station(a.station)
    print(f"{doc['id']}  {doc['name']}   {doc['lat']:.4f}, {doc['lon']:.4f}")
    if doc.get("project"):
        print(f"  project: {doc['project']}")
    print(f"  constants fetched {doc['fetched']}\n")
    for num, b in sorted(doc["bins"].items(), key=lambda x: int(x[0])):
        depth = f"{b['depth']} m" if b.get("depth") is not None else "depth unknown"
        kind = {"H": "harmonic, published by NOAA", "S": "subordinate, published by NOAA",
                "W": "weak and variable, no predictions", None: "constants only, unpublished"}[b.get("type")]
        extra = f"   to {b['offsets']['refStationId']} bin {b['offsets']['refStationBin']}" if b.get("offsets") else ""
        if b.get("type") != "S" and b.get("type") != "W" and not b.get("cons"):
            kind = "listed by NOAA with no constants, no predictions"
        print(f"    bin {num:<3} {depth:<14} {kind}{extra}")
    print("\n  The site's Recommended bin is the published bin nearest the dive area's seabed depth.")


def cmd_predict(a):
    doc = station(a.station)
    num, b = pick_bin(doc, a.bin)
    tz = zone_of(a.tz)
    header(doc, num, b, a.date, tz)
    if b.get("type") == "S":
        ev = subordinate_events(b, a.date, tz)
    else:
        start, minutes = day_span(a.date, tz, pad=5)
        ev = events(series(b, start, minutes))
    for t, kind, v in ev:
        t = (t + timedelta(seconds=30)).astimezone(tz)
        if t.date() != a.date:
            continue
        if kind == "slack":
            print(f"  {t:%H:%M}  SLACK")
        else:
            extra = f"  {v / KN:+.2f} kn" if a.knots else ""
            print(f"  {t:%H:%M}  {kind:<9} {v:+.2f} m/s{extra}")


def cmd_window(a):
    doc = station(a.station)
    num, b = pick_bin(doc, a.bin)
    if b.get("type") == "S":
        sys.exit(f"{doc['id']} bin {num} is subordinate: NOAA defines it by its slacks and maxima alone, "
                 "with no speed curve between them to measure a window on. Use `predict`.")
    tz = zone_of(a.tz)
    lim = a.max_speed
    header(doc, num, b, a.date, tz)
    print(f"  windows with |current| <= {lim:.2f} m/s\n")
    start, minutes = day_span(a.date, tz)
    runs, cur = [], []
    for t, v in series(b, start, minutes)[:-1]:
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
        mins = len(run)
        peak = max(abs(v) for _, v in run)
        if mins >= minutes:
            print(f"  all day          peak {peak:.2f} m/s")
            continue
        t0, t1 = run[0][0].astimezone(tz), (run[-1][0] + timedelta(minutes=1)).astimezone(tz)
        flag = "  <-- tight" if mins < 40 else ""
        print(f"  {t0:%H:%M} - {t1:%H:%M}   {mins:>3} min   peak {peak:.2f} m/s{flag}")
    print("\n  Times are AT THE STATION. Apply the site offset, and pad it until observed.")


def cmd_fetch(a):
    lst = station_list()["stations"]
    want = list(a.station)
    for sid in want:
        _entry(sid)
    if a.near:
        lat, lon = a.near
        scale = math.cos(math.radians(lat))
        want += [sid for sid, s in lst.items()
                 if math.hypot((s["lat"] - lat) * 60.0, (s["lon"] - lon) * 60.0 * scale) * 1.852 <= a.km]
    if a.all:
        want = list(lst)
    if not want:
        sys.exit("name stations, or pass --near LAT LON [--km R], or --all.")
    todo = [s for s in dict.fromkeys(want) if not os.path.exists(os.path.join(DB, f"{s}.json"))]
    print(f"{len(want) - len(todo)} of {len(dict.fromkeys(want))} already cached; downloading {len(todo)}.")
    for k, sid in enumerate(todo, 1):
        station(sid, quiet=True)
        print(f"  {k}/{len(todo)}  {sid}  {lst[sid]['name']}")
        _time.sleep(a.pause)
    # A subordinate bin predicts from its reference station; cache those too.
    refs = set()
    for sid in dict.fromkeys(want):
        for b in station(sid)["bins"].values():
            if b.get("offsets"):
                refs.add(b["offsets"]["refStationId"])
    for sid in sorted(r for r in refs if not os.path.exists(os.path.join(DB, f"{r}.json"))):
        station(sid, quiet=True)
        print(f"  reference  {sid}  {lst.get(sid, {}).get('name', '')}")
        _time.sleep(a.pause)
    print("done.")


def compare(doc, num, b, day0, days, speed_tol, time_tol):
    """One bin against NOAA's live API over `days` from `day0`: the speed every six minutes
    on a harmonic bin, and every slack and maximum on any bin. Returns the differences."""
    sub = b.get("type") == "S"
    utc = timezone.utc
    q = {"product": "currents_predictions", "application": "NOS.COOPS.TAC.CUR", "station": doc["id"],
         "bin": num, "time_zone": "gmt", "units": "metric", "format": "json",
         "begin_date": day0.strftime("%Y%m%d"), "end_date": (day0 + timedelta(days=days - 1)).strftime("%Y%m%d")}

    def api(interval):
        d = get(f"{DG}?{urllib.parse.urlencode({**q, 'interval': interval})}")
        cp = (d.get("current_predictions") or {}).get("cp")
        if not isinstance(cp, list) or not cp:
            return (d.get("error") or {}).get("message") or str(cp)
        return [(datetime.strptime(c["Time"], "%Y-%m-%d %H:%M").replace(tzinfo=utc), c.get("Type"),
                 float(c["Velocity_Major"]) / 100.0) for c in cp]

    r = {"station": doc["id"], "bin": num, "type": b.get("type"), "ok": True}
    if not sub:
        rows = api("6")
        if isinstance(rows, str):
            return {**r, "ok": False, "error": rows.strip()}
        worst = tot = 0.0
        for t, _, v in rows:
            got = speed(b, t)
            worst = max(worst, abs(got - v))
            tot += (got - v) ** 2
        r.update(speed_n=len(rows), speed_worst=round(worst, 4), speed_rms=round(math.sqrt(tot / len(rows)), 4))
        r["ok"] &= worst <= speed_tol
    theirs = api("MAX_SLACK")
    if isinstance(theirs, str):
        return {**r, "ok": False, "error": theirs.strip()}
    adj = [0] + [b["offsets"].get(k) or 0 for k in ("sbfTimeAdjMin", "mfcTimeAdjMin", "sbeTimeAdjMin",
                                                     "mecTimeAdjMin")] if sub else [0]

    def match(bin_):
        """(worst minutes, worst peak difference, unmatched, left out) of NOAA's events against
        this tool's for `bin_`."""
        mine = []
        for k in range(days):
            day = day0 + timedelta(days=k)
            if sub:
                mine += subordinate_events(bin_, day, utc)
            else:
                start, minutes = day_span(day, utc, pad=5)
                mine += events(series(bin_, start, minutes))
        dt_worst = dv_worst = 0.0
        missed = skipped = 0
        for t, kind, v in theirs:
            # NOAA's slack and maximum product keeps the old year's node factors for some hours
            # into a new UTC year, while its own speed series changes at the first hour. A
            # subordinate event carries its reference's hour, moved by the bin's correction.
            ny = datetime(t.year + (t.month == 12), 1, 1, tzinfo=utc)
            if ny + timedelta(minutes=-60 + min(adj)) <= t < ny + timedelta(minutes=720 + max(adj)):
                skipped += 1
                continue
            # NOAA calls a weak point between two floods a flood, or a slack when it is near
            # zero, and likewise for ebb; here both are a "min flood" or "min ebb".
            cands = [(abs((m[0] - t).total_seconds()) / 60, m) for m in mine
                     if m[1] == kind or (m[1].startswith("min ") and (kind == "slack" or m[1][4:] == kind))]
            if not cands or min(cands, key=lambda c: c[0])[0] > 90:
                missed += 1
                continue
            dt, m = min(cands, key=lambda c: c[0])
            # A slack on a flat curve moves minutes for a hair of speed; judge it on the speed.
            if kind == "slack" and not sub and dt > time_tol and abs(speed(bin_, t)) <= speed_tol:
                continue
            # A maximum on a flat top likewise: NOAA's minute holds the same speed as this one.
            if kind != "slack" and not sub and dt > time_tol and abs(speed(bin_, t) - m[2]) <= 0.005:
                dt = 0.0
            dt_worst = max(dt_worst, dt)
            if kind != "slack":
                dv_worst = max(dv_worst, abs(m[2] - v))
        return dt_worst, dv_worst, missed, skipped

    def good(res):
        return res[0] <= time_tol and res[1] <= speed_tol and res[2] == 0

    res = match(b)
    r.update(events_n=len(theirs), time_worst=round(res[0], 1), peak_worst=round(res[1], 4),
             unmatched=res[2], new_year_skipped=res[3])
    r["ok"] &= good(res)
    if sub and not r["ok"]:
        # NOAA's API answers every bin of a multi-bin subordinate station with the corrections
        # of the station's first bin. Say whether that is what happened here.
        first = min((n for n, x in doc["bins"].items() if x.get("type") == "S"), key=int)
        if first != num:
            adj += [doc["bins"][first]["offsets"].get(k) or 0 for k in (
                "sbfTimeAdjMin", "mfcTimeAdjMin", "sbeTimeAdjMin", "mecTimeAdjMin")]
            r["noaa_used_bin"] = first if good(match(doc["bins"][first])) else None
    return r


def _line(r):
    out = []
    if "error" in r:
        return [f"  NOAA: no predictions to compare with ({r['error']})"]
    if "speed_n" in r:
        out.append(f"  speed, {r['speed_n']} six-minute values: worst difference {r['speed_worst']:.3f} m/s, "
                   f"rms {r['speed_rms']:.3f} m/s")
    note = f", {r['new_year_skipped']} in the first hours of a new year left out" if r["new_year_skipped"] else ""
    out.append(f"  events, {r['events_n']} slacks and maxima: worst time difference {r['time_worst']:.1f} min, "
               f"worst peak difference {r['peak_worst']:.3f} m/s, {r['unmatched']} unmatched{note}")
    if r.get("noaa_used_bin"):
        out.append(f"  NOAA's API answered this bin with the corrections of bin {r['noaa_used_bin']}; this tool "
                   "applies the bin's own published corrections.")
    return out


def cmd_verify(a):
    """Compare with NOAA's own predictions, read live from its API."""
    if a.all:
        return verify_all(a)
    if not a.station:
        sys.exit("name a station, or pass --all.")
    doc = station(a.station)
    num, b = pick_bin(doc, a.bin)
    if b.get("type") is None:
        sys.exit(f"NOAA publishes no predictions for {doc['id']} bin {num}; there is nothing to compare with.")
    print(f"{doc['id']}  {doc['name']}  bin {num}  {a.date} for {a.days} days, against NOAA's API\n")
    r = compare(doc, num, b, a.date, a.days, a.speed_tol, a.time_tol)
    print("\n".join(_line(r)))
    print("\n  PASS" if r["ok"] else f"\n  FAIL: limits are {a.speed_tol} m/s and {a.time_tol} min." + (
              "" if r.get("noaa_used_bin") else " The cached constants may be older than NOAA's; delete the "
              "station's file to fetch them again."))
    sys.exit(0 if r["ok"] else 1)


def verify_all(a):
    """Every published harmonic and subordinate bin of every cached station, one result per
    line in the cache folder's _verify.jsonl. A bin already in that file is skipped, so a
    stopped run picks up where it left off; delete the file to start over."""
    done = {}
    if os.path.exists(REPORT):
        with open(REPORT) as f:
            for line in f:
                r = json.loads(line)
                done[(r["station"], r["bin"])] = r
    todo = []
    for sid, e in sorted(station_list()["stations"].items()):
        if not os.path.exists(os.path.join(DB, f"{sid}.json")):
            continue
        for num, pb in sorted(e["bins"].items(), key=lambda x: int(x[0])):
            if pb["type"] in ("H", "S") and (sid, num) not in done:
                todo.append((sid, num))
    print(f"{len(done)} bins already verified; {len(todo)} to go, {a.days} days from {a.date}.", flush=True)
    for k, (sid, num) in enumerate(todo, 1):
        doc = station(sid)
        b = doc["bins"][num]
        try:
            pick_bin(doc, num)
            r = compare(doc, num, b, a.date, a.days, a.speed_tol, a.time_tol)
        except SystemExit as e:
            # A reference station that cannot be read is this bin's result; a failed request
            # to NOAA stops the run, to be picked up again later.
            if str(e).startswith("NOAA:") and "weak and variable" not in str(e):
                raise
            r = {"station": sid, "bin": num, "type": b.get("type"), "ok": False, "error": str(e)}
        r.update(name=doc["name"], date=a.date.isoformat(), days=a.days, bins=len(doc["bins"]))
        with open(REPORT, "a") as f:
            f.write(json.dumps(r) + "\n")
        done[(sid, num)] = r
        if k % 25 == 0 or not r["ok"]:
            print(f"  {k}/{len(todo)}  {sid} bin {num} {b.get('type')}  {'ok' if r['ok'] else 'FAIL'}", flush=True)
        _time.sleep(a.pause)
    print()
    for kind, label in (("H", "harmonic"), ("S", "subordinate")):
        rs = [r for r in done.values() if r["type"] == kind]
        bad = [r for r in rs if not r["ok"]]
        print(f"  {label}: {len(rs) - len(bad)} of {len(rs)} bins within {a.speed_tol} m/s and {a.time_tol} min")
    print(f"  results: {os.path.relpath(REPORT, ROOT)}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("stations", help="current stations near a site")
    s.add_argument("--near", nargs=2, type=float, metavar=("LAT", "LON"), required=True)
    s.add_argument("-n", type=int, default=6)
    s.set_defaults(fn=cmd_stations)

    s = sub.add_parser("bins", help="bins, their depths and types")
    s.add_argument("station")
    s.set_defaults(fn=cmd_bins)

    def dated(sp):
        sp.add_argument("station")
        sp.add_argument("--date", type=date.fromisoformat, default=date.today())
        sp.add_argument("--bin", type=int, help="the site file's Recommended bin")

    def zoned(sp):
        sp.add_argument("--tz", required=True, metavar="IANA_ZONE", help="the site's time zone, the `tz` in its JSON")

    s = sub.add_parser("predict", help="slack / max flood / max ebb")
    dated(s)
    zoned(s)
    s.add_argument("--knots", action="store_true", help="also show knots")
    s.set_defaults(fn=cmd_predict)

    s = sub.add_parser("window", help="diveable slack windows")
    dated(s)
    zoned(s)
    _ms = _cfg("max_speed_ms", 0.25)
    s.add_argument("--max-speed", type=float, default=_ms, help=f"m/s, default {_ms}")
    s.set_defaults(fn=cmd_window)

    s = sub.add_parser("fetch", help="cache stations ahead of time")
    s.add_argument("station", nargs="*")
    s.add_argument("--near", nargs=2, type=float, metavar=("LAT", "LON"))
    s.add_argument("--km", type=float, default=50.0, help="radius for --near, default 50")
    s.add_argument("--all", action="store_true", help="every station NOAA lists")
    s.add_argument("--pause", type=float, default=0.3, help="seconds between stations, default 0.3")
    s.set_defaults(fn=cmd_fetch)

    s = sub.add_parser("verify", help="compare with NOAA's live API")
    s.add_argument("station", nargs="?")
    s.add_argument("--bin", type=int, help="the site file's Recommended bin")
    s.add_argument("--all", action="store_true", help="every published bin of every cached station")
    s.add_argument("--date", type=date.fromisoformat, default=date.today())
    s.add_argument("--days", type=int, default=30)
    s.add_argument("--speed-tol", type=float, default=0.02, help="m/s, default 0.02")
    s.add_argument("--time-tol", type=float, default=3.0, help="minutes, default 3")
    s.add_argument("--pause", type=float, default=0.2, help="seconds between bins with --all, default 0.2")
    s.set_defaults(fn=cmd_verify)

    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()

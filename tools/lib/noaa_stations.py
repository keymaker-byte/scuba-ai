"""NOAA's current stations as the current tool keeps them on this machine: NOAA's station list and
one file per station with every bin's harmonic constants, downloaded from NOAA's metadata API
when missing, and the check of a cached bin against NOAA's own live predictions."""
import json
import math
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, time, timedelta, timezone

from lib.current_harmonics import events, series, speed

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(TOOLS, "db", "noaa_current")
LIST = os.path.join(DB, "stations.json")
MD = "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations"
DG = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
UTC = timezone.utc
SPEED_TOL = 0.02    # m/s: a bin passes within this of NOAA's speed and peaks
TIME_TOL = 3.0      # minutes: and within this of every slack and maximum
FETCH_PAUSE = 0.3   # seconds after each station downloaded, under NOAA's rate limit (current_stations)


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


def entry(sid):
    lst = station_list()
    if sid not in lst["stations"]:
        sys.exit(f"{sid} is not in NOAA's current station list (fetched {lst['fetched']}). "
                 "Delete tools/db/noaa_current/stations.json to list again.")
    return lst["stations"][sid]


def station(sid, quiet=False):
    """One station's cached file: its metadata and every bin's constants, with each published
    harmonic bin's flood and ebb directions. Downloaded on first use."""
    path = os.path.join(DB, f"{sid}.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    e = entry(sid)
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
        if pb["type"] == "H":
            dirs = get(f"{MD}/{sid}_{num}/currentpredictionoffsets.json?units=metric", missing_ok=True) or {}
            b["flood_dir"], b["ebb_dir"] = dirs.get("meanFloodDir"), dirs.get("meanEbbDir")
    _save(path, doc)
    return doc


def harmonic_bins(doc):
    """The station's published harmonic bins with constants, the ones NOAA's API predicts and so
    the ones a check can compare."""
    return [(num, b) for num, b in sorted(doc["bins"].items(), key=lambda x: int(x[0]))
            if b.get("type") == "H" and b.get("cons")]


def _day_span(day, pad=0):
    start = datetime.combine(day, time(0), UTC)
    return start - timedelta(minutes=pad), 1440 + 2 * pad


def compare(doc, num, b, day0, days):
    """One harmonic bin against NOAA's live API over `days` from `day0`: the speed every six
    minutes, and every slack and maximum. Returns the differences."""
    speed_tol, time_tol = SPEED_TOL, TIME_TOL
    q = {"product": "currents_predictions", "application": "NOS.COOPS.TAC.CUR", "station": doc["id"],
         "bin": num, "time_zone": "gmt", "units": "metric", "format": "json",
         "begin_date": day0.strftime("%Y%m%d"), "end_date": (day0 + timedelta(days=days - 1)).strftime("%Y%m%d")}

    def api(interval):
        d = get(f"{DG}?{urllib.parse.urlencode({**q, 'interval': interval})}")
        cp = (d.get("current_predictions") or {}).get("cp")
        if not isinstance(cp, list) or not cp:
            return (d.get("error") or {}).get("message") or str(cp)
        return [(datetime.strptime(c["Time"], "%Y-%m-%d %H:%M").replace(tzinfo=UTC), c.get("Type"),
                 float(c["Velocity_Major"]) / 100.0) for c in cp]

    r = {"station": doc["id"], "bin": num, "type": "H", "ok": True}
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
    mine = []
    for k in range(days):
        start, minutes = _day_span(day0 + timedelta(days=k), pad=5)
        mine += events(series(b, start, minutes))
    dt_worst = dv_worst = 0.0
    missed = skipped = 0
    for t, kind, v in theirs:
        # NOAA's slack and maximum product keeps the old year's node factors for some hours
        # into a new UTC year, while its own speed series changes at the first hour.
        ny = datetime(t.year + (t.month == 12), 1, 1, tzinfo=UTC)
        if ny - timedelta(minutes=60) <= t < ny + timedelta(minutes=720):
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
        if kind == "slack" and dt > time_tol and abs(speed(b, t)) <= speed_tol:
            continue
        # A maximum on a flat top likewise: NOAA's minute holds the same speed as this one.
        if kind != "slack" and dt > time_tol and abs(speed(b, t) - m[2]) <= 0.005:
            dt = 0.0
        dt_worst = max(dt_worst, dt)
        if kind != "slack":
            dv_worst = max(dv_worst, abs(m[2] - v))
    r.update(events_n=len(theirs), time_worst=round(dt_worst, 1), peak_worst=round(dv_worst, 4),
             unmatched=missed, new_year_skipped=skipped)
    r["ok"] &= dt_worst <= time_tol and dv_worst <= speed_tol and missed == 0
    return r


def report_lines(r):
    if "error" in r:
        return [f"  NOAA: no predictions to compare with ({r['error']})"]
    note = f", {r['new_year_skipped']} in the first hours of a new year left out" if r["new_year_skipped"] else ""
    return [f"  speed, {r['speed_n']} six-minute values: worst difference {r['speed_worst']:.3f} m/s, "
            f"rms {r['speed_rms']:.3f} m/s",
            f"  events, {r['events_n']} slacks and maxima: worst time difference {r['time_worst']:.1f} min, "
            f"worst peak difference {r['peak_worst']:.3f} m/s, {r['unmatched']} unmatched{note}"]

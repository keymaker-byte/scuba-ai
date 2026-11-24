"""CHS's current stations as the current tool keeps them on this machine: CHS's station list, one
file per station (name, position, flood and ebb directions, time zone, and what CHS holds), and
one file per station and UTC year with that year's speed series and slack and maximum events,
each downloaded from CHS's IWLS API when missing; the signed series a station's constants are
fitted to; and the check of the cache against CHS's own live predictions.

CHS publishes finished predictions and keeps its harmonic constants to itself, so the cache holds
the predictions themselves. Speeds are in knots in the files, as CHS publishes them, and in m/s
everywhere they leave this module."""
import json
import math
import os
import sys
import time as _time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, time, timedelta, timezone

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(TOOLS, "db", "chs_current")
LIST = os.path.join(DB, "stations.json")
API = "https://api-iwls.dfo-mpo.gc.ca/api/v1"
KN = 0.514444  # m/s per knot
FMT = "%Y-%m-%dT%H:%M:%SZ"
UTC = timezone.utc
SPEED, EVENTS = "wcsp1", "wcp1-events"
CHUNK = timedelta(days=7)  # the longest span CHS answers for a speed series
KINDS = {"SLACK": "S", "EXTREMA_FLOOD": "F", "EXTREMA_EBB": "E", "WEAK_AND_VARIABLE": "W"}
PACE = 2.1  # seconds between requests: CHS allows 30 a minute from one address
FIT_STEP = 15  # minutes between the samples a station's constants are fitted to

_last = [0.0]


def get(path, **q):
    """Fetch CHS JSON at CHS's pace, or stop the run with what failed."""
    url = f"{API}/{path}" + (f"?{urllib.parse.urlencode(q)}" if q else "")
    last = None
    for attempt in range(3):
        wait = _last[0] + PACE - _time.monotonic()
        if wait > 0:
            _time.sleep(wait)
        _last[0] = _time.monotonic()
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code < 500 and e.code != 429:
                sys.exit(f"CHS: HTTP {e.code} for {url}. Nothing was cached.")
            last = f"HTTP {e.code}"
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last = f"unreachable ({getattr(e, 'reason', e)})"
        except ValueError:
            last = "an answer that is not JSON"
        _time.sleep(2 + 4 * attempt)
    sys.exit(f"CHS: {last} for {url}. Nothing was cached. Retry later.")


def _save(path, doc):
    os.makedirs(DB, exist_ok=True)
    tmp = path + ".part"
    with open(tmp, "w") as f:
        json.dump(doc, f, separators=(",", ":"))
    os.replace(tmp, path)


def _load(path):
    with open(path) as f:
        return json.load(f)


def _when(s):
    return datetime.strptime(s, FMT).replace(tzinfo=UTC)


# --- the cache: station list, one file per station, one per station and year ------------

def station_list():
    """CHS's current prediction stations: {code: {id, name, lat, lon}}. Downloaded once."""
    if os.path.exists(LIST):
        return _load(LIST)
    print("downloading CHS's current station list ...", file=sys.stderr, flush=True)
    rows = get("stations", **{"time-series-code": SPEED})
    if not isinstance(rows, list) or not rows:
        sys.exit("CHS: the station list came back empty. Nothing was cached. Retry later.")
    doc = {"fetched": date.today().isoformat(),
           "stations": {s["code"]: {"id": s["id"], "name": s["officialName"].strip(), "lat": s["latitude"],
                                    "lon": s["longitude"]} for s in rows}}
    _save(LIST, doc)
    return doc


def _holdings(sid, meta_series):
    """What CHS holds for a station's two series: {code: [[start, end], ...]} in UTC."""
    ids = {t["id"]: t["code"] for t in meta_series}
    out = {}
    for h in get(f"stations/{sid}/holdings"):
        code = ids.get(h.get("timeSeriesId"))
        if code in (SPEED, EVENTS):
            out[code] = [[x["dateStart"], x["dateEnd"]] for x in h.get("dataHoldings") or []]
    return out


def station(code, refresh=False):
    """One station's cached file: name, position, directions, zone, and what CHS holds for it.
    Downloaded on first use."""
    path = os.path.join(DB, f"{code}.json")
    if os.path.exists(path) and not refresh:
        return _load(path)
    st = station_list()
    e = st["stations"].get(code)
    if e is None:
        sys.exit(f"{code} is not in CHS's current station list (fetched {st['fetched']}). "
                 "Delete tools/db/chs_current/stations.json to list again.")
    meta = get(f"stations/{e['id']}/metadata")
    if not isinstance(meta, dict) or "timeSeries" not in meta:
        sys.exit(f"CHS: no metadata answer for {code}. Nothing was cached. Retry later.")
    doc = {"code": code, "id": e["id"], "fetched": date.today().isoformat(), "name": meta["officialName"].strip(),
           "lat": meta["latitude"], "lon": meta["longitude"], "flood": meta.get("floodDirection"),
           "ebb": meta.get("ebbDirection"), "tz": meta.get("timeZoneCode"),
           "holdings": _holdings(e["id"], meta["timeSeries"])}
    _save(path, doc)
    return doc


def _held(st, code, t0, t1):
    """The part of [t0, t1) CHS holds for a series, as a list of (start, end) spans."""
    out = []
    for a, b in st["holdings"].get(code, []):
        a, b = max(_when(a), t0), min(_when(b) + timedelta(minutes=1), t1)
        if a < b:
            out.append((a, b))
    return out


def _download_year(st, year, quiet=False):
    """One UTC year of a station's speed series and events, from CHS, as a year file's content;
    None for a year CHS holds no speeds for."""
    y0, y1 = datetime(year, 1, 1, tzinfo=UTC), datetime(year + 1, 1, 1, tzinfo=UTC)
    spans = _held(st, SPEED, y0, y1)
    if not spans:
        return None
    mins, kn = [], []
    tty = not quiet and sys.stderr.isatty()
    if not quiet and not tty:
        print(f"downloading CHS {st['code']} {st['name']} {year}, about two minutes ...", file=sys.stderr, flush=True)
    for a, b in spans:
        t = a
        while t < b:
            u = min(t + CHUNK, b)
            rows = get(f"stations/{st['id']}/data", **{"time-series-code": SPEED, "from": t.strftime(FMT),
                                                         "to": u.strftime(FMT)})
            if not isinstance(rows, list):
                sys.exit(f"CHS: no speed predictions answer for {st['code']} from {t:%Y-%m-%d}. Nothing was cached.")
            for r in rows:
                m = int((_when(r["eventDate"]) - y0).total_seconds() // 60)
                if not mins or m > mins[-1]:
                    mins.append(m)
                    kn.append(r["value"])
            if tty:
                print(f"\r  CHS {st['code']} {year}: speed through {u:%Y-%m-%d}", end="", file=sys.stderr, flush=True)
            t = u
    if tty:
        print(file=sys.stderr)
    if not mins:
        sys.exit(f"CHS: holdings list {st['code']} for {year} and the speed series came back empty. Nothing was cached.")
    events = []
    for a, b in _held(st, EVENTS, y0, y1):
        rows = get(f"stations/{st['id']}/data", **{"time-series-code": EVENTS, "from": a.strftime(FMT),
                                                     "to": (b - timedelta(minutes=1)).strftime(FMT)})
        if not isinstance(rows, list):
            sys.exit(f"CHS: no events answer for {st['code']} in {year}. Nothing was cached.")
        for r in rows:
            q = r.get("qualifier")
            if q not in KINDS:
                sys.exit(f"CHS: {st['code']} carries an event kind the current tool does not know ({q}). Report it.")
            events.append([int((_when(r["eventDate"]) - y0).total_seconds() // 60), KINDS[q], r["value"]])
    events.sort()
    step = mins[1] - mins[0] if len(mins) > 1 else 0
    regular = step > 0 and all(b - a == step for a, b in zip(mins, mins[1:]))
    doc = {"code": st["code"], "year": year, "fetched": date.today().isoformat(),
           "speed_spans": [[a.strftime(FMT), b.strftime(FMT)] for a, b in spans],
           "event_spans": [[a.strftime(FMT), b.strftime(FMT)] for a, b in _held(st, EVENTS, y0, y1)],
           "events": events, "kn": kn}
    doc.update({"start": mins[0], "step": step} if regular else {"mins": mins})
    return doc


def _recheck(st, when):
    """The station's file fetched again, for holdings CHS may have added since it was cached."""
    try:
        return station(st["code"], refresh=True)
    except SystemExit as e:
        sys.exit(f"The cache holds nothing for CHS {st['code']} {st['name']} on {when}, and asking CHS whether it "
                 f"now holds more failed. {e}")


def year_file(st, year, quiet=False):
    """A station's cached year, downloaded on first use; None for a year CHS does not hold. A year
    CHS did not hold when the station was cached is asked for again, once."""
    path = os.path.join(DB, f"{st['code']}_{year}.json")
    if os.path.exists(path):
        return _load(path)
    doc = _download_year(st, year, quiet)
    if doc is None:
        st.update(_recheck(st, f"{year}"))
        doc = _download_year(st, year, quiet)
    if doc is not None:
        _save(path, doc)
    return doc


def _covers(spans, t0, t1):
    return any(_when(a) <= t0 and t1 <= _when(b) for a, b in spans)


def _need(st, t0, t1, what):
    """The year files covering [t0, t1), each checked to hold `what` for its part of the span. A
    year cached while CHS held less of it is fetched again once CHS holds more."""
    series = SPEED if what == "speed_spans" else EVENTS
    out = []
    for year in range(t0.year, (t1 - timedelta(minutes=1)).year + 1):
        y0, y1 = datetime(year, 1, 1, tzinfo=UTC), datetime(year + 1, 1, 1, tzinfo=UTC)
        a, b = max(t0, y0), min(t1, y1)
        doc = year_file(st, year)
        if doc is not None and not _covers(doc[what], a, b):
            fresh = _recheck(st, f"{a:%Y-%m-%d} UTC")
            if fresh["holdings"] != st["holdings"]:
                st.update(fresh)
                new = _download_year(st, year)
                if new is not None:
                    _save(os.path.join(DB, f"{st['code']}_{year}.json"), new)
                    doc = new
        if doc is None or not _covers(doc[what], a, b):
            kind = "speed predictions" if what == "speed_spans" else "slack and maximum events"
            held = "; ".join(f"{x[:10]} to {y[:10]}" for x, y in st["holdings"].get(series, [])) or "none"
            sys.exit(f"CHS holds no {kind} for {st['code']} {st['name']} on {a:%Y-%m-%d} UTC. It holds: {held} "
                     f"(as of {st['fetched']}). CHS adds a year at a time. Stop and report it.")
        out.append((y0, doc))
    return out


def _minutes(doc):
    return doc["mins"] if "mins" in doc else range(doc["start"], doc["start"] + doc["step"] * len(doc["kn"]), doc["step"])


def speeds(st, t0, t1):
    """[(UTC datetime, m/s)] of CHS's speed series in [t0, t1), unsigned as CHS publishes it."""
    out = []
    for y0, doc in _need(st, t0, t1, "speed_spans"):
        lo, hi = (t0 - y0).total_seconds() / 60, (t1 - y0).total_seconds() / 60
        out += [(y0 + timedelta(minutes=m), v * KN) for m, v in zip(_minutes(doc), doc["kn"]) if lo <= m < hi]
    return out


def events(st, t0, t1):
    """[(UTC datetime, kind, m/s)] of CHS's slack and maximum events in [t0, t1); kind is S, F, E
    or W (weak and variable)."""
    out = []
    for y0, doc in _need(st, t0, t1, "event_spans"):
        lo, hi = (t0 - y0).total_seconds() / 60, (t1 - y0).total_seconds() / 60
        out += [(y0 + timedelta(minutes=m), k, v * KN) for m, k, v in doc["events"] if lo <= m < hi]
    return out


def signed_events(st, t0, t1):
    """CHS's events in [t0, t1) in the form the current tool scores predictions with:
    [(UTC datetime, "slack" | "flood" | "ebb", m/s flood positive)]; weak and variable left out."""
    name = {"S": "slack", "F": "flood", "E": "ebb"}
    return [(t, name[k], 0.0 if k == "S" else v if k == "F" else -v) for t, k, v in events(st, t0, t1) if k in name]


def signed(code, year, step=FIT_STEP):
    """A station's speed series for one UTC year, every `step` minutes, signed flood positive by
    the flood or ebb between the slacks around each sample; a sample whose turn holds no single
    flood or ebb (weak and variable, or a flood and an ebb with no slack between) is left out. The
    year is downloaded on first use."""
    st = station(code)
    d = year_file(st, year)
    if d is None or not d["events"]:
        sys.exit(f"CHS holds no {year} predictions with events for station {code}, so its constants cannot be "
                 "fitted to that year. Stop and report it.")
    t0 = datetime(year, 1, 1, tzinfo=UTC)
    ev = [(m, k) for m, k, _ in d["events"]]
    out, j = [], 0
    for m, kn in zip(_minutes(d), d["kn"]):
        if m % step:
            continue
        while j < len(ev) and ev[j][0] <= m:
            j += 1
        lo = j - 1
        while lo >= 0 and ev[lo][1] != "S":
            lo -= 1
        hi = j
        while hi < len(ev) and ev[hi][1] != "S":
            hi += 1
        if lo < 0 or hi >= len(ev):
            continue
        kinds = {k for _, k in ev[lo:hi + 1] if k != "S"}
        if kinds in ({"F"}, {"E"}):
            out.append((t0 + timedelta(minutes=m), (1 if kinds == {"F"} else -1) * kn * KN))
    return out


# --- the check against CHS's live API ---------------------------------------------------------

def _live(st, code, t0, t1):
    out, t = [], t0
    span = CHUNK if code == SPEED else timedelta(days=300)
    while t < t1:
        u = min(t + span, t1)
        rows = get(f"stations/{st['id']}/data", **{"time-series-code": code, "from": t.strftime(FMT),
                                                     "to": (u - timedelta(minutes=1)).strftime(FMT)})
        if not isinstance(rows, list):
            sys.exit(f"CHS: no answer to compare with for {st['code']}.")
        out += [(_when(r["eventDate"]), KINDS.get(r.get("qualifier")), r["value"] * KN) for r in rows]
        t = u
    return out


def compare(st, day0, days):
    """The cache against CHS's live API over `days` from `day0` UTC: every speed value and every
    event, passing only when all are identical."""
    t0 = datetime.combine(day0, time(0), UTC)
    t1 = t0 + timedelta(days=days)
    mine = dict(speeds(st, t0, t1))
    theirs = _live(st, SPEED, t0, t1)
    worst = max((abs(mine.get(t, math.inf) - v) for t, _, v in theirs), default=math.inf)
    r = {"station": st["code"], "speed_n": len(theirs), "speed_missing": abs(len(mine) - len(theirs)),
         "speed_worst": None if math.isinf(worst) else round(worst, 4)}
    me = {(t, k): v for t, k, v in events(st, t0, t1)}
    te = _live(st, EVENTS, t0, t1)
    diff = sum(1 for t, k, v in te if abs(me.get((t, k), math.inf) - v) > 1e-6) + abs(len(me) - len(te))
    r.update(events_n=len(te), events_differ=diff)
    r["ok"] = bool(theirs) and r["speed_missing"] == 0 and worst <= 1e-6 and diff == 0
    return r

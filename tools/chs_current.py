#!/usr/bin/env python3
"""Canadian Hydrographic Service current predictions: slack, max flood/ebb, and diveable windows,
read from CHS's own predictions kept on this machine.

  chs_current.py stations --near LAT LON                        CHS current stations near a site
  chs_current.py predict STATION [--date D]                     slack / max flood / max ebb
  chs_current.py window STATION [--date D]                      diveable windows under a speed threshold
  chs_current.py fetch [STATION ...] [--near LAT LON --km R] [--all] [--year Y ...]   cache ahead of time
  chs_current.py verify STATION [--date D] [--days N]           compare the cache with CHS's live API
  chs_current.py verify --all [--date D] [--days N]             the same for every cached station

STATION is the CHS five-digit station code, e.g. 07100.

CHS publishes finished predictions, with no harmonic constants to compute from, and only for
the years it holds. The data lives in tools/db/chs_current/: the station list, one file per
station, and one file per station and year holding that year's speed series and its slack and
maximum events. Each is downloaded the first time it is needed. Delete a file, or the folder,
to fetch CHS's current values again.
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

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "tools", "db", "chs_current")
LIST = os.path.join(DB, "stations.json")
API = "https://api-iwls.dfo-mpo.gc.ca/api/v1"
KN = 0.514444  # m/s per knot; CHS publishes current speed in knots
FMT = "%Y-%m-%dT%H:%M:%SZ"
UTC = timezone.utc
SPEED, EVENTS = "wcsp1", "wcp1-events"
CHUNK = timedelta(days=7)  # the longest span CHS answers for a speed series
KINDS = {"SLACK": "S", "EXTREMA_FLOOD": "F", "EXTREMA_EBB": "E", "WEAK_AND_VARIABLE": "W"}


def _cfg(key, default):
    """Read this tool's section of tool-config.json; missing file or key -> default."""
    try:
        with open(os.path.join(ROOT, "tool-config.json")) as f:
            return json.load(f).get("chs_current", {}).get(key, default)
    except (OSError, ValueError):
        return default


# --- CHS's API and the cache ---------------------------------------------------------------
PACE = 2.1  # seconds between requests: CHS allows 30 a minute from one address
_last = [0.0]


def get(path, **q):
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
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(doc, f, separators=(",", ":"))
    os.replace(tmp, path)


def _load(path):
    with open(path) as f:
        return json.load(f)


def _when(s):
    return datetime.strptime(s, FMT).replace(tzinfo=UTC)


def station_list():
    """CHS's current prediction stations: {code: {id, name, lat, lon}}. Downloaded once."""
    if os.path.exists(LIST):
        return _load(LIST)
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
    """One station's cached file: name, position, directions, zone, and what CHS holds for it."""
    path = os.path.join(DB, f"{code}.json")
    if os.path.exists(path) and not refresh:
        return _load(path)
    st = station_list()
    e = st["stations"].get(code)
    if e is None:
        sys.exit(f"{code} is not in CHS's current station list (fetched {st['fetched']}). List stations with "
                 "`stations --near`. Delete tools/db/chs_current/stations.json to list again.")
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
    """One UTC year of a station's speed series and events, from CHS, as a year file's content."""
    y0, y1 = datetime(year, 1, 1, tzinfo=UTC), datetime(year + 1, 1, 1, tzinfo=UTC)
    spans = _held(st, SPEED, y0, y1)
    if not spans:
        return None
    mins, kn = [], []
    tty = not quiet and sys.stderr.isatty()
    if not quiet and not tty:
        print(f"downloading {st['code']} {st['name']} {year} from CHS, about two minutes ...", file=sys.stderr, flush=True)
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
                print(f"\r  {st['code']} {year}: speed through {u:%Y-%m-%d}", end="", file=sys.stderr, flush=True)
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
                sys.exit(f"CHS: {st['code']} carries an event kind this tool does not know ({q}). Report it.")
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
        sys.exit(f"The cache holds nothing for {st['code']} {st['name']} on {when}, and asking CHS whether it "
                 f"now holds more failed. {e}")


def year_file(st, year, quiet=False):
    """A station's cached year, downloaded on first use; None for a year CHS does not hold. A
    year cached while CHS held only part of it is fetched again once CHS holds more."""
    path = os.path.join(DB, f"{st['code']}_{year}.json")
    if os.path.exists(path):
        return _load(path)
    doc = _download_year(st, year, quiet)
    if doc is None:
        fresh = _recheck(st, f"{year}")  # the holdings may have grown since the station was cached
        st.update(fresh)
        doc = _download_year(st, year, quiet)
    if doc is not None:
        _save(path, doc)
    return doc


def _covers(spans, t0, t1):
    return any(_when(a) <= t0 and t1 <= _when(b) for a, b in spans)


def _need(st, t0, t1, what):
    """The year files covering [t0, t1), each checked to hold `what` for its part of the span."""
    out = []
    for year in range(t0.year, (t1 - timedelta(minutes=1)).year + 1):
        y0, y1 = datetime(year, 1, 1, tzinfo=UTC), datetime(year + 1, 1, 1, tzinfo=UTC)
        a, b = max(t0, y0), min(t1, y1)
        doc = year_file(st, year)
        if doc is not None and not _covers(doc[what], a, b):
            # cached while CHS held less of the year: look again, once
            fresh = _recheck(st, f"{a:%Y-%m-%d} UTC")
            if _held(fresh, SPEED if what == "speed_spans" else EVENTS, a, b) != _held(st, SPEED if what == "speed_spans" else EVENTS, a, b) \
                    or fresh["holdings"] != st["holdings"]:
                st.update(fresh)
                new = _download_year(st, year)
                if new is not None:
                    _save(os.path.join(DB, f"{st['code']}_{year}.json"), new)
                    doc = new
        if doc is None or not _covers(doc[what], a, b):
            kind = "speed predictions" if what == "speed_spans" else "slack and maximum events"
            held = "; ".join(f"{x[:10]} to {y[:10]}" for x, y in st["holdings"].get(SPEED if what == "speed_spans" else EVENTS, [])) or "none"
            sys.exit(f"CHS holds no {kind} for {st['code']} {st['name']} on {a:%Y-%m-%d} UTC. It holds: {held} "
                     f"(as of {st['fetched']}). CHS adds a year at a time; there is nothing to predict from past that.")
        out.append((y0, doc))
    return out


def speeds(st, t0, t1):
    """[(UTC datetime, m/s)] of the speed series in [t0, t1)."""
    out = []
    for y0, doc in _need(st, t0, t1, "speed_spans"):
        kn = doc["kn"]
        if "mins" in doc:
            ms = doc["mins"]
        else:
            ms = range(doc["start"], doc["start"] + doc["step"] * len(kn), doc["step"])
        lo, hi = (t0 - y0).total_seconds() / 60, (t1 - y0).total_seconds() / 60
        out += [(y0 + timedelta(minutes=m), v * KN) for m, v in zip(ms, kn) if lo <= m < hi]
    return out


def events(st, t0, t1):
    """[(UTC datetime, kind, m/s)] of the slack and maximum events in [t0, t1); kind is S, F, E or W."""
    out = []
    for y0, doc in _need(st, t0, t1, "event_spans"):
        lo, hi = (t0 - y0).total_seconds() / 60, (t1 - y0).total_seconds() / 60
        out += [(y0 + timedelta(minutes=m), k, v * KN) for m, k, v in doc["events"] if lo <= m < hi]
    return out


# --- commands ------------------------------------------------------------------------------
def zone(name):
    """The zone every time prints in: the site's own, passed as --tz."""
    try:
        return ZoneInfo(name)
    except Exception:
        sys.exit(f"{name} is not an IANA time zone name. Pass the site's `tz` from its JSON, e.g. America/Los_Angeles.")


def local_day(day, tz):
    start = datetime.combine(day, time(0), tz).astimezone(UTC)
    end = datetime.combine(day + timedelta(days=1), time(0), tz).astimezone(UTC)
    return start, end


def header(st, day, tz, fetched):
    def deg(v):
        return "?" if v is None else f"{v:g}"
    print(f"{st['code']}  {st['name']}  {day}  ({tz.key})")
    print(f"  {st['lat']:.4f}, {st['lon']:.4f}   flood {deg(st.get('flood'))}°   ebb {deg(st.get('ebb'))}°")
    print(f"  CHS's own predictions as downloaded {fetched}\n")


def _fetched(st, t0, t1):
    return min(year_file(st, y)["fetched"] for y in range(t0.year, (t1 - timedelta(minutes=1)).year + 1))


def _km(lat, lon, s):
    return math.hypot((s["lat"] - lat) * 60.0, (s["lon"] - lon) * 60.0 * math.cos(math.radians(lat))) * 1.852


def cmd_stations(a):
    lat, lon = a.near
    st = station_list()
    rows = sorted((_km(lat, lon, s), code, s) for code, s in st["stations"].items())
    print(f"CHS current-prediction stations near {lat:.4f}, {lon:.4f} (CHS's list as fetched {st['fetched']}):\n")
    for km, code, s in rows[: a.n]:
        print(f"  {code:<7} {km:6.1f} km  {s['name']}")
    print("\nNearest is not automatically the governing station — pick the one whose water is")
    print("hydraulically connected to the site, then verify the offset in the water.")


def cmd_predict(a):
    st = station(a.station)
    tz = zone(a.tz)
    t0, t1 = local_day(a.date, tz)
    ev = events(st, t0, t1)
    header(st, a.date, tz, _fetched(st, t0, t1))
    if not ev:
        print("  no slack or maximum on this day.")
    for t, kind, v in ev:
        lt = t.astimezone(tz)
        if kind == "S":
            print(f"  {lt:%H:%M}  SLACK")
        elif kind == "W":
            print(f"  {lt:%H:%M}  weak and variable")
        else:
            print(f"  {lt:%H:%M}  {'flood' if kind == 'F' else 'ebb':<5} {v if kind == 'F' else -v:+.2f} m/s")


def cmd_window(a):
    st = station(a.station)
    tz = zone(a.tz)
    t0, t1 = local_day(a.date, tz)
    pts = [(t.astimezone(tz), v) for t, v in speeds(st, t0, t1)]
    lim = a.max_speed
    header(st, a.date, tz, _fetched(st, t0, t1))
    print(f"  windows with current <= {lim:.2f} m/s\n")

    def cross(p, q):
        """Time the speed crosses the limit between two samples, by linear interpolation."""
        (ta, va), (tb, vb) = p, q
        f = (lim - va) / (vb - va) if vb != va else 0.0
        return ta + (tb - ta) * f

    runs, start, peak = [], None, 0.0
    for i, (t, v) in enumerate(pts):
        if v <= lim:
            if start is None:
                start = pts[0][0] if i == 0 else cross(pts[i - 1], pts[i])
                peak = 0.0
            peak = max(peak, v)
        elif start is not None:
            runs.append((start, cross(pts[i - 1], pts[i]), peak))
            start = None
    if start is not None:
        runs.append((start, pts[-1][0], peak))

    if not runs:
        print(f"  none — current never drops below {lim:.2f} m/s. Not a dive day here.")
        return
    for ta, tb, pk in runs:
        mins = int((tb - ta).total_seconds() // 60)
        flag = "  <-- tight" if mins < 40 else ""
        print(f"  {ta:%H:%M} - {tb:%H:%M}   {mins:>3} min   peak {pk:.2f} m/s{flag}")
    print("\n  Times are AT THE STATION. Apply the site offset, and pad it until observed.")


def cmd_fetch(a):
    st = station_list()["stations"]
    if a.all:
        want = sorted(st)
    elif a.near:
        want = [code for code, s in sorted(st.items()) if _km(a.near[0], a.near[1], s) <= a.km]
    elif a.station:
        want = a.station
    else:
        sys.exit("name stations, or pass --near LAT LON [--km R], or --all.")
    n = 0
    for code in want:
        doc = station(code)
        held = [_when(x) for span in doc["holdings"].get(SPEED, []) for x in span]
        years = a.year or (sorted({y for y in range(min(held).year, max(held).year + 1)}) if held else [])
        for year in years:
            if os.path.exists(os.path.join(DB, f"{code}_{year}.json")):
                continue
            got = year_file(doc, year)
            n += got is not None
            print(f"  {code}  {doc['name']}  {year}: " + ("cached" if got else "CHS holds nothing"), flush=True)
            _time.sleep(a.pause)
    print(f"done; {n} station years downloaded.")


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
    """The cache against CHS's live API over `days` from `day0` UTC: every speed value and every event."""
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


def cmd_verify(a):
    """Compare the cache with CHS's own predictions, read live from its API."""
    if a.all:
        codes = sorted(f[:-5] for f in os.listdir(DB) if f.endswith(".json") and "_" not in f and f != "stations.json")
    elif a.station:
        codes = [a.station]
    else:
        sys.exit("name a station, or pass --all.")
    bad = 0
    for code in codes:
        st = station(code)
        r = compare(st, a.date, a.days)
        bad += not r["ok"]
        print(f"{code}  {st['name']}  {a.date} for {a.days} days, against CHS's API")
        print(f"  speed, {r['speed_n']} values: " + ("worst difference n/a" if r["speed_worst"] is None else
              f"worst difference {r['speed_worst']:.3f} m/s") + f", {r['speed_missing']} missing")
        print(f"  events, {r['events_n']} slacks and maxima: {r['events_differ']} differ")
        print("  PASS\n" if r["ok"] else "  FAIL: CHS has replaced these predictions since they were cached. Delete the "
              "station's files to fetch them again.\n", flush=True)
        _time.sleep(a.pause)
    sys.exit(1 if bad else 0)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("stations", help="find CHS current stations near a site")
    s.add_argument("--near", nargs=2, type=float, metavar=("LAT", "LON"), required=True)
    s.add_argument("-n", type=int, default=6)
    s.set_defaults(fn=cmd_stations)

    def dated(sp):
        sp.add_argument("station", help="CHS five-digit station code, e.g. 07100")
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

    s = sub.add_parser("fetch", help="cache stations ahead of time")
    s.add_argument("station", nargs="*")
    s.add_argument("--near", nargs=2, type=float, metavar=("LAT", "LON"))
    s.add_argument("--km", type=float, default=50.0, help="radius for --near, default 50")
    s.add_argument("--all", action="store_true", help="every station CHS lists")
    s.add_argument("--year", type=int, action="append", help="a UTC year to cache; repeatable; default every year CHS holds")
    s.add_argument("--pause", type=float, default=0.2, help="seconds between station years, default 0.2")
    s.set_defaults(fn=cmd_fetch)

    s = sub.add_parser("verify", help="compare the cache with CHS's live API")
    s.add_argument("station", nargs="?")
    s.add_argument("--all", action="store_true", help="every cached station")
    s.add_argument("--date", type=date.fromisoformat, default=date.today())
    s.add_argument("--days", type=int, default=7)
    s.add_argument("--pause", type=float, default=0.2, help="seconds between stations with --all, default 0.2")
    s.set_defaults(fn=cmd_verify)

    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()

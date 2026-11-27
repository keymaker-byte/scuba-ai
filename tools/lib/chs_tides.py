"""CHS water level prediction stations as the tide tool keeps them on this machine: CHS's station
list, one file per station (name, position, CHS's characteristic heights, what CHS holds), and one
file per station with harmonic constants fitted to CHS's own predictions; the height and the highs
and lows at any moment from those constants; and the check against CHS's live predictions.

CHS publishes finished predictions and keeps its harmonic constants to itself, so the tool fits its
own by Foreman's method (`lib/foreman.py`), the method CHS predicts with: to the newest two complete
years CHS holds, with the shallow water compounds the station's own series calls for, and tested on
the predictions CHS holds after them (or, with too few of those, on the complete year before). The
predictions are downloaded into memory for the fit and its test and kept nowhere. Where the
constants keep to the tool's limits on both, they reproduce CHS's predictions to the millimetre and
answer every date; where they do not, the station stops the run with the fit's figures, as a NOAA
station with nothing to predict from does. Heights are metres above CHS Chart Datum.

`lib/tide.py` reads it as the CHS source. Requests go through `lib/chs_stations.get`, the current
tool's CHS client, so both tools share CHS's pace of 30 requests a minute."""
import json
import math
import os
import re
import sys
from datetime import date, datetime, timedelta, timezone

from lib import chs_stations, foreman
from lib.tide_harmonics import extremes as find_extremes

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(TOOLS, "db", "tide", "chs")
LIST = os.path.join(DB, "stations.json")
SERIES, HILO = "wlp", "wlp-hilo"
STEP = timedelta(minutes=15)  # between the heights read from CHS: its FIFTEEN_MINUTES resolution
CHUNK = timedelta(days=31)  # the longest span CHS answers at that resolution
FMT = "%Y-%m-%dT%H:%M:%SZ"
UTC = timezone.utc
CODE = re.compile(r"\d{5}")  # a CHS station code; NOAA's IDs never take this shape
FIT_YEARS = 2  # years of predictions a fit takes: what Foreman's 68 constituents need to be resolved
TEST_MIN = timedelta(days=90)  # the least of CHS's predictions after the fit years a test reads
FIT_EVERY = timedelta(hours=2)  # between the samples a fit reads
PROBE_EVERY = timedelta(hours=1)  # between the samples its leftover is read from
PASS_HEIGHT, PASS_MIN = 0.02, 3.0  # the limits a fit must keep to answer for CHS
PASS_RMS = 0.002  # and its rms: CHS's own series is reproduced to 0.3 mm where it is a sum of tides
FLAT = 0.003  # m: a high or low whose fitted height at CHS's moment is this close is on a flat stand
LISTING_OFF = 0.01  # m: CHS's listed high or low this far from its own series at the moment is CHS's listing at odds
PAD = timedelta(days=1)  # read either side of a span of highs and lows, to tell each one's neighbours
SIDE = timedelta(hours=1)  # either side of a listed high or low, where CHS's own heights tell which it is


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


def _iso(t):
    return t.strftime(FMT)


def is_code(sid):
    return bool(CODE.fullmatch(sid))


# --- on this machine: the station list and one file per station ----------------------------

def station_list():
    """Every CHS station with water level predictions, keyed by code: id, name, lat, lon,
    region; and CHS's height types by id. Downloaded once."""
    if os.path.exists(LIST):
        return _load(LIST)
    print("downloading CHS's water level station list ...", file=sys.stderr, flush=True)
    rows = chs_stations.get("stations", **{"time-series-code": SERIES})
    if not isinstance(rows, list) or not rows:
        sys.exit("CHS: the water level station list came back empty. Nothing was cached. Retry later.")
    types = chs_stations.get("height-types")
    if not isinstance(types, list) or not types:
        sys.exit("CHS: the height type list came back empty. Nothing was cached. Retry later.")
    doc = {"fetched": date.today().isoformat(),
           "height_types": {h["id"]: h["code"] for h in types},
           "stations": {s["code"]: {"id": s["id"], "name": s["officialName"].strip(), "lat": s["latitude"],
                                    "lon": s["longitude"], "region": s.get("chsRegionCode")} for s in rows}}
    _save(LIST, doc)
    return doc


def station(code, quiet=False):
    """One station's file: name, position, CHS's heights above Chart Datum, its reference port,
    and the span CHS holds predictions for. Downloaded on first use."""
    path = os.path.join(DB, f"{code}.json")
    if os.path.exists(path):
        return _load(path)
    lst = station_list()
    e = lst["stations"].get(code)
    if e is None:
        sys.exit(f"{code} is not in CHS's water level station list (fetched {lst['fetched']}). List stations with "
                 "`stations --near`. Delete tools/db/tide/chs/stations.json to list again.")
    if not quiet:
        print(f"downloading CHS {code} {e['name']} ...", file=sys.stderr, flush=True)
    meta = chs_stations.get(f"stations/{e['id']}/metadata")
    if not isinstance(meta, dict) or "timeSeries" not in meta:
        sys.exit(f"CHS: no metadata answer for {code}. Nothing was cached. Retry later.")
    ids = {t["id"]: t["code"] for t in meta["timeSeries"]}
    held = {}
    for h in chs_stations.get(f"stations/{e['id']}/holdings"):
        series = ids.get(h.get("timeSeriesId"))
        if series in (SERIES, HILO):
            held[series] = [[x["dateStart"], x["dateEnd"]] for x in h.get("dataHoldings") or []]
    ref = meta.get("referencePortStationId")
    by_id = {s["id"]: c for c, s in lst["stations"].items()}
    doc = {"id": code, "chs_id": e["id"], "fetched": date.today().isoformat(), "name": meta["officialName"].strip(),
           "lat": meta["latitude"], "lon": meta["longitude"], "tz": meta.get("timeZoneCode"),
           "tidal": meta.get("isTidal"), "reference_port": bool(meta.get("isTideTableReferencePort")),
           "ref": by_id.get(ref) if ref else None,
           "heights": {lst["height_types"].get(h["heightTypeId"], h["heightTypeId"]): h["value"]
                       for h in meta.get("heights") or []},
           "holdings": held}
    _save(path, doc)
    return doc


def unusable(doc):
    """Why a station has nothing to fit constants to, or None when it has."""
    if doc.get("tidal") is False:
        return "CHS lists it as non-tidal: its levels are a water level above a chart datum, not a tide"
    if not doc["holdings"].get(SERIES) or not doc["holdings"].get(HILO):
        return "CHS holds no predicted heights, or no highs and lows, for it"
    return None


def held(doc):
    """The span CHS holds both predicted heights and highs and lows for: (start, end) in UTC."""
    a = max(min(_when(s) for s, _ in doc["holdings"][k]) for k in (SERIES, HILO))
    b = min(max(_when(e) for _, e in doc["holdings"][k]) for k in (SERIES, HILO))
    return a, b + timedelta(minutes=1)


def _held_text(doc):
    a, b = held(doc)
    return f"{a:%Y-%m-%d} to {b - timedelta(minutes=1):%Y-%m-%d} UTC"


def _inside(doc, t0, t1):
    a, b = held(doc)
    return a <= t0 and t1 <= b


class SeriesGap(SystemExit):
    """CHS's predicted series for a station has a hole inside the span CHS says it holds, so no fit
    can be made from it: the run stops with the message, as sys.exit does, and a caller that can go
    on without the station (the map's tide layer) catches it and names the station."""


# --- CHS's predictions, read into memory ---------------------------------------------------

def _span(doc, kind, t0, t1, resolution=None):
    """CHS's values for one series from t0 to t1 (end excluded), in chunks CHS answers:
    [(utc datetime, metres)]."""
    out = []
    t = t0
    chunk = CHUNK if kind == HILO or resolution else timedelta(days=7)
    while t < t1:
        u = min(t + chunk, t1)
        q = {"time-series-code": kind, "from": _iso(t), "to": _iso(u - timedelta(minutes=1))}
        if resolution:
            q["resolution"] = resolution
        rows = chs_stations.get(f"stations/{doc['chs_id']}/data", **q)
        if not isinstance(rows, list):
            sys.exit(f"CHS: {doc['id']} answered {kind} for {q['from']} with something other than a list. "
                     "Nothing was cached. Retry later.")
        out += [(_when(r["eventDate"]), r["value"]) for r in rows if r.get("value") is not None]
        t = u
    return out


def _grid(doc, t0, t1, what):
    """CHS's heights every 15 minutes from t0 to t1, as a list from t0; a gap stops the run."""
    n = int((t1 - t0) / STEP)
    h = [None] * n
    for t, v in _span(doc, SERIES, t0, t1, "FIFTEEN_MINUTES"):
        k, r = divmod(t - t0, STEP)
        if not r and 0 <= k < n:
            h[k] = v
    if None in h:
        miss = t0 + STEP * h.index(None)
        raise SeriesGap(f"CHS: {doc['id']}'s predicted heights for {what} have a gap at {miss:%Y-%m-%d %H:%M} UTC, inside the "
                 f"span CHS says it holds. Nothing was cached. Retry later, and report it if it persists.")
    return h


def _events(doc, t0, t1, series_at):
    """CHS's highs and lows from t0 to t1, [(utc, "H" or "L", metres)]. Each is a high when it
    stands above CHS's own predicted heights an hour either side of it (`series_at`), so a gap in
    CHS's listing leaves every event it does list read correctly; where the series has no value
    there, a high when it stands above the listed extremes either side of it, read a day past each
    end to find them."""
    a, b = held(doc)
    ev = sorted(_span(doc, HILO, max(a, t0 - PAD), min(b, t1 + PAD)))
    out = []
    for i, (t, v) in enumerate(ev):
        if t0 <= t < t1:
            nb = [series_at(t + d) for d in (-SIDE, SIDE)]
            if None in nb:
                nb = [ev[j][1] for j in (i - 1, i + 1) if 0 <= j < len(ev)]
                high = all(v > w for w in nb)
            else:
                high = v > sum(nb) / 2
            out.append((t, "H" if high else "L", v))
    return out


def _between(at, t):
    """A height between CHS's 15-minute values: a cubic through the four around t, where `at`
    gives the value at a moment on the grid, or None where it has none."""
    epoch = datetime(t.year, 1, 1, tzinfo=UTC)
    k, r = divmod(t - epoch, STEP)
    g = epoch + STEP * k
    p0, p1, p2, p3 = (at(g + STEP * i) for i in (-1, 0, 1, 2))
    if p1 is None or (r and p2 is None):
        return None
    if not r:
        return p1
    x = r / STEP
    if p0 is None or p3 is None:
        return p1 + (p2 - p1) * x
    return (p0 * -x * (x - 1) * (x - 2) / 6 + p1 * (x + 1) * (x - 1) * (x - 2) / 2
            - p2 * (x + 1) * x * (x - 2) / 2 + p3 * (x + 1) * x * (x - 1) / 6)


class _Period:
    """CHS's predictions over a span, in memory: the 15-minute heights and the highs and lows."""

    def __init__(self, doc, t0, t1, what):
        print(f"downloading CHS {doc['id']} {doc['name']}'s predictions, {what} ...", file=sys.stderr, flush=True)
        self.t0, self.t1 = t0, t1
        self.h = _grid(doc, t0, t1, what)
        self.events = _events(doc, t0, t1, lambda t: _between(self.at, t))
        if not self.events:
            sys.exit(f"CHS: no highs and lows for {doc['id']} in {what}. Nothing was cached. Retry later.")

    def at(self, t):
        k, r = divmod(t - self.t0, STEP)
        return self.h[k] if not r and 0 <= k < len(self.h) else None

    def samples(self, every):
        return [(self.t0 + STEP * k, self.h[k]) for k in range(0, len(self.h), every // STEP)]


# --- the fit -------------------------------------------------------------------------------

def _plan(doc):
    """What a fit reads: the newest FIT_YEARS complete UTC years CHS holds, and the span it is
    tested on, CHS's predictions after them where they run TEST_MIN or more, else the complete
    year before them. ([fit years], (test start, test end))."""
    a, b = held(doc)
    full = [y for y in range(a.year, b.year + 1)
            if a <= datetime(y, 1, 1, tzinfo=UTC) and datetime(y + 1, 1, 1, tzinfo=UTC) <= b]
    years = full[-FIT_YEARS:]
    after = datetime(years[-1] + 1, 1, 1, tzinfo=UTC) if years else b
    if len(years) == FIT_YEARS and b - after >= TEST_MIN:
        return years, (after, b)
    if len(full) > FIT_YEARS:
        y = full[-FIT_YEARS - 1]
        return years, (datetime(y, 1, 1, tzinfo=UTC), datetime(y + 1, 1, 1, tzinfo=UTC))
    sys.exit(f"{doc['id']} {doc['name']}: CHS holds too few predictions for it ({_held_text(doc)}) for a fit of "
             f"Foreman's constituents and its test: {FIT_YEARS} complete years, and {TEST_MIN.days} days after them "
             "or a complete year before.")


def _span_text(s):
    a, b = (_when(x) if isinstance(x, str) else x for x in s)
    return f"{a:%Y-%m-%d} to {b - timedelta(minutes=1):%Y-%m-%d}"


def _match_events(h, theirs, series_at, t0, t1):
    """The fit's highs and lows against CHS's [(utc, "H" or "L", metres)] between t0 and t1. A high
    or low on a flat stand moves minutes for a hair of height, so one whose fitted height at CHS's
    moment is within FLAT of the fit's own extreme is judged on the height; one CHS lists more than
    LISTING_OFF from its own series at that moment (`series_at`) is CHS's listing at odds with its
    series, left out and counted."""
    mine = find_extremes(lambda t: foreman.height(h, t), t0 - timedelta(hours=3), t1 + timedelta(hours=3))
    dt_worst = dv_worst = 0.0
    missed = flat = off = 0
    for t, kind, v in theirs:
        s = series_at(t)
        if s is not None and abs(s - v) > LISTING_OFF:
            off += 1
            continue
        same = [m for m in mine if m[1] == kind]
        m = min(same, key=lambda m: abs(m[0] - t)) if same else None
        if m is None or abs(m[0] - t) > timedelta(minutes=90):
            missed += 1
            continue
        dt = abs((m[0] - t).total_seconds()) / 60
        if dt > PASS_MIN and abs(foreman.height(h, t) - m[2]) <= FLAT:
            dt, flat = 0.0, flat + 1
        dt_worst = max(dt_worst, dt)
        dv_worst = max(dv_worst, abs(m[2] - v))
    return {"events_n": len(theirs), "time_worst": round(dt_worst, 1), "event_worst": round(dv_worst, 4),
            "unmatched": missed, "flat": flat, "listing_off": off}


def _check(h, periods):
    """The fit against every hourly height and every high and low of the periods."""
    sq = worst = 0.0
    n = 0
    ev = {"events_n": 0, "time_worst": 0.0, "event_worst": 0.0, "unmatched": 0, "flat": 0, "listing_off": 0}
    for p in periods:
        for t, v in p.samples(timedelta(hours=1)):
            e = foreman.height(h, t) - v
            sq += e * e
            worst = max(worst, abs(e))
            n += 1
        got = _match_events(h, p.events, lambda t: _between(p.at, t), p.t0, p.t1)
        for k in ("events_n", "unmatched", "flat", "listing_off"):
            ev[k] += got[k]
        for k in ("time_worst", "event_worst"):
            ev[k] = max(ev[k], got[k])
    return {"height_n": n, "height_rms": round(math.sqrt(sq / n), 4), "height_worst": round(worst, 4), **ev}


def _passes(c):
    return (c["height_rms"] <= PASS_RMS and c["height_worst"] <= PASS_HEIGHT and c["time_worst"] <= PASS_MIN
            and c["event_worst"] <= PASS_HEIGHT and not c["unmatched"])


def fit_path(code):
    return os.path.join(DB, f"{code}_fit.json")


def fit_file(doc):
    """A station's constants, fitted to its newest FIT_YEARS of CHS's predictions and tested on
    the span _plan names, with how closely they reproduce both; from this machine, or downloaded,
    fitted and kept when missing. The predictions themselves are dropped once the fit is made."""
    path = fit_path(doc["id"])
    if os.path.exists(path):
        return _load(path)
    years, (a, b) = _plan(doc)
    fitted = [_Period(doc, datetime(y, 1, 1, tzinfo=UTC), datetime(y + 1, 1, 1, tzinfo=UTC), str(y)) for y in years]
    test = _Period(doc, a, b, _span_text((a, b)))
    print(f"fitting Foreman's constituents to CHS {doc['id']} {doc['name']}, {years[0]} to {years[-1]} "
          "(a minute or two) ...", file=sys.stderr, flush=True)
    hours = (fitted[-1].t1 - fitted[0].t0).total_seconds() / 3600
    probe = [s for p in fitted for s in p.samples(PROBE_EVERY)]
    h = foreman.fit_station([s for p in fitted for s in p.samples(FIT_EVERY)], float(doc["lat"]), hours, probe)
    check, tested = _check(h, fitted), _check(h, [test])
    out = {"station": doc["id"], "fitted": date.today().isoformat(), "years": years, "check": check,
           "test_span": [_iso(a), _iso(b)], "test": tested, "passes": _passes(check) and _passes(tested),
           "constants": h}
    _save(path, out)
    return out


def _one(c):
    notes = [f"{c[k]} {w}" for k, w in (("unmatched", "unmatched"), ("flat", "on a flat stand, judged on height"),
                                         ("listing_off", "where CHS's listing is off its own series, left out")) if c[k]]
    return (f"{c['height_rms']:.4f} m rms and {c['height_worst']:.3f} m at worst, highs and lows within "
            f"{c['time_worst']:.0f} min and {c['event_worst']:.3f} m" + (f" ({', '.join(notes)})" if notes else ""))


def _accuracy(fd):
    return (f"CHS's {fd['years'][0]} to {fd['years'][-1]} predictions, which they were fitted to, within {_one(fd['check'])}; "
            f"CHS's {_span_text(fd['test_span'])}, which they were tested on, within {_one(fd['test'])}")


def refusal(doc):
    """Why a station answers nothing: nothing to fit to, or constants that fall short of CHS's
    own predictions; None when it answers. Makes the fit when missing."""
    why = unusable(doc)
    if why:
        return why
    fd = fit_file(doc)
    if fd["passes"]:
        return None
    return (f"the constants fitted to it reproduce {_accuracy(fd)}, outside the tool's limits ({PASS_RMS} m rms, "
            f"{PASS_HEIGHT} m at worst, highs and lows within {PASS_MIN:.0f} min and {PASS_HEIGHT} m), so the tool cannot "
            f"reproduce CHS's predictions there. Choose another station with `stations --near`; CHS may have revised "
            f"its predictions inside the span the fit reads, and a fit made after CHS's next year "
            f"(delete {os.path.relpath(fit_path(doc['id']), TOOLS)}) may pass")


def ready(code):
    """Whether a station is on this machine in full: its file, and its fit where it has one."""
    path = os.path.join(DB, f"{code}.json")
    if not os.path.exists(path):
        return False
    return bool(unusable(_load(path))) or os.path.exists(fit_path(code))


def make_ready(doc):
    """Make a station's fit, so it answers with no connection. Returns why it answers nothing, or None."""
    return refusal(doc)


# --- prediction ----------------------------------------------------------------------------

_BEYOND = set()


def _constants(doc, t0, t1):
    why = refusal(doc)
    if why:
        sys.exit(f"{doc['id']} {doc['name']}: {why}.")
    if not _inside(doc, t0, t1):
        _BEYOND.add(doc["id"])
    return fit_file(doc)["constants"]


def height(doc, t):
    """Metres above Chart Datum at UTC datetime t, from the station's fitted constants."""
    return foreman.height(_constants(doc, t, t + timedelta(minutes=1)), t)


def extremes(doc, start, end):
    """The highs and lows between two UTC datetimes: [(utc datetime, "H" or "L", metres)]."""
    h = _constants(doc, start, end)
    return [e for e in find_extremes(lambda t: foreman.height(h, t), start - timedelta(minutes=12), end)
            if start <= e[0] < end]


def provenance(doc):
    """What this run's answers at the station came from."""
    port = "a reference port" if doc.get("reference_port") else (
        f"a secondary station of {doc['ref']}" if doc.get("ref") else "a secondary station")
    fd = fit_file(doc)
    parts = [f"constants fitted by Foreman's method, CHS's own, on {fd['fitted']}, which reproduce {_accuracy(fd)}"]
    if doc["id"] in _BEYOND:
        parts.append(f"past the span CHS publishes ({_held_text(doc)}), the same constants carried forward or back")
    return "; ".join(parts + [f"{port}, station as fetched {doc['fetched']}"])


# --- the check against CHS's live predictions -----------------------------------------------

def compare(doc, day0, days, height_tol, time_tol):
    """The station's constants against CHS's live API from `day0` for `days`: every 15-minute
    height within height_tol, and every high and low within time_tol and height_tol, a flat stand
    judged on its height and a high or low off CHS's own series left out and counted."""
    t0 = datetime(day0.year, day0.month, day0.day, tzinfo=UTC)
    t1 = t0 + timedelta(days=days)
    r = {"station": doc["id"], "ok": True}
    why = refusal(doc)
    if why or not _inside(doc, t0, t1):
        return {**r, "ok": False, "error": why or f"the span asked for is outside what CHS holds, {_held_text(doc)}"}
    h = fit_file(doc)["constants"]
    live = dict(_span(doc, SERIES, t0, t1, "FIFTEEN_MINUTES"))
    worst = max(abs(foreman.height(h, t) - v) for t, v in live.items())
    ev = _match_events(h, _events(doc, t0, t1, lambda t: _between(live.get, t)),
                       lambda t: _between(live.get, t), t0, t1)
    r.update(series_n=len(live), fit_worst=round(worst, 4), **ev)
    r["ok"] = worst <= height_tol and ev["time_worst"] <= time_tol and ev["event_worst"] <= height_tol and not ev["unmatched"]
    return r


def report(r):
    if "error" in r:
        return [f"CHS: nothing to compare ({r['error']})"]
    return [f"height every 15 minutes, {r['series_n']} values: worst {r['fit_worst']:.3f} m from CHS's",
            f"highs and lows, {r['events_n']}: worst {r['time_worst']:.1f} min and {r['event_worst']:.3f} m from CHS's"
            + "".join(f", {r[k]} {w}" for k, w in (("unmatched", "unmatched"), ("flat", "on a flat stand, judged on height"),
                                                   ("listing_off", "where CHS's listing is off its own series, left out"))
                      if r.get(k))]

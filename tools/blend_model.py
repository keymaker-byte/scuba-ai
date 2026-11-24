#!/usr/bin/env python3
"""Tidal currents at any point of a region and any height above the seabed: an ADCIRC tidal
database corrected by the current stations around the point, NOAA's and CHS's.

  blend_model.py build [--name N [--bbox S W N E]]      build a region, or rebuild every one
  blend_model.py extract --site F [F ...]                write each site's constants into its JSON
  blend_model.py predict --file F --date D --tz Z        slacks and peaks
  blend_model.py window --file F --date D --tz Z         diveable windows under a speed threshold
  blend_model.py at --file F --time "D HH:MM" --tz Z     current at a moment
  blend_model.py verify [--name N]                       accuracy against hidden stations
  blend_model.py selftest [--db ENPAC15|EC2015]          the astronomy against each database's header
  blend_model.py verify-stations --file F | --name N | STATION ...   cached station data against each network's live service
"""
import argparse
import json
import math
import os
import statistics
import sys
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from lib.adcirc import DATABASES, read_vel_header, read_vel_nodes  # noqa: E402
from lib.adcirc import selftest as adcirc_selftest  # noqa: E402
from lib.current_harmonics import events, series  # noqa: E402
from lib.current_stations import NETWORKS, cx  # noqa: E402
from lib import noaa_stations  # noqa: E402
from lib.seabed import Seabed  # noqa: E402
from lib.tcd import Harmonics, velocity  # noqa: E402
from lib.blend import (ABOVE_BOTTOM, adcirc_cons, along, built_regions, database_for, DB, DEG, EXACT_KM,
                       extract_point, floor_km, FORMAT, load_region, log, make_bin, Mesh, NEIGHBOURS,
                       neighbours, point_bin, PRIOR, profile_table, REACH_KM, Refused, region_path,
                       SOFTEN_KM, to_noaa, UTC, wrap90, xc)  # noqa: E402

WORKSPACE = os.path.dirname(HERE)

VERIFY_DAYS = 30    # days of each verify test, from 1 December this year
BANDS_KM = [(0, 2), (2, 6), (6, REACH_KM), (REACH_KM, None)]


def _cfg(key, default):
    """Read this tool's section of tool-config.json; missing file or key -> default."""
    try:
        with open(os.path.join(WORKSPACE, "tool-config.json")) as f:
            return json.load(f).get("blend_model", {}).get(key, default)
    except (OSError, ValueError):
        return default


def resolve_tz(name):
    try:
        return ZoneInfo(name)
    except Exception:
        sys.exit(f"{name} is not an IANA time zone name. Pass the site's `tz` from its JSON, e.g. America/Los_Angeles.")


# --- the region's sources -----------------------------------------------------------------


def each(a, fn, known, what, fill):
    """Run `fn` on the one named, its missing arguments filled from what is already known, or on
    every one known when none is named."""
    if a.name is None:
        if not known:
            sys.exit(f"No {what} exists yet: name a new one with --name and give its --bbox.")
        for name in known:
            log(f"== {name}")
            fn(argparse.Namespace(**{**vars(a), "name": name, **fill(known[name])}))
        return
    if a.name in known:
        a = argparse.Namespace(**{**vars(a), **{k: v for k, v in fill(known[a.name]).items() if getattr(a, k) is None}})
    missing = [k for k in fill({}) if getattr(a, k) is None] if a.name not in known else []
    if missing:
        sys.exit(f"{a.name} is a new {what}: give " + " and ".join(f"--{k}" for k in missing) + ".")
    fn(a)


def legacy_harmonics():
    """The 2010 legacy tables, downloaded by noaa_legacy_current on first use."""
    import noaa_legacy_current
    noaa_legacy_current.index()
    return Harmonics(noaa_legacy_current.TCD)


def cmd_build(a):
    each(a, build_one, built_regions(), "region", lambda bbox: {"bbox": bbox})


def build_one(a):
    S, W, N, E = a.bbox
    inbox = lambda la, lo: S <= la <= N and W <= lo <= E
    db = database_for(a.bbox)
    fit_year = date.today().year  # the year of CHS predictions the Canadian constants are fitted to
    networks = [n() for n in NETWORKS]
    kind_of = {n.kind: n for n in networks}
    sources, others = [], []
    for n in networks:
        s, o = n.gather(inbox, fit_year)
        sources += s
        others += o
    legacy = []
    h = legacy_harmonics()
    recs = list(h.records())
    for r in recs:
        if r["type"] == 2 and "Current" in r["name"] and inbox(r["lat"], r["lon"]) and recs[r["ref"]]["type"] == 1:
            legacy.append({"id": r["name"], "kind": "legacy", "name": r["name"], "lat": r["lat"], "lon": r["lon"],
                           **{k: r[k] for k in ("ref", "flood_dir", "ebb_dir", "flood_time", "ebb_time",
                                                "flood_mult", "ebb_mult", "sbf_time", "sbe_time")}})
    log(", ".join(f"{sum(s['kind'] == n.kind for s in sources)} {n.kind} stations" for n in networks)
        + f", {len(others)} other stations without constants, {len(legacy)} legacy subordinate stations")

    mesh = Mesh(db, a.bbox)
    seabed = Seabed()
    pts = sources + legacy
    for s in pts:
        nodes, w, la, lo = mesh.place(s["lat"], s["lon"])
        s["_nodes"], s["_w"] = nodes, w
        s["node"] = max(zip(w, nodes))[1]
        s["seabed_mesh"] = round(sum(wi * mesh.dep[n] for wi, n in zip(w, nodes)), 2)
        # the seabed from the bathymetry that covers the station, where one is on this machine
        e, src = seabed.elevation(s["lat"], s["lon"])
        s["seabed_dem"] = round(-e, 2) if e is not None and e < 0 else None
        s["seabed_source"] = src if s["seabed_dem"] is not None else None
    if pts:
        header = read_vel_header(db)
        log(f"Streaming the velocity file for {len(pts)} points (a few minutes)...")
        vals = read_vel_nodes(db, sorted({n for s in pts for n in s["_nodes"]}))
    else:
        log("No station in the box: every point takes the database's own current, scaled to the height.")
    for s in pts:
        s["uv"] = to_noaa(adcirc_cons(header, vals, s["_nodes"], s["_w"]), db)

    rows = []
    for s in sources:
        # every bin with its height as a fraction of the depth above the seabed, its steady
        # current, its axis and its constants
        rows += kind_of[s["kind"]].prepare(s, s["seabed_dem"] or s["seabed_mesh"], s["seabed_dem"], fit_year, log)
    log(f"  vertical profile from {len({r['id'] for r in rows})} stations, {len(rows)} bins")

    log("Paths through the water between stations...")
    node_of = {}
    for i, s in enumerate(sources):
        node_of.setdefault(s["node"], []).append(i)
    for s in pts:
        d = mesh.paths(s["node"], 60.0)
        s["water_km"] = {str(i): round(d[n], 3) for n, ii in node_of.items() if n in d for i in ii if sources[i] is not s}
    for s in pts:
        s["uv"] = {k: [cx(zu), cx(zv)] for k, (zu, zv) in s["uv"].items()}
        for k in ("_nodes", "_w", "_bins"):
            s.pop(k, None)
    doc = {"format": FORMAT, "name": a.name, "bbox": a.bbox, "db": db, "built": datetime.now(UTC).isoformat(timespec="seconds"), "fit_year": fit_year,
           "sources": sources, "others": others, "legacy": legacy, "profile_rows": rows,
           "settings": {"neighbours": NEIGHBOURS, "reach_km": REACH_KM, "soften_km": SOFTEN_KM, "prior": PRIOR,
                        "exact_km": EXACT_KM}}
    os.makedirs(DB, exist_ok=True)
    with open(region_path(a.name) + ".part", "w") as f:
        json.dump(doc, f, separators=(",", ":"))
    os.replace(region_path(a.name) + ".part", region_path(a.name))
    log(f"  wrote {os.path.relpath(region_path(a.name), WORKSPACE)}")


# --- a point --------------------------------------------------------------------------------

def read_site(path):
    """A site JSON's coordinate and seabed depth: (doc, lat, lon, seabed_m); refuses a file it cannot
    read or one missing any of them."""
    try:
        with open(path) as f:
            doc = json.load(f)
    except OSError as e:
        raise Refused(f"Could not read --site {path}: {e}")
    except json.JSONDecodeError as e:
        raise Refused(f"Could not parse JSON in {path}: {e}")
    missing = [k for k in ("lat", "lon", "seabed_m") if not isinstance(doc.get(k), (int, float))]
    if missing:
        raise Refused(f"{path} has no {', '.join(missing)}: the site JSON carries the dive area's coordinate and "
                      f"its seabed depth below the datum, written when the site is created.")
    if doc["seabed_m"] <= 0:
        raise Refused(f"{path}: seabed_m is the seabed depth below the datum, a positive number of metres.")
    return doc, doc["lat"], doc["lon"], doc["seabed_m"]


def cmd_extract(a):
    """Every site given, each written into its own JSON. Every site is read and placed before any
    is written, so a refused one stops the run with nothing changed; the database's constants for
    all of them are read in one pass."""
    jobs, refused = [], []
    for path in a.site:
        try:
            doc, lat, lon, H = read_site(path)
            jobs.append({"path": path, "doc": doc, "lat": lat, "lon": lon, "H": H})
        except Refused as e:
            refused.append(str(e))
    groups = {}
    for j in jobs:
        reg = load_region(lat=j["lat"], lon=j["lon"])
        groups.setdefault(reg["name"], [reg, []])[1].append(j)
    meshes = {}
    for name, (reg, js) in groups.items():
        mesh = meshes[name] = Mesh(reg["db"], reg["bbox"])
        for j in js:
            try:
                j["nodes"], j["w"], ext = mesh.place_site(j["lat"], j["lon"])
            except Refused as e:
                refused.append(f"{j['path']}: {e}")
                continue
            if ext:
                log(f"  {j['path']}: water the mesh does not reach, the mesh edge's constants "
                    f"{ext * 1000:.0f} m away across water")
    if refused:
        sys.exit("Nothing was written. Stop and report:\n  " + "\n  ".join(refused))
    for name, (reg, js) in groups.items():
        mesh = meshes[name]
        header = read_vel_header(reg["db"])
        nodes = sorted({n for j in js for n in j["nodes"]})
        log(f"Streaming the {reg['db']} velocity file for {len(js)} point(s), {len(nodes)} nodes (a minute or several)...")
        vals = read_vel_nodes(reg["db"], nodes)
        for j in js:
            log(j["path"])
            uv = to_noaa(adcirc_cons(header, vals, j["nodes"], j["w"]), reg["db"])
            start = max(zip(j["w"], j["nodes"]))[1]
            cur = extract_point(uv, start, mesh, reg, j["H"], ABOVE_BOTTOM, j["lat"], j["lon"])
            j["doc"]["blend_model_current"] = cur
            with open(j["path"] + ".part", "w") as f:
                f.write(json.dumps(j["doc"], indent=2) + "\n")
            os.replace(j["path"] + ".part", j["path"])
            log(f"  wrote blend_model_current into {j['path']}")


def load_doc(a):
    try:
        with open(a.file) as fh:
            doc = json.load(fh)
    except OSError as e:
        sys.exit(f"Could not read --file {a.file}: {e}")
    except json.JSONDecodeError as e:
        sys.exit(f"Could not parse JSON in {a.file}: {e}")
    if "extract_point" not in doc.get("blend_model_current", {}):
        sys.exit(f"No blend_model_current extract in {a.file}: run `extract --site {a.file}`.")
    if getattr(a, "raw", False):
        doc.pop("blend_model_observed_offset", None)
    return doc


PAD_MIN = 180  # minutes of model curve either side of a day, for the offset's time shift


def curve(doc, b, start, minutes):
    """[(utc datetime, speed)] every minute at the site: the model's curve, moved by the site's
    observed offset where one is established. Each slack moves by its own offset, slack before
    flood or slack before ebb, and the moments between two slacks move by an offset that runs
    evenly from one to the other."""
    off = doc.get("blend_model_observed_offset") or {}
    fl, eb = off.get("before_flood_min"), off.get("before_ebb_min")
    if fl is None and eb is None:
        return series(b, start, minutes)
    m0 = start - timedelta(minutes=PAD_MIN)
    model = series(b, m0, minutes + 2 * PAD_MIN)
    slacks = []
    for k, (t, kind, _) in enumerate(ev := events(model)):
        if kind == "slack":
            nxt = next((v for _, kd, v in ev[k + 1:] if kd != "slack"), None)
            o = (fl if nxt is not None and nxt > 0 else eb) or 0
            slacks.append((t + timedelta(minutes=o), o))
    out, k = [], 0
    for m in range(minutes + 1):
        t = start + timedelta(minutes=m)
        while k + 1 < len(slacks) and slacks[k + 1][0] <= t:
            k += 1
        if not slacks:
            o = 0
        elif t <= slacks[0][0] or k + 1 == len(slacks):
            o = slacks[k][1]
        else:
            (ta, oa), (tb, ob) = slacks[k], slacks[k + 1]
            o = oa + (ob - oa) * (t - ta).total_seconds() / (tb - ta).total_seconds()
        x = (t - m0).total_seconds() / 60 - o
        i = max(0, min(len(model) - 2, int(x)))
        fr = min(max(x - i, 0.0), 1.0)
        out.append((t, model[i][1] + (model[i + 1][1] - model[i][1]) * fr))
    return out


def day_span(day, tz, pad=0):
    start = datetime(day.year, day.month, day.day, tzinfo=tz).astimezone(UTC)
    end = (datetime(day.year, day.month, day.day, tzinfo=tz) + timedelta(days=1)).astimezone(UTC)
    return start - timedelta(minutes=pad), int((end - start).total_seconds() // 60) + 2 * pad


def print_header(doc, day, tz):
    c = doc["blend_model_current"]
    p = c["extract_point"]
    print(f"{p['lat']:.5f}, {p['lon']:.5f}  {day}  {c['bottom']['above_bottom_m']:g} m above a {p['seabed_m']:g} m seabed  "
          f"({getattr(tz, 'key', None) or tz.tzname(None)})")
    fs = next((s for s in c["stations"] if s.get("sets_flood_ebb_direction")), None)
    src = (f", the flood direction of {fs['id']} {fs['km']:.1f} km away" if fs else
           ": the two ends of the current's axis, with no station to name which one is the flood")
    print(f"  flood {c['flood_dir']:.0f}°   ebb {c['ebb_dir']:.0f}°{src}")
    corr = [s for s in c["stations"] if s["km"] < REACH_KM]
    if corr:
        print("  corrected by " + ", ".join(f"{s['id']} {s['km']:.1f} km" for s in corr))
    else:
        print(f"  no station within {REACH_KM:.0f} km through the water: the database's own current")
    if "lat" in doc and (abs(doc["lat"] - p["lat"]) > 1e-6 or abs(doc["lon"] - p["lon"]) > 1e-6):
        print(f"  the site's coordinate ({doc['lat']}, {doc['lon']}) is not where this extract was taken: extract the site again")
    sb = doc.get("seabed_m")
    if sb is not None and abs(sb - p["seabed_m"]) > 0.005:
        print(f"  the site's seabed is {sb:g} m, and this extract was made for {p['seabed_m']:g} m: extract the site again")
    built = _region_built(p["lat"], p["lon"])
    if built and _when(built) > _when(p["extracted"]):
        print(f"  the region was rebuilt on {built[:10]}, after this extract ({p['extracted'][:10]}): extract the site again")
    off = doc.get("blend_model_observed_offset")
    if off:
        print(f"  observed offset applied: slack before flood {_mins(off.get('before_flood_min'))}, "
              f"slack before ebb {_mins(off.get('before_ebb_min'))}")
    print()


def _region_built(lat, lon):
    """When the region holding a point was last built, or None where none is on this machine."""
    if not os.path.isdir(DB):
        return None
    for fn in sorted(os.listdir(DB)):
        if fn.endswith(".json") and "_" not in fn:
            try:
                with open(os.path.join(DB, fn)) as f:
                    reg = json.load(f)
            except (OSError, ValueError):
                continue
            S, W, N, E = reg["bbox"]
            if S <= lat <= N and W <= lon <= E:
                return reg.get("built")
    return None


def _when(stamp):
    t = datetime.fromisoformat(stamp)
    return t if t.tzinfo else t.replace(tzinfo=UTC)


def _mins(m):
    return "none" if m is None else f"{abs(m):g} min {'after' if m >= 0 else 'before'} the model"


def cmd_predict(a):
    doc = load_doc(a)
    tz = resolve_tz(a.tz)
    c = doc["blend_model_current"]
    print_header(doc, a.date, tz)
    start, minutes = day_span(a.date, tz, pad=5)
    up = {round(t.timestamp() / 60): v for t, kind, v in events(curve(doc, c["upper"], start, minutes)) if kind != "slack"}
    print(f"            bottom      fastest above ({c['upper']['above_bottom_m']:g} m off the bottom)")
    for t, kind, v in events(curve(doc, c["bottom"], start, minutes)):
        tl = (t + timedelta(seconds=30)).astimezone(tz)
        if tl.date() != a.date:
            continue
        if kind == "slack":
            print(f"  {tl:%H:%M}  SLACK")
        else:
            m = round(t.timestamp() / 60)
            k = min(up, key=lambda x: abs(x - m), default=None)
            above = f"   {up[k]:+.2f} m/s" if k is not None and abs(k - m) < 60 and (up[k] > 0) == (v > 0) else ""
            print(f"  {tl:%H:%M}  {kind:<9} {v:+.2f} m/s{above}")


def cmd_window(a):
    doc = load_doc(a)
    tz = resolve_tz(a.tz)
    c = doc["blend_model_current"]
    lim = a.max_speed
    print_header(doc, a.date, tz)
    print(f"  windows with |current| <= {lim:.2f} m/s at the bottom, each with its peak there and in the fastest water above\n")
    start, minutes = day_span(a.date, tz)
    bot = curve(doc, c["bottom"], start, minutes)[:-1]
    upv = [v for _, v in curve(doc, c["upper"], start, minutes)[:-1]]
    runs, cur = [], []
    for k, (t, v) in enumerate(bot):
        if abs(v) <= lim:
            cur.append((t, v, upv[k]))
        elif cur:
            runs.append(cur)
            cur = []
    if cur:
        runs.append(cur)
    if not runs:
        print(f"  none, current never drops below {lim:.2f} m/s at the bottom.")
        return
    for run in runs:
        mins = len(run)
        peak = max(abs(v) for _, v, _ in run)
        above = max(abs(u) for _, _, u in run)
        if mins >= minutes:
            print(f"  all day          peak {peak:.2f} m/s, above {above:.2f} m/s")
            continue
        t0, t1 = run[0][0].astimezone(tz), (run[-1][0] + timedelta(minutes=1)).astimezone(tz)
        flag = "  <-- tight" if mins < 40 else ""
        print(f"  {t0:%H:%M} - {t1:%H:%M}   {mins:>3} min   peak {peak:.2f} m/s, above {above:.2f} m/s{flag}")


def cmd_at(a):
    doc = load_doc(a)
    tz = resolve_tz(a.tz)
    c = doc["blend_model_current"]
    t = datetime.strptime(a.time, "%Y-%m-%d %H:%M").replace(tzinfo=tz)
    print_header(doc, t.date(), tz)
    tu = t.astimezone(UTC)
    for lbl, b in (("bottom", c["bottom"]), (f"{c['upper']['above_bottom_m']:g} m off the bottom", c["upper"])):
        v = curve(doc, b, tu, 0)[0][1]
        print(f"  {t:%H:%M}  {lbl:<22} {abs(v):.2f} m/s toward {c['flood_dir'] if v >= 0 else c['ebb_dir']:.0f}° "
              f"({'flood' if v >= 0 else 'ebb'})")


# --- verify -----------------------------------------------------------------------------------

def _pairs(er, ex, slack):
    A = [e for e in er if (e[1] == "slack") == slack and "min" not in e[1]]
    B = [e for e in ex if (e[1] == "slack") == slack and "min" not in e[1]]
    out = []
    for e in A:
        best = None
        for f in B:
            d = abs((f[0] - e[0]).total_seconds())
            if d < 3 * 3600 and (slack or (f[2] > 0) == (e[2] > 0)) and (best is None or d < best[0]):
                best = (d, f)
        if best:
            out.append((e, best[1]))
    return out


def score(er, ex, minpk=0.15):
    """Median slack time error (min), share of slacks within 15 min, median peak speed error."""
    sl = [abs((f[0] - e[0]).total_seconds()) / 60 for e, f in _pairs(er, ex, True)]
    pk = [abs(abs(f[2]) / abs(e[2]) - 1) for e, f in _pairs(er, ex, False) if abs(e[2]) > minpk]
    if not sl:
        return None
    nsl = sum(1 for e in er if e[1] == "slack")
    return {"slack": statistics.median(sl), "slack15": sum(v <= 15 for v in sl) / max(nsl, 1),
            "speed": statistics.median(pk) if pk else None}


def _q(v, p):
    v = sorted(x for x in v if x is not None)
    return v[min(len(v) - 1, int(p * len(v)))] if v else float("nan")


def _summary(rows):
    rows = [r for r in rows if r]
    if not rows:
        return None
    sp = [r["speed"] for r in rows if r["speed"] is not None]
    return {"n": len(rows), "slack_min": round(statistics.median(r["slack"] for r in rows), 1),
            "slack_p80": round(_q([r["slack"] for r in rows], 0.8), 1),
            "within15_pct": round(100 * statistics.mean(r["slack15"] for r in rows)),
            "speed_pct": round(100 * statistics.median(sp)) if sp else None}


def _table(title, res, methods):
    print(f"\n{title}")
    for lo, hi in [(0, None)] + BANDS_KM:
        sel = lambda r: r and lo <= r["km"] < (hi if hi is not None else 1e9)
        label = "all" if (lo, hi) == (0, None) else f"nearest station {lo:g} to {hi:g} km" if hi else f"nearest station beyond {lo:g} km"
        n = sum(1 for r in res[methods[0]] if sel(r))
        if not n:
            continue
        print(f"  {label}, {n} points")
        for m in methods:
            s = _summary([r for r in res[m] if sel(r)])
            if s:
                print(f"    {m:28s} slack {s['slack_min']:4.0f} min (80% within {s['slack_p80']:3.0f})   "
                      f"within 15 min {s['within15_pct']:3d}%   peak speed {s['speed_pct'] if s['speed_pct'] is not None else '':>3}%")


def cmd_verify(a):
    each(a, verify_one, built_regions(), "region", lambda bbox: {})


def verify_one(a):
    reg = load_region(a.name)
    sources = reg["sources"]
    if not any(s["kind"] == "noaa" for s in sources):
        # every test predicts a NOAA station's bins; a region without them has nothing to test,
        # and its predictions are the database's own current scaled to the height
        out = {"verified": date.today().isoformat(), "stations": 0}
        with open(os.path.join(DB, f"{reg['name']}_verify.json"), "w") as f:
            json.dump(out, f, indent=1)
        print(f"The {reg['name']} region holds no NOAA harmonic station: nothing to verify against. "
              f"Its predictions are the {reg['db']} database's own current, scaled to the height.")
        return
    days, start = VERIFY_DAYS, date(date.today().year, 12, 1)
    t0 = datetime(start.year, start.month, start.day, tzinfo=UTC)
    minutes = days * 1440
    ser = lambda b: series(b, t0, minutes, 6)
    methods = ["nearest station", "ADCIRC, 1/7 power", "Blend Model"]
    res = {m: [] for m in methods}
    law = lambda f: (8 / 7) * max(f, 0.01) ** (1 / 7)
    log(f"Hidden stations: each NOAA station's deepest bin, predicted without it, {days} days from {start}...")
    for i, s in enumerate(sources):
        if s["kind"] != "noaa":
            continue
        bins = [b for b in noaa_stations.station(s["id"])["bins"].values() if b.get("cons") and b.get("depth") is not None]
        if not bins:
            continue
        tb = max(bins, key=lambda b: b["depth"])
        H = s["seabed_dem"] or s["seabed_mesh"]
        frac = max((H - tb["depth"]) / H, 0.02)
        dists = floor_km({int(j): d for j, d in s["water_km"].items()}, s["lat"], s["lon"], sources)
        cand = neighbours(dists, sources, exclude=s["id"])
        prof = profile_table(reg["profile_rows"], exclude=s["id"])
        bm_, az, _ = point_bin(s["uv"], cand, prof, frac, dists, sources, exclude=s["id"])
        preds = {"Blend Model": bm_}
        raw = {k: z * law(frac) for k, z in along(s["uv"], az).items()}
        preds["ADCIRC, 1/7 power"] = make_bin(raw, 0.0, az)
        near = sorted((d, j) for j, d in dists.items() if sources[j]["id"] != s["id"])
        if near:
            o = sources[near[0][1]]
            if o["kind"] == "chs":
                nb = {"cons": o["cons"], "mean_major": o["mean_major"], "azimuth": o["flood"]}
            else:
                ob = [b for b in noaa_stations.station(o["id"])["bins"].values() if b.get("cons") and b.get("depth") is not None]
                Ho = o["seabed_dem"] or o["seabed_mesh"]
                nb = min(ob, key=lambda b: abs((Ho - b["depth"]) / Ho - frac))
            if math.cos((nb["azimuth"] - az) * DEG) < 0:
                nb = {"cons": [[c[0], c[1], (c[2] + 180) % 360, 0, 0] for c in nb["cons"]],
                      "mean_major": -(nb.get("mean_major") or 0)}
            preds["nearest station"] = nb
        sign = 1 if math.cos((tb["azimuth"] - az) * DEG) >= 0 else -1
        truth = events(ser(tb if sign > 0 else {"cons": [[c[0], c[1], (c[2] + 180) % 360, 0, 0] for c in tb["cons"]],
                                                   "mean_major": -(tb.get("mean_major") or 0)}))
        km = cand[0][0] if cand else (near[0][0] if near else 99)
        for m in methods:
            sc = score(truth, events(ser(preds[m]))) if m in preds else None
            if sc:
                sc.update(id=s["id"], km=km)
            res[m].append(sc)
    _table(f"Hidden stations, {sum(1 for r in res[methods[-1]] if r)} NOAA stations' deepest bins, "
           f"by the distance through the water to the nearest other station", res, methods)

    leg_res = {m: [] for m in ("nearest station", "ADCIRC, surface", "Blend Model")}
    if reg["legacy"]:
        log(f"Legacy stations: {len(reg['legacy'])} subordinate stations of the 2010 tables...")
        h = legacy_harmonics()
        recs = list(h.records())
        refev = {}
        prof = profile_table(reg["profile_rows"])
        for p in reg["legacy"]:
            if p["ref"] not in refev:
                r = recs[p["ref"]]
                refev[p["ref"]] = events([(t0 + timedelta(minutes=m), velocity(h, r, t0 + timedelta(minutes=m)))
                                          for m in range(0, minutes + 1, 6)])
            avg = ((p["flood_time"] or 0) + (p["ebb_time"] or 0)) / 2
            ev, truth = refev[p["ref"]], []
            for k, (t, kind, v) in enumerate(ev):
                if "min" in kind:
                    continue
                if kind == "slack":
                    nxt = next((x[1] for x in ev[k + 1:] if x[1] in ("flood", "ebb")), None)
                    adj = p["sbf_time"] if nxt == "flood" else p["sbe_time"]
                    truth.append((t + timedelta(minutes=adj if adj is not None else avg), "slack", 0.0))
                elif kind == "flood":
                    truth.append((t + timedelta(minutes=p["flood_time"] or 0), "flood", v * p["flood_mult"]))
                else:
                    truth.append((t + timedelta(minutes=p["ebb_time"] or 0), "ebb", v * p["ebb_mult"]))
            truth.sort()
            uv = {k: (xc(v[0]), xc(v[1])) for k, v in p["uv"].items()}
            dists = floor_km({int(j): d for j, d in p["water_km"].items()}, p["lat"], p["lon"], sources)
            az = p["flood_dir"]   # the legacy table's own axis
            cand = neighbours(dists, sources)
            bm_, baz, _ = point_bin(uv, cand, prof, 0.9, dists, sources)
            if math.cos((baz - az) * DEG) < 0:
                bm_ = {"cons": [[c[0], c[1], (c[2] + 180) % 360, 0, 0] for c in bm_["cons"]],
                       "mean_major": -bm_["mean_major"], "azimuth": az}
            preds = {"Blend Model": bm_,
                     "ADCIRC, surface": make_bin({k: z * 8 / 7 for k, z in along(uv, az).items()}, 0.0, az)}
            near = sorted((d, j) for j, d in dists.items())
            if near:
                o = sources[near[0][1]]
                if o["kind"] == "chs":
                    nb = {"cons": o["cons"], "mean_major": o["mean_major"], "azimuth": o["flood"]}
                else:
                    ob = [b for b in noaa_stations.station(o["id"])["bins"].values() if b.get("cons")]
                    nb = min(ob, key=lambda b: b.get("depth") or 0)
                if math.cos((nb["azimuth"] - az) * DEG) < 0:
                    nb = {"cons": [[c[0], c[1], (c[2] + 180) % 360, 0, 0] for c in nb["cons"]],
                          "mean_major": -(nb.get("mean_major") or 0)}
                preds["nearest station"] = nb
            km = cand[0][0] if cand else (near[0][0] if near else 99)
            for m in leg_res:
                sc = score(truth, events(ser(preds[m]))) if m in preds else None
                if sc:
                    sc.update(id=p["id"], km=km)
                leg_res[m].append(sc)
        _table(f"Legacy stations, {sum(1 for r in leg_res['Blend Model'] if r)} subordinate stations of "
               "the 2010 tables (their reference moved by their own corrections), near the surface", leg_res, list(leg_res))

    # at the stations themselves: each NOAA station's deepest, middle and top bin, predicted at its own
    # position with the station in place; the per-bin corrections make these the station's own
    log("At the stations: each NOAA station's deepest, middle and top bins, with the station in place...")
    at = {"slack": [], "speed": [], "direction": []}
    prof = profile_table(reg["profile_rows"])
    for i, s in enumerate(sources):
        if s["kind"] != "noaa" or not s["seabed_dem"]:
            continue
        bins = sorted((b for b in noaa_stations.station(s["id"])["bins"].values() if b.get("cons") and b.get("depth") is not None),
                      key=lambda b: b["depth"])
        if not bins:
            continue
        dists = floor_km({int(j): d for j, d in s["water_km"].items()}, s["lat"], s["lon"], sources) | {i: 0.0}
        cand = neighbours(dists, sources)
        H = s["seabed_dem"]
        for tb in {id(b): b for b in (bins[-1], bins[len(bins) // 2], bins[0])}.values():
            frac = min(max((H - tb["depth"]) / H, 0.02), 0.98)
            pb, az, _ = point_bin(s["uv"], cand, prof, frac, dists, sources)
            sc = score(events(ser(tb)), events(ser(pb)))
            if sc:
                at["slack"].append(sc["slack"])
                if sc["speed"] is not None:
                    at["speed"].append(sc["speed"])
            at["direction"].append(abs(wrap90(az - tb["azimuth"])))
    at_sum = {"n": len(at["direction"]), "slack_min": round(statistics.median(at["slack"]), 1),
              "slack_p90": round(_q(at["slack"], 0.9), 1), "speed_pct": round(100 * statistics.median(at["speed"]), 1),
              "speed_p90": round(100 * _q(at["speed"], 0.9), 1), "direction_deg": round(statistics.median(at["direction"]), 1),
              "direction_p90": round(_q(at["direction"], 0.9), 1)}
    print(f"\nAt the stations, {at_sum['n']} bins of NOAA stations, each predicted at its own position and height")
    print(f"    slack {at_sum['slack_min']:g} min (90% within {at_sum['slack_p90']:g})   peak speed {at_sum['speed_pct']:g}% "
          f"(90% within {at_sum['speed_p90']:g})   direction {at_sum['direction_deg']:g}° (90% within {at_sum['direction_p90']:g})")

    by = []
    for lo, hi in BANDS_KM:
        s = _summary([r for r in res["Blend Model"] if r and lo <= r["km"] < (hi if hi is not None else math.inf)])
        if s:
            by.append({"from_km": lo, "to_km": hi} | s)
    out = {"verified": date.today().isoformat(), "start": start.isoformat(), "days": days,
           "by_distance": by,
           "hidden": {m: _summary(res[m]) for m in methods},
           "legacy": {m: _summary(leg_res[m]) for m in leg_res}, "at_stations": at_sum}
    with open(os.path.join(DB, f"{reg['name']}_verify.json"), "w") as f:
        json.dump(out, f, indent=1)
    print(f"\n  wrote tools/db/blend_model/{reg['name']}_verify.json, the figures the tool's documentation quotes")


def cmd_selftest(a):
    if not adcirc_selftest(a.db):
        sys.exit(1)


def cmd_verify_stations(a):
    """Each station's cached data against its own network's live service: the stations a site's
    extract names, every station of a built region, or the stations named."""
    if a.file:
        with open(a.file) as f:
            ids = [s["id"] for s in json.load(f).get("blend_model_current", {}).get("stations", [])]
        if not ids:
            sys.exit(f"{a.file} has no extract with stations: run `extract --site {a.file}`.")
    elif a.name:
        ids = [s["id"] for s in load_region(a.name)["sources"]]
    elif a.station:
        ids = a.station
    else:
        sys.exit("give --file <slug.json>, --name <region>, or station IDs.")
    networks = [n() for n in NETWORKS]
    failed = []
    for sid in ids:
        net = next((n for n in networks if n.owns(sid)), None)
        if net is None:
            sys.exit(f"{sid} belongs to no station network the Blend Model reads ({', '.join(n.kind for n in networks)}).")
        ok, lines = net.verify(sid)
        print("\n".join(lines) + "\n", flush=True)
        if not ok:
            failed.append(sid)
    print(f"{len(ids) - len(failed)} of {len(ids)} stations pass" + (f"; FAIL: {', '.join(failed)}" if failed else "."))
    sys.exit(1 if failed else 0)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("build", help="gather a region's stations and their corrections")
    s.add_argument("--name", help="the region's name; omitted, every built region is rebuilt")
    s.add_argument("--bbox", nargs=4, type=float, metavar=("S", "W", "N", "E"),
                   help="a new region's box; a built region keeps its own")
    s.set_defaults(fn=cmd_build)

    s = sub.add_parser("extract", help="each site's constants, written into its JSON")
    s.add_argument("--site", metavar="PATH", nargs="+", required=True,
                   help="one or more site JSONs: reads each one's lat, lon and seabed_m, and writes the extract into it")
    s.set_defaults(fn=cmd_extract)

    def doc_source(sp):
        sp.add_argument("--file", metavar="PATH", required=True, help="path to the site JSON holding the extract")
        sp.add_argument("--tz", required=True, metavar="IANA_ZONE", help="the site's time zone, the `tz` in its JSON")
        sp.add_argument("--raw", action="store_true",
                        help="the model's own prediction, without the site's observed offset: what an offset is measured against")

    s = sub.add_parser("predict", help="slack / max flood / max ebb")
    doc_source(s)
    s.add_argument("--date", type=date.fromisoformat, required=True)
    s.set_defaults(fn=cmd_predict)

    s = sub.add_parser("window", help="diveable windows")
    doc_source(s)
    s.add_argument("--date", type=date.fromisoformat, required=True)
    ms = _cfg("max_speed_ms", 0.25)
    s.add_argument("--max-speed", type=float, default=ms, help=f"m/s, default {ms}")
    s.set_defaults(fn=cmd_window)

    s = sub.add_parser("at", help="the current at a moment")
    doc_source(s)
    s.add_argument("--time", required=True, metavar="YYYY-MM-DD HH:MM")
    s.set_defaults(fn=cmd_at)

    s = sub.add_parser("verify", help="accuracy against hidden NOAA stations and the legacy tables")
    s.add_argument("--name", help="the region's name; omitted, every built region")
    s.set_defaults(fn=cmd_verify)

    s = sub.add_parser("selftest", help="the astronomy against each database's ADCIRC header")
    s.add_argument("--db", choices=sorted(DATABASES), action="append",
                   help="one database (repeatable); default every database")
    s.set_defaults(fn=cmd_selftest)

    s = sub.add_parser("verify-stations", help="cached station data against each network's live service")
    g = s.add_mutually_exclusive_group()
    g.add_argument("--file", metavar="PATH", help="a site JSON: the stations its extract names")
    g.add_argument("--name", help="a built region: every station behind its corrections")
    s.add_argument("station", nargs="*", help="station IDs, as an extract lists them (PUG1501, CHS07100)")
    s.set_defaults(fn=cmd_verify_stations)

    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()

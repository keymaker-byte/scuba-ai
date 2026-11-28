#!/usr/bin/env python3
"""Shoreline orientation and wind fetch at a dive site, from OpenStreetMap's coastline and HydroLAKES.

  shore_exposure.py extract --site F --entry ELAT ELON   shore site: write the wind section into the site JSON
  shore_exposure.py extract --site F --boat              boat site: the same, with the dive area alone
  shore_exposure.py extract --site F ... --raise NE=bad  a direction moved up a class by local knowledge, --calm-only for all Bad
  shore_exposure.py extract --site F [F ...]             again, each at its recorded entry and with its recorded raises
  shore_exposure.py at LAT LON --entry ELAT ELON         a coordinate: both shore facings, the swim out, the fetch
  shore_exposure.py at LAT LON [--json]                  a coordinate, boat site: the dive area shore facing and the fetch
"""
import argparse
import datetime
import json
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import config, shapes  # noqa: E402

R_KM = 6371.0
POINTS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
          "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]


def _cfg(key, default):
    """This tool's section of tool-config.jsonc; a missing file or key gives the default."""
    return config.get("shore_exposure", key, default)


MAX_FETCH_KM = _cfg("max_fetch_km", 30)
SHORE_SPAN_M = _cfg("shore_span_m", 250)
USER_AGENT = config.user_agent()
shapes.USER_AGENT = USER_AGENT


# ---------------------------------------------------------------- shoreline datasets: lib/shapes.py

# ---------------------------------------------------------------- geometry
# A local flat projection centred on the dive point, in km: x east, y north. Over the 30 km a fetch
# is measured across, its distortion is a fraction of a percent, well inside what a fetch needs.

def _proj(lat0, lon0):
    k = math.cos(math.radians(lat0))
    return lambda p: (math.radians(p[0] - lon0) * R_KM * k, math.radians(p[1] - lat0) * R_KM)


def _segments(lines, proj, keep=lambda a, b: True):
    segs = []
    for line in lines:
        segs.extend((proj(a), proj(b)) for a, b in zip(line, line[1:]) if a != b and keep(a, b))
    return segs


def _axis_aligned(a, b):
    """An edge running exactly along a meridian or a parallel. The cuts that split the land polygons
    into pieces are all such edges, running through land between two points on the shoreline. A ray
    from the water reaches the shoreline before any cut, so fetch reads every edge; the facing leaves
    these out, losing only a few short real ones."""
    return a[0] == b[0] or a[1] == b[1]


def _cross(a, b):
    return a[0] * b[1] - a[1] * b[0]


def _bearing(v):
    return math.degrees(math.atan2(v[0], v[1])) % 360


def _point(b):
    return POINTS[int((b + 11.25) // 22.5) % 16]


def _nearest(segs):
    """Closest point on any segment to the origin: (distance km, point)."""
    best = (float("inf"), None)
    for a, b in segs:
        e = (b[0] - a[0], b[1] - a[1])
        t = max(0.0, min(1.0, -(a[0] * e[0] + a[1] * e[1]) / (e[0] ** 2 + e[1] ** 2)))
        q = (a[0] + t * e[0], a[1] + t * e[1])
        d = math.hypot(*q)
        if d < best[0]:
            best = (d, q)
    return best


def _nearest_to(segs, p):
    """Closest point on any segment to p: (distance km, point)."""
    d, q = _nearest([((a[0] - p[0], a[1] - p[1]), (b[0] - p[0], b[1] - p[1])) for a, b in segs])
    return d, (q[0] + p[0], q[1] + p[1])


def _shore_normal(segs, q, span_km):
    """Seaward direction of the shore around q: the length-weighted mean of each nearby segment's
    normal, each turned toward the water side (the side the dive point sits on)."""
    sx = sy = 0.0
    for a, b in segs:
        m = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        if math.hypot(m[0] - q[0], m[1] - q[1]) > span_km:
            continue
        e = (b[0] - a[0], b[1] - a[1])
        nv = (e[1], -e[0])                       # a normal, length = segment length
        if nv[0] * -m[0] + nv[1] * -m[1] < 0:    # turn it toward the dive point
            nv = (-nv[0], -nv[1])
        sx, sy = sx + nv[0], sy + nv[1]
    return None if sx == sy == 0 else _bearing((sx, sy))


def _fetch(segs, bearing, cap):
    """Distance from the dive point to the first shoreline crossed along a bearing, km, capped."""
    d = (math.sin(math.radians(bearing)), math.cos(math.radians(bearing)))
    best = cap
    for a, b in segs:
        e = (b[0] - a[0], b[1] - a[1])
        den = _cross(d, e)
        if abs(den) < 1e-15:
            continue
        s = _cross(a, e) / den
        t = _cross(a, d) / den
        if 1e-6 < s < best and 0.0 <= t <= 1.0:
            best = s
    return best


def _angle(a, b):
    return abs((a - b + 180) % 360 - 180)


def _relation(wind_from, faces):
    off = _angle(wind_from, faces)
    return "onshore" if off <= 67.5 else "cross-shore" if off <= 112.5 else "offshore"


def _km(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return R_KM * 2 * math.asin(math.sqrt(a))


def _initial_bearing(lat1, lon1, lat2, lon2):
    p1, p2, dl = math.radians(lat1), math.radians(lat2), math.radians(lon2 - lon1)
    return math.degrees(math.atan2(math.sin(dl) * math.cos(p2),
                                   math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl))) % 360


# ---------------------------------------------------------------- the exposure at a point

class Refused(Exception):
    pass


def exposure(lat, lon, entry=None, cap=MAX_FETCH_KM, span_m=SHORE_SPAN_M):
    """The shore facings and the fetch at a dive area coordinate, and with entry (lat, lon) the entry
    shore's facing and the swim out. Refused on land outside every lake, or with no shoreline in reach."""
    proj = _proj(lat, lon)
    lake = None
    land = shapes.polygons("land", lat, lon, cap)
    if any(shapes.contains(rings, lon, lat) for _, rings in land):
        lake = next(((rec, rings) for rec, rings in shapes.polygons("lakes", lat, lon, 0) if shapes.contains(rings, lon, lat)), None)
        if lake is None:
            raise Refused("the coordinate sits on land, and inside no HydroLAKES lake (10 ha or more); walk it toward the water")

    if lake:
        info = shapes.lake_record(lake[0])
        segs = _segments(lake[1], proj)
        facing_segs = segs
        source = (f"HydroLAKES, {info.get('Lake_name') or 'unnamed lake'} "
                  f"(Hylak_id {info.get('Hylak_id')}, {float(info.get('Lake_area') or 0):g} km²)")
    else:
        rings = [ring + ring[:1] for _, rings in land for ring in rings]
        segs = _segments(rings, proj)
        facing_segs = _segments(rings, proj, keep=lambda p, q: not _axis_aligned(p, q))
        source = f"OpenStreetMap land polygons, {len(land)} pieces within {cap:g} km"
    if not segs:
        raise Refused(f"no mapped shoreline within {cap:g} km of this coordinate")

    dist, q = _nearest(segs)
    faces = _shore_normal(facing_segs, q, max(span_m / 1000, dist))
    entry_faces = None
    if entry:
        edist, eq = _nearest_to(segs, proj((entry[1], entry[0])))
        entry_faces = _shore_normal(facing_segs, eq, span_m / 1000)
    ref = entry_faces if entry else faces
    rows = []
    for i in range(16):
        b = i * 22.5
        f = _fetch(segs, b, cap)
        rows.append({"from": POINTS[i], "bearing": b, "fetch_km": round(f, 2), "capped": f >= cap,
                     "relation": _relation(b, ref) if ref is not None else None})

    out = {
        "requested": [lat, lon],
        "source": source,
        "nearest_shore_m": round(dist * 1000),
        "nearest_shore_bearing": round(_bearing(q)),
        "faces": None if faces is None else round(faces),
        "shore_span_m": round(max(span_m, dist * 1000)),
        "max_fetch_km": cap,
        "fetch": rows,
    }
    if entry:
        elat, elon = entry
        eb = _initial_bearing(elat, elon, lat, lon)
        out["entry"] = {"point": [elat, elon], "shore_m": round(edist * 1000),
                        "faces": None if entry_faces is None else round(entry_faces),
                        "bearing_to_dive": round(eb),
                        "distance_m": round(_km(elat, elon, lat, lon) * 1000),
                        "off_shore_normal": None if entry_faces is None else round(_angle(eb, entry_faces))}
    return out


# ---------------------------------------------------------------- the classes
# Each direction is classed by its shore relation and fetch: fetch-limited wind wave growth (JONSWAP)
# at the wind tools' no-go speed builds ripples over 1 km of fetch and real chop over 5 km. Short fetch
# and Mixed sit on one rung: a wind tool reads both with its bands moved up.

CLASSES = ("fine", "mixed", "short", "bad")
RANK = {"fine": 0, "mixed": 1, "short": 1, "bad": 2}


def measured_class(relation, fetch_km):
    if relation == "onshore":
        return "bad" if fetch_km >= 5 else "short" if fetch_km >= 1 else "fine"
    if relation == "cross-shore":
        return "mixed" if fetch_km >= 5 else "fine"
    return "fine"


def sector_points(spec):
    """'SW-WNW' (clockwise end to end) or 'N' -> the compass points it holds, in order."""
    ends = spec.strip().upper().split("-")
    if len(ends) > 2 or any(e not in POINTS for e in ends):
        raise Refused(f"bad sector {spec!r}: use compass points, e.g. SW-WNW or N")
    i, j = POINTS.index(ends[0]), POINTS.index(ends[-1])
    out = [POINTS[i]]
    while i != j:
        i = (i + 1) % 16
        out.append(POINTS[i])
    return out


def parse_raises(specs):
    """--raise SECTOR=CLASS, repeatable, several comma separated -> {point: class}."""
    out = {}
    for spec in specs or []:
        for part in spec.split(","):
            sec, _, cls = part.partition("=")
            cls = cls.strip().lower()
            if cls not in ("short", "mixed", "bad"):
                raise Refused(f"bad raise {part!r}: write SECTOR=CLASS, the class one of short, mixed or bad")
            for pt in sector_points(sec):
                out[pt] = cls
    return out


def sectors_of(classes):
    """{class: [sector, ...]}: adjacent points of one class joined, named clockwise end to end."""
    out = {c: [] for c in CLASSES}
    if len(set(classes)) == 1:
        out[classes[0]].append("N-NNW")
        return out
    start = next(i for i in range(16) if classes[i] != classes[i - 1])
    i = start
    while True:
        j = i
        while classes[(j + 1) % 16] == classes[i] and (j + 1) % 16 != start:
            j = (j + 1) % 16
        out[classes[i]].append(POINTS[i] if i == j else f"{POINTS[i]}-{POINTS[j]}")
        i = (j + 1) % 16
        if i == start:
            return out


def classify(rows, raised, calm_only):
    """Each row's class, the measured class moved up by the raises, every row Bad when calm only;
    and the raises that no longer move their point, for a note."""
    idle = []
    for r in rows:
        m = measured_class(r["relation"], r["fetch_km"]) if r["relation"] else "fine"
        c = m
        if calm_only:
            c = "bad"
        elif r["from"] in raised:
            if RANK[raised[r["from"]]] > RANK[m]:
                c = raised[r["from"]]
            else:
                idle.append(f"{r['from']} is {m} as measured, so raising it to {raised[r['from']]} moves nothing")
        r["class"] = c
    return idle


# ---------------------------------------------------------------- the site JSON's wind section

def wind_section(out, lat, lon, entry, span_m, raised, calm_only):
    """The wind section a site JSON carries: the point it was taken for, the dive area and entry shore
    facings, the swim out, the fetch, shore relation and class from each of the 16 compass points, the
    raises that moved a class, and the sectors of each class."""
    e = out.get("entry")
    rows = [{"from": r["from"], "bearing": r["bearing"], "fetch_km": r["fetch_km"],
             "capped": r["capped"], "relation": r["relation"]} for r in out["fetch"]]
    idle = classify(rows, raised, calm_only)
    return idle, {
        "extract_point": {"lat": lat, "lon": lon,
                          "entry": None if entry is None else {"lat": entry[0], "lon": entry[1]},
                          "shore_span_m": round(span_m), "max_fetch_km": out["max_fetch_km"],
                          "extracted": datetime.date.today().isoformat()},
        "shoreline": out["source"],
        "dive_area_faces": out["faces"],
        "entry_faces": None if e is None else e["faces"],
        "swim_out": None if e is None else {"bearing": e["bearing_to_dive"], "distance_m": e["distance_m"],
                                            "off_entry_faces": e["off_shore_normal"]},
        "calm_only": calm_only,
        "raised": {pt: raised[pt] for pt in POINTS if pt in raised},
        "fetch": rows,
        "sectors": sectors_of([r["class"] for r in rows]),
    }


def read_site(path):
    try:
        with open(path) as f:
            doc = json.load(f)
    except OSError as e:
        raise Refused(f"could not read --site {path}: {e}")
    except json.JSONDecodeError as e:
        raise Refused(f"could not parse JSON in {path}: {e}")
    if not all(isinstance(doc.get(k), (int, float)) for k in ("lat", "lon")):
        raise Refused(f"{path} has no lat and lon: the site JSON carries the dive area's coordinate, written when the site is created.")
    return doc


def write_site(path, doc):
    with open(path + ".part", "w") as f:
        f.write(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    os.replace(path + ".part", path)


def cmd_extract(a):
    """Every site given, each written into its own JSON. Every site is read and computed before any
    is written, so a refused one stops the run with nothing changed."""
    given = a.entry or a.boat or a.raise_ or a.calm_only or a.no_raise
    if given and len(a.site) > 1:
        sys.exit("--entry, --boat, --raise, --calm-only and --no-raise describe one site: give one --site with them.")
    try:
        new_raised = parse_raises(a.raise_)
    except Refused as e:
        sys.exit(str(e))
    jobs, refused = [], []
    for path in a.site:
        try:
            doc = read_site(path)
            old = doc.get("wind") if isinstance(doc.get("wind"), dict) else {}
            if a.entry:
                entry = tuple(a.entry)
            elif a.boat:
                entry = None
            elif isinstance(doc.get("wind"), dict) and "extract_point" in doc["wind"]:
                e = doc["wind"]["extract_point"].get("entry")
                entry = None if e is None else (e["lat"], e["lon"])
            else:
                raise Refused(f"{path} has no wind section yet: give the shore entry point as --entry LAT LON, "
                              f"or --boat for a boat site.")
            if a.raise_ or a.calm_only or a.no_raise:
                raised, calm_only = new_raised, a.calm_only
            else:
                raised, calm_only = dict(old.get("raised") or {}), bool(old.get("calm_only"))
            out = exposure(doc["lat"], doc["lon"], entry, a.max_fetch, a.shore_span)
            if out["faces"] is None or (entry and out["entry"]["faces"] is None):
                raise Refused(f"{path}: no shoreline inside the averaging span, so a shore facing is undetermined; "
                              f"check the coordinate")
            idle, wind = wind_section(out, doc["lat"], doc["lon"], entry, a.shore_span, raised, calm_only)
            if idle and a.raise_:
                raise Refused("a raise moves a direction up a class, never to its own or a lower one: " + "; ".join(idle))
            jobs.append((path, doc, entry, wind, idle))
        except Refused as e:
            refused.append(str(e) if str(e).startswith(path) else f"{path}: {e}")
    if refused:
        sys.exit("Nothing was written. Stop and report:\n  " + "\n  ".join(refused))
    for path, doc, entry, wind, idle in jobs:
        doc["wind"] = wind
        write_site(path, doc)
        w = doc["wind"]
        print(f"  wrote wind into {path}: dive area faces {w['dive_area_faces']}° ({_point(w['dive_area_faces'])})"
              + ("" if entry is None else f", entry faces {w['entry_faces']}° ({_point(w['entry_faces'])})"))
        print("    " + ", ".join(f"{c} {','.join(w['sectors'][c])}" for c in CLASSES if w["sectors"][c])
              + (", calm only" if w["calm_only"] else "")
              + ("" if not w["raised"] else ", raised " + ",".join(f"{k}={v}" for k, v in w["raised"].items())))
        for note in idle:
            print(f"    note: {note}; drop the raise with --no-raise and the others again with --raise")


def cmd_at(a):
    try:
        out = exposure(a.lat, a.lon, tuple(a.entry) if a.entry else None, a.max_fetch, a.shore_span)
    except Refused as e:
        sys.exit(str(e))
    if a.json:
        print(json.dumps(out, indent=2))
        return
    lat, lon, cap, faces = a.lat, a.lon, a.max_fetch, out["faces"]
    print(f"  requested                 {lat:.5f}, {lon:.5f}")
    print(f"  shoreline                 {out['source']}")
    print(f"  nearest                   shore {out['nearest_shore_m']} m away, toward {out['nearest_shore_bearing']}° ({_point(out['nearest_shore_bearing'])})")
    if faces is None:
        print("  dive area shore facing    undetermined: no shoreline inside the averaging span")
    else:
        print(f"  dive area shore facing    {faces}° ({_point(faces)}), the shore nearest the dive area, averaged over {out['shore_span_m']} m")
    if a.entry:
        e = out["entry"]
        ef = "undetermined" if e["faces"] is None else f"{e['faces']}° ({_point(e['faces'])})"
        print(f"  entry shore facing        {ef}, the shore at the entry point {e['point'][0]:.5f}, {e['point'][1]:.5f}, {e['shore_m']} m away")
        print(f"  swim out                  {e['bearing_to_dive']}° ({_point(e['bearing_to_dive'])}), {e['distance_m']} m to the dive area"
              + ("" if e["off_shore_normal"] is None else f", {e['off_shore_normal']}° off the entry shore's facing"))
    print()
    classify(out["fetch"], {}, False)
    print(f"  wind from          fetch     to the {'entry ' if a.entry else ''}shore   class, as measured")
    for r in out["fetch"]:
        f = f"over {cap:g} km" if r["capped"] else (f"{r['fetch_km'] * 1000:.0f} m" if r["fetch_km"] < 1 else f"{r['fetch_km']:.1f} km")
        print(f"  {r['from']:<4} {r['bearing']:>5.1f}°   {f:>12}     {r['relation'] or '':<14}{r['class']}")


def main():
    argv = sys.argv[1:]
    try:                                   # the older form, a bare coordinate, reads as `at`
        float(argv[0])
        argv = ["at"] + argv
    except (IndexError, ValueError):
        pass
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(q):
        q.add_argument("--max-fetch", type=float, default=MAX_FETCH_KM,
                       help=f"fetch cap and search radius, km (default {MAX_FETCH_KM})")
        q.add_argument("--shore-span", type=float, default=SHORE_SPAN_M,
                       help=f"metres of shoreline averaged for the shore normal (default {SHORE_SPAN_M})")

    q = sub.add_parser("at", help="the exposure at a coordinate, printed")
    q.add_argument("lat", type=float)
    q.add_argument("lon", type=float)
    q.add_argument("--entry", nargs=2, type=float, metavar=("LAT", "LON"),
                   help="shore entry point; reports its shore's facing and the swim out to the dive area")
    q.add_argument("--json", action="store_true", help="print the result as JSON")
    common(q)
    q.set_defaults(fn=cmd_at)

    q = sub.add_parser("extract", help="write the wind section into each site JSON")
    q.add_argument("--site", nargs="+", required=True, metavar="FILE")
    g = q.add_mutually_exclusive_group()
    g.add_argument("--entry", nargs=2, type=float, metavar=("LAT", "LON"),
                   help="the shore site's entry point, the Entry point coordinates row")
    g.add_argument("--boat", action="store_true", help="a boat site: the dive area alone")
    q.add_argument("--raise", dest="raise_", action="append", metavar="SECTOR=CLASS",
                   help="move a sector up a class by local knowledge, e.g. NE=bad or S-SW=short; replaces the recorded raises")
    q.add_argument("--calm-only", action="store_true", help="every direction Bad: the site is dived only in calm")
    q.add_argument("--no-raise", action="store_true", help="drop the recorded raises and calm only")
    common(q)
    q.set_defaults(fn=cmd_extract)

    a = p.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()

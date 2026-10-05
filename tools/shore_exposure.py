#!/usr/bin/env python3
"""Shoreline orientation and wind fetch at a dive site, from OpenStreetMap's coastline and HydroLAKES.

  shore_exposure.py LAT LON --entry ELAT ELON       site file, shore site: both shore facings, the swim out, the fetch
  shore_exposure.py LAT LON                         site file, boat site: the dive area shore facing and the fetch
  shore_exposure.py LAT LON ... --json              the same result as JSON

"""
import argparse
import json
import math
import mmap
import shutil
import struct
import sys
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

DB = Path(__file__).parent / "db"
R_KM = 6371.0
POINTS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
          "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]


def _cfg(key, default):
    """Read this tool's section of tool-config.json; missing file or key -> default."""
    try:
        with open(Path(__file__).resolve().parent.parent / "tool-config.json") as f:
            return json.load(f).get("shore_exposure", {}).get(key, default)
    except (OSError, ValueError):
        return default


MAX_FETCH_KM = _cfg("max_fetch_km", 30)
SHORE_SPAN_M = _cfg("shore_span_m", 250)
_email = _cfg("user_agent_email", None)
USER_AGENT = f"dive-planning ({_email})" if _email else "dive-planning"


# ---------------------------------------------------------------- shoreline datasets
# Two global polygon datasets, each one download kept under tools/db/ and fetched again whenever
# it is missing. The sea shoreline is OpenStreetMap's coastline as land polygons, cut into pieces
# on a roughly 1° grid so a search reads only the pieces near the site. Lakes are HydroLAKES,
# every lake of 10 ha or more, with islands as holes; the land polygons count a lake as land.

DATASETS = {
    "land": {"url": "https://osmdata.openstreetmap.de/download/land-polygons-split-4326.zip",
             "dir": DB / "land_polygons", "stem": "land_polygons", "parts": (".shp", ".shx")},
    "lakes": {"url": "https://data.hydrosheds.org/file/hydrolakes/HydroLAKES_polys_v10_shp.zip",
              "dir": DB / "hydrolakes", "stem": "HydroLAKES_polys_v10", "parts": (".shp", ".shx", ".dbf")},
}


def _files(name):
    d = DATASETS[name]
    return [d["dir"] / (d["stem"] + ext) for ext in d["parts"]]


def ensure(name):
    """The dataset's extracted files, downloading and unpacking the archive if any is missing."""
    d, files = DATASETS[name], _files(name)
    if all(f.exists() for f in files):
        return
    d["dir"].mkdir(parents=True, exist_ok=True)
    part = d["dir"] / "download.zip.part"
    print(f"{name} dataset missing; downloading {d['url']}", file=sys.stderr)
    req = urllib.request.Request(d["url"], headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=120) as r, open(part, "wb") as f:
            total = int(r.headers.get("Content-Length") or 0)
            done = step = 0
            while chunk := r.read(1 << 20):
                f.write(chunk)
                done += len(chunk)
                if done >= step:
                    print(f"  {done / 1e6:.0f} / {total / 1e6:.0f} MB", file=sys.stderr)
                    step += 100 << 20
    except (urllib.error.URLError, OSError) as e:
        part.unlink(missing_ok=True)
        sys.exit(f"{name} download failed: {getattr(e, 'reason', e)}; stop and report it")
    print("  unpacking", file=sys.stderr)
    with zipfile.ZipFile(part) as z:
        for member in z.namelist():
            for dest in files:
                if member.rsplit("/", 1)[-1] == dest.name:
                    tmp = dest.with_suffix(dest.suffix + ".part")
                    with z.open(member) as src, open(tmp, "wb") as out:
                        shutil.copyfileobj(src, out, 1 << 20)
                    tmp.rename(dest)
    part.unlink()
    missing = [f.name for f in files if not f.exists()]
    if missing:
        sys.exit(f"the {name} archive held no {', '.join(missing)}; its layout may have changed")


def polygons(name, lat, lon, km):
    """Every polygon in the dataset whose bounding box reaches within km of the point, as
    (record number, rings), each ring a list of (lon, lat). Longitudes are shifted by 360 where
    the search crosses the antimeridian, so every ring sits on the same side as the point."""
    ensure(name)
    shp_path, shx_path = _files(name)[:2]
    dlat = km / 111.32
    dlon = min(180.0, km / (111.32 * max(0.01, math.cos(math.radians(lat)))))
    s, n, w, e = lat - dlat, lat + dlat, lon - dlon, lon + dlon
    shifts = [0.0] + ([360.0] if w < -180 else []) + ([-360.0] if e > 180 else [])
    found = []
    with open(shx_path, "rb") as fx, open(shp_path, "rb") as fs:
        idx = fx.read()[100:]
        shp = mmap.mmap(fs.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            for rec, (off, _) in enumerate(struct.iter_unpack(">ii", idx)):
                pos = off * 2 + 8
                typ, x0, y0, x1, y1 = struct.unpack_from("<i4d", shp, pos)
                if typ != 5 or y1 < s or y0 > n:
                    continue
                shift = next((k for k in shifts if x1 + k >= w and x0 + k <= e), None)
                if shift is None:
                    continue
                nparts, npts = struct.unpack_from("<2i", shp, pos + 36)
                parts = struct.unpack_from(f"<{nparts}i", shp, pos + 44)
                xy = struct.unpack_from(f"<{2 * npts}d", shp, pos + 44 + 4 * nparts)
                bounds = list(parts) + [npts]
                found.append((rec, [[(xy[2 * i] + shift, xy[2 * i + 1]) for i in range(bounds[j], bounds[j + 1])]
                                    for j in range(nparts)]))
        finally:
            shp.close()
    return found


def lake_record(rec):
    """A HydroLAKES attribute row, by record number, as {field: text}."""
    with open(_files("lakes")[2], "rb") as f:
        head = f.read(32)
        hlen, rlen = struct.unpack_from("<HH", head, 8)
        fields, pos = [], 1
        while (desc := f.read(32))[0] != 0x0D:
            name = desc[:11].split(b"\0")[0].decode()
            fields.append((name, pos, desc[16]))
            pos += desc[16]
        f.seek(hlen + rec * rlen)
        row = f.read(rlen)
    return {k: row[p:p + w].decode("latin-1").strip() for k, p, w in fields}


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


def _inside(ring, x, y):
    c = False
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            c = not c
    return c


def _contains(rings, lon, lat):
    """Point in polygon, holes included: inside an odd number of the polygon's rings."""
    return sum(_inside(r, lon, lat) for r in rings) % 2 == 1


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


# ---------------------------------------------------------------- command

def exposure(a):
    lat, lon, cap = a.lat, a.lon, a.max_fetch
    proj = _proj(lat, lon)
    lake = None
    land = polygons("land", lat, lon, cap)
    if any(_contains(rings, lon, lat) for _, rings in land):
        lake = next(((rec, rings) for rec, rings in polygons("lakes", lat, lon, 0) if _contains(rings, lon, lat)), None)
        if lake is None:
            sys.exit("the coordinate sits on land, and inside no HydroLAKES lake (10 ha or more); walk it toward the water")

    if lake:
        info = lake_record(lake[0])
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
        sys.exit(f"no mapped shoreline within {cap:g} km of this coordinate")

    dist, q = _nearest(segs)
    faces = _shore_normal(facing_segs, q, max(a.shore_span / 1000, dist))
    entry_faces = None
    if a.entry:
        edist, eq = _nearest_to(segs, proj((a.entry[1], a.entry[0])))
        entry_faces = _shore_normal(facing_segs, eq, a.shore_span / 1000)
    ref = entry_faces if a.entry else faces
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
        "shore_span_m": round(max(a.shore_span, dist * 1000)),
        "max_fetch_km": cap,
        "fetch": rows,
    }
    if a.entry:
        elat, elon = a.entry
        eb = _initial_bearing(elat, elon, lat, lon)
        out["entry"] = {"point": [elat, elon], "shore_m": round(edist * 1000),
                        "faces": None if entry_faces is None else round(entry_faces),
                        "bearing_to_dive": round(eb),
                        "distance_m": round(_km(elat, elon, lat, lon) * 1000),
                        "off_shore_normal": None if entry_faces is None else round(_angle(eb, entry_faces))}

    if a.json:
        print(json.dumps(out, indent=2))
        return
    print(f"  requested                 {lat:.5f}, {lon:.5f}")
    print(f"  shoreline                 {source}")
    print(f"  nearest                   shore {out['nearest_shore_m']} m away, toward {out['nearest_shore_bearing']}° ({_point(out['nearest_shore_bearing'])})")
    if faces is None:
        print("  dive area shore facing    undetermined: no shoreline inside the averaging span")
    else:
        print(f"  dive area shore facing    {out['faces']}° ({_point(faces)}), the shore nearest the dive area, averaged over {out['shore_span_m']} m")
    if a.entry:
        e = out["entry"]
        ef = "undetermined" if e["faces"] is None else f"{e['faces']}° ({_point(e['faces'])})"
        print(f"  entry shore facing        {ef}, the shore at the entry point {e['point'][0]:.5f}, {e['point'][1]:.5f}, {e['shore_m']} m away")
        print(f"  swim out                  {e['bearing_to_dive']}° ({_point(e['bearing_to_dive'])}), {e['distance_m']} m to the dive area"
              + ("" if e["off_shore_normal"] is None else f", {e['off_shore_normal']}° off the entry shore's facing"))
    print()
    print(f"  wind from          fetch     to the {'entry ' if a.entry else ''}shore")
    for r in rows:
        f = f"over {cap:g} km" if r["capped"] else (f"{r['fetch_km'] * 1000:.0f} m" if r["fetch_km"] < 1 else f"{r['fetch_km']:.1f} km")
        print(f"  {r['from']:<4} {r['bearing']:>5.1f}°   {f:>12}     {r['relation'] or ''}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("lat", type=float)
    p.add_argument("lon", type=float)
    p.add_argument("--entry", nargs=2, type=float, metavar=("LAT", "LON"),
                   help="shore entry point; reports the bearing from it to the dive area")
    p.add_argument("--max-fetch", type=float, default=MAX_FETCH_KM,
                   help=f"fetch cap and search radius, km (default {MAX_FETCH_KM})")
    p.add_argument("--shore-span", type=float, default=SHORE_SPAN_M,
                   help=f"metres of shoreline averaged for the shore normal (default {SHORE_SPAN_M})")
    p.add_argument("--json", action="store_true", help="print the result as JSON")
    exposure(p.parse_args())


if __name__ == "__main__":
    main()

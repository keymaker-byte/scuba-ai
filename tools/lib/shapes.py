"""Shoreline shapes shared by shore_exposure.py and the depth tool: OpenStreetMap's land polygons
and HydroLAKES, each one download kept under tools/db/ and fetched again whenever missing, read
near a point, with a point-in-polygon test."""
import math
import mmap
import shutil
import struct
import sys
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

DB = Path(__file__).resolve().parent.parent / "db"
USER_AGENT = "dive-planning"  # a tool sets its own, with its contact address


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


_INDEX = {}         # name -> (mmap, file, boxes by record, records by 1-degree latitude band)
_RINGS = {}         # (name, record) -> rings, the most recent ones read
RING_CAP = 4000


def _index(name):
    """Every record's bounding box, read once per process from the shapefile, with the records
    bucketed by each degree of latitude their box spans."""
    if name not in _INDEX:
        ensure(name)
        shp_path, shx_path = _files(name)[:2]
        with open(shx_path, "rb") as fx:
            idx = fx.read()[100:]
        fs = open(shp_path, "rb")
        shp = mmap.mmap(fs.fileno(), 0, access=mmap.ACCESS_READ)
        boxes, bands = [], {}
        for rec, (off, _) in enumerate(struct.iter_unpack(">ii", idx)):
            pos = off * 2 + 8
            typ, x0, y0, x1, y1 = struct.unpack_from("<i4d", shp, pos)
            boxes.append((pos, typ, x0, y0, x1, y1))
            if typ == 5:
                for k in range(math.floor(y0), math.floor(y1) + 1):
                    bands.setdefault(k, []).append(rec)
        _INDEX[name] = (shp, fs, boxes, bands)
    return _INDEX[name]


def _rings(name, rec, shp, pos):
    key = (name, rec)
    got = _RINGS.get(key)
    if got is None:
        nparts, npts = struct.unpack_from("<2i", shp, pos + 36)
        parts = struct.unpack_from(f"<{nparts}i", shp, pos + 44)
        xy = struct.unpack_from(f"<{2 * npts}d", shp, pos + 44 + 4 * nparts)
        bounds = list(parts) + [npts]
        got = [[(xy[2 * i], xy[2 * i + 1]) for i in range(bounds[j], bounds[j + 1])] for j in range(nparts)]
        if len(_RINGS) >= RING_CAP:
            del _RINGS[next(iter(_RINGS))]
        _RINGS[key] = got
    return got


def polygons(name, lat, lon, km):
    """Every polygon in the dataset whose bounding box reaches within km of the point, as
    (record number, rings), each ring a list of (lon, lat), in record order. Longitudes are shifted
    by 360 where the search crosses the antimeridian, so every ring sits on the same side as the
    point."""
    shp, _, boxes, bands = _index(name)
    dlat = km / 111.32
    dlon = min(180.0, km / (111.32 * max(0.01, math.cos(math.radians(lat)))))
    s, n, w, e = lat - dlat, lat + dlat, lon - dlon, lon + dlon
    shifts = [0.0] + ([360.0] if w < -180 else []) + ([-360.0] if e > 180 else [])
    recs = sorted({r for k in range(math.floor(s), math.floor(n) + 1) for r in bands.get(k, ())})
    found = []
    for rec in recs:
        pos, typ, x0, y0, x1, y1 = boxes[rec]
        if typ != 5 or y1 < s or y0 > n:
            continue
        shift = next((k for k in shifts if x1 + k >= w and x0 + k <= e), None)
        if shift is None:
            continue
        rings = _rings(name, rec, shp, pos)
        found.append((rec, rings if shift == 0.0 else [[(x + shift, y) for x, y in r] for r in rings]))
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


def inside(ring, x, y):
    c = False
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            c = not c
    return c


def contains(rings, lon, lat):
    """Point in polygon, holes included: inside an odd number of the polygon's rings."""
    return sum(inside(r, lon, lat) for r in rings) % 2 == 1


def crossings(name, S, W, N, E, lats):
    """For each latitude, the sorted longitudes between W and E where it crosses the dataset's
    outlines inside the box: a point lies inside the shapes where an odd number of crossings sit
    west of it. The land polygons come cut into pieces whose cuts run through land, and a cut
    crosses twice at one longitude, which leaves the count right."""
    lat0, lon0 = (S + N) / 2, (W + E) / 2
    km = math.hypot((N - S) * 111.32, (E - W) * 111.32 * math.cos(math.radians(lat0))) / 2 + 2
    band = 0.01
    edges, buckets = [], {}
    for _, rings in polygons(name, lat0, lon0, km):
        for r in rings:
            for (ax, ay), (bx, by) in zip(r, r[1:] + r[:1]):
                if ay == by or max(ay, by) < S or min(ay, by) > N:
                    continue
                edges.append((ax, ay, bx, by))
                for k in range(int(min(ay, by) // band), int(max(ay, by) // band) + 1):
                    buckets.setdefault(k, []).append(len(edges) - 1)
    out = []
    for lat in lats:
        xs = []
        for i in buckets.get(int(lat // band), ()):
            ax, ay, bx, by = edges[i]
            if (ay > lat) != (by > lat):
                xs.append(ax + (lat - ay) * (bx - ax) / (by - ay))
        xs.sort()
        # crossings west of the box decide only whether its west edge starts on land
        west = sum(1 for x in xs if x < W)
        inner = [x for x in xs if W <= x <= E]
        out.append(([W] if west % 2 else []) + inner)
    return out

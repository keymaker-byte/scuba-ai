"""Shoreline shapes shared by shore_exposure.py and ncei_depth.py: OpenStreetMap's land polygons
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


def inside(ring, x, y):
    c = False
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            c = not c
    return c


def contains(rings, lon, lat):
    """Point in polygon, holes included: inside an odd number of the polygon's rings."""
    return sum(inside(r, lon, lat) for r in rings) % 2 == 1

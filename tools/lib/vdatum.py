"""NAVD 88's height above MLLW at a point, computed on this machine from NOAA VDatum's own
transformation grids: the same chain VDatum's conversion service runs, reproduced.

The grids come from VDatum's full package, `tools/db/vdatum/vdatum_all_<date>.zip`. Each
tidal sub-region VDatum defines is extracted from it the first time a point inside it is asked
for, into `tools/db/vdatum/<sub-region>/`: its `tss` and `mllw` grids, and the two geoid models
the chain runs through, cut to the sub-region's own box. After that a point needs no zip and no
network.

The chain, for a sub-region whose tidal grids are referenced to IGS14 (every Washington
sub-region): a point at NAVD 88 zero lies GEOID18's height above the NAD83(2011) ellipsoid;
HTDP's frame transformation carries it to the IGS14 ellipsoid at EPOCH; xGEOID20B places it
above IGS14's gravimetric geoid, where the sub-region's `tss` grid is mean sea level's
reference; and the `mllw` grid sets MLLW below mean sea level. NAVD 88 above MLLW is that
height plus `tss` minus `mllw`. Each grid is read bilinearly, and a corner VDatum holds no
value for leaves the point without an answer, as in VDatum.
"""
import array
import glob
import math
import os
import re
import shutil
import struct
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


DB = os.path.join(ROOT, "tools", "db", "vdatum")


ZIP_GLOB = "vdatum_all_*.zip"   # VDatum's full package, newest by its date


DOWNLOAD_PAGE = "https://vdatum.noaa.gov/download.php"


INDEX = ("tidal_area.inf", "tidal_area.dat")   # every sub-region, its box and its polygons


GEOID = ("geoid18", "g2018")      # NAVD 88 above the NAD83(2011) ellipsoid
GRAVIMETRIC = ("xgeoid20b", "")   # IGS14's gravimetric geoid, the tss grids' reference


FRAME = "IGS14"   # the frame the sub-regions this chain is proven for are referenced to


EPOCH = 2026.0    # HTDP's date for NAD83(2011) to IGS14; the result moves 1.4 mm a year with it


NULL = -87.8888   # VDatum's own test: a grid value at or below this is no value


MARGIN = 2        # geoid cells kept outside a sub-region's box when it is cut


# HTDP's 14 parameters from ITRF96 to each frame, as VDatum's own HTDP class holds them:
# translations (m), their rates (m/yr), rotations (rad), their rates (rad/yr), scale and its
# rate (per yr), and the reference epoch.
HTDP = {
    "NAD83": (0.991, -1.9072, -0.5129, 0.0, 0.0, 0.0,
              1.2503344835814934e-07, 4.678452022707023e-08, 5.6529275217371896e-08,
              2.579208783502731e-10, -3.5987719548760855e-09, -1.5320112323061339e-10,
              0.0, 0.0, 1997.0),
    "IGS14": (-0.0143, 0.00201, 0.02867, -7.9e-04, 6.0e-04, 0.00144,
              -1.4533744532301669e-09, 2.0380112712801564e-09, 1.5375381082707823e-09,
              -6.53044028454545e-11, 7.340079131998375e-11, 9.565373928291144e-11,
              -3.6891e-10, 7.201e-11, 2010.0),
}


# GRS 80, the ellipsoid of both frames.
A, F = 6378137.0, 1 / 298.257222101
E2 = F * (2 - F)


def _fail(msg):
    sys.exit(f"VDatum grids: {msg}")


# --- the package ---------------------------------------------------------------------------

def _zip():
    """The newest VDatum package in tools/db/vdatum/, opened; a stop when there is none."""
    found = sorted(glob.glob(os.path.join(DB, ZIP_GLOB)))
    if not found:
        _fail(f"no {ZIP_GLOB} in {os.path.relpath(DB, ROOT)}/ to extract from. VDatum's download page "
              f"refuses automated clients, so the package is downloaded by hand: the full package "
              f"(\"vdatum_all\") from {DOWNLOAD_PAGE}, saved unopened into {os.path.relpath(DB, ROOT)}/.")
    try:
        return zipfile.ZipFile(found[-1])
    except (OSError, zipfile.BadZipFile) as e:
        _fail(f"{os.path.relpath(found[-1], ROOT)} could not be opened as a zip ({e}).")


def _member(zf, name):
    """A member of the package by its path below the package's top folder."""
    for pre in ("vdatum/", ""):
        try:
            return zf.getinfo(pre + name)
        except KeyError:
            pass
    _fail(f"{name} is not in {os.path.basename(zf.filename)}.")


def _copy(zf, name, dest):
    """Extract one member to dest, whole or not at all."""
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with zf.open(_member(zf, name)) as src, open(dest + ".part", "wb") as out:
        shutil.copyfileobj(src, out, 1 << 20)
    os.replace(dest + ".part", dest)


def _header(raw):
    lat0, lon0, dlat, dlon, rows, cols = struct.unpack(">4d2i", raw[:40])
    return lat0, lon0 % 360, dlat, dlon, rows, cols


def _cut(zf, name, box, dest):
    """Extract the part of a gridded member covering box (S, W, N, E in degrees, W and E
    0 to 360) with MARGIN cells around it, as a GTX of its own."""
    S, W, N, E = box
    with zf.open(_member(zf, name)) as src:
        lat0, lon0, dlat, dlon, rows, cols = _header(src.read(40))
        r0 = max(0, int((S - lat0) / dlat) - MARGIN)
        r1 = min(rows - 1, int(math.ceil((N - lat0) / dlat)) + MARGIN)
        c0 = max(0, int((W - lon0) / dlon) - MARGIN)
        c1 = min(cols - 1, int(math.ceil((E - lon0) / dlon)) + MARGIN)
        if r0 > r1 or c0 > c1:
            _fail(f"{name} does not cover {box}.")
        width = cols * 4
        src.read(r0 * width)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest + ".part", "wb") as out:
            out.write(struct.pack(">4d2i", lat0 + r0 * dlat, lon0 + c0 * dlon, dlat, dlon,
                                  r1 - r0 + 1, c1 - c0 + 1))
            for _ in range(r1 - r0 + 1):
                row = src.read(width)
                if len(row) != width:
                    _fail(f"{name} ended early.")
                out.write(row[c0 * 4:(c1 + 1) * 4])
    os.replace(dest + ".part", dest)


def _covering(zf, folder, prefix, box):
    """The grid of a core model that covers box: the first, in the package's own order, that
    covers all of it, or else the one covering most of it, whose edge then bounds the
    sub-region's answers."""
    names = sorted(n for n in zf.namelist()
                   if re.fullmatch(rf"(vdatum/)?core/{folder}/{prefix}[^/]*\.gtx", n, re.I))
    S, W, N, E = box
    best, most = None, 0.0
    for n in names:
        with zf.open(n) as f:
            lat0, lon0, dlat, dlon, rows, cols = _header(f.read(40))
        n_, e_ = lat0 + (rows - 1) * dlat, lon0 + (cols - 1) * dlon
        if lat0 <= S and N <= n_ and lon0 <= W and E <= e_:
            return n.split("vdatum/", 1)[-1]
        area = max(0.0, min(N, n_) - max(S, lat0)) * max(0.0, min(E, e_) - max(W, lon0))
        if area > most:
            best, most = n, area
    if best is None:
        _fail(f"no {folder} grid in the package reaches {box}.")
    return best.split("vdatum/", 1)[-1]


# --- the sub-regions -----------------------------------------------------------------------

_index = None


def index():
    """Every tidal sub-region VDatum defines, in VDatum's own order: [{name, horz, box,
    polygons: [(type, lats, lons)]}]. The index files are extracted from the package once."""
    global _index
    if _index is not None:
        return _index
    paths = [os.path.join(DB, n) for n in INDEX]
    if not all(os.path.exists(p) for p in paths):
        with _zip() as zf:
            for n, p in zip(INDEX, paths):
                _copy(zf, n, p)
    with open(paths[0]) as f:
        props = dict(line.rstrip("\n").split("=", 1) for line in f if "=" in line and not line.startswith("#"))
    with open(paths[1], "rb") as f:
        dat = f.read()
    out = []
    for name in filter(None, props["grids"].split(";")):
        polys = []
        for rec in filter(None, props[f"{name}.polygons"].split(";;")):
            off, kind, count = (int(x) for x in rec.split(";")[:3])
            pts = struct.unpack(f">{2 * count}i", dat[off:off + 8 * count])
            polys.append((kind, [v / 1e6 for v in pts[0::2]], [v / 1e6 for v in pts[1::2]]))
        out.append({"name": name, "horz": props.get(f"{name}.horz", ""),
                    "box": tuple(float(props[f"{name}.{k}"]) for k in ("minlat", "minlon", "maxlat", "maxlon")),
                    "polygons": polys})
    _index = out
    return out


def _inside(lat, lon, lats, lons):
    hit, j = False, len(lats) - 1
    for i in range(len(lats)):
        if (lats[i] > lat) != (lats[j] > lat) and \
                lon < (lons[j] - lons[i]) * (lat - lats[i]) / (lats[j] - lats[i]) + lons[i]:
            hit = not hit
        j = i
    return hit


def region_at(lat, lon):
    """The sub-region VDatum reads a point in, and the type of its polygon there (0 tidal,
    1 non-tidal, 2 a priority area), or (None, None). As VDatum picks it: the highest type
    among the sub-regions whose polygons hold the point, the first in VDatum's order on a tie."""
    lon %= 360
    best, score = None, -1
    for g in index():
        S, W, N, E = g["box"]
        if not (S <= lat <= N and W <= lon <= E):
            continue
        kinds = [k for k, la, lo in g["polygons"] if _inside(lat, lon, la, lo)]
        if kinds and max(kinds) > score:
            best, score = g, max(kinds)
    return (best, score) if best else (None, None)


# --- the grids -----------------------------------------------------------------------------

class _Grid:
    """A GTX grid held in memory."""

    def __init__(self, path):
        with open(path, "rb") as f:
            raw = f.read()
        self.lat0, self.lon0, self.dlat, self.dlon, self.rows, self.cols = _header(raw)
        self.v = array.array("f")
        self.v.frombytes(raw[40:40 + 4 * self.rows * self.cols])
        if sys.byteorder == "little":
            self.v.byteswap()
        self.name = os.path.basename(path)

    def at(self, lat, lon):
        """Bilinear value at a point; None outside the grid or beside a cell with no value."""
        y = (lat - self.lat0) / self.dlat
        x = ((lon % 360) - self.lon0) / self.dlon
        r, c = math.floor(y), math.floor(x)
        if not (0 <= r < self.rows - 1 and 0 <= c < self.cols - 1):
            return None
        k = r * self.cols + c
        q = self.v[k], self.v[k + 1], self.v[k + self.cols], self.v[k + self.cols + 1]
        if min(q) <= NULL:
            return None
        fy, fx = y - r, x - c
        return (q[0] * (1 - fx) + q[1] * fx) * (1 - fy) + (q[2] * (1 - fx) + q[3] * fx) * fy


_grids = {}


def _files(name):
    d = os.path.join(DB, name)
    return {"tss": os.path.join(d, f"{name}_tss.gtx"), "mllw": os.path.join(d, f"{name}_mllw.gtx"),
            "geoid": os.path.join(d, f"{GEOID[0]}.gtx"), "grav": os.path.join(d, f"{GRAVIMETRIC[0]}.gtx")}


def extract(g):
    """Put a sub-region's grids in tools/db/vdatum/<name>/ from the package, where missing."""
    files = _files(g["name"])
    if all(os.path.exists(p) for p in files.values()):
        return files
    if g["horz"] != FRAME:
        _fail(f"{g['name']} is referenced to {g['horz'] or 'an unstated frame'}; this chain is "
              f"built for sub-regions referenced to {FRAME}.")
    S, W, N, E = g["box"]
    with _zip() as zf:
        for kind in ("tss", "mllw"):
            if not os.path.exists(files[kind]):
                _copy(zf, f"{g['name']}/{g['name']}_{kind}.gtx", files[kind])
        for kind, (folder, prefix) in (("geoid", GEOID), ("grav", GRAVIMETRIC)):
            if not os.path.exists(files[kind]):
                _cut(zf, _covering(zf, folder, prefix, (S, W, N, E)), (S, W, N, E), files[kind])
    return files


def _load(g):
    if g["name"] not in _grids:
        _grids[g["name"]] = {k: _Grid(p) for k, p in extract(g).items()}
    return _grids[g["name"]]


# --- NAD83(2011) to IGS14 --------------------------------------------------------------------

def _xyz(lat, lon, h):
    la, lo = math.radians(lat), math.radians(lon)
    n = A / math.sqrt(1 - E2 * math.sin(la) ** 2)
    return [(n + h) * math.cos(la) * math.cos(lo), (n + h) * math.cos(la) * math.sin(lo),
            (n * (1 - E2) + h) * math.sin(la)]


def _height(x, y, z):
    p = math.hypot(x, y)
    la = math.atan2(z, p * (1 - E2))
    for _ in range(8):
        n = A / math.sqrt(1 - E2 * math.sin(la) ** 2)
        h = p / math.cos(la) - n
        la = math.atan2(z, p * (1 - E2 * n / (n + h)))
    return h


def _params(p, t):
    dt = t - p[14]
    return [p[i] + p[i + 3] * dt for i in range(3)], [p[6 + i] + p[9 + i] * dt for i in range(3)], p[12] + p[13] * dt


def _from96(p, t, v):
    (tx, ty, tz), (rx, ry, rz), s = _params(p, t)
    x, y, z = v
    d = 1 + s
    return [tx + d * x + rz * y - ry * z, ty - rz * x + d * y + rx * z, tz + ry * x - rx * y + d * z]


def _to96(p, t, v):
    (tx, ty, tz), (rx, ry, rz), s = _params(p, t)
    x, y, z = v
    d = 1 - s
    return [-tx + d * x - rz * y + ry * z, -ty + rz * x + d * y - rx * z, -tz - ry * x + rx * y + d * z]


def frame_shift(lat, lon, h):
    """The IGS14 ellipsoid height minus the NAD83(2011) one, at a point and height, at EPOCH."""
    return _height(*_from96(HTDP[FRAME], EPOCH, _to96(HTDP["NAD83"], EPOCH, _xyz(lat, lon, h)))) - h


# --- the answer ------------------------------------------------------------------------------

def navd88_above_mllw(lat, lon):
    """(NAVD 88's height above MLLW in m, the sub-region) at a point, or (None, why)."""
    g, kind = region_at(lat, lon)
    if g is None:
        return None, "outside every VDatum tidal sub-region"
    if kind == 1:
        return None, f"in a non-tidal area of {g['name']}"
    gr = _load(g)
    vals = {k: gr[k].at(lat, lon) for k in ("tss", "mllw", "geoid", "grav")}
    if vals["tss"] is None or vals["mllw"] is None:
        return None, f"{g['name']}'s tidal grids hold no value here: the land side of their shoreline"
    if vals["geoid"] is None or vals["grav"] is None:
        return None, f"past the edge of {GEOID[0] if vals['geoid'] is None else GRAVIMETRIC[0]}, outside {g['name']}'s reach"
    h = vals["geoid"]
    above_geoid = h + frame_shift(lat, lon, h) - vals["grav"]
    return above_geoid + vals["tss"] - vals["mllw"], g["name"]


# Answers VDatum's own conversion service gave in November 2026, one or more in each
# Washington sub-region that holds a dive site; selftest() reproduces them.
SELFTEST = [
    (47.6621, -122.4417, 0.745), (47.276092, -122.650053, 1.097), (47.445874, -123.113249, 0.929),
    (47.80441, -122.39792, 0.701), (48.15683, -122.67062, 0.290), (48.1356, -122.759, 0.276),
    (48.49216, -122.70335, 0.036), (48.5124, -123.1472, 0.119), (48.6388, -122.78, 0.313),
    (48.140383, -123.430747, 0.146), (48.32717, -124.46778, 0.240), (48.1183, -122.491, 0.742),
]
SELFTEST_TOL = 0.003   # VDatum answers to the millimetre; the rest is its epoch's drift


def selftest():
    """Compare the chain with VDatum's own answers; True when every one is within SELFTEST_TOL."""
    worst, ok = 0.0, True
    for lat, lon, want in SELFTEST:
        got, region = navd88_above_mllw(lat, lon)
        if got is None:
            print(f"  {lat}, {lon}: no answer ({region})")
            ok = False
            continue
        d = got - want
        worst = max(worst, abs(d))
        print(f"  {lat:.5f}, {lon:.5f}  {region:18s} {got:6.3f}  VDatum {want:6.3f}  {d:+.4f}")
    ok = ok and worst <= SELFTEST_TOL
    print(f"{'passed' if ok else 'FAILED'}: worst {worst:.4f} m against {SELFTEST_TOL} m")
    return ok

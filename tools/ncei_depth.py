#!/usr/bin/env python3
"""Seabed depth at a coordinate from NOAA NCEI's ninth arc-second coastal DEM, read from
tiles kept on this machine.

  ncei_depth.py LAT LON                     depth below NAVD88 (~mean sea level)
  ncei_depth.py LAT LON --mllw              also below MLLW, the site file figure
  ncei_depth.py LAT LON --mllw --region R   pick the VDatum region explicitly
  ncei_depth.py LAT LON --verify            compare with NCEI's live service
  ncei_depth.py --fetch S W N E             download every tile touching a box, ahead of time
  ncei_depth.py --export-map                the map viewer's depth layer, from every cached tile
"""
import argparse
import array
import http.client
import json
import math
import os
import re
import struct
import sys
import urllib.error
import urllib.parse
import urllib.request
import zlib
from concurrent.futures import ThreadPoolExecutor
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import shapes  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "tools", "db", "ncei_depth")
INDEX = os.path.join(DB, "tiles.json")
OFFSETS = os.path.join(DB, "vdatum.json")
LIST_URL = ("https://chs.coast.noaa.gov/htdata/raster2/elevation/"
            "NCEI_ninth_Topobathy_2014_8483/urllist8483.txt")
LIVE_URL = "https://gis.ngdc.noaa.gov/arcgis/rest/services/DEM_mosaics/DEM_all/ImageServer/identify"
VDATUM_URL = "https://vdatum.noaa.gov/vdatumweb/api/convert"
TILE_DEG = 0.25     # a tile's side
DATUM = "NAVD 88"   # the ninth arc-second DEM's vertical datum
REUSE_M = 200       # an offset VDatum gave within this distance answers for the point


def _cfg(key, default=None):
    """Read this tool's section of tool-config.json; missing file or key -> default."""
    try:
        with open(os.path.join(ROOT, "tool-config.json")) as f:
            return json.load(f).get("ncei_depth", {}).get(key, default)
    except (OSError, ValueError):
        return default


def _user_agent():
    """Contact email for the User-Agent comes from tool-config.json (ncei_depth.user_agent_email)."""
    email = _cfg("user_agent_email")
    return f"dive-planning ({email})" if email else "dive-planning"


UA = _user_agent()
shapes.USER_AGENT = UA


# --- downloads ----------------------------------------------------------------------------

def _open(url, timeout=60):
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=timeout)


def _get_json(url, what):
    try:
        with _open(url) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"{what}: HTTP {e.code} for {url}")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        sys.exit(f"{what}: unreachable ({getattr(e, 'reason', e)}) for {url}")
    except ValueError:
        sys.exit(f"{what}: an answer that is not JSON for {url}")


def _save(path, doc):
    os.makedirs(DB, exist_ok=True)
    with open(path + ".part", "w") as f:
        json.dump(doc, f, separators=(",", ":"))
    os.replace(path + ".part", path)


def tile_index():
    """NOAA's list of ninth arc-second tiles: {"N,W": [url, ...]} keyed by a tile's north
    and west edges. Downloaded once."""
    if os.path.exists(INDEX):
        with open(INDEX) as f:
            return json.load(f)
    try:
        with _open(LIST_URL) as r:
            text = r.read().decode()
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        sys.exit(f"NOAA tile list: download failed ({getattr(e, 'reason', e)}) for {LIST_URL}. Nothing was cached.")
    tiles = {}
    for url in text.split():
        m = re.search(r"ncei19_n(\d+)x(\d+)_w(\d+)x(\d+)_(\d{4})v(\d+)\.tif$", url, re.I)
        if m:
            key = f"{int(m[1]) + int(m[2]) / 100:g},{-(int(m[3]) + int(m[4]) / 100):g}"
            tiles.setdefault(key, []).append(url)
    if not tiles:
        sys.exit(f"NOAA tile list: no tiles in the answer from {LIST_URL}. Nothing was cached.")
    doc = {"fetched": date.today().isoformat(), "tiles": tiles}
    _save(INDEX, doc)
    return doc


def _latest(urls):
    """Of a tile's editions, the newest: (url, local path)."""
    def edition(u):
        m = re.search(r"_(\d{4})v(\d+)\.tif$", u, re.I)
        return int(m[1]), int(m[2])
    url = max(urls, key=edition)
    return url, os.path.join(DB, url.rsplit("/", 1)[1])


def tile_for(lat, lon):
    """The local path of the tile covering a point, downloaded when missing."""
    idx = tile_index()
    key = f"{math.ceil(lat / TILE_DEG) * TILE_DEG:g},{math.floor(lon / TILE_DEG) * TILE_DEG:g}"
    urls = idx["tiles"].get(key)
    if not urls:
        sys.exit(f"No ninth arc-second DEM tile covers {lat}, {lon} (NOAA's list as fetched {idx['fetched']}). "
                 "The point is outside the coastal DEM. Delete tools/db/ncei_depth/tiles.json to list again.")
    url, path = _latest(urls)
    if not os.path.exists(path):
        _download(url, path)
    return path


def fetch(boxes, workers):
    """Download every tile touching any of the boxes (south, west, north, east), several at
    a time. Tiles already here are skipped, so a stopped run picks up where it left off."""
    want = {}
    for key, urls in tile_index()["tiles"].items():
        n, w = map(float, key.split(","))
        if any(n - TILE_DEG < bn and n > bs and w < be and w + TILE_DEG > bw for bs, bw, bn, be in boxes):
            url, path = _latest(urls)
            want[path] = url
    todo = sorted((u, p) for p, u in want.items() if not os.path.exists(p))
    print(f"{len(want)} tiles touch the box, {len(want) - len(todo)} already here, {len(todo)} to download", flush=True)
    failed = 0

    def one(job):
        try:
            _download(*job, quiet=True)
            return job[1], None
        except SystemExit as e:
            return job[1], str(e)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for i, (path, err) in enumerate(pool.map(one, todo), 1):
            failed += err is not None
            print(f"  {i}/{len(todo)}  {os.path.basename(path)}: " + (err or f"{os.path.getsize(path) / 1e6:.0f} MB"), flush=True)
    print(f"done; {len(todo) - failed} downloaded, {failed} failed.")
    return failed


def _download(url, path, quiet=False):
    os.makedirs(DB, exist_ok=True)
    part = path + ".part"
    try:
        with _open(url, timeout=120) as r, open(part, "wb") as f:
            size = int(r.headers.get("Content-Length") or 0)
            if not quiet:
                print(f"downloading {os.path.basename(path)} from NOAA, {size / 1e6:.0f} MB ...", file=sys.stderr, flush=True)
            got, shown, quiet = 0, 0, quiet or not sys.stderr.isatty()
            while chunk := r.read(1 << 20):
                f.write(chunk)
                got += len(chunk)
                if not quiet and size and got * 20 // size > shown:
                    shown = got * 20 // size
                    print(f"\r  {shown * 5}%", end="", file=sys.stderr, flush=True)
            if not quiet:
                print(file=sys.stderr)
        if size and got != size:
            raise OSError(f"{got} of {size} bytes arrived")
    except (urllib.error.URLError, http.client.HTTPException, TimeoutError, OSError) as e:
        if os.path.exists(part):
            os.remove(part)
        sys.exit(f"NOAA DEM tile: download failed ({getattr(e, 'reason', e)}) for {url}. Nothing was cached.")
    os.replace(part, path)


# --- GeoTIFF reader: one float band in tiles, deflate or LZW ------------------------------

def _lzw(data):
    """Decode one TIFF LZW block (MSB-first codes, early change)."""
    bits = int.from_bytes(data, "big")
    total = len(data) * 8
    table = [bytes([i]) for i in range(256)] + [b"", b""]
    out = bytearray()
    pos, width, prev = 0, 9, None
    while pos + width <= total:
        code = (bits >> (total - pos - width)) & ((1 << width) - 1)
        pos += width
        if code == 257:
            break
        if code == 256:
            table, width, prev = table[:258], 9, None
            continue
        if prev is None:
            entry = table[code]
        else:
            entry = table[code] if code < len(table) else prev + prev[:1]
            table.append(prev + entry[:1])
        out += entry
        prev = entry
        if len(table) >= (1 << width) - 1 and width < 12:
            width += 1
    return bytes(out)


class Tile:
    TYPES = {1: "B", 2: "s", 3: "H", 4: "I", 11: "f", 12: "d"}

    def __init__(self, path):
        self.path, self.name = path, os.path.basename(path)[:-4]
        self.f = open(path, "rb")
        head = self.f.read(8)
        self.bo = {b"II": "<", b"MM": ">"}.get(head[:2])
        if self.bo is None or struct.unpack(self.bo + "H", head[2:4])[0] != 42:
            self._bad("it is not a classic TIFF")
        t = self._ifd(struct.unpack(self.bo + "I", head[4:8])[0])
        self.w, self.h = t[256][0], t[257][0]
        self.comp, self.pred = t.get(259, (1,))[0], t.get(317, (1,))[0]
        if (t.get(258, (0,))[0], t.get(339, (1,))[0], t.get(277, (1,))[0]) != (32, 3, 1) or 322 not in t \
                or self.comp not in (1, 5, 8, 32946) or self.pred not in (1, 3):
            self._bad("expected one 32-bit float band in tiles, uncompressed, LZW or deflate")
        self.tw, self.th = t[322][0], t[323][0]
        self.offs, self.counts = t[324], t[325]
        self.sx, self.sy = t[33550][0], t[33550][1]
        tie = t[33922]
        self.x0, self.y0 = tie[3] - tie[0] * self.sx, tie[4] + tie[1] * self.sy  # the grid's north-west corner
        nodata = t.get(42113)
        self.nodata = float(nodata[0].split(b"\0")[0]) if nodata else None
        self.cite = (t.get(34737) or [b""])[0].split(b"\0")[0].decode("ascii", "replace").strip("| ")
        self._blocks = {}

    def _bad(self, why):
        sys.exit(f"{self.name}: unexpected tile layout, {why}. Delete the file to fetch it again, and report it if it repeats.")

    def _ifd(self, off):
        self.f.seek(off)
        n = struct.unpack(self.bo + "H", self.f.read(2))[0]
        raw = self.f.read(12 * n)
        tags = {}
        for i in range(n):
            tag, typ, cnt = struct.unpack(self.bo + "HHI", raw[i * 12:i * 12 + 8])
            code = self.TYPES.get(typ)
            if code is None:
                continue
            fmt = self.bo + (f"{cnt}s" if code == "s" else f"{cnt}{code}")
            size = struct.calcsize(fmt)
            if size <= 4:
                data = raw[i * 12 + 8:i * 12 + 8 + size]
            else:
                self.f.seek(struct.unpack(self.bo + "I", raw[i * 12 + 8:i * 12 + 12])[0])
                data = self.f.read(size)
            tags[tag] = struct.unpack(fmt, data)
        return tags

    def _block(self, i):
        if i not in self._blocks:
            self.f.seek(self.offs[i])
            data = self.f.read(self.counts[i])
            try:
                self._blocks[i] = data if self.comp == 1 else _lzw(data) if self.comp == 5 else zlib.decompress(data)
            except zlib.error as e:
                self._bad(f"a block does not decompress ({e})")
        return self._blocks[i]

    def pixel(self, lat, lon):
        """(row, col) of the pixel a point falls in; the tile's tie point is its outer corner."""
        return math.floor((self.y0 - lat) / self.sy), math.floor((lon - self.x0) / self.sx)

    def value(self, row, col):
        """Elevation (m) at a pixel; None outside the grid or where the tile holds no data."""
        if not (0 <= row < self.h and 0 <= col < self.w):
            return None
        raw = self._block((row // self.th) * math.ceil(self.w / self.tw) + col // self.tw)
        r, c, tw = row % self.th, col % self.tw, self.tw
        line = raw[r * tw * 4:(r + 1) * tw * 4]
        if self.pred == 3:
            # floating point predictor: the row's bytes are stored most significant plane
            # first, each byte as the difference from the one before it
            line, acc = bytearray(line), 0
            for i in range(len(line)):
                acc = (acc + line[i]) & 255
                line[i] = acc
            v = struct.unpack(">f", bytes(line[k * tw + c] for k in range(4)))[0]
        else:
            v = struct.unpack(self.bo + "f", line[c * 4:c * 4 + 4])[0]
        if self.nodata is not None and abs(v - self.nodata) < 1e-3:
            return None
        return v


# --- Lakes (tools/ncei_depth.md, Lakes) ----------------------------------------------------
LEVELS = os.path.join(DB, "lake_levels.json")
LAKE_MIN = 1.0      # m: water shallower than this under the level is shore, unsurveyed, or
                    # the surveyed surface's own ripple
LAKE_STEP_M = 30    # spacing of the shoreline profiles a level is read from
LAKE_FLAT = 0.2     # m: heights this close to the level count as the flat water surface
LAKE_SPREAD = 10    # of 12 stretches of shoreline the level must show in
LAKE_CHECK_M = 10   # m: largest difference from HydroLAKES' own rough level
JOIN_ZOOM = 14      # the pixel lattice joined water is traced on, the map's most detailed zoom
JOIN_CAP = 2000000  # pixels: joined water past this has spilled onto low ground
JOIN_KM = 25        # a point query tries the lakes with a level this close
JOIN_SEA = 0.5      # m: joined ground this low looks like water; dry land inland stands higher
JOIN_SHORE_M = 100  # joined ground this close to the outline, through the water, may stand higher


def _lake_record(rec):
    info = shapes.lake_record(rec)
    hid = int(info.get("Hylak_id") or 0)
    name = info.get("Lake_name") or ""
    return hid, (f"{name} (HydroLAKES {hid})" if name else f"HydroLAKES lake {hid}"), info


def lake_at(lat, lon):
    """(HydroLAKES id, name, outline rings, record) of the lake holding a point, or None.
    Reads the HydroLAKES outlines lib/shapes.py keeps, downloading them when missing."""
    for rec, rings in shapes.polygons("lakes", lat, lon, 0):
        if shapes.contains(rings, lon, lat):
            hid, name, info = _lake_record(rec)
            return hid, name, rings, info
    return None


def _px_lat(Y):
    return _tile_lat((Y + 0.5) / 256, 2 ** JOIN_ZOOM)


def _px_lon(X):
    return (X + 0.5) / (256 * 2 ** JOIN_ZOOM) * 360 - 180


def _px(lat, lon):
    """The JOIN_ZOOM pixel (X, Y) holding a point."""
    P = 256 * 2 ** JOIN_ZOOM
    return (int((lon + 180) / 360 * P),
            int((1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * P))


class _Rows:
    """Polygon edges bucketed by latitude, for inside tests a row of pixels at a time: the
    coastline's land, or the outlines of the lakes with a level."""
    BAND = 0.01  # degrees of latitude per bucket of edges

    def __init__(self, ring_sets, S=-90.0, N=90.0):
        self.edges, self.buckets, self.rows = [], {}, {}
        for rings in ring_sets:
            for r in rings:
                for a, b in zip(r, r[1:] + r[:1]):
                    if a[1] == b[1] or max(a[1], b[1]) < S or min(a[1], b[1]) > N:
                        continue
                    self.edges.append((a[0], a[1], b[0], b[1]))
                    for k in range(int(min(a[1], b[1]) // self.BAND), int(max(a[1], b[1]) // self.BAND) + 1):
                        self.buckets.setdefault(k, []).append(len(self.edges) - 1)

    def crossings(self, lats):
        """For each latitude, the sorted longitudes where it crosses an edge."""
        ks = range(int(min(lats) // self.BAND), int(max(lats) // self.BAND) + 1)
        edges = [self.edges[i] for i in {i for k in ks for i in self.buckets.get(k, ())}]
        return [sorted(ax + (lat - ay) * (bx - ax) / (by - ay)
                       for ax, ay, bx, by in edges if (ay > lat) != (by > lat)) for lat in lats]

    def inside_px(self, Y, lon):
        """Whether a point on JOIN_ZOOM pixel row Y lies inside."""
        import bisect
        xs = self.rows.get(Y)
        if xs is None:
            xs = self.rows[Y] = self.crossings([_px_lat(Y)])[0]
        return bisect.bisect_left(xs, lon) % 2 == 1

    @staticmethod
    def mask(rows, lons):
        """1 for each pixel of a tile inside, from crossings() of its 256 pixel rows."""
        import bisect
        out, dl = bytearray(65536), (lons[-1] - lons[0]) / 255
        for py, xs in enumerate(rows):
            i = bisect.bisect_left(xs, lons[0])
            inside, c, base = i % 2 == 1, 0, py * 256
            for x in xs[i:]:
                if x > lons[-1]:
                    break
                col = min(256, math.ceil((x - lons[0]) / dl))
                if inside and col > c:
                    out[base + c:base + col] = b"\x01" * (col - c)
                inside, c = not inside, col
            if inside and c < 256:
                out[base + c:base + 256] = b"\x01" * (256 - c)
        return out


def _join(rings, level, grid, land, levelled, unlevelled):
    """{pixel: steps} of the water joined to a lake: JOIN_ZOOM pixels inland of the coastline,
    outside every lake with a level and more than LAKE_MIN below this lake's level, reached from
    its outline through such pixels, each also looking like water: at or below JOIN_SEA, inside
    the outline of a lake with no level of its own, or within JOIN_SHORE_M of the outline through
    the water. It takes in the shallow shore the outline misses, a lake with no level, and a canal
    held at the lake's level, and stops at the coastline, at another lake, and at dry ground, a
    valley below a lake on a plateau among it."""
    import collections
    thr = level - LAKE_MIN
    shore = math.ceil(JOIN_SHORE_M / (2 * math.pi * 6371000 * math.cos(math.radians(rings[0][0][1]))
                                      / (256 * 2 ** JOIN_ZOOM)))
    seen, refused, q = {}, set(), collections.deque()

    def take(p, d):
        if p in seen or p in refused:
            return
        X, Y = p
        lon = _px_lon(X)
        e = None
        if land.inside_px(Y, lon) and not levelled.inside_px(Y, lon):
            e = grid.elev(_px_lat(Y), lon)
        if e is not None and e < thr and (e <= JOIN_SEA or d <= shore or unlevelled.inside_px(Y, lon)):
            seen[p] = d
            q.append(p)
        elif e is None or e >= thr or d > shore:
            refused.add(p)

    for r in rings:
        for a, b in zip(r, r[1:] + r[:1]):
            k = math.cos(math.radians(a[1])) * 111200
            m = max(1, int(math.hypot((b[0] - a[0]) * k, (b[1] - a[1]) * 111200) / 3))
            for i in range(m):
                t = (i + 0.5) / m
                X, Y = _px(a[1] + (b[1] - a[1]) * t, a[0] + (b[0] - a[0]) * t)
                for p in ((X, Y), (X + 1, Y), (X - 1, Y), (X, Y + 1), (X, Y - 1)):
                    take(p, 0)
    while q:
        X, Y = q.popleft()
        d = seen[(X, Y)] + 1
        for p in ((X + 1, Y), (X - 1, Y), (X, Y + 1), (X, Y - 1)):
            take(p, d)
        if len(seen) > JOIN_CAP:
            sys.exit(f"water joined to the lake at {level:+.1f} m ran past {JOIN_CAP} pixels from "
                     f"{_px_lat(Y):.4f}, {_px_lon(X):.4f}: it has spilled onto low ground. Stop and report it.")
    return seen


def lake_joined(lat, lon, grid):
    """(steps, (id, name, rings, record)) of the lake with a level whose joined water holds a
    point, the nearest by steps through the water, or None."""
    X, Y = _px(lat, lon)
    found, other = [], []
    for rec, rings in shapes.polygons("lakes", lat, lon, JOIN_KM):
        hid, name, info = _lake_record(rec)
        lvl = lake_level(hid, rings, info, grid)["level"]
        if lvl is not None:
            found.append((hid, name, rings, info, lvl))
        else:
            other.append(rings)
    e = grid.elev(_px_lat(Y), _px_lon(X))
    tries = [f for f in found if e is not None and e < f[4] - LAKE_MIN]
    if not tries:
        return None
    land = _Rows([r for _, r in shapes.polygons("land", lat, lon, JOIN_KM)])
    levelled, unlevelled = _Rows([f[2] for f in found]), _Rows(other)
    best = None
    for hid, name, rings, info, lvl in tries:
        d = _join(rings, lvl, grid, land, levelled, unlevelled).get((X, Y))
        if d is not None and (best is None or d < best[0]):
            best = (d, (hid, name, rings, info))
    return best


def inland(lat, lon):
    """Whether a point lies inside OpenStreetMap's land, the coastline's landward side, where
    the sea never reaches. lib/shapes.py keeps the polygons."""
    return any(shapes.contains(rings, lon, lat) for _, rings in shapes.polygons("land", lat, lon, 0))


def _find_level(rings, grid):
    """The water level of a lake from the DEM along its shoreline: a profile across the shore
    every LAKE_STEP_M, from 15 m outside the outline to 45 m inside, every 3 m. A profile
    whose most common height repeats three times holds a flat; the level is the flat most
    profiles share, accepted when it shows in LAKE_SPREAD of 12 stretches of the outer
    shore. A filled floor, a flat the survey left below the water, sits in one corner."""
    import collections
    outer = max(rings, key=len)
    flats, outer_profiles, partial = [], [], False
    for ring in rings:
        perim, profiles = 0.0, []
        for a, b in zip(ring, ring[1:] + ring[:1]):
            k = math.cos(math.radians(a[1])) * 111200
            seg = math.hypot((b[0] - a[0]) * k, (b[1] - a[1]) * 111200)
            if seg == 0:
                continue
            nx, ny = -(b[1] - a[1]) * 111200 / seg, (b[0] - a[0]) * k / seg
            n = max(1, int(seg / LAKE_STEP_M))
            for i in range(n):
                t = (i + 0.5) / n
                x, y = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
                s = 1 if shapes.contains(rings, x + nx * 3 / k, y + ny * 3 / 111200) else -1
                vs = []
                for d in range(-15, 46, 3):
                    la, lo = y + s * ny * d / 111200, x + s * nx * d / k
                    v = grid.elev(la, lo)
                    partial = partial or (v is None and grid.missing(la, lo))
                    vs.append(v)
                profiles.append((perim + seg * t, vs))
            perim += seg
        for _, vs in profiles:
            got = collections.Counter(round(v, 1) for v in vs if v is not None).most_common(1)
            if got and got[0][1] >= 3:
                flats.append(got[0][0])
        if ring is outer:
            outer_profiles = [(p / perim, vs) for p, vs in profiles]
    if not flats:
        return {"level": None, "why": "the DEM shows no flat water along its shore", "partial": partial}
    c = collections.Counter(flats)
    centre = max(c, key=lambda v: (sum(n for w, n in c.items() if abs(w - v) <= LAKE_FLAT + 1e-9), -v))
    near = sorted(v for v in flats if abs(v - centre) <= LAKE_FLAT + 1e-9)
    level = near[len(near) // 2]
    stretches = {min(11, int(p * 12)) for p, vs in outer_profiles
                 if sum(1 for v in vs if v is not None and abs(v - level) <= LAKE_FLAT + 1e-9) >= 3}
    if len(stretches) < LAKE_SPREAD:
        return {"level": None, "spread": len(stretches), "partial": partial,
                "why": f"its most common shoreline flat, {level:+.1f} m, shows along only "
                       f"{len(stretches)} of 12 stretches of its shore, the mark of a filled floor"}
    return {"level": level, "spread": len(stretches), "partial": partial}


def lake_level(hid, rings, info, grid):
    """{level, spread, ...} for a lake: its water level above NAVD 88 read from the DEM, or
    level None with why. Kept in lake_levels.json once read from complete tiles; deleting the
    file reads every level again."""
    levels = {}
    if os.path.exists(LEVELS):
        with open(LEVELS) as f:
            levels = json.load(f)
    if str(hid) in levels:
        return levels[str(hid)]
    res = _find_level(rings, grid)
    rough = info.get("Elevation")
    if res["level"] is not None and rough is not None and abs(res["level"] - float(rough)) > LAKE_CHECK_M:
        res = {"level": None, "spread": res["spread"], "partial": res["partial"],
               "why": f"its shoreline flat, {res['level']:+.1f} m, sits more than {LAKE_CHECK_M} m "
                      f"from HydroLAKES' own rough level, {float(rough):g} m"}
    if not res.pop("partial"):
        res["read"] = date.today().isoformat()
        levels[str(hid)] = res
        _save(LEVELS, levels)
    return res


def dem(lat, lon):
    """Return dict: elev (m, signed), depth (m below the tile datum), datum, source, res_m."""
    t = Tile(tile_for(lat, lon))
    row, col = t.pixel(lat, lon)
    elev = t.value(row, col)
    if elev is None:
        sys.exit(f"No DEM data at {lat}, {lon}: the tile {t.name} holds no value there.")
    return {"elev": elev, "depth": -elev, "datum": DATUM, "source": t.name,
            "res_m": round(t.sy * 111200, 1), "tile": t, "row": row, "col": col}


# --- NAVD88 to MLLW, from VDatum, kept per place ------------------------------------------

def _metres(lat, lon, s):
    return math.hypot((s["lat"] - lat) * 111200, (s["lon"] - lon) * 111200 * math.cos(math.radians(lat)))


def _vdatum(lat, lon, region):
    """NAVD88 above MLLW (m) at a point, asked of VDatum."""
    q = {"s_x": lon, "s_y": lat, "s_z": 0, "s_coor": "geo", "s_h_frame": "NAD83_2011",
         "s_v_frame": "NAVD88", "s_v_unit": "m", "t_v_frame": "MLLW", "t_v_unit": "m"}
    if region:
        q["region"] = region
    d = _get_json(VDATUM_URL + "?" + urllib.parse.urlencode(q), "VDatum")
    # Some regions require a specific target horizontal frame for a tidal target datum;
    # VDatum names the frame it wants in the error, so ask once more with that frame.
    if d.get("errorCode") is not None:
        m = re.search(r"Target Horizontal Frame should be (\S+)", d.get("message", ""))
        if m:
            d = _get_json(VDATUM_URL + "?" + urllib.parse.urlencode({**q, "t_h_frame": m.group(1)}), "VDatum")
    for k in ("t_z", "tar_z", "t_z_value"):
        if d.get(k) not in (None, "", "-999999"):
            try:
                return float(d[k])
            except (ValueError, TypeError):
                pass
    sys.exit(f"VDatum gave no NAVD88-to-MLLW height at {lat}, {lon} in region {region or 'contiguous'}: "
             f"{d.get('message') or d}. Check --region, and that the point is in tidal water.")


def mllw_offset(lat, lon, region):
    """(NAVD88 above MLLW in m, the sample it came from, its distance in m). The nearest
    offset VDatum already gave within REUSE_M answers; otherwise VDatum is asked once and
    the answer kept."""
    doc = {"samples": []}
    if os.path.exists(OFFSETS):
        with open(OFFSETS) as f:
            doc = json.load(f)
    near = [s for s in doc["samples"] if _metres(lat, lon, s) <= REUSE_M]
    if near:
        s = min(near, key=lambda s: _metres(lat, lon, s))
        return s["navd88_above_mllw"], s, _metres(lat, lon, s)
    s = {"lat": lat, "lon": lon, "navd88_above_mllw": round(_vdatum(lat, lon, region), 4),
         "region": region or "contiguous", "fetched": date.today().isoformat()}
    doc["samples"].append(s)
    _save(OFFSETS, doc)
    return s["navd88_above_mllw"], s, 0.0


# --- the check against NCEI's live service ------------------------------------------------

def verify(lat, lon, r):
    q = {"geometry": f"{lon},{lat}", "geometryType": "esriGeometryPoint", "sr": "4326",
         "returnGeometry": "false", "f": "json"}
    d = _get_json(LIVE_URL + "?" + urllib.parse.urlencode(q), "NCEI")
    try:
        live = float(d["value"])
        name = d["catalogItems"]["features"][0]["attributes"]["Name"]
    except (KeyError, IndexError, ValueError, TypeError):
        sys.exit(f"NCEI: no value to compare with at {lat}, {lon} ({d.get('value')!r}).")
    t = r["tile"]
    around = [t.value(r["row"] + dr, r["col"] + dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1)]
    gap = min(abs(v - live) for v in around if v is not None)
    same_tile = name.lower() == t.name.lower()
    ok = same_tile and gap <= 0.01
    print(f"  NCEI's live service: {live:.2f} m from {name}")
    print(f"  this tile: {r['elev']:.2f} m at the point's pixel; nearest of the nine pixels around it "
          f"differs from the live value by {gap:.3f} m")
    if ok:
        print("  PASS")
    elif not same_tile:
        print(f"  FAIL: NCEI now answers from {name}. Delete tools/db/ncei_depth/tiles.json and the tile to fetch again.")
    else:
        print(f"  FAIL: NCEI has replaced this tile's data. Delete tools/db/ncei_depth/{t.name}.tif to fetch it again.")
    return ok


# --- Map layer: the cached tiles as web map tiles carrying depth ---------------------------
#
# Each map tile is a 256 x 256 RGB PNG whose pixels hold a 16-bit value v (R high byte, G low
# byte, B zero): depth below NAVD 88 = (v - 1) * MAP_SCALE + MAP_SHALLOWEST, so it runs from
# MAP_SHALLOWEST (5 m above the datum, room for the tide on a drying flat) to the deepest
# water. v = 0, made transparent through the PNG's tRNS chunk, is higher ground or no data.
# The map viewer colours the depths itself, so one set of tiles serves every style.

MAP_DIR = os.path.join(ROOT, "map", "depth")
MAP_LAYER = "ncei"
MAP_SCALE = 0.1
MAP_SHALLOWEST = -5.0
MAP_CHECKS = 24


class _Grid:
    """Every cached tile, read block by block with the most recent blocks kept decoded."""

    def __init__(self, cap_blocks=500, download=False):
        """download: fetch a missing tile the first time a point inside it is read, as a point
        query does; without it only the tiles on this machine are read."""
        self.idx = tile_index()
        self.tiles, self.download = {}, download
        for key, urls in self.idx["tiles"].items():
            path = _latest(urls)[1]
            if os.path.exists(path):
                n, w = map(float, key.split(","))
                self.tiles[(n, w)] = Tile(path)
        if not self.tiles and not download:
            sys.exit(f"No tiles in {DB}; download an area with --fetch first.")
        self.cache, self.cap = {}, cap_blocks

    def missing(self, lat, lon):
        """Whether NOAA has a tile for the point that is not on this machine."""
        n, w = math.ceil(lat / TILE_DEG) * TILE_DEG, math.floor(lon / TILE_DEG) * TILE_DEG
        return (n, w) not in self.tiles and f"{n:g},{w:g}" in self.idx["tiles"]

    def bounds(self):
        ns = [k[0] for k in self.tiles]
        ws = [k[1] for k in self.tiles]
        return min(ns) - TILE_DEG, min(ws), max(ns), max(ws) + TILE_DEG

    def _decoded(self, t, bi):
        key = (t.name, bi)
        arr = self.cache.pop(key, None)
        if arr is None:
            raw = t._block(bi)
            t._blocks.clear()
            tw, th = t.tw, t.th
            arr = array.array("f")
            for r in range(th):
                line = raw[r * tw * 4:(r + 1) * tw * 4]
                if t.pred == 3:
                    b, acc = bytearray(line), 0
                    for i in range(len(b)):
                        acc = (acc + b[i]) & 255
                        b[i] = acc
                    inter = bytearray(4 * tw)
                    for k in range(4):
                        inter[k::4] = b[k * tw:(k + 1) * tw]
                    arr.extend(struct.unpack(f">{tw}f", bytes(inter)))
                else:
                    arr.extend(struct.unpack(f"{t.bo}{tw}f", line))
            if len(self.cache) >= self.cap:
                del self.cache[next(iter(self.cache))]
        self.cache[key] = arr
        return arr

    def elev(self, lat, lon):
        """Elevation at a point exactly as dem() reads it: the tile tile_for() picks and the
        pixel the point falls in. None where no cached tile or no data."""
        key = (math.ceil(lat / TILE_DEG) * TILE_DEG, math.floor(lon / TILE_DEG) * TILE_DEG)
        t = self.tiles.get(key)
        if t is None and self.download and self.missing(lat, lon):
            t = self.tiles[key] = Tile(tile_for(lat, lon))
        if t is None:
            return None
        row, col = t.pixel(lat, lon)
        if not (0 <= row < t.h and 0 <= col < t.w):
            return None
        bi = (row // t.th) * math.ceil(t.w / t.tw) + col // t.tw
        v = self._decoded(t, bi)[(row % t.th) * t.tw + col % t.tw]
        if t.nodata is not None and abs(v - t.nodata) < 1e-3:
            return None
        return v


def _tile_lat(y, n):
    return math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))


def _png(vals, kinds=None):
    """256 x 256 RGB PNG of 16-bit values (R high, G low) and a kind in B (0 sea, k the k-th
    listed lake); value 0 with kind 0 is transparent. Rows Up-filtered."""
    rgb = bytearray(3 * 65536)
    rgb[0::3] = bytes(v >> 8 for v in vals)
    rgb[1::3] = bytes(v & 255 for v in vals)
    if kinds is not None:
        rgb[2::3] = bytes(kinds)
    rows, prev = bytearray(), bytes(768)
    for y in range(256):
        line = rgb[y * 768:(y + 1) * 768]
        rows += b"\x02" + bytes((a - b) & 255 for a, b in zip(line, prev))
        prev = line

    def chunk(k, d):
        return struct.pack(">I", len(d)) + k + d + struct.pack(">I", zlib.crc32(k + d))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 256, 256, 8, 2, 0, 0, 0))
            + chunk(b"tRNS", bytes(6)) + chunk(b"IDAT", zlib.compress(bytes(rows), 9)) + chunk(b"IEND", b""))


def _unpng(path):
    """Values of a tile _png() wrote."""
    with open(path, "rb") as f:
        data = f.read()
    pos, idat = 8, b""
    while pos < len(data):
        n = struct.unpack(">I", data[pos:pos + 4])[0]
        if data[pos + 4:pos + 8] == b"IDAT":
            idat += data[pos + 8:pos + 8 + n]
        pos += 12 + n
    raw, prev, vals, kinds = zlib.decompress(idat), bytes(768), [], []
    for y in range(256):
        line = bytes((a + b) & 255 for a, b in zip(raw[y * 769 + 1:(y + 1) * 769], prev))
        prev = line
        vals.extend((line[i] << 8) | line[i + 1] for i in range(0, 768, 3))
        kinds.extend(line[2::3])
    return vals, kinds


def _write(z, x, y, vals, kinds):
    d = os.path.join(MAP_DIR, MAP_LAYER, str(z), str(x))
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, f"{y}.png"), "wb") as f:
        f.write(_png(vals, kinds))


class _Lakes:
    """Every HydroLAKES outline touching the area, to mark map pixels as lake: a lake with a
    level by its place in the table (1, 2, ...), any other lake EMPTY, never drawn."""
    EMPTY = 255

    def __init__(self, S, W, N, E, grid):
        km = math.hypot((N - S) * 111.2, (E - W) * 111.2 * math.cos(math.radians((S + N) / 2))) / 2
        found = []
        for rec, rings in shapes.polygons("lakes", (S + N) / 2, (W + E) / 2, km):
            xs = [x for r in rings for x, _ in r]
            ys = [y for r in rings for _, y in r]
            if max(ys) < S or min(ys) > N or max(xs) < W or min(xs) > E:
                continue
            hid, name, info = _lake_record(rec)
            lvl = lake_level(hid, rings, info, grid)["level"]
            found.append((min(xs), min(ys), max(xs), max(ys), rings, hid, name, lvl))
        with_level = sorted((L for L in found if L[7] is not None), key=lambda L: L[5])
        if len(with_level) >= self.EMPTY:
            sys.exit(f"{len(with_level)} lakes with a level; a map pixel's kind holds at most {self.EMPTY - 1}.")
        self._table = [{"id": L[5], "name": L[6].split(" (HydroLAKES")[0] if "(" in L[6] else "Lake",
                        "level": L[7]} for L in with_level]
        self.level = [None] + [L[7] for L in with_level]
        kind = {L[5]: i + 1 for i, L in enumerate(with_level)}
        self.levelled = [(i + 1, L[4], L[7]) for i, L in enumerate(with_level)]
        self.levelled_rows = _Rows([L[4] for L in with_level])
        self.unlevelled_rows = _Rows([L[4] for L in found if L[7] is None])
        self.lakes = []
        # Lakes with no level first, so a lake with one wins where two outlines overlap.
        for x0, y0, x1, y1, rings, hid, _, lvl in sorted(found, key=lambda L: L[7] is not None):
            edges = [(a[0], a[1], b[0], b[1]) for r in rings for a, b in zip(r, r[1:] + r[:1]) if a[1] != b[1]]
            self.lakes.append((x0, y0, x1, y1, edges, kind.get(hid, self.EMPTY)))
        print(f"{len(found)} lakes, {len(with_level)} with a level read from the DEM", file=sys.stderr, flush=True)

    def table(self):
        return self._table

    def kinds(self, lats, lons):
        """The kind of each pixel of a tile (pixel-centre latitudes and longitudes), as a list of
        65536, or None where no lake reaches the tile."""
        lo0, lo1, la0, la1 = lons[0], lons[-1], lats[-1], lats[0]
        near = [L for L in self.lakes if L[2] >= lo0 and L[0] <= lo1 and L[3] >= la0 and L[1] <= la1]
        if not near:
            return None
        out, dl = [0] * 65536, (lons[-1] - lons[0]) / 255
        for x0, y0, x1, y1, edges, kind in near:
            rows = [e for e in edges if max(e[1], e[3]) >= la0 and min(e[1], e[3]) <= la1]
            for py, lat in enumerate(lats):
                if not y0 <= lat <= y1:
                    continue
                xs = sorted(ax + (lat - ay) * (bx - ax) / (by - ay)
                            for ax, ay, bx, by in rows if (ay > lat) != (by > lat))
                for a, b in zip(xs[0::2], xs[1::2]):
                    c0 = max(0, math.ceil((a - lons[0]) / dl))
                    c1 = min(255, math.floor((b - lons[0]) / dl))
                    for c in range(c0, c1 + 1):
                        out[py * 256 + c] = kind
        return out


def _encode(e, kind, levels):
    """The stored value of one pixel from its elevation and kind, 0 for nothing drawn: depth
    below NAVD 88 at sea, depth below the lake's level in a lake with one."""
    if e is None or kind == _Lakes.EMPTY:
        return 0
    if kind:
        d = levels[kind] - e
        return 0 if d < LAKE_MIN else min(65535, round((d - MAP_SHALLOWEST) / MAP_SCALE) + 1)
    return 0 if -e < MAP_SHALLOWEST else min(65535, round((-e - MAP_SHALLOWEST) / MAP_SCALE) + 1)


def export_map(max_zoom, min_zoom):
    """Write map/depth/ncei/{z}/{x}/{y}.png for every cached tile, and map/depth/ncei.js, the
    layer's description with check values the viewer reproduces before drawing."""
    import random
    import shutil
    import time
    grid = _Grid()
    S, W, N, E = grid.bounds()
    t0 = time.time()
    lakes = _Lakes(S, W, N, E, grid)
    km = math.hypot((N - S) * 111.2, (E - W) * 111.2 * math.cos(math.radians((S + N) / 2))) / 2 + 5
    land = _Rows([r for _, r in shapes.polygons("land", (S + N) / 2, (W + E) / 2, km)], S, N)
    # Water joined to each lake with a level, by map tile: a pixel two lakes reach is the one
    # nearer through the water.
    best = {}
    for kind, rings, level in lakes.levelled:
        for p, d in _join(rings, level, grid, land, lakes.levelled_rows, lakes.unlevelled_rows).items():
            if p not in best or d < best[p][0]:
                best[p] = (d, kind)
    joined = {}
    for (X, Y), (_, kind) in best.items():
        joined.setdefault((X // 256, Y // 256), []).append(((Y % 256) * 256 + X % 256, kind))
    print(f"lakes, coastline and {len(best)} pixels of joined water read, {time.time() - t0:.0f} s",
          file=sys.stderr, flush=True)
    out = os.path.join(MAP_DIR, MAP_LAYER)
    if os.path.isdir(out):
        shutil.rmtree(out)
    n = 2 ** max_zoom
    x0, x1 = int((W + 180) / 360 * n), int((E + 180) / 360 * n)
    ty = lambda lat: int((1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n)
    cols = [x for x in range(x0, x1 + 1)]
    lons = {}
    written = {max_zoom: set()}
    # Check points: a lattice of pixels in each tile, kept by reservoir sampling per kind, at
    # sea outside the coastline and in a lake inside its own outline, as a point query reads.
    rng, want = random.Random(1), {0: MAP_CHECKS}
    seen, picks = {}, {}
    print(f"{len(grid.tiles)} cached tiles, {S:g} to {N:g} N, {W:g} to {E:g} E; "
          f"rendering zoom {max_zoom}...", file=sys.stderr, flush=True)
    for y in range(ty(N), ty(S) + 1):
        lats = [_tile_lat(y + (p + 0.5) / 256, n) for p in range(256)]
        rows = None
        for x in cols:
            if x not in lons:
                lons[x] = [(x + (p + 0.5) / 256) / n * 360 - 180 for p in range(256)]
            lx = lons[x]
            if lx[-1] < W or lx[0] > E or lats[-1] > N or lats[0] < S:
                continue
            cells = {(math.ceil(la / TILE_DEG) * TILE_DEG, math.floor(lo / TILE_DEG) * TILE_DEG)
                     for la in (lats[0], lats[-1]) for lo in (lx[0], lx[-1])}
            if not any(c in grid.tiles for c in cells):
                continue
            if rows is None:
                rows = land.crossings(lats)
            es = [grid.elev(lat, lon) for lat in lats for lon in lx]
            outline = lakes.kinds(lats, lx) or [0] * 65536
            kinds = list(outline)
            for i, kind in joined.get((x, y), ()):
                kinds[i] = kind
            onland = land.mask(rows, lx)
            # Inland of the coastline and in no lake: never sea.
            for i in range(65536):
                if onland[i] and not kinds[i]:
                    kinds[i] = _Lakes.EMPTY
            vals = [_encode(e, k, lakes.level) for e, k in zip(es, kinds)]
            if not any(vals):
                continue
            for py in range(16, 256, 32):
                for px in range(16, 256, 32):
                    i = py * 256 + px
                    k = kinds[i]
                    if not vals[i] or k != outline[i] or (k == 0 and onland[i]):
                        continue
                    seen[k] = seen.get(k, 0) + 1
                    got, cap, pt = picks.setdefault(k, []), want.get(k, 2), (lats[py], lx[px])
                    if len(got) < cap:
                        got.append(pt)
                    elif (j := rng.randrange(seen[k])) < cap:
                        got[j] = pt
            ks = [k if v else 0 for v, k in zip(vals, kinds)]
            _write(max_zoom, x, y, vals, ks if any(ks) else None)
            written[max_zoom].add((x, y))
        print(f"  row {y - ty(N) + 1}/{ty(S) - ty(N) + 1}, {len(written[max_zoom])} tiles, "
              f"{time.time() - t0:.0f} s", file=sys.stderr, flush=True)
    # Lower zooms: each pixel the mean of the 2 x 2 below it of the kind most of them hold,
    # kept where at least two hold data of that kind.
    for z in range(max_zoom - 1, min_zoom - 1, -1):
        written[z] = set()
        for (cx, cy) in {(x // 2, y // 2) for x, y in written[z + 1]}:
            vals, kinds = [0] * 65536, [0] * 65536
            for dx in (0, 1):
                for dy in (0, 1):
                    if (2 * cx + dx, 2 * cy + dy) not in written[z + 1]:
                        continue
                    cv, ck = _unpng(os.path.join(out, str(z + 1), str(2 * cx + dx), f"{2 * cy + dy}.png"))
                    for py in range(128):
                        for px in range(128):
                            q = [((2 * py + a) * 256 + 2 * px + b) for a in (0, 1) for b in (0, 1)]
                            q = [(cv[i], ck[i]) for i in q if cv[i]]
                            if len(q) < 2:
                                continue
                            kind = max({k for _, k in q}, key=lambda kk: sum(1 for _, k in q if k == kk))
                            same = [v for v, k in q if k == kind]
                            if len(same) >= 2:
                                o = (dy * 128 + py) * 256 + dx * 128 + px
                                vals[o], kinds[o] = round(sum(same) / len(same)), kind
            if any(vals):
                _write(z, cx, cy, vals, kinds)
                written[z].add((cx, cy))
        print(f"  zoom {z}: {len(written[z])} tiles, {time.time() - t0:.0f} s", file=sys.stderr, flush=True)
    _describe(grid, lakes, picks, written, max_zoom, min_zoom, out, t0)


def _describe(grid, lakes, picks, written, max_zoom, min_zoom, out, t0):
    """Write map/depth/ncei.js for the tiles written: the layer's description, with check
    values read at the picked points the way a point query reads them."""
    import time
    S, W, N, E = grid.bounds()
    checks = []
    for kind in sorted(picks):
        for lat, lon in picks[kind]:
            # The cached tile tile_for() would pick, read with Tile.value as dem() reads it.
            t = grid.tiles[(math.ceil(lat / TILE_DEG) * TILE_DEG, math.floor(lon / TILE_DEG) * TILE_DEG)]
            r, c = t.pixel(lat, lon)
            v = t.value(r, c)
            t._blocks.clear()
            depth = lakes.level[kind] - v if kind else -v
            checks.append({"lat": round(lat, 7), "lon": round(lon, 7), "depth": round(depth, 2), "lake": kind})
    if len(picks.get(0, ())) < MAP_CHECKS:
        sys.exit(f"found only {len(picks.get(0, ()))} sea check points of {MAP_CHECKS}")
    total_bytes = sum(os.path.getsize(os.path.join(out, str(z), str(x), f"{y}.png"))
                      for z, s in written.items() for x, y in s)
    layer = {
        "name": MAP_LAYER, "label": "Depth (NCEI)", "datum": DATUM,
        "tiles": f"map/depth/{MAP_LAYER}/{{z}}/{{x}}/{{y}}.png",
        "scale": MAP_SCALE, "shallowest": MAP_SHALLOWEST,
        "minZoom": min_zoom, "maxZoom": max_zoom,
        "bounds": [[S, W], [N, E]],
        "built": date.today().isoformat(),
        "sources": sorted(t.name for t in grid.tiles.values()),
        "lakes": lakes.table(),
        "present": {str(z): ",".join(f"{x}/{y}" for x, y in sorted(s)) for z, s in written.items()},
        "checks": checks,
    }
    with open(os.path.join(MAP_DIR, f"{MAP_LAYER}.js"), "w") as f:
        f.write("// Written by tools/ncei_depth.py --export-map; regenerate rather than edit.\n")
        f.write("window.MAP_DEPTH = window.MAP_DEPTH || {};\n")
        f.write(f"window.MAP_DEPTH[{json.dumps(MAP_LAYER)}] = {json.dumps(layer, separators=(',', ':'))};\n")
    count = sum(len(s) for s in written.values())
    print(f"wrote {count} tiles ({total_bytes / 1e6:.0f} MB) to map/depth/{MAP_LAYER}/ and "
          f"map/depth/{MAP_LAYER}.js, {len(checks)} checks, in {time.time() - t0:.0f} s", file=sys.stderr)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("lat", type=float, nargs="?")
    p.add_argument("lon", type=float, nargs="?")
    p.add_argument("--fetch", nargs=4, type=float, action="append", metavar=("S", "W", "N", "E"),
                   help="download every tile touching this box; repeatable")
    p.add_argument("--workers", type=int, default=6, help="tiles downloaded at once with --fetch, default 6")
    p.add_argument("--mllw", action="store_true", help="also convert to depth below MLLW (VDatum)")
    p.add_argument("--region", default=None,
                   help="VDatum region: contiguous (Atlantic/Gulf, VDatum's own default), westcoast, "
                        "ak, seak, hi, prvi, gcnmi, as, chesapeak_delaware, wgom, sgi, spi, sli; "
                        "defaults to ncei_depth.default_region in tool-config.json")
    p.add_argument("--verify", action="store_true", help="compare the tile with NCEI's live service")
    p.add_argument("--export-map", action="store_true",
                   help="write the map viewer's depth layer from every cached tile")
    p.add_argument("--max-zoom", type=int, default=14, help="--export-map's most detailed zoom, default 14")
    p.add_argument("--min-zoom", type=int, default=9, help="--export-map's least detailed zoom, default 9")
    a = p.parse_args()
    region = a.region or _cfg("default_region")
    if a.fetch:
        sys.exit(1 if fetch(a.fetch, a.workers) else 0)
    if a.export_map:
        export_map(a.max_zoom, a.min_zoom)
        return
    if a.lat is None or a.lon is None:
        p.error("give LAT LON, or --fetch S W N E")

    r = dem(a.lat, a.lon)
    print(f"{a.lat}, {a.lon}")
    grid = _Grid(download=True)
    lake, where = lake_at(a.lat, a.lon), ""
    if lake and lake_level(lake[0], lake[2], lake[3], grid)["level"] is None or not lake and inland(a.lat, a.lon):
        joined = lake_joined(a.lat, a.lon, grid)
        if joined:
            where = f", in {lake[1]} joined to it" if lake else ", in water joined to it outside its outline"
            lake = joined[1]
        elif not lake and r["elev"] < 0:
            print(f"  inland of the coastline and in no lake, at {r['elev']:+.1f} m {r['datum']}: "
                  f"water no lake outline holds, or diked ground; no depth.")
            print(f"  source {r['source']} (~{r['res_m']:.0f} m), read from this machine")
            return
    if lake:
        hid, name, rings, info = lake
        lv = lake_level(hid, rings, info, grid)
        level = lv["level"]
        if level is None:
            print(f"  in {name}: bed or water at {r['elev']:+.1f} m {r['datum']}; no depth, since "
                  f"no water level was found for the lake: {lv['why']}.")
        elif r["elev"] > level - LAKE_MIN:
            print(f"  in {name}{where}, at or above its water level ({r['elev']:+.1f} m {r['datum']}): "
                  f"shore, or water the DEM holds no bed for. Walk the coordinate out.")
        else:
            print(f"  lake bed {level - r['elev']:.1f} m below the water of {name}{where}")
            print(f"  (bed {r['elev']:+.1f} m {r['datum']}; water level {level:+.1f} m, the DEM's flat "
                  f"water along {lv['spread']} of 12 stretches of its shore on the day it was surveyed)")
        print(f"  source {r['source']} (~{r['res_m']:.0f} m), read from this machine")
        if a.mllw:
            print("  MLLW applies to the sea, never to a lake.")
        return
    if r["elev"] >= 0:
        print(f"  ABOVE WATER: +{r['elev']:.1f} m in the DEM ({r['datum']}). Check the coordinate.")
    else:
        print(f"  seabed {r['depth']:.1f} m below {r['datum']}")
    print(f"  source {r['source']} (~{r['res_m']:.0f} m), read from this machine")
    if a.mllw and r["elev"] < 0:
        off, s, dist = mllw_offset(a.lat, a.lon, region)
        where = "at this point" if dist < 1 else f"{dist:.0f} m away"
        print(f"  seabed {r['depth'] - off:.1f} m below MLLW  (NAVD 88 is {off:.2f} m above MLLW; "
              f"VDatum, asked {where} on {s['fetched']})")
    if a.verify and not verify(a.lat, a.lon, r):
        sys.exit(1)


if __name__ == "__main__":
    main()

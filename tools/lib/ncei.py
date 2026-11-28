"""NOAA NCEI's ninth arc-second coastal DEM, shared by the depth tool, map_export.py and the
current tool's seabed: the tile list and each tile, downloaded when missing, the elevation at a
point, the lakes and their water levels, and the NAVD 88 to MLLW offset, from VDatum's grids
kept on this machine (lib/vdatum.py)."""
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
from concurrent.futures import ThreadPoolExecutor
from datetime import date

from lib import shapes, vdatum
from lib.dem_tiles import Tile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


DB = os.path.join(ROOT, "tools", "db", "depth", "ncei")


INDEX = os.path.join(DB, "tiles.json")


LIST_URL = ("https://chs.coast.noaa.gov/htdata/raster2/elevation/"
            "NCEI_ninth_Topobathy_2014_8483/urllist8483.txt")


LIVE_URL = "https://gis.ngdc.noaa.gov/arcgis/rest/services/DEM_mosaics/DEM_all/ImageServer/identify"


TILE_DEG = 0.25     # a tile's side


DATUM = "NAVD 88"   # the ninth arc-second DEM's vertical datum


def _cfg(key, default=None):
    """The depth tool's section of tool-config.jsonc; a missing file or key gives the default."""
    from lib import config
    return config.get("depth", key, default)


def _user_agent():
    """The User-Agent carries tool-config.jsonc's top-level user_agent_email."""
    from lib import config
    return config.user_agent()


UA = _user_agent()


shapes.USER_AGENT = UA


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


_INDEX_DOC = []


def tile_index():
    """NOAA's list of ninth arc-second tiles: {"N,W": [url, ...]} keyed by a tile's north
    and west edges. Downloaded once, and read once per process."""
    if _INDEX_DOC:
        return _INDEX_DOC[0]
    if os.path.exists(INDEX):
        with open(INDEX) as f:
            _INDEX_DOC.append(json.load(f))
        return _INDEX_DOC[0]
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
    _INDEX_DOC.append(doc)
    return doc


def _latest(urls):
    """Of a tile's editions, the newest: (url, local path)."""
    def edition(u):
        m = re.search(r"_(\d{4})v(\d+)\.tif$", u, re.I)
        return int(m[1]), int(m[2])
    url = max(urls, key=edition)
    return url, os.path.join(DB, url.rsplit("/", 1)[1])


def tile_path(lat, lon):
    """The local path of the tile covering a point, downloaded when missing; None where NOAA's
    list holds no tile there."""
    key = f"{math.ceil(lat / TILE_DEG) * TILE_DEG:g},{math.floor(lon / TILE_DEG) * TILE_DEG:g}"
    urls = tile_index()["tiles"].get(key)
    if not urls:
        return None
    url, path = _latest(urls)
    if not os.path.exists(path):
        _download(url, path)
    return path


def tile_for(lat, lon):
    """The local path of the tile covering a point, downloaded when missing."""
    path = tile_path(lat, lon)
    if path is None:
        idx = tile_index()
        sys.exit(f"No ninth arc-second DEM tile covers {lat}, {lon} (NOAA's list as fetched {idx['fetched']}). "
                 "The point is outside the coastal DEM. Delete tools/db/depth/ncei/tiles.json to list again.")
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


# --- Lakes (tools/depth.md, Lakes) ----------------------------------------------------
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


def answer(lat, lon):
    """The depth at a point, below the datum of the water it lies in: {water, depth, datum,
    detail, why, dem}. water is "sea" (depth below MLLW, from VDatum's grids), "lake" (depth
    below the lake's water level read from the DEM), or "none" (no depth: land, shore, or water
    no lake holds), with why. dem is dem()'s reading, for verify."""
    r = dem(lat, lon)
    out = {"dem": r, "depth": None, "datum": None, "detail": None, "why": None}
    grid = _Grid(download=True)
    lake, where = lake_at(lat, lon), ""
    if lake and lake_level(lake[0], lake[2], lake[3], grid)["level"] is None or not lake and inland(lat, lon):
        joined = lake_joined(lat, lon, grid)
        if joined:
            where = f", in {lake[1]} joined to it" if lake else ", in water joined to it outside its outline"
            lake = joined[1]
        elif not lake and r["elev"] < 0:
            return {**out, "water": "none",
                    "why": f"inland of the coastline and in no lake, at {r['elev']:+.1f} m {r['datum']}: "
                           f"water no lake outline holds, or diked ground"}
    if lake:
        hid, name, rings, info = lake
        lv = lake_level(hid, rings, info, grid)
        level = lv["level"]
        if level is None:
            return {**out, "water": "none",
                    "why": f"in {name}, bed or water at {r['elev']:+.1f} m {r['datum']}, and no water "
                           f"level was found for the lake: {lv['why']}"}
        if r["elev"] > level - LAKE_MIN:
            return {**out, "water": "none",
                    "why": f"in {name}{where}, at or above its water level ({r['elev']:+.1f} m {r['datum']}): "
                           f"shore, or water the DEM holds no bed for; walk the coordinate out"}
        return {**out, "water": "lake", "depth": level - r["elev"], "datum": f"the surface of {name}",
                "detail": f"bed {r['elev']:+.1f} m {r['datum']}{where}; water level {level:+.1f} m, the DEM's "
                          f"flat water along {lv['spread']} of 12 stretches of its shore on the day it was surveyed"}
    if r["elev"] >= 0:
        return {**out, "water": "none",
                "why": f"above water, +{r['elev']:.1f} m {r['datum']} in the DEM; check the coordinate"}
    off, sub = mllw_offset(lat, lon)
    return {**out, "water": "sea", "depth": r["depth"] - off, "datum": "MLLW",
            "detail": f"{r['depth']:.1f} m below {r['datum']}, which sits {off:.2f} m above MLLW "
                      f"in VDatum sub-region {sub}"}


def has_tile(lat, lon):
    """Whether NOAA's tile list holds a tile for the point, with nothing downloaded but the list."""
    key = f"{math.ceil(lat / TILE_DEG) * TILE_DEG:g},{math.floor(lon / TILE_DEG) * TILE_DEG:g}"
    return key in tile_index()["tiles"]


def has_data(lat, lon):
    """Whether the tile covering a point holds a value at its pixel, downloading the tile when
    missing; False where NOAA's list holds no tile there."""
    path = tile_path(lat, lon)
    if path is None:
        return False
    t = _open_tile(path)
    return t.fast(*t.pixel(lat, lon)) is not None


_TILES = {}      # path -> Tile, kept open for the edge search
_SUMMARY = {}    # (tile name, block) -> 0 no data, 1 data at every pixel, 2 some


def _open_tile(path):
    t = _TILES.get(path)
    if t is None:
        t = _TILES[path] = Tile(path)
    return t


def _summary(t, bi):
    """Whether a block holds no data (0), data at every pixel it holds (1), or some (2)."""
    key = (t.name, bi)
    if key not in _SUMMARY:
        arr = t.floats(bi)
        bpr = (t.w + t.tw - 1) // t.tw
        br, bc = divmod(bi, bpr)
        rows, cols = min(t.th, t.h - br * t.th), min(t.tw, t.w - bc * t.tw)
        n = sum(1 for r in range(rows) for v in arr[r * t.tw:r * t.tw + cols] if t.is_nodata(v))
        _SUMMARY[key] = 1 if n == 0 else 0 if n == rows * cols else 2
    return _SUMMARY[key]


def nearest_data(lat, lon, limit_m, keep_row=None):
    """(metres, lat, lon, elevation) of the nearest pixel centre within limit_m where the tile the
    tool reads holds data, each tile searched over the pixels whose centres lie in its own quarter
    degree cell, as tile_path() picks it; None where there is none. Distances are metres on the
    local plane at the point. keep_row, when given, takes a pixel row's latitude and gives the
    [west, east] longitudes where its pixels count. Missing tiles touching the search are
    downloaded, as has_data() downloads them."""
    ky, kx = 111200.0, 111200.0 * math.cos(math.radians(lat))
    lim2 = limit_m * limit_m
    dlat, dlon = limit_m / ky, limit_m / kx
    idx = tile_index()["tiles"]
    best = None
    for ni in range(math.ceil((lat - dlat) / TILE_DEG), math.ceil((lat + dlat) / TILE_DEG) + 1):
        for wi in range(math.floor((lon - dlon) / TILE_DEG), math.floor((lon + dlon) / TILE_DEG) + 1):
            n, w = ni * TILE_DEG, wi * TILE_DEG
            if f"{n:g},{w:g}" not in idx:
                continue
            t = _open_tile(tile_path(n - TILE_DEG / 2, w + TILE_DEG / 2))
            lo_lat, hi_lat = max(n - TILE_DEG, lat - dlat), min(n, lat + dlat)
            lo_lon, hi_lon = max(w, lon - dlon), min(w + TILE_DEG, lon + dlon)
            if lo_lat >= hi_lat or lo_lon >= hi_lon:
                continue
            r0 = max(0, math.floor((t.y0 - hi_lat) / t.sy - 0.5) - 1)
            r1 = min(t.h - 1, math.ceil((t.y0 - lo_lat) / t.sy - 0.5) + 1)
            c0 = max(0, math.floor((lo_lon - t.x0) / t.sx - 0.5) - 1)
            c1 = min(t.w - 1, math.ceil((hi_lon - t.x0) / t.sx - 0.5) + 1)
            # only the centres in this tile's own cell
            while c0 <= c1 and math.floor((t.x0 + (c0 + 0.5) * t.sx) / TILE_DEG) * TILE_DEG != w:
                c0 += 1
            while c1 >= c0 and math.floor((t.x0 + (c1 + 0.5) * t.sx) / TILE_DEG) * TILE_DEG != w:
                c1 -= 1
            rs = (t.y0 - lat) / t.sy - 0.5     # the point's own fractional row and column
            cs = (lon - t.x0) / t.sx - 0.5
            bpr = (t.w + t.tw - 1) // t.tw
            for r in range(r0, r1 + 1):
                clat = t.y0 - (r + 0.5) * t.sy
                if math.ceil(clat / TILE_DEG) * TILE_DEG != n:
                    continue
                dy = (r - rs) * t.sy * ky
                cap = best[0] if best is not None else lim2
                if dy * dy >= cap:
                    continue
                spans = [(c0, c1)]
                if keep_row is not None:
                    spans = []
                    for a, b in keep_row(clat):
                        ca = max(c0, math.ceil((a - t.x0) / t.sx - 0.5))
                        cb = min(c1, math.floor((b - t.x0) / t.sx - 0.5))
                        if ca <= cb:
                            spans.append((ca, cb))
                br = r // t.th
                for ca, cb in spans:
                    for bc in range(ca // t.tw, cb // t.tw + 1):
                        a0, a1 = max(ca, bc * t.tw), min(cb, bc * t.tw + t.tw - 1)
                        bi = br * bpr + bc
                        kind = _summary(t, bi)
                        if kind == 0:
                            continue
                        cc = min(a1, max(a0, round(cs)))
                        dx = (cc - cs) * t.sx * kx
                        cap = best[0] if best is not None else lim2
                        if dx * dx + dy * dy >= cap:
                            continue
                        arr = t.floats(bi)
                        base = (r - br * t.th) * t.tw - bc * t.tw
                        if kind == 1:
                            found = cc
                        else:
                            # the row's columns in order of distance from the point: the first
                            # with data is the row's nearest, unless it is past the best so far
                            found, c, L, R = None, cc, cc - 1, cc + 1
                            while True:
                                if not t.is_nodata(arr[base + c]):
                                    found = c
                                    break
                                if L < a0 and R > a1:
                                    break
                                if R > a1 or (L >= a0 and abs(L - cs) <= abs(R - cs)):
                                    c, L = L, L - 1
                                else:
                                    c, R = R, R + 1
                                ex = (c - cs) * t.sx * kx
                                if ex * ex + dy * dy >= cap:
                                    break
                            if found is None:
                                continue
                        ex = (found - cs) * t.sx * kx
                        d2 = ex * ex + dy * dy
                        if d2 < cap:
                            best = (d2, clat, t.x0 + (found + 0.5) * t.sx, arr[base + found])
    if best is None:
        return None
    return math.sqrt(best[0]), best[1], best[2], best[3]


def in_vdatum(lat, lon):
    """Whether a point lies inside one of VDatum's sub-regions, where the tiles' NAVD 88 can be
    placed on MLLW."""
    return vdatum.region_at(lat, lon)[0] is not None


def covered(lat, lon):
    """Whether the NCEI DEM answers at a point: its tile holds data there, and the point lies in a
    VDatum sub-region or inland of the coastline. At sea the depth is placed on MLLW by VDatum, so
    NCEI's border tiles pass the Canadian water VDatum leaves out to the next source; a lake is
    read below its own level, with no VDatum."""
    return has_tile(lat, lon) and has_data(lat, lon) and (inland(lat, lon) or in_vdatum(lat, lon))


def mllw_offset(lat, lon):
    """(NAVD 88's height above MLLW in m, the VDatum sub-region it came from) at a point, from
    VDatum's grids kept on this machine. A point VDatum gives no answer for stops the run."""
    off, where = vdatum.navd88_above_mllw(lat, lon)
    if off is None:
        sys.exit(f"VDatum gives no NAVD 88 to MLLW height at {lat}, {lon}: {where}.")
    return off, where


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
        print(f"  FAIL: NCEI now answers from {name}. Delete tools/db/depth/ncei/tiles.json and the tile to fetch again.")
    else:
        print(f"  FAIL: NCEI has replaced this tile's data. Delete tools/db/depth/ncei/{t.name}.tif to fetch it again.")
    return ok


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
            sys.exit(f"No tiles in {DB}; download an area with depth.py fetch first.")
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

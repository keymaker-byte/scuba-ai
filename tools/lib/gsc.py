"""The Geological Survey of Canada's Canada West Coast topo-bathymetric DEM (Open File 8963,
Version 2), for the depth tool: the one 10 m GeoTIFF taken out of NRCan's zip and kept on this
machine, the BC Albers projection it is gridded on, and the elevation at a point, on CHS Chart
Datum."""
import json
import math
import os
import struct
import sys
import urllib.error
import urllib.parse
import urllib.request
import zlib
from datetime import date

from lib import ncei
from lib.dem_tiles import Tile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


DB = os.path.join(ROOT, "tools", "db", "depth", "gsc")


INDEX = os.path.join(DB, "index.json")


ZIP_URL = ("https://ftp.maps.canada.ca/pub/nrcan_rncan/Topography_Topographie/"
           "canada_west_coast_DEM-MNA_cote_ouest_canada/west_coast_dem_v2.zip")


TIF = "GeoTIFF/WestCoastDEM_Version2_Elevation.tif"   # the elevation band inside the zip


TFW = "GeoTIFF/WestCoastDEM_Version2_Elevation.tfw"   # its world file, the grid's georeference


LIVE_URL = ("https://maps-cartes.services.geo.ca/server_serveur/rest/services/NRCan/"
            "canada_west_coast_DEM_en/MapServer/identify")


LIVE_LAYER = 4      # the service's "West Coast DEM Elevations" layer


DATUM = "CHS Chart Datum"   # the DEM's vertical datum in the sea


BOX = (47.195224, -134.813125, 56.24407, -120.946228)   # the DEM's extent, S W N E, from its metadata


NAME = "GSC West Coast DEM"


UA = ncei.UA


# --- BC Albers (EPSG:3005): NAD83 on GRS 80, Snyder's ellipsoidal Albers equal-area ----------
_A, _F = 6378137.0, 1 / 298.257222101
_E2 = 2 * _F - _F * _F
_E = math.sqrt(_E2)
_LAT0, _LON0, _LAT1, _LAT2, _X0, _Y0 = 45.0, -126.0, 50.0, 58.5, 1000000.0, 0.0


def _q(phi):
    s = math.sin(phi)
    return (1 - _E2) * (s / (1 - _E2 * s * s) - math.log((1 - _E * s) / (1 + _E * s)) / (2 * _E))


def _m(phi):
    s = math.sin(phi)
    return math.cos(phi) / math.sqrt(1 - _E2 * s * s)


_m1, _m2 = _m(math.radians(_LAT1)), _m(math.radians(_LAT2))
_q1, _q2 = _q(math.radians(_LAT1)), _q(math.radians(_LAT2))
_N = (_m1 * _m1 - _m2 * _m2) / (_q2 - _q1)
_C = _m1 * _m1 + _N * _q1
_RHO0 = _A * math.sqrt(_C - _N * _q(math.radians(_LAT0))) / _N


def albers(lat, lon):
    """(x, y) in metres on BC Albers for a point in degrees on NAD83."""
    rho = _A * math.sqrt(_C - _N * _q(math.radians(lat))) / _N
    theta = _N * math.radians(lon - _LON0)
    return _X0 + rho * math.sin(theta), _Y0 + _RHO0 - rho * math.cos(theta)


# --- The zip on NRCan's server, and the members taken out of it ------------------------------
def _range(start, end, timeout=60):
    req = urllib.request.Request(ZIP_URL, headers={"User-Agent": UA, "Range": f"bytes={start}-{end}"})
    return urllib.request.urlopen(req, timeout=timeout)


def _read_range(start, end, what):
    try:
        with _range(start, end) as r:
            if r.status != 206:
                raise OSError(f"the server answered {r.status} to a byte range request")
            return r.read()
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        sys.exit(f"{NAME}: {what} failed ({getattr(e, 'reason', e)}) for {ZIP_URL}. Nothing was cached.")


def index():
    """Where the GeoTIFF and its world file sit inside NRCan's zip, read once from the zip's
    central directory with byte range requests: {fetched, last_modified, size, members: {name:
    {offset, csize, size, crc, method}}}."""
    if os.path.exists(INDEX):
        with open(INDEX) as f:
            return json.load(f)
    try:
        with urllib.request.urlopen(urllib.request.Request(ZIP_URL, method="HEAD", headers={"User-Agent": UA}),
                                    timeout=60) as r:
            size, modified = int(r.headers["Content-Length"]), r.headers.get("Last-Modified")
    except (urllib.error.URLError, TimeoutError, OSError, KeyError, ValueError) as e:
        sys.exit(f"{NAME}: the zip is unreachable ({getattr(e, 'reason', e)}) for {ZIP_URL}. Nothing was cached.")
    tail = _read_range(max(0, size - 65600), size - 1, "reading the zip's directory")
    end = tail.rfind(b"PK\x05\x06")
    if end < 0:
        sys.exit(f"{NAME}: no zip directory at the end of {ZIP_URL}. Nothing was cached.")
    cd_size, cd_off = struct.unpack("<II", tail[end + 12:end + 20])
    z64 = tail.rfind(b"PK\x06\x06")
    if z64 >= 0:
        cd_size, cd_off = struct.unpack("<QQ", tail[z64 + 40:z64 + 56])
    cd = _read_range(cd_off, cd_off + cd_size - 1, "reading the zip's directory")
    members, p = {}, 0
    while cd[p:p + 4] == b"PK\x01\x02":
        method, = struct.unpack("<H", cd[p + 10:p + 12])
        crc, csize, usize, nl, el, cl = struct.unpack("<IIIHHH", cd[p + 16:p + 34])
        off, = struct.unpack("<I", cd[p + 42:p + 46])
        name = cd[p + 46:p + 46 + nl].decode("utf8", "replace")
        extra, q = cd[p + 46 + nl:p + 46 + nl + el], 0
        while q + 4 <= len(extra):
            hid, hl = struct.unpack("<HH", extra[q:q + 4])
            if hid == 1:  # ZIP64 sizes and offset, in this order, for each field set to 0xFFFFFFFF
                vals, k = struct.unpack(f"<{hl // 8}Q", extra[q + 4:q + 4 + hl // 8 * 8]), 0
                if usize == 0xFFFFFFFF:
                    usize, k = vals[k], k + 1
                if csize == 0xFFFFFFFF:
                    csize, k = vals[k], k + 1
                if off == 0xFFFFFFFF:
                    off = vals[k]
            q += 4 + hl
        if name in (TIF, TFW):
            members[name] = {"offset": off, "csize": csize, "size": usize, "crc": crc, "method": method}
        p += 46 + nl + el + cl
    missing = [n for n in (TIF, TFW) if n not in members]
    if missing:
        sys.exit(f"{NAME}: the zip at {ZIP_URL} no longer holds {', '.join(missing)}; NRCan has changed "
                 "the package. Stop and report it. Nothing was cached.")
    doc = {"fetched": date.today().isoformat(), "last_modified": modified, "size": size, "members": members}
    os.makedirs(DB, exist_ok=True)
    with open(INDEX + ".part", "w") as f:
        json.dump(doc, f, indent=1)
    os.replace(INDEX + ".part", INDEX)
    return doc


def _local(name):
    return os.path.join(DB, os.path.basename(name))


def _extract(name, quiet=False):
    """One member of the zip, inflated straight off the server into DB, its size and CRC checked.
    A failure leaves no partial file."""
    m = index()["members"][name]
    path, part = _local(name), _local(name) + ".part"
    os.makedirs(DB, exist_ok=True)
    try:
        head = _read_range(m["offset"], m["offset"] + 29, f"reading {name}")
        if head[:4] != b"PK\x03\x04":
            raise OSError("no zip entry where the directory places it; delete tools/db/depth/gsc/index.json")
        nl, el = struct.unpack("<HH", head[26:30])
        start = m["offset"] + 30 + nl + el
        if m["method"] not in (0, 8):
            raise OSError(f"compression method {m['method']}, which this reader does not inflate")
        inflate = zlib.decompressobj(-15) if m["method"] == 8 else None
        quiet = quiet or not sys.stderr.isatty()
        if not quiet:
            print(f"downloading {os.path.basename(name)} from NRCan, {m['csize'] / 1e9:.1f} GB "
                  f"({m['size'] / 1e9:.1f} GB unpacked) ...", file=sys.stderr, flush=True)
        got, crc, out, shown = 0, 0, 0, 0
        with _range(start, start + m["csize"] - 1, timeout=120) as r, open(part, "wb") as f:
            if r.status != 206:
                raise OSError(f"the server answered {r.status} to a byte range request")
            while chunk := r.read(1 << 20):
                got += len(chunk)
                data = inflate.decompress(chunk) if inflate else chunk
                crc, out = zlib.crc32(data, crc), out + len(data)
                f.write(data)
                if not quiet and got * 100 // m["csize"] > shown:
                    shown = got * 100 // m["csize"]
                    print(f"\r  {shown}%", end="", file=sys.stderr, flush=True)
            if inflate:
                data = inflate.flush()
                crc, out = zlib.crc32(data, crc), out + len(data)
                f.write(data)
        if not quiet:
            print(file=sys.stderr)
        if got != m["csize"] or out != m["size"]:
            raise OSError(f"{got} of {m['csize']} bytes arrived, {out} of {m['size']} unpacked")
        if crc != m["crc"]:
            raise OSError("the unpacked file fails the zip's CRC check")
    except (urllib.error.URLError, TimeoutError, OSError, zlib.error) as e:
        if os.path.exists(part):
            os.remove(part)
        sys.exit(f"{NAME}: download of {name} failed ({getattr(e, 'reason', e)}) from {ZIP_URL}. Nothing was cached.")
    os.replace(part, path)
    return path


def tif_path():
    """The local GeoTIFF and world file, downloaded when missing; the GeoTIFF's path."""
    for name in (TFW, TIF):
        if not os.path.exists(_local(name)):
            _extract(name)
    return _local(TIF)


_tile = None


def tile():
    """The GeoTIFF opened, georeferenced by its world file: the centre of its north-west pixel and
    the pixel size, turned into the grid's outer corner."""
    global _tile
    if _tile is None:
        t = Tile(tif_path())
        with open(_local(TFW)) as f:
            sx, _, _, sy, cx, cy = (float(v) for v in f.read().split())
        t.sx, t.sy = sx, -sy
        t.x0, t.y0 = cx - sx / 2, cy - sy / 2
        _tile = t
    return _tile


def in_box(lat, lon):
    s, w, n, e = BOX
    return s <= lat <= n and w <= lon <= e


def pixel(t, lat, lon):
    x, y = albers(lat, lon)
    return math.floor((t.y0 - y) / t.sy), math.floor((x - t.x0) / t.sx)


def has_data(lat, lon):
    """Whether the DEM holds a value at the point, downloading it the first time a point inside
    its extent is asked for."""
    if not in_box(lat, lon):
        return False
    t = tile()
    return t.value(*pixel(t, lat, lon)) is not None


def dem(lat, lon):
    """{elev, depth, datum, source, res_m, tile, row, col}: the elevation of the pixel the point
    falls in, signed, on CHS Chart Datum."""
    t = tile()
    row, col = pixel(t, lat, lon)
    elev = t.value(row, col)
    if elev is None:
        sys.exit(f"No {NAME} data at {lat}, {lon}: the grid holds no value there.")
    return {"elev": elev, "depth": -elev, "datum": DATUM, "source": t.name, "res_m": t.sx,
            "tile": t, "row": row, "col": col}


def answer(lat, lon):
    """The depth at a point below CHS Chart Datum: {water, depth, datum, detail, why, dem}. water
    is "sea", or "none" with why: a lake, inland of the coastline, or ground that dries at Chart
    Datum. The DEM carries lakes as land surface, so it gives no lake depth."""
    r = dem(lat, lon)
    out = {"dem": r, "depth": None, "datum": None, "detail": None, "why": None}
    lake = ncei.lake_at(lat, lon)
    if lake:
        return {**out, "water": "none",
                "why": f"in {lake[1]}, a lake; the {NAME} gives sea depths below {DATUM} alone, "
                       f"and reads {r['elev']:+.1f} m there"}
    if ncei.inland(lat, lon):
        return {**out, "water": "none",
                "why": f"inland of the coastline, at {r['elev']:+.1f} m in the DEM; check the coordinate"}
    if r["elev"] >= 0:
        return {**out, "water": "none",
                "why": f"dries at {r['elev']:+.1f} m above {DATUM} in the DEM: the intertidal shore or land; "
                       f"walk the coordinate out"}
    return {**out, "water": "sea", "depth": r["depth"], "datum": DATUM,
            "detail": f"elevation {r['elev']:.1f} m in the DEM, which carries its sea depths on {DATUM}"}


def fetch(boxes, workers):
    """The DEM, when any box touches its extent; the number that failed. It is one file, so
    workers has nothing to share out."""
    if not any(bs < BOX[2] and bn > BOX[0] and bw < BOX[3] and be > BOX[1] for bs, bw, bn, be in boxes):
        print("no box touches the DEM's extent; nothing to download")
        return 0
    if all(os.path.exists(_local(n)) for n in (TIF, TFW)):
        print("the DEM touches the boxes and is already here")
        return 0
    try:
        tif_path()
    except SystemExit as e:
        print(f"  {e}")
        return 1
    print(f"done; {os.path.basename(TIF)}, {os.path.getsize(_local(TIF)) / 1e9:.1f} GB")
    return 0


def verify(lat, lon, r):
    """The service's own pixel value at the point against the nine pixels at and around it. The
    service draws a narrow window around the point, so it answers at full resolution."""
    d = 0.0005
    q = {"geometry": f"{lon},{lat}", "geometryType": "esriGeometryPoint", "sr": "4326",
         "layers": f"all:{LIVE_LAYER}", "tolerance": "0", "returnGeometry": "false", "f": "json",
         "mapExtent": f"{lon - d},{lat - d},{lon + d},{lat + d}", "imageDisplay": "400,400,96"}
    url = LIVE_URL + "?" + urllib.parse.urlencode(q)
    doc = ncei._get_json(url, NAME)
    try:
        live = float(next(x for x in doc["results"] if x["layerId"] == LIVE_LAYER)["attributes"]["Pixel Value"])
    except (KeyError, StopIteration, ValueError, TypeError):
        sys.exit(f"{NAME}: no pixel value to compare with at {lat}, {lon} from {url}")
    t = r["tile"]
    around = [t.value(r["row"] + dr, r["col"] + dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1)]
    gap = min(abs(v - live) for v in around if v is not None)
    ok = gap <= 0.01
    print(f"  NRCan's live service: {live:.2f} m")
    print(f"  this file: {r['elev']:.2f} m at the point's pixel; nearest of the nine pixels around it "
          f"differs from the live value by {gap:.3f} m")
    if ok:
        print("  PASS")
    else:
        print(f"  FAIL: NRCan's data differs from this copy. Delete tools/db/depth/gsc/ to fetch it again.")
    return ok


# BC Albers coordinates from Esri's geometry service, NAD83 (EPSG:4269) to EPSG:3005, November 2026
_REFERENCE = [
    ((45.0, -126.0), (1000000.000, 0.000)),
    ((48.62, -123.3), (1199378.679, 404243.890)),
    ((49.25, -123.95), (1149369.887, 472568.943)),
    ((56.2, -134.8), (456424.653, 1278998.279)),
    ((47.2, -121.0), (1380111.823, 256447.342)),
]


def selftest():
    """The projection against the reference coordinates, passing within 1 mm."""
    ok = True
    for (lat, lon), (rx, ry) in _REFERENCE:
        x, y = albers(lat, lon)
        gap = math.hypot(x - rx, y - ry)
        ok = ok and gap <= 0.001
        print(f"  {lat}, {lon}: {x:.3f}, {y:.3f}; reference {rx:.3f}, {ry:.3f}; {gap * 1000:.2f} mm")
    print("  PASS" if ok else "  FAIL")
    return ok

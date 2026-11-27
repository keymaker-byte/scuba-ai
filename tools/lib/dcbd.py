"""The DCBD coastal bathymetry of Bonaire (Meesters 2020), for the depth tool and the current
tool's seabed: the one 2 m GeoTIFF taken out of DCBD's zip and kept on this machine, the UTM zone
19N projection it is gridded on, and the depth at a point, a plain observed depth (datum NONE)."""
import json
import bisect
import math
import os
import struct
import sys
import urllib.error
import urllib.request
import zipfile
from datetime import date

from lib import ncei
from lib.dem_tiles import Tile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


DB = os.path.join(ROOT, "tools", "db", "depth", "dcbd")


INDEX = os.path.join(DB, "index.json")


# Meesters, E. (2020), "Coastal bathymetry Bonaire", Dutch Caribbean Biodiversity Database resource 2869.
PAGE_URL = "https://www.dcbd.nl/resource/2869"


ZIP_URL = "https://www.dcbd.nl/reposerver/api/file/3421"


MEMBER = "bonaire_depth_hires2.tif"   # the depth grid inside the zip


TIF = os.path.join(DB, MEMBER)


UTM_ZONE = 19   # the grid's own projection: WGS 84 / UTM zone 19N (EPSG:32619)


BOX = (12.0098, -68.4360, 12.3354, -68.1869)   # the grid's extent, S W N E, from its corners


DATUM = "the sea surface"   # the grid's zero: about sea level, the shoreline at zero


NAME = "DCBD coastal bathymetry of Bonaire"


SPREAD_M = 10    # the spread of depths reported around a point


SEARCH_M = 100   # how far a point with no data searches for the nearest pixel that has some


UA = ncei.UA


# --- WGS 84 to UTM (Krüger series, sub-millimetre inside a zone) ---------------------------

def utm(lat, lon, zone=UTM_ZONE):
    a, f, k0 = 6378137.0, 1 / 298.257223563, 0.9996
    n = f / (2 - f)
    A = a / (1 + n) * (1 + n ** 2 / 4 + n ** 4 / 64)
    al = (n / 2 - 2 * n ** 2 / 3 + 5 * n ** 3 / 16 + 41 * n ** 4 / 180,
          13 * n ** 2 / 48 - 3 * n ** 3 / 5 + 557 * n ** 4 / 1440,
          61 * n ** 3 / 240 - 103 * n ** 4 / 140,
          49561 * n ** 4 / 161280)
    phi, lam = math.radians(lat), math.radians(lon - (zone * 6 - 183))
    e = 2 * math.sqrt(n) / (1 + n)
    t = math.sinh(math.atanh(math.sin(phi)) - e * math.atanh(e * math.sin(phi)))
    xi, eta = math.atan2(t, math.cos(lam)), math.atanh(math.sin(lam) / math.sqrt(1 + t * t))
    x = eta + sum(al[j] * math.cos(2 * (j + 1) * xi) * math.sinh(2 * (j + 1) * eta) for j in range(4))
    y = xi + sum(al[j] * math.sin(2 * (j + 1) * xi) * math.cosh(2 * (j + 1) * eta) for j in range(4))
    return 500000 + k0 * A * x, k0 * A * y


def from_utm(x, y, zone=UTM_ZONE):
    """(lat, lon) of UTM (x, y), by Newton's method on utm(), to well under a millimetre."""
    lat, lon = y / 110600, zone * 6 - 183 + (x - 500000) / 111000
    for _ in range(6):
        x1, y1 = utm(lat, lon, zone)
        h = 1e-6
        xa, ya = utm(lat + h, lon, zone)
        xb, yb = utm(lat, lon + h, zone)
        a, b, c, d = (xa - x1) / h, (xb - x1) / h, (ya - y1) / h, (yb - y1) / h
        det = a * d - b * c
        ex, ey = x - x1, y - y1
        lat += (d * ex - b * ey) / det
        lon += (a * ey - c * ex) / det
    return lat, lon


# --- The zip on DCBD's server, and the grid taken out of it ---------------------------------

def _zip_member(data, total):
    """(size, crc) of MEMBER from a zip's central directory, given the zip's last bytes and its
    whole size."""
    end = data.rfind(b"PK\x05\x06")
    if end < 0:
        raise OSError("no zip directory at the end of the file")
    cd_size, cd_off = struct.unpack("<II", data[end + 12:end + 20])
    p = cd_off - (total - len(data))
    if p < 0:
        raise OSError("the zip's directory is larger than the bytes read")
    while data[p:p + 4] == b"PK\x01\x02":
        crc, _, usize, nl, el, cl = struct.unpack("<IIIHHH", data[p + 16:p + 34])
        if data[p + 46:p + 46 + nl].decode("utf8", "replace") == MEMBER:
            return usize, crc
        p += 46 + nl + el + cl
    raise OSError(f"the zip no longer holds {MEMBER}")


def _download():
    """The zip, its grid taken out and checked against the zip's own size and CRC, and the index
    of what was taken. A failure leaves no partial file."""
    os.makedirs(DB, exist_ok=True)
    part, tif_part = os.path.join(DB, "download.zip.part"), TIF + ".part"
    quiet = not sys.stderr.isatty()
    if not quiet:
        print(f"downloading the {NAME} from DCBD, about 34 MB ...", file=sys.stderr, flush=True)
    try:
        req = urllib.request.Request(ZIP_URL, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=300) as r, open(part, "wb") as f:
            size = int(r.headers.get("Content-Length") or 0)
            while chunk := r.read(1 << 20):
                f.write(chunk)
        got = os.path.getsize(part)
        if size and got != size:
            raise OSError(f"{got} of {size} bytes arrived")
        with zipfile.ZipFile(part) as z:
            info = z.getinfo(MEMBER)
            with z.open(info) as src, open(tif_part, "wb") as dst:   # zipfile checks the CRC as it reads
                while chunk := src.read(1 << 20):
                    dst.write(chunk)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, zipfile.BadZipFile, KeyError) as e:
        for p in (part, tif_part):
            if os.path.exists(p):
                os.remove(p)
        sys.exit(f"{NAME}: download failed ({getattr(e, 'reason', e)}) from {ZIP_URL}. Nothing was cached.")
    doc = {"fetched": date.today().isoformat(), "url": ZIP_URL, "zip_size": got,
           "member": {"name": MEMBER, "size": info.file_size, "crc": info.CRC}}
    os.replace(tif_part, TIF)
    with open(INDEX + ".part", "w") as f:
        json.dump(doc, f, indent=1)
    os.replace(INDEX + ".part", INDEX)
    os.remove(part)


def tif_path():
    """The local GeoTIFF, downloaded with its index when either is missing."""
    if not (os.path.exists(TIF) and os.path.exists(INDEX)):
        _download()
    return TIF


def index():
    tif_path()
    with open(INDEX) as f:
        return json.load(f)


_tile = None


def tile():
    """The GeoTIFF opened; its own tags georeference it in UTM metres."""
    global _tile
    if _tile is None:
        _tile = Tile(tif_path())
    return _tile


def in_box(lat, lon):
    s, w, n, e = BOX
    return s <= lat <= n and w <= lon <= e


def pixel(t, lat, lon):
    return pixel_utm(t, *utm(lat, lon))


def pixel_utm(t, x, y):
    """(row, col) of the pixel holding UTM zone 19N (x, y)."""
    return math.floor((t.y0 - y) / t.sy), math.floor((x - t.x0) / t.sx)


def centre(t, row, col):
    return t.x0 + (col + 0.5) * t.sx, t.y0 - (row + 0.5) * t.sy


def covers(lat, lon):
    """Whether the point lies on the grid, downloading it the first time a point inside its
    extent is asked for. A pixel on the grid with no data still answers, with the reason."""
    if not in_box(lat, lon):
        return False
    t = tile()
    row, col = pixel(t, lat, lon)
    return 0 <= row < t.h and 0 <= col < t.w


def elevation(lat, lon):
    """Signed elevation in metres, negative under water, or None off the grid or where it holds
    no data: the current tool's seabed."""
    if not in_box(lat, lon):
        return None
    t = tile()
    return t.fast(*pixel(t, lat, lon))


COMPASS = "N NNE NE ENE E ESE SE SSE S SSW SW WSW W WNW NW NNW".split()


def _bearing(dx, dy):
    b = math.degrees(math.atan2(dx, dy)) % 360
    return f"{b:.0f}° ({COMPASS[round(b / 22.5) % 16]})"


_COLS = {}        # (row, wet) -> sorted columns of the row holding data (under water, with wet)
COLS_CAP = 20000


def _cols(t, row, wet):
    key = (row, wet)
    got = _COLS.get(key)
    if got is None:
        got = []
        if 0 <= row < t.h and t.th == 1:
            arr = t.floats(row)[:t.w]
            nd = t.nodata
            got = [c for c, v in enumerate(arr)
                   if v == v and (nd is None or abs(v - nd) >= 1e-3) and not (wet and v >= 0)]
        elif 0 <= row < t.h:
            got = [c for c in range(t.w) if (v := t.fast(row, c)) is not None and not (wet and v >= 0)]
        if len(_COLS) >= COLS_CAP:
            del _COLS[next(iter(_COLS))]
        _COLS[key] = got
    return got


def nearest_data(t, x, y, row, col, limit_m, wet=False):
    """Nearest pixel with data within limit_m of (x, y), or with wet the nearest under water:
    (distance, dx, dy, value) or None. Searched over the square of rows and columns within
    limit_m of the pixel (row, col), that pixel itself left out, a row at a time: each row's
    nearest column with data, from the row's sorted columns."""
    k = int(limit_m / t.sx) + 1
    best = None
    for rr in range(row - k, row + k + 1):
        cy = t.y0 - (rr + 0.5) * t.sy
        dy = cy - y
        if abs(dy) > limit_m or best is not None and abs(dy) >= best[0]:
            continue
        cols = _cols(t, rr, wet)
        if not cols:
            continue
        cx = (x - t.x0) / t.sx - 0.5          # the point's fractional column
        i = bisect.bisect_left(cols, cx)
        for j in (i - 2, i - 1, i, i + 1):
            if 0 <= j < len(cols) and col - k <= cols[j] <= col + k and not (rr == row and cols[j] == col):
                cc = cols[j]
                px = t.x0 + (cc + 0.5) * t.sx
                d = math.hypot(px - x, dy)
                if d <= limit_m and (best is None or d < best[0]):
                    best = (d, px - x, dy, t.fast(rr, cc))
        # the nearest column may sit outside the square's columns on one side: the square's edge
        # column nearest the point is then the row's best within the square
        for edge in (col - k, col + k):
            j = bisect.bisect_left(cols, edge)
            if 0 <= j < len(cols) and cols[j] == edge:
                px = t.x0 + (edge + 0.5) * t.sx
                d = math.hypot(px - x, dy)
                if d <= limit_m and (best is None or d < best[0]):
                    best = (d, px - x, dy, t.fast(rr, edge))
    return best


def spread(t, x, y, row, col, radius_m):
    """(shallowest, deepest, share without data) of the pixels within radius_m, depths in metres
    below the surface; None where none holds data."""
    k = int(radius_m / t.sx)
    vals = [t.fast(rr, cc) for rr in range(row - k, row + k + 1) for cc in range(col - k, col + k + 1)
            if math.hypot(centre(t, rr, cc)[0] - x, centre(t, rr, cc)[1] - y) <= radius_m]
    have = [v for v in vals if v is not None]
    if not have:
        return None
    return -max(have), -min(have), (len(vals) - len(have)) / len(vals)


def answer(lat, lon):
    """The depth at a point below the sea surface, a plain observed depth: {water, depth, datum,
    detail, why, dem}. water is "sea", or "none" with why: a pixel with no data (land, water
    deeper than the survey reached, or unsurveyed), with the nearest pixel that has some, or ground
    at or above the surface."""
    t = tile()
    x, y = utm(lat, lon)
    row, col = pixel(t, lat, lon)
    elev = t.fast(row, col)
    r = {"elev": elev, "source": "2 m grid", "res_m": t.sx, "tile": t, "row": row, "col": col}
    out = {"dem": r, "depth": None, "datum": None, "detail": None, "why": None}
    if elev is None:
        near = nearest_data(t, x, y, row, col, SEARCH_M)
        where = (f"; the nearest data is {near[0]:.0f} m toward {_bearing(near[1], near[2])}, "
                 + (f"seabed {-near[3]:.1f} m" if near[3] < 0 else f"{near[3]:+.1f} m, above water")
                 if near else f"; none within {SEARCH_M} m")
        return {**out, "water": "none", "nodata": True,
                "why": f"no survey data at this pixel (land, deeper than the survey reached, or unsurveyed){where}"}
    if elev >= 0:
        return {**out, "water": "none", "why": f"above water, {elev:+.1f} m in the grid; walk the coordinate out"}
    s = spread(t, x, y, row, col, SPREAD_M)
    around = f"; within {SPREAD_M} m, {s[0]:.1f} to {s[1]:.1f} m"
    if s[2]:
        around += f", {s[2]:.0%} of it without data (land, deeper, or unsurveyed)"
    return {**out, "water": "sea", "depth": -elev, "datum": DATUM,
            "detail": f"elevation {elev:.1f} m in the grid, whose zero is about sea level with the shoreline "
                      f"at zero{around}"}


def fetch(boxes, workers):
    """The grid, when any box touches its extent; the number that failed. It is one file, so
    workers has nothing to share out."""
    if not any(bs < BOX[2] and bn > BOX[0] and bw < BOX[3] and be > BOX[1] for bs, bw, bn, be in boxes):
        print("no box touches the grid's extent; nothing to download")
        return 0
    if os.path.exists(TIF) and os.path.exists(INDEX):
        print("the grid touches the boxes and is already here")
        return 0
    try:
        tif_path()
    except SystemExit as e:
        print(f"  {e}")
        return 1
    print(f"done; {MEMBER}, {os.path.getsize(TIF) / 1e6:.0f} MB")
    return 0


def verify(lat, lon, r):
    """DCBD publishes the grid as a file and serves no depth at a point, so the check is on the
    file: the zip DCBD serves now, its size and the grid's size and CRC from its directory, read
    with one byte range request, against the copy on this machine."""
    have = index()
    try:
        req = urllib.request.Request(ZIP_URL, headers={"User-Agent": UA, "Range": "bytes=-65536"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            if resp.status != 206:
                raise OSError(f"the server answered {resp.status} to a byte range request")
            total = int(resp.headers["Content-Range"].rsplit("/", 1)[1])
            size, crc = _zip_member(resp.read(), total)
    except (urllib.error.URLError, TimeoutError, OSError, KeyError, ValueError, IndexError) as e:
        sys.exit(f"{NAME}: reading the zip's directory failed ({getattr(e, 'reason', e)}) for {ZIP_URL}")
    m = have["member"]
    ok = (total, size, crc) == (have["zip_size"], m["size"], m["crc"])
    print(f"  DCBD's zip now: {total} bytes, {MEMBER} {size} bytes, CRC {crc:08x}")
    print(f"  this copy, fetched {have['fetched']}: {have['zip_size']} bytes, {MEMBER} {m['size']} bytes, "
          f"CRC {m['crc']:08x}")
    if ok:
        print("  PASS")
    else:
        print(f"  FAIL: DCBD has replaced the grid. Delete tools/db/depth/dcbd/ to fetch it again.")
    return ok


# UTM zone 19N coordinates from Esri's geometry service, WGS 84 (EPSG:4326) to EPSG:32619, November 2026
_REFERENCE = [
    ((12.15, -68.4), (565280.213, 1343212.374)),
    ((12.03, -68.28), (578371.763, 1329973.618)),
    ((12.3, -68.24), (582642.512, 1359844.174)),
    ((12.38, -68.3), (576094.693, 1368673.528)),
    ((0.0, -69.0), (500000.000, 0.000)),
]


def selftest():
    """The projection against the reference coordinates, passing within 1 mm."""
    ok = True
    for (lat, lon), (rx, ry) in _REFERENCE:
        x, y = utm(lat, lon)
        gap = math.hypot(x - rx, y - ry)
        ok = ok and gap <= 0.001
        print(f"  {lat}, {lon}: {x:.3f}, {y:.3f}; reference {rx:.3f}, {ry:.3f}; {gap * 1000:.2f} mm")
    print("  PASS" if ok else "  FAIL")
    return ok

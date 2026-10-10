#!/usr/bin/env python3
"""Seabed depth on Bonaire's coastal reef from the 2 m coastal bathymetry (Meesters 2020, DCBD).

  dcbd_depth.py at LAT LON [--radius M]                     depth at a point, and the spread around it
  dcbd_depth.py transect LAT1 LON1 LAT2 LON2 [--step M]     depth every few metres along a line

The grid covers Bonaire and Klein Bonaire from the shoreline out to as deep as the survey reached,
20 m at most and often less. Land, deeper water and anything unsurveyed hold no data; the tool then
reports the nearest pixel that has some.
"""
import argparse
import json
import math
import os
import struct
import sys
import urllib.request
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "tools", "db")
TIF = os.path.join(DB, "dcbd_bonaire_depth.tif")
# Meesters, E. (2020), "Coastal bathymetry Bonaire", Dutch Caribbean Biodiversity Database resource 2869.
ZIP_URL = "https://www.dcbd.nl/reposerver/api/file/3421"
ZIP_MEMBER = "bonaire_depth_hires2.tif"
UTM_ZONE = 19  # the grid's own projection: WGS 84 / UTM zone 19N (EPSG 32619)


def _cfg(key, default):
    """Read this tool's section of tool-config.json; missing file or key -> default."""
    try:
        with open(os.path.join(ROOT, "tool-config.json")) as f:
            return json.load(f).get("dcbd_depth", {}).get(key, default)
    except (OSError, ValueError):
        return default


# --- download -----------------------------------------------------------------------------

def _ensure():
    if os.path.exists(TIF):
        return
    os.makedirs(DB, exist_ok=True)
    part = TIF + ".zip.part"
    print(f"downloading {ZIP_URL} (about 34 MB) ...", file=sys.stderr)
    req = urllib.request.Request(ZIP_URL, headers={"User-Agent": "Mozilla/5.0 (dcbd_depth.py)"})
    try:
        with urllib.request.urlopen(req, timeout=300) as r, open(part, "wb") as f:
            while chunk := r.read(1 << 20):
                f.write(chunk)
        with zipfile.ZipFile(part) as z, z.open(ZIP_MEMBER) as src, open(TIF + ".part", "wb") as dst:
            while chunk := src.read(1 << 20):
                dst.write(chunk)
    except (OSError, zipfile.BadZipFile, KeyError) as e:
        for p in (part, TIF + ".part"):
            if os.path.exists(p):
                os.remove(p)
        sys.exit(f"download failed ({e}); the Bonaire bathymetry grid is needed before any depth.")
    os.replace(TIF + ".part", TIF)
    os.remove(part)


# --- GeoTIFF reader: one float band, uncompressed or LZW, strip layout --------------------

def _lzw(data):
    """Decode one TIFF LZW strip (MSB-first codes, early change)."""
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


class Grid:
    TYPES = {1: ("B", 1), 2: ("s", 1), 3: ("H", 2), 4: ("I", 4), 11: ("f", 4), 12: ("d", 8), 16: ("Q", 8)}

    def __init__(self, path):
        self.f = open(path, "rb")
        head = self.f.read(8)
        if head[:4] not in (b"II*\0", b"MM\0*"):
            sys.exit(f"{path} is not a TIFF; delete it to fetch the grid again.")
        self.bo = "<" if head[:2] == b"II" else ">"
        (off,) = struct.unpack(self.bo + "I", head[4:])
        tags = self._ifd(off)
        self.width, self.height = tags[256][0], tags[257][0]
        compression = tags.get(259, (1,))[0]
        if tags.get(258, (0,))[0] != 32 or tags.get(339, (0,))[0] != 3 or tags.get(277, (1,))[0] != 1:
            sys.exit("unexpected TIFF layout: expected a single 32-bit float band.")
        if compression not in (1, 5) or tags.get(317, (1,))[0] != 1 or 322 in tags:
            sys.exit("unexpected TIFF layout: expected strips, uncompressed or LZW, no predictor.")
        self.lzw = compression == 5
        self.rps = tags.get(278, (self.height,))[0]
        self.offsets, self.counts = tags[273], tags[279]
        sx, sy = tags[33550][:2]
        _, _, _, x0, y0, _ = tags[33922]
        self.x0, self.y0, self.sx, self.sy = x0, y0, sx, sy
        self.nodata = float(tags[42113].rstrip(b"\0")) if 42113 in tags else None
        self.fmt = self.bo + f"{self.width}f"
        self.rows = {}

    def _ifd(self, off):
        self.f.seek(off)
        (n,) = struct.unpack(self.bo + "H", self.f.read(2))
        raw = self.f.read(12 * n)
        tags = {}
        for i in range(n):
            tag, typ, cnt = struct.unpack(self.bo + "HHI", raw[12 * i:12 * i + 8])
            if typ not in self.TYPES:
                continue
            ch, size = self.TYPES[typ]
            val = raw[12 * i + 8:12 * i + 12]
            if size * cnt > 4:
                (ptr,) = struct.unpack(self.bo + "I", val)
                here = self.f.tell()
                self.f.seek(ptr)
                val = self.f.read(size * cnt)
                self.f.seek(here)
            tags[tag] = val[:cnt] if typ == 2 else struct.unpack(self.bo + ch * cnt, val[:size * cnt])
        return tags

    def row(self, r):
        if r not in self.rows:
            s = r // self.rps
            self.f.seek(self.offsets[s])
            data = self.f.read(self.counts[s])
            if self.lzw:
                data = _lzw(data)
            n = self.width * 4
            k = r - s * self.rps
            self.rows[r] = struct.unpack(self.fmt, data[k * n:(k + 1) * n])
        return self.rows[r]

    def pixel(self, x, y):
        """Pixel (row, col) holding UTM x, y, or None when it falls outside the grid."""
        c, r = math.floor((x - self.x0) / self.sx), math.floor((self.y0 - y) / self.sy)
        if 0 <= r < self.height and 0 <= c < self.width:
            return r, c
        return None

    def value(self, r, c):
        """Signed elevation in metres (negative under water), or None where there is no data."""
        v = self.row(r)[c]
        if v != v or (self.nodata is not None and abs(v - self.nodata) <= abs(self.nodata) * 1e-6) or v < -1e30:
            return None
        return v

    def centre(self, r, c):
        return self.x0 + (c + 0.5) * self.sx, self.y0 - (r + 0.5) * self.sy


def grid():
    _ensure()
    return Grid(TIF)


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


# --- queries ------------------------------------------------------------------------------

COMPASS = "N NNE NE ENE E ESE SE SSE S SSW SW WSW W WNW NW NNW".split()


def _bearing(dx, dy):
    b = math.degrees(math.atan2(dx, dy)) % 360
    return f"{b:.0f}° ({COMPASS[round(b / 22.5) % 16]})"


def _depth(v):
    return f"+{v:.1f} m, ABOVE WATER" if v > 0 else f"{-v:.1f} m"


def nearest_data(g, x, y, r, c, limit_m):
    """Nearest pixel with data within limit_m of (x, y): (distance, dx, dy, value) or None."""
    best = None
    steps = int(limit_m / g.sx) + 1
    for ring in range(1, steps + 1):
        if best and (ring - 1) * g.sx > best[0]:
            break
        for rr in range(r - ring, r + ring + 1):
            if not 0 <= rr < g.height:
                continue
            edge = rr in (r - ring, r + ring)
            for cc in (range(c - ring, c + ring + 1) if edge else (c - ring, c + ring)):
                if not 0 <= cc < g.width:
                    continue
                v = g.value(rr, cc)
                if v is None:
                    continue
                px, py = g.centre(rr, cc)
                d = math.hypot(px - x, py - y)
                if d <= limit_m and (best is None or d < best[0]):
                    best = (d, px - x, py - y, v)
    return best


def cmd_at(a):
    g = grid()
    x, y = utm(a.lat, a.lon)
    print(f"{a.lat}, {a.lon}")
    p = g.pixel(x, y)
    if p is None:
        sys.exit("  outside the Bonaire coastal grid: no data here. Use emodnet_depth for open water.")
    r, c = p
    v = g.value(r, c)
    if v is not None:
        print(f"  seabed {_depth(v)}  [DCBD coastal bathymetry, 2 m grid]")
    else:
        print("  no data at this pixel: land, water deeper than the survey reached, or unsurveyed")
        near = nearest_data(g, x, y, r, c, a.search)
        if near:
            d, dx, dy, nv = near
            print(f"  nearest data {d:.0f} m away toward {_bearing(dx, dy)}, seabed {_depth(nv)}")
        else:
            print(f"  no data within {a.search:.0f} m: inland, open water past the reef, or unsurveyed")
    k = int(a.radius / g.sx)
    vals = []
    for rr in range(max(0, r - k), min(g.height, r + k + 1)):
        for cc in range(max(0, c - k), min(g.width, c + k + 1)):
            px, py = g.centre(rr, cc)
            if math.hypot(px - x, py - y) <= a.radius:
                vals.append(g.value(rr, cc))
    have = [w for w in vals if w is not None]
    if have:
        line = f"  within {a.radius:.0f} m: {-max(have):.1f} to {-min(have):.1f} m"
        if len(have) < len(vals):
            line += f", {100 * (len(vals) - len(have)) / len(vals):.0f}% of it without data (land, deeper, or unsurveyed)"
        print(line)


def cmd_transect(a):
    g = grid()
    x1, y1 = utm(a.lat1, a.lon1)
    x2, y2 = utm(a.lat2, a.lon2)
    length = math.hypot(x2 - x1, y2 - y1)
    n = max(1, round(length / a.step))
    print(f"{a.lat1}, {a.lon1} to {a.lat2}, {a.lon2}: {length:.0f} m toward {_bearing(x2 - x1, y2 - y1)}")
    print(f"  {'dist':>6}  {'lat':>10}  {'lon':>11}  seabed")
    for i in range(n + 1):
        t = i / n
        lat, lon = a.lat1 + t * (a.lat2 - a.lat1), a.lon1 + t * (a.lon2 - a.lon1)
        p = g.pixel(*utm(lat, lon))
        v = g.value(*p) if p else None
        shown = _depth(v) if v is not None else ("outside grid" if p is None else "no data (land, deeper, or unsurveyed)")
        print(f"  {t * length:5.0f}m  {lat:10.6f}  {lon:11.6f}  {shown}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("at", help="depth at a point, and the spread around it")
    s.add_argument("lat", type=float)
    s.add_argument("lon", type=float)
    s.add_argument("--radius", type=float, default=_cfg("radius_m", 10),
                   help="metres around the point to report the shallowest and deepest pixel (default 10)")
    s.add_argument("--search", type=float, default=_cfg("search_m", 100),
                   help="on a pixel with no data, metres to search for the nearest one with data (default 100)")
    s.set_defaults(fn=cmd_at)
    s = sub.add_parser("transect", help="depth every few metres along a straight line")
    for k in ("lat1", "lon1", "lat2", "lon2"):
        s.add_argument(k, type=float)
    s.add_argument("--step", type=float, default=_cfg("step_m", 10), help="metres between samples (default 10)")
    s.set_defaults(fn=cmd_transect)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Seabed depth at a coordinate from NOAA NCEI's ninth arc-second coastal DEM, read from
tiles kept on this machine.

  ncei_depth.py LAT LON                     depth below NAVD88 (~mean sea level)
  ncei_depth.py LAT LON --mllw              also below MLLW, the site file figure
  ncei_depth.py LAT LON --mllw --region R   pick the VDatum region explicitly
  ncei_depth.py LAT LON --verify            compare with NCEI's live service
  ncei_depth.py --fetch S W N E             download every tile touching a box, ahead of time

The data lives in tools/db/ncei_depth/: NOAA's tile list, one GeoTIFF per quarter-degree
tile (about 200 MB), and the NAVD88-to-MLLW offsets VDatum has answered. A tile is downloaded
the first time a point inside it is asked for, and an offset the first time a place is.
Delete a file, or the folder, to fetch NOAA's current data again.
"""
import argparse
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
    a = p.parse_args()
    region = a.region or _cfg("default_region")
    if a.fetch:
        sys.exit(1 if fetch(a.fetch, a.workers) else 0)
    if a.lat is None or a.lon is None:
        p.error("give LAT LON, or --fetch S W N E")

    r = dem(a.lat, a.lon)
    print(f"{a.lat}, {a.lon}")
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

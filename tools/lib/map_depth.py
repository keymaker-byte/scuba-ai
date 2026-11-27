"""The map viewer's depth layer, written by map_export.py: one pyramid of tiles over every area in
map/coverage.json, each pixel the depth the depth tool answers at its centre, kept at the
resolution of the source that answers there.

A tile is a 256 x 256 RGB PNG. Red (high byte) and green (low byte) hold v, the depth below the
pixel's own reference: (v - 1) * SCALE + SHALLOWEST, so ground up to -SHALLOWEST above the
reference is kept for the tide to cover; v = 0, transparent through the PNG's tRNS chunk, is no
depth. Blue names the water: WATER_TIDES' index for the sea, whose tide family the viewer adds at
its moment, or LAKE0 + k for the k-th lake of the layer's table, whose depth is below the lake's own
surface. The viewer adds no reference of its own: the total depth is the seabed plus the tide.

Each source is drawn to the zoom its own resolution calls for (SOURCE_ZOOM): every area is
rendered at BASE_ZOOM, and a tile is rendered again one zoom finer, four children, wherever a
source finer than the tile answers inside it. The viewer reads, at any point, the deepest tile
there. Lower zooms are means of the base zoom.

Two ways to read a pixel, giving the same answer. Around Bonaire, every pixel is the depth tool's
own answer_on(). Elsewhere a tile reads the NCEI DEM, the NCEI to GSC seam and the GSC DEM the way
answer_on() reads them, a row of pixels at a time: the tiles' pixels through their decoded blocks,
OpenStreetMap's coastline and VDatum's sub-region polygons by row crossings, NAVD 88's height above
MLLW bilinear between the exact figure every LATTICE pixels. Sample pixels of every source and lake
are read back through answer_on() before the layer's description is written, so the two cannot
drift apart unseen."""
import math
import multiprocessing
import os
import random
import shutil
import struct
import sys
import time
import zlib
from bisect import bisect_left, bisect_right
from datetime import date

from lib import datums, dcbd, depth as chain, gsc, ncei, nlhs, nlhs_1970, shapes, vdatum
from lib.ncei import JOIN_ZOOM, LAKE_MIN, TILE_DEG, _Grid, _join, _lake_record, _Rows, _tile_lat, lake_level

WORKSPACE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(WORKSPACE, "map", "depth")
TILES = os.path.join(OUT, "tiles")
META = os.path.join(OUT, "depth.js")

SCALE = 0.1          # m a step of v
SHALLOWEST = -10.0   # m: the highest ground kept, above the pixel's reference, for the tide to cover
BASE_ZOOM = 12       # every area is rendered here first
MIN_ZOOM = 8         # the coarsest zoom, means of the base zoom
LATTICE = 16         # pixels between the exact NAVD 88 to MLLW figures a tile interpolates
SEAM_M = chain.NceiGscSeam.BAND_M
FETCH_PAD = 0.01                  # degrees past each box the data is fetched for, about 1 km
SEAM_STEP = 0.02                  # degrees between the points the seam's CHS stations are read for
CHECKS_PER_SOURCE = 16
CHECK_MIN_DEPTH = 0.5   # m: check pixels at least this deep, where the depth tool answers a depth

# The tide family of each kind of sea, by the datum its depth is below: the viewer adds that family's
# tide, and none on NONE. Index 0 is no water.
WATER_TIDES = [None, datums.MLLW, datums.CHS, datums.NONE]
WATER_OF = {k: i for i, k in enumerate(WATER_TIDES) if k}
LAKE0 = len(WATER_TIDES)      # blue LAKE0 + k: the k-th lake of the table
EMPTY = 255                   # a lake outline with no level: never drawn

# Each source at the zoom its resolution calls for: about its own pixel, or finer.
SOURCE_ZOOM = {
    chain.Ncei.name: 14,          # 3 m, drawn at about 6 m as before
    chain.NceiGscSeam.name: 14,   # the band past NCEI's edge, at NCEI's zoom
    gsc.NAME: 13,                 # 10 m, drawn at about 12 m
    dcbd.NAME: 16,                # 2 m, drawn at about 2.3 m
    chain.DCBD_NAVY.name: 14,     # the 40 m band past DCBD's edge, at the 2019 survey's zoom
    nlhs.NAME: 14,                # 20 m cells, drawn at about 9 m
    chain.LEGACY_SEAM.name: 13,   # the 100 m band past the finer surveys
    nlhs_1970.NAME: 12,           # soundings hundreds of metres apart
}
LAKE_SOURCE = chain.Ncei.name    # lakes come from the NCEI DEM alone


def log(m):
    print(m, file=sys.stderr, flush=True)


# --- tiles ------------------------------------------------------------------------------------

def png(vals, kinds):
    """256 x 256 RGB PNG of 16-bit values (R high, G low) and the water in B; value 0 with water 0
    is transparent. Rows Up-filtered."""
    rgb = bytearray(3 * 65536)
    rgb[0::3] = bytes(v >> 8 for v in vals)
    rgb[1::3] = bytes(v & 255 for v in vals)
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


def unpng(path):
    """Values and waters of a tile png() wrote."""
    with open(path, "rb") as f:
        data = f.read()
    pos, idat = 8, b""
    while pos < len(data):
        n = struct.unpack(">I", data[pos:pos + 4])[0]
        if data[pos + 4:pos + 8] == b"IDAT":
            idat += data[pos + 8:pos + 8 + n]
        pos += 12 + n
    raw, prev, vals, kinds = zlib.decompress(idat), bytes(768), [], bytearray()
    for y in range(256):
        line = bytes((a + b) & 255 for a, b in zip(raw[y * 769 + 1:(y + 1) * 769], prev))
        prev = line
        vals.extend((line[i] << 8) | line[i + 1] for i in range(0, 768, 3))
        kinds.extend(line[2::3])
    return vals, kinds


def write_tile(z, x, y, vals, kinds):
    d = os.path.join(TILES, str(z), str(x))
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, f"{y}.png"), "wb") as f:
        f.write(png(vals, kinds))


def encode(d):
    """v for a depth below the pixel's reference, 0 for none or past the range."""
    if d is None or d < SHALLOWEST:
        return 0
    v = round((d - SHALLOWEST) / SCALE) + 1
    return v if v <= 65535 else 65535


def decode(v):
    return (v - 1) * SCALE + SHALLOWEST


def centres(z, x, y):
    n = 2 ** z
    lats = [_tile_lat(y + (p + 0.5) / 256, n) for p in range(256)]
    lons = [(x + (p + 0.5) / 256) / n * 360 - 180 for p in range(256)]
    return lats, lons


def tile_box(z, x, y):
    n = 2 ** z
    return _tile_lat(y + 1, n), x / n * 360 - 180, _tile_lat(y, n), (x + 1) / n * 360 - 180


def clip(boxes, lats, lons):
    """Which pixels lie inside the boxes: None for none, True for all, else 65536 flags."""
    spans = []
    for s, w, n, e in boxes:
        rows = [i for i, la in enumerate(lats) if s <= la <= n]
        cols = [i for i, lo in enumerate(lons) if w <= lo <= e]
        if rows and cols:
            spans.append((rows[0], rows[-1], cols[0], cols[-1]))
    if not spans:
        return None
    if any(r0 == 0 and r1 == 255 and c0 == 0 and c1 == 255 for r0, r1, c0, c1 in spans):
        return True
    mask = bytearray(65536)
    for r0, r1, c0, c1 in spans:
        for r in range(r0, r1 + 1):
            mask[r * 256 + c0:r * 256 + c1 + 1] = b"\x01" * (c1 - c0 + 1)
    return mask


# --- the lakes the NCEI DEM answers in --------------------------------------------------------

class Lakes:
    """Every HydroLAKES outline touching NCEI's water in the coverage, with the level the NCEI DEM
    gives it: a lake with a level by its place in the table (LAKE0, LAKE0 + 1, ...), any other EMPTY;
    and the water joined to each lake with a level, by JOIN_ZOOM pixel."""

    def __init__(self, boxes):
        grid = _Grid()
        found, seen = [], set()
        for S, W, N, E in boxes:
            km = math.hypot((N - S) * 111.2, (E - W) * 111.2 * math.cos(math.radians((S + N) / 2))) / 2
            for rec, rings in shapes.polygons("lakes", (S + N) / 2, (W + E) / 2, km):
                xs = [p[0] for r in rings for p in r]
                ys = [p[1] for r in rings for p in r]
                if max(ys) < S or min(ys) > N or max(xs) < W or min(xs) > E:
                    continue
                hid, name, info = _lake_record(rec)
                if hid in seen:
                    continue
                seen.add(hid)
                lvl = lake_level(hid, rings, info, grid)["level"]
                found.append((min(xs), min(ys), max(xs), max(ys), rings, hid, name, lvl))
        levelled = sorted((L for L in found if L[7] is not None), key=lambda L: L[5])
        if LAKE0 + len(levelled) >= EMPTY:
            sys.exit(f"{len(levelled)} lakes with a level: a pixel's water is a byte, which holds {EMPTY - LAKE0 - 1}.")
        self.table = [{"name": L[6].split(" (HydroLAKES")[0] if "(" in L[6] else "Lake", "level": round(L[7], 2)}
                      for L in levelled]
        self.level = {LAKE0 + i: L[7] for i, L in enumerate(levelled)}
        kind = {L[5]: LAKE0 + i for i, L in enumerate(levelled)}
        self.outlines = []
        # Lakes with no level first, so a lake with one wins where two outlines overlap.
        for x0, y0, x1, y1, rings, hid, _, lvl in sorted(found, key=lambda L: L[7] is not None):
            edges = [(a[0], a[1], b[0], b[1]) for r in rings for a, b in zip(r, r[1:] + r[:1]) if a[1] != b[1]]
            self.outlines.append((x0, y0, x1, y1, edges, kind.get(hid, EMPTY)))
        log(f"  lakes: {len(found)} outlines touch NCEI's water, {len(levelled)} with a level read from the DEM")
        # water joined to each lake with a level: a pixel two lakes reach is the one nearer through the water
        self.joined = {}
        if levelled:
            S, W = min(b[0] for b in boxes), min(b[1] for b in boxes)
            N, E = max(b[2] for b in boxes), max(b[3] for b in boxes)
            km = math.hypot((N - S) * 111.2, (E - W) * 111.2 * math.cos(math.radians((S + N) / 2))) / 2 + 5
            land = _Rows([r for _, r in shapes.polygons("land", (S + N) / 2, (W + E) / 2, km)], S, N)
            lrows = _Rows([L[4] for L in levelled])
            urows = _Rows([L[4] for L in found if L[7] is None])
            best = {}
            for L in levelled:
                for p, d in _join(L[4], L[7], grid, land, lrows, urows).items():
                    if p not in best or d < best[p][0]:
                        best[p] = (d, kind[L[5]])
            self.joined = {p: k for p, (_, k) in best.items()}
            log(f"  lakes: {len(self.joined)} pixels of water joined to them")
        # the base tiles holding joined water, for touches()
        span = 256 * 2 ** (JOIN_ZOOM - BASE_ZOOM)
        self.joined_tiles = {(px // span, py // span) for px, py in self.joined}

    def touches(self, z, x, y, S, W, N, E):
        """Whether a lake with a level, or water joined to one, may reach into a tile: a tile OpenStreetMap
        holds as land all over is still read where it does, since the land polygons count a lake as land."""
        if (x >> (z - BASE_ZOOM), y >> (z - BASE_ZOOM)) in self.joined_tiles:
            return True
        return any(k != EMPTY and x1 >= W and x0 <= E and y1 >= S and y0 <= N
                   for x0, y0, x1, y1, _, k in self.outlines)

    def kinds(self, lats, lons):
        """The lake outline of each pixel of a tile, as 65536 bytes, or None where none reaches it."""
        lo0, lo1, la0, la1 = lons[0], lons[-1], lats[-1], lats[0]
        near = [L for L in self.outlines if L[2] >= lo0 and L[0] <= lo1 and L[3] >= la0 and L[1] <= la1]
        if not near:
            return None
        out, dl = bytearray(65536), (lons[-1] - lons[0]) / 255
        for x0, y0, x1, y1, edges, kind in near:
            rows = [e for e in edges if max(e[1], e[3]) >= la0 and min(e[1], e[3]) <= la1]
            for py, lat in enumerate(lats):
                if not y0 <= lat <= y1:
                    continue
                xs = sorted(ax + (lat - ay) * (bx - ax) / (by - ay) for ax, ay, bx, by in rows if (ay > lat) != (by > lat))
                for a, b in zip(xs[0::2], xs[1::2]):
                    c0 = max(0, math.ceil((a - lons[0]) / dl))
                    c1 = min(255, math.floor((b - lons[0]) / dl))
                    for c in range(c0, c1 + 1):
                        out[py * 256 + c] = kind
        return out


# --- reading a tile ---------------------------------------------------------------------------

class Reader:
    """One worker's open sources, kept across the tiles it renders."""

    def __init__(self, lakes):
        self.lakes = lakes
        self.idx = ncei.tile_index()["tiles"]
        self.vd = None            # [(sub-region box, S, N, _Rows of one polygon)], VDatum's 0 to 360 longitudes
        self.land = None          # (box, _Rows) of the coastline around the current base tile
        self._vd_rows = {}        # latitude -> its VDatum test

    # VDatum's sub-region polygons, union of every type, as region_at() holds a point in one
    def vdatum_rows(self):
        if self.vd is None:
            self.vd = []
            for g in vdatum.index():
                for _, la, lo in g["polygons"]:
                    ring = list(zip(lo, la))
                    self.vd.append((g["box"], min(la), max(la), _Rows([[ring]])))
        return self.vd

    def in_vdatum_row(self, lat):
        """For one latitude, a test of a longitude: inside one of VDatum's sub-region polygons, as
        region_at() holds a point (inside the sub-region's box and an odd number of the polygon's
        crossings east of it), in VDatum's own 0 to 360 longitudes."""
        fn = self._vd_rows.get(lat)
        if fn is None:
            crossing = []
            for (gS, gW, gN, gE), pS, pN, rows in self.vdatum_rows():
                if gS <= lat <= gN and pS <= lat <= pN:
                    crossing.append((gW, gE, rows.crossings([lat])[0]))
            if not crossing:
                fn = lambda lon: False  # noqa: E731
            else:
                fn = lambda lon: any(gW <= lon % 360 <= gE and (len(xs) - bisect_right(xs, lon % 360)) % 2 == 1  # noqa: E731
                                     for gW, gE, xs in crossing)
            if len(self._vd_rows) > 200000:
                self._vd_rows.clear()
            self._vd_rows[lat] = fn
        return fn

    def keep(self, lat, lon):
        """ncei.in_vdatum() by row crossings, for the seam's edge search."""
        return self.in_vdatum_row(lat)(lon)

    def land_for(self, S, W, N, E):
        """The coastline's rows around a base tile, kept for its descendants."""
        if self.land and self.land[0] == (S, W, N, E):
            return self.land[1]
        km = math.hypot((N - S) * 111.2, (E - W) * 111.2 * math.cos(math.radians((S + N) / 2))) / 2 + 1
        rows = _Rows([r for _, r in shapes.polygons("land", (S + N) / 2, (W + E) / 2, km)], S - 0.01, N + 0.01)
        self.land = ((S, W, N, E), rows)
        return rows

    def ncei_tile(self, n, w):
        if f"{n:g},{w:g}" not in self.idx:
            return None
        return ncei._open_tile(ncei.tile_path(n - TILE_DEG / 2, w + TILE_DEG / 2))

    # -- the generic way: the depth tool's own answer at every pixel --

    def generic(self, z, lats, lons, inside, onland):
        """Around Bonaire. Finer than the 2019 survey's zoom only DCBD's own pixels are kept, and
        DCBD answers first wherever it holds water, so those are read straight from its grid; at the
        survey's zoom only the survey's box can hold anything kept."""
        vals, kinds, zooms, srcs = [0] * 65536, bytearray(65536), bytearray(65536), {}
        dz = SOURCE_ZOOM[dcbd.NAME]
        dt = dcbd.tile()
        for py, lat in enumerate(lats):
            for px, lon in enumerate(lons):
                i = py * 256 + px
                if (inside is not True and not inside[i]) or onland[i]:
                    continue
                if dcbd.in_box(lat, lon):
                    e = dt.fast(*dcbd.pixel(dt, lat, lon))
                    if e is not None and e < 0:
                        v = encode(-e)
                        if v:
                            vals[i], kinds[i], zooms[i], srcs[i] = v, WATER_OF[datums.NONE], dz, dcbd.NAME
                        continue
                if z > SOURCE_ZOOM[nlhs.NAME] or (z == SOURCE_ZOOM[nlhs.NAME] and not nlhs.in_box(lat, lon)):
                    continue
                try:
                    src, r = chain.answer_on(lat, lon)
                except chain.Refused:
                    continue
                if r["depth"] is None or r["key"] not in WATER_OF:
                    continue
                v = encode(r["depth"])
                if v:
                    vals[i], kinds[i] = v, WATER_OF[r["key"]]
                    zooms[i] = SOURCE_ZOOM.get(src.name, 14)
                    srcs[i] = src.name
        return vals, kinds, zooms, srcs

    # -- the row way: NCEI, the NCEI to GSC seam and the GSC DEM --

    def rows(self, z, x, y, lats, lons, inside, onland):
        """Elsewhere: NCEI where it answers, then the seam past its edge, then the GSC DEM. Finer
        than the GSC DEM's zoom only NCEI and the seam are kept, so a GSC pixel is read there only
        where the seam may reach it."""
        vals, kinds, zooms, srcs = [0] * 65536, bytearray(65536), bytearray(65536), {}
        gsc_kept = z <= SOURCE_ZOOM[gsc.NAME]
        S, W, N, E = tile_box(z, x, y)
        cells = {(math.ceil(la / TILE_DEG) * TILE_DEG, math.floor(lo / TILE_DEG) * TILE_DEG)
                 for la in (S + 1e-9, N - 1e-9) for lo in (W + 1e-9, E - 1e-9)}
        cells |= {(n, w) for n in {c[0] for c in cells} for w in {c[1] for c in cells}}
        tiles = {c: self.ncei_tile(*c) for c in cells}
        has_ncei = any(t is not None for t in tiles.values())
        # within the seam's reach of an NCEI tile: the seam has to be looked for
        dlat = SEAM_M / 111200
        dlon = SEAM_M / (111200 * math.cos(math.radians((S + N) / 2)))
        near = {(math.ceil(la / TILE_DEG) * TILE_DEG, math.floor(lo / TILE_DEG) * TILE_DEG)
                for la in (S - dlat, N + dlat) for lo in (W - dlon, E + dlon)}
        near = {(n, w) for n in {c[0] for c in near} for w in {c[1] for c in near}}
        seam_possible = any(f"{n:g},{w:g}" in self.idx for n, w in near)
        lake_kinds = self.lakes.kinds(lats, lons) if has_ncei else None
        n_px = 256 * 2 ** z
        P = 256 * 2 ** JOIN_ZOOM
        offs = None
        seam_blocks = {}
        if seam_possible:
            # a block of pixels whose centre lies farther than the seam's band plus the block's half
            # diagonal from NCEI's water holds no pixel the seam reaches
            wide = (E - W) * 111200 * math.cos(math.radians(S)) / 256 * LATTICE
            tall = (N - S) * 111200 / 256 * LATTICE
            half = math.hypot(wide, tall) / 2
            for bj in range(256 // LATTICE):
                for bi in range(256 // LATTICE):
                    cl, cn = lats[bj * LATTICE + LATTICE // 2], lons[bi * LATTICE + LATTICE // 2]
                    seam_blocks[(bj, bi)] = ncei.nearest_data(cl, cn, SEAM_M + half + 1,
                                                              keep_row=vdatum.row_intervals) is not None
        gt = gsc.tile()
        g_in = gsc.BOX
        for py, lat in enumerate(lats):
            in_vd = None
            row_cells = None
            for px, lon in enumerate(lons):
                i = py * 256 + px
                if inside is not True and not inside[i]:
                    continue
                if has_ncei:
                    t = tiles.get((math.ceil(lat / TILE_DEG) * TILE_DEG, math.floor(lon / TILE_DEG) * TILE_DEG))
                    e = None
                    if t is not None:
                        e = t.fast(*t.pixel(lat, lon))
                    if e is not None:
                        j = self.lakes.joined.get((int((lon + 180) / 360 * P),
                                                   int((1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * P)))
                        kd = j or (lake_kinds[i] if lake_kinds else 0)
                        if in_vd is None and not (kd or onland[i]):
                            in_vd = self.in_vdatum_row(lat)
                        if kd or onland[i] or in_vd(lon):
                            # NCEI answers here, as ncei.answer() does: inland of the coastline, or
                            # at sea inside a VDatum sub-region
                            if kd == EMPTY or (not kd and onland[i]):
                                continue
                            if kd:
                                d = self.lakes.level[kd] - e
                                if d < LAKE_MIN:
                                    continue
                                v, w_ = encode(d), kd
                            else:
                                if offs is None:
                                    offs = self._offsets(z, x, y)
                                off = self._offset(offs, px, py, lat, lon)
                                if off is None:
                                    continue
                                v, w_ = encode(-e - off), WATER_OF[datums.MLLW]
                            if v:
                                vals[i], kinds[i], zooms[i] = v, w_, SOURCE_ZOOM[chain.Ncei.name]
                                srcs[i] = chain.Ncei.name
                            continue
                # the GSC DEM, with the seam past NCEI's edge
                if onland[i] or not (g_in[0] <= lat <= g_in[2] and g_in[1] <= lon <= g_in[3]):
                    continue
                may_seam = seam_possible and seam_blocks[(py // LATTICE, px // LATTICE)]
                if not gsc_kept and not may_seam:
                    continue
                ge = gt.fast(*gsc.pixel(gt, lat, lon))
                if ge is None:
                    continue
                here, name = -ge, gsc.NAME
                if may_seam and ge < 0:
                    # the seam blends sea alone; ground the GSC DEM dries keeps its height, as the
                    # depth tool keeps the GSC DEM's answer there
                    edge = chain.NCEI_GSC.finish(ncei.nearest_data(lat, lon, SEAM_M, keep_row=vdatum.row_intervals))
                    if edge is not None:
                        here, name = chain.NCEI_GSC.blend(lat, lon, edge, here)[0], chain.NCEI_GSC.name
                v = encode(here)
                if v:
                    vals[i], kinds[i], zooms[i] = v, WATER_OF[datums.CHS], SOURCE_ZOOM[name]
                    srcs[i] = name
        return vals, kinds, zooms, srcs

    def _offsets(self, z, x, y):
        """NAVD 88's height above MLLW, exact, every LATTICE pixels across a tile."""
        n = 2 ** z
        k = 256 // LATTICE + 1
        out = []
        for j in range(k):
            lat = _tile_lat(y + j * LATTICE / 256, n)
            for i in range(k):
                lon = (x + i * LATTICE / 256) / n * 360 - 180
                out.append(vdatum.navd88_above_mllw(lat, lon)[0])
        return out

    def _offset(self, offs, px, py, lat, lon):
        """NAVD 88's height above MLLW at a pixel: bilinear between the four lattice figures around
        it, or exact where one of them is missing (the grids' shoreline)."""
        k = 256 // LATTICE + 1
        u, v = (px + 0.5) / LATTICE, (py + 0.5) / LATTICE
        i0, j0 = min(k - 2, int(u)), min(k - 2, int(v))
        fu, fv = u - i0, v - j0
        a, b = offs[j0 * k + i0], offs[j0 * k + i0 + 1]
        c, d = offs[(j0 + 1) * k + i0], offs[(j0 + 1) * k + i0 + 1]
        if None in (a, b, c, d):
            return vdatum.navd88_above_mllw(lat, lon)[0]
        return (a * (1 - fu) + b * fu) * (1 - fv) + (c * (1 - fu) + d * fu) * fv


BONAIRE_BOXES = (dcbd.BOX, nlhs.BOX, nlhs_1970.BOX)


def generic_tile(S, W, N, E):
    """Whether a tile touches the Bonaire surveys, which are read through answer_on() itself."""
    return any(s <= N and n >= S and w <= E and e >= W for s, w, n, e in BONAIRE_BOXES)


# --- the workers ------------------------------------------------------------------------------

_W = {}


def _offline(url, *a, **k):
    """A worker's urlopen. A forked process on macOS can crash inside the system's network code,
    so everything a worker reads is fetched before the fork, and a request here stops the run."""
    url = getattr(url, "full_url", url)
    raise RuntimeError(f"a depth worker asked the network for {url}: the export fetches every "
                       "source before it renders, so this piece was missed there; nothing was written.")


def _init(lakes, areas):
    import urllib.request
    urllib.request.urlopen = _offline
    _W["reader"] = Reader(lakes)
    _W["areas"] = areas


def render_tree(job):
    """render_one in a worker, with a refusal (sys.exit) carried back as an error: a pool worker
    that exits loses its tile and leaves the pool waiting for it."""
    try:
        return render_one(job)
    except SystemExit as e:
        raise RuntimeError(str(e.code)) from None


def render_one(job):
    """Render a base tile and, where a finer source answers inside it, its children, down to each
    source's zoom. (written [(z, x, y)], check candidates, leaf count)."""
    ai, x, y = job
    boxes = _W["areas"][ai]["boxes"]
    rd = _W["reader"]
    S, W, N, E = tile_box(BASE_ZOOM, x, y)
    land = rd.land_for(S, W, N, E)
    written, cands = [], {}
    rng = random.Random(x * 100003 + y)

    def one(z, tx, ty):
        lats, lons = centres(z, tx, ty)
        inside = clip(boxes, lats, lons)
        if inside is None:
            return
        onland = _Rows.mask(land.crossings(lats), lons)
        tS, tW, tN, tE = tile_box(z, tx, ty)
        if inside is True and all(onland) and not (rd.lakes and rd.lakes.touches(z, tx, ty, tS, tW, tN, tE)):
            return
        if generic_tile(tS, tW, tN, tE):
            vals, kinds, zooms, srcs = rd.generic(z, lats, lons, inside, onland)
        else:
            vals, kinds, zooms, srcs = rd.rows(z, tx, ty, lats, lons, inside, onland)
        if z > BASE_ZOOM:
            # a pixel of a coarser source is its ancestor's to show
            for i in [i for i, zz in enumerate(zooms) if vals[i] and zz < z]:
                vals[i], kinds[i], zooms[i] = 0, 0, 0
                srcs.pop(i, None)
        if not any(vals):
            return
        write_tile(z, tx, ty, vals, kinds)
        written.append((z, tx, ty))
        if max(zooms) > z:
            for dx in (0, 1):
                for dy in (0, 1):
                    one(z + 1, 2 * tx + dx, 2 * ty + dy)
        # sample pixels of the sources kept at this zoom; prove() keeps those the viewer reads here
        for i, name in srcs.items():
            if zooms[i] != z and not (z == BASE_ZOOM and zooms[i] < z):
                continue
            key = name if kinds[i] < LAKE0 else f"lake {kinds[i]}"
            if decode(vals[i]) < CHECK_MIN_DEPTH:
                continue
            got = cands.setdefault(key, [0, []])
            got[0] += 1
            pt = (lats[i // 256], lons[i % 256], vals[i], kinds[i], name, z)
            if len(got[1]) < 4 * CHECKS_PER_SOURCE:
                got[1].append(pt)
            elif (j := rng.randrange(got[0])) < 4 * CHECKS_PER_SOURCE:
                got[1][j] = pt

    one(BASE_ZOOM, x, y)
    return written, cands


# --- the layer --------------------------------------------------------------------------------

def base_tiles(areas):
    n = 2 ** BASE_ZOOM
    ty = lambda lat: int((1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n)  # noqa: E731
    tx = lambda lon: int((lon + 180) / 360 * n)  # noqa: E731
    jobs = []
    for ai, ar in enumerate(areas):
        tiles = {(x, y) for s, w, nn, e in ar["boxes"] for y in range(ty(nn), ty(s) + 1) for x in range(tx(w), tx(e) + 1)}
        jobs += [(ai, x, y) for x, y in sorted(tiles, key=lambda t: (t[1], t[0]))]
    return jobs


def padded(areas):
    """The coverage boxes, each widened by FETCH_PAD: a pixel near a box's edge reads past it, the
    seam's search for the NCEI DEM's nearest data among them, so the data just outside is fetched too."""
    return [[S - FETCH_PAD, W - FETCH_PAD, N + FETCH_PAD, E + FETCH_PAD] for ar in areas for S, W, N, E in ar["boxes"]]


def fetch(areas):
    """Every source's data touching the coverage, before any tile is drawn: the depth tool's own
    fetch for each source, so a failed download stops the export before it writes anything."""
    boxes = padded(areas)
    failed = 0
    for s in chain.sources():
        failed += s.fetch(boxes, 6) or 0
    if failed:
        sys.exit(f"{failed} downloads of the depth sources failed; the depth layer was left as it was.")
    # every VDatum sub-region inside the boxes, extracted once here rather than in each worker
    for S, W, N, E in boxes:
        for k in range(9):
            lat, lon = S + (N - S) * (k // 3) / 2, W + (E - W) * (k % 3) / 2
            vdatum.navd88_above_mllw(lat, lon)


def export(areas, workers=None):
    t0 = time.time()
    fetch(areas)
    ncei_boxes = []
    for S, W, N, E in padded(areas):
        for key in ncei.tile_index()["tiles"]:
            n, w = map(float, key.split(","))
            if n - TILE_DEG < N and n > S and w < E and w + TILE_DEG > W:
                ncei_boxes.append([max(S, n - TILE_DEG), max(W, w), min(N, n), min(E, w + TILE_DEG)])
    lakes = Lakes(ncei_boxes) if ncei_boxes else None
    # the CHS stations the NCEI to GSC seam takes MLLW from, read here so no worker downloads one
    for S, W, N, E in ncei_boxes:
        for i in range(int((N - S) / SEAM_STEP) + 2):
            for j in range(int((E - W) / SEAM_STEP) + 2):
                chain.mllw_above_cd(min(N, S + i * SEAM_STEP), min(E, W + j * SEAM_STEP))
    jobs = base_tiles(areas)
    log(f"  {len(jobs)} base tiles at zoom {BASE_ZOOM} over {len(areas)} areas; rendering with "
        f"{workers or os.cpu_count()} workers...")
    if os.path.isdir(TILES):
        shutil.rmtree(TILES)
    if os.path.exists(META):
        os.remove(META)
    written, cands = set(), {}
    ctx = multiprocessing.get_context("fork")
    try:
        with ctx.Pool(workers or os.cpu_count(), initializer=_init, initargs=(lakes, areas)) as pool:
            for k, (w, c) in enumerate(pool.imap_unordered(render_tree, jobs, chunksize=1), 1):
                written.update(w)
                for key, (n, pts) in c.items():
                    got = cands.setdefault(key, [0, []])
                    got[0] += n
                    got[1] += pts
                if k % 100 == 0 or k == len(jobs):
                    log(f"    {k}/{len(jobs)} base tiles, {len(written)} tiles written, {time.time() - t0:.0f} s")
    except RuntimeError as e:
        sys.exit(f"The depth layer stopped: {e}")
    if not written:
        sys.exit("No depth inside the coverage: no source answers inside its boxes.")
    # lower zooms: each pixel the mean of the 2 x 2 below it of the water most of them hold, kept
    # where at least two hold that water
    by_zoom = {}
    for z, x, y in written:
        by_zoom.setdefault(z, set()).add((x, y))
    for z in range(BASE_ZOOM - 1, MIN_ZOOM - 1, -1):
        by_zoom[z] = set()
        for cx, cy in {(x // 2, y // 2) for x, y in by_zoom[z + 1]}:
            vals, kinds = [0] * 65536, bytearray(65536)
            for dx in (0, 1):
                for dy in (0, 1):
                    if (2 * cx + dx, 2 * cy + dy) not in by_zoom[z + 1]:
                        continue
                    cv, ck = unpng(os.path.join(TILES, str(z + 1), str(2 * cx + dx), f"{2 * cy + dy}.png"))
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
                write_tile(z, cx, cy, vals, kinds)
                by_zoom[z].add((cx, cy))
        log(f"  zoom {z}: {len(by_zoom[z])} tiles, {time.time() - t0:.0f} s")
    checks = prove(cands, lakes, {z: t for z, t in by_zoom.items() if z >= BASE_ZOOM})
    describe(areas, by_zoom, lakes, checks, t0)


READ_AT = 0.3   # across a sample pixel, where it is read back: never on a pixel's edge at a finer zoom


def read_point(lat, lon, z):
    """Where a sample pixel of zoom z, centred at (lat, lon), is read back as the viewer reads it:
    READ_AT of the way across it. A pixel's centre lies on a corner of four pixels one zoom finer,
    where the browser's projection and this one can round to different pixels; READ_AT doubled at
    each finer zoom (0.6, 1.2, 2.4, 4.8) stays clear of every edge."""
    n = 2 ** z
    fx = math.floor((lon + 180) / 360 * n * 256) + READ_AT
    fy = math.floor((1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n * 256) + READ_AT
    return _tile_lat(fy / 256, n), fx / 256 / n * 360 - 180


def stored_at(lat, lon, present, cache):
    """What the viewer reads at a point: (zoom, v, water) of the deepest tile holding a value
    there, or None."""
    for z in sorted(present, reverse=True):
        n = 2 ** z
        fx = (lon + 180) / 360 * n
        fy = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
        x, y = int(fx), int(fy)
        if (x, y) not in present[z]:
            continue
        key = (z, x, y)
        if key not in cache:
            if len(cache) > 64:
                cache.clear()
            cache[key] = unpng(os.path.join(TILES, str(z), str(x), f"{y}.png"))
        vals, kinds = cache[key]
        i = int((fy - y) * 256) * 256 + int((fx - x) * 256)
        if vals[i]:
            return z, vals[i], kinds[i]
    return None


def prove(cands, lakes, present):
    """Read every sample pixel back the two ways: from the tiles as the viewer reads them, the
    deepest tile with a value at the pixel's centre, which has to be the pixel's own; and through
    the depth tool's answer_on(), which has to give the same water and the same depth, within half a
    step of v and a centimetre. A mismatch stops the export before the layer's description is
    written, so the viewer never draws a layer that fails its checks."""
    rng = random.Random(3)
    checks, bad, cache = [], [], {}
    tol = SCALE / 2 + 0.01
    for key in sorted(cands):
        pts = cands[key][1]
        rng.shuffle(pts)
        kept = 0
        for lat, lon, v, kind, name, z in pts:
            if kept == CHECKS_PER_SOURCE:
                break
            rlat, rlon = read_point(lat, lon, z)
            if stored_at(rlat, rlon, present, cache) != (z, v, kind):
                continue   # a deeper tile shows another pixel here
            kept += 1
            try:
                src, r = chain.answer_on(lat, lon)
            except chain.Refused as e:
                bad.append(f"{key} at {lat:.6f}, {lon:.6f}: the depth tool refuses it ({e})")
                continue
            want = WATER_OF.get(r["key"]) if r["key"] != datums.LAKE else None
            got = decode(v)
            if r["depth"] is None:
                bad.append(f"{key} at {lat:.6f}, {lon:.6f}: the map holds {got:.1f} m, the depth tool gives no depth "
                           f"({r.get('why')})")
                continue
            if (kind >= LAKE0) != (r["key"] == datums.LAKE) or (kind < LAKE0 and kind != want) \
                    or src.name != (name if kind < LAKE0 else LAKE_SOURCE) or abs(got - r["depth"]) > tol:
                bad.append(f"{key} at {lat:.6f}, {lon:.6f}: the map holds {got:.2f} m from {name}, the depth tool "
                           f"answers {r['depth']:.2f} m below {r['key']} from {src.name}")
                continue
            checks.append({"lat": round(rlat, 8), "lon": round(rlon, 8), "depth": round(got, 2), "water": kind})
        log(f"  checked {kept} pixels of {key} ({cands[key][0]} kept at their own zoom)")
        if kept == 0:
            bad.append(f"{key}: no sample pixel is the one the viewer reads at its centre")
    if bad:
        for b in bad[:40]:
            log("  MISMATCH " + b)
        sys.exit(f"{len(bad)} of the depth layer's sample pixels differ from the depth tool; the layer's description "
                 "was not written. Stop and report it.")
    return checks


def describe(areas, by_zoom, lakes, checks, t0):
    boxes = [b for ar in areas for b in ar["boxes"]]
    S, W = min(b[0] for b in boxes), min(b[1] for b in boxes)
    N, E = max(b[2] for b in boxes), max(b[3] for b in boxes)
    size = sum(os.path.getsize(os.path.join(TILES, str(z), str(x), f"{y}.png")) for z, s in by_zoom.items() for x, y in s)
    layer = {
        "label": "Depth",
        # the export's own moment in each tile's address, so a browser never pairs these checks with
        # tiles it cached from an earlier export
        "tiles": "map/depth/tiles/{z}/{x}/{y}.png?b=" + str(int(t0)),
        "scale": SCALE, "shallowest": SHALLOWEST,
        "minZoom": MIN_ZOOM, "baseZoom": BASE_ZOOM, "maxZoom": max(by_zoom),
        "bounds": [[S, W], [N, E]],
        "areas": [{"name": a["name"], "label": a["label"], "boxes": a["boxes"]} for a in areas],
        "built": date.today().isoformat(),
        "waters": [{"tide": t} for t in WATER_TIDES],
        "lakes": lakes.table if lakes else [],
        "lake0": LAKE0,
        "present": {str(z): ",".join(f"{x}/{y}" for x, y in sorted(s)) for z, s in sorted(by_zoom.items())},
        "checks": checks,
    }
    import json
    with open(META + ".part", "w") as f:
        f.write("// Written by tools/map_export.py; regenerate rather than edit.\n")
        f.write(f"window.MAP_DEPTH = {json.dumps(layer, separators=(',', ':'))};\n")
    os.replace(META + ".part", META)
    count = sum(len(s) for s in by_zoom.values())
    log(f"  wrote {count} tiles ({size / 1e6:.0f} MB) to map/depth/tiles/ and map/depth/depth.js, "
        f"{len(checks)} checks, in {time.time() - t0:.0f} s")

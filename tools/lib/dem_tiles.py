"""NCEI coastal DEM tiles shared by ncei_depth.py and current.py: the GeoTIFF reader
for one tile."""
import math
import os
import struct
import sys
import zlib

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

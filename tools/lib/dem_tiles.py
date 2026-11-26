"""DEM tiles shared by the depth tool and current.py: the GeoTIFF reader for one file, classic
TIFF or BigTIFF, in tiles or strips."""
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
    TYPES = {1: "B", 2: "s", 3: "H", 4: "I", 11: "f", 12: "d", 16: "Q", 17: "q", 18: "Q"}

    def __init__(self, path):
        self.path, self.name = path, os.path.splitext(os.path.basename(path))[0]
        self.f = open(path, "rb")
        head = self.f.read(16)
        self.bo = {b"II": "<", b"MM": ">"}.get(head[:2])
        magic = self.bo and struct.unpack(self.bo + "H", head[2:4])[0]
        if magic == 42:
            self.big, first = False, struct.unpack(self.bo + "I", head[4:8])[0]
        elif magic == 43:
            self.big, first = True, struct.unpack(self.bo + "Q", head[8:16])[0]
        else:
            self._bad("it is neither a classic TIFF nor a BigTIFF")
        t = self._ifd(first)
        self.w, self.h = t[256][0], t[257][0]
        self.comp, self.pred = t.get(259, (1,))[0], t.get(317, (1,))[0]
        if (t.get(258, (0,))[0], t.get(339, (1,))[0], t.get(277, (1,))[0]) != (32, 3, 1) \
                or not (322 in t or 273 in t) or self.comp not in (1, 5, 8, 32946) or self.pred not in (1, 2, 3):
            self._bad("expected one 32-bit float band in tiles or strips, uncompressed, LZW or deflate")
        if 322 in t:
            self.tw, self.th = t[322][0], t[323][0]
            self.offs, self.counts = t[324], t[325]
        else:  # strips: one tile column as wide as the image, RowsPerStrip tall
            self.tw, self.th = self.w, min(t.get(278, (self.h,))[0], self.h)
            self.offs, self.counts = t[273], t[279]
        self.sx = self.sy = self.x0 = self.y0 = None
        if 33550 in t and 33922 in t:
            self.sx, self.sy = t[33550][0], t[33550][1]
            tie = t[33922]
            self.x0, self.y0 = tie[3] - tie[0] * self.sx, tie[4] + tie[1] * self.sy  # the grid's north-west corner
        nodata = t.get(42113)
        # the tag is text; the pixels are float32, so the value is compared as the float32 it stores as
        self.nodata = struct.unpack("f", struct.pack("f", float(nodata[0].split(b"\0")[0])))[0] if nodata else None
        self.cite = (t.get(34737) or [b""])[0].split(b"\0")[0].decode("ascii", "replace").strip("| ")
        self._blocks = {}

    def _bad(self, why):
        sys.exit(f"{self.name}: unexpected tile layout, {why}. Delete the file to fetch it again, and report it if it repeats.")

    def _ifd(self, off):
        """The tags of one IFD: 12-byte entries with a 4-byte value field in a classic TIFF,
        20-byte entries with an 8-byte one in a BigTIFF."""
        cnt_fmt, ent, val = ("Q", 20, 8) if self.big else ("H", 12, 4)
        self.f.seek(off)
        n = struct.unpack(self.bo + cnt_fmt, self.f.read(struct.calcsize(cnt_fmt)))[0]
        raw = self.f.read(ent * n)
        tags = {}
        for i in range(n):
            e = raw[i * ent:(i + 1) * ent]
            tag, typ = struct.unpack(self.bo + "HH", e[:4])
            cnt = struct.unpack(self.bo + ("Q" if self.big else "I"), e[4:ent - val])[0]
            code = self.TYPES.get(typ)
            if code is None:
                continue
            fmt = self.bo + (f"{cnt}s" if code == "s" else f"{cnt}{code}")
            size = struct.calcsize(fmt)
            if size <= val:
                data = e[ent - val:ent - val + size]
            else:
                self.f.seek(struct.unpack(self.bo + ("Q" if self.big else "I"), e[ent - val:])[0])
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
        """(row, col) of the pixel a point falls in, for a tile georeferenced in degrees by its own
        GeoTIFF tags; the tile's tie point is its outer corner."""
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
        elif self.pred == 2:
            # horizontal differencing: each 32-bit sample stored as the difference from the one before it
            acc = sum(struct.unpack(f"{self.bo}{c + 1}I", line[:(c + 1) * 4])) & 0xFFFFFFFF
            v = struct.unpack("<f", struct.pack("<I", acc))[0]
        else:
            v = struct.unpack(self.bo + "f", line[c * 4:c * 4 + 4])[0]
        if v != v or self.nodata is not None and abs(v - self.nodata) < 1e-3:
            return None
        return v

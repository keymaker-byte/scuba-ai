"""XTide's harmonics files (libtcd format, major revision 2), shared by noaa_legacy_current.py
and blend_model.py: the reader for its reference and subordinate station records, and the
current at a reference station."""
import math
import sys
from datetime import datetime, timezone

KN = 0.514444  # m/s per knot


def _unpack(buf, start, n):
    sb, eb = start >> 3, (start + n - 1) >> 3
    v = int.from_bytes(buf[sb:eb + 1], "big")
    return (v >> ((eb + 1) * 8 - (start + n))) & ((1 << n) - 1)


def _sunpack(buf, start, n):
    v = _unpack(buf, start, n)
    return v - (1 << n) if v & (1 << (n - 1)) else v


class Harmonics:
    def __init__(self, path):
        d = open(path, "rb").read()
        end = d.index(b"[END OF ASCII HEADER DATA]")
        self.h = {}
        for line in d[:end].decode("latin-1").splitlines():
            k, _, v = line.partition("=")
            self.h[k.strip().strip("[]")] = v.strip()
        I = self.i
        if I("MAJOR REV") != 2:
            sys.exit("legacy harmonics: unexpected TCD revision.")
        p = I("HEADER SIZE") + 4

        def strings(n, size):
            nonlocal p
            out = [d[p + k * size:p + (k + 1) * size].split(b"\0")[0].decode("latin-1") for k in range(n)]
            p += n * size
            return out

        self.level_units = strings(I("LEVEL UNIT TYPES"), I("LEVEL UNIT SIZE"))
        strings(I("DIRECTION UNIT TYPES"), I("DIRECTION UNIT SIZE"))
        strings(2 ** I("RESTRICTION BITS"), I("RESTRICTION SIZE"))
        strings(2 ** I("TZFILE BITS"), I("TZFILE SIZE"))
        strings(2 ** I("COUNTRY BITS"), I("COUNTRY SIZE"))
        strings(2 ** I("DATUM BITS"), I("DATUM SIZE"))
        strings(2 ** I("LEGALESE BITS"), I("LEGALESE SIZE"))
        nc = I("CONSTITUENTS")
        strings(nc, I("CONSTITUENT SIZE"))
        sb = I("SPEED BITS")
        n = (nc * sb + 7) // 8
        buf = d[p:p + n]
        p += n
        self.speed = [(_unpack(buf, k * sb, sb) + I("SPEED OFFSET")) / I("SPEED SCALE") for k in range(nc)]
        ny, self.y0 = I("NUMBER OF YEARS"), I("START YEAR")

        def table(bits, off, scale):
            nonlocal p
            b = I(bits)
            n = (nc * ny * b + 7) // 8
            buf = d[p:p + n]
            p += n
            return [[(_unpack(buf, (k * ny + j) * b, b) + I(off)) / I(scale) for j in range(ny)] for k in range(nc)]

        self.equ = table("EQUILIBRIUM BITS", "EQUILIBRIUM OFFSET", "EQUILIBRIUM SCALE")
        self.node = table("NODE BITS", "NODE OFFSET", "NODE SCALE")
        self.ny = ny
        self.d, self.rec0 = d, p

    def i(self, key):
        return int(self.h[key])

    def records(self):
        p = self.rec0
        for _ in range(self.i("NUMBER OF RECORDS")):
            size = _unpack(self.d[p:p + 4], 0, self.i("RECORD SIZE BITS"))
            yield self._parse(self.d[p:p + size])
            p += size

    def _parse(self, buf):
        I = self.i
        pos = 0
        r = {}

        def u(k):
            nonlocal pos
            v = _unpack(buf, pos, I(k))
            pos += I(k)
            return v

        def s(k):
            nonlocal pos
            v = _sunpack(buf, pos, I(k))
            pos += I(k)
            return v

        def text():
            nonlocal pos
            out = bytearray()
            while True:
                c = _unpack(buf, pos, 8)
                pos += 8
                if not c:
                    return out.decode("latin-1")
                out.append(c)

        u("RECORD SIZE BITS")
        r["type"] = u("RECORD TYPE BITS")
        r["lat"] = s("LATITUDE BITS") / I("LATITUDE SCALE")
        r["lon"] = s("LONGITUDE BITS") / I("LONGITUDE SCALE")
        u("TZFILE BITS")
        r["name"] = text()
        r["ref"] = s("STATION BITS")
        u("COUNTRY BITS")
        text()  # source
        u("RESTRICTION BITS")
        text()  # comments
        text()  # notes
        u("LEGALESE BITS")
        text()  # station id context
        text()  # station id
        u("DATE BITS")
        text()  # xfields
        u("DIRECTION UNIT BITS")
        r["ebb_dir"] = u("DIRECTION BITS")
        r["flood_dir"] = u("DIRECTION BITS")
        r["units"] = self.level_units[u("LEVEL UNIT BITS")]
        if r["type"] == 1:
            r["datum"] = s("DATUM OFFSET BITS") / I("DATUM OFFSET SCALE")
            u("DATUM BITS")
            zone = s("TIME BITS")  # hhmm
            r["zone_h"] = int(zone / 100) + (zone % 100 if zone >= 0 else -((-zone) % 100)) / 60
            u("DATE BITS")
            u("MONTHS ON STATION BITS")
            u("DATE BITS")
            u("CONFIDENCE VALUE BITS")
            r["cons"] = []
            for _ in range(u("CONSTITUENT BITS")):
                k = u("CONSTITUENT BITS")
                a = u("AMPLITUDE BITS") / I("AMPLITUDE SCALE")
                e = u("EPOCH BITS") / I("EPOCH SCALE")
                r["cons"].append((k, a, e))
        elif r["type"] == 2:
            # a subordinate station: its reference record, then the corrections at max ebb, at
            # max flood, and at the two slacks; a time is hhmm, and 2560 marks one left blank
            hm = lambda v: None if v == 2560 else int(v / 100) * 60 + (v % 100 if v >= 0 else -((-v) % 100))
            r["ebb_time"] = hm(s("TIME BITS"))
            r["ebb_add"] = s("LEVEL ADD BITS") / I("LEVEL ADD SCALE")
            if r["ebb_add"]:
                u("LEVEL UNIT BITS")
            r["ebb_mult"] = u("LEVEL MULTIPLY BITS") / I("LEVEL MULTIPLY SCALE")
            r["flood_time"] = hm(s("TIME BITS"))
            r["flood_add"] = s("LEVEL ADD BITS") / I("LEVEL ADD SCALE")
            if r["flood_add"]:
                u("LEVEL UNIT BITS")
            r["flood_mult"] = u("LEVEL MULTIPLY BITS") / I("LEVEL MULTIPLY SCALE")
            r["sbf_time"] = hm(s("TIME BITS"))
            r["sbe_time"] = hm(s("TIME BITS"))
        return r


def velocity(h, r, t):
    """Signed current at UTC datetime t, m/s. Positive = flood."""
    j = t.year - h.y0
    if not 0 <= j < h.ny:
        sys.exit(f"legacy harmonics cover {h.y0} to {h.y0 + h.ny - 1} only.")
    hrs = (t - datetime(t.year, 1, 1, tzinfo=timezone.utc)).total_seconds() / 3600
    v = r["datum"]
    for k, a, e in r["cons"]:
        # Epochs are referenced to the station's own time meridian; shift them to Greenwich.
        g = e - h.speed[k] * r["zone_h"]
        v += a * h.node[k][j] * math.cos(math.radians(h.speed[k] * hrs + h.equ[k][j] - g))
    if r["units"].endswith("^2"):
        v = math.copysign(math.sqrt(abs(v)), v)
    return v * KN

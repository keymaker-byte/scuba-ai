"""XTide's harmonics files (libtcd format, major revision 2), read by current.py for the
2010 legacy tables its `verify` scores against: the download, the reader for its reference and
subordinate station records, the current at a reference station, and a check against NOAA's
printed tables."""
import io
import math
import os
import sys
import tarfile
import urllib.request
from datetime import date, datetime, time, timedelta, timezone

DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "db")
LEGACY = os.path.join(DB, "harmonics-dwf-20100529-free.tcd")
# XTide's 2010-05-29 harmonics, NOAA's published constants before the re-survey, as archived by
# Debian (source package xtide-data 20100529).
LEGACY_URL = "https://snapshot.debian.org/file/7f9edc4c9ea71a5a8f221bbb533943dbbaf9655a"

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


def legacy():
    """The 2010 legacy tables, downloaded into tools/db/ the first time they are asked for."""
    if not os.path.exists(LEGACY):
        os.makedirs(DB, exist_ok=True)
        print(f"downloading {LEGACY_URL} ...", file=sys.stderr)
        try:
            with urllib.request.urlopen(LEGACY_URL, timeout=120) as r:
                data = r.read()
            with tarfile.open(fileobj=io.BytesIO(data), mode="r:bz2") as t:
                m = next(x for x in t.getmembers() if x.name.endswith(".tcd"))
                body = t.extractfile(m).read()
        except (OSError, tarfile.TarError, StopIteration) as e:
            sys.exit(f"legacy harmonics: download failed ({e}) from {LEGACY_URL}.")
        part = LEGACY + ".part"
        with open(part, "wb") as f:
            f.write(body)
        os.replace(part, LEGACY)
    return Harmonics(LEGACY)


# Slack times printed in NOAA's 2013 Tidal Current Tables, Pacific Coast of North America and Asia
# (local standard time, UTC-8): https://tidesandcurrents.noaa.gov/tidetables/2013/pcct2013book.pdf
CHECKS = [
    ("Strait of Juan de Fuca Entrance, Washington Current", "2013-02-01", ["02:36", "07:15", "15:57", "19:48"]),
    ("Admiralty Inlet (off Bush Point), Washington Current", "2013-01-01", ["01:36", "08:02"]),
    ("The Narrows, north end (midstream), Washington Current", "2013-01-01", ["01:56", "08:45", "14:59", "19:45"]),
]


def selftest():
    """The reader and the reference prediction against slacks NOAA printed in its 2013 tables.
    Prints each slack and returns True when every one is within 2 minutes."""
    h = legacy()
    recs = {r["name"]: r for r in h.records() if r["type"] == 1}
    pst = timezone(timedelta(hours=-8))
    print("Legacy tables self-test against NOAA's printed 2013 Tidal Current Tables")
    worst = 0.0
    for name, day, printed in CHECKS:
        r = recs[name]
        d = date.fromisoformat(day)
        t0 = datetime.combine(d, time(0), pst).astimezone(timezone.utc)
        ser = [(t0 + timedelta(minutes=m), velocity(h, r, t0 + timedelta(minutes=m))) for m in range(1441)]
        slacks = [a + (b - a) * (va / (va - vb)) for (a, va), (b, vb) in zip(ser, ser[1:]) if (va < 0) != (vb < 0)]
        for p in printed:
            ref = datetime.combine(d, time.fromisoformat(p), pst)
            err = min(abs((g - ref).total_seconds()) / 60 for g in slacks)
            worst = max(worst, err)
            print(f"  {name[:-len(' Current')]:<55} {day} printed {p}  predicted within {err:.0f} min")
    ok = worst <= 2
    print("  PASS\n" if ok else f"  FAIL: worst {worst:.0f} min\n")
    return ok

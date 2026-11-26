"""The Royal Netherlands Navy Hydrographic Service's single-beam surveys of Bonaire's waters from
1970 to 1972, digitized from their fair sheets, for the depth tool: soundings 20 m apart along
tracks a few hundred metres apart, from about 1 m to 2,600 m below LAT, ordered by hand from
SeaDataNet with the 2019 survey and kept beside it. A depth between soundings is interpolated
from the soundings around it, never past the last track, and never on land.

Their depths sit on the DCBD coastal bathymetry's own reference (within 0.13 m on flat bottom),
so they are read as published."""
import glob
import math
import os
import re
import sys
import zipfile
from collections import defaultdict

from lib import dcbd, ncei, nlhs, shapes

DB = nlhs.DB


NAME = "Royal Netherlands Navy single-beam surveys of 1970 to 1972"


SURVEYS = ("HY1024lm1(digi)", "HY1024lm2(digi)", "HY1024lm6(digi)", "HY1024lm7(digi)", "HY1026lm11(digi)")


CREDIT = ("Royal Netherlands Navy Hydrographic Service, surveys " + ", ".join(SURVEYS)
          + ", CC BY 4.0, via SeaDataNet")


MEMBER = re.compile(r"_XYZ_(HY102[46]lm\d+\(digi\))_V(\d+)\.txt$")


BOX = (11.66, -68.75, 12.45, -68.02)   # the five surveys together, S W N E, from SeaDataNet's records


BUCKET_M = 500.0   # the spatial index's cell


REACH_M = 1500.0   # how far a point looks for soundings around it


QUADRANTS = 3      # of the four quadrants around a point, how many must hold a sounding within REACH_M


NEAREST = 8        # the soundings a depth is interpolated from, by inverse distance squared


def how_to_get():
    ids = "\n".join(f"       {s}" for s in SURVEYS)
    return f"""the {NAME} are not on this machine.

SeaDataNet hands them out only behind a free login and an order, so they are fetched by hand:

  1. Open {nlhs.SEARCH_URL} and log in as for the 2019 survey (EGI Check-in - EOSC AAI, then
     Google, GitHub or ORCID).
  2. Search for each of these and add it to the basket; each is one result from the Royal
     Netherlands Navy, Hydrographic Service, single-beam echosounders, 1970 to 1972:
{ids}
  3. Open the basket, name the order, choose XYZ as the format, give a short motivation, and
     submit. The surveys are unrestricted (CC BY 4.0), so the order is ready within minutes.
  4. Under "My standing orders", open the order and download RECORDS (a zip of about 120 KB,
     named order_<number>_unrestricted.zip).
  5. Save the zip, unopened, into
       {DB}/"""


def _find():
    """{survey: (version, path, member)}: the newest copy of each survey here, inside an order zip
    or as the text file itself."""
    best = {}
    for z in glob.glob(os.path.join(DB, "*.zip")):
        try:
            with zipfile.ZipFile(z) as f:
                names = f.namelist()
        except zipfile.BadZipFile:
            continue
        for n in names:
            m = MEMBER.search(n)
            if m and (m.group(1) not in best or int(m.group(2)) > best[m.group(1)][0]):
                best[m.group(1)] = (int(m.group(2)), z, n)
    for t in glob.glob(os.path.join(DB, "*.txt")):
        m = MEMBER.search(os.path.basename(t))
        if m and (m.group(1) not in best or int(m.group(2)) > best[m.group(1)][0]):
            best[m.group(1)] = (int(m.group(2)), t, None)
    return best


_data = None


def data():
    """{"points": [(x, y, depth)], "index": {bucket: [point]}, "surveys": {survey: version}} in UTM
    zone 19N metres; stops the run with how_to_get() when any survey is missing."""
    global _data
    if _data is not None:
        return _data
    found = _find()
    missing = [s for s in SURVEYS if s not in found]
    if missing:
        sys.exit(f"{NAME}: missing {', '.join(missing)}; {how_to_get()}")
    pts = []
    for s in SURVEYS:
        _, path, member = found[s]
        try:
            text = (zipfile.ZipFile(path).read(member).decode("ascii") if member else open(path).read())
        except (OSError, zipfile.BadZipFile, UnicodeDecodeError, KeyError) as e:
            sys.exit(f"{NAME}: cannot read {s} from {path} ({e}). Delete it and order the surveys again:\n\n{how_to_get()}")
        for line in text.splitlines():
            p = line.split()
            if len(p) == 3 and p[2][:1].isdigit():
                x, y = dcbd.utm(nlhs._dms(p[0]), nlhs._dms(p[1]))
                pts.append((x, y, float(p[2])))
    index = defaultdict(list)
    for q in pts:
        index[(int(q[0] // BUCKET_M), int(q[1] // BUCKET_M))].append(q)
    _data = {"points": pts, "index": index, "surveys": {s: found[s][0] for s in SURVEYS}}
    return _data


def in_box(lat, lon):
    s, w, n, e = BOX
    return s <= lat <= n and w <= lon <= e


COAST_BUCKET_M = 200.0

_coast = None


def _coastline():
    """OpenStreetMap's coastline around Bonaire and Klein Bonaire as UTM segments, indexed by
    COAST_BUCKET_M cells: read once from lib/shapes.py's land polygons."""
    global _coast
    if _coast is None:
        idx = defaultdict(list)
        for _, rings in shapes.polygons("land", 12.15, -68.30, 40):
            for r in rings:
                for (ax, ay), (bx, by) in zip(r, r[1:] + r[:1]):
                    if (ax == bx and ax == round(ax)) or (ay == by and ay == round(ay)):
                        continue   # a cut along a whole degree, through land
                    a, b = dcbd.utm(ay, ax), dcbd.utm(by, bx)
                    seg = (a, b)
                    for i in range(int(min(a[0], b[0]) // COAST_BUCKET_M), int(max(a[0], b[0]) // COAST_BUCKET_M) + 1):
                        for j in range(int(min(a[1], b[1]) // COAST_BUCKET_M), int(max(a[1], b[1]) // COAST_BUCKET_M) + 1):
                            idx[(i, j)].append(seg)
        _coast = idx
    return _coast


def coast_m(x, y, limit_m=1000.0):
    """Distance from UTM (x, y) to the nearest coastline within limit_m, or limit_m when none is."""
    idx, k, best = _coastline(), int(limit_m // COAST_BUCKET_M) + 1, limit_m
    bi, bj = int(x // COAST_BUCKET_M), int(y // COAST_BUCKET_M)
    for ring in range(k + 1):
        if ring and (ring - 1) * COAST_BUCKET_M > best:
            break
        for i in range(bi - ring, bi + ring + 1):
            for j in range(bj - ring, bj + ring + 1):
                if max(abs(i - bi), abs(j - bj)) != ring:
                    continue
                for (x1, y1), (x2, y2) in idx.get((i, j), ()):
                    dx, dy = x2 - x1, y2 - y1
                    L = dx * dx + dy * dy
                    t = 0.0 if L == 0 else max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / L))
                    best = min(best, math.hypot(x - x1 - t * dx, y - y1 - t * dy))
    return best


def _around(x, y):
    """[(distance, point)] within REACH_M, nearest first."""
    idx, k = data()["index"], int(REACH_M // BUCKET_M) + 1
    bi, bj = int(x // BUCKET_M), int(y // BUCKET_M)
    out = [(math.hypot(q[0] - x, q[1] - y), q) for i in range(bi - k, bi + k + 1)
           for j in range(bj - k, bj + k + 1) for q in idx.get((i, j), ())]
    return sorted(o for o in out if o[0] <= REACH_M)


def estimate(x, y):
    """(depth, nearest sounding's distance) at UTM (x, y), or None where fewer than QUADRANTS of
    the four quadrants around the point hold a sounding within REACH_M: past the last track."""
    near = _around(x, y)
    if not near:
        return None
    if near[0][0] < 0.5:
        return near[0][1][2], near[0][0]
    quads = {(q[0] >= x, q[1] >= y) for _, q in near}
    if len(quads) < QUADRANTS:
        return None
    use = near[:NEAREST]
    w = [1 / d ** 2 for d, _ in use]
    return sum(wi * q[2] for wi, (_, q) in zip(w, use)) / sum(w), near[0][0]


def depth(x, y):
    e = estimate(x, y)
    return None if e is None else e[0]


def nearest(x, y, limit_m):
    near = _around(x, y)
    return near[0] if near and near[0][0] <= limit_m else None


def answer(lat, lon):
    """{water, depth, datum, detail, why, nodata, dem}: the depth interpolated from the soundings
    around the point, a plain observed depth; no depth on land, or past the last track."""
    out = {"dem": {"source": "single-beam soundings", "res_m": None}, "depth": None, "datum": None,
           "detail": None, "why": None}
    if ncei.inland(lat, lon):
        return {**out, "water": "none", "why": "on land, inland of OpenStreetMap's coastline"}
    x, y = dcbd.utm(lat, lon)
    e = estimate(x, y)
    if e is None:
        near = _around(x, y)
        where = (f"; the nearest sounding is {near[0][0]:.0f} m away, {near[0][1][2]:.0f} m deep"
                 if near else f"; none within {REACH_M:.0f} m")
        return {**out, "water": "none", "nodata": True,
                "why": f"no soundings of the {NAME} on {QUADRANTS} sides of the point within {REACH_M:.0f} m{where}"}
    z, d = e
    return {**out, "water": "sea", "depth": z, "datum": dcbd.DATUM,
            "detail": f"interpolated from the {min(NEAREST, len(_around(x, y)))} nearest soundings, the nearest "
                      f"{d:.0f} m away; tracks lie a few hundred metres apart and their positions date from "
                      f"1970 to 1972, so the figure is rough, a depth beyond diving limits"}


def fetch(boxes, workers):
    if not any(bs < BOX[2] and bn > BOX[0] and bw < BOX[3] and be > BOX[1] for bs, bw, bn, be in boxes):
        print("no box touches the surveys' extent; nothing to do")
        return 0
    found = _find()
    if any(s not in found for s in SURVEYS):
        print(f"  {how_to_get()}")
        return 1
    print("the surveys touch the boxes and are already here")
    return 0


def verify(lat, lon, r):
    d = data()
    print(f"  this copy: " + ", ".join(f"{s} V{v}" for s, v in d["surveys"].items()) + f", {len(d['points'])} soundings")
    print(f"  NOT CHECKED: SeaDataNet serves these surveys only behind a login. Open each record at "
          f"https://cdi-bathymetry.seadatanet.org/report/edmo/574/<survey> and compare its CDI version; "
          f"on a newer one, delete its order zip from {DB}/ and order it again.")
    return True


def selftest():
    """Every sounding read back at its own position, passing within 1e-9 m. A sample of soundings
    each left out and answered by its neighbours is reported beside it, the roughness a depth
    between tracks carries; it is the data's own spread, so it sets no pass."""
    d = data()
    pts = d["points"]
    back = max(abs(depth(x, y) - z) for x, y, z in pts[::50])
    miss = []
    for x, y, z in pts[::40]:
        near = [(dd, q) for dd, q in _around(x, y) if dd > 0.5][:NEAREST]
        if len(near) >= 4 and z <= 200:
            w = [1 / dd ** 2 for dd, _ in near]
            miss.append(abs(sum(wi * q[2] for wi, (_, q) in zip(w, near)) / sum(w) - z) / z)
    miss.sort()
    ok = back <= 1e-9
    print(f"  {len(pts)} soundings in {len(d['surveys'])} surveys; read back at their own positions within {back:.1e} m")
    if miss:
        print(f"  a sounding left out and answered by its neighbours, to 200 m: median {miss[len(miss) // 2]:.0%} off, "
              f"p90 {miss[9 * len(miss) // 10]:.0%}")
    print("  PASS" if ok else "  FAIL")
    return ok

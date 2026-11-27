"""The Royal Netherlands Navy Hydrographic Service's single-beam surveys of Bonaire's waters from
1970 to 1972, digitized from their fair sheets, for the depth tool: soundings 20 m apart along
tracks a few hundred metres apart, from about 1 m to 2,600 m below LAT, ordered by hand from
SeaDataNet with the 2019 survey and kept beside it. A depth between soundings is interpolated
from the soundings around it, never past the last track, and never on land.

Their depths sit on the DCBD coastal bathymetry's own reference (within 0.13 m on flat bottom),
so they are read as published."""
import glob
import json
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


OPEN_DEG = 180.0   # the widest empty angle around a point, between the soundings within REACH_M, it answers under
FINER_M = 500.0    # how far the finer surveys' water, read as soundings' directions, is looked for around a point
BESIDE_M = 500.0   # a point this near a sounding lies beside its track, and answers whatever the angle


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


def coast_point(x, y, limit_m=1000.0):
    """(distance, x, y) of the nearest point of the coastline within limit_m of UTM (x, y), or
    None when none is."""
    idx, k, best = _coastline(), int(limit_m // COAST_BUCKET_M) + 1, (limit_m, None, None)
    bi, bj = int(x // COAST_BUCKET_M), int(y // COAST_BUCKET_M)
    for ring in range(k + 1):
        if ring and (ring - 1) * COAST_BUCKET_M > best[0]:
            break
        for i in range(bi - ring, bi + ring + 1):
            for j in range(bj - ring, bj + ring + 1):
                if max(abs(i - bi), abs(j - bj)) != ring:
                    continue
                for (x1, y1), (x2, y2) in idx.get((i, j), ()):
                    dx, dy = x2 - x1, y2 - y1
                    L = dx * dx + dy * dy
                    t = 0.0 if L == 0 else max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / L))
                    px, py = x1 + t * dx, y1 + t * dy
                    d = math.hypot(x - px, y - py)
                    if d < best[0]:
                        best = (d, px, py)
    return best if best[1] is not None else None


def coast_m(x, y, limit_m=1000.0):
    """Distance from UTM (x, y) to the nearest coastline within limit_m, or limit_m when none is."""
    c = coast_point(x, y, limit_m)
    return limit_m if c is None else c[0]


# --- Inside the soundings' coverage ----------------------------------------------------------
#
# A point far from every sounding lies past the last track or in a patch the tracks leave open
# inside the survey. The empty angle around it tells the two apart only locally, and calls a patch
# where the tracks run far apart "past the last track" too. The coverage settles it: on a grid of
# ENCLOSE_CELL_M, a cell of sea is covered where estimate() answers all through it, beside a track,
# by its empty angle, or in the finer surveys' water. Uncovered sea lies inside the coverage where
# the covered cells ring it on every side, so no path through open sea reaches the coast or the
# edge of the surveys' extent, or where it is a strip narrower than twice NARROW_CELLS between
# covered cells, the open sea's own rim along them excepted. Counting a cell's angle as covered rings a patch between tracks
# that fan out as well as one between tracks that meet. Every cell counted covered answers all
# through, so a point refused inside a ring always sits in a cell of the patch.

ENCLOSE_CELL_M = 50.0
NARROW_CELLS = 2   # a strip of uncovered sea up to twice this many cells wide, 200 m, lies inside

_enc = None


def _land_rows(x0, y0, cols, rows, cell):
    """bytearray(cols * rows), 1 where a cell's centre lies on OpenStreetMap's land, filled row by
    row between the crossings of the land polygons' rings."""
    land = bytearray(cols * rows)
    cross = defaultdict(list)
    for _, rings in shapes.polygons("land", 12.15, -68.30, 80):
        for r in rings:
            pts = [dcbd.utm(la, lo) for lo, la in r]
            for (ax, ay), (bx, by) in zip(pts, pts[1:] + pts[:1]):
                if ay == by:
                    continue
                lo_r = math.ceil((min(ay, by) - y0) / cell - 0.5)
                hi_r = math.floor((max(ay, by) - y0) / cell - 0.5)
                for rr in range(max(0, lo_r), min(rows - 1, hi_r) + 1):
                    yc = y0 + (rr + 0.5) * cell
                    if (ay <= yc < by) or (by <= yc < ay):
                        cross[rr].append(ax + (yc - ay) * (bx - ax) / (by - ay))
    for rr, xs in cross.items():
        xs.sort()
        for a, b in zip(xs[0::2], xs[1::2]):
            c0 = max(0, math.ceil((a - x0) / cell - 0.5))
            c1 = min(cols - 1, math.floor((b - x0) / cell - 0.5))
            for c in range(c0, c1 + 1):
                land[rr * cols + c] = 1
    return land


def _enclosure():
    """(mask, x0, y0, cols, rows): one byte per ENCLOSE_CELL_M cell over BOX in UTM zone 19N,
    1 where the cell lies inside the soundings' coverage. Worked out once, about 20 seconds, and kept in enclosed.bin beside the surveys, worked out again whenever a
    survey, the DCBD grid or the coastline changes."""
    global _enc
    if _enc is not None:
        return _enc
    cell = ENCLOSE_CELL_M
    corners = [dcbd.utm(la, lo) for la in (BOX[0], BOX[2]) for lo in (BOX[1], BOX[3])]
    x0, y0 = min(c[0] for c in corners), min(c[1] for c in corners)
    cols = int((max(c[0] for c in corners) - x0) // cell) + 1
    rows = int((max(c[1] for c in corners) - y0) // cell) + 1
    d = data()
    stamp = json.dumps({"surveys": d["surveys"], "nlhs": nlhs.grid()["id"],
                        "dcbd": {k: dcbd.index().get(k) for k in ("fetched", "zip_size", "member")},
                        "coast": sum(len(v) for v in _coastline().values()),
                        "cell": cell, "narrow": NARROW_CELLS, "beside": BESIDE_M, "reach": REACH_M,
                        "open": OPEN_DEG}, sort_keys=True).encode()
    path = os.path.join(DB, "enclosed.bin")
    if os.path.exists(path):
        with open(path, "rb") as f:
            raw = f.read()
        head = raw[:raw.index(b"\n")] if b"\n" in raw else b""
        body = raw[len(head) + 1:]
        if head == stamp and len(body) == cols * rows:
            _enc = (bytearray(body), x0, y0, cols, rows)
            return _enc
    if sys.stderr.isatty():
        print(f"working out where the {NAME} cover the sea, once, about 20 seconds ...",
              file=sys.stderr, flush=True)
    # a cell counts as covered only where estimate() answers at every point inside it, so a point
    # it refuses never sits in a covered cell: within its half diagonal, a point is that much
    # nearer or farther from each sounding, and sees each sounding farther than BESIDE_M less the
    # half diagonal turned by at most `turn`
    half = cell * math.sqrt(0.5)
    turn = math.degrees(math.asin(half / (BESIDE_M - half)))
    covered = bytearray(cols * rows)
    k = int(BESIDE_M // cell) + 2
    for x, y, _ in d["points"]:
        ci, cj = int((x - x0) // cell), int((y - y0) // cell)
        for i in range(max(0, ci - k), min(cols, ci + k + 1)):
            for j in range(max(0, cj - k), min(rows, cj + k + 1)):
                if math.hypot(x0 + (i + 0.5) * cell - x, y0 + (j + 0.5) * cell - y) <= BESIDE_M - half:
                    covered[j * cols + i] = 1
    # the finer surveys' water: a cell holding it, with its four neighbours holding it too
    wet = bytearray(cols * rows)

    def mark(x, y):
        i, j = int((x - x0) // cell), int((y - y0) // cell)
        if 0 <= i < cols and 0 <= j < rows:
            wet[j * cols + i] = 1
    t = dcbd.tile()
    mask, mrows, mcols = dcbd.wet_mask()
    bm = dcbd.WET_BLOCK * t.sx
    for r in range(mrows):
        for c in range(mcols):
            if mask[r * mcols + c]:
                mark(t.x0 + (c + 0.5) * bm, t.y0 - (r + 0.5) * dcbd.WET_BLOCK * t.sy)
    for (i, j) in nlhs.grid()["cells"]:
        mark(i * nlhs.CELL, j * nlhs.CELL)
    for p in range(cols * rows):
        i = p % cols
        if wet[p] and 0 < i < cols - 1 and cols <= p < (rows - 1) * cols and \
                wet[p - 1] and wet[p + 1] and wet[p - cols] and wet[p + cols]:
            covered[p] = 1
    land = _land_rows(x0, y0, cols, rows, cell)
    # sea farther than BESIDE_M from the tracks that estimate() answers by its empty angle: the
    # soundings within REACH_M less the half diagonal leave no empty angle of OPEN_DEG less twice
    # `turn` at the cell's centre
    for p in range(cols * rows):
        if covered[p] or land[p]:
            continue
        x, y = x0 + (p % cols + 0.5) * cell, y0 + (p // cols + 0.5) * cell
        near = _around(x, y, REACH_M - half)
        if near and _widest([math.degrees(math.atan2(q[1] - y, q[0] - x)) for _, q in near]) < OPEN_DEG - 2 * turn:
            covered[p] = 1
    # the open sea: uncovered sea farther than NARROW_CELLS from every covered cell, flooded from
    # the coast and the extent's edge, then widened by NARROW_CELLS back toward the covered cells;
    # what it never reaches, a patch the covered cells ring or a strip narrower than twice
    # NARROW_CELLS between them, lies inside the coverage
    n = cols * rows
    eight = (-1, 1, -cols, cols, -cols - 1, -cols + 1, cols - 1, cols + 1)

    def spread(start, steps, through):
        """Distance in cells, eight ways, from the cells of `start`, out to `steps` through the
        cells `through` allows; 255 beyond."""
        dist = bytearray([255]) * n
        front = [p for p in range(n) if start[p]]
        for p in front:
            dist[p] = 0
        for step in range(1, steps + 1):
            nxt = []
            for p in front:
                i = p % cols
                for o in eight:
                    q = p + o
                    if 0 <= q < n and abs(q % cols - i) <= 1 and dist[q] == 255 and through(q):
                        dist[q] = step
                        nxt.append(q)
            front = nxt
        return dist
    near = spread(covered, NARROW_CELLS, lambda q: True)
    core = bytearray(1 if land[p] or near[p] == 255 else 0 for p in range(n))
    edge = set(range(cols)) | set(range(n - cols, n)) | set(range(0, n, cols)) | set(range(cols - 1, n, cols))
    reached = bytearray(n)
    stack = [p for p in range(n) if core[p] and (land[p] or p in edge)]
    for p in stack:
        reached[p] = 1
    while stack:
        p = stack.pop()
        i = p % cols
        for q in ((p - 1) if i else -1, (p + 1) if i < cols - 1 else -1, p - cols, p + cols):
            if 0 <= q < n and not reached[q] and core[q]:
                reached[q] = 1
                stack.append(q)
    outside = spread(reached, NARROW_CELLS, lambda q: not covered[q])
    enc = bytearray(1 if not (covered[p] or land[p]) and outside[p] == 255 else 0 for p in range(n))
    with open(path + ".part", "wb") as f:
        f.write(stamp + b"\n" + bytes(enc))
    os.replace(path + ".part", path)
    _enc = (enc, x0, y0, cols, rows)
    return _enc


def enclosed(x, y):
    """Whether UTM (x, y) lies inside the soundings' coverage: in a patch of sea the covered cells
    ring on every side, or a strip of it narrower than twice NARROW_CELLS between them."""
    enc, x0, y0, cols, rows = _enclosure()
    i, j = int((x - x0) // ENCLOSE_CELL_M), int((y - y0) // ENCLOSE_CELL_M)
    return 0 <= i < cols and 0 <= j < rows and enc[j * cols + i] == 1


def _around(x, y, reach_m=REACH_M):
    """[(distance, point)] within reach_m, nearest first."""
    idx, k = data()["index"], int(reach_m // BUCKET_M) + 1
    bi, bj = int(x // BUCKET_M), int(y // BUCKET_M)
    out = [(math.hypot(q[0] - x, q[1] - y), q) for i in range(bi - k, bi + k + 1)
           for j in range(bj - k, bj + k + 1) for q in idx.get((i, j), ())]
    return sorted(o for o in out if o[0] <= reach_m)


def _widest(bearings):
    """The widest empty angle, in degrees, between bearings around a point."""
    b = sorted(set(round(v, 1) % 360 for v in bearings))
    if not b:
        return 360.0
    return max([b[0] + 360 - b[-1]] + [b2 - b1 for b1, b2 in zip(b, b[1:])])


def _finer_bearings(x, y):
    """Bearings from UTM (x, y) to the finer surveys' water within FINER_M: DCBD's 20 m blocks of
    water and the 2019 survey's cells."""
    out = []
    t = dcbd.tile()
    mask, rows, cols = dcbd.wet_mask()
    bm = dcbd.WET_BLOCK * t.sx
    row, col = dcbd.pixel_utm(t, x, y)
    br, bc, k = row // dcbd.WET_BLOCK, col // dcbd.WET_BLOCK, int(FINER_M / bm) + 1
    for r in range(max(0, br - k), min(rows, br + k + 1)):
        for c in range(max(0, bc - k), min(cols, bc + k + 1)):
            if mask[r * cols + c]:
                dx, dy = t.x0 + (c + 0.5) * bm - x, t.y0 - (r + 0.5) * bm - y
                if dx * dx + dy * dy <= FINER_M * FINER_M:
                    out.append(math.degrees(math.atan2(dy, dx)))
    cells, kc = nlhs.grid()["cells"], int(FINER_M / nlhs.CELL) + 1
    i0, j0 = round(x / nlhs.CELL), round(y / nlhs.CELL)
    for i in range(i0 - kc, i0 + kc + 1):
        for j in range(j0 - kc, j0 + kc + 1):
            if (i, j) in cells:
                dx, dy = i * nlhs.CELL - x, j * nlhs.CELL - y
                if dx * dx + dy * dy <= FINER_M * FINER_M:
                    out.append(math.degrees(math.atan2(dy, dx)))
    return out


def estimate(x, y):
    """(depth, nearest sounding's distance, soundings used) at UTM (x, y), or None past the last
    track: farther than BESIDE_M from every sounding, where the soundings within REACH_M, with the
    finer surveys' water within FINER_M as more directions, leave an empty angle of OPEN_DEG or
    more around it, and outside the soundings' coverage (enclosed())."""
    near = _around(x, y)
    if near and near[0][0] < 0.5:
        return near[0][1][2], near[0][0], 1
    if not near or near[0][0] > BESIDE_M:
        bearings = [math.degrees(math.atan2(q[1] - y, q[0] - x)) for _, q in near]
        if _widest(bearings) >= OPEN_DEG and _widest(bearings + _finer_bearings(x, y)) >= OPEN_DEG:
            if not enclosed(x, y):
                return None
            # inside the coverage with the soundings to one side: look farther for NEAREST of them
            reach = REACH_M
            while len(near) < NEAREST and reach < 4 * REACH_M:
                reach *= 2
                near = _around(x, y, reach)
    if not near:
        return None
    use = near[:NEAREST]
    w = [1 / d ** 2 for d, _ in use]
    return sum(wi * q[2] for wi, (_, q) in zip(w, use)) / sum(w), near[0][0], len(use)


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
                "why": f"past the last track of the {NAME}: no sounding within {BESIDE_M:.0f} m, the "
                       f"soundings within {REACH_M:.0f} m, with the finer "
                       f"surveys' water within {FINER_M:.0f} m, leave an empty angle of {OPEN_DEG:.0f}° or more around "
                       f"the point, and open sea joins it to the coast or the surveys' edge{where}"}
    z, d, used = e
    return {**out, "water": "sea", "depth": z, "datum": dcbd.DATUM,
            "detail": f"interpolated from the {used} nearest soundings, the nearest "
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

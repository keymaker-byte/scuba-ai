"""The Royal Netherlands Navy Hydrographic Service's 2019 multibeam survey of Bonaire (survey
HY191121-22-23-24), for the depth tool: its 20 m grid of mean depths below LAT, ordered by hand
from SeaDataNet and kept on this machine, read between cell centres, and lined up with the DCBD
coastal bathymetry by the offset measured where both surveys hold flat bottom.

SeaDataNet hands the survey out only behind a login and an order, so there is no download to
make: a missing file stops the run with the steps to order it and the folder to save it in."""
import glob
import json
import math
import os
import re
import statistics
import sys
import zipfile
from datetime import date

from lib import dcbd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


DB = os.path.join(ROOT, "tools", "db", "depth", "nlhs")


OFFSET = os.path.join(DB, "offset.json")   # the measured offset to DCBD, and the files it was measured on


NAME = "Royal Netherlands Navy multibeam survey of Bonaire"


SURVEY = "HY191121-22-23-24"


RECORD_URL = "https://cdi-bathymetry.seadatanet.org/report/edmo/574/hy191121-22-23-24"


SEARCH_URL = "https://cdi-bathymetry.seadatanet.org/search"


CREDIT = "Royal Netherlands Navy Hydrographic Service, survey HY191121-22-23-24, CC BY 4.0, via SeaDataNet"


MEMBER = re.compile(r"_XYZ_HY191121-22-23-24_V(\d+)\.txt$")   # the soundings file inside SeaDataNet's order zip


BOX = (12.0185, -68.4128, 12.2262, -68.1884)   # the survey's extent, S W N E, from SeaDataNet's record


CELL = 20.0   # metres: the survey's grid, cell centres on multiples of 20 m in WGS 84 / UTM zone 19N


SEARCH_M = 100   # how far a point with no data searches for the nearest cell that has some


SPREAD_M = 20    # the spread of depths reported around a point: the cells within it


# The cells the offset to DCBD is measured on: bottom flat in both surveys, where a few metres of
# position cannot move the depth. A Navy cell and its 8 neighbours within NAVY_RELIEF_M of each other,
# no deeper than MAX_DEPTH_M, and DCBD's 2 m pixels over the 40 m square around it holding at least
# DCBD_MIN_PIXELS with data, within DCBD_RELIEF_M of each other.
NAVY_RELIEF_M = 3.0
DCBD_RELIEF_M = 3.0
DCBD_HALF_M = 19
DCBD_MIN_PIXELS = 300
MAX_DEPTH_M = 22.0
MIN_CELLS = 30   # fewer flat shared cells than this, and the offset is not measured


def how_to_get():
    """The steps to order the survey from SeaDataNet and where to save it."""
    return f"""the {NAME} is not on this machine.

SeaDataNet hands it out only behind a free login and an order, so it is fetched by hand:

  1. Open {SEARCH_URL}
  2. Log in: choose "EGI Check-in - EOSC AAI", then sign in with Google, GitHub or ORCID. The
     first time, complete the profile (Organisation may be "Private individual") and accept
     the SeaDataNet licence.
  3. Search for {SURVEY}. One result, "Bonaire", Royal Netherlands Navy, Hydrographic Service,
     multi-beam echosounders, 2019-11-19. Add it to the basket.
  4. Open the basket, name the order, choose XYZ as the format, give a short motivation, and
     submit. The survey is unrestricted (CC BY 4.0), so the order is ready within minutes.
  5. Under "My standing orders", open the order and download RECORDS (a zip of about 560 KB,
     named order_<number>_unrestricted.zip).
  6. Save the zip, unopened, into
       {DB}/
     The record describing the survey is {RECORD_URL}"""


def _find():
    """(path, member, version) of the newest soundings file here: a SeaDataNet order zip holding
    it, or the text file itself. None when there is none."""
    found = []
    for z in glob.glob(os.path.join(DB, "*.zip")):
        try:
            with zipfile.ZipFile(z) as f:
                for n in f.namelist():
                    m = MEMBER.search(n)
                    if m:
                        found.append((int(m.group(1)), z, n))
        except zipfile.BadZipFile:
            continue
    for t in glob.glob(os.path.join(DB, "*.txt")):
        m = MEMBER.search(os.path.basename(t))
        if m:
            found.append((int(m.group(1)), t, None))
    if not found:
        return None
    v, path, member = max(found)
    return path, member, v


def _dms(s):
    """12-01-06.795227N to decimal degrees."""
    d, m, sec = s[:-1].split("-")
    v = int(d) + int(m) / 60 + float(sec) / 3600
    return -v if s[-1] in "SW" else v


_grid = None


def grid():
    """{(i, j): depth below LAT} keyed by the cell centre's UTM zone 19N metres over CELL, with
    the file read: {"path", "member", "version", "cells", "id"}. Stops the run with how_to_get()
    when the survey is missing."""
    global _grid
    if _grid is not None:
        return _grid
    hit = _find()
    if hit is None:
        sys.exit(f"{NAME}: {how_to_get()}")
    path, member, version = hit
    try:
        if member:
            with zipfile.ZipFile(path) as z:
                info = z.getinfo(member)
                text = z.read(member).decode("ascii")
                ident = {"file": os.path.basename(path), "member": member, "size": info.file_size, "crc": info.CRC}
        else:
            with open(path) as f:
                text = f.read()
            ident = {"file": os.path.basename(path), "member": None, "size": len(text), "crc": None}
    except (OSError, zipfile.BadZipFile, UnicodeDecodeError, KeyError) as e:
        sys.exit(f"{NAME}: cannot read {path} ({e}). Delete it and order the survey again:\n\n{how_to_get()}")
    cells = {}
    for line in text.splitlines():
        p = line.split()
        if len(p) != 3 or not p[2][:1].isdigit():
            continue   # the header line
        x, y = dcbd.utm(_dms(p[0]), _dms(p[1]))
        cells[(round(x / CELL), round(y / CELL))] = float(p[2])
    if not cells:
        sys.exit(f"{NAME}: {path} holds no soundings. Delete it and order the survey again:\n\n{how_to_get()}")
    _grid = {"cells": cells, "path": path, "member": member, "version": version, "id": ident}
    return _grid


def in_box(lat, lon):
    s, w, n, e = BOX
    return s <= lat <= n and w <= lon <= e


def raw(x, y):
    """Depth below LAT at UTM (x, y), interpolated between the four cell centres around it, or the
    cell the point falls in where one of the four is missing at the survey's edge; None where that
    cell has no data either."""
    cells = grid()["cells"]
    i0, j0 = math.floor(x / CELL), math.floor(y / CELL)
    fx, fy = x / CELL - i0, y / CELL - j0
    corners = [cells.get((i0 + a, j0 + b)) for a, b in ((0, 0), (1, 0), (0, 1), (1, 1))]
    if None not in corners:
        z00, z10, z01, z11 = corners
        return (z00 * (1 - fx) + z10 * fx) * (1 - fy) + (z01 * (1 - fx) + z11 * fx) * fy
    return cells.get((round(x / CELL), round(y / CELL)))


# --- The offset to DCBD ----------------------------------------------------------------------

def _measure():
    """{offset_m, cells, p10_m, p90_m}: DCBD's depth minus the Navy's below LAT over every cell
    flat in both surveys, its median the offset added to every Navy depth."""
    cells, t = grid()["cells"], dcbd.tile()
    diffs = []
    for (i, j), z in cells.items():
        if z > MAX_DEPTH_M:
            continue
        nb = [cells.get((i + a, j + b)) for a in (-1, 0, 1) for b in (-1, 0, 1) if a or b]
        if None in nb or max(nb) - min(nb) > NAVY_RELIEF_M:
            continue
        x, y = i * CELL, j * CELL
        vals = []
        for dx in range(-DCBD_HALF_M, DCBD_HALF_M + 1, 2):
            for dy in range(-DCBD_HALF_M, DCBD_HALF_M + 1, 2):
                row, col = dcbd.pixel_utm(t, x + dx, y + dy)
                v = t.value(row, col)
                if v is not None and v < 0:
                    vals.append(-v)
        if len(vals) < DCBD_MIN_PIXELS or max(vals) - min(vals) > DCBD_RELIEF_M:
            continue
        diffs.append(statistics.mean(vals) - z)
    if len(diffs) < MIN_CELLS:
        sys.exit(f"{NAME}: only {len(diffs)} cells hold flat bottom in both this survey and the "
                 f"{dcbd.NAME}, fewer than the {MIN_CELLS} the offset between them is measured on. "
                 "Stop and report it.")
    diffs.sort()
    return {"offset_m": round(statistics.median(diffs), 2), "cells": len(diffs),
            "p10_m": round(diffs[len(diffs) // 10], 2), "p90_m": round(diffs[9 * len(diffs) // 10], 2)}


_offset = None


def offset():
    """The measured offset to DCBD, kept in OFFSET with the two files it was measured on and
    measured again whenever either changes."""
    global _offset
    if _offset is not None:
        return _offset
    on = {"navy": grid()["id"], "dcbd": {k: dcbd.index()[k] for k in ("fetched", "zip_size", "member")}}
    if os.path.exists(OFFSET):
        with open(OFFSET) as f:
            doc = json.load(f)
        if doc.get("on") == on:
            _offset = doc
            return doc
    if sys.stderr.isatty():
        print(f"measuring the offset between the {NAME} and the {dcbd.NAME}, about a minute ...",
              file=sys.stderr, flush=True)
    doc = {**_measure(), "measured": date.today().isoformat(), "on": on}
    with open(OFFSET + ".part", "w") as f:
        json.dump(doc, f, indent=1)
    os.replace(OFFSET + ".part", OFFSET)
    _offset = doc
    return doc


def offset_note():
    o = offset()
    return (f"lined up with the {dcbd.NAME} by +{o['offset_m']:.2f} m, the median difference over "
            f"{o['cells']} cells flat in both surveys (p10 {o['p10_m']:+.2f}, p90 {o['p90_m']:+.2f} m)")


def depth(x, y):
    """Depth at UTM (x, y) lined up with DCBD, or None where the survey has no data."""
    z = raw(x, y)
    return None if z is None else z + offset()["offset_m"]


# --- The depth at a point --------------------------------------------------------------------

COMPASS = dcbd.COMPASS


def _nearest(x, y, limit_m):
    """(distance, dx, dy, depth below LAT) of the nearest cell centre with data within limit_m."""
    cells, best = grid()["cells"], None
    k = int(limit_m / CELL) + 1
    i0, j0 = round(x / CELL), round(y / CELL)
    for i in range(i0 - k, i0 + k + 1):
        for j in range(j0 - k, j0 + k + 1):
            z = cells.get((i, j))
            if z is None:
                continue
            d = math.hypot(i * CELL - x, j * CELL - y)
            if d <= limit_m and (best is None or d < best[0]):
                best = (d, i * CELL - x, j * CELL - y, z)
    return best


def _spread(x, y):
    cells = grid()["cells"]
    k = int(SPREAD_M / CELL) + 1
    i0, j0 = round(x / CELL), round(y / CELL)
    zs = [cells[(i, j)] for i in range(i0 - k, i0 + k + 1) for j in range(j0 - k, j0 + k + 1)
          if (i, j) in cells and math.hypot(i * CELL - x, j * CELL - y) <= SPREAD_M]
    return (min(zs), max(zs)) if zs else None


def answer(lat, lon):
    """The depth at a point lined up with DCBD, a plain observed depth: {water, depth, datum,
    detail, why, nodata, dem}. water is "sea", or "none" with why and nodata where the survey has
    no cell at the point, naming the nearest that has one."""
    x, y = dcbd.utm(lat, lon)
    z = raw(x, y)
    o = offset()["offset_m"]
    r = {"source": f"20 m grid, V{grid()['version']}", "res_m": CELL, "lat_m": z}
    out = {"dem": r, "depth": None, "datum": None, "detail": None, "why": None}
    if z is None:
        near = _nearest(x, y, SEARCH_M)
        where = (f"; the nearest cell is {near[0]:.0f} m toward {dcbd._bearing(near[1], near[2])}, "
                 f"seabed {near[3] + o:.1f} m" if near else f"; none within {SEARCH_M} m")
        return {**out, "water": "none", "nodata": True,
                "why": f"no cell of the {NAME} at this point (unsurveyed, or outside the survey){where}"}
    s = _spread(x, y)
    around = f"; cells within {SPREAD_M} m, {s[0] + o:.1f} to {s[1] + o:.1f} m" if s else ""
    return {**out, "water": "sea", "depth": z + o, "datum": dcbd.DATUM,
            "detail": f"{z:.1f} m below LAT in the survey, interpolated between its cell centres, "
                      f"{offset_note()}{around}"}


def fetch(boxes, workers):
    """Nothing to download: the survey is ordered by hand. Says whether it is here when a box
    touches it; the number missing."""
    if not any(bs < BOX[2] and bn > BOX[0] and bw < BOX[3] and be > BOX[1] for bs, bw, bn, be in boxes):
        print("no box touches the survey's extent; nothing to do")
        return 0
    hit = _find()
    if hit is None:
        print(f"  {how_to_get()}")
        return 1
    print(f"the survey touches the boxes and is already here: {os.path.basename(hit[0])}")
    offset()
    return 0


def verify(lat, lon, r):
    """SeaDataNet serves the survey only behind a login, so there is no live service to compare
    with. Says what is held and where to check for a newer version by hand."""
    g = grid()
    print(f"  this copy: {g['id']['file']}" + (f", {g['member']}" if g["member"] else "")
          + f", version V{g['version']}, {len(g['cells'])} cells")
    print(f"  NOT CHECKED: SeaDataNet serves this survey only behind a login. Open {RECORD_URL} and "
          f"compare its CDI version with V{g['version']}; on a newer one, delete {DB}/ and order it again.")
    return True


def selftest():
    """Every sounding on a cell centre of the 20 m UTM grid within 5 cm, and the depth read back at
    each cell centre equal to its own."""
    g = grid()
    text = (zipfile.ZipFile(g["path"]).read(g["member"]).decode("ascii") if g["member"]
            else open(g["path"]).read())
    worst, n = 0.0, 0
    for line in text.splitlines():
        p = line.split()
        if len(p) != 3 or not p[2][:1].isdigit():
            continue
        x, y = dcbd.utm(_dms(p[0]), _dms(p[1]))
        worst = max(worst, abs(x - round(x / CELL) * CELL), abs(y - round(y / CELL) * CELL))
        n += 1
    back = max(abs(raw(i * CELL, j * CELL) - z) for (i, j), z in g["cells"].items())
    ok = worst <= 0.05 and back <= 1e-9 and n == len(g["cells"])
    print(f"  {n} soundings, {len(g['cells'])} cells; farthest from a cell centre {worst * 100:.1f} cm; "
          f"read back at the centres within {back:.1e} m")
    print("  PASS" if ok else "  FAIL")
    return ok

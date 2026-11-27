#!/usr/bin/env python3
"""The map viewer's data layers, over the areas in map/coverage.json: the tidal current, the
depth, and the tides the depth layer adds to it. Each layer is computed with the library functions
the tools answer with, and carries values those functions gave at sample points, which the browser
reproduces before it draws anything: a point read on the map is the answer the tools give there.
The map names no datum: it shows the total depth, the seabed plus the tide.

  map_export.py                 every layer
  map_export.py depth           map/depth/tiles/ and map/depth/depth.js
  map_export.py tides           map/tides/stations.js
  map_export.py currents        map/currents/<area>-seafloor.js and map/currents/index.js
  map_export.py publish         every layer zipped into a GitHub release, online with the next push to main
  map_export.py depth --area bonaire    one area's depth tiles alone, keeping every other area's

Every source is downloaded first, the first time a layer needs it, so a first export runs long:
a CHS tide station is fitted in about three minutes. Every run after reads them locally."""
import argparse
import array
import base64
import json
import math
import os
import random
import shutil
import sys
import time
from datetime import date, datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lib.tidal_astronomy as astro  # noqa: E402
from lib import chs_tides, foreman, map_depth, shapes, tide  # noqa: E402
from lib.adcirc import WALK_STEP_M, read_vel_header, read_vel_nodes  # noqa: E402
from lib.blend import (ABOVE_BOTTOM, DEG, EXACT_KM, EXTEND_KM, LINE_STEP_M, MIN_AMP, NEIGHBOURS,  # noqa: E402
                       PRIOR, REACH_KM, SOFTEN_KM, UTC, Mesh, Refused, blend_at, extract_point, floor_km,
                       load_region, log, make_bin, neighbours, profile_table, source_bins, to_noaa)
from lib.current_harmonics import prepare as current_prepare, speed  # noqa: E402
from lib.datums import CHS, MLLW  # noqa: E402
from lib.seabed import Seabed  # noqa: E402
from lib.tidal_astronomy import CONS  # noqa: E402
from lib.tide_harmonics import RATE, height, prepare  # noqa: E402

WORKSPACE = os.path.dirname(HERE)
COVERAGE = os.path.join(WORKSPACE, "map", "coverage.json")
MAP_YEARS_BACK, MAP_YEARS_AHEAD = 1, 10  # the years the map's astronomy is prepared for


def coverage():
    """The areas the map covers: [{name, label, boxes: [[S, W, N, E], ...]}]. These are the map's
    own areas, set for the water its layers draw, apart from the regions sites are written in."""
    try:
        with open(COVERAGE) as f:
            areas = json.load(f)["areas"]
    except (OSError, ValueError, KeyError) as e:
        sys.exit(f"Could not read {os.path.relpath(COVERAGE, WORKSPACE)}: {e}")
    for ar in areas:
        if not ar.get("name") or not ar.get("label") or not ar.get("boxes"):
            sys.exit(f"Every area in {os.path.relpath(COVERAGE, WORKSPACE)} needs a name, a label and boxes.")
        for b in ar["boxes"]:
            if len(b) != 4 or not (b[0] < b[2] and b[1] < b[3]):
                sys.exit(f"{ar['name']}: a box is [south, west, north, east], got {b}.")
    return areas


def _blend_cfg(key, default):
    """The current tool's own setting in tool-config.json, which the current layer colours by."""
    try:
        with open(os.path.join(WORKSPACE, "tool-config.json")) as f:
            return json.load(f).get("current", {}).get(key, default)
    except (OSError, ValueError):
        return default


# --- the tidal current layer -----------------------------------------------------------------

MAP_SHORE_CHECKS = 20     # sample points just off the mesh's shoreline the browser reproduces, over the area
CELL_POINT_CHECKS = 3     # sample points inside its own elements each cell carries
CHUNK_NODES = 4000        # a cell is split in four while it owns more nodes than this
CHUNK_MIN_DEG = 0.05      # and while it is taller than this
HALO_KM = EXTEND_KM + 1.0  # the mesh a cell carries past its own box: as far as a point in it reaches, and a margin
CURRENT_MIN_ZOOM = 9      # the viewer loads cells from this zoom in, those in view


def b64(arr):
    """A typed array as little-endian base64, as the browser decodes it."""
    if sys.byteorder != "little":
        arr = array.array(arr.typecode, arr)
        arr.byteswap()
    return base64.b64encode(arr.tobytes()).decode("ascii")


def map_overlays():
    """Every overlay entry in map/currents/index.js: name, label, file and boxes."""
    path = os.path.join(WORKSPACE, "map", "currents", "index.js")
    if not os.path.exists(path):
        return []
    with open(path) as fh:
        src = fh.read()
    try:
        return json.loads(src[src.index("[", src.index("MAP_CURRENT_INDEX")):src.rindex("]") + 1])
    except ValueError as e:
        sys.exit(f"Could not read {path}: {e}. Delete it and run map_export.py currents again.")


def write_index(entry):
    """Add or replace `entry` in map/currents/index.js, the list of every overlay the map reads at
    load, keeping the others."""
    index_path = os.path.join(WORKSPACE, "map", "currents", "index.js")
    entries = map_overlays()
    entries = [e for e in entries if e["name"] != entry["name"]] + [entry]
    entries.sort(key=lambda e: e["name"])
    with open(index_path, "w") as fh:
        fh.write("// Generated by tools/map_export.py: every tidal current overlay.\n")
        fh.write("window.MAP_CURRENT_INDEX = ")
        fh.write(json.dumps(entries, indent=2))
        fh.write(";\n")
    log(f"  updated {os.path.relpath(index_path, WORKSPACE)} ({len(entries)} overlay(s))")


def drop_index(name):
    """Remove one overlay's entry from map/currents/index.js."""
    path = os.path.join(WORKSPACE, "map", "currents", "index.js")
    entries = [e for e in map_overlays() if e["name"] != name]
    with open(path, "w") as fh:
        fh.write("// Generated by tools/map_export.py: every tidal current overlay.\n")
        fh.write("window.MAP_CURRENT_INDEX = ")
        fh.write(json.dumps(entries, indent=2))
        fh.write(";\n")


MASK_M = 37.5   # m: the land mask's cell, a quarter of the map's drawing grid


def land_mask(S, W, N, E):
    """The coastline over a box, for the map viewer to keep its trails off land: rows evenly
    spaced in Web Mercator and columns in longitude, MASK_M apart, each row holding the columns
    where it crosses the coastline (OpenStreetMap's land polygons, through lib/shapes.py). A
    point is on land where an odd number of its row's crossings lie west of it."""
    merc = lambda lat: math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
    d_lon = MASK_M / (111320 * math.cos(math.radians((S + N) / 2)))
    d_y = math.radians(d_lon)
    y_n = merc(N)
    rows = math.ceil((y_n - merc(S)) / d_y)
    cols = math.ceil((E - W) / d_lon)
    if cols > 65535:
        sys.exit(f"the land mask is {cols} columns wide, past its 16-bit index; split the box.")
    lats = [math.degrees(2 * math.atan(math.exp(y_n - (r + 0.5) * d_y)) - math.pi / 2) for r in range(rows)]
    log(f"  land mask: {rows} x {cols} cells of {MASK_M:g} m from the coastline...")
    xs = shapes.crossings("land", S, W, N, E, lats)
    offsets, cross = array.array("I", [0]), array.array("H")
    for row in xs:
        cross.extend(min(cols, max(0, round((x - W) / d_lon))) for x in row)
        offsets.append(len(cross))
    if sys.byteorder != "little":
        offsets.byteswap()
        cross.byteswap()
    b64 = lambda arr: base64.b64encode(arr.tobytes()).decode("ascii")
    return {"W": W, "yN": y_n, "dLon": d_lon, "rows": rows, "cols": cols,
            "offsets": b64(offsets), "crossings": b64(cross)}


def export_currents(area):
    """The map viewer's seafloor overlay: everything the browser needs to run the tool's own
    blend at any point, the database's constants at every mesh node in the boxes, the stations'
    corrections, the vertical profile and each node's distances through the water to the
    stations, with the astronomy prepared for each year the map may show. The browser computes
    the current at a point exactly as `extract` and `at` do there; the trails it draws run along
    each node's own blended axis. The area's boxes cut it; within them, every mesh element whose
    corners all have a seabed depth. It is written as cells the viewer loads as they come into
    view (map/currents/<area>-seafloor/<cell>.js), beside one file every cell shares (common.js):
    the stations, the astronomy and the coastline. Each cell carries values the tool computed at
    its own sample nodes and points, which the browser reproduces before the cell draws. It reads
    the region and its sources, never a site file."""
    name, label, boxes = area["name"] + "-seafloor", area["label"] + " seafloor", area["boxes"]
    S, W = min(b[0] for b in boxes), min(b[1] for b in boxes)
    N, E = max(b[2] for b in boxes), max(b[3] for b in boxes)
    reg = load_region(lat=(S + N) / 2, lon=(W + E) / 2)
    rS, rW, rN, rE = reg["bbox"]
    if not (rS <= S and rW <= W and rN >= N and rE >= E):
        sys.exit(f"{area['name']}: its boxes reach past the current tool's {reg['name']} region "
                 f"({rS}, {rW}, {rN}, {rE}); rebuild that region over them with current.py build --name "
                 f"{reg['name']} --bbox S W N E, then run the export again.")
    sources = reg["sources"]
    mesh = Mesh(reg["db"], reg["bbox"])
    lon, lat = mesh.lon, mesh.lat
    inside = lambda i: any(bs <= lat[i] <= bn and bw <= lon[i] <= be for bs, bw, bn, be in boxes)
    tris = [n for n in mesh.elems if inside(n[0]) or inside(n[1]) or inside(n[2])]
    # the mesh's own shoreline: an edge with an end inside the boxes has every element it borders
    # among these, so one that borders a single element is the mesh's edge, not the boxes' cut
    count = {}
    for t in tris:
        for x, y in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
            k = (x, y) if x < y else (y, x)
            count[k] = count.get(k, 0) + 1
    shore = {i for (x, y), c in count.items() if c == 1 and (inside(x) or inside(y)) for i in (x, y)}
    seabed = Seabed()
    elev = {}
    for n in sorted({i for t in tris for i in t}):
        e, _ = seabed.elevation(lat[n], lon[n])
        if e is not None:
            elev[n] = e
    tris = [t for t in tris if all(i in elev for i in t)]
    nodes = sorted({i for t in tris for i in t})
    if not nodes:
        sys.exit(f"{area['name']}: no mesh node in its boxes has a seabed depth from a bathymetry.")
    wide = len(nodes) > 65535   # the triangles' node index: 16 bits, or 32 for a large mesh
    index = {n: j for j, n in enumerate(nodes)}
    log(f"  {len(nodes)} nodes with a seabed depth, {len(tris)} elements")
    hab = ABOVE_BOTTOM
    # each node's seabed for the trails: its own, or, at a corner on land or in water shallower
    # than the height, the deepest water at the middle of the elements around it, so the trails
    # along a shore run at the height above the shore's own seabed
    depth = {}
    around = {}
    for t in tris:
        for i in t:
            around.setdefault(i, []).append(t)
    for n in nodes:
        d = -elev[n]
        if d <= hab:
            mids = []
            for t in around[n]:
                e, _ = seabed.elevation(sum(lat[i] for i in t) / 3, sum(lon[i] for i in t) / 3)
                if e is not None and -e > hab:
                    mids.append(-e)
            d = max(mids) if mids else d
        depth[n] = d
    log("Paths through the water from every station...")
    near = {n: [] for n in nodes}
    for i, s in enumerate(sources):
        for n, d in mesh.paths(s["node"], REACH_KM).items():
            if n in near:
                near[n].append((d, i))
    log(f"Streaming the velocity file for {len(nodes)} nodes (a few minutes)...")
    header = read_vel_header(reg["db"])
    vals = read_vel_nodes(reg["db"], nodes)
    node_uv = {}
    for n in nodes:
        cons = [{"name": h[0], "f_ref": h[2], "v0u_deg": h[3], "u_amp": v[0], "u_phase": v[1],
                 "v_amp": v[2], "v_phase": v[3]} for h, v in zip(header, vals[n])]
        node_uv[n] = to_noaa(cons, reg["db"])
    keys = sorted(node_uv[nodes[0]])
    # the database's constants as int16 with one scale per node, its largest value, so weak
    # water keeps the shape of its tidal ellipse: east and north, real and imaginary, node by node
    scale = array.array("f", [max(max(abs(z.real), abs(z.imag)) for k in keys for z in node_uv[n][k]) / 32767 or 1.0
                              for n in nodes])
    q = array.array("h")
    for j, n in enumerate(nodes):
        for k in keys:
            zu, zv = node_uv[n][k]
            q.extend(int(round(x / scale[j])) for x in (zu.real, zu.imag, zv.real, zv.imag))
    deq = lambda j: {k: (complex(q[(j * len(keys) + m) * 4] * scale[j], q[(j * len(keys) + m) * 4 + 1] * scale[j]),
                         complex(q[(j * len(keys) + m) * 4 + 2] * scale[j], q[(j * len(keys) + m) * 4 + 3] * scale[j]))
                     for m, k in enumerate(keys)}
    # every constituent a prediction sums: the database's and the stations' own
    names = sorted(set(keys) | {c for s in sources for b in s["bins"] for c in b[3]})
    y0 = date.today().year - MAP_YEARS_BACK
    years = list(range(y0, date.today().year + MAP_YEARS_AHEAD + 1))
    prep = {y: current_prepare([[c, 1.0, 0.0, 0.0, 0.0] for c in names], y) for y in years}
    astronomy = {"epoch": astro.EPOCH.isoformat(), "names": names, "species": [CONS[c][0][0] for c in names],
                 "coef": [list(p[0]) for p in prep[years[0]]],
                 "years": {str(y): {"arg": [p[1] for p in pp], "f": [p[2] for p in pp]} for y, pp in prep.items()}}
    prof = profile_table(reg["profile_rows"])
    jc = lambda z: [z.real, z.imag]
    stations = []
    for s in sources:
        bins = [[frac, {c: jc(L) for c, L in Lc.items()}, {str(b): jc(L) for b, L in Lb.items()}, mean, turn,
                 {c: jc(z) for c, z in Z.items()}, az]
                for frac, Lc, Lb, mean, turn, Z, az in source_bins(s)]
        stations.append({"id": s["id"], "lat": s["lat"], "lon": s["lon"], "bins": bins})
    rng = random.Random(1)
    moments = [datetime(rng.choice(years), 1, 1, tzinfo=UTC) + timedelta(minutes=rng.randrange(525600)) for _ in range(5)]
    settings = {"aboveBottomM": hab, "neighbours": NEIGHBOURS, "reachKm": REACH_KM, "softenKm": SOFTEN_KM,
                "prior": PRIOR, "exactKm": EXACT_KM, "minAmp": MIN_AMP, "extendKm": EXTEND_KM,
                "walkStepM": WALK_STEP_M, "lineStepM": LINE_STEP_M}

    # The cells: the area's box cut by a quadtree on the elements' centroids, split while a cell
    # owns more than CHUNK_NODES nodes. A cell owns the elements whose centroid falls in it, and
    # carries as well every element reaching into its box, which a point inside it can fall in,
    # and every element on the mesh's edge within HALO_KM of its box, where a point inside it off
    # the mesh takes the edge's constants (EXTEND_KM, and the walk in). The nearest point of the
    # mesh to a point off it lies on the mesh's edge, so a point anywhere in the cell is placed and
    # blended on the cell alone exactly as on the whole mesh.
    cent = [(sum(lat[i] for i in t) / 3, sum(lon[i] for i in t) / 3) for t in tris]
    tbox = [(min(lat[i] for i in t), min(lon[i] for i in t), max(lat[i] for i in t), max(lon[i] for i in t))
            for t in tris]
    eps = 1e-6
    root = (min([S] + [c[0] for c in cent]) - eps, min([W] + [c[1] for c in cent]) - eps,
            max([N] + [c[0] for c in cent]) + eps, max([E] + [c[1] for c in cent]) + eps)
    edges = {}
    for t in tris:
        for x, y in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
            k = (x, y) if x < y else (y, x)
            edges[k] = edges.get(k, 0) + 1
    on_edge = [any(edges[(x, y) if x < y else (y, x)] == 1 for x, y in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])))
               for t in tris]

    def halo_of(box):
        s, w, n, e = box
        dl = HALO_KM / 111.2
        dw = HALO_KM / (111.2 * math.cos(math.radians(max(abs(s), abs(n)))))
        return [k for k, (a, b, c, d) in enumerate(tbox)
                if (a <= n and c >= s and b <= e and d >= w)
                or (on_edge[k] and a <= n + dl and c >= s - dl and b <= e + dw and d >= w - dw)]

    def split(box, ids):
        s, w, n, e = box
        if ids and len({i for k in ids for i in tris[k]}) > CHUNK_NODES and n - s > CHUNK_MIN_DEG:
            ms, mw = (s + n) / 2, (w + e) / 2
            out = []
            for b in ((s, w, ms, mw), (s, mw, ms, e), (ms, w, n, mw), (ms, mw, n, e)):
                out += split(b, [k for k in ids if b[0] <= cent[k][0] < b[2] and b[1] <= cent[k][1] < b[3]])
            return out
        return [(box, ids)]

    leaves = []
    for box, ids in split(root, list(range(len(tris)))):
        near_tris = halo_of(box)
        if near_tris:   # a cell owning nothing still answers the water within reach of its neighbours' mesh
            leaves.append((box, set(ids), sorted(set(near_tris) | set(ids))))
    log(f"  {len(leaves)} cells, at most {CHUNK_NODES} nodes owned by each")
    leaf_of = lambda la, lo: next((k for k, (b, _, _) in enumerate(leaves)
                                   if b[0] <= la < b[2] and b[1] <= lo < b[3]), None)

    def bottom_uv(Zb, az, t):
        sp = speed(Zb, t)
        return sp * math.sin(az * DEG), sp * math.cos(az * DEG)

    m2 = {n: abs(node_uv[n]["M2"][0]) + abs(node_uv[n]["M2"][1]) for n in nodes}

    def node_check(n):
        # the browser's port of the blend at a node, blended here from the same int16 constants
        # the browser reads, with the trails' seabed
        fl = floor_km({i: d for d, i in near[n]}, lat[n], lon[n], sources)
        H = depth[n]
        frac = max(min(hab, H) / H, 0.01) if H > 0 else 1.0
        Zn, mean, az, _ = blend_at(deq(index[n]), neighbours(fl, sources), prof, frac, fl, sources)
        b = make_bin(Zn, mean, az)
        return [(t, *bottom_uv(b, az, t)) for t in moments]

    def inner(t):
        # a point inside the element, one corner's weight clear of the others: the start node of
        # the paths through the water is the corner with the largest weight, which a near tie
        # leaves to rounding
        while True:
            w = sorted((rng.random(), rng.random(), rng.random()), reverse=True)
            if w[0] - w[1] > 0.1:
                break
        w = [x / sum(w) for x in w]
        rng.shuffle(w)
        return sum(wi * lat[i] for wi, i in zip(w, t)), sum(wi * lon[i] for wi, i in zip(w, t))

    def point_check(kind, la, lo):
        # a point placed and extracted as `extract` does at any coordinate, or None where the
        # tool gives nothing to prove there
        la, lo = round(la, 5), round(lo, 5)
        if not any(bs <= la <= bn and bw <= lo <= be for bs, bw, bn, be in boxes):
            return None
        e, _ = seabed.elevation(la, lo)
        if e is None or -e <= hab:
            return None
        try:
            nn, w, ext = mesh.place_site(la, lo)
        except Refused:
            return None
        if any(x not in index for x in nn) or (kind == "shore" and not ext):
            return None
        H = round(-e, 1)
        # interpolated from the same int16 constants the browser reads, as the node checks are,
        # so the check proves the port and leaves the file's rounding out of it
        dq = [deq(index[x]) for x in nn]
        uv = {k: (sum(wi * d[k][0] for wi, d in zip(w, dq)), sum(wi * d[k][1] for wi, d in zip(w, dq)))
              for k in keys}
        cur = extract_point(uv, max(zip(w, nn))[1], mesh, reg, H, ABOVE_BOTTOM, la, lo, say=lambda m: None)
        mine = {"cons": cur["bottom"]["cons"], "mean_major": cur["bottom"]["mean_major"]}
        # what `at` prints: the signed speed along the flood direction, which it gives to 0.1°
        return {"lat": la, "lon": lo, "seabed": H, "flood": cur["flood_dir"],
                "checks": [{"t": int(t.timestamp() * 1000), "s": round(speed(mine, t), 6)} for t in moments]}

    # every cell's checks: its strongest node and one more, points inside its own elements, and
    # points just off the mesh's shoreline, where the constants come from the mesh edge
    checks = [{"nodes": [], "points": []} for _ in leaves]
    for k, (box, owned, _) in enumerate(leaves):
        own_nodes = sorted({i for j in owned for i in tris[j]})
        if own_nodes:
            for n in sorted({max(own_nodes, key=lambda n: m2[n]), rng.choice(own_nodes)}):
                checks[k]["nodes"] += [{"node": n, "t": int(t.timestamp() * 1000), "u": round(u, 6), "v": round(v, 6)}
                                       for t, u, v in node_check(n)]
        own_list = sorted(owned)
        for j in own_list[::max(1, len(own_list) // (4 * CELL_POINT_CHECKS))]:
            if len(checks[k]["points"]) >= CELL_POINT_CHECKS:
                break
            p = point_check("inner", *inner(tris[j]))
            if p and leaf_of(p["lat"], p["lon"]) == k:
                checks[k]["points"].append(p)
    shore_nodes = sorted(n for n in nodes if n in shore)
    n_shore = 0
    for _ in range(MAP_SHORE_CHECKS * 100 if shore_nodes else 0):
        if n_shore >= MAP_SHORE_CHECKS:
            break
        n = rng.choice(shore_nodes)
        r, brg = rng.uniform(50, 1000 * EXTEND_KM), rng.uniform(0, 360) * DEG
        p = point_check("shore", lat[n] + r * math.cos(brg) / 111200,
                        lon[n] + r * math.sin(brg) / (111200 * math.cos(math.radians(lat[n]))))
        k = p and leaf_of(p["lat"], p["lon"])
        if p and k is not None:
            checks[k]["points"].append(p)
            n_shore += 1
    n_points = sum(len(c["points"]) for c in checks)
    log(f"  {n_points} sample points carried as checks, {n_shore} of them off the mesh's shoreline")
    if not n_points:
        sys.exit("No sample point in the boxes could be placed and extracted: the overlay would carry no point check.")

    common = {
        "name": name, "label": label, "bbox": [S, W, N, E], "boxes": boxes,
        "source": f"{reg['db']} ADCIRC tidal database corrected by NOAA and CHS current stations, "
                  f"{hab:g} m above the seabed",
        "maxSpeedMs": _blend_cfg("max_speed_ms", 0.25),
        "database": {"names": keys},
        "stations": stations,
        "profile": {str(b): [[f, z.real, z.imag] for f, z in prof[b]] for b in (1, 2)},
        "astronomy": astronomy,
        "settings": settings,
        "landMask": land_mask(S, W, N, E),
    }
    out_dir = os.path.join(WORKSPACE, "map", "currents", name)
    part = out_dir + ".part"
    shutil.rmtree(part, ignore_errors=True)
    os.makedirs(part)

    def write_js(path, key, doc, note):
        with open(path, "w") as fh:
            fh.write("// Generated by tools/map_export.py; regenerate rather than edit.\n")
            fh.write(f"// {note}\n")
            fh.write("window.MAP_CURRENTS = window.MAP_CURRENTS || {};\n")
            fh.write(f"window.MAP_CURRENTS[{json.dumps(key)}] = ")
            fh.write(json.dumps(doc, separators=(",", ":")))
            fh.write(";\n")

    write_js(os.path.join(part, "common.js"), name, common,
             f"{label}: the stations, astronomy and coastline every cell of the overlay shares.")
    rel = lambda p: os.path.relpath(p, WORKSPACE).replace(os.sep, "/").replace(".part/", "/", 1)
    cells = []
    for k, (box, owned, cell_tris) in enumerate(leaves):
        cn = sorted({i for j in cell_tris for i in tris[j]})
        ci = {n: m for m, n in enumerate(cn)}
        wide = len(cn) > 65535   # the triangles' node index: 16 bits, or 32 for a large cell
        xy, tri, dep = array.array("f"), array.array("I" if wide else "H"), array.array("f")
        own, sh, sc, qq = array.array("B"), array.array("B"), array.array("f"), array.array("h")
        cnt, src, km = array.array("B"), array.array("H"), array.array("f")
        nk4 = 4 * len(keys)
        for n in cn:
            j = index[n]
            xy.extend((lon[n], lat[n]))
            dep.append(depth[n])
            sh.append(1 if n in shore else 0)
            sc.append(scale[j])
            qq.extend(q[j * nk4:(j + 1) * nk4])
            lst = sorted((i, d) for d, i in near[n])
            if len(lst) > 255:
                sys.exit("a node with more than 255 stations within reach: the count is a byte.")
            cnt.append(len(lst))
            for i, d in lst:
                src.append(i)
                km.append(d)
        for j in cell_tris:
            tri.extend(ci[i] for i in tris[j])
            own.append(1 if j in owned else 0)
        cid = f"{k:03d}"
        doc = {
            "name": f"{name}/{cid}", "bbox": list(box),
            "nodeCount": len(cn), "triangleCount": len(cell_tris), "triangleIndex": "u32" if wide else "u16",
            "nodes": b64(xy), "triangles": b64(tri), "own": b64(own), "depth": b64(dep), "shoreNodes": b64(sh),
            "database": {"scale": b64(sc), "uv": b64(qq)},
            "near": {"count": b64(cnt), "station": b64(src), "km": b64(km)},
            "checks": {"nodes": [{**c, "node": ci[c["node"]]} for c in checks[k]["nodes"]], "points": checks[k]["points"]},
        }
        path = os.path.join(part, f"{cid}.js")
        write_js(path, f"{name}/{cid}", doc,
                 f"{label}, cell {cid}: {len(cn)} {reg['db']} mesh nodes, {len(cell_tris)} elements "
                 f"({len(owned)} its own). The browser runs the tool's blend.")
        cells.append({"id": cid, "box": [round(x, 7) for x in box], "file": rel(path),
                      "bytes": os.path.getsize(path)})
    shutil.rmtree(out_dir, ignore_errors=True)
    os.replace(part, out_dir)
    old = os.path.join(WORKSPACE, "map", "currents", f"{name}.js")   # the single-file form an earlier export wrote
    if os.path.exists(old):
        os.remove(old)
    size = sum(c["bytes"] for c in cells) + os.path.getsize(os.path.join(out_dir, "common.js"))
    log(f"  wrote {rel(out_dir)}/: common.js and {len(cells)} cells, {size / 1e6:.1f} MB in all, "
        f"the largest cell {max(c['bytes'] for c in cells) / 1e6:.1f} MB")
    write_index({
        "name": name, "label": label, "kind": "seafloor", "boxes": boxes, "version": int(time.time()),
        "dir": rel(out_dir), "common": rel(os.path.join(out_dir, "common.js")), "minZoom": CURRENT_MIN_ZOOM,
        "cells": [{k: c[k] for k in ("id", "box", "file")} for c in cells]})

# --- the tides --------------------------------------------------------------------------------

TIDES_FILE = os.path.join(WORKSPACE, "map", "tides", "stations.js")
TIDE_MARGIN_DEG = 0.3   # stations this far past the boxes join the blend at their edges
TIDE_CHECKS = 4         # sample moments per station the browser reproduces


def _moments(rng, years):
    return [datetime(rng.choice(years), 1, 1, tzinfo=timezone.utc) + timedelta(minutes=rng.randrange(525600))
            for _ in range(TIDE_CHECKS)]


def _highest(fn, year):
    """The highest tide of the year, hourly: ground below it is the tide's to cover."""
    start = datetime(year, 1, 1, tzinfo=timezone.utc)
    return max(fn(start + timedelta(hours=k)) for k in range(366 * 24))


def export_tides(areas):
    """Write map/tides/stations.js: every tide station of every source near the boxes that carries
    harmonic constants, grouped by the datum its heights are above, which is the family the depth
    layer adds to the seabed on that datum. NOAA's stations carry their constituents prepared for
    each year the map may ask about, as lib/tide_harmonics.py holds them; CHS's stations their
    constants fitted by Foreman's method, with the satellites of Foreman's table their node factors
    come from, as lib/foreman.py moves them day by day. Each station carries its heights at sample
    moments, which the browser reproduces before it uses them, and its highest tide of the year. A
    CHS station not yet fitted is fitted here, as the tide tool fits it."""
    y0 = date.today().year - MAP_YEARS_BACK
    years = list(range(y0, date.today().year + MAP_YEARS_AHEAD + 1))
    m = TIDE_MARGIN_DEG
    boxes = [[s - m, w - m, n + m, e + m] for ar in areas for s, w, n, e in ar["boxes"]]
    rng = random.Random(1)
    noaa, chs, left_out, used = [], [], [], set()
    rows = tide.in_boxes(boxes)
    for k, (src, sid, e) in enumerate(rows, 1):
        name = tide.label(src, sid)
        if e["kind"] == "subordinate":
            continue   # defined by its highs and lows alone; the reference station it follows is in the blend
        st = tide.Station(src, src.load(sid, quiet=True))
        try:
            h, why = st.constants()
        except chs_tides.SeriesGap as gap:
            h, why = None, f"no fit can be made: {gap.code}"
        if h is None:
            left_out.append(f"{name} {e['name']}: {why}")
            continue
        if src.datum == MLLW and h.get("method") != "foreman":
            prep = {y: prepare(h["cons"], y) for y in years}
            noaa.append({
                "id": name, "name": e["name"], "lat": e["lat"], "lon": e["lon"],
                "msl": round(h["z0"], 4), "high": round(_highest(lambda t: height(h, t), date.today().year), 3),
                "coef": [list(c) for c, _, _ in prep[years[0]]],
                "years": {str(y): {"arg": [round(a, 5) for _, a, _ in p], "amp": [round(f, 6) for _, _, f in p]}
                          for y, p in prep.items()},
                "checks": [{"t": int(t.timestamp() * 1000), "h": round(height(h, t), 5)} for t in _moments(rng, years)],
            })
        elif src.datum == CHS and h.get("method") == "foreman":
            names = list(h["cons"])
            used.update(names)
            chs.append({
                "id": name, "name": e["name"], "lat": e["lat"], "lon": e["lon"], "fitLat": h["lat"],
                "z0": round(h["z0"], 6), "names": names,
                "ab": [[round(a, 7), round(b, 7)] for a, b in h["cons"].values()],
                "high": round(_highest(lambda t: foreman.height(h, t), date.today().year), 3),
                "checks": [{"t": int(t.timestamp() * 1000), "h": round(foreman.height(h, t), 5)}
                           for t in _moments(rng, years)],
            })
        else:
            left_out.append(f"{name} {e['name']}: heights above {src.datum} in a form the map does not sum")
        if k % 25 == 0:
            log(f"  tides: {k}/{len(rows)} stations read")
    # Foreman's table, for the constituents the CHS stations carry and the ones their compounds are made of
    const = foreman.table()
    table = {}
    for n in sorted(used):
        c = const[n]
        if c["shallow"]:
            table[n] = {"shallow": [[k, mm] for k, mm in c["shallow"]]}
            for _, mm in c["shallow"]:
                used_main = const[mm]
                table.setdefault(mm, {"dood": used_main["dood"], "semi": used_main["semi"],
                                      "sats": [list(x) for x in used_main["sats"]]})
        else:
            table[n] = {"dood": c["dood"], "semi": c["semi"], "sats": [list(x) for x in c["sats"]]}
    data = {"built": date.today().isoformat(), "first_year": years[0], "last_year": years[-1],
            "families": {
                MLLW: {"model": "noaa", "epoch": astro.EPOCH.isoformat(), "rate": list(RATE), "stations": noaa},
                CHS: {"model": "foreman", "epoch": foreman.EPOCH.isoformat(), "table": table, "stations": chs},
            },
            "left_out": left_out}
    os.makedirs(os.path.dirname(TIDES_FILE), exist_ok=True)
    with open(TIDES_FILE + ".part", "w") as f:
        f.write("// Written by tools/map_export.py; regenerate rather than edit.\n")
        f.write(f"window.MAP_TIDES = {json.dumps(data, separators=(',', ':'))};\n")
    os.replace(TIDES_FILE + ".part", TIDES_FILE)
    log(f"wrote {len(noaa)} NOAA and {len(chs)} CHS stations, {years[0]} to {years[-1]}, to "
        f"map/tides/stations.js ({os.path.getsize(TIDES_FILE) / 1e3:.0f} KB)")
    for line in left_out:
        log(f"  left out {line}")


# --- commands -------------------------------------------------------------------------------

def cmd_currents(areas, only=None):
    names = {ar["name"] + "-seafloor" for ar in areas}
    for ar in areas:
        if only and ar["name"] not in only:
            continue
        log(f"== currents: {ar['label']}")
        export_currents(ar)
    # an overlay whose area left the coverage leaves the map with it
    for e in map_overlays():
        if e.get("kind") == "seafloor" and e["name"] not in names:
            path = os.path.join(WORKSPACE, e.get("dir") or e["file"])
            if os.path.isdir(path):
                shutil.rmtree(path)
            elif os.path.exists(path):
                os.remove(path)
            drop_index(e["name"])
            log(f"  removed {e.get('dir') or e['file']}: its area is no longer in the coverage")


def cmd_depth(areas, only=None):
    log("== depth")
    map_depth.export(areas, only=only)


def cmd_tides(areas, only=None):
    # every area's stations, whatever --area names: the file is one, and quick to write once the
    # CHS stations are fitted
    log("== tides")
    export_tides(areas)


LAYERS = {"tides": cmd_tides, "currents": cmd_currents, "depth": cmd_depth}

# The layers live outside git: each is zipped into a GitHub release, and the Pages workflow
# (.github/workflows/pages.yml) unzips the newest one beside map.html before it deploys.
RELEASE_PREFIX = "map-"
RELEASE_LAYERS = {"depth": "map/depth/depth.js", "currents": "map/currents/index.js", "tides": "map/tides/stations.js"}
RELEASE_KEEP = 2


def _gh(*args, capture=False):
    import subprocess
    if not shutil.which("gh"):
        sys.exit("publish needs the GitHub CLI: brew install gh, then gh auth login.")
    r = subprocess.run(["gh", *args], cwd=WORKSPACE, text=True, capture_output=capture)
    if r.returncode:
        sys.exit(f"gh {' '.join(args[:2])} failed" + (f": {r.stderr.strip()}" if capture else "") + ".")
    return r.stdout if capture else None


def cmd_publish(keep):
    """Zip every layer into a new release, tagged map-<UTC time>, and keep only the newest `keep`
    map releases. The release goes online with the next push to main, which runs the Pages workflow."""
    import tempfile
    import zipfile
    for name, desc in RELEASE_LAYERS.items():
        if not os.path.exists(os.path.join(WORKSPACE, desc)):
            sys.exit(f"{desc} is missing: run map_export.py {name} before publishing.")
    # every area of the coverage in every per-area layer, so an export of one area never publishes
    # a map missing the others
    missing = []
    with open(os.path.join(WORKSPACE, RELEASE_LAYERS["depth"])) as f:
        text = f.read()
    meta = json.loads(text[text.index("=") + 1:].strip().rstrip(";"))
    overlays = {e["name"] for e in map_overlays()}
    for ar in coverage():
        if not any(map_depth._owns(ar, int(z), *map(int, t.split("/")))
                   for z, lst in meta.get("present", {}).items() for t in filter(None, lst.split(","))):
            missing.append(f"map_export.py depth --area {ar['name']}")
        if ar["name"] + "-seafloor" not in overlays:
            missing.append(f"map_export.py currents --area {ar['name']}")
    if missing:
        sys.exit("Some areas of map/coverage.json are missing from the layers on disk; run "
                 + "; ".join(missing) + " before publishing.")
    tag = RELEASE_PREFIX + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    with tempfile.TemporaryDirectory() as tmp:
        zips = []
        for name in RELEASE_LAYERS:
            root = os.path.join(WORKSPACE, "map", name)
            path = os.path.join(tmp, f"{RELEASE_PREFIX}{name}.zip")
            n = 0
            with zipfile.ZipFile(path, "w") as z:
                for d, _, files in os.walk(root):
                    for fn in sorted(files):
                        if fn.startswith("."):
                            continue
                        full = os.path.join(d, fn)
                        # PNG tiles are compressed already; the scripts shrink well
                        z.write(full, os.path.relpath(full, WORKSPACE),
                                zipfile.ZIP_STORED if fn.endswith(".png") else zipfile.ZIP_DEFLATED)
                        n += 1
            log(f"  {os.path.basename(path)}: {n} files, {os.path.getsize(path) / 1e6:.0f} MB")
            zips.append(path)
        log(f"== publish: release {tag}")
        _gh("release", "create", tag, *zips, "--title", f"Map layers {tag[len(RELEASE_PREFIX):]}",
            "--notes", "Map layers written by tools/map_export.py, unzipped beside map.html by the Pages workflow.",
            "--latest")
    rels = json.loads(_gh("release", "list", "--limit", "200", "--json", "tagName,createdAt", capture=True))
    old = sorted((r for r in rels if r["tagName"].startswith(RELEASE_PREFIX)),
                 key=lambda r: r["createdAt"], reverse=True)[keep:]
    for r in old:
        _gh("release", "delete", r["tagName"], "--yes", "--cleanup-tag")
        log(f"  removed release {r['tagName']}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("layer", nargs="*", choices=sorted(LAYERS) + ["publish"],
                   help="the layers to write, omitted for every one; or publish, alone")
    p.add_argument("--keep", type=int, default=RELEASE_KEEP, help="publish: map releases to keep, newest first")
    p.add_argument("--area", action="append", metavar="NAME",
                   help="an area of map/coverage.json to write alone, repeatable; the depth and current layers keep "
                        "every other area's as they are on disk, and tides always writes every area")
    a = p.parse_args()
    if "publish" in a.layer:
        if len(a.layer) > 1 or a.area:
            sys.exit("publish runs alone, after the layers are written, and publishes every area.")
        if a.keep < 1:
            sys.exit("--keep is at least 1.")
        cmd_publish(a.keep)
        return
    areas = coverage()
    if a.area:
        unknown = sorted(set(a.area) - {ar["name"] for ar in areas})
        if unknown:
            sys.exit(f"No area {', '.join(unknown)} in map/coverage.json; the areas are "
                     f"{', '.join(ar['name'] for ar in areas)}.")
    for name in a.layer or list(LAYERS):
        LAYERS[name](areas, a.area)


if __name__ == "__main__":
    main()

"""The current tool's method, shared by current.py and map_export.py: an ADCIRC tidal
database corrected by the current stations around a point, read from a built region, and the
extract at a point and a height above the seabed. A point read through this library is the
same current whichever tool asks for it."""
import cmath
import heapq
import json
import math
import os
import statistics
import sys
from datetime import datetime, timezone

from lib.adcirc import CONSTITUENTS, DATABASES, WALK_STEP_M, calibrate, in_domain, interp_polar, locate, mean_longitudes, need_db, nodal, read_mesh, walk_in
from lib import shapes
from lib.current_stations import noaa_arg, noaa_name
from lib.tidal_astronomy import CONS
from lib.tidal_astronomy import nodal as noaa_nodal

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # tools/


DB = os.path.join(HERE, "db", "current")


UTC = timezone.utc


DEG = math.pi / 180


# The ADCIRC constants are written in NOAA's convention at this instant; both astronomies carry
# the node factors forward from it, so the result holds for any year.
TREF = datetime(2027, 1, 1, tzinfo=UTC)


# How the stations around a point are weighed, from `verify`'s comparison of the alternatives:
# the six nearest through the water within REACH_KM, each weighted 1 / (d² + SOFTEN_KM²), and
# PRIOR, the weight that pulls the result back toward the database's own value. Within reach of
# EXACT_KM the nearest station's own current takes over, by EXACT_KM² / (EXACT_KM² + d²): all of
# it at the station, half at EXACT_KM.
NEIGHBOURS = 6


REACH_KM = 16.0


SOFTEN_KM = 1.0


PRIOR = 0.3


EXACT_KM = 0.5


MIN_AMP = 1.0       # cm/s: a station constituent this small in the database keeps its band's correction


ABOVE_BOTTOM = 2.0  # m: the lowest measured height above the seabed


MARGIN = 0.15       # degrees of mesh kept around a region for the paths through the water


EXTEND_KM = 1.0     # how far toward shore a point outside the wet mesh takes the mesh edge's constants


ORIENT_KM = 300.0    # how far through the water the station naming the flood is looked for


LINE_STEP_M = 10.0  # spacing of the water test along the line from a point to the mesh edge


FORMAT = 2          # the region file's layout; a region built by another reads as out of date


def log(m):
    print(m, file=sys.stderr, flush=True)


def band(name):
    """1 diurnal, 2 semidiurnal, 3 the higher species, 0 long period: the group whose station
    correction a constituent shares when it has none of its own."""
    s = CONS[name][0][0]
    return 0 if s == 0 else 1 if s == 1 else 2 if s == 2 else 3


def to_noaa(cons, db):
    """An ADCIRC extract's constituents as {NOAA name: (Zu, Zv)}, complex east and north
    amplitudes in cm/s with Z = A e^(-ig) in NOAA's convention. A constituent the two
    astronomies define differently (M1) is left out."""
    C = calibrate(cons, db)
    nd = noaa_nodal(TREF.year)
    s, h, p, N, pp, T = mean_longitudes(TREF)
    out = {}
    for c in cons:
        key = noaa_name(c["name"])
        (nT, ns, nh, np_, npp), nk = CONSTITUENTS[c["name"]]
        if key not in CONS or tuple(CONS[key][0]) != (nT, ns, nh, np_, npp):
            continue
        f_adc, u = nodal(nk, N, c["f_ref"])
        base = (nT * T + ns * s + nh * h + np_ * p + npp * pp) + u + math.degrees(C[c["name"]])
        f_noaa = 1.0
        for b, pw in CONS[key][2]:
            f_noaa *= nd[b][0] ** abs(pw)
        sh = base - noaa_arg(key, TREF)
        r = 100 * f_adc / f_noaa
        out[key] = (r * c["u_amp"] * cmath.exp(-1j * (c["u_phase"] - sh) * DEG),
                    r * c["v_amp"] * cmath.exp(-1j * (c["v_phase"] - sh) * DEG))
    return out


def along(uv, az):
    a = az * DEG
    return {k: zu * math.sin(a) + zv * math.cos(a) for k, (zu, zv) in uv.items()}


def principal_axis(uv):
    """Bearing (deg) of the database's main current axis at a point, from its tidal ellipses."""
    sxx = sum(abs(zu) ** 2 for zu, _ in uv.values())
    syy = sum(abs(zv) ** 2 for _, zv in uv.values())
    sxy = sum((zu * zv.conjugate()).real for zu, zv in uv.values())
    th = 0.5 * math.atan2(2 * sxy, sxx - syy)
    return math.degrees(math.atan2(math.cos(th), math.sin(th))) % 360


def wrap90(x):
    return (x + 90) % 180 - 90


def adcirc_axis(uv, toward):
    """The database's main axis at a point, pointed within 90° of `toward`."""
    az = principal_axis(uv)
    return (az + 180) % 360 if math.cos((toward - az) * DEG) < 0 else az


def make_bin(Z, mean, az):
    cons = [[k, round(abs(z), 4), round((-math.degrees(cmath.phase(z))) % 360, 3), 0.0, 0.0]
            for k, z in sorted(Z.items()) if abs(z) >= 0.0005]
    return {"cons": cons, "mean_major": round(mean, 3), "azimuth": round(az, 1)}


xc = lambda v: complex(v[0], v[1])


def profile_table(rows, exclude=None):
    """{band: [(fraction of the depth above the seabed, complex speed ratio to the column mean)]}
    in tenths of the column, medians over the stations' bins."""
    out = {}
    for b, (rk, pk, om) in {2: ("m2r", "m2p", 28.984), 1: ("k1r", "k1p", 15.041)}.items():
        tab = []
        for i in range(10):
            lo = i / 10
            g = [r for r in rows if lo <= r["frac"] < lo + 0.1 and r["id"] != exclude]
            if len(g) >= 8:
                ratio = statistics.median(r[rk] for r in g)
                minutes = statistics.median(r[pk] for r in g)
                tab.append((lo + 0.05, ratio * cmath.exp(-1j * minutes / 60 * om * DEG)))
        out[b] = tab
    out[3] = out[0] = out[2]
    return out


def vfac(tab, frac):
    """The profile's complex ratio at a fraction of the depth above the seabed. Below the lowest
    tenth it follows the 1/7 power of the height. A region with no measured profile, one whose
    stations have too few bins or none, takes the 1/7 power law over the whole column: the
    speed at a height relative to the column mean, with no change in timing."""
    if not tab:
        return complex((8 / 7) * max(frac, 0.01) ** (1 / 7), 0)
    if frac <= tab[0][0]:
        return tab[0][1] * (max(frac, 0.01) / tab[0][0]) ** (1 / 7)
    for (f0, z0), (f1, z1) in zip(tab, tab[1:]):
        if frac <= f1:
            w = (frac - f0) / (f1 - f0)
            return z0 * (1 - w) + z1 * w
    return tab[-1][1]


def vprof(prof, name, f):
    """The regional profile's complex ratio to the column mean for one constituent at a fraction of
    the depth above the seabed: the diurnal table for the diurnals and the semidiurnal one for the
    rest, its phase scaled by the species so every constituent leads by the same time; amplitude
    alone for the long period ones."""
    sp = CONS[name][0][0]
    if sp == 1:
        return vfac(prof[1], f)
    z = vfac(prof[2], f)
    return complex(abs(z), 0) if sp == 0 else abs(z) * cmath.exp(1j * cmath.phase(z) * sp / 2)


def wrapc(z, ref):
    """A complex log with its phase unwrapped to within half a turn of ref's."""
    d = z - ref
    return ref + complex(d.real, (d.imag + math.pi) % (2 * math.pi) - math.pi)


BAND_KEY = {1: "K1", 2: "M2", 3: "M4"}


def source_bins(s):
    """A source's bins as corrections to the database, lowest first: (fraction of the depth above
    the seabed, {constituent: log ratio to the database along its axis}, {band: log ratio}, steady
    current cm/s, the bin's axis less the database's, the bin's own constants, the bin's axis)."""
    if "_pb" not in s:
        uv = s["uv"]
        A = along(uv, adcirc_axis(uv, s["flood"]))
        pa = principal_axis(uv)
        out = []
        for frac, mean, az, cons in s["bins"]:
            Z = {k: xc(v) for k, v in cons.items()}
            Lc = {c: cmath.log(Z[c] / A[c]) for c in Z if c in A and abs(A[c]) >= MIN_AMP and abs(Z[c]) > 1e-6}
            Lb = {b: cmath.log(Z[k] / A[k]) for b, k in BAND_KEY.items()
                  if k in Z and k in A and abs(A[k]) > 0 and abs(Z[k]) > 1e-6}
            out.append((frac, Lc, Lb, mean, wrap90(az - pa), Z, az))
        s["_pb"] = sorted(out, key=lambda x: x[0])
    return s["_pb"]


def at_frac(s, f, prof):
    """A source at a fraction of the depth: (log ratios, band log ratios, steady current, axis turn,
    own constants, own axis). Between two of its bins, interpolated; beyond them, its nearest bin
    moved by the regional profile."""
    bins = source_bins(s)
    if len(bins) == 1 or f <= bins[0][0] or f >= bins[-1][0]:
        fb, Lc, Lb, m, t, Z, az = bins[0] if (len(bins) == 1 or f <= bins[0][0]) else bins[-1]
        adj = {c: vprof(prof, c, f) / vprof(prof, c, fb) for c in set(Lc) | set(Z) | set(BAND_KEY.values())}
        return ({c: L + cmath.log(adj[c]) for c, L in Lc.items()},
                {b: L + cmath.log(adj[BAND_KEY[b]]) for b, L in Lb.items()}, m, t,
                {c: z * adj[c] for c, z in Z.items()}, az)
    for lo, hi in zip(bins, bins[1:]):
        if lo[0] <= f <= hi[0]:
            w = (f - lo[0]) / (hi[0] - lo[0]) if hi[0] > lo[0] else 0.0
            Lc = {c: lo[1][c] * (1 - w) + wrapc(hi[1][c], lo[1][c]) * w for c in lo[1] if c in hi[1]}
            Lb = {b: lo[2][b] * (1 - w) + wrapc(hi[2][b], lo[2][b]) * w for b in lo[2] if b in hi[2]}
            Z = {c: lo[5][c] * (1 - w) + hi[5][c] * w for c in lo[5] if c in hi[5]}
            return (Lc, Lb, lo[3] * (1 - w) + hi[3] * w, lo[4] + wrap90(hi[4] - lo[4]) * w, Z,
                    (lo[6] + ((hi[6] - lo[6] + 180) % 360 - 180) * w) % 360)


def blend_at(uv, cand, prof, frac, dists, sources, exclude=None):
    """The current at a point and a fraction of the depth above the seabed: ({constituent: complex
    amplitude along the flood, cm/s}, steady current cm/s, flood direction, (source, km) naming the
    flood). The database's constants along its axis, scaled and shifted by the neighbours' own
    ratios at that height, and, within reach of EXACT_KM, drawn toward the nearest station's own
    current, which they equal at the station itself."""
    az0 = principal_axis(uv)
    if not cand:
        az, near = orient(az0, dists, sources, exclude)
        A = along(uv, adcirc_axis(uv, az))
        return by_timing({c: z * vprof(prof, c, frac) for c, z in A.items()}, 0.0, az, near, prof, frac)
    ws = [1 / (d * d + SOFTEN_KM ** 2) for d, _ in cand]
    tot = PRIOR + sum(ws)
    per = [at_frac(s, frac, prof) for _, s in cand]
    lam = EXACT_KM ** 2 / (EXACT_KM ** 2 + cand[0][0] ** 2)
    # the axis: the database's, turned toward the neighbours' own, drawn toward none away from them
    e = sum(w * math.sin(2 * p[3] * DEG) for w, p in zip(ws, per))
    n = PRIOR + sum(w * math.cos(2 * p[3] * DEG) for w, p in zip(ws, per))
    turn = math.degrees(math.atan2(e, n)) / 2
    turn += lam * wrap90(per[0][3] - turn)
    az, near = orient((az0 + turn) % 360, dists, sources, exclude)
    A = along(uv, adcirc_axis(uv, az))
    # each band's ratio, drawn toward the regional profile alone; each constituent's, toward its band's
    Lband = {}
    for b, k in BAND_KEY.items():
        base = cmath.log(vprof(prof, k, frac))
        acc = PRIOR * base
        for w, p in zip(ws, per):
            acc += w * wrapc(p[0].get(k, p[1].get(b, base)), base)
        Lband[b] = acc / tot
    Z = {}
    for c, z in A.items():
        b = band(c)
        lb = Lband[b] if b else cmath.log(vprof(prof, c, frac))
        acc = PRIOR * lb
        for w, p in zip(ws, per):
            L = p[0].get(c)
            if L is None:
                L = (p[1][b] + cmath.log(vprof(prof, c, frac) / vprof(prof, BAND_KEY[b], frac))) if b and b in p[1] else lb
            acc += w * wrapc(L, lb)
        Z[c] = z * cmath.exp(acc / tot)
    mean = sum(w * p[2] * math.cos((p[5] - az) * DEG) for w, p in zip(ws, per)) / tot
    # near a station, its own current
    sign = 1 if math.cos((per[0][5] - az) * DEG) >= 0 else -1
    own = per[0][4]
    Z = {c: lam * sign * own.get(c, 0) + (1 - lam) * Z.get(c, 0) for c in set(Z) | set(own)}
    mean = lam * sign * per[0][2] + (1 - lam) * mean
    return by_timing(Z, mean, az, near, prof, frac)


def by_timing(Z, mean, az, near, prof, frac):
    """The point's flood named by the tide's timing: the end of its axis the water runs toward
    while the station naming the flood floods. The axis is turned end for end, with the constants'
    sign, wherever the point's current runs against that station's, as in a back eddy or a side
    channel; the water itself is unchanged."""
    if not near:
        return Z, mean, az, near
    own = at_frac(near[0], frac, prof)[4]
    cov = sum((Z[c] * own[c].conjugate()).real for c in Z if c in own)
    if cov < 0:
        return {c: -z for c, z in Z.items()}, -mean, (az + 180) % 360, near
    return Z, mean, az, near


def point_bin(uv, cand, prof, frac, dists, sources, exclude=None):
    """blend_at as a bin the prediction reads: (bin, flood direction, (source, km) naming it)."""
    Z, mean, az, near = blend_at(uv, cand, prof, frac, dists, sources, exclude)
    return make_bin(Z, mean, az), az, near


def neighbours(dists, sources, exclude=None):
    """The NEIGHBOURS nearest sources within REACH_KM, from {source index: km}."""
    c = sorted((d, i) for i, d in dists.items() if d < REACH_KM and sources[i]["id"] != exclude)
    return [(d, sources[i]) for d, i in c[:NEIGHBOURS]]


def floor_km(dists, lat, lon, sources):
    """Distances through the water, each at least the straight line: the path runs from mesh node
    to mesh node, so a point and a station sharing a node would otherwise sit 0 km apart."""
    out = {}
    for i, d in dists.items():
        s = sources[i]
        out[i] = max(d, math.hypot((s["lon"] - lon) * math.cos(math.radians(lat)), s["lat"] - lat) * 111.2)
    return out


def orient(az, dists, sources, exclude=None):
    """The main axis turned to point with the flood of the nearest source through the water,
    and that source; the axis as it is when no source is in reach."""
    near = [(d, i) for i, d in dists.items() if sources[i]["id"] != exclude]
    if not near:
        return az, None
    d, i = min(near)
    s = sources[i]
    if math.cos((s["flood"] - az) * DEG) < 0:
        az = (az + 180) % 360
    return az, (s, d)


class Refused(Exception):
    """A point the tool does not cover: on land, or water outside its reach toward shore."""


class Mesh:
    def __init__(self, db, bbox):
        need_db(db)
        log(f"{db}: reading mesh ({os.path.basename(DATABASES[db]['mesh'])})...")
        self.db = db
        self.lon, self.lat, self.dep, self.elems = read_mesh(db, depth=True)
        S, W, N, E = bbox
        inb = lambda i: S - MARGIN <= self.lat[i] <= N + MARGIN and W - MARGIN <= self.lon[i] <= E + MARGIN
        adj = {}
        for a, b, c in self.elems:
            if inb(a) and inb(b) and inb(c):
                for x, y in ((a, b), (b, c), (c, a)):
                    adj.setdefault(x, set()).add(y)
                    adj.setdefault(y, set()).add(x)
        self.adj = {u: [(v, self.km(u, v)) for v in vs] for u, vs in adj.items()}

    def km(self, u, v):
        lat = (self.lat[u] + self.lat[v]) / 2
        return math.hypot((self.lon[v] - self.lon[u]) * math.cos(math.radians(lat)), self.lat[v] - self.lat[u]) * 111.2

    def place(self, lat, lon, walk=True):
        """(nodes, weights, lat, lon) of the element a point falls in, walked into the wet mesh
        when it lies outside and `walk`; None outside without it. A station's own position."""
        nodes, w, inside, _ = locate(self.lon, self.lat, self.elems, lon, lat)
        if not inside:
            if not walk:
                return None
            lat, lon = walk_in(self.lon, self.lat, self.elems, lon, lat, WALK_STEP_M)
            nodes, w, inside, _ = locate(self.lon, self.lat, self.elems, lon, lat)
        return nodes, w, lat, lon

    def place_site(self, lat, lon):
        """(nodes, weights, km) for a site: the element it falls in, or, for water the mesh does not
        reach, the element at the nearest point of the mesh's edge, when that point lies within
        EXTEND_KM and the straight line to it crosses no land. km is how far the constants were
        taken from. Stops on land, past the cap, or with land between."""
        land = lambda la, lo, rings: any(shapes.contains(r, lo, la) for r in rings)
        near = [r for _, r in shapes.polygons("land", lat, lon, 0)]
        if land(lat, lon, near):
            raise Refused(f"{lat}, {lon} is on land by OpenStreetMap's coastline: give a coordinate in the water.")
        nodes, w, inside, _ = locate(self.lon, self.lat, self.elems, lon, lat)
        if inside:
            return nodes, w, 0.0
        elat, elon = walk_in(self.lon, self.lat, self.elems, lon, lat, WALK_STEP_M)
        km = math.hypot((elon - lon) * math.cos(math.radians(lat)), elat - lat) * 111.2
        if km > EXTEND_KM:
            raise Refused(f"{lat}, {lon} is water {km:.2f} km from the {self.db} mesh, past the {EXTEND_KM:g} km the "
                     f"tool reaches toward shore: the point is outside the tool's coverage. Stop and report it.")
        rings = [r for _, r in shapes.polygons("land", lat, lon, km + 0.1)]
        n = max(1, int(km * 1000 / LINE_STEP_M))
        for i in range(1, n + 1):
            f = i / n
            if land(lat + (elat - lat) * f, lon + (elon - lon) * f, rings):
                raise Refused(f"{lat}, {lon} is water outside the {self.db} mesh, and land lies between it and the "
                         f"mesh's nearest edge {km:.2f} km away: the point is outside the tool's coverage. Stop and report it.")
        nodes, w, inside, _ = locate(self.lon, self.lat, self.elems, elon, elat)
        return nodes, w, km

    def paths(self, start, cutoff):
        """{node: km} through the water from `start`, out to `cutoff` km."""
        dist = {start: 0.0}
        pq = [(0.0, start)]
        while pq:
            d0, u = heapq.heappop(pq)
            if d0 > dist.get(u, 1e9):
                continue
            for v, L in self.adj.get(u, ()):
                d1 = d0 + L
                if d1 <= cutoff and d1 < dist.get(v, 1e9):
                    dist[v] = d1
                    heapq.heappush(pq, (d1, v))
        return dist


def adcirc_cons(header, vals, nodes, w):
    """The extract at a point: each constituent interpolated across its element."""
    out = []
    for k, (name, freq, fnf, eqarg) in enumerate(header):
        n0, n1, n2 = (vals[nodes[i]][k] for i in range(3))
        ua, up = interp_polar(n0[0], n0[1], n1[0], n1[1], n2[0], n2[1], w)
        va, vp = interp_polar(n0[2], n0[3], n1[2], n1[3], n2[2], n2[3], w)
        out.append({"name": name, "f_ref": fnf, "v0u_deg": eqarg, "u_amp": ua, "u_phase": up,
                    "v_amp": va, "v_phase": vp})
    return out


def database_for(bbox):
    S, W, N, E = bbox
    dbs = [n for n in DATABASES if in_domain(n, S, W) and in_domain(n, N, E)]
    if not dbs:
        sys.exit("The box does not sit inside one ADCIRC database.")
    return dbs[0]


def region_path(name):
    return os.path.join(DB, f"{name}.json")


def built_regions():
    """{name: bbox} of every region built on this machine."""
    out = {}
    for f in sorted(os.listdir(DB)) if os.path.isdir(DB) else []:
        if f.endswith(".json") and "_" not in f:
            with open(os.path.join(DB, f)) as fh:
                out[f[:-5]] = json.load(fh)["bbox"]
    return out


def load_region(name=None, lat=None, lon=None):
    """A built region, by name or as the first whose box holds a point; sources get their
    corrections as complex numbers."""
    if not os.path.isdir(DB):
        sys.exit("No region is built yet: run `build` first.")
    names = [name] if name else sorted(f[:-5] for f in os.listdir(DB) if f.endswith(".json") and "_" not in f)
    for n in names:
        p = region_path(n)
        if not os.path.exists(p):
            sys.exit(f"No region named {n}: run `build --name {n} --bbox ...` first.")
        with open(p) as f:
            reg = json.load(f)
        S, W, N, E = reg["bbox"]
        if lat is None or (S <= lat <= N and W <= lon <= E):
            if reg.get("format") != FORMAT:
                sys.exit(f"The {n} region was built by an older version of the tool: run `build` again.")
            for s in reg["sources"]:
                s["uv"] = {k: (xc(v[0]), xc(v[1])) for k, v in s["uv"].items()}
            return reg
    sys.exit(f"No built region holds {lat}, {lon}; the built regions are {', '.join(names)}.")


def extract_point(uv, start, mesh, reg, H, above_bottom, qlat, qlon, say=log):
    """The current object for a point placed in the mesh: its constants at the height
    asked for and at the fastest height above, with the stations behind them; `say` takes the
    progress lines."""
    sources = reg["sources"]
    d = mesh.paths(start, ORIENT_KM)
    dists = floor_km({i: d[s["node"]] for i, s in enumerate(sources) if s["node"] in d}, qlat, qlon, sources)
    cand = neighbours(dists, sources)
    prof = profile_table(reg["profile_rows"])
    hab = min(above_bottom, H)
    frac = max(hab / H, 0.01)
    bottom, az, near = point_bin(uv, cand, prof, frac, dists, sources)
    # the fastest height above, for the descent and ascent: the strongest semidiurnal current
    ups = [frac] + [f / 20 for f in range(1, 20) if f / 20 > frac]
    upf = max(ups, key=lambda f: abs(blend_at(uv, cand, prof, f, dists, sources)[0].get("M2", 0)))
    upper = point_bin(uv, cand, prof, upf, dists, sources)[0]
    # the stations behind the correction, and the one whose flood names the flood here, which lies
    # beyond the correction's reach where no station is closer
    stations = [{"id": s["id"], "name": s["name"], "km": round(dd, 2),
                 "sets_flood_ebb_direction": bool(near and s is near[0])} for dd, s in cand]
    if near and not any(st["sets_flood_ebb_direction"] for st in stations):
        stations.append({"id": near[0]["id"], "name": near[0]["name"], "km": round(near[1], 2),
                         "sets_flood_ebb_direction": True})
    say(f"  flood {az:.0f}°, from {near[0]['id']} {near[1]:.1f} km away" if near
        else f"  axis {az:.0f}° and {(az + 180) % 360:.0f}°: no station within {ORIENT_KM:.0f} km names the flood")
    for dd, s in cand:
        say(f"  {s['id']:<9} {dd:5.1f} km  {s['name']}")
    if not cand:
        say(f"  no station within {REACH_KM:.0f} km through the water: the database's own current, scaled to the height")
    return {
        "extract_point": {"lat": qlat, "lon": qlon, "seabed_m": H,
                          "extracted": datetime.now(UTC).isoformat(timespec="seconds")},
        "flood_dir": round(az, 1), "ebb_dir": round((az + 180) % 360, 1),
        # the prediction reads the constituents and the steady current; the axis is flood_dir's
        "bottom": {"above_bottom_m": round(hab, 2), "cons": bottom["cons"], "mean_major": bottom["mean_major"]},
        "upper": {"above_bottom_m": round(upf * H, 1), "cons": upper["cons"], "mean_major": upper["mean_major"]},
        "stations": stations}

#!/usr/bin/env python3
"""Tidal currents at any point of a region and any height above the seabed: an ADCIRC tidal
database corrected by the current stations around the point, NOAA's and CHS's.

  blend_model.py build --name N --bbox S W N E          gather a region's stations, once
  blend_model.py extract --near LAT LON --seabed D       print a point's constants, once
  blend_model.py predict --file F --date D --tz Z        slacks and peaks
  blend_model.py window --file F --date D --tz Z         diveable windows under a speed threshold
  blend_model.py at --file F --time "D HH:MM" --tz Z     current at a moment
  blend_model.py verify --name N                         accuracy against hidden stations
  blend_model.py export-map --bbox S W N E [...] --name N --label L   the map viewer's seafloor overlay
"""
import argparse
import cmath
import heapq
import json
import math
import os
import statistics
import sys
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from lib.adcirc import (CONSTITUENTS, DATABASES, WALK_STEP_M, calibrate, in_domain,  # noqa: E402
                        interp_polar, locate, mean_longitudes, need_db, nodal, read_mesh,
                        read_vel_header, read_vel_nodes, walk_in, write_overlay)
from lib.current_harmonics import events, series  # noqa: E402
from lib import shapes  # noqa: E402
from lib.dem_tiles import CachedTiles  # noqa: E402
from lib.tcd import Harmonics, velocity  # noqa: E402
from lib.tidal_astronomy import ALIAS, CONS, longitudes  # noqa: E402
from lib.tidal_astronomy import nodal as noaa_nodal  # noqa: E402

WORKSPACE = os.path.dirname(HERE)
DB = os.path.join(HERE, "db", "blend_model")
NOAA_DB = os.path.join(HERE, "db", "noaa_current")
CHS_DB = os.path.join(HERE, "db", "chs_current")
TCD = os.path.join(HERE, "db", "harmonics-dwf-20100529-free.tcd")
UTC = timezone.utc
DEG = math.pi / 180
KN = 0.514444

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
CHS_NAMES = ["M2", "S2", "N2", "K2", "K1", "O1", "P1", "Q1", "2N2", "NU2", "MU2", "L2", "T2", "J1", "M1",
             "OO1", "2Q1", "RHO", "M4", "MS4", "MN4", "S4", "M6", "2MK3", "MK3", "M3", "M8", "LAM2",
             "SSA", "SA"]
BANDS_KM = [(0, 2), (2, 6), (6, REACH_KM), (REACH_KM, None)]
MARGIN = 0.15       # degrees of mesh kept around a region for the paths through the water
EXTEND_KM = 1.0     # how far toward shore a point outside the wet mesh takes the mesh edge's constants
ORIENT_KM = 300.0    # how far through the water the station naming the flood is looked for
LINE_STEP_M = 10.0  # spacing of the water test along the line from a point to the mesh edge


def log(m):
    print(m, file=sys.stderr, flush=True)


def _cfg(key, default):
    """Read this tool's section of tool-config.json; missing file or key -> default."""
    try:
        with open(os.path.join(WORKSPACE, "tool-config.json")) as f:
            return json.load(f).get("blend_model", {}).get(key, default)
    except (OSError, ValueError):
        return default


def resolve_tz(name):
    try:
        return ZoneInfo(name)
    except Exception:
        sys.exit(f"{name} is not an IANA time zone name. Pass the site's `tz` from its JSON, e.g. America/Los_Angeles.")


# --- constituents in NOAA's convention ----------------------------------------------------

def noaa_name(name):
    k = name.replace("(", "").replace(")", "").upper()
    return ALIAS.get(k, k)


def band(name):
    """1 diurnal, 2 semidiurnal, 3 the higher species, 0 long period: the group whose station
    correction a constituent shares when it has none of its own."""
    s = CONS[name][0][0]
    return 0 if s == 0 else 1 if s == 1 else 2 if s == 2 else 3


def _noaa_arg(key, t):
    """NOAA's argument (deg) for a constituent at UTC t, node phase included."""
    coef, const, parts = CONS[key]
    nd = noaa_nodal(t.year)
    u = sum(nd[b][1] * p for b, p in parts)
    s, h, p, _, p1 = longitudes(t)
    T = 15.0 * (t.hour + t.minute / 60 + t.second / 3600) + 180.0
    cT, cs, ch, cp, cp1 = coef
    return cT * T + cs * s + ch * h + cp * p + cp1 * p1 + const + u


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
        sh = base - _noaa_arg(key, TREF)
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


def bin_z(b):
    return {noaa_name(c[0]): c[1] * cmath.exp(-1j * c[2] * DEG) for c in b["cons"]}


def make_bin(Z, mean, az):
    cons = [[k, round(abs(z), 4), round((-math.degrees(cmath.phase(z))) % 360, 3), 0.0, 0.0]
            for k, z in Z.items() if abs(z) >= 0.0005]
    return {"cons": cons, "mean_major": round(mean, 3), "azimuth": round(az, 1)}


cx = lambda z: [round(z.real, 6), round(z.imag, 6)]
xc = lambda v: complex(v[0], v[1])


# --- the correction from the stations around a point --------------------------------------

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
    tenth it follows the 1/7 power of the height."""
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


# --- the mesh, and paths through the water --------------------------------------------------

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
            sys.exit(f"{lat}, {lon} is on land by OpenStreetMap's coastline: give a coordinate in the water.")
        nodes, w, inside, _ = locate(self.lon, self.lat, self.elems, lon, lat)
        if inside:
            return nodes, w, 0.0
        elat, elon = walk_in(self.lon, self.lat, self.elems, lon, lat, WALK_STEP_M)
        km = math.hypot((elon - lon) * math.cos(math.radians(lat)), elat - lat) * 111.2
        if km > EXTEND_KM:
            sys.exit(f"{lat}, {lon} is water {km:.2f} km from the {self.db} mesh, past the {EXTEND_KM:g} km the "
                     f"tool reaches toward shore: the point is outside the tool's coverage. Stop and report it.")
        rings = [r for _, r in shapes.polygons("land", lat, lon, km + 0.1)]
        n = max(1, int(km * 1000 / LINE_STEP_M))
        for i in range(1, n + 1):
            f = i / n
            if land(lat + (elat - lat) * f, lon + (elon - lon) * f, rings):
                sys.exit(f"{lat}, {lon} is water outside the {self.db} mesh, and land lies between it and the "
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


# --- the region's sources -----------------------------------------------------------------

def region_path(name):
    return os.path.join(DB, f"{name}.json")


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
            if "bins" not in (reg["sources"] or [{}])[0]:
                sys.exit(f"The {n} region was built by an older version of the tool: run `build` again.")
            for s in reg["sources"]:
                s["uv"] = {k: (xc(v[0]), xc(v[1])) for k, v in s["uv"].items()}
            return reg
    sys.exit(f"No built region holds {lat}, {lon}; the built regions are {', '.join(names)}.")


def chs_signed(code, year):
    """A CHS station's speed series for one UTC year, every 6 minutes, signed flood positive by
    the flood or ebb event between the slacks around it."""
    p = os.path.join(CHS_DB, f"{code}_{year}.json")
    if not os.path.exists(p):
        sys.exit(f"CHS station {code} has no cached {year}. Cache it with "
                 f"`python3 tools/chs_current.py fetch {code} --year {year}`, then build again.")
    with open(p) as f:
        d = json.load(f)
    t0 = datetime(year, 1, 1, tzinfo=UTC)
    ev = [(t0 + timedelta(minutes=m), k) for m, k, _ in d["events"]]
    ms = d["mins"] if "mins" in d else range(d["start"], d["start"] + d["step"] * len(d["kn"]), d["step"])
    out, j = [], 0
    for m, kn in zip(ms, d["kn"]):
        if m % 60:
            continue
        t = t0 + timedelta(minutes=m)
        while j < len(ev) and ev[j][0] <= t:
            j += 1
        lo = j - 1
        while lo >= 0 and ev[lo][1] != "S":
            lo -= 1
        hi = j
        while hi < len(ev) and ev[hi][1] != "S":
            hi += 1
        kinds = {k for _, k in ev[max(lo, 0):min(hi + 1, len(ev))] if k in ("F", "E")}
        if len(kinds) == 1:
            out.append((t, (1 if "F" in kinds else -1) * kn * KN))
    return out


def harmonic_fit(ser, names):
    """Least squares on hourly samples: the mean (m/s) and {name: (A cm/s, g deg)} in NOAA's
    convention."""
    names = [n for n in names if n in CONS]
    n = 1 + 2 * len(names)
    M = [[0.0] * n for _ in range(n)]
    v = [0.0] * n
    nds = {}
    for t, y in ser:
        nd = nds.setdefault(t.year, noaa_nodal(t.year))
        r = [1.0]
        for k in names:
            f = 1.0
            for b, p in CONS[k][2]:
                f *= nd[b][0] ** abs(p)
            V = _noaa_arg(k, t) * DEG
            r += [f * math.cos(V), f * math.sin(V)]
        for i in range(n):
            ri = r[i]
            v[i] += ri * y
            Mi = M[i]
            for j in range(i, n):
                Mi[j] += ri * r[j]
    for i in range(n):
        for j in range(i):
            M[i][j] = M[j][i]
    for i in range(n):
        p = max(range(i, n), key=lambda k: abs(M[k][i]))
        M[i], M[p], v[i], v[p] = M[p], M[i], v[p], v[i]
        for k in range(n):
            if k != i and M[k][i]:
                f = M[k][i] / M[i][i]
                Mk, Mi = M[k], M[i]
                for j in range(i, n):
                    Mk[j] -= f * Mi[j]
                v[k] -= f * v[i]
    x = [v[i] / M[i][i] for i in range(n)]
    return x[0], {k: (100 * math.hypot(x[1 + 2 * i], x[2 + 2 * i]),
                      math.degrees(math.atan2(x[2 + 2 * i], x[1 + 2 * i])) % 360) for i, k in enumerate(names)}


def cmd_build(a):
    S, W, N, E = a.bbox
    inbox = lambda la, lo: S <= la <= N and W <= lo <= E
    db = database_for(a.bbox)
    with open(os.path.join(NOAA_DB, "stations.json")) as f:
        lst = json.load(f)["stations"]
    missing = [sid for sid, s in lst.items() if inbox(s["lat"], s["lon"])
               and not os.path.exists(os.path.join(NOAA_DB, f"{sid}.json"))]
    if missing:
        sys.exit(f"{len(missing)} NOAA stations in the box are not cached ({', '.join(missing[:8])}...). "
                 f"Cache them with `python3 tools/noaa_current.py fetch --near <lat> <lon> --km <r>`, then build again.")
    sources, others = [], []
    for sid, s in sorted(lst.items()):
        if not inbox(s["lat"], s["lon"]):
            continue
        with open(os.path.join(NOAA_DB, f"{sid}.json")) as f:
            doc = json.load(f)
        bins = [b for b in doc["bins"].values() if b.get("cons")]
        if bins:
            sources.append({"id": sid, "kind": "noaa", "name": doc["name"], "lat": doc["lat"], "lon": doc["lon"],
                            "_bins": bins, "flood": bins[0]["azimuth"]})
        else:
            kinds = {b.get("type") for b in doc["bins"].values()}
            others.append({"id": sid, "kind": "noaa subordinate" if "S" in kinds else "noaa weak",
                           "name": doc["name"], "lat": doc["lat"], "lon": doc["lon"]})
    for fn in sorted(os.listdir(CHS_DB)):
        if len(fn) == 10 and fn.endswith(".json"):
            with open(os.path.join(CHS_DB, fn)) as f:
                d = json.load(f)
            if inbox(float(d["lat"]), float(d["lon"])):
                sources.append({"id": "CHS" + d["code"], "kind": "chs", "name": d["name"], "lat": float(d["lat"]),
                                "lon": float(d["lon"]), "code": d["code"], "flood": float(d["flood"])})
    legacy = []
    if os.path.exists(TCD):
        h = Harmonics(TCD)
        recs = list(h.records())
        for r in recs:
            if r["type"] == 2 and "Current" in r["name"] and inbox(r["lat"], r["lon"]) and recs[r["ref"]]["type"] == 1:
                legacy.append({"id": r["name"], "kind": "legacy", "name": r["name"], "lat": r["lat"], "lon": r["lon"],
                               **{k: r[k] for k in ("ref", "flood_dir", "ebb_dir", "flood_time", "ebb_time",
                                                    "flood_mult", "ebb_mult", "sbf_time", "sbe_time")}})
    log(f"{sum(s['kind'] == 'noaa' for s in sources)} NOAA harmonic stations, "
        f"{sum(s['kind'] == 'chs' for s in sources)} CHS stations, {len(others)} other NOAA stations, "
        f"{len(legacy)} legacy subordinate stations")

    mesh = Mesh(db, a.bbox)
    tiles = CachedTiles()
    pts = sources + legacy
    for s in pts:
        nodes, w, la, lo = mesh.place(s["lat"], s["lon"])
        s["_nodes"], s["_w"] = nodes, w
        s["node"] = max(zip(w, nodes))[1]
        s["seabed_mesh"] = round(sum(wi * mesh.dep[n] for wi, n in zip(w, nodes)), 2)
        e = tiles.elevation(s["lat"], s["lon"])
        s["seabed_ncei"] = round(-e, 2) if e is not None and e < 0 else None
    header = read_vel_header(db)
    log(f"Streaming the velocity file for {len(pts)} points (a few minutes)...")
    vals = read_vel_nodes(db, sorted({n for s in pts for n in s["_nodes"]}))
    for s in pts:
        s["uv"] = to_noaa(adcirc_cons(header, vals, s["_nodes"], s["_w"]), db)

    rows = []
    for s in sources:
        H = s["seabed_ncei"] or s["seabed_mesh"]
        if s["kind"] == "noaa":
            bins = s["_bins"]
            # every bin with its height as a fraction of the depth above the seabed, its steady
            # current, its axis and its constants
            s["bins"] = [[round(min(max((H - b["depth"]) / H, 0.02), 0.98), 3) if H and b.get("depth") is not None else 0.5,
                          b.get("mean_major") or 0.0, b["azimuth"], {c: cx(z) for c, z in bin_z(b).items()}]
                         for b in bins]
            deep = sorted((b for b in bins if b.get("depth") is not None), key=lambda b: b["depth"])
            Hn = s["seabed_ncei"]
            if len(deep) >= 3 and Hn and deep[-1]["depth"] <= Hn + 3:
                cm = {c: sum(bin_z(b)[c] for b in deep) / len(deep) for c in ("M2", "K1")}
                for b in deep:
                    Z = bin_z(b)
                    rows.append({"id": s["id"], "frac": round((Hn - b["depth"]) / Hn, 4),
                                 "m2r": abs(Z["M2"]) / abs(cm["M2"]),
                                 "m2p": -math.degrees(cmath.phase(Z["M2"] / cm["M2"])) / 28.984 * 60,
                                 "k1r": abs(Z["K1"]) / abs(cm["K1"]),
                                 "k1p": -math.degrees(cmath.phase(Z["K1"] / cm["K1"])) / 15.041 * 60})
        else:
            log(f"  fitting constants to CHS {s['code']} {s['name']}, {a.fit_year}...")
            mean, cons = harmonic_fit(chs_signed(s["code"], a.fit_year), CHS_NAMES)
            full = {k: A * cmath.exp(-1j * g * DEG) for k, (A, g) in cons.items()}
            s["cons"] = [[k, round(A, 4), round(g, 3), 0.0, 0.0] for k, (A, g) in cons.items()]
            s["mean_major"] = round(mean * 100, 3)
            # one series, taken as the middle of the water column
            s["bins"] = [[0.5, round(mean * 100, 3), s["flood"], {c: cx(z) for c, z in full.items()}]]
    log(f"  vertical profile from {len({r['id'] for r in rows})} stations, {len(rows)} bins")

    log("Paths through the water between stations...")
    node_of = {}
    for i, s in enumerate(sources):
        node_of.setdefault(s["node"], []).append(i)
    for s in pts:
        d = mesh.paths(s["node"], 60.0)
        s["water_km"] = {str(i): round(d[n], 3) for n, ii in node_of.items() if n in d for i in ii if sources[i] is not s}
    for s in pts:
        s["uv"] = {k: [cx(zu), cx(zv)] for k, (zu, zv) in s["uv"].items()}
        for k in ("_nodes", "_w", "_bins"):
            s.pop(k, None)
    doc = {"name": a.name, "bbox": a.bbox, "db": db, "built": datetime.now(UTC).isoformat(timespec="seconds"), "fit_year": a.fit_year,
           "sources": sources, "others": others, "legacy": legacy, "profile_rows": rows,
           "settings": {"neighbours": NEIGHBOURS, "reach_km": REACH_KM, "soften_km": SOFTEN_KM, "prior": PRIOR,
                        "exact_km": EXACT_KM}}
    os.makedirs(DB, exist_ok=True)
    with open(region_path(a.name) + ".part", "w") as f:
        json.dump(doc, f, separators=(",", ":"))
    os.replace(region_path(a.name) + ".part", region_path(a.name))
    log(f"  wrote {os.path.relpath(region_path(a.name), WORKSPACE)}")


# --- a point --------------------------------------------------------------------------------

def read_site(path):
    """A site JSON's coordinate and seabed depth: (doc, lat, lon, seabed_m); stops when any is missing."""
    try:
        with open(path) as f:
            doc = json.load(f)
    except OSError as e:
        sys.exit(f"Could not read --site {path}: {e}")
    except json.JSONDecodeError as e:
        sys.exit(f"Could not parse JSON in {path}: {e}")
    missing = [k for k in ("lat", "lon", "seabed_m") if not isinstance(doc.get(k), (int, float))]
    if missing:
        sys.exit(f"{path} has no {', '.join(missing)}: the site JSON carries the dive area's coordinate and "
                 f"its seabed depth below the datum, written when the site is created.")
    return doc, doc["lat"], doc["lon"], doc["seabed_m"]


def cmd_extract(a):
    if a.site:
        site_doc, qlat, qlon, a.seabed = read_site(a.site)
    else:
        if not a.near or a.seabed is None:
            sys.exit("Give --site <slug.json>, or --near LAT LON with --seabed M.")
        site_doc, (qlat, qlon) = None, a.near
    reg = load_region(lat=qlat, lon=qlon)
    sources = reg["sources"]
    mesh = Mesh(reg["db"], reg["bbox"])
    if a.seabed <= 0:
        sys.exit("--seabed is the seabed depth below the datum, a positive number of metres.")
    nodes, w, ext = mesh.place_site(qlat, qlon)
    if ext:
        log(f"  water the mesh does not reach: the mesh edge's constants, {ext * 1000:.0f} m away across water")
    header = read_vel_header(reg["db"])
    log("Streaming the velocity file for the 3 nodes (a minute or several)...")
    vals = read_vel_nodes(reg["db"], nodes)
    uv = to_noaa(adcirc_cons(header, vals, nodes, w), reg["db"])
    start = max(zip(w, nodes))[1]
    d = mesh.paths(start, ORIENT_KM)
    dists = floor_km({i: d[s["node"]] for i, s in enumerate(sources) if s["node"] in d}, qlat, qlon, sources)
    cand = neighbours(dists, sources)
    prof = profile_table(reg["profile_rows"])
    H = a.seabed
    hab = min(a.above_bottom, H)
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
    doc = {
        "blend_model_current": {
            "extract_point": {"lat": qlat, "lon": qlon, "seabed_m": H,
                              "extracted": datetime.now(UTC).isoformat(timespec="seconds")},
            "flood_dir": round(az, 1), "ebb_dir": round((az + 180) % 360, 1),
            # the prediction reads the constituents and the steady current; the axis is flood_dir's
            "bottom": {"above_bottom_m": round(hab, 2), "cons": bottom["cons"], "mean_major": bottom["mean_major"]},
            "upper": {"above_bottom_m": round(upf * H, 1), "cons": upper["cons"], "mean_major": upper["mean_major"]},
            "stations": stations},
    }
    log(f"  flood {az:.0f}°, from {near[0]['id']} {near[1]:.1f} km away" if near else "  no station to set the flood direction")
    for dd, s in cand:
        log(f"  {s['id']:<9} {dd:5.1f} km  {s['name']}")
    if not cand:
        log(f"  no station within {REACH_KM:.0f} km through the water: the database's own current, scaled to the height")
    if site_doc is None:
        print(json.dumps(doc, indent=2))
        return
    site_doc["blend_model_current"] = doc["blend_model_current"]
    with open(a.site + ".part", "w") as f:
        f.write(json.dumps(site_doc, indent=2) + "\n")
    os.replace(a.site + ".part", a.site)
    log(f"  wrote blend_model_current into {a.site}")


def load_doc(a):
    if a.json is not None:
        try:
            doc, src = json.loads(a.json), "--json"
        except json.JSONDecodeError as e:
            sys.exit(f"Could not parse --json: {e}")
    else:
        try:
            with open(a.file) as fh:
                doc, src = json.load(fh), a.file
        except OSError as e:
            sys.exit(f"Could not read --file {a.file}: {e}")
        except json.JSONDecodeError as e:
            sys.exit(f"Could not parse JSON in {a.file}: {e}")
    if "extract_point" not in doc.get("blend_model_current", {}):
        sys.exit(f"No blend_model_current extract in {src}: run `extract` and attach its output.")
    if getattr(a, "raw", False):
        doc.pop("blend_model_observed_offset", None)
    return doc


PAD_MIN = 180  # minutes of model curve either side of a day, for the offset's time shift


def curve(doc, b, start, minutes):
    """[(utc datetime, speed)] every minute at the site: the model's curve, moved by the site's
    observed offset where one is established. Each slack moves by its own offset, slack before
    flood or slack before ebb, and the moments between two slacks move by an offset that runs
    evenly from one to the other."""
    off = doc.get("blend_model_observed_offset") or {}
    fl, eb = off.get("before_flood_min"), off.get("before_ebb_min")
    if fl is None and eb is None:
        return series(b, start, minutes)
    m0 = start - timedelta(minutes=PAD_MIN)
    model = series(b, m0, minutes + 2 * PAD_MIN)
    slacks = []
    for k, (t, kind, _) in enumerate(ev := events(model)):
        if kind == "slack":
            nxt = next((v for _, kd, v in ev[k + 1:] if kd != "slack"), None)
            o = (fl if nxt is not None and nxt > 0 else eb) or 0
            slacks.append((t + timedelta(minutes=o), o))
    out, k = [], 0
    for m in range(minutes + 1):
        t = start + timedelta(minutes=m)
        while k + 1 < len(slacks) and slacks[k + 1][0] <= t:
            k += 1
        if not slacks:
            o = 0
        elif t <= slacks[0][0] or k + 1 == len(slacks):
            o = slacks[k][1]
        else:
            (ta, oa), (tb, ob) = slacks[k], slacks[k + 1]
            o = oa + (ob - oa) * (t - ta).total_seconds() / (tb - ta).total_seconds()
        x = (t - m0).total_seconds() / 60 - o
        i = max(0, min(len(model) - 2, int(x)))
        fr = min(max(x - i, 0.0), 1.0)
        out.append((t, model[i][1] + (model[i + 1][1] - model[i][1]) * fr))
    return out


def day_span(day, tz, pad=0):
    start = datetime(day.year, day.month, day.day, tzinfo=tz).astimezone(UTC)
    end = (datetime(day.year, day.month, day.day, tzinfo=tz) + timedelta(days=1)).astimezone(UTC)
    return start - timedelta(minutes=pad), int((end - start).total_seconds() // 60) + 2 * pad


def print_header(doc, day, tz):
    c = doc["blend_model_current"]
    p = c["extract_point"]
    print(f"{p['lat']:.5f}, {p['lon']:.5f}  {day}  {c['bottom']['above_bottom_m']:g} m above a {p['seabed_m']:g} m seabed  "
          f"({getattr(tz, 'key', None) or tz.tzname(None)})")
    fs = next((s for s in c["stations"] if s.get("sets_flood_ebb_direction")), None)
    src = f", the flood direction of {fs['id']} {fs['km']:.1f} km away" if fs else ""
    print(f"  flood {c['flood_dir']:.0f}°   ebb {c['ebb_dir']:.0f}°{src}")
    corr = [s for s in c["stations"] if s["km"] < REACH_KM]
    if corr:
        print("  corrected by " + ", ".join(f"{s['id']} {s['km']:.1f} km" for s in corr))
    else:
        print(f"  no station within {REACH_KM:.0f} km through the water: the database's own current")
    if "lat" in doc and (abs(doc["lat"] - p["lat"]) > 1e-6 or abs(doc["lon"] - p["lon"]) > 1e-6):
        print(f"  the site's coordinate ({doc['lat']}, {doc['lon']}) is not where this extract was taken: extract the site again")
    sb = doc.get("seabed_m")
    if sb is not None and abs(sb - p["seabed_m"]) > 0.005:
        print(f"  the site's seabed is {sb:g} m, and this extract was made for {p['seabed_m']:g} m: extract the site again")
    built = _region_built(p["lat"], p["lon"])
    if built and _when(built) > _when(p["extracted"]):
        print(f"  the region was rebuilt on {built[:10]}, after this extract ({p['extracted'][:10]}): extract the site again")
    off = doc.get("blend_model_observed_offset")
    if off:
        print(f"  observed offset applied: slack before flood {_mins(off.get('before_flood_min'))}, "
              f"slack before ebb {_mins(off.get('before_ebb_min'))}")
    print()


def _region_built(lat, lon):
    """When the region holding a point was last built, or None where none is on this machine."""
    if not os.path.isdir(DB):
        return None
    for fn in sorted(os.listdir(DB)):
        if fn.endswith(".json") and "_" not in fn:
            try:
                with open(os.path.join(DB, fn)) as f:
                    reg = json.load(f)
            except (OSError, ValueError):
                continue
            S, W, N, E = reg["bbox"]
            if S <= lat <= N and W <= lon <= E:
                return reg.get("built")
    return None


def _when(stamp):
    t = datetime.fromisoformat(stamp)
    return t if t.tzinfo else t.replace(tzinfo=UTC)


def _mins(m):
    return "none" if m is None else f"{abs(m):g} min {'after' if m >= 0 else 'before'} the model"


def cmd_predict(a):
    doc = load_doc(a)
    tz = resolve_tz(a.tz)
    c = doc["blend_model_current"]
    print_header(doc, a.date, tz)
    start, minutes = day_span(a.date, tz, pad=5)
    up = {round(t.timestamp() / 60): v for t, kind, v in events(curve(doc, c["upper"], start, minutes)) if kind != "slack"}
    print(f"            bottom      fastest above ({c['upper']['above_bottom_m']:g} m off the bottom)")
    for t, kind, v in events(curve(doc, c["bottom"], start, minutes)):
        tl = (t + timedelta(seconds=30)).astimezone(tz)
        if tl.date() != a.date:
            continue
        if kind == "slack":
            print(f"  {tl:%H:%M}  SLACK")
        else:
            m = round(t.timestamp() / 60)
            k = min(up, key=lambda x: abs(x - m), default=None)
            above = f"   {up[k]:+.2f} m/s" if k is not None and abs(k - m) < 60 and (up[k] > 0) == (v > 0) else ""
            print(f"  {tl:%H:%M}  {kind:<9} {v:+.2f} m/s{above}")


def cmd_window(a):
    doc = load_doc(a)
    tz = resolve_tz(a.tz)
    c = doc["blend_model_current"]
    lim = a.max_speed
    print_header(doc, a.date, tz)
    print(f"  windows with |current| <= {lim:.2f} m/s at the bottom, each with its peak there and in the fastest water above\n")
    start, minutes = day_span(a.date, tz)
    bot = curve(doc, c["bottom"], start, minutes)[:-1]
    upv = [v for _, v in curve(doc, c["upper"], start, minutes)[:-1]]
    runs, cur = [], []
    for k, (t, v) in enumerate(bot):
        if abs(v) <= lim:
            cur.append((t, v, upv[k]))
        elif cur:
            runs.append(cur)
            cur = []
    if cur:
        runs.append(cur)
    if not runs:
        print(f"  none, current never drops below {lim:.2f} m/s at the bottom.")
        return
    for run in runs:
        mins = len(run)
        peak = max(abs(v) for _, v, _ in run)
        above = max(abs(u) for _, _, u in run)
        if mins >= minutes:
            print(f"  all day          peak {peak:.2f} m/s, above {above:.2f} m/s")
            continue
        t0, t1 = run[0][0].astimezone(tz), (run[-1][0] + timedelta(minutes=1)).astimezone(tz)
        flag = "  <-- tight" if mins < 40 else ""
        print(f"  {t0:%H:%M} - {t1:%H:%M}   {mins:>3} min   peak {peak:.2f} m/s, above {above:.2f} m/s{flag}")


def cmd_at(a):
    doc = load_doc(a)
    tz = resolve_tz(a.tz)
    c = doc["blend_model_current"]
    t = datetime.strptime(a.time, "%Y-%m-%d %H:%M").replace(tzinfo=tz)
    print_header(doc, t.date(), tz)
    tu = t.astimezone(UTC)
    for lbl, b in (("bottom", c["bottom"]), (f"{c['upper']['above_bottom_m']:g} m off the bottom", c["upper"])):
        v = curve(doc, b, tu, 0)[0][1]
        print(f"  {t:%H:%M}  {lbl:<22} {abs(v):.2f} m/s toward {c['flood_dir'] if v >= 0 else c['ebb_dir']:.0f}° "
              f"({'flood' if v >= 0 else 'ebb'})")


# --- verify -----------------------------------------------------------------------------------

def _pairs(er, ex, slack):
    A = [e for e in er if (e[1] == "slack") == slack and "min" not in e[1]]
    B = [e for e in ex if (e[1] == "slack") == slack and "min" not in e[1]]
    out = []
    for e in A:
        best = None
        for f in B:
            d = abs((f[0] - e[0]).total_seconds())
            if d < 3 * 3600 and (slack or (f[2] > 0) == (e[2] > 0)) and (best is None or d < best[0]):
                best = (d, f)
        if best:
            out.append((e, best[1]))
    return out


def score(er, ex, minpk=0.15):
    """Median slack time error (min), share of slacks within 15 min, median peak speed error."""
    sl = [abs((f[0] - e[0]).total_seconds()) / 60 for e, f in _pairs(er, ex, True)]
    pk = [abs(abs(f[2]) / abs(e[2]) - 1) for e, f in _pairs(er, ex, False) if abs(e[2]) > minpk]
    if not sl:
        return None
    nsl = sum(1 for e in er if e[1] == "slack")
    return {"slack": statistics.median(sl), "slack15": sum(v <= 15 for v in sl) / max(nsl, 1),
            "speed": statistics.median(pk) if pk else None}


def _q(v, p):
    v = sorted(x for x in v if x is not None)
    return v[min(len(v) - 1, int(p * len(v)))] if v else float("nan")


def _summary(rows):
    rows = [r for r in rows if r]
    if not rows:
        return None
    sp = [r["speed"] for r in rows if r["speed"] is not None]
    return {"n": len(rows), "slack_min": round(statistics.median(r["slack"] for r in rows), 1),
            "slack_p80": round(_q([r["slack"] for r in rows], 0.8), 1),
            "within15_pct": round(100 * statistics.mean(r["slack15"] for r in rows)),
            "speed_pct": round(100 * statistics.median(sp)) if sp else None}


def _table(title, res, methods):
    print(f"\n{title}")
    for lo, hi in [(0, None)] + BANDS_KM:
        sel = lambda r: r and lo <= r["km"] < (hi if hi is not None else 1e9)
        label = "all" if (lo, hi) == (0, None) else f"nearest station {lo:g} to {hi:g} km" if hi else f"nearest station beyond {lo:g} km"
        n = sum(1 for r in res[methods[0]] if sel(r))
        if not n:
            continue
        print(f"  {label}, {n} points")
        for m in methods:
            s = _summary([r for r in res[m] if sel(r)])
            if s:
                print(f"    {m:28s} slack {s['slack_min']:4.0f} min (80% within {s['slack_p80']:3.0f})   "
                      f"within 15 min {s['within15_pct']:3d}%   peak speed {s['speed_pct'] if s['speed_pct'] is not None else '':>3}%")


def cmd_verify(a):
    reg = load_region(a.name)
    sources = reg["sources"]
    days = a.days
    t0 = datetime(a.start.year, a.start.month, a.start.day, tzinfo=UTC)
    minutes = days * 1440
    ser = lambda b: series(b, t0, minutes, 6)
    methods = ["nearest station", "ADCIRC, 1/7 power", "Blend Model"]
    res = {m: [] for m in methods}
    law = lambda f: (8 / 7) * max(f, 0.01) ** (1 / 7)
    log(f"Hidden stations: each NOAA station's deepest bin, predicted without it, {days} days from {a.start}...")
    for i, s in enumerate(sources):
        if s["kind"] != "noaa":
            continue
        with open(os.path.join(NOAA_DB, f"{s['id']}.json")) as f:
            bins = [b for b in json.load(f)["bins"].values() if b.get("cons") and b.get("depth") is not None]
        if not bins:
            continue
        tb = max(bins, key=lambda b: b["depth"])
        H = s["seabed_ncei"] or s["seabed_mesh"]
        frac = max((H - tb["depth"]) / H, 0.02)
        dists = floor_km({int(j): d for j, d in s["water_km"].items()}, s["lat"], s["lon"], sources)
        cand = neighbours(dists, sources, exclude=s["id"])
        prof = profile_table(reg["profile_rows"], exclude=s["id"])
        bm_, az, _ = point_bin(s["uv"], cand, prof, frac, dists, sources, exclude=s["id"])
        preds = {"Blend Model": bm_}
        raw = {k: z * law(frac) for k, z in along(s["uv"], az).items()}
        preds["ADCIRC, 1/7 power"] = make_bin(raw, 0.0, az)
        near = sorted((d, j) for j, d in dists.items() if sources[j]["id"] != s["id"])
        if near:
            o = sources[near[0][1]]
            if o["kind"] == "chs":
                nb = {"cons": o["cons"], "mean_major": o["mean_major"], "azimuth": o["flood"]}
            else:
                with open(os.path.join(NOAA_DB, f"{o['id']}.json")) as f:
                    ob = [b for b in json.load(f)["bins"].values() if b.get("cons") and b.get("depth") is not None]
                Ho = o["seabed_ncei"] or o["seabed_mesh"]
                nb = min(ob, key=lambda b: abs((Ho - b["depth"]) / Ho - frac))
            if math.cos((nb["azimuth"] - az) * DEG) < 0:
                nb = {"cons": [[c[0], c[1], (c[2] + 180) % 360, 0, 0] for c in nb["cons"]],
                      "mean_major": -(nb.get("mean_major") or 0)}
            preds["nearest station"] = nb
        sign = 1 if math.cos((tb["azimuth"] - az) * DEG) >= 0 else -1
        truth = events(ser(tb if sign > 0 else {"cons": [[c[0], c[1], (c[2] + 180) % 360, 0, 0] for c in tb["cons"]],
                                                   "mean_major": -(tb.get("mean_major") or 0)}))
        km = cand[0][0] if cand else (near[0][0] if near else 99)
        for m in methods:
            sc = score(truth, events(ser(preds[m]))) if m in preds else None
            if sc:
                sc.update(id=s["id"], km=km)
            res[m].append(sc)
    _table(f"Hidden stations, {sum(1 for r in res[methods[-1]] if r)} NOAA stations' deepest bins, "
           f"by the distance through the water to the nearest other station", res, methods)

    leg_res = {m: [] for m in ("nearest station", "ADCIRC, surface", "Blend Model")}
    if reg["legacy"]:
        log(f"Legacy stations: {len(reg['legacy'])} subordinate stations of the 2010 tables...")
        h = Harmonics(TCD)
        recs = list(h.records())
        refev = {}
        prof = profile_table(reg["profile_rows"])
        for p in reg["legacy"]:
            if p["ref"] not in refev:
                r = recs[p["ref"]]
                refev[p["ref"]] = events([(t0 + timedelta(minutes=m), velocity(h, r, t0 + timedelta(minutes=m)))
                                          for m in range(0, minutes + 1, 6)])
            avg = ((p["flood_time"] or 0) + (p["ebb_time"] or 0)) / 2
            ev, truth = refev[p["ref"]], []
            for k, (t, kind, v) in enumerate(ev):
                if "min" in kind:
                    continue
                if kind == "slack":
                    nxt = next((x[1] for x in ev[k + 1:] if x[1] in ("flood", "ebb")), None)
                    adj = p["sbf_time"] if nxt == "flood" else p["sbe_time"]
                    truth.append((t + timedelta(minutes=adj if adj is not None else avg), "slack", 0.0))
                elif kind == "flood":
                    truth.append((t + timedelta(minutes=p["flood_time"] or 0), "flood", v * p["flood_mult"]))
                else:
                    truth.append((t + timedelta(minutes=p["ebb_time"] or 0), "ebb", v * p["ebb_mult"]))
            truth.sort()
            uv = {k: (xc(v[0]), xc(v[1])) for k, v in p["uv"].items()}
            dists = floor_km({int(j): d for j, d in p["water_km"].items()}, p["lat"], p["lon"], sources)
            az = p["flood_dir"]   # the legacy table's own axis
            cand = neighbours(dists, sources)
            bm_, baz, _ = point_bin(uv, cand, prof, 0.9, dists, sources)
            if math.cos((baz - az) * DEG) < 0:
                bm_ = {"cons": [[c[0], c[1], (c[2] + 180) % 360, 0, 0] for c in bm_["cons"]],
                       "mean_major": -bm_["mean_major"], "azimuth": az}
            preds = {"Blend Model": bm_,
                     "ADCIRC, surface": make_bin({k: z * 8 / 7 for k, z in along(uv, az).items()}, 0.0, az)}
            near = sorted((d, j) for j, d in dists.items())
            if near:
                o = sources[near[0][1]]
                if o["kind"] == "chs":
                    nb = {"cons": o["cons"], "mean_major": o["mean_major"], "azimuth": o["flood"]}
                else:
                    with open(os.path.join(NOAA_DB, f"{o['id']}.json")) as f:
                        ob = [b for b in json.load(f)["bins"].values() if b.get("cons")]
                    nb = min(ob, key=lambda b: b.get("depth") or 0)
                if math.cos((nb["azimuth"] - az) * DEG) < 0:
                    nb = {"cons": [[c[0], c[1], (c[2] + 180) % 360, 0, 0] for c in nb["cons"]],
                          "mean_major": -(nb.get("mean_major") or 0)}
                preds["nearest station"] = nb
            km = cand[0][0] if cand else (near[0][0] if near else 99)
            for m in leg_res:
                sc = score(truth, events(ser(preds[m]))) if m in preds else None
                if sc:
                    sc.update(id=p["id"], km=km)
                leg_res[m].append(sc)
        _table(f"Legacy stations, {sum(1 for r in leg_res['Blend Model'] if r)} subordinate stations of "
               "the 2010 tables (their reference moved by their own corrections), near the surface", leg_res, list(leg_res))

    # at the stations themselves: each NOAA station's deepest, middle and top bin, predicted at its own
    # position with the station in place; the per-bin corrections make these the station's own
    log("At the stations: each NOAA station's deepest, middle and top bins, with the station in place...")
    at = {"slack": [], "speed": [], "direction": []}
    prof = profile_table(reg["profile_rows"])
    for i, s in enumerate(sources):
        if s["kind"] != "noaa" or not s["seabed_ncei"]:
            continue
        with open(os.path.join(NOAA_DB, f"{s['id']}.json")) as f:
            bins = sorted((b for b in json.load(f)["bins"].values() if b.get("cons") and b.get("depth") is not None),
                          key=lambda b: b["depth"])
        if not bins:
            continue
        dists = floor_km({int(j): d for j, d in s["water_km"].items()}, s["lat"], s["lon"], sources) | {i: 0.0}
        cand = neighbours(dists, sources)
        H = s["seabed_ncei"]
        for tb in {id(b): b for b in (bins[-1], bins[len(bins) // 2], bins[0])}.values():
            frac = min(max((H - tb["depth"]) / H, 0.02), 0.98)
            pb, az, _ = point_bin(s["uv"], cand, prof, frac, dists, sources)
            sc = score(events(ser(tb)), events(ser(pb)))
            if sc:
                at["slack"].append(sc["slack"])
                if sc["speed"] is not None:
                    at["speed"].append(sc["speed"])
            at["direction"].append(abs(wrap90(az - tb["azimuth"])))
    at_sum = {"n": len(at["direction"]), "slack_min": round(statistics.median(at["slack"]), 1),
              "slack_p90": round(_q(at["slack"], 0.9), 1), "speed_pct": round(100 * statistics.median(at["speed"]), 1),
              "speed_p90": round(100 * _q(at["speed"], 0.9), 1), "direction_deg": round(statistics.median(at["direction"]), 1),
              "direction_p90": round(_q(at["direction"], 0.9), 1)}
    print(f"\nAt the stations, {at_sum['n']} bins of NOAA stations, each predicted at its own position and height")
    print(f"    slack {at_sum['slack_min']:g} min (90% within {at_sum['slack_p90']:g})   peak speed {at_sum['speed_pct']:g}% "
          f"(90% within {at_sum['speed_p90']:g})   direction {at_sum['direction_deg']:g}° (90% within {at_sum['direction_p90']:g})")

    by = []
    for lo, hi in BANDS_KM:
        s = _summary([r for r in res["Blend Model"] if r and lo <= r["km"] < (hi if hi is not None else math.inf)])
        if s:
            by.append({"from_km": lo, "to_km": hi} | s)
    out = {"verified": date.today().isoformat(), "start": a.start.isoformat(), "days": days,
           "by_distance": by,
           "hidden": {m: _summary(res[m]) for m in methods},
           "legacy": {m: _summary(leg_res[m]) for m in leg_res}, "at_stations": at_sum}
    with open(os.path.join(DB, f"{reg['name']}_verify.json"), "w") as f:
        json.dump(out, f, indent=1)
    print(f"\n  wrote tools/db/blend_model/{reg['name']}_verify.json, the figures the tool's documentation quotes")


# --- map --------------------------------------------------------------------------------------

def cmd_export_map(a):
    """The seafloor current at every mesh node with a cached NCEI depth: the database's
    constants at each node corrected by the stations around it and scaled to the height above
    the seabed, written as an overlay the map viewer draws like the database's own."""
    boxes = a.bbox
    S, W = min(b[0] for b in boxes), min(b[1] for b in boxes)
    N, E = max(b[2] for b in boxes), max(b[3] for b in boxes)
    reg = load_region(a.region) if a.region else load_region(lat=(S + N) / 2, lon=(W + E) / 2)
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
    tiles = CachedTiles()
    depth = {}
    for n in sorted({i for t in tris for i in t}):
        e = tiles.elevation(lat[n], lon[n])
        if e is not None:
            depth[n] = -e
    tris = [t for t in tris if all(i in depth for i in t)]
    nodes = sorted({i for t in tris for i in t})
    if not nodes:
        sys.exit("No mesh node in the boxes has a cached NCEI depth.")
    log(f"  {len(nodes)} nodes with a cached NCEI depth, {len(tris)} elements")
    log("Paths through the water from every station...")
    near = {n: [] for n in nodes}
    for i, s in enumerate(sources):
        for n, d in mesh.paths(s["node"], REACH_KM).items():
            if n in near:
                near[n].append((d, i))
    log(f"Streaming the velocity file for {len(nodes)} nodes (a few minutes)...")
    header = read_vel_header(reg["db"])
    vals = read_vel_nodes(reg["db"], nodes)
    prof = profile_table(reg["profile_rows"])
    hab = a.above_bottom
    out_vals, nearest = {}, []
    for n in nodes:
        cons = [{"name": h[0], "f_ref": h[2], "v0u_deg": h[3], "u_amp": v[0], "u_phase": v[1],
                 "v_amp": v[2], "v_phase": v[3]} for h, v in zip(header, vals[n])]
        uv = to_noaa(cons, reg["db"])
        fl = floor_km({i: d for d, i in near[n]}, lat[n], lon[n], sources)
        cand = sorted(((d, sources[i]) for i, d in fl.items()), key=lambda x: x[0])[:NEIGHBOURS]
        nearest.append(cand[0][0] if cand else None)
        frac = min(hab / depth[n], 1.0) if depth[n] > hab else 1.0
        Zn, m, az, _ = blend_at(uv, cand, prof, frac, fl, sources)
        axis = adcirc_axis(uv, az)
        A = along(uv, axis)
        # the database's field at the node, turned onto the blended axis and scaled and shifted to
        # the blended constants along it; a constituent the database barely carries fades with it
        turn = wrap90(az - axis)
        ct, st = math.cos(turn * DEG), math.sin(turn * DEG)
        row = []
        for h, v in zip(header, vals[n]):
            key = noaa_name(h[0])
            if key not in uv:
                row.append(v)
                continue
            F = Zn.get(key, 0) / A[key] if abs(A[key]) >= 0.01 else 0j
            # turned clockwise by `turn`, then scaled and shifted by the correction
            cu, cv = cmath.rect(v[0], v[1] * DEG), cmath.rect(v[2], v[3] * DEG)
            cu, cv = cu * ct + cv * st, cv * ct - cu * st
            cu, cv = cu * F.conjugate(), cv * F.conjugate()
            row.append((abs(cu), math.degrees(cmath.phase(cu)), abs(cv), math.degrees(cmath.phase(cv))))
        m = m / 100
        mu, mv = m * math.sin(az * DEG), m * math.cos(az * DEG)
        row.append((abs(mu), 0.0 if mu >= 0 else 180.0, abs(mv), 0.0 if mv >= 0 else 180.0))
        out_vals[n] = row
    header = header + [("Z0", 0.0, 1.0, 0.0)]
    import array
    import base64
    q = array.array("B", [255 if d is None else min(254, round(d * 10)) for d in nearest])
    sh = array.array("B", [1 if n in shore else 0 for n in nodes])
    extra = {"aboveBottomM": hab, "nearestKm": base64.b64encode(q.tobytes()).decode("ascii"),
             "shoreNodes": base64.b64encode(sh.tobytes()).decode("ascii"), "extendKm": EXTEND_KM}
    out = a.out or os.path.join(WORKSPACE, "map", "currents", f"{a.name}.js")
    write_overlay(a.name, a.label, boxes, reg["db"], lon, lat, nodes, tris, header, out_vals, a.max_drop,
                  f"{reg['db']} ADCIRC tidal database corrected by NOAA and CHS current stations, {hab:g} m above the seabed",
                  out, "blend_model.py", _cfg("max_speed_ms", 0.25), extra=extra, kind="seafloor")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("build", help="gather a region's stations and their corrections, once")
    s.add_argument("--name", required=True, help="the region's name")
    s.add_argument("--bbox", nargs=4, type=float, metavar=("S", "W", "N", "E"), required=True)
    s.add_argument("--fit-year", type=int, default=date.today().year,
                   help="the year of CHS predictions the Canadian stations' constants are fitted to (default this year)")
    s.set_defaults(fn=cmd_build)

    s = sub.add_parser("extract", help="a site's constants, written into its JSON (or a point's, printed)")
    g = s.add_mutually_exclusive_group(required=True)
    g.add_argument("--site", metavar="PATH", help="the site JSON: reads its lat, lon and seabed_m, and writes the extract into it")
    g.add_argument("--near", nargs=2, type=float, metavar=("LAT", "LON"), help="a point that is not a site yet: prints the extract")
    s.add_argument("--seabed", type=float, metavar="M", help="with --near: the seabed depth at the point, m")
    s.add_argument("--above-bottom", type=float, default=ABOVE_BOTTOM, metavar="M",
                   help=f"height above the seabed, m (default {ABOVE_BOTTOM:g})")
    s.set_defaults(fn=cmd_extract)

    tz_help = "the site's time zone, the `tz` in its JSON"

    def doc_source(sp):
        g = sp.add_mutually_exclusive_group(required=True)
        g.add_argument("--json", metavar="JSON", help="the extract's full JSON content, inline")
        g.add_argument("--file", metavar="PATH", help="path to the site JSON holding the extract")
        sp.add_argument("--tz", required=True, metavar="IANA_ZONE", help=tz_help)
        sp.add_argument("--raw", action="store_true",
                        help="the model's own prediction, without the site's observed offset: what an offset is measured against")

    s = sub.add_parser("predict", help="slack / max flood / max ebb")
    doc_source(s)
    s.add_argument("--date", type=date.fromisoformat, required=True)
    s.set_defaults(fn=cmd_predict)

    s = sub.add_parser("window", help="diveable windows")
    doc_source(s)
    s.add_argument("--date", type=date.fromisoformat, required=True)
    ms = _cfg("max_speed_ms", 0.25)
    s.add_argument("--max-speed", type=float, default=ms, help=f"m/s, default {ms}")
    s.set_defaults(fn=cmd_window)

    s = sub.add_parser("at", help="the current at a moment")
    doc_source(s)
    s.add_argument("--time", required=True, metavar="YYYY-MM-DD HH:MM")
    s.set_defaults(fn=cmd_at)

    s = sub.add_parser("verify", help="accuracy against hidden NOAA stations and the legacy tables")
    s.add_argument("--name", required=True, help="the region's name")
    s.add_argument("--start", type=date.fromisoformat, default=date(date.today().year, 12, 1),
                   help="first day of the test (default 1 December this year)")
    s.add_argument("--days", type=int, default=30)
    s.set_defaults(fn=cmd_verify)

    s = sub.add_parser("export-map", help="write the map viewer's seafloor current overlay")
    s.add_argument("--bbox", nargs=4, type=float, metavar=("S", "W", "N", "E"), required=True, action="append",
                   help="bounding box; repeat it to cover the union of several boxes")
    s.add_argument("--name", required=True, help="the overlay's key, and its file name under map/currents/")
    s.add_argument("--label", required=True, help="display name of the area it covers")
    s.add_argument("--region", help="the built region to correct with (default the one holding the boxes' centre)")
    s.add_argument("--above-bottom", type=float, default=ABOVE_BOTTOM, metavar="M")
    s.add_argument("--max-drop", type=float, default=0.03,
                   help="m/s: the most amplitude dropped constituents may cost any node (default 0.03)")
    s.add_argument("--out", help="output path (default map/currents/<name>.js)")
    s.set_defaults(fn=cmd_export_map)

    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()

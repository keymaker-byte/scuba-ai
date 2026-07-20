#!/usr/bin/env python3
"""Spatial tidal current prediction from the ENPAC15 ADCIRC tidal database. Metric (m/s).

A supplement to noaa_current.py, not a replacement. NOAA current stations are harmonic
analyses of real measurements at one point and are the better number wherever a station
exists. ENPAC15 is a smooth, depth-averaged regional model: its value is the water BETWEEN
stations and at sites with no nearby station. It under-represents the sharp flood/ebb
asymmetry of real rapids, so treat it as the big picture, not the last word.

Two use cases, two paths:

  extract SLUG --near LAT LON [--water-depth M]
                                  pull the harmonic constituents at a site from the database
                                  (writes SLUG.json beside the site's SLUG.md in
                                  regions/<region>/sites/). Needed once when writing a new
                                  site file. Pass --water-depth (m below MLLW, from
                                  ncei_depth.py) to enable depth scaling. Downloads the
                                  ~700 MB database on first use if tools/db/ is empty.
  predict SLUG [--date D] [--depth M]   slack / max flood / max ebb from the site's extract
  window  SLUG [--date D] [--depth M]   diveable windows under a speed threshold
  at      SLUG --time "..." [--depth M] instantaneous current vector

Prediction reads only the tiny per-site extract; it never touches the big database.

The model current is depth-AVERAGED (the column mean, which runs slower than the near-surface
flow). Pass --depth to scale it toward your dive depth through a boundary-layer profile:
slower near the seabed, faster up high. Slack times do not move, only speeds. It is
approximate and ignores stratification, so where a proven NOAA station exists, trust the
station's depth bin. Times are America/Los_Angeles.
"""
import argparse
import glob
import gzip
import json
import math
import os
import sys
import urllib.request
from datetime import date, datetime, timezone, timedelta
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
WORKSPACE = os.path.dirname(HERE)
DB = os.path.join(HERE, "db")
MESH_GZ = os.path.join(DB, "wc2015_v1a_chk.grd.gz")
VEL_GZ = os.path.join(DB, "wc2015-v1a_1200tau1dt1VDatum_fort.54.gz")

# The ADCIRC tidal databases are distributed as static tarballs (no query API). The full
# ENPAC15 archive (elevation + velocity) lives on Dropbox, linked from
# https://adcirc.org/products/adcirc-tidal-databases/ . We only need the mesh and the
# velocity harmonics (fort.54); the 215 MB elevation file (fort.53) is skipped.
DB_TAR_URL = "https://www.dropbox.com/s/yeswh43qhw982ut/ENPAC15_tidaldatabase.tar?dl=1"
TAR_MESH = "ENPAC15_tidaldatabase/wc2015_v1a_chk.grd.gz"
TAR_VEL = "ENPAC15_tidaldatabase/wc2015-v1a_1200tau1dt1VDatum_fort.54.gz"

# The ENPAC mesh is too coarse to resolve nearshore bathymetry (its elements can span the
# beach to the deep basin), so the --depth scaling should not rely on it. Pass the real
# seabed depth with --water-depth (get it from tools/ncei_depth.py, which owns bathymetry);
# the coarse mesh depth is only a fallback when none is given.

PACIFIC = ZoneInfo("America/Los_Angeles")
UTC = timezone.utc


def _cfg(key, default):
    """Read this tool's section of tool-config.json; missing file or key -> default."""
    try:
        with open(os.path.join(WORKSPACE, "tool-config.json")) as f:
            return json.load(f).get("adcirc_current", {}).get(key, default)
    except (OSError, ValueError):
        return default

# ADCIRC run wc2015_v1a: fort.15 REFTIME 0.0, run id "410day_start_11162004". The nodal
# factors and equilibrium arguments in the fort.53/54 headers are therefore referenced to
# this instant. We calibrate our astronomy's phase constants against those header values,
# which pins our convention to ADCIRC's own regardless of the ±90°/180° species offsets.
REF_EPOCH = datetime(2004, 11, 16, 0, 0, tzinfo=UTC)

DEG = math.pi / 180.0

# --------------------------------------------------------------------------------------
# Tidal astronomy (pure Python, Schureman-style series). Doodson coefficients are on
# (T, s, h, p, pp): T = mean-sun hour angle, s/h/p/pp = mean longitudes of moon, sun,
# lunar perigee, solar perigee. The ascending-node term is carried by the nodal (f, u)
# correction, not by a coefficient. Frequencies implied by these coefficients are checked
# against the fort.54 header in `selftest`.
# --------------------------------------------------------------------------------------

# name -> (doodson (nT, ns, nh, np, npp), nodal_key)
CONSTITUENTS = {
    "M(2)":      ((2, -2, 2, 0, 0),  "M2"),
    "N(2)":      ((2, -3, 2, 1, 0),  "M2"),
    "S(2)":      ((2, 0, 0, 0, 0),   "none"),
    "O(1)":      ((1, -2, 1, 0, 0),  "O1"),
    "K(1)":      ((1, 0, 1, 0, 0),   "K1"),
    "K(2)":      ((2, 0, 2, 0, 0),   "K2"),
    "L(2)":      ((2, -1, 2, -1, 0), "fixed"),
    "2N(2)":     ((2, -4, 2, 2, 0),  "M2"),
    "R(2)":      ((2, 0, 1, 0, -1),  "none"),
    "T(2)":      ((2, 0, -1, 0, 1),  "none"),
    "Lambda(2)": ((2, -1, 0, 1, 0),  "M2"),
    "Mu(2)":     ((2, -4, 4, 0, 0),  "M2"),
    "Nu(2)":     ((2, -3, 4, -1, 0), "M2"),
    "J(1)":      ((1, 1, 1, -1, 0),  "J1"),
    "M(1)":      ((1, -1, 1, 0, 0),  "fixed"),
    "OO(1)":     ((1, 2, 1, 0, 0),   "OO1"),
    "P(1)":      ((1, 0, -1, 0, 0),  "none"),
    "Q(1)":      ((1, -3, 1, 1, 0),  "O1"),
    "2Q(1)":     ((1, -4, 1, 2, 0),  "O1"),
    "Rho(1)":    ((1, -3, 3, -1, 0), "O1"),
    "M(4)":      ((4, -4, 4, 0, 0),  "M2^2"),
    "M(6)":      ((6, -6, 6, 0, 0),  "M2^3"),
    "M(8)":      ((8, -8, 8, 0, 0),  "M2^4"),
    "S(4)":      ((4, 0, 0, 0, 0),   "none"),
    "S(6)":      ((6, 0, 0, 0, 0),   "none"),
    "M(3)":      ((3, -3, 3, 0, 0),  "M2^1.5"),
    "S(1)":      ((1, 0, 0, 0, 0),   "none"),
    "MK(3)":     ((3, -2, 3, 0, 0),  "M2*K1"),
    "2MK(3)":    ((3, -4, 3, 0, 0),  "M2^2*K1"),
    "MN(4)":     ((4, -5, 4, 1, 0),  "M2^2"),
    "MS(4)":     ((4, -2, 2, 0, 0),  "M2"),
    "2SM(2)":    ((2, 2, -2, 0, 0),  "M2"),
    "Mf":        ((0, 2, 0, 0, 0),   "Mf"),
    "Msf":       ((0, 2, -2, 0, 0),  "M2"),
    "Mm":        ((0, 1, 0, -1, 0),  "Mm"),
    "Sa":        ((0, 0, 1, 0, 0),   "none"),
    "Ssa":       ((0, 0, 2, 0, 0),   "none"),
}


def mean_longitudes(dt):
    """s, h, p, N, pp (degrees) at a UTC datetime, plus T (mean-sun hour angle, deg)."""
    jd = 2440587.5 + dt.timestamp() / 86400.0
    t = (jd - 2451545.0) / 36525.0  # Julian centuries from J2000.0
    s = 218.3164477 + 481267.88123421 * t - 0.0015786 * t * t
    h = 280.46646 + 36000.76983 * t + 0.0003032 * t * t
    p = 83.3532465 + 4069.0137287 * t - 0.01032 * t * t
    n = 125.04452 - 1934.136261 * t + 0.0020708 * t * t
    pp = 282.937348 + 1.7195366 * t + 0.00045688 * t * t
    ut_h = dt.hour + dt.minute / 60.0 + dt.second / 3600.0
    tt = 15.0 * ut_h  # constant offset folds into the per-constituent phase calibration
    return s % 360, h % 360, p % 360, n % 360, pp % 360, tt % 360


def _base_nodal(key, N):
    """Schureman f (factor) and u (phase, deg) for the fundamental nodal groups."""
    c, c2, c3 = math.cos(N * DEG), math.cos(2 * N * DEG), math.cos(3 * N * DEG)
    s, s2, s3 = math.sin(N * DEG), math.sin(2 * N * DEG), math.sin(3 * N * DEG)
    if key == "M2":
        return 1.0004 - 0.0373 * c + 0.0002 * c2, -2.14 * s
    if key == "O1":
        return (1.0089 + 0.1871 * c - 0.0147 * c2 + 0.0014 * c3,
                10.80 * s - 1.34 * s2 + 0.19 * s3)
    if key == "K1":
        return (1.0060 + 0.1150 * c - 0.0088 * c2 + 0.0006 * c3,
                -8.86 * s + 0.68 * s2 - 0.07 * s3)
    if key == "K2":
        return (1.0241 + 0.2863 * c + 0.0083 * c2 - 0.0015 * c3,
                -17.74 * s + 0.68 * s2 - 0.04 * s3)
    if key == "J1":
        return (1.0129 + 0.1676 * c - 0.0170 * c2 + 0.0016 * c3,
                -12.94 * s + 1.34 * s2 - 0.19 * s3)
    if key == "OO1":
        return (1.1027 + 0.6504 * c + 0.0317 * c2 - 0.0014 * c3,
                -36.68 * s + 4.02 * s2 - 0.57 * s3)
    if key == "Mf":
        return 1.0429 + 0.4135 * c - 0.0040 * c2, -23.74 * s + 2.68 * s2 - 0.38 * s3
    if key == "Mm":
        return 1.0000 - 0.1300 * c + 0.0013 * c2, 0.0
    return 1.0, 0.0


def nodal(key, N, header_f):
    """f, u (deg) for any constituent key, including compound products. `header_f` is used
    for the two special constituents (L2, M1) whose nodal depends on perigee, not just N;
    holding them at the database's own reference value costs only their tiny time variation.
    """
    if key == "none":
        return 1.0, 0.0
    if key == "fixed":
        return header_f, 0.0
    if key in ("M2", "O1", "K1", "K2", "J1", "OO1", "Mf", "Mm"):
        return _base_nodal(key, N)
    # compound constituents: f multiplies, u adds
    fm, um = _base_nodal("M2", N)
    fk, uk = _base_nodal("K1", N)
    table = {
        "M2^2": (fm ** 2, 2 * um),
        "M2^3": (fm ** 3, 3 * um),
        "M2^4": (fm ** 4, 4 * um),
        "M2^1.5": (fm ** 1.5, 1.5 * um),
        "M2*K1": (fm * fk, um + uk),
        "M2^2*K1": (fm ** 2 * fk, 2 * um + uk),
    }
    return table[key]


def calibrate(cons):
    """Given the constituent list from an extract (each with name, v0u_deg, f_ref), return
    {name: C_rad}. C absorbs ADCIRC's species phase offsets and any convention constant."""
    s, h, p, N, pp, T = mean_longitudes(REF_EPOCH)
    C = {}
    for c in cons:
        name = c["name"]
        (nT, ns, nh, np_, npp), key = CONSTITUENTS[name]
        a = (nT * T + ns * s + nh * h + np_ * p + npp * pp) * DEG
        _, u = nodal(key, N, c["f_ref"])
        C[name] = c["v0u_deg"] * DEG - (a + u * DEG)
    return C


def reconstruct(cons, C, dt, comp):
    """Depth-averaged velocity component (m/s) at UTC datetime `dt`. comp = 'u' (east) or
    'v' (north)."""
    s, h, p, N, pp, T = mean_longitudes(dt)
    amp_key, ph_key = (comp + "_amp"), (comp + "_phase")
    total = 0.0
    for c in cons:
        (nT, ns, nh, np_, npp), key = CONSTITUENTS[c["name"]]
        a = (nT * T + ns * s + nh * h + np_ * p + npp * pp) * DEG
        f, u = nodal(key, N, c["f_ref"])
        base = a + u * DEG + C[c["name"]]
        total += f * c[amp_key] * math.cos(base - c[ph_key] * DEG)
    return total


# --------------------------------------------------------------------------------------
# Mesh + fort.54 extraction
# --------------------------------------------------------------------------------------

def _need_db():
    if os.path.exists(MESH_GZ) and os.path.exists(VEL_GZ):
        return
    os.makedirs(DB, exist_ok=True)
    print("ENPAC15 database not present in tools/db/.")
    print(f"Downloading ~700 MB from the ADCIRC tidal database (one time)...", flush=True)
    import tarfile
    req = urllib.request.Request(DB_TAR_URL, headers={"User-Agent": "dive-planning"})
    with urllib.request.urlopen(req, timeout=120) as r:
        # stream the tar; extract only the two members we need, never storing the 700 MB
        with tarfile.open(fileobj=r, mode="r|") as tar:
            targets = {TAR_MESH: MESH_GZ, TAR_VEL: VEL_GZ}
            for m in tar:
                if m.name in targets:
                    print(f"  extracting {m.name} ({m.size / 1e6:.0f} MB)...", flush=True)
                    src = tar.extractfile(m)
                    with open(targets[m.name], "wb") as out:
                        while True:
                            chunk = src.read(1 << 20)
                            if not chunk:
                                break
                            out.write(chunk)
                    targets.pop(m.name)
                    if not targets:
                        break
    print("  done.", flush=True)


def read_mesh():
    """Return (lon, lat, dep, elements). lon/lat/dep indexed by node number (1-based, index 0
    unused); dep is still-water depth below the model datum (m). elements are (n1, n2, n3)."""
    with gzip.open(MESH_GZ, "rt") as fh:
        fh.readline()  # title
        ne, np_ = (int(x) for x in fh.readline().split())
        lon = [0.0] * (np_ + 1)
        lat = [0.0] * (np_ + 1)
        dep = [0.0] * (np_ + 1)
        for _ in range(np_):
            parts = fh.readline().split()
            i = int(parts[0])
            lon[i] = float(parts[1])
            lat[i] = float(parts[2])
            dep[i] = float(parts[3])
        elems = []
        for _ in range(ne):
            parts = fh.readline().split()
            elems.append((int(parts[2]), int(parts[3]), int(parts[4])))
    return lon, lat, dep, elems


def locate(lon, lat, elems, qlon, qlat):
    """Find the element containing (qlon, qlat); return (nodes, weights, inside, dist_km).
    Inside the mesh dist_km is 0. Outside (a shore-entry coordinate is often just past the
    model's wet boundary), snap to the element on the nearest node and report how far out."""
    for n in elems:
        x1, y1 = lon[n[0]], lat[n[0]]
        x2, y2 = lon[n[1]], lat[n[1]]
        x3, y3 = lon[n[2]], lat[n[2]]
        if qlon < min(x1, x2, x3) or qlon > max(x1, x2, x3):
            continue
        if qlat < min(y1, y2, y3) or qlat > max(y1, y2, y3):
            continue
        det = (y2 - y3) * (x1 - x3) + (x3 - x2) * (y1 - y3)
        if det == 0:
            continue
        w1 = ((y2 - y3) * (qlon - x3) + (x3 - x2) * (qlat - y3)) / det
        w2 = ((y3 - y1) * (qlon - x3) + (x1 - x3) * (qlat - y3)) / det
        w3 = 1 - w1 - w2
        if w1 >= -1e-9 and w2 >= -1e-9 and w3 >= -1e-9:
            return list(n), [w1, w2, w3], True, 0.0
    # outside: nearest node, and the element on it
    scale = math.cos(math.radians(qlat))
    bn, bd = 1, float("inf")
    for i in range(1, len(lon)):
        d = ((lon[i] - qlon) * scale) ** 2 + (lat[i] - qlat) ** 2
        if d < bd:
            bd, bn = d, i
    dist_km = math.sqrt(bd) * 111.0
    for n in elems:
        if bn in n:
            return list(n), [1 / 3, 1 / 3, 1 / 3], False, dist_km
    return [bn, bn, bn], [1 / 3, 1 / 3, 1 / 3], False, dist_km


def read_vel_header():
    """Return list of (name, freq_rad_s, f_ref, v0u_deg) from the fort.54 header, in order."""
    with gzip.open(VEL_GZ, "rt") as fh:
        nfreq = int(fh.readline())
        out = []
        for _ in range(nfreq):
            parts = fh.readline().split()
            freq, fnf, eqarg = float(parts[0]), float(parts[1]), float(parts[2])
            name = parts[3]
            out.append((name, freq, fnf, eqarg))
    return out


def read_vel_nodes(want):
    """Stream fort.54; return {node: [(u_amp, u_phase, v_amp, v_phase), ...37...]} for the
    requested node numbers. Node records are in increasing order, so we stop at the last."""
    want = set(want)
    stop = max(want)
    found = {}
    with gzip.open(VEL_GZ, "rt") as fh:
        nfreq = int(fh.readline())
        for _ in range(nfreq):
            fh.readline()
        fh.readline()  # NP
        while want:
            line = fh.readline()
            if not line:
                break
            node = int(line.split()[0])
            rows = [fh.readline() for _ in range(nfreq)]
            if node in want:
                cons = []
                for r in rows:
                    a = r.split()
                    cons.append((float(a[0]), float(a[1]), float(a[2]), float(a[3])))
                found[node] = cons
                want.discard(node)
            if node >= stop:
                break
    return found


def interp_polar(amp1, ph1, amp2, ph2, amp3, ph3, w):
    """Weight-interpolate three (amp, phase-deg) pairs via their complex form."""
    re = im = 0.0
    for amp, ph, wi in ((amp1, ph1, w[0]), (amp2, ph2, w[1]), (amp3, ph3, w[2])):
        re += wi * amp * math.cos(ph * DEG)
        im += wi * amp * math.sin(ph * DEG)
    return math.hypot(re, im), math.degrees(math.atan2(im, re)) % 360


# --------------------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------------------

def sites_dirs():
    """Every regions/<region>/sites/ folder in the workspace."""
    return sorted(glob.glob(os.path.join(WORKSPACE, "regions", "*", "sites")))


def extract_path(slug, region=None):
    """Where SLUG.json lives: beside the site's SLUG.md in regions/<region>/sites/. If the
    .md does not exist yet (a brand-new site), fall back to the named region, or the sole
    region if there is only one."""
    for d in sites_dirs():
        if os.path.exists(os.path.join(d, slug + ".md")):
            return os.path.join(d, slug + ".json")
    dirs = sites_dirs()
    if region:
        d = os.path.join(WORKSPACE, "regions", region, "sites")
        if d not in dirs:
            sys.exit(f"No such region sites folder: {d}")
        return os.path.join(d, slug + ".json")
    if len(dirs) == 1:
        return os.path.join(dirs[0], slug + ".json")
    sys.exit(f"Multiple regions found; pass --region. Options: "
             f"{[os.path.basename(os.path.dirname(d)) for d in dirs]}")


def find_extract(slug):
    """Locate an existing SLUG.json under any region's sites/ folder."""
    for d in sites_dirs():
        p = os.path.join(d, slug + ".json")
        if os.path.exists(p):
            return p
    return None


def cmd_extract(a):
    slug = a.slug
    path = extract_path(slug, a.region)
    if os.path.exists(path) and not a.force:
        sys.exit(f"Extract already exists: {path}\n  pass --force to overwrite.")
    _need_db()
    qlat, qlon = a.near
    print(f"Reading mesh ({os.path.basename(MESH_GZ)})...", flush=True)
    lon, lat, dep, elems = read_mesh()
    print(f"  {len(elems)} elements, locating {qlat:.5f}, {qlon:.5f}...", flush=True)
    nodes, w, inside, dist_km = locate(lon, lat, elems, qlon, qlat)
    water_depth = sum(w[i] * dep[nodes[i]] for i in range(3))
    if not inside:
        print(f"  point is outside the wet mesh; snapped to nearest edge {dist_km:.2f} km away.")
        if dist_km > 2.0:
            print("  That is far: the site is likely unresolved. Trust a NOAA station instead.")
        else:
            print("  Close to the boundary (a shore entry usually is); usable with caution.")
    else:
        print(f"  in element with nodes {nodes}, weights "
              f"{w[0]:.3f}/{w[1]:.3f}/{w[2]:.3f}", flush=True)
    if a.water_depth is not None:
        water_depth_m = a.water_depth
        depth_src = "provided (m below MLLW)"
        print(f"  water depth {water_depth_m:.1f} m (provided)", flush=True)
    else:
        water_depth_m = round(water_depth, 1)
        depth_src = "ADCIRC mesh (coarse; pass --water-depth from ncei_depth for a real depth)"
        print(f"  no --water-depth given; using coarse mesh depth {water_depth_m:.1f} m "
              f"(scaling will be rough)", flush=True)
    header = read_vel_header()
    print("Streaming fort.54 for the 3 nodes (one pass, may take a minute)...", flush=True)
    vals = read_vel_nodes(nodes)
    cons = []
    for k, (name, freq, fnf, eqarg) in enumerate(header):
        n0, n1, n2 = vals[nodes[0]][k], vals[nodes[1]][k], vals[nodes[2]][k]
        u_amp, u_ph = interp_polar(n0[0], n0[1], n1[0], n1[1], n2[0], n2[1], w)
        v_amp, v_ph = interp_polar(n0[2], n0[3], n1[2], n1[3], n2[2], n2[3], w)
        cons.append({
            "name": name, "f_ref": fnf, "v0u_deg": eqarg,
            "u_amp": u_amp, "u_phase": u_ph, "v_amp": v_amp, "v_phase": v_ph,
        })
    os.makedirs(os.path.dirname(path), exist_ok=True)
    doc = {
        "slug": slug, "lat": qlat, "lon": qlon,
        "source": "ENPAC15 (wc2015_v1a), depth-averaged tidal current",
        "extracted_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "water_depth_m": water_depth_m,
        "water_depth_source": depth_src,
        "mesh": {"inside": inside, "boundary_dist_km": round(dist_km, 3)},
        "constituents": cons,
    }
    with open(path, "w") as fh:
        json.dump(doc, fh, indent=2)
    axis, _ = principal_axis(doc)
    print(f"\nWrote {path}")
    print(f"  {len(cons)} constituents. Principal current axis {axis:.0f}°/{(axis + 180) % 360:.0f}° T.")
    print(f"  Water depth {water_depth_m:.0f} m (enables --depth scaling in predict/window).")
    print("  Validate against the nearest NOAA station before trusting timing (see selftest).")


def load_extract(slug):
    path = find_extract(slug)
    if not path:
        sys.exit(f"No extract for '{slug}'.\n"
                 f"  Create it first:  python3 {os.path.basename(__file__)} "
                 f"extract {slug} --near LAT LON")
    with open(path) as fh:
        return json.load(fh)


def series(doc, day):
    """(local_datetime, u_east, v_north) every 6 minutes across the local day, plus a margin."""
    cons, C = doc["constituents"], calibrate(doc["constituents"])
    start = datetime(day.year, day.month, day.day, tzinfo=PACIFIC)
    out = []
    for i in range(-20, 240 + 20):  # -2h .. +26h at 6-min steps
        t_local = start + timedelta(minutes=6 * i)
        t_utc = t_local.astimezone(UTC)
        u = reconstruct(cons, C, t_utc, "u")
        v = reconstruct(cons, C, t_utc, "v")
        out.append((t_local, u, v))
    return out


def principal_axis(doc, day=None):
    """Return (bearing_deg, samples). Bearing of the dominant flow axis (°T)."""
    day = day or date.today()
    samp = series(doc, day)
    sxx = sxy = syy = 0.0
    for _, u, v in samp:
        sxx += u * u
        sxy += u * v
        syy += v * v
    # principal eigenvector of [[sxx, sxy], [sxy, syy]]
    theta = 0.5 * math.atan2(2 * sxy, sxx - syy)  # angle from east axis, math convention
    ax_e, ax_n = math.cos(theta), math.sin(theta)
    bearing = math.degrees(math.atan2(ax_e, ax_n)) % 360  # compass, toward
    return bearing, samp


def _signed(samp, bearing):
    """Signed along-axis speed (m/s) at each sample; positive = toward `bearing`."""
    ax_e, ax_n = math.sin(bearing * DEG), math.cos(bearing * DEG)
    return [(t, u * ax_e + v * ax_n, math.hypot(u, v)) for t, u, v in samp]


def depth_factor(doc, dive_depth):
    """Multiplier from the column-mean speed to the speed at `dive_depth` (m below surface),
    via a 1/7-power tidal boundary layer. The mean sits at ~0.4 of the depth up from the bed;
    below that the water runs slower, above it faster. Returns (factor, note). A None dive
    depth (or a site with no stored water depth) leaves the column mean unscaled."""
    if dive_depth is None:
        return 1.0, "depth-averaged (whole column); near-surface runs faster"
    h = doc.get("water_depth_m")
    if not h or h <= 0:
        return 1.0, "no water depth stored for this site; showing the column mean"
    if dive_depth >= h:
        return 1.0, (f"dive depth {dive_depth:.0f} m is at/below the modelled seabed "
                     f"(~{h:.0f} m here); cannot scale, showing the column mean. The extract "
                     f"point is probably too close to shore, re-extract nearer the dive area")
    z = h - dive_depth                      # height above the bed
    frac = min(max(z / h, 0.05), 1.0)       # clamp: the profile is invalid right at the bed
    factor = (8.0 / 7.0) * frac ** (1.0 / 7.0)
    return factor, (f"scaled to {dive_depth:.0f} m in ~{h:.0f} m of water (x{factor:.2f} of the "
                    f"column mean, 1/7-power profile; approximate, ignores stratification)")


def reconstructors(doc, bearing):
    """(signed_fn, mag_fn): callables from a local datetime to the along-axis signed speed and
    to the total speed magnitude (both un-scaled by depth), evaluating the full reconstruction
    at any instant. These let slack and window boundaries be root-found off the 6-minute grid."""
    cons, C = doc["constituents"], calibrate(doc["constituents"])
    ax_e, ax_n = math.sin(bearing * DEG), math.cos(bearing * DEG)

    def uv(t_local):
        tu = t_local.astimezone(UTC)
        return reconstruct(cons, C, tu, "u"), reconstruct(cons, C, tu, "v")

    def signed_fn(t):
        u, v = uv(t)
        return u * ax_e + v * ax_n

    def mag_fn(t):
        u, v = uv(t)
        return math.hypot(u, v)

    return signed_fn, mag_fn


def refine_zero(f, t0, t1, tol_s=2.0):
    """Bisect for the root of f between t0 and t1, which must bracket a sign change. Halves the
    interval on the continuous function until it is under tol_s, so the crossing is pinned to a
    couple of seconds rather than read off the 6-minute grid."""
    f0 = f(t0)
    if f0 == 0:
        return t0
    while (t1 - t0).total_seconds() > tol_s:
        tm = t0 + (t1 - t0) / 2
        fm = f(tm)
        if fm == 0:
            return tm
        if (f0 < 0) != (fm < 0):
            t1 = tm
        else:
            t0, f0 = tm, fm
    return t0 + (t1 - t0) / 2


def parabolic_peak(seg):
    """Refine a flood/ebb peak by fitting a parabola through the largest sample in `seg` and its
    two neighbours (the grid max clips the true peak low and off-time). seg is consecutive
    (t, signed, mag) samples. Returns (t_peak, signed_peak); falls back to the sample at a
    segment edge, where no parabola can be fit."""
    im = max(range(len(seg)), key=lambda i: abs(seg[i][1]))
    if im == 0 or im == len(seg) - 1:
        return seg[im][0], seg[im][1]
    y0, y1, y2 = seg[im - 1][1], seg[im][1], seg[im + 1][1]
    denom = y0 - 2 * y1 + y2
    if denom == 0:
        return seg[im][0], seg[im][1]
    off = 0.5 * (y0 - y2) / denom               # fractional samples from the middle, in [-1, 1]
    h = seg[im][0] - seg[im - 1][0]             # sample spacing
    return seg[im][0] + h * off, y1 - 0.25 * (y0 - y2) * off


def slacks_and_peaks(sig, signed_fn=None):
    """Chronological events from the signed along-axis series: ('slack', t) at each zero crossing
    and ('max', t, signed_speed) at the peak between crossings. With signed_fn, the slack is
    root-found on the continuous reconstruction and the peak is parabola-refined; without it, a
    linear/grid estimate."""
    slacks, prev = [], None
    for t, s, _ in sig:
        if prev is not None and (prev[1] <= 0 < s or prev[1] >= 0 > s):
            if signed_fn:
                tc = refine_zero(signed_fn, prev[0], t)
            else:
                frac = -prev[1] / (s - prev[1]) if s != prev[1] else 0
                tc = prev[0] + (t - prev[0]) * frac
            slacks.append(tc)
        prev = (t, s)
    events = [("slack", tc, 0.0) for tc in slacks]
    bounds = [sig[0][0]] + slacks + [sig[-1][0]]
    for a_t, b_t in zip(bounds, bounds[1:]):
        seg = [x for x in sig if a_t <= x[0] <= b_t]
        if not seg:
            continue
        tpk, spk = parabolic_peak(seg)
        if abs(spk) > 0.02:
            events.append(("max", tpk, spk))
    events.sort(key=lambda e: e[1])
    return events


def cmd_predict(a):
    doc = load_extract(a.slug)
    factor, note = depth_factor(doc, a.depth)
    bearing, samp = principal_axis(doc, a.date)
    sig = _signed(samp, bearing)
    signed_fn, _ = reconstructors(doc, bearing)
    axis_a, axis_b = bearing % 360, (bearing + 180) % 360
    print(f"{a.slug}  {a.date}  ENPAC15 tidal current")
    print(f"  principal axis {axis_a:.0f}° T / {axis_b:.0f}° T "
          f"(which is flood is site-specific; confirm against the tide or a NOAA station)")
    print(f"  {note}")
    if not doc["mesh"]["inside"]:
        km = doc["mesh"].get("boundary_dist_km", "?")
        print(f"  NOTE: site is {km} km outside the wet mesh (snapped to the boundary); "
              f"indicative only.")
    print()
    for kind, tt, s in slacks_and_peaks(sig, signed_fn):
        if tt.date() != a.date:
            continue
        if kind == "slack":
            print(f"  {tt:%H:%M}  SLACK")
        else:
            toward = axis_a if s > 0 else axis_b
            print(f"  {tt:%H:%M}  max {abs(s) * factor:.2f} m/s  toward {toward:.0f}° T")
    print("\n  Verify slack against a NOAA station before trusting it.")


def cmd_window(a):
    doc = load_extract(a.slug)
    factor, note = depth_factor(doc, a.depth)
    bearing, samp = principal_axis(doc, a.date)
    sig = _signed(samp, bearing)
    _, mag_fn = reconstructors(doc, bearing)
    lim = a.max_speed
    print(f"{a.slug}  {a.date}  ENPAC15 tidal current")
    print(f"  windows with speed <= {lim:.2f} m/s (principal axis {bearing:.0f}° T)")
    print(f"  {note}\n")
    # runs of below-threshold samples on the full grid, then root-find each edge (where the
    # speed actually crosses the threshold) instead of taking the nearest 6-minute sample.
    below = [(t, mag * factor <= lim, mag * factor) for t, s, mag in sig]
    runs, i, n = [], 0, len(sig)
    while i < n:
        if not below[i][1]:
            i += 1
            continue
        j = i
        while j + 1 < n and below[j + 1][1]:
            j += 1
        t0, t1 = sig[i][0], sig[j][0]
        peak = max(below[k][2] for k in range(i, j + 1))
        if i > 0:
            t0 = refine_zero(lambda t: mag_fn(t) * factor - lim, sig[i - 1][0], sig[i][0])
        if j < n - 1:
            t1 = refine_zero(lambda t: mag_fn(t) * factor - lim, sig[j][0], sig[j + 1][0])
        runs.append((t0, t1, peak))
        i = j + 1
    # keep runs overlapping the target day, clipped to it
    day0 = datetime(a.date.year, a.date.month, a.date.day, tzinfo=PACIFIC)
    day1 = day0 + timedelta(days=1)
    shown = [(max(t0, day0), min(t1, day1), pk) for t0, t1, pk in runs
             if t1 > day0 and t0 < day1]
    if not shown:
        print(f"  none — current never drops below {lim:.2f} m/s here on this date.")
        return
    for t0, t1, peak in shown:
        mins = round((t1 - t0).total_seconds() / 60)
        flag = "  <-- tight" if mins < 40 else ""
        print(f"  {t0:%H:%M} - {t1:%H:%M}   {mins:>3} min   peak {peak:.2f} m/s{flag}")
    print("\n  Pad it, and confirm against a NOAA station and observation.")


def cmd_at(a):
    doc = load_extract(a.slug)
    factor, note = depth_factor(doc, a.depth)
    t_local = datetime.strptime(a.time, "%Y-%m-%d %H:%M").replace(tzinfo=PACIFIC)
    cons, C = doc["constituents"], calibrate(doc["constituents"])
    t_utc = t_local.astimezone(UTC)
    u = reconstruct(cons, C, t_utc, "u") * factor
    v = reconstruct(cons, C, t_utc, "v") * factor
    spd = math.hypot(u, v)
    toward = math.degrees(math.atan2(u, v)) % 360
    print(f"{a.slug}  {t_local:%Y-%m-%d %H:%M %Z}")
    print(f"  {note}")
    print(f"  speed {spd:.2f} m/s   toward {toward:.0f}° T   (east {u:+.2f}, north {v:+.2f})")


def cmd_list(a):
    found = []
    for d in sites_dirs():
        for p in sorted(glob.glob(os.path.join(d, "*.json"))):
            try:
                with open(p) as fh:
                    doc = json.load(fh)
                if "constituents" in doc and "mesh" in doc:
                    found.append((os.path.relpath(p, WORKSPACE), doc))
            except (ValueError, KeyError):
                continue
    if not found:
        print("No extracts yet.")
        return
    print("ENPAC15 extracts:\n")
    for rel, doc in found:
        m = doc["mesh"]
        flag = "" if m["inside"] else f"  (edge {m.get('boundary_dist_km', '?')} km out)"
        print(f"  {doc['slug']:<24} {doc['lat']:.4f}, {doc['lon']:.4f}{flag}")
        print(f"    {rel}")


def cmd_selftest(a):
    """Validate the astronomy against the fort.54 header values at REF_EPOCH: the frequency
    implied by each constituent's Doodson coefficients, and its nodal factor f."""
    _need_db()
    header = read_vel_header()
    s, h, p, N, pp, T = mean_longitudes(REF_EPOCH)
    rates = {"T": 15.0, "s": 0.54901653, "h": 0.04106864, "p": 0.00464183, "pp": 0.00000196}
    print(f"Astronomy self-test at REF_EPOCH {REF_EPOCH:%Y-%m-%d %H:%M} UTC")
    print("  constituent   freq(mine)   freq(hdr)   dω%     f(mine)  f(hdr)   df")
    fmax = wmax = 0.0
    for name, freq, fnf, eqarg in header:
        (nT, ns, nh, np_, npp), key = CONSTITUENTS[name]
        deg_hr = (nT * rates["T"] + ns * rates["s"] + nh * rates["h"]
                  + np_ * rates["p"] + npp * rates["pp"])
        mine = deg_hr * DEG / 3600.0  # rad/s
        dw = 100 * (mine - freq) / freq if freq else 0.0
        f, _ = nodal(key, N, fnf)
        df = f - fnf
        wmax = max(wmax, abs(dw))
        if key not in ("fixed",):
            fmax = max(fmax, abs(df))
        print(f"  {name:<11} {mine:.6e} {freq:.6e} {dw:+6.2f}  {f:7.4f} {fnf:7.4f} {df:+.4f}")
    print(f"\n  max |dω| = {wmax:.3f}%   max |df| (computed groups) = {fmax:.4f}")
    # Frequencies are structural (wrong Doodson coefficients show here); they must be tight.
    # Nodal f is a series approximation of ADCIRC's exact value; a few percent is expected and
    # affects amplitude only, not slack timing.
    if wmax < 0.1 and fmax < 0.07:
        print("  PASS: frequencies match structurally; nodal factors within series tolerance.")
    else:
        print("  CHECK: a large frequency deviation means a wrong Doodson coefficient.")


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("extract", help="pull constituents at a site from the database")
    s.add_argument("slug")
    s.add_argument("--near", nargs=2, type=float, metavar=("LAT", "LON"), required=True)
    s.add_argument("--water-depth", type=float, metavar="M",
                   help="seabed depth below MLLW (from ncei_depth.py); enables --depth scaling")
    s.add_argument("--force", action="store_true", help="overwrite an existing extract")
    s.add_argument("--region", help="region folder for a brand-new site (default: the only one)")
    s.set_defaults(fn=cmd_extract)

    depth_help = "m below surface; scale the column mean to your dive depth (default: no scaling)"

    def dated(sp):
        sp.add_argument("slug")
        sp.add_argument("--date", type=date.fromisoformat, default=date.today())
        sp.add_argument("--depth", type=float, help=depth_help)

    s = sub.add_parser("predict", help="slack / max flood / max ebb")
    dated(s)
    s.set_defaults(fn=cmd_predict)

    s = sub.add_parser("window", help="diveable windows")
    dated(s)
    _ms = _cfg("max_speed_ms", 0.25)
    s.add_argument("--max-speed", type=float, default=_ms, help=f"m/s, default {_ms}")
    s.set_defaults(fn=cmd_window)

    s = sub.add_parser("at", help="instantaneous current vector")
    s.add_argument("slug")
    s.add_argument("--time", required=True, metavar="YYYY-MM-DD HH:MM")
    s.add_argument("--depth", type=float, help=depth_help)
    s.set_defaults(fn=cmd_at)

    s = sub.add_parser("list", help="list extracted sites")
    s.set_defaults(fn=cmd_list)

    s = sub.add_parser("selftest", help="validate astronomy against the ADCIRC header")
    s.set_defaults(fn=cmd_selftest)

    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()

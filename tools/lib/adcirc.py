"""ADCIRC tidal databases read by blend_model.py: the databases and their download, the
astronomy calibrated to each run and its self-test, and the mesh and velocity readers."""
import gzip
import math
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone, timedelta

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(TOOLS, "db")
UTC = timezone.utc

# The ADCIRC tidal databases are distributed as static tarballs (no query API), linked from
# https://adcirc.org/products/adcirc-tidal-databases/ . Only the mesh and the velocity
# harmonics (fort.54) are kept; the elevation file (fort.53) is skipped.
#
# epoch: the start of the ADCIRC run the database comes from. The nodal factors and
# equilibrium arguments in its fort.54 header are referenced to this instant; we calibrate
# our astronomy's phase constants against those header values, which pins our convention to
# ADCIRC's own regardless of the ±90°/180° species offsets.
#   ENPAC15, run wc2015_v1a: fort.15 REFTIME 0.0, run id "410day_start_11162004".
#   EC2015, run ec2012_v3d_otis3: REFTIM 0.0, run id "410day_start111791" (RunNotes.txt:
#   "nodal factors set for 410-day run starting on 11/17/1991").
# Both runs are 410 days long. ADCIRC sets the header's nodal factors f, and the nodal phase u
# inside its equilibrium arguments, at the middle of the run: f in both headers matches our
# series at epoch + 205 days to 0.002 (selftest), against 0.06 to 0.12 at the epoch itself.
# The equilibrium arguments' astronomical part V0 is at the epoch.
# domain: the mesh's own extent (S, W, N, E), which picks the database for a coordinate.
DATABASES = {
    "ENPAC15": {
        "key": "enpac15_constituents",
        "region": "Eastern North Pacific",
        "url": "https://www.dropbox.com/s/yeswh43qhw982ut/ENPAC15_tidaldatabase.tar?dl=1",
        "size": "~700 MB",
        "tar_mesh": "ENPAC15_tidaldatabase/wc2015_v1a_chk.grd.gz",
        "tar_vel": "ENPAC15_tidaldatabase/wc2015-v1a_1200tau1dt1VDatum_fort.54.gz",
        "mesh": os.path.join(DB, "wc2015_v1a_chk.grd.gz"),
        "vel": os.path.join(DB, "wc2015-v1a_1200tau1dt1VDatum_fort.54.gz"),
        "epoch": datetime(2004, 11, 16, 0, 0, tzinfo=UTC),
        "domain": (19.57, -187.59, 61.50, -109.56),
    },
    "EC2015": {
        "key": "ec2015_constituents",
        "region": "Western North Atlantic, Gulf of Mexico and Caribbean Sea",
        "url": "https://www.dropbox.com/s/muitrh9i4jlfqy2/ec2015_tidaldb.tar?dl=1",
        "size": "~2.6 GB",
        "tar_mesh": "ec2015_tidaldb/ec2012_v3d_chk.grd.gz",
        "tar_vel": "ec2015_tidaldb/ec2012_v3d_otis3_fort.54.gz",
        "mesh": os.path.join(DB, "ec2012_v3d_chk.grd.gz"),
        "vel": os.path.join(DB, "ec2012_v3d_otis3_fort.54.gz"),
        "epoch": datetime(1991, 11, 17, 0, 0, tzinfo=UTC),
        "domain": (5.72, -97.86, 45.87, -53.81),
    },
}


def in_domain(name, lat, lon):
    S, W, N, E = DATABASES[name]["domain"]
    return S <= lat <= N and W <= lon <= E


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


def nodal_epoch(db):
    """The instant a database's nodal factors and nodal phases are set for: mid-run."""
    return DATABASES[db]["epoch"] + timedelta(days=205)


def calibrate(cons, db):
    """Given the constituent list from an extract (each with name, v0u_deg, f_ref) and the
    database it came from, return {name: C_rad}. C absorbs ADCIRC's species phase offsets and
    any convention constant. V0 is taken at the run's epoch and u at mid-run, as ADCIRC does."""
    s, h, p, _, pp, T = mean_longitudes(DATABASES[db]["epoch"])
    N = mean_longitudes(nodal_epoch(db))[3]
    C = {}
    for c in cons:
        name = c["name"]
        (nT, ns, nh, np_, npp), key = CONSTITUENTS[name]
        a = (nT * T + ns * s + nh * h + np_ * p + npp * pp) * DEG
        _, u = nodal(key, N, c["f_ref"])
        C[name] = c["v0u_deg"] * DEG - (a + u * DEG)
    return C


def selftest(dbs=None):
    """Validate the astronomy against each database's fort.54 header values at its epoch: the
    frequency implied by each constituent's Doodson coefficients, and its nodal factor f.
    Prints a table per database and returns True when every database passes."""
    ok = True
    for db in (dbs or list(DATABASES)):
        need_db(db)
        epoch = nodal_epoch(db)
        header = read_vel_header(db)
        s, h, p, N, pp, T = mean_longitudes(epoch)
        rates = {"T": 15.0, "s": 0.54901653, "h": 0.04106864, "p": 0.00464183, "pp": 0.00000196}
        print(f"{db} astronomy self-test at mid-run, {epoch:%Y-%m-%d %H:%M} UTC")
        print("  constituent   freq(mine)   freq(hdr)   dω%     f(mine)  f(hdr)   df")
        fmax = wmax = 0.0
        for name, freq, fnf, eqarg in header:
            if name not in CONSTITUENTS:
                sys.exit(f"  {db} carries {name}, a constituent this tool does not know.")
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
        # Nodal f is a series approximation of ADCIRC's exact value at mid-run; it agrees to a
        # few thousandths, and a larger gap means the epoch or the mid-run convention is off.
        if wmax < 0.1 and fmax < 0.01:
            print("  PASS: frequencies match structurally; nodal factors within series tolerance.\n")
        else:
            ok = False
            print("  CHECK: a large frequency deviation means a wrong Doodson coefficient.\n")
    return ok

# --------------------------------------------------------------------------------------
# Mesh + fort.54 extraction
# --------------------------------------------------------------------------------------

def need_db(db):
    d = DATABASES[db]
    if os.path.exists(d["mesh"]) and os.path.exists(d["vel"]):
        return
    os.makedirs(DB, exist_ok=True)
    log = lambda m: print(m, file=sys.stderr, flush=True)
    log(f"{db} database not present in tools/db/.")
    log(f"Downloading {d['size']} from the ADCIRC tidal database (one time)...")
    import tarfile
    req = urllib.request.Request(d["url"], headers={"User-Agent": "dive-planning"})
    targets = {d["tar_mesh"]: d["mesh"], d["tar_vel"]: d["vel"]}
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            # stream the tar; extract only the two members we need, never storing the archive
            with tarfile.open(fileobj=r, mode="r|") as tar:
                for m in tar:
                    if m.name in targets:
                        log(f"  extracting {m.name} ({m.size / 1e6:.0f} MB)...")
                        src, part = tar.extractfile(m), targets[m.name] + ".part"
                        with open(part, "wb") as out:
                            while True:
                                chunk = src.read(1 << 20)
                                if not chunk:
                                    break
                                out.write(chunk)
                        if os.path.getsize(part) != m.size:
                            raise OSError(f"{m.name} arrived short")
                        os.replace(part, targets.pop(m.name))
                        if not targets:
                            break
    except (OSError, tarfile.TarError, urllib.error.URLError) as e:
        for path in targets.values():
            if os.path.exists(path + ".part"):
                os.remove(path + ".part")
        sys.exit(f"{db} download failed ({getattr(e, 'reason', e)}).\n  {d['url']}")
    if targets:
        sys.exit(f"{db} archive is missing {', '.join(targets)}.\n  {d['url']}")
    log("  done.")


def read_mesh(db, depth=False):
    """Return (lon, lat, elements), or (lon, lat, depth, elements) with `depth`. lon/lat/depth
    indexed by node number (1-based, index 0 unused); depth is the mesh's own water depth in
    metres. elements are (n1, n2, n3)."""
    with gzip.open(DATABASES[db]["mesh"], "rt") as fh:
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
    return (lon, lat, dep, elems) if depth else (lon, lat, elems)


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


WALK_STEP_M = 5


def walk_in(lon, lat, elems, qlon, qlat, step_m):
    """The nearest point of the mesh to (qlon, qlat), on the edge of its wet area, stepped
    step_m further in toward the centroid of the element it lies on (at most halfway there).
    Returns (lat, lon) rounded to 5 decimals, about a metre."""
    sc = math.cos(math.radians(qlat))
    px, py = qlon * sc, qlat
    for r in (0.05, 0.2, 1.0, 5.0):
        cand = [n for n in elems
                if any(abs(lat[i] - qlat) <= r and abs(lon[i] - qlon) <= r / sc for i in n)]
        if cand:
            break
    best = None
    for n in cand:
        tri = [(lon[i] * sc, lat[i]) for i in n]
        for k in range(3):
            (ax, ay), (bx, by) = tri[k], tri[k - 1]
            dx, dy = bx - ax, by - ay
            L2 = dx * dx + dy * dy
            t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
            cx, cy = ax + t * dx, ay + t * dy
            d = math.hypot(cx - px, cy - py)
            if best is None or d < best[0]:
                best = (d, cx, cy, tri)
    _, cx, cy, tri = best
    gx, gy = sum(t[0] for t in tri) / 3, sum(t[1] for t in tri) / 3
    L = math.hypot(gx - cx, gy - cy)
    step = min(step_m / 111000.0, 0.5 * L)
    wx, wy = cx + (gx - cx) * step / L, cy + (gy - cy) * step / L
    return round(wy, 5), round(wx / sc, 5)


def read_vel_header(db):
    """Return list of (name, freq_rad_s, f_ref, v0u_deg) from the fort.54 header, in order."""
    with gzip.open(DATABASES[db]["vel"], "rt") as fh:
        nfreq = int(fh.readline())
        out = []
        for _ in range(nfreq):
            parts = fh.readline().split()
            freq, fnf, eqarg = float(parts[0]), float(parts[1]), float(parts[2])
            name = parts[3]
            out.append((name, freq, fnf, eqarg))
    return out


def read_vel_nodes(db, want):
    """Stream fort.54; return {node: [(u_amp, u_phase, v_amp, v_phase), ...37...]} for the
    requested node numbers. Node records are in increasing order, so we stop at the last."""
    want = set(want)
    stop = max(want)
    found = {}
    with gzip.open(DATABASES[db]["vel"], "rt") as fh:
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

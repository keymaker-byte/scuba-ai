"""Current station networks as the Blend Model reads them: each network gathers its stations in a
box from what its own tool cached on this machine, and turns each one into bins, the form every
correction is made from. A bin is [fraction of the depth above the seabed, steady current cm/s,
flood azimuth, {constituent: [re, im]}], the constituent a complex amplitude Z = A e^(-ig) in cm/s
in NOAA's convention, along the flood. A new network joins by adding a class with `kind`, `gather`
and `prepare` to NETWORKS."""
import cmath
import json
import math
import os
import sys
from datetime import datetime, timedelta, timezone

from lib.tidal_astronomy import ALIAS, CONS, longitudes
from lib.noaa_stations import DB as NOAA_DB
from lib.tidal_astronomy import nodal as noaa_nodal

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHS_DB = os.path.join(TOOLS, "db", "chs_current")
UTC = timezone.utc
DEG = math.pi / 180
KN = 0.514444

cx = lambda z: [round(z.real, 6), round(z.imag, 6)]  # noqa: E731


def noaa_name(name):
    k = name.replace("(", "").replace(")", "").upper()
    return ALIAS.get(k, k)


def noaa_arg(key, t):
    """NOAA's argument (deg) for a constituent at UTC t, node phase included."""
    coef, const, parts = CONS[key]
    nd = noaa_nodal(t.year)
    u = sum(nd[b][1] * p for b, p in parts)
    s, h, p, _, p1 = longitudes(t)
    T = 15.0 * (t.hour + t.minute / 60 + t.second / 3600) + 180.0
    cT, cs, ch, cp, cp1 = coef
    return cT * T + cs * s + ch * h + cp * p + cp1 * p1 + const + u


def bin_z(b):
    """A NOAA-form bin's constituents as {name: complex amplitude}."""
    return {noaa_name(c[0]): c[1] * cmath.exp(-1j * c[2] * DEG) for c in b["cons"]}


class NoaaHarmonic:
    """NOAA's harmonic current stations, every bin with constants, from the cache `stations fetch` keeps.
    Its subordinate and weak stations carry no constants and are listed as others. The bins of a
    station with three or more of them, over a known seabed, give the regional vertical profile."""
    kind = "noaa"

    def gather(self, inbox, fit_year):
        if not os.path.exists(os.path.join(NOAA_DB, "stations.json")):
            sys.exit("NOAA's current station list is not cached. Cache the region's stations with "
                     "`python3 tools/blend_model.py stations fetch --near <lat> <lon> --km <r>`, then build again.")
        with open(os.path.join(NOAA_DB, "stations.json")) as f:
            lst = json.load(f)["stations"]
        missing = [sid for sid, s in lst.items() if inbox(s["lat"], s["lon"])
                   and not os.path.exists(os.path.join(NOAA_DB, f"{sid}.json"))]
        if missing:
            sys.exit(f"{len(missing)} NOAA stations in the box are not cached ({', '.join(missing[:8])}...). "
                     f"Cache them with `python3 tools/blend_model.py stations fetch --near <lat> <lon> --km <r>`, then build again.")
        sources, others = [], []
        for sid, s in sorted(lst.items()):
            if not inbox(s["lat"], s["lon"]):
                continue
            with open(os.path.join(NOAA_DB, f"{sid}.json")) as f:
                doc = json.load(f)
            bins = [b for b in doc["bins"].values() if b.get("cons")]
            if bins:
                sources.append({"id": sid, "kind": self.kind, "name": doc["name"], "lat": doc["lat"], "lon": doc["lon"],
                                "_bins": bins, "flood": bins[0]["azimuth"]})
            else:
                kinds = {b.get("type") for b in doc["bins"].values()}
                others.append({"id": sid, "kind": "noaa subordinate" if "S" in kinds else "noaa weak",
                               "name": doc["name"], "lat": doc["lat"], "lon": doc["lon"]})
        return sources, others

    def prepare(self, s, H, Hdem, fit_year, log):
        """Sets s["bins"]; returns the station's vertical profile rows. H is the seabed the bins
        are placed on (the bathymetry's, else the mesh's), Hdem the bathymetry's alone."""
        bins = s["_bins"]
        s["bins"] = [[round(min(max((H - b["depth"]) / H, 0.02), 0.98), 3) if H and b.get("depth") is not None else 0.5,
                      b.get("mean_major") or 0.0, b["azimuth"], {c: cx(z) for c, z in bin_z(b).items()}]
                     for b in bins]
        rows = []
        deep = sorted((b for b in bins if b.get("depth") is not None), key=lambda b: b["depth"])
        if len(deep) >= 3 and Hdem and deep[-1]["depth"] <= Hdem + 3:
            cm = {c: sum(bin_z(b)[c] for b in deep) / len(deep) for c in ("M2", "K1")}
            for b in deep:
                Z = bin_z(b)
                rows.append({"id": s["id"], "frac": round((Hdem - b["depth"]) / Hdem, 4),
                             "m2r": abs(Z["M2"]) / abs(cm["M2"]),
                             "m2p": -math.degrees(cmath.phase(Z["M2"] / cm["M2"])) / 28.984 * 60,
                             "k1r": abs(Z["K1"]) / abs(cm["K1"]),
                             "k1p": -math.degrees(cmath.phase(Z["K1"] / cm["K1"])) / 15.041 * 60})
        return rows


CHS_NAMES = ["M2", "S2", "N2", "K2", "K1", "O1", "P1", "Q1", "2N2", "NU2", "MU2", "L2", "T2", "J1", "M1",
             "OO1", "2Q1", "RHO", "M4", "MS4", "MN4", "S4", "M6", "2MK3", "MK3", "M3", "M8", "LAM2",
             "SSA", "SA"]


class ChsPredictions:
    """CHS's current stations, from `chs_current`'s cache. CHS publishes predictions without
    constants, so each station's constants are fitted to a year of its predictions, and its one
    series is taken as a bin at mid-depth."""
    kind = "chs"

    def gather(self, inbox, fit_year):
        sources = []
        for fn in sorted(os.listdir(CHS_DB)) if os.path.isdir(CHS_DB) else []:
            if len(fn) == 10 and fn.endswith(".json"):
                with open(os.path.join(CHS_DB, fn)) as f:
                    d = json.load(f)
                if inbox(float(d["lat"]), float(d["lon"])):
                    sources.append({"id": "CHS" + d["code"], "kind": self.kind, "name": d["name"], "lat": float(d["lat"]),
                                    "lon": float(d["lon"]), "code": d["code"], "flood": float(d["flood"])})
        return sources, []

    def prepare(self, s, H, Hdem, fit_year, log):
        log(f"  fitting constants to CHS {s['code']} {s['name']}, {fit_year}...")
        mean, cons = harmonic_fit(chs_signed(s["code"], fit_year), CHS_NAMES)
        full = {k: A * cmath.exp(-1j * g * DEG) for k, (A, g) in cons.items()}
        s["cons"] = [[k, round(A, 4), round(g, 3), 0.0, 0.0] for k, (A, g) in cons.items()]
        s["mean_major"] = round(mean * 100, 3)
        s["bins"] = [[0.5, round(mean * 100, 3), s["flood"], {c: cx(z) for c, z in full.items()}]]
        return []


NETWORKS = (NoaaHarmonic, ChsPredictions)


def chs_signed(code, year):
    """A CHS station's speed series for one UTC year, every hour, signed flood positive by the
    flood or ebb event between the slacks around it."""
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
            V = noaa_arg(k, t) * DEG
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

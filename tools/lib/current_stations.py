"""Current station networks as the Blend Model reads them: each network gathers its stations in a
box, downloading through its own tool whatever is not yet on this machine, turns each one into
bins, the form every correction is made from, and checks a station's cached data against the
network's live service. A bin is [fraction of the depth above the seabed, steady current cm/s,
flood azimuth, {constituent: [re, im]}], the constituent a complex amplitude Z = A e^(-ig) in cm/s
in NOAA's convention, along the flood. A new network joins by adding a class to NETWORKS with
`kind`, `gather(inbox, fit_year)`, `prepare(station, H, Hdem, fit_year, log)`, `owns(id)` and
`verify(id)`, which returns (passed, report lines)."""
import cmath
import math
import sys
import time as _time
from datetime import date, datetime, timedelta, timezone

from lib.tidal_astronomy import ALIAS, CONS, longitudes
from lib import noaa_stations
from lib.tidal_astronomy import nodal as noaa_nodal

VERIFY_DAYS = 30  # days a station is compared with its network's live service, from today
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
    """NOAA's harmonic current stations, every bin with constants, from `noaa_stations`' cache, each
    station downloaded on first use. Its subordinate and weak stations carry no constants and are
    listed as others. The bins of a station with three or more of them, over a known seabed, give
    the regional vertical profile."""
    kind = "noaa"

    def gather(self, inbox, fit_year):
        lst = noaa_stations.station_list()["stations"]
        ids = [sid for sid, s in sorted(lst.items()) if inbox(s["lat"], s["lon"])]
        todo = [sid for sid in ids if not noaa_stations.cached(sid)]
        if todo:
            print(f"downloading {len(todo)} NOAA current stations in the box ...", file=sys.stderr, flush=True)
        sources, others = [], []
        for sid in ids:
            was = noaa_stations.cached(sid)
            doc = noaa_stations.station(sid, quiet=True)
            if not was:
                _time.sleep(noaa_stations.FETCH_PAUSE)
            bins = [b for b in doc["bins"].values() if b.get("cons")]
            if bins:
                sources.append({"id": sid, "kind": self.kind, "name": doc["name"], "lat": doc["lat"], "lon": doc["lon"],
                                "_bins": bins, "flood": bins[0]["azimuth"]})
            else:
                kinds = {b.get("type") for b in doc["bins"].values()}
                others.append({"id": sid, "kind": "noaa subordinate" if "S" in kinds else "noaa weak",
                               "name": doc["name"], "lat": doc["lat"], "lon": doc["lon"]})
        return sources, others

    def owns(self, sid):
        return sid in noaa_stations.station_list()["stations"]

    def verify(self, sid):
        """Every published harmonic bin against NOAA's live predictions."""
        doc = noaa_stations.station(sid)
        day, ok = date.today(), True
        lines = [f"{doc['id']}  {doc['name']}  NOAA, {day} for {VERIFY_DAYS} days, constants fetched {doc['fetched']}"]
        bins = noaa_stations.harmonic_bins(doc)
        if not bins:
            lines.append("  no bin NOAA publishes predictions for, so nothing to compare with: its constants "
                         "stand unchecked")
        for num, b in bins:
            r = noaa_stations.compare(doc, num, b, day, VERIFY_DAYS)
            lines.append(f"  bin {num}" + (f", {b['depth']} m" if b.get("depth") is not None else "")
                         + ("  PASS" if r["ok"] else "  FAIL"))
            lines += ["  " + x for x in noaa_stations.report_lines(r)]
            ok &= r["ok"]
        if not ok:
            lines.append(f"  limits are {noaa_stations.SPEED_TOL} m/s and {noaa_stations.TIME_TOL:g} min: NOAA has "
                         f"replaced the constants. Delete tools/db/noaa_current/{sid}.json, rebuild, and verify again.")
        return ok, lines

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
    """CHS's current stations, from `chs_current`'s cache, each station and year downloaded on
    first use. CHS publishes predictions without constants, so each station's constants are fitted
    to a year of its predictions, and its one series is taken as a bin at mid-depth."""
    kind = "chs"

    def gather(self, inbox, fit_year):
        import chs_current
        sources = []
        for code, e in sorted(chs_current.station_list()["stations"].items()):
            if inbox(float(e["lat"]), float(e["lon"])):
                d = chs_current.station(code)
                sources.append({"id": "CHS" + d["code"], "kind": self.kind, "name": d["name"], "lat": float(d["lat"]),
                                "lon": float(d["lon"]), "code": d["code"], "flood": float(d["flood"])})
        return sources, []

    def owns(self, sid):
        return sid.startswith("CHS") and len(sid) == 8

    def verify(self, sid):
        """Every speed value and event of the cached predictions against CHS's live API."""
        import chs_current
        st = chs_current.station(sid[3:])
        day = date.today()
        r = chs_current.compare(st, day, VERIFY_DAYS)
        lines = [f"{sid}  {st['name']}  CHS, {day} for {VERIFY_DAYS} days" + ("  PASS" if r["ok"] else "  FAIL"),
                 f"    speed, {r['speed_n']} values: " + ("worst difference n/a" if r["speed_worst"] is None else
                 f"worst difference {r['speed_worst']:.3f} m/s") + f", {r['speed_missing']} missing",
                 f"    events, {r['events_n']} slacks and maxima: {r['events_differ']} differ"]
        if not r["ok"]:
            lines.append(f"  CHS has replaced these predictions. Delete tools/db/chs_current/{sid[3:]}*.json, "
                         "rebuild, and verify again.")
        return r["ok"], lines

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
    flood or ebb event between the slacks around it. The year is downloaded on first use."""
    import chs_current
    d = chs_current.year_file(chs_current.station(code), year)
    if d is None:
        sys.exit(f"CHS holds no {year} predictions for station {code}, so its constants cannot be fitted "
                 "to this year. Stop and report it.")
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

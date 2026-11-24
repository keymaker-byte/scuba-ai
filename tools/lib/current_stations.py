"""Current station networks as the current tool reads them: each network gathers its stations in a
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
from datetime import date, timezone

from lib.tidal_astronomy import ALIAS, CONS, longitudes
from lib import chs_stations, noaa_stations
from lib.tidal_astronomy import nodal as noaa_nodal

VERIFY_DAYS = 30  # days a station is compared with its network's live service, from today
UTC = timezone.utc
DEG = math.pi / 180

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


FIT_SLACK_MS = 0.3  # m/s: a sample's weight in the CHS fit is 1 / (|speed| + this), so slack sets the timing


class ChsPredictions:
    """CHS's current stations, from `chs_stations`' cache, each station and year downloaded on
    first use. CHS publishes predictions without constants, so each station's constants are fitted
    to a year of its own predictions (`harmonic_fit`), and its one series is taken as a bin at
    mid-depth, where CHS states no depth for it. From there a CHS station corrects the database
    exactly as a NOAA bin does."""
    kind = "chs"

    def gather(self, inbox, fit_year):
        sources = []
        for code, e in sorted(chs_stations.station_list()["stations"].items()):
            if inbox(float(e["lat"]), float(e["lon"])):
                d = chs_stations.station(code)
                sources.append({"id": "CHS" + d["code"], "kind": self.kind, "name": d["name"], "lat": float(d["lat"]),
                                "lon": float(d["lon"]), "code": d["code"], "flood": float(d["flood"])})
        return sources, []

    def owns(self, sid):
        return sid.startswith("CHS") and len(sid) == 8

    def verify(self, sid):
        """Every speed value and event of the cached predictions against CHS's live API."""
        st = chs_stations.station(sid[3:])
        day = date.today()
        r = chs_stations.compare(st, day, VERIFY_DAYS)
        lines = [f"{sid}  {st['name']}  CHS, {day} for {VERIFY_DAYS} days, predictions downloaded {st['fetched']}"
                 + ("  PASS" if r["ok"] else "  FAIL"),
                 f"    speed, {r['speed_n']} values: " + ("worst difference n/a" if r["speed_worst"] is None else
                 f"worst difference {r['speed_worst']:.3f} m/s") + f", {r['speed_missing']} missing",
                 f"    events, {r['events_n']} slacks and maxima: {r['events_differ']} differ"]
        if not r["ok"]:
            lines.append(f"  CHS has replaced these predictions. Delete tools/db/chs_current/{sid[3:]}*.json, "
                         "rebuild, and verify again.")
        return r["ok"], lines

    def prepare(self, s, H, Hdem, fit_year, log):
        log(f"  fitting constants to CHS {s['code']} {s['name']}, {fit_year}...")
        ser = chs_stations.signed(s["code"], fit_year)
        mean, cons = harmonic_fit(ser, sorted(CONS), lambda y: 1 / (abs(y) + FIT_SLACK_MS))
        full = {k: A * cmath.exp(-1j * g * DEG) for k, (A, g) in cons.items()}
        s["cons"] = [[k, round(A, 4), round(g, 3), 0.0, 0.0] for k, (A, g) in cons.items()]
        s["mean_major"] = round(mean * 100, 3)
        s["fit_samples"] = len(ser)
        s["bins"] = [[0.5, round(mean * 100, 3), s["flood"], {c: cx(z) for c, z in full.items()}]]
        return []


NETWORKS = (NoaaHarmonic, ChsPredictions)


def harmonic_fit(ser, names, weight=None):
    """Weighted least squares on a signed speed series [(UTC datetime, m/s)]: the mean (m/s) and
    {name: (A cm/s, g deg)} in NOAA's convention, node factors held at each year's middle as the
    prediction holds them. `weight(speed)` gives each sample's weight, 1 when omitted."""
    names = [n for n in names if n in CONS]
    n = 1 + 2 * len(names)
    M = [[0.0] * n for _ in range(n)]
    v = [0.0] * n
    years = {}
    for t, y in ser:
        if t.year not in years:
            nd = noaa_nodal(t.year)
            row = []
            for k in names:
                coef, const, parts = CONS[k]
                f, u = 1.0, 0.0
                for b, p in parts:
                    f *= nd[b][0] ** abs(p)
                    u += nd[b][1] * p
                row.append((coef, const + u, f))
            years[t.year] = row
        s, h, p, _, p1 = longitudes(t)
        T = 15.0 * (t.hour + t.minute / 60 + t.second / 3600) + 180.0
        r = [1.0]
        for (cT, cs, ch, cp, cp1), c0, f in years[t.year]:
            V = (cT * T + cs * s + ch * h + cp * p + cp1 * p1 + c0) * DEG
            r += [f * math.cos(V), f * math.sin(V)]
        w = weight(y) if weight else 1.0
        for i in range(n):
            ri = r[i] * w
            v[i] += ri * y
            M[i] = [a + ri * b for a, b in zip(M[i], r)]
    A = [row + [v[i]] for i, row in enumerate(M)]
    for i in range(n):
        piv = max(range(i, n), key=lambda k: abs(A[k][i]))
        A[i], A[piv] = A[piv], A[i]
        for k in range(n):
            if k != i and A[k][i]:
                f = A[k][i] / A[i][i]
                A[k] = [a - f * b for a, b in zip(A[k], A[i])]
    x = [A[i][n] / A[i][i] for i in range(n)]
    return x[0], {k: (100 * math.hypot(x[1 + 2 * i], x[2 + 2 * i]),
                      math.degrees(math.atan2(x[2 + 2 * i], x[1 + 2 * i])) % 360) for i, k in enumerate(names)}

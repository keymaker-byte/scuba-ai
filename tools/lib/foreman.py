"""Foreman's tidal method, as the Canadian Hydrographic Service predicts with it: M. G. G. Foreman's
constituent table from the Institute of Ocean Sciences (its 146 constituents with their Doodson
numbers, the 162 satellites behind the node factors with their latitude factors, and the 101
shallow water compounds), the astronomical arguments, node factors worked out from the satellites
and updated as time runs, the Rayleigh choice of constituents for a record's length, the least
squares fit of constants to a height series, the shallow water compounds a station's own series
calls for beyond the standard set, and the height at any moment from them. Ported from
R. Pawlowicz's t_tide (t_getconsts, t_vuf, t_astron), which reads the same table.

Foreman's table, `tide3.dat`, comes inside t_tide's distribution and is downloaded from it the
first time it is needed, into tools/db/tide/foreman/. Standard library only.

A set of constants is {"method": "foreman", "lat": station latitude, "z0": mean water level above
the datum, m, "cons": {name: [a, b]}}: the height is z0 plus, for each constituent, its node factor
times (a cos 2pi(v + u) + b sin 2pi(v + u)), v its astronomical argument and u its node phase."""
import io
import math
import os
import re
import sys
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timedelta, timezone

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(TOOLS, "db", "tide", "foreman")
TABLE = os.path.join(DB, "tide3.dat")
URL = "https://www.eoas.ubc.ca/~rich/t_tide/t_tide_v1.5beta.zip"
UTC = timezone.utc
TWO_PI = 2 * math.pi
NUM = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)")
EPOCH = datetime(1899, 12, 31, 12, tzinfo=UTC)
SHAPE = (146, 162, 101)  # constituents, satellites, shallow water compounds in Foreman's table


def _download():
    print(f"downloading Foreman's constituent table from {URL} ...", file=sys.stderr, flush=True)
    try:
        with urllib.request.urlopen(URL, timeout=120) as r:
            body = r.read()
        with zipfile.ZipFile(io.BytesIO(body)) as z:
            data = z.read("tide3.dat")
    except (urllib.error.URLError, TimeoutError, OSError, zipfile.BadZipFile, KeyError) as e:
        sys.exit(f"Foreman: the constituent table could not be downloaded ({e}). Nothing was cached.\n  {URL}")
    os.makedirs(DB, exist_ok=True)
    with open(TABLE + ".part", "wb") as f:
        f.write(data)
    os.replace(TABLE + ".part", TABLE)


def _parse(text):
    """Foreman's table as t_tide's t_getconsts reads it: {name: {freq, kmpr, dood, semi, sats,
    shallow}}, in the table's order."""
    lines = text.split("\n")
    const, i = {}, 0
    while len(lines[i]) > 24:
        ln = lines[i]
        const[ln[4:8].strip()] = {"freq": float(ln[13:25]), "kmpr": (ln[29:] + "    ")[:4].strip(), "dood": None,
                                  "semi": 0.0, "sats": [], "shallow": None}
        i += 1
    i += 3
    while len(lines[i]) > 10:
        ln = lines[i]
        c = const[ln[6:10].strip()]
        nums = [float(x) for x in NUM.findall(ln[10:])[:8]]
        c["dood"], c["semi"], m = nums[:6], nums[6], int(nums[7])
        while m > 0:
            i += 1
            ln = lines[i] + " 0"
            for n in range(1, min(m, 3) + 1):
                f = [float(x) for x in NUM.findall(ln[n * 23 - 12:n * 23 + 8])]
                flag = ln[n * 23 + 9] if len(ln) > n * 23 + 9 else " "
                c["sats"].append((f[0], f[1], f[2], f[3], f[4], int(flag) if flag.strip() else 0))
                m -= 1
        i += 1
    i += 1
    names = list(const)
    while len(lines[i]) > 3:
        ln = lines[i]
        parts = []
        for m in range(1, int(ln[10:12]) + 1):
            short = ln[m * 15 + 4:m * 15 + 6].strip()
            parts.append((float(ln[m * 15 - 1:m * 15 + 3]), next(n for n in names if n.startswith(short))))
        const[ln[6:10].strip()]["shallow"] = parts
        i += 1
    return const


_TABLE = []


def table():
    """Foreman's constituents, read from this machine and downloaded when missing."""
    if not _TABLE:
        if not os.path.exists(TABLE):
            _download()
        with open(TABLE) as f:
            const = _parse(f.read())
        shape = (len(const), sum(len(c["sats"]) for c in const.values()), sum(1 for c in const.values() if c["shallow"]))
        if shape != SHAPE:
            sys.exit(f"Foreman: {TABLE} reads as {shape} constituents, satellites and compounds, where the table "
                     f"holds {SHAPE}. Delete it to download it again, and report it if it persists.")
        _TABLE.append(const)
    return _TABLE[0]


def astro(t):
    """[tau, s, h, p, N', p'] at UTC datetime t, in cycles (t_astron)."""
    d = (t - EPOCH).total_seconds() / 86400.0
    D = d / 10000.0
    args = (1.0, d, D * D, D ** 3)
    rows = ((270.434164, 13.1763965268, -0.0000850, 0.000000039),
            (279.696678, 0.9856473354, 0.00002267, 0.0),
            (334.329556, 0.1114040803, -0.0007739, -0.00000026),
            (-259.183275, 0.0529539222, -0.0001557, -0.000000050),
            (281.220844, 0.0000470684, 0.0000339, 0.000000070))
    a = [math.fmod(sum(c * x for c, x in zip(r, args)) / 360.0, 1.0) for r in rows]
    return [(d + 0.5) % 1.0 + a[1] - a[0]] + a


def select(hours):
    """The constituents a record of this many hours resolves, by the Rayleigh criterion against
    each one's neighbour in Foreman's table, as t_tide chooses them: 68 for two years."""
    const = table()
    return [n for n, c in const.items()
            if n != "Z0" and c["kmpr"] and abs(const[c["kmpr"]]["freq"] - c["freq"]) >= 1.0 / hours]


class Nodal:
    """Node factors and phases for a station's latitude, worked out from Foreman's satellites once
    per UTC day: they move by less than a hundredth of a degree a day, so a day's value is the
    continuous one to well under a millimetre."""

    def __init__(self, lat, names):
        self.names = list(names)
        lat = lat if abs(lat) >= 5 else math.copysign(5, lat)
        sl = math.sin(math.radians(lat))
        self.r = {0: 1.0, 1: 0.36309 * (1.0 - 5.0 * sl * sl) / sl, 2: 2.59808 * sl}
        self.const = table()
        self._day = {}

    def _main(self, n, A, memo):
        if n not in memo:
            fs = complex(1.0, 0.0)
            for d1, d2, d3, ph, amp, lf in self.const[n]["sats"]:
                uu = TWO_PI * (d1 * A[3] + d2 * A[4] + d3 * A[5] + ph)
                fs += amp * self.r[lf] * complex(math.cos(uu), math.sin(uu))
            memo[n] = (math.atan2(fs.imag, fs.real) / TWO_PI, abs(fs))
        return memo[n]

    def uf(self, t):
        """[(u cycles, f)] for each constituent on t's UTC day."""
        day = t.date()
        if day not in self._day:
            A = astro(datetime(day.year, day.month, day.day, 12, tzinfo=UTC))
            memo, out = {}, []
            for n in self.names:
                sh = self.const[n]["shallow"]
                if sh:
                    u, f = 0.0, 1.0
                    for k, m in sh:
                        um, fm = self._main(m, A, memo)
                        u += k * um
                        f *= fm ** abs(k)
                    out.append((u, f))
                else:
                    out.append(self._main(n, A, memo))
            if len(self._day) > 4000:
                self._day.clear()
            self._day[day] = out
        return self._day[day]

    def phases(self, t):
        """[(v + u in cycles, f)] for each constituent at t."""
        A = astro(t)
        out = []
        for n, (u, f) in zip(self.names, self.uf(t)):
            c = self.const[n]
            if c["shallow"]:
                v = 0.0
                for k, m in c["shallow"]:
                    mc = self.const[m]
                    v += k * (sum(a * b for a, b in zip(mc["dood"], A)) + mc["semi"])
            else:
                v = sum(a * b for a, b in zip(c["dood"], A)) + c["semi"]
            out.append((v + u, f))
        return out


def fit(series, lat, hours, names=None):
    """Constants fitted by least squares to a height series [(UTC datetime, metres)] spanning
    `hours`, with the constituents named, or else the ones that span resolves."""
    names = list(names or select(hours))
    nodal = Nodal(lat, names)
    n = 1 + 2 * len(names)
    M = [[0.0] * n for _ in range(n)]
    v = [0.0] * n
    for t, h in series:
        r = [1.0]
        for ph, f in nodal.phases(t):
            r += [f * math.cos(TWO_PI * ph), f * math.sin(TWO_PI * ph)]
        for i in range(n):
            ri = r[i]
            M[i] = [a + ri * b for a, b in zip(M[i], r)]
            v[i] += ri * h
    A = [row + [v[i]] for i, row in enumerate(M)]
    for i in range(n):
        piv = max(range(i, n), key=lambda k: abs(A[k][i]))
        A[i], A[piv] = A[piv], A[i]
        for k in range(n):
            if k != i and A[k][i]:
                fct = A[k][i] / A[i][i]
                A[k] = [a - fct * b for a, b in zip(A[k], A[i])]
    x = [A[i][n] / A[i][i] for i in range(n)]
    return {"method": "foreman", "lat": lat, "z0": x[0],
            "cons": {nm: [x[1 + 2 * i], x[2 + 2 * i]] for i, nm in enumerate(names)}}


LEFTOVER = 0.0005  # m: a shallow water compound standing this high in a fit's leftover joins the fit
ROUNDS = 3


def leftover(h, series):
    """[(amplitude m, name)] of every shallow water compound in Foreman's table outside the
    constants, read from what they leave unexplained in a height series, largest first."""
    res = [(t, v - height(h, t)) for t, v in series]
    t0 = res[0][0]
    hrs = [((t - t0).total_seconds() / 3600, r) for t, r in res]
    out = []
    for n, c in table().items():
        if not c["shallow"] or n in h["cons"]:
            continue
        w = TWO_PI * c["freq"]
        sc = sum(r * math.cos(w * x) for x, r in hrs)
        ss = sum(r * math.sin(w * x) for x, r in hrs)
        out.append((2 * math.hypot(sc, ss) / len(hrs), n))
    return sorted(out, reverse=True)


def fit_station(series, lat, hours, probe):
    """Constants for a station: Foreman's standard constituents the span resolves, joined by the
    shallow water compounds its leftover shows, as many as stand LEFTOVER high, in up to ROUNDS
    rounds. `series` is fitted; `probe`, the same years sampled at least hourly so the compounds
    of a few hours' period stay distinct, is where the leftover is read."""
    names = select(hours)
    h = fit(series, lat, hours, names)
    for _ in range(ROUNDS):
        more = [n for a, n in leftover(h, probe) if a >= LEFTOVER]
        if not more:
            break
        names += more
        h = fit(series, lat, hours, names)
    return h


_NODAL = {}


def height(h, t):
    """Height from a set of constants at UTC datetime t, metres above the station's datum."""
    key = id(h)
    if key not in _NODAL or _NODAL[key][0] is not h:
        _NODAL[key] = (h, Nodal(h["lat"], list(h["cons"])))
    z = h["z0"]
    for (ph, f), (a, b) in zip(_NODAL[key][1].phases(t), h["cons"].values()):
        z += f * (a * math.cos(TWO_PI * ph) + b * math.sin(TWO_PI * ph))
    return z

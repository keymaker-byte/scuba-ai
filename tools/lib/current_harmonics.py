"""Harmonic current prediction shared by current.py and lib/noaa_stations.py: a bin's
constants prepared for a year, its signed speed along the major axis at any moment, and the
slacks and maxima of a speed series."""
import math
import sys
from datetime import timedelta

from lib.tidal_astronomy import ALIAS, CONS, longitudes, nodal


def prepare(cons, year):
    """Constants ready to sum for one year: per constituent, the argument coefficients, and
    the node factor and phase of that year."""
    nd = nodal(year)
    out = []
    for name, amaj, gmaj, amin, gmin in cons:
        key = ALIAS.get(name.upper(), name.upper())
        if key not in CONS:
            sys.exit(f"constituent {name} is not one this tool can predict; the station's constants "
                     "changed shape. Report it rather than predicting without it.")
        coef, const, parts = CONS[key]
        f, u = 1.0, 0.0
        for base, power in parts:
            f *= nd[base][0] ** abs(power)
            u += nd[base][1] * power
        out.append((coef, const + u, f * amaj, gmaj, f * amin, gmin))
    return out


_PREP = {}


def speed(b, t):
    """Signed speed along the bin's major axis at UTC datetime t, m/s, flood positive: the
    bin's mean current plus the sum of its constituents."""
    key = (id(b), t.year)
    if key not in _PREP:  # the entry holds b itself, so its id stays this bin's for the whole run
        _PREP[key] = (b, prepare(b["cons"], t.year))
    s, h, p, _, p1 = longitudes(t)
    T = 15.0 * (t.hour + t.minute / 60 + t.second / 3600 + t.microsecond / 3.6e9) + 180.0
    major = b.get("mean_major") or 0.0
    for (cT, cs, ch, cp, cp1), const, amaj, gmaj, _, _ in _PREP[key][1]:
        major += amaj * math.cos(math.radians(cT * T + cs * s + ch * h + cp * p + cp1 * p1 + const - gmaj))
    return major / 100.0


def series(b, start, minutes, step=1):
    """[(utc datetime, speed)] every `step` minutes from `start`."""
    return [(start + timedelta(minutes=m), speed(b, start + timedelta(minutes=m)))
            for m in range(0, minutes + 1, step)]


def events(ser):
    """Slacks, and the maximum flood and ebb between them: [(utc datetime, kind, speed)]."""
    out = []
    for k in range(1, len(ser)):
        (t0, v0), (t1, v1) = ser[k - 1], ser[k]
        if (v0 < 0) != (v1 < 0):
            out.append((t0 + (t1 - t0) * (v0 / (v0 - v1)), "slack", 0.0))
        if k + 1 < len(ser):
            v2 = ser[k + 1][1]
            if (v1 - v0) * (v2 - v1) < 0 or (v1 == v2 and v1 != v0):
                den = v0 - 2 * v1 + v2
                x = 0.5 * (v0 - v2) / den if den else 0.0
                peak = v1 - 0.25 * (v0 - v2) * x
                top = v1 > v0
                kind = ("flood" if top else "min flood") if peak > 0 else ("min ebb" if top else "ebb")
                out.append((t1 + (ser[k + 1][0] - t1) * x, kind, peak))
    return out

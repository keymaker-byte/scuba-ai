"""Harmonic tide prediction, independent of any station network: a constituent named by any
network worked out to its arguments and nodal parts, a station's constants prepared for a year,
the height at a moment as a mean level above the station's datum plus the sum of its
constituents, and the highs and lows of any height curve. Shared by every source in
`lib/tide.py` and by map_export.py's tide station layer, so the map and the tool sum the same
terms. The astronomy is `lib/tidal_astronomy.py`.

A set of constants is {"key": a name unique to the station, "cons": [[name, amplitude m, phase
deg (Greenwich), speed deg/h], ...], "z0": mean sea level above the station's datum, m}."""
import itertools
import math
import sys
from datetime import timedelta

import lib.tidal_astronomy as astro

# Degrees per hour of T, s, h, p, p1: what a constituent's argument coefficients add up to.
RATE = (15.0, 0.54901653, 0.04106864, 0.00464183, 0.00000196)


# Constituents beyond lib/tidal_astronomy.py's 37: (T, s, h, p, p1) coefficients, constant, nodal parts.
EXTRA = {
    "SIGMA1": ((1, -4, 3, 0, 0), 90, [("O1", 2)]),
    # NOAA's names for pi1, psi1 and phi1, each with no nodal part.
    "TK1": ((1, 0, -2, 0, 1), 90, []),
    "RP1": ((1, 0, 2, 0, -1), -90, []),
    "KP1": ((1, 0, 3, 0, 0), -90, []),
    "CHI1": ((1, -1, 3, -1, 0), -90, [("J1", 1)]),
    "THETA1": ((1, 1, -1, 1, 0), -90, [("J1", 1)]),
}


# A compound's letters, each one of these constituents; K is K1 or K2, whichever fits.
LETTER = {"M": ["M2"], "S": ["S2"], "N": ["N2"], "L": ["L2"], "O": ["O1"], "P": ["P1"], "Q": ["Q1"],
          "J": ["J1"], "T": ["T2"], "R": ["R2"], "K": ["K1", "K2"]}


# Compounds whose name alone does not spell their parts.
NAMED = {"OO2": {"O1": 1, "Q1": 1}, "3KM5": {"K2": 1, "K1": 1, "M2": 1}}


def _base(name):
    key = astro.ALIAS.get(name.upper(), name.upper())
    return astro.CONS.get(key) or EXTRA.get(key)


def _rate(coef):
    return sum(c * r for c, r in zip(coef, RATE))


def _combine(parts):
    """A compound constituent from {base: count}: arguments, constants and nodal parts add."""
    coef, const, nodal = [0] * 5, 0, []
    for name, n in parts.items():
        c, k, nd = _base(name)
        coef = [a + n * b for a, b in zip(coef, c)]
        const += n * k
        nodal += [(b, p * n) for b, p in nd]
    return tuple(coef), const, nodal


_SOLVED = {}


def constituent(name, speed):
    """(coefficients, constant, nodal parts) for a constituent a network names, checked against
    the speed it publishes for it. A compound tide is worked out from its name: 2MK5 is twice
    M2 plus K1, MSN2 is M2 plus S2 less N2, the signs being the ones that give its speed."""
    key = name.upper()
    if key in _SOLVED:
        return _SOLVED[key]
    found = _base(key)
    if found is None and key in NAMED:
        found = _combine(NAMED[key])
    if found is None:
        found = _spell(key, speed)
    if found is None or abs(_rate(found[0]) - speed) > 2e-4:
        sys.exit(f"constituent {name} ({speed}°/h) is not one this tool can predict. Report it rather "
                 "than predicting without it.")
    _SOLVED[key] = found
    return found


def _spell(key, speed):
    body = key.rstrip("0123456789")
    if not body or any(not (ch.isdigit() or ch in LETTER) for ch in body) or body[-1].isdigit():
        return None
    if len(body) == 1:  # N4 is twice N2, M10 five times M2
        for base in LETTER[body]:
            for n in range(1, 8):
                combo = _combine({base: n})
                if abs(_rate(combo[0]) - speed) <= 2e-4:
                    return combo
        return None
    # A count belongs to the letter after it (2MS6 is 2M + S); failing that, to every letter up
    # to the next count (2MS8 is 2M + 2S, M2KS2 is M + 2K - 2S).
    for carry in (False, True):
        letters, count = [], 1
        for k, ch in enumerate(body):
            if ch.isdigit():
                continue
            if k and body[k - 1].isdigit():
                d = k - 1
                while d and body[d - 1].isdigit():
                    d -= 1
                count = int(body[d:k])
            elif not carry:
                count = 1
            letters.append((ch, count))
        for choice in itertools.product(*(LETTER[ch] for ch, _ in letters)):
            for signs in itertools.product((1, -1), repeat=len(letters)):
                parts = {}
                for base, (_, n), sg in zip(choice, letters, signs):
                    parts[base] = parts.get(base, 0) + sg * n
                combo = _combine(parts)
                if abs(_rate(combo[0]) - speed) <= 2e-4:
                    return combo
    return None


def prepare(cons, year):
    """A station's constituents for one UTC year: [(coefficients, argument constant with the
    node phase less the Greenwich phase, amplitude with the node factor)], node factors held at
    mid-year as NOAA holds them."""
    nd = astro.nodal(year)
    out = []
    for name, amp, phase, speed in cons:
        if not amp:
            continue
        coef, const, parts = constituent(name, speed)
        f, u = 1.0, 0.0
        for base, power in parts:
            f *= nd[base][0] ** abs(power)
            u += nd[base][1] * power
        out.append((coef, const + u - phase, f * amp))
    return out


_PREP = {}


def height(h, t):
    """Tide height from a set of constants at UTC datetime t, metres above the station's datum:
    its mean sea level above the datum plus the sum of the constituents."""
    key = (h["key"], t.year)
    if key not in _PREP:
        _PREP[key] = prepare(h["cons"], t.year)
    s, hh, p, _, p1 = astro.longitudes(t)
    T = 15.0 * (t.hour + t.minute / 60 + t.second / 3600 + t.microsecond / 3.6e9) + 180.0
    z = h["z0"]
    rad = math.radians
    for (cT, cs, ch, cp, cp1), const, amp in _PREP[key]:
        z += amp * math.cos(rad(cT * T + cs * s + ch * hh + cp * p + cp1 * p1 + const))
    return z


def extremes(fn, start, end, step=6):
    """The highs and lows of a height curve fn(utc datetime) from `start` to `end` (UTC datetimes,
    both included in the search): [(utc datetime, "H" or "L", metres)], each placed by a parabola
    through the three samples around it, `step` minutes apart, and its height read at that time."""
    n = int((end - start).total_seconds() // 60 // step) + 1
    ts = [start + timedelta(minutes=k * step) for k in range(n)]
    vs = [fn(t) for t in ts]
    out = []
    for k in range(1, n - 1):
        v0, v1, v2 = vs[k - 1], vs[k], vs[k + 1]
        if (v1 - v0) * (v2 - v1) < 0 or (v1 == v2 and v1 != v0):
            den = v0 - 2 * v1 + v2
            x = 0.5 * (v0 - v2) / den if den else 0.0
            t = ts[k] + timedelta(minutes=step * x)
            out.append((t, "H" if v1 > v0 else "L", fn(t)))
    return out

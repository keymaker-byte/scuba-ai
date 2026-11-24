"""Tidal astronomy shared by the current prediction, the current tool and noaa_tide.py: the constituent table, the mean
longitudes of the moon and sun, and the yearly node factors, after Schureman's Manual of
Harmonic Analysis and Prediction of Tides (1958) with NOAA's own conventions."""
import math
from datetime import datetime, timezone

# name -> ((T, s, h, p, p1) coefficients, constant in degrees, [(nodal base, power)])
CONS = {
    "M2": ((2, -2, 2, 0, 0), 0, [("M2", 1)]),
    "S2": ((2, 0, 0, 0, 0), 0, []),
    "N2": ((2, -3, 2, 1, 0), 0, [("M2", 1)]),
    "K1": ((1, 0, 1, 0, 0), -90, [("K1", 1)]),
    "M4": ((4, -4, 4, 0, 0), 0, [("M2", 2)]),
    "O1": ((1, -2, 1, 0, 0), 90, [("O1", 1)]),
    "M6": ((6, -6, 6, 0, 0), 0, [("M2", 3)]),
    "MK3": ((3, -2, 3, 0, 0), -90, [("M2", 1), ("K1", 1)]),
    "S4": ((4, 0, 0, 0, 0), 0, []),
    "MN4": ((4, -5, 4, 1, 0), 0, [("M2", 2)]),
    "NU2": ((2, -3, 4, -1, 0), 0, [("M2", 1)]),
    "S6": ((6, 0, 0, 0, 0), 0, []),
    "MU2": ((2, -4, 4, 0, 0), 0, [("M2", 1)]),
    "2N2": ((2, -4, 2, 2, 0), 0, [("M2", 1)]),
    "OO1": ((1, 2, 1, 0, 0), -90, [("OO1", 1)]),
    "LAM2": ((2, -1, 0, 1, 0), 180, [("M2", 1)]),
    "S1": ((1, 0, 0, 0, 0), 0, []),
    "M1": ((1, -1, 1, 1, 0), -90, [("M1", 1)]),
    "J1": ((1, 1, 1, -1, 0), -90, [("J1", 1)]),
    "MM": ((0, 1, 0, -1, 0), 0, [("MM", 1)]),
    "SSA": ((0, 0, 2, 0, 0), 0, []),
    "SA": ((0, 0, 1, 0, 0), 0, []),
    "MSF": ((0, 2, -2, 0, 0), 0, [("M2", -1)]),
    "MF": ((0, 2, 0, 0, 0), 0, [("MF", 1)]),
    "RHO": ((1, -3, 3, -1, 0), 90, [("O1", 1)]),
    "Q1": ((1, -3, 1, 1, 0), 90, [("O1", 1)]),
    "T2": ((2, 0, -1, 0, 1), 0, []),
    "R2": ((2, 0, 1, 0, -1), 180, []),
    "2Q1": ((1, -4, 1, 2, 0), 90, [("O1", 1)]),
    "P1": ((1, 0, -1, 0, 0), 90, []),
    "2SM2": ((2, 2, -2, 0, 0), 0, [("M2", -1)]),
    "M3": ((3, -3, 3, 0, 0), 0, [("M2", 1.5)]),
    "L2": ((2, -1, 2, -1, 0), 180, [("L2", 1)]),
    "2MK3": ((3, -4, 3, 0, 0), 90, [("M2", 2), ("K1", -1)]),
    "K2": ((2, 0, 2, 0, 0), 0, [("K2", 1)]),
    "M8": ((8, -8, 8, 0, 0), 0, [("M2", 4)]),
    "MS4": ((4, -2, 2, 0, 0), 0, [("M2", 1)]),
}
ALIAS = {"RHO1": "RHO", "LAMBDA2": "LAM2", "LDA2": "LAM2"}
EPOCH = datetime(1899, 12, 31, 12, tzinfo=timezone.utc)


def longitudes(t):
    """Mean longitudes at UTC datetime t, degrees: moon s, sun h, lunar perigee p, lunar
    node N, solar perigee p1."""
    T = (t - EPOCH).total_seconds() / 86400 / 36525
    return (270.434164 + 481267.8831417 * T - 0.0011333 * T * T,
            279.696678 + 36000.768925 * T + 0.0003025 * T * T,
            334.329556 + 4069.0340333 * T - 0.010325 * T * T,
            259.183275 - 1934.1420083 * T + 0.0020778 * T * T,
            281.220833 + 1.719175 * T + 0.0004528 * T * T)


def nodal(year):
    """Node factor f and phase u (degrees) for each nodal base, held at the middle of the
    year as NOAA's predictions hold them."""
    jan1 = datetime(year, 1, 1, tzinfo=timezone.utc)
    _, _, p, N, _ = longitudes(jan1 + (datetime(year + 1, 1, 1, tzinfo=timezone.utc) - jan1) / 2)
    p_jan1 = longitudes(jan1)[2]
    r, d = math.radians, math.degrees
    N = r((N + 180) % 360 - 180)
    w, i = r(23.452), r(5.145)
    I = math.acos(math.cos(i) * math.cos(w) - math.sin(i) * math.sin(w) * math.cos(N))
    a = math.atan(math.cos((w - i) / 2) / math.cos((w + i) / 2) * math.tan(N / 2))
    b = math.atan(math.sin((w - i) / 2) / math.sin((w + i) / 2) * math.tan(N / 2))
    xi, nu = N - (a + b), a - b
    si, s2i = math.sin(I), math.sin(2 * I)
    nup = math.atan2(s2i * math.sin(nu), s2i * math.cos(nu) + 0.3347)
    nupp2 = math.atan2(si * si * math.sin(2 * nu), si * si * math.cos(2 * nu) + 0.0727)
    P = r(p) - xi
    f_m2 = math.cos(I / 2) ** 4 / 0.9154
    f_o1 = si * math.cos(I / 2) ** 2 / 0.3800
    t2 = math.tan(I / 2) ** 2
    Q = math.atan2((5 * math.cos(I) - 1) * math.sin(P), (7 * math.cos(I) + 1) * math.cos(P))
    R = math.atan2(math.sin(2 * P), 1 / (6 * t2) - math.cos(2 * P))
    return {
        "M2": (f_m2, d(2 * xi - 2 * nu)),
        "O1": (f_o1, d(2 * xi - nu)),
        "K1": (math.sqrt(0.8965 * s2i * s2i + 0.6001 * s2i * math.cos(nu) + 0.1006), d(-nup)),
        "K2": (math.sqrt(19.0444 * si ** 4 + 2.7702 * si * si * math.cos(2 * nu) + 0.0981), d(-nupp2)),
        "J1": (s2i / 0.7214, d(-nu)),
        "OO1": (si * math.sin(I / 2) ** 2 / 0.0164, d(-2 * xi - nu)),
        "MM": ((2 / 3 - si * si) / 0.5021, 0.0),
        "MF": (si * si / 0.1578, d(-2 * xi)),
        # NOAA starts M1 from T - s + h - 90 at the year's first hour, adds xi - nu + Q from
        # mid-year, and runs it at the M1 speed, so perigee counts from January 1.
        "M1": (f_o1 * math.sqrt(2.310 + 1.435 * math.cos(2 * P)), d(xi - nu + Q) - p_jan1),
        "L2": (f_m2 * math.sqrt(1 - 12 * t2 * math.cos(2 * P) + 36 * t2 * t2), d(2 * xi - 2 * nu - R)),
    }

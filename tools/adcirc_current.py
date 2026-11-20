#!/usr/bin/env python3
"""Spatial tidal currents from the ADCIRC tidal databases: ENPAC15 (Eastern North Pacific)
and EC2015 (Western North Atlantic, Gulf of Mexico and Caribbean Sea).

  adcirc_current.py extract --near LAT LON                           print a point's extract, once
  adcirc_current.py predict --file F [--date D] [--position P]        slacks and peaks
  adcirc_current.py window --file F [--date D] [--position P]         diveable windows under a speed threshold
  adcirc_current.py at --file F --time "D HH:MM" [--position P]       current at a moment
  adcirc_current.py selftest                                          verify the astronomy
"""
import argparse
import json
import math
import os
import sys
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.adcirc import (DATABASES, DEG, UTC, WALK_STEP_M, WORKSPACE, calibrate, in_domain,  # noqa: E402
                        interp_polar, locate, need_db, nodal, nodal_epoch, mean_longitudes, read_mesh,
                        read_vel_header, read_vel_nodes, reconstruct, walk_in,
                        CONSTITUENTS)



def point_key(db):
    """The site JSON key recording where a database's extract was taken."""
    return DATABASES[db]["key"].replace("_constituents", "_extract_point")


def doc_db(doc, src="the extract"):
    """(database name, constituents) of a site JSON's extract; exits when it holds none."""
    found = [(n, doc[d["key"]]) for n, d in DATABASES.items() if d["key"] in doc]
    if not found:
        keys = " or ".join(d["key"] for d in DATABASES.values())
        sys.exit(f"No ADCIRC extract in {src} ({keys}): it holds the site's lat/lon/tz only.")
    if len(found) > 1:
        sys.exit(f"{src} holds extracts from more than one database; keep only one.")
    return found[0]


def _cfg(key, default):
    """Read this tool's section of tool-config.json; missing file or key -> default."""
    try:
        with open(os.path.join(WORKSPACE, "tool-config.json")) as f:
            return json.load(f).get("adcirc_current", {}).get(key, default)
    except (OSError, ValueError):
        return default


def resolve_tz(name):
    """IANA zone name -> ZoneInfo, or exit with a clear error on a bad name."""
    try:
        return ZoneInfo(name)
    except Exception:
        sys.exit(f"{name} is not an IANA time zone name. Pass the site's `tz` from its JSON, e.g. America/Los_Angeles.")



# --------------------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------------------

def cmd_extract(a):
    """Print the extract point and the constituents there as {"<db>_extract_point": {...},
    "<db>_constituents": [...]} on stdout, for the
    caller to attach to the site JSON; progress goes to stderr. The database is the one whose
    domain holds the point."""
    qlat, qlon = a.near
    log = lambda m: print(m, file=sys.stderr, flush=True)
    dbs = [n for n in DATABASES if in_domain(n, qlat, qlon)]
    if not dbs:
        sys.exit(f"{qlat}, {qlon} is outside every ADCIRC database this tool carries: "
                 + "; ".join(f"{n} covers {d['region']}" for n, d in DATABASES.items()) + ".")
    db = dbs[0]
    need_db(db)
    log(f"{db}: reading mesh ({os.path.basename(DATABASES[db]['mesh'])})...")
    lon, lat, elems = read_mesh(db)
    log(f"  {len(elems)} elements, locating {qlat:.5f}, {qlon:.5f}...")
    nodes, w, inside, dist_km = locate(lon, lat, elems, qlon, qlat)
    site = a.site
    if not inside and a.walk:
        site = site or (qlat, qlon)
        qlat, qlon = walk_in(lon, lat, elems, qlon, qlat, WALK_STEP_M)
        log(f"  outside the wet mesh; walked to the nearest point inside it, "
            f"{WALK_STEP_M} m in from its edge: {qlat:.5f}, {qlon:.5f}")
        nodes, w, inside, dist_km = locate(lon, lat, elems, qlon, qlat)
    if not inside:
        sys.exit(f"Point is outside the {db} wet mesh, {dist_km:.2f} km from its nearest node.\n"
                 f"  A boundary-snapped point reads as near-still water, not the site's real "
                 f"current, so this tool refuses it rather than predicting off it. The region's "
                 f"site conventions say where the extract is taken instead; --walk takes it at "
                 f"the nearest point inside the mesh.")
    side_km = max(math.hypot((lon[nodes[i]] - lon[nodes[i - 1]]) * math.cos(math.radians(qlat)),
                             lat[nodes[i]] - lat[nodes[i - 1]]) * 111.0 for i in range(3))
    log(f"  in element with nodes {nodes}, weights {w[0]:.3f}/{w[1]:.3f}/{w[2]:.3f}, "
        f"longest side {side_km * 1000:.0f} m")
    header = read_vel_header(db)
    log("Streaming fort.54 for the 3 nodes (one pass, a minute or several)...")
    vals = read_vel_nodes(db, nodes)
    cons = []
    for k, (name, freq, fnf, eqarg) in enumerate(header):
        n0, n1, n2 = vals[nodes[0]][k], vals[nodes[1]][k], vals[nodes[2]][k]
        u_amp, u_ph = interp_polar(n0[0], n0[1], n1[0], n1[1], n2[0], n2[1], w)
        v_amp, v_ph = interp_polar(n0[2], n0[3], n1[2], n1[3], n2[2], n2[3], w)
        cons.append({
            "name": name, "f_ref": fnf, "v0u_deg": eqarg,
            "u_amp": u_amp, "u_phase": u_ph, "v_amp": v_amp, "v_phase": v_ph,
        })
    slat, slon = site if site else (qlat, qlon)
    km = math.hypot((qlon - slon) * math.cos(math.radians(slat)), qlat - slat) * 111.0
    doc = {point_key(db): {"lat": qlat, "lon": qlon, "distance_from_site_km": round(km, 2)},
           DATABASES[db]["key"]: cons}
    axis, _ = principal_axis(doc, resolve_tz("UTC"))
    log(f"  {len(cons)} constituents. Principal current axis {axis:.0f}°/{(axis + 180) % 360:.0f}° T.")
    log("  Validate against the nearest NOAA station before trusting timing (see selftest).")
    print(json.dumps(doc, indent=2))



def load_doc(a):
    """The extract JSON to predict against: --json holds it inline, --file names a path to
    read it from. argparse enforces that exactly one of the two is given."""
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
    doc_db(doc, src)
    return doc


def series(doc, day, tz):
    """(local_datetime, u_east, v_north) every 6 minutes across the local day, plus a margin."""
    db, cons = doc_db(doc)
    C = calibrate(cons, db)
    start = datetime(day.year, day.month, day.day, tzinfo=tz)
    out = []
    for i in range(-20, 240 + 20):  # -2h .. +26h at 6-min steps
        t_local = start + timedelta(minutes=6 * i)
        t_utc = t_local.astimezone(UTC)
        u = reconstruct(cons, C, t_utc, "u")
        v = reconstruct(cons, C, t_utc, "v")
        out.append((t_local, u, v))
    return out


def principal_axis(doc, tz, day=None):
    """Return (bearing_deg, samples). Bearing of the dominant flow axis (°T)."""
    day = day or date.today()
    samp = series(doc, day, tz)
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


# Fraction of the water column's height, measured up from the bed, that each named position
# represents, and the label used when describing it. 0.05 rather than 0.0 for "bottom": the
# profile is a boundary layer, not defined at the bed itself, real flow there tends toward
# zero in a way this power law does not model.
POSITION_FRACS = {"bottom": (0.05, "the bottom of the water column"), "mid": (0.5, "mid-water"),
                  "surface": (1.0, "the surface")}


def position_factor(position):
    """Multiplier from the column-mean speed to the speed at a position in the water column,
    via a 1/7-power tidal boundary layer: the water runs slower near the bed, faster near the
    surface. `position` is one of 'bottom', 'mid', 'surface', or None for the column mean.
    Returns (factor, note)."""
    if position is None:
        return 1.0, "depth-averaged (whole column); near-surface runs faster"
    frac, label = POSITION_FRACS[position]
    factor = (8.0 / 7.0) * frac ** (1.0 / 7.0)
    return factor, (f"scaled to {label} (x{factor:.2f} of the column mean, 1/7-power profile; "
                    f"approximate, ignores stratification)")


def reconstructors(doc, bearing):
    """(signed_fn, mag_fn): callables from a local datetime to the along-axis signed speed and
    to the total speed magnitude (both un-scaled by depth), evaluating the full reconstruction
    at any instant. These let slack and window boundaries be root-found off the 6-minute grid."""
    db, cons = doc_db(doc)
    C = calibrate(cons, db)
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
    doc = load_doc(a)
    tz = resolve_tz(a.tz)
    factor, note = position_factor(a.position)
    bearing, samp = principal_axis(doc, tz, a.date)
    sig = _signed(samp, bearing)
    signed_fn, _ = reconstructors(doc, bearing)
    axis_a, axis_b = bearing % 360, (bearing + 180) % 360
    print(f"{doc['lat']:.4f}, {doc['lon']:.4f}  {a.date}  {doc_db(doc)[0]} tidal current")
    print(f"  principal axis {axis_a:.0f}° T / {axis_b:.0f}° T "
          f"(which is flood is site-specific; confirm against the tide or a NOAA station)")
    print(f"  {note}")
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
    doc = load_doc(a)
    tz = resolve_tz(a.tz)
    factor, note = position_factor(a.position)
    bearing, samp = principal_axis(doc, tz, a.date)
    sig = _signed(samp, bearing)
    _, mag_fn = reconstructors(doc, bearing)
    lim = a.max_speed
    print(f"{doc['lat']:.4f}, {doc['lon']:.4f}  {a.date}  {doc_db(doc)[0]} tidal current")
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
    day0 = datetime(a.date.year, a.date.month, a.date.day, tzinfo=tz)
    day1 = day0 + timedelta(days=1)
    shown = [(max(t0, day0), min(t1, day1), pk) for t0, t1, pk in runs
             if t1 > day0 and t0 < day1]
    if not shown:
        print(f"  none — current never drops below {lim:.2f} m/s here on this date.")
        return
    for t0, t1, peak in shown:
        mins = round((t1 - t0).total_seconds() / 60)
        if mins >= 1440:
            print(f"  all day          peak {peak:.2f} m/s")
            continue
        flag = "  <-- tight" if mins < 40 else ""
        print(f"  {t0:%H:%M} - {t1:%H:%M}   {mins:>3} min   peak {peak:.2f} m/s{flag}")
    print("\n  Pad it, and confirm against a NOAA station and observation.")


def cmd_at(a):
    doc = load_doc(a)
    tz = resolve_tz(a.tz)
    factor, note = position_factor(a.position)
    t_local = datetime.strptime(a.time, "%Y-%m-%d %H:%M").replace(tzinfo=tz)
    db, cons = doc_db(doc)
    C = calibrate(cons, db)
    t_utc = t_local.astimezone(UTC)
    u = reconstruct(cons, C, t_utc, "u") * factor
    v = reconstruct(cons, C, t_utc, "v") * factor
    spd = math.hypot(u, v)
    toward = math.degrees(math.atan2(u, v)) % 360
    print(f"{doc['lat']:.4f}, {doc['lon']:.4f}  {t_local:%Y-%m-%d %H:%M %Z}  {db} tidal current")
    print(f"  {note}")
    print(f"  speed {spd:.2f} m/s   toward {toward:.0f}° T   (east {u:+.2f}, north {v:+.2f})")


def cmd_selftest(a):
    """Validate the astronomy against each database's fort.54 header values at its epoch: the
    frequency implied by each constituent's Doodson coefficients, and its nodal factor f."""
    ok = True
    for db in (a.db or list(DATABASES)):
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
    if not ok:
        sys.exit(1)


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("extract", help="print a point's constituents as JSON, to attach to the site JSON")
    s.add_argument("--near", nargs=2, type=float, metavar=("LAT", "LON"), required=True,
                   help="the extraction point: the dive area, or a point walked into the mesh")
    s.add_argument("--site", nargs=2, type=float, metavar=("LAT", "LON"),
                   help="the site's own coordinate, when the extraction point is elsewhere "
                        "(default: the --near point)")
    s.add_argument("--walk", action="store_true",
                   help="a --near point outside the wet mesh is walked to the nearest point "
                        f"inside it, {WALK_STEP_M} m in from its edge, and recorded as the extract "
                        "point, with --near as the site")
    s.set_defaults(fn=cmd_extract)

    position_help = ("where in the water column: bottom, mid, or surface (default: the "
                      "column mean, unscaled)")
    tz_help = "the site's time zone, the `tz` in its JSON"

    def doc_source(sp):
        g = sp.add_mutually_exclusive_group(required=True)
        g.add_argument("--json", metavar="JSON", help="the extract's full JSON content, inline")
        g.add_argument("--file", metavar="PATH", help="path to the extract JSON file")

    def dated(sp):
        doc_source(sp)
        sp.add_argument("--date", type=date.fromisoformat, default=date.today())
        sp.add_argument("--position", choices=sorted(POSITION_FRACS), help=position_help)
        sp.add_argument("--tz", required=True, metavar="IANA_ZONE", help=tz_help)

    s = sub.add_parser("predict", help="slack / max flood / max ebb")
    dated(s)
    s.set_defaults(fn=cmd_predict)

    s = sub.add_parser("window", help="diveable windows")
    dated(s)
    _ms = _cfg("max_speed_ms", 0.25)
    s.add_argument("--max-speed", type=float, default=_ms, help=f"m/s, default {_ms}")
    s.set_defaults(fn=cmd_window)

    s = sub.add_parser("at", help="instantaneous current vector")
    doc_source(s)
    s.add_argument("--time", required=True, metavar="YYYY-MM-DD HH:MM")
    s.add_argument("--position", choices=sorted(POSITION_FRACS), help=position_help)
    s.add_argument("--tz", required=True, metavar="IANA_ZONE", help=tz_help)
    s.set_defaults(fn=cmd_at)

    s = sub.add_parser("selftest", help="validate astronomy against each database's ADCIRC header")
    s.add_argument("--db", choices=sorted(DATABASES), action="append",
                   help="one database (repeatable); default every database")
    s.set_defaults(fn=cmd_selftest)

    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()

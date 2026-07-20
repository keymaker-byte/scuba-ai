#!/usr/bin/env python3
"""Read the Subsurface dive log (native .xml/.ssrf). Read-only. Metric, local time.

  list [--site S] [--since D] [--limit N]   recent dives, one line each
  show SELECTOR                              full detail for one dive: aggregates, notes, marks
  profile SELECTOR [--csv]                   the per-sample time series (depth, temp, pressure)

SELECTOR picks a dive: a bare integer matches the dive number; otherwise it is a substring
matched against the date, site name, site region (location, state, country, ocean) or trip
tags. `list --site` matches name and region too. An ambiguous selector lists the candidates.

This never writes the file. Subsurface owns it; point Subsurface at it, not this tool. Set
SUBSURFACE_XML to override the path (defaults to the app's saved logbook).

Subsurface labels every value with its unit inline (depth='23.1 m', water='13.0 C',
pressure0='219.67 bar', size='10.0 l', weight='13.2 kg'), so this tool reads the suffix and
presents metric whatever the app's display units are set to. It also carries fields MacDive's
own export drops on the way to Subsurface: a computed SAC per dive, and (once backfilled)
visibility and current as 1-5 ratings and the diver's in-dive bookmarks. Times are local; a
sample's time is minutes:seconds into the dive, so its clock time is the dive start plus that.
"""
import argparse
import csv
import json
import os
import re
import sys
from datetime import datetime, timedelta
from xml.etree.ElementTree import iterparse, ParseError


def _log_path(env):
    """Resolve the logbook path: env var, else tool-config.json subsurface_log.file.
    Relative paths resolve against the workspace root; ~ expands. None if nothing is set."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    raw = os.environ.get(env)
    if not raw:
        try:
            with open(os.path.join(root, "tool-config.json")) as f:
                raw = json.load(f).get("subsurface_log", {}).get("file")
        except (OSError, ValueError):
            raw = None
    if not raw:
        return None
    p = os.path.expanduser(raw)
    return p if os.path.isabs(p) else os.path.join(root, p)


# Path is machine-specific, so it lives in tool-config.json (subsurface_log.file), not here.
LOG = _log_path("SUBSURFACE_XML")

# Value-with-unit -> metric float. Subsurface writes the unit, so convert off the suffix.
_SCALE = {"m": 1.0, "ft": 0.3048, "bar": 1.0, "psi": 0.0689476,
          "l": 1.0, "cuft": 28.3168, "ft3": 28.3168, "kg": 1.0, "lbs": 0.453592, "lb": 0.453592}
VIS_GLOSS = {1: "very poor", 2: "poor", 3: "moderate", 4: "good", 5: "excellent"}
CUR_GLOSS = {1: "strong", 2: "notable", 3: "moderate", 4: "mild", 5: "slack/none"}
SEA_GLOSS = {1: "severe", 2: "notable", 3: "moderate", 4: "mild", 5: "calm/none"}


def metric(s):
    """'23.1 m' -> 23.1 ; '70.0 F' -> 21.1 ; unit read off the suffix, result metric."""
    if not s:
        return None
    m = re.match(r"\s*(-?[\d.]+)\s*([a-zA-Z/]*)", s)
    if not m:
        return None
    v, u = float(m.group(1)), m.group(2)
    if u == "F":
        return (v - 32.0) * 5.0 / 9.0
    if u in ("C", ""):
        return v
    return v * _SCALE.get(u, 1.0)


def mmss_to_s(s):
    """'75:00 min' or '3:00 min' -> seconds."""
    if not s:
        return None
    m = re.match(r"\s*(\d+):(\d+)", s)
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None


def parse_dives():
    """Stream the log. Build the site table (it precedes the dives), then yield dive dicts."""
    if LOG is None:
        sys.exit("Subsurface file not configured. Its location is specific to this machine, so "
                 "set subsurface_log.file in tool-config.json (or the SUBSURFACE_XML env var) "
                 "to your saved logbook. If you do not use Subsurface, this source does not apply.")
    if not os.path.exists(LOG):
        sys.exit(f"Subsurface log not found: {LOG}\n"
                 f"Save your logbook from Subsurface (File > Save), or fix subsurface_log.file "
                 f"in tool-config.json.")
    sites = {}
    try:
        for _, el in iterparse(LOG, events=("end",)):
            if el.tag == "site":
                gps = (el.get("gps") or "").split()
                geo = {g.get("cat"): g.get("value") for g in el.findall("geo")}
                sites[el.get("uuid")] = {
                    "name": el.get("name") or "",
                    "lat": gps[0] if len(gps) == 2 else None,
                    "lon": gps[1] if len(gps) == 2 else None,
                    "location": (el.findtext("notes") or "").strip(),
                    # Subsurface taxonomy categories: 1 ocean, 2 country, 3 state/province
                    "ocean": geo.get("1"),
                    "country": geo.get("2"),
                    "state": geo.get("3"),
                }
                el.clear()
            elif el.tag == "dive":
                yield build_dive(el, sites)
                el.clear()
    except ParseError as e:
        sys.exit(f"Could not parse {LOG}: {e}\n"
                 f"If Subsurface is open and mid-save, close it and try again.")


def build_dive(el, sites):
    d = dict(el.attrib)
    d["site"] = sites.get(el.get("divesiteid"), {})
    d["notes"] = (el.findtext("notes") or "").strip()
    d["buddy"] = (el.findtext("buddy") or "").strip()
    d["divemaster"] = (el.findtext("divemaster") or "").strip()
    d["cylinders"] = [c.attrib for c in el.findall("cylinder")]
    ws = el.find("weightsystem")
    d["weight"] = ws.get("weight") if ws is not None else None
    dc = el.find("divecomputer")
    d["model"] = dc.get("model") if dc is not None else None
    depth = dc.find("depth") if dc is not None else None
    d["max_depth"] = depth.get("max") if depth is not None else None
    d["mean_depth"] = depth.get("mean") if depth is not None else None
    temp = dc.find("temperature") if dc is not None else None
    d["water_temp"] = temp.get("water") if temp is not None else None
    d["air_temp"] = temp.get("air") if temp is not None else None
    d["extra"] = {e.get("key"): e.get("value")
                  for e in (dc.findall("extradata") if dc is not None else [])}
    events = dc.findall("event") if dc is not None else []
    d["marks"] = [(mmss_to_s(e.get("time")), e.get("name") or "bookmark")
                  for e in events if e.get("type") == "8"]
    d["gaschanges"] = [(mmss_to_s(e.get("time")), e.get("cylinder"), e.get("o2"))
                       for e in events if e.get("name") == "gaschange"]
    d["samples"] = [(mmss_to_s(sm.get("time")), metric(sm.get("depth")),
                     metric(sm.get("temp")), metric(sm.get("pressure0")))
                    for sm in (dc.findall("sample") if dc is not None else [])]
    return d


def site_name(d):
    return (d.get("site") or {}).get("name") or "?"


def site_region(d):
    """Location (site notes), state and country, joined; ocean appended in parens."""
    s = d.get("site") or {}
    parts = ", ".join(x for x in (s.get("location"), s.get("state"), s.get("country")) if x)
    return parts + (f" ({s['ocean']})" if s.get("ocean") else "")


def dive_dt(d):
    try:
        return datetime.strptime(f"{d.get('date')} {d.get('time')}", "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return None


def matches(d, sel):
    if sel.isdigit() and d.get("number") == sel:
        return True
    hay = f"{d.get('date','')} {site_name(d)} {site_region(d)} {d.get('tags','')}"
    return sel.lower() in hay.lower()


def find(sel):
    hits = [d for d in parse_dives() if matches(d, sel)]
    if not hits:
        sys.exit(f"No dive matches {sel!r}.")
    if len(hits) > 1:
        exact = [d for d in hits if d.get("number") == sel]
        if len(exact) == 1:
            return exact[0]
        print(f"{sel!r} matches {len(hits)} dives:", file=sys.stderr)
        for d in hits[:20]:
            print(f"  #{d.get('number'):>4}  {d.get('date')} {d.get('time')}  {site_name(d)}", file=sys.stderr)
        sys.exit(1)
    return hits[0]


def gas_label(cyl):
    o2 = cyl.get("o2")
    if not o2:
        return "air"          # Subsurface omits o2 for air
    n = metric(o2)
    return "air" if n and round(n) == 21 else (f"EAN{round(n)}" if n else "?")


def cmd_list(args):
    rows = []
    for d in parse_dives():
        if args.site and args.site.lower() not in f"{site_name(d)} {site_region(d)}".lower():
            continue
        if args.since and (d.get("date") or "") < args.since:
            continue
        rows.append(d)
    rows.sort(key=lambda d: (d.get("date") or "", d.get("time") or ""), reverse=True)
    if args.limit:
        rows = rows[: args.limit]
    print(f"{'#':>4}  {'date':<19}  {'site':<26}  {'max':>6}  {'min':>4}  {'temp':>5}  {'vis':>3}  gas")
    for d in rows:
        secs = mmss_to_s(d.get("duration"))
        mind = f"{secs // 60}m" if secs else ""
        md = metric(d.get("max_depth"))
        wt = metric(d.get("water_temp"))
        vis = d.get("visibility") or ""
        gas = gas_label(d["cylinders"][0]) if d.get("cylinders") else ""
        print(f"{d.get('number',''):>4}  {(d.get('date','')+' '+d.get('time','')):<19}  "
              f"{site_name(d)[:26]:<26}  {(f'{md:.1f}m' if md is not None else ''):>6}  {mind:>4}  "
              f"{(f'{wt:.0f}C' if wt is not None else ''):>5}  {vis:>3}  {gas}")


def cmd_show(args):
    d = find(args.selector)
    st = dive_dt(d)
    print(f"Dive #{d.get('number')}  {d.get('date')} {d.get('time')}  {site_name(d)}")
    site = d.get("site") or {}
    if site.get("name"):
        gps = f"  ({site['lat']}, {site['lon']})" if site.get("lat") else ""
        print(f"  location     {site['name']}{gps}")
        region = site_region(d)
        if region:
            print(f"  region       {region}")
    print(f"  computer     {d.get('model')}")
    secs = mmss_to_s(d.get("duration"))
    if secs:
        print(f"  duration     {secs // 60} min ({secs} s)")
    md, mn = metric(d.get("max_depth")), metric(d.get("mean_depth"))
    print(f"  max depth    {md:.1f} m   avg {mn:.1f} m" if md is not None else "  max depth    (none)")
    wt, at = metric(d.get("water_temp")), metric(d.get("air_temp"))
    if wt is not None:
        print(f"  temperature  water {wt:.1f} C" + (f", air {at:.1f} C" if at is not None else ""))
    wkg = metric(d.get("weight"))
    if wkg is not None:
        print(f"  weight       {wkg:.1f} kg")
    for lbl in ("buddy", "divemaster"):
        if d.get(lbl):
            print(f"  {lbl:<12} {d[lbl]}")
    for key, gloss, lbl in (("visibility", VIS_GLOSS, "visibility"), ("current", CUR_GLOSS, "current")):
        v = d.get(key)
        if v and v.isdigit():
            print(f"  {lbl:<12} {v}/5 ({gloss.get(int(v), '')})")
    for key in ("wavesize", "surge", "chill"):
        v = d.get(key)
        if v and v.isdigit():
            print(f"  {key:<12} {v}/5 ({SEA_GLOSS.get(int(v), '')})")
    v = d.get("rating")
    if v and v.isdigit():
        print(f"  rating       {v}/5")
    for k, v in (d.get("extra") or {}).items():
        print(f"  {k:<12} {v}")
    if d.get("tags"):
        print(f"  tags         {d['tags']}")
    for c in d["cylinders"]:
        ps, pe = c.get("start"), c.get("end")
        rng = f"  {metric(ps):.0f}->{metric(pe):.0f} bar" if ps and pe else (f"  end {metric(pe):.0f} bar" if pe else "")
        vol = metric(c.get("size"))
        desc = f" ({c['description']})" if c.get("description") else ""
        print(f"  gas          {gas_label(c)}  {vol:.1f} L @ {metric(c.get('workpressure')):.0f} bar{desc}{rng}")
    if len(d["cylinders"]) > 1 and d.get("gaschanges"):
        for secs_g, cyl, o2 in sorted(d["gaschanges"], key=lambda g: g[0] or 0):
            print(f"  gas change   {secs_g // 60}:{secs_g % 60:02d}  cylinder {cyl}"
                  + (f" ({o2} O2)" if o2 else ""))
    if d.get("sac"):
        print(f"  SAC          {d['sac']}")
    if d.get("otu"):
        print(f"  OTU          {d['otu']}")
    if d.get("cns"):
        print(f"  CNS          {d['cns']}")
    if d.get("watersalinity"):
        print(f"  salinity     {d['watersalinity']}")

    s = d["samples"]
    if s:
        deep = max(s, key=lambda x: x[1] or 0)
        clock = f"  ({(st + timedelta(seconds=deep[0])).strftime('%H:%M:%S')})" if st and deep[0] is not None else ""
        print(f"  deepest      {deep[1]:.1f} m at {deep[0] / 60:.1f} min into the dive{clock}")
        temps = [t for _, _, t, _ in s if t is not None]
        if temps:
            print(f"  temp range   {min(temps):.0f} to {max(temps):.0f} C across {len(s)} samples")
    if d["marks"]:
        print("  marks:")
        for secs_m, label in sorted(d["marks"], key=lambda m: m[0] or 0):
            clock = f"  ({(st + timedelta(seconds=secs_m)).strftime('%H:%M:%S')})" if st and secs_m is not None else ""
            print(f"    {secs_m // 60}:{secs_m % 60:02d}  {label}{clock}")
    if d["notes"]:
        print("  notes:")
        for line in d["notes"].splitlines():
            print(f"    {line}")


def cmd_profile(args):
    d = find(args.selector)
    s = d["samples"]
    if not s:
        sys.exit(f"Dive #{d.get('number')} has no samples.")
    st = dive_dt(d)
    cols = ["clock", "t_min", "depth_m", "temp_c", "pressure_bar"]
    rows = []
    for t, depth, temp, press in s:
        clock = (st + timedelta(seconds=t)).strftime("%H:%M:%S") if st and t is not None else ""
        rows.append([clock, f"{t / 60:.2f}" if t is not None else "",
                     f"{depth:.1f}" if depth is not None else "",
                     f"{temp:.1f}" if temp is not None else "",
                     f"{press:.1f}" if press is not None else ""])
    if args.csv:
        w = csv.writer(sys.stdout)
        w.writerow(cols)
        w.writerows(rows)
        return
    print(f"Dive #{d.get('number')}  {d.get('date')} {d.get('time')}  {site_name(d)}  ({len(s)} samples)")
    print(f"  {'clock':<9} {'min':>6} {'depth':>7} {'temp':>5} {'press':>7}")
    for r in rows:
        print(f"  {r[0]:<9} {r[1]:>6} {r[2]:>7} {r[3]:>5} {r[4]:>7}")


def main():
    p = argparse.ArgumentParser(description="Read the Subsurface dive log (read-only).")
    sub = p.add_subparsers(dest="cmd", required=True)
    pl = sub.add_parser("list", help="recent dives, one line each")
    pl.add_argument("--site")
    pl.add_argument("--since", help="dives on or after YYYY-MM-DD")
    pl.add_argument("--limit", type=int, default=25)
    pl.set_defaults(func=cmd_list)
    ps = sub.add_parser("show", help="full detail for one dive")
    ps.add_argument("selector")
    ps.set_defaults(func=cmd_show)
    pp = sub.add_parser("profile", help="the per-sample time series")
    pp.add_argument("selector")
    pp.add_argument("--csv", action="store_true")
    pp.set_defaults(func=cmd_profile)
    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

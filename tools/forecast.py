#!/usr/bin/env python3
"""Forecast at a dive site, in five blocks: wind (with the go / no go call against the site's sectors),
waves (with their call against the entry's shore), the surface current and water temperature, the
weather and temperature, and the hazards and warnings in effect. Each block is answered by the first
source that covers the site: NWS in US water, Open-Meteo anywhere.

  forecast.py at  --file SLUG.JSON --time "YYYY-MM-DD HH:MM"     planning: every block at the entry or exit time
  forecast.py day --file SLUG.JSON --date YYYY-MM-DD             planning: every block for every hour of the day
  forecast.py at  --near LAT LON --tz ZONE --time ... [--sea LAT LON] [--bad S] [--short S]   by hand
"""
import argparse
import os
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import forecast as F  # noqa: E402


def f1(v, unit, fmt="{:.1f}"):
    return "-" if v is None else fmt.format(v) + unit


def direction(deg):
    return "-" if deg is None else f"{F.compass(deg)} ({deg:.0f}°)"


# ---------------------------------------------------------------- reading every block first

def read_all(site, blocks, t0, t1, only):
    """{block: (source, reading) or (None, why)}; any failed source stops the run before anything prints."""
    out = {}
    for b in blocks:
        try:
            src, why = F.pick(b, site, only)
            if src is None:
                out[b] = (None, why)
                continue
            lat, lon = site.point(b)
            out[b] = (src, src.read(b, lat, lon, site.tz, t0, t1, also=site.sea if b == "hazards" else None,
                                     inland=site.inland))
        except F.Failed as e:
            sys.exit(f"{F.TITLES[b]}: {e}\nNothing was reported: the forecast stops on a failed source.")
    return out


def header(site, a, zone):
    if site.path:
        s = site.raw_sectors
        print(f"  site       {site.path}")
        print(f"  sectors    bad {','.join(s['bad']) or 'none'}; short fetch {','.join(s['short']) or 'none'}; "
              f"mixed {','.join(s['mixed']) or 'none'}" + ("; calm only" if site.calm_only else ""))
    elif site.judged:
        print(f"  sectors    bad {','.join(a.bad or []) or 'none'}; short {','.join(a.short or []) or 'none'}")
    land = "the dive area, a boat site" if site.boat else "the entry point" if site.path else "--near"
    print(f"  land point {site.land[0]}, {site.land[1]}  ({land}: wind, weather, hazards)")
    if site.faces is not None:
        print(f"  shore      the {'dive area' if site.boat else 'entry'} faces {F.compass(site.faces)} ({site.faces:.0f}°)")
    if site.swim_out:
        so = site.swim_out
        print(f"  swim out   {so['distance_m']:.0f} m toward {F.compass(so['bearing'])} ({so['bearing']:.0f}°), "
              f"{so['off_entry_faces']:.0f}° off the shore's facing")
    print(f"  sea point  {site.sea[0]}, {site.sea[1]}  "
          f"({'the dive area' if site.path else '--sea' if site.sea != site.land else '--near'}: waves, surface current)")
    print(f"  zone       {zone.key}")


def block_head(b, got):
    src, r = got
    print()
    print(f"  {F.TITLES[b].upper()}")
    if src is None:
        print(f"    not covered: {r}")
        return False
    for line in r.meta:
        print(f"    {line}")
    if getattr(r, "empty", False):
        print(f"    no {'wave' if b == 'waves' else 'ocean'} model holds this water")
        return False
    return True


# ---------------------------------------------------------------- one moment

def wind_line(row, site):
    c = F.call_wind(row["speed"], row["gust"], row["dir"], site)
    rel = site.relation[F.point_index(row["dir"])] if site.relation and row["dir"] is not None else None
    return (f"{f1(row['speed'], ' m/s'):>8}  from {direction(row['dir']):10}  gust {f1(row['gust'], ' m/s'):>8}"
            + (f"  {rel:11}" if rel else "") + (f"   call {F.call_text(c)}" if c else "")), c


def waves_line(row, site):
    if row["height"] is None:
        return "no reading", None
    c = F.call_waves(row["height"], row["dir"], site)
    s = f"{f1(row['height'], ' m', '{:.2f}'):>7} from {direction(row['dir']):10} {f1(row['period'], ' s'):>6}"
    for label, k in (("wind waves", "wind_wave"), ("swell", "swell"), ("2nd swell", "swell2")):
        if row.get(f"{k}_height") is not None:
            s += (f"   {label} {f1(row[f'{k}_height'], ' m', '{:.2f}')} from {direction(row.get(f'{k}_dir'))} "
                  f"{f1(row.get(f'{k}_period'), ' s')}")
    return s + (f"   call {F.call_text(c)}" if c else ""), c


def models_at(b, r, t, site, fmt):
    rows = r.at(t)
    calls = []
    for i, m in enumerate(r.models):
        line, c = fmt(rows[m], site)
        tag = "" if len(r.models) == 1 else f"{m:22} "
        print(f"    {tag}{line}")
        calls.append(c)
    if len(r.models) > 1:
        r1, r2 = rows[r.models[0]], rows[r.models[1]]
        if r.disagrees(r1, r2):
            print("    <-- the models disagree: treat the figure with care, and plan on the more severe call")
        if calls[0] and calls[1] and calls[0][1] != calls[1][1]:
            print("    <-- the calls differ: the plan carries the more severe one")


def weather_at(row):
    print(f"    air {f1(row['air'], ' °C')}, feels like {f1(row['feels'], ' °C')}, dew point {f1(row['dew'], ' °C')}, "
          f"humidity {f1(row['rh'], '%', '{:.0f}')}")
    sky = row["sky"] or row["wx"]
    extra = f", {row['wx']}" if row["wx"] and row["wx"] != sky else ""
    print(f"    sky {f1(row['cloud'], '% cloud', '{:.0f}')}, {sky or '-'}{extra}")
    print(f"    rain chance {f1(row['pop'], '%', '{:.0f}')}, {f1(row['rain_mm_h'], ' mm/h')}")
    vis = row["vis_m"]
    print(f"    visibility {f1(vis / 1000 if vis is not None else None, ' km')}, fog {'yes' if row['fog'] else 'no'}")
    t = f"{row['thunder_pct']:.0f}%" if row.get("thunder_pct") is not None else ("yes" if row["thunder"] else "no")
    cape = f", CAPE {row['cape']:.0f} J/kg" if row.get("cape") is not None else ""
    print(f"    thunder {t}{cape}")
    print(f"    call {F.call_text(F.call_weather(row))}")


def when(a):
    if a["start"] and a["end"]:
        return f"{a['start']:%a %d %b %H:%M} to {a['end']:%a %d %b %H:%M}"
    return f"from {a['start']:%a %d %b %H:%M}" if a["start"] else f"until {a['end']:%a %d %b %H:%M}"


def hazards(r, t=None):
    if not r.alerts:
        print("    none in effect over the span")
        return
    for a in r.alerts:
        c = F.call_alert(a["event"])
        live = t is not None and (a["start"] is None or a["start"] <= t) and (a["end"] is None or t < a["end"])
        band = c if c else "not about the water"
        print(f"    {a['event']} ({a['severity']}), {when(a)}: {band}" + ("  [in effect at the moment]" if live else ""))
        print(f"      {a['headline']}")


def cmd_at(a, site, blocks):
    zone = ZoneInfo(site.tz)
    t = datetime.strptime(a.time, "%Y-%m-%d %H:%M").replace(tzinfo=zone)
    day = t.replace(hour=0, minute=0)
    got = read_all(site, blocks, day, day + timedelta(days=1), a.source)
    header(site, a, zone)
    print(f"  moment     {t:%Y-%m-%d %H:%M}")
    for b in blocks:
        if not block_head(b, got[b]):
            continue
        r = got[b][1]
        if b == "hazards":
            hazards(r, t)
            continue
        try:
            if b == "wind":
                models_at(b, r, t, site, wind_line)
            elif b == "waves":
                models_at(b, r, t, site, waves_line)
            elif b == "current":
                row = r.at(t)[r.models[0]]
                print(f"    {f1(row['speed'], ' m/s', '{:.2f}')} toward {direction(row['dir'])}, "
                      f"water at the surface {f1(row['sst'], ' °C')}")
            else:
                weather_at(r.at(t)[r.models[0]])
        except F.Failed as e:
            sys.exit(f"{F.TITLES[b]}: {e}")


# ---------------------------------------------------------------- one day

def cmd_day(a, site, blocks):
    zone = ZoneInfo(site.tz)
    day = datetime.strptime(a.date, "%Y-%m-%d").replace(tzinfo=zone)
    end = day + timedelta(days=1)
    got = read_all(site, blocks, day, end, a.source)
    header(site, a, zone)
    print(f"  date       {a.date}")
    for b in blocks:
        if not block_head(b, got[b]):
            continue
        r = got[b][1]
        if b == "hazards":
            hazards(r)
            continue
        hours = r.hours(day, end)
        if b in ("wind", "waves"):
            fmt = wind_line if b == "wind" else waves_line
            for m in r.models:
                if len(r.models) > 1:
                    print(f"    {m}{' (primary)' if m == r.models[0] else ' (cross-check)'}")
                for t in hours:
                    rows = r.at(t)
                    line, _ = fmt(rows[m], site)
                    flag = ""
                    if len(r.models) > 1 and m == r.models[0] and r.disagrees(rows[r.models[0]], rows[r.models[1]]):
                        flag = "  <-- models disagree"
                    print(f"    {t:%H:%M}  {line}{flag}")
        elif b == "current":
            for t in hours:
                row = r.at(t)[r.models[0]]
                print(f"    {t:%H:%M}  {f1(row['speed'], ' m/s', '{:.2f}'):>9} toward {direction(row['dir']):10}"
                      f"  water {f1(row['sst'], ' °C')}")
        else:
            print(f"    {'time':5}  {'air':>7}  {'feels':>7}  {'dew':>7}  {'rh':>4}  {'cloud':>5}  {'rain':>4}  "
                  f"{'mm/h':>4}  {'vis':>7}  fog  {'thunder':7}  {'call':10}  sky")
            for t in hours:
                w = r.at(t)[r.models[0]]
                vis = w["vis_m"] / 1000 if w["vis_m"] is not None else None
                th = f"{w['thunder_pct']:.0f}%" if w.get("thunder_pct") is not None else ("yes" if w["thunder"] else "no")
                print(f"    {t:%H:%M}  {f1(w['air'], ' °C'):>7}  {f1(w['feels'], ' °C'):>7}  {f1(w['dew'], ' °C'):>7}  "
                      f"{f1(w['rh'], '%', '{:.0f}'):>4}  {f1(w['cloud'], '%', '{:.0f}'):>5}  "
                      f"{f1(w['pop'], '%', '{:.0f}'):>4}  {f1(w['rain_mm_h'], '', '{:.1f}'):>4}  "
                      f"{f1(vis, ' km'):>7}  {'yes' if w['fog'] else 'no ':3}  {th:7}  {F.call_weather(w)[1]:10}  {w['sky'] or w['wx']}")


# ---------------------------------------------------------------- arguments

def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    for name, fn, helptext in (("at", cmd_at, "every block at one local moment"),
                               ("day", cmd_day, "every block for every hour of one local day")):
        s = sub.add_parser(name, help=helptext)
        if name == "at":
            s.add_argument("--time", required=True, metavar="YYYY-MM-DD HH:MM")
        else:
            s.add_argument("--date", required=True, metavar="YYYY-MM-DD")
        s.add_argument("--file", metavar="SLUG.JSON",
                       help="the site JSON: its entry and dive area, wind sectors, shore relations and tz")
        s.add_argument("--near", nargs=2, type=float, metavar=("LAT", "LON"),
                       help="by hand: the land point, the entry (wind, weather, hazards)")
        s.add_argument("--sea", nargs=2, type=float, metavar=("LAT", "LON"),
                       help="by hand: the sea point, the dive area (waves, surface current); --near by default")
        s.add_argument("--tz", metavar="IANA_ZONE", help="the site's time zone, the `tz` in its JSON")
        s.add_argument("--bad", action="append", metavar="SECTOR", help="by hand: the Bad sector(s), e.g. SW-WNW")
        s.add_argument("--short", action="append", metavar="SECTOR",
                       help="by hand: the Short fetch and Mixed sector(s); their bands move up")
        s.add_argument("--block", action="append", metavar="BLOCK",
                       help=f"only these blocks, comma separated or repeated: {', '.join(F.BLOCKS)}")
        s.add_argument("--source", choices=("nws", "open-meteo"),
                       help="the source for wind and weather, past the location's own choice")
        s.set_defaults(fn=fn)
    a = p.parse_args()
    if a.file:
        if a.near or a.sea or a.bad or a.short:
            sys.exit("--file names the points and the sectors: give it without --near, --sea, --bad or --short")
        site = F.site_from_file(a.file, a.tz)
    else:
        site = F.site_by_hand(a.near, a.tz, a.bad, a.short, a.sea)
    try:
        ZoneInfo(site.tz)
    except Exception:
        sys.exit(f"{site.tz} is not an IANA time zone name. Pass the site's `tz` from its JSON, e.g. America/Los_Angeles.")
    blocks = list(F.BLOCKS)
    if a.block:
        blocks = [b.strip() for spec in a.block for b in spec.split(",")]
        bad = [b for b in blocks if b not in F.BLOCKS]
        if bad:
            sys.exit(f"unknown block {', '.join(bad)}: choose from {', '.join(F.BLOCKS)}")
    a.fn(a, site, blocks)


if __name__ == "__main__":
    main()

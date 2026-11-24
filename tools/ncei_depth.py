#!/usr/bin/env python3
"""Seabed depth at a coordinate from NOAA NCEI's ninth arc-second coastal DEM, read from
tiles kept on this machine.

  ncei_depth.py LAT LON                     depth below NAVD88 (~mean sea level)
  ncei_depth.py LAT LON --mllw              also below MLLW, the site file figure
  ncei_depth.py LAT LON --mllw --region R   pick the VDatum region explicitly
  ncei_depth.py LAT LON --verify            compare with NCEI's live service
  ncei_depth.py --fetch S W N E             download every tile touching a box, ahead of time
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.ncei import (_cfg, _Grid, dem, fetch, inland, lake_at, lake_joined, lake_level, LAKE_MIN,
                      mllw_offset, verify)  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("lat", type=float, nargs="?")
    p.add_argument("lon", type=float, nargs="?")
    p.add_argument("--fetch", nargs=4, type=float, action="append", metavar=("S", "W", "N", "E"),
                   help="download every tile touching this box; repeatable")
    p.add_argument("--workers", type=int, default=6, help="tiles downloaded at once with --fetch, default 6")
    p.add_argument("--mllw", action="store_true", help="also convert to depth below MLLW (VDatum)")
    p.add_argument("--region", default=None,
                   help="VDatum region: contiguous (Atlantic/Gulf, VDatum's own default), westcoast, "
                        "ak, seak, hi, prvi, gcnmi, as, chesapeak_delaware, wgom, sgi, spi, sli; "
                        "defaults to ncei_depth.default_region in tool-config.json")
    p.add_argument("--verify", action="store_true", help="compare the tile with NCEI's live service")
    a = p.parse_args()
    region = a.region or _cfg("default_region")
    if a.fetch:
        sys.exit(1 if fetch(a.fetch, a.workers) else 0)
    if a.lat is None or a.lon is None:
        p.error("give LAT LON, or --fetch S W N E")

    r = dem(a.lat, a.lon)
    print(f"{a.lat}, {a.lon}")
    grid = _Grid(download=True)
    lake, where = lake_at(a.lat, a.lon), ""
    if lake and lake_level(lake[0], lake[2], lake[3], grid)["level"] is None or not lake and inland(a.lat, a.lon):
        joined = lake_joined(a.lat, a.lon, grid)
        if joined:
            where = f", in {lake[1]} joined to it" if lake else ", in water joined to it outside its outline"
            lake = joined[1]
        elif not lake and r["elev"] < 0:
            print(f"  inland of the coastline and in no lake, at {r['elev']:+.1f} m {r['datum']}: "
                  f"water no lake outline holds, or diked ground; no depth.")
            print(f"  source {r['source']} (~{r['res_m']:.0f} m), read from this machine")
            return
    if lake:
        hid, name, rings, info = lake
        lv = lake_level(hid, rings, info, grid)
        level = lv["level"]
        if level is None:
            print(f"  in {name}: bed or water at {r['elev']:+.1f} m {r['datum']}; no depth, since "
                  f"no water level was found for the lake: {lv['why']}.")
        elif r["elev"] > level - LAKE_MIN:
            print(f"  in {name}{where}, at or above its water level ({r['elev']:+.1f} m {r['datum']}): "
                  f"shore, or water the DEM holds no bed for. Walk the coordinate out.")
        else:
            print(f"  lake bed {level - r['elev']:.1f} m below the water of {name}{where}")
            print(f"  (bed {r['elev']:+.1f} m {r['datum']}; water level {level:+.1f} m, the DEM's flat "
                  f"water along {lv['spread']} of 12 stretches of its shore on the day it was surveyed)")
        print(f"  source {r['source']} (~{r['res_m']:.0f} m), read from this machine")
        if a.mllw:
            print("  MLLW applies to the sea, never to a lake.")
        return
    if r["elev"] >= 0:
        print(f"  ABOVE WATER: +{r['elev']:.1f} m in the DEM ({r['datum']}). Check the coordinate.")
    else:
        print(f"  seabed {r['depth']:.1f} m below {r['datum']}")
    print(f"  source {r['source']} (~{r['res_m']:.0f} m), read from this machine")
    if a.mllw and r["elev"] < 0:
        off, s, dist = mllw_offset(a.lat, a.lon, region)
        where = "at this point" if dist < 1 else f"{dist:.0f} m away"
        print(f"  seabed {r['depth'] - off:.1f} m below MLLW  (NAVD 88 is {off:.2f} m above MLLW; "
              f"VDatum, asked {where} on {s['fetched']})")
    if a.verify and not verify(a.lat, a.lon, r):
        sys.exit(1)


if __name__ == "__main__":
    main()

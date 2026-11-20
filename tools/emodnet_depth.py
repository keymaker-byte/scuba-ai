#!/usr/bin/env python3
"""Seabed depth at a coordinate from EMODnet Bathymetry.

  emodnet_depth.py LAT LON    depth below LAT, from EMODnet's survey-backed grid
"""
import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

EMODNET_URL = "https://rest.emodnet-bathymetry.eu/depth_sample"


def emodnet(lat, lon):
    """Return the raw depth_sample dict, or None if EMODnet has no coverage at this point."""
    geom = f"POINT({lon} {lat})"
    url = EMODNET_URL + "?" + urllib.parse.urlencode({"geom": geom})
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            if r.status == 204:
                return None
            body = r.read()
    except urllib.error.HTTPError as e:
        if e.code == 204:
            return None
        sys.exit(f"EMODnet request failed ({e.code} {e.reason})\n  {url}")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        sys.exit(f"EMODnet request failed ({getattr(e, 'reason', e)})\n  {url}")
    if not body.strip():
        return None
    try:
        d = json.loads(body)
    except ValueError:
        sys.exit(f"EMODnet answered with something other than JSON\n  {url}")
    if not isinstance(d, dict) or d.get("avg") is None:
        return None
    return d


def print_emodnet(d):
    avg = d["avg"]
    if avg >= 0:
        print(f"  ABOVE WATER: +{avg:.1f} m (EMODnet, LAT chart datum). Check the coordinate.")
        return
    n = d.get("elementarySurfaces")
    ref = d.get("reference") or {}
    print(f"  seabed {-avg:.1f} m below LAT (chart datum)  [EMODnet, ~115 m grid]")
    if "min" in d and "max" in d:
        print(f"  range {-d['max']:.1f} to {-d['min']:.1f} m within this grid cell "
              f"(stdev {d.get('stdev', 0):.1f} m)")
    if ref.get("identifier"):
        print(f"  source: survey {ref['identifier']}" + (f", {n} soundings in this cell" if n else ""))
        if ref.get("metadata_url"):
            print(f"  {ref['metadata_url']}")
    else:
        print(f"  source: interpolated, no cataloged survey behind this cell"
              + (f" ({n} soundings)" if n else ""))
    if d.get("interpolationType"):
        print("  note: this point fell between grid nodes and was interpolated")


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("lat", type=float)
    p.add_argument("lon", type=float)
    a = p.parse_args()

    print(f"{a.lat}, {a.lon}")
    d = emodnet(a.lat, a.lon)
    if d is None:
        sys.exit("  EMODnet has no coverage at this point.")
    print_emodnet(d)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Seabed depth at a coordinate from EMODnet Bathymetry, with a GEBCO fallback.

  emodnet_depth.py LAT LON            depth below LAT, EMODnet's survey-backed grid, GEBCO on no coverage
  emodnet_depth.py LAT LON --gebco    skip straight to the global GEBCO grid

"""
import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

EMODNET_URL = "https://rest.emodnet-bathymetry.eu/depth_sample"
GEBCO_URL = "https://api.opentopodata.org/v1/gebco2020"


def emodnet(lat, lon):
    """Return the raw depth_sample dict, or None if EMODnet has no coverage at this point."""
    geom = f"POINT({lon} {lat})"
    url = EMODNET_URL + "?" + urllib.parse.urlencode({"geom": geom})
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            if r.status == 204:
                return None
            return json.load(r)
    except urllib.error.HTTPError as e:
        if e.code == 204:
            return None
        raise RuntimeError(f"EMODnet request failed ({e.code} {e.reason})")
    except urllib.error.URLError as e:
        raise RuntimeError(f"EMODnet request failed ({e.reason})")


def gebco(lat, lon):
    """Return the GEBCO_2024 elevation (m, signed) at this point via OpenTopoData."""
    url = GEBCO_URL + "?" + urllib.parse.urlencode({"locations": f"{lat},{lon}"})
    with urllib.request.urlopen(url, timeout=30) as r:
        d = json.load(r)
    res = d["results"][0]
    if res.get("elevation") is None:
        raise RuntimeError("GEBCO returned no elevation for this point")
    return res["elevation"]


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


def print_gebco(elev):
    if elev >= 0:
        print(f"  ABOVE WATER: +{elev:.1f} m (GEBCO_2024, ~450 m grid). Check the coordinate.")
        return
    print(f"  seabed {-elev:.1f} m below sea level (approx.)  [GEBCO_2024, ~450 m grid, global]")


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("lat", type=float)
    p.add_argument("lon", type=float)
    p.add_argument("--gebco", action="store_true",
                   help="skip EMODnet and use the coarser global GEBCO grid directly")
    a = p.parse_args()

    print(f"{a.lat}, {a.lon}")

    if not a.gebco:
        try:
            d = emodnet(a.lat, a.lon)
        except RuntimeError as e:
            print(f"  EMODnet unavailable: {e}")
            d = None
        if d is not None:
            print_emodnet(d)
            return
        print("  EMODnet: no coverage at this point, falling back to GEBCO")

    try:
        elev = gebco(a.lat, a.lon)
    except (RuntimeError, urllib.error.URLError, KeyError, IndexError) as e:
        sys.exit(f"  GEBCO request failed ({e}); no depth available for this point")
    print_gebco(elev)


if __name__ == "__main__":
    main()

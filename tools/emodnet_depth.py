#!/usr/bin/env python3
"""Seabed depth at a coordinate from EMODnet Bathymetry, with a global GEBCO fallback.
Metric (metres).

  emodnet_depth.py LAT LON            depth below LAT (chart datum), EMODnet's survey-backed grid
  emodnet_depth.py LAT LON --gebco    skip straight to the coarser global GEBCO grid

EMODnet Bathymetry blends real multibeam and hydrographic survey soundings (SeaDataNet CDI
catalogued) into a 1/16 arc-minute grid, about 115 m at low latitudes: coarse next to a reef
terrace or a channel, but backed by an actual surveyed sounding where one exists, which the
response's own `reference` and `elementarySurfaces` fields disclose, so you can tell a real
survey cell from an interpolated gap-filled one. Coverage runs beyond continental Europe
wherever a contributing survey happens to reach, but it is not a global product; a point with
no survey behind it returns empty, and this tool then falls back to GEBCO_2024, the IHO/IOC's
global bathymetric grid at 15 arc-second (~450 m) resolution, served through OpenTopoData.
GEBCO covers everywhere but resolves nothing finer than that grid, and can misread a point near
a narrow shelf, a reef edge, or a coastline as land, or as a different depth than the water
actually dived. Neither of these is a substitute for a real chart or an in-water check.

Vertical datum: EMODnet reports depth below LAT (Lowest Astronomical Tide, the IHO chart
datum used on nautical charts); GEBCO's grid is referenced close to mean sea level. Neither is
MLLW, and the two are not each other; do not mix a figure from here with a region's own fixed
datum without converting first, and never mix an EMODnet figure with a GEBCO one as if they
were on the same reference. Positive means the point is on land.
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

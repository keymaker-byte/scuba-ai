#!/usr/bin/env python3
"""Seabed depth at a coordinate from the global GEBCO grid, served by OpenTopoData.

  gebco_depth.py LAT LON    elevation from GEBCO_2020, ~450 m grid, anywhere on Earth
"""
import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

DATASET = "gebco2020"
GEBCO_URL = f"https://api.opentopodata.org/v1/{DATASET}"


def gebco(lat, lon):
    """Return the GEBCO elevation (m, signed) at this point. Exits on any failure."""
    url = GEBCO_URL + "?" + urllib.parse.urlencode({"locations": f"{lat},{lon}"})
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            d = json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"GEBCO request failed ({e.code} {e.reason})\n  {url}")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        sys.exit(f"GEBCO request failed ({getattr(e, 'reason', e)})\n  {url}")
    except ValueError:
        sys.exit(f"OpenTopoData answered with something other than JSON\n  {url}")
    try:
        if d.get("status") != "OK":
            raise ValueError(d.get("error") or d.get("status"))
        elev = d["results"][0]["elevation"]
    except (KeyError, IndexError, TypeError, ValueError) as e:
        sys.exit(f"GEBCO request failed ({e})\n  {url}")
    if elev is None:
        sys.exit(f"GEBCO returned no elevation for this point\n  {url}")
    return elev


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("lat", type=float)
    p.add_argument("lon", type=float)
    a = p.parse_args()

    print(f"{a.lat}, {a.lon}")
    elev = gebco(a.lat, a.lon)
    if elev >= 0:
        print(f"  ABOVE WATER: +{elev:.1f} m (GEBCO_2020, ~450 m grid). Check the coordinate.")
        return
    print(f"  seabed {-elev:.1f} m below mean sea level  [GEBCO_2020, ~450 m grid]")


if __name__ == "__main__":
    main()

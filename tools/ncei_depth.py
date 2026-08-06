#!/usr/bin/env python3
"""Seabed depth at a coordinate from the NOAA NCEI coastal DEM. Metric (metres).

  ncei_depth.py LAT LON                     depth in the DEM tile's own datum (usually NAVD88)
  ncei_depth.py LAT LON --mllw              also convert to depth below MLLW via NOAA VDatum
  ncei_depth.py LAT LON --mllw --region R   pick the VDatum region explicitly

For writing a site file: a fast, ~3 m resolution seabed depth at the dive-site coordinate,
finer than a nautical chart's scattered soundings between wide contours, and a check that the
point is underwater at a divable depth at all. The DEM returns NAVD88 (~mean sea level here);
site files quote depth below MLLW, so --mllw runs the datum conversion. A separate NOAA
service from the currents API. Positive elevation means the point is on land.

VDatum's transform is tiled by geographic region, and it will not infer one from the
coordinate; the wrong region (or its own "contiguous" default, off the coast) fails with an
opaque "Uncaught error" rather than a useful message. Pick --region for wherever the
coordinate actually is. Valid values, per NOAA's API docs (vdatum.noaa.gov/docs/services.html):

  contiguous            Contiguous United States (Atlantic/Gulf coasts; VDatum's own default)
  westcoast             US West Coast (Washington, Oregon, California)
  ak                    Alaska
  seak                  Southeast Alaska (tidal)
  hi                    Hawaii
  prvi                  Puerto Rico and US Virgin Islands
  gcnmi                 Guam and the Commonwealth of the Northern Mariana Islands
  as                    American Samoa
  chesapeak_delaware    Chesapeake and Delaware Bay
  wgom                  West Gulf of Mexico
  sgi / spi / sli       Saint George Island / Saint Paul Island / Saint Lawrence Island

Some regions additionally require a specific target horizontal frame for a tidal target datum
(e.g. westcoast wants IGS14); VDatum states the required frame in its error message when this
applies, and this tool retries once with whatever frame it names, so that quirk is transparent
to the caller.

Default region: `ncei_depth.default_region` in tool-config.json, or VDatum's own default if unset.
"""
import argparse
import json
import math
import os
import re
import sys
import urllib.parse
import urllib.request

DEM_URL = ("https://gis.ngdc.noaa.gov/arcgis/rest/services/DEM_mosaics/DEM_all/"
           "ImageServer/identify")
VDATUM_URL = "https://vdatum.noaa.gov/vdatumweb/api/convert"
MDAPI = "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations.json"
DATUMS_URL = "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations/{}/datums.json"


def _cfg(key, default=None):
    """Read this tool's section of tool-config.json; missing file or key -> default."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        with open(os.path.join(root, "tool-config.json")) as f:
            return json.load(f).get("ncei_depth", {}).get(key, default)
    except (OSError, ValueError):
        return default


def _user_agent():
    """Contact email for API User-Agents comes from tool-config.json (ncei_depth.user_agent_email)."""
    email = _cfg("user_agent_email")
    return f"dive-planning ({email})" if email else "dive-planning"


UA = _user_agent()

# VerticalDatum strings the DEM reports -> VDatum frame codes for the source datum.
VDATUM_FRAME = {"NAVD 88": "NAVD88", "MHW": "MHW", "MHHW": "MHHW",
                "MSL": "LMSL", "Sea Level": "LMSL", "MLLW": "MLLW"}
# Last-resort NAVD88-above-MLLW offset. Puget Sound spans ~0.1 m (Strait of Juan de Fuca)
# to ~0.7 m (south Sound); the real value comes from VDatum or a tide station's datums,
# both tried first. This flat value is only for when neither service answers.
NOMINAL_NAVD88_ABOVE_MLLW = 0.6


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.load(r)


def dem(lat, lon):
    """Return dict: elevation (m, signed), depth (m below tile datum), datum, source, res_m."""
    q = {"geometry": f"{lon},{lat}", "geometryType": "esriGeometryPoint", "sr": "4326",
         "returnGeometry": "false", "f": "json"}
    d = _get(DEM_URL + "?" + urllib.parse.urlencode(q))
    try:
        elev = float(d["value"])
    except (KeyError, ValueError, TypeError):
        sys.exit(f"No DEM data at {lat}, {lon} (value: {d.get('value')!r}). "
                 f"Point may be outside coastal DEM coverage.")
    top = d["catalogItems"]["features"][0]["attributes"]
    res = top.get("CellsizeArcseconds")
    return {
        "elev": elev,
        "depth": -elev,
        "datum": top.get("VerticalDatum"),
        "source": top.get("Name", "?"),
        "res_m": round(res * 30.9, 1) if res else None,
    }


def to_mllw(lat, lon, elev, datum, region=None):
    """Convert an elevation at (lat, lon) from its DEM datum to MLLW via VDatum; return the
    depth below MLLW (m). Raises RuntimeError with a reason if VDatum cannot answer.

    region picks VDatum's geographic tile (see the module docstring for valid values); pass
    the one that actually covers (lat, lon), since VDatum will not infer it and its own
    "contiguous" default fails silently-ish off the Atlantic/Gulf coasts."""
    frame = VDATUM_FRAME.get(datum)
    if not frame:
        raise RuntimeError(f"no VDatum frame mapping for DEM datum {datum!r}")
    q = {"s_x": lon, "s_y": lat, "s_z": elev, "s_coor": "geo",
         "s_h_frame": "NAD83_2011", "s_v_frame": frame, "s_v_unit": "m",
         "t_v_frame": "MLLW", "t_v_unit": "m"}
    if region:
        q["region"] = region
    try:
        d = _get(VDATUM_URL + "?" + urllib.parse.urlencode(q))
        # Some regions require a specific target horizontal frame for a tidal target datum;
        # VDatum names the frame it wants in the error, so retry once with that frame rather
        # than hardcoding a per-region table that would drift out of date.
        if d.get("errorCode") is not None:
            m = re.search(r"Target Horizontal Frame should be (\S+)", d.get("message", ""))
            if m:
                d = _get(VDATUM_URL + "?" + urllib.parse.urlencode({**q, "t_h_frame": m.group(1)}))
    except Exception as e:
        raise RuntimeError(f"VDatum request failed ({e})")
    # VDatum has used a few key names for the transformed height across versions.
    for k in ("t_z", "tar_z", "t_z_value"):
        if k in d and d[k] not in (None, "", "-999999"):
            try:
                return -float(d[k])
            except (ValueError, TypeError):
                pass
    raise RuntimeError(f"VDatum returned no usable height ({d})")


def station_offset(lat, lon):
    """NAVD88-above-MLLW offset (m) from the nearest tide station that publishes both datums,
    with (offset, station_name, dist_km). Subordinate stations often omit NAVD88, so this
    walks outward from the point until a station carries the geodetic tie. None if none do."""
    sts = _get(MDAPI + "?type=tidepredictions")["stations"]
    scale = math.cos(math.radians(lat))
    sts.sort(key=lambda s: ((s["lat"] - lat) * 60) ** 2 + ((s["lng"] - lon) * 60 * scale) ** 2)
    for s in sts[:20]:
        try:
            d = _get(DATUMS_URL.format(s["id"]))
        except Exception:
            continue
        k = 0.3048 if d.get("units") == "feet" else 1.0
        m = {x["name"]: x["value"] for x in (d.get("datums") or [])}
        if m.get("NAVD88") is not None and m.get("MLLW") is not None:
            dist = math.hypot((s["lat"] - lat) * 60, (s["lng"] - lon) * 60 * scale) * 1.852
            return (m["NAVD88"] - m["MLLW"]) * k, s["name"], dist
    return None


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("lat", type=float)
    p.add_argument("lon", type=float)
    p.add_argument("--mllw", action="store_true", help="also convert to depth below MLLW (VDatum)")
    p.add_argument("--region", default=None,
                   help="VDatum region tile for the coordinate (see module docstring for the "
                        "list); defaults to ncei_depth.default_region in tool-config.json, or VDatum's "
                        "own default if that's unset too")
    a = p.parse_args()
    region = a.region or _cfg("default_region")

    r = dem(a.lat, a.lon)
    src = f"{r['source']} (~{r['res_m']:.0f} m)" if r["res_m"] else r["source"]
    print(f"{a.lat}, {a.lon}")
    if r["elev"] >= 0:
        print(f"  ABOVE WATER: +{r['elev']:.1f} m in the DEM ({r['datum']}). Check the coordinate.")
        print(f"  source {src}")
        return
    print(f"  seabed {r['depth']:.1f} m below {r['datum']}")
    print(f"  source {src}")
    if a.mllw:
        try:
            mllw = to_mllw(a.lat, a.lon, r["elev"], r["datum"], region=region)
            print(f"  seabed {mllw:.1f} m below MLLW  (VDatum)")
            return
        except RuntimeError as e:
            print(f"  VDatum unavailable: {e}")
        so = station_offset(a.lat, a.lon) if r["datum"] == "NAVD 88" else None
        if so:
            off, name, dist = so
            print(f"  seabed {r['depth'] - off:.1f} m below MLLW  "
                  f"({name} datums, {dist:.0f} km, offset {off:.2f} m)")
        else:
            approx = r["depth"] - NOMINAL_NAVD88_ABOVE_MLLW
            print(f"  approx {approx:.1f} m below MLLW  (nominal {NOMINAL_NAVD88_ABOVE_MLLW:.1f} m "
                  f"offset; VDatum and station datums both unavailable)")


if __name__ == "__main__":
    main()

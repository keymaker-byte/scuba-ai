#!/usr/bin/env python3
"""Dive site records from Divers Atlas.

  diversatlas.py near LAT LON [--radius 2]   every site within a radius (km), nearest first
  diversatlas.py search "keystone"           fallback: sites whose name matches every term
  diversatlas.py site keystone-jetty         one site's full record

"""
import argparse
import json
import math
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

LIST_COLUMNS = "site_id,slug,name,latitude,longitude,site_type,country,region_state"


def _cfg(key, default):
    """Read this tool's section of tool-config.json; missing file or key -> default."""
    try:
        with open(Path(__file__).resolve().parent.parent / "tool-config.json") as f:
            return json.load(f).get("diversatlas", {}).get(key, default)
    except (OSError, ValueError):
        return default


def _query(table, params):
    base, key = _cfg("database_url", None), _cfg("api_key", None)
    missing = [n for n, v in (("database_url", base), ("api_key", key)) if not v or v.startswith("<")]
    if missing:
        sys.exit(f"diversatlas.{' and diversatlas.'.join(missing)} not set in tool-config.json")
    url = f"{base.rstrip('/')}/rest/v1/{table}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"apikey": key, "Authorization": f"Bearer {key}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"Divers Atlas query failed: HTTP {e.code} {e.read().decode(errors='replace')[:300]}")
    except urllib.error.URLError as e:
        sys.exit(f"Divers Atlas unreachable: {e.reason}")


def _km(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(a))


def _dist(row, near):
    if not near or row.get("latitude") is None or row.get("longitude") is None:
        return None
    return _km(near[0], near[1], float(row["latitude"]), float(row["longitude"]))


def _fmt_dist(d):
    if d is None:
        return ""
    return f"{d * 1000:.0f} m away" if d < 1 else f"{d:.1f} km away"


def _print_list(rows, near):
    rows = [r for r in rows if "(Pending Review)" not in (r.get("name") or "")]
    if near:
        rows.sort(key=lambda r: (_dist(r, near) is None, _dist(r, near) or 0))
    if not rows:
        print("no matching sites")
        return
    for r in rows:
        where = ", ".join(x for x in (r.get("region_state"), r.get("country")) if x)
        print(f"  {r['slug']}")
        print(f"    {r.get('name')}  ·  {r.get('site_type') or '?'}  ·  {where or '?'}")
        print(f"    {r.get('latitude')}, {r.get('longitude')}  {_fmt_dist(_dist(r, near))}".rstrip())


def cmd_search(a):
    params = [("select", LIST_COLUMNS), ("limit", "50")]
    params += [("name", f"ilike.*{t}*") for t in a.name.split()]
    _print_list(_query("dive_sites", params), None)


def cmd_near(a):
    lat, lon = a.lat, a.lon
    dlat = a.radius / 111.0
    dlon = a.radius / (111.0 * max(math.cos(math.radians(lat)), 0.01))
    params = [
        ("select", LIST_COLUMNS), ("limit", "200"),
        ("latitude", f"gte.{lat - dlat}"), ("latitude", f"lte.{lat + dlat}"),
        ("longitude", f"gte.{lon - dlon}"), ("longitude", f"lte.{lon + dlon}"),
    ]
    rows = [r for r in _query("dive_sites", params) if (_dist(r, (lat, lon)) or 0) <= a.radius]
    _print_list(rows, (lat, lon))


# Bookkeeping columns with nothing to say about the dive.
INTERNAL = {
    "site_id", "slug", "name", "region_id", "site_alt_id", "thumbnail_url", "cover_photo",
    "created_at", "qr_code_url", "qr_code_generated_at", "qr_code_target_url", "country_code",
    "contributor_name", "latitude", "longitude", "street_address", "city", "county",
    "zip_code", "region_state", "country", "island", "site_type", "site_subtype",
    "site_material", "description",
}
# Feet columns, each shadowed by a *_meters twin; the metre one is printed instead.
IMPERIAL = {"max_depth": "max_depth_meters", "avg_depth": "avg_depth_meters", "visibility": "visibility_meters"}
# Free-text topics: a contributor-curated *_notes (or bare) field plus its *_tips list,
# merged and deduplicated (the notes field usually repeats the first tip verbatim).
TOPICS = [
    ("points of interest", "points_of_interest", "points_of_interest_tips"),
    ("notable life", "notable_life", None),
    ("safety", "safety_notes", "safety_tips"),
    ("recent conditions", "recent_conditions", "recent_conditions_tips"),
    ("access", "accessibility_notes", "accessibility_tips"),
    ("facilities", "facilities_notes", "facilities_tips"),
    ("adaptive divers", "adaptive_divers", "adaptive_divers_tips"),
]


def _empty(v):
    return v in (None, "", [], {})


def cmd_site(a):
    rows = _query("dive_sites", [("select", "*"), ("slug", f"eq.{a.slug}")])
    if not rows:
        sys.exit(f"no site with slug '{a.slug}'; try: diversatlas.py search <name>")
    r = rows[0]
    if a.raw:
        print(json.dumps(r, indent=2, ensure_ascii=False))
        return

    print(r.get("name"))
    kind = " / ".join(x for x in (r.get("site_type"), r.get("site_subtype"), r.get("site_material")) if x)
    if kind:
        print(f"  {kind}")
    print(f"  pin {r.get('latitude')}, {r.get('longitude')}")
    addr = ", ".join(str(r[k]) for k in ("street_address", "city", "county", "region_state", "zip_code", "country") if not _empty(r.get(k)))
    if addr:
        print(f"  {addr}")
    if not _empty(r.get("description")):
        print(f"\n  {r['description'].strip()}")

    shown = set(INTERNAL) | set(IMPERIAL)
    for label, notes, tips in TOPICS:
        shown.update(x for x in (notes, tips) if x)
        tip_rows = r.get(tips) or []
        if any(isinstance(t, dict) and t and "tip" not in t for t in tip_rows):
            sys.exit(f"Divers Atlas {tips} entries no longer carry a 'tip' field; the schema moved, see --raw")
        seen, lines = set(), []
        for text, date in [(r.get(notes), None)] + [(t.get("tip"), t.get("date_added")) for t in tip_rows if t.get("approved", True)]:
            text = (text or "").strip()
            if text and text.lower() not in seen:
                seen.add(text.lower())
                lines.append(f"{text}  ({str(date)[:10]})" if date else text)
        if lines:
            print(f"\n  {label}")
            for line in lines:
                print(f"    - {line}")

    rest = []
    for k, v in r.items():
        if k in shown:
            continue
        if _empty(v):
            twin = next((ft for ft, m in IMPERIAL.items() if m == k), None)
            if twin is None or _empty(r.get(twin)):
                continue
            v, k = f"{r[twin]} (feet only, unconverted)", twin
        if k.endswith("_meters"):
            v = f"{float(v):.1f} m"
        elif isinstance(v, (dict, list)):
            v = json.dumps(v, ensure_ascii=False)
        rest.append(f"    {k}: {v}")
    if rest:
        print("\n  details")
        print("\n".join(rest))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("search", help="fallback: sites whose name matches every term")
    s.add_argument("name")
    s.set_defaults(func=cmd_search)

    n = sub.add_parser("near", help="every site within a radius of a coordinate")
    n.add_argument("lat", type=float)
    n.add_argument("lon", type=float)
    n.add_argument("--radius", type=float, default=2.0, help="km (default 2)")
    n.set_defaults(func=cmd_near)

    t = sub.add_parser("site", help="one site's full record")
    t.add_argument("slug")
    t.add_argument("--raw", action="store_true", help="the record as JSON, empty fields included")
    t.set_defaults(func=cmd_site)

    a = ap.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()

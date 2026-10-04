#!/usr/bin/env python3
"""Dive site pages from Dive Atlas, a community dive site wiki.

  diveatlas.py near LAT LON [--radius 2]   every site within a radius (km), nearest first
  diveatlas.py search "seacrest"           fallback: sites whose title matches every term
  diveatlas.py site "Seacrest Cove 2"      one site's page, as plain text

"""
import argparse
import json
import math
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://diveatlas.org/api.php"
CACHE = Path(__file__).parent / "db" / "diveatlas_index.json"
FT = 0.3048


def _cfg(key, default):
    """Read this tool's section of tool-config.json; missing file or key -> default."""
    try:
        with open(Path(__file__).resolve().parent.parent / "tool-config.json") as f:
            return json.load(f).get("diveatlas", {}).get(key, default)
    except (OSError, ValueError):
        return default


CACHE_HOURS = _cfg("cache_hours", 1)
_email = _cfg("user_agent_email", None)
USER_AGENT = f"dive-planning ({_email})" if _email else "dive-planning"


def _api(params):
    url = f"{API}?{urllib.parse.urlencode({**params, 'format': 'json'})}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read()
    except urllib.error.HTTPError as e:
        sys.exit(f"Dive Atlas request failed: HTTP {e.code}")
    except urllib.error.URLError as e:
        sys.exit(f"Dive Atlas unreachable: {e.reason}")
    try:
        d = json.loads(body)
    except ValueError:
        # An HTML answer here is the site's anti-bot challenge or an outage page, never data.
        sys.exit("Dive Atlas returned a page instead of API data (challenge or outage); stop and report it")
    if "error" in d:
        sys.exit(f"Dive Atlas API error: {d['error'].get('info', d['error'])}")
    return d


def _index():
    """Every dive site's title, region, access type and coordinate, cached."""
    if CACHE.exists() and time.time() - CACHE.stat().st_mtime < CACHE_HOURS * 3600:
        return json.loads(CACHE.read_text())
    query = "[[Category:Dive sites]]|?Has coordinates|?Part of|?Has access type|?Has site type|limit=1000"
    res = _api({"action": "ask", "query": query}).get("query", {}).get("results")
    if res is None:
        sys.exit("Dive Atlas index query returned no results block; the semantic schema may have moved")
    sites = []
    for title, v in res.items():
        p = v.get("printouts", {})
        coord = (p.get("Has coordinates") or [None])[0]
        part = (p.get("Part of") or [{}])[0]
        sites.append({
            "title": title,
            "region": part.get("fulltext") if isinstance(part, dict) else part,
            "access": ", ".join(str(x.get("fulltext", x) if isinstance(x, dict) else x) for x in p.get("Has access type") or []),
            "lat": coord.get("lat") if coord else None,
            "lon": coord.get("lon") if coord else None,
        })
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(sites))
    return sites


def _km(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(a))


def _fmt_dist(d):
    return f"{d * 1000:.0f} m away" if d < 1 else f"{d:.1f} km away"


def _print_list(rows):
    if not rows:
        print("no matching sites")
        return
    for s, d in rows:
        print(f"  {s['title']}")
        print(f"    {s.get('region') or '?'}  ·  {s.get('access') or '?'}")
        if s.get("lat") is None:
            print("    no coordinate on the page")
        else:
            print(f"    {s['lat']}, {s['lon']}  {_fmt_dist(d) if d is not None else ''}".rstrip())


def cmd_near(a):
    rows = [(s, _km(a.lat, a.lon, s["lat"], s["lon"])) for s in _index() if s.get("lat") is not None]
    _print_list(sorted([r for r in rows if r[1] <= a.radius], key=lambda r: r[1]))


def cmd_search(a):
    terms = a.name.lower().split()
    _print_list([(s, None) for s in sorted(_index(), key=lambda s: s["title"]) if all(t in s["title"].lower() for t in terms)])


def _depth_m(raw):
    """'0-45ft' -> '0 to 14 m', '5-115m' -> '5 to 115 m'; anything else is returned as written."""
    m = re.fullmatch(r"\s*([\d.]+)\s*(?:-|to)?\s*([\d.]+)?\s*(ft|feet|m|meters|metres)?\s*", raw or "", re.I)
    if not m or not m.group(3):
        return raw
    nums = [float(x) for x in m.group(1, 2) if x]
    if m.group(3).lower().startswith("f"):
        nums = [n * FT for n in nums]
    return " to ".join(f"{n:.0f}" for n in nums) + " m"


def _plain(wikitext):
    t = wikitext
    t = re.sub(r"<!--.*?-->", "", t, flags=re.S)
    t = re.sub(r"<ref[^>/]*/>|<ref[^>]*>.*?</ref>", "", t, flags=re.S)
    t = re.sub(r"<gallery.*?</gallery>|<references\s*/>", "", t, flags=re.S | re.I)
    for _ in range(3):  # nested templates, innermost first
        t = re.sub(r"\{\{[^{}]*\}\}", "", t)
    t = re.sub(r"\[\[(?:File|Image|Category):(?:[^\[\]]|\[\[[^\]]*\]\]|\[[^\]]*\])*\]\]", "", t, flags=re.I)
    t = re.sub(r"\[\[([^|\]]+)\|([^\]]+)\]\]", r"\2", t)
    t = re.sub(r"\[\[([^\]]+)\]\]", r"\1", t)
    t = re.sub(r"\[(https?://\S+)\s+([^\]]+)\]", r"\2 <\1>", t)
    t = re.sub(r"\[(https?://[^\]\s]+)\]", r"<\1>", t)
    t = re.sub(r"'''?|<br\s*/?>", "", t)
    return t


def cmd_site(a):
    title = a.title.replace("_", " ")
    d = _api({"action": "parse", "page": title, "prop": "wikitext|categories", "redirects": 1})
    p = d["parse"]
    text = p["wikitext"]["*"]
    cats = [c["*"].replace("_", " ") for c in p.get("categories", [])]

    props = {}
    m = re.search(r"\{\{\s*Dive site/properties(.*?)\}\}", text, re.S)
    if m:
        for k, v in re.findall(r"\|\s*(\w+)\s*=\s*([^|]*)", m.group(1)):
            if v.strip():
                props[k] = v.strip()

    print(p["title"])
    if "coordinates" in props:
        print(f"  pin {props['coordinates']}")
    facts = [
        ("region", props.get("region")),
        ("access", props.get("site_access_type")),
        ("water", props.get("type")),
        ("depth", _depth_m(props["depth_range"]) if "depth_range" in props else None),
        ("level", ", ".join(c for c in cats if c in ("Beginner", "Intermediate", "Advanced", "Technical"))),
    ]
    for k, v in facts:
        if v:
            print(f"  {k}: {v}")
    if any(c.lower() == "needs love" for c in cats):
        print("  the wiki flags this page as incomplete")

    # Split into the lead (before the first heading) and the sections, then drop empty ones.
    parts = re.split(r"^(==+)\s*(.*?)\s*\1\s*$", _plain(text), flags=re.M)
    blocks = [("", parts[0])] + [(parts[i + 1], parts[i + 2]) for i in range(1, len(parts) - 2, 3)]
    printed = False
    for heading, body in blocks:
        body = "\n".join(line.rstrip() for line in body.strip().splitlines())
        body = re.sub(r"\n{3,}", "\n\n", body).strip()
        if not body or heading.lower() in ("notes", "references", "gallery"):
            continue
        print(f"\n  {heading.lower()}" if heading else "")
        for line in body.splitlines():
            print(f"    {line}" if line else "")
        printed = True
    if not printed:
        print("\n  stub page: no write-up beyond the properties above")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    n = sub.add_parser("near", help="every site within a radius of a coordinate")
    n.add_argument("lat", type=float)
    n.add_argument("lon", type=float)
    n.add_argument("--radius", type=float, default=2.0, help="km (default 2)")
    n.set_defaults(func=cmd_near)

    s = sub.add_parser("search", help="fallback: sites whose title matches every term")
    s.add_argument("name")
    s.set_defaults(func=cmd_search)

    t = sub.add_parser("site", help="one site's page, as plain text")
    t.add_argument("title", help="page title, spaces or underscores")
    t.set_defaults(func=cmd_site)

    a = ap.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()

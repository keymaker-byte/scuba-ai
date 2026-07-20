#!/usr/bin/env python3
"""Recent visibility reports from pnwdiving.com. Metric (m).

Reads ONLY the "Recent Dive Reports" summary table that pnwdiving server-renders on its
home page — an allowed, sitemapped path. The full report bodies live under /*/reports,
which their robots.txt disallows; we do not touch that, and this tool must never be
pointed at it. Read full reports in a browser like a human.

Reports are posted in feet; we convert to metres.

  viz                          recent reports, freshest first
  viz --site skyline           filter by site
  viz --max-age 4              only reports from the last N days
  viz --refresh                bypass the local cache
"""
import argparse
import html as H
import json
import re
import sys
import time
import urllib.request
from datetime import date, timedelta
from pathlib import Path

HOME = "https://pnwdiving.com/"
CACHE = Path(__file__).parent / ".cache" / "pnwdiving_home.html"


def _cfg(key, default):
    """Read this tool's section of tool-config.json; missing file or key -> default."""
    try:
        with open(Path(__file__).resolve().parent.parent / "tool-config.json") as f:
            return json.load(f).get("pnwdiving_viz", {}).get(key, default)
    except (OSError, ValueError):
        return default


CACHE_HOURS = _cfg("cache_hours", 6)
FT = 0.3048

# Qualitative words the community uses, worst to best.
QUALITY = ["chunky", "silty", "murky", "hazy", "clear"]


def fetch(refresh=False):
    if not refresh and CACHE.exists():
        age_h = (time.time() - CACHE.stat().st_mtime) / 3600.0
        if age_h < CACHE_HOURS and CACHE.stat().st_size > 1000:
            return CACHE.read_text(encoding="utf-8", errors="replace")
    req = urllib.request.Request(HOME, headers={"User-Agent": "personal dive planning (1 req)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        h = r.read().decode("utf-8", errors="replace")
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(h, encoding="utf-8")
    return h


def parse(h):
    i = h.lower().find("recent dive report")
    if i < 0:
        sys.exit("Could not find the Recent Dive Reports table — the page layout may have changed.")
    seg = h[i:]
    end = seg.lower().find("</table>")
    seg = seg[: end if end > 0 else 12000]

    rows = []
    for tr in re.findall(r"<tr[^>]*mat-row.*?</tr>", seg, re.S | re.I):
        cells = [
            re.sub(r"\s+", " ", H.unescape(re.sub(r"<[^>]+>", "", c))).strip()
            for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S | re.I)
        ]
        if len(cells) >= 3:
            rows.append({"site": cells[0], "viz": cells[1], "updated": cells[2]})
    return rows


def age_days(s):
    s = s.lower().strip()
    if "today" in s or "hour" in s or "just" in s:
        return 0
    m = re.search(r"(\d+)\s*day", s)
    if m:
        return int(m.group(1))
    m = re.search(r"(\d+)\s*week", s)
    if m:
        return int(m.group(1)) * 7
    return 99


def metres(viz):
    """Convert the feet figures in a report to metres, keeping the surrounding words."""

    def rng(m):
        a, b = int(m.group(1)), int(m.group(2))
        return f"{a * FT:.1f}–{b * FT:.1f} m"

    def plus(m):
        return f"{int(m.group(1)) * FT:.1f}+ m"

    def lt(m):
        return f"<{int(m.group(1)) * FT:.1f} m"

    def one(m):
        return f"{int(m.group(1)) * FT:.1f} m"

    v = viz
    v = re.sub(r"(\d+)\s*-\s*(\d+)\s*(?:feet|ft|')", rng, v, flags=re.I)
    v = re.sub(r"(\d+)\s*\+\s*(?:feet|ft|')", plus, v, flags=re.I)
    v = re.sub(r"<\s*(\d+)\s*(?:feet|ft|')", lt, v, flags=re.I)
    v = re.sub(r"(\d+)\s*(?:feet|ft|')", one, v, flags=re.I)
    return v


def quality(viz):
    for q in QUALITY:
        if q in viz.lower():
            return q
    return ""


def main():
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--site", help="substring match on site name")
    p.add_argument("--max-age", type=int, default=99, metavar="DAYS")
    p.add_argument("--refresh", action="store_true")
    p.add_argument("--raw", action="store_true", help="keep feet as reported, no conversion")
    a = p.parse_args()

    rows = parse(fetch(a.refresh))
    today = date.today()

    rows = [r for r in rows if age_days(r["updated"]) <= a.max_age]
    if a.site:
        rows = [r for r in rows if a.site.lower() in r["site"].lower()]
    if not rows:
        sys.exit("No matching reports.")

    print(f"pnwdiving — recent visibility  ({len(rows)} sites, as of {today})\n")
    for r in sorted(rows, key=lambda r: age_days(r["updated"])):
        d = age_days(r["updated"])
        when = (today - timedelta(days=d)).isoformat() if d < 99 else "?"
        stale = "  (stale)" if d > 7 else ""
        viz = r["viz"] if a.raw else metres(r["viz"])
        print(f"  {r['site'][:30]:<30} {when}{stale}")
        print(f"  {'':<30} {viz}\n")

    print("Summary only — full reports are at pnwdiving.com/visibility, in a browser.")
    print("Viz is informational: it sets torch/reel, not go/no-go. Current does that.")


if __name__ == "__main__":
    main()

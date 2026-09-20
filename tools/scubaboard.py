#!/usr/bin/env python3
"""Recent threads from a ScubaBoard forum, via that forum's own RSS feed.

  scubaboard.py list                                catalogue of covered forums
  scubaboard.py retrieve pacific_northwest           recent threads, newest first
  scubaboard.py retrieve technical_diving --limit 5  cap how many are printed
  scubaboard.py search cave_diving "sump,line"       only threads matching all keywords

ScubaBoard runs on XenForo, which publishes a live RSS feed for every forum at
/community/forums/<slug>.<id>/index.rss; each feed is a rolling window of that forum's
most recent ~20 threads (title, author, link, publish time, opening-post excerpt), no
older history and no reply bodies. Covers two kinds of forum:

  region  a place: a country, a coastline, a dive destination (e.g. Pacific Northwest,
          Bonaire, Cozumel). Use this for local diving signal: a closed gate, a bloom
          that just rolled in, a fee change, whether anyone got in this weekend, the
          kind of thing no prediction tool carries.
  topic   a subject, independent of place: training level, a technical discipline, a
          gear category, safety, classifieds. Use this for gear research or general
          chatter that isn't tied to a coastline.

Neither list is the whole site: ScubaBoard runs several hundred forums, and manufacturer
fan forums, dive clubs, and yearly "invasion" trip forums are left out as noise. `list`
prints what's actually covered. To add a forum, find its page on scubaboard.com and read
the slug and id out of its URL; the feed path is always .../index.rss from there, and a
forum's id is stable even if ScubaBoard later renames its slug.

Community content: unmoderated, anecdotal, and only as current as the last ~20 threads in
that forum. Good for "what's being talked about right now," not a citable fact.
"""
import argparse
import html
import re
import sys
import urllib.error
import urllib.request
from email.utils import parsedate_to_datetime

import feedparser

USER_AGENT = "dive-planning"

# name, slug.id -- taken straight from each forum's own URL on scubaboard.com.
REGIONS = {
    "pacific_northwest": ("Pacific Northwest", "pacific-northwest.81"),
    "california": ("California", "california.61"),
    "florida": ("Florida", "florida.55"),
    "hawaii": ("Hawai'i", "hawaii.291"),
    "texas": ("Texas", "texas.34"),
    "alaska": ("Alaska", "alaska.522"),
    "rocky_mountain": ("Rocky Mountain Region", "rocky-mountain-region.400"),
    "southwestern_us": ("Southwestern Region (US)", "southwestern-region.292"),
    "great_lakes": ("Great Lakes", "great-lakes-wrecking-crew.188"),
    "midwest_us": ("Mid-West Region (US)", "mid-west-region.312"),
    "new_england": ("New England", "new-england.56"),
    "mid_atlantic": ("Mid-Atlantic States", "mid-atlantic-states.59"),
    "north_carolina": ("North Carolina", "north-carolina.73"),
    "ontario": ("Ontario", "ontario.54"),
    "eastern_canada": ("Eastern Canada", "eastern-canada.171"),
    "western_canada": ("Western Canada", "western-canada.176"),
    "northern_canada": ("Northern Canada", "northern-canada.177"),
    "bonaire": ("Bonaire", "bonaire.562"),
    "curacao": ("Curaçao", "curacao.1091"),
    "bahamas": ("Bahamas", "bahamas.563"),
    "bermuda": ("Bermuda", "bermuda.565"),
    "cayman_islands": ("Cayman Islands", "cayman-islands.453"),
    "cozumel": ("Cozumel", "cozumel.208"),
    "belize": ("Belize", "belize.439"),
    "bay_islands": ("Bay Islands (Honduras)", "bay-islands.533"),
    "south_america": ("South America", "south-america.529"),
    "general_europe": ("General Europe", "general-europe.477"),
    "western_europe": ("Western Europe", "western-europe.25"),
    "british_isles": ("British Isles", "british-isles.57"),
    "scandinavia": ("Scandinavia", "scandinavia.472"),
    "central_eastern_europe": ("Central & Eastern Europe", "central-eastern-europe.471"),
    "africa": ("Africa", "africa.464"),
    "red_sea": ("Red Sea", "red-sea.465"),
    "the_gulf": ("The Gulf", "the-gulf.466"),
    "general_asia": ("General Asia", "general-asia.22"),
    "indonesia": ("Indonesia", "indonesia.575"),
    "philippines": ("Philippines", "philippine-paradise-divers.347"),
    "thailand": ("Thailand", "thailand.526"),
    "maldives": ("Maldives", "maldives.891"),
    "japan": ("Japan", "japan.307"),
    "malaysia_singapore": ("Malaysia & Singapore", "malaysia-singapore.495"),
    "greater_china": ("Greater China", "greater-china.772"),
    "taiwan": ("Taiwan", "taiwan.880"),
    "south_korea": ("South Korea", "south-korea.1153"),
    "australia": ("Australia", "australia.570"),
    "new_zealand": ("New Zealand", "new-zealand.564"),
    "pacific_islands": ("The Pacific Islands", "the-pacific-islands.540"),
}

TOPICS = {
    "new_divers": ("New Divers & Those Considering Diving", "new-divers-those-considering-diving.6"),
    "basic_scuba": ("Basic Scuba", "basic-scuba.1053"),
    "advanced_scuba": ("Advanced Scuba", "advanced-scuba.664"),
    "snorkeling_freediving": ("Snorkeling & Freediving", "snorkeling-freediving.342"),
    "technical_diving": ("Technical Diving", "technical-diving.43"),
    "cave_diving": ("Cave Diving", "cave-diving.45"),
    "wreck_diving": ("Wreck Diving", "wreck-diving.46"),
    "rebreather_diving": ("Rebreather Diving", "rebreather-diving.14"),
    "sidemount_diving": ("Sidemount Diving", "sidemount-diving.799"),
    "diving_medicine": ("Diving Physics, Physiology, & Medicine", "diving-physics-physiology-medicine.94"),
    "accidents_incidents": ("Accidents, Incidents, & Near Misses", "accidents-incidents-near-misses.286"),
    "general_equipment": ("General Scuba Equipment Discussions", "general-scuba-equipment-discussions.13"),
    "bcds_weights": ("Buoyancy Compensators (BC's) & Weight Systems", "buoyancy-compensators-bcs-weight-systems.18"),
    "computers_gauges": ("Computers, Gauges, Watches & Analyzers", "computers-gauges-watches-analyzers.17"),
    "regulators": ("Regulators", "regulators.16"),
    "exposure_suits": ("Exposure Suits", "exposure-suits.30"),
    "fins_masks_snorkels": ("Fins, Masks & Snorkels", "fins-masks-snorkels.31"),
    "tanks_valves": ("Tanks, Valves & Bands", "tanks-valves-bands.32"),
    "dpv": ("Diver Propulsion Vehicles (DPV)", "diver-propulsion-vehicles-dpv.334"),
    "lights": ("Lights", "lights.65"),
    "underwater_photography": ("Underwater Photography", "underwater-photography.3"),
    "underwater_videography": ("Underwater Videography", "underwater-videography.343"),
    "classifieds": ("ScubaBoard's Classified Section", "scubaboards-classified-section.220"),
}

# key -> (kind, name, slug.id)
FORUMS = {
    **{k: ("region", *v) for k, v in REGIONS.items()},
    **{k: ("topic", *v) for k, v in TOPICS.items()},
}


def feed_url(source):
    return f"https://www.scubaboard.com/community/forums/{FORUMS[source][2]}/index.rss"


def clean_html(raw_html):
    if not raw_html:
        return ""
    return html.unescape(re.sub(r"<[^>]+>", "", raw_html)).strip()


def when(published):
    """RSS pubDate -> 'YYYY-MM-DD HH:MM UTC'; the raw string if it won't parse."""
    try:
        dt = parsedate_to_datetime(published)
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    except (TypeError, ValueError):
        return published


def fetch_threads(source):
    url = feed_url(source)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            xml_data = response.read()
    except urllib.error.URLError as e:
        sys.exit(f"Could not reach {url}: {e}")

    feed = feedparser.parse(xml_data)
    if feed.bozo and not feed.entries:
        sys.exit(f"{url} did not parse as a feed ({feed.bozo_exception}). "
                 f"The forum may have been renamed or removed; check its URL on scubaboard.com.")

    return [
        {
            "title": clean_html(entry.get("title", "")),
            "author": clean_html(entry.get("author", "Unknown")),
            "link": entry.get("link", ""),
            "published": when(entry.get("published", "")),
            "summary": clean_html(entry.get("summary", "")),
        }
        for entry in feed.entries
    ]


def search_threads(threads, query):
    keywords = [kw.strip().lower() for kw in query.split(",") if kw.strip()]
    if not keywords:
        sys.exit("search requires at least one keyword")
    return [
        t for t in threads
        if all(kw in f"{t['title']} {t['summary']}".lower() for kw in keywords)
    ]


def print_threads(source, threads, limit):
    _, name, _ = FORUMS[source]
    shown = threads[:limit]
    print(f"{name}  ({len(shown)} of {len(threads)} threads)\n")
    if not shown:
        print("  no matching threads")
        return
    for t in shown:
        print(f"  {t['title']}")
        print(f"    {t['author']}  ·  {t['published']}")
        summary = t["summary"]
        if len(summary) > 220:
            summary = summary[:220].rsplit(" ", 1)[0] + "…"
        if summary:
            print(f"    {summary}")
        print(f"    {t['link']}\n")


def print_list():
    for kind, label in (("region", "Regions"), ("topic", "Topics")):
        print(f"{label}:")
        for key, (k, name, _) in FORUMS.items():
            if k == kind:
                print(f"  {key:24s} {name}")
        print()


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="forums this tool covers, by region and by topic")

    r = sub.add_parser("retrieve", help="recent threads in one forum")
    r.add_argument("source", choices=list(FORUMS.keys()))
    r.add_argument("--limit", type=int, default=10, metavar="N")

    s = sub.add_parser("search", help="recent threads in one forum matching all keywords")
    s.add_argument("source", choices=list(FORUMS.keys()))
    s.add_argument("query", help="comma-separated keywords, matched against title and summary")
    s.add_argument("--limit", type=int, default=10, metavar="N")

    a = p.parse_args()

    if a.cmd == "list":
        print_list()
        return

    threads = fetch_threads(a.source)
    if a.cmd == "search":
        threads = search_threads(threads, a.query)
    print_threads(a.source, threads, a.limit)


if __name__ == "__main__":
    main()

# Washington State Lakes Site File Conventions

These conventions apply to every site file written in this region.

## Region Specific Research

- **Sources.**
  - [NW Dive Club](https://nwdiveclub.com/viewforum.php?f=6), community write-ups of how a site is dived: the entry, what's worth seeing, what to expect. Read it through the Wayback Machine (`https://archive.org/wayback/available?url=<page>`, then `curl --compressed` the snapshot), and confirm the snapshot holds the full thread.
  - [The Perfect Dive](https://web.archive.org/web/20220413053905/http://theperfectdive.com/DEF-SiteList.asp), a defunct catalog of Pacific Northwest sites, frozen around 2022: dive type, difficulty, entry and attractions per site, including several lesser-known sites. Read this pinned snapshot with `curl --compressed`.

## Depth

- **Datum.** The lake's own surface: fresh water has no tide, so an observed depth is simply true. Its name in the tools and in a site JSON's `seabed_datum` is `LAKE`, the datum the depth tool gives a lake bed on, and the tide tool's height on it is 0.
- **No depth.** Where `depth.md` finds no water level for the lake and gives no depth, the Coordinates row carries none and the gap is reported in chat.

## Current

- **Current type.** None: lake water holds still apart from a wind driven surface drift.

# Washington State Lakes Site File Conventions

These conventions apply to every site file written in this region.

## Region Specific Research

- **Tool.** `subsurface_log.md`, the site's dives, matched by name and logged position; a dive matching only one is checked, and confirmed with the user when unclear. Their depths, times, temperatures, visibility, current felt and notes feed every section.
- **Tool.** `diversatlas.md`, found by the dive area coordinate: a second pin, entry, parking, landmarks, access, life and hazards.
- **Sources.**
  - [NW Dive Club](https://nwdiveclub.com/viewforum.php?f=6), community write-ups of how a site is dived: the entry, what's worth seeing, what to expect. Read it through the Wayback Machine (`https://archive.org/wayback/available?url=<page>`, then `curl --compressed` the snapshot), and confirm the snapshot holds the full thread.
  - [The Perfect Dive](https://web.archive.org/web/20220413053905/http://theperfectdive.com/DEF-SiteList.asp), a defunct catalog of Pacific Northwest sites, frozen around 2022: dive type, difficulty, entry and attractions per site, including several lesser-known sites. Read this pinned snapshot with `curl --compressed`.

## Depth

- **Datum.** None: fresh water has no tide, so an observed depth is simply true.
- **Tool.** `depth.md`, the lake bed's depth below the lake's surface at the dive area coordinate. Where the tool gives no depth, the Coordinates row carries none and the gap is reported in chat.
- **Depth range.** The dive log's maximum depths and the research sources.

## Current

- **Current type.** None: lake water holds still apart from a wind driven surface drift.

## Wind

- **Tool.** `shore_exposure.md`, reading the lake's own shoreline.

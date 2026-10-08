# Washington State Lakes Site File Conventions

These conventions apply to every site file written in this region.

## Region Specific Research

- **Tools.**
  - `subsurface_log.md`, the site's dives, matched by name and logged position; a dive matching only one is checked, and confirmed with the user when unclear. Their depths, times, temperatures, visibility, current felt and notes feed every section.
  - `diversatlas.md` and `diveatlas.md`, each found by the dive area coordinate: a second pin, entry, parking, landmarks, access, life and hazards.
- **Sources.**
  - [NW Dive Club](https://nwdiveclub.com/viewforum.php?f=6), community write-ups of how a site is dived: the entry, what's worth seeing, what to expect. Read it through the Wayback Machine (`https://archive.org/wayback/available?url=<page>`, then `curl --compressed` the snapshot), and confirm the snapshot holds the full thread.
  - [The Perfect Dive](https://web.archive.org/web/20220413053905/http://theperfectdive.com/DEF-SiteList.asp), a defunct catalog of Pacific Northwest sites, frozen around 2022: dive type, difficulty, entry and attractions per site, including several lesser-known sites. Read this pinned snapshot with `curl --compressed`.

## Depth

- **Datum.** None: fresh water has no tide, so an observed depth is simply true.
- **Depth range.** The dive log's maximum depths and the research sources; the lakes fall outside the workspace's bathymetry tools.

## Current

- **Current type.** None: lake water holds still apart from a wind driven surface drift.

## Wind

- **Tool.** `shore_exposure.md`, reading the lake's own shoreline.

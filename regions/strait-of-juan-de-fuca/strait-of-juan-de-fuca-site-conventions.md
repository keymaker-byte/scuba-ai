# Strait of Juan de Fuca Site File Conventions

These conventions apply to every site file written in this region.

## Region Specific Research

- **Sources.**
  - [NW Dive Club](https://nwdiveclub.com/viewforum.php?f=6), community write-ups of how a site is dived: the entry, what's worth seeing, what to expect. Read it through the Wayback Machine (`https://archive.org/wayback/available?url=<page>`, then `curl --compressed` the snapshot), and confirm the snapshot holds the full thread.
  - [The Perfect Dive](https://web.archive.org/web/20220413053905/http://theperfectdive.com/DEF-SiteList.asp), a defunct catalog of Pacific Northwest sites, frozen around 2022: dive type, difficulty, entry and attractions per site, including several lesser-known sites. Read this pinned snapshot with `curl --compressed`.

## Depth

- **Datum.** Every depth is normalized to MLLW, mean lower low water, the datum NOAA's charts and its tide and current predictions use for this coast. Its name in the tools and in a site JSON's `seabed_datum` is `MLLW`.

## Current

- **Current type.** Tidal.
- **No station within reach.** No current station lies within `current.md`'s reach of the western strait, from Sekiu west, so a site there is predicted from the tidal database alone.

# San Juan Islands Site File Conventions

These conventions apply to every site file written in this region.

## Region Specific Research

Read in full for every site file.

- **Sources.**
  - [NW Dive Club](https://nwdiveclub.com/viewforum.php?f=6), community write-ups of how a site is dived: the entry, what's worth seeing, what to expect. Read it through the Wayback Machine (`https://archive.org/wayback/available?url=<page>`, then `curl --compressed` the snapshot), and confirm the snapshot holds the full thread.
  - [The Perfect Dive](https://web.archive.org/web/20220413053905/http://theperfectdive.com/DEF-SiteList.asp), a defunct catalog of Pacific Northwest sites, frozen around 2022: dive type, difficulty, entry and attractions per site, including several lesser-known sites. Read this pinned snapshot with `curl --compressed`.
  - [Emerald Diving](https://www.emeralddiving.com/local_sites_sj.html), a diver's own guide to boat sites across the islands and Rosario Strait, one page per site with its location, depth, conditions and life. Read it live.
  - [San Juan Islands National Wildlife Refuge](https://www.fws.gov/refuge/san-juan-islands), which islands and rocks are refuge, closed to landing with their surrounding water closed to watercraft. Checked for every site near a rock or islet.

## Depth

- **Datum.** Every depth is normalized to MLLW, mean lower low water, the datum NOAA's charts and tide predictions use for these waters. Its name in the tools and in a site JSON's `seabed_datum` is `MLLW`.
- **Tide station.** On the same channel or shore as the site. The islands carry a dense network of subordinate tide stations, so the nearest station often sits across a pass or on another island's shore; where it does, the nearest one on the site's own side of the pass governs.

## Current

- **Current type.** Tidal.
- **Unequal windows.** The tide's strong inequality makes the windows uneven: the prose names the long window on the weak exchange and the short one either side of the large ebb, and notes any day the weak exchange holds under the threshold with no clean slack.
- **Points and channel junctions.** Off a point or where channels meet, upwellings, downwellings and whirlpools form, and the set close to shore can run opposite to the channel's. The prose describes the eddy where community sources or the dive log record one.

## Wind

- **Swell.** On the south shores open to the Strait of Juan de Fuca and on the southern Haro Strait shore, `shore_exposure.md`'s fetch along the straits reads capped; the swell those shores take arrives from beyond any fetch the tool measures, and the site's prose names it where community sources or the dive log record surge on the entry.

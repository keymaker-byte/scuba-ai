# San Juan Islands Site File Conventions

These conventions apply to every site file written in this region.

## Region Specific Research

Read in full for every site file.

- **Tool.** `subsurface_log.md`, the site's dives, matched by name and logged position; a dive matching only one is checked, and confirmed with the user when unclear. Their depths, times, temperatures, visibility, current felt and notes feed every section.
- **Tool.** `diversatlas.md`, found by the dive area coordinate: a second pin, entry, parking, landmarks, access, life and hazards.
- **Sources.**
  - [NW Dive Club](https://nwdiveclub.com/viewforum.php?f=6), community write-ups of how a site is dived: the entry, what's worth seeing, what to expect. Read it through the Wayback Machine (`https://archive.org/wayback/available?url=<page>`, then `curl --compressed` the snapshot), and confirm the snapshot holds the full thread.
  - [The Perfect Dive](https://web.archive.org/web/20220413053905/http://theperfectdive.com/DEF-SiteList.asp), a defunct catalog of Pacific Northwest sites, frozen around 2022: dive type, difficulty, entry and attractions per site, including several lesser-known sites. Read this pinned snapshot with `curl --compressed`.
  - [Emerald Diving](https://www.emeralddiving.com/local_sites_sj.html), a diver's own guide to boat sites across the islands and Rosario Strait, one page per site with its location, depth, conditions and life. Read it live.
  - [San Juan Islands National Wildlife Refuge](https://www.fws.gov/refuge/san-juan-islands), which islands and rocks are refuge, closed to landing with their surrounding water closed to watercraft. Checked for every site near a rock or islet.

## Depth

- **Datum.** Every depth is normalized to MLLW, mean lower low water, the datum NOAA's charts and tide predictions use for these waters. The seabed is fixed and the surface is not, so a raw depth reading holds only at the tide it was taken; every depth worth keeping is converted to depth below MLLW and never mixed with another datum. Tide height is signed, negative on a minus tide, so subtracting a negative tide height makes the datum depth the deeper number: Its name in the tools and in a site JSON's `seabed_datum` is `MLLW`, and every depth is read with `depth.py --datum MLLW`.

  ```
  depth below MLLW datum  =  observed depth (computer)  -  tide height at that moment
  depth below surface     =  datum depth                +  predicted tide height
  ```

- **Tool.** `depth.md`, the seabed depth below MLLW at the dive area coordinate.
- **Tool.** `tide.md`, the tide station: its typical range (median daily range, largest daily range, the year's span), and the dive log's maximum depths normalized to MLLW for the depth range.
- **Tide station.** A NOAA station on the same channel or shore as the site, its name and position verified. The islands carry a dense network of subordinate tide stations, so the nearest station often sits across a pass or on another island's shore; where it does, the nearest one on the site's own side of the pass governs.

## Current

- **Current type.** Tidal.
- **Tool.** `current.md`, the site's extract, attached to the site's `<slug>.json`, and its predictions of slack, set, peak speeds and diveable windows.
- **Tool.** `subsurface_log.md`, the set and strength actually felt at the site, and the timed slacks behind the observed offset.
- **Extract.** Taken once the dive area coordinate holds, with `extract --site` on the site JSON, at the tool's default height above the seabed. A coordinate the tool refuses, on land or in water outside its coverage, stops the site: report it and wait.
- **Unequal windows.** The tide's strong inequality makes the windows uneven: the prose names the long window on the weak exchange and the short one either side of the large ebb, and notes any day the weak exchange holds under the threshold with no clean slack.
- **Points and channel junctions.** Off a point or where channels meet, upwellings, downwellings and whirlpools form, and the set close to shore can run opposite to the channel's. The prose describes the eddy where community sources or the dive log record one.

## Wind

- **Tool.** `shore_exposure.md`. On the south shores open to the Strait of Juan de Fuca and on the southern Haro Strait shore, the fetch along the straits reads capped; the swell those shores take arrives from beyond any fetch the tool measures, and the site's prose names it where community sources or the dive log record surge on the entry.

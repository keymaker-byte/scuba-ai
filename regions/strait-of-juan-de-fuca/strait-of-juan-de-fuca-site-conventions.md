# Strait of Juan de Fuca Site File Conventions

These conventions apply to every site file written in this region.

## Region Specific Research

- **Tool.** `subsurface_log.md`, the site's dives, matched by name and logged position; a dive matching only one is checked, and confirmed with the user when unclear. Their depths, times, temperatures, visibility, current felt and notes feed every section.
- **Tool.** `diversatlas.md`, found by the dive area coordinate: a second pin, entry, parking, landmarks, access, life and hazards.
- **Sources.**
  - [NW Dive Club](https://nwdiveclub.com/viewforum.php?f=6), community write-ups of how a site is dived: the entry, what's worth seeing, what to expect. Read it through the Wayback Machine (`https://archive.org/wayback/available?url=<page>`, then `curl --compressed` the snapshot), and confirm the snapshot holds the full thread.
  - [The Perfect Dive](https://web.archive.org/web/20220413053905/http://theperfectdive.com/DEF-SiteList.asp), a defunct catalog of Pacific Northwest sites, frozen around 2022: dive type, difficulty, entry and attractions per site, including several lesser-known sites. Read this pinned snapshot with `curl --compressed`.

## Depth

- **Datum.** Every depth is normalized to MLLW, mean lower low water, the datum NOAA's charts and its tide and current predictions use for this coast. The seabed is fixed and the surface is not, so a raw depth reading holds only at the tide it was taken; every depth worth keeping is converted to depth below MLLW and never mixed with another datum. Tide height is signed, negative on a minus tide, so subtracting a negative tide height makes the datum depth the deeper number:

  ```
  depth below MLLW datum  =  observed depth (computer)  -  tide height at that moment
  depth below surface     =  datum depth                +  predicted tide height
  ```

- **Tool.** `ncei_depth.md`, the seabed depth below MLLW at the dive area coordinate.
- **Tool.** `noaa_tide.md`, the tide station: its typical range (median daily range, largest daily range, the year's span), and the dive log's maximum depths normalized to MLLW for the depth range.
- **Tide station.** A NOAA station in the same body of water as the site, its name and position verified.
- **Western mouth.** The fine-grained bathymetry gives out around Tatoosh Island and Duncan Rock, falling back to a coarse global grid; a site's depths there are a starting point to verify on the day.

## Current

- **Current type.** Tidal.
- **Tool.** `blend_model.md`, the site's extract, attached to the site's `<slug>.json`, and its predictions of slack, set, peak speeds and diveable windows.
- **Tool.** `subsurface_log.md`, the set and strength actually felt at the site, and the timed slacks behind the observed offset.
- **Extract.** Taken once the dive area coordinate holds, with `extract --site` on the site JSON, at the tool's default height above the seabed. A coordinate the tool refuses, on land or in water outside its coverage, stops the site: report it and wait.
- **No station within reach.** Where no current station lies within the tool's reach of the site, the prediction is the tidal database's own, scaled to the height, and the tool's header says so; the site's prose states its timing as a starting point to verify on the day. Today this is the western strait, from Sekiu west.

## Wind

- **Tool.** `shore_exposure.md`.

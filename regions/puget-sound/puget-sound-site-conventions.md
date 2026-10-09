# Puget Sound Site File Conventions

These conventions apply to every site file written in this region.

## Region Specific Research

- **Tools.**
  - `subsurface_log.md`, the site's dives, matched by name and logged position; a dive matching only one is checked, and confirmed with the user when unclear. Their depths, times, temperatures, visibility, current felt and notes feed every section.
  - `diversatlas.md` and `diveatlas.md`, each found by the dive area coordinate: a second pin, entry, parking, landmarks, access, life and hazards.
- **Sources.**
  - [NW Dive Club](https://nwdiveclub.com/viewforum.php?f=6), community write-ups of how a site is dived: the entry, what's worth seeing, what to expect. Read it through the Wayback Machine (`https://archive.org/wayback/available?url=<page>`, then `curl --compressed` the snapshot), and confirm the snapshot holds the full thread.
  - [The Perfect Dive](https://web.archive.org/web/20220413053905/http://theperfectdive.com/DEF-SiteList.asp), a defunct catalog of Pacific Northwest sites, frozen around 2022: dive type, difficulty, entry and attractions per site, including several lesser-known sites. Read this pinned snapshot with `curl --compressed`.

## Depth

- **Datum.** Every depth is normalized to MLLW, mean lower low water, the datum NOAA's charts and its tide and current predictions use for this coast. The seabed is fixed and the surface is not, so a raw depth reading holds only at the tide it was taken; every depth worth keeping is converted to depth below MLLW and never mixed with another datum. Tide height is signed, negative on a minus tide, so subtracting a negative tide height makes the datum depth the deeper number:

  ```
  depth below MLLW datum  =  observed depth (computer)  -  tide height at that moment
  depth below surface     =  datum depth                +  predicted tide height
  ```

- **Tools.**
  - `ncei_depth.md`, the seabed depth below MLLW at the dive area coordinate.
  - `noaa_tide.md`, the tide station: its typical range (median daily range, largest daily range, the year's span), and the dive log's maximum depths normalized to MLLW for the depth range.
- **Tide station.** A NOAA station in the same body of water and on the same side of any sill as the site, its name and position verified.

## Current

- **Current type.** Tidal.
- **Tools.**
  - `adcirc_current.md`, the site's ENPAC15 extract, carried as a companion `<slug>.json`, and its predictions of slack times and set direction.
  - `noaa_current.md`, the governing station, its recommended bin, axes, peak speeds and diveable windows.
  - `subsurface_log.md`, the set and strength actually felt at the site, and the timed slacks behind the observed offset.
- **Governing station.** The nearest live NOAA harmonic station (type H) with depth bins in the same reach as the site, nearest by the water path rather than a straight line over land: no sill, narrows or pass, sheltering spit or harbor, or basin boundary lies between them. Where a point or confluence shapes the site's flow, the station at that feature governs over a nearer one in the open channel. Subordinate (type S) and weak-and-variable (type W) stations never govern; where no harmonic station qualifies, the row names the nearest one with predictions and states that none governs. The extract never decides the choice; it stands beside the station at planning time as an independent estimate.
- **Recommended bin.** The station's published bin nearest the dive area's seabed depth.
- **Span.** 30 consecutive days of predictions, starting on the day the figures are computed: the governing station's at the recommended bin for the peak speeds and the diveable window, and the extract's at the bottom of the water column for the site sets. Thirty days takes in both spring tides of the lunar month, the larger perigean one included.
- **Axes and peak speeds.** The governing station's own, at the recommended bin: its axes in the Station flood axis and Station ebb axis rows, and the range of its daily peak flood and ebb over the span.
- **Site sets.** The median of the extract's daily principal axis at the dive area over the span, in the Site flood set and Site ebb set rows; of its two directions, the one nearer the station's flood is the flood. The prose underneath carries any shore-parallel set the extract misses. A site with no extract reads "As the station" in both rows.
- **Diveable window.** The station's windows under the current threshold, at the recommended bin, over the span.
- **Observed offset.** Timed slacks from the site's logged dives only, each a computer bookmark or a "slack HH:MM" note, measured against the station's nearest predicted slack that day. A slack's offset is established at 4 observations on 4 days, springs and neaps both, all within 10 minutes of their median, which its row states as a fact; otherwise not established. Neither the extract nor a legacy correction feeds it.
- **Legacy correction.** A correction published in an older current table goes in its own table at the end of the Current section, recorded as published: the legacy station by name and position with its distance and direction from the site, the reference station it was published against, by name and ID, and the minutes for each slack. It never feeds the Observed offset rows.
- **Hood Canal interior.** A site past the canal entrance has no governing station: the Governing station row names Hazel Point (PUG1601) as the nearest, the observed offset is not established, and the prose gives high and low water at the site's tide station as the slack guide.

## Wind

- **Tool.** `shore_exposure.md`.

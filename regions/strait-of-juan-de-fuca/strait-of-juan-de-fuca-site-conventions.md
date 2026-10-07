# Strait of Juan de Fuca Site File Conventions

These conventions apply to every site file written in this region.

## Region Specific Research

- **Tools.**
  - `subsurface_log.md`, searched under the site's name and its likely variants: each dive's depths, times, profile, temperatures and notes.
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
- **Tide station.** A NOAA station in the same body of water as the site, its name and position verified.
- **Western mouth.** The fine-grained bathymetry gives out around Tatoosh Island and Duncan Rock, falling back to a coarse global grid; a site's depths there are a starting point to verify on the day.

## Current

- **Current type.** Tidal.
- **Tools.**
  - `adcirc_current.md`, the site's ENPAC15 extract, carried as a companion `<slug>.json`, and its predictions of slack times and set direction.
  - `noaa_current.md`, the governing station, its recommended bin, axes, peak speeds and diveable windows.
  - `subsurface_log.md`, timed observations for the offset, each dive's profile placing the turn and the ascent on the clock.
- **Governing station.** The live NOAA current station whose slack times and set direction best match the extract's predictions, compared day by day over a span of weeks. It is a PUG-prefixed survey station; a PCT-prefixed station (Predicted Current Tables) publishes no depth bins, so the nearest PUG-prefixed one takes its place.
- **Recommended bin.** The station's published bin nearest the dive area's seabed depth.
- **Time offset.** Derived for the governing station alone, so a legacy correction stated against a retired station is re-derived. It comes from timed observations against the station's prediction for that day, from the station's slack times reconciled against the extract's, or from a source that names the governing station. State in chat which observations the offset rests on and which slack each one supports. Where none of these gives one, the row is written as not established.
- **Span.** Peak speeds, the diveable window and the site sets come from 30 consecutive days, starting on the day the figures are computed, with the extract read at the bottom of the water column. Thirty days takes in both spring tides of the lunar month, the larger perigean one included.
- **Axes and peak speeds.** The governing station's own, at the recommended bin: its axes in the Station flood axis and Station ebb axis rows, and the range of its daily peak flood and ebb over the span.
- **Site sets.** The median of the extract's daily principal axis at the dive area over the span, in the Site flood set and Site ebb set rows; of its two directions, the one nearer the station's flood is the flood. The prose underneath carries any shore-parallel set the extract misses. A site with no extract reads "As the station" in both rows.
- **Diveable window.** The station's windows under the current threshold, at the recommended bin, over the span.
- **Western reach.** Live stations thin out west of Port Angeles, 20 to 30 km from Sekiu or Neah Bay, and a coordinate off Tatoosh Island sits close to the edge of the ENPAC15 mesh; the site's prose states its timing as a starting point to verify on the day.

## Wind

- **Tool.** `shore_exposure.md`.

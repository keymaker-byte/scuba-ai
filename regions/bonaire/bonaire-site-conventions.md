# Bonaire Site File Conventions

These conventions apply to every site file written in this region.

## Region Specific Research

- **Tool.** `subsurface_log.md`, the site's dives, matched by name and logged position; a dive matching only one is checked, and confirmed with the user when unclear. Their depths, times, temperatures, visibility, current felt and notes feed every section.
- **Tool.** `diversatlas.md`, found by the dive area coordinate: a second pin, entry, parking, landmarks, access, life and hazards.
- **Sources.**
  - [Bonaire.com dive sites](https://bonaire.com/en/dive-sites/), the island guide's catalog of about a hundred sites: access, level, facilities, the nature fee, and a write-up of the reef, entry and life. Read a page at `/en/dive-sites/<slug>/` with `curl --compressed`. Its depth, visibility and current figures are rough, often in feet, and taken as behaviour only. Its long-form pages mix accurate detail with generic or wrong claims; use only what another source confirms.
  - [STINAPA dive map](https://stinapabonaire.org/bonaire-national-marine-park/dive-map/), the marine park's 86 numbered sites: official number and name, a pin, access tags, and a short description with a depth range. The markers sit in the page as the JSON array after `"places":`; parse it leniently, since it has invalid escapes. A marker's own tags are the icons after its photo, and the pin is approximate, often hundreds of metres off the site, so a rough cross-check only.

## Depth

- **Datum.** None: depth is a plain observed figure, since Bonaire's tidal range runs about 30 cm, too small to normalize against.
- **Tool.** `dcbd_depth.md`, the seabed depth at the dive area coordinate.

## Current

- **Current type.** Wind driven.
- **Usual set and typical speed.** The research sources' descriptions of the site and the dive log's own dives there, taken as behaviour and cross-checked between sources.
- **Drivers.** The winds or seasons those same sources tie to a stronger or reversed set.
- **No source.** A set no source describes is written as not established.
- **Tool.** `blend_model.md`, the site's extract, attached to the site's `<slug>.json`, for planning. It feeds no bullet of the site file: the tidal stream it models runs a few centimetres a second around the island, from mesh elements about 3.5 km across with no current station within reach, and the usual set comes from the sources above.
- **Extract.** Taken once the dive area coordinate holds, with `extract --site` on the site JSON, at the tool's default height above the seabed. A coordinate the tool refuses, on land or in water outside its coverage, stops the site: report it and wait.

## Wind

- **Tool.** `shore_exposure.md`.

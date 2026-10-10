# Bonaire Site File Conventions

These conventions apply to every site file written in this region.

## Region Specific Research

- **Tools.**
  - `subsurface_log.md`, the site's dives, matched by name and logged position; a dive matching only one is checked, and confirmed with the user when unclear. Their depths, times, temperatures, visibility, current felt and notes feed every section.
  - `diversatlas.md` and `diveatlas.md`, each found by the dive area coordinate: a second pin, entry, parking, landmarks, access, life and hazards.
- **Sources.**
  - [Bonaire.com dive sites](https://bonaire.com/en/dive-sites/), the island guide's catalog of about a hundred sites: access, level, facilities, the nature fee, and a write-up of the reef, entry and life. Read a page at `/en/dive-sites/<slug>/` with `curl --compressed`. Its depth, visibility and current figures are rough, often in feet, and taken as behaviour only.
  - [STINAPA dive map](https://stinapabonaire.org/bonaire-national-marine-park/dive-map/), the marine park's 86 numbered sites: official number and name, a pin, access tags, and a short description with a depth range. The markers sit in the page as the JSON array after `"places":`; parse it leniently, since it has invalid escapes. A marker's own tags are the icons after its photo, and the pin is a cross-check only.

## Depth

- **Datum.** None: depth is a plain observed figure, since Bonaire's tidal range runs about 30 cm, too small to normalize against.
- **Tool.** `emodnet_depth.md`, the seabed depth at the dive area coordinate.

## Current

- **Current type.** Wind driven.
- **Usual set and typical speed.** The research sources' descriptions of the site and the dive log's own dives there, taken as behaviour and cross-checked between sources.
- **Drivers.** The winds or seasons those same sources tie to a stronger or reversed set.
- **No source.** A set no source describes is written as not established.

## Wind

- **Tool.** `shore_exposure.md`.

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
- **Spatial extract.** `adcirc_current.md`, the site's EC2015 extract, run with `--walk` on the dive area coordinate and attached to the site's `<slug>.json` whole, for planning. It feeds no row of the site file: the tidal stream it models runs a few centimetres a second around the island, from mesh elements about 3.5 km across, and the usual set comes from the sources above. Where the dive area coordinate falls outside the EC2015 mesh, the extract is taken at the nearest point inside the mesh, 5 m in from its edge, and its `ec2015_extract_point` records that point and its `distance_from_site_km`, both reported in chat. A moved dive area coordinate takes a new extract.

## Wind

- **Tool.** `shore_exposure.md`.

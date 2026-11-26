# Bonaire Site File Conventions

These conventions apply to every site file written in this region.

## Region Specific Research

- **Sources.**
  - [Bonaire.com dive sites](https://bonaire.com/en/dive-sites/), the island guide's catalog of about a hundred sites: access, level, facilities, the nature fee, and a write-up of the reef, entry and life. Read a page at `/en/dive-sites/<slug>/` with `curl --compressed`. Its depth, visibility and current figures are rough, often in feet, and taken as behaviour only. Its long-form pages mix accurate detail with generic or wrong claims; use only what another source confirms.
  - [STINAPA dive map](https://stinapabonaire.org/bonaire-national-marine-park/dive-map/), the marine park's 86 numbered sites: official number and name, a pin, access tags, and a short description with a depth range. The markers sit in the page as the JSON array after `"places":`; parse it leniently, since it has invalid escapes. A marker's own tags are the icons after its photo, and the pin is approximate, often hundreds of metres off the site, so a rough cross-check only.

## Depth

- **Datum.** None: depth is a plain observed figure, since Bonaire's tidal range runs about 30 cm, too small to normalize against. Its name in the tools and in a site JSON's `seabed_datum` is `NONE`, on which the tide tool's height is 0.
- **Terrace.** The reef drops from a shallow terrace, so a dive area coordinate is walked across it to the drop-off with `depth.md`'s `transect`.

## Current

- **Current type.** Wind driven.
- **Tidal stream.** The tidal stream `current.md` models runs a few centimetres a second around the island, from mesh elements about 3.5 km across with no current station within reach, well under the wind-driven set.

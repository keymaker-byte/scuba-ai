# OpenStreetMap shoreline (orientation and wind fetch)

<https://osmdata.openstreetmap.de/data/land-polygons.html>, <https://www.hydrosheds.org/products/hydrolakes>

Which way a dive site's shore faces, and how far wind travels over open water to reach it from each of 16 compass directions. It reads two global shoreline datasets, OpenStreetMap's coastline for the sea and HydroLAKES for lakes, both downloaded once and read locally through `tools/lib/shapes.py`, a shared library, so it works at any coordinate worldwide with the same method everywhere.

- **Use it for.** Writing a site, the `create-dive-site` skill's wind step: `extract --site` writes the site JSON's `wind` section, the entry and dive area shore facings, the swim out, the shore relation, fetch and class of each of the 16 directions, and the Bad, Short fetch, Mixed and Fine sectors. A plan reads those sectors from the JSON with `forecast.md`'s `--file` for its wind and waves calls, and the site file's Wind bullets describe them.
- **Sea shoreline.** OpenStreetMap's coastline as land polygons, published by osmdata.openstreetmap.de and rebuilt from the live map daily. A ~900 MB download, unpacked into `tools/db/land_polygons/` (1.2 GB) and read locally after that. Deleting the folder fetches the current edition on the next run. The polygons come cut into pieces on a roughly 1° grid; every cut runs through land between two points on the shoreline, so it never stands between a site and open water.
- **Lake shoreline.** HydroLAKES (HydroSHEDS, CC BY 4.0): every lake and reservoir of 10 ha or more worldwide, islands included as holes. The land polygons count a lake as land, so a coordinate on land is looked up in HydroLAKES, and inside a lake the tool reads that lake's own shoreline and reports its id and area, plus its name where HydroLAKES carries one, which many lakes lack. An ~820 MB download, unpacked into `tools/db/hydrolakes/` (1.4 GB), fetched again whenever deleted. Its outlines come mostly from satellite water mapping on a ~30 m grid, coarser than the coastline: well inside a fetch, and a few degrees of noise on a facing. A coordinate on land and in no lake of 10 ha or more stops the run: walk it toward the water.
- **Fetch on a winding lake.** Fetch is measured in straight lines, and wind in a long valley lake follows the valley around its bends, so on a curving lake the along-lake fetch reads short. Where research shows wind funnelling along the lake onto a beach, the site skill's local knowledge rule moves that direction up a class with `--raise`, with its source.
- **Faces.** The seaward direction of a stretch of shore: the mean normal of the mapped shoreline within `shore_span_m` of the nearest shore point, turned toward the water. On a straight beach it is the beach's own facing; at a point or a bay mouth it averages the curve, so read it together with the fetch table. The tool reports it as the dive area shore facing, for the shore nearest the dive area, and with `--entry` as the entry shore facing too, for the shore a shore site's entry and exit face, which then sets the onshore column. Across a channel, those two face opposite ways.
- **Swim out.** With `--entry`, the bearing and distance from the entry point to the dive area, and its angle off the entry shore's facing. A large angle means the swim runs along the shore, or the dive area sits off a point.
- **Fetch.** The distance along each bearing to the first mapped shoreline, the far shore, an island or a headland, which is how much open water a wind from that direction crosses before it reaches the dive area. It is capped at `max_fetch_km`; a capped reading means open water as far as fetch matters.
- **The shore column.** Onshore within 67.5° of the facing, cross-shore to 112.5°, offshore beyond.
- **The class.** Each direction is classed by its shore relation and fetch, by the table below. The thresholds come from fetch-limited wind wave growth (JONSWAP): at the forecast tool's no-go speed, 1 km of fetch builds ripples and 5 km real chop. Swell is outside the table. Short fetch and Mixed stand on one rung: the forecast tool reads both with their bands moved up.

  | Relation | Fetch | Class |
  |---|---|---|
  | Onshore | 5 km or more | Bad |
  | Onshore | 1 to 5 km | Short fetch |
  | Onshore | Under 1 km | Fine |
  | Cross-shore | 5 km or more | Mixed |
  | Cross-shore | Under 5 km | Fine |
  | Offshore | Any | Fine |

- **Raised by local knowledge.** `--raise SECTOR=CLASS` moves a direction up a class (Fine to Short fetch, Mixed or Bad, Short fetch or Mixed to Bad), never down; a raise to the measured class or below it stops the run. `--calm-only` classes every direction Bad, for a site dived only in calm. Both are kept in the JSON and applied again on every extract after, until `--raise` or `--calm-only` replaces them or `--no-raise` drops them. A recorded raise a new shoreline makes moot is reported and kept.
- **Sectors.** Adjacent directions of one class joined, named clockwise end to end (`SW-WNW`, `N`), the form the forecast tool takes; all 16 of one class read `N-NNW`.
- **The map holds the shoreline only.** Terrain height is outside it: a high bluff that blocks an offshore wind, or a narrows that funnels one, reads the same as a flat shore. Small rocks, piers and breakwaters are mapped unevenly. Confirm both against community sources and the site's own description.

## The site JSON

`extract --site` reads the site JSON's `lat` and `lon`, the dive area coordinate, and writes `wind`, the way `current.md`'s extract writes `current`:

- **`extract_point`.** The point it was taken for: its `lat` and `lon`, the `entry` point as `lat` and `lon` (`null` for a boat site), the `shore_span_m` and `max_fetch_km` it was measured with, and the date it was `extracted`.
- **`shoreline`.** The shoreline read: OpenStreetMap's land polygons, or the HydroLAKES lake by name and id.
- **`dive_area_faces`.** The dive area shore facing, in degrees true.
- **`entry_faces`.** The entry shore facing, in degrees true; `null` for a boat site.
- **`swim_out`.** The `bearing` and `distance_m` from the entry to the dive area, and its angle `off_entry_faces`; `null` for a boat site.
- **`fetch`.** The 16 compass points clockwise from north, each with its `from` point, `bearing`, `fetch_km`, whether it is `capped` at `max_fetch_km`, and its `relation` to the entry shore (the dive area shore for a boat site), `onshore`, `cross-shore` or `offshore`, and its `class`, `bad`, `short`, `mixed` or `fine`, after any raise.
- **`calm_only` and `raised`.** Whether every direction is classed Bad, and each point moved up by `--raise` with the class it was moved to.
- **`sectors`.** The `bad`, `short`, `mixed` and `fine` sectors, each a list of compass shorthand, the ones the forecast tool's `--file` reads, beside each point's `relation`, which its waves call reads.

A shore site's first extract names its entry with `--entry`, the Entry point coordinates row, and a boat site's with `--boat`. After that, `extract --site` alone takes the site again at the entry its `wind` section was taken for and with its recorded raises, so a batch of sites re-extracts in one call. Every site is read and measured before any is written, so a refused one stops the run with nothing changed. Run it again whenever the site's coordinate or entry point changes, and after a fresh download of either shoreline.

## `tools/shore_exposure.py`

Standard library only.

```sh
python3 tools/shore_exposure.py extract --site <path/to/slug.json> --entry <entry lat> <entry lon>   # site JSON, shore site: write its wind section
python3 tools/shore_exposure.py extract --site <path/to/slug.json> --boat                            # site JSON, boat site
python3 tools/shore_exposure.py extract --site <path/to/slug.json> --raise N=bad --raise S-SW=bad     # a direction moved up a class by research
python3 tools/shore_exposure.py extract --site <path/to/slug.json> --calm-only                       # a site dived only in calm
python3 tools/shore_exposure.py extract --site <path/to/slug.json> [<path> ...]                      # again, each at its recorded entry
python3 tools/shore_exposure.py at <dive lat> <dive lon> --entry <entry lat> <entry lon>             # a coordinate, shore: both facings, the swim out, the fetch
python3 tools/shore_exposure.py at <dive lat> <dive lon>                                             # a coordinate, boat: the dive area facing and the fetch
python3 tools/shore_exposure.py at <dive lat> <dive lon> --entry <entry lat> <entry lon> --json      # the same result as JSON
```

`extract` takes the dive area from the site JSON and the entry from the Entry point coordinates row, so the facings and the fetch come from the coordinates the site states. `at` reads any coordinate, for walking a point before it goes in the JSON; a bare coordinate with no command reads as `at`. `at` prints the shoreline source, the nearest shore's distance and bearing, the dive area shore facing, the entry shore facing and the swim out when given, then the fetch for each of the 16 compass points with its onshore, cross-shore or offshore relation and its class as measured, before any raise. Bearings are degrees true; a fetch row is labelled by the direction the wind blows from. The first sea run downloads the land polygons and the first lake run downloads HydroLAKES, each a few minutes on a fast connection; every run after reads them locally in under a second.

`tool-config.jsonc` keys, each with a default: `max_fetch_km` (30), the fetch cap and search radius; `shore_span_m` (250), the metres of shoreline averaged for a facing. The top-level `user_agent_email` sets the contact address sent in the User-Agent of a dataset download. `--max-fetch` and `--shore-span` override the first two per run.

# OpenStreetMap shoreline (orientation and wind fetch)

<https://osmdata.openstreetmap.de/data/land-polygons.html>, <https://www.hydrosheds.org/products/hydrolakes>

Which way a dive site's shore faces, and how far wind travels over open water to reach it from each of 16 compass directions. It reads two global shoreline datasets, OpenStreetMap's coastline for the sea and HydroLAKES for lakes, both downloaded once and read locally, so it works at any coordinate worldwide with the same method everywhere.

- **Use it for.** Writing a site file's Wind section, the `create-dive-site` skill's wind step: the Entry shore facing and Dive area shore facing rows, and the shore relation and fetch for each of the 16 directions that sort it into Bad, short fetch, Mixed or Fine, whose sectors a plan then passes to the wind forecast tool for its go / no go call.
- **Sea shoreline.** OpenStreetMap's coastline as land polygons, published by osmdata.openstreetmap.de and rebuilt from the live map daily. A ~900 MB download, unpacked into `tools/db/land_polygons/` (1.2 GB) and read locally after that. Deleting the folder fetches the current edition on the next run. The polygons come cut into pieces on a roughly 1° grid; every cut runs through land between two points on the shoreline, so it never stands between a site and open water.
- **Lake shoreline.** HydroLAKES (HydroSHEDS, CC BY 4.0): every lake and reservoir of 10 ha or more worldwide, islands included as holes. The land polygons count a lake as land, so a coordinate on land is looked up in HydroLAKES, and inside a lake the tool reads that lake's own shoreline and reports its id and area, plus its name where HydroLAKES carries one, which many lakes lack. An ~820 MB download, unpacked into `tools/db/hydrolakes/` (1.4 GB), fetched again whenever deleted. Its outlines come mostly from satellite water mapping on a ~30 m grid, coarser than the coastline: well inside a fetch, and a few degrees of noise on a facing. A coordinate on land and in no lake of 10 ha or more stops the run: walk it toward the water.
- **Fetch on a winding lake.** Fetch is measured in straight lines, and wind in a long valley lake follows the valley around its bends, so on a curving lake the along-lake fetch reads short. Where research shows wind funnelling along the lake onto a beach, the site skill's local knowledge rule moves that direction up a class, with its source.
- **Faces.** The seaward direction of a stretch of shore: the mean normal of the mapped shoreline within `shore_span_m` of the nearest shore point, turned toward the water. On a straight beach it is the beach's own facing; at a point or a bay mouth it averages the curve, so read it together with the fetch table. The tool reports it as the dive area shore facing, for the shore nearest the dive area, and with `--entry` as the entry shore facing too, for the shore a shore site's entry and exit face, which then sets the onshore column. Across a channel, those two face opposite ways.
- **Swim out.** With `--entry`, the bearing and distance from the entry point to the dive area, and its angle off the entry shore's facing. A large angle means the swim runs along the shore, or the dive area sits off a point.
- **Fetch.** The distance along each bearing to the first mapped shoreline, the far shore, an island or a headland, which is how much open water a wind from that direction crosses before it reaches the dive area. It is capped at `max_fetch_km`; a capped reading means open water as far as fetch matters.
- **The shore column.** Onshore within 67.5° of the facing, cross-shore to 112.5°, offshore beyond. The `create-dive-site` skill's wind step sorts each direction into Bad, short fetch, Mixed or Fine from this relation and the fetch.
- **The map holds the shoreline only.** Terrain height is outside it: a high bluff that blocks an offshore wind, or a narrows that funnels one, reads the same as a flat shore. Small rocks, piers and breakwaters are mapped unevenly. Confirm both against community sources and the site's own description.

## `tools/shore_exposure.py`

Standard library only.

```sh
python3 tools/shore_exposure.py <dive lat> <dive lon> --entry <entry lat> <entry lon>   # site file, shore site: both facings, the swim out, the fetch
python3 tools/shore_exposure.py <dive lat> <dive lon>                                   # site file, boat site: the dive area facing and the fetch
python3 tools/shore_exposure.py <dive lat> <dive lon> --entry <entry lat> <entry lon> --json   # the same result as JSON, for an audit script
```

Give it the site file's own Coordinates row, and for a shore site its Entry point coordinates as `--entry`, always together, so the facings and the fetch come from the coordinates the file states. It prints the shoreline source, the nearest shore's distance and bearing, the dive area shore facing, the entry shore facing and the swim out when given, then the fetch for each of the 16 compass points with its onshore, cross-shore or offshore relation. Bearings are degrees true; a fetch row is labelled by the direction the wind blows from. The first sea run downloads the land polygons and the first lake run downloads HydroLAKES, each a few minutes on a fast connection; every run after reads them locally in under a second.

`tool-config.json` keys, each with a default: `max_fetch_km` (30), the fetch cap and search radius; `shore_span_m` (250), the metres of shoreline averaged for a facing; and `user_agent_email`, the contact address sent in the User-Agent of a dataset download. `--max-fetch` and `--shore-span` override the first two per run.

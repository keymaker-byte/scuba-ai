# NCEI coastal DEM (bathymetry, water depth)

<https://www.ncei.noaa.gov/products/coastal-elevation-models>

NOAA NCEI's coastal digital elevation model: the seabed depth at a point, at about 3 m resolution (1/9 arc-second). It owns bathymetry for the workspace. Read from the DEM's own tiles kept on this machine: a tile is downloaded once, the first time a point inside it is asked for, and every depth in that tile after that is read with no request at all.

- **Use it for.** The water depth at a dive point, which goes in the site file's Coordinates row and in the site JSON's `seabed_m`, the seabed the Blend Model's height above the bottom is measured from. A spatial current model's own mesh cannot supply it: its elements can span from the beach to the deep basin, so its nearshore depth can be wrong by tens of metres. The DEM's 3 m soundings are the authority.
- **Also a sanity check on a coordinate.** Is this point underwater at all, and at a divable depth? It reads the actual bottom where a nautical chart gives scattered soundings between wide contours.
- **Coverage.** The ninth arc-second tiles NOAA publishes, about 930 of them along the US coasts: Washington, Oregon, California, the Gulf, the Atlantic seaboard and part of Alaska. A point outside them stops the run with a message.
- **The data.** `tools/db/ncei_depth/` holds NOAA's tile list, one GeoTIFF per quarter-degree tile, and each lake's water level once read (`lake_levels.json`; deleting it reads them again). A tile is about 200 MB, so its first use takes a few minutes on a fast connection and much longer on a slow one. `--fetch` downloads a whole area ahead of time. Deleting a tile, or the folder, fetches NOAA's current data on the next run, which is how a re-surveyed tile is picked up.
- **Shared code.** The tile list, the downloads and the lakes are `tools/lib/ncei.py`, the GeoTIFF reader `tools/lib/dem_tiles.py`, and the MLLW offset `tools/lib/vdatum.py`, shared libraries the map's depth layer and the Blend Model's seabed read the same way.
- **The value is the pixel the point falls in.** The tile's own georeferencing places each 3 m pixel, and the tool reads the one containing the coordinate. NCEI's live map service answers with a pixel half a cell to the south-east, 1.7 m away, so the two agree within a few centimetres on a gentle bottom and differ by up to 1.4 m on a steep wall.
- **Datum.** NAVD 88 (roughly mean sea level here). A depth normalized to datum is converted to MLLW with `--mllw` before it goes in a site file.
- **MLLW comes from VDatum's grids, on this machine.** The height of NAVD 88 above MLLW runs from a few centimetres in some areas to more than a metre in others. `--mllw` computes it at the exact point from NOAA VDatum's own transformation grids, the chain VDatum's conversion service runs: GEOID18 from NAVD 88 to the NAD83(2011) ellipsoid, HTDP's frame transformation to IGS14 at the epoch 2026.0, xGEOID20B to IGS14's gravimetric geoid, then the sub-region's `tss` grid to mean sea level and its `mllw` grid to MLLW. It reproduces answers VDatum's own service gave within 2 mm. The output names the offset and the VDatum sub-region it came from.
- **The sub-region is read from the coordinate.** VDatum divides tidal water into sub-regions, each with its own polygons, and the tool picks the one VDatum itself picks: the highest polygon type holding the point (a priority area over tidal water), the first in VDatum's own order on a tie. A point in no sub-region, in a non-tidal area, or on the land side of the grids' shoreline stops the run with the reason.
- **The grids.** `tools/db/vdatum/` holds VDatum's full package as it downloads (`vdatum_all_<date>.zip`, about 3 GB), its index of sub-regions (`tidal_area.inf` and `tidal_area.dat`), and one folder per sub-region extracted from the package: the `tss` and `mllw` grids, and GEOID18 and xGEOID20B cut to the sub-region's box. A sub-region is extracted the first time a point inside it is asked for, in a second or two; after that it needs neither the package nor the network. The Washington sub-regions are about 250 MB. Deleting a folder extracts it again, which is how a new package is picked up.
- **The package is downloaded by hand.** VDatum's download page refuses automated clients, so a missing package stops the run with the page to fetch it from: <https://vdatum.noaa.gov/download.php>, the full package, saved unopened into `tools/db/vdatum/`. The newest package there by its date is the one read.
- **Sub-regions referenced to IGS14.** Every Washington sub-region, and 20 of VDatum's 52, carry their tidal grids on IGS14, the frame the chain is built for. A sub-region on NAD83 or IGS08 stops the run with its frame named.
- **Positive means land, outside a lake.** An elevation above zero flags a coordinate on land.
- **Lakes.** A lake bed is an elevation above NAVD 88, with no tide and no MLLW. Its depth is the lake's water level minus that elevation. The tool reads the level from the DEM: where the survey never reached the bed, the DEM holds the flat water surface on the day it was flown, so one height repeats along the shore. A level counts when it shows along at least 10 of 12 stretches of the shore and sits within 10 m of HydroLAKES' own rough level; a lake with none, such as one surveyed right up to its walls, gives the bed's elevation alone. The level moves with the seasons, so a depth holds to the survey day's water, usually within a metre.
- **Where the sea ends.** The sea ends at OpenStreetMap's coastline, and a lake at its HydroLAKES outline, both read through `tools/lib/shapes.py`, a shared library: a point inland of it, behind a lock or a dike, is never seabed. Water joined to a lake belongs to it: inland ground more than 1 m below the lake's level that also looks like water (at or below sea level, inside a lake with no level of its own, or within 100 m of the outline) takes the lake's level when it is reached from the outline without leaving such ground. That brings in the shallow shore the outline misses, a lake with no level of its own, and a canal held at the lake's level up to its lock, and stops at the coastline, at another lake, and at dry ground, such as the valley below a lake on a plateau. A point query traces it on the map's own 6 m grid, so both read the same water.
- **A failed download stops the run.** A refusal, a short or unreadable file or an unreachable server ends the run with what failed and the URL asked for, and leaves no partial file behind. A point in a cached tile, in an extracted VDatum sub-region, needs no network.

## Before relying on it

- **A tile goes stale silently.** NOAA replaces tiles as new surveys arrive, and a cached tile keeps the old soundings. `--verify` compares the tile with NCEI's live service at the point; run it when a site's depth matters more than usual.
- **A `--verify` failure is a stop.** Report it and wait; on a failure, delete the tile and the tile list, run it again, and report it if it still fails.
- **The DEM is a model of the bottom.** It blends surveys of different ages and densities, and a narrow wall or a pinnacle smaller than a few pixels is smoothed. Good to a metre or two at most dive sites.

## `tools/ncei_depth.py`

Standard library only.

```sh
python3 tools/ncei_depth.py <lat> <lon>                     # depth below NAVD88 (~mean sea level)
python3 tools/ncei_depth.py <lat> <lon> --mllw              # also below MLLW, the site file figure
python3 tools/ncei_depth.py <lat> <lon> --verify            # compare the tile with NCEI's live service
python3 tools/ncei_depth.py --fetch <S> <W> <N> <E>           # download every tile touching a box, ahead of time
python3 tools/ncei_depth.py --mllw-selftest                 # the MLLW offset against answers VDatum's own service gave
```

Each answer prints the depth, the tile it came from, and with `--mllw` the depth below MLLW with the offset used. `--verify` passes when NCEI's live service answers from the same tile and its value matches one of the nine pixels at and around the point within 0.01 m.

`--mllw-selftest` computes the MLLW offset at a dozen points across the Washington sub-regions and compares each with the answer VDatum's own conversion service gave there in November 2026, passing within 3 mm. Run it after a new VDatum package, or a change to `tools/lib/vdatum.py`.

`--fetch` caches tiles ahead of time, for working with no connection: every tile touching the box of south, west, north and east edges, six at a time (`--workers`), repeated for several boxes. It skips what is already here, so a stopped run picks up where it left off. The US side of the Salish Sea is 45 tiles and 8.4 GB:

```sh
python3 tools/ncei_depth.py --fetch 47.0 -123.5 49.0 -122.0 --fetch 48.0 -124.75 48.5 -123.5
```

`ncei_depth.user_agent_email` in `tool-config.json` sets the contact address sent in the User-Agent of a download.

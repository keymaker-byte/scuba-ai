# Map export (the map viewer's data layers)

The data layers `map.html` draws: the total depth at the map's moment, the tide stations behind it, and the tidal current. Each layer is computed with the same `tools/lib/` functions the tools answer with (`lib/depth.py`'s sources for the depth, `lib/tide.py` with `lib/tide_harmonics.py` and `lib/foreman.py` for the tide, `lib/blend.py` for the current), and carries values those functions gave at sample points, which the browser reproduces before it draws anything. A point read on the map is the answer the tool gives at that coordinate.

- **Use it for.** Writing or refreshing the map's layers. Nothing in a site file or a plan reads them.
- **One call.** `python3 tools/map_export.py` writes every layer over the areas in `map/coverage.json`, downloading first whatever data it lacks. Run it after the coverage changes, after a current tool rebuild, after a new VDatum package, in January when CHS adds a year, and after a depth source's data is replaced.
- **Coverage.** `map/coverage.json` lists the areas the map shows, each with a `name`, a `label` and `boxes` as `[south, west, north, east]`. These are the map's own areas, set by the water its layers draw and kept apart from the regions sites are written in: the Salish Sea with the outer coasts of Vancouver Island and Washington, from Cape Scott and Queen Charlotte Strait to the Columbia's mouth, and the whole of Bonaire. Every layer is cut to those boxes. Adding, removing or reshaping an area, then running the export, is how the map's coverage changes; an area removed takes its current layer with it.

## Depth

The total depth at the map's moment: the seabed the depth tool answers, plus the tide there. The map shows no datum; each pixel's datum only decides which tide is added to it.

- **The tiles.** `map/depth/tiles/{z}/{x}/{y}.png`, each pixel the depth the depth tool answers at its centre (`answer_on`, the chain `depth.py at` reads), to 0.1 m, and the water it is in: the sea below MLLW, the sea below Chart Datum, the sea with no tide (Bonaire's), or a lake by its outline. Ground and drying ground carry their height as a negative depth, so the tide covers them where it rises past them.
- **The tide added.** A pixel below MLLW takes the NOAA stations' tide, one below Chart Datum the CHS stations', each blended from its family's three nearest stations by the inverse square of the distance; a lake and Bonaire take none. The total is the same quantity on both sides of the border. Ground above the highest tide of the year there draws as land.
- **Each source at its own resolution.** A source is stored at the zoom that matches its grid: the NCEI DEM and the NCEI to GSC seam at zoom 14 (about 6 m a pixel at 48° N), the GSC DEM at 13, the DCBD grid at 16, the 2019 Navy survey and the DCBD seam at 14, the seam to the 1970s soundings at 13, and the soundings themselves at 12. A zoom 12 tile covers all the water; a finer tile exists only where a source that fine answers, holding only that source's pixels. The viewer reads at each point the finest tile with a value there, so no source is drawn coarser or finer than it is, and the join between two sources is the depth tool's own seam. Zooms 8 to 11 are the means of the tiles below them, for drawing alone.
- **Checks.** 16 sample pixels of every source and lake, each read back from the tiles as the viewer reads them and asked of the depth tool at the pixel's centre. A difference in depth, water or source stops the export before the layer's description (`map/depth/depth.js`) is written. The browser reads the same points back, at a place inside each pixel clear of every finer tile's pixel edges, and refuses the layer on a difference past 0.06 m.
- **Lakes.** Each lake the NCEI DEM holds water in, with the level the depth tool finds for it, and the water joined to it.

## Tide stations

`map/tides/stations.js`: every tide station within 0.3° of the boxes that carries its own harmonic constants, grouped by the datum its heights are above.

- **NOAA's reference stations.** Their constants with each year's node factors and arguments, held for the UTC year as `lib/tide_harmonics.py` holds them, for the year before the export to ten years after it.
- **CHS's stations.** Their constants fitted by Foreman's method, with the part of Foreman's table they use; the browser moves the node factors day by day as `lib/foreman.py` does. A station not yet fitted is fitted during the export, about three minutes each at the 30 requests a minute CHS allows.
- **Left out and named.** NOAA's subordinate stations, which their reference stations stand for in the blend, and every station that answers nothing: a CHS station whose fit falls short, one CHS lists as non-tidal or with no predictions, and one whose series has a gap (`tide.md`'s CHS section).
- **Checks.** Each station's heights at 4 sample moments, which the browser reproduces within 2 mm, and its highest tide of the year.

## Current

One overlay per area, from the built current tool region holding it, 2 m above the seabed: every mesh element in the boxes whose corners all have a seabed depth. The browser runs the tool's blend at the point under the pointer over the seabed the depth layer reads there, as `extract` and `at` do.

- **Cells.** `map/currents/<area>-seafloor/`: one file every cell shares (`common.js`: the stations, the astronomy and the coastline), and the cells, a quadtree over the elements' centroids split while a cell owns more than 4,000 mesh nodes. A cell carries the mesh within 2 km past its edge as well, as far as any point inside it reaches into the mesh, so a point reads on the cell alone what the whole mesh gives. The viewer loads the cells in view from zoom 9 in, and the cell under the pointer at any zoom.
- **Checks.** Each cell carries the tool's current at two of its own nodes and at up to three points inside its own elements, and the area 20 points just off the mesh's shoreline, where the constants come from the mesh's edge; the browser reproduces a cell's values within 1 mm/s and 0.15° before the cell draws.
- **The region.** An area's boxes lie inside the current tool's region holding it; a box past the region stops the export with the `current.py build` to run over it.

## Before relying on it

- **The browser refuses what it cannot reproduce.** A sample value off by more than the layer allows stops that layer, or that current cell, with a message naming the check.
- **Data downloads on first use.** Each source is downloaded the first time it is needed, so a first export can run long. A failed download stops the run with what failed and the URL; report it and wait.
- **The map is served.** The viewer reads tile pixels, which a browser allows only for a page served from a web address, so the depth layer and the current readout work on the published map and stay blank on a `map.html` opened from disk. Each export stamps its files' addresses, so a browser never pairs one export's description with another's tiles.

## `tools/map_export.py`

Standard library only.

```sh
python3 tools/map_export.py                  # every layer, over map/coverage.json
python3 tools/map_export.py tides            # map/tides/stations.js
python3 tools/map_export.py currents         # map/currents/<area>-seafloor/ and map/currents/index.js
python3 tools/map_export.py depth            # map/depth/tiles/ and map/depth/depth.js
```

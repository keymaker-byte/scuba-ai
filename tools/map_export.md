# Map export (the map viewer's data layers)

The data layers `map.html` draws: the tidal current, the depth with the tide at the map's moment, and the tide stations behind it. Each layer is computed with the same `tools/lib/` functions the tools answer with (`lib/blend.py`, `lib/ncei.py`, `lib/tides.py`), and carries values those functions gave at sample points, which the browser reproduces before it draws anything. A point read on the map is the answer the tool gives at that coordinate.

- **Use it for.** Writing or refreshing the map's layers. Nothing in a site file or a plan reads them.
- **Coverage.** `map/coverage.json` lists the areas the map shows, each with a `name`, a `label` and `boxes` as `[south, west, north, east]`. Every layer is cut to those boxes, so the depth and the current cover the same water. Adding, removing or reshaping an area there, then running the export, is how the map's coverage changes; an area removed takes its current layer with it.
- **Depth.** Every NCEI tile touching the boxes is downloaded first, then the pixels inside the boxes are drawn, each area with its own lakes and coastline. The depth below NAVD 88 is placed on MLLW in the browser with the tide stations layer.
- **Tide stations.** Every reference station inside the boxes with constants and an MLLW datum, and the points where NAVD 88's height above MLLW is known: the stations NOAA ties to NAVD 88 and the VDatum answers `ncei_depth --mllw` has kept.
- **Current.** One layer per area, from the built Blend Model region holding it, at 2 m above the seabed. Inside the boxes it covers every mesh element whose corners all have a seabed depth.
- **The browser refuses a layer it cannot reproduce.** A sample value off by more than the layer allows stops that layer with a message naming the check.
- **Data downloads on first use.** Each source is downloaded the first time it is needed, so a first export can run long. A failed download stops the run with what failed and the URL; report it and wait.
- **When to run it.** After `map/coverage.json` changes, after a Blend Model rebuild (`currents`), after new VDatum answers or a new year (`tides`), and after a tile is replaced (`depth`).
- **The depth layer is served.** The viewer reads tile pixels, which a browser allows only for a page served from a web address, so the depth layer and the exact current readout work on the published map and stay blank on a `map.html` opened from disk.

## `tools/map_export.py`

Standard library only.

```sh
python3 tools/map_export.py                  # every layer
python3 tools/map_export.py currents         # map/currents/<area>-seafloor.js and map/currents/index.js
python3 tools/map_export.py depth            # map/depth/ncei/{z}/{x}/{y}.png and map/depth/ncei.js
python3 tools/map_export.py tides            # map/tides/stations.js
```

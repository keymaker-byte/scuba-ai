# Depth (seabed depth at any point)

<https://www.ncei.noaa.gov/products/coastal-elevation-models>, <https://vdatum.noaa.gov>, <https://open.canada.ca/data/en/dataset/e6e11b99-f0cc-44f7-f5eb-3b995fb1637e>, <https://www.dcbd.nl/resource/2869>

The seabed depth at a point, below the datum of the water it lies in: MLLW in US tidal water, CHS Chart Datum in Canadian tidal water, the lake's own surface in a lake, and a plain observed depth on Bonaire's reef. The tool picks the bathymetry that covers the point and names it in every answer, so a site file and a plan read one tool wherever the site is. Every source keeps its data on this machine: each piece is downloaded once, the first time a point inside it is asked for, and every depth after that is read with no request at all.

- **Use it for.** The water depth at a dive point, which goes in the site file's Coordinates row and in the site JSON's `seabed_m`, with the datum it is on in `seabed_datum`, the seabed the current tool's height above the bottom is measured from. A spatial current model's own mesh cannot supply it: its elements can span from the beach to the deep basin, so its nearshore depth can be wrong by tens of metres.
- **Also a sanity check on a coordinate.** Is this point underwater at all, and at a divable depth? It reads the actual bottom where a nautical chart gives scattered soundings between wide contours.
- **Which source answers.** The first source in the tool's list that covers the point, or with `--datum K` the first one whose answer is on that datum. A point no source covers, or none on the datum asked for, stops the run naming what each source gave.
- **Datum.** MLLW in US water, the datum NOAA's charts and its tide and current predictions use; CHS Chart Datum in Canadian water, the datum Canadian charts and CHS's tide predictions use, Lower Low Water, Large Tide on the Pacific coast, which sits 0.8 to 1.3 m below MLLW in the Salish Sea; the lake's surface in a lake, which has no tide; none on Bonaire's reef, whose tide of about 30 cm sits inside the grid's own precision. Every answer names its datum by its name from `tools/lib/datums.py`, `[datum MLLW]`, `[datum CHS]`, `[datum LAKE]` or `[datum NONE]`, the name a site JSON's `seabed_datum` and the tide tool use. The two tidal datums are different surfaces, so a depth from one is never compared with a depth from the other, nor added to a tide above the other.
- **Across the border.** The NCEI tiles along the 49th parallel reach into Canadian water, and wherever they hold data they answer first, below MLLW: around the south Gulf Islands from Saturna to the Pender Islands, the NCEI DEM answers. A Canadian site's depth is read with `--datum CHS` (or `--file`, whose `seabed_datum` is `CHS`), which skips NCEI and answers from the GSC DEM, so the depth sits on the datum of the CHS tide station it is planned with. In that water the NCEI DEM is also the weaker reading: across Boundary Pass and Haro Strait, against CHS's own Chart Datum bathymetry (NONNA-10), the GSC DEM reads 0.33 m deeper at the median and the NCEI DEM 1.45 m deeper, where a true MLLW depth would read about 0.9 m shallower. A point in a border tile with no NCEI data there, and every point north of the tiles, falls to the GSC West Coast DEM, below Chart Datum. The GSC DEM also covers the Washington side of the Salish Sea, where NCEI answers first.
- **No depth.** A point on land, on the shore, inland of the coastline in water no lake holds, or in a lake whose water level the source cannot find, gives no depth and the reason. Walk the coordinate out and ask again.
- **A site JSON.** `at --file` reads the JSON's `lat`, `lon` and `seabed_datum`, answers on that datum, and checks its `seabed_m` against the answer at the 0.1 m it is written to, exiting non-zero on a difference or on a missing `seabed_datum`, with the datum to add. A site on `NONE`, a plain observed depth such as Bonaire's, is checked the same way, against the DCBD grid.
- **A failed download stops the run.** A refusal, a short or unreadable file or an unreachable server ends the run with what failed and the URL asked for, and leaves no partial file behind. A point whose data is already on this machine needs no network.

## Sources

### NCEI coastal DEM

NOAA NCEI's coastal digital elevation model, at about 3 m resolution (1/9 arc-second), on NAVD 88, with MLLW from NOAA VDatum's grids.

- **Coverage.** The ninth arc-second tiles NOAA publishes, about 930 of them along the US coasts: Washington, Oregon, California, the Gulf, the Atlantic seaboard and part of Alaska, with the lakes inside them.
- **The data.** `tools/db/depth/ncei/` holds NOAA's tile list, one GeoTIFF per quarter-degree tile, and each lake's water level once read (`lake_levels.json`; deleting it reads them again). A tile is about 200 MB, so its first use takes a few minutes on a fast connection and much longer on a slow one. `fetch` downloads a whole area ahead of time. Deleting a tile, or the folder, fetches NOAA's current data on the next run, which is how a re-surveyed tile is picked up.
- **Shared code.** The tile list, the downloads and the lakes are `tools/lib/ncei.py`, the GeoTIFF reader `tools/lib/dem_tiles.py`, and the MLLW offset `tools/lib/vdatum.py`, shared libraries the map's depth layer and the current tool's seabed read the same way.
- **The value is the pixel the point falls in.** The tile's own georeferencing places each 3 m pixel, and the tool reads the one containing the coordinate. NCEI's live map service answers with a pixel half a cell to the south-east, 1.7 m away, so the two agree within a few centimetres on a gentle bottom and differ by up to 1.4 m on a steep wall.
- **MLLW comes from VDatum's grids, on this machine.** The height of NAVD 88 above MLLW runs from a few centimetres in some areas to more than a metre in others. The tool computes it at the exact point from NOAA VDatum's own transformation grids, the chain VDatum's conversion service runs: GEOID18 from NAVD 88 to the NAD83(2011) ellipsoid, HTDP's frame transformation to IGS14 at the epoch 2026.0, xGEOID20B to IGS14's gravimetric geoid, then the sub-region's `tss` grid to mean sea level and its `mllw` grid to MLLW. It reproduces answers VDatum's own service gave within 2 mm. The answer names the offset and the VDatum sub-region it came from.
- **The sub-region is read from the coordinate.** VDatum divides tidal water into sub-regions, each with its own polygons, and the tool picks the one VDatum itself picks: the highest polygon type holding the point (a priority area over tidal water), the first in VDatum's own order on a tie. A sea point in no sub-region, in a non-tidal area, or on the land side of the grids' shoreline stops the run with the reason.
- **The grids.** `tools/db/vdatum/` holds VDatum's full package as it downloads (`vdatum_all_<date>.zip`, about 3 GB), its index of sub-regions (`tidal_area.inf` and `tidal_area.dat`), and one folder per sub-region extracted from the package: the `tss` and `mllw` grids, and GEOID18 and xGEOID20B cut to the sub-region's box. A sub-region is extracted the first time a point inside it is asked for, in a second or two; after that it needs neither the package nor the network. The Washington sub-regions are about 250 MB. Deleting a folder extracts it again, which is how a new package is picked up.
- **The package is downloaded by hand.** VDatum's download page refuses automated clients, so a missing package stops the run with the page to fetch it from: <https://vdatum.noaa.gov/download.php>, the full package, saved unopened into `tools/db/vdatum/`. The newest package there by its date is the one read.
- **Sub-regions referenced to IGS14.** Every Washington sub-region, and 20 of VDatum's 52, carry their tidal grids on IGS14, the frame the chain is built for. A sub-region on NAD83 or IGS08 stops the run with its frame named.
- **Lakes.** A lake bed is an elevation above NAVD 88, with no tide and no MLLW. Its depth is the lake's water level minus that elevation. The tool reads the level from the DEM: where the survey never reached the bed, the DEM holds the flat water surface on the day it was flown, so one height repeats along the shore. A level counts when it shows along at least 10 of 12 stretches of the shore and sits within 10 m of HydroLAKES' own rough level; a lake with none, such as one surveyed right up to its walls, gives no depth. The level moves with the seasons, so a depth holds to the survey day's water, usually within a metre.
- **Where the sea ends.** The sea ends at OpenStreetMap's coastline, and a lake at its HydroLAKES outline, both read through `tools/lib/shapes.py`, a shared library: a point inland of it, behind a lock or a dike, is never seabed. Water joined to a lake belongs to it: inland ground more than 1 m below the lake's level that also looks like water (at or below sea level, inside a lake with no level of its own, or within 100 m of the outline) takes the lake's level when it is reached from the outline without leaving such ground. That brings in the shallow shore the outline misses, a lake with no level of its own, and a canal held at the lake's level up to its lock, and stops at the coastline, at another lake, and at dry ground, such as the valley below a lake on a plateau. A point query traces it on the map's own 6 m grid, so both read the same water.
- **`--verify`.** Compares the tile with NCEI's live service at the point, passing when the service answers from the same tile and its value matches one of the nine pixels at and around the point within 0.01 m.
- **`selftest`.** Computes the MLLW offset at a dozen points across the Washington sub-regions and compares each with the answer VDatum's own conversion service gave there in November 2026, passing within 3 mm. Run it after a new VDatum package, or a change to `tools/lib/vdatum.py`.

### GSC West Coast DEM

The Geological Survey of Canada's Canada West Coast topo-bathymetric digital elevation model (Open File 8963), Version 2 of 2025, gridded at 10 m, with its sea depths below CHS Chart Datum.

- **Coverage.** 47.2° to 56.2° N and 134.8° to 120.9° W: the whole British Columbia coast and its continental shelf, the Canadian side of the Salish Sea (the Strait of Georgia, Haro Strait, the north shore of Juan de Fuca Strait, Howe Sound, Burrard Inlet and the Gulf Islands), and the Washington side, where NCEI answers first.
- **What it is built from.** CHS multibeam surveys from 1997 to 2024 at 1 to 5 m, DFO's coastal elevation model, NRCan's regional bathymetry from CHS contours, Ocean Networks Canada's Lower Mainland DEM and Washington DNR lidar, all resampled to one 10 m grid on BC Albers. Where multibeam covers the bottom the grid follows it closely; between surveys it is interpolated from older soundings and contours.
- **The data.** `tools/db/depth/gsc/` holds `index.json` (where the GeoTIFF sits inside NRCan's zip, and the zip's date), the GeoTIFF `WestCoastDEM_Version2_Elevation.tif` (7.9 GB, a BigTIFF) and its world file. It is one file, downloaded the first time a point inside its extent is asked for: 7.3 GB of NRCan's 12.2 GB zip, read out of the zip with byte range requests and unpacked as it arrives, with the zip's own size and CRC checked; the relief shading, source map and overviews in the zip stay on the server. A stopped download starts over. Deleting the folder fetches NRCan's current package on the next run.
- **Shared code.** The download, the projection and the reading are `tools/lib/gsc.py`, the GeoTIFF reader `tools/lib/dem_tiles.py`, the coastline and lakes `tools/lib/shapes.py`.
- **The value is the pixel the point falls in,** found by projecting the coordinate to BC Albers (EPSG:3005, NAD83 on GRS 80) and placing it on the grid by the world file. The coordinate is taken as NAD83; WGS 84 sits about 1 m from it in British Columbia, a tenth of a pixel.
- **Datum.** CHS Chart Datum in Canadian water: the compilers reduced every bathymetric source to it, and on flat bottom in Boundary Bay, the Strait of Georgia, Howe Sound, Saanich Inlet, the Gulf Islands and Burrard Inlet it agrees with CHS's own Chart Datum bathymetry (NONNA-10) within 0.01 to 0.30 m at the median of each area. In US water it sits on another surface: on flat bottom from Boundary Pass to Semiahmoo Bay it reads about 0.5 m shallower than the NCEI DEM's depth below MLLW, where Chart Datum would read about 1 m deeper, so its Washington side is read only as a placeholder; NCEI answers first there. The tool holds no line for the maritime boundary, so `--datum CHS` at a point in US water still answers from this DEM, on that other surface: a US site is read on `MLLW`, its region's datum. The land heights keep each land source's own datum, so a value above zero is read only as dry ground.
- **Drying ground.** A value at or above Chart Datum dries at low water and gives no depth, with the drying height.
- **Where the sea ends.** OpenStreetMap's coastline, as for NCEI: a point inland of it is never seabed. The DEM carries a lake as land surface, so a point in a HydroLAKES lake gives no depth.
- **`--verify`.** Reads the pixel value from NRCan's map service, its West Coast DEM Elevations layer, over a window a few metres across so it answers at full resolution, and passes when it matches one of the nine pixels at and around the point within 0.01 m.
- **`selftest`.** Projects five coordinates to BC Albers and compares each with the figure Esri's geometry service gave for NAD83 to EPSG:3005 in November 2026, passing within 1 mm. Run it after a change to `tools/lib/gsc.py`.

### DCBD coastal bathymetry of Bonaire

E. Meesters' 2020 coastal bathymetry of Bonaire and Klein Bonaire, published on the Dutch Caribbean Biodiversity Database, gridded at 2 m, a plain observed depth (`NONE`).

- **Coverage.** Both islands from the shoreline out as deep as the survey reached: 20 m at most, often about 10 to 12 m. The grid's extent runs 12.01° to 12.34° N and 68.44° to 68.19° W. Land, water deeper than the survey and anything unsurveyed hold no data. At 2 m it resolves the terrace, the sand and the reef crest a coarse grid averages into one figure.
- **The data.** `tools/db/depth/dcbd/` holds the GeoTIFF `bonaire_depth_hires2.tif` (48 MB) and `index.json`: the date it was fetched, and the zip's size and the grid's size and CRC as DCBD served them. It is one file, taken out of DCBD's 34 MB zip the first time a point inside the extent is asked for, its CRC checked against the zip's own. Deleting the folder fetches DCBD's current package on the next run.
- **Shared code.** The download, the projection and the reading are `tools/lib/dcbd.py`, the GeoTIFF reader `tools/lib/dem_tiles.py`. The current tool's seabed reads the same grid.
- **The value is the pixel the point falls in,** found by projecting the coordinate to WGS 84 / UTM zone 19N (EPSG:32619), the grid's own projection, and placing it by the GeoTIFF's tags.
- **Datum.** The dataset states none; its values sit at about sea level, with the shoreline at zero. Bonaire's tidal range of about 30 cm sits inside the grid's precision, so the depth is a plain observed one, on `NONE`.
- **The spread around a point.** Each depth also gives the shallowest and deepest pixel within 10 m, the relief right around the point: a narrow spread on the terrace or sand, a wide one on the drop-off.
- **No data at a pixel.** The answer gives no depth and names the nearest pixel with data within 100 m, with its distance, bearing and depth, so the edge of the survey shows where the reef keeps going deeper. The grid starts a few metres off the waterline, where the water is already 2 to 5 m deep off a rocky shore, so an entry point on the rocks reads no data, with the first water beside it. A depth past the survey's edge comes from `emodnet_depth`, on LAT.
- **`--verify`.** DCBD serves the grid as a file, with no depth at a point, so the check is on the file: one byte range request reads the directory of the zip DCBD serves now, and passes when the zip's size and the grid's size and CRC match the ones in `index.json`.
- **`selftest`.** Projects five coordinates to UTM zone 19N and compares each with the figure Esri's geometry service gave for WGS 84 to EPSG:32619 in November 2026, passing within 1 mm. Run it after a change to `tools/lib/dcbd.py`.

## Before relying on it

- **Data goes stale silently.** A source replaces its data as new surveys arrive, and the copy on this machine keeps the old. `--verify` compares it with the source's live service at the point; run it when a site's depth matters more than usual.
- **A `--verify` failure is a stop.** Report it and wait. For NCEI, delete the tile and the tile list; for the GSC DEM, delete `tools/db/depth/gsc/`; for DCBD, delete `tools/db/depth/dcbd/`; run it again, and report it if it still fails.
- **A bathymetry is a model of the bottom.** It blends surveys of different ages and densities, and a narrow wall or a pinnacle smaller than a few pixels is smoothed. Good to a metre or two at most dive sites.

## Adding a source

A source is a class in `tools/lib/depth.py`'s `SOURCES`, with its name and coverage, whether it covers a point, the depth there below the water's datum with the reading behind it and the datum's name from `tools/lib/datums.py` as `key`, a download of an area ahead of time, a check against its live service, and its own self-test, plus a section above. Its place in the list sets which source answers where two overlap: the more detailed one goes first.

## `tools/depth.py`

Standard library only.

```sh
python3 tools/depth.py at <lat> <lon>                          # depth below the water's datum, and the source
python3 tools/depth.py at <lat> <lon> --datum CHS              # the depth on one datum: a Canadian site inside the NCEI border tiles
python3 tools/depth.py at <lat> <lon> --verify                 # also compare the source's data with its live service
python3 tools/depth.py at --file <path/to/slug.json>           # the same at a site JSON's coordinate, on its seabed_datum, checked against its seabed_m
python3 tools/depth.py transect <lat1> <lon1> <lat2> <lon2> --step 10   # the depth every 10 m from entry to dive area
python3 tools/depth.py fetch <S> <W> <N> <E> [<S> <W> <N> <E> ...]   # download every source's data touching the boxes, ahead of time
python3 tools/depth.py selftest                                # each source's own checks
```

Each answer prints the depth below the water's datum with the datum's name, the source's own figure and the conversion between them, and the source with its tile or grid.

`transect` answers each point along the line as `at` does, every `--step` metres (default 10), and takes `--datum` the same way: walking a coordinate across the terrace to the drop-off.

`fetch` caches data ahead of time, for working with no connection: every source's data touching the boxes of south, west, north and east edges, six downloads at a time (`--workers`). It skips what is already here, so a stopped run picks up where it left off. The US side of the Salish Sea is 45 NCEI tiles and 8.4 GB; any box touching British Columbia also brings the GSC DEM, 7.3 GB, and one touching Bonaire the DCBD grid, 34 MB:

```sh
python3 tools/depth.py fetch 47.0 -123.5 49.0 -122.0 48.0 -124.75 48.5 -123.5
```

`depth.user_agent_email` in `tool-config.json` sets the contact address sent in the User-Agent of a download.

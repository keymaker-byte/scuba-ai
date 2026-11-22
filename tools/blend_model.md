# Blend Model (tidal currents at any point and height)

<https://adcirc.org/products/adcirc-tidal-databases/>, <https://api.tidesandcurrents.noaa.gov/mdapi/prod/>, <https://tides.gc.ca/en/web-services-offered-canadian-hydrographic-service>

The tidal current at any point of a built region and at any height above the seabed, 2 m by default: the ADCIRC tidal database's field, corrected constituent by constituent by every current station bin around the point, NOAA's harmonic stations and CHS's stations, and drawn onto a station's own measurement as the point nears it. It is the single current tool for the Puget Sound, San Juan Islands and Strait of Juan de Fuca regions, and for Bonaire: a site's constants are extracted once into its JSON, and every slack, speed and window in a plan comes from them. How the method works, why it is built this way, what was tried, and how to extend it to new regions, models and station networks is `tools/blend_model_design.md`.

- **Use it for.** Writing a site: `extract --site` on the site JSON, once the dive area coordinate and its seabed depth hold. Planning a dive: the slacks, the maxima and the windows at the bottom, and the fastest water above for the descent and ascent. The map's tidal current layer.
- **Exact at the stations.** At a station's own position and the height of one of its bins, the tool reproduces that bin: slack, peak speed and direction. Moving away, the station's own current gives way to the blend, half of it at 0.5 km and a fifth at 1 km.
- **Between stations.** Each station bin carries its own correction to the database, the size and timing of every constituent, its steady current and its direction. At a point, the corrections of the six nearest stations within 16 km through the water are blended at the asked height, each weighted by 1 / (d² + 1 km²), with a weight of 0.3 left on the database's own value. A station's bins are interpolated to the height; above or below them, its nearest bin is carried by the regional vertical profile.
- **Height above the seabed.** The regional profile is the median, over every NOAA station with three or more bins, of each tenth of the water column against the column average. Near the bottom the water runs slower and turns earlier: about 0.8 of the column average at 2 m above the seabed, and up to a few minutes earlier, 7 to 14 minutes where the current is weak. The lowest bins sit about 2 m above the seabed, so 2 m is the lowest height backed by a measurement; below it the profile follows the 1/7 power of the height.
- **The flood is named by the timing.** The flood direction is the end of the point's axis the water runs toward while the nearest station through the water floods. Where the point's current runs against that station's, as in a back eddy or a side channel, the flood points the other way from the station's. Where the current is a few cm/s, the timing barely ties the point to the station, and the label can flip over a few hundred metres.
- **Toward shore.** A point in the water between the database's mesh and the coastline takes the constants at the nearest point of the mesh's edge, when that edge lies within 1 km and the straight line to it stays on water. A point on land by OpenStreetMap's coastline, water more than 1 km from the mesh, and water with land between it and the mesh all stop `extract`: the point is outside the tool's coverage.
- **No station within reach.** Where no station lies within 16 km through the water, the prediction is the database's own current scaled to the height, with the flood named by the nearest station within 300 km. The header says so, and the map fades its trails there. Today this is southern Hood Canal, from Octopus Hole to Twanoh, 40 km or more from the nearest station, and the western Strait of Juan de Fuca, from Sekiu west.
- **A region with no stations.** A region whose box holds no current station, Bonaire today, predicts the database's own current everywhere, scaled to the height by the 1/7 power law, since it has no measured profile of its own. Its flood and ebb are the two ends of the current's axis, unnamed, and the header says so. `verify` has nothing to test there.
- **Its sources.** A region is built from what the other tools keep on this machine, read through three seams that each take a new source without touching the method. The tidal database: ADCIRC's ENPAC15 or EC2015 (`adcirc_current`), whichever holds the region's box. The station networks, `tools/lib/current_stations.py`: NOAA's harmonic stations (`noaa_current`) and CHS's stations (`chs_current`); CHS publishes predictions without constants, so `build` fits constants to a year of each CHS station's predictions and treats the series as one bin at mid-depth. The bathymetries for the seabed under each station and each map node, `tools/lib/seabed.py`: the NCEI tiles (`ncei_depth`) and the DCBD grid of Bonaire (`dcbd_depth`), with the database's own depth where neither covers a station. `verify` also reads the 2010 legacy tables (`noaa_legacy_current`). NOAA's subordinate and weak stations and the legacy stations carry no constants of their own and stay out of the correction.
- **How close it is.** `verify` runs three tests over 30 days of December 2026 on the Salish Sea region:
  - **At the stations.** 395 bins of NOAA stations, each predicted at its own position and height with the station in place: 0 minutes on slack, 0% on peak speed and 0° on direction.
  - **Hidden stations.** Each of 135 NOAA stations' deepest bin, predicted with that station left out: slack within 34 minutes at the median (80% within 56) and peak speed within 28%, against 45 minutes and 38% copying the nearest other station, and 40 minutes and 30% from the database alone. By the nearest remaining station: within 2 km 24 minutes (13 stations), 2 to 6 km 33 minutes, 6 to 16 km 36 minutes, beyond 16 km 48 minutes (2 stations).
  - **Legacy tables.** The 117 subordinate stations of the 2010 tables, near the surface: slack within 25 minutes and peak speed within 25%, against 29 minutes and 26% for the nearest station and 42 minutes and 35% for the database alone.
- **Hard places.** A weak, eddying current off a point, in a bay or behind pilings can differ by an hour from a station a km away, and the database's elements, 0.5 to 1.3 km across along much of the shore, cannot see it. Where the pin sits in an element touching the shore, the axis can follow the mesh's coarse coastline. A site's prose, from research and observation, describes that local water; an observed offset corrects its timing.
- **Tidal currents only.** Wind drift, river outflow and the year-to-year change in the estuarine flow are absent, as in the database itself.
- **Times.** `--tz` is required on every command that prints a time: the site's own IANA zone, the `tz` in its JSON. Every time prints in that zone, named in the header, daylight time included.
- **Offline.** `build` and `export-map` read only cached data, and stop with the command that caches what is missing. A missing NCEI tile leaves the map layer's nodes there out; it never starts a download.

## The site JSON

`extract --site` reads the site's `lat`, `lon` and `seabed_m` (the seabed depth below the region's datum), and writes `blend_model_current` into the same file. `predict`, `window` and `at` read only that object, so a plan needs no database.

- **`extract_point`.** The `lat`, `lon` and `seabed_m` the extract was taken for, and `extracted`, the moment it was taken, in UTC.
- **`flood_dir`, `ebb_dir`.** The point's flood and ebb directions, degrees true.
- **`bottom`.** The prediction at `above_bottom_m`: `cons`, every constituent's amplitude (cm/s) and phase in NOAA's own form, along the flood direction, and `mean_major`, the steady current (cm/s, flood positive).
- **`upper`.** The same at the height above where the semidiurnal current is strongest, searched in twentieths of the water column, for the descent and ascent.
- **`stations`.** The stations behind the correction, each with its `id`, `name`, `km` through the water, and `sets_flood_ebb_direction`, true on the one whose flood names the point's.
- **`blend_model_observed_offset`.** Beside `blend_model_current`, once established: `before_flood_min` and `before_ebb_min`.

## Observed offset

The minutes between the model's slack and the slack divers time at the site, one figure for slack before flood and one for slack before ebb, measured from the dive log alone.

- **Observations.** Timed slacks from the site's logged dives, each a computer bookmark or a "slack HH:MM" note, read with `subsurface_log.md`.
- **Measured against.** The model's own slack nearest the observation that day, read with `predict --raw`, so an offset already applied never feeds its own measurement. A slack followed by the flood is a slack before flood, and one followed by the ebb a slack before ebb. Each observation is its time minus the model's, in minutes, positive when the site turns later.
- **Established.** At 4 observations of the same slack on 4 different days, springs and neaps both, all within 10 minutes of their median. The offset is that median, to the minute. Otherwise it is not established and the site carries none.
- **Recorded.** In the site JSON as `blend_model_observed_offset`, with `before_flood_min` and `before_ebb_min`, a slack not established left as `null`, and in the site file's Current section. The tool moves each slack by its own offset and the moments between two slacks by an offset running evenly from one to the other, and says so in its header.
- **Measured again.** After every new extract, since the model the minutes were measured against has moved. The observations stay in the log, so the offset is recomputed from them, never carried over.

## Before relying on it

- **Rebuild after the sources change.** A station NOAA re-surveys, a new CHS year, or new NCEI tiles reach the tool through `build`, then `verify`, then `export-map`, then `extract --site` on every site in the region.
- **An extract goes out of date.** `predict`, `window` and `at` warn in their header when the site JSON's `lat`, `lon` or `seabed_m` differs from the extract's, or when the region was rebuilt after `extracted`. Run `extract --site` again.
- **The seabed depth sets the height.** The height above the seabed, as a fraction of the depth, selects the bins and the profile; a datum difference of a metre moves the answer by a few percent.

## `tools/blend_model.py`

Standard library only.

```sh
python3 tools/blend_model.py build --name salish-sea --bbox 47.0 -125.5 50.5 -122.0                 # once per region, and after its sources change
python3 tools/blend_model.py build --name bonaire --bbox 11.9 -68.6 12.5 -68.0                      # a region with no stations
python3 tools/blend_model.py verify --name salish-sea                                               # after each build
python3 tools/blend_model.py extract --site <path/to/slug.json> [<path> ...] [--above-bottom 2]     # site file: once, and every site after a rebuild
python3 tools/blend_model.py extract --near <lat> <lon> --seabed <D> [--above-bottom 2]             # a point that is not a site: prints the extract
python3 tools/blend_model.py predict --date 2026-07-12 --tz <IANA_ZONE> --file <path/to/slug.json>   # planning: slacks and peaks
python3 tools/blend_model.py window --date 2026-07-12 --tz <IANA_ZONE> --file <path/to/slug.json>    # planning: diveable windows
python3 tools/blend_model.py at --time "2026-07-12 09:18" --tz <IANA_ZONE> --file <path/to/slug.json> # current at a moment
python3 tools/blend_model.py export-map --bbox S W N E [--bbox ...] --name <name> --label "<area>"   # map viewer: the tidal current layer
```

`build` writes `tools/db/blend_model/<name>.json`: every station in the box with every bin's height, constants, steady current and direction, the database's constants at its position, the seabed under it and the bathymetry it came from, its distances through the water to the others, the legacy stations, and the bins the vertical profile is drawn from, stamped `built` in UTC. `--fit-year` picks the year of CHS predictions the Canadian constants are fitted to, this year by default. The Salish Sea region holds 135 NOAA harmonic stations with 859 bins and 17 CHS stations, and takes a few minutes; the Bonaire region holds none. A region file from an older layout stops every command with the message to build it again.

`verify` runs the three tests above and prints them beside the nearest station and the database alone, by distance to the nearest station, then writes `<name>_verify.json`. It takes about a minute. On a region with no stations it says so and writes the file with none.

`extract` locates each point in the region whose box holds it, streams the database's constants for all of them in one pass, and writes each extract into its own site JSON, atomically, with the stations used on stderr. Every site is read and placed before any is written, so a site the tool refuses stops the run with every file unchanged and names each refusal. `--near` with `--seabed` prints the same object for a point with no site JSON.

`predict` prints the day's slacks and maxima at the bottom, each maximum beside the same maximum in the fastest water above. `window` reports every span where the bottom current stays under `--max-speed`, with its peak there and the peak above; the threshold defaults to `blend_model.max_speed_ms` in `tool-config.json` (0.25 m/s). `at` gives the speed and direction at both heights at a moment. Every header names the flood direction and its station, the stations behind the correction, any warning that the extract is out of date, and the observed offset applied. `--raw` leaves the offset out.

`export-map` writes `map/currents/<name>.js` and its entry in `map/currents/index.js`, which the map viewer shows as its tidal current layer. The file carries the tool's inputs rather than its answers: the database's constants at every mesh node with a seabed depth inside the boxes, the stations' corrections, the vertical profile, each node's stations within 16 km through the water, the mesh's own shoreline, and the astronomy for last year to ten years ahead. The browser runs the same blend, so the current it reads at a point and a seabed is the current `extract` and `at` give there. The readout takes the point under the pointer and the seabed below MLLW from the depth layer there, which the browser reads only from the map's web address. Where it has no seabed it shows the trails' value and says so. The trails run along each node's own flood and ebb axis, the direction the tool predicts on, with the node's own seabed; a node on land or shallower than `--above-bottom` takes the deepest water at the middle of the elements around it. They are interpolated between nodes, and draw fainter where no station lies within 16 km through the water and the field is the database's own. The file also carries the tool's own values at sample nodes and at every site in the boxes, extracted afresh as `extract` does. The browser reproduces them before it draws anything and refuses the layer on a gap of more than 1 mm/s in speed or 0.15° in direction, both finer than the map prints. On the Salish Sea layer the 75 sites agree to 0.3 mm/s and 0.09°, and the slacks to 15 seconds. The export names any site JSON whose extract differs from the region as built, which `extract --site` then refreshes. The Salish Sea layer follows the depth layer's tiles:

```sh
python3 tools/blend_model.py export-map --bbox 47.0 -123.3 48.0 -122.0 --bbox 48.0 -124.0 48.8 -122.0 --bbox 48.15 -124.8 48.8 -124.0 --bbox 48.8 -124.6 49.8 -122.7 --bbox 49.8 -125.45 50.45 -123.5 --name salish-sea-seafloor --label "Salish Sea seafloor"
```

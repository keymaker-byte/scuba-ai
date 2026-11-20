# Blend Model (seafloor currents between stations)

<https://adcirc.org/products/adcirc-tidal-databases/>, <https://api.tidesandcurrents.noaa.gov/mdapi/prod/>, <https://tides.gc.ca/en/web-services-offered-canadian-hydrographic-service>

The tidal current at any point of a region and at any height above the seabed, 2 m by default: the ADCIRC tidal database's field, corrected constituent by constituent by the current stations around the point, NOAA's harmonic stations and CHS's stations, and scaled to the height through a vertical profile measured at the stations themselves. It gives a point between stations its own prediction, with the stations behind it and the error to expect at its distance from them.

- **Use it for.** A site with no current station close to it, and the water between stations. Writing a site file's Current section as a second estimate beside the governing station, or as the estimate where no station lies within a few km. Planning a dive there: the slack and the windows at the bottom, and the strongest water above for the descent and ascent. The map's seafloor current layer.
- **A station close by stays the authority.** Within about 2 km of a station, the station's own prediction at the right bin is as good or better, and the header says so. The tool earns its place from 2 km out, where copying the nearest station loses much more.
- **What it corrects.** At each station the tool compares the station's constants, the average of its bins over the water column, with the database's depth-averaged constants at the same point, constituent by constituent: the ratio holds both the size and the timing the database misses there. At a point it blends the ratios of the six nearest stations within 16 km, measured along the water through the model's mesh, each weighted by 1 / (d² + 1 km²), with a weight of 0.3 left on the database's own value. A constituent a station has too little of keeps that station's correction for its band (diurnal, semidiurnal, the higher species). The steady current, the stations' mean flow at the nearest height, is blended the same way.
- **Height above the seabed.** The bins of every NOAA station with three or more bins, against the NCEI seabed under it, give the speed and timing at each tenth of the water column relative to the column average. The near-bottom water runs slower and turns earlier: at 2 m above the seabed about 0.8 of the column average, by up to a few minutes earlier, and 7 to 14 minutes earlier where the current is weak. The lowest bins sit about 2 m above the seabed; below that the profile follows the 1/7 power of the height, so 2 m is the lowest height backed by a measurement.
- **The direction.** Each station's own axis differs from the database's there, by 10° at the median. That difference is blended between stations like the corrections and fades toward none away from them; it turns the database's axis at the point, and on the map it turns the whole flow at each node. At the stations the seafloor layer's axis then lies within 3° of the station's own at the median, against 10° for the database alone. The strength and timing corrections are measured along the database's own axis, so the turn changes the direction alone. The turned axis points toward the flood of the nearest station through the water, which the header names.
- **Its sources.** A region is built once from what the other tools keep on this machine: the cached NOAA stations (`noaa_current`), the cached CHS predictions (`chs_current`), the ADCIRC database (`adcirc_current`), the NCEI tiles (`ncei_depth`) and, for `verify`, the 2010 legacy tables (`noaa_legacy_current`). CHS publishes predictions without constants, so `build` fits constants to a year of each CHS station's predictions; refitted to 2026, they reproduce CHS's 2027 predictions to 0 to 13 minutes on slack and 0 to 12% on peak speed. NOAA's subordinate and weak stations and the legacy stations carry no constants of their own, so they stay out of the correction; the legacy stations serve `verify` as an independent test.
- **How close it is.** `verify` predicts each NOAA station's deepest bin with that station hidden, over 30 days of December 2026, and compares the slacks and maxima. Across the 135 Salish Sea stations the median slack error is 34 minutes (80% within 55 minutes) and the median peak speed error 28%, against 45 minutes and 38% copying the nearest other station, and 40 minutes and 30% from the database alone. By the nearest remaining station: within 2 km 22 minutes, 2 to 6 km 32 minutes, 6 to 16 km 37 minutes. On the 117 legacy subordinate stations of the 2010 tables, near the surface, it places slack within 27 minutes at the median and peak speed within 24%, against 29 minutes and 26% for the nearest station and 42 minutes and 35% for the database alone. With a station's own constants the same method reaches about 6 minutes; between stations about 30 minutes is the floor every alternative tried reached.
- **Hard places.** A weak, eddying current off a point or in a bay can differ by an hour from a station a km away, because the flow there is its own. Read the expected error as a typical figure, and trust an observed offset over it.
- **Tidal currents only.** Wind drift, river outflow and the year-to-year change in the estuarine flow are absent, as in the database itself.
- **Times.** `--tz` is required on every command that prints a time: the site's own IANA zone, the `tz` in its JSON. Every time prints in that zone, named in the header, daylight time included.
- **Offline.** `build` and `export-map` read only cached data, and stop with the command that caches what is missing. A missing NCEI tile leaves the map layer's nodes there out; it never starts a download.

## Before relying on it

- **Rebuild after the sources change.** A station NOAA re-surveys, a new CHS year, or new NCEI tiles reach the tool through `build`, then `verify`, then `export-map`.
- **The expected error comes from `verify`.** `extract` records the row of `verify`'s table for the point's distance to the nearest station; an extract taken before `verify` carries none, and the header says so.
- **The seabed depth is the site file's.** `--seabed` takes the Coordinates row's depth; the height above it, not the datum, sets the profile, so MLLW and NAVD 88 give the same answer to a few percent.

## `tools/blend_model.py`

Standard library only.

```sh
python3 tools/blend_model.py build --name salish-sea --bbox 47.0 -125.5 50.5 -122.0                  # once per region
python3 tools/blend_model.py verify --name salish-sea                                                # after each build
python3 tools/blend_model.py extract --near <lat> <lon> --seabed <D> [--above-bottom 2] --walk > <out.json>   # site file: once
python3 tools/blend_model.py predict --date 2026-07-12 --tz <IANA_ZONE> --file <path/to/slug.json>    # planning: slacks and peaks
python3 tools/blend_model.py window --date 2026-07-12 --tz <IANA_ZONE> --file <path/to/slug.json>     # planning: diveable windows
python3 tools/blend_model.py at --time "2026-07-12 09:18" --tz <IANA_ZONE> --file <path/to/slug.json>  # current at a moment
python3 tools/blend_model.py export-map --bbox S W N E [--bbox ...] --name <name> --label "<area>"    # map viewer: the seafloor overlay
```

`build` writes `tools/db/blend_model/<name>.json`: every station in the box with its corrections, its point in the mesh and its distances along the water to the others, the legacy stations, and the bins the vertical profile is drawn from. `--fit-year` picks the year of CHS predictions the Canadian constants are fitted to, this year by default. It takes a few minutes.

`verify` runs the two tests above and prints them beside the nearest station and the database alone, by distance to the nearest station, then writes `<name>_verify.json`, the table `extract` and the map read the expected error from. It takes about a minute.

`extract` prints two keys on stdout, `blend_model_extract_point` and `blend_model`, with the stations used on stderr, and writes no file; the object is attached to the site's `<slug>.json`. Give it the dive area's coordinate and its seabed depth. It holds two sets of constants in NOAA's own form, at the height asked for and at the fastest height above it, so `predict`, `window` and `at` run with no database at all. `--walk` takes a point outside the wet mesh at the nearest point inside it, 5 m in, and records how far it moved.

`predict` prints the day's slacks and maxima at the bottom, each maximum beside the same maximum at the fastest height above. `window` reports every span where the bottom current stays under `--max-speed`, with its peak there and the peak above; the threshold defaults to `blend_model.max_speed_ms` in `tool-config.json` (0.25 m/s). Every header names the stations behind the numbers, their distances, the flood direction's station and the expected error.

`export-map` writes `map/currents/<name>.js` and its entry in `map/currents/index.js`, marked as a seafloor overlay, which the map viewer shows as its tidal current layer. It corrects every mesh node with a cached NCEI depth inside the boxes and scales it to `--above-bottom` over that node's depth (the whole column where the water is shallower). It also carries each node's distance to the nearest station, which fades the trails beyond 2 and 6 km. The file carries values the tool computed from it, which the browser reproduces before it draws anything, and the coastline that keeps its trails off land, as the depth-averaged overlay does. The Salish Sea layer follows the depth layer's tiles:

```sh
python3 tools/blend_model.py export-map --bbox 47.0 -123.3 48.0 -122.0 --bbox 48.0 -124.0 48.8 -122.0 --bbox 48.15 -124.8 48.8 -124.0 --bbox 48.8 -124.6 49.8 -122.7 --bbox 49.8 -125.45 50.45 -123.5 --name salish-sea-seafloor --label "Salish Sea seafloor"
```

# Current (tidal currents at any point and height)

<https://adcirc.org/products/adcirc-tidal-databases/>, <https://api.tidesandcurrents.noaa.gov/mdapi/prod/>, <https://tides.gc.ca/en/web-services-offered-canadian-hydrographic-service>

The tidal current at any point of a built region, 2 m above the seabed and in the fastest water above: an ADCIRC tidal database corrected by the current stations around the point, NOAA's in US water and the Canadian Hydrographic Service's in Canadian water, and equal to a station's own current at its position. Both networks correct the database the same way, so a site reads one tool on either side of the border. A site's constants are extracted once into its JSON, and every slack, speed and window in a plan comes from them.

- **Use it for.** Writing a site: `extract --site` once the dive area coordinate and its `seabed_m` hold. Planning a dive: `predict`, `window` and `at` on the site JSON. Timing an observed offset: `predict --raw`. The map's tidal current layer is written by `map_export.md` from the same library, `tools/lib/blend.py`.
- **A refused extract stops the site.** The tool refuses a point outside its coverage and says why. Report it and wait.
- **Read the header.** Every prediction names the flood direction and the station that sets it, the stations behind the correction, and the observed offset applied, and warns when no station lies within reach (the prediction is the database's own current) or when the extract is out of date (run `extract --site` again).
- **Hard places.** A weak, eddying current off a point, in a bay or behind pilings can differ by an hour from a station a km away; the site's prose describes that water, and an observed offset corrects its timing.
- **Tidal currents only.** Wind drift and river outflow are absent.
- **Every site has an extract, a lake's included.** A site JSON on `LAKE` takes `extract --site` like any other, without reading the database: a lake has no tide, so it has no tidal current, and its extract holds no constants, no axis and no station. `predict`, `window` and `at` answer 0 m/s at every moment and height, with a header naming the lake, so a plan reads the current the same way at every site.
- **A CHS station is a fit to CHS's predictions.** CHS publishes predictions and keeps its constants to itself, so `build` fits each CHS station's constants to this year's predictions. At the station they follow CHS's own slacks within 3 minutes at the median and 9 minutes for 90% of them, and peak speed within 5%; at a few rapids and narrows whose current is far from a sum of tides (Tillicum Bridge, Juan de Fuca East, Sechelt Rapids) a slack can sit 20 to 30 minutes from CHS's. CHS's own Tide and Current Tables are the official word for timing a dive at one of its stations.
- **Times.** `--tz` is required on every prediction: the site's `tz` from its JSON.
- **Data downloads on first use.** Each source is downloaded the first time a command needs it and read locally after that, into `tools/db/`, so a first `build` can run long: a CHS station's year takes about two minutes, at the 30 requests a minute CHS allows. Deleting a source's folder fetches its current data on the next run. A failed download stops the run with what failed and the URL; report it and wait.

## The site JSON

`extract --site` reads `lat`, `lon`, `seabed_m` and `seabed_datum`, and writes `current`: the point it was taken for (its `lat`, `lon`, `seabed_m` and `seabed_datum`) and when, `flood_dir` and `ebb_dir` in degrees true, the constants at the `bottom` and `upper` heights, and the `stations` behind the correction, each with its `id`. On `LAKE` both directions are `null`, both heights' constants empty and no station. `predict`, `window` and `at` read that object: the header says to extract again when the site's coordinate or seabed no longer matches the point the extract was taken for, and a site whose `seabed_datum` no longer matches the extract's stops the run until it is extracted again.

An established observed offset sits beside it as `current_observed_offset`, with `before_flood_min` and `before_ebb_min`, `null` for a slack not established. The tool applies it and says so in the header.

## Observed offset

The minutes between the model's slack and the slack divers time at the site, from the dive log alone.

- **Observations.** Timed slacks from the site's logged dives, a computer bookmark or a "slack HH:MM" note, read with `subsurface_log.md`.
- **Measured against.** The model's slack nearest the observation that day, from `predict --raw`. A slack followed by the flood is a slack before flood, one followed by the ebb a slack before ebb. Each observation is its time minus the model's, in minutes, positive when the site turns later.
- **Established.** At 4 observations of the same slack on 4 different days, springs and neaps both, all within 10 minutes of their median. The offset is that median, to the minute.
- **Recorded.** In the site JSON as above, and in the site file's Current section.
- **Measured again.** After every new extract, recomputed from the log.

## Upkeep

- **Stale station data.** Station networks replace their data from time to time, and the cached copy keeps the old. Run `verify-stations --file` on a site's JSON before a plan that matters more than usual, and at least once a year. A failure is a stop: delete the files the message names, then rebuild. A NOAA station passes within 0.02 m/s and 3 minutes of NOAA's live predictions, a CHS station when every cached value and event matches CHS's live API. An extract with no station behind it, a lake's or the database's own current, has nothing to verify, and says so.
- **A new year.** CHS publishes a year at a time, and `build` fits CHS stations to the current year's predictions, downloading that year when it is missing. Rebuild in January.
- **Rebuild.** After station data is replaced: `build` and `verify`, each with no `--name` to cover everything built, then `extract --site` on every site JSON, and `map_export.py currents` for the map.
- **`selftest`.** After any change to `tools/lib/adcirc.py` or `tools/lib/tcd.py`. It checks the astronomy against each database's header, and the legacy tables' reader against slack times NOAA printed in its 2013 Tidal Current Tables.

## Accuracy

`verify` runs three tests over 30 days from 1 December and writes them to `<region>_verify.json`. The figures are the Salish Sea region's, December 2026.

- **At the stations.** Every NOAA bin predicted at its own position and height reads 0 minutes on slack, 0% on peak speed and 0° on direction; any change that moves it off zero is a regression. A CHS station reads its fit's own distance from CHS: 2.7 minutes on slack at the median (90% within 8.9) and 4.6% on peak speed.
- **Between stations.** A NOAA station left out and predicted from the rest misses slack by 34 minutes at the median (80% within 56) and peak speed by 28%, against 45 minutes for copying the nearest station and 40 minutes for the database alone. By distance to the nearest remaining station: 24 minutes within 2 km, 33 minutes from 2 to 6 km, 36 minutes from 6 to 16 km, 48 minutes beyond. A CHS station left out misses by 18 minutes at the median and 35% on speed.
- **Legacy tables.** NOAA's 2010 subordinate stations, near the surface: slack within 25 minutes and peak speed within 25%, against 29 minutes for the nearest station and 42 minutes for the database alone.
- **Near shore.** Where a pin falls in a database element touching the shore, the axis follows the mesh's coarse coastline and the speed can differ from the water divers describe; the site file's prose describes that water. Under a few cm/s the flood label ties loosely to its station and can flip over a few hundred metres. Eddies behind pilings, in coves and off points are beyond any tidal database here; the observed offset and the site's prose carry them.

## Extending it

`tools/lib/blend.py` holds the method, which `current.py` and `map_export.py` both call. What it reads comes through three lists a new source joins without touching the correction:

- **Tidal databases.** `DATABASES` in `tools/lib/adcirc.py` (ENPAC15, EC2015), picked by `database_for(bbox)` as the one whose domain holds the region's box. A new model needs a mesh with element connectivity, and its constituents at any point in NOAA's convention (`to_noaa`, `TREF`); the blend sees only `uv`, the complex east and north constituents at a point.
- **Station networks.** `NETWORKS` in `tools/lib/current_stations.py` (NOAA harmonic, CHS predictions). A network is a class with a `kind`, `gather(inbox, fit_year)` returning the stations in a box and the others without constants, downloading what is missing; `prepare(station, H, Hdem, fit_year, log)` setting its `bins` and returning vertical profile rows; `owns(id)` claiming its station IDs; and `verify(id)` returning a pass and report lines against its live service. A station is a dict with `id`, `kind`, `name`, `lat`, `lon` and `flood`; each bin is [fraction of the depth, steady current cm/s, azimuth, {constituent: complex amplitude in NOAA's convention}]. A network that publishes predictions alone follows CHS's route: fit constants to a year of them (`harmonic_fit`) and treat the series as one bin at mid-depth, or at its stated depth. Only a network with several bins over a known seabed adds profile rows.
- **Bathymetries.** `SOURCES` in `tools/lib/seabed.py` (NCEI tiles, the GSC West Coast DEM, DCBD Bonaire), asked in order for the seabed under each station and map node. A source is a class with a `name`, a `datum` and `elevation(lat, lon)` in metres, negative under water, or None where it holds nothing, read through the same `tools/lib/` module as the depth tool's source.
- **A new region.** `build --name <region> --bbox S W N E`, then `verify --name <region>`, whose at-stations test must read 0, 0, 0. Then `extract --site` on all of its sites, and an area in `map/coverage.json` when the map should show it. Region boxes stay apart, since `load_region` takes the first box holding a point. A region with no station takes the database's own constants, the 1/7 power law for its vertical profile, and the two ends of the axis for flood and ebb, each stated in the output.
- **Changing the method.** Change one thing, rebuild, and run `verify`, keeping the at-stations test at zero and comparing the other medians with the figures above; a change to the astronomy in `tools/lib/adcirc.py` runs `selftest` first. A change to the blend, the profile, the placing of a point or the prediction is mirrored in `map/currents.js`, and `map_export.py currents` then proves the two agree. A change to the region file's layout raises `FORMAT`, which makes every command ask for a rebuild.

## `tools/current.py`

Standard library only.

```sh
python3 tools/current.py extract --site <path/to/slug.json> [<path> ...]                        # site file: once, and every site after a rebuild
python3 tools/current.py predict --date 2026-07-12 --tz <IANA_ZONE> --file <path/to/slug.json>   # planning: slacks and maxima, bottom and above
python3 tools/current.py window --date 2026-07-12 --tz <IANA_ZONE> --file <path/to/slug.json>    # planning: spans under --max-speed at the bottom
python3 tools/current.py at --time "2026-07-12 09:18" --tz <IANA_ZONE> --file <path/to/slug.json> # planning: speed and direction at a moment
python3 tools/current.py predict --raw --date 2026-07-12 --tz <IANA_ZONE> --file <path/to/slug.json>   # observed offset: the model without it
python3 tools/current.py verify-stations --file <path/to/slug.json>                             # a site's stations against their networks' live services
python3 tools/current.py build [--name <region> --bbox S W N E]                                 # rebuild every region, or build a new one
python3 tools/current.py verify [--name <region>]                                               # after each build
python3 tools/current.py selftest [--db <database>]                                             # after a change to tools/lib/adcirc.py or tools/lib/tcd.py
```

`window`'s threshold defaults to `current.max_speed_ms` in `tool-config.json`. `verify-stations` also takes `--name <region>` for every station of a region, or station IDs as an extract lists them. A built region keeps its box, so naming one alone rebuilds it as it was.

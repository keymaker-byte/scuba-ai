# Current (tidal currents at any point and height)

<https://adcirc.org/products/adcirc-tidal-databases/>, <https://api.tidesandcurrents.noaa.gov/mdapi/prod/>, <https://tides.gc.ca/en/web-services-offered-canadian-hydrographic-service>

The tidal current at any point of a built region, 2 m above the seabed and in the fastest water above: an ADCIRC tidal database corrected by the current stations around the point, NOAA's in US water and the Canadian Hydrographic Service's in Canadian water, and equal to a station's own current at its position. Both networks correct the database the same way, so a site reads one tool on either side of the border. A site's constants are extracted once into its JSON, and every slack, speed and window in a plan comes from them. How it works, how accurate it is, and how to extend it is `tools/current_design.md`.

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

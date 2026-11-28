# Forecast (wind, waves, surface current, weather and hazards at a site)

<https://api.weather.gov>, <https://open-meteo.com/en/docs/ecmwf-api>, <https://open-meteo.com/en/docs/marine-weather-api>

The forecast at a dive site, in five blocks: the wind with its go / no go call against the site's own sectors, the waves with their call against the entry's shore, the surface current and the water temperature, the weather and the temperature with its call on fog and thunder, and the hazards and warnings in effect, each with its band. Each block is answered by the first source in its list that covers the site, so a plan reads one tool wherever the site is: the National Weather Service in US water, Open-Meteo anywhere. Every answer names its source, its grid point and how far that sits from the site.

- **Use it for.** Every plan: `at` at the entry and the exit time, `day` for the hour by hour picture and the best window, both with the site JSON as `--file`.
- **Two points of the site.** Wind, weather and hazards are read at the land point, the entry point (the dive area at a boat site), where the diver kits up and gets in. Waves and the surface current are read at the sea point, the dive area, out over the water.
- **The site JSON.** `--file` reads the dive area (`lat`, `lon`), the zone (`tz`), and from the `wind` section written by `shore_exposure.md` the entry point, the Bad sectors, the Short fetch and Mixed sectors, and each compass point's shore relation, the one its waves call reads. A site JSON with no `wind` section, or one taken at another coordinate, stops the run with the extract to run. A site on `LAKE` takes no wave or ocean reading: its chop is the wind call's.
- **By hand.** `--near` names the land point and `--tz` the zone, `--sea` the sea point (`--near` by default), and `--bad` and `--short` the sectors in compass shorthand, `SW-WNW` or `N`, several comma separated or repeated. With no sectors the wind and waves carry no call.
- **Blocks.** `--block` names the blocks to read, comma separated or repeated: `wind`, `waves`, `current`, `weather`, `hazards`. Every block is read by default.
- **Times.** Every time is read and printed in the site's own zone, the `tz` in its JSON, which `--file` reads and a `--tz` beside it must match.
- **A failed source stops the run.** A refused, unreachable or unreadable request, or a time outside a source's forecast window, ends the run before anything is printed, naming the block, what failed and the URL asked for. A block no source covers prints as not covered, with the reason.

## The blocks

### Wind

The sustained speed at 10 m, its direction (where it blows from), the gust and whether it blows onshore, cross-shore or offshore at the entry (the dive area at a boat site), with the call.

- **Sources.** NWS's gridpoint forecast where a public forecast zone or a coastal marine zone holds the land point; Open-Meteo, ECMWF IFS with GFS as a cross-check, everywhere else. `--source open-meteo` reads Open-Meteo in US water too; `--source nws` reads NWS alone, and a point it does not cover prints as not covered.
- **The call.** Each reading gets go, marginal or no go, with the sector kind it fell in:
  - **Bad.** Go under `go_below_ms` (5 m/s), marginal from there to `nogo_above_ms` (8 m/s), no go above it.
  - **Short.** The same bands, each moved up by `short_fetch_shift_ms` (3 m/s). The Short fetch and Mixed sectors both read here.
  - **Fine.** Go up to `offshore_marginal_ms` (8 m/s) and marginal above it, on the sustained speed alone, for the surface drift an offshore wind puts on a diver; the entry itself stays flat.
  - **Gusts.** On a bad or short reading, a gust more than `gust_margin_ms` (3 m/s) above the sustained speed moves the call up one band, for the chop gusts build on the entry.
- **The limits.** Anchored to the Beaufort scale's sea state: Beaufort 3 (3.4 to 5.4 m/s) is wavelets and scattered whitecaps, Beaufort 4 (5.5 to 7.9 m/s) small waves and frequent whitecaps, Beaufort 5 (8.0 to 10.7 m/s) moderate waves and many whitecaps.
- **Two models.** On Open-Meteo, each model gets its own call; a reading where the two differ by more than 3 m/s or 30° is flagged, and a reading where their calls differ is flagged too. The plan carries the more severe call.

### Waves

The significant wave height, its direction (where the waves come from) and period, split where the model carries it into wind waves, the primary swell and the secondary swell, with the call.

- **Source.** Open-Meteo's marine API: Meteo-France's MFWAM at about 8 km (`meteofrance_wave`, about 9 days ahead), with ECMWF's WAM at about 25 km (`ecmwf_wam025`) as a cross-check, flagged where the two differ by more than 0.3 m, or by more than 30° on waves of 0.3 m or more.
- **The call.** The height banded where the waves come from a direction onshore or cross-shore at the entry (the dive area at a boat site), by the site JSON's shore relation for that compass point: go under `waves_go_below_m` (0.5 m), marginal to `waves_nogo_above_m` (1 m), no go above it. Waves from an offshore direction are go.
- **Open water.** A wave model's cell is open water, and a cell near the coast steps out to the nearest one holding sea. The grid point's distance is printed, and past `grid_far_km` (5 km) it is flagged: the reading is the sea outside, a headland, a harbour or a spit between it and the entry changes what reaches the beach. The waves breaking at the entry are judged from the shore before kitting up. Across the sites written so far the grid point sits a median of about 3 to 4 km out in Puget Sound, the San Juan Islands and Bonaire, up to 23 km in Puget Sound, and 7 to 17 km out along the Strait of Juan de Fuca, whose shore sites the model reads from mid-strait.
- **Where it reads.** Open coasts, the straits and the main basins. Water neither model holds, such as Hood Canal, the inlets west of Seattle and the Sound south of Seattle, reads as no wave model holding the water.

### Surface current

The current at the sea surface, its speed and the direction it flows toward, and the water temperature at the surface.

- **Source.** Open-Meteo's marine API, Mercator's global ocean model (SMOC, `meteofrance_currents`) at about 8 km: the ocean circulation, the tide's current and the wind's wave drift together, at the surface.
- **What it is.** A picture of the drift on the surface swim and of the water out from the site, strongest as a guide where the current is wind driven. The tidal current at the site, at the bottom and the fastest water above, is `current.md`'s; this block never sets a slack.
- **Where it reads.** Open coasts and the open straits. Inland water the model leaves out, Puget Sound south of its northern entrance around Port Townsend and Admiralty Inlet, reads as no ocean model holding the water.

### Weather and temperature

The air temperature, what it feels like, the dew point and humidity, the cloud cover and the sky in words, the chance of rain and its amount, the visibility and fog, and thunder.

- **Sources.** NWS's gridpoint forecast where it covers the land point, Open-Meteo's ECMWF IFS everywhere else, by the same rule as the wind.
- **Fog.** Fog or freezing fog in the forecast's weather, or a visibility under `fog_visibility_m` (1 km).
- **Thunder.** On NWS, a probability of thunder of `thunder_probability_pct` (15%) or more, or thunderstorms in the forecast's weather. On Open-Meteo, a thunderstorm weather code, with the CAPE beside it: above about 1,000 J/kg the air holds the energy for a storm.
- **The call.** Fog takes `fog_call` and thunder `thunder_call`, both no go: in fog the entry and the shore drop out of sight from the water, and a diver on the surface is the highest point on it. With both, the more severe call stands; with neither, go.

### Hazards and warnings

Every alert in effect over the day asked for, for every NWS zone holding the land point or the sea point: public forecast zones, counties, coastal and offshore marine zones. Each carries its event, severity, start and end, headline, and the band it puts on a dive.

- **Source.** NWS's active alerts, which reach US land and water and NWS's offshore marine zones, the Caribbean's among them. A point in no NWS zone prints as not covered.
- **The land zones.** NWS's zone outlines can put a beach entry in the water. Where no public zone holds the entry, the tool walks inland, opposite the entry's shore facing, 100 m at a time up to 1 km, and takes the zones it finds there, naming the distance.
- **The band.** An event that bears on a dive, on the water, the wind, the air or the shore: a warning takes `warning_call` (no go), a watch `watch_call` and an advisory `advisory_call` (both marginal), and a statement or any other event `statement_call` (a note). Any other event, a river flood or a winter storm inland, prints as not about the water.
- **Issued ahead.** NWS issues alerts a few days ahead at most, so a dive further out reads none.

## Sources

### NWS

The National Weather Service's API: the gridpoint forecast on its 2.5 km grid, and the active alerts. No key; a User-Agent with a contact address is required, `tool-config.jsonc`'s top-level `user_agent_email`, and the tool stops if it is missing.

- **Coverage.** Read from NWS's own zones: the gridpoint answers a point in a public forecast zone or a coastal marine zone, about seven days ahead; the alerts any zone.
- **The grid cell.** A cell straddling the shoreline can read land-side conditions. NWS holds each value constant over a span of one or more hours, so `at` reports the span holding the moment.
- **A passing error.** NWS answers an HTTP 500 or drops a connection now and then; the tool tries once more after two seconds, then stops.
- **The code.** `tools/lib/nws.py`.

### Open-Meteo

Open-Meteo's weather API and marine API, free with no key for non-commercial use, at any coordinate worldwide.

- **Wind.** ECMWF IFS HRES at its native 9 km (`ecmwf_ifs`) is the verified most accurate global model for medium-range wind, ahead of NOAA's GFS by a real margin; GFS (`gfs_seamless`) comes in the same call as a second, independent model. About 16 days ahead.
- **Weather.** ECMWF IFS alone.
- **Marine.** The wave models and the ocean model above.
- **The grid point.** Every reading prints the grid point used and its distance from the point asked for. A few km is normal for ECMWF's 9 km grid; for a site tucked close to a coastline or a sharp local terrain feature, read the distance before trusting a number.
- **The code.** `tools/lib/open_meteo.py`.

## Configuration

The `forecast` section of `tool-config.jsonc`, each key explained in the file beside it and falling back to the default shown: the wind limits `go_below_ms` (5), `nogo_above_ms` (8), `short_fetch_shift_ms` (3), `gust_margin_ms` (3) and `offshore_marginal_ms` (8), the wave limits `waves_go_below_m` (0.5) and `waves_nogo_above_m` (1), `fog_visibility_m` (1000), `thunder_probability_pct` (15), `grid_far_km` (5), the calls `fog_call` and `thunder_call` (both `no go`), `warning_call` (`no go`), `watch_call` and `advisory_call` (both `marginal`) and `statement_call` (`note`), each one of `go`, `marginal`, `no go` or `note`, and the models: `wind_model` (`ecmwf_ifs`), `wind_cross_check_model` (`gfs_seamless`), `weather_model` (`ecmwf_ifs`), `wave_model` (`meteofrance_wave`), `wave_cross_check_model` (`ecmwf_wam025`) and `ocean_model` (`meteofrance_currents`), each any Open-Meteo model id.

## Adding a source

A source is a class in `tools/lib/<name>.py` with its key, name and blocks, whether it covers a block at a point, and a reading of a block over a span, in the site's own zone; the interface is written out at the top of `tools/lib/forecast.py`, and the source joins that file's `sources()` list for each block it answers, in the order the blocks ask. A national weather service outside the US, Environment Canada for British Columbia, say, goes ahead of Open-Meteo for wind and weather, and its alerts beside NWS's for hazards. It also takes a section above.

## `tools/forecast.py`

Standard library only.

```sh
python3 tools/forecast.py at --file <path/to/slug.json> --time "2026-07-12 09:30"                 # planning: every block at the entry or exit time
python3 tools/forecast.py day --file <path/to/slug.json> --date 2026-07-12                        # planning: every block for every hour of the day
python3 tools/forecast.py at --file <path/to/slug.json> --time "2026-07-12 09:30" --block wind,waves   # some blocks
python3 tools/forecast.py at --near <lat> <lon> --sea <lat> <lon> --tz <IANA_ZONE> --time "2026-07-12 09:30" --bad WSW-W --short SW,WNW-NW,S   # by hand
python3 tools/forecast.py day --near <lat> <lon> --tz <IANA_ZONE> --date 2026-07-12              # by hand, conditions alone, no call
```

The header names the site, the sectors, the land point, the shore's facing and the swim out from the entry to the dive area, the sea point and the zone; each block then names its source, grid point and update time before its readings. `at` interpolates Open-Meteo between the bracketing hours, directions on the circle. Speeds are m/s, heights m, temperatures °C; wind and waves name the direction they come from, the surface current the direction it flows toward.

### Worked examples

A Wind section reading:

```markdown
* **Bad.** West-southwest through west (WSW-W), onshore over 12 to 20 km of open water. …
* **Short fetch.** Southwest (SW), and west-northwest through northwest (WNW-NW), onshore over 1.5 to 4 km. …
* **Mixed.** South (S), along the shore over 9 km. …
* **Fine.** North clockwise through south-southeast. …
```

runs by hand as `--bad WSW-W --short SW,WNW-NW,S`; `--file` reads the same sectors from the site JSON. A calm only site, whose Bad bullet reads "All directions (N-NNW), calm only", runs as `--bad N-NNW`.

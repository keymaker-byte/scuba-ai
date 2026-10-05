# Open-Meteo wind (ECMWF IFS, GFS cross-check)

<https://open-meteo.com/en/docs/ecmwf-api>

A wind source that works at any coordinate worldwide, and the go / no go call on it. Free, JSON over HTTPS, no API key for non-commercial use.

- **Use it for.** The plan's wind verdict at the entry and the exit time: the tool reads the forecast from two models and calls each go, marginal or no go against the site's own sectors.
- **The site's sectors.** Each bullet of the site file's Wind section maps to one option: the Bad bullet's sectors go in as `--bad`, and the Short fetch and Mixed bullets' sectors as `--short`. Each sector is the compass shorthand in parentheses after it, written `SW-WNW` or `N`, several comma separated or repeated. The Fine bullet stays out: every direction left out of both options counts as fine. The worked examples below show the mapping.
- **The call.** Each model's reading gets go, marginal or no go, with the sector kind it fell in, and a reading where the two models' calls differ is flagged; the plan carries the more severe one.
  - **Bad.** Go under `go_below_ms` (5 m/s), marginal from there to `nogo_above_ms` (8 m/s), no go above it.
  - **Short.** The same bands, each moved up by `short_fetch_shift_ms` (3 m/s).
  - **Fine.** Go up to `offshore_marginal_ms` (8 m/s) and marginal above it, on the sustained speed alone, for the surface drift an offshore wind puts on a diver; the entry itself stays flat.
  - **Gusts.** On a bad or short reading, a gust more than `gust_margin_ms` (3 m/s) above the sustained speed moves the call up one band, for the chop gusts build on the entry.
- **The limits.** In `open_meteo_wind`'s section of `tool-config.json`, each falling back to the default shown, and anchored to the Beaufort scale's sea state: Beaufort 3 (3.4 to 5.4 m/s) is wavelets and scattered whitecaps, Beaufort 4 (5.5 to 7.9 m/s) small waves and frequent whitecaps, Beaufort 5 (8.0 to 10.7 m/s) moderate waves and many whitecaps.
- **Two models.** ECMWF's IFS HRES is the verified most accurate global model for medium-range wind, ahead of NOAA's GFS by a real margin in independent verification, with the gap widening at longer lead times. Open-Meteo serves ECMWF's own open data straight through as JSON at its native 9 km resolution (`ecmwf_ifs`). GFS (`gfs_seamless`) comes in the same call as a second, independent model, flagged wherever it disagrees with ECMWF by more than 3 m/s or 30°, so a plan rests on two models' word.
- **A numerical forecast.** A tide or current prediction runs years ahead; wind runs about 16 days ahead at most. Open-Meteo refuses a date outside its model window (about 16 days ahead, about 3 months back).
- **The grid point is not your point.** Both models are served off a grid, and the tool prints the grid point actually used and its distance from the coordinate asked for. A few km is normal for ECMWF's 9 km grid, more for GFS's coarser one. Read that distance before trusting a number for a site tucked close to a coastline or a sharp local terrain feature.
- **Timezone is mandatory.** `--tz` takes the site's IANA zone name; the API localizes every timestamp itself, so there is no UTC value to misread as local and no daylight saving boundary to get wrong by an hour.

## `tools/open_meteo_wind.py`

Standard library only.

```sh
python3 tools/open_meteo_wind.py at --near <lat> <lon> --time "2026-07-12 09:30" --tz <IANA_ZONE> --bad WSW-W --short SW,WNW-NW,S   # planning: the call at the entry or exit time
python3 tools/open_meteo_wind.py forecast --near <lat> <lon> --date 2026-07-12 --tz <IANA_ZONE> --bad WSW-W --short SW,WNW-NW,S     # planning: the call for every hour of the day
python3 tools/open_meteo_wind.py forecast --near <lat> <lon> --date 2026-07-12 --tz <IANA_ZONE>                             # wind alone, no call
```

Give it the entry point's coordinate. Both commands print the grid point actually used and its distance from the coordinate asked for, then each model's speed, direction and gust side by side, flagged where they disagree, with each model's call added whenever `--bad` or `--short` is given. `at` interpolates between the bracketing hours. Direction is degrees true, the direction the wind comes from. A malformed sector stops the run before any request.

`--models` overrides the pair with any comma-separated Open-Meteo model ids, the first one primary (`ecmwf_ifs025` is the coarser but guaranteed-available ECMWF tier, `icon_seamless` is DWD's ICON, `best_match` lets Open-Meteo pick). The defaults are `open_meteo_wind.primary_model` and `open_meteo_wind.cross_check_model` in `tool-config.json`.

### Worked examples

A Wind section reading:

```markdown
* **Bad.** West-southwest through west (WSW-W), onshore over 12 to 20 km of open water. …
* **Short fetch.** Southwest (SW), and west-northwest through northwest (WNW-NW), onshore over 1.5 to 4 km. …
* **Mixed.** South (S), along the shore over 9 km. …
* **Fine.** North clockwise through south-southeast. …
```

runs as `--bad WSW-W --short SW,WNW-NW,S`.

A Wind section with a Short fetch bullet alone, "Southwest through west-northwest (SW-WNW), onshore over 1.2 to 3.7 km", runs as `--short SW-WNW`.

A calm only site, whose Bad bullet reads "All directions (N-NNW), calm only", runs as `--bad N-NNW`.

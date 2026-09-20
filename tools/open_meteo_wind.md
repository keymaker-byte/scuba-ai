# Open-Meteo wind (ECMWF IFS, GFS cross-check)

<https://open-meteo.com/en/docs/ecmwf-api>

A wind source that works at any coordinate worldwide. Free, JSON over HTTPS, no API key for non-commercial use.

- **Use it for.** Wind speed, direction and gusts at the entry, hourly, on the day.
- **Why this source, not another.** ECMWF's IFS HRES is the verified most accurate global model for medium-range wind, beating NOAA's GFS by a real margin in independent verification, with the gap widening at longer lead times. Open-Meteo serves ECMWF's own open data straight through as JSON, at IFS HRES's native 9 km resolution (model id `ecmwf_ifs`), no GRIB parsing and no key required. GFS is pulled in the same call as a second, independent model (`gfs_seamless`) and flagged whenever it disagrees with ECMWF by more than 3 m/s or 30°, so a plan never rests on one model's word alone.
- **Numerical forecast, not an astronomical one.** A tide or current prediction can run years ahead; wind cannot. Open-Meteo refuses a date outside roughly today ± its own model window (about 16 days ahead, about 3 months back), and a date further out than that has no meaningful answer from any model, not just this one.
- **The grid point is not your point.** Both models are served off a grid, and the response reports the nearest grid point actually used, not the coordinate you asked for. The tool prints the distance between them on every call; a few km is normal for ECMWF's 9 km grid, more for GFS's coarser one. Read that distance before trusting a number for a site tucked close to a coastline or a sharp local terrain feature, since the grid point can sit over different terrain than the actual entry.
- **Timezone is mandatory, not defaulted.** `--tz` takes an IANA zone name, never a fixed offset; the API localizes every timestamp itself once told the zone, so there is no UTC value to mis-read as local and no daylight saving boundary to get wrong by an hour.
- **The wind call is per-site.** This tool gives you the number; which direction ruins a given entry, and what the fetch is, is site-specific and belongs in the site's own file, not here.

## `tools/open_meteo_wind.py`

```sh
# Hourly wind for one local calendar day, both models side by side
python3 tools/open_meteo_wind.py forecast --near <lat> <lon> --date 2026-07-12 --tz <IANA_ZONE>

# Wind at one local moment (entry or exit time), interpolated between the bracketing hours
python3 tools/open_meteo_wind.py at --near <lat> <lon> --time "2026-07-12 09:30" --tz <IANA_ZONE>
```

Sample output, `at`:

```
  requested   <lat>, <lon>
  grid point  <lat>, <lon>  (N.N km away, elevation NN m)
  models      ecmwf_ifs (primary), gfs_seamless (cross-check)

  ecmwf_ifs        (primary)        6.7 m/s  ESE (116°)  gust 13.2 m/s
  gfs_seamless     (cross-check)    8.5 m/s  ESE (107°)  gust 10.4 m/s
```

Direction is degrees true, the direction the wind comes FROM, same convention as a current axis elsewhere in this workspace. `--models` overrides the default pair with any comma-separated Open-Meteo model ids (`ecmwf_ifs025` is the coarser but guaranteed-available 0.25° ECMWF tier, `icon_seamless` is DWD's ICON, `best_match` lets Open-Meteo pick); the first id given is always treated as primary. Defaults live in `tool-config.json` as `open_meteo_wind.primary_model` and `open_meteo_wind.cross_check_model`.

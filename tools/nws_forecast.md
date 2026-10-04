# NWS point forecast (wind and surface conditions)

<https://api.weather.gov>

The wind source for US sites. National Weather Service, no key, no rate limit worth worrying about. Wind is a factor that decides whether the entry is diveable at all, and it is per-site: what matters is the wind on that beach, not the regional marine forecast.

- **Use it for.** Wind speed, direction and gusts at the entry, hourly, on the day. Plus wave height, air temperature and rain, which set what the surface interval feels like.
- **Point forecast, not the zone/marine forecast.** The marine forecast covers open water and will happily tell you it's blowing 15 kn offshore while the beach in the lee is glass.
- **US coordinates only.** A point outside NWS coverage is refused, often as an unhelpful HTTP 500; use Open-Meteo there.
- **About a week out.** The forecast runs roughly seven days ahead; a date past that has no answer.
- **The grid cell is not your point.** NWS forecasts on a 2.5 km grid. A cell straddling the shoreline can read land-side conditions, and wave height is populated only where the cell carries a marine forecast.
- **The wind call is per-site.** It lives in the site file: which direction ruins that particular entry, and what the fetch is. NWS gives you the number; the site file says whether that number matters. A 20 mph southerly is nothing at a north-facing beach and a dive-killer at a south-facing one.
- **Wind against current is worse than either alone.** Cross-check the wind direction against the site's ebb/flood axis before calling an entry flat.
- **User-Agent required.** NWS rejects requests without one. `nws_forecast.user_agent_email` in `tool-config.json` sets the contact address; the tool stops if it is missing.

## `tools/nws_forecast.py`

Standard library only.

```sh
python3 tools/nws_forecast.py forecast --near <lat> <lon> --date 2026-07-12          # hourly conditions for one local day
python3 tools/nws_forecast.py at --near <lat> <lon> --time "2026-07-12 09:30"        # conditions at the entry or exit time
```

Both print the gridpoint, the site's time zone and the forecast's last update, then wind speed, direction, gust, wave height, air temperature, chance of rain and sky. Times are local to the site, in the zone NWS assigns the gridpoint. Speeds are m/s; direction is degrees true, the direction the wind comes from. NWS holds each value constant over a span of one or more hours, so `at` reports the span containing the moment asked for.

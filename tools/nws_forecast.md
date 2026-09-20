# NWS point forecast (wind and surface conditions)

<https://api.weather.gov>. National Weather Service, no key, no rate limit worth worrying about.

The wind source. Wind is a factor that decides whether the entry is diveable at all, and it is per-site: what matters is the wind on that beach, not the regional marine forecast.

- **Use it for.** Wind speed and direction at the entry, hourly, on the day. Plus sea state, air temperature and rain, which set what the surface interval feels like.
- **How.** Resolve the beach's coordinates to a gridpoint, then follow `forecastHourly`:

  ```sh
  curl -s -H "User-Agent: dive-planning (<contact-email>)" \
    "https://api.weather.gov/points/<lat>,<lon>" | jq -r .properties.forecastHourly
  # then GET that URL: hourly periods with windSpeed, windDirection, temperature, shortForecast
  ```

  A `User-Agent` is required, NWS rejects requests without one. Use the contact email from `nws.user_agent_email` in `tool-config.json` for `<contact-email>` (the gmail address, deliberately not the DAN account email).
- **Point forecast, not the zone/marine forecast.** The marine forecast covers open water and will happily tell you it's blowing 15 kn offshore while the beach in the lee is glass.
- **The wind call is per-site.** It lives in the site file: which direction ruins that particular entry, and what the fetch is. NWS gives you the number; the site file says whether that number matters. A 20 mph southerly is nothing at a north-facing beach and a dive-killer at a south-facing one.
- **Wind against current is worse than either alone.** Cross-check the wind direction against the site's ebb/flood axis before calling an entry flat.

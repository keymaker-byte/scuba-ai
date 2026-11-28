# NWS point forecast (wind call and surface conditions)

<https://api.weather.gov>

The wind source for US sites, and the go / no go call on it. National Weather Service, no key, no rate limit worth worrying about. Wind decides whether the entry is diveable at all, and it is per-site: the wind on that beach, read against that beach's own exposure.

- **Use it for.** The plan's wind verdict at the entry and the exit time: the tool reads the forecast and calls it go, marginal or no go against the site's own sectors. Plus wave height, air temperature and rain, which set what the surface interval feels like.
- **The site's sectors.** `--file` with the site JSON reads them from its `wind` section, written by `shore_exposure.md`: the Bad sectors as `--bad`, the Short fetch and Mixed sectors as `--short`, the forecast point as the entry point (the dive area at a boat site), and the zone as the site's `tz`. By hand, `--bad` and `--short` take each sector as compass shorthand, written `SW-WNW` or `N`, several comma separated or repeated, the same shorthand the site file's Wind bullets carry in parentheses. Every direction left out of both options counts as fine. The worked examples below show the mapping.
- **The call.** Each reading gets go, marginal or no go, with the sector kind it fell in:
  - **Bad.** Go under `go_below_ms` (5 m/s), marginal from there to `nogo_above_ms` (8 m/s), no go above it.
  - **Short.** The same bands, each moved up by `short_fetch_shift_ms` (3 m/s).
  - **Fine.** Go up to `offshore_marginal_ms` (8 m/s) and marginal above it, on the sustained speed alone, for the surface drift an offshore wind puts on a diver; the entry itself stays flat.
  - **Gusts.** On a bad or short reading, a gust more than `gust_margin_ms` (3 m/s) above the sustained speed moves the call up one band, for the chop gusts build on the entry.
- **The limits.** In `nws_forecast`'s section of `tool-config.json`, each falling back to the default shown, and anchored to the Beaufort scale's sea state: Beaufort 3 (3.4 to 5.4 m/s) is wavelets and scattered whitecaps, Beaufort 4 (5.5 to 7.9 m/s) small waves and frequent whitecaps, Beaufort 5 (8.0 to 10.7 m/s) moderate waves and many whitecaps.
- **Point forecast.** The tool reads the forecast for the beach's own 2.5 km grid cell. The zone and marine forecasts cover open water and can read a strong offshore blow while the beach in its lee is glass.
- **The grid cell is not your point.** A cell straddling the shoreline can read land-side conditions, and wave height is populated only where the cell carries a marine forecast.
- **US coordinates only, about a week out.** A point outside NWS coverage is refused, often as an unhelpful HTTP 500; use Open-Meteo there. The forecast runs roughly seven days ahead; a date past that has no answer.
- **User-Agent required.** NWS rejects requests without one. `nws_forecast.user_agent_email` in `tool-config.json` sets the contact address; the tool stops if it is missing.

## `tools/nws_forecast.py`

Standard library only.

```sh
python3 tools/nws_forecast.py at --file <path/to/slug.json> --time "2026-07-12 09:30"        # planning: the call at the entry or exit time
python3 tools/nws_forecast.py forecast --file <path/to/slug.json> --date 2026-07-12          # planning: the call for every hour of the day
python3 tools/nws_forecast.py at --near <lat> <lon> --time "2026-07-12 09:30" --tz <IANA_ZONE> --bad WSW-W --short SW,WNW-NW,S    # by hand: the call at a moment
python3 tools/nws_forecast.py forecast --near <lat> <lon> --date 2026-07-12 --tz <IANA_ZONE> --bad WSW-W --short SW,WNW-NW,S      # by hand: the call for every hour
python3 tools/nws_forecast.py forecast --near <lat> <lon> --date 2026-07-12 --tz <IANA_ZONE>                              # conditions alone, no call
```

Give it the site JSON with `--file`, or the entry point's coordinate with `--near` and the zone with `--tz`. With `--file` it first prints the point and the sectors it read; a site JSON with no `wind` section, or one taken at another coordinate, stops the run with the extract to run, and `--near`, `--bad` or `--short` beside it stops the run too. Both commands print the gridpoint, the site's time zone and the forecast's last update, then wind speed, direction, gust, wave height, air temperature, chance of rain and sky, with the call added whenever `--bad` or `--short` is given. The zone is the site's own IANA zone, the `tz` in its JSON, which `--file` reads and a `--tz` beside it must match, and every time is read and printed in it. Speeds are m/s; direction is degrees true, the direction the wind comes from. NWS holds each value constant over a span of one or more hours, so `at` reports the span containing the moment asked for. A malformed sector stops the run before any request.

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

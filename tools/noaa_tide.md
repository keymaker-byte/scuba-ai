# NOAA CO-OPS water levels (tide height, and therefore depth)

<https://api.tidesandcurrents.noaa.gov/mdapi/prod/>

The predicted tide across the entry window: how deep the site is that day. This is what turns a depth reading into a number that means something on any other day, and the tool behind the workspace's depth convention: metres below MLLW. Computed on this machine from the harmonic constants and datums NOAA publishes for each tide station, the same constants NOAA's own predictions come from. A station is downloaded once, the first time it is asked for, and every prediction after that runs with no request at all, for any date.

- **Stations it serves.** Every tide prediction station NOAA lists, about 3,500 of them on every US coast and a scattering abroad: the reference stations with their own constants, and the subordinate stations with their corrections. `stations --near` lists what NOAA carries, with each station's kind.
- **Use it for.** The tide height across the entry window, and the day's high and low water, at a station in the same body of water as the site.
- **A site's median daily tidal range, its largest daily range, and its high/low span across the year.** `range` works through a full year of highs and lows in about a second and reports the median and max daily range and the year's span. The largest and the smallest daily ranges both cluster near the solstices, tracking diurnal inequality, which peaks near the solstices and is smallest near the equinoxes; the exact dates shift from year to year with the moon's cycle.
- **Pick a station in the same body of water.** Water level varies smoothly, so the nearest station is usually right, but "near" has to mean hydraulically near, not near on a map. Verify the station's name and position before trusting the label; a mislabelled tide station once cost about 1 m at high water.
- **Datum.** MLLW. It is what the charts and the predictions use. Never mix datums.
- **The data.** `tools/db/noaa_tide/` holds NOAA's station list and one small file per station: a reference station's constants and its MSL, MLLW and NAVD 88 datums (NAVD 88 where NOAA ties the station to it), or a subordinate station's corrections. Each is downloaded when missing. Deleting the folder, or one station's file, fetches NOAA's current values on the next run, which is how a re-analysed station is picked up. Every header prints the date its constants were fetched.
- **How it predicts.** The height at a reference station is its mean sea level above MLLW plus the sum of its constituents, 37 at most stations and up to 120 where NOAA publishes the shallow-water compounds, each with the node factor and phase of its year. The prediction is `tools/lib/tides.py`, shared with the map's depth layer, and the astronomy `tools/lib/tidal_astronomy.py`, a shared library: Schureman's Manual of Harmonic Analysis and Prediction of Tides with NOAA's own conventions, the node factors held at mid-year and changed at the first hour of the UTC year.
- **How close it is to NOAA.** `verify --all` compared every station with NOAA's live API over 30 days each, in November 2026. On all 1,255 reference stations that carry constants and datums, the height every six minutes agrees within 0.002 m and every high and low within 3 minutes and 0.02 m. On all 2,241 subordinate stations with a usable reference, every high and low agrees within 2 minutes and 0.02 m.
- **Subordinate stations.** Many stations in enclosed or nearshore waters are subordinate: NOAA defines each by its highs and lows alone, the reference station's moved by two time corrections and two height corrections (a ratio or a fixed offset). The tool applies those, and the reference station is downloaded with it. Between a high and a low NOAA publishes nothing; the tool follows the reference station's own curve between the same two extremes, stretched in time and height to fit, so `at`, `normalize` and `project` work at any station. That in-between height is an estimate, closest where the corrections are small.
- **Stations with nothing to predict from.** NOAA lists six stations the tool stops on, with a message: four reference stations with no constants (8660754, 8762483, 9450623, 9751388), one with no MSL or MLLW datum (Eugene Island, 8764311), and one subordinate station that names itself as its reference (Malakal Harbor, 1841275).
- **The turn of the year.** The change of node factors at 00:00 UTC on January 1 puts a small step in the curve, a few centimetres at most, in NOAA's predictions and here alike. A high or low within the hour either side of it can sit minutes and a few centimetres from NOAA's listing. January 1 UTC begins on the afternoon or evening of December 31 local time.
- **Times.** `--tz` is required on every command that prints a time: the site's own IANA zone, the `tz` in its JSON. Every time prints in that zone, named in the header, daylight time included.
- **A failed download stops the run.** A refusal, an empty or non-JSON answer, or an unreachable API ends the run with what failed and the URL asked for, and leaves no partial station file behind. A cached station needs no network.

## Before relying on it

- **It is NOAA's prediction, reproduced.** It is the astronomical tide at the station; wind, pressure and river flow move the real water level around it.
- **Constants go stale silently.** NOAA replaces a station's constants and datums from time to time, and a cached file keeps the old ones. The header prints the fetch date. Run `verify` on a site's tide station whenever its file is older than a year; on a failure, delete the station's file (and its reference station's, for a subordinate), run `verify` again, and report it if it still fails.
- **A `verify` failure is a stop.** It is the same kind of failure as an unreachable API: report it and wait, with no second station substituted.
- **Highs and lows are proven everywhere; a subordinate station's in-between height has nothing to be verified against.** A depth normalized at a subordinate station mid-tide carries that estimate; a reference station in the same water gives a proven height at any moment.
- **It needs `tools/lib/tidal_astronomy.py` beside it.** A change to its `longitudes`, `nodal` or constituent table is a change to every tool that shares it, to be followed by `verify` on a few stations of each.

## `tools/noaa_tide.py`

Standard library only.

```sh
python3 tools/noaa_tide.py stations --near <lat> <lon>                                                   # find a station, then verify its name
python3 tools/noaa_tide.py predict STATION_ID --date 2026-07-12 --tz <IANA_ZONE>                         # high/low water and the day's range
python3 tools/noaa_tide.py at STATION_ID --time "2026-07-12 09:18" --tz <IANA_ZONE>                      # tide height at a moment
python3 tools/noaa_tide.py range STATION_ID --year 2026 --tz <IANA_ZONE>                                 # site file: the "Typical range" row
python3 tools/noaa_tide.py project STATION_ID --datum-depth 15.4 --date 2026-07-12 --tz <IANA_ZONE>      # planning: datum depth to depth below surface, all day
python3 tools/noaa_tide.py normalize STATION_ID --time "2026-07-12 09:21" --depth 14.5 --tz <IANA_ZONE>  # logging: observed depth to depth below MLLW
python3 tools/noaa_tide.py fetch --near <lat> <lon> --km 50                                              # cache every station within a radius
python3 tools/noaa_tide.py fetch STATION_ID [STATION_ID ...]                                             # cache named stations
python3 tools/noaa_tide.py fetch --all                                                                   # cache every station NOAA lists
python3 tools/noaa_tide.py verify STATION_ID --days 30                                                   # compare one station with NOAA's live API
python3 tools/noaa_tide.py verify --all                                                                  # compare every cached station
```

`project` and `normalize` are inverses. Depth below MLLW is the observed depth minus the tide height; depth below the surface is the datum depth plus the tide height. Tide heights are signed, so a dive on a minus tide reads shallower than the datum depth.

`fetch` caches stations ahead of time, for working with no connection. It skips what is already cached, so a stopped run picks up where it left off. `--all` caches all 3,502 stations in about an hour and 14 MB; `--near` covers a region in a minute or two.

`verify` is the proof and the staleness check. It reads NOAA's predictions for the same station and dates and reports the worst difference in the six-minute height, at a reference station, and in the time and height of every high and low, passing within 0.02 m and 3 minutes. A high or low on a flat top, where minutes of time cost a hair of height, is judged on the height, and one at the turn of the UTC year is left out and counted. A failure on a station that used to pass means NOAA replaced its constants: delete the station's file and run it again.

`verify --all` runs the same comparison on every cached station and writes one JSON line per station to `tools/db/noaa_tide/_verify.jsonl`: the differences and `ok`. It makes about 4,800 requests and takes about three hours. A station already in the file is skipped, so a stopped run resumes; deleting the file starts it over. Run it after deleting the cache to refresh every station.

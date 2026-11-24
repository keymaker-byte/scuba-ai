# Tide (tide height at a station, and therefore depth)

<https://api.tidesandcurrents.noaa.gov/mdapi/prod/>

The predicted tide across the entry window: how deep the site is that day. This is what turns a depth reading into a number that means something on any other day, and the tool behind the workspace's depth convention: metres below the datum of the station's source, MLLW at a NOAA station. The tool reads every tide source it knows through one set of commands, and names the source and its datum in every answer, so a site file and a plan read one tool wherever the site is. Every source keeps its data on this machine: a station is downloaded once, the first time it is asked for, and every prediction after that runs with no request at all, for any date.

- **Use it for.** The tide height across the entry window, and the day's high and low water, at a station in the same body of water as the site.
- **A site's median daily tidal range, its largest daily range, and its high/low span across the year.** `range` works through a full year of highs and lows in about a second and reports the median and max daily range and the year's span. The largest and the smallest daily ranges both cluster near the solstices, tracking diurnal inequality, which peaks near the solstices and is smallest near the equinoxes; the exact dates shift from year to year with the moon's cycle.
- **Pick a station in the same body of water.** Water level varies smoothly, so the nearest station is usually right, but "near" has to mean hydraulically near, not near on a map. Verify the station's name and position before trusting the label; a mislabelled tide station once cost about 1 m at high water.
- **Naming a station.** A station is named by its source's own ID, `9447130`. Where two sources share an ID the tool stops and asks for it as `<source>:<id>`, `noaa:9447130`, which every command also accepts. `stations --near` lists every source's stations around a point, nearest first, each with its source and datum.
- **Datum.** Each source's heights are above its own datum, named in every header: MLLW at a NOAA station. Two datums are different surfaces, so a depth normalized against one is never compared with a depth normalized against another. Never mix datums.
- **Times.** `--tz` is required on every command that prints a time: the site's own IANA zone, the `tz` in its JSON. Every time prints in that zone, named in the header, daylight time included.
- **Data downloads on first use.** Each source keeps its station list and one small file per station under `tools/db/tide/<source>/`, each downloaded when missing. Deleting a station's file, or the source's folder, fetches the source's current values on the next run, which is how a re-analysed station is picked up. Every header prints the date its data was fetched.
- **A failed download stops the run.** A refusal, an empty or unreadable answer, or an unreachable service ends the run with what failed and the URL asked for, and leaves no partial station file behind. A cached station needs no network.
- **Shared code.** The sources are `tools/lib/tide.py`, the harmonic prediction every source and the map's tide layer sum with is `tools/lib/tide_harmonics.py`, and the astronomy `tools/lib/tidal_astronomy.py`: Schureman's Manual of Harmonic Analysis and Prediction of Tides with NOAA's own conventions, the node factors held at mid-year and changed at the first hour of the UTC year.

## Sources

### NOAA CO-OPS

NOAA's tide prediction stations, computed on this machine from the harmonic constants and datums NOAA publishes for each station, the same constants NOAA's own predictions come from. Heights above MLLW.

- **Stations it serves.** Every tide prediction station NOAA lists, about 3,500 of them on every US coast and a scattering abroad: the reference stations with their own constants, and the subordinate stations with their corrections.
- **The data.** `tools/db/tide/noaa/` holds NOAA's station list and one file per station: a reference station's constants and its MSL, MLLW and NAVD 88 datums (NAVD 88 where NOAA ties the station to it), or a subordinate station's corrections. The source is `tools/lib/noaa_tides.py`.
- **How it predicts.** The height at a reference station is its mean sea level above MLLW plus the sum of its constituents, 37 at most stations and up to 120 where NOAA publishes the shallow-water compounds, each with the node factor and phase of its year.
- **How close it is to NOAA.** `verify --all` compared every station with NOAA's live API over 30 days each, in November 2026. On all 1,255 reference stations that carry constants and datums, the height every six minutes agrees within 0.002 m and every high and low within 3 minutes and 0.02 m. On all 2,241 subordinate stations with a usable reference, every high and low agrees within 2 minutes and 0.02 m.
- **Subordinate stations.** Many stations in enclosed or nearshore waters are subordinate: NOAA defines each by its highs and lows alone, the reference station's moved by two time corrections and two height corrections (a ratio or a fixed offset). The tool applies those, and the reference station is downloaded with it. Between a high and a low NOAA publishes nothing; the tool follows the reference station's own curve between the same two extremes, stretched in time and height to fit, so `at`, `normalize` and `project` work at any station. That in-between height is an estimate, closest where the corrections are small.
- **Stations with nothing to predict from.** NOAA lists six stations the tool stops on, with a message: four reference stations with no constants (8660754, 8762483, 9450623, 9751388), one with no MSL or MLLW datum (Eugene Island, 8764311), and one subordinate station that names itself as its reference (Malakal Harbor, 1841275).
- **The turn of the year.** The change of node factors at 00:00 UTC on January 1 puts a small step in the curve, a few centimetres at most, in NOAA's predictions and here alike. A high or low within the hour either side of it can sit minutes and a few centimetres from NOAA's listing. January 1 UTC begins on the afternoon or evening of December 31 local time.
- **`verify`.** Reads NOAA's predictions for the same station and dates and reports the worst difference in the six-minute height, at a reference station, and in the time and height of every high and low, passing within 0.02 m and 3 minutes. A high or low on a flat top, where minutes of time cost a hair of height, is judged on the height, and one at the turn of the UTC year is left out and counted. `verify --all` over every NOAA station makes about 4,800 requests and takes about three hours.

## Before relying on it

- **It is the source's prediction, reproduced.** It is the astronomical tide at the station; wind, pressure and river flow move the real water level around it.
- **Data goes stale silently.** A source replaces a station's constants and datums from time to time, and a cached file keeps the old ones. The header prints the fetch date. Run `verify` on a site's tide station whenever its file is older than a year; on a failure, delete the station's file (and its reference station's, for a subordinate), run `verify` again, and report it if it still fails.
- **A `verify` failure is a stop.** It is the same kind of failure as an unreachable service: report it and wait, with no second station substituted.
- **Highs and lows are proven everywhere; a subordinate station's in-between height has nothing to be verified against.** A depth normalized at a subordinate station mid-tide carries that estimate; a reference station in the same water gives a proven height at any moment.
- **The shared libraries are shared.** A change to `tools/lib/tide_harmonics.py`, or to `tools/lib/tidal_astronomy.py`'s `longitudes`, `nodal` or constituent table, is a change to every source, the current tool and the map, to be followed by `verify` on a few stations of each source.

## Adding a source

A source is a class in `tools/lib/tide.py`'s `SOURCES`, with its key, name, datum and cache folder under `tools/db/tide/`, its station list, whether an ID is one of its stations, a station downloaded when missing, the height at a moment and the highs and lows between two moments, its harmonic constants where a station has its own, and a check against its live service; the interface is written out at the top of that file. A source whose stations carry harmonic constants predicts with `tools/lib/tide_harmonics.py`, so its constituents are summed as NOAA's are. It also takes a section above. The map's tide layer takes every source's stations that carry harmonic constants and heights above MLLW, the datum its depth layer is on, and leaves the rest out with the reason.

## `tools/tide.py`

Standard library only.

```sh
python3 tools/tide.py stations --near <lat> <lon>                                                   # find a station, then verify its name
python3 tools/tide.py predict STATION_ID --date 2026-07-12 --tz <IANA_ZONE>                         # high/low water and the day's range
python3 tools/tide.py at STATION_ID --time "2026-07-12 09:18" --tz <IANA_ZONE>                      # tide height at a moment
python3 tools/tide.py range STATION_ID --year 2026 --tz <IANA_ZONE>                                 # site file: the "Typical range" row
python3 tools/tide.py project STATION_ID --datum-depth 15.4 --date 2026-07-12 --tz <IANA_ZONE>      # planning: datum depth to depth below surface, all day
python3 tools/tide.py normalize STATION_ID --time "2026-07-12 09:21" --depth 14.5 --tz <IANA_ZONE>  # logging: observed depth to depth below the datum
python3 tools/tide.py fetch --near <lat> <lon> --km 50                                              # cache every station within a radius
python3 tools/tide.py fetch STATION_ID [STATION_ID ...]                                             # cache named stations
python3 tools/tide.py fetch --all [--source noaa]                                                   # cache every station a source lists
python3 tools/tide.py verify STATION_ID --days 30                                                   # compare one station with its source's live predictions
python3 tools/tide.py verify --all [--source noaa]                                                  # compare every cached station
```

`project` and `normalize` are inverses. Depth below the datum is the observed depth minus the tide height; depth below the surface is the datum depth plus the tide height. Tide heights are signed, so a dive on a minus tide reads shallower than the datum depth.

`stations` and `fetch --near` read every source; `--source` narrows either to one. `fetch` caches stations ahead of time, for working with no connection, with each subordinate station's reference. It skips what is already cached, so a stopped run picks up where it left off. `fetch --all --source noaa` caches all 3,502 NOAA stations in about an hour and 14 MB; `--near` covers a region in a minute or two.

`verify --all` runs each source's comparison on every cached station of it and writes one JSON line per station to the source's `_verify.jsonl`, `tools/db/tide/noaa/_verify.jsonl` for NOAA: the differences and `ok`. A station already in the file is skipped, so a stopped run resumes; deleting the file starts it over. Run it after deleting a cache to refresh every station.

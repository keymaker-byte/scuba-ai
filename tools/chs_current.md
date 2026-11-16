# CHS currents (Canadian slack and max flood/ebb)

<https://tides.gc.ca/en/web-services-offered-canadian-hydrographic-service>

The Canadian Hydrographic Service's current predictions, the official source for Canadian waters: slack times, flood and ebb maxima and the speed through the day at each CHS current station. CHS publishes finished predictions and keeps its harmonic constants to itself, so this tool keeps a copy of the predictions on this machine: a station's year is downloaded once, the first time a date in it is asked for, and every prediction in that year after that runs with no request at all.

- **Stations it serves.** All 30 CHS current stations, on both coasts, identified by their five-digit CHS code (`07100`, `07090`). A station row in a site file whose ID is a five-digit code is read with this tool. `stations --near` lists them with their codes.
- **Use it for.** The same two jobs as any current station tool. Writing a site file's Current section in Canadian water, or where a site's reference is a Canadian station: the station's slacks, axes and peak speeds. Planning a dive: the slack time and direction on the day, and the windows under the threshold.
- **One series per station.** A CHS station publishes a single prediction series, with no depth bins to choose from; the Recommended bin row reads "Single series" for a CHS station.
- **The years CHS holds.** Predictions exist only for the dates CHS has published: at most stations the speed series from the end of 2022 and the slack and maximum events from the start of 2025, both to the first days of January 2028. CHS adds a year at a time. A date outside a station's holdings stops the run with the spans CHS does hold; `predict` needs the events and `window` the speed series.
- **The data.** `tools/db/chs_current/` holds CHS's station list, one file per station (name, position, flood and ebb directions, time zone, and what CHS holds), and one file per station and UTC year with that year's speed series and events. Each is downloaded when missing. Every header prints the date its predictions were downloaded.
- **The first use of a station and year takes about two minutes.** CHS answers a speed series seven days at a time and allows 30 requests a minute from one address, and the tool keeps to that pace. A day that spans two UTC years, December 31 local time, needs both.
- **A date past what is cached.** The tool asks CHS what it now holds for the station and downloads what was added, so a new year appears on the first run that asks for it. That question needs the network; with no connection the run stops and says so.
- **Times.** `--tz` is required on every command that prints a time: the site's own IANA zone, the `tz` in its JSON. Every time prints in that zone, named in the header, daylight time included.
- **Every time it prints is at the station, un-offset.** The site file's Observed offset is applied to it, where established.
- **Weak and variable.** CHS marks some events weak and variable, a turn with no clear slack or maximum, and `predict` prints them under that name.
- **Units.** CHS publishes speed in knots; the tool converts to m/s. Flood is positive, ebb negative, against the station's own flood and ebb directions, which the header prints.
- **A failed download stops the run.** A refusal, an empty or non-JSON answer, or an unreachable API ends the run with what failed and the URL asked for, and leaves no partial file behind. A cached station and year needs no network.

## Before relying on it

- **It is CHS's prediction, copied.** It gives the current at the station's own point, un-offset; the site's own water is the site file's business. CHS's printed Tide and Current Tables can differ slightly from its API, and the tables are the official ones.
- **A copy goes stale silently.** CHS can replace a station's predictions, and a cached year keeps the old ones. The header prints the download date. Run `verify` on a site's station whenever its file is older than a year or a plan matters more than usual; on a failure, delete the station's files, run `verify` again, and report it if it still fails.
- **A `verify` failure is a stop.** It is the same kind of failure as an unreachable API: report it and wait, with no second station substituted.
- **Sample spacing.** Most stations carry a speed value every 15 minutes and six carry one every minute (07721, 07724, 07745, 08108, 09341, 09348). `window` interpolates the crossing times between samples, so a window edge at a 15-minute station is good to a few minutes.

## `tools/chs_current.py`

Standard library only.

```sh
python3 tools/chs_current.py stations --near <lat> <lon>                       # site file: CHS current stations near the site
python3 tools/chs_current.py predict 07100 --date 2026-07-12 --tz <IANA_ZONE>  # site file and planning: slack, max flood, max ebb
python3 tools/chs_current.py window 07100 --date 2026-07-12 --tz <IANA_ZONE>   # site file and planning: diveable windows
python3 tools/chs_current.py fetch 07100 07090 [--year 2027]                   # cache named stations
python3 tools/chs_current.py fetch --near <lat> <lon> --km 50                  # cache every station within a radius
python3 tools/chs_current.py fetch --all                                       # cache every station and every year CHS holds
python3 tools/chs_current.py verify 07100 --date 2026-07-12 --days 7           # compare the cache with CHS's live API
python3 tools/chs_current.py verify --all                                      # the same for every cached station
```

`predict` reads the station's slack and maximum events. `window` reads its speed series and reports every span under `--max-speed`, interpolating the crossing times between samples. The threshold defaults to `chs_current.max_speed_ms` in `tool-config.json` (0.25 m/s), the same placeholder the other current tools use.

`fetch` caches ahead of time, for working with no connection. It takes every year CHS holds for each station, or the years named with `--year`, and skips what is already cached, so a stopped run picks up where it left off. `--all` caches all 30 stations, about 200 station years, in about four hours and 200 MB; one station is about ten minutes.

`verify` is the staleness check. It reads CHS's predictions for the same station and dates and compares every speed value and every event with the cache, passing only when all of them are identical. A failure means CHS replaced the predictions since they were cached: delete the station's files and run it again. `verify --all` takes about three minutes.

A station code that CHS does not list stops the run with a message. The station list is downloaded once; deleting `tools/db/chs_current/stations.json` fetches it again.

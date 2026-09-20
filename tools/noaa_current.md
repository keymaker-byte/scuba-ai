# NOAA CO-OPS currents (slack and max flood/ebb)

<https://tidesandcurrents.noaa.gov/noaacurrents/stations.html?g=698>

The slack time and direction, on the day, for the reference station that governs the site. This is the number the whole plan hangs off. API, no key, machine-readable predictions for arbitrary future dates. Hundreds of live current-prediction stations sit along the coast, searchable by position; that is how a site gets re-based off a dead book-era station onto a live one.

- **Use it for.** The slack time and direction on the day, at the station governing the site, plus the max flood/ebb speeds bracketing the window.
- **Read the whole day, not just the one slack.** Slacks are not evenly spaced and not equal: a slack between two weak maxes is a wide window, between two strong maxes a narrow one. Note the max flood/ebb speeds either side of your window; they bracket how fast the site turns on you if you're late.
- **Mind the bin.** The default is near-surface. The stations are ADCPs with many depth bins, NOAA publishes predictions for only a few, and the default is a shallow one, not the water we dive. Pick the published bin nearest the site's working depth, and record which bin the offset was derived against; an offset against one bin is not the same number as against another. At a fast-moving pass the default bin might sit at 4.6 m and the deepest published bin at 30.6 m; on a test day the deep slack ran 20 minutes earlier than the surface slack, with max flood weaker (1.41 vs 1.61 m/s) and the flood axis rotated 286°→275°. Still pull the other bins: a wide spread between them is itself a warning that the offset is depth-sensitive.
- **Watch for.** Diurnal inequality (the two daily exchanges are not the same size), and big exchanges around new and full moon.
- **Every time it prints is at the station, un-offset.** The site correction (from a book, from repeated observation, tracked in `plan_log.csv`) is still ours to apply.

## `tools/noaa_current.py`

```sh
# Re-base a site: which live stations are near it?
python3 tools/noaa_current.py stations --near <lat> <lon>

# Which bins publish, and at what depth?
python3 tools/noaa_current.py bins STATION_ID

# Slack / max flood / max ebb, at the dive-depth bin
python3 tools/noaa_current.py predict STATION_ID --bin 1 --date 2026-07-12

# The number that actually matters: how long the window stays diveable
python3 tools/noaa_current.py window STATION_ID --bin 1 --date 2026-07-12 --max-speed 0.25
```

`window` is the planning command. Rather than a single slack instant it reports every span where the current stays under a threshold (default 0.25 m/s), with its duration and peak, so a 72-minute window and a 20-minute one stop looking alike. Sample output, bin 1, 12 Jul:

```
  01:06 - 02:12    72 min   peak 0.23 m/s
  06:54 - 07:36    48 min   peak 0.21 m/s
  17:30 - 18:18    54 min   peak 0.24 m/s
  21:54 - 23:36   108 min   peak 0.24 m/s
```

The threshold is a placeholder, not a considered limit: 0.25 m/s is roughly 0.5 kn, a guess at what's comfortable in a drysuit, worth setting from experience. The default lives in `tool-config.json` as `max_speed_ms`.

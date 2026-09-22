# NOAA CO-OPS water levels (tide height, and therefore depth)

<https://tidesandcurrents.noaa.gov/noaacurrents/stations.html?g=698>

The predicted tide across the entry window: how deep the site is that day. This is what turns a depth reading into a number that means something on any other day, and the tool behind the workspace's depth convention: metres below MLLW.

- **Use it for.** The tide height across the entry window, and the day's high and low water, at a station in the same body of water as the site.
- **A site's median daily tidal range, its largest daily range, and its high/low span across the year.** `range` pulls a full year of highs and lows in one API call (NOAA's `predictions` product accepts a year-long `begin_date`/`end_date` span when `interval=hilo`) and reports the median and max daily range and the year's span. The largest and the smallest daily ranges both cluster near the solstices, tracking diurnal inequality, which peaks near the solstices and is smallest near the equinoxes; the exact dates shift from year to year with the moon's cycle.
- **Pick a station in the same body of water.** Water level varies smoothly, so the nearest station is usually right, but "near" has to mean hydraulically near, not near on a map. Verify the station's name and position before trusting the label; a mislabelled tide station once cost about 1 m at high water.
- **Many stations in enclosed or nearshore waters are subordinate.** They publish high/low water only, no 6-minute series.
- **Datum.** MLLW. It is what the charts and the predictions use. Never mix datums.
- **Times.** `lst_ldt`, local, like everything else here.

## `tools/noaa_tide.py`

```sh
# Which tide stations are near the site? (VERIFY the name; IDs are not self-describing)
python3 tools/noaa_tide.py stations --near <lat> <lon>

# High/low water for the day, and the day's range
python3 tools/noaa_tide.py predict STATION_ID --date 2026-07-12

# Tide height at a moment
python3 tools/noaa_tide.py at STATION_ID --time "2026-07-12 09:18"

# SITE FILE "Typical range" row: exact median/max/min daily range and year span, one call
python3 tools/noaa_tide.py range STATION_ID --year 2026

# LOGGING: observed depth -> depth below MLLW datum. The number that carries between dives.
python3 tools/noaa_tide.py normalize STATION_ID --time "2026-07-12 09:21" --depth 14.5

# PLANNING: a known datum depth -> how deep it actually reads, through the day
python3 tools/noaa_tide.py project STATION_ID --datum-depth 15.4 --date 2026-07-12
```

`normalize` is the logging command, `project` is the planning command, and they are inverses:

```
$ noaa_tide.py normalize STATION_ID --time "2026-07-12 09:21" --depth 14.5
  observed depth        14.5 m
  tide height          -0.94 m
  depth below MLLW      15.4 m   <-- log this

$ noaa_tide.py project STATION_ID --datum-depth 15.4 --date 2026-07-12
  09:37  LOW   tide -0.95 m   ->  reads  14.4 m below surface
  17:44  HIGH  tide +3.36 m   ->  reads  18.8 m below surface
```

On subordinate stations it interpolates harmonically between the high/low extremes (the smooth form of the rule of twelfths), good to a few centimetres, far inside the precision a dive computer's depth deserves, so `at` and `normalize` work anywhere.

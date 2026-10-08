# NOAA CO-OPS currents (slack and max flood/ebb)

<https://tidesandcurrents.noaa.gov/noaacurrents/stations.html?g=698>

The slack time and direction, on the day, for the reference station that governs the site. This is the number the whole plan hangs off. API, no key, machine-readable predictions for arbitrary future dates. Hundreds of live current-prediction stations sit along the coast, searchable by position; that is how a site gets re-based off a dead book-era station onto a live one.

- **Stations it serves.** Every station NOAA's API publishes predictions for today, on every US coast. A station row in a site file whose ID is a NOAA ID is read with this tool; `stations --near` lists what is live, with each station's type. The ID prefix names a survey project or a set of tables (PUG Puget Sound, SFB San Francisco Bay, LIS Long Island Sound, PCT and ACT the Pacific and Atlantic current tables), not the kind of station; the type does. A retired station, one this tool answers with "predictions are not available", is read with `noaa_legacy_current`.
- **Use it for.** Two jobs. Writing a site file's Current section, by the region's current method: finding the governing station, its published bins, and the axes, peak speeds and typical window at the recommended bin. Planning a dive: the slack time and direction on the day at that station, plus the max flood/ebb speeds bracketing the window.
- **Read the whole day, not just the one slack.** Slacks are not evenly spaced and not equal: a slack between two weak maxes is a wide window, between two strong maxes a narrow one. Note the max flood/ebb speeds either side of your window; they bracket how fast the site turns on you if you're late.
- **Mind the bin.** The default is near-surface. The stations are ADCPs with many depth bins, NOAA publishes predictions for only a few, and the default is a shallow one, not the water we dive. The site file's Recommended bin, the published bin nearest the dive area's seabed depth, is the one every figure and every plan uses, and the offset is derived against it; an offset against one bin is not the same number as against another. At a fast-moving pass the default bin might sit at 4.6 m and the deepest published bin at 30.6 m; on a test day the deep slack ran 20 minutes earlier than the surface slack, with max flood weaker (1.41 vs 1.61 m/s) and the flood axis rotated 286°→275°. Still pull the other bins: a wide spread between them is itself a warning that the offset is depth-sensitive.
- **Watch for.** Diurnal inequality (the two daily exchanges are not the same size), and big exchanges around new and full moon.
- **Station types.** H, harmonic: the station's own constants, usually from an instrument survey that publishes depth bins. S, subordinate: time and speed corrections to a reference station, with no bins of its own; `bins` reports it has nothing to pick a working-depth bin from and exits. W, weak and variable: no predictions at all.
- **Every time it prints is at the station, un-offset.** The site file's Observed offset is applied to it, where established.

## `tools/noaa_current.py`

Standard library only.

```sh
python3 tools/noaa_current.py stations --near <lat> <lon>                      # site file: live stations near the site
python3 tools/noaa_current.py bins STATION_ID                                  # site file: published bins and their depths
python3 tools/noaa_current.py predict STATION_ID --bin B --date 2026-07-12     # site file and planning: slack, max flood, max ebb
python3 tools/noaa_current.py window STATION_ID --bin B --date 2026-07-12      # site file and planning: diveable windows
```

`window` is the planning command. It reports every span where the current stays under `--max-speed`, with its duration and peak, so a 72-minute window and a 20-minute one stop looking alike. The threshold defaults to `noaa_current.max_speed_ms` in `tool-config.json` (0.25 m/s), a placeholder for what's comfortable in a drysuit, worth setting from experience.

`--bin` defaults to the station's near-surface bin; always pass the site file's Recommended bin. A site file's peak speeds and typical window come from `predict` and `window` run across 30 consecutive days, which takes in both spring tides of the lunar month, the larger perigean one included.

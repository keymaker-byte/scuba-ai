# NOAA legacy currents (retired reference stations)

<https://tidesandcurrents.noaa.gov/historic_tide_tables.html>

Predictions for the NOAA current reference stations retired when NOAA re-surveyed its waters and replaced their constants, computed here from their archived pre-2016 harmonic constants. These are the stations older current tables were built on, and the stations a legacy correction is written against.

- **Stations it serves.** NOAA reference current stations that NOAA's API no longer publishes, identified by their legacy NOAA ID, PCT on the Pacific (`PCT1341`, `PCT1541`) and ACT on the Atlantic. A station row in a site file whose ID `noaa_current` answers with "predictions are not available" is read with this tool. `stations --near` lists what it carries.
- **Use it for.** Reading a site's legacy correction on the day: the legacy reference's slack and maximum times here, plus the correction the site file records. And comparing a legacy reference with the live governing station, when a legacy correction is reconciled against it.
- **Reference stations only.** It carries each reference station's own constants. A legacy subordinate station has no constants of its own; its slack is the reference's slack plus the correction, which the site file records.
- **Archived constants.** The constants are the 2010 edition of NOAA's published harmonics, the edition NOAA's own tables used until the re-survey. `selftest` checks the tool against slack times NOAA printed in its 2013 tables; run it after any change to the data.
- **Every time it prints is at the station, un-offset,** in local clock time (`--tz`, default from `tool-config.json`), daylight saving included. NOAA's printed tables give local standard time.
- **Units.** Speed in m/s, flood positive, ebb negative, against the station's own flood and ebb directions, which the header prints.

## `tools/noaa_legacy_current.py`

Standard library only.

```sh
python3 tools/noaa_legacy_current.py stations --near <lat> <lon>          # legacy reference stations near a site
python3 tools/noaa_legacy_current.py predict PCT1341 --date 2026-07-12    # slack, max flood, max ebb
python3 tools/noaa_legacy_current.py window PCT1341 --date 2026-07-12     # diveable windows
python3 tools/noaa_legacy_current.py selftest                             # check against NOAA's printed 2013 tables
```

The first run downloads two files into `tools/db/` and reads them locally after that: the 2010 harmonics (`harmonics-dwf-20100529-free.tcd`, about 1.7 MB) from Debian's package archive, and the 2018 harmonics listing that maps each legacy station's name to its NOAA ID, kept as `noaa_legacy_current_index.json`. Deleting either fetches it again. `window` reports every span under `--max-speed`, which defaults to `noaa_legacy_current.max_speed_ms` in `tool-config.json` (0.25 m/s).

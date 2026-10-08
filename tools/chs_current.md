# CHS currents (Canadian slack and max flood/ebb)

<https://tides.gc.ca/en/web-services-offered-canadian-hydrographic-service>

The Canadian Hydrographic Service's current predictions, the official source for Canadian waters: slack times, flood and ebb maxima and the speed through the day at each CHS current station. Read through the CHS Integrated Water Level System (IWLS) API, free, no key, JSON.

- **Stations it serves.** CHS current stations, identified by their five-digit CHS code (`07100`, `07090`). A station row in a site file whose ID is a five-digit code is read with this tool. `stations --near` lists them with their codes.
- **Use it for.** The same two jobs as any current station tool. Writing a site file's Current section in Canadian water, or where a site's reference is a Canadian station: the station's slacks, axes and peak speeds. Planning a dive: the slack time and direction on the day, and the windows under the threshold.
- **One series per station.** A CHS station publishes a single prediction series, with no depth bins to choose from; the Recommended bin row reads "Single series" for a CHS station.
- **Every time it prints is at the station, un-offset,** in the station's own time zone unless `--tz` names the site's. The site file's Observed offset is applied to it, where established.
- **Units.** CHS publishes speed in knots; the tool converts to m/s. Flood is positive, ebb negative, against the station's own flood and ebb directions, which the header prints.

## `tools/chs_current.py`

Standard library only.

```sh
python3 tools/chs_current.py stations --near <lat> <lon>             # site file: CHS current stations near the site
python3 tools/chs_current.py predict 07100 --date 2026-07-12         # site file and planning: slack, max flood, max ebb
python3 tools/chs_current.py window 07100 --date 2026-07-12          # site file and planning: diveable windows
```

`predict` reads the station's published slack and maximum events. `window` reads its 15-minute speed series and reports every span under `--max-speed`, interpolating the crossing times between samples. The threshold defaults to `chs_current.max_speed_ms` in `tool-config.json` (0.25 m/s), the same placeholder the other current tools use.

A station code that CHS does not serve stops the run with a message; the station list itself is CHS's own, read live on every call.

# ENPAC15 (ADCIRC spatial tidal currents)

<https://adcirc.org/products/adcirc-tidal-databases/>

A depth-averaged tidal current field for the whole Eastern North Pacific: the ENPAC15 harmonic constituent database, 37 constituents on an unstructured mesh of ~554k nodes refined into harbours, produced by the University of Oklahoma with NOAA's Coast Survey Development Laboratory using the ADCIRC model. Where a current station gives the current at a scattered point, this is a continuous field: it can predict at sites with no station near them and in the water between stations.

- **Use it for.** Current speed, direction and slack timing at any point inside the mesh, for any date, scaled to a position in the water column (bottom, mid, or surface) through the boundary layer profile. It predicts continuously across the whole domain, so it covers a site with no current station of its own and the water between existing stations equally well.
- **Depth-averaged, not a depth bin.** The mean over the whole column runs slower than the near-surface water and slower than the bin a current station reports. It is also smooth: it under-represents the sharp flood/ebb asymmetry of real rapids, softens the diurnal inequality, and is only approximate at any single point. It holds the semidiurnal slacks and the axis well; treat the unequal exchange and the peak speeds as approximate.
- **Coverage is not uniform.** Channels and passes are resolved; a coordinate walked too close to shore can fall outside the wet mesh. `extract` checks this and refuses a point outside the mesh rather than snapping to its boundary and predicting off a rough approximation; walk the coordinate back onto the covered side (toward the dive area) and re-run it. Trust a NOAA station instead for a site that never lands inside the mesh at all.
- **Behaviour, not the flood/ebb label.** It gives the current axis, the slack times, and the peak speeds; which of the two axis directions is the flood is site-specific and has to be fixed against the tide or a station.
- **Distribution, not an API.** A single ~700 MB download, cached once in `tools/db/` (it re-downloads on the next extraction if missing). Per-site extraction is time-independent: a site is extracted once and predicted forever.
- **Astronomy.** Pinned to the database's own reference nodal factors and equilibrium arguments (2004-11-16).

## `tools/adcirc_current.py`

Standard library only.

```sh
python3 tools/adcirc_current.py extract <path/to/slug.json> --near <lat> <lon> --tz <IANA_ZONE>        # site file: write the extract, once
python3 tools/adcirc_current.py window --date 2026-07-12 [--position P] --file <path/to/slug.json>     # planning: diveable windows
python3 tools/adcirc_current.py predict --date 2026-07-12 [--position P] --file <path/to/slug.json>    #    slacks and peaks
python3 tools/adcirc_current.py at --time "2026-07-12 09:18" [--position P] --file <path/to/slug.json> #    current at a moment
python3 tools/adcirc_current.py selftest                                                               # verify the astronomy
```

`extract` is the only command that reads the database. Give it the coordinate of the dive area (the deeper part actually dived, not the beach entry) and the full path to write, normally beside the site's `<slug>.md` in `regions/<region>/sites/`. `--tz` is the site's own zone, stored in the extract so every later prediction runs in the site's local time. A point outside the wet mesh is refused; walk it back toward the dive area and re-run. Validate a new extract against the current station governing the site before trusting its timing.

`window`, `predict` and `at` read only the extract, as `--file <path>` or as its content inline with `--json`, exactly one of the two. They print the principal current axis and, per exchange, the slack times and peak speeds, un-offset at the extract point and unlabelled for flood vs. ebb. `--position bottom`, `mid` or `surface` scales the depth-averaged speed toward that point in the water column; it moves speeds and window widths, never slack times. The `window` threshold defaults to `adcirc_current.max_speed_ms` in `tool-config.json` (0.25 m/s), a placeholder worth setting from experience.

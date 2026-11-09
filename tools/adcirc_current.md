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
python3 tools/adcirc_current.py extract --near <lat> <lon> > <out.json>                               # site file: print the extract, once
python3 tools/adcirc_current.py window --date 2026-07-12 [--position P] --file <path/to/slug.json>     # planning: diveable windows
python3 tools/adcirc_current.py predict --date 2026-07-12 [--position P] --file <path/to/slug.json>    #    slacks and peaks
python3 tools/adcirc_current.py at --time "2026-07-12 09:18" [--position P] --file <path/to/slug.json> #    current at a moment
python3 tools/adcirc_current.py selftest                                                               # verify the astronomy
python3 tools/adcirc_current.py export-map --bbox S W N E [--bbox ...] --name <name> --label "<area>"                 # map viewer: the current overlay
```

`extract` is the only command that reads the database. Give it the coordinate of the dive area (the deeper part actually dived, not the beach entry). It prints `{"enpac15_constituents": [...]}` on stdout, with its progress and the principal axis on stderr, and writes no file; that object is attached to the site's `<slug>.json`, which already holds the site's `lat`, `lon` and `tz`. A point outside the wet mesh is refused; walk it back toward the dive area and re-run. Every later prediction runs in the site JSON's `tz`. Validate a new extract against the current station governing the site before trusting its timing.

`window`, `predict` and `at` read only the extract, as `--file <path>` or as its content inline with `--json`, exactly one of the two, and stop on a site JSON that carries no constituents. They print the principal current axis and, per exchange, the slack times and peak speeds, un-offset at the extract point and unlabelled for flood vs. ebb. `--position bottom`, `mid` or `surface` scales the depth-averaged speed toward that point in the water column; it moves speeds and window widths, never slack times. The `window` threshold defaults to `adcirc_current.max_speed_ms` in `tool-config.json` (0.25 m/s), a placeholder worth setting from experience.

`export-map` writes the map viewer's tidal current overlay: every mesh element with a node inside the box, or inside any of several boxes when `--bbox` is repeated to follow a coastline, with the harmonic constants of its nodes, as `map/currents/<name>.js`. The browser reconstructs the field for any moment with the same astronomy as `at` and interpolates across each element exactly as `extract` does, so the overlay at a site's extract point reads the same current as `at`. It keeps the largest constituents until the ones left out could cost any node at most `--max-drop` (default 0.03 m/s), and reports the actual truncation error against all 37. The file carries values this tool computed from it, which the browser reproduces before it draws anything; a mismatch stops the overlay with a message. The overlay is the depth-averaged field, for seeing how the water moves around a site; plans still come from the site's governing station and extract. The current file covers the Salish Sea, from Olympia and Cape Flattery north through the Strait of Georgia to the Discovery Islands:

```sh
python3 tools/adcirc_current.py export-map --bbox 47.0 -123.3 48.0 -122.0 --bbox 48.0 -124.0 48.8 -122.0 --bbox 48.15 -124.8 48.8 -124.0 --bbox 48.8 -124.6 49.8 -122.7 --bbox 49.8 -125.45 50.45 -123.5 --name salish-sea --label "Salish Sea"
```

Each export also adds or replaces its entry in `map/currents/index.js`, the list of overlays the map loads.

# ENPAC15 (ADCIRC spatial tidal currents)

<https://adcirc.org/products/adcirc-tidal-databases/>

A depth-averaged tidal current field for the whole Eastern North Pacific: the ENPAC15 harmonic constituent database, 37 constituents on an unstructured mesh of ~554k nodes refined into harbours, produced by the University of Oklahoma with NOAA's Coast Survey Development Laboratory using the ADCIRC model. Where a current station gives the current at a scattered point, this is a continuous field: it can predict at sites with no station near them and in the water between stations.

- **Use it for.** Current speed, direction and slack timing at any point inside the mesh, for any date, scaled to any working depth through the boundary layer profile. It predicts continuously across the whole domain, so it covers a site with no current station of its own and the water between existing stations equally well.
- **Depth-averaged, not a depth bin.** The mean over the whole column runs slower than the near-surface water and slower than the bin a current station reports. It is also smooth: it under-represents the sharp flood/ebb asymmetry of real rapids, softens the diurnal inequality, and is only approximate at any single point. It holds the semidiurnal slacks and the axis well; treat the unequal exchange and the peak speeds as approximate.
- **Coverage is not uniform.** Channels and passes are resolved; some shore entries fall just outside the wet mesh and snap to the boundary. The tool records how far out: a few hundred metres is a shore entry at the model edge, usable with care; kilometres out is unresolved. `boundary_dist_km` is only a real distance when `mesh.inside` is false; when `mesh.inside` is true it is a fixed 0.0, not a measure of how close the point sits to the edge, so a point well inside the mesh reads no differently from one just barely inside it.
- **Behaviour, not the flood/ebb label.** It gives the current axis, the slack times, and the peak speeds; which of the two axis directions is the flood is site-specific and has to be fixed against the tide or a station.
- **Distribution, not an API.** A single ~700 MB download, cached once in `tools/db/`, safe to delete (it re-downloads on the next extraction). Per-site extraction is time-independent: a site is extracted once and predicted forever.
- **Astronomy.** Pinned to the database's own reference nodal factors and equilibrium arguments (2004-11-16).

## `tools/adcirc_current.py`

Two uses, on different files.

1. Writing a new site file (needs the database). Extract the constituents at the dive-area coordinate, passing in the seabed depth (metres below MLLW) at that point:

   ```sh
   python3 tools/adcirc_current.py extract <slug> --near <lat> <lon> --water-depth 20
   ```

   Use the coordinate of the dive area (the deeper part actually dived), not the beach entry: a dive-area point lands inside the mesh and reads the current you experience, a shoreline point snaps to the mesh edge and reads near-still water. The extract is written as `<slug>.json` beside the site's `<slug>.md`. The `--water-depth` is what `--depth` scaling later uses; without it the extract falls back to the coarse mesh depth and the scaling is rough.

2. Planning a dive (reads only the small extract, never the database).

   ```sh
   python3 tools/adcirc_current.py predict <slug> --date 2026-07-12 [--depth M]   # slacks + peaks
   python3 tools/adcirc_current.py window  <slug> --date 2026-07-12 [--depth M]   # diveable windows
   python3 tools/adcirc_current.py at      <slug> --time "2026-07-12 09:18" [--depth M]
   python3 tools/adcirc_current.py list                                           # extracted sites
   ```

   It prints the principal current axis and, per exchange, the slack times and peak speeds, un-offset at the extract point (the site correction is still ours to apply) and unlabelled for flood vs. ebb. `--depth M` (below MLLW) scales the depth-averaged speed toward your dive depth through a boundary-layer profile (slower near the seabed, faster higher up); it moves speeds and window widths but never slack times, refuses if the dive depth exceeds the site's water depth, and is approximate, ignoring any brackish surface layer. Put the `predict`/`window` output, predicted beside observed, in `plan_log.csv`.

The threshold used by `window` is a placeholder, not a considered limit: 0.25 m/s is roughly 0.5 kn, a guess at what's comfortable in a drysuit, worth setting from experience. The default lives in `tool-config.json` as `max_speed_ms`.

Validate a new extract against the current station governing the site before trusting its timing. `python3 tools/adcirc_current.py selftest` verifies the astronomy against the database's own reference values.

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

Two uses, on different files.

1. Writing a new site file (needs the database). Extract the constituents at the dive-area coordinate, passing the full path to write:

   ```sh
   python3 tools/adcirc_current.py extract <path/to/slug.json> --near <lat> <lon> --tz <IANA_ZONE>
   ```

   Use the coordinate of the dive area (the deeper part actually dived), not the beach entry: a dive-area point lands inside the mesh and reads the current you experience, a shoreline point can fall outside the mesh entirely and get refused. `<path/to/slug.json>` is wherever the extract belongs, normally beside the site's `<slug>.md` in `regions/<region>/sites/`.

2. Planning a dive (reads only the small extract, never the database). `predict`/`window`/`at` take the extract to run against as `--file <path>` or `--json <content>`, exactly one of the two:

   ```sh
   python3 tools/adcirc_current.py predict --date 2026-07-12 [--position P]   --file regions/<region>/sites/<slug>.json   # slacks + peaks
   python3 tools/adcirc_current.py window  --date 2026-07-12 [--position P]   --file regions/<region>/sites/<slug>.json   # diveable windows
   python3 tools/adcirc_current.py at      --time "2026-07-12 09:18" [--position P] --file regions/<region>/sites/<slug>.json
   ```

   `--file` suits reading an extract off disk, as above. `--json` takes the same content inline instead, e.g. `--json "$(cat regions/<region>/sites/<slug>.json)"`, which suits a wrapper (a web API, another script) that already holds the extract's content and has no file to point at.

   It prints the principal current axis and, per exchange, the slack times and peak speeds, un-offset at the extract point (the site correction is still ours to apply) and unlabelled for flood vs. ebb. `--position bottom`, `mid`, or `surface` scales the depth-averaged speed toward that point in the water column through a boundary-layer profile (slower near the seabed, faster higher up); it moves speeds and window widths but never slack times, and is approximate, ignoring any brackish surface layer.

The threshold used by `window` is a placeholder, not a considered limit: 0.25 m/s is roughly 0.5 kn, a guess at what's comfortable in a drysuit, worth setting from experience. The default lives in `tool-config.json` as `max_speed_ms`.

Validate a new extract against the current station governing the site before trusting its timing. `python3 tools/adcirc_current.py selftest` verifies the astronomy against the database's own reference values.

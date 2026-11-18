# ADCIRC tidal databases (spatial tidal currents)

<https://adcirc.org/products/adcirc-tidal-databases/>

Depth-averaged tidal current fields from the ADCIRC tidal databases, harmonic constituent databases on unstructured meshes refined into harbours, produced by the University of Oklahoma with NOAA's Coast Survey Development Laboratory using the ADCIRC model. Where a current station gives the current at a scattered point, a database is a continuous field: it can predict at sites with no station near them and in the water between stations. The tool carries two, and the coordinate picks between them:

| Database | Waters | Mesh | Archive |
|---|---|---|---|
| **ENPAC15** | Eastern North Pacific: Mexico's Pacific coast, the US West Coast, British Columbia and southern Alaska, 19.6° to 61.5° N | 553,802 nodes | ~700 MB |
| **EC2015** | Western North Atlantic, Gulf of Mexico and Caribbean Sea: the US Atlantic coast and Nova Scotia to 45.9° N, the Gulf, the Bahamas and the Caribbean to 5.7° N | 2,066,216 nodes | ~2.6 GB |

- **Use it for.** Current speed, direction and slack timing at any point inside a mesh, for any date, scaled to a position in the water column (bottom, mid, or surface) through the boundary layer profile. It covers a site with no current station of its own and the water between existing stations equally well.
- **Depth-averaged, not a depth bin.** The mean over the whole column runs slower than the near-surface water and slower than the bin a current station reports. It is also smooth: it under-represents the sharp flood/ebb asymmetry of real rapids, softens the diurnal inequality, and is only approximate at any single point. It holds the semidiurnal slacks and the axis well; treat the unequal exchange and the peak speeds as approximate.
- **Tidal currents only.** A database holds the astronomical tide's currents. Ocean currents, wind-driven drift and river outflow are absent, and where they dominate, as along a Caribbean island's leeward shore, the model's slack is only the tidal part of the water's movement.
- **Coverage is not uniform.** Channels and passes are resolved; a coordinate walked too close to shore can fall outside the wet mesh. `extract` checks this and refuses a point outside the mesh rather than snapping to its boundary and predicting off a rough approximation; walk the coordinate back onto the covered side (toward the dive area) and re-run it. Trust a NOAA station instead for a site that never lands inside the mesh at all.
- **Element size sets what it can see.** `extract` prints the longest side of the element the point falls in. EC2015 is refined to tens of metres in US harbours and the Florida Keys, and runs 2 to 4 km around Bonaire, Curaçao and Cozumel, where it gives the tide's open-water current offshore of the island and nothing of the reef's own flow.
- **Behaviour, not the flood/ebb label.** It gives the current axis, the slack times, and the peak speeds; which of the two axis directions is the flood is site-specific and has to be fixed against the tide or a station.
- **Distribution, not an API.** Each database is one download, kept in `tools/db/` as its mesh and velocity file, fetched the first time a point inside it is extracted and again whenever deleted. Per-site extraction is time-independent: a site is extracted once and predicted forever.
- **Astronomy.** Pinned to each database's own run: the equilibrium arguments at its start (ENPAC15 2004-11-16, EC2015 1991-11-17) and the nodal factors and phases at its middle, 205 days later, as ADCIRC sets them. `selftest` checks the frequencies and the nodal factors against both headers.

## `tools/adcirc_current.py`

Standard library only.

```sh
python3 tools/adcirc_current.py extract --near <lat> <lon> > <out.json>                               # site file: print the extract, once
python3 tools/adcirc_current.py window --date 2026-07-12 --tz <IANA_ZONE> [--position P] --file <path/to/slug.json>     # planning: diveable windows
python3 tools/adcirc_current.py predict --date 2026-07-12 --tz <IANA_ZONE> [--position P] --file <path/to/slug.json>    #    slacks and peaks
python3 tools/adcirc_current.py at --time "2026-07-12 09:18" --tz <IANA_ZONE> [--position P] --file <path/to/slug.json> #    current at a moment
python3 tools/adcirc_current.py selftest [--db ENPAC15|EC2015]                                         # verify the astronomy
python3 tools/adcirc_current.py export-map --bbox S W N E [--bbox ...] --name <name> --label "<area>"                 # map viewer: the current overlay
```

`extract` is the only command that reads a database. Give it the coordinate of the dive area (the deeper part actually dived, not the beach entry). It picks the database whose domain holds the point and prints `{"enpac15_constituents": [...]}` or `{"ec2015_constituents": [...]}` on stdout, with its progress, the element's size and the principal axis on stderr, and writes no file; that object is attached to the site's `<slug>.json`, which already holds the site's `lat`, `lon` and `tz`. An EC2015 extract streams a 1.7 GB velocity file and takes several minutes. A point outside the wet mesh is refused; walk it back toward the dive area and re-run. Every later prediction takes `--tz`, required: the site's own IANA zone, the `tz` in its JSON. Validate a new extract against the current station governing the site before trusting its timing.

`window`, `predict` and `at` read only the extract, as `--file <path>` or as its content inline with `--json`, exactly one of the two, and stop on a site JSON that carries no constituents. The key names the database, and the header prints it. They print the principal current axis and, per exchange, the slack times and peak speeds, un-offset at the extract point and unlabelled for flood vs. ebb. `--position bottom`, `mid` or `surface` scales the depth-averaged speed toward that point in the water column; it moves speeds and window widths, never slack times. The `window` threshold defaults to `adcirc_current.max_speed_ms` in `tool-config.json` (0.25 m/s), a placeholder worth setting from experience.

`export-map` writes the map viewer's tidal current overlay: every mesh element with a node inside the box, or inside any of several boxes when `--bbox` is repeated to follow a coastline, with the harmonic constants of its nodes, as `map/currents/<name>.js`. The boxes all sit in one database, which the tool picks from them. The browser reconstructs the field for any moment with the same astronomy as `at` and interpolates across each element exactly as `extract` does, so the overlay at a site's extract point reads the same current as `at`. It keeps the largest constituents until the ones left out could cost any node at most `--max-drop` (default 0.03 m/s), and reports the actual truncation error against all 37. The file carries values this tool computed from it, which the browser reproduces before it draws anything; a mismatch stops the overlay with a message. The overlay is the depth-averaged field, for seeing how the water moves around a site; plans still come from the site's governing station and extract. One file covers the Salish Sea, from Olympia and Cape Flattery north through the Strait of Georgia to the Discovery Islands:

```sh
python3 tools/adcirc_current.py export-map --bbox 47.0 -123.3 48.0 -122.0 --bbox 48.0 -124.0 48.8 -122.0 --bbox 48.15 -124.8 48.8 -124.0 --bbox 48.8 -124.6 49.8 -122.7 --bbox 49.8 -125.45 50.45 -123.5 --name salish-sea --label "Salish Sea"
```

A second file, from EC2015, covers Bonaire and Klein Bonaire:

```sh
python3 tools/adcirc_current.py export-map --bbox 11.95 -68.50 12.40 -68.10 --name bonaire --label "Bonaire"
```

Each export also adds or replaces its entry in `map/currents/index.js`, the list of overlays the map loads.

# Current tool design

How `current.py` predicts, why it is built this way, what was tried on the way, and how to grow it. `current.md` is the operating manual; this file is for the agent who changes the tool. The goal it serves is one current tool for every water the workspace dives, from any tidal database and station network that joins it.

## The problem

A diver needs the current at a dive site, near the bottom, on a given day: when it turns, how hard it runs, and which way. Two kinds of source exist, and neither answers it alone.

- **Current stations.** NOAA's harmonic stations (ADCP surveys, several depth bins each) and CHS's stations give the current at their own point very well: NOAA's constants reproduce NOAA's predictions to within minutes. A station's current holds only at its point; copying the nearest station to a site 2 to 6 km away misses slack by 45 minutes at the median.
- **A tidal database.** ADCIRC's ENPAC15 is a continuous field over the whole coast, depth-averaged, on elements from tens of metres in some channels to over a kilometre along much of the Salish Sea's shore. It covers every site, and misses slack by about 40 minutes at the stations, with the wrong strength at many of them.

The current tool uses the database for the shape of the field between stations and the stations for its size, timing and direction near them.

## The method

### Build: every bin a correction

`build` places every station in the database's mesh and reads the database's constants there. For each NOAA bin it stores the height above the seabed as a fraction of the depth (the seabed from the NCEI tiles, or the mesh's own depth where no tile is cached), the bin's constants, its steady current and its direction. CHS publishes predictions without constants, so a CHS station's constants are fitted to its own predictions (`harmonic_fit`): every constituent the astronomy carries, over every 15-minute sample of this year's speeds, each signed by the flood or ebb between the slacks around it and weighted 1 / (|speed| + 0.3 m/s) so the fit holds hardest where the current turns. CHS states no depth for its series, so it is stored as a single bin at mid-depth, with the seabed from the bathymetry as for a NOAA station. From there a CHS bin is a bin like any other: every step below treats the two networks alike.

At prediction time each bin becomes a correction against the database at the same point, `source_bins`:

- **Per constituent.** The log of the complex ratio of the bin's constituent to the database's, along the database's own axis: the real part is the size, the imaginary part the timing. A constituent the database carries at under 1 cm/s (`MIN_AMP`) takes no ratio of its own.
- **Per band.** The same ratio for K1, M2 and M4, standing for the diurnal, semidiurnal and higher species. A constituent with no ratio of its own takes its band's, moved by the regional profile.
- **The steady current, the turn and the bin itself.** The bin's mean flow, its axis less the database's (`wrap90`, so the turn lies within 90°), and its own constants and azimuth for the exact step below.

### The vertical profile

`profile_table` takes every NOAA station with three or more bins and an NCEI seabed, expresses each bin's M2 and K1 as a ratio to the station's column mean, and keeps the median in each tenth of the depth with at least 8 bins: a complex ratio, the size and the minutes of lead. `vprof` applies it to any constituent: the diurnal table to the diurnals, the semidiurnal one to the rest with the phase scaled by the species so every constituent leads by the same time, and the size alone to the long period ones. Below the lowest tenth it follows the 1/7 power of the height. The profile moves a station's correction to a height its bins do not reach (`at_frac`), and scales the database where no station is in reach.

### At a point

`blend_at` takes the point's database constants and its distances through the water to every station, from Dijkstra paths over the mesh (`Mesh.paths`), each floored at the straight line (`floor_km`) because paths run node to node and a point sharing a station's node would otherwise read 0 km.

1. **Candidates.** The six nearest stations within 16 km through the water (`neighbours`).
2. **Each station at the height.** `at_frac` interpolates the log ratios between the two bins around the height, in log space with the phase unwrapped (`wrapc`), or extends from the nearest bin with the profile.
3. **The axis.** The database's axis turned by the weighted mean of the stations' turns (averaged as doubled angles, since an axis has no sign), with weight 0.3 on no turn.
4. **The blend.** Each constituent's log ratio is the weighted mean of the stations', with 0.3 on the band's own mean, which itself carries 0.3 on the regional profile alone. Weights are 1 / (d² + 1 km²). The constituent is the database's along the turned axis times the exponent of that mean. The steady current is the weighted mean of the stations' along the axis.
5. **Exactness.** The nearest station's own current is mixed in with λ = 0.5² / (0.5² + d²): Z = λ · own + (1 − λ) · Z, over the union of both sets of constituents, and likewise the steady current and the turn. At d = 0 the result is the station's bin exactly, at 0.5 km half of it, at 1 km a fifth.
6. **The flood.** `orient` points the axis toward the flood of the nearest station through the water, up to 300 km; `by_timing` then turns the axis and the constants end for end where the point's constants, against that station's own at the same height, have a negative covariance (Σ Re(Z · conj(Z_station)) < 0).

With no station within 16 km the point takes the database scaled by the profile, the flood named the same way.

### The extract and the prediction

`extract` evaluates `blend_at` at the site's height (2 m above the seabed, as a fraction of `seabed_m`) and at every twentieth of the column above it, keeps the one with the strongest M2 as `upper`, and writes both as NOAA-form constant sets. Prediction is `tools/lib/current_harmonics.py`, the same summation `verify-stations` checks against NOAA's own predictions. The observed offset is applied in `curve` as a time shift that moves each slack by its own figure and interpolates between them, so a maximum stays between its two slacks.

### Toward shore

`Mesh.place_site` stops on land by OpenStreetMap's coastline. A water point outside the mesh takes the element at the nearest point of the mesh's edge (`walk_in`) when that point lies within 1 km (`EXTEND_KM`) and a line sampled every 10 m stays on water. The map applies the same rule in the browser (`place` and `_walkIn` in `map/currents.js`), and the drawing grid a shortcut of it (`edgePoint`), from the shoreline nodes `export-map` marks. Holding the edge's constants is the defensible extrapolation: the mesh carries no physics inside that strip, and anything fancier would be invented.

### The map

The browser runs the blend itself. `map_export.py currents` ships its inputs, computed with `tools/lib/blend.py`: the database's NOAA-form constants at each mesh node as int16 with one scale per node, each node's stations within 16 km through the water, every station's bins as `source_bins` prepares them, the profile table, and per year each constituent's node factor and argument constant. `map/currents.js` ports `blend_at`, `at_frac`, `vprof`, the placing of a point (`place_site`, `walk_in`, `locate`) and the prediction line for line, so a point read on the map is an extract taken there. Two parts are left out because they change no current: `orient` and `by_timing` turn the axis end for end with the sign of every constant. The map's land test is the coastline mask it draws with, not the polygons `place_site` reads, so the two can disagree on a point within a mask cell of the shore.

The trails use the same blend once per node at load, at the node's own seabed, and interpolate between nodes as before. Sample nodes, and sample points the export picks inside elements and just off the mesh's shoreline, ride along with the tool's own values as a check, so a port that drifts from the tool refuses to draw. The int16 constants hold each node to 1 part in 32,767 of its largest value; in water whose tidal ellipse is nearly a circle that moves the principal axis by a few hundredths of a degree, which sets the 0.15° the check allows.

## Why it is this way

### What was tried

- **Column-mean corrections.** The first version averaged each NOAA station's bins over the column into one correction and reached a height through the regional profile alone. Between stations it scored as well as today (34 minutes on hidden stations), but at the stations themselves it missed by 26 minutes, 11 to 14% on peaks and 4.5° on direction. Three causes: the station's own measured profile was thrown away; the 0.3 pull toward the database applied even at 0 km, so about 77% of a correction got through (at Agate Pass, PUG1501's M4 ratio fell from 2.17 to 1.81, flattening the flood and ebb difference); and constituents present in one source but absent from the other (MU2 at 5 cm/s in the database at PUG1501, the seasonal ones in the stations) moved slack by several minutes. Per-bin corrections, the exactness term over the union of constituents, and fading the absent ones with λ fixed all three, and the blind tests stayed the same or improved (legacy 27.0 to 25.4 minutes).
- **Additive near a station, ratio between them.** Mixing ratios near a station cannot reproduce a constituent the database lacks; mixing the constants themselves can. The exactness step is additive for that reason, and the blend between stations stays multiplicative, where ratios carry the database's spatial shape.
- **Weight shapes.** Inverse distance and exponential kernels, with several softening distances, neighbour counts and prior weights, were swept against both blind tests: every choice landed between 32 and 37 minutes on hidden stations and 28 to 30% on speed. The chosen 1 / (d² + 1 km²), six neighbours, 16 km and 0.3 sit on that plateau; between stations about 30 minutes is the floor every alternative reached, against about 6 minutes with a station's own constants.
- **Correcting per constituent or per band only, and straight-line distance against distance through the water.** Neither moved the blind scores much; distance through the water stays because it keeps a station across a peninsula from correcting a point on the other side.
- **The direction.** Turning the database's axis toward the stations' left timing and speed unchanged and brought the map's axis at the stations from 10° to 3° at the median; with per-bin corrections and exactness it is 0°.
- **The flood label.** Naming the flood by the nearest station's flood bearing alone flipped several sites by about 180°, where the point's axis lies across the station's. Naming it by the timing (`by_timing`) follows the water; a flip that remains is the point really running against the station.
- **The walk.** The first current tool on the database moved a point outside the mesh to the nearest point 5 m inside it and predicted there. The shore extension replaced it with a cap, a land check and the prediction kept at the site's own coordinate and seabed.

- **The CHS fit.** The first fit took 30 constituents over one year of hourly samples, unweighted: against CHS's own events it followed slack within 3.2 minutes at the median station (90% within 9.8), and at Tillicum Bridge 90% of its slacks fell within 104 minutes. Fitted to 2025 and 2026 and judged on December 2027, every 15-minute sample and all 37 constituents brought Tillicum Bridge's 90% to 33 minutes; weighting the samples by 1 / (|speed| + 0.3 m/s) brought Sechelt Rapids' from 24 to 15 minutes and Race Passage's from 18 to 14, for a point or two of peak speed. The softening speed sits on a plateau from 0.15 to 0.6 m/s, and a second year of samples moved nothing, so one year it stays, which keeps a first build's download at one year a station. What remains is the shape of a rapid's current, far from a sum of tides, which no set of constants reproduces.

### Alki Pipeline

The first test case. 1.4 km from PUG1516, the column-mean version missed its bins by 50 minutes; the station's own axis and depth-matched bins did not help. The site sits in a weak, eddying current off a point, and the database turns 62° across the bay between the station and the pin. It is the clearest example of the hard places below.

## The tests

`verify` is the record of the method; every change to it is judged by all three tests, each run on both networks wherever the region holds them, run over 30 days from 1 December, and written to `<region>_verify.json`. The figures below are the Salish Sea region's, December 2026.

- **At the stations.** Each NOAA station's deepest, middle and top bin, predicted at its own position and height with the station in place: 395 bins at 0 minutes on slack, 0% on peak speed and 0° on direction. It must stay there: any change that breaks exactness is a regression. Each CHS station, the same way, against CHS's own published slacks and maxima: 17 stations at 2.7 minutes on slack at the median (90% within 8.9), 4.6% on peak speed and 0° on direction. At a CHS station the blend equals the fitted constants exactly, so this figure is the fit's own distance from CHS.
- **Hidden stations.** Each NOAA station's deepest bin, predicted with the station and its profile rows left out, against copying the nearest other station and the database alone, by distance band. Over 135 stations: slack within 34 minutes at the median (80% within 56) and peak speed within 28%, against 45 minutes and 38% for the nearest station and 40 minutes and 30% for the database alone. By the nearest remaining station: within 2 km 24 minutes, 2 to 6 km 33 minutes, 6 to 16 km 36 minutes, beyond 16 km 48 minutes.
- **Hidden CHS stations.** Each CHS station predicted with it left out, against CHS's own published slacks and maxima at mid-depth. Over 17 stations: slack within 18 minutes at the median (80% within 29) and peak speed within 35%, against 19 minutes and 31% for the nearest station and 21 minutes and 33% for the database alone.
- **Legacy tables.** The 2010 subordinate stations, each its reference moved by its own published corrections, near the surface: a test independent of the modern surveys. Over 117 stations: slack within 25 minutes and peak speed within 25%, against 29 minutes and 26% for the nearest station and 42 minutes and 35% for the database alone.

### Station data

- **NOAA.** `tools/lib/noaa_stations.py` keeps NOAA's station list and one file per station in `tools/db/noaa_current/`: every bin's constants, depth, steady current and azimuth, and each published bin's flood and ebb directions. H stations carry their own constants, S stations only corrections to a reference, W stations no predictions; the build reads every bin with constants, the ones NOAA leaves unpublished included, and lists S and W as others. The prediction (`tools/lib/current_harmonics.py`, `tools/lib/tidal_astronomy.py`) follows Schureman with NOAA's conventions, node factors held at mid-year; in November 2026 all 2,281 published harmonic bins agreed with NOAA's live API over 30 days within 0.004 m/s every six minutes, and every slack and maximum within 3 minutes and 0.013 m/s on 2,279 (the other two differ by one event on a flat curve).
- **CHS.** `tools/lib/chs_stations.py` keeps CHS's station list in `tools/db/chs_current/`, one file per station (position, flood and ebb directions, and what CHS holds) and one per station and UTC year with that year's speed series and events, downloaded from CHS's IWLS API at the 30 requests a minute it allows, about two minutes a station year; a year CHS did not yet hold is asked for again once. `build` fits constants to this year's (`fit_year` in the region file). In November 2026, against CHS's own published events over December, the fit followed every station's slacks within 0.6 to 9.5 minutes at the median and peak speed within 0 to 17%; the stations in the high range are the rapids and narrows whose current is far from a sum of tides (Tillicum Bridge, Juan de Fuca East, Calamity Point, Sechelt Rapids, Second Narrows).
- **The check.** `verify-stations` gives each ID to the network whose `owns` claims it, and that network's `verify` compares its cache with the live service over the 30 days from today. A NOAA bin passes within 0.02 m/s and 3 minutes on speed and on every slack and maximum, a flat-curve event judged on speed and events in the first hours of a UTC year left out; a station with no published bin has nothing to compare and is reported so. A CHS station passes when every value and event matches exactly.
- **Downloads.** Every source fetches what it lacks the first time it is asked: the database through `need_db`, NOAA stations through `noaa_stations.station`, CHS stations and years through `chs_stations.year_file`, the legacy tables through `tcd.legacy`, NCEI tiles through `ncei.tile_path`, the DCBD grid through `dcbd.grid`.

### Pinned astronomy

The equilibrium arguments are set at each database run's start (ENPAC15 2004-11-16, EC2015 1991-11-17) and the nodal factors and phases at its middle, 205 days later, as ADCIRC sets them. `selftest` checks every constituent's frequency and nodal factor against each database's header.

## Open problems

- **Direction near shore.** Where a pin falls in a database element touching the shore, the axis follows the mesh's coarse coastline. At Sund Rock the canal floods southwest (219°) and the pins' elements give 143° to 146°. A candidate: take the direction, and possibly the speed, from the nearest element clear of the shore, and test it against the hidden stations nearest a coast.
- **Speed near shore.** The same elements can run slower or faster than the water divers describe: at Fox Island East Wall the site reads stronger than the tool, and at Richmond Beach Park research gives moderate where the tool gives gentle. The site file's wording, from research, describes the water; the tool's speed is what the plan uses.
- **The flood label in weak water.** Under a few cm/s the timing ties a point only loosely to its station, and the label can flip over a few hundred metres (off Point White Dock). A confidence for the label, from the covariance's size against the amplitudes, would let the header say so.
- **Eddies and back eddies.** Behind pilings, in coves and off points the local water can run against the channel for part of the tide (Titlow, Sunnyside). No tidal database here resolves them; the observed offset and the site's prose carry them.
- **The height of a CHS series.** CHS states no depth for its predictions, so each sits at mid-depth. A height nearer the surface would move each CHS correction down the column by the profile; the hidden CHS test, run with the bin at other heights, would show which reads truer.
- **Beyond reach.** Where no station lies within 16 km the error grows (48 minutes on the hidden stations past 16 km). A station surveyed there narrows it, and the next `build` takes it in.

## Extending it

`tools/lib/blend.py` holds the method, which `current.py` and `map_export.py` both call; what it reads comes through three seams, each a list a new source joins without touching the correction:

- **Tidal databases.** `DATABASES` in `tools/lib/adcirc.py` (ENPAC15, EC2015), picked by `database_for(bbox)` as the one whose domain holds the region's box.
- **Station networks.** `NETWORKS` in `tools/lib/current_stations.py` (NOAA harmonic, CHS predictions). Each network's `gather` lists its stations in a box, downloading through its own code whatever is not yet cached (NOAA's through `tools/lib/noaa_stations.py`, CHS's through `tools/lib/chs_stations.py`), its `prepare` turns one into bins and returns its vertical profile rows, and `owns` and `verify` let `verify-stations` hand a station ID to its network and check its cache against the network's live service. A new network brings all four.
- **Bathymetries.** `SOURCES` in `tools/lib/seabed.py` (NCEI tiles, the GSC West Coast DEM, DCBD Bonaire), asked in order for the seabed under each station and map node, each downloading what it covers the first time a point there is asked for. A station no bathymetry covers takes the database's own depth.

### A new region on the same database

1. `build --name <region> --bbox S W N E`, then `verify --name <region>`. The at-stations test must read 0, 0, 0; read the hidden and legacy tables against the nearest station and the database alone.
2. `extract --site` on all of its sites in one run, and an area for it in `map/coverage.json` when the map should show it.

`load_region` picks the first region whose box holds a point, so boxes should not overlap.

### A region with no stations

A region whose box holds no current station degrades in three places, and each is stated in the output:

- **No correction.** With no station within 16 km a point takes the database's own constants (`blend_at` with no candidates); with none in the region at all, every point does.
- **No measured profile.** `profile_table` finds no rows, and `vfac` falls back to the 1/7 power law over the whole column, speed alone, with no change in timing. Borrowing another region's profile was rejected: a profile belongs to its own water's stratification and tidal strength.
- **No flood name.** With no station within 300 km, `orient` leaves the axis as `principal_axis` gives it, and the header calls flood and ebb the two ends of the axis.

`verify` reports that it has nothing to test and writes a verify file with no stations. Adding a station network that covers such a region turns it into an ordinary one at the next build.

### A new tidal database

A different model enters as a `DATABASES` entry with its reader: it needs a mesh with element connectivity for the paths, the shore test and the map, and constituents at any point converted to NOAA's convention (`to_noaa`, `TREF`). The blend itself only sees `uv`, the database's complex east and north constituents at a point, so a model that can produce them plugs in without touching the correction.

### A new station network

A class in `NETWORKS` with a `kind`, `gather(inbox, fit_year)` returning (stations, others without constants) and downloading what is not cached, `prepare(station, H, Hdem, fit_year, log)` setting `bins` and returning profile rows, `owns(id)` claiming its station IDs, and `verify(id)` returning (passed, report lines) from a comparison with its live service. A station is a dict with `id`, `kind`, `name`, `lat`, `lon` and `flood`; each bin is [fraction of the depth, steady current cm/s, azimuth, {constituent: complex amplitude in NOAA's convention}]. NOAA's harmonic stations give these directly. CHS shows the route for a network that publishes predictions only: keep the predictions in its own `tools/lib/` module, fit constants to a year of them (`harmonic_fit`) and treat the series as one bin at mid-depth, or at its stated depth where the network gives one. Only a network with several bins over a known seabed adds profile rows.

### A new bathymetry

A class in `SOURCES` with a `name`, a `datum` and `elevation(lat, lon)`, answering metres, negative under water, or None where it holds nothing. It downloads through its own tool what covers a point the first time that point is asked for; the shared reader belongs in `tools/lib/`, as `dem_tiles.py` and `dcbd.py` do for their tools.

### Several databases at once

A coast covered by two models, or a model refined by a regional one, would build each region on the finer model inside its domain. Where two regions meet, the stations near the seam belong to both, so their corrections agree at the boundary; a point is extracted from the region holding it.

### Changing the method

Change one thing, rebuild, and run `verify`; a change to the astronomy in `tools/lib/adcirc.py` runs `selftest` first. A change to the blend, the profile, the placing of a point or the prediction is mirrored in `map/currents.js`; `map_export.py currents` then proves the two agree at sample nodes and sample points of its own choosing. A change to the region file's layout raises `FORMAT`, which makes every command ask for a rebuild. Keep the at-stations test at zero, compare the hidden and legacy medians with the figures above, and update this file with what was tried and what it scored, kept or not. The settings in force are recorded in each region file under `settings`.

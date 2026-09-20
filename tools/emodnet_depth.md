# EMODnet Bathymetry (with a GEBCO fallback)

<https://emodnet.ec.europa.eu/en/bathymetry>

Seabed depth at a coordinate. EMODnet Bathymetry is the European Marine Observation and Data Network's bathymetric grid, built by blending real multibeam and hydrographic survey soundings, catalogued through SeaDataNet's Common Data Index, rather than a single smoothed global surface. Free, JSON over HTTPS, no API key.

- **Use it for.** The seabed depth at a dive-area coordinate, and a check that the point is underwater at a plausible depth at all.
- **A real survey behind the number, where one exists.** Every query returns the count of soundings behind that grid cell and, where a cataloged survey covers it, that survey's own identifier and a link to its metadata. A cell with a real survey behind it is worth more than one silently interpolated from its neighbours, and the tool always tells you which you got.
- **Resolution.** About 115 m at low latitudes (a 1/16 arc-minute grid), coarse next to a reef terrace only a few hundred metres wide or a narrow channel. Good for confirming a point sits on the shelf, the wall, or well out past both, not for centimetre precision on a shore-entry coordinate.
- **Coverage is not global.** It runs well beyond continental Europe wherever a contributing survey happens to reach, but a point with nothing behind it returns empty. This tool falls back automatically to GEBCO_2024, the IHO/IOC's own global bathymetric grid, at a coarser 15 arc-second (~450 m) resolution, served through the OpenTopoData API. GEBCO always answers, but a demonstrated case at this same coordinate can differ from EMODnet's survey-backed figure by tens of metres near a steep drop-off; treat a GEBCO-only answer as a rough placeholder, not a number to build a plan on.
- **Datum.** EMODnet reports depth below LAT (Lowest Astronomical Tide, the chart datum used on nautical charts). GEBCO's grid sits close to mean sea level. The two are not interchangeable with each other or with a workspace region's own fixed datum; convert before mixing either with one.
- **Positive means land.** Both sources report a signed elevation; a positive value flags the coordinate as dry.

## `tools/emodnet_depth.py`

```sh
python3 tools/emodnet_depth.py <lat> <lon>            # EMODnet's survey-backed grid, GEBCO on no coverage
python3 tools/emodnet_depth.py <lat> <lon> --gebco    # skip straight to the global GEBCO grid
```

Sample output, a point with a real survey behind it:

```
12.140000, -68.280000
  seabed 92.1 m below LAT (chart datum)  [EMODnet, ~115 m grid]
  range 82.3 to 108.1 m within this grid cell (stdev 3.7 m)
  source: survey MB64PE430, 25213 soundings in this cell
  https://cdi-bathymetry.seadatanet.org/report/edmo/630/MB64PE430
```

The `range` line is the spread of individual soundings inside that one grid cell, not measurement noise; a wide spread means real relief within the cell (a slope or a step), not an unreliable reading. A high `elementarySurfaces` count backs the average with real data; a low one, or a `source` line reading "interpolated, no cataloged survey," is telling you the grid filled a gap rather than measured it, worth a second, closer-in query before trusting it for a shore-entry coordinate.

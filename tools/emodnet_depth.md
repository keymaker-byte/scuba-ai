# EMODnet Bathymetry (survey-backed depth, Europe and the European Caribbean)

<https://emodnet.ec.europa.eu/en/bathymetry>

Seabed depth at a coordinate. EMODnet Bathymetry is the European Marine Observation and Data Network's bathymetric grid, built by blending real multibeam and hydrographic survey soundings, catalogued through SeaDataNet's Common Data Index. Free, JSON over HTTPS, no API key.

- **Use it for.** The seabed depth at a dive-area coordinate, and a check that the point is underwater at a plausible depth at all.
- **A real survey behind the number, where one exists.** Every query returns the count of soundings behind that grid cell and, where a cataloged survey covers it, that survey's own identifier and a link to its metadata. A cell with a real survey behind it is worth more than one interpolated from its neighbours, and the tool always says which it is.
- **Resolution.** About 115 m (a 1/16 arc-minute grid), coarse next to a reef terrace only a few hundred metres wide or a narrow channel. Good for confirming a point sits on the shelf, the wall, or well out past both, and too coarse for a shore-entry coordinate.
- **Coverage.** Europe's seas and the North Atlantic from 25° to 85° N, plus a Caribbean tile from 11° to 19° N and 70.5° to 59.5° W that takes in Bonaire, Curaçao, Aruba and the Lesser Antilles. A point outside it stops the run with a message; `gebco_depth` is the separate global grid.
- **Datum.** Depth below LAT (Lowest Astronomical Tide, the chart datum used on nautical charts). Convert before mixing it with a region's own fixed datum.
- **Positive means land.** A positive elevation flags the coordinate as dry.
- **A failed request stops the run.** A refusal, a non-JSON answer or an unreachable service ends the run with what failed and the URL asked for.

## `tools/emodnet_depth.py`

Standard library only.

```sh
python3 tools/emodnet_depth.py <lat> <lon>    # EMODnet's survey-backed grid
```

Each answer prints the depth with its datum and grid, the spread of soundings inside the grid cell, and the source: a survey id with its sounding count and metadata link, or a note that the cell is interpolated with no cataloged survey. The spread is real relief within the cell, a slope or a step. A low sounding count or an interpolated cell filled a gap; query a point closer in before trusting it for a shore-entry coordinate.

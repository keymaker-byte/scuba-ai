# DCBD coastal bathymetry of Bonaire (2 m reef depth)

<https://www.dcbd.nl/resource/2869>

Seabed depth on Bonaire's and Klein Bonaire's shallow reef at 2 m resolution: E. Meesters' 2020 coastal bathymetry, published on the Dutch Caribbean Biodiversity Database.

- **Use it for.** The seabed depth at a dive area or entry on Bonaire, and walking a coordinate across the terrace to the drop-off. At 2 m it resolves the terrace, the sand and the reef crest that a coarse global grid averages into one figure.
- **Bonaire only, and shallow only.** The grid covers both islands from the shoreline out as deep as the survey reached: 20 m at most, often less (about 10 to 12 m in places). Land, water deeper than that, and anything unsurveyed all read as no data. On a pixel with no data the tool reports the nearest pixel that has some, with its distance, bearing and depth, so the edge of the survey shows where the reef keeps going deeper. For depth past the edge, use `emodnet_depth`.
- **The shoreline edge.** The grid starts a few metres off the waterline, where the water is already 2 to 5 m deep off a rocky shore, and holds no value on the beach or rock itself. An entry point on the rocks reads the first pixel of water beside it.
- **Datum.** The dataset states none; its values sit at about sea level, with the shoreline at zero. Bonaire's tidal range of about 30 cm sits inside the grid's own precision, so a depth here is read as a plain observed depth.
- **Projection.** The grid is in WGS 84 / UTM zone 19N; the tool converts the coordinate it is given.
- **The spread around a point.** `at` also gives the shallowest and deepest pixel within `--radius`, the relief right around the point: a narrow spread on the terrace or sand, a wide one on the drop-off.

## `tools/dcbd_depth.py`

Standard library only.

```sh
python3 tools/dcbd_depth.py at <lat> <lon>                                  # depth at a point, and the spread within 10 m
python3 tools/dcbd_depth.py at <lat> <lon> --radius 25 --search 200         # a wider spread, a wider search for data
python3 tools/dcbd_depth.py transect <lat1> <lon1> <lat2> <lon2> --step 10  # depth every 10 m from entry to dive area
```

The first run downloads the 34 MB zip from DCBD, keeps only its GeoTIFF as `tools/db/dcbd_bonaire_depth.tif` (48 MB), and reads it locally after that, in well under a second per query. Deleting the file fetches it again. A failed download stops the run with what failed.

`--radius` (default 10 m), `--search` (default 100 m) and `--step` (default 10 m) fall back to `radius_m`, `search_m` and `step_m` in the `dcbd_depth` section of `tool-config.json`.

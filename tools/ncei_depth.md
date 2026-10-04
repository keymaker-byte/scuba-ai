# NCEI coastal DEM (bathymetry, water depth)

<https://gis.ngdc.noaa.gov/arcgis/rest/services/DEM_mosaics/DEM_all/ImageServer>

NOAA NCEI's coastal digital elevation model: the seabed depth at a point, at up to ~3 m resolution (1/9 arc-second) in the best-mapped areas. It owns bathymetry for the workspace.

- **Use it for.** The water depth at a dive point, which goes in the site file's Coordinates row and into the ADCIRC extraction step's water-depth input. A spatial current model's own mesh cannot supply it: its elements can span from the beach to the deep basin, so its nearshore depth can be wrong by tens of metres. The DEM's 3 m soundings are the authority.
- **Also a sanity check on a coordinate.** Is this point underwater at all, and at a divable depth? It reads the actual bottom where a nautical chart gives scattered soundings between wide contours.
- **Datum.** The DEM tile's own, usually NAVD 88 (roughly mean sea level here), not MLLW. Good to a couple of metres for the boundary-layer scaling and a divable-or-not check; a depth normalized to datum still has to be converted to MLLW before it goes in a site file.
- **Point query.** Via the ImageServer `identify` operation, no key, needs a User-Agent. Returns the elevation and the source tile (name, resolution, datum). Positive means above water, which flags a coordinate on land.

## `tools/ncei_depth.py`

Standard library only.

```sh
python3 tools/ncei_depth.py <lat> <lon>                     # depth below NAVD88 (~mean sea level)
python3 tools/ncei_depth.py <lat> <lon> --mllw              # also below MLLW, the site file figure
python3 tools/ncei_depth.py <lat> <lon> --mllw --region R   # pick the VDatum region explicitly
```

`--mllw` converts via NOAA VDatum, falling back to the NAVD88-to-MLLW offset from the nearest tide station publishing both datums, then to a flat nominal if neither answers, and reports which it used. The offset is not constant: it runs from a few centimetres in some areas to most of a metre in others.

VDatum will not infer its region from the coordinate, and the wrong one fails with an opaque "Uncaught error". `--region` overrides `ncei_depth.default_region` in `tool-config.json`; `--help` lists every valid region code.

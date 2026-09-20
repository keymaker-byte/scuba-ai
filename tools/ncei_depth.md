# NCEI coastal DEM (bathymetry, water depth)

<https://gis.ngdc.noaa.gov/arcgis/rest/services/DEM_mosaics/DEM_all/ImageServer>

NOAA NCEI's coastal digital elevation model: the seabed depth at a point, at up to ~3 m resolution (1/9 arc-second) in the best-mapped areas. It owns bathymetry for the workspace.

- **Use it for.** The water depth at a dive point, which goes in the site file's Coordinates row and into the ADCIRC extraction step's water-depth input. A spatial current model's own mesh cannot supply it: its elements can span from the beach to the deep basin, so its nearshore depth can be wrong by tens of metres. The DEM's 3 m soundings are the authority.
- **Also a sanity check on a coordinate.** Is this point underwater at all, and at a divable depth? It reads the actual bottom where a nautical chart gives scattered soundings between wide contours.
- **Datum.** The DEM tile's own, usually NAVD 88 (roughly mean sea level here), not MLLW. Good to a couple of metres for the boundary-layer scaling and a divable-or-not check; a depth normalized to datum still has to be converted to MLLW before it goes in a site file.
- **Point query.** Via the ImageServer `identify` operation, no key, needs a User-Agent. Returns the elevation and the source tile (name, resolution, datum). Positive means above water, which flags a coordinate on land.

## `tools/ncei_depth.py`

```sh
python3 tools/ncei_depth.py <lat> <lon>                               # depth below NAVD88 (~mean sea level)
python3 tools/ncei_depth.py <lat> <lon> --mllw                        # also convert to depth below MLLW
python3 tools/ncei_depth.py <lat> <lon> --mllw --region R             # pick the VDatum region explicitly
```

Site files quote depth below MLLW, so use `--mllw`. It converts via NOAA VDatum, falling back to the NAVD88-to-MLLW offset from the nearest tide station publishing both datums, then to a flat nominal if neither answers, reporting which it used. The offset is not constant: it can run from a few centimetres in some areas to most of a metre in others.

VDatum tiles the world into named regions and will not infer one from the coordinate; the wrong region, or its own `contiguous` default (Atlantic/Gulf coasts), fails with an opaque "Uncaught error" rather than a useful message. `python3 tools/ncei_depth.py --help` lists every valid region code. `--region` overrides `ncei_depth.default_region` in `tool-config.json`, which holds this workspace's default (`westcoast`). Some regions additionally require a specific target horizontal frame for a tidal target datum (westcoast wants IGS14); VDatum names the required frame in its own error when this applies, and the tool retries once with whatever it names, so that quirk never needs to be handled by the caller.

# NCEI coastal DEM (bathymetry, water depth)

<https://www.ncei.noaa.gov/products/coastal-elevation-models>

NOAA NCEI's coastal digital elevation model: the seabed depth at a point, at about 3 m resolution (1/9 arc-second). It owns bathymetry for the workspace. Read from the DEM's own tiles kept on this machine: a tile is downloaded once, the first time a point inside it is asked for, and every depth in that tile after that is read with no request at all.

- **Use it for.** The water depth at a dive point, which goes in the site file's Coordinates row and into the ADCIRC extraction step's water-depth input. A spatial current model's own mesh cannot supply it: its elements can span from the beach to the deep basin, so its nearshore depth can be wrong by tens of metres. The DEM's 3 m soundings are the authority.
- **Also a sanity check on a coordinate.** Is this point underwater at all, and at a divable depth? It reads the actual bottom where a nautical chart gives scattered soundings between wide contours.
- **Coverage.** The ninth arc-second tiles NOAA publishes, about 930 of them along the US coasts: Washington, Oregon, California, the Gulf, the Atlantic seaboard and part of Alaska. A point outside them stops the run with a message.
- **The data.** `tools/db/ncei_depth/` holds NOAA's tile list, one GeoTIFF per quarter-degree tile, and the NAVD 88 to MLLW offsets VDatum has answered. A tile is about 200 MB, so its first use takes a few minutes on a fast connection and much longer on a slow one. `--fetch` downloads a whole area ahead of time. Deleting a tile, or the folder, fetches NOAA's current data on the next run, which is how a re-surveyed tile is picked up.
- **The value is the pixel the point falls in.** The tile's own georeferencing places each 3 m pixel, and the tool reads the one containing the coordinate. NCEI's live map service answers with a pixel half a cell to the south-east, 1.7 m away, so the two agree within a few centimetres on a gentle bottom and differ by up to 1.4 m on a steep wall.
- **Datum.** NAVD 88 (roughly mean sea level here). A depth normalized to datum is converted to MLLW with `--mllw` before it goes in a site file.
- **MLLW comes from VDatum, once per place.** The height of NAVD 88 above MLLW runs from a few centimetres in some areas to more than a metre in others. `--mllw` asks NOAA VDatum for it at the point, keeps the answer, and uses a kept answer for any later point within 200 m, so a site's second query needs no network. The output names the offset, where it was asked and when. VDatum publishes its grids behind a terms-of-use page that turns automated clients away, so the tool asks its conversion service point by point.
- **VDatum needs its region.** It will not infer the region from the coordinate, and the wrong one stops the run with VDatum's own message. `--region` overrides `ncei_depth.default_region` in `tool-config.json`; `--help` lists every valid region code.
- **Positive means land.** An elevation above zero flags a coordinate on land.
- **A failed download stops the run.** A refusal, a short or unreadable file, an unreachable server or a VDatum error ends the run with what failed and the URL asked for, and leaves no partial file behind. A point in a cached tile, with a kept offset nearby, needs no network.

## Before relying on it

- **A tile goes stale silently.** NOAA replaces tiles as new surveys arrive, and a cached tile keeps the old soundings. `--verify` compares the tile with NCEI's live service at the point; run it when a site's depth matters more than usual.
- **A `--verify` failure is a stop.** Report it and wait; on a failure, delete the tile and the tile list, run it again, and report it if it still fails.
- **The DEM is a model of the bottom.** It blends surveys of different ages and densities, and a narrow wall or a pinnacle smaller than a few pixels is smoothed. Good to a metre or two at most dive sites.

## `tools/ncei_depth.py`

Standard library only.

```sh
python3 tools/ncei_depth.py <lat> <lon>                     # depth below NAVD88 (~mean sea level)
python3 tools/ncei_depth.py <lat> <lon> --mllw              # also below MLLW, the site file figure
python3 tools/ncei_depth.py <lat> <lon> --mllw --region R   # pick the VDatum region explicitly
python3 tools/ncei_depth.py <lat> <lon> --verify            # compare the tile with NCEI's live service
python3 tools/ncei_depth.py --fetch <S> <W> <N> <E>           # download every tile touching a box, ahead of time
```

Each answer prints the depth, the tile it came from, and with `--mllw` the depth below MLLW with the offset used. `--verify` passes when NCEI's live service answers from the same tile and its value matches one of the nine pixels at and around the point within 0.01 m.

`--fetch` caches tiles ahead of time, for working with no connection: every tile touching the box of south, west, north and east edges, six at a time (`--workers`), repeated for several boxes. It skips what is already here, so a stopped run picks up where it left off. The US side of the Salish Sea is 45 tiles and 8.4 GB:

```sh
python3 tools/ncei_depth.py --fetch 47.0 -123.5 49.0 -122.0 --fetch 48.0 -124.75 48.5 -123.5
```

`ncei_depth.user_agent_email` in `tool-config.json` sets the contact address sent in the User-Agent of a download.

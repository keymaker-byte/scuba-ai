# GEBCO global grid (rough depth anywhere)

<https://www.gebco.net/data-products/gridded-bathymetry-data>, <https://www.opentopodata.org/datasets/gebco2020/>

Seabed depth at any coordinate on Earth from GEBCO, the IHO and IOC's global bathymetric grid, served point by point through the OpenTopoData API. Free, JSON over HTTPS, no API key.

- **Use it for.** A rough first look at a coordinate no other depth tool covers: is it underwater, on a shelf or off a drop-off.
- **A placeholder, never a plan figure.** The grid is 15 arc-seconds, about 450 m, and blends surveys with satellite-derived depths. Near a steep drop-off it can differ from a survey-backed figure by tens of metres. A site's depth comes from a survey-backed tool.
- **Edition.** GEBCO_2020, the edition OpenTopoData serves.
- **Datum.** Close to mean sea level.
- **Positive means land.** A positive elevation flags the coordinate as dry.
- **A failed request stops the run.** A refusal, a non-JSON answer or an unreachable service ends the run with what failed and the URL asked for.
- **Rate limit.** OpenTopoData's public API allows one request a second and 1,000 a day.

## `tools/gebco_depth.py`

Standard library only.

```sh
python3 tools/gebco_depth.py <lat> <lon>    # GEBCO's global grid
```

Each answer prints the depth below mean sea level, or flags the point as above water, with the edition and grid named.

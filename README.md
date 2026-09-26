# scuba-ai

Scuba AI is a collection of steering files, tools and dive site descriptions for scuba diving recreational planning within no-decompression limits. Point an LLM (e.g. Claude Code) at this workspace and it can plan dives, write up new dive sites, and answer questions using live NOAA current and tide predictions, tidal current models, bathymetry, wind forecasts and your own dive log, instead of guessing.

## Safety

This is a planning aid, not a dive plan by itself and not a substitute for training or judgement. It predicts; it does not guarantee.

- Dive only within the limits of your certification and training. Treat every prediction here as a starting point to verify against what you actually see, not a fact to trust blindly.
- Currents, tides and visibility are forecasts, built from models and stations some distance from the actual site. Conditions on the day can differ from any prediction, sometimes by a lot; confirm from the surface before committing, and abort if what you find does not match the plan.
- If you do not know a site or the area, dive it with a local guide or someone who does, especially the first time.
- Use this workspace, its tools and its site files at your own risk. None of it replaces proper training, a dive buddy, and your own judgement in the water.

## What's here

- `CLAUDE.md` — the steering file tying it all together: units, conventions (local time, depth datum), and workspace-wide rules.
- `regions/` — one steering file plus a `sites/` folder per diving region; each site is a guidebook style description paired with a machine read current extract.
- `tools/` — one self-contained markdown doc per source or tool (what it's for, its caveats, its CLI if it has one), paired with a `.py` script for the sources that have one.
- `site_template.md` — the canonical structure every dive site file follows.
- `region_template.md` — the canonical structure every region steering file follows.
- `docs/` — a map of every dive site, colored by shore or boat access, with entry point pins for shore dives. Reads from `docs/js/data.js`.


`diver-profile.json`, `tool-config.json` and `plan_log.csv` hold personal data (identity, gear, dive history) and are gitignored. A `_template` version of each is included as a starting point for setting up your own.

## Regions currently covered

| Region | Description |
|---|---|
| [Bonaire](regions/bonaire/bonaire.md) | A Caribbean island in the Netherlands' ABC islands, ringed by a near-continuous fringing reef dived almost entirely from shore at marked yellow rocks, with wind driven rather than tidal current. |
| [Puget Sound](regions/puget-sound/puget-sound.md) | An estuary in western Washington, reaching the Pacific through the Strait of Juan de Fuca. Made up of four basins, the Main Basin, Whidbey Basin, Hood Canal and South Sound, separated by submarine sills. |
| [Strait of Juan de Fuca](regions/strait-of-juan-de-fuca/strait-of-juan-de-fuca.md) | The strait running between Vancouver Island, British Columbia, and the Olympic Peninsula, Washington, connecting the inland Salish Sea to the open Pacific. |
| [Washington State Lakes](regions/washington-state-lakes/washington-state-lakes.md) | Freshwater lakes scattered across Washington State, from glacial lakes in the Olympics and Cascades to lowland lakes near Puget Sound. |

## Tools

| Tool | Source | Does | Script |
|---|---|---|---|
| [NOAA CO-OPS currents](tools/noaa_current.md) | NOAA CO-OPS | Current predictions at a NOAA current station: slack, max flood/ebb, and diveable windows under a speed threshold, at a chosen depth bin. | `noaa_current.py` |
| [NOAA CO-OPS water levels](tools/noaa_tide.md) | NOAA CO-OPS | Tide height predictions at a NOAA tide station; converts an observed depth to depth below MLLW datum and back (`normalize` / `project`). | `noaa_tide.py` |
| [ENPAC15 (ADCIRC spatial tidal currents)](tools/adcirc_current.md) | ADCIRC / ENPAC15 | Extracts a site specific tidal current prediction from the ENPAC15 model (for sites with no nearby current station), then predicts slacks, peaks and diveable windows from that extract. | `adcirc_current.py` |
| [NCEI coastal DEM](tools/ncei_depth.md) | NOAA NCEI | Seabed depth at a coordinate, with conversion to depth below MLLW via NOAA VDatum. US only. | `ncei_depth.py` |
| [EMODnet Bathymetry](tools/emodnet_depth.md) | EMODnet + GEBCO | Seabed depth at a coordinate outside the US, from real survey soundings where EMODnet has coverage, falling back to the global GEBCO grid. | `emodnet_depth.py` |
| [NWS point forecast](tools/nws_forecast.md) | National Weather Service | Hourly wind speed and direction, sea state, air temperature and rain at a US coordinate, via a documented curl fetch of the point forecast. | none, documented curl fetch |
| [Open-Meteo wind](tools/open_meteo_wind.md) | Open-Meteo (ECMWF IFS + GFS) | Hourly wind speed, direction and gusts at any coordinate worldwide, for regions outside NWS coverage; ECMWF as the primary model, GFS as an independent cross-check. | `open_meteo_wind.py` |
| [PNW Diving](tools/pnwdiving_viz.md) | pnwdiving.com | Recent visibility reports by site, from the public summary table, cached locally. | `pnwdiving_viz.py` |
| [Subsurface dive log](tools/subsurface_log.md) | Subsurface logbook | Read-only access to a Subsurface dive log: list dives, show a dive's aggregates and notes, or pull its full depth/temperature/pressure profile. | `subsurface_log.py` |
| [DAN](tools/dan.md) | Divers Alert Network | Dive medicine, accident data and case narratives, incident summaries, and DAN's emergency and non-emergency contact numbers. | none, reference site |
| [ScubaBoard forum feeds](tools/scubaboard.md) | ScubaBoard | Recent threads by region or by topic, via each forum's own RSS feed. | `scubaboard.py` |
| [NW Dive Club](tools/nwdiveclub.md) | nwdiveclub.com | Community site write-ups (entry, what's worth seeing, hazards) and site recommendations, read via the Wayback Machine since the live site blocks direct fetches. | none, read via Wayback Machine |
| [The Perfect Dive](tools/theperfectdive.md) | theperfectdive.com (archived) | A defunct structured PNW dive site catalog (type, difficulty, entry, attractions) plus marine-life galleries, read from its 2022 Wayback snapshot. | none, read via Wayback Machine |

Tools with a script read parameters from their own subsection of `tool-config.json` (a missing key falls back to a built-in default) and print metric units in local time. NWS also reads a subsection of `tool-config.json` (the contact email for its required User-Agent) despite having no script. DAN, NW Dive Club and The Perfect Dive have no script or config section; they're read directly by page or feed.

## Platform

- Requires Python 3.9 or later (for `zoneinfo`).
- Developed and tested only on macOS.
- It should run on Linux with no changes, since every tool is pure Python standard library (`urllib`, `json`, `csv`, `xml.etree`, `zoneinfo`, no pip packages required) and none of the code paths are macOS specific.
- Windows is untested; `zoneinfo` there needs the `tzdata` package (`pip install tzdata`) since Windows has no system IANA time zone database.

## Things you can ask it

- "Plan a dive at [site] for Saturday morning around slack tide."
- "How long does the current window stay under 0.25 m/s at [site] next Tuesday?"
- "Write a new site file for [site name] near these coordinates."
- "What's viz and water temperature been like at [site] recently?"
- "Check the wind forecast for [beach] this weekend, is the entry going to be blown out?"
- "Pull my last few dives at [site] from the logbook and summarize gas consumption and conditions."
- "Based on my last dive there, how should I offset the current station's prediction for this site?"

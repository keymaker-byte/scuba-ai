# scuba-ai

Scuba AI is a collection of steering files, tools and dive site descriptions for scuba diving recreational planning within no-decompression limits. Point an LLM (e.g. Claude Code) at this workspace and it can plan dives, write up new dive sites, and answer questions using live NOAA current and tide predictions, tidal current models, bathymetry, wind forecasts and your own dive log, instead of guessing.

## Safety

This is a planning aid, not a dive plan by itself and not a substitute for training or judgement. It predicts; it does not guarantee.

- Dive only within the limits of your certification and training. Treat every prediction here as a starting point to verify against what you actually see, not a fact to trust blindly.
- Currents, tides and visibility are forecasts, built from models and stations some distance from the actual site. Conditions on the day can differ from any prediction, sometimes by a lot; confirm from the surface before committing, and abort if what you find does not match the plan.
- If you do not know a site or the area, dive it with a local guide or someone who does, especially the first time.
- Use this workspace, its tools and its site files at your own risk. None of it replaces proper training, a dive buddy, and your own judgement in the water.

## What's here

- `tools/` — scripts that pull live data: NOAA current and tide predictions, ADCIRC (ENPAC15) tidal current fields, NCEI bathymetry, NWS wind forecasts, and a reader for a Subsurface dive log.
- `regions/` — one steering file plus a `sites/` folder per diving region; each site is a guidebook style description paired with a machine read current extract.
- `site_template.md` — the canonical structure every dive site file follows.
- `region_template.md` — the canonical structure every region steering file follows.
- `CLAUDE.md` — the steering file tying it all together: units, conventions (local time, depth datum), and when to use each source.

`diver-profile.json`, `tool-config.json` and `plan_log.csv` hold personal data (identity, gear, dive history) and are gitignored. A `_template` version of each is included as a starting point for setting up your own.

## Regions currently covered

| Region | Description |
|---|---|
| [Puget Sound](regions/puget-sound/puget-sound.md) | An estuary in western Washington, reaching the Pacific through the Strait of Juan de Fuca. Made up of four basins, the Main Basin, Whidbey Basin, Hood Canal and South Sound, separated by submarine sills. |
| [Strait of Juan de Fuca](regions/strait-of-juan-de-fuca/strait-of-juan-de-fuca.md) | The strait running between Vancouver Island, British Columbia, and the Olympic Peninsula, Washington, connecting the inland Salish Sea to the open Pacific. |
| [Washington State Lakes](regions/washington-state-lakes/washington-state-lakes.md) | Freshwater lakes across Washington State. |

## Tools

| Script | Source | Does |
|---|---|---|
| `noaa_current.py` | NOAA CO-OPS | Current predictions at a NOAA current station: slack, max flood/ebb, and diveable windows under a speed threshold, at a chosen depth bin. |
| `noaa_tide.py` | NOAA CO-OPS | Tide height predictions at a NOAA tide station; converts an observed depth to depth below MLLW datum and back (`normalize` / `project`). |
| `adcirc_current.py` | ENPAC15 (ADCIRC) | Extracts a site specific tidal current prediction from the ENPAC15 model (for sites with no nearby current station), then predicts slacks, peaks and diveable windows from that extract. |
| `ncei_depth.py` | NCEI coastal DEM | Seabed depth at a coordinate, with conversion to depth below MLLW via NOAA VDatum. |
| `subsurface_log.py` | Subsurface logbook | Read-only access to a Subsurface dive log: list dives, show a dive's aggregates and notes, or pull its full depth/temperature/pressure profile. |
| `pnwdiving_viz.py` | pnwdiving.com | Recent visibility reports by site, from the public summary table, cached locally. |

NWS wind forecasts are fetched directly (no wrapper script). All tools read parameters from `tool-config.json` and print metric units in local time.

## Platform

- Requires Python 3.9 or later (for `zoneinfo`).
- Developed and tested only on macOS. It should run on Linux with no changes, since every tool is pure Python standard library (`urllib`, `json`, `csv`, `xml.etree`, `zoneinfo`, no pip packages required) and none of the code paths are macOS specific. Windows is untested; `zoneinfo` there needs the `tzdata` package (`pip install tzdata`) since Windows has no system IANA time zone database.

## Things you can ask it

- "Plan a dive at [site] for Saturday morning around slack tide."
- "How long does the current window stay under 0.25 m/s at [site] next Tuesday?"
- "Write a new site file for [site name] near these coordinates."
- "What's viz and water temperature been like at [site] recently?"
- "Check the wind forecast for [beach] this weekend, is the entry going to be blown out?"
- "Pull my last few dives at [site] from the logbook and summarize gas consumption and conditions."
- "Based on my last dive there, how should I offset the current station's prediction for this site?"

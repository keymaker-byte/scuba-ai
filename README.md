# scuba-ai

Scuba AI is a Claude Code workspace for scuba diving recreational planning within no-decompression limits: steering files that hold the facts for each region and site, skills that drive the research and writing, and tools that pull live data instead of guessing. Point Claude Code at it and it can plan a dive, write up a new region or site, and log what actually happened, using live current and tide predictions, tidal current models, bathymetry, wind forecasts and your own dive log along the way.

**[Dive Atlas](https://keymaker-byte.github.io/scuba-ai/)** — a live map of every dive site in this repo (no planning fuctionality directly in this map yet)

## Safety

This is a planning aid, not a dive plan by itself and not a substitute for training or judgement. It predicts; it does not guarantee.

- Dive only within the limits of your certification and training. Treat every prediction here as a starting point to verify against what you actually see, not a fact to trust blindly.
- Currents, tides and visibility are forecasts, built from models and stations some distance from the actual site. Conditions on the day can differ from any prediction, sometimes by a lot; confirm from the surface before committing, and abort if what you find does not match the plan.
- If you do not know a site or the area, dive it with a local guide or someone who does, especially the first time.
- Use this workspace, its tools and its site files at your own risk. None of it replaces proper training, a dive buddy, and your own judgement in the water.

## What's here

- `CLAUDE.md` — the steering file tying it all together: units, conventions (local time, depth datum), and workspace-wide rules.
- `regions/` — one steering file plus a `sites/` folder per diving region; each site is a guidebook style description paired with a machine read current extract.
- `tools/` — one self-contained markdown doc per tool (what it's for, its caveats, its CLI), paired with its `.py` script.
- `.claude/skills/` — Claude Code skills, self-contained workflows for a specific task, each triggered automatically when the request matches.
- `map.html` — a map of every dive site, colored by shore or boat access, with entry point pins for shore dives. Reads from `map/data.js`, which every site file has an entry in.
- `tool-config.json` - holds personal data (tool parameters) and is gitignored. `tool-config_template.json` is included as a starting point for setting up your own.

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
| [NWS point forecast](tools/nws_forecast.md) | National Weather Service | Hourly wind speed, direction and gusts, wave height, air temperature and rain at a US coordinate. | `nws_forecast.py` |
| [Open-Meteo wind](tools/open_meteo_wind.md) | Open-Meteo (ECMWF IFS + GFS) | Hourly wind speed, direction and gusts at any coordinate worldwide, for regions outside NWS coverage; ECMWF as the primary model, GFS as an independent cross-check. | `open_meteo_wind.py` |
| [PNW Diving](tools/pnwdiving_viz.md) | pnwdiving.com | Recent visibility reports by site, from the public summary table, cached locally. | `pnwdiving_viz.py` |
| [Subsurface dive log](tools/subsurface_log.md) | Subsurface logbook | Read-only access to a Subsurface dive log: list dives, show a dive's aggregates and notes, or pull its full depth/temperature/pressure profile. | `subsurface_log.py` |
| [Divers Atlas](tools/diversatlas.md) | diversatlas.org | Community dive site records worldwide (pin, depth, visibility, entry and parking notes, points of interest, safety notes), found by coordinate. | `diversatlas.py` |
| [Dive Atlas](tools/diveatlas.md) | diveatlas.org | Community dive site wiki: pin, depth range, skill level and a guidebook-style write-up (access, hazards, life, facilities), found by coordinate. | `diveatlas.py` |

Each tool reads parameters from its own subsection of `tool-config.json` (a missing key falls back to a built-in default) and prints metric units in local time.

## Skills

| Skill | Does |
|---|---|
| [create-dive-region](.claude/skills/create-dive-region/SKILL.md) | Writes a new region steering file: identifies the region's extent, runs the deep research pass (geography, conditions, which tools apply, the depth datum if any, how planning works there, dive shops, emergency chambers), and handles the regions table and map data bookkeeping. |
| [create-dive-site](.claude/skills/create-dive-site/SKILL.md) | Writes a new dive site file: gathers the required inputs (coordinates, boat or shore access, parking and entry points, the governing region), loads that region's conventions, verifies the coordinate against bathymetry and current model coverage, runs the research pass, and handles the sites table and map data bookkeeping. |
| [create-dive-plan](.claude/skills/create-dive-plan/SKILL.md) | Plans a dive at a known site and date: pulls current, tide and wind at both entry and exit, orders the route so the return never fights the current, applies the NDL and EAN32 conventions, logs the predicted profile before the dive, and fills in what actually happened afterward. |

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

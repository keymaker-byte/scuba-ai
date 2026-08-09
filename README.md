# scuba-ai

Scuba AI is a collection of steering files, tools and dive site descriptions for scuba diving recreational planning within no-decompression limits. Point an LLM (e.g. Claude Code) at this workspace and it can plan dives, write up new dive sites, and answer questions using live NOAA current and tide predictions, tidal current models, bathymetry, wind forecasts and your own dive log, instead of guessing.

## What's here

- `tools/` — scripts that pull live data: NOAA current and tide predictions, ADCIRC (ENPAC15) tidal current fields, NCEI bathymetry, NWS wind forecasts, and a reader for a Subsurface dive log.
- `regions/` — one steering file plus a `sites/` folder per diving region; each site is a guidebook style description paired with a machine read current extract.
- `plan_log.csv` — a log of dive plans versus what was actually observed, used to calibrate current and tide offsets over time.
- `site_template.md` — the template every site file follows.
- `CLAUDE.md` — the steering file tying it all together: units, conventions (local time, depth datum), and when to use each source.

`diver-profile.json`, `tool-config.json` and `plan_log.csv` hold personal data (identity, gear, dive history) and are gitignored. A `_template` version of each is included as a starting point for setting up your own.

## Things you can ask it

- "Plan a dive at [site] for Saturday morning around slack tide."
- "How long does the current window stay under 0.25 m/s at [site] next Tuesday?"
- "Write a new site file for [site name] near these coordinates."
- "What's viz and water temperature been like at [site] recently?"
- "Check the wind forecast for [beach] this weekend, is the entry going to be blown out?"
- "Pull my last few dives at [site] from the logbook and summarize gas consumption and conditions."
- "Based on my last dive there, how should I offset the current station's prediction for this site?"

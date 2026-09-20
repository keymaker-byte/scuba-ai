# Subsurface dive log

Subsurface's saved logbook, read through a read-only tool: Subsurface owns the file, and this tool never writes it. Its path is set in `subsurface_log.file` in `tool-config.json`.

What any dive log is for: user-specific experience, a site's depth range, gas consumption, water temperature, viz by season, hazards hit, and calibrating current offsets against dives actually done. Two levels live in it. The per-dive aggregates (max depth, temperature, gas, visibility, current, the site) answer the daily questions; the full profile (depth and the rest, sampled every few seconds) places the deepest point, the turn and the ascent on the clock, which is what an offset calibration or an ascent-behaviour read needs. Read the free-text notes: notes are where *"anxiety again… down current"* lives, the thing that could actually hurt you, and the hazards are in the prose. Weight the subjective fields carefully; a visibility or current value is weak on its own, trustworthy only in aggregate. Times are local, so a sample's time is seconds into the dive and its clock time is the dive start plus that offset. The logbook is a snapshot refreshed after diving, so recent dives, or notes added since, are missing until the next refresh, never wrong, and it is large, so read it through this tool rather than opening it whole.

- **Format.** Subsurface native XML (`program='subsurface'`), also written as `.ssrf`. Every value carries its unit inline (`depth='23.1 m'`, `pressure0='219.67 bar'`, `size='9.67 l'`), so the tool converts off the suffix and always presents metric, whatever the app's display units are.
- **Condition ratings.** Come as 1 to 5: visibility (1 poor to 5 excellent), current (1 strong to 5 slack), and wavesize, surge and chill (1 severe to 5 calm/none).
- **Sites are normalized.** The name holds the site alone, the location (e.g. "Howe Sound", "Quintay") lives in the site's notes, and country, state and ocean live in its georeference entries. The tool reads all of these.
- **Read-only, but shared.** Subsurface rewrites the file on save, so keep the app closed when anything writes to it. This tool only ever reads.

## `tools/subsurface_log.py`

Streams the logbook, in metric and local time, without modifying it.

```sh
python3 tools/subsurface_log.py list [--site S] [--since D] [--limit N]   # recent dives, one line each
python3 tools/subsurface_log.py show SELECTOR                             # aggregates, ratings, marks, notes
python3 tools/subsurface_log.py profile SELECTOR [--csv]                  # depth, temperature, pressure per sample
```

`SELECTOR` is a dive number, or a substring of the date, site name, site region (location, state, country, ocean) or tags; `list --site` matches name and region too. `show` gives the aggregates plus the computed SAC, OTU and CNS, the condition ratings (visibility, current, wavesize, surge, chill), the buddy and divemaster, the site's region, gas changes on multi-cylinder dives, any in-dive marks, and the notes; `profile` is the per-sample series, each sample stamped with its clock time.

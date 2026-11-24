# Puget Sound Planning Conventions

These conventions apply to every dive planned in this region.

Ordered by what actually kills a dive plan in the Sound:

1. **Current** (primary). Nearly everything is a slack-tide dive; the window, not the site, is the plan.
   - **Tool.** `current.md`, the day's slacks, sets and diveable windows at the bottom, with the fastest water above for the descent and ascent, read by passing the site's `sites/<slug>.json` as `--file`. The tool applies the site's observed offset where one is established. A current prediction sets the slack; a tide station never does.
2. **Wind** (secondary). Wind decides whether the entry is diveable at all: chop on the entry, surf on the beach, a surface swim into a fetch.
   - **Tool.** `nws_forecast.md`, the wind call at the entry and the exit time against the site's Wind section sectors.
3. **Viz** (informational). Won't stop the dive, but sets expectations and gear (torch, reel).
   - **Tool.** `pnwdiving_viz.md`, the site's recent reports, weighted by recency.

Alongside the conditions, every plan carries:

- **Depth.** `noaa_tide.md` at the site's tide station, turning the site's MLLW depths into depth below the surface across the dive.
- **Past dives.** `subsurface_log.md`, the site's earlier dives: notes, hazards hit, and any timed slacks.

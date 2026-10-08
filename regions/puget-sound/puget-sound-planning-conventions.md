# Puget Sound Planning Conventions

These conventions apply to every dive planned in this region.

Ordered by what actually kills a dive plan in the Sound:

1. **Current** (primary). Nearly everything is a slack-tide dive; the window, not the site, is the plan.
   - **Tool.** `noaa_current.md`, the slack and diveable windows at the site's governing station and recommended bin, with the site's observed offset applied where established. A current station sets the slack; a tide station never does.
   - **Model.** `adcirc_current.md`, the day's slack and set from the site's extract. The Sound is four basins separated by sills that locally accelerate and redirect the flow, so a station some distance away does not always represent the site's own water, even a well proven one.
   - **Legacy.** `noaa_legacy_current.md`, where the site file carries a legacy correction: the legacy reference's slack on the day, plus the correction.
   - **Window.** Every estimate side by side: the station's slack, with the observed offset where established; the model's; the legacy's. The window is their overlap, padded by how far apart they fall on the day, and estimates more than 10 minutes apart are flagged in the plan.
2. **Wind** (secondary). Wind decides whether the entry is diveable at all: chop on the entry, surf on the beach, a surface swim into a fetch.
   - **Tool.** `nws_forecast.md`, the wind call at the entry and the exit time against the site's Wind section sectors.
3. **Viz** (informational). Won't stop the dive, but sets expectations and gear (torch, reel).
   - **Tool.** `pnwdiving_viz.md`, the site's recent reports, weighted by recency.

Alongside the conditions, every plan carries:

- **Depth.** `noaa_tide.md` at the site's tide station, turning the site's MLLW depths into depth below the surface across the dive.
- **Past dives.** `subsurface_log.md`, the site's earlier dives: notes, hazards hit, and any timed slacks.

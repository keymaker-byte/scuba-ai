# Strait of Juan de Fuca Planning Conventions

These conventions apply to every dive planned in this region.

This is open, oceanic water. The strait connects directly to the Pacific with nothing to break wind, swell or fog along most of its length.

Ordered by what actually kills a dive plan in the strait:

1. **Wind and swell** (primary). The strait is the only inland Washington waterway with a direct, unbroken fetch to the open Pacific, over 100 km along its own axis. Strong westerlies accelerate down that fetch, routinely reaching gale force with higher gusts, and genuine Pacific swell can run the length of the strait to break on shore at its eastern end, producing the largest wave heights recorded on any inland Washington water. Fog is also common, especially toward Cape Flattery, and is itself a go, no go factor for any boat site. Summer westerlies build through the afternoon, so the exit time is usually the reading that decides.
   - **Tool.** `nws_forecast.md`, the wind call at the entry and the exit time against the site's Wind section sectors.
   - **Swell.** Pacific swell runs the length of the strait under a light breeze, and a forecast that reads calm at Sekiu can still find real swell at Salt Creek off ocean weather two or three days old. A point forecast along this shore reads a land-side grid cell, with its wave height at 0 m whatever the sea; swell is judged from the NWS coastal waters forecast for the strait, recent local reports and the beach itself.
2. **Current** (secondary). Nearly every shore site here is a slack-tide dive, and the window, not the site, is the plan. Current in the open channel runs strong, up to 1 to 1.5 m/s, though many shore sites sit in the lee of a point or bluff and see much less.
   - **Tool.** `noaa_current.md`, the slack and diveable windows at the site's governing station and recommended bin, with the site's observed offset applied where established.
   - **Model.** `adcirc_current.md`, the day's slack and set from the site's extract at the bottom of the water column, read by passing the site's `sites/<slug>.json` as `--file`. The strait carries a real two-layer estuarine circulation, fresher water flowing out toward the Pacific near the surface and saltier water flowing in underneath, so the set at working depth can run opposite to the surface. Live current stations thin out west of Port Angeles, so the model carries more weight the further west the site sits.
   - **Legacy.** Where the site file carries a legacy correction, the legacy reference's slack on the day, plus the correction: `noaa_legacy_current.md` for a retired NOAA reference, `chs_current.md` for a Canadian one.
   - **Window.** Every estimate side by side: the station's slack, with the observed offset where established; the model's; the legacy's. The window is their overlap, padded by how far apart they fall on the day, and estimates more than 10 minutes apart are flagged in the plan.
3. **Viz** (informational). Won't stop the dive, but sets expectations and gear (torch, reel).
   - **Tool.** `pnwdiving_viz.md`, the site's recent reports, weighted by recency.

Alongside the conditions, every plan carries:

- **Depth.** `noaa_tide.md` at the site's tide station, turning the site's MLLW depths into depth below the surface across the dive.
- **Past dives.** `subsurface_log.md`, the site's earlier dives: notes, hazards hit, and any timed slacks.

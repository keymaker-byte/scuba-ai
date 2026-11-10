# San Juan Islands Planning Conventions

These conventions apply to every dive planned in this region.

The islands sit at the junction of three open straits, with the exchange between them forced through a web of channels and passes. Ordered by what actually kills a dive plan here:

1. **Current** (primary). Nearly everything is a slack-tide dive, and the window, not the site, is the plan. The tide is strongly mixed, so the windows are uneven: the weak exchange gives long, easy slacks, while the slacks either side of a big spring ebb are short and turn hard, with the main passes running past 2 m/s within the hour.
   - **Station Tool.** `noaa_current.md`, the slack and diveable windows at the site's governing station and recommended bin, with the site's observed offset applied where established. A current station sets the slack; a tide station never does.
   - **Spatial Model Tool.** `adcirc_current.md`, the day's slack and set from the site's extract, read by passing the site's `sites/<slug>.json` as `--file`. Points, passes and channel junctions bend and accelerate the flow, so a station across a channel does not always represent the site's own water.
   - **Legacy Station Tool.** `noaa_legacy_current.md`, where the site file carries a legacy correction: the legacy reference's slack on the day, plus the correction.
   - **Current Reconciliation.** To reconcile the slack predictions, put every source estimate side by side: the station, spatial model and legacy station (apply offsets where established). Then follow these steps: 1) Calculate their overlapped time window. 2) If 2 or more sources match within a 30 min range calculate a mid point. Always present all sources and the reconciled values.
   - **Station Weight.** No established offset: the governing station is a data point only, shown but left out of the overlap and mid point. Sole source: it sets the window, flagged as un-offset. The spatial model and legacy station always count in the overlap and mid point.
   - **Exchange.** The plan names which exchange the window sits on, weak or strong, with the peak speeds either side, since a window before a large ebb closes far faster than one on the weak exchange.
2. **Wind and swell** (secondary). Wind decides whether the entry is diveable at all: chop on the entry, surf on a cobble beach, a surface swim into a fetch. Summer westerlies run in down the Strait of Juan de Fuca and build through the afternoon, so the exit reading is usually the one that decides; winter brings south to southeast gales, and cold northeast outflow down the Fraser Valley reaches the northern islands.
   - **Tool.** `nws_forecast.md`, the wind call at the entry and the exit time against the site's Wind section sectors.
   - **Swell.** The south shores of San Juan and Lopez face the open Strait of Juan de Fuca, and Pacific swell runs up it to break on their beaches and the southern Haro Strait shore under a light local breeze, from distant ocean weather. A point forecast along these shores often reads a land-side grid cell with its wave height at 0 m whatever the sea, so for a site on these shores the swell is judged from the coastal waters forecast below, recent local reports, and the beach itself. Large ships in Haro Strait raise short-lived rollers on the shore as well.
   - **Source.** The NWS Seattle coastal waters forecast, read for its zones for the eastern Strait of Juan de Fuca and the northern inland waters including the San Juan Islands: wind and wave height over open water. No tool reads it; it is checked by hand.
3. **Viz** (informational). Won't stop the dive, but sets expectations and gear (torch, reel).
   - **Tool.** `pnwdiving_viz.md`, the site's recent reports, weighted by recency.

Alongside the conditions, every plan carries:

- **Depth.** `noaa_tide.md` at the site's tide station, turning the site's MLLW depths into depth below the surface across the dive.
- **Past dives.** `subsurface_log.md`, the site's earlier dives: notes, hazards hit, and any timed slacks.
- **Ferry and gas.** An island dive runs on the Washington State Ferries schedule out of Anacortes, and the islands have no public air fill: the plan carries the sailings there and back, and every cylinder the day needs, filled on the mainland.

Local rules that bind every dive here:

- **National wildlife refuge.** Every island and rock of the San Juan Islands National Wildlife Refuge is closed to landing, and the water within about 180 m of each is closed to watercraft. The exceptions are the public use areas on Matia and Turn Islands, where landing is allowed and the buffer lifts along those shores. A diver may swim near a refuge rock from shore; a boat stays outside the buffer, and no one climbs out on the rock.
- **Killer whales.** Every vessel, kayaks and paddleboards included, stays about 900 m from Southern Resident killer whales year round under state law, and about 180 m from all other killer whales under federal law. A dive boat that finds orcas close by stops, disengages and lets them pass before moving or putting divers in.
- **Marine preserves.** The WDFW marine preserves in the islands, among them False Bay and Argyle Lagoon on San Juan Island, the Friday Harbor preserve, Parks Bay on Shaw Island, and the water around Yellow Island and its neighbouring islet in the Wasp Islands, are closed to harvest of fish and shellfish. Check the WDFW marine protected area map before taking anything anywhere in the islands.
- **Parking passes.** Washington State Parks sites need a Discover Pass, $10 for a day or $45 for a year. San Juan County parks and the City of Anacortes set their own parking rules, and each site file states its own park's rule.

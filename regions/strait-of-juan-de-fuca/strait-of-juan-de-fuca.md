# Strait of Juan de Fuca Dive Planning

## The region

The Strait of Juan de Fuca runs about 154 km east to west between Vancouver Island, British Columbia, and the Olympic Peninsula, Washington, and is the primary connection between the inland Salish Sea and the open Pacific. It widens from about 19 km near its eastern end to about 40 km at its Pacific mouth. Mid channel depth runs from about 275 m near the Pacific entrance to about 90 m at the eastern end, averaging around 100 m: a deep, open channel, not a set of shallow, constricted basins.

This folder covers the US shore, from the Dungeness spit to Cape Flattery, along the Olympic Peninsula.

| Reach | Where |
|---|---|
| **Eastern approaches** | Dungeness spit to Ediz Hook and Port Angeles harbor |
| **Central bluffs** | Freshwater Bay to Crescent Bay, Salt Creek and Tongue Point, steep rock bluffs broken by pocket beaches |
| **Western strait** | Pillar Point, Clallam Bay, Sekiu, and Neah Bay |
| **The mouth** | Cape Flattery, Tatoosh Island and Duncan Rock, where the strait opens fully to the Pacific; boat access only |

### Boundaries

- **Eastern boundary.** Admiralty Inlet, roughly the line between Point Wilson and Partridge Point.
- **Western boundary.** Cape Flattery and Tatoosh Island, where the strait opens fully to the Pacific. Sites here and just offshore, Duncan Rock among them, are dived as an extension of strait diving, out of the same towns and off the same current logic.

### The western reach and the mouth

Sekiu, Neah Bay, Cape Flattery, Tatoosh Island and Duncan Rock are a different tier of diving from the rest of this folder. Duncan Rock in particular is regarded as one of the best sites on the peninsula and also one of the most dangerous: strong current, surge, depth and fog together mean it is genuinely diveable only a handful of days a year, boat access only, with a live-boat procedure. The same caution applies in a milder form to Tatoosh Island and the other boat sites out toward the cape. Treat any site in this reach as requiring its own careful go, no go call on the day, not just a slack time pulled off a station, and remember the point above: a bad outcome out here is a long way from help.

Both the ADCIRC mesh and the high-resolution coastal bathymetry thin out right at this corner: a point off Tatoosh Island lands close enough to the mesh edge to need caution on timing, and the fine-grained depth data gives out entirely around Tatoosh Island and Duncan Rock, falling back to a coarse global grid. Treat current predictions and quoted depths out here as a starting point to verify on the day, not a settled number.

### Shipping

A formal Traffic Separation Scheme and Vessel Traffic Service cover the length of the strait, one of the busiest approaches on the US west coast for tankers, container ships and cruise traffic. The lanes run mid channel; boat sites well offshore, Duncan Rock and the wreck of the Diamond Knot among them, sit close enough to that traffic to warrant a real look at vessel positions before the dive, not just a glance at the chart. Shore sites are generally well clear of the lanes themselves, but Ediz Hook and the Port Angeles approach see steady harbor and ferry traffic worth checking before an entry near the harbor mouth.

## Conditions

- **Water temperature.** Roughly 6 to 9 C at depth, reflecting the strait's direct connection to the ocean and periodic coastal upwelling. The surface layer warms into the low teens late in summer, less than a sheltered bay would over the same weeks. Drysuit year round.
- **Visibility.** Ranges widely, roughly 1.5 to 15 m, and swings hard with plankton blooms. Direct oceanic exchange tends to help it, water moving through rather than sitting behind a sill, but a bloom can still shut a site down for weeks. Best conditions tend to run late summer into fall. Recent reports beat any prediction.
- **Character.** Cold, oceanic and tidal, with real ocean swell and sustained wind layered on top of the tidal current. The western reach is remote: fewer facilities, longer drives, and a long response time to a chamber or hospital if something goes wrong. Neah Bay is about four and a half to five hours from Seattle by road.

## Tools

The following tools should be used in this region:

- noaa_current.md
- noaa_tide.md
- adcirc_current.md
- ncei_depth.md
- shore_exposure.md
- nws_forecast.md
- pnwdiving_viz.md
- subsurface_log.md
- scubaboard.md
- diversatlas.md
- diveatlas.md

## Web Sources

The following web sources should be used in this region:

- **[DAN (Divers Alert Network)](https://dan.org).** Dive medicine, accident data and case narratives (the Annual Diving Report, Incident Insights), the standing source for gear, procedure and debrief questions. Emergency line +1-919-684-9111, 24/7, collect calls accepted worldwide.
- **[NW Dive Club](https://nwdiveclub.com/viewforum.php?f=6).** Community write-ups of how a site is dived: the entry, what's worth seeing, what to expect. Read it through the Wayback Machine (`https://archive.org/wayback/available?url=<page>`, then `curl --compressed` the snapshot), and confirm the snapshot holds the full thread.
- **[The Perfect Dive](https://web.archive.org/web/20220413053905/http://theperfectdive.com/DEF-SiteList.asp).** A defunct catalog of Pacific Northwest sites, frozen around 2022: dive type, difficulty, entry and attractions per site, including several lesser-known sites. Read this pinned snapshot with `curl --compressed`, and verify access, fees and closures against a recent source.

## Site file conventions

These conventions apply to every site file written in this region.

Every site file carries a tide station in the same body of water, and a companion `<slug>.json`, an ENPAC15 current extract produced by `tools/adcirc_current.py`. Its current station comes from the current method below.

Depth here is normalized to MLLW, mean lower low water, the datum NOAA's charts and its tide and current predictions use for this coast. The seabed is fixed, the surface is not, so a raw depth reading is only true at the tide it was taken; every depth worth keeping is converted to depth below MLLW and never mixed with another datum. Tide height is signed, negative on a minus tide, so subtracting a negative tide height makes the datum depth the deeper number:

```
depth below MLLW datum  =  observed depth (computer)  -  tide height at that moment
depth below surface     =  datum depth                +  predicted tide height
```

Get a site's median daily tidal range, its largest daily range, and its high/low span across the year by running `noaa_tide.py range STATION --year Y`, which pulls every high and low for the year in one call and reports exactly those three figures.

Current here is tidal:

- **Governing station.** The live NOAA current station (`noaa_current.py stations --near`) whose slack timing and set direction best match the site's own ENPAC15 extract over a span of weeks. It is a PUG-prefixed survey station: a PCT-prefixed station (Predicted Current Tables) publishes no depth bins, so pick the nearest PUG-prefixed one instead.
- **Bin.** The published bin (`noaa_current.py bins`) nearest the dive area's seabed depth.
- **Time offset.** An offset is meaningful only against the station it was derived from, so a legacy correction stated against a retired station is re-derived for the governing station, never carried over. Establish it from timed observations, the station-to-ADCIRC reconciliation, or a source that names the governing station. Compute the station's prediction for each observed day, and state in chat which observations the offset rests on and which slack each one supports. Where none of these gives one, the row is written as not established.
- **Axes and peak speeds.** The governing station's own, at that bin, read from `noaa_current.py predict`. Where the station and the ENPAC15 extract disagree on axis, not just timing, the table carries the station's axis, since that is what the station publishes, and the site's real local behaviour, from the ADCIRC extract or a shore-parallel set the station's open-water position wouldn't show, goes in the prose underneath.

## Planning conventions

These conventions apply to every dive planned in this region.

This is open, oceanic water, not a sheltered inland waterway. The strait connects directly to the Pacific with nothing to break wind, swell or fog along most of its length.

Ordered by what actually kills a dive plan in the strait:

1. **Wind and swell** (primary). The strait is the only inland Washington waterway with a direct, unbroken fetch to the open Pacific, over 100 km along its own axis. Strong westerlies accelerate down that fetch, routinely reaching gale force with higher gusts, and genuine Pacific swell can run the length of the strait to break on shore at its eastern end, producing the largest wave heights recorded on any inland Washington water. Fog is also common, especially toward Cape Flattery, and is itself a go, no go factor for any boat site. The wind tool here is `nws_forecast.py`; summer westerlies build through the afternoon, so the exit time is usually the reading that decides.
   - **Swell.** Pacific swell runs the length of the strait under a light breeze, and a forecast that reads calm at Sekiu can still find real swell at Salt Creek off ocean weather two or three days old. A point forecast along this shore reads a land-side grid cell, with its wave height at 0 m whatever the sea; swell is judged from the NWS coastal waters forecast for the strait, recent local reports and the beach itself.
2. **Current** (secondary). Nearly every shore site here is a slack-tide dive: take the slack from the site's governing station with its offset applied, and treat the window, not the site, as the plan. Current in the open channel runs strong, up to 1 to 1.5 m/s, though many shore sites sit in the lee of a point or bluff and see much less. Cross-check the day's slack and set direction against the site's ENPAC15 extract at the bottom of the water column (`tools/adcirc_current.py predict --position bottom`) before calling a window, and reconcile the two: the strait carries a real two-layer estuarine circulation, fresher water flowing out toward the Pacific near the surface and saltier water flowing in underneath, so the set at working depth can run opposite to the surface. Live current stations thin out west of Port Angeles, 20 to 30 km from Sekiu or Neah Bay, so the cross-check carries more weight the further west the site sits.
3. **Viz** (informational). Won't stop the dive, but sets expectations and gear (torch, reel).

## Sites currently covered

| Site | Description |
|---|---|
| [Ediz Hook (Inner Harbor)](sites/ediz-hook.md) | Inner harbor shore of the Port Angeles spit, a colorful shallow shelf of sand and scattered rock with lingcod, crabs, nudibranchs and lost golf balls, giving way past 18 m to a slope of stacked, decaying logs where octopus den. |
| [Freshwater Bay (County Park)](sites/freshwater-bay.md) | County park west of Port Angeles, a long crossing over sand and eelgrass along the kelp-covered lee of Observatory Point Reef to Bachelor Rock, whose crevices hold octopus, wolf eels and Puget Sound king crab and whose outer wall drops to about 18 m. |
| [North Beach](sites/north-beach.md) | Bull kelp bed along the Port Townsend shore between McCurdy Point and Point Wilson at the mouth of Admiralty Inlet, offshore rocks scattered through the sand and kelp, with sand lance schools and harbor seals and river otters in the kelp. |
| [One Mile Beach](sites/one-mile-beach.md) | Driftwood-backed beach a mile west of the Sekiu boat launch, kelp-wrapped rock formations on a gentle sandy slope cut by channels and small tunnels, with wolf eels and octopus in the ledge holes and clouds of mysid shrimp in the kelp. |
| [Pinnacle Rock](sites/pinnacle-rock.md) | Cobble beach between Sekiu and Neah Bay named for a tall, tree-topped rock pinnacle in the intertidal, kelp-wrapped rocks over sand and cobble with channels wide enough to work, black rockfish in the canopy and grey whales occasionally in the cove. |
| [Salt Creek (Tongue Point)](sites/salt-creek.md) | Tongue Point marine sanctuary west of Port Angeles, a basalt reef of shelves, channels and boulders under thick summer kelp, carpeted in urchins, sponges, hydrocoral and fish eating anemones, with a rare rock greenling in the surf grass shallows. |
| [Sekiu Jetty](sites/sekiu.md) | Rock field beside the Sekiu jetty on Clallam Bay, leaning formations forming alleys under kelp, nearly every surface crowded with invertebrates and octopus middens at den entrances, with starry flounder and northern abalone on the sand and eelgrass beyond. |

## Dive shops and air fills

Tank fill spots for this folder's sites.

- **Curley's Resort and Dive Center.** 291 Front St, Sekiu, WA 98381. (360) 963-2281. curleysresort.com. Air fills to 241 bar; hours run shorter outside peak season.
- **Octopus Gardens Diving.** 2410 Washington St, Port Townsend, WA 98368. (360) 385-3483. octopusgardensdiving.com. Air and nitrox.
- **Dano's Dive Service.** Home based fill station near Ediz Hook, Port Angeles. Air only, no nitrox, arranged by phone in advance at (360) 461-9843; current hydro required. No public address or website found.
- **Scuba Supplies Co.** 120 E Front St, Port Angeles, WA 98362. (360) 457-3190. Air and nitrox fills, run out of the back of a bike and kayak shop. Not confirmed still in business; call ahead before relying on it.
- **Snow Creek Resort.** 691 WA-112, Neah Bay, WA 98357. (800) 883-1464. A campground and general store with an air compressor, about 2 miles east of Neah Bay, closer to Neah Bay and Cape Flattery than Curley's in Sekiu.

## Emergency

Local emergency number: 911. Call EMS first; call DAN once the diver is stabilized and transport is underway.

- **Virginia Mason Franciscan Health, Center for Hyperbaric Medicine, Seattle.** 1100 9th Ave, Seattle, WA 98101. (206) 583-6543. The only multiplace recompression chamber in Western Washington and the referral chamber for this region too; no closer chamber operates anywhere on the strait. About 2 to 2.5 hours from Port Angeles via the Kingston-Edmonds ferry, and about 4.5 to 5 hours by road from Neah Bay, the region's most remote dive town. Weigh that distance into the go, no go call on any dive out toward the western reach, where the section above already flags the risk as genuinely higher.


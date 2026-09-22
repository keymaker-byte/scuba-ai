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
- nws_forecast.md
- pnwdiving_viz.md
- subsurface_log.md
- dan.md
- scubaboard.md
- nwdiveclub.md
- theperfectdive.md

## Conventions

Every site file carries two stations: a governing current station (with its bin and offset) and a tide station in the same body of water. Each site also carries a companion `<slug>.json`, an ENPAC15 current extract produced by `tools/adcirc_current.py`.

Depth here is normalized to MLLW, mean lower low water, the datum NOAA's charts and its tide and current predictions use for this coast. The seabed is fixed, the surface is not, so a raw depth reading is only true at the tide it was taken; every depth worth keeping is converted to depth below MLLW and never mixed with another datum. Tide height is signed, negative on a minus tide, so subtracting a negative tide height makes the datum depth the deeper number:

```
depth below MLLW datum  =  observed depth (computer)  -  tide height at that moment
depth below surface     =  datum depth                +  predicted tide height
```

Get a site's median daily tidal range, its largest daily range, and its high/low span across the year by running `noaa_tide.py range STATION --year Y`, which pulls every high and low for the year in one call and reports exactly those three figures.

## How planning works here

This is open, oceanic water, not a sheltered inland waterway. The strait connects directly to the Pacific with nothing to break wind, swell or fog along most of its length.

Ordered by what actually kills a dive plan in the strait:

1. **Wind and swell** (primary). The strait is the only inland Washington waterway with a direct, unbroken fetch to the open Pacific, over 100 km along its own axis. Strong westerlies accelerate down that fetch, routinely reaching gale force with higher gusts, and genuine Pacific swell can run the length of the strait to break on shore at its eastern end, producing the largest wave heights recorded on any inland Washington water. A forecast that reads calm at Sekiu can still be running real swell at Salt Creek off ocean weather two or three days old; check a current marine forecast and recent local reports, not just the day's local wind at the entry. Fog is also common, especially toward Cape Flattery, and is itself a go, no go factor for any boat site.
2. **Current** (secondary). Nearly every shore site here is a slack-tide dive: get the slack time from a governing NOAA current station, apply the site's own offset and correction, and treat the window, not the site, as the plan. Current in the open channel runs strong, up to 1 to 1.5 m/s, though many shore sites sit in the lee of a point or bluff and see much less. Always cross-check the station's slack and set direction against a depth-scaled ADCIRC prediction (`tools/adcirc_current.py predict --depth`) before calling a window, and reconcile the two rather than trusting the station alone: the strait carries a real two-layer estuarine circulation, fresher water flowing out toward the Pacific near the surface, saltier water flowing in underneath, so current direction can genuinely differ between the surface and a working dive depth, not just fall off in speed with depth the way a simple boundary layer would, and a station's own published bin is usually a shallow one, not the working depth. Live current stations thin out west of Port Angeles, the nearest one to Sekiu or Neah Bay sits 20 to 30 km off, so a governing-station offset out there carries more uncertainty by default than a station a few kilometres from the site, and the ADCIRC cross-check matters more the further west the site sits. A few nearby stations (PCT1371 at Port Angeles among them) are Predicted Current Tables rather than survey stations and don't publish the depth bins a station offset needs; pick the nearest PUG-prefixed survey station instead. When the station and the ADCIRC cross-check disagree on axis rather than just timing, a site file's Current table still carries the governing station's own axis, since that is what the station publishes; the site's real local behavior goes in the prose underneath, not the table.
3. **Viz** (informational). Won't stop the dive, but sets expectations and gear (torch, reel).

## Sites currently covered

| Site | Description |
|---|---|
| [Ediz Hook (Inner Harbor)](sites/ediz-hook.md) | Easy, current free harbor side shelf off the Port Angeles spit that drops into an open slope of sunken log debris past recreational depths. |
| [Freshwater Bay (County Park)](sites/freshwater-bay.md) | Long surface crossing of a shallow bay to Bachelor Rock's sheltered inside wall; the swim itself, plus boat traffic and open water surge past the reef, is the hazard. |
| [North Beach](sites/north-beach.md) | Bull kelp bed along a sandy, clay bottom at the mouth of Admiralty Inlet, with current weak inside the kelp but building fast past its outer edge. |
| [One Mile Beach](sites/one-mile-beach.md) | Sandy, gravel slope near Sekiu to a rock and kelp ledge, exposed to open water with a direct line to the Pacific once past the kelp's shelter. |
| [Pinnacle Rock](sites/pinnacle-rock.md) | Remote sand and cobblestone slope between Sekiu and Neah Bay, marked by an intertidal rock pinnacle, exposed to strong current and surge with nothing to break either. |
| [Salt Creek (Tongue Point)](sites/salt-creek.md) | Advanced dive inside a marine sanctuary on a basalt reef of shelves and boulders under thick kelp; waves and surge at the rocky entry, not current, are the headline hazard. |
| [Sekiu Jetty](sites/sekiu.md) | Kelp wrapped rock field on sand and eelgrass by the Sekiu marina, densely covered in invertebrates; surge, current and thick kelp are the hazards in open water. |

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


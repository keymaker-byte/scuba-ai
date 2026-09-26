# Puget Sound Dive Planning

## The region

Puget Sound is an estuary in western Washington, running about 160 km from Deception Pass in the north to Olympia in the south. It reaches the Pacific through the Strait of Juan de Fuca by three entrances: Admiralty Inlet, which carries most of the exchange, plus Deception Pass and the Swinomish Channel. Surface area is about 2,640 km², volume about 110 km³, mean depth about 137 m, and the deepest water about 283 m off Jefferson Point. Roughly 2,140 km of shoreline make it a shore-diving region.

It is one system of four deep basins separated by sills, submarine ridges that throttle the exchange between them:

| Basin | Where |
|---|---|
| **Main Basin** | Admiralty Inlet and the Central Basin, Whidbey Island down to the Tacoma Narrows |
| **Whidbey Basin** | East of Whidbey Island, taking the Skagit, Stillaguamish and Snohomish |
| **Hood Canal** | West of the Kitsap Peninsula |
| **South Sound** | South of the Tacoma Narrows |

The sills matter to planning because they are where the water accelerates. The three that count are Admiralty Inlet (about 64 m), the Hood Canal entrance (about 53 m) and the Tacoma Narrows (about 44 m). Tidal range grows as you go south, about 2.5 m at Port Townsend and about 4.4 m at Olympia, so the depth convention matters more the further south you dive.

### Boundaries

- **Strict definition** (USGS): the water south of the three Strait entrances. That takes in Hood Canal, Admiralty Inlet and Possession Sound, and leaves out Bellingham Bay and the San Juan Islands.
- **This folder is broader.** Some sites sit north of Deception Pass, on Rosario Strait and the approaches to the San Juans, which are Salish Sea rather than Puget Sound proper. They are kept here because they are dived the same way, off the same tools and conventions. A site is located by its file's coordinates and stations, not by the folder name.
- **Hood Canal is inside the region.** It is one of the four basins, not a neighbouring body of water, but it behaves differently enough to carry its own section in this file.
- **Salish Sea** is the collective name for Puget Sound, the Strait of Juan de Fuca and the Strait of Georgia together, and the right word for water north or west of the Sound.

### Hood Canal

A fjord, not a sound: a narrow trench separating the Kitsap Peninsula from the Olympic Peninsula, entered between Foulweather Bluff and Tala Point south of Admiralty Inlet. It runs about 80 km southwest to Union, turns sharply northeast at the Great Bend, and continues about 24 km to Belfair, ending in the shallow tidelands of Lynch Cove. Average width is about 2.4 km, mean depth about 54 m, maximum depth about 180 m. Dabob Bay is the largest bay off it, and the Skokomish, Hamma Hamma, Duckabush, Dosewallips and Big Quilcene come in off the Olympics.

- **Dissolved oxygen is genuinely low.** It has fallen from 5 to 6 mg/L in the 1950s to under 0.2 mg/L in places this century, with recurring fish kills, worst in the southern reaches and Lynch Cove and worst in late summer and autumn. Not a diver safety issue directly, but it changes what is alive at depth and is why a wall can look bare below a certain contour.
- **Slack falls at high and low water.** This reach behaves as a standing wave, so slack sits within about half an hour of the tide extremes rather than midway between them. This is the exception to the region rule that high water is not slack. It matters because almost nothing in the canal has a governing current station: the nearest one publishing predictions is Hazel Point (PUG1601) up at the entrance. With no station, the tide extremes at the governing tide station are the slack guide. Apply this rule only if you are further into the Hood Canal, closer to the entrance might still behave as the rest of Puget Sound.

## Conditions

- **Water temperature.** Roughly 7 to 11 C at depth all year; the surface layer only warms into the low teens late in summer. Drysuit year round; the configuration is in the diver profile.
- **Visibility.** Swings hard with plankton blooms, worst in spring and summer. Recent reports beat any prediction.
- **Character.** Cold water, mostly shore entries, and tidal exchange drives almost everything. Assume current and a slack window are part of every plan unless told otherwise.

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

Ordered by what actually kills a dive plan in the Sound:

1. **Current** (primary). Nearly everything is a slack-tide dive; the window, not the site, is the plan. Get the slack from a NOAA current station, not a tide station (outside Hood Canal, high or low water is not slack), then apply the site's known offset and correction to that station. Always cross-check that station prediction's slack time and set direction against the site's own ENPAC15 extract (`tools/adcirc_current.py predict` / `window`) before calling a window, even where the station is a well proven one, and reconcile the two rather than trusting the station alone: the Sound is four basins separated by sills that locally accelerate and redirect the flow, so a station some distance away does not always represent the site's own water. When the two disagree on axis rather than just timing, a site file's Current table still carries the governing station's own axis, since that is what the station publishes; the site's real local behavior, from the ADCIRC extract or a shore-parallel set the station's open-water position wouldn't show, goes in the prose underneath, not the table. A site's Time offset should be stablished from a source, logged dives, the station-to-ADCIRC reconciliation, or a re-derived legacy correction, if not possible then it should read "Not established; slack should be confirmed in the water".
2. **Wind** (secondary). Wind decides whether the entry is diveable at all: chop on the entry, surf on the beach, a surface swim into a fetch. Wind against current is worse than either alone. Get the forecast for the beach, not the region.
3. **Viz** (informational). Won't stop the dive, but sets expectations and gear (torch, reel).

## Sites currently covered

| Site | Description |
|---|---|
| [Agate Pass](sites/agate-pass.md) | Fast tidal strait between Bainbridge Island and the Kitsap Peninsula at Suquamish, dived as a slack dive at the bridge pylons or a 1.6 km ebb drift to Old Man House Park; strong current and boat traffic overhead are the hazards. |
| [Alki Beach Park (Junkyard)](sites/alki-beach-park.md) | Wide, sandy Alki shore beach, an easy training entry with a dumped debris "junkyard" reef and a designated octopus preserve; overhead boat traffic is the hazard. |
| [Alki Pipeline](sites/alki-pipeline.md) | Shallow, easy old outfall pipeline off Constellation Park, a common night dive with the pipe itself as a guide rope; surf on the exposed beach is the risk. |
| [Burrows Pass (Skyline Wall)](sites/burrows-pass.md) | Advanced current dive on rock ledges dropping into a tidal channel near Anacortes; only the slack before the ebb is reliably diveable. |
| [Camano Island State Park](sites/camano-island-state-park.md) | Slope steepening into a wall at the island's southwest tip, with genuine current unlike the island's other shores; a fish-rich site best planned tight to slack. |
| [Edmonds Marina Beach (Oil Dock)](sites/edmonds-marina-beach.md) | Former UNOCAL oil pier at Marina Beach Park, just south of Edmonds Underwater Park; the pier itself is long gone, but a long sand swim still reaches rubble and piling stumps at a sharp drop-off. |
| [Edmonds Underwater Park (Brackett's Landing)](sites/edmonds-underwater-park.md) | The region's most dived site, a sanctuary of guide-rope trails over a shallow sandy bottom linking scuttled vessels and a sunken dry dock at the south edge; ferry traffic and poor viz are the hazards. |
| [Fay Bainbridge Park](sites/fay-bainbridge.md) | Sand and eelgrass shore dive at the northeast tip of Bainbridge Island, built around animal behaviour over open bottom rather than structure; the current runs harder than the plain terrain suggests. |
| [Fidalgo Head](sites/fidalgo-head.md) | Long rocky headland reached by a fifteen minute surface swim across a muddy bay at Washington Park, Anacortes; strong, current sensitive water and no alternate exit. |
| [Fort Flagler Fishing Pier](sites/fort-flagler-fishing-pier.md) | Remote reef of pilings and dumped concrete cylinders straight into Admiralty Inlet; current runs hard and dictates a low exchange window. |
| [Fort Ward Park](sites/fort-ward.md) | Sand and cobble slope on Bainbridge Island's Rich Passage shore, built around old WWII submarine net anchors known as the Cribs; ferry traffic overhead and a real, current sensitive tidal exchange are the hazards. |
| [Fort Worden Pier](sites/fort-worden-pier.md) | Pier pilings and a tire and concrete reef at the Port Townsend Marine Science Center, thick with rockfish and resident wolf eels; only works within a slack window on the current. |
| [Green Point](sites/green-point.md) | Low rocky point at Washington Park, Anacortes, rounded on a direct entry; current sensitive with strong nudibranch and encrusting life. |
| [Illahee State Park](sites/illahee-state-park.md) | Easy pier and dock dive on the Kitsap Peninsula's Port Orchard shore across from Bainbridge Island, wharf pilings dropping to a sand slope thick with nudibranchs; negligible current, boats and fishing line overhead are the hazard. |
| [Illahee Town Dock](sites/illahee-town-dock.md) | Port of Illahee community dock on Ocean View Boulevard NE, built around a sunken 1970s-80s tire reef strung together with rope on a gently sloping sand bottom; sparse life, boat traffic and the reef's own entanglement risk are the hazards. |
| [Kayak Point County Park](sites/kayak-point.md) | Easy, low current beginner site on Port Susan, limited mainly by often poor visibility and a working pier and boat ramp overhead. |
| [Keystone Jetty (Fort Casey)](sites/keystone-jetty.md) | Boulder jetty marine preserve on Admiralty Inlet with strong, erratic current that never fully slacks; planned off a current table, not a tide table. |
| [Mukilteo Lighthouse Park (Clay Wall)](sites/mukilteo-lighthouse-park.md) | Current sensitive clay slope riddled with wolf eel and octopus holes on the Mukilteo waterfront; comfortable on slack, dangerous on a big exchange. |
| [Mukilteo T-Dock](sites/mukilteo-t-dock.md) | Sheltered, unusually deep shore dive at the mouth of Possession Sound; the ferry lane, now east of the entry since the terminal moved, is the one hard hazard. |
| [Old Man House Park](sites/old-man-house-park.md) | Suquamish Tribe park at the north mouth of Agate Passage, the take-out for the Agate Pass Bridge drift and a shorter dive of its own in weaker current; boat traffic in Port Madison is the hazard. |
| [Picnic Point Park](sites/picnic-point-park.md) | Mild, low current sand and eelgrass slope between Mukilteo and Edmonds; the main inconvenience is the long walk in, not the dive itself. |
| [Point Whitney](sites/point-whitney.md) | WDFW shellfish lab shore dive on Hood Canal near Brinnon, built around an old discharge pipe thick with giant Pacific octopus dens and, well beyond it, a deep sea whip field; negligible current, easy straight-out navigation. |
| [Richmond Beach Park (Richmond Beach Saltwater Park)](sites/richmond-beach-park.md) | Casual Shoreline shore dive over a sand and cobble shelf that was once a ship breaking ground, its scattered debris, chain and concrete anchor blocks the main draw; the railroad crossing to reach it is the real hazard. |
| [Rockaway Beach (Norrander's Reef)](sites/rockaway-beach.md) | Bainbridge Island's one shore dive, a narrow natural rock reef at the mouth of Blakely Harbor thick with lingcod, octopus and nudibranchs, with usually mild current. |
| [Rosario Beach](sites/rosario-beach.md) | Protected sanctuary bay at Deception Pass with an easy sheltered dive around Urchin Rocks and harder, current driven options further out. |
| [Saltwater State Park](sites/salt-water-state-park.md) | Boulder and concrete piling reef fingers off a decayed barge wreck at Des Moines, reached by a long tide dependent surface swim; a marine protected area. |
| [Scenic Beach](sites/scenic-beach.md) | Negligible current Hood Canal sand and cobble bottom with a rare sea whip forest; not a slack dive, the hazard is small boat traffic. |
| [Seacrest Cove 2](sites/seacrest-cove-2.md) | The city's most dived night diving site, an old marina's pilings and sunken dories on a silty slope across from downtown Seattle; ferry dock and boat traffic overhead. |
| [Sund Rock](sites/sund-rock.md) | Rich, reliable Hood Canal boulder garden and rock walls, a marine preserve with tame lingcod, wolf eels and octopus; negligible current, so access and viz are the limiting factors. |
| [Suquamish Dock](sites/suquamish-dock.md) | Long public dock and boat ramp on the Suquamish waterfront in Port Madison proper, sheltered from Agate Passage's current and close to slack all the time; a shallow, low key dive over sand scattered with old bottles and glass. |
| [Three Tree Point (North)](sites/three-tree-point-north.md) | Artificial junk reef on a sand and cobble slope that continues past 40 m, so depth control is the standing concern; mild current, dives well day or night. |
| [Union Wharf](sites/union-wharf.md) | Port Townsend waterfront dive for period glass and crockery among wharf and pier wreckage rather than a reef; sparse life and unpredictable, if usually weak, current. |

## Dive shops and air fills

Tank fill spots near this folder's sites, by area.

**Seattle and South Sound**

- **Underwater Sports, Seattle.** 10545 Aurora Ave N, Seattle, WA 98133. (206) 362-3310. underwatersports.com. Air and nitrox, hydro testing.
- **Underwater Sports, Federal Way.** 34428 Pacific Highway S, Federal Way, WA 98003. (253) 874-9387. underwatersports.com. Air and nitrox.
- **Underwater Sports, Lakewood.** 9606 40th Ave SW, Lakewood, WA 98499. (253) 588-6634. underwatersports.com. Air and nitrox.
- **Silent World Diving Systems, Bellevue.** 1910 132nd Ave NE, Suite 11, Bellevue, WA 98005. (425) 747-8842. silent-world.com. Air and nitrox.
- **Underwater Sports, Bellevue.** 12003 NE 12th St, Suite 59, Bellevue, WA 98005. (425) 454-5168. underwatersports.com. Air and nitrox.

**North Sound: Everett, Edmonds, Lynnwood**

- **Underwater Sports, Edmonds.** 264 Railroad Ave, Edmonds, WA 98020. (425) 771-6322. underwatersports.com. Air and nitrox. On the same street as, and a few blocks from, Edmonds Underwater Park.
- **Lighthouse Diving Center, Lynnwood.** 13718 31st Ave W, Lynnwood, WA 98087. (425) 771-2679. lighthousediving.com. Air and nitrox.
- **Evergreen Dive Service, Everett.** 4610 Evergreen Way, Suite 1, Everett, WA 98203. (425) 512-8811. evergreendive.com. Air and nitrox.

**Whidbey Island and Anacortes**

- **Anacortes Diving and Supply.** 2502 Commercial Ave, Anacortes, WA 98221. (360) 293-2070. anacortesdiving.com. Air, nitrox and argon.

**Kitsap Peninsula and Hood Canal**

- **Sound Dive Center, Bremerton.** 5000 Burwell St, Bremerton, WA 98312. (360) 373-6141. sounddivecenter.com. Air, nitrox and CO2 fills.
- **Exotic Aquatics Scuba and Kayaking, Bainbridge Island.** 328 Madison Ave N, Suite B, Bainbridge Island, WA 98110. (206) 842-1980. exoticaquaticsscuba.com. Air and nitrox.
- **YSS Dive, Hoodsport.** 22320 N US Highway 101, Shelton, WA 98584. (360) 877-2318. yssdive.com. Air, nitrox and trimix.
- **Jade Scuba Adventures, Brinnon (seasonal).** (360) 300-7810. jadescubaadventures.com. Air fills near Point Whitney; seasonal, opening for the season in June, call ahead before relying on it.

**Jefferson County**

- **Octopus Gardens Diving, Port Townsend.** 2410 Washington St, Port Townsend, WA 98368. (360) 385-3483. octopusgardensdiving.com. Air and nitrox.

## Emergency

Local emergency number: 911. Call EMS first; call DAN once the diver is stabilized and transport is underway.

- **Virginia Mason Franciscan Health, Center for Hyperbaric Medicine, Seattle.** 1100 9th Ave, Seattle, WA 98101. (206) 583-6543. The only multiplace recompression chamber in Western Washington, UHMS accredited with distinction, with board certified hyperbaric physicians on staff. The region's chamber; no other public-access facility is known to operate in the Puget Sound area.
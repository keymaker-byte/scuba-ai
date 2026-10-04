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
- scubaboard.md
- diversatlas.md
- diveatlas.md

## Web Sources

The following web sources should be used in this region:

- **[DAN (Divers Alert Network)](https://dan.org).** Dive medicine, accident data and case narratives (the Annual Diving Report, Incident Insights), the standing source for gear, procedure and debrief questions. Emergency line +1-919-684-9111, 24/7, collect calls accepted worldwide.
- **[NW Dive Club](https://nwdiveclub.com/viewforum.php?f=6).** Community write-ups of how a site is dived: the entry, what's worth seeing, what to expect. Read it through the Wayback Machine (`https://archive.org/wayback/available?url=<page>`, then `curl --compressed` the snapshot), and confirm the snapshot holds the full thread.
- **[The Perfect Dive](https://web.archive.org/web/20220413053905/http://theperfectdive.com/DEF-SiteList.asp).** A defunct catalog of Pacific Northwest sites, frozen around 2022: dive type, difficulty, entry and attractions per site, including several lesser-known sites. Read this pinned snapshot with `curl --compressed`, and verify access, fees and closures against a recent source.

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
| [Agate Pass](sites/agate-pass.md) | Tidal strait between Bainbridge Island and the Kitsap Peninsula at Suquamish, centred on the Agate Pass Bridge pylons, encrusted with plumose anemones and barnacles with lingcod, cabezon and rockfish in their lee; the cobble channel runs 1.6 km north to Old Man House Park, the classic drift. |
| [Alki Beach Park (Junkyard)](sites/alki-beach-park.md) | Sandy north-facing beach near Alki Point in West Seattle, where a guide rope leads down the slope past dumped debris, the junkyard reef of a designated octopus preserve, with early-1900s boardwalk pilings in the eelgrass shallows. |
| [Alki Pipeline](sites/alki-pipeline.md) | Old outfall pipeline off Constellation Park on the southwest side of Alki Point, a broken rock path over white sand topped with orange and white plumose anemones the whole way out, sea pen fields beside it, and a little-visited true end 46 m past the apparent one. |
| [Burrows Pass (Skyline Wall)](sites/burrows-pass.md) | Rock ledges at the west end of Burrows Pass near Anacortes, opening onto Rosario Strait, carpeted in filter feeders: sponges, cup corals, crimson rose anemones sheltering candy-stripe shrimp, and the prized Puget Sound king crab; kelp marks the ledge from the surface in summer. |
| [Camano Island State Park](sites/camano-island-state-park.md) | Southwest tip of Camano Island near Camano Head, where a gradual slope off the beach steepens into a wall under a summer kelp bed, a fish site whose bottom fish reward divers who know where to look. |
| [Ed Munro Seahurst Park](sites/ed-munro-seahurst-park.md) | Long sand and cobble beach in Burien facing the north end of Vashon Island, where a compass swim west from the stream mouth past a small eelgrass bed leads to the rotted remains of a wooden barge and a field of large orange sea pens grazed by striped nudibranchs. |
| [Edmonds Marina Beach (Oil Dock)](sites/edmonds-marina-beach.md) | Site of the former UNOCAL oil pier at Marina Beach Park beside the Port of Edmonds breakwater, a long sand flat ending at a sharp drop-off where rubble and piling stumps hold large copper rockfish and unusually big dorid nudibranchs. |
| [Edmonds Underwater Park (Brackett's Landing)](sites/edmonds-underwater-park.md) | Sanctuary beside the Edmonds ferry terminal since 1970, some 4 km of named guide-rope trails over sand linking scuttled vessels and the sunken DeLion Dry Dock, its anemone-draped structure dense with lingcod, cabezon, octopus and wolf eels long used to divers. |
| [Fay Bainbridge Park](sites/fay-bainbridge.md) | Sand and eelgrass slope at the northeast tip of Bainbridge Island with no structure to navigate by, a site for animal behaviour over open bottom: hermit crabs, skates, flounder lunging from the sand and nudibranchs feeding on sea pens. |
| [Fidalgo Head](sites/fidalgo-head.md) | Rocky headland on the south side of Washington Park's bay at the west end of Fidalgo Island, reached by a fifteen minute compass swim across a muddy bay, its rock and kelp crowded with crabs, sea stars, urchins, chitons and nudibranchs. |
| [Fort Flagler Fishing Pier](sites/fort-flagler-fishing-pier.md) | Old pier line on Marrowstone Island's east shore facing Admiralty Inlet, running due east from the beach to a reef of concrete cylinders and slabs riddled with holes, home to wolf eels, lingcod, scallops and sea pens on the sand around it. |
| [Fort Ward Park](sites/fort-ward.md) | Sand and cobble slope on Bainbridge Island's Rich Passage shore, built around the Cribs, WWII submarine net anchors grown over with plumose anemones and home to a resident giant Pacific octopus and a mated pair of wolf eels. |
| [Fort Worden Pier](sites/fort-worden-pier.md) | Pier at the Port Townsend Marine Science Center in Fort Worden State Park, its pilings shaded under the deck carrying white plumose anemones and purple tube worms, with a tire and concrete reef to the north holding rockfish, octopus and resident wolf eels. |
| [Fox Island East Wall](sites/fox-island-east-wall.md) | Layered sandstone walls off the Fox Island Fishing Pier at Toy Point, at the south end of the Tacoma Narrows, carved by the current into ledges, overhangs and ravines that step down from just off the cobble beach, with a smaller ledge north of the pier, home to giant Pacific octopus, red Irish lords, rockfish and a wide range of sculpins. |
| [Green Point](sites/green-point.md) | Low basalt point at the northwest corner of Washington Park, Anacortes, followed along a kelp and eelgrass shoreline and rounded to a drop toward the channel, a strong nudibranch site with octopus dens in the rock at the point. |
| [Harper Fishing Pier (Barbara G)](sites/harper-fishing-pier.md) | Port of Bremerton fishing pier on Yukon Harbor opposite Blake Island, on the line of the old Mosquito Fleet landing, with a guide line out to the Barbara G trawler wreck, a small fiberglass hull, anemone-covered piling stumps and a field of old bottles and bricks. |
| [Illahee State Park](sites/illahee-state-park.md) | Wharf on the Kitsap Peninsula's Port Orchard shore across from Bainbridge Island, its pilings leading straight out to a sand slope, with an abundance of nudibranchs on the structure and sea stars, Dungeness crab and geoduck on the sand. |
| [Illahee Town Dock](sites/illahee-town-dock.md) | Port of Illahee community dock on Ocean View Boulevard NE, leading out to a 1970s-80s tire reef of rope-bound clumps on a gentle sand slope, sparse but holding rockfish, lingcod and sculpin, with tube worms on the connecting ropes. |
| [Kayak Point County Park](sites/kayak-point.md) | County park pier and boat ramp on the east shore of Port Susan, the only structure on an open silty slope that drops steadily offshore, with flounder, Dungeness crab and moon snails on the soft bottom and gray whales passing in late spring. |
| [Keystone Jetty (Fort Casey)](sites/keystone-jetty.md) | Boulder jetty in a marine preserve beside the Coupeville ferry terminal at Fort Casey, its sheltered east face draped in white plumose anemones and home to tame greenlings, lingcod and cabezon, with the encrusted Rock of Life and old wharf pilings 230 m east as landmarks. |
| [Mukilteo Lighthouse Park (Clay Wall)](sites/mukilteo-lighthouse-park.md) | Slope south of Elliott Point in Possession Sound, crossed by low clay banks pocked with holes that make the site's signature dens for wolf eels and giant Pacific octopus, with harbor seals year round and sea lions in winter. |
| [Mukilteo T-Dock](sites/mukilteo-t-dock.md) | Steep slope at the mouth of Possession Sound, strung with guidelines past an upright road sign to an encrusted PVC geodome with an angel statue at its centre, known for wolf eels and for octopus hunting in the open after dark. |
| [Old Man House Park](sites/old-man-house-park.md) | Suquamish Tribe park at the north mouth of Agate Passage where it opens into Port Madison, an eelgrass bed thinning into sand and gravel, the take-out for the Agate Pass Bridge drift and a short dive of its own, with seals beyond the grass. |
| [Port Washington Narrows](sites/port-washington-narrows.md) | Drift of about 2.6 km through Bremerton from the Manette Bridge, under the Warren Avenue Bridge, to Lions Park, over cobble scattered with boulders, where pink and sunflower stars dig for clams and octopus shelter among the larger rocks. |
| [Picnic Point Park](sites/picnic-point-park.md) | Gentle sand and eelgrass slope with no major structure between Mukilteo and Edmonds, a small stream crossing the beach as the shoreline landmark, with sea pens, striped nudibranchs and sunflower stars below the eelgrass line. |
| [Point White Dock (Crystal Springs Pier)](sites/point-white-dock.md) | Historic Mosquito Fleet steamer dock at Point White on Bainbridge Island, pilings running 85 m out over sand dollar beds and juvenile sea pens to an anemone-covered cartwheel past the dock end, with old glass in the sand. |
| [Point Whitney](sites/point-whitney.md) | WDFW shellfish lab shore dive on Hood Canal near Brinnon, where an old discharge pipe runs straight out as the single navigational spine, its concrete dividers thick with giant Pacific octopus and warbonnet dens, with a deep sea whip field beyond its end. |
| [Richmond Beach Park (Richmond Beach Saltwater Park)](sites/richmond-beach-park.md) | Shoreline saltwater park on a former ship breaking ground, a loop over a sand and cobble shelf through scattered debris, a cinderblock trail and anchor chain to concrete anchor blocks and a 4 m steel propeller on the deeper slope. |
| [Rockaway Beach (Norrander's Reef)](sites/rockaway-beach.md) | Bainbridge Island's natural rock reef at the mouth of Blakely Harbor, a narrow west to east rib of outcrops and cracks on sand, thick with lingcod, octopus, plumose anemones and lemon peel nudibranchs, continuing south to Metridium Wall and Leiker's Reef. |
| [Rosario Beach](sites/rosario-beach.md) | Sanctuary bay in Deception Pass State Park on Rosario Strait with four dives from one beach (Urchin Rocks under bull kelp, Rosario Head into Sharpe Cove, the north cliffs, and the walls of Northwest Island), its rock thick with urchins, spider crabs and clouds of shrimp. |
| [Saltwater State Park](sites/salt-water-state-park.md) | Marine protected area at Des Moines on East Passage, guide lines running from a buoyed, disintegrated barge wreck out to three reef fingers of boulders and concrete pilings built in 2009, home to wolf eels, big lingcod and several rockfish species. |
| [Scenic Beach](sites/scenic-beach.md) | Hood Canal sand slope just south of Misery Point, navigated by the stairs and the slope alone, from cobble and eelgrass down to a rare sea whip forest on the deep sand, with sea pens, nudibranchs and gatherings of hermit crabs. |
| [Seacrest Cove 2](sites/seacrest-cove-2.md) | Cove between the water taxi dock and the fishing pier at Seacrest Park, across Elliott Bay from downtown Seattle, a silty slope of old marina pilings, sunken dories, the Honey Bear cabin cruiser and deep I-beams, the city's favourite night dive for octopus and seals. |
| [Sund Rock North Wall](sites/sund-rock-north-wall.md) | Hood Canal marine preserve between Hoodsport and Lilliwaup, from a boulder garden at the entry to a wall stepping down in ledges, with a fish bowl and an old fishing wreck to the north and tame lingcod, wolf eels and octopus. |
| [Sund Rock South Wall](sites/sund-rock-south-wall.md) | Boulder formations at the south end of the Sund Rock preserve on Hood Canal, reached straight off their own footpath onto the wall, holding some of the best wolf eel and octopus dens on the property. |
| [Sunnyside Beach Park](sites/sunnyside-beach-park.md) | Steilacoom town beach on the South Sound, where an eelgrass flat drops down a short slope to guide lines leading to an abandoned outfall pipeline running out past 28 m and a cluster of small sunken boats, one crewed by Santa and Frosty, with octopus under the pipe and a spring crop of juvenile spiny lumpsuckers in the eelgrass. |
| [Sunrise Beach Park](sites/sunrise-beach-park.md) | Hard rock wall in the Colvos Passage Marine Preserve north of Gig Harbor, reached by swimming south along the beach to a deformed evergreen leaning over the water, its undercut ledges and crevices home to resident wolf eels, giant Pacific octopus and mosshead warbonnets above a boulder slope into deep water. |
| [Suquamish Dock](sites/suquamish-dock.md) | Long public dock and boat ramp on the Suquamish waterfront in Port Madison, kelp-covered metal pilings over a gentle sand bottom scattered with barnacle-encrusted bottles and glass from the site's long history as a village and trading place. |
| [Three Tree Point (North)](sites/three-tree-point-north.md) | Artificial reef on the north side of Three Tree Point in Burien, tires and sunken boats toward the point and a junkyard of concrete, pipe, appliances and a runabout on its trailer to the northeast, with frequent red octopus and a diverse sea star and sculpin cast. |
| [Titlow Beach](sites/titlow-beach.md) | Old ferry slip at Titlow Park on the Tacoma Narrows south of the Narrows Bridge, two converging rows of pilings so densely covered in white plumose anemones that divers call them the Cathedral, with lone goalpost pilings marking the way to sandstone and clay shelves to the south that hold giant Pacific octopus and wolf eel dens. |
| [Tramp Harbor Dock](sites/tramp-harbor-dock.md) | Former oil dock and fishing pier in Tramp Harbor on Vashon Island's east shore, its anemone-covered pilings running out over flat sand and lettuce kelp to a bottle garden off the southeast side, found on a bearing toward Robinson Point and home to small red octopus living in the bottles, with stubby squid breeding here in winter. |
| [Union Wharf](sites/union-wharf.md) | Port Townsend's downtown waterfront from the Adams Street beach, the rebuilt Union Wharf to the southwest and an abandoned ferry pier and its four pylons to the northeast, a dive for period glass and crockery among the debris on soft silt. |
| [Warren Avenue Bridge](sites/warren-avenue-bridge.md) | Three concrete pylons of the Warren Avenue Bridge in Port Washington Narrows, Bremerton, so thick with plumose anemones and feather duster worms the piers disappear beneath them, with boulders at the outer pylons and piddock-riddled clay sheltering sculpins. |

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
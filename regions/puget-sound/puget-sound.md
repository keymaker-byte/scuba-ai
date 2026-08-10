# Puget Sound Dive Planning

Region steering file for diving Puget Sound: the environment, how a plan comes together here, and the two conventions every number follows, local time and MLLW depth. The conventions exist because a number that looks right in the wrong frame is more dangerous than a number that is obviously missing.

## The region

Puget Sound is an estuary in western Washington, running about 160 km from Deception Pass in the north to Olympia in the south. It reaches the Pacific through the Strait of Juan de Fuca by three entrances: Admiralty Inlet, which carries most of the exchange, plus Deception Pass and the Swinomish Channel. Surface area is about 2,640 km², volume about 110 km³, mean depth about 137 m, and the deepest water about 283 m off Jefferson Point. Roughly 2,140 km of shoreline make it a shore-diving region.

It is one system of four deep basins separated by sills, submarine ridges that throttle the exchange between them:

| Basin | Where |
|---|---|
| **Main Basin** | Admiralty Inlet and the Central Basin, Whidbey Island down to the Tacoma Narrows |
| **Whidbey Basin** | East of Whidbey Island, taking the Skagit, Stillaguamish and Snohomish |
| **Hood Canal** | West of the Kitsap Peninsula |
| **South Sound** | South of the Tacoma Narrows |

The sills matter to planning because they are where the water accelerates. The three that count are Admiralty Inlet, the Hood Canal entrance (about 53 m) and the Tacoma Narrows (about 44 m). Tidal range grows as you go south, about 2.5 m at Port Townsend and about 4.4 m at Olympia, so the depth convention matters more the further south you dive.

### Boundaries

- **Strict definition** (USGS): the water south of the three Strait entrances. That takes in Hood Canal, Admiralty Inlet and Possession Sound, and leaves out Bellingham Bay and the San Juan Islands.
- **This folder is broader.** Some sites sit north of Deception Pass, on Rosario Strait and the approaches to the San Juans, which are Salish Sea rather than Puget Sound proper. They are kept here because they are dived the same way, off the same tools and conventions. A site is located by its file's coordinates and stations, not by the folder name.
- **Hood Canal is inside the region.** It is one of the four basins, not a neighbouring body of water, but it behaves differently enough to carry its own section in this file.
- **Salish Sea** is the collective name for Puget Sound, the Strait of Juan de Fuca and the Strait of Georgia together, and the right word for water north or west of the Sound.

## Conditions

- **Water temperature.** Roughly 7 to 11 C at depth all year; the surface layer only warms into the low teens late in summer. Drysuit year round; the configuration is in the diver profile.
- **Visibility.** Swings hard with plankton blooms, worst in spring and summer. Recent reports beat any prediction.
- **Character.** Cold water, mostly shore entries, and tidal exchange drives almost everything. Assume current and a slack window are part of every plan unless told otherwise.

## How planning works here

Ordered by what actually kills a dive plan in the Sound:

1. **Current** (primary). Nearly everything is a slack-tide dive; the window, not the site, is the plan. Get the slack from a NOAA current station, not a tide station (outside Hood Canal, high or low water is not slack), then apply the site's known offset and correction to that station. Always cross-check that station prediction's slack time and set direction against the site's own ENPAC15 extract (`adcirc_current.py predict` / `window`) before calling a window, even where the station is a well proven one, and reconcile the two rather than trusting the station alone: the Sound is four basins separated by sills that locally accelerate and redirect the flow, so a station some distance away does not always represent the site's own water.
2. **Wind** (secondary). Wind decides whether the entry is diveable at all: chop on the entry, surf on the beach, a surface swim into a fetch. Wind against current is worse than either alone. Get the forecast for the beach, not the region.
3. **Viz** (informational). Won't stop the dive, but sets expectations and gear (torch, reel).

## Hood Canal

A fjord, not a sound: a narrow trench separating the Kitsap Peninsula from the Olympic Peninsula, entered between Foulweather Bluff and Tala Point south of Admiralty Inlet. It runs about 80 km southwest to Union, turns sharply northeast at the Great Bend, and continues about 24 km to Belfair, ending in the shallow tidelands of Lynch Cove. Average width is about 2.4 km, mean depth about 54 m, maximum depth about 180 m. Dabob Bay is the largest bay off it, and the Skokomish, Hamma Hamma, Duckabush, Dosewallips and Big Quilcene come in off the Olympics.

- **Dissolved oxygen is genuinely low.** It has fallen from 5 to 6 mg/L in the 1950s to under 0.2 mg/L in places this century, with recurring fish kills, worst in the southern reaches and Lynch Cove and worst in late summer and autumn. Not a diver safety issue directly, but it changes what is alive at depth and is why a wall can look bare below a certain contour.
- **Slack falls at high and low water.** This reach behaves as a standing wave, so slack sits within about half an hour of the tide extremes rather than midway between them. This is the exception to the region rule that high water is not slack. It matters because almost nothing in the canal has a governing current station: the nearest one publishing predictions is Hazel Point (PUG1601) up at the entrance. With no station, the tide extremes at the governing tide station are the slack guide. Apply this rule only if you are further into the Hood Canal, closer to the entrance might still behave as the rest of Puget Sound.
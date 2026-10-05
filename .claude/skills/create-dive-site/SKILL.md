---
name: create-dive-site
description: This skill should be used when the user asks to create a new dive site file, write up a dive site, add a site to a region, document a new site, or substantially rewrite an existing site file in this scuba diving workspace. Covers gathering the required inputs, loading that region's own conventions, verifying the coordinate against bathymetry and current-model coverage, running research passes, working out the current section by the region's method and the wind section from the shoreline tool, the bookkeeping a new site needs, and a final independent audit of the site file's and region row's prose by a fresh agent.
---

# Create a dive site file

Produce one `regions/<region>/sites/<slug>.md` file, matching the template at the bottom of this skill, plus the bookkeeping entries that make the new site discoverable, then have a fresh agent audit the prose. This is a research and verification task before it is a writing task: most of the work is pinning down numbers against live sources.

## 1. Required inputs — stop and ask if any are missing

Do not guess any of these. Ask the user and wait rather than proceeding on an assumption: Coordinates, or a source to derive them. A decimal-degree pair for the dive area itself (the point underwater that is actually dived), or a source that pins it (a guidebook page, a forum post with a described location, a named chart feature). If neither a coordinate nor a usable source is given, stop and ask before doing anything else. Boat or shore. If shore, also get parking coordinates and entry point coordinates, or a clear source to find them (a described trailhead, a named parking lot). A boat-only site omits both rows entirely; don't ask for them in that case. Which region folder the site belongs to. Infer it only when it's unambiguous from the coordinate or the user's own wording (e.g. a coordinate that clearly falls inside a region already covered here). Otherwise stop and ask.

## 2. Load the region's own conventions before writing anything

Read `regions/<region>/<region>.md` in full before touching the site file. It fixes, for this region specifically, not as a workspace default: its "Site file conventions", the region's current type and the method behind every current figure, what every site file here carries, and the fixed depth datum (if any) this region normalizes depth to, with the arithmetic for converting an observed depth to it and back; which tools this region actually uses (its own "Tools" list), use only those for this site, not the full workspace tool list; which websites this region reads for site research (its own "Web Sources" list), and how each one is read; the region's hydrography and how planning works there, which situates where a new site fits among the ones already covered. A site file written without the region file loaded is not trustworthy: a depth figure with no datum behind it, or a current reasoned out against the wrong tool set, looks identical to a correct one until someone is in the water.

## 3. Verify the coordinate

A coordinate handed over (or found) is a first reference, not a final one. Check its seabed depth before writing anything. A point mid-channel or off the drop is not the dive. If it's too deep, or off the divable slope, walk it toward shore and re-check, comparing candidate depths against the source description (a guidebook, community reports, the site's own terrain narrative) until the coordinate's depth matches what is actually described as being dived. It also has to sit inside the coverage of the region's spatial current model, where it has one: extracting a prediction refuses a coordinate outside the model's domain, and a coordinate walked too close to shore can fall outside that coverage. If no point anywhere near the dive area lands inside the model's domain, don't force it: skip the spatial extraction for this site and pick the governing current and tide stations directly, the same as a region with no spatial current model at all.

## 4. Research: all mandatory, in order

Complete each one before starting the next. Take behaviour from community sources, never numbers: their depths sit at an unrecorded tide and their slack times carry no station. 

Important! Every pass feeds the same rule: if a source it depends on fails, stop and report it.

### 4.1 Research pass 1: the region's tools

Run every tool in the region file's own "Tools" list against this site. A tool that genuinely doesn't apply to a site file (a wind forecast needs a dive date) is named in chat as skipped and why, never silently dropped. The current figures are written up in step 5 and the shoreline tool runs in step 6, once the research is in.

- **Current.** Gather every input the region's current method names in its Site file conventions: the stations and their bins, the spatial current model extract, timed observations for an offset, the local descriptions behind a wind driven set.
- **Tide.** Pick the tide station in the same body of water, on the same side of any sill as the site, and verify its name and position.
- **Dive log.** Search the log for the site under its name and its likely variants. Every logged dive is calibration: its times anchor the offset, its maximum depths normalize to the datum and check the bathymetry, its temperatures and notes go into the file's own sections.
- **Community databases, visibility reports, forum feeds.** A tool that returns nothing for this site is checked once against a site it is known to carry before the empty result is accepted as "no record".

The pass is finished when every listed tool has either produced its figure or been reported as skipped or failed.

### 4.2 Research pass 2: the region's web sources

Read every entry in the region file's own "Web Sources" list, the way that entry says to. Reading a source means searching inside it for this site (the forum's site listings, the catalog's site list) and reading every page that turns up in full, not checking that an archived snapshot exists. Confirm an archived snapshot holds the whole page or thread before relying on it. A source that has nothing on the site is reported as having nothing, after its own index or search was actually read.

Initial dive guides the user supplies are a standing source for this pass, spanning both current behaviour and entries, hazards, marine life, and access. Their figures are dated, so re-derive every current and depth figure against a live source before it enters the file, and verify access, parking, fees and closures against a recent report.

The pass is finished when every listed source has been searched for the site and every hit read.

### 4.3 Research pass 3: the web deep dive

A broad, deep search of the open web, run after the first two passes and as its own step. Sources outside the fixed lists (a dive shop's own site page, a forum thread, a recent trip report, an incident writeup, a park district notice) turn up facts none of the standing sources carry alone: an access change, a renamed park, a new fee, a gate, a closure, a hazard, a behaviour of the current no table predicts.

- **Search wide.** Run many distinct queries in the thorough search mode, in parallel, covering at least: the site by name and every variant of it (former names, the park, the point, the pier, the street); trip reports and forum threads across the dive forums and community sites; access (the managing agency's own page, hours, fees, gates, closures, construction on the roads and bridges that reach it, towing); incidents (accidents, rescues, sheriff and coast guard reports, an agency's own blotter); and marine life (photo galleries, critter reports). Keep searching until new queries stop turning up new pages.
- **Read deep.** Open every relevant result and read it in full; a search snippet is a pointer, never a source. When a fetch fails, try the page directly, then an archived copy.
- **Keep a ledger.** Track every page found, whether it was read, and what it contributed or why it was set aside. Present the ledger in chat when the pass ends.
- **Stop on a gap.** If a page that looks relevant won't load, has only a broken archived copy, or is blocked, stop rather than writing the file around it. Tell the user what turned up and what wouldn't come through, and ask them to paste the content in, or confirm it's out of reach for them too, before continuing. Never present the file as complete over a gap like this.
- **Surface conflicts.** When two sources disagree on a fact that goes in the file (a fee one official page lists and another doesn't, two different closing hours), name both to the user and ask before choosing; if neither can be settled, state it conservatively.
- **Test a new behaviour against what is already established.** Before proposing a current behaviour or hazard drawn from a report, check whether the file already explains it (an early turn is the offset, not a second behaviour). A single anecdote that nothing else corroborates is a question for the user, not a fact for the file.
- **On an existing site file, propose, don't overwrite.** When the pass runs against a site file that already exists, present each addition or change in chat, with its sources, and wait for the user to choose which go in.

The pass is finished when the searches have stopped producing new pages, every relevant page is read or reported to the user as unreadable, and the ledger has been shown.

## 5. Work out the current section

The Current section states the same figures, in the same format, at every site of a given current type. The region decides how each figure is produced: its Site file conventions name the region's current type and the method behind every figure (the tools, stations, bins and reconciliation for that water). Follow that method, and write its results as below.

- **Current type.** Tidal, wind driven or none, as the region's Site file conventions set it. A site whose own water behaves differently from its region (a tidal pass in an otherwise slack region) states its own type, with the reason given in chat.
- **Tidal.** The governing station, its ID and distance; the recommended bin and its depth; the time offset and which slack it applies to, or "Not established; slack should be confirmed in the water"; the flood and ebb axes, each as the compass point spelled out and degrees ("southeast, 145°"); the peak flood and ebb speeds at the recommended bin, as the range of daily peaks over one spring to neap cycle (about 15 days), in m/s; and the diveable window, which slack and its typical length over the same cycle.
- **Wind driven.** A set that moves a diver at depth and that a dive is planned around. The usual set, as the compass point spelled out and degrees; its typical speed range in m/s; and the winds or seasons that strengthen or reverse it.
- **None.** Still water, or a surface drift alone. The Current type row alone.
- **Local behaviour.** The bullets after the table carry what its figures leave out: an eddy, a set along a wall, a turn in the shallows. Every figure comes from the region's method; a behaviour can come from community sources, under step 4's rule of behaviour, never numbers.
- **A figure the method can't produce** is written as not established and reported in chat.

## 6. Work out the wind section

The Wind section comes from one mechanism, the same at every site in every region: `tools/shore_exposure.py` measures the geometry, the site's own Current section gives the current's set, and the rules below turn both into the section's bullets. Run the tool on the coordinates that go in the file:

```sh
python3 tools/shore_exposure.py <dive lat> <dive lon> --entry <entry lat> <entry lon>   # shore site
python3 tools/shore_exposure.py <dive lat> <dive lon>                                   # boat site
```

- **Facing rows.** Each written as the compass point spelled out in lowercase and the tool's bearing ("west-southwest, 247°"). Each row takes the tool line of the same name: Entry shore facing, the shore at the entry point, which every shore site carries; Dive area shore facing, the shore nearest the dive area, which every site carries. A shore site carries both rows even where they agree.
- **Classify each of the 16 directions** by its shore relation and fetch, as the tool prints them:

| Wind direction | Fetch | Goes in |
|---|---|---|
| Onshore | 5 km or more | Bad |
| Onshore | 1 to 5 km | Short fetch |
| Onshore | Under 1 km | Fine |
| Cross-shore | 5 km or more | Mixed |
| Cross-shore | Under 5 km | Fine |
| Offshore | Any | Fine |

- **Group into sectors.** Adjacent directions in the same class form one sector, named clockwise from end to end in the 16 compass points. A Bad, Short fetch or Mixed sector is spelled out with its compass shorthand in parentheses ("south through west (S-W)") and its fetch range ("over 8 to 19 km of open water"); a Fine sector names its directions and what blocks them, from the tool output or the site file's own description of the shore (a bluff, a headland, a breakwater).
- **Calm only.** A site that research shows dives only in calm whatever the direction (an exposed windward coast, a kite beach, a site its own sources rule out in any wind) writes its Bad bullet as every direction, "all directions (N-NNW), calm only", with the reason.
- **Wind against current.** Read the set directions from the site's Current section: the flood and ebb axes of a tidal current, the usual set of a wind driven one. The wind opposing a set blows from the direction the water flows toward, within 45° either side; name each opposing wind with 1 km or more of fetch, together with the set it opposes ("a north wind against the ebb"). A site whose current type is none writes the bullet as one sentence: the water holds still, so wind alone sets the surface. Where the site's peak current stays under the threshold the region's current method names, the bullet says the current is too weak to stack against wind. A Current section with no set direction leaves this bullet unwritable: stop and report it as a gap in the Current section.
- **Local knowledge.** Research from step 4 can move a direction up a class (Fine to Short fetch or Bad, Short fetch to Bad), never down, with the reason stated in the bullet and a source behind it: wind funnelled along a narrows or a valley lake, swell wrapping around a point.
- **Tool stops.** A coordinate the tool reads as on land goes back to step 3. A failed download or an unreadable dataset is a failed source: stop and report it.

## 7. Write the file

Follow the template at the bottom of this skill for structure (section order, the table rows, what each one holds). A few rules that aren't obvious from the template alone: Type is exactly "Shore" or "Boat," nothing else. Shore is anything reachable from land, however long the surface swim; Boat only applies when there is no shore access at all. A surface swim distance, an access restriction, or a guided-only requirement belongs in Getting There, not folded into the Type value ("Boat or shore", "Shore, guided only" are both wrong). Keep the facts, drop the bookkeeping. A fact goes in whether it came from public data or from what was seen over repeated dives: coordinates, depth ranges, the governing current station and its bin, the offset, current behaviour, entry, hazards, temperatures, marine life. The confidence work still happens, it just doesn't live in the file: verify a station still publishes, verify the tide station's name and position, reason through the offset and how sure of it this is. That reasoning belongs in chat; the file carries only the best number it produced. Air fills and dive shops belong in the region's own steering file, not here. A site file's Facilities row names only what's physically at the site itself. Follow the workspace's Writing style, Units, Time and Depth conventions in `CLAUDE.md` for everything that goes in the file.

## 8. Bookkeeping, once the file exists

A new site isn't done until it's discoverable from both places that index it. A row in the region's own steering file, under its "Sites currently covered" table: the site name linking to `sites/<slug>.md`, plus a one-sentence description that characterises the site the way a guidebook index would: where it is, what the terrain and structure are, its navigation landmarks, its notable life, and anything unique to it. Leave out hazards, current, slack timing, skill level, access status and anything else that belongs to planning; the site file carries those. An entry in `map/data.js`, the index `map.html` draws its pins from. Add one object to the top-level `sites` array:

```json
{
  "slug": "<site-slug>",
  "name": "<site name>",
  "region": "<region folder slug>",
  "type": "shore" or "boat",
  "file": "regions/<region>/sites/<slug>.md",
  "site": { "lat": <dive site latitude>, "lon": <dive site longitude> },
  "parking": { "lat": <parking latitude>, "lon": <parking longitude> } or null,
  "entry": { "lat": <entry latitude>, "lon": <entry longitude> } or null
}
```

`site` is the dive site's own coordinate, the same one in the file's Coordinates row, never the parking or the entry point. `type` is `"shore"` or `"boat"`, lowercased from the file's Type row. `parking` and `entry` come from the file's own Parking coordinates and Entry point coordinates rows; both are shore-only, `null` for a boat-only site. The spatial current model extract, `regions/<region>/sites/<slug>.json`, if the region has spatial current model coverage and step 3 didn't rule it out for this coordinate. Keep both the region table and `map/data.js` current whenever a site file is added or a site's coordinates, name, type, parking, or entry point change.

## 9. Independent audit, once every file is written

The last step is an audit of the prose by a fresh agent, which reads the files exactly as written. Launch one with the Agent tool as a new `general-purpose` agent. The audit covers the site file and the site's row in the region's steering file. Give the agent the site file, the region steering file, `CLAUDE.md` and this skill file, and tell it to read them in full and report each finding with its file, line, the rule it breaks, the text as written, and a proposed fix. It checks:

- **Workspace conventions.** Every rule in `CLAUDE.md`'s Writing style, Units, Time and Depth sections, read from `CLAUDE.md` at audit time and applied line by line to the site file and the region row.
- **Region conventions.** The region steering file's "Site file conventions", read at audit time and applied to the site file: the stations and companion files it requires, and every depth stated against its datum.
- **Template and steps 7 and 8.** The site file against this skill's template and step 7, and the region row against step 8's rules for its description, all read from this file at audit time.
- **Current completeness.** The Current section against step 5: a Current type row, every row and bullet that type requires present, each in the stated format, and any missing figure written as not established.
- **Wind completeness.** The Wind section against step 6: both facing rows for a shore site and the dive area row for a boat site, each in the stated format; Bad, Short fetch, Mixed and Fine named as compass sectors with their fetch, and every Bad, Short fetch and Mixed sector carrying its compass shorthand in parentheses; and a wind against current bullet that names the set it opposes from the file's own Current section, or, for a current type of None, says the water holds still.
- **Consistency within the prose.** A fact stated more than once (a depth, a distance, a bearing, how strong the current is) says the same thing everywhere it appears in the site file, from the intro through the bullets, and the region row agrees with the site file.
- **Claims to check.** Any sentence that reads as a single anecdote stated as a fact, or a fact that looks carried over from a neighbouring site, listed for the writer to check.

Then work the findings yourself. Fix style, template and consistency findings directly. Hold each claim flagged for checking against the research from step 4: keep it if a source supports it, restate it conservatively if a source partly supports it, and remove it if no source supports it. Report the audit in chat as a table of findings, each with what was changed or why it was left as it is. The site is finished once every finding is resolved.

## Template

```markdown
# Site Name

Two to five sentences of plain prose: what the site is, where it is, its character, and its headline hazard. No bold, no dashes as connectors, no source names.

| | |
|---|---|
| **Location** | Town, state, and the body of water |
| **Coordinates** | Decimal degrees of the dive site (the area actually dived, not the entry or the parking), with the seabed depth at that point in parentheses (m below MLLW) |
| **Parking coordinates** | Decimal degrees of where to park, with a brief description. Shore sites only; omit this row for a boat-only site |
| **Entry point coordinates** | Decimal degrees of where you actually step into the water, with a brief description. Shore sites only; omit this row for a boat-only site |
| **Type** | Shore or Boat only. Surface swim time or other access notes go in Getting There, not here |
| **Depth range** | Below MLLW where a datum is known, otherwise the observed range |
| **Skill level** | Only if known; omit the row otherwise |

## Getting there

* **Entry.** Where and how to get in the water.
* **Parking.** Where to leave the car, and cost.
* **Access.** Hours, distances, restrictions.
* **Facilities.** Restrooms, anything on or near site.

## Navigation and landmarks

* **Topic.** Ordered landmarks or navigation notes, each led by a bold topic.

## Current

Optional sentence on what dominates the current here. Tidal and wind driven only.

| | |
|---|---|
| **Current type** | Tidal, Wind driven, or None |
| **Governing station** | Tidal only: station name and ID, and distance |
| **Recommended bin** | Tidal only: bin number and depth |
| **Time offset** | Tidal only: minutes and which slack, or "Not established; slack should be confirmed in the water" |
| **Flood axis** | Tidal only: compass point spelled out and degrees |
| **Ebb axis** | Tidal only: compass point spelled out and degrees |
| **Usual set** | Wind driven only: compass point spelled out and degrees |
| **Typical speed** | Wind driven only: m/s range |

* **Flood.** Tidal only: where it sets locally, and its peak speed range over a spring to neap cycle in m/s.
* **Ebb.** Tidal only: where it sets locally, and its peak speed range over a spring to neap cycle in m/s.
* **Diveable window.** Tidal only: which slack, its typical length under the region's current threshold, and any behaviour that narrows it.
* **Drivers.** Wind driven only: the winds or seasons that strengthen or reverse the set.
* **Topic.** Any further local behaviour, each led by a bold topic.

## Depth and tide

Short note on how much the tide swings the depth here.

| | |
|---|---|
| **Tide station** | Tide station name and ID, and distance |
| **Series** | High and low water only, or full series |
| **Typical range** | Median and maximum daily range, and the year's span |

Optional table of features by depth below MLLW, and how they read at a low and a high.

## Hazards

* **Topic.** Each hazard led by a bold topic.

## Wind

| | |
|---|---|
| **Entry shore facing** | Compass point spelled out in lowercase and degrees, the shore at the entry point. Shore sites only; omit this row for a boat-only site |
| **Dive area shore facing** | Compass point spelled out in lowercase and degrees, the shore nearest the dive area |

Optional prose after the table: the shoreline's shape where the bearing alone doesn't carry it (a cove, a point, a channel, a short fetch along a lake), stating only what the tool's output shows.

* **Bad.** Optional: each onshore sector with 5 km or more of fetch, spelled out with its compass shorthand in parentheses, its fetch range, and why it spoils the entry. A calm only site writes "all directions (N-NNW), calm only", with the reason.
* **Short fetch.** Optional: each onshore sector with 1 to 5 km of fetch, spelled out with its compass shorthand in parentheses, its fetch range, and why it spoils the entry.
* **Mixed.** Optional: each cross-shore sector with 5 km or more of fetch, spelled out with its compass shorthand in parentheses, which runs a swell past the entry.
* **Fine.** Offshore sectors, onshore sectors under 1 km of fetch, and cross-shore sectors under 5 km, and what blocks them, from the tool output or the site file's own description of the shore.
* **Wind against current.** The wind opposing each exchange, with the exchange named, or that the current is too weak to stack against wind.

## Visibility

* **Topic.** What drives visibility here and when it is best or worst. Overall description not based on single day anecdotes.

## Temperature

* **At depth.** Range through the year, and the season's figure. Exposure protocol.
* **Surface layer.** If it differs sharply from depth.

## Marine life

* **Topic.** What is seen, grouped by zone or type.
```

---
name: create-dive-site
description: This skill should be used when the user asks to create a new dive site file, write up a dive site, add a site to a region, document a new site, or substantially rewrite an existing site file in this scuba diving workspace. Covers gathering the required inputs, loading that region's own conventions, verifying the coordinate against bathymetry and current-model coverage, running research passes, working out the depth, current and wind sections by the region's site conventions, the bookkeeping a new site needs, and a final independent audit of the site file's prose by a fresh agent.
---

# Create a dive site file

Produce `regions/<region>/sites/<slug>.md` from the template at the bottom, plus its bookkeeping, then have a fresh agent audit the prose. Most of the work is pinning numbers down against live sources; the writing comes last.

The region's site conventions file names the tools and sources for this region and how each is used. This skill holds what applies in every region: the order of the work, the rules that turn tool output into the file, and the template.

## Ground rules, for every step

- **Stop on a failed source.** A tool error, an unreachable API, a page that won't load or has only a broken archived copy: stop, tell the user what failed and what it was meant to provide, and wait. Never write the file around the gap or present it as complete.
- **Behaviour, never numbers, from community sources.** Their depths sit at an unrecorded tide and their slack times carry no station nor normalization.
- **Reasoning in chat, facts in the file.** Station checks, offset reasoning, how sure a figure is, and conflicts between sources all go in chat. The file carries only the best figure produced.

## 1. Required inputs

Ask and wait if any is missing; never guess.

- **Dive area coordinate.** A decimal-degree pair for the point underwater that is actually dived, or a source that pins it (a guidebook page, a described forum post, a named chart feature). With neither, ask before anything else.
- **Shore or boat.** A shore site also needs parking and entry point coordinates, or a clear source for them. A boat site needs neither.
- **Region.** Infer it only when the coordinate or the user's wording makes it unambiguous.

## 2. Load the region

Read both of these region files in full before anything else.

- **`<region>-site-conventions.md`.** Use only the tools and sources it names, the way it says to use them.
- **`<region>.md`.** The hydrography and any subarea that behaves differently.

## 3. Verify the coordinate

- **Depth.** Check the seabed depth at the coordinate with the site conventions' Depth tool. If it is too deep or off the divable slope, walk it toward shore and re-check until its depth matches what the sources describe as dived.
- **Current model coverage.** Where the site conventions' Current section names a spatial model extract, the coordinate must sit inside the model's coverage. If no point near the dive area does, skip the extraction and work the current from the station alone, and say so in chat.

## 4. Research

Three passes, each finished before the next starts.

### 4.1 Research tools

Run every tool under the site conventions' Region Specific Research Tools. Done when each has produced its result or been reported as failed.

### 4.2 Research sources

Read every source under the site conventions' Region Specific Research Sources: search inside it for this site and read every hit in full. Confirm an archived snapshot holds the whole page before relying on it. Guides the user supplies count as a source here; re-derive their current and depth figures by the region's conventions, and verify their access, parking, fees and closures against a recent report.

Done when every source has been searched and every hit read, or reported as having nothing.

### 4.3 The open web

- **Search wide.** Many distinct queries, thorough mode, in parallel: every name variant (former names, the park, the point, the pier, the street); trip reports and forum threads; access (the managing agency, hours, fees, gates, closures, road and bridge work, towing); incidents (accidents, rescues, sheriff and coast guard reports); marine life (galleries, critter reports). Continue until new queries stop turning up new pages.
- **Read deep.** Open every relevant result in full; a snippet is a pointer. On a failed fetch, try the page directly, then an archived copy, then stop and ask the user to paste it or confirm it is out of reach.
- **Keep a ledger.** Every page found, whether read, and what it contributed or why it was set aside. Show it in chat at the end.
- **Surface conflicts.** Two sources disagreeing on a fact for the file go to the user before choosing; one that can't be settled is stated conservatively.
- **Test against what is established.** Before adding a behaviour or hazard from a report, check whether the file already explains it.

Done when searches stop producing new pages, every relevant page is read or reported unreadable, and the ledger is shown.

## 5. Depth

Produce every depth figure by the site conventions' Depth section: the seabed depth at the dive area, the depth range, and, where the region has a tide station, the station and its typical range.

## 6. Current

Produce every current figure by the site conventions' Current section.

- **Type.** As the region sets it, unless a specific site water behaves differently.
- **Local behaviour.** An eddy, a set along a wall, a turn in the shallows. Figures come from the region's method; behaviour may come from community sources.
- **Observation outranks the model.** A behaviour the existing file or the research describes from the water (a drift that ignores the tide, a set the extract doesn't show) stays in the prose even where the station or extract disagrees. Report the disagreement in chat; never resolve it by dropping the observation.
- **Missing figure.** Written as not established, and reported in chat.

## 7. Wind

Run the site conventions' Wind tool on the dive area coordinate, the one the Coordinates row will carry, and for a shore site also on the entry point, the one the Entry point coordinates row will carry; a boat site runs on the dive area alone. It gives the entry and dive area shore facings and the fetch from each of the 16 compass directions. A dive area coordinate it reads as on land goes back to step 3. The entry point is read against its nearest shore, so one on the beach is expected. Classify each of the 16 directions by the shore relation and fetch it prints:

| Relation | Fetch | Class |
|---|---|---|
| Onshore | 5 km or more | Bad |
| Onshore | 1 to 5 km | Short fetch |
| Onshore | Under 1 km | Fine |
| Cross-shore | 5 km or more | Mixed |
| Cross-shore | Under 5 km | Fine |
| Offshore | Any | Fine |

The thresholds come from fetch-limited wind wave growth (JONSWAP): at the wind tools' no-go speed, 1 km of fetch builds ripples and 5 km real chop. Swell is outside the table.

- **Sectors.** Adjacent directions in the same class form one sector, named clockwise end to end.
- **Calm only.** A site research shows dives only in calm whatever the direction (an exposed windward coast, a kite beach) classes every direction Bad, with the reason.
- **Local knowledge.** Research can move a direction up a class (Fine to Short fetch or Bad, Short fetch to Bad), never down, with the reason and a source: funnelling along a narrows or valley lake, swell wrapping a point. A wind note the existing file carries from observation stays in its bullet even where the class doesn't move.
- **Wind against current.** Take the set directions from the Current section (the site flood and ebb sets, or the usual set). An opposing wind blows from where the water flows toward, within 45° either side; name each one with 1 km or more of fetch and the set it opposes. A peak current under the region's threshold is too weak to stack against wind. Current type none: the water holds still, so wind alone sets the surface. Current type wind driven: leave the bullet out, since the wind sets the current itself. A tidal Current section with no set direction is a gap: stop and report it.

## 8. Write the file

Write the figures from steps 5 to 7 and the research from step 4 into the template, following its section order, rows and formats. Beyond it:

- **Type** is exactly Shore or Boat. Shore is anything reachable from land, however long the swim; Boat is only for no shore access at all. Swim distance, restrictions and guided-only rules go in Getting there.
- **Air fills and dive shops** go in the region file. Facilities names only what is physically at the site.
- **Every fact belongs**, whether from public data or repeated dives: coordinates, depths, station and bin, offset, current behaviour, entry, hazards, temperatures, life.

## 9. Bookkeeping

- **Region row.** Under "Sites currently covered" in `<region>.md`: the site name linking to `sites/<slug>.md`, and one sentence the way a guidebook index reads: where it is, its terrain and structure, its landmarks, its notable life, anything unique. Hazards, current, slack, skill level and access stay in the site file.
- **Map entry.** One object in `map/data.js`'s top-level `sites` array. `site` is the Coordinates row, never parking or entry; `type` is the Type row lowercased; `parking` and `entry` are their rows, `null` for a boat site.

  ```json
  {
    "slug": "<site-slug>",
    "name": "<site name>",
    "region": "<region folder slug>",
    "type": "shore" or "boat",
    "file": "regions/<region>/sites/<slug>.md",
    "site": { "lat": <lat>, "lon": <lon> },
    "parking": { "lat": <lat>, "lon": <lon> } or null,
    "entry": { "lat": <lat>, "lon": <lon> } or null
  }
  ```

- **Companion files.** Any the site conventions' Current section names, beside the site file, unless step 3 ruled the extraction out.

Keep the row and the map entry current whenever the site's coordinates, name, type, parking or entry change.

## 10. Independent audit

Launch a fresh `general-purpose` agent with the Agent tool. Give it the site file, `CLAUDE.md` and this skill, to read in full at audit time. It audits the site file's prose as written, and only the site file: it runs no tool, fetches nothing, and leaves every other file alone. It reports each finding with file, line, rule broken, text as written, and a proposed fix, checking:

- **Conventions.** `CLAUDE.md`'s Writing style, Units, Time and Depth, line by line over the site file.
- **Structure.** The site file against the template: every section in order, every required row and bullet present, each in its placeholder's format. Type reads exactly Shore or Boat, and Facilities names only what is physically at the site.
- **Depth, current and wind.** A figure the file lacks reads as not established. Every Bad, Short fetch and Mixed sector is named clockwise with its shorthand in parentheses and its fetch range. The wind against current bullet names a set the file's own Current section gives.
- **Consistency.** A fact stated twice (a depth, a distance, a bearing, a current strength) reads the same everywhere in the site file.
- **Claims to check.** A sentence that reads as one anecdote stated as fact, or a fact that looks carried over from a neighbouring site.

Then work the findings. Fix style, structure and consistency directly. Hold each flagged claim against the step 4 research: keep it if supported, restate it conservatively if partly supported, remove it if not. Report a table of findings in chat, each with what changed or why it stayed. The site is done when every finding is resolved.

## Template

Placeholder text says what each row or bullet holds. "Compass and degrees" means the compass point spelled out in lowercase and the bearing ("west-southwest, 247°"). A sector is spelled out with its shorthand in parentheses ("south through west (S-W)"). Depths are below the region's datum where it has one, otherwise observed.

```markdown
# Site Name

Two to five sentences: what the site is, where, its character, and its headline hazard.

| | |
|---|---|
| **Location** | Town, state, and the body of water |
| **Coordinates** | Decimal degrees of the dive area, with the seabed depth there in parentheses |
| **Parking coordinates** | Shore only: decimal degrees and a brief description |
| **Entry point coordinates** | Shore only: decimal degrees of where you step in, and a brief description |
| **Type** | Shore or Boat |
| **Depth range** | Shallowest to deepest dived |
| **Skill level** | Only if known |

## Getting there

* **Entry.** Where and how to get in the water.
* **Parking.** Where to leave the car, and cost.
* **Access.** Hours, distances, restrictions.
* **Facilities.** What is physically at the site.

## Navigation and landmarks

* **Topic.** Landmarks in order, each led by a bold topic.

## Site map

Optional, for a site with a mapped line or trail: a short description of how it runs and where the entry meets it, a diagram, and a table of features by distance along it with their datum depth.

## Current

Optional sentence on what dominates the current. Tidal and wind driven only.

| | |
|---|---|
| **Current type** | Tidal, Wind driven, or None |
| **Governing station** | Tidal: name, ID, and distance |
| **Recommended bin** | Tidal: number and depth |
| **Observed offset, slack before flood** | Tidal: minutes before or after the station, by the region's observed offset rule, or "Not established; slack should be confirmed in the water" |
| **Observed offset, slack before ebb** | Tidal: the same, for slack before ebb |
| **Station flood axis** | Tidal: compass and degrees |
| **Station ebb axis** | Tidal: compass and degrees |
| **Site flood set** | Tidal: the region's typical set at the dive area, compass and degrees, or "As the station" |
| **Site ebb set** | Tidal: the region's typical set at the dive area, compass and degrees, or "As the station" |
| **Usual set** | Wind driven: compass and degrees |
| **Typical speed** | Wind driven: range in m/s |

* **Flood.** Tidal: where it sets locally, and its daily peak speed range over the region's span, in m/s.
* **Ebb.** Tidal: where it sets locally, and its daily peak speed range over the region's span, in m/s.
* **Diveable window.** Tidal: which slack, its typical length under the region's threshold, and what narrows it.
* **Drivers.** Wind driven: the winds or seasons that strengthen or reverse the set.
* **Topic.** Further local behaviour, each led by a bold topic.

Optional, tidal only: "Legacy correction, carried as published and separate from the reconciled figures above:"

| | |
|---|---|
| **Legacy station** | Name, position, and distance and direction from the site, or "None; the reference is used directly" |
| **Legacy reference** | The reference station the correction was published against: name and ID |
| **Slack before flood** | Minutes before or after the reference, as published |
| **Slack before ebb** | Minutes before or after the reference, as published |

## Wind

| | |
|---|---|
| **Entry shore facing** | Shore only: compass and degrees |
| **Dive area shore facing** | Compass and degrees |

Optional prose on the shoreline's shape where the bearing alone doesn't carry it, from the tool output only.

* **Bad.** Each Bad sector, its fetch range ("over 8 to 19 km of open water"), and why it spoils the entry. Calm only: "all directions (N-NNW), calm only", with the reason.
* **Short fetch.** Each Short fetch sector, its fetch range, and why it spoils the entry.
* **Mixed.** Each Mixed sector, its fetch range, and the swell it runs past the entry.
* **Fine.** The Fine directions and what blocks them (a bluff, a headland, a breakwater).
* **Wind against current.** Tidal or none only: each opposing wind and the set it opposes, or that the current is too weak to stack, or that the water holds still.

## Depth and tide

Tidal regions only. One line on how much the tide swings the depth here.

| | |
|---|---|
| **Tide station** | Name, ID, and distance |
| **Series** | High and low water only, or full series |
| **Typical range** | Median and maximum daily range, and the year's span |

Optional table of features by datum depth, and how they read at a low and a high.

## Visibility

* **Topic.** What drives it, and when it runs best and worst, across seasons.

## Temperature

* **At depth.** Range through the year, and exposure protection.
* **Surface layer.** Only where it differs sharply from depth.

## Marine life

* **Topic.** What is seen, grouped by zone or type.

## Hazards

* **Topic.** Each hazard led by a bold topic.
```

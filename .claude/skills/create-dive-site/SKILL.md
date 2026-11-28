---
name: create-dive-site
description: This skill should be used when the user asks to create a new dive site file, write up a dive site, add a site to a region, document a new site, or substantially rewrite an existing site file in this scuba diving workspace. Covers opening a git worktree for the work, gathering the required inputs, loading that region's own conventions, verifying the coordinate against bathymetry, writing the site JSON, running research passes, working out the depth, current and wind sections by the region's site conventions, the bookkeeping a new site needs, a final independent audit of the site file's prose by a fresh agent, and committing and merging the work into main.
---

# Create a dive site file

Produce `regions/<region>/sites/<slug>.md` from the template at the bottom and its `<slug>.json` beside it, plus its bookkeeping, then have a fresh agent audit the prose. Most of the work is pinning numbers down against live sources; the writing comes last.

This skill holds what applies in every region: the order of the work, the workspace-wide tools and how each is used, the rules that turn tool output into the file, and the template. The workspace-wide tools are `depth.md`, `tide.md`, `current.md`, `shore_exposure.md`, `subsurface_log.md` and `diversatlas.md`, run in every region as the steps below say. The region's site conventions file holds only what is specific to the region: its datum, its current type, its own research sources and any tool used only there, how a tide station is chosen in its water, and the reaches that behave differently.

## Ground rules, for every step

- **Stop on a failed source.** A tool error, an unreachable API, a page that won't load or has only a broken archived copy: stop, tell the user what failed and what it was meant to provide, and wait. Never write the file around the gap or present it as complete.
- **Behaviour, never numbers, from community sources.** Their depths sit at an unrecorded tide and their slack times carry no station nor normalization.
- **Reasoning in chat, facts in the file.** Station checks, how sure a figure is, and conflicts between sources all go in chat. The file carries only the best figure produced.

## 0. Open a worktree

All work happens in a worktree on its own branch off `main`, opened before any file is touched. Run every command here from the root of the main checkout.

- **Main is clean.** Uncommitted changes in the main checkout to any of the four files below stop the run; ask the user to commit or discard them.
- **Create it, then link the ignored files.** Name it by region and slug, since a slug is unique only within its region; a leftover branch or folder of that name is reported, never reused or deleted. The worktree lacks the gitignored files the tools need, such as `tool-config.json` and `tools/db/`, so link each one in as git lists them, in one command:

  ```sh
  W=.claude/worktrees/<region>-<slug>; git worktree add "$W" -b site/<region>/<slug> main
  git ls-files --others --ignored --exclude-standard --directory | grep -v '^\.claude/worktrees/' |
    while read -r p; do p=${p%/}; mkdir -p "$W/$(dirname "$p")"; ln -s "$PWD/$p" "$W/$p"; done
  ```

- **Four files, no others.** Write only `regions/<region>/sites/<slug>.md`, `regions/<region>/sites/<slug>.json`, `map/data.js` and `regions/<region>/<region>.md`, all inside the worktree. A change anything else seems to need is reported in chat and left undone. Scratch files go outside the repository.

## 1. Required inputs

Ask and wait if any is missing; never guess.

- **Dive area coordinate.** A decimal-degree pair for the point underwater that is actually dived, or a source that pins it (a guidebook page, a described forum post, a named chart feature). With neither, ask before anything else.
- **Shore or boat.** A shore site also needs parking and entry point coordinates, or a clear source for them. A boat site needs neither.
- **Region.** Infer it only when the coordinate or the user's wording makes it unambiguous.

## 2. Load the region

Read both of these region files in full before anything else.

- **`<region>-site-conventions.md`.** The region's datum, current type, research sources, region-only tools and local rules. Use the workspace-wide tools as this skill says, and the region's own tools and sources the way the conventions say.
- **`<region>.md`.** The hydrography and any subarea that behaves differently.

## 3. Verify the coordinate and write the site JSON

- **Depth.** Check the seabed depth at the coordinate with `depth.md`, on the region's datum (`depth.py at <lat> <lon> --datum <K>`, with the datum name the site conventions' Depth section gives). If it is too deep or off the divable slope, walk it toward shore and re-check until its depth matches what the sources describe as dived; `transect` walks a line from the entry out to the dive area.
- **Site JSON.** Once the coordinate holds, write `<slug>.json` beside where the site file will go, for every site in every region: `lat` and `lon` are the coordinate, `tz` is the site's IANA time zone, `seabed_m` is the seabed depth there in metres, read with `depth.md` and expressed as the site conventions' Depth section sets it (below the region's datum, or a plain observed depth where it has none), and `seabed_datum` is that datum's name from `tools/lib/datums.py` (`MLLW`, `CHS`, `LAKE` or `NONE`), the one `depth.md` printed with the depth. The tide tool reads `seabed_datum` to refuse a station on another datum. The Coordinates row later states these same figures; the tools read them from the JSON. `depth.py at --file` checks `seabed_m` and `seabed_datum` together.

  ```json
  {
    "lat": <lat>,
    "lon": <lon>,
    "tz": "<IANA zone>",
    "seabed_m": <depth>,
    "seabed_datum": "<MLLW, CHS, LAKE or NONE>"
  }
  ```
  
## 4. Research

Three passes, each finished before the next starts.

### 4.1 Research tools

Run each of these, then every tool the site conventions' Region Specific Research section names. Done when each has produced its result or been reported as failed.

- **`subsurface_log.md`.** The site's dives, matched by name and logged position; a dive matching only one is checked, and confirmed with the user when unclear. Their depths, times, temperatures, visibility, current felt and notes feed every section.
- **`diversatlas.md`.** Found by the dive area coordinate: a second pin, entry, parking, landmarks, access, life and hazards.

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

Produce every depth figure on the region's datum, the one the site conventions' Depth section names, by the rules below and any region-specific rule the Depth section adds.

- **Seabed depth.** `depth.md` at the dive area coordinate, on the region's datum: the `seabed_m` step 3 wrote, stated in the Coordinates row.
- **Tide station.** On a tidal datum (`MLLW`, `CHS`), a `tide.md` station on that datum in the same body of water as the site, found with `stations --near --datum <K>`, its name and position verified; the site conventions add how a station is chosen in the region's own water. The station is a working input for the figures below and stays out of the site file. `LAKE` and `NONE` take no station, and their Depth section carries no Tide typical range or Tidal swing bullet.
- **Tide typical range.** `tide.md`'s `range` at the station for the current year: the median and the largest daily range, and the year's span, written as the Depth section's Tide typical range bullet.
- **Depth range.** The dive log's maximum depths and the research sources. On a tidal datum each logged maximum is normalized to the datum with `tide.md`'s `normalize` at the moment it was reached, taken from the dive's profile; on `LAKE` and `NONE` the logged depth stands as it is.
- **The arithmetic.** Tide height is signed, negative on a minus tide, and the same on every datum:

  ```
  depth below datum   =  observed depth (computer)  -  tide height at that moment
  depth below surface =  datum depth                +  predicted tide height
  ```

## 6. Current

Produce every current figure by the current type the site conventions' Current section names, the rules below, and any reach the Current section describes.

- **Extract.** Every site, whatever its current type: once the dive area coordinate holds, `current.md`'s `extract --site` on the site JSON, at the tool's default height above the seabed, attaches the site's constants. On `LAKE` the extract holds no tidal current, and every prediction from it is 0 m/s. A coordinate the tool refuses, on land or in water outside its coverage, stops the site: report it and wait.
- **Tidal.** The extract's predictions give the Flood, Ebb and Diveable window bullets: slack, set, peak speeds and the windows under the threshold. `subsurface_log.md` gives the set and strength actually felt at the site.
- **No station within reach.** Where `current.md`'s header reports no current station within reach, the prediction is the tidal database's own, and the prose states its timing as a starting point to verify on the day.
- **Wind driven.** The extract goes with the site JSON for planning, its tidal set a data point beside the wind. The Usual set and Drivers bullets come from the research sources' descriptions of the site and the log's own dives there, taken as behaviour and cross-checked between sources. A set no source pins to one direction is written in general terms (it runs either way along the reef, varying with the day); a bullet with nothing to say is dropped.

- **Type.** As the region sets it, unless a specific site water behaves differently.
- **In words.** The Current section describes the water from the research and the log: where it pushes, in compass points, and how it feels, in terms like ripping, steady or gentle.
- **Local behaviour.** An eddy, a set along a wall, a turn in the shallows, described in words.
- **Observation outranks the model.** A behaviour the existing file or the research describes from the water (a drift that ignores the tide, a set no tool shows) stays in the prose even where a tool disagrees. Report the disagreement in chat; never resolve it by dropping the observation.
- **Missing figure.** Left out of the file, or stated conservatively from what is known, and reported in chat under Gaps.

## 7. Wind

Run `shore_exposure.md` on the dive area coordinate, the one the Coordinates row will carry, and for a shore site also on the entry point, the one the Entry point coordinates row will carry; a boat site runs on the dive area alone. It gives the entry and dive area shore facings and the fetch from each of the 16 compass directions. A dive area coordinate it reads as on land goes back to step 3. The entry point is read against its nearest shore, so one on the beach is expected. Inside a lake it reads the lake's own shoreline. Any region-specific reading is in the site conventions' Wind section. Classify each of the 16 directions by the shore relation and fetch it prints:

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

## 8. Write the file

Write the figures from steps 5 to 7 and the research from step 4 into the template, following its section order, rows and formats. Beyond it:

- **Type** is exactly Shore or Boat. Shore is anything reachable from land, however long the swim; Boat is only for no shore access at all. Swim distance, restrictions and guided-only rules go in Getting there.
- **Skill level** is the diver's own call, made from the depth, current, entry and hazards the file describes; the file carries no rating of it. Prose may still note what a stretch of the site asks of a diver, as a hint.
- **Air fills and dive shops** go in the region file. Facilities names only what is physically at the site.
- **Every fact belongs**, whether from public data or repeated dives: coordinates, depths, current sets and speeds, current behaviour, entry, hazards, temperatures, life.

## 9. Bookkeeping

- **Region row.** Under "Sites currently covered" in `<region>.md`: the site name linking to `sites/<slug>.md`, and one sentence the way a guidebook index reads: where it is, its terrain and structure, its landmarks, its notable life, anything unique. Hazards, current, slack and access stay in the site file.
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

- **Site JSON.** The file step 3 wrote, with the current extract from step 6. Its `lat`, `lon` and `seabed_m` read exactly as the Coordinates row states them, and its `seabed_datum` names the region's datum.

Keep the row, the map entry and the site JSON current whenever the site's coordinates, seabed depth, name, type, parking or entry change.

## 10. Independent audit

Launch a fresh `general-purpose` agent with the Agent tool. Give it the site file, `CLAUDE.md` and this skill, to read in full at audit time. It audits the site file's prose as written, and only the site file: it runs no tool, fetches nothing, and leaves every other file alone. It reports each finding with file, line, rule broken, text as written, and a proposed fix, checking:

- **Conventions.** `CLAUDE.md`'s Writing style, Units, Time and Depth, line by line over the site file.
- **Structure.** The site file against the template: every section in order, every required row and bullet present, each in its placeholder's format. Type reads exactly Shore or Boat, and Facilities names only what is physically at the site.
- **Depth, current and wind.** The file carries no gap phrasing ("not established", "unknown", "not confirmed" or alike): a figure it lacks is left out or stated conservatively. Every Bad, Short fetch and Mixed sector is named clockwise with its shorthand in parentheses and its fetch range.
- **Consistency.** A fact stated twice (a depth, a distance, a bearing, a current strength) reads the same everywhere in the site file.
- **Claims to check.** A sentence that reads as one anecdote stated as fact, or a fact that looks carried over from a neighbouring site.

Then work the findings. Fix style, structure and consistency directly. Hold each flagged claim against the step 4 research: keep it if supported, restate it conservatively if partly supported, remove it if not. Report a table of findings in chat, each with what changed or why it stayed. The site is done when every finding is resolved.

## 11. Commit and merge

- **Commit.** In the worktree, stage the four files by path, confirm `git status` shows nothing else changed, and commit as `<region>: <site name>`, adding "rebuilt" for a rewrite.
- **Merge.** In the main checkout, on `main`: `git merge --no-edit site/<region>/<slug>`. Never push.
- **Conflicts.** In the region table or `map/data.js`, where each side changed a different site, keep both in the file's order and check `map/data.js` still parses. Any other conflict stops the merge: show the user both sides and wait.
- **Clean up.** `git worktree remove --force .claude/worktrees/<region>-<slug>` and `git branch -d site/<region>/<slug>`, then report the merge commit. First check `git -C <worktree> status --short --ignored` lists only step 0's symlinks; anything else stops the clean up and goes to the user. Other worktrees and `site/` branches are expected, since many sites are worked in parallel; remove only this run's own and leave every other one untouched, without listing or reporting them.

## 12. Summary

Close the run with a short summary in chat, after the merge, as bold-led bullets with one or two lines each.

- **Result.** The site, its coordinates, the merge commit, and the files changed.
- **Key data points.** The seabed depth, the depth range, the distances.
- **Key sections.** Depth, Current and Wind.
- **Decisions made.** Each conflict between sources and how it was settled.
- **Gaps.** Figures or information that was not established.
- **Sources used.** Source that contributed to the file and what did they contribute.

## Template

Placeholder text says what each row or bullet holds. A required row with no figure takes the conservative figure the bathymetry or research supports; an optional row or bullet with nothing to say is dropped. "Compass and degrees" means the compass point spelled out in lowercase and the bearing ("west-southwest, 247°"). A sector is spelled out with its shorthand in parentheses ("south through west (S-W)"). Depths are below the region's datum where it has one, otherwise observed.

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

## Getting there

* **Entry.** Where and how to get in the water.
* **Parking.** Where to leave the car, and cost.
* **Access.** Hours, distances, restrictions.
* **Facilities.** What is physically at the site.

## Navigation and landmarks

* **Topic.** Landmarks in order, each led by a bold topic.

## Site map

Optional, for a site with a mapped line or trail: a short description of how it runs and where the entry meets it, a diagram, and a table of features by distance along it with their datum depth.

## Depth

* **Tide typical range.** Tidal regions only: median and maximum daily range, and the year's span.
* **Tidal swing.** Tidal regions only: how much the tide swings the depth here.
* **Topic.** Further depth behaviour, each led by a bold topic: the bottom's profile, the working depth, how a feature reads at a low and a high, what the water level does to the entry.

Optional table of features by depth. The low and high columns are for tidal regions only, each headed with the tide height it reads at.

| Feature | Below <datum> | At a <height> m low | At a <height> m high |
|---|---|---|---|
| Feature name, and its distance or bearing where it helps | Depth below the datum | Depth below the surface at the low | Depth below the surface at the high |

## Current

Optional sentence on what dominates the current. Tidal and wind driven only.

* **Type.** Tidal, Wind driven, or None.
* **Flood.** Tidal: where it sets locally and how strongly it runs.
* **Ebb.** Tidal: the same, for the ebb.
* **Diveable window.** Tidal: which slack, how long it holds, and what narrows it.
* **Usual set.** Wind driven: where it sets and how strongly it runs.
* **Drivers.** Wind driven: the winds or seasons that strengthen or reverse the set.
* **Topic.** Further local behaviour, each led by a bold topic.

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

## Visibility

* **Visibility typical range.** The usual range in metres, and what drops it at its worst.
* **Topic.** What drives it, and when it runs best and worst, across seasons.

## Temperature

* **At depth.** Range through the year, and exposure protection.
* **Surface layer.** Only where it differs sharply from depth.

## Marine life

* **Topic.** What is seen, grouped by zone or type.

## Hazards

* **Topic.** Each hazard led by a bold topic.
```

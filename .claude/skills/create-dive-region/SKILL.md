---
name: create-dive-region
description: This skill should be used when the user asks to create a new region steering file, write up a diving region, add a region folder to the workspace, or document a new diving region. Covers identifying the region's extent, the mandatory deep research pass, following the canonical region template, and the bookkeeping a new region needs.
---

# Create a region file

Produce three files in `regions/<slug>/`, each matching its template at the bottom of this skill: `<slug>.md`, the region file; `<slug>-site-conventions.md`, what every site file here follows; and `<slug>-planning-conventions.md`, what every dive planned here is checked against. Plus a `sites/` subfolder that stays empty until the first site file is written into it, and the bookkeeping entries that make the region discoverable. This skill is almost entirely a research task and getting that research right is what makes every site written into this region afterward trustworthy.

## 1. Identify and size the region

A region is the extent over which one set of conventions holds: every site in it shares the same diving conditions, the same tools, and the same planning. Before researching in depth, decide whether the area the user named is that extent, or should be smaller or larger.

- **Name it.** If the user names a region too loosely to identify a specific, boundable body of water, ask which one before anything else. A region folder covers something nameable and bounded.
- **Test it against the conventions.** Across the whole area, check with a first pass of research: the same depth datum and tide source, or none; the same current type, worked out by the same method and tools; the same wind tool; and the same planning factors in the same order.
- **Too large.** If parts of the area fail that test (a tidal coast and an inland lake, an ocean-facing reach and a sheltered inlet that plan in a different order, a stretch outside the current model's coverage), propose splitting it along that line. A smaller difference that keeps the same tools and planning order stays inside the region as a named subarea section, the way a reach with its own slack behaviour does.
- **Too small.** If the area would share every convention with an existing region in `regions/` or its natural neighbours, propose widening it, or adding its sites to that existing region.
- **Grouping by conditions.** A region can group by conditions rather than geography, such as a state's deep lakes, as long as the conventions hold across all of it.
- **Confirm.** Present the proposed extent, what it includes and excludes, and the reason in conventions terms, and wait for the user before the full research pass.

## 2. Research pass — mandatory, deep, and done before drafting

This is the bulk of the work. Run a comprehensive web search, including region's own tourism board, parks or marine sanctuary authority, local dive shops, and regional dive forums.

Research should find at minimun:

- The region's geography: dimensions, how it connects to neighbouring water, and any sub areas, basins or reaches worth naming and placing.
- Typical water temperature through the year, at depth and at the surface if they diverge sharply, and what drives visibility here, with a sense of when it tends to run best or worst.
- The region's overall character. What kind of diving this is and what actually dominates conditions, tide, wind, open ocean swell, or something else. 
- What actually decides a dive here, for this region's own hydrography. For each factor that can end a dive, the value it ends it at, with enough research behind it to set its go, marginal and no go limits.
- The wind climate where the region is compact enough to have one, what blows, when, and which entries it blows offshore at, and where swell comes from. 
- The region's current type (tidal, wind driven, or none), the stations and model behind a tidal current, the local sources. 
- Which tools in `tools/` actually apply here, and to what: research, depth, current or wind for a site file, or a numbered condition in planning. And which websites (a regional forum, a site catalog, an archived guide, a park authority) belong in its research sources.
- Local dive shops and air fills.
- The local emergency number and every operating hyperbaric recompression chamber that could plausibly serve this region.

If a search turns up a page that looks relevant but won't load, an archived copy that's broken, or a fetch that's blocked, stop rather than writing the files around the gap. Tell the user what turned up and what wouldn't come through, and ask them to paste the content in, or confirm it's out of reach for them too, before continuing. Never present the files as complete over a gap like this, especially the emergency section: a wrong or missing chamber is not a cosmetic gap.

## 3. Write the files

Follow each file's template at the bottom of this skill for structure and section order. Omit a section the template marks optional only when the region genuinely has nothing for it. Name a tool by its file, `tool_name.md`, wherever it is used, never by its script or a command; the tool's own file holds how to run it. Every tool and source lives in the convention that uses it, under a **Tool** or **Tools** bullet, with one sub-bullet per item when there are several. Leave the "Sites currently covered" table with its header row only; the `create-dive-site` skill adds a row there the first time a site is written into this region.

## 4. Bookkeeping, once the files exist

A new region isn't done until it's discoverable from both places that index it. A row in the README's own "Regions currently covered" table: the region name linking to `regions/<slug>/<slug>.md`, and a brief description. An entry in `map/data.js`'s top-level `regions` object, keyed by the region's folder slug:

```json
"<region-slug>": {
  "name": "<region display name, matching the README table>",
  "file": "regions/<region-slug>/<region-slug>.md"
}
```

A site's `region` field is only a lookup key into this object; `map.html` reads a site's region name and steering-file link from here rather than deriving either from the slug. Keep both the README table and this entry current whenever a region is added or its display name or file path changes.

## Templates

One template per file. A conventions file that relies on a section of the region file (a subarea's own behaviour) links to it.

### `<slug>.md`, the region file

```markdown
# Region Name Dive Planning

## The region

Two to four sentences of plain prose: the body of water's geography, dimensions (length, width, depth, area if known), and how it connects to neighbouring water.

Optional table of sub areas, reaches or basins within the region, each row a name and roughly where it sits. Omit if the region has no meaningful internal divisions.

### Boundaries

Optional. Include only if this folder's coverage needs explaining: where it starts and stops and why, any water covered here that a stricter geographic definition would place elsewhere or exclude, and any wider collective name or neighbouring body of water this folder does not cover.

### A named subarea or topic

Optional, one section per subarea or region-wide topic that needs its own explanation beyond what Conditions and the conventions files can hold: a subarea that behaves differently enough from the rest of the region, or a region-wide topic significant enough to warrant its own space. Name the section after the subarea or topic itself, not "Subarea," and add as many of these as the region genuinely needs.

## Conditions

- **Water temperature.** Typical range at depth through the year, and the surface layer if it differs sharply.
- **Visibility.** What drives it, typical range, and when it tends to be best or worst.
- **Character.** The gestalt in a sentence or two: what kind of diving this is, and what dominates conditions here.

## Sites currently covered

| Site | Description |
|---|---|
| [Site Name](sites/slug.md) | One line, geographical and structural: what the site is and its character, short write-up. |

## Dive shops and air fills

Optional until real shops are known. Tank fill spots for this folder's sites, grouped by area if the region is large enough to need it.

- **Shop name, town.** Address. Phone. Website. What they fill (air, nitrox, trimix), and any caveat (limited hours, unconfirmed still open).

## Emergency

- **Local emergency.** The number, and any second line that reaches ambulance dispatch directly. Call EMS first, then DAN once the diver is stabilized and transport is underway.
- **[DAN (Divers Alert Network)](https://dan.org).** +1-919-684-9111, 24/7, collect calls accepted worldwide. Its Annual Diving Report and Incident Insights are the standing source for dive medicine, gear, procedure and debrief questions.
- **Chamber name, location.** One bullet per operating hyperbaric recompression chamber that could plausibly serve this region, nearest first, so there is a real alternative on hand if one is unreachable, closed, or unstaffed when it matters. How it's reached (through a hospital's own emergency room, a direct line, or both), and its distance or driving time from the region's own sites, especially a remote reach of it, since evacuation time is the safety-relevant fact. Note if it's restricted (military or otherwise not publicly accessible) rather than omitting it outright.
```

### `<slug>-site-conventions.md`, read when writing a site file

```markdown
# Region Name Site File Conventions

These conventions apply to every site file written in this region.

## Region Specific Research

Read in full for every site file.

- **Tools.**
  - `tool_name.md`, how the site is found in it, and what it gives a site file.
- **Sources.** Optional; omit when the region has no websites of its own.
  - [Source name](url), what it is and holds, and how to read it (a pinned archive snapshot, a Wayback Machine lookup).

## Depth

- **Datum.** The fixed datum depth is normalized to here and why, with the arithmetic for converting an observed depth to it and back; or "None", with the reason a plain observed depth is true here.
- **Tool** or **Tools.** Each tool behind a depth figure, with what it gives: the seabed depth at the dive area, the tide station and its typical range, the normalization of logged depths. Where no tool covers the region, the bullet that replaces it names where the depth range comes from.
- **Topic.** Optional, one bullet per region-specific rule: how a tide station is chosen, a reach where the bathymetry thins out.

## Current

- **Current type.** Tidal, wind driven, or none, with the reason for none.
- **Tool** or **Tools.** Each tool behind a current figure, with what it gives: a companion extract the site file carries, the station, bin, axes, peak speeds and windows, timed observations. Omit for a current type whose figures come from research alone.
- **Figure.** One bullet per figure the site skill's Current section requires for this type, naming how it is produced: how the station and its bin are chosen, how the offset is established, how a model cross-check is reconciled, the current threshold the window is measured against, and the wording for a figure no source gives.
- **Topic.** Optional, one bullet per reach that behaves differently from the rest of the region.

## Wind

- **Tool.** `shore_exposure.md`, and anything region-specific about how it reads here.
```

### `<slug>-planning-conventions.md`, read when planning a dive

```markdown
# Region Name Planning Conventions

These conventions apply to every dive planned in this region.

The factors that decide whether a dive goes well in this region, most important first, each with the limits a plan is checked against on the day. This ordering is specific to the region's own hydrography, an open, ocean-facing coast plans differently from a narrow, sill-bound inlet, and should be reasoned through for this region.

1. **Factor** (primary). Why it matters most here, and what any limit applies to (the working depth bin, the entry itself, the turn depth).
   - **Tool.** `tool_name.md`, what it reads for the plan, at both the entry and the exit time.
   - **Cross-check.** Optional, a second tool and how the two are reconciled.
   - **Go.** Under a stated value, and what the water is like there.
   - **Marginal.** The band between, and what it takes to dive it.
   - **No go.** Over a stated value, and why.
   - **Adjustment.** Optional, one bullet per adjustment the region needs: a sheltered or exposed class of site, a season that moves the value.
2. **Factor** (secondary).
3. **Factor** (informational). Sets expectations and gear.

Alongside the conditions, every plan carries:

- **Topic.** One bullet per tool a plan uses outside the numbered factors, with what it gives: depth below the surface across the dive, the site's past dives, the observed row once logged.

Optional, local rules that bind every dive here, after the list: permits and fees, marine park conduct and gear rules, areas closed to diving, required gear hygiene.
```

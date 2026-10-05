---
name: create-dive-region
description: This skill should be used when the user asks to create a new region steering file, write up a diving region, add a region folder to the workspace, or document a new diving region. Covers identifying the region's extent, the mandatory deep research pass, following the canonical region template, and the bookkeeping a new region needs.
---

# Create a region file

Produce one `regions/<slug>/<slug>.md` file, matching the template at the bottom of this skill, plus a `sites/` subfolder that stays empty until the first site file is written into it, and the bookkeeping entries that make the region discoverable. This skill is almost entirely a research task and getting that research right is what makes every site written into this region afterward trustworthy.

## 1. Required input — stop and ask if it's missing

Do not guess which body of water this is. If the user names a region loosely without enough to identify a specific, boundable body of water, stop and ask which one before researching anything. A region folder has to cover something nameable and bounded.

## 2. Research pass — mandatory, deep, and done before drafting

This is the bulk of the work. Run a comprehensive web search, including region's own tourism board, parks or marine sanctuary authority, local dive shops, and regional dive forums.

Research should find at minimun:

- The region's geography: dimensions, how it connects to neighbouring water, and any sub areas, basins or reaches worth naming and placing.
- Typical water temperature through the year, at depth and at the surface if they diverge sharply, and what drives visibility here, with a sense of when it tends to run best or worst.
- The region's overall character. What kind of diving this is and what actually dominates conditions, tide, wind, open ocean swell, or something else. 
- What actually decides a dive here, for this region's own hydrography. For each factor that can end a dive, the value it ends it at, with enough research behind it to set its go, marginal and no go limits.
- The wind climate where the region is compact enough to have one, what blows, when, and which entries it blows offshore at, and where swell comes from. 
- The region's current type (tidal, wind driven, or none), the stations and model behind a tidal current, the local sources. 
- Which tools in `tools/` actually apply here, and which websites (a regional forum, a site catalog, an archived guide, a park authority) belong in its Web Sources. 
- Local dive shops and air fills.
- The local emergency number and every operating hyperbaric recompression chamber that could plausibly serve this region.

If a search turns up a page that looks relevant but won't load, an archived copy that's broken, or a fetch that's blocked, stop rather than writing the file around the gap. Tell the user what turned up and what wouldn't come through, and ask them to paste the content in, or confirm it's out of reach for them too, before continuing. Never present the file as complete over a gap like this, especially the emergency section: a wrong or missing chamber is not a cosmetic gap.

## 3. Write the file

Follow the template at the bottom of this skill for structure and section order. Omit a section the template marks optional only when the region genuinely has nothing for it. Leave the "Sites currently covered" table with its header row only; the `create-dive-site` skill adds a row there the first time a site is written into this region.

## 4. Bookkeeping, once the file exists

A new region isn't done until it's discoverable from both places that index it. A row in the README's own "Regions currently covered" table: the region name linking to `regions/<slug>/<slug>.md`, and a brief description. An entry in `map/data.js`'s top-level `regions` object, keyed by the region's folder slug:

```json
"<region-slug>": {
  "name": "<region display name, matching the README table>",
  "file": "regions/<region-slug>/<region-slug>.md"
}
```

A site's `region` field is only a lookup key into this object; `map.html` reads a site's region name and steering-file link from here rather than deriving either from the slug. Keep both the README table and this entry current whenever a region is added or its display name or file path changes.

## Template

```markdown
# Region Name Dive Planning

## The region

Two to four sentences of plain prose: the body of water's geography, dimensions (length, width, depth, area if known), and how it connects to neighbouring water.

Optional table of sub areas, reaches or basins within the region, each row a name and roughly where it sits. Omit if the region has no meaningful internal divisions.

### Boundaries

Optional. Include only if this folder's coverage needs explaining: where it starts and stops and why, any water covered here that a stricter geographic definition would place elsewhere or exclude, and any wider collective name or neighbouring body of water this folder does not cover.

### A named subarea or topic

Optional, one section per subarea or region-wide topic that needs its own explanation beyond what Conditions and Planning conventions can hold: a subarea that behaves differently enough from the rest of the region, or a region-wide topic significant enough to warrant its own space. Name the section after the subarea or topic itself, not "Subarea," and add as many of these as the region genuinely needs.

## Conditions

- **Water temperature.** Typical range at depth through the year, and the surface layer if it differs sharply.
- **Visibility.** What drives it, typical range, and when it tends to be best or worst.
- **Character.** The gestalt in a sentence or two: what kind of diving this is, and what dominates conditions here.

## Tools

The following tools should be used in this region:

- tool_name.md

List only the tools this region actually uses.

## Web Sources

The following web sources should be used in this region:

- **[Source name](url).** One or two sentences, stating what it is and holds, and how to read it (a pinned archive snapshot, a Wayback Machine lookup).

List only the websites this region actually uses.

## Site file conventions

Open with "These conventions apply to every site file written in this region." Then what every site file in this region carries beyond the site template (a tide station, a companion current extract), and which fixed datum, if any, depth is normalized to here and why (the workspace has no default datum to fall back on). Where a datum applies, include the arithmetic for converting an observed depth to it and back, the same way the tide tool's own worked example does, and how a site's tidal range figures are derived.

The region's current type (tidal, wind driven, or none) and the method that produces each figure the site skill's Current section requires for that type: the tool, station or source behind it, how a station and its bin are chosen, how an offset is established, how a model cross-check is reconciled, and the current threshold the diveable window is measured against.

## Planning conventions

Open with "These conventions apply to every dive planned in this region." Then the factors that decide whether a dive goes well in this region, most important first, each with the limits a plan is checked against on the day. This ordering is specific to the region's own hydrography, an open, ocean-facing coast plans differently from a narrow, sill-bound inlet, and should be reasoned through for this region.

1. **Factor** (primary). Why it matters most here, and the concrete step to check it: the tool, station, forecast or observation that reads it, read at both the entry and the exit time, and what any limit applies to (the working depth bin, the entry itself, the turn depth). A factor that can end a dive carries its limits beneath it:
   - **Go.** Under a stated value, and what the water is like there.
   - **Marginal.** The band between, and what it takes to dive it.
   - **No go.** Over a stated value, and why.
   - **Adjustment.** Optional, one bullet per adjustment the region needs: a sheltered or exposed class of site, a season that moves the value.
2. **Factor** (secondary).
3. **Factor** (informational). Sets expectations and gear.

Optional, local rules that bind every dive here, after the list: permits and fees, marine park conduct and gear rules, areas closed to diving, required gear hygiene.

## Sites currently covered

| Site | Description |
|---|---|
| [Site Name](sites/slug.md) | One line, geographical and structural: what the site is and its character, short write-up. |

## Dive shops and air fills

Optional until real shops are known. Tank fill spots for this folder's sites, grouped by area if the region is large enough to need it.

- **Shop name, town.** Address. Phone. Website. What they fill (air, nitrox, trimix), and any caveat (limited hours, unconfirmed still open).

## Emergency

The local emergency number, then every operating hyperbaric recompression chamber that could plausibly serve this region, nearest first, so there is a real alternative on hand if one is unreachable, closed, or unstaffed when it matters. Call local EMS first, then DAN, once the diver is stabilized and transport is underway, not instead of it.

- **Chamber name, location.** How it's reached (through a hospital's own emergency room, a direct line, or both), and its distance or driving time from the region's own sites, especially a remote reach of it, since evacuation time is the safety-relevant fact. Note if it's restricted (military or otherwise not publicly accessible) rather than omitting it outright.
```

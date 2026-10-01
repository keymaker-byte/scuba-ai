---
name: create-dive-region
description: This skill should be used when the user asks to create a new region steering file, write up a diving region, add a region folder to the workspace, or document a new diving region. Covers identifying the region's extent, the mandatory deep research pass (geography, conditions, which tools apply, whether a fixed depth datum applies and its conversion arithmetic, how planning works there, dive shops, and emergency chambers), following the canonical region template, and the bookkeeping a new region needs (the README's "Regions currently covered" table and map/data.js).
---

# Create a region file

Produce one `regions/<slug>/<slug>.md` file, matching the template at the bottom of this skill, plus a `sites/` subfolder that stays empty until the first site file is written into it, and the bookkeeping entries that make the region discoverable (README table, map data). This skill is almost entirely a research task and getting that research right is what makes every site written into this region afterward trustworthy.

## 1. Required input — stop and ask if it's missing

Do not guess which body of water this is. If the user names a region loosely (a coastline, a vague area, a country with many diveable coasts) without enough to identify a specific, boundable body of water, stop and ask which one before researching anything. A region folder has to cover something nameable and bounded, not an open-ended area that could mean several different things.

## 2. Research pass — mandatory, deep, and done before drafting

This is the bulk of the work. The template below only has blanks; filling them with anything less than researched, cross-checked facts is how a region file goes stale on day one, and every site written under it inherits that gap. Cover, at minimum, the following, and run a comprehensive web search beyond the standing tool list for all of it: a region's own tourism board, a park or marine sanctuary authority, a local dive shop's site, and a regional dive forum each carry facts none of the fixed sources do.

The region's geography: dimensions, how it connects to neighbouring water, and any sub areas, basins or reaches worth naming and placing. Typical water temperature through the year, at depth and at the surface if they diverge sharply, and what drives visibility here, with a sense of when it tends to run best or worst. The region's overall character in a sentence or two: what kind of diving this is and what actually dominates conditions, tide, wind, open ocean swell, or something else, since that answer drives most of what follows. Which tools in `tools/` actually apply here. The order of factors that actually decide whether a dive goes well here, reasoned through for this region's own hydrography, an open ocean-facing coast plans differently from a narrow sill-bound inlet, rather than copied from another region's ordering. Local dive shops and air fills where they're actually known and verifiable; leave the section for later rather than fabricating one if nothing concrete turned up. The local emergency number and every operating hyperbaric recompression chamber that could plausibly serve this region, nearest first, with how it's reached (through a hospital's own emergency room, a direct line, or both) and its distance or driving time from the region's own sites, especially a remote reach of it, noting any chamber that's restricted (military or otherwise not publicly accessible) rather than omitting it outright.

If a search turns up a page that looks relevant but won't load, an archived copy that's broken, or a fetch that's blocked, stop rather than writing the file around the gap. Tell the user what turned up and what wouldn't come through, and ask them to paste the content in, or confirm it's out of reach for them too, before continuing. Never present the file as complete over a gap like this, especially the emergency section: a wrong or missing chamber is not a cosmetic gap.

## 3. Write the file

Follow the template at the bottom of this skill for structure and section order. Omit a section the template marks optional (Boundaries, a named subarea, the depth-by-tide table, Dive shops and air fills) only when the region genuinely has nothing for it, never as a shortcut past the research above. Leave the "Sites currently covered" table with its header row only; the `create-dive-site` skill adds a row there the first time a site is written into this region. Follow the workspace's Writing style, Units, Time and Depth conventions in `CLAUDE.md` for everything that goes in the file.

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

Optional, one section per subarea or region-wide topic that needs its own explanation beyond what Conditions and How planning works here can hold: a subarea that behaves differently enough from the rest of the region, or a region-wide topic significant enough to warrant its own space. Name the section after the subarea or topic itself, not "Subarea," and add as many of these as the region genuinely needs.

## Conditions

- **Water temperature.** Typical range at depth through the year, and the surface layer if it differs sharply.
- **Visibility.** What drives it, typical range, and when it tends to be best or worst.
- **Character.** The gestalt in a sentence or two: what kind of diving this is, and what dominates conditions here.

## Tools

The following tools should be used in this region:

- tool_name.md

List only the tools this region actually uses.

## Conventions

The local region conventions beyond the workspace default, and which fixed datum, if any, depth is normalized to here and why (the workspace has no default datum to fall back on). Where a datum applies, include the arithmetic for converting an observed depth to it and back, the same way the tide tool's own worked example does.


## How planning works here

Ordered by what actually decides whether a dive goes well in this region, most important first. This ordering is specific to the region's own hydrography, an open, ocean-facing coast plans differently from a narrow, sill-bound inlet, and should be reasoned through for this region.

1. **Factor** (primary). Why it matters most here, and the concrete step to check it: a tool, a station, a forecast.
2. **Factor** (secondary).
3. **Factor** (informational).

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

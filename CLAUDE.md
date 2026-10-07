# Scuba Diving

This workspace is for scuba diving planning.

## Region Files

A region is three steering files under `regions/<slug>/`, covering one bounded body of water over which one set of conventions holds, plus the `sites/` folder holding every site written under it:

- **`<slug>.md`.** The region file: geography, typical conditions, sites currently covered, dive shops and emergency.
- **`<slug>-site-conventions.md`.** The research, depth, current and wind conventions every site file in the region follows, with the tools and sources each one uses.
- **`<slug>-planning-conventions.md`.** The conditions every dive planned in the region is checked against, with the tool for each, and the local rules that bind it.

The region has a row in the README's own "Regions currently covered" table and an entry in `map/data.js`'s top-level `regions` object, keyed by the region's folder slug; `map.html` reads a site's region name and steering-file link from there rather than deriving either from the slug. Keep both current whenever a region is added or its display name or file path changes.

Creating a new region is handled by the `create-dive-region` skill: it holds the canonical template for all three files. Invoke it rather than freehanding them.

Important! Always read all three of the region's steering files, `<region>.md`, `<region>-site-conventions.md` and `<region>-planning-conventions.md`, whenever working on or referencing a region.

## Site Files

A site file is a single guidebook style `<slug>.md` under its region's `sites/` folder: coordinates, depth range, currents, entry, hazards, wind exposure, temperatures, and marine life, paired with a `<slug>.json` where the region has spatial current model coverage. It also has a row in its region file, under that file's "Sites currently covered" table, and an entry in `map/data.js`, the index `map.html` draws its pins from. Keep both current whenever a site is added or its coordinates, name, type, parking, or entry point change.

Creating a new site file, or substantially rewriting an existing one, is handled by the `create-dive-site` skill: it holds the canonical template. Invoke it rather than freehanding a site file.

Important! Always read all three of the region's steering files and the `<site>.md` file whenever working on or referencing a diving site.

## Map Files

`map.html`, with its supporting files under `map/`, is a local map viewer: every dive site plotted, colored by shore or boat access, with parking and entry point pins for shore sites. It reads `map/data.js`, the index of every site's coordinates and every region's display name and steering-file link, as a top-level `regions` object keyed by region folder slug plus a `sites` array; a site's `region` field is only a lookup key into that `regions` object, and `map.html` derives neither a region's name nor its file path from a slug, only from what's written there.

Populating `map/data.js` is handled by the `create-dive-region` and `create-dive-site` skills, each keeping its own part of it current (a region's entry in `regions`, a site's entry in `sites`) as part of creating or updating that region or site file. Invoke those rather than editing `map/data.js` by hand.

## Planning a dive

A dive plan is an entry-to-exit profile for a known site and date, checked against current, tide and wind at both ends of the dive, logged beside what was actually observed once the dive happens.

Planning a new dive, and logging one afterward, is handled by the `create-dive-plan` skill: it holds the planning workflow and the post-dive observed-row discipline. Invoke it rather than freehanding a plan.

## Tools

- @tool-config.json
- @tools/noaa_current.md
- @tools/noaa_tide.md
- @tools/adcirc_current.md
- @tools/ncei_depth.md
- @tools/emodnet_depth.md
- @tools/shore_exposure.md
- @tools/nws_forecast.md
- @tools/open_meteo_wind.md
- @tools/pnwdiving_viz.md
- @tools/subsurface_log.md
- @tools/diversatlas.md
- @tools/diveatlas.md

`tool-config.json` holds personal data and is gitignored, so a fresh clone of this workspace won't have it. If it's missing at session start, don't proceed, tell the user it's missing and ask them to copy `tool-config_template.json` to the real filename and fill it in, then continue once it exists.

Use these tools when writing a new region file, a new dive site file, planning a dive, or answering questions for the user. Each tool lives in `tools/`, one self-contained markdown file per tool (`tools/<name>.md`), paired with its `tools/<name>.py` script. Each tool reads its own parameters from its own subsection of `tool-config.json`. A region's two conventions files name the subset that region actually uses, so working a site narrows down to the right already-loaded tools rather than loading anything new.

If a tool errors out, an API is unreachable, or a site is down, stop and report it to the user rather than working around it. Never substitute a cached value, a plausible estimate, a different station, or a different bin to paper over the gap, and never present a plan or a site file as complete when a source it depends on failed. Say plainly what failed and what it was supposed to provide, and wait for the user before continuing. This matters because a plan built on partial data looks exactly like one built on complete data. A missing current window or a silently skipped tide check does not announce itself in the output, and by the time it matters it is a diver in the water holding a plan that was never actually checked.

## Units convention: use metric

- **Use metric.** Bar, metres, litres, celsius.
- **Do the arithmetic in metric.** Present results in metric, and don't append imperial conversions in parentheses unless asked. Gas planning in bar and litres, depth in metres, temperature in celsius, cylinder size in litres and working pressure in bar.

## Time convention: use the timezone of the dive site

- **Use local time zone.** Dive sites and planning should use the dive site local time zone. Never carry a UTC timestamp into a plan, a site file, or the log. This is a strict rule because slack, wind, and entry time are only useful against each other. A source silently read in the wrong zone or time shifts the slack window by 7 to 8 hours, which is obvious, or by exactly one hour across a DST boundary, which is not obvious and looks entirely plausible.

## Depth convention: normalize to a fixed datum

- **Depth is not a property of a site.** Where the water has a tide, the seabed is fixed but the surface is not, so an un-normalized depth is not comparable to any other dive at any other tide. Every depth worth keeping in a tidal region is normalized to a fixed datum, and never mixed with another. Which datum applies, and the arithmetic for it, is specific to whichever source produces that region's tide and current predictions, not a workspace-wide constant. That convention lives in the region's own site conventions file.
- **Not every region has a tide to normalize against at all.** A region may have no datum, in which case a plain observed depth is simply true.

## Diving conventions: NDL and EAN32

- **Non-decompression limits only.** Plan inside the no-decompression limit for the depth and gas on the day. Never plan a decompression dive.
- **EAN32 by default.** Assume EAN32 for planning unless the user specifies a different mix.

## Writing style: Clean like a book

- **State facts positively.** Say "is X," not "is X instead of Y" or "is X rather than Y." The same holds for plain negation: write what a thing is or does ("leaves the entry flat"), not what it isn't or doesn't ("does not count against the entry"). Keep a contrast only when the alternative is one a reader would otherwise plausibly assume and naming it corrects something real; drop it when it adds nothing the positive statement didn't already say.
- **No bold text inside paragraphs.** Bold is reserved for a bullet's lead topic and a table's left column.
- **No manual line breaks inside a paragraph or bullet.** Write each one as a single unbroken line in the markdown source, however long, and let the renderer wrap it. A hard break splits a sentence that was never meant to be split, and turns a later one-clause edit into a diff of the whole paragraph.
- **Avoid the dash as a connector or separator.** Use commas, periods, parentheses, or "to" for a range. Genuine hyphens in names and compound words are fine.
- **State a fact flatly.** No confidence flags, no source attributions (a book, the forums, our own log), no logged dive stats standing in for a fact (dive counts, runtimes, a specific dive number, a computer bookmark). A derived number is written as a plain fact; a number you're unsure of is stated conservatively.
- **Write like an entry in a public dive guidebook.** Factual, readable, and useful to any diver preparing for the region or site, not a page of our own notes.
- **A site file stands alone.** Never reference another site by name as a comparison or shorthand; describe the behavior itself.

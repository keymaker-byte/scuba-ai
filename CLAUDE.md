# Scuba Diving

This workspace is for scuba diving planning and data analysis.

## Workspace structure

- `diver-profile.json` holds the user's specific diver profile and personal data.
- `tool-config.json` holds per-tool parameters, one subsection per tool in `tools/`.
- `plan_log.csv` holds dive plans vs observed data.
- Each diving region is a folder under `regions/` holding one `<region>.md` steering file and a `sites/` subfolder containing `<site>.md` files.
- `map.html`, with its supporting files under `map/`, is a local map viewer. It reads `map/data.js`, the index of every site's coordinates.

## Session Context

Import these companion files into context:

- @diver-profile_template.json
- @tool-config_template.json
- @plan_log_template.csv
- @diver-profile.json
- @tool-config.json
- @plan_log.csv

`diver-profile.json`, `tool-config.json` and `plan_log.csv` hold personal data and are gitignored, so a fresh clone of this workspace won't have them. If any is missing at session start, don't proceed, tell the user it's missing and ask them to copy the matching `diver-profile_template.json`, `tool-config_template.json` or `plan_log_template.csv` to the real filename and fill it in, then continue once it exists.

Important! Always read the corresponding `<region>.md` steering file and the `<site>.md` steering file whenever working on or referencing a diving site.

Important! Always read the corresponding `<region>.md` steering file whenever working on or referencing a region.

## Sources and tools

Use these sources when writing a new dive site file, planning a dive, or answering questions for the user. Each tool lives in `tools/`, one self-contained markdown file per tool (`tools/<name>.md`), paired with a `tools/<name>.py` script when the tool has one. Each tool reads its own parameters from its own subsection of `tool-config.json`. All of them load into context at session start, below; a region's steering file lists only the subset that region actually uses, so working a site narrows down to the right already-loaded tools rather than loading anything new.

- @tools/noaa_current.md
- @tools/noaa_tide.md
- @tools/adcirc_current.md
- @tools/ncei_depth.md
- @tools/emodnet_depth.md
- @tools/nws_forecast.md
- @tools/open_meteo_wind.md
- @tools/pnwdiving_viz.md
- @tools/subsurface_log.md
- @tools/dan.md
- @tools/scubaboard.md
- @tools/nwdiveclub.md
- @tools/theperfectdive.md

If a tool errors out, an API is unreachable, or a site is down, stop and report it to the user rather than working around it. Never substitute a cached value, a plausible estimate, a different station, or a different bin to paper over the gap, and never present a plan or a site file as complete when a source it depends on failed. Say plainly what failed and what it was supposed to provide, and wait for the user before continuing. This matters because a plan built on partial data looks exactly like one built on complete data. A missing current window or a silently skipped tide check does not announce itself in the output, and by the time it matters it is a diver in the water holding a plan that was never actually checked.

## Units convention: use metric

- **Use metric.** Bar, metres, litres, celsius.
- **Do the arithmetic in metric.** Present results in metric, and don't append imperial conversions in parentheses unless asked. Gas planning in bar and litres, depth in metres, temperature in celsius, cylinder size in litres and working pressure in bar.

## Time convention: use the timezone of the dive site

- **Use local time zone.** Dive sites and planning should use the dive site local time zone. Never carry a UTC timestamp into a plan, a site file, or the log. This is a strict rule because slack, wind, and entry time are only useful against each other. A source silently read in the wrong zone or time shifts the slack window by 7 to 8 hours, which is obvious, or by exactly one hour across a DST boundary, which is not obvious and looks entirely plausible.

## Depth convention: normalize to a fixed datum

- **Depth is not a property of a site.** Where the water has a tide, the seabed is fixed but the surface is not, so an un-normalized depth is not comparable to any other dive at any other tide. Every depth worth keeping in a tidal region is normalized to a fixed datum, and never mixed with another. Which datum applies, and the arithmetic for it, is specific to whichever source produces that region's tide and current predictions, not a workspace-wide constant. That convention lives in the region's own steering file.
- **Not every region has a tide to normalize against at all.** A region may have no datum, in which case a plain observed depth is simply true.

## Writing style

- **State facts positively.** Say "is X," not "is X instead of Y" or "is X rather than Y." Keep a contrast only when the alternative is one a reader would otherwise plausibly assume and naming it corrects something real; drop it when it adds nothing the positive statement didn't already say.
- **No bold text inside paragraphs.** Bold is reserved for a bullet's lead topic and a table's left column.
- **Avoid the dash as a connector or separator.** Use commas, periods, parentheses, or "to" for a range. Genuine hyphens in names and compound words are fine.
- **State a fact flatly.** No confidence flags, no source attributions (a book, the forums, our own log), no logged dive stats standing in for a fact (dive counts, runtimes, a specific dive number, a computer bookmark). A derived number is written as a plain fact; a number you're unsure of is stated conservatively.
- **Write like an entry in a public dive guidebook.** Factual, readable, and useful to any diver preparing for the region or site, not a page of our own notes.

## Region Files

The canonical structure is `region_template.md`.

Every region needs a row in the README's own "Regions currently covered" table: the region name linking to `regions/<slug>/<slug>.md`, and a brief description. Keep this table current.

A region also needs an entry in `map/data.js`'s top-level `regions` object, keyed by the region's folder slug:

```json
"<region-slug>": {
  "name": "<region display name, matching the README table>",
  "file": "regions/<region-slug>/<region-slug>.md"
}
```

A site's `region` field is only a lookup key into this object; `map.html` reads a site's region name and steering-file link from here rather than deriving either from the slug. Keep this entry current.

## Site Files

The canonical structure is `site_template.md`.

A site file also needs a row in its region's steering file, under that file's "Sites currently covered" table: the site name linking to `sites/<slug>.md`, plus a brief one-line description. Keep this table current.

**Type is exactly "Shore" or "Boat", nothing else.** Shore is anything reachable from land, however long the surface swim. Boat only applies when there is no shore access at all. Don't qualify it ("Boat or shore", "Shore, guided only", "Boat, shore or snorkel"); a surface swim distance, an access restriction, or a guided-only requirement belongs in Getting There, not folded into the Type value.

A site file also needs an entry in `map/data.js`, the index `map.html` draws its pins from. It is a single `window.MAP_DATA = { "sites": [...] };` assignment; add one object to the `sites` array:

```json
{
  "slug": "<site-slug>",
  "name": "<site name, as the file's H1, without any numbering prefix>",
  "region": "<region folder slug>",
  "type": "shore" or "boat",
  "file": "regions/<region>/sites/<slug>.md",
  "site": { "lat": <dive site latitude>, "lon": <dive site longitude> },
  "entry": { "lat": <entry latitude>, "lon": <entry longitude> } or null
}
```

`site` is the dive site's own coordinate, the same one in the file's Coordinates row, never the entry point. `type` is `"shore"` or `"boat"`, lowercased from the file's Type row. `entry` is only set when the site is shore-accessed and the Coordinates row gives a separate entry coordinate; leave it `null` for a boat-only site or a shore site with no separate entry coordinate on file. Keep this file current.

A coordinate handed to you for a new site is a first reference. Check its seabed depth before writing anything; a point mid-channel or off the drop is not the dive. If it is too deep, or off the divable slope, walk it toward shore and re-check, comparing candidate depths against the source description (a guidebook, community reports, the site's own terrain narrative) until the coordinate's depth matches what is actually described as being dived. It also has to stay inside the coverage of the region's spatial current model, where it has one: extracting a prediction at the coordinate reports whether the point landed inside the model's domain and how far outside it sits when it didn't, and a coordinate walked too close to shore can fall outside that coverage or snap to its boundary, which reads as near-still water rather than the site's real current. Don't walk it past that edge; if the divable depth and model coverage conflict, keep the coordinate on the covered side and note the shallower part of the dive separately. Extract the spatial current prediction and pick the governing current and tide stations against that corrected coordinate, not the original.

Initial dive guides are a standing source for a new site file: site-specific current behaviour and entries, hazards, marine life, and access, spanning shore dives as well as boat access to sites further afield. Their figures are dated, so re-derive every current and depth figure against a live source before it enters a site file. Verify access, parking, fees, and closures against a recent report. Referenced stations can be legacy: a stated correction is against a current station that may no longer publish predictions, and an offset is only meaningful against the station it was derived from. Do not apply an offset to a modern station; that is how you end up in the water at max ebb holding a plan that says slack. Per site, pick the governing modern station, establish our own offset to it.

Creating a site file draws on every source and tool that applies, and beyond them always run a comprehensive web search for the site by name. Sources outside the fixed list, a dive shop's site page, a forum thread, a recent trip report, an incident writeup, turn up facts none of the standing sources carry alone (an access change, a renamed park, a hazard). Don't stop at the standing source list; go find what's out there. If that search turns up a page that looks relevant but won't load, an archived copy that's broken, or a fetch that's blocked, stop rather than writing the file around the gap: tell the user what turned up and what wouldn't come through, and ask them to paste the content in, or confirm it's out of reach for them too, before continuing.

Keep the facts, drop the bookkeeping. A fact goes in a site file whether it came from public data or from what we saw over repeated dives: coordinates, depth ranges, the governing current station and its bin, the offset, current behaviour, entry, hazards, temperatures, marine life. See Writing style for how each one is written.

The confidence work still happens, it just doesn't live in the file. Verify a station still publishes, verify the tide station's name and position, reason through the offset and how sure you are of it. Reasoning belongs in the chat; the site file carries only the best number it produced.

Air fills and dive shops belong in the region's steering file. A site's Facilities row names what's at the site itself.

## Plan log

The canonical structure is `plan_log_template.csv`.

`plan_log.csv` records every dive planned, with what we predicted beside what was actually observed. One row per record; two rows per plan, predicted and observed, distinguished by the `record_type` column and sharing the same `plan_id`.

`plan_log.csv` is CSV format, UTF-8 with a BOM (`utf-8-sig`). The BOM is what makes Excel read the accents, arrows and degree signs (`°`, `−`, `→`, `≈`) correctly on a double-click; keep writing it. If a session regenerates the file, write it with `encoding="utf-8-sig"`.

What goes in each of the 40 columns lives in `plan_log_template.csv` itself, as the row directly below the header: read that row before filling in a column rather than guessing from its name. It also marks which columns are model or forecast output with nothing aboard to re-measure them by (no anemometer, no thermometer, no station readout at depth) and so stay predicted-only, left blank on the observed row.

### How to use it

1. **Before the dive:** Append the `predicted` row. Fill the predicted fields completely, including the things we're unsure about (put the uncertainty in the matching `*_note` column, not the typed one).

When creating a new plan, follow these rules:

- **Non-decompression only.** Plan inside the no-decompression limit for the depth and gas on the day. Never plan a decompression dive.
- **Safety stop, always.** Every plan carries a stop before surfacing, whatever the profile.
- **EAN32 by default.** If the diver holds an Enriched Air certification, assume EAN32 for planning. Without that certification, or with no mix specified, assume Air.
- **Never plan the return against the current.** Order the excursion so the leg back to the entry point runs with the current or through slack, never against it. Where the governing current sets a known direction after slack, work the far leg first, upstream of the entry, and turn for home before the current builds against a return swim; a plan that has the diver kicking home into a developing current is a planning failure, not a detail to note afterward.
- **Check conditions at both ends of the dive.** Pull current, wind, and weather for the entry time and again for the exit time, not just once for the window as a whole. Current can build across the dive, wind can rise or shift, and fog or weather can move in while the diver is underwater; a plan that only checks conditions at entry misses exactly the change that would have changed the plan.

2. **After the dive:** Append (or fill) the `observed` row. A blank cell is fine where you didn't notice; never guess. A wrong entry here is worse than a missing one, because it gets averaged into an offset.

The three observations that matter most, because they're what the offsets are built from:

- Which way did the current set you, along the shore, and when (`set_direction`, `slack_note`).
- When did it actually go slack, the moment it was limpest, as best you can place it (`slack_time`, `slack_note`).
- What was the viz, at depth and in the shallows, separately (`viz_depth_*`, `viz_shallows_*`).

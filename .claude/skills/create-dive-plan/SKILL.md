---
name: create-dive-plan
description: This skill should be used when the user asks to plan a dive, create a dive plan, plan a dive at a site, or build an entry-to-exit profile. Covers identifying the site and date, loading the region's planning conventions, pulling every current estimate the site has for the entry and exit time, the wind, swell and tide checks, ordering the route so the return never fights the current, applying the workspace conventions, and presenting the plan in chat as a table plus a summary to share with dive buddies.
---

# Create a dive plan

Plan one dive at a known site on a known date, and present it in chat: a table of every figure the plan rests on, then a short summary written to be shared with the dive buddies. A plan is only as good as the sources it pulled from; this is a verification and sequencing task as much as a writing one.

## Ground rules, for every step

- **Stop on a failed source.** A tool error, an unreachable API, a source that is down: stop, say what failed and what it was meant to provide, and wait. Never substitute a cached value, an estimate, a different station or a different bin, and never present a plan as complete over a gap.

## 1. Required inputs

Ask and wait if either is missing; never guess.

- **Site.** A site file that already exists under `regions/<region>/sites/`.
- **Date,** and ideally a target entry time or window.

## 2. Load the site and region

Read the site file, `<region>-planning-conventions.md` and `<region>.md` in full before planning anything.

## 3. Build the plan

Follow the region's planning conventions in their own order: each factor, the tool that reads it, and how its estimates combine. Beyond them:

- **Both ends of the dive.** Every factor at the entry time and again at the exit time. Current builds, wind rises or shifts, and fog moves in while the diver is underwater.
- **Never return against the current.** Order the route so the leg back to the entry runs with the current or through slack. Where the current sets a known direction after slack, work the far leg first, up-current of the entry, and turn for home before the current builds against the return.
- **Wind.** A marginal call means a short surface swim only, with the entry and exit confirmed from shore before kitting up. A forecast direction in the site's Wind against current sectors while the current runs is noted beside the call.
- **Swell.** Breaking waves at the entry under 0.5 m are go, 0.5 to 1 m marginal, over 1 m no go.
- **The verdict.** A no go reading on any factor ends the plan at that site and time; a marginal one stays in the plan with the condition its band attaches.

## 4. Present the plan

Two parts, in chat.

**The table,** one row per item, every figure with its source:

| Item | What it holds |
|---|---|
| **Site and date** | Site name, region, date, and the day's exchange size |
| **Verdict** | Go, marginal or no go, and the factor that decides it |
| **Entry and exit** | Entry time, exit time, runtime |
| **Slack estimates** | Each available estimate on its own line: station, station with observed offset, model, legacy |
| **Diveable window** | The window from their overlap, its padding, and any estimates flagged as far apart |
| **Current at entry and exit** | Speed and set at each end, from the station and from the model |
| **Max flood and ebb** | The governing station's maxima bracketing the window, with times |
| **Wind** | Speed, direction and call at entry and exit, from each model, with the sector kind |
| **Swell and sea state** | The reading and its band |
| **Tide** | Height at entry and exit, and the depth below the surface of the site's main features |
| **Route** | The dive from entry to exit in order: the far leg, the turn, the return, the safety stop |
| **Depth, gas and NDL** | Planned maximum depth, the mix, and the no-decompression limit at that depth |
| **Visibility and temperature** | Recent visibility reports and the expected water temperature |
| **Weather** | Air temperature, sky, rain and fog |
| **Hazards on the day** | The site's hazards that apply to this plan, and any local rule that binds it |

**The buddy summary,** a few short paragraphs in plain language, ready to paste into a message: where and when to meet and enter, the verdict and why, the route and the turn, the depth and gas, the conditions to expect, and the two or three things everyone should watch for. No tool names, no station IDs, no model talk; the figures a diver needs, stated plainly.

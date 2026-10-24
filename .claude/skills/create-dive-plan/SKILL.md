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

Read the site file, its `<slug>.json` companion beside it in `sites/`, `<region>-planning-conventions.md` and `<region>.md` in full before planning anything.

## 3. Build the plan

Follow the region's planning conventions in their own order: each factor, the tool that reads it, and how its estimates combine. Beyond them:

- **Both ends of the dive.** Every factor at the entry time and again at the exit time. Current builds, wind rises or shifts, and fog moves in while the diver is underwater.
- **Never return against the current.** Order the route so the leg back to the entry runs with the current or through slack. Where the current sets a known direction after slack, work the far leg first, up-current of the entry, and turn for home before the current builds against the return.
- **Wind.** A marginal call means a short surface swim only, with the entry and exit confirmed from shore before kitting up. A forecast direction in the site's Wind against current sectors while the current runs is noted beside the call.
- **Swell.** Breaking waves at the entry under 0.5 m are go, 0.5 to 1 m marginal, over 1 m no go.
- **The verdict.** A no go reading on any factor ends the plan at that site and time; a marginal one stays in the plan with the condition its band attaches.
- **Divable Window.** Consider all factors that impact a divable window, suggest the best window to dive.
- **Doubts and Important Decicions.** In case of doubts or where a decision is needed, stop, present the options and ask the user to choose an option.

## 4. Present the plan


- **Format.** Follow the format below, present plan in chat.
- **Time Format.** For time use 12-hour clock system.
- **Directions Format.** For directions (current, wind) use a human readable format using the 8 Compass Points abbreviations.

---

**1. The Data.** A general table, and tables for entry and exit data.

| Item | |
|---|---|
| **Site and date** | Site name, region, date and dive time |
| **Site Summary** | Site summary, where to park, how to enter the water |
| **Diveable window** | The window from factors overlap, its padding, and any estimates flagged as far apart |
| **Verdict** | Go, marginal or no go, and the factor that decides it |
| **Time** | Time for meet, entry time, exit time, dive runtime |
| **Current** | Prediced current slack time closer to the dive, each source and final reconciliation |
| **Tide** | Predicted tide slack closer to the dive, size of the tide exchange comparable to the month |
| **Weather** | Wind conditions, air temperature, sky, rain and fog |
| **Visibility and temperature** | Recent visibility reports and the expected water temperature |
| **Route** | The dive from entry to exit in order: the far leg, the features and their depth, the turn, the return, the safety stop |
| **Hazards on the day** | The site's hazards that apply to this plan, and any local rule that binds it |

| Entry Factor | |
|---|---|
| **Time** | Entry time |
| **Current** | Speed and set at entry, each source and final reconciliation |
| **Tide** | Height at entry |
| **Wind** | Speed, direction and call at entry |
| **Swell and sea state** | The reading and its band at entry |

| Exit Factor | |
|---|---|
| **Time** | Exit time |
| **Current** | Speed and set at exit, each source and final reconciliation |
| **Tide** | Height at exit |
| **Wind** | Speed, direction and call at exit |
| **Swell and sea state** | The reading and its band at exit |

**2. The summary.** Create a dive plan summary including site description and bullet points using emojis to summarise each dive factor. Make it short and to the point, include resulting data (e.g. current speed/direction, wind speed/direction, deph, temperature, vizibility).

- **Title.** Site name, day and date, and the splash time.
- **Description.** One short paragraph: where the site is, the underwater scene and life, and any important rule.
- **Bullets.** Times, parking, entry, surface swim, current, tide, depth, wind, temperature, viz, route, watch for.

Follow the example below for the format.

```markdown
### 🤿 Example Reef: Sat 12 Jul, 9:30 AM

A low rock reef runs out from the beach at a small city park, a line of boulders crossing a sand slope into open water. Plumose anemones cover the tops of the rocks, with rockfish and greenling in the gaps, and sea pens and flounders on the sand either side. A second, deeper boulder pile lies 30 m past the end of the main reef. The site is a marine reserve, so look, don't take.

- ⏰ **Times:** meet 8:45 AM, in the water 9:30 AM, out 10:30 AM (60 min).
- 🚗 **Parking:** free street parking along the park road beside the picnic area. Restrooms by the lot.
- 🚶 **Entry:** follow the paved path down to the beach, then cross a short stretch of cobble to the water, easier on a higher tide.
- 🏊 **Surface swim:** about 100 m W, lined up on the flagpole, until rocks appear below. Descend there.
- 🌊 **Current:** slack around 10:05 AM on a small exchange, under 0.10 m/s for the whole dive towards SW.
- 🌙 **Tide:** high +3.20 m at 10:10 AM.
- 📏 **Depth:** 8 to 15 m along the reef, 18 m maximum at the outer pile.
- 💨 **Wind:** N at 2 to 3 m/s, offshore, gusts under 4 m/s, flat water. Go.
- 🌡️ **Temperature:** water about 11 °C, air 16 to 18 °C, sunny, dry.
- 👀 **Viz:** about 5 m (nearby site, 9 Jul).
- 🧭 **Route:** W at 270° along the reef, hold the bearing across the gap to the outer pile, turn by 10:00 AM, follow the reef E home, safety stop at 5 m.
- ⚠️ **Watch for:** boat traffic (fly a buoy), seals (keep 90 m away).
```
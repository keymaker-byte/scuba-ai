---
name: create-dive-plan
description: This skill should be used when the user asks to plan a dive, create a dive plan, plan a dive at a site, or build an entry-to-exit profile. Covers identifying the site and date, loading the region's planning conventions, the current prediction for the entry and exit time, the forecast's wind, waves, surface current, weather and warnings, the tide check, ordering the route so the return never fights the current, applying the workspace conventions, and presenting the plan in chat as a table plus a summary to share with dive buddies.
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

Read the site file, its `<slug>.json` companion beside it in `sites/`, and the region's three steering files, `<region>.md`, `<region>-site-conventions.md` and `<region>-planning-conventions.md`, in full before planning anything. The site conventions name the region's datum and current type, which set the checks below.

## 3. Build the plan

Follow the region's planning conventions in their own order: each factor, its limits, and the region-only tool that reads it, such as the visibility reports. The workspace-wide tools are read the same way in every region, each run with the site JSON as `--file` and the site's `tz` as `--tz`:

- **Current.** `current.md` on every site, read the same way at every site whatever its current type; how the plan uses the answer follows the type the region's site conventions name.
- **Current, tidal.** The day's slacks, sets and diveable windows at the bottom with `predict` and `window`, the fastest water above for the descent and ascent, and `at` at the entry and the exit time. A current prediction sets the slack; a tide station never does. Where the header reports no current station within reach, the plan states the slack as a starting point to confirm from the beach. This is the region's current factor, at the rank its planning conventions give it.
- **Current, wind driven.** `at` at the entry and the exit time gives the tidal set, a data point beside the wind outside the go / no go call. The plan gives its direction and notes whether it runs with the wind's drift, downwind, or against it.
- **Current, none.** A lake, on `LAKE`: `at` at the entry and the exit time answers 0 m/s, and the plan's Current rows state no tidal current.
- **Depth.** `tide.md`'s `project` on every site turns the site's datum depths into depth below the surface across the dive: depth below the surface is the datum depth plus the tide height. On a tidal datum (`MLLW`, `CHS`) it runs at a station on the site's datum in the same body of water, found with `stations --near --datum <K>` at the site's coordinate, its name and position verified and chosen by the region's site conventions, and `predict` gives the day's highs and lows; the tool refuses a station off the site's datum. On `LAKE` and `NONE` it runs with no station, and the tide height is 0.
- **Forecast.** `forecast.md` on every site, with the site JSON as `--file`, which reads the shore exposure written into its `wind` section with the site: `at` at the entry and the exit time, and `day` for the hour by hour picture behind the window. It answers in five blocks, each from the source that covers the site, and every block goes into the plan:
  - **Wind.** At the entry point (the dive area at a boat site), onshore, cross-shore or offshore there, with its call against the site's sectors. Where two models answer, the plan carries the more severe call.
  - **Waves.** At the dive area: the height, period and direction, the wind waves and the swell, with the call against the entry's shore. The reading is open water; where the tool flags its grid point as far, the plan names the distance and the swell is confirmed from the shore.
  - **Surface current and water temperature.** At the dive area, from an ocean model: the drift on the surface swim and the water temperature at the surface. The tidal current at the site is `current.md`'s, and this block never sets a slack. Where no ocean model holds the water, the water temperature is the region file's.
  - **Weather and temperature.** At the entry point: air temperature and what it feels like, sky, rain, visibility and fog, and thunder, with its call on fog and thunder.
  - **Hazards and warnings.** Every NWS alert in effect over the day for the zones holding the entry and the dive area, with the band it puts on the dive.
- **Past dives.** `subsurface_log.md`, the site's earlier dives: depths reached, notes, hazards hit, and how the current ran.

Beyond them:

- **Both ends of the dive.** Every factor at the entry time and again at the exit time. Current builds, wind rises or shifts, and fog moves in while the diver is underwater.
- **Never return against the current.** Order the route so the leg back to the entry runs with the current or through slack. Where the current sets a known direction after slack, work the far leg first, up-current of the entry, and turn for home before the current builds against the return.
- **Wind.** A marginal call means a short surface swim only, with the entry and exit confirmed from shore before kitting up.
- **Wind against current.** At the entry and at the exit, compare the forecast wind with the current's predicted set at that moment. A wind blowing from within 45° of the direction the current flows toward, from a direction outside the site's Fine sectors, while the current runs at or above the region's threshold, stands the chop up steeper and shorter than the wind alone: note it beside the wind call. A slower current, or a site whose current type is wind driven or none, has nothing to note.
- **Waves.** The forecast's waves call at the entry and the exit. The waves breaking at the entry are judged from the shore before kitting up against the same limits, `waves_go_below_m` and `waves_nogo_above_m` in `tool-config.jsonc`'s `forecast` section, and they decide over the forecast where the two differ.
- **Surface current.** Where the block reads, compare its set with the swim out the forecast's header prints: a drift across or against the surface swim lengthens it, and the plan says which way it carries a diver on the surface. In a region whose current is wind driven, it is the forecast of that current, beside the tidal set.
- **Fog and thunder.** The forecast's weather call at the entry and the exit.
- **Warnings.** The band the forecast puts on each alert in effect at the entry or the exit. A marginal or noted alert carries its headline beside the factor it concerns (a Coastal Flood Advisory on the entry and the parking, a Small Craft Advisory on the waves). An alert the tool marks as not about the water stays out of the plan.
- **The verdict.** A no go reading on any factor ends the plan at that site and time; a marginal one stays in the plan with the condition its band attaches.
- **Divable Window.** Consider all factors that impact a divable window, suggest the best window to dive.
- **Doubts and Important Decicions.** In case of doubts or where a decision is needed, stop, present the options and ask the user to choose an option.

## 4. Present the plan


- **Format.** Follow the format below, present plan in chat.
- **Time Format.** For time use 12-hour clock system.
- **Day Format.** Refer to the dive day by its day or date ("Saturday's tide", "on the day"). Use "today", "tonight" or "tomorrow" only for a dive on the calendar day of the session.
- **Directions Format.** For directions (current, wind) use a human readable format using the 8 Compass Points abbreviations.

---

**1. The Data.** A general table, and tables for entry and exit data.

| Item | |
|---|---|
| **Site and date** | Site name, region, date and dive time |
| **Site Summary** | Site summary, where to park, how to enter the water |
| **Diveable window** | The window from the factors' overlap and its padding |
| **Verdict** | Go, marginal or no go, and the factor that decides it |
| **Time** | Time for meet, entry time, exit time, dive runtime |
| **Current** | Predicted slack closest to the dive and its set either side |
| **Tide** | Predicted tide slack closer to the dive, size of the tide exchange comparable to the month |
| **Weather** | Wind across the dive, air temperature and what it feels like, sky, rain, fog and thunder |
| **Waves** | Height, period and direction, the swell, and the call, with the grid point's distance where it is flagged |
| **Surface current** | The ocean model's surface drift and its effect on the surface swim, where the block reads |
| **Warnings** | Every alert in effect over the dive with its band, or none |
| **Visibility and temperature** | Recent visibility reports, and the water temperature: the forecast's surface reading where it has one, the region file's otherwise |
| **Route** | The dive from entry to exit in order: the far leg, the features and their depth, the turn, the return, the safety stop |
| **Hazards on the day** | The site's hazards that apply to this plan, and any local rule that binds it |

| Entry Factor | |
|---|---|
| **Time** | Entry time |
| **Current** | Speed and set at entry, at the bottom and in the fastest water above |
| **Tide** | Height at entry |
| **Wind** | Speed, direction, gust and call at entry, and any wind against current |
| **Waves** | Height, period, direction and call at entry |
| **Weather** | Air temperature, sky, rain, fog and thunder at entry, and any warning in effect |

| Exit Factor | |
|---|---|
| **Time** | Exit time |
| **Current** | Speed and set at exit, at the bottom and in the fastest water above |
| **Tide** | Height at exit |
| **Wind** | Speed, direction, gust and call at exit, and any wind against current |
| **Waves** | Height, period, direction and call at exit |
| **Weather** | Air temperature, sky, rain, fog and thunder at exit, and any warning in effect |

**2. The summary.** Create a dive plan summary including site description and bullet points using emojis to summarise each dive factor. Make it short and to the point, include resulting data (e.g. current speed/direction, wind speed/direction, deph, temperature, vizibility).

- **Title.** Site name, day and date, and the splash time.
- **Description.** One short paragraph: where the site is, the underwater scene and life, and any important rule.
- **Bullets.** Times, parking, entry, surface swim, current, tide, depth, wind, waves, weather, temperature, viz, warnings, route, watch for. The warnings bullet is dropped when none is in effect.

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
- 🌊 **Waves:** under 0.2 m from the NW, 6 s period, offshore. Go.
- ☁️ **Weather:** sunny, dry, no fog or thunder.
- 🌡️ **Temperature:** water about 11 °C, air 16 to 18 °C, feels like 15 °C.
- 🚨 **Warnings:** Small Craft Advisory until 9 AM, lifting before the splash.
- 👀 **Viz:** about 5 m (nearby site, 9 Jul).
- 🧭 **Route:** W at 270° along the reef, hold the bearing across the gap to the outer pile, turn by 10:00 AM, follow the reef E home, safety stop at 5 m.
- ⚠️ **Watch for:** boat traffic (fly a buoy), seals (keep 90 m away).
```
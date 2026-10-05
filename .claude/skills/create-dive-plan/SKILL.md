---
name: create-dive-plan
description: This skill should be used when the user asks to plan a dive, create a dive plan, plan a dive at a site, build an entry-to-exit profile, or log a completed dive (fill in the observed half of a plan already logged). Covers identifying the site and date, pulling current, tide and wind for both the entry and exit time, ordering the route so the return never fights the current, applying the workspace's non-decompression and EAN32-by-default conventions, appending the predicted row to the plan log before the dive, and filling in the observed row afterward.
---

# Create a dive plan

Produce a `predicted` row in `tools/db/plan_log.csv`, matching the structure at the bottom of this skill, for a single dive at a known site and date, then its paired `observed` row once the dive happens. The log records every dive planned against what was actually observed: two rows per plan, `predicted` and `observed`, sharing a `plan_id` and distinguished by `record_type`. A plan is only as good as the sources it pulled from; this is a verification and sequencing task as much as a writing one.

## 1. Required inputs — stop and ask if any are missing

Do not guess either of these. Which site. It has to be a site file that already exists under `regions/<region>/sites/`; if the user hasn't named one, or named one ambiguously, ask. Once known, read that site's own `<slug>.md` and its region's `<region>.md` steering file in full before planning anything, the standing workspace rule, since the plan hangs off the current station, offset, datum and tool list fixed there, not guessed fresh per plan. The date, and ideally a target entry time or window. Current, tide and wind are all date-specific; nothing below can run without one.

## 2. Build the plan

Follow the region's own "Planning conventions" ordering: it fixes what actually decides a dive going well in that region, most important first, reasoned through for that region's hydrography, so this skill defers to it rather than imposing one planning order on every region. Pull the site's current as its Current section's type sets it (for a tidal site, its governing station, bin and offset, for slack and the diveable window across the candidate date), the tide where the region has one, and the region's wind tool at the entry's own coordinates.

Never plan the return against the current. Order the excursion so the leg back to the entry point runs with the current or through slack, never against it. Where the governing current sets a known direction after slack, work the far leg first, upstream of the entry, and turn for home before the current builds against a return swim; a plan that has the diver kicking home into a developing current is a planning failure, not a detail to note afterward.

Check conditions at both ends of the dive. Pull current, wind, and weather for the entry time and again for the exit time, not just once for the window as a whole. Current can build across the dive, wind can rise or shift, and fog or weather can move in while the diver is underwater; a plan that only checks conditions at entry misses exactly the change that would have changed the plan.

Check the plan against the wind call and the swell limits below, and against the region's own "Planning conventions": every other factor limit the region sets, plus any local rules binding every dive there. A reading in the no go band ends the plan at that site and time; a marginal one goes in the plan with the condition its band attaches.

The wind call comes from the region's wind tool, the same mechanism in every region. Run it with the site's own sectors from its Wind section, as the wind tool's documentation shows: the Bad bullet's sectors as `--bad`, and the Short fetch and Mixed bullets' sectors as `--short`. The tool prints go, marginal or no go for each reading, from the limits in its own section of `tool-config.json`; that call is the plan's wind verdict. Marginal means dive only with a short surface swim, and confirm the entry and the exit from the shore before kitting up. Where the two models of a cross-checked forecast give different calls, the plan carries the more severe one. Read the forecast direction against the site's Wind against current bullet too: where it falls in the opposing wind the site names while the current is running, outside slack, the plan says so beside the call, since the two together build a steeper sea than either alone.

Swell is its own check, read from the source the region names, since no tool reports it at the entry: breaking waves at the entry under 0.5 m are go, 0.5 to 1 m marginal, and over 1 m no go.

Respect `CLAUDE.md`'s Diving conventions for every plan: inside the no-decompression limit for the depth and gas on the day, never a decompression dive, a safety stop before surfacing whatever the profile, and EAN32 unless the user specifies a different mix.

If a tool errors out, an API is unreachable, or a source is down, stop and report it to the user rather than working around it. Never substitute a cached value, a plausible estimate, a different station, or a different bin to paper over the gap, and never present the plan as complete when a source it depends on failed; say plainly what failed and what it was supposed to provide, and wait before continuing.

## 3. Append the predicted row

`tools/db/plan_log.csv` is CSV, UTF-8 with a BOM (`utf-8-sig`); keep writing it that way, the BOM is what makes Excel read the accents, arrows and degree signs (`°`, `−`, `→`, `≈`) correctly on a double-click; if a session regenerates the file, write it with `encoding="utf-8-sig"`. If the file already exists, append to it as is, using its existing header row. If it doesn't exist yet, create it first (including the `tools/db/` folder if that's also missing) with exactly the header row given at the bottom of this skill, then append to that.

One row per record, two rows per plan, predicted and observed, sharing the same `plan_id` and distinguished by `record_type`. What goes in each of the 41 columns is given in the reference table at the bottom of this skill; read it before filling in a column rather than guessing from its name, and note which columns it marks predicted-only, model or forecast output with nothing aboard to re-measure them by (no anemometer, no thermometer, no station readout at depth), left blank on the observed row. Fill the predicted fields completely, including the things that are unsure, and put the uncertainty in the matching `*_note` column rather than the typed one.

## 4. After the dive, log what happened

Append, or fill in, the `observed` row for the same `plan_id`. A blank cell is fine where something wasn't noticed; never guess. A wrong entry here is worse than a missing one, because it gets averaged into an offset the next plan at this site will lean on.

The three observations that matter most, because they're what the offsets are built from: which way the current actually set, along the shore, and when (`set_direction`, `slack_note`); when it actually went slack, the moment it was limpest, as best it can be placed (`slack_time`, `slack_note`); what the viz actually was, at depth and in the shallows, kept separate (`viz_depth_*`, `viz_shallows_*`).

## Template

The canonical header row for `tools/db/plan_log.csv`, used verbatim to create the file when it doesn't exist yet:

```csv
plan_id,date,site,record_type,entry_time,exit_time,runtime_min,dive_plan,slack_time,slack_note,current_at_entry,spatial_entry_speed_ms,spatial_entry_dir_deg,spatial_exit_speed_ms,spatial_exit_dir_deg,set_direction,set_strength,reversal_at_slack,max_flood,max_ebb,diveable_window,ebb_exchange_size,viz_depth_min_m,viz_depth_max_m,viz_shallows_min_m,viz_shallows_max_m,viz_note,wind_speed_ms,wind_dir,wind_call,sea_state,air_temp_min_c,air_temp_max_c,surface_note,water_temp_min_c,water_temp_max_c,water_temp_note,max_depth_read_m,max_depth_normalized_m,depth_note,tide_across_dive
```

What each column holds:

| Column | Meaning |
|---|---|
| `plan_id` | ID shared by a plan's predicted and observed row, e.g. P001. |
| `date` | Dive date (site's local calendar day). |
| `site` | Site name, matching its file under `regions/*/sites/`. |
| `record_type` | predicted or observed. |
| `entry_time` | Local time in the water. Predicted: planned. Observed: actual. |
| `exit_time` | Local time out. Predicted: entry_time + runtime_min. Observed: actual. |
| `runtime_min` | Minutes underwater. Predicted: planned. Observed: actual. |
| `dive_plan` | Prose, both rows, never blank. Predicted: the actual plan entry to exit in order, not a restatement of the columns around it; follows this skill's planning rules (NDL only, safety stop, never return against the current). Observed: past-tense recap of what happened, noting where it departed from plan and what changed; a short recap is fine for an uneventful dive. |
| `slack_time` | Predicted: expected slack time. Observed: when it actually felt slack. |
| `slack_note` | Prose. Predicted: station or model used and offset confidence. Observed: what was actually felt or seen at slack. |
| `current_at_entry` | Prose: expected (predicted) or felt (observed) current right at entry. |
| `spatial_entry_speed_ms` | PREDICTED ONLY, blank on observed. Region's spatial current tool's speed (m/s) at entry, un-offset. Blank if the region has no spatial model. |
| `spatial_entry_dir_deg` | PREDICTED ONLY, blank on observed. Same tool's set direction (deg true) at entry. |
| `spatial_exit_speed_ms` | PREDICTED ONLY, blank on observed. Same tool's speed (m/s) at exit. |
| `spatial_exit_dir_deg` | PREDICTED ONLY, blank on observed. Same tool's set direction (deg true) at exit. |
| `set_direction` | Predicted: expected set, in words. Observed: the set actually felt or seen. |
| `set_strength` | Predicted: expected strength. Observed: felt strength. |
| `reversal_at_slack` | Predicted: expected reversal, e.g. ebb to flood. Observed: whether and when a reversal was actually felt. |
| `max_flood` | PREDICTED ONLY, blank on observed. Governing station's bracketing max flood, value at time. |
| `max_ebb` | PREDICTED ONLY, blank on observed. Governing station's bracketing max ebb, value at time. |
| `diveable_window` | Predicted: the numeric window(s) from the current tool's window command. Observed: short prose on whether a limiting current ever actually showed up. |
| `ebb_exchange_size` | PREDICTED ONLY, blank on observed. The day's exchange size from the governing station (small, moderate, large). |
| `viz_depth_min_m` | Metres at working depth. Predicted: forecast low end. Observed: what was seen. |
| `viz_depth_max_m` | Metres at working depth. Predicted: forecast high end. Observed: what was seen. |
| `viz_shallows_min_m` | Metres in the shallows, kept separate from depth viz. Predicted low end, observed reading. |
| `viz_shallows_max_m` | Metres in the shallows, kept separate from depth viz. Predicted high end, observed reading. |
| `viz_note` | Prose. Predicted: source and recency of the report used. Observed: description of what was actually seen. |
| `wind_speed_ms` | PREDICTED ONLY, blank on observed. m/s, from the region's wind forecast. |
| `wind_dir` | PREDICTED ONLY, blank on observed. Forecast wind direction. |
| `wind_call` | PREDICTED ONLY, blank on observed. The wind tool's call at the entry and the exit time with its sector kind, the more severe where the two models differ, e.g. `go (fine) / marginal (short)`. |
| `sea_state` | Predicted: forecast chop or swell. Observed: what was actually seen. |
| `air_temp_min_c` | PREDICTED ONLY, blank on observed. Celsius, forecast low. |
| `air_temp_max_c` | PREDICTED ONLY, blank on observed. Celsius, forecast high. |
| `surface_note` | Prose: sky, rain, general surface conditions, either row. |
| `water_temp_min_c` | Celsius. Predicted: seasonal expectation. Observed: measured. |
| `water_temp_max_c` | Celsius. Predicted: seasonal expectation. Observed: measured. |
| `water_temp_note` | Prose: thermocline or surface-layer difference, either row. |
| `max_depth_read_m` | Metres, raw computer reading. Predicted: planned max. Observed: actual max. |
| `max_depth_normalized_m` | Metres below the region's fixed datum. Blank if the region has none. |
| `depth_note` | Prose: what the depth figure covers, tide context, either row. |
| `tide_across_dive` | Prose: tide state and height across entry to exit, either row. |

# Scuba Diving

This workspace is for scuba diving planning and data analysis.

Import these companion files into context alongside it at session start:

- @diver-profile.json
- @tool-config.json
- @plan_log.csv
- @site_template.md

`diver-profile.json`, `tool-config.json` and `plan_log.csv` hold personal data and are gitignored, so a fresh clone of this workspace won't have them. If any is missing at session start, don't proceed as if it's empty and don't invent values for it: tell the user it's missing and ask them to copy the matching `diver-profile_template.json`, `tool-config_template.json` or `plan_log_template.csv` to the real filename and fill it in, then continue once it exists.

## Workspace structure

- `diver-profile.json` holds the user's specific diver profile and personal data.
- `tool-config.json` holds per-tool parameters, one subsection per tool in `tools/`; a missing key falls back to the tool's built-in default.
- `plan_log.csv` holds dive plans vs observed data.
- `site_template.md` is the template to write descriptions for new dive sites.
- Each diving region is a folder under `regions/` holding one `<region>.md` steering file and a `sites/` subfolder. Each site is a pair in `sites/`: `<slug>.md`, the guidebook description, and `<slug>.json`, its ENPAC15 current extract, machine-read by `tools/adcirc_current.py` and never hand-edited. A region's steering file is not loaded at session start; load it whenever working on or referencing a site `.md` or `.json` in that region's `sites/` folder, before acting on that site.

## Units: use metric

- Use metric: bar, metres, litres, C.
- Do the arithmetic in metric, present results in metric, and don't append imperial conversions in parentheses unless asked. Gas planning in bar and litres, depth in metres, temperature in C, cylinder size in litres and working pressure in bar.
- Imperial only survives where it's part of a product's actual name (a "Faber HP 80" is called that on the sticker), and even then the working figure next to it is metric.

## Time convention: use the timezone of the dive site

- Dive sites and planning should use the dive site local time zone. Never carry a UTC timestamp into a plan, a site file, or the log.
- This is a strict rule because slack, wind, and entry time are only useful against each other. A source silently read in the wrong zone or time shifts the slack window by 7 to 8 hours, which is obvious, or by exactly one hour across a DST boundary, which is not obvious and looks entirely plausible.

## Depth convention: normalized to MLLW

- Depth is not a property of a site. The seabed is fixed, the surface is not, so an un-normalized depth is not comparable to any other dive. Every depth worth keeping is normalized to the MLLW datum, the datum NOAA charts and predictions use. Never mix datums.
- Tide height is signed. It goes negative on a minus tide, so a low-water dive reads shallower than the site's datum depth; subtracting a negative makes the datum depth the deeper number.

```
depth below MLLW datum  =  observed depth (computer)  -  tide height at that moment
depth below surface     =  datum depth                +  predicted tide height
```

## Sources and tools

Use these sources when writing a new dive site file, planning a dive, or answering questions for the user. A source with a wrapper script carries it as a subchapter; every tool lives in `tools/`, works in metric, and prints local time. Each tool reads its parameters from its own subsection of `tool-config.json`.

### Stop on tool or source failure

If a tool errors out, an API is unreachable, or a site is down, stop and report it to the user rather than working around it. Never substitute a cached value, a plausible estimate, a different station, or a different bin to paper over the gap, and never present a plan or a site file as complete when a source it depends on failed. Say plainly what failed and what it was supposed to provide, and wait for the user before continuing. This matters because a plan built on partial data looks exactly like one built on complete data. A missing current window or a silently skipped tide check does not announce itself in the output, and by the time it matters it is a diver in the water holding a plan that was never actually checked.

### Dive logs

What any dive log is for: user-specific experience, a site's depth range, gas consumption, water temperature, viz by season, hazards hit, and calibrating current offsets against dives actually done. Two levels live in each. The per-dive aggregates (max depth, temperature, gas, visibility, current, the site) answer the daily questions; the full profile (depth and the rest, sampled every few seconds) places the deepest point, the turn and the ascent on the clock, which is what an offset calibration or an ascent-behaviour read needs. Read the free-text notes: notes are where *"anxiety again… down current"* lives, the thing that could actually hurt you, and the hazards are in the prose. Weight the subjective fields carefully; a visibility or current value is weak on its own, trustworthy only in aggregate. Times are local, so a sample's time is seconds into the dive and its clock time is the dive start plus that offset. Each file is a snapshot refreshed after diving, so recent dives, or notes added since, are missing until the next refresh, never wrong, and each is large, so read it through its tool rather than opening it whole.

#### Subsurface

Subsurface's saved logbook, read through a read-only tool: Subsurface owns the file, and this tool never writes it. Its path is set in `subsurface_log.file` in `tool-config.json`.

- **Format.** Subsurface native XML (`program='subsurface'`), also written as `.ssrf`. Every value carries its unit inline (`depth='23.1 m'`, `pressure0='219.67 bar'`, `size='9.67 l'`), so the tool converts off the suffix and always presents metric, whatever the app's display units are.
- Condition ratings come as 1 to 5: visibility (1 poor to 5 excellent), current (1 strong to 5 slack), and wavesize, surge and chill (1 severe to 5 calm/none).
- Sites are normalized: the name holds the site alone, the location (e.g. "Howe Sound", "Quintay") lives in the site's notes, and country, state and ocean live in its georeference entries. The tool reads all of these.
- Read-only, but shared: Subsurface rewrites the file on save, so keep the app closed when anything writes to it. This tool only ever reads.

##### `tools/subsurface_log.py`

Streams the logbook, in metric and local time, without modifying it.

```sh
python3 tools/subsurface_log.py list [--site S] [--since D] [--limit N]   # recent dives, one line each
python3 tools/subsurface_log.py show SELECTOR                             # aggregates, ratings, marks, notes
python3 tools/subsurface_log.py profile SELECTOR [--csv]                  # depth, temperature, pressure per sample
```

`SELECTOR` is a dive number, or a substring of the date, site name, site region (location, state, country, ocean) or tags; `list --site` matches name and region too. `show` gives the aggregates plus the computed SAC, OTU and CNS, the condition ratings (visibility, current, wavesize, surge, chill), the buddy and divemaster, the site's region, gas changes on multi-cylinder dives, any in-dive marks, and the notes; `profile` is the per-sample series, each sample stamped with its clock time.

### DAN (Divers Alert Network)

<https://dan.org>

The authority on what actually goes wrong, and why: dive medicine, accident data, and the practices that come out of them.

- Emergency: +1-919-684-9111, 24/7, collect calls accepted worldwide. Call local EMS first, then DAN. Non-emergency medical questions: +1-919-684-2948 (option 4), Mon-Fri 08:30 to 17:00 ET.
- Use it for: the standing questions, not the daily ones. Gas and O2 exposure, decompression and DCS, cold-water and drysuit physiology, ascent behaviour, configuration and redundancy, fitness to dive, when to call an incident an incident. And post-dive: symptom triage and who to call.
- What's actually there:
  - Annual Diving Report: fatalities, injuries and case narratives from a database DAN has kept since 1989. Free PDF in the [publication library](https://dan.org/research-reports/publication-library/). The case narratives are the valuable part; read those, not just the tables.
  - [Incident Insights](https://dan.org/safety-prevention/diver-safety/case-summaries/): short curated case summaries, the everyday failures rather than only the fatal ones.
  - Health & medicine reference and smart guides: the medical answers, sourced.
  - Alert Diver: the magazine, back issues free.
- Read it against our config, not in general. The parts of this workspace it bears on are in `diver-profile.json`; an incident report is useful here when it says something about one of those.
- Weight accordingly: authoritative on medicine and honest about the data, but there is no denominator. Incidents are self-reported with no exposure count behind them, so it yields mechanisms, never rates. Take "here is how this went wrong" and leave "this is how likely it is."
- Not a planning source. It never knows the slack, the wind, or the viz, so it changes nothing on a go/no-go. It belongs in gear decisions, procedures, and debriefs, not in `plan_log.csv`.
- Freely fetchable: `robots.txt` is open, no AI-crawler carve-outs, sitemap published.
- The diver's own DAN membership details (member number, coverage, renewal deadline) are in `diver-profile.json`, not here.

### Books

Print dive guides for the region. There is no copy of their contents in this workspace and you cannot read them: when a book is likely to cover a site, ask the diver for the relevant pages. Take the behaviour, never the numbers; their figures are dated, so re-derive every current and depth figure against NOAA before it enters a site file. Both are snapshots, too: verify access, parking, fees, and closures against a recent report before driving out.

#### Northwest Shore Dives (Stephen Fischnaller)

Site-specific current behaviour and entries, focused on Puget Sound shore dives. It documents most established ones.

- Use it for: where the entry is, what the site actually does on the flood vs. the ebb, whether it's slack-only, hazards, parking. Its method (reference station plus a site correction) is the right one and is what we follow.
- ⚠️ Its reference stations are legacy: the corrections are stated against NOAA current stations that in most cases no longer publish predictions, and an offset is only meaningful against the station it was derived from. Do not apply a book offset to a modern station; that is how you end up in the water at max ebb holding a plan that says slack. Per site, pick the governing modern NOAA station, establish our own offset to it, and track its confidence in `plan_log.csv`.

#### 151 Dives in the Protected Waters of British Columbia and Washington State (Betty Pratt-Johnson)

Wider in scope than Fischnaller: it reaches beyond Puget Sound shore dives into the San Juans, the Strait of Juan de Fuca, the Gulf Islands, and British Columbia, and it covers boat access as well as shore.

- Use it for: where the entry is, how the site is dived, hazards, marine life, and access, especially for sites north and west of the Sound that Fischnaller does not reach.

### NOAA CO-OPS (current predictions and water levels)

<https://tidesandcurrents.noaa.gov/noaacurrents/stations.html?g=698>

Two products, two station networks, both authoritative, both needed: currents give the slack window (what makes the dive possible), water levels give the tide height (what makes the depth comparable). One API serves both, but a site's current station and its tide station are different places with different IDs, neither substitutes for the other, and a site file records both.

#### Currents (slack and max flood/ebb)

The slack time and direction, on the day, for the reference station that governs the site. This is the number the whole plan hangs off.

- Use it for: the slack time and direction on the day, at the station governing the site, plus the max flood/ebb speeds bracketing the window.
- Read the whole day, not just the one slack. Slacks are not evenly spaced and not equal: a slack between two weak maxes is a wide window, between two strong maxes a narrow one. Note the max flood/ebb speeds either side of your window; they bracket how fast the site turns on you if you're late.
- ⚠️ Mind the bin: the default is near-surface. The stations are ADCPs with many depth bins, NOAA publishes predictions for only a few, and the default is a shallow one, not the water we dive. Pick the published bin nearest the site's working depth, and record which bin the offset was derived against; an offset against one bin is not the same number as against another. At Burrows Pass the default bin sits at 4.6 m and the deepest published bin at 30.6 m; on a test day the deep slack ran 20 minutes earlier than the surface slack, with max flood weaker (1.41 vs 1.61 m/s) and the flood axis rotated 286°→275°. Still pull the other bins: a wide spread between them is itself a warning that the offset is depth-sensitive.
- Watch for: diurnal inequality (the two daily exchanges are not the same size), and big exchanges around new and full moon.
- API, no key, machine-readable predictions for arbitrary future dates. ~412 live current-prediction stations sit inside the Puget Sound box, searchable by position; that is how a site gets re-based off a dead Fischnaller station onto a live one.

##### `tools/noaa_current.py`

```sh
# Re-base a site: which live stations are near it?
python3 tools/noaa_current.py stations --near 48.4895 -122.6867

# Which bins publish, and at what depth?
python3 tools/noaa_current.py bins PUG1738

# Slack / max flood / max ebb, at the dive-depth bin
python3 tools/noaa_current.py predict PUG1738 --bin 1 --date 2026-07-12

# The number that actually matters: how long the window stays diveable
python3 tools/noaa_current.py window PUG1738 --bin 1 --date 2026-07-12 --max-speed 0.25
```

`window` is the planning command. Rather than a single slack instant it reports every span where the current stays under a threshold (default 0.25 m/s), with its duration and peak, so a 72-minute window and a 20-minute one stop looking alike. Sample output, Burrows Pass, bin 1, 12 Jul:

```
  01:06 - 02:12    72 min   peak 0.23 m/s
  06:54 - 07:36    48 min   peak 0.21 m/s
  17:30 - 18:18    54 min   peak 0.24 m/s
  21:54 - 23:36   108 min   peak 0.24 m/s
```

Two things it does not do, on purpose: the threshold is a placeholder, not a considered limit (0.25 m/s is roughly 0.5 kn, a guess at what's comfortable in a drysuit, worth setting from experience; the default lives in `tool-config.json` as `max_speed_ms`, for this tool and for `adcirc_current`), and every time it prints is at the station, un-offset. The site correction is still ours to apply.

#### Water levels (tide height, and therefore depth)

The predicted tide across the entry window: how deep the site is that day. This is what turns a depth reading into a number that means something on any other day.

- Use it for: the tide height across the entry window, and the day's high and low water, at a station in the same body of water as the site.
- ⚠️ Pick a station in the same body of water. Water level varies smoothly, so the nearest station is usually right, but "near" has to mean hydraulically near, not near on a map. Verify the station's name and position before trusting the label; a mislabelled tide station once cost about 1 m at high water.
- ⚠️ Most Sound stations are subordinate: they publish high/low water only, no 6-minute series.
- Datum: MLLW. It is what the charts and the predictions use. Never mix datums.
- Times: `lst_ldt`, local, like everything else here.

##### `tools/noaa_tide.py`

The tool behind the depth convention: it is what makes a depth comparable between dives. Metres below MLLW.

```sh
# Which tide stations are near the site? (VERIFY the name - IDs are not self-describing)
python3 tools/noaa_tide.py stations --near 47.9497 -122.3026

# High/low water for the day, and the day's range
python3 tools/noaa_tide.py predict 9447814 --date 2026-07-12

# Tide height at a moment
python3 tools/noaa_tide.py at 9447814 --time "2026-07-12 09:18"

# LOGGING: observed depth -> depth below MLLW datum. The number that carries between dives.
python3 tools/noaa_tide.py normalize 9447814 --time "2026-07-12 09:21" --depth 14.5

# PLANNING: a known datum depth -> how deep it actually reads, through the day
python3 tools/noaa_tide.py project 9447814 --datum-depth 15.4 --date 2026-07-12
```

`normalize` is the logging command, `project` is the planning command, and they are inverses:

```
$ noaa_tide.py normalize 9447814 --time "2026-07-12 09:21" --depth 14.5
  observed depth        14.5 m
  tide height          -0.94 m
  depth below MLLW      15.4 m   <-- log this

$ noaa_tide.py project 9447814 --datum-depth 15.4 --date 2026-07-12
  09:37  LOW   tide -0.95 m   ->  reads  14.4 m below surface
  17:44  HIGH  tide +3.36 m   ->  reads  18.8 m below surface
```

On subordinate stations it interpolates harmonically between the high/low extremes (the smooth form of the rule of twelfths), good to a few centimetres, far inside the precision a dive computer's depth deserves, so `at` and `normalize` work anywhere.

### ENPAC15 (ADCIRC spatial tidal currents)

<https://adcirc.org/products/adcirc-tidal-databases/>

A depth-averaged tidal current field for the whole Eastern North Pacific: the ENPAC15 harmonic constituent database, 37 constituents on an unstructured mesh of ~554k nodes refined into harbours, produced by the University of Oklahoma with NOAA's Coast Survey Development Laboratory using the ADCIRC model. Where NOAA gives the current at scattered station points, this is a continuous field: it can predict at sites with no station near them and in the water between stations.

- Use it for: current speed, direction and slack timing at any point inside the mesh, for any date, scaled to any working depth through the boundary layer profile. It predicts continuously across the whole domain rather than at scattered points, so it covers a site with no current station of its own and the water between existing stations equally well.
- ⚠️ Depth-averaged, not a depth bin: the mean over the whole column, which runs slower than the near-surface water and slower than the bin a NOAA station reports. It is also smooth: it under-represents the sharp flood/ebb asymmetry of real rapids, softens the diurnal inequality, and is only approximate at any single point. It holds the semidiurnal slacks and the axis well; treat the unequal exchange and the peak speeds as approximate.
- ⚠️ Coverage is not uniform. Channels and passes are resolved; some shore entries fall just outside the wet mesh and snap to the boundary. The tool records how far out: a few hundred metres is a shore entry at the model edge, usable with care; kilometres out is unresolved.
- ⚠️ Behaviour, not the flood/ebb label. It gives the current axis, the slack times, and the peak speeds; which of the two axis directions is the flood is site-specific and has to be fixed against the tide or a station.
- Distribution, not an API: a single ~700 MB download, cached once in `tools/db/`, safe to delete (it re-downloads on the next extraction). Per-site extraction is time-independent: a site is extracted once and predicted forever.
- Its astronomy is pinned to the database's own reference nodal factors and equilibrium arguments (2004-11-16).

#### `tools/adcirc_current.py`

Two uses, on different files.

1. Writing a new site file (needs the database). Get the seabed depth at the dive-area coordinate from `ncei_depth.py`, then extract the constituents, passing that depth in:

   ```sh
   python3 tools/ncei_depth.py 48.49042 -122.69148 --mllw
   python3 tools/adcirc_current.py extract <slug> --near 48.49042 -122.69148 --water-depth 20
   ```

   Use the coordinate of the dive area (the deeper part actually dived), not the beach entry: a dive-area point lands inside the mesh and reads the current you experience, a shoreline point snaps to the mesh edge and reads near-still water. The extract is written as `<slug>.json` beside the site's `<slug>.md`. The `--water-depth` (m below MLLW) is what `--depth` scaling later uses; without it the extract falls back to the coarse mesh depth and the scaling is rough.

2. Planning a dive (reads only the small extract, never the database).

   ```sh
   python3 tools/adcirc_current.py predict <slug> --date 2026-07-12 [--depth M]   # slacks + peaks
   python3 tools/adcirc_current.py window  <slug> --date 2026-07-12 [--depth M]   # diveable windows
   python3 tools/adcirc_current.py at      <slug> --time "2026-07-12 09:18" [--depth M]
   python3 tools/adcirc_current.py list                                           # extracted sites
   ```

   It prints the principal current axis and, per exchange, the slack times and peak speeds, un-offset at the extract point (the site correction is yours to apply, same as the station tools) and unlabelled for flood vs. ebb. `--depth M` (below MLLW) scales the depth-averaged speed toward your dive depth through a boundary-layer profile (slower near the seabed, faster higher up); it moves speeds and window widths but never slack times, refuses if the dive depth exceeds the site's water depth, and is approximate, ignoring the Sound's brackish surface layer. Put the `predict`/`window` output, predicted beside observed, in `plan_log.csv`.

Validate a new extract against the site's NOAA station before trusting its timing. `python3 tools/adcirc_current.py selftest` verifies the astronomy against the database's own reference values.

### NCEI coastal DEM (bathymetry, water depth)

<https://gis.ngdc.noaa.gov/arcgis/rest/services/DEM_mosaics/DEM_all/ImageServer>

NOAA NCEI's coastal digital elevation model: the seabed depth at a point, at ~3 m resolution (1/9 arc-second) in Puget Sound. A separate NOAA service from the currents and VDatum APIs. It owns bathymetry for the workspace.

- Use it for: the water depth at a dive point, which goes in the site file's Coordinates row and into `adcirc_current.py extract --water-depth`. The ENPAC mesh cannot supply it: its elements can span from the beach to the deep basin, so its nearshore depth can be wrong by tens of metres. The DEM's 3 m soundings are the authority.
- Also a sanity check on a coordinate: is this point underwater at all, and at a divable depth? It reads the actual bottom where a nautical chart gives scattered soundings between wide contours.
- ⚠️ Datum is the DEM tile's own, usually NAVD 88 (roughly mean sea level here), not MLLW. Good to a couple of metres for the boundary-layer scaling and a divable-or-not check; a depth normalized to datum still goes through `noaa_tide.py` and MLLW.
- Point query via the ImageServer `identify` operation, no key, needs a User-Agent. Returns the elevation and the source tile (name, resolution, datum). Positive means above water, which flags a coordinate on land.

#### `tools/ncei_depth.py`

```sh
python3 tools/ncei_depth.py 47.95029 -122.30297                       # depth below NAVD88 (~mean sea level)
python3 tools/ncei_depth.py 47.95029 -122.30297 --mllw                # also convert to depth below MLLW
python3 tools/ncei_depth.py 47.95029 -122.30297 --mllw --region R     # pick the VDatum region explicitly
```

Site files quote depth below MLLW, so use `--mllw`. It converts via NOAA VDatum, falling back to the NAVD88-to-MLLW offset from the nearest tide station publishing both datums, then to a flat nominal if neither answers, reporting which it used. The offset is not constant: about 0.1 m in the Strait of Juan de Fuca to about 0.7 m in the south Sound.

⚠️ VDatum tiles the world into named regions and will not infer one from the coordinate; the wrong region, or its own `contiguous` default (Atlantic/Gulf coasts), fails with an opaque "Uncaught error" rather than a useful message. `python3 tools/ncei_depth.py --help` lists every valid region code. `--region` overrides `ncei_depth.default_region` in `tool-config.json`, which holds this workspace's default (`westcoast`). Some regions additionally require a specific target horizontal frame for a tidal target datum (westcoast wants IGS14); VDatum names the required frame in its own error when this applies, and the tool retries once with whatever it names, so that quirk never needs to be handled by the caller.

### NWS point forecast (wind and surface conditions)

<https://api.weather.gov>. National Weather Service, no key, no rate limit worth worrying about.

The wind source. Wind is the second-order factor that decides whether the entry is diveable at all, and it is per-site: what matters is the wind on that beach, not the regional marine forecast.

- Use it for: wind speed and direction at the entry, hourly, on the day. Plus sea state, air temperature and rain, which set what the surface interval feels like.
- How: resolve the beach's coordinates to a gridpoint, then follow `forecastHourly`:

  ```sh
  curl -s -H "User-Agent: dive-planning (<contact-email>)" \
    "https://api.weather.gov/points/47.9497,-122.3026" | jq -r .properties.forecastHourly
  # then GET that URL - hourly periods with windSpeed, windDirection, temperature, shortForecast
  ```

  A `User-Agent` is required, NWS rejects requests without one. Use the contact email from `nws.user_agent_email` in `tool-config.json` for `<contact-email>` (the gmail address, deliberately not the DAN account email).
- Point forecast, not the zone/marine forecast. The marine forecast covers open water and will happily tell you it's blowing 15 kn offshore while the beach in the lee is glass.
- The wind call is per-site, so it lives in the site file: which direction ruins that particular entry, and what the fetch is. NWS gives you the number; the site file says whether that number matters. A 20 mph southerly is nothing at a north-facing beach and a dive-killer at a south-facing one.
- Wind against current is worse than either alone. Cross-check the direction against the ebb/flood axis from the NOAA current data before calling an entry flat.

### Community sources (local knowledge)

Three of them, different strengths. This is where you learn how a site is actually dived, the stuff that is in nobody's database: which gate is locked, where people really park, which end of the beach you enter from, whether anyone got in this weekend.

Weight them accordingly: unmoderated, anecdotal, undated as often as not. Good for signal that something changed, weak for numbers. One person's "great viz" is worth nothing without a date and a site, and a post's times are local and approximate.

#### ScubaBoard (Pacific Northwest forum)

<https://www.scubaboard.com/community/forums/pacific-northwest.81/>

Big one. Conditions chatter, closures, buddy finding, general local knowledge.

- Use it for: things that don't appear in any prediction, a closed gate, a fee change, a bloom that just rolled in, whether anyone actually got in this weekend.
- Broad but diffuse: a national board with a PNW room, so the local signal is diluted.

#### NW Dive Club (site descriptions and recommendations)

<https://nwdiveclub.com/viewforum.php?f=6>

The better of the two forums for site descriptions: community write-ups of how to dive a specific site, and recommendations on where to go. Narrower and more local than ScubaBoard.

- Use it for: how a site is dived, where the entry is, what's worth seeing, what to expect. Also site recommendations when picking somewhere new.
- It complements the Fischnaller book, with the opposite failure mode: the book is coherent and authoritative but frozen in time, the forum is current but unedited and uneven. Where they overlap, prefer the book for behaviour and the forum for access.
- ⚠️ Same rule as the books: take the behaviour, never the numbers. A forum post's depths are raw computer readings at an unrecorded tide, and its slack times carry no station. Re-derive both against NOAA CO-OPS, and normalize any depth to datum before it is comparable to ours.
- ⚠️ The live site blocks our fetches (HTTP 403), so read it through the Wayback Machine: query `https://archive.org/wayback/available?url=<page>` for the closest snapshot, then pull the archived copy. `web.archive.org` refuses the fetch tool too, so `curl --compressed` the snapshot URL. A snapshot lags the live thread, but site descriptions age slowly; check the snapshot date and verify anything time-sensitive against a fresher source.

#### The Perfect Dive (archived PNW site catalog)

<https://web.archive.org/web/20220413053905/http://theperfectdive.com/DEF-SiteList.asp>

A defunct catalog of Pacific Northwest dive sites (Puget Sound north and south, Hood Canal, the San Juans, the Strait of Juan de Fuca, and the Washington and Oregon coasts), each with a structured detail page (dive type, difficulty, entry, attractions) plus marine-life photo-ID galleries and a critter-sightings calendar. It is the catalog the NW Dive Club threads link out to for sites and critters.

- Use it for: a fast structured read on a site we don't know (difficulty, entry, what's down there) and to cross-check NW Dive Club and the books. It lists some sites the others skip.
- ⚠️ Defunct, Wayback only: every read is a snapshot from around 2022, frozen in time like a book and older than the forums. Verify anything time-sensitive (access, fees, closures) against a recent source.
- ⚠️ Same rule: behaviour, not numbers. Re-derive depth and slack against NOAA CO-OPS and normalize depth to datum.

### PNW Diving (recent visibility reports)

<https://pnwdiving.com>

Recent viz reports, the one thing prediction can't give you.

- Use it for: what viz has actually been like at the site in the last few days/weeks.
- Weight by recency: a report older than about a week through a bloom is stale. Prefer a report from the same site and the same tide phase.
- What we may take, and what we may not. The operator drew this line themselves, and we hold to it:
  - ✅ The "Recent Dive Reports" summary table on the home page (`/`): site, viz, age. It is server-rendered, on an allowed and sitemapped path, and the page itself says *"Press 'View Posts' to see all the details"*, i.e. the summary is the public part. It covers ~28 sites over ~9 days and updates live.
  - ❌ The full report bodies under `/*/reports`: explicitly `Disallow:`-ed in robots.txt, alongside `Google-Extended: Disallow: /`. Never scrape these. The visibility map on the home page is also off-limits in practice: its points are not in the HTML, they are fetched client-side from the reports API, so getting them would mean driving a headless browser or calling that API, circumvention either way.

#### `tools/pnwdiving_viz.py`

Reads exactly the public summary table, once, cached (`pnwdiving_viz.cache_hours` in `tool-config.json`, default 6), converted to metres. The feed is live and updates continuously.

```sh
python3 tools/pnwdiving_viz.py --max-age 3      # only fresh reports
python3 tools/pnwdiving_viz.py --site skyline   # one site
python3 tools/pnwdiving_viz.py --raw            # feet, as the reporter wrote it
```

## Sites

**Important!** Write site files like an entry in a public dive guidebook. Factual, readable, and useful to any diver preparing for the site, not a page of our own notes.

The canonical structure is `site_template.md`. All site files, new and old, follow it: a title, a plain-prose description, a facts table, then `##` sections whose bullets each open with a bold topic followed by the explanation. Section order: Getting there, Navigation and landmarks, Current, Depth and tide, Hazards, Wind, Visibility, Temperature, Marine life. Include a section only when there is data for it.

A coordinate handed to you for a new site is a first reference, not the final one. Check its seabed depth (`ncei_depth.py`) before writing anything; a point mid-channel or off the drop is not the dive. If it is too deep, or off the divable slope, walk it toward shore and re-check, comparing candidate depths against the source description (the guidebook, the community reports, the site's own terrain narrative) until the coordinate's depth matches what is actually described as being dived. It also has to stay inside the ENPAC15 mesh: `adcirc_current.py extract` reports `mesh.inside` and `boundary_dist_km` on the result, and a coordinate walked too close to shore can fall outside the wet mesh or snap to its boundary, which reads as near-still water rather than the site's real current. Don't walk it past that edge; if the divable depth and mesh coverage conflict, keep the coordinate on the mesh side and note the shallower part of the dive separately. Extract ADCIRC and pick the governing current and tide stations against that corrected coordinate, not the original.

Creating a site file draws on every source under Sources and tools that applies, and beyond them always run a comprehensive web search for the site by name. Sources outside the fixed list, a dive shop's site page, a forum thread, a recent trip report, an incident writeup, turn up facts none of the standing sources carry alone (an access change, a renamed park, a hazard). Don't stop at the standing source list; go find what's out there.

Keep the facts, drop the bookkeeping. A fact goes in the file whether it came from public data (NOAA) or from what we saw over repeated dives: coordinates, depth ranges, the governing current station and its bin, the offset, current behaviour, entry, hazards, temperatures, marine life. Our own apparatus does not: no confidence flags (`derived` / `observed` / `unverified`), no logged dive stats (dive counts, runtimes, a specific dive number, a computer bookmark), no source attributions (Fischnaller, the forums, our own log). A derived number is written as a plain fact, stated flatly, without naming where it came from.

The confidence work still happens, it just doesn't live in the file. Verify a station still publishes, verify the tide station's name and position, reason through the offset and how sure you are of it. That reasoning belongs in the chat and its results in `plan_log.csv` (predicted beside observed); the site file carries only the best number it produced. A number you are unsure of is stated conservatively, not annotated.

Style, same as the files themselves: metric only; no bold text inside paragraphs (bold is for a bullet's lead topic and the table's left column); avoid the dash as a connector or separator (use commas, periods, parentheses, or "to" for a range). Genuine hyphens in names and compound words are fine.

Every site file carries two stations, and they are not the same station: a governing current station (with its bin and offset) and a tide station in the same body of water (name and position verified, not just its ID). Every depth is quoted as a datum depth (m below MLLW), because a raw depth is only true at the tide it was read at. The companion `<slug>.json` extract stays data beside the guidebook: never edited by hand, never folded into the prose.

## Plan log

`plan_log.csv` records every dive planned, with what we predicted beside what was actually observed. One row per record; two rows per plan, predicted and observed, distinguished by the `record_type` column and sharing the same `plan_id`.

### Format

- CSV, UTF-8 with a BOM (`utf-8-sig`). The BOM is what makes Excel read the accents, arrows and degree signs (`°`, `−`, `→`, `≈`) correctly on a double-click; keep writing it. If a session regenerates the file, write it with `encoding="utf-8-sig"`.
- Hybrid schema. Clean numerics are typed into their own columns; irreducibly-prose fields stay as single text columns. Metric throughout, same as the rest of the workspace (convert wind to m/s, depths to m, temps to C). Ranges are split into `*_min` / `*_max` pairs; a single reading fills both. A value-with-time-and-comment (a max flood, a tank summary) keeps the whole string in one prose cell.
- Columns (40), in order:
  - *identity:* `plan_id`, `date`, `site`, `record_type`
  - *times / profile:* `entry_time`, `exit_time`, `runtime_min`, `dive_plan`. On a predicted row, `exit_time` is entry plus runtime.
  - *current:* `slack_time`, `slack_note`, `current_at_entry`, `spatial_entry_speed_ms`, `spatial_entry_dir_deg`, `spatial_exit_speed_ms`, `spatial_exit_dir_deg`, `set_direction`, `set_strength`, `reversal_at_slack`, `max_flood`, `max_ebb`, `diveable_window`, `ebb_exchange_size`. The `spatial_*` columns are the ENPAC15 prediction at the site (`adcirc_current.py at <slug> --time ...`) at entry and exit: depth-averaged speed in m/s and set direction in degrees true, un-offset, filled on the predicted row.
  - *visibility:* `viz_depth_min_m`, `viz_depth_max_m`, `viz_shallows_min_m`, `viz_shallows_max_m`, `viz_note`
  - *wind / surface:* `wind_speed_ms`, `wind_dir`, `sea_state`, `air_temp_min_c`, `air_temp_max_c`, `surface_note`
  - *water / depth:* `water_temp_min_c`, `water_temp_max_c`, `water_temp_note`, `max_depth_read_m`, `max_depth_normalized_m`, `depth_note`, `tide_across_dive`

### Dive plan

`dive_plan` is a single prose column, filled on the predicted row: the actual plan from entry to exit, in the order it happens, not a restatement of the typed columns around it. Where the excursion goes, in what order, and when to turn for the exit.

Every plan follows the same rules, regardless of site:

- **Non-decompression only.** Plan inside the no-decompression limit for the depth and gas on the day. Never plan a decompression dive.
- **Safety stop, always.** Every plan carries a stop before surfacing, whatever the profile.
- **EAN32 by default.** If the diver holds an Enriched Air certification, assume EAN32 for planning, matching `standard_configuration.back_gas` in `diver-profile.json`, unless the plan states a different mix. Without that certification, or with no mix specified, assume Air.
- **Never plan the return against the current.** Order the excursion so the leg back to the entry point runs with the current or through slack, never against it. Where the governing current sets a known direction after slack, work the far leg first, upstream of the entry, and turn for home before the current builds against a return swim; a plan that has the diver kicking home into a developing current is a planning failure, not a detail to note afterward.

### How to use it

1. Before the dive: append the `predicted` row. Fill the predicted fields completely, including the things we're unsure about (put the uncertainty in the matching `*_note` column, not the typed one).
2. After the dive: append (or fill) the `observed` row. A blank cell is fine where you didn't notice; never guess. A wrong entry here is worse than a missing one, because it gets averaged into an offset.

The three observations that matter most, because they're what the offsets are built from:

- Which way did the current set you, along the shore, and when (`set_direction`, `slack_note`).
- When did it actually go slack, the moment it was limpest, as best you can place it (`slack_time`, `slack_note`).
- What was the viz, at depth and in the shallows, separately (`viz_depth_*`, `viz_shallows_*`).

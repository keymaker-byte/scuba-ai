# Dive Atlas (community dive site wiki)

<https://diveatlas.org>

A community wiki of dive sites. Each site page carries structured properties (coordinate, region, access type, water type, depth range, a skill level category) followed by a guidebook-style write-up: location and access, diving, attractions and life, hazards, facilities.

- **Use it for.** Writing a new site file: a second pin for the dive area to cross-check against our own coordinate, and the write-up's entry, landmarks, parking, hazards and facilities, which a good page covers in useful local detail.
- **Pages vary in completeness.** A page can be a stub: the property block, a skill level and a link elsewhere, every section empty. `site` says so when a page has nothing past its properties, and flags pages the wiki itself marks as incomplete. A full page reads well; a stub is only a pin.
- **Same rule as any community source.** Behaviour, not numbers. A page's depths are contributor figures at an unrecorded tide, often in feet: re-derive depth against bathymetry to the region's datum, and any current timing against the region's current source. Temperatures and visibility can be plainly wrong for the region; check them against the region file.

## `tools/diveatlas.py`

Standard library only.

```sh
python3 tools/diveatlas.py near 47.5888 -122.3800 --radius 2   # 1. find the page by coordinate
python3 tools/diveatlas.py search "seacrest"                   # 2. fallback only, by title
python3 tools/diveatlas.py site "Seacrest Cove 2"              # 3. read the page
```

Find the page with `near` at the site's dive-area coordinate; it lists every site within the radius, nearest first, with each pin's distance. The wiki sometimes holds two pages for one site, a full one and a stub, under different titles, and `near` shows both. Fall back to `search`, which matches every term in the title, only when `near` returns nothing, and confirm a title match is the same site before reading it.

`near` and `search` run against a local index of every site's coordinate, built from one Semantic MediaWiki query and cached in `tools/db/diveatlas_index.json` (`diveatlas.cache_hours` in `tool-config.json`, default 1). `site` fetches one page live and prints its properties (depth converted to metres), then each non-empty section as plain text, with templates, images, galleries and references dropped. `diveatlas.user_agent_email` sets the contact address in the User-Agent, as MediaWiki asks of API clients.

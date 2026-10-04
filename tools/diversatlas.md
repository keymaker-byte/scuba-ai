# Divers Atlas (community dive site database)

<https://diversatlas.org>

A nonprofit, user-contributed database of dive sites worldwide, with coordinates, a site type, a description and whatever fields contributors have filled in.

- **Use it for.** Additional information when writing a new site file.
- **Configuration.** `database_url` and `api_key` in the `diversatlas` section of `tool-config.json`. Both are required, there are no defaults, and the tool stops if either is missing. A `401` means the key is no longer valid; stop and report it.
- **Undocumented, and can change.** The table and column names are the site's internal schema. A query that starts failing or returning empty means the schema moved; stop and report it rather than guessing at a replacement.
- **Same rule as any community source.** Behaviour, not numbers. A record's depths and times are unnormalized contributor figures. A pin is a cross-check, never a replacement for a coordinate verified the workspace's own way.

## `tools/diversatlas.py`

Standard library only.

```sh
python3 tools/diversatlas.py near 48.15683 -122.67062 --radius 2   # 1. find the record by coordinate
python3 tools/diversatlas.py search "keystone"                     # 2. fallback only, by name
python3 tools/diversatlas.py site keystone-jetty                   # 3. read the record
python3 tools/diversatlas.py site keystone-jetty --raw             #    the record as JSON, for troubleshooting
```

Find the record with `near` at the site's dive-area coordinate. It lists every site within the radius, nearest first, with each pin's distance, so it also answers how far their pin sits from ours, and turns up neighbouring records worth reading. A name or slug is a poor key: contributors misspell them, name a site differently from us, or reuse a name from elsewhere in the world. Fall back to `search`, which matches every term in the name, only when `near` returns nothing, since a contributor sometimes pins a site at the town or the parking lot, out of reach of the radius; confirm a name match is the same site before reading it.

`site` prints the pin, the address and description, then each free-text topic (points of interest, notable life, safety, recent conditions, access, facilities) with its contributor tips merged in and dated, then every remaining non-empty field under "details": access status, fees and passes, ownership, and depth and visibility in metres. Internal ids and the feet duplicates of the metre fields are dropped; any field the tool doesn't know yet still prints under "details".

Coverage is uneven. A well-documented record carries depth, visibility, parking, an entry heading and points of interest with their depths; a thin one carries only the pin. The points of interest and access notes are the most useful part for a site file: entry directions, landmarks and parking that the other community sources may lack. The depth figures are contributor estimates in round feet converted to metres, a rough range to check bathymetry against, never a datum depth.

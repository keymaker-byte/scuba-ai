# ScubaBoard forum feeds (recent threads, by region or by topic)

<https://www.scubaboard.com/community/forums/>

Recent thread activity from ScubaBoard, read through each forum's own RSS feed rather than by scraping HTML. ScubaBoard runs on XenForo, which publishes a feed for every forum at `/community/forums/<slug>.<id>/index.rss`, the same feed a forum page itself advertises in its `<link rel="alternate">` tag; nothing here reads a page XenForo doesn't already offer as a feed.

- **Region forums.** A place: a country, a coastline, a dive destination (Pacific Northwest, Bonaire, Cozumel, Red Sea are a few of the ones ScubaBoard has a forum for). Use these for local diving signal a prediction tool can't give you: a closed gate, a bloom that just rolled in, a fee change, whether anyone actually got in this weekend. The covered list is fixed inside this tool, independent of whatever regions this workspace has a folder for; a region's steering file adds this tool to its own Tools list whenever ScubaBoard has a forum worth checking for it.
- **Topic forums.** A subject, independent of place: training level, a technical discipline (cave, wreck, rebreather, sidemount), a gear category, safety, classifieds. Use these for gear research or general chatter that isn't tied to a coastline.
- **Use it for.** A quick read on what's currently active in a forum: recent thread titles, who posted, when, and the opening post's excerpt. A keyword search narrows that to threads matching every term given.
- **Not a full-text or historical archive.** Each feed is a rolling window of that forum's newest ~20 threads, with the opening post's excerpt only, not later replies and not older history. A thread that has aged out of the window is invisible to this tool no matter what it contains.
- **Coverage is curated, not the whole site.** ScubaBoard runs several hundred forums; manufacturer fan forums, dive clubs, and yearly "invasion" trip forums are left out as noise. To add one, find the forum's page on scubaboard.com and read its slug and id out of the URL; the feed path is always `.../index.rss` from there, and a forum's id is stable even if ScubaBoard later renames its slug.
- **Community content.** Unmoderated, anecdotal, and only as current as whatever sits in that forum's last ~20 threads right now. Take the behaviour and the pointer, not a number, as a settled fact; verify anything that matters against a live source before it goes in a plan or a site file.
- **No key, no rate limit stated.** A plain RSS fetch, no authentication or specific `User-Agent` required.

## `tools/scubaboard.py`

Standard library only.

```sh
python3 tools/scubaboard.py list                                 # every region and topic covered
python3 tools/scubaboard.py retrieve pacific_northwest           # recent threads, newest first
python3 tools/scubaboard.py retrieve technical_diving --limit 5  # cap how many print
python3 tools/scubaboard.py search cave_diving "sump,line"       # only threads matching every keyword
```

`search`'s keywords are comma-separated and matched case-insensitively against each thread's title and excerpt; a thread must match every keyword given. Each thread prints its title, author, timestamp, excerpt and link. The timestamp is the feed's own `pubDate` in UTC; it dates a forum post, not a dive, so the workspace's local-time convention does not apply.

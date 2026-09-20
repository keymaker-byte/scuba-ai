# ScubaBoard forum feeds (recent threads, by region or by topic)

<https://www.scubaboard.com/community/forums/>

Recent thread activity from ScubaBoard, read through each forum's own RSS feed rather
than by scraping HTML. ScubaBoard runs on XenForo, which publishes a feed for every forum
at `/community/forums/<slug>.<id>/index.rss`, the same feed a forum page itself
advertises in its `<link rel="alternate">` tag; nothing here reads a page XenForo doesn't
already offer as a feed.

Covers two kinds of forum:

- **Region.** A place: a country, a coastline, a dive destination (Pacific Northwest,
  Bonaire, Cozumel, Red Sea are a few of the ones ScubaBoard has a forum for). Use this
  for local diving signal a prediction tool can't give you: a closed gate, a bloom that
  just rolled in, a fee change, whether anyone actually got in this weekend. The covered
  list is fixed inside this tool, independent of whatever regions this workspace happens
  to have a folder for at any given time; a region's steering file should add this tool
  to its own Tools list whenever ScubaBoard has a forum worth checking for it.
- **Topic.** A subject, independent of place: training level, a technical discipline
  (cave, wreck, rebreather, sidemount), a gear category, safety, classifieds. Use this
  for gear research or general chatter that isn't tied to a coastline.

- **Use it for.** A quick read on what's currently active in a forum: recent thread
  titles, who posted, when, and the opening post's excerpt. A keyword search narrows
  that to threads matching every term given.
- **Not a full-text or historical archive.** Each feed is a rolling window of that
  forum's most recent threads, XenForo's own default is the newest ~20, with the opening
  post's excerpt only, not later replies and not older history. `search` filters only
  what the feed currently holds; a thread that has aged out of the window is invisible
  to this tool no matter what it contains.
- **Coverage is curated, not the whole site.** ScubaBoard runs several hundred forums;
  manufacturer fan forums, dive clubs, and yearly "invasion" trip forums are left out as
  noise. `list` prints every region and topic actually covered. To add one, find the
  forum's page on scubaboard.com and read its slug and id out of the URL; the feed path
  is always `.../index.rss` from there, and a forum's id is stable even if ScubaBoard
  later renames its slug.
- **Community content.** Unmoderated, anecdotal, and only as current as whatever sits in
  that forum's last ~20 threads right now. Take the behaviour and the pointer, not a
  number, as a settled fact; verify anything that matters against a live source before
  it goes in a plan or a site file.
- **No key, no rate limit stated.** A plain RSS fetch. ScubaBoard's feeds don't require
  authentication or a specific `User-Agent` to answer.

## `tools/scubaboard.py`

Needs the `feedparser` package (see the workspace README's Platform section).

```sh
python3 tools/scubaboard.py list                                 # every region and topic covered
python3 tools/scubaboard.py retrieve pacific_northwest            # recent threads, newest first
python3 tools/scubaboard.py retrieve technical_diving --limit 5   # cap how many print
python3 tools/scubaboard.py search cave_diving "sump,line"        # only threads matching every keyword
```

`search`'s keywords are comma-separated and matched case-insensitively against each
thread's title and excerpt; a thread must match every keyword given, not just one.

Sample output, `retrieve`:

```
Pacific Northwest  (2 of 20 threads)

  San Juan's Boat Dive
    Land Pinniped  ·  2026-06-05 22:12 UTC
    Hi Everyone, I'm trying to find good boat dive spots in the San Juan islands that I
    can toss an anchor and also have an interesting dive. I usually leave from Anacortes...
    https://scubaboard.com/community/threads/san-juans-boat-dive.665807/
```

The timestamp is the feed's own `pubDate`, UTC, not converted to any dive site's local
time; it dates a forum post, not a dive, so the workspace's local-time convention for
plans and site files does not apply here.

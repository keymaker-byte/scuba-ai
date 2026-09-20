# NW Dive Club (site descriptions and recommendations)

<https://nwdiveclub.com/viewforum.php?f=6>

Community write-ups of how to dive a specific site, and recommendations on where to go. Narrower and more local than a general regional forum, and the better source for site descriptions specifically. Unmoderated and undated as often as not, current but not always coherent: good for signal that something changed, weak for numbers.

- **Use it for.** How a site is dived, where the entry is, what's worth seeing, what to expect. Also site recommendations when picking somewhere new.
- **Take the behaviour, never the numbers.** A forum post's depths are raw computer readings at an unrecorded tide, and its slack times carry no station. Re-derive both against NOAA CO-OPS, and normalize any depth to datum before it is comparable to ours.
- **The live site blocks our fetches (HTTP 403).** Read it through the Wayback Machine: query `https://archive.org/wayback/available?url=<page>` for the closest snapshot, then pull the archived copy. `web.archive.org` refuses the fetch tool too, so `curl --compressed` the snapshot URL. A snapshot lags the live thread, but site descriptions age slowly; check the snapshot date and verify anything time-sensitive against a fresher source.
- **"Closest" isn't always a real page.** The `available` API can hand back a dead capture, a redirect stub with no page content rather than the archived forum thread. Check the fetched content actually has the page before trusting it, and retry `available` or fall back to browsing `web.archive.org/web/*/nwdiveclub.com/*` for a different snapshot if it doesn't.

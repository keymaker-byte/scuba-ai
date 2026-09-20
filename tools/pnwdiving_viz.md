# PNW Diving (recent visibility reports)

<https://pnwdiving.com>

Recent viz reports, the one thing prediction can't give you.

- **Use it for.** What viz has actually been like at the site in the last few days/weeks.
- **Weight by recency.** A report older than about a week through a bloom is stale. Prefer a report from the same site and the same tide phase.
- **What we may take, and what we may not.** The operator drew this line themselves, and we hold to it:
  - **The "Recent Dive Reports" summary table on the home page (`/`) is fair game.** Site, viz, age. It is server-rendered, on an allowed and sitemapped path, and the page itself says *"Press 'View Posts' to see all the details"*, i.e. the summary is the public part. It covers ~28 sites over ~9 days and updates live.
  - **The full report bodies under `/*/reports` are off-limits.** Explicitly `Disallow:`-ed in robots.txt, alongside `Google-Extended: Disallow: /`. Never scrape these. The visibility map on the home page is also off-limits in practice: its points are not in the HTML, they are fetched client-side from the reports API, so getting them would mean driving a headless browser or calling that API, circumvention either way.

## `tools/pnwdiving_viz.py`

Reads exactly the public summary table, once, cached (`pnwdiving_viz.cache_hours` in `tool-config.json`, default 6), converted to metres. The feed is live and updates continuously.

```sh
python3 tools/pnwdiving_viz.py --max-age 3      # only fresh reports
python3 tools/pnwdiving_viz.py --site skyline   # one site
python3 tools/pnwdiving_viz.py --raw            # feet, as the reporter wrote it
```

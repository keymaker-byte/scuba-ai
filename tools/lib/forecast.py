"""The forecast tool's blocks, calls and sources: wind, waves, surface current, weather and hazards at a
dive site, each block answered by the first source in its list that covers the point.

A block is read at one point of the site: wind, weather and hazards at the entry point (the dive area at
a boat site), waves and the surface current at the dive area, out over the water. Every source keeps the
site's own time zone: it takes `tz` and returns local datetimes.

A source is a class with:
  key, name                    its short name and its full name
  blocks                       the blocks it answers, a subset of BLOCKS
  covers(block, lat, lon)      whether it answers the block at the point; None or False passes the point
                               to the next source, a failed request stops the run (Failed)
  read(block, lat, lon, tz, t0, t1)
                               a Reading for the span, local datetimes t0 to t1; a span outside the
                               source's forecast window stops the run (Failed)
plus a section for it under Sources in tools/forecast.md. SOURCES lists, per block, the sources in the
order they are asked.

A Reading is a block's answer from one source: `meta`, the lines naming the source, its grid point and
its update time; `models`, the model names in order, the first primary; `at(t)`, {model: {field: value}}
at a local moment; `hours(t0, t1)`, the local hours of the span it holds; and, for hazards, `alerts`."""
import json
import math
import os
import sys

BLOCKS = ("wind", "waves", "current", "weather", "hazards")
TITLES = {"wind": "Wind", "waves": "Waves", "current": "Surface current",
          "weather": "Weather and temperature", "hazards": "Hazards and warnings"}
COMPASS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
           "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
BANDS = ["go", "marginal", "no go"]
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class Failed(Exception):
    """A source that could not answer: unreachable, refused, unreadable, or asked outside its window."""


def cfg(key, default):
    """The forecast section of tool-config.jsonc; a missing file or key gives the default."""
    from lib import config
    return config.get("forecast", key, default)


LIMITS = {k: float(cfg(k, d)) for k, d in (
    ("go_below_ms", 5.0), ("nogo_above_ms", 8.0), ("short_fetch_shift_ms", 3.0),
    ("gust_margin_ms", 3.0), ("offshore_marginal_ms", 8.0),
    ("waves_go_below_m", 0.5), ("waves_nogo_above_m", 1.0),
    ("fog_visibility_m", 1000.0), ("thunder_probability_pct", 15.0), ("grid_far_km", 5.0))}


def _band(key, default):
    """A call set in tool-config.jsonc: one of go, marginal, no go, or note."""
    v = str(cfg(key, default)).lower()
    if v not in BANDS + ["note"]:
        sys.exit(f"forecast.{key} in tool-config.jsonc is '{v}': use one of go, marginal, no go, note")
    return v


CALLS = {k: _band(k, d) for k, d in (
    ("fog_call", "no go"), ("thunder_call", "no go"),
    ("warning_call", "no go"), ("watch_call", "marginal"), ("advisory_call", "marginal"),
    ("statement_call", "note"))}
SEVERITY = {"go": 0, "note": 0, "marginal": 1, "no go": 2}


# ---------------------------------------------------------------- compass and geometry

def compass(deg):
    return COMPASS[round((deg % 360) / 22.5) % 16]


def point_index(deg):
    return round((deg % 360) / 22.5) % 16


def sectors(specs):
    """'SW-WNW' (clockwise from the first point to the second) or 'N' -> the set of compass indices."""
    out = set()
    for spec in specs or []:
        for part in spec.upper().split(","):
            ends = part.strip().split("-")
            if len(ends) > 2 or any(e not in COMPASS for e in ends):
                sys.exit(f"bad sector '{part.strip()}': use compass points, e.g. SW-WNW or N")
            i, j = COMPASS.index(ends[0]), COMPASS.index(ends[-1])
            out.add(i)
            while i != j:
                i = (i + 1) % 16
                out.add(i)
    return out


def haversine_km(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi, dlmb = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(a))


def destination(lat, lon, bearing, km):
    """The point km along a bearing in degrees true from lat, lon."""
    d, b = km / 6371.0, math.radians(bearing)
    p1, l1 = math.radians(lat), math.radians(lon)
    p2 = math.asin(math.sin(p1) * math.cos(d) + math.cos(p1) * math.sin(d) * math.cos(b))
    l2 = l1 + math.atan2(math.sin(b) * math.sin(d) * math.cos(p1), math.cos(d) - math.sin(p1) * math.sin(p2))
    return math.degrees(p2), (math.degrees(l2) + 540) % 360 - 180


def lerp(v0, v1, frac, circular=False):
    if v0 is None or v1 is None:
        return v0 if frac < 0.5 else v1
    if not circular:
        return v0 + (v1 - v0) * frac
    x = math.sin(math.radians(v0)) + (math.sin(math.radians(v1)) - math.sin(math.radians(v0))) * frac
    y = math.cos(math.radians(v0)) + (math.cos(math.radians(v1)) - math.cos(math.radians(v0))) * frac
    return math.degrees(math.atan2(x, y)) % 360


# ---------------------------------------------------------------- the calls

def call_wind(speed, gust, deg, site):
    """(sector kind, band) for one wind reading against the site's sectors, or None where a value is missing."""
    if speed is None or deg is None or not site.judged:
        return None
    i = point_index(deg)
    kind = "short" if i in site.short else "bad" if i in site.bad else "fine"
    if kind == "fine":
        # Offshore, the risk is surface drift: the sustained speed alone sets the call, and gusts don't count.
        return kind, BANDS[1 if speed > LIMITS["offshore_marginal_ms"] else 0]
    shift = LIMITS["short_fetch_shift_ms"] if kind == "short" else 0.0
    go, nogo = LIMITS["go_below_ms"] + shift, LIMITS["nogo_above_ms"] + shift
    band = 0 if speed < go else 1 if speed <= nogo else 2
    if gust is not None and gust > speed + LIMITS["gust_margin_ms"]:
        band = min(band + 1, 2)  # gusts onto the entry steepen the chop
    return kind, BANDS[band]


def call_waves(height, deg, site):
    """(shore relation, band) for one wave reading: the height banded where the waves come from a
    direction onshore or cross-shore at the entry, go where they come from offshore. None without the
    site's shore relations or a value."""
    if height is None or deg is None or not site.relation:
        return None
    rel = site.relation[point_index(deg)]
    if rel == "offshore":
        return rel, BANDS[0]
    band = 0 if height < LIMITS["waves_go_below_m"] else 1 if height <= LIMITS["waves_nogo_above_m"] else 2
    return rel, BANDS[band]


# Alert events that bear on a dive: the water, the wind over it, the air above it, the shore.
DIVE_EVENTS = ("marine", "gale", "storm", "hurricane", "tropical", "typhoon", "small craft", "hazardous seas",
               "high surf", "rip current", "beach hazard", "coastal flood", "lakeshore flood", "tsunami",
               "thunderstorm", "tornado", "waterspout", "wind", "fog", "smoke", "freezing spray", "heat",
               "cold", "freeze", "squall", "seiche", "ashfall", "air quality", "special weather")


def call_alert(event):
    """The band an alert puts on a dive: a warning no go, a watch or an advisory marginal, a statement
    or anything else a note; None for an event that does not bear on a dive."""
    e = event.lower()
    if not any(k in e for k in DIVE_EVENTS):
        return None
    for kind in ("warning", "watch", "advisory"):
        if e.endswith(kind):
            return CALLS[f"{kind}_call"]
    return CALLS["statement_call"]


def call_weather(row):
    """(what decides, band) for one weather reading: fog and thunder by their configured calls, the
    more severe of the two; go with neither."""
    found = [(what, CALLS[f"{what}_call"]) for what in ("fog", "thunder") if row.get(what)]
    if not found:
        return "clear of fog and thunder", BANDS[0]
    worst = max(SEVERITY[b] for _, b in found)
    return " and ".join(w for w, b in found if SEVERITY[b] == worst), next(b for _, b in found if SEVERITY[b] == worst)


def call_text(c):
    return "" if c is None else f"{c[1]} ({c[0]})"


# ---------------------------------------------------------------- the site

class Site:
    """What the tool reads at a site: the land point (the entry, the dive area at a boat site), the sea
    point (the dive area), the zone, the wind sectors and the shore relation of each compass point."""

    def __init__(self, land, sea, tz, bad=(), short=(), relation=None, lake=False, path=None, boat=False):
        self.land, self.sea, self.tz = land, sea, tz
        self.bad, self.short = sectors(bad), sectors(short)
        self.relation, self.lake, self.path, self.boat = relation, lake, path, boat
        self.judged = bool(self.bad or self.short)
        self.raw_sectors = None
        self.faces = None      # the entry shore facing (the dive area's at a boat site), degrees true
        self.swim_out = None   # {"bearing", "distance_m", "off_entry_faces"} from the entry to the dive area
        self.inland = None  # the bearing inland from the entry, opposite its shore facing

    def point(self, block):
        return self.sea if block in ("waves", "current") else self.land


def site_from_file(path, tz=None):
    """The site JSON: its dive area, its wind section's entry point, sectors and shore relations, and
    its tz. Stops the run on anything it cannot read or that disagrees."""
    try:
        with open(path) as f:
            doc = json.load(f)
    except OSError as e:
        sys.exit(f"could not read --file {path}: {e}")
    except json.JSONDecodeError as e:
        sys.exit(f"could not parse JSON in {path}: {e}")
    w = doc.get("wind")
    if not isinstance(w, dict) or "sectors" not in w:
        sys.exit(f"{path} has no wind section with sectors: run `shore_exposure.py extract --site {path}`")
    p = w["extract_point"]
    if (p["lat"], p["lon"]) != (doc.get("lat"), doc.get("lon")):
        sys.exit(f"{path}: the site's coordinate ({doc.get('lat')}, {doc.get('lon')}) is not where its wind section "
                 f"was taken ({p['lat']}, {p['lon']}): run `shore_exposure.py extract --site {path}` again")
    zone = doc.get("tz")
    if tz and zone and tz != zone:
        sys.exit(f"--tz {tz} is not the site's own zone, {zone}, from {path}")
    zone = zone or tz
    if not zone:
        sys.exit(f"{path} has no tz: give --tz")
    e = p.get("entry")
    sea = (doc["lat"], doc["lon"])
    land = (e["lat"], e["lon"]) if e else sea
    s = w["sectors"]
    relation = [None] * 16
    for row in w.get("fetch", []):
        relation[COMPASS.index(row["from"])] = row["relation"]
    site = Site(land, sea, zone, s["bad"], s["short"] + s["mixed"],
                relation if None not in relation else None,
                lake=doc.get("seabed_datum") == "LAKE", path=path, boat=e is None)
    site.raw_sectors = s
    faces = w.get("entry_faces") if e else w.get("dive_area_faces")
    site.inland = (faces + 180) % 360 if faces is not None else None
    site.faces = faces
    site.swim_out = w.get("swim_out")
    site.calm_only = bool(w.get("calm_only"))
    return site


def site_by_hand(near, tz, bad, short, sea=None):
    if not near or not tz:
        missing = [o for o, v in (("--near", near), ("--tz", tz)) if not v]
        sys.exit(f"give {' and '.join(missing)}, or --file with the site JSON")
    land = tuple(near)
    return Site(land, tuple(sea) if sea else land, tz, bad or (), short or ())


# ---------------------------------------------------------------- choosing a source

def sources():
    from lib import nws, open_meteo  # imported here so lib/forecast.py stays importable on its own
    return {
        "wind": [nws.Gridpoint(), open_meteo.Weather()],
        "weather": [nws.Gridpoint(), open_meteo.Weather()],
        "waves": [open_meteo.Marine()],
        "current": [open_meteo.Marine()],
        "hazards": [nws.Alerts()],
    }


def pick(block, site, only=None):
    """The source that answers the block at the site, or (None, why) where none covers it. `only`
    names a source key to use for the wind and weather blocks, past the location's own choice."""
    if site.lake and block in ("waves", "current"):
        return None, ("a lake: no wave model reads it, and its chop is the wind call's" if block == "waves"
                      else "a lake: no tidal or ocean current, and the water temperature is the region's")
    lat, lon = site.point(block)
    chain = sources()[block]
    if only and block in ("wind", "weather"):
        chain = [s for s in chain if s.key == only]
        if not chain:
            sys.exit(f"--source {only}: no source by that key answers {block}")
    points = [(lat, lon)] + ([site.sea] if block == "hazards" and site.sea != (lat, lon) else [])
    for src in chain:
        if any(src.covers(block, *p) for p in points):
            return src, None
    names = ", ".join(s.name for s in chain)
    return None, f"no source covers {lat:.4f}, {lon:.4f} ({names})"

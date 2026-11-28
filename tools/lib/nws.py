"""The National Weather Service's sources for the forecast tool: the gridpoint forecast (wind and weather)
and the active alerts (hazards), both from api.weather.gov, US coordinates and US marine zones only.

Coverage comes from NWS's own zones: the gridpoint answers a point inside a public forecast zone or a
coastal marine zone, and the alerts a point inside any zone (public, county, coastal or offshore). A
point in no zone passes to the next source; a failed request stops the run."""
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from lib import config
from lib.forecast import Failed, LIMITS, destination

BASE = "https://api.weather.gov"
KMH = 1 / 3.6
DURATION = re.compile(r"P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?)?$")
_cache = {}


def get(url):
    if url in _cache:
        return _cache[url]
    if not config.user_agent_email():
        raise Failed("user_agent_email not set in tool-config.jsonc (NWS requires a contact in its User-Agent)")
    req = urllib.request.Request(url, headers={"User-Agent": config.user_agent(),
                                               "Accept": "application/geo+json"})
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                doc = json.load(r)
            _cache[url] = doc
            return doc
        except urllib.error.HTTPError as e:
            try:
                detail = json.loads(e.read()).get("detail", "")
            except ValueError:
                detail = ""
            if e.code >= 500 and attempt == 0:
                time.sleep(2)  # NWS answers a passing 500 now and then; one more try before stopping
                continue
            raise Failed(f"NWS: HTTP {e.code} {detail} ({url})".rstrip())
        except urllib.error.URLError as e:
            if attempt == 0:
                time.sleep(2)
                continue
            raise Failed(f"NWS unreachable: {e.reason} ({url})")
        except (OSError, ValueError) as e:
            raise Failed(f"NWS read failed: {e} ({url})")


def zones(lat, lon):
    """The NWS zones holding the point: [(id, type)], type public, county, coastal, offshore or fire."""
    doc = get(f"{BASE}/zones?point={lat:.4f},{lon:.4f}")
    return [(f["properties"]["id"], f["properties"]["type"]) for f in doc.get("features", [])]


def intervals(layer, tz):
    """A gridpoint layer as [(start, end, value)] in local time; values hold constant over each span."""
    out = []
    for v in (layer or {}).get("values", []):
        start, dur = v["validTime"].split("/")
        d, h, m = (int(x or 0) for x in DURATION.match(dur).groups())
        t0 = datetime.fromisoformat(start).astimezone(tz)
        out.append((t0, t0 + timedelta(days=d, hours=h, minutes=m), v["value"]))
    return out


def value_at(spans, t):
    for t0, t1, v in spans:
        if t0 <= t < t1:
            return v
    return None


def span_at(spans, t):
    for t0, t1, v in spans:
        if t0 <= t < t1:
            return t0, t1, v
    return None


def weather_text(items):
    """NWS's weather layer entry as words: 'chance light rain, patchy fog'."""
    words = []
    for w in items or []:
        if not w.get("weather"):
            continue
        parts = [w.get("coverage"), w.get("intensity"), w["weather"]]
        words.append(" ".join(p.replace("_", " ") for p in parts if p))
    return ", ".join(words)


class GridReading:
    def __init__(self, block, pt, grid, layers, sky, lat, lon, tz):
        self.block, self.tz = block, tz
        self.layers, self.sky = layers, sky
        rel = pt.get("relativeLocation", {}).get("properties", {})
        updated = datetime.fromisoformat(grid["updateTime"]).astimezone(tz)
        self.models = ["NWS"]
        self.meta = [f"NWS gridpoint {pt['gridId']} {pt['gridX']},{pt['gridY']} (2.5 km cell, elevation "
                     f"{grid['elevation']['value']:.0f} m, near {rel.get('city', '?')}, {rel.get('state', '?')}), "
                     f"for {lat:.4f}, {lon:.4f}",
                     f"updated {updated:%Y-%m-%d %H:%M}"]
        cover = layers["windSpeed"]
        self.first, self.last = (cover[0][0], cover[-1][1]) if cover else (None, None)

    def hours(self, t0, t1):
        out, t = [], t0
        while t < t1:
            if self.first <= t < self.last:
                out.append(t)
            t += timedelta(hours=1)
        return out

    def at(self, t):
        L = self.layers
        if self.block == "wind":
            spd, gu = value_at(L["windSpeed"], t), value_at(L["windGust"], t)
            return {"NWS": {"speed": spd * KMH if spd is not None else None,
                            "dir": value_at(L["windDirection"], t),
                            "gust": gu * KMH if gu is not None else None}}
        q = span_at(L["quantitativePrecipitation"], t)
        rate = None
        if q and q[2] is not None:
            rate = q[2] / max((q[1] - q[0]).total_seconds() / 3600, 1)
        vis = value_at(L["visibility"], t)
        wx = value_at(L["weather"], t) or []
        kinds = {w.get("weather") for w in wx}
        thunder = value_at(L["probabilityOfThunder"], t)
        if "thunderstorms" in kinds and not thunder:
            thunder = None  # the text names it; the probability layer is empty
        return {"NWS": {
            "air": value_at(L["temperature"], t),
            "feels": value_at(L["apparentTemperature"], t),
            "dew": value_at(L["dewpoint"], t),
            "rh": value_at(L["relativeHumidity"], t),
            "cloud": value_at(L["skyCover"], t),
            "pop": value_at(L["probabilityOfPrecipitation"], t),
            "rain_mm_h": rate,
            "vis_m": vis,
            "fog": bool(kinds & {"fog", "freezing_fog"}) or (vis is not None and vis < LIMITS["fog_visibility_m"]),
            "thunder_pct": thunder,
            "thunder": "thunderstorms" in kinds or bool(thunder and thunder >= LIMITS["thunder_probability_pct"]),
            "sky": value_at(self.sky, t) or "",
            "wx": weather_text(wx),
        }}


class Gridpoint:
    """NWS's 2.5 km gridpoint forecast: wind speed, direction and gust, and the weather."""
    key = "nws"
    name = "NWS gridpoint forecast"
    blocks = ("wind", "weather")

    def covers(self, block, lat, lon):
        return any(t in ("public", "coastal") for _, t in zones(lat, lon))

    def read(self, block, lat, lon, tz, t0, t1, **_):
        tz = ZoneInfo(tz)
        pt = get(f"{BASE}/points/{lat:.4f},{lon:.4f}")["properties"]
        grid = get(pt["forecastGridData"])["properties"]
        keys = (("windSpeed", "windDirection", "windGust") if block == "wind" else
                ("windSpeed", "temperature", "apparentTemperature", "dewpoint", "relativeHumidity", "skyCover",
                 "probabilityOfPrecipitation", "quantitativePrecipitation", "visibility", "weather",
                 "probabilityOfThunder"))
        layers = {k: intervals(grid.get(k), tz) for k in keys}
        sky = []
        if block == "weather":
            hourly = get(pt["forecastHourly"] + "?units=si")["properties"]["periods"]
            sky = [(datetime.fromisoformat(p["startTime"]).astimezone(tz),
                    datetime.fromisoformat(p["endTime"]).astimezone(tz), p["shortForecast"]) for p in hourly]
        r = GridReading(block, pt, grid, layers, sky, lat, lon, tz)
        if r.first is None or t1 <= r.first or t0 >= r.last:
            span = f"{r.first:%Y-%m-%d %H:%M} to {r.last:%Y-%m-%d %H:%M}" if r.first else "nothing"
            raise Failed(f"outside the NWS forecast window (it covers {span}, local)")
        return r


class AlertReading:
    def __init__(self, alerts, ids, note):
        self.models = ["NWS"]
        self.alerts = alerts
        self.meta = [f"NWS active alerts for zones {', '.join(ids)}{note}"]


class Alerts:
    """NWS's active alerts for every zone holding the entry or the dive area: warnings, watches,
    advisories and statements, issued up to a few days ahead."""
    key = "nws"
    name = "NWS alerts"
    blocks = ("hazards",)

    def covers(self, block, lat, lon):
        return any(t != "fire" for _, t in zones(lat, lon))

    def read(self, block, lat, lon, tz, t0, t1, also=None, inland=None, **_):
        tz = ZoneInfo(tz)
        found = zones(lat, lon)
        note = ""
        if inland is not None and not any(t == "public" for _, t in found):
            # NWS's zone outlines can put a beach entry in the water: walk inland, away from the
            # entry's shore facing, until a public zone holds the point, and take its zones too.
            for step in range(1, 11):
                p = destination(lat, lon, inland, 0.1 * step)
                more = zones(*p)
                if any(t == "public" for _, t in more):
                    found += more
                    note = f" (the land zones read {100 * step} m inland of the entry)"
                    break
        if also:
            found += zones(*also)
        ids = []
        for zid, t in found:
            if t != "fire" and zid not in ids:
                ids.append(zid)
        doc = get(f"{BASE}/alerts/active?" + urllib.parse.urlencode({"zone": ",".join(ids)}))
        seen, out = set(), []
        for f in doc.get("features", []):
            p = f["properties"]
            if p.get("status") != "Actual" or p.get("messageType") == "Cancel":
                continue
            start = p.get("onset") or p.get("effective")
            end = p.get("ends") or p.get("expires")
            a0 = datetime.fromisoformat(start).astimezone(tz) if start else None
            a1 = datetime.fromisoformat(end).astimezone(tz) if end else None
            if (a1 and a1 <= t0) or (a0 and a0 >= t1):
                continue
            key = (p["event"], a0, a1)
            if key in seen:
                continue
            seen.add(key)
            out.append({"event": p["event"], "severity": p.get("severity"), "start": a0, "end": a1,
                        "headline": p.get("headline") or "", "area": p.get("areaDesc") or "",
                        "sender": p.get("senderName") or ""})
        out.sort(key=lambda a: (a["start"] or t0))
        return AlertReading(out, ids, note)

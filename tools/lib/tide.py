"""The tide tool's sources: every network of tide prediction stations the tide tool reads, each
kept on this machine under tools/db/tide/<key>/ and downloaded as it is first needed. A station is
named by its network's own ID, or as <key>:<id> where two networks share an ID; `station` finds
the source that owns it, and `near` lists every source's stations around a point.

A source is a class in SOURCES with:
  key, name, datum, db              its short name, full name, the datum its heights are above,
                                    and the folder it caches into
  failed                            the start of the message a failed download stops the run with,
                                    which stops `verify --all` too, to be resumed later
  listing()                         {"fetched", "stations": {id: {name, lat, lon, kind, ref}}},
                                    kind "reference" or "subordinate", ref the reference's ID or None;
                                    downloaded when missing
  owns(sid), cached(sid)            whether the ID is one of its stations, and whether it is on this machine
  load(sid, quiet)                  the station's file, downloaded when missing
  provenance(doc)                   the line naming what a prediction was computed from, and when it was fetched
  height(doc, t), extremes(doc, start, end)
                                    metres above the datum at UTC datetime t, and the highs and lows
                                    between two UTC datetimes as [(utc datetime, "H" or "L", metres)]
  constants(doc)                    (constants, None) for a station predicted from its own harmonic
                                    constants, in lib/tide_harmonics.py's form, or (None, why not)
  compare(doc, day0, days, height_tol, time_tol)
                                    the station against the network's live predictions: a dict with
                                    "ok", saved as one line of the source's _verify.jsonl
  report(r)                         that dict as lines to print
plus a section for it under Sources in tools/tide.md."""
import math

from lib import noaa_tides


class Refused(Exception):
    """A station no source owns, or one two sources share."""


class Noaa:
    """NOAA CO-OPS' tide prediction stations: about 3,500 on every US coast and a scattering
    abroad, reference stations from their harmonic constants and subordinate ones from their
    reference moved by NOAA's corrections. Heights above MLLW."""
    key = "noaa"
    name = "NOAA CO-OPS"
    datum = "MLLW"
    db = noaa_tides.DB
    failed = "NOAA:"

    def listing(self):
        raw = noaa_tides.station_list()
        return {"fetched": raw["fetched"],
                "stations": {sid: {"name": s["name"], "lat": s["lat"], "lon": s["lon"],
                                   "kind": "subordinate" if s["type"] == "S" else "reference",
                                   "ref": s["ref"] if s["type"] == "S" else None}
                             for sid, s in raw["stations"].items()}}

    def owns(self, sid):
        return sid in noaa_tides.station_list()["stations"]

    def cached(self, sid):
        return noaa_tides.cached(sid)

    def load(self, sid, quiet=False):
        return noaa_tides.station(sid, quiet)

    def provenance(self, doc):
        if doc["type"] == "S":
            ref = noaa_tides.reference(doc)
            return (f"subordinate to {ref['id']} {ref['name']}; computed locally from NOAA's corrections as "
                    f"fetched {doc['fetched']} and constants as fetched {ref['fetched']}")
        noaa_tides.reference(doc)
        return f"computed locally from NOAA's constants as fetched {doc['fetched']}"

    def height(self, doc, t):
        return noaa_tides.height_at(doc, t)

    def extremes(self, doc, start, end):
        return noaa_tides.extremes(doc, start, end)

    def constants(self, doc):
        if doc["type"] == "S":
            return None, "a subordinate station, defined by its highs and lows alone"
        why = noaa_tides.unusable(doc)
        return (None, why) if why else (noaa_tides.constants(doc), None)

    def compare(self, doc, day0, days, height_tol, time_tol):
        return noaa_tides.compare(doc, day0, days, height_tol, time_tol)

    def report(self, r):
        if "error" in r:
            return [f"NOAA: no predictions to compare with ({r['error']})"]
        out = []
        if "height_n" in r:
            out.append(f"height, {r['height_n']} six-minute values: worst difference {r['height_worst']:.3f} m, "
                       f"rms {r['height_rms']:.3f} m")
        out.append(f"events, {r['events_n']} highs and lows: worst time difference {r['time_worst']:.1f} min, "
                   f"worst height difference {r['event_worst']:.3f} m, {r['unmatched']} unmatched")
        if r.get("new_year"):
            out.append(f"{r['new_year']} at the turn of the UTC year left out")
        return out


SOURCES = (Noaa,)


def sources(key=None):
    """Every source, or the one named by its key."""
    every = [s() for s in SOURCES]
    if key is None:
        return every
    found = [s for s in every if s.key == key]
    if not found:
        raise Refused(f"No tide source is named {key}. The sources are: " + ", ".join(s.key for s in every) + ".")
    return found


class Station:
    """One station as the tide tool reads it, whichever source it comes from."""

    def __init__(self, source, doc):
        self.source, self.doc = source, doc
        self.id, self.name = doc["id"], doc["name"]
        self.lat, self.lon = doc["lat"], doc["lon"]
        self.datum = source.datum

    def provenance(self):
        return self.source.provenance(self.doc)

    def height(self, t):
        return self.source.height(self.doc, t)

    def extremes(self, start, end):
        return self.source.extremes(self.doc, start, end)

    def constants(self):
        return self.source.constants(self.doc)

    def compare(self, day0, days, height_tol, time_tol):
        return self.source.compare(self.doc, day0, days, height_tol, time_tol)

    def report(self, r):
        return self.source.report(r)


def split(name):
    """(source key or None, station ID) from "9447130" or "noaa:9447130"."""
    if ":" in name:
        key, sid = name.split(":", 1)
        return key.lower(), sid
    return None, name


def owner(name):
    """(source, station ID) for a station name; Refused when no source owns it, or more than one."""
    key, sid = split(name)
    found = [s for s in sources(key) if s.owns(sid)]
    if not found:
        where = f"the {key} source" if key else "any tide source"
        raise Refused(f"{sid} is not a station in {where}. List stations with `stations --near LAT LON`.")
    if len(found) > 1:
        raise Refused(f"{sid} is a station in more than one source ({', '.join(s.key for s in found)}); "
                      f"name it as {found[0].key}:{sid}.")
    return found[0], sid


def station(name, quiet=False):
    """The station a name refers to, downloaded when missing."""
    src, sid = owner(name)
    return Station(src, src.load(sid, quiet))


def km(lat1, lon1, lat2, lon2):
    scale = math.cos(math.radians(lat1))
    return math.hypot((lat2 - lat1) * 60.0, (lon2 - lon1) * 60.0 * scale) * 1.852


def near(lat, lon, n=None, radius_km=None, key=None):
    """Every source's stations around a point, nearest first: [(km, source, ID, entry)]."""
    rows = []
    for s in sources(key):
        for sid, e in s.listing()["stations"].items():
            d = km(lat, lon, e["lat"], e["lon"])
            if radius_km is None or d <= radius_km:
                rows.append((d, s, sid, e))
    rows.sort(key=lambda r: r[0])
    return rows[:n] if n else rows


def in_boxes(boxes, key=None):
    """Every source's stations inside any of the boxes [S, W, N, E]: [(source, ID, entry)], by source and ID."""
    inside = lambda lat, lon: any(s <= lat <= n and w <= lon <= e for s, w, n, e in boxes)  # noqa: E731
    return [(s, sid, e) for s in sources(key) for sid, e in sorted(s.listing()["stations"].items())
            if inside(e["lat"], e["lon"])]


def label(src, sid):
    """A station's name as the tool prints it: the bare ID with one source, <key>:<id> with several."""
    return sid if len(SOURCES) == 1 else f"{src.key}:{sid}"

"""The seabed at a point from whichever bathymetry covers it, each source downloading through
its own tool whatever it needs that is not yet on this machine. Each source answers a signed elevation in metres, negative under water, against
its own datum, or None where it holds nothing; `Seabed` asks them in order and names the one
that answered. A new bathymetry joins by adding a class with `name`, `datum` and `elevation`
to SOURCES."""
from lib import gsc, ncei
from lib.dem_tiles import Tile


class NceiTiles:
    """NOAA NCEI's coastal DEM, 1/9 arc-second, the US coasts: `lib/ncei.py`'s tiles, each one
    downloaded the first time a point inside it is asked for (about 200 MB a tile)."""
    name = "NCEI coastal DEM"
    datum = "NAVD 88"

    def __init__(self):
        self.open = {}

    def elevation(self, lat, lon):
        path = ncei.tile_path(lat, lon)
        if path is None:
            return None
        t = self.open.get(path)
        if t is None:
            t = self.open[path] = Tile(path)
        return t.value(*t.pixel(lat, lon))


class GscWestCoast:
    """The GSC Canada West Coast DEM, 10 m, British Columbia and the Salish Sea: `lib/gsc.py`'s one
    GeoTIFF, taken out of NRCan's zip the first time a point inside its extent is asked for (7.3 GB).
    Its sea depths are on CHS Chart Datum, a metre or two from NAVD 88, well inside what a
    station's height above the seabed, as a fraction of the depth, is sensitive to."""
    name = gsc.NAME
    datum = "CHS Chart Datum"

    def elevation(self, lat, lon):
        if not gsc.in_box(lat, lon):
            return None
        t = gsc.tile()
        return t.value(*gsc.pixel(t, lat, lon))


class BonaireSurveys:
    """Bonaire's and Klein Bonaire's surveys, read through the depth tool's own chain in
    `lib/depth.py`: the DCBD 2 m grid from the shore to about 20 m, the Navy's 2019 20 m grid on
    the leeward wall and slope, the Navy's 1970 to 1972 soundings beyond them, and the seams that
    join each to the next. Each is downloaded, or ordered by hand, as the depth tool says. A plain
    observed depth, so the seabed here is the one the depth tool and the map's depth layer read."""
    name = "Bonaire surveys"
    datum = "none (a plain observed depth)"

    def __init__(self):
        from lib import depth
        self.chain = [depth.Dcbd(), depth.DCBD_NAVY, depth.Nlhs(), depth.LEGACY_SEAM, depth.Nlhs1970()]
        self.names = {id(s): s.name for s in self.chain}

    def elevation(self, lat, lon):
        for s in self.chain:
            if not s.covers(lat, lon):
                continue
            r = s.answer(lat, lon)
            if r["depth"] is None and r.get("nodata"):
                continue
            if r["depth"] is None:
                return None
            self.name = s.name
            return -r["depth"]
        return None


SOURCES = (NceiTiles, GscWestCoast, BonaireSurveys)


class Seabed:
    """Every source, asked in order. `elevation` answers (metres, source name) or (None, None)."""

    def __init__(self):
        self.sources = [s() for s in SOURCES]

    def elevation(self, lat, lon):
        for s in self.sources:
            e = s.elevation(lat, lon)
            if e is not None:
                return e, s.name
        return None, None

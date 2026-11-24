"""The seabed at a point from whichever bathymetry covers it, each source downloading through
its own tool whatever it needs that is not yet on this machine. Each source answers a signed elevation in metres, negative under water, against
its own datum, or None where it holds nothing; `Seabed` asks them in order and names the one
that answered. A new bathymetry joins by adding a class with `name`, `datum` and `elevation`
to SOURCES."""
from lib.dcbd import grid as dcbd_grid, utm as dcbd_utm
from lib import ncei
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


class DcbdBonaire:
    """The DCBD coastal bathymetry of Bonaire and Klein Bonaire, 2 m, from the shore to about
    20 m deep: `dcbd_depth`'s grid, downloaded on first use."""
    name = "DCBD coastal bathymetry of Bonaire"
    datum = "about sea level"

    def __init__(self):
        self.grid = None
        self.tried = False

    def elevation(self, lat, lon):
        if not -69.0 <= lon <= -67.9 or not 11.8 <= lat <= 12.5:
            return None
        if not self.tried:
            self.grid, self.tried = dcbd_grid(), True
        if self.grid is None:
            return None
        p = self.grid.pixel(*dcbd_utm(lat, lon))
        return self.grid.value(*p) if p else None


SOURCES = (NceiTiles, DcbdBonaire)


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

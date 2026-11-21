"""The seabed at a point from whichever bathymetry covers it, read only from data already on
this machine. Each source answers a signed elevation in metres, negative under water, against
its own datum, or None where it holds nothing; `Seabed` asks them in order and names the one
that answered. A new bathymetry joins by adding a class with `name`, `datum` and `elevation`
to SOURCES."""
from lib.dcbd import cached as dcbd_cached, utm as dcbd_utm
from lib.dem_tiles import CachedTiles


class NceiTiles:
    """NOAA NCEI's coastal DEM, 1/9 arc-second, the US coasts: the tiles `ncei_depth` cached."""
    name = "NCEI coastal DEM"
    datum = "NAVD 88"

    def __init__(self):
        self.tiles = CachedTiles()

    def elevation(self, lat, lon):
        return self.tiles.elevation(lat, lon)


class DcbdBonaire:
    """The DCBD coastal bathymetry of Bonaire and Klein Bonaire, 2 m, from the shore to about
    20 m deep: the grid `dcbd_depth` cached."""
    name = "DCBD coastal bathymetry of Bonaire"
    datum = "about sea level"

    def __init__(self):
        self.grid = None
        self.tried = False

    def elevation(self, lat, lon):
        if not -69.0 <= lon <= -67.9 or not 11.8 <= lat <= 12.5:
            return None
        if not self.tried:
            self.grid, self.tried = dcbd_cached(), True
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

"""The depth tool's sources: every bathymetry the depth tool reads, and which one answers at a
point. Each source names what it is, says whether it covers a point, and answers the depth below
the datum of the water there (MLLW in US tidal water, CHS Chart Datum in Canadian, a lake's own surface in a lake,
none on Bonaire's reef, where the depth is a plain observed one), with the reading behind it. `answer_on` gives the first source in SOURCES that covers the point, so a
more detailed source listed ahead of a broader one wins where both cover it. Every answer carries
`key`, the name of its datum from lib/datums.py (MLLW, CHS, LAKE or NONE), and `answer_on` picks the
first source that answers on a given datum, so a site's depth always comes on the datum its tide
is predicted above.

A new bathymetry joins by adding a class with `name`, `coverage`, `covers`, `answer`, `fetch`,
`verify` and `selftest` to SOURCES, and a section for it under Sources in tools/depth.md."""
from lib import datums, dcbd, gsc, ncei, vdatum


class Refused(Exception):
    """A point no source covers."""


class Ncei:
    """NOAA NCEI's ninth arc-second coastal DEM, about 3 m, the US coasts and their lakes:
    `lib/ncei.py`'s tiles, each downloaded the first time a point inside it is asked for."""
    name = "NCEI coastal DEM"
    coverage = "the US coasts and their lakes, from NOAA NCEI's ninth arc-second tiles"

    def covers(self, lat, lon):
        """A tile on NOAA's list holding data at the point. A tile on the border holds none on the
        Canadian side, which falls to the next source."""
        return ncei.has_tile(lat, lon) and ncei.has_data(lat, lon)

    def answer(self, lat, lon):
        a = ncei.answer(lat, lon)
        r = a.pop("dem")
        key = {"sea": datums.MLLW, "lake": datums.LAKE}.get(a["water"])
        return {**a, "key": key, "source": f"{self.name}, tile {r['source']} (~{r['res_m']:.0f} m)", "reading": r}

    def fetch(self, boxes, workers):
        """Every tile touching the boxes; the number that failed."""
        return ncei.fetch(boxes, workers)

    def verify(self, lat, lon, a):
        return ncei.verify(lat, lon, a["reading"])

    def selftest(self):
        print(f"{self.name}: the NAVD 88 to MLLW offset against VDatum's own service")
        return vdatum.selftest()


class Gsc:
    """The Geological Survey of Canada's Canada West Coast topo-bathymetric DEM, Version 2, at
    10 m, Canada's west coast and the Salish Sea: `lib/gsc.py`'s one GeoTIFF, taken out of NRCan's
    zip the first time a point inside its extent is asked for. Depths below CHS Chart Datum."""
    name = gsc.NAME
    coverage = "Canada's west coast and the Salish Sea, from the GSC Canada West Coast DEM, Version 2"

    def covers(self, lat, lon):
        return gsc.has_data(lat, lon)

    def answer(self, lat, lon):
        a = gsc.answer(lat, lon)
        r = a.pop("dem")
        key = datums.CHS if a["water"] == "sea" else None
        return {**a, "key": key, "source": f"{self.name}, {r['source']} (~{r['res_m']:.0f} m)", "reading": r}

    def fetch(self, boxes, workers):
        """The DEM, when any box touches it; the number that failed."""
        return gsc.fetch(boxes, workers)

    def verify(self, lat, lon, a):
        return gsc.verify(lat, lon, a["reading"])

    def selftest(self):
        print(f"{self.name}: the BC Albers projection the DEM is gridded on")
        return gsc.selftest()


class Dcbd:
    """E. Meesters' 2020 coastal bathymetry of Bonaire and Klein Bonaire on the Dutch Caribbean
    Biodiversity Database, at 2 m, from the shore to about 20 m deep: `lib/dcbd.py`'s one GeoTIFF,
    taken out of DCBD's zip the first time a point inside its extent is asked for. A plain observed
    depth, on NONE: Bonaire's tide of about 30 cm sits inside the grid's own precision."""
    name = dcbd.NAME
    coverage = "Bonaire's and Klein Bonaire's reef to about 20 m, from the DCBD coastal bathymetry"

    def covers(self, lat, lon):
        return dcbd.covers(lat, lon)

    def answer(self, lat, lon):
        a = dcbd.answer(lat, lon)
        r = a.pop("dem")
        key = datums.NONE if a["water"] == "sea" else None
        return {**a, "key": key, "source": f"{self.name}, {r['source']} (~{r['res_m']:.0f} m)", "reading": r}

    def fetch(self, boxes, workers):
        """The grid, when any box touches it; the number that failed."""
        return dcbd.fetch(boxes, workers)

    def verify(self, lat, lon, a):
        return dcbd.verify(lat, lon, a["reading"])

    def selftest(self):
        print(f"{self.name}: the UTM zone 19N projection the grid is on")
        return dcbd.selftest()


SOURCES = (Dcbd, Ncei, Gsc)


def sources():
    return [s() for s in SOURCES]


def answer_on(lat, lon, datum=None):
    """(source, answer) at a point: the first covering source's answer, or with a datum the first
    covering source whose answer is on it; Refused when none is, naming what each one gave."""
    every = sources()
    covering = [s for s in every if s.covers(lat, lon)]
    if not covering:
        raise Refused(f"No depth source covers {lat}, {lon}. The sources are: "
                      + "; ".join(f"{s.name}, {s.coverage}" for s in every) + ".")
    gave = []
    for s in covering:
        r = s.answer(lat, lon)
        if datum is None or r["key"] == datum:
            return s, r
        gave.append(f"{s.name} " + (f"answers {r['depth']:.1f} m below {r['key']}" if r["key"] else f"gives no depth ({r['why']})"))
    raise Refused(f"No depth source answers on {datum} ({datums.MEANING[datum]}) at {lat}, {lon}: " + "; ".join(gave) + ".")

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
import math

from lib import datums, dcbd, gsc, ncei, nlhs, nlhs_1970, vdatum


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


# --- Bonaire: three surveys, finest first, and the seams between them ------------------------
#
# DCBD's 2 m grid answers where it has data; past its edge the Navy's 2019 20 m grid, lined up
# with DCBD; past both the Navy's 1970 to 1972 soundings. Each step out is joined by a seam: over
# a band past the edge of the finer surveys, the coarser one's depth plus the two's difference at
# the nearest edge point, applied in full there and fading to none across the band, so the depth
# runs on from one survey to the next with no step.

def _dcbd_state(lat, lon):
    """"data" where DCBD has a pixel under water, "dry" at a pixel at or above the surface, "none"
    where it holds no data or the point lies off its grid."""
    if not dcbd.in_box(lat, lon):
        return "none"
    t = dcbd.tile()
    row, col = dcbd.pixel(t, lat, lon)
    if not (0 <= row < t.h and 0 <= col < t.w):
        return "none"
    v = t.value(row, col)
    return "none" if v is None else ("data" if v < 0 else "dry")


def _navy_domain(lat, lon):
    """Where the Navy's 2019 grid answers: DCBD silent, inside the survey's extent."""
    return nlhs.in_box(lat, lon) and _dcbd_state(lat, lon) == "none"


LEGACY_SEAWARD_M = 100.0   # how near the finer surveys a 1970s answer must lie seaward of them


def _legacy_domain(lat, lon):
    """Where the 1970s soundings answer: DCBD silent, no cell of the 2019 grid, at sea, and seaward
    of the finer surveys. A point within LEGACY_SEAWARD_M of their nearest data answers only when
    it lies farther from the coastline than that data does, so the strip between the shore and
    DCBD's first pixel, which the soundings never resolved, takes no depth from them."""
    if not nlhs_1970.in_box(lat, lon) or _dcbd_state(lat, lon) != "none":
        return False
    x, y = dcbd.utm(lat, lon)
    if nlhs.in_box(lat, lon) and nlhs.raw(x, y) is not None:
        return False
    if ncei.inland(lat, lon):
        return False
    found = [e for f in (_dcbd_edge, _navy_edge_raw) if (e := f(x, y, LEGACY_SEAWARD_M))]
    if not found:
        return nlhs_1970.coast_m(x, y) >= LEGACY_SEAWARD_M
    _, ex, ey, _ = min(found)
    return nlhs_1970.coast_m(x, y) > nlhs_1970.coast_m(ex, ey)


def _navy_edge_raw(x, y, limit_m):
    """(distance, x, y, None) of the 2019 grid's nearest cell within limit_m: its position only."""
    e = nlhs._nearest(x, y, limit_m) if nlhs.in_box(*dcbd.from_utm(x, y)) else None
    return (e[0], x + e[1], y + e[2], None) if e else None


def _dcbd_edge(x, y, limit_m):
    """(distance, x, y, depth) of DCBD's nearest pixel under water within limit_m."""
    t = dcbd.tile()
    row, col = dcbd.pixel_utm(t, x, y)
    e = dcbd.nearest_data(t, x, y, row, col, limit_m, wet=True)
    return (e[0], x + e[1], y + e[2], -e[3]) if e else None


def _navy_edge(x, y, limit_m):
    """(distance, x, y, depth) of the 2019 grid's nearest cell within limit_m, its depth the one
    the finer surveys answer there: the DCBD to Navy seam's where it covers the cell."""
    e = nlhs._nearest(x, y, limit_m) if nlhs.in_box(*dcbd.from_utm(x, y)) else None
    if not e:
        return None
    ex, ey = x + e[1], y + e[2]
    lat, lon = dcbd.from_utm(ex, ey)
    z = DCBD_NAVY.depth_at(lat, lon) if DCBD_NAVY.covers(lat, lon) else nlhs.depth(ex, ey)
    return (e[0], ex, ey, z)


class Seam:
    """The transition from finer surveys to a coarser one over the first `band_m` past the finer
    ones' edge: the coarser survey's depth plus the two's difference at the nearest edge point,
    applied in full there and fading to none at `band_m`."""

    def __init__(self, name, coverage, band_m, edges, domain, outer, outer_name, note, step_m, drop_m):
        self.name, self.coverage, self.BAND_M = name, coverage, band_m
        self._edges, self._domain, self._outer, self._outer_name, self._note = edges, domain, outer, outer_name, note
        self.STEP_M, self.DROP_M = step_m, drop_m

    def _edge(self, lat, lon):
        """(x, y, (distance, ex, ey, depth)) at a point in the band, or None."""
        if not self._domain(lat, lon):
            return None
        x, y = dcbd.utm(lat, lon)
        if self._outer(x, y) is None:
            return None
        found = [e for f in self._edges if (e := f(x, y, self.BAND_M))]
        if not found:
            return None
        e = min(found)
        return (x, y, e) if e[0] < self.BAND_M else None

    def covers(self, lat, lon):
        return self._edge(lat, lon) is not None

    def depth_at(self, lat, lon):
        return self._blend(*self._edge(lat, lon))[0]

    def _blend(self, x, y, e):
        d, ex, ey, inner = e
        here = self._outer(x, y)
        there = self._outer(ex, ey)
        if there is None:
            there = here   # the coarser survey has nothing under the edge point: take the difference at the point
        gap = inner - there
        w = 1 - d / self.BAND_M
        return here + w * gap, d, inner, here, there, gap, w

    def answer(self, lat, lon):
        z, d, inner, here, there, gap, w = self._blend(*self._edge(lat, lon))
        return {"water": "sea", "depth": z, "datum": dcbd.DATUM, "key": datums.NONE, "why": None,
                "detail": f"{d:.0f} m past the edge of the finer surveys, which read {inner:.1f} m there; the "
                          f"{self._outer_name} reads {here:.1f} m here and {there:.1f} m under that edge point, so "
                          f"{w:.0%} of the {gap:+.1f} m difference between them is added{self._note()}",
                "source": f"{self.name}", "reading": None}

    def fetch(self, boxes, workers):
        return 0   # it reads the surveys on either side, each fetched as its own source

    def verify(self, lat, lon, a):
        print(f"  {self.name} reads the surveys on either side; verify a point on each of them")
        return True

    def selftest(self):
        """The step left where the finer surveys end: the seam's depth STEP_M past the nearest edge
        point, toward a sample of points in the band, against that edge point's own depth, and the
        same step had the coarser survey answered there alone. It passes when the seam leaves no
        more than DROP_M of step at the median, the drop of a steep wall over STEP_M, and less than
        the coarser survey alone at the median and at p90."""
        print(f"{self.name}: the step where the finer surveys end, against the {self._outer_name} alone")
        seam, alone = [], []
        for x, y in self._samples():
            lat, lon = dcbd.from_utm(x, y)
            got = self._edge(lat, lon)
            if not got or got[2][0] <= self.STEP_M:
                continue
            d, ex, ey, inner = got[2]
            px, py = ex + (x - ex) / d * self.STEP_M, ey + (y - ey) / d * self.STEP_M
            plat, plon = dcbd.from_utm(px, py)
            if not self.covers(plat, plon):
                continue
            o = self._outer(px, py)
            seam.append(abs(self.depth_at(plat, plon) - inner))
            alone.append(abs(o - inner))
        if len(seam) < 30:
            print(f"  only {len(seam)} points in the band")
            print("  FAIL")
            return False
        seam.sort()
        alone.sort()
        med, p90 = (lambda a: a[len(a) // 2]), (lambda a: a[9 * len(a) // 10])
        ok = med(seam) <= self.DROP_M and med(seam) < med(alone) and p90(seam) < p90(alone)
        print(f"  {len(seam)} points; step {self.STEP_M:.0f} m past the edge: seam median {med(seam):.2f} m, "
              f"p90 {p90(seam):.2f} m; {self._outer_name} alone median {med(alone):.2f} m, p90 {p90(alone):.2f} m "
              f"(passing within {self.DROP_M:.1f} m at the median)")
        print("  PASS" if ok else "  FAIL")
        return ok


class _DcbdNavySeam(Seam):
    def __init__(self):
        super().__init__(
            "DCBD to Navy 2019 seam", "the first 40 m past the edge of the DCBD survey of Bonaire, where "
            "the Navy's 2019 survey holds data", 40.0, [_dcbd_edge], _navy_domain, nlhs.depth,
            "Navy's 2019 survey", lambda: f"; the 2019 survey is {nlhs.offset_note()}", 2.0, 2.5)

    def _samples(self):
        """Every 2019 cell centre outside DCBD's data."""
        for (i, j) in nlhs.grid()["cells"]:
            yield i * nlhs.CELL, j * nlhs.CELL


class _LegacySeam(Seam):
    def __init__(self):
        super().__init__(
            "Bonaire surveys to Navy 1970s seam", "the first 100 m past the edge of the DCBD survey and "
            "the Navy's 2019 survey of Bonaire, where the Navy's 1970s soundings answer", 100.0,
            [_dcbd_edge, _navy_edge], _legacy_domain, nlhs_1970.depth, "Navy's 1970s soundings",
            lambda: "; the 1970s soundings are rough, a depth beyond diving limits", 5.0, 6.0)

    def _samples(self):
        """Every 1970s sounding no deeper than 150 m: the ones near enough the reef to fall in the band."""
        for x, y, z in nlhs_1970.data()["points"]:
            if z <= 150:
                yield x, y


DCBD_NAVY = _DcbdNavySeam()
LEGACY_SEAM = _LegacySeam()


class Nlhs:
    """The Royal Netherlands Navy Hydrographic Service's 2019 multibeam survey of Bonaire's
    leeward coast, a 20 m grid from about 1 m to 230 m deep: `lib/nlhs.py`'s order from
    SeaDataNet, saved by hand, read where the DCBD survey has no data, interpolated between cell
    centres, and lined up with DCBD by the offset measured where both hold flat bottom."""
    name = nlhs.NAME
    coverage = "Bonaire's leeward coast from Karpata to the Invisibles, 1 to 230 m, from the Navy's 2019 survey"

    def covers(self, lat, lon):
        return _navy_domain(lat, lon)

    def answer(self, lat, lon):
        a = nlhs.answer(lat, lon)
        r = a.pop("dem")
        key = datums.NONE if a["water"] == "sea" else None
        return {**a, "key": key, "source": f"{self.name}, {r['source']} (~{r['res_m']:.0f} m), {nlhs.CREDIT}",
                "reading": r}

    def fetch(self, boxes, workers):
        return nlhs.fetch(boxes, workers)

    def verify(self, lat, lon, a):
        return nlhs.verify(lat, lon, a["reading"])

    def selftest(self):
        print(f"{self.name}: the soundings on the 20 m UTM zone 19N grid, and read back at each cell")
        return nlhs.selftest()


class Nlhs1970:
    """The Royal Netherlands Navy Hydrographic Service's single-beam surveys of 1970 to 1972 around
    Bonaire and Klein Bonaire, about 1 m to 2,600 m deep: `lib/nlhs_1970.py`'s order from
    SeaDataNet, saved by hand, read where neither DCBD nor the 2019 survey has data, interpolated
    from the soundings around a point. A rough depth, beyond diving limits."""
    name = nlhs_1970.NAME
    coverage = "the waters around Bonaire and Klein Bonaire to about 2,600 m, from the Navy's 1970 to 1972 soundings"

    def covers(self, lat, lon):
        return _legacy_domain(lat, lon)

    def answer(self, lat, lon):
        a = nlhs_1970.answer(lat, lon)
        r = a.pop("dem")
        key = datums.NONE if a["water"] == "sea" else None
        return {**a, "key": key, "source": f"{self.name}, {r['source']}, {nlhs_1970.CREDIT}", "reading": r}

    def fetch(self, boxes, workers):
        return nlhs_1970.fetch(boxes, workers)

    def verify(self, lat, lon, a):
        return nlhs_1970.verify(lat, lon, a["reading"])

    def selftest(self):
        print(f"{self.name}: each sounding read back, and left out and answered by its neighbours")
        return nlhs_1970.selftest()


SOURCES = (Dcbd, lambda: DCBD_NAVY, Nlhs, lambda: LEGACY_SEAM, Nlhs1970, Ncei, Gsc)


def sources():
    return [s() for s in SOURCES]


def answer_on(lat, lon, datum=None):
    """(source, answer) at a point: the first covering source's answer with a depth, or with a datum
    the first covering source whose answer is on it; Refused when none is, naming what each one
    gave. An answer marked nodata (the source has no survey at the point) passes the point on to
    the next covering source; any other answer with no depth (land, a shore) stands."""
    every = sources()
    covering = [s for s in every if s.covers(lat, lon)]
    if not covering:
        raise Refused(f"No depth source covers {lat}, {lon}. The sources are: "
                      + "; ".join(f"{s.name}, {s.coverage}" for s in every) + ".")
    gave, silent = [], []
    for s in covering:
        r = s.answer(lat, lon)
        if datum is None and r["depth"] is None and r.get("nodata"):
            silent.append((s, r))
            continue
        if datum is None or r["key"] == datum:
            return s, r
        gave.append(f"{s.name} " + (f"answers {r['depth']:.1f} m below {r['key']}" if r["key"] else f"gives no depth ({r['why']})"))
    if silent:
        s, r = silent[0]
        return s, {**r, "why": "; ".join(f"{t.name}: {q['why']}" for t, q in silent)}
    raise Refused(f"No depth source answers on {datum} ({datums.MEANING[datum]}) at {lat}, {lon}: " + "; ".join(gave) + ".")

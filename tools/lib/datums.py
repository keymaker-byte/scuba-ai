"""The datums a depth is measured below, one short name each, shared by the depth tool, the tide
tool and the site JSON's `seabed_datum`, so the three can be checked against each other by name.

A depth below a datum plus the tide height above that same datum is the depth below the
surface; that sum holds only when both sides name the same datum, so every tool that reads or
writes a depth or a tide height carries one of these names with it.

  MLLW   Mean Lower Low Water, NOAA's tidal datum: US charts and NOAA's tide predictions.
  CHS    CHS Chart Datum: Canadian charts and the Canadian Hydrographic Service's tide
         predictions; on the Pacific coast, Lower Low Water, Large Tide, which sits about 1 m
         below MLLW in the Salish Sea.
  LAKE   A lake's own surface. A lake has no tide; its level moves with the seasons.
  NONE   No datum: a plain observed depth, in water whose tide is too small to normalize against.

LAKE and NONE carry no tide, so the tide height above them is 0 by definition and the same
arithmetic holds everywhere."""
import sys

MLLW, CHS, LAKE, NONE = "MLLW", "CHS", "LAKE", "NONE"

MEANING = {
    MLLW: "Mean Lower Low Water, NOAA's tidal datum in US water",
    CHS: "CHS Chart Datum, the datum of Canadian charts and CHS's tide predictions "
         "(Lower Low Water, Large Tide on the Pacific coast)",
    LAKE: "the lake's own surface, with no tide",
    NONE: "no datum: a plain observed depth, in water with too little tide to normalize against",
}

NO_TIDE = (LAKE, NONE)


def check(name, where="--datum"):
    """A datum name as given, or stop the run naming the ones there are."""
    if name not in MEANING:
        sys.exit(f"{where}: {name!r} is not a datum. The datums are: "
                 + "; ".join(f"{k} ({v})" for k, v in MEANING.items()) + ".")
    return name


def of_site(doc, path):
    """A site JSON's `seabed_datum`, or stop the run saying how to add it."""
    name = doc.get("seabed_datum")
    if name is None:
        sys.exit(f"{path}: no seabed_datum, so its seabed_m cannot be matched to a tide. Add the datum the depth "
                 "tool gave the depth on (`depth.py at --file` prints it): one of " + ", ".join(MEANING) + ".")
    return check(name, f"{path}: seabed_datum")

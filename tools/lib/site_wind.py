"""A site JSON's wind section, as the wind forecast tools read it: the point to forecast at and the
sectors to call against, both written by shore_exposure.py's extract."""
import json
import sys


def apply_file(a):
    """With --file, fill a.near, a.bad, a.short and a.tz from the site JSON; without it, require
    --near and --tz. Stops the run on anything it cannot read or that disagrees."""
    if not getattr(a, "file", None):
        missing = [o for o, v in (("--near", a.near), ("--tz", a.tz)) if not v]
        if missing:
            sys.exit(f"give {' and '.join(missing)}, or --file with the site JSON")
        return
    path = a.file
    if a.near or a.bad or a.short:
        sys.exit("--file names the point and the sectors: give it without --near, --bad or --short")
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
    tz = doc.get("tz")
    if a.tz and tz and a.tz != tz:
        sys.exit(f"--tz {a.tz} is not the site's own zone, {tz}, from {path}")
    a.tz = a.tz or tz
    if not a.tz:
        sys.exit(f"{path} has no tz: give --tz")
    e = p.get("entry")
    a.near = [e["lat"], e["lon"]] if e else [doc["lat"], doc["lon"]]
    s = w["sectors"]
    a.bad = s["bad"]
    a.short = s["short"] + s["mixed"]
    where = "entry point" if e else "dive area, a boat site"
    print(f"  site            {path}")
    print(f"  forecast at     the {where}, {a.near[0]}, {a.near[1]}")
    print(f"  sectors         bad {','.join(s['bad']) or 'none'}; short fetch {','.join(s['short']) or 'none'}; "
          f"mixed {','.join(s['mixed']) or 'none'}" + ("; calm only" if w.get("calm_only") else ""))

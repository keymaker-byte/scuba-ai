"""Open-Meteo's sources for the forecast tool, at any coordinate worldwide: the weather API (wind from two
models, ECMWF IFS with GFS as a cross-check, and the weather from the primary one) and the marine API
(waves from two wave models, the surface current and the water temperature from Mercator's ocean model).

Open-Meteo answers from a grid: every reading names the grid point it was served from and its distance
from the point asked for. A marine reading of null everywhere means no ocean model holds that water, an
answer about coverage; a refused or unreachable request stops the run."""
import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from lib.forecast import Failed, LIMITS, cfg, haversine_km, lerp

WEATHER = "https://api.open-meteo.com/v1/forecast"
MARINE = "https://marine-api.open-meteo.com/v1/marine"
DISAGREE = {"wind": (3.0, 30.0), "waves": (0.3, 30.0)}  # m/s or m, and degrees, between the two models

WMO = {0: "clear", 1: "mainly clear", 2: "partly cloudy", 3: "overcast", 45: "fog", 48: "freezing fog",
       51: "light drizzle", 53: "drizzle", 55: "heavy drizzle", 56: "freezing drizzle", 57: "freezing drizzle",
       61: "light rain", 63: "rain", 65: "heavy rain", 66: "freezing rain", 67: "freezing rain",
       71: "light snow", 73: "snow", 75: "heavy snow", 77: "snow grains", 80: "light showers", 81: "showers",
       82: "violent showers", 85: "snow showers", 86: "snow showers", 95: "thunderstorm",
       96: "thunderstorm, hail", 99: "thunderstorm, heavy hail"}

FIELDS = {
    "wind": {"speed": "wind_speed_10m", "dir": "wind_direction_10m", "gust": "wind_gusts_10m"},
    "weather": {"air": "temperature_2m", "feels": "apparent_temperature", "dew": "dew_point_2m",
                "rh": "relative_humidity_2m", "cloud": "cloud_cover", "pop": "precipitation_probability",
                "rain_mm_h": "precipitation", "vis_m": "visibility", "code": "weather_code", "cape": "cape"},
    "waves": {"height": "wave_height", "dir": "wave_direction", "period": "wave_period",
              "wind_wave_height": "wind_wave_height", "wind_wave_dir": "wind_wave_direction",
              "wind_wave_period": "wind_wave_period", "swell_height": "swell_wave_height",
              "swell_dir": "swell_wave_direction", "swell_period": "swell_wave_period",
              "swell2_height": "secondary_swell_wave_height", "swell2_dir": "secondary_swell_wave_direction",
              "swell2_period": "secondary_swell_wave_period"},
    "current": {"speed": "ocean_current_velocity", "dir": "ocean_current_direction",
                "sst": "sea_surface_temperature"},
}
CIRCULAR = {"dir", "wind_wave_dir", "swell_dir", "swell2_dir"}
STEP = {"code"}  # taken from the nearer hour, never interpolated


def models_for(block):
    if block == "wind":
        return [cfg("wind_model", "ecmwf_ifs"), cfg("wind_cross_check_model", "gfs_seamless")]
    if block == "weather":
        return [cfg("weather_model", "ecmwf_ifs")]
    if block == "waves":
        return [cfg("wave_model", "meteofrance_wave"), cfg("wave_cross_check_model", "ecmwf_wam025")]
    return [cfg("ocean_model", "meteofrance_currents")]


def get(url):
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        try:
            reason = json.loads(e.read()).get("reason", "")
        except ValueError:
            reason = ""
        raise Failed(f"Open-Meteo: HTTP {e.code} {reason} ({url})".rstrip())
    except urllib.error.URLError as e:
        raise Failed(f"Open-Meteo unreachable: {e.reason} ({url})")
    except (OSError, ValueError) as e:
        raise Failed(f"Open-Meteo read failed: {e} ({url})")


class Reading:
    def __init__(self, block, doc, models, lat, lon, tz, api):
        self.block, self.models, self.tz = block, models, ZoneInfo(tz)
        h = doc["hourly"]
        self.times = [datetime.fromisoformat(t).replace(tzinfo=self.tz) for t in h["time"]]
        self.series = {}
        for m in models:
            col = {}
            for f, name in FIELDS[block].items():
                key = name if len(models) == 1 else f"{name}_{m}"
                vals = h.get(key, [None] * len(self.times))
                if block == "current" and f == "speed":
                    vals = [v / 3.6 if v is not None else None for v in vals]  # km/h to m/s
                col[f] = vals
            self.series[m] = col
        self.dist_km = haversine_km(lat, lon, doc["latitude"], doc["longitude"])
        far = self.dist_km > LIMITS["grid_far_km"]
        role = (f"{models[0]} (primary), {models[1]} (cross-check)" if len(models) > 1 else models[0])
        self.meta = [f"Open-Meteo {api}, {role}",
                     f"grid point {doc['latitude']:.4f}, {doc['longitude']:.4f}, {self.dist_km:.1f} km from "
                     f"{lat:.4f}, {lon:.4f}" + (f" (elevation {doc['elevation']:.0f} m)" if api == "weather API"
                                                and doc.get("elevation") is not None else "")
                     + ("  <-- far: the reading is the water out there, not at the site"
                        if far and block in ("waves", "current") else "")]
        key = {"waves": "height", "current": "speed"}.get(block)
        self.empty = bool(key) and all(v is None for m in models for v in self.series[m][key])

    def hours(self, t0, t1):
        return [t for t in self.times if t0 <= t < t1]

    def at(self, t):
        if not self.times or t < self.times[0] or t > self.times[-1]:
            raise Failed(f"{t:%Y-%m-%d %H:%M} falls outside the Open-Meteo series "
                         f"({self.times[0]:%Y-%m-%d %H:%M} to {self.times[-1]:%Y-%m-%d %H:%M})")
        i = max(k for k, tt in enumerate(self.times) if tt <= t)
        j = min(i + 1, len(self.times) - 1)
        span = (self.times[j] - self.times[i]).total_seconds()
        frac = (t - self.times[i]).total_seconds() / span if span else 0.0
        out = {}
        for m in self.models:
            row = {}
            for f, vals in self.series[m].items():
                if f in STEP:
                    row[f] = vals[i] if frac < 0.5 else vals[j]
                else:
                    row[f] = lerp(vals[i], vals[j], frac, circular=f in CIRCULAR)
            if self.block == "weather":
                code = row.get("code")
                code = int(code) if code is not None else None
                row["code"] = code
                row["wx"] = WMO.get(code, "") if code is not None else ""
                row["sky"] = row["wx"]
                vis = row.get("vis_m")
                row["fog"] = code in (45, 48) or (vis is not None and vis < LIMITS["fog_visibility_m"])
                row["thunder"] = code in (95, 96, 99)
                row["thunder_pct"] = None
            out[m] = row
        return out

    def disagrees(self, row1, row2):
        lim = DISAGREE.get(self.block)
        f = "speed" if self.block == "wind" else "height"
        if not lim or None in (row1.get(f), row2.get(f), row1.get("dir"), row2.get("dir")):
            return False
        d = abs(row1["dir"] - row2["dir"])
        if abs(row1[f] - row2[f]) > lim[0]:
            return True
        # a direction means little on ripples: the waves' is compared once both models read real waves
        return min(d, 360 - d) > lim[1] and (self.block == "wind" or min(row1[f], row2[f]) >= lim[0])


def _read(api, url, block, lat, lon, tz, t0, t1, extra=None):
    models = models_for(block)
    q = {"latitude": lat, "longitude": lon, "hourly": ",".join(FIELDS[block].values()),
         "models": ",".join(models), "timezone": tz,
         "start_date": t0.date().isoformat(), "end_date": (t1 - timedelta(seconds=1)).date().isoformat()}
    q.update(extra or {})
    return Reading(block, get(url + "?" + urllib.parse.urlencode(q)), models, lat, lon, tz, api)


class Weather:
    """Open-Meteo's weather API: wind from ECMWF IFS and GFS, the weather from ECMWF IFS."""
    key = "open-meteo"
    name = "Open-Meteo weather"
    blocks = ("wind", "weather")

    def covers(self, block, lat, lon):
        return True

    def read(self, block, lat, lon, tz, t0, t1, **_):
        return _read("weather API", WEATHER, block, lat, lon, tz, t0, t1, {"wind_speed_unit": "ms"})


class Marine:
    """Open-Meteo's marine API: waves from Meteo-France's MFWAM and ECMWF's WAM, the surface current
    and the water temperature from Mercator's ocean model (SMOC)."""
    key = "open-meteo"
    name = "Open-Meteo marine"
    blocks = ("waves", "current")

    def covers(self, block, lat, lon):
        return True

    def read(self, block, lat, lon, tz, t0, t1, **_):
        return _read("marine API", MARINE, block, lat, lon, tz, t0, t1)

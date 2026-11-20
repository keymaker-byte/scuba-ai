// Tide heights for the map viewer's depth layer, reproduced from NOAA's harmonic constants
// exactly as tools/noaa_tide.py predicts them.
//
// `tools/noaa_tide.py export-map` writes map/tides/stations.js (window.MAP_TIDES): each
// reference station's constituents, prepared for every year the map may ask about (the
// argument constant with its node phase and the amplitude with its node factor, held for the
// UTC year as NOAA holds them), its mean sea level and highest tide of the year above MLLW,
// and its heights at sample moments, which selfCheck() reproduces; plus the points where
// NAVD 88's height above MLLW is known. A height at any other place is blended from the
// nearest stations, weighted by the inverse square of the distance.
(function (root) {
  'use strict';

  const RAD = Math.PI / 180;
  const TIDE_NEIGHBOURS = 3;
  const DATUM_NEIGHBOURS = 4;

  function km(lat1, lon1, lat2, lon2) {
    const x = (lon2 - lon1) * Math.cos((lat1 + lat2) / 2 * RAD);
    return 111.2 * Math.hypot(x, lat2 - lat1);
  }

  // The k nearest points to (lat, lon), with inverse distance squared weights summing to 1.
  function blend(points, lat, lon, k) {
    const near = points.map((p, i) => ({ i, d: km(lat, lon, p.lat, p.lon) }))
      .sort((a, b) => a.d - b.d).slice(0, k);
    if (near[0].d < 0.01) return [{ i: near[0].i, w: 1 }];
    const inv = near.map(n => 1 / (n.d * n.d));
    const sum = inv.reduce((a, b) => a + b, 0);
    return near.map((n, j) => ({ i: n.i, w: inv[j] / sum }));
  }

  class TideModel {
    constructor(data) {
      this.data = data;
      this.stations = data.stations;
      this.datum = data.datum;
      this.epoch = Date.parse(data.epoch);
      this._levelsAt = null;
      this._levels = null;
    }

    // Mean longitudes (degrees) at a moment: moon s, sun h, lunar perigee p, solar perigee p1.
    _longitudes(ms) {
      const T = (ms - this.epoch) / 86400000 / 36525;
      return [
        270.434164 + 481267.8831417 * T - 0.0011333 * T * T,
        279.696678 + 36000.768925 * T + 0.0003025 * T * T,
        334.329556 + 4069.0340333 * T - 0.010325 * T * T,
        281.220833 + 1.719175 * T + 0.0004528 * T * T,
      ];
    }

    // Height above MLLW at station i at a moment (ms since 1970, UTC).
    height(i, ms) {
      const st = this.stations[i];
      const year = new Date(ms).getUTCFullYear();
      const y = st.years[year];
      if (!y) {
        throw new Error(`the tide stations cover ${this.data.first_year} to ${this.data.last_year}; ` +
          'regenerate map/tides/stations.js with noaa_tide.py export-map');
      }
      const [s, h, p, p1] = this._longitudes(ms);
      const d = new Date(ms);
      const T = 15 * (d.getUTCHours() + d.getUTCMinutes() / 60 + d.getUTCSeconds() / 3600
        + d.getUTCMilliseconds() / 3.6e6) + 180;
      let z = st.msl;
      for (let k = 0; k < st.coef.length; k++) {
        const c = st.coef[k];
        z += y.amp[k] * Math.cos(RAD * (c[0] * T + c[1] * s + c[2] * h + c[3] * p + c[4] * p1 + y.arg[k]));
      }
      return z;
    }

    // Every station's height at a moment, kept for the last moment asked.
    levels(ms) {
      if (this._levelsAt !== ms) {
        this._levels = Float64Array.from(this.stations, (_, i) => this.height(i, ms));
        this._levelsAt = ms;
      }
      return this._levels;
    }

    tideBlend(lat, lon) { return blend(this.stations, lat, lon, TIDE_NEIGHBOURS); }

    // NAVD 88's height above MLLW at a place, and the highest tide of the year there.
    datumAt(lat, lon) {
      const navd88 = blend(this.datum, lat, lon, DATUM_NEIGHBOURS)
        .reduce((a, n) => a + n.w * this.datum[n.i].navd88, 0);
      const high = this.tideBlend(lat, lon)
        .reduce((a, n) => a + n.w * this.stations[n.i].high, 0);
      return { navd88, high };
    }

    // The tide above MLLW at a place and moment, with the stations it came from.
    tideAt(lat, lon, ms) {
      const lv = this.levels(ms);
      const parts = this.tideBlend(lat, lon);
      return {
        height: parts.reduce((a, n) => a + n.w * lv[n.i], 0),
        parts: parts.map(n => ({ name: this.stations[n.i].name, weight: n.w })),
      };
    }

    // Reproduce the heights noaa_tide.py computed at its sample moments.
    selfCheck() {
      let worst = 0;
      this.stations.forEach((st, i) => {
        for (const c of st.checks) worst = Math.max(worst, Math.abs(this.height(i, c.t) - c.h));
      });
      return { ok: worst <= 0.002, worst };
    }
  }

  root.DiveTides = { TideModel };
})(typeof window !== 'undefined' ? window : globalThis);

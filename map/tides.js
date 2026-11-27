// Tide heights for the map viewer's depth layer, reproduced from each station's harmonic constants
// exactly as tools/tide.py predicts them.
//
// `tools/map_export.py tides` writes map/tides/stations.js (window.MAP_TIDES): the stations of each
// tide source, grouped into families by the datum their heights are above, the family a depth
// pixel's seabed is on. Two ways of summing constants:
//   noaa     NOAA's stations, each constituent prepared for every year the map may ask about (the
//            argument constant with its node phase and the amplitude with its node factor, held for
//            the UTC year as NOAA holds them): tools/lib/tide_harmonics.py.
//   foreman  CHS's stations, constants fitted by Foreman's method, with node factors and phases
//            worked out from the satellites of Foreman's table once per UTC day, at noon, for the
//            station's latitude: tools/lib/foreman.py.
// Each station carries its heights at sample moments, which selfCheck() reproduces, and its highest
// tide of the year. The tide at any place is blended from the family's nearest stations, weighted by
// the inverse square of the distance.
(function (root) {
  'use strict';

  const RAD = Math.PI / 180;
  const TAU = 2 * Math.PI;
  const TIDE_NEIGHBOURS = 3;
  const DAY_MS = 86400000;

  function km(lat1, lon1, lat2, lon2) {
    const x = (lon2 - lon1) * Math.cos((lat1 + lat2) / 2 * RAD);
    return 111.2 * Math.hypot(x, lat2 - lat1);
  }

  // The k nearest points to (lat, lon), with inverse distance squared weights summing to 1.
  function blend(points, lat, lon, k) {
    const near = points.map((p, i) => ({ i, d: km(lat, lon, p.lat, p.lon) }))
      .sort((a, b) => a.d - b.d).slice(0, k);
    if (!near.length) return [];
    if (near[0].d < 0.01) return [{ i: near[0].i, w: 1 }];
    const inv = near.map(n => 1 / (n.d * n.d));
    const sum = inv.reduce((a, b) => a + b, 0);
    return near.map((n, j) => ({ i: n.i, w: inv[j] / sum }));
  }

  // NOAA's form: tools/lib/tide_harmonics.py.
  class NoaaFamily {
    constructor(fam, span) {
      this.stations = fam.stations;
      this.epoch = Date.parse(fam.epoch);
      this.span = span;
    }

    // Mean longitudes (degrees) at a moment: moon s, sun h, lunar perigee p, solar perigee p1.
    _longitudes(ms) {
      const T = (ms - this.epoch) / DAY_MS / 36525;
      return [
        270.434164 + 481267.8831417 * T - 0.0011333 * T * T,
        279.696678 + 36000.768925 * T + 0.0003025 * T * T,
        334.329556 + 4069.0340333 * T - 0.010325 * T * T,
        281.220833 + 1.719175 * T + 0.0004528 * T * T,
      ];
    }

    height(i, ms) {
      const st = this.stations[i];
      const y = st.years[new Date(ms).getUTCFullYear()];
      if (!y) throw new Error(this.span);
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
  }

  // Foreman's form: tools/lib/foreman.py, line for line.
  class ForemanFamily {
    constructor(fam, span) {
      this.stations = fam.stations;
      this.table = fam.table;
      this.epoch = Date.parse(fam.epoch);
      this.span = span;
      this.days = this.stations.map(() => new Map());   // per station: UTC day -> [u, f] per constituent
      // the latitude factors of the satellites, per station (Nodal.__init__)
      this.r = this.stations.map(st => {
        let lat = st.fitLat;
        if (Math.abs(lat) < 5) lat = Math.sign(lat) * 5 || 5;
        const sl = Math.sin(lat * RAD);
        return [1.0, 0.36309 * (1.0 - 5.0 * sl * sl) / sl, 2.59808 * sl];
      });
    }

    // [tau, s, h, p, N', p'] in cycles at a moment (t_astron).
    astro(ms) {
      const d = (ms - this.epoch) / DAY_MS;
      const D = d / 10000.0;
      const args = [1.0, d, D * D, D * D * D];
      const rows = [[270.434164, 13.1763965268, -0.0000850, 0.000000039],
        [279.696678, 0.9856473354, 0.00002267, 0.0],
        [334.329556, 0.1114040803, -0.0007739, -0.00000026],
        [-259.183275, 0.0529539222, -0.0001557, -0.000000050],
        [281.220844, 0.0000470684, 0.0000339, 0.000000070]];
      const a = rows.map(r => ((r[0] * args[0] + r[1] * args[1] + r[2] * args[2] + r[3] * args[3]) / 360.0) % 1.0);
      const tau = (((d + 0.5) % 1.0) + 1.0) % 1.0 + a[1] - a[0];
      return [tau, ...a];
    }

    _main(name, A, r, memo) {
      let got = memo.get(name);
      if (!got) {
        let re = 1.0, im = 0.0;
        for (const [d1, d2, d3, ph, amp, lf] of this.table[name].sats) {
          const uu = TAU * (d1 * A[3] + d2 * A[4] + d3 * A[5] + ph);
          re += amp * r[lf] * Math.cos(uu);
          im += amp * r[lf] * Math.sin(uu);
        }
        got = [Math.atan2(im, re) / TAU, Math.hypot(re, im)];
        memo.set(name, got);
      }
      return got;
    }

    // [u cycles, f] for each of a station's constituents on the UTC day of a moment.
    uf(i, ms) {
      const day = Math.floor(ms / DAY_MS);
      const cache = this.days[i];
      let out = cache.get(day);
      if (!out) {
        const A = this.astro(day * DAY_MS + DAY_MS / 2);
        const memo = new Map(), r = this.r[i];
        out = this.stations[i].names.map(n => {
          const sh = this.table[n].shallow;
          if (!sh) return this._main(n, A, r, memo);
          let u = 0.0, f = 1.0;
          for (const [k, m] of sh) {
            const [um, fm] = this._main(m, A, r, memo);
            u += k * um;
            f *= fm ** Math.abs(k);
          }
          return [u, f];
        });
        if (cache.size > 64) cache.clear();
        cache.set(day, out);
      }
      return out;
    }

    height(i, ms) {
      const st = this.stations[i];
      const A = this.astro(ms);
      const uf = this.uf(i, ms);
      let z = st.z0;
      for (let k = 0; k < st.names.length; k++) {
        const c = this.table[st.names[k]];
        let v = 0.0;
        if (c.shallow) {
          for (const [kk, m] of c.shallow) {
            const mc = this.table[m];
            let s = mc.semi;
            for (let j = 0; j < 6; j++) s += mc.dood[j] * A[j];
            v += kk * s;
          }
        } else {
          v = c.semi;
          for (let j = 0; j < 6; j++) v += c.dood[j] * A[j];
        }
        const ph = TAU * (v + uf[k][0]);
        const [a, b] = st.ab[k];
        z += uf[k][1] * (a * Math.cos(ph) + b * Math.sin(ph));
      }
      return z;
    }
  }

  class TideModel {
    constructor(data) {
      this.data = data;
      const span = `the tide stations cover ${data.first_year} to ${data.last_year}; ` +
        'regenerate map/tides/stations.js with map_export.py tides';
      this.families = {};
      for (const [key, fam] of Object.entries(data.families)) {
        this.families[key] = fam.model === 'foreman' ? new ForemanFamily(fam, span) : new NoaaFamily(fam, span);
      }
      this._levels = {};
    }

    family(key) {
      const f = this.families[key];
      if (!f) throw new Error(`map/tides/stations.js holds no ${key} family`);
      return f;
    }

    // Every station of a family at a moment, kept for the last moment asked.
    levels(key, ms) {
      const got = this._levels[key];
      if (got && got.ms === ms) return got.v;
      const f = this.family(key);
      const v = Float64Array.from(f.stations, (_, i) => f.height(i, ms));
      this._levels[key] = { ms, v };
      return v;
    }

    // The family's nearest stations to a place, with their weights.
    tideBlend(key, lat, lon) { return blend(this.family(key).stations, lat, lon, TIDE_NEIGHBOURS); }

    // The highest tide of the year at a place, above the family's datum.
    highAt(key, lat, lon) {
      const st = this.family(key).stations;
      return this.tideBlend(key, lat, lon).reduce((a, n) => a + n.w * st[n.i].high, 0);
    }

    // The tide at a place and moment, above the family's datum, with the stations it came from.
    tideAt(key, lat, lon, ms) {
      const lv = this.levels(key, ms);
      const st = this.family(key).stations;
      const parts = this.tideBlend(key, lat, lon);
      return {
        height: parts.reduce((a, n) => a + n.w * lv[n.i], 0),
        parts: parts.map(n => ({ name: st[n.i].name, weight: n.w })),
      };
    }

    // Reproduce the heights the tide tool's own summation gave at every station's sample moments.
    selfCheck() {
      let worst = 0, where = '';
      for (const [key, f] of Object.entries(this.families)) {
        f.stations.forEach((st, i) => {
          for (const c of st.checks) {
            const d = Math.abs(f.height(i, c.t) - c.h);
            if (!(d <= worst)) { worst = d; where = `${st.id} ${st.name}`; }
          }
        });
      }
      return { ok: worst <= 0.002, worst, where };
    }
  }

  root.DiveTides = { TideModel };
})(typeof window !== 'undefined' ? window : globalThis);

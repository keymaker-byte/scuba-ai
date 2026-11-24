// Tidal current overlay for map.html: the current tool's seafloor current, computed in the
// browser exactly as `tools/current.py` computes it. `map_export.py currents` writes
// map/currents/<name>.js with the tool's inputs: the ADCIRC database's constants at every mesh
// node, the stations' corrections, the regional vertical profile, each node's distances through
// the water to the stations, and the astronomy prepared for each year the map may show. The code
// below is a line-for-line port of the tool's blend_at, at_frac, vprof and its prediction, and of
// `extract`'s placing of a point in the mesh, so the current read at a point and a seabed depth is
// the current `extract` and `at` give there. Each overlay file carries values the tool computed at
// sample nodes and at sample points it picked in the overlay, which `selfCheck` reproduces before
// the overlay is allowed to draw.
//
// Particles drift along the flow, each trail coloured by its speed, over whatever lies beneath
// (the depth layer among it). The trails run along each mesh node's own blended axis, the flood
// and ebb axis the tool predicts on, with the node's seabed, and are interpolated between nodes;
// they draw fainter where no station lies within the tool's reach and the field is the database's
// own. Each overlay also carries the coastline, and no trail starts or runs over land. They read a
// regular grid laid over the mesh, evenly spaced in Web Mercator so that it maps onto the screen
// with a plain scale and offset at every zoom.
(function (root) {
  'use strict';

  const DEG = Math.PI / 180;
  const TAU = 2 * Math.PI;
  const mod = (a, n) => ((a % n) + n) % n;  // Python's %, never negative
  const wrap90 = x => mod(x + 90, 180) - 90;

  // ---- complex numbers, as [re, im] ----------------------------------------------------------

  const cadd = (a, b) => [a[0] + b[0], a[1] + b[1]];
  const cmul = (a, b) => [a[0] * b[0] - a[1] * b[1], a[0] * b[1] + a[1] * b[0]];
  const cdiv = (a, b) => {
    const d = b[0] * b[0] + b[1] * b[1];
    return [(a[0] * b[0] + a[1] * b[1]) / d, (a[1] * b[0] - a[0] * b[1]) / d];
  };
  const cscale = (a, k) => [a[0] * k, a[1] * k];
  const cabs = a => Math.hypot(a[0], a[1]);
  const clog = a => [Math.log(cabs(a)), Math.atan2(a[1], a[0])];
  const cexp = a => { const m = Math.exp(a[0]); return [m * Math.cos(a[1]), m * Math.sin(a[1])]; };
  // a complex log with its phase unwrapped to within half a turn of ref's
  const wrapc = (z, ref) => [z[0], ref[1] + mod(z[1] - ref[1] + Math.PI, TAU) - Math.PI];

  function decode(b64, Type) {
    const bin = atob(b64);
    const bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    return new Type(bytes.buffer);
  }

  const mercY = lat => Math.log(Math.tan(Math.PI / 4 + lat * DEG / 2));
  const invMercY = y => (2 * Math.atan(Math.exp(y)) - Math.PI / 2) / DEG;

  // ---- astronomy (port of tools/lib/tidal_astronomy.py and current_harmonics.speed) ---------

  // Each constituent's argument coefficients, and per UTC year its node factor and its constant
  // with the node phase, held for the year as NOAA holds them.
  class Astronomy {
    constructor(a) {
      this.epoch = Date.parse(a.epoch);
      this.names = a.names;
      this.species = a.species;
      this.coef = a.coef;
      this.years = a.years;
      this.first = Math.min(...Object.keys(a.years).map(Number));
      this.last = Math.max(...Object.keys(a.years).map(Number));
    }

    // f cos(arg) and f sin(arg) of every constituent at a UTC instant in ms: a constituent's
    // speed there is Re(Z (fc + i fs)), with Z = A e^(-ig) in cm/s
    factors(ms) {
      const d = new Date(ms);
      const y = this.years[d.getUTCFullYear()];
      if (!y) {
        throw new Error(`the current overlay covers ${this.first} to ${this.last}; ` +
          'regenerate it with map_export.py currents');
      }
      const T0 = (ms - this.epoch) / 86400000 / 36525;
      const s = 270.434164 + 481267.8831417 * T0 - 0.0011333 * T0 * T0;
      const h = 279.696678 + 36000.768925 * T0 + 0.0003025 * T0 * T0;
      const p = 334.329556 + 4069.0340333 * T0 - 0.010325 * T0 * T0;
      const p1 = 281.220833 + 1.719175 * T0 + 0.0004528 * T0 * T0;
      const T = 15 * (d.getUTCHours() + d.getUTCMinutes() / 60 + d.getUTCSeconds() / 3600
        + d.getUTCMilliseconds() / 3.6e6) + 180;
      const n = this.names.length, fc = new Float64Array(n), fs = new Float64Array(n);
      for (let k = 0; k < n; k++) {
        const c = this.coef[k];
        const arg = (c[0] * T + c[1] * s + c[2] * h + c[3] * p + c[4] * p1 + y.arg[k]) * DEG;
        fc[k] = y.f[k] * Math.cos(arg);
        fs[k] = y.f[k] * Math.sin(arg);
      }
      return { fc, fs };
    }
  }

  // ---- the blend (port of tools/current.py) -----------------------------------------------

  // Constituents are held by their index in the astronomy's list, each as a complex pair in a
  // Float64Array; a constituent a station or a bin does not carry holds NaN.
  const has = (a, i) => a[2 * i] === a[2 * i];  // not NaN
  const BANDS_OF = [1, 2, 3];
  const MAX_SPECIES = 8;

  class Blend {
    constructor(data) {
      const st = data.settings;
      this.prior = st.prior;
      this.soft2 = st.softenKm * st.softenKm;
      this.exact2 = st.exactKm * st.exactKm;
      this.neighbours = st.neighbours;
      this.reach = st.reachKm;
      const names = data.astronomy.names;
      this.na = names.length;
      this.idx = new Map(names.map((c, i) => [c, i]));
      this.sp = Int8Array.from(data.astronomy.species);
      this.band = Int8Array.from(this.sp, sp => (sp === 0 ? 0 : sp === 1 ? 1 : sp === 2 ? 2 : 3));
      // each band's key constituent (BAND_KEY), by its species
      this.bandSp = { 1: this.sp[this.idx.get('K1')], 2: this.sp[this.idx.get('M2')], 3: this.sp[this.idx.get('M4')] };
      this.dbIdx = Int16Array.from(data.database.names, c => this.idx.get(c));
      const tab = rows => rows.map(([f, re, im]) => [f, [re, im]]);
      this.prof = { 1: tab(data.profile[1] || []), 2: tab(data.profile[2] || []) };
      this.speciesHere = [...new Set(this.sp)];
      const pack = o => {
        const a = new Float64Array(2 * this.na).fill(NaN);
        for (const [c, z] of Object.entries(o)) { const i = this.idx.get(c); a[2 * i] = z[0]; a[2 * i + 1] = z[1]; }
        return a;
      };
      this.stations = data.stations.map(s => ({
        id: s.id, lat: s.lat, lon: s.lon,
        bins: s.bins.map(([frac, Lc, Lb, mean, turn, Z, az]) => {
          const lb = new Float64Array(8).fill(NaN);
          for (const [k, z] of Object.entries(Lb)) { lb[2 * k] = z[0]; lb[2 * k + 1] = z[1]; }
          return { frac, Lc: pack(Lc), Lb: lb, mean, turn, Z: pack(Z), az, v: this.table(frac) };
        }),
      }));
    }

    // the profile's complex ratio at a fraction of the depth above the seabed (vfac)
    vfac(tab, frac) {
      if (!tab.length) return [(8 / 7) * Math.max(frac, 0.01) ** (1 / 7), 0];
      if (frac <= tab[0][0]) return cscale(tab[0][1], (Math.max(frac, 0.01) / tab[0][0]) ** (1 / 7));
      for (let i = 0; i + 1 < tab.length; i++) {
        const [f0, z0] = tab[i], [f1, z1] = tab[i + 1];
        if (frac <= f1) {
          const w = (frac - f0) / (f1 - f0);
          return cadd(cscale(z0, 1 - w), cscale(z1, w));
        }
      }
      return tab[tab.length - 1][1];
    }

    // The ratio to the column mean at a fraction of the depth for every species (vprof): the
    // diurnal table for the diurnals and the semidiurnal one for the rest, its phase scaled by
    // the species; amplitude alone for the long period ones. [re, im] per species.
    table(f) {
      const t = new Float64Array(2 * (MAX_SPECIES + 1));
      const y = this.vfac(this.prof[2], f), m = cabs(y), ph = Math.atan2(y[1], y[0]);
      for (const sp of this.speciesHere) {
        const z = sp === 1 ? this.vfac(this.prof[1], f) : sp === 0 ? [m, 0] : [m * Math.cos(ph * sp / 2), m * Math.sin(ph * sp / 2)];
        t[2 * sp] = z[0];
        t[2 * sp + 1] = z[1];
      }
      return t;
    }

    // a station at a fraction of the depth, vq the table there (at_frac)
    atFrac(st, f, vq) {
      const bins = st.bins, last = bins[bins.length - 1], n2 = 2 * this.na;
      if (bins.length === 1 || f <= bins[0].frac || f >= last.frac) {
        const b = bins.length === 1 || f <= bins[0].frac ? bins[0] : last;
        // per species, the profile's ratio from the bin's height to f, and its log
        const adj = new Float64Array(2 * (MAX_SPECIES + 1)), la = new Float64Array(adj.length);
        for (const sp of this.speciesHere) {
          const [ar, ai] = cdiv([vq[2 * sp], vq[2 * sp + 1]], [b.v[2 * sp], b.v[2 * sp + 1]]);
          adj[2 * sp] = ar; adj[2 * sp + 1] = ai;
          la[2 * sp] = Math.log(Math.hypot(ar, ai)); la[2 * sp + 1] = Math.atan2(ai, ar);
        }
        const Lc = new Float64Array(n2), Z = new Float64Array(n2), Lb = new Float64Array(8).fill(NaN);
        for (let i = 0; i < this.na; i++) {
          const s2 = 2 * this.sp[i];
          Lc[2 * i] = b.Lc[2 * i] + la[s2]; Lc[2 * i + 1] = b.Lc[2 * i + 1] + la[s2 + 1];
          const zr = b.Z[2 * i], zi = b.Z[2 * i + 1];
          Z[2 * i] = zr * adj[s2] - zi * adj[s2 + 1]; Z[2 * i + 1] = zr * adj[s2 + 1] + zi * adj[s2];
        }
        for (const k of BANDS_OF) {
          const s2 = 2 * this.bandSp[k];
          Lb[2 * k] = b.Lb[2 * k] + la[s2]; Lb[2 * k + 1] = b.Lb[2 * k + 1] + la[s2 + 1];
        }
        return { Lc, Lb, mean: b.mean, turn: b.turn, Z, az: b.az };
      }
      for (let i = 0; i + 1 < bins.length; i++) {
        const lo = bins[i], hi = bins[i + 1];
        if (lo.frac <= f && f <= hi.frac) {
          const w = hi.frac > lo.frac ? (f - lo.frac) / (hi.frac - lo.frac) : 0;
          const mix = (a, b, wrap) => {
            const out = new Float64Array(a.length).fill(NaN);
            for (let j = 0; j < a.length; j += 2) {
              if (a[j] !== a[j] || b[j] !== b[j]) continue;
              const bi = wrap ? a[j + 1] + mod(b[j + 1] - a[j + 1] + Math.PI, TAU) - Math.PI : b[j + 1];
              out[j] = a[j] * (1 - w) + b[j] * w;
              out[j + 1] = a[j + 1] * (1 - w) + bi * w;
            }
            return out;
          };
          return {
            Lc: mix(lo.Lc, hi.Lc, true), Lb: mix(lo.Lb, hi.Lb, true),
            mean: lo.mean * (1 - w) + hi.mean * w, turn: lo.turn + wrap90(hi.turn - lo.turn) * w,
            Z: mix(lo.Z, hi.Z, false),
            az: mod(lo.az + (mod(hi.az - lo.az + 180, 360) - 180) * w, 360),
          };
        }
      }
      throw new Error(`station ${st.id} has no bin around ${f}`);
    }

    // the database's main axis at a point, from its tidal ellipses (principal_axis); uv holds
    // (Zu re, im, Zv re, im) per constituent
    principalAxis(uv) {
      let sxx = 0, syy = 0, sxy = 0;
      for (const i of this.dbIdx) {
        const k = 4 * i;
        sxx += uv[k] * uv[k] + uv[k + 1] * uv[k + 1];
        syy += uv[k + 2] * uv[k + 2] + uv[k + 3] * uv[k + 3];
        sxy += uv[k] * uv[k + 2] + uv[k + 1] * uv[k + 3];
      }
      const th = 0.5 * Math.atan2(2 * sxy, sxx - syy);
      return mod(Math.atan2(Math.cos(th), Math.sin(th)) / DEG, 360);
    }

    // The current at a point, from the database's constants there, its stations within reach
    // nearest first ([{d, st}]) and a fraction of the depth above the seabed: { Z, mean, az },
    // Z the complex constants along az in cm/s per constituent, zero where none (blend_at).
    // The tool then points the axis at the nearest station's flood, turning Z and mean with
    // it; the current itself, az with the signed speed along it, is the same either way.
    blendAt(uv, cand, frac) {
      const na = this.na, vq = this.table(frac);
      const az0 = this.principalAxis(uv);
      const Z = new Float64Array(2 * na);
      const along = (az, i) => {
        const sa = Math.sin(az * DEG), ca = Math.cos(az * DEG), k = 4 * i;
        return [uv[k] * sa + uv[k + 2] * ca, uv[k + 1] * sa + uv[k + 3] * ca];
      };
      if (!cand.length) {
        for (const i of this.dbIdx) {
          const z = cmul(along(az0, i), [vq[2 * this.sp[i]], vq[2 * this.sp[i] + 1]]);
          Z[2 * i] = z[0]; Z[2 * i + 1] = z[1];
        }
        return { Z, mean: 0, az: az0 };
      }
      const ws = cand.map(c => 1 / (c.d * c.d + this.soft2));
      const tot = this.prior + ws.reduce((a, b) => a + b, 0);
      const per = cand.map(c => this.atFrac(c.st, frac, vq));
      const lam = this.exact2 / (this.exact2 + cand[0].d * cand[0].d);
      let e = 0, n = this.prior;
      per.forEach((p, i) => { e += ws[i] * Math.sin(2 * p.turn * DEG); n += ws[i] * Math.cos(2 * p.turn * DEG); });
      let turn = Math.atan2(e, n) / DEG / 2;
      turn += lam * wrap90(per[0].turn - turn);
      const az = mod(az0 + turn, 360);
      const axis = Math.cos((az - az0) * DEG) < 0 ? mod(az0 + 180, 360) : az0;
      const lq = s => clog([vq[2 * s], vq[2 * s + 1]]);
      // each band's ratio, drawn toward the regional profile alone
      const Lband = {};
      for (const b of BANDS_OF) {
        const k = { 1: this.idx.get('K1'), 2: this.idx.get('M2'), 3: this.idx.get('M4') }[b];
        const base = lq(this.bandSp[b]);
        let ar = this.prior * base[0], ai = this.prior * base[1];
        per.forEach((p, j) => {
          const L = has(p.Lc, k) ? [p.Lc[2 * k], p.Lc[2 * k + 1]] : has(p.Lb, b) ? [p.Lb[2 * b], p.Lb[2 * b + 1]] : base;
          const wc = wrapc(L, base);
          ar += ws[j] * wc[0]; ai += ws[j] * wc[1];
        });
        Lband[b] = [ar / tot, ai / tot];
      }
      // each constituent's, drawn toward its band's
      for (const i of this.dbIdx) {
        const b = this.band[i], sp = this.sp[i];
        const lb = b ? Lband[b] : lq(sp);
        let ar = this.prior * lb[0], ai = this.prior * lb[1];
        per.forEach((p, j) => {
          let L;
          if (has(p.Lc, i)) L = [p.Lc[2 * i], p.Lc[2 * i + 1]];
          else if (b && has(p.Lb, b)) {
            const r = clog(cdiv([vq[2 * sp], vq[2 * sp + 1]], [vq[2 * this.bandSp[b]], vq[2 * this.bandSp[b] + 1]]));
            L = [p.Lb[2 * b] + r[0], p.Lb[2 * b + 1] + r[1]];
          } else L = lb;
          const wc = wrapc(L, lb);
          ar += ws[j] * wc[0]; ai += ws[j] * wc[1];
        });
        const z = cmul(along(axis, i), cexp([ar / tot, ai / tot]));
        Z[2 * i] = z[0]; Z[2 * i + 1] = z[1];
      }
      let mean = 0;
      per.forEach((p, j) => { mean += ws[j] * p.mean * Math.cos((p.az - az) * DEG); });
      mean /= tot;
      // near a station, its own current
      const sign = Math.cos((per[0].az - az) * DEG) >= 0 ? 1 : -1;
      const own = per[0].Z, a = lam * sign, c = 1 - lam;
      for (let i = 0; i < na; i++) {
        const or = has(own, i) ? own[2 * i] : 0, oi = has(own, i) ? own[2 * i + 1] : 0;
        Z[2 * i] = a * or + c * Z[2 * i];
        Z[2 * i + 1] = a * oi + c * Z[2 * i + 1];
      }
      return { Z, mean: lam * sign * per[0].mean + (1 - lam) * mean, az };
    }
  }

  // ---- the field ----------------------------------------------------------------------------

  class CurrentField {
    constructor(data) {
      this.data = data;
      this.nodeCount = data.nodeCount;
      const n = this.nodeCount;
      this.xy = decode(data.nodes, Float32Array);         // lon, lat per node
      this.tri = decode(data.triangles, Uint16Array);     // three node indices per element
      this.depth = decode(data.depth, Float32Array);      // the trails' seabed per node, m
      const db = data.database;
      this.dbNames = db.names;
      const q = decode(db.uv, Int16Array);                // node, constituent, (Zu re, im, Zv re, im)
      const scale = decode(db.scale, Float32Array);       // per node, cm/s a step
      const nk = db.names.length;
      if (this.xy.length !== 2 * n || this.tri.length !== 3 * data.triangleCount ||
          this.depth.length !== n || scale.length !== n || q.length !== 4 * n * nk) {
        throw new Error('overlay arrays do not match their stated sizes');
      }
      this.uv = new Float64Array(q.length);
      for (let j = 0, k = 0; j < n; j++) {
        for (let i = 0; i < 4 * nk; i++, k++) this.uv[k] = q[k] * scale[j];
      }
      // each node's stations within reach through the water
      const cnt = decode(data.near.count, Uint8Array);
      this.nearSt = decode(data.near.station, Uint16Array);
      this.nearKmPath = decode(data.near.km, Float32Array);
      if (cnt.length !== n || this.nearSt.length !== this.nearKmPath.length) {
        throw new Error('overlay station distances do not match its node count');
      }
      this.nearAt = new Uint32Array(n + 1);
      for (let j = 0; j < n; j++) this.nearAt[j + 1] = this.nearAt[j] + cnt[j];
      this.blend = new Blend(data);
      this.astro = new Astronomy(data.astronomy);
      this.settings = data.settings;
      this.ab = data.settings.aboveBottomM;
      // the coastline, as each mask row's crossings: land where an odd number lie west of a point
      const m = data.landMask;
      this.mask = m ? { ...m, dY: m.dLon * DEG, off: decode(m.offsets, Uint32Array), cr: decode(m.crossings, Uint16Array) } : null;
      this._shoreEdges(data);
      // the trails: every node blended once, at its own seabed
      const na = this.astro.names.length;
      this.nodeZ = new Float64Array(n * na * 2);
      this.nodeMean = new Float64Array(n);
      this.nodeSin = new Float64Array(n);
      this.nodeCos = new Float64Array(n);
      this.nearest = new Float32Array(n);
      for (let j = 0; j < n; j++) {
        const lat = this.xy[2 * j + 1], lon = this.xy[2 * j];
        const cand = this.candidates(j, lat, lon);
        this.nearest[j] = cand.length ? cand[0].d : NaN;
        const r = this.blend.blendAt(this.nodeUV([j], [1]), cand, this.frac(this.depth[j]));
        this.nodeZ.set(r.Z, j * na * 2);
        this.nodeMean[j] = r.mean;
        this.nodeSin[j] = Math.sin(r.az * DEG);
        this.nodeCos[j] = Math.cos(r.az * DEG);
      }
      this.u = new Float32Array(n);
      this.v = new Float32Array(n);
      this.time = null;
    }

    // the fraction of the depth the height above the seabed sits at, as `extract` takes it
    frac(H) {
      return H > 0 ? Math.max(Math.min(this.ab, H) / H, 0.01) : 1;
    }

    // the database's constants across an element, (Zu re, im, Zv re, im) per constituent
    nodeUV(nodes, w) {
      const nk = this.dbNames.length, out = new Float64Array(4 * this.blend.na), di = this.blend.dbIdx;
      for (let i = 0; i < nk; i++) {
        let a = 0, b = 0, c = 0, d = 0;
        for (let m = 0; m < nodes.length; m++) {
          const k = (nodes[m] * nk + i) * 4, x = w[m];
          a += x * this.uv[k]; b += x * this.uv[k + 1]; c += x * this.uv[k + 2]; d += x * this.uv[k + 3];
        }
        const o = 4 * di[i];
        out[o] = a; out[o + 1] = b; out[o + 2] = c; out[o + 3] = d;
      }
      return out;
    }

    // The stations within reach of a point, nearest first, as the tool picks them: the paths
    // through the water from the mesh node nearest the point, each at least the straight line
    // from the point itself (floor_km, neighbours).
    candidates(start, lat, lon) {
      const out = [];
      const sc = Math.cos(lat * DEG);
      for (let k = this.nearAt[start]; k < this.nearAt[start + 1]; k++) {
        const i = this.nearSt[k], st = this.blend.stations[i];
        const d = Math.max(this.nearKmPath[k], Math.hypot((st.lon - lon) * sc, st.lat - lat) * 111.2);
        if (d < this.blend.reach) out.push({ d, i, st });
      }
      out.sort((a, b) => a.d - b.d || a.i - b.i);
      return out.slice(0, this.blend.neighbours);
    }

    // The mesh's own shoreline, its edges bucketed by 0.02°, for water the mesh does not reach.
    _shoreEdges(data) {
      this.extendKm = this.settings.extendKm || 0;
      this.buckets = new Map();
      if (!data.shoreNodes || !this.extendKm) return;
      const sh = decode(data.shoreNodes, Uint8Array);
      if (sh.length !== this.nodeCount) throw new Error('overlay shoreline nodes do not match its node count');
      const { xy, tri } = this;
      const seen = new Map();
      for (let e = 0; e < tri.length; e += 3) {
        for (let k = 0; k < 3; k++) {
          const a = tri[e + k], b = tri[e + (k + 1) % 3];
          const key = a < b ? a * 1e6 + b : b * 1e6 + a;
          seen.set(key, seen.has(key) ? -1 : e * 3 + k);
        }
      }
      for (const [, v] of seen) {
        if (v < 0) continue;
        const e = Math.floor(v / 3), k = v % 3;
        const a = tri[e + k], b = tri[e + (k + 1) % 3];
        if (!sh[a] || !sh[b]) continue;
        const r0 = Math.floor(Math.min(xy[2 * a + 1], xy[2 * b + 1]) / 0.02), r1 = Math.floor(Math.max(xy[2 * a + 1], xy[2 * b + 1]) / 0.02);
        const c0 = Math.floor(Math.min(xy[2 * a], xy[2 * b]) / 0.02), c1 = Math.floor(Math.max(xy[2 * a], xy[2 * b]) / 0.02);
        for (let r = r0; r <= r1; r++) {
          for (let c = c0; c <= c1; c++) {
            const id = r * 100000 + c;
            if (!this.buckets.has(id)) this.buckets.set(id, []);
            this.buckets.get(id).push(e, k);
          }
        }
      }
    }

    // For water outside the mesh, the drawing grid's shortcut: the element and weights at the
    // nearest point of the mesh's shoreline, when it lies within extendKm and the straight line
    // to it crosses no land; null otherwise, and null on land.
    edgePoint(lat, lon) {
      if (!this.buckets.size || this.onLand(lon, mercY(lat))) return null;
      const { xy, tri } = this;
      const sc = Math.cos(lat * DEG), kmDeg = 111.2;
      const R = Math.floor(lat / 0.02), C = Math.floor(lon / 0.02);
      let best = null;
      for (let r = R - 1; r <= R + 1; r++) {
        for (let c = C - 1; c <= C + 1; c++) {
          const list = this.buckets.get(r * 100000 + c);
          if (!list) continue;
          for (let i = 0; i < list.length; i += 2) {
            const e = list[i], k = list[i + 1];
            const a = tri[e + k], b = tri[e + (k + 1) % 3];
            const ax = xy[2 * a] * sc, ay = xy[2 * a + 1], bx = xy[2 * b] * sc, by = xy[2 * b + 1];
            const dx = bx - ax, dy = by - ay, L2 = dx * dx + dy * dy;
            const t = L2 ? Math.max(0, Math.min(1, ((lon * sc - ax) * dx + (lat - ay) * dy) / L2)) : 0;
            const d = Math.hypot(ax + t * dx - lon * sc, ay + t * dy - lat) * kmDeg;
            if (!best || d < best.d) best = { d, e, k, t, lat: ay + t * dy, lon: (ax + t * dx) / sc };
          }
        }
      }
      if (!best || best.d > this.extendKm) return null;
      const n = Math.max(1, Math.ceil(best.d * 100));
      for (let i = 1; i < n; i++) {
        const f = i / n;
        if (this.onLand(lon + (best.lon - lon) * f, mercY(lat + (best.lat - lat) * f))) return null;
      }
      const w = [0, 0, 0];
      w[best.k] = 1 - best.t;
      w[(best.k + 1) % 3] = best.t;
      return { e: best.e, w1: w[0], w2: w[1], w3: w[2] };
    }

    // whether a point, as its longitude and Web Mercator y, lies on land; false with no mask
    onLand(lon, my) {
      const m = this.mask;
      if (!m) return false;
      const r = Math.floor((m.yN - my) / m.dY);
      if (r < 0 || r >= m.rows) return false;
      const c = (lon - m.W) / m.dLon;
      const a = m.off[r];
      let lo = a, hi = m.off[r + 1];
      while (lo < hi) {
        const mid = (lo + hi) >> 1;
        if (m.cr[mid] <= c) lo = mid + 1; else hi = mid;
      }
      return ((lo - a) & 1) === 1;
    }

    // the element a point falls in, first in the mesh's order: { nodes, w } or null (locate)
    _inside(lat, lon) {
      const { xy, tri } = this;
      for (let e = 0; e < tri.length; e += 3) {
        const a = tri[e], b = tri[e + 1], c = tri[e + 2];
        const x1 = xy[2 * a], y1 = xy[2 * a + 1], x2 = xy[2 * b], y2 = xy[2 * b + 1], x3 = xy[2 * c], y3 = xy[2 * c + 1];
        if (lon < Math.min(x1, x2, x3) || lon > Math.max(x1, x2, x3)) continue;
        if (lat < Math.min(y1, y2, y3) || lat > Math.max(y1, y2, y3)) continue;
        const det = (y2 - y3) * (x1 - x3) + (x3 - x2) * (y1 - y3);
        if (det === 0) continue;
        const w1 = ((y2 - y3) * (lon - x3) + (x3 - x2) * (lat - y3)) / det;
        const w2 = ((y3 - y1) * (lon - x3) + (x1 - x3) * (lat - y3)) / det;
        const w3 = 1 - w1 - w2;
        if (w1 >= -1e-9 && w2 >= -1e-9 && w3 >= -1e-9) return { nodes: [a, b, c], w: [w1, w2, w3] };
      }
      return null;
    }

    // The nearest point of the mesh, on the edge of its wet area, stepped walkStepM further in
    // toward the centroid of its element (walk_in): [lat, lon].
    _walkIn(lat, lon) {
      const { xy, tri } = this;
      const sc = Math.cos(lat * DEG), px = lon * sc, py = lat;
      let cand = [];
      for (const r of [0.05, 0.2, 1.0, 5.0]) {
        for (let e = 0; e < tri.length; e += 3) {
          for (let m = 0; m < 3; m++) {
            const i = tri[e + m];
            if (Math.abs(xy[2 * i + 1] - lat) <= r && Math.abs(xy[2 * i] - lon) <= r / sc) { cand.push(e); break; }
          }
        }
        if (cand.length) break;
      }
      let best = null;
      for (const e of cand) {
        const t3 = [0, 1, 2].map(m => [xy[2 * tri[e + m]] * sc, xy[2 * tri[e + m] + 1]]);
        for (let k = 0; k < 3; k++) {
          const [ax, ay] = t3[k], [bx, by] = t3[(k + 2) % 3];
          const dx = bx - ax, dy = by - ay, L2 = dx * dx + dy * dy;
          const t = L2 === 0 ? 0 : Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / L2));
          const cx = ax + t * dx, cy = ay + t * dy;
          const d = Math.hypot(cx - px, cy - py);
          if (best === null || d < best.d) best = { d, cx, cy, t3 };
        }
      }
      if (!best) return null;
      const gx = (best.t3[0][0] + best.t3[1][0] + best.t3[2][0]) / 3, gy = (best.t3[0][1] + best.t3[1][1] + best.t3[2][1]) / 3;
      const L = Math.hypot(gx - best.cx, gy - best.cy);
      const step = Math.min(this.settings.walkStepM / 111000, 0.5 * L);
      const wx = best.cx + (gx - best.cx) * step / L, wy = best.cy + (gy - best.cy) * step / L;
      return [Math.round(wy * 1e5) / 1e5, Math.round(wx / sc * 1e5) / 1e5];
    }

    // A point placed as `extract` places a site (place_site): the element it falls in, or, for
    // water the mesh does not reach, the element at the nearest point of the mesh's edge, when
    // that lies within extendKm and the straight line to it crosses no land. { nodes, w } or null.
    place(lat, lon) {
      if (this.onLand(lon, mercY(lat))) return null;
      const hit = this._inside(lat, lon);
      if (hit) return hit;
      if (!this.extendKm) return null;
      const walked = this._walkIn(lat, lon);
      if (!walked) return null;
      const [elat, elon] = walked;
      const km = Math.hypot((elon - lon) * Math.cos(lat * DEG), elat - lat) * 111.2;
      if (km > this.extendKm) return null;
      const n = Math.max(1, Math.floor(km * 1000 / this.settings.lineStepM));
      for (let i = 1; i <= n; i++) {
        const f = i / n;
        if (this.onLand(lon + (elon - lon) * f, mercY(lat + (elat - lat) * f))) return null;
      }
      return this._inside(elat, elon);
    }

    // The current at a point over a seabed H m deep (MLLW), as `extract` computes it there:
    // { Z, mean, az, km } with km the nearest station's distance (null beyond reach); null
    // where the tool does not reach.
    pointAt(lat, lon, H) {
      const p = this.place(lat, lon);
      if (!p) return null;
      let start = 0;
      for (let m = 1; m < 3; m++) {
        if (p.w[m] > p.w[start] || (p.w[m] === p.w[start] && p.nodes[m] > p.nodes[start])) start = m;
      }
      const cand = this.candidates(p.nodes[start], lat, lon);
      const r = this.blend.blendAt(this.nodeUV(p.nodes, p.w), cand, this.frac(H));
      r.km = cand.length ? cand[0].d : null;
      return r;
    }

    // The signed speed along the point's axis at a UTC instant, m/s (current_harmonics.speed),
    // and the current it makes: { u, v, speed, toward, km }.
    signedSpeed(r, ms) {
      const { fc, fs } = this.astro.factors(ms);
      let s = r.mean;
      for (let i = 0; i < fc.length; i++) s += r.Z[2 * i] * fc[i] - r.Z[2 * i + 1] * fs[i];
      return s / 100;
    }

    currentOf(r, ms) {
      const s = this.signedSpeed(r, ms);
      const u = s * Math.sin(r.az * DEG), v = s * Math.cos(r.az * DEG);
      return { u, v, speed: Math.abs(s), toward: mod(Math.atan2(u, v) / DEG, 360), km: r.km, field: this };
    }

    at(lat, lon, H, ms) {
      const r = this.pointAt(lat, lon, H);
      return r ? this.currentOf(r, ms) : null;
    }

    // u, v (m/s, east and north) at every node at a UTC instant in ms, for the trails
    computeNodes(ms) {
      const { fc, fs } = this.astro.factors(ms);
      const na = fc.length, Z = this.nodeZ;
      for (let j = 0, k = 0; j < this.nodeCount; j++) {
        let s = this.nodeMean[j];
        for (let i = 0; i < na; i++, k += 2) s += Z[k] * fc[i] - Z[k + 1] * fs[i];
        s /= 100;
        this.u[j] = s * this.nodeSin[j];
        this.v[j] = s * this.nodeCos[j];
      }
      this.time = ms;
    }

    // km to the nearest station at a point of an element, null where a corner has none in reach
    nearKm(a, b, c, w1, w2, w3) {
      const n = this.nearest;
      if (Number.isNaN(n[a]) || Number.isNaN(n[b]) || Number.isNaN(n[c])) return null;
      return w1 * n[a] + w2 * n[b] + w3 * n[c];
    }

    // Reproduce the values the Python tool computed when it wrote the file: the trails' current
    // at sample nodes, and at sample points over their own seabed, read as the map reads any point: the
    // signed speed `at` prints and the flood direction it prints to 0.1°. The file holds the
    // database's constants to 1 part in 32,767 of each node's largest, which in water whose
    // tidal ellipse is nearly a circle moves the axis by a few hundredths of a degree; the speed
    // holds to 1 mm/s and the axis to 0.15°, finer than the map prints either. Any wider drift
    // means the port no longer matches the tool, and the overlay must not draw.
    selfCheck(tolerance = 0.001, axisDeg = 0.15) {
      let worst = 0, where = null;
      const note = (off, what) => { if (!(off <= worst)) { worst = off; where = what; } };
      for (const c of this.data.checks.nodes) {
        this.computeNodes(c.t);
        note(Math.hypot(this.u[c.node] - c.u, this.v[c.node] - c.v), `node ${c.node}`);
      }
      for (const s of this.data.checks.points) {
        const label = `point ${s.lat}, ${s.lon}`;
        const r = this.pointAt(s.lat, s.lon, s.seabed);
        if (!r || Math.abs(wrap90(r.az - s.flood)) > axisDeg) {
          note(Infinity, label);
          continue;
        }
        const sign = Math.cos((r.az - s.flood) * DEG) >= 0 ? 1 : -1;
        for (const c of s.checks) note(Math.abs(sign * this.signedSpeed(r, c.t) - c.s), label);
      }
      this.time = null;
      const count = this.data.checks.nodes.length + this.data.checks.points.length;
      return { ok: worst <= tolerance, worst, where, count };
    }

    // The trails' own value at a point, interpolated between the nodes as they draw it.
    drawnAt(lat, lon) {
      const p = this._inside(lat, lon) || (q => q && { nodes: [this.tri[q.e], this.tri[q.e + 1], this.tri[q.e + 2]], w: [q.w1, q.w2, q.w3] })(this.edgePoint(lat, lon));
      if (!p) return null;
      let u = 0, v = 0;
      p.nodes.forEach((j, m) => { u += p.w[m] * this.u[j]; v += p.w[m] * this.v[j]; });
      return { u, v, speed: Math.hypot(u, v), toward: mod(Math.atan2(u, v) / DEG, 360),
        km: this.nearKm(...p.nodes, ...p.w), field: this };
    }
  }

  // A regular grid over the field's box, square cells of about `cellM` metres, evenly spaced in
  // Web Mercator. Each cell remembers the element its centre falls in, as its number plus one,
  // and two of its weights in 1/255ths, kept small so a box the size of the Salish Sea fits in
  // memory. A cell whose centre is outside the mesh but which still reaches into it, along the
  // mesh's edge, takes the element one of its corners falls in. A water cell beyond the mesh's
  // own shoreline, within the field's extendKm of it, takes the nearest point of that shoreline,
  // so the trails run up to the coast; every other cell holds 0 and stays blank.
  class FieldGrid {
    constructor(field, cellM = 150) {
      const [S, W, N, E] = field.data.bbox;
      const midLat = (S + N) / 2;
      this.dLon = cellM / (111320 * Math.cos(midLat * DEG));
      this.W = W;
      this.yN = mercY(N);
      this.dY = this.dLon * DEG; // same step in Mercator units as in longitude radians
      this.cols = Math.ceil((E - W) / this.dLon);
      this.rows = Math.ceil((this.yN - mercY(S)) / this.dY);
      this.north = N;
      this.south = invMercY(this.yN - this.rows * this.dY);
      this.east = W + this.cols * this.dLon;
      const size = this.cols * this.rows;
      this.elem = new (field.data.triangleCount < 65535 ? Uint16Array : Uint32Array)(size);
      this.w1 = new Uint8Array(size);
      this.w2 = new Uint8Array(size);
      this.u = new Float32Array(size);
      this.v = new Float32Array(size);
      this.field = field;

      const { xy, tri } = field;
      const gx = j => (xy[2 * j] - W) / this.dLon;
      const gy = j => (this.yN - mercY(xy[2 * j + 1])) / this.dY;
      // First every cell centre that falls in an element, then, for the cells still empty, a
      // corner (or the middle of a side) that does.
      const probes = [[[0.5, 0.5]], [[0, 0], [1, 0], [0, 1], [1, 1], [0.5, 0], [0.5, 1], [0, 0.5], [1, 0.5]]];
      for (const offsets of probes) {
        for (let e = 0; e < tri.length; e += 3) {
          const x1 = gx(tri[e]), y1 = gy(tri[e]), x2 = gx(tri[e + 1]), y2 = gy(tri[e + 1]), x3 = gx(tri[e + 2]), y3 = gy(tri[e + 2]);
          const det = (y2 - y3) * (x1 - x3) + (x3 - x2) * (y1 - y3);
          if (det === 0) continue;
          const c0 = Math.max(0, Math.floor(Math.min(x1, x2, x3) - 1));
          const c1 = Math.min(this.cols - 1, Math.ceil(Math.max(x1, x2, x3)));
          const r0 = Math.max(0, Math.floor(Math.min(y1, y2, y3) - 1));
          const r1 = Math.min(this.rows - 1, Math.ceil(Math.max(y1, y2, y3)));
          for (let r = r0; r <= r1; r++) {
            for (let c = c0; c <= c1; c++) {
              const idx = r * this.cols + c;
              if (this.elem[idx] !== 0) continue;
              for (const [ox, oy] of offsets) {
                const px = c + ox, py = r + oy;
                const a = ((y2 - y3) * (px - x3) + (x3 - x2) * (py - y3)) / det;
                const b = ((y3 - y1) * (px - x3) + (x1 - x3) * (py - y3)) / det;
                if (a < -1e-9 || b < -1e-9 || 1 - a - b < -1e-9) continue;
                this.elem[idx] = e / 3 + 1;
                this.w1[idx] = Math.round(Math.max(0, a) * 255);
                this.w2[idx] = Math.round(Math.max(0, b) * 255);
                break;
              }
            }
          }
        }
      }
      // water the mesh does not reach, within extendKm of its shoreline: the nearest edge point
      // to the cell centre; then, for a cell beside one that draws whose centre is on land, to
      // the first of a 4 x 4 set of points inside it that is water, so a cell the coastline
      // crosses still draws its water
      if (field.buckets.size) {
        const put = (idx, q) => {
          this.elem[idx] = q.e / 3 + 1;
          this.w1[idx] = Math.round(q.w1 * 255);
          this.w2[idx] = Math.round(q.w2 * 255);
        };
        for (let r = 0; r < this.rows; r++) {
          const lat = invMercY(this.yN - (r + 0.5) * this.dY);
          for (let c = 0; c < this.cols; c++) {
            const idx = r * this.cols + c;
            if (this.elem[idx] !== 0) continue;
            const q = field.edgePoint(lat, W + (c + 0.5) * this.dLon);
            if (q) put(idx, q);
          }
        }
        const drawn = this.elem.slice();
        const subs = [];
        for (const oy of [0.125, 0.375, 0.625, 0.875]) for (const ox of [0.125, 0.375, 0.625, 0.875]) subs.push([ox, oy]);
        for (let r = 0; r < this.rows; r++) {
          for (let c = 0; c < this.cols; c++) {
            const idx = r * this.cols + c;
            if (drawn[idx] !== 0) continue;
            let beside = false;
            for (let rr = Math.max(0, r - 1); rr <= Math.min(this.rows - 1, r + 1) && !beside; rr++) {
              for (let cc = Math.max(0, c - 1); cc <= Math.min(this.cols - 1, c + 1); cc++) {
                if (drawn[rr * this.cols + cc] !== 0) { beside = true; break; }
              }
            }
            if (!beside || !field.onLand(W + (c + 0.5) * this.dLon, this.yN - (r + 0.5) * this.dY)) continue;
            for (const [ox, oy] of subs) {
              const q = field.edgePoint(invMercY(this.yN - (r + oy) * this.dY), W + (c + ox) * this.dLon);
              if (q) { put(idx, q); break; }
            }
          }
        }
      }
      // how faint each cell draws: 0 where a station corrects the field, 1 where none is within
      // the tool's reach and the field is the database's own
      this.fade = null;
      if (field.near) {
        this.fade = new Uint8Array(size);
        for (let i = 0; i < size; i++) {
          if (this.elem[i] === 0) continue;
          const e = (this.elem[i] - 1) * 3;
          const x = this.w1[i] / 255, y = this.w2[i] / 255;
          const km = field.nearKm(tri[e], tri[e + 1], tri[e + 2], x, y, Math.max(0, 1 - x - y));
          this.fade[i] = km === null ? 1 : 0;
        }
      }
    }

    update() {
      const { field, elem, w1, w2 } = this;
      const tri = field.tri, nu = field.u, nv = field.v;
      for (let i = 0; i < elem.length; i++) {
        if (elem[i] === 0) continue;
        const e = (elem[i] - 1) * 3;
        const a = tri[e], b = tri[e + 1], c = tri[e + 2];
        const x = w1[i] / 255, y = w2[i] / 255, z = 1 - x - y;
        this.u[i] = x * nu[a] + y * nu[b] + z * nu[c];
        this.v[i] = x * nv[a] + y * nv[b] + z * nv[c];
      }
    }

    // u, v at a fractional grid position, and the fade, blended from the four nearest cell
    // centres that hold the mesh; null where the position's own cell is outside it
    sample(gx, gy) {
      const own = Math.floor(gy) * this.cols + Math.floor(gx);
      if (gx < 0 || gy < 0 || gx >= this.cols || gy >= this.rows || !this.elem[own]) return null;
      const x = gx - 0.5, y = gy - 0.5;
      const c = Math.floor(x), r = Math.floor(y);
      const fx = x - c, fy = y - r;
      let u = 0, v = 0, w = 0;
      for (const [dc, dr, k] of [[0, 0, (1 - fx) * (1 - fy)], [1, 0, fx * (1 - fy)], [0, 1, (1 - fx) * fy], [1, 1, fx * fy]]) {
        const cc = c + dc, rr = r + dr;
        if (cc < 0 || rr < 0 || cc >= this.cols || rr >= this.rows) continue;
        const i = rr * this.cols + cc;
        if (!this.elem[i] || k === 0) continue;
        u += this.u[i] * k; v += this.v[i] * k; w += k;
      }
      if (w === 0) return [this.u[own], this.v[own], this.fade ? this.fade[own] : 0];
      return [u / w, v / w, this.fade ? this.fade[own] : 0];
    }
  }

  // ---- colour ---------------------------------------------------------------------------------

  // Speed in m/s to a trail colour, in hues the depth layer's blues leave free: white at still
  // water and deepening greens through the slow water, a jump to a light lime at SLOW, the window
  // threshold, then lime into yellow and on through orange to dark red in the fastest passes. The anchors below
  // set the colours; between each two a band halfway in speed takes the colour halfway between
  // them, so the colour moves in small steps, except across SLOW, which stays a clean jump. Each
  // band runs from its own speed up to the next band's; the legend shows the same bands.
  const SLOW = 0.25;
  const ANCHORS = [
    [0.00, [255, 255, 255]],
    [0.05, [187, 247, 208]],
    [0.10, [134, 239, 172]],
    [0.15, [74, 222, 128]],
    [0.20, [22, 163, 74]],
    [0.25, [163, 230, 53]],
    [0.35, [210, 226, 40]],
    [0.50, [250, 204, 21]],
    [0.70, [245, 158, 11]],
    [0.90, [251, 146, 60]],
    [1.10, [249, 115, 22]],
    [1.40, [234, 88, 12]],
    [1.80, [220, 38, 38]],
    [2.20, [185, 28, 28]],
    [2.75, [127, 29, 29]],
  ];
  const BANDS = ANCHORS.flatMap(([from, rgb], i) => {
    const next = ANCHORS[i + 1];
    if (!next || next[0] === SLOW) return [[from, rgb]];
    const mid = Math.round((from + next[0]) / 2 * 1000) / 1000;
    return [[from, rgb], [mid, rgb.map((c, k) => Math.round((c + next[1][k]) / 2))]];
  });
  const STROKES = BANDS.map(([, rgb]) => `rgb(${rgb.join(',')})`);
  // trail opacity: where stations correct the field, and where none is within reach
  const FADES = [1, 0.35];
  const bandOf = sp => {
    let k = 0;
    while (k < BANDS.length - 1 && sp >= BANDS[k + 1][0]) k++;
    return k;
  };

  // ---- the Leaflet layer ----------------------------------------------------------------------

  function makeLayer(L) {
    return L.Layer.extend({
      options: { pane: 'overlayPane', particleSpeed: 0.45, particleDensity: 1 / 220, maxParticles: 6000 },

      initialize(fields, options) {
        L.setOptions(this, options);
        this._grids = fields.map(f => new FieldGrid(f));
        this._time = Date.now();
        this._particles = [];
      },

      // The current at a coordinate over a seabed H m deep (below MLLW) at the layer's moment,
      // exactly as `current.py extract` and `at` give it there: { u, v, speed, toward, km }
      // in m/s, degrees true and km to the nearest station, null where no overlay reaches.
      readAt(lat, lon, H) {
        for (const g of this._grids) {
          const r = g.field.at(lat, lon, H, this._time);
          if (r) return r;
        }
        return null;
      },

      // The trails' own value at a coordinate, interpolated between mesh nodes, for when no
      // seabed depth is at hand.
      drawnAt(lat, lon) {
        for (const g of this._grids) {
          if (g.field.time !== this._time) {
            g.field.computeNodes(this._time);
            g.update();
          }
          const r = g.field.drawnAt(lat, lon);
          if (r) return r;
        }
        return null;
      },

      setTime(ms) {
        this._time = ms;
        if (!this._map) return;
        if (this._pendingTime) return;
        this._pendingTime = requestAnimationFrame(() => {
          this._pendingTime = null;
          this._computeField();
        });
      },

      onAdd(map) {
        const pane = map.getPane(this.options.pane);
        this._particleCanvas = L.DomUtil.create('canvas', 'leaflet-zoom-hide current-particles', pane);
        this._particleCanvas.style.position = 'absolute';
        this._particleCanvas.style.pointerEvents = 'none';
        map.on('moveend zoomend resize viewreset', this._reset, this);
        map.on('zoomstart movestart', this._pause, this);
        this._computeField();
        this._reset();
      },

      onRemove(map) {
        map.off('moveend zoomend resize viewreset', this._reset, this);
        map.off('zoomstart movestart', this._pause, this);
        cancelAnimationFrame(this._frame);
        cancelAnimationFrame(this._pendingTime);
        this._pendingTime = null;
        this._particleCanvas.remove();
      },

      _computeField() {
        for (const g of this._grids) {
          g.field.computeNodes(this._time);
          g.update();
        }
      },

      _pause() {
        cancelAnimationFrame(this._frame);
        this._frame = null;
      },

      _reset() {
        const map = this._map;
        if (!map) return;
        const size = map.getSize();
        const ratio = window.devicePixelRatio || 1;
        const topLeft = map.containerPointToLayerPoint([0, 0]);
        for (const c of [this._particleCanvas]) {
          c.width = size.x * ratio;
          c.height = size.y * ratio;
          c.style.width = `${size.x}px`;
          c.style.height = `${size.y}px`;
          L.DomUtil.setPosition(c, topLeft);
          c.getContext('2d').setTransform(ratio, 0, 0, ratio, 0, 0);
        }
        this._size = size;
        // grid -> screen: the grid is even in Mercator, so its corners fix a scale and offset
        this._views = this._grids.map(g => {
          const nw = map.latLngToContainerPoint([g.north, g.W]);
          const se = map.latLngToContainerPoint([g.south, g.east]);
          const sx = (se.x - nw.x) / g.cols, sy = (se.y - nw.y) / g.rows;
          const c0 = Math.max(0, Math.floor(-nw.x / sx)), c1 = Math.min(g.cols, Math.ceil((size.x - nw.x) / sx));
          const r0 = Math.max(0, Math.floor(-nw.y / sy)), r1 = Math.min(g.rows, Math.ceil((size.y - nw.y) / sy));
          return { g, nw, sx, sy, visible: c1 > c0 && r1 > r0 };
        });
        this._seedParticles();
        this._pause();
        this._animate();
      },

      // whether a screen point lies on land, by its field's coastline
      _onLand(view, x, y) {
        const g = view.g;
        return g.field.onLand(g.W + ((x - view.nw.x) / view.sx) * g.dLon, g.yN - ((y - view.nw.y) / view.sy) * g.dY);
      },

      // a random point on screen that sits inside a field's mesh and off land, or null after a few tries
      _spawn(p) {
        const views = this._views.filter(v => v.visible);
        if (!views.length) return false;
        for (let tries = 0; tries < 20; tries++) {
          const x = Math.random() * this._size.x, y = Math.random() * this._size.y;
          for (const view of views) {
            const gx = (x - view.nw.x) / view.sx, gy = (y - view.nw.y) / view.sy;
            if (view.g.sample(gx, gy) && !this._onLand(view, x, y)) {
              p.x = x; p.y = y; p.view = view; p.age = Math.floor(Math.random() * 90); p.live = true;
              return true;
            }
          }
        }
        p.live = false;
        p.age = Math.floor(Math.random() * 90);
        return false;
      },

      _seedParticles() {
        const n = Math.min(this.options.maxParticles,
          Math.round(this._size.x * this._size.y * this.options.particleDensity));
        this._particles = Array.from({ length: n }, () => {
          const p = {};
          this._spawn(p);
          return p;
        });
        this._particleCanvas.getContext('2d').clearRect(0, 0, this._size.x, this._size.y);
      },

      _animate() {
        const ctx = this._particleCanvas.getContext('2d');
        ctx.lineCap = 'round';
        const step = () => {
          if (!this._map) return;
          const { x: w, y: h } = this._size;
          ctx.globalCompositeOperation = 'destination-in';
          ctx.fillStyle = 'rgba(0,0,0,0.95)';
          ctx.fillRect(0, 0, w, h);
          ctx.globalCompositeOperation = 'source-over';
          // This frame's segments by speed band, wider in faster water, and by fade.
          const segs = Array.from({ length: BANDS.length * FADES.length }, () => []);
          const k = this.options.particleSpeed;
          for (const p of this._particles) {
            if (--p.age < 0 || !p.live) {
              if (p.age < 0) this._spawn(p);
              continue;
            }
            const view = p.view;
            const uv = view.g.sample((p.x - view.nw.x) / view.sx, (p.y - view.nw.y) / view.sy);
            if (!uv) { p.age = -1; continue; }
            // On screen a trail moves with the square root of the speed, so slow water still
            // visibly drifts while the fastest passes stay readable; 1 m/s is unchanged.
            const sp = Math.hypot(uv[0], uv[1]);
            const m = sp > 0 ? k / Math.sqrt(sp) : 0;
            const nx = p.x + uv[0] * m, ny = p.y - uv[1] * m;
            if (this._onLand(view, nx, ny)) { p.age = -1; continue; }
            segs[bandOf(sp) * FADES.length + uv[2]].push(p.x, p.y, nx, ny);
            p.x = nx; p.y = ny;
            if (nx < 0 || ny < 0 || nx > w || ny > h) p.age = -1;
          }
          // Each band's trails as one path, in its own colour; slow water draws thin and white.
          const path = xy => {
            ctx.beginPath();
            for (let i = 0; i < xy.length; i += 4) {
              ctx.moveTo(xy[i], xy[i + 1]);
              ctx.lineTo(xy[i + 2], xy[i + 3]);
            }
          };
          const width = b => (b === 0 ? 1 : 1.3 + Math.min(BANDS[b][0], 2) * 0.6);
          segs.forEach((xy, k) => {
            if (!xy.length) return;
            const b = Math.floor(k / FADES.length);
            path(xy);
            ctx.globalAlpha = FADES[k % FADES.length];
            ctx.strokeStyle = b === 0 ? 'rgba(255,255,255,0.8)' : STROKES[b];
            ctx.lineWidth = width(b);
            ctx.stroke();
          });
          ctx.globalAlpha = 1;
          this._frame = requestAnimationFrame(step);
        };
        this._frame = requestAnimationFrame(step);
      },
    });
  }

  const api = { Astronomy, Blend, CurrentField, FieldGrid, BANDS, SLOW };
  if (typeof module === 'object' && module.exports) {
    module.exports = api;
  } else {
    root.DiveCurrents = api;
    if (root.L) api.CurrentLayer = makeLayer(root.L);
  }
})(typeof window !== 'undefined' ? window : this);

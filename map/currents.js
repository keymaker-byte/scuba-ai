// Tidal current overlay for map.html: the Blend Model's seafloor field, reconstructed in the
// browser for any moment from the harmonic constants that `tools/blend_model.py export-map`
// writes to map/currents/<name>.js. The astronomy below is a line-for-line port of
// tools/lib/adcirc.py's mean_longitudes, _base_nodal, nodal and reconstruct, and each overlay
// file carries values the tool computed itself, which `selfCheck` reproduces before the overlay
// is allowed to draw.
//
// Particles that drift along the flow, each trail coloured by its speed, over whatever lies
// beneath (the depth layer among it). An overlay that carries each node's distance to the nearest
// current station it was corrected with draws its trails fainter the further that station is.
// Each overlay also carries the coastline, and no trail starts or runs over land. They read a regular grid laid over the mesh, evenly spaced
// in Web Mercator so that it maps onto the screen with a plain scale and offset at every zoom.
(function (root) {
  'use strict';

  const DEG = Math.PI / 180;

  // ---- astronomy (port of tools/lib/adcirc.py) -------------------------------------------

  function meanLongitudes(ms) {
    const jd = 2440587.5 + ms / 86400000;
    const t = (jd - 2451545.0) / 36525.0;
    const s = 218.3164477 + 481267.88123421 * t - 0.0015786 * t * t;
    const h = 280.46646 + 36000.76983 * t + 0.0003032 * t * t;
    const p = 83.3532465 + 4069.0137287 * t - 0.01032 * t * t;
    const n = 125.04452 - 1934.136261 * t + 0.0020708 * t * t;
    const pp = 282.937348 + 1.7195366 * t + 0.00045688 * t * t;
    const d = new Date(ms);
    const utH = d.getUTCHours() + d.getUTCMinutes() / 60 + d.getUTCSeconds() / 3600;
    return { s, h, p, n, pp, T: 15 * utH };
  }

  function baseNodal(key, N) {
    const c = Math.cos(N * DEG), c2 = Math.cos(2 * N * DEG), c3 = Math.cos(3 * N * DEG);
    const s = Math.sin(N * DEG), s2 = Math.sin(2 * N * DEG), s3 = Math.sin(3 * N * DEG);
    switch (key) {
      case 'M2': return [1.0004 - 0.0373 * c + 0.0002 * c2, -2.14 * s];
      case 'O1': return [1.0089 + 0.1871 * c - 0.0147 * c2 + 0.0014 * c3, 10.80 * s - 1.34 * s2 + 0.19 * s3];
      case 'K1': return [1.0060 + 0.1150 * c - 0.0088 * c2 + 0.0006 * c3, -8.86 * s + 0.68 * s2 - 0.07 * s3];
      case 'K2': return [1.0241 + 0.2863 * c + 0.0083 * c2 - 0.0015 * c3, -17.74 * s + 0.68 * s2 - 0.04 * s3];
      case 'J1': return [1.0129 + 0.1676 * c - 0.0170 * c2 + 0.0016 * c3, -12.94 * s + 1.34 * s2 - 0.19 * s3];
      case 'OO1': return [1.1027 + 0.6504 * c + 0.0317 * c2 - 0.0014 * c3, -36.68 * s + 4.02 * s2 - 0.57 * s3];
      case 'Mf': return [1.0429 + 0.4135 * c - 0.0040 * c2, -23.74 * s + 2.68 * s2 - 0.38 * s3];
      case 'Mm': return [1.0000 - 0.1300 * c + 0.0013 * c2, 0.0];
      default: return [1.0, 0.0];
    }
  }

  function nodal(key, N, fRef) {
    if (key === 'none') return [1.0, 0.0];
    if (key === 'fixed') return [fRef, 0.0];
    if (['M2', 'O1', 'K1', 'K2', 'J1', 'OO1', 'Mf', 'Mm'].includes(key)) return baseNodal(key, N);
    const [fm, um] = baseNodal('M2', N);
    const [fk, uk] = baseNodal('K1', N);
    switch (key) {
      case 'M2^2': return [fm ** 2, 2 * um];
      case 'M2^3': return [fm ** 3, 3 * um];
      case 'M2^4': return [fm ** 4, 4 * um];
      case 'M2^1.5': return [fm ** 1.5, 1.5 * um];
      case 'M2*K1': return [fm * fk, um + uk];
      case 'M2^2*K1': return [fm ** 2 * fk, 2 * um + uk];
      default: throw new Error(`unknown nodal group ${key}`);
    }
  }

  function decode(b64, Type) {
    const bin = atob(b64);
    const bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    return new Type(bytes.buffer);
  }

  const mercY = lat => Math.log(Math.tan(Math.PI / 4 + lat * DEG / 2));
  const invMercY = y => (2 * Math.atan(Math.exp(y)) - Math.PI / 2) / DEG;

  // ---- the field ----------------------------------------------------------------------------

  class CurrentField {
    constructor(data) {
      this.data = data;
      this.nodeCount = data.nodeCount;
      this.cons = data.constituents;
      this.xy = decode(data.nodes, Float32Array);         // lon, lat per node
      this.tri = decode(data.triangles, Uint16Array);     // three node indices per element
      this.coeff = decode(data.coefficients, Int16Array); // node, constituent, (a_u, b_u, a_v, b_v)
      if (this.xy.length !== 2 * this.nodeCount || this.tri.length !== 3 * data.triangleCount ||
          this.coeff.length !== 4 * this.nodeCount * this.cons.length) {
        throw new Error('overlay arrays do not match their stated sizes');
      }
      // the coastline, as each mask row's crossings: land where an odd number lie west of a point
      const m = data.landMask;
      this.mask = m ? { ...m, dY: m.dLon * DEG, off: decode(m.offsets, Uint32Array), cr: decode(m.crossings, Uint16Array) } : null;
      // distance to the nearest station, 0.1 km a step, 255 where none is within reach
      this.near = data.nearestKm ? decode(data.nearestKm, Uint8Array) : null;
      if (this.near && this.near.length !== this.nodeCount) {
        throw new Error('overlay station distances do not match its node count');
      }
      this.u = new Float32Array(this.nodeCount);
      this.v = new Float32Array(this.nodeCount);
      this.time = null;
      this._shoreEdges(data);
    }

    // The mesh's own shoreline, its edges bucketed by 0.02°: water the mesh does not reach takes
    // the current at the nearest point of it, within extendKm, as `extract` does.
    _shoreEdges(data) {
      this.extendKm = data.extendKm || 0;
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
      for (const [key, v] of seen) {
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

    // For water outside the mesh: the element and weights at the nearest point of the mesh's
    // shoreline, when it lies within extendKm and the straight line to it crosses no land; null
    // otherwise, and null on land.
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

    // km to the nearest station at a point of an element, null where a corner has none in reach
    nearKm(a, b, c, w1, w2, w3) {
      if (!this.near) return null;
      const n = this.near;
      if (n[a] === 255 || n[b] === 255 || n[c] === 255) return null;
      return (w1 * n[a] + w2 * n[b] + w3 * n[c]) / 10;
    }

    // u, v (m/s, east and north, depth-averaged) at every node at a UTC instant in ms
    computeNodes(ms) {
      const { s, h, p, n: N, pp, T } = meanLongitudes(ms);
      const nk = this.cons.length;
      const fc = new Float64Array(nk), fs = new Float64Array(nk);
      this.cons.forEach((c, i) => {
        const [nT, ns, nh, np, npp] = c.doodson;
        const a = (nT * T + ns * s + nh * h + np * p + npp * pp) * DEG;
        const [f, u] = nodal(c.nodal, N, c.fRef);
        const base = a + u * DEG + c.C;
        fc[i] = f * Math.cos(base) * c.scale;
        fs[i] = f * Math.sin(base) * c.scale;
      });
      const q = this.coeff;
      for (let j = 0, k = 0; j < this.nodeCount; j++) {
        let u = 0, v = 0;
        for (let i = 0; i < nk; i++, k += 4) {
          u += q[k] * fc[i] + q[k + 1] * fs[i];
          v += q[k + 2] * fc[i] + q[k + 3] * fs[i];
        }
        this.u[j] = u;
        this.v[j] = v;
      }
      this.time = ms;
    }

    // Reproduce the values the Python tool computed when it wrote the file; any drift means the
    // browser's astronomy no longer matches the Python tool's, and the overlay must not draw.
    selfCheck(tolerance = 0.002) {
      let worst = 0;
      for (const c of this.data.checks) {
        this.computeNodes(c.t * 1000);
        worst = Math.max(worst, Math.hypot(this.u[c.node] - c.u, this.v[c.node] - c.v));
      }
      this.time = null;
      return { ok: worst <= tolerance, worst, count: this.data.checks.length };
    }

    // The current at a coordinate, interpolated across its element in lon/lat exactly as
    // `extract` does, or at the nearest point of the mesh's shoreline for water the mesh does not
    // reach; null elsewhere. Needs computeNodes first.
    at(lat, lon) {
      const { xy, tri } = this;
      const value = (a, b, c, w1, w2, w3) => {
        const u = w1 * this.u[a] + w2 * this.u[b] + w3 * this.u[c];
        const v = w1 * this.v[a] + w2 * this.v[b] + w3 * this.v[c];
        return { u, v, speed: Math.hypot(u, v), toward: (Math.atan2(u, v) / DEG + 360) % 360,
          km: this.nearKm(a, b, c, w1, w2, w3), field: this };
      };
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
        if (w1 < -1e-9 || w2 < -1e-9 || w3 < -1e-9) continue;
        return value(a, b, c, w1, w2, w3);
      }
      const q = this.edgePoint(lat, lon);
      return q ? value(tri[q.e], tri[q.e + 1], tri[q.e + 2], q.w1, q.w2, q.w3) : null;
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
      if (field.buckets.size) {
        for (let r = 0; r < this.rows; r++) {
          const lat = invMercY(this.yN - (r + 0.5) * this.dY);
          for (let c = 0; c < this.cols; c++) {
            const idx = r * this.cols + c;
            if (this.elem[idx] !== 0) continue;
            const q = field.edgePoint(lat, W + (c + 0.5) * this.dLon);
            if (!q) continue;
            this.elem[idx] = q.e / 3 + 1;
            this.w1[idx] = Math.round(q.w1 * 255);
            this.w2[idx] = Math.round(q.w2 * 255);
          }
        }
      }
      // how faint each cell draws: 0 within 2 km of a station, 1 to 6 km, 2 beyond or with none
      this.fade = null;
      if (field.near) {
        this.fade = new Uint8Array(size);
        for (let i = 0; i < size; i++) {
          if (this.elem[i] === 0) continue;
          const e = (this.elem[i] - 1) * 3;
          const x = this.w1[i] / 255, y = this.w2[i] / 255;
          const km = field.nearKm(tri[e], tri[e + 1], tri[e + 2], x, y, Math.max(0, 1 - x - y));
          this.fade[i] = km === null || km >= 6 ? 2 : km >= 2 ? 1 : 0;
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

  // Speed in m/s to a trail colour, in stepped bands so each level stands apart from the next,
  // in hues the depth layer's blues leave free: white at still water and violet through the slow
  // bands, a jump to teal at SLOW, the window threshold, then green and yellow to red in the
  // fastest passes. Each band runs from its own speed up to the next band's; the legend shows
  // the same bands.
  const SLOW = 0.25;
  const BANDS = [
    [0.00, [255, 255, 255]],
    [0.05, [196, 181, 253]],
    [0.10, [167, 139, 250]],
    [0.15, [139, 92, 246]],
    [0.20, [109, 40, 217]],
    [0.25, [20, 184, 166]],
    [0.35, [34, 197, 94]],
    [0.50, [132, 204, 22]],
    [0.70, [234, 179, 8]],
    [0.90, [245, 158, 11]],
    [1.10, [249, 115, 22]],
    [1.40, [239, 68, 68]],
    [1.80, [220, 38, 38]],
    [2.20, [185, 28, 28]],
    [2.75, [127, 29, 29]],
  ];
  const STROKES = BANDS.map(([, rgb]) => `rgb(${rgb.join(',')})`);
  // trail opacity by distance to the nearest station: within 2 km, 2 to 6 km, beyond
  const FADES = [1, 0.6, 0.35];
  const bandOf = sp => {
    let k = 0;
    while (k < BANDS.length - 1 && sp >= BANDS[k + 1][0]) k++;
    return k;
  };

  // ---- the Leaflet layer ----------------------------------------------------------------------

  function makeLayer(L) {
    return L.Layer.extend({
      options: { pane: 'overlayPane', particleSpeed: 0.75, particleDensity: 1 / 220, maxParticles: 6000 },

      initialize(fields, options) {
        L.setOptions(this, options);
        this._grids = fields.map(f => new FieldGrid(f));
        this._time = Date.now();
        this._particles = [];
      },

      // The current at a coordinate at the layer's moment, exactly as `blend_model.py at`
      // reads an extract there: { u, v, speed, toward } in m/s and degrees true, null outside
      // every mesh.
      readAt(lat, lon) {
        for (const g of this._grids) {
          if (g.field.time !== this._time) {
            g.field.computeNodes(this._time);
            g.update();
          }
          const r = g.field.at(lat, lon);
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

  const api = { meanLongitudes, nodal, CurrentField, FieldGrid, BANDS, SLOW };
  if (typeof module === 'object' && module.exports) {
    module.exports = api;
  } else {
    root.DiveCurrents = api;
    if (root.L) api.CurrentLayer = makeLayer(root.L);
  }
})(typeof window !== 'undefined' ? window : this);

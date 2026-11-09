// Tidal current overlay for map.html: the ENPAC15 ADCIRC field, reconstructed in the browser
// for any moment from the harmonic constants that `tools/adcirc_current.py export-map` writes
// to map/currents/<name>.js. The astronomy below is a line-for-line port of that tool's
// mean_longitudes, _base_nodal, nodal and reconstruct, and each overlay file carries values the
// tool computed itself, which `selfCheck` reproduces before the overlay is allowed to draw.
//
// Two layers on one Leaflet layer: speed as shades of blue, and particles that drift along the
// flow. Both read a regular grid laid over the mesh, evenly spaced in Web Mercator so that it
// maps onto the screen with a plain scale and offset at every zoom.
(function (root) {
  'use strict';

  const DEG = Math.PI / 180;

  // ---- astronomy (port of tools/adcirc_current.py) ---------------------------------------

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
      this.u = new Float32Array(this.nodeCount);
      this.v = new Float32Array(this.nodeCount);
      this.time = null;
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
    // browser's astronomy no longer matches `adcirc_current.py`, and the overlay must not draw.
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
    // `extract` does; null outside the mesh. Needs computeNodes first.
    at(lat, lon) {
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
        if (w1 < -1e-9 || w2 < -1e-9 || w3 < -1e-9) continue;
        const u = w1 * this.u[a] + w2 * this.u[b] + w3 * this.u[c];
        const v = w1 * this.v[a] + w2 * this.v[b] + w3 * this.v[c];
        return { u, v, speed: Math.hypot(u, v), toward: (Math.atan2(u, v) / DEG + 360) % 360 };
      }
      return null;
    }
  }

  // A regular grid over the field's box, square cells of about `cellM` metres, evenly spaced in
  // Web Mercator. Each cell remembers the element its centre falls in, as its number plus one,
  // and two of its weights in 1/255ths, kept small so a box the size of the Salish Sea fits in
  // memory; cells outside the mesh hold 0 and stay blank.
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
      for (let e = 0; e < tri.length; e += 3) {
        const x1 = gx(tri[e]), y1 = gy(tri[e]), x2 = gx(tri[e + 1]), y2 = gy(tri[e + 1]), x3 = gx(tri[e + 2]), y3 = gy(tri[e + 2]);
        const det = (y2 - y3) * (x1 - x3) + (x3 - x2) * (y1 - y3);
        if (det === 0) continue;
        const c0 = Math.max(0, Math.floor(Math.min(x1, x2, x3) - 0.5));
        const c1 = Math.min(this.cols - 1, Math.ceil(Math.max(x1, x2, x3) - 0.5));
        const r0 = Math.max(0, Math.floor(Math.min(y1, y2, y3) - 0.5));
        const r1 = Math.min(this.rows - 1, Math.ceil(Math.max(y1, y2, y3) - 0.5));
        for (let r = r0; r <= r1; r++) {
          const py = r + 0.5;
          for (let c = c0; c <= c1; c++) {
            const idx = r * this.cols + c;
            if (this.elem[idx] !== 0) continue;
            const px = c + 0.5;
            const a = ((y2 - y3) * (px - x3) + (x3 - x2) * (py - y3)) / det;
            const b = ((y3 - y1) * (px - x3) + (x1 - x3) * (py - y3)) / det;
            if (a < -1e-9 || b < -1e-9 || 1 - a - b < -1e-9) continue;
            this.elem[idx] = e / 3 + 1;
            this.w1[idx] = Math.round(Math.max(0, a) * 255);
            this.w2[idx] = Math.round(Math.max(0, b) * 255);
          }
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

    // bilinear u, v at a fractional grid position; null where any corner is outside the mesh
    sample(gx, gy) {
      const x = gx - 0.5, y = gy - 0.5;
      const c = Math.floor(x), r = Math.floor(y);
      if (c < 0 || r < 0 || c + 1 >= this.cols || r + 1 >= this.rows) return null;
      const i = r * this.cols + c;
      const { elem } = this;
      if (!elem[i] || !elem[i + 1] || !elem[i + this.cols] || !elem[i + this.cols + 1]) return null;
      const fx = x - c, fy = y - r;
      const bl = (arr) => (arr[i] * (1 - fx) + arr[i + 1] * fx) * (1 - fy) +
        (arr[i + this.cols] * (1 - fx) + arr[i + this.cols + 1] * fx) * fy;
      return [bl(this.u), bl(this.v)];
    }
  }

  // ---- colour ---------------------------------------------------------------------------------

  // Speed in m/s to a colour, in stepped bands so each level stands apart from the next: light
  // sky blue at slack, through teal, green and yellow, to red in the fastest passes. The slow
  // bands are pale and partly transparent, close to the base map's own water, so the shoreline,
  // where the water is usually slow, blends into the map. Each band runs from its own speed up
  // to the next band's; the 0.25 m/s step is the window threshold.
  const BANDS = [
    [0.00, [125, 211, 252], 0.40],
    [0.10, [56, 189, 248], 0.50],
    [0.25, [14, 165, 233], 0.60],
    [0.40, [18, 163, 168], 0.72],
    [0.60, [47, 191, 138], 0.72],
    [0.80, [124, 207, 79], 0.72],
    [1.00, [200, 214, 47], 0.72],
    [1.25, [245, 197, 24], 0.72],
    [1.50, [245, 147, 34], 0.72],
    [2.00, [232, 84, 28], 0.72],
    [2.50, [200, 29, 29], 0.72],
  ];
  const LUT_MAX = 3.0, LUT_N = 301;
  const LUT = new Uint8ClampedArray(LUT_N * 4);
  for (let i = 0; i < LUT_N; i++) {
    const sp = (i / (LUT_N - 1)) * LUT_MAX + 1e-9;
    let k = 0;
    while (k < BANDS.length - 1 && sp >= BANDS[k + 1][0]) k++;
    const [, rgb, alpha] = BANDS[k];
    for (let ch = 0; ch < 3; ch++) LUT[i * 4 + ch] = rgb[ch];
    LUT[i * 4 + 3] = 255 * alpha;
  }

  // ---- the Leaflet layer ----------------------------------------------------------------------

  function makeLayer(L) {
    return L.Layer.extend({
      options: { pane: 'overlayPane', particleSpeed: 0.9, particleDensity: 1 / 220, maxParticles: 6000 },

      initialize(fields, options) {
        L.setOptions(this, options);
        this._grids = fields.map(f => new FieldGrid(f));
        this._time = Date.now();
        this._particles = [];
      },

      setTime(ms) {
        this._time = ms;
        if (!this._map) return;
        if (this._pendingTime) return;
        this._pendingTime = requestAnimationFrame(() => {
          this._pendingTime = null;
          this._computeField();
          this._drawSpeed();
        });
      },

      onAdd(map) {
        const pane = map.getPane(this.options.pane);
        this._speedCanvas = L.DomUtil.create('canvas', 'leaflet-zoom-hide current-speed', pane);
        this._particleCanvas = L.DomUtil.create('canvas', 'leaflet-zoom-hide current-particles', pane);
        for (const c of [this._speedCanvas, this._particleCanvas]) {
          c.style.position = 'absolute';
          c.style.pointerEvents = 'none';
        }
        this._raster = this._grids.map(g => {
          const c = document.createElement('canvas');
          c.width = g.cols;
          c.height = g.rows;
          return { canvas: c, ctx: c.getContext('2d'), image: c.getContext('2d').createImageData(g.cols, g.rows) };
        });
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
        this._speedCanvas.remove();
        this._particleCanvas.remove();
      },

      _computeField() {
        this._grids.forEach((g, n) => {
          g.field.computeNodes(this._time);
          g.update();
          const { image } = this._raster[n];
          const px = image.data;
          for (let i = 0; i < g.elem.length; i++) {
            const o = i * 4;
            if (g.elem[i] === 0) { px[o + 3] = 0; continue; }
            const sp = Math.hypot(g.u[i], g.v[i]);
            const k = Math.min(LUT_N - 1, Math.floor((sp / LUT_MAX) * (LUT_N - 1))) * 4;
            px[o] = LUT[k]; px[o + 1] = LUT[k + 1]; px[o + 2] = LUT[k + 2]; px[o + 3] = LUT[k + 3];
          }
          this._raster[n].ctx.putImageData(image, 0, 0);
        });
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
        for (const c of [this._speedCanvas, this._particleCanvas]) {
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
        this._drawSpeed();
        this._seedParticles();
        this._pause();
        this._animate();
      },

      _drawSpeed() {
        if (!this._size) return;
        const ctx = this._speedCanvas.getContext('2d');
        ctx.clearRect(0, 0, this._size.x, this._size.y);
        ctx.imageSmoothingEnabled = true;
        this._views.forEach((view, n) => {
          if (!view.visible) return;
          const { g, nw, sx, sy } = view;
          ctx.drawImage(this._raster[n].canvas, nw.x, nw.y, sx * g.cols, sy * g.rows);
        });
      },

      // a random point on screen that sits inside a field's mesh, or null after a few tries
      _spawn(p) {
        const views = this._views.filter(v => v.visible);
        if (!views.length) return false;
        for (let tries = 0; tries < 20; tries++) {
          const x = Math.random() * this._size.x, y = Math.random() * this._size.y;
          for (const view of views) {
            const gx = (x - view.nw.x) / view.sx, gy = (y - view.nw.y) / view.sy;
            if (view.g.sample(gx, gy)) {
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
        const step = () => {
          if (!this._map) return;
          const { x: w, y: h } = this._size;
          ctx.globalCompositeOperation = 'destination-in';
          ctx.fillStyle = 'rgba(0,0,0,0.92)';
          ctx.fillRect(0, 0, w, h);
          ctx.globalCompositeOperation = 'source-over';
          ctx.strokeStyle = 'rgba(255,255,255,0.85)';
          ctx.lineWidth = 1.2;
          ctx.beginPath();
          const k = this.options.particleSpeed;
          for (const p of this._particles) {
            if (--p.age < 0 || !p.live) {
              if (p.age < 0) this._spawn(p);
              continue;
            }
            const view = p.view;
            const uv = view.g.sample((p.x - view.nw.x) / view.sx, (p.y - view.nw.y) / view.sy);
            if (!uv) { p.age = -1; continue; }
            const nx = p.x + uv[0] * k, ny = p.y - uv[1] * k;
            ctx.moveTo(p.x, p.y);
            ctx.lineTo(nx, ny);
            p.x = nx; p.y = ny;
            if (nx < 0 || ny < 0 || nx > w || ny > h) p.age = -1;
          }
          ctx.stroke();
          this._frame = requestAnimationFrame(step);
        };
        this._frame = requestAnimationFrame(step);
      },
    });
  }

  const api = { meanLongitudes, nodal, CurrentField, FieldGrid };
  if (typeof module === 'object' && module.exports) {
    module.exports = api;
  } else {
    root.DiveCurrents = api;
    if (root.L) api.CurrentLayer = makeLayer(root.L);
  }
})(typeof window !== 'undefined' ? window : this);

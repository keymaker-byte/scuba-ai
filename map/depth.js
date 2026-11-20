// Seabed depth layer for the map viewer: the depth at the map's moment, tide included.
//
// `tools/ncei_depth.py --export-map` writes the tiles and a description of the layer
// (map/depth/<name>.js, window.MAP_DEPTH[name]). Each tile pixel holds a 16-bit value v in its
// red (high byte) and green (low byte) channels: depth below NAVD 88 = (v - 1) * scale +
// shallowest; v = 0 is transparent, higher ground or no data. The blue channel names the water:
// 0 the sea, k the k-th lake in the description's `lakes`, whose pixels hold the depth below
// that lake's own surface and take no tide. The description carries depths the Python tool read
// at sample points; check() reproduces them before the layer draws.
//
// A DiveTides.TideModel (map/tides.js) places each depth on MLLW and adds the tide:
//   depth below MLLW  = depth below NAVD 88 - NAVD 88's height above MLLW
//   depth at a moment = depth below MLLW + the tide above MLLW at that moment
// Both are blended from the nearest points that know them, and vary slowly, so a tile works
// them out on a lattice every 16 pixels and interpolates between. Ground the tide uncovers
// is drawn in sand; ground above the year's highest tide is left transparent.
(function (root) {
  'use strict';

  // Depth bands at the moment, in metres below the surface, shallow to deep.
  const BANDS = [
    { to: 1, color: [232, 247, 253] },
    { to: 2, color: [220, 242, 252] },
    { to: 3, color: [208, 237, 250] },
    { to: 5, color: [196, 232, 248] },
    { to: 10, color: [177, 222, 245] },
    { to: 15, color: [155, 211, 240] },
    { to: 20, color: [125, 194, 232] },
    { to: 25, color: [95, 175, 223] },
    { to: 30, color: [70, 155, 211] },
    { to: 35, color: [52, 135, 196] },
    { to: 40, color: [40, 115, 179] },
    { to: 60, color: [31, 94, 156] },
    { to: 100, color: [25, 74, 130] },
    { to: Infinity, color: [20, 56, 104] },
  ];
  const DRY = [222, 206, 160];
  function bandOf(d) {
    if (d < 0) return -1;
    for (let i = 0; i < BANDS.length; i++) if (d < BANDS[i].to) return i;
    return BANDS.length - 1;
  }

  // Light from the north-west, 45 degrees up, the usual hillshade.
  const SUN_AZ = 315 * Math.PI / 180;
  const SUN_ALT = 45 * Math.PI / 180;
  const FLAT = Math.sin(SUN_ALT);
  // The direction toward the sun, in east, north, up.
  const SUN = [Math.sin(SUN_AZ) * Math.cos(SUN_ALT), Math.cos(SUN_AZ) * Math.cos(SUN_ALT), Math.sin(SUN_ALT)];
  const EARTH_M = 2 * Math.PI * 6378137;
  const CACHE_TILES = 256;
  const STEP = 16;                 // lattice spacing, stored-tile pixels
  const NODES = 256 / STEP + 1;    // lattice nodes per side

  // Change in depth per cell along (ux, uy) at cell (c, r): centred where both neighbours exist
  // and hold data, one-sided at the tile's edge or beside a gap, so an edge keeps full shading.
  function slopeAlong(at, c, r, ux, uy, d) {
    const inside = (cc, rr) => cc >= 0 && cc < 256 && rr >= 0 && rr < 256;
    const a = inside(c + ux, r + uy) ? at(c + ux, r + uy) : NaN;
    const b = inside(c - ux, r - uy) ? at(c - ux, r - uy) : NaN;
    if (!Number.isNaN(a) && !Number.isNaN(b)) return (a - b) / 2;
    if (!Number.isNaN(a)) return a - d;
    if (!Number.isNaN(b)) return d - b;
    return 0;
  }

  const tileLat = (y, z) => Math.atan(Math.sinh(Math.PI * (1 - 2 * y / 2 ** z))) * 180 / Math.PI;
  const tileLon = (x, z) => x / 2 ** z * 360 - 180;

  class DepthSource {
    constructor(meta, tides) {
      this.meta = meta;
      this.tides = tides;
      this.present = {};
      for (const [z, list] of Object.entries(meta.present)) {
        this.present[z] = new Set(list ? list.split(',') : []);
      }
      this.cache = new Map();
      this.lattices = new Map();
    }

    has(z, x, y) {
      const s = this.present[z];
      return !!s && s.has(`${x}/${y}`);
    }

    // One stored tile: depth, a Float32Array of 65536 (NaN where none), below NAVD 88 at sea
    // and below the lake's surface in a lake; kind, a Uint8Array, 0 sea or the lake's number.
    // Rejects with the browser's SecurityError when the page cannot read image pixels.
    load(z, x, y) {
      const key = `${z}/${x}/${y}`;
      let p = this.cache.get(key);
      if (p) {
        this.cache.delete(key);
        this.cache.set(key, p);
        return p;
      }
      const { scale, shallowest } = this.meta;
      p = new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = () => {
          try {
            const c = document.createElement('canvas');
            c.width = c.height = 256;
            const ctx = c.getContext('2d', { willReadFrequently: true });
            ctx.drawImage(img, 0, 0);
            const px = ctx.getImageData(0, 0, 256, 256).data;
            const depth = new Float32Array(65536), kind = new Uint8Array(65536);
            for (let i = 0; i < 65536; i++) {
              const v = px[4 * i + 3] ? (px[4 * i] << 8) | px[4 * i + 1] : 0;
              depth[i] = v ? (v - 1) * scale + shallowest : NaN;
              kind[i] = v ? px[4 * i + 2] : 0;
            }
            resolve({ depth, kind });
          } catch (err) {
            reject(err);
          }
        };
        img.onerror = () => reject(new Error(`depth tile ${key} failed to load`));
        img.src = this.meta.tiles.replace('{z}', z).replace('{x}', x).replace('{y}', y);
      });
      p.catch(() => this.cache.delete(key));
      this.cache.set(key, p);
      while (this.cache.size > CACHE_TILES) this.cache.delete(this.cache.keys().next().value);
      return p;
    }

    // A stored tile's lattice: at each node, NAVD 88's height above MLLW, the year's highest
    // tide, and the tide stations with their weights.
    lattice(z, x, y) {
      const key = `${z}/${x}/${y}`;
      let lat = this.lattices.get(key);
      if (!lat) {
        const n = NODES * NODES;
        lat = { navd88: new Float32Array(n), high: new Float32Array(n), blend: new Array(n) };
        for (let j = 0; j < NODES; j++) {
          for (let i = 0; i < NODES; i++) {
            const la = tileLat(y + j * STEP / 256, z), lo = tileLon(x + i * STEP / 256, z);
            const k = j * NODES + i;
            const d = this.tides.datumAt(la, lo);
            lat.navd88[k] = d.navd88;
            lat.high[k] = d.high;
            lat.blend[k] = this.tides.tideBlend(la, lo);
          }
        }
        this.lattices.set(key, lat);
        while (this.lattices.size > CACHE_TILES) this.lattices.delete(this.lattices.keys().next().value);
      }
      return lat;
    }

    // The stored pixel at a point, read at the most detailed zoom: { depth, lake }, depth below
    // NAVD 88 at sea (lake 0) or below the surface of lake number `lake`; null where the layer
    // holds nothing (outside its tiles, or higher ground).
    async depthAt(map, latlng) {
      const z = this.meta.maxZoom;
      const p = map.project(latlng, z);
      const x = Math.floor(p.x / 256), y = Math.floor(p.y / 256);
      if (!this.has(z, x, y)) return null;
      const t = await this.load(z, x, y);
      const i = Math.floor(p.y - y * 256) * 256 + Math.floor(p.x - x * 256);
      return Number.isNaN(t.depth[i]) ? null : { depth: t.depth[i], lake: t.kind[i] };
    }

    // Everything the readout shows at a point and moment, or null where the layer holds
    // nothing. mllw is the depth below MLLW (negative on ground that dries), tide the height
    // above MLLW, total their sum; above the year's highest tide the point is land.
    // In a lake: { lake: name, depth } below the lake's surface.
    async readAt(map, latlng, ms) {
      const px = await this.depthAt(map, latlng);
      if (px === null) return null;
      if (px.lake) return { lake: this.meta.lakes[px.lake - 1].name, depth: px.depth };
      const navd = px.depth;
      const { navd88, high } = this.tides.datumAt(latlng.lat, latlng.lng);
      const mllw = navd - navd88;
      if (mllw < -high) return { land: true };
      const tide = this.tides.tideAt(latlng.lat, latlng.lng, ms);
      return { mllw, tide: tide.height, total: mllw + tide.height, parts: tide.parts };
    }

    // Reproduce the depths the Python tool read at its sample points.
    async check(map) {
      let worst = 0;
      const tol = this.meta.scale / 2 + 0.01;
      for (const c of this.meta.checks) {
        const d = await this.depthAt(map, L.latLng(c.lat, c.lon));
        worst = Math.max(worst, d === null || d.lake !== c.lake ? Infinity : Math.abs(d.depth - c.depth));
      }
      return { ok: worst <= tol, worst };
    }
  }

  const DepthLayer = L.GridLayer.extend({
    initialize(source, options) {
      this.source = source;
      this.time = Date.now();
      L.GridLayer.prototype.initialize.call(this, L.extend({
        minZoom: source.meta.minZoom,
        bounds: L.latLngBounds(source.meta.bounds),
        opacity: 0.8,
      }, options));
    },

    // Repaint every tile on screen for a new moment, at most once per animation frame.
    setTime(ms) {
      this.time = ms;
      if (this._frame || !this._map) return;
      this._frame = requestAnimationFrame(() => {
        this._frame = 0;
        for (const t of Object.values(this._tiles || {})) {
          if (t.el._depth) this._paint(t.el);
        }
      });
    },

    createTile(coords, done) {
      const tile = document.createElement('canvas');
      tile.width = tile.height = 256;
      const zMax = this.source.meta.maxZoom;
      const dz = Math.max(0, coords.z - zMax);
      const zd = coords.z - dz;
      const k = 2 ** dz;
      const xd = Math.floor(coords.x / k), yd = Math.floor(coords.y / k);
      if (!this.source.has(zd, xd, yd)) {
        setTimeout(() => done(null, tile), 0);
        return tile;
      }
      this.source.load(zd, xd, yd).then(({ depth, kind }) => {
        tile._depth = {
          depth, kind, zd, xd, yd, k,
          ox: (coords.x - xd * k) * 256 / k, oy: (coords.y - yd * k) * 256 / k,
          lattice: this.source.lattice(zd, xd, yd),
        };
        try {
          this._paint(tile);
          done(null, tile);
        } catch (err) {
          done(err, tile);
          this.fire('tidefailure', { error: err });
        }
      }, err => done(err, tile));
      return tile;
    },

    // Colour, shade and outline one screen tile at the layer's moment, from the stored tile
    // that covers it: the screen tile is the stored tile's square at (ox, oy), magnified k times.
    _paint(tile) {
      const { depth, kind, zd, yd, k, ox, oy, lattice } = tile._depth;
      const lv = this.source.tides.levels(this.time);
      // At each lattice node: the shift from depth below NAVD 88 to depth at the moment, and
      // the depth below NAVD 88 above which the ground is out of the tide's reach.
      const n = NODES * NODES;
      const shift = new Float32Array(n), reach = new Float32Array(n);
      for (let i = 0; i < n; i++) {
        let tide = 0;
        for (const b of lattice.blend[i]) tide += b.w * lv[b.i];
        shift[i] = tide - lattice.navd88[i];
        reach[i] = lattice.navd88[i] - lattice.high[i];
      }
      const lerp = (arr, u, v) => {
        const gu = Math.min(NODES - 1.001, u / STEP), gv = Math.min(NODES - 1.001, v / STEP);
        const i0 = Math.floor(gu), j0 = Math.floor(gv), fu = gu - i0, fv = gv - j0;
        const a = arr[j0 * NODES + i0], b = arr[j0 * NODES + i0 + 1];
        const c = arr[(j0 + 1) * NODES + i0], d = arr[(j0 + 1) * NODES + i0 + 1];
        return (a * (1 - fu) + b * fu) * (1 - fv) + (c * (1 - fu) + d * fu) * fv;
      };
      const lat = Math.atan(Math.sinh(Math.PI * (1 - 2 * (yd + 0.5) / 2 ** zd)));
      const cell = EARTH_M * Math.cos(lat) / (256 * 2 ** zd);
      const idx = (c, r) => Math.min(255, Math.max(0, r)) * 256 + Math.min(255, Math.max(0, c));
      const at = (c, r) => depth[idx(c, r)];
      const ctx = tile.getContext('2d');
      const img = ctx.createImageData(256, 256);
      const out = img.data;
      const src = i => Math.floor(i / k);
      const x0 = Math.floor(ox), y0 = Math.floor(oy);
      for (let j = 0; j < 256; j++) {
        const r = y0 + src(j), rDown = y0 + src(j + 1);
        const v = oy + (j + 0.5) / k;
        for (let i = 0; i < 256; i++) {
          const c = x0 + src(i);
          const d = at(c, r);
          if (Number.isNaN(d)) continue;
          // A lake pixel is its depth below the lake's own surface; the sea moves with the tide.
          const lake = kind[idx(c, r)];
          const u = ox + (i + 0.5) / k;
          if (!lake && d < lerp(reach, u, v)) continue;  // above the year's highest tide
          const s = lake ? 0 : lerp(shift, u, v);
          const band = bandOf(d + s);
          let [R, G, B] = band < 0 ? DRY : BANDS[band].color;
          // Slope shading. dx is the depth's change eastward, dy southward (down the rows); the
          // seabed's upward normal is then (dx, -dy, 1) in east, north, up.
          const dx = slopeAlong(at, c, r, 1, 0, d) / cell;
          const dy = slopeAlong(at, c, r, 0, 1, d) / cell;
          const shade = (dx * SUN[0] - dy * SUN[1] + SUN[2]) / Math.hypot(dx, dy, 1);
          let f = Math.min(1.2, Math.max(0.6, 1 + 0.9 * (shade - FLAT)));
          // Band edges, the waterline among them: a right or lower neighbour in another band.
          const cR = x0 + src(i + 1);
          const dR = kind[idx(cR, r)] === lake ? at(cR, r) : NaN;
          const dD = kind[idx(c, rDown)] === lake ? at(c, rDown) : NaN;
          if ((!Number.isNaN(dR) && bandOf(dR + s) !== band) || (!Number.isNaN(dD) && bandOf(dD + s) !== band)) {
            f *= 0.72;
          }
          const o = 4 * (j * 256 + i);
          out[o] = R * f; out[o + 1] = G * f; out[o + 2] = B * f; out[o + 3] = 255;
        }
      }
      ctx.putImageData(img, 0, 0);
    },
  });

  root.DiveDepth = { BANDS, DRY, DepthSource, DepthLayer };
})(typeof window !== 'undefined' ? window : globalThis);

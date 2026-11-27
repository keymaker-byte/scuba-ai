// Seabed depth layer for the map viewer: the total depth at the map's moment, the seabed plus the
// tide.
//
// `tools/map_export.py depth` writes the tiles and a description of the layer (map/depth/depth.js,
// window.MAP_DEPTH). Each tile pixel holds a 16-bit value v in its red (high byte) and green (low
// byte) channels: the seabed = (v - 1) * scale + shallowest, the depth the depth tool answers at the
// pixel's centre; v = 0 is transparent. The blue channel names the water: an entry of `waters`,
// whose `tide` names the tide family (map/tides.js) the seabed is measured against, none for water
// with no tide; or lake0 + k, the k-th of `lakes`, whose seabed is below the lake's own surface.
//   total depth at a moment = seabed + the family's tide at that moment
//
// Every pixel is kept at the zoom of the source that answers there: a tile finer than baseZoom holds
// only the pixels of sources that fine and leaves the rest to its ancestors. At any point the layer
// reads the deepest tile holding a value there, and draws a screen tile the same way, pixel by pixel.
// The description carries depths the depth tool answered at sample pixels; check() reproduces them
// before the layer draws. The tide is blended from a family's nearest stations; it varies slowly, so
// a screen tile works it out on a lattice every 16 pixels and interpolates between. Ground the tide
// uncovers is drawn in sand; ground above the year's highest tide is left transparent.
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
  const SUN = [Math.sin(SUN_AZ) * Math.cos(SUN_ALT), Math.cos(SUN_AZ) * Math.cos(SUN_ALT), Math.sin(SUN_ALT)];
  const EARTH_M = 2 * Math.PI * 6378137;
  const CACHE_TILES = 384;
  const STEP = 16;                 // lattice spacing, screen pixels
  const NODES = 256 / STEP + 1;    // lattice nodes per side

  const tileLat = (y, z) => Math.atan(Math.sinh(Math.PI * (1 - 2 * y / 2 ** z))) * 180 / Math.PI;
  const tileLon = (x, z) => x / 2 ** z * 360 - 180;

  // Change in depth per cell along (ux, uy) at cell (c, r) of a stored tile: centred where both
  // neighbours hold data, one-sided beside a gap or the tile's edge, so an edge keeps full shading.
  function slopeAlong(depth, c, r, ux, uy, d) {
    const at = (cc, rr) => (cc >= 0 && cc < 256 && rr >= 0 && rr < 256) ? depth[rr * 256 + cc] : NaN;
    const a = at(c + ux, r + uy), b = at(c - ux, r - uy);
    if (!Number.isNaN(a) && !Number.isNaN(b)) return (a - b) / 2;
    if (!Number.isNaN(a)) return a - d;
    if (!Number.isNaN(b)) return d - b;
    return 0;
  }

  class DepthSource {
    constructor(meta, tides) {
      this.meta = meta;
      this.tides = tides;
      this.present = {};
      for (const [z, list] of Object.entries(meta.present)) this.present[z] = new Set(list ? list.split(',') : []);
      this.cache = new Map();
      this.lattices = new Map();
      for (const w of meta.waters) if (w.tide && w.tide !== 'NONE') this.tides.family(w.tide);
    }

    has(z, x, y) {
      const s = this.present[z];
      return !!s && s.has(`${x}/${y}`);
    }

    // The stored tiles a screen tile reads, deepest first: from the most detailed zoom at or below
    // the screen's down to the base zoom, each with the screen tile's square in it. Below the base
    // zoom, the stored tile at the screen's own zoom.
    chain(z, x, y) {
      const out = [];
      const { baseZoom, maxZoom } = this.meta;
      const top = z < baseZoom ? z : Math.min(z, maxZoom), bottom = z < baseZoom ? z : baseZoom;
      for (let zz = top; zz >= bottom; zz--) {
        const k = 2 ** (z - zz);
        const xs = Math.floor(x / k), ys = Math.floor(y / k);
        if (this.has(zz, xs, ys)) out.push({ z: zz, x: xs, y: ys, k, ox: (x - xs * k) * 256 / k, oy: (y - ys * k) * 256 / k });
      }
      return out;
    }

    // One stored tile: seabed, a Float32Array of 65536 (NaN where none), and water, a Uint8Array.
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
            const depth = new Float32Array(65536), water = new Uint8Array(65536);
            for (let i = 0; i < 65536; i++) {
              const v = px[4 * i + 3] ? (px[4 * i] << 8) | px[4 * i + 1] : 0;
              depth[i] = v ? (v - 1) * scale + shallowest : NaN;
              water[i] = v ? px[4 * i + 2] : 0;
            }
            resolve({ depth, water, z });
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

    // The tide family of a pixel's water: a family's name, or null for no tide (a lake, or the sea
    // where the depth tool answers with no tide).
    familyOf(water) {
      if (water >= this.meta.lake0) return null;
      const t = (this.meta.waters[water] || {}).tide;
      return t && t !== 'NONE' ? t : null;
    }

    // A screen tile's lattice: at each node, each family's stations with their weights and the
    // year's highest tide.
    lattice(z, x, y, families) {
      const key = `${z}/${x}/${y}`;
      let lat = this.lattices.get(key);
      if (!lat) {
        lat = {};
        this.lattices.set(key, lat);
        while (this.lattices.size > CACHE_TILES) this.lattices.delete(this.lattices.keys().next().value);
      }
      for (const fam of families) {
        if (lat[fam]) continue;
        const n = NODES * NODES, high = new Float32Array(n), blend = new Array(n);
        for (let j = 0; j < NODES; j++) {
          for (let i = 0; i < NODES; i++) {
            const la = tileLat(y + j * STEP / 256, z), lo = tileLon(x + i * STEP / 256, z);
            const k = j * NODES + i;
            blend[k] = this.tides.tideBlend(fam, la, lo);
            high[k] = this.tides.highAt(fam, la, lo);
          }
        }
        lat[fam] = { high, blend };
      }
      return lat;
    }

    // The stored pixel at a point, as the deepest tile holding a value there reads it: { seabed,
    // water, z }, or null where the layer holds nothing.
    async pixelAt(map, latlng) {
      for (let z = this.meta.maxZoom; z >= this.meta.baseZoom; z--) {
        const p = map.project(latlng, z);
        const x = Math.floor(p.x / 256), y = Math.floor(p.y / 256);
        if (!this.has(z, x, y)) continue;
        const t = await this.load(z, x, y);
        const i = Math.floor(p.y - y * 256) * 256 + Math.floor(p.x - x * 256);
        if (!Number.isNaN(t.depth[i])) return { seabed: t.depth[i], water: t.water[i], z };
      }
      return null;
    }

    // Everything the readout shows at a point and moment, or null where the layer holds nothing:
    // { total, seabed, tide, parts } in the sea, { lake, total, seabed, tide: 0 } in a lake, and
    // { land: true } on ground above the year's highest tide.
    async readAt(map, latlng, ms) {
      const px = await this.pixelAt(map, latlng);
      if (px === null) return null;
      if (px.water >= this.meta.lake0) {
        return { lake: this.meta.lakes[px.water - this.meta.lake0].name, total: px.seabed, seabed: px.seabed, tide: 0 };
      }
      const fam = this.familyOf(px.water);
      if (!fam) {
        if (px.seabed < 0) return { land: true };
        return { total: px.seabed, seabed: px.seabed, tide: 0, parts: [] };
      }
      if (px.seabed < -this.tides.highAt(fam, latlng.lat, latlng.lng)) return { land: true };
      const tide = this.tides.tideAt(fam, latlng.lat, latlng.lng, ms);
      return { total: px.seabed + tide.height, seabed: px.seabed, tide: tide.height, parts: tide.parts };
    }

    // Reproduce the depths the depth tool answered at the sample pixels, read as the viewer reads them.
    async check(map) {
      let worst = 0;
      const tol = this.meta.scale / 2 + 0.01;
      for (const c of this.meta.checks) {
        const d = await this.pixelAt(map, L.latLng(c.lat, c.lon));
        worst = Math.max(worst, d === null || d.water !== c.water ? Infinity : Math.abs(d.seabed - c.depth));
      }
      return { ok: this.meta.checks.length > 0 && worst <= tol, worst };
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
      const chain = this.source.chain(coords.z, coords.x, coords.y);
      if (!chain.length) {
        setTimeout(() => done(null, tile), 0);
        return tile;
      }
      Promise.all(chain.map(c => this.source.load(c.z, c.x, c.y))).then(stored => {
        tile._depth = { coords, levels: chain.map((c, i) => ({ ...c, ...stored[i] })) };
        try {
          this._compose(tile);
          this._paint(tile);
          done(null, tile);
        } catch (err) {
          done(err, tile);
          this.fire('tidefailure', { error: err });
        }
      }, err => done(err, tile));
      return tile;
    },

    // For every screen pixel, the stored tile and pixel it reads: the deepest holding a value.
    _compose(tile) {
      const { coords, levels } = tile._depth;
      const seabed = new Float32Array(65536).fill(NaN), water = new Uint8Array(65536);
      const from = new Int8Array(65536).fill(-1), at = new Int32Array(65536);
      const families = new Set();
      for (let j = 0; j < 256; j++) {
        for (let i = 0; i < 256; i++) {
          const o = j * 256 + i;
          for (let l = 0; l < levels.length; l++) {
            const lv = levels[l];
            const c = Math.floor(lv.ox + (i + 0.5) / lv.k), r = Math.floor(lv.oy + (j + 0.5) / lv.k);
            const s = r * 256 + c, d = lv.depth[s];
            if (Number.isNaN(d)) continue;
            seabed[o] = d; water[o] = lv.water[s]; from[o] = l; at[o] = s;
            const fam = this.source.familyOf(water[o]);
            if (fam) families.add(fam);
            break;
          }
        }
      }
      Object.assign(tile._depth, { seabed, water, from, at,
        lattice: this.source.lattice(coords.z, coords.x, coords.y, families), families: [...families] });
    },

    // Colour, shade and outline one screen tile at the layer's moment.
    _paint(tile) {
      const { coords, levels, seabed, water, from, at, lattice, families } = tile._depth;
      const n = NODES * NODES;
      const shift = {}, reach = {};
      for (const fam of families) {
        const lv = this.source.tides.levels(fam, this.time);
        const { blend, high } = lattice[fam];
        shift[fam] = new Float32Array(n);
        reach[fam] = new Float32Array(n);
        for (let i = 0; i < n; i++) {
          let tide = 0;
          for (const b of blend[i]) tide += b.w * lv[b.i];
          shift[fam][i] = tide;
          reach[fam][i] = -high[i];
        }
      }
      const lerp = (arr, u, v) => {
        const gu = Math.min(NODES - 1.001, u / STEP), gv = Math.min(NODES - 1.001, v / STEP);
        const i0 = Math.floor(gu), j0 = Math.floor(gv), fu = gu - i0, fv = gv - j0;
        const a = arr[j0 * NODES + i0], b = arr[j0 * NODES + i0 + 1];
        const c = arr[(j0 + 1) * NODES + i0], d = arr[(j0 + 1) * NODES + i0 + 1];
        return (a * (1 - fu) + b * fu) * (1 - fv) + (c * (1 - fu) + d * fu) * fv;
      };
      const cells = levels.map(lv => {
        const lat = Math.atan(Math.sinh(Math.PI * (1 - 2 * (lv.y + 0.5) / 2 ** lv.z)));
        return EARTH_M * Math.cos(lat) / (256 * 2 ** lv.z);
      });
      // the depth at the moment of every screen pixel, NaN where nothing is drawn
      const now = new Float32Array(65536).fill(NaN);
      for (let j = 0; j < 256; j++) {
        for (let i = 0; i < 256; i++) {
          const o = j * 256 + i, d = seabed[o];
          if (Number.isNaN(d)) continue;
          const fam = this.source.familyOf(water[o]);
          if (fam) {
            const u = i + 0.5, v = j + 0.5;
            if (d < lerp(reach[fam], u, v)) continue;   // above the year's highest tide
            now[o] = d + lerp(shift[fam], u, v);
          } else {
            if (water[o] < this.source.meta.lake0 && d < 0) continue;   // above water where there is no tide
            now[o] = d;
          }
        }
      }
      const ctx = tile.getContext('2d');
      const img = ctx.createImageData(256, 256);
      const out = img.data;
      for (let j = 0; j < 256; j++) {
        for (let i = 0; i < 256; i++) {
          const o = j * 256 + i, d = now[o];
          if (Number.isNaN(d)) continue;
          const band = bandOf(d);
          let [R, G, B] = band < 0 ? DRY : BANDS[band].color;
          // Slope shading, in the stored tile the pixel reads, at its own resolution. dx is the
          // seabed's change eastward, dy southward; the upward normal is then (dx, -dy, 1).
          const lv = levels[from[o]], s = at[o], c = s % 256, r = (s - c) / 256;
          const dx = slopeAlong(lv.depth, c, r, 1, 0, lv.depth[s]) / cells[from[o]];
          const dy = slopeAlong(lv.depth, c, r, 0, 1, lv.depth[s]) / cells[from[o]];
          const shade = (dx * SUN[0] - dy * SUN[1] + SUN[2]) / Math.hypot(dx, dy, 1);
          let f = Math.min(1.2, Math.max(0.6, 1 + 0.9 * (shade - FLAT)));
          // Band edges, the waterline among them: a right or lower neighbour in another band.
          const dR = i < 255 && water[o + 1] === water[o] ? now[o + 1] : NaN;
          const dD = j < 255 && water[o + 256] === water[o] ? now[o + 256] : NaN;
          if ((!Number.isNaN(dR) && bandOf(dR) !== band) || (!Number.isNaN(dD) && bandOf(dD) !== band)) f *= 0.72;
          const q = 4 * o;
          out[q] = R * f; out[q + 1] = G * f; out[q + 2] = B * f; out[q + 3] = 255;
        }
      }
      ctx.putImageData(img, 0, 0);
    },
  });

  root.DiveDepth = { BANDS, DRY, DepthSource, DepthLayer };
})(typeof window !== 'undefined' ? window : globalThis);

/**
 * Port map editor — drag ports on chart-area tilemaps, snap to shore (rule A).
 */
(function () {
  const GW = 2000;
  const GH = 1000;

  const TILE_COLORS = {
    totally_sea: "#1a4a6e",
    totally_land: "#6b5a45",
  };
  const COAST_COLOR = "#c9a86c";
  const SEA_RGBA = [26, 74, 110, 255];
  const LAND_RGBA = [107, 90, 69, 255];

  /** Wheel zoom per tick (~4%; previously 10% with 1.1 / 0.9). */
  const WHEEL_ZOOM_FACTOR = 1.04;
  /** Max wheel zoom (was 12). Higher reveals individual half-tile diagonals. */
  const MAX_ZOOM = 64;
  const MIN_ZOOM = 0.15;
  /**
   * Sub-pixel multiplier for the offscreen tilemap canvas. Each global tile
   * coord becomes RENDER_SCALE canvas pixels, so a 3-unit tile is rendered at
   * 12 px and diagonal/corner shapes stay crisp under high CSS zoom.
   */
  const RENDER_SCALE = 4;

  const $ = (id) => document.getElementById(id);
  const areaSelect = $("area-select");
  const portSelect = $("port-select");
  const portList = $("port-list");
  const portMeta = $("port-meta");
  const inlandCb = $("inland-exception");
  const centerBtn = $("center-port");
  const exportBtn = $("export-btn");
  const canvas = $("map-canvas");
  const ctx = canvas.getContext("2d");
  const mapWrap = $("map-wrap");
  const mapOverlay = $("map-overlay");
  const statusText = $("status-text");
  const coordsText = $("coords-text");

  let chartAreas = [];
  let allPorts = [];
  /** @type {Map<string, {id, name, chart_area_id, map_u, map_v, inland?: boolean}>} */
  const portState = new Map();

  let areaId = "";
  let bounds = null;
  let tileSize = 3;
  let shoreTiles = [];
  let landTiles = [];
  let areaPorts = [];
  let selectedPortId = "";

  /** Offscreen bitmap holding the precomposed sea+land fills (passes 1+2). */
  let tilemapCache = null;

  let viewScale = 1;
  let viewPanX = 0;
  let viewPanY = 0;

  let draggingPort = false;
  let panning = false;
  let dragOffsetX = 0;
  let dragOffsetY = 0;
  let lastPointerX = 0;
  let lastPointerY = 0;
  let dirtySession = false;

  function setStatus(msg, isErr) {
    statusText.textContent = msg;
    statusText.className = isErr ? "err" : "";
  }

  function isShoreTile(type) {
    return type !== "totally_sea" && type !== "totally_land";
  }

  function globalFromUv(map_u, map_v) {
    return { gx: map_u * GW, gy: map_v * GH };
  }

  function uvFromGlobal(gx, gy) {
    return { map_u: gx / GW, map_v: gy / GH };
  }

  function localFromGlobal(gx, gy) {
    return { lx: gx - bounds.x0, ly: gy - bounds.y0 };
  }

  function globalFromLocal(lx, ly) {
    return { gx: lx + bounds.x0, gy: ly + bounds.y0 };
  }

  function clampGlobal(gx, gy) {
    const maxX = bounds.x1 - tileSize;
    const maxY = bounds.y1 - tileSize;
    return {
      gx: Math.max(bounds.x0, Math.min(maxX, gx)),
      gy: Math.max(bounds.y0, Math.min(maxY, gy)),
    };
  }

  function areaCenterGlobal() {
    return {
      gx: (bounds.x0 + bounds.x1) / 2,
      gy: (bounds.y0 + bounds.y1) / 2,
    };
  }

  function tileCenter(t) {
    return { cx: t.x + tileSize / 2, cy: t.y + tileSize / 2 };
  }

  function nearestSnap(gx, gy, inland) {
    const pool = inland ? landTiles : shoreTiles;
    if (!pool.length) {
      return { gx, gy, tile: inland ? "totally_land" : "unknown" };
    }
    let best = pool[0];
    let bestD = Infinity;
    for (const t of pool) {
      const c = tileCenter(t);
      const d = (c.cx - gx) ** 2 + (c.cy - gy) ** 2;
      if (d < bestD) {
        bestD = d;
        best = t;
      }
    }
    const c = tileCenter(best);
    return { gx: c.cx, gy: c.cy, tile: best.tile };
  }

  function getPortPos(portId) {
    const p = portState.get(portId);
    if (!p) return null;
    if (p.map_u != null && p.map_v != null && !Number.isNaN(p.map_u)) {
      return globalFromUv(p.map_u, p.map_v);
    }
    return areaCenterGlobal();
  }

  function setPortGlobal(portId, gx, gy, tile, inland) {
    const uv = uvFromGlobal(gx, gy);
    const p = portState.get(portId);
    if (!p) return;
    p.map_u = uv.map_u;
    p.map_v = uv.map_v;
    p.snapped_tile = tile;
    if (inland !== undefined) p.inland = inland;
    dirtySession = true;
    updateMeta();
    draw();
  }

  function ensurePortInitialized(portId) {
    const p = portState.get(portId);
    if (!p) return;
    if (p.map_u == null || p.map_v == null || p.map_u < 0) {
      const c = areaCenterGlobal();
      const snap = nearestSnap(c.gx, c.gy, !!p.inland);
      setPortGlobal(portId, snap.gx, snap.gy, snap.tile, p.inland);
    }
  }

  function screenToLocal(clientX, clientY) {
    // Return local coords in CSS / global-tile units (not canvas pixels),
    // so hit-tests, dragging and localFromGlobal share the same coord space.
    // The canvas's internal bitmap is RENDER_SCALE times larger than its CSS
    // size, so we divide out that factor here.
    const rect = canvas.getBoundingClientRect();
    if (rect.width < 1 || rect.height < 1) return { lx: 0, ly: 0 };
    const w = bounds ? bounds.x1 - bounds.x0 : canvas.width / RENDER_SCALE;
    const h = bounds ? bounds.y1 - bounds.y0 : canvas.height / RENDER_SCALE;
    const lx = ((clientX - rect.left) / rect.width) * w;
    const ly = ((clientY - rect.top) / rect.height) * h;
    return { lx, ly };
  }

  function applyViewTransform() {
    canvas.style.transform = `translate(${viewPanX}px, ${viewPanY}px) scale(${viewScale})`;
  }

  function fitView() {
    const wrapW = mapWrap.clientWidth;
    const wrapH = mapWrap.clientHeight;
    const mapW = bounds.x1 - bounds.x0;
    const mapH = bounds.y1 - bounds.y0;
    canvas.style.width = mapW + "px";
    canvas.style.height = mapH + "px";
    viewScale = Math.min(wrapW / mapW, wrapH / mapH) * 0.95;
    viewPanX = (wrapW - mapW * viewScale) / 2;
    viewPanY = (wrapH - mapH * viewScale) / 2;
    applyViewTransform();
  }

  /**
   * Point-in-land test for local coords inside one cell (0..ts).
   * Matches tools/tile-factory/scripts/autotile_geometry.py land_mask().
   */
  function isLandAt(topology, lx, ly, ts) {
    if (topology === "totally_sea") return false;
    if (topology === "totally_land") return true;
    const h = ts / 2;
    const q = ts / 4;
    switch (topology) {
      case "horizontal_top_land":
        return ly < h;
      case "horizontal_bottom_land":
        return ly >= h;
      case "vertical_left_land":
        return lx < h;
      case "vertical_right_land":
        return lx >= h;
      case "vertical_channel_land":
        return lx < q || lx >= ts - q;
      case "horizontal_channel_land":
        return ly < q || ly >= ts - q;
      case "cape_north_land":
        return ly >= h;
      case "cape_south_land":
        return ly < h;
      case "cape_east_land":
        return lx < h;
      case "cape_west_land":
        return lx >= h;
      case "diagonal_descending_right_land":
        return lx + ly >= h;
      case "diagonal_rising_left_land":
        return lx + ly <= 3 * h - 2;
      case "diagonal_rising_right_land":
        return ly <= lx + h - 1;
      case "diagonal_descending_left_land":
        return ly >= lx - h + 1;
      default:
        return true;
    }
  }

  /** Vector land path (used only for coast-stroke overlay). */
  function traceLandInto(c, topology, lx, ly, ts) {
    const h = ts / 2;
    const q = ts / 4;
    switch (topology) {
      case "totally_land":
        c.rect(lx, ly, ts, ts);
        return true;
      case "horizontal_top_land":
        c.rect(lx, ly, ts, h);
        return true;
      case "horizontal_bottom_land":
        c.rect(lx, ly + h, ts, h);
        return true;
      case "vertical_left_land":
        c.rect(lx, ly, h, ts);
        return true;
      case "vertical_right_land":
        c.rect(lx + h, ly, h, ts);
        return true;
      case "vertical_channel_land":
        c.rect(lx, ly, q, ts);
        c.rect(lx + ts - q, ly, q, ts);
        return true;
      case "horizontal_channel_land":
        c.rect(lx, ly, ts, q);
        c.rect(lx, ly + ts - q, ts, q);
        return true;
      case "cape_north_land":
        c.rect(lx, ly + h, ts, h);
        return true;
      case "cape_south_land":
        c.rect(lx, ly, ts, h);
        return true;
      case "cape_east_land":
        c.rect(lx, ly, h, ts);
        return true;
      case "cape_west_land":
        c.rect(lx + h, ly, h, ts);
        return true;
      case "diagonal_descending_right_land":
        c.moveTo(lx + h, ly);
        c.lineTo(lx + ts, ly);
        c.lineTo(lx + ts, ly + ts);
        c.lineTo(lx, ly + ts);
        c.lineTo(lx, ly + h);
        c.closePath();
        return true;
      case "diagonal_rising_left_land": {
        const lim = 3 * h - 2;
        if (lim >= ts) {
          c.rect(lx, ly, ts, ts);
          return true;
        }
        c.moveTo(lx, ly);
        c.lineTo(lx + Math.min(ts, lim), ly);
        c.lineTo(lx, ly + Math.min(ts, lim));
        c.lineTo(lx, ly + ts);
        c.lineTo(lx + ts, ly + ts);
        c.lineTo(lx + ts, ly);
        c.closePath();
        return true;
      }
      case "diagonal_rising_right_land": {
        const y0 = h - 1;
        c.moveTo(lx, ly);
        c.lineTo(lx + ts, ly);
        c.lineTo(lx + ts, ly + ts);
        c.lineTo(lx, ly + Math.max(0, y0));
        c.closePath();
        return true;
      }
      case "diagonal_descending_left_land": {
        const x0 = Math.max(0, h - 1);
        c.moveTo(lx, ly);
        c.lineTo(lx + x0, ly);
        c.lineTo(lx + ts, ly);
        c.lineTo(lx + ts, ly + ts);
        c.lineTo(lx, ly + ts);
        c.closePath();
        return true;
      }
      default:
        c.rect(lx, ly, ts, ts);
        return true;
    }
  }

  /** Coast line for shore tiles (optional tan overlay). */
  function traceCoastEdge(topology, lx, ly, ts) {
    const h = ts / 2;
    const q = ts / 4;
    switch (topology) {
      case "horizontal_top_land":
      case "horizontal_bottom_land":
        ctx.moveTo(lx, ly + h);
        ctx.lineTo(lx + ts, ly + h);
        return true;
      case "vertical_left_land":
      case "vertical_right_land":
        ctx.moveTo(lx + h, ly);
        ctx.lineTo(lx + h, ly + ts);
        return true;
      case "diagonal_rising_left_land":
        ctx.moveTo(lx + Math.min(ts, 3 * h - 2), ly);
        ctx.lineTo(lx, ly + Math.min(ts, 3 * h - 2));
        return true;
      case "diagonal_rising_right_land":
        ctx.moveTo(lx, ly + Math.max(0, h - 1));
        ctx.lineTo(lx + ts, ly + Math.min(ts, ts + h - 1));
        return true;
      case "diagonal_descending_left_land":
        ctx.moveTo(lx + Math.max(0, h - 1), ly);
        ctx.lineTo(lx + ts, ly + Math.min(ts, ts - h + 1));
        return true;
      case "diagonal_descending_right_land":
        ctx.moveTo(lx + h, ly);
        ctx.lineTo(lx, ly + h);
        return true;
      case "cape_north_land":
        ctx.moveTo(lx, ly + h);
        ctx.lineTo(lx + ts, ly + h);
        return true;
      case "cape_south_land":
        ctx.moveTo(lx, ly + h);
        ctx.lineTo(lx + ts, ly + h);
        return true;
      case "cape_east_land":
        ctx.moveTo(lx + h, ly);
        ctx.lineTo(lx + h, ly + ts);
        return true;
      case "cape_west_land":
        ctx.moveTo(lx + h, ly);
        ctx.lineTo(lx + h, ly + ts);
        return true;
      case "horizontal_channel_land":
        ctx.moveTo(lx, ly + q);
        ctx.lineTo(lx + ts, ly + q);
        ctx.moveTo(lx, ly + ts - q);
        ctx.lineTo(lx + ts, ly + ts - q);
        return true;
      case "vertical_channel_land":
        ctx.moveTo(lx + q, ly);
        ctx.lineTo(lx + q, ly + ts);
        ctx.moveTo(lx + ts - q, ly);
        ctx.lineTo(lx + ts - q, ly + ts);
        return true;
      default:
        return false;
    }
  }

  /**
   * Rasterize tilemap into ImageData at RENDER_SCALE using isLandAt() per pixel.
   * Avoids vector gaps between adjacent shore cells (blue corner triangles).
   */
  function buildTilemapCache() {
    const w = bounds.x1 - bounds.x0;
    const h = bounds.y1 - bounds.y0;
    const pw = w * RENDER_SCALE;
    const ph = h * RENDER_SCALE;
    const cache = document.createElement("canvas");
    cache.width = pw;
    cache.height = ph;
    const tctx = cache.getContext("2d");
    tctx.imageSmoothingEnabled = false;

    const img = tctx.createImageData(pw, ph);
    const data = img.data;
    const [sr, sg, sb, sa] = SEA_RGBA;
    const [lr, lg, lb, la] = LAND_RGBA;
    for (let i = 0; i < data.length; i += 4) {
      data[i] = sr;
      data[i + 1] = sg;
      data[i + 2] = sb;
      data[i + 3] = sa;
    }

    const tiles = window._areaTiles || [];
    const ts = tileSize;
    const ps = Math.max(1, Math.round(ts * RENDER_SCALE));

    for (const t of tiles) {
      if (t.tile === "totally_sea") continue;
      const baseLx = t.x - bounds.x0;
      const baseLy = t.y - bounds.y0;
      const px0 = Math.round(baseLx * RENDER_SCALE);
      const py0 = Math.round(baseLy * RENDER_SCALE);

      if (t.tile === "totally_land") {
        for (let sy = 0; sy < ps; sy++) {
          const row = (py0 + sy) * pw;
          for (let sx = 0; sx < ps; sx++) {
            const i = (row + px0 + sx) * 4;
            data[i] = lr;
            data[i + 1] = lg;
            data[i + 2] = lb;
            data[i + 3] = la;
          }
        }
        continue;
      }

      for (let sy = 0; sy < ps; sy++) {
        const ly = (sy + 0.5) / RENDER_SCALE;
        const row = (py0 + sy) * pw;
        for (let sx = 0; sx < ps; sx++) {
          const lx = (sx + 0.5) / RENDER_SCALE;
          if (!isLandAt(t.tile, lx, ly, ts)) continue;
          const i = (row + px0 + sx) * 4;
          data[i] = lr;
          data[i + 1] = lg;
          data[i + 2] = lb;
          data[i + 3] = la;
        }
      }
    }

    tctx.putImageData(img, 0, 0);
    tilemapCache = cache;

    // Match the visible canvas to the cache once per area load. Setting
    // canvas.width/height resets context state, so doing it here (rather than
    // every drawTilemap) keeps drag/zoom redraws cheap.
    canvas.width = cache.width;
    canvas.height = cache.height;
    canvas.style.width = w + "px";
    canvas.style.height = h + "px";
    ctx.imageSmoothingEnabled = false;
  }

  function drawTilemap() {
    if (!tilemapCache) return;
    const w = bounds.x1 - bounds.x0;
    const h = bounds.y1 - bounds.y0;

    // Blit the cached fills over the whole canvas, then overlay the
    // viewScale-dependent coast stroke. drawImage covers everything so no
    // explicit clear is needed.
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.drawImage(tilemapCache, 0, 0);
    ctx.setTransform(RENDER_SCALE, 0, 0, RENDER_SCALE, 0, 0);

    const tiles = window._areaTiles || [];
    const s = viewScale > 0 ? viewScale : 1;
    ctx.strokeStyle = COAST_COLOR;
    // Constant ~1 screen-pixel stroke at any zoom. Floor avoids vanishing at
    // extreme zoom-in where 1/s rounds toward zero.
    ctx.lineWidth = Math.max(0.05, 1 / s);
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.beginPath();
    let anyEdge = false;
    for (const t of tiles) {
      if (t.tile === "totally_sea" || t.tile === "totally_land") continue;
      const lx = t.x - bounds.x0;
      const ly = t.y - bounds.y0;
      if (lx < -tileSize || ly < -tileSize || lx > w || ly > h) continue;
      if (traceCoastEdge(t.tile, lx, ly, tileSize)) anyEdge = true;
    }
    if (anyEdge) ctx.stroke();
  }

  function drawMarkers() {
    // Compensate for the CSS scale on the canvas so markers stay the same
    // pixel size on screen regardless of zoom level.
    const s = viewScale > 0 ? viewScale : 1;
    const r = 10 / s;
    const stroke = 2 / s;
    const labelOffset = 4 / s;
    const fontPx = 11 / s;
    for (const p of areaPorts) {
      const pos = getPortPos(p.id);
      if (!pos) continue;
      const { lx, ly } = localFromGlobal(pos.gx, pos.gy);
      const selected = p.id === selectedPortId;
      ctx.beginPath();
      ctx.arc(lx, ly, r, 0, Math.PI * 2);
      ctx.fillStyle = selected ? "#ff6b4a" : "#f0c040";
      ctx.fill();
      ctx.strokeStyle = "#1a1008";
      ctx.lineWidth = stroke;
      ctx.stroke();
      if (selected) {
        ctx.fillStyle = "#fff";
        ctx.font = `${fontPx}px system-ui,sans-serif`;
        ctx.fillText(p.name, lx + r + labelOffset, ly + labelOffset);
      }
    }
  }

  function draw() {
    if (!bounds) return;
    drawTilemap();
    drawMarkers();
    const p = portState.get(selectedPortId);
    if (p && p.map_u != null) {
      const { gx, gy } = globalFromUv(p.map_u, p.map_v);
      coordsText.textContent = `map_u=${p.map_u.toFixed(6)} map_v=${p.map_v.toFixed(6)} · global (${gx.toFixed(1)}, ${gy.toFixed(1)}) · tile ${p.snapped_tile || "—"}`;
    } else {
      coordsText.textContent = "";
    }
  }

  function updateMeta() {
    const p = portState.get(selectedPortId);
    if (!p) {
      portMeta.textContent = "Select a port.";
      return;
    }
    const { gx, gy } = getPortPos(selectedPortId) || { gx: 0, gy: 0 };
    portMeta.innerHTML =
      `<strong>${p.name}</strong> (${p.id})<br>` +
      `chart_area_id: ${p.chart_area_id}<br>` +
      `map_u: ${p.map_u != null ? p.map_u.toFixed(6) : "—"}<br>` +
      `map_v: ${p.map_v != null ? p.map_v.toFixed(6) : "—"}<br>` +
      `global: (${gx.toFixed(1)}, ${gy.toFixed(1)})`;
    inlandCb.checked = !!p.inland;
  }

  function renderPortList() {
    portList.innerHTML = "";
    portSelect.innerHTML = '<option value="">— choose port —</option>';
    const sorted = [...areaPorts].sort((a, b) => a.name.localeCompare(b.name));
    for (const p of sorted) {
      const opt = document.createElement("option");
      opt.value = p.id;
      opt.textContent = `${p.name} (${p.id})`;
      portSelect.appendChild(opt);

      const li = document.createElement("li");
      li.dataset.id = p.id;
      if (p.id === selectedPortId) li.classList.add("selected");
      const st = portState.get(p.id);
      const uv =
        st && st.map_u != null
          ? `${st.map_u.toFixed(3)}, ${st.map_v.toFixed(3)}`
          : "no coords → center on select";
      li.innerHTML = `<div>${p.name}</div><div class="sub">${p.id} · ${uv}</div>`;
      li.addEventListener("click", () => selectPort(p.id));
      portList.appendChild(li);
    }
    portSelect.disabled = sorted.length === 0;
    centerBtn.disabled = !selectedPortId;
    inlandCb.disabled = !selectedPortId;
    exportBtn.disabled = areaPorts.length === 0;
  }

  function selectPort(portId) {
    if (!areaPorts.some((p) => p.id === portId)) return;
    selectedPortId = portId;
    ensurePortInitialized(portId);
    portSelect.value = portId;
    renderPortList();
    updateMeta();
    draw();
    mapOverlay.textContent = `Editing: ${portState.get(portId)?.name || portId}`;
  }

  async function loadArea(id) {
    areaId = id;
    selectedPortId = "";
    setStatus(`Loading tilemap ${id}…`);
    mapOverlay.textContent = "Loading tilemap…";
    exportBtn.disabled = true;

    const res = await fetch(`/api/tilemap/${encodeURIComponent(id)}`);
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();

    const ca = data.chart_area || {};
    bounds = ca.bounds || chartAreas.find((a) => a.id === id)?.bounds;
    if (!bounds) throw new Error("missing bounds");

    tileSize = data.coordinate_system?.final_tile_size || 3;
    const tiles = data.tiles || [];
    window._areaTiles = tiles;

    shoreTiles = [];
    landTiles = [];
    for (const t of tiles) {
      if (t.tile === "totally_land") landTiles.push(t);
      else if (isShoreTile(t.tile)) shoreTiles.push(t);
    }

    buildTilemapCache();

    areaPorts = allPorts.filter((p) => p.chart_area_id === id);
    for (const p of areaPorts) {
      if (!portState.has(p.id)) {
        portState.set(p.id, {
          id: p.id,
          name: p.name,
          chart_area_id: p.chart_area_id,
          map_u: p.map_u,
          map_v: p.map_v,
          inland: false,
        });
      }
    }

    fitView();
    renderPortList();
    draw();
    exportBtn.disabled = areaPorts.length === 0;
    const src = data._source_file ? ` · ${data._source_file}` : "";
    setStatus(
      `${ca.name || id}: ${tiles.length} tiles, ${shoreTiles.length} shore snap targets, ${areaPorts.length} ports${src}`,
    );
    mapOverlay.textContent = "Left-drag map to pan · drag a marker to move port · wheel to zoom";
  }

  function hitTestPort(lx, ly) {
    // Match the on-screen marker size: drawn radius is 10/viewScale in canvas
    // space, so the hit radius scales the same way (with a small pad).
    const s = viewScale > 0 ? viewScale : 1;
    const hitR = 14 / s;
    for (const p of areaPorts) {
      const pos = getPortPos(p.id);
      if (!pos) continue;
      const loc = localFromGlobal(pos.gx, pos.gy);
      const d = Math.hypot(loc.lx - lx, loc.ly - ly);
      if (d <= hitR) return p.id;
    }
    return null;
  }

  canvas.addEventListener("pointerdown", (e) => {
    if (!bounds) return;
    const { lx, ly } = screenToLocal(e.clientX, e.clientY);
    lastPointerX = e.clientX;
    lastPointerY = e.clientY;

    // Explicit pan modifiers: right-click, middle-click, or Alt+left.
    // These pan even when the click lands on a port marker.
    if (e.button === 1 || e.button === 2 || (e.button === 0 && e.altKey)) {
      // Middle-click would otherwise open the Windows autoscroll cursor.
      e.preventDefault();
      panning = true;
      canvas.classList.add("panning");
      canvas.setPointerCapture(e.pointerId);
      return;
    }

    if (e.button !== 0) return;

    // Plain left-click: drag a marker if we hit one, otherwise pan the map.
    // Selecting a port is no longer required to pan, so freshly-zoomed views
    // can be navigated immediately.
    const hit = hitTestPort(lx, ly);
    if (hit) {
      selectPort(hit);
      draggingPort = true;
      const pos = getPortPos(hit);
      const loc = localFromGlobal(pos.gx, pos.gy);
      dragOffsetX = lx - loc.lx;
      dragOffsetY = ly - loc.ly;
      canvas.classList.add("dragging-port");
      canvas.setPointerCapture(e.pointerId);
    } else {
      panning = true;
      canvas.classList.add("panning");
      canvas.setPointerCapture(e.pointerId);
    }
  });

  canvas.addEventListener("pointermove", (e) => {
    if (panning) {
      viewPanX += e.clientX - lastPointerX;
      viewPanY += e.clientY - lastPointerY;
      applyViewTransform();
      lastPointerX = e.clientX;
      lastPointerY = e.clientY;
      return;
    }
    if (!draggingPort || !selectedPortId) return;
    const { lx, ly } = screenToLocal(e.clientX, e.clientY);
    let { gx, gy } = globalFromLocal(lx - dragOffsetX, ly - dragOffsetY);
    ({ gx, gy } = clampGlobal(gx, gy));
    const p = portState.get(selectedPortId);
    const uv = uvFromGlobal(gx, gy);
    p.map_u = uv.map_u;
    p.map_v = uv.map_v;
    dirtySession = true;
    draw();
    updateMeta();
  });

  canvas.addEventListener("pointerup", (e) => {
    if (draggingPort && selectedPortId) {
      const p = portState.get(selectedPortId);
      const { gx, gy } = globalFromUv(p.map_u, p.map_v);
      const snap = nearestSnap(gx, gy, !!p.inland);
      setPortGlobal(selectedPortId, snap.gx, snap.gy, snap.tile, p.inland);
      renderPortList();
    }
    draggingPort = false;
    panning = false;
    canvas.classList.remove("dragging-port", "panning");
    try {
      canvas.releasePointerCapture(e.pointerId);
    } catch (_) {}
  });

  canvas.addEventListener("wheel", (e) => {
    e.preventDefault();
    const factor = e.deltaY > 0 ? 1 / WHEEL_ZOOM_FACTOR : WHEEL_ZOOM_FACTOR;
    const wrapRect = mapWrap.getBoundingClientRect();
    const mx = e.clientX - wrapRect.left;
    const my = e.clientY - wrapRect.top;
    viewPanX = mx - (mx - viewPanX) * factor;
    viewPanY = my - (my - viewPanY) * factor;
    viewScale = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, viewScale * factor));
    applyViewTransform();
    // Marker size compensates for viewScale, so redraw after zooming.
    draw();
  }, { passive: false });

  canvas.addEventListener("contextmenu", (e) => e.preventDefault());

  areaSelect.addEventListener("change", async () => {
    const id = areaSelect.value;
    if (!id) return;
    try {
      await loadArea(id);
    } catch (err) {
      setStatus(String(err), true);
    }
  });

  portSelect.addEventListener("change", () => {
    if (portSelect.value) selectPort(portSelect.value);
  });

  inlandCb.addEventListener("change", () => {
    const p = portState.get(selectedPortId);
    if (!p) return;
    p.inland = inlandCb.checked;
    const { gx, gy } = globalFromUv(p.map_u, p.map_v);
    const snap = nearestSnap(gx, gy, p.inland);
    setPortGlobal(selectedPortId, snap.gx, snap.gy, snap.tile, p.inland);
    renderPortList();
  });

  centerBtn.addEventListener("click", () => {
    if (!selectedPortId) return;
    const c = areaCenterGlobal();
    const p = portState.get(selectedPortId);
    const snap = nearestSnap(c.gx, c.gy, !!p.inland);
    setPortGlobal(selectedPortId, snap.gx, snap.gy, snap.tile, p.inland);
    renderPortList();
  });

  exportBtn.addEventListener("click", async () => {
    const edits = [];
    for (const st of portState.values()) {
      if (!st || st.map_u == null || st.map_v == null) continue;
      const { gx, gy } = globalFromUv(st.map_u, st.map_v);
      edits.push({
        id: st.id,
        name: st.name,
        chart_area_id: st.chart_area_id,
        map_u: st.map_u,
        map_v: st.map_v,
        global_x: Math.round(gx),
        global_y: Math.round(gy),
        snapped_tile: st.snapped_tile || null,
        inland_exception: !!st.inland,
      });
    }
    edits.sort((a, b) => a.id.localeCompare(b.id));

    setStatus("Saving…");
    const res = await fetch("/api/export", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ edits }),
    });
    const out = await res.json();
    if (!res.ok) {
      setStatus(out.error || "Save failed", true);
      return;
    }
    setStatus(`Saved ${out.count} ports → ${out.path}`, false);
    statusText.classList.add("ok");
  });

  window.addEventListener("resize", () => {
    if (!bounds) return;
    fitView();
    // Coast stroke width tracks viewScale, which changes on resize.
    draw();
  });

  async function init() {
    try {
      const res = await fetch("/api/bootstrap");
      const data = await res.json();
      chartAreas = data.chart_areas || [];
      allPorts = data.ports || [];
      for (const p of allPorts) {
        portState.set(p.id, {
          id: p.id,
          name: p.name,
          chart_area_id: p.chart_area_id,
          map_u: p.map_u,
          map_v: p.map_v,
          inland: false,
        });
      }
      areaSelect.innerHTML = '<option value="">— select chart area —</option>';
      for (const a of chartAreas) {
        const opt = document.createElement("option");
        opt.value = a.id;
        opt.textContent = a.name || a.id;
        areaSelect.appendChild(opt);
      }
      const src = data.source || "world_full.json";
      let msg = `Loaded ${allPorts.length} ports from ${src}.`;
      if (data.export_exists && !data.merge_export_on_load) {
        msg += ` (${data.export_path} ignored — apply with apply_port_map_export.py, then archive/delete export.)`;
      }
      setStatus(msg);
      mapOverlay.textContent = "Select a chart area";
    } catch (err) {
      setStatus(String(err), true);
    }
  }

  init();
})();

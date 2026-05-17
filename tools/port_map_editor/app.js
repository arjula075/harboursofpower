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

  /** Wheel zoom per tick (~4%; previously 10% with 1.1 / 0.9). */
  const WHEEL_ZOOM_FACTOR = 1.04;

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
    const rect = canvas.getBoundingClientRect();
    if (rect.width < 1 || rect.height < 1) return { lx: 0, ly: 0 };
    const lx = ((clientX - rect.left) / rect.width) * canvas.width;
    const ly = ((clientY - rect.top) / rect.height) * canvas.height;
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

  function drawTilemap() {
    const w = bounds.x1 - bounds.x0;
    const h = bounds.y1 - bounds.y0;
    canvas.width = w;
    canvas.height = h;
    ctx.fillStyle = "#0a0e12";
    ctx.fillRect(0, 0, w, h);

    const tiles = window._areaTiles || [];
    for (const t of tiles) {
      const lx = t.x - bounds.x0;
      const ly = t.y - bounds.y0;
      if (lx < -tileSize || ly < -tileSize || lx > w || ly > h) continue;
      let col = COAST_COLOR;
      if (t.tile === "totally_sea") col = TILE_COLORS.totally_sea;
      else if (t.tile === "totally_land") col = TILE_COLORS.totally_land;
      ctx.fillStyle = col;
      ctx.fillRect(lx, ly, tileSize, tileSize);
    }
  }

  function drawMarkers() {
    const r = 10;
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
      ctx.lineWidth = 2;
      ctx.stroke();
      if (selected) {
        ctx.fillStyle = "#fff";
        ctx.font = "11px system-ui,sans-serif";
        ctx.fillText(p.name, lx + r + 4, ly + 4);
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
    setStatus(
      `${ca.name || id}: ${tiles.length} tiles, ${shoreTiles.length} shore snap targets, ${areaPorts.length} ports`,
    );
    mapOverlay.textContent = "Drag port · wheel zoom · right-drag pan";
  }

  function hitTestPort(lx, ly) {
    const hitR = 14;
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

    if (e.button === 2 || (e.button === 0 && e.altKey)) {
      panning = true;
      canvas.classList.add("panning");
      canvas.setPointerCapture(e.pointerId);
      return;
    }

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
    } else if (selectedPortId) {
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
    viewScale = Math.max(0.15, Math.min(12, viewScale * factor));
    applyViewTransform();
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
    if (bounds) fitView();
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

/**
 * Port map editor — Wang-16 · 1px chart-area tilemaps.
 * Basemap from pre-rendered PNG; snap via server spatial index.
 */
(function () {
  const GW = 2000;
  const GH = 1000;

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
  /** @type {Map<string, {id, name, chart_area_id, map_u, map_v, inland?: boolean, snapped_tile?: string}>} */
  const portState = new Map();

  let areaId = "";
  let bounds = null;
  let tileSize = 1;
  let mapImage = null;
  let areaPorts = [];
  let selectedPortId = "";
  let shoreSnapCount = 0;

  let viewScale = 1;
  let viewPanX = 0;
  let viewPanY = 0;

  let draggingPort = false;
  let panning = false;
  let dragOffsetX = 0;
  let dragOffsetY = 0;
  let lastPointerX = 0;
  let lastPointerY = 0;

  function setStatus(msg, isErr) {
    statusText.textContent = msg;
    statusText.className = isErr ? "err" : "";
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
    const maxX = bounds.x1 - tileSize * 0.5;
    const maxY = bounds.y1 - tileSize * 0.5;
    return {
      gx: Math.max(bounds.x0 + tileSize * 0.5, Math.min(maxX, gx)),
      gy: Math.max(bounds.y0 + tileSize * 0.5, Math.min(maxY, gy)),
    };
  }

  function areaCenterGlobal() {
    return {
      gx: (bounds.x0 + bounds.x1) / 2,
      gy: (bounds.y0 + bounds.y1) / 2,
    };
  }

  function getPortPos(portId) {
    const p = portState.get(portId);
    if (!p) return null;
    if (p.map_u != null && p.map_v != null && !Number.isNaN(p.map_u)) {
      return globalFromUv(p.map_u, p.map_v);
    }
    return areaCenterGlobal();
  }

  async function snapGlobal(gx, gy, inland) {
    const res = await fetch("/api/snap", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ area_id: areaId, gx, gy, inland }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "snap failed");
    return { gx: data.gx, gy: data.gy, tile: data.tile };
  }

  async function setPortGlobal(portId, gx, gy, tile, inland) {
    const uv = uvFromGlobal(gx, gy);
    const p = portState.get(portId);
    if (!p) return;
    p.map_u = uv.map_u;
    p.map_v = uv.map_v;
    p.snapped_tile = tile;
    if (inland !== undefined) p.inland = inland;
    updateMeta();
    draw();
  }

  async function snapAndSetPort(portId, gx, gy, inland) {
    const snap = await snapGlobal(gx, gy, inland);
    await setPortGlobal(portId, snap.gx, snap.gy, snap.tile, inland);
    return snap;
  }

  async function ensurePortInitialized(portId) {
    const p = portState.get(portId);
    if (!p) return;
    if (p.map_u == null || p.map_v == null || p.map_u < 0) {
      const c = areaCenterGlobal();
      await snapAndSetPort(portId, c.gx, c.gy, !!p.inland);
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

  function drawBasemap() {
    const w = bounds.x1 - bounds.x0;
    const h = bounds.y1 - bounds.y0;
    canvas.width = w;
    canvas.height = h;
    ctx.fillStyle = "#0a0e12";
    ctx.fillRect(0, 0, w, h);
    if (mapImage && mapImage.complete) {
      ctx.drawImage(mapImage, 0, 0, w, h);
    }
  }

  function drawMarkers() {
    const r = 8;
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
    drawBasemap();
    drawMarkers();
    const p = portState.get(selectedPortId);
    if (p && p.map_u != null) {
      const { gx, gy } = globalFromUv(p.map_u, p.map_v);
      const tile = p.snapped_tile || "—";
      const shortTile = tile.length > 48 ? tile.slice(0, 45) + "…" : tile;
      coordsText.textContent =
        `map_u=${p.map_u.toFixed(6)} map_v=${p.map_v.toFixed(6)} · global (${gx.toFixed(1)}, ${gy.toFixed(1)}) · ${shortTile}`;
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
      `global: (${gx.toFixed(1)}, ${gy.toFixed(1)})<br>` +
      `tile: ${p.snapped_tile || "—"}`;
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

  async function selectPort(portId) {
    if (!areaPorts.some((p) => p.id === portId)) return;
    selectedPortId = portId;
    await ensurePortInitialized(portId);
    portSelect.value = portId;
    renderPortList();
    updateMeta();
    draw();
    mapOverlay.textContent = `Editing: ${portState.get(portId)?.name || portId}`;
  }

  function loadMapImage(url) {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = () => reject(new Error("map image failed to load"));
      img.src = url;
    });
  }

  async function loadArea(id) {
    areaId = id;
    selectedPortId = "";
    mapImage = null;
    setStatus(`Loading ${id}…`);
    mapOverlay.textContent = "Loading tilemap…";
    exportBtn.disabled = true;

    const res = await fetch(`/api/tilemap/${encodeURIComponent(id)}`);
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();

    bounds = data.bounds || chartAreas.find((a) => a.id === id)?.bounds;
    if (!bounds) throw new Error("missing bounds");

    tileSize = data.coordinate_system?.final_tile_size || 1;
    shoreSnapCount = data.shore_snap_targets || 0;

    mapOverlay.textContent = "Loading map image…";
    const mapUrl =
      data.map_image_url ||
      `/api/map-image/${encodeURIComponent(id)}?v=${data.mask_version || Date.now()}`;
    mapImage = await loadMapImage(mapUrl);

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
    const areaName = chartAreas.find((a) => a.id === id)?.name || id;
    setStatus(
      `${areaName}: ${shoreSnapCount.toLocaleString()} shore snap targets · ${areaPorts.length} ports · 1px wang16`,
    );
    mapOverlay.textContent = "Drag port · wheel zoom · right-drag pan";
  }

  function hitTestPort(lx, ly) {
    const hitR = 12;
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
    draw();
    updateMeta();
  });

  canvas.addEventListener("pointerup", async (e) => {
    if (draggingPort && selectedPortId) {
      const p = portState.get(selectedPortId);
      const { gx, gy } = globalFromUv(p.map_u, p.map_v);
      try {
        await snapAndSetPort(selectedPortId, gx, gy, !!p.inland);
        renderPortList();
      } catch (err) {
        setStatus(String(err), true);
      }
    }
    draggingPort = false;
    panning = false;
    canvas.classList.remove("dragging-port", "panning");
    try {
      canvas.releasePointerCapture(e.pointerId);
    } catch (_) {}
  });

  canvas.addEventListener(
    "wheel",
    (e) => {
      e.preventDefault();
      const factor = e.deltaY > 0 ? 1 / WHEEL_ZOOM_FACTOR : WHEEL_ZOOM_FACTOR;
      const wrapRect = mapWrap.getBoundingClientRect();
      const mx = e.clientX - wrapRect.left;
      const my = e.clientY - wrapRect.top;
      viewPanX = mx - (mx - viewPanX) * factor;
      viewPanY = my - (my - viewPanY) * factor;
      viewScale = Math.max(0.15, Math.min(24, viewScale * factor));
      applyViewTransform();
    },
    { passive: false },
  );

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

  inlandCb.addEventListener("change", async () => {
    const p = portState.get(selectedPortId);
    if (!p) return;
    p.inland = inlandCb.checked;
    const { gx, gy } = globalFromUv(p.map_u, p.map_v);
    try {
      await snapAndSetPort(selectedPortId, gx, gy, p.inland);
      renderPortList();
    } catch (err) {
      setStatus(String(err), true);
    }
  });

  centerBtn.addEventListener("click", async () => {
    if (!selectedPortId) return;
    const c = areaCenterGlobal();
    const p = portState.get(selectedPortId);
    try {
      await snapAndSetPort(selectedPortId, c.gx, c.gy, !!p.inland);
      renderPortList();
    } catch (err) {
      setStatus(String(err), true);
    }
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
      let msg = `Loaded ${allPorts.length} ports from ${src} (wang16 1px).`;
      if (data.export_exists && !data.merge_export_on_load) {
        msg += ` (${data.export_path} ignored — apply with apply_port_map_wang16_1px_export.py)`;
      }
      const stamp = $("build-stamp");
      if (stamp) {
        stamp.textContent = `Basemap mask v${data.mask_version || "?"} · ${data.mask_path || ""}`;
      }
      setStatus(msg);
      mapOverlay.textContent = "Select a chart area";
    } catch (err) {
      setStatus(String(err), true);
    }
  }

  init();
})();

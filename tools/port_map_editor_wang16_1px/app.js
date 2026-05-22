/**
 * Port map editor — Wang-16 · 1px chart-area tilemaps.
 * Basemap from pre-rendered PNG; snap via server spatial index.
 */
(function () {
  const EDITOR_BUILD = "terrain-feedback-5";
  const GW = 2000;
  const GH = 1000;

  const WHEEL_ZOOM_FACTOR = 1.04;
  /** Target on-screen marker radius (px); canvas radius divides by viewScale. */
  const MARKER_SCREEN_RADIUS = 10;
  const MARKER_HIT_PAD = 4;

  const $ = (id) => document.getElementById(id);
  const areaSelect = $("area-select");
  const portSelect = $("port-select");
  const portList = $("port-list");
  const portMeta = $("port-meta");
  const inlandCb = $("inland-exception");
  const centerBtn = $("center-port");
  const exportBtn = $("export-btn");
  const portsToolPanel = $("ports-tool-panel");
  const terrainPanel = $("terrain-panel");
  const terrainDryRunBtn = $("terrain-dry-run-btn");
  const terrainSaveBtn = $("terrain-save-btn");
  const terrainDiscardBtn = $("terrain-discard-btn");
  const terrainFeedback = $("terrain-feedback");
  const terrainFeedbackTitle = $("terrain-feedback-title");
  const terrainFeedbackBody = $("terrain-feedback-body");
  const terrainFeedbackDismiss = $("terrain-feedback-dismiss");
  const terrainReportDetails = $("terrain-report-details");
  const terrainReport = $("terrain-report");
  const terrainDiskStatus = $("terrain-disk-status");
  const canvas = $("map-canvas");
  const ctx = canvas.getContext("2d");
  const mapWrap = $("map-wrap");
  const mapOverlay = $("map-overlay");
  const statusText = $("status-text");
  const coordsText = $("coords-text");

  let toolMode = "ports";
  let terrainBrush = "land";
  let computing = false;
  let terrainPreviewImage = null;
  let terrainPreviewVersion = 0;
  let terrainDirty = false;
  let terrainBoundaryWarning = "";

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

  function setComputing(on, label) {
    computing = on;
    const app = $("app");
    if (app) app.classList.toggle("computing", on);
    if (mapWrap) mapWrap.classList.toggle("computing", on);
    const overlay = $("computing-overlay");
    if (overlay) overlay.textContent = label || "Recomputing chart area…";
    updateToolUi();
  }

  function updateToolUi() {
    const isTerrain = toolMode === "terrain";
    if (terrainPanel) terrainPanel.classList.toggle("hidden", !isTerrain);
    if (portsToolPanel) portsToolPanel.classList.toggle("hidden", isTerrain);
    if (canvas) canvas.classList.toggle("terrain-mode", isTerrain);

    const hasArea = !!areaId;
    const busy = computing;
    // Do not use HTML disabled — it blocks click events entirely (including delegation).
    if (terrainDryRunBtn) {
      terrainDryRunBtn.classList.toggle("btn-inactive", !hasArea || busy);
      terrainDryRunBtn.title = hasArea
        ? "Preview save without writing files"
        : "Select a chart area first";
    }
    if (terrainSaveBtn) {
      terrainSaveBtn.classList.toggle("btn-inactive", !hasArea || busy);
      terrainSaveBtn.classList.toggle("btn-needs-paint", hasArea && !terrainDirty && !busy);
      terrainSaveBtn.title = !terrainDirty
        ? "Paint at least one land/sea cell first"
        : "Write full tilemap + mask to disk";
    }
    if (terrainDiscardBtn) {
      terrainDiscardBtn.classList.toggle("btn-inactive", !hasArea || busy);
      terrainDiscardBtn.classList.toggle("btn-needs-paint", hasArea && !terrainDirty && !busy);
      terrainDiscardBtn.title = !terrainDirty ? "No unsaved terrain edits" : "Revert session to disk";
    }
  }

  function getTerrainBrush() {
    const el = document.querySelector('input[name="terrain-brush"]:checked');
    return el ? el.value : "land";
  }

  async function loadTerrainPreview() {
    if (!areaId) return;
    const url = `/api/terrain/preview/${encodeURIComponent(areaId)}?v=${terrainPreviewVersion}`;
    terrainPreviewImage = await loadMapImage(url);
  }

  async function initTerrainSession() {
    if (!areaId) return;
    const res = await fetch("/api/terrain/session", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ area_id: areaId }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "terrain session failed");
    terrainDirty = !!data.dirty;
    terrainPreviewVersion = data.preview_version || 0;
    terrainBoundaryWarning = "";
    if (data.cross_area_ripple) {
      const areas = (data.overlapping_chart_areas || []).join(", ");
      terrainBoundaryWarning = `Boundary changed (${data.boundary_corners_changed} corners). Overlapping areas: ${areas || "—"}`;
    }
    await loadTerrainPreview();
  }

  function formatTerrainFeedback(out) {
    if (out.no_edits) {
      return {
        tone: "warn",
        title: "Nothing to save",
        html:
          `<p>${out.message || "No unsaved terrain edits in this server session."}</p>` +
          `<p>Paint at least one cell, then dry-run or save again.</p>`,
      };
    }
    if (out.dry_run) {
      const areas = (out.applied_chart_areas || out.dirty_chart_areas || []).join(", ") || "—";
      const warns = out.overlap_warnings || [];
      let warnHtml = "";
      if (warns.length) {
        warnHtml =
          "<p><strong>Boundary ripple</strong> (may affect overlapping areas on real save):</p><ul>" +
          warns
            .map(
              (w) =>
                `<li>${w.area_id}: ${w.boundary_corners_changed} corners → ${(w.overlapping_chart_areas || []).join(", ")}</li>`,
            )
            .join("") +
          "</ul>";
      }
      return {
        tone: "dry-run",
        title: "Dry-run complete — disk unchanged",
        html:
          `<p>${out.message || ""}</p>` +
          `<ul><li>Chart areas: <code>${areas}</code></li>` +
          `<li>Ports that would resnap: <b>${out.ports_resnapped ?? 0}</b></li></ul>` +
          warnHtml +
          `<p>Click <b>Save terrain</b> to write files.</p>`,
      };
    }
    if (out.written_to_disk) {
      const v = out.verification || {};
      const base = out.base_data || {};
      let baseList = "";
      if (base.mask_png) {
        baseList =
          "<p><strong>Base data updated</strong> (editor, routes map, Godot chunk map):</p><ul>" +
          `<li>Mask: <code>${base.mask_png}</code></li>` +
          (base.chunk_manifest ? `<li>Chunks: <code>${base.chunk_webps || "?"}</code> + manifest</li>` : "") +
          (base.chart_area_tilemaps ? `<li>Chart areas: <code>${base.chart_area_tilemaps}/*</code></li>` : "") +
          "</ul>";
      }
      return {
        tone: "saved",
        title: "Saved to disk",
        html:
          `<p>${out.message || "Terrain save completed."}</p>` +
          baseList +
          `<ul>` +
          `<li>Saved at: <code>${out.saved_at || "?"}</code></li>` +
          `<li>Export: <code>${out.export_path || "?"}</code> (${v.export_bytes != null ? (v.export_bytes / 1024).toFixed(1) + " KB" : "?"})</li>` +
          `<li>Full tilemap: ${v.full_tilemap_bytes != null ? (v.full_tilemap_bytes / 1e6).toFixed(1) + " MB" : "?"}</li>` +
          (v.chunks != null ? `<li>Game chunks refreshed: ${v.chunks}</li>` : "") +
          (v.backup ? `<li>Backup: <code>${v.backup}</code></li>` : "") +
          `</ul>` +
          `<p><strong>Next:</strong> <code>${out.next_step || "python3 tools/apply_port_map_wang16_1px_export.py"}</code></p>`,
      };
    }
    return {
      tone: "warn",
      title: "Result",
      html: `<p>${out.message || JSON.stringify(out)}</p>`,
    };
  }

  function dismissTerrainFeedback() {
    if (terrainFeedback) terrainFeedback.classList.add("hidden");
    if (terrainReportDetails) terrainReportDetails.classList.add("hidden");
    if (mapOverlay) {
      mapOverlay.style.background = "";
      if (bounds) {
        mapOverlay.textContent =
          toolMode === "terrain"
            ? "Terrain: click cell · Land/Sea brush · shore = derived Wang"
            : "Ports: drag port · wheel zoom · right-drag pan";
      }
    }
  }

  function showTerrainFeedback(out) {
    const { tone, title, html } = formatTerrainFeedback(out);
    const plain = (out.message || title).replace(/<[^>]+>/g, "");
    setStatus(plain, tone === "err" || tone === "warn");
    if (tone === "saved") statusText.classList.add("ok");
    if (mapOverlay && (tone === "saved" || tone === "dry-run")) {
      mapOverlay.textContent = plain;
      mapOverlay.style.background = "rgba(0,0,0,0.75)";
    }
    if (terrainFeedback) {
      terrainFeedback.className = `terrain-feedback ${tone}`;
      if (terrainFeedbackTitle) terrainFeedbackTitle.textContent = title;
      if (terrainFeedbackBody) terrainFeedbackBody.innerHTML = html;
      terrainFeedback.classList.remove("hidden");
      terrainFeedback.scrollIntoView({ block: "nearest", behavior: "smooth" });
    } else {
      window.alert(`${title}\n\n${plain}`);
    }
    if (terrainReport) terrainReport.textContent = JSON.stringify(out, null, 2);
    if (terrainReportDetails) terrainReportDetails.classList.remove("hidden");
    updateTerrainDiskStatus(out.disk_status);
    console.info("[terrain]", tone, out);
  }

  if (terrainFeedbackDismiss) {
    terrainFeedbackDismiss.addEventListener("click", (e) => {
      e.preventDefault();
      dismissTerrainFeedback();
    });
  }

  function updateTerrainDiskStatus(disk) {
    if (!terrainDiskStatus || !disk) return;
    if (disk.on_disk) {
      terrainDiskStatus.innerHTML =
        `Last terrain save on disk: <code>${disk.last_saved_at || disk.export_generated_at || "?"}</code>` +
        (disk.export_port_count != null ? ` · export has ${disk.export_port_count} ports` : "");
      terrainDiskStatus.classList.remove("err");
    } else {
      terrainDiskStatus.textContent =
        "No terrain editor save on disk yet (tilemap still 3px upscale / no export).";
      terrainDiskStatus.classList.add("err");
    }
  }

  async function refreshTerrainDiskStatus() {
    try {
      const res = await fetch("/api/terrain/status");
      const data = await res.json();
      if (res.ok) updateTerrainDiskStatus(data.disk);
      if (data.unsaved_sessions?.length) {
        terrainDirty = true;
        updateToolUi();
      }
    } catch (_) {}
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

  function markerCanvasScale() {
    return viewScale > 0 ? viewScale : 1;
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
    const img =
      toolMode === "terrain" && terrainPreviewImage && terrainPreviewImage.complete
        ? terrainPreviewImage
        : mapImage;
    if (img && img.complete) {
      ctx.drawImage(img, 0, 0, w, h);
    }
  }

  function drawMarkers() {
    const s = markerCanvasScale();
    const r = MARKER_SCREEN_RADIUS / s;
    const stroke = 2 / s;
    const labelGap = 4 / s;
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
        ctx.fillText(p.name, lx + r + labelGap, ly + labelGap);
      }
    }
  }

  function draw() {
    if (!bounds) return;
    drawBasemap();
    if (toolMode === "ports") drawMarkers();
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

    setComputing(true, "Loading terrain session…");
    try {
      await initTerrainSession();
    } finally {
      setComputing(false);
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
    const areaName = chartAreas.find((a) => a.id === id)?.name || id;
    setStatus(
      `${areaName}: ${shoreSnapCount.toLocaleString()} shore snap targets · ${areaPorts.length} ports · 1px wang16`,
    );
    updateToolUi();
    mapOverlay.textContent =
      toolMode === "terrain"
        ? "Terrain: click cell · Land/Sea brush · shore = derived Wang"
        : "Ports: drag port · wheel zoom · right-drag pan";
    if (terrainBoundaryWarning) setStatus(terrainBoundaryWarning, true);
  }

  async function paintTerrainAt(lx, ly) {
    let { gx, gy } = globalFromLocal(lx, ly);
    gx = Math.round(gx);
    gy = Math.round(gy);
    setComputing(true, "Recomputing chart area…");
    try {
      const res = await fetch("/api/terrain/paint", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          area_id: areaId,
          gx,
          gy,
          terrain: terrainBrush,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "paint failed");
      terrainDirty = true;
      terrainPreviewVersion = data.preview_version || terrainPreviewVersion + 1;
      await loadTerrainPreview();
      draw();
      let msg = `Painted (${gx}, ${gy}) → ${data.tile_after}`;
      if (data.cross_area_ripple) {
        const areas = (data.overlapping_chart_areas || []).join(", ");
        msg += ` · boundary ripple → ${areas}`;
        terrainBoundaryWarning = msg;
        setStatus(msg, true);
      } else {
        setStatus(msg);
      }
    } finally {
      setComputing(false);
    }
  }

  function hitTestPort(lx, ly) {
    const s = markerCanvasScale();
    const hitR = (MARKER_SCREEN_RADIUS + MARKER_HIT_PAD) / s;
    for (const p of areaPorts) {
      const pos = getPortPos(p.id);
      if (!pos) continue;
      const loc = localFromGlobal(pos.gx, pos.gy);
      const d = Math.hypot(loc.lx - lx, loc.ly - ly);
      if (d <= hitR) return p.id;
    }
    return null;
  }

  canvas.addEventListener("pointerdown", async (e) => {
    if (!bounds || computing) return;
    const { lx, ly } = screenToLocal(e.clientX, e.clientY);
    lastPointerX = e.clientX;
    lastPointerY = e.clientY;

    if (toolMode === "terrain" && e.button === 0 && !e.altKey) {
      try {
        await paintTerrainAt(lx, ly);
      } catch (err) {
        setStatus(String(err), true);
      }
      return;
    }

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
      if (toolMode === "ports") draw();
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

  document.querySelectorAll('input[name="tool-mode"]').forEach((el) => {
    el.addEventListener("change", () => {
      const checked = document.querySelector('input[name="tool-mode"]:checked');
      if (checked) toolMode = checked.value;
      updateToolUi();
      if (toolMode === "terrain" && areaId && !terrainPreviewImage) {
        loadTerrainPreview()
          .then(() => draw())
          .catch((err) => setStatus(String(err), true));
      } else {
        draw();
      }
      if (bounds) {
        mapOverlay.textContent =
          toolMode === "terrain"
            ? "Terrain: click cell · Land/Sea brush"
            : "Ports: drag port · wheel zoom · right-drag pan";
      }
    });
  });

  document.querySelectorAll('input[name="terrain-brush"]').forEach((el) => {
    el.addEventListener("change", () => {
      terrainBrush = getTerrainBrush();
    });
  });

  async function postTerrainSave(dryRun) {
    const res = await fetch("/api/terrain/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ dry_run: dryRun }),
    });
    const text = await res.text();
    let out;
    try {
      out = JSON.parse(text);
    } catch (_) {
      if (res.status === 404) {
        throw new Error(
          "POST /api/terrain/save not found — restart port_map_editor_wang16_1px_server.py (not the old 8766 editor).",
        );
      }
      throw new Error(`Server returned non-JSON (${res.status}): ${text.slice(0, 120)}`);
    }
    if (!res.ok) throw new Error(out.error || `HTTP ${res.status}`);
    return out;
  }

  async function runTerrainDryRun() {
    if (!areaId) {
      setStatus("Select a chart area first", true);
      return;
    }
    setStatus("Dry-run: contacting server…");
    setComputing(true, "Dry-run save…");
    if (mapOverlay) mapOverlay.textContent = "Dry-run: checking edits…";
    try {
      const out = await postTerrainSave(true);
      showTerrainFeedback(out);
    } catch (err) {
      const msg = String(err);
      if (terrainFeedback) {
        terrainFeedback.className = "terrain-feedback err";
        terrainFeedback.innerHTML = `<h4>Dry-run failed</h4><p>${msg}</p>`;
        terrainFeedback.classList.remove("hidden");
      }
      setStatus(msg, true);
      window.alert(`Dry-run failed:\n${msg}`);
    } finally {
      setComputing(false);
      updateToolUi();
    }
  }

  async function runTerrainSave() {
    if (!areaId) {
      setStatus("Select a chart area first", true);
      return;
    }
    if (!terrainDirty) {
      setStatus("Paint at least one cell before saving terrain", true);
      window.alert("Paint at least one land/sea cell on the map, then save.");
      return;
    }
    if (
      !window.confirm(
        "Save terrain? Rewrites full wang16 tilemap, mask PNG, all chart-area files, and exports auto-resnap JSON.",
      )
    ) {
      return;
    }
    setStatus("Saving terrain…");
    setComputing(true, "Saving terrain (full rebuild)…");
    if (mapOverlay) mapOverlay.textContent = "Writing tilemap + mask + chart areas…";
    try {
      const out = await postTerrainSave(false);
      showTerrainFeedback(out);
      if (!out.written_to_disk) return;
      terrainDirty = false;
      terrainBoundaryWarning = "";
      mapImage = null;
      await loadArea(areaId);
      await refreshTerrainDiskStatus();
    } catch (err) {
      const msg = String(err);
      if (terrainFeedback) {
        terrainFeedback.className = "terrain-feedback err";
        terrainFeedback.innerHTML =
          `<h4>Save failed</h4><p>${msg}</p><p>Check the server terminal for tracebacks.</p>`;
        terrainFeedback.classList.remove("hidden");
      }
      setStatus(msg, true);
      window.alert(`Save failed:\n${msg}`);
    } finally {
      setComputing(false);
      updateToolUi();
    }
  }

  async function runTerrainDiscard() {
    if (!areaId) return;
    setComputing(true, "Discarding…");
    try {
      await fetch("/api/terrain/discard", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ area_id: areaId }),
      });
      terrainDirty = false;
      dismissTerrainFeedback();
      terrainBoundaryWarning = "";
      await loadArea(areaId);
      setStatus("Terrain edits discarded");
    } catch (err) {
      setStatus(String(err), true);
    } finally {
      setComputing(false);
      updateToolUi();
    }
  }

  const sidebar = $("sidebar");
  if (sidebar) {
    sidebar.addEventListener("click", (e) => {
      const btn = e.target.closest("button");
      if (!btn || computing || btn.classList.contains("btn-inactive")) return;
      if (btn.id === "terrain-dry-run-btn") {
        e.preventDefault();
        void runTerrainDryRun();
      } else if (btn.id === "terrain-save-btn") {
        e.preventDefault();
        void runTerrainSave();
      } else if (btn.id === "terrain-discard-btn") {
        e.preventDefault();
        void runTerrainDiscard();
      }
    });
  } else {
    console.error("[terrain] #sidebar missing — button clicks will not work");
  }

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
        stamp.textContent =
          `Editor ${EDITOR_BUILD} · basemap v${data.mask_version || "?"} · ${data.mask_path || ""}`;
      }
      if (!data.terrain_disk) {
        setStatus("Warning: server missing terrain API — use port_map_editor_wang16_1px_server.py", true);
      }
      updateTerrainDiskStatus(data.terrain_disk);
      refreshTerrainDiskStatus();
      let statusMsg = msg;
      let statusErr = false;
      try {
        const tr = await fetch("/api/terrain/status");
        if (!tr.ok) {
          statusMsg = `Terrain API missing (HTTP ${tr.status}) — use port_map_editor_wang16_1px_server.py + hard-refresh`;
          statusErr = true;
        }
      } catch (e) {
        statusMsg = `Terrain API unreachable: ${e}`;
        statusErr = true;
      }
      setStatus(statusMsg, statusErr);
      updateToolUi();
      mapOverlay.textContent = "Select a chart area";
    } catch (err) {
      setStatus(String(err), true);
    }
  }

  init();
})();

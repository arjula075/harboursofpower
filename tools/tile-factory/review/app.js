(function () {
  const setSelect = document.getElementById("set-select");
  const poolSelect = document.getElementById("pool-select");
  const generationSelect = document.getElementById("generation-select");
  const variationSelect = document.getElementById("variation-select");
  const viewSelect = document.getElementById("view-select");
  const refreshBtn = document.getElementById("refresh-btn");
  const approveAllBtn = document.getElementById("approve-all-btn");
  const setMeta = document.getElementById("set-meta");
  const statusEl = document.getElementById("status");
  const serverHint = document.getElementById("server-hint");
  const mosaicPanel = document.getElementById("mosaic-panel");
  const gridPanel = document.getElementById("grid-panel");
  const mosaicGrid = document.getElementById("mosaic-grid");
  const tileGrid = document.getElementById("tile-grid");

  let sets = [];

  function setStatus(msg, kind) {
    statusEl.textContent = msg;
    statusEl.className = "status" + (kind ? " " + kind : "");
  }
  window.tileReviewSetStatus = setStatus;

  function currentSetKey() {
    const v = setSelect.value;
    if (!v) return null;
    const [biome, season] = v.split("|");
    return { biome, season };
  }

  function qs(params) {
    return new URLSearchParams(params).toString();
  }

  async function api(path) {
    const res = await fetch(path);
    let body = null;
    try {
      body = await res.json();
    } catch {
      if (!res.ok) {
        throw new Error(`Request failed (${res.status})`);
      }
      throw new Error("Invalid JSON from server");
    }
    if (!res.ok) {
      throw new Error(body.error || body.message || `Request failed (${res.status})`);
    }
    return body;
  }

  async function loadSets() {
    const data = await api("/api/sets");
    sets = data.sets || [];
    setSelect.innerHTML = "";
    if (!sets.length) {
      const opt = document.createElement("option");
      opt.value = "";
      opt.textContent = "(no tile sets found)";
      setSelect.appendChild(opt);
      return;
    }
    for (const s of sets) {
      const opt = document.createElement("option");
      opt.value = `${s.biome}|${s.season}`;
      const label = `${s.name} — ${s.season} (${s.pending_count} pending, ${s.approved_count} approved)`;
      opt.textContent = label;
      setSelect.appendChild(opt);
    }
    const cfgBiome = "sparse_olive|summer";
    const dry = "dry_scrubland|summer";
    if ([...setSelect.options].some((o) => o.value === cfgBiome)) {
      setSelect.value = cfgBiome;
    } else if ([...setSelect.options].some((o) => o.value === dry)) {
      setSelect.value = dry;
    }
    populateGenerations();
    updateSetMeta();
  }

  function updateSetMeta() {
    const key = currentSetKey();
    if (!key) {
      setMeta.textContent = "";
      return;
    }
    const row = sets.find((s) => s.biome === key.biome && s.season === key.season);
    if (!row) {
      setMeta.textContent = `${key.biome} / ${key.season}`;
      return;
    }
    const genLabel =
      (row.generations || []).find((g) => g.generation === currentGeneration())?.label ||
      `g${String(currentGeneration()).padStart(3, "0")}`;
    setMeta.textContent = `${row.name} · ${row.status || "—"} · ${genLabel} · pending ${row.pending_count} · approved ${row.approved_count}`;
  }

  function currentGeneration() {
    const v = generationSelect.value;
    return v ? parseInt(v, 10) : 1;
  }

  function populateGenerations() {
    const key = currentSetKey();
    generationSelect.innerHTML = "";
    if (!key) return;
    const row = sets.find((s) => s.biome === key.biome && s.season === key.season);
    const gens = row?.generations?.length ? row.generations : [{ generation: 1, label: "g001 (legacy)" }];
    for (const g of gens) {
      const opt = document.createElement("option");
      opt.value = String(g.generation);
      opt.textContent = g.label || `g${String(g.generation).padStart(3, "0")}`;
      generationSelect.appendChild(opt);
    }
    const active = row?.active_generation;
    if (active && [...generationSelect.options].some((o) => o.value === String(active))) {
      generationSelect.value = String(active);
    } else if (gens.length) {
      generationSelect.value = String(gens[gens.length - 1].generation);
    }
  }

  async function fetchJson(url, options) {
    const res = await fetch(url, options);
    let body = {};
    try {
      body = await res.json();
    } catch {
      if (!res.ok) throw new Error(`Request failed (${res.status})`);
      throw new Error("Invalid JSON");
    }
    if (!res.ok) throw new Error(body.error || body.message || `HTTP ${res.status}`);
    return body;
  }

  async function pollRegenerate(jobId, onStatus) {
    for (let i = 0; i < 600; i++) {
      const job = await fetchJson(`/api/regenerate/${jobId}`);
      if (onStatus) onStatus(job);
      if (job.status === "done" || job.status === "failed") return job;
      await new Promise((r) => setTimeout(r, 1500));
    }
    throw new Error("Regenerate timed out");
  }

  function buildPromptPanel(tileId, onRefresh) {
    const wrap = document.createElement("div");
    wrap.className = "prompt-panel";
    const title = document.createElement("p");
    title.className = "prompt-panel-title";
    title.textContent = "Prompts & recreate";
    wrap.appendChild(title);
    const loading = document.createElement("p");
    loading.className = "hint";
    loading.textContent = "Loading prompts…";
    wrap.appendChild(loading);

    (async () => {
      try {
        const data = await fetchJson(`/api/prompt?${new URLSearchParams({ id: tileId })}`);
        loading.remove();
        if (data.procedural_note) {
          const note = document.createElement("p");
          note.className = "hint procedural-note";
          note.textContent = data.procedural_note;
          wrap.appendChild(note);
        }

        const layerEditors = {};
        const actions = document.createElement("div");
        actions.className = "card-actions prompt-actions";

        const saveBtn = document.createElement("button");
        saveBtn.type = "button";
        saveBtn.textContent = "Save prompts";
        const resetBtn = document.createElement("button");
        resetBtn.type = "button";
        resetBtn.className = "secondary";
        resetBtn.textContent = "Reset defaults";
        const regenBtn = document.createElement("button");
        regenBtn.type = "button";
        regenBtn.textContent = data.procedural ? "Recreate (sea)" : "Recreate tile";

        actions.appendChild(saveBtn);
        actions.appendChild(resetBtn);
        actions.appendChild(regenBtn);
        wrap.appendChild(actions);

        const details = document.createElement("details");
        details.className = "prompt-details";
        details.open = true;
        const summary = document.createElement("summary");
        summary.textContent = "Edit prompt layers";
        details.appendChild(summary);

        for (const layer of data.layers || []) {
          const block = document.createElement("details");
          block.className = "prompt-layer" + (layer.customized ? " customized" : "");
          block.open = false;
          const s = document.createElement("summary");
          s.textContent = layer.label + (layer.customized ? " · edited" : "");
          block.appendChild(s);
          const src = document.createElement("p");
          src.className = "layer-source";
          src.textContent = layer.source;
          block.appendChild(src);
          const ta = document.createElement("textarea");
          ta.className = "layer-text";
          ta.rows = Math.min(10, Math.max(3, Math.ceil(layer.text.length / 60)));
          ta.value = layer.text;
          layerEditors[layer.key] = ta;
          block.appendChild(ta);
          details.appendChild(block);
        }

        const fullTa = document.createElement("textarea");
        fullTa.className = "layer-text readonly";
        fullTa.readOnly = true;
        fullTa.rows = 6;
        fullTa.value = data.full_prompt || "";
        const fullLbl = document.createElement("p");
        fullLbl.className = "layer-source";
        fullLbl.textContent = "Full prompt sent to API (preview)";
        details.appendChild(fullLbl);
        details.appendChild(fullTa);
        wrap.appendChild(details);

        saveBtn.addEventListener("click", async () => {
          saveBtn.disabled = true;
          try {
            const layers = {};
            for (const [key, ta] of Object.entries(layerEditors)) {
              layers[key] = ta.value;
            }
            const saved = await fetchJson("/api/prompt", {
              method: "PUT",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ id: tileId, layers, clear_full_override: true }),
            });
            fullTa.value = saved.prompt?.full_prompt || saved.full_prompt || "";
            setStatus("Prompts saved for " + tileId, "ok");
          } catch (e) {
            setStatus(String(e.message || e), "err");
          }
          saveBtn.disabled = false;
        });

        resetBtn.addEventListener("click", async () => {
          if (!confirm("Reset prompt layers to style-bible defaults?")) return;
          try {
            await fetchJson("/api/prompt", {
              method: "PUT",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ id: tileId, layers: {}, clear_full_override: true }),
            });
            const parent = wrap.parentElement;
            const fresh = buildPromptPanel(tileId, onRefresh);
            parent.replaceChild(fresh, wrap);
            setStatus("Prompts reset", "ok");
          } catch (e) {
            setStatus(String(e.message || e), "err");
          }
        });

        regenBtn.addEventListener("click", async () => {
          if (
            !confirm(
              data.procedural
                ? "Rebuild procedural sea tile?"
                : "Regenerate via OpenAI + compositor? (API cost, ~1–2 min)"
            )
          ) {
            return;
          }
          regenBtn.disabled = true;
          saveBtn.disabled = true;
          const logEl = document.createElement("pre");
          logEl.className = "regen-log";
          logEl.textContent = "Starting…";
          wrap.appendChild(logEl);
          try {
            const started = await fetchJson("/api/regenerate", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ id: tileId }),
            });
            const job = await pollRegenerate(started.job_id, (j) => {
              logEl.textContent = j.log || j.status;
            });
            logEl.textContent = job.log || (job.ok ? "Done" : "Failed");
            setStatus(job.ok ? `Recreated ${tileId}` : `Recreate failed`, job.ok ? "ok" : "err");
            if (job.ok && onRefresh) onRefresh();
          } catch (e) {
            logEl.textContent = String(e.message || e);
            setStatus(String(e.message || e), "err");
          }
          regenBtn.disabled = false;
          saveBtn.disabled = false;
        });
      } catch (e) {
        loading.textContent = "Prompts failed: " + (e.message || e);
        loading.className = "hint err-text";
      }
    })();

    return wrap;
  }

  function makeApproveButton(tile, onDone) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = "Approve";
    btn.disabled = !tile.can_approve;
    btn.addEventListener("click", async () => {
      btn.disabled = true;
      setStatus(`Approving ${tile.id}…`);
      try {
        const res = await fetch("/api/approve", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ id: tile.id }),
        });
        let body = {};
        try {
          body = await res.json();
        } catch {
          throw new Error(res.ok ? "Invalid server response" : `Server error (${res.status})`);
        }
        if (!body.ok) {
          throw new Error(body.error || "approve failed");
        }
        setStatus(`Approved ${tile.id}`, "ok");
        if (onDone) onDone();
        else refresh();
      } catch (e) {
        setStatus(String(e.message || e), "err");
        btn.disabled = false;
      }
    });
    return btn;
  }

  function renderMosaic(data) {
    mosaicGrid.innerHTML = "";
    mosaicGrid.style.gridTemplateColumns = `repeat(${data.cols}, 128px)`;
    for (const cell of data.cells) {
      const div = document.createElement("div");
      div.className = "cell" + (cell.missing ? " missing" : "");
      if (cell.missing) {
        div.innerHTML = `<div class="ph">?</div><p>${cell.label}</p><p class="id">${cell.id}</p>`;
      } else {
        const img = document.createElement("img");
        img.src = cell.image_url;
        img.alt = cell.label;
        img.loading = "lazy";
        div.appendChild(img);
        const p = document.createElement("p");
        p.textContent = cell.label;
        div.appendChild(p);
        if (cell.id) {
          div.appendChild(buildPromptPanel(cell.id, refresh));
        }
        const actions = document.createElement("div");
        actions.className = "card-actions";
        if (cell.can_approve) {
          actions.appendChild(makeApproveButton(cell, refresh));
        }
        if (actions.childNodes.length) div.appendChild(actions);
      }
      mosaicGrid.appendChild(div);
    }
    if (data.missing && data.missing.length) {
      setStatus(`${data.missing.length} missing tile(s) in this set / variation`, "err");
    }
  }

  function renderGrid(tiles) {
    tileGrid.innerHTML = "";
    if (!tiles.length) {
      tileGrid.innerHTML = "<p class=\"hint\">No tiles in this pool / variation.</p>";
      return;
    }
    const sorted = [...tiles].sort((a, b) => {
      const ta = a.topology.localeCompare(b.topology);
      if (ta !== 0) return ta;
      return a.variation - b.variation;
    });
    for (const tile of sorted) {
      const card = document.createElement("div");
      card.className = "card" + (tile.pool === "approved" ? " approved" : "");
      const img = document.createElement("img");
      img.src = tile.image_url;
      img.alt = tile.id;
      img.loading = "lazy";
      card.appendChild(img);
      const title = document.createElement("p");
      title.className = "card-title";
      const gen = tile.generation ? ` · ${tile.generation > 1 ? "g" + String(tile.generation).padStart(3, "0") : "g001"}` : "";
      title.textContent = `${tile.label} · v${String(tile.variation).padStart(2, "0")}${gen}`;
      card.appendChild(title);
      const idp = document.createElement("p");
      idp.className = "id";
      idp.textContent = tile.id;
      card.appendChild(idp);
      const badge = document.createElement("span");
      badge.className = "badge badge-" + tile.pool;
      badge.textContent = tile.pool;
      card.appendChild(badge);
      if (tile.spec_status) {
        const sb = document.createElement("span");
        sb.className = "badge";
        sb.textContent = tile.spec_status;
        card.appendChild(sb);
      }
      card.appendChild(buildPromptPanel(tile.id, refresh));
      const actions = document.createElement("div");
      actions.className = "card-actions";
      if (tile.can_approve) {
        actions.appendChild(makeApproveButton(tile, refresh));
      }
      card.appendChild(actions);
      tileGrid.appendChild(card);
    }
  }

  async function refresh() {
    const key = currentSetKey();
    if (!key) return;
    populateGenerations();
    updateSetMeta();
    const pool = poolSelect.value;
    const variation = variationSelect.value;
    const generation = currentGeneration();
    const view = viewSelect.value;
    mosaicPanel.classList.toggle("hidden", view !== "mosaic");
    gridPanel.classList.toggle("hidden", view !== "grid");
    approveAllBtn.disabled = view !== "grid" || pool === "approved";

    setStatus("Loading…");
    try {
      if (view === "mosaic") {
        const varN = variation === "all" ? "1" : variation;
        const data = await api(
          `/api/mosaic?${qs({
            biome: key.biome,
            season: key.season,
            pool: pool === "both" ? "pending" : pool,
            variation: varN,
            generation,
          })}`
        );
        renderMosaic(data);
        if (!data.missing || !data.missing.length) {
          setStatus(
            `Lake mosaic · ${key.biome} / ${key.season} · g${String(generation).padStart(3, "0")} · v${varN} · ${pool}`
          );
        }
      } else {
        const data = await api(
          `/api/tiles?${qs({ biome: key.biome, season: key.season, pool, variation, generation })}`
        );
        renderGrid(data.tiles || []);
        setStatus(
          `${(data.tiles || []).length} tile(s) · ${key.biome} / ${key.season} · g${String(generation).padStart(3, "0")}`
        );
      }
    } catch (e) {
      setStatus(String(e.message || e), "err");
    }
  }

  async function approveAllVisible() {
    const key = currentSetKey();
    if (!key) return;
    const variation = variationSelect.value;
    const generation = currentGeneration();
    const data = await api(
      `/api/tiles?${qs({ biome: key.biome, season: key.season, pool: "pending", variation, generation })}`
    );
    const tiles = (data.tiles || []).filter((t) => t.can_approve);
    if (!tiles.length) {
      setStatus("No pending tiles to approve", "err");
      return;
    }
    if (!confirm(`Approve ${tiles.length} pending tile(s) in this view?`)) return;
    approveAllBtn.disabled = true;
    let ok = 0;
    let fail = 0;
    for (const tile of tiles) {
      try {
        const res = await fetch("/api/approve", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ id: tile.id }),
        });
        const body = await res.json();
        if (body.ok) ok += 1;
        else fail += 1;
      } catch {
        fail += 1;
      }
    }
    await loadSets();
    await refresh();
    setStatus(`Bulk approve: ${ok} ok, ${fail} failed`, fail ? "err" : "ok");
    approveAllBtn.disabled = false;
  }

  setSelect.addEventListener("change", () => {
    populateGenerations();
    refresh();
  });
  poolSelect.addEventListener("change", refresh);
  generationSelect.addEventListener("change", refresh);
  variationSelect.addEventListener("change", refresh);
  viewSelect.addEventListener("change", refresh);
  refreshBtn.addEventListener("click", refresh);
  approveAllBtn.addEventListener("click", approveAllVisible);

  loadSets()
    .then(refresh)
    .catch(() => {
      serverHint.classList.remove("hidden");
      setStatus("Cannot reach review API — start review_server.py", "err");
    });
})();

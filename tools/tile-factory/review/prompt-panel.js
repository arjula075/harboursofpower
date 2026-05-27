/** Prompt editor + recreate — loaded by index.html */
(function (global) {
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
    wrap.innerHTML = '<p class="hint">Loading prompts…</p>';

    (async () => {
      try {
        const data = await fetchJson(`/api/prompt?${new URLSearchParams({ id: tileId })}`);
        wrap.innerHTML = "";
        if (data.procedural_note) {
          const note = document.createElement("p");
          note.className = "hint procedural-note";
          note.textContent = data.procedural_note;
          wrap.appendChild(note);
        }

        const details = document.createElement("details");
        details.className = "prompt-details";
        details.open = false;
        const summary = document.createElement("summary");
        summary.textContent = "Generation prompts";
        details.appendChild(summary);

        const layerEditors = {};
        for (const layer of data.layers || []) {
          const block = document.createElement("details");
          block.className = "prompt-layer" + (layer.customized ? " customized" : "");
          const s = document.createElement("summary");
          s.textContent = layer.label + (layer.customized ? " · edited" : "");
          block.appendChild(s);
          const src = document.createElement("p");
          src.className = "layer-source";
          src.textContent = layer.source;
          block.appendChild(src);
          const ta = document.createElement("textarea");
          ta.className = "layer-text";
          ta.rows = Math.min(12, Math.max(3, Math.ceil(layer.text.length / 70)));
          ta.value = layer.text;
          ta.dataset.key = layer.key;
          layerEditors[layer.key] = ta;
          block.appendChild(ta);
          details.appendChild(block);
        }

        const fullBlock = document.createElement("details");
        fullBlock.className = "prompt-layer full-prompt";
        fullBlock.open = false;
        const fs = document.createElement("summary");
        fs.textContent = "Full assembled prompt (read-only)";
        fullBlock.appendChild(fs);
        const fullTa = document.createElement("textarea");
        fullTa.className = "layer-text readonly";
        fullTa.readOnly = true;
        fullTa.rows = 10;
        fullTa.value = data.full_prompt || "";
        fullBlock.appendChild(fullTa);
        details.appendChild(fullBlock);

        wrap.appendChild(details);

        const actions = document.createElement("div");
        actions.className = "card-actions prompt-actions";

        const saveBtn = document.createElement("button");
        saveBtn.type = "button";
        saveBtn.textContent = "Save prompts";
        saveBtn.addEventListener("click", async () => {
          saveBtn.disabled = true;
          try {
            const layers = {};
            for (const [key, ta] of Object.entries(layerEditors)) {
              layers[key] = ta.value;
            }
            await fetchJson("/api/prompt", {
              method: "PUT",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ id: tileId, layers, clear_full_override: true }),
            });
            if (global.tileReviewSetStatus) global.tileReviewSetStatus("Prompts saved for " + tileId, "ok");
            const refreshed = await fetchJson(`/api/prompt?${new URLSearchParams({ id: tileId })}`);
            fullTa.value = refreshed.full_prompt || "";
          } catch (e) {
            if (global.tileReviewSetStatus) global.tileReviewSetStatus(String(e.message || e), "err");
          }
          saveBtn.disabled = false;
        });
        actions.appendChild(saveBtn);

        const resetBtn = document.createElement("button");
        resetBtn.type = "button";
        resetBtn.className = "secondary";
        resetBtn.textContent = "Reset to defaults";
        resetBtn.addEventListener("click", async () => {
          if (!confirm("Reset all prompt layers to style-bible defaults?")) return;
          try {
            await fetchJson("/api/prompt", {
              method: "PUT",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ id: tileId, layers: {}, clear_full_override: true }),
            });
            const parent = wrap.parentElement;
            const fresh = buildPromptPanel(tileId, onRefresh);
            parent.replaceChild(fresh, wrap);
            if (global.tileReviewSetStatus) global.tileReviewSetStatus("Prompts reset", "ok");
          } catch (e) {
            if (global.tileReviewSetStatus) global.tileReviewSetStatus(String(e.message || e), "err");
          }
        });
        actions.appendChild(resetBtn);

        const regenBtn = document.createElement("button");
        regenBtn.type = "button";
        regenBtn.textContent = data.procedural ? "Recreate (procedural)" : "Recreate tile";
        regenBtn.addEventListener("click", async () => {
          if (
            !confirm(
              "Regenerate this tile? " +
                (data.procedural
                  ? "Rebuilds procedural sea (fast)."
                  : "Calls OpenAI + compositor (uses API credits, ~1–2 min).")
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
            if (global.tileReviewSetStatus) {
              global.tileReviewSetStatus(
                job.ok ? `Recreated ${tileId}` : `Recreate failed: ${tileId}`,
                job.ok ? "ok" : "err"
              );
            }
            if (job.ok && onRefresh) onRefresh();
          } catch (e) {
            logEl.textContent = String(e.message || e);
            if (global.tileReviewSetStatus) global.tileReviewSetStatus(String(e.message || e), "err");
          }
          regenBtn.disabled = false;
          saveBtn.disabled = false;
        });
        actions.appendChild(regenBtn);

        wrap.appendChild(actions);
      } catch (e) {
        wrap.innerHTML = `<p class="hint err-text">Prompts: ${e.message || e}</p>`;
      }
    })();

    return wrap;
  }

  global.buildTilePromptPanel = buildPromptPanel;
})();

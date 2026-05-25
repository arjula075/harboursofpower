# HarboursOfPower — Cursor Canvases

These `.canvas.tsx` files are **live documents** (rendered UI), not ordinary source files to edit from the file tree.

## Open in **viewing** (rendered) mode — default for reading

| Do this | Result |
|--------|--------|
| **`Cmd+Shift+P`** → **`Open Canvas`** (under **View**) → pick a canvas | **Rendered** layout (tables, epics, stats) |
| Click the **canvas card** at the end of an Agent reply | **Rendered** view beside chat |
| **Agents Window** → new tab → Canvas | **Rendered** tab |

## File-tree click opens **editing** (source) mode

Double-clicking `*.canvas.tsx` in the explorer opens the **TSX source** editor. That is expected Cursor behaviour today.

To switch back to the human-readable view:

1. With the canvas tab active, use the canvas toolbar to switch from **Source** → **Preview** / **Rendered** (exact label varies by Cursor version), **or**
2. Close the tab and reopen via **`Open Canvas`** above.

## Two copies of each canvas

| Location | Purpose |
|----------|---------|
| `HarboursOfPower/canvases/` (this folder) | **Git** — versioned project docs |
| `~/.cursor/projects/Users-ari-lahti-HarboursOfPower/canvases/` | **Preview server** — must exist here for **Open Canvas** to list the file |

After adding or heavily editing a canvas in the repo, copy it to the managed folder (or ask Agent to sync) so preview and **Open Canvas** stay in sync.

## Main backlog (epics & features)

**`harbours-consolidated-implementation-plan.canvas.tsx`** — open via **Open Canvas**, not the raw file tree.

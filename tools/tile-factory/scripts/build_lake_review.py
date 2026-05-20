"""Build 5x5 lake mosaic review page (25 tiles) + composite PNG."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image

from common import FACTORY_ROOT, load_config, load_topology_rules, repo_path

LAYOUT_PATH = Path(__file__).with_name("lake_layout.json")
CELL_PX = 128


def tile_webp_path(biome: str, season: str, topology: str, variation: int = 1) -> Path:
    return repo_path(f"assets/tiles/pending/{biome}/{season}/{topology}/v{variation:02d}.webp")


def main() -> int:
    cfg = load_config()
    biome = cfg["biome"]
    season = cfg["season"]
    tile_size = int(cfg["tile_size"])

    with LAYOUT_PATH.open(encoding="utf-8") as f:
        layout = json.load(f)["grid"]
    rows = len(layout)
    cols = len(layout[0])

    missing: list[str] = []
    mosaic = Image.new("RGB", (cols * tile_size, rows * tile_size))
    cells_html: list[str] = []

    for row_idx, row in enumerate(layout):
        for col_idx, topology in enumerate(row):
            path = tile_webp_path(biome, season, topology, 1)
            rel = path.relative_to(repo_path(".")).as_posix()
            label = topology.replace("_", " ")
            if not path.is_file():
                missing.append(rel)
                cells_html.append(
                    f'<div class="cell missing" title="{topology}">'
                    f'<motion></motion><motion></motion><div class="ph">?</div><p>{label}</p></div>'
                )
                continue
            img = Image.open(path).convert("RGB")
            if img.size != (tile_size, tile_size):
                img = img.resize((tile_size, tile_size), Image.Resampling.LANCZOS)
            mosaic.paste(img, (col_idx * tile_size, row_idx * tile_size))
            cells_html.append(
                f'<div class="cell"><img src="../../../{rel}" width="{CELL_PX}" height="{CELL_PX}" />'
                f"<p>{label}</p></div>"
            )

    reports = repo_path(cfg["paths"]["reports"])
    reports.mkdir(parents=True, exist_ok=True)
    mosaic_thumb = mosaic.resize((cols * CELL_PX, rows * CELL_PX), Image.Resampling.LANCZOS)
    mosaic_path = reports / "lake_mosaic_5x5.png"
    mosaic_thumb.save(mosaic_path)

    grid_html = "".join(cells_html).replace("<motion></motion>", "")
    missing_block = ""
    if missing:
        missing_block = "<h2>Missing tiles (run generate-full-v1)</h2><ul>" + "".join(
            f"<li><code>{m}</code></li>" for m in missing
        ) + "</ul>"

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Lake mosaic — 10 tile set</title>
<style>
body {{ font-family: system-ui; background: #1a1a1a; color: #eee; margin: 16px; }}
h1 {{ margin-bottom: 4px; }}
.sub {{ color: #aaa; margin-bottom: 16px; }}
.mosaic-wrap {{ margin-bottom: 24px; }}
.mosaic-wrap img {{ border: 1px solid #444; image-rendering: auto; }}
.grid {{
  display: grid;
  grid-template-columns: repeat(5, {CELL_PX}px);
  gap: 4px;
  width: fit-content;
}}
.cell {{ background: #2a2a2a; padding: 4px; border-radius: 4px; text-align: center; }}
.cell p {{ font-size: 9px; margin: 4px 0 0; line-height: 1.2; color: #bbb; }}
.cell.missing .ph {{ width:{CELL_PX}px; height:{CELL_PX}px; background:#522; display:flex; align-items:center; justify-content:center; font-size:32px; }}
code {{ font-size: 11px; }}
</style></head><body>
<h1>Lake mosaic (5×5)</h1>
<p class="sub">Center = open sea · inner ring = shores · outer ring = land · 25 tiles total</p>
<div class="mosaic-wrap">
  <p><strong>Stitched preview</strong></p>
  <img src="../../../{mosaic_path.relative_to(repo_path('.')).as_posix()}" width="{cols * CELL_PX}" height="{rows * CELL_PX}" />
</div>
<div class="grid">{grid_html}</motion></div>
{missing_block}
<p style="margin-top:20px"><code>orchestrator.py approve dry_scrubland/summer/TOPOLOGY/v01</code></p>
</body></html>"""
    html = html.replace("</motion>", "")

    out = FACTORY_ROOT / "review" / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"Review -> {out}")
    print(f"Mosaic -> {mosaic_path}")
    if missing:
        print(f"Missing {len(missing)} tiles")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

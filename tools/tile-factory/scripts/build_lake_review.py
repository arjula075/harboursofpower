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

    for row_idx, row in enumerate(layout):
        for col_idx, topology in enumerate(row):
            path = tile_webp_path(biome, season, topology, 1)
            rel = path.relative_to(repo_path(".")).as_posix()
            if not path.is_file():
                missing.append(rel)
                continue
            img = Image.open(path).convert("RGB")
            if img.size != (tile_size, tile_size):
                img = img.resize((tile_size, tile_size), Image.Resampling.LANCZOS)
            mosaic.paste(img, (col_idx * tile_size, row_idx * tile_size))

    reports = repo_path(cfg["paths"]["reports"])
    reports.mkdir(parents=True, exist_ok=True)
    mosaic_thumb = mosaic.resize((cols * CELL_PX, rows * CELL_PX), Image.Resampling.LANCZOS)
    mosaic_path = reports / "lake_mosaic_5x5.png"
    mosaic_thumb.save(mosaic_path)

    print(f"Mosaic PNG -> {mosaic_path}")
    print("Open review UI:  python3 tools/tile-factory/review_server.py")
    print("                 http://127.0.0.1:8768/")
    if missing:
        print(f"Missing {len(missing)} tiles")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

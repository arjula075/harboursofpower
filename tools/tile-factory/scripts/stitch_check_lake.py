"""Verify land/sea mask agreement along shared edges in lake_layout.json."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from autotile_geometry import land_mask
from common import FACTORY_ROOT, load_config, repo_path


def _load_pending(topology: str, cfg: dict) -> np.ndarray | None:
    biome, season = cfg["biome"], cfg["season"]
    p = repo_path(f"assets/tiles/pending/{biome}/{season}/{topology}/v01.webp")
    if not p.is_file():
        return None
    return np.asarray(Image.open(p).convert("RGB"))


def main() -> int:
    cfg = load_config()
    layout = json.loads((FACTORY_ROOT / "scripts" / "lake_layout.json").read_text(encoding="utf-8"))
    grid = layout["grid"]
    size = int(cfg["tile_size"])
    errors: list[str] = []

    for r in range(len(grid) - 1):
        for c in range(len(grid[0]) - 1):
            a_id, b_id = grid[r][c], grid[r][c + 1]
            ma, mb = land_mask(a_id, size), land_mask(b_id, size)
            edge_a = ma[:, -1]
            edge_b = mb[:, 0]
            if not np.array_equal(edge_a, edge_b):
                mism = int(np.sum(edge_a != edge_b))
                errors.append(f"E-W {a_id}|{b_id} @ row {r}: {mism} px mismatch")

    for r in range(len(grid) - 1):
        for c in range(len(grid[0])):
            a_id, b_id = grid[r][c], grid[r + 1][c]
            ma, mb = land_mask(a_id, size), land_mask(b_id, size)
            edge_a = ma[-1, :]
            edge_b = mb[0, :]
            if not np.array_equal(edge_a, edge_b):
                mism = int(np.sum(edge_a != edge_b))
                errors.append(f"N-S {a_id}|{b_id} @ col {c}: {mism} px mismatch")

    if errors:
        print("MASK MISMATCHES:")
        for e in errors:
            print(f"  {e}")
        return 1
    print("All lake_layout shared edges: land/sea masks agree (0 px mismatch).")
    return 0


if __name__ == "__main__":
    sys.exit(main())

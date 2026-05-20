"""Publish every raw PNG in raw/ to pending/ as WebP (for review mosaic)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image

from common import FACTORY_ROOT, load_config, load_topology_rules, repo_path, spec_path
from generate_sail_mask import write_mask_for_tile


def main() -> int:
    cfg = load_config()
    biome = cfg["biome"]
    season = cfg["season"]
    size = int(cfg["tile_size"])
    count = 0
    for topo in load_topology_rules()["topologies"]:
        if topo.get("phase") != "v1":
            continue
        for v in range(1, int(cfg["variations_per_topology"]) + 1):
            tid = f"{biome}/{season}/{topo['id']}/v{v:02d}"
            sp = spec_path(tid)
            if not sp.is_file():
                continue
            with sp.open(encoding="utf-8") as f:
                spec = json.load(f)
            raw = Path(spec["raw_path"])
            if not raw.is_file():
                continue
            pending = Path(spec["pending_path"])
            pending.parent.mkdir(parents=True, exist_ok=True)
            img = Image.open(raw).convert("RGB")
            if img.size != (size, size):
                img = img.resize((size, size), Image.Resampling.LANCZOS)
            img.save(pending, format="WEBP", lossless=True)
            img.save(pending.with_suffix(".composed.png"))
            write_mask_for_tile(pending, spec["topology"], cfg)
            count += 1
            print(f"Published {tid}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

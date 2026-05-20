"""Re-apply the autotile contract to existing raw tiles, no API calls.

Useful after tweaking enforce_contract.py or land/sea anchors.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image

from autotile_geometry import SHORE_TOPOLOGIES
from autotile_agent import regenerate_uniform_sea_set
from tile_publish import resolve_land_anchor
from common import load_config, repo_path, spec_path
from enforce_contract import enforce_contract, measure_edge_uniformity
from generate_sail_mask import write_mask_for_tile
from make_uniform_sea import get_open_sea_rgb, save_open_sea_rgb


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--variations", type=int, nargs="*", default=None)
    args = parser.parse_args()

    cfg = load_config()
    biome = cfg["biome"]
    season = cfg["season"]
    sea_rgb = get_open_sea_rgb(cfg)
    save_open_sea_rgb(cfg, sea_rgb)
    land_anchor = resolve_land_anchor(cfg)
    coast_band = int(cfg.get("autotile_coast_band_px", 32))
    sea_fade = int(cfg.get("autotile_sea_fade_px", 96))

    print(f"Using sea_rgb={sea_rgb}, land_anchor={'YES' if land_anchor else 'NO'}", flush=True)

    variations = args.variations or list(range(1, int(cfg["variations_per_topology"]) + 1))

    for topo in SHORE_TOPOLOGIES:
        for v in variations:
            tid = f"{biome}/{season}/{topo}/v{v:02d}"
            sp = spec_path(tid)
            if not sp.is_file():
                continue
            with sp.open(encoding="utf-8") as f:
                spec = json.load(f)
            raw_p = Path(spec["raw_path"])
            if not raw_p.is_file():
                print(f"  skip (no raw): {tid}", flush=True)
                continue
            raw = Image.open(raw_p).convert("RGB")
            enforced = enforce_contract(
                raw,
                topo,
                sea_rgb,
                coast_band_px=coast_band,
                sea_fade_px=sea_fade,
                land_anchor=land_anchor,
                diagonal_sea_fade_px=int(cfg.get("diagonal_sea_fade_px", 48)),
                cfg=cfg,
                variation=int(spec.get("variation", v)),
            )
            pending = Path(spec["pending_path"])
            pending.parent.mkdir(parents=True, exist_ok=True)
            enforced.save(pending.with_suffix(".composed.png"))
            enforced.save(pending, format="WEBP", lossless=True)
            write_mask_for_tile(pending, topo, cfg)
            diag = measure_edge_uniformity(enforced, sea_rgb, topo, band=4)
            worst = max((v for v in diag.values() if v >= 0), default=0.0)
            print(f"  {tid}: worst outer edge diff {worst:.2f}", flush=True)

    regenerate_uniform_sea_set(cfg, sea_rgb)
    print("done.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Build sailing-map chunks: one image pixel per game tile (1×1 wang16 cells).

Outputs:
  - docs/maps/chunks/tile_{cx}_{cy}.webp  (128×128 tiles per chunk by default)
  - data/maps/chunk_manifest.json         (layout: tile_pixels)

Run from repo root:
  .venv/bin/python tools/build_tile_pixel_chunks.py
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

REPO = Path(__file__).resolve().parents[1]
TILE_FACTORY_SCRIPTS = REPO / "tools" / "tile-factory" / "scripts"
if str(TILE_FACTORY_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(TILE_FACTORY_SCRIPTS))

from common import load_config  # type: ignore
from corner_wang_topology import (  # type: ignore
    topology_grid_from_tilemap_json,
)
from tile_texture_render import (  # type: ignore
    V1_TOPOLOGIES,
    load_texture_cache,
)

TILEMAP_PATH = REPO / "docs" / "mediterranean_recursive_tilemap_wang16_1px.json"
MASK_PATH = REPO / "docs" / "mediterranean_recursive_tilemap_wang16_1px_mask.png"
CHUNKS_DIR = REPO / "docs" / "maps" / "chunks"
MANIFEST_PATH = REPO / "data" / "maps" / "chunk_manifest.json"
CHART_INDEX = REPO / "docs" / "chart_area_tilemaps_and_maps" / "chart_area_index.json"

LOG_W = 2000
LOG_H = 1000
FULL_LAND = "totally_land"
FULL_SEA = "totally_sea"

SEA_RGB = (30, 80, 120)
LAND_RGB = (190, 170, 130)
COAST_PALETTE = (
    (200, 120, 80),
    (220, 140, 90),
    (240, 160, 100),
    (180, 100, 70),
    (160, 90, 60),
    (210, 150, 95),
    (170, 110, 75),
    (230, 170, 110),
)


def _topology_index_grid_from_tilemap(tilemap_path: Path) -> np.ndarray:
    """Resolve corner-Wang cells to strict Wang16 shore ids, then map to texture indices."""
    topo_names = ["totally_sea"] + [name for name in sorted(V1_TOPOLOGIES) if name != "totally_sea"]
    topo_index = {name: i for i, name in enumerate(topo_names)}
    default_idx = topo_index["totally_sea"]
    topo_grid = topology_grid_from_tilemap_json(tilemap_path, width=LOG_W, height=LOG_H)
    idx = np.full((LOG_H, LOG_W), default_idx, dtype=np.uint8)
    for y in range(LOG_H):
        for x in range(LOG_W):
            name = str(topo_grid[y, x])
            idx[y, x] = topo_index.get(name, default_idx)
    return idx


def _load_texture_lut(
    *,
    biome: str,
    season: str,
    variation: int,
    generation: int | None,
    pool: str,
    cell_px: int,
) -> np.ndarray:
    textures = load_texture_cache(
        biome,
        season,
        variation,
        generation=generation,
        cell_px=cell_px,
        pool=pool,
    )
    if not textures:
        raise FileNotFoundError(
            f"No textures for biome={biome} season={season} pool={pool} variation=v{variation:02d}"
        )
    topo_names = ["totally_sea"] + [name for name in sorted(V1_TOPOLOGIES) if name != "totally_sea"]
    fallback = textures.get("totally_sea") or textures.get("totally_land")
    if fallback is None:
        fallback = Image.new("RGB", (cell_px, cell_px), SEA_RGB)
    lut = np.zeros((len(topo_names), cell_px, cell_px, 3), dtype=np.uint8)
    for i, name in enumerate(topo_names):
        img = textures.get(name, fallback)
        arr = np.asarray(img, dtype=np.uint8)
        if arr.shape[0] != cell_px or arr.shape[1] != cell_px:
            arr = np.asarray(
                Image.fromarray(arr, mode="RGB").resize((cell_px, cell_px), Image.Resampling.LANCZOS),
                dtype=np.uint8,
            )
        lut[i] = arr
    return lut


def _render_chunk_rgb(chunk_topology: np.ndarray, texture_lut: np.ndarray) -> np.ndarray:
    # chunk_topology: [tile_h, tile_w], lut: [topologies, cell_px, cell_px, 3]
    patches = texture_lut[chunk_topology]  # [tile_h, tile_w, cell_px, cell_px, 3]
    return patches.transpose(0, 2, 1, 3, 4).reshape(
        chunk_topology.shape[0] * texture_lut.shape[1],
        chunk_topology.shape[1] * texture_lut.shape[2],
        3,
    )


def build_tile_pixel_chunks(
    *,
    tilemap_path: Path = TILEMAP_PATH,
    chunks_dir: Path = CHUNKS_DIR,
    manifest_path: Path = MANIFEST_PATH,
    chunk_tile_size: int = 128,
    cell_px: int = 4,
    biome: str | None = None,
    season: str = "summer",
    variation: int = 1,
    generation: int | None = None,
    pool: str = "approved",
    webp_quality: int = 85,
) -> dict:
    if not tilemap_path.is_file():
        raise FileNotFoundError(tilemap_path)

    cfg = load_config()
    biome_id = str(biome or cfg.get("biome", "sparse_olive"))
    cell_px = max(1, int(cell_px))
    print(f"Loading tilemap {tilemap_path.name} …")
    topo_grid = _topology_index_grid_from_tilemap(tilemap_path)
    texture_lut = _load_texture_lut(
        biome=biome_id,
        season=season,
        variation=variation,
        generation=generation,
        pool=pool,
        cell_px=cell_px,
    )
    chunks_dir.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    cx_max = math.ceil(LOG_W / chunk_tile_size)
    cy_max = math.ceil(LOG_H / chunk_tile_size)
    entries: list[dict] = []

    for cy in range(cy_max):
        for cx in range(cx_max):
            x0 = cx * chunk_tile_size
            y0 = cy * chunk_tile_size
            x1 = min(x0 + chunk_tile_size, LOG_W)
            y1 = min(y0 + chunk_tile_size, LOG_H)
            topo_crop = topo_grid[y0:y1, x0:x1]
            # Pad edge chunks to full chunk size for consistent UV mapping.
            if topo_crop.shape[0] != chunk_tile_size or topo_crop.shape[1] != chunk_tile_size:
                padded_topo = np.zeros((chunk_tile_size, chunk_tile_size), dtype=np.uint8)
                padded_topo[0 : topo_crop.shape[0], 0 : topo_crop.shape[1]] = topo_crop
                topo_crop = padded_topo
            crop = _render_chunk_rgb(topo_crop, texture_lut)
            rel = Path("docs/maps/chunks") / f"tile_{cx}_{cy}.webp"
            out = REPO / rel
            Image.fromarray(crop, mode="RGB").save(
                out, format="WEBP", quality=webp_quality, method=6
            )
            entries.append(
                {
                    "id": f"{cx}_{cy}",
                    "cx": cx,
                    "cy": cy,
                    "path": f"res://{rel.as_posix()}",
                    "x0": x0,
                    "y0": y0,
                    "x1": x1,
                    "y1": y1,
                    "tile_w": x1 - x0,
                    "tile_h": y1 - y0,
                }
            )

    chart_meta: list[dict] = []
    if CHART_INDEX.is_file():
        index = json.loads(CHART_INDEX.read_text(encoding="utf-8"))
        for area in index.get("chart_areas", []):
            if isinstance(area, dict):
                chart_meta.append(
                    {
                        "id": str(area.get("id", "")),
                        "name": str(area.get("name", "")),
                        "bounds": area.get("bounds"),
                    }
                )

    manifest = {
        "schema": 3,
        "layout": "tile_pixels",
        "tile_size": cell_px,
        "chunk_tile_size": chunk_tile_size,
        "source_tilemap": tilemap_path.name,
        "source_mask": MASK_PATH.name if MASK_PATH.is_file() else "",
        "source_biome": biome_id,
        "source_season": season,
        "source_variation": variation,
        "source_pool": pool,
        "world_width": LOG_W,
        "world_height": LOG_H,
        "logical_width": LOG_W,
        "logical_height": LOG_H,
        "chunk_count_x": cx_max,
        "chunk_count_y": cy_max,
        "chart_areas": chart_meta,
        "chunks": entries,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(entries)} tile chunks ({chunk_tile_size}×{chunk_tile_size} tiles each)")
    print(f"Manifest: {manifest_path}")
    return manifest


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tilemap", type=Path, default=TILEMAP_PATH)
    ap.add_argument("--chunk-tile-size", type=int, default=128)
    ap.add_argument("--cell-px", type=int, default=4, help="Rendered pixels per logical map tile")
    ap.add_argument("--biome", type=str, default=None)
    ap.add_argument("--season", type=str, default="summer")
    ap.add_argument("--variation", type=int, default=1)
    ap.add_argument("--generation", type=int, default=None)
    ap.add_argument("--pool", choices=("approved", "pending"), default="approved")
    ap.add_argument("--chunks-dir", type=Path, default=CHUNKS_DIR)
    ap.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    args = ap.parse_args()
    build_tile_pixel_chunks(
        tilemap_path=args.tilemap,
        chunks_dir=args.chunks_dir,
        manifest_path=args.manifest,
        chunk_tile_size=max(16, int(args.chunk_tile_size)),
        cell_px=max(1, int(args.cell_px)),
        biome=args.biome,
        season=args.season,
        variation=max(1, int(args.variation)),
        generation=args.generation,
        pool=args.pool,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

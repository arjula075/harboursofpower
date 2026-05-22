#!/usr/bin/env python3
"""Slice a master map image into world-pixel chunks and write chunk_manifest.json.

Default master: docs/mediterranean_recursive_tilemap_wang16_1px_mask.png (2000x1000).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parents[1]
DEFAULT_MASTER = REPO / "docs" / "mediterranean_recursive_tilemap_wang16_1px_mask.png"
DEFAULT_CHUNKS = REPO / "docs" / "maps" / "chunks"
DEFAULT_MANIFEST = REPO / "data" / "maps" / "chunk_manifest.json"
LOGICAL_W = 2000
LOGICAL_H = 1000


def slice_master(
    master_path: Path,
    *,
    chunk_size: int,
    chunks_dir: Path,
    manifest_path: Path,
    logical_width: int = LOGICAL_W,
    logical_height: int = LOGICAL_H,
) -> dict:
    im = Image.open(master_path).convert("RGB")
    world_w, world_h = im.size
    chunks_dir.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    entries: list[dict] = []
    cx_max = (world_w + chunk_size - 1) // chunk_size
    cy_max = (world_h + chunk_size - 1) // chunk_size
    for cy in range(cy_max):
        for cx in range(cx_max):
            x0 = cx * chunk_size
            y0 = cy * chunk_size
            x1 = min(x0 + chunk_size, world_w)
            y1 = min(y0 + chunk_size, world_h)
            if x1 <= x0 or y1 <= y0:
                continue
            crop = im.crop((x0, y0, x1, y1))
            rel = Path("docs/maps/chunks") / f"med_{cx}_{cy}.webp"
            out = REPO / rel
            crop.save(out, format="WEBP", quality=90)
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
                }
            )

    manifest = {
        "schema": 1,
        "source_master": master_path.name,
        "world_width": world_w,
        "world_height": world_h,
        "logical_width": logical_width,
        "logical_height": logical_height,
        "chunk_size": chunk_size,
        "chunks": entries,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_MASTER)
    parser.add_argument("--chunk-size", type=int, default=2048)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_CHUNKS)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args()
    if not args.input.is_file():
        raise SystemExit(f"Missing master image: {args.input}")
    manifest = slice_master(
        args.input,
        chunk_size=args.chunk_size,
        chunks_dir=args.output_dir,
        manifest_path=args.manifest,
    )
    print(f"Wrote {len(manifest['chunks'])} chunk(s) -> {args.output_dir}")
    print(f"Manifest: {args.manifest} ({manifest['world_width']}x{manifest['world_height']})")


if __name__ == "__main__":
    main()

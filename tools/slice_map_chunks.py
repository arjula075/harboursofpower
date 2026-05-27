#!/usr/bin/env python3
"""Build chunk_manifest.json for in-game sailing map.

Modes:
  --by-chart-area (default) — one texture per chart_area_index.json region (wang16 *_map.png).
  --grid — legacy fixed grid (2048 px tiles) from the full master mask.

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
CHART_INDEX = REPO / "docs" / "chart_area_tilemaps_and_maps" / "chart_area_index.json"
WANG16_MAPS = REPO / "docs" / "chart_area_tilemaps_and_maps_wang16_1px"
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


def slice_chart_areas(
    *,
    index_path: Path = CHART_INDEX,
    map_dir: Path = WANG16_MAPS,
    master_path: Path = DEFAULT_MASTER,
    chunks_dir: Path = DEFAULT_CHUNKS,
    manifest_path: Path = DEFAULT_MANIFEST,
    logical_width: int = LOGICAL_W,
    logical_height: int = LOGICAL_H,
) -> dict:
    """One sailing-map chunk per chart area (bounds = logical map pixels)."""
    if not index_path.is_file():
        raise FileNotFoundError(index_path)

    index = json.loads(index_path.read_text(encoding="utf-8"))
    areas: list[dict] = index.get("chart_areas", [])
    master: Image.Image | None = None
    if master_path.is_file():
        master = Image.open(master_path).convert("RGB")

    chunks_dir.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    entries: list[dict] = []
    world_w = logical_width
    world_h = logical_height

    if master is not None:
        rel_base = Path("docs/maps/chunks") / "chart_baseline.webp"
        out_base = REPO / rel_base
        master.save(out_base, format="WEBP", quality=90)
        entries.append(
            {
                "id": "_baseline",
                "chart_area_id": "",
                "name": "Open sea baseline",
                "path": f"res://{rel_base.as_posix()}",
                "x0": 0,
                "y0": 0,
                "x1": world_w,
                "y1": world_h,
                "pixel_area": world_w * world_h,
                "draw_order": 0,
            }
        )
        print(f"  _baseline: {world_w}x{world_h} -> {rel_base.name}")

    for area in areas:
        aid = str(area["id"])
        bounds = area["bounds"]
        x0, y0, x1, y1 = (
            int(bounds["x0"]),
            int(bounds["y0"]),
            int(bounds["x1"]),
            int(bounds["y1"]),
        )
        w, h = x1 - x0, y1 - y0
        if w <= 0 or h <= 0:
            continue

        area_png = map_dir / f"{aid}_map.png"
        if area_png.is_file():
            crop = Image.open(area_png).convert("RGB")
        elif master is not None:
            crop = master.crop((x0, y0, x1, y1))
        else:
            print(f"  skip {aid}: no map png and no master mask")
            continue

        if crop.size != (w, h):
            crop = crop.resize((w, h), Image.Resampling.LANCZOS)

        rel = Path("docs/maps/chunks") / f"chart_{aid}.webp"
        out = REPO / rel
        crop.save(out, format="WEBP", quality=90)
        pixel_area = w * h
        entries.append(
            {
                "id": aid,
                "chart_area_id": aid,
                "name": str(area.get("name", aid)),
                "path": f"res://{rel.as_posix()}",
                "x0": x0,
                "y0": y0,
                "x1": x1,
                "y1": y1,
                "pixel_area": pixel_area,
                "draw_order": 1,
            }
        )
        print(f"  {aid}: {w}x{h} -> {rel.name}")

    # Baseline first (open sea), then coast regions smallest-on-top in overlaps.
    entries.sort(
        key=lambda e: (
            int(e.get("draw_order", 1)),
            int(e.get("pixel_area", 0)),
        )
    )

    chart_meta = [
        {
            "id": str(a["id"]),
            "name": str(a.get("name", a["id"])),
            "description": str(a.get("description", "")),
            "bounds": a["bounds"],
        }
        for a in areas
    ]

    manifest = {
        "schema": 2,
        "layout": "chart_area",
        "source_master": master_path.name if master_path.is_file() else "",
        "world_width": logical_width,
        "world_height": logical_height,
        "logical_width": logical_width,
        "logical_height": logical_height,
        "chart_areas": chart_meta,
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
    parser.add_argument(
        "--chart-areas",
        action="store_true",
        help="Per-chart-area coastal cuts (legacy; open sea uses baseline)",
    )
    parser.add_argument(
        "--grid",
        action="store_true",
        help="Single full-map image chunk (legacy)",
    )
    args = parser.parse_args()

    if not args.chart_areas and not args.grid:
        from build_tile_pixel_chunks import build_tile_pixel_chunks

        build_tile_pixel_chunks(
            chunks_dir=args.output_dir,
            manifest_path=args.manifest,
        )
        return

    if args.grid:
        if not args.input.is_file():
            raise SystemExit(f"Missing master image: {args.input}")
        manifest = slice_master(
            args.input,
            chunk_size=args.chunk_size,
            chunks_dir=args.output_dir,
            manifest_path=args.manifest,
        )
    else:
        manifest = slice_chart_areas(
            master_path=args.input,
            chunks_dir=args.output_dir,
            manifest_path=args.manifest,
        )

    print(f"Wrote {len(manifest['chunks'])} chunk(s) -> {args.output_dir}")
    print(f"Manifest: {args.manifest} ({manifest['world_width']}x{manifest['world_height']})")


if __name__ == "__main__":
    main()

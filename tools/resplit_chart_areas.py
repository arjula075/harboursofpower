#!/usr/bin/env python3
"""Re-cut per-chart-area tilemaps after chart_area_index.json bounds change.

Writes:
  - docs/chart_area_tilemaps_and_maps_wang16_1px/{area}_*
  - docs/chart_area_tilemaps_and_maps/shore_fixed/{area}_tilemap.json

Run from repo root after editing chart_area_index.json:
  .venv/bin/python tools/resplit_chart_areas.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
INDEX_PATH = REPO / "docs" / "chart_area_tilemaps_and_maps" / "chart_area_index.json"
WANG16_FULL = REPO / "docs" / "mediterranean_recursive_tilemap_wang16_1px.json"
WANG16_MASK = REPO / "docs" / "mediterranean_recursive_tilemap_wang16_1px_mask.png"
WANG16_CHART = REPO / "docs" / "chart_area_tilemaps_and_maps_wang16_1px"
SHORE3_FULL = REPO / "docs" / "mediterranean_recursive_tilemap_aegean_illyrian_restored.json"
SHORE_FIXED = REPO / "docs" / "chart_area_tilemaps_and_maps" / "shore_fixed"

# Import wang16 chart export helpers
sys.path.insert(0, str(REPO / "tools"))
from build_recursive_tilemap_wang16_1px import write_chart_area_exports  # noqa: E402
import numpy as np
from PIL import Image


def load_land_mask() -> np.ndarray:
    rgb = np.array(Image.open(WANG16_MASK).convert("RGB"))
    return (rgb[:, :, 0] > 140) & (rgb[:, :, 2] < 130)


def split_shore_fixed(index: dict, obsolete_ids: set[str]) -> None:
    data = json.loads(SHORE3_FULL.read_text(encoding="utf-8"))
    tiles = data.get("tiles", [])
    template_path = SHORE_FIXED / "iberia_gaul_tilemap.json"
    template = json.loads(template_path.read_text(encoding="utf-8")) if template_path.is_file() else {}

    for aid in obsolete_ids:
        old = SHORE_FIXED / f"{aid}_tilemap.json"
        if old.is_file():
            old.unlink()
            print(f"  removed obsolete {old.name}")

    for area in index["chart_areas"]:
        aid = str(area["id"])
        bounds = area["bounds"]
        x0, y0, x1, y1 = bounds["x0"], bounds["y0"], bounds["x1"], bounds["y1"]
        area_tiles = [t for t in tiles if x0 <= int(t["x"]) < x1 and y0 <= int(t["y"]) < y1]
        counts = Counter(t["tile"] for t in area_tiles)
        out = {
            "chart_area": {
                "id": aid,
                "name": area.get("name", aid),
                "description": area.get("description", ""),
                "bounds": bounds,
            },
            "coordinate_system": data.get("coordinate_system", {}),
            "tile_counts": dict(sorted(counts.items())),
            "tiles": area_tiles,
        }
        if template:
            for key in ("classification_pipeline", "strict_wang16"):
                if key in template:
                    out[key] = template[key]
        path = SHORE_FIXED / f"{aid}_tilemap.json"
        path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"  shore_fixed/{aid}: {len(area_tiles):,} cells")


def main() -> int:
    if not INDEX_PATH.is_file():
        print(f"Missing {INDEX_PATH}", file=sys.stderr)
        return 1

    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    area_ids = {str(a["id"]) for a in index["chart_areas"]}

    # Obsolete chart-area files (removed from index)
    obsolete = set()
    for path in WANG16_CHART.glob("*_tilemap.json"):
        aid = path.name.replace("_tilemap.json", "")
        if aid not in area_ids:
            obsolete.add(aid)
    for path in SHORE_FIXED.glob("*_tilemap.json"):
        aid = path.name.replace("_tilemap.json", "")
        if aid not in area_ids:
            obsolete.add(aid)

    print("=== Wang-16 1px chart cuts ===")
    if not WANG16_FULL.is_file():
        print(f"Missing {WANG16_FULL}", file=sys.stderr)
        return 1
    full = json.loads(WANG16_FULL.read_text(encoding="utf-8"))
    tiles = full.get("tiles", [])
    land = load_land_mask()
    for aid in obsolete:
        for pat in (f"{aid}_tilemap.json", f"{aid}_map.png"):
            p = WANG16_CHART / pat
            if p.is_file():
                p.unlink()
                print(f"  removed obsolete {pat}")
    write_chart_area_exports(
        WANG16_CHART,
        index,
        tiles,
        land,
        src_label="mediterranean_recursive_tilemap_wang16_1px.json",
        source_mode="resplit_chart_areas",
    )

    print("\n=== shore_fixed (3px) chart cuts ===")
    if SHORE3_FULL.is_file():
        split_shore_fixed(index, obsolete)
    else:
        print(f"  skip: missing {SHORE3_FULL.name}")

    (WANG16_CHART / "chart_area_index.json").write_text(
        json.dumps(
            {
                "source_tilemap": "mediterranean_recursive_tilemap_wang16_1px.json",
                "note": index.get("note", ""),
                "chart_areas": index["chart_areas"],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print("\n=== sailing map chunks (1px per tile) ===")
    from build_tile_pixel_chunks import build_tile_pixel_chunks

    build_tile_pixel_chunks()

    print("\nDone. Restart Godot / port_map_editor; hard-refresh browser.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

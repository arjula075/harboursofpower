#!/usr/bin/env python3
"""Split the ship reference spritesheet into per-class PNGs + ship_visuals_manifest.json.

Source layout (left-to-right):
  row 0: italic_coastal, greek_merchant, phoenician_deep, sicilian_grain, greek_trireme
  row 1: carthage_heavy_galley, levantine_luxury, illyrian_raider, egyptian_river_hybrid
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "docs" / "2a72b7d4-3770-4ea0-a0d1-d691d1348469.png"
OUT_DIR = ROOT / "assets" / "ships"
MANIFEST_PATH = ROOT / "data" / "ship_visuals_manifest.json"
SHIPS_PATH = ROOT / "data" / "ships.json"

# Grid tuned for 1536x1024 sheet; each cell is trimmed to non-background pixels.
LAYOUT = {
    "sheet_size": [1536, 1024],
    "rows": [
        {
            "y0": 36,
            "y1": 468,
            "ids": [
                "italic_coastal",
                "greek_merchant",
                "phoenician_deep",
                "sicilian_grain",
                "greek_trireme",
            ],
        },
        {
            "y0": 532,
            "y1": 968,
            "ids": [
                "carthage_heavy_galley",
                "levantine_luxury",
                "illyrian_raider",
                "egyptian_river_hybrid",
            ],
        },
    ],
}

# Art-derived metadata (gameplay stats remain in data/ships.json).
VISUAL_META: dict[str, dict] = {
    "italic_coastal": {
        "propulsion": "sail",
        "size_tier": "small",
        "has_sail": True,
        "has_oars": False,
        "oar_pairs": 0,
        "notes": "Compact coastal trader; open deck cargo.",
    },
    "greek_merchant": {
        "propulsion": "sail",
        "size_tier": "medium",
        "has_sail": True,
        "has_oars": False,
        "oar_pairs": 0,
        "notes": "Wide roundship; deck crates.",
    },
    "phoenician_deep": {
        "propulsion": "sail",
        "size_tier": "medium",
        "has_sail": True,
        "has_oars": False,
        "oar_pairs": 0,
        "notes": "Long narrow deep-water hull.",
    },
    "sicilian_grain": {
        "propulsion": "sail",
        "size_tier": "large",
        "has_sail": False,
        "has_oars": False,
        "oar_pairs": 0,
        "notes": "Open grain hold; minimal rigging shown.",
    },
    "greek_trireme": {
        "propulsion": "oar",
        "size_tier": "large",
        "has_sail": False,
        "has_oars": True,
        "oar_pairs": 12,
        "notes": "Ram warship; banks of oars, no sail.",
    },
    "carthage_heavy_galley": {
        "propulsion": "oar",
        "size_tier": "large",
        "has_sail": False,
        "has_oars": True,
        "oar_pairs": 10,
        "notes": "Heavy galley; raised fighting decks.",
    },
    "levantine_luxury": {
        "propulsion": "sail",
        "size_tier": "medium",
        "has_sail": True,
        "has_oars": False,
        "oar_pairs": 0,
        "notes": "Purple cabin / awning on deck.",
    },
    "illyrian_raider": {
        "propulsion": "oar",
        "size_tier": "small",
        "has_sail": False,
        "has_oars": True,
        "oar_pairs": 4,
        "notes": "Sleek raider; few oar pairs.",
    },
    "egyptian_river_hybrid": {
        "propulsion": "sail_and_oar",
        "size_tier": "medium",
        "has_sail": True,
        "has_oars": True,
        "oar_pairs": 3,
        "notes": "Square sail plus stern oars; river–sea hybrid.",
    },
}


def _content_mask(arr: np.ndarray) -> np.ndarray:
    rgb = arr[:, :, :3]
    alpha = arr[:, :, 3]
    return (rgb.max(axis=2) > 25) & (alpha > 10)


def _trim_box(mask: np.ndarray, pad: int = 6) -> tuple[int, int, int, int] | None:
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return None
    x0, x1 = int(xs.min()), int(xs.max())
    y0, y1 = int(ys.min()), int(ys.max())
    h, w = mask.shape
    return (
        max(0, x0 - pad),
        max(0, y0 - pad),
        min(w - 1, x1 + pad),
        min(h - 1, y1 + pad),
    )


def _split_row_cells(x0: int, x1: int, n: int) -> list[tuple[int, int]]:
    width = x1 - x0
    cell = width / n
    return [(int(x0 + i * cell), int(x0 + (i + 1) * cell)) for i in range(n)]


def extract(source: Path) -> list[dict]:
    im = Image.open(source).convert("RGBA")
    w, h = im.size
    arr = np.array(im)
    mask_full = _content_mask(arr)

    objects: list[dict] = []
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for row in LAYOUT["rows"]:
        y0, y1 = row["y0"], row["y1"]
        ids: list[str] = row["ids"]
        x_margin = 24
        cells = _split_row_cells(x_margin, w - x_margin, len(ids))
        for sid, (cx0, cx1) in zip(ids, cells):
            cell_mask = mask_full[y0:y1, cx0:cx1]
            box = _trim_box(cell_mask)
            if box is None:
                print(f"WARN: empty cell for {sid}", file=sys.stderr)
                continue
            lx0, ly0, lx1, ly1 = box
            gx0, gy0 = cx0 + lx0, y0 + ly0
            gx1, gy1 = cx0 + lx1, y0 + ly1
            crop = im.crop((gx0, gy0, gx1 + 1, gy1 + 1))
            out_path = OUT_DIR / f"{sid}.png"
            crop.save(out_path, optimize=True)
            tw, th = crop.size
            meta = VISUAL_META.get(sid, {})
            objects.append(
                {
                    "id": sid,
                    "ship_class_id": sid,
                    "texture": f"res://assets/ships/{sid}.png",
                    "source_sheet": str(source.relative_to(ROOT)).replace("\\", "/"),
                    "source_rect": [gx0, gy0, gx1 + 1, gy1 + 1],
                    "size_px": [tw, th],
                    "facing": "east",
                    "pivot_norm": [0.5, 0.5],
                    "map_scale": _map_scale_for_tier(meta.get("size_tier", "medium")),
                    **meta,
                }
            )
            print(f"{sid}: {tw}x{th} -> {out_path.relative_to(ROOT)}")
    return objects


def _map_scale_for_tier(tier: str) -> float:
    return {"small": 0.85, "medium": 1.0, "large": 1.15}.get(tier, 1.0)


def main() -> int:
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SOURCE
    if not source.is_file():
        print(f"Missing source image: {source}", file=sys.stderr)
        return 1

    with SHIPS_PATH.open(encoding="utf-8") as f:
        ship_ids = {row["id"] for row in json.load(f).get("ships", [])}

    objects = extract(source)
    extracted_ids = {o["id"] for o in objects}
    missing = sorted(ship_ids - extracted_ids)
    extra = sorted(extracted_ids - ship_ids)
    if missing:
        print(f"WARN: ships.json ids without sprites: {missing}", file=sys.stderr)
    if extra:
        print(f"WARN: sprites without ships.json ids: {extra}", file=sys.stderr)

    manifest = {
        "version": 1,
        "source_sheet": str(source.relative_to(ROOT)).replace("\\", "/"),
        "sheet_size": list(Image.open(source).size),
        "layout": LAYOUT,
        "objects": objects,
    }
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with MANIFEST_PATH.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")
    print(f"Wrote {len(objects)} ship visual objects -> {MANIFEST_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

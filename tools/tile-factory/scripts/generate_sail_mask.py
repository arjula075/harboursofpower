"""Procedural sail masks from topology (white=navigable, black=blocked)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

from common import band_px, load_config, topology_by_id


def mask_for_topology(topology_id: str, size: int, band: int) -> Image.Image:
    img = Image.new("L", (size, size), 0)
    topo = topology_by_id(topology_id)
    tc = topo.get("terrain_class", "land")
    if tc == "sea":
        return Image.new("L", (size, size), 255)
    if tc == "land":
        return img

    draw = ImageDraw.Draw(img)
    w, h = size, size
    hint = topo.get("sail_mask", "")

    if hint == "sea_south":
        draw.rectangle((0, h // 2, w, h), fill=255)
    elif hint == "sea_north":
        draw.rectangle((0, 0, w, h // 2), fill=255)
    elif hint == "sea_east":
        draw.rectangle((w // 2, 0, w, h), fill=255)
    elif hint == "sea_west":
        draw.rectangle((0, 0, w // 2, h), fill=255)
    elif hint == "sea_se_corner":
        draw.polygon([(w - 1, h // 2), (w - 1, h - 1), (w // 2, h - 1)], fill=255)
    elif hint == "sea_sw_corner":
        draw.polygon([(0, h // 2), (0, h - 1), (w // 2, h - 1)], fill=255)
    elif hint == "sea_ne_corner":
        draw.polygon([(w - 1, h // 2), (w - 1, 0), (w // 2, 0)], fill=255)
    elif hint == "sea_nw_corner":
        draw.polygon([(0, h // 2), (0, 0), (w // 2, 0)], fill=255)
    elif hint == "sea_channel_vertical":
        draw.rectangle((w // 4, 0, 3 * w // 4, h), fill=255)
    elif hint == "sea_channel_horizontal":
        draw.rectangle((0, h // 4, w, 3 * h // 4), fill=255)
    else:
        draw.rectangle((0, h // 2, w, h), fill=255)

    # Soften inner edge slightly
    return img


def write_mask_for_tile(tile_webp: Path, topology_id: str, cfg: dict) -> Path:
    size = int(cfg["tile_size"])
    band = band_px(cfg)
    mask = mask_for_topology(topology_id, size, band)
    out = tile_webp.with_suffix(".sail.png")
    mask.save(out)
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    args = parser.parse_args()
    cfg = load_config()
    with args.spec.open(encoding="utf-8") as f:
        spec = json.load(f)
    if spec["kind"] != "terrain":
        print("Sail masks only for terrain")
        return 0
    pending = Path(spec["pending_path"])
    if not pending.is_file():
        print(f"Missing pending tile: {pending}")
        return 1
    out = write_mask_for_tile(pending, spec["topology"], cfg)
    print(f"Sail mask -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

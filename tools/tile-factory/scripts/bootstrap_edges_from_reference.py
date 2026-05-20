"""Build edge strips by cropping the photorealistic reference coast image."""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

from common import band_px, edge_strip_path, load_config

REFERENCE = Path(__file__).resolve().parents[1] / "style" / "reference_coast.png"


def resize_band(strip: Image.Image, size: int, band: int) -> Image.Image:
    return strip.resize((size, band), Image.Resampling.LANCZOS)


def main() -> int:
    cfg = load_config()
    biome = cfg["biome"]
    season = cfg["season"]
    size = int(cfg["tile_size"])
    band = band_px(cfg)

    if not REFERENCE.is_file():
        print(f"Missing reference: {REFERENCE}", file=sys.stderr)
        return 1

    ref = Image.open(REFERENCE).convert("RGB")
    w, h = ref.size

    # Reference layout: sea on left, rocky scrubland on right, vertical shoreline ~40% from left.
    sea_sea = resize_band(ref.crop((0, 0, w // 3, band)), size, band)
    land_land = resize_band(ref.crop((2 * w // 3, 0, w, band)), size, band)

    coast_col = ref.crop((w // 3 - 20, 0, 2 * w // 3 + 20, h)).resize((size, size), Image.Resampling.LANCZOS)
    coast_rot = coast_col.transpose(Image.Transpose.ROTATE_90)
    mid = size // 2
    land_sea = coast_rot.crop((0, mid - band // 2, size, mid + band // 2))
    sea_land = land_sea.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

    out_dir = edge_strip_path(biome, season, "sea_sea").parent
    out_dir.mkdir(parents=True, exist_ok=True)
    sea_sea.save(edge_strip_path(biome, season, "sea_sea"))
    land_land.save(edge_strip_path(biome, season, "land_land"))
    land_sea.save(edge_strip_path(biome, season, "land_sea"))
    sea_land.save(edge_strip_path(biome, season, "sea_land"))
    print(f"Bootstrapped edge strips from {REFERENCE.name} -> {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Apply seam correction: soft feather blend of edge strips (or pass-through raw)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image

from common import band_px, edge_strip_path, load_config, topology_by_id


def load_strip(biome: str, season: str, edge_kind: str, size: int, band: int) -> Image.Image:
    path = edge_strip_path(biome, season, edge_kind)
    if not path.is_file():
        raise FileNotFoundError(f"Missing edge strip: {path}")
    img = Image.open(path).convert("RGB")
    if img.size != (size, band):
        img = img.resize((size, band), Image.Resampling.LANCZOS)
    return img


def orient_strip(strip: Image.Image, side: str) -> Image.Image:
    if side == "north":
        return strip
    if side == "south":
        return strip.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    if side == "east":
        return strip.transpose(Image.Transpose.ROTATE_270)
    if side == "west":
        return strip.transpose(Image.Transpose.ROTATE_90)
    return strip


def _blend_band(
    base: Image.Image,
    strip: Image.Image,
    side: str,
    band: int,
    strength: float,
) -> None:
    """Feather-blend strip into the outer band (avoids hard colored frames)."""
    size = base.size[0]
    px = base.load()
    sp = strip.load()
    for i in range(band):
        t = (1.0 - i / max(band - 1, 1)) * strength
        if side == "north":
            y = i
            for x in range(size):
                for c in range(3):
                    px[x, y] = int(sp[x, i][c] * t + px[x, y][c] * (1.0 - t))
        elif side == "south":
            y = size - band + i
            sy = strip.height - band + i
            for x in range(size):
                for c in range(3):
                    px[x, y] = int(sp[x, sy][c] * t + px[x, y][c] * (1.0 - t))
        elif side == "west":
            x = i
            for y in range(size):
                for c in range(3):
                    px[x, y] = int(sp[i, y][c] * t + px[x, y][c] * (1.0 - t))
        elif side == "east":
            x = size - band + i
            sx = strip.width - band + i
            for y in range(size):
                for c in range(3):
                    px[x, y] = int(sp[sx, y][c] * t + px[x, y][c] * (1.0 - t))


def compose_tile(
    raw_path: Path,
    out_path: Path,
    biome: str,
    season: str,
    topology_id: str,
) -> None:
    cfg = load_config()
    size = int(cfg["tile_size"])
    band = band_px(cfg)
    mode = cfg.get("edge_compose_mode", "soft")
    strength = float(cfg.get("edge_blend_strength", 0.35))

    base = Image.open(raw_path).convert("RGB")
    if base.size != (size, size):
        base = base.resize((size, size), Image.Resampling.LANCZOS)
    out = base.copy()

    if mode == "none":
        out_path.parent.mkdir(parents=True, exist_ok=True)
        lossless_png = out_path.with_suffix(".composed.png")
        out.save(lossless_png)
        out.save(out_path, format="WEBP", lossless=True)
        return

    topo = topology_by_id(topology_id)
    edges = topo["edges"]

    if mode == "soft":
        for side, edge_kind in edges.items():
            strip = orient_strip(load_strip(biome, season, edge_kind, size, band), side)
            _blend_band(out, strip, side, band, strength)
    else:
        # Legacy hard paste (not recommended)
        for side, edge_kind in edges.items():
            strip = orient_strip(load_strip(biome, season, edge_kind, size, band), side)
            if side == "north":
                out.paste(strip, (0, 0))
            elif side == "south":
                out.paste(strip, (0, size - band))
            elif side == "west":
                out.paste(strip, (0, 0))
            elif side == "east":
                out.paste(strip, (size - band, 0))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    lossless_png = out_path.with_suffix(".composed.png")
    out.save(lossless_png)
    out.save(out_path, format="WEBP", lossless=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Compose / soft-seam terrain tile")
    parser.add_argument("spec", type=Path, help="Path to tile spec JSON")
    args = parser.parse_args()
    with args.spec.open(encoding="utf-8") as f:
        spec = json.load(f)
    raw = Path(spec["raw_path"])
    out = Path(spec["pending_path"])
    compose_tile(raw, out, spec["biome"], spec["season"], spec["topology"])
    print(f"Composed -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Procedural open-sea tiles matched to shore water color; seamless edges."""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Iterable

from PIL import Image

from common import FACTORY_ROOT, band_px, edge_strip_path, load_config, repo_path, spec_path


def _water_pixels(rgb: Image.Image, box: tuple[int, int, int, int]) -> list[tuple[int, int, int]]:
    crop = rgb.crop(box)
    out: list[tuple[int, int, int]] = []
    for r, g, b in crop.getdata():
        if b > r + 4 and b >= g - 15 and b > 25:
            out.append((r, g, b))
    return out


def _median_rgb(pixels: Iterable[tuple[int, int, int]]) -> tuple[int, int, int] | None:
    px = list(pixels)
    if not px:
        return None
    return tuple(int(statistics.median([p[i] for p in px])) for i in range(3))


def sample_sea_rgb_from_shores(cfg: dict) -> tuple[int, int, int]:
    """Read sea color from pending shore tiles so open ocean meets coastline."""
    pending = repo_path(cfg["paths"]["pending"])
    biome = cfg["biome"]
    season = cfg["season"]
    samples: list[tuple[int, int, int]] = []

    h_path = pending / biome / season / "horizontal_top_land" / "v01.webp"
    if h_path.is_file():
        im = Image.open(h_path).convert("RGB")
        w, h = im.size
        for box in ((0, h // 2, w, h), (0, h - 24, w, h), (w // 4, 3 * h // 4, 3 * w // 4, h)):
            m = _median_rgb(_water_pixels(im, box))
            if m:
                samples.append(m)

    v_path = pending / biome / season / "vertical_right_land" / "v01.webp"
    if v_path.is_file():
        im = Image.open(v_path).convert("RGB")
        w, h = im.size
        for box in ((0, 0, w // 2, h), (0, 0, 24, h), (w // 4, h // 4, w // 2, 3 * h // 4)):
            m = _median_rgb(_water_pixels(im, box))
            if m:
                samples.append(m)

    if samples:
        return tuple(int(statistics.mean([s[i] for s in samples])) for i in range(3))

    # Fallback: reference coast open water (left third)
    ref = FACTORY_ROOT / "style" / "reference_coast.png"
    if ref.is_file():
        im = Image.open(ref).convert("RGB")
        w, h = im.size
        m = _median_rgb(_water_pixels(im, (0, 0, w // 3, h)))
        if m:
            return m

    return tuple(cfg.get("open_sea_rgb", [10, 45, 52]))


def save_open_sea_rgb(cfg: dict, rgb: tuple[int, int, int]) -> None:
    cfg_path = FACTORY_ROOT / "config.json"
    cfg["open_sea_rgb"] = list(rgb)
    with cfg_path.open("w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
        f.write("\n")


def get_open_sea_rgb(cfg: dict) -> tuple[int, int, int]:
    if "open_sea_rgb" in cfg:
        t = cfg["open_sea_rgb"]
        return (int(t[0]), int(t[1]), int(t[2]))
    return sample_sea_rgb_from_shores(cfg)


def make_uniform_sea(size: int, variation: int, edge_rgb: tuple[int, int, int]) -> Image.Image:
    shifts = [(0, 0, 0), (-1, 1, -1), (1, -1, 1)]
    dr, dg, db = shifts[(variation - 1) % 3]
    interior = (
        max(0, min(255, edge_rgb[0] + dr)),
        max(0, min(255, edge_rgb[1] + dg)),
        max(0, min(255, edge_rgb[2] + db)),
    )
    img = Image.new("RGB", (size, size), interior)
    px = img.load()
    band = 8
    for y in range(size):
        for x in range(size):
            if x < band or x >= size - band or y < band or y >= size - band:
                px[x, y] = edge_rgb
    return img


def publish_spec(spec: dict, img: Image.Image, cfg: dict) -> None:
    size = int(cfg["tile_size"])
    raw = Path(spec["raw_path"])
    pending = Path(spec["pending_path"])
    raw.parent.mkdir(parents=True, exist_ok=True)
    pending.parent.mkdir(parents=True, exist_ok=True)
    if img.size != (size, size):
        img = img.resize((size, size), Image.Resampling.LANCZOS)
    img.save(raw)
    img.save(pending, format="WEBP", lossless=True)
    img.save(pending.with_suffix(".composed.png"))


def sync_edge_strip_sea(biome: str, season: str, rgb: tuple[int, int, int], size: int, band: int) -> None:
    """Update sea_sea strip so compositor (if used) matches open ocean."""
    path = edge_strip_path(biome, season, "sea_sea")
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (size, band), rgb).save(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variations", type=int, nargs="*", default=[1, 2, 3])
    parser.add_argument("--sync-only", action="store_true", help="Only sample shore color into config")
    args = parser.parse_args()
    cfg = load_config()
    rgb = sample_sea_rgb_from_shores(cfg)
    save_open_sea_rgb(cfg, rgb)
    print(f"Open sea RGB (from shores): {rgb}")
    if args.sync_only:
        return 0

    biome = cfg["biome"]
    season = cfg["season"]
    size = int(cfg["tile_size"])
    band = int(cfg["edge_band_px"])
    sync_edge_strip_sea(biome, season, rgb, size, band)

    for v in args.variations:
        tid = f"{biome}/{season}/totally_sea/v{v:02d}"
        sp = spec_path(tid)
        if not sp.is_file():
            print(f"Skip {tid}: no spec")
            continue
        with sp.open(encoding="utf-8") as f:
            spec = json.load(f)
        img = make_uniform_sea(size, v, rgb)
        publish_spec(spec, img, cfg)
        print(f"Uniform sea -> {tid}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Publish raw tiles to pending/ (land anchor, composited shores)."""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from common import load_config, repo_path, spec_path


def resolve_land_anchor(cfg: dict) -> Image.Image | None:
    biome = cfg["biome"]
    season = cfg["season"]
    for root in ("approved", "pending"):
        p = repo_path(f"assets/tiles/{root}/{biome}/{season}/totally_land/v01.webp")
        if p.is_file():
            return Image.open(p).convert("RGB")
    return None


def publish_raw_to_pending(spec: dict, cfg: dict | None = None) -> Path:
    """Copy raw PNG to pending WebP (lossless) + composed PNG."""
    cfg = cfg or load_config()
    raw = Path(spec["raw_path"])
    pending = Path(spec["pending_path"])
    size = int(cfg["tile_size"])
    img = Image.open(raw).convert("RGB")
    if img.size != (size, size):
        img = img.resize((size, size), Image.Resampling.LANCZOS)
    pending.parent.mkdir(parents=True, exist_ok=True)
    img.save(pending, format="WEBP", lossless=True)
    img.save(pending.with_suffix(".composed.png"))
    return pending


def publish_land_anchor_v01(cfg: dict | None = None) -> Path:
    """Publish totally_land/v01 raw as the land anchor in pending/."""
    from generate_sail_mask import write_mask_for_tile

    cfg = cfg or load_config()
    biome = cfg["biome"]
    season = cfg["season"]
    tid = f"{biome}/{season}/totally_land/v01"
    sp = spec_path(tid)
    if not sp.is_file():
        raise FileNotFoundError(f"Missing spec: {tid}")
    with sp.open(encoding="utf-8") as f:
        spec = json.load(f)
    raw = Path(spec["raw_path"])
    if not raw.is_file():
        raise FileNotFoundError(f"Generate land anchor first: {raw}")
    pending = publish_raw_to_pending(spec, cfg)
    write_mask_for_tile(pending, "totally_land", cfg)
    return pending


def publish_composited_shore(
    spec: dict,
    img: Image.Image,
    cfg: dict | None = None,
) -> Path:
    from generate_sail_mask import write_mask_for_tile

    cfg = cfg or load_config()
    pending = Path(spec["pending_path"])
    pending.parent.mkdir(parents=True, exist_ok=True)
    img.save(pending.with_suffix(".composed.png"))
    img.save(pending, format="WEBP", lossless=True)
    write_mask_for_tile(pending, spec["topology"], cfg)
    return pending

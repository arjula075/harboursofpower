"""Publish raw tiles to pending/ (land anchor, composited shores)."""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from common import get_active_generation, load_config, repo_path, spec_path, terrain_asset_relpath, tile_id


def resolve_land_anchor(
    cfg: dict,
    *,
    biome: str | None = None,
    season: str | None = None,
    generation: int | None = None,
) -> Image.Image | None:
    biome = biome or cfg["biome"]
    season = season or cfg["season"]
    generation = generation if generation is not None else get_active_generation(cfg, biome, season)
    rel = terrain_asset_relpath(biome, season, "totally_land", 1, generation=generation, ext=".webp")
    for root in ("approved", "pending"):
        p = repo_path(f"assets/tiles/{root}") / rel
        if p.is_file():
            return Image.open(p).convert("RGB")
    if generation > 1:
        rel_legacy = terrain_asset_relpath(biome, season, "totally_land", 1, generation=1, ext=".webp")
        for root in ("approved", "pending"):
            p = repo_path(f"assets/tiles/{root}") / rel_legacy
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


def publish_land_anchor_v01(
    cfg: dict | None = None,
    *,
    biome: str | None = None,
    season: str | None = None,
    generation: int | None = None,
) -> Path:
    """Publish totally_land/v01 raw as the land anchor in pending/."""
    from generate_sail_mask import write_mask_for_tile
    from review_lib import normalize_spec_paths

    cfg = cfg or load_config()
    biome = biome or cfg["biome"]
    season = season or cfg["season"]
    generation = generation if generation is not None else get_active_generation(cfg, biome, season)
    tid = tile_id(biome, season, "totally_land", 1, generation=generation)
    sp = spec_path(tid)
    if not sp.is_file():
        raise FileNotFoundError(f"Missing spec: {tid}")
    with sp.open(encoding="utf-8") as f:
        spec = json.load(f)
    normalize_spec_paths(spec)
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

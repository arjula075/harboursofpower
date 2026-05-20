"""Apply autotile contract to shore tiles via procedural compositing."""
from __future__ import annotations

from typing import Tuple

import numpy as np
from PIL import Image

from autotile_geometry import SHORE_TOPOLOGIES, land_mask
from shore_composite import composite_shore_from_cfg


def enforce_contract(
    raw: Image.Image,
    topology: str,
    sea_rgb: Tuple[int, int, int],
    *,
    coast_band_px: int = 32,
    sea_fade_px: int = 96,
    boundary_clamp_px: int = 6,
    land_anchor: Image.Image | None = None,
    land_enforce_strength: float = 1.0,
    land_perimeter_px: int = 64,
    diagonal_sea_fade_px: int | None = None,
    cfg: dict | None = None,
    variation: int | None = None,
) -> Image.Image:
    """Composite shore tiles from land anchor + beach + sea ramp (+ narrow AI coast)."""
    if land_anchor is None:
        return raw.convert("RGB")
    if topology not in SHORE_TOPOLOGIES:
        return raw.convert("RGB")

    from common import load_config

    cfg = dict(cfg or load_config())
    if diagonal_sea_fade_px is not None and "diagonal" in topology:
        cfg["sea_shallow_px"] = min(int(cfg.get("sea_shallow_px", 36)), diagonal_sea_fade_px)
    cfg["autotile_boundary_clamp_px"] = boundary_clamp_px
    cfg["coast_ai_px"] = coast_band_px
    w = float(land_enforce_strength) * float(cfg.get("coast_ai_weight", 0.35))
    cfg["coast_ai_weight"] = min(w, 0.5)

    return composite_shore_from_cfg(raw, topology, land_anchor, sea_rgb, cfg, variation=variation)


def procedural_shore_fallback(
    topology: str,
    sea_rgb: Tuple[int, int, int],
    land_anchor: Image.Image,
    *,
    size: int = 512,
    coast_blend_px: int = 24,
    cfg: dict | None = None,
) -> Image.Image:
    """Procedural shore with no AI (human-review fallback)."""
    from common import load_config

    cfg = dict(cfg or load_config())
    cfg["coast_ai_weight"] = 0.0
    return composite_shore_from_cfg(None, topology, land_anchor, sea_rgb, cfg)


def measure_edge_uniformity(img: Image.Image, sea_rgb: Tuple[int, int, int], topology: str, *, band: int = 4) -> dict:
    """Diagnose outermost-edge sea pixels vs uniform open sea."""
    size = img.size[0]
    arr = np.asarray(img.convert("RGB")).astype(np.float32)
    mask = land_mask(topology, size)
    sea_color = np.array(sea_rgb, dtype=np.float32)
    report: dict[str, float] = {}
    edges = {
        "north": (slice(0, band), slice(0, size)),
        "south": (slice(size - band, size), slice(0, size)),
        "west": (slice(0, size), slice(0, band)),
        "east": (slice(0, size), slice(size - band, size)),
    }
    for side, sl in edges.items():
        sub_mask = mask[sl]
        sub_arr = arr[sl]
        sea_pixels = sub_arr[sub_mask == 0]
        if sea_pixels.size == 0:
            report[side] = -1.0
            continue
        diff = np.abs(sea_pixels - sea_color).mean()
        report[side] = float(diff)
    return report

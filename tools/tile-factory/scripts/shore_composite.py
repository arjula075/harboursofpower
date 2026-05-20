"""Procedural shore compositing: land anchor + beach + flat open sea.

Sea is a thin surf band at the coast, then uniform open-sea colour (same as
totally_sea). No distance-to-opposite-edge ramp — that caused tubular shading.
"""
from __future__ import annotations

import numpy as np
from PIL import Image

from autotile_geometry import land_mask, signed_distance_from_coast
from common import load_config, repo_path
from prompts import biome_palette
from prompts import biome_palette


def _lerp_rgb(a: np.ndarray, b: np.ndarray, t: np.ndarray) -> np.ndarray:
    t = np.clip(t[..., None], 0.0, 1.0)
    return a * (1.0 - t) + b * t


def _smoothstep(t: np.ndarray) -> np.ndarray:
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _coast_noise(size: int, seed: float = 0.0) -> np.ndarray:
    """Tileable-ish smooth noise for coast wobble (-1..1)."""
    ys, xs = np.indices((size, size)).astype(np.float32)
    n = np.zeros((size, size), dtype=np.float32)
    amp, freq = 1.0, 2.5 / size
    for octave in range(3):
        phase = seed + octave * 17.3
        n += amp * np.sin((xs + phase) * freq * 6.283) * np.cos((ys + phase * 1.7) * freq * 4.712)
        amp *= 0.5
        freq *= 2.1
    n /= 1.75
    return np.clip(n, -1.0, 1.0)


def _apply_v01_natural_shoreline(
    out: np.ndarray,
    raw: np.ndarray,
    dist: np.ndarray,
    mask: np.ndarray,
    land_arr: np.ndarray,
    deep: np.ndarray,
    *,
    sea_shallow_px: int,
    wobble_px: float = 11.0,
    land_detail_px: int = 46,
    surf_detail_px: int = 18,
    land_ai_weight: float = 0.68,
    surf_ai_weight: float = 0.42,
) -> np.ndarray:
    """Break up pool-straight edge on v01 using AI rocks/sand + slight coast wobble."""
    size = out.shape[0]
    sea_dist = np.clip(-dist, 0, None)
    in_sea = mask == 0

    wobble = _coast_noise(size, seed=1.0) * wobble_px
    d_w = dist + wobble

    # Land: beach rocks, scrub, irregular sand from raw generation
    land_band = (mask == 255) & (d_w >= 0) & (d_w < land_detail_px)
    w_land = _smoothstep(1.0 - d_w / land_detail_px) * land_ai_weight
    out[land_band] = out[land_band] * (1.0 - w_land[land_band, None]) + raw[land_band] * w_land[land_band, None]

    # Sea: rocks / foam in surf only (re-flat deep water beyond shallow band)
    surf_band = in_sea & (d_w > -surf_detail_px) & (d_w < 10) & (sea_dist <= sea_shallow_px)
    w_surf = _smoothstep(1.0 - np.abs(d_w) / surf_detail_px) * surf_ai_weight
    out[surf_band] = out[surf_band] * (1.0 - w_surf[surf_band, None]) + raw[surf_band] * w_surf[surf_band, None]

    out[in_sea & (sea_dist > sea_shallow_px)] = deep
    if land_detail_px > 0:
        inland = (mask == 255) & (dist >= land_detail_px * 0.85)
        out[inland] = land_arr[inland]
    return out


def sample_coast_palette(cfg: dict, sea_rgb: tuple[int, int, int]) -> dict[str, tuple[int, int, int]]:
    """Beach from config biomes; optional override from pending horizontal v01."""
    biome, season = cfg["biome"], cfg["season"]
    pending = repo_path(cfg["paths"]["pending"])
    pal = biome_palette(cfg)
    beach = pal["beach_rgb"]
    sea_rgb = pal["open_sea_rgb"]

    h_path = pending / biome / season / "horizontal_top_land" / "v01.webp"
    if h_path.is_file():
        im = np.asarray(Image.open(h_path).convert("RGB"))
        h, w = im.shape[:2]
        band = im[h // 2 - 28 : h // 2 - 4, w // 4 : 3 * w // 4]
        beach = tuple(int(np.median(band[..., i])) for i in range(3))

    sr, sg, sb = sea_rgb
    shallow = (min(255, sr + 10), min(255, sg + 22), min(255, sb + 18))
    return {"beach": beach, "shallow": shallow, "deep": sea_rgb}


def composite_shore_tile(
    raw: Image.Image | None,
    topology: str,
    land_anchor: Image.Image,
    sea_rgb: tuple[int, int, int],
    palette: dict[str, tuple[int, int, int]],
    *,
    size: int = 512,
    beach_land_px: int = 22,
    beach_sea_px: int = 10,
    sea_shallow_px: int = 36,
    coast_ai_px: int = 26,
    coast_ai_weight: float = 0.35,
    boundary_clamp_px: int = 6,
    variation: int | None = None,
    v01_wobble_px: float = 11.0,
    v01_land_detail_px: int = 46,
    v01_surf_detail_px: int = 18,
    v01_land_ai_weight: float = 0.68,
    v01_surf_ai_weight: float = 0.42,
) -> Image.Image:
    """Build a contract-compliant shore tile from anchors + procedural coast."""
    if land_anchor.size != (size, size):
        land_anchor = land_anchor.resize((size, size), Image.Resampling.LANCZOS)
    land_arr = np.asarray(land_anchor.convert("RGB")).astype(np.float32)
    beach = np.array(palette["beach"], dtype=np.float32)
    shallow = np.array(palette["shallow"], dtype=np.float32)
    deep = np.array(palette["deep"], dtype=np.float32)

    dist = signed_distance_from_coast(topology, size).astype(np.float32)
    mask = land_mask(topology, size)
    out = land_arr.copy()

    # --- Beach (land side + narrow wet surf on sea side)
    t_land = _smoothstep(np.clip(dist / max(beach_land_px, 1), 0.0, 1.0))
    land_side = (mask == 255) & (dist >= 0) & (dist < beach_land_px)
    out[land_side] = _lerp_rgb(beach, land_arr, t_land)[land_side]

    t_wet = _smoothstep(np.clip((-dist) / max(beach_sea_px, 1), 0.0, 1.0))
    wet = (mask == 0) & (dist > -beach_sea_px) & (dist <= 0)
    out[wet] = _lerp_rgb(shallow, beach, t_wet)[wet]

    # --- Sea: narrow shallow band from coast, then flat open ocean (no mid-tile gradient)
    sea_dist = np.clip(-dist, 0, None)
    in_sea = mask == 0

    shallow_zone = in_sea & (sea_dist > beach_sea_px) & (sea_dist <= sea_shallow_px)
    t_sh = _smoothstep((sea_dist - beach_sea_px) / max(sea_shallow_px - beach_sea_px, 1))
    out[shallow_zone] = _lerp_rgb(deep, shallow, 1.0 - t_sh)[shallow_zone]

    open_water = in_sea & (sea_dist > sea_shallow_px)
    out[open_water] = deep

    # Also treat very near-coast sea (past wet band) as starting ramp
    near = in_sea & (sea_dist > 0) & (sea_dist <= beach_sea_px)
    t_near = np.full(sea_dist.shape, 0.35, dtype=np.float32)
    out[near] = _lerp_rgb(deep, shallow, t_near)[near]

    if boundary_clamp_px > 0:
        bc = boundary_clamp_px
        ys, xs = np.indices((size, size))
        boundary = (ys < bc) | (ys >= size - bc) | (xs < bc) | (xs >= size - bc)
        out[in_sea & boundary] = deep

    ai_arr: np.ndarray | None = None
    if raw is not None:
        if raw.size != (size, size):
            raw = raw.resize((size, size), Image.Resampling.LANCZOS)
        ai_arr = np.asarray(raw.convert("RGB")).astype(np.float32)

    # v01: richer irregular shoreline (rocks, sand) from raw + coast wobble
    if variation == 1 and ai_arr is not None:
        out = _apply_v01_natural_shoreline(
            out,
            ai_arr,
            dist,
            mask,
            land_arr,
            deep,
            sea_shallow_px=sea_shallow_px,
            wobble_px=v01_wobble_px,
            land_detail_px=v01_land_detail_px,
            surf_detail_px=v01_surf_detail_px,
            land_ai_weight=v01_land_ai_weight,
            surf_ai_weight=v01_surf_ai_weight,
        )
        if boundary_clamp_px > 0:
            bc = boundary_clamp_px
            ys, xs = np.indices((size, size))
            boundary = (ys < bc) | (ys >= size - bc) | (xs < bc) | (xs >= size - bc)
            out[in_sea & boundary] = deep
    elif ai_arr is not None and coast_ai_weight > 0 and coast_ai_px > 0:
        # v02+: light land-side detail only
        coast_band = (np.abs(dist) < coast_ai_px) & (dist > 0)
        w = _smoothstep(1.0 - np.abs(dist) / coast_ai_px) * coast_ai_weight
        w = coast_band.astype(np.float32) * w
        out = out * (1.0 - w[..., None]) + ai_arr * w[..., None]

    inland = (mask == 255) & (dist >= beach_land_px)
    out[inland] = land_arr[inland]

    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), mode="RGB")


def composite_shore_from_cfg(
    raw: Image.Image | None,
    topology: str,
    land_anchor: Image.Image,
    sea_rgb: tuple[int, int, int],
    cfg: dict | None = None,
    *,
    variation: int | None = None,
) -> Image.Image:
    cfg = cfg or load_config()
    palette = sample_coast_palette(cfg, sea_rgb)
    size = int(cfg["tile_size"])
    return composite_shore_tile(
        raw,
        topology,
        land_anchor,
        sea_rgb,
        palette,
        size=size,
        beach_land_px=int(cfg.get("beach_land_px", 22)),
        beach_sea_px=int(cfg.get("beach_sea_px", 10)),
        sea_shallow_px=int(cfg.get("sea_shallow_px", 36)),
        coast_ai_px=int(cfg.get("coast_ai_px", 26)),
        coast_ai_weight=float(cfg.get("coast_ai_weight", 0.35)),
        boundary_clamp_px=int(cfg.get("autotile_boundary_clamp_px", 6)),
        variation=variation,
        v01_wobble_px=float(cfg.get("v01_coast_wobble_px", 11)),
        v01_land_detail_px=int(cfg.get("v01_coast_land_detail_px", 46)),
        v01_surf_detail_px=int(cfg.get("v01_coast_surf_detail_px", 18)),
        v01_land_ai_weight=float(cfg.get("v01_coast_land_ai_weight", 0.68)),
        v01_surf_ai_weight=float(cfg.get("v01_coast_surf_ai_weight", 0.42)),
    )

"""Heuristic checks for tile content (land in sea, edge repeatability)."""
from __future__ import annotations

import hashlib
from typing import Tuple

from PIL import Image


def water_ratio(img: Image.Image) -> float:
    """Fraction of pixels that look water-like (blue-dominant)."""
    rgb = img.convert("RGB")
    water = 0
    total = rgb.size[0] * rgb.size[1]
    for r, g, b in rgb.getdata():
        if b > r + 12 and b > g - 15 and b > 60:
            water += 1
    return water / max(total, 1)


def land_vegetation_ratio(img: Image.Image) -> float:
    """Fraction of pixels that look like dry land / green scrub (not water)."""
    rgb = img.convert("RGB")
    land = 0
    total = rgb.size[0] * rgb.size[1]
    for r, g, b in rgb.getdata():
        if g > 70 and r > 60 and b < min(r, g) + 40:
            land += 1
        elif r > 130 and g > 110 and b < 100:
            land += 1
    return land / max(total, 1)


def band_image(img: Image.Image, side: str, band: int) -> Image.Image:
    w, h = img.size
    if side == "north":
        return img.crop((0, 0, w, band))
    if side == "south":
        return img.crop((0, h - band, w, h))
    if side == "west":
        return img.crop((0, 0, band, h))
    if side == "east":
        return img.crop((w - band, 0, w, h))
    raise ValueError(side)


def band_similarity(a: Image.Image, b: Image.Image) -> float:
    """0 = identical, higher = more different (mean abs diff per channel, 0-255)."""
    if a.size != b.size:
        b = b.resize(a.size, Image.Resampling.LANCZOS)
    pa = list(a.convert("RGB").getdata())
    pb = list(b.convert("RGB").getdata())
    if not pa:
        return 0.0
    diff = sum(abs(pa[i][c] - pb[i][c]) for i in range(len(pa)) for c in range(3))
    return diff / (len(pa) * 3)


def bands_match(img: Image.Image, side_a: str, side_b: str, band: int, max_mean_diff: float = 18.0) -> Tuple[bool, float]:
    sim = band_similarity(band_image(img, side_a, band), band_image(img, side_b, band))
    return sim <= max_mean_diff, sim

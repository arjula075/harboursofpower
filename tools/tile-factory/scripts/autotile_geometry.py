"""Per-topology land/sea binary masks and signed distance from coast.

Contract: cardinals = exact 50/50 (coast at midline).
Diagonals = corner triangle (sea/land in 1/8 of tile), coast hits adjacent edges
at exact mid-point so the coast line continues into neighboring cardinal tiles.
"""
from __future__ import annotations

import math
from typing import Iterable

import numpy as np

SQ2 = math.sqrt(2.0)


def land_mask(topology: str, size: int = 512) -> np.ndarray:
    """uint8 (H, W): 255 = land, 0 = sea."""
    half = size // 2
    m = np.zeros((size, size), dtype=np.uint8)
    ys, xs = np.indices((size, size))
    if topology == "totally_land":
        m[:] = 255
    elif topology == "totally_sea":
        pass
    elif topology == "horizontal_top_land":
        m[ys < half] = 255
    elif topology == "horizontal_bottom_land":
        m[ys >= half] = 255
    elif topology == "vertical_left_land":
        m[xs < half] = 255
    elif topology == "vertical_right_land":
        m[xs >= half] = 255
    elif topology == "diagonal_rising_left_land":
        # Sea = SE triangle. Coast hits E at y=half and S at x=half (cardinal-aligned).
        # Land when x+y <= 3*half-2 so sea begins at y>=half on east edge (matches horiz shore).
        m[xs + ys <= 3 * half - 2] = 255
    elif topology == "diagonal_rising_right_land":
        # Sea = SW triangle. Coast hits W at y=half and S at x=half.
        m[ys <= xs + half - 1] = 255
    elif topology == "diagonal_descending_left_land":
        # Sea = NE triangle. Coast hits N at x=half and E at y=half.
        m[ys >= xs - half + 1] = 255
    elif topology == "diagonal_descending_right_land":
        # Sea = NW triangle. Coast hits N at x=half and W at y=half.
        m[xs + ys >= half] = 255
    elif topology == "vertical_channel_land":
        # Sea N+S: navigable vertical band through centre.
        m[xs < size // 4] = 255
        m[xs >= 3 * size // 4] = 255
    elif topology == "horizontal_channel_land":
        m[ys < size // 4] = 255
        m[ys >= 3 * size // 4] = 255
    elif topology == "cape_north_land":
        m[ys >= half] = 255
    elif topology == "cape_south_land":
        m[ys < half] = 255
    elif topology == "cape_east_land":
        m[xs < half] = 255
    elif topology == "cape_west_land":
        m[xs >= half] = 255
    else:
        raise ValueError(f"Unknown topology: {topology}")
    return m


def signed_distance_from_coast(topology: str, size: int = 512) -> np.ndarray:
    """float32 (H, W). Positive on land side, negative on sea side, units = pixels."""
    half = size // 2
    ys, xs = np.indices((size, size)).astype(np.float32)
    if topology == "totally_land":
        return np.full((size, size), float(size), dtype=np.float32)
    if topology == "totally_sea":
        return np.full((size, size), -float(size), dtype=np.float32)
    if topology == "horizontal_top_land":
        return half - ys
    if topology == "horizontal_bottom_land":
        return ys - half
    if topology == "vertical_left_land":
        return half - xs
    if topology == "vertical_right_land":
        return xs - half
    if topology == "diagonal_rising_left_land":
        return (3 * half - 2 - xs - ys) / SQ2
    if topology == "diagonal_rising_right_land":
        return (xs - ys + half - 1) / SQ2
    if topology == "diagonal_descending_left_land":
        return (ys - xs + half - 1) / SQ2
    if topology == "diagonal_descending_right_land":
        return (xs + ys - half) / SQ2
    if topology == "vertical_channel_land":
        return np.minimum(half - xs, xs - (size - half)) / SQ2
    if topology == "horizontal_channel_land":
        return np.minimum(half - ys, ys - (size - half)) / SQ2
    if topology == "cape_north_land":
        return ys - half
    if topology == "cape_south_land":
        return half - ys
    if topology == "cape_east_land":
        return half - xs
    if topology == "cape_west_land":
        return xs - half
    raise ValueError(topology)


def expected_coast_hits(topology: str, size: int = 512) -> list[tuple[str, int, str]]:
    """Where the coast meets the tile edges. (side, pixel_along_edge, axis)."""
    half = size // 2
    if topology in ("horizontal_top_land", "horizontal_bottom_land"):
        return [("west", half, "y"), ("east", half, "y")]
    if topology in ("vertical_left_land", "vertical_right_land"):
        return [("north", half, "x"), ("south", half, "x")]
    if topology == "diagonal_rising_left_land":
        return [("east", half, "y"), ("south", half, "x")]
    if topology == "diagonal_rising_right_land":
        return [("west", half, "y"), ("south", half, "x")]
    if topology == "diagonal_descending_left_land":
        return [("north", half, "x"), ("east", half, "y")]
    if topology == "diagonal_descending_right_land":
        return [("north", half, "x"), ("west", half, "y")]
    return []


SHORE_TOPOLOGIES: list[str] = [
    "horizontal_top_land",
    "horizontal_bottom_land",
    "vertical_left_land",
    "vertical_right_land",
    "diagonal_rising_left_land",
    "diagonal_rising_right_land",
    "diagonal_descending_left_land",
    "diagonal_descending_right_land",
    "vertical_channel_land",
    "cape_north_land",
    "horizontal_channel_land",
    "cape_east_land",
    "cape_south_land",
    "cape_west_land",
]

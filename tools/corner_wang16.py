"""Corner Wang-16 helpers (1px Mediterranean tilemaps).

Used by build_recursive_tilemap_wang16_1px.py and the port map editor terrain tool.
"""
from __future__ import annotations

from collections import Counter
from typing import Iterable

import numpy as np

LOG_W = 2000
LOG_H = 1000

FULL_LAND = "totally_land"
FULL_SEA = "totally_sea"

CORNER_ORDER = ("NW", "NE", "SE", "SW")


def parse_tile_corners(tile: str) -> tuple[bool, bool, bool, bool]:
    """Return (nw, ne, se, sw) land flags from a corner-Wang tile name."""
    if tile == FULL_LAND:
        return True, True, True, True
    if tile == FULL_SEA:
        return False, False, False, False
    parts = tile.split("_")
    if len(parts) % 2 != 0:
        raise ValueError(f"Unrecognized corner tile name: {tile}")
    corners: dict[str, bool] = {}
    for i in range(0, len(parts), 2):
        label = parts[i]
        kind = parts[i + 1]
        if label not in CORNER_ORDER or kind not in ("land", "sea"):
            raise ValueError(f"Unrecognized corner tile name: {tile}")
        corners[label] = kind == "land"
    return (
        corners["NW"],
        corners["NE"],
        corners["SE"],
        corners["SW"],
    )


def wang_tile_name(nw: bool, ne: bool, se: bool, sw: bool) -> str:
    if nw and ne and se and sw:
        return FULL_LAND
    if not nw and not ne and not se and not sw:
        return FULL_SEA
    parts = []
    for label, is_land in zip(CORNER_ORDER, (nw, ne, se, sw), strict=True):
        parts.append(f"{label}_{'land' if is_land else 'sea'}")
    return "_".join(parts)


def build_corner_grid(land: np.ndarray) -> np.ndarray:
    """(LOG_H+1) x (LOG_W+1) bool corners from per-cell land mask."""
    h, w = land.shape
    corners = np.zeros((h + 1, w + 1), dtype=bool)
    corners[:h, :w] = land
    corners[h, :w] = land[h - 1, :]
    corners[:h, w] = land[:, w - 1]
    corners[h, w] = land[h - 1, w - 1]
    return corners


def corners_from_tiles(
    tiles: Iterable[dict],
    *,
    x0: int,
    y0: int,
    x1: int,
    y1: int,
    default_sea: bool = True,
) -> np.ndarray:
    """Build local corner grid (y1-y0+1) x (x1-x0+1) from sparse tiles in bounds."""
    w = x1 - x0
    h = y1 - y0
    corners = np.zeros((h + 1, w + 1), dtype=bool)
    if not default_sea:
        corners.fill(True)
    for t in tiles:
        x, y = int(t["x"]), int(t["y"])
        if x < x0 or x >= x1 or y < y0 or y >= y1:
            continue
        nw, ne, se, sw = parse_tile_corners(str(t.get("tile", FULL_SEA)))
        lx, ly = x - x0, y - y0
        corners[ly, lx] = nw
        corners[ly, lx + 1] = ne
        corners[ly + 1, lx + 1] = se
        corners[ly + 1, lx] = sw
    return corners


def paint_cell(corners: np.ndarray, lx: int, ly: int, *, land: bool) -> None:
    """Set one cell to totally_land or totally_sea (all four corners)."""
    val = bool(land)
    if ly < 0 or lx < 0 or ly + 1 >= corners.shape[0] or lx + 1 >= corners.shape[1]:
        raise IndexError(f"paint out of range: ({lx}, {ly}) in {corners.shape}")
    corners[ly, lx] = val
    corners[ly, lx + 1] = val
    corners[ly + 1, lx + 1] = val
    corners[ly + 1, lx] = val


def tiles_from_corners(
    corners: np.ndarray,
    *,
    x0: int = 0,
    y0: int = 0,
) -> tuple[list[dict], Counter]:
    """Enumerate every cell covered by corners (width-1 x height-1 cells)."""
    h, w = corners.shape[0] - 1, corners.shape[1] - 1
    tiles: list[dict] = []
    counts: Counter = Counter()
    for ly in range(h):
        for lx in range(w):
            nw = bool(corners[ly, lx])
            ne = bool(corners[ly, lx + 1])
            se = bool(corners[ly + 1, lx + 1])
            sw = bool(corners[ly + 1, lx])
            name = wang_tile_name(nw, ne, se, sw)
            tiles.append({"x": x0 + lx, "y": y0 + ly, "tile": name})
            counts[name] += 1
    return tiles, counts


def land_mask_from_corners(corners: np.ndarray) -> np.ndarray:
    """Per-cell land = all four corners land (matches totally_land cells)."""
    h, w = corners.shape[0] - 1, corners.shape[1] - 1
    land = np.zeros((h, w), dtype=bool)
    for ly in range(h):
        for lx in range(w):
            land[ly, lx] = (
                corners[ly, lx]
                and corners[ly, lx + 1]
                and corners[ly + 1, lx + 1]
                and corners[ly + 1, lx]
            )
    return land


def boundary_corner_changes(
    baseline: np.ndarray,
    current: np.ndarray,
) -> int:
    """Count perimeter corner positions that differ (cross-area ripple indicator)."""
    if baseline.shape != current.shape:
        raise ValueError("baseline/current shape mismatch")
    h, w = current.shape[0] - 1, current.shape[1] - 1
    n = 0
    for lx in range(current.shape[1]):
        if baseline[0, lx] != current[0, lx]:
            n += 1
        if baseline[h, lx] != current[h, lx]:
            n += 1
    for ly in range(1, h):
        if baseline[ly, 0] != current[ly, 0]:
            n += 1
        if baseline[ly, w] != current[ly, w]:
            n += 1
    return n


def overlapping_chart_areas(area_id: str, index: dict, bounds: dict) -> list[str]:
    """Other chart areas whose bounds intersect this one."""
    x0, y0, x1, y1 = bounds["x0"], bounds["y0"], bounds["x1"], bounds["y1"]
    out: list[str] = []
    for area in index.get("chart_areas", []):
        if not isinstance(area, dict):
            continue
        aid = str(area.get("id", ""))
        if aid == area_id or not aid:
            continue
        b = area.get("bounds") or {}
        if not isinstance(b, dict):
            continue
        bx0, by0, bx1, by1 = int(b["x0"]), int(b["y0"]), int(b["x1"]), int(b["y1"])
        if x0 < bx1 and x1 > bx0 and y0 < by1 and y1 > by0:
            out.append(aid)
    return sorted(out)


def render_area_preview_png(
    tiles: list[dict],
    *,
    x0: int,
    y0: int,
    x1: int,
    y1: int,
) -> bytes:
    """RGB PNG with full shore tile-type colours for editor terrain mode."""
    import io

    from PIL import Image

    coast_colors = {
        0: (200, 120, 80),
        1: (220, 140, 90),
        2: (240, 160, 100),
        3: (180, 100, 70),
    }
    w, h = x1 - x0, y1 - y0
    img = np.zeros((h, w, 3), dtype=np.uint8)
    grid = {(int(t["x"]) - x0, int(t["y"]) - y0): str(t["tile"]) for t in tiles}
    coast_idx = 0
    coast_map: dict[str, tuple[int, int, int]] = {}
    for ly in range(h):
        for lx in range(w):
            name = grid.get((lx, ly), FULL_SEA)
            if name == FULL_LAND:
                img[ly, lx] = (190, 170, 130)
            elif name == FULL_SEA:
                img[ly, lx] = (30, 80, 120)
            else:
                if name not in coast_map:
                    coast_map[name] = coast_colors[coast_idx % len(coast_colors)]
                    coast_idx += 1
                img[ly, lx] = coast_map[name]
    buf = io.BytesIO()
    Image.fromarray(img, mode="RGB").save(buf, format="PNG")
    return buf.getvalue()

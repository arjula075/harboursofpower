"""Map 1px corner-Wang tile names to strict Wang16 render topologies (v1 art)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
if str(REPO / "tools") not in sys.path:
    sys.path.insert(0, str(REPO / "tools"))

from corner_wang16 import FULL_LAND, FULL_SEA  # noqa: E402
from strict_wang16 import build_registry, topology_for_mask, wang_mask_at  # noqa: E402

# v2 / cape masks → nearest v1 texture when no dedicated art exists.
RENDER_TOPOLOGY_FALLBACK: dict[str, str] = {
    "cape_north_land": "horizontal_bottom_land",
    "cape_south_land": "horizontal_top_land",
    "cape_east_land": "vertical_left_land",
    "cape_west_land": "vertical_right_land",
    "horizontal_channel_land": "horizontal_top_land",
    "vertical_channel_land": "vertical_left_land",
}


def render_topology(topology: str) -> str:
    """Topology id used when sampling approved tile textures."""
    if topology in RENDER_TOPOLOGY_FALLBACK:
        return RENDER_TOPOLOGY_FALLBACK[topology]
    return topology


def _sparse_tile_dict(tiles: list[dict], width: int, height: int) -> dict[tuple[int, int], str]:
    out: dict[tuple[int, int], str] = {}
    for t in tiles:
        x = int(t["x"])
        y = int(t["y"])
        if 0 <= x < width and 0 <= y < height:
            out[(x, y)] = str(t.get("tile", FULL_SEA))
    return out


def _binary_land_for_mask(tile_name: str) -> bool:
    """Frozen land/sea for cardinal-neighbour Wang masks (matches strict_wang16 seeding)."""
    return tile_name != FULL_SEA


def topology_grid_from_corner_tiles(
    tiles: list[dict],
    *,
    width: int,
    height: int,
) -> np.ndarray:
    """Dense (H, W) array of render-ready topology ids (strings stored as object array)."""
    sparse = _sparse_tile_dict(tiles, width, height)
    binary: dict[tuple[int, int], bool] = {}
    for y in range(height):
        for x in range(width):
            binary[(x, y)] = _binary_land_for_mask(sparse.get((x, y), FULL_SEA))

    mask_to_topo, _, _ = build_registry()
    out = np.empty((height, width), dtype=object)
    for y in range(height):
        for x in range(width):
            name = sparse.get((x, y), FULL_SEA)
            if name == FULL_LAND:
                topo = FULL_LAND
            elif name == FULL_SEA:
                topo = FULL_SEA
            else:
                mask = wang_mask_at(x, y, binary, 1)
                topo = topology_for_mask(mask, mask_to_topo)
            out[y, x] = render_topology(str(topo))
    return out


def topology_grid_from_tilemap_json(path: Path, *, width: int, height: int) -> np.ndarray:
    data = json.loads(path.read_text(encoding="utf-8"))
    tiles = data.get("tiles", [])
    if len(tiles) < width * height * 0.5:
        raise SystemExit(f"Expected dense corner-Wang tilemap in {path}")
    return topology_grid_from_corner_tiles(tiles, width=width, height=height)

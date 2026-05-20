"""Strict 16-tile Wang: bitmask derivation and topology registry helpers."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
RULES_PATH = REPO / "tools" / "tile-factory" / "topology_rules.json"

WANG_BITS: dict[str, int] = {"N": 8, "E": 4, "S": 2, "W": 1}
CARDINAL: tuple[tuple[str, int, int], ...] = (
    ("N", 0, -1),
    ("E", 1, 0),
    ("S", 0, 1),
    ("W", -1, 0),
)

FULL_LAND = "totally_land"
FULL_SEA = "totally_sea"


def load_rules() -> dict[str, Any]:
    return json.loads(RULES_PATH.read_text(encoding="utf-8"))


def build_registry(rules: dict[str, Any] | None = None) -> tuple[dict[int, str], dict[str, int], dict[str, str]]:
    """mask -> topology id, topology id -> mask, topology id -> terrain_class."""
    rules = rules or load_rules()
    mask_to_topo: dict[int, str] = {}
    topo_to_mask: dict[str, int] = {}
    topo_to_class: dict[str, str] = {}
    for t in rules["topologies"]:
        tid = str(t["id"])
        mask = int(t["wang_mask"])
        if mask in mask_to_topo and mask_to_topo[mask] != tid:
            raise ValueError(f"Duplicate wang_mask {mask}: {mask_to_topo[mask]} vs {tid}")
        mask_to_topo[mask] = tid
        topo_to_mask[tid] = mask
        topo_to_class[tid] = str(t.get("terrain_class", "land"))
    for m in range(16):
        if m not in mask_to_topo:
            raise ValueError(f"Missing topology for wang_mask {m}")
    return mask_to_topo, topo_to_mask, topo_to_class


def is_land_terrain(topology: str, topo_to_class: dict[str, str]) -> bool:
    tc = topo_to_class.get(topology, "land")
    return tc in ("land", "shore")


def seed_binary(
    grid: dict[tuple[int, int], str],
    topo_to_class: dict[str, str],
) -> dict[tuple[int, int], bool]:
    """Frozen land/sea for neighbour bitmask (does not change across passes).

    totally_sea -> water; totally_land and legacy shore -> land. This prevents
    strict reassignment from turning the whole sparse chart into land when former
    sea cells become shore tiles but must still read as water for 4-neighbour masks.
    """
    binary: dict[tuple[int, int], bool] = {}
    for key, topo in grid.items():
        if topo == FULL_SEA:
            binary[key] = False
        else:
            binary[key] = True
    return binary


def wang_mask_at(
    x: int,
    y: int,
    binary: dict[tuple[int, int], bool],
    step: int,
) -> int:
    """4-connect mask from cardinal neighbors; absent cells = sea."""
    mask = 0
    for name, dx, dy in CARDINAL:
        if binary.get((x + dx * step, y + dy * step), False):
            mask |= WANG_BITS[name]
    return mask


def topology_for_mask(mask: int, mask_to_topo: dict[int, str]) -> str:
    if mask not in mask_to_topo:
        raise KeyError(f"No topology for wang_mask {mask}")
    return mask_to_topo[mask]


def edges_from_mask(mask: int) -> dict[str, str]:
    """Edge strip kinds for compositing (matches v1 shore conventions)."""
    edges: dict[str, str] = {}
    for side, bit in (("north", 8), ("east", 4), ("south", 2), ("west", 1)):
        if mask & bit:
            edges[side] = "land_land"
        elif side == "north":
            edges[side] = "sea_land"
        elif side == "south":
            edges[side] = "land_sea"
        elif side == "east":
            edges[side] = "sea_land"
        else:
            edges[side] = "land_sea"
    return edges


def binary_from_topology(
    grid: dict[tuple[int, int], str],
    topo_to_class: dict[str, str],
) -> dict[tuple[int, int], bool]:
    return {
        k: is_land_terrain(topo, topo_to_class) for k, topo in grid.items()
    }


def reassign_strict(
    grid: dict[tuple[int, int], str],
    step: int,
    *,
    max_passes: int = 64,
) -> tuple[dict[tuple[int, int], str], dict[str, Any]]:
    """Assign topology from wang_mask(frozen base_binary neighbours).

    base_binary is seeded once from legacy land/sea/shore and never updated, so
    open-sea cells stay water for bitmask purposes even after they receive a shore
    topology. Iterates until topology labels stabilise. Absent neighbours = sea.
    """
    mask_to_topo, topo_to_mask, _topo_to_class = build_registry()
    base_binary = seed_binary(grid, _topo_to_class)
    stats: dict[str, Any] = {"passes": 0, "changes_per_pass": []}

    for pass_i in range(max_passes):
        changed = 0
        new_grid: dict[tuple[int, int], str] = {}
        for (x, y), old in grid.items():
            mask = wang_mask_at(x, y, base_binary, step)
            topo = topology_for_mask(mask, mask_to_topo)
            new_grid[(x, y)] = topo
            if topo != old:
                changed += 1
        stats["passes"] = pass_i + 1
        stats["changes_per_pass"].append(changed)
        grid = new_grid
        if changed == 0:
            break
    else:
        stats["did_not_converge"] = True

    stats["compliance_mismatch"] = count_mask_mismatch(grid, base_binary, step, topo_to_mask)
    stats["final_counts"] = _count_topologies(grid)
    return grid, stats


def count_mask_mismatch(
    grid: dict[tuple[int, int], str],
    binary: dict[tuple[int, int], bool],
    step: int,
    topo_to_mask: dict[str, int],
) -> int:
    n = 0
    for (x, y), topo in grid.items():
        mask = wang_mask_at(x, y, binary, step)
        if topo_to_mask.get(topo) != mask:
            n += 1
    return n


def _count_topologies(grid: dict[tuple[int, int], str]) -> dict[str, int]:
    from collections import Counter

    return dict(sorted(Counter(grid.values()).items()))


def shore_topology_ids(rules: dict[str, Any] | None = None) -> frozenset[str]:
    rules = rules or load_rules()
    return frozenset(
        t["id"]
        for t in rules["topologies"]
        if t.get("terrain_class") == "shore"
    )

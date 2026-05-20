#!/usr/bin/env python3
"""Analyze chart-area tilemaps vs 16-tile Wang contract (topology_rules.json)."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TILE_DIR = REPO / "docs" / "chart_area_tilemaps_and_maps"
RULES = REPO / "tools" / "tile-factory" / "topology_rules.json"
WORLD = REPO / "data" / "world_full.json"
GW, GH = 2000, 1000

WANG_BITS = {"N": 8, "E": 4, "S": 2, "W": 1}
DIRS = [("N", 0, -1), ("E", 1, 0), ("S", 0, 1), ("W", -1, 0)]

TOPO_TO_MASK: dict[str, int] = {}
MASK_TO_TOPO: dict[int, str] = {}
SHORE_TOPOS: set[str] = set()
PENDING_MASKS: set[int] = set()


def load_rules() -> None:
    data = json.loads(RULES.read_text(encoding="utf-8"))
    for t in data["topologies"]:
        tid = t["id"]
        m = int(t["wang_mask"])
        TOPO_TO_MASK[tid] = m
        MASK_TO_TOPO[m] = tid
        if t.get("terrain_class") == "shore":
            SHORE_TOPOS.add(tid)
    PENDING_MASKS.update(data.get("wang16_extension", {}).get("pending_masks", []))


def load_tilemap(path: Path) -> tuple[dict[tuple[int, int], str], int, dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    step = int(data.get("coordinate_system", {}).get("final_tile_size", 3))
    grid: dict[tuple[int, int], str] = {}
    for t in data.get("tiles", []):
        grid[(int(t["x"]), int(t["y"]))] = str(t["tile"])
    return grid, step, data.get("chart_area", {})


def merge_grids(
    area_files: list[Path],
) -> tuple[dict[tuple[int, int], str], dict[tuple[int, int], list[str]], int]:
    merged: dict[tuple[int, int], str] = {}
    sources: dict[tuple[int, int], list[str]] = defaultdict(list)
    step = 3
    for p in area_files:
        g, step, meta = load_tilemap(p)
        aid = meta.get("id", p.stem)
        for k, v in g.items():
            if k in merged and merged[k] != v:
                sources[k].append(f"{aid}:{merged[k]}->{v}")
            merged[k] = v
            if aid not in sources[k]:
                sources[k].append(aid)
    return merged, dict(sources), step


def is_land(tile: str | None, *, shore_counts_as: str) -> bool | None:
    if tile is None:
        return None
    if tile == "totally_land":
        return True
    if tile == "totally_sea":
        return False
    if tile in SHORE_TOPOS:
        if shore_counts_as == "land":
            return True
        if shore_counts_as == "sea":
            return False
        return None  # ambiguous
    return None


def wang_mask_from_neighbors(
    grid: dict[tuple[int, int], str],
    x: int,
    y: int,
    step: int,
    *,
    shore_counts_as: str,
) -> int | None:
    mask = 0
    for name, dx, dy in DIRS:
        nt = grid.get((x + dx * step, y + dy * step))
        land = is_land(nt, shore_counts_as=shore_counts_as)
        if land is None:
            return None
        if land:
            mask |= WANG_BITS[name]
    return mask


def analyze_grid(
    grid: dict[tuple[int, int], str],
    step: int,
    *,
    shore_counts_as: str,
    label: str,
) -> dict:
    unknown_topos: Counter[str] = Counter()
    mask_mismatch: Counter[tuple[str, int, int]] = Counter()  # (stored, expected_mask, got_mask)
    topo_vs_neighbor_mask: Counter[tuple[str, int]] = Counter()  # stored topo, expected from neighbors
    cells_with_unmapped_mask: Counter[int] = Counter()
    shore_ambiguous_neighbors = 0
    inspected = 0

    for (x, y), topo in grid.items():
        if topo not in TOPO_TO_MASK:
            unknown_topos[topo] += 1
            continue
        inspected += 1
        stored_mask = TOPO_TO_MASK[topo]
        expected = wang_mask_from_neighbors(grid, x, y, step, shore_counts_as=shore_counts_as)
        if expected is None:
            shore_ambiguous_neighbors += 1
            continue
        topo_vs_neighbor_mask[(topo, expected)] += 1
        if stored_mask != expected:
            mask_mismatch[(topo, stored_mask, expected)] += 1
        if expected not in MASK_TO_TOPO:
            cells_with_unmapped_mask[expected] += 1

    return {
        "label": label,
        "cells": len(grid),
        "inspected": inspected,
        "unknown_topos": dict(unknown_topos),
        "mask_mismatch": {
            f"{a}(mask {sm}) vs neighbor-derived {em}": c
            for (a, sm, em), c in mask_mismatch.most_common(30)
        },
        "mask_mismatch_total": sum(mask_mismatch.values()),
        "topo_neighbor_pairs_top": {
            f"{topo} when neighbors imply mask {mask} ({MASK_TO_TOPO.get(mask, 'MISSING')})": c
            for (topo, mask), c in topo_vs_neighbor_mask.most_common(25)
        },
        "unmapped_neighbor_masks": {
            str(m): c for m, c in sorted(cells_with_unmapped_mask.items())
        },
        "shore_ambiguous_neighbor_cells": shore_ambiguous_neighbors,
    }


def overlap_conflicts(sources: dict[tuple[int, int], list[str]]) -> list[dict]:
    out = []
    for (x, y), notes in sources.items():
        if any("->" in n for n in notes):
            out.append({"x": x, "y": y, "notes": notes})
    return out[:20]


def port_tile_audit(world_path: Path, grid: dict[tuple[int, int], str], step: int) -> dict:
    data = json.loads(world_path.read_text(encoding="utf-8"))
    ports = data.get("ports", [])
    on_sea = 0
    on_land = 0
    on_shore = 0
    missing_tile = 0
    shore_kinds: Counter[str] = Counter()
    mask_at_port: Counter[int] = Counter()

    for p in ports:
        u, v = p.get("map_u"), p.get("map_v")
        if u is None or v is None:
            continue
        gx = int(round(float(u) * GW))
        gy = int(round(float(v) * GH))
        gx = (gx // step) * step
        gy = (gy // step) * step
        topo = grid.get((gx, gy))
        if topo is None:
            missing_tile += 1
            continue
        if topo == "totally_sea":
            on_sea += 1
        elif topo == "totally_land":
            on_land += 1
        elif topo in SHORE_TOPOS:
            on_shore += 1
            shore_kinds[topo] += 1
        m = wang_mask_from_neighbors(grid, gx, gy, step, shore_counts_as="land")
        if m is not None:
            mask_at_port[m] += 1

    return {
        "ports_total": len(ports),
        "on_totally_sea": on_sea,
        "on_totally_land": on_land,
        "on_shore": on_shore,
        "missing_sparse_tile": missing_tile,
        "shore_topology_counts": dict(shore_kinds.most_common(10)),
        "neighbor_mask_at_ports_land_shore": {str(k): v for k, v in mask_at_port.most_common(16)},
    }


def shore_only_report(
    grid: dict[tuple[int, int], str], step: int, *, shore_counts_as: str, label: str
) -> dict:
    shore_cells = {k: v for k, v in grid.items() if v in SHORE_TOPOS}
    sub = analyze_grid(shore_cells, step, shore_counts_as=shore_counts_as, label=label)
    sub["shore_cells"] = len(shore_cells)
    return sub


def main() -> None:
    load_rules()
    area_files = sorted(TILE_DIR.glob("*_tilemap.json"))
    shore_files = sorted((TILE_DIR / "shore_fixed").glob("*_tilemap.json"))

    for label, files in [("raw_chart_cutouts", area_files), ("shore_fixed", shore_files)]:
        grid, sources, step = merge_grids(files)
        conflicts = overlap_conflicts(sources)
        for policy in ("land", "sea"):
            rep = analyze_grid(grid, step, shore_counts_as=policy, label=f"{label}/shore_as_{policy}")
            print("\n" + "=" * 72)
            print(json.dumps(rep, indent=2))
        print("\n--- overlap conflicts (sample) ---")
        print(json.dumps({"count": len([k for k, v in sources.items() if any('->' in n for n in v)]), "sample": conflicts}, indent=2))

    raw_grid, _, _ = merge_grids(area_files)
    fixed_grid, _, step = merge_grids(shore_files)
    print("\n--- shore band size (raw vs shore_fixed) ---")
    raw_shore = sum(1 for v in raw_grid.values() if v in SHORE_TOPOS)
    fixed_shore = sum(1 for v in fixed_grid.values() if v in SHORE_TOPOS)
    print(json.dumps({"raw_shore_cells": raw_shore, "shore_fixed_shore_cells": fixed_shore, "added": fixed_shore - raw_shore}))

    print("\n--- mismatch on SHORE cells only (shore_fixed, shore_as_land) ---")
    print(json.dumps(shore_only_report(fixed_grid, step, shore_counts_as="land", label="shore_only"), indent=2))

    grid = fixed_grid
    # Merged shore_fixed for port audit
    print("\n" + "=" * 72)
    print("PORT PLACEMENT vs shore_fixed tilemap")
    print(json.dumps(port_tile_audit(WORLD, grid, step), indent=2))

    # Global mask coverage on shore_fixed
    all_masks: Counter[int] = Counter()
    for (x, y), topo in grid.items():
        if topo in TOPO_TO_MASK:
            all_masks[TOPO_TO_MASK[topo]] += 1
    derived: Counter[int] = Counter()
    for (x, y) in grid:
        m = wang_mask_from_neighbors(grid, x, y, step, shore_counts_as="land")
        if m is not None:
            derived[m] += 1
    print("\n--- stored wang masks (by topology assignment) ---")
    print(dict(sorted(all_masks.items())))
    print("\n--- neighbor-derived masks (shore=land) ---")
    print(dict(sorted(derived.items())))
    missing_art = [m for m in derived if m not in MASK_TO_TOPO]
    print("\n--- derived masks with NO v1 topology ---")
    print({m: derived[m] for m in sorted(missing_art)})


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Audit chart tilemap Wang consistency (4-cardinal neighbour masks)."""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TOPO_RULES = REPO / "tools" / "tile-factory" / "topology_rules.json"

# Cardinal bit: N=8, E=4, S=2, W=1 (1 = land mass across shared edge)
BIT = {"north": 8, "east": 4, "south": 2, "west": 1}
OPPOSITE = {"north": "south", "south": "north", "east": "west", "west": "east"}
NEIGHBOR_DELTA = {"north": (0, -1), "east": (1, 0), "south": (0, 1), "west": (-1, 0)}

SUPPORTED_MASKS = {0, 1, 2, 3, 4, 6, 8, 9, 12, 15}
MASK_TO_TOPO = {}


def load_topology() -> dict[str, dict]:
    rules = json.loads(TOPO_RULES.read_text(encoding="utf-8"))
    by_id: dict[str, dict] = {}
    for t in rules["topologies"]:
        by_id[t["id"]] = t
        MASK_TO_TOPO[int(t["wang_mask"])] = t["id"]
    return by_id


def land_across_edge(topo: dict, side: str) -> bool:
    """True if the edge toward an adjacent cell is land_land (terra firma continues)."""
    return topo["edges"][side] == "land_land"


def expected_mask(
    grid: dict[tuple[int, int], str],
    x: int,
    y: int,
    step: int,
    by_topo: dict[str, dict],
) -> tuple[int, dict[str, str | None]]:
    """Mask from cardinal neighbours; also return neighbour tile ids."""
    neigh: dict[str, str | None] = {}
    mask = 0
    for side, (dx, dy) in NEIGHBOR_DELTA.items():
        key = (x + dx * step, y + dy * step)
        nt = grid.get(key)
        neigh[side] = nt
        if nt is None:
            continue
        # This cell's `side` touches the neighbour's opposite edge.
        opp = OPPOSITE[side]
        t = by_topo.get(nt)
        if t and land_across_edge(t, opp):
            mask |= BIT[side]
    return mask, neigh


def topo_for_mask(mask: int) -> str | None:
    return MASK_TO_TOPO.get(mask)


def audit_tilemap(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    step = int(data.get("coordinate_system", {}).get("final_tile_size", 3))
    by_topo = load_topology()
    grid = {(int(t["x"]), int(t["y"])): str(t["tile"]) for t in data["tiles"]}

    mismatches: list[dict] = []
    unsupported: list[dict] = []
    for (x, y), tile in grid.items():
        exp, neigh = expected_mask(grid, x, y, step, by_topo)
        actual_topo = by_topo.get(tile)
        actual_mask = int(actual_topo["wang_mask"]) if actual_topo else -1

        if exp not in SUPPORTED_MASKS:
            unsupported.append(
                {
                    "x": x,
                    "y": y,
                    "tile": tile,
                    "expected_mask": exp,
                    "expected_topo": topo_for_mask(exp),
                    "neighbors": neigh,
                }
            )

        if actual_mask != exp:
            mismatches.append(
                {
                    "x": x,
                    "y": y,
                    "tile": tile,
                    "actual_mask": actual_mask,
                    "expected_mask": exp,
                    "expected_topo": topo_for_mask(exp),
                    "neighbors": neigh,
                }
            )

    return {
        "path": str(path),
        "step": step,
        "cells": len(grid),
        "mismatches": mismatches,
        "unsupported": unsupported,
    }


def find_dense_window(
    mismatches: list[dict], step: int, radius: int = 8
) -> tuple[int, int]:
    """Pick window center with many shore+mismatch cells (strait-like)."""
    score: Counter[tuple[int, int]] = Counter()
    for m in mismatches:
        gx, gy = m["x"], m["y"]
        # bucket to coarse cells
        bx, by = gx // (step * 5), gy // (step * 5)
        score[(bx, by)] += 1
    if not score:
        return 1200, 500
    bx, by = score.most_common(1)[0][0]
    cx = bx * step * 5 + step * 10
    cy = by * step * 5 + step * 10
    return cx, cy


def dump_region(
    grid: dict[tuple[int, int], str],
    cx: int,
    cy: int,
    step: int,
    by_topo: dict[str, dict],
    radius: int = 6,
) -> list[dict]:
    rows: list[dict] = []
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            x = cx + dx * step
            y = cy + dy * step
            tile = grid.get((x, y))
            if tile is None:
                continue
            exp, neigh = expected_mask(grid, x, y, step, by_topo)
            actual = by_topo.get(tile)
            am = int(actual["wang_mask"]) if actual else -1
            rows.append(
                {
                    "x": x,
                    "y": y,
                    "tile": tile,
                    "actual_mask": am,
                    "expected_mask": exp,
                    "match": am == exp,
                    "expected_topo": topo_for_mask(exp),
                    "neighbors": neigh,
                }
            )
    return sorted(rows, key=lambda r: (r["y"], r["x"]))


def main() -> None:
    path = REPO / "docs" / "chart_area_tilemaps_and_maps" / "aegean_tilemap.json"
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])

    data = json.loads(path.read_text(encoding="utf-8"))
    step = int(data.get("coordinate_system", {}).get("final_tile_size", 3))
    by_topo = load_topology()
    grid = {(int(t["x"]), int(t["y"])): str(t["tile"]) for t in data["tiles"]}

    report = audit_tilemap(path)
    mm = report["mismatches"]
    uns = report["unsupported"]

    print(f"File: {path.name}")
    print(f"Cells: {report['cells']}, step={step}")
    print(f"Wang mismatches (actual_mask != expected from land_land edges): {len(mm)}")
    print(f"Unsupported expected masks (not in 10-type set): {len(uns)}")

  # Also binary audit: expected mask treating any non-totally_sea as land
    binary_mm = 0
    for (x, y), tile in grid.items():
        mask = 0
        for side, (dx, dy) in NEIGHBOR_DELTA.items():
            nt = grid.get((x + dx * step, y + dy * step))
            if nt and nt != "totally_sea":
                mask |= BIT[side]
        am = int(by_topo[tile]["wang_mask"])
        if am != mask:
            binary_mm += 1
    print(f"Binary mismatches (non-sea neighbour = land bit): {binary_mm}")

    cx, cy = find_dense_window(mm, step)
    # Refine: center on a mismatch in that bucket
    local = [m for m in mm if abs(m["x"] - cx) < step * 30 and abs(m["y"] - cy) < step * 30]
    if local:
        cx, cy = local[0]["x"], local[0]["y"]

    print(f"\nSample window center: ({cx}, {cy}) — radius 6 cells")
    region = dump_region(grid, cx, cy, step, by_topo, radius=6)
    bad = [r for r in region if not r["match"]]
    print(f"Cells in window: {len(region)}, mismatches in window: {len(bad)}")

    out_path = REPO / "data" / "aegean_wang_audit_sample.json"
    out_path.write_text(
        json.dumps(
            {
                "center": {"x": cx, "y": cy},
                "step": step,
                "window_mismatches": bad,
                "all_cells_in_window": region,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {out_path}")

    print("\n--- Mismatches in sample window (first 40) ---")
    for r in bad[:40]:
        n = r["neighbors"]
        print(
            f"  ({r['x']:4d},{r['y']:4d})  {r['tile']:32s}  "
            f"actual={r['actual_mask']:2d}  expected={r['expected_mask']:2d} "
            f"({r['expected_topo'] or '?'})  "
            f"N={n['north'] or '-':22s} E={n['east'] or '-':22s} "
            f"S={n['south'] or '-':22s} W={n['west'] or '-'}"
        )


if __name__ == "__main__":
    main()

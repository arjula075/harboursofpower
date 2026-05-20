#!/usr/bin/env python3
"""DEPRECATED: use tools/convert_chart_tilemaps_strict_wang16.py instead.

Legacy land-centric shore buffer. Strict Wang16 conversion replaces this pipeline.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
INPUT_DIR = REPO / "docs" / "chart_area_tilemaps_and_maps"
OUTPUT_DIR = INPUT_DIR / "shore_fixed"

FULL_LAND = "totally_land"
FULL_SEA = "totally_sea"

CARDINAL = (
    ("N", 0, -1),
    ("E", 1, 0),
    ("S", 0, 1),
    ("W", -1, 0),
)
DIAGONAL = (
    ("NE", 1, -1),
    ("NW", -1, -1),
    ("SE", 1, 1),
    ("SW", -1, 1),
)

# Diagonal-only sea contact -> coast tile (from restored Mediterranean map stats).
DIAG_SEA_COAST = {
    "NE": "horizontal_bottom_land",
    "SE": "horizontal_top_land",
    "SW": "horizontal_top_land",
    "NW": "horizontal_bottom_land",
}


def _neighbour_sets(
    grid: dict[tuple[int, int], str], x: int, y: int, step: int
) -> tuple[frozenset[str], frozenset[str]]:
    ortho: set[str] = set()
    diag: set[str] = set()
    for name, dx, dy in CARDINAL:
        if grid.get((x + dx * step, y + dy * step)) == FULL_SEA:
            ortho.add(name)
    for name, dx, dy in DIAGONAL:
        if grid.get((x + dx * step, y + dy * step)) == FULL_SEA:
            diag.add(name)
    return frozenset(ortho), frozenset(diag)


def coast_type_for_sea(ortho: frozenset[str], diag: frozenset[str]) -> str | None:
    if ortho:
        s = ortho
        if s == frozenset({"S"}):
            return "horizontal_top_land"
        if s == frozenset({"N"}):
            return "horizontal_bottom_land"
        if s == frozenset({"E"}):
            return "vertical_left_land"
        if s == frozenset({"W"}):
            return "vertical_right_land"
        if s == frozenset({"S", "E"}):
            return "diagonal_descending_right_land"
        if s == frozenset({"S", "W"}):
            return "diagonal_descending_left_land"
        if s == frozenset({"N", "E"}):
            return "diagonal_rising_left_land"
        if s == frozenset({"N", "W"}):
            return "diagonal_rising_right_land"
        if s == frozenset({"N", "S"}):
            return "horizontal_top_land"
        if s == frozenset({"E", "W"}):
            return "vertical_left_land"
        if len(s) == 3:
            if "S" in s and "E" in s:
                return "diagonal_descending_right_land"
            if "S" in s and "W" in s:
                return "diagonal_descending_left_land"
            if "N" in s and "E" in s:
                return "diagonal_rising_left_land"
            if "N" in s and "W" in s:
                return "diagonal_rising_right_land"
        return "horizontal_top_land"

    if not diag:
        return None

    if len(diag) == 1:
        return DIAG_SEA_COAST[next(iter(diag))]

    # Rare multi-diagonal corners: prefer SE/SW over NE/NW (Aegean island tips).
    for key in ("SE", "SW", "NE", "NW"):
        if key in diag:
            return DIAG_SEA_COAST[key]
    return "horizontal_top_land"


def count_land_sea_touch(
    grid: dict[tuple[int, int], str], step: int, *, eight: bool
) -> int:
    dirs = list(CARDINAL)
    if eight:
        dirs = list(CARDINAL) + list(DIAGONAL)
    n = 0
    for (x, y), tile in grid.items():
        if tile not in (FULL_LAND, FULL_SEA):
            continue
        for _name, dx, dy in dirs:
            nt = grid.get((x + dx * step, y + dy * step))
            if (tile == FULL_LAND and nt == FULL_SEA) or (
                tile == FULL_SEA and nt == FULL_LAND
            ):
                n += 1
    return n // 2


def fix_grid(grid: dict[tuple[int, int], str], step: int) -> int:
    """Convert boundary totally_land cells; return number of cells changed."""
    changed = 0
    for (x, y), tile in list(grid.items()):
        if tile != FULL_LAND:
            continue
        ortho, diag = _neighbour_sets(grid, x, y, step)
        if not ortho and not diag:
            continue
        new_type = coast_type_for_sea(ortho, diag)
        if new_type and new_type != tile:
            grid[(x, y)] = new_type
            changed += 1
    return changed


def recompute_tile_counts(grid: dict[tuple[int, int], str]) -> dict[str, int]:
    return dict(sorted(Counter(grid.values()).items()))


def process_tilemap(data: dict) -> tuple[dict, dict]:
    step = int(data.get("coordinate_system", {}).get("final_tile_size", 3))
    grid = {(int(t["x"]), int(t["y"])): str(t["tile"]) for t in data["tiles"]}

    before_4 = count_land_sea_touch(grid, step, eight=False)
    before_8 = count_land_sea_touch(grid, step, eight=True)

    changed = fix_grid(grid, step)

    after_4 = count_land_sea_touch(grid, step, eight=False)
    after_8 = count_land_sea_touch(grid, step, eight=True)

    out = dict(data)
    out["tiles"] = [
        {"x": x, "y": y, "tile": grid[(x, y)]}
        for (x, y) in sorted(grid.keys())
    ]
    out["tile_counts"] = recompute_tile_counts(grid)
    out["shore_buffer_fix"] = {
        "tool": "tools/fix_chart_tilemap_shore_buffer.py",
        "rule": "totally_land touching totally_sea (4- or 8-neighbour) -> oriented coast tile",
        "cells_converted_land_to_coast": changed,
        "land_sea_pairs_4_neighbour_before": before_4,
        "land_sea_pairs_4_neighbour_after": after_4,
        "land_sea_pairs_8_neighbour_before": before_8,
        "land_sea_pairs_8_neighbour_after": after_8,
    }
    stats = out["shore_buffer_fix"]
    return out, stats


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=INPUT_DIR,
        help="Directory containing *_tilemap.json files",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help="Directory for fixed copies",
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    paths = sorted(args.input_dir.glob("*_tilemap.json"))
    if not paths:
        raise SystemExit(f"No *_tilemap.json in {args.input_dir}")

    print(f"Writing fixed tilemaps to {args.output_dir}\n")
    for path in paths:
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        fixed, stats = process_tilemap(data)
        out_path = args.output_dir / path.name
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(fixed, f, indent=2)
            f.write("\n")
        area_id = data.get("chart_area", {}).get("id", path.stem)
        print(
            f"{area_id}: converted {stats['cells_converted_land_to_coast']} cells | "
            f"4-neigh {stats['land_sea_pairs_4_neighbour_before']} -> "
            f"{stats['land_sea_pairs_4_neighbour_after']} | "
            f"8-neigh {stats['land_sea_pairs_8_neighbour_before']} -> "
            f"{stats['land_sea_pairs_8_neighbour_after']}"
        )


if __name__ == "__main__":
    main()

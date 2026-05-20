#!/usr/bin/env python3
"""Convert chart-area tilemaps to strict 16-tile Wang (bitmask-driven topology).

Reads docs/chart_area_tilemaps_and_maps/*_tilemap.json, merges to a global sparse
grid (resolving overlaps), reassigns every cell from 4-neighbour land/sea, then
writes per-area tilemaps + shore_fixed copies + conversion report.

Absent neighbours outside the sparse grid are treated as sea.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from strict_wang16 import (
    FULL_LAND,
    FULL_SEA,
    build_registry,
    count_mask_mismatch,
    reassign_strict,
    seed_binary,
)

REPO = Path(__file__).resolve().parents[1]
TILE_DIR = REPO / "docs" / "chart_area_tilemaps_and_maps"
SHORE_DIR = TILE_DIR / "shore_fixed"
REPORT_PATH = REPO / "data" / "strict_wang16_conversion_report.json"

# When chart areas overlap, prefer the more specific coast label over plain land/sea.
_PRIORITY = {
    FULL_SEA: 0,
    FULL_LAND: 1,
}


def _prio(topo: str) -> int:
    if topo in _PRIORITY:
        return _PRIORITY[topo]
    return 2 + len(topo)


def load_area_grids() -> tuple[dict[tuple[int, int], str], dict[tuple[int, int], list[str]], int]:
    merged: dict[tuple[int, int], str] = {}
    provenance: dict[tuple[int, int], list[str]] = {}
    step = 3
    for path in sorted(TILE_DIR.glob("*_tilemap.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        step = int(data.get("coordinate_system", {}).get("final_tile_size", step))
        area_id = str(data.get("chart_area", {}).get("id", path.stem.replace("_tilemap", "")))
        for t in data.get("tiles", []):
            key = (int(t["x"]), int(t["y"]))
            topo = str(t["tile"])
            if key in merged:
                if _prio(topo) >= _prio(merged[key]):
                    if topo != merged[key]:
                        provenance.setdefault(key, []).append(f"{area_id}:{merged[key]}->{topo}")
                    merged[key] = topo
            else:
                merged[key] = topo
            if area_id not in provenance.get(key, []):
                provenance.setdefault(key, []).append(area_id)
    return merged, provenance, step


def split_by_bounds(
    global_grid: dict[tuple[int, int], str],
    index_path: Path,
) -> dict[str, dict[tuple[int, int], str]]:
    index = json.loads(index_path.read_text(encoding="utf-8"))
    per_area: dict[str, dict[tuple[int, int], str]] = {}
    for area in index["chart_areas"]:
        aid = str(area["id"])
        b = area["bounds"]
        x0, y0, x1, y1 = int(b["x0"]), int(b["y0"]), int(b["x1"]), int(b["y1"])
        per_area[aid] = {
            k: v for k, v in global_grid.items() if x0 <= k[0] < x1 and y0 <= k[1] < y1
        }
    return per_area


def write_tilemap(
    path: Path,
    template: dict,
    grid: dict[tuple[int, int], str],
    extra_meta: dict,
) -> None:
    out = dict(template)
    out["tiles"] = [{"x": x, "y": y, "tile": grid[(x, y)]} for (x, y) in sorted(grid.keys())]
    out["tile_counts"] = dict(sorted(Counter(grid.values()).items()))
    out["strict_wang16"] = extra_meta
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def compliance_summary(
    grid: dict[tuple[int, int], str],
    step: int,
    base_binary: dict[tuple[int, int], bool] | None = None,
) -> dict:
    from strict_wang16 import seed_binary

    _, topo_to_mask, topo_to_class = build_registry()
    if base_binary is None:
        base_binary = seed_binary(grid, topo_to_class)
    mismatch = count_mask_mismatch(grid, base_binary, step, topo_to_mask)
    return {"cells": len(grid), "mask_mismatch": mismatch}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="Report only; do not write tilemaps")
    args = ap.parse_args()

    merged, provenance, step = load_area_grids()
    conflicts = [k for k, notes in provenance.items() if any("->" in n for n in notes)]

    _, _, topo_to_class = build_registry()
    base_binary = seed_binary(merged, topo_to_class)
    converted, stats = reassign_strict(merged, step)
    comp = compliance_summary(converted, step, base_binary)

    per_area = split_by_bounds(converted, TILE_DIR / "chart_area_index.json")

    templates: dict[str, dict] = {}
    for path in sorted(TILE_DIR.glob("*_tilemap.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        aid = str(data.get("chart_area", {}).get("id", ""))
        templates[aid] = data

    conversion_meta = {
        "tool": "tools/convert_chart_tilemaps_strict_wang16.py",
        "step": step,
        "global_reassign": stats,
        "compliance_after": comp,
        "overlap_conflicts_resolved": len(conflicts),
    }

    report = {
        "conversion": conversion_meta,
        "global_before": _count_topologies(merged),
        "global_after": _count_topologies(converted),
        "per_area_after": {aid: dict(sorted(Counter(g.values()).items())) for aid, g in per_area.items()},
        "overlap_samples": [
            {"x": k[0], "y": k[1], "notes": provenance[k]} for k in conflicts[:20]
        ],
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"\nReport: {REPORT_PATH}")

    if args.dry_run:
        print("Dry run; tilemaps not written.")
        return

    for aid, grid in per_area.items():
        tpl = templates.get(aid)
        if tpl is None:
            print(f"Skip unknown area (no template): {aid}")
            continue
        meta = {**conversion_meta, "chart_area_id": aid}
        out_main = TILE_DIR / f"{aid}_tilemap.json"
        out_shore = SHORE_DIR / f"{aid}_tilemap.json"
        write_tilemap(out_main, tpl, grid, meta)
        write_tilemap(out_shore, tpl, grid, {**meta, "copy": "shore_fixed mirror of strict wang16"})
        print(f"Wrote {out_main.name} ({len(grid)} cells)")

    print("Done.")


def _count_topologies(grid: dict[tuple[int, int], str]) -> dict[str, int]:
    return dict(sorted(Counter(grid.values()).items()))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Reassign chart-area tilemap cells from 4-cardinal Wang neighbour masks (16-type set).

Uses tools/strict_wang16.py:
  - Frozen land/sea binary from the input grid (totally_sea = water; all else = land
    for bitmask purposes).
  - Every mask 0–15 maps to exactly one topology in topology_rules.json (including
    vertical_channel_land, horizontal_channel_land, cape_* for masks 5,7,10,11,13,14).
  - Iterates per file until topology labels stabilise.

For global merge across overlapping chart areas, prefer:
  python tools/convert_chart_tilemaps_strict_wang16.py

Usage:
  python tools/repair_tilemap_wang_masks.py --dry-run
  python tools/repair_tilemap_wang_masks.py
  python tools/repair_tilemap_wang_masks.py --also-shore-fixed
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEFAULT_DIR = REPO / "docs" / "chart_area_tilemaps_and_maps"
REPORT_PATH = REPO / "data" / "wang_mask_repair_report.json"

# Allow running as script from repo root
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from strict_wang16 import (  # noqa: E402
    build_registry,
    count_mask_mismatch,
    reassign_strict,
    seed_binary,
)


def process_file(path: Path, dry_run: bool, *, max_passes: int = 64) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    step = int(data.get("coordinate_system", {}).get("final_tile_size", 3))
    grid = {(int(t["x"]), int(t["y"])): str(t["tile"]) for t in data["tiles"]}

    _, topo_to_mask, topo_to_class = build_registry()
    base_binary = seed_binary(grid, topo_to_class)
    before_mismatch = count_mask_mismatch(grid, base_binary, step, topo_to_mask)

    repaired, stats = reassign_strict(grid, step, max_passes=max_passes)
    # Compliance is measured against the frozen binary used during reassignment
    # (totally_sea = water, all other input labels = land for neighbour masks).
    after_mismatch = int(stats.get("compliance_mismatch", 0))
    compliance = {"cells": len(grid), "mask_mismatch": after_mismatch}

    out_stats = {
        "path": str(path.relative_to(REPO)),
        "cells": len(grid),
        "step": step,
        "mismatches_before": before_mismatch,
        "mismatches_after": after_mismatch,
        "reassign": stats,
        "compliance_after": compliance,
    }

    if dry_run:
        return out_stats

    data["tiles"] = [
        {"x": x, "y": y, "tile": repaired[(x, y)]}
        for (x, y) in sorted(repaired.keys())
    ]
    data["tile_counts"] = dict(sorted(Counter(repaired.values()).items()))
    data["wang_mask_repair"] = {
        "tool": "tools/repair_tilemap_wang_masks.py",
        "step": step,
        "mismatches_before": before_mismatch,
        "mismatches_after": after_mismatch,
        "reassign": stats,
        "compliance_after": compliance,
        "note": (
            "Per-area strict Wang-16 reassignment (frozen binary neighbours). "
            "All masks 0–15 including channel and cape types."
        ),
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out_stats


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="Report only; do not write")
    ap.add_argument(
        "--also-shore-fixed",
        action="store_true",
        help="Also repair shore_fixed/ copies (default: parent chart_area_tilemaps only)",
    )
    ap.add_argument(
        "--all",
        action="store_true",
        help="Repair parent + shore_fixed in one run (same as --also-shore-fixed)",
    )
    ap.add_argument("--file", type=Path, default=None, help="Single tilemap JSON")
    ap.add_argument(
        "--max-passes",
        type=int,
        default=64,
        help="Max Jacobi passes per file (default 64)",
    )
    args = ap.parse_args()

    paths: list[Path] = []
    if args.file:
        paths = [args.file.resolve()]
    else:
        paths = sorted(DEFAULT_DIR.glob("*_tilemap.json"))
        if args.also_shore_fixed or args.all:
            shore = sorted((DEFAULT_DIR / "shore_fixed").glob("*_tilemap.json"))
            paths.extend(p for p in shore if p not in paths)

    if not paths:
        raise SystemExit(f"No tilemaps under {DEFAULT_DIR}")

    prefix = "DRY RUN — " if args.dry_run else ""
    print(f"{prefix}Wang-16 repair on {len(paths)} file(s)\n")

    report_rows: list[dict] = []
    for path in paths:
        if not path.is_file():
            print(f"Skip missing: {path}")
            continue
        st = process_file(path, args.dry_run, max_passes=args.max_passes)
        report_rows.append(st)
        changes = sum(st["reassign"].get("changes_per_pass", []))
        passes = st["reassign"].get("passes", 0)
        print(
            f"{path.name}: {st['cells']} cells | "
            f"mismatch {st['mismatches_before']} -> {st['mismatches_after']} | "
            f"{passes} pass(es), {changes} cell updates"
        )
        if st["reassign"].get("did_not_converge"):
            print("  WARNING: did not converge within max passes")

    summary = {
        "dry_run": args.dry_run,
        "files": report_rows,
        "totals": {
            "files": len(report_rows),
            "cells": sum(r["cells"] for r in report_rows),
            "mismatches_before": sum(r["mismatches_before"] for r in report_rows),
            "mismatches_after": sum(r["mismatches_after"] for r in report_rows),
            "cell_updates": sum(
                sum(r["reassign"].get("changes_per_pass", [])) for r in report_rows
            ),
        },
    }
    if not args.dry_run:
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(f"\nReport: {REPORT_PATH}")


if __name__ == "__main__":
    main()

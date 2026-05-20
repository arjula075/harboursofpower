#!/usr/bin/env python3
"""Re-snap every port in data/world_full.json to the nearest shore tile.

For each port, the script:
  1. Reads the port's current (map_u, map_v) -> global (gx, gy) on a 2000x1000 grid.
  2. Loads the port's chart_area_id tilemap from
     docs/chart_area_tilemaps_and_maps/<area>_tilemap.json (strict Wang16).
  3. Finds the nearest tile whose topology has terrain_class=shore and snaps
     map_u/map_v to that tile's centre.

Inland exception keep-list lives in INLAND_KEEP below; ids in it are left
untouched. Add ports (Rome, Memphis, etc.) there if you want them to remain
on `totally_land` instead of being pulled to the coast.

Usage:
  python tools/resnap_ports_to_shore_fixed.py            # write + report
  python tools/resnap_ports_to_shore_fixed.py --dry-run  # report only
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))
from strict_wang16 import shore_topology_ids

SHORE_IDS = shore_topology_ids()
WORLD = REPO / "data" / "world_full.json"
TILE_DIR = REPO / "docs" / "chart_area_tilemaps_and_maps"
REPORT_PATH = REPO / "data" / "resnap_report.json"

GW = 2000.0
GH = 1000.0

# Ports that should stay inland (`totally_land`) instead of being snapped to a
# coast tile. Add ids here as needed; empty by default so the run reflects the
# user's "resnap_all" choice.
INLAND_KEEP: set[str] = set()


def _load_partial_coast_centres(area_id: str):
    p = TILE_DIR / f"{area_id}_tilemap.json"
    if not p.is_file():
        return None
    with p.open(encoding="utf-8") as f:
        data = json.load(f)
    step = float(data.get("coordinate_system", {}).get("final_tile_size", 3))
    half = step / 2.0
    centres: list[tuple[float, float, str]] = []
    for t in data.get("tiles", []):
        kind = str(t.get("tile", ""))
        if kind not in SHORE_IDS:
            continue
        cx = float(t["x"]) + half
        cy = float(t["y"]) + half
        centres.append((cx, cy, kind))
    return centres


def _nearest(centres, gx: float, gy: float):
    best = centres[0]
    best_d2 = float("inf")
    for cx, cy, kind in centres:
        d2 = (cx - gx) ** 2 + (cy - gy) ** 2
        if d2 < best_d2:
            best_d2 = d2
            best = (cx, cy, kind)
    return best, best_d2 ** 0.5


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Report without writing world_full.json")
    args = ap.parse_args()

    world = json.loads(WORLD.read_text(encoding="utf-8"))
    ports = world.get("ports", [])

    cache: dict[str, list | None] = {}
    moves: list[dict] = []
    inland_kept: list[str] = []
    skipped: list[dict] = []
    unchanged: list[str] = []

    for p in ports:
        if not isinstance(p, dict):
            continue
        pid = str(p.get("id", ""))
        if not pid:
            continue
        if pid in INLAND_KEEP:
            inland_kept.append(pid)
            continue
        ca = str(p.get("chart_area_id", ""))
        if not ca:
            skipped.append({"id": pid, "reason": "no chart_area_id"})
            continue
        if ca not in cache:
            cache[ca] = _load_partial_coast_centres(ca)
        centres = cache[ca]
        if centres is None:
            skipped.append({"id": pid, "reason": f"tilemap missing: {ca}"})
            continue
        if not centres:
            skipped.append({"id": pid, "reason": f"no partial-coast tiles in {ca}"})
            continue
        u = p.get("map_u")
        v = p.get("map_v")
        if u is None or v is None:
            skipped.append({"id": pid, "reason": "missing map_u/map_v"})
            continue
        gx = float(u) * GW
        gy = float(v) * GH
        (cx, cy, kind), dist = _nearest(centres, gx, gy)
        new_u = min(1.0, max(0.0, round(cx / GW, 6)))
        new_v = min(1.0, max(0.0, round(cy / GH, 6)))
        old_u = round(float(u), 6)
        old_v = round(float(v), 6)
        if new_u == old_u and new_v == old_v:
            unchanged.append(pid)
            continue
        moves.append(
            {
                "id": pid,
                "name": str(p.get("name", pid)),
                "chart_area_id": ca,
                "tile": kind,
                "distance_global": round(dist, 2),
                "old": {"map_u": old_u, "map_v": old_v},
                "new": {"map_u": new_u, "map_v": new_v},
            }
        )
        p["map_u"] = new_u
        p["map_v"] = new_v

    moves.sort(key=lambda m: -m["distance_global"])

    total = sum(1 for q in ports if isinstance(q, dict))
    print(f"Ports inspected: {total}")
    print(f"  unchanged    : {len(unchanged)}")
    print(f"  moved        : {len(moves)}")
    print(f"  inland kept  : {len(inland_kept)}")
    print(f"  skipped      : {len(skipped)}")
    if moves:
        print("\nTop 20 moves (by distance in global tiles):")
        for m in moves[:20]:
            print(
                f"  {m['id']:24s} {m['name'][:24]:24s} {m['chart_area_id']:18s} "
                f"d={m['distance_global']:>6.1f}  "
                f"({m['old']['map_u']:.4f},{m['old']['map_v']:.4f}) -> "
                f"({m['new']['map_u']:.4f},{m['new']['map_v']:.4f}) [{m['tile']}]"
            )
    if skipped:
        print("\nSkipped:")
        for s in skipped[:20]:
            print(f"  {s['id']}: {s['reason']}")
        if len(skipped) > 20:
            print(f"  ... and {len(skipped) - 20} more")

    report = {
        "world_file": str(WORLD.relative_to(REPO)),
        "tilemap_dir": str(TILE_DIR.relative_to(REPO)),
        "global_grid_width": int(GW),
        "global_grid_height": int(GH),
        "inland_keep_list": sorted(INLAND_KEEP),
        "totals": {
            "inspected": total,
            "moved": len(moves),
            "unchanged": len(unchanged),
            "inland_kept": len(inland_kept),
            "skipped": len(skipped),
        },
        "moves": moves,
        "skipped": skipped,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nReport: {REPORT_PATH}")

    if args.dry_run:
        print("Dry run; world_full.json not modified.")
        return

    WORLD.write_text(json.dumps(world, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {WORLD}")


if __name__ == "__main__":
    main()

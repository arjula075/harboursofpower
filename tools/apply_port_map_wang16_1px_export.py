#!/usr/bin/env python3
"""Apply data/port_map_editor_wang16_1px_export.json edits into data/world_full.json.

  python3 tools/apply_port_map_wang16_1px_export.py
  python3 tools/apply_port_map_wang16_1px_export.py --dry-run
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
EXPORT = REPO / "data" / "port_map_editor_wang16_1px_export.json"
WORLD = REPO / "data" / "world_full.json"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Print changes without writing")
    ap.add_argument(
        "--keep-export",
        action="store_true",
        help="Do not rename export to .applied.json after a successful write",
    )
    args = ap.parse_args()

    if not EXPORT.is_file():
        raise SystemExit(f"Missing export: {EXPORT}")

    export = json.loads(EXPORT.read_text(encoding="utf-8"))
    edits = {str(e["id"]): e for e in export.get("edits", []) if isinstance(e, dict) and e.get("id")}

    world = json.loads(WORLD.read_text(encoding="utf-8"))
    ports = world.get("ports", [])
    updated = 0
    missing = []
    for p in ports:
        if not isinstance(p, dict):
            continue
        pid = str(p.get("id", ""))
        if pid not in edits:
            continue
        e = edits[pid]
        p["map_u"] = round(float(e["map_u"]), 6)
        p["map_v"] = round(float(e["map_v"]), 6)
        updated += 1

    found = {str(p.get("id", "")) for p in ports if isinstance(p, dict)}
    for pid in edits:
        if pid not in found:
            missing.append(pid)

    print(f"Would update {updated} ports in {WORLD.name}")
    if missing:
        print(f"Warning: {len(missing)} export ids not in world: {', '.join(missing[:8])}…")

    if args.dry_run:
        return

    WORLD.write_text(json.dumps(world, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {WORLD}")

    if not args.keep_export:
        applied = EXPORT.with_name("port_map_editor_wang16_1px_export.applied.json")
        EXPORT.rename(applied)
        print(f"Renamed {EXPORT.name} → {applied.name}")


if __name__ == "__main__":
    main()

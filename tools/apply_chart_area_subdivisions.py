#!/usr/bin/env python3
"""Apply chart_area_index subdivisions to world_full.json port chart_area_id fields.

Reads PORT_TO_AREA from build_full_world.py (single source of truth) and patches
data/world_full.json. Run after editing chart areas:

  .venv/bin/python tools/apply_chart_area_subdivisions.py
  .venv/bin/python tools/resplit_chart_areas.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))

from build_full_world import CHART_AREAS, PORT_TO_AREA  # noqa: E402

WORLD = REPO / "data" / "world_full.json"
OLD_IDS = frozenset(
    {
        "iberia_gaul",
        "tyrrhenian",
        "sicily_ionian",
        "north_africa",
        "egypt_cyrenaica",
        "aegean",
        "levant_cyprus",
        "propontis_pontus",
    }
)


def resolve_area(port_id: str, current: str) -> str:
    if port_id in PORT_TO_AREA:
        return PORT_TO_AREA[port_id]
    # Colonies / yards: strip suffix and look up base port
    base = port_id
    for suf in (
        "_hinterland",
        "_bread",
        "_coast",
        "_coast_bread",
        "_resource_yards",
        "_fields",
        "_plain",
        "_estuary",
    ):
        if base.endswith(suf):
            base = base[: -len(suf)]
            break
    if base in PORT_TO_AREA:
        return PORT_TO_AREA[base]
    if current not in OLD_IDS:
        return current
    return current


def main() -> int:
    w = json.loads(WORLD.read_text(encoding="utf-8"))
    w["chart_areas"] = list(CHART_AREAS)

    n_ports = 0
    for p in w.get("ports", []):
        pid = str(p.get("id", ""))
        cur = str(p.get("chart_area_id", ""))
        new = resolve_area(pid, cur)
        if new != cur:
            p["chart_area_id"] = new
            n_ports += 1

    n_other = 0
    for key in ("colonies", "feeding_colonies", "resource_sites"):
        for row in w.get(key, []) or []:
            if not isinstance(row, dict):
                continue
            cur = str(row.get("chart_area_id", ""))
            ref = str(row.get("port_id") or row.get("id", ""))
            new = resolve_area(ref, cur)
            if new != cur:
                row["chart_area_id"] = new
                n_other += 1

    WORLD.write_text(json.dumps(w, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Updated {WORLD.relative_to(REPO)}")
    print(f"  chart_areas: {len(CHART_AREAS)}")
    print(f"  ports remapped: {n_ports}")
    print(f"  colonies/sites remapped: {n_other}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

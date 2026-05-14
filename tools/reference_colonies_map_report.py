#!/usr/bin/env python3
"""Summarize reference colonies chart alignment (schema v2 in data/)."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALIGN = ROOT / "data" / "reference_colonies_map_alignment.json"
EXTRA = ROOT / "data" / "extra_colony_ports.json"


def main() -> None:
    data = json.loads(ALIGN.read_text(encoding="utf-8"))
    print("reference_colonies_map_alignment.json")
    print("  schema_version:", data.get("schema_version"))
    cs = data.get("coordinate_sheet_png") or {}
    print("  coordinate sheet:", cs.get("path"), cs.get("png_dimensions_px"), "grid", cs.get("logical_grid"))
    rm = data.get("reference_basemap_png") or {}
    print("  basemap texture:", rm.get("path"), rm.get("dimensions_px"))
    cps = data.get("control_points") or []
    print("  control_points:", len(cps))
    ports = data.get("ports") or []
    anchored = sum(1 for p in ports if p.get("alignment_status") == "aligned_to_grid_sheet")
    print("  ports:", len(ports), "| snapped to grid sheet:", anchored)
    aff = data.get("affine_propagation_previous_to_grid") or {}
    if aff.get("coefficients"):
        print("  affine u coeffs:", aff["coefficients"].get("u"))
        print("  affine v coeffs:", aff["coefficients"].get("v"))

    if EXTRA.exists():
        ex = json.loads(EXTRA.read_text(encoding="utf-8"))
        n = len(ex.get("entries") or [])
        print("\nextra_colony_ports.json entries:", n)


if __name__ == "__main__":
    main()

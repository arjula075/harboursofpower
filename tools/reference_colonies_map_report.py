#!/usr/bin/env python3
"""Summarize reference colonies basemap alignment metadata (no extra deps)."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALIGN = ROOT / "data" / "reference_colonies_map_alignment.json"


def main() -> None:
    data = json.loads(ALIGN.read_text(encoding="utf-8"))
    img = data["reference_image"]
    ports = data["ports"]
    filled = sum(1 for p in ports if p.get("image_u") is not None and p.get("image_v") is not None)
    print("reference_colonies_map_alignment.json")
    print("  image:", img["repository_path"], f'{img["width_px"]}x{img["height_px"]}')
    print("  ports:", len(ports), "| image coords filled:", filled)
    print("  control_points:", len(data.get("control_points") or []))
    if data.get("name_ambiguities"):
        print("  ambiguities:", len(data["name_ambiguities"]))
    if filled == 0:
        print("\nNext: add entries to control_points (port_id + image_u + image_v), then fit transform and write image_u/image_v per port.")


if __name__ == "__main__":
    main()

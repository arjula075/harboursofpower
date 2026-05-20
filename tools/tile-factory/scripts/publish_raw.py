"""Copy raw PNG tiles to pending/ as WebP (no edge compositing). Use for photorealistic output."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image

from common import FACTORY_ROOT, load_config


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--proof", action="store_true")
    parser.add_argument("id", nargs="?")
    args = parser.parse_args()
    cfg = load_config()
    count = 0
    for spec_file in sorted((FACTORY_ROOT / "specs").glob("*.json")):
        with spec_file.open(encoding="utf-8") as f:
            spec = json.load(f)
        if spec.get("kind") != "terrain":
            continue
        if args.id and spec["id"] != args.id:
            continue
        if args.proof and spec.get("topology") not in (
            "totally_sea",
            "totally_land",
            "horizontal_top_land",
        ):
            if spec.get("topology") == "totally_sea" and int(spec.get("variation", 0)) > 3:
                continue
            if spec.get("topology") != "totally_sea" and int(spec.get("variation", 0)) > 1:
                continue
        raw = Path(spec["raw_path"])
        if not raw.is_file():
            print(f"Skip {spec['id']}: no raw")
            continue
        out = Path(spec["pending_path"])
        out.parent.mkdir(parents=True, exist_ok=True)
        img = Image.open(raw).convert("RGB")
        if img.size != (int(cfg["tile_size"]), int(cfg["tile_size"])):
            img = img.resize((int(cfg["tile_size"]), int(cfg["tile_size"])), Image.Resampling.LANCZOS)
        img.save(out, format="WEBP", lossless=True)
        composed = out.with_suffix(".composed.png")
        img.save(composed)
        print(f"Published raw -> {out}")
        count += 1
    print(f"Done ({count} tiles)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

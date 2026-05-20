"""Regenerate tiles: API raw + contract compositing (shores) or procedural sea."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image

from common import band_px, load_config, spec_path
from enforce_contract import enforce_contract
from generate_raw import generate_spec
from make_uniform_sea import get_open_sea_rgb, make_uniform_sea, publish_spec as publish_sea_spec
from tile_analysis import bands_match, land_vegetation_ratio, water_ratio
from tile_publish import publish_composited_shore, publish_land_anchor_v01, publish_raw_to_pending, resolve_land_anchor


def load_spec(tile_id: str) -> dict:
    with spec_path(tile_id).open(encoding="utf-8") as f:
        return json.load(f)


def content_errors(spec: dict, raw_path: Path, cfg: dict) -> list[str]:
    errors: list[str] = []
    if not raw_path.is_file():
        return ["missing raw"]
    img = Image.open(raw_path).convert("RGB")
    topo = spec["topology"]
    band = band_px(cfg)

    if topo == "totally_sea":
        wr = water_ratio(img)
        lr = land_vegetation_ratio(img)
        if wr < float(cfg.get("sea_min_water_ratio", 0.93)):
            errors.append(f"not enough water ({wr:.2%})")
        if lr > float(cfg.get("sea_max_land_ratio", 0.04)):
            errors.append(f"land detected ({lr:.2%})")

    if topo == "horizontal_top_land":
        ok, diff = bands_match(img, "west", "east", band, float(cfg.get("horizontal_edge_max_diff", 22)))
        if not ok:
            errors.append(f"left/right edges differ (diff {diff:.1f})")
        north = img.crop((0, 0, img.size[0], img.size[1] // 2))
        if water_ratio(north) > 0.45:
            errors.append("northern half has too much water")

    if topo in ("vertical_left_land", "vertical_right_land"):
        ok, diff = bands_match(img, "north", "south", band, float(cfg.get("vertical_edge_max_diff", 22)))
        if not ok:
            errors.append(f"top/bottom edges differ (diff {diff:.1f})")

    return errors


def publish_terrain(spec: dict, cfg: dict, *, land_anchor: Image.Image | None = None) -> None:
    topo = spec["topology"]
    raw = Path(spec["raw_path"])
    if topo == "totally_land":
        publish_raw_to_pending(spec, cfg)
        from generate_sail_mask import write_mask_for_tile

        write_mask_for_tile(Path(spec["pending_path"]), topo, cfg)
        return

    if land_anchor is None:
        land_anchor = resolve_land_anchor(cfg)
    if land_anchor is None:
        raise RuntimeError("totally_land/v01 anchor required in pending/ or approved/")

    sea_rgb = get_open_sea_rgb(cfg)
    raw_img = Image.open(raw).convert("RGB")
    enforced = enforce_contract(
        raw_img,
        topo,
        sea_rgb,
        land_anchor=land_anchor,
        cfg=cfg,
        variation=int(spec.get("variation", 1)),
    )
    publish_composited_shore(spec, enforced, cfg)


def regenerate(tile_id: str, max_attempts: int, *, lenient: bool = False) -> bool:
    cfg = load_config()
    spec = load_spec(tile_id)
    print(f"\n--- {tile_id} ---")
    topo = spec["topology"]

    if topo == "totally_sea":
        v = int(spec["variation"])
        size = int(cfg["tile_size"])
        rgb = get_open_sea_rgb(cfg)
        img = make_uniform_sea(size, v, rgb)
        publish_sea_spec(spec, img, cfg)
        from generate_sail_mask import write_mask_for_tile

        write_mask_for_tile(Path(spec["pending_path"]), "totally_sea", cfg)
        print(f"  OK {tile_id} (procedural sea)")
        return True

    if topo == "totally_land":
        for attempt in range(1, max_attempts + 1):
            print(f"  attempt {attempt}/{max_attempts}")
            if not generate_spec(spec, cfg, force=True):
                continue
            errs = content_errors(spec, Path(spec["raw_path"]), cfg)
            if errs and not (lenient and attempt == max_attempts):
                print(f"    content FAIL: {', '.join(errs)}")
                continue
            if int(spec.get("variation", 0)) == 1:
                publish_land_anchor_v01(cfg)
            else:
                publish_raw_to_pending(spec, cfg)
                from generate_sail_mask import write_mask_for_tile

                write_mask_for_tile(Path(spec["pending_path"]), topo, cfg)
            print(f"  OK {tile_id}")
            return True
        print(f"  GAVE UP {tile_id}")
        return False

    land_anchor = resolve_land_anchor(cfg)
    if land_anchor is None:
        print("  ERROR: need totally_land/v01 in pending/ first")
        return False

    for attempt in range(1, max_attempts + 1):
        print(f"  attempt {attempt}/{max_attempts}")
        if not generate_spec(spec, cfg, force=True):
            continue
        raw = Path(spec["raw_path"])
        errs = content_errors(spec, raw, cfg)
        if errs:
            print(f"    content FAIL: {', '.join(errs)}")
            if not (lenient and attempt == max_attempts):
                continue
            print("    lenient: publishing last attempt anyway")
        try:
            publish_terrain(spec, cfg, land_anchor=land_anchor)
        except Exception as exc:
            print(f"    publish FAIL: {exc}")
            continue
        print(f"  OK {tile_id}")
        return True
    print(f"  GAVE UP {tile_id}")
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--topology", required=True)
    parser.add_argument("--variations", type=int, nargs="*", default=[1, 2, 3])
    parser.add_argument("--max-attempts", type=int, default=5)
    parser.add_argument("--lenient", action="store_true")
    args = parser.parse_args()
    cfg = load_config()
    biome = cfg["biome"]
    season = cfg["season"]
    failed = 0
    for v in args.variations:
        tid = f"{biome}/{season}/{args.topology}/v{v:02d}"
        if not spec_path(tid).is_file():
            print(f"No spec for {tid}")
            failed += 1
            continue
        if not regenerate(tid, args.max_attempts, lenient=args.lenient):
            failed += 1
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

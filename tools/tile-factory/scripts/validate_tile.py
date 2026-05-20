"""Automated tile QA: size, edge hashes, sea stitch, variation distance."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import imagehash
from PIL import Image

from common import (
    band_px,
    edge_strip_path,
    load_config,
    repo_path,
    topology_by_id,
)
from tile_analysis import bands_match, land_vegetation_ratio, water_ratio


def extract_band(img: Image.Image, side: str, band: int) -> Image.Image:
    w, h = img.size
    if side == "north":
        return img.crop((0, 0, w, band))
    if side == "south":
        return img.crop((0, h - band, w, h))
    if side == "west":
        return img.crop((0, 0, band, h))
    if side == "east":
        return img.crop((w - band, 0, w, h))
    raise ValueError(side)


def hashlib_md5_image(img: Image.Image) -> str:
    return hashlib.md5(img.tobytes()).hexdigest()


def band_md5(img: Image.Image, side: str, band: int) -> str:
    band_img = extract_band(img, side, band)
    return hashlib.md5(band_img.tobytes()).hexdigest()


def validate_edges(tile_path: Path, spec: dict[str, Any], cfg: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    band = band_px(cfg)
    size = int(cfg["tile_size"])
    topo = topology_by_id(spec["topology"])
    img = Image.open(tile_path).convert("RGB")
    if img.size != (size, size):
        errors.append(f"size {img.size} != {size}x{size}")
        return errors
    homogeneous = spec.get("topology") in ("totally_sea", "totally_land")
    edge_items = list(topo["edges"].items())
    if homogeneous:
        edge_items = [(s, k) for s, k in edge_items if s in ("north", "south")]

    for side, edge_kind in edge_items:
        got = band_md5(img, side, band)
        try:
            exp_strip = edge_strip_path(spec["biome"], spec["season"], edge_kind)
            if not exp_strip.is_file():
                errors.append(f"missing strip {exp_strip}")
                continue
            from compose_edges import load_strip, orient_strip

            ref = orient_strip(
                load_strip(spec["biome"], spec["season"], edge_kind, side, size, band),
                edge_kind,
                side,
            )
            exp = hashlib_md5_image(ref)
        except Exception as e:
            errors.append(f"edge ref {side}: {e}")
            continue
        if got != exp:
            errors.append(f"edge mismatch {side} ({edge_kind}): got {got[:8]} expected {exp[:8]}")
    return errors


def validate_sea_stitch(tile_path: Path, spec: dict[str, Any], cfg: dict[str, Any]) -> list[str]:
    """2x2 grid of identical sea tiles — corners should match."""
    errors: list[str] = []
    if spec["topology"] != "totally_sea":
        return errors
    size = int(cfg["tile_size"])
    band = band_px(cfg)
    composed = tile_path.with_suffix(".composed.png")
    src = composed if composed.is_file() else tile_path
    tile = Image.open(src).convert("RGB")
    grid = Image.new("RGB", (size * 2, size * 2))
    for ox, oy in ((0, 0), (size, 0), (0, size), (size, size)):
        grid.paste(tile, (ox, oy))
    # Compare internal seams: east band of left vs west band of right
    left_e = grid.crop((size - band, 0, size, size * 2))
    right_w = grid.crop((size, 0, size + band, size * 2))
    if hashlib_md5_image(left_e) != hashlib_md5_image(right_w):
        errors.append("sea 2x2 horizontal internal seam mismatch")
    top_s = grid.crop((0, size - band, size * 2, size))
    bot_n = grid.crop((0, size, size * 2, size + band))
    if hashlib_md5_image(top_s) != hashlib_md5_image(bot_n):
        errors.append("sea 2x2 vertical internal seam mismatch")
    return errors


def validate_phash_distance(tile_path: Path, spec: dict[str, Any], cfg: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    pending = repo_path(cfg["paths"]["pending"])
    tid_prefix = f"{spec['biome']}/{spec['season']}/{spec['topology']}/"
    target = imagehash.phash(Image.open(tile_path))
    threshold = int(cfg["phash_hamming_threshold"])
    for other in pending.rglob("*.webp"):
        other_id = str(other.relative_to(pending)).replace("\\", "/").replace(".webp", "")
        if other_id == spec["id"]:
            continue
        if not other_id.startswith(tid_prefix):
            continue
        dist = target - imagehash.phash(Image.open(other))
        if dist < threshold:
            errors.append(f"too similar to {other_id} (phash dist {dist} < {threshold})")
    return errors


def validate(spec_path: Path) -> dict[str, Any]:
    cfg = load_config()
    with spec_path.open(encoding="utf-8") as f:
        spec = json.load(f)
    pending = Path(spec.get("pending_path", ""))
    composed = pending.with_suffix(".composed.png") if pending else Path()
    tile_path = composed if composed.is_file() else Path(spec.get("pending_path") or spec.get("approved_path", ""))
    report: dict[str, Any] = {"id": spec["id"], "path": str(tile_path), "ok": True, "errors": []}
    if not tile_path.is_file():
        report["ok"] = False
        report["errors"].append(f"tile not found: {tile_path}")
        return report
    topo = spec["topology"]
    img_path = tile_path.with_suffix(".composed.png") if tile_path.with_suffix(".composed.png").is_file() else tile_path
    img = Image.open(img_path).convert("RGB")
    band = band_px(cfg)

    if topo == "totally_sea":
        wr = water_ratio(img)
        lr = land_vegetation_ratio(img)
        if wr < float(cfg.get("sea_min_water_ratio", 0.93)):
            report["errors"].append(f"not enough water ({wr:.2%})")
        if lr > float(cfg.get("sea_max_land_ratio", 0.04)):
            report["errors"].append(f"land/vegetation ({lr:.2%})")
        # Reject strong gradients (directional sun on water breaks tiling).
        corners = [
            img.getpixel((0, 0)),
            img.getpixel((img.size[0] - 1, 0)),
            img.getpixel((0, img.size[1] - 1)),
            img.getpixel((img.size[0] - 1, img.size[1] - 1)),
        ]
        center = img.getpixel((img.size[0] // 2, img.size[1] // 2))
        def lum(p):
            return 0.299 * p[0] + 0.587 * p[1] + 0.114 * p[2]

        cl = lum(center)
        if max(abs(lum(c) - cl) for c in corners) > float(cfg.get("sea_max_corner_luma_delta", 12)):
            report["errors"].append("gradient lighting detected (corners vs center)")
        if not report["errors"]:
            report["errors"].extend(validate_sea_stitch(tile_path, spec, cfg))
    elif topo == "horizontal_top_land":
        ok, diff = bands_match(img, "west", "east", band, float(cfg.get("horizontal_edge_max_diff", 22)))
        if not ok:
            report["errors"].append(f"E/W edges differ (diff {diff:.1f})")
    elif topo in ("vertical_left_land", "vertical_right_land"):
        ok, diff = bands_match(img, "north", "south", band, float(cfg.get("vertical_edge_max_diff", 22)))
        if not ok:
            report["errors"].append(f"N/S edges differ (diff {diff:.1f})")
    elif topo not in ("totally_land",) and not str(topo).startswith(
        ("horizontal_", "vertical_", "diagonal_")
    ):
        report["errors"].extend(validate_edges(tile_path, spec, cfg))
    if topo != "totally_sea":
        report["errors"].extend(validate_phash_distance(tile_path, spec, cfg))
    report["ok"] = len(report["errors"]) == 0
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("spec", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = validate(args.spec)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        if report["ok"]:
            print(f"OK {report['id']}")
        else:
            for e in report["errors"]:
                print(f"FAIL {report['id']}: {e}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())

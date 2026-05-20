"""Autotile agent: deterministic pipeline that enforces the position+color contract.

Per topology + variation:
  1. Call OpenAI Images API with a strict coast-position prompt.
  2. Apply enforce_contract (mask outer sea zone to uniform color).
  3. Verify edge color tolerance.
  4. If still bad after N attempts: use procedural fallback (uniform sea + land
     anchor + soft coast) and append to human_review.jsonl.
  5. Save WebP + sail mask + .composed.png; mark spec autotile_contract=true.

All v01/v02/v03 of a topology share the *same* coast geometry; variation only
changes inland detail.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

from autotile_geometry import SHORE_TOPOLOGIES
from common import FACTORY_ROOT, load_config, repo_path, spec_path
from enforce_contract import enforce_contract, measure_edge_uniformity, procedural_shore_fallback
from generate_sail_mask import write_mask_for_tile
from make_uniform_sea import (
    get_open_sea_rgb,
    make_uniform_sea,
    publish_spec as publish_sea_spec,
    sample_sea_rgb_from_shores,
    save_open_sea_rgb,
)
from openai_client import generate_image, save_image_response
from prompts import SHORE_GEOMETRY_PROMPTS, shore_terrain_prompt
from tile_publish import resolve_land_anchor

def _load_spec(tile_id: str) -> dict:
    with spec_path(tile_id).open(encoding="utf-8") as f:
        return json.load(f)


def _save_spec(tile_id: str, spec: dict) -> None:
    with spec_path(tile_id).open("w", encoding="utf-8") as f:
        json.dump(spec, f, indent=2)


def _log_cost(report_dir: Path, entry: dict) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    with (report_dir / "api_cost.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def _log_review(reports: Path, entry: dict) -> None:
    reports.mkdir(parents=True, exist_ok=True)
    with (reports / "human_review.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def _publish_enforced(spec: dict, img: Image.Image) -> Path:
    pending = Path(spec["pending_path"])
    pending.parent.mkdir(parents=True, exist_ok=True)
    img.save(pending.with_suffix(".composed.png"))
    img.save(pending, format="WEBP", lossless=True)
    return pending


def _build_prompt(topology: str, variation: int, cfg: dict) -> str:
    return shore_terrain_prompt(topology, variation, biome=cfg["biome"], season=cfg["season"])


def autotile_one(
    spec: dict,
    cfg: dict,
    sea_rgb: tuple[int, int, int],
    land_anchor: Image.Image,
    *,
    max_attempts: int = 2,
    edge_tolerance: float = 14.0,
) -> tuple[bool, bool, str]:
    """Returns (published, used_fallback, message)."""
    topology = spec["topology"]
    raw_path = Path(spec["raw_path"])
    coast_band = int(cfg.get("autotile_coast_band_px", 32))
    sea_fade = int(cfg.get("autotile_sea_fade_px", 96))
    reports_dir = repo_path(cfg["paths"]["reports"])
    size = int(cfg["tile_size"])

    last_diag: dict = {}
    for attempt in range(1, max_attempts + 1):
        prompt = _build_prompt(topology, int(spec["variation"]), cfg)
        print(f"  [{attempt}/{max_attempts}] generating {spec['id']}", flush=True)
        try:
            response = generate_image(prompt, cfg)
            save_image_response(response, raw_path, size)
            _log_cost(
                reports_dir,
                {
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "kind": "autotile",
                    "id": spec["id"],
                    "attempt": attempt,
                },
            )
        except Exception as exc:
            print(f"    API error: {exc}", flush=True)
            continue

        raw_img = Image.open(raw_path).convert("RGB")
        enforced = enforce_contract(
            raw_img,
            topology,
            sea_rgb,
            coast_band_px=coast_band,
            sea_fade_px=sea_fade,
            land_anchor=land_anchor,
            diagonal_sea_fade_px=int(cfg.get("diagonal_sea_fade_px", 48)),
            cfg=cfg,
            variation=int(spec.get("variation", 1)),
        )
        diag = measure_edge_uniformity(enforced, sea_rgb, topology, band=4)
        last_diag = diag
        worst = max((v for v in diag.values() if v >= 0), default=0.0)
        print(f"    outermost edge sea-color worst diff: {worst:.2f} (tol {edge_tolerance})", flush=True)
        if worst <= edge_tolerance:
            _publish_enforced(spec, enforced)
            return True, False, f"ok (worst edge {worst:.1f})"

    print(f"  fallback: procedural shore for {spec['id']}", flush=True)
    enforced = procedural_shore_fallback(topology, sea_rgb, land_anchor, size=size)
    _publish_enforced(spec, enforced)
    _log_review(
        reports_dir,
        {
            "ts": datetime.now(timezone.utc).isoformat(),
            "id": spec["id"],
            "reason": "autotile fallback",
            "last_edge_diag": last_diag,
        },
    )
    return True, True, "fallback"


def regenerate_uniform_sea_set(cfg: dict, sea_rgb: tuple[int, int, int]) -> None:
    size = int(cfg["tile_size"])
    for v in range(1, int(cfg["variations_per_topology"]) + 1):
        tid = f"{cfg['biome']}/{cfg['season']}/totally_sea/v{v:02d}"
        sp = spec_path(tid)
        if not sp.is_file():
            continue
        with sp.open(encoding="utf-8") as f:
            spec = json.load(f)
        img = make_uniform_sea(size, v, sea_rgb)
        publish_sea_spec(spec, img, cfg)
        write_mask_for_tile(Path(spec["pending_path"]), "totally_sea", cfg)
        print(f"Uniform sea -> {tid}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--topologies", nargs="*", default=None, help="Subset of shore topologies")
    parser.add_argument("--variations", type=int, nargs="*", default=None)
    parser.add_argument("--max-attempts", type=int, default=2)
    args = parser.parse_args()

    cfg = load_config()
    biome = cfg["biome"]
    season = cfg["season"]

    land_anchor = resolve_land_anchor(cfg)
    if land_anchor is None:
        print("ERROR: need pending/approved totally_land/v01.webp for fallback")
        return 1

    sea_rgb = get_open_sea_rgb(cfg)
    save_open_sea_rgb(cfg, sea_rgb)
    print(f"Using open sea RGB {sea_rgb}")

    topologies = args.topologies or SHORE_TOPOLOGIES
    variations = args.variations or list(range(1, int(cfg["variations_per_topology"]) + 1))

    fallbacks: list[str] = []
    for topo in topologies:
        if topo not in SHORE_GEOMETRY_PROMPTS:
            print(f"Skip unknown topology: {topo}")
            continue
        for v in variations:
            tid = f"{biome}/{season}/{topo}/v{v:02d}"
            sp = spec_path(tid)
            if not sp.is_file():
                print(f"Missing spec: {tid}")
                continue
            spec = _load_spec(tid)
            print(f"\n--- {tid} ---")
            _, used_fallback, msg = autotile_one(
                spec, cfg, sea_rgb, land_anchor, max_attempts=args.max_attempts
            )
            spec["autotile_contract"] = True
            spec["autotile_fallback"] = bool(used_fallback)
            spec["status"] = "pending"
            _save_spec(tid, spec)
            write_mask_for_tile(Path(spec["pending_path"]), topo, cfg)
            if used_fallback:
                fallbacks.append(tid)
            print(f"  -> {msg}")

    regenerate_uniform_sea_set(cfg, sea_rgb)

    print(f"\nautotile complete. {len(fallbacks)} fallback tiles need human review:")
    for f in fallbacks:
        print(f"  - {f}")
    if fallbacks:
        print(
            f"\nLog: {repo_path(cfg['paths']['reports']) / 'human_review.jsonl'}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Build v1 terrain set + 5×5 lake mosaic."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from common import FACTORY_ROOT, load_config, load_topology_rules, repo_path, spec_path
from preflight import check_build, exit_if_failed
from tile_publish import publish_land_anchor_v01, resolve_land_anchor

SCRIPTS = Path(__file__).parent


def _run(script: str, *args: str) -> int:
    cmd = [sys.executable, str(SCRIPTS / script), *args]
    print("\n+ " + " ".join(cmd), flush=True)
    return subprocess.call(cmd, cwd=str(repo_path(".")))


def _v1_shore_topologies() -> list[str]:
    return [
        t["id"]
        for t in load_topology_rules()["topologies"]
        if t.get("phase") == "v1" and t["id"] not in ("totally_sea", "totally_land")
    ]


def _ensure_specs() -> None:
    from orchestrator import cmd_enqueue_v1

    if not any(FACTORY_ROOT.glob("specs/*.json")):
        print("No specs found — running enqueue-v1...", flush=True)
        cmd_enqueue_v1(argparse.Namespace())


def _apply_config_overrides(cfg: dict, args: argparse.Namespace) -> dict:
    if not (args.biome or args.season):
        return cfg
    cfg = dict(cfg)
    if args.biome:
        cfg["biome"] = args.biome
    if args.season:
        cfg["season"] = args.season
    cfg_path = FACTORY_ROOT / "config.json"
    with cfg_path.open("w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
        f.write("\n")
    return cfg


def _generate_terrain(cfg: dict, variations: list[int], *, force: bool, proof: bool) -> int:
    biome, season = cfg["biome"], cfg["season"]
    failed = 0

    if proof:
        topologies = _v1_shore_topologies()
        land_variations: list[int] = []
    else:
        topologies = [t["id"] for t in load_topology_rules()["topologies"] if t.get("phase") == "v1"]
        land_variations = variations

    for topo in topologies:
        if topo == "totally_sea":
            continue
        vars_for_topo = [1] if (proof and topo in _v1_shore_topologies()) else variations
        if topo == "totally_land":
            vars_for_topo = land_variations
        for v in vars_for_topo:
            if topo == "totally_land" and v == 1:
                continue
            tid = f"{biome}/{season}/{topo}/v{v:02d}"
            if not spec_path(tid).is_file():
                print(f"  skip (no spec): {tid}", flush=True)
                failed += 1
                continue
            code = _run("generate_raw.py", tid, *(["--force"] if force else []))
            if code != 0:
                failed += 1
    return failed


def main() -> int:
    parser = argparse.ArgumentParser(description="Build v1 tile set + lake mosaic review")
    parser.add_argument("--biome", help="Override config biome")
    parser.add_argument("--season", help="Override config season")
    parser.add_argument("--variations", type=int, nargs="*", default=None)
    parser.add_argument(
        "--proof",
        action="store_true",
        help="Cheap proof: v01 only — 1 land + 8 shores + lake mosaic (~9 API images)",
    )
    parser.add_argument("--force", action="store_true", help="Regenerate existing raw PNGs")
    parser.add_argument("--skip-generate", action="store_true", help="Only reenforce + lake review")
    parser.add_argument("--validate", action="store_true", help="Run validator on pending v1 tiles after build")
    args = parser.parse_args()

    cfg = _apply_config_overrides(load_config(), args)
    variations = [1] if args.proof else sorted(set(args.variations or [1, 2, 3]))

    pf = check_build(cfg, variations, skip_generate=args.skip_generate, proof=args.proof)
    if exit_if_failed(pf) != 0:
        return 1

    biome, season = cfg["biome"], cfg["season"]
    mode = "PROOF" if args.proof else "FULL"
    print(f"\nbuild-v1-mosaic [{mode}]: {biome}/{season} variations={variations}", flush=True)

    _ensure_specs()

    if args.skip_generate:
        print("\n=== Skip generate: reenforce + review only ===", flush=True)
    else:
        print("\n=== 1/5 Land anchor (totally_land v01) ===", flush=True)
        tid_land = f"{biome}/{season}/totally_land/v01"
        if _run("generate_raw.py", tid_land, *(["--force"] if args.force else [])) != 0:
            return 1
        try:
            publish_land_anchor_v01(cfg)
            print(f"Land anchor published: {tid_land}", flush=True)
        except FileNotFoundError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 1

        label = "8 shores v01" if args.proof else "shores + land v02/v03"
        print(f"\n=== 2/5 Raw terrain ({label}) ===", flush=True)
        if _generate_terrain(cfg, variations, force=args.force, proof=args.proof) != 0:
            print("WARNING: some raw generations failed", flush=True)

        print("\n=== 3/5 Procedural open sea ===", flush=True)
        sea_vars = [1] if args.proof else variations
        if _run("make_uniform_sea.py", "--variations", *[str(v) for v in sea_vars]) != 0:
            return 1

    if resolve_land_anchor(cfg) is None:
        print("ERROR: totally_land/v01 missing in pending/", file=sys.stderr)
        return 1

    print("\n=== 4/5 Shore compositing (reenforce) ===", flush=True)
    reenforce_vars = [1] if args.proof else variations
    if _run("reenforce_all.py", "--variations", *[str(v) for v in reenforce_vars]) != 0:
        return 1

    if not args.proof:
        # Full set: refresh sea colour from shores then re-enforce sea tiles only
        if _run("make_uniform_sea.py", "--variations", *[str(v) for v in variations]) != 0:
            return 1

    print("\n=== 5/5 Lake QA + review ===", flush=True)
    if _run("stitch_check_lake.py") != 0:
        print("WARNING: lake mask stitch check reported mismatches", flush=True)
    if _run("build_lake_review.py") != 0:
        return 1

    if args.validate:
        print("\n=== Validate pending v1 ===", flush=True)
        val_args = ["--variations", *[str(v) for v in reenforce_vars]]
        if args.proof:
            val_args.append("--proof")
        if _run("validate_pending_v1.py", *val_args) != 0:
            print("WARNING: some tiles failed validation", flush=True)

    review = FACTORY_ROOT / "review" / "index.html"
    mosaic = FACTORY_ROOT / "reports" / "lake_mosaic_5x5.png"
    print("\n--- Done ---", flush=True)
    print(f"  Review:  {review}", flush=True)
    print(f"  Mosaic:  {mosaic}", flush=True)
    if args.proof:
        print("  Proof run complete. If OK: build-v1-mosaic --variations 1 2 3", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

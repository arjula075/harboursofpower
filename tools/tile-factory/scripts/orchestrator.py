"""Tile factory CLI: enqueue, compose, validate, review, approve."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from common import (
    FACTORY_ROOT,
    load_config,
    load_topology_rules,
    repo_path,
    spec_path,
    tile_id,
    topology_by_id,
)

# Allow running as script from repo root
sys.path.insert(0, str(Path(__file__).parent))


def _compose_tile(*args, **kwargs):
    from compose_edges import compose_tile

    return compose_tile(*args, **kwargs)


def _validate(spec_path: Path):
    from validate_tile import validate

    return validate(spec_path)


def write_spec(spec: dict) -> Path:
    p = spec_path(spec["id"])
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        json.dump(spec, f, indent=2)
    return p


def make_terrain_spec(biome: str, season: str, topology: str, variation: int) -> dict:
    cfg = load_config()
    tid = tile_id(biome, season, topology, variation)
    topo = topology_by_id(topology)
    rel_pending = Path(cfg["paths"]["pending"]) / biome / season / topology / f"v{variation:02d}.webp"
    rel_raw = Path("tools/tile-factory/raw") / biome / season / topology / f"v{variation:02d}.png"
    return {
        "id": tid,
        "kind": "terrain",
        "biome": biome,
        "season": season,
        "topology": topology,
        "legacy_id": topo.get("legacy_id", topology),
        "wang_mask": topo.get("wang_mask"),
        "terrain_class": topo.get("terrain_class"),
        "variation": variation,
        "status": "pending",
        "raw_path": str(repo_path(str(rel_raw))),
        "pending_path": str(repo_path(str(rel_pending))),
        "approved_path": str(
            repo_path(cfg["paths"]["approved"]) / biome / season / topology / f"v{variation:02d}.webp"
        ),
    }


def make_port_spec(culture: str, season: str, variation: int) -> dict:
    cfg = load_config()
    tid = f"overlay/port_{culture}/{season}/v{variation:02d}"
    rel_pending = Path("assets/tiles/overlays/pending") / f"port_{culture}" / season / f"v{variation:02d}.webp"
    rel_raw = Path("tools/tile-factory/raw/overlays") / f"port_{culture}" / season / f"v{variation:02d}.png"
    return {
        "id": tid,
        "kind": "port_overlay",
        "culture": culture,
        "season": season,
        "variation": variation,
        "status": "pending",
        "raw_path": str(repo_path(str(rel_raw))),
        "pending_path": str(repo_path(str(rel_pending))),
        "approved_path": str(
            repo_path("assets/tiles/overlays/approved") / f"port_{culture}" / season / f"v{variation:02d}.webp"
        ),
    }


def cmd_enqueue_v1(_: argparse.Namespace) -> int:
    cfg = load_config()
    biome = cfg["biome"]
    season = cfg["season"]
    n = int(cfg["variations_per_topology"])
    rules = load_topology_rules()
    count = 0
    for topo in rules["topologies"]:
        if topo.get("phase") != "v1":
            continue
        for v in range(1, n + 1):
            write_spec(make_terrain_spec(biome, season, topo["id"], v))
            count += 1
    for v in range(1, 6):
        write_spec(make_port_spec("greek", season, v))
        count += 1
    print(f"Enqueued {count} specs under {FACTORY_ROOT / 'specs'}")
    return 0


def cmd_compose(args: argparse.Namespace) -> int:
    _warn_deprecated("compose", "build-v1-mosaic / refresh-mosaic (edge_compose_mode is none)")
    spec_file = spec_path(args.id) if not args.spec else Path(args.spec)
    with spec_file.open(encoding="utf-8") as f:
        spec = json.load(f)
    if spec["kind"] != "terrain":
        print("compose only applies to terrain tiles with edge contracts")
        return 1
    raw = Path(spec["raw_path"])
    if not raw.is_file():
        print(f"Missing raw: {raw}")
        return 1
    _compose_tile(raw, Path(spec["pending_path"]), spec["biome"], spec["season"], spec["topology"])
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    if args.all:
        failed = 0
        for spec_file in sorted((FACTORY_ROOT / "specs").glob("*.json")):
            report = _validate(spec_file)
            if not report["ok"]:
                failed += 1
                print(f"FAIL {report['id']}: {', '.join(report['errors'])}")
            else:
                print(f"OK   {report['id']}")
        return 1 if failed else 0
    spec_file = spec_path(args.id) if args.id else Path(args.spec)
    report = _validate(spec_file)
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


def cmd_approve(args: argparse.Namespace) -> int:
    cfg = load_config()
    spec_file = spec_path(args.id)
    with spec_file.open(encoding="utf-8") as f:
        spec = json.load(f)
    pending = Path(spec["pending_path"])
    approved = Path(spec["approved_path"])
    if not pending.is_file():
        print(f"Not in pending: {pending}")
        return 1
    approved.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(pending, approved)
    sail_src = pending.with_suffix(".sail.png")
    if sail_src.is_file():
        shutil.copy2(sail_src, approved.with_suffix(".sail.png"))
    spec["status"] = "approved"
    with spec_file.open("w", encoding="utf-8") as f:
        json.dump(spec, f, indent=2)
    print(f"Approved -> {approved}")
    return 0


def _scripts_dir() -> Path:
    return Path(__file__).parent


def _run_py(script: str, *args: str) -> int:
    cmd = [sys.executable, str(_scripts_dir() / script), *args]
    print("+", " ".join(cmd))
    return subprocess.call(cmd, cwd=str(repo_path(".")))


def _warn_deprecated(name: str, alternative: str) -> None:
    print(f"\n*** DEPRECATED: `{name}` — use `{alternative}` for v1 mosaics. ***\n", flush=True)


def cmd_generate_edges(_: argparse.Namespace) -> int:
    return _run_py("generate_edges.py")


def cmd_generate(args: argparse.Namespace) -> int:
    extra = []
    if args.proof:
        extra.append("--proof")
    if args.kind:
        extra.extend(["--kind", args.kind])
    if args.force:
        extra.append("--force")
    if args.id:
        extra.append(args.id)
    return _run_py("generate_raw.py", *extra)


def cmd_compose_all(args: argparse.Namespace) -> int:
    _warn_deprecated("compose-all", "build-v1-mosaic or refresh-mosaic")
    failed = 0
    for spec_file in sorted((FACTORY_ROOT / "specs").glob("*.json")):
        with spec_file.open(encoding="utf-8") as f:
            spec = json.load(f)
        if spec.get("kind") != "terrain":
            continue
        if args.proof and spec.get("topology") not in (
            "totally_sea",
            "totally_land",
            "horizontal_top_land",
        ):
            continue
        if args.proof and spec.get("topology") == "totally_sea" and int(spec.get("variation", 0)) > 3:
            continue
        if args.proof and spec.get("topology") != "totally_sea" and int(spec.get("variation", 0)) > 1:
            continue
        raw = Path(spec["raw_path"])
        if not raw.is_file():
            print(f"Skip compose (no raw): {spec['id']}")
            failed += 1
            continue
        _compose_tile(raw, Path(spec["pending_path"]), spec["biome"], spec["season"], spec["topology"])
        print(f"Composed {spec['id']}")
    return 1 if failed else 0


def cmd_sail_all(args: argparse.Namespace) -> int:
    from generate_sail_mask import write_mask_for_tile

    cfg = load_config()
    for spec_file in sorted((FACTORY_ROOT / "specs").glob("*.json")):
        with spec_file.open(encoding="utf-8") as f:
            spec = json.load(f)
        if spec.get("kind") != "terrain":
            continue
        pending = Path(spec["pending_path"])
        if not pending.is_file():
            continue
        if args.proof and not _proof_spec(spec):
            continue
        write_mask_for_tile(pending, spec["topology"], cfg)
    return 0


def _proof_spec(spec: dict) -> bool:
    tid = spec.get("topology")
    var = int(spec.get("variation", 99))
    if tid == "totally_sea" and var <= 3:
        return True
    if tid in ("totally_land", "horizontal_top_land") and var == 1:
        return True
    return False


def cmd_fix_sea(_: argparse.Namespace) -> int:
    code = _run_py("make_uniform_sea.py", "--variations", "1", "2", "3")
    if code != 0:
        return code
    from generate_sail_mask import write_mask_for_tile

    cfg = load_config()
    for v in (1, 2, 3):
        tid = f"{cfg['biome']}/{cfg['season']}/totally_sea/v{v:02d}"
        sp = spec_path(tid)
        if sp.is_file():
            with sp.open(encoding="utf-8") as f:
                spec = json.load(f)
            pending = Path(spec["pending_path"])
            if pending.is_file():
                write_mask_for_tile(pending, "totally_sea", cfg)
    cmd_build_review(argparse.Namespace())
    print("Uniform open-sea tiles ready (no gradient, seamless edges).")
    return 0


def cmd_fix_feedback(_: argparse.Namespace) -> int:
    """User QA: pure sea, horizontal stackable shore, vertical shore from reference layout."""
    _run_py("try_adopt_vertical.py")
    steps = [
        ("totally_sea", "1", "2", "3"),
        ("horizontal_top_land", "1"),
        ("vertical_right_land", "1"),
    ]
    for topo, *vars_ in steps:
        code = _run_py("regenerate.py", "--topology", topo, "--variations", *vars_)
        if code != 0:
            return code
    cmd_build_review(argparse.Namespace())
    print("\nfix-feedback done. Review tools/tile-factory/review/index.html")
    return 0


def cmd_refresh_proof(args: argparse.Namespace) -> int:
    """Re-bootstrap edges from reference, regenerate proof tiles with photorealistic prompts."""
    print("=== bootstrap edges from reference_coast.png ===")
    if _run_py("bootstrap_edges_from_reference.py") != 0:
        return 1
    steps = [
        ("generate-proof", lambda: cmd_generate(argparse.Namespace(proof=True, kind="terrain", force=True, id=None))),
        ("compose-proof", lambda: cmd_compose_all(argparse.Namespace(proof=True))),
        ("sail-proof", lambda: cmd_sail_all(argparse.Namespace(proof=True))),
    ]
    for name, fn in steps:
        print(f"\n=== {name} ===")
        if fn() != 0:
            print(f"Stopped at {name}")
            return 1
    cmd_build_review(argparse.Namespace())
    print("\nRefresh complete. Open tools/tile-factory/review/index.html")
    print("Tip: compare raw/ vs pending/ — raw is the model output before soft seam blend.")
    return 0


def cmd_phase1(args: argparse.Namespace) -> int:
    """Phase 1: edge library, proof terrain tiles, compose, sail masks, validate, stitch previews."""
    _warn_deprecated("phase1", "bootstrap-biome && build-v1-mosaic --proof")
    steps = [
        ("bootstrap-edges", lambda: _run_py("bootstrap_edges_from_reference.py")),
        ("generate-proof", lambda: cmd_generate(argparse.Namespace(proof=True, kind="terrain", force=args.force, id=None))),
        ("compose-proof", lambda: cmd_compose_all(argparse.Namespace(proof=True))),
        ("sail-proof", lambda: cmd_sail_all(argparse.Namespace(proof=True))),
    ]
    for name, fn in steps:
        print(f"\n=== {name} ===")
        if fn() != 0:
            print(f"Phase1 stopped at {name}")
            return 1

    print("\n=== validate (proof) ===")
    failed = 0
    for spec_file in sorted((FACTORY_ROOT / "specs").glob("*.json")):
        with spec_file.open(encoding="utf-8") as f:
            spec = json.load(f)
        if not _proof_spec(spec):
            continue
        pending = Path(spec["pending_path"])
        if not pending.is_file():
            continue
        report = _validate(spec_file)
        if not report["ok"]:
            failed += 1
            print(f"FAIL {report['id']}: {', '.join(report['errors'])}")

    print("\n=== stitch previews ===")
    _run_py("stitch_preview.py", "--topology", "totally_sea", "--grid", "5", "5")
    _run_py("stitch_preview.py", "--topology", "horizontal_top_land", "--grid", "3", "3")
    cmd_build_review(argparse.Namespace())
    print("\nPhase1 complete. Open tools/tile-factory/review/index.html and approve tiles you like.")
    return failed


def cmd_build_review(_: argparse.Namespace) -> int:
    cfg = load_config()
    pending = repo_path(cfg["paths"]["pending"])
    overlay_pending = repo_path("assets/tiles/overlays/pending")
    rows = []
    for root in (pending, overlay_pending):
        if not root.is_dir():
            continue
        for webp in sorted(root.rglob("*.webp")):
            rel = webp.relative_to(repo_path("."))
            rows.append(
                f'<div class="card"><img src="../../../{rel.as_posix()}" width="256" height="256" />'
                f"<p>{rel.as_posix()}</p></div>"
            )
    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Tile review</title>
<style>
body {{ font-family: system-ui; background: #1a1a1a; color: #eee; }}
.grid {{ display: flex; flex-wrap: wrap; gap: 12px; }}
.card {{ background: #2a2a2a; padding: 8px; border-radius: 8px; }}
.card p {{ font-size: 12px; margin: 8px 0 0; word-break: break-all; }}
</style></head><body>
<h1>Pending tiles — approve via CLI</h1>
<p><code>python tools/tile-factory/scripts/orchestrator.py approve BIOME/season/topology/vNN</code></p>
<div class="grid">{''.join(rows) if rows else '<p>No pending tiles.</p>'}</div>
</body></html>"""
    html = html.replace("<motion></motion>", "")
    out = FACTORY_ROOT / "review" / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"Review gallery -> {out}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="HarboursOfPower tile factory")
    sub = parser.add_subparsers(dest="cmd", required=True)

    def cmd_bootstrap_biome(args: argparse.Namespace) -> int:
        from preflight import (
            check_bootstrap,
            count_api_images,
            ensure_biome_palette_in_config,
            estimate_cost_usd,
            exit_if_failed,
            load_openai_api_key,
        )
        from prompts import biome_style_path

        cfg = load_config()
        if args.biome:
            cfg["biome"] = args.biome
        if args.season:
            cfg["season"] = args.season
        cfg_path = FACTORY_ROOT / "config.json"
        with cfg_path.open("w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
            f.write("\n")

        biome = cfg["biome"]
        pf = check_bootstrap(cfg, biome=biome)
        if exit_if_failed(pf) != 0:
            return 1

        cfg = ensure_biome_palette_in_config(load_config(), biome)
        cmd_enqueue_v1(args)

        print(f"\nBiome ready: {biome}/{cfg['season']}")
        if load_openai_api_key():
            n = count_api_images(cfg, [1], proof=True)
            lo, hi = estimate_cost_usd(n, cfg.get("openai_image_model"))
            print(f"Proof build (~{n} API images): est. ${lo:.2f}–${hi:.2f} USD")
            print("  orchestrator.py build-v1-mosaic --proof")
        else:
            print("Set OPENAI_API_KEY in .env before build-v1-mosaic")
        return 0

    def cmd_build_v1_mosaic(args: argparse.Namespace) -> int:
        extra: list[str] = []
        if args.biome:
            extra += ["--biome", args.biome]
        if args.season:
            extra += ["--season", args.season]
        if getattr(args, "proof", False):
            extra.append("--proof")
        elif args.variations:
            extra += ["--variations", *[str(v) for v in args.variations]]
        if args.force:
            extra.append("--force")
        if args.skip_generate:
            extra.append("--skip-generate")
        if getattr(args, "validate", False):
            extra.append("--validate")
        return _run_py("build_v1_mosaic.py", *extra)

    p_boot = sub.add_parser("bootstrap-biome", help="Set biome/season, verify style, enqueue v1 specs")
    p_boot.add_argument("--biome", help="Biome id (must have style/biomes/{biome}.md)")
    p_boot.add_argument("--season", default="summer")
    p_boot.set_defaults(func=cmd_bootstrap_biome)

    p_build = sub.add_parser(
        "build-v1-mosaic",
        help="Full v1 pipeline: land anchor → raw shores → sea → composite → lake review",
    )
    p_build.add_argument("--biome")
    p_build.add_argument("--season")
    p_build.add_argument("--variations", type=int, nargs="*", default=None)
    p_build.add_argument("--proof", action="store_true", help="v01 only: 1 land + 8 shores (~9 API images)")
    p_build.add_argument("--force", action="store_true")
    p_build.add_argument("--skip-generate", action="store_true", help="Only reenforce + lake review")
    p_build.add_argument("--validate", action="store_true", help="Run validator after build")
    p_build.set_defaults(func=cmd_build_v1_mosaic)

    p_refresh = sub.add_parser("refresh-mosaic", help="Re-composite shores + rebuild lake (no API)")
    p_refresh.add_argument("--variations", type=int, nargs="*", default=[1, 2, 3])
    def _refresh(a):
        extra = ["--skip-generate", "--variations", *[str(v) for v in a.variations]]
        return _run_py("build_v1_mosaic.py", *extra)
    p_refresh.set_defaults(func=_refresh)

    p_enqueue = sub.add_parser("enqueue-v1", help="Create specs for v1 biome (10 terrain + 5 greek port)")
    p_enqueue.set_defaults(func=cmd_enqueue_v1)

    p_compose = sub.add_parser("compose", help="Compose edges onto raw using spec id")
    p_compose.add_argument("id", nargs="?", help="Tile id e.g. dry_scrubland/summer/totally_sea/v01")
    p_compose.add_argument("--spec", type=Path)
    p_compose.set_defaults(func=cmd_compose)

    p_val = sub.add_parser("validate", help="Run validator")
    p_val.add_argument("id", nargs="?")
    p_val.add_argument("--spec", type=Path)
    p_val.add_argument("--all", action="store_true")
    p_val.set_defaults(func=cmd_validate)

    p_app = sub.add_parser("approve", help="Copy pending -> approved (human gate)")
    p_app.add_argument("id", help="Tile id")
    p_app.set_defaults(func=cmd_approve)

    p_rev = sub.add_parser("build-review", help="Build review/index.html")
    p_rev.set_defaults(func=cmd_build_review)

    p_edges = sub.add_parser("generate-edges", help="Generate edge strip library (OpenAI)")
    p_edges.set_defaults(func=cmd_generate_edges)

    p_gen = sub.add_parser("generate", help="Generate raw PNGs from specs (OpenAI)")
    p_gen.add_argument("id", nargs="?")
    p_gen.add_argument("--kind", choices=["terrain", "port_overlay"])
    p_gen.add_argument("--proof", action="store_true")
    p_gen.add_argument("--force", action="store_true")
    p_gen.set_defaults(func=cmd_generate)

    p_call = sub.add_parser("compose-all", help="Compose all terrain with existing raw")
    p_call.add_argument("--proof", action="store_true")
    p_call.set_defaults(func=cmd_compose_all)

    p_sail = sub.add_parser("sail-all", help="Write procedural sail masks for pending terrain")
    p_sail.add_argument("--proof", action="store_true")
    p_sail.set_defaults(func=cmd_sail_all)

    p_p1 = sub.add_parser("phase1", help="Run full phase1 pipeline (edges + proof tiles + QA)")
    p_p1.add_argument("--force", action="store_true", help="Regenerate even if raw exists")
    p_p1.set_defaults(func=cmd_phase1)

    p_ref = sub.add_parser(
        "refresh-proof",
        help="Bootstrap edges from reference + regenerate proof tiles (fixes frame borders)",
    )
    p_ref.set_defaults(func=cmd_refresh_proof)

    p_raw = sub.add_parser(
        "publish-raw",
        help="Copy raw model PNGs to pending/ (no seam overlay — best for review)",
    )
    p_raw.add_argument("id", nargs="?")
    p_raw.add_argument("--proof", action="store_true")
    p_raw.set_defaults(func=lambda a: _run_py("publish_raw.py", *(["--proof"] if a.proof else []), *([a.id] if a.id else [])))

    p_fix = sub.add_parser(
        "fix-feedback",
        help="Regenerate sea, horizontal_top_land; adopt or regen vertical_right_land",
    )
    p_fix.set_defaults(func=cmd_fix_feedback)

    p_sea = sub.add_parser("fix-sea", help="Rebuild totally_sea as uniform tileable ocean (no AI)")
    p_sea.set_defaults(func=cmd_fix_sea)

    p_full = sub.add_parser(
        "generate-full-v1",
        help="Alias for build-v1-mosaic (legacy name)",
    )
    p_full.add_argument("--variations", type=int, nargs="*", default=[1, 2, 3])
    p_full.add_argument("--force", action="store_true")
    p_full.set_defaults(
        func=lambda a: _run_py(
            "build_v1_mosaic.py",
            "--variations",
            *[str(v) for v in a.variations],
            *(["--force"] if a.force else []),
        )
    )

    p_lake = sub.add_parser("build-lake-review", help="5×5 lake mosaic in review/index.html")
    p_lake.set_defaults(func=lambda _: _run_py("build_lake_review.py"))

    p_all = sub.add_parser("make-full-set", help="Alias for build-v1-mosaic")
    p_all.add_argument("--variations", type=int, nargs="*", default=[1, 2, 3])
    p_all.set_defaults(
        func=lambda a: _run_py(
            "build_v1_mosaic.py",
            "--variations",
            *[str(v) for v in a.variations],
        )
    )

    p_auto = sub.add_parser("autotile", help="Run autotile contract agent on shore tiles")
    p_auto.add_argument("--topologies", nargs="*")
    p_auto.add_argument("--variations", type=int, nargs="*")
    p_auto.add_argument("--max-attempts", type=int, default=2)
    def _auto(a):
        extra = ["--max-attempts", str(a.max_attempts)]
        if a.topologies:
            extra += ["--topologies", *a.topologies]
        if a.variations:
            extra += ["--variations", *[str(v) for v in a.variations]]
        code = _run_py("autotile_agent.py", *extra)
        if code == 0:
            _run_py("build_lake_review.py")
        return code
    p_auto.set_defaults(func=_auto)

    p_re = sub.add_parser("reenforce", help="Re-apply contract to existing raws (no API)")
    p_re.set_defaults(
        func=lambda _: 0
        if _run_py("reenforce_all.py") == 0 and _run_py("build_lake_review.py") == 0
        else 1
    )

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

"""Regenerate full v1 terrain sets (API raw + compositing) for one or more biomes."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from common import (
    FACTORY_ROOT,
    generation_dir_name,
    load_config,
    load_topology_rules,
    next_generation,
    set_active_generation,
    spec_path,
)
from orchestrator import make_terrain_spec, write_spec
from preflight import check_build, ensure_biome_palette_in_config, exit_if_failed, load_openai_api_key
from regenerate import regenerate

CONFIG_PATH = FACTORY_ROOT / "config.json"


def _set_active_biome(biome: str, season: str) -> dict:
    """Point config.json at the biome being regenerated (land anchor + compositor)."""
    cfg = load_config()
    cfg["biome"] = biome
    cfg["season"] = season
    cfg = ensure_biome_palette_in_config(cfg, biome)
    with CONFIG_PATH.open("w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
        f.write("\n")
    return cfg


def _v1_topology_ids() -> list[str]:
    return [
        t["id"]
        for t in load_topology_rules()["topologies"]
        if t.get("phase") == "v1"
    ]


def _enqueue_generation_specs(biome: str, season: str, generation: int) -> list[dict]:
    """Create spec JSON for every v1 topology × slot in a new generation batch."""
    cfg = load_config()
    n = int(cfg.get("variations_per_topology", 3))
    specs: list[dict] = []
    for topo in _v1_topology_ids():
        for slot in range(1, n + 1):
            spec = make_terrain_spec(biome, season, topo, slot, generation=generation)
            write_spec(spec)
            specs.append(spec)
    return specs


def _terrain_specs(
    *,
    biomes: list[str],
    seasons: list[str],
    generation: int | None = None,
) -> list[dict]:
    v1_ids = set(_v1_topology_ids())
    out: list[dict] = []
    for path in sorted((FACTORY_ROOT / "specs").glob("*.json")):
        with path.open(encoding="utf-8") as f:
            spec = json.load(f)
        if spec.get("kind") != "terrain":
            continue
        if spec.get("biome") not in biomes:
            continue
        if spec.get("season") not in seasons:
            continue
        if spec.get("topology") not in v1_ids:
            continue
        if generation is not None and int(spec.get("generation", 1)) != generation:
            continue
        out.append(spec)
    return out


def _is_complete(spec: dict) -> bool:
    pending = Path(spec["pending_path"])
    if spec.get("topology") == "totally_sea":
        return pending.is_file()
    raw = Path(spec["raw_path"])
    return raw.is_file() and pending.is_file()


def _sort_key(spec: dict) -> tuple:
    topo = spec["topology"]
    v = int(spec.get("variation", 1))
    g = int(spec.get("generation", 1))
    if topo == "totally_land" and v == 1:
        return (0, g, v)
    if topo == "totally_land":
        return (1, g, v)
    if topo == "totally_sea":
        return (4, g, topo, v)
    return (2, g, topo, v)


def main() -> int:
    parser = argparse.ArgumentParser(description="Regenerate all v1 terrain tiles for biomes")
    parser.add_argument(
        "--biomes",
        nargs="+",
        default=None,
        help="Biomes to process (default: dry_scrubland sparse_olive)",
    )
    parser.add_argument("--season", default="summer")
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--lenient", action="store_true", default=True)
    parser.add_argument("--shores-only", action="store_true", help="Skip land and sea tiles")
    parser.add_argument(
        "--skip-complete",
        action="store_true",
        help="Skip tiles that already have raw PNG and pending WebP",
    )
    parser.add_argument(
        "--only",
        nargs="+",
        default=None,
        help="Only regenerate these tile ids",
    )
    parser.add_argument(
        "--new-generation",
        action="store_true",
        default=True,
        help="Write to next gNNN folder instead of overwriting legacy v01–v03 (default: on)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Reuse existing specs/paths (overwrites current generation files)",
    )
    args = parser.parse_args()
    if args.overwrite:
        args.new_generation = False

    biomes = args.biomes or ["dry_scrubland", "sparse_olive"]
    seasons = [args.season]

    if not load_openai_api_key():
        print("ERROR: OPENAI_API_KEY not set (export it or add to repo-root .env)", file=sys.stderr)
        return 1

    failed: list[str] = []
    for biome in biomes:
        cfg = _set_active_biome(biome, args.season)
        pf = check_build(cfg, [1, 2, 3], skip_generate=False, proof=False)
        if exit_if_failed(pf) != 0:
            return 1

        generation: int | None = None
        if args.new_generation:
            generation = next_generation(biome, args.season)
            cfg = set_active_generation(cfg, biome, args.season, generation)
            with CONFIG_PATH.open("w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
                f.write("\n")
            print(
                f"\n=== {biome}/{args.season}: new generation {generation_dir_name(generation)} ===",
                flush=True,
            )
            specs = _enqueue_generation_specs(biome, args.season, generation)
        else:
            specs = _terrain_specs(biomes=[biome], seasons=seasons)

        if args.shores_only:
            specs = [s for s in specs if s.get("topology") not in ("totally_land", "totally_sea")]
        specs.sort(key=_sort_key)

        if args.only:
            only_set = set(args.only)
            specs = [s for s in specs if s["id"] in only_set]

        print(f"=== {biome}/{args.season}: {len(specs)} tiles ===", flush=True)
        for spec in specs:
            tid = spec["id"]
            if not spec_path(tid).is_file():
                print(f"  skip (no spec file): {tid}", flush=True)
                failed.append(tid)
                continue
            if args.skip_complete and _is_complete(spec):
                print(f"  skip (complete): {tid}", flush=True)
                continue
            if not regenerate(tid, args.max_attempts, lenient=args.lenient):
                failed.append(tid)

    if failed:
        print(f"\nFailed ({len(failed)}):", flush=True)
        for tid in failed:
            print(f"  {tid}", flush=True)
        return 1
    print("\nAll tiles regenerated.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

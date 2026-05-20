"""Pre-flight checks before tile-factory API runs."""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

from common import FACTORY_ROOT, load_config, load_topology_rules, repo_path, spec_path
from prompts import biome_palette, biome_style_path
from tile_publish import resolve_land_anchor


@dataclass
class PreflightResult:
    ok: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def fail(self, msg: str) -> None:
        self.ok = False
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)


def load_openai_api_key() -> str | None:
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if key:
        return key
    env_file = repo_path(".env")
    if not env_file.is_file():
        return None
    try:
        from dotenv import load_dotenv

        load_dotenv(env_file, override=False)
        key = os.environ.get("OPENAI_API_KEY", "").strip()
        return key or None
    except ImportError:
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("OPENAI_API_KEY="):
                val = line.split("=", 1)[1].strip().strip('"').strip("'")
                return val or None
    return None


def count_api_images(cfg: dict, variations: list[int], *, proof: bool) -> int:
    """Images API calls for build-v1-mosaic generate phase."""
    if proof:
        # 1 land + 8 shores (v01 only)
        return 1 + 8
    n = len(variations)
    # 1 land v01 + land (n-1) other vars + 8 shores * n
    land_calls = 1 + max(0, n - 1)
    shore_calls = 8 * n
    return land_calls + shore_calls


def estimate_cost_usd(api_calls: int, model: str | None = None) -> tuple[float, float]:
    """Rough USD range (low, high) per image call."""
    model = (model or "gpt-image-1").lower()
    if "dall-e-3" in model:
        return api_calls * 0.04, api_calls * 0.08
    # gpt-image-1 medium quality ~$0.02–0.06 per 1024 image (varies by tier)
    return api_calls * 0.02, api_calls * 0.06


def v1_shore_topologies() -> list[str]:
    return [
        t["id"]
        for t in load_topology_rules()["topologies"]
        if t.get("phase") == "v1" and t["id"] not in ("totally_sea", "totally_land")
    ]


def ensure_biome_palette_in_config(cfg: dict, biome: str) -> dict:
    """Add default palette entry for biome if missing; persist config.json."""
    cfg = dict(cfg)
    palettes = dict(cfg.get("biomes", {}))
    if biome not in palettes:
        palettes[biome] = {
            "open_sea_rgb": list(cfg.get("open_sea_rgb", [17, 54, 58])),
            "beach_rgb": [196, 178, 142],
        }
        cfg["biomes"] = palettes
        cfg_path = FACTORY_ROOT / "config.json"
        with cfg_path.open("w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
            f.write("\n")
        print(f"Added default palette → config biomes.{biome}", flush=True)
    return cfg


def check_bootstrap(cfg: dict, *, biome: str | None = None) -> PreflightResult:
    r = PreflightResult()
    biome = biome or cfg["biome"]
    style = biome_style_path(biome)
    if not style.is_file():
        r.fail(f"Missing biome style bible: {style}")
        r.fail("Copy tools/tile-factory/style/biomes/_template.md → biomes/{biome}.md")
    palettes = cfg.get("biomes", {})
    if biome not in palettes:
        r.warn(
            f"No palette in config.json → biomes.{biome} "
            "(will use defaults until shores are composited)"
        )
    spec_count = len(list(FACTORY_ROOT.glob("specs/*.json")))
    if spec_count == 0:
        r.warn("No specs yet — bootstrap will run enqueue-v1")
    return r


def check_build(
    cfg: dict,
    variations: list[int],
    *,
    skip_generate: bool,
    proof: bool,
    require_land_anchor: bool = True,
) -> PreflightResult:
    r = PreflightResult()
    biome = cfg["biome"]
    season = cfg["season"]

    style = biome_style_path(biome)
    if not style.is_file():
        r.fail(f"Missing biome style: {style}")
        r.fail("Run: orchestrator.py bootstrap-biome --biome " + biome)

    if not skip_generate:
        if not load_openai_api_key():
            r.fail("OPENAI_API_KEY not set (env or repo-root .env)")
        model = cfg.get("openai_image_model", "gpt-image-1")
        n = count_api_images(cfg, variations, proof=proof)
        lo, hi = estimate_cost_usd(n, model)
        print(
            f"API plan: ~{n} image generations ({model}), est. ${lo:.2f}–${hi:.2f} USD",
            flush=True,
        )

    missing_specs: list[str] = []
    vars_ = [1] if proof else variations
    for topo in ("totally_land", *v1_shore_topologies()):
        for v in vars_:
            if topo == "totally_land" and proof and v > 1:
                continue
            if topo == "totally_land" and not proof and v == 1:
                tid = f"{biome}/{season}/totally_land/v01"
                if not spec_path(tid).is_file():
                    missing_specs.append(tid)
                continue
            tid = f"{biome}/{season}/{topo}/v{v:02d}"
            if not spec_path(tid).is_file():
                missing_specs.append(tid)
    if missing_specs:
        r.fail(f"Missing {len(missing_specs)} spec(s), e.g. {missing_specs[0]}")
        r.fail("Run: orchestrator.py bootstrap-biome")

    if require_land_anchor and resolve_land_anchor(cfg) is None:
        if skip_generate:
            r.fail(
                f"Land anchor missing: assets/tiles/pending/{biome}/{season}/totally_land/v01.webp"
            )
            r.fail("Run build without --skip-generate first, or generate land v01 manually")
        else:
            r.warn("Land anchor will be created in step 1")

    if skip_generate:
        pending = repo_path(cfg["paths"]["pending"])
        for topo in v1_shore_topologies():
            for v in vars_:
                p = pending / biome / season / topo / f"v{v:02d}.webp"
                raw = FACTORY_ROOT / "raw" / biome / season / topo / f"v{v:02d}.png"
                if not p.is_file() and not raw.is_file():
                    r.warn(f"No pending or raw for {biome}/{season}/{topo}/v{v:02d}")

    return r


def print_result(r: PreflightResult) -> None:
    for w in r.warnings:
        print(f"WARNING: {w}", flush=True)
    if not r.ok:
        print("\nPre-flight FAILED:", file=sys.stderr, flush=True)
        for e in r.errors:
            print(f"  • {e}", file=sys.stderr, flush=True)
        print(file=sys.stderr, flush=True)


def exit_if_failed(r: PreflightResult) -> int:
    print_result(r)
    return 0 if r.ok else 1

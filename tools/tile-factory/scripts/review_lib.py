"""Tile review: discover sets, mosaic layout, approve pending tiles."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from common import (
    FACTORY_ROOT,
    generation_dir_name,
    get_active_generation,
    is_generation_dir,
    list_generations as _list_generations,
    load_config,
    repo_path,
    spec_path,
    terrain_asset_relpath,
    tile_id,
)
from prompts import assemble_generation_prompt, default_prompt_layers_for_spec, prompt_detail_for_spec

LAYOUT_PATH = Path(__file__).with_name("lake_layout.json")


def _rel_repo(path: Path) -> str:
    try:
        return path.resolve().relative_to(repo_path(".")).as_posix()
    except ValueError:
        return str(path)


def resolve_tile_paths(spec: dict) -> tuple[Path, Path]:
    """Pending/approved paths from spec fields — never trust stale absolute paths in JSON."""
    cfg = load_config()
    kind = str(spec.get("kind", "terrain"))
    variation = int(spec.get("variation", 1))
    if kind == "terrain":
        biome = str(spec["biome"])
        season = str(spec["season"])
        topology = str(spec["topology"])
        generation = int(spec.get("generation", 1))
        rel = terrain_asset_relpath(
            biome, season, topology, variation, generation=generation, ext=".webp"
        )
        pending = repo_path(cfg["paths"]["pending"]) / rel
        approved = repo_path(cfg["paths"]["approved"]) / rel
        return pending, approved
    culture = str(spec.get("culture", "greek"))
    season = str(spec["season"])
    pending = repo_path("assets/tiles/overlays/pending") / f"port_{culture}" / season / fname
    approved = repo_path("assets/tiles/overlays/approved") / f"port_{culture}" / season / fname
    return pending, approved


def load_spec(tile_id_str: str) -> dict:
    sp = spec_path(tile_id_str)
    if not sp.is_file():
        raise FileNotFoundError(f"No spec: {_rel_repo(sp)}")
    return json.loads(sp.read_text(encoding="utf-8"))


def save_spec(spec: dict) -> None:
    tid = str(spec.get("id", ""))
    if not tid:
        raise ValueError("spec missing id")
    sp = spec_path(tid)
    normalize_spec_paths(spec)
    sp.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")


def get_prompt_detail(tile_id_str: str) -> dict[str, Any]:
    spec = load_spec(tile_id_str)
    return prompt_detail_for_spec(spec)


def save_prompt_layers(
    tile_id_str: str,
    layers: dict[str, str] | None = None,
    *,
    generation_prompt: str | None = None,
    clear_full_override: bool = False,
) -> dict[str, Any]:
    spec = load_spec(tile_id_str)
    defaults = default_prompt_layers_for_spec(spec)
    stored: dict[str, dict] = {}
    if layers:
        for key, text in layers.items():
            if key not in defaults:
                continue
            default_text = str(defaults[key]["text"])
            new_text = str(text)
            if new_text.strip() != default_text.strip():
                stored[key] = {"text": new_text}
    if stored:
        spec["prompt_layers"] = stored
    elif "prompt_layers" in spec and not stored:
        spec.pop("prompt_layers", None)
    if clear_full_override:
        spec.pop("generation_prompt", None)
    elif generation_prompt is not None and str(generation_prompt).strip():
        spec["generation_prompt"] = str(generation_prompt).strip()
    save_spec(spec)
    return prompt_detail_for_spec(spec)


def run_regenerate_tile(tile_id_str: str) -> dict[str, Any]:
    """Regenerate one tile (API + compositing). Returns ok + message."""
    import io
    import sys
    from contextlib import redirect_stderr, redirect_stdout

    spec = load_spec(tile_id_str)
    if spec.get("kind") == "terrain" and spec.get("topology") == "totally_sea":
        from regenerate import regenerate

        buf_out = io.StringIO()
        buf_err = io.StringIO()
        with redirect_stdout(buf_out), redirect_stderr(buf_err):
            ok = regenerate(tile_id_str, max_attempts=1, lenient=True)
        log = (buf_out.getvalue() + buf_err.getvalue()).strip()
        return {"ok": bool(ok), "id": tile_id_str, "log": log or ("OK" if ok else "failed")}

    from regenerate import regenerate

    buf_out = io.StringIO()
    buf_err = io.StringIO()
    with redirect_stdout(buf_out), redirect_stderr(buf_err):
        ok = regenerate(tile_id_str, max_attempts=3, lenient=True)
    log = (buf_out.getvalue() + buf_err.getvalue()).strip()
    return {
        "ok": bool(ok),
        "id": tile_id_str,
        "log": log or ("OK" if ok else "Regeneration failed"),
    }


def normalize_spec_paths(spec: dict) -> None:
    """Rewrite pending/approved/raw paths in spec to repo-relative posix (fixes cross-machine specs)."""
    pending, approved = resolve_tile_paths(spec)
    spec["pending_path"] = str(pending)
    spec["approved_path"] = str(approved)
    if spec.get("kind") != "terrain":
        return
    variation = int(spec.get("variation", 1))
    generation = int(spec.get("generation", 1))
    rel = terrain_asset_relpath(
        str(spec["biome"]),
        str(spec["season"]),
        str(spec["topology"]),
        variation,
        generation=generation,
        ext=".png",
    )
    spec["raw_path"] = str(repo_path("tools/tile-factory/raw") / rel)


def _load_lake_layout() -> list[list[str]]:
    with LAYOUT_PATH.open(encoding="utf-8") as f:
        return json.load(f)["grid"]


def discover_sets() -> list[dict[str, Any]]:
    """Unique biome/season pairs that have at least one terrain .webp."""
    seen: set[tuple[str, str]] = set()
    out: list[dict[str, Any]] = []
    cfg = load_config()
    catalog = {b["id"]: b for b in cfg.get("biome_catalog", []) if isinstance(b, dict)}
    pending_root = repo_path(cfg["paths"]["pending"])
    approved_root = repo_path(cfg["paths"]["approved"])

    for root in (pending_root, approved_root):
        if not root.is_dir():
            continue
        for biome_dir in sorted(root.iterdir()):
            if not biome_dir.is_dir():
                continue
            biome = biome_dir.name
            for season_dir in sorted(biome_dir.iterdir()):
                if not season_dir.is_dir():
                    continue
                season = season_dir.name
                key = (biome, season)
                if key in seen:
                    continue
                seen.add(key)
                pending_n = (
                    len(list((pending_root / biome / season).rglob("*.webp")))
                    if (pending_root / biome / season).is_dir()
                    else 0
                )
                approved_n = (
                    len(list((approved_root / biome / season).rglob("*.webp")))
                    if (approved_root / biome / season).is_dir()
                    else 0
                )
                if pending_n == 0 and approved_n == 0:
                    continue
                meta = catalog.get(biome, {})
                generations = [
                    {
                        "generation": g,
                        "label": "g001 (legacy)" if g <= 1 else generation_dir_name(g),
                    }
                    for g in _list_generations(biome, season)
                ]
                active_gen = get_active_generation(cfg, biome, season)
                out.append(
                    {
                        "biome": biome,
                        "season": season,
                        "name": str(meta.get("name", biome.replace("_", " "))),
                        "status": str(meta.get("status", "")),
                        "pending_count": pending_n,
                        "approved_count": approved_n,
                        "generations": generations,
                        "active_generation": active_gen,
                    }
                )
    return sorted(out, key=lambda r: (r["biome"], r["season"]))


def _tile_path(
    pool: str,
    biome: str,
    season: str,
    topology: str,
    variation: int,
    *,
    generation: int = 1,
) -> Path:
    cfg = load_config()
    root = repo_path(cfg["paths"]["pending" if pool == "pending" else "approved"])
    rel = terrain_asset_relpath(biome, season, topology, variation, generation=generation, ext=".webp")
    return root / rel


def _parse_webp_rel(rel: Path, pool: str) -> dict[str, Any] | None:
    parts = rel.parts
    if len(parts) < 4 or not parts[-1].endswith(".webp"):
        return None
    fname = parts[-1]
    if not fname.startswith("v") or not fname.endswith(".webp"):
        return None
    try:
        variation = int(fname[1:3])
    except ValueError:
        return None
    # Legacy: biome/season/topology/vNN.webp
    # New:    biome/season/gNNN/topology/vNN.webp
    if len(parts) == 4:
        topology, season, biome = parts[-2], parts[-3], parts[-4]
        generation = 1
    elif len(parts) == 5 and is_generation_dir(parts[-3]):
        topology, gen_name, season, biome = parts[-2], parts[-3], parts[-4], parts[-5]
        generation = int(gen_name[1:])
    else:
        return None
    tid = tile_id(biome, season, topology, variation, generation=generation)
    url_path = rel.as_posix()
    return {
        "id": tid,
        "biome": biome,
        "season": season,
        "topology": topology,
        "variation": variation,
        "generation": generation,
        "pool": pool,
        "label": topology.replace("_", " "),
        "image_url": f"/assets/tiles/{pool}/{url_path}",
        "has_composed": False,
        "has_sail": False,
    }


def list_tiles(
    biome: str,
    season: str,
    *,
    pool: str = "pending",
    variation: int | None = None,
    generation: int | None = None,
) -> list[dict[str, Any]]:
    cfg = load_config()
    if generation is None:
        generation = get_active_generation(cfg, biome, season)
    pools = ["pending", "approved"] if pool == "both" else [pool]
    tiles: list[dict[str, Any]] = []
    for pl in pools:
        root = repo_path(cfg["paths"]["pending" if pl == "pending" else "approved"])
        base = root / biome / season
        if not base.is_dir():
            continue
        for webp in sorted(base.rglob("*.webp")):
            rel = webp.relative_to(root)
            row = _parse_webp_rel(rel, pl)
            if row is None:
                continue
            if generation is not None and row.get("generation") != generation:
                continue
            if variation is not None and row["variation"] != variation:
                continue
            row["has_composed"] = webp.with_suffix(".composed.png").is_file()
            row["has_sail"] = webp.with_suffix(".sail.png").is_file()
            sp = spec_path(row["id"])
            row["has_spec"] = sp.is_file()
            row["spec_status"] = ""
            if sp.is_file():
                try:
                    spec = json.loads(sp.read_text(encoding="utf-8"))
                    row["spec_status"] = str(spec.get("status", ""))
                except (json.JSONDecodeError, OSError):
                    pass
            if pl == "pending":
                row["can_approve"] = True
            else:
                row["can_approve"] = False
            tiles.append(row)
    return tiles


def build_mosaic(
    biome: str,
    season: str,
    variation: int = 1,
    *,
    pool: str = "pending",
    generation: int | None = None,
) -> dict[str, Any]:
    cfg = load_config()
    if generation is None:
        generation = get_active_generation(cfg, biome, season)
    layout = _load_lake_layout()
    cells: list[dict[str, Any]] = []
    missing: list[str] = []
    for row in layout:
        for topology in row:
            path = _tile_path(
                pool, biome, season, topology, variation, generation=generation
            )
            rel = path.relative_to(repo_path(".")).as_posix() if path.is_file() else ""
            tid = tile_id(biome, season, topology, variation, generation=generation)
            cell: dict[str, Any] = {
                "topology": topology,
                "label": topology.replace("_", " "),
                "id": tid,
                "generation": generation,
                "missing": not path.is_file(),
            }
            if path.is_file():
                asset_rel = terrain_asset_relpath(
                    biome, season, topology, variation, generation=generation, ext=".webp"
                )
                cell["image_url"] = f"/assets/tiles/{pool}/{asset_rel.as_posix()}"
                cell["can_approve"] = pool == "pending"
            else:
                missing.append(tid)
            cells.append(cell)
    return {
        "biome": biome,
        "season": season,
        "variation": variation,
        "generation": generation,
        "pool": pool,
        "rows": len(layout),
        "cols": len(layout[0]) if layout else 0,
        "cells": cells,
        "missing": missing,
    }


def approve_tile(tile_id_str: str) -> dict[str, Any]:
    sp = spec_path(tile_id_str)
    if not sp.is_file():
        return {"ok": False, "error": f"No spec file: {_rel_repo(sp)}"}
    spec = json.loads(sp.read_text(encoding="utf-8"))
    pending, approved = resolve_tile_paths(spec)
    if not pending.is_file():
        return {"ok": False, "error": f"Not in pending: {_rel_repo(pending)}"}
    approved.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(pending, approved)
    sail_src = pending.with_suffix(".sail.png")
    if sail_src.is_file():
        shutil.copy2(sail_src, approved.with_suffix(".sail.png"))
    composed_src = pending.with_suffix(".composed.png")
    if composed_src.is_file():
        shutil.copy2(composed_src, approved.with_suffix(".composed.png"))
    spec["status"] = "approved"
    normalize_spec_paths(spec)
    sp.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
    return {
        "ok": True,
        "id": tile_id_str,
        "approved_path": _rel_repo(approved),
    }

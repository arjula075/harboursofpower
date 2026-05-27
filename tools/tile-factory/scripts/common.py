"""Shared paths and config for tile-factory."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
FACTORY_ROOT = REPO_ROOT / "tools" / "tile-factory"


def load_config() -> dict[str, Any]:
    with (FACTORY_ROOT / "config.json").open(encoding="utf-8") as f:
        return json.load(f)


def load_topology_rules() -> dict[str, Any]:
    with (FACTORY_ROOT / "topology_rules.json").open(encoding="utf-8") as f:
        return json.load(f)


def topology_by_id(topology_id: str) -> dict[str, Any]:
    rules = load_topology_rules()
    for t in rules["topologies"]:
        if t["id"] == topology_id:
            return t
    raise KeyError(f"Unknown topology: {topology_id}")


def repo_path(rel: str) -> Path:
    return REPO_ROOT / rel


def edge_strip_path(biome: str, season: str, edge_kind: str) -> Path:
    return FACTORY_ROOT / "edges" / biome / season / f"{edge_kind}.png"


def generation_dir_name(generation: int) -> str:
    """Folder name for a prompt/art generation batch (g001, g002, …)."""
    return f"g{generation:03d}"


def is_generation_dir(name: str) -> bool:
    return len(name) == 4 and name.startswith("g") and name[1:].isdigit()


def parse_generation_dir(name: str) -> int | None:
    if is_generation_dir(name):
        return int(name[1:])
    return None


def tile_id(
    biome: str,
    season: str,
    topology: str,
    variation: int,
    *,
    generation: int = 1,
) -> str:
    slot = f"v{variation:02d}"
    if generation <= 1:
        return f"{biome}/{season}/{topology}/{slot}"
    return f"{biome}/{season}/{generation_dir_name(generation)}/{topology}/{slot}"


def terrain_asset_relpath(
    biome: str,
    season: str,
    topology: str,
    variation: int,
    *,
    generation: int = 1,
    ext: str,
) -> Path:
    """Relative path under pending/, approved/, or raw/ roots."""
    slot = f"v{variation:02d}"
    if generation <= 1:
        return Path(biome) / season / topology / f"{slot}{ext}"
    return Path(biome) / season / generation_dir_name(generation) / topology / f"{slot}{ext}"


def list_generations(biome: str, season: str) -> list[int]:
    """Known generation numbers for a biome/season (1 = legacy flat layout)."""
    cfg = load_config()
    found: set[int] = set()
    for key in ("pending", "approved"):
        base = repo_path(cfg["paths"][key]) / biome / season
        if not base.is_dir():
            continue
        for child in base.iterdir():
            if not child.is_dir():
                continue
            gen = parse_generation_dir(child.name)
            if gen is not None:
                found.add(gen)
            elif child.name not in ("overlays",) and any(child.iterdir()):
                # Legacy: topology folders directly under season (e.g. totally_land/)
                found.add(1)
    raw_base = FACTORY_ROOT / "raw" / biome / season
    if raw_base.is_dir():
        for child in raw_base.iterdir():
            if child.is_dir():
                gen = parse_generation_dir(child.name)
                if gen is not None:
                    found.add(gen)
                elif child.name not in ("overlays",):
                    found.add(1)
    return sorted(found) if found else [1]


def next_generation(biome: str, season: str) -> int:
    gens = list_generations(biome, season)
    return max(gens) + 1


def set_active_generation(cfg: dict, biome: str, season: str, generation: int) -> dict:
    """Persist which generation batch review/compositing should prefer."""
    active = dict(cfg.get("active_generation", {}))
    per_biome = dict(active.get(biome, {}))
    per_biome[season] = generation
    active[biome] = per_biome
    cfg = dict(cfg)
    cfg["active_generation"] = active
    return cfg


def get_active_generation(cfg: dict, biome: str, season: str) -> int:
    active = cfg.get("active_generation", {})
    if isinstance(active, dict):
        per_biome = active.get(biome, {})
        if isinstance(per_biome, dict) and season in per_biome:
            return int(per_biome[season])
    gens = list_generations(biome, season)
    return gens[-1] if gens else 1


def spec_path(tile_id_str: str) -> Path:
    return FACTORY_ROOT / "specs" / f"{tile_id_str.replace('/', '__')}.json"


def md5_file(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def band_px(cfg: dict[str, Any]) -> int:
    return int(cfg["edge_band_px"])

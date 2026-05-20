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


def tile_id(biome: str, season: str, topology: str, variation: int) -> str:
    return f"{biome}/{season}/{topology}/v{variation:02d}"


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

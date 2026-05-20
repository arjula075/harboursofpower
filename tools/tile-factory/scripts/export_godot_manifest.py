"""Export data/tiles_manifest.json from approved tiles + specs."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from common import load_config, load_topology_rules, repo_path, spec_path


def main() -> int:
    cfg = load_config()
    approved = repo_path(cfg["paths"]["approved"])
    entries = []
    rules = {t["id"]: t for t in load_topology_rules()["topologies"]}
    for webp in sorted(approved.rglob("*.webp")):
        rel = webp.relative_to(approved)
        parts = rel.parts
        if len(parts) < 4:
            continue
        biome, season, topology, var_file = parts[0], parts[1], parts[2], parts[3]
        variation = int(var_file.replace("v", "").replace(".webp", ""))
        tid = f"{biome}/{season}/{topology}/v{variation:02d}"
        spec_file = spec_path(tid)
        meta = {"id": tid, "biome": biome, "season": season, "topology": topology, "variation": variation}
        if spec_file.is_file():
            with spec_file.open(encoding="utf-8") as f:
                meta.update({k: v for k, v in json.load(f).items() if k in ("wang_mask", "terrain_class", "legacy_id")})
        if topology in rules:
            meta.setdefault("wang_mask", rules[topology].get("wang_mask"))
            meta.setdefault("terrain_class", rules[topology].get("terrain_class"))
            meta.setdefault("legacy_id", rules[topology].get("legacy_id"))
        meta["texture"] = str(webp.relative_to(repo_path("."))).replace("\\", "/")
        sail = webp.with_suffix(".sail.png")
        if sail.is_file():
            meta["sail_mask"] = str(sail.relative_to(repo_path("."))).replace("\\", "/")
        entries.append(meta)
    manifest_path = repo_path(cfg["paths"]["manifest"])
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {"version": 1, "tiles": entries}
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"Exported {len(entries)} tiles -> {manifest_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Generate v01 only for topologies missing raw (diagonals etc.)."""
from __future__ import annotations

import sys
from pathlib import Path

from common import load_config, load_topology_rules, spec_path
from regenerate import regenerate

sys.path.insert(0, str(Path(__file__).parent))


def main() -> int:
    cfg = load_config()
    failed = 0
    for topo in load_topology_rules()["topologies"]:
        if topo.get("phase") != "v1" or topo["id"] == "totally_sea":
            continue
        tid = f"{cfg['biome']}/{cfg['season']}/{topo['id']}/v01"
        raw = Path(json_raw_path(tid, cfg))
        if raw.is_file():
            print(f"Skip {tid} (raw exists)")
            continue
        if not regenerate(tid, max_attempts=3, use_compose=False, lenient=True):
            failed += 1
    return 1 if failed else 0


def json_raw_path(tid: str, cfg: dict) -> str:
    import json

    with spec_path(tid).open(encoding="utf-8") as f:
        return json.load(f)["raw_path"]


if __name__ == "__main__":
    sys.exit(main())

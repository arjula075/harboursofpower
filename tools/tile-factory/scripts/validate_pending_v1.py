"""Validate pending v1 terrain tiles for current biome (composed WebP)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from common import FACTORY_ROOT, load_config, load_topology_rules, repo_path, spec_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variations", type=int, nargs="*", default=[1, 2, 3])
    parser.add_argument("--proof", action="store_true", help="Only variation 1")
    args = parser.parse_args()

    from validate_tile import validate

    cfg = load_config()
    biome, season = cfg["biome"], cfg["season"]
    variations = [1] if args.proof else sorted(set(args.variations))
    failed = 0
    checked = 0

    for topo in load_topology_rules()["topologies"]:
        if topo.get("phase") != "v1":
            continue
        for v in variations:
            tid = f"{biome}/{season}/{topo['id']}/v{v:02d}"
            sp = spec_path(tid)
            if not sp.is_file():
                continue
            pending = repo_path(f"assets/tiles/pending/{tid}.webp")
            if not pending.is_file():
                print(f"SKIP (no pending): {tid}")
                continue
            report = validate(sp)  # spec path; validator loads pending/composed webp
            checked += 1
            if report["ok"]:
                print(f"OK   {tid}")
            else:
                failed += 1
                print(f"FAIL {tid}: {', '.join(report['errors'])}")

    print(f"\nValidated {checked} tiles, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

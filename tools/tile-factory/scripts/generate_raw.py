"""Generate raw PNG tiles from specs using OpenAI Images API."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from common import FACTORY_ROOT, load_config, repo_path
from openai_client import generate_image, save_image_response
from prompts import port_overlay_prompt, terrain_prompt


def log_cost(report_dir: Path, entry: dict) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    with (report_dir / "api_cost.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def generate_spec(spec: dict, cfg: dict, force: bool = False) -> bool:
    raw = Path(spec["raw_path"])
    if raw.is_file() and not force:
        print(f"Skip existing {spec['id']}")
        return True

    if spec["kind"] == "terrain":
        prompt = terrain_prompt(spec["topology"], int(spec["variation"]))
    elif spec["kind"] == "port_overlay":
        culture = spec["culture"].replace("port_", "") if "culture" in spec else "greek"
        prompt = port_overlay_prompt(culture, int(spec["variation"]))
    else:
        raise ValueError(f"Unknown kind {spec['kind']}")

    model = cfg.get("openai_image_model", "gpt-image-1")
    size = int(cfg["tile_size"])

    print(f"Generating {spec['id']} ({model})...")
    response = generate_image(prompt, cfg)
    save_image_response(response, raw, size)
    log_cost(
        repo_path(cfg["paths"]["reports"]),
        {
            "ts": datetime.now(timezone.utc).isoformat(),
            "kind": spec["kind"],
            "id": spec["id"],
            "model": model,
            "raw_path": str(raw),
        },
    )
    print(f"  -> {raw}")
    return True


def iter_specs(
    *,
    kind: str | None,
    topology: str | None,
    proof_only: bool,
) -> list[dict]:
    out: list[dict] = []
    for path in sorted((FACTORY_ROOT / "specs").glob("*.json")):
        with path.open(encoding="utf-8") as f:
            spec = json.load(f)
        if kind and spec.get("kind") != kind:
            continue
        if topology and spec.get("topology") != topology:
            continue
        if proof_only:
            if spec.get("kind") != "terrain":
                continue
            tid = spec.get("topology")
            var = int(spec.get("variation", 99))
            if tid == "totally_sea" and var <= 3:
                out.append(spec)
            elif tid == "totally_land" and var == 1:
                out.append(spec)
            elif tid == "horizontal_top_land" and var == 1:
                out.append(spec)
            continue
        out.append(spec)
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kind", choices=["terrain", "port_overlay"])
    parser.add_argument("--topology")
    parser.add_argument("--proof", action="store_true", help="Phase1 proof set only (5 tiles)")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("id", nargs="?", help="Single tile id")
    args = parser.parse_args()
    cfg = load_config()

    if args.id:
        from common import spec_path

        sp = spec_path(args.id)
        with sp.open(encoding="utf-8") as f:
            specs = [json.load(f)]
    else:
        specs = iter_specs(kind=args.kind, topology=args.topology, proof_only=args.proof)

    if not specs:
        print("No specs matched.")
        return 1

    failed = 0
    for spec in specs:
        try:
            generate_spec(spec, cfg, force=args.force)
        except Exception as e:
            failed += 1
            print(f"FAIL {spec['id']}: {e}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

"""Generate canonical edge strips via OpenAI Images API."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

from common import band_px, edge_strip_path, load_config, repo_path
from openai_client import generate_image, save_image_response
from prompts import EDGE_PROMPTS


def log_cost(report_dir: Path, entry: dict) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    line = json.dumps(entry) + "\n"
    with (report_dir / "api_cost.jsonl").open("a", encoding="utf-8") as f:
        f.write(line)


def generate_strip(edge_kind: str, biome: str, season: str, cfg: dict) -> Path:
    size = int(cfg["tile_size"])
    band = band_px(cfg)
    model = cfg.get("openai_image_model", "gpt-image-1")
    prompt = EDGE_PROMPTS[edge_kind]
    print(f"Generating edge strip {edge_kind} ({model})...")
    response = generate_image(prompt, cfg)

    tmp = repo_path(f"tools/tile-factory/raw/_edges/{edge_kind}_full.png")
    save_image_response(response, tmp, size)

    full = Image.open(tmp).convert("RGB")
    out = edge_strip_path(biome, season, edge_kind)
    out.parent.mkdir(parents=True, exist_ok=True)

    if edge_kind in ("land_sea", "sea_land"):
        # Horizontal transition: store as wide band (size x band)
        strip = full.crop((0, size // 2 - band // 2, size, size // 2 + band // 2))
        strip = strip.resize((size, band), Image.Resampling.LANCZOS)
    else:
        # Homogeneous: take north band
        strip = full.crop((0, 0, size, band))

    strip.save(out)
    log_cost(
        repo_path(cfg["paths"]["reports"]),
        {
            "ts": datetime.now(timezone.utc).isoformat(),
            "kind": "edge_strip",
            "edge_kind": edge_kind,
            "model": model,
            "path": str(out),
        },
    )
    print(f"  -> {out}")
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--biome", default=None)
    parser.add_argument("--season", default=None)
    parser.add_argument("--only", nargs="*", choices=list(EDGE_PROMPTS.keys()))
    args = parser.parse_args()
    cfg = load_config()
    biome = args.biome or cfg["biome"]
    season = args.season or cfg["season"]
    kinds = args.only or list(EDGE_PROMPTS.keys())
    for kind in kinds:
        generate_strip(kind, biome, season, cfg)
    return 0


if __name__ == "__main__":
    sys.exit(main())

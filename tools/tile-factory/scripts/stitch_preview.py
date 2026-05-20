"""Build stitch preview PNG/HTML for a topology or sea grid."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image

from common import load_config, repo_path


def build_grid(tile_path: Path, cols: int, rows: int, out: Path) -> None:
    tile = Image.open(tile_path).convert("RGB")
    w, h = tile.size
    grid = Image.new("RGB", (w * cols, h * rows))
    for row in range(rows):
        for col in range(cols):
            grid.paste(tile, (col * w, row * h))
    out.parent.mkdir(parents=True, exist_ok=True)
    grid.save(out)
    print(f"Wrote {out}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tile", type=Path, help="Path to a single webp/png tile")
    parser.add_argument("--topology", type=str, help="Use first pending match for topology")
    parser.add_argument("--grid", type=int, nargs=2, default=[3, 3], metavar=("COLS", "ROWS"))
    parser.add_argument("-o", "--out", type=Path, default=None)
    args = parser.parse_args()
    cfg = load_config()
    tile_path = args.tile

    def prefer_composed(p: Path) -> Path:
        composed = p.with_suffix(".composed.png")
        return composed if composed.is_file() else p

    if args.topology and not tile_path:
        pending = repo_path(cfg["paths"]["pending"])
        matches = sorted(pending.rglob(f"*/{args.topology}/*.webp"))
        if not matches:
            matches = sorted(pending.rglob(f"**/{args.topology}/**/*.webp"))
        if not matches:
            print(f"No pending tile for topology {args.topology}", file=sys.stderr)
            return 1
        tile_path = prefer_composed(matches[0])
    elif tile_path:
        tile_path = prefer_composed(tile_path)
    if not tile_path or not tile_path.is_file():
        print("Provide --tile or --topology", file=sys.stderr)
        return 1
    out = args.out or (repo_path("tools/tile-factory/reports") / f"stitch_{tile_path.stem}.png")
    build_grid(tile_path, args.grid[0], args.grid[1], out)
    return 0


if __name__ == "__main__":
    sys.exit(main())

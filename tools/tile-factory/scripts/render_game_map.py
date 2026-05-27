"""CLI: render chart areas from approved terrain tiles (see tile_texture_render.py)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from common import load_config, repo_path
from tile_texture_render import (
    chart_area_bounds,
    load_chart_index,
    render_chart_area_image,
    texture_preview_meta,
)
from tile_texture_render import align_start, load_merged_shore_grid  # noqa: F401 — re-export for tests


def main() -> int:
    parser = argparse.ArgumentParser(description="Render game map from approved tiles")
    parser.add_argument("--biome", default=None, help="Biome id (default: config.json biome)")
    parser.add_argument("--season", default="summer")
    parser.add_argument("--variation", type=int, default=1, help="Slot v01–v03 (default 1)")
    parser.add_argument("--generation", type=int, default=None)
    parser.add_argument("--pool", choices=("approved", "pending"), default="approved")
    parser.add_argument("--chart-area", default=None, help="e.g. aegean (default: full chart)")
    parser.add_argument("--width", type=int, default=2000)
    parser.add_argument("--height", type=int, default=1000)
    parser.add_argument("--scale", type=int, default=8, help="Pixels per 3×3 shore cell")
    parser.add_argument("-o", "--out", type=Path, default=None)
    args = parser.parse_args()

    cfg = load_config()
    biome = args.biome or str(cfg["biome"])
    season = args.season

    if not args.chart_area:
        # Full chart: synthetic id handled via bounds
        index = load_chart_index()
        if not index.get("chart_areas"):
            print("Missing chart_area_index.json", file=sys.stderr)
            return 1
        x0, y0, x1, y1 = 0, 0, args.width, args.height
        from tile_texture_render import load_texture_cache, render_map

        grid, step = load_merged_shore_grid()
        if not grid:
            print("No shore_fixed tilemaps found", file=sys.stderr)
            return 1
        x0 = align_start(x0, step)
        y0 = align_start(y0, step)
        cell_px = max(4, int(args.scale))
        textures = load_texture_cache(
            biome,
            season,
            args.variation,
            generation=args.generation,
            cell_px=cell_px,
            pool=args.pool,
        )
        if not textures:
            print(f"No textures for {biome}/{season} pool={args.pool}", file=sys.stderr)
            return 1
        mosaic = render_map(
            grid,
            x0=x0,
            y0=y0,
            x1=x1,
            y1=y1,
            step=step,
            cell_px=cell_px,
            textures=textures,
        )
        out_name = f"game_map_{biome}_full_v{args.variation:02d}.png"
    else:
        if chart_area_bounds(args.chart_area) is None:
            print(f"Unknown chart area: {args.chart_area}", file=sys.stderr)
            return 1
        try:
            mosaic = render_chart_area_image(
                args.chart_area,
                biome=biome,
                season=season,
                variation=args.variation,
                generation=args.generation,
                pool=args.pool,
                scale=args.scale,
            )
        except (FileNotFoundError, ValueError) as exc:
            print(exc, file=sys.stderr)
            return 1
        out_name = f"game_map_{biome}_{args.chart_area}_v{args.variation:02d}.png"

    reports = repo_path(cfg["paths"]["reports"])
    reports.mkdir(parents=True, exist_ok=True)
    if args.out:
        out_path = args.out if args.out.is_absolute() else repo_path(str(args.out))
    else:
        out_path = reports / out_name

    mosaic.save(out_path)
    print(f"Wrote {out_path} ({mosaic.size[0]}×{mosaic.size[1]} px)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

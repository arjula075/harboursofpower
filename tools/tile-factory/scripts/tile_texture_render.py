"""Render chart areas from shore_fixed topology + approved/pending tile textures."""
from __future__ import annotations

import io
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from common import list_generations, load_config, repo_path, terrain_asset_relpath

_PIL_INSTALL_HINT = (
    "Pillow is required for tile map preview. From repo root:\n"
    "  python3 -m venv tools/tile-factory/.venv\n"
    "  tools/tile-factory/.venv/bin/pip install -r tools/tile-factory/requirements.txt\n"
    "  tools/tile-factory/.venv/bin/python3 tools/tile-factory/review_server.py"
)


def _pil():
    try:
        from PIL import Image
    except ImportError as exc:
        raise ImportError(_PIL_INSTALL_HINT) from exc
    return Image

REPO = Path(__file__).resolve().parents[3]
SHORE_FIXED_DIR = REPO / "docs" / "chart_area_tilemaps_and_maps" / "shore_fixed"
CHART_INDEX = REPO / "docs" / "chart_area_tilemaps_and_maps" / "chart_area_index.json"

V1_TOPOLOGIES = frozenset(
    {
        "totally_land",
        "totally_sea",
        "horizontal_top_land",
        "horizontal_bottom_land",
        "vertical_left_land",
        "vertical_right_land",
        "diagonal_rising_left_land",
        "diagonal_rising_right_land",
        "diagonal_descending_left_land",
        "diagonal_descending_right_land",
    }
)

_PRIORITY = {"totally_sea": 0, "totally_land": 1}


def _prio(topo: str) -> int:
    if topo in _PRIORITY:
        return _PRIORITY[topo]
    return 2 + len(topo)


def normalize_topology(name: str) -> str:
    if name in V1_TOPOLOGIES:
        return name
    if name in ("totally_land", "totally_sea"):
        return name
    # Corner-Wang names (NW_land_NE_sea_…) must not collapse to flat land/sea.
    if name.startswith("NW_"):
        parts = name.split("_")
        if len(parts) % 2 != 0:
            return "totally_sea"
        corners: dict[str, bool] = {}
        for i in range(0, len(parts), 2):
            label, kind = parts[i], parts[i + 1]
            if label not in ("NW", "NE", "SE", "SW") or kind not in ("land", "sea"):
                return "totally_sea"
            corners[label] = kind == "land"
        nw, ne, se, sw = corners["NW"], corners["NE"], corners["SE"], corners["SW"]
        if nw and ne and se and sw:
            return "totally_land"
        if not nw and not ne and not se and not sw:
            return "totally_sea"
        key = (nw, ne, se, sw)
        corner_to_v1 = {
            (True, True, False, False): "horizontal_top_land",
            (False, False, True, True): "horizontal_bottom_land",
            (True, False, False, True): "diagonal_rising_left_land",
            (False, True, True, False): "diagonal_rising_right_land",
            (True, False, True, False): "diagonal_descending_left_land",
            (False, True, False, True): "diagonal_descending_right_land",
            (True, False, False, False): "vertical_left_land",
            (False, True, False, False): "vertical_right_land",
            (False, False, False, True): "vertical_left_land",
            (False, False, True, False): "vertical_right_land",
            (True, True, True, False): "horizontal_top_land",
            (True, True, False, True): "horizontal_top_land",
            (True, False, True, True): "horizontal_bottom_land",
            (False, True, True, True): "horizontal_bottom_land",
        }
        return corner_to_v1.get(key, "horizontal_top_land")
    if name.startswith("cape_"):
        fallbacks = {
            "cape_north_land": "horizontal_bottom_land",
            "cape_south_land": "horizontal_top_land",
            "cape_east_land": "vertical_left_land",
            "cape_west_land": "vertical_right_land",
        }
        return fallbacks.get(name, "totally_land")
    return "totally_sea"


@lru_cache(maxsize=1)
def load_merged_shore_grid() -> tuple[dict[tuple[int, int], str], int]:
    merged: dict[tuple[int, int], str] = {}
    step = 3
    if not SHORE_FIXED_DIR.is_dir():
        return merged, step
    for path in sorted(SHORE_FIXED_DIR.glob("*_tilemap.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        step = int(data.get("coordinate_system", {}).get("final_tile_size", step))
        for t in data.get("tiles", []):
            key = (int(t["x"]), int(t["y"]))
            topo = normalize_topology(str(t["tile"]))
            if key in merged:
                if _prio(topo) >= _prio(merged[key]):
                    merged[key] = topo
            else:
                merged[key] = topo
    return merged, step


def align_start(v: int, step: int) -> int:
    r = v % step
    return v if r == 0 else v + (step - r)


def load_chart_index() -> dict[str, Any]:
    if not CHART_INDEX.is_file():
        return {"chart_areas": []}
    return json.loads(CHART_INDEX.read_text(encoding="utf-8"))


def chart_area_bounds(chart_area_id: str) -> dict[str, int] | None:
    for area in load_chart_index().get("chart_areas", []):
        if isinstance(area, dict) and str(area.get("id")) == chart_area_id:
            b = area.get("bounds")
            if isinstance(b, dict):
                return {
                    "x0": int(b["x0"]),
                    "y0": int(b["y0"]),
                    "x1": int(b["x1"]),
                    "y1": int(b["y1"]),
                }
    return None


def find_approved_image(
    biome: str,
    season: str,
    topology: str,
    variation: int,
    *,
    generation: int | None,
    pool: str = "approved",
) -> Path | None:
    cfg = load_config()
    root = repo_path(cfg["paths"][pool])
    if generation is not None:
        candidates = [generation]
    else:
        candidates = list_generations(biome, season)
        if not candidates:
            candidates = [1]

    for gen in reversed(candidates):
        rel = terrain_asset_relpath(biome, season, topology, variation, generation=gen, ext=".webp")
        ext_path = root / rel
        composed = ext_path.with_suffix(".composed.png")
        if composed.is_file():
            return composed
        if ext_path.is_file():
            return ext_path
    legacy = root / biome / season / topology / f"v{variation:02d}.webp"
    composed = legacy.with_suffix(".composed.png")
    if composed.is_file():
        return composed
    if legacy.is_file():
        return legacy
    return None


def load_texture_cache(
    biome: str,
    season: str,
    variation: int,
    *,
    generation: int | None,
    cell_px: int,
    pool: str,
) -> dict:
    Image = _pil()
    cache: dict = {}
    for topo in V1_TOPOLOGIES:
        path = find_approved_image(
            biome, season, topo, variation, generation=generation, pool=pool
        )
        if path is None:
            continue
        img = Image.open(path).convert("RGB")
        if img.size != (cell_px, cell_px):
            img = img.resize((cell_px, cell_px), Image.Resampling.LANCZOS)
        cache[topo] = img
    return cache


def render_map(
    grid: dict[tuple[int, int], str],
    *,
    x0: int,
    y0: int,
    x1: int,
    y1: int,
    step: int,
    cell_px: int,
    textures: dict[str, Any],
    default_topo: str = "totally_sea",
):
    Image = _pil()
    cols = len(range(x0, x1, step))
    rows = len(range(y0, y1, step))
    out = Image.new("RGB", (cols * cell_px, rows * cell_px))
    fallback = textures.get(default_topo) or textures.get("totally_land")
    if fallback is None:
        fallback = Image.new("RGB", (cell_px, cell_px), (30, 80, 120))

    for row_i, y in enumerate(range(y0, y1, step)):
        for col_i, x in enumerate(range(x0, x1, step)):
            topo = grid.get((x, y), default_topo)
            tile = textures.get(topo, fallback)
            out.paste(tile, (col_i * cell_px, row_i * cell_px))
    return out


def render_chart_area_image(
    chart_area_id: str,
    *,
    biome: str | None = None,
    season: str = "summer",
    variation: int = 1,
    generation: int | None = None,
    pool: str = "approved",
    scale: int = 10,
):
    bounds = chart_area_bounds(chart_area_id)
    if bounds is None:
        raise ValueError(f"unknown chart area: {chart_area_id}")

    cfg = load_config()
    biome_id = biome or str(cfg.get("biome", "sparse_olive"))
    cell_px = max(4, int(scale))

    grid, step = load_merged_shore_grid()
    if not grid:
        raise FileNotFoundError(f"no shore_fixed tilemaps under {SHORE_FIXED_DIR}")

    x0 = align_start(bounds["x0"], step)
    y0 = align_start(bounds["y0"], step)
    x1, y1 = bounds["x1"], bounds["y1"]

    textures = load_texture_cache(
        biome_id,
        season,
        variation,
        generation=generation,
        cell_px=cell_px,
        pool=pool,
    )
    if not textures:
        raise FileNotFoundError(
            f"no {pool} textures for {biome_id}/{season} v{variation:02d}"
        )

    return render_map(
        grid,
        x0=x0,
        y0=y0,
        x1=x1,
        y1=y1,
        step=step,
        cell_px=cell_px,
        textures=textures,
    )


def render_chart_area_png(
    chart_area_id: str,
    **kwargs: Any,
) -> bytes:
    buf = io.BytesIO()
    render_chart_area_image(chart_area_id, **kwargs).save(buf, format="PNG")
    return buf.getvalue()


def texture_preview_meta() -> dict[str, Any]:
    cfg = load_config()
    biomes = []
    for entry in cfg.get("biome_catalog", []):
        if not isinstance(entry, dict):
            continue
        bid = str(entry.get("id", ""))
        if bid:
            biomes.append({"id": bid, "name": str(entry.get("name", bid))})
    if not biomes:
        biomes = [{"id": str(cfg.get("biome", "sparse_olive")), "name": "Default"}]

    areas = []
    for area in load_chart_index().get("chart_areas", []):
        if not isinstance(area, dict):
            continue
        aid = str(area.get("id", ""))
        if not aid:
            continue
        areas.append(
            {
                "id": aid,
                "name": str(area.get("name", aid)),
                "description": str(area.get("description", "")),
                "bounds": area.get("bounds"),
            }
        )

    active_gen = cfg.get("active_generation") or {}
    default_biome = str(cfg.get("biome", "sparse_olive"))
    gen_for_biome = active_gen.get(default_biome, {})
    default_generation = None
    if isinstance(gen_for_biome, dict):
        g = gen_for_biome.get(str(cfg.get("season", "summer")))
        if g is not None:
            default_generation = int(g)

    return {
        "chart_areas": areas,
        "biomes": biomes,
        "defaults": {
            "biome": default_biome,
            "season": str(cfg.get("season", "summer")),
            "variation": 1,
            "pool": "approved",
            "scale": 10,
            "generation": default_generation,
        },
        "topology_source": "docs/chart_area_tilemaps_and_maps/shore_fixed",
        "note": "Cape/channel topologies fall back to totally_land/sea until dedicated art exists.",
    }

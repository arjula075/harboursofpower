#!/usr/bin/env python3
"""Build 1×1 corner-Wang-16 tilemap (parallel asset set).

Default: upscale the proven 3×3 tilemap (mediterranean_recursive_tilemap_aegean_illyrian_restored.json)
to 1×1 land/sea, then assign corner-Wang tile names. This preserves islands, straits, and coasts
that PNG colour classification loses at 1px.

Optional --from-png re-runs semantic masking on docs/mi8l8sc4s5z81.png (less accurate).

Outputs (under docs/ by default):
  - mediterranean_recursive_tilemap_wang16_1px.json
  - mediterranean_recursive_tilemap_wang16_1px_mask.png
  - mediterranean_recursive_tilemap_wang16_1px_wang_preview.png
  - chart_area_tilemaps_and_maps_wang16_1px/{area}_tilemap.json
  - chart_area_tilemaps_and_maps_wang16_1px/chart_area_index.json
  - chart_area_tilemaps_and_maps_wang16_1px/{area}_map.png

Run from repo root:
  .venv/bin/python tools/build_recursive_tilemap_wang16_1px.py
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

REPO = Path(__file__).resolve().parents[1]
SOURCE_IMAGE = REPO / "docs" / "mi8l8sc4s5z81.png"
SOURCE_TILEMAP_3PX = REPO / "docs" / "mediterranean_recursive_tilemap_aegean_illyrian_restored.json"
CHART_INDEX_SRC = REPO / "docs" / "chart_area_tilemaps_and_maps" / "chart_area_index.json"

LOG_W = 2000
LOG_H = 1000
SUBDIVISION_SEQUENCE = [81, 27, 9, 3, 1]
FINAL_TILE_SIZE = 1
LAND_COMPONENT_MIN_PIXELS = 18
STEP_3PX = 3

FULL_LAND = "totally_land"
FULL_SEA = "totally_sea"

CORNER_ORDER = ("NW", "NE", "SE", "SW")

# 3×3 land patterns (True=land) inside each 3px coast macro-cell; sea lies on named side(s).
_COAST_3X3: dict[str, np.ndarray] = {
    "horizontal_top_land": np.array(
        [[1, 1, 1], [1, 1, 1], [0, 0, 0]], dtype=bool
    ),  # sea S
    "horizontal_bottom_land": np.array([[0, 0, 0], [1, 1, 1], [1, 1, 1]], dtype=bool),
    "vertical_left_land": np.array([[1, 1, 0], [1, 1, 0], [1, 1, 0]], dtype=bool),
    "vertical_right_land": np.array([[0, 1, 1], [0, 1, 1], [0, 1, 1]], dtype=bool),
    "diagonal_descending_right_land": np.array(
        [[1, 1, 0], [1, 0, 0], [0, 0, 0]], dtype=bool
    ),  # sea S,E
    "diagonal_descending_left_land": np.array(
        [[0, 1, 1], [0, 0, 1], [0, 0, 0]], dtype=bool
    ),
    "diagonal_rising_left_land": np.array([[0, 0, 0], [0, 0, 1], [1, 1, 1]], dtype=bool),
    "diagonal_rising_right_land": np.array([[0, 0, 0], [1, 0, 0], [1, 1, 1]], dtype=bool),
}


def classify_pixels(rgb: np.ndarray) -> np.ndarray:
    """Return int8 array: -1 ignore, 0 sea, 1 land.

    mi8l8sc4s5z81.png uses warm beige land (r dominant) and blue-grey sea (b dominant).
    The old rule (high r,g,b + low |r-g|) misclassified sea as land.
    """
    r = rgb[:, :, 0].astype(np.int16)
    g = rgb[:, :, 1].astype(np.int16)
    b = rgb[:, :, 2].astype(np.int16)
    lum = r + g + b
    chroma = np.maximum.reduce([r, g, b]) - np.minimum.reduce([r, g, b])
    out = np.full((rgb.shape[0], rgb.shape[1]), -1, dtype=np.int8)

    # Ignore: text, legend, near-black/grey ink (incl. much coast hatching)
    ignore = (lum < 75) | ((lum < 130) & (chroma < 25))
    out[ignore] = -1

    # Sea: b is the dominant channel (map water ≈ RGB 175,192,215)
    sea = (b >= g - 2) & (b >= r) & ((b - r) >= 18) & (b >= 155) & (b <= 235)
    out[sea] = 0

    # Land: warm beige (r≥g≥b), green regions, or pink colonies — must not overlap sea
    land_beige = (r >= g) & (g >= b + 5) & (r >= 215)
    land_green = (g >= r + 12) & (g >= b + 8) & (g >= 110)
    land_pink = (r >= 195) & (g <= 175) & (b <= 175) & (r >= g + 15)
    land = (land_beige | land_green | land_pink) & ~sea
    out[land] = 1

    return out


def neighbor_fill_ignore_fast(mask: np.ndarray, max_passes: int = 12) -> np.ndarray:
    """Vectorized-ish fill: repeated dilate known into ignore."""
    m = mask.copy()
    land = m == 1
    sea = m == 0
    for _ in range(max_passes):
        prev = m.copy()
        # For ignore cells, if any cardinal neighbour known, take majority of known 8-neigh
        unknown = m == -1
        if not unknown.any():
            break
        known = m >= 0
        # propagate: count land neighbours
        land_n = ndimage.convolve(land.astype(np.int16), np.ones((3, 3), dtype=np.int16), mode="constant") - land.astype(
            np.int16
        )
        sea_n = ndimage.convolve(sea.astype(np.int16), np.ones((3, 3), dtype=np.int16), mode="constant") - sea.astype(
            np.int16
        )
        fill_land = unknown & (land_n > sea_n) & (land_n > 0)
        fill_sea = unknown & (sea_n > land_n) & (sea_n > 0)
        fill_tie = unknown & (land_n == sea_n) & (land_n > 0)
        m[fill_land] = 1
        m[fill_sea] = 0
        m[fill_tie] = 1
        if np.array_equal(m, prev):
            break
    m[m == -1] = 0
    return m


def morph_land(mask: np.ndarray) -> np.ndarray:
    """Close then open on land (fills holes, removes specks)."""
    land = mask == 1
    struct = np.ones((3, 3), dtype=bool)
    land = ndimage.binary_closing(land, structure=struct)
    land = ndimage.binary_opening(land, structure=struct)
    out = np.zeros_like(mask)
    out[land] = 1
    out[~land] = 0
    return out


def land_mask_from_3px_tilemap(path: Path) -> np.ndarray:
    """Expand each 3px tile to a 3×3 1px block; preserves restored Mediterranean geography."""
    data = json.loads(path.read_text(encoding="utf-8"))
    step = int(data.get("coordinate_system", {}).get("final_tile_size", STEP_3PX))
    if step != STEP_3PX:
        raise ValueError(f"expected 3px source, got step={step}")

    land = np.zeros((LOG_H, LOG_W), dtype=bool)
    default_coast = _COAST_3X3["horizontal_top_land"]

    for t in data.get("tiles", []):
        x, y = int(t["x"]), int(t["y"])
        if x < 0 or y < 0 or x + step > LOG_W or y + step > LOG_H:
            continue
        typ = str(t.get("tile", FULL_SEA))
        if typ == FULL_LAND:
            land[y : y + step, x : x + step] = True
        elif typ == FULL_SEA:
            land[y : y + step, x : x + step] = False
        else:
            pat = _COAST_3X3.get(typ, default_coast)
            land[y : y + step, x : x + step] = pat

    return land


def remove_small_components(mask: np.ndarray, min_size: int) -> np.ndarray:
    """Drop land blobs and sea holes smaller than min_size pixels."""
    out = mask.copy()
    land = out == 1
    sea = out == 0
    land_labeled, n_land = ndimage.label(land)
    for label_id in range(1, n_land + 1):
        component = land_labeled == label_id
        if int(component.sum()) < min_size:
            out[component] = 0
    sea_labeled, n_sea = ndimage.label(out == 0)
    for label_id in range(1, n_sea + 1):
        component = sea_labeled == label_id
        if int(component.sum()) < min_size:
            out[component] = 1
    return out


def build_corner_grid(land: np.ndarray) -> np.ndarray:
    """(LOG_H+1) x (LOG_W+1) bool corners; edge clamps last row/col."""
    h, w = land.shape
    corners = np.zeros((h + 1, w + 1), dtype=bool)
    corners[:h, :w] = land
    corners[h, :w] = land[h - 1, :]
    corners[:h, w] = land[:, w - 1]
    corners[h, w] = land[h - 1, w - 1]
    return corners


def wang_tile_name(nw: bool, ne: bool, se: bool, sw: bool) -> str:
    if nw and ne and se and sw:
        return FULL_LAND
    if not nw and not ne and not se and not sw:
        return FULL_SEA
    parts = []
    for label, is_land in zip(CORNER_ORDER, (nw, ne, se, sw), strict=True):
        parts.append(f"{label}_{'land' if is_land else 'sea'}")
    return "_".join(parts)


def tiles_from_corners(corners: np.ndarray) -> tuple[list[dict], Counter]:
    """Enumerate all cells; sparse list of {x,y,tile}."""
    tiles: list[dict] = []
    counts: Counter = Counter()
    for y in range(LOG_H):
        for x in range(LOG_W):
            nw = bool(corners[y, x])
            ne = bool(corners[y, x + 1])
            se = bool(corners[y + 1, x + 1])
            sw = bool(corners[y + 1, x])
            name = wang_tile_name(nw, ne, se, sw)
            tiles.append({"x": x, "y": y, "tile": name})
            counts[name] += 1
    return tiles, counts


def collect_tile_types(counts: Counter) -> list[str]:
    types = [FULL_SEA, FULL_LAND]
    coast = sorted(k for k in counts if k not in (FULL_SEA, FULL_LAND))
    types.extend(coast)
    return types


def land_from_mask_png(path: Path) -> np.ndarray:
    rgb = np.array(Image.open(path).convert("RGB"))
    return rgb[:, :, 0] > 100


def write_mask_png(path: Path, land: np.ndarray) -> None:
    img = np.zeros((LOG_H, LOG_W, 3), dtype=np.uint8)
    img[land] = (180, 160, 120)
    img[~land] = (26, 74, 110)
    Image.fromarray(img, mode="RGB").save(path)


def write_wang_preview(path: Path, tiles: list[dict]) -> None:
    """Colour-code coast wang tiles; land/sea flat."""
    coast_colors = {
        0: (200, 120, 80),
        1: (220, 140, 90),
        2: (240, 160, 100),
        3: (180, 100, 70),
    }
    img = np.zeros((LOG_H, LOG_W, 3), dtype=np.uint8)
    grid = {(t["x"], t["y"]): t["tile"] for t in tiles}
    coast_idx = 0
    coast_map: dict[str, tuple[int, int, int]] = {}
    for y in range(LOG_H):
        for x in range(LOG_W):
            name = grid[(x, y)]
            if name == FULL_LAND:
                img[y, x] = (190, 170, 130)
            elif name == FULL_SEA:
                img[y, x] = (30, 80, 120)
            else:
                if name not in coast_map:
                    coast_map[name] = coast_colors[coast_idx % len(coast_colors)]
                    coast_idx += 1
                img[y, x] = coast_map[name]
    Image.fromarray(img, mode="RGB").save(path)


def extract_chart_area(tiles: list[dict], bounds: dict) -> list[dict]:
    x0, y0, x1, y1 = bounds["x0"], bounds["y0"], bounds["x1"], bounds["y1"]
    return [t for t in tiles if x0 <= t["x"] < x1 and y0 <= t["y"] < y1]


def write_area_map_png(path: Path, land: np.ndarray, bounds: dict) -> None:
    """Editor basemap: land/sea only (no per-pixel wang coast colours)."""
    x0, y0, x1, y1 = bounds["x0"], bounds["y0"], bounds["x1"], bounds["y1"]
    sub = land[y0:y1, x0:x1]
    img = np.zeros((sub.shape[0], sub.shape[1], 3), dtype=np.uint8)
    img[sub] = (190, 170, 130)
    img[~sub] = (30, 80, 120)
    Image.fromarray(img, mode="RGB").save(path)


def build_payload(
    tiles: list[dict],
    tile_types: list[str],
    counts: Counter,
    *,
    source_image: str,
    chart_bounds: dict | None = None,
    source_mode: str = "3px_upscale",
) -> dict:
    if source_mode == "3px_upscale":
        pipeline = {
            "source_mode": "3px_upscale",
            "source_tilemap_3px": SOURCE_TILEMAP_3PX.name,
            "upscale": "each 3px cell → 3×3 1px block; coast cells use oriented 3×3 land/sea pattern",
            "cleanup": ["no extra component filter (geometry from restored 3px tilemap)"],
            "wang": {
                "style": "corner",
                "interior_tiles": [FULL_LAND, FULL_SEA],
                "coast_naming": "NW_{land|sea}_NE_{land|sea}_SE_{land|sea}_SW_{land|sea}",
            },
            "note": "1px wang16 parallel set derived from aegean_illyrian_restored 3px tilemap.",
        }
    else:
        pipeline = {
            "source_mode": "png_semantic",
            "semantic_classes": ["sea", "land", "ignore"],
            "cleanup": [
                "neighbor-fill ignored pixels",
                "morphological close/open",
                f"remove small isolated land/sea components (<{LAND_COMPONENT_MIN_PIXELS}px)",
            ],
            "wang": {
                "style": "corner",
                "interior_tiles": [FULL_LAND, FULL_SEA],
                "coast_naming": "NW_{land|sea}_NE_{land|sea}_SE_{land|sea}_SW_{land|sea}",
            },
            "note": "PNG-derived mask (experimental; loses small islands).",
        }
    if chart_bounds:
        pipeline["chart_bounds"] = chart_bounds
    return {
        "source_image": source_image,
        "coordinate_system": {
            "origin": "top_left",
            "max_x": LOG_W,
            "max_y": LOG_H,
            "subdivision_sequence": SUBDIVISION_SEQUENCE,
            "final_tile_size": FINAL_TILE_SIZE,
        },
        "classification_pipeline": pipeline,
        "tile_types": tile_types,
        "tile_counts": dict(counts),
        "tiles": tiles,
    }


def write_chart_area_exports(
    chart_dir: Path,
    index: dict,
    tiles: list[dict],
    land: np.ndarray,
    *,
    src_label: str,
    source_mode: str,
) -> None:
    """Write per-area JSON + map PNG using bounds from chart_area_index.json."""
    chart_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        "source_tilemap": "mediterranean_recursive_tilemap_wang16_1px.json",
        "note": (
            "Parallel 1px corner-Wang-16 chart cuts (same bounds as chart_area_tilemaps_and_maps). "
            "Interior: totally_land / totally_sea; coast: corner bitmask names."
        ),
        "chart_areas": index["chart_areas"],
    }
    (chart_dir / "chart_area_index.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    for area in index["chart_areas"]:
        aid = area["id"]
        bounds = area["bounds"]
        area_tiles = extract_chart_area(tiles, bounds)
        area_types = collect_tile_types(Counter(t["tile"] for t in area_tiles))
        area_counts = Counter(t["tile"] for t in area_tiles)
        area_payload = build_payload(
            area_tiles,
            area_types,
            area_counts,
            source_image=src_label,
            chart_bounds=bounds,
            source_mode=source_mode,
        )
        area_payload["chart_area_id"] = aid
        out_json = chart_dir / f"{aid}_tilemap.json"
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(area_payload, f, separators=(",", ":"))
        write_area_map_png(chart_dir / f"{aid}_map.png", land, bounds)
        print(f"  {aid}: {len(area_tiles):,} tiles -> {out_json.name}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO / "docs",
        help="Directory for full-map JSON and mask PNGs",
    )
    parser.add_argument(
        "--chart-dir",
        type=Path,
        default=REPO / "docs" / "chart_area_tilemaps_and_maps_wang16_1px",
        help="Parallel chart-area tilemaps",
    )
    parser.add_argument("--skip-chart-areas", action="store_true")
    parser.add_argument(
        "--from-png",
        action="store_true",
        help="Build land mask from mi8l8sc4s5z81.png colour rules instead of 3px tilemap upscale",
    )
    parser.add_argument(
        "--maps-only",
        action="store_true",
        help="Only rewrite chart-area *_map.png from land mask (fast editor basemap refresh)",
    )
    parser.add_argument(
        "--split-only",
        action="store_true",
        help=(
            "Split existing full-map JSON into chart-area files using bounds from "
            "chart_area_tilemaps_and_maps/chart_area_index.json (no 3px/PNG rebuild)"
        ),
    )
    parser.add_argument(
        "--full-tilemap",
        type=Path,
        default=None,
        help="Full-map JSON for --split-only (default: output-dir/mediterranean_recursive_tilemap_wang16_1px.json)",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip Phase A 'Are you sure?' prompt (automation only)",
    )
    args = parser.parse_args()

    if args.maps_only and args.split_only:
        raise SystemExit("--maps-only and --split-only are mutually exclusive")

    if not (args.maps_only or args.split_only):
        from chunk_map_phase_a import confirm_tile_generation

        if not confirm_tile_generation(assume_yes=args.yes):
            raise SystemExit("Aborted.")

    out_dir = args.output_dir
    chart_dir = args.chart_dir
    index = json.loads(CHART_INDEX_SRC.read_text(encoding="utf-8"))

    if args.split_only:
        full_path = args.full_tilemap or (out_dir / "mediterranean_recursive_tilemap_wang16_1px.json")
        mask_path = out_dir / "mediterranean_recursive_tilemap_wang16_1px_mask.png"
        if not full_path.is_file():
            raise SystemExit(f"Missing full tilemap: {full_path}")
        print(f"Loading {full_path.name} …")
        data = json.loads(full_path.read_text(encoding="utf-8"))
        tiles = data.get("tiles", [])
        if not isinstance(tiles, list):
            raise SystemExit("full tilemap has no tiles[]")
        src_label = str(data.get("source_image", SOURCE_TILEMAP_3PX.name))
        pipeline = data.get("classification_pipeline", {})
        source_mode = str(pipeline.get("source_mode", "3px_upscale"))
        if mask_path.is_file():
            land = land_from_mask_png(mask_path)
        else:
            print("Mask PNG missing — building land grid from totally_land tiles (slow) …")
            land = np.zeros((LOG_H, LOG_W), dtype=bool)
            for t in tiles:
                if t.get("tile") == FULL_LAND:
                    land[int(t["y"]), int(t["x"])] = True
        print(f"Splitting into {len(index['chart_areas'])} chart areas …")
        write_chart_area_exports(chart_dir, index, tiles, land, src_label=src_label, source_mode=source_mode)
        print("Done (split only).")
        return

    if args.from_png:
        if not SOURCE_IMAGE.is_file():
            raise SystemExit(f"Missing source image: {SOURCE_IMAGE}")
        print(f"Loading {SOURCE_IMAGE} (PNG semantic mask) …")
        im = Image.open(SOURCE_IMAGE).convert("RGB")
        im = im.resize((LOG_W, LOG_H), Image.Resampling.NEAREST)
        rgb = np.array(im)
        print("Classifying …")
        mask = classify_pixels(rgb)
        print("Neighbor-fill ignore …")
        mask = neighbor_fill_ignore_fast(mask)
        print("Morphology …")
        mask = morph_land(mask)
        print(f"Remove components < {LAND_COMPONENT_MIN_PIXELS}px …")
        mask = remove_small_components(mask, LAND_COMPONENT_MIN_PIXELS)
        land = mask == 1
        source_mode = "png_semantic"
    else:
        if not SOURCE_TILEMAP_3PX.is_file():
            raise SystemExit(f"Missing 3px tilemap: {SOURCE_TILEMAP_3PX}")
        print(f"Upscaling {SOURCE_TILEMAP_3PX.name} → 1px land mask …")
        land = land_mask_from_3px_tilemap(SOURCE_TILEMAP_3PX)
        source_mode = "3px_upscale"

    out_dir.mkdir(parents=True, exist_ok=True)
    mask_path = out_dir / "mediterranean_recursive_tilemap_wang16_1px_mask.png"
    write_mask_png(mask_path, land)
    print(f"Wrote {mask_path}")

    chart_dir.mkdir(parents=True, exist_ok=True)
    if args.maps_only:
        for area in index["chart_areas"]:
            aid = area["id"]
            write_area_map_png(chart_dir / f"{aid}_map.png", land, area["bounds"])
            print(f"  map {aid}")
        print("Done (maps only).")
        return

    print("Building corner Wang tiles …")
    corners = build_corner_grid(land)
    tiles, counts = tiles_from_corners(corners)
    tile_types = collect_tile_types(counts)
    print(f"Tiles: {len(tiles):,}  types: {len(tile_types)}  counts sample: {counts.most_common(6)}")

    full_path = out_dir / "mediterranean_recursive_tilemap_wang16_1px.json"
    src_label = SOURCE_IMAGE.name if source_mode == "png_semantic" else SOURCE_TILEMAP_3PX.name
    payload = build_payload(tiles, tile_types, counts, source_image=src_label, source_mode=source_mode)
    print(f"Writing {full_path} …")
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, separators=(",", ":"))
    print(f"Wrote {full_path} ({full_path.stat().st_size / 1e6:.1f} MB)")

    preview_path = out_dir / "mediterranean_recursive_tilemap_wang16_1px_wang_preview.png"
    write_wang_preview(preview_path, tiles)
    print(f"Wrote {preview_path}")

    if args.skip_chart_areas:
        print("Done (full map only).")
        return

    print(f"Splitting into {len(index['chart_areas'])} chart areas …")
    write_chart_area_exports(chart_dir, index, tiles, land, src_label=src_label, source_mode=source_mode)
    print("Done.")


if __name__ == "__main__":
    main()

"""Build generation prompts from style bibles and topology (single source of truth)."""
from __future__ import annotations

from pathlib import Path

from common import FACTORY_ROOT, load_config, topology_by_id

# Strict coast geometry — shared by generate_raw and autotile_agent.
SHORE_GEOMETRY_PROMPTS: dict[str, str] = {
    "horizontal_top_land": (
        "A perfectly STRAIGHT EAST-WEST coastline at the EXACT VERTICAL CENTER of the image. "
        "TOP half (above center): land only. "
        "BOTTOM half (below center): sea only — shallow near the coast, UNIFORM DEEP BLUE at the bottom edge. "
        "Left and right edges must be visually identical so the tile repeats horizontally. "
        "NO sun glare, NO waves at the bottom edge, NO text, NO borders, NO color gradient on the open water."
    ),
    "horizontal_bottom_land": (
        "A perfectly STRAIGHT EAST-WEST coastline at the EXACT VERTICAL CENTER. "
        "TOP half: sea only — shallow near coast, UNIFORM DEEP BLUE at the top edge. "
        "BOTTOM half: land only. "
        "Left and right edges identical so the tile repeats horizontally. "
        "No sun glare, no waves at the top edge, no text, no borders, no gradient on the open water."
    ),
    "vertical_left_land": (
        "A perfectly STRAIGHT NORTH-SOUTH coastline at the EXACT HORIZONTAL CENTER. "
        "LEFT half: land only. "
        "RIGHT half: sea only — shallow near coast, UNIFORM DEEP BLUE at the right edge. "
        "Top and bottom edges identical so the tile repeats vertically."
    ),
    "vertical_right_land": (
        "A perfectly STRAIGHT NORTH-SOUTH coastline at the EXACT HORIZONTAL CENTER. "
        "LEFT half: sea only — shallow near coast, UNIFORM DEEP BLUE at the left edge. "
        "RIGHT half: land only. "
        "Top and bottom edges identical so the tile repeats vertically."
    ),
    "diagonal_rising_left_land": (
        "Most of the image (about 7/8) is land. "
        "A small triangular bay occupies ONLY the LOWER-RIGHT corner (about 1/8). "
        "The straight diagonal coastline runs from the RIGHT edge at mid-height to the BOTTOM edge at mid-width. "
        "Water is UNIFORM DEEP BLUE in the corner. No waves, no sun glare, no borders, no text."
    ),
    "diagonal_rising_right_land": (
        "Most of the image (about 7/8) is land. "
        "A small triangular bay occupies ONLY the LOWER-LEFT corner. "
        "The straight diagonal coastline runs from the LEFT edge at mid-height to the BOTTOM edge at mid-width. "
        "Water is UNIFORM DEEP BLUE in the corner. No waves, no sun glare, no borders, no text."
    ),
    "diagonal_descending_left_land": (
        "Most of the image (about 7/8) is land. "
        "A small triangular bay occupies ONLY the UPPER-RIGHT corner. "
        "The straight diagonal coastline runs from the TOP edge at mid-width to the RIGHT edge at mid-height. "
        "Water is UNIFORM DEEP BLUE in the corner. No waves, no sun glare, no borders, no text."
    ),
    "diagonal_descending_right_land": (
        "Most of the image (about 7/8) is land. "
        "A small triangular bay occupies ONLY the UPPER-LEFT corner. "
        "The straight diagonal coastline runs from the TOP edge at mid-width to the LEFT edge at mid-height. "
        "Water is UNIFORM DEEP BLUE in the corner. No waves, no sun glare, no borders, no text."
    ),
}

EDGE_PROMPTS = {
    "sea_sea": (
        "Photorealistic aerial drone photo, open sea only, top-down. "
        "Deep blue offshore, subtle ripples. Full frame is water — no land, no border."
    ),
    "land_land": (
        "Photorealistic aerial drone photo, inland terrain only, top-down. "
        "Full frame is land — no sea, no border."
    ),
    "land_sea": (
        "Photorealistic aerial drone photo, top-down coastline running horizontally: "
        "land on top half, clear sea on bottom half. Natural rocky beach. No borders."
    ),
    "sea_land": (
        "Photorealistic aerial drone photo, top-down coastline running horizontally: "
        "sea on top half, land on bottom half. No borders."
    ),
}


def read_style(*parts: str) -> str:
    path = FACTORY_ROOT / "style" / Path(*parts)
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return ""


def biome_style_path(biome: str) -> Path:
    return FACTORY_ROOT / "style" / "biomes" / f"{biome}.md"


def biome_palette(cfg: dict | None = None) -> dict:
    """Per-biome colours from config.json `biomes` block, with fallbacks."""
    cfg = cfg or load_config()
    biome = cfg["biome"]
    palettes = cfg.get("biomes", {})
    entry = palettes.get(biome, {})
    sea = tuple(entry.get("open_sea_rgb", cfg.get("open_sea_rgb", [17, 54, 58])))
    beach = tuple(entry.get("beach_rgb", [196, 178, 142]))
    return {
        "open_sea_rgb": (int(sea[0]), int(sea[1]), int(sea[2])),
        "beach_rgb": (int(beach[0]), int(beach[1]), int(beach[2])),
    }


def terrain_prompt(
    topology_id: str,
    variation: int,
    *,
    biome: str | None = None,
    season: str | None = None,
) -> str:
    cfg = load_config()
    biome = biome or cfg["biome"]
    season = season or cfg["season"]
    global_style = read_style("global.md")
    biome_style = read_style("biomes", f"{biome}.md")
    ref_style = read_style("reference_style.md")
    topo = topology_by_id(topology_id)
    legacy = topo.get("legacy_id", topology_id)

    variation_note = (
        f"Variation #{variation}: change shrub and rock placement on land only; "
        "coastline position is fixed and identical across variations."
    )

    if topology_id in SHORE_GEOMETRY_PROMPTS:
        return shore_terrain_prompt(topology_id, variation, biome=biome, season=season)

    topology_hints = {
        "totally_sea": (
            "DEPRECATED — use procedural make_uniform_sea. "
            "If generating: one uniform deep blue, no gradient, no land."
        ),
        "totally_land": (
            "Entire tile is inland terrain for this biome. No coastline, no sea visible. "
            "Edge-to-edge photorealistic ground cover."
        ),
    }
    hint = topology_hints.get(topology_id, f"Topology {legacy}.")

    return (
        f"{global_style}\n\n{biome_style}\n\n{ref_style}\n\n"
        f"TASK: One 512x512 photorealistic aerial map tile. biome={biome} season={season} topology={legacy}.\n"
        f"{hint}\n{variation_note}\n"
        "CRITICAL: Edge-to-edge drone photo. NO borders, frames, vignettes, or flat color margins. "
        "NO cartoon style."
    )


def shore_terrain_prompt(
    topology_id: str,
    variation: int,
    *,
    biome: str | None = None,
    season: str | None = None,
) -> str:
    """Full prompt for shore tiles (used by generate_raw and autotile_agent)."""
    if topology_id not in SHORE_GEOMETRY_PROMPTS:
        raise KeyError(f"Not a shore topology: {topology_id}")

    cfg = load_config()
    biome = biome or cfg["biome"]
    season = season or cfg["season"]
    global_style = read_style("global.md")
    biome_style = read_style("biomes", f"{biome}.md")
    ref_style = read_style("reference_style.md")
    geometry = SHORE_GEOMETRY_PROMPTS[topology_id]

    return (
        f"{global_style}\n\n{biome_style}\n\n{ref_style}\n\n"
        f"TASK: Photorealistic aerial top-down drone photo, 512x512. "
        f"biome={biome} season={season} topology={topology_id}.\n"
        f"{geometry}\n"
        f"Variation #{variation}: change ONLY land-side shrubs and rocks; coastline geometry is fixed.\n"
        "Rocky natural beach at the waterline. CRITICAL: edge-to-edge content, NO borders or frames."
    )


def shore_prompt_short(topology_id: str, variation: int) -> str:
    """Compact prompt suffix for autotile retries (geometry + variation)."""
    return (
        SHORE_GEOMETRY_PROMPTS[topology_id]
        + f"\nVariation seed #{variation}: change ONLY shrubs and rocks on the land side; "
        "coastline position is fixed."
    )


def port_overlay_prompt(culture: str, variation: int) -> str:
    global_style = read_style("global.md")
    culture_style = read_style("cultures", f"{culture}_port.md")
    ref_style = read_style("reference_style.md")
    return (
        f"{global_style}\n\n{culture_style}\n\n{ref_style}\n\n"
        f"TASK: 512x512 photorealistic port overlay, culture={culture}, variation #{variation}. "
        "Soft blend at edges; no text."
    )

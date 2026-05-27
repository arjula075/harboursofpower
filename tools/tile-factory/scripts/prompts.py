"""Build generation prompts from style bibles and topology (single source of truth)."""
from __future__ import annotations

from pathlib import Path

from common import FACTORY_ROOT, load_config, topology_by_id

# Strict coast geometry — shared by generate_raw and autotile_agent.
SHORE_GEOMETRY_PREAMBLE = (
    "Terrain features must remain self-contained within the tile. "
    "No large landmarks, roads, rivers, cliffs, or structures touching image borders. "
    "Small subtle human traces allowed: faint dirt paths, tiny stone ruins, sparse terracing, "
    "barely visible footpaths.\n"
    "Coastlines must connect seamlessly to neighboring tiles. Preserve tile exit connectivity at the "
    "edge locations described below (near midpoints); local shoreline shape must remain organically "
    "irregular between exits. Avoid geometric separators, wedges, sectors, or vector-clean splits."
)

# Shared shoreline language (silhouette + band + shallow water).
SHORE_SILHOUETTE = (
    "The coastline must appear naturally eroded and visibly irregular at medium scale, with continuous "
    "meandering variation along the entire shore. Include asymmetric rocky intrusions, uneven erosion "
    "shelves, small coves, fragmented boulder clusters, and subtle shoreline wobble with lateral "
    "displacement and non-uniform shoreline thickness. The shoreline SILHOUETTE must NEVER resemble a "
    "straight line, geometric diagonal, clean separator, vector edge, masked gradient, or uniform-width "
    "dividing band. Texture roughness alone is insufficient — the coast outline itself must meander."
)

SHORE_COAST_BAND = (
    "The shoreline transition zone should occupy a visibly broad natural coastal band with rocky "
    "outcroppings extending into shallow water — not a thin two-pixel separator."
)

SHORE_SHALLOW_WATER = (
    "Shallow underwater rock formations and seabed contours should irregularly mirror the coastline "
    "shape beneath clear turquoise shallows, breaking any artificial straight edge in the water. "
    "Beyond the shallows, open water is uniform deep blue."
)

SHORE_VARIATION_NOTE = (
    "Overall coastline connectivity and tile exits remain consistent across variations; local shoreline "
    "shape and inland shrubs/rocks may vary naturally."
)

# Per-topology bodies (preamble + SHORE_SILHOUETTE applied via shore_geometry_text).
SHORE_GEOMETRY_PROMPTS: dict[str, str] = {
    "horizontal_top_land": (
        "SHORE_NORTH. Most of the image (about 7/8) is LAND in the upper portion. "
        "Sea occupies the LOWER portion.\n"
        "Tile exits: the coastline enters the LEFT edge near the vertical midpoint and exits the RIGHT "
        "edge near the vertical midpoint, meandering horizontally between those points.\n"
        f"{SHORE_SILHOUETTE}\n"
        f"{SHORE_COAST_BAND}\n"
        f"{SHORE_SHALLOW_WATER}\n"
        "Rocky natural beach at the waterline. Inland terrain: sparse olive trees, dry grass, exposed "
        "stone, scattered shrubs."
    ),
    "horizontal_bottom_land": (
        "SHORE_SOUTH. Most of the image (about 7/8) is LAND in the lower portion. "
        "Sea occupies the UPPER portion.\n"
        "Tile exits: the coastline enters the LEFT edge near the vertical midpoint and exits the RIGHT "
        "edge near the vertical midpoint, meandering horizontally between those points.\n"
        f"{SHORE_SILHOUETTE}\n"
        f"{SHORE_COAST_BAND}\n"
        f"{SHORE_SHALLOW_WATER}\n"
        "Rocky shoreline transition with dry Mediterranean terrain inland. Sparse olive trees and low "
        "shrubs scattered naturally."
    ),
    "vertical_right_land": (
        "SHORE_EAST. Most of the image (about 7/8) is LAND on the right side. "
        "Sea occupies the LEFT side.\n"
        "Tile exits: the coastline enters the TOP edge near the horizontal midpoint and exits the BOTTOM "
        "edge near the horizontal midpoint, meandering vertically between those points.\n"
        f"{SHORE_SILHOUETTE}\n"
        f"{SHORE_COAST_BAND}\n"
        f"{SHORE_SHALLOW_WATER}\n"
        "Rocky natural beach at waterline. Mediterranean dry terrain inland with sparse olive vegetation "
        "and exposed rock."
    ),
    "vertical_left_land": (
        "SHORE_WEST. Most of the image (about 7/8) is LAND on the left side. "
        "Sea occupies the RIGHT side.\n"
        "Tile exits: the coastline enters the TOP edge near the horizontal midpoint and exits the BOTTOM "
        "edge near the horizontal midpoint, meandering vertically between those points.\n"
        f"{SHORE_SILHOUETTE}\n"
        f"{SHORE_COAST_BAND}\n"
        f"{SHORE_SHALLOW_WATER}\n"
        "Rocky natural beach at shoreline. Dry Mediterranean inland terrain with sparse olive trees, "
        "dusty paths, exposed stone patches."
    ),
    "diagonal_rising_left_land": (
        "SHORE_DIAGONAL_NE / INNER CORNER SEA. Most of the image (about 7/8) is LAND in the upper-left "
        "region. A compact irregular bay occupies only the lower-right corner region (about 1/8 of the "
        "tile), forming a concave coastal pocket — not a geometric shape.\n"
        "Tile exits: the coastline enters the RIGHT edge near the vertical midpoint and exits the BOTTOM "
        "edge near the horizontal midpoint, remaining organically irregular between those locations.\n"
        f"{SHORE_SILHOUETTE}\n"
        f"{SHORE_COAST_BAND}\n"
        f"{SHORE_SHALLOW_WATER}\n"
        "The coast curves naturally inward toward the lower-right corner with asymmetric erosion. Inland: "
        "sparse olive vegetation, dusty ground, exposed rock, faint ancient footpaths."
    ),
    "diagonal_rising_right_land": (
        "SHORE_DIAGONAL_NW. Most of the image (about 7/8) is LAND in the upper-right region. "
        "A compact irregular bay occupies only the lower-left corner region (about 1/8 of the tile).\n"
        "Tile exits: the coastline enters the LEFT edge near the vertical midpoint and exits the BOTTOM "
        "edge near the horizontal midpoint, remaining organically irregular between those locations.\n"
        f"{SHORE_SILHOUETTE}\n"
        f"{SHORE_COAST_BAND}\n"
        f"{SHORE_SHALLOW_WATER}\n"
        "Sparse Mediterranean vegetation inland with scattered shrubs, olive trees, occasional stone "
        "remnants."
    ),
    "diagonal_descending_left_land": (
        "SHORE_INNER CORNER SEA (upper-right). Most of the image (about 7/8) is LAND in the lower-left "
        "region. A compact irregular bay occupies only the upper-right corner region (about 1/8 of the "
        "tile), forming a concave coastal pocket.\n"
        "Tile exits: the coastline enters the TOP edge near the horizontal midpoint and exits the RIGHT "
        "edge near the vertical midpoint, remaining organically irregular between those locations.\n"
        f"{SHORE_SILHOUETTE}\n"
        f"{SHORE_COAST_BAND}\n"
        f"{SHORE_SHALLOW_WATER}\n"
        "Dry Mediterranean inland biome with sparse olive trees and exposed stone."
    ),
    "diagonal_descending_right_land": (
        "SHORE_OUTER CORNER LAND. Land occupies roughly the lower-right quadrant as an organic convex "
        "peninsula-like outer corner. Sea surrounds from the top and left.\n"
        "Tile exits: the coastline enters the TOP edge near the horizontal midpoint and exits the LEFT "
        "edge near the vertical midpoint, remaining organically irregular between those locations.\n"
        f"{SHORE_SILHOUETTE}\n"
        f"{SHORE_COAST_BAND}\n"
        f"{SHORE_SHALLOW_WATER}\n"
        "The landform must feel eroded and asymmetric, not geometric. Sparse olive vegetation, dry grass, "
        "rocky terrain on the peninsula."
    ),
}


def shore_geometry_text(topology_id: str) -> str:
    """Preamble plus topology-specific coast geometry (single source for agents and UI)."""
    body = SHORE_GEOMETRY_PROMPTS[topology_id]
    return f"{SHORE_GEOMETRY_PREAMBLE}\n\n{body}"

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
    geometry = shore_geometry_text(topology_id)

    return (
        f"{global_style}\n\n{biome_style}\n\n{ref_style}\n\n"
        f"TASK: Photorealistic aerial top-down drone photo, 512x512. "
        f"biome={biome} season={season} topology={topology_id}.\n"
        f"{geometry}\n"
        f"Variation #{variation}: change ONLY land-side shrubs and rocks; {SHORE_VARIATION_NOTE}\n"
        "CRITICAL: edge-to-edge content, NO borders or frames."
    )


def shore_prompt_short(topology_id: str, variation: int) -> str:
    """Compact prompt suffix for autotile retries (geometry + variation)."""
    return (
        shore_geometry_text(topology_id)
        + f"\nVariation seed #{variation}: change ONLY shrubs and rocks on the land side; "
        f"{SHORE_VARIATION_NOTE}"
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


def _variation_note_terrain(topology_id: str, variation: int) -> str:
    if topology_id in SHORE_GEOMETRY_PROMPTS:
        return (
            f"Variation #{variation}: change ONLY land-side shrubs and rocks; "
            f"{SHORE_VARIATION_NOTE}"
        )
    return (
        f"Variation #{variation}: change shrub and rock placement on land only; "
        "coastline position is fixed and identical across variations."
    )


def _task_geometry_terrain(topology_id: str, biome: str, season: str) -> tuple[str, str]:
    """Returns (label, body) for the task / geometry layer."""
    if topology_id in SHORE_GEOMETRY_PROMPTS:
        return (
            "Coast geometry",
            (
                f"TASK: Photorealistic aerial top-down drone photo, 512x512. "
                f"biome={biome} season={season} topology={topology_id}.\n"
                f"{shore_geometry_text(topology_id)}\n"
                "CRITICAL: edge-to-edge content, NO borders or frames."
            ),
        )
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
    topo = topology_by_id(topology_id)
    legacy = topo.get("legacy_id", topology_id)
    hint = topology_hints.get(
        topology_id,
        f"Topology {legacy}.",
    )
    return (
        "Task & topology",
        (
            f"TASK: One 512x512 photorealistic aerial map tile. biome={biome} season={season} topology={legacy}.\n"
            f"{hint}\n"
            "CRITICAL: Edge-to-edge drone photo. NO borders, frames, vignettes, or flat color margins. "
            "NO cartoon style."
        ),
    )


def default_prompt_layers_for_spec(spec: dict) -> dict[str, dict]:
    """Default layer texts keyed by layer id (for UI and spec storage)."""
    cfg = load_config()
    kind = str(spec.get("kind", "terrain"))
    if kind == "port_overlay":
        culture = str(spec.get("culture", "greek")).replace("port_", "")
        variation = int(spec.get("variation", 1))
        return {
            "global_style": {
                "label": "Global style",
                "source": "tools/tile-factory/style/global.md",
                "text": read_style("global.md"),
            },
            "culture_style": {
                "label": "Culture / port style",
                "source": f"tools/tile-factory/style/cultures/{culture}_port.md",
                "text": read_style("cultures", f"{culture}_port.md"),
            },
            "reference_style": {
                "label": "Reference style",
                "source": "tools/tile-factory/style/reference_style.md",
                "text": read_style("reference_style.md"),
            },
            "task_geometry": {
                "label": "Task",
                "source": "builtin:port_overlay",
                "text": (
                    f"TASK: 512x512 photorealistic port overlay, culture={culture}, variation #{variation}. "
                    "Soft blend at edges; no text."
                ),
            },
        }

    biome = str(spec.get("biome", cfg["biome"]))
    season = str(spec.get("season", cfg["season"]))
    topology_id = str(spec.get("topology", "totally_land"))
    variation = int(spec.get("variation", 1))
    task_label, task_text = _task_geometry_terrain(topology_id, biome, season)
    return {
        "global_style": {
            "label": "Global style",
            "source": "tools/tile-factory/style/global.md",
            "text": read_style("global.md"),
        },
        "biome_style": {
            "label": "Biome style",
            "source": f"tools/tile-factory/style/biomes/{biome}.md",
            "text": read_style("biomes", f"{biome}.md"),
        },
        "reference_style": {
            "label": "Reference style",
            "source": "tools/tile-factory/style/reference_style.md",
            "text": read_style("reference_style.md"),
        },
        "task_geometry": {
            "label": task_label,
            "source": f"builtin:{topology_id}",
            "text": task_text,
        },
        "variation_note": {
            "label": "Variation",
            "source": "builtin:variation",
            "text": _variation_note_terrain(topology_id, variation),
        },
    }


def effective_prompt_layers(spec: dict) -> dict[str, dict]:
    """Merge spec overrides onto defaults."""
    defaults = default_prompt_layers_for_spec(spec)
    overrides: dict = spec.get("prompt_layers") if isinstance(spec.get("prompt_layers"), dict) else {}
    out: dict[str, dict] = {}
    for key, base in defaults.items():
        row = dict(base)
        ov = overrides.get(key) if isinstance(overrides.get(key), dict) else {}
        if isinstance(ov, dict) and str(ov.get("text", "")).strip():
            row["text"] = str(ov["text"])
            row["customized"] = True
        else:
            row["customized"] = False
        out[key] = row
    return out


def assemble_generation_prompt(spec: dict) -> str:
    """Prompt sent to OpenAI (or full override from spec)."""
    full = str(spec.get("generation_prompt", "")).strip()
    if full:
        return full
    layers = effective_prompt_layers(spec)
    parts = [str(layers[k]["text"]).strip() for k in layers if str(layers[k].get("text", "")).strip()]
    return "\n\n".join(parts)


def prompt_detail_for_spec(spec: dict) -> dict:
    kind = str(spec.get("kind", "terrain"))
    topology = str(spec.get("topology", ""))
    procedural = kind == "terrain" and topology == "totally_sea"
    layers = effective_prompt_layers(spec)
    layer_list = [
        {
            "key": key,
            "label": row["label"],
            "source": row["source"],
            "text": row["text"],
            "customized": bool(row.get("customized")),
        }
        for key, row in layers.items()
    ]
    return {
        "id": str(spec.get("id", "")),
        "kind": kind,
        "topology": topology,
        "procedural": procedural,
        "procedural_note": (
            "totally_sea is rebuilt procedurally (no API image). Recreate runs make_uniform_sea + publish."
            if procedural
            else ""
        ),
        "layers": layer_list,
        "full_prompt": assemble_generation_prompt(spec),
        "has_full_override": bool(str(spec.get("generation_prompt", "")).strip()),
    }

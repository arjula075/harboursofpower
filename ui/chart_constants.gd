extends RefCounted
class_name HarboursChartGrid

## Logical grid for `world_full.json` `map_u` / `map_v` (origin top-left of sheet space).
const LOGICAL_GRID_WIDTH := 2000
const LOGICAL_GRID_HEIGHT := 1000

## Cropped map-only basemap (no sheet chrome). Takes precedence over the full coordinate sheet.
## For unchanged `world_full.json` UVs, pixels should still align with the same logical 2000×1000 frame; otherwise refresh UVs or add a transform.
const CHUNK_MANIFEST_JSON := "res://data/maps/chunk_manifest.json"
const CHUNK_MASK_MASTER_PNG := "res://docs/mediterranean_recursive_tilemap_wang16_1px_mask.png"

const MAP_ORIGIN_BASEMAP_PNG := "res://docs/mi8l8sc4s5z81.png"

## Full reference sheet (table, margins) under `res://docs/`.
const COORDINATE_SHEET_PNG := "res://docs/8670b2bf-409a-4880-ae53-683f5eb2d2a6.png"

const SEA_CHART_SVG := "res://assets/ui/sea_chart.svg"

## Default horizontal span of the Routes map view in logical map coordinates (same units as LOGICAL_GRID_WIDTH).
## Smaller `view_w` = more zoomed in. Was 100; 58 keeps the player hull and home port readable on open.
const ROUTES_LOCAL_VIEW_WIDTH_MAP := 58.0

## First available basemap texture (cropped sheet → full sheet → sea SVG); returns null if none load.
static func load_route_basemap_texture() -> Texture2D:
	for path in [MAP_ORIGIN_BASEMAP_PNG, COORDINATE_SHEET_PNG, SEA_CHART_SVG]:
		if ResourceLoader.exists(path):
			var t: Texture2D = load(path) as Texture2D
			if t != null:
				return t
	return null


## Where the texture lands inside the control when using uniform scale-to-fit (contain), centered.
static func texture_contain_region(control_size: Vector2, texture_pixel_size: Vector2) -> Rect2:
	if texture_pixel_size.x <= 0.0 or texture_pixel_size.y <= 0.0:
		return Rect2(Vector2.ZERO, control_size)
	var s: float = minf(control_size.x / texture_pixel_size.x, control_size.y / texture_pixel_size.y)
	var dw: float = texture_pixel_size.x * s
	var dh: float = texture_pixel_size.y * s
	var ox: float = (control_size.x - dw) * 0.5
	var oy: float = (control_size.y - dh) * 0.5
	return Rect2(ox, oy, dw, dh)


static func uv_to_region_px(uv: Vector2, region: Rect2) -> Vector2:
	return region.position + Vector2(uv.x * region.size.x, uv.y * region.size.y)

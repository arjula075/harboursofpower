extends RefCounted
class_name HarboursChartProjection

## Map UV (0..1) and logical/world pixels ↔ screen for pan/zoom chart views.

const VIEW_W_MIN := 30.0
const VIEW_ZOOM_STEP := 1.14

var world_width: int = HarboursChartGrid.LOGICAL_GRID_WIDTH
var world_height: int = HarboursChartGrid.LOGICAL_GRID_HEIGHT
var logical_width: int = HarboursChartGrid.LOGICAL_GRID_WIDTH
var logical_height: int = HarboursChartGrid.LOGICAL_GRID_HEIGHT

var center_map: Vector2 = Vector2(1000.0, 500.0)
var view_w: float = HarboursChartGrid.ROUTES_LOCAL_VIEW_WIDTH_MAP


func configure_from_manifest(doc: Dictionary) -> void:
	if doc.is_empty():
		return
	world_width = int(doc.get("world_width", world_width))
	world_height = int(doc.get("world_height", world_height))
	logical_width = int(doc.get("logical_width", logical_width))
	logical_height = int(doc.get("logical_height", logical_height))


func view_w_max() -> float:
	return minf(900.0, float(logical_width))


func uv_to_map(uv: Vector2) -> Vector2:
	return Vector2(uv.x * float(logical_width), uv.y * float(logical_height))


func reset_center_from_uv(uv: Vector2) -> void:
	if uv.x >= 0.0:
		center_map = uv_to_map(uv)
	else:
		center_map = Vector2(float(logical_width) * 0.5, float(logical_height) * 0.5)
	view_w = HarboursChartGrid.ROUTES_LOCAL_VIEW_WIDTH_MAP


func view_geo(control_size: Vector2) -> Dictionary:
	var sz: Vector2 = control_size
	var lw := float(logical_width)
	var lh := float(logical_height)
	var vw: float = clampf(view_w, VIEW_W_MIN, view_w_max())
	if sz.x < 1.0:
		return {"tl": Vector2.ZERO, "vw": vw, "vh": 0.0, "sz": sz, "lw": lw, "lh": lh, "ww": float(world_width), "wh": float(world_height)}
	var px_per_mx: float = sz.x / vw
	var vh: float = sz.y / px_per_mx
	var half := Vector2(vw * 0.5, vh * 0.5)
	var tl := center_map - half
	tl.x = clampf(tl.x, 0.0, maxf(0.0, lw - vw))
	tl.y = clampf(tl.y, 0.0, maxf(0.0, lh - vh))
	return {
		"tl": tl,
		"vw": vw,
		"vh": vh,
		"sz": sz,
		"lw": lw,
		"lh": lh,
		"ww": float(world_width),
		"wh": float(world_height),
		"px_per_mx": px_per_mx,
	}


func map_to_screen(mx: float, my: float, geo: Dictionary) -> Vector2:
	var tl: Vector2 = geo["tl"]
	var vw: float = geo["vw"]
	var vh: float = geo["vh"]
	var sz: Vector2 = geo["sz"]
	return Vector2((mx - tl.x) / vw * sz.x, (my - tl.y) / vh * sz.y)


func screen_to_map_delta(screen_delta: Vector2, geo: Dictionary) -> Vector2:
	var vw: float = geo["vw"]
	var vh: float = geo["vh"]
	var sz: Vector2 = geo["sz"]
	if sz.x <= 0.0 or sz.y <= 0.0:
		return Vector2.ZERO
	return Vector2(screen_delta.x / sz.x * vw, screen_delta.y / sz.y * vh)


func visible_map_rect(geo: Dictionary) -> Rect2:
	var tl: Vector2 = geo["tl"]
	return Rect2(tl, Vector2(geo["vw"], geo["vh"]))

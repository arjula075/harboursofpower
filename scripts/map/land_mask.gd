extends RefCounted
class_name HarboursLandMask

## Land/sea for free sailing — sampled from the Wang-16 mask PNG (same 2000×1000 frame as
## map_u / map_v and the tile-pixel chart chunks). Chart *display* is baked from the JSON
## tilemap; collision reads this mask file (derived from the same tilemap at build time).
## Use is_blocked_for_sailing() for movement — it ignores 1px land specks in open water.

const MASK_PATH := "res://docs/mediterranean_recursive_tilemap_wang16_1px_mask.png"

static var _image: Image
static var _loaded := false
static var _w := 1
static var _h := 1


static func _ensure_loaded() -> void:
	if _loaded:
		return
	_loaded = true
	if not FileAccess.file_exists(MASK_PATH):
		push_warning("Land mask missing: %s" % MASK_PATH)
		return
	var img := Image.load_from_file(MASK_PATH)
	if img == null:
		push_warning("Land mask failed to load: %s" % MASK_PATH)
		return
	_image = img
	_w = img.get_width()
	_h = img.get_height()


static func map_size() -> Vector2i:
	_ensure_loaded()
	return Vector2i(_w, _h)


## Colours from write_mask_png() in build_recursive_tilemap_wang16_1px.py (not chart coast hues).
const _SEA_REF := Color8(26, 74, 110, 255)
const _LAND_REF := Color8(180, 160, 120, 255)
const _MASK_CLASSIFY_EPS := 0.12


static func _sample_pixel(map_x: float, map_y: float) -> Color:
	var x := clampi(int(map_x), 0, _w - 1)
	var y := clampi(int(map_y), 0, _h - 1)
	return _image.get_pixel(x, y)


static func _color_distance_sq(a: Color, b: Color) -> float:
	var dr := a.r - b.r
	var dg := a.g - b.g
	var db := a.b - b.b
	return dr * dr + dg * dg + db * db


static func is_land(map_x: float, map_y: float) -> bool:
	_ensure_loaded()
	if _image == null:
		return false
	var c := _sample_pixel(map_x, map_y)
	var d_land := _color_distance_sq(c, _LAND_REF)
	var d_sea := _color_distance_sq(c, _SEA_REF)
	if d_land <= _MASK_CLASSIFY_EPS * _MASK_CLASSIFY_EPS:
		return true
	if d_sea <= _MASK_CLASSIFY_EPS * _MASK_CLASSIFY_EPS:
		return false
	return c.r > 0.55 and c.g > 0.51 and c.b > 0.39


static func is_sea(map_x: float, map_y: float) -> bool:
	_ensure_loaded()
	if _image == null:
		return true
	return not is_land(map_x, map_y)


static func _is_land_speck(map_x: float, map_y: float) -> bool:
	## Single-pixel totally_land cells surrounded by sea (invisible at chart zoom).
	if not is_land(map_x, map_y):
		return false
	var land_neighbors := 0
	for dy in [-1, 0, 1]:
		for dx in [-1, 0, 1]:
			if dx == 0 and dy == 0:
				continue
			if is_land(map_x + float(dx), map_y + float(dy)):
				land_neighbors += 1
	return land_neighbors <= 1


static func is_blocked_for_sailing(map_x: float, map_y: float) -> bool:
	## Same grid cell as the yellow hull marker — only solid land, not coast specks.
	return is_land(map_x, map_y) and not _is_land_speck(map_x, map_y)


static func debug_cell(map_x: float, map_y: float) -> Dictionary:
	_ensure_loaded()
	var x := clampi(int(map_x), 0, _w - 1)
	var y := clampi(int(map_y), 0, _h - 1)
	if _image == null:
		return {"px": [x, y], "rgb": [], "is_land": false, "is_blocked": false, "is_speck": false}
	var c := _image.get_pixel(x, y)
	var on_land := is_land(map_x, map_y)
	return {
		"px": [x, y],
		"rgb": [int(c.r * 255.0), int(c.g * 255.0), int(c.b * 255.0)],
		"is_land": on_land,
		"is_blocked": is_blocked_for_sailing(map_x, map_y),
		"is_speck": on_land and _is_land_speck(map_x, map_y),
	}


static func heading_away_from_land(map_x: float, map_y: float, sample_radius: int = 36) -> float:
	## Unit vector pointing from nearby land toward open water; used on cast-off.
	var land_pull := Vector2.ZERO
	var n := 0
	for dy in range(-sample_radius, sample_radius + 1, 6):
		for dx in range(-sample_radius, sample_radius + 1, 6):
			if dx == 0 and dy == 0:
				continue
			var px := map_x + float(dx)
			var py := map_y + float(dy)
			if is_land(px, py):
				land_pull += Vector2(float(dx), float(dy))
				n += 1
	if n <= 0:
		return 0.0
	var away: Vector2 = -(land_pull / float(n))
	if away.length_squared() < 0.01:
		return 0.0
	return away.angle()


static func nearest_port_id(
	port_uv: Dictionary,
	map_x: float,
	map_y: float,
	radius_map: float,
) -> String:
	var best_id := ""
	var best_d := radius_map * radius_map
	for pid: Variant in port_uv.keys():
		var uv: Vector2 = port_uv[pid]
		if uv.x < 0.0:
			continue
		var px := uv.x * float(HarboursChartGrid.LOGICAL_GRID_WIDTH)
		var py := uv.y * float(HarboursChartGrid.LOGICAL_GRID_HEIGHT)
		var dx := px - map_x
		var dy := py - map_y
		var d2 := dx * dx + dy * dy
		if d2 <= best_d:
			best_d = d2
			best_id = str(pid)
	return best_id

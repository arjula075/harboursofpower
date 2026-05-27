extends RefCounted
class_name HarboursChartAreaLookup

## Resolve logical map (x,y) to chart_area_id using chunk_manifest chart_areas bounds.


static var _areas: Array = []
static var _loaded := false


static func _ensure_loaded() -> void:
	if _loaded:
		return
	_loaded = true
	var doc: Dictionary = HarboursChunkManifestLoader.load_document()
	var raw: Variant = doc.get("chart_areas", [])
	if typeof(raw) == TYPE_ARRAY:
		_areas = raw


static func reload() -> void:
	_loaded = false
	_areas.clear()
	_ensure_loaded()


static func area_at_map(map_x: float, map_y: float) -> String:
	_ensure_loaded()
	var best_id := ""
	var best_area := INF
	for entry: Variant in _areas:
		if typeof(entry) != TYPE_DICTIONARY:
			continue
		var d: Dictionary = entry
		var aid := str(d.get("id", ""))
		if aid.is_empty():
			continue
		var b: Variant = d.get("bounds", null)
		if typeof(b) != TYPE_DICTIONARY:
			continue
		var x0 := int(b.get("x0", 0))
		var y0 := int(b.get("y0", 0))
		var x1 := int(b.get("x1", 0))
		var y1 := int(b.get("y1", 0))
		if map_x < float(x0) or map_x >= float(x1) or map_y < float(y0) or map_y >= float(y1):
			continue
		var area := (x1 - x0) * (y1 - y0)
		if area < best_area:
			best_area = area
			best_id = aid
	return best_id


static func area_at_uv(uv: Vector2) -> String:
	if uv.x < 0.0:
		return ""
	var mx := uv.x * float(HarboursChartGrid.LOGICAL_GRID_WIDTH)
	var my := uv.y * float(HarboursChartGrid.LOGICAL_GRID_HEIGHT)
	return area_at_map(mx, my)

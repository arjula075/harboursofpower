extends RefCounted
class_name HarboursShipVisualCatalog

## Loads `data/ship_visuals_manifest.json` and exposes map/chart ship sprites by class id.

const MANIFEST_PATH := "res://data/ship_visuals_manifest.json"

static var _objects_by_id: Dictionary = {}
static var _textures_by_id: Dictionary = {}
static var _loaded := false


static func _ensure_loaded() -> void:
	if _loaded:
		return
	_loaded = true
	_objects_by_id.clear()
	_textures_by_id.clear()
	if not FileAccess.file_exists(MANIFEST_PATH):
		push_warning("Ship visual manifest missing: %s" % MANIFEST_PATH)
		return
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(MANIFEST_PATH))
	if typeof(parsed) != TYPE_DICTIONARY:
		push_warning("Ship visual manifest is not a JSON object: %s" % MANIFEST_PATH)
		return
	for row: Variant in (parsed as Dictionary).get("objects", []):
		if typeof(row) != TYPE_DICTIONARY:
			continue
		var obj: Dictionary = row as Dictionary
		var sid := str(obj.get("id", ""))
		if sid.is_empty():
			continue
		_objects_by_id[sid] = obj
		var tex_path := str(obj.get("texture", ""))
		if tex_path.is_empty() or not ResourceLoader.exists(tex_path):
			continue
		var tex := load(tex_path) as Texture2D
		if tex != null:
			_textures_by_id[sid] = tex


static func has_visual(ship_class_id: String) -> bool:
	_ensure_loaded()
	return _textures_by_id.has(ship_class_id)


static func get_visual_object(ship_class_id: String) -> Dictionary:
	_ensure_loaded()
	return (_objects_by_id.get(ship_class_id, {}) as Dictionary).duplicate(true)


static func get_texture(ship_class_id: String) -> Texture2D:
	_ensure_loaded()
	return _textures_by_id.get(ship_class_id) as Texture2D


static func get_map_scale(ship_class_id: String) -> float:
	var obj := get_visual_object(ship_class_id)
	return float(obj.get("map_scale", 1.0))


static func make_sprite(ship_class_id: String) -> Sprite2D:
	var spr := Sprite2D.new()
	spr.name = "ShipSprite"
	spr.texture = get_texture(ship_class_id)
	spr.centered = true
	var obj := get_visual_object(ship_class_id)
	var pivot: Variant = obj.get("pivot_norm", [0.5, 0.5])
	if pivot is Array and (pivot as Array).size() >= 2:
		spr.offset = Vector2.ZERO
		spr.centered = true
	var facing := str(obj.get("facing", "east")).to_lower()
	match facing:
		"west":
			spr.flip_h = true
		_:
			spr.flip_h = false
	return spr

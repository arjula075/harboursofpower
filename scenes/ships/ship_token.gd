extends Node2D
class_name HarboursShipToken

## Map token for a hull class. Assign `ship_class_id` then call `apply_visual()`.

@export var ship_class_id: String = "greek_merchant"
@export var map_scale_multiplier: float = 1.0

@onready var _sprite: Sprite2D = $ShipSprite


func _ready() -> void:
	apply_visual()


func apply_visual() -> void:
	if _sprite == null:
		_sprite = get_node_or_null("ShipSprite") as Sprite2D
	if _sprite == null:
		return
	var tex := HarboursShipVisualCatalog.get_texture(ship_class_id)
	_sprite.texture = tex
	_sprite.visible = tex != null
	var scale := HarboursShipVisualCatalog.get_map_scale(ship_class_id) * map_scale_multiplier
	_sprite.scale = Vector2(scale, scale)
	var obj := HarboursShipVisualCatalog.get_visual_object(ship_class_id)
	if str(obj.get("facing", "east")).to_lower() == "west":
		_sprite.flip_h = true
	else:
		_sprite.flip_h = false

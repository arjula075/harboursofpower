extends Button
## Wraps hover text to a fixed max width so engine tooltips do not span the whole panel.
const TOOLTIP_MAX_WIDTH_PX := 340

func _make_custom_tooltip(for_text: String) -> Object:
	if for_text.is_empty():
		return null
	var margin := MarginContainer.new()
	margin.add_theme_constant_override("margin_left", 10)
	margin.add_theme_constant_override("margin_right", 10)
	margin.add_theme_constant_override("margin_top", 8)
	margin.add_theme_constant_override("margin_bottom", 8)
	var lbl := Label.new()
	lbl.text = for_text
	lbl.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	lbl.custom_minimum_size = Vector2(float(TOOLTIP_MAX_WIDTH_PX), 0.0)
	lbl.size_flags_horizontal = Control.SIZE_SHRINK_BEGIN
	lbl.size_flags_vertical = Control.SIZE_SHRINK_BEGIN
	margin.add_child(lbl)
	return margin

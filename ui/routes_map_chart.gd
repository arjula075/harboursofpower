extends Control
class_name RoutesMapChart

## Emitted when the player picks a destination port on the chart (same as legacy Sail).
signal sail_requested(port_id: String)

const _VIEW_W_MIN := 30.0
const _VIEW_W_MAX := 900.0
const _ZOOM_STEP := 1.14

var _gs: HarboursGameState
var _texture: Texture2D
var _rows: Array = []

## Map-space center (0..LOGICAL_GRID_WIDTH, 0..LOGICAL_GRID_HEIGHT).
var _center_map: Vector2 = Vector2(1000.0, 500.0)
## Horizontal span of the view in map coordinates (uniform scale on both axes).
var _view_w: float = HarboursChartGrid.ROUTES_LOCAL_VIEW_WIDTH_MAP

var _dragging := false
var _drag_moved := false
var _press_screen: Vector2


func setup(gs: HarboursGameState, rows: Array) -> void:
	_gs = gs
	_rows = rows
	_texture = HarboursChartGrid.load_route_basemap_texture()
	_reset_view_from_player()


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_STOP
	clip_contents = true
	if get_node_or_null("RoutesMapHover") == null:
		var h := Label.new()
		h.name = "RoutesMapHover"
		h.mouse_filter = Control.MOUSE_FILTER_IGNORE
		h.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		h.add_theme_font_size_override("font_size", 11)
		h.add_theme_color_override("font_color", Color(0.92, 0.9, 0.86))
		h.add_theme_color_override("font_outline_color", Color(0.05, 0.05, 0.08, 0.9))
		h.add_theme_constant_override("outline_size", 4)
		h.horizontal_alignment = HORIZONTAL_ALIGNMENT_LEFT
		h.vertical_alignment = VERTICAL_ALIGNMENT_BOTTOM
		h.set_anchors_preset(Control.PRESET_BOTTOM_WIDE)
		h.offset_top = -52.0
		h.offset_left = 8.0
		h.offset_right = -8.0
		h.offset_bottom = -4.0
		add_child(h)
	gui_input.connect(_on_gui_input)
	var vp := get_viewport()
	if vp != null:
		if not vp.size_changed.is_connected(apply_fill_height):
			vp.size_changed.connect(apply_fill_height)
	call_deferred("apply_fill_height")


func _exit_tree() -> void:
	var vp := get_viewport()
	if vp != null and vp.size_changed.is_connected(apply_fill_height):
		vp.size_changed.disconnect(apply_fill_height)


func _reset_view_from_player() -> void:
	var uv: Vector2 = _gs.get_port_map_uv(_gs.player_port_id)
	var lw := float(HarboursChartGrid.LOGICAL_GRID_WIDTH)
	var lh := float(HarboursChartGrid.LOGICAL_GRID_HEIGHT)
	if uv.x >= 0.0:
		_center_map = Vector2(uv.x * lw, uv.y * lh)
	else:
		_center_map = Vector2(lw * 0.5, lh * 0.5)
	_view_w = HarboursChartGrid.ROUTES_LOCAL_VIEW_WIDTH_MAP
	queue_redraw()


func _risk_color(risk: String) -> Color:
	var r := risk.to_lower()
	if r.contains("higher") or r.contains("high open"):
		return Color(0.95, 0.32, 0.28)
	if r.contains("moderate"):
		return Color(0.98, 0.78, 0.22)
	return Color(0.28, 0.82, 0.42)


func _view_geo() -> Dictionary:
	var sz: Vector2 = size
	var lw := float(HarboursChartGrid.LOGICAL_GRID_WIDTH)
	var lh := float(HarboursChartGrid.LOGICAL_GRID_HEIGHT)
	var vw: float = clampf(_view_w, _VIEW_W_MIN, minf(_VIEW_W_MAX, lw))
	if sz.x < 1.0:
		return {"tl": Vector2.ZERO, "vw": vw, "vh": 0.0, "sz": sz, "lw": lw, "lh": lh}
	var px_per_mx: float = sz.x / vw
	var vh: float = sz.y / px_per_mx
	var half := Vector2(vw * 0.5, vh * 0.5)
	var tl := _center_map - half
	tl.x = clampf(tl.x, 0.0, maxf(0.0, lw - vw))
	tl.y = clampf(tl.y, 0.0, maxf(0.0, lh - vh))
	return {"tl": tl, "vw": vw, "vh": vh, "sz": sz, "lw": lw, "lh": lh, "px_per_mx": px_per_mx}


func _map_to_screen(mx: float, my: float, geo: Dictionary) -> Vector2:
	var tl: Vector2 = geo["tl"]
	var vw: float = geo["vw"]
	var vh: float = geo["vh"]
	var sz: Vector2 = geo["sz"]
	return Vector2((mx - tl.x) / vw * sz.x, (my - tl.y) / vh * sz.y)


func _notification(what: int) -> void:
	if what == NOTIFICATION_DRAW:
		_draw_map()


func _draw_map() -> void:
	var geo := _view_geo()
	var sz: Vector2 = geo["sz"]
	if sz.x < 4.0 or sz.y < 4.0:
		return
	var tl: Vector2 = geo["tl"]
	var vw: float = geo["vw"]
	var vh: float = geo["vh"]
	var lw: float = geo["lw"]
	var lh: float = geo["lh"]

	if _texture == null:
		draw_rect(Rect2(Vector2.ZERO, sz), Color(0.07, 0.12, 0.2))
		return

	var tw: float = _texture.get_width()
	var th: float = _texture.get_height()
	var src := Rect2(tl.x / lw * tw, tl.y / lh * th, vw / lw * tw, vh / lh * th)
	var bounds := Rect2(0.0, 0.0, tw, th)
	src = src.intersection(bounds)
	if src.size.x < 0.5 or src.size.y < 0.5:
		draw_rect(Rect2(Vector2.ZERO, sz), Color(0.05, 0.08, 0.12))
		return
	var dest := Rect2(Vector2.ZERO, sz)
	draw_texture_rect_region(_texture, dest, src)

	var font := get_theme_default_font()
	var fz := 12
	var legend := "Risk: green low · yellow moderate · red higher open-sea / piracy read"
	draw_string(font, Vector2(8.0, 18.0), legend, HORIZONTAL_ALIGNMENT_LEFT, -1, fz, Color(0.85, 0.88, 0.92))

	for row in _rows:
		var d: Dictionary = row
		var pid := str(d.get("id", ""))
		var uv: Vector2 = _gs.get_port_map_uv(pid)
		if uv.x < 0.0:
			continue
		var mx: float = uv.x * lw
		var my: float = uv.y * lh
		var pscr: Vector2 = _map_to_screen(mx, my, geo)
		if pscr.x < -40.0 or pscr.y < -40.0 or pscr.x > sz.x + 40.0 or pscr.y > sz.y + 40.0:
			continue
		var risk: String = str(d.get("risk", ""))
		var col: Color = _risk_color(risk)
		var rad: float = 9.0
		draw_circle(pscr, rad + 1.5, Color(0.02, 0.03, 0.06, 0.65))
		draw_circle(pscr, rad, col)
		var pname: String = str(d.get("name", pid))
		var short := pname if pname.length() <= 18 else pname.substr(0, 16) + "…"
		draw_string(font, Vector2(pscr.x + rad + 5.0, pscr.y + 4.0), short, HORIZONTAL_ALIGNMENT_LEFT, -1, fz, Color(0.96, 0.94, 0.9))

	_draw_player_ship(geo, lw, lh)


func _draw_player_ship(geo: Dictionary, lw: float, lh: float) -> void:
	var player_uv: Vector2 = _gs.get_player_chart_uv()
	if player_uv.x < 0.0:
		return
	var hx: float = player_uv.x * lw
	var hy: float = player_uv.y * lh
	var hscr: Vector2 = _map_to_screen(hx, hy, geo)
	var sz: Vector2 = geo["sz"]
	if hscr.x < -80.0 or hscr.y < -80.0 or hscr.x > sz.x + 80.0 or hscr.y > sz.y + 80.0:
		return
	var sid := _gs.get_player_ship_class_id()
	if not HarboursShipVisualCatalog.draw_map_ship(self, hscr, sid):
		var cross := 14.0
		draw_line(hscr + Vector2(-cross, 0.0), hscr + Vector2(cross, 0.0), Color(0.95, 0.95, 1.0, 0.95), 2.0)
		draw_line(hscr + Vector2(0.0, -cross), hscr + Vector2(0.0, cross), Color(0.95, 0.95, 1.0, 0.95), 2.0)
	else:
		draw_circle(hscr, 5.0, Color(0.95, 0.92, 0.4, 0.85))


func _row_for_port(port_id: String) -> Dictionary:
	for row in _rows:
		var d: Dictionary = row
		if str(d.get("id", "")) == port_id:
			return d
	return {}


func _nearest_port_screen(screen_pos: Vector2, max_dist: float) -> String:
	var geo := _view_geo()
	var best_id := ""
	var best_d := max_dist
	for row in _rows:
		var d: Dictionary = row
		var pid := str(d.get("id", ""))
		var uv: Vector2 = _gs.get_port_map_uv(pid)
		if uv.x < 0.0:
			continue
		var lw: float = geo["lw"]
		var lh: float = geo["lh"]
		var mx: float = uv.x * lw
		var my: float = uv.y * lh
		var pscr: Vector2 = _map_to_screen(mx, my, geo)
		var dist: float = pscr.distance_to(screen_pos)
		if dist < best_d:
			best_d = dist
			best_id = pid
	return best_id


func _on_gui_input(ev: InputEvent) -> void:
	if ev is InputEventMouseButton:
		var mb := ev as InputEventMouseButton
		if mb.button_index == MOUSE_BUTTON_LEFT:
			if mb.pressed:
				_dragging = true
				_drag_moved = false
				_press_screen = mb.position
			else:
				if _dragging and not _drag_moved and _press_screen.distance_to(mb.position) < 6.0:
					var pick := _nearest_port_screen(mb.position, 36.0)
					if not pick.is_empty() and pick != _gs.player_port_id:
						sail_requested.emit(pick)
				_dragging = false
				_drag_moved = false
		elif mb.pressed:
			if mb.button_index == MOUSE_BUTTON_WHEEL_UP:
				_view_w = clampf(_view_w / _ZOOM_STEP, _VIEW_W_MIN, minf(_VIEW_W_MAX, float(HarboursChartGrid.LOGICAL_GRID_WIDTH)))
				queue_redraw()
				get_viewport().set_input_as_handled()
			elif mb.button_index == MOUSE_BUTTON_WHEEL_DOWN:
				_view_w = clampf(_view_w * _ZOOM_STEP, _VIEW_W_MIN, minf(_VIEW_W_MAX, float(HarboursChartGrid.LOGICAL_GRID_WIDTH)))
				queue_redraw()
				get_viewport().set_input_as_handled()
	elif ev is InputEventMouseMotion:
		var mm := ev as InputEventMouseMotion
		if _dragging and (mm.button_mask & MOUSE_BUTTON_MASK_LEFT) != 0:
			var geo := _view_geo()
			var vw: float = geo["vw"]
			var vh: float = geo["vh"]
			var sz: Vector2 = geo["sz"]
			if sz.x > 0.0 and sz.y > 0.0:
				_center_map -= Vector2(mm.relative.x / sz.x * vw, mm.relative.y / sz.y * vh)
			if mm.relative.length() > 1.5:
				_drag_moved = true
			queue_redraw()
		else:
			_update_hover(mm.position)


func _update_hover(screen_pos: Vector2) -> void:
	var lbl := get_node_or_null("RoutesMapHover") as Label
	if lbl == null:
		return
	var pid := _nearest_port_screen(screen_pos, 40.0)
	if pid.is_empty():
		lbl.text = ""
		return
	var d := _row_for_port(pid)
	var name: String = str(d.get("name", pid))
	var risk: String = str(d.get("risk", ""))
	var days: int = int(d.get("days", 0))
	var route: String = str(d.get("route", ""))
	var rel: int = int(d.get("reliability_pct", 0))
	var bits: PackedStringArray = PackedStringArray()
	bits.append(name)
	if days > 0:
		bits.append("%d d" % days)
	if not route.is_empty():
		bits.append(route)
	if not risk.is_empty():
		bits.append(risk)
	bits.append("%d%% rel." % rel)
	var glue := " — "
	var line := ""
	for i in range(bits.size()):
		if i > 0:
			line += glue
		line += bits[i]
	lbl.text = line


func apply_fill_height() -> void:
	var p := get_parent()
	if p == null:
		return
	var gp := p.get_parent()
	if gp != null and not (gp is ScrollContainer):
		custom_minimum_size = Vector2.ZERO
		queue_redraw()
		return
	var sc := gp as ScrollContainer
	if sc == null or not is_instance_valid(sc):
		custom_minimum_size.y = int(get_viewport().get_visible_rect().size.y * 0.58)
		return
	var h: int = int(sc.size.y) - 56
	if h < 260:
		h = int(get_viewport().get_visible_rect().size.y * 0.58)
	custom_minimum_size = Vector2(0, h)

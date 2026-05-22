extends Control
class_name WorldMapChart

## Chunk-based Mediterranean chart (Phase C). Same UX contract as RoutesMapChart.

signal sail_requested(port_id: String)

var _gs: HarboursGameState
var _rows: Array = []
var _projection := HarboursChartProjection.new()
var _manifest: Dictionary = {}
var _chunks: Array = []
var _textures: Dictionary = {}  # path -> Texture2D

var _dragging := false
var _drag_moved := false
var _press_screen: Vector2


func setup(gs: HarboursGameState, rows: Array) -> void:
	_gs = gs
	_rows = rows
	_load_chunks()
	_projection.reset_center_from_uv(_gs.get_port_map_uv(_gs.player_port_id))
	queue_redraw()


func _load_chunks() -> void:
	_manifest = HarboursChunkManifestLoader.load_document()
	_chunks = HarboursChunkManifestLoader.load_chunks(_manifest)
	_projection.configure_from_manifest(_manifest)
	_textures.clear()
	for entry in _chunks:
		var d: Dictionary = entry
		var path := str(d.get("path", ""))
		if path.is_empty() or _textures.has(path):
			continue
		if ResourceLoader.exists(path):
			var tex: Texture2D = load(path) as Texture2D
			if tex != null:
				_textures[path] = tex


static func is_available() -> bool:
	return HarboursChunkManifestLoader.manifest_available()


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
	if vp != null and not vp.size_changed.is_connected(apply_fill_height):
		vp.size_changed.connect(apply_fill_height)
	call_deferred("apply_fill_height")


func _exit_tree() -> void:
	var vp := get_viewport()
	if vp != null and vp.size_changed.is_connected(apply_fill_height):
		vp.size_changed.disconnect(apply_fill_height)


func _risk_color(risk: String) -> Color:
	var r := risk.to_lower()
	if r.contains("higher") or r.contains("high open"):
		return Color(0.95, 0.32, 0.28)
	if r.contains("moderate"):
		return Color(0.98, 0.78, 0.22)
	return Color(0.28, 0.82, 0.42)


func _notification(what: int) -> void:
	if what == NOTIFICATION_DRAW:
		_draw_map()


func _draw_map() -> void:
	var geo := _projection.view_geo(size)
	var sz: Vector2 = geo["sz"]
	if sz.x < 4.0 or sz.y < 4.0:
		return
	var vis := _projection.visible_map_rect(geo)

	if _chunks.is_empty():
		draw_rect(Rect2(Vector2.ZERO, sz), Color(0.07, 0.12, 0.2))
		_draw_legend(geo)
		return

	for entry in _chunks:
		_draw_chunk(entry, geo, vis)

	_draw_ports(geo)
	_draw_legend(geo)


func _draw_chunk(entry: Dictionary, geo: Dictionary, vis: Rect2) -> void:
	var path := str(entry.get("path", ""))
	if not _textures.has(path):
		return
	var tex: Texture2D = _textures[path]
	var x0 := float(entry.get("x0", 0))
	var y0 := float(entry.get("y0", 0))
	var x1 := float(entry.get("x1", 0))
	var y1 := float(entry.get("y1", 0))
	var chunk_rect := Rect2(x0, y0, x1 - x0, y1 - y0)
	var clip := chunk_rect.intersection(vis)
	if clip.size.x < 0.5 or clip.size.y < 0.5:
		return
	var cw := maxf(x1 - x0, 1.0)
	var ch := maxf(y1 - y0, 1.0)
	var tw := float(tex.get_width())
	var th := float(tex.get_height())
	var src := Rect2(
		(clip.position.x - x0) / cw * tw,
		(clip.position.y - y0) / ch * th,
		clip.size.x / cw * tw,
		clip.size.y / ch * th,
	)
	var tl_scr := _projection.map_to_screen(clip.position.x, clip.position.y, geo)
	var br_scr := _projection.map_to_screen(clip.end.x, clip.end.y, geo)
	var dest := Rect2(tl_scr, br_scr - tl_scr)
	if dest.size.x < 0.5 or dest.size.y < 0.5:
		return
	draw_texture_rect_region(tex, dest, src)


func _draw_ports(geo: Dictionary) -> void:
	var font := get_theme_default_font()
	var fz := 12
	var sz: Vector2 = geo["sz"]
	for row in _rows:
		var d: Dictionary = row
		var pid := str(d.get("id", ""))
		var uv: Vector2 = _gs.get_port_map_uv(pid)
		if uv.x < 0.0:
			continue
		var mp := _projection.uv_to_map(uv)
		var pscr := _projection.map_to_screen(mp.x, mp.y, geo)
		if pscr.x < -40.0 or pscr.y < -40.0 or pscr.x > sz.x + 40.0 or pscr.y > sz.y + 40.0:
			continue
		var col := _risk_color(str(d.get("risk", "")))
		var rad := 9.0
		draw_circle(pscr, rad + 1.5, Color(0.02, 0.03, 0.06, 0.65))
		draw_circle(pscr, rad, col)
		var pname: String = str(d.get("name", pid))
		var short := pname if pname.length() <= 18 else pname.substr(0, 16) + "…"
		draw_string(font, Vector2(pscr.x + rad + 5.0, pscr.y + 4.0), short, HORIZONTAL_ALIGNMENT_LEFT, -1, fz, Color(0.96, 0.94, 0.9))

	var here_uv: Vector2 = _gs.get_port_map_uv(_gs.player_port_id)
	if here_uv.x >= 0.0:
		var hp := _projection.uv_to_map(here_uv)
		var hscr := _projection.map_to_screen(hp.x, hp.y, geo)
		var cross := 14.0
		draw_line(hscr + Vector2(-cross, 0.0), hscr + Vector2(cross, 0.0), Color(0.95, 0.95, 1.0, 0.95), 2.0)
		draw_line(hscr + Vector2(0.0, -cross), hscr + Vector2(0.0, cross), Color(0.95, 0.95, 1.0, 0.95), 2.0)


func _draw_legend(geo: Dictionary) -> void:
	var font := get_theme_default_font()
	var n := _chunks.size()
	var legend := "Chunk map (%d) · drag pan · wheel zoom · click port to sail" % n
	draw_string(font, Vector2(8.0, 18.0), legend, HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color(0.85, 0.88, 0.92))


func _row_for_port(port_id: String) -> Dictionary:
	for row in _rows:
		var d: Dictionary = row
		if str(d.get("id", "")) == port_id:
			return d
	return {}


func _nearest_port_screen(screen_pos: Vector2, max_dist: float) -> String:
	var geo := _projection.view_geo(size)
	var best_id := ""
	var best_d := max_dist
	for row in _rows:
		var d: Dictionary = row
		var pid := str(d.get("id", ""))
		var uv: Vector2 = _gs.get_port_map_uv(pid)
		if uv.x < 0.0:
			continue
		var mp := _projection.uv_to_map(uv)
		var pscr := _projection.map_to_screen(mp.x, mp.y, geo)
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
				_projection.view_w = clampf(
					_projection.view_w / HarboursChartProjection.VIEW_ZOOM_STEP,
					HarboursChartProjection.VIEW_W_MIN,
					_projection.view_w_max(),
				)
				queue_redraw()
				get_viewport().set_input_as_handled()
			elif mb.button_index == MOUSE_BUTTON_WHEEL_DOWN:
				_projection.view_w = clampf(
					_projection.view_w * HarboursChartProjection.VIEW_ZOOM_STEP,
					HarboursChartProjection.VIEW_W_MIN,
					_projection.view_w_max(),
				)
				queue_redraw()
				get_viewport().set_input_as_handled()
	elif ev is InputEventMouseMotion:
		var mm := ev as InputEventMouseMotion
		if _dragging and (mm.button_mask & MOUSE_BUTTON_MASK_LEFT) != 0:
			var geo := _projection.view_geo(size)
			_projection.center_map -= _projection.screen_to_map_delta(mm.relative, geo)
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

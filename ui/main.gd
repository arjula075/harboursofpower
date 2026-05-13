extends Control

const _PLACE_MARKET := 0
const _PLACE_HARBOR := 1
const _PLACE_INFLUENCE := 2
const _PLACE_TAVERN := 3
const _PLACE_LEDGER := 4
const _PLACE_ROUTES := 5

const _CITY_PLACE_LABELS: PackedStringArray = [
	"Market",
	"Harbor",
	"Influence",
	"Tavern & intel",
	"Ledger",
	"Routes",
]

const _SEA_CHART_PATH := "res://assets/ui/sea_chart.svg"
const _STATUS_LOG_MAX_CHARS := 12000
## Engine `TooltipLabel` width for word wrap (fraction of game viewport width).
const _TOOLTIP_WRAP_WIDTH_FRAC := 0.3

@onready var _gs: HarboursGameState = get_node("/root/GameState") as HarboursGameState
@onready var day_label: Label = %DayLabel
@onready var money_label: Label = %MoneyLabel
@onready var cargo_label: Label = %CargoLabel
@onready var port_stock_label: Label = %PortStockLabel
@onready var location_label: Label = %LocationLabel
@onready var city_title: Label = %CityTitle
@onready var city_places_vbox: VBoxContainer = %CityPlacesVBox
@onready var advance_button: Button = %AdvanceButton
@onready var save_button: Button = %SaveButton
@onready var load_button: Button = %LoadButton
@onready var status_log: TextEdit = %StatusLog
@onready var trade_box: VBoxContainer = %TradeBox
@onready var admin_window: Window = %AdminWindow
@onready var admin_dump_text: TextEdit = %AdminDumpText
@onready var refresh_admin_button: Button = %RefreshAdmin
@onready var close_admin_button: Button = %CloseAdmin

var _city_place_index: int = _PLACE_MARKET
var _city_place_group: ButtonGroup = ButtonGroup.new()
var _city_place_buttons_built: bool = false
var _captains_chart: Control = null
var _ledger_area_list: ItemList = null
var _ledger_port_list: ItemList = null
var _ledger_goods_host: VBoxContainer = null
var _ledger_last_area_id: String = ""
var _ledger_last_port_id: String = ""


func _ready() -> void:
	status_log.focus_mode = Control.FOCUS_NONE
	advance_button.pressed.connect(_on_advance_pressed)
	save_button.pressed.connect(_on_save_pressed)
	load_button.pressed.connect(_on_load_pressed)
	_gs.day_advanced.connect(_on_day_advanced)
	_gs.voyage_started.connect(_on_voyage_started)
	_gs.voyage_completed.connect(_on_voyage_completed)
	_gs.game_saved.connect(_on_game_saved)
	_gs.game_loaded.connect(_on_game_loaded)
	_gs.game_load_failed.connect(_on_game_load_failed)
	_gs.cargo_changed.connect(_on_cargo_money)
	_gs.money_changed.connect(_on_cargo_money)
	_gs.market_changed.connect(_on_market_changed)
	_gs.food_riot_report.connect(_on_food_riot_report)
	_gs.crop_rumor_report.connect(_on_crop_rumor_report)
	_gs.player_encounter_report.connect(_on_player_encounter_report)
	refresh_admin_button.pressed.connect(_refresh_admin_dump_text)
	close_admin_button.pressed.connect(_hide_admin_window)
	admin_window.close_requested.connect(_hide_admin_window)
	admin_window.hide()
	status_log.text = ""
	_append_log("Numbers on every table are tagged with source, age, and reliability — not omniscient truth.")
	get_tree().node_added.connect(_on_scene_tree_node_added_for_tooltips)
	get_viewport().size_changed.connect(_on_viewport_size_changed_for_tooltips)
	_rebuild_trade()
	_refresh_header()


func _tooltip_wrap_width_px() -> int:
	var vp := get_viewport()
	if vp == null:
		return 480
	var w: int = int(vp.get_visible_rect().size.x * _TOOLTIP_WRAP_WIDTH_FRAC)
	return maxi(160, w)


func _apply_wrapped_tooltip_label(lbl: Label) -> void:
	lbl.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	lbl.custom_minimum_size = Vector2(float(_tooltip_wrap_width_px()), 0.0)


func _on_scene_tree_node_added_for_tooltips(node: Node) -> void:
	if not (node is Label):
		return
	if str(node.get_class()) != "TooltipLabel":
		return
	_apply_wrapped_tooltip_label(node as Label)


func _on_viewport_size_changed_for_tooltips() -> void:
	var w: float = float(_tooltip_wrap_width_px())
	_recurse_tooltip_labels_set_width(get_tree().root, w)


func _recurse_tooltip_labels_set_width(node: Node, width_px: float) -> void:
	if node is Label and str(node.get_class()) == "TooltipLabel":
		var lbl: Label = node as Label
		lbl.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		lbl.custom_minimum_size = Vector2(width_px, 0.0)
	for c in node.get_children():
		_recurse_tooltip_labels_set_width(c, width_px)


func _append_log(line: String) -> void:
	var stamp: String = str(_gs.current_day) if _gs != null else "—"
	var block: String = "[%s] %s\n%s" % [stamp, line, status_log.text]
	if block.length() > _STATUS_LOG_MAX_CHARS:
		block = block.substr(0, _STATUS_LOG_MAX_CHARS)
	status_log.text = block


func _on_market_changed() -> void:
	call_deferred("_deferred_rebuild_trade_and_header")


func _on_day_advanced(_new_day: int) -> void:
	_rebuild_trade()
	_refresh_header()
	_maybe_refresh_admin_dump()


func _on_voyage_started(_to: String, _days: int) -> void:
	call_deferred("_deferred_rebuild_trade_and_header")


func _on_voyage_completed(_at: String) -> void:
	_rebuild_trade()
	_refresh_header()


func _on_cargo_money() -> void:
	_refresh_header()


func _on_game_saved(_path: String) -> void:
	_append_log("Saved campaign.")
	_refresh_header()


func _on_game_loaded(_path: String) -> void:
	_append_log("Loaded campaign.")
	_rebuild_trade()
	_refresh_header()
	_maybe_refresh_admin_dump()


func _on_game_load_failed(reason: String) -> void:
	_append_log("Load failed: %s" % reason)


func _on_food_riot_report(summary: String) -> void:
	if not summary.is_empty():
		_append_log(summary)


func _on_crop_rumor_report(summary: String) -> void:
	if not summary.is_empty():
		_append_log(summary)


func _on_player_encounter_report(summary: String) -> void:
	if not summary.is_empty():
		_append_log(summary)


func _refresh_header() -> void:
	day_label.text = _gs.get_calendar_header_line()
	money_label.text = "Coins: %d" % _gs.get_money()
	cargo_label.text = _gs.get_cargo_summary() + "\n" + _gs.get_ship_status_line()
	if _gs.is_at_sea():
		port_stock_label.visible = false
		port_stock_label.text = ""
	else:
		port_stock_label.visible = true
		port_stock_label.text = "Port stock: on each Market row · Moods & reads: Tavern tab"
	location_label.text = _gs.get_location_summary()


func _append_wrapped(v: VBoxContainer, text: String) -> void:
	var lb := Label.new()
	lb.text = text
	lb.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	v.add_child(lb)


func _card_section(parent: VBoxContainer, title: String) -> VBoxContainer:
	var panel := PanelContainer.new()
	var margin := MarginContainer.new()
	margin.add_theme_constant_override("margin_left", 10)
	margin.add_theme_constant_override("margin_top", 8)
	margin.add_theme_constant_override("margin_right", 10)
	margin.add_theme_constant_override("margin_bottom", 10)
	var inner := VBoxContainer.new()
	inner.add_theme_constant_override("separation", 6)
	var ttl := Label.new()
	ttl.text = title
	ttl.add_theme_font_size_override("font_size", 13)
	inner.add_child(ttl)
	margin.add_child(inner)
	panel.add_child(margin)
	parent.add_child(panel)
	return inner


func _tbl_cell(txt: String, min_w: float = 0.0) -> Label:
	var lb := Label.new()
	lb.text = txt
	lb.autowrap_mode = TextServer.AUTOWRAP_OFF
	if min_w > 0.0:
		lb.custom_minimum_size.x = min_w
	lb.add_theme_font_size_override("font_size", 11)
	return lb


func _truncate(s: String, max_len: int) -> String:
	if s.length() <= max_len:
		return s
	return s.substr(0, maxi(0, max_len - 1)) + "…"


func _ensure_city_place_buttons() -> void:
	if _city_place_buttons_built:
		return
	_city_place_buttons_built = true
	for i in range(_CITY_PLACE_LABELS.size()):
		var b := Button.new()
		b.text = _CITY_PLACE_LABELS[i]
		b.toggle_mode = true
		b.button_group = _city_place_group
		b.focus_mode = Control.FOCUS_NONE
		b.pressed.connect(_on_city_place_pressed.bind(i))
		city_places_vbox.add_child(b)


func _sync_city_place_buttons() -> void:
	var ch := city_places_vbox.get_children()
	for i in range(ch.size()):
		if ch[i] is Button:
			(ch[i] as Button).set_pressed_no_signal(i == _city_place_index)


func _on_city_place_pressed(place_idx: int) -> void:
	_city_place_index = place_idx
	_sync_city_place_buttons()
	_rebuild_city_place_content()


func _rebuild_trade() -> void:
	for c in trade_box.get_children():
		trade_box.remove_child(c)
		c.free()
	_captains_chart = null
	city_places_vbox.show()
	city_title.text = "City"
	if _gs.is_at_sea():
		city_title.text = "Under way"
		city_places_vbox.hide()
		var voyage_intel: String = _gs.get_player_voyage_intel_block()
		if not voyage_intel.is_empty():
			_append_wrapped(trade_box, voyage_intel)
		_append_wrapped(trade_box, "No city tables while the hull is at sea — advance days until landfall.")
		return
	city_title.text = "City — %s" % _gs.get_port_name(_gs.player_port_id)
	_ensure_city_place_buttons()
	_sync_city_place_buttons()
	_rebuild_city_place_content()


func _rebuild_city_place_content() -> void:
	for c in trade_box.get_children():
		trade_box.remove_child(c)
		c.free()
	match _city_place_index:
		_PLACE_MARKET:
			_build_market_panel(trade_box)
		_PLACE_HARBOR:
			_build_harbor_panel(trade_box)
		_PLACE_INFLUENCE:
			_build_influence_panel(trade_box)
		_PLACE_TAVERN:
			_build_tavern_panel(trade_box)
		_PLACE_LEDGER:
			_build_ledger_panel(trade_box)
		_PLACE_ROUTES:
			_build_routes_panel(trade_box)
		_:
			_append_wrapped(trade_box, "Unknown view.")


func _build_market_panel(parent: VBoxContainer) -> void:
	var hint_row := HBoxContainer.new()
	hint_row.add_theme_constant_override("separation", 8)
	var hint := Label.new()
	hint.text = "Each tile is one good: port stock is the city tally on the row; trend compares to yesterday’s ask before the dawn bell."
	hint.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	hint.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	hint.add_theme_font_size_override("font_size", 10)
	hint_row.add_child(hint)
	var digest_btn := Button.new()
	digest_btn.text = "City supply digest → log"
	digest_btn.add_theme_font_size_override("font_size", 10)
	digest_btn.tooltip_text = "Farms, mines, population — same text the old card showed."
	digest_btn.pressed.connect(_append_log.bind(_gs.get_port_city_supply_digest()))
	hint_row.add_child(digest_btn)
	var stocks_btn := Button.new()
	stocks_btn.text = "Full port stock line → log"
	stocks_btn.add_theme_font_size_override("font_size", 10)
	stocks_btn.tooltip_text = "All goods in one clerk-style sentence."
	stocks_btn.pressed.connect(_append_log.bind(_gs.get_port_market_line()))
	hint_row.add_child(stocks_btn)
	parent.add_child(hint_row)
	parent.add_child(HSeparator.new())
	var rows: Array = _gs.list_player_market_table_rows()
	var cols := HBoxContainer.new()
	cols.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	cols.add_theme_constant_override("separation", 10)
	for _ci in range(3):
		var vb := VBoxContainer.new()
		vb.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		vb.size_flags_vertical = Control.SIZE_SHRINK_BEGIN
		cols.add_child(vb)
	for i in range(rows.size()):
		var d: Dictionary = rows[i] as Dictionary
		var col: VBoxContainer = cols.get_child(i % 3) as VBoxContainer
		col.add_child(_make_market_good_block(d))
	parent.add_child(cols)


func _make_market_good_block(d: Dictionary) -> VBoxContainer:
	var block := VBoxContainer.new()
	block.add_theme_constant_override("separation", 3)
	var gid := str(d.get("good_id", ""))
	var src: String = _truncate(str(d.get("source", "")), 44)
	var line: String = (
		"%s · port stock %d · buy %dc · sell %dc · toll %dc/u · trend %s · trade age %dd · %d%% · %s"
		% [
			str(d.get("name", "")),
			int(d.get("port_qty", 0)),
			int(d.get("buy_unit", 0)),
			int(d.get("sell_unit", 0)),
			int(d.get("toll_per_unit", 0)),
			str(d.get("trend", "—")),
			int(d.get("age_days", 0)),
			int(d.get("reliability_pct", 0)),
			src,
		]
	)
	var cap := Label.new()
	cap.text = line
	cap.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	cap.add_theme_font_size_override("font_size", 10)
	block.add_child(cap)
	var why := Button.new()
	why.text = "?"
	why.add_theme_font_size_override("font_size", 10)
	why.tooltip_text = _gs.get_player_data_provenance("market_good", gid)
	why.focus_mode = Control.FOCUS_NONE
	why.pressed.connect(_append_log.bind(_gs.get_player_data_provenance("market_good", gid)))
	block.add_child(why)
	var row_btns := HBoxContainer.new()
	row_btns.add_theme_constant_override("separation", 4)
	for qty_raw in [1, 5]:
		var qty: int = int(qty_raw)
		var bbtn := Button.new()
		var cost: int = _gs.get_trade_buy_total_coins(gid, qty)
		bbtn.text = "Buy +%d (%dc)" % [qty, cost]
		bbtn.add_theme_font_size_override("font_size", 9)
		bbtn.disabled = (
			_gs.get_money() < cost
			or int(d.get("port_qty", 0)) < qty
			or _gs.get_player_cargo_used() + qty > _gs.get_player_cargo_capacity()
		)
		bbtn.pressed.connect(_on_buy_pressed.bind(gid, qty))
		row_btns.add_child(bbtn)
	for qty_raw in [1, 5]:
		var qtys: int = int(qty_raw)
		var sbtn := Button.new()
		var revenue: int = _gs.get_trade_sell_net_coins(gid, qtys)
		sbtn.text = "Sell −%d (+%dc)" % [qtys, revenue]
		sbtn.add_theme_font_size_override("font_size", 9)
		var player_have: int = _gs.get_player_cargo_qty(gid)
		sbtn.disabled = player_have < qtys
		sbtn.pressed.connect(_on_sell_pressed.bind(gid, qtys))
		row_btns.add_child(sbtn)
	block.add_child(row_btns)
	return block


func _build_harbor_panel(parent: VBoxContainer) -> void:
	var slip: String = _gs.get_used_hull_slip_summary_line()
	if not slip.is_empty():
		var slip_card := _card_section(parent, "Slip board")
		_append_wrapped(slip_card, slip)
	_append_wrapped(
		parent,
		"Harbor: fleet, slip builds, used hulls. Hull repairs still run overnight when timber, textiles, metal, and coin allow."
	)
	var grid := GridContainer.new()
	grid.columns = 9
	var hdrs: PackedStringArray = [
		"Ship",
		"Cargo",
		"Speed",
		"Cond.",
		"Crew",
		"Risk",
		"Captain",
		"Status",
		"Why",
	]
	for h in hdrs:
		grid.add_child(_tbl_cell(h, 24.0))
	for row in _gs.list_player_harbor_ship_rows():
		var d: Dictionary = row
		grid.add_child(_tbl_cell(str(d.get("ship", "")), 100.0))
		grid.add_child(_tbl_cell(str(d.get("cargo", "")), 52.0))
		grid.add_child(_tbl_cell(str(int(d.get("speed_score", 0))), 36.0))
		grid.add_child(_tbl_cell(str(int(d.get("condition", 0))), 36.0))
		grid.add_child(_tbl_cell(str(d.get("crew_note", "")), 72.0))
		grid.add_child(_tbl_cell(str(d.get("risk", "")), 80.0))
		grid.add_child(_tbl_cell(str(d.get("captain", "")), 48.0))
		grid.add_child(_tbl_cell(str(d.get("status", "")), 56.0))
		var whyh := Button.new()
		whyh.text = "?"
		whyh.tooltip_text = _gs.get_player_data_provenance("harbor", "fleet")
		whyh.focus_mode = Control.FOCUS_NONE
		whyh.pressed.connect(_append_log.bind(_gs.get_player_data_provenance("harbor", "fleet")))
		grid.add_child(whyh)
	parent.add_child(grid)
	_build_dock_fleet_section(parent)


func _build_influence_panel(parent: VBoxContainer) -> void:
	_append_wrapped(
		parent,
		"Influence — registers, temple marks, and quay mood. Each metric row carries source, age, and stated confidence."
	)
	var reg := _gs.get_player_city_official_intel_block()
	if not reg.is_empty():
		_append_wrapped(parent, reg)
	var grid := GridContainer.new()
	grid.columns = 6
	for h in ["Metric", "Value", "Source", "Age", "Rel.", "Why"]:
		grid.add_child(_tbl_cell(h, 20.0))
	for row in _gs.list_player_influence_metrics():
		var d: Dictionary = row
		grid.add_child(_tbl_cell(str(d.get("metric", "")), 100.0))
		grid.add_child(_tbl_cell(str(d.get("value", "")), 44.0))
		grid.add_child(_tbl_cell(_truncate(str(d.get("source", "")), 28), 100.0))
		grid.add_child(_tbl_cell("%dd" % int(d.get("age_days", 0)), 28.0))
		grid.add_child(_tbl_cell("%d%%" % int(d.get("reliability_pct", 0)), 32.0))
		var wi := Button.new()
		wi.text = "?"
		wi.tooltip_text = _gs.get_player_data_provenance("influence", str(d.get("metric", "")))
		wi.focus_mode = Control.FOCUS_NONE
		wi.pressed.connect(_append_log.bind(_gs.get_player_data_provenance("influence", str(d.get("metric", "")))))
		grid.add_child(wi)
	parent.add_child(grid)
	parent.add_child(HSeparator.new())
	_append_wrapped(parent, _gs.get_player_city_temple_intel_block())
	var vow := HBoxContainer.new()
	vow.add_theme_constant_override("separation", 8)
	for ti in range(3):
		var ob := Button.new()
		var tier_name: String = (["Small", "Fair", "Grand"])[ti]
		ob.text = "%s offering (%dc)" % [tier_name, _gs.get_temple_offering_coin_cost(ti)]
		ob.disabled = not _gs.player_can_make_temple_offering(ti)
		ob.pressed.connect(_on_temple_offering_pressed.bind(ti))
		vow.add_child(ob)
	parent.add_child(vow)
	if _gs.player_port_has_mint():
		parent.add_child(HSeparator.new())
		var mint_box := VBoxContainer.new()
		mint_box.add_theme_constant_override("separation", 6)
		_append_wrapped(mint_box, _gs.get_player_mint_dock_summary())
		var mint_btn := Button.new()
		mint_btn.text = "Strike one mint batch from cargo (gold + silver)"
		mint_btn.disabled = not _gs.player_can_strike_mint_batch_from_cargo()
		mint_btn.pressed.connect(_on_mint_batch_pressed)
		mint_box.add_child(mint_btn)
		parent.add_child(mint_box)
	if _gs.player_docked_port_has_tolls():
		parent.add_child(HSeparator.new())
		var pol := VBoxContainer.new()
		pol.add_theme_constant_override("separation", 6)
		var pol_lbl := Label.new()
		var gday: int = int(_gs.get_player_customs_graft_until_day())
		var graft_line: String = (
			"Customs graft active here through day %d (import duties waived on your sales)."
			% gday
			if gday >= _gs.current_day
			else "Quaestor duties on cargo you sell into this city — a discreet gift can buy silence."
		)
		pol_lbl.text = "Quaestor — " + graft_line
		pol_lbl.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		pol.add_child(pol_lbl)
		var graft_cost: int = _gs.get_player_customs_graft_coin_cost()
		var graft_btn := Button.new()
		graft_btn.text = "Offer customs graft (~%dc; waives your tolls here for several days)" % graft_cost
		graft_btn.disabled = _gs.get_money() < graft_cost or (gday >= _gs.current_day)
		graft_btn.pressed.connect(_on_customs_graft_pressed)
		pol.add_child(graft_btn)
		parent.add_child(pol)
	_append_wrapped(
		parent,
		"Later: public-works tithe, sealed privilege, contract broker — for now temple, mint, and quaestor gifts cover most face."
	)


func _build_tavern_panel(parent: VBoxContainer) -> void:
	var moods := _card_section(parent, "Moods & your reads")
	_append_wrapped(moods, _gs.get_player_tavern_mood_block())
	parent.add_child(HSeparator.new())
	_append_wrapped(parent, _gs.get_player_city_tavern_intel_block())
	parent.add_child(HSeparator.new())
	var escort_offer := CheckBox.new()
	escort_offer.text = "Offer crew for NPC convoy escort jobs (fast hulls only; pay on safe arrival)"
	escort_offer.button_pressed = _gs.get_player_offers_convoy_escort()
	escort_offer.toggled.connect(_on_convoy_escort_offer_toggled)
	parent.add_child(escort_offer)
	var grid := GridContainer.new()
	grid.columns = 7
	for h in ["Rumor", "Area", "Age", "Rel.", "Verify", "Action", "Why"]:
		grid.add_child(_tbl_cell(h, 20.0))
	for row in _gs.list_player_tavern_rumor_rows():
		var d: Dictionary = row
		var kind := str(d.get("intel_kind", ""))
		grid.add_child(_tbl_cell(_truncate(str(d.get("summary", "")), 40), 140.0))
		grid.add_child(_tbl_cell(str(d.get("area", "")), 72.0))
		grid.add_child(_tbl_cell("%dd" % int(d.get("age_days", 0)), 28.0))
		grid.add_child(_tbl_cell("%d%%" % int(d.get("reliability_pct", 0)), 32.0))
		grid.add_child(_tbl_cell("%dc" % int(d.get("verify_cost", 0)), 36.0))
		var act := Button.new()
		act.text = "Pay / investigate" if kind != "routes" else "Refresh tables"
		act.add_theme_font_size_override("font_size", 10)
		act.pressed.connect(_on_tavern_intel_row_pressed.bind(kind))
		act.disabled = _intel_row_disabled(kind)
		grid.add_child(act)
		var wq := Button.new()
		wq.text = "?"
		wq.tooltip_text = "Paid work tightens reads or buys clerk time — still not omniscience."
		wq.focus_mode = Control.FOCUS_NONE
		wq.pressed.connect(_append_log.bind("Intel row (%s): coin buys procedure, not prophecy." % kind))
		grid.add_child(wq)
	parent.add_child(grid)
	var rumor_tools := HBoxContainer.new()
	rumor_tools.add_theme_constant_override("separation", 8)
	var spr_tight := Button.new()
	spr_tight.text = "Spread scarcity whispers (%dc)" % _gs.get_player_crop_intel_spread_rumor_coin_cost()
	spr_tight.disabled = not _gs.player_can_spread_crop_market_rumor()
	spr_tight.pressed.connect(_on_spread_crop_rumor_pressed.bind(true))
	rumor_tools.add_child(spr_tight)
	var spr_soft := Button.new()
	spr_soft.text = "Spread plenty whispers (%dc)" % _gs.get_player_crop_intel_spread_rumor_coin_cost()
	spr_soft.disabled = not _gs.player_can_spread_crop_market_rumor()
	spr_soft.pressed.connect(_on_spread_crop_rumor_pressed.bind(false))
	rumor_tools.add_child(spr_soft)
	var war_hot := Button.new()
	war_hot.text = "Inflame war fear (%dc)" % _gs.get_player_war_intel_spread_rumor_coin_cost()
	war_hot.disabled = not _gs.player_can_spread_war_rumor()
	war_hot.pressed.connect(_on_spread_war_rumor_pressed.bind(true))
	rumor_tools.add_child(war_hot)
	var war_calm := Button.new()
	war_calm.text = "Cool war fear (%dc)" % _gs.get_player_war_intel_spread_rumor_coin_cost()
	war_calm.disabled = not _gs.player_can_spread_war_rumor()
	war_calm.pressed.connect(_on_spread_war_rumor_pressed.bind(false))
	rumor_tools.add_child(war_calm)
	parent.add_child(rumor_tools)


func _intel_row_disabled(kind: String) -> bool:
	match str(kind):
		"crop":
			return not _gs.player_can_investigate_crop_market_intel()
		"war":
			return not _gs.player_can_investigate_war_rumor_intel()
		"piracy", "routes":
			return _gs.get_money() < _gs.get_player_intel_verify_coin_cost(kind)
		_:
			return true


func _on_tavern_intel_row_pressed(kind: String) -> void:
	if not _gs.try_player_buy_intel(kind):
		_append_log("Could not buy intel (%s) — coin, place, or already certain." % kind)
		return
	_refresh_header()
	_maybe_refresh_admin_dump()
	_append_log("Paid for %s intel / clerk refresh." % kind)
	_rebuild_trade()


func _build_ledger_panel(parent: VBoxContainer) -> void:
	var areas_data: Array = _gs.list_player_ledger_chart_areas()
	if areas_data.is_empty():
		_append_wrapped(parent, "No chart entries yet — your purser is still mute.")
		return
	var hint := Label.new()
	hint.text = (
		_gs.get_player_ledger_summary_line()
		+ " Pick a sea, then a harbor — the lower pane is your remembered buy / sell / toll (not live quay unless you just advanced docked there)."
	)
	hint.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	hint.add_theme_font_size_override("font_size", 11)
	hint.size_flags_vertical = Control.SIZE_SHRINK_BEGIN
	parent.add_child(hint)
	var log_digest := Button.new()
	log_digest.text = "Full harbor digest → status log"
	log_digest.add_theme_font_size_override("font_size", 10)
	log_digest.tooltip_text = "Long recap: every harbor’s grain band, source, and reliability (same text as the old ledger header)."
	log_digest.pressed.connect(_append_log.bind(_gs.get_player_ledger_block()))
	log_digest.size_flags_vertical = Control.SIZE_SHRINK_BEGIN
	parent.add_child(log_digest)
	var vsplit := VSplitContainer.new()
	vsplit.size_flags_vertical = Control.SIZE_EXPAND_FILL
	vsplit.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	vsplit.custom_minimum_size = Vector2(0, 360)
	var top_hs := HSplitContainer.new()
	top_hs.size_flags_vertical = Control.SIZE_EXPAND_FILL
	top_hs.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var left := VBoxContainer.new()
	left.custom_minimum_size = Vector2(200, 0)
	left.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var sea_lbl := Label.new()
	sea_lbl.text = "Chart areas"
	sea_lbl.add_theme_font_size_override("font_size", 12)
	left.add_child(sea_lbl)
	var area_list := ItemList.new()
	area_list.size_flags_vertical = Control.SIZE_EXPAND_FILL
	area_list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	area_list.custom_minimum_size = Vector2(200, 96)
	for ad in areas_data:
		var rowa: Dictionary = ad
		var aid := str(rowa.get("area_id", ""))
		var nm := str(rowa.get("area_name", aid))
		var nports := int(rowa.get("known_ports", 0))
		area_list.add_item("%s (%d)" % [nm, nports])
		var idxa := area_list.item_count - 1
		area_list.set_item_metadata(idxa, aid)
		var tip := _gs.get_chart_area_description(aid)
		if not tip.is_empty():
			area_list.set_item_tooltip(idxa, tip)
	left.add_child(area_list)
	top_hs.add_child(left)
	var port_col := VBoxContainer.new()
	port_col.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	port_col.custom_minimum_size = Vector2(220, 0)
	var port_lbl := Label.new()
	port_lbl.text = "Harbors (hover for grain band & source)"
	port_lbl.add_theme_font_size_override("font_size", 12)
	port_col.add_child(port_lbl)
	var port_list := ItemList.new()
	port_list.size_flags_vertical = Control.SIZE_EXPAND_FILL
	port_list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	port_list.custom_minimum_size = Vector2(220, 96)
	port_col.add_child(port_list)
	top_hs.add_child(port_col)
	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.custom_minimum_size = Vector2(0, 260)
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	var goods_host := VBoxContainer.new()
	goods_host.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	goods_host.size_flags_vertical = Control.SIZE_EXPAND_FILL
	goods_host.custom_minimum_size = Vector2(0, 120)
	scroll.add_child(goods_host)
	vsplit.add_child(top_hs)
	vsplit.add_child(scroll)
	parent.add_child(vsplit)
	vsplit.split_offset = 200
	_ledger_area_list = area_list
	_ledger_port_list = port_list
	_ledger_goods_host = goods_host
	top_hs.split_offset = 260
	area_list.item_selected.connect(_on_ledger_area_item_selected)
	port_list.item_selected.connect(_on_ledger_port_item_selected)
	var have_last_area := false
	for ii in range(area_list.item_count):
		if str(area_list.get_item_metadata(ii)) == _ledger_last_area_id:
			have_last_area = true
			break
	if not have_last_area:
		var rd0: Dictionary = areas_data[0] as Dictionary
		_ledger_last_area_id = str(rd0.get("area_id", ""))
	var sel_a := 0
	for ii2 in range(area_list.item_count):
		if str(area_list.get_item_metadata(ii2)) == _ledger_last_area_id:
			sel_a = ii2
			break
	area_list.select(sel_a)
	_refresh_ledger_port_list(_ledger_last_area_id)


func _on_ledger_area_item_selected(index: int) -> void:
	if _ledger_area_list == null or not is_instance_valid(_ledger_area_list):
		return
	_ledger_last_area_id = str(_ledger_area_list.get_item_metadata(index))
	_refresh_ledger_port_list(_ledger_last_area_id)


func _on_ledger_port_item_selected(index: int) -> void:
	if _ledger_port_list == null or not is_instance_valid(_ledger_port_list):
		return
	_ledger_last_port_id = str(_ledger_port_list.get_item_metadata(index))
	_refresh_ledger_goods_panel(_ledger_last_port_id)


func _refresh_ledger_port_list(area_id: String) -> void:
	if _ledger_port_list == null or not is_instance_valid(_ledger_port_list):
		return
	_ledger_port_list.clear()
	var rows: Array = _gs.list_player_ledger_ports_for_chart_area(area_id)
	for rd in rows:
		var d: Dictionary = rd
		var pid := str(d.get("port_id", ""))
		var nm := str(d.get("name", pid))
		var line: String = "%s · %dd · %d%%" % [nm, int(d.get("age_days", 0)), int(d.get("reliability_pct", 0))]
		var idxp := _ledger_port_list.item_count
		_ledger_port_list.add_item(line)
		var tip: String = "%s — grain band %s — %s — food mood: %s" % [
			nm,
			str(d.get("grain_range", "—")),
			str(d.get("source", "")),
			str(d.get("risk_hint", "")),
		]
		_ledger_port_list.set_item_tooltip(idxp, tip)
		_ledger_port_list.set_item_metadata(idxp, pid)
	var found_port := false
	for j in range(_ledger_port_list.item_count):
		if str(_ledger_port_list.get_item_metadata(j)) == _ledger_last_port_id:
			_ledger_port_list.select(j)
			found_port = true
			_refresh_ledger_goods_panel(_ledger_last_port_id)
			break
	if not found_port and _ledger_port_list.item_count > 0:
		_ledger_last_port_id = str(_ledger_port_list.get_item_metadata(0))
		_ledger_port_list.select(0)
		_refresh_ledger_goods_panel(_ledger_last_port_id)
	elif not found_port:
		_ledger_last_port_id = ""
		_refresh_ledger_goods_panel("")


func _refresh_ledger_goods_panel(port_id: String) -> void:
	if _ledger_goods_host == null or not is_instance_valid(_ledger_goods_host):
		return
	for c in _ledger_goods_host.get_children():
		_ledger_goods_host.remove_child(c)
		c.free()
	if port_id.is_empty():
		var empty_l := Label.new()
		empty_l.text = "Select a harbor to see remembered prices."
		empty_l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		_ledger_goods_host.add_child(empty_l)
		return
	var hdr := Label.new()
	hdr.text = "%s — goods your book carries" % _gs.get_port_name(port_id)
	hdr.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	hdr.add_theme_font_size_override("font_size", 12)
	_ledger_goods_host.add_child(hdr)
	var prov := Button.new()
	prov.text = "Why this harbor line exists"
	prov.add_theme_font_size_override("font_size", 10)
	prov.tooltip_text = _gs.get_player_data_provenance("ledger", port_id)
	prov.pressed.connect(_append_log.bind(_gs.get_player_data_provenance("ledger", port_id)))
	_ledger_goods_host.add_child(prov)
	var goods_rows: Array = _gs.list_player_ledger_goods_for_port(port_id)
	if goods_rows.is_empty():
		var none_l := Label.new()
		none_l.text = "No per-good rows stored for this harbor yet."
		none_l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		_ledger_goods_host.add_child(none_l)
		return
	var grid := GridContainer.new()
	grid.columns = 8
	for h in ["Good", "Buy", "Sell", "Toll/u", "Note day", "Age", "Rel.", "Why"]:
		grid.add_child(_tbl_cell(h, 16.0))
	for gr in goods_rows:
		var d: Dictionary = gr
		var gid := str(d.get("good_id", ""))
		grid.add_child(_tbl_cell(str(d.get("name", gid)), 72.0))
		grid.add_child(_tbl_cell(str(int(d.get("buy_unit", 0))), 36.0))
		grid.add_child(_tbl_cell(str(int(d.get("sell_unit", 0))), 36.0))
		grid.add_child(_tbl_cell(str(int(d.get("toll_per_unit", 0))), 36.0))
		grid.add_child(_tbl_cell("day %d" % int(d.get("note_day", 0)), 44.0))
		grid.add_child(_tbl_cell("%dd" % int(d.get("ledger_age_days", 0)), 32.0))
		grid.add_child(_tbl_cell("%d%%" % int(d.get("reliability_pct", 0)), 32.0))
		var wl := Button.new()
		wl.text = "?"
		wl.tooltip_text = _gs.get_player_data_provenance("ledger_good", "%s|%s" % [port_id, gid])
		wl.focus_mode = Control.FOCUS_NONE
		wl.pressed.connect(_append_log.bind(_gs.get_player_data_provenance("ledger_good", "%s|%s" % [port_id, gid])))
		grid.add_child(wl)
	_ledger_goods_host.add_child(grid)


func _build_routes_panel(parent: VBoxContainer) -> void:
	if str(_gs.player_voyage_role) == "escort":
		_append_wrapped(
			parent,
			"While you hold a convoy escort commission, the master cannot plot a private voyage — finish the contract first."
		)
		return
	var rows: Array = _gs.get_player_route_table()
	if rows.is_empty():
		_append_wrapped(
			parent,
			"No open routes from this roadstead — check lanes in data/world.json or your hull’s limits."
		)
		return
	_append_wrapped(
		parent,
		"Table-first route planner — map is context only. Paying clerks (Tavern → refresh) tightens declared reliability for a tide."
	)
	var pay_refresh := Button.new()
	pay_refresh.text = "Pay clerks to refresh route tables (%dc)" % _gs.get_player_intel_verify_coin_cost("routes")
	pay_refresh.disabled = _gs.get_money() < _gs.get_player_intel_verify_coin_cost("routes")
	pay_refresh.pressed.connect(_on_pay_route_refresh_pressed)
	parent.add_child(pay_refresh)
	var chart := Control.new()
	chart.name = "CaptainsChart"
	chart.custom_minimum_size = Vector2(320, 200)
	chart.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	chart.clip_contents = true
	chart.add_child(_sea_chart_background())
	parent.add_child(chart)
	_captains_chart = chart
	chart.resized.connect(_on_captains_chart_resized)
	_captains_chart_relayout()
	var grid := GridContainer.new()
	grid.columns = 8
	for h in ["Destination", "Days", "Route", "Risk read", "Data age", "Rel.", "Sail", "Why"]:
		grid.add_child(_tbl_cell(h, 20.0))
	for row in rows:
		var d: Dictionary = row
		var pid := str(d.get("id", ""))
		grid.add_child(_tbl_cell(str(d.get("name", pid)), 96.0))
		grid.add_child(_tbl_cell(str(int(d.get("days", 0))), 28.0))
		grid.add_child(_tbl_cell(_truncate(str(d.get("route", "")), 20), 72.0))
		grid.add_child(_tbl_cell(str(d.get("risk", "")), 88.0))
		grid.add_child(_tbl_cell("%dd" % int(d.get("data_age_days", 0)), 32.0))
		grid.add_child(_tbl_cell("%d%%" % int(d.get("reliability_pct", 0)), 32.0))
		var sail := Button.new()
		sail.text = "Sail"
		sail.pressed.connect(_on_destination_chosen.bind(pid))
		grid.add_child(sail)
		var wr := Button.new()
		wr.text = "?"
		wr.tooltip_text = _gs.get_player_data_provenance("route", pid)
		wr.focus_mode = Control.FOCUS_NONE
		wr.pressed.connect(_append_log.bind(_gs.get_player_data_provenance("route", pid)))
		grid.add_child(wr)
	parent.add_child(grid)
	var any_missing_uv := false
	for row2 in rows:
		var d2: Dictionary = row2
		if _gs.get_port_map_uv(str(d2.get("id", ""))).x < 0.0:
			any_missing_uv = true
			break
	if any_missing_uv:
		_append_wrapped(parent, "Some ports lack chart pins — use the table above.")


func _on_pay_route_refresh_pressed() -> void:
	if not _gs.try_player_buy_intel("routes"):
		_append_log("Could not refresh routes (need coin ashore).")
		return
	_append_log("Clerks re-measured open-sea legs on your charts.")
	_rebuild_trade()
	_refresh_header()


func _sea_chart_background() -> Control:
	if ResourceLoader.exists(_SEA_CHART_PATH):
		var tex: Texture2D = load(_SEA_CHART_PATH) as Texture2D
		if tex != null:
			var tr := TextureRect.new()
			tr.name = "ChartSea"
			tr.mouse_filter = Control.MOUSE_FILTER_IGNORE
			tr.set_anchors_preset(Control.PRESET_FULL_RECT)
			tr.offset_right = 0.0
			tr.offset_bottom = 0.0
			tr.texture = tex
			tr.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
			tr.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
			return tr
	var cr := ColorRect.new()
	cr.name = "ChartSea"
	cr.mouse_filter = Control.MOUSE_FILTER_IGNORE
	cr.set_anchors_preset(Control.PRESET_FULL_RECT)
	cr.color = Color(0.07, 0.12, 0.2)
	return cr


func _style_port_chart_button(btn: Button) -> void:
	var normal := StyleBoxFlat.new()
	normal.bg_color = Color(0.82, 0.62, 0.28, 0.94)
	normal.border_color = Color(0.32, 0.22, 0.12, 1.0)
	normal.set_border_width_all(1)
	normal.set_corner_radius_all(15)
	normal.content_margin_left = 8.0
	normal.content_margin_right = 8.0
	normal.content_margin_top = 5.0
	normal.content_margin_bottom = 5.0
	var hover := normal.duplicate() as StyleBoxFlat
	hover.bg_color = Color(0.93, 0.74, 0.38, 0.98)
	var pressed := normal.duplicate() as StyleBoxFlat
	pressed.bg_color = Color(0.62, 0.44, 0.18, 1.0)
	btn.add_theme_stylebox_override("normal", normal)
	btn.add_theme_stylebox_override("hover", hover)
	btn.add_theme_stylebox_override("pressed", pressed)
	btn.add_theme_stylebox_override("focus", hover)
	btn.add_theme_color_override("font_color", Color(0.1, 0.06, 0.04))
	btn.add_theme_color_override("font_pressed_color", Color(0.98, 0.94, 0.88))
	btn.add_theme_color_override("font_hover_color", Color(0.06, 0.04, 0.02))
	btn.add_theme_font_size_override("font_size", 12)


func _on_captains_chart_resized() -> void:
	call_deferred("_captains_chart_relayout")


func _captains_chart_relayout() -> void:
	var chart := _captains_chart
	if chart == null or not is_instance_valid(chart):
		return
	for ch in chart.get_children():
		if str(ch.name).begins_with("PortMarker_"):
			chart.remove_child(ch)
			ch.free()
	var sz: Vector2 = chart.size
	if sz.x < 24.0 or sz.y < 24.0:
		return
	for row in _gs.get_player_route_table():
		var d: Dictionary = row
		var pid := str(d.get("id", ""))
		var uv: Vector2 = _gs.get_port_map_uv(pid)
		if uv.x < 0.0:
			continue
		var btn := Button.new()
		btn.name = "PortMarker_%s" % pid
		btn.flat = true
		btn.focus_mode = Control.FOCUS_ALL
		var pname: String = str(d.get("name", pid))
		var days: int = int(d.get("days", 0))
		var rlabel: String = str(d.get("route", ""))
		btn.text = pname if pname.length() <= 16 else pname.substr(0, 14) + "…"
		if rlabel.is_empty():
			btn.tooltip_text = "%s — %d days at sea" % [pname, days]
		else:
			btn.tooltip_text = "%s — %d days (%s)" % [pname, days, rlabel]
		btn.custom_minimum_size = Vector2(108, 30)
		_style_port_chart_button(btn)
		btn.pressed.connect(_on_destination_chosen.bind(pid))
		chart.add_child(btn)
		var half := btn.custom_minimum_size * 0.5
		btn.position = Vector2(uv.x * sz.x - half.x, uv.y * sz.y - half.y)


func _build_dock_fleet_section(parent: VBoxContainer) -> void:
	var fleet_box := VBoxContainer.new()
	fleet_box.add_theme_constant_override("separation", 6)
	var fleet_cap: int = _gs.get_player_cargo_capacity()
	var fleet_used: int = _gs.get_player_cargo_used()
	var fleet_n: int = _gs.get_player_fleet_ships()
	var labor: int = _gs.get_fleet_ship_purchase_cost()
	var nominal: int = _gs.get_fleet_new_ship_nominal_coins()
	var build_days: int = _gs.get_fleet_new_ship_build_days()
	var yard_left: int = _gs.get_player_fleet_shipyard_days_remaining()
	var fleet_lbl := Label.new()
	fleet_lbl.text = (
		"Fleet: %d/%d ships · hold %d/%d units · new hull: %dc labor + port timber/textiles/metal · ~%d days in slip (nominal hull value ~%dc; used slips often beat waiting)."
		% [fleet_n, _gs.get_player_fleet_max_ships(), fleet_used, fleet_cap, labor, build_days, nominal]
	)
	fleet_lbl.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	fleet_lbl.add_theme_font_size_override("font_size", 11)
	fleet_box.add_child(fleet_lbl)
	if yard_left > 0:
		var yd := Label.new()
		yd.text = "Shipyard order: %d day(s) until the new hull joins the convoy." % yard_left
		yd.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		fleet_box.add_child(yd)
	var fleet_btn := Button.new()
	fleet_btn.text = "Order new hull (+%dc labor · ~%d d)" % [labor, build_days]
	fleet_btn.disabled = not _gs.player_can_order_new_fleet_ship()
	fleet_btn.pressed.connect(_on_buy_fleet_ship_pressed)
	fleet_box.add_child(fleet_btn)
	var listings: Array = _gs.get_used_hull_listings_at_player_port()
	if not listings.is_empty():
		var best: int = 999999999
		for cell in listings:
			if typeof(cell) != TYPE_DICTIONARY:
				continue
			best = mini(best, int((cell as Dictionary).get("ask", 999999999)))
		var used_lbl := Label.new()
		used_lbl.text = (
			"Used hulls on the slip: %d for sale (cheapest ~%dc vs ~%dc nominal new hull)."
			% [listings.size(), best, _gs.get_fleet_new_ship_nominal_coins()]
		)
		used_lbl.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		fleet_box.add_child(used_lbl)
		var buy_used := Button.new()
		buy_used.text = "Buy used hull (cheapest listing)"
		buy_used.disabled = fleet_n >= _gs.get_player_fleet_max_ships() or _gs.get_money() < best
		buy_used.pressed.connect(_on_buy_used_hull_pressed)
		fleet_box.add_child(buy_used)
	if fleet_n > 1:
		var sell_fs := Button.new()
		sell_fs.text = "Fire-sale −1 hull (used slip; keeps ≥1 ship)"
		sell_fs.disabled = not _gs.player_can_fire_sale_fleet_ship()
		sell_fs.pressed.connect(_on_fire_sale_hull_pressed)
		fleet_box.add_child(sell_fs)
	parent.add_child(fleet_box)


func _on_convoy_escort_offer_toggled(pressed: bool) -> void:
	_gs.set_player_offers_convoy_escort(pressed)


func _on_spread_crop_rumor_pressed(scarcity_talk: bool) -> void:
	if not _gs.try_player_spread_crop_market_rumor(scarcity_talk):
		_append_log("Cannot spread crop talk (need coin and a grain market here).")
		return
	_append_log(
		"Whisper campaign on the quay — prices shift; your own read wobbles; repute dips."
		if scarcity_talk
		else "Plenty talk on the quay — softer repute hit."
	)
	_refresh_header()
	_maybe_refresh_admin_dump()


func _on_spread_war_rumor_pressed(inflame_fear: bool) -> void:
	if not _gs.try_player_spread_war_rumor(inflame_fear):
		_append_log("Cannot spread war talk (need coin and a port).")
		return
	_append_log("Dockside war-fear campaign — metal and wire feel it; your notebook wobbles.")
	_refresh_header()
	_maybe_refresh_admin_dump()


func _on_temple_offering_pressed(tier: int) -> void:
	if not _gs.try_player_temple_offering(tier):
		_append_log("Temple cannot take your vow (ashore, silver, or cap).")
		return
	_append_log("Temple offering recorded — storm relief queued for your next sailing.")
	_refresh_header()
	_maybe_refresh_admin_dump()


func _on_buy_fleet_ship_pressed() -> void:
	if _gs.try_buy_fleet_ship():
		_rebuild_trade()
		_refresh_header()
		return
	_append_log(
		"Cannot order new hull (at sea, fleet cap, slip building, or need %dc labor + materials)."
		% _gs.get_fleet_ship_purchase_cost()
	)


func _on_buy_used_hull_pressed() -> void:
	if not _gs.try_player_buy_used_fleet_ship():
		_append_log("Could not buy a used hull (coins, fleet cap, or no listing).")
		return
	_rebuild_trade()
	_refresh_header()


func _on_fire_sale_hull_pressed() -> void:
	if not _gs.try_player_fire_sale_fleet_ship():
		_append_log("Fire-sale only with 2+ ships docked in port.")
		return
	_rebuild_trade()
	_refresh_header()


func _on_buy_pressed(good_id: String, qty: int) -> void:
	if not _gs.try_buy(good_id, qty):
		return
	_rebuild_trade()
	_refresh_header()


func _on_sell_pressed(good_id: String, qty: int) -> void:
	if not _gs.try_sell(good_id, qty):
		return
	_rebuild_trade()
	_refresh_header()


func _on_customs_graft_pressed() -> void:
	if not _gs.player_try_customs_graft():
		_append_log("Graft refused (need coin and a port that levies tolls).")
		return
	_rebuild_trade()
	_refresh_header()


func _on_mint_batch_pressed() -> void:
	if not _gs.try_player_strike_mint_batch_from_cargo():
		_append_log("Cannot strike mint batch (mint port? specie in hold?).")
		return
	_rebuild_trade()
	_refresh_header()


func _deferred_rebuild_trade_and_header() -> void:
	_rebuild_trade()
	_refresh_header()


func _on_destination_chosen(to_id: String) -> void:
	if not _gs.start_voyage(to_id):
		return
	_append_log("Course set — advance days at sea.")
	_rebuild_trade()
	_refresh_header()


func _on_advance_pressed() -> void:
	_gs.advance_day()


func _on_save_pressed() -> void:
	_gs.save_campaign()


func _on_load_pressed() -> void:
	_gs.load_campaign()


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		if event.keycode == KEY_F12:
			if admin_window.visible:
				_hide_admin_window()
			else:
				_refresh_admin_dump_text()
				admin_window.popup_centered()
			get_viewport().set_input_as_handled()


func _hide_admin_window() -> void:
	admin_window.hide()


func _refresh_admin_dump_text() -> void:
	admin_dump_text.text = _gs.get_admin_world_dump()


func _maybe_refresh_admin_dump() -> void:
	if admin_window.visible:
		_refresh_admin_dump_text()

extends SceneTree

## Headless run: `Godot --headless --path . -s res://tools/sim_100_days.gd`
## Player does not sail or trade; world + NPCs + population run this many ticks.

const DAYS := 5000


func _progress_log_step(total: int) -> int:
	if total <= 200:
		return 10
	if total <= 2000:
		return 100
	return 1000


func _should_log_progress(tick_index: int, total: int) -> bool:
	if tick_index == total:
		return true
	var step: int = _progress_log_step(total)
	return tick_index % step == 0


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	var gs := HarboursGameState.new()
	root.add_child(gs)
	await process_frame
	print("=== HarboursOfPower simulation: %d daily ticks (player idle, no trades/sails) ===" % DAYS)
	print("  (progress log every %d ticks)" % _progress_log_step(DAYS))
	_print_block("baseline (before first advance_day)", gs.get_simulation_metrics())
	for d in range(DAYS):
		gs.advance_day()
		var n: int = d + 1
		if _should_log_progress(n, DAYS):
			_print_block("after advance #%d (game calendar day %d)" % [n, gs.current_day], gs.get_simulation_metrics())
	print("=== end ===")
	quit(0)


func _print_block(title: String, m: Dictionary) -> void:
	print("")
	print("-- %s --" % title)
	print(
		(
			"  player: money=%d  ship=%d/%d  port=%s  at_sea=%s  |  npc: agents=%d  at_sea=%d  total_purse=%d"
		)
		% [
			int(m.get("player_money", 0)),
			int(m.get("player_ship_condition", 100)),
			100,
			str(m.get("player_port", "")),
			str(m.get("player_at_sea", false)),
			int(m.get("npc_agent_count", 0)),
			int(m.get("npc_at_sea", 0)),
			int(m.get("npc_total_money", 0)),
		]
	)
	var ports: Variant = m.get("ports", {})
	if typeof(ports) != TYPE_DICTIONARY:
		return
	var keys: Array = (ports as Dictionary).keys()
	keys.sort_custom(func(a, b) -> bool: return str(a) < str(b))
	for pid in keys:
		var pv: Variant = (ports as Dictionary).get(pid, null)
		if typeof(pv) != TYPE_DICTIONARY:
			continue
		var p: Dictionary = pv as Dictionary
		var war_c: String = "  "
		if bool(p.get("at_war", false)):
			war_c = "W%d" % int(p.get("war_days_left", 0))
		var imo: int = int(p.get("industrial_metal_sink", 0))
		var iwo: int = int(p.get("industrial_wire_sink", 0))
		var mood: String = str(p.get("food_unrest_mood", ""))
		var pop_m: int = int(p.get("population_grain", 0))
		var pop_sc: float = float(p.get("population_output_scale", 1.0))
		var fam: int = int(p.get("famine_streak_days", 0))
		var prs: int = int(p.get("prosperity_streak_days", 0))
		print(
			(
				"  port %-10s  wealth=%4d (attract=%4d)  grain=%4d  wine=%4d  m=%3d w=%3d  spoil=%2d  "
				+ "food_days=%5.1f  unrest=%3d W%2d P%2d (%s)  pop=%d out×%.2f fam=%d pro=%d  ind_mw=%2d/%2d  npc docked=%d inbound=%d  %s"
			)
			% [
				str(pid),
				int(p.get("wealth", 0)),
				int(p.get("attractor", 0)),
				int(p.get("stock_grain", 0)),
				int(p.get("stock_wine", 0)),
				int(p.get("stock_metal", 0)),
				int(p.get("stock_wire", 0)),
				int(p.get("grain_spoiled", 0)),
				float(p.get("grain_food_days", 9999.0)),
				int(p.get("food_unrest", 0)),
				int(p.get("food_worry", 0)),
				int(p.get("food_panic", 0)),
				mood,
				pop_m,
				pop_sc,
				fam,
				prs,
				imo,
				iwo,
				int(p.get("npc_docked", 0)),
				int(p.get("npc_inbound", 0)),
				war_c,
			]
		)

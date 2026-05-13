extends SceneTree

## Headless smoke: same HarboursGameState as F5; longest listed leg, then 2-hull leg (sink allowed).
## Run: godot --headless --path . -s res://tools/playtest_short.gd

func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	var gs := HarboursGameState.new()
	root.add_child(gs)
	for _i in range(2):
		await process_frame

	var from_id: String = gs.player_port_id
	var dests: Array = gs.list_destinations()
	if dests.is_empty():
		push_error("playtest_short: no destinations")
		quit(1)
		return

	var best: Dictionary = dests[0] as Dictionary
	for d in dests:
		var row: Dictionary = d as Dictionary
		if int(row.get("days", 0)) > int(best.get("days", 0)):
			best = row

	var to_id: String = str(best.get("id", ""))
	var days_plan: int = int(best.get("days", 0))
	var route: String = str(best.get("route", ""))
	var cond0: int = gs.player_ship_condition
	var ships0: int = gs.player_fleet_ships

	if not gs.start_voyage(to_id):
		push_error("playtest_short: start_voyage failed")
		quit(1)
		return

	var adv := 0
	while gs.is_at_sea():
		gs.advance_day()
		adv += 1
		if adv > 800:
			push_error("playtest_short: voyage too long")
			quit(1)
			return

	print("=== playtest_short (headless == same GameState as editor) ===")
	print(
		(
			"  leg1 from=%s to=%s route=%s planned_days=%d advances=%d"
			% [from_id, to_id, route, days_plan, adv]
		)
	)
	print(
		(
			"  ship_condition %d -> %d | fleet %d -> %d | booked_after=%d open_after=%.3f"
			% [
				cond0,
				gs.player_ship_condition,
				ships0,
				gs.player_fleet_ships,
				gs.player_voyage_booked_days,
				gs.player_voyage_open_sea_01,
			]
		)
	)

	gs.player_fleet_ships = 2
	var cond1: int = gs.player_ship_condition
	var fleet1: int = gs.player_fleet_ships
	var dests2: Array = gs.list_destinations()
	var pick2: Dictionary = dests2[0] as Dictionary
	for d in dests2:
		var dd: Dictionary = d as Dictionary
		if str(dd.get("id", "")) != to_id and int(dd.get("days", 0)) >= int(pick2.get("days", 0)):
			pick2 = dd
	if str(pick2.get("id", "")) == to_id and dests2.size() > 1:
		pick2 = dests2[1] as Dictionary

	if not gs.start_voyage(str(pick2.get("id", ""))):
		print("  [2 hulls] skip leg2 (start_voyage failed)")
		print("=== playtest_short ok ===")
		quit(0)
		return

	adv = 0
	while gs.is_at_sea():
		gs.advance_day()
		adv += 1
		if adv > 800:
			push_error("playtest_short: leg2 too long")
			quit(1)
			return

	print(
		(
			"  leg2 to=%s (%s) advances=%d cond %d->%d fleet %d->%d"
			% [
				str(pick2.get("id", "")),
				str(pick2.get("name", "")),
				adv,
				cond1,
				gs.player_ship_condition,
				fleet1,
				gs.player_fleet_ships,
			]
		)
	)
	print("=== playtest_short ok ===")
	quit(0)

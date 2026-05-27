extends RefCounted
class_name HarboursFreeSailBumpLog

## Debug log for free-sailing shore bumps (user://free_sail_bumps.json).

const LOG_PATH := "user://free_sail_bumps.json"

static var _bumps: Array = []
static var _next_id := 1


static func reset_session() -> void:
	_bumps.clear()
	_next_id = 1
	_persist()


static func bump_count() -> int:
	return _bumps.size()


static func get_last_bump() -> Dictionary:
	if _bumps.is_empty():
		return {}
	return (_bumps[_bumps.size() - 1] as Dictionary).duplicate(true)


static func record_bump(
	at_x: float,
	at_y: float,
	blocked_x: float,
	blocked_y: float,
	heading_rad: float,
	game_day: int,
) -> int:
	var entry := {
		"id": _next_id,
		"day": game_day,
		"at": {"x": at_x, "y": at_y},
		"blocked_at": {"x": blocked_x, "y": blocked_y},
		"heading_deg": rad_to_deg(heading_rad),
		"user_bad": false,
		"marked_bad_at": "",
		"at_sample": HarboursLandMask.debug_cell(at_x, at_y),
		"blocked_sample": HarboursLandMask.debug_cell(blocked_x, blocked_y),
	}
	_next_id += 1
	_bumps.append(entry)
	_persist()
	return int(entry["id"])


static func mark_last_as_bad() -> Dictionary:
	if _bumps.is_empty():
		return {"ok": false, "message": "No bump recorded yet — hit shore first."}
	var entry: Dictionary = _bumps[_bumps.size() - 1]
	if bool(entry.get("user_bad", false)):
		return {
			"ok": true,
			"message": "Bump #%d already flagged bad." % int(entry["id"]),
			"entry": entry.duplicate(true),
		}
	entry["user_bad"] = true
	entry["marked_bad_at"] = Time.get_datetime_string_from_system(true)
	_bumps[_bumps.size() - 1] = entry
	_persist()
	return {
		"ok": true,
		"message": "Flagged bump #%d as bad (saved to %s)." % [int(entry["id"]), LOG_PATH],
		"entry": entry.duplicate(true),
	}


static func format_bump_line(entry: Dictionary) -> String:
	if entry.is_empty():
		return ""
	var at: Dictionary = entry.get("at", {})
	var blk: Dictionary = entry.get("blocked_at", {})
	var bad := " BAD" if bool(entry.get("user_bad", false)) else ""
	return (
		"Bump #%d%s day %d at (%.0f,%.0f) blocked→(%.0f,%.0f) hdg %.0f°"
		% [
			int(entry.get("id", 0)),
			bad,
			int(entry.get("day", 0)),
			float(at.get("x", 0.0)),
			float(at.get("y", 0.0)),
			float(blk.get("x", 0.0)),
			float(blk.get("y", 0.0)),
			float(entry.get("heading_deg", 0.0)),
		]
	)


static func get_log_path() -> String:
	return LOG_PATH


static func _persist() -> void:
	var payload := {
		"schema": 1,
		"updated": Time.get_datetime_string_from_system(true),
		"count": _bumps.size(),
		"bad_count": _count_bad(),
		"bumps": _bumps,
	}
	var text := JSON.stringify(payload, "\t")
	var f := FileAccess.open(LOG_PATH, FileAccess.WRITE)
	if f == null:
		push_warning("free_sail_bump_log: could not write %s" % LOG_PATH)
		return
	f.store_string(text)


static func _count_bad() -> int:
	var n := 0
	for row: Variant in _bumps:
		if bool((row as Dictionary).get("user_bad", false)):
			n += 1
	return n

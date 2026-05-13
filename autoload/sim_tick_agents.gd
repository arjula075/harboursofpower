extends RefCounted
## Modular daily-tick domains for HarboursGameState (see orchestration in `game_state.gd`).
## Order: information (decay) → city snapshots & consumption → production (farms, mines, slaves) →
## industry (peace sinks, war materiel) → NPC trade & harbour → information (rumours, war gossip) →
## merchants (counts, cartels) → unrest & demographics (incl. plague) → war (countdown, recurring).
## Keep formulas in sync with `tools/sim_100_days.py` (same constant names / values).

const COMMERCE_DOCKED_REF := 10.0
const COMMERCE_HARBOUR_COINS_REF := 120.0
const COMMERCE_UNITS_REF := 80.0
const COMMERCE_COINS_REF := 400.0
const COMMERCE_EMA_ALPHA := 0.13
## Stops the pulse collapsing to “dead quay” after quiet patches (living baseline). Sync sim_100_days.py.
const COMMERCE_PULSE_PREV_FLOOR := 0.12
const COMMERCE_WEALTH_TARGET_COEF := 0.055
const COMMERCE_WEALTH_CENTER := 0.38
const PLAGUE_TARGET_MULT := 0.93
const CARTEL_BUY_TIGHTEN := 0.055
const CARTEL_SELL_INFLATE := 0.06
const RUMOR_MULT_MIN := 0.88
const RUMOR_MULT_MAX := 1.14


static func commerce_activity_raw(
	docked_npcs: int,
	harbour_due_coins: int,
	npc_buy_units: int,
	npc_sell_units: int,
	npc_buy_coins: int,
	npc_sell_coins: int,
) -> float:
	var d: float = clampf(float(docked_npcs) / COMMERCE_DOCKED_REF, 0.0, 1.2)
	var h: float = clampf(float(harbour_due_coins) / COMMERCE_HARBOUR_COINS_REF, 0.0, 1.2)
	var u: float = clampf(float(npc_buy_units + npc_sell_units) / COMMERCE_UNITS_REF, 0.0, 1.2)
	var c: float = clampf(float(npc_buy_coins + npc_sell_coins) / COMMERCE_COINS_REF, 0.0, 1.2)
	return clampf(0.22 * d + 0.28 * h + 0.26 * u + 0.24 * c, 0.0, 1.0)


static func commerce_pulse_ema(prev: float, raw: float, alpha: float = COMMERCE_EMA_ALPHA) -> float:
	return lerpf(prev, raw, alpha)


static func wealth_target_commerce_scale(pulse: float) -> float:
	var p: float = clampf(pulse, 0.0, 1.0)
	return 1.0 + COMMERCE_WEALTH_TARGET_COEF * (p - COMMERCE_WEALTH_CENTER)


static func rumor_price_mult(war_rumor_01: float, good_id: String, extra_delta: float) -> float:
	var wr: float = clampf(war_rumor_01, 0.0, 1.0)
	var fear: float = 0.0
	match good_id:
		"grain", "metal", "wire", "wine":
			fear = wr * 0.042
		_:
			fear = wr * 0.018
	return clampf((1.0 + fear) * (1.0 + extra_delta), RUMOR_MULT_MIN, RUMOR_MULT_MAX)

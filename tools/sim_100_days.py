#!/usr/bin/env python3
"""
Offline twin of autoload/game_state.gd daily tick.

Constants _CALENDAR_YEAR_LEN, _HARVEST_* (grain/wine farms ship only in harvest window; wine annual mass preserved),
_FARM_GRAIN_MASS_MULT (farm grain-only multiplier vs nominal closure),
_PORT_ROLE_BREADBASKET / _BREADBASKET_FARM_GRAIN_WINE_MULT (breadbasket ports: ×1.15 farm grain & wine into port),
_STORM_SEASON_* / _FISH_SEASON_WINTER_MULT, summer-deferred recurring wars (_port_war_pending_burst),
_GRAIN_SPOIL_*, _NPC_PORT_* , _NPC_PURSE_RESERVE, _NPC_MASTER_*, _NPC_SEASON_MASTERY_*, _NPC_RISK_AVERSE_MAX_LOT, _NPC_DOCK_DUST_*,
_FOOD_UNREST_* (incl. _FOOD_UNREST_DECAY_WHEN_TIGHT, tight-runway drip), _FOOD_RIOT_*,
_FOOD_RIOT_NEAR_MISS_VENT, _FOOD_RIOT_NO_FAMINE_VENT, _FOOD_RIOT_ELIGIBLE_RUNWAY_MAX,
_FOOD_UNREST_WAR_RATION_GAP_PER,
_COMMERCE_POOR_PULSE, _COMMERCE_* (pulse EMA, wealth attractor scale), _PLAGUE_TARGET_MULT,
_CARTEL_BUY_TIGHTEN, _CARTEL_SELL_INFLATE, _RUMOR_MULT_* (war gossip + per-good deltas on player prices),
_FOOD_UNREST_TIGHT_RUNWAY_DAYS, _FOOD_UNREST_TIGHT_RUNWAY_DRIP, _WAR_RIOT_GRACE_EXTRA,
_WAR_RIOT_PANIC_RAMP_DAYS,
_RESERVE_* (smooth curves, player vs NPC caps, incl. metal-from-food), _LUXURY_* / _LUXURY_IMPORT_* / _FAR_TRADE_*,
_SLAVE_* (labor demand incl. farm fish, attrition, war captives onto market),
_MARKET_* (demand/supply price pressure), _TRADE_PRICE_BIAS_CLAMP, _WINE_FARM_HELP_*, _WAR_* (materiel, _WAR_CYCLE_PEACE_*, burst 50–85),
_INDUSTRIAL_SINK_*, _POP_* (population v1; _POP_PROSPERITY_POOR_UNREST_EXCEEDS), _SHIP_* (crew wine from hold; no grain running draw), _FLEET_* (player convoy cargo + upkeep), _USED_HULL_* (used slip market),
_CROP_INFO_* / _CROP_RUMOR_* (Phase 3–4: inbound crop reports + Sicilian rumor delta on market stress; GT unchanged),
_WAR_PEACE_* (post-war food calm),
_CAPTAIN_TRADE_FEE_* (dock trade coin friction), _HARBOUR_DUE_* / _HARBOUR_BUSY_* / _HARBOUR_WEALTH_PER_COINS_PAID (harbour dues → port prosperity, busier quay bonus),
_NPC_DEPART_STAY_GATE, _MERCHANT_HOME_COUNT_STEP_MAX, _COMMERCE_PULSE_PREV_FLOOR, world.json autonomy_warmup_days (Sim.load / GameState deferred warmup), optional root `npc_city_grain_contracts_enabled` (Phase 0 NPC civic grain contracts),
optional `npc_lanes` sparse directed graph: when present, NPC merchant / convoy `_voyage_plan` uses coastal shortest paths on that graph; player voyages still use full `lanes` mesh.
_NPC_TRAIT_* (Big Five–style fields + depart/memory/lot/dust/agree wholesale hooks),
_NPC convoy Phase 2–4 + Phase 5 player-at-sea pirate checks (merchant role; twin counters) must match game_state.gd.
_SCATTERED_IDS_DECAY_DAILY_P / _NPC_CONTACT_BIAS_DOCKED_DECAY_MULT (convoy tail + docked contact-bias decay).
Marines: `goods.json` buy/sell = kit; optional `wage_per_unit_per_day` + `_MARINE_WAGE_PER_UNIT_PER_DAY_DEFAULT` docked wage bill with officer pay_scale.
Uses Python's random.Random; Godot uses RandomNumberGenerator — trends match,
exact numbers will not match a Godot run unless RNG is ported.

Run from repo root:
  python3 tools/sim_100_days.py              # default 10_000 ticks (sparse progress logs)
  python3 tools/sim_100_days.py 200          # shorter run, denser logs
  python3 tools/sim_100_days.py 5000 --no-graphs   # skip time-series + matplotlib

After each run, tools/sim_analysis/ gets one `{port}_port.png` per port: wealth vs stock-implied attractor
(war shading + food-riot markers); population grain mouths/cap with fish stock (twin axis) when fish exists;
timber & textiles port stocks; daily industrial sinks (metal / wire / timber / textiles).

Per port, per day: NPC dock wholesale only — `commerce_npc_buy_*` (goods/coins merchants took from port stock),
`commerce_npc_sell_*` (goods/coins merchants delivered to port). Optional per-port `tolls` in world.json: import duty
coins per unit on **sales into** that port only; NPC smuggle / graft; wholesale relief when any duty is levied.
Full run: `sim.commerce_daily_log` (list of
`{ "day", "ports" }`); same keys in `metrics()` / `timeseries_snapshot()` for the last completed daily tick.
Install matplotlib in a venv, e.g.:
  python3 -m venv .venv && . .venv/bin/activate && pip install -r tools/requirements-sim.txt
"""

from __future__ import annotations

import json
import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORLD_PATH = ROOT / "data" / "world.json"
GOODS_PATH = ROOT / "data" / "goods.json"
SHIPS_PATH = ROOT / "data" / "ships.json"

_WEALTH_LERP = 0.14
_DEFAULT_STOCK_PER_GOOD = 50
_DEFAULT_STOCK_SLAVES = 36
_SLAVE_DEM_FARM_GRAIN = 3
_SLAVE_DEM_FARM_WINE = 5
_SLAVE_DEM_FARM_FISH = 4
_SLAVE_DEM_MINE_METAL = 11
_SLAVE_DEM_MINE_WIRE = 9
_SLAVE_DEM_MINE_GOLD = 6
_SLAVE_DEM_MINE_SILVER = 5
_SLAVE_OUTPUT_FLOOR = 0.22
_SLAVE_ATTRITION_FRAC = 0.0028
_SLAVE_ATTRITION_OVERWORK_MUL = 0.11
_SLAVE_WAR_CAPTIVES_BASE = 22
_SLAVE_WAR_CAPTIVES_JITTER = 7
_SLAVE_WAR_CAPTIVES_PER_CAMPAIGN_DAY = 5
_SLAVE_WAR_CAPTIVES_DAY_DEN = 10
_NPC_RISK_AVERSE_MAX_LOT = 5
_NPC_START_MONEY_MIN = 78
_NPC_START_MONEY_MAX = 295
_WORLD_TREASURY_MAX = 9999999
_WORLD_TREASURY_FALLBACK = 9200
_MINT_STRIKE_WEALTH_FRAC = 0.05
_MINT_STRIKE_WEALTH_BONUS_MAX = 8
_LUXURY_IMPORT_COST_FRAC_DEFAULT = 0.38
_LUXURY_IMPORT_TREASURY_TAKE_FRAC_DEFAULT = 0.40
_LUXURY_IMPORT_SINK_CAP = 420
_GRAIN_SPOIL_FRACTION = 0.017
_GRAIN_SPOIL_CAP = 38
_GRAIN_SPOIL_MIN_STOCK = 14
_NPC_PORT_BUY_MULT = 0.765
_NPC_PORT_SELL_MULT = 1.505
_TOLL_MERCHANT_BUY_RELIEF = 0.048
_TOLL_MERCHANT_SELL_RELIEF = 0.078
_TOLL_NPC_BRIBE_DAILY_CHANCE = 0.055
_TOLL_BRIBE_DAYS_MIN = 5
_TOLL_BRIBE_DAYS_MAX = 14
_NPC_PURSE_RESERVE = 11
_NPC_MASTER_MIN = 0.74
_NPC_MASTER_MAX = 1.24
_NPC_BUST_EMPTY_STREAK_DAYS = 9
_NPC_SEASON_MASTERY_DAYS = 75
_NPC_SEASON_MASTERY_BUMP = 0.005
_NPC_DOCK_DUST_PURSE = 28
_NPC_DOCK_DUST_MAX_UNITS = 8
_NPC_TRAIT_OPEN = "trait_openness"
_NPC_TRAIT_CONSC = "trait_conscientiousness"
_NPC_TRAIT_EXTRA = "trait_extraversion"
_NPC_TRAIT_AGREE = "trait_agreeableness"
_NPC_TRAIT_NEURO = "trait_neuroticism"
_FOOD_UNREST_DECAY = 16
_FOOD_UNREST_DECAY_WHEN_TIGHT = 3
_FOOD_UNREST_SHORTAGE = 9
_FOOD_UNREST_PER_MISS = 2
_FOOD_UNREST_PANIC_LT1DAY = 11
_FOOD_UNREST_CRITICAL_DAYS = 8
_FOOD_RIOT_THRESHOLD = 190
_FOOD_RIOT_ELIGIBLE_RUNWAY_MAX = 0.30
_FOOD_RIOT_ROLL_BASE = 0.0009
_FOOD_RIOT_ROLL_PER_OVER = 750.0
_FOOD_RIOT_NO_FAMINE_VENT = 22
_FOOD_RIOT_UNREST_SCALE = 0.26
_WAR_RIOT_GRACE_EXTRA = 25
_WAR_RIOT_PANIC_RAMP_DAYS = 21
_WAR_PEACE_FOOD_UNREST_VENT = 34
_WAR_PEACE_RIOT_GRACE_DAYS = 16
_WAR_PEACE_RIOT_THRESHOLD_BONUS = 34
_FOOD_RIOT_NEAR_MISS_VENT = 12
_FOOD_UNREST_TIGHT_RUNWAY_DAYS = 5.0
_FOOD_UNREST_TIGHT_RUNWAY_DRIP = 2
_FOOD_UNREST_WAR_RATION_GAP_PER = 1
_RESERVE_REF_GRAIN_DAYS = 2.25
_RESERVE_REF_WINE_DAYS = 1.85
_RESERVE_CURVE_K_PLAYER = 2.35
_RESERVE_CURVE_K_NPC = 1.05
_RESERVE_CURVE_CAP_GRAIN_BUY_PLAYER = 0.30
_RESERVE_CURVE_CAP_GRAIN_BUY_NPC = 0.175
_RESERVE_CURVE_CAP_GRAIN_SELL_PLAYER = 0.34
_RESERVE_CURVE_CAP_GRAIN_SELL_NPC = 0.195
_RESERVE_CURVE_CAP_WINE_PLAYER = 0.28
_RESERVE_CURVE_CAP_WINE_NPC = 0.16
_RESERVE_STRESS_CAP = 0.38
_RESERVE_UNREST_PER_POINT = 0.00095
_RESERVE_COMFORT_GRAIN_TIGHT = 0.07
_RESERVE_METAL_FROM_FOOD_STRESS = 0.68
_LUXURY_WEALTH_EXCESS_COEF = 0.11
_LUXURY_SPREAD_MAX = 0.34
_FAR_TRADE_LANE_REF_DAYS = 2.75
_FAR_TRADE_LANE_COEF = 0.14
_FAR_TRADE_SPREAD_MAX = 0.24
_LUXURY_FAR_COMBINED_MAX = 0.48
_WAR_METAL_DEMAND_STRESS = 0.24
_WAR_METAL_RESERVE_CAP = 0.52
_WAR_FARM_OUTPUT_MULT = 0.72
_WAR_GRAIN_RATION_MULT = 1.22
_WAR_DEFAULT_DAYS = 75
_WAR_CYCLE_PEACE_MIN = 200
_WAR_CYCLE_PEACE_MAX = 480
_WAR_RECURRING_BURST_MIN = 50
_WAR_RECURRING_BURST_MAX = 85
_WAR_MATERIEL_METAL_BASE = 8
_WAR_MATERIEL_METAL_LINEAR = 4
_WAR_MATERIEL_METAL_MAX = 58
_WAR_MATERIEL_METAL_STOCK_SKIM_DIV = 120
_WAR_MATERIEL_METAL_STOCK_SKIM_MAX = 42
_WAR_MATERIEL_WIRE_BASE = 6
_WAR_MATERIEL_WIRE_LINEAR_DIV = 2
_WAR_MATERIEL_WIRE_MAX = 48
_WAR_MATERIEL_WIRE_STOCK_SKIM_DIV = 140
_WAR_MATERIEL_WIRE_STOCK_SKIM_MAX = 36
_WAR_MATERIEL_DAILY_HARD_CAP = 140
_INDUSTRIAL_SINK_METAL_MAX = 48
_INDUSTRIAL_SINK_WIRE_MAX = 36
_INDUSTRIAL_SINK_TIMBER_MAX = 24
_INDUSTRIAL_SINK_TEXTILES_MAX = 20
_MARKET_HORIZON_DAYS = 7.0
_MARKET_STOCK_PRESSURE_WEIGHT = 0.26
_MARKET_FLOW_PRESSURE_WEIGHT = 0.16
_MARKET_PRESSURE_ABS_MAX = 0.52
_MARKET_PRICE_MULT_MIN = 0.74
_MARKET_PRICE_MULT_MAX = 1.42
_TRADE_PRICE_BIAS_CLAMP = 0.42
_WINE_FARM_HELP_EMPTY = 4
_WINE_FARM_HELP_LOW = 2
_WINE_FARM_HELP_PORT_DAILY_CAP = 10
## Population v1 (famine/prosperity streaks, farm/mine output scale). Keep in sync with game_state.gd.
_POP_GRAIN_FLOOR = 4
_POP_GRAIN_CEILING_BOOST = 22
_POP_FAMINE_STREAK_TO_LOSS = 24
_POP_FAMINE_STREAK_RESET = 8
_POP_FAMINE_HARSH_CONSEC_ZERO_GRAIN_DAYS = 9
_POP_FAMINE_CALM_CONSEC_FULL_RATION_DAYS = 2
_POP_FAMINE_HARSH_UNREST_MIN = 118
_POP_PROSPERITY_STREAK_TO_GAIN = 30
_POP_PROSPERITY_STREAK_RESET = 14
_POP_PROSPERITY_POOR_UNREST_EXCEEDS = 118
_POP_PROSPERITY_POOR_DECAY = 4
## Iron-age rural→urban migration pull (see comment in game_state.gd). Keep in sync.
_POP_MIGRATION_PULL = 4
_POP_OUTPUT_SCALE_MIN = 0.72
_POP_OUTPUT_SCALE_MAX = 1.28
## Civic grain rationing (resilience helper A). Keep in sync with game_state.gd.
_RATION_TRIGGER_FOOD_DAYS = 5.0
_RATION_END_FOOD_DAYS = 11.0
_RATION_BITE_FRAC = 0.62
_RATION_BITE_MIN = 2
_RATION_UNREST_TICK = 2
_RATION_MAX_DAYS = 75
## Summer foraging (resilience helper B). Keep in sync with game_state.gd.
_FORAGE_SUMMER_START_DOY = 100
_FORAGE_SUMMER_END_DOY = 235
_FORAGE_SUMMER_PEAK_MOUTHS = 4.0
## Preserved-foods reserve (resilience helper D). Keep in sync with game_state.gd.
_PRESERVED_FOOD_CAP_MULT = 8
_PRESERVED_FOOD_CAP_MIN = 24
_PRESERVED_FOOD_FILL_FOODDAYS_MIN = 45.0
_PRESERVED_FOOD_FILL_PER_DAY = 0.4
_PRESERVED_FOOD_INITIAL_FRAC = 0.5
_POP_BASELINE_RISE_FRAC = 0.88
_POP_BASELINE_RISE_DAYS = 110
_POP_BASELINE_FALL_FRAC = 0.58
_POP_BASELINE_FALL_DAYS = 100
_POP_EXISTENTIAL_WAR_BURST_OFF = 999
## Trireme crew + maintenance (player idle twin). Keep in sync with game_state.gd.
_SHIP_CREW_WINE_EVERY_N_DAYS = 7
_SHIP_OFFICER_PAY_DAILY = 1
_MARINE_WAGE_PER_UNIT_PER_DAY_DEFAULT = 0.38
_MARINE_WAGE_RATE_MAX = 9.0
_SHIP_OFFICER_UNDERPAY_CONDITION_PENALTY = 0
_SHIP_WEAR_AT_SEA = 0
_SHIP_CONDITION_MIN = 15
_SHIP_CONDITION_MAX = 100
_SHIP_RATION_MISS_GRAIN_PENALTY = 0
_SHIP_RATION_MISS_WINE_PENALTY = 0
_SHIP_REPAIR_MATERIALS_GAIN = 8
_SHIP_REPAIR_COIN_COST = 2
_SHIP_REPAIR_COIN_GAIN = 4
_SHIP_REPAIR_COIN_MAX_CONDITION = 93
_FLEET_CARGO_PER_SHIP = 24
_FLEET_SHIP_NOMINAL_COINS = 240
_FLEET_NEW_SHIP_LABOR_COINS = 72
_FLEET_NEW_SHIP_TIMBER = 45
_FLEET_NEW_SHIP_TEXTILES = 32
_FLEET_NEW_SHIP_METAL = 24
_FLEET_NEW_SHIP_BUILD_DAYS = 90
_FLEET_MAX_SHIPS = 12
_FLEET_REPAIR_COIN_PER_EXTRA_SHIP = 1
## Coin destroyed on dock trades (porters, measures, petty dues). Keep in sync with game_state.gd.
_CAPTAIN_TRADE_FEE_BUY_DIV = 32
_CAPTAIN_TRADE_FEE_SELL_DIV = 40
## Daily harbour dues when berthed → port prosperity (+ busy-quay bonus). Keep in sync with game_state.gd.
_HARBOUR_DUE_BASE = 1
_HARBOUR_DUE_PER_SHIP = 1
_HARBOUR_DUE_PURSE_THRESHOLD = 350
_HARBOUR_DUE_PURSE_DIV = 22
_HARBOUR_DUE_PROGRESSIVE_CAP = 72
_HARBOUR_BUSY_PER_DOCK_PCT = 3
_HARBOUR_BUSY_MAX_BONUS_PCT = 36
_HARBOUR_WEALTH_PER_COINS_PAID = 8
_USED_HULL_MIN_PAYOUT = 22
_USED_HULL_PAYOUT_FRAC_LOW = 0.28
_USED_HULL_PAYOUT_FRAC_HIGH = 0.50
_USED_HULL_ASK_MARKUP = 1.12
_USED_HULL_MAX_PER_PORT = 10
_ROOKIE_BANKRUPTCY_USED_HULL_CHANCE = 0.46
_ROOKIE_USED_HULL_CHARTER_WEALTH_DIV = 14
_NPC_PEER_LOAN_MAX_DEBTS = 2
_NPC_PEER_LOAN_MIN_PRINCIPAL = 30
_NPC_PEER_LOAN_MAX_PRINCIPAL = 130
_NPC_PEER_LOAN_OFFER_ROLL = 0.16
_NPC_PEER_LOAN_DEBTOR_PURSE_MAX = 34
_NPC_PEER_LOAN_CREDITOR_PURSE_MIN = 118
_NPC_PEER_LOAN_CREDITOR_RESERVE = 22
_NPC_PEER_LOAN_HOME_AVOID_PER_COIN = 0.018
_NPC_PEER_LOAN_FLEE_GATE_SUB_MAX = 0.22
_VOYAGE_BOLD_DAY_MULT = 0.70
_VOYAGE_COASTAL_OPENNESS = 0.07
_VOYAGE_DISCONNECTED_BASE_DAYS = 15
## 360-day calendar; farms ship grain/wine only in harvest window. Sync game_state.gd.
_CALENDAR_YEAR_LEN = 360
_HARVEST_START_DOY = 181
_HARVEST_END_DOY = 240
_HARVEST_DAYS = _HARVEST_END_DOY - _HARVEST_START_DOY + 1
_CROP_OFFSEASON_SCALE = 0.10
_CROP_HARVEST_DAILY_SCALE = (
    float(_CALENDAR_YEAR_LEN) - float(_CALENDAR_YEAR_LEN - _HARVEST_DAYS) * _CROP_OFFSEASON_SCALE
) / float(_HARVEST_DAYS)
_SEASON_SUMMER_START_DOY = 91
_SEASON_SUMMER_END_DOY = 180
_SEASON_WINTER_START_DOY = 271
_STORM_SEASON_WINTER_MULT = 1.24
_STORM_SEASON_AUTUMN_MULT = 1.08
_FISH_SEASON_WINTER_MULT = 0.96
_PORT_ROLE_BREADBASKET = "breadbasket"
_BREADBASKET_FARM_GRAIN_WINE_MULT = 1.15
_FARM_GRAIN_MASS_MULT = 1.58
_CROP_MOISTURE_ADJUST_RATE = 0.055
_CROP_GROWTH_LAG_RATE = 0.11
_CROP_GRAIN_YIELD_MULT_MIN = 0.88
_CROP_GRAIN_YIELD_MULT_MAX = 1.06
_CROP_STRESS_PRICE_BUY_THRESHOLD = 0.52
_CROP_STRESS_PRICE_BUY_EXTRA = 0.12
_CROP_STRESS_PRICE_SELL_THRESHOLD = 0.48
_CROP_STRESS_PRICE_SELL_DISC = 0.055
## Phase 2 crop ladder (twin game_state.gd). Major tier: war + drought moisture + isolated from neighbor grain.
_CROP_PHASE2_DROUGHT_MOISTURE_MAX = 0.34
_CROP_PHASE2_NEIGHBOR_GRAIN_ISOLATED_MAX = 48
_CROP_PHASE2_BIAS_STRESS_LO = 0.38
_CROP_PHASE2_BIAS_STRESS_HI = 0.58
_CROP_PHASE2_BIAS_MAX_ADD = 0.20
_CROP_PHASE2_BIAS_MAJOR_EXTRA = 0.08
_CROP_PHASE2_BIAS_MAJOR_STRESS_MIN = 0.46
_CROP_PHASE2_UNREST_STRESS_MID = 0.48
_CROP_PHASE2_UNREST_STRESS_HIGH = 0.62
_CROP_PHASE2_UNREST_MAJOR_STRESS_MIN = 0.54
_CROP_PHASE2_UNREST_ADD_MID = 1
_CROP_PHASE2_UNREST_ADD_HIGH = 2
_CROP_PHASE2_UNREST_ADD_MAJOR = 1
_CROP_PHASE2_UNREST_DAILY_CAP = 4
_CROP_PHASE2_HOARD_STRESS_LO = 0.36
_CROP_PHASE2_HOARD_MAJOR_BOOST = 0.26
_CROP_PHASE2_NPC_GRAIN_SELL_FLOOR_SHIFT = 0.15
_CROP_PHASE2_NPC_GRAIN_BUY_CEIL_SHIFT = 0.13
_CROP_PHASE2_NPC_GRAIN_P_BUY_SHIFT = 0.22
## Phase 3 crop information (twin game_state.gd).
_CROP_INFO_LOCAL_NOISE_MAX = 0.048
_CROP_INFO_REPORT_NOISE_MAX = 0.095
_CROP_INFO_MARKET_REPORT_MAX = 8
_CROP_INFO_MARKET_LOCAL_WEIGHT = 0.52
## Phase 4 crop rumors (twin game_state.gd): public market stress delta; GT unchanged.
_CROP_RUMOR_DELTA_ABS_MAX = 0.26
_CROP_RUMOR_DAILY_DECAY = 0.987
_CROP_RUMOR_HARVEST_EXTRA_DECAY = 0.93
_CROP_RUMOR_SICILY_EVENT_DAILY_P = 0.0024
_CROP_RUMOR_SICILY_BUMPER_MAG_MIN = 0.072
_CROP_RUMOR_SICILY_BUMPER_MAG_MAX = 0.14
_CROP_RUMOR_SICILY_FAIL_MAG_MIN = 0.055
_CROP_RUMOR_SICILY_FAIL_MAG_MAX = 0.12
_CROP_RUMOR_GT_CORREL = 0.028
_CROP_RUMOR_HIGH_TRUST_DAMP_P = 0.055
_CROP_RUMOR_HIGH_TRUST_DAMP_MULT = 0.68
_SICILY_CROP_RUMOR_LISTENER_PORT_IDS = (
    "ostia",
    "neapolis",
    "rhegium",
    "carthage",
    "hippo",
    "tingis",
    "messana",
    "panormus",
)
_VOYAGE_STORM_BASE_P = 0.0036
_VOYAGE_STORM_PER_BOOKED_DAY = 0.00175
_VOYAGE_STORM_OPEN_MULT = 0.05
_VOYAGE_STORM_P_CAP = 0.195
_VOYAGE_STORM_COND_DAMAGE_MIN = 5
_VOYAGE_STORM_COND_DAMAGE_MAX = 15
_VOYAGE_STORM_HULL_LOSS_CHANCE = 0.12
_SHIP_AGE_STORM_DAMAGE_SCALE = 0.42
_SHIP_AGE_LEAK_DAILY_P = 0.011
_RNG_SEED = 2026
## Phase 1 convoy/piracy scaffold (roles + escort contract). Sync game_state.gd.
_VOYAGE_ROLE_MERCHANT = "merchant"
_VOYAGE_ROLE_ESCORT = "escort"
_VOYAGE_ROLE_PIRATE = "pirate"
_PIRATE_MAX_ACTIVE = 6
_PIRATE_SPAWN_PURSE_MAX = 96
_PIRATE_SPAWN_ROLL_BASE = 0.048
_PIRATE_DEPART_STAY_GATE = 0.38
_ENCOUNTER_BASE_P = 0.058
_PIRATE_FLEE_POWER_RATIO = 1.36
_PIRATE_RAIDER_HULL_ID = "illyrian_raider"
_PIRATE_NOTORIETY_CAP = 800.0
_PLAYER_PIRATE_CATCH_BASE_P = 0.052
## Phase 2 NPC merchant convoys (shared voyage). Sync game_state.gd.
_CONVOY_MAX_MERCHANTS = 4
_NPC_CITY_GRAIN_CONTRACT_OFFER_P = 0.034
_NPC_CITY_GRAIN_CONTRACT_QTY_MIN = 5
_NPC_CITY_GRAIN_CONTRACT_QTY_MAX = 22
_NPC_CITY_GRAIN_CONTRACT_DUE_MIN = 16
_NPC_CITY_GRAIN_CONTRACT_DUE_MAX = 52
_NPC_CITY_TRUST_PORT_MAX_KEYS = 8
_NPC_CITY_CONTRACT_TREASURY_FRAC = 0.08
_SCATTERED_IDS_DECAY_DAILY_P = 0.07
_NPC_CONTACT_BIAS_DOCKED_DECAY_MULT = 0.93
_ESCORT_PAY_BASE = 16
_ESCORT_PAY_PER_DAY = 5
_ESCORT_PAY_OPEN_MUL = 42
_ESCORT_PAY_MIN = 12
_ESCORT_PAY_MAX = 320
_ESCORT_HULL_FAST_VOYAGE_MULT = 0.94
## Sim tick agents (commerce / rumours / cartels / plague). Keep in sync with autoload/sim_tick_agents.gd + game_state.gd.
_COMMERCE_POOR_PULSE = 0.10
_COMMERCE_DOCKED_REF = 10.0
_COMMERCE_HARBOUR_COINS_REF = 120.0
_COMMERCE_UNITS_REF = 80.0
_COMMERCE_COINS_REF = 400.0
_COMMERCE_EMA_ALPHA = 0.13
_COMMERCE_WEALTH_TARGET_COEF = 0.055
_COMMERCE_WEALTH_CENTER = 0.38
_COMMERCE_PULSE_PREV_FLOOR = 0.12
_PLAGUE_TARGET_MULT = 0.93
_CARTEL_BUY_TIGHTEN = 0.055
_CARTEL_SELL_INFLATE = 0.06
_RUMOR_MULT_MIN = 0.88
_RUMOR_MULT_MAX = 1.14
_NPC_DEPART_STAY_GATE = 0.45
_MERCHANT_HOME_COUNT_STEP_MAX = 6
## Parse / sanity ceiling for world.json `npc_traders` (not a gameplay balance cap).
_PORT_NPC_TRADERS_LOAD_MAX = 999
## Bankruptcy rookie: only respawn if the home harbour still has wholesale activity, pulse life, or enough stock to haul.
_NPC_BANKRUPTCY_REPLACE_MIN_PULSE = 0.20
_NPC_BANKRUPTCY_REPLACE_MIN_PORT_STOCK_UNITS = 36

_MAX_PURSE_COINS_PY: int = 999999
_MAX_DAY_COUNTER_PY: int = 999999


def clampi(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, int(v)))


def _captain_trade_fee_on_buy(cost: int) -> int:
    if cost <= 0:
        return 0
    return max(1, int(cost) // _CAPTAIN_TRADE_FEE_BUY_DIV)


def _captain_trade_fee_on_sell(revenue: int) -> int:
    if revenue <= 0:
        return 0
    return max(1, int(revenue) // _CAPTAIN_TRADE_FEE_SELL_DIV)


def _harbour_due_for_captain(purse: int, ships: int) -> int:
    p = clampi(int(purse), 0, _MAX_PURSE_COINS_PY)
    sh = clampi(int(ships), 1, _FLEET_MAX_SHIPS)
    base_d = _HARBOUR_DUE_BASE + sh * _HARBOUR_DUE_PER_SHIP
    thr = _HARBOUR_DUE_PURSE_THRESHOLD
    divv = max(1, _HARBOUR_DUE_PURSE_DIV)
    capg = _HARBOUR_DUE_PROGRESSIVE_CAP
    prog = max(0, (p - thr) // divv)
    return max(0, base_d + min(capg, prog))


def _take_harbour_due_from_purse(purse: int, ships: int) -> int:
    due = _harbour_due_for_captain(purse, ships)
    return min(due, clampi(int(purse), 0, _MAX_PURSE_COINS_PY))


def clampf(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(v)))


def _commerce_activity_raw_py(
    docked: int,
    harbour_coins: int,
    npc_buy_units: int,
    npc_sell_units: int,
    npc_buy_coins: int,
    npc_sell_coins: int,
) -> float:
    d = clampf(float(docked) / _COMMERCE_DOCKED_REF, 0.0, 1.2)
    h = clampf(float(harbour_coins) / _COMMERCE_HARBOUR_COINS_REF, 0.0, 1.2)
    u = clampf(float(npc_buy_units + npc_sell_units) / _COMMERCE_UNITS_REF, 0.0, 1.2)
    c = clampf(float(npc_buy_coins + npc_sell_coins) / _COMMERCE_COINS_REF, 0.0, 1.2)
    return clampf(0.22 * d + 0.28 * h + 0.26 * u + 0.24 * c, 0.0, 1.0)


def _commerce_pulse_ema_py(prev: float, raw: float, alpha: float = _COMMERCE_EMA_ALPHA) -> float:
    return prev + (raw - prev) * alpha


def _wealth_target_commerce_scale_py(pulse: float) -> float:
    p = clampf(pulse, 0.0, 1.0)
    return 1.0 + _COMMERCE_WEALTH_TARGET_COEF * (p - _COMMERCE_WEALTH_CENTER)


def _rumor_price_mult_py(war_rumor_01: float, good_id: str, extra_delta: float) -> float:
    wr = clampf(war_rumor_01, 0.0, 1.0)
    if good_id in ("grain", "metal", "wire", "wine"):
        fear = wr * 0.042
    else:
        fear = wr * 0.018
    return clampf((1.0 + fear) * (1.0 + extra_delta), _RUMOR_MULT_MIN, _RUMOR_MULT_MAX)


_INT31 = 2147483647


def _npc_str_mix_py(s: str, salt: int) -> int:
    h = salt & 0x7FFFFFFF
    for ch in s:
        h = abs(h * 131 + ord(ch)) % _INT31
    return h


def _crop_seasonal_moisture_target_01_py(doy: int, port_id: str) -> float:
    phase = float(_npc_str_mix_py(port_id, 4001) % 1000) / 1000.0
    y = float(_CALENDAR_YEAR_LEN)
    ang = math.tau * (float(doy) + 60.0 - phase * 12.0) / y
    wet = 0.5 + 0.5 * math.cos(ang)
    lo, hi = 0.28, 0.80
    base = lo + (hi - lo) * wet
    return clampf(base + (phase - 0.5) * 0.10, 0.0, 1.0)


def _npc_regional_buy_factor_py(port_id: str, good_id: str) -> float:
    h = (_npc_str_mix_py(port_id, 17) ^ _npc_str_mix_py(good_id, 31)) & 0x7FFFFFFF
    h = abs(h * 1103515245 + 12345) % _INT31
    t = (h % 1000) / 1000.0
    return 0.74 + (1.10 - 0.74) * t


def _npc_regional_sell_factor_py(port_id: str, good_id: str) -> float:
    h = (_npc_str_mix_py(port_id, 7919) * 65537 + _npc_str_mix_py(good_id, 97)) % _INT31
    h = abs(h + 97) % _INT31
    t = (h % 1000) / 1000.0
    return 0.90 + (1.28 - 0.90) * t


def lane_key(a: str, b: str) -> str:
    return f"{a}|{b}"


class Sim:
    def __init__(self, rng: random.Random) -> None:
        self.rng = rng
        self.current_day = 1
        self.port_order: list[str] = []
        self.port_names: dict[str, str] = {}
        self.port_stocks: dict[str, dict[str, int]] = {}
        self.port_initial_stock: dict[str, dict[str, int]] = {}
        self.port_npc_trader_count: dict[str, int] = {}
        self.port_population_grain: dict[str, int] = {}
        self.port_population_wine_base: dict[str, int] = {}
        self.port_population_fish_per_day: dict[str, int] = {}
        self.port_population_grain_baseline: dict[str, int] = {}
        self.port_population_grain_cap: dict[str, int] = {}
        self.port_famine_streak_days: dict[str, int] = {}
        self.port_consecutive_grain_full_ration_days: dict[str, int] = {}
        self.port_consecutive_grain_zero_eat_days: dict[str, int] = {}
        self.port_prosperity_streak_days: dict[str, int] = {}
        self.port_rationing_active: dict[str, bool] = {}
        self.port_rationing_days_active: dict[str, int] = {}
        self.port_preserved_food: dict[str, float] = {}
        self.port_initial_wealth: dict[str, int] = {}
        self.port_role_wealth_bonus: dict[str, int] = {}
        self.port_roles: dict[str, str] = {}
        self.port_existential_war_burst_days: dict[str, int] = {}
        self.port_baseline_momentum_up: dict[str, int] = {}
        self.port_baseline_momentum_dn: dict[str, int] = {}
        self.port_wealth: dict[str, int] = {}
        self.farms: list[dict] = []
        self.mines: list[dict] = []
        self.port_mint_cfg: dict[str, dict] = {}
        self.world_treasury_coins: int = 0
        self.world_initial_treasury: int = 0
        self.lane_days: dict[str, int] = {}
        self.npc_lane_days: dict[str, int] = {}
        self.port_neighbors: dict[str, list[str]] = {}
        self.port_neighbors_npc: dict[str, list[str]] = {}
        self._voyage_coastal_shortest_cache: dict[str, int] = {}
        self._voyage_coastal_shortest_cache_npc: dict[str, int] = {}
        self.goods: dict[str, dict] = {}
        self.npc_agents: list[dict] = []
        self.npc_next_id = 0
        self._last_grain_spoilage: dict[str, int] = {}
        self.bankruptcy_events: int = 0
        self.convoy_formations: int = 0
        self.escort_coins_paid: int = 0
        self.pirate_encounter_attempts: int = 0
        self.pirate_raids_success: int = 0
        self.pirate_escort_flees: int = 0
        self.pirate_marines_lost: int = 0
        self.pirate_loot_coins: int = 0
        self.player_pirate_encounter_rolls: int = 0
        self.player_pirate_repelled: int = 0
        self.player_pirate_hits: int = 0
        self.npc_purse_peak_run: int = 0
        self.npc_fleet_hulls_peak_run: int = 0
        self.npc_city_grain_contracts_signed: int = 0
        self.npc_city_grain_contracts_fulfilled: int = 0
        self.npc_city_grain_contracts_breached: int = 0
        self.port_food_unrest: dict[str, int] = {}
        self.last_grain_food_days: dict[str, float] = {}
        self.last_pop_digest: dict[str, dict] = {}
        self.riot_events: int = 0
        self.last_food_riot_summary: str = ""
        self.port_war_days_remaining: dict[str, int] = {}
        self.port_war_recurring: dict[str, bool] = {}
        self.port_war_peace_remaining: dict[str, int] = {}
        self.port_war_pending_burst: dict[str, int] = {}
        self.port_war_burst_initial: dict[str, int] = {}
        self.last_war_industry_digest: dict[str, dict[str, int]] = {}
        self.port_industrial_metal_per_day: dict[str, int] = {}
        self.port_industrial_wire_per_day: dict[str, int] = {}
        self.port_industrial_timber_per_day: dict[str, int] = {}
        self.port_industrial_textiles_per_day: dict[str, int] = {}
        self.port_trade_price_bias: dict[str, dict[str, float]] = {}
        self.port_market_demand_override: dict[str, dict[str, float]] = {}
        self.port_good_tolls: dict[str, dict[str, int]] = {}
        self.last_industrial_sink_digest: dict[str, dict[str, int]] = {}
        self.last_slave_digest: dict[str, dict] = {}
        self.last_food_riot_by_port: dict[str, int] = {}
        self.port_peace_riot_grace_days: dict[str, int] = {}
        self.player_port_id: str = ""
        self.player_money: int = 300
        self.player_cargo: dict[str, int] = {}
        self.player_voyage_days_remaining: int = 0
        self.player_voyage_dest_id: str = ""
        self.player_voyage_booked_days: int = 0
        self.player_voyage_open_sea_01: float = 0.0
        self.player_voyage_risk_aversion: float = 0.48
        self.player_ship_condition: int = _SHIP_CONDITION_MAX
        self.player_ship_wine_counter: int = 0
        self.player_fleet_ships: int = 1
        self.player_fleet_shipyard_days_remaining: int = 0
        self.player_fleet_shipyard_port_id: str = ""
        self.port_used_hull_listings: dict[str, list[dict]] = {}
        self.next_used_hull_listing_id: int = 1
        ## Per port, current tick: NPC dock wholesale only (`_npc_buy_from_port` / `_npc_sell_to_port`).
        self._port_commerce_tick: dict[str, dict[str, int]] = {}
        ## One entry per completed `_run_daily_population_and_npcs`: { "day": int, "ports": { pid: { ... } } }.
        self.commerce_daily_log: list[dict] = []
        self.port_commerce_pulse: dict[str, float] = {}
        self._luxury_import_cfg: dict = {}
        self._port_luxury_import_queue: dict[str, list[dict]] = {}
        self.port_harbour_due_coins_tick: dict[str, int] = {}
        self.port_cartel_strength: dict[str, float] = {}
        self.port_war_rumor: dict[str, float] = {}
        self.port_plague_days: dict[str, int] = {}
        self.port_rumor_good_delta: dict[str, dict[str, float]] = {}
        self._world_autonomy_warmup_days: int = 24
        self._world_crop_agro_model: bool = True
        self._world_npc_city_grain_contracts_enabled: bool = True
        self.port_crop_moisture_01: dict[str, float] = {}
        self.port_crop_growth_01: dict[str, float] = {}
        self.port_local_crop_belief_01: dict[str, float] = {}
        self.port_inbound_crop_reports: dict[str, list[float]] = {}
        self.port_crop_rumor_public_delta: dict[str, float] = {}
        self.block_npc_merchant_voyages: bool = False
        self._ship_classes: dict[str, dict] = {}
        self._ship_default_id: str = "greek_merchant"
        self._port_shipyard_classes: dict[str, list[str]] = {}
        self._port_cultures: dict[str, str] = {}
        self.player_ship_class_id: str = ""
        self.player_captain_culture: str = "italic"
        self.player_ship_age_days: int = 0
        self.player_voyage_role: str = _VOYAGE_ROLE_MERCHANT
        self.player_offers_convoy_escort: bool = True
        self.player_escort_contract: dict = {}

    def load(self) -> None:
        world = json.loads(WORLD_PATH.read_text())
        goods_doc = json.loads(GOODS_PATH.read_text())
        for g in goods_doc.get("goods", []):
            gid = str(g["id"])
            row: dict = {
                "name": str(g.get("name", gid)),
                "unit_buy_price": int(g.get("unit_buy_price", 1)),
                "unit_sell_price": int(g.get("unit_sell_price", 1)),
                "stock_target": max(1, int(g.get("stock_target", 80))),
                "need_tier": str(g.get("need_tier", "")),
            }
            if "market_demand_per_day" in g:
                row["market_demand_per_day"] = max(0.0, float(g["market_demand_per_day"]))
            if "wage_per_unit_per_day" in g:
                row["wage_per_unit_per_day"] = clampf(float(g["wage_per_unit_per_day"]), 0.0, _MARINE_WAGE_RATE_MAX)
            self.goods[gid] = row
        self.port_trade_price_bias.clear()
        self.port_market_demand_override.clear()
        self.port_good_tolls.clear()
        self.port_used_hull_listings.clear()
        self.next_used_hull_listing_id = 1
        self.commerce_daily_log.clear()
        self.port_commerce_pulse.clear()
        self.port_harbour_due_coins_tick.clear()
        self.port_cartel_strength.clear()
        self.port_war_rumor.clear()
        self.port_plague_days.clear()
        self.port_rumor_good_delta.clear()
        self.port_crop_moisture_01.clear()
        self.port_crop_growth_01.clear()
        self.port_local_crop_belief_01.clear()
        self.port_inbound_crop_reports.clear()
        self.port_crop_rumor_public_delta.clear()
        self.port_war_pending_burst.clear()
        role_bonuses: dict[str, int] = {}
        prb = world.get("port_role_wealth_bonuses")
        if isinstance(prb, dict):
            for rk, rv in prb.items():
                role_bonuses[str(rk)] = max(0, int(rv))
        self.port_mint_cfg.clear()
        tre_raw = clampi(int(world.get("initial_treasury_coins", _WORLD_TREASURY_FALLBACK)), 0, _WORLD_TREASURY_MAX)
        self.world_initial_treasury = clampi(tre_raw, 0, _WORLD_TREASURY_MAX)
        self.world_treasury_coins = self.world_initial_treasury
        self._world_crop_agro_model = bool(world.get("crop_agro_model", True))
        self._world_npc_city_grain_contracts_enabled = bool(world.get("npc_city_grain_contracts_enabled", True))
        self._luxury_import_cfg = {
            "enabled": True,
            "spawn_roll": 0.10,
            "lead_min": 3,
            "lead_max": 8,
            "qty_min": 1,
            "qty_max": 3,
            "max_pending": 4,
            "cost_frac": _LUXURY_IMPORT_COST_FRAC_DEFAULT,
            "treasury_take_frac": _LUXURY_IMPORT_TREASURY_TAKE_FRAC_DEFAULT,
        }
        li_raw = world.get("luxury_import")
        if isinstance(li_raw, dict):
            lid = li_raw
            if "enabled" in lid:
                self._luxury_import_cfg["enabled"] = bool(lid["enabled"])
            if "spawn_roll" in lid:
                self._luxury_import_cfg["spawn_roll"] = clampf(float(lid["spawn_roll"]), 0.0, 0.6)
            if "lead_min" in lid:
                self._luxury_import_cfg["lead_min"] = clampi(int(lid["lead_min"]), 1, 30)
            if "lead_max" in lid:
                self._luxury_import_cfg["lead_max"] = clampi(int(lid["lead_max"]), 1, 40)
            if int(self._luxury_import_cfg["lead_max"]) < int(self._luxury_import_cfg["lead_min"]):
                self._luxury_import_cfg["lead_max"] = int(self._luxury_import_cfg["lead_min"])
            if "qty_min" in lid:
                self._luxury_import_cfg["qty_min"] = clampi(int(lid["qty_min"]), 1, 12)
            if "qty_max" in lid:
                self._luxury_import_cfg["qty_max"] = clampi(int(lid["qty_max"]), 1, 16)
            if int(self._luxury_import_cfg["qty_max"]) < int(self._luxury_import_cfg["qty_min"]):
                self._luxury_import_cfg["qty_max"] = int(self._luxury_import_cfg["qty_min"])
            if "max_pending" in lid:
                self._luxury_import_cfg["max_pending"] = clampi(int(lid["max_pending"]), 1, 12)
            if "cost_frac" in lid:
                self._luxury_import_cfg["cost_frac"] = clampf(float(lid["cost_frac"]), 0.05, 0.85)
            if "treasury_take_frac" in lid:
                self._luxury_import_cfg["treasury_take_frac"] = clampf(float(lid["treasury_take_frac"]), 0.0, 0.95)
        self.port_role_wealth_bonus.clear()
        self.port_roles.clear()
        self.port_existential_war_burst_days.clear()
        self.port_baseline_momentum_up.clear()
        self.port_baseline_momentum_dn.clear()
        self.port_order.clear()
        self.port_names.clear()
        for p in world.get("ports", []):
            pid = str(p["id"])
            self.port_order.append(pid)
            self.port_names[pid] = str(p.get("name", pid))
            init = p.get("initial_stock") or {}
            self.port_initial_stock[pid] = {str(k): max(0, int(v)) for k, v in init.items()}
            self.port_npc_trader_count[pid] = clampi(int(p.get("npc_traders", 4)), 1, _PORT_NPC_TRADERS_LOAD_MAX)
            self.port_population_grain[pid] = clampi(int(p.get("population_grain_per_day", 6)), 0, 120)
            self.port_population_wine_base[pid] = clampi(int(p.get("population_wine_per_day", 1)), 0, 40)
            self.port_population_fish_per_day[pid] = clampi(int(p.get("population_fish_per_day", 0)), 0, 40)
            iw = p.get("initial_wealth", -1)
            if int(iw) >= 0:
                self.port_initial_wealth[pid] = int(iw)
            role_s = str(p.get("role", ""))
            if role_s:
                self.port_roles[pid] = role_s
            self.port_role_wealth_bonus[pid] = role_bonuses.get(role_s, 0) if role_s else 0
            exb_raw = p.get("population_existential_war_burst_days", _POP_EXISTENTIAL_WAR_BURST_OFF)
            exb = clampi(int(exb_raw), 1, _POP_EXISTENTIAL_WAR_BURST_OFF)
            if exb < _POP_EXISTENTIAL_WAR_BURST_OFF:
                self.port_existential_war_burst_days[pid] = exb
            else:
                self.port_existential_war_burst_days.pop(pid, None)
            war_here = bool(p.get("at_war", False))
            war_len = clampi(int(p.get("war_days", _WAR_DEFAULT_DAYS)), 1, 200)
            self.port_war_days_remaining[pid] = war_len if war_here else 0
            recurring = bool(p.get("war_recurring", True))
            self.port_war_recurring[pid] = recurring
            if war_here:
                self.port_war_peace_remaining[pid] = 0
                self.port_war_burst_initial[pid] = war_len
            elif recurring:
                self.port_war_peace_remaining[pid] = self.rng.randint(
                    _WAR_CYCLE_PEACE_MIN, _WAR_CYCLE_PEACE_MAX
                )
            else:
                self.port_war_peace_remaining[pid] = 0
            self.port_industrial_metal_per_day[pid] = clampi(
                int(p.get("industrial_metal_per_day", 0)), 0, _INDUSTRIAL_SINK_METAL_MAX
            )
            self.port_industrial_wire_per_day[pid] = clampi(
                int(p.get("industrial_wire_per_day", 0)), 0, _INDUSTRIAL_SINK_WIRE_MAX
            )
            self.port_industrial_timber_per_day[pid] = clampi(
                int(p.get("industrial_timber_per_day", 0)), 0, _INDUSTRIAL_SINK_TIMBER_MAX
            )
            self.port_industrial_textiles_per_day[pid] = clampi(
                int(p.get("industrial_textiles_per_day", 0)), 0, _INDUSTRIAL_SINK_TEXTILES_MAX
            )
            bias_row: dict[str, float] = {}
            bias_raw = p.get("trade_price_bias")
            if isinstance(bias_raw, dict):
                for gkb, bvv in bias_raw.items():
                    bias_row[str(gkb)] = clampf(float(bvv), -_TRADE_PRICE_BIAS_CLAMP, _TRADE_PRICE_BIAS_CLAMP)
            self.port_trade_price_bias[pid] = bias_row
            mdd_row: dict[str, float] = {}
            mdd_raw = p.get("market_demand_per_day")
            if isinstance(mdd_raw, dict):
                for gkm, dv in mdd_raw.items():
                    mdd_row[str(gkm)] = max(0.0, float(dv))
            self.port_market_demand_override[pid] = mdd_row
            tol_row: dict[str, int] = {}
            tol_raw = p.get("tolls")
            if isinstance(tol_raw, dict):
                for tk, tv in tol_raw.items():
                    gkt = str(tk)
                    v0 = clampi(int(tv), 0, 80)
                    if v0 > 0:
                        tol_row[gkt] = v0
            self.port_good_tolls[pid] = tol_row
            mint_raw = p.get("mint")
            if isinstance(mint_raw, dict) and bool(mint_raw.get("enabled", False)):
                cpb0 = clampi(int(mint_raw.get("coins_per_batch", 72)), 1, 500)
                self.port_mint_cfg[pid] = {
                    "gold_per_batch": clampi(int(mint_raw.get("gold_per_batch", 1)), 0, 24),
                    "silver_per_batch": clampi(int(mint_raw.get("silver_per_batch", 2)), 0, 36),
                    "coins_per_batch": clampi(cpb0, 1, 500),
                    "max_batches_per_day": clampi(int(mint_raw.get("max_batches_per_day", 6)), 1, 40),
                    "treasury_sink_frac": clampf(float(mint_raw.get("treasury_sink_frac", 0.09)), 0.0, 0.45),
                }
        self._prune_port_good_tolls_to_known_goods()
        self.lane_days.clear()
        self.npc_lane_days.clear()
        for lane in world.get("lanes", []):
            a, b = str(lane["from"]), str(lane["to"])
            d = int(lane["days"])
            if a and b and d >= 0:
                self.lane_days[lane_key(a, b)] = d
        for nl in world.get("npc_lanes", []):
            if not isinstance(nl, dict):
                continue
            na, nb = str(nl.get("from", "")), str(nl.get("to", ""))
            nd = max(1, int(round(float(nl.get("days", 1)))))
            if na and nb:
                self.npc_lane_days[lane_key(na, nb)] = nd
        for fr in world.get("farms", []):
            self.farms.append(
                {
                    "port_id": str(fr.get("port_id", "")),
                    "grain_per_day": max(0, int(fr.get("grain_per_day", 0))),
                    "wine_per_day": max(0, int(fr.get("wine_per_day", 0))),
                    "fish_per_day": max(0, int(fr.get("fish_per_day", 0))),
                }
            )
        self.mines.clear()
        for mn in world.get("mines", []):
            mport = str(mn.get("port_id", ""))
            if not mport or mport not in self.port_names:
                continue
            self.mines.append(
                {
                    "id": str(mn.get("id", "")),
                    "name": str(mn.get("name", mn.get("id", ""))),
                    "port_id": mport,
                    "metal_per_day": max(0, int(mn.get("metal_per_day", 0))),
                    "wire_per_day": max(0, int(mn.get("wire_per_day", 0))),
                    "gold_per_day": max(0, int(mn.get("gold_per_day", 0))),
                    "silver_per_day": max(0, int(mn.get("silver_per_day", 0))),
                }
            )
        self._port_cultures.clear()
        self._port_shipyard_classes.clear()
        pc = world.get("port_cultures")
        if isinstance(pc, dict):
            for k, v in pc.items():
                pk = str(k)
                if pk in self.port_names:
                    self._port_cultures[pk] = str(v)
        psy = world.get("port_shipyards")
        if isinstance(psy, dict):
            for k, v in psy.items():
                pk = str(k)
                if pk not in self.port_names:
                    continue
                self._port_shipyard_classes[pk] = [str(x) for x in v] if isinstance(v, list) else []
        self._build_port_neighbors()
        self._rebuild_coastal_shortest_path_cache()
        self._rebuild_coastal_shortest_path_cache_npc()
        self._load_ship_catalog()
        self._finalize_port_stocks()
        self._bootstrap_npc_agents()
        self._init_port_wealth_baseline()
        self._init_port_food_unrest_zero()
        for pid in self.port_order:
            self.port_war_days_remaining.setdefault(pid, 0)
            self.port_war_recurring.setdefault(pid, False)
            self.port_war_peace_remaining.setdefault(pid, 0)
            self.port_industrial_metal_per_day.setdefault(pid, 0)
            self.port_industrial_wire_per_day.setdefault(pid, 0)
            self.port_industrial_timber_per_day.setdefault(pid, 0)
            self.port_industrial_textiles_per_day.setdefault(pid, 0)
            self.port_population_fish_per_day.setdefault(pid, 0)
            self.port_trade_price_bias.setdefault(pid, {})
            self.port_market_demand_override.setdefault(pid, {})
            self._ensure_war_burst_initial_for_port(pid)
        self._ensure_sim_agent_port_defaults()
        self._bootstrap_recurring_war_timers()
        self._ensure_used_hull_listings_for_all_ports()
        self._init_port_demographics_from_world()
        self._init_port_crop_agro_state()
        self.player_port_id = self.port_order[0] if self.port_order else ""
        self.player_money = 300
        self.player_cargo = {"grain": 5, "wine": 2}
        self.player_voyage_days_remaining = 0
        self.player_voyage_dest_id = ""
        self.player_voyage_booked_days = 0
        self.player_voyage_open_sea_01 = 0.0
        self.player_voyage_risk_aversion = 0.48
        self.player_ship_condition = _SHIP_CONDITION_MAX
        self.player_ship_wine_counter = 0
        self.player_fleet_ships = 1
        self.player_fleet_shipyard_days_remaining = 0
        self.player_fleet_shipyard_port_id = ""
        self.player_ship_class_id = self._default_ship_class_for_port(self.player_port_id)
        self.player_captain_culture = str(self._port_cultures.get(self.player_port_id, "italic"))
        self.player_ship_age_days = 0
        self.player_voyage_role = _VOYAGE_ROLE_MERCHANT
        self.player_escort_contract = {}
        self.player_offers_convoy_escort = True
        self._ensure_player_voyage_role_and_contract_py()
        self.port_peace_riot_grace_days.clear()
        self.bankruptcy_events = 0
        self.convoy_formations = 0
        self.escort_coins_paid = 0
        self.pirate_encounter_attempts = 0
        self.pirate_raids_success = 0
        self.pirate_escort_flees = 0
        self.pirate_marines_lost = 0
        self.pirate_loot_coins = 0
        self.player_pirate_encounter_rolls = 0
        self.player_pirate_repelled = 0
        self.player_pirate_hits = 0
        self.npc_purse_peak_run = 0
        self.npc_fleet_hulls_peak_run = 0
        self.npc_city_grain_contracts_signed = 0
        self.npc_city_grain_contracts_fulfilled = 0
        self.npc_city_grain_contracts_breached = 0
        self._world_autonomy_warmup_days = clampi(int(world.get("autonomy_warmup_days", 24)), 0, 180)
        n_warm = clampi(int(self._world_autonomy_warmup_days), 0, 180)
        for _ in range(n_warm):
            self._run_daily_population_and_npcs()
            self.current_day += 1

    def _load_ship_catalog(self) -> None:
        self._ship_classes.clear()
        if not SHIPS_PATH.is_file():
            self._ship_default_id = "greek_merchant"
            return
        try:
            doc = json.loads(SHIPS_PATH.read_text())
        except (OSError, json.JSONDecodeError):
            self._ship_default_id = "greek_merchant"
            return
        self._ship_default_id = str(doc.get("default_player_class", "greek_merchant"))
        for row in doc.get("ships", []):
            if not isinstance(row, dict):
                continue
            sid = str(row.get("id", ""))
            if sid:
                self._ship_classes[sid] = row
        if self._ship_default_id not in self._ship_classes:
            self._ship_default_id = (
                "greek_merchant" if "greek_merchant" in self._ship_classes else next(iter(self._ship_classes), "greek_merchant")
            )

    def _orderable_shipyard_ids_at_port(self, port_id: str) -> list[str]:
        ps = str(port_id)
        out: list[str] = []
        if ps not in self.port_names:
            return out
        for sid in self._port_shipyard_classes.get(ps, []):
            row = self._ship_classes.get(str(sid))
            if isinstance(row, dict) and bool(row.get("player_orderable", True)):
                out.append(str(sid))
        return out

    def _default_ship_class_for_port(self, port_id: str) -> str:
        opts = self._orderable_shipyard_ids_at_port(str(port_id))
        return opts[0] if opts else self._ship_default_id

    def _fallback_ship_row(self) -> dict:
        row = self._ship_classes.get(self._ship_default_id)
        if isinstance(row, dict):
            return row
        return {
            "cargo_per_hull": _FLEET_CARGO_PER_SHIP,
            "grain_hold_efficiency": 1.0,
            "voyage_day_mult": 1.0,
            "open_sea_exposure_mul": 1.0,
            "storm_probability_mul": 1.0,
            "storm_damage_mul": 1.0,
            "crew_wine_per_ship": 1,
            "officer_pay_per_hull": 1,
            "foreign_ops_mult": 1.1,
            "repair_coin_mult": 1.0,
            "build": {},
        }

    def _npc_ship_row(self, agent: dict) -> dict:
        sid = str(agent.get("ship_class_id", ""))
        if sid and sid in self._ship_classes:
            return self._ship_classes[sid]
        return self._fallback_ship_row()

    def _player_ship_row(self) -> dict:
        sid = str(self.player_ship_class_id)
        if sid and sid in self._ship_classes:
            return self._ship_classes[sid]
        return self._fallback_ship_row()

    def _ship_build_block(self, row: dict) -> dict:
        b = row.get("build")
        if not isinstance(b, dict):
            return {
                "labor_mult": 1.0,
                "timber_mult": 1.0,
                "textiles_mult": 1.0,
                "metal_mult": 1.0,
                "days_mult": 1.0,
            }
        return b

    def _npc_fleet_build_ints(self, agent: dict) -> dict:
        row = self._npc_ship_row(agent)
        b = self._ship_build_block(row)
        return {
            "labor": max(1, int(round(float(_FLEET_NEW_SHIP_LABOR_COINS) * float(b.get("labor_mult", 1.0))))),
            "timber": max(1, int(round(float(_FLEET_NEW_SHIP_TIMBER) * float(b.get("timber_mult", 1.0))))),
            "textiles": max(1, int(round(float(_FLEET_NEW_SHIP_TEXTILES) * float(b.get("textiles_mult", 1.0))))),
            "metal": max(1, int(round(float(_FLEET_NEW_SHIP_METAL) * float(b.get("metal_mult", 1.0))))),
            "days": max(1, int(round(float(_FLEET_NEW_SHIP_BUILD_DAYS) * float(b.get("days_mult", 1.0))))),
        }

    def _player_age_stress_01(self) -> float:
        return clampf(float(self.player_ship_age_days) / 2200.0, 0.0, 1.0)

    def _player_cultural_ops_scale(self) -> float:
        row = self._player_ship_row()
        hull_culture = str(row.get("culture", "greek"))
        cap = str(self.player_captain_culture).strip()
        if not cap:
            cap = str(self._port_cultures.get(self.player_port_id, "italic"))
        fom = clampf(float(row.get("foreign_ops_mult", 1.1)), 1.0, 1.55)
        if cap == hull_culture:
            return 1.0
        return fom

    def _npc_cultural_ops_scale(self, agent: dict) -> dict:
        row = self._npc_ship_row(agent)
        hull_culture = str(row.get("culture", "greek"))
        home = str(agent.get("home_port", ""))
        cap0 = str(agent.get("captain_culture", self._port_cultures.get(home, "greek")))
        fom = clampf(float(row.get("foreign_ops_mult", 1.1)), 1.0, 1.55)
        if cap0 == hull_culture:
            return {"wine_scale": 1.0, "officer_scale": 1.0}
        return {"wine_scale": fom, "officer_scale": fom}

    def _npc_officer_due_coins(self, agent: dict) -> int:
        self._ensure_npc_ship_fields(agent)
        sh = clampi(int(agent.get("fleet_ships", 1)), 1, _FLEET_MAX_SHIPS)
        culd = self._npc_cultural_ops_scale(agent)
        oph = max(1, int(self._npc_ship_row(agent).get("officer_pay_per_hull", 1)))
        pay_sc = float(oph) * float(culd.get("officer_scale", 1.0))
        officer_leg = max(1, int(math.ceil(float(sh * _SHIP_OFFICER_PAY_DAILY) * pay_sc)))
        cr = agent.get("cargo")
        cargo_d: dict = cr if isinstance(cr, dict) else {}
        return officer_leg + self._marine_wage_due_for_cargo(cargo_d, pay_sc)

    def _bootstrap_recurring_war_timers(self) -> None:
        for pid in self.port_order:
            ps = str(pid)
            if not bool(self.port_war_recurring.get(ps, False)):
                continue
            if self.get_port_war_days_remaining(ps) > 0:
                continue
            if int(self.port_war_peace_remaining.get(ps, 0)) > 0:
                continue
            self.port_war_peace_remaining[ps] = self.rng.randint(
                _WAR_CYCLE_PEACE_MIN, _WAR_CYCLE_PEACE_MAX
            )

    def get_port_war_days_remaining(self, port_id: str) -> int:
        ps = str(port_id)
        if ps not in self.port_names:
            return 0
        return max(0, int(self.port_war_days_remaining.get(ps, 0)))

    def is_port_at_war(self, port_id: str) -> bool:
        return self.get_port_war_days_remaining(port_id) > 0

    def _ensure_war_burst_initial_for_port(self, port_id: str) -> None:
        ps = str(port_id)
        if self.get_port_war_days_remaining(ps) <= 0:
            self.port_war_burst_initial.pop(ps, None)
            return
        cur = int(self.port_war_burst_initial.get(ps, 0))
        if cur <= 0:
            self.port_war_burst_initial[ps] = max(1, self.get_port_war_days_remaining(ps))

    def _food_riot_threshold_for_port(self, port_id: str) -> int:
        ps = str(port_id)
        if "grain" not in self.goods:
            return _FOOD_RIOT_THRESHOLD
        if self.is_port_at_war(ps):
            burst0 = max(1, int(self.port_war_burst_initial.get(ps, self.get_port_war_days_remaining(ps))))
            rem = self.get_port_war_days_remaining(ps)
            elapsed = max(0, burst0 - rem)
            bonus = clampi(_WAR_RIOT_GRACE_EXTRA - elapsed, 0, _WAR_RIOT_GRACE_EXTRA)
            return _FOOD_RIOT_THRESHOLD + bonus
        gr = clampi(int(self.port_peace_riot_grace_days.get(ps, 0)), 0, 999)
        if gr > 0:
            return _FOOD_RIOT_THRESHOLD + _WAR_PEACE_RIOT_THRESHOLD_BONUS
        return _FOOD_RIOT_THRESHOLD

    def _war_panic_mult_for_port(self, port_id: str) -> float:
        ps = str(port_id)
        if not self.is_port_at_war(ps):
            return 1.0
        burst0 = max(1, int(self.port_war_burst_initial.get(ps, self.get_port_war_days_remaining(ps))))
        elapsed = max(0, burst0 - self.get_port_war_days_remaining(ps))
        return min(1.0, float(elapsed) / float(_WAR_RIOT_PANIC_RAMP_DAYS))

    def _food_unrest_tier_label(self, unrest: int) -> str:
        u = clampi(int(unrest), 0, 200)
        if u < 40:
            return "Calm"
        if u < 65:
            return "Uneasy"
        if u < 88:
            return "Tense"
        return "Critical"

    def _init_port_demographics_from_world(self) -> None:
        for pid in self.port_order:
            ps = str(pid)
            p0 = clampi(int(self.port_population_grain.get(ps, 0)), 0, 120)
            if p0 < _POP_GRAIN_FLOOR:
                p0 = _POP_GRAIN_FLOOR
                self.port_population_grain[ps] = p0
            self.port_population_grain_baseline[ps] = max(1, p0)
            self.port_population_grain_cap[ps] = min(
                120,
                max(p0 + _POP_GRAIN_CEILING_BOOST, int(math.ceil(float(p0) * 1.48))),
            )
            self.port_famine_streak_days[ps] = 0
            self.port_consecutive_grain_full_ration_days[ps] = 0
            self.port_consecutive_grain_zero_eat_days[ps] = 0
            self.port_prosperity_streak_days[ps] = 0
            self.port_rationing_active[ps] = False
            self.port_rationing_days_active[ps] = 0
            self.port_baseline_momentum_up[ps] = 0
            self.port_baseline_momentum_dn[ps] = 0
            cap_pres = float(self._preserved_food_cap_for_port(ps))
            self.port_preserved_food[ps] = cap_pres * _PRESERVED_FOOD_INITIAL_FRAC

    def _preserved_food_cap_for_port(self, port_id: str) -> int:
        ps = str(port_id)
        b = max(1, int(self.port_population_grain_baseline.get(ps, 1)))
        return max(_PRESERVED_FOOD_CAP_MIN, b * _PRESERVED_FOOD_CAP_MULT)

    def _population_baseline_floor_for_port(self, port_id: str) -> int:
        rl = str(self.port_roles.get(str(port_id), ""))
        if rl in ("metropole", "great_city"):
            return 7
        if rl == "imperial_port":
            return 6
        if rl in ("regional_capital", "breadbasket"):
            return 5
        return _POP_GRAIN_FLOOR

    def _recompute_population_grain_cap_for_port(self, port_id: str) -> None:
        ps = str(port_id)
        if ps not in self.port_names:
            return
        base = clampi(int(self.port_population_grain_baseline.get(ps, 1)), 1, 120)
        popv = clampi(int(self.port_population_grain.get(ps, 0)), 0, 120)
        cap_calc = min(120, max(base + _POP_GRAIN_CEILING_BOOST, int(math.ceil(float(base) * 1.48))))
        self.port_population_grain_cap[ps] = min(120, max(cap_calc, popv + 1))

    def _famine_streak_to_loss_for_port(self, port_id: str) -> int:
        ps = str(port_id)
        th = clampi(int(self.port_existential_war_burst_days.get(ps, _POP_EXISTENTIAL_WAR_BURST_OFF)), 1, _POP_EXISTENTIAL_WAR_BURST_OFF)
        if th >= _POP_EXISTENTIAL_WAR_BURST_OFF:
            return _POP_FAMINE_STREAK_TO_LOSS
        if not self.is_port_at_war(ps):
            return _POP_FAMINE_STREAK_TO_LOSS
        burst0 = max(1, int(self.port_war_burst_initial.get(ps, self.get_port_war_days_remaining(ps))))
        if burst0 < th:
            return _POP_FAMINE_STREAK_TO_LOSS
        return max(8, int(math.ceil(float(_POP_FAMINE_STREAK_TO_LOSS) * 0.5)))

    def _summer_forage_mouths_for_doy(self, doy: int) -> int:
        if doy < _FORAGE_SUMMER_START_DOY or doy > _FORAGE_SUMMER_END_DOY:
            return 0
        width = float(_FORAGE_SUMMER_END_DOY - _FORAGE_SUMMER_START_DOY)
        if width <= 0.0:
            return 0
        t = (float(doy) - float(_FORAGE_SUMMER_START_DOY)) / width
        v = _FORAGE_SUMMER_PEAK_MOUTHS * math.sin(math.pi * t)
        return clampi(int(round(v)), 0, int(round(_FORAGE_SUMMER_PEAK_MOUTHS)))

    def _population_output_scale_for_port(self, port_id: str) -> float:
        ps = str(port_id)
        if ps not in self.port_names:
            return 1.0
        base = max(1, int(self.port_population_grain_baseline.get(ps, 1)))
        cur = max(1, clampi(int(self.port_population_grain.get(ps, 0)), 0, 120))
        return clampf(float(cur) / float(base), _POP_OUTPUT_SCALE_MIN, _POP_OUTPUT_SCALE_MAX)

    def _tick_population_demographics(self) -> None:
        if not self.port_order:
            return
        for pid in self.port_order:
            ps = str(pid)
            eat0 = clampi(int(self.port_population_grain.get(ps, 0)), 0, 120)
            if eat0 < _POP_GRAIN_FLOOR:
                continue
            fd = float(self.last_grain_food_days.get(ps, 9999.0))
            u = clampi(int(self.port_food_unrest.get(ps, 0)), 0, 200)
            eat_need = self.get_population_grain_eat_effective(ps)
            dig = self.last_pop_digest.get(ps, {})
            if isinstance(dig, dict):
                eaten_eff = int(dig.get("grain", 0)) + int(dig.get("preserved", 0)) + int(dig.get("forage", 0))
            else:
                eaten_eff = 0
            full_d = clampi(int(self.port_consecutive_grain_full_ration_days.get(ps, 0)), 0, 999)
            zero_d = clampi(int(self.port_consecutive_grain_zero_eat_days.get(ps, 0)), 0, 999)
            if eat_need <= 0:
                full_d = 0
                zero_d = 0
            elif eaten_eff >= eat_need:
                full_d = min(999, full_d + 1)
                zero_d = 0
            elif eaten_eff <= 0:
                zero_d = min(999, zero_d + 1)
                full_d = 0
            else:
                full_d = 0
                zero_d = 0
            self.port_consecutive_grain_full_ration_days[ps] = full_d
            self.port_consecutive_grain_zero_eat_days[ps] = zero_d
            base_ln = max(1, int(self.port_population_grain_baseline.get(ps, 1)))
            if eat0 >= int(math.ceil(float(base_ln) * _POP_BASELINE_RISE_FRAC)) and fd >= 1.85 and u < 96:
                self.port_baseline_momentum_up[ps] = min(999, int(self.port_baseline_momentum_up.get(ps, 0)) + 1)
                self.port_baseline_momentum_dn[ps] = 0
            else:
                self.port_baseline_momentum_up[ps] = 0
            if eat0 <= int(math.floor(float(base_ln) * _POP_BASELINE_FALL_FRAC)) and (u > 112 or zero_d >= 6):
                self.port_baseline_momentum_dn[ps] = min(999, int(self.port_baseline_momentum_dn.get(ps, 0)) + 1)
            else:
                self.port_baseline_momentum_dn[ps] = 0
            harsh = (eat_need > 0 and zero_d >= _POP_FAMINE_HARSH_CONSEC_ZERO_GRAIN_DAYS) or u >= _POP_FAMINE_HARSH_UNREST_MIN
            calm = (eat_need > 0 and full_d >= _POP_FAMINE_CALM_CONSEC_FULL_RATION_DAYS) and u < 38
            fs = clampi(int(self.port_famine_streak_days.get(ps, 0)), 0, 999)
            if harsh:
                fs = min(999, fs + 1)
            elif calm:
                fs = 0
            else:
                fs = max(0, fs - 1)
            self.port_famine_streak_days[ps] = fs
            streak_need = self._famine_streak_to_loss_for_port(ps)
            if fs >= streak_need and eat0 > _POP_GRAIN_FLOOR:
                self.port_population_grain[ps] = eat0 - 1
                self.port_famine_streak_days[ps] = _POP_FAMINE_STREAK_RESET
            eat0 = clampi(int(self.port_population_grain.get(ps, 0)), 0, 120)
            base_ln = max(1, int(self.port_population_grain_baseline.get(ps, 1)))
            if int(self.port_baseline_momentum_up.get(ps, 0)) >= _POP_BASELINE_RISE_DAYS and base_ln < 120:
                self.port_population_grain_baseline[ps] = base_ln + 1
                self.port_baseline_momentum_up[ps] = 0
                self._recompute_population_grain_cap_for_port(ps)
                base_ln = int(self.port_population_grain_baseline.get(ps, 1))
            if int(self.port_baseline_momentum_dn.get(ps, 0)) >= _POP_BASELINE_FALL_DAYS:
                floor_b = self._population_baseline_floor_for_port(ps)
                if base_ln > floor_b:
                    self.port_population_grain_baseline[ps] = base_ln - 1
                    self.port_baseline_momentum_dn[ps] = 0
                    self._recompute_population_grain_cap_for_port(ps)
                    base_ln = int(self.port_population_grain_baseline.get(ps, 1))
            wv = int(self.port_wealth.get(ps, 50))
            att = self._wealth_stock_target_for_port(ps)
            pulse0 = clampf(float(self.port_commerce_pulse.get(ps, 0.38)), 0.0, 1.0)
            commerce_poor = pulse0 < _COMMERCE_POOR_PULSE and float(wv) < float(max(1, att)) * 0.95
            wealthy = float(wv) > float(max(1, att)) * 1.04 and fd >= 2.4 and u < 65
            poor = (
                float(wv) < float(max(1, att)) * 0.92
                or fd < 1.5
                or u > _POP_PROSPERITY_POOR_UNREST_EXCEEDS
                or commerce_poor
            )
            psr = clampi(int(self.port_prosperity_streak_days.get(ps, 0)), 0, 999)
            if wealthy:
                inc = 1
                baseline_eat = max(1, int(self.port_population_grain_baseline.get(ps, 1)))
                if eat0 < baseline_eat:
                    gap_frac = float(baseline_eat - eat0) / float(baseline_eat)
                    inc += int(math.floor(gap_frac * float(_POP_MIGRATION_PULL)))
                psr = min(999, psr + inc)
            elif poor:
                psr = max(0, psr - _POP_PROSPERITY_POOR_DECAY)
            else:
                psr = max(0, psr - 1)
            self.port_prosperity_streak_days[ps] = psr
            cap = clampi(
                int(self.port_population_grain_cap.get(ps, eat0 + 20)),
                eat0,
                120,
            )
            if psr >= _POP_PROSPERITY_STREAK_TO_GAIN and eat0 < cap:
                self.port_population_grain[ps] = eat0 + 1
                self.port_prosperity_streak_days[ps] = _POP_PROSPERITY_STREAK_RESET
                if self.rng.random() < 0.35:
                    wb = clampi(int(self.port_population_wine_base.get(ps, 1)), 1, 40)
                    if wb < 40:
                        self.port_population_wine_base[ps] = wb + 1
            plg = clampi(int(self.port_plague_days.get(ps, 0)), 0, 999)
            if plg == 0 and eat0 >= _POP_GRAIN_FLOOR and u > 155 and fd < 0.45 and self.rng.random() < 0.0005:
                self.port_plague_days[ps] = self.rng.randint(9, 16)
                plg = int(self.port_plague_days[ps])
            if plg > 0:
                eatp = clampi(int(self.port_population_grain.get(ps, 0)), 0, 120)
                if eatp > _POP_GRAIN_FLOOR and self.rng.random() < 0.085:
                    self.port_population_grain[ps] = eatp - 1
                self.port_plague_days[ps] = max(0, plg - 1)

    def _player_cargo_qty(self, good_id: str) -> int:
        return max(0, int(self.player_cargo.get(str(good_id), 0)))

    def _adjust_player_cargo_delta(self, good_id: str, delta: int) -> None:
        gid = str(good_id)
        if gid not in self.goods:
            return
        q = self._player_cargo_qty(gid) + int(delta)
        if q <= 0:
            self.player_cargo.pop(gid, None)
        else:
            self.player_cargo[gid] = q

    def is_player_at_sea(self) -> bool:
        return int(self.player_voyage_days_remaining) > 0

    def _captain_cargo_qty(self, cargo: dict, good_id: str) -> int:
        return max(0, int(cargo.get(str(good_id), 0)))

    def _captain_cargo_apply_delta(self, cargo: dict, good_id: str, delta: int) -> None:
        gid = str(good_id)
        if gid not in self.goods:
            return
        q = self._captain_cargo_qty(cargo, gid) + int(delta)
        if q <= 0:
            cargo.pop(gid, None)
        else:
            cargo[gid] = q

    def _marine_wage_rate_per_unit(self) -> float:
        if "marines" not in self.goods:
            return 0.0
        g = self.goods["marines"]
        return clampf(float(g.get("wage_per_unit_per_day", _MARINE_WAGE_PER_UNIT_PER_DAY_DEFAULT)), 0.0, _MARINE_WAGE_RATE_MAX)

    def _marine_wage_due_for_cargo(self, cargo: dict, pay_scale: float) -> int:
        if "marines" not in self.goods:
            return 0
        n = self._captain_cargo_qty(cargo, "marines")
        if n <= 0:
            return 0
        rate = self._marine_wage_rate_per_unit()
        if rate <= 0.0:
            return 0
        sc = clampf(float(pay_scale), 0.2, 8.0)
        return max(0, int(math.ceil(float(n) * rate * sc)))

    def _tick_captain_officer_pay(self, cap: dict) -> None:
        money = clampi(int(cap.get("money", 0)), 0, _MAX_PURSE_COINS_PY)
        cond = clampi(
            int(cap.get("ship_condition", _SHIP_CONDITION_MAX)),
            _SHIP_CONDITION_MIN,
            _SHIP_CONDITION_MAX,
        )
        ships = clampi(int(cap.get("fleet_ships", 1)), 1, _FLEET_MAX_SHIPS)
        pay_scale = clampf(float(cap.get("officer_pay_scale", 1.0)), 0.2, 8.0)
        officer_pay = max(1, int(math.ceil(float(_SHIP_OFFICER_PAY_DAILY) * float(ships) * pay_scale)))
        marine_w = 0
        cargo = cap.get("cargo")
        if isinstance(cargo, dict):
            marine_w = self._marine_wage_due_for_cargo(cargo, pay_scale)
        pay = officer_pay + marine_w
        pay_actual = min(pay, money)
        if pay_actual > 0:
            money -= pay_actual
        if pay_actual < pay and _SHIP_OFFICER_UNDERPAY_CONDITION_PENALTY > 0:
            cond = clampi(
                cond - _SHIP_OFFICER_UNDERPAY_CONDITION_PENALTY,
                _SHIP_CONDITION_MIN,
                _SHIP_CONDITION_MAX,
            )
        cap["money"] = clampi(money, 0, _MAX_PURSE_COINS_PY)
        cap["ship_condition"] = cond

    def _tick_captain_shared(
        self, cap: dict, was_at_sea_today: bool, docked_for_repair: bool
    ) -> None:
        cargo = cap.get("cargo")
        if not isinstance(cargo, dict):
            return
        money_before = clampi(int(cap.get("money", 0)), 0, _MAX_PURSE_COINS_PY)
        money = money_before
        cond = clampi(
            int(cap.get("ship_condition", _SHIP_CONDITION_MAX)),
            _SHIP_CONDITION_MIN,
            _SHIP_CONDITION_MAX,
        )
        wctr = clampi(int(cap.get("ship_wine_counter", 0)), 0, 9999)
        cargo_touch = False
        ships = clampi(int(cap.get("fleet_ships", 1)), 1, _FLEET_MAX_SHIPS)
        wine_per_ship = max(1, int(cap.get("crew_wine_per_ship", 1)))
        wine_cult = clampf(float(cap.get("crew_wine_cultural_scale", 1.0)), 0.5, 2.5)
        if "wine" in self.goods:
            wctr += 1
            if wctr % _SHIP_CREW_WINE_EVERY_N_DAYS == 0:
                need_w = max(1, int(math.ceil(float(ships * wine_per_ship) * wine_cult)))
                take_w = min(need_w, self._captain_cargo_qty(cargo, "wine"))
                if take_w > 0:
                    self._captain_cargo_apply_delta(cargo, "wine", -take_w)
                    cargo_touch = True
                if take_w < need_w and _SHIP_RATION_MISS_WINE_PENALTY > 0:
                    cond = clampi(
                        cond - (need_w - take_w) * _SHIP_RATION_MISS_WINE_PENALTY,
                        _SHIP_CONDITION_MIN,
                        _SHIP_CONDITION_MAX,
                    )
        if was_at_sea_today and _SHIP_WEAR_AT_SEA > 0:
            cond = clampi(
                cond - _SHIP_WEAR_AT_SEA,
                _SHIP_CONDITION_MIN,
                _SHIP_CONDITION_MAX,
            )
        if docked_for_repair and cond < _SHIP_CONDITION_MAX:
            did_repair = False
            if "metal" in self.goods and "wire" in self.goods:
                if self._captain_cargo_qty(cargo, "metal") >= 1 and self._captain_cargo_qty(cargo, "wire") >= 1:
                    self._captain_cargo_apply_delta(cargo, "metal", -1)
                    self._captain_cargo_apply_delta(cargo, "wire", -1)
                    cargo_touch = True
                    cond = min(_SHIP_CONDITION_MAX, cond + _SHIP_REPAIR_MATERIALS_GAIN)
                    did_repair = True
            if not did_repair and cond < _SHIP_REPAIR_COIN_MAX_CONDITION:
                rcm = clampf(float(cap.get("repair_coin_mult", 1.0)), 0.35, 3.5)
                coin_cost = max(
                    1,
                    int(
                        math.ceil(
                            float(_SHIP_REPAIR_COIN_COST + max(0, ships - 1) * _FLEET_REPAIR_COIN_PER_EXTRA_SHIP)
                            * rcm
                        )
                    ),
                )
                if money >= coin_cost:
                    money -= coin_cost
                    cond = min(_SHIP_CONDITION_MAX, cond + _SHIP_REPAIR_COIN_GAIN)
        cond = clampi(cond, _SHIP_CONDITION_MIN, _SHIP_CONDITION_MAX)
        money = clampi(money, 0, _MAX_PURSE_COINS_PY)
        cap["money"] = money
        cap["ship_condition"] = cond
        cap["ship_wine_counter"] = wctr

    def _tick_player_ship_and_crew(self, was_at_sea_today: bool) -> None:
        row = self._player_ship_row()
        cw = max(1, int(row.get("crew_wine_per_ship", 1)))
        oph = max(1, int(row.get("officer_pay_per_hull", 1)))
        cul = self._player_cultural_ops_scale()
        off_scale = float(oph) * cul
        cap = {
            "money": int(self.player_money),
            "cargo": self.player_cargo,
            "ship_condition": int(self.player_ship_condition),
            "ship_wine_counter": int(self.player_ship_wine_counter),
            "fleet_ships": clampi(int(self.player_fleet_ships), 1, _FLEET_MAX_SHIPS),
            "crew_wine_per_ship": cw,
            "officer_pay_scale": off_scale,
            "repair_coin_mult": float(row.get("repair_coin_mult", 1.0)),
            "crew_wine_cultural_scale": cul,
        }
        self._tick_captain_shared(cap, was_at_sea_today, not self.is_player_at_sea())
        self.player_money = clampi(int(cap.get("money", 0)), 0, _MAX_PURSE_COINS_PY)
        self.player_ship_condition = clampi(
            int(cap.get("ship_condition", _SHIP_CONDITION_MAX)),
            _SHIP_CONDITION_MIN,
            _SHIP_CONDITION_MAX,
        )
        self.player_ship_wine_counter = clampi(int(cap.get("ship_wine_counter", 0)), 0, 9999)
        if self.player_ship_age_days > 360 and self.rng.random() < _SHIP_AGE_LEAK_DAILY_P * (
            0.15 + self._player_age_stress_01()
        ):
            self.player_ship_condition = clampi(int(self.player_ship_condition) - 1, _SHIP_CONDITION_MIN, _SHIP_CONDITION_MAX)

    def get_population_grain_eat_effective(self, port_id: str) -> int:
        ps = str(port_id)
        base = clampi(int(self.port_population_grain.get(ps, 0)), 0, 120)
        if base <= 0 or not self.is_port_at_war(ps):
            return base
        return clampi(int(math.ceil(float(base) * _WAR_GRAIN_RATION_MULT)), base + 1, 120)

    def _npc_trade_skills_from_seed(self, seed: int) -> dict[str, float]:
        b = clampf(
            0.92 + math.sin(float(seed) * 2.17) * 0.16 + math.sin(float(seed) * 0.41) * 0.09,
            _NPC_MASTER_MIN,
            _NPC_MASTER_MAX,
        )
        s = clampf(
            0.92 + math.cos(float(seed) * 1.97) * 0.16 + math.cos(float(seed) * 0.37) * 0.09,
            _NPC_MASTER_MIN,
            _NPC_MASTER_MAX,
        )
        return {"buy": b, "sell": s}

    def _roll_npc_trade_skills(self) -> dict[str, float]:
        b = self.rng.uniform(0.84, 1.12)
        s = self.rng.uniform(0.84, 1.12)
        r = self.rng.random()
        if r < 0.11:
            b = self.rng.uniform(0.76, 0.91)
            s = self.rng.uniform(0.76, 0.91)
        elif r < 0.24:
            b = self.rng.uniform(1.04, 1.22)
            s = self.rng.uniform(0.79, 0.99)
        elif r < 0.37:
            b = self.rng.uniform(0.79, 0.99)
            s = self.rng.uniform(1.04, 1.22)
        elif r < 0.50:
            b = self.rng.uniform(1.02, 1.20)
            s = self.rng.uniform(1.02, 1.20)
        return {
            "buy": clampf(b, _NPC_MASTER_MIN, _NPC_MASTER_MAX),
            "sell": clampf(s, _NPC_MASTER_MIN, _NPC_MASTER_MAX),
        }

    def _normalize_npc_trade_skills(self, ag: dict) -> None:
        if "buy_mastery" in ag and "sell_mastery" in ag:
            ag["buy_mastery"] = clampf(float(ag.get("buy_mastery", 1.0)), _NPC_MASTER_MIN, _NPC_MASTER_MAX)
            ag["sell_mastery"] = clampf(float(ag.get("sell_mastery", 1.0)), _NPC_MASTER_MIN, _NPC_MASTER_MAX)
        elif "merchant_acumen" in ag:
            u = clampf(float(ag.get("merchant_acumen", 1.0)), 0.88, 1.18)
            ag["buy_mastery"] = clampf(u, _NPC_MASTER_MIN, _NPC_MASTER_MAX)
            ag["sell_mastery"] = clampf(u, _NPC_MASTER_MIN, _NPC_MASTER_MAX)
            del ag["merchant_acumen"]
        else:
            sid = int(ag.get("id", 0))
            sk = self._npc_trade_skills_from_seed(sid)
            ag["buy_mastery"] = sk["buy"]
            ag["sell_mastery"] = sk["sell"]

    def _append_unique_neighbor_to(self, neigh_out: dict[str, list[str]], port_id: str, neighbor_id: str) -> None:
        neigh_out.setdefault(port_id, [])
        arr = neigh_out[port_id]
        if neighbor_id not in arr:
            arr.append(neighbor_id)

    def _build_port_neighbors_from(self, lane_src: dict[str, int], neigh_out: dict[str, list[str]]) -> None:
        neigh_out.clear()
        for key in lane_src:
            parts = str(key).split("|", 1)
            if len(parts) != 2:
                continue
            a, b = parts[0], parts[1]
            self._append_unique_neighbor_to(neigh_out, a, b)
            self._append_unique_neighbor_to(neigh_out, b, a)

    def _build_port_neighbors(self) -> None:
        self._build_port_neighbors_from(self.lane_days, self.port_neighbors)

    def _voyage_lane_weight_undirected_for(self, lanes: dict[str, int], a: str, b: str) -> int:
        w = int(lanes.get(lane_key(a, b), -1))
        if w >= 0:
            return w
        return int(lanes.get(lane_key(b, a), -1))

    def _voyage_lane_weight_undirected(self, a: str, b: str) -> int:
        return self._voyage_lane_weight_undirected_for(self.lane_days, a, b)

    def _voyage_max_lane_weight_for(self, lanes: dict[str, int]) -> int:
        mx = 1
        for _k, dv in lanes.items():
            mx = max(mx, int(dv))
        return mx

    def _voyage_max_lane_weight(self) -> int:
        return self._voyage_max_lane_weight_for(self.lane_days)

    def _rebuild_coastal_shortest_path_cache_for(
        self,
        neigh_src: dict[str, list[str]],
        lane_src: dict[str, int],
        cache_out: dict[str, int],
    ) -> None:
        cache_out.clear()
        if not self.port_names:
            return
        for src in self.port_order:
            best: dict[str, int] = {str(pk): 999999 for pk in self.port_order}
            best[str(src)] = 0
            used: dict[str, bool] = {}
            for _iter in range(len(self.port_order) + 4):
                pick = ""
                pick_dist = 999999
                for ps2 in self.port_order:
                    if used.get(ps2, False):
                        continue
                    dv2 = int(best.get(ps2, 999999))
                    if dv2 < pick_dist:
                        pick_dist = dv2
                        pick = ps2
                if not pick or pick_dist >= 999999:
                    break
                used[pick] = True
                neigh = neigh_src.get(pick) or []
                for nx in neigh:
                    if used.get(str(nx), False):
                        continue
                    wgt = self._voyage_lane_weight_undirected_for(lane_src, pick, str(nx))
                    if wgt < 0:
                        continue
                    alt = pick_dist + wgt
                    if alt < int(best.get(str(nx), 999999)):
                        best[str(nx)] = alt
            for dst in self.port_order:
                if str(dst) == str(src):
                    continue
                fin = int(best.get(str(dst), 999999))
                if fin >= 999999:
                    cache_out[lane_key(str(src), str(dst))] = -1
                else:
                    cache_out[lane_key(str(src), str(dst))] = fin

    def _rebuild_coastal_shortest_path_cache(self) -> None:
        self._rebuild_coastal_shortest_path_cache_for(
            self.port_neighbors, self.lane_days, self._voyage_coastal_shortest_cache
        )

    def _rebuild_coastal_shortest_path_cache_npc(self) -> None:
        self._voyage_coastal_shortest_cache_npc.clear()
        self.port_neighbors_npc.clear()
        if not self.npc_lane_days:
            return
        self._build_port_neighbors_from(self.npc_lane_days, self.port_neighbors_npc)
        self._rebuild_coastal_shortest_path_cache_for(
            self.port_neighbors_npc, self.npc_lane_days, self._voyage_coastal_shortest_cache_npc
        )

    def _coastal_shortest_days_lookup(self, from_id: str, to_id: str) -> int:
        k = lane_key(str(from_id), str(to_id))
        if k in self._voyage_coastal_shortest_cache:
            return int(self._voyage_coastal_shortest_cache[k])
        return 999999

    def _coastal_shortest_days_lookup_npc(self, from_id: str, to_id: str) -> int:
        k = lane_key(str(from_id), str(to_id))
        if k in self._voyage_coastal_shortest_cache_npc:
            return int(self._voyage_coastal_shortest_cache_npc[k])
        return 999999

    def _voyage_route_choice_roll(self, from_id: str, to_id: str) -> float:
        s = f"{from_id}>{to_id}>voyageRouteV1"
        h = 5381
        for ch in s:
            h = ((h << 5) + h + ord(ch)) & 0x7FFFFFFF
        return float(h % 1000003) / 1000003.0

    def _voyage_plan(self, from_id: str, to_id: str, risk_aversion_01: float, use_npc_graph: bool = False) -> dict:
        ra = clampf(float(risk_aversion_01), 0.0, 1.0)
        use_npc = bool(use_npc_graph) and bool(self.npc_lane_days)
        if use_npc:
            d_c = self._coastal_shortest_days_lookup_npc(from_id, to_id)
            lane_fb = self.npc_lane_days
        else:
            d_c = self._coastal_shortest_days_lookup(from_id, to_id)
            lane_fb = self.lane_days
        disconnected = d_c < 0 or d_c >= 500000
        if disconnected:
            md = self._voyage_max_lane_weight_for(lane_fb)
            dd = clampi(_VOYAGE_DISCONNECTED_BASE_DAYS + md, 10, 48)
            return {"days": dd, "open_01": 0.92, "route_label": "open sea"}
        d_b = d_c
        if d_c >= 4:
            d_b = max(1, int(float(d_c) * _VOYAGE_BOLD_DAY_MULT))
            d_b = min(d_b, max(1, d_c - 1))
        elif d_c >= 3:
            d_b = max(1, d_c - 1)
        roll = self._voyage_route_choice_roll(from_id, to_id)
        take_bold = roll > ra and d_b < d_c
        days_ch = d_c
        open_01 = _VOYAGE_COASTAL_OPENNESS
        label = "coastal"
        if take_bold:
            days_ch = d_b
            open_01 = clampf(1.0 - float(d_b) / float(max(d_c, 1)), 0.1, 0.95)
            label = "bold run"
        return {"days": days_ch, "open_01": open_01, "route_label": label}

    def _player_cargo_effective_used_units(self) -> int:
        row = self._player_ship_row()
        geff = max(0.5, float(row.get("grain_hold_efficiency", 1.0)))
        s = 0
        for gk, qv in self.player_cargo.items():
            q = max(0, int(qv))
            if str(gk) == "grain":
                s += int(math.ceil(float(q) / geff))
            else:
                s += q
        return s

    def _player_cargo_capacity_units(self) -> int:
        row = self._player_ship_row()
        per = clampi(int(row.get("cargo_per_hull", _FLEET_CARGO_PER_SHIP)), 1, 120)
        return per * clampi(int(self.player_fleet_ships), 1, _FLEET_MAX_SHIPS)

    def _player_trim_cargo_to_capacity(self) -> None:
        while self._player_cargo_effective_used_units() > self._player_cargo_capacity_units():
            worst_gid = ""
            worst_q = 0
            for gk, qv in list(self.player_cargo.items()):
                q = max(0, int(qv))
                if q > worst_q:
                    worst_q = q
                    worst_gid = str(gk)
            if not worst_gid or worst_q <= 0:
                break
            self._adjust_player_cargo_delta(worst_gid, -1)

    def _npc_trim_cargo_to_capacity(self, agent: dict) -> None:
        if "cargo" not in agent or not isinstance(agent["cargo"], dict):
            agent["cargo"] = {}
        cargo = agent["cargo"]
        while self._npc_cargo_effective_used_units(agent) > self._npc_cargo_capacity_units(agent):
            worst_gid = ""
            worst_q = 0
            for gk, qv in list(cargo.items()):
                q = max(0, int(qv))
                if q > worst_q:
                    worst_q = q
                    worst_gid = str(gk)
            if not worst_gid or worst_q <= 0:
                break
            self._npc_adjust_cargo(cargo, worst_gid, -1)

    def _tick_player_storm_if_at_sea(self) -> None:
        if int(self.player_voyage_days_remaining) <= 0:
            return
        d0 = max(1, int(self.player_voyage_booked_days))
        op = clampf(float(self.player_voyage_open_sea_01), 0.0, 1.0)
        row = self._player_ship_row()
        spm = clampf(float(row.get("storm_probability_mul", 1.0)), 0.35, 2.0)
        p = clampf(
            (
                _VOYAGE_STORM_BASE_P
                + _VOYAGE_STORM_PER_BOOKED_DAY * float(d0) / 24.0
                + _VOYAGE_STORM_OPEN_MULT * op
            )
            * spm,
            0.0,
            _VOYAGE_STORM_P_CAP,
        )
        doy_s = self._calendar_doy_1based()
        p = clampf(p * self._season_storm_probability_scale(doy_s), 0.0, _VOYAGE_STORM_P_CAP)
        if self.rng.random() >= p:
            return
        sdm = clampf(float(row.get("storm_damage_mul", 1.0)), 0.4, 2.2)
        age_f = 1.0 + _SHIP_AGE_STORM_DAMAGE_SCALE * self._player_age_stress_01()
        dmg = int(
            math.ceil(
                float(self.rng.randint(_VOYAGE_STORM_COND_DAMAGE_MIN, _VOYAGE_STORM_COND_DAMAGE_MAX))
                * sdm
                * age_f
            )
        )
        self.player_ship_condition = clampi(
            int(self.player_ship_condition) - dmg,
            _SHIP_CONDITION_MIN,
            _SHIP_CONDITION_MAX,
        )
        ships = clampi(int(self.player_fleet_ships), 1, _FLEET_MAX_SHIPS)
        if ships > 1 and self.rng.random() < _VOYAGE_STORM_HULL_LOSS_CHANCE:
            self.player_fleet_ships = max(1, ships - 1)
            self._player_trim_cargo_to_capacity()

    def _player_boarding_marine_qty_py(self) -> int:
        if "marines" not in self.goods:
            return 0
        return clampi(self._player_cargo_qty("marines"), 0, 9999)

    def _player_boarding_power_py(self) -> float:
        mar = self._player_boarding_marine_qty_py()
        row = self._player_ship_row()
        vm = clampf(float(row.get("voyage_day_mult", 1.0)), 0.55, 1.55)
        cat = str(row.get("category", "merchant"))
        hull_bonus = 4.0 if cat == "galley" else 0.0
        ex, neu = 0.5, 0.5
        return float(mar) * 2.35 + 8.0 + hull_bonus + (vm - 0.55) * 5.5 + ex * 2.8 + neu * 1.1

    def _pirate_npc_steal_from_player_py(self, pr: dict) -> str:
        purse_v = clampi(int(self.player_money), 0, _MAX_PURSE_COINS_PY)
        take_c = min(purse_v, max(6, int(round(float(purse_v) * 0.17))) + self.rng.randint(0, 28))
        take_c = min(take_c, purse_v)
        if take_c > 0:
            self.player_money = clampi(purse_v - take_c, 0, _MAX_PURSE_COINS_PY)
            pr["money"] = clampi(int(pr.get("money", 0)) + take_c, 0, _MAX_PURSE_COINS_PY)
        if "cargo" not in pr or not isinstance(pr["cargo"], dict):
            pr["cargo"] = {}
        p_cargo = pr["cargo"]
        stolen_bits: list[str] = []
        for _ in range(self.rng.randint(1, 3)):
            candidates = []
            for gid, qv in list(self.player_cargo.items()):
                gis = str(gid)
                if gis in ("grain", "marines") or gis not in self.goods:
                    continue
                qq = self._player_cargo_qty(gis)
                if qq <= 0:
                    continue
                up = max(1, int(self.goods[gis].get("unit_sell_price", 1)))
                candidates.append({"gid": gis, "w": float(qq * up)})
            if not candidates:
                break
            tw = sum(float(c.get("w", 1.0)) for c in candidates)
            x = self.rng.random() * tw
            pick_gid = ""
            for c2 in candidates:
                x -= float(c2.get("w", 1.0))
                if x <= 0.0:
                    pick_gid = str(c2.get("gid", ""))
                    break
            if not pick_gid:
                pick_gid = str(candidates[0].get("gid", ""))
            steal = self.rng.randint(1, 3)
            steal = min(steal, self._player_cargo_qty(pick_gid))
            if steal <= 0:
                continue
            self._adjust_player_cargo_delta(pick_gid, -steal)
            self._npc_adjust_cargo(p_cargo, pick_gid, steal)
            nm = str(self.goods.get(pick_gid, {}).get("name", pick_gid))
            stolen_bits.append(f"{nm}×{steal}")
        if take_c > 0 and not stolen_bits:
            return f"{take_c}c"
        if take_c > 0:
            return f"{take_c}c, {', '.join(stolen_bits)}"
        if stolen_bits:
            return ", ".join(stolen_bits)
        return ""

    def _player_apply_boarding_marine_loss_py(self, loss: int) -> None:
        if loss <= 0 or "marines" not in self.goods:
            return
        have = self._player_cargo_qty("marines")
        take = min(have, loss)
        if take > 0:
            self._adjust_player_cargo_delta("marines", -take)

    def _tick_player_pirate_encounter_if_at_sea(self) -> None:
        if int(self.player_voyage_days_remaining) <= 0:
            return
        if "marines" not in self.goods:
            return
        if str(self.player_voyage_role) != _VOYAGE_ROLE_MERCHANT:
            return
        rows = []
        dest_pl = str(self.player_voyage_dest_id or "")
        for pr in self.npc_agents:
            if not isinstance(pr, dict):
                continue
            if str(pr.get("voyage_role", "")) != _VOYAGE_ROLE_PIRATE:
                continue
            if int(pr.get("voyage_days_remaining", 0)) <= 0:
                continue
            w = 0.58
            if str(pr.get("voyage_dest_id", "")) == dest_pl:
                w += 2.1
            srow = self._npc_ship_row(pr)
            vm = clampf(float(srow.get("voyage_day_mult", 1.0)), 0.55, 1.55)
            w += (vm - 0.55) * 1.6
            op = clampf(
                0.5 * (float(self.player_voyage_open_sea_01) + float(pr.get("voyage_open_sea_01", 0.0))),
                0.0,
                1.0,
            )
            w *= 0.72 + op * 0.5
            rows.append({"ag": pr, "w": max(0.06, w)})
        if not rows:
            return
        pirate = self._npc_weighted_pick_agent(rows)
        if not pirate:
            return
        row_p = self._player_ship_row()
        vmin = clampf(float(row_p.get("voyage_day_mult", 1.0)), 0.55, 1.55)
        pm = clampf(float(self._npc_ship_row(pirate).get("voyage_day_mult", 1.0)), 0.55, 1.55)
        op2 = clampf(
            0.5 * (float(self.player_voyage_open_sea_01) + float(pirate.get("voyage_open_sea_01", 0.0))),
            0.0,
            1.0,
        )
        p_catch = clampf(
            _PLAYER_PIRATE_CATCH_BASE_P * (0.88 + (vmin - pm) * 0.48) * (0.64 + op2 * 0.48),
            0.01,
            0.40,
        )
        self.player_pirate_encounter_rolls += 1
        if self.rng.random() > p_catch:
            return
        p_player = self._player_boarding_power_py() + self.rng.random() * 10.0
        p_pir = self._npc_pirate_boarding_power(pirate) + self.rng.random() * 7.0
        if p_player >= p_pir * 0.92:
            hurt = self.rng.randint(2, 7)
            self._npc_pirate_apply_marine_losses(pirate, hurt)
            self.player_pirate_repelled += 1
            return
        loss_p = self.rng.randint(1, 5)
        self._player_apply_boarding_marine_loss_py(loss_p)
        self._pirate_npc_steal_from_player_py(pirate)
        pn0 = float(pirate.get("pirate_notoriety", 0.0))
        pirate["pirate_notoriety"] = clampf(pn0 + 2.5, 0.0, _PIRATE_NOTORIETY_CAP)
        self._npc_trim_cargo_to_capacity(pirate)
        self.player_pirate_hits += 1

    def _tick_npc_storms_at_sea(self) -> None:
        for ag in self.npc_agents:
            if not isinstance(ag, dict):
                continue
            days_left = int(ag.get("voyage_days_remaining", 0))
            if days_left <= 0:
                continue
            d0 = max(1, int(ag.get("voyage_booked_days", days_left)))
            op = clampf(float(ag.get("voyage_open_sea_01", _VOYAGE_COASTAL_OPENNESS)), 0.0, 1.0)
            self._ensure_npc_ship_fields(ag)
            srow = self._npc_ship_row(ag)
            spm2 = clampf(float(srow.get("storm_probability_mul", 1.0)), 0.35, 2.0)
            p = clampf(
                (
                    _VOYAGE_STORM_BASE_P
                    + _VOYAGE_STORM_PER_BOOKED_DAY * float(d0) / 24.0
                    + _VOYAGE_STORM_OPEN_MULT * op
                )
                * spm2,
                0.0,
                _VOYAGE_STORM_P_CAP,
            )
            doy_s = self._calendar_doy_1based()
            p = clampf(p * self._season_storm_probability_scale(doy_s), 0.0, _VOYAGE_STORM_P_CAP)
            if self.rng.random() >= p:
                continue
            cond0 = clampi(
                int(ag.get("ship_condition", _SHIP_CONDITION_MAX)),
                _SHIP_CONDITION_MIN,
                _SHIP_CONDITION_MAX,
            )
            sdm2 = clampf(float(srow.get("storm_damage_mul", 1.0)), 0.4, 2.2)
            dmg = max(
                1,
                int(
                    math.ceil(
                        float(self.rng.randint(_VOYAGE_STORM_COND_DAMAGE_MIN, _VOYAGE_STORM_COND_DAMAGE_MAX))
                        * sdm2
                    )
                ),
            )
            ag["ship_condition"] = clampi(cond0 - dmg, _SHIP_CONDITION_MIN, _SHIP_CONDITION_MAX)
            sh = clampi(int(ag.get("fleet_ships", 1)), 1, _FLEET_MAX_SHIPS)
            if sh > 1 and self.rng.random() < _VOYAGE_STORM_HULL_LOSS_CHANCE:
                ag["fleet_ships"] = max(1, sh - 1)
                self._npc_trim_cargo_to_capacity(ag)

    def _finalize_port_stocks(self) -> None:
        self.port_stocks.clear()
        for pid in self.port_order:
            row: dict[str, int] = {}
            init_d = self.port_initial_stock.get(pid, {})
            for gid in self.goods:
                if gid in init_d:
                    row[gid] = max(0, int(init_d[gid]))
                elif gid in ("gold", "silver"):
                    row[gid] = 0
                else:
                    row[gid] = _DEFAULT_STOCK_SLAVES if gid == "slaves" else _DEFAULT_STOCK_PER_GOOD
            self.port_stocks[pid] = row

    def _stock_target_for_good(self, good_id: str) -> int:
        g = self.goods.get(good_id)
        if not g:
            return 80
        return max(1, int(g["stock_target"]))

    def _port_stock_qty(self, port_id: str, good_id: str) -> int:
        p = self.port_stocks.get(port_id)
        if not p:
            return 0
        return max(0, int(p.get(good_id, 0)))

    def _adjust_port_stock(self, port_id: str, good_id: str, delta: int) -> None:
        q = self._port_stock_qty(port_id, good_id) + delta
        self.port_stocks.setdefault(port_id, {})
        self.port_stocks[port_id][good_id] = max(0, q)

    def get_grain_food_days_for_port(self, port_id: str) -> float:
        if "grain" not in self.goods:
            return 9999.0
        ps = str(port_id)
        if ps not in self.port_names:
            return 0.0
        eat = self.get_population_grain_eat_effective(ps)
        if eat <= 0:
            return 9999.0
        return float(self._port_stock_qty(ps, "grain")) / float(eat)

    def get_port_food_unrest(self, port_id: str) -> int:
        ps = str(port_id)
        if ps not in self.port_names:
            return 0
        return clampi(int(self.port_food_unrest.get(ps, 0)), 0, 200)

    def _need_tier_for_good(self, good_id: str) -> str:
        g = self.goods.get(good_id)
        if not g:
            return ""
        return str(g.get("need_tier", ""))

    def _port_wine_want_per_day(self, port_id: str) -> int:
        ps = str(port_id)
        if ps not in self.port_names:
            return 0
        w_base = int(self.port_population_wine_base.get(ps, 1))
        wealth = int(self.port_wealth.get(ps, 100))
        w_extra = clampi(int(float(wealth) / 95.0), 0, 14)
        return clampi(w_base + w_extra, 0, 50)

    def _wine_cover_days_for_port(self, port_id: str) -> float:
        if "wine" not in self.goods:
            return 9999.0
        want = self._port_wine_want_per_day(port_id)
        if want <= 0:
            return 9999.0
        return float(self._port_stock_qty(str(port_id), "wine")) / float(want)

    def _grain_shortfall_span(self, port_id: str) -> float:
        days = self.get_grain_food_days_for_port(port_id)
        if days >= 9000.0:
            return 0.0
        return max(0.0, _RESERVE_REF_GRAIN_DAYS - min(days, _RESERVE_REF_GRAIN_DAYS * 2.2))

    def _grain_reservation_pressure(self, port_id: str) -> float:
        span = self._grain_shortfall_span(port_id)
        return max(0.0, min(1.0, span / max(0.001, _RESERVE_REF_GRAIN_DAYS)))

    def _wine_reservation_pressure(self, port_id: str) -> float:
        if "wine" not in self.goods:
            return 0.0
        wdays = self._wine_cover_days_for_port(port_id)
        if wdays >= 9000.0:
            return 0.0
        span = max(0.0, _RESERVE_REF_WINE_DAYS - min(wdays, _RESERVE_REF_WINE_DAYS * 2.2))
        return max(0.0, min(1.0, span / max(0.001, _RESERVE_REF_WINE_DAYS)))

    @staticmethod
    def _smooth_reservation_addon(pressure_01: float, cap: float, k: float) -> float:
        if pressure_01 <= 0.0 or cap <= 0.0:
            return 0.0
        return cap * (1.0 - math.exp(-k * pressure_01))

    def _grain_food_unrest_addon(self, port_id: str, unrest_scale: float) -> float:
        u = float(self.get_port_food_unrest(port_id))
        return min(_RESERVE_STRESS_CAP * 0.5, u * _RESERVE_UNREST_PER_POINT * unrest_scale)

    def _grain_buy_reservation_total(self, port_id: str, player_counterparty: bool) -> float:
        p = self._grain_reservation_pressure(port_id)
        cap = _RESERVE_CURVE_CAP_GRAIN_BUY_PLAYER if player_counterparty else _RESERVE_CURVE_CAP_GRAIN_BUY_NPC
        k = _RESERVE_CURVE_K_PLAYER if player_counterparty else _RESERVE_CURVE_K_NPC
        curved = self._smooth_reservation_addon(p, cap, k)
        uadd = self._grain_food_unrest_addon(port_id, 1.0)
        return min(_RESERVE_STRESS_CAP, curved + uadd)

    def _grain_sell_reservation_total(self, port_id: str, player_counterparty: bool) -> float:
        p = self._grain_reservation_pressure(port_id)
        cap = _RESERVE_CURVE_CAP_GRAIN_SELL_PLAYER if player_counterparty else _RESERVE_CURVE_CAP_GRAIN_SELL_NPC
        k = _RESERVE_CURVE_K_PLAYER if player_counterparty else _RESERVE_CURVE_K_NPC
        curved = self._smooth_reservation_addon(p, cap, k)
        uadd = self._grain_food_unrest_addon(port_id, 1.05)
        return min(_RESERVE_STRESS_CAP, curved + uadd)

    def _wine_buy_reservation_total(self, port_id: str, player_counterparty: bool) -> float:
        p = self._wine_reservation_pressure(port_id)
        cap = _RESERVE_CURVE_CAP_WINE_PLAYER if player_counterparty else _RESERVE_CURVE_CAP_WINE_NPC
        k = _RESERVE_CURVE_K_PLAYER if player_counterparty else _RESERVE_CURVE_K_NPC
        return min(_RESERVE_STRESS_CAP * 0.88, self._smooth_reservation_addon(p, cap, k))

    def _port_avg_outbound_lane_days(self, port_id: str) -> float:
        neigh = self.port_neighbors.get(port_id) or []
        if not neigh:
            return 0.0
        s = 0.0
        n = 0
        for nb in neigh:
            d = int(self.lane_days.get(lane_key(port_id, str(nb)), -1))
            if d > 0:
                s += float(d)
                n += 1
        if n <= 0:
            return 0.0
        return s / float(n)

    def _layer_luxury_far_mult_for_port(self, port_id: str) -> float:
        ps = str(port_id)
        if ps not in self.port_names:
            return 1.0
        attract = max(1, self._wealth_stock_target_for_port(ps))
        wealth = max(1, int(self.port_wealth.get(ps, attract)))
        w_ex = max(0.0, min(2.5, float(wealth) / float(attract) - 1.0))
        from_wealth = min(_LUXURY_SPREAD_MAX, w_ex * _LUXURY_WEALTH_EXCESS_COEF)
        lanes = self._port_avg_outbound_lane_days(ps)
        lane_u = max(0.0, min(2.0, lanes / max(0.5, _FAR_TRADE_LANE_REF_DAYS)))
        from_lanes = min(_FAR_TRADE_SPREAD_MAX, lane_u * _FAR_TRADE_LANE_COEF)
        return 1.0 + min(_LUXURY_FAR_COMBINED_MAX, from_wealth + from_lanes)

    def _food_tier_stress_from_grain(self, port_id: str) -> float:
        if "grain" not in self.goods:
            return 0.0
        return self._grain_buy_reservation_total(port_id, True)

    def _comfort_tier_stress_from_wine(self, port_id: str) -> float:
        if "wine" not in self.goods:
            return 0.0
        return self._wine_buy_reservation_total(port_id, True)

    def _farm_wine_help_extra(self, port_id: str, already_helped: int) -> int:
        if "wine" not in self.goods:
            return 0
        room = max(0, _WINE_FARM_HELP_PORT_DAILY_CAP - already_helped)
        if room <= 0:
            return 0
        have = self._port_stock_qty(port_id, "wine")
        want = self._port_wine_want_per_day(port_id)
        if want <= 0:
            return min(room, _WINE_FARM_HELP_EMPTY) if have <= 0 else 0
        if have <= 0:
            need_empty = max(_WINE_FARM_HELP_EMPTY, min(9, want // 2 + 2))
            return min(room, need_empty)
        low_line = clampi(want * 2, 8, 48)
        if have < low_line:
            return min(room, max(_WINE_FARM_HELP_LOW, want // 6 + 1))
        return 0

    def _replenish_wine_vineyards_after_bites(self) -> None:
        if "wine" not in self.goods:
            return
        if not self._is_harvest_doy(self._calendar_doy_1based()):
            return
        vine_yield: dict[str, int] = {}
        for fd in self.farms:
            pid = str(fd.get("port_id", ""))
            if not pid or pid not in self.port_names:
                continue
            wv = max(0, int(fd.get("wine_per_day", 0)))
            if wv <= 0:
                continue
            vine_yield[pid] = int(vine_yield.get(pid, 0)) + wv
        for pid, sumw in vine_yield.items():
            if self._port_stock_qty(pid, "wine") > 0:
                continue
            want = self._port_wine_want_per_day(pid)
            bump = clampi(sumw + want // 4, 5, 18)
            self._adjust_port_stock(pid, "wine", bump)

    def _metal_tier_stress_from_food(self, port_id: str) -> float:
        if "grain" not in self.goods:
            return 0.0
        fg = self._food_tier_stress_from_grain(port_id)
        return min(_RESERVE_STRESS_CAP * 0.92, fg * _RESERVE_METAL_FROM_FOOD_STRESS)

    def _war_metal_reservation_addon(self, port_id: str) -> float:
        if not self.is_port_at_war(port_id):
            return 0.0
        return float(_WAR_METAL_DEMAND_STRESS)

    def _war_metal_loss_qty(self, port_id: str) -> int:
        if not self.is_port_at_war(port_id) or "metal" not in self.goods:
            return 0
        ps = str(port_id)
        eat = int(self.port_population_grain.get(ps, 0))
        stock = self._port_stock_qty(ps, "metal")
        line = clampi(
            _WAR_MATERIEL_METAL_BASE + (eat * _WAR_MATERIEL_METAL_LINEAR) // 5,
            _WAR_MATERIEL_METAL_BASE,
            _WAR_MATERIEL_METAL_MAX,
        )
        skim = min(
            _WAR_MATERIEL_METAL_STOCK_SKIM_MAX,
            stock // max(1, _WAR_MATERIEL_METAL_STOCK_SKIM_DIV),
        )
        return min(_WAR_MATERIEL_DAILY_HARD_CAP, line + skim)

    def _war_wire_loss_qty(self, port_id: str) -> int:
        if not self.is_port_at_war(port_id) or "wire" not in self.goods:
            return 0
        ps = str(port_id)
        eat = int(self.port_population_grain.get(ps, 0))
        stock = self._port_stock_qty(ps, "wire")
        line = clampi(
            _WAR_MATERIEL_WIRE_BASE + eat // max(1, _WAR_MATERIEL_WIRE_LINEAR_DIV),
            _WAR_MATERIEL_WIRE_BASE,
            _WAR_MATERIEL_WIRE_MAX,
        )
        skim = min(
            _WAR_MATERIEL_WIRE_STOCK_SKIM_MAX,
            stock // max(1, _WAR_MATERIEL_WIRE_STOCK_SKIM_DIV),
        )
        return min(_WAR_MATERIEL_DAILY_HARD_CAP, line + skim)

    def _apply_war_materiel_consumption(self) -> None:
        for pid in self.port_order:
            ps = str(pid)
            if not self.is_port_at_war(ps):
                continue
            want_m = self._war_metal_loss_qty(ps)
            want_w = self._war_wire_loss_qty(ps)
            take_m = min(want_m, self._port_stock_qty(ps, "metal")) if want_m > 0 else 0
            take_w = min(want_w, self._port_stock_qty(ps, "wire")) if want_w > 0 else 0
            if take_m > 0:
                self._adjust_port_stock(ps, "metal", -take_m)
            if take_w > 0:
                self._adjust_port_stock(ps, "wire", -take_w)
            if take_m > 0 or take_w > 0:
                self.last_war_industry_digest[ps] = {"metal": take_m, "wire": take_w}

    def _apply_industrial_metal_sinks(self) -> None:
        for pid in self.port_order:
            ps = str(pid)
            want_m = int(self.port_industrial_metal_per_day.get(ps, 0))
            want_w = int(self.port_industrial_wire_per_day.get(ps, 0))
            want_t = int(self.port_industrial_timber_per_day.get(ps, 0))
            want_x = int(self.port_industrial_textiles_per_day.get(ps, 0))
            take_m = 0
            take_w = 0
            take_t = 0
            take_x = 0
            if want_m > 0 and "metal" in self.goods:
                take_m = min(want_m, self._port_stock_qty(ps, "metal"))
                if take_m > 0:
                    self._adjust_port_stock(ps, "metal", -take_m)
            if want_w > 0 and "wire" in self.goods:
                take_w = min(want_w, self._port_stock_qty(ps, "wire"))
                if take_w > 0:
                    self._adjust_port_stock(ps, "wire", -take_w)
            if want_t > 0 and "timber" in self.goods:
                take_t = min(want_t, self._port_stock_qty(ps, "timber"))
                if take_t > 0:
                    self._adjust_port_stock(ps, "timber", -take_t)
            if want_x > 0 and "textiles" in self.goods:
                take_x = min(want_x, self._port_stock_qty(ps, "textiles"))
                if take_x > 0:
                    self._adjust_port_stock(ps, "textiles", -take_x)
            if take_m > 0 or take_w > 0 or take_t > 0 or take_x > 0:
                self.last_industrial_sink_digest[ps] = {
                    "metal": take_m,
                    "wire": take_w,
                    "timber": take_t,
                    "textiles": take_x,
                }

    def _need_mult_player_buys_from_port(self, port_id: str, good_id: str, player_counterparty: bool = True) -> float:
        tier = self._need_tier_for_good(good_id)
        if tier == "food" and good_id == "grain":
            return 1.0 + self._grain_buy_reservation_total(port_id, player_counterparty)
        if tier == "comfort" and good_id == "wine":
            return 1.0 + self._wine_buy_reservation_total(port_id, player_counterparty)
        if tier == "metal" and good_id in ("metal", "wire"):
            food_m = self._metal_tier_stress_from_food(port_id)
            war_m = self._war_metal_reservation_addon(port_id)
            return 1.0 + min(_WAR_METAL_RESERVE_CAP, food_m + war_m)
        return 1.0

    def _need_mult_player_sells_to_port(self, port_id: str, good_id: str, player_counterparty: bool = True) -> float:
        tier = self._need_tier_for_good(good_id)
        if tier == "food" and good_id == "grain":
            return 1.0 + self._grain_sell_reservation_total(port_id, player_counterparty)
        if tier == "comfort" and good_id == "wine":
            mult = 1.0 + self._wine_buy_reservation_total(port_id, player_counterparty)
            gd = self.get_grain_food_days_for_port(port_id)
            if gd < 9000.0 and gd < 1.05:
                trim = max(0.0, min(1.0, (1.05 - gd) / 1.05)) * _RESERVE_COMFORT_GRAIN_TIGHT
                mult *= max(0.72, 1.0 - trim)
            return mult
        if tier == "metal" and good_id in ("metal", "wire"):
            food_m2 = self._metal_tier_stress_from_food(port_id)
            war_m2 = self._war_metal_reservation_addon(port_id)
            return 1.0 + min(_RESERVE_STRESS_CAP * 0.88 + 0.1, food_m2 * 1.02 + war_m2 * 0.92)
        return 1.0

    def _goods_default_market_velocity_demand(self, good_id: str) -> float:
        gd = self.goods.get(good_id)
        if not gd:
            return 0.22
        if "market_demand_per_day" in gd:
            return max(0.0, float(gd["market_demand_per_day"]))
        tgt = float(self._stock_target_for_good(good_id))
        return max(0.1, tgt * 0.034)

    def _estimated_farm_supply_per_day(self, port_id: str, good_id: str) -> float:
        ps = str(port_id)
        farm_mult = _WAR_FARM_OUTPUT_MULT if self.is_port_at_war(ps) else 1.0
        pop_sc = self._population_output_scale_for_port(ps)
        slave_sc = self._port_slave_output_mult(ps)
        raw = 0.0
        for fd in self.farms:
            if str(fd.get("port_id", "")) != ps:
                continue
            if good_id == "grain":
                raw += float(fd.get("grain_per_day", 0))
            elif good_id == "wine":
                raw += float(fd.get("wine_per_day", 0))
            elif good_id == "fish":
                raw += float(fd.get("fish_per_day", 0))
        return raw * farm_mult * pop_sc * slave_sc

    def _estimated_mine_supply_per_day(self, port_id: str, good_id: str) -> float:
        ps = str(port_id)
        pop_sc = self._population_output_scale_for_port(ps)
        slave_sc = self._port_slave_output_mult(ps)
        raw = 0.0
        for md in self.mines:
            if str(md.get("port_id", "")) != ps:
                continue
            if good_id == "metal":
                raw += float(md.get("metal_per_day", 0))
            elif good_id == "wire":
                raw += float(md.get("wire_per_day", 0))
            elif good_id == "gold":
                raw += float(md.get("gold_per_day", 0))
            elif good_id == "silver":
                raw += float(md.get("silver_per_day", 0))
        return raw * pop_sc * slave_sc

    def _port_structural_demand_per_day(self, port_id: str, good_id: str) -> float:
        ps = str(port_id)
        if good_id == "grain":
            eat = float(self.get_population_grain_eat_effective(ps))
            ghave = self._port_stock_qty(ps, "grain")
            spoil = 0.0
            if ghave > _GRAIN_SPOIL_MIN_STOCK:
                spoil = min(float(_GRAIN_SPOIL_CAP), float(ghave) * _GRAIN_SPOIL_FRACTION)
            return eat + spoil
        if good_id == "wine":
            return float(self._port_wine_want_per_day(ps))
        if good_id == "fish":
            return float(clampi(int(self.port_population_fish_per_day.get(ps, 0)), 0, 40))
        if good_id == "metal":
            dm = float(int(self.port_industrial_metal_per_day.get(ps, 0)))
            if self.is_port_at_war(ps) and "metal" in self.goods:
                dm += float(self._war_metal_loss_qty(ps))
            return max(dm, self._goods_default_market_velocity_demand("metal"))
        if good_id == "wire":
            dw = float(int(self.port_industrial_wire_per_day.get(ps, 0)))
            if self.is_port_at_war(ps) and "wire" in self.goods:
                dw += float(self._war_wire_loss_qty(ps))
            return max(dw, self._goods_default_market_velocity_demand("wire"))
        if good_id == "timber":
            ind_t = float(int(self.port_industrial_timber_per_day.get(ps, 0)))
            return max(ind_t, self._goods_default_market_velocity_demand("timber"))
        if good_id == "textiles":
            ind_x = float(int(self.port_industrial_textiles_per_day.get(ps, 0)))
            return max(ind_x, self._goods_default_market_velocity_demand("textiles"))
        if good_id == "gold":
            gdm = 0.0
            cg = self.port_mint_cfg.get(ps)
            if isinstance(cg, dict):
                gpb = clampi(int(cg.get("gold_per_batch", 0)), 0, 24)
                mxb = clampi(int(cg.get("max_batches_per_day", 0)), 0, 40)
                if gpb > 0 and mxb > 0:
                    gdm = float(gpb * mxb) * 0.32
            return max(gdm, self._goods_default_market_velocity_demand("gold"))
        if good_id == "silver":
            sdm = 0.0
            cg2 = self.port_mint_cfg.get(ps)
            if isinstance(cg2, dict):
                spb = clampi(int(cg2.get("silver_per_batch", 0)), 0, 36)
                mxb2 = clampi(int(cg2.get("max_batches_per_day", 0)), 0, 40)
                if spb > 0 and mxb2 > 0:
                    sdm = float(spb * mxb2) * 0.32
            return max(sdm, self._goods_default_market_velocity_demand("silver"))
        return self._goods_default_market_velocity_demand(good_id)

    def _port_resolved_market_demand_per_day(self, port_id: str, good_id: str) -> float:
        ps = str(port_id)
        od = self.port_market_demand_override.get(ps)
        if isinstance(od, dict) and good_id in od:
            return max(0.0, float(od[good_id]))
        return self._port_structural_demand_per_day(ps, good_id)

    def _port_structural_supply_per_day(self, port_id: str, good_id: str) -> float:
        if good_id in ("grain", "wine", "fish"):
            return self._estimated_farm_supply_per_day(port_id, good_id)
        if good_id in ("metal", "wire", "gold", "silver"):
            return self._estimated_mine_supply_per_day(port_id, good_id)
        return 0.0

    def _market_demand_supply_mult_for_port_good(self, port_id: str, good_id: str) -> float:
        ps = str(port_id)
        if ps not in self.port_names or good_id not in self.goods:
            return 1.0
        d_day = self._port_resolved_market_demand_per_day(ps, good_id)
        s_day = self._port_structural_supply_per_day(ps, good_id)
        stock = float(self._port_stock_qty(ps, good_id))
        need = max(1.0, d_day * _MARKET_HORIZON_DAYS)
        stock_pressure = clampf((need - stock) / need, -1.35, 1.35)
        if d_day >= 0.35:
            flow_pressure = clampf((d_day - s_day) / d_day, -1.2, 1.2)
        elif s_day >= 0.5:
            flow_pressure = clampf(-s_day / max(1.0, s_day), -1.0, 0.0)
        else:
            flow_pressure = 0.0
        adj = clampf(
            _MARKET_STOCK_PRESSURE_WEIGHT * stock_pressure + _MARKET_FLOW_PRESSURE_WEIGHT * flow_pressure,
            -_MARKET_PRESSURE_ABS_MAX,
            _MARKET_PRESSURE_ABS_MAX,
        )
        return clampf(1.0 + adj, _MARKET_PRICE_MULT_MIN, _MARKET_PRICE_MULT_MAX)

    def _port_trade_price_bias_mult(self, port_id: str, good_id: str) -> float:
        ps = str(port_id)
        gid = str(good_id)
        row = self.port_trade_price_bias.get(ps)
        if not isinstance(row, dict):
            if gid == "grain" and self._world_crop_agro_model and "grain" in self.goods:
                return clampf(1.0 + self._crop_phase2_grain_trade_bias_add(ps), 0.62, 1.55)
            return 1.0
        if gid not in row:
            if gid == "grain" and self._world_crop_agro_model and "grain" in self.goods:
                return clampf(1.0 + self._crop_phase2_grain_trade_bias_add(ps), 0.62, 1.55)
            return 1.0
        b = float(row[gid])
        if gid == "grain" and self._world_crop_agro_model and "grain" in self.goods:
            b += self._crop_phase2_grain_trade_bias_add(ps)
        return clampf(1.0 + b, 0.62, 1.55)

    def _compute_player_buy_unit(self, port_id: str, good_id: str, player_counterparty: bool = True) -> int:
        gd = self.goods.get(good_id)
        if not gd:
            return 1
        base = max(1, int(gd["unit_buy_price"]))
        target = self._stock_target_for_good(good_id)
        stock = self._port_stock_qty(port_id, good_id)
        t = float(max(1, target))
        skew = max(-1.0, min(2.0, (float(target) - float(stock)) / t))
        mult = 1.0 + skew * 0.58
        tier = self._need_tier_for_good(good_id)
        mult *= self._need_mult_player_buys_from_port(port_id, good_id, player_counterparty)
        if tier == "luxury":
            mult *= self._layer_luxury_far_mult_for_port(port_id)
        mult *= self._market_demand_supply_mult_for_port_good(port_id, good_id)
        mult *= self._port_trade_price_bias_mult(port_id, good_id)
        mult *= self._rumor_price_mult_for_port_good(port_id, good_id)
        if good_id == "grain":
            mult *= self._crop_grain_buy_price_stress_mult(port_id)
        return max(1, int(round(float(base) * mult)))

    def _compute_player_sell_unit(self, port_id: str, good_id: str, player_counterparty: bool = True) -> int:
        gd = self.goods.get(good_id)
        if not gd:
            return 1
        base = max(1, int(gd["unit_sell_price"]))
        target = self._stock_target_for_good(good_id)
        stock = self._port_stock_qty(port_id, good_id)
        t = float(max(1, target))
        skew = max(-1.5, min(2.0, (float(stock) - float(target)) / t))
        mult = 1.0 - skew * 0.38
        tier = self._need_tier_for_good(good_id)
        mult *= self._need_mult_player_sells_to_port(port_id, good_id, player_counterparty)
        if tier == "luxury":
            mult *= self._layer_luxury_far_mult_for_port(port_id)
        mult *= self._market_demand_supply_mult_for_port_good(port_id, good_id)
        mult *= self._port_trade_price_bias_mult(port_id, good_id)
        mult *= self._rumor_price_mult_for_port_good(port_id, good_id)
        if good_id == "grain":
            mult *= self._crop_grain_sell_price_stress_mult(port_id)
        return max(1, int(round(float(base) * mult)))

    def _wealth_stock_target_value(self, port_id: str) -> float:
        # Bullion intentionally excluded from this attractor (port stock != municipal prosperity)—do not re-linearize; keep in sync with game_state.gd.
        g = float(self._port_stock_qty(port_id, "grain"))
        w = float(self._port_stock_qty(port_id, "wine"))
        mt = float(self._port_stock_qty(port_id, "metal")) if "metal" in self.goods else 0.0
        wr = float(self._port_stock_qty(port_id, "wire")) if "wire" in self.goods else 0.0
        sa = float(self._port_stock_qty(port_id, "salt")) if "salt" in self.goods else 0.0
        oo = float(self._port_stock_qty(port_id, "olive_oil")) if "olive_oil" in self.goods else 0.0
        po = float(self._port_stock_qty(port_id, "pottery")) if "pottery" in self.goods else 0.0
        sp = float(self._port_stock_qty(port_id, "spice")) if "spice" in self.goods else 0.0
        sl = float(self._port_stock_qty(port_id, "slaves")) if "slaves" in self.goods else 0.0
        fi = float(self._port_stock_qty(port_id, "fish")) if "fish" in self.goods else 0.0
        tb = float(self._port_stock_qty(port_id, "timber")) if "timber" in self.goods else 0.0
        tx = float(self._port_stock_qty(port_id, "textiles")) if "textiles" in self.goods else 0.0
        rb = float(max(0, int(self.port_role_wealth_bonus.get(port_id, 0))))
        target = (
            45.0
            + rb
            + g * 0.19
            + w * 0.5
            + sa * 0.09
            + oo * 0.2
            + po * 0.14
            + fi * 0.11
            + tb * 0.1
            + tx * 0.13
            + mt * 0.11
            + wr * 0.07
            + sp * 0.35
            + sl * 0.06
        )
        pulse = clampf(float(self.port_commerce_pulse.get(port_id, 0.38)), 0.0, 1.0)
        target *= _wealth_target_commerce_scale_py(pulse)
        if clampi(int(self.port_plague_days.get(port_id, 0)), 0, 999) > 0:
            target *= _PLAGUE_TARGET_MULT
        return max(35.0, min(8000.0, target))

    def _wealth_stock_target_for_port(self, port_id: str) -> int:
        return int(round(self._wealth_stock_target_value(port_id)))

    def _refresh_port_wealth(self, port_id: str) -> None:
        target = self._wealth_stock_target_value(port_id)
        cur = float(int(self.port_wealth.get(port_id, int(round(target)))))
        nxt = cur + (target - cur) * _WEALTH_LERP
        self.port_wealth[port_id] = clampi(int(round(nxt)), 25, 999999)

    def _bump_port_wealth(self, port_id: str, delta: int) -> None:
        if delta == 0 or port_id not in self.port_names:
            return
        v = int(self.port_wealth.get(port_id, 200)) + delta
        self.port_wealth[port_id] = clampi(v, 10, 999999)

    def _init_port_wealth_baseline(self) -> None:
        self.port_wealth.clear()
        for pid in self.port_order:
            if pid in self.port_initial_wealth:
                self.port_wealth[pid] = clampi(int(self.port_initial_wealth[pid]), 20, 8000)
            else:
                g = self._port_stock_qty(pid, "grain")
                w = self._port_stock_qty(pid, "wine")
                mt0 = self._port_stock_qty(pid, "metal") if "metal" in self.goods else 0
                wr0 = self._port_stock_qty(pid, "wire") if "wire" in self.goods else 0
                sa0 = self._port_stock_qty(pid, "salt") if "salt" in self.goods else 0
                oo0 = self._port_stock_qty(pid, "olive_oil") if "olive_oil" in self.goods else 0
                po0 = self._port_stock_qty(pid, "pottery") if "pottery" in self.goods else 0
                fi0 = self._port_stock_qty(pid, "fish") if "fish" in self.goods else 0
                tb0 = self._port_stock_qty(pid, "timber") if "timber" in self.goods else 0
                tx0 = self._port_stock_qty(pid, "textiles") if "textiles" in self.goods else 0
                self.port_wealth[pid] = clampi(
                    int(
                        50.0
                        + float(g) * 0.22
                        + float(w) * 0.55
                        + float(sa0) * 0.1
                        + float(oo0) * 0.22
                        + float(po0) * 0.16
                        + float(fi0) * 0.12
                        + float(tb0) * 0.11
                        + float(tx0) * 0.14
                        + float(mt0) * 0.12
                        + float(wr0) * 0.08
                    ),
                    40,
                    4000,
                )

    def _random_npc_starting_cargo(self) -> dict[str, int]:
        cargo: dict[str, int] = {}
        for gid in self.goods:
            if gid == "grain":
                cargo[gid] = self.rng.randint(2, 10)
            elif gid == "wine":
                cargo[gid] = self.rng.randint(0, 7)
            elif gid in ("metal", "wire"):
                cargo[gid] = self.rng.randint(0, 4)
            elif gid in ("gold", "silver"):
                cargo[gid] = self.rng.randint(0, 1) if self.rng.random() < 0.14 else 0
            elif gid == "slaves":
                cargo[gid] = self.rng.randint(0, 2)
            elif gid == "marines":
                cargo[gid] = self.rng.randint(0, 2)
            else:
                cargo[gid] = self.rng.randint(0, 4)
        return cargo

    def _ensure_npc_ship_fields(self, ag: dict) -> None:
        if "ship_condition" not in ag:
            ag["ship_condition"] = _SHIP_CONDITION_MAX
        else:
            ag["ship_condition"] = clampi(
                int(ag.get("ship_condition", _SHIP_CONDITION_MAX)),
                _SHIP_CONDITION_MIN,
                _SHIP_CONDITION_MAX,
            )
        if "ship_wine_counter" not in ag:
            ag["ship_wine_counter"] = 0
        else:
            ag["ship_wine_counter"] = clampi(int(ag.get("ship_wine_counter", 0)), 0, 9999)
        if "fleet_ships" not in ag:
            ag["fleet_ships"] = 1
        else:
            ag["fleet_ships"] = clampi(int(ag.get("fleet_ships", 1)), 1, _FLEET_MAX_SHIPS)
        if "fleet_shipyard_days" not in ag:
            ag["fleet_shipyard_days"] = 0
        else:
            ag["fleet_shipyard_days"] = clampi(int(ag.get("fleet_shipyard_days", 0)), 0, 999)
        yp = str(ag.get("fleet_shipyard_port_id", ""))
        if int(ag.get("fleet_shipyard_days", 0)) <= 0 or not yp or yp not in self.port_names:
            ag["fleet_shipyard_port_id"] = ""
        else:
            ag["fleet_shipyard_port_id"] = yp
        vdays = int(ag.get("voyage_days_remaining", 0))
        if vdays > 0:
            if "voyage_booked_days" not in ag:
                ag["voyage_booked_days"] = max(1, vdays)
            else:
                ag["voyage_booked_days"] = clampi(int(ag.get("voyage_booked_days", 0)), 1, 999)
            ag["voyage_open_sea_01"] = clampf(
                float(ag.get("voyage_open_sea_01", _VOYAGE_COASTAL_OPENNESS)), 0.0, 1.0
            )
        else:
            ag["voyage_booked_days"] = 0
            ag["voyage_open_sea_01"] = 0.0
        hp0 = str(ag.get("home_port", ""))
        if "ship_class_id" not in ag or not str(ag.get("ship_class_id", "")).strip():
            ag["ship_class_id"] = self._default_ship_class_for_port(hp0 if hp0 in self.port_names else (self.port_order[0] if self.port_order else ""))
        elif str(ag.get("ship_class_id", "")) not in self._ship_classes:
            ag["ship_class_id"] = self._default_ship_class_for_port(hp0 if hp0 in self.port_names else (self.port_order[0] if self.port_order else ""))
        if "captain_culture" not in ag or not str(ag.get("captain_culture", "")).strip():
            ag["captain_culture"] = str(self._port_cultures.get(hp0, "greek"))
        self._ensure_npc_voyage_role_and_contract(ag)
        self._ensure_npc_convoy_fields(ag)
        if "voyage_origin_port_id" not in ag:
            ag["voyage_origin_port_id"] = ""
        else:
            ag["voyage_origin_port_id"] = str(ag.get("voyage_origin_port_id") or "")
        if "crop_stress_belief_01" not in ag:
            ag["crop_stress_belief_01"] = 0.0
        else:
            ag["crop_stress_belief_01"] = clampf(float(ag.get("crop_stress_belief_01", 0.0)), 0.0, 1.0)

    def _rookie_try_charter_cheapest_used_hull_from_slip(self, agent: dict, home_port: str) -> None:
        hp = str(home_port)
        if hp not in self.port_names:
            return
        if self.rng.uniform(0.0, 1.0) > _ROOKIE_BANKRUPTCY_USED_HULL_CHANCE:
            return
        arr = self._used_hull_listings_array(hp)
        if not arr:
            return
        best_i = -1
        best_ask = 999999999
        best_cond = _SHIP_CONDITION_MAX
        for idx, c0 in enumerate(arr):
            if not isinstance(c0, dict):
                continue
            ak = int(c0.get("ask", 999999999))
            if ak < best_ask:
                best_ask = ak
                best_i = idx
                best_cond = clampi(int(c0.get("condition", _SHIP_CONDITION_MAX)), _SHIP_CONDITION_MIN, _SHIP_CONDITION_MAX)
        if best_i < 0 or best_ask >= 999999000:
            return
        del arr[best_i]
        self.port_used_hull_listings[hp] = arr
        agent["ship_condition"] = best_cond
        self._bump_port_wealth(hp, -max(1, best_ask // _ROOKIE_USED_HULL_CHARTER_WEALTH_DIV))

    def _new_npc_agent(
        self, home_port: str, bankruptcy_replacement: bool = False, inherit_trade: dict | None = None
    ) -> dict:
        sk1 = self._roll_npc_trade_skills()
        if inherit_trade:
            pb = clampf(float(inherit_trade.get("buy", 1.0)), _NPC_MASTER_MIN, _NPC_MASTER_MAX)
            psb = clampf(float(inherit_trade.get("sell", 1.0)), _NPC_MASTER_MIN, _NPC_MASTER_MAX)
            sk1["buy"] = clampf(0.42 * sk1["buy"] + 0.58 * pb, _NPC_MASTER_MIN, _NPC_MASTER_MAX)
            sk1["sell"] = clampf(0.42 * sk1["sell"] + 0.58 * psb, _NPC_MASTER_MIN, _NPC_MASTER_MAX)
        pmn = _NPC_START_MONEY_MIN
        pmx = _NPC_START_MONEY_MAX
        purse_want = self.rng.randint(
            min(pmn, pmx),
            max(pmn, pmx),
        )
        from_t = min(purse_want, self.world_treasury_coins)
        self.world_treasury_coins = clampi(self.world_treasury_coins - from_t, 0, _WORLD_TREASURY_MAX)
        ag = {
            "id": self.npc_next_id,
            "home_port": home_port,
            "docked_port": home_port,
            "voyage_dest_id": "",
            "voyage_days_remaining": 0,
            "cargo": self._random_npc_starting_cargo(),
            "money": purse_want,
            "buy_mastery": sk1["buy"],
            "sell_mastery": sk1["sell"],
            "ship_condition": _SHIP_CONDITION_MAX,
            "ship_wine_counter": 0,
            "fleet_ships": 1,
            "fleet_shipyard_days": 0,
            "fleet_shipyard_port_id": "",
            "purse_bust_streak": 0,
            "price_memory": {},
            "risk_aversion": self.rng.uniform(0.08, 0.92),
            "voyage_booked_days": 0,
            "voyage_open_sea_01": 0.0,
            "ship_class_id": self._default_ship_class_for_port(home_port),
            "captain_culture": str(self._port_cultures.get(home_port, "greek")),
            "voyage_role": _VOYAGE_ROLE_MERCHANT,
            "escort_contract": {},
            "convoy_leader_id": 0,
            "convoy_member_ids": [],
            "convoy_formed": False,
            "convoy_escort_id": 0,
            "convoy_escort_player": False,
            "scattered_ids": [],
            "contact_candidate_bias": 0.0,
            "escort_reliability": 0.55,
            "pirate_notoriety": 0.0,
            "npc_peer_debts": [],
            "voyage_origin_port_id": "",
            "crop_stress_belief_01": 0.0,
            "merchant_season_ticks": 0,
            "merchant_repute_01": clampf(0.46 + 0.26 * float(self.npc_next_id % 991) / 991.0, 0.0, 1.0),
            "npc_city_trust_01": {},
            "city_grain_contract": {},
        }
        for kb, vb in self._roll_npc_big_five().items():
            ag[kb] = vb
        self._ensure_npc_ship_fields(ag)
        self.npc_next_id += 1
        if bankruptcy_replacement:
            self._rookie_try_charter_cheapest_used_hull_from_slip(ag, home_port)
        return ag

    def _bootstrap_npc_agents(self) -> None:
        self.npc_agents.clear()
        self.npc_next_id = 0
        for pid in self.port_order:
            n = clampi(int(self.port_npc_trader_count.get(pid, 4)), 1, _PORT_NPC_TRADERS_LOAD_MAX)
            for _ in range(n):
                self.npc_agents.append(self._new_npc_agent(pid))

    def _npc_cargo_qty(self, cargo: dict, good_id: str) -> int:
        return max(0, int(cargo.get(good_id, 0)))

    def _npc_adjust_cargo(self, cargo: dict, good_id: str, delta: int) -> None:
        q = self._npc_cargo_qty(cargo, good_id) + delta
        if q <= 0:
            cargo.pop(good_id, None)
        else:
            cargo[good_id] = q

    def _ensure_npc_money_field(self, agent: dict) -> None:
        if "money" not in agent:
            agent["money"] = _default_npc_money_from_seed(int(agent.get("id", 0)))
        else:
            agent["money"] = clampi(int(agent.get("money", 0)), 0, _MAX_PURSE_COINS_PY)
        self._normalize_npc_trade_skills(agent)
        self._ensure_npc_ship_fields(agent)
        if "purse_bust_streak" not in agent:
            agent["purse_bust_streak"] = 0
        else:
            agent["purse_bust_streak"] = clampi(int(agent.get("purse_bust_streak", 0)), 0, 999)
        pm = agent.get("price_memory")
        if not isinstance(pm, dict):
            agent["price_memory"] = {}
        else:
            agent["price_memory"] = self._sanitize_price_memory(pm)
        self._ensure_npc_risk_aversion(agent)
        self._ensure_npc_big_five(agent)
        self._ensure_npc_escort_reputation_fields(agent)
        self._sanitize_npc_peer_debts(agent)
        if "pirate_notoriety" not in agent:
            agent["pirate_notoriety"] = 0.0
        else:
            try:
                agent["pirate_notoriety"] = clampf(float(agent.get("pirate_notoriety", 0.0)), 0.0, _PIRATE_NOTORIETY_CAP)
            except (TypeError, ValueError):
                agent["pirate_notoriety"] = 0.0
        self._ensure_npc_merchant_contract_fields(agent)

    def _ensure_npc_merchant_contract_fields(self, ag: dict) -> None:
        if "merchant_repute_01" not in ag:
            sid = int(ag.get("id", 0))
            ag["merchant_repute_01"] = clampf(0.48 + 0.22 * float(sid % 997) / 997.0, 0.0, 1.0)
        else:
            try:
                ag["merchant_repute_01"] = clampf(float(ag.get("merchant_repute_01", 0.52)), 0.0, 1.0)
            except (TypeError, ValueError):
                ag["merchant_repute_01"] = 0.52
        ct0 = ag.get("npc_city_trust_01")
        if not isinstance(ct0, dict):
            ag["npc_city_trust_01"] = {}
        else:
            cto: dict[str, float] = {}
            for pk, pv in ct0.items():
                pxs = str(pk)
                if pxs not in self.port_names:
                    continue
                try:
                    cto[pxs] = clampf(float(pv), 0.0, 1.0)
                except (TypeError, ValueError):
                    continue
            ag["npc_city_trust_01"] = cto
        self._npc_prune_npc_city_trust_dict(ag)
        cg0 = ag.get("city_grain_contract")
        if not isinstance(cg0, dict):
            ag["city_grain_contract"] = {}
        else:
            iss = str(cg0.get("issuer", ""))
            dst = str(cg0.get("dest", ""))
            qty = clampi(int(cg0.get("qty", 0)), 0, 999)
            due = clampi(int(cg0.get("due", 0)), 0, 9999999)
            adv = clampi(int(cg0.get("advance", 0)), 0, _MAX_PURSE_COINS_PY)
            if (
                not iss
                or iss not in self.port_names
                or not dst
                or dst not in self.port_names
                or iss == dst
                or qty < _NPC_CITY_GRAIN_CONTRACT_QTY_MIN
                or "grain" not in self.goods
            ):
                ag["city_grain_contract"] = {}
            else:
                ag["city_grain_contract"] = {
                    "issuer": iss,
                    "dest": dst,
                    "good": "grain",
                    "qty": qty,
                    "due": due,
                    "advance": adv,
                }

    def _npc_prune_npc_city_trust_dict(self, ag: dict) -> None:
        m = ag.get("npc_city_trust_01")
        if not isinstance(m, dict):
            ag["npc_city_trust_01"] = {}
            return
        if len(m) <= _NPC_CITY_TRUST_PORT_MAX_KEYS:
            return
        scored = sorted(
            ((str(k), clampf(float(v), 0.0, 1.0)) for k, v in m.items() if str(k) in self.port_names),
            key=lambda t: t[1],
        )
        drop = len(m) - _NPC_CITY_TRUST_PORT_MAX_KEYS
        for i in range(min(drop, len(scored))):
            ek = scored[i][0]
            if ek:
                m.pop(ek, None)
        ag["npc_city_trust_01"] = m

    def _npc_city_trust_get(self, ag: dict, port_id: str) -> float:
        ps = str(port_id)
        if ps not in self.port_names:
            return 0.5
        m = ag.get("npc_city_trust_01")
        if isinstance(m, dict) and ps in m:
            try:
                return clampf(float(m[ps]), 0.0, 1.0)
            except (TypeError, ValueError):
                pass
        try:
            return clampf(float(ag.get("merchant_repute_01", 0.52)), 0.0, 1.0)
        except (TypeError, ValueError):
            return 0.52

    def _npc_city_trust_bump(self, ag: dict, port_id: str, delta: float) -> None:
        ps = str(port_id)
        if ps not in self.port_names:
            return
        m = dict(ag.get("npc_city_trust_01") or {})
        cur = self._npc_city_trust_get(ag, ps)
        m[ps] = clampf(cur + delta, 0.0, 1.0)
        ag["npc_city_trust_01"] = m
        self._npc_prune_npc_city_trust_dict(ag)

    def _npc_city_grain_contract_active(self, ag: dict) -> bool:
        cg = ag.get("city_grain_contract")
        if not isinstance(cg, dict) or not cg:
            return False
        iss = str(cg.get("issuer", ""))
        dst = str(cg.get("dest", ""))
        return iss in self.port_names and dst in self.port_names and iss != dst

    def _npc_clear_city_grain_contract(self, ag: dict) -> None:
        ag["city_grain_contract"] = {}

    def _npc_depart_dest_contract_bias(self, ag: dict, here: str, dest: str) -> str:
        if not self._world_npc_city_grain_contracts_enabled:
            return dest
        if not self._npc_city_grain_contract_active(ag):
            return dest
        cg = ag.get("city_grain_contract")
        if not isinstance(cg, dict):
            return dest
        cdest = str(cg.get("dest", ""))
        due = clampi(int(cg.get("due", 0)), 0, 9999999)
        if not cdest or cdest not in self.port_names or cdest == here:
            return dest
        if dest == cdest:
            return dest
        try:
            rep = clampf(float(ag.get("merchant_repute_01", 0.52)), 0.0, 1.0)
        except (TypeError, ValueError):
            rep = 0.52
        consc = self._npc_trait_f(ag, _NPC_TRAIT_CONSC)
        extra = self._npc_trait_f(ag, _NPC_TRAIT_EXTRA)
        p_stick = 0.18 + 0.48 * rep + 0.22 * consc - 0.12 * extra
        slack = due - int(self.current_day)
        if slack <= 14:
            p_stick += 0.20
        if slack <= 7:
            p_stick += 0.14
        plan = self._voyage_plan(here, cdest, clampf(float(ag.get("risk_aversion", 0.5)), 0.0, 1.0), True)
        est_d = max(1, int(plan.get("days", 4)))
        if slack <= est_d + 2:
            p_stick += 0.12
        p_stick = clampf(p_stick, 0.06, 0.91)
        if self.rng.random() < p_stick:
            return cdest
        return dest

    def _npc_try_fulfill_city_grain_contract_on_arrival(self, ag: dict, dest: str) -> None:
        if not self._npc_city_grain_contract_active(ag):
            return
        cg = ag.get("city_grain_contract")
        if not isinstance(cg, dict) or str(cg.get("dest", "")) != str(dest):
            return
        cr = ag.get("cargo")
        if not isinstance(cr, dict):
            return
        need = clampi(int(cg.get("qty", 0)), 1, 999)
        have = self._npc_cargo_qty(cr, "grain")
        if have < need:
            return
        iss = str(cg.get("issuer", ""))
        self._npc_adjust_cargo(cr, "grain", -need)
        self._adjust_port_stock(dest, "grain", need)
        bonus = clampi(6 + need // 2, 4, 48)
        ag["money"] = clampi(int(ag.get("money", 0)) + bonus, 0, _MAX_PURSE_COINS_PY)
        self._bump_port_wealth(dest, max(1, bonus // 3))
        try:
            ag["merchant_repute_01"] = clampf(float(ag.get("merchant_repute_01", 0.5)) + 0.028, 0.0, 1.0)
        except (TypeError, ValueError):
            ag["merchant_repute_01"] = 0.55
        self._npc_city_trust_bump(ag, iss, 0.045)
        self._npc_city_trust_bump(ag, dest, 0.022)
        self.npc_city_grain_contracts_fulfilled += 1
        self._npc_clear_city_grain_contract(ag)

    def _npc_city_grain_contract_breach(self, ag: dict, issuer: str) -> None:
        iss = str(issuer)
        if iss not in self.port_names:
            self._npc_clear_city_grain_contract(ag)
            return
        cg = ag.get("city_grain_contract")
        adv = clampi(int((cg or {}).get("advance", 0)), 0, _MAX_PURSE_COINS_PY) if isinstance(cg, dict) else 0
        fine = clampi(int(math.ceil(float(max(adv, 12)) * 1.25)), 0, _MAX_PURSE_COINS_PY)
        purse = clampi(int(ag.get("money", 0)), 0, _MAX_PURSE_COINS_PY)
        take = min(fine, purse)
        ag["money"] = purse - take
        if take > 0:
            self._bump_port_wealth(iss, max(1, take // 4))
        try:
            ag["merchant_repute_01"] = clampf(float(ag.get("merchant_repute_01", 0.5)) - 0.05, 0.0, 1.0)
        except (TypeError, ValueError):
            ag["merchant_repute_01"] = 0.45
        self._npc_city_trust_bump(ag, iss, -0.14)
        self.npc_city_grain_contracts_breached += 1
        self._npc_clear_city_grain_contract(ag)

    def _npc_tick_merchant_city_contracts_docked(self) -> None:
        for ag in self.npc_agents:
            if not isinstance(ag, dict):
                continue
            if str(ag.get("voyage_role", _VOYAGE_ROLE_MERCHANT)) != _VOYAGE_ROLE_MERCHANT:
                continue
            if int(ag.get("voyage_days_remaining", 0)) != 0:
                continue
            if not self._npc_city_grain_contract_active(ag):
                continue
            cg = ag.get("city_grain_contract")
            if not isinstance(cg, dict):
                continue
            due = clampi(int(cg.get("due", 0)), 0, 9999999)
            if int(self.current_day) <= due:
                continue
            iss = str(cg.get("issuer", ""))
            dst = str(cg.get("dest", ""))
            need = clampi(int(cg.get("qty", 0)), 1, 999)
            cr = ag.get("cargo")
            if not isinstance(cr, dict):
                self._npc_city_grain_contract_breach(ag, iss)
                continue
            have = self._npc_cargo_qty(cr, "grain")
            dp = str(ag.get("docked_port", ""))
            if dp == dst and have >= need:
                self._npc_try_fulfill_city_grain_contract_on_arrival(ag, dst)
            else:
                self._npc_city_grain_contract_breach(ag, iss)

    def _npc_try_offer_city_grain_contract(self, agent: dict, dock_pid: str) -> None:
        if not self._world_npc_city_grain_contracts_enabled:
            return
        if "grain" not in self.goods:
            return
        if self._npc_convoy_is_follower(agent) or bool(agent.get("convoy_formed", False)):
            return
        if str(agent.get("voyage_role", _VOYAGE_ROLE_MERCHANT)) != _VOYAGE_ROLE_MERCHANT:
            return
        if int(agent.get("voyage_days_remaining", 0)) != 0:
            return
        if self._npc_city_grain_contract_active(agent):
            return
        ps = str(dock_pid)
        if ps not in self.port_names:
            return
        try:
            rep = clampf(float(agent.get("merchant_repute_01", 0.52)), 0.0, 1.0)
        except (TypeError, ValueError):
            rep = 0.52
        p_offer = clampf(_NPC_CITY_GRAIN_CONTRACT_OFFER_P * (0.78 + (1.12 - 0.78) * rep), 0.012, 0.068)
        if self.rng.random() > p_offer:
            return
        opts = [str(p) for p in self.port_order if str(p) != ps]
        if not opts:
            return
        dest = str(opts[self.rng.randint(0, len(opts) - 1)])
        if dest not in self.port_names:
            return
        qty = self.rng.randint(_NPC_CITY_GRAIN_CONTRACT_QTY_MIN, _NPC_CITY_GRAIN_CONTRACT_QTY_MAX)
        if self._port_stock_qty(ps, "grain") < qty:
            return
        due = int(self.current_day) + self.rng.randint(
            _NPC_CITY_GRAIN_CONTRACT_DUE_MIN, _NPC_CITY_GRAIN_CONTRACT_DUE_MAX
        )
        tr_iss = self._npc_city_trust_get(agent, ps)
        agree = self._npc_trait_f(agent, _NPC_TRAIT_AGREE)
        consc = self._npc_trait_f(agent, _NPC_TRAIT_CONSC)
        neuro = self._npc_trait_f(agent, _NPC_TRAIT_NEURO)
        p_accept = clampf(0.22 + 0.55 * rep + 0.18 * tr_iss + 0.12 * agree + 0.10 * consc - 0.08 * neuro, 0.08, 0.92)
        if self.rng.random() > p_accept:
            return
        advance = clampi(int(12.0 + float(qty) * 2.1 + 70.0 * rep + 40.0 * tr_iss), 10, 160)
        pw = clampi(int(self.port_wealth.get(ps, 100)), 0, 999999)
        if pw < advance // 2:
            return
        self.port_wealth[ps] = clampi(pw - advance // 2, 0, 999999)
        trsy = clampi(int(math.floor(float(advance) * _NPC_CITY_CONTRACT_TREASURY_FRAC)), 0, _WORLD_TREASURY_MAX)
        self.world_treasury_coins = clampi(self.world_treasury_coins + trsy, 0, _WORLD_TREASURY_MAX)
        agent["money"] = clampi(int(agent.get("money", 0)) + advance, 0, _MAX_PURSE_COINS_PY)
        agent["city_grain_contract"] = {
            "issuer": ps,
            "dest": dest,
            "good": "grain",
            "qty": qty,
            "due": due,
            "advance": advance,
        }
        self.npc_city_grain_contracts_signed += 1

    def _is_valid_voyage_role_py(self, role: str) -> bool:
        r = str(role)
        return r in (_VOYAGE_ROLE_MERCHANT, _VOYAGE_ROLE_ESCORT, _VOYAGE_ROLE_PIRATE)

    def _sanitize_escort_contract_py(self, raw: dict) -> dict:
        if not isinstance(raw, dict):
            return {}
        eid = int(raw.get("employer_id", -1))
        o0 = str(raw.get("origin", ""))
        d0 = str(raw.get("dest", ""))
        return {
            "employer_id": clampi(eid, -1, 999999),
            "pay_coins": clampi(int(raw.get("pay_coins", 0)), 0, _MAX_PURSE_COINS_PY),
            "origin": o0 if o0 in self.port_names else "",
            "dest": d0 if d0 in self.port_names else "",
            "started_day": clampi(int(raw.get("started_day", 0)), 0, 9999999),
        }

    def _ensure_npc_voyage_role_and_contract(self, ag: dict) -> None:
        r0 = str(ag.get("voyage_role", _VOYAGE_ROLE_MERCHANT))
        ag["voyage_role"] = r0 if self._is_valid_voyage_role_py(r0) else _VOYAGE_ROLE_MERCHANT
        cr = ag.get("escort_contract")
        if not isinstance(cr, dict):
            ag["escort_contract"] = {}
        else:
            ag["escort_contract"] = self._sanitize_escort_contract_py(cr)
        if str(ag.get("voyage_role", "")) != _VOYAGE_ROLE_ESCORT:
            ag["escort_contract"].clear()

    def _ensure_player_voyage_role_and_contract_py(self) -> None:
        r0 = str(self.player_voyage_role)
        self.player_voyage_role = r0 if self._is_valid_voyage_role_py(r0) else _VOYAGE_ROLE_MERCHANT
        if not isinstance(self.player_escort_contract, dict):
            self.player_escort_contract = {}
        else:
            self.player_escort_contract = self._sanitize_escort_contract_py(self.player_escort_contract)
        if self.player_voyage_role != _VOYAGE_ROLE_ESCORT:
            self.player_escort_contract.clear()

    def _apply_player_escort_contract_on_voyage_arrival_py(self) -> None:
        self.player_escort_contract.clear()
        if self.player_voyage_role == _VOYAGE_ROLE_ESCORT:
            self.player_voyage_role = _VOYAGE_ROLE_MERCHANT

    def _apply_npc_escort_contract_on_voyage_arrival(self, ag: dict) -> None:
        if isinstance(ag.get("escort_contract"), dict):
            ag["escort_contract"].clear()
        else:
            ag["escort_contract"] = {}
        if str(ag.get("voyage_role", _VOYAGE_ROLE_MERCHANT)) == _VOYAGE_ROLE_ESCORT:
            ag["voyage_role"] = _VOYAGE_ROLE_MERCHANT

    def _ensure_npc_convoy_fields(self, ag: dict) -> None:
        ag.setdefault("convoy_leader_id", 0)
        ag["convoy_leader_id"] = max(0, int(ag.get("convoy_leader_id", 0)))
        mids = ag.get("convoy_member_ids")
        if not isinstance(mids, list):
            ag["convoy_member_ids"] = []
        else:
            out_m = []
            seen = set()
            for it in mids:
                mid = int(it)
                if mid <= 0 or mid in seen:
                    continue
                seen.add(mid)
                out_m.append(mid)
                if len(out_m) >= 8:
                    break
            ag["convoy_member_ids"] = out_m
        scat = ag.get("scattered_ids")
        if not isinstance(scat, list):
            ag["scattered_ids"] = []
        else:
            out_s = []
            seen2 = set()
            for it2 in scat:
                sid = int(it2)
                if sid <= 0 or sid in seen2:
                    continue
                seen2.add(sid)
                out_s.append(sid)
                if len(out_s) >= 16:
                    break
            ag["scattered_ids"] = out_s
        ag["convoy_formed"] = bool(ag.get("convoy_formed", False))
        ag.setdefault("convoy_escort_id", 0)
        ag["convoy_escort_id"] = max(0, int(ag.get("convoy_escort_id", 0)))
        ag.setdefault("convoy_escort_player", False)
        ag["convoy_escort_player"] = bool(ag.get("convoy_escort_player", False))
        if ag["convoy_escort_player"]:
            ag["convoy_escort_id"] = 0
        elif int(ag.get("convoy_escort_id", 0)) > 0:
            ag["convoy_escort_player"] = False
        try:
            ag["contact_candidate_bias"] = clampf(float(ag.get("contact_candidate_bias", 0.0)), 0.0, 1.0)
        except (TypeError, ValueError):
            ag["contact_candidate_bias"] = 0.0

    def _ensure_npc_escort_reputation_fields(self, ag: dict) -> None:
        if "escort_reliability" not in ag:
            ag["escort_reliability"] = 0.55
        else:
            try:
                ag["escort_reliability"] = clampf(float(ag.get("escort_reliability", 0.55)), 0.0, 1.0)
            except (TypeError, ValueError):
                ag["escort_reliability"] = 0.55

    def _npc_convoy_is_follower(self, ag: dict) -> bool:
        self_id = int(ag.get("id", 0))
        cl = int(ag.get("convoy_leader_id", 0))
        return cl > 0 and cl != self_id

    def _npc_index_agents_by_id(self) -> dict:
        return {int(ag.get("id", -1)): ag for ag in self.npc_agents if isinstance(ag, dict)}

    def _npc_convoy_reset_docked(self, ag: dict) -> None:
        ag["convoy_leader_id"] = 0
        ag["convoy_member_ids"] = []
        ag["convoy_formed"] = False
        ag["convoy_escort_id"] = 0
        ag["convoy_escort_player"] = False
        ag["scattered_ids"] = []
        ag["contact_candidate_bias"] = 0.0

    def _npc_convoy_fixup_removed_agent_id(self, dead_id: int) -> None:
        if dead_id <= 0:
            return
        for ag in self.npc_agents:
            if not isinstance(ag, dict):
                continue
            if int(ag.get("convoy_escort_id", 0)) == dead_id:
                ag["convoy_escort_id"] = 0
            if int(ag.get("convoy_leader_id", 0)) == dead_id:
                ag["convoy_leader_id"] = 0
                ag["convoy_member_ids"] = []
                ag["convoy_formed"] = False
            mm = ag.get("convoy_member_ids")
            if not isinstance(mm, list) or not mm:
                continue
            nm = [int(x) for x in mm if int(x) != dead_id]
            ag["convoy_member_ids"] = nm
            if not nm and int(ag.get("convoy_leader_id", 0)) == int(ag.get("id", 0)):
                ag["convoy_formed"] = False
        if str(self.player_voyage_role) == _VOYAGE_ROLE_ESCORT:
            emdead = int(self.player_escort_contract.get("employer_id", -9))
            if emdead == dead_id:
                self.player_escort_contract.clear()
                self.player_voyage_role = _VOYAGE_ROLE_MERCHANT

    def _normalize_npc_convoy_invariants_py(self, ag: dict) -> None:
        self._ensure_npc_convoy_fields(ag)
        vdays = int(ag.get("voyage_days_remaining", 0))
        self_id = int(ag.get("id", 0))
        cl = int(ag.get("convoy_leader_id", 0))
        if vdays <= 0:
            self._npc_convoy_reset_docked(ag)
            return
        dest_me = str(ag.get("voyage_dest_id", ""))
        idx = self._npc_index_agents_by_id()
        if cl == self_id:
            mids = ag.get("convoy_member_ids")
            if not isinstance(mids, list) or not mids:
                ag["convoy_formed"] = False
                ag["convoy_leader_id"] = 0
                ag["convoy_escort_id"] = 0
                ag["convoy_escort_player"] = False
                return
            keep = []
            for it in mids:
                mid = int(it)
                if mid == self_id:
                    continue
                oth = idx.get(mid)
                if not isinstance(oth, dict):
                    continue
                if (
                    self._npc_convoy_is_follower(oth)
                    and int(oth.get("convoy_leader_id", 0)) == self_id
                    and str(oth.get("voyage_dest_id", "")) == dest_me
                    and int(oth.get("voyage_days_remaining", 0)) > 0
                ):
                    keep.append(mid)
            ag["convoy_member_ids"] = keep
            if not keep:
                ag["convoy_formed"] = False
                ag["convoy_leader_id"] = 0
                ag["convoy_escort_id"] = 0
                ag["convoy_escort_player"] = False
                return
            es0 = int(ag.get("convoy_escort_id", 0))
            esc_pl = bool(ag.get("convoy_escort_player", False))
            if esc_pl:
                ok_p = (
                    str(self.player_voyage_role) == _VOYAGE_ROLE_ESCORT
                    and int(self.player_escort_contract.get("employer_id", -9)) == self_id
                    and str(self.player_voyage_dest_id or "") == dest_me
                    and int(self.player_voyage_days_remaining) > 0
                )
                if not ok_p:
                    ag["convoy_escort_player"] = False
            elif es0 > 0:
                if es0 not in idx:
                    ag["convoy_escort_id"] = 0
                else:
                    ex = idx[es0]
                    if not isinstance(ex, dict):
                        ag["convoy_escort_id"] = 0
                    else:
                        ok_es = (
                            str(ex.get("voyage_role", "")) == _VOYAGE_ROLE_ESCORT
                            and int(ex.get("convoy_leader_id", 0)) == self_id
                            and str(ex.get("voyage_dest_id", "")) == dest_me
                            and int(ex.get("voyage_days_remaining", 0)) > 0
                        )
                        if not ok_es:
                            ag["convoy_escort_id"] = 0
            return
        if cl > 0 and cl != self_id:
            L = idx.get(cl)
            ok = False
            if isinstance(L, dict):
                if (
                    int(L.get("voyage_days_remaining", 0)) > 0
                    and str(L.get("voyage_dest_id", "")) == dest_me
                    and int(L.get("convoy_leader_id", 0)) == cl
                ):
                    ok = True
            if not ok:
                ag["convoy_leader_id"] = 0
                ag["convoy_member_ids"] = []
                ag["convoy_formed"] = False
                if str(ag.get("voyage_role", "")) == _VOYAGE_ROLE_ESCORT:
                    self._apply_npc_escort_contract_on_voyage_arrival(ag)

    def _npc_voyage_facing_params(self, agent: dict, here: str, dest: str) -> dict:
        if not here or not dest or here not in self.port_names or dest not in self.port_names:
            return {}
        self._ensure_npc_risk_aversion(agent)
        plan = self._voyage_plan(here, dest, clampf(float(agent.get("risk_aversion", 0.5)), 0.0, 1.0), True)
        d = int(plan.get("days", -1))
        if d < 0:
            return {}
        self._ensure_npc_ship_fields(agent)
        nrow = self._npc_ship_row(agent)
        nvm = clampf(float(nrow.get("voyage_day_mult", 1.0)), 0.45, 2.2)
        d = max(1, int(math.ceil(float(d) * nvm)))
        nop0 = clampf(float(plan.get("open_01", _VOYAGE_COASTAL_OPENNESS)), 0.0, 1.0)
        nox = clampf(float(nrow.get("open_sea_exposure_mul", 1.0)), 0.55, 1.5)
        open_01 = clampf(nop0 * nox, 0.0, 1.0)
        return {"days": d, "open_01": open_01}

    def _npc_convoy_join_roll(self, leader: dict, member: dict, _dest: str, route_open_01: float) -> bool:
        p = 0.38
        if str(leader.get("home_port", "")) == str(member.get("home_port", "")):
            p += 0.14
        if str(leader.get("captain_culture", "")) == str(member.get("captain_culture", "")):
            p += 0.10
        a = 0.5 * (self._npc_trait_f(leader, _NPC_TRAIT_AGREE) + self._npc_trait_f(member, _NPC_TRAIT_AGREE))
        p += 0.18 * (a - 0.5)
        nmem = self._npc_trait_f(member, _NPC_TRAIT_NEURO)
        p *= 1.0 - 0.28 * route_open_01 * nmem
        p = clampf(p, 0.06, 0.92)
        return self.rng.random() < p

    def _npc_escort_candidate_hull(self, agent: dict) -> bool:
        self._ensure_npc_ship_fields(agent)
        nrow = self._npc_ship_row(agent)
        cat = str(nrow.get("category", "")).lower()
        if cat == "galley":
            return True
        vm = clampf(float(nrow.get("voyage_day_mult", 1.0)), 0.45, 2.2)
        return vm <= _ESCORT_HULL_FAST_VOYAGE_MULT

    def _npc_escort_job_pay_offer(self, days: int, open_01: float) -> int:
        raw = _ESCORT_PAY_BASE + days * _ESCORT_PAY_PER_DAY + int(round(float(_ESCORT_PAY_OPEN_MUL) * open_01))
        raw_s = raw
        return clampi(
            raw_s,
            _ESCORT_PAY_MIN,
            _ESCORT_PAY_MAX,
        )

    def _npc_escort_accept_job_roll(self, escort_candidate: dict, pay_coins: int, route_open_01: float) -> bool:
        p = 0.18 + float(pay_coins) / 620.0
        if self._npc_escort_candidate_hull(escort_candidate):
            p += 0.10
        exv = self._npc_trait_f(escort_candidate, _NPC_TRAIT_EXTRA)
        agr = self._npc_trait_f(escort_candidate, _NPC_TRAIT_AGREE)
        neu = self._npc_trait_f(escort_candidate, _NPC_TRAIT_NEURO)
        p += 0.12 * (exv - 0.5) + 0.10 * (agr - 0.5)
        p -= 0.20 * route_open_01 * neu
        p = clampf(p, 0.04, 0.82)
        return self.rng.random() < p

    def _player_escort_traits_dummy_for_roll_py(self) -> dict:
        return {
            _NPC_TRAIT_OPEN: 0.52,
            _NPC_TRAIT_CONSC: 0.52,
            _NPC_TRAIT_EXTRA: 0.52,
            _NPC_TRAIT_AGREE: 0.52,
            _NPC_TRAIT_NEURO: 0.52,
        }

    def _player_escort_candidate_hull_py(self) -> bool:
        nrow = self._player_ship_row()
        cat = str(nrow.get("category", "")).lower()
        if cat == "galley":
            return True
        vm = clampf(float(nrow.get("voyage_day_mult", 1.0)), 0.45, 2.2)
        return vm <= _ESCORT_HULL_FAST_VOYAGE_MULT

    def _player_try_hire_as_convoy_escort_py(
        self, leader: dict, here: str, dest: str, d_max: int, op_max: float, pay_paid: int
    ) -> None:
        if not self.player_offers_convoy_escort:
            return
        if str(self.player_voyage_role) != _VOYAGE_ROLE_MERCHANT:
            return
        if int(self.player_voyage_days_remaining) != 0:
            return
        if str(self.player_port_id) != here:
            return
        if not self._player_escort_candidate_hull_py():
            return
        if not self._npc_escort_accept_job_roll(self._player_escort_traits_dummy_for_roll_py(), pay_paid, op_max):
            return
        lid = int(leader.get("id", 0))
        if lid <= 0:
            return
        self._ensure_npc_convoy_fields(leader)
        leader["convoy_escort_id"] = 0
        leader["convoy_escort_player"] = True
        self.player_voyage_role = _VOYAGE_ROLE_ESCORT
        self.player_escort_contract = self._sanitize_escort_contract_py(
            {
                "employer_id": lid,
                "pay_coins": pay_paid,
                "origin": here,
                "dest": dest,
                "started_day": int(self.current_day),
            }
        )
        self.player_voyage_dest_id = dest
        self.player_voyage_days_remaining = d_max
        self.player_voyage_booked_days = d_max
        self.player_voyage_open_sea_01 = op_max

    def _player_escort_pay_on_convoy_arrival_py(self, employer: dict) -> int:
        if str(self.player_voyage_role) != _VOYAGE_ROLE_ESCORT:
            return 0
        ct = self.player_escort_contract
        if not isinstance(ct, dict):
            return 0
        if int(ct.get("employer_id", -2)) != int(employer.get("id", -3)):
            return 0
        promised = clampi(int(ct.get("pay_coins", 0)), 0, _ESCORT_PAY_MAX)
        if promised <= 0:
            return 0
        ep = clampi(int(employer.get("money", 0)), 0, _MAX_PURSE_COINS_PY)
        paid = min(promised, ep)
        if paid <= 0:
            return 0
        employer["money"] = clampi(ep - paid, 0, _MAX_PURSE_COINS_PY)
        self.player_money = clampi(int(self.player_money) + paid, 0, _MAX_PURSE_COINS_PY)
        self.escort_coins_paid += paid
        return paid

    def _player_finish_escort_on_npc_convoy_arrival_py(self, employer: dict, dest: str) -> None:
        _ = employer
        self.player_voyage_days_remaining = 0
        self.player_voyage_dest_id = ""
        self.player_voyage_booked_days = 0
        self.player_voyage_open_sea_01 = 0.0
        if dest in self.port_names:
            self.player_port_id = dest
        self._apply_player_escort_contract_on_voyage_arrival_py()

    def _player_escort_combat_flee_py(self, leader: dict) -> None:
        leader["convoy_escort_id"] = 0
        leader["convoy_escort_player"] = False
        self.player_escort_contract.clear()
        self.player_voyage_role = _VOYAGE_ROLE_MERCHANT
        self.pirate_escort_flees += 1

    def _sync_player_escort_with_employer_after_npc_advance_py(self) -> None:
        if str(self.player_voyage_role) != _VOYAGE_ROLE_ESCORT:
            return
        if int(self.player_voyage_days_remaining) <= 0:
            return
        eid = int(self.player_escort_contract.get("employer_id", -9))
        if eid <= 0:
            self._apply_player_escort_contract_on_voyage_arrival_py()
            return
        idxe = self._npc_index_agents_by_id()
        if eid not in idxe:
            self._apply_player_escort_contract_on_voyage_arrival_py()
            return
        boss = idxe[eid]
        if not isinstance(boss, dict) or not bool(boss.get("convoy_escort_player", False)):
            self._apply_player_escort_contract_on_voyage_arrival_py()
            return
        bd = int(boss.get("voyage_days_remaining", 0))
        dst = str(boss.get("voyage_dest_id", ""))
        self.player_voyage_days_remaining = max(0, bd)
        self.player_voyage_dest_id = dst
        self.player_voyage_booked_days = int(boss.get("voyage_booked_days", bd))
        self.player_voyage_open_sea_01 = clampf(float(boss.get("voyage_open_sea_01", 0.0)), 0.0, 1.0)

    def _npc_try_hire_escort_for_convoy(
        self, leader: dict, follower_ids: list, here: str, dest: str, d_max: int, op_max: float
    ) -> None:
        self._ensure_npc_convoy_fields(leader)
        leader["convoy_escort_id"] = 0
        leader["convoy_escort_player"] = False
        if not follower_ids:
            return
        lid = int(leader.get("id", 0))
        excluded = {lid: True}
        for it in follower_ids:
            excluded[int(it)] = True
        pay_want = self._npc_escort_job_pay_offer(d_max, op_max)
        purse = clampi(int(leader.get("money", 0)), 0, _MAX_PURSE_COINS_PY)
        reserve = min(
            48,
            max(12, self._npc_officer_due_coins(leader)),
        )
        pay_paid = clampi(
            min(pay_want, purse - reserve),
            _ESCORT_PAY_MIN,
            _ESCORT_PAY_MAX,
        )
        if pay_paid < _ESCORT_PAY_MIN or purse < pay_paid + reserve:
            return
        cands = []
        for c in self.npc_agents:
            if not isinstance(c, dict):
                continue
            cid = int(c.get("id", 0))
            if cid in excluded or cid == lid:
                continue
            if int(c.get("voyage_days_remaining", 0)) != 0:
                continue
            if str(c.get("docked_port", "")) != here:
                continue
            if str(c.get("voyage_role", _VOYAGE_ROLE_MERCHANT)) != _VOYAGE_ROLE_MERCHANT:
                continue
            if not self._npc_escort_candidate_hull(c):
                continue
            cands.append(c)
        for si in range(len(cands) - 1, 0, -1):
            ji = self.rng.randint(0, si)
            cands[si], cands[ji] = cands[ji], cands[si]
        for cand in cands:
            if not self._npc_escort_accept_job_roll(cand, pay_paid, op_max):
                continue
            esc = cand
            self._ensure_npc_escort_reputation_fields(esc)
            esc["voyage_role"] = _VOYAGE_ROLE_ESCORT
            esc["escort_contract"] = self._sanitize_escort_contract_py(
                {
                    "employer_id": lid,
                    "pay_coins": pay_paid,
                    "origin": here,
                    "dest": dest,
                    "started_day": int(self.current_day),
                }
            )
            self._ensure_npc_convoy_fields(esc)
            esc["convoy_leader_id"] = lid
            esc["convoy_member_ids"] = []
            esc["convoy_formed"] = True
            esc["scattered_ids"] = []
            esc["contact_candidate_bias"] = 0.0
            esc["voyage_dest_id"] = dest
            esc["voyage_days_remaining"] = d_max
            esc["voyage_booked_days"] = d_max
            esc["voyage_open_sea_01"] = op_max
            esc["docked_port"] = ""
            leader["convoy_escort_id"] = int(esc.get("id", 0))
            leader["convoy_escort_player"] = False
            return
        self._player_try_hire_as_convoy_escort_py(leader, here, dest, d_max, op_max, pay_paid)

    def _npc_escort_reliability_apply(self, escort: dict, full_pay: bool, promised_pay: int) -> None:
        self._ensure_npc_escort_reputation_fields(escort)
        try:
            r = float(escort.get("escort_reliability", 0.55))
        except (TypeError, ValueError):
            r = 0.55
        if full_pay and promised_pay > 0:
            r = clampf(r + 0.035, 0.0, 1.0)
        elif promised_pay > 0:
            r = clampf(r - 0.028, 0.0, 1.0)
        else:
            r = clampf(r - 0.06, 0.0, 1.0)
        escort["escort_reliability"] = r

    def _npc_escort_pay_on_convoy_arrival(self, employer: dict, escort: dict) -> int:
        if str(escort.get("voyage_role", "")) != _VOYAGE_ROLE_ESCORT:
            return 0
        ct = escort.get("escort_contract")
        if not isinstance(ct, dict):
            return 0
        if int(ct.get("employer_id", -2)) != int(employer.get("id", -3)):
            return 0
        promised = clampi(int(ct.get("pay_coins", 0)), 0, _ESCORT_PAY_MAX)
        if promised <= 0:
            return 0
        ep = clampi(int(employer.get("money", 0)), 0, _MAX_PURSE_COINS_PY)
        paid = min(promised, ep)
        if paid <= 0:
            self._npc_escort_reliability_apply(escort, False, promised)
            return 0
        employer["money"] = clampi(ep - paid, 0, _MAX_PURSE_COINS_PY)
        escort["money"] = clampi(int(escort.get("money", 0)) + paid, 0, _MAX_PURSE_COINS_PY)
        self._npc_escort_reliability_apply(escort, paid >= promised, promised)
        self.escort_coins_paid += paid
        return paid

    def _npc_finish_npc_voyage_arrival(self, ag: dict, dest: str) -> None:
        self._npc_apply_crop_information_on_arrival(ag, dest)
        ag["voyage_dest_id"] = ""
        ag["voyage_days_remaining"] = 0
        ag["voyage_booked_days"] = 0
        ag["voyage_open_sea_01"] = 0.0
        if dest in self.port_names:
            ag["docked_port"] = dest
        else:
            home = str(ag.get("home_port", ""))
            if home in self.port_names:
                ag["docked_port"] = home
            elif self.port_order:
                ag["docked_port"] = str(self.port_order[0])
            else:
                ag["docked_port"] = ""
        self._apply_npc_escort_contract_on_voyage_arrival(ag)
        self._npc_convoy_reset_docked(ag)
        self._npc_try_fulfill_city_grain_contract_on_arrival(ag, dest)

    def _npc_depart_solo_merchant(self, agent: dict, here: str, dest: str) -> None:
        vf = self._npc_voyage_facing_params(agent, here, dest)
        if not vf:
            return
        d = int(vf.get("days", 1))
        op = float(vf.get("open_01", _VOYAGE_COASTAL_OPENNESS))
        self._ensure_npc_convoy_fields(agent)
        agent["convoy_leader_id"] = 0
        agent["convoy_member_ids"] = []
        agent["convoy_formed"] = False
        agent["convoy_escort_id"] = 0
        agent["convoy_escort_player"] = False
        agent["scattered_ids"] = []
        agent["contact_candidate_bias"] = 0.0
        agent["voyage_dest_id"] = dest
        agent["voyage_days_remaining"] = d
        agent["voyage_booked_days"] = d
        agent["voyage_open_sea_01"] = op
        agent["voyage_origin_port_id"] = here
        agent["docked_port"] = ""

    def _npc_depart_convoy_group(self, leader: dict, followers: list, here: str, dest: str) -> None:
        ships = [leader] + list(followers)
        d_max = 1
        op_max = 0.0
        for ags in ships:
            vf = self._npc_voyage_facing_params(ags, here, dest)
            if not vf:
                return
            d_max = max(d_max, int(vf.get("days", 1)))
            op_max = max(op_max, float(vf.get("open_01", 0.0)))
        op_max = clampf(op_max, 0.0, 1.0)
        lid = int(leader.get("id", 0))
        fids = [int(x.get("id", 0)) for x in followers]
        self._ensure_npc_convoy_fields(leader)
        leader["convoy_escort_id"] = 0
        leader["convoy_escort_player"] = False
        leader["convoy_leader_id"] = lid
        leader["convoy_member_ids"] = list(fids)
        leader["convoy_formed"] = True
        leader["scattered_ids"] = []
        leader["contact_candidate_bias"] = float(self.rng.random())
        leader["voyage_dest_id"] = dest
        leader["voyage_days_remaining"] = d_max
        leader["voyage_booked_days"] = d_max
        leader["voyage_open_sea_01"] = op_max
        leader["voyage_origin_port_id"] = here
        leader["docked_port"] = ""
        for fw in followers:
            self._ensure_npc_convoy_fields(fw)
            fw["convoy_leader_id"] = lid
            fw["convoy_member_ids"] = []
            fw["convoy_formed"] = True
            fw["scattered_ids"] = []
            fw["contact_candidate_bias"] = 0.0
            fw["voyage_dest_id"] = dest
            fw["voyage_days_remaining"] = d_max
            fw["voyage_booked_days"] = d_max
            fw["voyage_open_sea_01"] = op_max
            fw["voyage_origin_port_id"] = here
            fw["docked_port"] = ""
        self.convoy_formations += 1
        self._npc_try_hire_escort_for_convoy(leader, fids, here, dest, d_max, op_max)

    def _npc_convoy_process_depart_group(self, pid: str, dest: str, mut_pool: list, used_global: dict) -> None:
        while mut_pool:
            leader = mut_pool[0]
            lid = int(leader.get("id", 0))
            if lid in used_global:
                mut_pool.pop(0)
                continue
            vf0 = self._npc_voyage_facing_params(leader, pid, dest)
            if not vf0:
                mut_pool.pop(0)
                continue
            mut_pool.pop(0)
            route_open = float(vf0.get("open_01", 0.0))
            followers: list = []
            idx = 0
            while idx < len(mut_pool) and len(followers) < _CONVOY_MAX_MERCHANTS - 1:
                cand = mut_pool[idx]
                cid = int(cand.get("id", 0))
                if cid in used_global:
                    mut_pool.pop(idx)
                    continue
                if self._npc_convoy_join_roll(leader, cand, dest, route_open):
                    followers.append(cand)
                    mut_pool.pop(idx)
                    continue
                idx += 1
            if not followers:
                self._npc_depart_solo_merchant(leader, pid, dest)
                used_global[lid] = True
            else:
                self._npc_depart_convoy_group(leader, followers, pid, dest)
                used_global[lid] = True
                for fw in followers:
                    used_global[int(fw.get("id", 0))] = True

    def _npc_convoy_formation_and_depart_tick(self) -> None:
        if self.block_npc_merchant_voyages:
            return
        if len(self.port_names) < 2:
            return
        used_global: dict = {}
        port_list = list(self.port_order)
        for si in range(len(port_list) - 1, 0, -1):
            ji = self.rng.randint(0, si)
            port_list[si], port_list[ji] = port_list[ji], port_list[si]
        for pid in port_list:
            if pid not in self.port_names:
                continue
            docked: list = []
            for ag in self.npc_agents:
                if not isinstance(ag, dict):
                    continue
                if int(ag.get("voyage_days_remaining", 0)) != 0:
                    continue
                if str(ag.get("docked_port", "")) != pid:
                    continue
                if str(ag.get("voyage_role", _VOYAGE_ROLE_MERCHANT)) != _VOYAGE_ROLE_MERCHANT:
                    continue
                docked.append(ag)
            for sj in range(len(docked) - 1, 0, -1):
                jj = self.rng.randint(0, sj)
                docked[sj], docked[jj] = docked[jj], docked[sj]
            proposals = []
            for agd in docked:
                aid = int(agd.get("id", 0))
                if aid in used_global:
                    continue
                if self.rng.random() > self._npc_depart_effective_stay_gate(agd, pid):
                    continue
                if self.rng.random() < self._npc_trading_memory_pick_probability(agd):
                    dest = self._npc_pick_trading_dest_any_port(agd, pid)
                else:
                    opts = [str(p) for p in self.port_order if str(p) != pid]
                    if not opts:
                        continue
                    dest = str(opts[self.rng.randint(0, len(opts) - 1)])
                if not dest or dest not in self.port_names:
                    continue
                dest = self._npc_depart_dest_contract_bias(agd, pid, dest)
                if not dest or dest not in self.port_names:
                    continue
                proposals.append((agd, dest))
            by_dest: dict = {}
            for ag2, dk in proposals:
                by_dest.setdefault(dk, []).append(ag2)
            for dk, grp in by_dest.items():
                if not grp:
                    continue
                grp.sort(key=lambda x: int(x.get("id", 0)))
                pool = [g2 for g2 in grp if int(g2.get("id", 0)) not in used_global]
                if not pool:
                    continue
                for sk2 in range(len(pool) - 1, 0, -1):
                    jk2 = self.rng.randint(0, sk2)
                    pool[sk2], pool[jk2] = pool[jk2], pool[sk2]
                self._npc_convoy_process_depart_group(pid, str(dk), pool, used_global)

    def _npc_active_pirate_count(self) -> int:
        return sum(
            1
            for ag in self.npc_agents
            if isinstance(ag, dict) and str(ag.get("voyage_role", "")) == _VOYAGE_ROLE_PIRATE
        )

    def _npc_boarding_marine_qty(self, ag: dict) -> int:
        if "marines" not in self.goods:
            return 0
        cargo = ag.get("cargo")
        if not isinstance(cargo, dict):
            return 0
        return clampi(int(cargo.get("marines", 0)), 0, 9999)

    def _npc_cargo_estimated_sell_value_coins(self, ag: dict) -> int:
        cargo = ag.get("cargo")
        if not isinstance(cargo, dict):
            return 0
        t = 0
        for gid, q in cargo.items():
            gs = str(gid)
            if gs not in self.goods:
                continue
            row = self.goods[gs]
            up = max(0, int(row.get("unit_sell_price", 0)))
            t += up * self._npc_cargo_qty(cargo, gs)
        return t

    def _npc_pirate_boarding_power(self, ag: dict) -> float:
        mar = self._npc_boarding_marine_qty(ag)
        row = self._npc_ship_row(ag)
        vm = clampf(float(row.get("voyage_day_mult", 1.0)), 0.55, 1.55)
        cat = str(row.get("category", "merchant"))
        hull_bonus = 4.0 if cat == "galley" else 0.0
        ex = self._npc_trait_f(ag, _NPC_TRAIT_EXTRA)
        neu = self._npc_trait_f(ag, _NPC_TRAIT_NEURO)
        return float(mar) * 2.35 + 8.0 + hull_bonus + (vm - 0.55) * 5.5 + ex * 2.8 + neu * 1.1

    def _npc_weighted_pick_agent(self, rows: list) -> dict:
        if not rows:
            return {}
        tw = sum(max(0.0001, float(r.get("w", 1.0))) for r in rows)
        x = self.rng.random() * tw
        for d1 in rows:
            wf = max(0.0001, float(d1.get("w", 1.0)))
            x -= wf
            if x <= 0.0:
                ag = d1.get("ag")
                return ag if isinstance(ag, dict) else {}
        last = rows[-1]
        ag2 = last.get("ag")
        return ag2 if isinstance(ag2, dict) else {}

    def _npc_pirate_convoy_leader_for(self, victim: dict, idxm: dict) -> dict:
        cl = int(victim.get("convoy_leader_id", 0))
        sid = int(victim.get("id", 0))
        if cl > 0 and cl != sid and cl in idxm:
            L = idxm[cl]
            if isinstance(L, dict):
                if int(L.get("voyage_days_remaining", 0)) > 0 and str(L.get("voyage_dest_id", "")) == str(
                    victim.get("voyage_dest_id", "")
                ):
                    return L
        return victim

    def _npc_pirate_pick_contact_ship(self, leader: dict, idxm: dict) -> dict:
        rows = []
        c0 = leader
        mar0 = self._npc_boarding_marine_qty(c0)
        est0 = self._npc_cargo_estimated_sell_value_coins(c0)
        w0 = float(est0) / (float(mar0) + 3.0) * 0.02 + 0.14 + float(c0.get("contact_candidate_bias", 0.0)) * 0.12
        rows.append({"ag": c0, "w": max(0.05, w0)})
        mids = leader.get("convoy_member_ids")
        if isinstance(mids, list):
            for mid in mids:
                mid_i = int(mid)
                if mid_i not in idxm:
                    continue
                mem = idxm[mid_i]
                if not isinstance(mem, dict):
                    continue
                if not self._npc_convoy_is_follower(mem):
                    continue
                if str(mem.get("voyage_role", _VOYAGE_ROLE_MERCHANT)) != _VOYAGE_ROLE_MERCHANT:
                    continue
                mmar = self._npc_boarding_marine_qty(mem)
                mest = self._npc_cargo_estimated_sell_value_coins(mem)
                ww = float(mest) / (float(mmar) + 3.0) * 0.02 + 0.12
                rows.append({"ag": mem, "w": max(0.05, ww)})
        return self._npc_weighted_pick_agent(rows)

    def _npc_pirate_apply_marine_losses(self, ag: dict, loss: int) -> None:
        if loss <= 0 or "marines" not in self.goods:
            return
        cargo = ag.get("cargo")
        if not isinstance(cargo, dict):
            return
        have = self._npc_cargo_qty(cargo, "marines")
        take = min(have, loss)
        if take > 0:
            self.pirate_marines_lost += take
            self._npc_adjust_cargo(cargo, "marines", -take)

    def _npc_escort_combat_flee(self, leader: dict, escort: dict) -> None:
        leader["convoy_escort_id"] = 0
        leader["convoy_escort_player"] = False
        promised = 0
        ct0 = escort.get("escort_contract")
        if isinstance(ct0, dict):
            promised = clampi(int(ct0.get("pay_coins", 0)), 0, _ESCORT_PAY_MAX)
        escort["voyage_role"] = _VOYAGE_ROLE_MERCHANT
        escort["escort_contract"] = {}
        escort["convoy_leader_id"] = 0
        escort["convoy_member_ids"] = []
        escort["convoy_formed"] = False
        self._npc_escort_reliability_apply(escort, False, promised)
        self._ensure_npc_escort_reputation_fields(escort)
        r = float(escort.get("escort_reliability", 0.55))
        escort["escort_reliability"] = clampf(r - 0.11, 0.0, 1.0)
        self.pirate_escort_flees += 1

    def _npc_pirate_loot_contact(self, pirate: dict, contact: dict) -> None:
        purse_v = clampi(int(contact.get("money", 0)), 0, _MAX_PURSE_COINS_PY)
        take_c = min(purse_v, max(8, int(round(float(purse_v) * 0.21))) + self.rng.randint(0, 36))
        take_c = min(take_c, purse_v)
        if take_c > 0:
            contact["money"] = purse_v - take_c
            pirate["money"] = clampi(int(pirate.get("money", 0)) + take_c, 0, _MAX_PURSE_COINS_PY)
            self.pirate_loot_coins += take_c
        p_cargo = pirate.get("cargo")
        v_cargo = contact.get("cargo")
        if not isinstance(p_cargo, dict) or not isinstance(v_cargo, dict):
            return
        tries = self.rng.randint(1, 3)
        for _ in range(tries):
            candidates = []
            for gid, q in v_cargo.items():
                gis = str(gid)
                if gis in ("grain", "marines") or gis not in self.goods:
                    continue
                qq = self._npc_cargo_qty(v_cargo, gis)
                if qq <= 0:
                    continue
                up = max(1, int(self.goods[gis].get("unit_sell_price", 1)))
                candidates.append({"gid": gis, "w": float(qq * up)})
            if not candidates:
                break
            tw = sum(float(c.get("w", 1.0)) for c in candidates)
            x = self.rng.random() * tw
            pick_gid = ""
            for c2 in candidates:
                x -= float(c2.get("w", 1.0))
                if x <= 0.0:
                    pick_gid = str(c2.get("gid", ""))
                    break
            if not pick_gid:
                pick_gid = str(candidates[0].get("gid", ""))
            steal = self.rng.randint(1, 4)
            steal = min(steal, self._npc_cargo_qty(v_cargo, pick_gid))
            if steal <= 0:
                continue
            self._npc_adjust_cargo(v_cargo, pick_gid, -steal)
            self._npc_adjust_cargo(p_cargo, pick_gid, steal)

    def _npc_convoy_detach_follower(self, leader: dict, member_id: int) -> None:
        mids = leader.get("convoy_member_ids")
        if not isinstance(mids, list):
            return
        nm = [int(it) for it in mids if int(it) != member_id]
        leader["convoy_member_ids"] = nm
        scat = leader.get("scattered_ids")
        if not isinstance(scat, list):
            scat = []
        if member_id not in scat:
            scat.append(member_id)
        leader["scattered_ids"] = scat
        for ag in self.npc_agents:
            if not isinstance(ag, dict):
                continue
            if int(ag.get("id", 0)) != member_id:
                continue
            ag["convoy_leader_id"] = 0
            ag["convoy_member_ids"] = []
            ag["convoy_formed"] = False
            break

    def _npc_pirate_maybe_scatter_convoy(self, leader: dict) -> None:
        if not bool(leader.get("convoy_formed", False)):
            return
        mm = leader.get("convoy_member_ids")
        if not isinstance(mm, list) or not mm:
            return
        if self.rng.random() > 0.24:
            return
        pick = int(mm[self.rng.randint(0, len(mm) - 1)])
        self._npc_convoy_detach_follower(leader, pick)

    def _npc_resolve_pirate_catch(self, pr: dict, victim: dict, idxm: dict) -> None:
        leader = self._npc_pirate_convoy_leader_for(victim, idxm)
        esc_pl = bool(leader.get("convoy_escort_player", False))
        esid = int(leader.get("convoy_escort_id", 0))
        escort_fled = False
        if esc_pl:
            lidp = int(leader.get("id", 0))
            if (
                str(self.player_voyage_role) == _VOYAGE_ROLE_ESCORT
                and int(self.player_escort_contract.get("employer_id", -9)) == lidp
                and int(self.player_voyage_days_remaining) > 0
                and str(self.player_voyage_dest_id or "") == str(leader.get("voyage_dest_id", ""))
            ):
                pp2 = self._npc_pirate_boarding_power(pr)
                ep2 = self._player_boarding_power_py()
                if pp2 > ep2 * _PIRATE_FLEE_POWER_RATIO:
                    self._player_escort_combat_flee_py(leader)
                    escort_fled = True
                else:
                    ratio2 = pp2 / max(1.0, ep2)
                    lose_e2 = self.rng.randint(0, 2) + int(ratio2 * 2.1)
                    lose_p2 = self.rng.randint(0, 2) + int((1.0 / max(0.35, ratio2)) * 1.4)
                    self._player_apply_boarding_marine_loss_py(lose_e2)
                    self._npc_pirate_apply_marine_losses(pr, lose_p2)
                    if self._npc_boarding_marine_qty(pr) <= 0:
                        return
        elif esid > 0 and esid in idxm:
            esc = idxm[esid]
            if isinstance(esc, dict):
                if str(esc.get("voyage_role", "")) == _VOYAGE_ROLE_ESCORT and int(esc.get("convoy_leader_id", 0)) == int(
                    leader.get("id", 0)
                ):
                    pp = self._npc_pirate_boarding_power(pr)
                    ep = self._npc_pirate_boarding_power(esc)
                    if pp > ep * _PIRATE_FLEE_POWER_RATIO:
                        self._npc_escort_combat_flee(leader, esc)
                        escort_fled = True
                    else:
                        ratio = pp / max(1.0, ep)
                        lose_e = self.rng.randint(0, 2) + int(ratio * 2.1)
                        lose_p = self.rng.randint(0, 2) + int((1.0 / max(0.35, ratio)) * 1.4)
                        self._npc_pirate_apply_marine_losses(esc, lose_e)
                        self._npc_pirate_apply_marine_losses(pr, lose_p)
                        if self._npc_boarding_marine_qty(pr) <= 0:
                            return
        contact = self._npc_pirate_pick_contact_ship(leader, idxm)
        if not contact:
            return
        vic_power = self._npc_pirate_boarding_power(contact)
        if bool(leader.get("convoy_formed", False)) and int(contact.get("convoy_leader_id", 0)) == int(leader.get("id", 0)):
            vic_power += 3.5
        atk = self._npc_pirate_boarding_power(pr) + self.rng.random() * 9.0
        if atk < vic_power * 0.9:
            self._npc_pirate_apply_marine_losses(pr, self.rng.randint(1, 5))
            return
        self._npc_pirate_loot_contact(pr, contact)
        pn0 = float(pr.get("pirate_notoriety", 0.0))
        pr["pirate_notoriety"] = clampf(pn0 + 3.5 + (5.0 if escort_fled else 0.0), 0.0, _PIRATE_NOTORIETY_CAP)
        self._npc_pirate_maybe_scatter_convoy(leader)
        self._npc_trim_cargo_to_capacity(pr)
        self.pirate_raids_success += 1

    def _npc_pirate_encounters_tick(self) -> None:
        if "marines" not in self.goods:
            return
        idxm = self._npc_index_agents_by_id()
        for pr in self.npc_agents:
            if not isinstance(pr, dict):
                continue
            if str(pr.get("voyage_role", "")) != _VOYAGE_ROLE_PIRATE:
                continue
            if int(pr.get("voyage_days_remaining", 0)) <= 0:
                continue
            rows = []
            for v in self.npc_agents:
                if not isinstance(v, dict):
                    continue
                if int(v.get("id", 0)) == int(pr.get("id", 0)):
                    continue
                if int(v.get("voyage_days_remaining", 0)) <= 0:
                    continue
                if str(v.get("voyage_role", _VOYAGE_ROLE_MERCHANT)) != _VOYAGE_ROLE_MERCHANT:
                    continue
                w = 0.62
                if str(v.get("voyage_dest_id", "")) == str(pr.get("voyage_dest_id", "")):
                    w += 2.0
                srow = self._npc_ship_row(v)
                vm = clampf(float(srow.get("voyage_day_mult", 1.0)), 0.55, 1.55)
                w += (vm - 0.55) * 1.75
                op = clampf(
                    0.5 * (float(pr.get("voyage_open_sea_01", 0.0)) + float(v.get("voyage_open_sea_01", 0.0))),
                    0.0,
                    1.0,
                )
                w *= 0.72 + op * 0.52
                rows.append({"ag": v, "w": max(0.07, w)})
            if not rows:
                continue
            victim = self._npc_weighted_pick_agent(rows)
            if not victim:
                continue
            vmin = clampf(float(self._npc_ship_row(victim).get("voyage_day_mult", 1.0)), 0.55, 1.55)
            pm = clampf(float(self._npc_ship_row(pr).get("voyage_day_mult", 1.0)), 0.55, 1.55)
            op2 = clampf(
                0.5 * (float(pr.get("voyage_open_sea_01", 0.0)) + float(victim.get("voyage_open_sea_01", 0.0))),
                0.0,
                1.0,
            )
            p_catch = clampf(
                _ENCOUNTER_BASE_P * (0.88 + (vmin - pm) * 0.48) * (0.64 + op2 * 0.48),
                0.011,
                0.42,
            )
            self.pirate_encounter_attempts += 1
            if self.rng.random() > p_catch:
                continue
            self._npc_resolve_pirate_catch(pr, victim, idxm)

    def _npc_try_convert_merchant_to_pirate(self, ag: dict) -> None:
        if self._npc_active_pirate_count() >= _PIRATE_MAX_ACTIVE:
            return
        if str(ag.get("voyage_role", "")) != _VOYAGE_ROLE_MERCHANT:
            return
        if self._npc_convoy_is_follower(ag):
            return
        if int(ag.get("voyage_days_remaining", 0)) != 0:
            return
        if clampi(int(ag.get("money", 0)), 0, _MAX_PURSE_COINS_PY) > _PIRATE_SPAWN_PURSE_MAX:
            return
        open_ = self._npc_trait_f(ag, _NPC_TRAIT_OPEN)
        neu = self._npc_trait_f(ag, _NPC_TRAIT_NEURO)
        p_spawn = clampf(_PIRATE_SPAWN_ROLL_BASE + (1.0 - open_) * 0.04 + neu * 0.03, 0.02, 0.14)
        if self.rng.random() > p_spawn:
            return
        ag["voyage_role"] = _VOYAGE_ROLE_PIRATE
        if _PIRATE_RAIDER_HULL_ID in self._ship_classes:
            ag["ship_class_id"] = _PIRATE_RAIDER_HULL_ID
        self._npc_convoy_reset_docked(ag)
        ag["escort_contract"] = {}
        cargo = ag.get("cargo")
        if not isinstance(cargo, dict):
            ag["cargo"] = {}
            cargo = ag["cargo"]
        if "marines" in self.goods:
            add_m = self.rng.randint(6, 16)
            self._npc_adjust_cargo(cargo, "marines", add_m)
        ag["pirate_notoriety"] = 0.0
        self._npc_trim_cargo_to_capacity(ag)

    def _npc_pirate_spawn_docked_tick(self) -> None:
        if "marines" not in self.goods:
            return
        for ag in self.npc_agents:
            if not isinstance(ag, dict):
                continue
            if self._npc_active_pirate_count() >= _PIRATE_MAX_ACTIVE:
                return
            self._npc_try_convert_merchant_to_pirate(ag)

    def _npc_pirate_dock_depart_tick(self) -> None:
        if len(self.port_names) < 2:
            return
        for ag in self.npc_agents:
            if not isinstance(ag, dict):
                continue
            if str(ag.get("voyage_role", "")) != _VOYAGE_ROLE_PIRATE:
                continue
            if int(ag.get("voyage_days_remaining", 0)) != 0:
                continue
            here = str(ag.get("docked_port", ""))
            if not here or here not in self.port_names:
                continue
            if self.rng.random() > _PIRATE_DEPART_STAY_GATE:
                continue
            opts = [str(p) for p in self.port_order if str(p) != here]
            if not opts:
                continue
            dest = str(opts[self.rng.randint(0, len(opts) - 1)])
            self._npc_depart_solo_merchant(ag, here, dest)

    def _sanitize_price_memory(self, pm: dict) -> dict:
        out: dict[str, dict[str, dict[str, int]]] = {}
        for pk, row in pm.items():
            ps = str(pk)
            if self.port_names and ps not in self.port_names:
                continue
            if not isinstance(row, dict):
                continue
            rf: dict[str, dict[str, int]] = {}
            for gk, cell in row.items():
                gis = str(gk)
                if gis not in self.goods:
                    continue
                if not isinstance(cell, dict):
                    continue
                rf[gis] = {
                    "bu": clampi(int(cell.get("bu", 0)), 0, _MAX_PURSE_COINS_PY),
                    "se": clampi(int(cell.get("se", 0)), 0, _MAX_PURSE_COINS_PY),
                }
            out[ps] = rf
        return out

    def _prune_port_good_tolls_to_known_goods(self) -> None:
        for pid in list(self.port_good_tolls.keys()):
            row = self.port_good_tolls.get(pid)
            if not isinstance(row, dict):
                del self.port_good_tolls[pid]
                continue
            self.port_good_tolls[pid] = {str(gk): int(v) for gk, v in row.items() if str(gk) in self.goods}

    def _port_toll_row(self, port_id: str) -> dict[str, int]:
        ps = str(port_id)
        row = self.port_good_tolls.get(ps)
        return dict(row) if isinstance(row, dict) else {}

    def _port_toll_per_unit(self, port_id: str, good_id: str) -> int:
        row = self._port_toll_row(port_id)
        return clampi(int(row.get(str(good_id), 0)), 0, 80)

    def _port_any_toll(self, port_id: str) -> bool:
        return any(clampi(int(v), 0, 999) > 0 for v in self._port_toll_row(port_id).values())

    def _port_count_positive_tolls(self, port_id: str) -> int:
        return sum(1 for v in self._port_toll_row(port_id).values() if clampi(int(v), 0, 999) > 0)

    def _toll_total_coins(self, port_id: str, good_id: str, qty: int) -> int:
        if qty <= 0:
            return 0
        return self._port_toll_per_unit(port_id, good_id) * qty

    def _npc_toll_graft_last_day(self, agent: dict, port_id: str) -> int:
        raw = agent.get("toll_graft_until")
        if not isinstance(raw, dict):
            return 0
        return clampi(int(raw.get(str(port_id), 0)), 0, _MAX_DAY_COUNTER_PY)

    def _npc_has_toll_graft(self, agent: dict, port_id: str) -> bool:
        return self.current_day <= self._npc_toll_graft_last_day(agent, port_id)

    def _npc_set_toll_graft(self, agent: dict, port_id: str, last_day_inclusive: int) -> None:
        raw = agent.get("toll_graft_until")
        m = dict(raw) if isinstance(raw, dict) else {}
        m[str(port_id)] = clampi(last_day_inclusive, 0, _MAX_DAY_COUNTER_PY)
        agent["toll_graft_until"] = m

    def _npc_roll_toll_coins_paid(self, agent: dict, port_id: str, base_toll_coins: int) -> int:
        if base_toll_coins <= 0:
            return 0
        if self._npc_has_toll_graft(agent, port_id):
            return 0
        openn = self._npc_trait_f(agent, _NPC_TRAIT_OPEN)
        consc = self._npc_trait_f(agent, _NPC_TRAIT_CONSC)
        neuro = self._npc_trait_f(agent, _NPC_TRAIT_NEURO)
        risk = clampf(float(agent.get("risk_aversion", 0.5)), 0.0, 1.0)
        p_smuggle = clampf(
            0.08 + openn * 0.22 - consc * 0.10 - risk * 0.08 + neuro * 0.04,
            0.02,
            0.52,
        )
        if self.rng.random() > p_smuggle:
            return base_toll_coins
        p_caught = clampf(0.14 + consc * 0.12 - openn * 0.06 + risk * 0.10, 0.05, 0.45)
        if self.rng.random() < p_caught:
            return min(base_toll_coins * 2, base_toll_coins + 72)
        return 0

    def _bump_port_for_toll_receipt(self, port_id: str, toll_coins: int) -> None:
        if toll_coins <= 0:
            return
        ps = str(port_id)
        if ps not in self.port_names:
            return
        self._bump_port_wealth(ps, max(1, toll_coins // 3))

    def _prune_npc_toll_grafts_expired(self) -> None:
        for ag in self.npc_agents:
            if not isinstance(ag, dict):
                continue
            raw = ag.get("toll_graft_until")
            if not isinstance(raw, dict):
                continue
            newd = {
                pk: d
                for pk, d in raw.items()
                if str(pk) in self.port_names and self.current_day <= int(d)
            }
            if newd:
                ag["toll_graft_until"] = newd
            else:
                ag.pop("toll_graft_until", None)

    def _npc_docked_toll_graft_tick(self) -> None:
        self._prune_npc_toll_grafts_expired()
        for ag in self.npc_agents:
            if not isinstance(ag, dict):
                continue
            if int(ag.get("voyage_days_remaining", 0)) != 0:
                continue
            ps = str(ag.get("docked_port", ""))
            if not ps or ps not in self.port_names:
                continue
            if not self._port_any_toll(ps):
                continue
            if self._npc_has_toll_graft(ag, ps):
                continue
            if self.rng.random() > _TOLL_NPC_BRIBE_DAILY_CHANCE:
                continue
            coins = clampi(int(ag.get("money", 0)), 0, _MAX_PURSE_COINS_PY)
            n_tolls = self._port_count_positive_tolls(ps)
            cost = clampi(12 + 4 * n_tolls, 16, 98)
            if coins < cost + _NPC_PURSE_RESERVE + 6:
                continue
            ag["money"] = coins - cost
            du = self.rng.randint(_TOLL_BRIBE_DAYS_MIN, _TOLL_BRIBE_DAYS_MAX)
            self._npc_set_toll_graft(ag, ps, self.current_day + du - 1)

    def _npc_wholesale_skill_edge(self, agent: dict) -> float:
        bm = clampf(float(agent.get("buy_mastery", 1.0)), _NPC_MASTER_MIN, _NPC_MASTER_MAX)
        sm = clampf(float(agent.get("sell_mastery", 1.0)), _NPC_MASTER_MIN, _NPC_MASTER_MAX)
        return clampf(0.5 * (bm + sm) - 1.0, -0.26, 0.24)

    def _npc_effective_buy_unit(self, agent: dict, port_id: str, good_id: str) -> int:
        buy_m = clampf(float(agent.get("buy_mastery", 1.0)), _NPC_MASTER_MIN, _NPC_MASTER_MAX)
        base_unit = self._compute_player_buy_unit(port_id, good_id, False)
        if base_unit <= 0:
            return 999999
        reg = _npc_regional_buy_factor_py(port_id, good_id)
        edge = self._npc_wholesale_skill_edge(agent)
        cart = clampf(float(self.port_cartel_strength.get(str(port_id), 0.0)), 0.0, 1.0)
        buy_mult = clampf(
            _NPC_PORT_BUY_MULT * (1.0 - 0.14 * edge) * (1.0 - _CARTEL_BUY_TIGHTEN * cart),
            0.58,
            0.88,
        )
        agree_b = self._npc_big5_agree_buy_mult(agent)
        return max(1, int(math.floor(float(base_unit) * reg * buy_mult * agree_b / buy_m)))

    def _npc_effective_sell_unit(self, agent: dict, port_id: str, good_id: str) -> int:
        sell_m = clampf(float(agent.get("sell_mastery", 1.0)), _NPC_MASTER_MIN, _NPC_MASTER_MAX)
        base_unit = self._compute_player_sell_unit(port_id, good_id, False)
        if base_unit <= 0:
            return 0
        reg = _npc_regional_sell_factor_py(port_id, good_id)
        edge = self._npc_wholesale_skill_edge(agent)
        cart2 = clampf(float(self.port_cartel_strength.get(str(port_id), 0.0)), 0.0, 1.0)
        sell_mult = clampf(
            _NPC_PORT_SELL_MULT * (1.0 + 0.14 * edge) * (1.0 + _CARTEL_SELL_INFLATE * cart2),
            1.20,
            1.78,
        )
        agree_s = self._npc_big5_agree_sell_mult(agent)
        return max(1, int(math.ceil(float(base_unit) * reg * sell_mult * agree_s * sell_m)))

    def _npc_snapshot_price_memory(self, agent: dict, port_id: str) -> None:
        if port_id not in self.port_names:
            return
        if not isinstance(agent.get("price_memory"), dict):
            agent["price_memory"] = {}
        pm = agent["price_memory"]
        row: dict[str, dict[str, int]] = {}
        for gid in self.goods.keys():
            gids = str(gid)
            row[gids] = {
                "bu": self._npc_effective_buy_unit(agent, port_id, gids),
                "se": self._npc_effective_sell_unit(agent, port_id, gids),
            }
        pm[port_id] = row

    def _npc_memory_sell_edge(self, agent: dict, port_id: str, good_id: str) -> float:
        cur = self._npc_effective_sell_unit(agent, port_id, good_id)
        if cur <= 0:
            return 1.0
        pm = agent.get("price_memory")
        if not isinstance(pm, dict):
            return 1.0
        bestm = 0
        for pk, prow in pm.items():
            ps = str(pk)
            if ps == port_id or ps not in self.port_names:
                continue
            if not isinstance(prow, dict):
                continue
            cell = prow.get(good_id)
            if not isinstance(cell, dict):
                continue
            bestm = max(bestm, int(cell.get("se", 0)))
        if bestm <= 0:
            return 1.0
        return clampf(float(cur) / float(max(1, bestm)), 0.62, 1.52)

    def _npc_memory_buy_edge(self, agent: dict, port_id: str, good_id: str) -> float:
        cur = self._npc_effective_buy_unit(agent, port_id, good_id)
        if cur >= 999000:
            return 1.0
        pm = agent.get("price_memory")
        if not isinstance(pm, dict):
            return 1.0
        bestc = 999999999
        for pk, prow in pm.items():
            ps = str(pk)
            if ps == port_id or ps not in self.port_names:
                continue
            if not isinstance(prow, dict):
                continue
            cell = prow.get(good_id)
            if not isinstance(cell, dict):
                continue
            bestc = min(bestc, int(cell.get("bu", 999999999)))
        if bestc >= 999999000:
            return 1.0
        return clampf(float(bestc) / float(max(1, cur)), 1.0, 1.62)

    def _sanitize_npc_peer_debts(self, ag: dict) -> None:
        raw = ag.get("npc_peer_debts")
        if not isinstance(raw, list):
            ag["npc_peer_debts"] = []
            return
        out: list[dict] = []
        for cell in raw:
            if not isinstance(cell, dict):
                continue
            cid = int(cell.get("creditor", 0))
            rem = max(0, int(cell.get("remaining", 0)))
            if cid <= 0 or rem <= 0:
                continue
            out.append({"creditor": cid, "remaining": rem})
            if len(out) >= _NPC_PEER_LOAN_MAX_DEBTS:
                break
        ag["npc_peer_debts"] = out

    def _npc_peer_debt_sum_remaining(self, ag: dict) -> int:
        self._sanitize_npc_peer_debts(ag)
        t = 0
        for cell in ag["npc_peer_debts"]:
            if isinstance(cell, dict):
                t += max(0, int(cell.get("remaining", 0)))
        return t

    def _npc_peer_loan_repay_from_margin(self, ag: dict, margin_coins: int) -> int:
        if margin_coins <= 0:
            return margin_coins
        self._sanitize_npc_peer_debts(ag)
        debts: list = ag["npc_peer_debts"]
        if not debts:
            return margin_coins
        idxm = self._npc_index_agents_by_id()
        left = margin_coins
        i = 0
        while i < len(debts) and left > 0:
            c0 = debts[i]
            if not isinstance(c0, dict):
                i += 1
                continue
            row = dict(c0)
            cid = int(row.get("creditor", 0))
            rem = max(0, int(row.get("remaining", 0)))
            if rem <= 0:
                debts.pop(i)
                continue
            pay = min(left, rem)
            rem -= pay
            left -= pay
            row["remaining"] = rem
            if cid in idxm:
                cr = idxm[cid]
                cm = clampi(int(cr.get("money", 0)), 0, _MAX_PURSE_COINS_PY)
                cr["money"] = clampi(cm + pay, 0, _MAX_PURSE_COINS_PY)
            if rem <= 0:
                debts.pop(i)
            else:
                debts[i] = row
                i += 1
        ag["npc_peer_debts"] = debts
        return left

    def _npc_peer_creditor_ids_for_agent(self, ag: dict) -> list:
        self._sanitize_npc_peer_debts(ag)
        ids: list[int] = []
        for cell in ag["npc_peer_debts"]:
            if isinstance(cell, dict):
                cid = int(cell.get("creditor", 0))
                if cid > 0:
                    ids.append(cid)
        return ids

    def _npc_peer_creditor_present_at_port(self, ag: dict, docked_port: str) -> bool:
        ps = str(docked_port)
        if not ps:
            return False
        idxm = self._npc_index_agents_by_id()
        for cid in self._npc_peer_creditor_ids_for_agent(ag):
            if cid not in idxm:
                continue
            cr = idxm[cid]
            if int(cr.get("voyage_days_remaining", 0)) != 0:
                continue
            if str(cr.get("docked_port", "")) == ps:
                return True
        return False

    def _npc_peer_creditor_home_penalty(self, agent: dict, dest: str) -> float:
        ds = str(dest)
        if not ds:
            return 0.0
        self._sanitize_npc_peer_debts(agent)
        debts = agent["npc_peer_debts"]
        if not debts:
            return 0.0
        idxm = self._npc_index_agents_by_id()
        pen = 0.0
        for cell in debts:
            if not isinstance(cell, dict):
                continue
            rem = max(0, int(cell.get("remaining", 0)))
            if rem <= 0:
                continue
            cid = int(cell.get("creditor", 0))
            if cid not in idxm:
                continue
            hp = str(idxm[cid].get("home_port", ""))
            if not hp or hp != ds:
                continue
            consc = self._npc_trait_f(agent, _NPC_TRAIT_CONSC)
            neuro = self._npc_trait_f(agent, _NPC_TRAIT_NEURO)
            flee = clampf((1.0 - consc) * 0.55 + neuro * 0.45, 0.0, 1.0)
            pen += float(rem) * _NPC_PEER_LOAN_HOME_AVOID_PER_COIN * flee
        return pen

    def _npc_peer_loan_flee_gate_sub(self, agent: dict, docked_port: str) -> float:
        if not self._npc_peer_creditor_present_at_port(agent, docked_port):
            return 0.0
        owed = self._npc_peer_debt_sum_remaining(agent)
        if owed <= 0:
            return 0.0
        neuro = self._npc_trait_f(agent, _NPC_TRAIT_NEURO)
        consc = self._npc_trait_f(agent, _NPC_TRAIT_CONSC)
        open_ = self._npc_trait_f(agent, _NPC_TRAIT_OPEN)
        frac = clampf(float(owed) / 220.0, 0.0, 1.0)
        flee = clampf((1.0 - consc) * 0.5 + neuro * 0.42 + open_ * 0.12, 0.0, 1.0)
        return min(_NPC_PEER_LOAN_FLEE_GATE_SUB_MAX, 0.05 + frac * flee * 0.38)

    def _npc_try_peer_loans_after_dock_trade(self) -> None:
        byp: dict[str, list] = {}
        for ag in self.npc_agents:
            if not isinstance(ag, dict):
                continue
            if str(ag.get("voyage_role", _VOYAGE_ROLE_MERCHANT)) != _VOYAGE_ROLE_MERCHANT:
                continue
            if int(ag.get("voyage_days_remaining", 0)) != 0:
                continue
            pid = str(ag.get("docked_port", ""))
            if pid not in self.port_names:
                continue
            byp.setdefault(pid, []).append(ag)
        for pid, arr in byp.items():
            if len(arr) < 2:
                continue
            for debtor in arr:
                if not isinstance(debtor, dict):
                    continue
                d = debtor
                self._sanitize_npc_peer_debts(d)
                if len(d["npc_peer_debts"]) >= _NPC_PEER_LOAN_MAX_DEBTS:
                    continue
                try:
                    rep_d = clampf(float(d.get("merchant_repute_01", 0.52)), 0.0, 1.0)
                except (TypeError, ValueError):
                    rep_d = 0.52
                p_loan_roll = clampf(_NPC_PEER_LOAN_OFFER_ROLL * (0.78 + (1.22 - 0.78) * rep_d), 0.0, 0.58)
                if self.rng.uniform(0.0, 1.0) > p_loan_roll:
                    continue
                purse_d = clampi(int(d.get("money", 0)), 0, _MAX_PURSE_COINS_PY)
                if purse_d > _NPC_PEER_LOAN_DEBTOR_PURSE_MAX:
                    continue
                creditors = list(arr)
                for _ in range(max(1, len(creditors) * 2)):
                    j = self.rng.randint(0, max(0, len(creditors) - 1))
                    k = self.rng.randint(0, max(0, len(creditors) - 1))
                    creditors[j], creditors[k] = creditors[k], creditors[j]
                for cred_raw in creditors:
                    if not isinstance(cred_raw, dict):
                        continue
                    c = cred_raw
                    if int(c.get("id", -1)) == int(d.get("id", -2)):
                        continue
                    purse_c = clampi(int(c.get("money", 0)), 0, _MAX_PURSE_COINS_PY)
                    if purse_c < _NPC_PEER_LOAN_CREDITOR_PURSE_MIN:
                        continue
                    cushion = _NPC_PEER_LOAN_CREDITOR_RESERVE + self._npc_officer_due_coins(c) * 2
                    cap = purse_c - cushion
                    if cap < _NPC_PEER_LOAN_MIN_PRINCIPAL:
                        continue
                    agree = self._npc_trait_f(c, _NPC_TRAIT_AGREE)
                    lend_p = 0.07 + (0.36 - 0.07) * agree
                    if self.rng.uniform(0.0, 1.0) > lend_p:
                        continue
                    d_consc = self._npc_trait_f(d, _NPC_TRAIT_CONSC)
                    recv_p = 0.1 + (0.62 - 0.1) * d_consc
                    if self.rng.uniform(0.0, 1.0) > recv_p:
                        continue
                    pmax = min(
                        int(round(float(_NPC_PEER_LOAN_MAX_PRINCIPAL) * (0.9 + (1.1 - 0.9) * rep_d))),
                        cap,
                    )
                    pmin = min(_NPC_PEER_LOAN_MIN_PRINCIPAL, pmax)
                    if pmin > pmax:
                        continue
                    principal = self.rng.randint(pmin, pmax)
                    if principal <= 0:
                        continue
                    c["money"] = clampi(purse_c - principal, 0, _MAX_PURSE_COINS_PY)
                    d["money"] = clampi(purse_d + principal, 0, _MAX_PURSE_COINS_PY)
                    lst = list(d["npc_peer_debts"])
                    lst.append({"creditor": int(c.get("id", 0)), "remaining": principal})
                    d["npc_peer_debts"] = lst
                    break

    def _npc_voyage_dest_score(self, agent: dict, here: str, dest: str) -> float:
        cargo = agent.get("cargo")
        if not isinstance(cargo, dict):
            return 0.12
        pm = agent.get("price_memory")
        if not isinstance(pm, dict):
            return 0.35
        row_here = pm.get(here) if isinstance(pm.get(here), dict) else {}
        row_dest = pm.get(dest) if isinstance(pm.get(dest), dict) else {}
        has_dest = isinstance(row_dest, dict) and bool(row_dest)
        sc = 0.1
        for gid, qty in cargo.items():
            gis = str(gid)
            if gis not in self.goods or qty <= 0:
                continue
            se_h = 0
            rh = row_here.get(gis) if isinstance(row_here, dict) else None
            if isinstance(rh, dict):
                se_h = max(0, int(rh.get("se", 0)))
            se_d = 0
            if has_dest:
                rd = row_dest.get(gis)
                if isinstance(rd, dict):
                    se_d = max(0, int(rd.get("se", 0)))
            if se_d > 0 and se_h > 0:
                sc += float(qty) * (float(se_d) / float(max(1, se_h)) - 1.0)
            elif se_d > 0:
                sc += float(qty) * 0.18
            else:
                sc += float(qty) * 0.04
        ntr = self._npc_trait_f(agent, _NPC_TRAIT_NEURO)
        udst = float(self.get_port_food_unrest(dest)) / 200.0
        sc *= 1.0 - 0.24 * (ntr - 0.5) * udst
        if self._world_npc_city_grain_contracts_enabled and self._npc_city_grain_contract_active(agent):
            cgd = agent.get("city_grain_contract")
            if isinstance(cgd, dict) and str(cgd.get("dest", "")) == dest:
                due_c = clampi(int(cgd.get("due", 0)), 0, 9999999)
                slack_c = due_c - int(self.current_day)
                cbon = 0.42 + 0.28 * clampf(float(slack_c) / 44.0, 0.0, 1.0)
                if slack_c <= 14:
                    cbon += 0.62
                if slack_c <= 7:
                    cbon += 0.38
                sc += cbon
        sc = max(0.02, sc) - self._npc_peer_creditor_home_penalty(agent, dest)
        return max(0.02, sc)

    def _npc_memory_pick_neighbor_dest(self, agent: dict, here: str, neigh: list) -> str:
        if not neigh:
            return ""
        best = str(neigh[0])
        best_sc = -1.0e15
        for ni in neigh:
            d = str(ni)
            sc = self._npc_voyage_dest_score(agent, here, d)
            if sc > best_sc:
                best_sc = sc
                best = d
        return best

    def _ensure_npc_risk_aversion(self, ag: dict) -> None:
        if "risk_aversion" not in ag:
            sid = int(ag.get("id", 0))
            ag["risk_aversion"] = clampf(0.4 + 0.55 * math.sin(float(sid) * 2.963 + 1.1), 0.05, 0.98)
        else:
            ag["risk_aversion"] = clampf(float(ag.get("risk_aversion", 0.5)), 0.0, 1.0)

    def _npc_big_five_from_seed(self, seed: int) -> dict[str, float]:
        s = float(seed)
        o = clampf(0.5 + 0.41 * math.sin(s * 0.813 + 0.17) * math.cos(s * 0.291), 0.06, 0.94)
        c = clampf(0.5 + 0.41 * math.cos(s * 0.733 + 0.31) * math.sin(s * 0.377), 0.06, 0.94)
        e = clampf(0.5 + 0.41 * math.sin(s * 0.511 + 0.91) * math.sin(s * 0.619), 0.06, 0.94)
        a = clampf(0.5 + 0.41 * math.cos(s * 0.443 + 0.07) * math.cos(s * 0.881), 0.06, 0.94)
        n = clampf(0.5 + 0.41 * math.sin(s * 0.667 + 0.53) * math.cos(s * 0.409), 0.06, 0.94)
        return {
            _NPC_TRAIT_OPEN: o,
            _NPC_TRAIT_CONSC: c,
            _NPC_TRAIT_EXTRA: e,
            _NPC_TRAIT_AGREE: a,
            _NPC_TRAIT_NEURO: n,
        }

    def _roll_npc_big_five(self) -> dict[str, float]:
        return {
            _NPC_TRAIT_OPEN: self.rng.uniform(0.1, 0.9),
            _NPC_TRAIT_CONSC: self.rng.uniform(0.1, 0.9),
            _NPC_TRAIT_EXTRA: self.rng.uniform(0.1, 0.9),
            _NPC_TRAIT_AGREE: self.rng.uniform(0.1, 0.9),
            _NPC_TRAIT_NEURO: self.rng.uniform(0.1, 0.9),
        }

    def _ensure_npc_big_five(self, ag: dict) -> None:
        seeded = self._npc_big_five_from_seed(int(ag.get("id", 0)))
        for k, v in seeded.items():
            if k in ag:
                ag[k] = clampf(float(ag[k]), 0.0, 1.0)
            else:
                ag[k] = clampf(float(v), 0.0, 1.0)

    def _npc_trait_f(self, ag: dict, trait_key: str) -> float:
        self._ensure_npc_big_five(ag)
        return clampf(float(ag.get(trait_key, 0.5)), 0.0, 1.0)

    def _npc_trade_effective_risk(self, agent: dict) -> float:
        self._ensure_npc_risk_aversion(agent)
        self._ensure_npc_big_five(agent)
        r = clampf(float(agent.get("risk_aversion", 0.5)), 0.0, 1.0)
        n = clampf(float(agent.get(_NPC_TRAIT_NEURO, 0.5)), 0.0, 1.0)
        return min(0.91, clampf(r + 0.22 * (n - 0.5), 0.0, 1.0))

    def _npc_depart_effective_stay_gate(self, agent: dict, docked_port: str) -> float:
        self._ensure_npc_big_five(agent)
        o = self._npc_trait_f(agent, _NPC_TRAIT_OPEN)
        c = self._npc_trait_f(agent, _NPC_TRAIT_CONSC)
        e = self._npc_trait_f(agent, _NPC_TRAIT_EXTRA)
        n = self._npc_trait_f(agent, _NPC_TRAIT_NEURO)
        gate = float(_NPC_DEPART_STAY_GATE)
        gate -= 0.072 * (e - 0.5)
        gate -= 0.055 * (o - 0.5)
        urel = float(self.get_port_food_unrest(docked_port)) / 200.0
        gate += 0.095 * (c - 0.5) * urel
        gate -= 0.14 * (n - 0.5) * urel
        gate -= self._npc_peer_loan_flee_gate_sub(agent, docked_port)
        return clampf(gate, 0.10, 0.94)

    def _npc_trading_memory_pick_probability(self, agent: dict) -> float:
        self._ensure_npc_big_five(agent)
        o = self._npc_trait_f(agent, _NPC_TRAIT_OPEN)
        c = self._npc_trait_f(agent, _NPC_TRAIT_CONSC)
        p = (0.40 + (0.82 - 0.40) * c) * (1.08 + (0.54 - 1.08) * o)
        return clampf(p, 0.26, 0.88)

    def _npc_dock_dust_purse_floor(self, agent: dict) -> int:
        self._ensure_npc_big_five(agent)
        n = clampf(float(agent.get(_NPC_TRAIT_NEURO, 0.5)), 0.0, 1.0)
        return _NPC_DOCK_DUST_PURSE + int(round(9.0 * n))

    def _npc_big5_agree_buy_mult(self, agent: dict) -> float:
        return 1.0 + 0.034 * (self._npc_trait_f(agent, _NPC_TRAIT_AGREE) - 0.5)

    def _npc_big5_agree_sell_mult(self, agent: dict) -> float:
        return 1.0 - 0.034 * (self._npc_trait_f(agent, _NPC_TRAIT_AGREE) - 0.5)

    def _npc_cargo_effective_used_units(self, agent: dict) -> int:
        if "cargo" not in agent or not isinstance(agent["cargo"], dict):
            return 0
        cargo = agent["cargo"]
        row = self._npc_ship_row(agent)
        geff = max(0.5, float(row.get("grain_hold_efficiency", 1.0)))
        s = 0
        for gk, qv in cargo.items():
            q = max(0, int(qv))
            if str(gk) == "grain":
                s += int(math.ceil(float(q) / geff))
            else:
                s += q
        return s

    def _npc_cargo_capacity_units(self, agent: dict) -> int:
        self._ensure_npc_ship_fields(agent)
        row = self._npc_ship_row(agent)
        per = clampi(int(row.get("cargo_per_hull", _FLEET_CARGO_PER_SHIP)), 1, 120)
        return per * clampi(int(agent.get("fleet_ships", 1)), 1, _FLEET_MAX_SHIPS)

    def _npc_cargo_free_space(self, agent: dict) -> int:
        return max(0, self._npc_cargo_capacity_units(agent) - self._npc_cargo_effective_used_units(agent))

    def _npc_roll_trade_lot_qty(self, agent: dict, port_id: str, good_id: str, for_buy: bool) -> int:
        self._ensure_npc_ship_fields(agent)
        r = self._npc_trade_effective_risk(agent)
        if for_buy:
            cap = min(self._npc_cargo_free_space(agent), self._port_stock_qty(port_id, good_id))
        else:
            c = agent.get("cargo")
            if not isinstance(c, dict):
                return 0
            cap = self._npc_cargo_qty(c, good_id)
        if cap <= 0:
            return 0
        brav = 1.0 - r
        tceil = min(_NPC_RISK_AVERSE_MAX_LOT, cap)
        hi = int(round(float(tceil) + (float(cap) - float(tceil)) * brav))
        hi = clampi(hi, 1, cap)
        return self.rng.randint(1, hi)

    def _npc_buy_from_port(self, agent: dict, port_id: str, good_id: str, qty: int) -> None:
        if qty <= 0 or good_id not in self.goods:
            return
        if "cargo" not in agent or not isinstance(agent["cargo"], dict):
            agent["cargo"] = {}
        cargo = agent["cargo"]
        unit = self._npc_effective_buy_unit(agent, port_id, good_id)
        if unit >= 999000:
            return
        coins = clampi(int(agent.get("money", 0)), 0, _MAX_PURSE_COINS_PY)
        max_by_money = coins // unit
        have = self._port_stock_qty(port_id, good_id)
        cap_free = self._npc_cargo_free_space(agent)
        q = min(qty, have, max_by_money, cap_free)
        if q <= 0:
            return
        while q > 0:
            cost_test = unit * q
            fee_test = _captain_trade_fee_on_buy(cost_test)
            if coins - cost_test - fee_test >= _NPC_PURSE_RESERVE:
                break
            q -= 1
        if q <= 0:
            return
        cost = unit * q
        buy_fee = _captain_trade_fee_on_buy(cost)
        agent["money"] = coins - cost - buy_fee
        self._bump_port_wealth(port_id, max(1, cost // 14))
        self._adjust_port_stock(port_id, good_id, -q)
        self._npc_adjust_cargo(cargo, good_id, q)
        self._bump_npc_commerce_buy(port_id, q, cost)

    def _npc_sell_to_port(self, agent: dict, port_id: str, good_id: str, qty: int) -> None:
        if qty <= 0 or good_id not in self.goods:
            return
        if "cargo" not in agent or not isinstance(agent["cargo"], dict):
            agent["cargo"] = {}
        cargo = agent["cargo"]
        have = self._npc_cargo_qty(cargo, good_id)
        q = min(qty, have)
        if q <= 0:
            return
        unit = self._npc_effective_sell_unit(agent, port_id, good_id)
        if unit <= 0:
            return
        revenue = unit * q
        sell_fee = _captain_trade_fee_on_sell(revenue)
        toll_base = self._port_toll_per_unit(port_id, good_id) * q
        toll_paid = 0
        if toll_base > 0 and not self._npc_has_toll_graft(agent, port_id):
            toll_paid = self._npc_roll_toll_coins_paid(agent, port_id, toll_base)
        margin0 = max(0, revenue - sell_fee - toll_paid)
        margin1 = self._npc_peer_loan_repay_from_margin(agent, margin0)
        agent["money"] = clampi(int(agent.get("money", 0)) + margin1, 0, _MAX_PURSE_COINS_PY)
        if toll_paid > 0:
            self._bump_port_for_toll_receipt(port_id, toll_paid)
        self._bump_port_wealth(port_id, max(1, revenue // 12))
        self._npc_adjust_cargo(cargo, good_id, -q)
        self._adjust_port_stock(port_id, good_id, q)
        self._bump_npc_commerce_sell(port_id, q, revenue)

    def _reset_port_commerce_tick(self) -> None:
        z = {"npc_buy_units": 0, "npc_sell_units": 0, "npc_buy_coins": 0, "npc_sell_coins": 0}
        self._port_commerce_tick = {str(pid): {k: v for k, v in z.items()} for pid in self.port_order}

    def _bump_npc_commerce_buy(self, port_id: str, qty: int, cost: int) -> None:
        ps = str(port_id)
        row = self._port_commerce_tick.setdefault(
            ps,
            {"npc_buy_units": 0, "npc_sell_units": 0, "npc_buy_coins": 0, "npc_sell_coins": 0},
        )
        row["npc_buy_units"] += max(0, qty)
        row["npc_buy_coins"] += max(0, cost)

    def _bump_npc_commerce_sell(self, port_id: str, qty: int, revenue: int) -> None:
        ps = str(port_id)
        row = self._port_commerce_tick.setdefault(
            ps,
            {"npc_buy_units": 0, "npc_sell_units": 0, "npc_buy_coins": 0, "npc_sell_coins": 0},
        )
        row["npc_sell_units"] += max(0, qty)
        row["npc_sell_coins"] += max(0, revenue)

    def _npc_try_optional_mint_bullion_at_dock(self, trader: dict, port_id: str) -> bool:
        ps = str(port_id)
        cfg0 = self.port_mint_cfg.get(ps)
        if not isinstance(cfg0, dict):
            return False
        if self.rng.random() >= 0.062:
            return False
        gb = clampi(int(cfg0.get("gold_per_batch", 1)), 0, 24)
        sb = clampi(int(cfg0.get("silver_per_batch", 2)), 0, 36)
        if gb <= 0 and sb <= 0:
            return False
        cargo = trader["cargo"]
        if gb > 0 and self._npc_cargo_qty(cargo, "gold") < gb:
            return False
        if sb > 0 and self._npc_cargo_qty(cargo, "silver") < sb:
            return False
        cpb = clampi(int(cfg0.get("coins_per_batch", 72)), 1, 500)
        fee = max(1, cpb // 24)
        if gb > 0:
            self._npc_adjust_cargo(cargo, "gold", -gb)
        if sb > 0:
            self._npc_adjust_cargo(cargo, "silver", -sb)
        pur = clampi(int(trader.get("money", 0)), 0, _MAX_PURSE_COINS_PY)
        trader["money"] = clampi(pur + cpb - fee, 0, _MAX_PURSE_COINS_PY)
        self._bump_port_wealth(ps, fee)
        return True

    def _npc_tick_one(self, port_id: str, trader: dict) -> None:
        if "cargo" not in trader or not isinstance(trader["cargo"], dict):
            trader["cargo"] = {}
        self._ensure_npc_money_field(trader)
        cargo = trader["cargo"]
        g_tgt = self._stock_target_for_good("grain")
        w_tgt = self._stock_target_for_good("wine")
        g_stock = self._port_stock_qty(port_id, "grain")
        w_stock = self._port_stock_qty(port_id, "wine")
        g_ratio = float(g_stock) / float(max(1, g_tgt))
        w_ratio = float(w_stock) / float(max(1, w_tgt))
        crop_hoard_01 = 0.0
        if "grain" in self.goods:
            crop_hoard_01 = self._crop_phase2_npc_hoard_weight_01(port_id)
        roll = self.rng.random()
        if self.rng.random() < 0.52:
            best_sg = ""
            best_se = 1.0
            for gk in list(cargo.keys()):
                gim = str(gk)
                if gim not in self.goods or self._npc_cargo_qty(cargo, gim) <= 0:
                    continue
                ed = self._npc_memory_sell_edge(trader, port_id, gim)
                if ed > best_se:
                    best_se = ed
                    best_sg = gim
            if best_sg and best_se >= 1.09:
                self._npc_sell_to_port(
                    trader, port_id, best_sg, self._npc_roll_trade_lot_qty(trader, port_id, best_sg, False)
                )
                return
        if self.rng.random() < 0.44:
            best_bg = ""
            best_be = 1.0
            for gid2 in self.goods.keys():
                gids2 = str(gid2)
                be = self._npc_memory_buy_edge(trader, port_id, gids2)
                if be > best_be:
                    best_be = be
                    best_bg = gids2
            if best_bg and best_be >= 1.10 and self._port_stock_qty(port_id, best_bg) > 0:
                self._npc_buy_from_port(
                    trader, port_id, best_bg, self._npc_roll_trade_lot_qty(trader, port_id, best_bg, True)
                )
                return
        if "grain" in self.goods:
            g_sell_lo = 0.42 + _CROP_PHASE2_NPC_GRAIN_SELL_FLOOR_SHIFT * crop_hoard_01
            g_buy_hi = 1.1 - _CROP_PHASE2_NPC_GRAIN_BUY_CEIL_SHIFT * crop_hoard_01
            if g_ratio < g_sell_lo and self._npc_cargo_qty(cargo, "grain") > 0:
                self._npc_sell_to_port(
                    trader, port_id, "grain", self._npc_roll_trade_lot_qty(trader, port_id, "grain", False)
                )
                return
            if g_ratio > g_buy_hi:
                self._npc_buy_from_port(
                    trader, port_id, "grain", self._npc_roll_trade_lot_qty(trader, port_id, "grain", True)
                )
                return
        if "wine" in self.goods:
            if w_ratio < 0.46 and self._npc_cargo_qty(cargo, "wine") > 0:
                self._npc_sell_to_port(
                    trader, port_id, "wine", self._npc_roll_trade_lot_qty(trader, port_id, "wine", False)
                )
                return
            if w_ratio > 1.02:
                self._npc_buy_from_port(
                    trader, port_id, "wine", self._npc_roll_trade_lot_qty(trader, port_id, "wine", True)
                )
                return
        if "metal" in self.goods:
            m_tgt = self._stock_target_for_good("metal")
            m_stock = self._port_stock_qty(port_id, "metal")
            m_ratio = float(m_stock) / float(max(1, m_tgt))
            if m_ratio < 0.36 and self._npc_cargo_qty(cargo, "metal") > 0:
                self._npc_sell_to_port(
                    trader, port_id, "metal", self._npc_roll_trade_lot_qty(trader, port_id, "metal", False)
                )
                return
            if m_ratio > 1.06:
                self._npc_buy_from_port(
                    trader, port_id, "metal", self._npc_roll_trade_lot_qty(trader, port_id, "metal", True)
                )
                return
        if "wire" in self.goods:
            wi_tgt = self._stock_target_for_good("wire")
            wi_stock = self._port_stock_qty(port_id, "wire")
            wi_ratio = float(wi_stock) / float(max(1, wi_tgt))
            if wi_ratio < 0.34 and self._npc_cargo_qty(cargo, "wire") > 0:
                self._npc_sell_to_port(
                    trader, port_id, "wire", self._npc_roll_trade_lot_qty(trader, port_id, "wire", False)
                )
                return
            if wi_ratio > 1.04:
                self._npc_buy_from_port(
                    trader, port_id, "wire", self._npc_roll_trade_lot_qty(trader, port_id, "wire", True)
                )
                return
        if "salt" in self.goods:
            sa_tgt = self._stock_target_for_good("salt")
            sa_stock = self._port_stock_qty(port_id, "salt")
            sa_ratio = float(sa_stock) / float(max(1, sa_tgt))
            if sa_ratio < 0.4 and self._npc_cargo_qty(cargo, "salt") > 0:
                self._npc_sell_to_port(
                    trader, port_id, "salt", self._npc_roll_trade_lot_qty(trader, port_id, "salt", False)
                )
                return
            if sa_ratio > 1.05:
                self._npc_buy_from_port(
                    trader, port_id, "salt", self._npc_roll_trade_lot_qty(trader, port_id, "salt", True)
                )
                return
        if "olive_oil" in self.goods:
            oo_tgt = self._stock_target_for_good("olive_oil")
            oo_stock = self._port_stock_qty(port_id, "olive_oil")
            oo_ratio = float(oo_stock) / float(max(1, oo_tgt))
            if oo_ratio < 0.4 and self._npc_cargo_qty(cargo, "olive_oil") > 0:
                self._npc_sell_to_port(
                    trader,
                    port_id,
                    "olive_oil",
                    self._npc_roll_trade_lot_qty(trader, port_id, "olive_oil", False),
                )
                return
            if oo_ratio > 1.03:
                self._npc_buy_from_port(
                    trader,
                    port_id,
                    "olive_oil",
                    self._npc_roll_trade_lot_qty(trader, port_id, "olive_oil", True),
                )
                return
        if "pottery" in self.goods:
            po_tgt = self._stock_target_for_good("pottery")
            po_stock = self._port_stock_qty(port_id, "pottery")
            po_ratio = float(po_stock) / float(max(1, po_tgt))
            if po_ratio < 0.38 and self._npc_cargo_qty(cargo, "pottery") > 0:
                self._npc_sell_to_port(
                    trader,
                    port_id,
                    "pottery",
                    self._npc_roll_trade_lot_qty(trader, port_id, "pottery", False),
                )
                return
            if po_ratio > 1.03:
                self._npc_buy_from_port(
                    trader,
                    port_id,
                    "pottery",
                    self._npc_roll_trade_lot_qty(trader, port_id, "pottery", True),
                )
                return
        if "fish" in self.goods:
            fi_tgt = self._stock_target_for_good("fish")
            fi_stock = self._port_stock_qty(port_id, "fish")
            fi_ratio = float(fi_stock) / float(max(1, fi_tgt))
            if fi_ratio < 0.4 and self._npc_cargo_qty(cargo, "fish") > 0:
                self._npc_sell_to_port(
                    trader, port_id, "fish", self._npc_roll_trade_lot_qty(trader, port_id, "fish", False)
                )
                return
            if fi_ratio > 1.04:
                self._npc_buy_from_port(
                    trader, port_id, "fish", self._npc_roll_trade_lot_qty(trader, port_id, "fish", True)
                )
                return
        if "timber" in self.goods:
            tb_tgt = self._stock_target_for_good("timber")
            tb_stock = self._port_stock_qty(port_id, "timber")
            tb_ratio = float(tb_stock) / float(max(1, tb_tgt))
            if tb_ratio < 0.38 and self._npc_cargo_qty(cargo, "timber") > 0:
                self._npc_sell_to_port(
                    trader, port_id, "timber", self._npc_roll_trade_lot_qty(trader, port_id, "timber", False)
                )
                return
            if tb_ratio > 1.03:
                self._npc_buy_from_port(
                    trader, port_id, "timber", self._npc_roll_trade_lot_qty(trader, port_id, "timber", True)
                )
                return
        if "textiles" in self.goods:
            tx_tgt = self._stock_target_for_good("textiles")
            tx_stock = self._port_stock_qty(port_id, "textiles")
            tx_ratio = float(tx_stock) / float(max(1, tx_tgt))
            if tx_ratio < 0.38 and self._npc_cargo_qty(cargo, "textiles") > 0:
                self._npc_sell_to_port(
                    trader,
                    port_id,
                    "textiles",
                    self._npc_roll_trade_lot_qty(trader, port_id, "textiles", False),
                )
                return
            if tx_ratio > 1.03:
                self._npc_buy_from_port(
                    trader,
                    port_id,
                    "textiles",
                    self._npc_roll_trade_lot_qty(trader, port_id, "textiles", True),
                )
                return
        if "spice" in self.goods:
            s_tgt = self._stock_target_for_good("spice")
            s_stock = self._port_stock_qty(port_id, "spice")
            s_ratio = float(s_stock) / float(max(1, s_tgt))
            if s_ratio < 0.38 and self._npc_cargo_qty(cargo, "spice") > 0:
                self._npc_sell_to_port(
                    trader, port_id, "spice", self._npc_roll_trade_lot_qty(trader, port_id, "spice", False)
                )
                return
            if s_ratio > 1.02:
                self._npc_buy_from_port(
                    trader, port_id, "spice", self._npc_roll_trade_lot_qty(trader, port_id, "spice", True)
                )
                return
        if "gold" in self.goods:
            au_tgt = self._stock_target_for_good("gold")
            au_stock = self._port_stock_qty(port_id, "gold")
            au_ratio = float(au_stock) / float(max(1, au_tgt))
            if au_ratio < 0.36 and self._npc_cargo_qty(cargo, "gold") > 0:
                self._npc_sell_to_port(
                    trader, port_id, "gold", self._npc_roll_trade_lot_qty(trader, port_id, "gold", False)
                )
                return
            if au_ratio > 1.02:
                self._npc_buy_from_port(
                    trader, port_id, "gold", self._npc_roll_trade_lot_qty(trader, port_id, "gold", True)
                )
                return
        if "silver" in self.goods:
            ag_tgt = self._stock_target_for_good("silver")
            ag_stock = self._port_stock_qty(port_id, "silver")
            ag_ratio = float(ag_stock) / float(max(1, ag_tgt))
            if ag_ratio < 0.36 and self._npc_cargo_qty(cargo, "silver") > 0:
                self._npc_sell_to_port(
                    trader, port_id, "silver", self._npc_roll_trade_lot_qty(trader, port_id, "silver", False)
                )
                return
            if ag_ratio > 1.02:
                self._npc_buy_from_port(
                    trader, port_id, "silver", self._npc_roll_trade_lot_qty(trader, port_id, "silver", True)
                )
                return
        if self._npc_try_optional_mint_bullion_at_dock(trader, port_id):
            return
        if "slaves" in self.goods:
            sl_tgt = self._stock_target_for_good("slaves")
            sl_stock = self._port_stock_qty(port_id, "slaves")
            sl_ratio = float(sl_stock) / float(max(1, sl_tgt))
            if sl_ratio < 0.4 and self._npc_cargo_qty(cargo, "slaves") > 0:
                self._npc_sell_to_port(
                    trader, port_id, "slaves", self._npc_roll_trade_lot_qty(trader, port_id, "slaves", False)
                )
                return
            if sl_ratio > 1.03:
                self._npc_buy_from_port(
                    trader, port_id, "slaves", self._npc_roll_trade_lot_qty(trader, port_id, "slaves", True)
                )
                return
        if roll < 0.5 and "grain" in self.goods:
            p_grain_buy = clampf(
                0.55 + _CROP_PHASE2_NPC_GRAIN_P_BUY_SHIFT * crop_hoard_01, 0.48, 0.90
            )
            if self.rng.random() < p_grain_buy:
                self._npc_buy_from_port(
                    trader, port_id, "grain", self._npc_roll_trade_lot_qty(trader, port_id, "grain", True)
                )
            else:
                if self._npc_cargo_qty(cargo, "grain") > 0:
                    self._npc_sell_to_port(
                        trader, port_id, "grain", self._npc_roll_trade_lot_qty(trader, port_id, "grain", False)
                    )
        elif "wine" in self.goods:
            if self.rng.random() < 0.55:
                self._npc_buy_from_port(
                    trader, port_id, "wine", self._npc_roll_trade_lot_qty(trader, port_id, "wine", True)
                )
            else:
                if self._npc_cargo_qty(cargo, "wine") > 0:
                    self._npc_sell_to_port(
                        trader, port_id, "wine", self._npc_roll_trade_lot_qty(trader, port_id, "wine", False)
                    )
        elif roll < 0.68 and "metal" in self.goods:
            if self.rng.random() < 0.52:
                self._npc_buy_from_port(
                    trader, port_id, "metal", self._npc_roll_trade_lot_qty(trader, port_id, "metal", True)
                )
            else:
                if self._npc_cargo_qty(cargo, "metal") > 0:
                    self._npc_sell_to_port(
                        trader, port_id, "metal", self._npc_roll_trade_lot_qty(trader, port_id, "metal", False)
                    )
        elif "wire" in self.goods:
            if self.rng.random() < 0.52:
                self._npc_buy_from_port(
                    trader, port_id, "wire", self._npc_roll_trade_lot_qty(trader, port_id, "wire", True)
                )
            else:
                if self._npc_cargo_qty(cargo, "wire") > 0:
                    self._npc_sell_to_port(
                        trader, port_id, "wire", self._npc_roll_trade_lot_qty(trader, port_id, "wire", False)
                    )

    def _npc_advance_voyages(self) -> None:
        idxm = self._npc_index_agents_by_id()
        for ags in self.npc_agents:
            if not isinstance(ags, dict):
                continue
            if not self._npc_convoy_is_follower(ags):
                continue
            cl0 = int(ags.get("convoy_leader_id", 0))
            if cl0 not in idxm:
                continue
            L0 = idxm[cl0]
            if not isinstance(L0, dict):
                continue
            if int(L0.get("voyage_days_remaining", 0)) <= 0:
                continue
            ags["voyage_days_remaining"] = int(L0.get("voyage_days_remaining", 0))
            ags["voyage_dest_id"] = str(L0.get("voyage_dest_id", ""))
            ags["voyage_booked_days"] = int(L0.get("voyage_booked_days", 0))
            ags["voyage_open_sea_01"] = clampf(float(L0.get("voyage_open_sea_01", 0.0)), 0.0, 1.0)
        for ag in self.npc_agents:
            if not isinstance(ag, dict):
                continue
            if self._npc_convoy_is_follower(ag):
                continue
            cl0 = int(ag.get("convoy_leader_id", 0))
            self_id0 = int(ag.get("id", 0))
            days = int(ag.get("voyage_days_remaining", 0))
            if days <= 0:
                continue
            days -= 1
            ag["voyage_days_remaining"] = days
            if cl0 == self_id0 and bool(ag.get("convoy_formed", False)):
                mm = ag.get("convoy_member_ids")
                if isinstance(mm, list):
                    for mid in mm:
                        fw = idxm.get(int(mid))
                        if not isinstance(fw, dict):
                            continue
                        if not self._npc_convoy_is_follower(fw):
                            continue
                        if int(fw.get("convoy_leader_id", 0)) != self_id0:
                            continue
                        fw["voyage_days_remaining"] = days
                esid0 = int(ag.get("convoy_escort_id", 0))
                if esid0 > 0 and esid0 in idxm:
                    exs = idxm[esid0]
                    if isinstance(exs, dict):
                        if str(exs.get("voyage_role", "")) == _VOYAGE_ROLE_ESCORT and int(
                            exs.get("convoy_leader_id", 0)
                        ) == self_id0:
                            exs["voyage_days_remaining"] = days
            if days != 0:
                continue
            dest = str(ag.get("voyage_dest_id", ""))
            member_ids_arrive = []
            if cl0 == self_id0 and bool(ag.get("convoy_formed", False)):
                mm2 = ag.get("convoy_member_ids")
                if isinstance(mm2, list):
                    member_ids_arrive = list(mm2)
            escort_arrive_id = int(ag.get("convoy_escort_id", 0))
            hire_player_arrive = bool(ag.get("convoy_escort_player", False))
            if hire_player_arrive:
                if (
                    str(self.player_voyage_role) == _VOYAGE_ROLE_ESCORT
                    and int(self.player_escort_contract.get("employer_id", -9)) == self_id0
                ):
                    self._player_escort_pay_on_convoy_arrival_py(ag)
                    self._player_finish_escort_on_npc_convoy_arrival_py(ag, dest)
            elif escort_arrive_id > 0 and escort_arrive_id in idxm:
                esca = idxm[escort_arrive_id]
                if isinstance(esca, dict):
                    if str(esca.get("voyage_role", "")) == _VOYAGE_ROLE_ESCORT and int(
                        esca.get("convoy_leader_id", 0)
                    ) == self_id0:
                        self._npc_escort_pay_on_convoy_arrival(ag, esca)
            self._npc_finish_npc_voyage_arrival(ag, dest)
            for mid2 in member_ids_arrive:
                mem = idxm.get(int(mid2))
                if not isinstance(mem, dict):
                    continue
                if not self._npc_convoy_is_follower(mem):
                    continue
                if str(mem.get("voyage_dest_id", "")) != dest:
                    continue
                self._npc_finish_npc_voyage_arrival(mem, dest)
            if escort_arrive_id > 0 and escort_arrive_id in idxm:
                escb = idxm[escort_arrive_id]
                if isinstance(escb, dict) and int(escb.get("voyage_days_remaining", 0)) <= 0:
                    self._npc_finish_npc_voyage_arrival(escb, dest)

    def _npc_trade_if_docked(self, agent: dict) -> None:
        if int(agent.get("voyage_days_remaining", 0)) != 0:
            return
        pid = str(agent.get("docked_port", ""))
        if not pid or pid not in self.port_names:
            return
        self._npc_fire_sale_for_cashflow_docked(pid, agent)
        self._npc_tick_one(pid, agent)
        if int(agent.get("voyage_days_remaining", 0)) != 0:
            return
        ex = self._npc_trait_f(agent, _NPC_TRAIT_EXTRA)
        p2 = clampf(0.72 + 0.06 * (ex - 0.5), 0.62, 0.80)
        if self.rng.random() < p2:
            self._npc_tick_one(pid, agent)
        if int(agent.get("voyage_days_remaining", 0)) != 0:
            return
        p3 = clampf(0.42 + 0.05 * (ex - 0.5), 0.32, 0.52)
        if self.rng.random() < p3:
            self._npc_tick_one(pid, agent)
        self._npc_liquidate_one_unit_if_dust_docked(pid, agent)
        self._npc_snapshot_price_memory(agent, pid)
        self._npc_maybe_voluntary_hull_fire_sale_if_docked(pid, agent)
        self._npc_try_offer_city_grain_contract(agent, pid)

    def _npc_apply_officer_pay_if_docked_after_trade(self) -> None:
        for ag in self.npc_agents:
            if not isinstance(ag, dict):
                continue
            if int(ag.get("voyage_days_remaining", 0)) != 0:
                continue
            pid = str(ag.get("docked_port", ""))
            if not pid or pid not in self.port_names:
                continue
            self._ensure_npc_ship_fields(ag)
            if "cargo" not in ag or not isinstance(ag["cargo"], dict):
                ag["cargo"] = {}
            cargo_d = ag["cargo"]
            ships = clampi(int(ag.get("fleet_ships", 1)), 1, _FLEET_MAX_SHIPS)
            srow_o = self._npc_ship_row(ag)
            culd_o = self._npc_cultural_ops_scale(ag)
            oph_o = max(1, int(srow_o.get("officer_pay_per_hull", 1)))
            off_sc_o = float(oph_o) * float(culd_o.get("officer_scale", 1.0))
            cap = {
                "money": clampi(int(ag.get("money", 0)), 0, _MAX_PURSE_COINS_PY),
                "cargo": cargo_d,
                "ship_condition": int(ag.get("ship_condition", _SHIP_CONDITION_MAX)),
                "ship_wine_counter": int(ag.get("ship_wine_counter", 0)),
                "fleet_ships": ships,
                "officer_pay_scale": off_sc_o,
            }
            self._tick_captain_officer_pay(cap)
            ag["money"] = clampi(int(cap.get("money", 0)), 0, _MAX_PURSE_COINS_PY)
            ag["ship_condition"] = clampi(
                int(cap.get("ship_condition", _SHIP_CONDITION_MAX)),
                _SHIP_CONDITION_MIN,
                _SHIP_CONDITION_MAX,
            )

    def _harbour_due_port_wealth_bump(self, port_id: str, take: int, traffic_berths: int) -> None:
        if take <= 0:
            return
        ps = str(port_id)
        if not ps or ps not in self.port_names:
            return
        self.port_harbour_due_coins_tick[ps] = int(self.port_harbour_due_coins_tick.get(ps, 0)) + int(take)
        n = max(1, int(traffic_berths))
        bonus_pct = min(_HARBOUR_BUSY_MAX_BONUS_PCT, max(0, n - 1) * _HARBOUR_BUSY_PER_DOCK_PCT)
        scaled = (take * (100 + bonus_pct)) // 100
        self._bump_port_wealth(ps, max(1, scaled // _HARBOUR_WEALTH_PER_COINS_PAID))

    def _npc_apply_harbour_dues_if_docked_after_trade(self) -> None:
        traffic_n: dict[str, int] = {}
        for ag0 in self.npc_agents:
            if not isinstance(ag0, dict):
                continue
            if int(ag0.get("voyage_days_remaining", 0)) != 0:
                continue
            dp = str(ag0.get("docked_port", ""))
            if not dp or dp not in self.port_names:
                continue
            traffic_n[dp] = traffic_n.get(dp, 0) + 1
        for ag in self.npc_agents:
            if not isinstance(ag, dict):
                continue
            if int(ag.get("voyage_days_remaining", 0)) != 0:
                continue
            pid = str(ag.get("docked_port", ""))
            if not pid or pid not in self.port_names:
                continue
            self._ensure_npc_ship_fields(ag)
            purse = clampi(int(ag.get("money", 0)), 0, _MAX_PURSE_COINS_PY)
            ships = clampi(int(ag.get("fleet_ships", 1)), 1, _FLEET_MAX_SHIPS)
            take = _take_harbour_due_from_purse(purse, ships)
            if take > 0:
                ag["money"] = clampi(purse - take, 0, _MAX_PURSE_COINS_PY)
                n_here = max(1, int(traffic_n.get(pid, 1)))
                self._harbour_due_port_wealth_bump(pid, take, n_here)

    def _norm_ship_condition_01(self, cond: int) -> float:
        span = max(1, _SHIP_CONDITION_MAX - _SHIP_CONDITION_MIN)
        return clampf((float(cond) - float(_SHIP_CONDITION_MIN)) / float(span), 0.0, 1.0)

    def _used_hull_fire_sale_payout(self, cond: int) -> int:
        u = self._norm_ship_condition_01(cond)
        frac = _USED_HULL_PAYOUT_FRAC_LOW + (_USED_HULL_PAYOUT_FRAC_HIGH - _USED_HULL_PAYOUT_FRAC_LOW) * u
        nom = _FLEET_SHIP_NOMINAL_COINS
        p = int(round(float(nom) * frac))
        return clampi(
            p,
            _USED_HULL_MIN_PAYOUT,
            nom - 12,
        )

    def _used_hull_listing_ask_from_payout(self, payout: int) -> int:
        ask = max(
            payout + 6,
            int(round(float(payout) * _USED_HULL_ASK_MARKUP)),
        )
        nom2 = _FLEET_SHIP_NOMINAL_COINS
        return min(nom2 - 8, ask)

    def _merge_hull_condition_on_buy(self, old_cond: int, old_ships: int, added_cond: int) -> int:
        os = max(1, old_ships)
        return clampi(
            int(round((float(old_cond) * float(os) + float(added_cond)) / float(os + 1))),
            _SHIP_CONDITION_MIN,
            _SHIP_CONDITION_MAX,
        )

    def _ensure_used_hull_listings_for_all_ports(self) -> None:
        for pid in self.port_order:
            self.port_used_hull_listings.setdefault(pid, [])

    def _used_hull_listings_array(self, port_id: str) -> list:
        ps = str(port_id)
        if ps not in self.port_names:
            return []
        return self.port_used_hull_listings.setdefault(ps, [])

    def _append_used_hull_listing(self, port_id: str, condition: int, ask: int) -> None:
        ps = str(port_id)
        if ps not in self.port_names:
            return
        arr = self._used_hull_listings_array(ps)
        while len(arr) >= _USED_HULL_MAX_PER_PORT:
            arr.pop(0)
        lid = self.next_used_hull_listing_id
        self.next_used_hull_listing_id += 1
        arr.append(
            {
                "id": lid,
                "ask": max(1, ask),
                "condition": clampi(condition, _SHIP_CONDITION_MIN, _SHIP_CONDITION_MAX),
            }
        )

    def _npc_try_fire_sale_one_hull_if_desperate(self, port_id: str, agent: dict) -> bool:
        """Drop one ship if fleet > 1 and hold fits in smaller convoy; coin + slip listing. Deterministic (no RNG)."""
        self._ensure_npc_ship_fields(agent)
        ships = clampi(int(agent.get("fleet_ships", 1)), 1, _FLEET_MAX_SHIPS)
        if ships <= 1:
            return False
        per_h = clampi(int(self._npc_ship_row(agent).get("cargo_per_hull", _FLEET_CARGO_PER_SHIP)), 1, 120)
        new_cap = per_h * (ships - 1)
        if self._npc_cargo_effective_used_units(agent) > new_cap:
            return False
        cond = clampi(int(agent.get("ship_condition", _SHIP_CONDITION_MAX)), _SHIP_CONDITION_MIN, _SHIP_CONDITION_MAX)
        payout = self._used_hull_fire_sale_payout(cond)
        ask = self._used_hull_listing_ask_from_payout(payout)
        agent["fleet_ships"] = ships - 1
        agent["money"] = clampi(int(agent.get("money", 0)) + payout, 0, _MAX_PURSE_COINS_PY)
        self._append_used_hull_listing(port_id, cond, ask)
        return True

    def _fleet_new_build_goods_present(self) -> bool:
        return "timber" in self.goods and "textiles" in self.goods and "metal" in self.goods

    def _tick_player_fleet_shipyard_order(self) -> None:
        d = clampi(int(self.player_fleet_shipyard_days_remaining), 0, 999)
        if d <= 0:
            return
        d -= 1
        self.player_fleet_shipyard_days_remaining = d
        if d > 0:
            return
        self.player_fleet_shipyard_port_id = ""
        ships0 = clampi(int(self.player_fleet_ships), 1, _FLEET_MAX_SHIPS)
        if ships0 >= _FLEET_MAX_SHIPS:
            return
        self.player_fleet_ships = min(_FLEET_MAX_SHIPS, ships0 + 1)

    def _npc_cancel_fleet_shipyard_order(self, agent: dict) -> None:
        days = clampi(int(agent.get("fleet_shipyard_days", 0)), 0, 999)
        if days <= 0:
            return
        ypid = str(agent.get("fleet_shipyard_port_id", ""))
        nb = self._npc_fleet_build_ints(agent)
        if ypid and ypid in self.port_names and self._fleet_new_build_goods_present():
            self._adjust_port_stock(ypid, "timber", int(nb.get("timber", _FLEET_NEW_SHIP_TIMBER)))
            self._adjust_port_stock(ypid, "textiles", int(nb.get("textiles", _FLEET_NEW_SHIP_TEXTILES)))
            self._adjust_port_stock(ypid, "metal", int(nb.get("metal", _FLEET_NEW_SHIP_METAL)))
        agent["money"] = clampi(int(agent.get("money", 0)) + int(nb.get("labor", _FLEET_NEW_SHIP_LABOR_COINS)), 0, _MAX_PURSE_COINS_PY)
        agent["fleet_shipyard_days"] = 0
        agent["fleet_shipyard_port_id"] = ""

    def _tick_npc_fleet_shipyard_orders(self) -> None:
        for ag in self.npc_agents:
            if not isinstance(ag, dict):
                continue
            days = clampi(int(ag.get("fleet_shipyard_days", 0)), 0, 999)
            if days <= 0:
                continue
            days -= 1
            ag["fleet_shipyard_days"] = days
            if days > 0:
                continue
            ag["fleet_shipyard_port_id"] = ""
            self._ensure_npc_ship_fields(ag)
            sh = clampi(int(ag.get("fleet_ships", 1)), 1, _FLEET_MAX_SHIPS)
            if sh >= _FLEET_MAX_SHIPS:
                continue
            ag["fleet_ships"] = min(_FLEET_MAX_SHIPS, sh + 1)

    def _npc_try_buy_used_hull_if_docked(self, agent: dict) -> None:
        if int(agent.get("voyage_days_remaining", 0)) != 0:
            return
        pid = str(agent.get("docked_port", ""))
        if not pid or pid not in self.port_names:
            return
        self._ensure_npc_ship_fields(agent)
        ships = clampi(int(agent.get("fleet_ships", 1)), 1, _FLEET_MAX_SHIPS)
        if ships >= _FLEET_MAX_SHIPS:
            return
        arr = self._used_hull_listings_array(pid)
        if not arr:
            return
        best_i = -1
        best_ask = 999999999
        best_cond = _SHIP_CONDITION_MAX
        for idx, row in enumerate(arr):
            if not isinstance(row, dict):
                continue
            ak = int(row.get("ask", 999999999))
            if ak < best_ask:
                best_ask = ak
                best_i = idx
                best_cond = clampi(int(row.get("condition", _SHIP_CONDITION_MAX)), _SHIP_CONDITION_MIN, _SHIP_CONDITION_MAX)
        if best_i < 0 or best_ask >= 999999000:
            return
        purse = clampi(int(agent.get("money", 0)), 0, _MAX_PURSE_COINS_PY)
        cushion = _NPC_PURSE_RESERVE + self._npc_officer_due_coins(agent) * 2
        if purse < best_ask + cushion:
            return
        if self.rng.random() > 0.62:
            return
        if int(agent.get("fleet_shipyard_days", 0)) > 0:
            self._npc_cancel_fleet_shipyard_order(agent)
        purse2 = clampi(int(agent.get("money", 0)), 0, _MAX_PURSE_COINS_PY)
        arr.pop(best_i)
        agent["money"] = clampi(purse2 - best_ask, 0, _MAX_PURSE_COINS_PY)
        self._bump_port_wealth(pid, max(1, best_ask // 16))
        agent["fleet_ships"] = min(_FLEET_MAX_SHIPS, ships + 1)
        cond0 = clampi(int(agent.get("ship_condition", _SHIP_CONDITION_MAX)), _SHIP_CONDITION_MIN, _SHIP_CONDITION_MAX)
        agent["ship_condition"] = self._merge_hull_condition_on_buy(cond0, ships, best_cond)

    def _npc_fire_sale_for_cashflow_docked(self, port_id: str, agent: dict) -> None:
        """Sell cargo at bid until officer purse met; empty hold + still short → must fire-sale hulls."""
        self._ensure_npc_ship_fields(agent)
        if "cargo" not in agent or not isinstance(agent["cargo"], dict):
            agent["cargo"] = {}
        rounds = 0
        while rounds < 512:
            rounds += 1
            ships = clampi(int(agent.get("fleet_ships", 1)), 1, _FLEET_MAX_SHIPS)
            need_purse = self._npc_officer_due_coins(agent)
            purse = clampi(int(agent.get("money", 0)), 0, _MAX_PURSE_COINS_PY)
            if purse >= need_purse:
                return
            cargo = agent["cargo"]
            progressed = False
            if self._npc_cargo_total_units(agent) > 0:
                for pass_i in range(2):
                    for gid2 in self.goods.keys():
                        gid = str(gid2)
                        staple = gid in ("grain", "wine")
                        if pass_i == 0 and staple:
                            continue
                        if pass_i == 1 and not staple:
                            continue
                        if self._npc_cargo_qty(cargo, gid) <= 0:
                            continue
                        if self._npc_effective_sell_unit(agent, port_id, gid) <= 0:
                            continue
                        have = self._npc_cargo_qty(cargo, gid)
                        chunk = min(have, 24)
                        self._npc_sell_to_port(agent, port_id, gid, chunk)
                        progressed = True
                        break
                    if progressed:
                        break
            if progressed:
                continue
            # No more cargo to sell at bid; must fire-sale hulls until solvent or down to one ship.
            if ships > 1 and self._npc_try_fire_sale_one_hull_if_desperate(port_id, agent):
                continue
            return

    def _npc_liquidate_one_unit_if_dust_docked(self, port_id: str, agent: dict) -> None:
        dust_need = self._npc_dock_dust_purse_floor(agent)
        for _ in range(_NPC_DOCK_DUST_MAX_UNITS):
            if clampi(int(agent.get("money", 0)), 0, _MAX_PURSE_COINS_PY) >= dust_need:
                return
            cargo = agent.get("cargo")
            if not isinstance(cargo, dict):
                return
            sold = False
            for gid in list(cargo.keys()):
                if gid in self.goods and self._npc_cargo_qty(cargo, gid) > 0:
                    self._npc_sell_to_port(agent, port_id, gid, 1)
                    sold = True
                    break
            if not sold:
                sh = clampi(int(agent.get("fleet_ships", 1)), 1, _FLEET_MAX_SHIPS)
                purse = clampi(int(agent.get("money", 0)), 0, _MAX_PURSE_COINS_PY)
                need_off = self._npc_officer_due_coins(agent)
                thin_purse = purse < max(need_off, dust_need)
                if (
                    sh > 1
                    and thin_purse
                    and self._npc_cargo_total_units(agent) == 0
                    and self._npc_try_fire_sale_one_hull_if_desperate(port_id, agent)
                ):
                    continue
                return

    def _npc_maybe_voluntary_hull_fire_sale_if_docked(self, port_id: str, agent: dict) -> None:
        """Solvent on officer pay; stochastic trim — same slip listing as forced fire-sales."""
        self._ensure_npc_ship_fields(agent)
        ships = clampi(int(agent.get("fleet_ships", 1)), 1, _FLEET_MAX_SHIPS)
        if ships <= 1:
            return
        need_purse = self._npc_officer_due_coins(agent)
        purse = clampi(int(agent.get("money", 0)), 0, _MAX_PURSE_COINS_PY)
        if purse < need_purse:
            return
        per_h = clampi(int(self._npc_ship_row(agent).get("cargo_per_hull", _FLEET_CARGO_PER_SHIP)), 1, 120)
        new_cap = per_h * (ships - 1)
        if self._npc_cargo_effective_used_units(agent) > new_cap:
            return
        self._ensure_npc_risk_aversion(agent)
        ra = clampf(float(agent.get("risk_aversion", 0.5)), 0.0, 1.0)
        p_vol = 0.0
        if ships >= 4:
            p_vol += 0.034
        if ships >= 3 and ra > 0.62:
            p_vol += 0.042
        if ships >= 3 and purse >= need_purse + 320:
            p_vol += 0.022
        p_vol = clampf(p_vol, 0.0, 0.11)
        n_big = self._npc_trait_f(agent, _NPC_TRAIT_NEURO)
        c_big = self._npc_trait_f(agent, _NPC_TRAIT_CONSC)
        p_vol *= 1.0 + 0.24 * max(0.0, n_big - 0.45)
        p_vol *= 1.0 - 0.20 * max(0.0, c_big - 0.55) * (1.0 - n_big)
        p_vol = clampf(p_vol, 0.0, 0.14)
        if self.rng.random() >= p_vol:
            return
        self._npc_try_fire_sale_one_hull_if_desperate(port_id, agent)

    def _npc_try_expand_fleet_if_docked(self, agent: dict) -> None:
        """Labor + port timber/textiles/metal; ~90 days (mirrors player shipyard)."""
        if int(agent.get("voyage_days_remaining", 0)) != 0:
            return
        pid = str(agent.get("docked_port", ""))
        if not pid or pid not in self.port_names:
            return
        self._ensure_npc_ship_fields(agent)
        if int(agent.get("fleet_shipyard_days", 0)) > 0:
            return
        if not self._fleet_new_build_goods_present():
            return
        ships = clampi(int(agent.get("fleet_ships", 1)), 1, _FLEET_MAX_SHIPS)
        if ships >= _FLEET_MAX_SHIPS:
            return
        nb = self._npc_fleet_build_ints(agent)
        labor_n = int(nb.get("labor", _FLEET_NEW_SHIP_LABOR_COINS))
        timb_n = int(nb.get("timber", _FLEET_NEW_SHIP_TIMBER))
        tex_n = int(nb.get("textiles", _FLEET_NEW_SHIP_TEXTILES))
        met_n = int(nb.get("metal", _FLEET_NEW_SHIP_METAL))
        day_n = int(nb.get("days", _FLEET_NEW_SHIP_BUILD_DAYS))
        purse = clampi(int(agent.get("money", 0)), 0, _MAX_PURSE_COINS_PY)
        oph = max(1, int(self._npc_ship_row(agent).get("officer_pay_per_hull", 1)))
        culd = self._npc_cultural_ops_scale(agent)
        off_sc = float(oph) * float(culd.get("officer_scale", 1.0))
        cushion = _NPC_PURSE_RESERVE + max(
            1, int(math.ceil(float(ships * _SHIP_OFFICER_PAY_DAILY * 2) * off_sc))
        )
        need = labor_n + cushion
        if purse < need:
            return
        if self._port_stock_qty(pid, "timber") < timb_n:
            return
        if self._port_stock_qty(pid, "textiles") < tex_n:
            return
        if self._port_stock_qty(pid, "metal") < met_n:
            return
        excess = purse - need
        p_buy = clampf(0.13 + float(excess) / 4200.0, 0.09, 0.60)
        c_exp = self._npc_trait_f(agent, _NPC_TRAIT_CONSC)
        n_exp = self._npc_trait_f(agent, _NPC_TRAIT_NEURO)
        p_buy += 0.055 * (c_exp - 0.5) * (0.52 - n_exp)
        p_buy = clampf(p_buy, 0.08, 0.68)
        if self.rng.random() > p_buy:
            return
        agent["money"] = clampi(purse - labor_n, 0, _MAX_PURSE_COINS_PY)
        self._adjust_port_stock(pid, "timber", -timb_n)
        self._adjust_port_stock(pid, "textiles", -tex_n)
        self._adjust_port_stock(pid, "metal", -met_n)
        agent["fleet_shipyard_port_id"] = pid
        agent["fleet_shipyard_days"] = day_n

    def _npc_pick_trading_dest_any_port(self, agent: dict, here: str) -> str:
        rows: list[dict] = []
        for pid in self.port_order:
            ps = str(pid)
            if ps == here:
                continue
            sc = self._npc_voyage_dest_score(agent, here, ps)
            rows.append({"id": ps, "sc": sc})
        if not rows:
            return ""
        rows.sort(key=lambda r: float(r["sc"]), reverse=True)
        pick_n = min(3, len(rows))
        idx = self.rng.randint(0, pick_n - 1)
        return str(rows[idx].get("id", ""))

    def _port_slave_labor_demand(self, port_id: str) -> int:
        if "slaves" not in self.goods:
            return 0
        ps = str(port_id)
        sumd = 0
        for fd in self.farms:
            if str(fd.get("port_id", "")) != ps:
                continue
            g = max(0, int(fd.get("grain_per_day", 0)))
            w = max(0, int(fd.get("wine_per_day", 0)))
            fi = max(0, int(fd.get("fish_per_day", 0)))
            if g <= 0 and w <= 0 and fi <= 0:
                continue
            sumd += max(
                1,
                (g * _SLAVE_DEM_FARM_GRAIN + w * _SLAVE_DEM_FARM_WINE + fi * _SLAVE_DEM_FARM_FISH + 9) // 10,
            )
        for md in self.mines:
            if str(md.get("port_id", "")) != ps:
                continue
            mt = max(0, int(md.get("metal_per_day", 0)))
            wr = max(0, int(md.get("wire_per_day", 0)))
            ga = max(0, int(md.get("gold_per_day", 0)))
            sv = max(0, int(md.get("silver_per_day", 0)))
            if mt <= 0 and wr <= 0 and ga <= 0 and sv <= 0:
                continue
            sumd += max(
                1,
                (
                    mt * _SLAVE_DEM_MINE_METAL
                    + wr * _SLAVE_DEM_MINE_WIRE
                    + ga * _SLAVE_DEM_MINE_GOLD
                    + sv * _SLAVE_DEM_MINE_SILVER
                    + 9
                )
                // 10,
            )
        return sumd

    def _port_slave_output_mult(self, port_id: str) -> float:
        if "slaves" not in self.goods:
            return 1.0
        dem = self._port_slave_labor_demand(port_id)
        if dem <= 0:
            return 1.0
        have = self._port_stock_qty(str(port_id), "slaves")
        return max(_SLAVE_OUTPUT_FLOOR, min(1.0, float(have) / float(dem)))

    def _last_slave_lost_for_port(self, ps: str) -> int:
        d = self.last_slave_digest.get(ps)
        if not isinstance(d, dict):
            return 0
        return max(0, int(d.get("lost", 0)))

    def _last_slave_output_mult_for_port(self, ps: str) -> float:
        d = self.last_slave_digest.get(ps)
        if isinstance(d, dict):
            return float(d.get("output_mult", 1.0))
        return self._port_slave_output_mult(ps)

    def _grant_war_slave_captives(self, port_id: str, campaign_days: int) -> None:
        if "slaves" not in self.goods:
            return
        ps = str(port_id)
        cd = clampi(campaign_days, 1, 500)
        jitter = self.rng.randint(-_SLAVE_WAR_CAPTIVES_JITTER, _SLAVE_WAR_CAPTIVES_JITTER)
        add = (
            _SLAVE_WAR_CAPTIVES_BASE
            + jitter
            + (cd * _SLAVE_WAR_CAPTIVES_PER_CAMPAIGN_DAY) // _SLAVE_WAR_CAPTIVES_DAY_DEN
        )
        add = max(0, add)
        if add <= 0:
            return
        self._adjust_port_stock(ps, "slaves", add)
        prev = self.last_slave_digest.get(ps)
        if isinstance(prev, dict):
            prev["captives"] = add
        else:
            self.last_slave_digest[ps] = {
                "demand": self._port_slave_labor_demand(ps),
                "have_start": self._port_stock_qty(ps, "slaves"),
                "lost": 0,
                "output_mult": 1.0,
                "captives": add,
            }

    def _tick_slave_attrition_for_ports(self) -> None:
        self.last_slave_digest.clear()
        if "slaves" not in self.goods:
            return
        for pid in self.port_order:
            ps = str(pid)
            dem = self._port_slave_labor_demand(ps)
            have = self._port_stock_qty(ps, "slaves")
            mult0 = self._port_slave_output_mult(ps)
            base_loss = int(math.floor(float(have) * _SLAVE_ATTRITION_FRAC))
            gap = max(0, dem - have)
            over_loss = int(math.ceil(float(gap) * _SLAVE_ATTRITION_OVERWORK_MUL))
            loss = min(have, base_loss + over_loss)
            if loss > 0:
                self._adjust_port_stock(ps, "slaves", -loss)
            self.last_slave_digest[ps] = {
                "demand": dem,
                "have_start": have,
                "lost": loss,
                "output_mult": mult0,
                "captives": 0,
            }

    def _calendar_doy_1based(self) -> int:
        d = max(1, int(self.current_day))
        return ((d - 1) % _CALENDAR_YEAR_LEN) + 1

    def _is_harvest_doy(self, doy: int) -> bool:
        return _HARVEST_START_DOY <= doy <= _HARVEST_END_DOY

    def _season_is_summer_for_war(self, doy: int) -> bool:
        return _SEASON_SUMMER_START_DOY <= doy <= _SEASON_SUMMER_END_DOY

    def _crop_daily_scale(self, doy: int) -> float:
        return _CROP_HARVEST_DAILY_SCALE if self._is_harvest_doy(doy) else _CROP_OFFSEASON_SCALE

    def _season_storm_probability_scale(self, doy: int) -> float:
        if doy >= _SEASON_WINTER_START_DOY:
            return _STORM_SEASON_WINTER_MULT
        if doy >= _HARVEST_START_DOY:
            return _STORM_SEASON_AUTUMN_MULT
        return 1.0

    def _season_fish_mult(self, doy: int) -> float:
        if doy >= _SEASON_WINTER_START_DOY:
            return _FISH_SEASON_WINTER_MULT
        return 1.0

    def _ensure_port_crop_agro_all_ports(self) -> None:
        doy = self._calendar_doy_1based()
        for pid in self.port_order:
            ps = str(pid)
            if ps in self.port_crop_moisture_01:
                continue
            t = _crop_seasonal_moisture_target_01_py(doy, ps)
            self.port_crop_moisture_01[ps] = t
            self.port_crop_growth_01[ps] = t

    def _init_port_crop_agro_state(self) -> None:
        self.port_crop_moisture_01.clear()
        self.port_crop_growth_01.clear()
        self._ensure_port_crop_agro_all_ports()
        self._init_port_crop_information_state()

    def _init_port_crop_information_state(self) -> None:
        self.port_local_crop_belief_01.clear()
        self.port_inbound_crop_reports.clear()
        self.port_crop_rumor_public_delta.clear()

    def _decay_crop_rumor_public_deltas(self) -> None:
        if not self._world_crop_agro_model:
            return
        doy = self._calendar_doy_1based()
        harv = self._is_harvest_doy(doy)
        rm: list[str] = []
        for pk in list(self.port_crop_rumor_public_delta.keys()):
            ps = str(pk)
            if ps not in self.port_names:
                rm.append(ps)
                continue
            d = float(self.port_crop_rumor_public_delta[ps])
            d *= _CROP_RUMOR_DAILY_DECAY
            if harv:
                d *= _CROP_RUMOR_HARVEST_EXTRA_DECAY
            if abs(d) < 0.0035:
                rm.append(ps)
            else:
                self.port_crop_rumor_public_delta[ps] = clampf(
                    d, -_CROP_RUMOR_DELTA_ABS_MAX, _CROP_RUMOR_DELTA_ABS_MAX
                )
        for rk in rm:
            self.port_crop_rumor_public_delta.pop(rk, None)

    def _maybe_roll_sicilian_crop_rumor_event(self) -> None:
        if not self._world_crop_agro_model:
            return
        if self.rng.random() >= _CROP_RUMOR_SICILY_EVENT_DAILY_P:
            return
        bumper = self.rng.random() < 0.57
        if bumper:
            mag = self.rng.uniform(_CROP_RUMOR_SICILY_BUMPER_MAG_MIN, _CROP_RUMOR_SICILY_BUMPER_MAG_MAX)
        else:
            mag = self.rng.uniform(_CROP_RUMOR_SICILY_FAIL_MAG_MIN, _CROP_RUMOR_SICILY_FAIL_MAG_MAX)
        dd = -mag if bumper else mag
        gt_sic = 0.5
        corr = 0.0
        if "messana" in self.port_names and "panormus" in self.port_names:
            gt_sic = 0.5 * (
                self._crop_grain_stress_gt_01_for_port("messana")
                + self._crop_grain_stress_gt_01_for_port("panormus")
            )
            corr = _CROP_RUMOR_GT_CORREL * (gt_sic - 0.5) * (1.0 if bumper else -1.0)
        elif "messana" in self.port_names:
            gt_sic = self._crop_grain_stress_gt_01_for_port("messana")
            corr = _CROP_RUMOR_GT_CORREL * (gt_sic - 0.5) * (1.0 if bumper else -1.0)
        for ps in _SICILY_CROP_RUMOR_LISTENER_PORT_IDS:
            if ps not in self.port_names:
                continue
            cur = float(self.port_crop_rumor_public_delta.get(ps, 0.0))
            self.port_crop_rumor_public_delta[ps] = clampf(
                cur + dd + corr, -_CROP_RUMOR_DELTA_ABS_MAX, _CROP_RUMOR_DELTA_ABS_MAX
            )

    def _tick_crop_rumor_events_phase4(self) -> None:
        self._decay_crop_rumor_public_deltas()
        self._maybe_roll_sicilian_crop_rumor_event()

    def _tick_port_crop_agro(self) -> None:
        if not self._world_crop_agro_model:
            return
        self._ensure_port_crop_agro_all_ports()
        doy = self._calendar_doy_1based()
        for pid in self.port_order:
            ps = str(pid)
            tgt = _crop_seasonal_moisture_target_01_py(doy, ps)
            m = clampf(float(self.port_crop_moisture_01.get(ps, 0.5)), 0.0, 1.0)
            m = m + (tgt - m) * _CROP_MOISTURE_ADJUST_RATE
            self.port_crop_moisture_01[ps] = m
            g = clampf(float(self.port_crop_growth_01.get(ps, 0.5)), 0.0, 1.0)
            g = g + (m - g) * _CROP_GROWTH_LAG_RATE
            self.port_crop_growth_01[ps] = g

    def _crop_grain_stress_gt_01_for_port(self, port_id: str) -> float:
        if not self._world_crop_agro_model:
            return 0.0
        ps = str(port_id)
        g = clampf(float(self.port_crop_growth_01.get(ps, 0.5)), 0.0, 1.0)
        return clampf(1.0 - g, 0.0, 1.0)

    def _crop_grain_stress_01_for_port(self, port_id: str) -> float:
        return self._crop_grain_stress_gt_01_for_port(port_id)

    def _crop_grain_stress_01_market_for_port(self, port_id: str) -> float:
        if not self._world_crop_agro_model:
            return 0.0
        ps = str(port_id)
        gt_f = self._crop_grain_stress_gt_01_for_port(ps)
        local_b = clampf(float(self.port_local_crop_belief_01.get(ps, gt_f)), 0.0, 1.0)
        blended = local_b
        arr = self.port_inbound_crop_reports.get(ps)
        if isinstance(arr, list) and len(arr) > 0:
            sm = sum(clampf(float(v), 0.0, 1.0) for v in arr)
            avg = sm / float(len(arr))
            w = _CROP_INFO_MARKET_LOCAL_WEIGHT
            blended = clampf(w * local_b + (1.0 - w) * avg, 0.0, 1.0)
        rumor_d = clampf(
            float(self.port_crop_rumor_public_delta.get(ps, 0.0)),
            -_CROP_RUMOR_DELTA_ABS_MAX,
            _CROP_RUMOR_DELTA_ABS_MAX,
        )
        return clampf(blended + rumor_d, 0.0, 1.0)

    def _port_crop_inbound_report_count(self, port_id: str) -> int:
        arr = self.port_inbound_crop_reports.get(str(port_id))
        return len(arr) if isinstance(arr, list) else 0

    def _append_port_crop_arrival_report(self, dest: str, report_val: float) -> None:
        ps = str(dest)
        if ps not in self.port_names:
            return
        if ps not in self.port_inbound_crop_reports:
            self.port_inbound_crop_reports[ps] = []
        arr = self.port_inbound_crop_reports[ps]
        arr.append(clampf(float(report_val), 0.0, 1.0))
        while len(arr) > _CROP_INFO_MARKET_REPORT_MAX:
            arr.pop(0)

    def _refresh_port_local_crop_beliefs(self) -> None:
        if not self._world_crop_agro_model:
            return
        for pid in self.port_order:
            ps = str(pid)
            gt = self._crop_grain_stress_gt_01_for_port(ps)
            noise = self.rng.uniform(-_CROP_INFO_LOCAL_NOISE_MAX, _CROP_INFO_LOCAL_NOISE_MAX)
            self.port_local_crop_belief_01[ps] = clampf(gt + noise, 0.0, 1.0)
        for ag in self.npc_agents:
            if not isinstance(ag, dict):
                continue
            if str(ag.get("voyage_role", _VOYAGE_ROLE_MERCHANT)) != _VOYAGE_ROLE_MERCHANT:
                continue
            if int(ag.get("voyage_days_remaining", 0)) != 0:
                continue
            dp = str(ag.get("docked_port", ""))
            hp = str(ag.get("home_port", ""))
            if not dp or dp not in self.port_names:
                continue
            if hp == dp:
                lb0 = clampf(
                    float(self.port_local_crop_belief_01.get(dp, self._crop_grain_stress_gt_01_for_port(dp))),
                    0.0,
                    1.0,
                )
                ag["crop_stress_belief_01"] = clampf(
                    lb0 + self.rng.uniform(-_CROP_INFO_LOCAL_NOISE_MAX * 0.25, _CROP_INFO_LOCAL_NOISE_MAX * 0.25),
                    0.0,
                    1.0,
                )

    def _npc_apply_crop_information_on_arrival(self, ag: dict, dest: str) -> None:
        if not self._world_crop_agro_model:
            return
        if str(ag.get("voyage_role", _VOYAGE_ROLE_MERCHANT)) != _VOYAGE_ROLE_MERCHANT:
            return
        d = str(dest)
        if d not in self.port_names:
            return
        origin = str(ag.get("voyage_origin_port_id", ""))
        if not origin or origin not in self.port_names:
            origin = str(ag.get("home_port", ""))
        if not origin or origin not in self.port_names:
            ag["voyage_origin_port_id"] = ""
            return
        gt_o = self._crop_grain_stress_gt_01_for_port(origin)
        nz = self.rng.uniform(-_CROP_INFO_REPORT_NOISE_MAX, _CROP_INFO_REPORT_NOISE_MAX)
        rep = clampf(gt_o + nz, 0.0, 1.0)
        if not self._npc_convoy_is_follower(ag):
            self._append_port_crop_arrival_report(d, rep)
        home = str(ag.get("home_port", ""))
        if home != d:
            ag["crop_stress_belief_01"] = rep
        else:
            loc_b = clampf(float(self.port_local_crop_belief_01.get(d, gt_o)), 0.0, 1.0)
            ag["crop_stress_belief_01"] = clampf(
                loc_b + self.rng.uniform(-_CROP_INFO_LOCAL_NOISE_MAX * 0.35, _CROP_INFO_LOCAL_NOISE_MAX * 0.35),
                0.0,
                1.0,
            )
        ag["voyage_origin_port_id"] = ""
        if not self._npc_convoy_is_follower(ag) and self.rng.random() < _CROP_RUMOR_HIGH_TRUST_DAMP_P:
            if d in self.port_crop_rumor_public_delta:
                rd0 = float(self.port_crop_rumor_public_delta[d])
                rd0 *= _CROP_RUMOR_HIGH_TRUST_DAMP_MULT
                if abs(rd0) < 0.0035:
                    self.port_crop_rumor_public_delta.pop(d, None)
                else:
                    self.port_crop_rumor_public_delta[d] = clampf(
                        rd0, -_CROP_RUMOR_DELTA_ABS_MAX, _CROP_RUMOR_DELTA_ABS_MAX
                    )

    def _crop_grain_yield_mult_for_port(self, port_id: str) -> float:
        if not self._world_crop_agro_model:
            return 1.0
        g = clampf(float(self.port_crop_growth_01.get(str(port_id), 0.5)), 0.0, 1.0)
        return _CROP_GRAIN_YIELD_MULT_MIN + (_CROP_GRAIN_YIELD_MULT_MAX - _CROP_GRAIN_YIELD_MULT_MIN) * g

    def _crop_grain_buy_price_stress_mult(self, port_id: str) -> float:
        if not self._world_crop_agro_model:
            return 1.0
        st = self._crop_grain_stress_01_market_for_port(port_id)
        return 1.0 + clampf(st - _CROP_STRESS_PRICE_BUY_THRESHOLD, 0.0, 1.0) * _CROP_STRESS_PRICE_BUY_EXTRA

    def _crop_grain_sell_price_stress_mult(self, port_id: str) -> float:
        if not self._world_crop_agro_model:
            return 1.0
        st = self._crop_grain_stress_01_market_for_port(port_id)
        return 1.0 - clampf(st - _CROP_STRESS_PRICE_SELL_THRESHOLD, 0.0, 1.0) * _CROP_STRESS_PRICE_SELL_DISC

    def _crop_phase2_neighbor_max_grain(self, port_id: str) -> int:
        ps = str(port_id)
        mx = 0
        nr = self.port_neighbors.get(ps)
        if not nr:
            return 0
        for x in nr:
            nb = str(x)
            if nb not in self.port_names:
                continue
            mx = max(mx, self._port_stock_qty(nb, "grain"))
        return mx

    def _crop_phase2_stress_major_gate(self, port_id: str) -> bool:
        if not self._world_crop_agro_model:
            return False
        ps = str(port_id)
        if ps not in self.port_names:
            return False
        if not self.is_port_at_war(ps):
            return False
        m01 = clampf(float(self.port_crop_moisture_01.get(ps, 0.5)), 0.0, 1.0)
        if m01 > _CROP_PHASE2_DROUGHT_MOISTURE_MAX:
            return False
        if self._crop_phase2_neighbor_max_grain(ps) > _CROP_PHASE2_NEIGHBOR_GRAIN_ISOLATED_MAX:
            return False
        return True

    def _crop_phase2_grain_trade_bias_add(self, port_id: str) -> float:
        if not self._world_crop_agro_model or "grain" not in self.goods:
            return 0.0
        st = self._crop_grain_stress_01_market_for_port(port_id)
        if st < _CROP_PHASE2_BIAS_STRESS_LO:
            return 0.0
        span = max(0.0001, _CROP_PHASE2_BIAS_STRESS_HI - _CROP_PHASE2_BIAS_STRESS_LO)
        t = clampf((st - _CROP_PHASE2_BIAS_STRESS_LO) / span, 0.0, 1.0)
        add = t * _CROP_PHASE2_BIAS_MAX_ADD
        if self._crop_phase2_stress_major_gate(port_id) and st >= _CROP_PHASE2_BIAS_MAJOR_STRESS_MIN:
            add += _CROP_PHASE2_BIAS_MAJOR_EXTRA
        return clampf(add, 0.0, _TRADE_PRICE_BIAS_CLAMP)

    def _crop_phase2_food_unrest_addon(self, port_id: str) -> int:
        if not self._world_crop_agro_model:
            return 0
        st = self._crop_grain_stress_gt_01_for_port(port_id)
        n = 0
        if st >= _CROP_PHASE2_UNREST_STRESS_HIGH:
            n = _CROP_PHASE2_UNREST_ADD_HIGH
        elif st >= _CROP_PHASE2_UNREST_STRESS_MID:
            n = _CROP_PHASE2_UNREST_ADD_MID
        if self._crop_phase2_stress_major_gate(port_id) and st >= _CROP_PHASE2_UNREST_MAJOR_STRESS_MIN:
            n += _CROP_PHASE2_UNREST_ADD_MAJOR
        return min(_CROP_PHASE2_UNREST_DAILY_CAP, n)

    def _crop_phase2_npc_hoard_weight_01(self, port_id: str) -> float:
        if not self._world_crop_agro_model:
            return 0.0
        st = self._crop_grain_stress_01_market_for_port(port_id)
        hw = clampf((st - _CROP_PHASE2_HOARD_STRESS_LO) / 0.42, 0.0, 1.0)
        if self._crop_phase2_stress_major_gate(port_id):
            hw = min(1.0, hw + _CROP_PHASE2_HOARD_MAJOR_BOOST)
        return clampf(hw * 0.88, 0.0, 1.0)

    def _farm_breadbasket_grain_wine_mult(self, port_id: str) -> float:
        if str(self.port_roles.get(str(port_id), "")) == _PORT_ROLE_BREADBASKET:
            return float(_BREADBASKET_FARM_GRAIN_WINE_MULT)
        return 1.0

    def _apply_farm_production(self) -> None:
        wine_help_used: dict[str, int] = {}
        doy = self._calendar_doy_1based()
        crop_sc = self._crop_daily_scale(doy)
        fish_mul = self._season_fish_mult(doy)
        for fd in self.farms:
            pid = str(fd.get("port_id", ""))
            if not pid or pid not in self.port_names:
                continue
            gadd = int(fd.get("grain_per_day", 0))
            wadd = int(fd.get("wine_per_day", 0))
            farm_mult = _WAR_FARM_OUTPUT_MULT if self.is_port_at_war(pid) else 1.0
            pop_sc = self._population_output_scale_for_port(pid)
            slave_sc = self._port_slave_output_mult(pid)
            basket_m = self._farm_breadbasket_grain_wine_mult(pid)
            if gadd > 0 and "grain" in self.goods:
                yld_m = self._crop_grain_yield_mult_for_port(pid)
                g_ship = max(
                    0,
                    int(
                        math.floor(
                            float(gadd)
                            * crop_sc
                            * farm_mult
                            * pop_sc
                            * slave_sc
                            * basket_m
                            * float(_FARM_GRAIN_MASS_MULT)
                            * yld_m
                        )
                    ),
                )
                if g_ship > 0:
                    self._adjust_port_stock(pid, "grain", g_ship)
            if wadd > 0 and "wine" in self.goods:
                w_ship = max(
                    0,
                    int(
                        math.floor(
                            float(wadd) * crop_sc * farm_mult * pop_sc * slave_sc * basket_m
                        )
                    ),
                )
                used = int(wine_help_used.get(pid, 0))
                extra = self._farm_wine_help_extra(pid, used)
                wine_help_used[pid] = used + extra
                if w_ship + extra > 0:
                    self._adjust_port_stock(pid, "wine", w_ship + extra)
            fadd = int(fd.get("fish_per_day", 0))
            if fadd > 0 and "fish" in self.goods:
                f_ship = max(
                    0,
                    int(math.floor(float(fadd) * fish_mul * farm_mult * pop_sc * slave_sc)),
                )
                if f_ship > 0:
                    self._adjust_port_stock(pid, "fish", f_ship)

    def _apply_mine_production(self) -> None:
        for md in self.mines:
            pid = str(md.get("port_id", ""))
            if not pid or pid not in self.port_names:
                continue
            madd = int(md.get("metal_per_day", 0))
            wadd = int(md.get("wire_per_day", 0))
            pop_sc = self._population_output_scale_for_port(pid)
            slave_sc = self._port_slave_output_mult(pid)
            if madd > 0 and "metal" in self.goods:
                m_ship = max(0, int(math.floor(float(madd) * pop_sc * slave_sc)))
                if m_ship > 0:
                    self._adjust_port_stock(pid, "metal", m_ship)
            if wadd > 0 and "wire" in self.goods:
                w_ship = max(0, int(math.floor(float(wadd) * pop_sc * slave_sc)))
                if w_ship > 0:
                    self._adjust_port_stock(pid, "wire", w_ship)
            gadd = int(md.get("gold_per_day", 0))
            if gadd > 0 and "gold" in self.goods:
                g_ship = max(0, int(math.floor(float(gadd) * pop_sc * slave_sc)))
                if g_ship > 0:
                    self._adjust_port_stock(pid, "gold", g_ship)
            sadd = int(md.get("silver_per_day", 0))
            if sadd > 0 and "silver" in self.goods:
                s_ship = max(0, int(math.floor(float(sadd) * pop_sc * slave_sc)))
                if s_ship > 0:
                    self._adjust_port_stock(pid, "silver", s_ship)

    def _apply_mint_pulse_to_treasury(self) -> None:
        for pid, cfg0 in self.port_mint_cfg.items():
            ps = str(pid)
            if ps not in self.port_names:
                continue
            if not isinstance(cfg0, dict):
                continue
            gb = clampi(int(cfg0.get("gold_per_batch", 1)), 0, 24)
            sb = clampi(int(cfg0.get("silver_per_batch", 2)), 0, 36)
            if gb <= 0 and sb <= 0:
                continue
            c_pb = clampi(int(cfg0.get("coins_per_batch", 72)), 1, 500)
            mx = clampi(int(cfg0.get("max_batches_per_day", 6)), 1, 40)
            sf = clampf(float(cfg0.get("treasury_sink_frac", 0.09)), 0.0, 0.45)
            b = 0
            while b < mx:
                if gb > 0 and self._port_stock_qty(ps, "gold") < gb:
                    break
                if sb > 0 and self._port_stock_qty(ps, "silver") < sb:
                    break
                if gb > 0:
                    self._adjust_port_stock(ps, "gold", -gb)
                if sb > 0:
                    self._adjust_port_stock(ps, "silver", -sb)
                self.world_treasury_coins = clampi(self.world_treasury_coins + c_pb, 0, _WORLD_TREASURY_MAX)
                sk = max(0, int(math.floor(float(c_pb) * sf)))
                self.world_treasury_coins = clampi(
                    self.world_treasury_coins - min(sk, self.world_treasury_coins), 0, _WORLD_TREASURY_MAX
                )
                wb = clampi(max(1, int(math.floor(float(c_pb) * _MINT_STRIKE_WEALTH_FRAC))), 1, _MINT_STRIKE_WEALTH_BONUS_MAX)
                self._bump_port_wealth(ps, wb)
                b += 1

    def _apply_granary_spoilage(self) -> None:
        if "grain" not in self.goods:
            return
        for ps in self.port_order:
            g = self._port_stock_qty(ps, "grain")
            if g <= 0:
                self._last_grain_spoilage[ps] = 0
                continue
            loss = int(math.ceil(float(g) * _GRAIN_SPOIL_FRACTION))
            if g > _GRAIN_SPOIL_MIN_STOCK and loss < 1:
                loss = 1
            loss = min(g, min(_GRAIN_SPOIL_CAP, max(0, loss)))
            if loss <= 0:
                self._last_grain_spoilage[ps] = 0
                continue
            self._last_grain_spoilage[ps] = loss
            self._adjust_port_stock(ps, "grain", -loss)

    def _init_port_food_unrest_zero(self) -> None:
        self.port_food_unrest = {pid: 0 for pid in self.port_order}

    def _ensure_sim_agent_port_defaults(self) -> None:
        for pid in self.port_order:
            ps = str(pid)
            self.port_commerce_pulse.setdefault(ps, 0.38)
            self.port_cartel_strength.setdefault(ps, 0.0)
            self.port_war_rumor.setdefault(ps, 0.0)
            self.port_plague_days.setdefault(ps, 0)
            self.port_rumor_good_delta.setdefault(ps, {})

    def _rumor_extra_delta_for_port_good(self, port_id: str, good_id: str) -> float:
        ps = str(port_id)
        gid = str(good_id)
        row = self.port_rumor_good_delta.get(ps)
        if not isinstance(row, dict) or gid not in row:
            return 0.0
        return float(row[gid])

    def _rumor_price_mult_for_port_good(self, port_id: str, good_id: str) -> float:
        ps = str(port_id)
        wr = clampf(float(self.port_war_rumor.get(ps, 0.0)), 0.0, 1.0)
        ex = self._rumor_extra_delta_for_port_good(ps, good_id)
        return _rumor_price_mult_py(wr, str(good_id), ex)

    def _agent_information_decay_tick(self) -> None:
        for pid in self.port_order:
            ps = str(pid)
            wr = clampf(float(self.port_war_rumor.get(ps, 0.0)), 0.0, 1.0)
            self.port_war_rumor[ps] = clampf(wr * 0.965, 0.0, 1.0)
            row = self.port_rumor_good_delta.get(ps)
            if not isinstance(row, dict):
                continue
            rm: list[str] = []
            for gk, gv in list(row.items()):
                v = float(gv) * 0.86
                if abs(v) < 0.002:
                    rm.append(str(gk))
                else:
                    row[str(gk)] = v
            for rk in rm:
                row.pop(rk, None)
        for pid in self.port_order:
            ps = str(pid)
            if self.get_port_war_days_remaining(ps) > 0:
                continue
            neigh = self.port_neighbors.get(ps)
            if not isinstance(neigh, list):
                continue
            bump = 0.0
            for ni in neigh:
                nb = str(ni)
                if self.get_port_war_days_remaining(nb) > 0:
                    bump += 0.034
            if bump > 0.0:
                cur2 = clampf(float(self.port_war_rumor.get(ps, 0.0)), 0.0, 1.0)
                self.port_war_rumor[ps] = clampf(cur2 + min(0.22, bump), 0.0, 1.0)

    def _npc_tick_scatter_memory_decay(self) -> None:
        for ag in self.npc_agents:
            if not isinstance(ag, dict):
                continue
            if str(ag.get("voyage_role", _VOYAGE_ROLE_MERCHANT)) != _VOYAGE_ROLE_MERCHANT:
                continue
            scv = ag.get("scattered_ids")
            if isinstance(scv, list) and len(scv) > 0:
                if self.rng.random() < _SCATTERED_IDS_DECAY_DAILY_P:
                    ri = self.rng.randint(0, len(scv) - 1)
                    scv.pop(ri)
                    ag["scattered_ids"] = scv
            if int(ag.get("voyage_days_remaining", 0)) <= 0:
                b0 = clampf(float(ag.get("contact_candidate_bias", 0.0)), 0.0, 1.0)
                if b0 > 0.001:
                    b0 = clampf(b0 * _NPC_CONTACT_BIAS_DOCKED_DECAY_MULT, 0.0, 1.0)
                    if b0 < 0.02:
                        b0 = 0.0
                    ag["contact_candidate_bias"] = b0

    def _agent_information_post_trade_tick(self) -> None:
        for pid in self.port_order:
            ps = str(pid)
            if self.rng.random() >= 0.0028:
                continue
            if not self.goods:
                continue
            keys = list(self.goods.keys())
            pick = str(keys[self.rng.randint(0, len(keys) - 1)])
            row = self.port_rumor_good_delta.setdefault(ps, {})
            d0 = float(row.get(pick, 0.0))
            row[pick] = clampf(d0 + self.rng.uniform(-0.056, 0.056), -0.12, 0.12)

    def _agent_production_tick_farms_mines_slaves(self) -> None:
        self._apply_farm_production()
        self._apply_mine_production()
        self._apply_mint_pulse_to_treasury()
        self._tick_slave_attrition_for_ports()

    def _agent_industry_and_war_materiel_tick(self) -> None:
        self._apply_industrial_metal_sinks()
        self._apply_war_materiel_consumption()

    def _agent_merchant_cartel_tick(self) -> None:
        for pid in self.port_order:
            ps = str(pid)
            rich = 0
            for ag in self.npc_agents:
                if not isinstance(ag, dict):
                    continue
                if int(ag.get("voyage_days_remaining", 0)) != 0:
                    continue
                if str(ag.get("docked_port", "")) != ps:
                    continue
                if clampi(int(ag.get("money", 0)), 0, _MAX_PURSE_COINS_PY) >= 260:
                    rich += 1
            c = clampf(float(self.port_cartel_strength.get(ps, 0.0)), 0.0, 1.0)
            if rich >= 4:
                c = clampf(c + 0.07, 0.0, 1.0)
            else:
                c = max(0.0, c - 0.055)
            self.port_cartel_strength[ps] = c

    def _port_total_trade_units_in_stock(self, port_id: str) -> int:
        ps = str(port_id)
        if ps not in self.port_names:
            return 0
        sumu = 0
        for gid in self.goods.keys():
            gis = str(gid)
            if gis in ("gold", "silver"):
                continue
            sumu += self._port_stock_qty(ps, gis)
        return sumu

    def _home_port_deserves_bankruptcy_replacement(self, home: str) -> bool:
        ps = str(home)
        if ps not in self.port_names:
            return False
        cm = self._port_commerce_tick.get(ps, {})
        if isinstance(cm, dict):
            bu = int(cm.get("npc_buy_units", 0))
            su = int(cm.get("npc_sell_units", 0))
            bc = int(cm.get("npc_buy_coins", 0))
            sc = int(cm.get("npc_sell_coins", 0))
            if bu + su > 0 or bc + sc > 0:
                return True
        pulse = clampf(float(self.port_commerce_pulse.get(ps, 0.0)), 0.0, 1.0)
        if pulse >= _NPC_BANKRUPTCY_REPLACE_MIN_PULSE:
            return True
        return self._port_total_trade_units_in_stock(ps) >= _NPC_BANKRUPTCY_REPLACE_MIN_PORT_STOCK_UNITS

    def _agent_merchant_sync_home_counts_to_pulse(self) -> None:
        for pid in self.port_order:
            ps = str(pid)
            base = clampi(int(self.port_npc_trader_count.get(ps, 4)), 1, _PORT_NPC_TRADERS_LOAD_MAX)
            pulse = clampf(float(self.port_commerce_pulse.get(ps, 0.38)), 0.0, 1.0)
            bonus = int(round((pulse - 0.38) * 7.0))
            att = self._wealth_stock_target_for_port(ps)
            wv = int(self.port_wealth.get(ps, att))
            if float(wv) < float(max(1, att)) * 0.82:
                bonus -= 1
            if pulse < 0.22:
                bonus -= 1
            want = max(1, base + bonus)
            cur = 0
            for ag in self.npc_agents:
                if not isinstance(ag, dict):
                    continue
                if str(ag.get("home_port", "")) == ps:
                    cur += 1
            if cur < want:
                add_n = min(_MERCHANT_HOME_COUNT_STEP_MAX, want - cur)
                for _ in range(add_n):
                    self.npc_agents.append(self._new_npc_agent(ps))
                    cur += 1
            elif cur > want:
                rem_n = min(_MERCHANT_HOME_COUNT_STEP_MAX, cur - want)
                for _ in range(rem_n):
                    worst_i = -1
                    worst_bs = 2_147_483_647
                    worst_id = 2_147_483_647
                    for i2, ag2 in enumerate(self.npc_agents):
                        if not isinstance(ag2, dict):
                            continue
                        if str(ag2.get("home_port", "")) != ps:
                            continue
                        bs2 = self._npc_merchant_balance_sheet_coins(ag2)
                        id2 = int(ag2.get("id", 0))
                        if bs2 < worst_bs or (bs2 == worst_bs and id2 > worst_id):
                            worst_bs = bs2
                            worst_id = id2
                            worst_i = i2
                    if worst_i >= 0:
                        del self.npc_agents[worst_i]
                        cur -= 1
                    else:
                        break

    def _agent_city_commerce_pulse_tick(self) -> None:
        for pid in self.port_order:
            ps = str(pid)
            docked = self._count_npc_docked_at(ps)
            hc = clampi(int(self.port_harbour_due_coins_tick.get(ps, 0)), 0, _MAX_PURSE_COINS_PY)
            cm = self._port_commerce_tick.get(ps, {})
            bu = int(cm.get("npc_buy_units", 0))
            su = int(cm.get("npc_sell_units", 0))
            bc = int(cm.get("npc_buy_coins", 0))
            sc = int(cm.get("npc_sell_coins", 0))
            raw = _commerce_activity_raw_py(docked, hc, bu, su, bc, sc)
            prev = max(
                _COMMERCE_PULSE_PREV_FLOOR,
                clampf(float(self.port_commerce_pulse.get(ps, 0.38)), 0.0, 1.0),
            )
            self.port_commerce_pulse[ps] = _commerce_pulse_ema_py(prev, raw)

    def _luxury_import_far_good_ids(self) -> list[str]:
        out: list[str] = []
        for gid in self.goods.keys():
            g = str(gid)
            if str(self.goods[g].get("need_tier", "")) != "luxury":
                continue
            if g in ("gold", "silver"):
                continue
            out.append(g)
        return out

    def _luxury_import_apply_coin_sink(self, port_id: str, sink_total: int) -> None:
        ps = str(port_id)
        if sink_total <= 0 or ps not in self.port_names:
            return
        ttf = clampf(
            float(self._luxury_import_cfg.get("treasury_take_frac", _LUXURY_IMPORT_TREASURY_TAKE_FRAC_DEFAULT)),
            0.0,
            0.95,
        )
        from_t = min(self.world_treasury_coins, int(math.ceil(float(sink_total) * ttf)))
        self.world_treasury_coins = clampi(self.world_treasury_coins - from_t, 0, _WORLD_TREASURY_MAX)
        remain = sink_total - from_t
        if remain <= 0:
            return
        docked: list[dict] = []
        for ag in self.npc_agents:
            if not isinstance(ag, dict):
                continue
            if int(ag.get("voyage_days_remaining", 0)) > 0:
                continue
            if str(ag.get("docked_port", "")) != ps:
                continue
            docked.append(ag)
        guard = 0
        while remain > 0 and guard < 500:
            guard += 1
            progressed = False
            for ag2 in docked:
                purse0 = clampi(int(ag2.get("money", 0)), 0, _MAX_PURSE_COINS_PY)
                headroom = purse0 - _NPC_PURSE_RESERVE - 1
                if headroom <= 0:
                    continue
                take = min(remain, max(1, headroom // 3))
                take = min(take, headroom)
                if take <= 0:
                    continue
                ag2["money"] = clampi(purse0 - take, 0, _MAX_PURSE_COINS_PY)
                remain -= take
                progressed = True
            if not progressed:
                break
        if remain > 0:
            pv = max(0, int(self.port_wealth.get(ps, 0)) - 22)
            if pv > 0:
                self._bump_port_wealth(ps, -min(pv, remain))

    def _luxury_import_tick(self) -> None:
        if not bool(self._luxury_import_cfg.get("enabled", True)):
            return
        for pid in self.port_order:
            ps = str(pid)
            arr0 = self._port_luxury_import_queue.get(ps)
            if not isinstance(arr0, list):
                continue
            i = 0
            while i < len(arr0):
                c0 = arr0[i]
                if not isinstance(c0, dict):
                    arr0.pop(i)
                    continue
                d0 = int(c0.get("d", 0)) - 1
                c0["d"] = d0
                if d0 > 0:
                    i += 1
                    continue
                gid = str(c0.get("g", ""))
                qv = max(0, int(c0.get("q", 0)))
                arr0.pop(i)
                if gid not in self.goods or qv <= 0:
                    continue
                unit0 = self._compute_player_buy_unit(ps, gid, False)
                notional = max(1, qv * max(1, unit0))
                cfrac = clampf(
                    float(self._luxury_import_cfg.get("cost_frac", _LUXURY_IMPORT_COST_FRAC_DEFAULT)),
                    0.05,
                    0.88,
                )
                sink_total = clampi(
                    int(math.floor(float(notional) * cfrac)),
                    1,
                    _LUXURY_IMPORT_SINK_CAP,
                )
                self._luxury_import_apply_coin_sink(ps, sink_total)
                self._adjust_port_stock(ps, gid, qv)
        mxq = clampi(int(self._luxury_import_cfg.get("max_pending", 4)), 1, 12)
        spawn_roll = clampf(float(self._luxury_import_cfg.get("spawn_roll", 0.10)), 0.0, 0.6)
        lead_lo = clampi(int(self._luxury_import_cfg.get("lead_min", 3)), 1, 30)
        lead_hi = clampi(int(self._luxury_import_cfg.get("lead_max", 8)), lead_lo, 40)
        q_lo = clampi(int(self._luxury_import_cfg.get("qty_min", 1)), 1, 12)
        q_hi = clampi(int(self._luxury_import_cfg.get("qty_max", 3)), q_lo, 16)
        cands = self._luxury_import_far_good_ids()
        if cands:
            for pid2 in self.port_order:
                ps2 = str(pid2)
                if self.rng.random() > spawn_roll * clampf(
                    0.28 + float(self.port_commerce_pulse.get(ps2, 0.38)) * 1.05, 0.18, 1.2
                ):
                    continue
                arr2 = self._port_luxury_import_queue.setdefault(ps2, [])
                if len(arr2) >= mxq:
                    continue
                pick_g = str(cands[self.rng.randrange(len(cands))])
                if pick_g not in self.goods:
                    continue
                tgt = self._stock_target_for_good(pick_g)
                stk = self._port_stock_qty(ps2, pick_g)
                tight = float(stk) / float(max(1, tgt))
                if tight > 1.08 and self.rng.random() < 0.72:
                    continue
                qn = self.rng.randint(q_lo, q_hi)
                ld = self.rng.randint(lead_lo, lead_hi)
                arr2.append({"g": pick_g, "q": qn, "d": ld})

    def _agent_war_tick_end_of_day(self) -> None:
        self._tick_war_countdown()
        self._tick_war_recurring_peace()

    def _count_npc_docked_at(self, port_id: str) -> int:
        ps = str(port_id)
        n = 0
        for ag in self.npc_agents:
            if not isinstance(ag, dict):
                continue
            if int(ag.get("voyage_days_remaining", 0)) != 0:
                continue
            if str(ag.get("docked_port", "")) == ps:
                n += 1
        return n

    def _run_daily_population_and_npcs(self) -> None:
        self._last_grain_spoilage.clear()
        self.last_pop_digest.clear()
        self.last_war_industry_digest.clear()
        self.last_industrial_sink_digest.clear()
        self.last_slave_digest.clear()
        self._reset_port_commerce_tick()
        for ps in self.port_order:
            self.port_harbour_due_coins_tick[str(ps)] = 0
        self._agent_information_decay_tick()
        self._npc_tick_scatter_memory_decay()
        self._ensure_sim_agent_port_defaults()
        self._tick_all_npc_captain_ship_costs()
        self._tick_npc_storms_at_sea()
        self._npc_pirate_encounters_tick()
        self._npc_advance_voyages()
        self._tick_player_fleet_shipyard_order()
        self._tick_npc_fleet_shipyard_orders()
        self._tick_port_crop_agro()
        self._refresh_port_local_crop_beliefs()
        self._tick_crop_rumor_events_phase4()
        self._agent_production_tick_farms_mines_slaves()
        for pid in self.port_order:
            self._refresh_port_wealth(pid)
        doy_pop = self._calendar_doy_1based()
        forage_today = self._summer_forage_mouths_for_doy(doy_pop)
        for pid_s in self.port_order:
            eat = self.get_population_grain_eat_effective(pid_s)
            ghave = self._port_stock_qty(pid_s, "grain") if "grain" in self.goods else 0
            food_days_pre = 9999.0
            if eat > 0:
                food_days_pre = float(ghave) / float(eat)
            rationing = bool(self.port_rationing_active.get(pid_s, False))
            rationing_days = clampi(int(self.port_rationing_days_active.get(pid_s, 0)), 0, 999)
            if rationing:
                rationing_days = min(999, rationing_days + 1)
                if food_days_pre > _RATION_END_FOOD_DAYS or rationing_days > _RATION_MAX_DAYS:
                    rationing = False
                    rationing_days = 0
            elif eat > 0 and food_days_pre < _RATION_TRIGGER_FOOD_DAYS:
                rationing = True
                rationing_days = 1
            self.port_rationing_active[pid_s] = rationing
            self.port_rationing_days_active[pid_s] = rationing_days
            eat_today = eat
            if rationing and eat > 0:
                eat_today = min(eat, max(_RATION_BITE_MIN, int(round(float(eat) * _RATION_BITE_FRAC))))
            eaten_g = 0
            if eat_today > 0 and "grain" in self.goods:
                eaten_g = min(eat_today, ghave)
                if eaten_g > 0:
                    self._adjust_port_stock(pid_s, "grain", -eaten_g)
            preserved_used = 0
            shortfall = max(0, eat - eaten_g)
            if shortfall > 0:
                avail_p = float(self.port_preserved_food.get(pid_s, 0.0))
                if avail_p >= 1.0:
                    take = min(shortfall, int(math.floor(avail_p)))
                    if take > 0:
                        preserved_used = take
                        self.port_preserved_food[pid_s] = avail_p - float(take)
            if rationing:
                u_now = clampi(int(self.port_food_unrest.get(pid_s, 0)), 0, 200)
                self.port_food_unrest[pid_s] = clampi(u_now + _RATION_UNREST_TICK, 0, 200)
            if eat > 0 and food_days_pre >= _PRESERVED_FOOD_FILL_FOODDAYS_MIN:
                cur_p = float(self.port_preserved_food.get(pid_s, 0.0))
                cap_p = float(self._preserved_food_cap_for_port(pid_s))
                if cur_p < cap_p:
                    self.port_preserved_food[pid_s] = clampf(cur_p + _PRESERVED_FOOD_FILL_PER_DAY, 0.0, cap_p)
            eaten_w = 0
            if "wine" in self.goods:
                w_base = int(self.port_population_wine_base.get(pid_s, 1))
                wealth = int(self.port_wealth.get(pid_s, 100))
                w_extra = clampi(int(float(wealth) / 95.0), 0, 14)
                want_w = clampi(w_base + w_extra, 0, 50)
                whave = self._port_stock_qty(pid_s, "wine")
                eaten_w = min(want_w, whave)
                if eaten_w > 0:
                    self._adjust_port_stock(pid_s, "wine", -eaten_w)
            eaten_f = 0
            if "fish" in self.goods:
                want_f = clampi(int(self.port_population_fish_per_day.get(pid_s, 0)), 0, 40)
                if want_f > 0:
                    fhave = self._port_stock_qty(pid_s, "fish")
                    eaten_f = min(want_f, fhave)
                    if eaten_f > 0:
                        self._adjust_port_stock(pid_s, "fish", -eaten_f)
            self.last_pop_digest[pid_s] = {
                "grain": eaten_g,
                "wine": eaten_w,
                "fish": eaten_f,
                "preserved": preserved_used,
                "forage": forage_today,
                "rationing": 1 if rationing else 0,
            }
        self._agent_industry_and_war_materiel_tick()
        self._replenish_wine_vineyards_after_bites()
        for ag in self.npc_agents:
            self._npc_trade_if_docked(ag)
        self._npc_try_peer_loans_after_dock_trade()
        self._npc_docked_toll_graft_tick()
        self._npc_apply_harbour_dues_if_docked_after_trade()
        self._npc_apply_officer_pay_if_docked_after_trade()
        self._npc_merchant_seasoned_mastery_tick()
        self._npc_tick_merchant_city_contracts_docked()
        for ag in self.npc_agents:
            self._npc_try_buy_used_hull_if_docked(ag)
        for ag in self.npc_agents:
            self._npc_try_expand_fleet_if_docked(ag)
        self._npc_convoy_formation_and_depart_tick()
        self._npc_pirate_spawn_docked_tick()
        self._npc_pirate_dock_depart_tick()
        self._agent_information_post_trade_tick()
        self._agent_merchant_cartel_tick()
        self._agent_city_commerce_pulse_tick()
        self._luxury_import_tick()
        self.commerce_daily_log.append(
            {
                "day": int(self.current_day),
                "ports": {str(ps): dict(self._port_commerce_tick[str(ps)]) for ps in self.port_order},
            }
        )
        self._apply_granary_spoilage()
        self._npc_cull_bankrupts()
        self._finalize_daily_grain_food_days_and_unrest()
        self._agent_war_tick_end_of_day()
        self._tick_population_demographics()
        self._agent_merchant_sync_home_counts_to_pulse()
        for pid in self.port_order:
            ps = str(pid)
            g0 = clampi(int(self.port_peace_riot_grace_days.get(ps, 0)), 0, 999)
            if g0 > 0:
                self.port_peace_riot_grace_days[ps] = g0 - 1
        day_max_purse = 0
        day_hulls = 0
        for ag in self.npc_agents:
            if not isinstance(ag, dict):
                continue
            day_max_purse = max(day_max_purse, clampi(int(ag.get("money", 0)), 0, _MAX_PURSE_COINS_PY))
            self._ensure_npc_ship_fields(ag)
            self._normalize_npc_convoy_invariants_py(ag)
            self._ensure_npc_escort_reputation_fields(ag)
            day_hulls += clampi(int(ag.get("fleet_ships", 1)), 1, _FLEET_MAX_SHIPS)
        self.npc_purse_peak_run = max(self.npc_purse_peak_run, day_max_purse)
        self.npc_fleet_hulls_peak_run = max(self.npc_fleet_hulls_peak_run, day_hulls)

    def _tick_war_countdown(self) -> None:
        for ps in self.port_order:
            r = clampi(int(self.port_war_days_remaining.get(ps, 0)), 0, 999)
            if r <= 0:
                continue
            burst_len = max(1, int(self.port_war_burst_initial.get(ps, r)))
            nxt = r - 1
            self.port_war_days_remaining[ps] = nxt
            if nxt == 0:
                self._grant_war_slave_captives(ps, burst_len)
                self.port_war_burst_initial.pop(ps, None)
                if bool(self.port_war_recurring.get(ps, False)):
                    self.port_war_peace_remaining[ps] = self.rng.randint(
                        _WAR_CYCLE_PEACE_MIN,
                        _WAR_CYCLE_PEACE_MAX,
                    )
                u0 = clampi(int(self.port_food_unrest.get(ps, 0)), 0, 200)
                self.port_food_unrest[ps] = max(0, u0 - _WAR_PEACE_FOOD_UNREST_VENT)
                self.port_peace_riot_grace_days[ps] = _WAR_PEACE_RIOT_GRACE_DAYS

    def _tick_war_recurring_peace(self) -> None:
        doy = self._calendar_doy_1based()
        for ps in self.port_order:
            if not bool(self.port_war_recurring.get(ps, False)):
                continue
            if self.get_port_war_days_remaining(ps) > 0:
                continue
            pend = clampi(int(self.port_war_pending_burst.get(ps, 0)), 0, 999)
            if pend > 0 and self._season_is_summer_for_war(doy):
                self.port_war_days_remaining[ps] = pend
                self.port_war_burst_initial[ps] = pend
                self.port_war_pending_burst.pop(ps, None)
                continue
            pr = clampi(int(self.port_war_peace_remaining.get(ps, 0)), 0, 999)
            if pr <= 0:
                continue
            nxt = pr - 1
            self.port_war_peace_remaining[ps] = nxt
            if nxt == 0:
                burst = self.rng.randint(
                    _WAR_RECURRING_BURST_MIN,
                    _WAR_RECURRING_BURST_MAX,
                )
                if self._season_is_summer_for_war(doy):
                    self.port_war_days_remaining[ps] = burst
                    self.port_war_burst_initial[ps] = burst
                else:
                    self.port_war_pending_burst[ps] = burst

    def _apply_one_food_riot(self, port_id: str, eat: int, unrest: int, riot_lines: list[str]) -> int:
        cap_loot = eat * self.rng.randint(2, 5) + self.rng.randint(4, 18)
        loot_g = min(self._port_stock_qty(port_id, "grain"), cap_loot)
        if loot_g > 0:
            self._adjust_port_stock(port_id, "grain", -loot_g)
        wine_l = 0
        if "wine" in self.goods:
            sw = self._port_stock_qty(port_id, "wine")
            wine_l = min(sw, self.rng.randint(2, 10))
            if wine_l > 0:
                self._adjust_port_stock(port_id, "wine", -wine_l)
        wv = int(self.port_wealth.get(port_id, 100))
        smash = self.rng.randint(35, 95)
        self.port_wealth[port_id] = clampi(wv - smash, 25, 999999)
        name = self.port_names.get(port_id, port_id)
        line = f"{name} food riot: ~{loot_g} grain"
        if wine_l > 0:
            line += f", {wine_l} wine"
        line += f" seized; prosperity −{smash}."
        riot_lines.append(line)
        self.riot_events += 1
        self.last_food_riot_by_port[str(port_id)] = 1
        return clampi(int(round(float(unrest) * _FOOD_RIOT_UNREST_SCALE)), 10, 62)

    def _finalize_daily_grain_food_days_and_unrest(self) -> None:
        self.last_food_riot_summary = ""
        self.last_food_riot_by_port = {p: 0 for p in self.port_order}
        if "grain" not in self.goods:
            self.last_grain_food_days.clear()
            return
        riot_lines: list[str] = []
        for pid_s in self.port_order:
            eat = self.get_population_grain_eat_effective(pid_s)
            if eat <= 0:
                self.last_grain_food_days[pid_s] = 9999.0
                continue
            gstock = self._port_stock_qty(pid_s, "grain")
            days_r = float(gstock) / float(eat)
            self.last_grain_food_days[pid_s] = days_r
            base_eat = clampi(int(self.port_population_grain.get(pid_s, 0)), 0, 120)
            days_panic = days_r
            if self.is_port_at_war(pid_s) and base_eat > 0:
                days_panic = float(gstock) / float(base_eat)
            u = clampi(int(self.port_food_unrest.get(pid_s, 0)), 0, 200)
            dig = self.last_pop_digest.get(pid_s, {})
            eaten_g = int(dig.get("grain", 0))
            if eaten_g >= eat:
                tight_runway = min(days_panic, days_r) < _FOOD_UNREST_TIGHT_RUNWAY_DAYS
                dec = _FOOD_UNREST_DECAY_WHEN_TIGHT if tight_runway else _FOOD_UNREST_DECAY
                u = max(0, u - dec)
            elif self.is_port_at_war(pid_s) and base_eat > 0 and eaten_g >= base_eat:
                tight2 = min(days_panic, days_r) < _FOOD_UNREST_TIGHT_RUNWAY_DAYS
                dec2 = _FOOD_UNREST_DECAY_WHEN_TIGHT if tight2 else _FOOD_UNREST_DECAY
                u = max(0, u - dec2)
                gap = eat - eaten_g
                if gap > 0:
                    u += gap * _FOOD_UNREST_WAR_RATION_GAP_PER
            else:
                u += _FOOD_UNREST_SHORTAGE + (eat - eaten_g) * _FOOD_UNREST_PER_MISS
            pm = self._war_panic_mult_for_port(pid_s)
            if days_panic < 1.0:
                u += int(
                    round(
                        float(_FOOD_UNREST_PANIC_LT1DAY)
                        * (pm if self.is_port_at_war(pid_s) else 1.0)
                    )
                )
            if days_panic < 0.5:
                u += int(
                    round(
                        float(_FOOD_UNREST_CRITICAL_DAYS)
                        * (pm if self.is_port_at_war(pid_s) else 1.0)
                    )
                )
            if min(days_panic, days_r) < _FOOD_UNREST_TIGHT_RUNWAY_DAYS:
                u += _FOOD_UNREST_TIGHT_RUNWAY_DRIP
            if self._world_crop_agro_model:
                u += self._crop_phase2_food_unrest_addon(pid_s)
            u = clampi(u, 0, 200)
            riot_thr = self._food_riot_threshold_for_port(pid_s)
            runway_worst = min(days_panic, days_r)
            famine_riot_eligible = (
                eaten_g < eat and runway_worst < _FOOD_RIOT_ELIGIBLE_RUNWAY_MAX
            )
            if u >= riot_thr:
                if famine_riot_eligible:
                    p_riot = min(
                        1.0,
                        _FOOD_RIOT_ROLL_BASE + float(u - riot_thr) / _FOOD_RIOT_ROLL_PER_OVER,
                    )
                    if self.rng.random() < p_riot:
                        u = self._apply_one_food_riot(pid_s, eat, u, riot_lines)
                    else:
                        u = clampi(u - _FOOD_RIOT_NEAR_MISS_VENT, 0, 200)
                else:
                    u = clampi(u - _FOOD_RIOT_NO_FAMINE_VENT, 0, 200)
            self.port_food_unrest[pid_s] = u
        if riot_lines:
            self.last_food_riot_summary = "; ".join(riot_lines)

    def _tick_all_npc_captain_ship_costs(self) -> None:
        for ag in self.npc_agents:
            if not isinstance(ag, dict):
                continue
            self._ensure_npc_ship_fields(ag)
            if "cargo" not in ag or not isinstance(ag["cargo"], dict):
                ag["cargo"] = {}
            cargo_d = ag["cargo"]
            days = int(ag.get("voyage_days_remaining", 0))
            was_at_sea = days > 0
            docked_for_repair = days <= 0
            ships = clampi(int(ag.get("fleet_ships", 1)), 1, _FLEET_MAX_SHIPS)
            srow = self._npc_ship_row(ag)
            culd = self._npc_cultural_ops_scale(ag)
            oph = max(1, int(srow.get("officer_pay_per_hull", 1)))
            off_sc = float(oph) * float(culd.get("officer_scale", 1.0))
            cap = {
                "money": clampi(int(ag.get("money", 0)), 0, _MAX_PURSE_COINS_PY),
                "cargo": cargo_d,
                "ship_condition": int(ag.get("ship_condition", _SHIP_CONDITION_MAX)),
                "ship_wine_counter": int(ag.get("ship_wine_counter", 0)),
                "fleet_ships": ships,
                "crew_wine_per_ship": max(1, int(srow.get("crew_wine_per_ship", 1))),
                "crew_wine_cultural_scale": float(culd.get("wine_scale", 1.0)),
                "officer_pay_scale": off_sc,
                "repair_coin_mult": float(srow.get("repair_coin_mult", 1.0)),
            }
            self._tick_captain_shared(cap, was_at_sea, docked_for_repair)
            ag["money"] = clampi(int(cap.get("money", 0)), 0, _MAX_PURSE_COINS_PY)
            ag["ship_condition"] = clampi(
                int(cap.get("ship_condition", _SHIP_CONDITION_MAX)),
                _SHIP_CONDITION_MIN,
                _SHIP_CONDITION_MAX,
            )
            ag["ship_wine_counter"] = clampi(int(cap.get("ship_wine_counter", 0)), 0, 9999)
            ag["fleet_ships"] = clampi(int(cap.get("fleet_ships", ships)), 1, _FLEET_MAX_SHIPS)

    def _npc_cargo_total_units(self, ag: dict) -> int:
        c = ag.get("cargo")
        if not isinstance(c, dict):
            return 0
        return sum(max(0, int(v)) for v in c.values())

    def _npc_mark_port_for_cargo_mark(self, ag: dict) -> str:
        """Port used to mark cargo: docked → that harbour; at sea → voyage destination if known, else home."""
        dp = str(ag.get("docked_port", "")).strip()
        if dp and dp in self.port_names:
            return dp
        vd = str(ag.get("voyage_dest_id", "")).strip()
        if vd and vd in self.port_names:
            return vd
        hp = str(ag.get("home_port", "")).strip()
        if hp and hp in self.port_names:
            return hp
        return str(self.port_order[0]) if self.port_order else ""

    def _npc_fleet_book_value_coins(self, ag: dict) -> int:
        """Book value of hulls at nominal new-hull reference (`_FLEET_SHIP_NOMINAL_COINS` per ship)."""
        self._ensure_npc_ship_fields(ag)
        ships = clampi(int(ag.get("fleet_ships", 1)), 1, _FLEET_MAX_SHIPS)
        return ships * _FLEET_SHIP_NOMINAL_COINS

    def _npc_cargo_estimated_coin_value(self, ag: dict) -> int:
        """Coins if the whole hold were wholesaled at `_npc_mark_port_for_cargo_mark` (NPC effective sell unit × qty)."""
        cargo = ag.get("cargo")
        if not isinstance(cargo, dict) or not cargo:
            return 0
        pid = self._npc_mark_port_for_cargo_mark(ag)
        if not pid or pid not in self.port_names:
            return 0
        total = 0
        for gk, qv in cargo.items():
            gid = str(gk)
            qty = max(0, int(qv))
            if qty <= 0 or gid not in self.goods:
                continue
            unit = self._npc_effective_sell_unit(ag, pid, gid)
            if unit <= 0 or unit >= 999000:
                continue
            total += qty * int(unit)
        return min(99_999_999, total)

    def _npc_merchant_balance_sheet_coins(self, ag: dict) -> int:
        self._ensure_npc_money_field(ag)
        purse = clampi(int(ag.get("money", 0)), 0, _MAX_PURSE_COINS_PY)
        return purse + self._npc_fleet_book_value_coins(ag) + self._npc_cargo_estimated_coin_value(ag)

    def _npc_merchant_seasoned_mastery_tick(self) -> None:
        for ag in self.npc_agents:
            if not isinstance(ag, dict):
                continue
            if str(ag.get("voyage_role", _VOYAGE_ROLE_MERCHANT)) != _VOYAGE_ROLE_MERCHANT:
                continue
            self._ensure_npc_ship_fields(ag)
            purse = clampi(int(ag.get("money", 0)), 0, _MAX_PURSE_COINS_PY)
            cargo_u = self._npc_cargo_total_units(ag)
            ships = clampi(int(ag.get("fleet_ships", 1)), 1, _FLEET_MAX_SHIPS)
            sea = int(ag.get("voyage_days_remaining", 0))
            viable = purse > 0 or cargo_u > 0 or ships > 1 or sea > 0
            if not viable:
                ag["merchant_season_ticks"] = 0
                continue
            st = clampi(int(ag.get("merchant_season_ticks", 0)), 0, 999) + 1
            ag["merchant_season_ticks"] = st
            if st < _NPC_SEASON_MASTERY_DAYS:
                continue
            ag["merchant_season_ticks"] = 0
            bm = clampf(float(ag.get("buy_mastery", 1.0)), _NPC_MASTER_MIN, _NPC_MASTER_MAX)
            sm = clampf(float(ag.get("sell_mastery", 1.0)), _NPC_MASTER_MIN, _NPC_MASTER_MAX)
            if bm >= _NPC_MASTER_MAX - 0.001 and sm >= _NPC_MASTER_MAX - 0.001:
                continue
            if bm <= sm:
                ag["buy_mastery"] = clampf(bm + _NPC_SEASON_MASTERY_BUMP, _NPC_MASTER_MIN, _NPC_MASTER_MAX)
            else:
                ag["sell_mastery"] = clampf(sm + _NPC_SEASON_MASTERY_BUMP, _NPC_MASTER_MIN, _NPC_MASTER_MAX)

    def _npc_cull_bankrupts(self) -> None:
        i = 0
        while i < len(self.npc_agents):
            ag = self.npc_agents[i]
            if not isinstance(ag, dict):
                del self.npc_agents[i]
                continue
            purse = clampi(int(ag.get("money", 0)), 0, _MAX_PURSE_COINS_PY)
            if purse > 0:
                ag["purse_bust_streak"] = 0
                i += 1
                continue
            if self._npc_cargo_total_units(ag) > 0:
                ag["purse_bust_streak"] = 0
                i += 1
                continue
            streak = clampi(int(ag.get("purse_bust_streak", 0)), 0, 999) + 1
            ag["purse_bust_streak"] = streak
            if streak < _NPC_BUST_EMPTY_STREAK_DAYS:
                i += 1
                continue
            self.bankruptcy_events += 1
            old_id = int(ag.get("id", 0))
            self._npc_convoy_fixup_removed_agent_id(old_id)
            home = str(ag.get("home_port", ""))
            if home not in self.port_names:
                if not self.port_order:
                    del self.npc_agents[i]
                    continue
                home = self.port_order[0]
            inherit = {
                "buy": clampf(float(ag.get("buy_mastery", 1.0)), _NPC_MASTER_MIN, _NPC_MASTER_MAX),
                "sell": clampf(float(ag.get("sell_mastery", 1.0)), _NPC_MASTER_MIN, _NPC_MASTER_MAX),
            }
            if not self._home_port_deserves_bankruptcy_replacement(home):
                del self.npc_agents[i]
                continue
            self.npc_agents[i] = self._new_npc_agent(home, True, inherit)
            i += 1

    def advance_day(self) -> None:
        self.current_day += 1
        was_at_sea = self.player_voyage_days_remaining > 0
        if was_at_sea:
            self._tick_player_storm_if_at_sea()
            if str(self.player_voyage_role) == _VOYAGE_ROLE_MERCHANT:
                self._tick_player_pirate_encounter_if_at_sea()
        escorting = str(self.player_voyage_role) == _VOYAGE_ROLE_ESCORT and int(self.player_voyage_days_remaining) > 0
        if int(self.player_voyage_days_remaining) > 0 and not escorting:
            self.player_voyage_days_remaining = int(self.player_voyage_days_remaining) - 1
            if int(self.player_voyage_days_remaining) == 0:
                dest_ar = str(self.player_voyage_dest_id or "")
                if dest_ar in self.port_names:
                    self.player_port_id = dest_ar
                self.player_voyage_dest_id = ""
                self.player_voyage_booked_days = 0
                self.player_voyage_open_sea_01 = 0.0
                self._apply_player_escort_contract_on_voyage_arrival_py()
        self._tick_player_ship_and_crew(was_at_sea)
        self._run_daily_population_and_npcs()
        if escorting:
            self._sync_player_escort_with_employer_after_npc_advance_py()
        if not self.is_player_at_sea():
            pid_hd = str(self.player_port_id)
            traffic_hd = 1
            for agx in self.npc_agents:
                if not isinstance(agx, dict):
                    continue
                if int(agx.get("voyage_days_remaining", 0)) != 0:
                    continue
                if str(agx.get("docked_port", "")) == pid_hd:
                    traffic_hd += 1
            take_hd = _take_harbour_due_from_purse(
                int(self.player_money), clampi(int(self.player_fleet_ships), 1, _FLEET_MAX_SHIPS)
            )
            if take_hd > 0:
                self.player_money = clampi(int(self.player_money) - take_hd, 0, _MAX_PURSE_COINS_PY)
                self._harbour_due_port_wealth_bump(pid_hd, take_hd, traffic_hd)
            rowp = self._player_ship_row()
            oph_p = max(1, int(rowp.get("officer_pay_per_hull", 1)))
            cap = {
                "money": int(self.player_money),
                "cargo": self.player_cargo,
                "ship_condition": int(self.player_ship_condition),
                "ship_wine_counter": int(self.player_ship_wine_counter),
                "fleet_ships": clampi(int(self.player_fleet_ships), 1, _FLEET_MAX_SHIPS),
                "officer_pay_scale": float(oph_p) * self._player_cultural_ops_scale(),
            }
            self._tick_captain_officer_pay(cap)
            self.player_money = clampi(int(cap.get("money", 0)), 0, _MAX_PURSE_COINS_PY)
            self.player_ship_condition = clampi(
                int(cap.get("ship_condition", _SHIP_CONDITION_MAX)),
                _SHIP_CONDITION_MIN,
                _SHIP_CONDITION_MAX,
            )
        self.player_ship_age_days = min(_MAX_DAY_COUNTER_PY, int(self.player_ship_age_days) + 1)

    def merchant_skill_money_rows(
        self,
    ) -> list[tuple[int, float, float, int, float, int, int, int, int]]:
        """id, buy_m, sell_m, purse, skill_avg, fleet_ships, cargo_est_coins, fleet_book_coins, investment_wealth_coins.

        `investment_wealth_coins` = fleet_book + cargo_est (ships at purchase price + hold marked to wholesale sell).
        Balance-sheet total for a merchant = purse + investment_wealth_coins.
        """
        rows: list[tuple[int, float, float, int, float, int, int, int, int]] = []
        for ag in self.npc_agents:
            if not isinstance(ag, dict):
                continue
            self._ensure_npc_ship_fields(ag)
            bid = int(ag.get("id", -1))
            bm = clampf(float(ag.get("buy_mastery", 1.0)), _NPC_MASTER_MIN, _NPC_MASTER_MAX)
            sm = clampf(float(ag.get("sell_mastery", 1.0)), _NPC_MASTER_MIN, _NPC_MASTER_MAX)
            purse = clampi(int(ag.get("money", 0)), 0, _MAX_PURSE_COINS_PY)
            avg = 0.5 * (bm + sm)
            ships = clampi(int(ag.get("fleet_ships", 1)), 1, _FLEET_MAX_SHIPS)
            cargo_est = self._npc_cargo_estimated_coin_value(ag)
            fleet_book = self._npc_fleet_book_value_coins(ag)
            invest = fleet_book + cargo_est
            rows.append((bid, bm, sm, purse, avg, ships, cargo_est, fleet_book, invest))
        rows.sort(key=lambda r: r[3] + r[8], reverse=True)
        return rows

    def timeseries_snapshot(self) -> dict:
        """One row per port for plotting: wealth, attractor, stocks, prices, industrial sinks (Phase 1)."""
        ports: dict[str, dict] = {}
        good_ids = sorted(self.goods.keys())
        for pid in self.port_order:
            ps = str(pid)
            row: dict = {
                "wealth": int(self.port_wealth.get(ps, 0)),
                "attractor": int(self._wealth_stock_target_for_port(ps)),
                "at_war": 1 if self.is_port_at_war(ps) else 0,
                "war_days_left": int(self.get_port_war_days_remaining(ps)),
                "food_riot": int(self.last_food_riot_by_port.get(ps, 0)),
                "population_grain": int(self.port_population_grain.get(ps, 0)),
                "population_grain_cap": int(self.port_population_grain_cap.get(ps, 0)),
                "population_fish_per_day": int(self.port_population_fish_per_day.get(ps, 0)),
            }
            idig = self.last_industrial_sink_digest.get(ps)
            row["industrial_metal_sink"] = int(idig.get("metal", 0)) if isinstance(idig, dict) else 0
            row["industrial_wire_sink"] = int(idig.get("wire", 0)) if isinstance(idig, dict) else 0
            row["industrial_timber_sink"] = int(idig.get("timber", 0)) if isinstance(idig, dict) else 0
            row["industrial_textiles_sink"] = int(idig.get("textiles", 0)) if isinstance(idig, dict) else 0
            for gid in good_ids:
                row[f"stock_{gid}"] = int(self._port_stock_qty(ps, gid))
                row[f"buy_{gid}"] = int(self._compute_player_buy_unit(ps, gid))
                row[f"sell_{gid}"] = int(self._compute_player_sell_unit(ps, gid))
            if "fish" in self.goods:
                ration = max(0, int(self.port_population_fish_per_day.get(ps, 0)))
                fs = int(self._port_stock_qty(ps, "fish"))
                row["fish_runway_days"] = float(fs) / float(ration) if ration > 0 else 9999.0
            cm = self._port_commerce_tick.get(ps, {})
            row["commerce_npc_buy_units"] = int(cm.get("npc_buy_units", 0))
            row["commerce_npc_sell_units"] = int(cm.get("npc_sell_units", 0))
            row["commerce_npc_buy_coins"] = int(cm.get("npc_buy_coins", 0))
            row["commerce_npc_sell_coins"] = int(cm.get("npc_sell_coins", 0))
            row["crop_moisture_01"] = clampf(float(self.port_crop_moisture_01.get(ps, 0.5)), 0.0, 1.0)
            row["crop_growth_01"] = clampf(float(self.port_crop_growth_01.get(ps, 0.5)), 0.0, 1.0)
            row["crop_stress_01"] = self._crop_grain_stress_01_for_port(ps)
            row["crop_stress_market_01"] = self._crop_grain_stress_01_market_for_port(ps)
            row["crop_belief_local_01"] = clampf(
                float(self.port_local_crop_belief_01.get(ps, self._crop_grain_stress_gt_01_for_port(ps))), 0.0, 1.0
            )
            row["crop_inbound_reports_n"] = self._port_crop_inbound_report_count(ps)
            row["crop_rumor_delta_01"] = clampf(
                float(self.port_crop_rumor_public_delta.get(ps, 0.0)),
                -_CROP_RUMOR_DELTA_ABS_MAX,
                _CROP_RUMOR_DELTA_ABS_MAX,
            )
            row["crop_grain_yield_mult"] = self._crop_grain_yield_mult_for_port(ps)
            row["crop_phase2_major"] = 1 if self._crop_phase2_stress_major_gate(ps) else 0
            row["crop_phase2_bias_add"] = self._crop_phase2_grain_trade_bias_add(ps)
            row["crop_phase2_hoard_01"] = self._crop_phase2_npc_hoard_weight_01(ps)
            ports[ps] = row
        return {"day": int(self.current_day), "ports": ports}

    def metrics(self) -> dict:
        npc_money = 0
        npc_at_sea = 0
        npc_fleet_ships_total = 0
        npc_fleet_book_total = 0
        npc_cargo_est_total = 0
        for ag in self.npc_agents:
            npc_money += clampi(int(ag.get("money", 0)), 0, _MAX_PURSE_COINS_PY)
            if int(ag.get("voyage_days_remaining", 0)) > 0:
                npc_at_sea += 1
            if isinstance(ag, dict):
                self._ensure_npc_ship_fields(ag)
                npc_fleet_ships_total += clampi(int(ag.get("fleet_ships", 1)), 1, _FLEET_MAX_SHIPS)
                npc_fleet_book_total += self._npc_fleet_book_value_coins(ag)
                npc_cargo_est_total += self._npc_cargo_estimated_coin_value(ag)
        ports = {}
        for pid in self.port_order:
            gdays = 9999.0
            if "grain" in self.goods:
                eatm = self.get_population_grain_eat_effective(pid)
                if eatm > 0:
                    gdays = float(self._port_stock_qty(pid, "grain")) / float(eatm)
            sm = self._port_stock_qty(pid, "metal") if "metal" in self.goods else 0
            swr = self._port_stock_qty(pid, "wire") if "wire" in self.goods else 0
            sau = self._port_stock_qty(pid, "gold") if "gold" in self.goods else 0
            sag = self._port_stock_qty(pid, "silver") if "silver" in self.goods else 0
            idig = self.last_industrial_sink_digest.get(pid)
            isink_m = int(idig.get("metal", 0)) if isinstance(idig, dict) else 0
            isink_w = int(idig.get("wire", 0)) if isinstance(idig, dict) else 0
            isink_tb = int(idig.get("timber", 0)) if isinstance(idig, dict) else 0
            isink_tx = int(idig.get("textiles", 0)) if isinstance(idig, dict) else 0
            ports[pid] = {
                "wealth": int(self.port_wealth.get(pid, 0)),
                "stock_grain": self._port_stock_qty(pid, "grain"),
                "stock_wine": self._port_stock_qty(pid, "wine"),
                "stock_metal": sm,
                "stock_wire": swr,
                "stock_gold": sau,
                "stock_silver": sag,
                "attractor": self._wealth_stock_target_for_port(pid),
                "grain_spoiled": int(self._last_grain_spoilage.get(pid, 0)),
                "grain_food_days": gdays,
                "food_unrest": clampi(int(self.port_food_unrest.get(pid, 0)), 0, 200),
                "food_unrest_mood": self._food_unrest_tier_label(
                    clampi(int(self.port_food_unrest.get(pid, 0)), 0, 200)
                ),
                "population_grain": int(self.port_population_grain.get(pid, 0)),
                "population_grain_cap": int(self.port_population_grain_cap.get(pid, 0)),
                "famine_streak_days": int(self.port_famine_streak_days.get(pid, 0)),
                "prosperity_streak_days": int(self.port_prosperity_streak_days.get(pid, 0)),
                "population_output_scale": self._population_output_scale_for_port(pid),
                "at_war": self.is_port_at_war(pid),
                "war_days_left": self.get_port_war_days_remaining(pid),
                "war_recurring": bool(self.port_war_recurring.get(pid, False)),
                "war_peace_days": int(self.port_war_peace_remaining.get(pid, 0)),
                "industrial_metal_sink": isink_m,
                "industrial_wire_sink": isink_w,
                "industrial_timber_sink": isink_tb,
                "industrial_textiles_sink": isink_tx,
                "slave_labor_demand": self._port_slave_labor_demand(pid) if "slaves" in self.goods else 0,
                "stock_slaves": self._port_stock_qty(pid, "slaves") if "slaves" in self.goods else 0,
                "slave_output_mult": self._last_slave_output_mult_for_port(pid) if "slaves" in self.goods else 1.0,
                "slaves_lost_last_tick": self._last_slave_lost_for_port(pid) if "slaves" in self.goods else 0,
                "slave_war_captives_last_tick": int(
                    (self.last_slave_digest.get(pid) or {}).get("captives", 0)
                )
                if "slaves" in self.goods
                else 0,
            }
            cm = self._port_commerce_tick.get(str(pid), {})
            ports[pid]["commerce_npc_buy_units"] = int(cm.get("npc_buy_units", 0))
            ports[pid]["commerce_npc_sell_units"] = int(cm.get("npc_sell_units", 0))
            ports[pid]["commerce_npc_buy_coins"] = int(cm.get("npc_buy_coins", 0))
            ports[pid]["commerce_npc_sell_coins"] = int(cm.get("npc_sell_coins", 0))
            ports[pid]["commerce_pulse"] = float(self.port_commerce_pulse.get(str(pid), 0.0))
            ports[pid]["cartel_strength"] = float(self.port_cartel_strength.get(str(pid), 0.0))
            ports[pid]["war_rumor"] = float(self.port_war_rumor.get(str(pid), 0.0))
            ports[pid]["plague_days"] = int(self.port_plague_days.get(str(pid), 0))
            ports[pid]["npc_docked"] = self._count_npc_docked_at(pid)
            ports[pid]["crop_moisture_01"] = clampf(float(self.port_crop_moisture_01.get(str(pid), 0.5)), 0.0, 1.0)
            ports[pid]["crop_growth_01"] = clampf(float(self.port_crop_growth_01.get(str(pid), 0.5)), 0.0, 1.0)
            ports[pid]["crop_stress_01"] = self._crop_grain_stress_01_for_port(pid)
            ports[pid]["crop_stress_market_01"] = self._crop_grain_stress_01_market_for_port(pid)
            ports[pid]["crop_belief_local_01"] = clampf(
                float(self.port_local_crop_belief_01.get(str(pid), self._crop_grain_stress_gt_01_for_port(pid))),
                0.0,
                1.0,
            )
            ports[pid]["crop_inbound_reports_n"] = self._port_crop_inbound_report_count(pid)
            ports[pid]["crop_rumor_delta_01"] = clampf(
                float(self.port_crop_rumor_public_delta.get(str(pid), 0.0)),
                -_CROP_RUMOR_DELTA_ABS_MAX,
                _CROP_RUMOR_DELTA_ABS_MAX,
            )
            ports[pid]["crop_grain_yield_mult"] = self._crop_grain_yield_mult_for_port(pid)
            ports[pid]["crop_phase2_major"] = 1 if self._crop_phase2_stress_major_gate(pid) else 0
            ports[pid]["crop_phase2_bias_add"] = self._crop_phase2_grain_trade_bias_add(pid)
            ports[pid]["crop_phase2_hoard_01"] = self._crop_phase2_npc_hoard_weight_01(pid)
        n_ag = len(self.npc_agents)
        npc_fleet_mean = float(npc_fleet_ships_total) / float(n_ag) if n_ag > 0 else 0.0
        npc_investment_wealth_total = npc_fleet_book_total + npc_cargo_est_total
        npc_balance_sheet_total = npc_money + npc_investment_wealth_total
        return {
            "day": self.current_day,
            "player_money": int(self.player_money),
            "world_treasury_coins": clampi(int(self.world_treasury_coins), 0, _WORLD_TREASURY_MAX),
            "player_port": str(self.player_port_id),
            "player_fleet_ships": clampi(int(self.player_fleet_ships), 1, _FLEET_MAX_SHIPS),
            "player_cargo_capacity": self._player_cargo_capacity_units(),
            "player_ship_condition": clampi(
                int(self.player_ship_condition), _SHIP_CONDITION_MIN, _SHIP_CONDITION_MAX
            ),
            "player_at_sea": self.is_player_at_sea(),
            "ports": ports,
            "npc_agent_count": n_ag,
            "npc_at_sea": npc_at_sea,
            "npc_total_money": npc_money,
            "npc_fleet_ships_total": int(npc_fleet_ships_total),
            "npc_fleet_ships_mean": npc_fleet_mean,
            "npc_total_fleet_book_coins": int(npc_fleet_book_total),
            "npc_total_cargo_est_coins": int(npc_cargo_est_total),
            "npc_total_investment_wealth_coins": int(npc_investment_wealth_total),
            "npc_total_balance_sheet_coins": int(npc_balance_sheet_total),
            "pirate_encounter_attempts": int(self.pirate_encounter_attempts),
            "pirate_raids_success": int(self.pirate_raids_success),
            "pirate_escort_flees": int(self.pirate_escort_flees),
            "pirate_marines_lost": int(self.pirate_marines_lost),
            "pirate_loot_coins": int(self.pirate_loot_coins),
            "player_pirate_encounter_rolls": int(self.player_pirate_encounter_rolls),
            "player_pirate_repelled": int(self.player_pirate_repelled),
            "player_pirate_hits": int(self.player_pirate_hits),
            "npc_city_grain_contracts_enabled": bool(self._world_npc_city_grain_contracts_enabled),
            "npc_city_grain_contracts_signed": int(self.npc_city_grain_contracts_signed),
            "npc_city_grain_contracts_fulfilled": int(self.npc_city_grain_contracts_fulfilled),
            "npc_city_grain_contracts_breached": int(self.npc_city_grain_contracts_breached),
        }


def _default_npc_money_from_seed(seed: int) -> int:
    mn = _NPC_START_MONEY_MIN
    mx = _NPC_START_MONEY_MAX
    if mx < mn:
        mx = mn
    span = mx - mn + 1
    s = ((seed * 31 + 17) % span + span) % span
    return mn + s


def _print_block(title: str, m: dict) -> None:
    print()
    print(f"-- {title} --")
    print(
        f"  player: money={m.get('player_money', 0)}  fleet={m.get('player_fleet_ships', 1)}  "
        f"cargo_cap={m.get('player_cargo_capacity', _FLEET_CARGO_PER_SHIP)}  "
        f"ship={m.get('player_ship_condition', 100)}/{_SHIP_CONDITION_MAX}  "
        f"port={m.get('player_port', '')}  at_sea={m.get('player_at_sea', False)}  |  "
        f"world_treasury={int(m.get('world_treasury_coins', 0))}c  |  "
        f"npc: agents={m['npc_agent_count']}  ships={m.get('npc_fleet_ships_total', 0)}  "
        f"at_sea={m['npc_at_sea']}  total_purse={m['npc_total_money']}"
    )
    bs = m.get("npc_total_balance_sheet_coins")
    if bs is not None:
        print(
            f"  npc merchant balance_sheet(all)={int(bs)}c  "
            f"investments={int(m.get('npc_total_investment_wealth_coins', 0))}c  "
            f"(fleet_book={int(m.get('npc_total_fleet_book_coins', 0))}c + "
            f"cargo_mark={int(m.get('npc_total_cargo_est_coins', 0))}c)"
        )
    for pid in sorted(m["ports"].keys()):
        p = m["ports"][pid]
        gfd = float(p.get("grain_food_days", 9999.0))
        fur = int(p.get("food_unrest", 0))
        mood = str(p.get("food_unrest_mood", ""))
        pop_m = int(p.get("population_grain", 0))
        pop_sc = float(p.get("population_output_scale", 1.0))
        fam = int(p.get("famine_streak_days", 0))
        prs = int(p.get("prosperity_streak_days", 0))
        sm = int(p.get("stock_metal", 0))
        swr = int(p.get("stock_wire", 0))
        wl = int(p.get("war_days_left", 0))
        war = f"W{wl}" if p.get("at_war") else "  "
        imo = int(p.get("industrial_metal_sink", 0))
        iwo = int(p.get("industrial_wire_sink", 0))
        itb = int(p.get("industrial_timber_sink", 0))
        itx = int(p.get("industrial_textiles_sink", 0))
        cbu = int(p.get("commerce_npc_buy_units", 0))
        csu = int(p.get("commerce_npc_sell_units", 0))
        cbc = int(p.get("commerce_npc_buy_coins", 0))
        csc = int(p.get("commerce_npc_sell_coins", 0))
        print(
            f"  port {pid:10}  wealth={p['wealth']:4} (attract={p['attractor']:4})  "
            f"grain={p['stock_grain']:4}  wine={p['stock_wine']:4}  m={sm:3} w={swr:3}  spoil={p.get('grain_spoiled', 0):2}  "
            f"food_days={gfd:5.1f}  unrest={fur:3} ({mood})  pop={pop_m} out×{pop_sc:.2f} fam={fam} pro={prs}  "
            f"ind_mwtx={imo:2}/{iwo:2}/{itb:2}/{itx:2}  {war}  "
            f"npc_wholesale buy={cbu}u/{cbc}c sell={csu}u/{csc}c"
        )


def _progress_log_step(total_days: int) -> int:
    """How often to print a full metrics block (avoid huge logs on long runs)."""
    if total_days <= 200:
        return 10
    if total_days <= 2000:
        return 100
    return 1000


def _should_log_progress(tick_index: int, total_days: int) -> bool:
    """tick_index is 1-based day count after an advance_day."""
    if tick_index == total_days:
        return True
    step = _progress_log_step(total_days)
    return tick_index % step == 0


def _timeseries_sample_step(total_days: int) -> int:
    """At most ~20k snapshots so long runs stay bounded in memory."""
    cap = 20000
    if total_days <= cap:
        return 1
    return (total_days + cap - 1) // cap


def _plot_war_shading(ax, days: list, war_flags: list) -> None:
    """Light horizontal bands while `at_war` is true (from snapshots)."""
    n = len(days)
    if n == 0:
        return
    i = 0
    while i < n:
        if not war_flags[i]:
            i += 1
            continue
        j = i + 1
        while j < n and war_flags[j]:
            j += 1
        x0 = float(days[i])
        x1 = float(days[j - 1])
        if x1 <= x0:
            x1 = x0 + 1.0
        ax.axvspan(x0, x1, facecolor="#e6d595", alpha=0.38, linewidth=0, zorder=0)
        i = j


def _plot_riot_markers(
    ax, days: list, riot_flags: list, y_frac: float = 0.94, *, legend_label: bool = True
) -> int:
    """Down-triangles at food-riot days; uses current y-limits. Call after main series."""
    xs = [d for d, r in zip(days, riot_flags) if r]
    if not xs:
        return 0
    lo, hi = ax.get_ylim()
    if hi <= lo:
        return 0
    y = lo + (hi - lo) * y_frac
    lab = "food riot" if legend_label else "_nolegend_"
    ax.scatter(xs, [y] * len(xs), marker="v", c="crimson", s=55, zorder=6, clip_on=False, label=lab)
    return len(xs)


def _write_sim_timeseries_graphs(sim: Sim, history: list[dict], out_dir: Path) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.patches import Patch
    except ImportError:
        print("  (matplotlib not installed; skipped graphs. pip install matplotlib)")
        return
    if not history:
        return
    out_dir.mkdir(parents=True, exist_ok=True)
    days = [int(h["day"]) for h in history]
    max_pts = 8000
    if len(days) > max_pts:
        step_i = max(1, len(days) // max_pts)
        idx = list(range(0, len(days), step_i))
        if idx[-1] != len(days) - 1:
            idx.append(len(days) - 1)
    else:
        idx = list(range(len(days)))
    days_plt = [days[i] for i in idx]
    war_legend = Patch(facecolor="#e6d595", alpha=0.45, edgecolor="none", label="war (shaded)")

    for pid in sim.port_order:
        safe = pid.replace("/", "_").replace(" ", "_")
        war_f = [bool(history[i]["ports"][pid].get("at_war", 0)) for i in idx]
        riot_f = [bool(history[i]["ports"][pid].get("food_riot", 0)) for i in idx]

        wealth = [history[i]["ports"][pid]["wealth"] for i in idx]
        attract = [int(history[i]["ports"][pid].get("attractor", 0)) for i in idx]
        pop_eat = [int(history[i]["ports"][pid].get("population_grain", 0)) for i in idx]
        pop_cap = [int(history[i]["ports"][pid].get("population_grain_cap", 0)) for i in idx]
        fish_stock = [int(history[i]["ports"][pid].get("stock_fish", 0)) for i in idx] if "fish" in sim.goods else []
        tb_stock = [int(history[i]["ports"][pid].get("stock_timber", 0)) for i in idx] if "timber" in sim.goods else []
        tx_stock = [int(history[i]["ports"][pid].get("stock_textiles", 0)) for i in idx] if "textiles" in sim.goods else []
        is_m = [int(history[i]["ports"][pid].get("industrial_metal_sink", 0)) for i in idx]
        is_w = [int(history[i]["ports"][pid].get("industrial_wire_sink", 0)) for i in idx]
        is_tb = [int(history[i]["ports"][pid].get("industrial_timber_sink", 0)) for i in idx]
        is_tx = [int(history[i]["ports"][pid].get("industrial_textiles_sink", 0)) for i in idx]

        fig, (ax_w, ax_p, ax_tb, ax_ind) = plt.subplots(4, 1, figsize=(11, 11.2), sharex=True)
        pname = str(sim.port_names.get(pid, pid))

        _plot_war_shading(ax_w, days_plt, war_f)
        ax_w.plot(days_plt, wealth, color="tab:blue", linewidth=1.15, zorder=2, label="wealth")
        ax_w.plot(
            days_plt,
            attract,
            color="tab:orange",
            linestyle="--",
            linewidth=1.05,
            alpha=0.85,
            zorder=2,
            label="attractor (stock-implied)",
        )
        ax_w.set_ylabel("coins")
        ax_w.set_title(f"{pname} ({pid}) — prosperity vs target (tan = war; red ▼ = food riot)")
        ax_w.grid(True, alpha=0.3)
        _plot_riot_markers(ax_w, days_plt, riot_f, legend_label=True)
        h0, _lw0 = ax_w.get_legend_handles_labels()
        ax_w.legend(handles=[*h0, war_legend], loc="upper right", fontsize=8)

        _plot_war_shading(ax_p, days_plt, war_f)
        ax_p.plot(
            days_plt,
            pop_eat,
            color="tab:green",
            linewidth=1.15,
            zorder=2,
            label="population (grain mouths / day)",
        )
        if any(pop_cap):
            ax_p.plot(
                days_plt,
                pop_cap,
                color="gray",
                linestyle="--",
                linewidth=1.0,
                alpha=0.75,
                zorder=2,
                label="population cap",
            )
        ax_p.set_ylabel("grain mouths / day")
        ax_p.set_title("Population (grain) + fish (Phase 1)")
        ax_p.grid(True, alpha=0.3)
        _plot_riot_markers(ax_p, days_plt, riot_f, legend_label=False)
        h_p, l_p = ax_p.get_legend_handles_labels()
        if "fish" in sim.goods and fish_stock:
            ax_pf = ax_p.twinx()
            ax_pf.plot(
                days_plt,
                fish_stock,
                color="tab:cyan",
                linewidth=1.05,
                alpha=0.9,
                zorder=3,
                label="fish stock",
            )
            ax_pf.set_ylabel("fish (port stock)", color="tab:cyan")
            ax_pf.tick_params(axis="y", labelcolor="tab:cyan")
            h_pf, l_pf = ax_pf.get_legend_handles_labels()
            ax_p.legend(
                handles=h_p + h_pf + [war_legend],
                labels=l_p + l_pf + [war_legend.get_label()],
                loc="upper right",
                fontsize=7,
            )
        else:
            ax_p.legend(
                handles=h_p + [war_legend],
                labels=l_p + [war_legend.get_label()],
                loc="upper right",
                fontsize=8,
            )

        _plot_war_shading(ax_tb, days_plt, war_f)
        if tb_stock and tx_stock:
            ax_tb.plot(days_plt, tb_stock, color="#8B4513", linewidth=1.1, label="timber stock", zorder=2)
            ax_tb.plot(days_plt, tx_stock, color="tab:purple", linewidth=1.1, label="textiles stock", zorder=2)
            ax_tb.set_ylabel("units")
            ax_tb.set_title("Workshop goods (port stock)")
        elif tb_stock:
            ax_tb.plot(days_plt, tb_stock, color="#8B4513", linewidth=1.1, label="timber stock", zorder=2)
            ax_tb.set_ylabel("timber")
            ax_tb.set_title("Timber (port stock)")
        elif tx_stock:
            ax_tb.plot(days_plt, tx_stock, color="tab:purple", linewidth=1.1, label="textiles stock", zorder=2)
            ax_tb.set_ylabel("textiles")
            ax_tb.set_title("Textiles (port stock)")
        else:
            ax_tb.text(0.5, 0.5, "(no timber/textiles in goods.json)", ha="center", va="center", transform=ax_tb.transAxes)
            ax_tb.set_title("Workshop goods")
        ax_tb.grid(True, alpha=0.3)
        _plot_riot_markers(ax_tb, days_plt, riot_f, legend_label=False)
        if tb_stock or tx_stock:
            ax_tb.legend(loc="upper right", fontsize=8)

        _plot_war_shading(ax_ind, days_plt, war_f)
        ax_ind.plot(days_plt, is_m, color="tab:gray", linewidth=1.0, label="metal sink", zorder=2)
        ax_ind.plot(days_plt, is_w, color="goldenrod", linewidth=1.0, label="wire sink", zorder=2)
        ax_ind.plot(days_plt, is_tb, color="#8B4513", linewidth=1.0, label="timber sink", zorder=2)
        ax_ind.plot(days_plt, is_tx, color="tab:purple", linewidth=1.0, label="textiles sink", zorder=2)
        ax_ind.set_ylabel("units / day")
        ax_ind.set_xlabel("calendar day")
        ax_ind.set_title("Industrial draw (last tick; peace-time workshops)")
        ax_ind.grid(True, alpha=0.3)
        _plot_riot_markers(ax_ind, days_plt, riot_f, legend_label=False)
        ax_ind.legend(loc="upper right", fontsize=7, ncol=2)

        fig.tight_layout()
        fig.savefig(out_dir / f"{safe}_port.png", dpi=120)
        plt.close(fig)
    print(f"  Time-series graphs (4-panel per port: wealth/attractor, pop+fish, stocks, industrial): {out_dir.resolve()}/")


def _print_run_analysis(sim: Sim, m0: dict, m1: dict, max_unrest: dict[str, int], min_grain_days: dict[str, float]) -> None:
    print()
    print("— Run analysis (first snapshot → final) —")
    d0 = int(m0.get("day", 1))
    d1 = int(m1.get("day", d0))
    npc0 = int(m0.get("npc_total_money", 0))
    npc1 = int(m1.get("npc_total_money", 0))
    hull0 = int(m0.get("npc_fleet_ships_total", 0))
    hull1 = int(m1.get("npc_fleet_ships_total", 0))
    print(f"  Calendar: day {d0} → {d1}  ({d1 - d0} advances)")
    print(f"  NPC purse total: {npc0} → {npc1}  (Δ {npc1 - npc0:+d})")
    inv0 = int(m0.get("npc_total_investment_wealth_coins", 0))
    inv1 = int(m1.get("npc_total_investment_wealth_coins", 0))
    bs0 = int(m0.get("npc_total_balance_sheet_coins", npc0 + inv0))
    bs1 = int(m1.get("npc_total_balance_sheet_coins", npc1 + inv1))
    print(
        f"  NPC investments (fleet book {_FLEET_SHIP_NOMINAL_COINS}c/hull + cargo wholesale mark): "
        f"{inv0} → {inv1}  (Δ {inv1 - inv0:+d})"
    )
    print(f"  NPC balance sheet (purse + investments): {bs0} → {bs1}  (Δ {bs1 - bs0:+d})")
    print(f"  NPC merchant hulls (sum of fleet_ships): {hull0} → {hull1}  (Δ {hull1 - hull0:+d})")
    print(f"  Food riots: {sim.riot_events}  |  Merchant bankruptcies: {sim.bankruptcy_events}")
    print(
        f"  Phase 0 civic grain contracts (enabled={m1.get('npc_city_grain_contracts_enabled', True)}): "
        f"signed={int(m1.get('npc_city_grain_contracts_signed', 0))}, "
        f"fulfilled={int(m1.get('npc_city_grain_contracts_fulfilled', 0))}, "
        f"breached={int(m1.get('npc_city_grain_contracts_breached', 0))}"
    )
    print(f"  NPC merchant convoys formed (multi-ship departures): {sim.convoy_formations}")
    print(f"  Escort wages paid (convoy arrivals, coins): {sim.escort_coins_paid}")
    print(
        f"  Pirates: encounter rolls={sim.pirate_encounter_attempts}, successful raids={sim.pirate_raids_success}, "
        f"escort flees={sim.pirate_escort_flees}, marines lost (boarding)={sim.pirate_marines_lost}, loot coins={sim.pirate_loot_coins}"
    )
    print(
        f"  Player vs pirates (at-sea days only): rolls={sim.player_pirate_encounter_rolls}, "
        f"repelled={sim.player_pirate_repelled}, hits={sim.player_pirate_hits}"
    )
    ports0 = m0.get("ports") or {}
    ports1 = m1.get("ports") or {}
    print("  Per port (wealth Δ, grain Δ, final grain-days, final unrest, min grain-days seen, max unrest seen):")
    for pid in sorted(ports1.keys()):
        p0 = ports0.get(pid) or {}
        p1 = ports1[pid]
        w0, w1 = int(p0.get("wealth", 0)), int(p1.get("wealth", 0))
        g0, g1 = int(p0.get("stock_grain", 0)), int(p1.get("stock_grain", 0))
        fd1 = float(p1.get("grain_food_days", 9999.0))
        u1 = int(p1.get("food_unrest", 0))
        mind = float(min_grain_days.get(pid, 99999.0))
        maxu = int(max_unrest.get(pid, 0))
        mind_s = f"{mind:.2f}" if mind < 9000.0 else "—"
        print(
            f"    {pid:10}  wealth {w0:4}→{w1:4} (Δ{w1 - w0:+4})  grain {g0:4}→{g1:4} (Δ{g1 - g0:+4})  "
            f"end_days={fd1:5.1f}  end_unrest={u1:3}  min_days≈{mind_s:>6}  max_unrest={maxu:3}"
        )


def _print_commerce_run_summary(sim: Sim) -> None:
    log = sim.commerce_daily_log
    n = len(log)
    if n <= 0:
        return
    totals: dict[str, dict[str, int]] = {
        pid: {"bu": 0, "su": 0, "bc": 0, "sc": 0} for pid in sim.port_order
    }
    for entry in log:
        ports = entry.get("ports") or {}
        for pid in sim.port_order:
            r = ports.get(pid) or {}
            t = totals[pid]
            t["bu"] += int(r.get("npc_buy_units", 0))
            t["su"] += int(r.get("npc_sell_units", 0))
            t["bc"] += int(r.get("npc_buy_coins", 0))
            t["sc"] += int(r.get("npc_sell_coins", 0))
    denom = float(max(1, n))
    print()
    print("— NPC dock wholesale commerce (full run; buy = stock out of port, sell = stock into port) —")
    print(f"  Logged days: {n}  (see sim.commerce_daily_log for per-day rows)")
    for pid in sorted(sim.port_order):
        t = totals[pid]
        print(
            f"    {pid:10}  mean/day: buy {t['bu'] / denom:5.1f}u {t['bc'] / denom:7.0f}c  "
            f"sell {t['su'] / denom:5.1f}u {t['sc'] / denom:7.0f}c  |  "
            f"totals buy {t['bu']:7d}u {t['bc']:9d}c  sell {t['su']:7d}u {t['sc']:9d}c"
        )


def _print_merchant_outcomes(sim: Sim) -> None:
    print()
    print("— Merchant outcomes (this run) —")
    print(f"  Bankruptcies (liquidations / conditional rookies): {sim.bankruptcy_events}")
    print(
        f"  Rule: {_NPC_BUST_EMPTY_STREAK_DAYS} consecutive days with 0c and empty hold (no gold, no goods) → remove or rookie; "
        f"rookie only if home had dock wholesale this day, commerce pulse ≥{_NPC_BANKRUPTCY_REPLACE_MIN_PULSE:.2f}, "
        f"or ≥{_NPC_BANKRUPTCY_REPLACE_MIN_PORT_STOCK_UNITS} tradeable units in stock (excl. gold/silver). "
        f"dock: fire-sale to officer purse (ships×{_SHIP_OFFICER_PAY_DAILY}c) if short, then dust-sell up to {_NPC_DOCK_DUST_MAX_UNITS}u while purse below base "
        f"{_NPC_DOCK_DUST_PURSE}c + neuroticism bump. "
        f"Start {_NPC_START_MONEY_MIN}–{_NPC_START_MONEY_MAX}c. "
        f"Bankruptcy rookies: chance {_ROOKIE_BANKRUPTCY_USED_HULL_CHANCE:.2f} to charter cheapest slip hull at home (listing removed, condition from listing, port wealth −ask/{_ROOKIE_USED_HULL_CHARTER_WEALTH_DIV}). "
        f"NPC peer loans: docked merchants may borrow coin (max {_NPC_PEER_LOAN_MAX_DEBTS} debts); sell margin repays creditors; traits bias avoiding creditors' home ports and fleeing shared docks."
    )
    print(
        "  NPC captains use the same trireme rules as the player (_SHIP_*): crew wine from hold (no daily grain draw), "
        "wear at sea, dock repair before voyage advance; docked officer pay + marine wages after that day's port trade; "
        "bankruptcy check follows trades and pay."
    )
    rows = sim.merchant_skill_money_rows()
    if not rows:
        print("  (no NPC agents)")
        return
    purses = [r[3] for r in rows]
    avgs = [r[4] for r in rows]
    ship_counts = [r[5] for r in rows]
    cargo_ests = [r[6] for r in rows]
    fleet_books = [r[7] for r in rows]
    investments = [r[8] for r in rows]
    totals = [r[3] + r[8] for r in rows]
    med_skill = sorted(avgs)[len(avgs) // 2]
    hi = [r for r in rows if r[4] >= med_skill]
    lo = [r for r in rows if r[4] < med_skill]
    mean_hi = sum(r[3] for r in hi) / max(1, len(hi))
    mean_lo = sum(r[3] for r in lo) / max(1, len(lo))
    total_ships = sum(ship_counts)
    mean_ships = float(total_ships) / float(len(rows)) if rows else 0.0
    print(
        f"  Active merchants: {len(rows)}  |  total hulls: {total_ships}  (mean {mean_ships:.2f} ships/merchant)  "
        f"|  run peak: richest purse {getattr(sim, 'npc_purse_peak_run', 0)}c, hulls sum {getattr(sim, 'npc_fleet_hulls_peak_run', 0)}"
    )
    print(
        f"  Merchant wealth score (investments): fleet book {_FLEET_SHIP_NOMINAL_COINS}c × hulls + cargo wholesale mark; "
        f"balance sheet = purse + that score."
    )
    print(f"  Median (buy+sell)/2 skill ≈ {med_skill:.3f}")
    print(f"  Mean purse: skill ≥ median → {mean_hi:.1f} coins   skill < median → {mean_lo:.1f} coins")
    if investments:
        print(
            f"  Investment wealth (fleet book + cargo~): sum {sum(investments)}c  "
            f"mean {sum(investments) / len(investments):.1f}c  max {max(investments)}c"
        )
    if totals:
        print(
            f"  Balance sheet (purse + investments): sum {sum(totals)}c  "
            f"mean {sum(totals) / len(totals):.1f}c  max {max(totals)}c  min {min(totals)}c"
        )
        n_m = len(rows)
        k10 = max(1, int(math.ceil(0.10 * n_m)))
        top_rows = rows[:k10]
        top_totals = [r[3] + r[8] for r in top_rows]
        top_purses = [r[3] for r in top_rows]
        top_inv = [r[8] for r in top_rows]
        share = 100.0 * float(sum(top_totals)) / float(max(1, sum(totals)))
        print(
            f"  Wealthiest 10% ({k10} of {n_m} merchants, balance sheet desc): "
            f"sum {sum(top_totals)}c  mean {sum(top_totals) / k10:.1f}c  "
            f"range {min(top_totals)}–{max(top_totals)}c  |  purse mean {sum(top_purses) / k10:.1f}c  "
            f"inv mean {sum(top_inv) / k10:.1f}c  |  hold {share:.1f}% of all merchant balance-sheet coin"
        )
    if cargo_ests:
        print(
            f"  Cargo mark only (wholesale @ dock or voyage dest): "
            f"sum {sum(cargo_ests)}c  mean {sum(cargo_ests) / len(cargo_ests):.1f}c  max {max(cargo_ests)}c"
        )
    if fleet_books:
        print(
            f"  Fleet book only ({_FLEET_SHIP_NOMINAL_COINS}c/hull): sum {sum(fleet_books)}c  "
            f"mean {sum(fleet_books) / len(fleet_books):.1f}c  max {max(fleet_books)}c"
        )
    print("  Wealthiest 5 by balance sheet (purse + fleet book + cargo~; id / total / purse / inv / ships / buy / sell):")
    for r in rows[:5]:
        tot = r[3] + r[8]
        print(
            f"    id {r[0]:3}  total {tot:6}  purse {r[3]:4}  inv {r[8]:5}  "
            f"(fleet {r[7]:4} + cargo {r[6]:4})  ships {r[5]:2}  buy {r[1]:.2f}  sell {r[2]:.2f}"
        )
    print("  Thinnest 5 balance sheets (same columns):")
    for r in rows[-5:]:
        tot = r[3] + r[8]
        print(
            f"    id {r[0]:3}  total {tot:6}  purse {r[3]:4}  inv {r[8]:5}  "
            f"(fleet {r[7]:4} + cargo {r[6]:4})  ships {r[5]:2}  buy {r[1]:.2f}  sell {r[2]:.2f}"
        )
    if purses:
        print(f"  Purse spread: min {min(purses)}  max {max(purses)}  total {sum(purses)}")


def _run_info_starvation_check() -> None:
    """Same RNG seed + GT; blocked voyages → no inbound crop reports → information-starved market stress path."""
    n = 450
    rng1 = random.Random(_RNG_SEED)
    a = Sim(rng1)
    a.load()
    for _ in range(n):
        a.advance_day()
    rng2 = random.Random(_RNG_SEED)
    b = Sim(rng2)
    b.block_npc_merchant_voyages = True
    b.load()
    for _ in range(n):
        b.advance_day()
    rep_a = sum(int(p.get("crop_inbound_reports_n", 0)) for p in a.metrics()["ports"].values())
    rep_b = sum(int(p.get("crop_inbound_reports_n", 0)) for p in b.metrics()["ports"].values())
    print("=== Phase 3 information starvation check (450 ticks, same seed) ===")
    print(f"  Inbound crop report count (sum ports): voyages ON → {rep_a}   voyages BLOCKED → {rep_b}")
    print(f"  NPC convoy formations: ON → {a.convoy_formations}   BLOCKED → {b.convoy_formations}")
    ost = "ostia" if "ostia" in a.port_names else (a.port_order[0] if a.port_order else "")
    if ost and "grain" in a.goods:
        pa = a.metrics()["ports"].get(ost, {})
        pb = b.metrics()["ports"].get(ost, {})
        bu_a = a._compute_player_buy_unit(ost, "grain")
        bu_b = b._compute_player_buy_unit(ost, "grain")
        print(
            f"  {ost} grain buy_unit: voyages ON → {bu_a}   BLOCKED → {bu_b}  "
            f"(market stress {pa.get('crop_stress_market_01', 0):.3f} vs {pb.get('crop_stress_market_01', 0):.3f})"
        )


def main() -> None:
    argv_raw = sys.argv[1:]
    if "--info-starvation-check" in argv_raw:
        _run_info_starvation_check()
        return
    no_graphs = "--no-graphs" in argv_raw
    block_voyages = "--block-npc-voyages" in argv_raw
    argv = [a for a in argv_raw if a not in ("--no-graphs", "--block-npc-voyages")]
    days = int(argv[0]) if argv else 10000
    rng = random.Random(_RNG_SEED)
    sim = Sim(rng)
    sim.block_npc_merchant_voyages = block_voyages
    sim.load()
    m0 = sim.metrics()
    max_unrest: dict[str, int] = {pid: 0 for pid in sim.port_order}
    min_grain_days: dict[str, float] = {pid: 99999.0 for pid in sim.port_order}
    ts_step = 1 if no_graphs else _timeseries_sample_step(days)
    history: list[dict] = []
    if not no_graphs:
        history.append(sim.timeseries_snapshot())
    print(f"=== Python twin: {days} ticks (RNG seed {_RNG_SEED}), data from {WORLD_PATH.name} ===")
    if block_voyages:
        print("  (NPC merchant voyages BLOCKED — Phase 3 information starvation mode)")
    print(f"  (progress log every {_progress_log_step(days)} ticks for this run length)")
    if not no_graphs and ts_step > 1:
        print(f"  (time-series samples every {ts_step} ticks for graphs; day 1 + last day always if aligned)")
    _print_block(
        f"baseline (after load + autonomy warmup; calendar day {m0.get('day', 1)} before scripted advances)",
        m0,
    )
    for d in range(days):
        sim.advance_day()
        n = d + 1
        if not no_graphs and (n % ts_step == 0 or n == days):
            history.append(sim.timeseries_snapshot())
        for pid in sim.port_order:
            max_unrest[pid] = max(max_unrest[pid], sim.get_port_food_unrest(pid))
            gf = sim.get_grain_food_days_for_port(pid)
            if gf < 9000.0:
                min_grain_days[pid] = min(min_grain_days[pid], gf)
        if _should_log_progress(n, days):
            _print_block(f"after advance #{n} (calendar day {sim.current_day})", sim.metrics())
    m1 = sim.metrics()
    print()
    print("=== end ===")
    print(f"  Food riots (total across run): {sim.riot_events}")
    print(
        f"  Phase 0 civic grain contracts: signed={sim.npc_city_grain_contracts_signed}, "
        f"fulfilled={sim.npc_city_grain_contracts_fulfilled}, breached={sim.npc_city_grain_contracts_breached}"
    )
    if sim.last_food_riot_summary:
        print(f"  Last riot tick summary: {sim.last_food_riot_summary}")
    _print_run_analysis(sim, m0, m1, max_unrest, min_grain_days)
    _print_commerce_run_summary(sim)
    _print_merchant_outcomes(sim)
    if not no_graphs and history:
        out_dir = ROOT / "tools" / "sim_analysis"
        _write_sim_timeseries_graphs(sim, history, out_dir)


if __name__ == "__main__":
    main()

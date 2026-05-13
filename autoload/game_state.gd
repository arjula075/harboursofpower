extends Node
class_name HarboursGameState

## Global simulation: calendar, ship, world graph, money/cargo, port stocks, save/load.
## Autoload name remains `GameState` in Project Settings; UI can resolve via HarboursGameState + get_node.

const _SimAgents := preload("res://autoload/sim_tick_agents.gd")
## After trade: stay docked if randf() > this; else try neighbour voyage (higher gate = more sea traffic). Sync sim.
const _NPC_DEPART_STAY_GATE := 0.45
## Max home-port merchants added or removed per port per day (smoother autonomous economy). Sync sim.
const _MERCHANT_HOME_COUNT_STEP_MAX := 6
## Parse / sanity ceiling for `world.json` `npc_traders` (not a gameplay balance cap).
const _PORT_NPC_TRADERS_LOAD_MAX := 999
## Bankruptcy rookie: only respawn if the home harbour still has wholesale activity, pulse life, or enough stock to haul.
const _NPC_BANKRUPTCY_REPLACE_MIN_PULSE := 0.20
const _NPC_BANKRUPTCY_REPLACE_MIN_PORT_STOCK_UNITS := 36

const SAVE_VERSION := 42
## Phase 1 convoy/piracy scaffold: captain hat + escort job contract (no combat yet).
## Phase 2: NPC merchant convoys — same-dest dock cohort, join roll (home/culture/agree + route openness); shared voyage days/open-sea = max over hulls; `scattered_ids` (detach memory, daily decay) + `contact_candidate_bias` (leader boarding weight; fades docked). Sync tools/sim_100_days.py.
## Phase 3: Escort job match + pay on convoy arrival. Sync tools/sim_100_days.py.
## Phase 4: NPC pirates (marines good), sea-day encounter + escort flee / boarding loot, scatter rolls, notoriety. Sync tools/sim_100_days.py.
## Phase 5: player merchant at sea can meet NPC pirates (boarding roll + loot); `player_encounter_report` for UI.
## Phase 5b: dockside crop *market* intel — posterior mean + σ→confidence, investigate (coin, tightens read), spread rumor (public delta + rep; muddies your own read).
## Phase 5c: same pattern for neighbour-war *fear* (`_port_war_rumor`): posterior vs quay truth, investigate, spread (bumps `_port_war_rumor`; rep + self-muddle).
## Phase 5d: per-port mercantile standing (`player_port_civic_reputation_01`); local officials brief true-ish grain / war fear when that score is high enough.
## Phase 5e: temple offerings — coin eases gale odds on **next** departure; capped rep from vows; civic rep drifts toward neutral daily.
## Phase 6: player hired as NPC convoy escort (`convoy_escort_player`), voyage sync after world tick, pay on arrival, pirate vs player escort.
## Phase 0 (NPC-only): civic **grain delivery** contracts — advance + deadline, sparse `npc_city_trust_01`, `merchant_repute_01`; sticky depart + voyage scoring; breach = local fine + trust hit. Toggle `world.json` `npc_city_grain_contracts_enabled`. Player UI later.
const _NPC_CITY_GRAIN_CONTRACT_OFFER_P := 0.034
const _NPC_CITY_GRAIN_CONTRACT_QTY_MIN := 5
const _NPC_CITY_GRAIN_CONTRACT_QTY_MAX := 22
const _NPC_CITY_GRAIN_CONTRACT_DUE_MIN := 16
const _NPC_CITY_GRAIN_CONTRACT_DUE_MAX := 52
const _NPC_CITY_TRUST_PORT_MAX_KEYS := 8
const _NPC_CITY_CONTRACT_TREASURY_FRAC := 0.08
const _CONVOY_MAX_MERCHANTS := 4
const _ESCORT_PAY_BASE := 16
const _ESCORT_PAY_PER_DAY := 5
const _ESCORT_PAY_OPEN_MUL := 42
const _ESCORT_PAY_MIN := 12
const _ESCORT_PAY_MAX := 320
const _ESCORT_HULL_FAST_VOYAGE_MULT := 0.94
## Convoy tail memory: one detached id may drop off the leader’s list per day (pirate gossip fades). Sync sim.
const _SCATTERED_IDS_DECAY_DAILY_P := 0.07
## While berthed, leader contact bias drifts toward neutral (next convoy still rerolls on depart). Sync sim.
const _NPC_CONTACT_BIAS_DOCKED_DECAY_MULT := 0.93
const _VOYAGE_ROLE_MERCHANT := "merchant"
const _VOYAGE_ROLE_ESCORT := "escort"
const _VOYAGE_ROLE_PIRATE := "pirate"
const _WEALTH_LERP := 0.14
const _PIRATE_MAX_ACTIVE := 6
const _PIRATE_SPAWN_PURSE_MAX := 96
const _PIRATE_SPAWN_ROLL_BASE := 0.048
const _PIRATE_DEPART_STAY_GATE := 0.38
const _ENCOUNTER_BASE_P := 0.058
const _PIRATE_FLEE_POWER_RATIO := 1.36
const _PIRATE_RAIDER_HULL_ID := "illyrian_raider"
const _PIRATE_NOTORIETY_CAP := 800.0
const _PLAYER_PIRATE_CATCH_BASE_P := 0.052

const SAVE_PATH := "user://harbours_campaign.json"
const _DEFAULT_STOCK_PER_GOOD := 50
const _DEFAULT_STOCK_SLAVES := 36
const _WORLD_TREASURY_MAX := 9999999
const _WORLD_TREASURY_FALLBACK := 9200
const _MAX_PURSE_COINS: int = 999999
## Each successful civic mint strike: fraction of `coins_per_batch` → minting port prosperity (monetary prestige). Clamped per strike. Sync tools/sim_100_days.py.
const _MINT_STRIKE_WEALTH_FRAC := 0.05
const _MINT_STRIKE_WEALTH_BONUS_MAX := 8
## Far-trade luxury import queue: fraction of landed cargo notional (buy anchor) destroyed as specie drain; treasury absorbs `treasury_take_frac` of that first. Sync tools/sim_100_days.py.
const _LUXURY_IMPORT_COST_FRAC_DEFAULT := 0.38
const _LUXURY_IMPORT_TREASURY_TAKE_FRAC_DEFAULT := 0.40
const _LUXURY_IMPORT_SINK_CAP := 420
## Slave economy: farms + mines need labor pool; shortfall cuts output; attrition consumes slaves; war victory adds captives to market stock. Keep in sync with tools/sim_100_days.py.
const _SLAVE_DEM_FARM_GRAIN := 3
const _SLAVE_DEM_FARM_WINE := 5
const _SLAVE_DEM_FARM_FISH := 4
const _SLAVE_DEM_MINE_METAL := 11
const _SLAVE_DEM_MINE_WIRE := 9
const _SLAVE_DEM_MINE_GOLD := 6
const _SLAVE_DEM_MINE_SILVER := 5
const _SLAVE_OUTPUT_FLOOR := 0.22
const _SLAVE_ATTRITION_FRAC := 0.0028
const _SLAVE_ATTRITION_OVERWORK_MUL := 0.11
const _SLAVE_WAR_CAPTIVES_BASE := 22
const _SLAVE_WAR_CAPTIVES_JITTER := 7
const _SLAVE_WAR_CAPTIVES_PER_CAMPAIGN_DAY := 5
const _SLAVE_WAR_CAPTIVES_DAY_DEN := 10
## At risk_aversion = 1.0, lot size is rand 1..mini(this, feasible cap); at 0.0, up to full feasible cap (hold/stock/coins).
const _NPC_RISK_AVERSE_MAX_LOT := 5
const _NPC_START_MONEY_MIN := 78
const _NPC_START_MONEY_MAX := 295
## Port granaries: daily loss to damp rot + vermin (fraction of stock, capped). Keep in sync with tools/sim_100_days.py.
const _GRAIN_SPOIL_FRACTION := 0.017
const _GRAIN_SPOIL_CAP := 38
const _GRAIN_SPOIL_MIN_STOCK := 14  # above this, at least 1 unit can be lost if rounding would be 0
## NPCs trade on wholesale terms vs the public bid/ask (still keyed off the same stock dynamics).
## NPC wholesale vs port bid/ask: wider spread so skilled captains compound (no piracy in model).
## Slightly favours NPC liquidity vs port (twin + canvas). Tune with sim bankruptcies / mean purse.
const _NPC_PORT_BUY_MULT := 0.765
const _NPC_PORT_SELL_MULT := 1.505
## Try to leave at least this many coins after a buy (skip or shrink lots otherwise).
const _NPC_PURSE_RESERVE := 11
## Per-NPC buy/sell mastery clamps (higher buy = pay less per unit; higher sell = earn more per unit).
const _NPC_MASTER_MIN := 0.74
const _NPC_MASTER_MAX := 1.24
## Merchant rookie replacement after `_NPC_BUST_EMPTY_STREAK_DAYS` empty-purse days: only if
## `_home_port_deserves_bankruptcy_replacement` (same-day wholesale at home, pulse, or stock to haul); else agent is removed.
## Consecutive end-of-day ticks in that state before replacement. Sync tools/sim_100_days.py.
const _NPC_BUST_EMPTY_STREAK_DAYS := 9
## Long-run “dynasty” tilt: solvent trading days nudge the weaker buy/sell mastery toward cap. Sync sim.
const _NPC_SEASON_MASTERY_DAYS := 75
const _NPC_SEASON_MASTERY_BUMP := 0.005
## Docked “dust” sell if purse below this after normal trade rounds (avoid coin-stuck captains).
const _NPC_DOCK_DUST_PURSE := 28
const _NPC_DOCK_DUST_MAX_UNITS := 8
## NPC “Big Five”–style traits (0–1): openness, conscientiousness, extraversion, agreeableness, neuroticism.
## Mild gameplay weights only; sync tools/sim_100_days.py helpers on the Sim class.
const _NPC_TRAIT_OPEN := "trait_openness"
const _NPC_TRAIT_CONSC := "trait_conscientiousness"
const _NPC_TRAIT_EXTRA := "trait_extraversion"
const _NPC_TRAIT_AGREE := "trait_agreeableness"
const _NPC_TRAIT_NEURO := "trait_neuroticism"
## Food stress: population grain demand vs granary (after full daily tick). Riots when unrest hits threshold.
const _FOOD_UNREST_DECAY := 16
const _FOOD_UNREST_DECAY_WHEN_TIGHT := 3  # when granary runway is thin but today’s ration was met; sync sim
const _FOOD_UNREST_SHORTAGE := 9
const _FOOD_UNREST_PER_MISS := 2
const _FOOD_UNREST_PANIC_LT1DAY := 11
const _FOOD_UNREST_CRITICAL_DAYS := 8  # extra when runway < 0.5 days
const _FOOD_RIOT_THRESHOLD := 190  # near cap; riot only under closing granary stress + rare roll (sync sim)
const _FOOD_RIOT_ELIGIBLE_RUNWAY_MAX := 0.30  # worst closing runway (post-trade/spoil) below this (sync sim)
const _FOOD_RIOT_ROLL_BASE := 0.0009  # daily chance when eligible (then scales with overshoot); keep sync sim
const _FOOD_RIOT_ROLL_PER_OVER := 750.0  # p += (unrest - threshold) / this; keep in sync with tools/sim_100_days.py
const _FOOD_RIOT_NO_FAMINE_VENT := 22  # ineligible for grain riot this day — bleed mob tension (sync sim)
const _FOOD_RIOT_UNREST_SCALE := 0.26  # post-riot unrest fraction → clamped band
## While at war: riot threshold starts higher (citizens tolerate early privation), eases toward base as the campaign drags. Panic spikes ramp in over _WAR_RIOT_PANIC_RAMP_DAYS. Keep in sync with tools/sim_100_days.py.
const _WAR_RIOT_GRACE_EXTRA := 25
const _WAR_RIOT_PANIC_RAMP_DAYS := 21
## When hostilities end: vent stored food tension and briefly keep riot checks high (peace used to drop threshold to base while unrest stayed war-high). Keep in sync with tools/sim_100_days.py.
const _WAR_PEACE_FOOD_UNREST_VENT := 34
const _WAR_PEACE_RIOT_GRACE_DAYS := 16
const _WAR_PEACE_RIOT_THRESHOLD_BONUS := 34
const _FOOD_RIOT_NEAR_MISS_VENT := 12  # if unrest crosses riot line but no riot, bleed off a little (avoids daily re-rolls)
## If either civilian or effective grain runway is below this, add a small daily unrest tick (pressure before outright missed rations). Sync sim.
const _FOOD_UNREST_TIGHT_RUNWAY_DAYS := 5.0
const _FOOD_UNREST_TIGHT_RUNWAY_DRIP := 2
## Population v1: famine streak → grain mouths lost; prosperity streak + headroom → growth (`_POP_PROSPERITY_POOR_UNREST_EXCEEDS` for `poor`). Farm/mine daily output scales with headcount vs founding cohort. Keep in sync with tools/sim_100_days.py.
const _POP_GRAIN_FLOOR := 4
const _POP_GRAIN_CEILING_BOOST := 22
## Consecutive harsh days before −1 grain mouth (no dedicated crop-failure layer yet — keep rare). Sync tools/sim_100_days.py.
const _POP_FAMINE_STREAK_TO_LOSS := 24
const _POP_FAMINE_STREAK_RESET := 8
## Famine streak harsh/calm: meal-based, not granary runway. Short shortages and single unrest spikes shouldn't doom a city; the iron-age default is resilience, not collapse-every-season. Sync tools/sim_100_days.py.
const _POP_FAMINE_HARSH_CONSEC_ZERO_GRAIN_DAYS := 9
const _POP_FAMINE_CALM_CONSEC_FULL_RATION_DAYS := 2
## Harsh day from unrest alone (famine streak) when no zero-grain run; only sustained Critical-tier crises (was 92 — too easy, fired during normal seasonal swings). Sync tools/sim_100_days.py.
const _POP_FAMINE_HARSH_UNREST_MIN := 118
## Prosperity → growth: lowered streak from 52 → 30 so a healthy month yields +1 mouth. Reset 14 keeps subsequent gains paced. Sync tools/sim_100_days.py.
const _POP_PROSPERITY_STREAK_TO_GAIN := 30
const _POP_PROSPERITY_STREAK_RESET := 14
## Only sustained Critical-tier unrest blocks prosperity (was 88 — wiped streaks during ordinary tension). On `poor`, streak now decays by `_POP_PROSPERITY_POOR_DECAY` instead of resetting to 0 (single bad day no longer erases weeks of recovery). Sync tools/sim_100_days.py.
const _POP_PROSPERITY_POOR_UNREST_EXCEEDS := 118
const _POP_PROSPERITY_POOR_DECAY := 4
## Iron-age rural→urban migration pull: when current pop is below the founding baseline AND the day is `wealthy`, the prosperity streak gains an extra +`floor(gap_frac × _POP_MIGRATION_PULL)` on top of the natural +1. Models second-sons, refugees, and rural surplus flowing into the metropolis (big cities = bigger empty-homes pull). Disabled once pop ≥ baseline so natural growth continues at +1/day past the founding cohort. Sync tools/sim_100_days.py.
const _POP_MIGRATION_PULL := 4
## Low commerce pulse counts toward “poor” for population prosperity (busy ports recover). 0.10 (was 0.19) keeps only truly dead trade hubs in the `poor` bucket. Sync sim.
const _COMMERCE_POOR_PULSE := 0.10
const _POP_OUTPUT_SCALE_MIN := 0.72
const _POP_OUTPUT_SCALE_MAX := 1.28
## Civic grain rationing (resilience helper A): when granary runway drops under the trigger, officials cut the per-day grain bite to `_RATION_BITE_FRAC` (min `_RATION_BITE_MIN`). Granary stretches ~40% further; demographics tick sees a partial-ration day (neither full nor zero), so the famine streak holds steady instead of climbing. Auto-ends when runway recovers or after `_RATION_MAX_DAYS`. Costs a small daily unrest tick. Sync tools/sim_100_days.py.
const _RATION_TRIGGER_FOOD_DAYS := 5.0
const _RATION_END_FOOD_DAYS := 11.0
const _RATION_BITE_FRAC := 0.62
const _RATION_BITE_MIN := 2
const _RATION_UNREST_TICK := 2
const _RATION_MAX_DAYS := 75
## Summer foraging (resilience helper B): half-sine bonus over DOY [`_FORAGE_SUMMER_START_DOY`, `_FORAGE_SUMMER_END_DOY`], peak `_FORAGE_SUMMER_PEAK_MOUTHS` mouths/day of virtual food (berries, figs, wild greens, shore fish) — never touches the granary, but counts toward `eaten_eff` in the demographics tick. Sync tools/sim_100_days.py.
const _FORAGE_SUMMER_START_DOY := 100
const _FORAGE_SUMMER_END_DOY := 235
const _FORAGE_SUMMER_PEAK_MOUTHS := 4.0
## Preserved-foods reserve (resilience helper D): per-port emergency buffer (salt fish, dried beans, olive oil) measured in mouth-days. Refills slowly when granary runway is abundant; auto-drawn to cover any grain shortfall before demographics tick scores the day. Sync tools/sim_100_days.py.
const _PRESERVED_FOOD_CAP_MULT := 8
const _PRESERVED_FOOD_CAP_MIN := 24
const _PRESERVED_FOOD_FILL_FOODDAYS_MIN := 45.0
const _PRESERVED_FOOD_FILL_PER_DAY := 0.4
const _PRESERVED_FOOD_INITIAL_FRAC := 0.5
## Baseline drift: `port_population_grain_baseline` is the city’s “institutional” size (migration target, farm scale ref). It rises slowly when population & food stay healthy; it falls slowly under prolonged collapse — not fixed to world.json forever. Small ports can outgrow old baselines; metropoles can shrink after generations of crisis. Sync tools/sim_100_days.py.
const _POP_BASELINE_RISE_FRAC := 0.88
const _POP_BASELINE_RISE_DAYS := 110
const _POP_BASELINE_FALL_FRAC := 0.58
const _POP_BASELINE_FALL_DAYS := 100
## Existential war: if `is_port_at_war` and this port’s initial burst length ≥ `population_existential_war_burst_days` (world.json; default 999 = off), famine streak needs half as many harsh days before −1 mouth (siege / Third-Punic style collapse). Sync tools/sim_100_days.py.
const _POP_EXISTENTIAL_WAR_BURST_OFF := 999
## While at war, unrest tracks “civilian” grain stress: panic uses stock ÷ peacetime ration (war ration alone must not read as famine). If granary meets peacetime draw but not full war ration, add only mild strain. Keep in sync with tools/sim_100_days.py.
const _FOOD_UNREST_WAR_RATION_GAP_PER := 1
## p2 Need-based reservation: smooth exponential curves (player vs NPC counterparty use different depth).
## Keep in sync with tools/sim_100_days.py.
const _RESERVE_REF_GRAIN_DAYS := 2.25
const _RESERVE_REF_WINE_DAYS := 1.85
const _RESERVE_CURVE_K_PLAYER := 2.35
const _RESERVE_CURVE_K_NPC := 1.05
const _RESERVE_CURVE_CAP_GRAIN_BUY_PLAYER := 0.30
const _RESERVE_CURVE_CAP_GRAIN_BUY_NPC := 0.175
const _RESERVE_CURVE_CAP_GRAIN_SELL_PLAYER := 0.34
const _RESERVE_CURVE_CAP_GRAIN_SELL_NPC := 0.195
const _RESERVE_CURVE_CAP_WINE_PLAYER := 0.28
const _RESERVE_CURVE_CAP_WINE_NPC := 0.16
const _RESERVE_STRESS_CAP := 0.38
const _RESERVE_UNREST_PER_POINT := 0.00095  # food-tier only; unrest tail added after curve
const _RESERVE_COMFORT_GRAIN_TIGHT := 0.07  # max trim on wine bid when grain runway < ~1 d
## Metal-tier goods: food stress raises industrial hoarding (asks/bids follow grain pressure, scaled).
const _RESERVE_METAL_FROM_FOOD_STRESS := 0.68
## Luxury / far-trade layer: wealth above stock attractor + mean outbound lane days.
const _LUXURY_WEALTH_EXCESS_COEF := 0.11
const _LUXURY_SPREAD_MAX := 0.34
const _FAR_TRADE_LANE_REF_DAYS := 2.75
const _FAR_TRADE_LANE_COEF := 0.14
const _FAR_TRADE_SPREAD_MAX := 0.24
const _LUXURY_FAR_COMBINED_MAX := 0.48
## Port at war (world.json `at_war` or random cycle): daily metal/wire materiel draw + stronger metal-tier reservation. Keep in sync with tools/sim_100_days.py.
const _WAR_METAL_DEMAND_STRESS := 0.24
const _WAR_METAL_RESERVE_CAP := 0.52
## While at war: farms ship less grain/wine to the port; population grain ration rises. Keep in sync with tools/sim_100_days.py.
const _WAR_FARM_OUTPUT_MULT := 0.72
const _WAR_GRAIN_RATION_MULT := 1.22
## Default / recurring campaign length when `war_days` omitted (typical ~2–3 months).
const _WAR_DEFAULT_DAYS := 75
const _WAR_MIGRATE_V7_REMAINING_DAYS := 18
## Random local wars: each recurring port draws peace then a war burst (independent RNG per port). Longer peace = less frequent wars. Keep in sync with tools/sim_100_days.py.
const _WAR_CYCLE_PEACE_MIN := 200
const _WAR_CYCLE_PEACE_MAX := 480
const _WAR_RECURRING_BURST_MIN := 50
const _WAR_RECURRING_BURST_MAX := 85
## Daily war materiel: ingots + wire (drawn bronze/copper & rigging — same need_tier as metal). Base + population scale + skim of huge local stocks.
const _WAR_MATERIEL_METAL_BASE := 8
const _WAR_MATERIEL_METAL_LINEAR := 4
const _WAR_MATERIEL_METAL_MAX := 58
const _WAR_MATERIEL_METAL_STOCK_SKIM_DIV := 120
const _WAR_MATERIEL_METAL_STOCK_SKIM_MAX := 42
const _WAR_MATERIEL_WIRE_BASE := 6
const _WAR_MATERIEL_WIRE_LINEAR_DIV := 2
const _WAR_MATERIEL_WIRE_MAX := 48
const _WAR_MATERIEL_WIRE_STOCK_SKIM_DIV := 140
const _WAR_MATERIEL_WIRE_STOCK_SKIM_MAX := 36
const _WAR_MATERIEL_DAILY_HARD_CAP := 140
## Peace-time industry: daily draw from port stock (world.json `industrial_*_per_day`). Applied before war materiel. Keep in sync with tools/sim_100_days.py.
const _INDUSTRIAL_SINK_METAL_MAX := 48
const _INDUSTRIAL_SINK_WIRE_MAX := 36
const _INDUSTRIAL_SINK_TIMBER_MAX := 24
const _INDUSTRIAL_SINK_TEXTILES_MAX := 20
## Port market: near-future demand vs stock + daily flow vs local production (world.json overrides + goods.json defaults). Keep in sync with tools/sim_100_days.py.
const _MARKET_HORIZON_DAYS := 7.0
const _MARKET_STOCK_PRESSURE_WEIGHT := 0.26
const _MARKET_FLOW_PRESSURE_WEIGHT := 0.16
const _MARKET_PRESSURE_ABS_MAX := 0.52
const _MARKET_PRICE_MULT_MIN := 0.74
const _MARKET_PRICE_MULT_MAX := 1.42
const _TRADE_PRICE_BIAS_CLAMP := 0.42
## When local wine is empty / tight, vineyard output gets a same-day bump (capped per port across farms).
const _WINE_FARM_HELP_EMPTY := 4
const _WINE_FARM_HELP_LOW := 2
const _WINE_FARM_HELP_PORT_DAILY_CAP := 10
## Trireme: crew wine from hold (grain is not drawn daily as ship running cost), docked officer pay + marine wages, hull/rigging wear at sea, dockside repair. Keep in sync with tools/sim_100_days.py.
const _SHIP_CREW_WINE_EVERY_N_DAYS := 7  # 1 unit of wine consumed every N calendar days
const _SHIP_OFFICER_PAY_DAILY := 1
const _SHIP_OFFICER_UNDERPAY_CONDITION_PENALTY := 0
## Marines: `goods.json` buy/sell = kit-out; `wage_per_unit_per_day` (optional) = docked daily wage per man (× officer pay_scale). Sync tools/sim_100_days.py.
const _MARINE_WAGE_PER_UNIT_PER_DAY_DEFAULT := 0.38
const _MARINE_WAGE_RATE_MAX := 9.0
const _SHIP_WEAR_AT_SEA := 0
const _SHIP_CONDITION_MIN := 15
const _SHIP_CONDITION_MAX := 100
const _SHIP_RATION_MISS_GRAIN_PENALTY := 0  # condition per missing grain unit
const _SHIP_RATION_MISS_WINE_PENALTY := 0
const _SHIP_REPAIR_MATERIALS_GAIN := 8
const _SHIP_REPAIR_COIN_COST := 2
const _SHIP_REPAIR_COIN_GAIN := 4
## Coin yard hire only when hull this worn. Keep in sync with tools/sim_100_days.py.
const _SHIP_REPAIR_COIN_MAX_CONDITION := 93
## Fleet: extra hulls add cargo space and scale daily crew/officer/repair coin. Keep in sync with tools/sim_100_days.py.
const _FLEET_CARGO_PER_SHIP := 24
## Nominal “new hull” value for used-slip payouts, listing caps, fleet book. New builds charge labor + port materials only.
const _FLEET_SHIP_NOMINAL_COINS := 240
const _FLEET_NEW_SHIP_LABOR_COINS := 72
const _FLEET_NEW_SHIP_TIMBER := 45
const _FLEET_NEW_SHIP_TEXTILES := 32
const _FLEET_NEW_SHIP_METAL := 24
const _FLEET_NEW_SHIP_BUILD_DAYS := 90
const _FLEET_MAX_SHIPS := 12
const _FLEET_REPAIR_COIN_PER_EXTRA_SHIP := 1
## Coin destroyed on dock trades (porters, measures, petty dues); not added to port stock math. Keep in sync with tools/sim_100_days.py.
const _CAPTAIN_TRADE_FEE_BUY_DIV := 32
const _CAPTAIN_TRADE_FEE_SELL_DIV := 40
## Per-port `tolls` in world.json: coins per unit on **sales into the city** (import duty). Buys from the quay are not tolled.
## NPCs may smuggle duties or pay graft to skip.
## When a port levies any toll, wholesale buy/sell curves tilt slightly in merchants' favour so most stay solvent.
const _TOLL_MERCHANT_BUY_RELIEF := 0.048
const _TOLL_MERCHANT_SELL_RELIEF := 0.078
const _TOLL_NPC_BRIBE_DAILY_CHANCE := 0.055
const _TOLL_BRIBE_DAYS_MIN := 5
const _TOLL_BRIBE_DAYS_MAX := 14
## Each docked calendar day after cargo trade: wharfage + scaled levy on large purses (paid to port prosperity; busier quay bonus). Keep in sync with tools/sim_100_days.py.
const _HARBOUR_DUE_BASE := 1
const _HARBOUR_DUE_PER_SHIP := 1
const _HARBOUR_DUE_PURSE_THRESHOLD := 350
const _HARBOUR_DUE_PURSE_DIV := 22
const _HARBOUR_DUE_PROGRESSIVE_CAP := 72
## Harbour dues flow into port prosperity; busier quays yield a larger wealth bump per coin (same total due from each captain).
const _HARBOUR_BUSY_PER_DOCK_PCT := 3
const _HARBOUR_BUSY_MAX_BONUS_PCT := 36
const _HARBOUR_WEALTH_PER_COINS_PAID := 8
## Used hulls: captains sell a hull for immediate coin; a slip listing appears at the port for others (NPC/PC) docked there.
## Forced when officer purse is short and the hold is empty (must liquidate a hull if fleet > 1 and cargo still fits after).
## Voluntary listings when daybooks are covered but the captain still chooses to trim the fleet. Keep in sync with tools/sim_100_days.py.
const _USED_HULL_MIN_PAYOUT := 22
const _USED_HULL_PAYOUT_FRAC_LOW := 0.28
const _USED_HULL_PAYOUT_FRAC_HIGH := 0.50
const _USED_HULL_ASK_MARKUP := 1.12
const _USED_HULL_MAX_PER_PORT := 10
## Bust-replacement rookies may inherit the cheapest slip hull (guild charter; no purse spend).
const _ROOKIE_BANKRUPTCY_USED_HULL_CHANCE := 0.46
## Port wealth soft ding vs listing ask when a rookie is placed into a slip hull (charter subsidy fiction).
const _ROOKIE_USED_HULL_CHARTER_WEALTH_DIV := 14
## NPC↔NPC dock loans (no bank): debtor keeps { creditor, remaining } on agent; repay from sell margin; traits bias flee.
const _NPC_PEER_LOAN_MAX_DEBTS := 2
const _NPC_PEER_LOAN_MIN_PRINCIPAL := 30
const _NPC_PEER_LOAN_MAX_PRINCIPAL := 130
const _NPC_PEER_LOAN_OFFER_ROLL := 0.16
const _NPC_PEER_LOAN_DEBTOR_PURSE_MAX := 34
const _NPC_PEER_LOAN_CREDITOR_PURSE_MIN := 118
const _NPC_PEER_LOAN_CREDITOR_RESERVE := 22
const _NPC_PEER_LOAN_HOME_AVOID_PER_COIN := 0.018
const _NPC_PEER_LOAN_FLEE_GATE_SUB_MAX := 0.22
## Free sailing: coastal shortest path vs shorter “bold” offshore shortcut (higher storm openness). Sync tools/sim_100_days.py.
const _VOYAGE_BOLD_DAY_MULT := 0.70
const _VOYAGE_COASTAL_OPENNESS := 0.07
const _VOYAGE_DISCONNECTED_BASE_DAYS := 15
## Daily storm check while at sea (long booked legs + open water raise p). Hull loss only if fleet > 1.
## Abstract 360-day calendar: grain/wine from farms only in harvest window (wine annual mass vs nominal; grain also × `_FARM_GRAIN_MASS_MULT`).
## Winter = higher storm odds at sea; recurring local wars start in summer (or defer to next summer).
## Sync tools/sim_100_days.py.
const _CALENDAR_YEAR_LEN := 360
const _HARVEST_START_DOY := 181
const _HARVEST_END_DOY := 240
const _HARVEST_DAYS := (_HARVEST_END_DOY - _HARVEST_START_DOY + 1)
## Off-season trickle (fraction of farm's nominal daily rate) so granaries aren't empty all spring; harvest scale picks up the slack to preserve ~360× annual mass.
## Inter-harvest trickle (fraction of nominal farm rate); harvest scale is derived to preserve ~360× annual mass. Raised from 6%: lean season + winter shipping could not refill granaries before next harvest.
const _CROP_OFFSEASON_SCALE := 0.10
const _CROP_HARVEST_DAILY_SCALE := (
	(float(_CALENDAR_YEAR_LEN) - float(_CALENDAR_YEAR_LEN - _HARVEST_DAYS) * _CROP_OFFSEASON_SCALE)
	/ float(_HARVEST_DAYS)
)
const _PORT_ROLE_BREADBASKET := "breadbasket"
## Extra multiplier on farm grain & wine into ports with world.json role `breadbasket`. Sync tools/sim_100_days.py.
const _BREADBASKET_FARM_GRAIN_WINE_MULT := 1.15
## Global bump to farm **grain** only (not wine/fish): raises annual grain mass above nominal 360× `grain_per_day` closure. Sync tools/sim_100_days.py.
const _FARM_GRAIN_MASS_MULT := 1.58
## Per-port crop moisture/growth (twin-parity, no RNG). Moisture tracks a seasonal target; growth lags moisture. Sync tools/sim_100_days.py.
const _CROP_MOISTURE_ADJUST_RATE := 0.055
const _CROP_GROWTH_LAG_RATE := 0.11
const _CROP_GRAIN_YIELD_MULT_MIN := 0.88
const _CROP_GRAIN_YIELD_MULT_MAX := 1.06
const _CROP_STRESS_PRICE_BUY_THRESHOLD := 0.52
const _CROP_STRESS_PRICE_BUY_EXTRA := 0.12
const _CROP_STRESS_PRICE_SELL_THRESHOLD := 0.48
const _CROP_STRESS_PRICE_SELL_DISC := 0.055
## Phase 2: severity ladder + economy coupling (twin-parity, deterministic). Major extras only if war + drought moisture + weak neighbor grain relief. Sync tools/sim_100_days.py.
const _CROP_PHASE2_DROUGHT_MOISTURE_MAX := 0.34
const _CROP_PHASE2_NEIGHBOR_GRAIN_ISOLATED_MAX := 48
const _CROP_PHASE2_BIAS_STRESS_LO := 0.38
const _CROP_PHASE2_BIAS_STRESS_HI := 0.58
const _CROP_PHASE2_BIAS_MAX_ADD := 0.20
const _CROP_PHASE2_BIAS_MAJOR_EXTRA := 0.08
const _CROP_PHASE2_BIAS_MAJOR_STRESS_MIN := 0.46
const _CROP_PHASE2_UNREST_STRESS_MID := 0.48
const _CROP_PHASE2_UNREST_STRESS_HIGH := 0.62
const _CROP_PHASE2_UNREST_MAJOR_STRESS_MIN := 0.54
const _CROP_PHASE2_UNREST_ADD_MID := 1
const _CROP_PHASE2_UNREST_ADD_HIGH := 2
const _CROP_PHASE2_UNREST_ADD_MAJOR := 1
const _CROP_PHASE2_UNREST_DAILY_CAP := 4
const _CROP_PHASE2_HOARD_STRESS_LO := 0.36
const _CROP_PHASE2_HOARD_MAJOR_BOOST := 0.26
const _CROP_PHASE2_NPC_GRAIN_SELL_FLOOR_SHIFT := 0.15
const _CROP_PHASE2_NPC_GRAIN_BUY_CEIL_SHIFT := 0.13
const _CROP_PHASE2_NPC_GRAIN_P_BUY_SHIFT := 0.22
## Phase 3: crop information — locals ≈ GT+noise; foreign merchants inject delayed noisy origin reports into port FIFO; market grain prices use blend(local, mean(reports)). Sync tools/sim_100_days.py.
const _CROP_INFO_LOCAL_NOISE_MAX := 0.048
const _CROP_INFO_REPORT_NOISE_MAX := 0.095
const _CROP_INFO_MARKET_REPORT_MAX := 8
const _CROP_INFO_MARKET_LOCAL_WEIGHT := 0.52
## Phase 4: crop rumors shift *public* market stress (additive delta); GT unchanged. Harvest window + trusted arrivals correct. Sync tools/sim_100_days.py.
const _CROP_RUMOR_DELTA_ABS_MAX := 0.26
const _CROP_RUMOR_DAILY_DECAY := 0.987
const _CROP_RUMOR_HARVEST_EXTRA_DECAY := 0.93
const _CROP_RUMOR_SICILY_EVENT_DAILY_P := 0.0024
const _CROP_RUMOR_SICILY_BUMPER_MAG_MIN := 0.072
const _CROP_RUMOR_SICILY_BUMPER_MAG_MAX := 0.14
const _CROP_RUMOR_SICILY_FAIL_MAG_MIN := 0.055
const _CROP_RUMOR_SICILY_FAIL_MAG_MAX := 0.12
const _CROP_RUMOR_GT_CORREL := 0.028
## Phase 5b: player crop market-stress intel (UI; not GT).
const _PLAYER_CROP_INTEL_SIGMA_INIT := 0.24
const _PLAYER_CROP_INTEL_SIGMA_MIN := 0.042
const _PLAYER_CROP_INTEL_SIGMA_CONF_SCALE := 0.36
const _PLAYER_CROP_INVESTIGATE_COINS := 32
const _PLAYER_INTEL_ROUTES_REFRESH_COINS := 10
const _PLAYER_INTEL_PIRACY_SCUTTLEBUTT_COINS := 12
const _PLAYER_CROP_SPREAD_RUMOR_COINS := 12
const _PLAYER_CROP_SPREAD_DELTA := 0.052
## Phase 5c: war-fear intel (reuses σ scale constants above).
const _PLAYER_WAR_INVESTIGATE_COINS := 28
const _PLAYER_WAR_SPREAD_RUMOR_COINS := 14
const _PLAYER_WAR_RUMOR_SPREAD_BUMP := 0.065
## Phase 5d: per-port mercantile board vs harbor clerks (official quarter briefings).
const _LOCAL_PORT_CIVIC_RUMOR_HIT := 0.034
const _LOCAL_PORT_CIVIC_INVESTIGATE_BUMP := 0.012
const _LOCAL_PORT_CIVIC_MINT_BUMP := 0.022
const _LOCAL_PORT_CIVIC_GRAFT_HIT := 0.048
const _OFFICIAL_LOCAL_REP_HINT := 0.43
const _OFFICIAL_LOCAL_REP_SOLID := 0.58
const _OFFICIAL_LOCAL_REP_NUMERIC := 0.72
## Phase 5e: temple vows + ambient reputation fading (toward neutral 50%).
const _TEMPLE_OFFERING_SMALL_COINS := 16
const _TEMPLE_OFFERING_MEDIUM_COINS := 48
const _TEMPLE_OFFERING_LARGE_COINS := 120
const _TEMPLE_STORM_PENDING_P_SUB_SMALL := 0.0028
const _TEMPLE_STORM_PENDING_P_SUB_MEDIUM := 0.0058
const _TEMPLE_STORM_PENDING_P_SUB_LARGE := 0.0095
const _TEMPLE_STORM_PENDING_P_SUB_TOTAL_CAP := 0.0155
const _TEMPLE_REP_GRANT_SMALL := 0.0058
const _TEMPLE_REP_GRANT_MEDIUM := 0.0095
const _TEMPLE_REP_GRANT_LARGE := 0.014
const _TEMPLE_REP_LIFETIME_CAP := 0.108
## Fraction of offering coin remitted to the abstract world mint pool (`_world_treasury_coins`); quaestor tithe mirrors civic mint bookkeeping.
const _TEMPLE_OFFERING_TREASURY_FRAC := 0.265
const _CIVIC_REPUTATION_NEUTRAL_01 := 0.50
const _CIVIC_REPUTATION_DRIFT_STEP := 0.0035
const _CROP_RUMOR_HIGH_TRUST_DAMP_P := 0.055
const _CROP_RUMOR_HIGH_TRUST_DAMP_MULT := 0.68
const _SEASON_SUMMER_START_DOY := 91
const _SEASON_SUMMER_END_DOY := 180
const _SEASON_WINTER_START_DOY := 271
const _STORM_SEASON_WINTER_MULT := 1.24
const _STORM_SEASON_AUTUMN_MULT := 1.08
const _FISH_SEASON_WINTER_MULT := 0.96
const _VOYAGE_STORM_BASE_P := 0.0036
const _VOYAGE_STORM_PER_BOOKED_DAY := 0.00175
const _VOYAGE_STORM_OPEN_MULT := 0.05
const _VOYAGE_STORM_P_CAP := 0.195
const _VOYAGE_STORM_COND_DAMAGE_MIN := 5
const _VOYAGE_STORM_COND_DAMAGE_MAX := 15
const _VOYAGE_STORM_HULL_LOSS_CHANCE := 0.12
const _SHIP_AGE_STORM_DAMAGE_SCALE := 0.42
const _SHIP_AGE_LEAK_DAILY_P := 0.011
const _SHIP_REFIT_LABOR_COINS := 44

signal day_advanced(new_day: int)
## Fired after a tick where at least one port had a grain riot (combined message).
signal food_riot_report(summary: String)
## Dockside / agora grain gossip (Phase 4); does not change GT crop, only market-facing stress blend.
signal crop_rumor_report(summary: String)
signal voyage_started(to_port_id: String, days: int)
signal voyage_completed(at_port_id: String)
signal game_saved(path: String)
signal game_loaded(path: String)
signal game_load_failed(reason: String)
signal cargo_changed()
signal money_changed()
signal market_changed()
## Sea boarding / piracy (and later escort notices): short line for the status strip after `advance_day`.
signal player_encounter_report(summary: String)

var _pending_player_encounter_msg: String = ""

var current_day: int = 1

var _port_names: Dictionary = {}  # id -> display name
## Optional chart positions from world.json `map_u` / `map_v` in [0,1] for UI sea-chart.
var _port_map_uv: Dictionary = {}  # id -> Vector2
var _lane_days: Dictionary = {}  # "from|to" -> int days
## Sparse NPC voyage graph from world.json `npc_lanes` (optional). When non-empty, NPC merchants use this
## graph for `_voyage_plan` coastal shortest days; player keeps full `lanes`. Sync tools/sim_100_days.py.
var _npc_lane_days: Dictionary = {}  # "from|to" -> int days
## port_id -> Array[String] neighbor port ids (undirected).
var _port_neighbors: Dictionary = {}
## Neighbors derived from `_npc_lane_days` only (for NPC voyage cache).
var _port_neighbors_npc: Dictionary = {}
## Cached coastal shortest travel days `from|to` (int days, or -1 if unreachable by lanes alone).
var _voyage_coastal_shortest_cache: Dictionary = {}
## Same as above but on `_npc_lane_days` when present.
var _voyage_coastal_shortest_cache_npc: Dictionary = {}
var _goods: Dictionary = {}  # id -> { name, buy, sell, stock_target, optional market_demand_per_day }
## Per-port commodity stock (city + warehouses abstraction).
var _port_stocks: Dictionary = {}  # port_id -> Dictionary good_id -> int
## Parsed from world.json before goods exist — finalized in _finalize_port_stocks().
var _port_initial_stock: Dictionary = {}  # port_id -> Dictionary good_id -> int
## Per-port simulation tuning (from world.json).
var _port_npc_trader_count: Dictionary = {}  # port_id -> int (from world.json; clamped 1.._PORT_NPC_TRADERS_LOAD_MAX on load)
var _port_population_grain: Dictionary = {}  # port_id -> int eaten from port stock per day
var _port_population_wine_base: Dictionary = {}  # port_id -> base wine units / day before wealth scaling
var _port_population_fish_per_day: Dictionary = {}  # port_id -> fixed fish ration / day (coastal protein)
## founding cohort size (from world at load); farm/mine output scales vs this.
var _port_population_grain_baseline: Dictionary = {}  # port_id -> int
var _port_population_grain_cap: Dictionary = {}  # port_id -> int max grain mouths
var _port_famine_streak_days: Dictionary = {}  # port_id -> int consecutive harsh-food days
## Consecutive days population received a full grain ration (eaten >= need); resets famine streak when ≥ `_POP_FAMINE_CALM_CONSEC_FULL_RATION_DAYS` and unrest < 38.
var _port_consecutive_grain_full_ration_days: Dictionary = {}  # port_id -> int
## Consecutive days with **zero** grain eaten while need > 0; counts toward harsh famine pressure.
var _port_consecutive_grain_zero_eat_days: Dictionary = {}  # port_id -> int
var _port_prosperity_streak_days: Dictionary = {}  # port_id -> int consecutive prosperous days
## Civic rationing toggle + consecutive days active (resilience helper A — see `_RATION_*`).
var _port_rationing_active: Dictionary = {}  # port_id -> bool
var _port_rationing_days_active: Dictionary = {}  # port_id -> int
## Preserved-foods reserve (mouth-day units; float for fractional daily refill, see `_PRESERVED_FOOD_*`).
var _port_preserved_food: Dictionary = {}  # port_id -> float
var _port_initial_wealth: Dictionary = {}  # port_id -> optional starting liquidity (abstract coin)
## world.json `port_role_wealth_bonuses` keyed by port `role` — added to stock-implied wealth attractor.
var _port_role_wealth_bonus: Dictionary = {}  # port_id -> int
## world.json each port `role` id (e.g. breadbasket) for mechanics beyond wealth bonus.
var _port_roles: Dictionary = {}  # port_id -> String
## Optional per port: `population_existential_war_burst_days` in world.json — if current war’s `burst_initial` ≥ this (and value < `_POP_EXISTENTIAL_WAR_BURST_OFF`), famine losses accelerate for that campaign.
var _port_existential_war_burst_days: Dictionary = {}  # port_id -> int
## Counters for baseline drift (not saved; reset on load).
var _port_baseline_momentum_up: Dictionary = {}  # port_id -> int
var _port_baseline_momentum_dn: Dictionary = {}  # port_id -> int
## Smoothed local prosperity; high values increase wine demand.
var _port_wealth: Dictionary = {}  # port_id -> int
## Filled at the start of each daily sim tick (before voyages, farms, wealth refresh, population, NPCs).
var _wealth_snapshot_tick_start: Dictionary = {}  # port_id -> int
## Stock-implied wealth attractor at that same moment (see _wealth_stock_target_value).
var _wealth_stock_target_tick_start: Dictionary = {}  # port_id -> int
## Farmland that ships into a port each tick: { id, name, port_id, grain_per_day, wine_per_day, optional fish_per_day }
var _farms: Array = []
## Mines: daily ingot + wire output into a port (same tick as farms).
var _mines: Array = []
## world.json `mint` on a port: civic batches consume port-stock Au/Ag → world treasury (with sink frac).
var _port_mint_cfg: Dictionary = {} # port_id -> { gold_per_batch, silver_per_batch, coins_per_batch, max_batches_per_day, treasury_sink_frac }
## Optional root `luxury_import` in world.json; defaults used if absent. Bullion excluded from auto-queue (mines + mint handle Au/Ag).
var _luxury_import_cfg: Dictionary = {}
## port_id -> Array of { "g": good_id, "q": int, "d": int } — days until consignment lands.
var _port_luxury_import_queue: Dictionary = {}
## State-mint coin pool (NPC spawn draws first; municipal mint pulse refills). Not a full bank ledger.
var _world_treasury_coins: int = 0
## Snapshot of world.json `initial_treasury_coins` for migrating saves older than SAVE_VERSION 26.
var _world_initial_treasury_coins: int = 0
## Last resolved population bites (for UI / admin).
var _last_pop_digest: Dictionary = {}  # port_id -> { "grain": int, "wine": int }
## Per port: days of war left (0 = peace). Seeded from world.json at_war + war_days; ticks down daily. Keep in sync with sim.
var _port_war_days_remaining: Dictionary = {}  # port_id -> int
## If true (default from world.json), port runs its own random peace→war burst cycle (world.json war_recurring: false to opt out).
var _port_war_recurring: Dictionary = {}  # port_id -> bool
## Days until next recurring war burst (only when recurring and not at war).
var _port_war_peace_remaining: Dictionary = {}  # port_id -> int
## Recurring war: burst length rolled when peace hits 0 but calendar is not summer — starts next summer.
var _port_war_pending_burst: Dictionary = {}  # port_id -> int days
## When a war burst begins, original campaign length (for elapsed → riot threshold + panic ramp). Cleared when war ends.
var _port_war_burst_initial: Dictionary = {}  # port_id -> int
## Last tick war draw from port stock (ingots + wire).
var _last_war_industry_digest: Dictionary = {}  # port_id -> { "metal": int, "wire": int }
## world.json `industrial_*_per_day` (peace-time workshops, shipyards, wood yards, looms).
var _port_industrial_metal_per_day: Dictionary = {}  # port_id -> int
var _port_industrial_wire_per_day: Dictionary = {}  # port_id -> int
var _port_industrial_timber_per_day: Dictionary = {}  # port_id -> int
var _port_industrial_textiles_per_day: Dictionary = {}  # port_id -> int
## world.json `trade_price_bias` per good: multiplier offset (final ≈ 1 + clamp(bias)).
var _port_trade_price_bias: Dictionary = {}  # port_id -> Dictionary good_id -> float
## world.json `market_demand_per_day` per good: explicit units/day for pricing (replaces auto estimate for listed goods).
var _port_market_demand_override: Dictionary = {}  # port_id -> Dictionary good_id -> float
## port_id -> Dictionary good_id -> int coins per unit import duty (applied when selling **to** the port). From world.json `tolls` per port.
var _port_good_tolls: Dictionary = {}
## port_id -> last calendar day (inclusive) player customs graft suppresses tolls there.
var _player_toll_graft_until: Dictionary = {}
## Last tick industrial consumption (cannot exceed on-hand stock).
var _last_industrial_sink_digest: Dictionary = {}  # port_id -> metal, wire, timber, textiles
## Grain lost to spoilage/vermin on the last daily tick (port_id -> int).
var _last_grain_spoilage: Dictionary = {}
## Last tick: slave labor demand, stock before losses, deaths, output mult, optional war captives (port_id -> Dictionary).
var _last_slave_digest: Dictionary = {}
## End-of-tick grain stock / population grain demand (same eat rate as UI "grain/day").
var _last_grain_food_days: Dictionary = {}  # port_id -> float
## 0–200; grain shortage + low runway add; full rations decay. At threshold triggers a riot tick.
var _port_food_unrest: Dictionary = {}  # port_id -> int
## Days left where riot threshold stays boosted after a war ends (see _WAR_PEACE_*).
var _port_peace_riot_grace_days: Dictionary = {}  # port_id -> int
## Phase 4 pirate combat aggregates (session cumulative; reset on new GameState / load as 0).
var _pirate_metrics_attempts: int = 0
var _pirate_metrics_raids: int = 0
var _pirate_metrics_flees: int = 0
var _pirate_metrics_marines_lost: int = 0
var _pirate_metrics_loot_coins: int = 0
## Coins paid to the player on NPC convoy escort jobs (Phase 6); headless metrics only.
var _escort_player_coins_paid: int = 0
## Last riot line(s) from the most recent sim tick (for admin / debugging).
var _last_food_riot_summary: String = ""
## Traveling NPC merchants: cargo + docked_port or at-sea voyage (same day-tick model as player).
var _npc_agents: Array = []
var _npc_next_agent_id: int = 0
## Per port, same-day NPC dock wholesale (mirrors tools/sim_100_days.py `_port_commerce_tick`).
var _port_commerce_tick: Dictionary = {}
## Smoothed 0–1 “quay activity” from dock traffic, harbour dues, and NPC trade volume.
var _port_commerce_pulse: Dictionary = {}
## Harbour due coins collected this daily tick (NPC loop; reset tick start). Sync sim.
var _port_harbour_due_coins_tick: Dictionary = {}
## Dockside cartel / ring strength 0–1 (rich NPC cluster tightens wholesale vs the port).
var _port_cartel_strength: Dictionary = {}
## Neighbour-at-war gossip 0–1 (decays; biases staple/strategic prices via rumours).
var _port_war_rumor: Dictionary = {}
## Per-good false or specific rumour delta added on top of war fear (decays). port_id -> good_id -> float.
var _port_rumor_good_delta: Dictionary = {}
## Plague days remaining: suppresses wealth attractor and can cost population. Sync sim.
var _port_plague_days: Dictionary = {}
## From world.json `autonomy_warmup_days`: invisible daily ticks on fresh campaigns (no save file).
var _world_autonomy_warmup_days: int = 24
## When false, crop agro tick/yield/price/unrest hooks are no-ops (world.json `crop_agro_model`, default true).
var _world_crop_agro_model: bool = true
## Phase 0: NPC civic grain contracts (offers + routing bias + voyage score); fulfill/breach tick always runs. world.json `npc_city_grain_contracts_enabled`, default true.
var _world_npc_city_grain_contracts_enabled: bool = true
## When true, NPC merchant convoys/solo depart are skipped (twin/debug: information starvation vs same GT).
var block_npc_merchant_voyages: bool = false
## port_id -> 0..1 soil moisture (abstract).
var _port_crop_moisture_01: Dictionary = {}
## port_id -> 0..1 standing crop condition (lags moisture).
var _port_crop_growth_01: Dictionary = {}
## Phase 3: collective local crop-stress belief (GT + small daily noise).
var _port_local_crop_belief_01: Dictionary = {}
## Phase 3: port_id -> Array of recent inbound foreign crop-stress reports (FIFO cap).
var _port_inbound_crop_reports: Dictionary = {}
## Phase 4: port_id -> additive public rumor skew on crop *market* stress (not GT). Decays daily; harvest damps faster.
var _port_crop_rumor_public_delta: Dictionary = {}
## One line for UI activity block (cleared each dawn tick, set when a rumor fires).
var _last_crop_rumor_ui_line: String = ""

var _rng := RandomNumberGenerator.new()

var player_port_id: String = ""
var voyage_dest_id: String = ""
var voyage_days_remaining: int = 0
## Set at voyage start for storm odds (does not tick down with remaining days).
var player_voyage_booked_days: int = 0
var player_voyage_open_sea_01: float = 0.0
## Higher = more likely to pick the safer (longer) coastal route vs bold shortcut when the roll allows.
var player_voyage_risk_aversion: float = 0.48
## `merchant` | `escort` | `pirate` — escort/pirate behaviour comes in later phases.
var player_voyage_role: String = _VOYAGE_ROLE_MERCHANT
## Active escort job: employer NPC id, agreed pay, route, day the contract started (`current_day`). Cleared on voyage arrival.
var player_escort_contract: Dictionary = {}
## When true, NPC convoy leaders may hire the player as escort if docked with a suitable hull (Phase 6).
var player_offers_convoy_escort: bool = true
## Port id for which `player_crop_intel_*` was last reset (new visit when it differs from `player_port_id`).
var player_crop_intel_port_id: String = ""
## Player's posterior mean for **market** grain stress (0..1), vs ground-truth blend in `_crop_grain_stress_01_market_for_port`.
var player_crop_intel_mean_01: float = 0.5
## Uncertainty (higher σ ⇒ lower confidence in UI).
var player_crop_intel_sigma_01: float = _PLAYER_CROP_INTEL_SIGMA_INIT
## Calendar day the notebook was last refreshed (investigate) or port visit reset.
var player_crop_intel_update_day: int = 0
## 0..1 — how “clean” your name is on the quay; spreading rumors costs face.
var player_civic_reputation_01: float = 0.62
## port_id -> 0..1 — mercantile / quaestor standing **in that city** (official intel gates on this; falls back to `player_civic_reputation_01` if unset).
var player_port_civic_reputation_01: Dictionary = {}
## Port id for which `player_war_intel_*` was last reset (new visit when it differs from `player_port_id`).
var player_war_intel_port_id: String = ""
## Posterior mean for **war fear** at the quay (`_port_war_rumor`, 0..1).
var player_war_intel_mean_01: float = 0.35
var player_war_intel_sigma_01: float = _PLAYER_CROP_INTEL_SIGMA_INIT
var player_war_intel_update_day: int = 0
## Storm probability **subtractor** queued at temple → applied on **current** voyage only (consumes queued amount at departure).
var player_voyage_weather_bless_p_sub: float = 0.0
## Accumulated temple storm relief for the **next** merchant/escort departure (capped until transferred at sail).
var player_temple_pending_storm_p_sub: float = 0.0
## Lifetime rep already granted via temple offerings (caps bought face; fades still apply separately).
var player_temple_offerings_rep_granted_01: float = 0.0

## Player-visible ledger + market memory (evidence UI). Sync SAVE_VERSION / save/load.
var _player_ledger_by_port: Dictionary = {}
## Composite key "%s|%s" % [port_id, good_id] -> last calendar day's buy unit (end-of-tick snapshot) for trend.
var _player_market_buy_prev: Dictionary = {}
## good_id -> day of last dock trade (buy or sell) by player.
var _player_good_last_trade_day: Dictionary = {}
## Day the player last paid clerks to refresh route/piracy tables at the quay.
var _player_route_intel_refresh_day: int = 0

## Sea-chart grouping for City → Ledger (`world.json` chart_areas + per-port chart_area_id).
const _LEDGER_CHART_AREA_FALLBACK := "_unassigned"
var _chart_area_labels: Dictionary = {} ## area_id -> display name
var _chart_area_notes: Dictionary = {} ## area_id -> optional description
var _port_chart_area_id: Dictionary = {} ## port_id -> area_id

## Hull design for the whole convoy (all hulls match this slip; refit swaps the design). See `data/ships.json`.
var player_ship_class_id: String = ""
## Captain’s naval culture (Italic, Greek, …) — mismatched hulls cost more in wine/officers.
var player_captain_culture: String = "italic"
## Calendar days this hull lineage has been in service (wear, storm vulnerability creep).
var player_ship_age_days: int = 0

var player_money: int = 300
## good_id -> quantity (int)
var player_cargo: Dictionary = {}
## Hull, rigging, oars (100 = sound; wear + missed rations pull it down). Dock repairs when materials or coin available.
var player_ship_condition: int = _SHIP_CONDITION_MAX
## Increments each day; wine ration when counter % _SHIP_CREW_WINE_EVERY_N_DAYS == 0.
var player_ship_wine_counter: int = 0
## Convoy size (≥1). Each ship adds _FLEET_CARGO_PER_SHIP cargo capacity and scales crew pay/rations.
var player_fleet_ships: int = 1
## New hull ordered at `player_fleet_shipyard_port_id`; counts down daily, then +1 ship.
var player_fleet_shipyard_days_remaining: int = 0
var player_fleet_shipyard_port_id: String = ""
## port_id -> Array of { "id": int, "ask": int, "condition": int } (slip-side used hulls after a captain’s fire sale).
var _port_used_hull_listings: Dictionary = {}
var _next_used_hull_listing_id: int = 1
## ship_id -> ship definition (from `data/ships.json`).
var _ship_classes: Dictionary = {}
var _ship_default_id: String = "greek_merchant"
## port_id -> PackedStringArray of ship ids offered at that slip.
var _port_shipyard_classes: Dictionary = {}
## port_id -> culture id for captains raised there (NPC + player start).
var _port_cultures: Dictionary = {}


func _ready() -> void:
	_rng.randomize()
	_load_world("res://data/world.json")
	_load_goods("res://data/goods.json")
	_prune_port_tolls_to_known_goods()
	_load_ship_catalog("res://data/ships.json")
	_finalize_port_stocks()
	_bootstrap_npc_agents()
	_init_port_wealth_baseline()
	_init_port_food_unrest_zero()
	if player_port_id.is_empty() and not _port_names.is_empty():
		player_port_id = str(_port_names.keys()[0])
	_apply_new_game_defaults()
	call_deferred("_maybe_run_world_autonomy_warmup")


func _maybe_run_world_autonomy_warmup() -> void:
	if FileAccess.file_exists(SAVE_PATH):
		if _player_seed_opening_ledger_hearsay_if_empty():
			market_changed.emit()
		return
	var n: int = clampi(_world_autonomy_warmup_days, 0, 180)
	for _i in n:
		_run_daily_population_and_npcs()
		current_day += 1
	if n > 0:
		market_changed.emit()
		day_advanced.emit(current_day)
	if _player_seed_opening_ledger_hearsay_if_empty():
		market_changed.emit()


func _apply_new_game_defaults() -> void:
	if player_cargo.is_empty():
		player_cargo["grain"] = 5
		player_cargo["wine"] = 2
	if player_ship_class_id.is_empty() or not _ship_classes.has(player_ship_class_id):
		player_ship_class_id = _default_ship_class_for_port(player_port_id)
	if player_captain_culture.is_empty():
		player_captain_culture = str(_port_cultures.get(player_port_id, "italic"))
	player_civic_reputation_01 = 0.62
	player_port_civic_reputation_01.clear()
	player_crop_intel_port_id = ""
	player_crop_intel_mean_01 = 0.5
	player_crop_intel_sigma_01 = _PLAYER_CROP_INTEL_SIGMA_INIT
	player_crop_intel_update_day = 0
	player_war_intel_port_id = ""
	player_war_intel_mean_01 = 0.35
	player_war_intel_sigma_01 = _PLAYER_CROP_INTEL_SIGMA_INIT
	player_war_intel_update_day = 0
	player_voyage_weather_bless_p_sub = 0.0
	player_temple_pending_storm_p_sub = 0.0
	player_temple_offerings_rep_granted_01 = 0.0
	_ensure_player_voyage_role_and_contract()


func get_port_name(port_id: String) -> String:
	return str(_port_names.get(port_id, port_id))


func get_port_chart_area_id(port_id: String) -> String:
	var ps := str(port_id)
	if _port_chart_area_id.has(ps):
		return str(_port_chart_area_id[ps])
	return _LEDGER_CHART_AREA_FALLBACK


func get_chart_area_display_name(area_id: String) -> String:
	var aid := str(area_id)
	return str(_chart_area_labels.get(aid, aid.replace("_", " ").capitalize()))


func get_chart_area_description(area_id: String) -> String:
	return str(_chart_area_notes.get(str(area_id), ""))


## Sea-chart anchor in [0,1]×[0,1] if world.json defines `map_u` / `map_v`; else (-1,-1).
func get_port_map_uv(port_id: String) -> Vector2:
	var ps := str(port_id)
	if _port_map_uv.has(ps):
		return _port_map_uv[ps] as Vector2
	return Vector2(-1.0, -1.0)


func is_port_at_war(port_id: String) -> bool:
	return get_port_war_days_remaining(port_id) > 0


func get_port_war_days_remaining(port_id: String) -> int:
	var ps := str(port_id)
	if not _port_names.has(ps):
		return 0
	return maxi(0, int(_port_war_days_remaining.get(ps, 0)))


## Grain eaten from port stock per day (base ration × war stress when at war).
func get_population_grain_eat_effective(port_id: String) -> int:
	var ps := str(port_id)
	var base: int = clampi(int(_port_population_grain.get(ps, 0)), 0, 120)
	if base <= 0 or not is_port_at_war(ps):
		return base
	return clampi(int(ceil(float(base) * _WAR_GRAIN_RATION_MULT)), base + 1, 120)


func is_at_sea() -> bool:
	return voyage_days_remaining > 0


func get_location_summary() -> String:
	if is_at_sea():
		var sea_note: String = (
			" · open-water routing" if player_voyage_open_sea_01 > 0.34 else " · mostly coastal lanes"
		)
		var head: String = "At sea toward %s (%d d left%s)" % [
			get_port_name(voyage_dest_id),
			voyage_days_remaining,
			sea_note,
		]
		if str(player_voyage_role) == _VOYAGE_ROLE_ESCORT and not player_escort_contract.is_empty():
			var dct: String = str(player_escort_contract.get("dest", ""))
			if _port_names.has(dct):
				head += " · escort to %s" % get_port_name(dct)
			else:
				head += " · escort duty"
		return head
	return "Docked at %s" % get_port_name(player_port_id)


## Read-only: leg summary while `is_at_sea()` (storm odds match `_tick_player_storm_if_at_sea`).
func get_player_voyage_intel_block() -> String:
	if not is_at_sea():
		return ""
	var parts: PackedStringArray = []
	var role_s: String = str(player_voyage_role)
	if role_s == _VOYAGE_ROLE_ESCORT and not player_escort_contract.is_empty():
		var pay: int = clampi(int(player_escort_contract.get("pay_coins", 0)), 0, _MAX_PURSE_COINS)
		var dest_e: String = str(player_escort_contract.get("dest", ""))
		var dest_nm: String = (
			get_port_name(dest_e) if _port_names.has(dest_e) else "agreed port"
		)
		parts.append("Escort contract — %dc on safe arrival at %s." % [pay, dest_nm])
	else:
		parts.append("Merchant passage — storms stress rigging; pirates hunt open water.")
	var op: float = clampf(player_voyage_open_sea_01, 0.0, 1.0)
	var route: String = (
		"open-water routing (higher wave odds)" if op > 0.34 else "mostly coastal lanes"
	)
	parts.append(
		"Toward %s · %d d left · %s"
		% [get_port_name(voyage_dest_id), voyage_days_remaining, route]
	)
	var p_storm: float = _player_daily_storm_probability()
	parts.append(
		"Rough daily gale chance: ~%.1f%% (%s seas)"
		% [p_storm * 100.0, get_calendar_season_name()]
	)
	if player_voyage_weather_bless_p_sub > 0.00005:
		var p_base: float = _player_daily_storm_probability_without_weather_bless()
		parts.append(
			"Temple vow at your last departure — clerks would put the raw gauge nearer ~%.1f%% without that small turn of luck."
			% (p_base * 100.0)
		)
	if get_player_fleet_ships() > 1:
		parts.append(
			"If a gale hits, multi-ship lines risk losing one hull (~%d%%)."
			% [int(round(_VOYAGE_STORM_HULL_LOSS_CHANCE * 100.0))]
		)
	return "\n".join(parts)


func _calendar_doy_1based(calendar_day: int) -> int:
	var d: int = maxi(1, calendar_day)
	return ((d - 1) % _CALENDAR_YEAR_LEN) + 1


func get_calendar_day_of_year() -> int:
	return _calendar_doy_1based(current_day)


func get_calendar_year_index() -> int:
	return (maxi(1, current_day) - 1) / _CALENDAR_YEAR_LEN + 1


func get_calendar_season_name() -> String:
	var doy: int = get_calendar_day_of_year()
	if doy >= _SEASON_WINTER_START_DOY:
		return "Winter"
	if doy <= 90:
		return "Spring"
	if doy <= _SEASON_SUMMER_END_DOY:
		return "Summer"
	return "Autumn"


func get_calendar_header_line() -> String:
	var harvest_note: String = (
		" · harvest" if _is_harvest_doy(get_calendar_day_of_year()) else ""
	)
	return "Day %d · %s Y%d%s" % [current_day, get_calendar_season_name(), get_calendar_year_index(), harvest_note]


func _is_harvest_doy(doy: int) -> bool:
	return doy >= _HARVEST_START_DOY and doy <= _HARVEST_END_DOY


func _season_is_summer_for_war(doy: int) -> bool:
	return doy >= _SEASON_SUMMER_START_DOY and doy <= _SEASON_SUMMER_END_DOY


func _crop_daily_scale_for_doy(doy: int) -> float:
	return _CROP_HARVEST_DAILY_SCALE if _is_harvest_doy(doy) else _CROP_OFFSEASON_SCALE


func _season_storm_probability_scale_for_doy(doy: int) -> float:
	if doy >= _SEASON_WINTER_START_DOY:
		return _STORM_SEASON_WINTER_MULT
	if doy >= _HARVEST_START_DOY:
		return _STORM_SEASON_AUTUMN_MULT
	return 1.0


func _season_fish_mult_for_doy(doy: int) -> float:
	if doy >= _SEASON_WINTER_START_DOY:
		return _FISH_SEASON_WINTER_MULT
	return 1.0


func _crop_seasonal_moisture_target_01(doy: int, port_id: String) -> float:
	var phase: float = float(_npc_str_mix(port_id, 4001) % 1000) / 1000.0
	var y: float = float(_CALENDAR_YEAR_LEN)
	var ang: float = TAU * (float(doy) + 60.0 - phase * 12.0) / y
	var wet: float = 0.5 + 0.5 * cos(ang)
	return clampf(lerpf(0.28, 0.80, wet) + (phase - 0.5) * 0.10, 0.0, 1.0)


## Ground-truth crop stress from standing crop (growth). Metrics and food-unrest use this.
func _crop_grain_stress_gt_01_for_port(port_id: String) -> float:
	if not _world_crop_agro_model:
		return 0.0
	var ps := str(port_id)
	var g: float = clampf(float(_port_crop_growth_01.get(ps, 0.5)), 0.0, 1.0)
	return clampf(1.0 - g, 0.0, 1.0)


## Same as `_crop_grain_stress_gt_01_for_port` (saved name for metrics / unrest).
func _crop_grain_stress_01_for_port(port_id: String) -> float:
	return _crop_grain_stress_gt_01_for_port(port_id)


func _crop_grain_stress_01_market_for_port(port_id: String) -> float:
	if not _world_crop_agro_model:
		return 0.0
	var ps := str(port_id)
	var gt_f: float = _crop_grain_stress_gt_01_for_port(ps)
	var local_b: float = clampf(float(_port_local_crop_belief_01.get(ps, gt_f)), 0.0, 1.0)
	var blended: float = local_b
	var arr0: Variant = _port_inbound_crop_reports.get(ps, null)
	if typeof(arr0) == TYPE_ARRAY:
		var arr: Array = arr0 as Array
		if not arr.is_empty():
			var sm: float = 0.0
			for v in arr:
				sm += clampf(float(v), 0.0, 1.0)
			var avg: float = sm / float(arr.size())
			var w: float = _CROP_INFO_MARKET_LOCAL_WEIGHT
			blended = clampf(w * local_b + (1.0 - w) * avg, 0.0, 1.0)
	var rumor_d: float = clampf(float(_port_crop_rumor_public_delta.get(ps, 0.0)), -_CROP_RUMOR_DELTA_ABS_MAX, _CROP_RUMOR_DELTA_ABS_MAX)
	return clampf(blended + rumor_d, 0.0, 1.0)


func _port_crop_inbound_report_count(port_id: String) -> int:
	var arr0: Variant = _port_inbound_crop_reports.get(str(port_id), null)
	if typeof(arr0) != TYPE_ARRAY:
		return 0
	return (arr0 as Array).size()


func _append_port_crop_arrival_report(dest: String, report_val: float) -> void:
	var ps := str(dest)
	if not _port_names.has(ps):
		return
	if not _port_inbound_crop_reports.has(ps):
		_port_inbound_crop_reports[ps] = [] as Array
	var arr: Array = _port_inbound_crop_reports[ps] as Array
	arr.append(clampf(report_val, 0.0, 1.0))
	while arr.size() > _CROP_INFO_MARKET_REPORT_MAX:
		arr.remove_at(0)


func _refresh_port_local_crop_beliefs() -> void:
	if not _world_crop_agro_model:
		return
	for pid in _port_names.keys():
		var ps := str(pid)
		var gt: float = _crop_grain_stress_gt_01_for_port(ps)
		var noise: float = _rng.randf_range(-_CROP_INFO_LOCAL_NOISE_MAX, _CROP_INFO_LOCAL_NOISE_MAX)
		_port_local_crop_belief_01[ps] = clampf(gt + noise, 0.0, 1.0)
	for item in _npc_agents:
		if typeof(item) != TYPE_DICTIONARY:
			continue
		var ag: Dictionary = item as Dictionary
		if str(ag.get("voyage_role", _VOYAGE_ROLE_MERCHANT)) != _VOYAGE_ROLE_MERCHANT:
			continue
		if int(ag.get("voyage_days_remaining", 0)) != 0:
			continue
		var dp: String = str(ag.get("docked_port", ""))
		var hp: String = str(ag.get("home_port", ""))
		if dp.is_empty() or not _port_names.has(dp):
			continue
		if hp == dp:
			var lb0: float = clampf(float(_port_local_crop_belief_01.get(dp, _crop_grain_stress_gt_01_for_port(dp))), 0.0, 1.0)
			ag["crop_stress_belief_01"] = clampf(
				lb0 + _rng.randf_range(-_CROP_INFO_LOCAL_NOISE_MAX * 0.25, _CROP_INFO_LOCAL_NOISE_MAX * 0.25),
				0.0,
				1.0
			)


func _npc_apply_crop_information_on_arrival(ag: Dictionary, dest: String) -> void:
	if not _world_crop_agro_model:
		return
	if str(ag.get("voyage_role", _VOYAGE_ROLE_MERCHANT)) != _VOYAGE_ROLE_MERCHANT:
		return
	var d: String = str(dest)
	if not _port_names.has(d):
		return
	var origin: String = str(ag.get("voyage_origin_port_id", ""))
	if origin.is_empty() or not _port_names.has(origin):
		origin = str(ag.get("home_port", ""))
	if origin.is_empty() or not _port_names.has(origin):
		ag["voyage_origin_port_id"] = ""
		return
	var gt_o: float = _crop_grain_stress_gt_01_for_port(origin)
	var nz: float = _rng.randf_range(-_CROP_INFO_REPORT_NOISE_MAX, _CROP_INFO_REPORT_NOISE_MAX)
	var rep: float = clampf(gt_o + nz, 0.0, 1.0)
	if not _npc_convoy_is_follower(ag):
		_append_port_crop_arrival_report(d, rep)
	var home: String = str(ag.get("home_port", ""))
	if home != d:
		ag["crop_stress_belief_01"] = rep
	else:
		var loc_b: float = clampf(float(_port_local_crop_belief_01.get(d, gt_o)), 0.0, 1.0)
		ag["crop_stress_belief_01"] = clampf(
			loc_b + _rng.randf_range(-_CROP_INFO_LOCAL_NOISE_MAX * 0.35, _CROP_INFO_LOCAL_NOISE_MAX * 0.35),
			0.0,
			1.0
		)
	ag["voyage_origin_port_id"] = ""
	if not _npc_convoy_is_follower(ag) and _rng.randf() < _CROP_RUMOR_HIGH_TRUST_DAMP_P:
		if _port_crop_rumor_public_delta.has(d):
			var rd0: float = float(_port_crop_rumor_public_delta[d])
			rd0 *= _CROP_RUMOR_HIGH_TRUST_DAMP_MULT
			if absf(rd0) < 0.0035:
				_port_crop_rumor_public_delta.erase(d)
			else:
				_port_crop_rumor_public_delta[d] = clampf(rd0, -_CROP_RUMOR_DELTA_ABS_MAX, _CROP_RUMOR_DELTA_ABS_MAX)


func _crop_grain_yield_mult_for_port(port_id: String) -> float:
	if not _world_crop_agro_model:
		return 1.0
	var g: float = clampf(float(_port_crop_growth_01.get(str(port_id), 0.5)), 0.0, 1.0)
	return lerpf(_CROP_GRAIN_YIELD_MULT_MIN, _CROP_GRAIN_YIELD_MULT_MAX, g)


func _crop_grain_buy_price_stress_mult(port_id: String) -> float:
	if not _world_crop_agro_model:
		return 1.0
	var st: float = _crop_grain_stress_01_market_for_port(port_id)
	return 1.0 + clampf(st - _CROP_STRESS_PRICE_BUY_THRESHOLD, 0.0, 1.0) * _CROP_STRESS_PRICE_BUY_EXTRA


func _crop_grain_sell_price_stress_mult(port_id: String) -> float:
	if not _world_crop_agro_model:
		return 1.0
	var st: float = _crop_grain_stress_01_market_for_port(port_id)
	return 1.0 - clampf(st - _CROP_STRESS_PRICE_SELL_THRESHOLD, 0.0, 1.0) * _CROP_STRESS_PRICE_SELL_DISC


func _crop_phase2_neighbor_max_grain(port_id: String) -> int:
	var ps := str(port_id)
	var mx: int = 0
	var nr: Variant = _port_neighbors.get(ps, null)
	if typeof(nr) != TYPE_ARRAY:
		return 0
	for x in nr as Array:
		var nb: String = str(x)
		if not _port_names.has(nb):
			continue
		mx = maxi(mx, _port_stock_qty(nb, "grain"))
	return mx


func _crop_phase2_stress_major_gate(port_id: String) -> bool:
	if not _world_crop_agro_model:
		return false
	var ps := str(port_id)
	if not _port_names.has(ps):
		return false
	if not is_port_at_war(ps):
		return false
	var m01: float = clampf(float(_port_crop_moisture_01.get(ps, 0.5)), 0.0, 1.0)
	if m01 > _CROP_PHASE2_DROUGHT_MOISTURE_MAX:
		return false
	if _crop_phase2_neighbor_max_grain(ps) > _CROP_PHASE2_NEIGHBOR_GRAIN_ISOLATED_MAX:
		return false
	return true


func _crop_phase2_grain_trade_bias_add(port_id: String) -> float:
	if not _world_crop_agro_model or not _goods.has("grain"):
		return 0.0
	var st: float = _crop_grain_stress_01_market_for_port(port_id)
	if st < _CROP_PHASE2_BIAS_STRESS_LO:
		return 0.0
	var span: float = maxf(0.0001, _CROP_PHASE2_BIAS_STRESS_HI - _CROP_PHASE2_BIAS_STRESS_LO)
	var t: float = clampf((st - _CROP_PHASE2_BIAS_STRESS_LO) / span, 0.0, 1.0)
	var add: float = t * _CROP_PHASE2_BIAS_MAX_ADD
	if _crop_phase2_stress_major_gate(port_id) and st >= _CROP_PHASE2_BIAS_MAJOR_STRESS_MIN:
		add += _CROP_PHASE2_BIAS_MAJOR_EXTRA
	return clampf(add, 0.0, _TRADE_PRICE_BIAS_CLAMP)


func _crop_phase2_food_unrest_addon(port_id: String) -> int:
	if not _world_crop_agro_model:
		return 0
	var st: float = _crop_grain_stress_gt_01_for_port(port_id)
	var n: int = 0
	if st >= _CROP_PHASE2_UNREST_STRESS_HIGH:
		n = _CROP_PHASE2_UNREST_ADD_HIGH
	elif st >= _CROP_PHASE2_UNREST_STRESS_MID:
		n = _CROP_PHASE2_UNREST_ADD_MID
	if _crop_phase2_stress_major_gate(port_id) and st >= _CROP_PHASE2_UNREST_MAJOR_STRESS_MIN:
		n += _CROP_PHASE2_UNREST_ADD_MAJOR
	return mini(_CROP_PHASE2_UNREST_DAILY_CAP, n)


func _crop_phase2_npc_hoard_weight_01(port_id: String) -> float:
	if not _world_crop_agro_model:
		return 0.0
	var st: float = _crop_grain_stress_01_market_for_port(port_id)
	var hw: float = clampf((st - _CROP_PHASE2_HOARD_STRESS_LO) / 0.42, 0.0, 1.0)
	if _crop_phase2_stress_major_gate(port_id):
		hw = minf(1.0, hw + _CROP_PHASE2_HOARD_MAJOR_BOOST)
	return clampf(hw * 0.88, 0.0, 1.0)


func _ensure_port_crop_agro_all_ports() -> void:
	var doy: int = _calendar_doy_1based(current_day)
	for pid in _port_names.keys():
		var ps := str(pid)
		if _port_crop_moisture_01.has(ps):
			continue
		var t: float = _crop_seasonal_moisture_target_01(doy, ps)
		_port_crop_moisture_01[ps] = t
		_port_crop_growth_01[ps] = t


func _init_port_crop_agro_state() -> void:
	_port_crop_moisture_01.clear()
	_port_crop_growth_01.clear()
	_ensure_port_crop_agro_all_ports()
	_init_port_crop_information_state()


func _init_port_crop_information_state() -> void:
	_port_local_crop_belief_01.clear()
	_port_inbound_crop_reports.clear()
	_port_crop_rumor_public_delta.clear()


func _decay_crop_rumor_public_deltas() -> void:
	if not _world_crop_agro_model:
		return
	var doy: int = get_calendar_day_of_year()
	var harv: bool = _is_harvest_doy(doy)
	var rm: Array[String] = []
	for pk in _port_crop_rumor_public_delta.keys():
		var ps: String = str(pk)
		if not _port_names.has(ps):
			rm.append(ps)
			continue
		var d: float = float(_port_crop_rumor_public_delta[ps])
		d *= _CROP_RUMOR_DAILY_DECAY
		if harv:
			d *= _CROP_RUMOR_HARVEST_EXTRA_DECAY
		if absf(d) < 0.0035:
			rm.append(ps)
		else:
			_port_crop_rumor_public_delta[ps] = clampf(d, -_CROP_RUMOR_DELTA_ABS_MAX, _CROP_RUMOR_DELTA_ABS_MAX)
	for rk in rm:
		_port_crop_rumor_public_delta.erase(rk)


func _crop_rumor_sicily_listener_ids() -> PackedStringArray:
	return PackedStringArray(
		["ostia", "neapolis", "rhegium", "carthage", "hippo", "tingis", "messana", "panormus"]
	)


func _maybe_roll_sicilian_crop_rumor_event() -> void:
	if not _world_crop_agro_model:
		return
	if _rng.randf() >= _CROP_RUMOR_SICILY_EVENT_DAILY_P:
		return
	var bumper: bool = _rng.randf() < 0.57
	var mag: float = (
		_rng.randf_range(_CROP_RUMOR_SICILY_BUMPER_MAG_MIN, _CROP_RUMOR_SICILY_BUMPER_MAG_MAX)
		if bumper
		else _rng.randf_range(_CROP_RUMOR_SICILY_FAIL_MAG_MIN, _CROP_RUMOR_SICILY_FAIL_MAG_MAX)
	)
	var dd: float = -mag if bumper else mag
	var gt_sic: float = 0.5
	var corr: float = 0.0
	if _port_names.has("messana") and _port_names.has("panormus"):
		gt_sic = 0.5 * (_crop_grain_stress_gt_01_for_port("messana") + _crop_grain_stress_gt_01_for_port("panormus"))
		corr = _CROP_RUMOR_GT_CORREL * (gt_sic - 0.5) * (1.0 if bumper else -1.0)
	elif _port_names.has("messana"):
		gt_sic = _crop_grain_stress_gt_01_for_port("messana")
		corr = _CROP_RUMOR_GT_CORREL * (gt_sic - 0.5) * (1.0 if bumper else -1.0)
	var ids: PackedStringArray = _crop_rumor_sicily_listener_ids()
	for i in range(ids.size()):
		var ps: String = str(ids[i])
		if not _port_names.has(ps):
			continue
		var cur: float = float(_port_crop_rumor_public_delta.get(ps, 0.0))
		_port_crop_rumor_public_delta[ps] = clampf(cur + dd + corr, -_CROP_RUMOR_DELTA_ABS_MAX, _CROP_RUMOR_DELTA_ABS_MAX)
	var pp: String = str(player_port_id)
	var line: String = ""
	if is_at_sea():
		if bumper:
			line = (
				"Fleet grapevine: Sicilian harvest hearsay—coastal books may ease grain asks before your next landfall."
			)
		else:
			line = (
				"Fleet grapevine: dark Sicilian crop chatter—expect grain dearer at the next quay, true or not."
			)
	elif pp == "ostia":
		if bumper:
			line = (
				"Dockside grain talk (Ostia): Sicilian harvest rumors already ease what buyers ask—"
				+ "no granary shortage here yet, only whispers from the wheat islands."
			)
		else:
			line = (
				"Dockside grain talk (Ostia): grim Sicilian crop tales nudge grain prices dearer—"
				+ "city bins are unchanged, but the rumor has the quay counting sacks twice."
			)
	else:
		var pn: String = get_port_name(pp) if _port_names.has(pp) else pp
		if bumper:
			line = "%s: Sicilian harvest gossip eases grain mood before any tally reaches this port." % pn
		else:
			line = "%s: anxious Sicilian crop chatter lifts grain mood—traders hedge on rumor alone." % pn
	_last_crop_rumor_ui_line = line
	crop_rumor_report.emit(line)
	market_changed.emit()


func _tick_crop_rumor_events_phase4() -> void:
	_decay_crop_rumor_public_deltas()
	_maybe_roll_sicilian_crop_rumor_event()


func _serialize_port_crop_agro() -> Dictionary:
	var out: Dictionary = {}
	for pid in _port_names.keys():
		var ps := str(pid)
		out[ps] = {
			"m": clampf(float(_port_crop_moisture_01.get(ps, 0.5)), 0.0, 1.0),
			"g": clampf(float(_port_crop_growth_01.get(ps, 0.5)), 0.0, 1.0),
		}
	return out


func _serialize_port_crop_inbound_reports() -> Dictionary:
	var out: Dictionary = {}
	for pk in _port_inbound_crop_reports.keys():
		var ps: String = str(pk)
		var arr0: Variant = _port_inbound_crop_reports.get(ps, null)
		if typeof(arr0) != TYPE_ARRAY:
			continue
		var fd: Array = []
		for v in arr0 as Array:
			fd.append(clampf(float(v), 0.0, 1.0))
		out[ps] = fd
	return out


func _deserialize_port_crop_inbound_reports(data: Variant) -> void:
	_port_inbound_crop_reports.clear()
	if typeof(data) != TYPE_DICTIONARY:
		return
	for pk in (data as Dictionary).keys():
		var pid: String = str(pk)
		if not _port_names.has(pid):
			continue
		var arr0: Variant = (data as Dictionary)[pk]
		if typeof(arr0) != TYPE_ARRAY:
			continue
		var arr: Array = []
		for v in arr0 as Array:
			if arr.size() >= _CROP_INFO_MARKET_REPORT_MAX:
				arr.remove_at(0)
			arr.append(clampf(float(v), 0.0, 1.0))
		_port_inbound_crop_reports[pid] = arr


func _deserialize_port_crop_agro(data: Dictionary) -> void:
	_port_crop_moisture_01.clear()
	_port_crop_growth_01.clear()
	for pk in data.keys():
		var ps := str(pk)
		if not _port_names.has(ps):
			continue
		var row: Variant = data[pk]
		if typeof(row) != TYPE_DICTIONARY:
			continue
		var rd: Dictionary = row as Dictionary
		_port_crop_moisture_01[ps] = clampf(float(rd.get("m", 0.5)), 0.0, 1.0)
		_port_crop_growth_01[ps] = clampf(float(rd.get("g", 0.5)), 0.0, 1.0)
	_ensure_port_crop_agro_all_ports()


func _tick_port_crop_agro() -> void:
	if not _world_crop_agro_model:
		return
	_ensure_port_crop_agro_all_ports()
	var doy: int = _calendar_doy_1based(current_day)
	for pid in _port_names.keys():
		var ps := str(pid)
		var tgt: float = _crop_seasonal_moisture_target_01(doy, ps)
		var m: float = clampf(float(_port_crop_moisture_01.get(ps, 0.5)), 0.0, 1.0)
		m = lerpf(m, tgt, _CROP_MOISTURE_ADJUST_RATE)
		_port_crop_moisture_01[ps] = m
		var g: float = clampf(float(_port_crop_growth_01.get(ps, 0.5)), 0.0, 1.0)
		g = lerpf(g, m, _CROP_GROWTH_LAG_RATE)
		_port_crop_growth_01[ps] = g


func get_money() -> int:
	return player_money


func get_player_fleet_ships() -> int:
	return clampi(player_fleet_ships, 1, _FLEET_MAX_SHIPS)


func get_player_fleet_max_ships() -> int:
	return _FLEET_MAX_SHIPS


func get_player_cargo_capacity() -> int:
	var row: Dictionary = _player_ship_row()
	var per: int = clampi(int(row.get("cargo_per_hull", _FLEET_CARGO_PER_SHIP)), 1, 120)
	return per * get_player_fleet_ships()


func get_player_cargo_used() -> int:
	var row: Dictionary = _player_ship_row()
	var geff: float = maxf(0.5, float(row.get("grain_hold_efficiency", 1.0)))
	var t: int = 0
	for k in player_cargo.keys():
		var gid := str(k)
		var q: int = maxi(0, int(player_cargo[k]))
		if gid == "grain":
			t += int(ceil(float(q) / geff))
		else:
			t += q
	return t


## Yard hire (labor only); timber/textiles/metal come from the dock’s port stock.
func get_fleet_ship_purchase_cost() -> int:
	return int(_player_fleet_build_ints().get("labor", _FLEET_NEW_SHIP_LABOR_COINS))


func get_fleet_new_ship_nominal_coins() -> int:
	return _FLEET_SHIP_NOMINAL_COINS


func get_fleet_new_ship_build_days() -> int:
	return int(_player_fleet_build_ints().get("days", _FLEET_NEW_SHIP_BUILD_DAYS))


func get_player_fleet_shipyard_days_remaining() -> int:
	return maxi(0, player_fleet_shipyard_days_remaining)


func _fleet_new_build_goods_present() -> bool:
	return _goods.has("timber") and _goods.has("textiles") and _goods.has("metal")


func player_port_has_fleet_build_materials() -> bool:
	if not _fleet_new_build_goods_present():
		return false
	if is_at_sea():
		return false
	var ps := player_port_id
	if ps.is_empty() or not _port_names.has(ps):
		return false
	var b: Dictionary = _player_fleet_build_ints()
	if _port_stock_qty(ps, "timber") < int(b.get("timber", _FLEET_NEW_SHIP_TIMBER)):
		return false
	if _port_stock_qty(ps, "textiles") < int(b.get("textiles", _FLEET_NEW_SHIP_TEXTILES)):
		return false
	if _port_stock_qty(ps, "metal") < int(b.get("metal", _FLEET_NEW_SHIP_METAL)):
		return false
	return true


func player_can_order_new_fleet_ship() -> bool:
	if is_at_sea() or player_fleet_ships >= _FLEET_MAX_SHIPS:
		return false
	if player_fleet_shipyard_days_remaining > 0:
		return false
	var labor_need: int = int(_player_fleet_build_ints().get("labor", _FLEET_NEW_SHIP_LABOR_COINS))
	if player_money < labor_need:
		return false
	return player_port_has_fleet_build_materials()


## Docked only. Queues a new hull at this port: labor coins now, port timber/textiles/metal, ~3 months until delivery.
func try_buy_fleet_ship() -> bool:
	if is_at_sea():
		return false
	if player_fleet_ships >= _FLEET_MAX_SHIPS:
		return false
	if player_fleet_shipyard_days_remaining > 0:
		return false
	if not _fleet_new_build_goods_present():
		return false
	var b: Dictionary = _player_fleet_build_ints()
	var labor_need: int = int(b.get("labor", _FLEET_NEW_SHIP_LABOR_COINS))
	var timb: int = int(b.get("timber", _FLEET_NEW_SHIP_TIMBER))
	var tex: int = int(b.get("textiles", _FLEET_NEW_SHIP_TEXTILES))
	var met: int = int(b.get("metal", _FLEET_NEW_SHIP_METAL))
	var dayb: int = int(b.get("days", _FLEET_NEW_SHIP_BUILD_DAYS))
	if player_money < labor_need:
		return false
	var ps := player_port_id
	if ps.is_empty() or not _port_names.has(ps):
		return false
	if _port_stock_qty(ps, "timber") < timb:
		return false
	if _port_stock_qty(ps, "textiles") < tex:
		return false
	if _port_stock_qty(ps, "metal") < met:
		return false
	player_money = clampi(player_money - labor_need, 0, _MAX_PURSE_COINS)
	_adjust_port_stock(ps, "timber", -timb)
	_adjust_port_stock(ps, "textiles", -tex)
	_adjust_port_stock(ps, "metal", -met)
	player_fleet_shipyard_port_id = ps
	player_fleet_shipyard_days_remaining = dayb
	money_changed.emit()
	market_changed.emit()
	return true


func _norm_ship_condition_01(cond: int) -> float:
	var span: int = maxi(1, _SHIP_CONDITION_MAX - _SHIP_CONDITION_MIN)
	return clampf((float(cond) - float(_SHIP_CONDITION_MIN)) / float(span), 0.0, 1.0)


func _used_hull_fire_sale_payout(cond: int) -> int:
	var u: float = _norm_ship_condition_01(cond)
	var frac: float = lerpf(_USED_HULL_PAYOUT_FRAC_LOW, _USED_HULL_PAYOUT_FRAC_HIGH, u)
	var nom: int = _FLEET_SHIP_NOMINAL_COINS
	var p: int = int(round(float(nom) * frac))
	return clampi(p, _USED_HULL_MIN_PAYOUT, nom - 12)


func _used_hull_listing_ask_from_payout(payout: int) -> int:
	var ask: int = maxi(payout + 6, int(round(float(payout) * _USED_HULL_ASK_MARKUP)))
	var nom2: int = _FLEET_SHIP_NOMINAL_COINS
	return mini(nom2 - 8, ask)


func _merge_hull_condition_on_buy(old_cond: int, old_ships: int, added_cond: int) -> int:
	var os: int = maxi(1, old_ships)
	return clampi(
		int(round((float(old_cond) * float(os) + float(added_cond)) / float(os + 1))),
		_SHIP_CONDITION_MIN,
		_SHIP_CONDITION_MAX,
	)


func _ensure_used_hull_listings_for_all_ports() -> void:
	for pid in _port_names.keys():
		var ps := str(pid)
		if not _port_used_hull_listings.has(ps):
			_port_used_hull_listings[ps] = []


func _used_hull_listings_array(port_id: String) -> Array:
	var ps := str(port_id)
	if not _port_names.has(ps):
		return []
	if not _port_used_hull_listings.has(ps):
		_port_used_hull_listings[ps] = []
	var raw: Variant = _port_used_hull_listings[ps]
	return raw as Array if typeof(raw) == TYPE_ARRAY else []


func _append_used_hull_listing(port_id: String, condition: int, ask: int) -> void:
	var ps := str(port_id)
	if not _port_names.has(ps):
		return
	var arr: Array = _used_hull_listings_array(ps)
	while arr.size() >= _USED_HULL_MAX_PER_PORT:
		arr.pop_front()
	var lid: int = _next_used_hull_listing_id
	_next_used_hull_listing_id += 1
	arr.append({"id": lid, "ask": maxi(1, ask), "condition": clampi(condition, _SHIP_CONDITION_MIN, _SHIP_CONDITION_MAX)})
	_port_used_hull_listings[ps] = arr


## Bankruptcy replacement only: take cheapest local slip listing into single-hull `ship_condition` (no coin); clears one listing.
func _rookie_try_charter_cheapest_used_hull_from_slip(agent: Dictionary, home_port: String) -> void:
	var hp: String = str(home_port)
	if not _port_names.has(hp):
		return
	if _rng.randf() > _ROOKIE_BANKRUPTCY_USED_HULL_CHANCE:
		return
	var arr: Array = _used_hull_listings_array(hp)
	if arr.is_empty():
		return
	var best_i: int = -1
	var best_ask: int = 999999999
	var best_cond: int = _SHIP_CONDITION_MAX
	var idx: int = 0
	while idx < arr.size():
		var c0: Variant = arr[idx]
		if typeof(c0) != TYPE_DICTIONARY:
			idx += 1
			continue
		var row: Dictionary = c0 as Dictionary
		var ak: int = int(row.get("ask", 999999999))
		if ak < best_ask:
			best_ask = ak
			best_i = idx
			best_cond = clampi(int(row.get("condition", _SHIP_CONDITION_MAX)), _SHIP_CONDITION_MIN, _SHIP_CONDITION_MAX)
		idx += 1
	if best_i < 0 or best_ask >= 999999000:
		return
	arr.remove_at(best_i)
	_port_used_hull_listings[hp] = arr
	agent["ship_condition"] = best_cond
	_bump_port_wealth(hp, -maxi(1, best_ask / _ROOKIE_USED_HULL_CHARTER_WEALTH_DIV))


func get_used_hull_listing_count_at_port(port_id: String) -> int:
	return _used_hull_listings_array(str(port_id)).size()


## Docked only. Empty at sea. Short line for market header (cheapest ask among slip listings).
func get_used_hull_slip_summary_line() -> String:
	if is_at_sea():
		return ""
	var arr: Array = _used_hull_listings_array(player_port_id)
	if arr.is_empty():
		return ""
	var best: int = 999999999
	for cell in arr:
		if typeof(cell) != TYPE_DICTIONARY:
			continue
		best = mini(best, int((cell as Dictionary).get("ask", 999999999)))
	if best >= 999999000:
		return "Used slips: %d hull(s) for sale (ask varies)." % arr.size()
	return "Used slips: %d hull(s); cheapest ask ~%dc (vs ~%dc new hull value)." % [arr.size(), best, _FLEET_SHIP_NOMINAL_COINS]


## Docked only. Each entry: { "id", "ask", "condition" }.
func get_used_hull_listings_at_player_port() -> Array:
	if is_at_sea():
		return []
	var out: Array = []
	for cell in _used_hull_listings_array(player_port_id):
		if typeof(cell) != TYPE_DICTIONARY:
			continue
		out.append((cell as Dictionary).duplicate(true))
	return out


## Docked, fleet > 1. Scraps one hull for fire-sale coin; a used listing appears on the local slip for others to buy.
func player_can_fire_sale_fleet_ship() -> bool:
	if is_at_sea() or player_fleet_ships <= 1:
		return false
	var per: int = clampi(int(_player_ship_row().get("cargo_per_hull", _FLEET_CARGO_PER_SHIP)), 1, 120)
	var new_cap: int = per * (player_fleet_ships - 1)
	return get_player_cargo_used() <= new_cap


func try_player_fire_sale_fleet_ship() -> bool:
	if not player_can_fire_sale_fleet_ship():
		return false
	var cond: int = clampi(player_ship_condition, _SHIP_CONDITION_MIN, _SHIP_CONDITION_MAX)
	var payout: int = _used_hull_fire_sale_payout(cond)
	var ask: int = _used_hull_listing_ask_from_payout(payout)
	player_fleet_ships = maxi(1, player_fleet_ships - 1)
	player_money = clampi(player_money + payout, 0, _MAX_PURSE_COINS)
	_append_used_hull_listing(player_port_id, cond, ask)
	money_changed.emit()
	market_changed.emit()
	return true


func _cancel_player_fleet_shipyard_order() -> void:
	if player_fleet_shipyard_days_remaining <= 0:
		return
	var ypid: String = str(player_fleet_shipyard_port_id)
	var b: Dictionary = _player_fleet_build_ints()
	if not ypid.is_empty() and _port_names.has(ypid) and _fleet_new_build_goods_present():
		_adjust_port_stock(ypid, "timber", int(b.get("timber", _FLEET_NEW_SHIP_TIMBER)))
		_adjust_port_stock(ypid, "textiles", int(b.get("textiles", _FLEET_NEW_SHIP_TEXTILES)))
		_adjust_port_stock(ypid, "metal", int(b.get("metal", _FLEET_NEW_SHIP_METAL)))
	player_money = clampi(player_money + int(b.get("labor", _FLEET_NEW_SHIP_LABOR_COINS)), 0, _MAX_PURSE_COINS)
	player_fleet_shipyard_days_remaining = 0
	player_fleet_shipyard_port_id = ""
	money_changed.emit()
	market_changed.emit()


func _tick_player_fleet_shipyard_order() -> void:
	if player_fleet_shipyard_days_remaining <= 0:
		return
	player_fleet_shipyard_days_remaining -= 1
	if player_fleet_shipyard_days_remaining > 0:
		return
	player_fleet_shipyard_port_id = ""
	var ships0: int = clampi(player_fleet_ships, 1, _FLEET_MAX_SHIPS)
	if ships0 >= _FLEET_MAX_SHIPS:
		market_changed.emit()
		return
	player_fleet_ships = mini(_FLEET_MAX_SHIPS, ships0 + 1)
	cargo_changed.emit()
	market_changed.emit()


## Docked only. Buys the cheapest listed used hull at this port (same as NPC dock shoppers).
func try_player_buy_used_fleet_ship() -> bool:
	if is_at_sea():
		return false
	if player_fleet_ships >= _FLEET_MAX_SHIPS:
		return false
	var ps := player_port_id
	var arr: Array = _used_hull_listings_array(ps)
	if arr.is_empty():
		return false
	var best_i: int = -1
	var best_ask: int = 999999999
	var best_cond: int = _SHIP_CONDITION_MAX
	var idx: int = 0
	while idx < arr.size():
		var c0: Variant = arr[idx]
		if typeof(c0) != TYPE_DICTIONARY:
			idx += 1
			continue
		var row: Dictionary = c0 as Dictionary
		var ak: int = int(row.get("ask", 999999999))
		if ak < best_ask:
			best_ask = ak
			best_i = idx
			best_cond = clampi(int(row.get("condition", _SHIP_CONDITION_MAX)), _SHIP_CONDITION_MIN, _SHIP_CONDITION_MAX)
		idx += 1
	if best_i < 0 or best_ask >= 999999000 or player_money < best_ask:
		return false
	_cancel_player_fleet_shipyard_order()
	player_money = clampi(player_money - best_ask, 0, _MAX_PURSE_COINS)
	_bump_port_wealth(ps, maxi(1, best_ask / 16))
	arr.remove_at(best_i)
	_port_used_hull_listings[ps] = arr
	var ships0: int = clampi(player_fleet_ships, 1, _FLEET_MAX_SHIPS)
	player_fleet_ships = mini(_FLEET_MAX_SHIPS, ships0 + 1)
	player_ship_condition = _merge_hull_condition_on_buy(player_ship_condition, ships0, best_cond)
	money_changed.emit()
	market_changed.emit()
	return true


## Drops one ship if fleet > 1 and hold fits in the smaller convoy; pays fire-sale coin and appends a slip listing. Not random.
func _npc_try_fire_sale_one_hull_if_desperate(port_id: String, agent: Dictionary) -> bool:
	_ensure_npc_ship_fields(agent)
	var ships: int = clampi(int(agent.get("fleet_ships", 1)), 1, _FLEET_MAX_SHIPS)
	if ships <= 1:
		return false
	var per_h: int = clampi(int(_npc_ship_row(agent).get("cargo_per_hull", _FLEET_CARGO_PER_SHIP)), 1, 120)
	var new_cap: int = per_h * (ships - 1)
	if _npc_cargo_effective_used_units(agent) > new_cap:
		return false
	var cond: int = clampi(int(agent.get("ship_condition", _SHIP_CONDITION_MAX)), _SHIP_CONDITION_MIN, _SHIP_CONDITION_MAX)
	var payout: int = _used_hull_fire_sale_payout(cond)
	var ask: int = _used_hull_listing_ask_from_payout(payout)
	agent["fleet_ships"] = ships - 1
	agent["money"] = clampi(int(agent.get("money", 0)) + payout, 0, _MAX_PURSE_COINS)
	_append_used_hull_listing(port_id, cond, ask)
	return true


func _npc_cancel_fleet_shipyard_order(agent: Dictionary) -> void:
	var days: int = clampi(int(agent.get("fleet_shipyard_days", 0)), 0, 999)
	if days <= 0:
		return
	var ypid: String = str(agent.get("fleet_shipyard_port_id", ""))
	var nb: Dictionary = _npc_fleet_build_ints(agent)
	if not ypid.is_empty() and _port_names.has(ypid) and _fleet_new_build_goods_present():
		_adjust_port_stock(ypid, "timber", int(nb.get("timber", _FLEET_NEW_SHIP_TIMBER)))
		_adjust_port_stock(ypid, "textiles", int(nb.get("textiles", _FLEET_NEW_SHIP_TEXTILES)))
		_adjust_port_stock(ypid, "metal", int(nb.get("metal", _FLEET_NEW_SHIP_METAL)))
	agent["money"] = clampi(int(agent.get("money", 0)) + int(nb.get("labor", _FLEET_NEW_SHIP_LABOR_COINS)), 0, _MAX_PURSE_COINS)
	agent["fleet_shipyard_days"] = 0
	agent["fleet_shipyard_port_id"] = ""


func _tick_npc_fleet_shipyard_orders() -> void:
	for item in _npc_agents:
		if typeof(item) != TYPE_DICTIONARY:
			continue
		var ag: Dictionary = item as Dictionary
		var days: int = clampi(int(ag.get("fleet_shipyard_days", 0)), 0, 999)
		if days <= 0:
			continue
		days -= 1
		ag["fleet_shipyard_days"] = days
		if days > 0:
			continue
		ag["fleet_shipyard_port_id"] = ""
		_ensure_npc_ship_fields(ag)
		var sh: int = clampi(int(ag.get("fleet_ships", 1)), 1, _FLEET_MAX_SHIPS)
		if sh >= _FLEET_MAX_SHIPS:
			continue
		ag["fleet_ships"] = mini(_FLEET_MAX_SHIPS, sh + 1)


func _npc_try_buy_used_hull_if_docked(agent: Dictionary) -> void:
	if int(agent.get("voyage_days_remaining", 0)) != 0:
		return
	var pid: String = str(agent.get("docked_port", ""))
	if pid.is_empty() or not _port_names.has(pid):
		return
	_ensure_npc_ship_fields(agent)
	var ships: int = clampi(int(agent.get("fleet_ships", 1)), 1, _FLEET_MAX_SHIPS)
	if ships >= _FLEET_MAX_SHIPS:
		return
	var arr: Array = _used_hull_listings_array(pid)
	if arr.is_empty():
		return
	var best_i: int = -1
	var best_ask: int = 999999999
	var best_cond: int = _SHIP_CONDITION_MAX
	var idx: int = 0
	while idx < arr.size():
		var c0: Variant = arr[idx]
		if typeof(c0) != TYPE_DICTIONARY:
			idx += 1
			continue
		var row: Dictionary = c0 as Dictionary
		var ak: int = int(row.get("ask", 999999999))
		if ak < best_ask:
			best_ask = ak
			best_i = idx
			best_cond = clampi(int(row.get("condition", _SHIP_CONDITION_MAX)), _SHIP_CONDITION_MIN, _SHIP_CONDITION_MAX)
		idx += 1
	if best_i < 0 or best_ask >= 999999000:
		return
	var purse: int = clampi(int(agent.get("money", 0)), 0, _MAX_PURSE_COINS)
	var cushion: int = _NPC_PURSE_RESERVE + _npc_officer_due_coins(agent) * 2
	if purse < best_ask + cushion:
		return
	if _rng.randf() > 0.62:
		return
	if int(agent.get("fleet_shipyard_days", 0)) > 0:
		_npc_cancel_fleet_shipyard_order(agent)
	var purse2: int = clampi(int(agent.get("money", 0)), 0, _MAX_PURSE_COINS)
	arr.remove_at(best_i)
	_port_used_hull_listings[pid] = arr
	agent["money"] = clampi(purse2 - best_ask, 0, _MAX_PURSE_COINS)
	_bump_port_wealth(pid, maxi(1, best_ask / 16))
	agent["fleet_ships"] = mini(_FLEET_MAX_SHIPS, ships + 1)
	var cond0: int = clampi(int(agent.get("ship_condition", _SHIP_CONDITION_MAX)), _SHIP_CONDITION_MIN, _SHIP_CONDITION_MAX)
	agent["ship_condition"] = _merge_hull_condition_on_buy(cond0, ships, best_cond)


func _serialize_used_hull_listings() -> Dictionary:
	var out: Dictionary = {}
	for pid in _port_names.keys():
		var ps := str(pid)
		var arr: Array = _used_hull_listings_array(ps)
		if arr.is_empty():
			continue
		var ser: Array = []
		for cell in arr:
			if typeof(cell) != TYPE_DICTIONARY:
				continue
			var d: Dictionary = cell as Dictionary
			ser.append(
				{
					"id": int(d.get("id", 0)),
					"ask": int(d.get("ask", 0)),
					"condition": clampi(int(d.get("condition", _SHIP_CONDITION_MAX)), _SHIP_CONDITION_MIN, _SHIP_CONDITION_MAX),
				}
			)
		if not ser.is_empty():
			out[ps] = ser
	return out


func _deserialize_used_hull_listings(data: Dictionary) -> void:
	_port_used_hull_listings.clear()
	var max_id: int = 0
	for pk in data.keys():
		var ps := str(pk)
		if not _port_names.has(ps):
			continue
		var raw: Variant = data[pk]
		if typeof(raw) != TYPE_ARRAY:
			continue
		var arr: Array = []
		for item in raw as Array:
			if typeof(item) != TYPE_DICTIONARY:
				continue
			var d: Dictionary = item as Dictionary
			var lid: int = int(d.get("id", 0))
			max_id = maxi(max_id, lid)
			arr.append(
				{
					"id": lid,
					"ask": maxi(1, int(d.get("ask", 1))),
					"condition": clampi(int(d.get("condition", _SHIP_CONDITION_MAX)), _SHIP_CONDITION_MIN, _SHIP_CONDITION_MAX),
				}
			)
		_port_used_hull_listings[ps] = arr
	_next_used_hull_listing_id = maxi(_next_used_hull_listing_id, max_id + 1)


func get_player_cargo_qty(good_id: String) -> int:
	return maxi(0, int(player_cargo.get(good_id, 0)))


func get_cargo_summary() -> String:
	if player_cargo.is_empty():
		return "Hold: empty"
	var parts: PackedStringArray = []
	for good_id in player_cargo.keys():
		var qty: int = int(player_cargo[good_id])
		if qty <= 0:
			continue
		parts.append("%s x%d" % [get_good_name(str(good_id)), qty])
	if parts.is_empty():
		return "Hold: empty"
	return "Hold: " + ", ".join(parts)


func get_ship_status_line() -> String:
	var cond: int = clampi(player_ship_condition, _SHIP_CONDITION_MIN, _SHIP_CONDITION_MAX)
	var ships: int = get_player_fleet_ships()
	var capv: int = get_player_cargo_capacity()
	var used: int = get_player_cargo_used()
	var payd: int = _player_officer_due_coins()
	var wine_note: String = (
		"%d wine / %d d" % [ships, _SHIP_CREW_WINE_EVERY_N_DAYS]
		if ships > 1
		else "wine every %d d" % _SHIP_CREW_WINE_EVERY_N_DAYS
	)
	var hull_name: String = get_player_ship_display_name()
	return (
		"%s · fleet %d ships · cargo %d/%d · condition %d/%d · crew %s · dock pay ~%dc/d (officers + marine wages when berthed)"
		% [hull_name, ships, used, capv, cond, _SHIP_CONDITION_MAX, wine_note, payd]
	)


func _adjust_player_cargo_delta(good_id: String, delta: int) -> void:
	var gid := str(good_id)
	if not _goods.has(gid):
		return
	var q: int = get_player_cargo_qty(gid) + delta
	if q <= 0:
		player_cargo.erase(gid)
	else:
		player_cargo[gid] = q


func _captain_cargo_qty(cargo: Dictionary, good_id: String) -> int:
	return maxi(0, int(cargo.get(str(good_id), 0)))


func _captain_cargo_apply_delta(cargo: Dictionary, good_id: String, delta: int) -> void:
	var gid := str(good_id)
	if not _goods.has(gid):
		return
	var q: int = _captain_cargo_qty(cargo, gid) + delta
	if q <= 0:
		cargo.erase(gid)
	else:
		cargo[gid] = q


## Officer wages only (no rations/repair). Not used at sea; for docked captains call after port trade so they can sell first. Sync tools/sim_100_days.py.
func _captain_trade_fee_on_buy(cost: int) -> int:
	if cost <= 0:
		return 0
	return maxi(1, cost / _CAPTAIN_TRADE_FEE_BUY_DIV)


func _captain_trade_fee_on_sell(revenue: int) -> int:
	if revenue <= 0:
		return 0
	return maxi(1, revenue / _CAPTAIN_TRADE_FEE_SELL_DIV)


func _prune_player_toll_graft_expired() -> void:
	var to_erase: Array[String] = []
	for pk in _player_toll_graft_until.keys():
		if current_day > int(_player_toll_graft_until.get(pk, 0)):
			to_erase.append(str(pk))
	for ek in to_erase:
		_player_toll_graft_until.erase(ek)


func _prune_port_tolls_to_known_goods() -> void:
	for pid in _port_good_tolls.keys():
		var row: Variant = _port_good_tolls.get(pid, null)
		if typeof(row) != TYPE_DICTIONARY:
			_port_good_tolls.erase(pid)
			continue
		var inner: Dictionary = (row as Dictionary).duplicate(true)
		for gk in inner.keys():
			if not _goods.has(str(gk)):
				inner.erase(gk)
		_port_good_tolls[pid] = inner


func _port_toll_row(port_id: String) -> Dictionary:
	var ps := str(port_id)
	if not _port_good_tolls.has(ps):
		return {}
	var raw: Variant = _port_good_tolls.get(ps, null)
	if typeof(raw) != TYPE_DICTIONARY:
		return {}
	return raw as Dictionary


func _port_toll_per_unit(port_id: String, good_id: String) -> int:
	var row: Dictionary = _port_toll_row(port_id)
	if row.is_empty():
		return 0
	return clampi(int(row.get(str(good_id), 0)), 0, 80)


func _port_any_toll(port_id: String) -> bool:
	var row: Dictionary = _port_toll_row(port_id)
	for k in row.keys():
		if clampi(int(row[k]), 0, 999) > 0:
			return true
	return false


func _port_count_positive_tolls(port_id: String) -> int:
	var row: Dictionary = _port_toll_row(port_id)
	var c: int = 0
	for k in row.keys():
		if clampi(int(row[k]), 0, 999) > 0:
			c += 1
	return c


func _toll_total_coins(port_id: String, good_id: String, qty: int) -> int:
	if qty <= 0:
		return 0
	return _port_toll_per_unit(port_id, good_id) * qty


func _player_has_toll_graft(port_id: String) -> bool:
	var ps := str(port_id)
	return current_day <= int(_player_toll_graft_until.get(ps, 0))


func _player_toll_coins_for_trade(port_id: String, good_id: String, qty: int) -> int:
	if qty <= 0 or _player_has_toll_graft(port_id):
		return 0
	return _toll_total_coins(port_id, good_id, qty)


func _npc_toll_graft_last_day(agent: Dictionary, port_id: String) -> int:
	var raw: Variant = agent.get("toll_graft_until", null)
	if typeof(raw) != TYPE_DICTIONARY:
		return 0
	return clampi(int((raw as Dictionary).get(str(port_id), 0)), 0, 999999)


func _npc_has_toll_graft(agent: Dictionary, port_id: String) -> bool:
	return current_day <= _npc_toll_graft_last_day(agent, port_id)


func _npc_set_toll_graft(agent: Dictionary, port_id: String, last_day_inclusive: int) -> void:
	var raw: Variant = agent.get("toll_graft_until", null)
	var m: Dictionary
	if typeof(raw) == TYPE_DICTIONARY:
		m = (raw as Dictionary).duplicate()
	else:
		m = {}
	m[str(port_id)] = clampi(last_day_inclusive, 0, 999999)
	agent["toll_graft_until"] = m


func _npc_roll_toll_coins_paid(agent: Dictionary, port_id: String, base_toll_coins: int) -> int:
	if base_toll_coins <= 0:
		return 0
	if _npc_has_toll_graft(agent, port_id):
		return 0
	var openn: float = _npc_trait_f(agent, _NPC_TRAIT_OPEN)
	var consc: float = _npc_trait_f(agent, _NPC_TRAIT_CONSC)
	var neuro: float = _npc_trait_f(agent, _NPC_TRAIT_NEURO)
	var risk: float = clampf(float(agent.get("risk_aversion", 0.5)), 0.0, 1.0)
	var p_smuggle: float = clampf(
		0.08 + openn * 0.22 - consc * 0.10 - risk * 0.08 + neuro * 0.04,
		0.02,
		0.52,
	)
	if _rng.randf() > p_smuggle:
		return base_toll_coins
	var p_caught: float = clampf(0.14 + consc * 0.12 - openn * 0.06 + risk * 0.10, 0.05, 0.45)
	if _rng.randf() < p_caught:
		return mini(base_toll_coins * 2, base_toll_coins + 72)
	return 0


func _npc_docked_toll_graft_tick() -> void:
	for item in _npc_agents:
		if typeof(item) != TYPE_DICTIONARY:
			continue
		var ag: Dictionary = item as Dictionary
		if int(ag.get("voyage_days_remaining", 0)) != 0:
			continue
		var ps: String = str(ag.get("docked_port", ""))
		if ps.is_empty() or not _port_names.has(ps):
			continue
		if not _port_any_toll(ps):
			continue
		if _npc_has_toll_graft(ag, ps):
			continue
		if _rng.randf() > _TOLL_NPC_BRIBE_DAILY_CHANCE:
			continue
		var coins: int = clampi(int(ag.get("money", 0)), 0, _MAX_PURSE_COINS)
		var n_tolls: int = _port_count_positive_tolls(ps)
		var cost: int = clampi(12 + 4 * n_tolls, 16, 98)
		if coins < cost + _NPC_PURSE_RESERVE + 6:
			continue
		ag["money"] = coins - cost
		var du: int = _rng.randi_range(_TOLL_BRIBE_DAYS_MIN, _TOLL_BRIBE_DAYS_MAX)
		_npc_set_toll_graft(ag, ps, current_day + du - 1)


func _bump_port_for_toll_receipt(port_id: String, toll_coins: int) -> void:
	if toll_coins <= 0:
		return
	var ps := str(port_id)
	if not _port_names.has(ps):
		return
	_bump_port_wealth(ps, maxi(1, toll_coins / 3))


func _harbour_due_for_captain(purse: int, ships: int) -> int:
	var p: int = clampi(purse, 0, _MAX_PURSE_COINS)
	var sh: int = clampi(ships, 1, _FLEET_MAX_SHIPS)
	var base_d: int = _HARBOUR_DUE_BASE + sh * _HARBOUR_DUE_PER_SHIP
	var thr: int = _HARBOUR_DUE_PURSE_THRESHOLD
	var divv: int = maxi(1, _HARBOUR_DUE_PURSE_DIV)
	var capg: int = _HARBOUR_DUE_PROGRESSIVE_CAP
	var prog: int = maxi(0, (p - thr) / divv)
	return maxi(0, base_d + mini(capg, prog))


func _take_harbour_due_from_purse(purse: int, ships: int) -> int:
	var due: int = _harbour_due_for_captain(purse, ships)
	return mini(due, clampi(purse, 0, _MAX_PURSE_COINS))


func _harbour_due_port_wealth_bump(port_id: String, take: int, traffic_berths: int) -> void:
	if take <= 0:
		return
	var ps: String = str(port_id)
	if ps.is_empty() or not _port_names.has(ps):
		return
	_port_harbour_due_coins_tick[ps] = int(_port_harbour_due_coins_tick.get(ps, 0)) + take
	var n: int = maxi(1, traffic_berths)
	var bonus_pct: int = mini(_HARBOUR_BUSY_MAX_BONUS_PCT, maxi(0, n - 1) * _HARBOUR_BUSY_PER_DOCK_PCT)
	var scaled: int = (take * (100 + bonus_pct)) / 100
	_bump_port_wealth(ps, maxi(1, scaled / _HARBOUR_WEALTH_PER_COINS_PAID))


func _npc_apply_harbour_dues_if_docked_after_trade() -> void:
	var traffic_n: Dictionary = {}
	for item in _npc_agents:
		if typeof(item) != TYPE_DICTIONARY:
			continue
		var ag0: Dictionary = item as Dictionary
		if int(ag0.get("voyage_days_remaining", 0)) != 0:
			continue
		var dp: String = str(ag0.get("docked_port", ""))
		if dp.is_empty() or not _port_names.has(dp):
			continue
		traffic_n[dp] = int(traffic_n.get(dp, 0)) + 1
	for item in _npc_agents:
		if typeof(item) != TYPE_DICTIONARY:
			continue
		var ag: Dictionary = item as Dictionary
		if int(ag.get("voyage_days_remaining", 0)) != 0:
			continue
		var pid: String = str(ag.get("docked_port", ""))
		if pid.is_empty() or not _port_names.has(pid):
			continue
		_ensure_npc_ship_fields(ag)
		var purse: int = clampi(int(ag.get("money", 0)), 0, _MAX_PURSE_COINS)
		var ships: int = clampi(int(ag.get("fleet_ships", 1)), 1, _FLEET_MAX_SHIPS)
		var take: int = _take_harbour_due_from_purse(purse, ships)
		if take > 0:
			ag["money"] = clampi(purse - take, 0, _MAX_PURSE_COINS)
			var n_here: int = maxi(1, int(traffic_n.get(pid, 1)))
			_harbour_due_port_wealth_bump(pid, take, n_here)


func _marine_wage_rate_per_unit() -> float:
	if not _goods.has("marines"):
		return 0.0
	var g: Dictionary = _goods["marines"] as Dictionary
	return clampf(float(g.get("wage_per_unit_per_day", _MARINE_WAGE_PER_UNIT_PER_DAY_DEFAULT)), 0.0, _MARINE_WAGE_RATE_MAX)


func _marine_wage_due_for_cargo(cargo: Dictionary, pay_scale: float) -> int:
	if not _goods.has("marines"):
		return 0
	var n: int = _captain_cargo_qty(cargo, "marines")
	if n <= 0:
		return 0
	var rate: float = _marine_wage_rate_per_unit()
	if rate <= 0.0:
		return 0
	var sc: float = clampf(pay_scale, 0.2, 8.0)
	return maxi(0, int(ceil(float(n) * rate * sc)))


func _tick_captain_officer_pay(cap: Dictionary, emit_player_signals: bool) -> void:
	var money_before: int = clampi(int(cap.get("money", 0)), 0, _MAX_PURSE_COINS)
	var money: int = money_before
	var cond: int = clampi(int(cap.get("ship_condition", _SHIP_CONDITION_MAX)), _SHIP_CONDITION_MIN, _SHIP_CONDITION_MAX)
	var ships: int = clampi(int(cap.get("fleet_ships", 1)), 1, _FLEET_MAX_SHIPS)
	var pay_scale: float = clampf(float(cap.get("officer_pay_scale", 1.0)), 0.2, 8.0)
	var officer_pay: int = maxi(1, int(ceil(float(_SHIP_OFFICER_PAY_DAILY) * float(ships) * pay_scale)))
	var marine_w: int = 0
	var cargo_v: Variant = cap.get("cargo", null)
	if typeof(cargo_v) == TYPE_DICTIONARY:
		marine_w = _marine_wage_due_for_cargo(cargo_v as Dictionary, pay_scale)
	var pay: int = officer_pay + marine_w
	var pay_actual: int = mini(pay, money)
	if pay_actual > 0:
		money -= pay_actual
	if pay_actual < pay and _SHIP_OFFICER_UNDERPAY_CONDITION_PENALTY > 0:
		cond = clampi(cond - _SHIP_OFFICER_UNDERPAY_CONDITION_PENALTY, _SHIP_CONDITION_MIN, _SHIP_CONDITION_MAX)
	money = clampi(money, 0, _MAX_PURSE_COINS)
	cap["money"] = money
	cap["ship_condition"] = cond
	if emit_player_signals and money != money_before:
		money_changed.emit()


## Shared trireme rules: crew wine from hold (no grain draw from hold), sea wear, dock repair. Officer pay is omitted here — at sea it is not charged; when docked it runs after port trade (`_tick_captain_officer_pay`). `cap` keys: money (int), cargo (Dictionary), ship_condition, ship_wine_counter, optional fleet_ships (default 1 for NPCs).
func _tick_captain_shared(cap: Dictionary, was_at_sea_today: bool, docked_for_repair: bool, emit_player_signals: bool) -> void:
	var cargo: Variant = cap.get("cargo", null)
	if typeof(cargo) != TYPE_DICTIONARY:
		return
	var cargo_d: Dictionary = cargo as Dictionary
	var money_before: int = clampi(int(cap.get("money", 0)), 0, _MAX_PURSE_COINS)
	var money: int = money_before
	var cond: int = clampi(int(cap.get("ship_condition", _SHIP_CONDITION_MAX)), _SHIP_CONDITION_MIN, _SHIP_CONDITION_MAX)
	var wctr: int = clampi(int(cap.get("ship_wine_counter", 0)), 0, 9999)
	var cargo_touch: bool = false
	var ships: int = clampi(int(cap.get("fleet_ships", 1)), 1, _FLEET_MAX_SHIPS)
	var wine_per_ship: int = maxi(1, int(cap.get("crew_wine_per_ship", 1)))
	var wine_cult: float = clampf(float(cap.get("crew_wine_cultural_scale", 1.0)), 0.5, 2.5)
	if _goods.has("wine"):
		wctr += 1
		if wctr % _SHIP_CREW_WINE_EVERY_N_DAYS == 0:
			var need_w2: int = maxi(1, int(ceil(float(ships * wine_per_ship) * wine_cult)))
			var take_w2: int = mini(need_w2, _captain_cargo_qty(cargo_d, "wine"))
			if take_w2 > 0:
				_captain_cargo_apply_delta(cargo_d, "wine", -take_w2)
				cargo_touch = true
			if take_w2 < need_w2 and _SHIP_RATION_MISS_WINE_PENALTY > 0:
				cond = clampi(
					cond - (need_w2 - take_w2) * _SHIP_RATION_MISS_WINE_PENALTY,
					_SHIP_CONDITION_MIN,
					_SHIP_CONDITION_MAX,
				)
	if was_at_sea_today and _SHIP_WEAR_AT_SEA > 0:
		cond = clampi(cond - _SHIP_WEAR_AT_SEA, _SHIP_CONDITION_MIN, _SHIP_CONDITION_MAX)
	if docked_for_repair and cond < _SHIP_CONDITION_MAX:
		var did_repair: bool = false
		if _goods.has("metal") and _goods.has("wire"):
			if _captain_cargo_qty(cargo_d, "metal") >= 1 and _captain_cargo_qty(cargo_d, "wire") >= 1:
				_captain_cargo_apply_delta(cargo_d, "metal", -1)
				_captain_cargo_apply_delta(cargo_d, "wire", -1)
				cargo_touch = true
				cond = mini(_SHIP_CONDITION_MAX, cond + _SHIP_REPAIR_MATERIALS_GAIN)
				did_repair = true
		if not did_repair and cond < _SHIP_REPAIR_COIN_MAX_CONDITION:
			var rcm: float = clampf(float(cap.get("repair_coin_mult", 1.0)), 0.35, 3.5)
			var coin_cost: int = maxi(
				1,
				int(
					ceil(
						float(_SHIP_REPAIR_COIN_COST + maxi(0, ships - 1) * _FLEET_REPAIR_COIN_PER_EXTRA_SHIP)
						* rcm
					)
				)
			)
			if money >= coin_cost:
				money -= coin_cost
				cond = mini(_SHIP_CONDITION_MAX, cond + _SHIP_REPAIR_COIN_GAIN)
	cond = clampi(cond, _SHIP_CONDITION_MIN, _SHIP_CONDITION_MAX)
	money = clampi(money, 0, _MAX_PURSE_COINS)
	cap["money"] = money
	cap["ship_condition"] = cond
	cap["ship_wine_counter"] = wctr
	if emit_player_signals and (cargo_touch or money != money_before):
		cargo_changed.emit()
		money_changed.emit()


## Crew wine from hold, sea wear, dockside repair (after voyage resolution for this calendar day). Officer pay when in port runs at end of `advance_day` after world/NPC trade.
func _tick_player_ship_and_crew(was_at_sea_today: bool) -> void:
	var row: Dictionary = _player_ship_row()
	var cw: int = maxi(1, int(row.get("crew_wine_per_ship", 1)))
	var oph: int = maxi(1, int(row.get("officer_pay_per_hull", 1)))
	var cul: float = _player_cultural_ops_scale()
	var off_scale: float = float(oph) * cul
	var cap: Dictionary = {
		"money": player_money,
		"cargo": player_cargo,
		"ship_condition": player_ship_condition,
		"ship_wine_counter": player_ship_wine_counter,
		"fleet_ships": clampi(player_fleet_ships, 1, _FLEET_MAX_SHIPS),
		"crew_wine_per_ship": cw,
		"officer_pay_scale": off_scale,
		"repair_coin_mult": float(row.get("repair_coin_mult", 1.0)),
		"crew_wine_cultural_scale": cul,
	}
	_tick_captain_shared(cap, was_at_sea_today, not is_at_sea(), true)
	player_money = clampi(int(cap.get("money", 0)), 0, _MAX_PURSE_COINS)
	player_ship_condition = clampi(int(cap.get("ship_condition", _SHIP_CONDITION_MAX)), _SHIP_CONDITION_MIN, _SHIP_CONDITION_MAX)
	player_ship_wine_counter = clampi(int(cap.get("ship_wine_counter", 0)), 0, 9999)
	if player_ship_age_days > 360 and _rng.randf() < _SHIP_AGE_LEAK_DAILY_P * (0.15 + _player_age_stress_01()):
		player_ship_condition = clampi(player_ship_condition - 1, _SHIP_CONDITION_MIN, _SHIP_CONDITION_MAX)


## One-line summary of this port's stock while docked.
func get_port_market_line() -> String:
	if is_at_sea():
		return ""
	var pid := player_port_id
	var bits: PackedStringArray = []
	for good_id in _goods.keys():
		var gid := str(good_id)
		bits.append("%s %d" % [get_good_name(gid), _port_stock_qty(pid, gid)])
	if bits.is_empty():
		return "Port stock: —"
	return "Port stock: " + ", ".join(bits)


## Population drain + farms + NPC headcount while docked (full string: digest + food mood + dock rumor). Prefer UI: `get_port_city_supply_digest` + `get_player_tavern_mood_block`.
func get_port_activity_summary() -> String:
	if is_at_sea():
		return ""
	var digest: String = get_port_city_supply_digest()
	var mood_s: String = ""
	if _goods.has("grain"):
		var eat_cfg: int = get_population_grain_eat_effective(player_port_id)
		if eat_cfg > 0:
			var pid := player_port_id
			var unrest: int = get_port_food_unrest(pid)
			var fd: float = get_grain_food_days_for_port(pid)
			var fd_show: String = ">200 d" if fd > 200.0 else "%.1f d" % fd
			var thr: int = _food_riot_threshold_for_port(pid)
			var tier: String = _food_unrest_tier_label(unrest)
			mood_s = "Grain runway ~%s (this ration); mood %s (unrest %d/200, riot checks near ≥%d). " % [fd_show, tier, unrest, thr]
		else:
			mood_s = "No population grain ration configured. "
	var rumor_tail: String = ""
	if not _last_crop_rumor_ui_line.is_empty():
		rumor_tail = "\n" + _last_crop_rumor_ui_line
	return digest + mood_s + rumor_tail


## City calendar, harvest rhythm, population draw, farms/mines, industry, war — **without** grain-mood sentence or dock rumor (those go to Tavern UI).
func get_port_city_supply_digest() -> String:
	if is_at_sea():
		return ""
	var pid := player_port_id
	var eat_g: int = get_population_grain_eat_effective(pid)
	var w_base: int = int(_port_population_wine_base.get(pid, 1))
	var f_base: int = clampi(int(_port_population_fish_per_day.get(pid, 0)), 0, 40)
	var wealth: int = int(_port_wealth.get(pid, 100))
	var w_extra: int = clampi(int(float(wealth) / 95.0), 0, 14)
	var w_cap: int = w_base + w_extra
	var dg: Variant = _last_pop_digest.get(pid, null)
	var w_shown: int = w_cap
	var g_shown: int = eat_g
	var f_shown: int = f_base
	if typeof(dg) == TYPE_DICTIONARY:
		var dd: Dictionary = dg as Dictionary
		g_shown = int(dd.get("grain", eat_g))
		w_shown = int(dd.get("wine", w_cap))
		f_shown = int(dd.get("fish", f_base))
	var n_docked: int = _count_npc_docked_at(pid)
	var n_in: int = _count_npc_sailing_toward(pid)
	var farm_s: String = _farms_one_liner_for_port(pid)
	var mine_s: String = _mines_one_liner_for_port(pid)
	var spoil: int = int(_last_grain_spoilage.get(pid, 0))
	var spoil_s: String = "last night granary loss ~%d grain (rot/vermin)." % spoil if spoil > 0 else "no granary loss last night."
	var ind_s: String = ""
	var idig: Variant = _last_industrial_sink_digest.get(pid, null)
	if typeof(idig) == TYPE_DICTIONARY:
		var imt: int = int((idig as Dictionary).get("metal", 0))
		var iwt: int = int((idig as Dictionary).get("wire", 0))
		var itb: int = int((idig as Dictionary).get("timber", 0))
		var itx: int = int((idig as Dictionary).get("textiles", 0))
		if imt > 0 or iwt > 0 or itb > 0 or itx > 0:
			ind_s = (
				"Workshops drew ~%d ingots, ~%d wire, ~%d timber, ~%d textiles from city stores. "
				% [imt, iwt, itb, itx]
			)
	var war_s: String = ""
	if is_port_at_war(pid):
		var wd_left: int = get_port_war_days_remaining(pid)
		var war_head: String = "City at war (%d d left) — " % wd_left
		var wm: int = 0
		var ww: int = 0
		var wd: Variant = _last_war_industry_digest.get(pid, null)
		if typeof(wd) == TYPE_DICTIONARY:
			wm = int((wd as Dictionary).get("metal", 0))
			ww = int((wd as Dictionary).get("wire", 0))
		if wm > 0 or ww > 0:
			war_s = war_head + "last night ~%d ingots, ~%d wire drawn for arms, hulls, and rigging (metal market tight). " % [wm, ww]
		else:
			war_s = war_head + "farms yield less grain/wine; ration demand is up; metal prices elevated. "
	var pop_scale_s: String = "Farm & mine output ×%.2f vs founding headcount. " % _population_output_scale_for_port(pid)
	var pop_line: String = (
		"Population ~%d grain/day, ~%d wine/day (base %d + prosperity; wealth %d)"
		% [g_shown, w_shown, w_base, wealth]
	)
	if _goods.has("fish") and f_base > 0:
		pop_line += ", ~%d fish/day (ration %d)" % [f_shown, f_base]
	pop_line += ". " + farm_s + mine_s + spoil_s + ind_s + war_s + pop_scale_s
	pop_line += "NPCs: %d docked, ~%d inbound by sea." % [n_docked, n_in]
	var doy0: int = get_calendar_day_of_year()
	var cal_head: String = (
		"%s Y%d (calendar day %d/%d). "
		% [get_calendar_season_name(), get_calendar_year_index(), doy0, _CALENDAR_YEAR_LEN]
	)
	var harv_note: String = (
		"Harvest peak ~%d–%d (heavy grain & wine); rest of year a small field trickle (~%.0f%% of farm rate) + trade. "
		% [_HARVEST_START_DOY, _HARVEST_END_DOY, _CROP_OFFSEASON_SCALE * 100.0]
		if not _is_harvest_doy(doy0)
		else "Harvest window — fields are shipping grain and wine into city stores. "
	)
	return cal_head + harv_note + pop_line


## Grain runway + unrest tier (for Tavern “moods” card). Empty if no grain ration.
func get_player_port_food_mood_sentence() -> String:
	if is_at_sea() or not _goods.has("grain"):
		return ""
	var pid := str(player_port_id)
	if not _port_names.has(pid):
		return ""
	var eat_cfg: int = get_population_grain_eat_effective(pid)
	if eat_cfg <= 0:
		return "No population grain ration configured."
	var unrest: int = get_port_food_unrest(pid)
	var fd: float = get_grain_food_days_for_port(pid)
	var fd_show: String = ">200 d" if fd > 200.0 else "%.1f d" % fd
	var thr: int = _food_riot_threshold_for_port(pid)
	var tier: String = _food_unrest_tier_label(unrest)
	return "Grain runway ~%s (this ration); mood %s (unrest %d/200, riot checks near ≥%d)." % [fd_show, tier, unrest, thr]


## Docked tavern card: public food mood + your crop/war reads + last dockside crop rumor line.
func get_player_tavern_mood_block() -> String:
	if is_at_sea():
		return ""
	var lines: PackedStringArray = []
	var food_m: String = get_player_port_food_mood_sentence()
	if not food_m.is_empty():
		lines.append(food_m)
	var cr: String = get_player_crop_rumor_intel_strip_line()
	if not cr.is_empty():
		lines.append(cr)
	var wr: String = get_player_war_rumor_intel_strip_line()
	if not wr.is_empty():
		lines.append(wr)
	if not _last_crop_rumor_ui_line.is_empty():
		lines.append("Dockside crop chatter: " + _last_crop_rumor_ui_line)
	if lines.is_empty():
		return "No separate mood reads yet — dock a grain port or wait for harbor talk."
	return "\n\n".join(lines)


## UI: civic mood label for food unrest (0–200 scale).
func get_port_mood_label(port_id: String) -> String:
	return _food_unrest_tier_label(get_port_food_unrest(port_id))


## Merchants with non-empty `scattered_ids` (convoy tail broken by piracy etc.). x = leaders, y = detached ids.
func _npc_scattered_convoy_tail_stats() -> Vector2i:
	var leaders: int = 0
	var tails: int = 0
	for item in _npc_agents:
		if typeof(item) != TYPE_DICTIONARY:
			continue
		var ag: Dictionary = item as Dictionary
		if str(ag.get("voyage_role", _VOYAGE_ROLE_MERCHANT)) != _VOYAGE_ROLE_MERCHANT:
			continue
		var scv: Variant = ag.get("scattered_ids", null)
		if typeof(scv) != TYPE_ARRAY:
			continue
		var sca: Array = scv as Array
		if sca.is_empty():
			continue
		leaders += 1
		tails += sca.size()
	return Vector2i(leaders, tails)


## Tavern / notice-board style intel (rumours, smuggling talk). Docked only; empty at sea.
func get_player_city_tavern_intel_block() -> String:
	if is_at_sea():
		return "No tavern ashore while you are at sea."
	var pid := player_port_id
	var lines: PackedStringArray = []
	lines.append(
		"Pitch, dice, and spilled wine — pilots, clerks, and discharged oarsmen trade gossip, "
		+ "contraband tips, and names of captains who need escorts."
	)
	var wr: float = clampf(float(_port_war_rumor.get(pid, 0.0)), 0.0, 1.0)
	if wr > 0.08:
		lines.append(
			"Neighbour-war fear runs high (~%d%% on the old hands’ scale); "
			% int(round(wr * 100.0))
			+ "staples and arms are what they argue over, not perfume."
		)
	else:
		lines.append(
			"Tonight the talk is warehouses and weather more than spears — "
			+ "only a faint reek of distant battle on the rumor wind."
		)
	var row0: Variant = _port_rumor_good_delta.get(pid, null)
	if typeof(row0) == TYPE_DICTIONARY:
		var row: Dictionary = row0 as Dictionary
		var scored: Array[Dictionary] = []
		for gk in row.keys():
			var gid := str(gk)
			var dv: float = float(row[gk])
			scored.append({"id": gid, "absv": absf(dv), "dv": dv})
		scored.sort_custom(
			func(a: Dictionary, b: Dictionary) -> bool: return float(a["absv"]) > float(b["absv"])
		)
		var whispers: PackedStringArray = []
		for i in range(mini(4, scored.size())):
			var cell: Dictionary = scored[i]
			var gnm: String = get_good_name(str(cell["id"]))
			var dv2: float = float(cell["dv"])
			if dv2 > 0.004:
				whispers.append("%s: talk of scarcity and dearer holds" % gnm)
			elif dv2 < -0.004:
				whispers.append("%s: talk of gluts and soft prices" % gnm)
		if not whispers.is_empty():
			lines.append("Whispers: " + "; ".join(whispers) + ".")
	if player_docked_port_has_tolls():
		lines.append(
			"Smuggling: the quaestor’s clerks weigh every bale — "
			+ "cargadors wink about which scales can be… adjusted. "
			+ "(Gifts and minting are handled in the official quarter, not here.)"
		)
	else:
		lines.append("Smuggling: light duties here — more grumbling about prices than about seals.")
	var pulse: float = clampf(float(_port_commerce_pulse.get(pid, 0.38)), 0.0, 1.0)
	lines.append(
		(
			"Contracts & crew: escort postings favor fast hulls; the market hall sells marine "
			+ "kit (arms and armour) while a separate dock ledger pays their wages each day in port."
		)
		+ " Harbor bustle sits at ~%d%%." % int(round(pulse * 100.0))
	)
	var sc_stats: Vector2i = _npc_scattered_convoy_tail_stats()
	if sc_stats.x > 0:
		lines.append(
			"Pirate talk: %d merchant masters still curse convoy breaks — %d hulls peeled off their ledgers to sail alone after raids."
			% [sc_stats.x, sc_stats.y]
		)
		lines.append(
			"Same hands: each new convoy sortie the master draws a fresh “bold station” weight — corsairs use it when picking which hull to grapple first; names fall off the tail list over time, and the weight fades in harbor."
		)
	return "\n\n".join(lines)


func _player_crop_intel_reset_for_port_visit(port_id: String) -> void:
	var ps := str(port_id)
	if not _port_names.has(ps) or not _goods.has("grain"):
		return
	player_crop_intel_port_id = ps
	var mk: float = _crop_grain_stress_01_market_for_port(ps)
	player_crop_intel_mean_01 = clampf(mk + _rng.randf_range(-0.11, 0.11), 0.0, 1.0)
	player_crop_intel_sigma_01 = _PLAYER_CROP_INTEL_SIGMA_INIT
	player_crop_intel_update_day = current_day


func _ensure_player_crop_intel_port_sync() -> void:
	if is_at_sea() or not _world_crop_agro_model or not _goods.has("grain"):
		return
	var ps := str(player_port_id)
	if not _port_names.has(ps):
		return
	if player_crop_intel_port_id != ps:
		_player_crop_intel_reset_for_port_visit(ps)


func get_player_crop_intel_confidence_percent() -> int:
	var sig: float = clampf(player_crop_intel_sigma_01, 0.0, 1.0)
	var t: float = clampf(sig / maxf(0.0001, _PLAYER_CROP_INTEL_SIGMA_CONF_SCALE), 0.0, 1.0)
	return clampi(int(round((1.0 - t) * 100.0)), 0, 100)


## One-line status strip: market grain-stress read, confidence, last notebook day (Phase 5b).
func get_player_crop_rumor_intel_strip_line() -> String:
	if is_at_sea() or not _world_crop_agro_model or not _goods.has("grain"):
		return ""
	_ensure_player_crop_intel_port_sync()
	var pct: int = clampi(int(round(clampf(player_crop_intel_mean_01, 0.0, 1.0) * 100.0)), 0, 100)
	var conf: int = get_player_crop_intel_confidence_percent()
	var day_s: String = str(player_crop_intel_update_day) if player_crop_intel_update_day > 0 else "—"
	return (
		"Grain trade mood (your read): ~%d%% stressed · confidence %d%% · notebook day %s · quay repute ~%d%%"
		% [pct, conf, day_s, clampi(int(round(clampf(player_civic_reputation_01, 0.0, 1.0) * 100.0)), 0, 100)]
	)


func get_player_crop_intel_investigate_coin_cost() -> int:
	return _PLAYER_CROP_INVESTIGATE_COINS


func get_player_crop_intel_spread_rumor_coin_cost() -> int:
	return _PLAYER_CROP_SPREAD_RUMOR_COINS


func player_can_investigate_crop_market_intel() -> bool:
	if is_at_sea() or not _world_crop_agro_model or not _goods.has("grain"):
		return false
	if not _port_names.has(str(player_port_id)):
		return false
	_ensure_player_crop_intel_port_sync()
	if player_money < _PLAYER_CROP_INVESTIGATE_COINS:
		return false
	return player_crop_intel_sigma_01 > _PLAYER_CROP_INTEL_SIGMA_MIN + 0.014


func player_can_spread_crop_market_rumor() -> bool:
	if is_at_sea() or not _world_crop_agro_model or not _goods.has("grain"):
		return false
	return _port_names.has(str(player_port_id)) and player_money >= _PLAYER_CROP_SPREAD_RUMOR_COINS


## Spend coin + clerk time: pull market stress posterior toward truth with noise (never perfect).
func try_player_investigate_crop_market_intel() -> bool:
	if not player_can_investigate_crop_market_intel():
		return false
	var ps := str(player_port_id)
	var truth: float = _crop_grain_stress_01_market_for_port(ps)
	var pull: float = lerpf(0.36, 0.58, clampf(player_civic_reputation_01, 0.0, 1.0))
	var mn: float = clampf(
		player_crop_intel_mean_01 + (truth - player_crop_intel_mean_01) * pull + _rng.randf_range(-0.024, 0.024),
		0.0,
		1.0
	)
	player_crop_intel_mean_01 = mn
	player_crop_intel_sigma_01 = maxf(_PLAYER_CROP_INTEL_SIGMA_MIN, player_crop_intel_sigma_01 * 0.68)
	player_crop_intel_update_day = current_day
	player_civic_reputation_01 = clampf(player_civic_reputation_01 + 0.0055, 0.0, 1.0)
	_bump_player_port_civic_reputation_01(ps, _LOCAL_PORT_CIVIC_INVESTIGATE_BUMP)
	player_money = clampi(player_money - _PLAYER_CROP_INVESTIGATE_COINS, 0, _MAX_PURSE_COINS)
	money_changed.emit()
	market_changed.emit()
	return true


## Dockside talk: shifts *public* crop rumor delta (prices), costs repute, widens your own uncertainty.
func try_player_spread_crop_market_rumor(scarcity_talk: bool) -> bool:
	if not player_can_spread_crop_market_rumor():
		return false
	var ps := str(player_port_id)
	var cur: float = float(_port_crop_rumor_public_delta.get(ps, 0.0))
	var add: float = _PLAYER_CROP_SPREAD_DELTA if scarcity_talk else -_PLAYER_CROP_SPREAD_DELTA * 0.92
	cur = clampf(cur + add, -_CROP_RUMOR_DELTA_ABS_MAX, _CROP_RUMOR_DELTA_ABS_MAX)
	if absf(cur) < 0.0025:
		_port_crop_rumor_public_delta.erase(ps)
	else:
		_port_crop_rumor_public_delta[ps] = cur
	player_money = clampi(player_money - _PLAYER_CROP_SPREAD_RUMOR_COINS, 0, _MAX_PURSE_COINS)
	var rep_hit: float = 0.019 if scarcity_talk else 0.016
	player_civic_reputation_01 = clampf(player_civic_reputation_01 - rep_hit, 0.0, 1.0)
	_bump_player_port_civic_reputation_01(ps, -_LOCAL_PORT_CIVIC_RUMOR_HIT)
	player_crop_intel_sigma_01 = clampf(player_crop_intel_sigma_01 + 0.034, _PLAYER_CROP_INTEL_SIGMA_MIN, 0.34)
	if _rng.randf() < 0.28:
		var bias: float = _rng.randf_range(0.04, 0.09) * (1.0 if scarcity_talk else -1.0)
		player_crop_intel_mean_01 = clampf(player_crop_intel_mean_01 + bias, 0.0, 1.0)
	player_crop_intel_update_day = current_day
	money_changed.emit()
	market_changed.emit()
	return true


func _player_war_intel_truth_for_port(port_id: String) -> float:
	var ps := str(port_id)
	if not _port_names.has(ps):
		return 0.0
	return clampf(float(_port_war_rumor.get(ps, 0.0)), 0.0, 1.0)


func _player_war_intel_reset_for_port_visit(port_id: String) -> void:
	var ps := str(port_id)
	if not _port_names.has(ps):
		return
	player_war_intel_port_id = ps
	var mk: float = _player_war_intel_truth_for_port(ps)
	player_war_intel_mean_01 = clampf(mk + _rng.randf_range(-0.12, 0.12), 0.0, 1.0)
	player_war_intel_sigma_01 = _PLAYER_CROP_INTEL_SIGMA_INIT
	player_war_intel_update_day = current_day


func _ensure_player_war_intel_port_sync() -> void:
	if is_at_sea():
		return
	var ps := str(player_port_id)
	if not _port_names.has(ps):
		return
	if player_war_intel_port_id != ps:
		_player_war_intel_reset_for_port_visit(ps)


func get_player_war_intel_confidence_percent() -> int:
	var sig: float = clampf(player_war_intel_sigma_01, 0.0, 1.0)
	var t: float = clampf(sig / maxf(0.0001, _PLAYER_CROP_INTEL_SIGMA_CONF_SCALE), 0.0, 1.0)
	return clampi(int(round((1.0 - t) * 100.0)), 0, 100)


func get_player_war_rumor_intel_strip_line() -> String:
	if is_at_sea():
		return ""
	_ensure_player_war_intel_port_sync()
	var pct: int = clampi(int(round(clampf(player_war_intel_mean_01, 0.0, 1.0) * 100.0)), 0, 100)
	var conf: int = get_player_war_intel_confidence_percent()
	var day_s: String = str(player_war_intel_update_day) if player_war_intel_update_day > 0 else "—"
	return (
		"Neighbour-war fear (your read): ~%d%% · confidence %d%% · notebook day %s · quay repute ~%d%%"
		% [pct, conf, day_s, clampi(int(round(clampf(player_civic_reputation_01, 0.0, 1.0) * 100.0)), 0, 100)]
	)


func get_player_war_intel_investigate_coin_cost() -> int:
	return _PLAYER_WAR_INVESTIGATE_COINS


func get_player_war_intel_spread_rumor_coin_cost() -> int:
	return _PLAYER_WAR_SPREAD_RUMOR_COINS


func player_can_investigate_war_rumor_intel() -> bool:
	if is_at_sea():
		return false
	if not _port_names.has(str(player_port_id)):
		return false
	_ensure_player_war_intel_port_sync()
	if player_money < _PLAYER_WAR_INVESTIGATE_COINS:
		return false
	return player_war_intel_sigma_01 > _PLAYER_CROP_INTEL_SIGMA_MIN + 0.014


func player_can_spread_war_rumor() -> bool:
	if is_at_sea():
		return false
	return _port_names.has(str(player_port_id)) and player_money >= _PLAYER_WAR_SPREAD_RUMOR_COINS


func try_player_investigate_war_rumor_intel() -> bool:
	if not player_can_investigate_war_rumor_intel():
		return false
	var ps := str(player_port_id)
	var truth: float = _player_war_intel_truth_for_port(ps)
	var pull: float = lerpf(0.34, 0.56, clampf(player_civic_reputation_01, 0.0, 1.0))
	var mn: float = clampf(
		player_war_intel_mean_01 + (truth - player_war_intel_mean_01) * pull + _rng.randf_range(-0.026, 0.026),
		0.0,
		1.0
	)
	player_war_intel_mean_01 = mn
	player_war_intel_sigma_01 = maxf(_PLAYER_CROP_INTEL_SIGMA_MIN, player_war_intel_sigma_01 * 0.68)
	player_war_intel_update_day = current_day
	player_civic_reputation_01 = clampf(player_civic_reputation_01 + 0.0045, 0.0, 1.0)
	_bump_player_port_civic_reputation_01(ps, _LOCAL_PORT_CIVIC_INVESTIGATE_BUMP)
	player_money = clampi(player_money - _PLAYER_WAR_INVESTIGATE_COINS, 0, _MAX_PURSE_COINS)
	money_changed.emit()
	market_changed.emit()
	return true


## Inflame or cool **public** war-fear at this port; costs repute; widens your own war-read σ.
func try_player_spread_war_rumor(inflame_fear: bool) -> bool:
	if not player_can_spread_war_rumor():
		return false
	var ps := str(player_port_id)
	var wr: float = clampf(float(_port_war_rumor.get(ps, 0.0)), 0.0, 1.0)
	var dlt: float = _PLAYER_WAR_RUMOR_SPREAD_BUMP if inflame_fear else -_PLAYER_WAR_RUMOR_SPREAD_BUMP * 0.88
	wr = clampf(wr + dlt, 0.0, 1.0)
	_port_war_rumor[ps] = wr
	player_money = clampi(player_money - _PLAYER_WAR_SPREAD_RUMOR_COINS, 0, _MAX_PURSE_COINS)
	var rep_hit: float = 0.022 if inflame_fear else 0.017
	player_civic_reputation_01 = clampf(player_civic_reputation_01 - rep_hit, 0.0, 1.0)
	_bump_player_port_civic_reputation_01(ps, -_LOCAL_PORT_CIVIC_RUMOR_HIT)
	player_war_intel_sigma_01 = clampf(player_war_intel_sigma_01 + 0.036, _PLAYER_CROP_INTEL_SIGMA_MIN, 0.34)
	if _rng.randf() < 0.30:
		var bias: float = _rng.randf_range(0.045, 0.095) * (1.0 if inflame_fear else -1.0)
		player_war_intel_mean_01 = clampf(player_war_intel_mean_01 + bias, 0.0, 1.0)
	player_war_intel_update_day = current_day
	money_changed.emit()
	market_changed.emit()
	return true


func _get_player_port_civic_reputation_01(port_id: String) -> float:
	var ps := str(port_id)
	if player_port_civic_reputation_01.has(ps):
		return clampf(float(player_port_civic_reputation_01[ps]), 0.0, 1.0)
	return clampf(player_civic_reputation_01, 0.0, 1.0)


func _bump_player_port_civic_reputation_01(port_id: String, delta: float) -> void:
	var ps := str(port_id)
	if not _port_names.has(ps):
		return
	var cur: float = _get_player_port_civic_reputation_01(ps)
	player_port_civic_reputation_01[ps] = clampf(cur + delta, 0.0, 1.0)


func _tick_player_reputation_drift_daily() -> void:
	var nu: float = _CIVIC_REPUTATION_NEUTRAL_01
	var step: float = _CIVIC_REPUTATION_DRIFT_STEP
	player_civic_reputation_01 = clampf(
		player_civic_reputation_01 + (nu - player_civic_reputation_01) * step,
		0.0,
		1.0
	)
	var to_clear: PackedStringArray = []
	for pk in player_port_civic_reputation_01.keys():
		var pxs: String = str(pk)
		if not _port_names.has(pxs):
			to_clear.append(pxs)
			continue
		var v0: float = clampf(float(player_port_civic_reputation_01[pk]), 0.0, 1.0)
		var v1: float = clampf(v0 + (nu - v0) * step, 0.0, 1.0)
		if absf(v1 - nu) < 0.0012:
			to_clear.append(pxs)
		else:
			player_port_civic_reputation_01[pxs] = v1
	for ecs in to_clear:
		player_port_civic_reputation_01.erase(ecs)


func _transfer_temple_pending_storm_into_active_voyage_bless() -> void:
	if voyage_days_remaining <= 0:
		return
	player_voyage_weather_bless_p_sub = clampf(
		player_temple_pending_storm_p_sub,
		0.0,
		_TEMPLE_STORM_PENDING_P_SUB_TOTAL_CAP,
	)
	player_temple_pending_storm_p_sub = 0.0


func _official_det_jitter_01(port_id: String, salt: int) -> float:
	var ps := str(port_id)
	var h: int = absi(_npc_str_mix(ps, salt + maxi(0, current_day / 7)) % 10001)
	return float(h) / 10000.0


## Quaestor / mercantile desk: grain-trade stress & neighbour-war fear — precision rises with local standing.
func _player_official_merchant_register_lines(port_id: String) -> PackedStringArray:
	var out: PackedStringArray = []
	var ps := str(port_id)
	if not _port_names.has(ps):
		return out
	var locr: float = _get_player_port_civic_reputation_01(ps)
	var glo_pct: int = clampi(int(round(clampf(player_civic_reputation_01, 0.0, 1.0) * 100.0)), 0, 100)
	var loc_pct: int = clampi(int(round(clampf(locr, 0.0, 1.0) * 100.0)), 0, 100)
	out.append(
		(
			"Mercantile register: clerks score your reckon **in %s** near %d%% on their harbor board — "
			% [get_port_name(ps), loc_pct]
			+ "your wider quay name (gossip from other ports) sits near %d%%."
			% glo_pct
		)
	)
	if locr < _OFFICIAL_LOCAL_REP_HINT:
		out.append(
			(
				"They will not seal grain-trade or war-fear tallies for you until that **local** score clears about %d%% — "
				% int(round(_OFFICIAL_LOCAL_REP_HINT * 100.0))
				+ "honest tolls, civic coin struck here, and fewer manufactured panics on this wharf move their pens."
			)
		)
		return out
	var mk: float = _crop_grain_stress_01_market_for_port(ps)
	var wr: float = clampf(float(_port_war_rumor.get(ps, 0.0)), 0.0, 1.0)
	if _world_crop_agro_model and _goods.has("grain"):
		if locr < _OFFICIAL_LOCAL_REP_SOLID:
			var gtxt: String = (
				"easy consignments by the tallies"
				if mk < 0.36
				else "mixed signals on grain consignments" if mk < 0.58 else "tight grain consignments on the harbor watch-list"
			)
			out.append(
				"Grain (harbor trade blend, not the fields’ private truth): a clerk hints the mood is %s — no numbers yet."
				% gtxt
			)
		elif locr < _OFFICIAL_LOCAL_REP_NUMERIC:
			var gband: int = clampi(int(floor(mk * 5.0)), 0, 4)
			var gwords: Array = ["very light", "light", "middling", "heavy", "severe"]
			out.append(
				"Grain (harbor blend): they initial a note — stress on their watch-list reads %s."
				% str(gwords[gband])
			)
		else:
			var gmag: float = lerpf(0.11, 0.022, clampf((locr - _OFFICIAL_LOCAL_REP_NUMERIC) / 0.23, 0.0, 1.0))
			var gread: float = clampf(mk + ( _official_det_jitter_01(ps, 4411) - 0.5) * 2.0 * gmag, 0.0, 1.0)
			out.append(
				"Grain (sealed harbor blend): they whisper the stress figure is near **%d%%**."
				% clampi(int(round(gread * 100.0)), 0, 100)
			)
	if locr < _OFFICIAL_LOCAL_REP_SOLID:
		var wtxt: String = (
			"few coastal alarums"
			if wr < 0.34
			else "mixed talk of fleets abroad" if wr < 0.56 else "prefect’s runners ask after armor more than usual"
		)
		out.append("Neighbour-war fear on their coastal net: %s — still vague." % wtxt)
	elif locr < _OFFICIAL_LOCAL_REP_NUMERIC:
		var wband: int = clampi(int(floor(wr * 5.0)), 0, 4)
		var wwords: Array = ["quiet passes", "eddies of rumor", "uneasy harbors", "beacons watched", "fear running hot"]
		out.append("Neighbour-war fear: their signal desk calls it **%s**." % str(wwords[wband]))
	else:
		var wmag: float = lerpf(0.10, 0.020, clampf((locr - _OFFICIAL_LOCAL_REP_NUMERIC) / 0.23, 0.0, 1.0))
		var wread: float = clampf(wr + (_official_det_jitter_01(ps, 5529) - 0.5) * 2.0 * wmag, 0.0, 1.0)
		out.append(
			"Neighbour-war fear (signal desk): they put the dial near **%d%%**."
			% clampi(int(round(wread * 100.0)), 0, 100)
		)
	return out


## Basilica / courts / army — read-only flavour plus war facts.
func get_player_city_official_intel_block() -> String:
	if is_at_sea():
		return ""
	var pid := player_port_id
	var lines: PackedStringArray = []
	lines.append(
		"Marble steps, wax tablets, and soldiers on the portico — "
		+ "summons, requisitions, and the governor’s clerks all meet here."
	)
	if is_port_at_war(pid):
		var wd: int = get_port_war_days_remaining(pid)
		lines.append(
			"Law & army: the city is on a war footing (~%d d remain in this levy). "
			% wd
			+ "Courts sit in short sessions; admiralty presses ingots, wire, and timber."
		)
	else:
		var peace_next: int = clampi(int(_port_war_peace_remaining.get(pid, 0)), 0, 999)
		if peace_next > 0:
			lines.append(
				"Law & army: peace for now; veterans say the next storm may break in ~%d d if the cycle holds."
				% peace_next
			)
		else:
			lines.append(
				"Law & army: edicts posted for taxes, seizures, and harbor fines — "
				+ "the garrison drills, but no general mobilization today."
			)
	for reg_line in _player_official_merchant_register_lines(pid):
		lines.append(reg_line)
	return "\n\n".join(lines)


## Temple: omens tied to civic stress (food unrest, plague).
func get_player_city_temple_intel_block() -> String:
	if is_at_sea():
		return ""
	var pid := player_port_id
	var unrest: int = get_port_food_unrest(pid)
	var mood: String = get_port_mood_label(pid)
	var thr: int = _food_riot_threshold_for_port(pid)
	var lines: PackedStringArray = []
	lines.append(
		"Incense, vows, and processions — priests read the city’s temper as much as the gods’."
	)
	lines.append(
		"Civic temper: %s (unrest %d/200; priests warn when talk crosses ~%d)."
		% [mood, unrest, thr]
	)
	var plg: int = clampi(int(_port_plague_days.get(pid, 0)), 0, 999)
	if plg > 0:
		lines.append(
			"Sickness: offerings pile up — a visitation is said to linger (~%d more days of rites)."
			% plg
		)
	else:
		lines.append("Sickness: no major visitation in the smoke today.")
	var rep_head: float = maxf(0.0, _TEMPLE_REP_LIFETIME_CAP - player_temple_offerings_rep_granted_01)
	var rep_open_pct: int = 0
	if _TEMPLE_REP_LIFETIME_CAP > 0.0001:
		rep_open_pct = clampi(int(round(100.0 * rep_head / _TEMPLE_REP_LIFETIME_CAP)), 0, 100)
	lines.append(
		(
			"Votives: priests will record coin for lamps and safe returns. Handsome offerings buy a scrap of **quay repute**, "
			+ "but the temple ledger only seals so much bought praise (~%d%% of that clergy cap still open today). "
			% rep_open_pct
			+ "Gossip, flattering or foul, likewise **slackens** toward indifference unless you tend it."
		)
	)
	lines.append(
		(
			"State ledgers: a fixed share of sworn coin passes to the **world treasury pool** "
			+ "(the same abstract chest that civic mint pulses feed) — clergy call it the emperor’s tenth; clerks round and stamp."
		)
	)
	if player_temple_pending_storm_p_sub > 0.0001:
		lines.append(
			"Voyage offering: a storm-vow waits for **your next departure** — the sea-day gale roll stays a little softer for that whole passage (stacked gifts help, but modestly capped). Spent once you make port."
		)
	else:
		lines.append(
			"Voyage offering: no storm-vow is banked for your next sailing — leave silver here before you sail if you want the hymn for a gentler crossing."
		)
	return "\n\n".join(lines)


func get_temple_offering_coin_cost(tier: int) -> int:
	match clampi(tier, 0, 2):
		0:
			return _TEMPLE_OFFERING_SMALL_COINS
		1:
			return _TEMPLE_OFFERING_MEDIUM_COINS
		_:
			return _TEMPLE_OFFERING_LARGE_COINS


func player_can_make_temple_offering(tier: int) -> bool:
	if is_at_sea():
		return false
	if not _port_names.has(str(player_port_id)):
		return false
	var c: int = get_temple_offering_coin_cost(tier)
	return player_money >= c and c > 0


func try_player_temple_offering(tier: int) -> bool:
	if not player_can_make_temple_offering(tier):
		return false
	var ps := str(player_port_id)
	var coins: int = get_temple_offering_coin_cost(clampi(tier, 0, 2))
	var p_add: float = 0.0
	var rep_want: float = 0.0
	match clampi(tier, 0, 2):
		0:
			p_add = _TEMPLE_STORM_PENDING_P_SUB_SMALL
			rep_want = _TEMPLE_REP_GRANT_SMALL
		1:
			p_add = _TEMPLE_STORM_PENDING_P_SUB_MEDIUM
			rep_want = _TEMPLE_REP_GRANT_MEDIUM
		_:
			p_add = _TEMPLE_STORM_PENDING_P_SUB_LARGE
			rep_want = _TEMPLE_REP_GRANT_LARGE
	player_money = clampi(player_money - coins, 0, _MAX_PURSE_COINS)
	var treasury_gift: int = clampi(int(floor(float(coins) * _TEMPLE_OFFERING_TREASURY_FRAC)), 0, _WORLD_TREASURY_MAX)
	_world_treasury_coins = clampi(_world_treasury_coins + treasury_gift, 0, _WORLD_TREASURY_MAX)
	_bump_port_wealth(ps, maxi(2, coins / 8))
	var cap_t: float = _TEMPLE_STORM_PENDING_P_SUB_TOTAL_CAP
	player_temple_pending_storm_p_sub = clampf(player_temple_pending_storm_p_sub + p_add, 0.0, cap_t)
	var rep_left: float = maxf(0.0, _TEMPLE_REP_LIFETIME_CAP - player_temple_offerings_rep_granted_01)
	var rep_gain: float = mini(rep_want, rep_left)
	if rep_gain > 0.00005:
		player_temple_offerings_rep_granted_01 = clampf(player_temple_offerings_rep_granted_01 + rep_gain, 0.0, _TEMPLE_REP_LIFETIME_CAP)
		player_civic_reputation_01 = clampf(player_civic_reputation_01 + rep_gain, 0.0, 1.0)
		_bump_player_port_civic_reputation_01(ps, rep_gain * 0.88)
	money_changed.emit()
	market_changed.emit()
	return true


## Shipwright’s yard — long refits (flavour); hull condition is real state.
func get_player_city_shipwright_intel_block() -> String:
	if is_at_sea():
		return ""
	var cond: int = clampi(player_ship_condition, _SHIP_CONDITION_MIN, _SHIP_CONDITION_MAX)
	var lines: PackedStringArray = []
	lines.append(
		"Sheds, saw pits, and copper nails — master builders talk of re-framing, "
		+ "sheathing, and rerigging when a hull is laid up for weeks, not hours."
	)
	lines.append(
		"Your squadron is rated %d/%d condition. "
		% [cond, _SHIP_CONDITION_MAX]
		+ "Overnight dockhands still patch wear when timber, textiles, metal, and coin allow — "
		+ "this yard is for the slow, dear work."
	)
	return "\n\n".join(lines)


## Money-changers and bonded storage — tied to local prosperity.
func get_player_city_finance_intel_block() -> String:
	if is_at_sea():
		return ""
	var pid := player_port_id
	var wealth: int = clampi(int(_port_wealth.get(pid, 100)), 0, _MAX_PURSE_COINS)
	var lines: PackedStringArray = []
	lines.append(
		"Argentarii discount letters, weigh foreign coin, and gossip about who is illiquid. "
		+ "Bonded warehouses stack sealed jars and bales for merchants who pay storage in advance."
	)
	lines.append(
		"This port’s books feel %s (prosperity index ~%d) — "
		% ["heavy" if wealth < 85 else "steady" if wealth < 140 else "flush", wealth]
		+ "no separate loan ledger yet; your purse is still your own."
	)
	return "\n\n".join(lines)


## Baths & inn — comfort and harbor pulse.
func get_player_city_baths_intel_block() -> String:
	if is_at_sea():
		return ""
	var pid := player_port_id
	var pulse: float = clampf(float(_port_commerce_pulse.get(pid, 0.38)), 0.0, 1.0)
	var lines: PackedStringArray = []
	lines.append(
		"Steam, oil, and hired rooms — traders scrub off the bilge smell and hear softer news than in the tavern."
	)
	lines.append(
		"The innkeeper claims harbor life is ~%d%% of what a great festival day could be — "
		% int(round(pulse * 100.0))
		+ "good for sleep, poor for secrets."
	)
	return "\n\n".join(lines)


## Kilns, smithies, fullers — yesterday’s workshop draw from city stores.
func get_player_city_works_intel_block() -> String:
	if is_at_sea():
		return ""
	var pid := player_port_id
	var idig: Variant = _last_industrial_sink_digest.get(pid, null)
	var lines: PackedStringArray = []
	lines.append(
		"Smoke from kilns and forges rolls over the industrial quarter — "
		+ "potters, smiths, and ropewalks pull stock from the same granaries you trade against."
	)
	if typeof(idig) == TYPE_DICTIONARY:
		var imt: int = int((idig as Dictionary).get("metal", 0))
		var iwt: int = int((idig as Dictionary).get("wire", 0))
		var itb: int = int((idig as Dictionary).get("timber", 0))
		var itx: int = int((idig as Dictionary).get("textiles", 0))
		if imt > 0 or iwt > 0 or itb > 0 or itx > 0:
			lines.append(
				"Yesterday’s tally from workshops: ~%d ingots, ~%d wire, ~%d timber, ~%d textiles from city stores."
				% [imt, iwt, itb, itx]
			)
		else:
			lines.append("Yesterday’s tally: light draws — mostly repairs and house lots.")
	else:
		lines.append("Yesterday’s tally: no workshop digest yet.")
	return "\n\n".join(lines)


## Lighthouse / signal tower — who moves on the roads of the sea.
func get_player_city_beacon_intel_block() -> String:
	if is_at_sea():
		return ""
	var pid := player_port_id
	var n_docked: int = _count_npc_docked_at(pid)
	var n_in: int = _count_npc_sailing_toward(pid)
	var wr: float = clampf(float(_port_war_rumor.get(pid, 0.0)), 0.0, 1.0)
	var lines: PackedStringArray = []
	lines.append(
		"Smoke by day, fire-baskets by night — pilots log hulls that round the headland."
	)
	lines.append("Signal log: %d hulls in harbor, ~%d more inward bound on the lanes." % [n_docked, n_in])
	if wr > 0.12:
		lines.append(
			"The watch adds: inland rumor of war sits at ~%d%% — expect nervous convoys."
			% int(round(wr * 100.0))
		)
	return "\n\n".join(lines)


func _farms_one_liner_for_port(port_id: String) -> String:
	var bits: PackedStringArray = []
	for f in _farms:
		if typeof(f) != TYPE_DICTIONARY:
			continue
		var fd: Dictionary = f as Dictionary
		if str(fd.get("port_id", "")) != port_id:
			continue
		var nm: String = str(fd.get("name", fd.get("id", "Farm")))
		var g: int = int(fd.get("grain_per_day", 0))
		var w: int = int(fd.get("wine_per_day", 0))
		var fi: int = int(fd.get("fish_per_day", 0))
		if g > 0 or w > 0 or fi > 0:
			if fi > 0:
				bits.append("%s +%dg/%dw/%df" % [nm, g, w, fi])
			else:
				bits.append("%s +%dg/%dw" % [nm, g, w])
	if bits.is_empty():
		return "Farms: (none) "
	return "Farms: " + ", ".join(bits) + " "


func _mines_one_liner_for_port(port_id: String) -> String:
	var bits: PackedStringArray = []
	for m in _mines:
		if typeof(m) != TYPE_DICTIONARY:
			continue
		var md: Dictionary = m as Dictionary
		if str(md.get("port_id", "")) != port_id:
			continue
		var nm: String = str(md.get("name", md.get("id", "Mine")))
		var met: int = int(md.get("metal_per_day", 0))
		var wir: int = int(md.get("wire_per_day", 0))
		if met > 0 or wir > 0:
			bits.append("%s +%dm/%dw" % [nm, met, wir])
	if bits.is_empty():
		return "Mines: (none) "
	return "Mines: " + ", ".join(bits) + " "


func get_good_name(good_id: String) -> String:
	var meta: Variant = _goods.get(good_id, null)
	if typeof(meta) == TYPE_DICTIONARY:
		return str((meta as Dictionary).get("name", good_id))
	return good_id


func _count_npc_docked_at(port_id: String) -> int:
	var c: int = 0
	for ag in _npc_agents:
		if typeof(ag) != TYPE_DICTIONARY:
			continue
		var d: Dictionary = ag as Dictionary
		if int(d.get("voyage_days_remaining", 0)) != 0:
			continue
		if str(d.get("docked_port", "")) == port_id:
			c += 1
	return c


func _count_npc_sailing_toward(port_id: String) -> int:
	var c: int = 0
	for ag in _npc_agents:
		if typeof(ag) != TYPE_DICTIONARY:
			continue
		var d: Dictionary = ag as Dictionary
		if int(d.get("voyage_days_remaining", 0)) <= 0:
			continue
		if str(d.get("voyage_dest_id", "")) == port_id:
			c += 1
	return c


func get_player_buy_unit_price(good_id: String) -> int:
	if is_at_sea():
		return 0
	return _compute_player_buy_unit(player_port_id, good_id)


func get_player_sell_unit_price(good_id: String) -> int:
	if is_at_sea():
		return 0
	return _compute_player_sell_unit(player_port_id, good_id)


func get_port_stock_qty_for_player_port(good_id: String) -> int:
	if is_at_sea():
		return 0
	return _port_stock_qty(player_port_id, good_id)


## Docked only. Buys from the port at dynamic ask price; port stock must cover qty.
func try_buy(good_id: String, qty: int) -> bool:
	if qty <= 0 or is_at_sea():
		return false
	var meta: Variant = _goods.get(good_id, null)
	if typeof(meta) != TYPE_DICTIONARY:
		return false
	var port_id := player_port_id
	var unit: int = _compute_player_buy_unit(port_id, good_id)
	var cost: int = unit * qty
	var buy_fee: int = _captain_trade_fee_on_buy(cost)
	if player_money < cost + buy_fee:
		return false
	if _port_stock_qty(port_id, good_id) < qty:
		return false
	if get_player_cargo_used() + qty > get_player_cargo_capacity():
		return false
	player_money -= cost + buy_fee
	player_cargo[good_id] = int(player_cargo.get(good_id, 0)) + qty
	_adjust_port_stock(port_id, good_id, -qty)
	_bump_port_wealth(port_id, maxi(1, cost / 14))
	_player_good_last_trade_day[str(good_id)] = current_day
	money_changed.emit()
	cargo_changed.emit()
	market_changed.emit()
	return true


## Docked only. Sells to the port at dynamic bid price.
func try_sell(good_id: String, qty: int) -> bool:
	if qty <= 0 or is_at_sea():
		return false
	var meta: Variant = _goods.get(good_id, null)
	if typeof(meta) != TYPE_DICTIONARY:
		return false
	var have: int = int(player_cargo.get(good_id, 0))
	if have < qty:
		return false
	var port_id := player_port_id
	var unit: int = _compute_player_sell_unit(port_id, good_id)
	var revenue: int = unit * qty
	var sell_fee: int = _captain_trade_fee_on_sell(revenue)
	var toll: int = _player_toll_coins_for_trade(port_id, good_id, qty)
	player_money += maxi(0, revenue - sell_fee - toll)
	if toll > 0:
		_bump_port_for_toll_receipt(port_id, toll)
	var left: int = have - qty
	if left <= 0:
		player_cargo.erase(good_id)
	else:
		player_cargo[good_id] = left
	_adjust_port_stock(port_id, good_id, qty)
	_bump_port_wealth(port_id, maxi(1, revenue / 12))
	_player_good_last_trade_day[str(good_id)] = current_day
	money_changed.emit()
	cargo_changed.emit()
	market_changed.emit()
	return true


func get_trade_buy_total_coins(good_id: String, qty: int) -> int:
	if qty <= 0 or is_at_sea():
		return 0
	var pid := player_port_id
	var unit: int = _compute_player_buy_unit(pid, good_id)
	var cost: int = unit * qty
	return cost + _captain_trade_fee_on_buy(cost)


func get_trade_sell_net_coins(good_id: String, qty: int) -> int:
	if qty <= 0 or is_at_sea():
		return 0
	var pid := player_port_id
	var unit: int = _compute_player_sell_unit(pid, good_id)
	var revenue: int = unit * qty
	return maxi(0, revenue - _captain_trade_fee_on_sell(revenue) - _player_toll_coins_for_trade(pid, good_id, qty))


func get_player_customs_graft_until_day() -> int:
	if is_at_sea():
		return 0
	return int(_player_toll_graft_until.get(str(player_port_id), 0))


func player_docked_port_has_tolls() -> bool:
	if is_at_sea():
		return false
	return _port_any_toll(player_port_id)


func get_player_customs_graft_coin_cost() -> int:
	if is_at_sea():
		return 999999
	return clampi(14 + 4 * _port_count_positive_tolls(player_port_id), 20, 120)


func player_try_customs_graft() -> bool:
	if is_at_sea():
		return false
	var ps := str(player_port_id)
	if not _port_names.has(ps) or not _port_any_toll(ps):
		return false
	if _player_has_toll_graft(ps):
		return true
	var n_tolls: int = _port_count_positive_tolls(ps)
	var cost: int = clampi(14 + 4 * n_tolls, 20, 120)
	if player_money < cost:
		return false
	player_money -= cost
	var du: int = _rng.randi_range(_TOLL_BRIBE_DAYS_MIN, _TOLL_BRIBE_DAYS_MAX)
	_player_toll_graft_until[ps] = current_day + du - 1
	_bump_port_for_toll_receipt(ps, maxi(1, cost / 2))
	_bump_player_port_civic_reputation_01(ps, -_LOCAL_PORT_CIVIC_GRAFT_HIT)
	money_changed.emit()
	market_changed.emit()
	return true


## Each entry: id, name, port_qty, buy_unit (player pays), sell_unit (player receives), need_tier (optional)
func list_goods_for_trade() -> Array:
	var out: Array = []
	if is_at_sea():
		return out
	var pid := player_port_id
	for good_id in _goods.keys():
		var gid := str(good_id)
		var gd: Dictionary = _goods[gid]
		out.append(
			{
				"id": gid,
				"name": str(gd.get("name", gid)),
				"port_qty": _port_stock_qty(pid, gid),
				"buy_unit": _compute_player_buy_unit(pid, gid),
				"sell_unit": _compute_player_sell_unit(pid, gid),
				"toll_import_per_unit": _port_toll_per_unit(pid, gid),
				"need_tier": _need_tier_for_good(gid),
			}
		)
	out.sort_custom(func(a: Dictionary, b: Dictionary) -> bool: return str(a.name) < str(b.name))
	return out


func player_port_has_mint() -> bool:
	return (not is_at_sea()) and _port_mint_cfg.has(str(player_port_id))


func get_player_mint_dock_summary() -> String:
	if is_at_sea():
		return ""
	var ps := str(player_port_id)
	if not _port_mint_cfg.has(ps):
		return ""
	var cfg: Dictionary = _port_mint_cfg[ps] as Dictionary
	var gb: int = clampi(int(cfg.get("gold_per_batch", 1)), 0, 24)
	var sb: int = clampi(int(cfg.get("silver_per_batch", 2)), 0, 36)
	var cpb: int = clampi(int(cfg.get("coins_per_batch", 72)), 1, 500)
	return (
		"Civic mint: strike from your hold (%d gold + %d silver → ~%dc; small quaestor fee stays in the port)."
		% [gb, sb, cpb]
	)


func player_can_strike_mint_batch_from_cargo() -> bool:
	if is_at_sea():
		return false
	var ps := str(player_port_id)
	if not _port_mint_cfg.has(ps):
		return false
	if not _goods.has("gold") or not _goods.has("silver"):
		return false
	var cfg: Dictionary = _port_mint_cfg[ps] as Dictionary
	var gb: int = clampi(int(cfg.get("gold_per_batch", 1)), 0, 24)
	var sb: int = clampi(int(cfg.get("silver_per_batch", 2)), 0, 36)
	if gb > 0 and get_player_cargo_qty("gold") < gb:
		return false
	if sb > 0 and get_player_cargo_qty("silver") < sb:
		return false
	return true


func try_player_strike_mint_batch_from_cargo() -> bool:
	if not player_can_strike_mint_batch_from_cargo():
		return false
	var ps := str(player_port_id)
	var cfg: Dictionary = _port_mint_cfg[ps] as Dictionary
	var gb: int = clampi(int(cfg.get("gold_per_batch", 1)), 0, 24)
	var sb: int = clampi(int(cfg.get("silver_per_batch", 2)), 0, 36)
	var cpb: int = clampi(int(cfg.get("coins_per_batch", 72)), 1, 500)
	if gb > 0:
		_adjust_player_cargo_delta("gold", -gb)
	if sb > 0:
		_adjust_player_cargo_delta("silver", -sb)
	var fee: int = maxi(1, cpb / 22)
	var net: int = maxi(0, cpb - fee)
	player_money = clampi(player_money + net, 0, _MAX_PURSE_COINS)
	_bump_port_wealth(ps, fee)
	_bump_player_port_civic_reputation_01(ps, _LOCAL_PORT_CIVIC_MINT_BUMP)
	money_changed.emit()
	cargo_changed.emit()
	market_changed.emit()
	return true


## Each entry: { "id", "days", "name", "route" } — any port; days/route from coastal vs bold shortcut vs open-sea fallback.
func list_destinations() -> Array:
	var out: Array = []
	if is_at_sea():
		return out
	if str(player_voyage_role) == _VOYAGE_ROLE_ESCORT:
		return out
	var from_id := player_port_id
	for pk in _port_names.keys():
		var to_id := str(pk)
		if to_id == from_id:
			continue
		var plan: Dictionary = _voyage_plan(from_id, to_id, player_voyage_risk_aversion)
		var d: int = int(plan.get("days", -1))
		if d < 0:
			continue
		var row: Dictionary = _player_ship_row()
		var vm: float = clampf(float(row.get("voyage_day_mult", 1.0)), 0.45, 2.2)
		d = maxi(1, int(ceil(float(d) * vm)))
		out.append(
			{
				"id": to_id,
				"days": d,
				"name": get_port_name(to_id),
				"route": str(plan.get("route_label", "")),
			}
		)
	out.sort_custom(func(a: Dictionary, b: Dictionary) -> bool: return str(a.name) < str(b.name))
	return out


func _player_market_prev_key(port_id: String, good_id: String) -> String:
	return "%s|%s" % [str(port_id), str(good_id)]


func _player_quay_reliability_percent(port_id: String) -> int:
	var ps := str(port_id)
	if not _port_names.has(ps):
		return 55
	var loc: float = _get_player_port_civic_reputation_01(ps)
	var base: int = clampi(int(round(lerpf(62.0, 94.0, loc))), 50, 96)
	var pulse: float = clampf(float(_port_commerce_pulse.get(ps, 0.4)), 0.0, 1.0)
	var bump: int = int(round((pulse - 0.4) * 10.0))
	return clampi(base + bump, 48, 97)


func _player_ledger_build_per_good_snapshot(port_id: String) -> Dictionary:
	var out: Dictionary = {}
	var ps := str(port_id)
	if not _port_names.has(ps):
		return out
	for gid_key in _goods.keys():
		var gid := str(gid_key)
		var gd: Dictionary = _goods[gid] as Dictionary
		out[gid] = {
			"name": str(gd.get("name", gid)),
			"buy": maxi(0, _compute_player_buy_unit(ps, gid)),
			"sell": maxi(0, _compute_player_sell_unit(ps, gid)),
			"toll": maxi(0, _port_toll_per_unit(ps, gid)),
		}
	return out


func _player_record_ledger_snapshot(port_id: String) -> void:
	var ps := str(port_id)
	if not _port_names.has(ps) or not _goods.has("grain"):
		return
	var per_good: Dictionary = _player_ledger_build_per_good_snapshot(ps)
	var buy_g: int = _compute_player_buy_unit(ps, "grain")
	var sell_g: int = _compute_player_sell_unit(ps, "grain")
	var rel: float = clampf(float(_player_quay_reliability_percent(ps)) / 100.0, 0.0, 1.0)
	_player_ledger_by_port[ps] = {
		"day": current_day,
		"grain_buy": buy_g,
		"grain_sell": sell_g,
		"source": "observed market",
		"reliability": rel,
		"per_good": per_good,
	}


## Poor merchants still hear distant quay prices; seed once so the ledger is not blank before the first nightfall log.
## Returns true if any row was written.
func _player_seed_opening_ledger_hearsay_if_empty() -> bool:
	if not _player_ledger_by_port.is_empty():
		return false
	if not _goods.has("grain"):
		return false
	var home := str(player_port_id)
	if not _port_names.has(home):
		return false
	for pk in _port_names.keys():
		var ps := str(pk)
		if not _port_names.has(ps):
			continue
		var per_good: Dictionary = _player_ledger_build_per_good_snapshot(ps)
		var buy_g: int = _compute_player_buy_unit(ps, "grain")
		var sell_g: int = _compute_player_sell_unit(ps, "grain")
		var note_day: int
		var src: String
		var rel: float
		if ps == home:
			note_day = maxi(1, current_day)
			src = "home quay · remembered cargoes (book opened here)"
			rel = clampf(0.74 + 0.01 * float(abs(home.hash()) % 9), 0.62, 0.86)
		else:
			note_day = maxi(1, current_day - 4 - (abs(ps.hash()) % 16))
			src = "coastal prices · sailor & chandler talk (unvouched)"
			rel = clampf(0.52 + 0.012 * float(abs(ps.hash()) % 11), 0.42, 0.68)
		_player_ledger_by_port[ps] = {
			"day": note_day,
			"grain_buy": buy_g,
			"grain_sell": sell_g,
			"source": src,
			"reliability": rel,
			"per_good": per_good,
		}
	return true


## Call at the **start** of advance_day (before day++): yesterday's ask curve for trend after the tick.
func _player_snapshot_market_buy_prev_before_day_roll() -> void:
	if is_at_sea():
		return
	var ps := str(player_port_id)
	if not _port_names.has(ps):
		return
	for good_id in _goods.keys():
		var gid := str(good_id)
		var buyu: int = _compute_player_buy_unit(ps, gid)
		_player_market_buy_prev[_player_market_prev_key(ps, gid)] = buyu


## Rows for evidence-aware market UI. Docked current port only.
func list_player_market_table_rows() -> Array:
	var out: Array = []
	if is_at_sea():
		return out
	var ps := str(player_port_id)
	if not _port_names.has(ps):
		return out
	for row in list_goods_for_trade():
		var d: Dictionary = row
		var gid := str(d.get("id", ""))
		if gid.is_empty():
			continue
		var buyu: int = int(d.get("buy_unit", 0))
		var prev_key: String = _player_market_prev_key(ps, gid)
		var prev_v: int = int(_player_market_buy_prev.get(prev_key, -1))
		var trend: String = "—"
		if prev_v >= 0:
			var diff: int = buyu - prev_v
			var th: int = maxi(1, prev_v / 40)
			if absi(diff) <= th:
				trend = "stable"
			elif diff > 0:
				trend = "rising"
			else:
				trend = "falling"
		var last_td: int = int(_player_good_last_trade_day.get(gid, 0))
		var age_days: int = 0 if last_td <= 0 else maxi(0, current_day - last_td)
		var src: String = "observed quay · clerk scales"
		if last_td > 0:
			src += " · last trade %dd ago" % age_days
		var rel_pct: int = _player_quay_reliability_percent(ps)
		out.append(
			{
				"good_id": gid,
				"name": str(d.get("name", gid)),
				"port_qty": int(d.get("port_qty", 0)),
				"buy_unit": buyu,
				"sell_unit": int(d.get("sell_unit", 0)),
				"toll_per_unit": int(d.get("toll_import_per_unit", 0)),
				"trend": trend,
				"source": src,
				"age_days": age_days,
				"reliability_pct": rel_pct,
			}
		)
	return out


## One row per convoy line (single design today); numbers are slip-side readouts.
func list_player_harbor_ship_rows() -> Array:
	var out: Array = []
	var row: Dictionary = _player_ship_row()
	var vm: float = clampf(float(row.get("voyage_day_mult", 1.0)), 0.45, 2.2)
	var speed_score: int = clampi(int(round((2.2 - vm) / 1.75 * 100.0)), 12, 92)
	var storm_m: float = clampf(float(row.get("storm_probability_mul", 1.0)), 0.55, 1.45)
	var risk_word: String = "low"
	if storm_m >= 1.12:
		risk_word = "high storm exposure"
	elif storm_m >= 1.02:
		risk_word = "moderate storms"
	var crew_note: String = "wine every %d d" % _SHIP_CREW_WINE_EVERY_N_DAYS
	out.append(
		{
			"ship": get_player_ship_display_name(),
			"cargo": "%d/%d" % [get_player_cargo_used(), get_player_cargo_capacity()],
			"speed_score": speed_score,
			"condition": clampi(player_ship_condition, _SHIP_CONDITION_MIN, _SHIP_CONDITION_MAX),
			"crew_note": crew_note,
			"risk": risk_word,
			"captain": str(player_captain_culture),
			"status": "under way" if is_at_sea() else "in harbor",
			"fleet_ships": clampi(player_fleet_ships, 1, _FLEET_MAX_SHIPS),
		}
	)
	return out


func list_player_influence_metrics() -> Array:
	var out: Array = []
	if is_at_sea():
		return out
	var ps := str(player_port_id)
	if not _port_names.has(ps):
		return out
	var loc_pct: int = clampi(int(round(_get_player_port_civic_reputation_01(ps) * 100.0)), 0, 100)
	out.append(
		{
			"metric": "Official access",
			"value": "%d%%" % loc_pct,
			"source": "harbor register + last quaestor contact",
			"age_days": 0,
			"reliability_pct": clampi(72 + mini(18, loc_pct / 7), 55, 95),
		}
	)
	var temple_pts: int = clampi(int(round(player_temple_offerings_rep_granted_01 * 100.0)), 0, 100)
	out.append(
		{
			"metric": "Temple standing",
			"value": "%d" % temple_pts,
			"source": "offering records (lifetime face bought)",
			"age_days": 0,
			"reliability_pct": 88,
		}
	)
	var wide_pct: int = clampi(int(round(player_civic_reputation_01 * 100.0)), 0, 100)
	var crop_age: int = (
		maxi(0, current_day - player_crop_intel_update_day) if player_crop_intel_port_id == ps else 7
	)
	out.append(
		{
			"metric": "Quay-wide name",
			"value": "%d%%" % wide_pct,
			"source": "cross-port gossip",
			"age_days": crop_age,
			"reliability_pct": clampi(55 + wide_pct / 5, 45, 82),
		}
	)
	var unrest: int = get_port_food_unrest(ps)
	var dep: int = clampi(unrest / 2, 0, 100)
	out.append(
		{
			"metric": "City strain (food mood)",
			"value": "%d" % dep,
			"source": "public granary mood (not field truth)",
			"age_days": 0,
			"reliability_pct": clampi(60 + (100 - mini(unrest, 120)) / 8, 40, 90),
		}
	)
	return out


## Narrative block backing City → Influence table.
func get_player_city_relationship_block() -> String:
	if is_at_sea():
		return "No city relationship sheet while the hull is at sea."
	var lines: PackedStringArray = []
	for row in list_player_influence_metrics():
		var d: Dictionary = row
		lines.append(
			"%s — %s (%s · %dd · ~%d%% confidence)"
			% [
				str(d.get("metric", "")),
				str(d.get("value", "")),
				str(d.get("source", "")),
				int(d.get("age_days", 0)),
				int(d.get("reliability_pct", 0)),
			]
		)
	lines.append(
		"Temple and quaestor actions live here; mint strikes and toll gifts stay lawful but shift how clerks read you."
	)
	return "\n".join(lines)


func list_player_ledger_rows() -> Array:
	var out: Array = []
	for pid in _port_names.keys():
		var ps := str(pid)
		if not _player_ledger_by_port.has(ps):
			continue
		var cell: Dictionary = _player_ledger_by_port[ps] as Dictionary
		var day0: int = clampi(int(cell.get("day", 0)), 0, 9999999)
		var age: int = maxi(0, current_day - day0)
		var gb: int = maxi(0, int(cell.get("grain_buy", 0)))
		var gs: int = maxi(0, int(cell.get("grain_sell", 0)))
		var lo: int = mini(gb, gs)
		var hi: int = maxi(gb, gs)
		var rel: float = clampf(float(cell.get("reliability", 0.72)), 0.0, 1.0)
		var rel_pct: int = clampi(int(round(rel * 100.0)), 0, 100)
		var risk: String = _food_unrest_tier_label(get_port_food_unrest(ps))
		var chart_aid: String = get_port_chart_area_id(ps)
		out.append(
			{
				"port_id": ps,
				"name": get_port_name(ps),
				"chart_area_id": chart_aid,
				"chart_area_name": get_chart_area_display_name(chart_aid),
				"last_day": day0,
				"age_days": age,
				"grain_range": ("%d–%d" % [lo, hi]) if lo > 0 or hi > 0 else "—",
				"source": str(cell.get("source", "unknown")),
				"reliability_pct": rel_pct,
				"risk_hint": risk,
			}
		)
	out.sort_custom(func(a: Dictionary, b: Dictionary) -> bool: return int(a.get("age_days", 999)) < int(b.get("age_days", 999)))
	return out


func list_player_ledger_chart_areas() -> Array:
	var counts: Dictionary = {}
	for row in list_player_ledger_rows():
		var aid := str(row.get("chart_area_id", _LEDGER_CHART_AREA_FALLBACK))
		counts[aid] = int(counts.get(aid, 0)) + 1
	var keys: Array = counts.keys()
	keys.sort_custom(func(a, b): return get_chart_area_display_name(str(a)) < get_chart_area_display_name(str(b)))
	var out: Array = []
	for aid_v in keys:
		var aid := str(aid_v)
		out.append(
			{
				"area_id": aid,
				"area_name": get_chart_area_display_name(aid),
				"known_ports": int(counts[aid]),
			}
		)
	return out


func list_player_ledger_ports_for_chart_area(area_id: String) -> Array:
	var want := str(area_id)
	var out: Array = []
	for row in list_player_ledger_rows():
		if str(row.get("chart_area_id", _LEDGER_CHART_AREA_FALLBACK)) != want:
			continue
		out.append(row)
	out.sort_custom(func(a: Dictionary, b: Dictionary) -> bool: return str(a.get("name", "")) < str(b.get("name", "")))
	return out


func list_player_ledger_goods_for_port(port_id: String) -> Array:
	var out: Array = []
	var ps := str(port_id)
	if not _port_names.has(ps) or not _player_ledger_by_port.has(ps):
		return out
	var cell: Dictionary = _player_ledger_by_port[ps] as Dictionary
	var day0: int = clampi(int(cell.get("day", 0)), 0, 9999999)
	var age_notes: int = maxi(0, current_day - day0)
	var rel_pct: int = clampi(
		int(round(clampf(float(cell.get("reliability", 0.72)), 0.0, 1.0) * 100.0)), 0, 100
	)
	var pg: Variant = cell.get("per_good", null)
	if typeof(pg) == TYPE_DICTIONARY and not (pg as Dictionary).is_empty():
		var tmp: Array = []
		for gk in (pg as Dictionary).keys():
			var gids := str(gk)
			if not _goods.has(gids):
				continue
			var rv: Variant = (pg as Dictionary)[gk]
			if typeof(rv) != TYPE_DICTIONARY:
				continue
			var rd: Dictionary = rv as Dictionary
			var nm: String = str(rd.get("name", str((_goods[gids] as Dictionary).get("name", gids))))
			tmp.append(
				{
					"good_id": gids,
					"name": nm,
					"buy_unit": maxi(0, int(rd.get("buy", 0))),
					"sell_unit": maxi(0, int(rd.get("sell", 0))),
					"toll_per_unit": maxi(0, int(rd.get("toll", 0))),
					"note_day": day0,
					"ledger_age_days": age_notes,
					"reliability_pct": rel_pct,
				}
			)
		tmp.sort_custom(func(a: Dictionary, b: Dictionary) -> bool: return str(a.get("name", "")) < str(b.get("name", "")))
		for t in tmp:
			out.append(t)
	elif _goods.has("grain"):
		var gb: int = maxi(0, int(cell.get("grain_buy", 0)))
		var gs: int = maxi(0, int(cell.get("grain_sell", 0)))
		out.append(
			{
				"good_id": "grain",
				"name": str((_goods["grain"] as Dictionary).get("name", "Grain")),
				"buy_unit": gb,
				"sell_unit": gs,
				"toll_per_unit": maxi(0, _port_toll_per_unit(ps, "grain")),
				"note_day": day0,
				"ledger_age_days": age_notes,
				"reliability_pct": rel_pct,
			}
		)
	return out


func get_player_ledger_block() -> String:
	var rows: Array = list_player_ledger_rows()
	if rows.is_empty():
		return "Ledger is empty — your purser only records harbors where you have closed a day ashore since this book was bound."
	var lines: PackedStringArray = []
	for r in rows:
		var d: Dictionary = r
		lines.append(
			"%s — %dd ago — grain ask band %s — %s (~%d%%)"
			% [
				str(d.get("name", "")),
				int(d.get("age_days", 0)),
				str(d.get("grain_range", "")),
				str(d.get("source", "")),
				int(d.get("reliability_pct", 0)),
			]
		)
	return "\n".join(lines)


## One line for compact UI; full prose lives in `get_player_ledger_block()` (e.g. log export).
func get_player_ledger_summary_line() -> String:
	var rows: Array = list_player_ledger_rows()
	if rows.is_empty():
		return "Libellum is empty — your purser has no harbor lines yet."
	var areas_n: int = list_player_ledger_chart_areas().size()
	return "%d harbor(s) across %d chart area(s); grain band per harbor is in tooltips and in the grain row below." % [
		rows.size(),
		maxi(1, areas_n),
	]


func list_player_tavern_rumor_rows() -> Array:
	var out: Array = []
	if is_at_sea():
		return out
	var ps := str(player_port_id)
	if not _port_names.has(ps):
		return out
	if _world_crop_agro_model and _goods.has("grain"):
		_ensure_player_crop_intel_port_sync()
		var crop_age: int = maxi(0, current_day - player_crop_intel_update_day)
		out.append(
			{
				"id": "crop_notebook",
				"summary": "Grain trade mood in this harbor (your notebook)",
				"area": get_port_name(ps),
				"age_days": crop_age,
				"reliability_pct": get_player_crop_intel_confidence_percent(),
				"verify_cost": get_player_crop_intel_investigate_coin_cost(),
				"intel_kind": "crop",
			}
		)
	var wr: float = clampf(float(_port_war_rumor.get(ps, 0.0)), 0.0, 1.0)
	if wr > 0.04:
		var war_age: int = maxi(0, current_day - player_war_intel_update_day)
		out.append(
			{
				"id": "war_quay",
				"summary": "Neighbour-war fear on this quay (~%d%%)" % int(round(wr * 100.0)),
				"area": get_port_name(ps),
				"age_days": war_age,
				"reliability_pct": get_player_war_intel_confidence_percent(),
				"verify_cost": get_player_war_intel_investigate_coin_cost(),
				"intel_kind": "war",
			}
		)
	var sc_stats: Vector2i = _npc_scattered_convoy_tail_stats()
	if sc_stats.x > 0:
		var pir_age: int = maxi(0, current_day - _player_route_intel_refresh_day)
		out.append(
			{
				"id": "pirate_scuttlebutt",
				"summary": "Pirate and convoy-break talk (%d masters still in the wind)" % sc_stats.x,
				"area": "wine hall",
				"age_days": pir_age,
				"reliability_pct": clampi(48 + mini(30, sc_stats.x * 2), 38, 78),
				"verify_cost": _PLAYER_INTEL_PIRACY_SCUTTLEBUTT_COINS,
				"intel_kind": "piracy",
			}
		)
	out.append(
		{
			"id": "route_clerks",
			"summary": "Harbor clerks can re-measure open-sea exposure on your working charts",
			"area": get_port_name(ps),
			"age_days": maxi(0, current_day - _player_route_intel_refresh_day),
			"reliability_pct": 58,
			"verify_cost": _PLAYER_INTEL_ROUTES_REFRESH_COINS,
			"intel_kind": "routes",
		}
	)
	return out


## Pay for sharper tables or investigations. `branch`: crop | war | routes | piracy
func try_player_buy_intel(branch: String) -> bool:
	var b := str(branch).to_lower()
	match b:
		"crop":
			return try_player_investigate_crop_market_intel()
		"war":
			return try_player_investigate_war_rumor_intel()
		"routes":
			if is_at_sea():
				return false
			if player_money < _PLAYER_INTEL_ROUTES_REFRESH_COINS:
				return false
			player_money = clampi(player_money - _PLAYER_INTEL_ROUTES_REFRESH_COINS, 0, _MAX_PURSE_COINS)
			_player_route_intel_refresh_day = current_day
			money_changed.emit()
			market_changed.emit()
			return true
		"piracy":
			if is_at_sea():
				return false
			if player_money < _PLAYER_INTEL_PIRACY_SCUTTLEBUTT_COINS:
				return false
			player_money = clampi(player_money - _PLAYER_INTEL_PIRACY_SCUTTLEBUTT_COINS, 0, _MAX_PURSE_COINS)
			_player_route_intel_refresh_day = current_day
			money_changed.emit()
			market_changed.emit()
			return true
		_:
			return false


func get_player_intel_verify_coin_cost(intel_kind: String) -> int:
	match str(intel_kind).to_lower():
		"crop":
			return get_player_crop_intel_investigate_coin_cost()
		"war":
			return get_player_war_intel_investigate_coin_cost()
		"piracy":
			return _PLAYER_INTEL_PIRACY_SCUTTLEBUTT_COINS
		"routes":
			return _PLAYER_INTEL_ROUTES_REFRESH_COINS
		_:
			return 0


## Explain why a cell shows what it shows. `kind`: market_good | influence | ledger | ledger_good | route | harbor
func get_player_data_provenance(kind: String, key: String) -> String:
	var k := str(kind).to_lower()
	var idk := str(key)
	match k:
		"market_good":
			if not _goods.has(idk):
				return "No market row for that good."
			var ps := str(player_port_id)
			var rel: int = _player_quay_reliability_percent(ps)
			var last_td: int = int(_player_good_last_trade_day.get(idk, 0))
			var age: String = "never traded here" if last_td <= 0 else "%d days since your last hold trade" % maxi(0, current_day - last_td)
			return (
				"Prices are what the harbor clerks show on their tablets today — not the countryside's secret granary count. "
				+ "Reliability (~%d%%) rises when local quaestors tolerate you; your own trades sharpen how you read the scales. "
				% rel
				+ " "
				+ age
				+ "."
			)
		"influence":
			return "Influence numbers blend registers you have seen, temple vow marks, and gossip age — they are not omniscient faction meters."
		"ledger":
			if not _port_names.has(idk):
				return "Unknown port."
			if not _player_ledger_by_port.has(idk):
				return "No purser entry yet — spend a night in that harbor after markets close to log prices."
			var cell: Dictionary = _player_ledger_by_port[idk] as Dictionary
			var src_s: String = str(cell.get("source", "observed"))
			if src_s.findn("unvouched") >= 0 or src_s.findn("remembered cargoes") >= 0:
				return (
					"Notebook line from wagons and slips before this book was bound — grain bands are tavern chalk and "
					+ "incoming masters' boasting until you log a night ashore with clerk-counted prices (%s)."
					% src_s
				)
			return (
				"Snapshot from nightfall on day %d: grain ask/bid as your purser heard them (%s)."
				% [int(cell.get("day", 0)), src_s]
			)
		"ledger_good":
			var bar: int = idk.find("|")
			if bar <= 0 or bar >= idk.length() - 1:
				return "Use port_id|good_id as the key."
			var port_lg: String = idk.substr(0, bar)
			var good_lg: String = idk.substr(bar + 1)
			if not _goods.has(good_lg):
				return "Unknown good."
			if not _player_ledger_by_port.has(port_lg):
				return "No ledger line for that harbor."
			var cellg: Dictionary = _player_ledger_by_port[port_lg] as Dictionary
			var src_g: String = str(cellg.get("source", "observed"))
			var gnm: String = str((_goods[good_lg] as Dictionary).get("name", good_lg))
			if src_g.findn("unvouched") >= 0 or src_g.findn("remembered cargoes") >= 0:
				return (
					"%s in %s — numbers come from the same ledger line as the harbor summary (hearsay or night log); "
					% [gnm, get_port_name(port_lg)]
					+ "they are not today’s live clerk tablet unless you are docked there after a fresh advance (%s)."
					% src_g
				)
			return (
				"%s in %s — logged with the nightfall snapshot on day %d (%s)."
				% [gnm, get_port_name(port_lg), int(cellg.get("day", 0)), src_g]
			)
			if not _port_names.has(idk):
				return "Unknown destination."
			return (
				"Days and route labels come from your current master’s plan at this anchorage; "
				+ "open-sea share sets storm and corsair odds. Paying clerks to re-measure raises declared confidence for a few tides."
			)
		"harbor":
			return "Hull line mixes catalog rig data with what your boatswain sees on the planking — repairs still happen overnight when stores allow."
		_:
			return "No provenance note."


func get_player_route_table() -> Array:
	var out: Array = []
	if is_at_sea() or str(player_voyage_role) == _VOYAGE_ROLE_ESCORT:
		return out
	var from_id := str(player_port_id)
	if not _port_names.has(from_id):
		return out
	var rowh: Dictionary = _player_ship_row()
	var ox: float = clampf(float(rowh.get("open_sea_exposure_mul", 1.0)), 0.55, 1.5)
	for dest in list_destinations():
		var d: Dictionary = dest
		var tid := str(d.get("id", ""))
		if tid.is_empty():
			continue
		var plan: Dictionary = _voyage_plan(from_id, tid, player_voyage_risk_aversion)
		var open0: float = clampf(float(plan.get("open_01", _VOYAGE_COASTAL_OPENNESS)), 0.0, 1.0)
		var open_c: float = clampf(open0 * ox, 0.0, 1.0)
		var risk: String = "low piracy read"
		if open_c > 0.48:
			risk = "higher open-sea / piracy read"
		elif open_c > 0.26:
			risk = "moderate offshore exposure"
		var fresh: int = maxi(0, current_day - _player_route_intel_refresh_day)
		var rel: int = clampi(72 + int((1.0 - open_c) * 22.0) - mini(12, fresh * 2), 38, 93)
		out.append(
			{
				"id": tid,
				"name": str(d.get("name", tid)),
				"days": int(d.get("days", 0)),
				"route": str(d.get("route", "")),
				"risk": risk,
				"data_age_days": fresh,
				"reliability_pct": rel,
				"open_01": open_c,
			}
		)
	return out


func start_voyage(to_port_id: String) -> bool:
	if is_at_sea():
		return false
	if str(player_voyage_role) == _VOYAGE_ROLE_ESCORT:
		return false
	var tid: String = str(to_port_id)
	if tid.is_empty() or not _port_names.has(tid) or tid == player_port_id:
		return false
	var plan: Dictionary = _voyage_plan(player_port_id, tid, player_voyage_risk_aversion)
	var d: int = int(plan.get("days", -1))
	if d < 0:
		return false
	var row: Dictionary = _player_ship_row()
	var vm: float = clampf(float(row.get("voyage_day_mult", 1.0)), 0.45, 2.2)
	d = maxi(1, int(ceil(float(d) * vm)))
	var op0: float = clampf(float(plan.get("open_01", _VOYAGE_COASTAL_OPENNESS)), 0.0, 1.0)
	var ox: float = clampf(float(row.get("open_sea_exposure_mul", 1.0)), 0.55, 1.5)
	voyage_dest_id = tid
	voyage_days_remaining = d
	player_voyage_booked_days = d
	player_voyage_open_sea_01 = clampf(op0 * ox, 0.0, 1.0)
	_transfer_temple_pending_storm_into_active_voyage_bless()
	voyage_started.emit(tid, d)
	return true


func advance_day() -> void:
	_player_snapshot_market_buy_prev_before_day_roll()
	current_day += 1
	_tick_player_reputation_drift_daily()
	_prune_player_toll_graft_expired()
	var was_at_sea: bool = voyage_days_remaining > 0
	if was_at_sea:
		_tick_player_storm_if_at_sea()
		if str(player_voyage_role) == _VOYAGE_ROLE_MERCHANT:
			_tick_player_pirate_encounter_if_at_sea()
	var escorting: bool = str(player_voyage_role) == _VOYAGE_ROLE_ESCORT and voyage_days_remaining > 0
	if voyage_days_remaining > 0 and not escorting:
		voyage_days_remaining -= 1
		if voyage_days_remaining == 0:
			player_port_id = voyage_dest_id
			voyage_dest_id = ""
			player_voyage_booked_days = 0
			player_voyage_open_sea_01 = 0.0
			player_voyage_weather_bless_p_sub = 0.0
			_apply_player_escort_contract_on_voyage_arrival()
			voyage_completed.emit(player_port_id)
	_tick_player_ship_and_crew(was_at_sea)
	_run_daily_population_and_npcs()
	if escorting:
		_sync_player_escort_with_employer_after_npc_advance()
	if not _pending_player_encounter_msg.is_empty():
		var pem: String = _pending_player_encounter_msg
		_pending_player_encounter_msg = ""
		player_encounter_report.emit(pem)
	if not is_at_sea():
		var pid_hd: String = player_port_id
		var traffic_hd: int = _count_npc_docked_at(pid_hd) + 1
		var take_hd: int = _take_harbour_due_from_purse(player_money, clampi(player_fleet_ships, 1, _FLEET_MAX_SHIPS))
		if take_hd > 0:
			player_money = clampi(player_money - take_hd, 0, _MAX_PURSE_COINS)
			_harbour_due_port_wealth_bump(pid_hd, take_hd, traffic_hd)
			money_changed.emit()
		var rowp: Dictionary = _player_ship_row()
		var oph_p: int = maxi(1, int(rowp.get("officer_pay_per_hull", 1)))
		var cap_pay: Dictionary = {
			"money": player_money,
			"cargo": player_cargo,
			"ship_condition": player_ship_condition,
			"ship_wine_counter": player_ship_wine_counter,
			"fleet_ships": clampi(player_fleet_ships, 1, _FLEET_MAX_SHIPS),
			"officer_pay_scale": float(oph_p) * _player_cultural_ops_scale(),
		}
		_tick_captain_officer_pay(cap_pay, true)
		player_money = clampi(int(cap_pay.get("money", 0)), 0, _MAX_PURSE_COINS)
		player_ship_condition = clampi(
			int(cap_pay.get("ship_condition", _SHIP_CONDITION_MAX)),
			_SHIP_CONDITION_MIN,
			_SHIP_CONDITION_MAX,
		)
	if not is_at_sea():
		_player_record_ledger_snapshot(str(player_port_id))
	player_ship_age_days = mini(999999, player_ship_age_days + 1)
	day_advanced.emit(current_day)


func save_campaign() -> bool:
	var packed := {
		"save_version": SAVE_VERSION,
		"current_day": current_day,
		"player_port_id": player_port_id,
		"voyage_dest_id": voyage_dest_id,
		"voyage_days_remaining": voyage_days_remaining,
		"player_voyage_booked_days": clampi(player_voyage_booked_days, 0, 999),
		"player_voyage_open_sea_01": clampf(player_voyage_open_sea_01, 0.0, 1.0),
		"player_voyage_risk_aversion": clampf(player_voyage_risk_aversion, 0.0, 1.0),
		"player_ship_class_id": str(get_player_ship_class_id()),
		"player_captain_culture": str(player_captain_culture),
		"player_ship_age_days": clampi(player_ship_age_days, 0, 999999),
		"player_voyage_role": str(player_voyage_role),
		"player_escort_contract": player_escort_contract.duplicate(true),
		"player_offers_convoy_escort": player_offers_convoy_escort,
		"player_crop_intel_port_id": str(player_crop_intel_port_id),
		"player_crop_intel_mean_01": clampf(player_crop_intel_mean_01, 0.0, 1.0),
		"player_crop_intel_sigma_01": clampf(player_crop_intel_sigma_01, 0.0, 1.0),
		"player_crop_intel_update_day": clampi(player_crop_intel_update_day, 0, 9999999),
		"player_war_intel_port_id": str(player_war_intel_port_id),
		"player_war_intel_mean_01": clampf(player_war_intel_mean_01, 0.0, 1.0),
		"player_war_intel_sigma_01": clampf(player_war_intel_sigma_01, 0.0, 1.0),
		"player_war_intel_update_day": clampi(player_war_intel_update_day, 0, 9999999),
		"player_civic_reputation_01": clampf(player_civic_reputation_01, 0.0, 1.0),
		"player_port_civic_reputation_01": player_port_civic_reputation_01.duplicate(true),
		"player_voyage_weather_bless_p_sub": clampf(player_voyage_weather_bless_p_sub, 0.0, _TEMPLE_STORM_PENDING_P_SUB_TOTAL_CAP),
		"player_temple_pending_storm_p_sub": clampf(player_temple_pending_storm_p_sub, 0.0, _TEMPLE_STORM_PENDING_P_SUB_TOTAL_CAP),
		"player_temple_offerings_rep_granted_01": clampf(player_temple_offerings_rep_granted_01, 0.0, _TEMPLE_REP_LIFETIME_CAP),
		"player_money": player_money,
		"world_treasury_coins": clampi(_world_treasury_coins, 0, _WORLD_TREASURY_MAX),
		"player_toll_graft_until": _player_toll_graft_until.duplicate(true),
		"player_cargo": player_cargo.duplicate(true),
		"port_stocks": _serialize_port_stocks(),
		"npc_agents": _serialize_npc_agents(),
		"port_wealth": _serialize_port_wealth(),
		"port_food_unrest": _serialize_port_food_unrest(),
		"port_war_days_remaining": _serialize_port_war_days_remaining(),
		"port_war_recurring": _serialize_port_war_recurring(),
		"port_war_peace_remaining": _serialize_port_war_peace_remaining(),
		"port_war_burst_initial": _serialize_port_war_burst_initial(),
		"port_war_pending_burst": _serialize_port_int_map(_port_war_pending_burst),
		"port_population_grain": _serialize_port_population_grain(),
		"port_population_wine_base": _serialize_port_population_wine_base(),
		"port_population_grain_baseline": _serialize_port_population_grain_baseline(),
		"port_population_grain_cap": _serialize_port_population_grain_cap(),
		"port_famine_streak_days": _serialize_port_famine_streak_days(),
		"port_consecutive_grain_full_ration_days": _serialize_port_int_map(_port_consecutive_grain_full_ration_days),
		"port_consecutive_grain_zero_eat_days": _serialize_port_int_map(_port_consecutive_grain_zero_eat_days),
		"port_crop_agro": _serialize_port_crop_agro(),
		"port_prosperity_streak_days": _serialize_port_prosperity_streak_days(),
		"port_rationing_active": _serialize_port_rationing_active(),
		"port_rationing_days_active": _serialize_port_int_map(_port_rationing_days_active),
		"port_preserved_food": _serialize_port_float_map(_port_preserved_food),
		"player_ship_condition": clampi(player_ship_condition, _SHIP_CONDITION_MIN, _SHIP_CONDITION_MAX),
		"player_ship_wine_counter": clampi(player_ship_wine_counter, 0, 9999),
		"player_fleet_ships": clampi(player_fleet_ships, 1, _FLEET_MAX_SHIPS),
		"player_fleet_shipyard_days_remaining": clampi(player_fleet_shipyard_days_remaining, 0, 999),
		"player_fleet_shipyard_port_id": str(player_fleet_shipyard_port_id),
		"used_hull_listings": _serialize_used_hull_listings(),
		"used_hull_listing_next_id": _next_used_hull_listing_id,
		"port_commerce_pulse": _serialize_port_float_map(_port_commerce_pulse),
		"port_cartel_strength": _serialize_port_float_map(_port_cartel_strength),
		"port_war_rumor": _serialize_port_float_map(_port_war_rumor),
		"port_plague_days": _serialize_port_int_map(_port_plague_days),
		"port_rumor_good_delta": _serialize_port_nested_float_map(_port_rumor_good_delta),
		"port_local_crop_belief_01": _serialize_port_float_map(_port_local_crop_belief_01),
		"port_crop_inbound_reports": _serialize_port_crop_inbound_reports(),
		"port_crop_rumor_public_delta": _serialize_port_float_map(_port_crop_rumor_public_delta),
		"player_ledger_by_port": _serialize_player_ledger_by_port(),
		"player_market_buy_prev": _player_market_buy_prev.duplicate(true),
		"player_good_last_trade_day": _serialize_player_good_last_trade_days(),
		"player_route_intel_refresh_day": clampi(_player_route_intel_refresh_day, 0, 9999999),
	}
	var json_text: String = JSON.stringify(packed, "\t")
	var f = FileAccess.open(SAVE_PATH, FileAccess.WRITE)
	if f == null:
		push_error("HarboursOfPower: cannot write save: %s" % SAVE_PATH)
		return false
	f.store_string(json_text)
	f.close()
	game_saved.emit(SAVE_PATH)
	return true


func load_campaign() -> bool:
	if not FileAccess.file_exists(SAVE_PATH):
		game_load_failed.emit("No save file yet.")
		return false
	var text := FileAccess.get_file_as_string(SAVE_PATH)
	if text.is_empty():
		game_load_failed.emit("Save file is empty.")
		return false
	var data: Variant = JSON.parse_string(text)
	if data == null or typeof(data) != TYPE_DICTIONARY:
		game_load_failed.emit("Save file is corrupt.")
		return false
	var d: Dictionary = data
	_port_peace_riot_grace_days.clear()
	var ver: int = int(d.get("save_version", 0))
	if ver < 1 or ver > SAVE_VERSION:
		game_load_failed.emit("Save is from a different version.")
		return false
	current_day = maxi(1, int(d.get("current_day", 1)))
	player_port_id = str(d.get("player_port_id", player_port_id))
	voyage_dest_id = str(d.get("voyage_dest_id", ""))
	voyage_days_remaining = maxi(0, int(d.get("voyage_days_remaining", 0)))
	player_money = int(d.get("player_money", 0))
	if ver >= 26:
		_world_treasury_coins = clampi(
			int(d.get("world_treasury_coins", _world_initial_treasury_coins)), 0, _WORLD_TREASURY_MAX
		)
	else:
		_world_treasury_coins = clampi(_world_initial_treasury_coins, 0, _WORLD_TREASURY_MAX)
	var cargo_raw: Variant = d.get("player_cargo", {})
	if typeof(cargo_raw) != TYPE_DICTIONARY:
		player_cargo = {}
	else:
		player_cargo = (cargo_raw as Dictionary).duplicate(true)
	if ver >= 28:
		var ptg: Variant = d.get("player_toll_graft_until", null)
		_player_toll_graft_until.clear()
		if typeof(ptg) == TYPE_DICTIONARY:
			for pk in (ptg as Dictionary).keys():
				var pxs2: String = str(pk)
				if _port_names.has(pxs2):
					_player_toll_graft_until[pxs2] = clampi(int((ptg as Dictionary)[pk]), 0, 999999)
	else:
		_player_toll_graft_until.clear()
	if not _port_names.has(player_port_id) and not _port_names.is_empty():
		player_port_id = str(_port_names.keys()[0])
	if voyage_days_remaining > 0 and (voyage_dest_id.is_empty() or not _port_names.has(voyage_dest_id)):
		voyage_days_remaining = 0
		voyage_dest_id = ""
	if ver >= 19:
		player_voyage_booked_days = clampi(int(d.get("player_voyage_booked_days", 0)), 0, 999)
		player_voyage_open_sea_01 = clampf(float(d.get("player_voyage_open_sea_01", 0.0)), 0.0, 1.0)
		player_voyage_risk_aversion = clampf(float(d.get("player_voyage_risk_aversion", 0.48)), 0.0, 1.0)
		if voyage_days_remaining <= 0:
			player_voyage_booked_days = 0
			player_voyage_open_sea_01 = 0.0
	else:
		player_voyage_risk_aversion = 0.48
		if voyage_days_remaining > 0 and not voyage_dest_id.is_empty() and _port_names.has(voyage_dest_id):
			player_voyage_booked_days = maxi(voyage_days_remaining, 1)
			var pl0: Dictionary = _voyage_plan(player_port_id, voyage_dest_id, player_voyage_risk_aversion)
			player_voyage_open_sea_01 = clampf(float(pl0.get("open_01", 0.22)), 0.0, 1.0)
		else:
			player_voyage_booked_days = 0
			player_voyage_open_sea_01 = 0.0
	if ver >= 2:
		var ps: Variant = d.get("port_stocks", null)
		if typeof(ps) == TYPE_DICTIONARY:
			_deserialize_port_stocks(ps as Dictionary)
		else:
			_finalize_port_stocks()
	else:
		_finalize_port_stocks()
	_npc_agents.clear()
	_npc_next_agent_id = 0
	if ver >= 5:
		var na: Variant = d.get("npc_agents", null)
		if typeof(na) == TYPE_ARRAY:
			_deserialize_npc_agents(na as Array)
		else:
			_bootstrap_npc_agents()
	elif ver >= 3:
		var nt: Variant = d.get("npc_traders", null)
		if typeof(nt) == TYPE_DICTIONARY:
			_migrate_old_npc_traders_to_agents(nt as Dictionary)
		else:
			_bootstrap_npc_agents()
	else:
		_bootstrap_npc_agents()
	if ver >= 17:
		var pcp0: Variant = d.get("port_commerce_pulse", null)
		if typeof(pcp0) == TYPE_DICTIONARY:
			_deserialize_port_float_map_into(_port_commerce_pulse, pcp0 as Dictionary, 0.0, 1.0)
		var pcs0: Variant = d.get("port_cartel_strength", null)
		if typeof(pcs0) == TYPE_DICTIONARY:
			_deserialize_port_float_map_into(_port_cartel_strength, pcs0 as Dictionary, 0.0, 1.0)
		var pwr0: Variant = d.get("port_war_rumor", null)
		if typeof(pwr0) == TYPE_DICTIONARY:
			_deserialize_port_float_map_into(_port_war_rumor, pwr0 as Dictionary, 0.0, 1.0)
		var ppd0: Variant = d.get("port_plague_days", null)
		if typeof(ppd0) == TYPE_DICTIONARY:
			_deserialize_port_int_map_into(_port_plague_days, ppd0 as Dictionary, 0, 999)
		var prd0: Variant = d.get("port_rumor_good_delta", null)
		if typeof(prd0) == TYPE_DICTIONARY:
			_deserialize_port_rumor_good_delta(prd0 as Dictionary)
	else:
		_port_commerce_pulse.clear()
		_port_cartel_strength.clear()
		_port_war_rumor.clear()
		_port_plague_days.clear()
		_port_rumor_good_delta.clear()
	_ensure_sim_agent_port_defaults()
	_ensure_npc_counts_match_config()
	if ver >= 4:
		var pw: Variant = d.get("port_wealth", null)
		if typeof(pw) == TYPE_DICTIONARY:
			_deserialize_port_wealth(pw as Dictionary)
		else:
			_init_port_wealth_baseline()
	else:
		_init_port_wealth_baseline()
	if ver >= 6:
		var fu: Variant = d.get("port_food_unrest", null)
		if typeof(fu) == TYPE_DICTIONARY:
			_deserialize_port_food_unrest(fu as Dictionary)
		else:
			_init_port_food_unrest_zero()
	else:
		_init_port_food_unrest_zero()
	if ver >= 8:
		var wr: Variant = d.get("port_war_days_remaining", null)
		if typeof(wr) == TYPE_DICTIONARY:
			_deserialize_port_war_days_remaining(wr as Dictionary)
		else:
			_ensure_war_days_defaults()
	elif ver == 7:
		_migrate_save_v7_war_to_remaining(d)
	else:
		_ensure_war_days_defaults()
	if ver >= 9:
		var rec: Variant = d.get("port_war_recurring", null)
		if typeof(rec) == TYPE_DICTIONARY:
			_deserialize_port_war_recurring(rec as Dictionary)
		else:
			_ensure_war_recurring_defaults()
		var pe: Variant = d.get("port_war_peace_remaining", null)
		if typeof(pe) == TYPE_DICTIONARY:
			_deserialize_port_war_peace_remaining(pe as Dictionary)
		else:
			_ensure_war_peace_defaults()
	else:
		_ensure_war_recurring_defaults()
		_ensure_war_peace_defaults()
	_port_war_burst_initial.clear()
	if ver >= 10:
		var bi: Variant = d.get("port_war_burst_initial", null)
		if typeof(bi) == TYPE_DICTIONARY:
			_deserialize_port_war_burst_initial(bi as Dictionary)
		else:
			_ensure_war_burst_initial_defaults()
	else:
		_ensure_war_burst_initial_defaults()
	_port_war_pending_burst.clear()
	if ver >= 32:
		var wpb: Variant = d.get("port_war_pending_burst", null)
		if typeof(wpb) == TYPE_DICTIONARY:
			_deserialize_port_int_map_into(_port_war_pending_burst, wpb as Dictionary, 0, 999)
	if ver >= 11:
		var ppg: Variant = d.get("port_population_grain", null)
		if typeof(ppg) == TYPE_DICTIONARY:
			_deserialize_port_population_grain(ppg as Dictionary)
		var ppw: Variant = d.get("port_population_wine_base", null)
		if typeof(ppw) == TYPE_DICTIONARY:
			_deserialize_port_population_wine_base(ppw as Dictionary)
		var ppb: Variant = d.get("port_population_grain_baseline", null)
		if typeof(ppb) == TYPE_DICTIONARY:
			_deserialize_port_population_grain_baseline(ppb as Dictionary)
		var ppc: Variant = d.get("port_population_grain_cap", null)
		if typeof(ppc) == TYPE_DICTIONARY:
			_deserialize_port_population_grain_cap(ppc as Dictionary)
		var pfs: Variant = d.get("port_famine_streak_days", null)
		if typeof(pfs) == TYPE_DICTIONARY:
			_deserialize_port_famine_streak_days(pfs as Dictionary)
		var pps: Variant = d.get("port_prosperity_streak_days", null)
		if typeof(pps) == TYPE_DICTIONARY:
			_deserialize_port_prosperity_streak_days(pps as Dictionary)
		var pra: Variant = d.get("port_rationing_active", null)
		if typeof(pra) == TYPE_DICTIONARY:
			_deserialize_port_rationing_active(pra as Dictionary)
		var prd: Variant = d.get("port_rationing_days_active", null)
		if typeof(prd) == TYPE_DICTIONARY:
			_deserialize_port_int_map_into(_port_rationing_days_active, prd as Dictionary, 0, 999)
		var ppf: Variant = d.get("port_preserved_food", null)
		if typeof(ppf) == TYPE_DICTIONARY:
			_deserialize_port_preserved_food(ppf as Dictionary)
		_ensure_port_demographics_post_load()
	else:
		_init_port_demographics_from_world()
	if ver >= 33:
		var pca: Variant = d.get("port_crop_agro", null)
		if typeof(pca) == TYPE_DICTIONARY:
			_deserialize_port_crop_agro(pca as Dictionary)
		else:
			_init_port_crop_agro_state()
	else:
		_init_port_crop_agro_state()
	if ver >= 35:
		var plb: Variant = d.get("port_local_crop_belief_01", null)
		if typeof(plb) == TYPE_DICTIONARY:
			_deserialize_port_float_map_into(_port_local_crop_belief_01, plb as Dictionary, 0.0, 1.0)
		else:
			_port_local_crop_belief_01.clear()
		var picr: Variant = d.get("port_crop_inbound_reports", null)
		_deserialize_port_crop_inbound_reports(picr)
		if ver >= 36:
			var prd0: Variant = d.get("port_crop_rumor_public_delta", null)
			if typeof(prd0) == TYPE_DICTIONARY:
				_deserialize_port_float_map_into(
					_port_crop_rumor_public_delta,
					prd0 as Dictionary,
					-_CROP_RUMOR_DELTA_ABS_MAX,
					_CROP_RUMOR_DELTA_ABS_MAX
				)
			else:
				_port_crop_rumor_public_delta.clear()
		else:
			_port_crop_rumor_public_delta.clear()
	else:
		_init_port_crop_information_state()
	if ver >= 34:
		var pcf: Variant = d.get("port_consecutive_grain_full_ration_days", null)
		if typeof(pcf) == TYPE_DICTIONARY:
			_deserialize_port_int_map_into(_port_consecutive_grain_full_ration_days, pcf as Dictionary, 0, 999)
		else:
			_port_consecutive_grain_full_ration_days.clear()
		var pcz: Variant = d.get("port_consecutive_grain_zero_eat_days", null)
		if typeof(pcz) == TYPE_DICTIONARY:
			_deserialize_port_int_map_into(_port_consecutive_grain_zero_eat_days, pcz as Dictionary, 0, 999)
		else:
			_port_consecutive_grain_zero_eat_days.clear()
	else:
		_port_consecutive_grain_full_ration_days.clear()
		_port_consecutive_grain_zero_eat_days.clear()
	_ensure_port_meal_streak_counters_post_load()
	if ver >= 12:
		player_ship_condition = clampi(
			int(d.get("player_ship_condition", _SHIP_CONDITION_MAX)),
			_SHIP_CONDITION_MIN,
			_SHIP_CONDITION_MAX,
		)
		player_ship_wine_counter = clampi(int(d.get("player_ship_wine_counter", 0)), 0, 9999)
	else:
		player_ship_condition = _SHIP_CONDITION_MAX
		player_ship_wine_counter = 0
	if ver >= 14:
		player_fleet_ships = clampi(int(d.get("player_fleet_ships", 1)), 1, _FLEET_MAX_SHIPS)
	else:
		player_fleet_ships = 1
	if ver >= 18:
		player_fleet_shipyard_days_remaining = clampi(int(d.get("player_fleet_shipyard_days_remaining", 0)), 0, 999)
		player_fleet_shipyard_port_id = str(d.get("player_fleet_shipyard_port_id", ""))
		if player_fleet_shipyard_days_remaining > 0 and (
			player_fleet_shipyard_port_id.is_empty() or not _port_names.has(player_fleet_shipyard_port_id)
		):
			player_fleet_shipyard_days_remaining = 0
			player_fleet_shipyard_port_id = ""
	else:
		player_fleet_shipyard_days_remaining = 0
		player_fleet_shipyard_port_id = ""
	if ver >= 20:
		player_ship_class_id = str(d.get("player_ship_class_id", ""))
		player_captain_culture = str(d.get("player_captain_culture", "italic"))
		player_ship_age_days = clampi(int(d.get("player_ship_age_days", 0)), 0, 999999)
	else:
		player_ship_class_id = ""
		player_captain_culture = ""
		player_ship_age_days = 0
	if ver >= 22:
		var pr0: String = str(d.get("player_voyage_role", _VOYAGE_ROLE_MERCHANT))
		player_voyage_role = pr0 if _is_valid_voyage_role(pr0) else _VOYAGE_ROLE_MERCHANT
		var pec: Variant = d.get("player_escort_contract", null)
		if typeof(pec) == TYPE_DICTIONARY:
			player_escort_contract = _sanitize_escort_contract(pec as Dictionary)
		else:
			player_escort_contract = {}
		if player_voyage_role != _VOYAGE_ROLE_ESCORT:
			player_escort_contract.clear()
	else:
		player_voyage_role = _VOYAGE_ROLE_MERCHANT
		player_escort_contract = {}
	if ver >= 31:
		player_offers_convoy_escort = bool(d.get("player_offers_convoy_escort", true))
	else:
		player_offers_convoy_escort = true
	if ver >= 37:
		player_crop_intel_port_id = str(d.get("player_crop_intel_port_id", ""))
		player_crop_intel_mean_01 = clampf(float(d.get("player_crop_intel_mean_01", 0.5)), 0.0, 1.0)
		player_crop_intel_sigma_01 = clampf(float(d.get("player_crop_intel_sigma_01", _PLAYER_CROP_INTEL_SIGMA_INIT)), 0.0, 1.0)
		player_crop_intel_update_day = clampi(int(d.get("player_crop_intel_update_day", 0)), 0, 9999999)
		player_civic_reputation_01 = clampf(float(d.get("player_civic_reputation_01", 0.62)), 0.0, 1.0)
	else:
		player_crop_intel_port_id = ""
		player_crop_intel_mean_01 = 0.5
		player_crop_intel_sigma_01 = _PLAYER_CROP_INTEL_SIGMA_INIT
		player_crop_intel_update_day = 0
		player_civic_reputation_01 = 0.62
	if ver >= 38:
		player_war_intel_port_id = str(d.get("player_war_intel_port_id", ""))
		player_war_intel_mean_01 = clampf(float(d.get("player_war_intel_mean_01", 0.35)), 0.0, 1.0)
		player_war_intel_sigma_01 = clampf(float(d.get("player_war_intel_sigma_01", _PLAYER_CROP_INTEL_SIGMA_INIT)), 0.0, 1.0)
		player_war_intel_update_day = clampi(int(d.get("player_war_intel_update_day", 0)), 0, 9999999)
	else:
		player_war_intel_port_id = ""
		player_war_intel_mean_01 = 0.35
		player_war_intel_sigma_01 = _PLAYER_CROP_INTEL_SIGMA_INIT
		player_war_intel_update_day = 0
	player_port_civic_reputation_01.clear()
	if ver >= 39:
		var ppc: Variant = d.get("player_port_civic_reputation_01", null)
		if typeof(ppc) == TYPE_DICTIONARY:
			var ppcd: Dictionary = ppc as Dictionary
			for pk in ppcd.keys():
				var pxs: String = str(pk)
				if not _port_names.has(pxs):
					continue
				player_port_civic_reputation_01[pxs] = clampf(float(ppcd[pk]), 0.0, 1.0)
	player_voyage_weather_bless_p_sub = 0.0
	player_temple_pending_storm_p_sub = 0.0
	player_temple_offerings_rep_granted_01 = 0.0
	if ver >= 40:
		player_temple_pending_storm_p_sub = clampf(
			float(d.get("player_temple_pending_storm_p_sub", 0.0)),
			0.0,
			_TEMPLE_STORM_PENDING_P_SUB_TOTAL_CAP,
		)
		player_temple_offerings_rep_granted_01 = clampf(
			float(d.get("player_temple_offerings_rep_granted_01", 0.0)),
			0.0,
			_TEMPLE_REP_LIFETIME_CAP,
		)
		if voyage_days_remaining > 0:
			player_voyage_weather_bless_p_sub = clampf(
				float(d.get("player_voyage_weather_bless_p_sub", 0.0)),
				0.0,
				_TEMPLE_STORM_PENDING_P_SUB_TOTAL_CAP,
			)
	if ver >= 16:
		var uh: Variant = d.get("used_hull_listings", null)
		if typeof(uh) == TYPE_DICTIONARY:
			_deserialize_used_hull_listings(uh as Dictionary)
		else:
			_port_used_hull_listings.clear()
			_next_used_hull_listing_id = 1
			_ensure_used_hull_listings_for_all_ports()
		_next_used_hull_listing_id = maxi(1, int(d.get("used_hull_listing_next_id", _next_used_hull_listing_id)))
	else:
		_port_used_hull_listings.clear()
		_next_used_hull_listing_id = 1
		_ensure_used_hull_listings_for_all_ports()
	if ver >= 42:
		_deserialize_player_ui_memory_v42(d)
	else:
		_player_ledger_by_port.clear()
		_player_market_buy_prev.clear()
		_player_good_last_trade_day.clear()
		_player_route_intel_refresh_day = 0
	_player_seed_opening_ledger_hearsay_if_empty()
	_ensure_player_ship_identity_post_load()
	_bootstrap_recurring_war_timers()
	_port_luxury_import_queue.clear()
	_pending_player_encounter_msg = ""
	game_loaded.emit(SAVE_PATH)
	money_changed.emit()
	cargo_changed.emit()
	market_changed.emit()
	return true


func _serialize_player_ledger_by_port() -> Dictionary:
	var out: Dictionary = {}
	for pk in _player_ledger_by_port.keys():
		var cell: Variant = _player_ledger_by_port.get(pk, null)
		if typeof(cell) != TYPE_DICTIONARY:
			continue
		out[str(pk)] = (cell as Dictionary).duplicate(true)
	return out


func _serialize_player_good_last_trade_days() -> Dictionary:
	var out: Dictionary = {}
	for gk in _player_good_last_trade_day.keys():
		out[str(gk)] = clampi(int(_player_good_last_trade_day[gk]), 0, 9999999)
	return out


func _deserialize_player_ui_memory_v42(d: Dictionary) -> void:
	_player_ledger_by_port.clear()
	var lg: Variant = d.get("player_ledger_by_port", null)
	if typeof(lg) == TYPE_DICTIONARY:
		for pk in (lg as Dictionary).keys():
			var pid := str(pk)
			if not _port_names.has(pid):
				continue
			var row0: Variant = (lg as Dictionary)[pk]
			if typeof(row0) != TYPE_DICTIONARY:
				continue
			var rd: Dictionary = row0 as Dictionary
			var cell_out: Dictionary = {
				"day": clampi(int(rd.get("day", 0)), 0, 9999999),
				"grain_buy": maxi(0, int(rd.get("grain_buy", 0))),
				"grain_sell": maxi(0, int(rd.get("grain_sell", 0))),
				"source": str(rd.get("source", "observed market")),
				"reliability": clampf(float(rd.get("reliability", 0.75)), 0.0, 1.0),
			}
			var pg_raw: Variant = rd.get("per_good", null)
			if typeof(pg_raw) == TYPE_DICTIONARY:
				var pg_clean: Dictionary = {}
				for gkk in (pg_raw as Dictionary).keys():
					var gg := str(gkk)
					if not _goods.has(gg):
						continue
					var rvg0: Variant = (pg_raw as Dictionary)[gkk]
					if typeof(rvg0) != TYPE_DICTIONARY:
						continue
					var rvg: Dictionary = rvg0 as Dictionary
					pg_clean[gg] = {
						"name": str(rvg.get("name", str((_goods[gg] as Dictionary).get("name", gg)))),
						"buy": maxi(0, int(rvg.get("buy", 0))),
						"sell": maxi(0, int(rvg.get("sell", 0))),
						"toll": maxi(0, int(rvg.get("toll", 0))),
					}
				if not pg_clean.is_empty():
					cell_out["per_good"] = pg_clean
			_player_ledger_by_port[pid] = cell_out
	_player_market_buy_prev.clear()
	var mp: Variant = d.get("player_market_buy_prev", null)
	if typeof(mp) == TYPE_DICTIONARY:
		for k in (mp as Dictionary).keys():
			_player_market_buy_prev[str(k)] = maxi(0, int((mp as Dictionary)[k]))
	_player_good_last_trade_day.clear()
	var gt: Variant = d.get("player_good_last_trade_day", null)
	if typeof(gt) == TYPE_DICTIONARY:
		for gk in (gt as Dictionary).keys():
			var gids := str(gk)
			if not _goods.has(gids):
				continue
			_player_good_last_trade_day[gids] = clampi(int((gt as Dictionary)[gk]), 0, 9999999)
	_player_route_intel_refresh_day = clampi(int(d.get("player_route_intel_refresh_day", 0)), 0, 9999999)


func _serialize_port_stocks() -> Dictionary:
	var out: Dictionary = {}
	for port_id in _port_stocks.keys():
		var inner: Variant = _port_stocks.get(port_id, null)
		if typeof(inner) != TYPE_DICTIONARY:
			continue
		var copy: Dictionary = (inner as Dictionary).duplicate(true)
		out[str(port_id)] = copy
	return out


func _deserialize_port_stocks(data: Dictionary) -> void:
	_port_stocks.clear()
	for port_key in data.keys():
		var pid := str(port_key)
		if not _port_names.has(pid):
			continue
		var inner_raw: Variant = data[port_key]
		if typeof(inner_raw) != TYPE_DICTIONARY:
			continue
		var inner: Dictionary = inner_raw as Dictionary
		var row: Dictionary = {}
		for gk in inner.keys():
			var gid := str(gk)
			if not _goods.has(gid):
				continue
			row[gid] = maxi(0, int(inner[gk]))
		_port_stocks[pid] = row
	_ensure_all_ports_have_all_goods()


func _lane_key(from_id: String, to_id: String) -> String:
	return "%s|%s" % [from_id, to_id]


func _append_unique_neighbor_to(neigh_out: Dictionary, port_id: String, neighbor_id: String) -> void:
	if not neigh_out.has(port_id):
		neigh_out[port_id] = []
	var arr: Array = neigh_out[port_id] as Array
	if arr.find(neighbor_id) < 0:
		arr.append(neighbor_id)


func _build_port_neighbors_from(lane_src: Dictionary, neigh_out: Dictionary) -> void:
	neigh_out.clear()
	for key in lane_src.keys():
		var parts: PackedStringArray = String(key).split("|", false)
		if parts.size() != 2:
			continue
		var a: String = str(parts[0])
		var b: String = str(parts[1])
		_append_unique_neighbor_to(neigh_out, a, b)
		_append_unique_neighbor_to(neigh_out, b, a)


func _build_port_neighbors() -> void:
	_build_port_neighbors_from(_lane_days, _port_neighbors)


func _voyage_lane_weight_undirected_for(lanes: Dictionary, a: String, b: String) -> int:
	var w: int = int(lanes.get(_lane_key(a, b), -1))
	if w >= 0:
		return w
	return int(lanes.get(_lane_key(b, a), -1))


func _voyage_lane_weight_undirected(a: String, b: String) -> int:
	return _voyage_lane_weight_undirected_for(_lane_days, a, b)


func _voyage_max_lane_weight_for(lanes: Dictionary) -> int:
	var mx: int = 1
	for lk in lanes.keys():
		mx = maxi(mx, int(lanes[lk]))
	return mx


func _voyage_max_lane_weight() -> int:
	return _voyage_max_lane_weight_for(_lane_days)


func _rebuild_coastal_shortest_path_cache_for(neigh_src: Dictionary, lane_src: Dictionary, cache_out: Dictionary) -> void:
	cache_out.clear()
	if _port_names.is_empty():
		return
	for src_key in _port_names.keys():
		var src: String = str(src_key)
		var best: Dictionary = {}
		for pk in _port_names.keys():
			best[str(pk)] = 999999
		best[src] = 0
		var used: Dictionary = {}
		for _iter in _port_names.size() + 4:
			var pick: String = ""
			var pick_dist: int = 999999
			for pk2 in _port_names.keys():
				var ps2: String = str(pk2)
				if bool(used.get(ps2, false)):
					continue
				var dv2: int = int(best.get(ps2, 999999))
				if dv2 < pick_dist:
					pick_dist = dv2
					pick = ps2
			if pick.is_empty() or pick_dist >= 999999:
				break
			used[pick] = true
			var neigh_raw: Variant = neigh_src.get(pick, null)
			if typeof(neigh_raw) != TYPE_ARRAY:
				continue
			for nb in neigh_raw as Array:
				var nx: String = str(nb)
				if bool(used.get(nx, false)):
					continue
				var wgt: int = _voyage_lane_weight_undirected_for(lane_src, pick, nx)
				if wgt < 0:
					continue
				var alt: int = pick_dist + wgt
				if alt < int(best.get(nx, 999999)):
					best[nx] = alt
		for dst_key in _port_names.keys():
			var dst: String = str(dst_key)
			if dst == src:
				continue
			var fin: int = int(best.get(dst, 999999))
			if fin >= 999999:
				cache_out[_lane_key(src, dst)] = -1
			else:
				cache_out[_lane_key(src, dst)] = fin


func _rebuild_coastal_shortest_path_cache() -> void:
	_rebuild_coastal_shortest_path_cache_for(_port_neighbors, _lane_days, _voyage_coastal_shortest_cache)


func _rebuild_coastal_shortest_path_cache_npc() -> void:
	_voyage_coastal_shortest_cache_npc.clear()
	_port_neighbors_npc.clear()
	if _npc_lane_days.is_empty():
		return
	_build_port_neighbors_from(_npc_lane_days, _port_neighbors_npc)
	_rebuild_coastal_shortest_path_cache_for(_port_neighbors_npc, _npc_lane_days, _voyage_coastal_shortest_cache_npc)


func _coastal_shortest_days_lookup(from_id: String, to_id: String) -> int:
	var k: String = _lane_key(from_id, to_id)
	if _voyage_coastal_shortest_cache.has(k):
		return int(_voyage_coastal_shortest_cache[k])
	return 999999


func _coastal_shortest_days_lookup_npc(from_id: String, to_id: String) -> int:
	var k: String = _lane_key(from_id, to_id)
	if _voyage_coastal_shortest_cache_npc.has(k):
		return int(_voyage_coastal_shortest_cache_npc[k])
	return 999999


func _voyage_route_choice_roll(from_id: String, to_id: String) -> float:
	var s: String = str(from_id) + ">" + str(to_id) + ">voyageRouteV1"
	var h: int = 5381
	for i in s.length():
		var c: int = s.unicode_at(i)
		h = ((h << 5) + h + c) & 0x7FFFFFFF
	var u: int = h % 1000003
	return float(u) / 1000003.0


func _voyage_plan(from_id: String, to_id: String, risk_aversion_01: float, use_npc_graph: bool = false) -> Dictionary:
	var ra: float = clampf(risk_aversion_01, 0.0, 1.0)
	var use_npc: bool = use_npc_graph and not _npc_lane_days.is_empty()
	var D_c: int
	var lane_fb: Dictionary
	if use_npc:
		D_c = _coastal_shortest_days_lookup_npc(from_id, to_id)
		lane_fb = _npc_lane_days
	else:
		D_c = _coastal_shortest_days_lookup(from_id, to_id)
		lane_fb = _lane_days
	var disconnected: bool = D_c < 0 or D_c >= 500000
	if disconnected:
		var md: int = _voyage_max_lane_weight_for(lane_fb)
		var dd: int = clampi(_VOYAGE_DISCONNECTED_BASE_DAYS + md, 10, 48)
		return {"days": dd, "open_01": 0.92, "route_label": "open sea"}
	var D_b: int = D_c
	if D_c >= 4:
		D_b = maxi(1, int(floor(float(D_c) * _VOYAGE_BOLD_DAY_MULT)))
		D_b = mini(D_b, maxi(1, D_c - 1))
	elif D_c >= 3:
		D_b = maxi(1, D_c - 1)
	var roll: float = _voyage_route_choice_roll(from_id, to_id)
	var take_bold: bool = roll > ra and D_b < D_c
	var days_ch: int = D_c
	var open_01: float = _VOYAGE_COASTAL_OPENNESS
	var label: String = "coastal"
	if take_bold:
		days_ch = D_b
		open_01 = clampf(1.0 - float(D_b) / float(maxi(D_c, 1)), 0.1, 0.95)
		label = "bold run"
	return {"days": days_ch, "open_01": open_01, "route_label": label}


func _player_trim_cargo_to_capacity() -> void:
	while get_player_cargo_used() > get_player_cargo_capacity():
		var worst_gid: String = ""
		var worst_q: int = 0
		for gk in player_cargo.keys():
			var gid: String = str(gk)
			var qv: int = get_player_cargo_qty(gid)
			if qv > worst_q:
				worst_q = qv
				worst_gid = gid
		if worst_gid.is_empty() or worst_q <= 0:
			break
		_adjust_player_cargo_delta(worst_gid, -1)


func _npc_trim_cargo_to_capacity(agent: Dictionary) -> void:
	if not agent.has("cargo") or typeof(agent.get("cargo")) != TYPE_DICTIONARY:
		agent["cargo"] = {}
	var cargo: Dictionary = agent["cargo"] as Dictionary
	while _npc_cargo_effective_used_units(agent) > _npc_cargo_capacity_units(agent):
		var worst_gid: String = ""
		var worst_q: int = 0
		for gk in cargo.keys():
			var gid: String = str(gk)
			var qv: int = _npc_cargo_qty(cargo, gid)
			if qv > worst_q:
				worst_q = qv
				worst_gid = gid
		if worst_gid.is_empty() or worst_q <= 0:
			break
		_npc_adjust_cargo(cargo, worst_gid, -1)


func _player_daily_storm_probability_without_weather_bless() -> float:
	if voyage_days_remaining <= 0:
		return 0.0
	var D0: int = maxi(1, player_voyage_booked_days)
	var op: float = clampf(player_voyage_open_sea_01, 0.0, 1.0)
	var row: Dictionary = _player_ship_row()
	var spm: float = clampf(float(row.get("storm_probability_mul", 1.0)), 0.35, 2.0)
	var p: float = clampf(
		(
			_VOYAGE_STORM_BASE_P
			+ _VOYAGE_STORM_PER_BOOKED_DAY * float(D0) / 24.0
			+ _VOYAGE_STORM_OPEN_MULT * op
		)
		* spm,
		0.0,
		_VOYAGE_STORM_P_CAP,
	)
	return clampf(
		p * _season_storm_probability_scale_for_doy(_calendar_doy_1based(current_day)),
		0.0,
		_VOYAGE_STORM_P_CAP,
	)


func _player_daily_storm_probability() -> float:
	var p0: float = _player_daily_storm_probability_without_weather_bless()
	if p0 <= 0.0 or player_voyage_weather_bless_p_sub <= 0.0:
		return p0
	var sub: float = mini(
		player_voyage_weather_bless_p_sub,
		p0 * 0.38,
	)
	return clampf(p0 - sub, 0.0, _VOYAGE_STORM_P_CAP)


func _tick_player_storm_if_at_sea() -> void:
	var p: float = _player_daily_storm_probability()
	if p <= 0.0 or _rng.randf() >= p:
		return
	var row: Dictionary = _player_ship_row()
	var sdm: float = clampf(float(row.get("storm_damage_mul", 1.0)), 0.4, 2.2)
	var age_f: float = 1.0 + _SHIP_AGE_STORM_DAMAGE_SCALE * _player_age_stress_01()
	var dmg: int = int(
		ceil(
			float(_rng.randi_range(_VOYAGE_STORM_COND_DAMAGE_MIN, _VOYAGE_STORM_COND_DAMAGE_MAX)) * sdm * age_f
		)
	)
	player_ship_condition = clampi(player_ship_condition - dmg, _SHIP_CONDITION_MIN, _SHIP_CONDITION_MAX)
	var ships: int = clampi(player_fleet_ships, 1, _FLEET_MAX_SHIPS)
	if ships > 1 and _rng.randf() < _VOYAGE_STORM_HULL_LOSS_CHANCE:
		player_fleet_ships = maxi(1, ships - 1)
		_player_trim_cargo_to_capacity()
	cargo_changed.emit()
	market_changed.emit()


func _player_boarding_marine_qty() -> int:
	if not _goods.has("marines"):
		return 0
	return clampi(get_player_cargo_qty("marines"), 0, 9999)


func _player_boarding_power() -> float:
	var mar: int = _player_boarding_marine_qty()
	var row: Dictionary = _player_ship_row()
	var vm: float = clampf(float(row.get("voyage_day_mult", 1.0)), 0.55, 1.55)
	var cat: String = str(row.get("category", "merchant"))
	var hull_bonus: float = 4.0 if cat == "galley" else 0.0
	var ex: float = 0.5
	var neu: float = 0.5
	return float(mar) * 2.35 + 8.0 + hull_bonus + (vm - 0.55) * 5.5 + ex * 2.8 + neu * 1.1


func _player_weighted_pick_pirate(rows: Array) -> Dictionary:
	return _npc_weighted_pick_agent(rows)


func _pirate_npc_steal_from_player(pr: Dictionary) -> String:
	var purse_v: int = clampi(player_money, 0, _MAX_PURSE_COINS)
	var take_c: int = mini(
		purse_v,
		maxi(6, int(round(float(purse_v) * 0.17))) + _rng.randi_range(0, 28)
	)
	take_c = mini(take_c, purse_v)
	if take_c > 0:
		player_money = clampi(purse_v - take_c, 0, _MAX_PURSE_COINS)
		pr["money"] = clampi(int(pr.get("money", 0)) + take_c, 0, _MAX_PURSE_COINS)
	var crp: Variant = pr.get("cargo", null)
	if typeof(crp) != TYPE_DICTIONARY:
		pr["cargo"] = {}
		crp = pr["cargo"]
	var p_cargo: Dictionary = crp as Dictionary
	var tries: int = _rng.randi_range(1, 3)
	var stolen_bits: PackedStringArray = []
	for _t in tries:
		var candidates: Array = []
		for gk in player_cargo.keys():
			var gid: String = str(gk)
			if gid == "grain" or gid == "marines" or not _goods.has(gid):
				continue
			var q: int = get_player_cargo_qty(gid)
			if q <= 0:
				continue
			var up: int = maxi(1, int((_goods[gid] as Dictionary).get("unit_sell_price", 1)))
			candidates.append({"gid": gid, "w": float(q * up)})
		if candidates.is_empty():
			break
		var tw: float = 0.0
		for c in candidates:
			tw += float((c as Dictionary).get("w", 1.0))
		var x: float = _rng.randf() * tw
		var pick_gid: String = ""
		for c2 in candidates:
			var d2: Dictionary = c2 as Dictionary
			x -= float(d2.get("w", 1.0))
			if x <= 0.0:
				pick_gid = str(d2.get("gid", ""))
				break
		if pick_gid.is_empty():
			pick_gid = str((candidates[0] as Dictionary).get("gid", ""))
		var steal: int = _rng.randi_range(1, 3)
		steal = mini(steal, get_player_cargo_qty(pick_gid))
		if steal <= 0:
			continue
		_adjust_player_cargo_delta(pick_gid, -steal)
		_npc_adjust_cargo(p_cargo, pick_gid, steal)
		stolen_bits.append("%s×%d" % [get_good_name(pick_gid), steal])
	var loot_s: String = ""
	if take_c > 0 and stolen_bits.is_empty():
		loot_s = "%dc" % take_c
	elif take_c > 0:
		loot_s = "%dc, %s" % [take_c, ", ".join(stolen_bits)]
	elif not stolen_bits.is_empty():
		loot_s = ", ".join(stolen_bits)
	return loot_s


func _player_apply_boarding_marine_loss(loss: int) -> void:
	if loss <= 0 or not _goods.has("marines"):
		return
	var have: int = get_player_cargo_qty("marines")
	var take: int = mini(have, loss)
	if take > 0:
		_adjust_player_cargo_delta("marines", -take)


func _tick_player_pirate_encounter_if_at_sea() -> void:
	if voyage_days_remaining <= 0:
		return
	if not _goods.has("marines"):
		return
	if str(player_voyage_role) != _VOYAGE_ROLE_MERCHANT:
		return
	var rows: Array = []
	for item in _npc_agents:
		if typeof(item) != TYPE_DICTIONARY:
			continue
		var pr: Dictionary = item as Dictionary
		if str(pr.get("voyage_role", "")) != _VOYAGE_ROLE_PIRATE:
			continue
		if int(pr.get("voyage_days_remaining", 0)) <= 0:
			continue
		var w: float = 0.58
		if str(pr.get("voyage_dest_id", "")) == str(voyage_dest_id):
			w += 2.1
		var srow: Dictionary = _npc_ship_row(pr)
		var vm: float = clampf(float(srow.get("voyage_day_mult", 1.0)), 0.55, 1.55)
		w += (vm - 0.55) * 1.6
		var op: float = clampf(
			0.5 * (player_voyage_open_sea_01 + float(pr.get("voyage_open_sea_01", 0.0))),
			0.0,
			1.0
		)
		w *= 0.72 + op * 0.5
		rows.append({"ag": pr, "w": maxf(0.06, w)})
	if rows.is_empty():
		return
	var pirate: Dictionary = _player_weighted_pick_pirate(rows)
	if pirate.is_empty():
		return
	var vmin: float = clampf(float(_player_ship_row().get("voyage_day_mult", 1.0)), 0.55, 1.55)
	var pm: float = clampf(float(_npc_ship_row(pirate).get("voyage_day_mult", 1.0)), 0.55, 1.55)
	var op2: float = clampf(
		0.5 * (player_voyage_open_sea_01 + float(pirate.get("voyage_open_sea_01", 0.0))),
		0.0,
		1.0
	)
	var p_catch: float = clampf(
		_PLAYER_PIRATE_CATCH_BASE_P * (0.88 + (vmin - pm) * 0.48) * (0.64 + op2 * 0.48),
		0.01,
		0.40
	)
	if _rng.randf() > p_catch:
		return
	var p_player: float = _player_boarding_power() + _rng.randf() * 10.0
	var p_pir: float = _npc_pirate_boarding_power(pirate) + _rng.randf() * 7.0
	if p_player >= p_pir * 0.92:
		var hurt: int = _rng.randi_range(2, 7)
		_npc_pirate_apply_marine_losses(pirate, hurt)
		_pending_player_encounter_msg = "Boarders repelled — pirate crew took heavy losses in the grapple."
		return
	var loss_p: int = _rng.randi_range(1, 5)
	_player_apply_boarding_marine_loss(loss_p)
	var loot_desc: String = _pirate_npc_steal_from_player(pirate)
	var pn0: float = float(pirate.get("pirate_notoriety", 0.0))
	pirate["pirate_notoriety"] = clampf(pn0 + 2.5, 0.0, _PIRATE_NOTORIETY_CAP)
	_npc_trim_cargo_to_capacity(pirate)
	money_changed.emit()
	cargo_changed.emit()
	var msg: String
	if loot_desc.is_empty():
		msg = "Raiders boarded — marines bloodied but nothing carried off."
	else:
		msg = "Raiders took: %s." % loot_desc
	_pending_player_encounter_msg = msg


func _tick_npc_storms_at_sea() -> void:
	var any_hit: bool = false
	for item in _npc_agents:
		if typeof(item) != TYPE_DICTIONARY:
			continue
		var ag: Dictionary = item as Dictionary
		var days_left: int = int(ag.get("voyage_days_remaining", 0))
		if days_left <= 0:
			continue
		var D0: int = maxi(1, int(ag.get("voyage_booked_days", days_left)))
		var op: float = clampf(float(ag.get("voyage_open_sea_01", _VOYAGE_COASTAL_OPENNESS)), 0.0, 1.0)
		var srow: Dictionary = _npc_ship_row(ag)
		var spm2: float = clampf(float(srow.get("storm_probability_mul", 1.0)), 0.35, 2.0)
		var p: float = clampf(
			(
				_VOYAGE_STORM_BASE_P
				+ _VOYAGE_STORM_PER_BOOKED_DAY * float(D0) / 24.0
				+ _VOYAGE_STORM_OPEN_MULT * op
			)
			* spm2,
			0.0,
			_VOYAGE_STORM_P_CAP,
		)
		p = clampf(
			p * _season_storm_probability_scale_for_doy(_calendar_doy_1based(current_day)),
			0.0,
			_VOYAGE_STORM_P_CAP,
		)
		if _rng.randf() >= p:
			continue
		_ensure_npc_ship_fields(ag)
		var cond0: int = clampi(int(ag.get("ship_condition", _SHIP_CONDITION_MAX)), _SHIP_CONDITION_MIN, _SHIP_CONDITION_MAX)
		var sdm2: float = clampf(float(srow.get("storm_damage_mul", 1.0)), 0.4, 2.2)
		var dmg: int = maxi(
			1,
			int(ceil(float(_rng.randi_range(_VOYAGE_STORM_COND_DAMAGE_MIN, _VOYAGE_STORM_COND_DAMAGE_MAX)) * sdm2))
		)
		ag["ship_condition"] = clampi(cond0 - dmg, _SHIP_CONDITION_MIN, _SHIP_CONDITION_MAX)
		var sh: int = clampi(int(ag.get("fleet_ships", 1)), 1, _FLEET_MAX_SHIPS)
		if sh > 1 and _rng.randf() < _VOYAGE_STORM_HULL_LOSS_CHANCE:
			ag["fleet_ships"] = maxi(1, sh - 1)
			_npc_trim_cargo_to_capacity(ag)
		any_hit = true
	if any_hit:
		market_changed.emit()


func _load_world(path: String) -> void:
	_port_names.clear()
	_port_map_uv.clear()
	_lane_days.clear()
	_npc_lane_days.clear()
	_voyage_coastal_shortest_cache.clear()
	_voyage_coastal_shortest_cache_npc.clear()
	_port_neighbors_npc.clear()
	_port_initial_stock.clear()
	_port_npc_trader_count.clear()
	_port_population_grain.clear()
	_port_population_wine_base.clear()
	_port_population_fish_per_day.clear()
	_port_population_grain_baseline.clear()
	_port_population_grain_cap.clear()
	_port_famine_streak_days.clear()
	_port_consecutive_grain_full_ration_days.clear()
	_port_consecutive_grain_zero_eat_days.clear()
	_port_prosperity_streak_days.clear()
	_port_rationing_active.clear()
	_port_rationing_days_active.clear()
	_port_preserved_food.clear()
	_port_initial_wealth.clear()
	_port_role_wealth_bonus.clear()
	_port_roles.clear()
	_port_existential_war_burst_days.clear()
	_port_baseline_momentum_up.clear()
	_port_baseline_momentum_dn.clear()
	_port_war_days_remaining.clear()
	_port_war_recurring.clear()
	_port_war_peace_remaining.clear()
	_port_war_pending_burst.clear()
	_port_war_burst_initial.clear()
	_port_peace_riot_grace_days.clear()
	_port_commerce_tick.clear()
	_port_commerce_pulse.clear()
	_port_harbour_due_coins_tick.clear()
	_port_cartel_strength.clear()
	_port_war_rumor.clear()
	_port_rumor_good_delta.clear()
	_port_plague_days.clear()
	_port_crop_moisture_01.clear()
	_port_crop_growth_01.clear()
	_farms.clear()
	_mines.clear()
	_port_mint_cfg.clear()
	_port_luxury_import_queue.clear()
	_luxury_import_cfg = {
		"enabled": true,
		"spawn_roll": 0.10,
		"lead_min": 3,
		"lead_max": 8,
		"qty_min": 1,
		"qty_max": 3,
		"max_pending": 4,
		"cost_frac": _LUXURY_IMPORT_COST_FRAC_DEFAULT,
		"treasury_take_frac": _LUXURY_IMPORT_TREASURY_TAKE_FRAC_DEFAULT,
	}
	_port_industrial_metal_per_day.clear()
	_port_industrial_wire_per_day.clear()
	_port_industrial_timber_per_day.clear()
	_port_industrial_textiles_per_day.clear()
	_port_trade_price_bias.clear()
	_port_market_demand_override.clear()
	_port_good_tolls.clear()
	_player_toll_graft_until.clear()
	_port_used_hull_listings.clear()
	_next_used_hull_listing_id = 1
	_port_shipyard_classes.clear()
	_port_cultures.clear()
	_chart_area_labels.clear()
	_chart_area_notes.clear()
	_port_chart_area_id.clear()
	var text := FileAccess.get_file_as_string(path)
	if text.is_empty():
		push_error("HarboursOfPower: missing or empty world file: %s" % path)
		return
	var data: Variant = JSON.parse_string(text)
	if data == null:
		push_error("HarboursOfPower: invalid JSON: %s" % path)
		return
	if typeof(data) != TYPE_DICTIONARY:
		push_error("HarboursOfPower: world root must be object")
		return
	var doc: Dictionary = data
	var tre_raw: int = clampi(int(doc.get("initial_treasury_coins", _WORLD_TREASURY_FALLBACK)), 0, _WORLD_TREASURY_MAX)
	_world_treasury_coins = clampi(tre_raw, 0, _WORLD_TREASURY_MAX)
	_world_initial_treasury_coins = _world_treasury_coins
	_world_autonomy_warmup_days = clampi(int(doc.get("autonomy_warmup_days", 24)), 0, 180)
	_world_crop_agro_model = bool(doc.get("crop_agro_model", true))
	_world_npc_city_grain_contracts_enabled = bool(doc.get("npc_city_grain_contracts_enabled", true))
	_luxury_import_cfg = {
		"enabled": true,
		"spawn_roll": 0.10,
		"lead_min": 3,
		"lead_max": 8,
		"qty_min": 1,
		"qty_max": 3,
		"max_pending": 4,
		"cost_frac": _LUXURY_IMPORT_COST_FRAC_DEFAULT,
		"treasury_take_frac": _LUXURY_IMPORT_TREASURY_TAKE_FRAC_DEFAULT,
	}
	var li_raw: Variant = doc.get("luxury_import", null)
	if typeof(li_raw) == TYPE_DICTIONARY:
		var lid: Dictionary = li_raw as Dictionary
		if lid.has("enabled"):
			_luxury_import_cfg["enabled"] = bool(lid["enabled"])
		if lid.has("spawn_roll"):
			_luxury_import_cfg["spawn_roll"] = clampf(float(lid["spawn_roll"]), 0.0, 0.6)
		if lid.has("lead_min"):
			_luxury_import_cfg["lead_min"] = clampi(int(lid["lead_min"]), 1, 30)
		if lid.has("lead_max"):
			_luxury_import_cfg["lead_max"] = clampi(int(lid["lead_max"]), 1, 40)
		if int(_luxury_import_cfg["lead_max"]) < int(_luxury_import_cfg["lead_min"]):
			_luxury_import_cfg["lead_max"] = int(_luxury_import_cfg["lead_min"])
		if lid.has("qty_min"):
			_luxury_import_cfg["qty_min"] = clampi(int(lid["qty_min"]), 1, 12)
		if lid.has("qty_max"):
			_luxury_import_cfg["qty_max"] = clampi(int(lid["qty_max"]), 1, 16)
		if int(_luxury_import_cfg["qty_max"]) < int(_luxury_import_cfg["qty_min"]):
			_luxury_import_cfg["qty_max"] = int(_luxury_import_cfg["qty_min"])
		if lid.has("max_pending"):
			_luxury_import_cfg["max_pending"] = clampi(int(lid["max_pending"]), 1, 12)
		if lid.has("cost_frac"):
			_luxury_import_cfg["cost_frac"] = clampf(float(lid["cost_frac"]), 0.05, 0.85)
		if lid.has("treasury_take_frac"):
			_luxury_import_cfg["treasury_take_frac"] = clampf(float(lid["treasury_take_frac"]), 0.0, 0.95)
	var role_bonuses: Dictionary = {}
	var prb_raw: Variant = doc.get("port_role_wealth_bonuses", null)
	if typeof(prb_raw) == TYPE_DICTIONARY:
		for rk in (prb_raw as Dictionary).keys():
			role_bonuses[str(rk)] = maxi(0, int((prb_raw as Dictionary)[rk]))
	var chart_raw: Variant = doc.get("chart_areas", null)
	if typeof(chart_raw) == TYPE_ARRAY:
		for ca in chart_raw as Array:
			if typeof(ca) != TYPE_DICTIONARY:
				continue
			var cad: Dictionary = ca as Dictionary
			var caid := str(cad.get("id", ""))
			if caid.is_empty():
				continue
			_chart_area_labels[caid] = str(cad.get("name", caid))
			var desc: String = str(cad.get("description", cad.get("note", "")))
			if not desc.is_empty():
				_chart_area_notes[caid] = desc
	for p in doc.get("ports", []):
		if typeof(p) != TYPE_DICTIONARY:
			continue
		var pd: Dictionary = p
		var idv: Variant = pd.get("id", "")
		var namev: Variant = pd.get("name", idv)
		if str(idv).is_empty():
			continue
		var pid := str(idv)
		_port_names[pid] = str(namev)
		var map_u: float = float(pd.get("map_u", -1.0))
		var map_v: float = float(pd.get("map_v", -1.0))
		if map_u >= 0.0 and map_u <= 1.0 and map_v >= 0.0 and map_v <= 1.0:
			_port_map_uv[pid] = Vector2(map_u, map_v)
		var st: Dictionary = {}
		var init_raw: Variant = pd.get("initial_stock", null)
		if typeof(init_raw) == TYPE_DICTIONARY:
			for gk in (init_raw as Dictionary).keys():
				st[str(gk)] = maxi(0, int((init_raw as Dictionary)[gk]))
		_port_initial_stock[pid] = st
		var n_npc: int = int(pd.get("npc_traders", 4))
		_port_npc_trader_count[pid] = clampi(n_npc, 1, _PORT_NPC_TRADERS_LOAD_MAX)
		var eat_g: int = int(pd.get("population_grain_per_day", 6))
		_port_population_grain[pid] = clampi(eat_g, 0, 120)
		var wine_b: int = int(pd.get("population_wine_per_day", 1))
		_port_population_wine_base[pid] = clampi(wine_b, 0, 40)
		var fish_d: int = int(pd.get("population_fish_per_day", 0))
		_port_population_fish_per_day[pid] = clampi(fish_d, 0, 40)
		var iw: Variant = pd.get("initial_wealth", -1)
		if int(iw) >= 0:
			_port_initial_wealth[pid] = int(iw)
		var role_s: String = str(pd.get("role", ""))
		if not role_s.is_empty():
			_port_roles[pid] = role_s
		var rbonus: int = 0
		if not role_s.is_empty() and role_bonuses.has(role_s):
			rbonus = int(role_bonuses[role_s])
		_port_role_wealth_bonus[pid] = rbonus
		var chart_aid := str(pd.get("chart_area_id", ""))
		if chart_aid.is_empty():
			chart_aid = str(pd.get("chart_area", ""))
		if chart_aid.is_empty():
			chart_aid = _LEDGER_CHART_AREA_FALLBACK
		_port_chart_area_id[pid] = chart_aid
		var exb_raw: Variant = pd.get("population_existential_war_burst_days", _POP_EXISTENTIAL_WAR_BURST_OFF)
		var exb: int = clampi(int(exb_raw), 1, _POP_EXISTENTIAL_WAR_BURST_OFF)
		if exb < _POP_EXISTENTIAL_WAR_BURST_OFF:
			_port_existential_war_burst_days[pid] = exb
		else:
			_port_existential_war_burst_days.erase(pid)
		var war_here: bool = bool(pd.get("at_war", false))
		var war_len: int = clampi(int(pd.get("war_days", _WAR_DEFAULT_DAYS)), 1, 200)
		_port_war_days_remaining[pid] = war_len if war_here else 0
		## Default on: every port runs its own peace→war cycle unless war_recurring is false in world.json.
		var recurring: bool = bool(pd.get("war_recurring", true))
		_port_war_recurring[pid] = recurring
		if war_here:
			_port_war_peace_remaining[pid] = 0
			_port_war_burst_initial[pid] = int(_port_war_days_remaining[pid])
		elif recurring:
			_port_war_peace_remaining[pid] = _rng.randi_range(_WAR_CYCLE_PEACE_MIN, _WAR_CYCLE_PEACE_MAX)
		else:
			_port_war_peace_remaining[pid] = 0
		_port_industrial_metal_per_day[pid] = clampi(int(pd.get("industrial_metal_per_day", 0)), 0, _INDUSTRIAL_SINK_METAL_MAX)
		_port_industrial_wire_per_day[pid] = clampi(int(pd.get("industrial_wire_per_day", 0)), 0, _INDUSTRIAL_SINK_WIRE_MAX)
		_port_industrial_timber_per_day[pid] = clampi(
			int(pd.get("industrial_timber_per_day", 0)), 0, _INDUSTRIAL_SINK_TIMBER_MAX
		)
		_port_industrial_textiles_per_day[pid] = clampi(
			int(pd.get("industrial_textiles_per_day", 0)), 0, _INDUSTRIAL_SINK_TEXTILES_MAX
		)
		var bias_row: Dictionary = {}
		var bias_raw: Variant = pd.get("trade_price_bias", null)
		if typeof(bias_raw) == TYPE_DICTIONARY:
			for bk in (bias_raw as Dictionary).keys():
				var gkb := str(bk)
				var bv: float = float((bias_raw as Dictionary)[bk])
				bias_row[gkb] = clampf(bv, -_TRADE_PRICE_BIAS_CLAMP, _TRADE_PRICE_BIAS_CLAMP)
		_port_trade_price_bias[pid] = bias_row
		var mdd_row: Dictionary = {}
		var mdd_raw: Variant = pd.get("market_demand_per_day", null)
		if typeof(mdd_raw) == TYPE_DICTIONARY:
			for mk in (mdd_raw as Dictionary).keys():
				var gkm := str(mk)
				mdd_row[gkm] = maxf(0.0, float((mdd_raw as Dictionary)[mk]))
		_port_market_demand_override[pid] = mdd_row
		var tol_row: Dictionary = {}
		var tol_raw: Variant = pd.get("tolls", null)
		if typeof(tol_raw) == TYPE_DICTIONARY:
			for tk in (tol_raw as Dictionary).keys():
				var gkt := str(tk)
				var tv: int = clampi(int((tol_raw as Dictionary)[tk]), 0, 80)
				if tv > 0:
					tol_row[gkt] = tv
		_port_good_tolls[pid] = tol_row
		var mint_raw: Variant = pd.get("mint", null)
		if typeof(mint_raw) == TYPE_DICTIONARY:
			var mdmin: Dictionary = mint_raw as Dictionary
			if bool(mdmin.get("enabled", false)):
				_port_mint_cfg[pid] = {
					"gold_per_batch": clampi(int(mdmin.get("gold_per_batch", 1)), 0, 24),
					"silver_per_batch": clampi(int(mdmin.get("silver_per_batch", 2)), 0, 36),
					"coins_per_batch": clampi(int(mdmin.get("coins_per_batch", 72)), 1, 500),
					"max_batches_per_day": clampi(int(mdmin.get("max_batches_per_day", 6)), 1, 40),
					"treasury_sink_frac": clampf(float(mdmin.get("treasury_sink_frac", 0.09)), 0.0, 0.45),
				}
	for lane in doc.get("lanes", []):
		if typeof(lane) != TYPE_DICTIONARY:
			continue
		var ld: Dictionary = lane
		var a: String = str(ld.get("from", ""))
		var b: String = str(ld.get("to", ""))
		var days: int = int(ld.get("days", -1))
		if a.is_empty() or b.is_empty() or days < 0:
			continue
		_lane_days[_lane_key(a, b)] = days
	for nl in doc.get("npc_lanes", []):
		if typeof(nl) != TYPE_DICTIONARY:
			continue
		var nld: Dictionary = nl as Dictionary
		var na: String = str(nld.get("from", ""))
		var nb: String = str(nld.get("to", ""))
		var ndays: int = maxi(1, int(round(float(nld.get("days", 1)))))
		if na.is_empty() or nb.is_empty():
			continue
		_npc_lane_days[_lane_key(na, nb)] = ndays
	for fr in doc.get("farms", []):
		if typeof(fr) != TYPE_DICTIONARY:
			continue
		var fd: Dictionary = fr as Dictionary
		var fid := str(fd.get("id", ""))
		var fname := str(fd.get("name", fid))
		var fport := str(fd.get("port_id", ""))
		if fport.is_empty() or not _port_names.has(fport):
			continue
		_farms.append(
			{
				"id": fid,
				"name": fname,
				"port_id": fport,
				"grain_per_day": maxi(0, int(fd.get("grain_per_day", 0))),
				"wine_per_day": maxi(0, int(fd.get("wine_per_day", 0))),
				"fish_per_day": maxi(0, int(fd.get("fish_per_day", 0))),
			}
		)
	for mn in doc.get("mines", []):
		if typeof(mn) != TYPE_DICTIONARY:
			continue
		var md: Dictionary = mn as Dictionary
		var mid := str(md.get("id", ""))
		var mname := str(md.get("name", mid))
		var mport := str(md.get("port_id", ""))
		if mport.is_empty() or not _port_names.has(mport):
			continue
		_mines.append(
			{
				"id": mid,
				"name": mname,
				"port_id": mport,
				"metal_per_day": maxi(0, int(md.get("metal_per_day", 0))),
				"wire_per_day": maxi(0, int(md.get("wire_per_day", 0))),
				"gold_per_day": maxi(0, int(md.get("gold_per_day", 0))),
				"silver_per_day": maxi(0, int(md.get("silver_per_day", 0))),
			}
		)
	var pc_raw: Variant = doc.get("port_cultures", null)
	if typeof(pc_raw) == TYPE_DICTIONARY:
		for ck in (pc_raw as Dictionary).keys():
			var pk0 := str(ck)
			if _port_names.has(pk0):
				_port_cultures[pk0] = str((pc_raw as Dictionary)[ck])
	var psy_raw: Variant = doc.get("port_shipyards", null)
	if typeof(psy_raw) == TYPE_DICTIONARY:
		for syk in (psy_raw as Dictionary).keys():
			var pk1 := str(syk)
			if not _port_names.has(pk1):
				continue
			var arr_raw: Variant = (psy_raw as Dictionary).get(syk, [])
			var acc: Array = []
			if typeof(arr_raw) == TYPE_ARRAY:
				for x in arr_raw as Array:
					acc.append(str(x))
			_port_shipyard_classes[pk1] = acc
	for pid in _port_names.keys():
		var ps := str(pid)
		if not _port_population_wine_base.has(ps):
			_port_population_wine_base[ps] = 1
		if not _port_war_days_remaining.has(ps):
			_port_war_days_remaining[ps] = 0
		if not _port_war_recurring.has(ps):
			_port_war_recurring[ps] = false
		if not _port_war_peace_remaining.has(ps):
			_port_war_peace_remaining[ps] = 0
		_ensure_war_burst_initial_for_port(ps)
		if not _port_industrial_metal_per_day.has(ps):
			_port_industrial_metal_per_day[ps] = 0
		if not _port_industrial_wire_per_day.has(ps):
			_port_industrial_wire_per_day[ps] = 0
		if not _port_industrial_timber_per_day.has(ps):
			_port_industrial_timber_per_day[ps] = 0
		if not _port_industrial_textiles_per_day.has(ps):
			_port_industrial_textiles_per_day[ps] = 0
		if not _port_population_fish_per_day.has(ps):
			_port_population_fish_per_day[ps] = 0
		if not _port_trade_price_bias.has(ps):
			_port_trade_price_bias[ps] = {}
		if not _port_market_demand_override.has(ps):
			_port_market_demand_override[ps] = {}
		if not _port_chart_area_id.has(ps):
			_port_chart_area_id[ps] = _LEDGER_CHART_AREA_FALLBACK
		var aref: String = str(_port_chart_area_id[ps])
		if not _chart_area_labels.has(aref):
			_chart_area_labels[aref] = "Unknown chart (%s)" % aref
		_init_port_demographics_from_world()
		_init_port_crop_agro_state()
		_build_port_neighbors()
		_rebuild_coastal_shortest_path_cache()
		_rebuild_coastal_shortest_path_cache_npc()
		_bootstrap_recurring_war_timers()
		_ensure_used_hull_listings_for_all_ports()
		_ensure_sim_agent_port_defaults()


func _load_goods(path: String) -> void:
	_goods.clear()
	var text := FileAccess.get_file_as_string(path)
	if text.is_empty():
		push_error("HarboursOfPower: missing goods file: %s" % path)
		return
	var data: Variant = JSON.parse_string(text)
	if data == null or typeof(data) != TYPE_DICTIONARY:
		push_error("HarboursOfPower: invalid goods JSON")
		return
	var doc: Dictionary = data
	for g in doc.get("goods", []):
		if typeof(g) != TYPE_DICTIONARY:
			continue
		var gd: Dictionary = g
		var idv := str(gd.get("id", ""))
		if idv.is_empty():
			continue
		var row: Dictionary = {
			"name": str(gd.get("name", idv)),
			"unit_buy_price": int(gd.get("unit_buy_price", -1)),
			"unit_sell_price": int(gd.get("unit_sell_price", -1)),
			"stock_target": int(gd.get("stock_target", 80)),
			"need_tier": str(gd.get("need_tier", "")),
		}
		if gd.has("market_demand_per_day"):
			row["market_demand_per_day"] = maxf(0.0, float(gd.get("market_demand_per_day", 0.0)))
		if gd.has("wage_per_unit_per_day"):
			row["wage_per_unit_per_day"] = clampf(float(gd.get("wage_per_unit_per_day", 0.0)), 0.0, _MARINE_WAGE_RATE_MAX)
		_goods[idv] = row


func _load_ship_catalog(path: String) -> void:
	_ship_classes.clear()
	var text := FileAccess.get_file_as_string(path)
	if text.is_empty():
		push_error("HarboursOfPower: missing ships file: %s" % path)
		_ship_default_id = "greek_merchant"
		return
	var data: Variant = JSON.parse_string(text)
	if data == null or typeof(data) != TYPE_DICTIONARY:
		push_error("HarboursOfPower: invalid ships JSON")
		_ship_default_id = "greek_merchant"
		return
	var doc: Dictionary = data
	_ship_default_id = str(doc.get("default_player_class", "greek_merchant"))
	for row_raw in doc.get("ships", []):
		if typeof(row_raw) != TYPE_DICTIONARY:
			continue
		var row: Dictionary = row_raw as Dictionary
		var sid := str(row.get("id", ""))
		if sid.is_empty():
			continue
		_ship_classes[sid] = row
	if not _ship_classes.has(_ship_default_id):
		if _ship_classes.has("greek_merchant"):
			_ship_default_id = "greek_merchant"
		elif not _ship_classes.is_empty():
			_ship_default_id = str(_ship_classes.keys()[0])


func _ship_class_defaults() -> Dictionary:
	return {
		"id": "greek_merchant",
		"name": "Merchant hull",
		"category": "merchant",
		"culture": "greek",
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
		"luxury_sell_bonus": {},
		"build": {"labor_mult": 1.0, "timber_mult": 1.0, "textiles_mult": 1.0, "metal_mult": 1.0, "days_mult": 1.0},
	}


func _ship_def(ship_id: String) -> Dictionary:
	var sid := str(ship_id)
	if sid.is_empty() or not _ship_classes.has(sid):
		sid = _ship_default_id
	if not _ship_classes.has(sid):
		return _ship_class_defaults()
	return _ship_classes[sid] as Dictionary


func _player_ship_row() -> Dictionary:
	return _ship_def(player_ship_class_id)


func _npc_ship_row(agent: Dictionary) -> Dictionary:
	return _ship_def(str(agent.get("ship_class_id", _ship_default_id)))


func _ship_build_block(row: Dictionary) -> Dictionary:
	var b: Variant = row.get("build", null)
	if typeof(b) != TYPE_DICTIONARY:
		return {"labor_mult": 1.0, "timber_mult": 1.0, "textiles_mult": 1.0, "metal_mult": 1.0, "days_mult": 1.0}
	return b as Dictionary


func _player_fleet_build_ints() -> Dictionary:
	var row: Dictionary = _player_ship_row()
	var b: Dictionary = _ship_build_block(row)
	return {
		"labor": maxi(1, int(round(float(_FLEET_NEW_SHIP_LABOR_COINS) * float(b.get("labor_mult", 1.0))))),
		"timber": maxi(1, int(round(float(_FLEET_NEW_SHIP_TIMBER) * float(b.get("timber_mult", 1.0))))),
		"textiles": maxi(1, int(round(float(_FLEET_NEW_SHIP_TEXTILES) * float(b.get("textiles_mult", 1.0))))),
		"metal": maxi(1, int(round(float(_FLEET_NEW_SHIP_METAL) * float(b.get("metal_mult", 1.0))))),
		"days": maxi(1, int(round(float(_FLEET_NEW_SHIP_BUILD_DAYS) * float(b.get("days_mult", 1.0))))),
	}


func _npc_fleet_build_ints(agent: Dictionary) -> Dictionary:
	var row: Dictionary = _npc_ship_row(agent)
	var b: Dictionary = _ship_build_block(row)
	return {
		"labor": maxi(1, int(round(float(_FLEET_NEW_SHIP_LABOR_COINS) * float(b.get("labor_mult", 1.0))))),
		"timber": maxi(1, int(round(float(_FLEET_NEW_SHIP_TIMBER) * float(b.get("timber_mult", 1.0))))),
		"textiles": maxi(1, int(round(float(_FLEET_NEW_SHIP_TEXTILES) * float(b.get("textiles_mult", 1.0))))),
		"metal": maxi(1, int(round(float(_FLEET_NEW_SHIP_METAL) * float(b.get("metal_mult", 1.0))))),
		"days": maxi(1, int(round(float(_FLEET_NEW_SHIP_BUILD_DAYS) * float(b.get("days_mult", 1.0))))),
	}


func _player_cultural_ops_scale() -> float:
	var row: Dictionary = _player_ship_row()
	var hull_culture: String = str(row.get("culture", "greek"))
	var cap: String = str(player_captain_culture)
	if cap.is_empty():
		cap = str(_port_cultures.get(player_port_id, "italic"))
	var fom: float = clampf(float(row.get("foreign_ops_mult", 1.1)), 1.0, 1.55)
	if cap == hull_culture:
		return 1.0
	return fom


func _player_officer_due_coins() -> int:
	var sh: int = get_player_fleet_ships()
	var row: Dictionary = _player_ship_row()
	var oph: int = maxi(1, int(row.get("officer_pay_per_hull", 1)))
	var pay_sc: float = float(oph) * _player_cultural_ops_scale()
	var officer_leg: int = maxi(1, int(ceil(float(sh * _SHIP_OFFICER_PAY_DAILY) * pay_sc)))
	return officer_leg + _marine_wage_due_for_cargo(player_cargo, pay_sc)


func _npc_cultural_ops_scale(agent: Dictionary) -> Dictionary:
	var row: Dictionary = _npc_ship_row(agent)
	var hull_culture: String = str(row.get("culture", "greek"))
	var home: String = str(agent.get("home_port", ""))
	var cap0: String = str(agent.get("captain_culture", _port_cultures.get(home, "greek")))
	var fom: float = clampf(float(row.get("foreign_ops_mult", 1.1)), 1.0, 1.55)
	if cap0 == hull_culture:
		return {"wine_scale": 1.0, "officer_scale": 1.0}
	return {"wine_scale": fom, "officer_scale": fom}


func _npc_officer_due_coins(agent: Dictionary) -> int:
	_ensure_npc_ship_fields(agent)
	var sh: int = clampi(int(agent.get("fleet_ships", 1)), 1, _FLEET_MAX_SHIPS)
	var culd: Dictionary = _npc_cultural_ops_scale(agent)
	var oph: int = maxi(1, int(_npc_ship_row(agent).get("officer_pay_per_hull", 1)))
	var pay_sc: float = float(oph) * float(culd.get("officer_scale", 1.0))
	var officer_leg: int = maxi(1, int(ceil(float(sh * _SHIP_OFFICER_PAY_DAILY) * pay_sc)))
	var cr: Variant = agent.get("cargo", null)
	var cargo_d: Dictionary = {}
	if typeof(cr) == TYPE_DICTIONARY:
		cargo_d = cr as Dictionary
	return officer_leg + _marine_wage_due_for_cargo(cargo_d, pay_sc)


func _player_age_stress_01() -> float:
	return clampf(float(player_ship_age_days) / 2200.0, 0.0, 1.0)


func _default_ship_class_for_port(port_id: String) -> String:
	var opts: PackedStringArray = _orderable_shipyard_ids_at_port(str(port_id))
	if opts.size() > 0:
		return str(opts[0])
	return _ship_default_id


func _orderable_shipyard_ids_at_port(port_id: String) -> PackedStringArray:
	var ps := str(port_id)
	var out: PackedStringArray = PackedStringArray()
	if not _port_names.has(ps):
		return out
	var raw: Variant = _port_shipyard_classes.get(ps, null)
	if typeof(raw) == TYPE_ARRAY:
		for x in raw as Array:
			var sid := str(x)
			if sid.is_empty() or not _ship_classes.has(sid):
				continue
			var row: Dictionary = _ship_classes[sid] as Dictionary
			if bool(row.get("player_orderable", true)):
				out.append(sid)
	return out


func _ship_is_orderable_at_port(port_id: String, ship_id: String) -> bool:
	var sid := str(ship_id)
	for x in _orderable_shipyard_ids_at_port(port_id):
		if str(x) == sid:
			return true
	return false


func get_orderable_ship_classes_at_port(port_id: String) -> Array:
	var out: Array = []
	for sid in _orderable_shipyard_ids_at_port(port_id):
		var row: Dictionary = _ship_def(sid)
		out.append(
			{
				"id": sid,
				"name": str(row.get("name", sid)),
				"category": str(row.get("category", "")),
				"identity": str(row.get("identity", "")),
				"culture": str(row.get("culture", "")),
			}
		)
	return out


func get_player_ship_class_id() -> String:
	if player_ship_class_id.is_empty():
		return _ship_default_id
	return player_ship_class_id


func get_player_ship_display_name() -> String:
	return str(_player_ship_row().get("name", get_player_ship_class_id()))


func player_can_refit_to_ship_class(to_class_id: String) -> bool:
	if is_at_sea():
		return false
	if player_fleet_shipyard_days_remaining > 0:
		return false
	var tid := str(to_class_id)
	if tid.is_empty() or tid == get_player_ship_class_id():
		return false
	if not _ship_is_orderable_at_port(player_port_id, tid):
		return false
	return player_money >= _SHIP_REFIT_LABOR_COINS


func try_player_refit_ship_class(to_class_id: String) -> bool:
	if player_fleet_shipyard_days_remaining > 0:
		return false
	if not player_can_refit_to_ship_class(to_class_id):
		return false
	var tid := str(to_class_id)
	player_money = clampi(player_money - _SHIP_REFIT_LABOR_COINS, 0, _MAX_PURSE_COINS)
	player_ship_class_id = tid
	player_ship_age_days = maxi(0, player_ship_age_days - 140)
	money_changed.emit()
	cargo_changed.emit()
	market_changed.emit()
	return true


func try_set_player_captain_culture(culture_tag: String) -> bool:
	if is_at_sea():
		return false
	var c := str(culture_tag)
	if c.is_empty():
		return false
	player_captain_culture = c
	return true


func _ensure_player_ship_identity_post_load() -> void:
	if player_ship_class_id.is_empty() or not _ship_classes.has(player_ship_class_id):
		player_ship_class_id = _default_ship_class_for_port(player_port_id)
	if player_captain_culture.is_empty():
		player_captain_culture = str(_port_cultures.get(player_port_id, "italic"))
	_ensure_player_voyage_role_and_contract()
	while get_player_cargo_used() > get_player_cargo_capacity():
		_player_trim_cargo_to_capacity()


func _is_valid_voyage_role(role: String) -> bool:
	var r := str(role)
	return r == _VOYAGE_ROLE_MERCHANT or r == _VOYAGE_ROLE_ESCORT or r == _VOYAGE_ROLE_PIRATE


## Escort job scaffold: `employer_id` (NPC id), `pay_coins`, `origin`, `dest`, `started_day` (calendar).
func _sanitize_escort_contract(raw: Dictionary) -> Dictionary:
	var out: Dictionary = {}
	var eid: int = int(raw.get("employer_id", -1))
	out["employer_id"] = clampi(eid, -1, 999999)
	out["pay_coins"] = clampi(int(raw.get("pay_coins", 0)), 0, _MAX_PURSE_COINS)
	var o0: String = str(raw.get("origin", ""))
	var d0: String = str(raw.get("dest", ""))
	out["origin"] = o0 if _port_names.has(o0) else ""
	out["dest"] = d0 if _port_names.has(d0) else ""
	out["started_day"] = clampi(int(raw.get("started_day", 0)), 0, 9999999)
	return out


func _ensure_player_voyage_role_and_contract() -> void:
	if player_voyage_role.is_empty() or not _is_valid_voyage_role(player_voyage_role):
		player_voyage_role = _VOYAGE_ROLE_MERCHANT
	if typeof(player_escort_contract) != TYPE_DICTIONARY:
		player_escort_contract = {}
	else:
		player_escort_contract = _sanitize_escort_contract(player_escort_contract as Dictionary)
	if player_voyage_role != _VOYAGE_ROLE_ESCORT:
		player_escort_contract.clear()


func _ensure_npc_voyage_role_and_contract(ag: Dictionary) -> void:
	var r0: String = str(ag.get("voyage_role", _VOYAGE_ROLE_MERCHANT))
	ag["voyage_role"] = r0 if _is_valid_voyage_role(r0) else _VOYAGE_ROLE_MERCHANT
	var cr: Variant = ag.get("escort_contract", null)
	if typeof(cr) != TYPE_DICTIONARY:
		ag["escort_contract"] = {}
	else:
		ag["escort_contract"] = _sanitize_escort_contract(cr as Dictionary)
	if str(ag.get("voyage_role", "")) != _VOYAGE_ROLE_ESCORT:
		(ag["escort_contract"] as Dictionary).clear()


func _apply_player_escort_contract_on_voyage_arrival() -> void:
	player_escort_contract.clear()
	if player_voyage_role == _VOYAGE_ROLE_ESCORT:
		player_voyage_role = _VOYAGE_ROLE_MERCHANT


func _apply_npc_escort_contract_on_voyage_arrival(ag: Dictionary) -> void:
	if typeof(ag.get("escort_contract", null)) == TYPE_DICTIONARY:
		(ag["escort_contract"] as Dictionary).clear()
	else:
		ag["escort_contract"] = {}
	if str(ag.get("voyage_role", _VOYAGE_ROLE_MERCHANT)) == _VOYAGE_ROLE_ESCORT:
		ag["voyage_role"] = _VOYAGE_ROLE_MERCHANT


func _ensure_npc_convoy_fields(ag: Dictionary) -> void:
	if not ag.has("convoy_leader_id"):
		ag["convoy_leader_id"] = 0
	else:
		ag["convoy_leader_id"] = maxi(0, int(ag.get("convoy_leader_id", 0)))
	var mids: Variant = ag.get("convoy_member_ids", null)
	if typeof(mids) != TYPE_ARRAY:
		ag["convoy_member_ids"] = []
	else:
		var out_m: Array = []
		var seen: Dictionary = {}
		for it in mids as Array:
			var mid: int = int(it)
			if mid <= 0 or seen.has(mid):
				continue
			seen[mid] = true
			out_m.append(mid)
			if out_m.size() >= 8:
				break
		ag["convoy_member_ids"] = out_m
	var scat: Variant = ag.get("scattered_ids", null)
	if typeof(scat) != TYPE_ARRAY:
		ag["scattered_ids"] = []
	else:
		var out_s: Array = []
		var seen2: Dictionary = {}
		for it2 in scat as Array:
			var sid: int = int(it2)
			if sid <= 0 or seen2.has(sid):
				continue
			seen2[sid] = true
			out_s.append(sid)
			if out_s.size() >= 16:
				break
		ag["scattered_ids"] = out_s
	ag["convoy_formed"] = bool(ag.get("convoy_formed", false))
	if not ag.has("convoy_escort_id"):
		ag["convoy_escort_id"] = 0
	else:
		ag["convoy_escort_id"] = maxi(0, int(ag.get("convoy_escort_id", 0)))
	if not ag.has("contact_candidate_bias"):
		ag["contact_candidate_bias"] = 0.0
	else:
		ag["contact_candidate_bias"] = clampf(float(ag.get("contact_candidate_bias", 0.0)), 0.0, 1.0)
	if not ag.has("convoy_escort_player"):
		ag["convoy_escort_player"] = false
	else:
		ag["convoy_escort_player"] = bool(ag.get("convoy_escort_player", false))
	if bool(ag.get("convoy_escort_player", false)):
		ag["convoy_escort_id"] = 0
	else:
		var esi: int = int(ag.get("convoy_escort_id", 0))
		if esi > 0:
			ag["convoy_escort_player"] = false


func _ensure_npc_escort_reputation_fields(ag: Dictionary) -> void:
	if not ag.has("escort_reliability"):
		ag["escort_reliability"] = 0.55
	else:
		ag["escort_reliability"] = clampf(float(ag.get("escort_reliability", 0.55)), 0.0, 1.0)


func _npc_convoy_is_follower(ag: Dictionary) -> bool:
	var self_id: int = int(ag.get("id", 0))
	var cl: int = int(ag.get("convoy_leader_id", 0))
	return cl > 0 and cl != self_id


func _npc_index_agents_by_id() -> Dictionary:
	var m: Dictionary = {}
	for item in _npc_agents:
		if typeof(item) != TYPE_DICTIONARY:
			continue
		var ag: Dictionary = item as Dictionary
		m[int(ag.get("id", -1))] = ag
	return m


func _npc_convoy_reset_docked(ag: Dictionary) -> void:
	ag["convoy_leader_id"] = 0
	ag["convoy_member_ids"] = []
	ag["convoy_formed"] = false
	ag["convoy_escort_id"] = 0
	ag["convoy_escort_player"] = false
	ag["scattered_ids"] = []
	ag["contact_candidate_bias"] = 0.0


func _npc_convoy_fixup_removed_agent_id(dead_id: int) -> void:
	if dead_id <= 0:
		return
	for item in _npc_agents:
		if typeof(item) != TYPE_DICTIONARY:
			continue
		var ag: Dictionary = item as Dictionary
		if int(ag.get("convoy_escort_id", 0)) == dead_id:
			ag["convoy_escort_id"] = 0
		if int(ag.get("convoy_leader_id", 0)) == dead_id:
			ag["convoy_leader_id"] = 0
			ag["convoy_member_ids"] = []
			ag["convoy_formed"] = false
		var mm: Array = ag.get("convoy_member_ids", []) as Array
		if mm.is_empty():
			continue
		var nm: Array = []
		for it in mm:
			if int(it) != dead_id:
				nm.append(int(it))
		ag["convoy_member_ids"] = nm
		if nm.is_empty() and int(ag.get("convoy_leader_id", 0)) == int(ag.get("id", 0)):
			ag["convoy_formed"] = false
	if str(player_voyage_role) == _VOYAGE_ROLE_ESCORT:
		var emdead: int = int(player_escort_contract.get("employer_id", -9))
		if emdead == dead_id:
			player_escort_contract.clear()
			player_voyage_role = _VOYAGE_ROLE_MERCHANT


func _normalize_npc_convoy_invariants(ag: Dictionary) -> void:
	_ensure_npc_convoy_fields(ag)
	var vdays: int = int(ag.get("voyage_days_remaining", 0))
	var self_id: int = int(ag.get("id", 0))
	var cl: int = int(ag.get("convoy_leader_id", 0))
	if vdays <= 0:
		_npc_convoy_reset_docked(ag)
		return
	var dest_me: String = str(ag.get("voyage_dest_id", ""))
	if cl == self_id:
		var mids: Array = ag.get("convoy_member_ids", []) as Array
		if mids.is_empty():
			ag["convoy_formed"] = false
			ag["convoy_leader_id"] = 0
			ag["convoy_escort_id"] = 0
			ag["convoy_escort_player"] = false
			return
		var idx: Dictionary = _npc_index_agents_by_id()
		var keep: Array = []
		for it in mids:
			var mid: int = int(it)
			if mid == self_id:
				continue
			if not idx.has(mid):
				continue
			var oth: Dictionary = idx[mid] as Dictionary
			if _npc_convoy_is_follower(oth) and int(oth.get("convoy_leader_id", 0)) == self_id:
				if str(oth.get("voyage_dest_id", "")) == dest_me and int(oth.get("voyage_days_remaining", 0)) > 0:
					keep.append(mid)
		ag["convoy_member_ids"] = keep
		if keep.is_empty():
			ag["convoy_formed"] = false
			ag["convoy_leader_id"] = 0
			ag["convoy_escort_id"] = 0
			ag["convoy_escort_player"] = false
			return
		var es0: int = int(ag.get("convoy_escort_id", 0))
		var esc_pl: bool = bool(ag.get("convoy_escort_player", false))
		if esc_pl:
			var ok_p: bool = (
				str(player_voyage_role) == _VOYAGE_ROLE_ESCORT
				and int(player_escort_contract.get("employer_id", -9)) == self_id
				and str(voyage_dest_id) == dest_me
				and voyage_days_remaining > 0
			)
			if not ok_p:
				ag["convoy_escort_player"] = false
		elif es0 > 0:
			if not idx.has(es0):
				ag["convoy_escort_id"] = 0
			else:
				var ex: Dictionary = idx[es0] as Dictionary
				var ok_es: bool = (
					str(ex.get("voyage_role", "")) == _VOYAGE_ROLE_ESCORT
					and int(ex.get("convoy_leader_id", 0)) == self_id
					and str(ex.get("voyage_dest_id", "")) == dest_me
					and int(ex.get("voyage_days_remaining", 0)) > 0
				)
				if not ok_es:
					ag["convoy_escort_id"] = 0
		return
	if cl > 0 and cl != self_id:
		var idx2: Dictionary = _npc_index_agents_by_id()
		var ok: bool = false
		if idx2.has(cl):
			var L: Dictionary = idx2[cl] as Dictionary
			if (
				int(L.get("voyage_days_remaining", 0)) > 0
				and str(L.get("voyage_dest_id", "")) == dest_me
				and int(L.get("convoy_leader_id", 0)) == cl
			):
				ok = true
		if not ok:
			ag["convoy_leader_id"] = 0
			ag["convoy_member_ids"] = []
			ag["convoy_formed"] = false
			if str(ag.get("voyage_role", "")) == _VOYAGE_ROLE_ESCORT:
				_apply_npc_escort_contract_on_voyage_arrival(ag)


func _npc_voyage_facing_params(agent: Dictionary, here: String, dest: String) -> Dictionary:
	if here.is_empty() or dest.is_empty() or not _port_names.has(here) or not _port_names.has(dest):
		return {}
	_ensure_npc_risk_aversion(agent)
	var plan: Dictionary = _voyage_plan(here, dest, clampf(float(agent.get("risk_aversion", 0.5)), 0.0, 1.0), true)
	var d: int = int(plan.get("days", -1))
	if d < 0:
		return {}
	_ensure_npc_ship_fields(agent)
	var nrow: Dictionary = _npc_ship_row(agent)
	var nvm: float = clampf(float(nrow.get("voyage_day_mult", 1.0)), 0.45, 2.2)
	d = maxi(1, int(ceil(float(d) * nvm)))
	var nop0: float = clampf(float(plan.get("open_01", _VOYAGE_COASTAL_OPENNESS)), 0.0, 1.0)
	var nox: float = clampf(float(nrow.get("open_sea_exposure_mul", 1.0)), 0.55, 1.5)
	var open_01: float = clampf(nop0 * nox, 0.0, 1.0)
	return {"days": d, "open_01": open_01}


func _npc_convoy_join_roll(leader: Dictionary, member: Dictionary, _dest: String, route_open_01: float) -> bool:
	var p: float = 0.38
	if str(leader.get("home_port", "")) == str(member.get("home_port", "")):
		p += 0.14
	if str(leader.get("captain_culture", "")) == str(member.get("captain_culture", "")):
		p += 0.10
	var a: float = 0.5 * (_npc_trait_f(leader, _NPC_TRAIT_AGREE) + _npc_trait_f(member, _NPC_TRAIT_AGREE))
	p += 0.18 * (a - 0.5)
	var nmem: float = _npc_trait_f(member, _NPC_TRAIT_NEURO)
	p *= 1.0 - 0.28 * route_open_01 * nmem
	p = clampf(p, 0.06, 0.92)
	return _rng.randf() < p


func _npc_escort_candidate_hull(agent: Dictionary) -> bool:
	_ensure_npc_ship_fields(agent)
	var nrow: Dictionary = _npc_ship_row(agent)
	var cat: String = str(nrow.get("category", "")).to_lower()
	if cat == "galley":
		return true
	var vm: float = clampf(float(nrow.get("voyage_day_mult", 1.0)), 0.45, 2.2)
	return vm <= _ESCORT_HULL_FAST_VOYAGE_MULT


func _npc_escort_job_pay_offer(days: int, open_01: float) -> int:
	var raw: int = _ESCORT_PAY_BASE + days * _ESCORT_PAY_PER_DAY + int(round(float(_ESCORT_PAY_OPEN_MUL) * open_01))
	var raw_s: int = raw
	return clampi(
		raw_s,
		_ESCORT_PAY_MIN,
		_ESCORT_PAY_MAX
	)


func _player_escort_traits_dummy_for_roll() -> Dictionary:
	return {
		_NPC_TRAIT_OPEN: 0.52,
		_NPC_TRAIT_CONSC: 0.52,
		_NPC_TRAIT_EXTRA: 0.52,
		_NPC_TRAIT_AGREE: 0.52,
		_NPC_TRAIT_NEURO: 0.52,
	}


func _player_escort_candidate_hull() -> bool:
	var nrow: Dictionary = _player_ship_row()
	var cat: String = str(nrow.get("category", "")).to_lower()
	if cat == "galley":
		return true
	var vm: float = clampf(float(nrow.get("voyage_day_mult", 1.0)), 0.45, 2.2)
	return vm <= _ESCORT_HULL_FAST_VOYAGE_MULT


func _player_try_hire_as_convoy_escort(
	leader: Dictionary, here: String, dest: String, d_max: int, op_max: float, pay_paid: int
) -> void:
	if not player_offers_convoy_escort:
		return
	if str(player_voyage_role) != _VOYAGE_ROLE_MERCHANT:
		return
	if voyage_days_remaining != 0:
		return
	if str(player_port_id) != here:
		return
	if not _player_escort_candidate_hull():
		return
	if not _npc_escort_accept_job_roll(_player_escort_traits_dummy_for_roll(), pay_paid, op_max):
		return
	var lid: int = int(leader.get("id", 0))
	if lid <= 0:
		return
	_ensure_npc_convoy_fields(leader)
	leader["convoy_escort_id"] = 0
	leader["convoy_escort_player"] = true
	player_voyage_role = _VOYAGE_ROLE_ESCORT
	player_escort_contract = _sanitize_escort_contract(
		{
			"employer_id": lid,
			"pay_coins": pay_paid,
			"origin": here,
			"dest": dest,
			"started_day": current_day,
		}
	)
	voyage_dest_id = dest
	voyage_days_remaining = d_max
	player_voyage_booked_days = d_max
	player_voyage_open_sea_01 = op_max
	_transfer_temple_pending_storm_into_active_voyage_bless()


func _player_escort_pay_on_convoy_arrival(employer: Dictionary) -> int:
	if str(player_voyage_role) != _VOYAGE_ROLE_ESCORT:
		return 0
	var ct: Variant = player_escort_contract
	if typeof(ct) != TYPE_DICTIONARY:
		return 0
	var ctd: Dictionary = ct as Dictionary
	if int(ctd.get("employer_id", -2)) != int(employer.get("id", -3)):
		return 0
	var promised: int = clampi(int(ctd.get("pay_coins", 0)), 0, _ESCORT_PAY_MAX)
	if promised <= 0:
		return 0
	var ep: int = clampi(int(employer.get("money", 0)), 0, _MAX_PURSE_COINS)
	var paid: int = mini(promised, ep)
	if paid <= 0:
		return 0
	employer["money"] = clampi(ep - paid, 0, _MAX_PURSE_COINS)
	player_money = clampi(player_money + paid, 0, _MAX_PURSE_COINS)
	_escort_player_coins_paid += paid
	return paid


func _player_finish_escort_on_npc_convoy_arrival(employer: Dictionary, dest: String) -> void:
	voyage_days_remaining = 0
	voyage_dest_id = ""
	player_voyage_booked_days = 0
	player_voyage_open_sea_01 = 0.0
	player_voyage_weather_bless_p_sub = 0.0
	if _port_names.has(dest):
		player_port_id = dest
	_apply_player_escort_contract_on_voyage_arrival()
	voyage_completed.emit(player_port_id)
	money_changed.emit()


func _player_escort_combat_flee(leader: Dictionary) -> void:
	leader["convoy_escort_id"] = 0
	leader["convoy_escort_player"] = false
	player_escort_contract.clear()
	player_voyage_role = _VOYAGE_ROLE_MERCHANT
	_pirate_metrics_flees += 1


func _sync_player_escort_with_employer_after_npc_advance() -> void:
	if str(player_voyage_role) != _VOYAGE_ROLE_ESCORT:
		return
	if voyage_days_remaining <= 0:
		return
	var eid: int = int(player_escort_contract.get("employer_id", -9))
	if eid <= 0:
		_apply_player_escort_contract_on_voyage_arrival()
		return
	var idxe: Dictionary = _npc_index_agents_by_id()
	if not idxe.has(eid):
		_apply_player_escort_contract_on_voyage_arrival()
		return
	var boss: Dictionary = idxe[eid] as Dictionary
	if not bool(boss.get("convoy_escort_player", false)):
		_apply_player_escort_contract_on_voyage_arrival()
		return
	var bd: int = int(boss.get("voyage_days_remaining", 0))
	var dst: String = str(boss.get("voyage_dest_id", ""))
	voyage_days_remaining = maxi(0, bd)
	voyage_dest_id = dst
	player_voyage_booked_days = int(boss.get("voyage_booked_days", bd))
	player_voyage_open_sea_01 = clampf(float(boss.get("voyage_open_sea_01", 0.0)), 0.0, 1.0)


func _npc_escort_accept_job_roll(escort_candidate: Dictionary, pay_coins: int, route_open_01: float) -> bool:
	var p: float = 0.18 + float(pay_coins) / 620.0
	if _npc_escort_candidate_hull(escort_candidate):
		p += 0.10
	var exv: float = _npc_trait_f(escort_candidate, _NPC_TRAIT_EXTRA)
	var agr: float = _npc_trait_f(escort_candidate, _NPC_TRAIT_AGREE)
	var neu: float = _npc_trait_f(escort_candidate, _NPC_TRAIT_NEURO)
	p += 0.12 * (exv - 0.5) + 0.10 * (agr - 0.5)
	p -= 0.20 * route_open_01 * neu
	p = clampf(p, 0.04, 0.82)
	return _rng.randf() < p


func _npc_try_hire_escort_for_convoy(
	leader: Dictionary, follower_ids: Array, here: String, dest: String, d_max: int, op_max: float
) -> void:
	_ensure_npc_convoy_fields(leader)
	leader["convoy_escort_id"] = 0
	leader["convoy_escort_player"] = false
	if follower_ids.is_empty():
		return
	var lid: int = int(leader.get("id", 0))
	var excluded: Dictionary = {}
	excluded[lid] = true
	for it in follower_ids:
		excluded[int(it)] = true
	var pay_want: int = _npc_escort_job_pay_offer(d_max, op_max)
	var purse: int = clampi(int(leader.get("money", 0)), 0, _MAX_PURSE_COINS)
	var reserve: int = mini(48, maxi(12, _npc_officer_due_coins(leader)))
	var pay_paid: int = clampi(
		mini(pay_want, purse - reserve),
		_ESCORT_PAY_MIN,
		_ESCORT_PAY_MAX
	)
	if pay_paid < _ESCORT_PAY_MIN or purse < pay_paid + reserve:
		return
	var cands: Array = []
	for item in _npc_agents:
		if typeof(item) != TYPE_DICTIONARY:
			continue
		var c: Dictionary = item as Dictionary
		var cid: int = int(c.get("id", 0))
		if excluded.has(cid) or cid == lid:
			continue
		if int(c.get("voyage_days_remaining", 0)) != 0:
			continue
		if str(c.get("docked_port", "")) != here:
			continue
		if str(c.get("voyage_role", _VOYAGE_ROLE_MERCHANT)) != _VOYAGE_ROLE_MERCHANT:
			continue
		if not _npc_escort_candidate_hull(c):
			continue
		cands.append(c)
	for si in range(cands.size() - 1, 0, -1):
		var ji: int = _rng.randi_range(0, si)
		var td: Dictionary = cands[si] as Dictionary
		cands[si] = cands[ji]
		cands[ji] = td
	for cand in cands:
		if not _npc_escort_accept_job_roll(cand as Dictionary, pay_paid, op_max):
			continue
		var esc: Dictionary = cand as Dictionary
		_ensure_npc_escort_reputation_fields(esc)
		esc["voyage_role"] = _VOYAGE_ROLE_ESCORT
		esc["escort_contract"] = _sanitize_escort_contract(
			{
				"employer_id": lid,
				"pay_coins": pay_paid,
				"origin": here,
				"dest": dest,
				"started_day": current_day,
			}
		)
		_ensure_npc_convoy_fields(esc)
		esc["convoy_leader_id"] = lid
		esc["convoy_member_ids"] = []
		esc["convoy_formed"] = true
		esc["scattered_ids"] = []
		esc["contact_candidate_bias"] = 0.0
		esc["voyage_dest_id"] = dest
		esc["voyage_days_remaining"] = d_max
		esc["voyage_booked_days"] = d_max
		esc["voyage_open_sea_01"] = op_max
		esc["docked_port"] = ""
		leader["convoy_escort_id"] = int(esc.get("id", 0))
		leader["convoy_escort_player"] = false
		return
	_player_try_hire_as_convoy_escort(leader, here, dest, d_max, op_max, pay_paid)


func _npc_escort_reliability_apply(escort: Dictionary, full_pay: bool, promised_pay: int) -> void:
	_ensure_npc_escort_reputation_fields(escort)
	var r: float = float(escort.get("escort_reliability", 0.55))
	if full_pay and promised_pay > 0:
		r = clampf(r + 0.035, 0.0, 1.0)
	elif promised_pay > 0:
		r = clampf(r - 0.028, 0.0, 1.0)
	else:
		r = clampf(r - 0.06, 0.0, 1.0)
	escort["escort_reliability"] = r


func _npc_escort_pay_on_convoy_arrival(employer: Dictionary, escort: Dictionary) -> int:
	if str(escort.get("voyage_role", "")) != _VOYAGE_ROLE_ESCORT:
		return 0
	var ct: Variant = escort.get("escort_contract", null)
	if typeof(ct) != TYPE_DICTIONARY:
		return 0
	var ctd: Dictionary = ct as Dictionary
	if int(ctd.get("employer_id", -2)) != int(employer.get("id", -3)):
		return 0
	var promised: int = clampi(int(ctd.get("pay_coins", 0)), 0, _ESCORT_PAY_MAX)
	if promised <= 0:
		return 0
	var ep: int = clampi(int(employer.get("money", 0)), 0, _MAX_PURSE_COINS)
	var paid: int = mini(promised, ep)
	if paid <= 0:
		_npc_escort_reliability_apply(escort, false, promised)
		return 0
	employer["money"] = clampi(ep - paid, 0, _MAX_PURSE_COINS)
	escort["money"] = clampi(int(escort.get("money", 0)) + paid, 0, _MAX_PURSE_COINS)
	_npc_escort_reliability_apply(escort, paid >= promised, promised)
	return paid


func _npc_finish_npc_voyage_arrival(ag: Dictionary, dest: String) -> void:
	_npc_apply_crop_information_on_arrival(ag, dest)
	ag["voyage_dest_id"] = ""
	ag["voyage_days_remaining"] = 0
	ag["voyage_booked_days"] = 0
	ag["voyage_open_sea_01"] = 0.0
	if _port_names.has(dest):
		ag["docked_port"] = dest
	else:
		var home: String = str(ag.get("home_port", ""))
		if _port_names.has(home):
			ag["docked_port"] = home
		elif not _port_names.is_empty():
			ag["docked_port"] = str(_port_names.keys()[0])
		else:
			ag["docked_port"] = ""
	_apply_npc_escort_contract_on_voyage_arrival(ag)
	_npc_convoy_reset_docked(ag)
	_npc_try_fulfill_city_grain_contract_on_arrival(ag, dest)


func _npc_depart_solo_merchant(agent: Dictionary, here: String, dest: String) -> void:
	var vf: Dictionary = _npc_voyage_facing_params(agent, here, dest)
	if vf.is_empty():
		return
	var d: int = int(vf.get("days", 1))
	var op: float = float(vf.get("open_01", _VOYAGE_COASTAL_OPENNESS))
	_ensure_npc_convoy_fields(agent)
	agent["convoy_leader_id"] = 0
	agent["convoy_member_ids"] = []
	agent["convoy_formed"] = false
	agent["convoy_escort_id"] = 0
	agent["convoy_escort_player"] = false
	agent["scattered_ids"] = []
	agent["contact_candidate_bias"] = 0.0
	agent["voyage_dest_id"] = dest
	agent["voyage_days_remaining"] = d
	agent["voyage_booked_days"] = d
	agent["voyage_open_sea_01"] = op
	agent["voyage_origin_port_id"] = here
	agent["docked_port"] = ""


func _npc_depart_convoy_group(leader: Dictionary, followers: Array, here: String, dest: String) -> void:
	var ships: Array = [leader]
	for f in followers:
		ships.append(f as Dictionary)
	var d_max: int = 1
	var op_max: float = 0.0
	for s in ships:
		var ags: Dictionary = s as Dictionary
		var vf: Dictionary = _npc_voyage_facing_params(ags, here, dest)
		if vf.is_empty():
			return
		d_max = maxi(d_max, int(vf.get("days", 1)))
		op_max = maxf(op_max, float(vf.get("open_01", 0.0)))
	op_max = clampf(op_max, 0.0, 1.0)
	var lid: int = int(leader.get("id", 0))
	var fids: Array = []
	for s2 in followers:
		fids.append(int((s2 as Dictionary).get("id", 0)))
	_ensure_npc_convoy_fields(leader)
	leader["convoy_escort_id"] = 0
	leader["convoy_escort_player"] = false
	leader["convoy_leader_id"] = lid
	leader["convoy_member_ids"] = fids.duplicate()
	leader["convoy_formed"] = true
	leader["scattered_ids"] = []
	leader["contact_candidate_bias"] = _rng.randf()
	leader["voyage_dest_id"] = dest
	leader["voyage_days_remaining"] = d_max
	leader["voyage_booked_days"] = d_max
	leader["voyage_open_sea_01"] = op_max
	leader["voyage_origin_port_id"] = here
	leader["docked_port"] = ""
	for s3 in followers:
		var fw: Dictionary = s3 as Dictionary
		_ensure_npc_convoy_fields(fw)
		fw["convoy_leader_id"] = lid
		fw["convoy_member_ids"] = []
		fw["convoy_formed"] = true
		fw["scattered_ids"] = []
		fw["contact_candidate_bias"] = 0.0
		fw["voyage_dest_id"] = dest
		fw["voyage_days_remaining"] = d_max
		fw["voyage_booked_days"] = d_max
		fw["voyage_open_sea_01"] = op_max
		fw["voyage_origin_port_id"] = here
		fw["docked_port"] = ""
	_npc_try_hire_escort_for_convoy(leader, fids, here, dest, d_max, op_max)


func _npc_convoy_process_depart_group(
	_pid: String, dest: String, mut_pool: Array, used_global: Dictionary
) -> void:
	while mut_pool.size() > 0:
		var leader: Dictionary = mut_pool[0] as Dictionary
		var lid: int = int(leader.get("id", 0))
		if used_global.has(lid):
			mut_pool.remove_at(0)
			continue
		var vf0: Dictionary = _npc_voyage_facing_params(leader, _pid, dest)
		if vf0.is_empty():
			mut_pool.remove_at(0)
			continue
		mut_pool.remove_at(0)
		var route_open: float = float(vf0.get("open_01", 0.0))
		var followers: Array = []
		var idx: int = 0
		while idx < mut_pool.size() and followers.size() < _CONVOY_MAX_MERCHANTS - 1:
			var cand: Dictionary = mut_pool[idx] as Dictionary
			var cid: int = int(cand.get("id", 0))
			if used_global.has(cid):
				mut_pool.remove_at(idx)
				continue
			if _npc_convoy_join_roll(leader, cand, dest, route_open):
				followers.append(cand)
				mut_pool.remove_at(idx)
				continue
			idx += 1
		if followers.is_empty():
			_npc_depart_solo_merchant(leader, _pid, dest)
			used_global[lid] = true
		else:
			_npc_depart_convoy_group(leader, followers, _pid, dest)
			used_global[lid] = true
			for fw in followers:
				used_global[int((fw as Dictionary).get("id", 0))] = true


func _npc_convoy_formation_and_depart_tick() -> void:
	if block_npc_merchant_voyages:
		return
	if _port_names.size() < 2:
		return
	var used_global: Dictionary = {}
	var port_list: Array = _port_names.keys()
	for si in range(port_list.size() - 1, 0, -1):
		var ji: int = _rng.randi_range(0, si)
		var tps: String = str(port_list[si])
		port_list[si] = port_list[ji]
		port_list[ji] = tps
	for _pi in range(port_list.size()):
		var pid: String = str(port_list[_pi])
		if not _port_names.has(pid):
			continue
		var docked: Array = []
		for item in _npc_agents:
			if typeof(item) != TYPE_DICTIONARY:
				continue
			var ag: Dictionary = item as Dictionary
			if int(ag.get("voyage_days_remaining", 0)) != 0:
				continue
			if str(ag.get("docked_port", "")) != pid:
				continue
			if str(ag.get("voyage_role", _VOYAGE_ROLE_MERCHANT)) != _VOYAGE_ROLE_MERCHANT:
				continue
			docked.append(ag)
		for sj in range(docked.size() - 1, 0, -1):
			var jj: int = _rng.randi_range(0, sj)
			var td: Dictionary = docked[sj] as Dictionary
			docked[sj] = docked[jj]
			docked[jj] = td
		var proposals: Array = []
		for ag2 in docked:
			var agd: Dictionary = ag2 as Dictionary
			var aid: int = int(agd.get("id", 0))
			if used_global.has(aid):
				continue
			if _rng.randf() > _npc_depart_effective_stay_gate(agd, pid):
				continue
			var dest: String = ""
			if _rng.randf() < _npc_trading_memory_pick_probability(agd):
				dest = _npc_pick_trading_dest_any_port(agd, pid)
			else:
				var opts: Array = []
				for pk in _port_names.keys():
					var ps2: String = str(pk)
					if ps2 != pid:
						opts.append(ps2)
				if opts.is_empty():
					continue
				dest = str(opts[_rng.randi_range(0, opts.size() - 1)])
			if dest.is_empty() or not _port_names.has(dest):
				continue
			dest = _npc_depart_dest_contract_bias(agd, pid, dest)
			if dest.is_empty() or not _port_names.has(dest):
				continue
			proposals.append({"ag": agd, "dest": dest})
		var by_dest: Dictionary = {}
		for pr in proposals:
			var pd: Dictionary = pr as Dictionary
			var dkey: String = str(pd.get("dest", ""))
			if not by_dest.has(dkey):
				by_dest[dkey] = []
			(by_dest[dkey] as Array).append(pd["ag"])
		for dk in by_dest.keys():
			var grp: Array = by_dest[dk] as Array
			if grp.is_empty():
				continue
			grp.sort_custom(func(a: Dictionary, b: Dictionary) -> bool: return int(a.get("id", 0)) < int(b.get("id", 0)))
			var pool: Array = []
			for g2 in grp:
				var g2d: Dictionary = g2 as Dictionary
				if not used_global.has(int(g2d.get("id", 0))):
					pool.append(g2d)
			if pool.is_empty():
				continue
			for sk2 in range(pool.size() - 1, 0, -1):
				var jk2: int = _rng.randi_range(0, sk2)
				var tx: Dictionary = pool[sk2] as Dictionary
				pool[sk2] = pool[jk2]
				pool[jk2] = tx
			_npc_convoy_process_depart_group(pid, str(dk), pool, used_global)


func _npc_active_pirate_count() -> int:
	var n: int = 0
	for item in _npc_agents:
		if typeof(item) != TYPE_DICTIONARY:
			continue
		if str((item as Dictionary).get("voyage_role", "")) == _VOYAGE_ROLE_PIRATE:
			n += 1
	return n


func _npc_boarding_marine_qty(ag: Dictionary) -> int:
	if not _goods.has("marines"):
		return 0
	var cr0: Variant = ag.get("cargo", null)
	if typeof(cr0) != TYPE_DICTIONARY:
		return 0
	return clampi(int((cr0 as Dictionary).get("marines", 0)), 0, 9999)


func _npc_cargo_estimated_sell_value_coins(ag: Dictionary) -> int:
	var cr0: Variant = ag.get("cargo", null)
	if typeof(cr0) != TYPE_DICTIONARY:
		return 0
	var cargo: Dictionary = cr0 as Dictionary
	var t: int = 0
	for gk in cargo.keys():
		var gid: String = str(gk)
		if not _goods.has(gid):
			continue
		var gd: Variant = _goods[gid]
		if typeof(gd) != TYPE_DICTIONARY:
			continue
		var up: int = maxi(0, int((gd as Dictionary).get("unit_sell_price", 0)))
		t += up * _npc_cargo_qty(cargo, gid)
	return t


func _npc_pirate_boarding_power(ag: Dictionary) -> float:
	var mar: int = _npc_boarding_marine_qty(ag)
	var row: Dictionary = _npc_ship_row(ag)
	var vm: float = clampf(float(row.get("voyage_day_mult", 1.0)), 0.55, 1.55)
	var cat: String = str(row.get("category", "merchant"))
	var hull_bonus: float = 4.0 if cat == "galley" else 0.0
	var ex: float = _npc_trait_f(ag, _NPC_TRAIT_EXTRA)
	var neu: float = _npc_trait_f(ag, _NPC_TRAIT_NEURO)
	return float(mar) * 2.35 + 8.0 + hull_bonus + (vm - 0.55) * 5.5 + ex * 2.8 + neu * 1.1


func _npc_weighted_pick_agent(rows: Array) -> Dictionary:
	if rows.is_empty():
		return {}
	var tw: float = 0.0
	for r0 in rows:
		var rd: Dictionary = r0 as Dictionary
		tw += maxf(0.0001, float(rd.get("w", 1.0)))
	var x: float = _rng.randf() * tw
	for r1 in rows:
		var d1: Dictionary = r1 as Dictionary
		var wf: float = maxf(0.0001, float(d1.get("w", 1.0)))
		x -= wf
		if x <= 0.0:
			return d1["ag"] as Dictionary
	return (rows[rows.size() - 1] as Dictionary)["ag"] as Dictionary


func _npc_pirate_convoy_leader_for(victim: Dictionary, idxm: Dictionary) -> Dictionary:
	var cl: int = int(victim.get("convoy_leader_id", 0))
	var sid: int = int(victim.get("id", 0))
	if cl > 0 and cl != sid and idxm.has(cl):
		var L: Dictionary = idxm[cl] as Dictionary
		if int(L.get("voyage_days_remaining", 0)) > 0 and str(L.get("voyage_dest_id", "")) == str(
			victim.get("voyage_dest_id", "")
		):
			return L
	return victim


func _npc_pirate_pick_contact_ship(leader: Dictionary, idxm: Dictionary) -> Dictionary:
	var rows: Array = []
	var c0: Dictionary = leader
	var mar0: int = _npc_boarding_marine_qty(c0)
	var est0: int = _npc_cargo_estimated_sell_value_coins(c0)
	var w0: float = float(est0) / (float(mar0) + 3.0) * 0.02 + 0.14 + float(c0.get("contact_candidate_bias", 0.0)) * 0.12
	rows.append({"ag": c0, "w": maxf(0.05, w0)})
	var mids: Array = leader.get("convoy_member_ids", []) as Array
	for mid in mids:
		var mid_i: int = int(mid)
		if not idxm.has(mid_i):
			continue
		var mem: Dictionary = idxm[mid_i] as Dictionary
		if not _npc_convoy_is_follower(mem):
			continue
		if str(mem.get("voyage_role", _VOYAGE_ROLE_MERCHANT)) != _VOYAGE_ROLE_MERCHANT:
			continue
		var mmar: int = _npc_boarding_marine_qty(mem)
		var mest: int = _npc_cargo_estimated_sell_value_coins(mem)
		var ww: float = float(mest) / (float(mmar) + 3.0) * 0.02 + 0.12
		rows.append({"ag": mem, "w": maxf(0.05, ww)})
	return _npc_weighted_pick_agent(rows)


func _npc_pirate_apply_marine_losses(ag: Dictionary, loss: int) -> void:
	if loss <= 0 or not _goods.has("marines"):
		return
	var cr0: Variant = ag.get("cargo", null)
	if typeof(cr0) != TYPE_DICTIONARY:
		return
	var cargo: Dictionary = cr0 as Dictionary
	var have: int = _npc_cargo_qty(cargo, "marines")
	var take: int = mini(have, loss)
	if take > 0:
		_pirate_metrics_marines_lost += take
		_npc_adjust_cargo(cargo, "marines", -take)


func _npc_escort_combat_flee(leader: Dictionary, escort: Dictionary) -> void:
	leader["convoy_escort_id"] = 0
	leader["convoy_escort_player"] = false
	var promised: int = 0
	var ct0: Variant = escort.get("escort_contract", null)
	if typeof(ct0) == TYPE_DICTIONARY:
		promised = clampi(int((ct0 as Dictionary).get("pay_coins", 0)), 0, _MAX_PURSE_COINS)
	escort["voyage_role"] = _VOYAGE_ROLE_MERCHANT
	if typeof(escort.get("escort_contract", null)) == TYPE_DICTIONARY:
		(escort["escort_contract"] as Dictionary).clear()
	else:
		escort["escort_contract"] = {}
	escort["convoy_leader_id"] = 0
	escort["convoy_member_ids"] = []
	escort["convoy_formed"] = false
	_npc_escort_reliability_apply(escort, false, promised)
	_ensure_npc_escort_reputation_fields(escort)
	var r: float = float(escort.get("escort_reliability", 0.55))
	escort["escort_reliability"] = clampf(r - 0.11, 0.0, 1.0)
	_pirate_metrics_flees += 1


func _npc_pirate_loot_contact(pirate: Dictionary, contact: Dictionary) -> void:
	var purse_v: int = clampi(int(contact.get("money", 0)), 0, _MAX_PURSE_COINS)
	var take_c: int = mini(purse_v, maxi(8, int(round(float(purse_v) * 0.21))) + _rng.randi_range(0, 36))
	take_c = mini(take_c, purse_v)
	if take_c > 0:
		contact["money"] = purse_v - take_c
		pirate["money"] = clampi(int(pirate.get("money", 0)) + take_c, 0, _MAX_PURSE_COINS)
		_pirate_metrics_loot_coins += take_c
	var crp: Variant = pirate.get("cargo", null)
	var crc: Variant = contact.get("cargo", null)
	if typeof(crp) != TYPE_DICTIONARY or typeof(crc) != TYPE_DICTIONARY:
		return
	var p_cargo: Dictionary = crp as Dictionary
	var v_cargo: Dictionary = crc as Dictionary
	var tries: int = _rng.randi_range(1, 3)
	for _t in tries:
		var candidates: Array = []
		for gk in v_cargo.keys():
			var gid: String = str(gk)
			if gid == "grain" or gid == "marines" or not _goods.has(gid):
				continue
			var q: int = _npc_cargo_qty(v_cargo, gid)
			if q <= 0:
				continue
			var up: int = maxi(1, int((_goods[gid] as Dictionary).get("unit_sell_price", 1)))
			candidates.append({"gid": gid, "w": float(q * up)})
		if candidates.is_empty():
			break
		var tw: float = 0.0
		for c in candidates:
			tw += float((c as Dictionary).get("w", 1.0))
		var x: float = _rng.randf() * tw
		var pick_gid: String = ""
		for c2 in candidates:
			var d2: Dictionary = c2 as Dictionary
			x -= float(d2.get("w", 1.0))
			if x <= 0.0:
				pick_gid = str(d2.get("gid", ""))
				break
		if pick_gid.is_empty():
			pick_gid = str((candidates[0] as Dictionary).get("gid", ""))
		var steal: int = _rng.randi_range(1, 4)
		steal = mini(steal, _npc_cargo_qty(v_cargo, pick_gid))
		if steal <= 0:
			continue
		_npc_adjust_cargo(v_cargo, pick_gid, -steal)
		_npc_adjust_cargo(p_cargo, pick_gid, steal)


func _npc_convoy_detach_follower(leader: Dictionary, member_id: int) -> void:
	var mids: Array = leader.get("convoy_member_ids", []) as Array
	var nm: Array = []
	for it in mids:
		if int(it) != member_id:
			nm.append(int(it))
	leader["convoy_member_ids"] = nm
	var scat: Array = leader.get("scattered_ids", []) as Array
	if not scat.has(member_id):
		scat.append(member_id)
	leader["scattered_ids"] = scat
	for item in _npc_agents:
		if typeof(item) != TYPE_DICTIONARY:
			continue
		var ag: Dictionary = item as Dictionary
		if int(ag.get("id", 0)) != member_id:
			continue
		ag["convoy_leader_id"] = 0
		ag["convoy_member_ids"] = []
		ag["convoy_formed"] = false
		break


func _npc_pirate_maybe_scatter_convoy(leader: Dictionary) -> void:
	if not bool(leader.get("convoy_formed", false)):
		return
	var mm: Array = leader.get("convoy_member_ids", []) as Array
	if mm.is_empty():
		return
	if _rng.randf() > 0.24:
		return
	var pick: int = int(mm[_rng.randi_range(0, mm.size() - 1)])
	_npc_convoy_detach_follower(leader, pick)


func _npc_resolve_pirate_catch(pr: Dictionary, victim: Dictionary, idxm: Dictionary) -> void:
	var leader: Dictionary = _npc_pirate_convoy_leader_for(victim, idxm)
	var esc_pl: bool = bool(leader.get("convoy_escort_player", false))
	var esid: int = int(leader.get("convoy_escort_id", 0))
	var escort_fled: bool = false
	if esc_pl:
		var lidp: int = int(leader.get("id", 0))
		if (
			str(player_voyage_role) == _VOYAGE_ROLE_ESCORT
			and int(player_escort_contract.get("employer_id", -9)) == lidp
			and voyage_days_remaining > 0
			and str(voyage_dest_id) == str(leader.get("voyage_dest_id", ""))
		):
			var pp2: float = _npc_pirate_boarding_power(pr)
			var ep2: float = _player_boarding_power()
			if pp2 > ep2 * _PIRATE_FLEE_POWER_RATIO:
				_player_escort_combat_flee(leader)
				escort_fled = true
			else:
				var ratio2: float = pp2 / maxf(1.0, ep2)
				var lose_e2: int = _rng.randi_range(0, 2) + int(ratio2 * 2.1)
				var lose_p2: int = _rng.randi_range(0, 2) + int((1.0 / maxf(0.35, ratio2)) * 1.4)
				_player_apply_boarding_marine_loss(lose_e2)
				_npc_pirate_apply_marine_losses(pr, lose_p2)
				if _npc_boarding_marine_qty(pr) <= 0:
					return
	elif esid > 0 and idxm.has(esid):
		var esc: Dictionary = idxm[esid] as Dictionary
		if (
			str(esc.get("voyage_role", "")) == _VOYAGE_ROLE_ESCORT
			and int(esc.get("convoy_leader_id", 0)) == int(leader.get("id", 0))
		):
			var pp: float = _npc_pirate_boarding_power(pr)
			var ep: float = _npc_pirate_boarding_power(esc)
			if pp > ep * _PIRATE_FLEE_POWER_RATIO:
				_npc_escort_combat_flee(leader, esc)
				escort_fled = true
			else:
				var ratio: float = pp / maxf(1.0, ep)
				var lose_e: int = _rng.randi_range(0, 2) + int(ratio * 2.1)
				var lose_p: int = _rng.randi_range(0, 2) + int((1.0 / maxf(0.35, ratio)) * 1.4)
				_npc_pirate_apply_marine_losses(esc, lose_e)
				_npc_pirate_apply_marine_losses(pr, lose_p)
				if _npc_boarding_marine_qty(pr) <= 0:
					return
	var contact: Dictionary = _npc_pirate_pick_contact_ship(leader, idxm)
	if contact.is_empty():
		return
	var vic_power: float = _npc_pirate_boarding_power(contact)
	if bool(leader.get("convoy_formed", false)) and int(contact.get("convoy_leader_id", 0)) == int(leader.get("id", 0)):
		vic_power += 3.5
	var atk: float = _npc_pirate_boarding_power(pr) + _rng.randf() * 9.0
	if atk < vic_power * 0.9:
		_npc_pirate_apply_marine_losses(pr, _rng.randi_range(1, 5))
		return
	_npc_pirate_loot_contact(pr, contact)
	var pn0: float = float(pr.get("pirate_notoriety", 0.0))
	pr["pirate_notoriety"] = clampf(pn0 + 3.5 + (5.0 if escort_fled else 0.0), 0.0, _PIRATE_NOTORIETY_CAP)
	_npc_pirate_maybe_scatter_convoy(leader)
	_npc_trim_cargo_to_capacity(pr)
	_pirate_metrics_raids += 1


func _npc_pirate_encounters_tick() -> void:
	if not _goods.has("marines"):
		return
	var idxm: Dictionary = _npc_index_agents_by_id()
	for item in _npc_agents:
		if typeof(item) != TYPE_DICTIONARY:
			continue
		var pr: Dictionary = item as Dictionary
		if str(pr.get("voyage_role", "")) != _VOYAGE_ROLE_PIRATE:
			continue
		if int(pr.get("voyage_days_remaining", 0)) <= 0:
			continue
		var rows: Array = []
		for item2 in _npc_agents:
			if typeof(item2) != TYPE_DICTIONARY:
				continue
			var v: Dictionary = item2 as Dictionary
			if int(v.get("id", 0)) == int(pr.get("id", 0)):
				continue
			if int(v.get("voyage_days_remaining", 0)) <= 0:
				continue
			if str(v.get("voyage_role", _VOYAGE_ROLE_MERCHANT)) != _VOYAGE_ROLE_MERCHANT:
				continue
			var w: float = 0.62
			if str(v.get("voyage_dest_id", "")) == str(pr.get("voyage_dest_id", "")):
				w += 2.0
			var srow: Dictionary = _npc_ship_row(v)
			var vm: float = clampf(float(srow.get("voyage_day_mult", 1.0)), 0.55, 1.55)
			w += (vm - 0.55) * 1.75
			var op: float = clampf(
				0.5 * (float(pr.get("voyage_open_sea_01", 0.0)) + float(v.get("voyage_open_sea_01", 0.0))),
				0.0,
				1.0
			)
			w *= 0.72 + op * 0.52
			rows.append({"ag": v, "w": maxf(0.07, w)})
		if rows.is_empty():
			continue
		var victim: Dictionary = _npc_weighted_pick_agent(rows)
		if victim.is_empty():
			continue
		var vmin: float = clampf(float(_npc_ship_row(victim).get("voyage_day_mult", 1.0)), 0.55, 1.55)
		var pm: float = clampf(float(_npc_ship_row(pr).get("voyage_day_mult", 1.0)), 0.55, 1.55)
		var op2: float = clampf(
			0.5 * (float(pr.get("voyage_open_sea_01", 0.0)) + float(victim.get("voyage_open_sea_01", 0.0))),
			0.0,
			1.0
		)
		var p_catch: float = clampf(
			_ENCOUNTER_BASE_P * (0.88 + (vmin - pm) * 0.48) * (0.64 + op2 * 0.48),
			0.011,
			0.42
		)
		_pirate_metrics_attempts += 1
		if _rng.randf() > p_catch:
			continue
		_npc_resolve_pirate_catch(pr, victim, idxm)


func _npc_try_convert_merchant_to_pirate(ag: Dictionary) -> void:
	if _npc_active_pirate_count() >= _PIRATE_MAX_ACTIVE:
		return
	if str(ag.get("voyage_role", "")) != _VOYAGE_ROLE_MERCHANT:
		return
	if _npc_convoy_is_follower(ag):
		return
	if int(ag.get("voyage_days_remaining", 0)) != 0:
		return
	if clampi(int(ag.get("money", 0)), 0, _MAX_PURSE_COINS) > _PIRATE_SPAWN_PURSE_MAX:
		return
	var open: float = _npc_trait_f(ag, _NPC_TRAIT_OPEN)
	var neu: float = _npc_trait_f(ag, _NPC_TRAIT_NEURO)
	var p_spawn: float = clampf(_PIRATE_SPAWN_ROLL_BASE + (1.0 - open) * 0.04 + neu * 0.03, 0.02, 0.14)
	if _rng.randf() > p_spawn:
		return
	ag["voyage_role"] = _VOYAGE_ROLE_PIRATE
	if _ship_classes.has(_PIRATE_RAIDER_HULL_ID):
		ag["ship_class_id"] = _PIRATE_RAIDER_HULL_ID
	_npc_convoy_reset_docked(ag)
	if typeof(ag.get("escort_contract", null)) == TYPE_DICTIONARY:
		(ag["escort_contract"] as Dictionary).clear()
	else:
		ag["escort_contract"] = {}
	var cr0: Variant = ag.get("cargo", null)
	if typeof(cr0) != TYPE_DICTIONARY:
		ag["cargo"] = {}
		cr0 = ag["cargo"]
	var cargo: Dictionary = cr0 as Dictionary
	if _goods.has("marines"):
		var add_m: int = _rng.randi_range(6, 16)
		_npc_adjust_cargo(cargo, "marines", add_m)
	ag["pirate_notoriety"] = 0.0
	_npc_trim_cargo_to_capacity(ag)


func _npc_pirate_spawn_docked_tick() -> void:
	if not _goods.has("marines"):
		return
	for item in _npc_agents:
		if typeof(item) != TYPE_DICTIONARY:
			continue
		if _npc_active_pirate_count() >= _PIRATE_MAX_ACTIVE:
			return
		_npc_try_convert_merchant_to_pirate(item as Dictionary)


func _npc_pirate_dock_depart_tick() -> void:
	if _port_names.size() < 2:
		return
	for item in _npc_agents:
		if typeof(item) != TYPE_DICTIONARY:
			continue
		var ag: Dictionary = item as Dictionary
		if str(ag.get("voyage_role", "")) != _VOYAGE_ROLE_PIRATE:
			continue
		if int(ag.get("voyage_days_remaining", 0)) != 0:
			continue
		var here: String = str(ag.get("docked_port", ""))
		if here.is_empty() or not _port_names.has(here):
			continue
		if _rng.randf() > _PIRATE_DEPART_STAY_GATE:
			continue
		var opts: Array = []
		for pk in _port_names.keys():
			var ps2: String = str(pk)
			if ps2 != here:
				opts.append(ps2)
		if opts.is_empty():
			continue
		var dest: String = str(opts[_rng.randi_range(0, opts.size() - 1)])
		_npc_depart_solo_merchant(ag, here, dest)


func get_player_voyage_role() -> String:
	return str(player_voyage_role)


func get_player_escort_contract() -> Dictionary:
	return player_escort_contract.duplicate(true)


func get_player_offers_convoy_escort() -> bool:
	return player_offers_convoy_escort


func set_player_offers_convoy_escort(v: bool) -> void:
	player_offers_convoy_escort = v


func _finalize_port_stocks() -> void:
	_port_stocks.clear()
	for pid in _port_names.keys():
		var row: Dictionary = {}
		var init_raw: Variant = _port_initial_stock.get(pid, null)
		var init_d: Dictionary = {}
		if typeof(init_raw) == TYPE_DICTIONARY:
			init_d = init_raw as Dictionary
		for good_id in _goods.keys():
			var gid := str(good_id)
			if init_d.has(gid):
				row[gid] = maxi(0, int(init_d[gid]))
			elif gid == "gold" or gid == "silver":
				row[gid] = 0
			else:
				row[gid] = _DEFAULT_STOCK_SLAVES if gid == "slaves" else _DEFAULT_STOCK_PER_GOOD
		_port_stocks[pid] = row


func _ensure_all_ports_have_all_goods() -> void:
	for pid in _port_names.keys():
		if not _port_stocks.has(pid):
			_port_stocks[pid] = {}
		var row: Dictionary = _port_stocks[pid]
		for good_id in _goods.keys():
			var gid := str(good_id)
			if not row.has(gid):
				if gid == "gold" or gid == "silver":
					row[gid] = 0
				else:
					row[gid] = _DEFAULT_STOCK_SLAVES if gid == "slaves" else _DEFAULT_STOCK_PER_GOOD


func _stock_target_for_good(good_id: String) -> int:
	var meta: Variant = _goods.get(good_id, null)
	if typeof(meta) != TYPE_DICTIONARY:
		return 80
	var gd: Dictionary = meta as Dictionary
	return maxi(1, int(gd.get("stock_target", 80)))


func _port_stock_qty(port_id: String, good_id: String) -> int:
	var p: Variant = _port_stocks.get(port_id, null)
	if typeof(p) != TYPE_DICTIONARY:
		return 0
	return maxi(0, int((p as Dictionary).get(good_id, 0)))


func _adjust_port_stock(port_id: String, good_id: String, delta: int) -> void:
	var q: int = _port_stock_qty(port_id, good_id) + delta
	if not _port_stocks.has(port_id):
		_port_stocks[port_id] = {}
	var d: Dictionary = _port_stocks[port_id]
	d[good_id] = maxi(0, q)


func _need_tier_for_good(good_id: String) -> String:
	var meta: Variant = _goods.get(good_id, null)
	if typeof(meta) != TYPE_DICTIONARY:
		return ""
	return str((meta as Dictionary).get("need_tier", ""))


## Population wine demand / day (matches daily bite logic).
func _port_wine_want_per_day(port_id: String) -> int:
	var ps := str(port_id)
	if not _port_names.has(ps):
		return 0
	var w_base: int = int(_port_population_wine_base.get(ps, 1))
	var wealth: int = int(_port_wealth.get(ps, 100))
	var w_extra: int = clampi(int(float(wealth) / 95.0), 0, 14)
	return clampi(w_base + w_extra, 0, 50)


func _wine_cover_days_for_port(port_id: String) -> float:
	if not _goods.has("wine"):
		return 9999.0
	var want: int = _port_wine_want_per_day(port_id)
	if want <= 0:
		return 9999.0
	return float(_port_stock_qty(str(port_id), "wine")) / float(want)


func _grain_shortfall_span(port_id: String) -> float:
	var days: float = get_grain_food_days_for_port(port_id)
	if days >= 9000.0:
		return 0.0
	return maxf(0.0, _RESERVE_REF_GRAIN_DAYS - minf(days, _RESERVE_REF_GRAIN_DAYS * 2.2))


func _grain_reservation_pressure(port_id: String) -> float:
	var span: float = _grain_shortfall_span(port_id)
	return clampf(span / maxf(0.001, _RESERVE_REF_GRAIN_DAYS), 0.0, 1.0)


func _wine_reservation_pressure(port_id: String) -> float:
	if not _goods.has("wine"):
		return 0.0
	var wdays: float = _wine_cover_days_for_port(port_id)
	if wdays >= 9000.0:
		return 0.0
	var span: float = maxf(0.0, _RESERVE_REF_WINE_DAYS - minf(wdays, _RESERVE_REF_WINE_DAYS * 2.2))
	return clampf(span / maxf(0.001, _RESERVE_REF_WINE_DAYS), 0.0, 1.0)


func _smooth_reservation_addon(pressure_01: float, cap: float, k: float) -> float:
	if pressure_01 <= 0.0 or cap <= 0.0:
		return 0.0
	return cap * (1.0 - exp(-k * pressure_01))


func _grain_food_unrest_addon(port_id: String, unrest_scale: float) -> float:
	var u: float = float(get_port_food_unrest(port_id))
	return minf(_RESERVE_STRESS_CAP * 0.5, u * _RESERVE_UNREST_PER_POINT * unrest_scale)


func _grain_buy_reservation_total(port_id: String, player_counterparty: bool) -> float:
	var p: float = _grain_reservation_pressure(port_id)
	var cap: float = (
		_RESERVE_CURVE_CAP_GRAIN_BUY_PLAYER
		if player_counterparty
		else _RESERVE_CURVE_CAP_GRAIN_BUY_NPC
	)
	var k: float = _RESERVE_CURVE_K_PLAYER if player_counterparty else _RESERVE_CURVE_K_NPC
	var curved: float = _smooth_reservation_addon(p, cap, k)
	var uadd: float = _grain_food_unrest_addon(port_id, 1.0)
	return minf(_RESERVE_STRESS_CAP, curved + uadd)


func _grain_sell_reservation_total(port_id: String, player_counterparty: bool) -> float:
	var p: float = _grain_reservation_pressure(port_id)
	var cap: float = (
		_RESERVE_CURVE_CAP_GRAIN_SELL_PLAYER
		if player_counterparty
		else _RESERVE_CURVE_CAP_GRAIN_SELL_NPC
	)
	var k: float = _RESERVE_CURVE_K_PLAYER if player_counterparty else _RESERVE_CURVE_K_NPC
	var curved: float = _smooth_reservation_addon(p, cap, k)
	var uadd: float = _grain_food_unrest_addon(port_id, 1.05)
	return minf(_RESERVE_STRESS_CAP, curved + uadd)


func _wine_buy_reservation_total(port_id: String, player_counterparty: bool) -> float:
	var p: float = _wine_reservation_pressure(port_id)
	var cap: float = _RESERVE_CURVE_CAP_WINE_PLAYER if player_counterparty else _RESERVE_CURVE_CAP_WINE_NPC
	var k: float = _RESERVE_CURVE_K_PLAYER if player_counterparty else _RESERVE_CURVE_K_NPC
	return minf(_RESERVE_STRESS_CAP * 0.88, _smooth_reservation_addon(p, cap, k))


func _port_avg_outbound_lane_days(port_id: String) -> float:
	var neigh_raw: Variant = _port_neighbors.get(port_id, null)
	if neigh_raw == null or typeof(neigh_raw) != TYPE_ARRAY:
		return 0.0
	var neigh: Array = neigh_raw as Array
	if neigh.is_empty():
		return 0.0
	var sumd: float = 0.0
	var n: int = 0
	for nb in neigh:
		var d: int = int(_lane_days.get(_lane_key(port_id, str(nb)), -1))
		if d > 0:
			sumd += float(d)
			n += 1
	if n <= 0:
		return 0.0
	return sumd / float(n)


## Luxury + far-trade markup for `need_tier == "luxury"` (same shelf quote for player and NPC).
func _layer_luxury_far_mult_for_port(port_id: String) -> float:
	if not _port_names.has(str(port_id)):
		return 1.0
	var ps := str(port_id)
	var attract: int = maxi(1, _wealth_stock_target_for_port(ps))
	var wealth: int = maxi(1, int(_port_wealth.get(ps, attract)))
	var w_ex: float = clampf(float(wealth) / float(attract) - 1.0, 0.0, 2.5)
	var from_wealth: float = minf(_LUXURY_SPREAD_MAX, w_ex * _LUXURY_WEALTH_EXCESS_COEF)
	var lanes: float = _port_avg_outbound_lane_days(ps)
	var lane_u: float = clampf(lanes / maxf(0.5, _FAR_TRADE_LANE_REF_DAYS), 0.0, 2.0)
	var from_lanes: float = minf(_FAR_TRADE_SPREAD_MAX, lane_u * _FAR_TRADE_LANE_COEF)
	return 1.0 + minf(_LUXURY_FAR_COMBINED_MAX, from_wealth + from_lanes)


func _food_tier_stress_from_grain(port_id: String) -> float:
	if not _goods.has("grain"):
		return 0.0
	return _grain_buy_reservation_total(port_id, true)


func _comfort_tier_stress_from_wine(port_id: String) -> float:
	if not _goods.has("wine"):
		return 0.0
	return _wine_buy_reservation_total(port_id, true)


func _farm_wine_help_extra(port_id: String, already_helped: int) -> int:
	if not _goods.has("wine"):
		return 0
	var room: int = maxi(0, _WINE_FARM_HELP_PORT_DAILY_CAP - already_helped)
	if room <= 0:
		return 0
	var have: int = _port_stock_qty(port_id, "wine")
	var want: int = _port_wine_want_per_day(port_id)
	if want <= 0:
		return mini(room, _WINE_FARM_HELP_EMPTY) if have <= 0 else 0
	if have <= 0:
		var need_empty: int = maxi(_WINE_FARM_HELP_EMPTY, mini(9, want / 2 + 2))
		return mini(room, need_empty)
	var low_line: int = clampi(want * 2, 8, 48)
	if have < low_line:
		return mini(room, maxi(_WINE_FARM_HELP_LOW, want / 6 + 1))
	return 0


## After population drinks: if a port still has no wine but has vineyards, add a conservative same-day top-up.
func _replenish_wine_vineyards_after_bites() -> void:
	if not _goods.has("wine"):
		return
	if not _is_harvest_doy(_calendar_doy_1based(current_day)):
		return
	var vine_yield: Dictionary = {}  # port_id -> sum wine_per_day from farms at that port
	for f in _farms:
		if typeof(f) != TYPE_DICTIONARY:
			continue
		var fd: Dictionary = f as Dictionary
		var pid := str(fd.get("port_id", ""))
		if pid.is_empty() or not _port_names.has(pid):
			continue
		var wv: int = maxi(0, int(fd.get("wine_per_day", 0)))
		if wv <= 0:
			continue
		vine_yield[pid] = int(vine_yield.get(pid, 0)) + wv
	for pid in vine_yield.keys():
		if _port_stock_qty(str(pid), "wine") > 0:
			continue
		var sumw: int = int(vine_yield[pid])
		var want: int = _port_wine_want_per_day(str(pid))
		var bump: int = clampi(sumw + want / 4, 5, 18)
		_adjust_port_stock(str(pid), "wine", bump)


func _war_metal_reservation_addon(port_id: String) -> float:
	if not is_port_at_war(port_id):
		return 0.0
	return _WAR_METAL_DEMAND_STRESS


func _war_metal_loss_qty(port_id: String) -> int:
	if not is_port_at_war(port_id) or not _goods.has("metal"):
		return 0
	var ps := str(port_id)
	var eat: int = int(_port_population_grain.get(ps, 0))
	var stock: int = _port_stock_qty(ps, "metal")
	var line: int = clampi(
		_WAR_MATERIEL_METAL_BASE + (eat * _WAR_MATERIEL_METAL_LINEAR) / 5,
		_WAR_MATERIEL_METAL_BASE,
		_WAR_MATERIEL_METAL_MAX
	)
	var skim: int = mini(
		_WAR_MATERIEL_METAL_STOCK_SKIM_MAX,
		stock / maxi(1, _WAR_MATERIEL_METAL_STOCK_SKIM_DIV)
	)
	return mini(_WAR_MATERIEL_DAILY_HARD_CAP, line + skim)


func _war_wire_loss_qty(port_id: String) -> int:
	if not is_port_at_war(port_id) or not _goods.has("wire"):
		return 0
	var ps := str(port_id)
	var eat: int = int(_port_population_grain.get(ps, 0))
	var stock: int = _port_stock_qty(ps, "wire")
	var line: int = clampi(
		_WAR_MATERIEL_WIRE_BASE + eat / maxi(1, _WAR_MATERIEL_WIRE_LINEAR_DIV),
		_WAR_MATERIEL_WIRE_BASE,
		_WAR_MATERIEL_WIRE_MAX
	)
	var skim: int = mini(
		_WAR_MATERIEL_WIRE_STOCK_SKIM_MAX,
		stock / maxi(1, _WAR_MATERIEL_WIRE_STOCK_SKIM_DIV)
	)
	return mini(_WAR_MATERIEL_DAILY_HARD_CAP, line + skim)


## Daily draw on port ingots + wire while `at_war` (after population wine bite, before vineyard top-up).
func _apply_war_materiel_consumption() -> void:
	for pid in _port_names.keys():
		var ps := str(pid)
		if not is_port_at_war(ps):
			continue
		var want_m: int = _war_metal_loss_qty(ps)
		var want_w: int = _war_wire_loss_qty(ps)
		var take_m: int = mini(want_m, _port_stock_qty(ps, "metal")) if want_m > 0 else 0
		var take_w: int = mini(want_w, _port_stock_qty(ps, "wire")) if want_w > 0 else 0
		if take_m > 0:
			_adjust_port_stock(ps, "metal", -take_m)
		if take_w > 0:
			_adjust_port_stock(ps, "wire", -take_w)
		if take_m > 0 or take_w > 0:
			_last_war_industry_digest[ps] = {"metal": take_m, "wire": take_w}


## Daily peace-time draw: metal, wire, timber, textiles (world.json industrial_*_per_day).
func _apply_industrial_metal_sinks() -> void:
	for pid in _port_names.keys():
		var ps := str(pid)
		var want_m: int = int(_port_industrial_metal_per_day.get(ps, 0))
		var want_w: int = int(_port_industrial_wire_per_day.get(ps, 0))
		var want_t: int = int(_port_industrial_timber_per_day.get(ps, 0))
		var want_x: int = int(_port_industrial_textiles_per_day.get(ps, 0))
		var take_m: int = 0
		var take_w: int = 0
		var take_t: int = 0
		var take_x: int = 0
		if want_m > 0 and _goods.has("metal"):
			take_m = mini(want_m, _port_stock_qty(ps, "metal"))
			if take_m > 0:
				_adjust_port_stock(ps, "metal", -take_m)
		if want_w > 0 and _goods.has("wire"):
			take_w = mini(want_w, _port_stock_qty(ps, "wire"))
			if take_w > 0:
				_adjust_port_stock(ps, "wire", -take_w)
		if want_t > 0 and _goods.has("timber"):
			take_t = mini(want_t, _port_stock_qty(ps, "timber"))
			if take_t > 0:
				_adjust_port_stock(ps, "timber", -take_t)
		if want_x > 0 and _goods.has("textiles"):
			take_x = mini(want_x, _port_stock_qty(ps, "textiles"))
			if take_x > 0:
				_adjust_port_stock(ps, "textiles", -take_x)
		if take_m > 0 or take_w > 0 or take_t > 0 or take_x > 0:
			_last_industrial_sink_digest[ps] = {
				"metal": take_m,
				"wire": take_w,
				"timber": take_t,
				"textiles": take_x,
			}


func _metal_tier_stress_from_food(port_id: String) -> float:
	if not _goods.has("grain"):
		return 0.0
	var fg: float = _food_tier_stress_from_grain(port_id)
	return minf(_RESERVE_STRESS_CAP * 0.92, fg * _RESERVE_METAL_FROM_FOOD_STRESS)


## Port ask when this counterparty buys from the port (player vs NPC wholesale curves differ on grain/wine).
func _need_mult_player_buys_from_port(port_id: String, good_id: String, player_counterparty: bool = true) -> float:
	var tier: String = _need_tier_for_good(good_id)
	if tier == "food" and good_id == "grain":
		return 1.0 + _grain_buy_reservation_total(port_id, player_counterparty)
	if tier == "comfort" and good_id == "wine":
		return 1.0 + _wine_buy_reservation_total(port_id, player_counterparty)
	if tier == "metal" and (good_id == "metal" or good_id == "wire"):
		var food_m: float = _metal_tier_stress_from_food(port_id)
		var war_m: float = _war_metal_reservation_addon(port_id)
		return 1.0 + minf(_WAR_METAL_RESERVE_CAP, food_m + war_m)
	return 1.0


## Port bid when this counterparty sells to the port.
func _need_mult_player_sells_to_port(port_id: String, good_id: String, player_counterparty: bool = true) -> float:
	var tier: String = _need_tier_for_good(good_id)
	if tier == "food" and good_id == "grain":
		return 1.0 + _grain_sell_reservation_total(port_id, player_counterparty)
	if tier == "comfort" and good_id == "wine":
		var mult: float = 1.0 + _wine_buy_reservation_total(port_id, player_counterparty)
		var gfd: float = get_grain_food_days_for_port(port_id)
		if gfd < 9000.0 and gfd < 1.05:
			var trim: float = clampf((1.05 - gfd) / 1.05, 0.0, 1.0) * _RESERVE_COMFORT_GRAIN_TIGHT
			mult *= maxf(0.72, 1.0 - trim)
		return mult
	if tier == "metal" and (good_id == "metal" or good_id == "wire"):
		var food_m2: float = _metal_tier_stress_from_food(port_id)
		var war_m2: float = _war_metal_reservation_addon(port_id)
		return 1.0 + minf(_RESERVE_STRESS_CAP * 0.88 + 0.1, food_m2 * 1.02 + war_m2 * 0.92)
	return 1.0


func _goods_default_market_velocity_demand(good_id: String) -> float:
	var meta: Variant = _goods.get(good_id, null)
	if typeof(meta) != TYPE_DICTIONARY:
		return 0.22
	var gd: Dictionary = meta as Dictionary
	if gd.has("market_demand_per_day"):
		return maxf(0.0, float(gd.get("market_demand_per_day", 0.0)))
	var tgt: float = float(_stock_target_for_good(good_id))
	return maxf(0.1, tgt * 0.034)


func _estimated_farm_supply_per_day(port_id: String, good_id: String) -> float:
	var ps := str(port_id)
	var farm_mult: float = _WAR_FARM_OUTPUT_MULT if is_port_at_war(ps) else 1.0
	var pop_sc: float = _population_output_scale_for_port(ps)
	var slave_sc: float = _port_slave_output_mult(ps)
	var raw: float = 0.0
	for f in _farms:
		if typeof(f) != TYPE_DICTIONARY:
			continue
		var fd: Dictionary = f as Dictionary
		if str(fd.get("port_id", "")) != ps:
			continue
		match good_id:
			"grain":
				raw += float(fd.get("grain_per_day", 0))
			"wine":
				raw += float(fd.get("wine_per_day", 0))
			"fish":
				raw += float(fd.get("fish_per_day", 0))
			_:
				pass
	return raw * farm_mult * pop_sc * slave_sc


func _estimated_mine_supply_per_day(port_id: String, good_id: String) -> float:
	var ps := str(port_id)
	var pop_sc: float = _population_output_scale_for_port(ps)
	var slave_sc: float = _port_slave_output_mult(ps)
	var raw: float = 0.0
	for m in _mines:
		if typeof(m) != TYPE_DICTIONARY:
			continue
		var md: Dictionary = m as Dictionary
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


func _port_structural_demand_per_day(port_id: String, good_id: String) -> float:
	var ps := str(port_id)
	match good_id:
		"grain":
			var eat: float = float(get_population_grain_eat_effective(ps))
			var ghave: int = _port_stock_qty(ps, "grain")
			var spoil: float = 0.0
			if ghave > _GRAIN_SPOIL_MIN_STOCK:
				spoil = minf(float(_GRAIN_SPOIL_CAP), float(ghave) * _GRAIN_SPOIL_FRACTION)
			return eat + spoil
		"wine":
			return float(_port_wine_want_per_day(ps))
		"fish":
			return float(clampi(int(_port_population_fish_per_day.get(ps, 0)), 0, 40))
		"metal":
			var dm: float = float(int(_port_industrial_metal_per_day.get(ps, 0)))
			if is_port_at_war(ps) and _goods.has("metal"):
				dm += float(_war_metal_loss_qty(ps))
			return maxf(dm, _goods_default_market_velocity_demand("metal"))
		"wire":
			var dw: float = float(int(_port_industrial_wire_per_day.get(ps, 0)))
			if is_port_at_war(ps) and _goods.has("wire"):
				dw += float(_war_wire_loss_qty(ps))
			return maxf(dw, _goods_default_market_velocity_demand("wire"))
		"timber":
			var ind_t: float = float(int(_port_industrial_timber_per_day.get(ps, 0)))
			return maxf(ind_t, _goods_default_market_velocity_demand("timber"))
		"textiles":
			var ind_x: float = float(int(_port_industrial_textiles_per_day.get(ps, 0)))
			return maxf(ind_x, _goods_default_market_velocity_demand("textiles"))
		"gold":
			var gdm: float = 0.0
			if _port_mint_cfg.has(ps):
				var cg: Dictionary = _port_mint_cfg[ps] as Dictionary
				var gpb: int = clampi(int(cg.get("gold_per_batch", 0)), 0, 24)
				var mxb: int = clampi(int(cg.get("max_batches_per_day", 0)), 0, 40)
				if gpb > 0 and mxb > 0:
					gdm = float(gpb * mxb) * 0.32
			return maxf(gdm, _goods_default_market_velocity_demand("gold"))
		"silver":
			var sdm: float = 0.0
			if _port_mint_cfg.has(ps):
				var cg2: Dictionary = _port_mint_cfg[ps] as Dictionary
				var spb: int = clampi(int(cg2.get("silver_per_batch", 0)), 0, 36)
				var mxb2: int = clampi(int(cg2.get("max_batches_per_day", 0)), 0, 40)
				if spb > 0 and mxb2 > 0:
					sdm = float(spb * mxb2) * 0.32
			return maxf(sdm, _goods_default_market_velocity_demand("silver"))
		_:
			return _goods_default_market_velocity_demand(good_id)


func _port_resolved_market_demand_per_day(port_id: String, good_id: String) -> float:
	var ps := str(port_id)
	var row0: Variant = _port_market_demand_override.get(ps, null)
	if typeof(row0) == TYPE_DICTIONARY:
		var od: Dictionary = row0 as Dictionary
		if od.has(good_id):
			return maxf(0.0, float(od[good_id]))
	return _port_structural_demand_per_day(ps, good_id)


func _port_structural_supply_per_day(port_id: String, good_id: String) -> float:
	match good_id:
		"grain", "wine", "fish":
			return _estimated_farm_supply_per_day(port_id, good_id)
		"metal", "wire", "gold", "silver":
			return _estimated_mine_supply_per_day(port_id, good_id)
		_:
			return 0.0


func _market_demand_supply_mult_for_port_good(port_id: String, good_id: String) -> float:
	var ps := str(port_id)
	if not _port_names.has(ps) or not _goods.has(good_id):
		return 1.0
	var d_day: float = _port_resolved_market_demand_per_day(ps, good_id)
	var s_day: float = _port_structural_supply_per_day(ps, good_id)
	var stock: float = float(_port_stock_qty(ps, good_id))
	var need: float = maxf(1.0, d_day * _MARKET_HORIZON_DAYS)
	var stock_pressure: float = clampf((need - stock) / need, -1.35, 1.35)
	var flow_pressure: float = 0.0
	if d_day >= 0.35:
		flow_pressure = clampf((d_day - s_day) / d_day, -1.2, 1.2)
	elif s_day >= 0.5:
		flow_pressure = clampf(-s_day / maxf(1.0, s_day), -1.0, 0.0)
	var adj: float = clampf(
		_MARKET_STOCK_PRESSURE_WEIGHT * stock_pressure + _MARKET_FLOW_PRESSURE_WEIGHT * flow_pressure,
		-_MARKET_PRESSURE_ABS_MAX,
		_MARKET_PRESSURE_ABS_MAX
	)
	return clampf(1.0 + adj, _MARKET_PRICE_MULT_MIN, _MARKET_PRICE_MULT_MAX)


func _port_trade_price_bias_mult(port_id: String, good_id: String) -> float:
	var ps := str(port_id)
	var gid := str(good_id)
	var row0: Variant = _port_trade_price_bias.get(ps, null)
	if typeof(row0) != TYPE_DICTIONARY:
		if gid == "grain" and _world_crop_agro_model and _goods.has("grain"):
			return clampf(1.0 + _crop_phase2_grain_trade_bias_add(ps), 0.62, 1.55)
		return 1.0
	var row: Dictionary = row0 as Dictionary
	if not row.has(gid):
		if gid == "grain" and _world_crop_agro_model and _goods.has("grain"):
			return clampf(1.0 + _crop_phase2_grain_trade_bias_add(ps), 0.62, 1.55)
		return 1.0
	var b: float = float(row[gid])
	if gid == "grain" and _world_crop_agro_model and _goods.has("grain"):
		b += _crop_phase2_grain_trade_bias_add(ps)
	return clampf(1.0 + b, 0.62, 1.55)


func _rumor_extra_delta_for_port_good(port_id: String, good_id: String) -> float:
	var ps := str(port_id)
	var gid := str(good_id)
	var row0: Variant = _port_rumor_good_delta.get(ps, null)
	if typeof(row0) != TYPE_DICTIONARY:
		return 0.0
	var row: Dictionary = row0 as Dictionary
	if not row.has(gid):
		return 0.0
	return float(row[gid])


func _rumor_price_mult_for_port_good(port_id: String, good_id: String) -> float:
	var ps := str(port_id)
	var wr: float = clampf(float(_port_war_rumor.get(ps, 0.0)), 0.0, 1.0)
	var ex: float = _rumor_extra_delta_for_port_good(ps, good_id)
	return _SimAgents.rumor_price_mult(wr, str(good_id), ex)


func _port_cartel_strength_clamped(port_id: String) -> float:
	return clampf(float(_port_cartel_strength.get(str(port_id), 0.0)), 0.0, 1.0)


func _reset_port_commerce_tick() -> void:
	var z: Dictionary = {"npc_buy_units": 0, "npc_sell_units": 0, "npc_buy_coins": 0, "npc_sell_coins": 0}
	_port_commerce_tick.clear()
	for pid in _port_names.keys():
		_port_commerce_tick[str(pid)] = z.duplicate()


func _bump_npc_commerce_buy(port_id: String, qty: int, cost: int) -> void:
	var ps := str(port_id)
	if not _port_names.has(ps):
		return
	var row: Dictionary = _port_commerce_tick.get(ps, {}) as Dictionary
	if row.is_empty():
		row = {"npc_buy_units": 0, "npc_sell_units": 0, "npc_buy_coins": 0, "npc_sell_coins": 0}
		_port_commerce_tick[ps] = row
	row["npc_buy_units"] = int(row.get("npc_buy_units", 0)) + maxi(0, qty)
	row["npc_buy_coins"] = int(row.get("npc_buy_coins", 0)) + maxi(0, cost)


func _bump_npc_commerce_sell(port_id: String, qty: int, revenue: int) -> void:
	var ps := str(port_id)
	if not _port_names.has(ps):
		return
	var row: Dictionary = _port_commerce_tick.get(ps, {}) as Dictionary
	if row.is_empty():
		row = {"npc_buy_units": 0, "npc_sell_units": 0, "npc_buy_coins": 0, "npc_sell_coins": 0}
		_port_commerce_tick[ps] = row
	row["npc_sell_units"] = int(row.get("npc_sell_units", 0)) + maxi(0, qty)
	row["npc_sell_coins"] = int(row.get("npc_sell_coins", 0)) + maxi(0, revenue)


func _ensure_sim_agent_port_defaults() -> void:
	for pid in _port_names.keys():
		var ps := str(pid)
		if not _port_commerce_pulse.has(ps):
			_port_commerce_pulse[ps] = 0.38
		if not _port_cartel_strength.has(ps):
			_port_cartel_strength[ps] = 0.0
		if not _port_war_rumor.has(ps):
			_port_war_rumor[ps] = 0.0
		if not _port_plague_days.has(ps):
			_port_plague_days[ps] = 0
		if not _port_rumor_good_delta.has(ps):
			_port_rumor_good_delta[ps] = {}


func _agent_information_decay_tick() -> void:
	for pid in _port_names.keys():
		var ps := str(pid)
		var wr: float = clampf(float(_port_war_rumor.get(ps, 0.0)), 0.0, 1.0)
		_port_war_rumor[ps] = clampf(wr * 0.965, 0.0, 1.0)
		var row0: Variant = _port_rumor_good_delta.get(ps, null)
		if typeof(row0) != TYPE_DICTIONARY:
			continue
		var row: Dictionary = row0 as Dictionary
		var rm: Array[String] = []
		for gk in row.keys():
			var gid := str(gk)
			var v: float = float(row[gk]) * 0.86
			if absf(v) < 0.002:
				rm.append(gid)
			else:
				row[gk] = v
		for rk in rm:
			row.erase(rk)
	for pid in _port_names.keys():
		var ps2 := str(pid)
		if is_port_at_war(ps2):
			continue
		var neigh_raw: Variant = _port_neighbors.get(ps2, null)
		if typeof(neigh_raw) != TYPE_ARRAY:
			continue
		var bump: float = 0.0
		for ni in neigh_raw as Array:
			var nb: String = str(ni)
			if is_port_at_war(nb):
				bump += 0.034
		if bump > 0.0:
			var cur2: float = clampf(float(_port_war_rumor.get(ps2, 0.0)), 0.0, 1.0)
			_port_war_rumor[ps2] = clampf(cur2 + mini(0.22, bump), 0.0, 1.0)


func _npc_tick_scatter_memory_decay() -> void:
	for item in _npc_agents:
		if typeof(item) != TYPE_DICTIONARY:
			continue
		var ag: Dictionary = item as Dictionary
		if str(ag.get("voyage_role", _VOYAGE_ROLE_MERCHANT)) != _VOYAGE_ROLE_MERCHANT:
			continue
		var scv: Variant = ag.get("scattered_ids", null)
		if typeof(scv) == TYPE_ARRAY:
			var sca: Array = scv as Array
			if not sca.is_empty() and _rng.randf() < _SCATTERED_IDS_DECAY_DAILY_P:
				var ri: int = _rng.randi_range(0, sca.size() - 1)
				sca.remove_at(ri)
				ag["scattered_ids"] = sca
		if int(ag.get("voyage_days_remaining", 0)) <= 0:
			var b0: float = clampf(float(ag.get("contact_candidate_bias", 0.0)), 0.0, 1.0)
			if b0 > 0.001:
				b0 = clampf(b0 * _NPC_CONTACT_BIAS_DOCKED_DECAY_MULT, 0.0, 1.0)
				if b0 < 0.02:
					b0 = 0.0
				ag["contact_candidate_bias"] = b0


func _agent_information_post_trade_tick() -> void:
	for pid in _port_names.keys():
		var ps := str(pid)
		if _rng.randf() >= 0.0028:
			continue
		if _goods.is_empty():
			continue
		var keys: Array = _goods.keys()
		var pick: String = str(keys[_rng.randi_range(0, keys.size() - 1)])
		var row0: Variant = _port_rumor_good_delta.get(ps, null)
		if typeof(row0) != TYPE_DICTIONARY:
			_port_rumor_good_delta[ps] = {}
			row0 = _port_rumor_good_delta[ps]
		var row: Dictionary = row0 as Dictionary
		var d0: float = float(row.get(pick, 0.0))
		row[pick] = clampf(d0 + _rng.randf_range(-0.056, 0.056), -0.12, 0.12)


func _agent_production_tick_farms_mines_slaves() -> void:
	_apply_farm_production()
	_apply_mine_production()
	_apply_mint_pulse_to_treasury()
	_tick_slave_attrition_for_ports()


func _agent_industry_and_war_materiel_tick() -> void:
	_apply_industrial_metal_sinks()
	_apply_war_materiel_consumption()


func _agent_merchant_cartel_tick() -> void:
	for pid in _port_names.keys():
		var ps := str(pid)
		var rich: int = 0
		for item in _npc_agents:
			if typeof(item) != TYPE_DICTIONARY:
				continue
			var ag: Dictionary = item as Dictionary
			if int(ag.get("voyage_days_remaining", 0)) != 0:
				continue
			if str(ag.get("docked_port", "")) != ps:
				continue
			if clampi(int(ag.get("money", 0)), 0, _MAX_PURSE_COINS) >= 260:
				rich += 1
		var c: float = clampf(float(_port_cartel_strength.get(ps, 0.0)), 0.0, 1.0)
		if rich >= 4:
			c = clampf(c + 0.07, 0.0, 1.0)
		else:
			c = maxf(0.0, c - 0.055)
		_port_cartel_strength[ps] = c


func _port_total_trade_units_in_stock(port_id: String) -> int:
	var ps := str(port_id)
	if not _port_names.has(ps):
		return 0
	var sumu: int = 0
	for gk in _goods.keys():
		var gis := str(gk)
		if gis == "gold" or gis == "silver":
			continue
		sumu += _port_stock_qty(ps, gis)
	return sumu


## True if a bankrupt captain at `home` is worth replacing with a rookie (harbour still has trade to do).
func _home_port_deserves_bankruptcy_replacement(home: String) -> bool:
	var ps := str(home)
	if not _port_names.has(ps):
		return false
	var row0: Variant = _port_commerce_tick.get(ps, null)
	if typeof(row0) == TYPE_DICTIONARY:
		var row: Dictionary = row0 as Dictionary
		var bu: int = int(row.get("npc_buy_units", 0))
		var su: int = int(row.get("npc_sell_units", 0))
		var bc: int = int(row.get("npc_buy_coins", 0))
		var sc: int = int(row.get("npc_sell_coins", 0))
		if bu + su > 0 or bc + sc > 0:
			return true
	var pulse: float = clampf(float(_port_commerce_pulse.get(ps, 0.0)), 0.0, 1.0)
	if pulse >= _NPC_BANKRUPTCY_REPLACE_MIN_PULSE:
		return true
	return _port_total_trade_units_in_stock(ps) >= _NPC_BANKRUPTCY_REPLACE_MIN_PORT_STOCK_UNITS


func _agent_merchant_sync_home_counts_to_pulse() -> void:
	for pid in _port_names.keys():
		var ps := str(pid)
		var base: int = clampi(int(_port_npc_trader_count.get(ps, 4)), 1, _PORT_NPC_TRADERS_LOAD_MAX)
		var pulse: float = clampf(float(_port_commerce_pulse.get(ps, 0.38)), 0.0, 1.0)
		var bonus: int = int(round((pulse - 0.38) * 7.0))
		var att: int = _wealth_stock_target_for_port(ps)
		var wv: int = int(_port_wealth.get(ps, att))
		if float(wv) < float(maxi(1, att)) * 0.82:
			bonus -= 1
		if pulse < 0.22:
			bonus -= 1
		var want: int = maxi(1, base + bonus)
		var cur: int = 0
		for ag in _npc_agents:
			if typeof(ag) != TYPE_DICTIONARY:
				continue
			if str((ag as Dictionary).get("home_port", "")) == ps:
				cur += 1
		if cur < want:
			var add_n: int = mini(_MERCHANT_HOME_COUNT_STEP_MAX, want - cur)
			for _j in add_n:
				_npc_agents.append(_new_npc_agent(ps))
				cur += 1
		elif cur > want:
			var rem_n: int = mini(_MERCHANT_HOME_COUNT_STEP_MAX, cur - want)
			for _j in rem_n:
				var worst_i: int = -1
				var worst_bs: int = 2147483647
				var worst_id: int = 2147483647
				for i2 in range(_npc_agents.size()):
					var raw2: Variant = _npc_agents[i2]
					if typeof(raw2) != TYPE_DICTIONARY:
						continue
					var ag2: Dictionary = raw2 as Dictionary
					if str(ag2.get("home_port", "")) != ps:
						continue
					var bs2: int = _npc_merchant_balance_sheet_coins(ag2)
					var id2: int = int(ag2.get("id", 0))
					if bs2 < worst_bs or (bs2 == worst_bs and id2 > worst_id):
						worst_bs = bs2
						worst_id = id2
						worst_i = i2
				if worst_i >= 0:
					_npc_agents.remove_at(worst_i)
					cur -= 1
				else:
					break


func _agent_city_commerce_pulse_tick() -> void:
	for pid in _port_names.keys():
		var ps := str(pid)
		var docked: int = _count_npc_docked_at(ps)
		var hc: int = clampi(int(_port_harbour_due_coins_tick.get(ps, 0)), 0, _MAX_PURSE_COINS)
		var row0: Variant = _port_commerce_tick.get(ps, null)
		var bu: int = 0
		var su: int = 0
		var bc: int = 0
		var sc: int = 0
		if typeof(row0) == TYPE_DICTIONARY:
			var row: Dictionary = row0 as Dictionary
			bu = int(row.get("npc_buy_units", 0))
			su = int(row.get("npc_sell_units", 0))
			bc = int(row.get("npc_buy_coins", 0))
			sc = int(row.get("npc_sell_coins", 0))
		var raw: float = _SimAgents.commerce_activity_raw(docked, hc, bu, su, bc, sc)
		var prev: float = maxf(
			_SimAgents.COMMERCE_PULSE_PREV_FLOOR,
			clampf(float(_port_commerce_pulse.get(ps, 0.38)), 0.0, 1.0)
		)
		_port_commerce_pulse[ps] = _SimAgents.commerce_pulse_ema(prev, raw)


func _agent_war_tick_end_of_day() -> void:
	_tick_war_countdown()
	_tick_war_recurring_peace()



func _compute_player_buy_unit(port_id: String, good_id: String, player_counterparty: bool = true) -> int:
	var meta: Variant = _goods.get(good_id, null)
	if typeof(meta) != TYPE_DICTIONARY:
		return 1
	var gd: Dictionary = meta as Dictionary
	var base: int = maxi(1, int(gd.get("unit_buy_price", 1)))
	var target: int = _stock_target_for_good(good_id)
	var stock: int = _port_stock_qty(port_id, good_id)
	var t: float = float(maxi(1, target))
	var skew: float = clamp((float(target) - float(stock)) / t, -1.0, 2.0)
	var mult: float = 1.0 + skew * 0.58
	var tier: String = _need_tier_for_good(good_id)
	mult *= _need_mult_player_buys_from_port(port_id, good_id, player_counterparty)
	if tier == "luxury":
		mult *= _layer_luxury_far_mult_for_port(port_id)
	mult *= _market_demand_supply_mult_for_port_good(port_id, good_id)
	mult *= _port_trade_price_bias_mult(port_id, good_id)
	mult *= _rumor_price_mult_for_port_good(port_id, good_id)
	if good_id == "grain":
		mult *= _crop_grain_buy_price_stress_mult(port_id)
	return maxi(1, int(round(float(base) * mult)))


func _compute_player_sell_unit(port_id: String, good_id: String, player_counterparty: bool = true) -> int:
	var meta: Variant = _goods.get(good_id, null)
	if typeof(meta) != TYPE_DICTIONARY:
		return 1
	var gd: Dictionary = meta as Dictionary
	var base: int = maxi(1, int(gd.get("unit_sell_price", 1)))
	var target: int = _stock_target_for_good(good_id)
	var stock: int = _port_stock_qty(port_id, good_id)
	var t: float = float(maxi(1, target))
	var skew: float = clamp((float(stock) - float(target)) / t, -1.5, 2.0)
	var mult: float = 1.0 - skew * 0.38
	var tier: String = _need_tier_for_good(good_id)
	mult *= _need_mult_player_sells_to_port(port_id, good_id, player_counterparty)
	if tier == "luxury":
		mult *= _layer_luxury_far_mult_for_port(port_id)
	mult *= _market_demand_supply_mult_for_port_good(port_id, good_id)
	mult *= _port_trade_price_bias_mult(port_id, good_id)
	mult *= _rumor_price_mult_for_port_good(port_id, good_id)
	if good_id == "grain":
		mult *= _crop_grain_sell_price_stress_mult(port_id)
	var lux_raw: Variant = _player_ship_row().get("luxury_sell_bonus", null)
	if typeof(lux_raw) == TYPE_DICTIONARY:
		var lux: Dictionary = lux_raw as Dictionary
		var gk := str(good_id)
		if lux.has(gk):
			mult *= clampf(float(lux[gk]), 1.0, 1.35)
	return maxi(1, int(round(float(base) * mult)))


func _serialize_npc_agents() -> Array:
	var out: Array = []
	for item in _npc_agents:
		if typeof(item) != TYPE_DICTIONARY:
			continue
		var ag: Dictionary = (item as Dictionary).duplicate(true)
		var cargo_raw: Variant = ag.get("cargo", {})
		var cargo_copy: Dictionary = {}
		if typeof(cargo_raw) == TYPE_DICTIONARY:
			for gk in (cargo_raw as Dictionary).keys():
				var gid := str(gk)
				cargo_copy[gid] = maxi(0, int((cargo_raw as Dictionary)[gk]))
		ag["cargo"] = cargo_copy
		ag["money"] = clampi(int(ag.get("money", 0)), 0, _MAX_PURSE_COINS)
		ag["ship_condition"] = clampi(int(ag.get("ship_condition", _SHIP_CONDITION_MAX)), _SHIP_CONDITION_MIN, _SHIP_CONDITION_MAX)
		ag["ship_wine_counter"] = clampi(int(ag.get("ship_wine_counter", 0)), 0, 9999)
		ag["fleet_ships"] = clampi(int(ag.get("fleet_ships", 1)), 1, _FLEET_MAX_SHIPS)
		ag["fleet_shipyard_days"] = clampi(int(ag.get("fleet_shipyard_days", 0)), 0, 999)
		if int(ag.get("fleet_shipyard_days", 0)) <= 0:
			ag["fleet_shipyard_port_id"] = ""
		else:
			ag["fleet_shipyard_port_id"] = str(ag.get("fleet_shipyard_port_id", ""))
		var vdays: int = clampi(int(ag.get("voyage_days_remaining", 0)), 0, 999)
		if vdays <= 0:
			ag["voyage_booked_days"] = 0
			ag["voyage_open_sea_01"] = 0.0
		else:
			ag["voyage_booked_days"] = clampi(int(ag.get("voyage_booked_days", vdays)), 1, 999)
			ag["voyage_open_sea_01"] = clampf(float(ag.get("voyage_open_sea_01", _VOYAGE_COASTAL_OPENNESS)), 0.0, 1.0)
		ag["purse_bust_streak"] = clampi(int(ag.get("purse_bust_streak", 0)), 0, 999)
		ag.erase("merchant_acumen")
		ag["buy_mastery"] = clampf(float(ag.get("buy_mastery", 1.0)), _NPC_MASTER_MIN, _NPC_MASTER_MAX)
		ag["sell_mastery"] = clampf(float(ag.get("sell_mastery", 1.0)), _NPC_MASTER_MIN, _NPC_MASTER_MAX)
		if ag.has("risk_aversion"):
			ag["risk_aversion"] = clampf(float(ag.get("risk_aversion", 0.5)), 0.0, 1.0)
		_ensure_npc_big_five(ag)
		_ensure_npc_ship_fields(ag)
		_ensure_npc_voyage_role_and_contract(ag)
		_ensure_npc_convoy_fields(ag)
		_ensure_npc_escort_reputation_fields(ag)
		_sanitize_npc_peer_debts(ag)
		out.append(ag)
	return out


func _deserialize_npc_agents(data: Array) -> void:
	_npc_agents.clear()
	var max_id: int = -1
	for entry in data:
		if typeof(entry) != TYPE_DICTIONARY:
			continue
		var ed: Dictionary = (entry as Dictionary).duplicate(true)
		_normalize_npc_agent_dict(ed)
		var aid: int = int(ed.get("id", -1))
		if aid > max_id:
			max_id = aid
		_npc_agents.append(ed)
	if max_id >= 0:
		_npc_next_agent_id = maxi(_npc_next_agent_id, max_id + 1)


func _migrate_old_npc_traders_to_agents(data: Dictionary) -> void:
	_npc_agents.clear()
	for port_key in data.keys():
		var pid := str(port_key)
		if not _port_names.has(pid):
			continue
		var raw: Variant = data[port_key]
		if typeof(raw) != TYPE_ARRAY:
			continue
		for entry in raw as Array:
			if typeof(entry) != TYPE_DICTIONARY:
				continue
			var ed: Dictionary = entry as Dictionary
			var cargo: Dictionary = {}
			var cr: Variant = ed.get("cargo", null)
			if typeof(cr) == TYPE_DICTIONARY:
				for gk in (cr as Dictionary).keys():
					var gid := str(gk)
					if not _goods.has(gid):
						continue
					cargo[gid] = maxi(0, int((cr as Dictionary)[gk]))
			var sk0: Dictionary = _npc_trade_skills_from_seed(_npc_next_agent_id)
			var sid_m: int = _npc_next_agent_id
			var ag: Dictionary = {
				"id": sid_m,
				"home_port": pid,
				"docked_port": pid,
				"voyage_dest_id": "",
				"voyage_days_remaining": 0,
				"cargo": cargo,
				"money": _default_npc_money_from_seed(sid_m),
				"buy_mastery": float(sk0.get("buy", 1.0)),
				"sell_mastery": float(sk0.get("sell", 1.0)),
				"ship_condition": _SHIP_CONDITION_MAX,
				"ship_wine_counter": 0,
				"fleet_ships": 1,
				"fleet_shipyard_days": 0,
				"fleet_shipyard_port_id": "",
				"voyage_booked_days": 0,
				"voyage_open_sea_01": 0.0,
				"ship_class_id": _default_ship_class_for_port(pid),
				"captain_culture": str(_port_cultures.get(pid, "greek")),
				"voyage_role": _VOYAGE_ROLE_MERCHANT,
				"escort_contract": {},
				"convoy_leader_id": 0,
				"convoy_member_ids": [],
				"convoy_formed": false,
				"convoy_escort_id": 0,
				"convoy_escort_player": false,
				"scattered_ids": [],
				"contact_candidate_bias": 0.0,
				"escort_reliability": 0.55,
				"price_memory": {},
				"risk_aversion": clampf(0.4 + 0.55 * sin(float(sid_m) * 2.963 + 1.1), 0.05, 0.98),
				"voyage_origin_port_id": "",
				"crop_stress_belief_01": 0.0,
			}
			var bf0: Dictionary = _npc_big_five_from_seed(sid_m)
			for kb in bf0.keys():
				ag[kb] = bf0[kb]
			_npc_next_agent_id += 1
			_npc_agents.append(ag)


func _normalize_npc_agent_dict(ag: Dictionary) -> void:
	if not ag.has("cargo") or typeof(ag.get("cargo")) != TYPE_DICTIONARY:
		ag["cargo"] = {}
	var hp: String = str(ag.get("home_port", ""))
	var dp: String = str(ag.get("docked_port", ""))
	if hp.is_empty() and not dp.is_empty():
		ag["home_port"] = dp
	var days: int = maxi(0, int(ag.get("voyage_days_remaining", 0)))
	ag["voyage_days_remaining"] = days
	if days > 0:
		# At sea: do not infer docked_port from home (would break voyages).
		ag["docked_port"] = ""
	else:
		ag["voyage_dest_id"] = ""
		var dp_now: String = str(ag.get("docked_port", ""))
		if dp_now.is_empty() and not hp.is_empty():
			ag["docked_port"] = hp
		else:
			dp_now = str(ag.get("docked_port", ""))
			if not dp_now.is_empty() and not _port_names.has(dp_now):
				ag["docked_port"] = hp
	if days > 0:
		if not ag.has("voyage_booked_days"):
			ag["voyage_booked_days"] = maxi(1, days)
		else:
			ag["voyage_booked_days"] = clampi(int(ag.get("voyage_booked_days", 0)), 1, 999)
		var opx: float = float(ag.get("voyage_open_sea_01", _VOYAGE_COASTAL_OPENNESS))
		ag["voyage_open_sea_01"] = clampf(opx, 0.0, 1.0)
	else:
		ag["voyage_booked_days"] = 0
		ag["voyage_open_sea_01"] = 0.0
	if not ag.has("money"):
		var hid: int = int(ag.get("id", 0))
		ag["money"] = _default_npc_money_from_seed(hid)
	else:
		ag["money"] = clampi(int(ag.get("money", 0)), 0, _MAX_PURSE_COINS)
	_normalize_npc_trade_skills(ag)
	_ensure_npc_ship_fields(ag)
	if not ag.has("fleet_shipyard_days"):
		ag["fleet_shipyard_days"] = 0
	else:
		ag["fleet_shipyard_days"] = clampi(int(ag.get("fleet_shipyard_days", 0)), 0, 999)
	var yport: String = str(ag.get("fleet_shipyard_port_id", ""))
	if int(ag.get("fleet_shipyard_days", 0)) <= 0 or yport.is_empty() or not _port_names.has(yport):
		ag["fleet_shipyard_port_id"] = ""
	else:
		ag["fleet_shipyard_port_id"] = yport
	if not ag.has("purse_bust_streak"):
		ag["purse_bust_streak"] = 0
	else:
		ag["purse_bust_streak"] = clampi(int(ag.get("purse_bust_streak", 0)), 0, 999)
	if not ag.has("price_memory") or typeof(ag.get("price_memory")) != TYPE_DICTIONARY:
		ag["price_memory"] = {}
	else:
		var pm_in: Dictionary = ag["price_memory"] as Dictionary
		var pm_out: Dictionary = {}
		for pk in pm_in.keys():
			var ps: String = str(pk)
			if not _port_names.is_empty() and not _port_names.has(ps):
				continue
			var r0: Variant = pm_in[pk]
			if typeof(r0) != TYPE_DICTIONARY:
				continue
			var rf: Dictionary = {}
			for gk in (r0 as Dictionary).keys():
				var gis: String = str(gk)
				if not _goods.has(gis):
					continue
				var cell: Variant = (r0 as Dictionary)[gk]
				if typeof(cell) != TYPE_DICTIONARY:
					continue
				rf[gis] = {
					"bu": clampi(int((cell as Dictionary).get("bu", 0)), 0, _MAX_PURSE_COINS),
					"se": clampi(int((cell as Dictionary).get("se", 0)), 0, _MAX_PURSE_COINS),
				}
			pm_out[ps] = rf
		ag["price_memory"] = pm_out
	_ensure_npc_risk_aversion(ag)
	_ensure_npc_big_five(ag)
	_ensure_npc_voyage_role_and_contract(ag)
	_normalize_npc_convoy_invariants(ag)
	_ensure_npc_escort_reputation_fields(ag)
	_sanitize_npc_peer_debts(ag)
	var tgu: Variant = ag.get("toll_graft_until", null)
	if typeof(tgu) == TYPE_DICTIONARY:
		var tgo: Dictionary = {}
		for pk in (tgu as Dictionary).keys():
			var pxs: String = str(pk)
			if not _port_names.has(pxs):
				continue
			var u0: int = clampi(int((tgu as Dictionary)[pk]), 0, 999999)
			if current_day <= u0:
				tgo[pxs] = u0
		if tgo.is_empty():
			ag.erase("toll_graft_until")
		else:
			ag["toll_graft_until"] = tgo
	else:
		ag.erase("toll_graft_until")
	if not ag.has("voyage_origin_port_id"):
		ag["voyage_origin_port_id"] = ""
	else:
		ag["voyage_origin_port_id"] = str(ag.get("voyage_origin_port_id", ""))
	if not ag.has("crop_stress_belief_01"):
		ag["crop_stress_belief_01"] = 0.0
	else:
		ag["crop_stress_belief_01"] = clampf(float(ag.get("crop_stress_belief_01", 0.0)), 0.0, 1.0)
	if not ag.has("pirate_notoriety"):
		ag["pirate_notoriety"] = 0.0
	else:
		ag["pirate_notoriety"] = clampf(float(ag.get("pirate_notoriety", 0.0)), 0.0, _PIRATE_NOTORIETY_CAP)
	_ensure_npc_merchant_contract_fields(ag)


func _ensure_npc_merchant_contract_fields(ag: Dictionary) -> void:
	if not ag.has("merchant_repute_01"):
		var sid: int = int(ag.get("id", 0))
		ag["merchant_repute_01"] = clampf(0.48 + 0.22 * float(sid % 997) / 997.0, 0.0, 1.0)
	else:
		ag["merchant_repute_01"] = clampf(float(ag.get("merchant_repute_01", 0.52)), 0.0, 1.0)
	var ct0: Variant = ag.get("npc_city_trust_01", null)
	if typeof(ct0) != TYPE_DICTIONARY:
		ag["npc_city_trust_01"] = {}
	else:
		var ctd: Dictionary = ct0 as Dictionary
		var cto: Dictionary = {}
		for pk in ctd.keys():
			var pxs: String = str(pk)
			if not _port_names.has(pxs):
				continue
			cto[pxs] = clampf(float(ctd[pk]), 0.0, 1.0)
		ag["npc_city_trust_01"] = cto
	_npc_prune_npc_city_trust_dict(ag)
	var cg0: Variant = ag.get("city_grain_contract", null)
	if typeof(cg0) != TYPE_DICTIONARY:
		ag["city_grain_contract"] = {}
	else:
		var cg: Dictionary = cg0 as Dictionary
		var iss: String = str(cg.get("issuer", ""))
		var dst: String = str(cg.get("dest", ""))
		var qty: int = clampi(int(cg.get("qty", 0)), 0, 999)
		var due: int = clampi(int(cg.get("due", 0)), 0, 9999999)
		var adv: int = clampi(int(cg.get("advance", 0)), 0, _MAX_PURSE_COINS)
		if (
			iss.is_empty()
			or not _port_names.has(iss)
			or dst.is_empty()
			or not _port_names.has(dst)
			or iss == dst
			or qty < _NPC_CITY_GRAIN_CONTRACT_QTY_MIN
			or not _goods.has("grain")
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


func _npc_prune_npc_city_trust_dict(ag: Dictionary) -> void:
	var m: Dictionary = ag.get("npc_city_trust_01", {}) as Dictionary
	if m.size() <= _NPC_CITY_TRUST_PORT_MAX_KEYS:
		return
	var scored: Array[Dictionary] = []
	for pk in m.keys():
		scored.append({"k": str(pk), "v": clampf(float(m[pk]), 0.0, 1.0)})
	scored.sort_custom(func(a: Dictionary, b: Dictionary) -> bool: return float(a["v"]) < float(b["v"]))
	var drop: int = m.size() - _NPC_CITY_TRUST_PORT_MAX_KEYS
	var i: int = 0
	while i < drop and not scored.is_empty():
		var ek: String = str(scored[i].get("k", ""))
		if not ek.is_empty():
			m.erase(ek)
		i += 1
	ag["npc_city_trust_01"] = m


func _npc_city_trust_get(ag: Dictionary, port_id: String) -> float:
	var ps := str(port_id)
	if not _port_names.has(ps):
		return 0.5
	var m: Dictionary = ag.get("npc_city_trust_01", {}) as Dictionary
	if m.has(ps):
		return clampf(float(m[ps]), 0.0, 1.0)
	return clampf(float(ag.get("merchant_repute_01", 0.52)), 0.0, 1.0)


func _npc_city_trust_bump(ag: Dictionary, port_id: String, delta: float) -> void:
	var ps := str(port_id)
	if not _port_names.has(ps):
		return
	var m: Dictionary = (ag.get("npc_city_trust_01", {}) as Dictionary).duplicate()
	var cur: float = _npc_city_trust_get(ag, ps)
	m[ps] = clampf(cur + delta, 0.0, 1.0)
	ag["npc_city_trust_01"] = m
	_npc_prune_npc_city_trust_dict(ag)


func _npc_city_grain_contract_active(ag: Dictionary) -> bool:
	var cg: Dictionary = ag.get("city_grain_contract", {}) as Dictionary
	if cg.is_empty():
		return false
	var iss: String = str(cg.get("issuer", ""))
	var dst: String = str(cg.get("dest", ""))
	return _port_names.has(iss) and _port_names.has(dst) and iss != dst


func _npc_clear_city_grain_contract(ag: Dictionary) -> void:
	ag["city_grain_contract"] = {}


func _npc_depart_dest_contract_bias(ag: Dictionary, here: String, dest: String) -> String:
	if not _world_npc_city_grain_contracts_enabled:
		return dest
	if not _npc_city_grain_contract_active(ag):
		return dest
	var cg: Dictionary = ag.get("city_grain_contract", {}) as Dictionary
	var cdest: String = str(cg.get("dest", ""))
	var due: int = clampi(int(cg.get("due", 0)), 0, 9999999)
	if cdest.is_empty() or not _port_names.has(cdest) or cdest == here:
		return dest
	if dest == cdest:
		return dest
	var rep: float = clampf(float(ag.get("merchant_repute_01", 0.52)), 0.0, 1.0)
	var consc: float = _npc_trait_f(ag, _NPC_TRAIT_CONSC)
	var extra: float = _npc_trait_f(ag, _NPC_TRAIT_EXTRA)
	var p_stick: float = 0.18 + 0.48 * rep + 0.22 * consc - 0.12 * extra
	var slack: int = due - current_day
	if slack <= 14:
		p_stick += 0.20
	if slack <= 7:
		p_stick += 0.14
	var plan: Dictionary = _voyage_plan(here, cdest, float(ag.get("risk_aversion", 0.5)), true)
	var est_d: int = maxi(1, int(plan.get("days", 4)))
	if slack <= est_d + 2:
		p_stick += 0.12
	p_stick = clampf(p_stick, 0.06, 0.91)
	if _rng.randf() < p_stick:
		return cdest
	return dest


func _npc_try_fulfill_city_grain_contract_on_arrival(ag: Dictionary, dest: String) -> void:
	if not _npc_city_grain_contract_active(ag):
		return
	var cg: Dictionary = ag.get("city_grain_contract", {}) as Dictionary
	if str(cg.get("dest", "")) != str(dest):
		return
	if not ag.has("cargo") or typeof(ag.get("cargo")) != TYPE_DICTIONARY:
		return
	var cargo: Dictionary = ag["cargo"] as Dictionary
	var need: int = clampi(int(cg.get("qty", 0)), 1, 999)
	var have: int = _npc_cargo_qty(cargo, "grain")
	if have < need:
		return
	var iss: String = str(cg.get("issuer", ""))
	_npc_adjust_cargo(cargo, "grain", -need)
	_adjust_port_stock(dest, "grain", need)
	var bonus: int = clampi(6 + need / 2, 4, 48)
	ag["money"] = clampi(int(ag.get("money", 0)) + bonus, 0, _MAX_PURSE_COINS)
	_bump_port_wealth(dest, maxi(1, bonus / 3))
	ag["merchant_repute_01"] = clampf(float(ag.get("merchant_repute_01", 0.5)) + 0.028, 0.0, 1.0)
	_npc_city_trust_bump(ag, iss, 0.045)
	_npc_city_trust_bump(ag, dest, 0.022)
	_npc_clear_city_grain_contract(ag)


func _npc_city_grain_contract_breach(ag: Dictionary, issuer: String) -> void:
	if not _port_names.has(str(issuer)):
		_npc_clear_city_grain_contract(ag)
		return
	var cg: Dictionary = ag.get("city_grain_contract", {}) as Dictionary
	var adv: int = clampi(int(cg.get("advance", 0)), 0, _MAX_PURSE_COINS)
	var fine: int = clampi(int(ceil(float(maxi(adv, 12)) * 1.25)), 0, _MAX_PURSE_COINS)
	var purse: int = clampi(int(ag.get("money", 0)), 0, _MAX_PURSE_COINS)
	var take: int = mini(fine, purse)
	ag["money"] = purse - take
	if take > 0:
		_bump_port_wealth(str(issuer), maxi(1, take / 4))
	ag["merchant_repute_01"] = clampf(float(ag.get("merchant_repute_01", 0.5)) - 0.05, 0.0, 1.0)
	_npc_city_trust_bump(ag, str(issuer), -0.14)
	_npc_clear_city_grain_contract(ag)


func _npc_tick_merchant_city_contracts_docked() -> void:
	for item in _npc_agents:
		if typeof(item) != TYPE_DICTIONARY:
			continue
		var ag: Dictionary = item as Dictionary
		if str(ag.get("voyage_role", _VOYAGE_ROLE_MERCHANT)) != _VOYAGE_ROLE_MERCHANT:
			continue
		if int(ag.get("voyage_days_remaining", 0)) != 0:
			continue
		if not _npc_city_grain_contract_active(ag):
			continue
		var cg: Dictionary = ag.get("city_grain_contract", {}) as Dictionary
		var due: int = clampi(int(cg.get("due", 0)), 0, 9999999)
		if current_day <= due:
			continue
		var iss: String = str(cg.get("issuer", ""))
		var dst: String = str(cg.get("dest", ""))
		var need: int = clampi(int(cg.get("qty", 0)), 1, 999)
		if not ag.has("cargo") or typeof(ag.get("cargo")) != TYPE_DICTIONARY:
			_npc_city_grain_contract_breach(ag, iss)
			continue
		var have: int = _npc_cargo_qty(ag["cargo"] as Dictionary, "grain")
		var dp: String = str(ag.get("docked_port", ""))
		if dp == dst and have >= need:
			_npc_try_fulfill_city_grain_contract_on_arrival(ag, dst)
		else:
			_npc_city_grain_contract_breach(ag, iss)


func _npc_try_offer_city_grain_contract(agent: Dictionary, dock_pid: String) -> void:
	if not _world_npc_city_grain_contracts_enabled:
		return
	if not _goods.has("grain"):
		return
	if _npc_convoy_is_follower(agent) or bool(agent.get("convoy_formed", false)):
		return
	if str(agent.get("voyage_role", _VOYAGE_ROLE_MERCHANT)) != _VOYAGE_ROLE_MERCHANT:
		return
	if int(agent.get("voyage_days_remaining", 0)) != 0:
		return
	if _npc_city_grain_contract_active(agent):
		return
	var ps: String = str(dock_pid)
	if not _port_names.has(ps):
		return
	var rep: float = clampf(float(agent.get("merchant_repute_01", 0.52)), 0.0, 1.0)
	var p_offer: float = clampf(
		_NPC_CITY_GRAIN_CONTRACT_OFFER_P * lerpf(0.78, 1.12, rep), 0.012, 0.068
	)
	if _rng.randf() > p_offer:
		return
	var opts: PackedStringArray = []
	for pk in _port_names.keys():
		var p2: String = str(pk)
		if p2 != ps:
			opts.append(p2)
	if opts.is_empty():
		return
	var dest: String = str(opts[_rng.randi_range(0, opts.size() - 1)])
	if not _port_names.has(dest):
		return
	var qty: int = _rng.randi_range(_NPC_CITY_GRAIN_CONTRACT_QTY_MIN, _NPC_CITY_GRAIN_CONTRACT_QTY_MAX)
	if _port_stock_qty(ps, "grain") < qty:
		return
	var due: int = current_day + _rng.randi_range(_NPC_CITY_GRAIN_CONTRACT_DUE_MIN, _NPC_CITY_GRAIN_CONTRACT_DUE_MAX)
	var tr_iss: float = _npc_city_trust_get(agent, ps)
	var agree: float = _npc_trait_f(agent, _NPC_TRAIT_AGREE)
	var consc: float = _npc_trait_f(agent, _NPC_TRAIT_CONSC)
	var p_accept: float = clampf(0.22 + 0.55 * rep + 0.18 * tr_iss + 0.12 * agree + 0.10 * consc - 0.08 * _npc_trait_f(agent, _NPC_TRAIT_NEURO), 0.08, 0.92)
	if _rng.randf() > p_accept:
		return
	var advance: int = clampi(int(12.0 + float(qty) * 2.1 + 70.0 * rep + 40.0 * tr_iss), 10, 160)
	var pw: int = clampi(int(_port_wealth.get(ps, 100)), 0, 999999)
	if pw < advance / 2:
		return
	_port_wealth[ps] = clampi(pw - advance / 2, 0, 999999)
	var trsy: int = clampi(int(floor(float(advance) * _NPC_CITY_CONTRACT_TREASURY_FRAC)), 0, _WORLD_TREASURY_MAX)
	_world_treasury_coins = clampi(_world_treasury_coins + trsy, 0, _WORLD_TREASURY_MAX)
	agent["money"] = clampi(int(agent.get("money", 0)) + advance, 0, _MAX_PURSE_COINS)
	agent["city_grain_contract"] = {
		"issuer": ps,
		"dest": dest,
		"good": "grain",
		"qty": qty,
		"due": due,
		"advance": advance,
	}


func _ensure_npc_risk_aversion(ag: Dictionary) -> void:
	if not ag.has("risk_aversion"):
		var sid: int = int(ag.get("id", 0))
		ag["risk_aversion"] = clampf(0.4 + 0.55 * sin(float(sid) * 2.963 + 1.1), 0.05, 0.98)
	else:
		ag["risk_aversion"] = clampf(float(ag.get("risk_aversion", 0.5)), 0.0, 1.0)


func _npc_big_five_from_seed(seed: int) -> Dictionary:
	var s: float = float(seed)
	var o: float = clampf(0.5 + 0.41 * sin(s * 0.813 + 0.17) * cos(s * 0.291), 0.06, 0.94)
	var c: float = clampf(0.5 + 0.41 * cos(s * 0.733 + 0.31) * sin(s * 0.377), 0.06, 0.94)
	var e: float = clampf(0.5 + 0.41 * sin(s * 0.511 + 0.91) * sin(s * 0.619), 0.06, 0.94)
	var a: float = clampf(0.5 + 0.41 * cos(s * 0.443 + 0.07) * cos(s * 0.881), 0.06, 0.94)
	var n: float = clampf(0.5 + 0.41 * sin(s * 0.667 + 0.53) * cos(s * 0.409), 0.06, 0.94)
	return {
		_NPC_TRAIT_OPEN: o,
		_NPC_TRAIT_CONSC: c,
		_NPC_TRAIT_EXTRA: e,
		_NPC_TRAIT_AGREE: a,
		_NPC_TRAIT_NEURO: n,
	}


func _roll_npc_big_five() -> Dictionary:
	return {
		_NPC_TRAIT_OPEN: _rng.randf_range(0.1, 0.9),
		_NPC_TRAIT_CONSC: _rng.randf_range(0.1, 0.9),
		_NPC_TRAIT_EXTRA: _rng.randf_range(0.1, 0.9),
		_NPC_TRAIT_AGREE: _rng.randf_range(0.1, 0.9),
		_NPC_TRAIT_NEURO: _rng.randf_range(0.1, 0.9),
	}


func _ensure_npc_big_five(ag: Dictionary) -> void:
	var seeded: Dictionary = _npc_big_five_from_seed(int(ag.get("id", 0)))
	for k in seeded.keys():
		if ag.has(k):
			ag[k] = clampf(float(ag[k]), 0.0, 1.0)
		else:
			ag[k] = clampf(float(seeded[k]), 0.0, 1.0)


func _npc_trait_f(ag: Dictionary, trait_key: String) -> float:
	_ensure_npc_big_five(ag)
	return clampf(float(ag.get(trait_key, 0.5)), 0.0, 1.0)


func _npc_trade_effective_risk(agent: Dictionary) -> float:
	_ensure_npc_risk_aversion(agent)
	_ensure_npc_big_five(agent)
	var r: float = clampf(float(agent.get("risk_aversion", 0.5)), 0.0, 1.0)
	var n: float = clampf(float(agent.get(_NPC_TRAIT_NEURO, 0.5)), 0.0, 1.0)
	# Softer than 0.38: high neuroticism + small lots → many fee-bearing trades → thin purses.
	return mini(0.91, clampf(r + 0.22 * (n - 0.5), 0.0, 1.0))


func _npc_depart_effective_stay_gate(agent: Dictionary, docked_port: String) -> float:
	_ensure_npc_big_five(agent)
	var o: float = _npc_trait_f(agent, _NPC_TRAIT_OPEN)
	var c: float = _npc_trait_f(agent, _NPC_TRAIT_CONSC)
	var e: float = _npc_trait_f(agent, _NPC_TRAIT_EXTRA)
	var n: float = _npc_trait_f(agent, _NPC_TRAIT_NEURO)
	var gate: float = _NPC_DEPART_STAY_GATE
	gate -= 0.072 * (e - 0.5)
	gate -= 0.055 * (o - 0.5)
	var urel: float = float(get_port_food_unrest(docked_port)) / 200.0
	gate += 0.095 * (c - 0.5) * urel
	gate -= 0.14 * (n - 0.5) * urel
	gate -= _npc_peer_loan_flee_gate_sub(agent, docked_port)
	return clampf(gate, 0.10, 0.94)


func _npc_trading_memory_pick_probability(agent: Dictionary) -> float:
	_ensure_npc_big_five(agent)
	var o: float = _npc_trait_f(agent, _NPC_TRAIT_OPEN)
	var c: float = _npc_trait_f(agent, _NPC_TRAIT_CONSC)
	var p: float = lerpf(0.40, 0.82, c) * lerpf(1.08, 0.54, o)
	return clampf(p, 0.26, 0.88)


func _npc_dock_dust_purse_floor(agent: Dictionary) -> int:
	_ensure_npc_big_five(agent)
	var n: float = clampf(float(agent.get(_NPC_TRAIT_NEURO, 0.5)), 0.0, 1.0)
	return _NPC_DOCK_DUST_PURSE + int(round(9.0 * n))


func _npc_big5_agree_buy_mult(agent: Dictionary) -> float:
	return 1.0 + 0.034 * (_npc_trait_f(agent, _NPC_TRAIT_AGREE) - 0.5)


func _npc_big5_agree_sell_mult(agent: Dictionary) -> float:
	return 1.0 - 0.034 * (_npc_trait_f(agent, _NPC_TRAIT_AGREE) - 0.5)


func _ensure_npc_ship_fields(ag: Dictionary) -> void:
	if not ag.has("ship_condition"):
		ag["ship_condition"] = _SHIP_CONDITION_MAX
	else:
		ag["ship_condition"] = clampi(int(ag.get("ship_condition", _SHIP_CONDITION_MAX)), _SHIP_CONDITION_MIN, _SHIP_CONDITION_MAX)
	if not ag.has("ship_wine_counter"):
		ag["ship_wine_counter"] = 0
	else:
		ag["ship_wine_counter"] = clampi(int(ag.get("ship_wine_counter", 0)), 0, 9999)
	if not ag.has("fleet_ships"):
		ag["fleet_ships"] = 1
	else:
		ag["fleet_ships"] = clampi(int(ag.get("fleet_ships", 1)), 1, _FLEET_MAX_SHIPS)
	var hp0: String = str(ag.get("home_port", ""))
	if not ag.has("ship_class_id") or str(ag.get("ship_class_id", "")).is_empty():
		ag["ship_class_id"] = _default_ship_class_for_port(hp0 if _port_names.has(hp0) else player_port_id)
	elif not _ship_classes.has(str(ag.get("ship_class_id", ""))):
		ag["ship_class_id"] = _default_ship_class_for_port(hp0 if _port_names.has(hp0) else player_port_id)
	if not ag.has("captain_culture") or str(ag.get("captain_culture", "")).is_empty():
		ag["captain_culture"] = str(_port_cultures.get(hp0, "greek"))


func _normalize_npc_trade_skills(ag: Dictionary) -> void:
	if ag.has("buy_mastery") and ag.has("sell_mastery"):
		ag["buy_mastery"] = clampf(float(ag.get("buy_mastery", 1.0)), _NPC_MASTER_MIN, _NPC_MASTER_MAX)
		ag["sell_mastery"] = clampf(float(ag.get("sell_mastery", 1.0)), _NPC_MASTER_MIN, _NPC_MASTER_MAX)
	elif ag.has("merchant_acumen"):
		var u: float = clampf(float(ag.get("merchant_acumen", 1.0)), 0.88, 1.18)
		ag["buy_mastery"] = clampf(u, _NPC_MASTER_MIN, _NPC_MASTER_MAX)
		ag["sell_mastery"] = clampf(u, _NPC_MASTER_MIN, _NPC_MASTER_MAX)
		ag.erase("merchant_acumen")
	else:
		var sid: int = int(ag.get("id", 0))
		var sk: Dictionary = _npc_trade_skills_from_seed(sid)
		ag["buy_mastery"] = float(sk.get("buy", 1.0))
		ag["sell_mastery"] = float(sk.get("sell", 1.0))


func _npc_trade_skills_from_seed(seed: int) -> Dictionary:
	var b: float = clampf(
		0.92 + sin(float(seed) * 2.17) * 0.16 + sin(float(seed) * 0.41) * 0.09, _NPC_MASTER_MIN, _NPC_MASTER_MAX
	)
	var s: float = clampf(
		0.92 + cos(float(seed) * 1.97) * 0.16 + cos(float(seed) * 0.37) * 0.09, _NPC_MASTER_MIN, _NPC_MASTER_MAX
	)
	return {"buy": b, "sell": s}


func _roll_npc_trade_skills() -> Dictionary:
	var b: float = _rng.randf_range(0.84, 1.12)
	var s: float = _rng.randf_range(0.84, 1.12)
	var r: float = _rng.randf()
	if r < 0.11:
		b = _rng.randf_range(0.76, 0.91)
		s = _rng.randf_range(0.76, 0.91)
	elif r < 0.24:
		b = _rng.randf_range(1.04, 1.22)
		s = _rng.randf_range(0.79, 0.99)
	elif r < 0.37:
		b = _rng.randf_range(0.79, 0.99)
		s = _rng.randf_range(1.04, 1.22)
	elif r < 0.50:
		b = _rng.randf_range(1.02, 1.20)
		s = _rng.randf_range(1.02, 1.20)
	return {"buy": clampf(b, _NPC_MASTER_MIN, _NPC_MASTER_MAX), "sell": clampf(s, _NPC_MASTER_MIN, _NPC_MASTER_MAX)}


func _default_npc_money_from_seed(seed: int) -> int:
	var mn: int = _NPC_START_MONEY_MIN
	var mx: int = _NPC_START_MONEY_MAX
	if mx < mn:
		mx = mn
	var span: int = mx - mn + 1
	var s: int = ((seed * 31 + 17) % span + span) % span
	return mn + s


func _ensure_npc_money_field(agent: Dictionary) -> void:
	if not agent.has("money"):
		agent["money"] = _default_npc_money_from_seed(int(agent.get("id", 0)))
	else:
		agent["money"] = clampi(int(agent.get("money", 0)), 0, _MAX_PURSE_COINS)
	_normalize_npc_trade_skills(agent)
	_ensure_npc_ship_fields(agent)
	_ensure_npc_risk_aversion(agent)
	_ensure_npc_big_five(agent)
	_ensure_npc_voyage_role_and_contract(agent)
	_ensure_npc_convoy_fields(agent)
	_ensure_npc_escort_reputation_fields(agent)
	_sanitize_npc_peer_debts(agent)


func _random_npc_starting_cargo() -> Dictionary:
	var cargo: Dictionary = {}
	for good_id in _goods.keys():
		var gid := str(good_id)
		if gid == "grain":
			cargo[gid] = _rng.randi_range(2, 10)
		elif gid == "wine":
			cargo[gid] = _rng.randi_range(0, 7)
		elif gid == "metal" or gid == "wire":
			cargo[gid] = _rng.randi_range(0, 4)
		elif gid == "gold" or gid == "silver":
			cargo[gid] = _rng.randi_range(0, 1) if _rng.randf() < 0.14 else 0
		elif gid == "slaves":
			cargo[gid] = _rng.randi_range(0, 2)
		elif gid == "marines":
			cargo[gid] = _rng.randi_range(0, 2)
		else:
			cargo[gid] = _rng.randi_range(0, 4)
	return cargo


func _new_npc_agent(home_port: String, bankruptcy_replacement: bool = false, inherit_skills: Variant = null) -> Dictionary:
	var sk1: Dictionary = _roll_npc_trade_skills()
	if inherit_skills != null and typeof(inherit_skills) == TYPE_DICTIONARY:
		var inh: Dictionary = inherit_skills as Dictionary
		var pb: float = clampf(float(inh.get("buy", 1.0)), _NPC_MASTER_MIN, _NPC_MASTER_MAX)
		var psb: float = clampf(float(inh.get("sell", 1.0)), _NPC_MASTER_MIN, _NPC_MASTER_MAX)
		sk1["buy"] = clampf(0.42 * float(sk1["buy"]) + 0.58 * pb, _NPC_MASTER_MIN, _NPC_MASTER_MAX)
		sk1["sell"] = clampf(0.42 * float(sk1["sell"]) + 0.58 * psb, _NPC_MASTER_MIN, _NPC_MASTER_MAX)
	var pmn: int = _NPC_START_MONEY_MIN
	var pmx: int = _NPC_START_MONEY_MAX
	var purse_want: int = _rng.randi_range(mini(pmn, pmx), maxi(pmn, pmx))
	var from_t: int = mini(purse_want, _world_treasury_coins)
	_world_treasury_coins = clampi(_world_treasury_coins - from_t, 0, _WORLD_TREASURY_MAX)
	var ag: Dictionary = {
		"id": _npc_next_agent_id,
		"home_port": home_port,
		"docked_port": home_port,
		"voyage_dest_id": "",
		"voyage_days_remaining": 0,
		"cargo": _random_npc_starting_cargo(),
		"money": purse_want,
		"buy_mastery": float(sk1.get("buy", 1.0)),
		"sell_mastery": float(sk1.get("sell", 1.0)),
		"ship_condition": _SHIP_CONDITION_MAX,
		"ship_wine_counter": 0,
		"fleet_ships": 1,
		"fleet_shipyard_days": 0,
		"fleet_shipyard_port_id": "",
		"purse_bust_streak": 0,
		"price_memory": {},
		"risk_aversion": _rng.randf_range(0.08, 0.92),
		"voyage_booked_days": 0,
		"voyage_open_sea_01": 0.0,
		"ship_class_id": _default_ship_class_for_port(home_port),
		"captain_culture": str(_port_cultures.get(home_port, "greek")),
		"voyage_role": _VOYAGE_ROLE_MERCHANT,
		"escort_contract": {},
		"convoy_leader_id": 0,
		"convoy_member_ids": [],
		"convoy_formed": false,
		"convoy_escort_id": 0,
		"convoy_escort_player": false,
		"scattered_ids": [],
		"contact_candidate_bias": 0.0,
		"escort_reliability": 0.55,
		"pirate_notoriety": 0.0,
		"npc_peer_debts": [],
		"voyage_origin_port_id": "",
		"crop_stress_belief_01": 0.0,
		"merchant_season_ticks": 0,
		"merchant_repute_01": clampf(0.46 + 0.26 * float(_npc_next_agent_id % 991) / 991.0, 0.0, 1.0),
		"npc_city_trust_01": {},
		"city_grain_contract": {},
	}
	var bf1: Dictionary = _roll_npc_big_five()
	for kb in bf1.keys():
		ag[kb] = bf1[kb]
	_npc_next_agent_id += 1
	if bankruptcy_replacement:
		_rookie_try_charter_cheapest_used_hull_from_slip(ag, home_port)
	return ag


func _bootstrap_npc_agents() -> void:
	_npc_agents.clear()
	_npc_next_agent_id = 0
	for pid in _port_names.keys():
		var n: int = clampi(int(_port_npc_trader_count.get(pid, 4)), 1, _PORT_NPC_TRADERS_LOAD_MAX)
		for _i in n:
			_npc_agents.append(_new_npc_agent(str(pid)))


func _ensure_npc_counts_match_config() -> void:
	_agent_merchant_sync_home_counts_to_pulse()


func _npc_advance_voyages() -> void:
	var idxm: Dictionary = _npc_index_agents_by_id()
	for item2 in _npc_agents:
		if typeof(item2) != TYPE_DICTIONARY:
			continue
		var ags: Dictionary = item2 as Dictionary
		if not _npc_convoy_is_follower(ags):
			continue
		var cl0: int = int(ags.get("convoy_leader_id", 0))
		if not idxm.has(cl0):
			continue
		var L0: Dictionary = idxm[cl0] as Dictionary
		if int(L0.get("voyage_days_remaining", 0)) <= 0:
			continue
		ags["voyage_days_remaining"] = int(L0.get("voyage_days_remaining", 0))
		ags["voyage_dest_id"] = str(L0.get("voyage_dest_id", ""))
		ags["voyage_booked_days"] = int(L0.get("voyage_booked_days", 0))
		ags["voyage_open_sea_01"] = clampf(float(L0.get("voyage_open_sea_01", 0.0)), 0.0, 1.0)
	for item in _npc_agents:
		if typeof(item) != TYPE_DICTIONARY:
			continue
		var ag: Dictionary = item as Dictionary
		if _npc_convoy_is_follower(ag):
			continue
		var days: int = int(ag.get("voyage_days_remaining", 0))
		if days <= 0:
			continue
		days -= 1
		ag["voyage_days_remaining"] = days
		var lid0: int = int(ag.get("convoy_leader_id", 0))
		var self_id0: int = int(ag.get("id", 0))
		if lid0 == self_id0 and bool(ag.get("convoy_formed", false)):
			var mm: Array = ag.get("convoy_member_ids", []) as Array
			for mid in mm:
				if not idxm.has(int(mid)):
					continue
				var fw: Dictionary = idxm[int(mid)] as Dictionary
				if not _npc_convoy_is_follower(fw):
					continue
				if int(fw.get("convoy_leader_id", 0)) != self_id0:
					continue
				fw["voyage_days_remaining"] = days
			var esid0: int = int(ag.get("convoy_escort_id", 0))
			if esid0 > 0 and idxm.has(esid0):
				var exs: Dictionary = idxm[esid0] as Dictionary
				if str(exs.get("voyage_role", "")) == _VOYAGE_ROLE_ESCORT and int(exs.get("convoy_leader_id", 0)) == self_id0:
					exs["voyage_days_remaining"] = days
		if days != 0:
			continue
		var dest: String = str(ag.get("voyage_dest_id", ""))
		var member_ids_arrive: Array = []
		if lid0 == self_id0 and bool(ag.get("convoy_formed", false)):
			member_ids_arrive = (ag.get("convoy_member_ids", []) as Array).duplicate()
		var escort_arrive_id: int = int(ag.get("convoy_escort_id", 0))
		var hire_player_arrive: bool = bool(ag.get("convoy_escort_player", false))
		if hire_player_arrive:
			if (
				str(player_voyage_role) == _VOYAGE_ROLE_ESCORT
				and int(player_escort_contract.get("employer_id", -9)) == self_id0
			):
				_player_escort_pay_on_convoy_arrival(ag)
				_player_finish_escort_on_npc_convoy_arrival(ag, dest)
		elif escort_arrive_id > 0 and idxm.has(escort_arrive_id):
			var esca: Dictionary = idxm[escort_arrive_id] as Dictionary
			if str(esca.get("voyage_role", "")) == _VOYAGE_ROLE_ESCORT and int(esca.get("convoy_leader_id", 0)) == self_id0:
				_npc_escort_pay_on_convoy_arrival(ag, esca)
		_npc_finish_npc_voyage_arrival(ag, dest)
		for mid2 in member_ids_arrive:
			if not idxm.has(int(mid2)):
				continue
			var mem: Dictionary = idxm[int(mid2)] as Dictionary
			if not _npc_convoy_is_follower(mem):
				continue
			if str(mem.get("voyage_dest_id", "")) != dest:
				continue
			_npc_finish_npc_voyage_arrival(mem, dest)
		if escort_arrive_id > 0 and idxm.has(escort_arrive_id):
			var escb: Dictionary = idxm[escort_arrive_id] as Dictionary
			if int(escb.get("voyage_days_remaining", 0)) <= 0:
				_npc_finish_npc_voyage_arrival(escb, dest)


func _npc_trade_if_docked(agent: Dictionary) -> void:
	if int(agent.get("voyage_days_remaining", 0)) != 0:
		return
	var pid: String = str(agent.get("docked_port", ""))
	if pid.is_empty() or not _port_names.has(pid):
		return
	_npc_fire_sale_for_cashflow_docked(pid, agent)
	_npc_tick_one(pid, agent)
	if int(agent.get("voyage_days_remaining", 0)) != 0:
		return
	var ex: float = _npc_trait_f(agent, _NPC_TRAIT_EXTRA)
	var p2: float = clampf(0.72 + 0.06 * (ex - 0.5), 0.62, 0.80)
	if _rng.randf() < p2:
		_npc_tick_one(pid, agent)
	if int(agent.get("voyage_days_remaining", 0)) != 0:
		return
	var p3: float = clampf(0.42 + 0.05 * (ex - 0.5), 0.32, 0.52)
	if _rng.randf() < p3:
		_npc_tick_one(pid, agent)
	_npc_liquidate_one_unit_if_dust_docked(pid, agent)
	_npc_snapshot_price_memory(agent, pid)
	_npc_maybe_voluntary_hull_fire_sale_if_docked(pid, agent)
	_npc_try_offer_city_grain_contract(agent, pid)


func _npc_apply_officer_pay_if_docked_after_trade() -> void:
	for item in _npc_agents:
		if typeof(item) != TYPE_DICTIONARY:
			continue
		var ag: Dictionary = item as Dictionary
		if int(ag.get("voyage_days_remaining", 0)) != 0:
			continue
		var pid: String = str(ag.get("docked_port", ""))
		if pid.is_empty() or not _port_names.has(pid):
			continue
		_ensure_npc_ship_fields(ag)
		if not ag.has("cargo") or typeof(ag.get("cargo")) != TYPE_DICTIONARY:
			ag["cargo"] = {}
		var cargo_d: Dictionary = ag["cargo"] as Dictionary
		var ships: int = clampi(int(ag.get("fleet_ships", 1)), 1, _FLEET_MAX_SHIPS)
		var srow_o: Dictionary = _npc_ship_row(ag)
		var culd_o: Dictionary = _npc_cultural_ops_scale(ag)
		var oph_o: int = maxi(1, int(srow_o.get("officer_pay_per_hull", 1)))
		var off_sc_o: float = float(oph_o) * float(culd_o.get("officer_scale", 1.0))
		var cap: Dictionary = {
			"money": clampi(int(ag.get("money", 0)), 0, _MAX_PURSE_COINS),
			"cargo": cargo_d,
			"ship_condition": int(ag.get("ship_condition", _SHIP_CONDITION_MAX)),
			"ship_wine_counter": int(ag.get("ship_wine_counter", 0)),
			"fleet_ships": ships,
			"officer_pay_scale": off_sc_o,
		}
		_tick_captain_officer_pay(cap, false)
		ag["money"] = clampi(int(cap.get("money", 0)), 0, _MAX_PURSE_COINS)
		ag["ship_condition"] = clampi(
			int(cap.get("ship_condition", _SHIP_CONDITION_MAX)),
			_SHIP_CONDITION_MIN,
			_SHIP_CONDITION_MAX,
		)


## While purse cannot cover today's officer wage (due after docked trade), sell hold to the port at the current bid (no memory-edge gate; non-staples before grain/wine).
## With an empty hold and still short, captains must fire-sale a hull (each pass) until solvent or down to one ship.
func _npc_fire_sale_for_cashflow_docked(port_id: String, agent: Dictionary) -> void:
	_ensure_npc_ship_fields(agent)
	if not agent.has("cargo") or typeof(agent.get("cargo")) != TYPE_DICTIONARY:
		agent["cargo"] = {}
	var rounds: int = 0
	while rounds < 512:
		rounds += 1
		var ships: int = clampi(int(agent.get("fleet_ships", 1)), 1, _FLEET_MAX_SHIPS)
		var need_purse: int = _npc_officer_due_coins(agent)
		var purse: int = clampi(int(agent.get("money", 0)), 0, _MAX_PURSE_COINS)
		if purse >= need_purse:
			return
		var cargo: Dictionary = agent["cargo"] as Dictionary
		var progressed: bool = false
		if _npc_cargo_total_units(agent) > 0:
			for pass_i in range(2):
				for gk in _goods.keys():
					var gid: String = str(gk)
					var staple: bool = gid == "grain" or gid == "wine"
					if pass_i == 0 and staple:
						continue
					if pass_i == 1 and not staple:
						continue
					if _npc_cargo_qty(cargo, gid) <= 0:
						continue
					if _npc_effective_sell_unit(agent, port_id, gid) <= 0:
						continue
					var have: int = _npc_cargo_qty(cargo, gid)
					var chunk: int = mini(have, 24)
					_npc_sell_to_port(agent, port_id, gid, chunk)
					progressed = true
					break
				if progressed:
					break
		if progressed:
			continue
		if ships > 1 and _npc_try_fire_sale_one_hull_if_desperate(port_id, agent):
			continue
		return


## If purse is thin while in port, unload one hold unit so captains are not coin-stuck (no piracy model).
func _npc_liquidate_one_unit_if_dust_docked(port_id: String, agent: Dictionary) -> void:
	var dust_need: int = _npc_dock_dust_purse_floor(agent)
	for _i in range(_NPC_DOCK_DUST_MAX_UNITS):
		var purse: int = clampi(int(agent.get("money", 0)), 0, _MAX_PURSE_COINS)
		if purse >= dust_need:
			return
		var cr: Variant = agent.get("cargo", null)
		if typeof(cr) != TYPE_DICTIONARY:
			return
		var cargo: Dictionary = cr as Dictionary
		var sold: bool = false
		for gk in cargo.keys():
			var gid: String = str(gk)
			if not _goods.has(gid):
				continue
			if _npc_cargo_qty(cargo, gid) <= 0:
				continue
			_npc_sell_to_port(agent, port_id, gid, 1)
			sold = true
			break
		if not sold:
			var sh: int = clampi(int(agent.get("fleet_ships", 1)), 1, _FLEET_MAX_SHIPS)
			var need_off: int = _npc_officer_due_coins(agent)
			var thin_purse: bool = purse < maxi(need_off, dust_need)
			if (
				sh > 1
				and thin_purse
				and _npc_cargo_total_units(agent) == 0
				and _npc_try_fire_sale_one_hull_if_desperate(port_id, agent)
			):
				continue
			return


## After trades, solvent captains may still list a hull (timid trim, large fleet, or flush purse) — same slip mechanic as forced sales.
func _npc_maybe_voluntary_hull_fire_sale_if_docked(port_id: String, agent: Dictionary) -> void:
	_ensure_npc_ship_fields(agent)
	var ships: int = clampi(int(agent.get("fleet_ships", 1)), 1, _FLEET_MAX_SHIPS)
	if ships <= 1:
		return
	var need_purse: int = _npc_officer_due_coins(agent)
	var purse: int = clampi(int(agent.get("money", 0)), 0, _MAX_PURSE_COINS)
	if purse < need_purse:
		return
	var per_h2: int = clampi(int(_npc_ship_row(agent).get("cargo_per_hull", _FLEET_CARGO_PER_SHIP)), 1, 120)
	var new_cap: int = per_h2 * (ships - 1)
	if _npc_cargo_effective_used_units(agent) > new_cap:
		return
	_ensure_npc_risk_aversion(agent)
	var ra: float = clampf(float(agent.get("risk_aversion", 0.5)), 0.0, 1.0)
	var p_vol: float = 0.0
	if ships >= 4:
		p_vol += 0.034
	if ships >= 3 and ra > 0.62:
		p_vol += 0.042
	if ships >= 3 and purse >= need_purse + 320:
		p_vol += 0.022
	p_vol = clampf(p_vol, 0.0, 0.11)
	var n_big: float = _npc_trait_f(agent, _NPC_TRAIT_NEURO)
	var c_big: float = _npc_trait_f(agent, _NPC_TRAIT_CONSC)
	p_vol *= 1.0 + 0.24 * maxf(0.0, n_big - 0.45)
	p_vol *= 1.0 - 0.20 * maxf(0.0, c_big - 0.55) * (1.0 - n_big)
	p_vol = clampf(p_vol, 0.0, 0.14)
	if _rng.randf() >= p_vol:
		return
	_npc_try_fire_sale_one_hull_if_desperate(port_id, agent)


## Docked merchants may queue a new hull (labor + local timber/textiles/metal; ~3 months).
func _npc_try_expand_fleet_if_docked(agent: Dictionary) -> void:
	if int(agent.get("voyage_days_remaining", 0)) != 0:
		return
	var pid: String = str(agent.get("docked_port", ""))
	if pid.is_empty() or not _port_names.has(pid):
		return
	_ensure_npc_ship_fields(agent)
	if int(agent.get("fleet_shipyard_days", 0)) > 0:
		return
	if not _fleet_new_build_goods_present():
		return
	var ships: int = clampi(int(agent.get("fleet_ships", 1)), 1, _FLEET_MAX_SHIPS)
	if ships >= _FLEET_MAX_SHIPS:
		return
	var nb: Dictionary = _npc_fleet_build_ints(agent)
	var labor_n: int = int(nb.get("labor", _FLEET_NEW_SHIP_LABOR_COINS))
	var timb_n: int = int(nb.get("timber", _FLEET_NEW_SHIP_TIMBER))
	var tex_n: int = int(nb.get("textiles", _FLEET_NEW_SHIP_TEXTILES))
	var met_n: int = int(nb.get("metal", _FLEET_NEW_SHIP_METAL))
	var day_n: int = int(nb.get("days", _FLEET_NEW_SHIP_BUILD_DAYS))
	var purse: int = clampi(int(agent.get("money", 0)), 0, _MAX_PURSE_COINS)
	var oph: int = maxi(1, int(_npc_ship_row(agent).get("officer_pay_per_hull", 1)))
	var culd: Dictionary = _npc_cultural_ops_scale(agent)
	var off_sc: float = float(oph) * float(culd.get("officer_scale", 1.0))
	var cushion: int = _NPC_PURSE_RESERVE + maxi(1, int(ceil(float(ships * _SHIP_OFFICER_PAY_DAILY * 2) * off_sc)))
	var need: int = labor_n + cushion
	if purse < need:
		return
	if _port_stock_qty(pid, "timber") < timb_n:
		return
	if _port_stock_qty(pid, "textiles") < tex_n:
		return
	if _port_stock_qty(pid, "metal") < met_n:
		return
	var excess: int = purse - need
	var p_buy: float = clampf(0.13 + float(excess) / 4200.0, 0.09, 0.60)
	var c_exp: float = _npc_trait_f(agent, _NPC_TRAIT_CONSC)
	var n_exp: float = _npc_trait_f(agent, _NPC_TRAIT_NEURO)
	p_buy += 0.055 * (c_exp - 0.5) * (0.52 - n_exp)
	p_buy = clampf(p_buy, 0.08, 0.68)
	if _rng.randf() > p_buy:
		return
	agent["money"] = clampi(purse - labor_n, 0, _MAX_PURSE_COINS)
	_adjust_port_stock(pid, "timber", -timb_n)
	_adjust_port_stock(pid, "textiles", -tex_n)
	_adjust_port_stock(pid, "metal", -met_n)
	agent["fleet_shipyard_port_id"] = pid
	agent["fleet_shipyard_days"] = day_n


func _npc_pick_trading_dest_any_port(agent: Dictionary, here: String) -> String:
	var rows: Array = []
	for pk in _port_names.keys():
		var ps: String = str(pk)
		if ps == here:
			continue
		var sc: float = _npc_voyage_dest_score(agent, here, ps)
		rows.append({"id": ps, "sc": sc})
	if rows.is_empty():
		return ""
	rows.sort_custom(func(a: Dictionary, b: Dictionary) -> bool: return float(a["sc"]) > float(b["sc"]))
	var pick_n: int = mini(3, rows.size())
	var idx: int = _rng.randi_range(0, pick_n - 1)
	return str((rows[idx] as Dictionary).get("id", ""))


func _run_daily_population_and_npcs() -> void:
	_last_crop_rumor_ui_line = ""
	_last_pop_digest.clear()
	_last_grain_spoilage.clear()
	_last_war_industry_digest.clear()
	_last_industrial_sink_digest.clear()
	_last_slave_digest.clear()
	_reset_port_commerce_tick()
	for pid in _port_names.keys():
		_port_harbour_due_coins_tick[str(pid)] = 0
	_agent_information_decay_tick()
	_npc_tick_scatter_memory_decay()
	_ensure_sim_agent_port_defaults()
	for pid in _port_names.keys():
		var ps := str(pid)
		_wealth_snapshot_tick_start[ps] = int(_port_wealth.get(ps, 0))
		_wealth_stock_target_tick_start[ps] = _wealth_stock_target_for_port(ps)
	_tick_all_npc_captain_ship_costs()
	_tick_npc_storms_at_sea()
	_npc_pirate_encounters_tick()
	_npc_advance_voyages()
	_tick_player_fleet_shipyard_order()
	_tick_npc_fleet_shipyard_orders()
	_tick_port_crop_agro()
	_refresh_port_local_crop_beliefs()
	_tick_crop_rumor_events_phase4()
	_agent_production_tick_farms_mines_slaves()
	for pid in _port_names.keys():
		_refresh_port_wealth(str(pid))
	var doy_pop: int = get_calendar_day_of_year()
	var forage_today: int = _summer_forage_mouths_for_doy(doy_pop)
	for pid in _port_names.keys():
		var pid_s := str(pid)
		var eat: int = get_population_grain_eat_effective(pid_s)
		var ghave: int = _port_stock_qty(pid_s, "grain") if _goods.has("grain") else 0
		var food_days_pre: float = 9999.0
		if eat > 0:
			food_days_pre = float(ghave) / float(eat)
		var rationing: bool = bool(_port_rationing_active.get(pid_s, false))
		var rationing_days: int = clampi(int(_port_rationing_days_active.get(pid_s, 0)), 0, 999)
		if rationing:
			rationing_days = mini(999, rationing_days + 1)
			if food_days_pre > _RATION_END_FOOD_DAYS or rationing_days > _RATION_MAX_DAYS:
				rationing = false
				rationing_days = 0
		elif eat > 0 and food_days_pre < _RATION_TRIGGER_FOOD_DAYS:
			rationing = true
			rationing_days = 1
		_port_rationing_active[pid_s] = rationing
		_port_rationing_days_active[pid_s] = rationing_days
		var eat_today: int = eat
		if rationing and eat > 0:
			eat_today = mini(eat, maxi(_RATION_BITE_MIN, int(round(float(eat) * _RATION_BITE_FRAC))))
		var eaten_g: int = 0
		if eat_today > 0 and _goods.has("grain"):
			eaten_g = mini(eat_today, ghave)
			if eaten_g > 0:
				_adjust_port_stock(pid_s, "grain", -eaten_g)
		var preserved_used: int = 0
		var shortfall: int = maxi(0, eat - eaten_g)
		if shortfall > 0:
			var avail_p: float = float(_port_preserved_food.get(pid_s, 0.0))
			if avail_p >= 1.0:
				var take: int = mini(shortfall, int(floor(avail_p)))
				if take > 0:
					preserved_used = take
					_port_preserved_food[pid_s] = avail_p - float(take)
		if rationing:
			var u_now: int = clampi(int(_port_food_unrest.get(pid_s, 0)), 0, 200)
			_port_food_unrest[pid_s] = clampi(u_now + _RATION_UNREST_TICK, 0, 200)
		if eat > 0 and food_days_pre >= _PRESERVED_FOOD_FILL_FOODDAYS_MIN:
			var cur_p: float = float(_port_preserved_food.get(pid_s, 0.0))
			var cap_p: float = float(_preserved_food_cap_for_port(pid_s))
			if cur_p < cap_p:
				_port_preserved_food[pid_s] = clampf(cur_p + _PRESERVED_FOOD_FILL_PER_DAY, 0.0, cap_p)
		var eaten_w: int = 0
		if _goods.has("wine"):
			var w_base: int = int(_port_population_wine_base.get(pid_s, 1))
			var wealth: int = int(_port_wealth.get(pid_s, 100))
			var w_extra: int = clampi(int(float(wealth) / 95.0), 0, 14)
			var want_w: int = clampi(w_base + w_extra, 0, 50)
			var whave: int = _port_stock_qty(pid_s, "wine")
			eaten_w = mini(want_w, whave)
			if eaten_w > 0:
				_adjust_port_stock(pid_s, "wine", -eaten_w)
		var eaten_f: int = 0
		if _goods.has("fish"):
			var want_f: int = clampi(int(_port_population_fish_per_day.get(pid_s, 0)), 0, 40)
			if want_f > 0:
				var fhave: int = _port_stock_qty(pid_s, "fish")
				eaten_f = mini(want_f, fhave)
				if eaten_f > 0:
					_adjust_port_stock(pid_s, "fish", -eaten_f)
		_last_pop_digest[pid_s] = {
			"grain": eaten_g,
			"wine": eaten_w,
			"fish": eaten_f,
			"preserved": preserved_used,
			"forage": forage_today,
			"rationing": 1 if rationing else 0,
		}
	_agent_industry_and_war_materiel_tick()
	_replenish_wine_vineyards_after_bites()
	for item in _npc_agents:
		if typeof(item) != TYPE_DICTIONARY:
			continue
		_npc_trade_if_docked(item as Dictionary)
	_npc_try_peer_loans_after_dock_trade()
	_npc_docked_toll_graft_tick()
	_npc_apply_harbour_dues_if_docked_after_trade()
	_npc_apply_officer_pay_if_docked_after_trade()
	_npc_merchant_seasoned_mastery_tick()
	_npc_tick_merchant_city_contracts_docked()
	for item in _npc_agents:
		if typeof(item) != TYPE_DICTIONARY:
			continue
		_npc_try_buy_used_hull_if_docked(item as Dictionary)
	for item in _npc_agents:
		if typeof(item) != TYPE_DICTIONARY:
			continue
		_npc_try_expand_fleet_if_docked(item as Dictionary)
	_npc_convoy_formation_and_depart_tick()
	_npc_pirate_spawn_docked_tick()
	_npc_pirate_dock_depart_tick()
	_agent_information_post_trade_tick()
	_agent_merchant_cartel_tick()
	_agent_city_commerce_pulse_tick()
	_luxury_import_tick()
	_apply_granary_spoilage()
	_npc_cull_bankrupts()
	_finalize_daily_grain_food_days_and_unrest()
	_agent_war_tick_end_of_day()
	_tick_population_demographics()
	_agent_merchant_sync_home_counts_to_pulse()
	for pid in _port_names.keys():
		var ps := str(pid)
		var g0: int = clampi(int(_port_peace_riot_grace_days.get(ps, 0)), 0, 999)
		if g0 > 0:
			_port_peace_riot_grace_days[ps] = g0 - 1


func _init_port_food_unrest_zero() -> void:
	_port_food_unrest.clear()
	_port_peace_riot_grace_days.clear()
	for pid in _port_names.keys():
		_port_food_unrest[str(pid)] = 0


func _serialize_port_war_days_remaining() -> Dictionary:
	var out: Dictionary = {}
	for pid in _port_names.keys():
		var ps := str(pid)
		out[ps] = clampi(int(_port_war_days_remaining.get(ps, 0)), 0, 999)
	return out


func _deserialize_port_war_days_remaining(data: Dictionary) -> void:
	_port_war_days_remaining.clear()
	for pk in data.keys():
		var pid := str(pk)
		if not _port_names.has(pid):
			continue
		_port_war_days_remaining[pid] = clampi(int(data[pk]), 0, 999)
	_ensure_war_days_defaults()


func _migrate_save_v7_war_to_remaining(d: Dictionary) -> void:
	_port_war_days_remaining.clear()
	var aw: Variant = d.get("port_at_war", null)
	var awd: Dictionary = {}
	if typeof(aw) == TYPE_DICTIONARY:
		awd = aw as Dictionary
	for pid in _port_names.keys():
		var ps := str(pid)
		var was: bool = false
		if awd.has(ps):
			var raw: Variant = awd[ps]
			if typeof(raw) == TYPE_BOOL:
				was = bool(raw)
			else:
				was = int(raw) != 0
		_port_war_days_remaining[ps] = _WAR_MIGRATE_V7_REMAINING_DAYS if was else 0
	_ensure_war_days_defaults()


func _ensure_war_days_defaults() -> void:
	for pid in _port_names.keys():
		var ps := str(pid)
		if not _port_war_days_remaining.has(ps):
			_port_war_days_remaining[ps] = 0


func _ensure_war_recurring_defaults() -> void:
	for pid in _port_names.keys():
		var ps := str(pid)
		if not _port_war_recurring.has(ps):
			_port_war_recurring[ps] = false


func _ensure_war_peace_defaults() -> void:
	for pid in _port_names.keys():
		var ps := str(pid)
		if not _port_war_peace_remaining.has(ps):
			_port_war_peace_remaining[ps] = 0


func _bootstrap_recurring_war_timers() -> void:
	for pid in _port_names.keys():
		var ps := str(pid)
		if not bool(_port_war_recurring.get(ps, false)):
			continue
		if get_port_war_days_remaining(ps) > 0:
			continue
		if int(_port_war_peace_remaining.get(ps, 0)) > 0:
			continue
		_port_war_peace_remaining[ps] = _rng.randi_range(_WAR_CYCLE_PEACE_MIN, _WAR_CYCLE_PEACE_MAX)


func _serialize_port_war_recurring() -> Dictionary:
	var out: Dictionary = {}
	for pid in _port_names.keys():
		var ps := str(pid)
		out[ps] = 1 if bool(_port_war_recurring.get(ps, false)) else 0
	return out


func _deserialize_port_war_recurring(data: Dictionary) -> void:
	_port_war_recurring.clear()
	for pk in data.keys():
		var pid := str(pk)
		if not _port_names.has(pid):
			continue
		var raw: Variant = data[pk]
		var on: bool = bool(raw) if typeof(raw) == TYPE_BOOL else int(raw) != 0
		_port_war_recurring[pid] = on
	_ensure_war_recurring_defaults()


func _serialize_port_war_peace_remaining() -> Dictionary:
	var out: Dictionary = {}
	for pid in _port_names.keys():
		var ps := str(pid)
		out[ps] = clampi(int(_port_war_peace_remaining.get(ps, 0)), 0, 999)
	return out


func _deserialize_port_war_peace_remaining(data: Dictionary) -> void:
	_port_war_peace_remaining.clear()
	for pk in data.keys():
		var pid := str(pk)
		if not _port_names.has(pid):
			continue
		_port_war_peace_remaining[pid] = clampi(int(data[pk]), 0, 999)
	_ensure_war_peace_defaults()


func _serialize_port_war_burst_initial() -> Dictionary:
	var out: Dictionary = {}
	for pid in _port_names.keys():
		var ps := str(pid)
		var v: int = clampi(int(_port_war_burst_initial.get(ps, 0)), 0, 999)
		if v > 0:
			out[ps] = v
	return out


func _deserialize_port_war_burst_initial(data: Dictionary) -> void:
	_port_war_burst_initial.clear()
	for pk in data.keys():
		var pid := str(pk)
		if not _port_names.has(pid):
			continue
		_port_war_burst_initial[pid] = clampi(int(data[pk]), 0, 999)
	_ensure_war_burst_initial_defaults()


func _ensure_war_burst_initial_defaults() -> void:
	for pid in _port_names.keys():
		_ensure_war_burst_initial_for_port(str(pid))


func _ensure_war_burst_initial_for_port(ps: String) -> void:
	if get_port_war_days_remaining(ps) <= 0:
		_port_war_burst_initial.erase(ps)
		return
	var cur: int = int(_port_war_burst_initial.get(ps, 0))
	if cur <= 0:
		_port_war_burst_initial[ps] = maxi(1, get_port_war_days_remaining(ps))


func _tick_war_countdown() -> void:
	var ended: bool = false
	for pid in _port_names.keys():
		var ps := str(pid)
		var r: int = clampi(int(_port_war_days_remaining.get(ps, 0)), 0, 999)
		if r <= 0:
			continue
		var burst_len: int = maxi(1, int(_port_war_burst_initial.get(ps, r)))
		r -= 1
		_port_war_days_remaining[ps] = r
		if r == 0:
			_grant_war_slave_captives(ps, burst_len)
			ended = true
			_port_war_burst_initial.erase(ps)
			if bool(_port_war_recurring.get(ps, false)):
				_port_war_peace_remaining[ps] = _rng.randi_range(_WAR_CYCLE_PEACE_MIN, _WAR_CYCLE_PEACE_MAX)
			var u0: int = clampi(int(_port_food_unrest.get(ps, 0)), 0, 200)
			_port_food_unrest[ps] = maxi(0, u0 - _WAR_PEACE_FOOD_UNREST_VENT)
			_port_peace_riot_grace_days[ps] = _WAR_PEACE_RIOT_GRACE_DAYS
	if ended:
		market_changed.emit()


func _tick_war_recurring_peace() -> void:
	var started: bool = false
	var doy: int = _calendar_doy_1based(current_day)
	for pid in _port_names.keys():
		var ps := str(pid)
		if not bool(_port_war_recurring.get(ps, false)):
			continue
		if get_port_war_days_remaining(ps) > 0:
			continue
		var pend: int = clampi(int(_port_war_pending_burst.get(ps, 0)), 0, 999)
		if pend > 0 and _season_is_summer_for_war(doy):
			_port_war_days_remaining[ps] = pend
			_port_war_burst_initial[ps] = pend
			_port_war_pending_burst.erase(ps)
			started = true
			continue
		var pr: int = clampi(int(_port_war_peace_remaining.get(ps, 0)), 0, 999)
		if pr <= 0:
			continue
		var nxt: int = pr - 1
		_port_war_peace_remaining[ps] = nxt
		if nxt == 0:
			var burst: int = _rng.randi_range(_WAR_RECURRING_BURST_MIN, _WAR_RECURRING_BURST_MAX)
			if _season_is_summer_for_war(doy):
				_port_war_days_remaining[ps] = burst
				_port_war_burst_initial[ps] = burst
			else:
				_port_war_pending_burst[ps] = burst
			started = true
	if started:
		market_changed.emit()


func _serialize_port_food_unrest() -> Dictionary:
	var out: Dictionary = {}
	for k in _port_food_unrest.keys():
		out[str(k)] = clampi(int(_port_food_unrest[k]), 0, 200)
	return out


func _deserialize_port_food_unrest(data: Dictionary) -> void:
	_port_food_unrest.clear()
	for pk in data.keys():
		var pid := str(pk)
		if not _port_names.has(pid):
			continue
		_port_food_unrest[pid] = clampi(int(data[pk]), 0, 200)
	for pid in _port_names.keys():
		var ps := str(pid)
		if not _port_food_unrest.has(ps):
			_port_food_unrest[ps] = 0


func _serialize_port_population_grain() -> Dictionary:
	var out: Dictionary = {}
	for pid in _port_names.keys():
		out[str(pid)] = clampi(int(_port_population_grain.get(str(pid), 0)), 0, 120)
	return out


func _deserialize_port_population_grain(data: Dictionary) -> void:
	for pk in data.keys():
		var pid := str(pk)
		if not _port_names.has(pid):
			continue
		_port_population_grain[pid] = clampi(int(data[pk]), _POP_GRAIN_FLOOR, 120)


func _serialize_port_population_wine_base() -> Dictionary:
	var out: Dictionary = {}
	for pid in _port_names.keys():
		out[str(pid)] = clampi(int(_port_population_wine_base.get(str(pid), 1)), 0, 40)
	return out


func _deserialize_port_population_wine_base(data: Dictionary) -> void:
	for pk in data.keys():
		var pid := str(pk)
		if not _port_names.has(pid):
			continue
		_port_population_wine_base[pid] = clampi(int(data[pk]), 0, 40)


func _serialize_port_population_grain_baseline() -> Dictionary:
	var out: Dictionary = {}
	for pid in _port_names.keys():
		out[str(pid)] = clampi(int(_port_population_grain_baseline.get(str(pid), 1)), 1, 120)
	return out


func _deserialize_port_population_grain_baseline(data: Dictionary) -> void:
	for pk in data.keys():
		var pid := str(pk)
		if not _port_names.has(pid):
			continue
		_port_population_grain_baseline[pid] = clampi(int(data[pk]), 1, 120)


func _serialize_port_population_grain_cap() -> Dictionary:
	var out: Dictionary = {}
	for pid in _port_names.keys():
		out[str(pid)] = clampi(int(_port_population_grain_cap.get(str(pid), 40)), 1, 120)
	return out


func _deserialize_port_population_grain_cap(data: Dictionary) -> void:
	for pk in data.keys():
		var pid := str(pk)
		if not _port_names.has(pid):
			continue
		_port_population_grain_cap[pid] = clampi(int(data[pk]), 1, 120)


func _serialize_port_famine_streak_days() -> Dictionary:
	var out: Dictionary = {}
	for pid in _port_names.keys():
		out[str(pid)] = clampi(int(_port_famine_streak_days.get(str(pid), 0)), 0, 999)
	return out


func _deserialize_port_famine_streak_days(data: Dictionary) -> void:
	for pk in data.keys():
		var pid := str(pk)
		if not _port_names.has(pid):
			continue
		_port_famine_streak_days[pid] = clampi(int(data[pk]), 0, 999)


func _serialize_port_prosperity_streak_days() -> Dictionary:
	var out: Dictionary = {}
	for pid in _port_names.keys():
		out[str(pid)] = clampi(int(_port_prosperity_streak_days.get(str(pid), 0)), 0, 999)
	return out


func _deserialize_port_prosperity_streak_days(data: Dictionary) -> void:
	for pk in data.keys():
		var pid := str(pk)
		if not _port_names.has(pid):
			continue
		_port_prosperity_streak_days[pid] = clampi(int(data[pk]), 0, 999)


func _serialize_port_rationing_active() -> Dictionary:
	var out: Dictionary = {}
	for pid in _port_names.keys():
		out[str(pid)] = 1 if bool(_port_rationing_active.get(str(pid), false)) else 0
	return out


func _deserialize_port_rationing_active(data: Dictionary) -> void:
	for pk in data.keys():
		var pid := str(pk)
		if not _port_names.has(pid):
			continue
		_port_rationing_active[pid] = int(data[pk]) != 0


func _deserialize_port_preserved_food(data: Dictionary) -> void:
	for pk in data.keys():
		var pid := str(pk)
		if not _port_names.has(pid):
			continue
		var cap_p: float = float(_preserved_food_cap_for_port(pid))
		_port_preserved_food[pid] = clampf(float(data[pk]), 0.0, cap_p)


func _ensure_port_demographics_post_load() -> void:
	for pid in _port_names.keys():
		var ps := str(pid)
		var p0: int = clampi(int(_port_population_grain.get(ps, 0)), 0, 120)
		if p0 < _POP_GRAIN_FLOOR:
			p0 = _POP_GRAIN_FLOOR
			_port_population_grain[ps] = p0
		if not _port_population_grain_baseline.has(ps) or int(_port_population_grain_baseline.get(ps, 0)) < 1:
			_port_population_grain_baseline[ps] = maxi(1, p0)
		if not _port_population_grain_cap.has(ps):
			_port_population_grain_cap[ps] = mini(120, maxi(p0 + _POP_GRAIN_CEILING_BOOST, int(ceil(float(p0) * 1.48))))
		if not _port_famine_streak_days.has(ps):
			_port_famine_streak_days[ps] = 0
		if not _port_consecutive_grain_full_ration_days.has(ps):
			_port_consecutive_grain_full_ration_days[ps] = 0
		if not _port_consecutive_grain_zero_eat_days.has(ps):
			_port_consecutive_grain_zero_eat_days[ps] = 0
		if not _port_prosperity_streak_days.has(ps):
			_port_prosperity_streak_days[ps] = 0
		if not _port_population_fish_per_day.has(ps):
			_port_population_fish_per_day[ps] = 0
		if not _port_rationing_active.has(ps):
			_port_rationing_active[ps] = false
		if not _port_rationing_days_active.has(ps):
			_port_rationing_days_active[ps] = 0
		if not _port_baseline_momentum_up.has(ps):
			_port_baseline_momentum_up[ps] = 0
		if not _port_baseline_momentum_dn.has(ps):
			_port_baseline_momentum_dn[ps] = 0
		if not _port_preserved_food.has(ps):
			var cap_p: float = float(_preserved_food_cap_for_port(ps))
			_port_preserved_food[ps] = cap_p * _PRESERVED_FOOD_INITIAL_FRAC
		var capv: int = clampi(int(_port_population_grain_cap.get(ps, 120)), 1, 120)
		if capv < p0:
			_port_population_grain_cap[ps] = mini(120, p0 + _POP_GRAIN_CEILING_BOOST)


## Port grain stock ÷ configured population grain demand (no grain good → huge sentinel).
func get_grain_food_days_for_port(port_id: String) -> float:
	if not _goods.has("grain"):
		return 9999.0
	var ps := str(port_id)
	if not _port_names.has(ps):
		return 0.0
	var eat: int = get_population_grain_eat_effective(ps)
	if eat <= 0:
		return 9999.0
	return float(_port_stock_qty(ps, "grain")) / float(eat)


func get_port_food_unrest(port_id: String) -> int:
	var ps := str(port_id)
	if not _port_names.has(ps):
		return 0
	return clampi(int(_port_food_unrest.get(ps, 0)), 0, 200)


func _food_unrest_tier_label(unrest: int) -> String:
	var u: int = clampi(unrest, 0, 200)
	if u < 40:
		return "Calm"
	if u < 65:
		return "Uneasy"
	if u < 88:
		return "Tense"
	return "Critical"


func _init_port_demographics_from_world() -> void:
	for pid in _port_names.keys():
		var ps := str(pid)
		var p0: int = clampi(int(_port_population_grain.get(ps, 0)), 0, 120)
		if p0 < _POP_GRAIN_FLOOR:
			p0 = _POP_GRAIN_FLOOR
			_port_population_grain[ps] = p0
		_port_population_grain_baseline[ps] = maxi(1, p0)
		_port_population_grain_cap[ps] = mini(120, maxi(p0 + _POP_GRAIN_CEILING_BOOST, int(ceil(float(p0) * 1.48))))
		_port_famine_streak_days[ps] = 0
		_port_consecutive_grain_full_ration_days[ps] = 0
		_port_consecutive_grain_zero_eat_days[ps] = 0
		_port_prosperity_streak_days[ps] = 0
		_port_rationing_active[ps] = false
		_port_rationing_days_active[ps] = 0
		_port_baseline_momentum_up[ps] = 0
		_port_baseline_momentum_dn[ps] = 0
		var cap_pres: float = float(_preserved_food_cap_for_port(ps))
		_port_preserved_food[ps] = cap_pres * _PRESERVED_FOOD_INITIAL_FRAC


func _ensure_port_meal_streak_counters_post_load() -> void:
	for pid in _port_names.keys():
		var ps := str(pid)
		if not _port_consecutive_grain_full_ration_days.has(ps):
			_port_consecutive_grain_full_ration_days[ps] = 0
		if not _port_consecutive_grain_zero_eat_days.has(ps):
			_port_consecutive_grain_zero_eat_days[ps] = 0


## Per-port preserved-foods reserve cap (mouth-days). Scales with the founding cohort so
## larger cities have more "iron rations" warehoused. Sync tools/sim_100_days.py.
func _preserved_food_cap_for_port(port_id: String) -> int:
	var ps := str(port_id)
	var b: int = maxi(1, int(_port_population_grain_baseline.get(ps, 1)))
	return maxi(_PRESERVED_FOOD_CAP_MIN, b * _PRESERVED_FOOD_CAP_MULT)


## Minimum institutional baseline by port role (baseline cannot drift below this). Sync sim.
func _population_baseline_floor_for_port(port_id: String) -> int:
	var rl: String = str(_port_roles.get(str(port_id), ""))
	if rl == "metropole" or rl == "great_city":
		return 7
	if rl == "imperial_port":
		return 6
	if rl == "regional_capital" or rl == "breadbasket":
		return 5
	return _POP_GRAIN_FLOOR


func _recompute_population_grain_cap_for_port(port_id: String) -> void:
	var ps := str(port_id)
	if not _port_names.has(ps):
		return
	var base: int = clampi(int(_port_population_grain_baseline.get(ps, 1)), 1, 120)
	var popv: int = clampi(int(_port_population_grain.get(ps, 0)), 0, 120)
	var cap_calc: int = mini(120, maxi(base + _POP_GRAIN_CEILING_BOOST, int(ceil(float(base) * 1.48))))
	_port_population_grain_cap[ps] = mini(120, maxi(cap_calc, popv + 1))


## Siege / existential campaign: harsher famine cadence when this war’s burst is long enough (per-port threshold in world.json).
func _famine_streak_to_loss_for_port(port_id: String) -> int:
	var ps := str(port_id)
	var th: int = clampi(int(_port_existential_war_burst_days.get(ps, _POP_EXISTENTIAL_WAR_BURST_OFF)), 1, _POP_EXISTENTIAL_WAR_BURST_OFF)
	if th >= _POP_EXISTENTIAL_WAR_BURST_OFF:
		return _POP_FAMINE_STREAK_TO_LOSS
	if not is_port_at_war(ps):
		return _POP_FAMINE_STREAK_TO_LOSS
	var burst0: int = maxi(1, int(_port_war_burst_initial.get(ps, get_port_war_days_remaining(ps))))
	if burst0 < th:
		return _POP_FAMINE_STREAK_TO_LOSS
	return maxi(8, int(ceil(float(_POP_FAMINE_STREAK_TO_LOSS) * 0.5)))


## Summer foraging supplement (virtual mouths/day, never touches stock). Half-sine over
## the foraging window so May/June peaks taper into autumn. Sync tools/sim_100_days.py.
func _summer_forage_mouths_for_doy(doy: int) -> int:
	if doy < _FORAGE_SUMMER_START_DOY or doy > _FORAGE_SUMMER_END_DOY:
		return 0
	var width: float = float(_FORAGE_SUMMER_END_DOY - _FORAGE_SUMMER_START_DOY)
	if width <= 0.0:
		return 0
	var t: float = (float(doy) - float(_FORAGE_SUMMER_START_DOY)) / width
	var v: float = _FORAGE_SUMMER_PEAK_MOUTHS * sin(PI * t)
	return clampi(int(round(v)), 0, int(round(_FORAGE_SUMMER_PEAK_MOUTHS)))


func _population_output_scale_for_port(port_id: String) -> float:
	var ps := str(port_id)
	if not _port_names.has(ps):
		return 1.0
	var base: int = maxi(1, int(_port_population_grain_baseline.get(ps, 1)))
	var cur: int = maxi(1, clampi(int(_port_population_grain.get(ps, 0)), 0, 120))
	return clampf(float(cur) / float(base), _POP_OUTPUT_SCALE_MIN, _POP_OUTPUT_SCALE_MAX)


func _tick_population_demographics() -> void:
	if _port_names.is_empty():
		return
	var changed: bool = false
	for pid in _port_names.keys():
		var ps := str(pid)
		var eat0: int = clampi(int(_port_population_grain.get(ps, 0)), 0, 120)
		if eat0 < _POP_GRAIN_FLOOR:
			continue
		var fd: float = float(_last_grain_food_days.get(ps, 9999.0))
		var u: int = clampi(int(_port_food_unrest.get(ps, 0)), 0, 200)
		var eat_need: int = get_population_grain_eat_effective(ps)
		var dig: Variant = _last_pop_digest.get(ps, null)
		var eaten_eff: int = 0
		if typeof(dig) == TYPE_DICTIONARY:
			var dd: Dictionary = dig as Dictionary
			eaten_eff = int(dd.get("grain", 0)) + int(dd.get("preserved", 0)) + int(dd.get("forage", 0))
		var full_d: int = clampi(int(_port_consecutive_grain_full_ration_days.get(ps, 0)), 0, 999)
		var zero_d: int = clampi(int(_port_consecutive_grain_zero_eat_days.get(ps, 0)), 0, 999)
		if eat_need <= 0:
			full_d = 0
			zero_d = 0
		elif eaten_eff >= eat_need:
			full_d = mini(999, full_d + 1)
			zero_d = 0
		elif eaten_eff <= 0:
			zero_d = mini(999, zero_d + 1)
			full_d = 0
		else:
			full_d = 0
			zero_d = 0
		_port_consecutive_grain_full_ration_days[ps] = full_d
		_port_consecutive_grain_zero_eat_days[ps] = zero_d
		var base_ln: int = maxi(1, int(_port_population_grain_baseline.get(ps, 1)))
		if eat0 >= int(ceil(float(base_ln) * _POP_BASELINE_RISE_FRAC)) and fd >= 1.85 and u < 96:
			_port_baseline_momentum_up[ps] = mini(999, int(_port_baseline_momentum_up.get(ps, 0)) + 1)
			_port_baseline_momentum_dn[ps] = 0
		else:
			_port_baseline_momentum_up[ps] = 0
		if eat0 <= int(floor(float(base_ln) * _POP_BASELINE_FALL_FRAC)) and (u > 112 or zero_d >= 6):
			_port_baseline_momentum_dn[ps] = mini(999, int(_port_baseline_momentum_dn.get(ps, 0)) + 1)
		else:
			_port_baseline_momentum_dn[ps] = 0
		var harsh: bool = (
			(eat_need > 0 and zero_d >= _POP_FAMINE_HARSH_CONSEC_ZERO_GRAIN_DAYS)
			or u >= _POP_FAMINE_HARSH_UNREST_MIN
		)
		var calm: bool = (eat_need > 0 and full_d >= _POP_FAMINE_CALM_CONSEC_FULL_RATION_DAYS) and u < 38
		var fs: int = clampi(int(_port_famine_streak_days.get(ps, 0)), 0, 999)
		if harsh:
			fs = mini(999, fs + 1)
		elif calm:
			fs = 0
		else:
			fs = maxi(0, fs - 1)
		_port_famine_streak_days[ps] = fs
		var streak_need: int = _famine_streak_to_loss_for_port(ps)
		if fs >= streak_need and eat0 > _POP_GRAIN_FLOOR:
			_port_population_grain[ps] = eat0 - 1
			_port_famine_streak_days[ps] = _POP_FAMINE_STREAK_RESET
			changed = true
		eat0 = clampi(int(_port_population_grain.get(ps, 0)), 0, 120)
		base_ln = maxi(1, int(_port_population_grain_baseline.get(ps, 1)))
		if int(_port_baseline_momentum_up.get(ps, 0)) >= _POP_BASELINE_RISE_DAYS and base_ln < 120:
			_port_population_grain_baseline[ps] = base_ln + 1
			_port_baseline_momentum_up[ps] = 0
			_recompute_population_grain_cap_for_port(ps)
			changed = true
			base_ln = int(_port_population_grain_baseline.get(ps, 1))
		if int(_port_baseline_momentum_dn.get(ps, 0)) >= _POP_BASELINE_FALL_DAYS:
			var floor_b: int = _population_baseline_floor_for_port(ps)
			if base_ln > floor_b:
				_port_population_grain_baseline[ps] = base_ln - 1
				_port_baseline_momentum_dn[ps] = 0
				_recompute_population_grain_cap_for_port(ps)
				changed = true
				base_ln = int(_port_population_grain_baseline.get(ps, 1))
		var wv: int = int(_port_wealth.get(ps, 50))
		var att: int = _wealth_stock_target_for_port(ps)
		var pulse0: float = clampf(float(_port_commerce_pulse.get(ps, 0.38)), 0.0, 1.0)
		var commerce_poor: bool = (
			pulse0 < _COMMERCE_POOR_PULSE and float(wv) < float(maxi(1, att)) * 0.95
		)
		var wealthy: bool = float(wv) > float(maxi(1, att)) * 1.04 and fd >= 2.4 and u < 65
		var poor: bool = (
			float(wv) < float(maxi(1, att)) * 0.92
			or fd < 1.5
			or u > _POP_PROSPERITY_POOR_UNREST_EXCEEDS
			or commerce_poor
		)
		var psr: int = clampi(int(_port_prosperity_streak_days.get(ps, 0)), 0, 999)
		if wealthy:
			var inc: int = 1
			var baseline_eat: int = maxi(1, int(_port_population_grain_baseline.get(ps, 1)))
			if eat0 < baseline_eat:
				var gap_frac: float = float(baseline_eat - eat0) / float(baseline_eat)
				inc += int(floor(gap_frac * float(_POP_MIGRATION_PULL)))
			psr = mini(999, psr + inc)
		elif poor:
			psr = maxi(0, psr - _POP_PROSPERITY_POOR_DECAY)
		else:
			psr = maxi(0, psr - 1)
		_port_prosperity_streak_days[ps] = psr
		var cap: int = clampi(int(_port_population_grain_cap.get(ps, eat0 + 20)), eat0, 120)
		if psr >= _POP_PROSPERITY_STREAK_TO_GAIN and eat0 < cap:
			_port_population_grain[ps] = eat0 + 1
			_port_prosperity_streak_days[ps] = _POP_PROSPERITY_STREAK_RESET
			if _rng.randf() < 0.35:
				var wb: int = clampi(int(_port_population_wine_base.get(ps, 1)), 1, 40)
				if wb < 40:
					_port_population_wine_base[ps] = wb + 1
			changed = true
		var plg: int = clampi(int(_port_plague_days.get(ps, 0)), 0, 999)
		if plg == 0 and eat0 >= _POP_GRAIN_FLOOR and u > 155 and fd < 0.45 and _rng.randf() < 0.0005:
			_port_plague_days[ps] = _rng.randi_range(9, 16)
			plg = int(_port_plague_days[ps])
		if plg > 0:
			var eatp: int = clampi(int(_port_population_grain.get(ps, 0)), 0, 120)
			if eatp > _POP_GRAIN_FLOOR and _rng.randf() < 0.085:
				_port_population_grain[ps] = eatp - 1
				changed = true
			_port_plague_days[ps] = maxi(0, plg - 1)
	if changed:
		market_changed.emit()


func _food_riot_threshold_for_port(port_id: String) -> int:
	var ps := str(port_id)
	if not _goods.has("grain"):
		return _FOOD_RIOT_THRESHOLD
	if is_port_at_war(ps):
		var burst0: int = maxi(1, int(_port_war_burst_initial.get(ps, get_port_war_days_remaining(ps))))
		var rem: int = get_port_war_days_remaining(ps)
		var elapsed: int = maxi(0, burst0 - rem)
		var bonus: int = clampi(_WAR_RIOT_GRACE_EXTRA - elapsed, 0, _WAR_RIOT_GRACE_EXTRA)
		return _FOOD_RIOT_THRESHOLD + bonus
	var gr: int = clampi(int(_port_peace_riot_grace_days.get(ps, 0)), 0, 999)
	if gr > 0:
		return _FOOD_RIOT_THRESHOLD + _WAR_PEACE_RIOT_THRESHOLD_BONUS
	return _FOOD_RIOT_THRESHOLD


func _war_panic_mult_for_port(port_id: String) -> float:
	var ps := str(port_id)
	if not is_port_at_war(ps):
		return 1.0
	var burst0: int = maxi(1, int(_port_war_burst_initial.get(ps, get_port_war_days_remaining(ps))))
	var elapsed: int = maxi(0, burst0 - get_port_war_days_remaining(ps))
	return minf(1.0, float(elapsed) / float(_WAR_RIOT_PANIC_RAMP_DAYS))


func _finalize_daily_grain_food_days_and_unrest() -> void:
	_last_food_riot_summary = ""
	if not _goods.has("grain"):
		_last_grain_food_days.clear()
		return
	var riot_lines: PackedStringArray = []
	for pid in _port_names.keys():
		var ps := str(pid)
		var eat: int = get_population_grain_eat_effective(ps)
		if eat <= 0:
			_last_grain_food_days[ps] = 9999.0
			continue
		var gstock: int = _port_stock_qty(ps, "grain")
		var days_r: float = float(gstock) / float(eat)
		_last_grain_food_days[ps] = days_r
		var base_eat: int = clampi(int(_port_population_grain.get(ps, 0)), 0, 120)
		var days_panic: float = days_r
		if is_port_at_war(ps) and base_eat > 0:
			days_panic = float(gstock) / float(base_eat)
		var u: int = clampi(int(_port_food_unrest.get(ps, 0)), 0, 200)
		var dig: Variant = _last_pop_digest.get(ps, null)
		var eaten_g: int = 0
		if typeof(dig) == TYPE_DICTIONARY:
			eaten_g = int((dig as Dictionary).get("grain", 0))
		if eaten_g >= eat:
			var tight_runway: bool = minf(days_panic, days_r) < _FOOD_UNREST_TIGHT_RUNWAY_DAYS
			var dec: int = _FOOD_UNREST_DECAY_WHEN_TIGHT if tight_runway else _FOOD_UNREST_DECAY
			u = maxi(0, u - dec)
		elif is_port_at_war(ps) and base_eat > 0 and eaten_g >= base_eat:
			var tight2: bool = minf(days_panic, days_r) < _FOOD_UNREST_TIGHT_RUNWAY_DAYS
			var dec2: int = _FOOD_UNREST_DECAY_WHEN_TIGHT if tight2 else _FOOD_UNREST_DECAY
			u = maxi(0, u - dec2)
			var gap: int = eat - eaten_g
			if gap > 0:
				u += gap * _FOOD_UNREST_WAR_RATION_GAP_PER
		else:
			u += _FOOD_UNREST_SHORTAGE + (eat - eaten_g) * _FOOD_UNREST_PER_MISS
		var pm: float = _war_panic_mult_for_port(ps)
		if days_panic < 1.0:
			u += int(round(float(_FOOD_UNREST_PANIC_LT1DAY) * (pm if is_port_at_war(ps) else 1.0)))
		if days_panic < 0.5:
			u += int(round(float(_FOOD_UNREST_CRITICAL_DAYS) * (pm if is_port_at_war(ps) else 1.0)))
		if minf(days_panic, days_r) < _FOOD_UNREST_TIGHT_RUNWAY_DAYS:
			u += _FOOD_UNREST_TIGHT_RUNWAY_DRIP
		if _world_crop_agro_model:
			u += _crop_phase2_food_unrest_addon(ps)
		u = clampi(u, 0, 200)
		var riot_thr: int = _food_riot_threshold_for_port(ps)
		# Grain riot: missed ration today AND worst closing runway still tiny (post-trade/spoil; war uses civilian draw too).
		var runway_worst: float = minf(days_panic, days_r)
		var famine_riot_eligible: bool = eaten_g < eat and runway_worst < _FOOD_RIOT_ELIGIBLE_RUNWAY_MAX
		if u >= riot_thr:
			if famine_riot_eligible:
				var p_riot: float = minf(1.0, _FOOD_RIOT_ROLL_BASE + float(u - riot_thr) / _FOOD_RIOT_ROLL_PER_OVER)
				if _rng.randf() < p_riot:
					u = _apply_one_food_riot(ps, eat, u, riot_lines)
				else:
					u = clampi(u - _FOOD_RIOT_NEAR_MISS_VENT, 0, 200)
			else:
				u = clampi(u - _FOOD_RIOT_NO_FAMINE_VENT, 0, 200)
		_port_food_unrest[ps] = u
	if not riot_lines.is_empty():
		_last_food_riot_summary = "; ".join(riot_lines)
		food_riot_report.emit(_last_food_riot_summary)


func _apply_one_food_riot(port_id: String, eat: int, unrest: int, out_lines: PackedStringArray) -> int:
	var ps := port_id
	var cap_loot: int = eat * _rng.randi_range(2, 5) + _rng.randi_range(4, 18)
	var loot_g: int = mini(_port_stock_qty(ps, "grain"), cap_loot)
	if loot_g > 0:
		_adjust_port_stock(ps, "grain", -loot_g)
	var wine_l: int = 0
	if _goods.has("wine"):
		var sw: int = _port_stock_qty(ps, "wine")
		wine_l = mini(sw, _rng.randi_range(2, 10))
		if wine_l > 0:
			_adjust_port_stock(ps, "wine", -wine_l)
	var wv: int = int(_port_wealth.get(ps, 100))
	var smash: int = _rng.randi_range(35, 95)
	_port_wealth[ps] = clampi(wv - smash, 25, 999999)
	var wn: String = get_port_name(ps)
	var line: String = "%s food riot: ~%d grain" % [wn, loot_g]
	if wine_l > 0:
		line += ", %d wine" % wine_l
	line += " seized; prosperity −%d." % smash
	out_lines.append(line)
	market_changed.emit()
	return clampi(int(round(float(unrest) * _FOOD_RIOT_UNREST_SCALE)), 10, 62)


## Same trireme economics as the player: rations, wear, repair from at-sea / docked state before voyage advance. Officer pay runs after docked trade (`_npc_apply_officer_pay_if_docked_after_trade`).
func _tick_all_npc_captain_ship_costs() -> void:
	for item in _npc_agents:
		if typeof(item) != TYPE_DICTIONARY:
			continue
		var ag: Dictionary = item as Dictionary
		_ensure_npc_ship_fields(ag)
		var cr: Variant = ag.get("cargo", null)
		if typeof(cr) != TYPE_DICTIONARY:
			ag["cargo"] = {}
		var cargo_d: Dictionary = ag["cargo"] as Dictionary
		var days: int = int(ag.get("voyage_days_remaining", 0))
		var was_at_sea: bool = days > 0
		var docked_for_repair: bool = days <= 0
		var ships: int = clampi(int(ag.get("fleet_ships", 1)), 1, _FLEET_MAX_SHIPS)
		var srow: Dictionary = _npc_ship_row(ag)
		var culd: Dictionary = _npc_cultural_ops_scale(ag)
		var oph: int = maxi(1, int(srow.get("officer_pay_per_hull", 1)))
		var off_sc: float = float(oph) * float(culd.get("officer_scale", 1.0))
		var cap: Dictionary = {
			"money": clampi(int(ag.get("money", 0)), 0, _MAX_PURSE_COINS),
			"cargo": cargo_d,
			"ship_condition": int(ag.get("ship_condition", _SHIP_CONDITION_MAX)),
			"ship_wine_counter": int(ag.get("ship_wine_counter", 0)),
			"fleet_ships": ships,
			"crew_wine_per_ship": maxi(1, int(srow.get("crew_wine_per_ship", 1))),
			"crew_wine_cultural_scale": float(culd.get("wine_scale", 1.0)),
			"officer_pay_scale": off_sc,
			"repair_coin_mult": float(srow.get("repair_coin_mult", 1.0)),
		}
		_tick_captain_shared(cap, was_at_sea, docked_for_repair, false)
		ag["money"] = clampi(int(cap.get("money", 0)), 0, _MAX_PURSE_COINS)
		ag["ship_condition"] = clampi(int(cap.get("ship_condition", _SHIP_CONDITION_MAX)), _SHIP_CONDITION_MIN, _SHIP_CONDITION_MAX)
		ag["ship_wine_counter"] = clampi(int(cap.get("ship_wine_counter", 0)), 0, 9999)
		ag["fleet_ships"] = clampi(int(cap.get("fleet_ships", ships)), 1, _FLEET_MAX_SHIPS)


func _npc_cargo_total_units(agent: Dictionary) -> int:
	var cr: Variant = agent.get("cargo", null)
	if typeof(cr) != TYPE_DICTIONARY:
		return 0
	var cargo: Dictionary = cr as Dictionary
	var sumu: int = 0
	for gk in cargo.keys():
		sumu += maxi(0, int(cargo[gk]))
	return sumu


func _npc_cargo_effective_used_units(agent: Dictionary) -> int:
	var cr: Variant = agent.get("cargo", null)
	if typeof(cr) != TYPE_DICTIONARY:
		return 0
	var cargo: Dictionary = cr as Dictionary
	var row: Dictionary = _npc_ship_row(agent)
	var geff: float = maxf(0.5, float(row.get("grain_hold_efficiency", 1.0)))
	var sumu: int = 0
	for gk in cargo.keys():
		var gid: String = str(gk)
		var qv: int = maxi(0, int(cargo[gk]))
		if gid == "grain":
			sumu += int(ceil(float(qv) / geff))
		else:
			sumu += qv
	return sumu


func _npc_cargo_capacity_units(agent: Dictionary) -> int:
	_ensure_npc_ship_fields(agent)
	var row: Dictionary = _npc_ship_row(agent)
	var per: int = clampi(int(row.get("cargo_per_hull", _FLEET_CARGO_PER_SHIP)), 1, 120)
	return per * clampi(int(agent.get("fleet_ships", 1)), 1, _FLEET_MAX_SHIPS)


func _npc_cargo_free_space(agent: Dictionary) -> int:
	return maxi(0, _npc_cargo_capacity_units(agent) - _npc_cargo_effective_used_units(agent))


## Lot size for one wholesale action: blended risk (risk_aversion + neuroticism) 1 → small lots; 0 → up to full feasible cap (hold/stock/coins clamp in buy).
func _npc_roll_trade_lot_qty(agent: Dictionary, port_id: String, good_id: String, for_buy: bool) -> int:
	_ensure_npc_ship_fields(agent)
	var r: float = _npc_trade_effective_risk(agent)
	var cap: int = 0
	if for_buy:
		cap = mini(_npc_cargo_free_space(agent), _port_stock_qty(port_id, good_id))
	else:
		if not agent.has("cargo") or typeof(agent.get("cargo")) != TYPE_DICTIONARY:
			return 0
		cap = _npc_cargo_qty(agent["cargo"] as Dictionary, good_id)
	if cap <= 0:
		return 0
	var brav: float = 1.0 - r
	var tceil: int = mini(_NPC_RISK_AVERSE_MAX_LOT, cap)
	var hi: int = int(round(lerpf(float(tceil), float(cap), brav)))
	hi = clampi(hi, 1, cap)
	return _rng.randi_range(1, hi)


func _npc_merchant_seasoned_mastery_tick() -> void:
	for item in _npc_agents:
		if typeof(item) != TYPE_DICTIONARY:
			continue
		var ag: Dictionary = item as Dictionary
		if str(ag.get("voyage_role", _VOYAGE_ROLE_MERCHANT)) != _VOYAGE_ROLE_MERCHANT:
			continue
		_ensure_npc_ship_fields(ag)
		var purse: int = clampi(int(ag.get("money", 0)), 0, _MAX_PURSE_COINS)
		var cargo_u: int = _npc_cargo_total_units(ag)
		var ships: int = clampi(int(ag.get("fleet_ships", 1)), 1, _FLEET_MAX_SHIPS)
		var sea: int = int(ag.get("voyage_days_remaining", 0))
		var viable: bool = purse > 0 or cargo_u > 0 or ships > 1 or sea > 0
		if not viable:
			ag["merchant_season_ticks"] = 0
			continue
		var st: int = clampi(int(ag.get("merchant_season_ticks", 0)), 0, 999) + 1
		ag["merchant_season_ticks"] = st
		if st < _NPC_SEASON_MASTERY_DAYS:
			continue
		ag["merchant_season_ticks"] = 0
		var bm: float = clampf(float(ag.get("buy_mastery", 1.0)), _NPC_MASTER_MIN, _NPC_MASTER_MAX)
		var sm: float = clampf(float(ag.get("sell_mastery", 1.0)), _NPC_MASTER_MIN, _NPC_MASTER_MAX)
		if bm >= _NPC_MASTER_MAX - 0.001 and sm >= _NPC_MASTER_MAX - 0.001:
			continue
		if bm <= sm:
			ag["buy_mastery"] = clampf(bm + _NPC_SEASON_MASTERY_BUMP, _NPC_MASTER_MIN, _NPC_MASTER_MAX)
		else:
			ag["sell_mastery"] = clampf(sm + _NPC_SEASON_MASTERY_BUMP, _NPC_MASTER_MIN, _NPC_MASTER_MAX)


func _npc_cull_bankrupts() -> void:
	var i: int = 0
	while i < _npc_agents.size():
		var raw: Variant = _npc_agents[i]
		if typeof(raw) != TYPE_DICTIONARY:
			_npc_agents.remove_at(i)
			continue
		var ag: Dictionary = raw as Dictionary
		var purse: int = clampi(int(ag.get("money", 0)), 0, _MAX_PURSE_COINS)
		if purse > 0:
			ag["purse_bust_streak"] = 0
			i += 1
			continue
		if _npc_cargo_total_units(ag) > 0:
			ag["purse_bust_streak"] = 0
			i += 1
			continue
		var streak: int = clampi(int(ag.get("purse_bust_streak", 0)), 0, 999) + 1
		ag["purse_bust_streak"] = streak
		if streak < _NPC_BUST_EMPTY_STREAK_DAYS:
			i += 1
			continue
		var old_id: int = int(ag.get("id", 0))
		_npc_convoy_fixup_removed_agent_id(old_id)
		var home: String = str(ag.get("home_port", ""))
		if not _port_names.has(home):
			if _port_names.is_empty():
				_npc_agents.remove_at(i)
				continue
			home = str(_port_names.keys()[0])
		var inherit: Dictionary = {
			"buy": clampf(float(ag.get("buy_mastery", 1.0)), _NPC_MASTER_MIN, _NPC_MASTER_MAX),
			"sell": clampf(float(ag.get("sell_mastery", 1.0)), _NPC_MASTER_MIN, _NPC_MASTER_MAX),
		}
		if not _home_port_deserves_bankruptcy_replacement(home):
			_npc_agents.remove_at(i)
			continue
		_npc_agents[i] = _new_npc_agent(home, true, inherit)
		i += 1


func _apply_granary_spoilage() -> void:
	if not _goods.has("grain"):
		return
	for pid in _port_names.keys():
		var ps := str(pid)
		var g: int = _port_stock_qty(ps, "grain")
		if g <= 0:
			_last_grain_spoilage[ps] = 0
			continue
		var loss: int = int(ceil(float(g) * _GRAIN_SPOIL_FRACTION))
		if g > _GRAIN_SPOIL_MIN_STOCK and loss < 1:
			loss = 1
		loss = mini(g, mini(_GRAIN_SPOIL_CAP, maxi(0, loss)))
		if loss <= 0:
			_last_grain_spoilage[ps] = 0
			continue
		_last_grain_spoilage[ps] = loss
		_adjust_port_stock(ps, "grain", -loss)


func _npc_cargo_qty(cargo: Dictionary, good_id: String) -> int:
	return maxi(0, int(cargo.get(good_id, 0)))


func _npc_adjust_cargo(cargo: Dictionary, good_id: String, delta: int) -> void:
	var q: int = _npc_cargo_qty(cargo, good_id) + delta
	if q <= 0:
		cargo.erase(good_id)
	else:
		cargo[good_id] = q


## Combined buy/sell mastery → extra wholesale edge (rich get richer vs weak traders).
func _npc_wholesale_skill_edge(agent: Dictionary) -> float:
	var bm: float = clampf(float(agent.get("buy_mastery", 1.0)), _NPC_MASTER_MIN, _NPC_MASTER_MAX)
	var sm: float = clampf(float(agent.get("sell_mastery", 1.0)), _NPC_MASTER_MIN, _NPC_MASTER_MAX)
	return clampf(0.5 * (bm + sm) - 1.0, -0.26, 0.24)


## Deterministic per (port, good): regional cheap/dear bands for NPC wholesale. Matches tools/sim_100_days.py.
func _npc_str_mix(s: String, salt: int) -> int:
	var h: int = salt & 0x7fffffff
	var i: int = 0
	while i < s.length():
		h = absi((h * 131 + int(s.unicode_at(i))) % 2147483647)
		i += 1
	return h


func _npc_regional_buy_factor(port_id: String, good_id: String) -> float:
	var h: int = (_npc_str_mix(port_id, 17) ^ _npc_str_mix(good_id, 31)) & 0x7fffffff
	h = absi((h * 1103515245 + 12345) % 2147483647)
	var t: float = float(h % 1000) / 1000.0
	return lerpf(0.74, 1.10, t)


func _npc_regional_sell_factor(port_id: String, good_id: String) -> float:
	var h: int = _npc_str_mix(port_id, 7919) * 65537 + _npc_str_mix(good_id, 97)
	h = absi((h + 97) % 2147483647)
	var t: float = float(h % 1000) / 1000.0
	return lerpf(0.90, 1.28, t)


func _npc_mark_port_for_cargo_mark(ag: Dictionary) -> String:
	var dp: String = str(ag.get("docked_port", "")).strip_edges()
	if not dp.is_empty() and _port_names.has(dp):
		return dp
	var vd: String = str(ag.get("voyage_dest_id", "")).strip_edges()
	if not vd.is_empty() and _port_names.has(vd):
		return vd
	var hp: String = str(ag.get("home_port", "")).strip_edges()
	if not hp.is_empty() and _port_names.has(hp):
		return hp
	if _port_names.is_empty():
		return ""
	return str(_port_names.keys()[0])


func _npc_fleet_book_value_coins(ag: Dictionary) -> int:
	_ensure_npc_ship_fields(ag)
	var ships: int = clampi(int(ag.get("fleet_ships", 1)), 1, _FLEET_MAX_SHIPS)
	return ships * _FLEET_SHIP_NOMINAL_COINS


func _npc_cargo_estimated_coin_value(ag: Dictionary) -> int:
	var cr0: Variant = ag.get("cargo", null)
	if typeof(cr0) != TYPE_DICTIONARY:
		return 0
	var cargo: Dictionary = cr0 as Dictionary
	if cargo.is_empty():
		return 0
	var pid: String = _npc_mark_port_for_cargo_mark(ag)
	if pid.is_empty() or not _port_names.has(pid):
		return 0
	var total: int = 0
	for gk in cargo.keys():
		var gid: String = str(gk)
		var qty: int = maxi(0, _npc_cargo_qty(cargo, gid))
		if qty <= 0 or not _goods.has(gid):
			continue
		var unit: int = _npc_effective_sell_unit(ag, pid, gid)
		if unit <= 0 or unit >= 999000:
			continue
		total += qty * unit
	return mini(99_999_999, total)


func _npc_merchant_balance_sheet_coins(ag: Dictionary) -> int:
	_ensure_npc_money_field(ag)
	var purse: int = clampi(int(ag.get("money", 0)), 0, _MAX_PURSE_COINS)
	return purse + _npc_fleet_book_value_coins(ag) + _npc_cargo_estimated_coin_value(ag)


func _npc_effective_buy_unit(agent: Dictionary, port_id: String, good_id: String) -> int:
	var buy_m: float = clampf(float(agent.get("buy_mastery", 1.0)), _NPC_MASTER_MIN, _NPC_MASTER_MAX)
	var base_unit: int = _compute_player_buy_unit(port_id, good_id, false)
	if base_unit <= 0:
		return 999999
	var reg: float = _npc_regional_buy_factor(port_id, good_id)
	var edge: float = _npc_wholesale_skill_edge(agent)
	var cart: float = _port_cartel_strength_clamped(port_id)
	var toll_buy_rel: float = _TOLL_MERCHANT_BUY_RELIEF if _port_any_toll(port_id) else 0.0
	var buy_mult: float = clampf(
		_NPC_PORT_BUY_MULT * (1.0 - 0.14 * edge) * (1.0 - _SimAgents.CARTEL_BUY_TIGHTEN * cart) * (1.0 - toll_buy_rel),
		0.58,
		0.88,
	)
	var agree_b: float = _npc_big5_agree_buy_mult(agent)
	return maxi(1, int(floor(float(base_unit) * reg * buy_mult * agree_b / buy_m)))


func _npc_effective_sell_unit(agent: Dictionary, port_id: String, good_id: String) -> int:
	var sell_m: float = clampf(float(agent.get("sell_mastery", 1.0)), _NPC_MASTER_MIN, _NPC_MASTER_MAX)
	var base_unit: int = _compute_player_sell_unit(port_id, good_id, false)
	if base_unit <= 0:
		return 0
	var reg: float = _npc_regional_sell_factor(port_id, good_id)
	var edge: float = _npc_wholesale_skill_edge(agent)
	var cart2: float = _port_cartel_strength_clamped(port_id)
	var toll_sell_rel: float = _TOLL_MERCHANT_SELL_RELIEF if _port_any_toll(port_id) else 0.0
	var sell_mult: float = clampf(
		_NPC_PORT_SELL_MULT * (1.0 + 0.14 * edge) * (1.0 + _SimAgents.CARTEL_SELL_INFLATE * cart2) * (1.0 + toll_sell_rel),
		1.20,
		1.78,
	)
	var agree_s: float = _npc_big5_agree_sell_mult(agent)
	return maxi(1, int(ceil(float(base_unit) * reg * sell_mult * agree_s * sell_m)))


func _npc_snapshot_price_memory(agent: Dictionary, port_id: String) -> void:
	if not _port_names.has(port_id):
		return
	if not agent.has("price_memory") or typeof(agent.get("price_memory")) != TYPE_DICTIONARY:
		agent["price_memory"] = {}
	var pm: Dictionary = agent["price_memory"] as Dictionary
	var row: Dictionary = {}
	for gk in _goods.keys():
		var gids: String = str(gk)
		row[gids] = {
			"bu": _npc_effective_buy_unit(agent, port_id, gids),
			"se": _npc_effective_sell_unit(agent, port_id, gids),
		}
	pm[port_id] = row


func _npc_memory_sell_edge(agent: Dictionary, port_id: String, good_id: String) -> float:
	var cur: int = _npc_effective_sell_unit(agent, port_id, good_id)
	if cur <= 0:
		return 1.0
	var pm0: Variant = agent.get("price_memory", null)
	if typeof(pm0) != TYPE_DICTIONARY:
		return 1.0
	var pm: Dictionary = pm0 as Dictionary
	var bestm: int = 0
	for pk in pm.keys():
		var ps: String = str(pk)
		if ps == port_id:
			continue
		if not _port_names.has(ps):
			continue
		var row0: Variant = (pm[pk] as Dictionary).get(good_id, null)
		if typeof(row0) != TYPE_DICTIONARY:
			continue
		var sev: int = int((row0 as Dictionary).get("se", 0))
		bestm = maxi(bestm, sev)
	if bestm <= 0:
		return 1.0
	return clampf(float(cur) / float(maxi(1, bestm)), 0.62, 1.52)


func _npc_memory_buy_edge(agent: Dictionary, port_id: String, good_id: String) -> float:
	var cur: int = _npc_effective_buy_unit(agent, port_id, good_id)
	if cur >= 999000:
		return 1.0
	var pm0: Variant = agent.get("price_memory", null)
	if typeof(pm0) != TYPE_DICTIONARY:
		return 1.0
	var pm: Dictionary = pm0 as Dictionary
	var bestc: int = 999999999
	for pk in pm.keys():
		var ps: String = str(pk)
		if ps == port_id:
			continue
		if not _port_names.has(ps):
			continue
		var row0: Variant = (pm[pk] as Dictionary).get(good_id, null)
		if typeof(row0) != TYPE_DICTIONARY:
			continue
		var buv: int = int((row0 as Dictionary).get("bu", 999999999))
		bestc = mini(bestc, buv)
	if bestc >= 999999000:
		return 1.0
	return clampf(float(bestc) / float(maxi(1, cur)), 1.0, 1.62)


func _sanitize_npc_peer_debts(ag: Dictionary) -> void:
	var raw: Variant = ag.get("npc_peer_debts", null)
	if typeof(raw) != TYPE_ARRAY:
		ag["npc_peer_debts"] = []
		return
	var arr: Array = raw as Array
	var out: Array = []
	for cell in arr:
		if typeof(cell) != TYPE_DICTIONARY:
			continue
		var row: Dictionary = cell as Dictionary
		var cid: int = int(row.get("creditor", 0))
		var rem: int = maxi(0, int(row.get("remaining", 0)))
		if cid <= 0 or rem <= 0:
			continue
		out.append({"creditor": cid, "remaining": rem})
		if out.size() >= _NPC_PEER_LOAN_MAX_DEBTS:
			break
	ag["npc_peer_debts"] = out


func _npc_peer_debt_sum_remaining(ag: Dictionary) -> int:
	_sanitize_npc_peer_debts(ag)
	var t: int = 0
	for cell in ag["npc_peer_debts"] as Array:
		if typeof(cell) != TYPE_DICTIONARY:
			continue
		t += maxi(0, int((cell as Dictionary).get("remaining", 0)))
	return t


func _npc_peer_loan_repay_from_margin(ag: Dictionary, margin_coins: int) -> int:
	if margin_coins <= 0:
		return margin_coins
	_sanitize_npc_peer_debts(ag)
	var debts: Array = ag["npc_peer_debts"] as Array
	if debts.is_empty():
		return margin_coins
	var idxm: Dictionary = _npc_index_agents_by_id()
	var left: int = margin_coins
	var i: int = 0
	while i < debts.size() and left > 0:
		var c0: Variant = debts[i]
		if typeof(c0) != TYPE_DICTIONARY:
			i += 1
			continue
		var row: Dictionary = c0 as Dictionary
		var cid: int = int(row.get("creditor", 0))
		var rem: int = maxi(0, int(row.get("remaining", 0)))
		if rem <= 0:
			debts.remove_at(i)
			continue
		var pay: int = mini(left, rem)
		rem -= pay
		left -= pay
		row["remaining"] = rem
		if idxm.has(cid):
			var cr: Dictionary = idxm[cid] as Dictionary
			var cm: int = clampi(int(cr.get("money", 0)), 0, _MAX_PURSE_COINS)
			cr["money"] = clampi(cm + pay, 0, _MAX_PURSE_COINS)
		if rem <= 0:
			debts.remove_at(i)
		else:
			debts[i] = row
			i += 1
	ag["npc_peer_debts"] = debts
	return left


func _npc_peer_creditor_ids_for_agent(ag: Dictionary) -> Array:
	_sanitize_npc_peer_debts(ag)
	var ids: Array = []
	for cell in ag["npc_peer_debts"] as Array:
		if typeof(cell) != TYPE_DICTIONARY:
			continue
		var cid: int = int((cell as Dictionary).get("creditor", 0))
		if cid > 0:
			ids.append(cid)
	return ids


func _npc_peer_creditor_present_at_port(ag: Dictionary, docked_port: String) -> bool:
	var ps: String = str(docked_port)
	if ps.is_empty():
		return false
	var idxm: Dictionary = _npc_index_agents_by_id()
	for cid_v in _npc_peer_creditor_ids_for_agent(ag):
		var cid: int = int(cid_v)
		if not idxm.has(cid):
			continue
		var cr: Dictionary = idxm[cid] as Dictionary
		if int(cr.get("voyage_days_remaining", 0)) != 0:
			continue
		if str(cr.get("docked_port", "")) == ps:
			return true
	return false


func _npc_peer_creditor_home_penalty(agent: Dictionary, dest: String) -> float:
	var ds: String = str(dest)
	if ds.is_empty():
		return 0.0
	_sanitize_npc_peer_debts(agent)
	var debts: Array = agent["npc_peer_debts"] as Array
	if debts.is_empty():
		return 0.0
	var idxm: Dictionary = _npc_index_agents_by_id()
	var pen: float = 0.0
	for cell in debts:
		if typeof(cell) != TYPE_DICTIONARY:
			continue
		var row: Dictionary = cell as Dictionary
		var rem: int = maxi(0, int(row.get("remaining", 0)))
		if rem <= 0:
			continue
		var cid: int = int(row.get("creditor", 0))
		if not idxm.has(cid):
			continue
		var hp: String = str((idxm[cid] as Dictionary).get("home_port", ""))
		if hp.is_empty() or hp != ds:
			continue
		var consc: float = _npc_trait_f(agent, _NPC_TRAIT_CONSC)
		var neuro: float = _npc_trait_f(agent, _NPC_TRAIT_NEURO)
		var flee: float = clampf((1.0 - consc) * 0.55 + neuro * 0.45, 0.0, 1.0)
		pen += float(rem) * _NPC_PEER_LOAN_HOME_AVOID_PER_COIN * flee
	return pen


func _npc_peer_loan_flee_gate_sub(agent: Dictionary, docked_port: String) -> float:
	if not _npc_peer_creditor_present_at_port(agent, docked_port):
		return 0.0
	var owed: int = _npc_peer_debt_sum_remaining(agent)
	if owed <= 0:
		return 0.0
	var neuro: float = _npc_trait_f(agent, _NPC_TRAIT_NEURO)
	var consc: float = _npc_trait_f(agent, _NPC_TRAIT_CONSC)
	var open: float = _npc_trait_f(agent, _NPC_TRAIT_OPEN)
	var frac: float = clampf(float(owed) / 220.0, 0.0, 1.0)
	var flee: float = clampf((1.0 - consc) * 0.5 + neuro * 0.42 + open * 0.12, 0.0, 1.0)
	return mini(_NPC_PEER_LOAN_FLEE_GATE_SUB_MAX, 0.05 + frac * flee * 0.38)


func _npc_try_peer_loans_after_dock_trade() -> void:
	var byp: Dictionary = {}
	for item in _npc_agents:
		if typeof(item) != TYPE_DICTIONARY:
			continue
		var ag: Dictionary = item as Dictionary
		if str(ag.get("voyage_role", _VOYAGE_ROLE_MERCHANT)) != _VOYAGE_ROLE_MERCHANT:
			continue
		if int(ag.get("voyage_days_remaining", 0)) != 0:
			continue
		var pid: String = str(ag.get("docked_port", ""))
		if not _port_names.has(pid):
			continue
		if not byp.has(pid):
			byp[pid] = []
		(byp[pid] as Array).append(ag)
	for pid in byp.keys():
		var arr: Array = byp[pid] as Array
		if arr.size() < 2:
			continue
		for debtor in arr:
			if typeof(debtor) != TYPE_DICTIONARY:
				continue
			var d: Dictionary = debtor as Dictionary
			_sanitize_npc_peer_debts(d)
			if (d["npc_peer_debts"] as Array).size() >= _NPC_PEER_LOAN_MAX_DEBTS:
				continue
			var rep_d: float = clampf(float(d.get("merchant_repute_01", 0.52)), 0.0, 1.0)
			var p_loan_roll: float = clampf(
				_NPC_PEER_LOAN_OFFER_ROLL * lerpf(0.78, 1.22, rep_d), 0.0, 0.58
			)
			if _rng.randf() > p_loan_roll:
				continue
			var purse_d: int = clampi(int(d.get("money", 0)), 0, _MAX_PURSE_COINS)
			if purse_d > _NPC_PEER_LOAN_DEBTOR_PURSE_MAX:
				continue
			var creditors: Array = arr.duplicate()
			for _s in range(maxi(1, creditors.size() * 2)):
				var j: int = _rng.randi_range(0, maxi(0, creditors.size() - 1))
				var k: int = _rng.randi_range(0, maxi(0, creditors.size() - 1))
				var tmp: Variant = creditors[j]
				creditors[j] = creditors[k]
				creditors[k] = tmp
			for cred_raw in creditors:
				if typeof(cred_raw) != TYPE_DICTIONARY:
					continue
				var c: Dictionary = cred_raw as Dictionary
				if int(c.get("id", -1)) == int(d.get("id", -2)):
					continue
				var purse_c: int = clampi(int(c.get("money", 0)), 0, _MAX_PURSE_COINS)
				if purse_c < _NPC_PEER_LOAN_CREDITOR_PURSE_MIN:
					continue
				var cushion: int = _NPC_PEER_LOAN_CREDITOR_RESERVE + _npc_officer_due_coins(c) * 2
				var cap: int = purse_c - cushion
				if cap < _NPC_PEER_LOAN_MIN_PRINCIPAL:
					continue
				var agree: float = _npc_trait_f(c, _NPC_TRAIT_AGREE)
				if _rng.randf() > lerpf(0.07, 0.36, agree):
					continue
				var d_consc: float = _npc_trait_f(d, _NPC_TRAIT_CONSC)
				if _rng.randf() > lerpf(0.1, 0.62, d_consc):
					continue
				var pmax: int = mini(
					int(round(float(_NPC_PEER_LOAN_MAX_PRINCIPAL) * lerpf(0.9, 1.1, rep_d))),
					cap
				)
				var pmin: int = mini(_NPC_PEER_LOAN_MIN_PRINCIPAL, pmax)
				if pmin > pmax:
					continue
				var principal: int = _rng.randi_range(pmin, pmax)
				if principal <= 0:
					continue
				c["money"] = clampi(purse_c - principal, 0, _MAX_PURSE_COINS)
				d["money"] = clampi(purse_d + principal, 0, _MAX_PURSE_COINS)
				var lst: Array = d["npc_peer_debts"] as Array
				lst.append({"creditor": int(c.get("id", 0)), "remaining": principal})
				d["npc_peer_debts"] = lst
				break


func _npc_voyage_dest_score(agent: Dictionary, here: String, dest: String) -> float:
	var cr0: Variant = agent.get("cargo", null)
	if typeof(cr0) != TYPE_DICTIONARY:
		return 0.12
	var cargo: Dictionary = cr0 as Dictionary
	var pm0: Variant = agent.get("price_memory", null)
	if typeof(pm0) != TYPE_DICTIONARY:
		return 0.35
	var pm: Dictionary = pm0 as Dictionary
	var row_here: Dictionary = {}
	if pm.has(here) and typeof(pm[here]) == TYPE_DICTIONARY:
		row_here = pm[here] as Dictionary
	var row_dest: Dictionary = {}
	var has_dest: bool = pm.has(dest) and typeof(pm[dest]) == TYPE_DICTIONARY
	if has_dest:
		row_dest = pm[dest] as Dictionary
	var sc: float = 0.1
	for gk in cargo.keys():
		var gid: String = str(gk)
		if not _goods.has(gid):
			continue
		var qty: int = _npc_cargo_qty(cargo, gid)
		if qty <= 0:
			continue
		var se_h: int = 0
		var rh0: Variant = row_here.get(gid, null)
		if typeof(rh0) == TYPE_DICTIONARY:
			se_h = maxi(0, int((rh0 as Dictionary).get("se", 0)))
		var se_d: int = 0
		if has_dest:
			var rd0: Variant = row_dest.get(gid, null)
			if typeof(rd0) == TYPE_DICTIONARY:
				se_d = maxi(0, int((rd0 as Dictionary).get("se", 0)))
		if se_d > 0 and se_h > 0:
			sc += float(qty) * (float(se_d) / float(maxi(1, se_h)) - 1.0)
		elif se_d > 0:
			sc += float(qty) * 0.18
		else:
			sc += float(qty) * 0.04
	var ntr: float = _npc_trait_f(agent, _NPC_TRAIT_NEURO)
	var udst: float = float(get_port_food_unrest(dest)) / 200.0
	sc *= 1.0 - 0.24 * (ntr - 0.5) * udst
	if _world_npc_city_grain_contracts_enabled and _npc_city_grain_contract_active(agent):
		var cgd: Dictionary = agent.get("city_grain_contract", {}) as Dictionary
		if str(cgd.get("dest", "")) == dest:
			var due_c: int = clampi(int(cgd.get("due", 0)), 0, 9999999)
			var slack_c: int = due_c - current_day
			var cbon: float = 0.42 + 0.28 * clampf(float(slack_c) / 44.0, 0.0, 1.0)
			if slack_c <= 14:
				cbon += 0.62
			if slack_c <= 7:
				cbon += 0.38
			sc += cbon
	sc = maxf(0.02, sc) - _npc_peer_creditor_home_penalty(agent, dest)
	return maxf(0.02, sc)


func _npc_memory_pick_neighbor_dest(agent: Dictionary, here: String, neigh: Array) -> String:
	if neigh.is_empty():
		return ""
	var best: String = str(neigh[0])
	var best_sc: float = -1.0e15
	for ni in neigh:
		var d: String = str(ni)
		var sc: float = _npc_voyage_dest_score(agent, here, d)
		if sc > best_sc:
			best_sc = sc
			best = d
	return best


func _npc_buy_from_port(agent: Dictionary, port_id: String, good_id: String, qty: int) -> void:
	if qty <= 0 or not _goods.has(good_id):
		return
	if not agent.has("cargo") or typeof(agent["cargo"]) != TYPE_DICTIONARY:
		agent["cargo"] = {}
	var cargo: Dictionary = agent["cargo"] as Dictionary
	var unit: int = _npc_effective_buy_unit(agent, port_id, good_id)
	if unit >= 999000:
		return
	var coins: int = clampi(int(agent.get("money", 0)), 0, _MAX_PURSE_COINS)
	var max_by_money: int = coins / unit
	var have: int = _port_stock_qty(port_id, good_id)
	var cap_free: int = _npc_cargo_free_space(agent)
	var q: int = mini(mini(mini(qty, have), max_by_money), cap_free)
	if q <= 0:
		return
	while q > 0:
		var cost_test: int = unit * q
		var fee_test: int = _captain_trade_fee_on_buy(cost_test)
		if coins - cost_test - fee_test >= _NPC_PURSE_RESERVE:
			break
		q -= 1
	if q <= 0:
		return
	var cost: int = unit * q
	var buy_fee: int = _captain_trade_fee_on_buy(cost)
	agent["money"] = coins - cost - buy_fee
	_bump_port_wealth(port_id, maxi(1, cost / 14))
	_adjust_port_stock(port_id, good_id, -q)
	_npc_adjust_cargo(cargo, good_id, q)
	_bump_npc_commerce_buy(port_id, q, cost)


func _npc_sell_to_port(agent: Dictionary, port_id: String, good_id: String, qty: int) -> void:
	if qty <= 0 or not _goods.has(good_id):
		return
	if not agent.has("cargo") or typeof(agent["cargo"]) != TYPE_DICTIONARY:
		agent["cargo"] = {}
	var cargo: Dictionary = agent["cargo"] as Dictionary
	var have: int = _npc_cargo_qty(cargo, good_id)
	var q: int = mini(qty, have)
	if q <= 0:
		return
	var unit: int = _npc_effective_sell_unit(agent, port_id, good_id)
	if unit <= 0:
		return
	var revenue: int = unit * q
	var sell_fee: int = _captain_trade_fee_on_sell(revenue)
	var toll_base: int = _port_toll_per_unit(port_id, good_id) * q
	var toll_paid: int = 0
	if toll_base > 0 and not _npc_has_toll_graft(agent, port_id):
		toll_paid = _npc_roll_toll_coins_paid(agent, port_id, toll_base)
	var margin0: int = maxi(0, revenue - sell_fee - toll_paid)
	var margin1: int = _npc_peer_loan_repay_from_margin(agent, margin0)
	agent["money"] = clampi(int(agent.get("money", 0)) + margin1, 0, _MAX_PURSE_COINS)
	if toll_paid > 0:
		_bump_port_for_toll_receipt(port_id, toll_paid)
	_bump_port_wealth(port_id, maxi(1, revenue / 12))
	_npc_adjust_cargo(cargo, good_id, -q)
	_adjust_port_stock(port_id, good_id, q)
	_bump_npc_commerce_sell(port_id, q, revenue)


## Rare: docked captain with bullion uses the civic mint to strike coin from cargo (fee stays in port prosperity).
func _npc_try_optional_mint_bullion_at_dock(trader: Dictionary, port_id: String) -> bool:
	var ps := str(port_id)
	if not _port_mint_cfg.has(ps):
		return false
	if _rng.randf() >= 0.062:
		return false
	var cfg0: Variant = _port_mint_cfg.get(ps, null)
	if typeof(cfg0) != TYPE_DICTIONARY:
		return false
	var cfg: Dictionary = cfg0 as Dictionary
	var gb: int = clampi(int(cfg.get("gold_per_batch", 1)), 0, 24)
	var sb: int = clampi(int(cfg.get("silver_per_batch", 2)), 0, 36)
	if gb <= 0 and sb <= 0:
		return false
	var cargo: Dictionary = trader["cargo"] as Dictionary
	if gb > 0 and _npc_cargo_qty(cargo, "gold") < gb:
		return false
	if sb > 0 and _npc_cargo_qty(cargo, "silver") < sb:
		return false
	var cpb: int = clampi(int(cfg.get("coins_per_batch", 72)), 1, 500)
	var fee: int = maxi(1, cpb / 24)
	if gb > 0:
		_npc_adjust_cargo(cargo, "gold", -gb)
	if sb > 0:
		_npc_adjust_cargo(cargo, "silver", -sb)
	var pur: int = clampi(int(trader.get("money", 0)), 0, _MAX_PURSE_COINS)
	trader["money"] = clampi(pur + cpb - fee, 0, _MAX_PURSE_COINS)
	_bump_port_wealth(ps, fee)
	return true


func _npc_tick_one(port_id: String, trader: Dictionary) -> void:
	if not trader.has("cargo") or typeof(trader["cargo"]) != TYPE_DICTIONARY:
		trader["cargo"] = {}
	_ensure_npc_money_field(trader)
	var cargo: Dictionary = trader["cargo"] as Dictionary
	var g_tgt: int = _stock_target_for_good("grain")
	var w_tgt: int = _stock_target_for_good("wine")
	var g_stock: int = _port_stock_qty(port_id, "grain")
	var w_stock: int = _port_stock_qty(port_id, "wine")
	var g_ratio: float = float(g_stock) / float(maxi(1, g_tgt))
	var w_ratio: float = float(w_stock) / float(maxi(1, w_tgt))
	var crop_hoard_01: float = 0.0
	if _goods.has("grain"):
		crop_hoard_01 = _crop_phase2_npc_hoard_weight_01(port_id)
	var roll: float = _rng.randf()
	if _rng.randf() < 0.52:
		var best_sg: String = ""
		var best_se: float = 1.0
		for gk in cargo.keys():
			var gim: String = str(gk)
			if not _goods.has(gim):
				continue
			if _npc_cargo_qty(cargo, gim) <= 0:
				continue
			var ed: float = _npc_memory_sell_edge(trader, port_id, gim)
			if ed > best_se:
				best_se = ed
				best_sg = gim
		if not best_sg.is_empty() and best_se >= 1.09:
			_npc_sell_to_port(trader, port_id, best_sg, _npc_roll_trade_lot_qty(trader, port_id, best_sg, false))
			return
	if _rng.randf() < 0.44:
		var best_bg: String = ""
		var best_be: float = 1.0
		for gk2 in _goods.keys():
			var gids2: String = str(gk2)
			var be: float = _npc_memory_buy_edge(trader, port_id, gids2)
			if be > best_be:
				best_be = be
				best_bg = gids2
		if (
			not best_bg.is_empty()
			and best_be >= 1.10
			and _port_stock_qty(port_id, best_bg) > 0
		):
			_npc_buy_from_port(trader, port_id, best_bg, _npc_roll_trade_lot_qty(trader, port_id, best_bg, true))
			return
	# Prefer restocking the port when public granaries are tight; skim when full.
	if _goods.has("grain"):
		var g_sell_lo: float = 0.42 + _CROP_PHASE2_NPC_GRAIN_SELL_FLOOR_SHIFT * crop_hoard_01
		var g_buy_hi: float = 1.1 - _CROP_PHASE2_NPC_GRAIN_BUY_CEIL_SHIFT * crop_hoard_01
		if g_ratio < g_sell_lo and _npc_cargo_qty(cargo, "grain") > 0:
			_npc_sell_to_port(trader, port_id, "grain", _npc_roll_trade_lot_qty(trader, port_id, "grain", false))
			return
		if g_ratio > g_buy_hi:
			_npc_buy_from_port(trader, port_id, "grain", _npc_roll_trade_lot_qty(trader, port_id, "grain", true))
			return
	if _goods.has("wine"):
		if w_ratio < 0.46 and _npc_cargo_qty(cargo, "wine") > 0:
			_npc_sell_to_port(trader, port_id, "wine", _npc_roll_trade_lot_qty(trader, port_id, "wine", false))
			return
		if w_ratio > 1.02:
			_npc_buy_from_port(trader, port_id, "wine", _npc_roll_trade_lot_qty(trader, port_id, "wine", true))
			return
	if _goods.has("metal"):
		var m_tgt: int = _stock_target_for_good("metal")
		var m_stock: int = _port_stock_qty(port_id, "metal")
		var m_ratio: float = float(m_stock) / float(maxi(1, m_tgt))
		if m_ratio < 0.36 and _npc_cargo_qty(cargo, "metal") > 0:
			_npc_sell_to_port(trader, port_id, "metal", _npc_roll_trade_lot_qty(trader, port_id, "metal", false))
			return
		if m_ratio > 1.06:
			_npc_buy_from_port(trader, port_id, "metal", _npc_roll_trade_lot_qty(trader, port_id, "metal", true))
			return
	if _goods.has("wire"):
		var wi_tgt: int = _stock_target_for_good("wire")
		var wi_stock: int = _port_stock_qty(port_id, "wire")
		var wi_ratio: float = float(wi_stock) / float(maxi(1, wi_tgt))
		if wi_ratio < 0.34 and _npc_cargo_qty(cargo, "wire") > 0:
			_npc_sell_to_port(trader, port_id, "wire", _npc_roll_trade_lot_qty(trader, port_id, "wire", false))
			return
		if wi_ratio > 1.04:
			_npc_buy_from_port(trader, port_id, "wire", _npc_roll_trade_lot_qty(trader, port_id, "wire", true))
			return
	if _goods.has("salt"):
		var sa_tgt: int = _stock_target_for_good("salt")
		var sa_stock: int = _port_stock_qty(port_id, "salt")
		var sa_ratio: float = float(sa_stock) / float(maxi(1, sa_tgt))
		if sa_ratio < 0.4 and _npc_cargo_qty(cargo, "salt") > 0:
			_npc_sell_to_port(trader, port_id, "salt", _npc_roll_trade_lot_qty(trader, port_id, "salt", false))
			return
		if sa_ratio > 1.05:
			_npc_buy_from_port(trader, port_id, "salt", _npc_roll_trade_lot_qty(trader, port_id, "salt", true))
			return
	if _goods.has("olive_oil"):
		var oo_tgt: int = _stock_target_for_good("olive_oil")
		var oo_stock: int = _port_stock_qty(port_id, "olive_oil")
		var oo_ratio: float = float(oo_stock) / float(maxi(1, oo_tgt))
		if oo_ratio < 0.4 and _npc_cargo_qty(cargo, "olive_oil") > 0:
			_npc_sell_to_port(trader, port_id, "olive_oil", _npc_roll_trade_lot_qty(trader, port_id, "olive_oil", false))
			return
		if oo_ratio > 1.03:
			_npc_buy_from_port(trader, port_id, "olive_oil", _npc_roll_trade_lot_qty(trader, port_id, "olive_oil", true))
			return
	if _goods.has("pottery"):
		var po_tgt: int = _stock_target_for_good("pottery")
		var po_stock: int = _port_stock_qty(port_id, "pottery")
		var po_ratio: float = float(po_stock) / float(maxi(1, po_tgt))
		if po_ratio < 0.38 and _npc_cargo_qty(cargo, "pottery") > 0:
			_npc_sell_to_port(trader, port_id, "pottery", _npc_roll_trade_lot_qty(trader, port_id, "pottery", false))
			return
		if po_ratio > 1.03:
			_npc_buy_from_port(trader, port_id, "pottery", _npc_roll_trade_lot_qty(trader, port_id, "pottery", true))
			return
	if _goods.has("fish"):
		var fi_tgt: int = _stock_target_for_good("fish")
		var fi_stock: int = _port_stock_qty(port_id, "fish")
		var fi_ratio: float = float(fi_stock) / float(maxi(1, fi_tgt))
		if fi_ratio < 0.4 and _npc_cargo_qty(cargo, "fish") > 0:
			_npc_sell_to_port(trader, port_id, "fish", _npc_roll_trade_lot_qty(trader, port_id, "fish", false))
			return
		if fi_ratio > 1.04:
			_npc_buy_from_port(trader, port_id, "fish", _npc_roll_trade_lot_qty(trader, port_id, "fish", true))
			return
	if _goods.has("timber"):
		var tb_tgt: int = _stock_target_for_good("timber")
		var tb_stock: int = _port_stock_qty(port_id, "timber")
		var tb_ratio: float = float(tb_stock) / float(maxi(1, tb_tgt))
		if tb_ratio < 0.38 and _npc_cargo_qty(cargo, "timber") > 0:
			_npc_sell_to_port(trader, port_id, "timber", _npc_roll_trade_lot_qty(trader, port_id, "timber", false))
			return
		if tb_ratio > 1.03:
			_npc_buy_from_port(trader, port_id, "timber", _npc_roll_trade_lot_qty(trader, port_id, "timber", true))
			return
	if _goods.has("textiles"):
		var tx_tgt: int = _stock_target_for_good("textiles")
		var tx_stock: int = _port_stock_qty(port_id, "textiles")
		var tx_ratio: float = float(tx_stock) / float(maxi(1, tx_tgt))
		if tx_ratio < 0.38 and _npc_cargo_qty(cargo, "textiles") > 0:
			_npc_sell_to_port(trader, port_id, "textiles", _npc_roll_trade_lot_qty(trader, port_id, "textiles", false))
			return
		if tx_ratio > 1.03:
			_npc_buy_from_port(trader, port_id, "textiles", _npc_roll_trade_lot_qty(trader, port_id, "textiles", true))
			return
	if _goods.has("spice"):
		var s_tgt: int = _stock_target_for_good("spice")
		var s_stock: int = _port_stock_qty(port_id, "spice")
		var s_ratio: float = float(s_stock) / float(maxi(1, s_tgt))
		if s_ratio < 0.38 and _npc_cargo_qty(cargo, "spice") > 0:
			_npc_sell_to_port(trader, port_id, "spice", _npc_roll_trade_lot_qty(trader, port_id, "spice", false))
			return
		if s_ratio > 1.02:
			_npc_buy_from_port(trader, port_id, "spice", _npc_roll_trade_lot_qty(trader, port_id, "spice", true))
			return
	if _goods.has("gold"):
		var au_tgt: int = _stock_target_for_good("gold")
		var au_stock: int = _port_stock_qty(port_id, "gold")
		var au_ratio: float = float(au_stock) / float(maxi(1, au_tgt))
		if au_ratio < 0.36 and _npc_cargo_qty(cargo, "gold") > 0:
			_npc_sell_to_port(trader, port_id, "gold", _npc_roll_trade_lot_qty(trader, port_id, "gold", false))
			return
		if au_ratio > 1.02:
			_npc_buy_from_port(trader, port_id, "gold", _npc_roll_trade_lot_qty(trader, port_id, "gold", true))
			return
	if _goods.has("silver"):
		var ag_tgt: int = _stock_target_for_good("silver")
		var ag_stock: int = _port_stock_qty(port_id, "silver")
		var ag_ratio: float = float(ag_stock) / float(maxi(1, ag_tgt))
		if ag_ratio < 0.36 and _npc_cargo_qty(cargo, "silver") > 0:
			_npc_sell_to_port(trader, port_id, "silver", _npc_roll_trade_lot_qty(trader, port_id, "silver", false))
			return
		if ag_ratio > 1.02:
			_npc_buy_from_port(trader, port_id, "silver", _npc_roll_trade_lot_qty(trader, port_id, "silver", true))
			return
	if _npc_try_optional_mint_bullion_at_dock(trader, port_id):
		return
	if _goods.has("slaves"):
		var sl_tgt: int = _stock_target_for_good("slaves")
		var sl_stock: int = _port_stock_qty(port_id, "slaves")
		var sl_ratio: float = float(sl_stock) / float(maxi(1, sl_tgt))
		if sl_ratio < 0.4 and _npc_cargo_qty(cargo, "slaves") > 0:
			_npc_sell_to_port(trader, port_id, "slaves", _npc_roll_trade_lot_qty(trader, port_id, "slaves", false))
			return
		if sl_ratio > 1.03:
			_npc_buy_from_port(trader, port_id, "slaves", _npc_roll_trade_lot_qty(trader, port_id, "slaves", true))
			return
	if roll < 0.5 and _goods.has("grain"):
		var p_grain_buy: float = clampf(0.55 + _CROP_PHASE2_NPC_GRAIN_P_BUY_SHIFT * crop_hoard_01, 0.48, 0.90)
		if _rng.randf() < p_grain_buy:
			_npc_buy_from_port(trader, port_id, "grain", _npc_roll_trade_lot_qty(trader, port_id, "grain", true))
		else:
			if _npc_cargo_qty(cargo, "grain") > 0:
				_npc_sell_to_port(trader, port_id, "grain", _npc_roll_trade_lot_qty(trader, port_id, "grain", false))
	elif _goods.has("wine"):
		if _rng.randf() < 0.55:
			_npc_buy_from_port(trader, port_id, "wine", _npc_roll_trade_lot_qty(trader, port_id, "wine", true))
		else:
			if _npc_cargo_qty(cargo, "wine") > 0:
				_npc_sell_to_port(trader, port_id, "wine", _npc_roll_trade_lot_qty(trader, port_id, "wine", false))
	elif roll < 0.68 and _goods.has("metal"):
		if _rng.randf() < 0.52:
			_npc_buy_from_port(trader, port_id, "metal", _npc_roll_trade_lot_qty(trader, port_id, "metal", true))
		else:
			if _npc_cargo_qty(cargo, "metal") > 0:
				_npc_sell_to_port(trader, port_id, "metal", _npc_roll_trade_lot_qty(trader, port_id, "metal", false))
	elif _goods.has("wire"):
		if _rng.randf() < 0.52:
			_npc_buy_from_port(trader, port_id, "wire", _npc_roll_trade_lot_qty(trader, port_id, "wire", true))
		else:
			if _npc_cargo_qty(cargo, "wire") > 0:
				_npc_sell_to_port(trader, port_id, "wire", _npc_roll_trade_lot_qty(trader, port_id, "wire", false))


func _init_port_wealth_baseline() -> void:
	_port_wealth.clear()
	for pid in _port_names.keys():
		var pid_s := str(pid)
		if _port_initial_wealth.has(pid_s):
			_port_wealth[pid_s] = clampi(int(_port_initial_wealth[pid_s]), 20, 8000)
		else:
			var g: int = _port_stock_qty(pid_s, "grain")
			var w: int = _port_stock_qty(pid_s, "wine")
			var mt0: int = _port_stock_qty(pid_s, "metal") if _goods.has("metal") else 0
			var wr0: int = _port_stock_qty(pid_s, "wire") if _goods.has("wire") else 0
			var sa0: int = _port_stock_qty(pid_s, "salt") if _goods.has("salt") else 0
			var oo0: int = _port_stock_qty(pid_s, "olive_oil") if _goods.has("olive_oil") else 0
			var po0: int = _port_stock_qty(pid_s, "pottery") if _goods.has("pottery") else 0
			var fi0: int = _port_stock_qty(pid_s, "fish") if _goods.has("fish") else 0
			var tb0: int = _port_stock_qty(pid_s, "timber") if _goods.has("timber") else 0
			var tx0: int = _port_stock_qty(pid_s, "textiles") if _goods.has("textiles") else 0
			_port_wealth[pid_s] = clampi(
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
				4000
			)


func _serialize_port_wealth() -> Dictionary:
	var out: Dictionary = {}
	for k in _port_wealth.keys():
		out[str(k)] = int(_port_wealth[k])
	return out


func _deserialize_port_wealth(data: Dictionary) -> void:
	_port_wealth.clear()
	for pk in data.keys():
		var pid := str(pk)
		if not _port_names.has(pid):
			continue
		_port_wealth[pid] = clampi(int(data[pk]), 1, 999999)


func _serialize_port_float_map(m: Dictionary) -> Dictionary:
	var out: Dictionary = {}
	for pid in _port_names.keys():
		var ps := str(pid)
		out[ps] = float(m.get(ps, 0.0))
	return out


func _serialize_port_int_map(m: Dictionary) -> Dictionary:
	var out: Dictionary = {}
	for pid in _port_names.keys():
		var ps := str(pid)
		out[ps] = int(m.get(ps, 0))
	return out


func _serialize_port_nested_float_map(m: Dictionary) -> Dictionary:
	var out: Dictionary = {}
	for pid in _port_names.keys():
		var ps := str(pid)
		var inner0: Variant = m.get(ps, null)
		if typeof(inner0) != TYPE_DICTIONARY:
			continue
		var row: Dictionary = {}
		for gk in (inner0 as Dictionary).keys():
			row[str(gk)] = float((inner0 as Dictionary)[gk])
		if not row.is_empty():
			out[ps] = row
	return out


func _deserialize_port_float_map_into(
	target: Dictionary,
	data: Dictionary,
	lo: float,
	hi: float,
) -> void:
	target.clear()
	for pk in data.keys():
		var pid := str(pk)
		if not _port_names.has(pid):
			continue
		target[pid] = clampf(float(data[pk]), lo, hi)


func _deserialize_port_int_map_into(target: Dictionary, data: Dictionary, lo: int, hi: int) -> void:
	target.clear()
	for pk in data.keys():
		var pid := str(pk)
		if not _port_names.has(pid):
			continue
		target[pid] = clampi(int(data[pk]), lo, hi)


func _deserialize_port_rumor_good_delta(data: Dictionary) -> void:
	_port_rumor_good_delta.clear()
	for pk in data.keys():
		var pid := str(pk)
		if not _port_names.has(pid):
			continue
		var inner0: Variant = data[pk]
		if typeof(inner0) != TYPE_DICTIONARY:
			continue
		var row: Dictionary = {}
		for gk in (inner0 as Dictionary).keys():
			var gid := str(gk)
			if not _goods.has(gid):
				continue
			row[gid] = clampf(float((inner0 as Dictionary)[gk]), -0.15, 0.15)
		_port_rumor_good_delta[pid] = row


func _port_slave_labor_demand(port_id: String) -> int:
	if not _goods.has("slaves"):
		return 0
	var ps := str(port_id)
	var sumd: int = 0
	for f in _farms:
		if typeof(f) != TYPE_DICTIONARY:
			continue
		var fd: Dictionary = f as Dictionary
		if str(fd.get("port_id", "")) != ps:
			continue
		var g: int = maxi(0, int(fd.get("grain_per_day", 0)))
		var w: int = maxi(0, int(fd.get("wine_per_day", 0)))
		var fi: int = maxi(0, int(fd.get("fish_per_day", 0)))
		if g <= 0 and w <= 0 and fi <= 0:
			continue
		sumd += maxi(1, (g * _SLAVE_DEM_FARM_GRAIN + w * _SLAVE_DEM_FARM_WINE + fi * _SLAVE_DEM_FARM_FISH + 9) / 10)
	for m in _mines:
		if typeof(m) != TYPE_DICTIONARY:
			continue
		var md: Dictionary = m as Dictionary
		if str(md.get("port_id", "")) != ps:
			continue
		var mt: int = maxi(0, int(md.get("metal_per_day", 0)))
		var wr: int = maxi(0, int(md.get("wire_per_day", 0)))
		var ga: int = maxi(0, int(md.get("gold_per_day", 0)))
		var sv: int = maxi(0, int(md.get("silver_per_day", 0)))
		if mt <= 0 and wr <= 0 and ga <= 0 and sv <= 0:
			continue
		sumd += maxi(
			1,
			(mt * _SLAVE_DEM_MINE_METAL + wr * _SLAVE_DEM_MINE_WIRE + ga * _SLAVE_DEM_MINE_GOLD + sv * _SLAVE_DEM_MINE_SILVER + 9)
			/ 10
		)
	return sumd


func _port_slave_output_mult(port_id: String) -> float:
	if not _goods.has("slaves"):
		return 1.0
	var dem: int = _port_slave_labor_demand(port_id)
	if dem <= 0:
		return 1.0
	var have: int = _port_stock_qty(str(port_id), "slaves")
	return clampf(float(have) / float(dem), _SLAVE_OUTPUT_FLOOR, 1.0)


func _grant_war_slave_captives(port_id: String, campaign_days: int) -> void:
	if not _goods.has("slaves"):
		return
	var ps := str(port_id)
	var cd: int = clampi(campaign_days, 1, 500)
	var jitter: int = _rng.randi_range(-_SLAVE_WAR_CAPTIVES_JITTER, _SLAVE_WAR_CAPTIVES_JITTER)
	var add: int = (
		_SLAVE_WAR_CAPTIVES_BASE
		+ jitter
		+ (cd * _SLAVE_WAR_CAPTIVES_PER_CAMPAIGN_DAY) / _SLAVE_WAR_CAPTIVES_DAY_DEN
	)
	add = maxi(0, add)
	if add <= 0:
		return
	_adjust_port_stock(ps, "slaves", add)
	var prev: Variant = _last_slave_digest.get(ps, null)
	if typeof(prev) == TYPE_DICTIONARY:
		(prev as Dictionary)["captives"] = add
	else:
		_last_slave_digest[ps] = {
			"demand": _port_slave_labor_demand(ps),
			"have_start": _port_stock_qty(ps, "slaves"),
			"lost": 0,
			"output_mult": 1.0,
			"captives": add,
		}


func _last_slave_lost_for_port(port_id: String) -> int:
	var v: Variant = _last_slave_digest.get(str(port_id), null)
	if typeof(v) != TYPE_DICTIONARY:
		return 0
	return maxi(0, int((v as Dictionary).get("lost", 0)))


func _last_slave_captives_for_port(port_id: String) -> int:
	var v: Variant = _last_slave_digest.get(str(port_id), null)
	if typeof(v) != TYPE_DICTIONARY:
		return 0
	return maxi(0, int((v as Dictionary).get("captives", 0)))


func _last_slave_output_mult_for_port(port_id: String) -> float:
	var v: Variant = _last_slave_digest.get(str(port_id), null)
	if typeof(v) == TYPE_DICTIONARY:
		return float((v as Dictionary).get("output_mult", 1.0))
	return _port_slave_output_mult(port_id)


func _tick_slave_attrition_for_ports() -> void:
	_last_slave_digest.clear()
	if not _goods.has("slaves"):
		return
	for pid in _port_names.keys():
		var ps := str(pid)
		var dem: int = _port_slave_labor_demand(ps)
		var have: int = _port_stock_qty(ps, "slaves")
		var mult0: float = _port_slave_output_mult(ps)
		var base_loss: int = int(floor(float(have) * _SLAVE_ATTRITION_FRAC))
		var gap: int = maxi(0, dem - have)
		var over_loss: int = int(ceil(float(gap) * _SLAVE_ATTRITION_OVERWORK_MUL))
		var loss: int = mini(have, base_loss + over_loss)
		if loss > 0:
			_adjust_port_stock(ps, "slaves", -loss)
		_last_slave_digest[ps] = {
			"demand": dem,
			"have_start": have,
			"lost": loss,
			"output_mult": mult0,
			"captives": 0,
		}


func _farm_breadbasket_grain_wine_mult(port_id: String) -> float:
	if str(_port_roles.get(str(port_id), "")) == _PORT_ROLE_BREADBASKET:
		return _BREADBASKET_FARM_GRAIN_WINE_MULT
	return 1.0


func _apply_farm_production() -> void:
	var wine_help_used: Dictionary = {}  # port_id -> int extra wine already added this tick
	var doy: int = _calendar_doy_1based(current_day)
	var crop_sc: float = _crop_daily_scale_for_doy(doy)
	var fish_mul: float = _season_fish_mult_for_doy(doy)
	for f in _farms:
		if typeof(f) != TYPE_DICTIONARY:
			continue
		var fd: Dictionary = f as Dictionary
		var pid := str(fd.get("port_id", ""))
		if pid.is_empty() or not _port_names.has(pid):
			continue
		var gadd: int = int(fd.get("grain_per_day", 0))
		var wadd: int = int(fd.get("wine_per_day", 0))
		var farm_mult: float = _WAR_FARM_OUTPUT_MULT if is_port_at_war(pid) else 1.0
		var pop_sc: float = _population_output_scale_for_port(pid)
		var slave_sc: float = _port_slave_output_mult(pid)
		var basket_m: float = _farm_breadbasket_grain_wine_mult(pid)
		if gadd > 0 and _goods.has("grain"):
			var yld_m: float = _crop_grain_yield_mult_for_port(pid)
			var g_ship: int = maxi(
				0,
				int(
					floor(
						float(gadd) * crop_sc * farm_mult * pop_sc * slave_sc * basket_m * _FARM_GRAIN_MASS_MULT * yld_m
					)
				),
			)
			if g_ship > 0:
				_adjust_port_stock(pid, "grain", g_ship)
		if wadd > 0 and _goods.has("wine"):
			var w_ship: int = maxi(
				0,
				int(
					floor(
						float(wadd) * crop_sc * farm_mult * pop_sc * slave_sc * basket_m
					)
				),
			)
			var used: int = int(wine_help_used.get(pid, 0))
			var extra: int = _farm_wine_help_extra(pid, used)
			wine_help_used[pid] = used + extra
			if w_ship + extra > 0:
				_adjust_port_stock(pid, "wine", w_ship + extra)
		var fadd: int = int(fd.get("fish_per_day", 0))
		if fadd > 0 and _goods.has("fish"):
			var f_ship: int = maxi(
				0,
				int(floor(float(fadd) * fish_mul * farm_mult * pop_sc * slave_sc)),
			)
			if f_ship > 0:
				_adjust_port_stock(pid, "fish", f_ship)


func _apply_mine_production() -> void:
	for m in _mines:
		if typeof(m) != TYPE_DICTIONARY:
			continue
		var md: Dictionary = m as Dictionary
		var pid := str(md.get("port_id", ""))
		if pid.is_empty() or not _port_names.has(pid):
			continue
		var madd: int = int(md.get("metal_per_day", 0))
		var wadd: int = int(md.get("wire_per_day", 0))
		var pop_sc: float = _population_output_scale_for_port(pid)
		var slave_sc: float = _port_slave_output_mult(pid)
		if madd > 0 and _goods.has("metal"):
			var m_ship: int = maxi(0, int(floor(float(madd) * pop_sc * slave_sc)))
			if m_ship > 0:
				_adjust_port_stock(pid, "metal", m_ship)
		if wadd > 0 and _goods.has("wire"):
			var w_ship: int = maxi(0, int(floor(float(wadd) * pop_sc * slave_sc)))
			if w_ship > 0:
				_adjust_port_stock(pid, "wire", w_ship)
		var gadd: int = int(md.get("gold_per_day", 0))
		if gadd > 0 and _goods.has("gold"):
			var g_ship: int = maxi(0, int(floor(float(gadd) * pop_sc * slave_sc)))
			if g_ship > 0:
				_adjust_port_stock(pid, "gold", g_ship)
		var sadd: int = int(md.get("silver_per_day", 0))
		if sadd > 0 and _goods.has("silver"):
			var s_ship: int = maxi(0, int(floor(float(sadd) * pop_sc * slave_sc)))
			if s_ship > 0:
				_adjust_port_stock(pid, "silver", s_ship)


## State mint: consume port-stock gold/silver at civic mints → treasury; treasury_sink_frac destroys part of each batch's coin credit; minting port gains small prosperity per strike (_MINT_STRIKE_*).
func _apply_mint_pulse_to_treasury() -> void:
	for pid in _port_mint_cfg.keys():
		var ps := str(pid)
		if not _port_names.has(ps):
			continue
		var cfg0: Variant = _port_mint_cfg.get(ps, null)
		if typeof(cfg0) != TYPE_DICTIONARY:
			continue
		var cfg: Dictionary = cfg0 as Dictionary
		var gb: int = clampi(int(cfg.get("gold_per_batch", 1)), 0, 24)
		var sb: int = clampi(int(cfg.get("silver_per_batch", 2)), 0, 36)
		if gb <= 0 and sb <= 0:
			continue
		var c_pb: int = clampi(int(cfg.get("coins_per_batch", 72)), 1, 500)
		var mx: int = clampi(int(cfg.get("max_batches_per_day", 6)), 1, 40)
		var sf: float = clampf(float(cfg.get("treasury_sink_frac", 0.09)), 0.0, 0.45)
		var b: int = 0
		while b < mx:
			if gb > 0 and _port_stock_qty(ps, "gold") < gb:
				break
			if sb > 0 and _port_stock_qty(ps, "silver") < sb:
				break
			if gb > 0:
				_adjust_port_stock(ps, "gold", -gb)
			if sb > 0:
				_adjust_port_stock(ps, "silver", -sb)
			_world_treasury_coins = clampi(_world_treasury_coins + c_pb, 0, _WORLD_TREASURY_MAX)
			var sk: int = maxi(0, int(floor(float(c_pb) * sf)))
			_world_treasury_coins = clampi(_world_treasury_coins - mini(sk, _world_treasury_coins), 0, _WORLD_TREASURY_MAX)
			var strike_wealth: int = clampi(
				maxi(1, int(floor(float(c_pb) * _MINT_STRIKE_WEALTH_FRAC))), 1, _MINT_STRIKE_WEALTH_BONUS_MAX
			)
			_bump_port_wealth(ps, strike_wealth)
			b += 1


func _luxury_import_far_good_ids() -> Array[String]:
	var out: Array[String] = []
	for gid in _goods.keys():
		var g := str(gid)
		if _need_tier_for_good(g) != "luxury":
			continue
		if g == "gold" or g == "silver":
			continue
		out.append(g)
	return out


func _luxury_import_apply_coin_sink(port_id: String, sink_total: int) -> void:
	var ps := str(port_id)
	if sink_total <= 0 or not _port_names.has(ps):
		return
	var ttf: float = clampf(
		float(_luxury_import_cfg.get("treasury_take_frac", _LUXURY_IMPORT_TREASURY_TAKE_FRAC_DEFAULT)), 0.0, 0.95
	)
	var from_t: int = mini(_world_treasury_coins, int(ceil(float(sink_total) * ttf)))
	_world_treasury_coins = clampi(_world_treasury_coins - from_t, 0, _WORLD_TREASURY_MAX)
	var remain: int = sink_total - from_t
	if remain <= 0:
		return
	var docked: Array = []
	for item in _npc_agents:
		if typeof(item) != TYPE_DICTIONARY:
			continue
		var ag: Dictionary = item as Dictionary
		if int(ag.get("voyage_days_remaining", 0)) > 0:
			continue
		if str(ag.get("docked_port", "")) != ps:
			continue
		docked.append(ag)
	var guard: int = 0
	while remain > 0 and guard < 500:
		guard += 1
		var progressed: bool = false
		for ag2 in docked:
			var purse0: int = clampi(int(ag2.get("money", 0)), 0, _MAX_PURSE_COINS)
			var headroom: int = purse0 - _NPC_PURSE_RESERVE - 1
			if headroom <= 0:
				continue
			var slice: int = mini(remain, maxi(1, headroom / 3))
			slice = mini(slice, headroom)
			if slice <= 0:
				continue
			ag2["money"] = clampi(purse0 - slice, 0, _MAX_PURSE_COINS)
			remain -= slice
			progressed = true
		if not progressed:
			break
	if remain > 0:
		var pv: int = maxi(0, int(_port_wealth.get(ps, 0)) - 22)
		if pv > 0:
			_bump_port_wealth(ps, -mini(pv, remain))


func _luxury_import_tick() -> void:
	if not bool(_luxury_import_cfg.get("enabled", true)):
		return
	var any_arrival: bool = false
	for pid in _port_names.keys():
		var ps := str(pid)
		var arr0: Variant = _port_luxury_import_queue.get(ps, null)
		if typeof(arr0) != TYPE_ARRAY:
			continue
		var arr: Array = arr0 as Array
		var i: int = 0
		while i < arr.size():
			var c0: Variant = arr[i]
			if typeof(c0) != TYPE_DICTIONARY:
				arr.remove_at(i)
				continue
			var cell: Dictionary = c0 as Dictionary
			var d0: int = int(cell.get("d", 0)) - 1
			cell["d"] = d0
			if d0 > 0:
				i += 1
				continue
			var gid := str(cell.get("g", ""))
			var qv: int = maxi(0, int(cell.get("q", 0)))
			arr.remove_at(i)
			if not _goods.has(gid) or qv <= 0:
				continue
			var unit0: int = _compute_player_buy_unit(ps, gid, false)
			var notional: int = maxi(1, qv * maxi(1, unit0))
			var cfrac: float = clampf(float(_luxury_import_cfg.get("cost_frac", _LUXURY_IMPORT_COST_FRAC_DEFAULT)), 0.05, 0.88)
			var sink_total: int = clampi(
				int(floor(float(notional) * cfrac)), 1, _LUXURY_IMPORT_SINK_CAP
			)
			_luxury_import_apply_coin_sink(ps, sink_total)
			_adjust_port_stock(ps, gid, qv)
			any_arrival = true
	var mxq: int = clampi(int(_luxury_import_cfg.get("max_pending", 4)), 1, 12)
	var spawn_roll: float = clampf(float(_luxury_import_cfg.get("spawn_roll", 0.10)), 0.0, 0.6)
	var lead_lo: int = clampi(int(_luxury_import_cfg.get("lead_min", 3)), 1, 30)
	var lead_hi: int = clampi(int(_luxury_import_cfg.get("lead_max", 8)), lead_lo, 40)
	var q_lo: int = clampi(int(_luxury_import_cfg.get("qty_min", 1)), 1, 12)
	var q_hi: int = clampi(int(_luxury_import_cfg.get("qty_max", 3)), q_lo, 16)
	var cands: Array[String] = _luxury_import_far_good_ids()
	if not cands.is_empty():
		for pid2 in _port_names.keys():
			var ps2 := str(pid2)
			if _rng.randf() > spawn_roll * clampf(0.28 + float(_port_commerce_pulse.get(ps2, 0.38)) * 1.05, 0.18, 1.2):
				continue
			var arr2: Array = _port_luxury_import_queue.get(ps2, []) as Array
			if arr2.size() >= mxq:
				continue
			var pick_g: String = str(cands[_rng.randi_range(0, cands.size() - 1)])
			if not _goods.has(pick_g):
				continue
			var tgt: int = _stock_target_for_good(pick_g)
			var stk: int = _port_stock_qty(ps2, pick_g)
			var tight: float = float(stk) / float(maxi(1, tgt))
			if tight > 1.08 and _rng.randf() < 0.72:
				continue
			var qn: int = _rng.randi_range(q_lo, q_hi)
			var ld: int = _rng.randi_range(lead_lo, lead_hi)
			if not _port_luxury_import_queue.has(ps2):
				_port_luxury_import_queue[ps2] = []
			var slot: Array = _port_luxury_import_queue[ps2] as Array
			slot.append({"g": pick_g, "q": qn, "d": ld})
	if any_arrival:
		market_changed.emit()


func _wealth_stock_target_value(port_id: String) -> float:
	## Bullion is intentionally excluded from this attractor (granary gold/silver != municipal prosperity)—do not re-linearize it here.
	if not _port_names.has(port_id):
		return 45.0
	var g: float = float(_port_stock_qty(port_id, "grain"))
	var w: float = float(_port_stock_qty(port_id, "wine"))
	var mt: float = float(_port_stock_qty(port_id, "metal")) if _goods.has("metal") else 0.0
	var wr: float = float(_port_stock_qty(port_id, "wire")) if _goods.has("wire") else 0.0
	var sa: float = float(_port_stock_qty(port_id, "salt")) if _goods.has("salt") else 0.0
	var oo: float = float(_port_stock_qty(port_id, "olive_oil")) if _goods.has("olive_oil") else 0.0
	var po: float = float(_port_stock_qty(port_id, "pottery")) if _goods.has("pottery") else 0.0
	var sp: float = float(_port_stock_qty(port_id, "spice")) if _goods.has("spice") else 0.0
	var sl: float = float(_port_stock_qty(port_id, "slaves")) if _goods.has("slaves") else 0.0
	var fi: float = float(_port_stock_qty(port_id, "fish")) if _goods.has("fish") else 0.0
	var tb: float = float(_port_stock_qty(port_id, "timber")) if _goods.has("timber") else 0.0
	var tx: float = float(_port_stock_qty(port_id, "textiles")) if _goods.has("textiles") else 0.0
	var rb: float = float(maxi(0, int(_port_role_wealth_bonus.get(port_id, 0))))
	var target: float = (
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
	var pulse: float = clampf(float(_port_commerce_pulse.get(port_id, 0.38)), 0.0, 1.0)
	target *= _SimAgents.wealth_target_commerce_scale(pulse)
	if clampi(int(_port_plague_days.get(port_id, 0)), 0, 999) > 0:
		target *= _SimAgents.PLAGUE_TARGET_MULT
	return clampf(target, 35.0, 8000.0)


func _wealth_stock_target_for_port(port_id: String) -> int:
	return int(round(_wealth_stock_target_value(port_id)))


func _refresh_port_wealth(port_id: String) -> void:
	if not _port_names.has(port_id):
		return
	var target: float = _wealth_stock_target_value(port_id)
	var cur: float = float(int(_port_wealth.get(port_id, int(round(target)))))
	var nxt: float = lerpf(cur, target, _WEALTH_LERP)
	_port_wealth[port_id] = clampi(int(round(nxt)), 25, 999999)


func _bump_port_wealth(port_id: String, delta: int) -> void:
	if not _port_names.has(port_id) or delta == 0:
		return
	var v: int = int(_port_wealth.get(port_id, 200)) + delta
	_port_wealth[port_id] = clampi(v, 10, 999999)


## Headless benchmarks: snapshot while player is idle (no UI). Ports keyed by id string.
func get_simulation_metrics() -> Dictionary:
	var ports: Dictionary = {}
	for pid in _port_names.keys():
		var ps := str(pid)
		var gdays: float = 9999.0
		if _goods.has("grain"):
			var eatm: int = get_population_grain_eat_effective(ps)
			if eatm > 0:
				gdays = float(_port_stock_qty(ps, "grain")) / float(eatm)
		var sm: int = _port_stock_qty(ps, "metal") if _goods.has("metal") else 0
		var swr: int = _port_stock_qty(ps, "wire") if _goods.has("wire") else 0
		var sau: int = _port_stock_qty(ps, "gold") if _goods.has("gold") else 0
		var sag: int = _port_stock_qty(ps, "silver") if _goods.has("silver") else 0
		var isink_m: int = 0
		var isink_w: int = 0
		var isink_tb: int = 0
		var isink_tx: int = 0
		var idsink: Variant = _last_industrial_sink_digest.get(ps, null)
		if typeof(idsink) == TYPE_DICTIONARY:
			isink_m = int((idsink as Dictionary).get("metal", 0))
			isink_w = int((idsink as Dictionary).get("wire", 0))
			isink_tb = int((idsink as Dictionary).get("timber", 0))
			isink_tx = int((idsink as Dictionary).get("textiles", 0))
		ports[ps] = {
			"wealth": int(_port_wealth.get(ps, 0)),
			"stock_grain": _port_stock_qty(ps, "grain"),
			"stock_wine": _port_stock_qty(ps, "wine"),
			"stock_metal": sm,
			"stock_wire": swr,
			"stock_gold": sau,
			"stock_silver": sag,
			"attractor": _wealth_stock_target_for_port(ps),
			"grain_spoiled": int(_last_grain_spoilage.get(ps, 0)),
			"grain_food_days": gdays,
			"food_unrest": get_port_food_unrest(ps),
			"food_unrest_mood": _food_unrest_tier_label(get_port_food_unrest(ps)),
			"population_grain": int(_port_population_grain.get(ps, 0)),
			"population_grain_cap": int(_port_population_grain_cap.get(ps, 0)),
			"famine_streak_days": int(_port_famine_streak_days.get(ps, 0)),
			"prosperity_streak_days": int(_port_prosperity_streak_days.get(ps, 0)),
			"population_output_scale": _population_output_scale_for_port(ps),
			"at_war": is_port_at_war(ps),
			"war_days_left": get_port_war_days_remaining(ps),
			"war_recurring": bool(_port_war_recurring.get(ps, false)),
			"war_peace_days": int(_port_war_peace_remaining.get(ps, 0)),
			"npc_docked": _count_npc_docked_at(ps),
			"commerce_pulse": clampf(float(_port_commerce_pulse.get(ps, 0.0)), 0.0, 1.0),
			"cartel_strength": clampf(float(_port_cartel_strength.get(ps, 0.0)), 0.0, 1.0),
			"war_rumor": clampf(float(_port_war_rumor.get(ps, 0.0)), 0.0, 1.0),
			"plague_days": clampi(int(_port_plague_days.get(ps, 0)), 0, 999),
			"npc_inbound": _count_npc_sailing_toward(ps),
			"industrial_metal_sink": isink_m,
			"industrial_wire_sink": isink_w,
			"industrial_timber_sink": isink_tb,
			"industrial_textiles_sink": isink_tx,
			"slave_labor_demand": _port_slave_labor_demand(ps) if _goods.has("slaves") else 0,
			"stock_slaves": _port_stock_qty(ps, "slaves") if _goods.has("slaves") else 0,
			"slave_output_mult": _last_slave_output_mult_for_port(ps) if _goods.has("slaves") else 1.0,
			"slaves_lost_last_tick": _last_slave_lost_for_port(ps) if _goods.has("slaves") else 0,
			"slave_war_captives_last_tick": _last_slave_captives_for_port(ps) if _goods.has("slaves") else 0,
			"crop_moisture_01": clampf(float(_port_crop_moisture_01.get(ps, 0.5)), 0.0, 1.0),
			"crop_growth_01": clampf(float(_port_crop_growth_01.get(ps, 0.5)), 0.0, 1.0),
			"crop_stress_01": _crop_grain_stress_01_for_port(ps),
			"crop_stress_market_01": _crop_grain_stress_01_market_for_port(ps),
			"crop_belief_local_01": clampf(float(_port_local_crop_belief_01.get(ps, _crop_grain_stress_gt_01_for_port(ps))), 0.0, 1.0),
			"crop_inbound_reports_n": _port_crop_inbound_report_count(ps),
			"crop_grain_yield_mult": _crop_grain_yield_mult_for_port(ps),
			"crop_phase2_major": 1 if _crop_phase2_stress_major_gate(ps) else 0,
			"crop_phase2_bias_add": _crop_phase2_grain_trade_bias_add(ps),
			"crop_phase2_hoard_01": _crop_phase2_npc_hoard_weight_01(ps),
		}
	var npc_money: int = 0
	var npc_at_sea: int = 0
	for item in _npc_agents:
		if typeof(item) != TYPE_DICTIONARY:
			continue
		var ag: Dictionary = item as Dictionary
		npc_money += clampi(int(ag.get("money", 0)), 0, _MAX_PURSE_COINS)
		if int(ag.get("voyage_days_remaining", 0)) > 0:
			npc_at_sea += 1
	return {
		"day": current_day,
		"calendar_doy": get_calendar_day_of_year(),
		"calendar_season": get_calendar_season_name(),
		"calendar_year": get_calendar_year_index(),
		"player_money": player_money,
		"world_treasury_coins": clampi(_world_treasury_coins, 0, _WORLD_TREASURY_MAX),
		"player_port": player_port_id,
		"player_fleet_ships": get_player_fleet_ships(),
		"player_fleet_shipyard_days_remaining": clampi(player_fleet_shipyard_days_remaining, 0, 999),
		"player_fleet_shipyard_port_id": str(player_fleet_shipyard_port_id),
		"player_cargo_capacity": get_player_cargo_capacity(),
		"player_ship_condition": clampi(player_ship_condition, _SHIP_CONDITION_MIN, _SHIP_CONDITION_MAX),
		"player_at_sea": is_at_sea(),
		"ports": ports,
		"npc_agent_count": _npc_agents.size(),
		"npc_at_sea": npc_at_sea,
		"npc_total_money": npc_money,
		"pirate_encounter_attempts": _pirate_metrics_attempts,
		"pirate_raids_success": _pirate_metrics_raids,
		"pirate_escort_flees": _pirate_metrics_flees,
		"pirate_marines_lost": _pirate_metrics_marines_lost,
		"pirate_loot_coins": _pirate_metrics_loot_coins,
		"escort_player_coins_paid": _escort_player_coins_paid,
		"player_offers_convoy_escort": player_offers_convoy_escort,
		"player_crop_intel_mean_01": clampf(player_crop_intel_mean_01, 0.0, 1.0),
		"player_crop_intel_sigma_01": clampf(player_crop_intel_sigma_01, 0.0, 1.0),
		"player_crop_intel_update_day": player_crop_intel_update_day,
		"player_war_intel_mean_01": clampf(player_war_intel_mean_01, 0.0, 1.0),
		"player_war_intel_sigma_01": clampf(player_war_intel_sigma_01, 0.0, 1.0),
		"player_war_intel_update_day": player_war_intel_update_day,
		"player_civic_reputation_01": clampf(player_civic_reputation_01, 0.0, 1.0),
	}


## Admin / debug: full plain-text snapshot of every port, stock, and each NPC hold.
func get_admin_world_dump() -> String:
	var lines: PackedStringArray = []
	lines.append("Harbours of Power — admin snapshot (day %d)" % current_day)
	lines.append(
		"Player: money=%d  port=%s  at_sea=%s  fleet=%d ships  cargo=%d/%d  ship_condition=%d/%d  wine_counter=%d  shipyard_days=%d shipyard_port=%s"
		% [
			player_money,
			player_port_id,
			str(is_at_sea()),
			get_player_fleet_ships(),
			get_player_cargo_used(),
			get_player_cargo_capacity(),
			clampi(player_ship_condition, _SHIP_CONDITION_MIN, _SHIP_CONDITION_MAX),
			_SHIP_CONDITION_MAX,
			player_ship_wine_counter,
			player_fleet_shipyard_days_remaining,
			player_fleet_shipyard_port_id,
		]
	)
	lines.append("Player cargo: %s" % get_cargo_summary())
	lines.append(get_ship_status_line())
	var sc_adm: Vector2i = _npc_scattered_convoy_tail_stats()
	lines.append(
		(
			"NPC convoy scatter: %d merchant leader(s), %d detached id(s) in scattered_ids "
			+ "(~%.0f%%/d one id may drop; docked contact_bias ×%.2f/d toward 0)."
		)
		% [
			sc_adm.x,
			sc_adm.y,
			_SCATTERED_IDS_DECAY_DAILY_P * 100.0,
			_NPC_CONTACT_BIAS_DOCKED_DECAY_MULT,
		]
	)
	if not _last_food_riot_summary.is_empty():
		lines.append("Last tick grain riot(s): %s" % _last_food_riot_summary)
	lines.append("")
	lines.append("— Farmland (daily → port stock) —")
	if _farms.is_empty():
		lines.append("(none)")
	else:
		for f in _farms:
			if typeof(f) != TYPE_DICTIONARY:
				continue
			var fd: Dictionary = f as Dictionary
			lines.append(
				"  %s → %s  +%d grain / +%d wine"
				% [
					str(fd.get("name", fd.get("id", "?"))),
					str(fd.get("port_id", "?")),
					int(fd.get("grain_per_day", 0)),
					int(fd.get("wine_per_day", 0)),
				]
			)
	lines.append("")
	lines.append("— Mines (daily → port stock) —")
	if _mines.is_empty():
		lines.append("(none)")
	else:
		for m in _mines:
			if typeof(m) != TYPE_DICTIONARY:
				continue
			var md: Dictionary = m as Dictionary
			lines.append(
				"  %s → %s  +%d metal / +%d wire"
				% [
					str(md.get("name", md.get("id", "?"))),
					str(md.get("port_id", "?")),
					int(md.get("metal_per_day", 0)),
					int(md.get("wire_per_day", 0)),
				]
			)
	lines.append("")
	lines.append(
		(
			"Wealth note: each day prosperity lerps toward a stock-derived attractor (grain, wine, salt, olive oil, pottery, fish, timber, textiles, metal, wire, spice, slaves weighted). initial_wealth in world data above that curve decays until it aligns. Player dock trades: stock-skewed bid/ask; need_tier uses smooth reservation curves (grain/wine: steeper for the player counterparty than NPC wholesale). Luxury tier adds wealth+mean-lane far-trade markup. Wine also gets cover-day supply/demand price pressure and same-day vineyard help (+0–3/port) when stocks are empty/tight. Metal=scaled food stress; optional per-port industrial_*_per_day (world.json) drains metal, wire, timber, textiles for workshops & shipyards before war materiel. Population eats fish from port stock when population_fish_per_day is set; farms may ship fish_per_day. Slave labor: port `slaves` stock vs farm+mine labor demand scales daily farm/mine output; attrition removes slaves; when a campaign ends (hostilities tick to 0) captives add to the port slave market. Each port defaults to its own random war cycle (peace %d–%d d, then hostilities %d–%d d; world.json war_recurring: false opts out). Optional at_war + war_days starts a port mid-campaign. While at war: farm grain/wine to port is reduced, grain ration up, metal-tier prices up, extra ingots + wire drawn (wire = rigging; large piles skim faster). Coin sinks: dock trade friction on each buy/sell (coins destroyed). Daily harbour dues when berthed (fleet + capped purse levy) leave the captain and raise port prosperity; busier quays (more berthed merchants that day) increase the port wealth bump per coin. NPCs trade vs port at wholesale buy/sell multipliers with a modest purse reserve so trade can net coins. NPC wine restock slightly earlier vs stock ratio. Grain granary rot/vermin (capped). Population headcount drifts with sustained famine vs sustained prosperity; farm/mine daily output scales with population vs founding cohort from world.json."
			% [_WAR_CYCLE_PEACE_MIN, _WAR_CYCLE_PEACE_MAX, _WAR_RECURRING_BURST_MIN, _WAR_RECURRING_BURST_MAX]
		)
	)
	lines.append("— NPC merchants (home port + travel) —")
	if _npc_agents.is_empty():
		lines.append("(none)")
	else:
		var sorted_agents: Array = _npc_agents.duplicate()
		sorted_agents.sort_custom(
			func(a: Variant, b: Variant) -> bool:
				if typeof(a) != TYPE_DICTIONARY or typeof(b) != TYPE_DICTIONARY:
					return false
				return int((a as Dictionary).get("id", 0)) < int((b as Dictionary).get("id", 0))
		)
		for item in sorted_agents:
			if typeof(item) != TYPE_DICTIONARY:
				continue
			var ag: Dictionary = item as Dictionary
			var aid: int = int(ag.get("id", -1))
			var cargo_line: String = _format_admin_cargo(ag.get("cargo", null))
			var state_s: String
			var days: int = int(ag.get("voyage_days_remaining", 0))
			if days > 0:
				state_s = "at sea → %s (%d d left)" % [str(ag.get("voyage_dest_id", "?")), days]
			else:
				state_s = "docked %s (home %s)" % [str(ag.get("docked_port", "?")), str(ag.get("home_port", "?"))]
			var purse: int = clampi(int(ag.get("money", 0)), 0, _MAX_PURSE_COINS)
			var bm: float = clampf(float(ag.get("buy_mastery", 1.0)), _NPC_MASTER_MIN, _NPC_MASTER_MAX)
			var sm: float = clampf(float(ag.get("sell_mastery", 1.0)), _NPC_MASTER_MIN, _NPC_MASTER_MAX)
			var scatter_s: String = ""
			var scv_ad: Variant = ag.get("scattered_ids", null)
			if typeof(scv_ad) == TYPE_ARRAY:
				var sca_ad: Array = scv_ad as Array
				if not sca_ad.is_empty():
					var id_bits: PackedStringArray = []
					var lim_ad: int = mini(6, sca_ad.size())
					for sii in range(lim_ad):
						id_bits.append(str(int(sca_ad[sii])))
					var more_ad: String = (
						"+%d" % (sca_ad.size() - lim_ad) if sca_ad.size() > lim_ad else ""
					)
					scatter_s = " scatter[%s%s]" % [",".join(id_bits), more_ad]
			var cb_ad: float = clampf(float(ag.get("contact_candidate_bias", 0.0)), 0.0, 1.0)
			var bias_s: String = (" c_bias=%.2f" % cb_ad) if cb_ad >= 0.02 else ""
			lines.append(
				"  id %d  %s  |  purse %d  buy %.2f sell %.2f%s%s  |  %s"
				% [aid, state_s, purse, bm, sm, scatter_s, bias_s, cargo_line]
			)
	lines.append("")
	var port_ids: Array = _port_names.keys()
	port_ids.sort_custom(func(a, b) -> bool: return str(a) < str(b))
	for pid in port_ids:
		var pid_s := str(pid)
		var pname: String = get_port_name(pid_s)
		lines.append("=== %s (%s) ===" % [pname, pid_s])
		var eat: int = get_population_grain_eat_effective(pid_s)
		var eat_base: int = int(_port_population_grain.get(pid_s, 0))
		var w_base: int = int(_port_population_wine_base.get(pid_s, 0))
		var wealth: int = int(_port_wealth.get(pid_s, 0))
		var w_tick0: Variant = _wealth_snapshot_tick_start.get(pid_s, null)
		var t_tick0: Variant = _wealth_stock_target_tick_start.get(pid_s, null)
		var attract_now: int = _wealth_stock_target_for_port(pid_s)
		var w0_s: String = "—"
		var t0_s: String = "—"
		if w_tick0 != null:
			w0_s = str(int(w_tick0))
		if t_tick0 != null:
			t0_s = str(int(t_tick0))
		var dig: Variant = _last_pop_digest.get(pid_s, null)
		var dg_s: String = "—"
		if typeof(dig) == TYPE_DICTIONARY:
			var dg: Dictionary = dig as Dictionary
			dg_s = "last bite grain %d wine %d fish %d" % [
				int(dg.get("grain", 0)),
				int(dg.get("wine", 0)),
				int(dg.get("fish", 0)),
			]
		var n_cfg: int = int(_port_npc_trader_count.get(pid_s, 0))
		var n_d: int = _count_npc_docked_at(pid_s)
		var n_in: int = _count_npc_sailing_toward(pid_s)
		var eat_line: String = "%d" % eat
		if eat != eat_base:
			eat_line = "%d (peace ration %d)" % [eat, eat_base]
		lines.append(
			"Population grain/day: %s  wine base/day: %d  wealth now: %d  tick-start wealth: %s  tick-start stock→attractor: %s  attractor(now stocks): %d  (%s)  npc home: %d  docked: %d  inbound: %d"
			% [eat_line, w_base, wealth, w0_s, t0_s, attract_now, dg_s, n_cfg, n_d, n_in]
		)
		var st_bits: PackedStringArray = []
		for gid in _goods.keys():
			var gis := str(gid)
			st_bits.append("%s %d" % [get_good_name(gis), _port_stock_qty(pid_s, gis)])
		lines.append("Port stock: " + ", ".join(st_bits))
		var spoil_ad: int = int(_last_grain_spoilage.get(pid_s, 0))
		lines.append("Granary (last tick): grain lost to rot/vermin: %d" % spoil_ad)
		if _goods.has("slaves"):
			var sld: Variant = _last_slave_digest.get(pid_s, null)
			if typeof(sld) == TYPE_DICTIONARY:
				var sdd: Dictionary = sld as Dictionary
				var wc: int = int(sdd.get("captives", 0))
				var cap_s: String = ("; war captives onto market +%d" % wc) if wc > 0 else ""
				lines.append(
					"Slave economy (last tick): labor demand %d, stock start %d, farm/mine output ×%.2f, attrition −%d%s"
					% [
						int(sdd.get("demand", 0)),
						int(sdd.get("have_start", 0)),
						float(sdd.get("output_mult", 1.0)),
						int(sdd.get("lost", 0)),
						cap_s,
					]
				)
			else:
				lines.append(
					"Slave economy: labor demand %d, stock %d (no attrition digest yet this session)."
					% [_port_slave_labor_demand(pid_s), _port_stock_qty(pid_s, "slaves")]
				)
		var ind_m_cfg: int = int(_port_industrial_metal_per_day.get(pid_s, 0))
		var ind_w_cfg: int = int(_port_industrial_wire_per_day.get(pid_s, 0))
		var ind_t_cfg: int = int(_port_industrial_timber_per_day.get(pid_s, 0))
		var ind_x_cfg: int = int(_port_industrial_textiles_per_day.get(pid_s, 0))
		if ind_m_cfg > 0 or ind_w_cfg > 0 or ind_t_cfg > 0 or ind_x_cfg > 0:
			lines.append(
				"Industrial demand (world.json): %d metal, %d wire, %d timber, %d textiles / day (draw capped by stock)."
				% [ind_m_cfg, ind_w_cfg, ind_t_cfg, ind_x_cfg]
			)
			var isd: Variant = _last_industrial_sink_digest.get(pid_s, null)
			var ism: int = 0
			var isw: int = 0
			var ist: int = 0
			var isx: int = 0
			if typeof(isd) == TYPE_DICTIONARY:
				ism = int((isd as Dictionary).get("metal", 0))
				isw = int((isd as Dictionary).get("wire", 0))
				ist = int((isd as Dictionary).get("timber", 0))
				isx = int((isd as Dictionary).get("textiles", 0))
			lines.append(
				"Industrial sinks (last tick): %d metal, %d wire, %d timber, %d textiles." % [ism, isw, ist, isx]
			)
		var gfd: float = float(_last_grain_food_days.get(pid_s, get_grain_food_days_for_port(pid_s)))
		var fu_ad: int = get_port_food_unrest(pid_s)
		var thr_ad: int = _food_riot_threshold_for_port(pid_s)
		var tier_ad: String = _food_unrest_tier_label(fu_ad)
		var pbase: int = int(_port_population_grain_baseline.get(pid_s, eat_base))
		var pcap: int = int(_port_population_grain_cap.get(pid_s, eat_base + _POP_GRAIN_CEILING_BOOST))
		var fst: int = clampi(int(_port_famine_streak_days.get(pid_s, 0)), 0, 999)
		var pst: int = clampi(int(_port_prosperity_streak_days.get(pid_s, 0)), 0, 999)
		var psc: float = _population_output_scale_for_port(pid_s)
		lines.append(
			"Grain runway (stock÷ration, end of last tick): %.2f d  |  food unrest: %d / 200  mood: %s  (riot checks near ≥%d)"
			% [gfd, fu_ad, tier_ad, thr_ad]
		)
		lines.append(
			"Population v1: grain mouths %d (baseline %d, cap %d); famine streak %d d; prosperity streak %d d; farm/mine output scale ×%.2f."
			% [eat_base, pbase, pcap, fst, pst, psc]
		)
		if bool(_port_war_recurring.get(pid_s, false)):
			if is_port_at_war(pid_s):
				lines.append(
					"War cycle: recurring — at war (%d d left in this campaign; next quiet spell %d–%d d after it ends)."
					% [
						get_port_war_days_remaining(pid_s),
						_WAR_CYCLE_PEACE_MIN,
						_WAR_CYCLE_PEACE_MAX,
					]
				)
			else:
				lines.append(
					"War cycle: recurring — %d d quiet, then next campaign %d–%d d."
					% [
						int(_port_war_peace_remaining.get(pid_s, 0)),
						_WAR_RECURRING_BURST_MIN,
						_WAR_RECURRING_BURST_MAX,
					]
				)
		if is_port_at_war(pid_s):
			lines.append(
				"War: active — %d day(s) left; farm grain/wine to port ×%.2f; population grain ration ×%.2f while hostilities last."
				% [get_port_war_days_remaining(pid_s), _WAR_FARM_OUTPUT_MULT, _WAR_GRAIN_RATION_MULT]
			)
			var wad: Variant = _last_war_industry_digest.get(pid_s, null)
			var wm_a: int = 0
			var ww_a: int = 0
			if typeof(wad) == TYPE_DICTIONARY:
				wm_a = int((wad as Dictionary).get("metal", 0))
				ww_a = int((wad as Dictionary).get("wire", 0))
			lines.append("War materiel (last tick): %d metal, %d wire." % [wm_a, ww_a])
		lines.append("")
	return "\n".join(lines)


func _format_admin_cargo(cargo_raw: Variant) -> String:
	if typeof(cargo_raw) != TYPE_DICTIONARY:
		return "(empty hold)"
	var cargo: Dictionary = cargo_raw as Dictionary
	if cargo.is_empty():
		return "(empty hold)"
	var bits: PackedStringArray = []
	var keys: Array = cargo.keys()
	keys.sort_custom(func(a, b) -> bool: return str(a) < str(b))
	for gk in keys:
		var gid := str(gk)
		var q: int = maxi(0, int(cargo[gk]))
		if q <= 0:
			continue
		bits.append("%s x%d" % [get_good_name(gid), q])
	if bits.is_empty():
		return "(empty hold)"
	return ", ".join(bits)

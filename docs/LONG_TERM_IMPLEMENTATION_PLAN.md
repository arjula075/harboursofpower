# Harbours of Power — long-term implementation plan

Living roadmap for simulation depth, UI, and data. **Update this file** when a milestone ships or priorities shift.

## Recently completed

| Area | Notes |
|------|--------|
| City locations UI | Docked play split across Tavern … Beacon; intel blocks + escort-offer checkbox in Tavern (`ui/main.gd`, `game_state.gd` helpers). |
| Display / layout | Larger window, stretch, TradeScroll ratio (`project.godot`, scenes). |
| Calendar & seasons | 360-day year, harvest window, off-season crop drip, seasonal storms at sea, summer war deferral, fish/wine tuning, `SAVE_VERSION` / save fields (`game_state.gd`, `sim_100_days.py`, canvas). |
| Breadbasket ports | Role `breadbasket`, wealth bonus, ×1.15 farm grain & wine into port (`data/world.json`, twin, canvas). |
| At-sea voyage readout | `get_player_voyage_intel_block()` + `_player_daily_storm_probability()`; city panel title "Under way" (`game_state.gd`, `ui/main.gd`). |
| Convoy scatter slice 1 | Tavern rumour + admin summary for global `scattered_ids` tail counts. |
| Convoy scatter slice 2 | Daily decay: random id removed from `scattered_ids` (p≈7%); docked `contact_candidate_bias` ×0.93/d toward 0; admin per-NPC `scatter[…]` + `c_bias=`; tavern explains bias when scatter gossip shows (`game_state.gd`, `sim_100_days.py`). |

## Convoy / piracy phases (see `game_state.gd` header)

| Phase | Status | Follow-up |
|-------|--------|-----------|
| 1 — Roles + escort scaffold | Done | — |
| 2 — NPC merchant convoys | Done | Optional: encounter-chain UI from `scattered_ids` |
| 3 — Escort pay on convoy arrival | Done | — |
| 4 — NPC pirates, boarding, loot | Done | Balance passes from sim metrics |
| 5 — Player merchant vs pirates at sea | Done | Optional: dedicated encounter log panel |
| 6 — Player hired as NPC convoy escort | Done | — |

## Economy & twin

- Keep `tools/sim_100_days.py` aligned with `game_state.gd` for any tick-order or constant change.
- After behaviour changes: run `python3 tools/sim_100_days.py 10000 --no-graphs` and refresh `harbours-economy-rules.canvas.tsx` when rules change.

## Backlog (ordered roughly by dependency / player value)

1. **Location-specific actions** — Temple / Shipwright / Bank / Baths / Works / Beacon: mechanics beyond flavour where design allows.
2. **Player encounter log** — Scrollable strip or dock panel for last N sea events (storms, pirates, escort pay).
3. **Save migration hardening** — Regression tests for `SAVE_VERSION` bumps.
4. **Playtest / balance** — Grain-days, riots, bankruptcies vs design targets after major economy edits.

## Current focus

**Next:** Location-specific actions (light mechanics at city sites), or **player encounter log** if sea UX is the priority.

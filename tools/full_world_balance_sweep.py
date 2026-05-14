#!/usr/bin/env python3
"""
Batch-run the Python twin on `data/world_full.json` with full NPC density/mass (1.0)
and compare grain stress vs aggregate economy growth.

Usage (repo root):
  python3 tools/full_world_balance_sweep.py
  python3 tools/full_world_balance_sweep.py --quick              # 3 scenarios × 240 ticks
  python3 tools/full_world_balance_sweep.py --days 1200          # longer per scenario

Does not modify game_state.gd — for tuning ideas only until constants are ported.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import tools.sim_100_days as twin  # noqa: E402


def _restore_tunables(
    wealth_lerp: float,
    commerce_wealth_target_coef: float,
    grain_spoil_fraction: float,
) -> None:
    twin._WEALTH_LERP = wealth_lerp
    twin._COMMERCE_WEALTH_TARGET_COEF = commerce_wealth_target_coef
    twin._GRAIN_SPOIL_FRACTION = grain_spoil_fraction


def _run_once(days: int) -> dict:
    rng = random.Random(twin._RNG_SEED)
    sim = twin.Sim(rng)
    sim.load()
    m0 = sim.metrics()
    ports0 = m0.get("ports") or {}
    min_grain_seen = 99999.0
    max_unrest_seen = 0
    for _ in range(days):
        sim.advance_day()
        for pid in sim.port_order:
            max_unrest_seen = max(max_unrest_seen, sim.get_port_food_unrest(pid))
            gf = sim.get_grain_food_days_for_port(pid)
            if gf < 9000.0:
                min_grain_seen = min(min_grain_seen, gf)
    m1 = sim.metrics()
    ports1 = m1.get("ports") or {}

    w0 = sum(int((ports0.get(pid) or {}).get("wealth", 0)) for pid in sim.port_order)
    w1 = sum(int((ports1.get(pid) or {}).get("wealth", 0)) for pid in sim.port_order)
    g0 = sum(int((ports0.get(pid) or {}).get("stock_grain", 0)) for pid in sim.port_order)
    g1 = sum(int((ports1.get(pid) or {}).get("stock_grain", 0)) for pid in sim.port_order)

    inv0 = int(m0.get("npc_total_investment_wealth_coins", 0))
    inv1 = int(m1.get("npc_total_investment_wealth_coins", 0))
    mny0 = int(m0.get("npc_total_money", 0))
    mny1 = int(m1.get("npc_total_money", 0))
    bs0 = int(m0.get("npc_total_balance_sheet_coins", mny0 + inv0))
    bs1 = int(m1.get("npc_total_balance_sheet_coins", mny1 + inv1))

    end_grain_days = [
        float((ports1.get(pid) or {}).get("grain_food_days", 9999.0)) for pid in sim.port_order
    ]
    med_end_days = sorted(end_grain_days)[len(end_grain_days) // 2]

    return {
        "agents": len(sim.npc_agents),
        "hulls": sum(int(a.get("fleet_ships", 1)) for a in sim.npc_agents),
        "riots": int(sim.riot_events),
        "bankruptcies": int(sim.bankruptcy_events),
        "min_grain_days_seen": float(min_grain_seen) if min_grain_seen < 9000.0 else 99999.0,
        "median_end_grain_days": float(med_end_days),
        "max_unrest_seen": int(max_unrest_seen),
        "sum_wealth_delta": int(w1 - w0),
        "sum_grain_stock_delta": int(g1 - g0),
        "npc_balance_sheet_delta": int(bs1 - bs0),
        "world_treasury_end": int(m1.get("world_treasury_coins", 0)),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--days",
        type=int,
        default=800,
        help="Ticks per scenario (default 800; full world is ~1.3s/tick on a laptop).",
    )
    ap.add_argument(
        "--quick",
        action="store_true",
        help="240 ticks, three scenarios (sanity).",
    )
    args = ap.parse_args()

    days = 240 if args.quick else int(args.days)
    world_path = ROOT / "data" / "world_full.json"
    if not world_path.is_file():
        raise SystemExit(f"missing {world_path}")

    twin.WORLD_PATH = world_path.resolve()
    twin.NPC_DENSITY_SCALE = 1.0
    twin.NPC_MASS_SCALE = 1.0

    base_wl = float(twin._WEALTH_LERP)
    base_cc = float(twin._COMMERCE_WEALTH_TARGET_COEF)
    base_gs = float(twin._GRAIN_SPOIL_FRACTION)

    # Curated corners (not full grid): ~1.3s/tick × 800 × 12 ≈ 3.5h on reference laptop.
    if args.quick:
        scenarios = [
            ("baseline", base_wl, base_cc, base_gs),
            ("wl0.11", 0.11, base_cc, base_gs),
            ("cc0.045", base_wl, 0.045, base_gs),
        ]
    else:
        scenarios = [
            ("baseline", base_wl, base_cc, base_gs),
            ("wl0.12", 0.12, base_cc, base_gs),
            ("wl0.11", 0.11, base_cc, base_gs),
            ("wl0.10", 0.10, base_cc, base_gs),
            ("cc0.050", base_wl, 0.050, base_gs),
            ("cc0.045", base_wl, 0.045, base_gs),
            ("cc0.038", base_wl, 0.038, base_gs),
            ("gs0.015", base_wl, base_cc, 0.015),
            ("gs0.019", base_wl, base_cc, 0.019),
            ("combo_tame", 0.11, 0.045, base_gs),
            ("combo_tight_grain", 0.10, 0.042, 0.019),
            ("combo_growth_brake", 0.10, 0.038, 0.017),
        ]

    rows: list[dict] = []
    print(f"# full-world sweep :: {world_path.name} :: {days} ticks/scenario :: {len(scenarios)} runs", flush=True)
    for name, wl, cc, gs in scenarios:
        _restore_tunables(wl, cc, gs)
        r = _run_once(days)
        r["name"] = name
        r["_wealth_lerp"] = wl
        r["_commerce_wealth_target_coef"] = cc
        r["_grain_spoil_fraction"] = gs
        rows.append(r)
        print(json.dumps({"scenario": name, **{k: v for k, v in r.items() if not k.startswith("_")}}), flush=True)

    def grain_ok(mgd: float) -> bool:
        return mgd >= 2.0

    def score_row(r: dict) -> float:
        """Lower is better: penalize growth and unrest; reward comfortable grain floor."""
        mg = float(r["min_grain_days_seen"])
        if mg >= 9000.0:
            mg = 0.0
        riot_pen = 5000.0 * int(r["riots"])
        bust_pen = 200.0 * int(r["bankruptcies"])
        growth = max(0, int(r["npc_balance_sheet_delta"])) / 250000.0 + max(0, int(r["sum_wealth_delta"])) / 800000.0
        grain_pen = 0.0 if grain_ok(mg) else (12.0 - min(mg, 12.0)) * 800.0
        unrest_pen = max(0, int(r["max_unrest_seen"]) - 120) * 2.0
        return growth + riot_pen + bust_pen + grain_pen + unrest_pen

    rows.sort(key=score_row)
    out_path = ROOT / "tools" / "full_world_balance_sweep_last.json"
    out_path.write_text(json.dumps({"days": days, "world": str(world_path), "ranked": rows}, indent=2))
    best = rows[0]
    print()
    print("=== ranked (best first) ===")
    for r in rows[:12]:
        print(
            f"  {score_row(r):8.1f}  {r['name']}: "
            f"riots={r['riots']} bust={r['bankruptcies']} "
            f"min_grain≈{r['min_grain_days_seen']:.2f} med_end={r['median_end_grain_days']:.1f} "
            f"max_unrest={r['max_unrest_seen']} "
            f"Δwealth_sum={r['sum_wealth_delta']:+d} Δnpc_bs={r['npc_balance_sheet_delta']:+d}"
        )
    print()
    print(
        f"Best scenario: {best['name']}  "
        f"(_WEALTH_LERP={best['_wealth_lerp']}, "
        f"_COMMERCE_WEALTH_TARGET_COEF={best['_commerce_wealth_target_coef']}, "
        f"_GRAIN_SPOIL_FRACTION={best['_grain_spoil_fraction']})"
    )
    print(f"Full table: {out_path}")


if __name__ == "__main__":
    main()

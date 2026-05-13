"""Per-port population resilience analysis (post-resilience-helpers).

Runs the same 10000-day twin scenario, tracks per-port `population_grain` every day,
and prints:

  baseline / end / min / max / mean / median pop
  days at or above baseline
  days at floor (4 mouths/day)
  days population rationing was active
  end-of-run preserved-food reserve as % of cap

Usage:
  python3 tools/analyze_pop_resilience.py 10000
"""

from __future__ import annotations

import random
import statistics
import sys
from pathlib import Path

# Make the sim importable as a module.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.sim_100_days import _RNG_SEED, Sim  # noqa: E402


def fmt_int(v: int, width: int = 4) -> str:
    return f"{v:>{width}}"


def fmt_float(v: float, width: int = 6, precision: int = 1) -> str:
    return f"{v:>{width}.{precision}f}"


def main() -> None:
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 10000
    rng = random.Random(_RNG_SEED)
    sim = Sim(rng)
    sim.load()

    baselines = {pid: int(sim.port_population_grain_baseline.get(pid, 0)) for pid in sim.port_order}
    history: dict[str, list[int]] = {pid: [] for pid in sim.port_order}
    ration_days_count: dict[str, int] = {pid: 0 for pid in sim.port_order}

    history_yearly_min: dict[str, list[int]] = {pid: [] for pid in sim.port_order}
    history_yearly_max: dict[str, list[int]] = {pid: [] for pid in sim.port_order}
    year_len = 360
    current_year_min: dict[str, int] = {pid: 120 for pid in sim.port_order}
    current_year_max: dict[str, int] = {pid: 0 for pid in sim.port_order}

    print(f"=== resilience analysis: {days} ticks (RNG seed {_RNG_SEED}) ===")

    for d in range(days):
        sim.advance_day()
        n = d + 1
        for pid in sim.port_order:
            pop = int(sim.port_population_grain.get(pid, 0))
            history[pid].append(pop)
            current_year_min[pid] = min(current_year_min[pid], pop)
            current_year_max[pid] = max(current_year_max[pid], pop)
            if bool(sim.port_rationing_active.get(pid, False)):
                ration_days_count[pid] += 1
        if n % year_len == 0:
            for pid in sim.port_order:
                history_yearly_min[pid].append(current_year_min[pid])
                history_yearly_max[pid].append(current_year_max[pid])
                current_year_min[pid] = 120
                current_year_max[pid] = 0

    print()
    print("--- per-port population over the whole run ---")
    header = (
        f"{'port':<10} {'base':>4} {'end':>4} {'min':>4} {'max':>4} {'mean':>6} "
        f"{'med':>4} {'≥base%':>7} {'=floor%':>8} {'ration_d':>9}"
    )
    print(header)
    print("-" * len(header))

    kept_count = 0
    grew_count = 0
    lost_count = 0

    for pid in sim.port_order:
        ts = history[pid]
        b = baselines[pid]
        end = ts[-1]
        mn = min(ts)
        mx = max(ts)
        mean = statistics.mean(ts)
        med = statistics.median(ts)
        ge_base = 100.0 * sum(1 for v in ts if v >= b) / len(ts)
        floor_pct = 100.0 * sum(1 for v in ts if v <= 4) / len(ts)
        rd = ration_days_count[pid]

        if end >= b:
            if end > b:
                grew_count += 1
            else:
                kept_count += 1
        else:
            lost_count += 1

        print(
            f"{pid:<10} "
            f"{fmt_int(b)} {fmt_int(end)} {fmt_int(mn)} {fmt_int(mx)} "
            f"{fmt_float(mean)} {fmt_int(int(round(med)))} "
            f"{fmt_float(ge_base)}% {fmt_float(floor_pct)}% "
            f"{fmt_int(rd, 8)}"
        )

    print()
    print("--- end-of-run population vs. founding baseline ---")
    total = len(sim.port_order)
    print(f"  kept_baseline_exactly: {kept_count} / {total}")
    print(f"  grew_above_baseline  : {grew_count} / {total}")
    print(f"  below_baseline       : {lost_count} / {total}")

    print()
    print("--- yearly peaks (max pop reached each year) — first 6 / last 6 years ---")
    n_years = len(next(iter(history_yearly_max.values())))
    if n_years > 0:
        head = min(6, n_years)
        tail = min(6, n_years)
        print(f"  port        baseline | first {head}y peaks ...    | ... last {tail}y peaks")
        for pid in sim.port_order:
            firsts = " ".join(f"{v:>3}" for v in history_yearly_max[pid][:head])
            lasts = " ".join(f"{v:>3}" for v in history_yearly_max[pid][-tail:])
            print(f"  {pid:<11} {baselines[pid]:>4}    | {firsts}    | {lasts}")

    print()
    print("--- end-of-run preserved-food reserves ---")
    for pid in sim.port_order:
        cap = sim._preserved_food_cap_for_port(pid)
        cur = float(sim.port_preserved_food.get(pid, 0.0))
        pct = (100.0 * cur / cap) if cap > 0 else 0.0
        print(f"  {pid:<11} reserve={cur:6.1f} / cap={cap:>4}  ({pct:5.1f}%)")


if __name__ == "__main__":
    main()

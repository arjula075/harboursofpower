#!/usr/bin/env python3
"""
Streaming version of `tools/sim_100_days.py`.

Runs the Python twin one tick at a time so you can watch the world progress.
After every tick (or every Nth tick when `--every N` is supplied) the script:

1. prints a compact one-line digest to stdout
2. atomically rewrites a per-port snapshot file (`--snapshot-out`, default
   `tools/sim_stream/latest.json`) — point any viewer / dashboard at it and it
   will always show the latest finished tick
3. appends one compact line per tick to a **trend** file (`--trend-out`, default
   `tools/sim_stream/trend.jsonl`) with just the top-level metrics so the dashboard
   can persist its chart across reloads. Truncated at the start of each run; pass
   `--no-trend` to skip
4. optionally appends a single **full** snapshot per tick to a full timeline
   (`--timeline-out`) so you can replay or plot the whole run later
   (each line is ~6–8 KB for 75 ports — opt in)

The script is a thin wrapper around `Sim.advance_day()` from `tools/sim_100_days.py`;
no economy logic is duplicated.

Usage:
  python3 tools/sim_stream.py                       # 365 ticks, every tick, default 8-port world
  python3 tools/sim_stream.py 1000 --every 1        # full per-tick stream
  python3 tools/sim_stream.py 5000 --every 25       # snapshot every 25 ticks (still ticks daily)
  python3 tools/sim_stream.py 2000 --world data/world_full.json
  python3 tools/sim_stream.py 365 --pause-ms 50     # slow it down for visual updates
  python3 tools/sim_stream.py 365 --timeline-out tools/sim_stream/run.jsonl

The `latest.json` schema mirrors a trimmed `Sim.metrics()` so it stays small:

  {
    "tick": int,
    "day": int,
    "started_at": ISO-8601 str,
    "updated_at": ISO-8601 str,
    "world_path": str,
    "elapsed_s": float,
    "ticks_per_sec": float,
    "world_treasury_coins": int,
    "npc_total_money": int,
    "npc_at_sea": int,
    "riot_events_total": int,
    "bankruptcy_events_total": int,
    "ports": { pid: { wealth, attractor, grain_food_days, food_unrest,
                       population_grain, at_war, war_days_left, ... } }
  }
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Import after the path tweak so `from tools.sim_100_days import ...` works
# when the script is launched directly from the repo root.
sys.path.insert(0, str(ROOT))

import tools.sim_100_days as twin  # noqa: E402  (after sys.path tweak)


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2))
    os.replace(tmp, path)


def _port_row(metrics_port: dict) -> dict:
    """Keep the snapshot small but useful for a viewer."""
    return {
        "wealth": int(metrics_port.get("wealth", 0)),
        "attractor": int(metrics_port.get("attractor", 0)),
        "grain_food_days": round(float(metrics_port.get("grain_food_days", 0.0)), 2),
        "food_unrest": int(metrics_port.get("food_unrest", 0)),
        "food_unrest_mood": str(metrics_port.get("food_unrest_mood", "")),
        "population_grain": int(metrics_port.get("population_grain", 0)),
        "population_grain_cap": int(metrics_port.get("population_grain_cap", 0)),
        "at_war": bool(metrics_port.get("at_war", False)),
        "war_days_left": int(metrics_port.get("war_days_left", 0)),
        "war_recurring": bool(metrics_port.get("war_recurring", False)),
        "commerce_pulse": round(float(metrics_port.get("commerce_pulse", 0.0)), 3),
        "stock_grain": int(metrics_port.get("stock_grain", 0)),
        "stock_metal": int(metrics_port.get("stock_metal", 0)),
        "stock_wire": int(metrics_port.get("stock_wire", 0)),
        "plague_days": int(metrics_port.get("plague_days", 0)),
        "famine_streak_days": int(metrics_port.get("famine_streak_days", 0)),
    }


def _build_snapshot(sim, tick_idx: int, started_at: str, t0: float) -> dict:
    m = sim.metrics()
    elapsed = max(1e-6, time.perf_counter() - t0)
    return {
        "tick": tick_idx,
        "day": int(m.get("day", sim.current_day)),
        "started_at": started_at,
        "updated_at": _utc_iso(),
        "world_path": str(twin.WORLD_PATH),
        "elapsed_s": round(elapsed, 3),
        "ticks_per_sec": round(tick_idx / elapsed, 3),
        "world_treasury_coins": int(m.get("world_treasury_coins", 0)),
        "npc_total_money": int(m.get("npc_total_money", 0)),
        "npc_total_balance_sheet_coins": int(m.get("npc_total_balance_sheet_coins", 0)),
        "npc_at_sea": int(m.get("npc_at_sea", 0)),
        "npc_agent_count": int(m.get("npc_agent_count", 0)),
        "riot_events_total": int(getattr(sim, "riot_events", 0)),
        "bankruptcy_events_total": int(getattr(sim, "bankruptcy_events", 0)),
        "pirate_raids_success": int(m.get("pirate_raids_success", 0)),
        "ports": {pid: _port_row(prow) for pid, prow in m.get("ports", {}).items()},
    }


def _print_line(snap: dict) -> None:
    ports = snap.get("ports", {})
    # Worst three by food_unrest for a quick read.
    worst = sorted(ports.items(), key=lambda kv: -int(kv[1].get("food_unrest", 0)))[:3]
    hot = ", ".join(f"{pid}={p['food_unrest']}" for pid, p in worst if int(p["food_unrest"]) > 0) or "calm"
    print(
        f"d{snap['day']:>5}  t{snap['tick']:>5}  "
        f"riots={snap['riot_events_total']:>4}  "
        f"bust={snap['bankruptcy_events_total']:>3}  "
        f"npc_purse={snap['npc_total_money']:>7}  "
        f"at_sea={snap['npc_at_sea']:>4}/{snap['npc_agent_count']:<4}  "
        f"tps={snap['ticks_per_sec']:>5.1f}  "
        f"hot[{hot}]",
        flush=True,
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="Stream the HarboursOfPower twin one tick at a time.")
    ap.add_argument("days", nargs="?", type=int, default=365, help="Total ticks to run (default 365).")
    ap.add_argument(
        "--world",
        type=str,
        default=None,
        help="Path to world.json to use; default = whatever tools/sim_100_days.py points at.",
    )
    ap.add_argument(
        "--every",
        type=int,
        default=1,
        help="Write snapshot + print every N ticks (default 1).",
    )
    ap.add_argument(
        "--snapshot-out",
        type=str,
        default=str(ROOT / "tools" / "sim_stream" / "latest.json"),
        help="Where to atomically rewrite the latest tick snapshot.",
    )
    ap.add_argument(
        "--trend-out",
        type=str,
        default=str(ROOT / "tools" / "sim_stream" / "trend.jsonl"),
        help="Compact per-tick trend file (top-level metrics only). Truncated at run start.",
    )
    ap.add_argument(
        "--no-trend",
        action="store_true",
        help="Skip the always-on trend file.",
    )
    ap.add_argument(
        "--timeline-out",
        type=str,
        default="",
        help="Optional full-snapshot JSONL; appends one large line per emitted snapshot.",
    )
    ap.add_argument(
        "--pause-ms",
        type=int,
        default=0,
        help="Sleep this many ms between ticks (useful when you want to watch the snapshot file update).",
    )
    ap.add_argument(
        "--quiet",
        action="store_true",
        help="Do not print the per-tick line (file outputs still happen).",
    )
    args = ap.parse_args()

    if args.world:
        twin.WORLD_PATH = Path(args.world).resolve()
        if not twin.WORLD_PATH.is_file():
            raise SystemExit(f"world file not found: {twin.WORLD_PATH}")

    import random  # local import to mirror sim_100_days conventions

    rng = random.Random(twin._RNG_SEED)
    sim = twin.Sim(rng)
    sim.load()

    snap_path = Path(args.snapshot_out).resolve()
    timeline_path = Path(args.timeline_out).resolve() if args.timeline_out else None
    trend_path: Path | None = None
    if not args.no_trend:
        trend_path = Path(args.trend_out).resolve()
        trend_path.parent.mkdir(parents=True, exist_ok=True)
        trend_path.write_text("")
    if timeline_path is not None:
        timeline_path.parent.mkdir(parents=True, exist_ok=True)
        timeline_path.write_text("")

    started_at = _utc_iso()
    t0 = time.perf_counter()

    def _trend_row(snap: dict) -> dict:
        return {
            "tick": int(snap["tick"]),
            "day": int(snap["day"]),
            "updated_at": snap["updated_at"],
            "npc_purse": int(snap["npc_total_money"]),
            "npc_balance_sheet": int(snap["npc_total_balance_sheet_coins"]),
            "npc_at_sea": int(snap["npc_at_sea"]),
            "npc_agent_count": int(snap["npc_agent_count"]),
            "riot_events_total": int(snap["riot_events_total"]),
            "bankruptcy_events_total": int(snap["bankruptcy_events_total"]),
            "pirate_raids_success": int(snap["pirate_raids_success"]),
            "world_treasury_coins": int(snap["world_treasury_coins"]),
        }

    def _emit(snap: dict) -> None:
        _atomic_write_json(snap_path, snap)
        if trend_path is not None:
            with trend_path.open("a") as fh:
                fh.write(json.dumps(_trend_row(snap)) + "\n")
        if timeline_path is not None:
            with timeline_path.open("a") as fh:
                fh.write(json.dumps(snap) + "\n")

    # Emit a tick 0 snapshot so viewers see baseline before any advance.
    snap = _build_snapshot(sim, 0, started_at, t0)
    _emit(snap)
    if not args.quiet:
        print(
            f"# streaming twin :: world={twin.WORLD_PATH}  total_ticks={args.days}  every={args.every}  "
            f"snapshot={snap_path}  trend={trend_path or '-'}  timeline={timeline_path or '-'}"
        )
        _print_line(snap)

    every = max(1, int(args.every))
    pause = max(0, int(args.pause_ms)) / 1000.0

    try:
        for i in range(1, int(args.days) + 1):
            sim.advance_day()
            if i % every == 0 or i == int(args.days):
                snap = _build_snapshot(sim, i, started_at, t0)
                _emit(snap)
                if not args.quiet:
                    _print_line(snap)
            if pause > 0.0:
                time.sleep(pause)
    except KeyboardInterrupt:
        if not args.quiet:
            print("\n# interrupted — final snapshot still on disk", file=sys.stderr)


if __name__ == "__main__":
    main()

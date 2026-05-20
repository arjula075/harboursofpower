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
  python3 tools/sim_stream.py                       # 365 ticks, every tick, twin default world (world_full.json)
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
    "price_grain_mean": float,   # mean dock buy for grain (legacy; kept for trend compat)
    "price_metal_mean": float,  # mean dock buy for metal good (legacy)
    "price_tier_food": float,   # mean dock buy averaged across food-tier goods
    "price_tier_comfort": float,
    "price_tier_metal": float,  # metal-tier goods (metal + wire)
    "food_unrest_mean": float,
    "contracts": { active_by_type, active_total, lane_active, city_grain_*, adjacency_*, phase3_*, ... },
    "chart_areas": [ { id, name }, ... ],
    "regions": { area_id: { port_count, wealth_mean, food_unrest_mean, ... }, ... },
    "ports": { pid: { ..., chart_area_id }, ... }
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
    # On Windows os.replace can transiently fail with PermissionError
    # (WinError 5/32) when another process — the dashboard's static HTTP
    # server, Defender, search indexer, OneDrive — briefly has the target
    # file open. Retry a few times with a short backoff; if it still fails,
    # fall back to a non-atomic write rather than crashing the whole run.
    last_err: OSError | None = None
    for attempt in range(8):
        try:
            os.replace(tmp, path)
            return
        except PermissionError as e:
            last_err = e
            time.sleep(0.05 * (attempt + 1))
    try:
        path.write_text(json.dumps(payload, indent=2))
        try:
            tmp.unlink()
        except OSError:
            pass
    except OSError:
        if last_err is not None:
            raise last_err
        raise


def _round_floats(obj, places: int = 2):
    """Recursively round float values; leave ints, bools, strings, None alone.

    Booleans are technically ints in Python, so check bool first.
    """
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, float):
        return round(obj, places)
    if isinstance(obj, dict):
        return {k: _round_floats(v, places) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_round_floats(v, places) for v in obj]
    if isinstance(obj, tuple):
        return tuple(_round_floats(v, places) for v in obj)
    return obj


_ALLIANCE_BAND_NAMES = (
    "Italic rim",
    "Carthaginian bloc",
    "Iberian gateway",
    "Levantine network",
)


def _load_port_meta(world_path: Path) -> dict[str, dict]:
    """Per-port static fields from world JSON for dashboard rollups / map."""
    try:
        world = json.loads(world_path.read_text())
    except (OSError, ValueError):
        return {}
    out: dict[str, dict] = {}
    for p in world.get("ports", []):
        pid = str(p.get("id", ""))
        if not pid:
            continue
        out[pid] = {
            "name": str(p.get("name", pid)),
            "role": str(p.get("role", "") or ""),
            "chart_area_id": str(p.get("chart_area_id", "") or ""),
            "map_u": round(float(p.get("map_u", 0.5)), 5),
            "map_v": round(float(p.get("map_v", 0.5)), 5),
        }
    return out


def _load_port_roles(world_path: Path) -> dict[str, str]:
    return {pid: str(m.get("role", "") or "") for pid, m in _load_port_meta(world_path).items()}


def _load_port_chart_areas(world_path: Path) -> dict[str, str]:
    return {pid: str(m.get("chart_area_id", "") or "") for pid, m in _load_port_meta(world_path).items()}


def _load_chart_areas(world_path: Path) -> list[dict]:
    """Ordered chart-area catalogue from world JSON."""
    try:
        world = json.loads(world_path.read_text())
    except (OSError, ValueError):
        return []
    out: list[dict] = []
    for a in world.get("chart_areas", []):
        if not isinstance(a, dict):
            continue
        aid = str(a.get("id", ""))
        if not aid:
            continue
        out.append({"id": aid, "name": str(a.get("name", aid))})
    return out


def _load_goods_need_tiers(goods_path: Path | None = None) -> dict[str, str]:
    """Good id → need_tier from goods.json (food / comfort / metal / luxury / '')."""
    path = goods_path or (ROOT / "data" / "goods.json")
    try:
        doc = json.loads(path.read_text())
    except (OSError, ValueError):
        return {}
    out: dict[str, str] = {}
    for g in doc.get("goods", []):
        if not isinstance(g, dict):
            continue
        gid = str(g.get("id", ""))
        if gid:
            out[gid] = str(g.get("need_tier", "") or "")
    return out


def _port_row(
    metrics_port: dict,
    initial_pop: int = 0,
    role: str = "",
    chart_area_id: str = "",
    port_name: str = "",
    map_u: float = 0.5,
    map_v: float = 0.5,
    alliance_band: int = -1,
) -> dict:
    """Keep the snapshot small but useful for a viewer."""
    return {
        "name": str(port_name or ""),
        "map_u": round(float(map_u), 5),
        "map_v": round(float(map_v), 5),
        "alliance_band": int(alliance_band),
        "wealth": int(metrics_port.get("wealth", 0)),
        "attractor": int(metrics_port.get("attractor", 0)),
        "grain_food_days": round(float(metrics_port.get("grain_food_days", 0.0)), 2),
        "food_unrest": int(metrics_port.get("food_unrest", 0)),
        "food_worry": int(metrics_port.get("food_worry", 0)),
        "food_panic": int(metrics_port.get("food_panic", 0)),
        "food_unrest_mood": str(metrics_port.get("food_unrest_mood", "")),
        "food_riot_events": int(metrics_port.get("food_riot_events", 0)),
        "population_grain": int(metrics_port.get("population_grain", 0)),
        "population_grain_cap": int(metrics_port.get("population_grain_cap", 0)),
        "population_initial": int(initial_pop),
        "role": str(role or ""),
        "chart_area_id": str(chart_area_id or ""),
        "at_war": bool(metrics_port.get("at_war", False)),
        "war_days_left": int(metrics_port.get("war_days_left", 0)),
        "war_recurring": bool(metrics_port.get("war_recurring", False)),
        "commerce_pulse": round(float(metrics_port.get("commerce_pulse", 0.0)), 3),
        "commerce_npc_buy_coins": int(metrics_port.get("commerce_npc_buy_coins", 0)),
        "commerce_npc_sell_coins": int(metrics_port.get("commerce_npc_sell_coins", 0)),
        "stock_grain": int(metrics_port.get("stock_grain", 0)),
        "stock_metal": int(metrics_port.get("stock_metal", 0)),
        "stock_wire": int(metrics_port.get("stock_wire", 0)),
        "plague_days": int(metrics_port.get("plague_days", 0)),
        "famine_streak_days": int(metrics_port.get("famine_streak_days", 0)),
        "starvation_streak_days": int(metrics_port.get("starvation_streak_days", 0)),
    }


def _load_initial_populations(world_path: Path) -> dict[str, int]:
    """Read each port's seed `population_grain_per_day` from the world JSON.

    That value (clamped to `_POP_GRAIN_FLOOR=4`) is what `_init_port_demographics_from_world`
    uses to seed both the starting population and the baseline. We capture it once at
    startup so the dashboard can compare current population vs the "founding cohort"
    without the twin having to remember the original baseline.
    """
    try:
        world = json.loads(world_path.read_text())
    except (OSError, ValueError):
        return {}
    floor = int(getattr(twin, "_POP_GRAIN_FLOOR", 4))
    out: dict[str, int] = {}
    for p in world.get("ports", []):
        pid = str(p.get("id", ""))
        if not pid:
            continue
        gpd = int(p.get("population_grain_per_day", 6))
        out[pid] = max(floor, gpd)
    return out


def _mean_dock_buy_tier(sim, tier: str, goods_tiers: dict[str, str]) -> float:
    """Unweighted mean of per-good dock-buy means for all goods in a need_tier."""
    tier_s = str(tier)
    gids = [gid for gid, t in goods_tiers.items() if t == tier_s and gid in sim.goods]
    if not gids:
        return 0.0
    total = sum(_mean_dock_buy_unit(sim, gid) for gid in gids)
    return round(total / float(len(gids)), 2)


def _count_convoy_escort_leaders(sim) -> dict[str, int]:
    """Convoy escort is tracked on voyage agents, not in institutional_contracts[]."""
    leaders_npc = 0
    leaders_player = 0
    for ag in getattr(sim, "npc_agents", []) or []:
        if not isinstance(ag, dict):
            continue
        if bool(ag.get("convoy_escort_player", False)):
            leaders_player += 1
        elif int(ag.get("convoy_escort_id", 0) or 0) > 0:
            leaders_npc += 1
    return {
        "leaders_npc_escort": int(leaders_npc),
        "leaders_player_escort": int(leaders_player),
    }


def _count_active_contracts_by_type(sim) -> dict[str, int]:
    """Active institutional contract rows on NPC agents, keyed by contract type id."""
    counts: dict[str, int] = {}
    for ag in getattr(sim, "npc_agents", []) or []:
        if not isinstance(ag, dict):
            continue
        icm = ag.get("institutional_contracts")
        if not isinstance(icm, list):
            continue
        for row in icm:
            if not isinstance(row, dict):
                continue
            t = str(row.get("type", "") or "unknown")
            counts[t] = counts.get(t, 0) + 1
    return counts


def _build_contracts_summary(sim, metrics: dict) -> dict:
    """Institutional / civic contract aggregates for the dashboard."""
    by_type = _count_active_contracts_by_type(sim)
    catalogue = list(getattr(sim, "_world_institutional_contract_types", []) or [])
    simulated_types = ["grain_delivery"]
    return {
        "catalogue": catalogue,
        "simulated_types": simulated_types,
        "active_by_type": by_type,
        "convoy_escort": _count_convoy_escort_leaders(sim),
        "active_total": int(sum(by_type.values())),
        "lane_active": int(metrics.get("npc_institutional_lane_contracts_active", 0)),
        "institutional_rows": int(metrics.get("npc_institutional_contract_rows", 0)),
        "city_grain_signed": int(metrics.get("npc_city_grain_contracts_signed", 0)),
        "city_grain_fulfilled": int(metrics.get("npc_city_grain_contracts_fulfilled", 0)),
        "city_grain_breached": int(metrics.get("npc_city_grain_contracts_breached", 0)),
        "adjacency_rows": int(metrics.get("npc_adjacency_grain_contract_rows", 0)),
        "adjacency_earmark_units": int(metrics.get("npc_adjacency_grain_earmark_units", 0)),
        "adjacency_privileged_buy_units": int(metrics.get("npc_adjacency_grain_privileged_buy_units", 0)),
        "route_habit_mass": round(float(metrics.get("npc_route_habit_mass", 0.0)), 2),
        "route_habit_slots": int(metrics.get("npc_route_habit_slots", 0)),
        "phase3_bands": int(metrics.get("npc_institutional_phase3_bands", 0)),
        "phase3_ports_tagged": int(metrics.get("npc_institutional_phase3_ports_tagged", 0)),
        "phase4_houses": int(metrics.get("npc_institutional_phase4_merchant_houses", 0)),
        "enabled": {
            "city_grain": bool(metrics.get("npc_city_grain_contracts_enabled", True)),
            "adjacency": bool(metrics.get("adjacency_grain_contracts_enabled", True)),
            "phase4": bool(metrics.get("npc_institutional_phase4_enabled", False)),
            "phase5": bool(metrics.get("npc_institutional_phase5_surface_enabled", False)),
        },
    }


def _build_region_rollups(
    ports: dict[str, dict],
    chart_areas: list[dict],
) -> dict[str, dict]:
    """Per chart_area_id aggregates from the port snapshot rows."""
    buckets: dict[str, list[dict]] = {str(a["id"]): [] for a in chart_areas}
    buckets["_other"] = []
    for prow in ports.values():
        aid = str(prow.get("chart_area_id", "") or "")
        if aid in buckets:
            buckets[aid].append(prow)
        else:
            buckets["_other"].append(prow)

    names = {str(a["id"]): str(a.get("name", a["id"])) for a in chart_areas}
    names["_other"] = "Unassigned"

    out: dict[str, dict] = {}
    for aid, rows in buckets.items():
        if not rows and aid == "_other":
            continue
        n = len(rows)
        if n == 0:
            out[aid] = {
                "id": aid,
                "name": names.get(aid, aid),
                "port_count": 0,
                "wealth_mean": 0.0,
                "food_unrest_mean": 0.0,
                "grain_food_days_mean": 0.0,
                "population_mean": 0.0,
                "ports_at_war": 0,
                "riot_events_sum": 0,
            }
            continue
        out[aid] = {
            "id": aid,
            "name": names.get(aid, aid),
            "port_count": n,
            "wealth_mean": round(sum(int(r.get("wealth", 0)) for r in rows) / float(n), 1),
            "food_unrest_mean": round(sum(int(r.get("food_unrest", 0)) for r in rows) / float(n), 1),
            "grain_food_days_mean": round(
                sum(float(r.get("grain_food_days", 0.0)) for r in rows) / float(n), 2
            ),
            "population_mean": round(sum(int(r.get("population_grain", 0)) for r in rows) / float(n), 1),
            "ports_at_war": sum(1 for r in rows if bool(r.get("at_war", False))),
            "riot_events_sum": sum(int(r.get("food_riot_events", 0)) for r in rows),
        }
    return out


def _load_alliance_band_port_lists(world_path: Path) -> list[list[str]]:
    try:
        world = json.loads(world_path.read_text())
    except (OSError, ValueError):
        return []
    it = world.get("institutional_trade")
    if not isinstance(it, dict):
        return []
    p3 = it.get("phase3")
    if not isinstance(p3, dict):
        return []
    raw = p3.get("bands")
    if not isinstance(raw, list):
        return []
    out: list[list[str]] = []
    for band in raw:
        if not isinstance(band, list):
            continue
        ids = [str(p) for p in band if str(p)]
        if ids:
            out.append(ids)
    return out


def _band_voyage_stats(sim, band_ports: set[str]) -> dict:
    """Underway merchants homed in this band: intra-band dest share."""
    intra = 0
    cross = 0
    other = 0
    p3_active = bool(sim._inst_p3_active()) if hasattr(sim, "_inst_p3_active") else False
    port_names = set(getattr(sim, "port_names", []) or [])
    for ag in getattr(sim, "npc_agents", []) or []:
        if not isinstance(ag, dict):
            continue
        if int(ag.get("voyage_days_remaining", 0) or 0) <= 0:
            continue
        home = str(ag.get("home_port", ""))
        if home not in band_ports:
            continue
        dest = str(ag.get("voyage_dest_id", ""))
        if dest not in port_names:
            other += 1
            continue
        if not p3_active:
            other += 1
            continue
        try:
            bh = sim._inst_p3_port_band(home)
            bd = sim._inst_p3_port_band(dest)
        except (TypeError, ValueError):
            other += 1
            continue
        if bh >= 0 and bh == bd:
            intra += 1
        else:
            cross += 1
    total = intra + cross + other
    share = float(intra) / float(total) if total > 0 else 0.0
    return {
        "voyages_at_sea": int(total),
        "intra_band": int(intra),
        "cross_band": int(cross),
        "intra_share": round(share, 3),
    }


def _build_alliance_bands(sim, world_path: Path, metrics_ports: dict) -> dict:
    """Phase-3 alliance band cards for the dashboard."""
    band_lists = _load_alliance_band_port_lists(world_path)
    enabled = bool(sim._inst_p3_active()) if hasattr(sim, "_inst_p3_active") else False
    mul = {
        "ally_toll_mul": round(float(getattr(sim, "_world_inst_p3_ally_toll_mul", 0.86)), 3),
        "enemy_toll_mul": round(float(getattr(sim, "_world_inst_p3_enemy_toll_mul", 1.14)), 3),
        "ally_buy_mul": round(float(getattr(sim, "_world_inst_p3_ally_buy_mul", 0.985)), 3),
        "route_ally_bonus": round(float(getattr(sim, "_world_inst_p3_route_ally_bonus", 0.10)), 3),
        "route_hostile_penalty": round(float(getattr(sim, "_world_inst_p3_route_hostile_penalty", 0.24)), 3),
        "escort_same_band_p": round(float(getattr(sim, "_world_inst_p3_escort_same_band_p", 0.075)), 3),
    }
    port_band_map = getattr(sim, "_port_inst_alliance_band", {}) or {}
    cards: list[dict] = []
    for bi, port_ids in enumerate(band_lists):
        members = [pid for pid in port_ids if pid in metrics_ports]
        band_set = set(members)
        commerce_buy = sum(int(metrics_ports[pid].get("commerce_npc_buy_coins", 0)) for pid in members)
        commerce_sell = sum(int(metrics_ports[pid].get("commerce_npc_sell_coins", 0)) for pid in members)
        at_war = sum(1 for pid in members if bool(metrics_ports[pid].get("at_war", False)))
        label = _ALLIANCE_BAND_NAMES[bi] if bi < len(_ALLIANCE_BAND_NAMES) else f"Band {bi}"
        cards.append(
            {
                "band_index": bi,
                "name": label,
                "port_count": len(members),
                "port_ids": members,
                "commerce_npc_buy_coins": int(commerce_buy),
                "commerce_npc_sell_coins": int(commerce_sell),
                "ports_at_war": int(at_war),
                "voyage": _band_voyage_stats(sim, band_set),
                "configured_toll_mul": mul["ally_toll_mul"],
                "configured_buy_mul": mul["ally_buy_mul"],
                "configured_route_ally_bonus": mul["route_ally_bonus"],
            }
        )
    return {
        "enabled": enabled,
        "band_count": len(cards),
        "ports_tagged": len(port_band_map),
        "multipliers": mul,
        "bands": cards,
    }


def _build_wars_summary(ports: dict[str, dict]) -> dict:
    """Per-port war state (wars are not paired in the twin)."""
    at_war = [(pid, p) for pid, p in ports.items() if bool(p.get("at_war", False))]
    at_war.sort(key=lambda kv: (-int(kv[1].get("war_days_left", 0)), kv[0]))
    total = len(at_war)
    days = [int(p.get("war_days_left", 0)) for _, p in at_war]
    avg_days = round(sum(days) / float(total), 1) if total > 0 else 0.0
    top = []
    for pid, p in at_war[:5]:
        top.append(
            {
                "port_id": pid,
                "name": str(p.get("name", pid) or pid),
                "war_days_left": int(p.get("war_days_left", 0)),
                "war_recurring": bool(p.get("war_recurring", False)),
                "food_unrest": int(p.get("food_unrest", 0)),
            }
        )
    return {
        "active_count": int(total),
        "avg_days_remaining": avg_days,
        "recurring_count": sum(1 for _, p in at_war if bool(p.get("war_recurring", False))),
        "top": top,
    }


def _gini_coefficient(values: list[float]) -> float:
    """Gini coefficient 0–1 from a list of non-negative values."""
    vals = sorted(float(v) for v in values if v is not None and float(v) >= 0)
    n = len(vals)
    if n < 2:
        return 0.0
    total = sum(vals)
    if total <= 0:
        return 0.0
    weighted = sum((2 * i - n - 1) * x for i, x in enumerate(vals, 1))
    return round(weighted / (n * total), 4)


def _build_goods_flow_summary(sim) -> dict:
    """Global structural supply vs demand per good (twin formulas, units/day)."""
    rows: list[dict] = []
    port_order = list(getattr(sim, "port_order", []) or [])
    goods = getattr(sim, "goods", {}) or {}
    for gid in sorted(goods.keys()):
        prod = 0.0
        cons = 0.0
        for pid in port_order:
            try:
                prod += float(sim._port_structural_supply_per_day(pid, gid))
                cons += float(sim._port_resolved_market_demand_per_day(pid, gid))
            except (TypeError, ValueError, AttributeError):
                continue
        rows.append(
            {
                "id": str(gid),
                "production_per_day": round(prod, 2),
                "consumption_per_day": round(cons, 2),
                "net_per_day": round(prod - cons, 2),
            }
        )
    rows.sort(key=lambda r: -abs(float(r["net_per_day"])))
    return {"goods": rows}


def _accumulate_goods_flow_tick(cumulative: dict[str, dict], sim) -> None:
    """Add one sim-day of structural supply and demand to running totals."""
    port_order = list(getattr(sim, "port_order", []) or [])
    goods = getattr(sim, "goods", {}) or {}
    for gid in goods.keys():
        prod = 0.0
        cons = 0.0
        gid_s = str(gid)
        for pid in port_order:
            try:
                prod += float(sim._port_structural_supply_per_day(pid, gid_s))
                cons += float(sim._port_resolved_market_demand_per_day(pid, gid_s))
            except (TypeError, ValueError, AttributeError):
                continue
        row = cumulative.setdefault(
            gid_s,
            {"production_total": 0.0, "consumption_total": 0.0},
        )
        row["production_total"] += prod
        row["consumption_total"] += cons


def _format_cumulative_goods_flow(cumulative: dict[str, dict], ticks: int) -> dict:
    """Snapshot-friendly cumulative production − consumption since stream start."""
    goods: list[dict] = []
    tot_prod = 0.0
    tot_cons = 0.0
    for gid in sorted(cumulative.keys()):
        s = cumulative[gid]
        p = float(s.get("production_total", 0.0))
        c = float(s.get("consumption_total", 0.0))
        tot_prod += p
        tot_cons += c
        goods.append(
            {
                "id": gid,
                "production_total": round(p, 2),
                "consumption_total": round(c, 2),
                "net_total": round(p - c, 2),
            }
        )
    goods.sort(key=lambda r: -abs(float(r["net_total"])))
    return {
        "ticks": int(ticks),
        "production_total": round(tot_prod, 2),
        "consumption_total": round(tot_cons, 2),
        "net_total": round(tot_prod - tot_cons, 2),
        "goods": goods,
    }


def _attach_cumulative_goods_flow(snap: dict, cumulative: dict[str, dict]) -> None:
    gf = snap.get("goods_flow")
    if not isinstance(gf, dict):
        gf = {}
        snap["goods_flow"] = gf
    gf["cumulative"] = _format_cumulative_goods_flow(cumulative, int(snap.get("tick", 0)))


def _global_port_stock_totals(sim) -> dict[str, float]:
    """Sum port warehouse qty per good across the chart."""
    port_order = list(getattr(sim, "port_order", []) or [])
    goods = getattr(sim, "goods", {}) or {}
    totals: dict[str, float] = {str(gid): 0.0 for gid in goods.keys()}
    stocks = getattr(sim, "port_stocks", {}) or {}
    for pid in port_order:
        ps = str(pid)
        row = stocks.get(ps)
        if isinstance(row, dict):
            for gid in totals:
                totals[gid] += float(row.get(gid, 0))
        else:
            for gid in totals:
                try:
                    totals[gid] += float(sim._port_stock_qty(ps, gid))
                except (TypeError, ValueError, AttributeError):
                    continue
    return totals


def _init_stock_tracker(sim) -> dict:
    base = _global_port_stock_totals(sim)
    return {"baseline": dict(base), "prev": dict(base), "last_day_delta": {str(g): 0.0 for g in base}}


def _accumulate_stock_tick(stock_state: dict, sim) -> None:
    cur = _global_port_stock_totals(sim)
    prev = stock_state.get("prev") or {}
    last: dict[str, float] = {}
    for gid, q in cur.items():
        last[gid] = float(q) - float(prev.get(gid, 0.0))
    stock_state["last_day_delta"] = last
    stock_state["prev"] = dict(cur)


def _accumulate_trade_tick(trade_cum: dict, sim) -> None:
    port_order = list(getattr(sim, "port_order", []) or [])
    commerce = getattr(sim, "_port_commerce_tick", {}) or {}
    sell_day = 0
    buy_day = 0
    for pid in port_order:
        row = commerce.get(str(pid))
        if not isinstance(row, dict):
            continue
        sell_day += int(row.get("npc_sell_units", 0))
        buy_day += int(row.get("npc_buy_units", 0))
    trade_cum["npc_sell_total"] = float(trade_cum.get("npc_sell_total", 0.0)) + float(sell_day)
    trade_cum["npc_buy_total"] = float(trade_cum.get("npc_buy_total", 0.0)) + float(buy_day)
    trade_cum["npc_sell_per_day"] = float(sell_day)
    trade_cum["npc_buy_per_day"] = float(buy_day)


def _format_stock_flow(stock_state: dict, ticks: int) -> dict:
    base = stock_state.get("baseline") or {}
    cur = stock_state.get("prev") or {}
    last = stock_state.get("last_day_delta") or {}
    goods: list[dict] = []
    tot_change = 0.0
    tot_stock = 0.0
    for gid in sorted(cur.keys()):
        total = float(cur.get(gid, 0.0))
        change = total - float(base.get(gid, 0.0))
        tot_change += change
        tot_stock += total
        goods.append(
            {
                "id": gid,
                "stock_total": round(total, 2),
                "stock_delta_per_day": round(float(last.get(gid, 0.0)), 2),
                "stock_change_total": round(change, 2),
            }
        )
    goods.sort(key=lambda r: -abs(float(r["stock_change_total"])))
    return {
        "ticks": int(ticks),
        "stock_total": round(tot_stock, 2),
        "stock_change_total": round(tot_change, 2),
        "goods": goods,
    }


def _format_trade_flow(trade_cum: dict, ticks: int) -> dict:
    sell = float(trade_cum.get("npc_sell_total", 0.0))
    buy = float(trade_cum.get("npc_buy_total", 0.0))
    return {
        "ticks": int(ticks),
        "npc_sell_total": round(sell, 2),
        "npc_buy_total": round(buy, 2),
        "net_inflow_total": round(sell - buy, 2),
        "npc_sell_per_day": round(float(trade_cum.get("npc_sell_per_day", 0.0)), 2),
        "npc_buy_per_day": round(float(trade_cum.get("npc_buy_per_day", 0.0)), 2),
    }


def _format_balance_flow(cumulative: dict[str, dict], stock_flow: dict) -> dict:
    """Per good: structural cumulative gap vs actual stock change (trade + other flows)."""
    struct_map: dict[str, float] = {}
    for gid, row in (cumulative or {}).items():
        p = float(row.get("production_total", 0.0))
        c = float(row.get("consumption_total", 0.0))
        struct_map[str(gid)] = p - c
    stock_goods = stock_flow.get("goods") or []
    stock_map = {str(r["id"]): float(r.get("stock_change_total", 0.0)) for r in stock_goods}
    gids = sorted(set(struct_map) | set(stock_map))
    goods: list[dict] = []
    tot_offset = 0.0
    for gid in gids:
        structural = float(struct_map.get(gid, 0.0))
        stock_chg = float(stock_map.get(gid, 0.0))
        offset = round(stock_chg - structural, 2)
        tot_offset += offset
        goods.append(
            {
                "id": gid,
                "structural_net_total": round(structural, 2),
                "stock_change_total": round(stock_chg, 2),
                "offset_total": offset,
            }
        )
    goods.sort(key=lambda r: -abs(float(r["offset_total"])))
    return {
        "ticks": int(stock_flow.get("ticks", 0)),
        "offset_total": round(tot_offset, 2),
        "goods": goods,
    }


def _attach_goods_flow_extras(
    snap: dict,
    cumulative: dict[str, dict],
    stock_state: dict,
    trade_cum: dict,
) -> None:
    gf = snap.get("goods_flow")
    if not isinstance(gf, dict):
        gf = {}
        snap["goods_flow"] = gf
    tick = int(snap.get("tick", 0))
    stock_flow = _format_stock_flow(stock_state, tick)
    gf["stock"] = stock_flow
    gf["trade"] = _format_trade_flow(trade_cum, tick)
    gf["balance"] = _format_balance_flow(cumulative, stock_flow)
    for row in gf.get("goods") or []:
        if not isinstance(row, dict):
            continue
        gid = str(row.get("id", ""))
        for extra in stock_flow.get("goods") or []:
            if str(extra.get("id")) == gid:
                row["stock_total"] = extra.get("stock_total")
                row["stock_delta_per_day"] = extra.get("stock_delta_per_day")
                row["stock_change_total"] = extra.get("stock_change_total")
                break


def _build_treasury_summary(sim, snap: dict, prev_snap: dict | None) -> dict:
    """World treasury + harbour dues collected this tick (proxy for quay income)."""
    harbour_tick = sum(
        int(v) for v in (getattr(sim, "port_harbour_due_coins_tick", {}) or {}).values()
    )
    cur = int(snap.get("world_treasury_coins", 0))
    initial = int(getattr(sim, "world_initial_treasury", 0))
    prev_coins = int(prev_snap.get("world_treasury_coins", cur)) if prev_snap else cur
    return {
        "initial_coins": initial,
        "coins": cur,
        "delta_since_prev": cur - prev_coins,
        "harbour_dues_tick": int(harbour_tick),
        "pct_of_initial": round(100.0 * cur / float(initial), 1) if initial > 0 else None,
    }


def _build_inequality_summary(ports: dict[str, dict], prev_ports: dict | None) -> dict:
    """Port wealth distribution and poll-to-poll movers."""
    wealths = [float(int(p.get("wealth", 0))) for p in ports.values()]
    gini = _gini_coefficient(wealths)
    deltas: list[dict] = []
    for pid, p in ports.items():
        w = int(p.get("wealth", 0))
        pw = int((prev_ports or {}).get(pid, {}).get("wealth", w))
        deltas.append(
            {
                "port_id": pid,
                "name": str(p.get("name", pid) or pid),
                "wealth": w,
                "wealth_delta": w - pw,
            }
        )
    top_gain = sorted(deltas, key=lambda x: -int(x["wealth_delta"]))[:10]
    top_loss = sorted(deltas, key=lambda x: int(x["wealth_delta"]))[:10]
    return {
        "gini": gini,
        "wealth_mean": round(sum(wealths) / len(wealths), 1) if wealths else 0.0,
        "wealth_total": int(sum(wealths)),
        "top_gainers": top_gain,
        "top_losers": top_loss,
    }


def _compute_tick_events(snap: dict, prev_snap: dict | None) -> dict:
    """Per-emit deltas for the event timeline (vs previous snapshot)."""
    ports = snap.get("ports") or {}
    ports_at_war = sum(1 for p in ports.values() if bool(p.get("at_war", False)))
    plague_ports = sum(1 for p in ports.values() if int(p.get("plague_days", 0)) > 0)
    if not prev_snap:
        return {
            "riot_delta": 0,
            "bust_delta": 0,
            "war_new_ports": 0,
            "plague_new_ports": 0,
            "ports_at_war": int(ports_at_war),
            "plague_ports": int(plague_ports),
        }
    riot_delta = max(0, int(snap.get("riot_events_total", 0)) - int(prev_snap.get("riot_events_total", 0)))
    bust_delta = max(
        0, int(snap.get("bankruptcy_events_total", 0)) - int(prev_snap.get("bankruptcy_events_total", 0))
    )
    prev_ports = prev_snap.get("ports") or {}
    war_new = 0
    plague_new = 0
    for pid, prow in ports.items():
        pp = prev_ports.get(pid) or {}
        if bool(prow.get("at_war", False)) and not bool(pp.get("at_war", False)):
            war_new += 1
        if int(prow.get("plague_days", 0)) > 0 and int(pp.get("plague_days", 0)) <= 0:
            plague_new += 1
    return {
        "riot_delta": int(riot_delta),
        "bust_delta": int(bust_delta),
        "war_new_ports": int(war_new),
        "plague_new_ports": int(plague_new),
        "ports_at_war": int(ports_at_war),
        "plague_ports": int(plague_ports),
    }


def _mean_dock_buy_unit(sim, good_id: str) -> float:
    """Unweighted mean NPC-counterparty dock buy price (coins/unit) across all ports.

    Matches the wholesale unit used inside `_npc_effective_buy_unit` (player_counterparty=False).
    """
    gid = str(good_id)
    if gid not in sim.goods:
        return 0.0
    ports = list(getattr(sim, "port_order", []) or [])
    if not ports:
        return 0.0
    total = 0
    for pid in ports:
        ps = str(pid)
        total += int(sim._compute_player_buy_unit(ps, gid, False))
    return round(float(total) / float(len(ports)), 2)


def _pop_summary(ports: dict[str, dict]) -> dict:
    """Aggregate population stats: mean, median, totals and below-initial counts."""
    pops = [int(p.get("population_grain", 0)) for p in ports.values()]
    inits = [int(p.get("population_initial", 0)) for p in ports.values()]
    caps = [int(p.get("population_grain_cap", 0)) for p in ports.values()]
    n = len(pops)
    if n == 0:
        return {
            "ports_total": 0,
            "population_total": 0,
            "population_initial_total": 0,
            "population_mean": 0.0,
            "population_median": 0.0,
            "ports_under_initial": 0,
            "ports_over_initial": 0,
            "ports_at_initial": 0,
            "population_total_capacity": 0,
        }
    sorted_pops = sorted(pops)
    if n % 2 == 1:
        median = float(sorted_pops[n // 2])
    else:
        median = (sorted_pops[n // 2 - 1] + sorted_pops[n // 2]) / 2.0
    under = sum(1 for p, i in zip(pops, inits) if i > 0 and p < i)
    over = sum(1 for p, i in zip(pops, inits) if i > 0 and p > i)
    at = sum(1 for p, i in zip(pops, inits) if i > 0 and p == i)
    return {
        "ports_total": n,
        "population_total": sum(pops),
        "population_initial_total": sum(inits),
        "population_mean": sum(pops) / float(n),
        "population_median": median,
        "ports_under_initial": under,
        "ports_over_initial": over,
        "ports_at_initial": at,
        "population_total_capacity": sum(caps),
    }


def _mean_food_unrest(ports: dict[str, dict]) -> float:
    """Unweighted mean `food_unrest` (0–200) across all ports in the snapshot."""
    if not ports:
        return 0.0
    n = len(ports)
    total = sum(int(p.get("food_unrest", 0)) for p in ports.values())
    return round(float(total) / float(n), 2)


def _build_snapshot(
    sim,
    tick_idx: int,
    started_at: str,
    t0: float,
    initial_pops: dict[str, int],
    port_meta: dict[str, dict],
    chart_areas: list[dict],
    goods_tiers: dict[str, str],
    world_path: Path,
) -> dict:
    m = sim.metrics()
    metrics_ports = m.get("ports", {}) or {}
    elapsed = max(1e-6, time.perf_counter() - t0)
    port_band_map = getattr(sim, "_port_inst_alliance_band", {}) or {}
    rows = []
    for pid, prow in metrics_ports.items():
        meta = port_meta.get(pid, {})
        rows.append(
            (
                pid,
                _port_row(
                    prow,
                    initial_pops.get(pid, 0),
                    str(meta.get("role", "") or ""),
                    str(meta.get("chart_area_id", "") or ""),
                    str(meta.get("name", pid) or pid),
                    float(meta.get("map_u", 0.5)),
                    float(meta.get("map_v", 0.5)),
                    int(port_band_map.get(pid, -1)),
                ),
            )
        )
    # Sort ports by population (largest first); break ties on wealth, then pid
    # for stable ordering when populations match (common at game start).
    rows.sort(key=lambda kv: (-int(kv[1]["population_grain"]), -int(kv[1]["wealth"]), kv[0]))
    ports = dict(rows)
    snap = {
        "tick": tick_idx,
        "day": int(m.get("day", sim.current_day)),
        "started_at": started_at,
        "updated_at": _utc_iso(),
        "world_path": str(twin.WORLD_PATH),
        "elapsed_s": elapsed,
        "ticks_per_sec": tick_idx / elapsed,
        "world_treasury_coins": int(m.get("world_treasury_coins", 0)),
        "npc_total_money": int(m.get("npc_total_money", 0)),
        "npc_total_balance_sheet_coins": int(m.get("npc_total_balance_sheet_coins", 0)),
        "npc_at_sea": int(m.get("npc_at_sea", 0)),
        "npc_agent_count": int(m.get("npc_agent_count", 0)),
        "riot_events_total": int(getattr(sim, "riot_events", 0)),
        "bankruptcy_events_total": int(getattr(sim, "bankruptcy_events", 0)),
        "pirate_raids_success": int(m.get("pirate_raids_success", 0)),
        "price_grain_mean": _mean_dock_buy_unit(sim, "grain"),
        "price_metal_mean": _mean_dock_buy_unit(sim, "metal"),
        "price_tier_food": _mean_dock_buy_tier(sim, "food", goods_tiers),
        "price_tier_comfort": _mean_dock_buy_tier(sim, "comfort", goods_tiers),
        "price_tier_metal": _mean_dock_buy_tier(sim, "metal", goods_tiers),
        "food_unrest_mean": _mean_food_unrest(ports),
        "pop_summary": _pop_summary(ports),
        "contracts": _build_contracts_summary(sim, m),
        "chart_areas": chart_areas,
        "regions": _build_region_rollups(ports, chart_areas),
        "alliance_bands": _build_alliance_bands(sim, world_path, metrics_ports),
        "wars": _build_wars_summary(ports),
        "goods_flow": _build_goods_flow_summary(sim),
        "ports": ports,
        "port_sort_key": "population_grain_desc",
    }
    return _round_floats(snap, 2)


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
        help="Path to world data JSON (default: tools/sim_100_days.WORLD_PATH, normally data/world_full.json).",
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
    ap.add_argument(
        "--npc-scale",
        type=float,
        default=1.0,
        help=(
            "Coarse-graining: fraction of NPC merchants to keep (0.01..4.0). "
            "Default 1.0 (no change). 0.1 keeps ~10%% of agents."
        ),
    )
    ap.add_argument(
        "--npc-mass",
        type=float,
        default=None,
        help=(
            "Per-surviving-NPC mass multiplier for fleet_ships and starting purse (0.25..12.0). "
            "If omitted with --npc-scale, defaults to 1/scale so total carrying-capacity "
            "stays roughly constant."
        ),
    )
    args = ap.parse_args()

    if args.npc_scale != 1.0 or args.npc_mass is not None:
        twin.NPC_DENSITY_SCALE = max(0.01, min(4.0, float(args.npc_scale)))
        mass = args.npc_mass
        if mass is None:
            mass = 1.0 / twin.NPC_DENSITY_SCALE if twin.NPC_DENSITY_SCALE > 0 else 1.0
        twin.NPC_MASS_SCALE = max(0.25, min(12.0, float(mass)))

    if args.world:
        twin.WORLD_PATH = Path(args.world).resolve()
        if not twin.WORLD_PATH.is_file():
            raise SystemExit(f"world file not found: {twin.WORLD_PATH}")

    import random  # local import to mirror sim_100_days conventions

    rng = random.Random(twin._RNG_SEED)
    sim = twin.Sim(rng)
    sim.load()
    initial_pops = _load_initial_populations(twin.WORLD_PATH)
    port_meta = _load_port_meta(twin.WORLD_PATH)
    chart_areas = _load_chart_areas(twin.WORLD_PATH)
    goods_tiers = _load_goods_need_tiers()

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
    cumulative_goods: dict[str, dict] = {}
    stock_state = _init_stock_tracker(sim)
    trade_cum: dict[str, float] = {
        "npc_sell_total": 0.0,
        "npc_buy_total": 0.0,
        "npc_sell_per_day": 0.0,
        "npc_buy_per_day": 0.0,
    }

    def _trend_row(snap: dict) -> dict:
        ps = snap.get("pop_summary") or {}
        ev = snap.get("events") or {}
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
            "population_total": int(ps.get("population_total", 0)),
            "population_initial_total": int(ps.get("population_initial_total", 0)),
            "population_mean": round(float(ps.get("population_mean", 0.0)), 2),
            "population_median": round(float(ps.get("population_median", 0.0)), 2),
            "ports_under_initial": int(ps.get("ports_under_initial", 0)),
            "ports_total": int(ps.get("ports_total", 0)),
            "price_grain_mean": float(snap.get("price_grain_mean", 0.0)),
            "price_metal_mean": float(snap.get("price_metal_mean", 0.0)),
            "price_tier_food": float(snap.get("price_tier_food", 0.0)),
            "price_tier_comfort": float(snap.get("price_tier_comfort", 0.0)),
            "price_tier_metal": float(snap.get("price_tier_metal", 0.0)),
            "food_unrest_mean": round(float(snap.get("food_unrest_mean", 0.0)), 2),
            "contracts_active_total": int((snap.get("contracts") or {}).get("active_total", 0)),
            "riot_delta": int(ev.get("riot_delta", 0)),
            "bust_delta": int(ev.get("bust_delta", 0)),
            "war_new_ports": int(ev.get("war_new_ports", 0)),
            "plague_new_ports": int(ev.get("plague_new_ports", 0)),
            "ports_at_war": int(ev.get("ports_at_war", 0)),
            "plague_ports": int(ev.get("plague_ports", 0)),
            "harbour_dues_tick": int((snap.get("treasury") or {}).get("harbour_dues_tick", 0)),
            "gini": float((snap.get("inequality") or {}).get("gini", 0.0)),
            "goods_net_cumulative": float(
                ((snap.get("goods_flow") or {}).get("cumulative") or {}).get("net_total", 0.0)
            ),
            "stock_change_total": float(
                ((snap.get("goods_flow") or {}).get("stock") or {}).get("stock_change_total", 0.0)
            ),
            "trade_net_inflow": float(
                ((snap.get("goods_flow") or {}).get("trade") or {}).get("net_inflow_total", 0.0)
            ),
        }

    last_snap: dict | None = None

    def _emit(snap: dict) -> None:
        nonlocal last_snap
        ev = _compute_tick_events(snap, last_snap)
        snap["events"] = ev
        snap["treasury"] = _build_treasury_summary(sim, snap, last_snap)
        snap["inequality"] = _build_inequality_summary(
            snap.get("ports") or {}, (last_snap or {}).get("ports")
        )
        _attach_cumulative_goods_flow(snap, cumulative_goods)
        _attach_goods_flow_extras(snap, cumulative_goods, stock_state, trade_cum)
        last_snap = snap
        _atomic_write_json(snap_path, snap)
        if trend_path is not None:
            with trend_path.open("a") as fh:
                fh.write(json.dumps(_trend_row(snap)) + "\n")
        if timeline_path is not None:
            with timeline_path.open("a") as fh:
                fh.write(json.dumps(snap) + "\n")

    # Emit a tick 0 snapshot so viewers see baseline before any advance.
    snap = _build_snapshot(sim, 0, started_at, t0, initial_pops, port_meta, chart_areas, goods_tiers, twin.WORLD_PATH)
    _emit(snap)
    if not args.quiet:
        print(
            f"# streaming twin :: world={twin.WORLD_PATH}  total_ticks={args.days}  every={args.every}  "
            f"snapshot={snap_path}  trend={trend_path or '-'}  timeline={timeline_path or '-'}"
        )
        if twin.NPC_DENSITY_SCALE != 1.0 or twin.NPC_MASS_SCALE != 1.0:
            agents = len(sim.npc_agents)
            hulls = sum(int(a.get("fleet_ships", 1)) for a in sim.npc_agents)
            print(
                f"# coarse-grained :: npc-scale={twin.NPC_DENSITY_SCALE:g}  "
                f"npc-mass={twin.NPC_MASS_SCALE:g}  agents={agents}  hulls={hulls}"
            )
        _print_line(snap)

    every = max(1, int(args.every))
    pause = max(0, int(args.pause_ms)) / 1000.0

    try:
        for i in range(1, int(args.days) + 1):
            sim.advance_day()
            _accumulate_goods_flow_tick(cumulative_goods, sim)
            _accumulate_stock_tick(stock_state, sim)
            _accumulate_trade_tick(trade_cum, sim)
            if i % every == 0 or i == int(args.days):
                snap = _build_snapshot(
                    sim, i, started_at, t0, initial_pops, port_meta, chart_areas, goods_tiers, twin.WORLD_PATH
                )
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

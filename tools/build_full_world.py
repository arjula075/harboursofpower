"""
Build `data/world_full.json` from `docs/world_with_npc_networked_node_map.json`.

1. Loads the networked world (same 75 ports / full `lanes` mesh as the revised doc, plus `npc_lanes`
   and `networked_node_map`).
2. Adds `chart_areas` (regions) and per-port `chart_area_id`.
3. Sets `npc_city_grain_contracts_enabled` for current gameplay parity.
4. Applies Carthage / Ostia balance overrides (population, grain seed, existential war threshold).
5. Removes Gibraltar strait **bypass** edges from `npc_lanes` only (Carthage↔Tingis, Hippo↔Tingis
   long open-sea hops) so NPC routing must use Gades/Malaka; full `lanes` mesh unchanged for the player.
6. Rebuilds `networked_node_map.adjacency` + counts from the filtered `npc_lanes`.
7. Rounds full-mesh `lanes` days to int ≥ 1 (drops `travel_type` on lanes only).
8. Drops descriptive-only keys not consumed by the game: `good_sources`, `resource_sites`,
   `simulation_tuning`, `trade_network_rules`.

Run from repo root:  python3 tools/build_full_world.py
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "docs" / "world_with_npc_networked_node_map.json"
DST = ROOT / "data" / "world_full.json"

# Undirected pairs to drop from npc_lanes (Gibraltar choke — keep Tingis↔Iberia coastal hops).
NPC_TINGIS_BYPASS_PAIRS = frozenset(
    {
        frozenset({"carthage", "tingis"}),
        frozenset({"hippo", "tingis"}),
    }
)


CHART_AREAS = [
    {
        "id": "iberia_gaul",
        "name": "Iberian coast & Ligurian sea",
        "description": "Atlantic gateway and the Gallo-Iberian rim — Gades, Massalia, the Catalan strand.",
    },
    {
        "id": "tyrrhenian",
        "name": "Tyrrhenian sea & approaches",
        "description": "Italian west coast, Sardinia, Corsica, Latium and Campania.",
    },
    {
        "id": "sicily_ionian",
        "name": "Sicily & Ionian basin",
        "description": "Sicilian roadsteads and the heel-and-toe of Italy.",
    },
    {
        "id": "north_africa",
        "name": "North African coast",
        "description": "Carthaginian capital and the Tripolitanian and Mauretanian shores.",
    },
    {
        "id": "egypt_cyrenaica",
        "name": "Egypt & Cyrenaica",
        "description": "Cyrenaican headlands and the Nile-mouth grain hubs.",
    },
    {
        "id": "aegean",
        "name": "Aegean & Cretan sea",
        "description": "Mainland Greece, the Aegean islands, western Anatolia and Crete.",
    },
    {
        "id": "levant_cyprus",
        "name": "Levant & Cyprus",
        "description": "Phoenician home ports and the Cypriot ring.",
    },
    {
        "id": "propontis_pontus",
        "name": "Propontis & Pontus Euxinus",
        "description": "Marmara mouth and the Black Sea grain horizon.",
    },
]

PORT_TO_AREA: dict[str, str] = {
    "gades": "iberia_gaul",
    "malaka": "iberia_gaul",
    "sexi": "iberia_gaul",
    "carthago_nova": "iberia_gaul",
    "rhode_iberia": "iberia_gaul",
    "emporion": "iberia_gaul",
    "antipolis": "iberia_gaul",
    "nikaia": "iberia_gaul",
    "massalia": "iberia_gaul",
    "aleria": "tyrrhenian",
    "populonia": "tyrrhenian",
    "pyrgi": "tyrrhenian",
    "caere": "tyrrhenian",
    "rome": "tyrrhenian",
    "ostia": "tyrrhenian",
    "cumae": "tyrrhenian",
    "neapolis": "tyrrhenian",
    "olbia_sardinia": "tyrrhenian",
    "tharros": "tyrrhenian",
    "sulci": "tyrrhenian",
    "caralis": "tyrrhenian",
    "poseidonia": "tyrrhenian",
    "panormus": "sicily_ionian",
    "motya": "sicily_ionian",
    "solus": "sicily_ionian",
    "selinus": "sicily_ionian",
    "akragas": "sicily_ionian",
    "gela": "sicily_ionian",
    "syracuse": "sicily_ionian",
    "catane": "sicily_ionian",
    "naxos_sicily": "sicily_ionian",
    "messana": "sicily_ionian",
    "rhegium": "sicily_ionian",
    "locri": "sicily_ionian",
    "croton": "sicily_ionian",
    "taras": "sicily_ionian",
    "tingis": "north_africa",
    "hippo": "north_africa",
    "utica": "north_africa",
    "carthage": "north_africa",
    "oea": "north_africa",
    "sabratha": "north_africa",
    "leptis_magna": "north_africa",
    "cyrene": "egypt_cyrenaica",
    "apollonia_cyrenaica": "egypt_cyrenaica",
    "naucratis": "egypt_cyrenaica",
    "alexandria": "egypt_cyrenaica",
    "memphis": "egypt_cyrenaica",
    "corinth": "aegean",
    "megara": "aegean",
    "athens_piraeus": "aegean",
    "chalcis": "aegean",
    "eretria": "aegean",
    "gythion": "aegean",
    "smyrna": "aegean",
    "ephesus": "aegean",
    "miletus": "aegean",
    "halicarnassus": "aegean",
    "rhodes": "aegean",
    "knossos": "aegean",
    "kydonia": "aegean",
    "paphos": "levant_cyprus",
    "kition": "levant_cyprus",
    "salamis_cyprus": "levant_cyprus",
    "arados": "levant_cyprus",
    "byblos": "levant_cyprus",
    "sidon": "levant_cyprus",
    "tyre": "levant_cyprus",
    "byzantion": "propontis_pontus",
    "chalcedon": "propontis_pontus",
    "sinope": "propontis_pontus",
    "trapezus": "propontis_pontus",
    "olbia_pontic": "propontis_pontus",
    "chersonesos": "propontis_pontus",
    "pantikapaion": "propontis_pontus",
}

PORT_OVERRIDES: dict[str, dict] = {
    "ostia": {
        "population_grain_per_day": 11,
        "initial_stock_overrides": {"grain": 168},
    },
    "carthage": {
        "population_grain_per_day": 16,
        "population_existential_war_burst_days": 68,
        "initial_stock_overrides": {"grain": 228},
    },
}

DROP_TOP_LEVEL_KEYS = (
    "good_sources",
    "resource_sites",
    "simulation_tuning",
    "trade_network_rules",
)


def _filter_npc_lanes(raw: list) -> list[dict]:
    out: list[dict] = []
    for e in raw:
        if not isinstance(e, dict):
            continue
        a = str(e.get("from", ""))
        b = str(e.get("to", ""))
        if not a or not b:
            continue
        if frozenset({a, b}) in NPC_TINGIS_BYPASS_PAIRS:
            continue
        d = float(e.get("days", 1))
        tt = str(e.get("travel_type", "coastal"))
        out.append({"from": a, "to": b, "days": d, "travel_type": tt})
    return out


def _rebuild_networked_node_map(src_nm: dict, npc_lanes: list[dict], port_ids: list[str]) -> dict:
    adj: dict[str, list[dict]] = defaultdict(list)
    for e in npc_lanes:
        adj[e["from"]].append(
            {"to": e["to"], "days": e["days"], "travel_type": e.get("travel_type", "coastal")}
        )
    for pid in port_ids:
        adj.setdefault(pid, [])
    return {
        "purpose": str(src_nm.get("purpose", "")),
        "design_rule": str(src_nm.get("design_rule", ""))
        + " Gibraltar bypass (Carthage/Hippo direct to Tingis) removed from npc_lanes; route via Iberian ports.",
        "node_count": len(port_ids),
        "directed_edge_count": len(npc_lanes),
        "uses_port_ids_from": str(src_nm.get("uses_port_ids_from", "ports")),
        "preferred_for": list(src_nm.get("preferred_for", [])),
        "keep_complete_lanes_for": list(src_nm.get("keep_complete_lanes_for", [])),
        "adjacency": {k: adj[k] for k in sorted(adj.keys())},
    }


def main() -> None:
    src = json.loads(SRC.read_text())

    port_ids = [p["id"] for p in src["ports"]]
    missing = [pid for pid in port_ids if pid not in PORT_TO_AREA]
    if missing:
        raise SystemExit(f"PORT_TO_AREA missing entries for: {missing}")
    extra = [pid for pid in PORT_TO_AREA if pid not in port_ids]
    if extra:
        print(f"  warn: PORT_TO_AREA has stale ids (no matching port): {extra}")

    raw_npc = src.get("npc_lanes") or []
    if not isinstance(raw_npc, list):
        raw_npc = []
    npc_filtered = _filter_npc_lanes(raw_npc)
    src_nm = src.get("networked_node_map") if isinstance(src.get("networked_node_map"), dict) else {}
    networked = _rebuild_networked_node_map(src_nm, npc_filtered, port_ids)

    out: dict = {}
    out["autonomy_warmup_days"] = src.get("autonomy_warmup_days", 24)
    out["npc_city_grain_contracts_enabled"] = True
    out["initial_treasury_coins"] = src.get("initial_treasury_coins", 9600)
    out["port_role_wealth_bonuses"] = src.get("port_role_wealth_bonuses", {})
    out["chart_areas"] = CHART_AREAS

    new_ports: list[dict] = []
    for p in src["ports"]:
        pid = p["id"]
        np: dict = dict(p)
        np["chart_area_id"] = PORT_TO_AREA[pid]
        ov = PORT_OVERRIDES.get(pid, {})
        for k, v in ov.items():
            if k == "initial_stock_overrides":
                stock = dict(np.get("initial_stock", {}))
                stock.update(v)
                np["initial_stock"] = stock
            else:
                np[k] = v
        new_ports.append(np)
    out["ports"] = new_ports

    out["farms"] = list(src.get("farms", []))
    out["mines"] = list(src.get("mines", []))

    clean_lanes: list[dict] = []
    for ln in src.get("lanes", []):
        a = str(ln.get("from", ""))
        b = str(ln.get("to", ""))
        d = max(1, int(round(float(ln.get("days", 1)))))
        if a and b:
            clean_lanes.append({"from": a, "to": b, "days": d})
    out["lanes"] = clean_lanes

    out["npc_lanes"] = npc_filtered
    out["networked_node_map"] = networked

    if "port_cultures" in src:
        out["port_cultures"] = src["port_cultures"]
    if "port_shipyards" in src:
        out["port_shipyards"] = src["port_shipyards"]

    for k in DROP_TOP_LEVEL_KEYS:
        out.pop(k, None)

    DST.parent.mkdir(parents=True, exist_ok=True)
    DST.write_text(json.dumps(out, indent=2) + "\n")
    print(f"Wrote {DST.relative_to(ROOT)}")
    print(
        f"  ports={len(out['ports'])}, farms={len(out['farms'])}, mines={len(out['mines'])}, "
        f"lanes={len(out['lanes'])}, npc_lanes={len(out['npc_lanes'])}, chart_areas={len(out['chart_areas'])}"
    )
    print(
        "  npc_traders sum =",
        sum(int(p.get("npc_traders", 0)) for p in out["ports"]),
    )
    print(f"  npc_lanes removed (bypass): {len(raw_npc) - len(npc_filtered)}")


if __name__ == "__main__":
    main()

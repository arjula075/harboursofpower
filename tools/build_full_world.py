"""
Build `data/world_full.json` from `docs/world_with_npc_networked_node_map.json`.

1. Loads the networked world (same 75 base ports / full `lanes` mesh as the revised doc, plus `npc_lanes`
   and `networked_node_map`).
2. Adds `chart_areas` (regions) and per-port `chart_area_id`.
3. Appends **five feeder roadsteads** (rusellae, baelo, saguntum, notium, mylae) with farms, player `lanes`,
   and `npc_lanes` into former choke hubs; those ports set `war_recurring: false`.
4. Sets `npc_city_grain_contracts_enabled` for current gameplay parity.
5. Adds root `institutional_trade` (Phase 0 schema catalogue; mirrors civic grain in runtime; Phase 3 alliance bands + Phase 4 patronage knobs when present).
6. Applies Carthage / Ostia balance overrides (population, grain seed, existential war threshold).
7. Removes Gibraltar strait **bypass** edges from `npc_lanes` only (Carthage↔Tingis, Hippo↔Tingis
   long open-sea hops) so NPC routing must use Gades/Malaka; full `lanes` mesh unchanged for the player except feeder appendices.
8. Rebuilds `networked_node_map.adjacency` + counts from the merged `npc_lanes`.
9. Rounds full-mesh `lanes` days to int ≥ 1 (drops `travel_type` on lanes only).
10. Drops descriptive-only keys not consumed by the game: `good_sources`, `resource_sites`,
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
        "id": "iberia_atlantic",
        "name": "Atlantic Iberia (Gades)",
        "description": "Gades and the Atlantic facade west of the Pillars.",
    },
    {
        "id": "gibraltar_strait",
        "name": "Strait of Gibraltar",
        "description": "Pillars of Hercules — Gades, Sexi, Tingis, and the channel.",
    },
    {
        "id": "iberia_east",
        "name": "Iberian Mediterranean coast",
        "description": "Baetis to Emporion — Nova Carthago and the Catalan shore.",
    },
    {
        "id": "ligurian",
        "name": "Ligurian sea & Gulf of Lion",
        "description": "Massalia, Narbonensis, and the Gallic littoral.",
    },
    {
        "id": "tyrrhenian_etruria",
        "name": "Etruria & north Tyrrhenian",
        "description": "Populonia, Caere, Pyrgi, and the Tuscan littoral.",
    },
    {
        "id": "tyrrhenian_sardinia",
        "name": "Sardinia",
        "description": "Caralis, Sulci, Tharros, and Olbia.",
    },
    {
        "id": "tyrrhenian_latium",
        "name": "Latium & Campania",
        "description": "Rome, Ostia, Naples, Cumae, and the Tyrrhenian toe.",
    },
    {
        "id": "sicily_island",
        "name": "Sicily",
        "description": "Panormus to Syracuse — the Sicilian ring.",
    },
    {
        "id": "strait_messina",
        "name": "Strait of Messina",
        "description": "Messana, Rhegium, and the narrows to Magna Graecia.",
    },
    {
        "id": "magna_graecia",
        "name": "Magna Graecia",
        "description": "Taras, Croton, Locri, and the Calabrian instep.",
    },
    {
        "id": "tunisia_carthage",
        "name": "Tunisia & Carthage",
        "description": "Carthage, Utica, Hippo, and the shore opposite Sicily.",
    },
    {
        "id": "libya_tripolitania",
        "name": "Tripolitania",
        "description": "Oea, Sabratha, and Leptis Magna.",
    },
    {
        "id": "cyrenaica",
        "name": "Cyrenaica",
        "description": "Cyrene and Apollonia — the Libyan pentapolis coast.",
    },
    {
        "id": "nile_delta",
        "name": "Nile delta & Egypt",
        "description": "Alexandria, Naucratis, Memphis, and the grain mouths.",
    },
    {
        "id": "greece_mainland",
        "name": "Greece (mainland)",
        "description": "Athens, Corinth, Megara, and the Peloponnese approaches.",
    },
    {
        "id": "ionia_caria",
        "name": "Ionia & Caria",
        "description": "Smyrna, Ephesus, Miletus, Halicarnassus.",
    },
    {
        "id": "crete_dodecanese",
        "name": "Crete & Dodecanese",
        "description": "Knossos, Rhodes, and the southern Aegean gate.",
    },
    {
        "id": "cyprus",
        "name": "Cyprus",
        "description": "Salamis, Kition, Paphos, and the copper isle.",
    },
    {
        "id": "phoenicia",
        "name": "Phoenicia & Levant coast",
        "description": "Tyre, Sidon, Byblos, and the Syrian strand.",
    },
    {
        "id": "propontis",
        "name": "Propontis (Marmara)",
        "description": "Byzantium and Chalcedon — Marmara mouth.",
    },
    {
        "id": "pontus_euxinus",
        "name": "Pontus Euxinus",
        "description": "Sinope, Trapezus, Olbia, and the Black Sea grain horizon.",
    },
]

PORT_TO_AREA: dict[str, str] = {
    "gades": "gibraltar_strait",
    "malaka": "gibraltar_strait",
    "sexi": "gibraltar_strait",
    "tingis": "gibraltar_strait",
    "carthago_nova": "iberia_east",
    "baelo": "iberia_east",
    "saguntum": "iberia_east",
    "rhode_iberia": "iberia_east",
    "emporion": "iberia_east",
    "antipolis": "ligurian",
    "nikaia": "ligurian",
    "massalia": "ligurian",
    "aleria": "tyrrhenian_etruria",
    "populonia": "tyrrhenian_etruria",
    "pyrgi": "tyrrhenian_etruria",
    "caere": "tyrrhenian_etruria",
    "rome": "tyrrhenian_latium",
    "rusellae": "tyrrhenian_latium",
    "ostia": "tyrrhenian_latium",
    "cumae": "tyrrhenian_latium",
    "neapolis": "tyrrhenian_latium",
    "olbia_sardinia": "tyrrhenian_sardinia",
    "tharros": "tyrrhenian_sardinia",
    "sulci": "tyrrhenian_sardinia",
    "caralis": "tyrrhenian_sardinia",
    "poseidonia": "tyrrhenian_latium",
    "panormus": "sicily_island",
    "motya": "sicily_island",
    "solus": "sicily_island",
    "selinus": "sicily_island",
    "akragas": "sicily_island",
    "gela": "sicily_island",
    "syracuse": "sicily_island",
    "catane": "sicily_island",
    "naxos_sicily": "sicily_island",
    "messana": "strait_messina",
    "mylae": "sicily_island",
    "rhegium": "strait_messina",
    "locri": "magna_graecia",
    "croton": "magna_graecia",
    "taras": "magna_graecia",
    "hippo": "tunisia_carthage",
    "utica": "tunisia_carthage",
    "carthage": "tunisia_carthage",
    "oea": "libya_tripolitania",
    "sabratha": "libya_tripolitania",
    "leptis_magna": "libya_tripolitania",
    "cyrene": "cyrenaica",
    "apollonia_cyrenaica": "cyrenaica",
    "naucratis": "nile_delta",
    "alexandria": "nile_delta",
    "memphis": "nile_delta",
    "corinth": "greece_mainland",
    "megara": "greece_mainland",
    "athens_piraeus": "greece_mainland",
    "chalcis": "greece_mainland",
    "eretria": "greece_mainland",
    "gythion": "greece_mainland",
    "smyrna": "ionia_caria",
    "ephesus": "ionia_caria",
    "miletus": "ionia_caria",
    "notium": "ionia_caria",
    "halicarnassus": "ionia_caria",
    "rhodes": "crete_dodecanese",
    "knossos": "crete_dodecanese",
    "kydonia": "crete_dodecanese",
    "paphos": "cyprus",
    "kition": "cyprus",
    "salamis_cyprus": "cyprus",
    "arados": "phoenicia",
    "byblos": "phoenicia",
    "sidon": "phoenicia",
    "tyre": "phoenicia",
    "byzantion": "propontis",
    "chalcedon": "propontis",
    "sinope": "pontus_euxinus",
    "trapezus": "pontus_euxinus",
    "olbia_pontic": "pontus_euxinus",
    "chersonesos": "pontus_euxinus",
    "pantikapaion": "pontus_euxinus",
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

# Farm grain-per-day floor for the non-Nile breadbasket bracket.
# Egypt's Nile delta (memphis 30, naucratis 30, alexandria 26) was previously
# 2.5x the next tier (everyone else at 12), which depopulated the rest of the
# Mediterranean. Lift Sicily, Cyrenaica, Phoenicia/Africa and the Pontic
# grain belt to 18 so the food gradient is less lopsided. Egypt still leads
# but no longer dominates by 250%.
FARM_GRAIN_BUMPS: dict[str, int] = {
    "akragas_hinterland": 18,
    "catane_hinterland": 18,
    "chersonesos_hinterland": 18,
    "cyrene_hinterland": 18,
    "gela_hinterland": 18,
    "hippo_hinterland": 18,
    "messana_hinterland": 18,
    "olbia_pontic_hinterland": 18,
    "panormus_hinterland": 18,
}

# Five small coastal roadsteads: extra NPC + player lanes into former degree-4 choke hubs.
# `war_recurring: false` keeps them out of the independent local-war RNG (calmer feeders).
EXTRA_FEEDER_PORTS: list[dict] = [
    {
        "id": "rusellae",
        "name": "Rusellae",
        "map_u": 0.388,
        "map_v": 0.276,
        "role": "maritime_town",
        "industrial_metal_per_day": 0,
        "industrial_wire_per_day": 0,
        "industrial_timber_per_day": 1,
        "industrial_textiles_per_day": 1,
        "initial_stock": {
            "grain": 72,
            "wine": 34,
            "salt": 22,
            "olive_oil": 26,
            "pottery": 26,
            "fish": 22,
            "timber": 16,
            "textiles": 16,
            "metal": 10,
            "wire": 7,
            "spice": 3,
            "slaves": 18,
            "gold": 0,
            "silver": 1,
        },
        "npc_traders": 18,
        "population_grain_per_day": 4,
        "population_wine_per_day": 2,
        "population_fish_per_day": 3,
        "initial_wealth": 86,
        "trade_price_bias": {"grain": -0.04},
        "npc_traders_base": 3,
        "war_recurring": False,
    },
    {
        "id": "baelo",
        "name": "Baelo Claudia",
        "map_u": 0.042,
        "map_v": 0.586,
        "role": "maritime_town",
        "industrial_metal_per_day": 0,
        "industrial_wire_per_day": 0,
        "industrial_timber_per_day": 1,
        "industrial_textiles_per_day": 1,
        "initial_stock": {
            "grain": 70,
            "wine": 38,
            "salt": 28,
            "olive_oil": 28,
            "pottery": 24,
            "fish": 36,
            "timber": 16,
            "textiles": 14,
            "metal": 12,
            "wire": 8,
            "spice": 3,
            "slaves": 18,
            "gold": 0,
            "silver": 1,
        },
        "npc_traders": 18,
        "population_grain_per_day": 4,
        "population_wine_per_day": 2,
        "population_fish_per_day": 4,
        "initial_wealth": 84,
        "trade_price_bias": {"fish": -0.04},
        "npc_traders_base": 3,
        "war_recurring": False,
    },
    {
        "id": "saguntum",
        "name": "Saguntum",
        "map_u": 0.168,
        "map_v": 0.505,
        "role": "maritime_town",
        "industrial_metal_per_day": 0,
        "industrial_wire_per_day": 0,
        "industrial_timber_per_day": 1,
        "industrial_textiles_per_day": 1,
        "initial_stock": {
            "grain": 76,
            "wine": 32,
            "salt": 24,
            "olive_oil": 26,
            "pottery": 26,
            "fish": 30,
            "timber": 17,
            "textiles": 16,
            "metal": 11,
            "wire": 8,
            "spice": 3,
            "slaves": 19,
            "gold": 0,
            "silver": 1,
        },
        "npc_traders": 19,
        "population_grain_per_day": 4,
        "population_wine_per_day": 2,
        "population_fish_per_day": 3,
        "initial_wealth": 88,
        "trade_price_bias": {},
        "npc_traders_base": 3,
        "war_recurring": False,
    },
    {
        "id": "notium",
        "name": "Notion",
        "map_u": 0.566,
        "map_v": 0.434,
        "role": "maritime_town",
        "industrial_metal_per_day": 0,
        "industrial_wire_per_day": 0,
        "industrial_timber_per_day": 1,
        "industrial_textiles_per_day": 1,
        "initial_stock": {
            "grain": 74,
            "wine": 36,
            "salt": 24,
            "olive_oil": 30,
            "pottery": 26,
            "fish": 28,
            "timber": 16,
            "textiles": 16,
            "metal": 10,
            "wire": 7,
            "spice": 3,
            "slaves": 18,
            "gold": 0,
            "silver": 1,
        },
        "npc_traders": 18,
        "population_grain_per_day": 4,
        "population_wine_per_day": 2,
        "population_fish_per_day": 3,
        "initial_wealth": 86,
        "trade_price_bias": {"grain": -0.03},
        "npc_traders_base": 3,
        "war_recurring": False,
    },
    {
        "id": "mylae",
        "name": "Mylae",
        "map_u": 0.472,
        "map_v": 0.498,
        "role": "maritime_town",
        "industrial_metal_per_day": 0,
        "industrial_wire_per_day": 0,
        "industrial_timber_per_day": 1,
        "industrial_textiles_per_day": 1,
        "initial_stock": {
            "grain": 68,
            "wine": 32,
            "salt": 22,
            "olive_oil": 26,
            "pottery": 24,
            "fish": 32,
            "timber": 15,
            "textiles": 15,
            "metal": 9,
            "wire": 7,
            "spice": 3,
            "slaves": 17,
            "gold": 0,
            "silver": 1,
        },
        "npc_traders": 18,
        "population_grain_per_day": 4,
        "population_wine_per_day": 2,
        "population_fish_per_day": 4,
        "initial_wealth": 82,
        "trade_price_bias": {"fish": -0.03},
        "npc_traders_base": 3,
        "war_recurring": False,
    },
]

EXTRA_FEEDER_FARMS: list[dict] = [
    {
        "id": "rusellae_hinterland",
        "name": "Rusellae hinterland",
        "port_id": "rusellae",
        "grain_per_day": 6,
        "wine_per_day": 3,
        "fish_per_day": 2,
    },
    {
        "id": "baelo_hinterland",
        "name": "Baelo hinterland",
        "port_id": "baelo",
        "grain_per_day": 5,
        "wine_per_day": 3,
        "fish_per_day": 4,
    },
    {
        "id": "saguntum_hinterland",
        "name": "Saguntum hinterland",
        "port_id": "saguntum",
        "grain_per_day": 6,
        "wine_per_day": 3,
        "fish_per_day": 3,
    },
    {
        "id": "notium_hinterland",
        "name": "Notion hinterland",
        "port_id": "notium",
        "grain_per_day": 5,
        "wine_per_day": 3,
        "fish_per_day": 3,
    },
    {
        "id": "mylae_hinterland",
        "name": "Mylae hinterland",
        "port_id": "mylae",
        "grain_per_day": 5,
        "wine_per_day": 3,
        "fish_per_day": 4,
    },
]

# Undirected coastal hops; _filter_npc_lanes will copy both directions as needed (source format is one row per direction sometimes — we store one row each way for clarity).
EXTRA_NPC_LANES_RAW: list[dict] = [
    {"from": "rusellae", "to": "rome", "days": 1.0, "travel_type": "coastal"},
    {"from": "rome", "to": "rusellae", "days": 1.0, "travel_type": "coastal"},
    {"from": "rusellae", "to": "pyrgi", "days": 1.5, "travel_type": "coastal"},
    {"from": "pyrgi", "to": "rusellae", "days": 1.5, "travel_type": "coastal"},
    {"from": "baelo", "to": "gades", "days": 1.0, "travel_type": "coastal"},
    {"from": "gades", "to": "baelo", "days": 1.0, "travel_type": "coastal"},
    {"from": "baelo", "to": "malaka", "days": 2.0, "travel_type": "coastal"},
    {"from": "malaka", "to": "baelo", "days": 2.0, "travel_type": "coastal"},
    {"from": "saguntum", "to": "carthago_nova", "days": 1.5, "travel_type": "coastal"},
    {"from": "carthago_nova", "to": "saguntum", "days": 1.5, "travel_type": "coastal"},
    {"from": "saguntum", "to": "emporion", "days": 2.5, "travel_type": "coastal"},
    {"from": "emporion", "to": "saguntum", "days": 2.5, "travel_type": "coastal"},
    {"from": "notium", "to": "ephesus", "days": 1.0, "travel_type": "coastal"},
    {"from": "ephesus", "to": "notium", "days": 1.0, "travel_type": "coastal"},
    {"from": "notium", "to": "smyrna", "days": 1.5, "travel_type": "coastal"},
    {"from": "smyrna", "to": "notium", "days": 1.5, "travel_type": "coastal"},
    {"from": "mylae", "to": "syracuse", "days": 1.0, "travel_type": "coastal"},
    {"from": "syracuse", "to": "mylae", "days": 1.0, "travel_type": "coastal"},
    {"from": "mylae", "to": "messana", "days": 1.0, "travel_type": "coastal"},
    {"from": "messana", "to": "mylae", "days": 1.0, "travel_type": "coastal"},
]

# Symmetric player `lanes` (int days); appended after base mesh cleanup.
EXTRA_PLAYER_LANE_TRIPS: list[tuple[str, str, int]] = [
    ("rusellae", "rome", 1),
    ("rome", "rusellae", 1),
    ("rusellae", "pyrgi", 2),
    ("pyrgi", "rusellae", 2),
    ("baelo", "gades", 1),
    ("gades", "baelo", 1),
    ("baelo", "malaka", 2),
    ("malaka", "baelo", 2),
    ("saguntum", "carthago_nova", 2),
    ("carthago_nova", "saguntum", 2),
    ("saguntum", "emporion", 3),
    ("emporion", "saguntum", 3),
    ("notium", "ephesus", 1),
    ("ephesus", "notium", 1),
    ("notium", "smyrna", 2),
    ("smyrna", "notium", 2),
    ("mylae", "syracuse", 1),
    ("syracuse", "mylae", 1),
    ("mylae", "messana", 1),
    ("messana", "mylae", 1),
]

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

    port_ids = [p["id"] for p in src["ports"]] + [p["id"] for p in EXTRA_FEEDER_PORTS]
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
    npc_extra = _filter_npc_lanes(EXTRA_NPC_LANES_RAW)
    npc_merged = npc_filtered + npc_extra
    src_nm = src.get("networked_node_map") if isinstance(src.get("networked_node_map"), dict) else {}
    networked = _rebuild_networked_node_map(src_nm, npc_merged, port_ids)
    if isinstance(networked.get("design_rule"), str):
        networked["design_rule"] += (
            " Feeder roadsteads: +5 ports (rusellae, baelo, saguntum, notium, mylae), extra npc_lanes + player lanes."
        )

    out: dict = {}
    out["autonomy_warmup_days"] = src.get("autonomy_warmup_days", 24)
    out["npc_city_grain_contracts_enabled"] = True
    out["institutional_trade"] = {
        "enabled": True,
        "contract_types": [
            "grain_delivery",
            "temple_supply",
            "military_provisioning",
            "convoy_escort",
            "harbor_priority",
            "toll_privilege",
            "exclusive_purchase",
            "city_patronage",
        ],
        "phase3": {
            "enabled": True,
            "bands": [
                ["ostia", "neapolis", "rhegium", "messana", "panormus"],
                ["carthage", "hippo", "tingis"],
            ],
            "ally_toll_mul": 0.86,
            "enemy_toll_mul": 1.14,
            "ally_buy_mul": 0.985,
            "route_ally_bonus": 0.1,
            "route_hostile_penalty": 0.24,
            "escort_same_band_p": 0.075,
        },
        "phase4": {
            "enabled": True,
            "stress_grain_days_ref": 32,
            "stress_unrest_floor": 50,
            "issuer_offer_p_mul_max": 1.52,
            "issuer_advance_scale_max": 1.16,
            "loyal_house_repute_floor": 0.5,
            "loyal_offer_p_mul": 1.11,
            "fulfill_issuer_wealth_per_qty": 0.55,
            "war_stress_add": 0.06,
        },
        "phase5": {
            "enabled": True,
        },
    }
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
    for ep in EXTRA_FEEDER_PORTS:
        pid = str(ep["id"])
        npx: dict = dict(ep)
        npx["chart_area_id"] = PORT_TO_AREA[pid]
        new_ports.append(npx)
    out["ports"] = new_ports

    bumped_farms: list[dict] = []
    for f in src.get("farms", []):
        nf = dict(f)
        fid = str(nf.get("id", ""))
        if fid in FARM_GRAIN_BUMPS:
            nf["grain_per_day"] = int(FARM_GRAIN_BUMPS[fid])
        bumped_farms.append(nf)
    bumped_farms.extend(dict(f) for f in EXTRA_FEEDER_FARMS)
    out["farms"] = bumped_farms
    out["mines"] = list(src.get("mines", []))

    clean_lanes: list[dict] = []
    for ln in src.get("lanes", []):
        a = str(ln.get("from", ""))
        b = str(ln.get("to", ""))
        d = max(1, int(round(float(ln.get("days", 1)))))
        if a and b:
            clean_lanes.append({"from": a, "to": b, "days": d})
    for trip_a, trip_b, trip_d in EXTRA_PLAYER_LANE_TRIPS:
        clean_lanes.append({"from": trip_a, "to": trip_b, "days": trip_d})
    out["lanes"] = clean_lanes

    out["npc_lanes"] = npc_merged
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
    print(f"  npc_lanes appended (feeders): {len(npc_extra)}")
    bumps_applied = sum(
        1 for f in out["farms"] if str(f.get("id", "")) in FARM_GRAIN_BUMPS
    )
    print(f"  farm grain bumps applied: {bumps_applied} (target {len(FARM_GRAIN_BUMPS)})")


if __name__ == "__main__":
    main()

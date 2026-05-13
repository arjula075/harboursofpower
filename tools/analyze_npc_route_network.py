"""
Analyse the sparse NPC route network in
`docs/world_with_npc_networked_node_map.json`.

Reports:
- Degree distribution (in/out), per-port adjacency stats
- Coastal vs open-sea split
- Connectedness (treating the graph as undirected via the bidirection check)
- Articulation ports (chokepoints whose removal would disconnect a region)
- Diameter & mean shortest-path days (Floyd–Warshall on int-rounded days)
- Hubs by betweenness centrality (approx via shortest-path counting)
- Comparison with the chart_areas I assigned in tools/build_full_world.py:
  cross-region edges, intra-region density, isolated areas
- Comparison with the full 5550-edge `lanes` mesh: redundancy ratio
"""

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "docs" / "world_with_npc_networked_node_map.json"

# Mirror PORT_TO_AREA from build_full_world.py without importing it (kept inline so
# this script stays usable even if that file is renamed). Update both together.
PORT_TO_AREA: dict[str, str] = {
    # iberia_gaul
    "gades": "iberia_gaul", "malaka": "iberia_gaul", "sexi": "iberia_gaul",
    "carthago_nova": "iberia_gaul", "rhode_iberia": "iberia_gaul",
    "emporion": "iberia_gaul", "antipolis": "iberia_gaul",
    "nikaia": "iberia_gaul", "massalia": "iberia_gaul",
    # tyrrhenian
    "aleria": "tyrrhenian", "populonia": "tyrrhenian", "pyrgi": "tyrrhenian",
    "caere": "tyrrhenian", "rome": "tyrrhenian", "ostia": "tyrrhenian",
    "cumae": "tyrrhenian", "neapolis": "tyrrhenian",
    "olbia_sardinia": "tyrrhenian", "tharros": "tyrrhenian",
    "sulci": "tyrrhenian", "caralis": "tyrrhenian", "poseidonia": "tyrrhenian",
    # sicily_ionian
    "panormus": "sicily_ionian", "motya": "sicily_ionian", "solus": "sicily_ionian",
    "selinus": "sicily_ionian", "akragas": "sicily_ionian", "gela": "sicily_ionian",
    "syracuse": "sicily_ionian", "catane": "sicily_ionian",
    "naxos_sicily": "sicily_ionian", "messana": "sicily_ionian",
    "rhegium": "sicily_ionian", "locri": "sicily_ionian",
    "croton": "sicily_ionian", "taras": "sicily_ionian",
    # north_africa
    "tingis": "north_africa", "hippo": "north_africa", "utica": "north_africa",
    "carthage": "north_africa", "oea": "north_africa",
    "sabratha": "north_africa", "leptis_magna": "north_africa",
    # egypt_cyrenaica
    "cyrene": "egypt_cyrenaica", "apollonia_cyrenaica": "egypt_cyrenaica",
    "naucratis": "egypt_cyrenaica", "alexandria": "egypt_cyrenaica",
    "memphis": "egypt_cyrenaica",
    # aegean
    "corinth": "aegean", "megara": "aegean", "athens_piraeus": "aegean",
    "chalcis": "aegean", "eretria": "aegean", "gythion": "aegean",
    "smyrna": "aegean", "ephesus": "aegean", "miletus": "aegean",
    "halicarnassus": "aegean", "rhodes": "aegean",
    "knossos": "aegean", "kydonia": "aegean",
    # levant_cyprus
    "paphos": "levant_cyprus", "kition": "levant_cyprus",
    "salamis_cyprus": "levant_cyprus", "arados": "levant_cyprus",
    "byblos": "levant_cyprus", "sidon": "levant_cyprus", "tyre": "levant_cyprus",
    # propontis_pontus
    "byzantion": "propontis_pontus", "chalcedon": "propontis_pontus",
    "sinope": "propontis_pontus", "trapezus": "propontis_pontus",
    "olbia_pontic": "propontis_pontus", "chersonesos": "propontis_pontus",
    "pantikapaion": "propontis_pontus",
}


def main() -> None:
    data = json.loads(SRC.read_text())
    ports = data["ports"]
    pid_set = {p["id"] for p in ports}
    npc_lanes = data["npc_lanes"]
    full_lanes = data["lanes"]
    nm = data["networked_node_map"]

    print("=" * 72)
    print("NPC ROUTE NETWORK — sparse maritime graph for NPC pathfinding")
    print("=" * 72)
    print(f"Design: {nm['purpose']}")
    print(f"Rule  : {nm['design_rule']}")
    print(
        f"Nodes : {nm['node_count']}   "
        f"Directed edges: {nm['directed_edge_count']}   "
        f"Full-mesh lanes (player ref): {len(full_lanes)}"
    )
    print(f"Preferred for : {', '.join(nm['preferred_for'])}")
    print(f"Full lanes for: {', '.join(nm['keep_complete_lanes_for'])}")

    # ---- 1. Adjacency stats ----
    out_deg: dict[str, int] = defaultdict(int)
    in_deg: dict[str, int] = defaultdict(int)
    edges = []           # (a, b, days, type) directed
    edges_und: dict[tuple[str, str], int] = {}  # undirected (a<=b) -> min days
    travel_split = Counter()
    for ln in npc_lanes:
        a, b = ln["from"], ln["to"]
        d = max(1, int(round(float(ln["days"]))))
        out_deg[a] += 1
        in_deg[b] += 1
        edges.append((a, b, d, ln.get("travel_type", "?")))
        travel_split[ln.get("travel_type", "?")] += 1
        key = (a, b) if a <= b else (b, a)
        prev = edges_und.get(key)
        edges_und[key] = d if prev is None else min(prev, d)
    # symmetry check
    asymmetric = sum(1 for (a, b) in edges_und if (a, b) not in {(e[0], e[1]) for e in edges} or (b, a) not in {(e[0], e[1]) for e in edges})

    print("\n-- Adjacency stats --")
    print(
        f"out-degree min/mean/max: {min(out_deg.values())} / "
        f"{round(sum(out_deg.values())/len(out_deg),2)} / {max(out_deg.values())}"
    )
    print(
        f"in-degree  min/mean/max: {min(in_deg.values())} / "
        f"{round(sum(in_deg.values())/len(in_deg),2)} / {max(in_deg.values())}"
    )
    print(f"travel_type split: coastal={travel_split['coastal']}  open_sea={travel_split['open_sea']}")
    days_int = [d for _, _, d, _ in edges]
    print(
        f"hop length (int-rounded days): min={min(days_int)} mean={round(sum(days_int)/len(days_int),2)} "
        f"max={max(days_int)}"
    )
    print(f"undirected edges: {len(edges_und)} (perfect bidirectional: {sum(1 for (a,b) in edges_und if (b,a,) in {(e[0],e[1]) for e in edges} and (a,b) in {(e[0],e[1]) for e in edges})})")

    # Hubs by total degree
    deg = {pid: out_deg.get(pid, 0) + in_deg.get(pid, 0) for pid in pid_set}
    top = sorted(deg.items(), key=lambda kv: -kv[1])[:12]
    print("\n-- Top-degree hubs (out+in) --")
    for pid, k in top:
        print(f"  {pid:22s} deg={k:2d}  ({PORT_TO_AREA.get(pid, '?')})")

    # ---- 2. Build undirected adjacency for connectivity / paths ----
    adj_und: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for (a, b), d in edges_und.items():
        adj_und[a].append((b, d))
        adj_und[b].append((a, d))

    # BFS components
    def bfs_component(start: str) -> set[str]:
        seen = {start}
        q = deque([start])
        while q:
            v = q.popleft()
            for nb, _ in adj_und[v]:
                if nb not in seen:
                    seen.add(nb)
                    q.append(nb)
        return seen

    components: list[set[str]] = []
    remaining = set(pid_set)
    while remaining:
        s = next(iter(remaining))
        comp = bfs_component(s)
        components.append(comp)
        remaining -= comp
    print("\n-- Connectivity --")
    print(f"Connected components: {len(components)}")
    for i, c in enumerate(sorted(components, key=len, reverse=True)):
        print(f"  comp[{i}] size={len(c)} sample={sorted(c)[:6]}")

    # ---- 3. Articulation points (Tarjan, undirected, on biggest comp) ----
    biggest = max(components, key=len)
    disc: dict[str, int] = {}
    low: dict[str, int] = {}
    parent: dict[str, str | None] = {}
    timer = [0]
    arts: set[str] = set()

    def dfs(u: str) -> None:
        disc[u] = low[u] = timer[0]
        timer[0] += 1
        children = 0
        for nb, _ in adj_und[u]:
            if nb not in disc:
                parent[nb] = u
                children += 1
                dfs(nb)
                low[u] = min(low[u], low[nb])
                if parent.get(u) is None and children > 1:
                    arts.add(u)
                if parent.get(u) is not None and low[nb] >= disc[u]:
                    arts.add(u)
            elif nb != parent.get(u):
                low[u] = min(low[u], disc[nb])

    import sys

    sys.setrecursionlimit(2000)
    start = sorted(biggest)[0]
    parent[start] = None
    dfs(start)
    print(f"\n-- Articulation ports (chokepoints) in biggest component (n={len(biggest)}) --")
    if arts:
        for a in sorted(arts):
            print(f"  {a:22s} deg={deg[a]:2d}  ({PORT_TO_AREA.get(a, '?')})")
    else:
        print("  (none — graph has no single-port chokepoints)")

    # ---- 4. Floyd–Warshall on int-rounded days, biggest component only ----
    print("\n-- Shortest-path stats (int-rounded days, biggest comp) --")
    nodes = sorted(biggest)
    idx = {n: i for i, n in enumerate(nodes)}
    N = len(nodes)
    INF = 10**9
    dist = [[INF] * N for _ in range(N)]
    for i in range(N):
        dist[i][i] = 0
    for (a, b), d in edges_und.items():
        if a in idx and b in idx:
            i, j = idx[a], idx[b]
            if d < dist[i][j]:
                dist[i][j] = dist[j][i] = d
    for k in range(N):
        dk = dist[k]
        for i in range(N):
            di = dist[i]
            dik = di[k]
            if dik == INF:
                continue
            for j in range(N):
                v = dik + dk[j]
                if v < di[j]:
                    di[j] = v
    all_d = [dist[i][j] for i in range(N) for j in range(i + 1, N) if dist[i][j] < INF]
    print(f"  pairs evaluated: {len(all_d)}")
    print(
        f"  mean = {round(sum(all_d)/len(all_d),2)} days   "
        f"median ≈ {sorted(all_d)[len(all_d)//2]} days   "
        f"max (diameter) = {max(all_d)} days"
    )
    # Most distant pair(s)
    far = []
    dmax = max(all_d)
    for i in range(N):
        for j in range(i + 1, N):
            if dist[i][j] == dmax:
                far.append((nodes[i], nodes[j]))
    print(f"  diameter pair(s) at {dmax}d:")
    for a, b in far[:6]:
        print(f"    {a:22s} <-> {b:22s}")

    # ---- 5. Region cohesion (chart_areas vs npc_lanes) ----
    print("\n-- Region cohesion (chart_areas mapping vs npc_lanes) --")
    area_internal: dict[str, int] = defaultdict(int)
    area_external: dict[str, int] = defaultdict(int)
    cross_pairs: Counter = Counter()
    for (a, b), _ in edges_und.items():
        aa, ba = PORT_TO_AREA.get(a, "?"), PORT_TO_AREA.get(b, "?")
        if aa == ba:
            area_internal[aa] += 1
        else:
            area_external[aa] += 1
            area_external[ba] += 1
            key = tuple(sorted([aa, ba]))
            cross_pairs[key] += 1
    sizes = Counter(PORT_TO_AREA.values())
    print(f"  {'area':22s} {'ports':>5s} {'intra':>5s} {'inter':>5s} {'density':>9s}")
    for area in sorted(sizes):
        n = sizes[area]
        intra = area_internal[area]
        inter = area_external[area]
        max_intra = n * (n - 1) // 2 if n > 1 else 0
        dens = round(intra / max_intra, 2) if max_intra else float("nan")
        print(f"  {area:22s} {n:>5d} {intra:>5d} {inter:>5d} {dens:>9.2f}")
    print("\n  inter-region bridges (undirected edge counts, top 12):")
    for (a, b), n in cross_pairs.most_common(12):
        print(f"    {a:22s} <-> {b:22s}  edges={n}")

    # ---- 6. Compare to full lanes mesh ----
    print("\n-- vs. full lanes mesh --")
    full_und = {tuple(sorted([ln["from"], ln["to"]])) for ln in full_lanes}
    npc_und = set(edges_und.keys())
    print(f"  full mesh undirected pairs : {len(full_und)}")
    print(f"  npc graph undirected pairs : {len(npc_und)}")
    print(f"  overlap (npc ⊆ full?)      : {len(npc_und & full_und)} / {len(npc_und)}")
    print(f"  npc edges not in full mesh : {len(npc_und - full_und)}  (should be 0)")

    # ---- 7. Per-port avg outbound days summary (helps voyage cost feel) ----
    print("\n-- avg coastal hop (rounded days) per area --")
    by_area_hop: dict[str, list[int]] = defaultdict(list)
    for a, b, d, _ in edges:
        if PORT_TO_AREA.get(a) == PORT_TO_AREA.get(b):
            by_area_hop[PORT_TO_AREA.get(a, "?")].append(d)
    for area in sorted(by_area_hop):
        hs = by_area_hop[area]
        print(f"  {area:22s} mean hop ≈ {round(sum(hs)/len(hs), 2)} d   "
              f"(n={len(hs)}, min={min(hs)}, max={max(hs)})")


if __name__ == "__main__":
    main()

import {
  Callout,
  Card,
  CardBody,
  CardHeader,
  Code,
  Divider,
  Grid,
  H1,
  H2,
  H3,
  Pill,
  Row,
  Stack,
  Stat,
  Table,
  Text,
  TodoListCard,
  type TodoItem,
  type TodoStatus,
  useCanvasState,
} from "cursor/canvas";

/**
 * Single SAFe-style backlog: Epics → Features → acceptance outcomes.
 * Detail lives in referenced canvases; update feature status here when scope ships.
 *
 * HOW TO VIEW (not edit TSX): Cmd+Shift+P → "Open Canvas" → this file.
 * File-tree double-click opens Source; switch to Preview in the tab or use Open Canvas.
 * See canvases/README.md
 */

type FeatureStatus = TodoStatus | "deferred";

interface SafeFeature {
  id: string;
  name: string;
  status: FeatureStatus;
  acceptance: string;
  enabler?: boolean;
  detailCanvas: string;
  codePaths?: string;
}

interface Epic {
  id: string;
  title: string;
  pi: string;
  horizon: string;
  intent: string;
  primaryCanvas: string;
  secondaryCanvases?: string[];
  features: SafeFeature[];
}

const EPICS: Epic[] = [
  {
    id: "EPIC-ECON",
    title: "Living economy & twin credibility",
    pi: "PI-1 · Now",
    horizon: "A — Economy & civic money",
    intent:
      "NPC traffic, pricing, specie, duties, and institutional flows stay believable at 5k-day horizons; Godot and Python twin stay aligned. Behavioural variety via OCEAN is shipped; personhood (names, history, player + NPC social memory) lives in EPIC-NPC.",
    primaryCanvas: "harbours-economy-rules.canvas.tsx",
    secondaryCanvases: [
      "harbours-implementation-plan.canvas.tsx",
      "harbours-institutional-trade-roadmap.canvas.tsx",
    ],
    features: [
      {
        id: "FEAT-ECON-01",
        name: "Autonomous economy warmup",
        status: "completed",
        acceptance: "New campaign runs NPC-only warmup days from world_full.json; twin mirrors on Sim.load.",
        detailCanvas: "harbours-implementation-plan.canvas.tsx",
        codePaths: "game_state.gd, sim_100_days.py, data/world_full.json",
      },
      {
        id: "FEAT-ECON-02",
        name: "Named tick agents & phase order",
        status: "completed",
        acceptance:
          "Information → production → trade/dues/cartel → unrest → war → demographics → merchant sync; documented in economy-rules canvas.",
        detailCanvas: "harbours-economy-rules.canvas.tsx",
        codePaths: "game_state.gd, sim_tick_agents.gd",
      },
      {
        id: "FEAT-ECON-03",
        name: "NPC personality (OCEAN-style)",
        status: "completed",
        acceptance:
          "Five traits affect depart, memory, lots, wholesale, purse floor, voyage stress, hull behaviour; not yet tied to faction cartels.",
        detailCanvas: "harbours-economy-rules.canvas.tsx",
      },
      {
        id: "FEAT-ECON-04",
        name: "Merchant liquidity tuning",
        status: "completed",
        acceptance:
          "Softer trait coefficients, better wholesale mults, reserve/rookie/grace; bankruptcies measurable in twin.",
        detailCanvas: "harbours-implementation-plan.canvas.tsx",
      },
      {
        id: "FEAT-ECON-05",
        name: "Closed-loop specie & civic mint",
        status: "completed",
        acceptance: "Mint, treasury, bullion flows; wealth attractor excludes bullion where intended.",
        detailCanvas: "harbours-combined-delivery-roadmap.canvas.tsx",
      },
      {
        id: "FEAT-ECON-06",
        name: "Luxury far-trade queue",
        status: "completed",
        acceptance: "Delayed consignments, luxury stock, explicit coin sink; twin parity.",
        detailCanvas: "harbours-combined-delivery-roadmap.canvas.tsx",
      },
      {
        id: "FEAT-ECON-07",
        name: "Import duties & dock graft v1",
        status: "completed",
        acceptance:
          "Per-port tolls on city sales, NPC smuggle/pay, player graft UI, wholesale relief; twin parity.",
        detailCanvas: "harbours-economy-rules.canvas.tsx",
      },
      {
        id: "FEAT-ECON-08",
        name: "5k-day economy tuning pass",
        status: "in_progress",
        acceptance:
          "Twin report: NPC purse drift, food riots, merchant bankruptcies, treasury, worst/best ports by grain-days and unrest within targets.",
        detailCanvas: "harbours-combined-delivery-roadmap.canvas.tsx",
        codePaths: "tools/sim_100_days.py (5000 --no-graphs)",
      },
      {
        id: "FEAT-ECON-09",
        name: "Conditional NPC bankruptcy relief",
        status: "pending",
        acceptance:
          "Only if 5k twin still shows excessive bankruptcies: fee discount or officer-pay carve-out; re-measure before ship.",
        detailCanvas: "harbours-implementation-plan.canvas.tsx",
      },
    ],
  },
  {
    id: "EPIC-NPC",
    title: "NPCs as persons",
    pi: "PI-2 · Next",
    horizon: "A → B — Living world & people",
    intent:
      "Merchants and captains feel like people in a truly living world. OCEAN traits drive behaviour today; add stable identity, names, traceable history, relationship memory with the player on player interaction, and pairwise memory between NPCs when they interact in the sim (trade, rivalry, deals) — so the world has social continuity even when the player is absent.",
    primaryCanvas: "harbours-long-term-implementation-plan.canvas.tsx",
    secondaryCanvases: [
      "harbours-economy-rules.canvas.tsx",
      "harbours-use-case-map.canvas.tsx",
      "harbours-implementation-plan.canvas.tsx",
    ],
    features: [
      {
        id: "FEAT-NPC-01",
        name: "OCEAN behavioural traits (floor)",
        status: "completed",
        acceptance:
          "Five persisted traits affect trade, voyage, and hull decisions; documented in economy-rules; id-seeded on load.",
        detailCanvas: "harbours-economy-rules.canvas.tsx",
        codePaths: "game_state.gd, sim_100_days.py",
      },
      {
        id: "FEAT-NPC-02",
        name: "Stable NPC identity model",
        status: "pending",
        acceptance:
          "Each merchant/captain has persistent id across sessions; no re-roll of personality on same entity; SAVE_VERSION migration documented.",
        detailCanvas: "harbours-long-term-implementation-plan.canvas.tsx",
        enabler: true,
      },
      {
        id: "FEAT-NPC-03",
        name: "Procedural names & display titles",
        status: "pending",
        acceptance:
          "Culture-appropriate names (and optional epithets) generated from port/home culture + seed; shown in UI and logs where NPC referenced.",
        detailCanvas: "harbours-implementation-plan.canvas.tsx",
      },
      {
        id: "FEAT-NPC-04",
        name: "Personal history ledger",
        status: "pending",
        acceptance:
          "Append-only record per NPC: home port, notable voyages, deals, busts, wars survived; readable in admin or player dossier.",
        detailCanvas: "harbours-long-term-implementation-plan.canvas.tsx",
      },
      {
        id: "FEAT-NPC-05",
        name: "Player relationship memory",
        status: "pending",
        acceptance:
          "On player interaction (trade, charter, graft, hail): update trust/grudge/last_met; NPC pricing or dialogue bias may reference it; twin parity for sim-touching fields.",
        detailCanvas: "harbours-economy-rules.canvas.tsx",
      },
      {
        id: "FEAT-NPC-07",
        name: "NPC-to-NPC social memory",
        status: "pending",
        acceptance:
          "Pairwise ledger when two NPCs interact in twin (same-port trade, competing lots, charter, smuggle/graft events): update trust/grudge/last_met both ways; may bias future wholesale/partner choice; bounded graph size; twin parity.",
        detailCanvas: "harbours-economy-rules.canvas.tsx",
        codePaths: "game_state.gd, sim_100_days.py",
      },
      {
        id: "FEAT-NPC-06",
        name: "Roster & encounter surfacing",
        status: "pending",
        acceptance:
          "Player sees met captains/merchants in port UI; use-case canvas lists flows; relationships not hidden in dumps only.",
        detailCanvas: "harbours-use-case-map.canvas.tsx",
        codePaths: "ui/main.gd",
      },
      {
        id: "FEAT-NPC-08",
        name: "Personal scribe — Tiro UI",
        status: "pending",
        acceptance:
          "Household slave/freedman secretary (Cicero/Tiro analogue): auto-appends witnessed interactions to player codex; query UI for what happened, who said what, whom to ask next; source/age/reliability on entries; no omniscient world dump — complements Status log and Ledger.",
        detailCanvas: "harbours-use-case-map.canvas.tsx",
        codePaths: "ui/main.gd, game_state.gd (scribe_log in save)",
      },
    ],
  },
  {
    id: "EPIC-INST",
    title: "Institutional trade & obligations",
    pi: "PI-1 · Now",
    horizon: "A — Economy (contracts layer)",
    intent:
      "Charters, civic grain registers, breach law, and alliance visibility — twin-first, then player clerk surface.",
    primaryCanvas: "harbours-institutional-trade-roadmap.canvas.tsx",
    secondaryCanvases: ["harbours-economy-rules.canvas.tsx"],
    features: [
      {
        id: "FEAT-INST-01",
        name: "Institutional phases 0–4 (twin)",
        status: "completed",
        acceptance: "Obligation graph, NPC civic flows, metrics in sim; phases documented in institutional canvas.",
        detailCanvas: "harbours-institutional-trade-roadmap.canvas.tsx",
      },
      {
        id: "FEAT-INST-02",
        name: "Phase 5 player surface (charter clerk)",
        status: "completed",
        acceptance:
          "Influence tab: contract law, breach copy, alliance map, live NPC civic grain register; world_full phase5 gate; twin metric enabled.",
        detailCanvas: "harbours-use-case-map.canvas.tsx",
        codePaths: "ui/main.gd, game_state.gd, data/world_full.json",
      },
      {
        id: "FEAT-INST-03",
        name: "Phase 6+ obligation types (if any)",
        status: "deferred",
        acceptance: "New obligation kinds only when fiction requires; otherwise close institutional epic.",
        detailCanvas: "harbours-institutional-trade-roadmap.canvas.tsx",
      },
    ],
  },
  {
    id: "EPIC-MAP",
    title: "Navigable chart & world shell",
    pi: "PI-1 · Now → PI-2",
    horizon: "Map layer (parallel to A)",
    intent:
      "Continuous Mediterranean art from mask/chunks; ports on graph; gameplay authority from mask sample — not Wang tile sprites as coastline.",
    primaryCanvas: "harbours-chunk-based-gaming-map.canvas.tsx",
    secondaryCanvases: [
      "harbours-navigable-chart-implementation.canvas.tsx",
      "harbours-use-case-map.canvas.tsx",
    ],
    features: [
      {
        id: "FEAT-MAP-01",
        name: "Chunk manifest & mask-derived WEBP",
        status: "completed",
        acceptance:
          "slice_map_chunks.py produces data/maps/chunk_manifest.json + docs/maps/chunks/med_*; 2000×1000 wang16 mask master.",
        detailCanvas: "harbours-chunk-based-gaming-map.canvas.tsx",
        codePaths: "tools/slice_map_chunks.py, data/maps/chunk_manifest.json",
      },
      {
        id: "FEAT-MAP-02",
        name: "WorldMapChart + chart projection",
        status: "completed",
        acceptance:
          "Routes overlay uses WorldMapChart when manifest exists; map_u/v ↔ pixels ↔ screen shared pan/zoom.",
        detailCanvas: "harbours-chunk-based-gaming-map.canvas.tsx",
        codePaths: "ui/world_map_chart.gd, scripts/map/chart_projection.gd",
      },
      {
        id: "FEAT-MAP-03",
        name: "Terrain editor & wang16 save pipeline",
        status: "completed",
        acceptance:
          "Corner-Wang paint, dry-run/save refreshes tilemap, mask, chart-area exports, chunks; editor_terrain source_mode on disk.",
        detailCanvas: "harbours-chunk-based-gaming-map.canvas.tsx",
        codePaths: "tools/terrain_edit_session.py, tools/port_map_editor_wang16_1px/",
      },
      {
        id: "FEAT-MAP-04",
        name: "Port UV apply to world_full",
        status: "completed",
        acceptance:
          "apply_port_map_wang16_1px_export.py updates port positions; export marked .applied.json; commit world_full when ready.",
        detailCanvas: "harbours-chunk-based-gaming-map.canvas.tsx",
        codePaths: "data/world_full.json, tools/apply_port_map_wang16_1px_export.py",
      },
      {
        id: "FEAT-MAP-05",
        name: "Lane polylines overlay (read-only)",
        status: "pending",
        acceptance: "lanes[] from world_full drawn on chart; no travel duality; visible trade graph on art.",
        detailCanvas: "harbours-chunk-based-gaming-map.canvas.tsx",
        codePaths: "ui/world_map_chart.gd, data/world_full.json",
      },
      {
        id: "FEAT-MAP-06",
        name: "MapDataLayer mask sampling",
        status: "pending",
        acceptance:
          "Sample mask at world pixel → land / coastal_water / open_sea; optional chart_area_id from index bounds.",
        detailCanvas: "harbours-chunk-based-gaming-map.canvas.tsx",
        codePaths: "scripts/map/ (MapDataLayer.gd or WorldMapChart)",
      },
      {
        id: "FEAT-MAP-07",
        name: "Routes UX polish",
        status: "pending",
        acceptance:
          "Header copy for chunk vs fallback chart; optional saved view and chart-area filter; use-case canvas updated.",
        detailCanvas: "harbours-use-case-map.canvas.tsx",
        codePaths: "ui/main.gd",
      },
      {
        id: "FEAT-MAP-08",
        name: "Richer basemap re-slice (optional)",
        status: "pending",
        acceptance: "Higher-fidelity art → slice_map_chunks; player sees improved WEBP, same mask authority.",
        detailCanvas: "harbours-forward-analysis.canvas.tsx",
      },
      {
        id: "FEAT-MAP-09",
        name: "Legacy navigable-chart reconciliation",
        status: "pending",
        acceptance:
          "Navigable canvas tasks marked completed/cancelled; colonies PNG path optional reference only; chunk canvas is source of truth.",
        detailCanvas: "harbours-navigable-chart-implementation.canvas.tsx",
        enabler: true,
      },
    ],
  },
  {
    id: "EPIC-CIVIC",
    title: "Cities, stress & legibility",
    pi: "PI-2 · Next",
    horizon: "B — Cities & people",
    intent: "Player reads famine, riot risk, and recovery in-port without digging through admin-only lines.",
    primaryCanvas: "harbours-long-term-implementation-plan.canvas.tsx",
    secondaryCanvases: ["harbours-use-case-map.canvas.tsx"],
    features: [
      {
        id: "FEAT-CIVIC-01",
        name: "City stress UX panel",
        status: "pending",
        acceptance:
          "Docked view surfaces grain-days runway, unrest tier, riot/recovery state with plain copy; ties to GameState signals.",
        detailCanvas: "harbours-use-case-map.canvas.tsx",
        codePaths: "ui/main.gd, game_state.gd",
      },
      {
        id: "FEAT-CIVIC-02",
        name: "Warmup calendar clarity banner",
        status: "pending",
        acceptance: "Optional UI when NPC warmup advances calendar (e.g. Day 25 after 24 NPC days); no sim change.",
        detailCanvas: "harbours-implementation-plan.canvas.tsx",
      },
    ],
  },
  {
    id: "EPIC-POL",
    title: "Player agency, politics & factions",
    pi: "PI-3 · Then",
    horizon: "C — Player agency & politics",
    intent:
      "Marginal influence early, city-scale leverage late — reputation, embargoes, war contribution beyond graft v1.",
    primaryCanvas: "harbours-long-term-implementation-plan.canvas.tsx",
    secondaryCanvases: ["harbours-implementation-plan.canvas.tsx"],
    features: [
      {
        id: "FEAT-POL-01",
        name: "Political staging design pass",
        status: "pending",
        acceptance:
          "Document which player actions feed reputation, embargoes, riots, war; hooks listed in use-case + economy canvases.",
        detailCanvas: "harbours-combined-delivery-roadmap.canvas.tsx",
      },
      {
        id: "FEAT-POL-02",
        name: "Reputation & embargo hooks v1",
        status: "pending",
        acceptance: "First playable hooks in Godot + twin; measurable in 5k sim where applicable.",
        detailCanvas: "harbours-economy-rules.canvas.tsx",
      },
      {
        id: "FEAT-POL-03",
        name: "Cartels & alliances graph",
        status: "pending",
        acceptance:
          "Wire OCEAN traits to port_cartel_strength + diplomacy graph when faction model exists.",
        detailCanvas: "harbours-implementation-plan.canvas.tsx",
      },
    ],
  },
  {
    id: "EPIC-TRAVEL",
    title: "Pirates-style travel duality",
    pi: "PI-3 · Then",
    horizon: "D — Sea (client layer)",
    intent:
      "Godot shows hull pose and lane progress; headless twin keeps abstract legs — no duplicate economy on map.",
    primaryCanvas: "harbours-pirates-style-travel-roadmap.canvas.tsx",
    secondaryCanvases: ["harbours-chunk-based-gaming-map.canvas.tsx"],
    features: [
      {
        id: "FEAT-TRAVEL-01",
        name: "Prerequisite: map shell complete",
        status: "in_progress",
        acceptance: "FEAT-MAP-05 and FEAT-MAP-06 shipped before any hull-on-map work starts.",
        detailCanvas: "harbours-forward-analysis.canvas.tsx",
        enabler: true,
      },
      {
        id: "FEAT-TRAVEL-02",
        name: "Lane-following route preview (client)",
        status: "pending",
        acceptance: "Player sees course along lane geometry; twin voyage unchanged.",
        detailCanvas: "harbours-pirates-style-travel-roadmap.canvas.tsx",
      },
      {
        id: "FEAT-TRAVEL-03",
        name: "Hull / NPC tokens on chart",
        status: "pending",
        acceptance: "PC and NPC markers move along lanes at correct scale; zoom-stable like port editor pattern.",
        detailCanvas: "harbours-pirates-style-travel-roadmap.canvas.tsx",
      },
      {
        id: "FEAT-TRAVEL-04",
        name: "Hail & trade-at-sea stub",
        status: "pending",
        acceptance: "UI affordance for encounter/trade at sea without full combat.",
        detailCanvas: "harbours-use-case-map.canvas.tsx",
      },
    ],
  },
  {
    id: "EPIC-SEA",
    title: "Voyage hazards & abstract combat",
    pi: "PI-4 · Later",
    horizon: "D — Sea & spectacle",
    intent: "Seasonal storms, lane risk, maintenance costs; combat resolves abstractly unless high stakes.",
    primaryCanvas: "harbours-long-term-implementation-plan.canvas.tsx",
    features: [
      {
        id: "FEAT-SEA-01",
        name: "Voyage hazards v1",
        status: "pending",
        acceptance: "Storms, lane risk, abstract maintenance in twin + surfaced in voyage UI.",
        detailCanvas: "harbours-combined-delivery-roadmap.canvas.tsx",
      },
      {
        id: "FEAT-SEA-02",
        name: "Abstract combat default",
        status: "pending",
        acceptance: "Resolution without tactical map; optional light mode for high stakes only.",
        detailCanvas: "harbours-long-term-implementation-plan.canvas.tsx",
      },
    ],
  },
  {
    id: "EPIC-PLATFORM",
    title: "Engineering discipline & canvas hygiene",
    pi: "PI-1 · Continuous",
    horizon: "Cross-cutting",
    intent: "Docs and twins stay truthful; player contract canvases update with shipped affordances.",
    primaryCanvas: "harbours-forward-analysis.canvas.tsx",
    secondaryCanvases: [
      "harbours-economy-rules.canvas.tsx",
      "harbours-use-case-map.canvas.tsx",
    ],
    features: [
      {
        id: "FEAT-PLAT-01",
        name: "Economy rules canvas accuracy",
        status: "in_progress",
        acceptance: "Tick order and formulas match game_state / sim after every substantive economy edit.",
        detailCanvas: "harbours-economy-rules.canvas.tsx",
        enabler: true,
      },
      {
        id: "FEAT-PLAT-02",
        name: "Use-case map sync",
        status: "in_progress",
        acceptance: "Player flows and GameState wiring documented when UI affordances change.",
        detailCanvas: "harbours-use-case-map.canvas.tsx",
        enabler: true,
      },
      {
        id: "FEAT-PLAT-03",
        name: "Post-change 5k sim gate",
        status: "in_progress",
        acceptance: "Substantive economy/world edits run tools/sim_100_days.py 5000 --no-graphs; summary in PR notes.",
        detailCanvas: ".cursor/rules/post-change-sim-5k.mdc",
        enabler: true,
      },
      {
        id: "FEAT-PLAT-04",
        name: "Consolidated SAFe plan (this canvas)",
        status: "completed",
        acceptance: "Single epic/feature backlog with PI grouping and canvas cross-links.",
        detailCanvas: "harbours-consolidated-implementation-plan.canvas.tsx",
      },
    ],
  },
  {
    id: "EPIC-MP",
    title: "Multiplayer & session topology",
    pi: "PI-5 · Deferred",
    horizon: "E — Multiplayer (last)",
    intent: "Rules engine and counterparty layer separable; no MMO claims until solo economy + map credible.",
    primaryCanvas: "harbours-long-term-implementation-plan.canvas.tsx",
    features: [
      {
        id: "FEAT-MP-01",
        name: "Rules engine UI-agnostic boundary",
        status: "deferred",
        acceptance: "Sim core callable without Godot UI; session vs MMO decision documented.",
        detailCanvas: "harbours-long-term-implementation-plan.canvas.tsx",
      },
    ],
  },
];

const PI_ROWS: string[][] = [
  [
    "PI-1",
    "Now",
    "Economy tune · map shell finish · platform discipline",
    "EPIC-ECON, EPIC-INST, EPIC-MAP (05–09), EPIC-PLATFORM",
    "harbours-combined-delivery-roadmap.canvas.tsx",
  ],
  [
    "PI-2",
    "Next",
    "Chart gameplay overlay · city stress UX · NPC personhood",
    "EPIC-MAP (05–07), EPIC-CIVIC, EPIC-NPC",
    "harbours-chunk-based-gaming-map.canvas.tsx",
  ],
  [
    "PI-3",
    "Then",
    "Politics staging · pirates travel lite",
    "EPIC-POL, EPIC-TRAVEL",
    "harbours-pirates-style-travel-roadmap.canvas.tsx",
  ],
  [
    "PI-4",
    "Later",
    "Sea hazards · abstract combat",
    "EPIC-SEA",
    "harbours-long-term-implementation-plan.canvas.tsx",
  ],
  [
    "PI-5",
    "Deferred",
    "Multiplayer topology",
    "EPIC-MP",
    "harbours-long-term-implementation-plan.canvas.tsx",
  ],
];

const CANVAS_INDEX: string[][] = [
  ["harbours-consolidated-implementation-plan.canvas.tsx", "This file — SAFe backlog", "All epics"],
  ["harbours-forward-analysis.canvas.tsx", "Audit & gap analysis", "Cross-epic priorities"],
  ["harbours-combined-delivery-roadmap.canvas.tsx", "Executive merge (tactical + strategic)", "EPIC-ECON milestones"],
  ["harbours-implementation-plan.canvas.tsx", "Tactical economy pulse", "EPIC-ECON shipped/next"],
  [
    "harbours-long-term-implementation-plan.canvas.tsx",
    "Horizons A–E, north star (incl. NPCs as persons)",
    "EPIC-NPC, CIVIC, POL, SEA, MP",
  ],
  ["harbours-economy-rules.canvas.tsx", "Tick formulas (living doc)", "EPIC-ECON, INST, POL"],
  ["harbours-institutional-trade-roadmap.canvas.tsx", "Charter phases 0–5+", "EPIC-INST"],
  ["harbours-chunk-based-gaming-map.canvas.tsx", "Chunk map technical plan", "EPIC-MAP"],
  ["harbours-navigable-chart-implementation.canvas.tsx", "Legacy alignment (reconcile)", "FEAT-MAP-09"],
  ["harbours-pirates-style-travel-roadmap.canvas.tsx", "Travel duality Phase 2", "EPIC-TRAVEL"],
  ["harbours-use-case-map.canvas.tsx", "Player-visible flows", "EPIC-MAP, CIVIC, TRAVEL, INST"],
];

const STATUS_ORDER: FeatureStatus[] = ["pending", "in_progress", "completed", "deferred"];

function nextFeatureStatus(s: FeatureStatus): FeatureStatus {
  const i = STATUS_ORDER.indexOf(s);
  return STATUS_ORDER[(i + 1) % STATUS_ORDER.length] ?? "pending";
}

function statusLabel(s: FeatureStatus): string {
  if (s === "deferred") return "deferred";
  return s.replace("_", " ");
}

function featuresToTodos(epic: Epic, statuses: Record<string, FeatureStatus>): TodoItem[] {
  return epic.features.map((f) => ({
    id: f.id,
    content: `${f.name} — ${f.acceptance.slice(0, 120)}${f.acceptance.length > 120 ? "…" : ""}`,
    status: (statuses[f.id] ?? f.status) === "deferred" ? "pending" : (statuses[f.id] ?? f.status),
  }));
}

function epicProgress(epic: Epic, statuses: Record<string, FeatureStatus>): { done: number; total: number } {
  const total = epic.features.length;
  const done = epic.features.filter((f) => (statuses[f.id] ?? f.status) === "completed").length;
  return { done, total };
}

function EpicSection({
  epic,
  statuses,
  onFeatureClick,
}: {
  epic: Epic;
  statuses: Record<string, FeatureStatus>;
  onFeatureClick: (featureId: string) => void;
}) {
  const { done, total } = epicProgress(epic, statuses);
  const featureRows = epic.features.map((f) => {
    const st = statuses[f.id] ?? f.status;
    return [
      f.id,
      f.name + (f.enabler ? " (enabler)" : ""),
      statusLabel(st),
      f.acceptance,
      f.detailCanvas.replace(".canvas.tsx", ""),
      f.codePaths ?? "—",
    ];
  });

  return (
    <Stack gap={12}>
      <Row gap={12} align="center" wrap>
        <H2>
          {epic.id} — {epic.title}
        </H2>
        <Pill tone="info" size="small">
          {epic.pi}
        </Pill>
        <Pill tone="neutral" size="small">
          {epic.horizon}
        </Pill>
        <Pill tone={done === total ? "success" : "warning"} size="small">
          {done}/{total} features
        </Pill>
      </Row>
      <Text tone="secondary" size="small">
        {epic.intent}
      </Text>
      <Text size="small">
        Detail: <Code>{epic.primaryCanvas}</Code>
        {epic.secondaryCanvases?.map((c) => (
          <span key={c}>
            {" "}
            · <Code>{c}</Code>
          </span>
        ))}
      </Text>
      <Table
        headers={["Feature", "Name", "Status", "Acceptance criteria", "Detail canvas", "Code paths"]}
        rows={featureRows.map((row) => [
          row[0],
          row[1],
          row[2],
          row[3],
          row[4],
          row[5],
        ])}
      />
      <TodoListCard
        title={`${epic.id} — click to cycle feature status`}
        todos={featuresToTodos(epic, statuses)}
        defaultExpanded={false}
        onTodoClick={(todo) => onFeatureClick(todo.id)}
      />
    </Stack>
  );
}

function buildInitialStatuses(): Record<string, FeatureStatus> {
  const out: Record<string, FeatureStatus> = {};
  for (const epic of EPICS) {
    for (const f of epic.features) {
      out[f.id] = f.status;
    }
  }
  return out;
}

export default function HarboursConsolidatedImplementationPlan() {
  const [statuses, setStatuses] = useCanvasState<Record<string, FeatureStatus>>(
    "consolidated-safe-features-v1",
    buildInitialStatuses()
  );

  const onFeatureClick = (featureId: string) => {
    setStatuses((prev) => {
      const current = prev[featureId] ?? "pending";
      return { ...prev, [featureId]: nextFeatureStatus(current) };
    });
  };

  const allFeatures = EPICS.flatMap((e) => e.features);
  const completedCount = allFeatures.filter((f) => (statuses[f.id] ?? f.status) === "completed").length;
  const inProgressCount = allFeatures.filter((f) => (statuses[f.id] ?? f.status) === "in_progress").length;

  return (
    <Stack gap={24}>
      <Stack gap={8}>
        <H1>HarboursOfPower — consolidated implementation plan</H1>
        <Text tone="secondary" size="small">
          SAFe-style structure: <strong>Program Increments (PI)</strong> → <strong>Epics</strong> (value streams) →{" "}
          <strong>Features</strong> (shippable increments with acceptance criteria). Deep specs stay in referenced
          canvases; cycle feature status here for prioritisation (persists under{" "}
          <Code>consolidated-safe-features-v1</Code>).
        </Text>
      </Stack>

      <Callout tone="neutral" title="How to open this canvas (viewing, not editing)">
        <Text size="small">
          For the human-readable layout: <strong>Cmd+Shift+P</strong> → <strong>Open Canvas</strong> → select this file.
          Clicking the file in the project tree opens <strong>Source (TSX)</strong>; use the tab's{" "}
          <strong>Preview / Rendered</strong> control or reopen via Open Canvas. Details in{" "}
          <Code>canvases/README.md</Code>.
        </Text>
      </Callout>

      <Grid columns={4} gap={16}>
        <Stat value={String(EPICS.length)} label="Epics" />
        <Stat value={String(allFeatures.length)} label="Features" tone="info" />
        <Stat value={String(completedCount)} label="Completed" tone="success" />
        <Stat value={String(inProgressCount)} label="In progress" tone="warning" />
      </Grid>

      <Callout tone="info" title="North star — living world includes persons">
        <Text>
          NPC traffic must stay economically credible <em>and</em> eventually feel like people: OCEAN traits (shipped) plus
          names, personal history, relationships with the player on interaction, and <strong>NPC-to-NPC memory</strong> when
          merchants and captains interact in the sim — a truly living world, not only a player-centric diary. The player
          employs a <strong>personal scribe (Tiro)</strong> to hold the written record and answer questions from that
          codex (<Code>FEAT-NPC-08</Code>). See <strong>EPIC-NPC</strong> below; full goal prose in{" "}
          <Code>harbours-long-term-implementation-plan.canvas.tsx</Code>.
        </Text>
      </Callout>

      <Callout tone="info" title="How this relates to other canvases">
        <Stack gap={8}>
          <Text>
            This canvas <strong>does not replace</strong> economy formulas, institutional phase prose, or chunk-map
            technical detail. It is the <strong>single backlog view</strong>. When a feature ships, update its status here
            and reconcile the <strong>detail canvas</strong> listed on that row (per repo rules for economy and use-case
            maps).
          </Text>
          <Text size="small" tone="secondary">
            Prior audit: <Code>harbours-forward-analysis.canvas.tsx</Code> · Executive merge:{" "}
            <Code>harbours-combined-delivery-roadmap.canvas.tsx</Code>
          </Text>
        </Stack>
      </Callout>

      <Divider />

      <H2>Program increments (release trains)</H2>
      <Text tone="secondary" size="small">
        Ordered delivery waves — not calendar commitments. Finish PI-1 before expanding PI-3 travel work.
      </Text>
      <Table headers={["PI", "When", "Theme", "Epics", "Also see"]} rows={PI_ROWS} />

      <Divider />

      <H2>Epic map (progress directions)</H2>
      <Table
        headers={["Epic", "Direction", "PI", "Horizon", "Primary detail canvas"]}
        rows={EPICS.map((e) => [
          e.id,
          e.title,
          e.pi.split(" · ")[0] ?? e.pi,
          e.horizon,
          e.primaryCanvas,
        ])}
      />

      <Divider />

      <H2>Epics &amp; features</H2>
      <Text tone="secondary" size="small">
        Tables list acceptance criteria; collapsible todo lists per epic let you click to cycle status (pending → in
        progress → completed → deferred).
      </Text>

      {EPICS.map((epic) => (
        <Card key={epic.id}>
          <CardBody>
            <EpicSection epic={epic} statuses={statuses} onFeatureClick={onFeatureClick} />
          </CardBody>
        </Card>
      ))}

      <Divider />

      <H2>Canvas index (references)</H2>
      <Table headers={["Canvas file", "Role in program", "Epic / feature owner"]} rows={CANVAS_INDEX} />

      <Callout tone="warning" title="Maintenance">
        When strategic scope shifts, edit the <strong>detail canvas</strong> first, then add or reword features here.
        Retire duplicate tasks on <Code>harbours-navigable-chart-implementation.canvas.tsx</Code> via{" "}
        <Code>FEAT-MAP-09</Code>. Map work must not restart Wang tile sprites as player coastline (see chunk canvas
        Phase A guard).
      </Callout>

      <Text tone="tertiary" size="small">
        Repo: HarboursOfPower · Godot + Python twin · Documentation canvas only.
      </Text>
    </Stack>
  );
}

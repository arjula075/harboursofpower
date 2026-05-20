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
 * Incremental plan: (1) build a playable navigable chart in Godot, (2) Pirates!-style
 * map travel with PC + NPC merchants on that chart, (3) keep abstract travel for
 * headless world sims so bulk runs stay fast.
 */

const STATUS_ORDER: TodoStatus[] = ["pending", "in_progress", "completed"];

function nextStatus(s: TodoStatus): TodoStatus {
  const i = STATUS_ORDER.indexOf(s);
  return STATUS_ORDER[(i + 1) % STATUS_ORDER.length] ?? "pending";
}

const INITIAL_TRACKER: TodoItem[] = [
  {
    id: "t-chart-basemap",
    content:
      "Godot map mode scene: ocean + coastline basemap from docs/reference_greek_phoenician_colonies_mediterranean.png (+ data/reference_colonies_map_alignment.json); camera (pan/zoom/clamp); legacy SVG maps optional only.",
    status: "pending",
  },
  {
    id: "t-chart-projection",
    content:
      "Projection layer: port lat/lon or JSON chart coords → screen space; single source of truth so ships, ports, and lanes share the same transform.",
    status: "pending",
  },
  {
    id: "t-chart-ports",
    content:
      "Port markers from `data/world_full.json`: ids match GameState port_id; hover/click hit-test, labels, filter; click ties into destination / intel flows.",
    status: "pending",
  },
  {
    id: "t-chart-lanes",
    content:
      "Lane / leg geometry on chart: polylines or sampled arcs aligned with voyage graph edges so interpolation matches coastal vs bold semantics (fallback: great-circle between endpoints).",
    status: "pending",
  },
  {
    id: "t-audit-time",
    content:
      "Split runtimes: client map pose vs headless abstract legs; document determinism, acceptable drift, and what the twin must mirror (ledgers) vs omit (screen x/y).",
    status: "pending",
  },
  {
    id: "t-sea-state",
    content:
      "Client: persist per-agent at-sea state for map-tracked merchants + PC; query API for chart layer + hail range.",
    status: "pending",
  },
  {
    id: "t-map-ship",
    content:
      "Chart: render PC + NPC markers along legs using lane geometry + progress; LOD when crowded.",
    status: "pending",
  },
  {
    id: "t-map-interact",
    content:
      "Chart interaction: select / hail merchant (range, LOS); wire to trade, extort, duel stubs.",
    status: "pending",
  },
  {
    id: "t-sail-controls",
    content:
      "Client pacing: PC sail vs hold; NPC legs auto-tick advance_day and refresh pose structs the chart reads.",
    status: "pending",
  },
  {
    id: "t-route-choice",
    content:
      "Routing: PC coastal vs bold; NPC RNG/policy + same route metadata for chart + tooltips.",
    status: "pending",
  },
  {
    id: "t-divert",
    content:
      "Divert: PC reroute UI + shared recompute helper; NPC via sim rules on client; headless stays abstract-only reroute.",
    status: "pending",
  },
  {
    id: "t-encounters",
    content:
      "Client encounters with co-presence to rendered merchants; no requirement for headless to step chart geometry.",
    status: "pending",
  },
  {
    id: "t-headless-abstract",
    content:
      "World sims (sim_100_days.py, large NPC counts): keep old-style abstract travel — day counters between ports, no per-hull map loop; coarse-graining flags stay valid.",
    status: "pending",
  },
  {
    id: "t-twin",
    content:
      "Parity: twin mirrors economy fields the rules need; chart-only fields optional; document contract. Default 10k-day check stays on abstract path.",
    status: "pending",
  },
  {
    id: "t-polish",
    content:
      "Chart polish: wind rose, speed readout, focus PC, SFX; optional secondary overlay from docs SVGs if needed for extra geography (primary basemap = colonies PNG).",
    status: "pending",
  },
];

export default function HarboursPiratesStyleTravelRoadmap() {
  const [tracker, setTracker] = useCanvasState<TodoItem[]>("pirates-travel-tracker-v4", INITIAL_TRACKER);

  const onTodoClick = (todo: TodoItem) => {
    setTracker((prev) => {
      return prev.map((t) => {
        if (t.id !== todo.id) {
          return t;
        }
        return { ...t, status: nextStatus(t.status) };
      });
    });
  };

  const done = tracker.filter((t) => t.status === "completed").length;

  return (
    <Stack gap={20}>
      <Stack gap={6}>
        <H1>Navigable chart + Pirates!-style travel — incremental plan</H1>
        <Text tone="secondary" size="small">
          Three tracks: <strong>(1) Chart</strong> — a real map mode in Godot (basemap, projection, ports, lanes,
          camera). <strong>(2) Client travel</strong> — PC + NPC merchants move and interact on that chart using the
          same leg/pose model. <strong>(3) World sim</strong> — headless runs keep abstract day-based voyages only so
          whole-world simulations stay fast. Repo already has reference cartography under <Code>docs/</Code> (e.g.{" "}
          <Code>reference_greek_phoenician_colonies_mediterranean.png</Code> plus{" "}
          <Code>data/reference_colonies_map_alignment.json</Code>); the game still needs an interactive chart scene wired
          to <Code>data/world_full.json</Code> and <Code>autoload/game_state.gd</Code>.
        </Text>
      </Stack>

      <Grid columns={4} gap={16}>
        <Stat value="15" label="Tracked slices" />
        <Stat value={`${done}/${tracker.length}`} label="Canvas checklist done" tone={done === tracker.length ? "success" : undefined} />
        <Stat value="4" label="Delivery waves" />
        <Stat value="2" label="Fidelity lanes" tone="info" />
      </Grid>

      <Callout tone="neutral" title="Prerequisite — the chart is not optional">
        Ships, hail range, and reroutes all assume a <strong>navigable map surface</strong>: projection, zoom, and
        hit-testing. Build the chart substrate before polishing motion; otherwise markers float in a list UI, not a
        sea. The colonies PNG is the default basemap; older SVG coast files are optional overlays, not the interactive layer
        by themselves.
      </Callout>

      <Callout tone="info" title="Headless world sim — abstract travel only">
        For <Code>tools/sim_100_days.py</Code> and bulk NPC ticks, <strong>keep old-style travel</strong> (port-to-port
        days, graph math). Do not integrate continuous chart stepping for every hull. Optional coarse-graining stays
        valid. Twin parity is ledgers + voyage <em>math</em>, not pixel positions.
      </Callout>

      <Divider />

      <H2>Wave 0 — Build the actual map (chart substrate)</H2>
      <Text>
        Deliver a <strong>map mode</strong> the player can read and steer: geography-anchored layout, stable ids, and
        room for many markers. Travel waves hang off this surface.
      </Text>
      <Table
        headers={["Slice", "Ships when", "Touches (typical)"]}
        rows={[
          ["M1 — Map scene", "Dedicated map UI state/tab; Control tree for chart + chrome (legend, filters).", "New scene or branch in ui/main.gd"],
          ["M2 — Projection", "World coords → chart pixels; resize-safe; same util for ports, lanes, ships.", "Shared autoload or map controller script"],
          ["M3 — Basemap art", "TextureRect with colonies reference PNG; optional SVG overlay; alignment via manifest + control points.", "TextureRect / Shader"],
          ["M4 — Ports layer", "All ports plotted; tooltips; selection sync with GameState port ids.", "data/world*.json + GameState"],
          ["M5 — Lanes layer", "Draw graph edges or route preview polylines used for ship interpolation.", "Lane data from sim / JSON / runtime cache"],
        ]}
      />

      <H2>Wave A — Show every leg (PC + merchants on the chart)</H2>
      <Text>
        With M1–M5 in place, derive <strong>honest poses</strong> on the chart from remaining days + route metadata.
        No new economy rules until markers sit on the correct polylines.
      </Text>
      <Table
        headers={["Slice", "Ships when", "Touches (typical)"]}
        rows={[
          ["A1 — Agent query", "Chart lists at-sea agents with from, to, route label, remaining days.", "GameState query + map scene"],
          ["A2 — Progress param", "progress = 1 - remaining/booked days per agent (clamp).", "game_state.gd leg fields"],
          ["A3 — Interpolated pose", "Markers move along M5 polylines (fallback arc if missing).", "Map markers + timer/day sync"],
          ["A4 — Merchant identity", "Faction / cargo hints on markers; clutter controls.", "Icons, filters"],
        ]}
      />

      <H2>Wave B — Agency split (player steers, world ticks everyone)</H2>
      <Text>
        <strong>PC:</strong> explicit sail vs hold on the chart. <strong>NPC merchants (client):</strong> auto leg tick
        updates pose structs the chart reads. <strong>Headless:</strong> unchanged abstract pacing.
      </Text>
      <Table
        headers={["Slice", "Ships when", "Risk / mitigation"]}
        rows={[
          ["B1 — Sail vs hold", "PC gated day consume; NPC client auto tick on advance_day.", "Single writer for client leg state."],
          ["B2 — Prepick route", "PC coastal vs bold; NPC stores route metadata for chart tooltips.", "Shared struct, different decision fn."],
          ["B3 — Divert", "PC reroute on chart; NPC sim-driven reroute shares recompute helper.", "Headless abstract-only; document divergence if any."],
        ]}
      />

      <H2>Wave C — Interaction and tension on the chart</H2>
      <Text>
        <strong>Hail / encounter</strong> when the PC is in chart range of a merchant marker; outcomes touch ledgers
        the twin must still understand.
      </Text>
      <Table
        headers={["Slice", "Ships when", "Notes"]}
        rows={[
          ["C1 — Hail + range", "Pick merchant on chart; range + LOS; open panel.", "Hit-test in chart space"],
          ["C2 — Event queue", "Co-presence boosts encounters; client queue.", "Twin omits geometry"],
          ["C3 — Ledger hooks", "Cargo, coins, reputation with clear copy.", "Mirror in twin when economy-affecting"],
          ["C4 — Combat placeholder", "Abstract fight or timed flee.", "Bounded scope"],
        ]}
      />

      <Divider />

      <H2>Code & data anchors</H2>
      <Card>
        <CardHeader>Where to wire work</CardHeader>
        <CardBody>
          <Stack gap={10}>
            <Text size="small">
              <strong>Chart assets (reference):</strong> primary <Code>docs/reference_greek_phoenician_colonies_mediterranean.png</Code>{" "}
              + <Code>data/reference_colonies_map_alignment.json</Code>; optional legacy{" "}
              <Code>docs/harbours_full_world_coordinate_map.svg</Code> for extra linework.
            </Text>
            <Text size="small">
              <strong>Data:</strong> <Code>data/world_full.json</Code> — port ids,
              coordinates, lane graph inputs the chart and <Code>_voyage_plan</Code> already depend on.
            </Text>
            <Text size="small">
              <Code>list_destinations</Code> / <Code>start_voyage</Code> / <Code>_voyage_plan</Code> —{" "}
              <Code>autoload/game_state.gd</Code> (shared math for client + headless).
            </Text>
            <Text size="small">
              <Code>ui/main.gd</Code> — tab/scene entry for map mode, destination flow, day advance; may split into a
              dedicated map scene as M1 grows.
            </Text>
            <Text size="small">
              <Code>tools/sim_100_days.py</Code> — default long runs stay <strong>abstract travel</strong>; extend only
              for ledger fields rules require; optional slow “faithful chart” debug behind a flag, never default 10k-day
              CI.
            </Text>
          </Stack>
        </CardBody>
      </Card>

      <H2>Incremental checklist (click rows to cycle status)</H2>
      <Text tone="secondary" size="small">
        Local-only planning state; not synced to the repo. Key <Code>pirates-travel-tracker-v4</Code> adds chart
        substrate + headless lane rows.
      </Text>
      <TodoListCard todos={tracker} defaultExpanded onTodoClick={onTodoClick} />

      <Divider />

      <H2>Ordering principle</H2>
      <H3>Chart first, then motion, then hail</H3>
      <Text>
        Wave 0 unlocks A–C: without projection and lanes, ship sprites are misleading. Economy parity for twins comes
        from shared voyage math and ledgers, not from simulating every hull in Python.
      </Text>

      <H3>Documentation hooks</H3>
      <Text tone="secondary" size="small">
        New map tab, signals, or save fields → <Code>harbours-use-case-map.canvas.tsx</Code>. Voyage math or tick order
        → <Code>harbours-economy-rules.canvas.tsx</Code> + 10k-day twin (abstract path).
      </Text>
    </Stack>
  );
}

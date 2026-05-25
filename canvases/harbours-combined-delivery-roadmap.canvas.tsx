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
 * Combined view: tactical delivery (harbours-implementation-plan) + strategic horizons
 * (harbours-long-term-implementation-plan). Edit the source canvases for detail; refresh this
 * file when north-star or “shipped / next” materially changes.
 */

const ANALYSIS = `The tactical canvas is a short horizon: what already landed in code, what you are
likely touching next sprint, and bookmark paths. The long-term canvas is the north star: product
and technical goals, horizons A–E, and clickable milestones that persist in canvas state.

Together they answer two different questions — “is the twin credible this month?” versus
“what kind of game are we still building in two years?”. This combined canvas links both,
deduplicates the relationship in prose, and gives one scrollable executive view. Deep tick math
still lives in harbours-economy-rules.canvas.tsx; institutional contract layers in
harbours-institutional-trade-roadmap.canvas.tsx.`;

const COMBINED_MILESTONES_INITIAL: TodoItem[] = [
  {
    id: "m-specie-mint",
    content:
      "Closed-loop specie: civic mint, world treasury, NPC/player bullion flows; wealth attractor excludes bullion where intended.",
    status: "completed",
  },
  {
    id: "m-luxury-import",
    content:
      "Luxury far-trade queue: delayed consignments, non-bullion luxury stock, explicit coin sink (treasury + purses + port wealth); twin parity.",
    status: "completed",
  },
  {
    id: "m-import-duties",
    content:
      "Port politics v1: per-port JSON tolls as import duty (sales into city only), NPC smuggle vs caught vs pay, dock graft immunity, player graft UI, wholesale relief at tolled ports; twin parity.",
    status: "completed",
  },
  {
    id: "m-econ-tune",
    content:
      "Economy tuning vs 5k-day twin: NPC bankruptcy rate under duties, riot/grain runway, treasury drift; optional export tolls or player smuggle risk UI.",
    status: "in_progress",
  },
  {
    id: "m-npc-persons",
    content:
      "NPCs as persons: stable identity, names, history ledger, player relationships on interaction, NPC-to-NPC social memory when they interact; save + twin parity.",
    status: "pending",
  },
  {
    id: "m-tiro-scribe",
    content:
      "Personal scribe (Tiro): UI secretary records interactions; player queries what happened, who said what, whom to ask — witnessed/paid intel only.",
    status: "pending",
  },
  {
    id: "m-institutional-surface",
    content:
      "Institutional trade player surface (phase5): charter clerk under Influence — law, breach copy, alliance map, live NPC civic grain register; world_full.json phase5 gate; twin metric npc_institutional_phase5_surface_enabled.",
    status: "completed",
  },
  {
    id: "m-city-ux",
    content:
      "City stress UX: richer in-port read on famine, riot risk, and recovery than status/admin lines alone; optional civic institutions when fiction supports it.",
    status: "pending",
  },
  {
    id: "m-player-power",
    content:
      "Player political staging: extend graft into reputation, embargoes, war contribution; marginal influence early, city-scale leverage late.",
    status: "pending",
  },
  {
    id: "m-sea-layer",
    content:
      "Voyage hazards v1: seasonal storms, lane risk, abstract maintenance costs; captains as fragile assets (ties traits and treatment).",
    status: "pending",
  },
  {
    id: "m-combat",
    content: "Combat: abstract resolution default; optional light tactical mode for high stakes only.",
    status: "pending",
  },
  {
    id: "m-social-graph",
    content: "Cartels, alliances, and diplomacy graph wired to existing NPC traits and port cartel fields when faction model exists.",
    status: "pending",
  },
  {
    id: "m-mp-deferred",
    content:
      "Multiplayer: keep rules engine and counterparty layer separable; session vs MMO topology open — ship only after solo economy is credible.",
    status: "pending",
  },
];

const STATUS_ORDER: TodoStatus[] = ["pending", "in_progress", "completed"];

function nextStatus(s: TodoStatus): TodoStatus {
  const i = STATUS_ORDER.indexOf(s);
  return STATUS_ORDER[(i + 1) % STATUS_ORDER.length] ?? "pending";
}

export default function HarboursCombinedDeliveryRoadmap() {
  const [milestones, setMilestones] = useCanvasState<TodoItem[]>(
    "combined-delivery-milestones-v1",
    COMBINED_MILESTONES_INITIAL
  );

  const onMilestoneClick = (todo: TodoItem) => {
    setMilestones((prev) => prev.map((t) => (t.id === todo.id ? { ...t, status: nextStatus(t.status) } : t)));
  };

  return (
    <Stack gap={20}>
      <Stack gap={6}>
        <H1>HarboursOfPower — combined delivery roadmap</H1>
        <Text tone="secondary" size="small">
          Merges the tactical <strong>implementation plan</strong> with the strategic <strong>long-term plan</strong>.
          Repo: <Code>/Users/ari.lahti/HarboursOfPower</Code> — Godot autoload + Python twin{" "}
          <Code>tools/sim_100_days.py</Code>. Save schema: <Code>SAVE_VERSION</Code> in{" "}
          <Code>autoload/game_state.gd</Code>.
        </Text>
      </Stack>

      <Callout tone="info" title="How the two plans relate">
        {ANALYSIS}
      </Callout>

      <Grid columns="4" gap={16}>
        <Stat value="Twin" label="GD + Python parity" tone="success" />
        <Stat value="Solo" label="Primary ship" />
        <Stat value="A→E" label="Strategic horizons" />
        <Stat value="Now" label="Tactical next list" />
      </Grid>

      <Divider />

      <H2>Strategic snapshot (long-term plan)</H2>
      <Card>
        <CardHeader>North star (condensed)</CardHeader>
        <CardBody style={{ paddingTop: 0 }}>
          <Stack gap={8}>
            <Text>
              <strong>Solo depth first</strong> — long campaigns with legible cause and effect; NPC traffic substitutes
              for humans without breaking prices.
            </Text>
            <Text>
              <strong>Merchant fantasy</strong> — leverage through logistics, credit, captains, and city condition, not
              map painting alone.
            </Text>
            <Text>
              <strong>Living world</strong> — ports and fleets stay believable when idle; wars strain food without
              scripted riot guarantees. <strong>NPCs as persons</strong> — OCEAN traits today; names, history, and
              persistent relationships (player and NPC-to-NPC) when interactions happen, tomorrow. A{" "}
              <strong>personal scribe (Tiro)</strong> in UI keeps your codex and answers &quot;who said what&quot; from
              what you actually recorded.
            </Text>
            <Text tone="secondary" size="small">
              Full goal cards, technical goals table, and horizon A–E tables:{" "}
              <Code>harbours-long-term-implementation-plan.canvas.tsx</Code>.
            </Text>
          </Stack>
        </CardBody>
      </Card>

      <H3>Horizons × tactical bridge</H3>
      <Text tone="secondary" size="small">
        Each horizon is thematic order from the long-term canvas; the right column ties the current tactical “next”
        items that lean on that horizon.
      </Text>
      <Table
        headers={["Horizon", "Theme", "Tactical bridge (implementation plan)"]}
        rows={[
          [
            "A — Economy & civic money",
            "Pricing, NPC merchants, specie, luxury, duties, materiel stability.",
            "Living world first; twin alignment; 5k-day tuning; OCEAN shipped — next personhood (names, history, player + NPC social memory); measure bankruptcies and riots.",
          ],
          [
            "B — Cities & people",
            "Population, famine, unrest, riots, NPCs the player remembers, later institutions.",
            "City stress UX; Tiro scribe UI (m-tiro-scribe); surface met merchants/captains; m-npc-persons.",
          ],
          [
            "C — Player agency & politics",
            "Duties v1 shipped; reputation, embargoes, war leverage, factions.",
            "Player political weight track; cartels/alliances when faction graph exists; graft extension in long-term.",
          ],
          [
            "D — Sea & spectacle",
            "Voyage hazards, pirates/escorts, abstract combat default.",
            "Godot validation after major tick changes; sea-layer milestones pending.",
          ],
          [
            "E — Multiplayer (last)",
            "Isolated rules engine, session topology before MMO claims.",
            "Explicitly deferred; keep sim core UI-agnostic.",
          ],
        ]}
      />

      <Divider />

      <H2>Tactical pulse (implementation plan)</H2>
      <H3>Recently shipped (high level)</H3>
      <Table
        headers={["Area", "What landed", "Where"]}
        rows={[
          [
            "Autonomous economy",
            "Deferred NPC-only warmup; world_full.json autonomy_warmup_days; twin mirrors on Sim.load.",
            "game_state.gd, sim_100_days.py, data/world_full.json",
          ],
          [
            "Tick agents",
            "Named phases through demographics and merchant home-count sync.",
            "game_state.gd, sim_tick_agents.gd, sim_100_days.py",
          ],
          [
            "NPC personality",
            "OCEAN-style traits; depart, memory, lots, wholesale, dust floor, voyage stress, hull behaviour.",
            "game_state.gd, sim_100_days.py",
          ],
          [
            "Merchant liquidity",
            "Softer coefficients, better wholesale mults, reserve/rookie/grace tuning.",
            "game_state.gd, sim_100_days.py",
          ],
          [
            "Docs & twin discipline",
            "Economy rules canvas + post-change 5k sim rule for substantive economy edits.",
            ".cursor/rules, sim_100_days.py",
          ],
          [
            "Institutional phase 5 (player surface)",
            "Charter clerk under Influence — contract law, breach copy, alliance map, live NPC civic grain register; phase5 world gate.",
            "game_state.gd, ui/main.gd, data/world_full.json, sim twin metric",
          ],
        ]}
      />

      <H3>Current focus</H3>
      <Text>
        <strong>Living world first:</strong> economy and NPC traffic should read as credible before the player moves the
        political needle. Re-run long sims after tuning; keep Godot and twin aligned.
      </Text>

      <H3>Next (tactical queue)</H3>
      <Table
        headers={["Track", "Goal", "Notes"]}
        rows={[
          [
            "Player political weight",
            "Stage impact: early none → mid local → late city-scale rise/fall.",
            "Design which actions feed reputation, embargoes, riots, war — then hooks.",
          ],
          [
            "Cartels & alliances",
            "Wire traits when faction systems exist.",
            "Reuse port_cartel_strength + diplomacy graph.",
          ],
          [
            "UX clarity",
            "Optional banner when warmup advances calendar (e.g. Day 25 after 24 NPC days).",
            "Small UI; no sim change.",
          ],
          [
            "Further NPC economy",
            "If bankruptcies stay high at long horizons: fee discount or officer-pay carve-out.",
            "Measure with sim_100_days.py at realistic N.",
          ],
          ["Godot validation", "Playtest + headless checks after major tick changes.", "CI / local Godot as available."],
        ]}
      />

      <Divider />

      <H2>Strategic milestones (combined canvas state)</H2>
      <Text tone="secondary" size="small">
        Persists under key <Code>combined-delivery-milestones-v1</Code> (independent from{" "}
        <Code>lt-milestones-v2</Code> on the long-term canvas). Click a row to cycle status for your own prioritisation.
        Keep milestone text loosely in sync with <Code>harbours-long-term-implementation-plan.canvas.tsx</Code> when
        scope shifts.
      </Text>
      <TodoListCard todos={milestones} defaultExpanded onTodoClick={onMilestoneClick} />

      <Divider />

      <H2>Related artifacts</H2>
      <Table
        headers={["Canvas / file", "Role"]}
        rows={[
          ["harbours-implementation-plan.canvas.tsx", "Tactical shipped vs next; bookmark paths."],
          ["harbours-long-term-implementation-plan.canvas.tsx", "Goals, horizons A–E, original milestone todos."],
          ["harbours-economy-rules.canvas.tsx", "Tick order and economy formulas; must stay code-accurate."],
          ["harbours-institutional-trade-roadmap.canvas.tsx", "Institutional phases 0–5 and design thesis."],
          ["harbours-use-case-map.canvas.tsx", "Player-visible UI flows and GameState wiring."],
        ]}
      />

      <Callout tone="warning" title="Maintenance">
        When you change strategic north star or tactical “next”, update the <strong>source</strong> canvases first,
        then reconcile this combined view so it does not contradict them.
      </Callout>

      <Text tone="tertiary" size="small">
        Documentation only — open beside chat as a Cursor Canvas.
      </Text>
    </Stack>
  );
}

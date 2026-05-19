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
 * Long-term delivery map for HarboursOfPower. Goals are stated up front; phases
 * and milestones are planning defaults — edit when the north star shifts.
 * Tactical "what shipped / next sprint" lives in harbours-implementation-plan.canvas.tsx.
 * Combined executive view: harbours-combined-delivery-roadmap.canvas.tsx.
 */

const GOALS_INTRO = `No open questions were left unanswered in the request; the goals below are explicit
authoring defaults aligned with existing design direction (solo Mediterranean merchant fantasy,
Godot sim + Python twin, data-driven economy). Change them here if your priorities diverge.`;

const INITIAL_MILESTONES: TodoItem[] = [
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
      "Port politics v1: per-port JSON tolls as import duty (sales into city only), NPC smuggle vs caught vs pay, dock graft immunity, player graft UI, wholesale relief at tolled ports; SAVE_VERSION 28 field; twin parity.",
    status: "completed",
  },
  {
    id: "m-econ-tune",
    content:
      "Economy tuning vs 5k-day twin: NPC bankruptcy rate under duties, riot/grain runway, treasury drift; optional export tolls or player smuggle risk UI.",
    status: "in_progress",
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

export default function HarboursLongTermImplementationPlan() {
  const [milestones, setMilestones] = useCanvasState<TodoItem[]>("lt-milestones-v2", INITIAL_MILESTONES);

  const onMilestoneClick = (todo: TodoItem) => {
    setMilestones((prev) => prev.map((t) => (t.id === todo.id ? { ...t, status: nextStatus(t.status) } : t)));
  };

  return (
    <Stack gap={20}>
      <Stack gap={6}>
        <H1>HarboursOfPower — long-term implementation plan</H1>
        <Text tone="secondary" size="small">
          Repo: /Users/ari.lahti/HarboursOfPower — Godot 4 autoload sim, data JSON, headless twin <Code>tools/sim_100_days.py</Code>.
          Code truth beats this document; save schema follows <Code>SAVE_VERSION</Code> in <Code>autoload/game_state.gd</Code>.
        </Text>
      </Stack>

      <Callout tone="neutral" title="How this document was written">
        {GOALS_INTRO}
      </Callout>

      <Card>
        <CardHeader>Product and experience goals</CardHeader>
        <CardBody style={{ paddingTop: 0 }}>
          <Stack gap={10}>
            <Text>
              Solo depth first. A single player should get a long-lived campaign with legible cause and effect; NPC
              traffic stands in for absent humans without cheating the economy.
            </Text>
            <Text>
              Merchant fantasy, not map painting. Influence through logistics, credit, captains, and city condition —
              trust and betrayal under uncertainty, not only territory control.
            </Text>
            <Text>
              Living world credibility. Ports, granaries, fleets, and prices should remain believable when the player is
              idle; wars strain food and materiel without scripted riot guarantees.
            </Text>
            <Text>
              Fair observability. Long simulations and admin dumps should make stress visible for tuning; the Python twin
              stays in parity with Godot for substantive economy changes.
            </Text>
            <Text>
              Data-driven extensibility. Ports, goods, and world parameters live in JSON so designers can rebalance
              without rewriting core loops.
            </Text>
            <Text>
              Deferred breadth. Multiplayer and optional tactical combat are explicitly later phases; keep seams clean so
              they do not destabilize the solo economy.
            </Text>
          </Stack>
        </CardBody>
      </Card>

      <Grid columns="4" gap={16}>
        <Stat value="1d" label="Atomic tick (v1)" />
        <Stat value="Twin" label="GD + Python parity" tone="success" />
        <Stat value="Solo" label="Primary ship target" />
        <Stat value="v1" label="Duties + graft shipped" tone="success" />
      </Grid>

      <Divider />

      <H2>Technical goals</H2>
      <Table
        headers={["Goal", "Meaning", "Guardrail"]}
        rows={[
          [
            "Deterministic replay hooks",
            "Same seed and inputs should yield the same world trajectory in the twin; Godot run matches where feasible.",
            "Document intentional exceptions (UI-only randomness).",
          ],
          [
            "Save forward compatibility",
            "Bump SAVE_VERSION with migrations; never silent corruption on load.",
            "Twin load mirrors version gates.",
          ],
          [
            "Performance headroom",
            "Daily tick stays cheap enough for many ports, NPCs, and player fleet as scope grows.",
            "Profile before adding heavy graph solvers per tick.",
          ],
          [
            "UI honesty",
            "Numbers the player sees should map to sim state, or be labeled as estimates.",
            "Avoid hidden punitive RNG without surfaced odds.",
          ],
        ]}
      />

      <Divider />

      <H2>Roadmap by horizon</H2>
      <Text tone="secondary" size="small">
        Horizons are thematic order, not calendar commitments. Work can overlap; sequencing favours economy truth before
        political fantasy before network features.
      </Text>

      <H3>Horizon A — Economy and civic money (mostly shipped; tuning continues)</H3>
      <Table
        headers={["Track", "Status", "Notes"]}
        rows={[
          [
            "Pricing and stock dynamics",
            "Shipped baseline",
            "Reservation curves, market horizon, port biases; wine and grain under war; keep tuning with 5k-day runs.",
          ],
          [
            "NPC merchants",
            "Shipped + tune",
            "Purses, wholesale, traits, risk lots, dust-sell, bust streaks, used-hull slip; duties add pressure — watch twin bankruptcies.",
          ],
          [
            "Specie loop",
            "Shipped",
            "Mint batches, treasury, NPC/player gold and silver at mint-capable ports; strike wealth bonus; twin parity.",
          ],
          [
            "Luxury far trade",
            "Shipped + tune",
            "Queued consignments, coin sink on landing, spice-tier luxury; optional world_full.json luxury_import; twin parity.",
          ],
          [
            "Import duties (politics v1)",
            "Shipped + tune",
            "world_full.json per-port tolls on sales into city; NPC smuggle/graft; player graft + SAVE 28; wholesale relief when any duty exists.",
          ],
          [
            "Closed-loop materiel",
            "Ongoing",
            "Metal, wire, industry, war drawdowns; verify long-run twin stability as scope grows.",
          ],
        ]}
      />

      <H3>Horizon B — Cities and people</H3>
      <Table
        headers={["Track", "Outcomes", "Notes"]}
        rows={[
          [
            "Population and famine",
            "Grain mouths respond to sustained shortage and recovery; prosperity feeds back into commerce scale.",
            "Sim hooks exist; surface more clearly in play.",
          ],
          [
            "Unrest and riots",
            "Player understands runway, war grace, and probabilistic riot without spreadsheet literacy.",
            "Pair with better port-level narrative feedback.",
          ],
          [
            "Institutions (later)",
            "Temples, granary policy, patronage — only when they reinforce the economy loop, not decoration.",
            "Defer until food and coin loops are stable.",
          ],
        ]}
      />

      <H3>Horizon C — Player agency and politics</H3>
      <Table
        headers={["Track", "Outcomes", "Notes"]}
        rows={[
          [
            "Civic corruption and duties (v1)",
            "Per-good duties, graft to waive player import charges, NPC smuggling abstraction; coin flows to port prosperity.",
            "Extend: reputation cost, audits, export tolls, or two-sided quay fees without double-taxing the same leg.",
          ],
          [
            "Reputation and contracts",
            "Actions change how counterparties price and trust the player over seasons.",
            "Start local (one port cluster) before empire-scale.",
          ],
          [
            "War and peace leverage",
            "Embargoes, convoy pressure, materiel contribution change outcomes without instant win buttons.",
            "Align with existing war burst and food models.",
          ],
          [
            "Factions and cartels",
            "Agreements bind prices or routes; NPC traits modulate adherence.",
            "Reuse port_cartel_strength and trait fields when ready.",
          ],
        ]}
      />

      <H3>Horizon D — Sea, steel, and spectacle</H3>
      <Table
        headers={["Track", "Outcomes", "Notes"]}
        rows={[
          [
            "Voyage hazards",
            "Storms, delays, and lane risk modulated by season, cargo, and politics.",
            "Environmental, not hidden anti-player punishment.",
          ],
          [
            "Pirates and escorts",
            "Abstract losses and legal fallout first; tactics optional.",
            "Tie to visibility and nemesis systems in design docs.",
          ],
          [
            "Combat default",
            "Abstract battle resolution with clear inputs and casualties.",
            "Optional tactical screen only when opted in or stakes demand it.",
          ],
        ]}
      />

      <H3>Horizon E — Multiplayer (explicitly last)</H3>
      <Table
        headers={["Track", "Outcomes", "Notes"]}
        rows={[
          [
            "Rules engine isolation",
            "Sim core callable without Godot UI assumptions.",
            "Enables headless server path later.",
          ],
          [
            "Session topology",
            "Co-op or competitive trade sessions before MMO-scale claims.",
            "Open design; document chosen topology when picked.",
          ],
        ]}
      />

      <Divider />

      <H2>Strategic milestones (click to cycle status)</H2>
      <Text tone="secondary" size="small">
        Persists in canvas state (key lt-milestones-v2). Use for your own prioritisation; not a substitute for issues or
        the tactical canvas.
      </Text>
      <TodoListCard todos={milestones} defaultExpanded onTodoClick={onMilestoneClick} />

      <Divider />

      <H2>Related artifacts</H2>
      <Table
        headers={["Artifact", "Purpose"]}
        rows={[
          [
            "harbours-combined-delivery-roadmap.canvas.tsx",
            "Single view: strategic horizons + tactical shipped/next + milestones (separate canvas state key).",
          ],
          ["harbours-implementation-plan.canvas.tsx", "Near-term shipped vs next; personality and liquidity notes."],
          ["harbours-economy-rules.canvas.tsx", "Tick-level economy behaviour digest; keep in sync with code changes."],
          [
            "trade-empires-mechanics.canvas.tsx (other project)",
            "Original Mediterranean mechanics design sheet — cross-check philosophy when in doubt.",
          ],
        ]}
      />

      <Callout tone="info" title="When to revise this plan">
        After major scope decisions (combat default, MP shape, or a new core fantasy pillar), rewrite the goal cards and
        horizon tables here first, then align the tactical implementation canvas and economy rules canvas.
      </Callout>
    </Stack>
  );
}

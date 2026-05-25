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
} from "cursor/canvas";

/**
 * Cross-canvas audit (May 2026): implementation plans vs repo reality.
 * Update when major tracks ship or canvases are merged.
 */

const MAP_DONE = [
  "WorldMapChart + chunk manifest + mask-derived WEBP (ui/world_map_chart.gd)",
  "HarboursChartProjection + chunk_manifest_loader (scripts/map/)",
  "tools/slice_map_chunks.py; terrain save refreshes chunks",
  "Port map editor: corner-Wang terrain paint, dry-run/save, zoom-stable markers",
  "Editor-corrected wang16 tilemap + mask on disk; 16 ports applied to world_full.json",
  "Routes overlay prefers chunk map when manifest exists (ui/main.gd)",
  "use-case-map documents WorldMapChart fallback to RoutesMapChart",
];

const MAP_NEXT = [
  {
    id: "n1",
    content: "Lane polylines on chart from world_full.json lanes[] (read-only overlay)",
    why: "Graph visible on art; no travel duality yet",
  },
  {
    id: "n2",
    content: "MapDataLayer: sample mask at pixel → land/sea (block nonsense sea clicks later)",
    why: "Separates visual from gameplay authority",
  },
  {
    id: "n3",
    content: "Routes UX polish: saved view, chart-area filter, header copy when chunk vs fallback",
    why: "Player-facing completeness of Phase 1 shell",
  },
  {
    id: "n4",
    content: "Reconcile canvases: merge navigable + chunk plans; mark colonies-PNG path optional",
    why: "Docs currently contradict (all navigable tasks still pending)",
  },
  {
    id: "n5",
    content: "Optional richer basemap: wang_preview or 4096 art → re-slice (not Wang tile sprites)",
    why: "Mask-only chunks are functional but plain",
  },
];

const ECON_NEXT = [
  {
    id: "e1",
    content: "Close m-econ-tune: 5k-day twin — bankruptcies, grain-days, riots, treasury",
    why: "Long-term + combined canvases still in_progress",
  },
  {
    id: "e2",
    content: "City stress UX — famine/riot/recovery beyond admin lines",
    why: "Horizon B; makes civic economy legible",
  },
  {
    id: "e3",
    content: "Player political staging — reputation, embargoes, war hooks",
    why: "Horizon C; graft v1 exists, leverage does not",
  },
];

const PIRATES_DEFER = [
  "Per-hull map pose + hail/trade at sea",
  "Client vs headless travel split (twin stays abstract)",
  "Encounters tied to chart geometry",
];

const CANVAS_ROWS: string[][] = [
  [
    "harbours-economy-rules",
    "Reference",
    "Tick order, formulas, constants",
    "Keep synced with game_state / sim",
    "Living doc — not a backlog",
  ],
  [
    "harbours-implementation-plan",
    "Tactical economy",
    "Shipped: warmup, tick agents, OCEAN, liquidity",
    "Missing: all map/terrain work",
    "Add cross-link to map canvas or combined view",
  ],
  [
    "harbours-long-term-implementation-plan",
    "Strategic",
    "Horizons A–E, clickable milestones",
    "m-econ-tune in_progress",
    "North star — edit milestones as you ship",
  ],
  [
    "harbours-combined-delivery-roadmap",
    "Executive",
    "Merges tactical + strategic",
    "Institutional phase5 surface marked done",
    "Use for planning reviews; refresh after map ship",
  ],
  [
    "harbours-institutional-trade-roadmap",
    "Economy feature",
    "Phases 0–5 largely shipped in twin",
    "Player charter clerk surface",
    "Phase 6+ only if new obligation types",
  ],
  [
    "harbours-chunk-based-gaming-map",
    "Map (primary)",
    "C0–C2 done; terrain editor beyond plan",
    "C3–C7 pending",
    "Update tracker: terrain save, editor paint, applied ports",
  ],
  [
    "harbours-navigable-chart-implementation",
    "Map (legacy?)",
    "13 tasks all pending",
    "Superseded by chunk path for basemap",
    "Archive or merge — colonies PNG not primary anymore",
  ],
  [
    "harbours-pirates-style-travel-roadmap",
    "Map + sim duality",
    "All pending",
    "Still valid post-shell",
    "Do not start until lane overlay + mask sample exist",
  ],
  [
    "harbours-use-case-map",
    "Player flows",
    "Routes → WorldMapChart when manifest exists",
    "Terrain editor not player-facing",
    "Update when map UX changes",
  ],
];

const INITIAL_RECOMMENDED: TodoItem[] = MAP_NEXT.slice(0, 4).map((t) => ({
  id: t.id,
  content: t.content,
  status: "pending" as const,
}));

export default function HarboursForwardAnalysis() {
  return (
    <Stack gap={20}>
      <Stack gap={6}>
        <H1>Implementation canvases — audit &amp; forward path</H1>
        <Text tone="secondary" size="small">
          Nine canvases under <Code>canvases/</Code>. Code truth: repo (May 2026). Two parallel tracks —{" "}
          <strong>economy/sim</strong> (mature) and <strong>map/navigation</strong> (shell shipped, gameplay overlay
          thin).
        </Text>
      </Stack>

      <Grid columns={4} gap={16}>
        <Stat value="9" label="Canvases" />
        <Stat value="2" label="Active tracks" tone="info" />
        <Stat value="~60%" label="Map shell done" tone="success" />
        <Stat value="Stale" label="navigable-chart plan" tone="warning" />
      </Grid>

      <Callout tone="warning" title="Main finding: map docs lag code">
        Chunk map, terrain editor, and <Code>world_full.json</Code> port apply shipped recently, but{" "}
        <Code>harbours-navigable-chart-implementation.canvas.tsx</Code> still lists every task as pending and still
        centres the old colonies reference PNG. <Code>harbours-implementation-plan</Code> does not mention map work at
        all. Risk: the next sprint replans work that is already done or picks the wrong basemap path.
      </Callout>

      <Divider />

      <H2>Canvas roles (what each is for)</H2>
      <Table
        headers={["Canvas", "Role", "Accuracy vs repo", "Action"]}
        rows={CANVAS_ROWS}
      />

      <Divider />

      <H2>Track A — Economy &amp; living world (continue)</H2>
      <Text>
        Implementation, long-term, combined, institutional, and economy-rules canvases agree: the twin is the
        product core. Institutional trade phases 0–5 are largely in code; combined canvas marks phase5 player surface
        complete. North-star update: living world also means <strong>NPCs as persons</strong> — OCEAN traits shipped;
        names, history, player + NPC social memory, and a <strong>personal scribe (Tiro)</strong> UI to query the player&apos;s
        codex (who said what, whom to ask) are planned under <Code>EPIC-NPC</Code> / <Code>UC-PLAN-01</Code>.
      </Text>
      <Table
        headers={["Priority", "Work", "Why now"]}
        rows={ECON_NEXT.map((r) => [r.id.toUpperCase(), r.content, r.why])}
      />
      <Callout tone="neutral" title="Discipline">
        Any change to <Code>game_state.gd</Code>, <Code>sim_100_days.py</Code>, <Code>world_full.json</Code>, or{" "}
        <Code>goods.json</Code> → update economy-rules canvas + run 5k twin (per repo rules).
      </Callout>

      <Divider />

      <H2>Track B — Map &amp; navigation (finish Phase 1, then pirates)</H2>
      <H3>Already landed (not reflected in all canvases)</H3>
      <Card>
        <CardBody>
          <Stack gap={6}>
            {MAP_DONE.map((line) => (
              <Text key={line} size="small">
                ✓ <Code>{line}</Code>
              </Text>
            ))}
          </Stack>
        </CardBody>
      </Card>

      <H3>Recommended next (4–6 weeks of focused work)</H3>
      <TodoListCard title="Map track — suggested order" todos={INITIAL_RECOMMENDED} />

      <Table
        headers={["Step", "Deliverable", "Touches", "Defer"]}
        rows={[
          [
            "1",
            "Lane overlay on WorldMapChart",
            "world_full.json lanes[], chart_projection.gd",
            "Ship movement on map",
          ],
          [
            "2",
            "Mask sampler (land vs sea)",
            "MapDataLayer or inline in WorldMapChart",
            "Shallow/deep bands, fog",
          ],
          [
            "3",
            "Routes UX pass",
            "main.gd, use-case canvas",
            "Saved camera, filters",
          ],
          [
            "4",
            "Canvas consolidation",
            "chunk + navigable + combined",
            "Deleting history",
          ],
          [
            "5",
            "Richer art (optional)",
            "Basemap PNG → slice_map_chunks",
            "Tile-factory coast sprites",
          ],
        ]}
      />

      <Callout tone="info" title="Pirates / travel duality — explicit defer">
        <Stack gap={6}>
          <Text>
            <Code>harbours-pirates-style-travel-roadmap.canvas.tsx</Code> remains the right long arc, but starting it
            before the chart shows lanes and respects land/sea will duplicate effort. Keep{" "}
            <Code>sim_100_days.py</Code> on abstract legs; add client-only pose when the shell is credible.
          </Text>
          <Text size="small" tone="secondary">
            Deferred items: {PIRATES_DEFER.join(" · ")}
          </Text>
        </Stack>
      </Callout>

      <Divider />

      <H2>Suggested consolidation (reduce confusion)</H2>
      <Grid columns={2} gap={16}>
        <Card>
          <CardHeader>Keep</CardHeader>
          <CardBody style={{ paddingTop: 0 }}>
            <Stack gap={6}>
              <Text size="small">harbours-economy-rules — formula sheet</Text>
              <Text size="small">harbours-implementation-plan — tactical economy pulse</Text>
              <Text size="small">harbours-long-term + combined — strategy</Text>
              <Text size="small">harbours-institutional-trade — feature depth</Text>
              <Text size="small">harbours-use-case-map — player contract</Text>
              <Text size="small">harbours-chunk-based-gaming-map — map backlog (update tracker)</Text>
              <Text size="small">harbours-pirates-style-travel — Phase 2 map (unchanged scope)</Text>
            </Stack>
          </CardBody>
        </Card>
        <Card>
          <CardHeader>Merge or archive</CardHeader>
          <CardBody style={{ paddingTop: 0 }}>
            <Stack gap={6}>
              <Text size="small">
                <strong>harbours-navigable-chart-implementation</strong> — fold remaining items (alignment manifest,
                homography, colonies PNG as optional reference) into chunk canvas as a short “legacy alignment”
                section; mark duplicate tasks completed or cancelled.
              </Text>
              <Text size="small">
                Stop treating Wang tile sprites and repeated tile-gen as the player basemap path (Phase A guard already
                warns tooling).
              </Text>
            </Stack>
          </CardBody>
        </Card>
      </Grid>

      <Divider />

      <H2>One sensible roadmap (integrated)</H2>
      <Table
        headers={["Phase", "Focus", "Success looks like"]}
        rows={[
          [
            "Now",
            "Economy tune + map shell polish",
            "5k twin within targets; Routes shows mask chunks, lanes, stable port drag",
          ],
          [
            "Next",
            "City stress UX + political staging design",
            "Player reads famine/riot; design doc for reputation/embargo hooks",
          ],
          [
            "Then",
            "Pirates-style client travel (lite)",
            "PC/NPC tokens on lanes; twin still abstract; hail stub",
          ],
          [
            "Later",
            "Sea hazards, combat abstract, factions",
            "Long-term milestones C, D, social graph",
          ],
          [
            "Last",
            "Multiplayer",
            "Only if solo economy + map credible",
          ],
        ]}
      />

      <Callout tone="success" title="Immediate next action (single sprint)">
        Pick <strong>one</strong> map ticket (lane overlay) and <strong>one</strong> economy ticket (5k twin report after
        last world_full port moves). Update <Code>harbours-chunk-based-gaming-map.canvas.tsx</Code> tracker in the same PR
        so canvases stop lying.         Open <Code>harbours-consolidated-implementation-plan.canvas.tsx</Code> for the SAFe backlog;{" "}
        <Code>harbours-combined-delivery-roadmap.canvas.tsx</Code> for executive milestones.
      </Callout>

      <Text tone="tertiary" size="small">
        Generated from repo state May 2026. Not a substitute for editing source canvases when you ship.
      </Text>
    </Stack>
  );
}

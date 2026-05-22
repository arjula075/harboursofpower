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
 * Hybrid Mediterranean map: continuous visual chunks + logical data grid + existing
 * port/lane graph. Complements harbours-navigable-chart-implementation.canvas.tsx
 * (UI shell) and harbours-pirates-style-travel-roadmap.canvas.tsx (travel duality).
 *
 * Source discussion: ChatGPT “Hybrid Map System” — tiles as metadata, not coastline art.
 */

const STATUS_ORDER: TodoStatus[] = ["pending", "in_progress", "completed"];

function nextStatus(s: TodoStatus): TodoStatus {
  const i = STATUS_ORDER.indexOf(s);
  return STATUS_ORDER[(i + 1) % STATUS_ORDER.length] ?? "pending";
}

const INITIAL_TRACKER: TodoItem[] = [
  {
    id: "a-phase-confirm",
    content:
      "Phase A only: before tile coastline generation, prompt “Are you sure?” every time (tools/chunk_map_phase_a.py; orchestrator + build_recursive_tilemap_wang16; pass --yes for scripts).",
    status: "completed",
  },
  {
    id: "c0-roles",
    content:
      "Document three layers in repo README snippet: Visual (chunks), Gameplay (world_full lanes/ports), Data (mask/grid from tile JSON).",
    status: "pending",
  },
  {
    id: "c1-basemap-master",
    content:
      "Master: mediterranean_recursive_tilemap_wang16_1px_mask.png (2000×1000) → docs/maps/chunks via slice tool.",
    status: "completed",
  },
  {
    id: "c1-slice-tool",
    content:
      "tools/slice_map_chunks.py — CHUNK_SIZE 2048, med_{cx}_{cy}.webp + data/maps/chunk_manifest.json.",
    status: "completed",
  },
  {
    id: "c2-godot-root",
    content:
      "WorldMapChart Control in Routes overlay (draw-time chunk blit; SubViewport/WorldMapRoot.tscn deferred).",
    status: "completed",
  },
  {
    id: "c2-chunk-loader",
    content:
      "Chunk textures loaded from manifest in WorldMapChart; multi-chunk culling when manifest has 2+ entries.",
    status: "completed",
  },
  {
    id: "c2-projection",
    content:
      "scripts/map/chart_projection.gd — map_u/v ↔ logical pixels ↔ screen (shared pan/zoom).",
    status: "completed",
  },
  {
    id: "c3-mask-export",
    content:
      "Export gameplay mask from mediterranean_recursive_tilemap_wang16_1px_mask.png (or RLE grid) — land/sea/shallow bands; NOT wang tile sprites.",
    status: "pending",
  },
  {
    id: "c3-data-api",
    content:
      "MapDataLayer.gd: sample terrain at world pixel (land, coastal_water, open_sea); optional chart_area_id lookup from chart_area_index bounds.",
    status: "pending",
  },
  {
    id: "c4-lanes-ui",
    content:
      "Lane polylines from world_full.json lanes[] on NavigationOverlay; voyage progress along edge geometry (pirates roadmap).",
    status: "pending",
  },
  {
    id: "c4-hit-test",
    content:
      "Port hit-test on graph nodes; sea click = empty / future course; block land pixels via mask sample if free movement added later.",
    status: "pending",
  },
  {
    id: "c5-chart-areas",
    content:
      "Optional: preload chunk subset when filtering by chart_area_id (8 rects in chart_area_index.json); overlaps OK.",
    status: "pending",
  },
  {
    id: "c6-editor",
    content:
      "Keep port_map_editor_* for mask/port placement; stop investing in wang coast tile *visuals*; editor writes ports + alignment only.",
    status: "pending",
  },
  {
    id: "c7-use-case-canvas",
    content:
      "When map mode ships: update harbours-use-case-map.canvas.tsx; link this canvas from navigable-chart canvas.",
    status: "pending",
  },
];

export default function HarboursChunkBasedGamingMap() {
  const [tracker, setTracker] = useCanvasState<TodoItem[]>("chunk-map-tracker-v1", INITIAL_TRACKER);

  const onTodoClick = (todo: TodoItem) => {
    setTracker((prev) =>
      prev.map((t) => (t.id === todo.id ? { ...t, status: nextStatus(t.status) } : t)),
    );
  };

  const done = tracker.filter((t) => t.status === "completed").length;

  return (
    <Stack gap={20}>
      <Stack gap={6}>
        <H1>Chunk-based gaming map — implementation plan</H1>
        <Text tone="secondary" size="small">
          Analysis of the hybrid map proposal (continuous visuals + invisible navigation + data grids) applied to
          HarboursOfPower. Tiles remain tooling; the player-facing sea is chunked painted art. Gameplay routing stays on{" "}
          <Code>data/world_full.json</Code> ports and <Code>lanes</Code> / <Code>npc_lanes</Code>.
        </Text>
      </Stack>

      <Grid columns={4} gap={16}>
        <Stat value="3" label="Layers" tone="info" />
        <Stat value="8" label="Chart areas (load hints)" />
        <Stat value="2000×1000" label="Logical grid" />
        <Stat value={`${done}/${tracker.length}`} label="Checklist done" tone={done === tracker.length ? "success" : undefined} />
      </Grid>

      <Callout tone="info" title="Verdict on the ChatGPT thread">
        The recommendation matches where the project already points: <Code>world_full.json</Code> is the sea graph;
        recursive tile JSON is land/sea classification and editor geometry, not the shipping art path. The gap is a{" "}
        <strong>deliberate visual layer</strong> (chunked textures) wired to the same <Code>map_u</Code>/<Code>map_v</Code> frame
        as ports — not another Wang/tile coastline iteration.
      </Callout>

      <Divider />

      <H2>What we have today</H2>
      <Table
        headers={["Asset / system", "Role today", "Hybrid role"]}
        rows={[
          [
            "docs/mediterranean_recursive_tilemap_*.json",
            "1px/3px land–sea + coast bitmasks; port editors",
            "Data layer only — export masks / shallow bands",
          ],
          [
            "docs/chart_area_tilemaps_and_maps/*",
            "8 rectangular cuts in 2000×1000 space",
            "Regional preload hints + editor crops (not visual tiles)",
          ],
          [
            "data/world_full.json",
            "Ports, lanes, npc_lanes, chart_areas, map_u/v",
            "Gameplay graph — unchanged authority",
          ],
          [
            "docs/reference_greek_phoenician_colonies_mediterranean.png",
            "Planned navigable-chart basemap",
            "Candidate master art → upscale → chunk slice",
          ],
          [
            "tools/sim_100_days.py + GameState",
            "Abstract day-tick voyages",
            "Headless stays abstract; client adds map pose (pirates canvas)",
          ],
        ]}
      />

      <H2>Target architecture (three layers)</H2>
      <Card>
        <CardBody>
          <Code>
            {`WorldMapRoot (Node2D)
 ├─ MapVisuals          # Sprite2D chunks — painted Mediterranean, no tile repeat
 ├─ NavigationOverlay   # Lane polylines + port markers (graph from world_full)
 ├─ DataLayers          # Optional ColorRect/mask sampler — land/sea/shallow
 └─ Ships               # Tokens along lane geometry + progress

Parallel data (not rendered as tiles):
  res://maps/mediterranean/chunks/med_{cx}_{cy}.webp
  res://maps/mediterranean/masks/land_sea_mask.png   # from wang16 mask export
  data/world_full.json                               # ports + lanes (SeaNode equivalent)
  data/reference_colonies_map_alignment.json         # PNG ↔ logical grid`}
          </Code>
        </CardBody>
      </Card>

      <H3>Coordinate contract</H3>
      <Text>
        Keep the existing logical frame: <Code>map_u = x / 2000</Code>, <Code>map_v = y / 1000</Code> (see navigable-chart
        canvas). World pixels for rendering: <Code>world_x = map_u × MAP_WORLD_W</Code>,{" "}
        <Code>world_y = map_v × MAP_WORLD_H</Code>. Default <Code>MAP_WORLD_W/H = 4096×2048</Code> (2× logical) so coast
        detail matches mask resolution; chunks are in <em>world pixel</em> space, not tile indices.
      </Text>

      <H3>Chunk loading (Godot 4)</H3>
      <Table
        headers={["Constant", "Suggested value", "Notes"]}
        rows={[
          ["CHUNK_SIZE", "2048", "WEBP/PNG per chunk; ~4–9 visible at zoom 1"],
          ["LOAD_RADIUS", "1", "3×3 neighbourhood around camera chunk"],
          ["get_chunk_coord(pos)", "Vector2i(floor(pos.x / CHUNK_SIZE), …)", "Unload distant children"],
        ]}
      />

      <H3>Sea graph — already exists</H3>
      <Text>
        ChatGPT’s <Code>SeaNode</Code> + edges map directly to <Code>world_full.json</Code>: each port is a node;{" "}
        <Code>lanes[]</Code> entries carry <Code>from</Code>/<Code>to</Code>, days, open-sea fraction, piracy metadata.
        Do <em>not</em> introduce a second graph format until lane geometry for the chart is stable — extend lane records
        with optional <Code>{"waypoints: [{u,v}, …]"}</Code> for curved coastal legs on the overlay only.
      </Text>

      <Divider />

      <H2>Tile JSON — not useless</H2>
      <Grid columns={2} gap={16}>
        <Stack gap={8}>
          <H3>Keep for data</H3>
          <Text size="small">
            Land/sea classification, minimum land components, chart-area bounds, port snap indices, future shallow/deep
            bands, encounter density, faction tint grids, fog-of-war cells.
          </Text>
        </Stack>
        <Stack gap={8}>
          <H3>Stop for visuals</H3>
          <Text size="small">
            Repeated Wang coast sprites, per-cell orange coast preview as basemap, fighting tile seams for a
            satellite-like sea. The mask PNG (<Code>mediterranean_recursive_tilemap_wang16_1px_mask.png</Code>) is the
            handoff artifact into <Code>masks/land_sea_mask.png</Code>.
          </Text>
        </Stack>
      </Grid>

      <Divider />

      <H2>Phase A — tile generation guard (only deliverable)</H2>
      <Callout tone="warning" title="Are you sure?">
        Phase A does not block tooling or remove tile-factory. It only adds a user-facing rule: whenever someone
        starts coastline tile generation, ask <strong>Are you sure?</strong> every time. Implemented in{" "}
        <Code>tools/chunk_map_phase_a.py</Code>; wired into <Code>tools/tile-factory/scripts/orchestrator.py</Code> (API /
        mosaic commands) and <Code>tools/build_recursive_tilemap_wang16_1px.py</Code> (full rebuild; skipped for{" "}
        <Code>--maps-only</Code> / <Code>--split-only</Code>). Use <Code>--yes</Code> only for automation.
      </Callout>

      <H2>Migration path (low risk)</H2>
      <Table
        headers={["Phase", "Outcome", "Touches"]}
        rows={[
          [
            "A — Tile gen guard",
            "Prompt “Are you sure?” on every tile-generation CLI run; no other Phase A work",
            "chunk_map_phase_a.py, orchestrator.py, build_recursive_tilemap_wang16_1px.py",
          ],
          [
            "B — Master + manifest",
            "One stylized master image + chunk_manifest.json",
            "tools/slice_map_chunks.py, docs/maps/",
          ],
          [
            "C — Godot chunk viewer",
            "Pan/zoom chunked sprites; ports from map_u/v",
            "scenes/map/, chunk_loader.gd",
          ],
          [
            "D — Mask sampler",
            "Point queries: land vs sea; optional coastal band",
            "MapDataLayer.gd, mask PNG",
          ],
          [
            "E — Lanes + ships",
            "Overlay + pirates travel client pose",
            "ui/main.gd, game_state signals",
          ],
          [
            "F — Sim duality",
            "Twin unchanged; client-only interpolation",
            "sim_100_days.py audit (pirates canvas)",
          ],
        ]}
      />

      <H2>Proposed repo layout</H2>
      <Card variant="borderless">
        <CardBody>
          <Stack gap={6}>
            <Text size="small">
              <Code>docs/maps/mediterranean_master_4096.webp</Code> — source art (or import from reference PNG pipeline)
            </Text>
            <Text size="small">
              <Code>docs/maps/chunks/med_0_0.webp</Code> … — build artifacts (Godot import or copy to res://)
            </Text>
            <Text size="small">
              <Code>data/maps/chunk_manifest.json</Code> — chunk size, world size, files[], optional chart_area tags
            </Text>
            <Text size="small">
              <Code>docs/maps/masks/land_sea_mask.png</Code> — 4096×2048 aligned to master (from wang16 mask upscale)
            </Text>
            <Text size="small">
              <Code>scenes/map/world_map_root.tscn</Code> + <Code>scripts/map/chart_projection.gd</Code>
            </Text>
          </Stack>
        </CardBody>
      </Card>

      <H2>chunk_manifest.json (sketch)</H2>
      <Card>
        <CardBody>
          <Code>
            {`{
  "schema": 1,
  "world_width": 4096,
  "world_height": 2048,
  "logical_width": 2000,
  "logical_height": 1000,
  "chunk_size": 2048,
  "chunks": [
    { "id": "0_0", "cx": 0, "cy": 0, "path": "chunks/med_0_0.webp",
      "x0": 0, "y0": 0, "x1": 2048, "y1": 2048 }
  ]
}`}
          </Code>
        </CardBody>
      </Card>

      <Divider />

      <H2>Relationship to other canvases</H2>
      <Table
        headers={["Canvas", "Scope"]}
        rows={[
          [
            "harbours-navigable-chart-implementation",
            "UI entry, camera, projection, single-PNG basemap prototype — chunk loader supersedes single TextureRect at scale",
          ],
          [
            "harbours-pirates-style-travel-roadmap",
            "Client map pose vs headless abstract legs; lane interpolation",
          ],
          [
            "harbours-use-case-map",
            "Player flows when map mode ships",
          ],
          [
            "This canvas",
            "Visual/data split, chunk pipeline, demotion of tile art",
          ],
        ]}
      />

      <Divider />

      <H2>Implementation checklist</H2>
      <Text tone="secondary" size="small">
        Key <Code>chunk-map-tracker-v1</Code> — click rows to cycle status.
      </Text>
      <TodoListCard todos={tracker} defaultExpanded onTodoClick={onTodoClick} />

      <Divider />

      <H3>Recommended order</H3>
      <Text tone="secondary" size="small">
        A is done when the confirm prompt ships (no further Phase A scope). Then B (master + slice tool) → C (Godot chunks
        + projection, parallel with navigable-chart phases 1–4) → D (mask) → E (lanes/ships per pirates roadmap) → F.
        Ship the smallest playable slice: chunked static map + port dots + lane lines, no free sailing.
      </Text>

      <Callout tone="neutral" title="First vertical slice (MVP)">
        One master WEBP, 2×2 or 4×2 chunks, camera pan/zoom, ports from <Code>world_full.json</Code>, straight or
        great-circle lane segments between endpoints. No shallow-water gameplay, no procedural coast. Validates the hybrid
        before depth/wind zones or mask-driven movement blocks.
      </Callout>
    </Stack>
  );
}

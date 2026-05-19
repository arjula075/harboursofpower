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
 * Navigable chart only. Basemap: colonies reference PNG + alignment manifest in
 * data/reference_colonies_map_alignment.json. Travel sim duality lives in
 * harbours-pirates-style-travel-roadmap.canvas.tsx.
 */

const STATUS_ORDER: TodoStatus[] = ["pending", "in_progress", "completed"];

function nextStatus(s: TodoStatus): TodoStatus {
  const i = STATUS_ORDER.indexOf(s);
  return STATUS_ORDER[(i + 1) % STATUS_ORDER.length] ?? "pending";
}

const INITIAL_TRACKER: TodoItem[] = [
  {
    id: "m-entry",
    content:
      "Map mode entry from main UI; enter/exit; behaviour vs port UI documented in use-case canvas when shipped.",
    status: "pending",
  },
  {
    id: "m-viewport",
    content:
      "Chart viewport Control with clipping; resizable shell before art dependency.",
    status: "pending",
  },
  {
    id: "m-align-manifest",
    content:
      "Wire Godot to data/reference_colonies_map_alignment.json (schema v2) + world_full.json map_u/map_v.",
    status: "pending",
  },
  {
    id: "m-projection",
    content:
      "Projection: map_u/map_v (0..1 game chart) ↔ screen; apply optional homography once control_points[] populated from PNG picks.",
    status: "pending",
  },
  {
    id: "m-chart-areas",
    content:
      "chart_areas legend/filters from world.chart_areas + port.chart_area_id.",
    status: "pending",
  },
  {
    id: "m-basemap-png",
    content:
      "TextureRect (or equivalent) using docs/reference_greek_phoenician_colonies_mediterranean.png as primary basemap; legacy SVG maps optional overlay only.",
    status: "pending",
  },
  {
    id: "m-camera",
    content:
      "Pan/zoom with clamps; wheel-to-cursor; optional saved view.",
    status: "pending",
  },
  {
    id: "m-ports",
    content:
      "Port markers from GameState + world JSON; tooltips; selection → destination flow.",
    status: "pending",
  },
  {
    id: "m-hit-empty",
    content:
      "Sea vs port hit-testing; hooks for future course plotting.",
    status: "pending",
  },
  {
    id: "m-lanes",
    content:
      "Lane overlay (Line2D / batch) from voyage graph; toggle visibility.",
    status: "pending",
  },
  {
    id: "m-dynamic",
    content:
      "Ship token layer above lanes; day-tick batch updates.",
    status: "pending",
  },
  {
    id: "m-perf",
    content:
      "Label LOD, marker pooling, bake large textures at load if needed.",
    status: "pending",
  },
  {
    id: "m-docs",
    content:
      "Update harbours-use-case-map.canvas.tsx when navigation ships; run tools/reference_colonies_map_report.py to verify manifest fill state.",
    status: "pending",
  },
];

export default function HarboursNavigableChartImplementation() {
  const [tracker, setTracker] = useCanvasState<TodoItem[]>("navigable-chart-tracker-v2", INITIAL_TRACKER);

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
        <H1>HarboursOfPower — navigable chart (implementation plan)</H1>
        <Text tone="secondary" size="small">
          Primary chart frame: <Code>map_u</Code> = <Code>x / 2000</Code>, <Code>map_v</Code> = <Code>y / 1000</Code> (logical grid from{" "}
          <Code>docs/8670b2bf-409a-4880-ae53-683f5eb2d2a6.png</Code> table). <Code>data/world_full.json</Code> is the single
          source of truth for port coords. Basemap texture:{" "}
          <Code>docs/reference_greek_phoenician_colonies_mediterranean.png</Code>. Manifest + affine:{" "}
          <Code>data/reference_colonies_map_alignment.json</Code>. Future-only settlements:{" "}
          <Code>data/extra_colony_ports.json</Code>. Run <Code>python3 tools/reference_colonies_map_report.py</Code>.
        </Text>
      </Stack>

      <Grid columns={4} gap={16}>
        <Stat value="8" label="Phases" />
        <Stat value={`${done}/${tracker.length}`} label="Checklist done" tone={done === tracker.length ? "success" : undefined} />
        <Stat value="13" label="Tracked tasks" />
        <Stat value="2000×1000" label="Logical grid" tone="info" />
      </Grid>

      <Callout tone="neutral" title="Coordinate sheet → world data">
        Ten ports were snapped to the grid table in <Code>docs/8670b2bf-409a-4880-ae53-683f5eb2d2a6.png</Code>; the
        other 65 used the recorded affine from the previous chart (see <Code>data/reference_colonies_map_alignment.json</Code>
        ). Godot still uses the 1024×508 colonies PNG as art; add a UV homography later if pixel pick diverges from the
        logical grid. Extra map-only cities: <Code>data/extra_colony_ports.json</Code>.
      </Callout>

      <Divider />

      <H2>Phase 1 — Shell & entry</H2>
      <Table
        headers={["Slice", "Done when", "Typical touch"]}
        rows={[
          ["1a — Map mode route", "Open/close map from main UI.", "ui/main.gd or map scene"],
          ["1b — Viewport root", "Clipped chart rect; resize-safe.", "Control"],
          ["1c — Placeholder", "Flat sea colour under everything.", "ColorRect"],
        ]}
      />

      <H2>Phase 2 — Projection & manifest bind</H2>
      <Text>
        Load <Code>reference_colonies_map_alignment.json</Code>; until <Code>control_points</Code> is filled, treat{" "}
        <Code>world_full.json</Code> <Code>map_u</Code>/<Code>map_v</Code> as the authoritative gameplay chart (same
        0..1 frame as today). After homography, either update JSON coords or multiply projection matrix at runtime.
      </Text>
      <Table
        headers={["Slice", "Done when", "Notes"]}
        rows={[
          ["2a — JSON load", "Parse manifest + port rows at startup.", "Resource or FileAccess"],
          ["2b — Affine fit", "Solve from ≥3 non-collinear control points.", "Emit warnings if RMS error high"],
          ["2c — Resize", "Recompute pixel positions on resize.", "Centralize in one ChartProjection module"],
        ]}
      />

      <H2>Phase 3 — Basemap (reference PNG)</H2>
      <Text>
        Drop the PNG under <Code>TextureRect</Code> (stretch mode = keep aspect or crop to chart frame). Optional:
        multiply tint by <Code>chart_areas</Code> for readability. Older SVG coast files stay secondary references
        only.
      </Text>
      <Table
        headers={["Slice", "Done when", "Notes"]}
        rows={[
          ["3a — PNG import", "Godot .import present; mipmaps off for crisp labels if blurry.", "Import defaults"],
          ["3b — Legend crop", "If title/legend steals clicks, crop texture or mask input region.", "NinePatch / margin"],
          ["3c — Fallback", "If PNG missing, flat colour + text warning.", "Dev-only assert"],
        ]}
      />

      <H2>Phase 4 — Pan & zoom</H2>
      <Table
        headers={["Slice", "Done when", "Risk"]}
        rows={[
          ["4a — Pan", "Drag pans; clamp.", "Do not swallow port clicks"],
          ["4b — Zoom", "Wheel + limits.", "HiDPI"],
          ["4c — Reset", "Recenter control.", "Optional"],
        ]}
      />

      <H2>Phase 5 — Ports & hit-testing</H2>
      <Table
        headers={["Slice", "Done when", "Notes"]}
        rows={[
          ["5a — Markers", "Instanced port nodes at projected positions.", "Same ids as GameState"],
          ["5b — Tooltips", "Name + role from world data.", ""],
          ["5c — Selection", "Signal port_id to existing voyage / intel flows.", "Single selection"],
        ]}
      />

      <H2>Phase 6 — Lanes & dynamic tokens</H2>
      <Text>Lane geometry above basemap, below or above ship tokens per z-order choice; batch updates from sim.</Text>

      <H2>Phase 7 — Performance</H2>
      <Text>Label LOD, pooling, async texture work for full <Code>world_full.json</Code> port counts.</Text>

      <H2>Phase 8 — Polish</H2>
      <Text>Filters, minimap strip, contrast pass, optional SFX.</Text>

      <Divider />

      <Card>
        <CardHeader>Repo files for this track</CardHeader>
        <CardBody>
          <Stack gap={10}>
            <Text size="small">
              <Code>docs/8670b2bf-409a-4880-ae53-683f5eb2d2a6.png</Code> — grid coordinate sheet (1600×983 PNG, 2000×1000
              logical table).
            </Text>
            <Text size="small">
              <Code>data/extra_colony_ports.json</Code> — map-only colony candidates (not sim ports until promoted).
            </Text>
            <Text size="small">
              <Code>data/reference_colonies_map_alignment.json</Code> — dimensions, workflow, per-port rows, ambiguity
              notes, <Code>control_points</Code> array (you fill).
            </Text>
            <Text size="small">
              <Code>tools/reference_colonies_map_report.py</Code> — quick manifest summary.
            </Text>
            <Text size="small">
              <Code>data/world_full.json</Code> — <Code>ports[].map_u</Code>, <Code>map_v</Code>,{" "}
              <Code>chart_area_id</Code>.
            </Text>
          </Stack>
        </CardBody>
      </Card>

      <H2>Task checklist</H2>
      <Text tone="secondary" size="small">
        Key <Code>navigable-chart-tracker-v2</Code> (click rows to cycle status).
      </Text>
      <TodoListCard todos={tracker} defaultExpanded onTodoClick={onTodoClick} />

      <Divider />

      <H3>Order of operations</H3>
      <Text tone="secondary" size="small">
        1 → 2 (manifest + projection) → 4 → 5 → 6 → 7 → 3 polish order: get PNG on screen early in phase 3 parallel
        with projection experiments, but do not block pan/zoom on art.
      </Text>
    </Stack>
  );
}

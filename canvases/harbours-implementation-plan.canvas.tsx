import { Callout, Code, Divider, H1, H2, H3, Stack, Table, Text } from "cursor/canvas";

/**
 * HarboursOfPower — delivery / roadmap canvas (not the economy formula sheet).
 * Pair with harbours-economy-rules.canvas.tsx for tick-level behaviour.
 */
export default function HarboursImplementationPlan() {
  return (
    <Stack gap={20}>
      <Stack gap={6}>
        <H1>HarboursOfPower — implementation plan</H1>
        <Text tone="secondary" size="small">
          Updated with living-economy, NPC personality, and merchant-liquidity work. Code truth: repo; save format
          follows <Code>SAVE_VERSION</Code> in <Code>autoload/game_state.gd</Code>.
        </Text>
      </Stack>

      <Callout tone="info" title="How to use this canvas">
        Track <strong>shipped vs next</strong> for autonomous world + player staging. When scope shifts, edit this
        file; when economy numbers or tick order change, still update{" "}
        <Code>harbours-economy-rules.canvas.tsx</Code> per <Code>.cursor/rules/update-economy-rules-canvas.mdc</Code>.
        For a single scroll that merges this file with the long-term horizons, open{" "}
        <Code>harbours-combined-delivery-roadmap.canvas.tsx</Code>.
      </Callout>

      <H2>Recently shipped (living world &amp; merchants)</H2>
      <Table
        headers={["Area", "What landed", "Where"]}
        rows={[
          [
            "Autonomous economy",
            "Deferred NPC-only warmup on new campaign; world_full.json autonomy_warmup_days; twin runs same on Sim.load.",
            "game_state.gd, sim_100_days.py, data/world_full.json",
          ],
          [
            "Tick agents",
            "Named phases: information, production, industry, NPC trade + dues + cartel + commerce pulse, unrest, war, demographics, merchant home-count sync.",
            "game_state.gd, sim_tick_agents.gd, sim_100_days.py",
          ],
          [
            "NPC personality (OCEAN-style)",
            "Five persisted traits (0–1); affect depart gate, memory vs random dest, lot size blend, agreeable wholesale tilt, dust purse floor, extraversion trade passes, voyage stress, hull/expand behaviour. Not wired to faction cartels yet.",
            "game_state.gd, sim_100_days.py, economy rules canvas",
          ],
          [
            "Merchant liquidity",
            "Softer neuro/agree/extraversion coefficients; slightly better NPC wholesale mults; lower purse reserve; higher rookie purse band; 6-day bust grace; capped effective risk blend.",
            "game_state.gd, sim_100_days.py, economy rules canvas",
          ],
          [
            "Docs &amp; twin discipline",
            "Economy rules canvas + sim module docstring list synced constants; post-change 5k sim rule for substantive economy edits.",
            ".cursor/rules/*.mdc, tools/sim_100_days.py",
          ],
        ]}
      />

      <Divider />

      <H2>Current focus</H2>
      <Text>
        <strong>Living world first:</strong> economy and NPC traffic should feel credible before the player moves
        the political needle. Keep twin and Godot behaviour aligned; re-run long sims after tuning.
      </Text>

      <Divider />

      <H2>Next (not started or early)</H2>
      <Table
        headers={["Track", "Goal", "Notes"]}
        rows={[
          [
            "Player political weight",
            "Stage impact: early none → mid local → late city-scale rise/fall.",
            "Design pass: which actions feed reputation, embargoes, riots, war — then code hooks.",
          ],
          [
            "Cartels &amp; alliances",
            "Traits already avoid social cartel use; wire agreeableness/extraversion when faction systems exist.",
            "May reuse port_cartel_strength + new diplomacy graph.",
          ],
          [
            "UX clarity",
            "Optional banner when warmup advances calendar (Day 25 after 24 NPC days).",
            "Small UI only; no sim change required.",
          ],
          [
            "Further NPC economy",
            "If bankruptcies still high at long horizons: NPC-only trade fee discount or officer-pay carve-out; profile fee vs wholesale.",
            "Measure with sim_100_days.py at realistic N.",
          ],
          ["Godot validation", "Playtest + headless checks after major tick changes.", "CI / local Godot as available."],
        ]}
      />

      <Divider />

      <H3>Key files (bookmark)</H3>
      <Table
        headers={["Path", "Role"]}
        rows={[
          ["autoload/game_state.gd", "Daily tick orchestration, NPC agents, save/load, SAVE_VERSION."],
          ["autoload/sim_tick_agents.gd", "Shared commerce / pulse / cartel helpers."],
          ["tools/sim_100_days.py", "Python twin; must match GD constants and tick order."],
          ["data/world_full.json", "Ports, npc_traders, autonomy_warmup_days, war, industry."],
          ["data/goods.json", "Prices, tiers, stock targets."],
          ["harbours-economy-rules.canvas.tsx", "Behaviour digest for economy-facing code."],
        ]}
      />

      <Text tone="tertiary" size="small">
        Open beside chat as a Cursor Canvas. Documentation only.
      </Text>
    </Stack>
  );
}

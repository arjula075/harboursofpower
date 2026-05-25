import { Callout, Code, Divider, Grid, H1, H2, H3, Stack, Table, Text } from "cursor/canvas";

/**
 * Player-visible use case map for HarboursOfPower.
 * Keep in sync when flows change — see `.cursor/rules/update-use-case-map-canvas.mdc`.
 */
export default function HarboursUseCaseMap() {
  return (
    <Stack gap={20}>
      <Stack gap={6}>
        <H1>HarboursOfPower — use case map</H1>
        <Text tone="secondary" size="small">
          Describes <strong>who does what, where, and what changes</strong> in the shipped UI. For tick-order and economy
          math, use <Code>harbours-economy-rules.canvas.tsx</Code>.
        </Text>
      </Stack>

      <Callout tone="warning" title="Maintenance">
        After any change listed in <Code>.cursor/rules/update-use-case-map-canvas.mdc</Code>, update this canvas in the
        same pass: add or retire use cases, fix states and triggers, and adjust code pointers so nothing here lies about
        the build.
      </Callout>

      <Callout tone="info" title="Scope">
        Covers the main scene (<Code>ui/main.gd</Code>) plus <Code>HarboursGameState</Code> APIs those panels call.
        Design rule: <strong>show numbers, not omniscient truth</strong> — tables carry source, age, and reliability where
        the engine exposes them.
      </Callout>

      <Grid columns={2} gap={20}>
        <Stack gap={10}>
          <H2>Player states</H2>
          <Text>
            <strong>Docked</strong> — <Code>player_port_id</Code> set; left rail shows six city views; main{" "}
            <Code>TradeScroll</Code> hosts tables and actions. <strong>Under way</strong> — <Code>is_at_sea()</Code>; rail
            hidden; main panel shows voyage readout only; advance until landfall.
          </Text>
          <H3>Macro loop</H3>
          <Text tone="secondary" size="small">
            Pick a view → act → <strong>Advance day</strong> runs the global tick → UI rebuilds on <Code>day_advanced</Code>
            , <Code>market_changed</Code>, cargo or money signals, voyage start / complete, save/load. Quay price memory
            snapshots <em>before</em> the calendar increments so market &quot;trend&quot; compares yesterday&apos;s ask
            to today&apos;s tick.
          </Text>
        </Stack>
        <Stack gap={10}>
          <H2>Surfaces</H2>
          <Text>
            <strong>Header row</strong> — calendar, purse, hold/ship line; short pointer that stocks and supply sit under{" "}
            <strong>Market</strong> and moods under <strong>Tavern</strong>. <strong>Location</strong> — docked port name
            or at-sea line only (no long intel strips in the header). <strong>City split</strong> — vertical{" "}
            <strong>Market · Harbor · Influence · Tavern &amp; intel · Ledger · Routes</strong> toggles (planned:{" "}
            <strong>Scribe / Codex</strong> — personal secretary, Tiro analogue — see Planned section); main evidence
            tables and buttons.             <strong>Routes</strong> — full-window sea chart overlay (pan/zoom, click to sail); uses{" "}
            <Code>WorldMapChart</Code> (chunk manifest) when <Code>data/maps/chunk_manifest.json</Code> exists, else{" "}
            <Code>RoutesMapChart</Code>. Esc / Close chart / another tab dismisses overlay.{" "}
            <strong>Status log</strong> — read-only log for rumors, saves, encounters, provenance dumps.
          </Text>
        </Stack>
      </Grid>

      <Divider />

      <H2>Use case catalogue</H2>
      <Text tone="secondary" size="small">
        IDs are stable labels for reviews and rules; change them only if you rename the underlying feature.
      </Text>
      <Table
        headers={["ID", "State", "Goal", "Trigger / UI", "Outcome (summary)", "Primary code"]}
        rows={[
          [
            "UC-01",
            "Any",
            "Progress the world",
            "Advance day",
            "Daily simulation tick; panels refresh.",
            "`advance_day` · `_on_advance_pressed`",
          ],
          [
            "UC-02",
            "Docked",
            "Trade with provenance",
            "City → Market — three columns of goods; physical port stock on each row with grain/fish shippable cap when clerks ring-fence granaries; city supply / full stock line via log buttons.",
            "Round-robin columns; per-good line shows port tally (≤N shippable when capped), buy/sell/toll, trend, trade age, reliability, source; ? opens provenance.",
            "`get_port_market_line` · `get_port_city_supply_digest` · `list_player_market_table_rows` · `get_port_quay_max_buy_qty_docked` · `try_buy` / `try_sell`",
          ],
          [
            "UC-03",
            "Docked",
            "Fleet and slip",
            "City → Harbor — ship row + fleet actions",
            "Order new hull (immediate), used hull, fire-sale; condition and risk readouts.",
            "`list_player_harbor_ship_rows` · `try_buy_fleet_ship` · `try_player_buy_used_fleet_ship` · `try_player_fire_sale_fleet_ship`",
          ],
          [
            "UC-04",
            "Docked",
            "Relationship sheet",
            "City → Influence — metrics + temple / mint / tolls + charter clerk (institutional phase5)",
            "Official access, temple standing, quay name, food mood; offerings, mint strike, customs graft when available; when institutional_trade.phase5 is on, charter law, breach text, alliance map, live NPC civic grain ticket grid, digest → log.",
            "`get_player_city_relationship_block` · `list_player_influence_metrics` · `try_player_temple_offering` · mint / graft helpers · `institutional_phase5_player_surface_enabled` · `get_player_institutional_charter_law_block` · `get_player_institutional_breach_law_block` · `get_player_institutional_alliance_map_block` · `list_player_institutional_charter_board_rows`",
          ],
          [
            "UC-05",
            "Docked",
            "Actionable rumors",
            "City → Tavern & intel — moods card, then notice-board + rumor table + whispers + escort",
            "Moods card: granary runway/unrest, crop & war strips, dock chatter; then escort toggle and paid intel rows.",
            "`get_player_tavern_mood_block` · `list_player_tavern_rumor_rows` · `try_player_buy_intel` · `try_player_spread_*`",
          ],
          [
            "UC-06",
            "Docked",
            "Known-world ledger",
            "City → Ledger",
            "Compact summary + sea/harbor pickers + lower pane for per-good remembered prices; full grain digest optional → status log.",
            "`get_player_ledger_summary_line` · `list_player_ledger_chart_areas` · `list_player_ledger_ports_for_chart_area` · `list_player_ledger_goods_for_port` · `get_player_ledger_block` (log digest)",
          ],
          [
            "UC-07",
            "Docked (merchant)",
            "Plan and sail",
            "City → Routes — full-height map + pay refresh",
            "`get_player_route_table` drives markers; click port → `start_voyage`; pay clerks on overlay bar. Full-window overlay (`RoutesFullscreenLayer` on `Main`); `WorldMapChart` or `RoutesMapChart`.",
            "`get_player_route_table` · `start_voyage` · `try_player_buy_intel(routes)` · `_show_routes_fullscreen_overlay` · `WorldMapChart` · `RoutesMapChart` · `HarboursChartGrid` · `data/maps/chunk_manifest.json`",
          ],
          [
            "UC-08",
            "At sea",
            "Read voyage risk",
            "No city rail — main panel voyage block",
            "Storm / open-sea intel from `get_player_voyage_intel_block`.",
            "`_rebuild_trade` sea branch",
          ],
          [
            "UC-09",
            "At sea",
            "Landfall",
            "Advance until `voyage_days_remaining` hits 0",
            "Port set, ledger snapshot for that night, `voyage_completed` fires (replaces hearsay for that port when docked).",
            "`advance_day` voyage resolution · `_player_record_ledger_snapshot` · `_player_seed_opening_ledger_hearsay_if_empty`",
          ],
          [
            "UC-10",
            "Docked",
            "Escort blocks private course",
            "Routes view while `player_voyage_role` is escort",
            "Message only — finish contract.",
            "`_build_routes_panel` escort branch",
          ],
          [
            "UC-11",
            "Any",
            "Persist session",
            "Save / Load",
            "Save v42 adds ledger + market memory fields.",
            "`save_campaign` · `load_campaign`",
          ],
          [
            "UC-12",
            "Any",
            "Debug twin",
            "F12 admin window",
            "`get_admin_world_dump`",
            "Admin window in `ui/main.gd`",
          ],
          [
            "UC-13",
            "Any (async)",
            "Feed the status log",
            "`food_riot_report` · `crop_rumor_report` · `player_encounter_report` + action outcomes",
            "Prepends timestamped lines to `StatusLog`.",
            "Signals in `ui/main.gd` `_append_log`",
          ],
          [
            "UC-16",
            "Docked",
            "Read city relationship",
            "City → Influence",
            "Official access, temple standing, merchant trust analogue, food mood; charter clerk (phase5) when enabled; each row lists source, age, reliability in the table.",
            "`get_player_city_relationship_block` · `list_player_influence_metrics` · `institutional_phase5_player_surface_enabled` · institutional charter helpers",
          ],
          [
            "UC-17",
            "Docked",
            "Review known-world ledger",
            "City → Ledger",
            "Chart area → harbor → per-good remembered buy/sell/toll (per_good in save when present; grain-only legacy rows still work).",
            "`get_player_ledger_summary_line` · `get_player_ledger_block` (optional log digest) · `list_player_ledger_rows` · `list_player_ledger_chart_areas` · `list_player_ledger_goods_for_port` · `get_player_data_provenance(ledger_good)`",
          ],
          [
            "UC-18",
            "Docked",
            "Plan voyage from chart",
            "City → Routes",
            "Map markers from `get_player_route_table`; click destination → `start_voyage` (no route table).",
            "`get_player_route_table` · `start_voyage` · `RoutesMapChart`",
          ],
          [
            "UC-19",
            "Docked",
            "Buy intelligence",
            "Tavern & intel — Pay / investigate per rumor row (+ route refresh button on Routes)",
            "Crop/war investigations delegate to existing tries; routes/piracy spend coin and stamp refresh day.",
            "`try_player_buy_intel`",
          ],
          [
            "UC-20",
            "Docked",
            "Inspect data provenance",
            "Why buttons / tooltips on Market, Harbor, Ledger; route provenance from map context (no per-row ? on Routes)",
            "Opens log line from `get_player_data_provenance` (kind: `market_good` | `influence` | `ledger` | `ledger_good` | `route` | `harbor`).",
            "`get_player_data_provenance`",
          ],
        ]}
      />

      <Divider />

      <H2>Planned — not shipped</H2>
      <Callout tone="info" title="Personal scribe (Tiro)">
        <Stack gap={8}>
          <Text>
            Roman merchants and magistrates relied on household secretaries; Cicero&apos;s <strong>Tiro</strong> (slave,
            later freedman) kept correspondence and case notes. The player will have the same fiction: a{" "}
            <strong>personal scribe</strong> who writes down what you witness — dock meetings, tavern whispers you paid
            for, charter clauses, who refused to trade — and whom you query later: <em>what happened in Syracuse?</em>,{" "}
            <em>who said the grain tax would rise?</em>, <em>whom should I ask in Massalia?</em>
          </Text>
          <Text tone="secondary" size="small">
            Same design rule as the rest of the UI: the scribe&apos;s codex is <strong>not omniscient truth</strong> — only
            entries the player earned (seen, heard, paid intel, scribe present). Deep NPC social memory in the twin may
            inform what eventually gets written when you are not there, but the player reads it through the secretary,
            not a debug dump.
          </Text>
        </Stack>
      </Callout>
      <Table
        headers={["ID", "State", "Goal", "Trigger / UI (planned)", "Outcome (summary)", "Primary code (planned)"]}
        rows={[
          [
            "UC-PLAN-01",
            "Any (docked primary)",
            "Consult your scribe",
            "Planned: header affordance or city tab (e.g. Scribe / Codex) — search by person, port, date; prompts: what happened, who said what, whom to ask",
            "Returns indexed entries from player scribe log with source, age, reliability; may suggest a named NPC to visit when personhood ships",
            "`list_player_scribe_entries` · `query_player_scribe` · `append_player_scribe_entry` (TBD) · `ui/main.gd`",
          ],
        ]}
      />

      <Divider />

      <H2>UI ↔ simulation wiring</H2>
      <Text tone="secondary" size="small">
        Main subscriptions: <Code>day_advanced</Code>, <Code>voyage_started</Code>, <Code>voyage_completed</Code>,{" "}
        <Code>market_changed</Code>, <Code>cargo_changed</Code>, <Code>money_changed</Code>, save/load results, and the
        three report signals. New player-facing signals should get a canvas row and a <Code>ui/main.gd</Code> handler.
      </Text>
    </Stack>
  );
}

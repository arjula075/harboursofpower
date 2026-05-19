import { Callout, Code, Divider, H1, H2, H3, Stack, Table, Text } from "cursor/canvas";

/**
 * Roadmap: socially embedded trade (contracts, trust, alliances, sticky routes).
 * Complements harbours-implementation-plan.canvas.tsx and sim/economy work.
 */
export default function HarboursInstitutionalTradeRoadmap() {
  return (
    <Stack gap={20}>
      <Stack gap={6}>
        <H1>Institutional trade layer</H1>
        <Text tone="secondary" size="small">
          From pure margin-chasing toward relationship-driven, semi-rigid networks. Aligns NPC + player with
          contracts, trust persistence, and politics that distort economics—not flat bonuses.
        </Text>
      </Stack>

      <Callout tone="info" title="Core thesis (source text)">
        Arbitrage optimizes prices; institutions (contracts, patronage, protection, temple ties) create{" "}
        <strong>sticky corridors</strong> and <strong>path dependence</strong>. Switching networks was costly and
        dangerous—simulations should encode <strong>inertia</strong> and <strong>obligation</strong>, not only
        spot spreads.
      </Callout>

      <H2>Suggested decision weights (NPC route / supplier choice)</H2>
      <Text size="small" tone="secondary">
        Treat as design target; normalize and tune against your tick budget and existing OCEAN + convoy code.
      </Text>
      <Code>
        {`{
  "merchant_route_evaluation": {
    "expected_profit": 0.35,
    "trust_and_relationships": 0.20,
    "route_safety": 0.15,
    "political_alignment": 0.10,
    "contractual_obligations": 0.10,
    "captain_familiarity": 0.05,
    "religious_cultural_affinity": 0.03,
    "habit_and_inertia": 0.02
  }
}`}
      </Code>

      <Divider />

      <H2>Phased implementation</H2>
      <Table
        headers={["Phase", "Deliverable", "Touches (typical)", "Success signal"]}
        rows={[
          [
            "0 — Schema",
            "Shipped: root `institutional_trade` in `world_full.json` (`enabled`, `contract_types` catalogue); per-NPC `institutional_contracts` + `institutional_next_contract_id`; each row has `id`, `type`, `state`, `expires_day`, `breach_day`/`fulfilled_day`, `parties[]` (`kind` port|npc_merchant, `role`, `id`), `terms` object. Active civic grain mirrors as `grain_delivery` while both layers on. Toggle export with `institutional_trade.enabled` (NPC civic grain sim unchanged).",
            "`data/world_full.json`, `SAVE_VERSION` 43, `game_state.gd`, `tools/sim_100_days.py`, admin dump",
            "Save includes rows; admin “Institutional trade (Phase 0 schema)” lists active rows; twin metrics `npc_institutional_contract_rows`.",
          ],
          [
            "1 — Trust & inertia",
            "Shipped: sparse `npc_route_habit_01` + daily lerp toward 0 (tiny entries dropped); `npc_city_trust_01` lerps toward `merchant_repute_01`; voyage dest score adds habit + trust-offset; weighted random merchant depart + civic grain-offer dest over a partial port sample; arrival bump on docked port. Gated by `institutional_trade.enabled` (uniform random when off). `SAVE_VERSION` 44; twin `tools/sim_100_days.py`; metrics `npc_route_habit_mass` / `npc_route_habit_slots`.",
            "`autoload/game_state.gd`, `tools/sim_100_days.py`, NPC depart / arrival / grain offer",
            "Twin shows non-zero habit mass over long runs; merchants stick to familiar corridors vs pure uniform.",
          ],
          [
            "2 — Spot vs contract",
            "Shipped (NPC, institutional + civic grain): harbour-due multiplier at issuer/consignee; issuer grain wholesale buy discount while under contract qty; grain import-toll reduction at party ports; voyage score bonus toward issuer when short; depart stickiness bump toward contract dest; peer-loan max principal multiplier. `SAVE_VERSION` 45; twin `tools/sim_100_days.py`; metric `npc_institutional_lane_contracts_active`.",
            "`autoload/game_state.gd`, `tools/sim_100_days.py` (harbour dues, wholesale, tolls, voyage score, depart bias, peer loans)",
            "Merchants on active lanes face softer frictions at contract ports and stronger pull to finish the haul.",
          ],
          [
            "3 — Alliances → economics",
            "Shipped: optional `institutional_trade.phase3` (`enabled`, `bands` as ordered arrays of port ids; first band wins if a port is listed twice). Tunables clamp in code: same-band import toll multiplier on toll coins before smuggle roll; higher toll when bands differ and the trade port is at war; slightly better same-band NPC wholesale grain buy mult after Phase 2 issuer discount; voyage dest score +ally / −hostile when dest is at war across bands; escort job accept roll +p when escort home band matches convoy leader home band (player dummy traits include `home_port`). `SAVE_VERSION` 46; twin `tools/sim_100_days.py`; metrics `npc_institutional_phase3_bands`, `npc_institutional_phase3_ports_tagged`.",
            "`data/world_full.json`, `autoload/game_state.gd`, `tools/sim_100_days.py`, `tools/build_full_world.py`, war state reader",
            "Twin shows non-zero ports_tagged when bands list real ports; tolls and routes diverge modestly by band + war without breaking food stability.",
          ],
          [
            "4 — Patronage & cities as agents",
            "Shipped: optional `institutional_trade.phase4` (`enabled` + tunables). Issuer food stress (tight grain-days vs `stress_grain_days_ref`, unrest above `stress_unrest_floor`, small add when at war) scales civic grain contract daily offer probability toward `issuer_offer_p_mul_max` and advance coins toward `issuer_advance_scale_max`. Merchants at or above `loyal_house_repute_floor` repute get `loyal_offer_p_mul` on that offer draw. On fulfill, consignee still receives grain + captain bonus; issuer also gets `fulfill_issuer_wealth_per_qty` wealth per grain unit (cap in code). Each NPC merchant carries stable `merchant_house_id` (1..4096) for dynasty-style analytics. `SAVE_VERSION` 47; twin `tools/sim_100_days.py`; metrics `npc_institutional_phase4_enabled`, `npc_institutional_phase4_merchant_houses`.",
            "`data/world_full.json`, `autoload/game_state.gd`, `tools/sim_100_days.py`, civic grain offer/fulfill paths",
            "Stressed ports sign more grain contracts in the twin; fulfilled lanes leave issuer prosperity slightly higher when phase4 is on.",
          ],
          [
            "5 — Player surface",
            "Shipped: optional world_full.json institutional_trade.phase5.enabled (default on when block absent). City → Influence — charter clerk: civic grain law + breach copy, alliance map from phase3, live NPC civic grain ticket table, digest → status log. APIs: institutional_phase5_player_surface_enabled, get_player_institutional_charter_law_block, get_player_institutional_breach_law_block, get_player_institutional_alliance_map_block, list_player_institutional_charter_board_rows. Twin metric npc_institutional_phase5_surface_enabled (no extra tick). Player-signed civic grain not offered yet; breach path matches NPCs when added.",
            "`data/world_full.json`, `autoload/game_state.gd`, `ui/main.gd`, `tools/sim_100_days.py`, `tools/build_full_world.py`",
            "Influence shows alliance bands + live haul rows; digest matches clerk copy; twin reports surface flag.",
          ],
        ]}
      />

      <Divider />

      <H2>Toll / friction improvements (within institutional frame)</H2>
      <Table
        headers={["Idea", "Role"]}
        rows={[
          ["Relationship-modulated toll", "Same posted rate; effective rate from trust + alliance + graft state."],
          ["Contract toll carve-out", "Counterparty pays or exempts slice for term of contract."],
          ["Harbour priority queue", "Abstract delay cost unless contract/patronage—reduces effective trip time without magic speed."],
        ]}
      />

      <Divider />

      <H2>Clarifying questions (answer in chat or annotate repo)</H2>
      <Stack gap={10}>
        <H3>Scope &amp; audience</H3>
        <Text>
          <strong>Primary goal:</strong> deeper autonomous world, better player fantasy, or competitive fairness
          between the two?
        </Text>
        <H3>Factions</H3>
        <Text>
          Explicit <strong>Rome / Carthage / Greek cities</strong> graph in data, or emergent only from port
          attributes + war state?
        </Text>
        <H3>NPC memory budget</H3>
        <Text>
          OK to add per-merchant sparse maps (e.g. top-N ports + contract partners), or require hard caps and
          decay for performance?
        </Text>
        <H3>Contracts first vs alliances first</H3>
        <Text>
          Which ship first: <strong>bi-lateral obligations</strong> (easier to reason) or <strong>alliance-wide
          modifiers</strong> (faster visible geopolitics)?
        </Text>
        <H3>Player parity</H3>
        <Text>
          Must every NPC contract rule apply to the player day-1, or can NPCs lead by a phase?
        </Text>
      </Stack>

      <Callout tone="warning" title="Risk notes">
        <Stack gap={6}>
          <Text size="small">
            <strong>Twin drift:</strong> every new field must mirror in <Code>tools/sim_100_days.py</Code> or
            consciously stay player-only.
          </Text>
          <Text size="small">
            <strong>Deadlocks:</strong> hard obligations without liquidity escape hatches can bankrupt the whole
            merchant pool—keep breach + rookie paths.
          </Text>
        </Stack>
      </Callout>
    </Stack>
  );
}

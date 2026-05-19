import {
  Callout,
  Code,
  Divider,
  Grid,
  H1,
  H2,
  H3,
  Stack,
  Table,
  Text,
} from "cursor/canvas";

/**
 * HarboursOfPower economy rules sheet (design digest).
 * Keep in sync with autoload/game_state.gd + tools/sim_100_days.py — see .cursor/rules/update-economy-rules-canvas.mdc
 */
export default function HarboursEconomyRules() {
  return (
    <Stack gap={20}>
      <Stack gap={6}>
        <H1>HarboursOfPower — city &amp; commerce rules</H1>
        <Text tone="secondary" size="small">
          Source of truth: <Code>autoload/game_state.gd</Code> and twin <Code>tools/sim_100_days.py</Code>. Numeric
          constants live in code; this sheet describes behaviour.
        </Text>
      </Stack>

      <Callout tone="warning" title="Maintenance">
        When you change economy / city / pricing / merchant upkeep in the files listed in{" "}
        <Code>.cursor/rules/update-economy-rules-canvas.mdc</Code>, update this canvas in the same change (or
        immediately after) so the sheet stays accurate.
      </Callout>

      <Callout tone="info" title="Scope">
        Economy-facing systems: stocks, prices, prosperity, population, war, industry, slaves, food stress,
        dock commerce. Fresh campaigns (no save file) run <Code>world_full.json</Code> <Code>autonomy_warmup_days</Code>{" "}
        NPC-only daily ticks so ports and captains are already in motion when the player appears. Ports may list{" "}
        <Code>chart_area_id</Code> (see root <Code>chart_areas</Code>) for ledger navigation; ledger cells can store{" "}
        <Code>per_good</Code> buy/sell/toll snapshots. Not: combat narrative, full UI flow, or art.
      </Callout>

      <Grid columns={2} gap={20}>
        <Stack gap={12}>
          <H2>Commerce in the city</H2>
          <Text>
            <strong>Port stock</strong> is the ledger per good. Dock trades move units between port and
            captain (player or NPC). <strong>Grain and fish</strong> are civic staples: quaestors ring-fence stock so
            the quay only sells <em>surplus</em> above a rationed bite × capped days-to-harvest calendar (fish uses the
            same band when <Code>population_fish_per_day</Code> &gt; 0). Official planning mouths = max(war-stressed census
            ration, institutional baseline). Player ask skew and NPC dock buys use that tradable slice for grain/fish.
          </Text>
          <H3>Player</H3>
          <Text>
            <Code>try_buy</Code> / <Code>try_sell</Code>: stock changes; pay/receive <Code>unit × qty</Code>;
            <strong>trade fee</strong> (coins destroyed: max(1, cost÷32) buy, max(1, revenue÷40) sell);{" "}
            <Code>_bump_port_wealth</Code> (~cost÷14 buy, ~revenue÷12 sell). <strong>Marines</strong> in the market
            list are priced as <strong>arms &amp; armour</strong> (kit); daily <strong>wages</strong> for marines in
            hold are charged when berthed (same tick as officer pay), from <Code>wage_per_unit_per_day</Code> in{" "}
            <Code>goods.json</Code>.
          </Text>
          <H3>NPC wholesale</H3>
          <Text>
            Same stock. Base unit from player curve with <Code>player_counterparty: false</Code>, then
            wholesale mults (~0.765 buy / ~1.505 sell of base), regional factor, mastery, scaled by dockside{" "}
            <strong>cartel strength</strong> (many rich captains berthed tightens buy mult / inflates sell mult).
            Wealth bump as player. Lot size from <Code>risk_aversion</Code>, capped by hold space, stock, purse
            reserve (~12c after buys).
          </Text>
          <H3>Institutional contracts (Phase 0–4)</H3>
          <Text tone="secondary" size="small">
            Optional root <Code>institutional_trade</Code> in <Code>world_full.json</Code>: <Code>enabled</Code> (when
            false, NPCs keep <Code>city_grain_contract</Code> behaviour but <Code>institutional_contracts</Code> stays
            empty) and a <Code>contract_types</Code> catalogue for forward types. Each NPC carries{" "}
            <Code>institutional_contracts</Code> (array of objects) and <Code>institutional_next_contract_id</Code>.
            While civic grain contracts run, one canonical <Code>grain_delivery</Code> row mirrors issuer port, carrier
            merchant id, consignee port, <Code>expires_day</Code> (= due calendar day), and <Code>terms</Code> (grain
            qty, advance coins). Admin snapshot prints active rows; headless metrics expose{" "}
            <Code>npc_institutional_contract_rows</Code>.
          </Text>
          <Text tone="secondary" size="small">
            <strong>Adjacency grain provisioning (optional root <Code>adjacency_grain_contracts_enabled</Code>, default on):</strong>{" "}
            standing lanes between a <strong>hub</strong> (role metropole, great_city, or imperial_port) and a{" "}
            <strong>lane-adjacent spoke</strong> (breadbasket, maritime_town, or regional_capital). Each lane gets three
            deterministic chartered <Code>merchant_house_id</Code> values. After population eats and before dock wholesale,
            the spoke accrues an earmarked grain tranche (capped) from surplus above the same <strong>granary ring-fence</strong>{" "}
            as dock trades; accrual nudges up when the hub&apos;s grain runway is under ~14 days. NPCs whose <Code>home_port</Code> is the hub and whose house
            is chartered pay a slightly lower wholesale grain buy unit on the portion of the purchase drawn from that earmark.
            Metrics: <Code>adjacency_grain_contracts_enabled</Code>, <Code>npc_adjacency_grain_contract_rows</Code>,{" "}
            <Code>npc_adjacency_grain_earmark_units</Code>, <Code>npc_adjacency_grain_privileged_buy_units</Code>.
          </Text>
          <Text tone="secondary" size="small">
            <strong>Phase 1 (same toggle):</strong> merchants keep a sparse <Code>npc_route_habit_01</Code> (per-destination
            inertia, capped keys) reinforced on arrival, decaying toward zero with tiny entries pruned;{" "}
            <Code>npc_city_trust_01</Code> lerps daily toward <Code>merchant_repute_01</Code>. When enabled, NPC voyage
            destination score adds habit + trust-offset terms; &quot;random&quot; depart ports and civic grain contract
            destination draws are weighted by that score (partial port sample). Pirates stay uniform random. Twin
            metrics: <Code>npc_route_habit_mass</Code>, <Code>npc_route_habit_slots</Code>.
          </Text>
          <Text tone="secondary" size="small">
            <strong>Phase 2 (same toggle + civic grain on):</strong> treats the mirrored <Code>grain_delivery</Code> lane
            as a contract vs pure spot: NPC harbour due is reduced while berthed at <strong>issuer or consignee</strong>;
            wholesale <strong>grain buy unit</strong> is cheaper at the issuer while cargo grain is below contract qty;
            <strong>import toll</strong> on grain sales into issuer/consignee is reduced; voyage scoring adds a load
            nudge toward the issuer when short; convoy depart bias toward the contract destination is slightly stickier
            (higher cap); peer-loan principal ceiling is scaled up for debtors carrying an active lane. Metric{" "}
            <Code>npc_institutional_lane_contracts_active</Code> counts merchants with that state. Breach/fulfill
            rules unchanged from civic grain.
          </Text>
          <Text tone="secondary" size="small">
            <strong>Phase 3 (optional <Code>institutional_trade.phase3</Code>):</strong> when <Code>enabled</Code> and{" "}
            <Code>bands</Code> tag ports, NPC import <strong>toll base</strong> (per unit × qty, before smuggle/graft
            roll) scales down for same home/trade band, up when bands differ and the trade port is at war. NPC
            wholesale <strong>buy unit</strong> gets an extra same-band multiplier (after Phase 2 issuer grain
            discount). <strong>Voyage dest score</strong> adds a same-band bonus and subtracts when crossing into an
            at-war destination in another band. <strong>Escort hire</strong> accept probability gains a small same-band
            bonus vs the convoy leader. Player escort-offer dummy traits carry <Code>home_port</Code> so the same rule
            applies. Metrics: <Code>npc_institutional_phase3_bands</Code>,{" "}
            <Code>npc_institutional_phase3_ports_tagged</Code>. In the full Mediterranean chart,{" "}
            <Code>phase3.bands</Code> is four lists: Tyrrhenian/Ostia hub cluster plus Latium bread feeders; Carthage
            orbit with Tripolitanian bread coasts; Gades–Baetis–Atlantic gateway with Iberian feeders; Tyre–Sidon–
            Levant including Cyprus (<Code>kition</Code>, <Code>salamis_cyprus</Code>) with coastal grain spokes (
            <Code>acre_feed</Code>, <Code>dor_coast_bread</Code>, <Code>ptolemais_akkaron</Code>).
          </Text>
          <Text tone="secondary" size="small">
            <strong>Phase 4 (optional <Code>institutional_trade.phase4</Code>):</strong> when <Code>enabled</Code> with civic
            grain contracts on, issuer cities under <strong>food stress</strong> (short grain runway vs{" "}
            <Code>stress_grain_days_ref</Code>, unrest above <Code>stress_unrest_floor</Code>, plus a small bump while{" "}
            <Code>at_war</Code>) scale up the daily probability they offer a civic grain haul and slightly increase the
            advance paid to the carrier. Merchants whose <Code>merchant_repute_01</Code> meets{" "}
            <Code>loyal_house_repute_floor</Code> get an extra loyal-house multiplier on that offer roll. When the haul
            is delivered, the issuer gains a small <Code>fulfill_issuer_wealth_per_qty</Code> prosperity slice per grain
            unit (on top of existing captain/consignee effects). Each merchant keeps a stable{" "}
            <Code>merchant_house_id</Code> for house-level analytics. Metrics: <Code>npc_institutional_phase4_enabled</Code>,{" "}
            <Code>npc_institutional_phase4_merchant_houses</Code>.
          </Text>
          <Text tone="secondary" size="small">
            <strong>Phase 5 (optional <Code>institutional_trade.phase5</Code>):</strong> when <Code>enabled</Code> (default
            on if the block is absent) and root <Code>institutional_trade.enabled</Code>, the Godot client shows a charter
            clerk under City → Influence — civic grain law text, breach formula, alliance map from Phase 3 bands, and a
            live table of NPC <Code>city_grain_contract</Code> tickets. No extra daily tick math; twin exposes{" "}
            <Code>npc_institutional_phase5_surface_enabled</Code> for parity. Player civic grain offers are not in the
            build yet; breach math matches NPCs when they ship.
          </Text>
          <H3>Daily tick (summary)</H3>
          <Text tone="secondary" size="small">
            Reset dock commerce counters + harbour-coin bucket → information decay (war gossip + per-good rumour
            deltas) → scatter / convoy tail decay → institutional Phase 1 trust &amp; route-habit decay (when{" "}
            <Code>institutional_trade.enabled</Code>; Phase 3 alliance toll/buy/voyage/escort hooks apply when{" "}
            <Code>phase3</Code> is enabled and bands map ports) → NPC captain costs → voyage advance → production agent (farms, mines, slaves) → refresh
            wealth attractor → population eats grain/wine/fish → industry agent (peace sinks + war materiel) →
            vineyard help → NPC dock trade (bumps commerce counters; civic grain contract offers consult Phase 4 patronage when enabled) → harbour dues → officer pay + marine wages
            (per <Code>goods.json</Code> <Code>wage_per_unit_per_day</Code> on marines, × same scale as officers) →
            used hulls
            → seasoned mastery tick (long-solvent merchants) → fleet expand → depart → post-trade rumours (random per-good jitter) → cartel strength from rich
            docked captains → commerce pulse EMA from dock traffic + dues + wholesale units/coins → granary
            spoilage → bankrupt cull → food-unrest finalize → war agent (countdown + recurring bursts) →
            demographics (commerce-depressed “poor”, plague days) → merchant count sync vs pulse/wealth (drops
            lowest balance-sheet home captain per step when over quota).
          </Text>
          <H3>Calendar &amp; seasons (360-day year)</H3>
          <Text tone="secondary" size="small">
            <strong>Day-of-year</strong> <Code>1…360</Code> wraps from <Code>current_day</Code>.{" "}
            <strong>Spring</strong> 1–90, <strong>Summer</strong> 91–180, <strong>Autumn</strong> 181–270,{" "}
            <strong>Winter</strong> 271–360. <strong>Harvest peak</strong> (grain + wine): DOY{" "}
            <Code>181–240</Code> (60 days) uses a boosted multiplier so most of each farm&apos;s yearly tonnage lands
            in autumn; outside that, a small <strong>off-season trickle</strong> (<Code>~6%</Code> of the same nominal
            rate per day) keeps springs from starving before the first convoy while keeping the “lean granary between
            harvests” feel. Baseline annual mass still ties to <Code>grain_per_day × 360</Code> via harvest scaling +{" "}
            <Code>_FARM_GRAIN_MASS_MULT</Code>; an extra global <Code>_FARM_FOOD_PRODUCTION_MULT</Code> (currently{" "}
            <Code>2.0</Code>) multiplies farm <strong>grain, wine, and fish</strong> into port stocks for tuning /
            stress tests.{" "}
            <strong>Fish</strong> from farms uses a mild winter
            multiplier (~0.88). <strong>Storms</strong> at sea (player + NPC): probability multiplied in winter (~1.48)
            and autumn (~1.08) before the usual cap. <strong>Recurring wars</strong>: when peace countdown hits zero,
            burst length is rolled; war starts immediately only if DOY is in summer, else stored in{" "}
            <Code>port_war_pending_burst</Code> until the next summer day.
          </Text>
        </Stack>

        <Stack gap={12}>
          <H2>City prosperity (wealth)</H2>
          <Text>
            <Code>_port_wealth</Code> is smoothed prosperity (not coin in treasury). It lerps each day toward a{" "}
            <strong>stock-implied attractor</strong> (<Code>_WEALTH_LERP</Code> ≈ 0.14).
          </Text>
          <Text>
            Attractor = weighted sum of port stocks (grain, wine, salt, oil, pottery, fish, timber, textiles,
            metal, wire, spice, slaves) + flat base, clamped, plus{" "}
            <strong>role bonus</strong>: <Code>world_full.json</Code> <Code>port_role_wealth_bonuses</Code> keyed by
            each port&apos;s <Code>role</Code> (in <Code>_wealth_stock_target_value</Code>). Ports with role{" "}
            <Code>breadbasket</Code> also get <Code>×1.15</Code> on farm <strong>grain &amp; wine</strong> delivered
            into that port (fish unchanged). Then multiply by a{" "}
            <strong>commerce pulse</strong> factor (EMA of dock traffic + harbour dues + NPC wholesale
            volume; busy quays lift the target, quiet ones depress it). While <Code>plague_days</Code> &gt; 0,
            attractor is further scaled down (~0.93).
          </Text>
          <Text>
            <Code>initial_wealth</Code> per port seeds starting prosperity when present; high values decay
            toward the attractor until aligned.
          </Text>
          <H3>Food riots</H3>
          <Text>
            Per-port <strong>food worry</strong> (0–100) and <strong>food panic</strong> (0–100). Citizens do not see
            granary stock: <strong>worry</strong> rises while <strong>civic rationing</strong> is in effect (visible
            policy). <strong>Panic</strong> accrues only after <strong>three consecutive days</strong> where mouths are
            not fully fed from grain + preserved + summer forage (shortfall-weighted spike, stronger under war panic
            ramp). <Code>food_unrest</Code> in metrics is the composite <Code>worry + panic</Code> (0–200) for
            backward-compatible hooks (mood tiers, grain reservations, voyage scores). When fully fed, daily decay drains{" "}
            <strong>panic first</strong>, then worry; faster decay when closing grain runway (food-days) is comfortable.
            Post-war vent and riot aftermath use the same panic-first rule; riot near-miss / no-famine vents re-split the
            lowered composite. Grain riots roll only when composite is above threshold <em>and</em> the port is
            famine-eligible (starvation streak), not merely from low granary runway. Each resolved riot increments a
            per-port cumulative counter (<Code>food_riot_events</Code> in twin metrics; <Code>port_food_riot_events</Code>{" "}
            in saves) surfaced in the sim dashboard and city supply digest.
          </Text>
        </Stack>
      </Grid>

      <Divider />

      <H2>Simulation tick agents (code modules)</H2>
      <Text tone="secondary" size="small">
        Shared helpers and tick order notes: <Code>autoload/sim_tick_agents.gd</Code>. Orchestration lives in{" "}
        <Code>HarboursGameState._run_daily_population_and_npcs</Code> (Godot) and <Code>Sim._run_daily_population_and_npcs</Code>{" "}
        (Python twin).
      </Text>
      <Table
        headers={["Agent", "Responsibility"]}
        rows={[
          ["City & wealth", "Wealth snapshots/lerp, population consumption, commerce-linked attractor + plague modifier, prosperity streaks treat very low commerce+poor liquidity as “poor”."],
          [
            "Production",
            "Farms (grain/wine seasonal harvest window; fish mild winter taper; global _FARM_FOOD_PRODUCTION_MULT on farm food into port), mines, slave labour pool + attrition (same tick order as before extraction).",
          ],
          ["Industry & war materiel", "Peace industrial sinks then daily war metal/wire draw when at war."],
          ["NPC merchants", "Wholesale trade, harbour dues, cartel ring strength, dynamic home-port trader count vs commerce pulse and liquidity; seasoned mastery drift; bankruptcy rookies blend parent trade skills; trims drop lowest balance-sheet home captains first."],
          ["Information", "Rumour decay/spread, random dock gossip, war fear from adjacent warring ports."],
          [
            "War",
            "Burst countdown; recurring peace→war with summer campaign start (winter/spring/autumn peace expiry queues burst until next summer), post-war unrest vents.",
          ],
          [
            "Autonomy warmup",
            "On new game without a save, GameState runs N deferred full daily ticks (player ship not aged) from world_full.json autonomy_warmup_days so markets and voyages already cycled.",
          ],
        ]}
      />

      <Divider />

      <H2>How prices are formed</H2>
      <Text>
        Player list prices: <Code>_compute_player_buy_unit</Code> / <Code>_compute_player_sell_unit</Code>{" "}
        (base from <Code>goods.json</Code>), multiplicative layers:
      </Text>
      <Table
        headers={["Layer", "Effect"]}
        rows={[
          ["Stock skew", "Buy mult rises when stock below per-good stock_target; sell mult responds when above."],
          ["Need tier", "Food/comfort/metal/luxury: smooth reservation on grain & wine (player K and caps > NPC). Metal tier adds food-stress + war hoarding. Luxury adds wealth excess + mean outbound lane days (combined cap)."],
          ["Market mult", "~7d structural demand vs stock + flow vs farm/mine supply; clamp ~0.74–1.42."],
          ["Port bias", "world_full.json trade_price_bias per good (clamped offset)."],
          ["Rumours", "War gossip 0–1 per port (neighbour-at-war bleed-in, daily decay) + sparse per-good false deltas; combined multiplicative clamp on buy/sell (staples/strategic goods react more to war gossip)."],
          ["NPC path", "Same base with NPC false, then wholesale + regional + mastery + cartel scale on effective unit."],
        ]}
      />

      <Divider />

      <H2>Merchant running costs (player &amp; NPC)</H2>
      <Grid columns={2} gap={16}>
        <Stack gap={8}>
          <Text>
            Shared trireme path (<Code>_tick_captain_shared</Code>): <strong>crew wine</strong> drawn from hold
            on the wine cycle (no daily grain ration from hold as ship upkeep), <strong>wear</strong> at sea,{" "}
            <strong>dock repair</strong> (metal+wire from hold or coin), then{" "}
            <strong>officer pay</strong> when docked after that day&apos;s trades (<Code>_SHIP_OFFICER_PAY_DAILY</Code>{" "}
            × ships, default 1c/ship/day).
          </Text>
          <Text>
            <strong>Fleet:</strong> new hull labour uses <Code>_FLEET_NEW_SHIP_LABOR_COINS</Code> (× class{" "}
            <Code>labor_mult</Code>); nominal book value per hull is <Code>_FLEET_SHIP_NOMINAL_COINS</Code>;{" "}
            <Code>_FLEET_CARGO_PER_SHIP</Code> 24 units per ship (max 12).{" "}
            <Code>_FLEET_NEW_SHIP_BUILD_DAYS</Code> (0 in the current build) is slip delay before +1 hull;{" "}
            <Code>0</Code> means same-day delivery after materials + labour are committed. Used-hull slip market from forced (empty hold
            + thin purse) and voluntary captain listings.
          </Text>
        </Stack>
        <Stack gap={8}>
          <Text>
            <strong>Player only:</strong> harbour dues end of docked day (base + per ship + progressive purse
            slice, capped). Trade fees on buy/sell as above.
          </Text>
          <Text>
            <strong>NPC:</strong> same ship tick order as player; harbour dues from purse when docked after trade
            (same formula as player). See <strong>NPC captain agents</strong> below for bust streak, dust-sell,
            hull fire-sale, and voyage behaviour.
          </Text>
        </Stack>
      </Grid>
      <H3>Civic spend conservation (Phase 1)</H3>
      <Text>
        Officers, marines, dockworkers, and customs clerks all spend their pay in port —
        &quot;every last penny&quot;. Phase 1 of coin conservation closes the silent destruction holes by
        having each of the following NPC outflows bump the host port&apos;s prosperity at the same{" "}
        <Code>_HARBOUR_WEALTH_PER_COINS_PAID=8</Code> ratio harbour dues already use (8 coins → +1 wealth).
        Helper: <Code>_npc_civic_spend_to_port_wealth(port_id, coins)</Code>.
      </Text>
      <Table
        headers={["Outflow", "Site", "Before Phase 1", "After"]}
        rows={[
          ["Officer pay", <Code>_npc_apply_officer_pay_if_docked_after_trade</Code>, "Money lost from NPC purse, no credit anywhere.", "Host port wealth bumped by (pay // 8)."],
          ["Marine wages", "Same call (`_marine_wage_due_for_cargo`).", "Same destruction.", "Same credit (rolled into the officer-pay bump)."],
          ["Shipyard coin repair", <Code>_tick_all_npc_captain_ship_costs → _tick_captain_shared</Code>, "Coin paid for +4 ship condition vanished.", "Host port wealth bumped by (repair_cost // 8)."],
          ["Buy-side trade fee", <Code>_npc_buy_from_port</Code>, <><Code>cost / 14</Code> already bumped wealth; the per-trade buy_fee did not.</>, "Now also (buy_fee // 8) → port wealth."],
          ["Sell-side trade fee", <Code>_npc_sell_to_port</Code>, "Same gap on the sell side.", "Now also (sell_fee // 8) → port wealth."],
          ["Tolls", <>Already credited via <Code>_bump_port_for_toll_receipt(..., toll_paid / 3)</Code>.</>, "Worked.", "Unchanged."],
          ["Harbour dues", <Code>_harbour_due_port_wealth_bump</Code>, <><Code>take / 8 × busy_bonus</Code> already credited.</>, "Unchanged (this was the reference pattern)."],
        ]}
      />
      <Text>
        <strong>Sim effect (3k-tick coarse-grained full Med):</strong> Phase 1 visibly redistributes wealth
        toward the busy trade hubs — Ostia ends +2.77× initial, Solus +2.52×, Tingis +1.63× — while
        low-traffic regional capitals (Croton, Knossos) slide toward their attractor. NPC purses still trend
        down because <em>total</em> wealth is bounded by the lerp-to-attractor: bumps lift wealth above the
        attractor, the next-tick lerp claws part of it back. Genuine coin accumulation needs Phase 2.
      </Text>
      <H3>Treasury &amp; coin conservation (Phase 2 — design note)</H3>
      <Text>
        <strong>Problem.</strong> <Code>port_wealth</Code> today is a smoothed prosperity indicator (lerped
        toward an attractor each tick), not a treasury. NPC outflows bump it but the daily lerp partly undoes
        the bump, so coin doesn&apos;t truly accumulate in cities; the total monetary mass in the world
        slowly shrinks as NPCs spend.
      </Text>
      <Text>
        <strong>Proposed model.</strong> Introduce a new per-port field <Code>port_treasury_coins[pid]</Code>{" "}
        that accumulates without lerping. Every NPC ↔ port coin flow becomes a strict balance transfer:
      </Text>
      <Table
        headers={["Flow", "NPC purse", "Port treasury"]}
        rows={[
          ["NPC buys from port", "−cost − fee", "+cost + fee (full conservation)"],
          ["NPC sells to port", "+revenue − fee − toll", "−revenue + fee + toll  (port pays from treasury; if insufficient, sell is capped)"],
          ["Harbour dues", "−take", "+take"],
          ["Officer pay / marine wages", "−pay", "+pay  (officers and marines spend it locally — credited to host port)"],
          ["Shipyard coin repair", "−cost", "+cost  (paid to shipwrights and chandlers)"],
          ["Pirate loot", "transfer within `npc_agents` (already conservative)", "—"],
        ]}
      />
      <Text>
        <strong>Treasury seed and decay.</strong> Seed each port&apos;s treasury at load from{" "}
        <Code>initial_wealth × _PORT_TREASURY_SEED_MULT</Code> (proposed 4×, so a port worth 200 wealth
        starts with ~800 coins). The treasury drains slowly to civic upkeep (population × small per-mouth
        coin cost) representing wages of city workers, garrison, and maintenance — the coin re-enters the
        market through merchants who sell to the city.
      </Text>
      <Text>
        <strong>Knock-on effects to design.</strong>{" "}
        (a) <em>Sieges and sacks</em>: an existential-war loss should drain the loser&apos;s treasury into
        the winner&apos;s (or into the world-treasury for tribute).{" "}
        (b) <em>Bankruptcy rookies</em>: today they&apos;re seeded from <Code>world_treasury_coins</Code>;
        Phase 2 should seed them from the home-port treasury, making rookie regeneration a localised
        liquidity question.{" "}
        (c) <em>Trade caps in poor regions</em>: a port with empty treasury literally can&apos;t buy from
        merchants — historically realistic (Egyptian temples sat on grain surplus while interior cities
        couldn&apos;t afford imports during droughts).{" "}
        (d) <em>Commerce pulse</em>: should also read treasury depletion as a poor-liquidity signal.{" "}
        (e) <em>Player contracts</em>: civic grain contracts could be paid out of treasury instead of being
        magical coin appearance, and treasury depletion blocks new contracts.
      </Text>
      <Text>
        <strong>`port_wealth` after Phase 2.</strong> Becomes a derived indicator{" "}
        <Code>w = lerp(w, f(treasury, stock_value, commerce_pulse, plague, war), _WEALTH_LERP)</Code>;
        treasury directly drives the attractor, so a port with full treasury and good stocks gets a high
        wealth indicator naturally without ad-hoc bump factors.
      </Text>
      <Text>
        <strong>Out of scope for Phase 1.</strong> Anything that touches war / siege economics, the
        bankruptcy rookie pipeline, the commerce-pulse formula, or the player&apos;s civic-contract flow.
        Those land together in Phase 2 so the conservation invariant holds at every tick.
      </Text>

      <Divider />

      <H2>NPC captain agents</H2>
      <Text tone="secondary" size="small">
        Agent dicts live in <Code>_npc_agents</Code>; bootstrap uses each port&apos;s <Code>npc_traders</Code> in{" "}
        <Code>world_full.json</Code> (clamped 1–999 on load for parse safety). Daily sync nudges home-merchant count toward{" "}
        <Code>npc_traders</Code> + commerce pulse bonus (up to <Code>_MERCHANT_HOME_COUNT_STEP_MAX</Code> add/remove per port per day).{" "}
        After a bust streak, a rookie replaces the bankrupt only if the home harbour still shows trade (wholesale tick, pulse, or stock to haul); otherwise the slot is dropped until sync refills.
      </Text>

      <H3>Persisted fields (summary)</H3>
      <Table
        headers={["Field", "Role"]}
        rows={[
          ["id", "Integer id; missing money on load is back-filled deterministically from id."],
          ["home_port, docked_port", "Home for respawn; docked port empty string while at sea."],
          ["voyage_dest_id, voyage_days_remaining", "Neighbour lane from world graph; days from lane table."],
          ["money", "Purse clamped 0..999999."],
          ["cargo", "Per-good unit counts; starting mix random by good class (grain, wine, metal/wire, slaves, other)."],
          ["buy_mastery, sell_mastery", "Wholesale edge vs port; clamped to mastery band below."],
          ["risk_aversion", "0.08–0.92; blended with trait_neuroticism for effective wholesale lot sizing."],
          [
            "trait_openness … trait_neuroticism",
            "Five floats 0–1 (OCEAN-style); rolled on new captains, id-seeded on old saves, persisted in save v21+.",
          ],
          ["fleet_ships", "1.._FLEET_MAX_SHIPS (12); optional fleet_shipyard_* fields when a new hull is queued (build days &gt; 0); at 0 days the hull joins the same day."],
          ["ship_condition, ship_wine_counter", "Shared trireme upkeep state."],
          ["purse_bust_streak", "Consecutive end-of-day states: 0 coins and zero cargo units → increments."],
          [
            "price_memory",
            "Per-good remembered prices; scored-destination pick probability scales with conscientiousness vs openness (not a fixed 64%).",
          ],
        ]}
      />

      <H3>Captain personality (Big Five–style, gameplay)</H3>
      <Text tone="secondary" size="small">
        Keys: <Code>trait_openness</Code>, <Code>trait_conscientiousness</Code>, <Code>trait_extraversion</Code>,{" "}
        <Code>trait_agreeableness</Code>, <Code>trait_neuroticism</Code>. Not used for cartels/alliances yet—only
        individual behaviour. Coefficients live in <Code>game_state.gd</Code> / <Code>sim_100_days.py</Code>.
      </Text>
      <Table
        headers={["Trait (high end)", "Effect in sim"]}
        rows={[
          ["Openness", "More random trading-destination picks vs memory-scored routes; slightly more likely to sail."],
          ["Conscientiousness", "More memory-scored picks; in tense ports (food unrest) slightly more likely to stay docked; steadier voluntary hull trims; slightly more likely to queue new hulls when solvent."],
          ["Extraversion", "More second/third wholesale passes per dock day (busier quay)."],
          ["Agreeableness", "Mild wholesale tilt vs the port (small buy/sell multipliers from neutral)—cooperative pricing, not faction diplomacy."],
          ["Neuroticism", "Gentle blend into lot-size caution with risk_aversion (capped); modest dust-sell purse bump; voyage scores down-weight high-unrest destinations; anxious captains trim voluntary hulls more; in unrestful ports more likely to depart (flee)."],
        ]}
      />

      <H3>Trade skills (new captains)</H3>
      <Text>
        <Code>_roll_npc_trade_skills</Code>: default uniform rolls for buy and sell in ~0.84–1.12, then clamped to{" "}
        <Code>_NPC_MASTER_MIN</Code>–<Code>_NPC_MASTER_MAX</Code>. Weighted rerolls skew a minority toward weak
        pairs, buy-heavy/sell-light, sell-heavy/buy-light, or strong both—see code for exact probability bins.
        Captains who stay solvent with cargo, coin, extra hulls, or an active voyage accumulate{" "}
        <Code>merchant_season_ticks</Code>; every <Code>_NPC_SEASON_MASTERY_DAYS</Code> the lower mastery stat gains{" "}
        <Code>_NPC_SEASON_MASTERY_BUMP</Code> (rich-get-richer on wholesale edge, slow vs a career).
        Legacy saves with <Code>merchant_acumen</Code> split into both masteries; missing skills derive from id via{" "}
        <Code>_npc_trade_skills_from_seed</Code> (deterministic sine/cosine mix).
      </Text>

      <H3>Constants (sync sim)</H3>
      <Table
        headers={["Symbol", "Typical value", "Use"]}
        rows={[
          ["_NPC_START_MONEY_MIN / _MAX", "78 / 295", "Rookie starting purse (random or id-seeded default)."],
          ["_NPC_MASTER_MIN / _MAX", "0.74 / 1.24", "Clamp for buy_mastery and sell_mastery."],
          ["_NPC_PORT_BUY_MULT / _NPC_PORT_SELL_MULT", "0.765 / 1.505", "Wholesale vs player curve (tuned for NPC liquidity)."],
          ["_NPC_PURSE_RESERVE", "11", "Wholesale buys shrink until fee+reserve satisfied."],
          ["_NPC_RISK_AVERSE_MAX_LOT", "5", "When effective risk (risk_aversion + neuroticism blend) = 1, random lot uses 1..min(5, feasible cap)."],
          ["_NPC_BUST_EMPTY_STREAK_DAYS", "9", "End-of-day broke + empty hold streak → replace with _new_npc_agent (heir rookies blend parent buy/sell mastery into fresh roll)."],
          ["_NPC_SEASON_MASTERY_DAYS / _BUMP", "75 / 0.005", "Per merchant: consecutive solvent trading days (purse, cargo, multi-hull, or at sea) then +bump on the lower of buy_mastery / sell_mastery (clamped)."],
          ["_NPC_DOCK_DUST_PURSE", "28", "Base dust floor; neuroticism adds up to ~+9c effective minimum purse before dust loop stops."],
          ["_NPC_DOCK_DUST_MAX_UNITS", "8", "Max single-dock-pass dust units sold."],
          ["_NPC_DEPART_STAY_GATE", "0.45", "Base stay gate; per-captain effective gate from traits + local food unrest (see code)."],
          ["_MERCHANT_HOME_COUNT_STEP_MAX", "1", "Per home port per day: at most one trader add/remove toward pulse/wealth target."],
        ]}
      />

      <H3>Bankruptcy and liquidity</H3>
      <Text>
        After trades and officer pay: <strong>bust</strong> only counts when purse is exactly 0 and total cargo
        units are 0. Streak increments daily; at <Code>_NPC_BUST_EMPTY_STREAK_DAYS</Code> the row is replaced by a
        fresh rookie at <Code>home_port</Code> with trade skills rolled as a blend (~42% new roll, ~58% bankrupt
        captain&apos;s buy/sell masteries). While docked, thin purse triggers staged unloading (chunk sells),
        optional forced hull fire-sale when multi-ship and empty hold, then <Code>_npc_liquidate_one_unit_if_dust_docked</Code>{" "}
        (up to <Code>_NPC_DOCK_DUST_MAX_UNITS</Code> single-unit sells if still under trait-adjusted dust purse floor).
        Voluntary hull listings use risk, fleet size, and personality (see Used hull listings).
      </Text>

      <H3>Voyages</H3>
      <Text>
        When docked with no days remaining, if random passes the captain&apos;s effective stay gate, pick any other
        port (lane-valid voyage plan); with trait-scaled probability use a memory-scored destination (top few by{" "}
        <Code>_npc_voyage_dest_score</Code>), else uniform random port. Voyage scores penalize high-unrest
        destinations for neurotic captains. Advance consumes remaining days; shared ship costs run at tick start with
        at-sea vs docked repair flags aligned to voyage state.
      </Text>
      <Text>
        <strong>Two graphs:</strong> full-mesh <Code>lanes</Code> in <Code>world_full.json</Code> drives the{" "}
        <strong>player</strong> <Code>_voyage_plan</Code> (shortest coastal days + bold-run shortcut). When{" "}
        <Code>npc_lanes</Code> is present (see <Code>data/world_full.json</Code> from{" "}
        <Code>tools/build_full_world.py</Code>), <strong>NPC merchants and convoys</strong> use that sparse graph for
        coastal shortest days and disconnected-day fallback max-hop; luxury far-trade markup still uses mean outbound
        days on the <strong>full</strong> neighbor list so pricing reflects economic reach, not NPC routing shortcuts.
      </Text>

      <H3>Coarse-graining knob (twin only)</H3>
      <Text>
        Both <Code>tools/sim_100_days.py</Code> and <Code>tools/sim_stream.py</Code> accept{" "}
        <Code>--npc-scale K</Code> (0.01..4.0) and <Code>--npc-mass M</Code> (0.25..12.0). At load time{" "}
        <Code>_apply_npc_density_scale</Code> rescales every port&apos;s <Code>npc_traders</Code> count so
        that <strong>both</strong> the bootstrap spawn and the per-tick home-count syncer target K·base
        merchants. Each surviving NPC is given <Code>fleet_ships = max(1, round(M))</Code> (capped at{" "}
        <Code>_FLEET_MAX_SHIPS=12</Code>) and starting purse × M. If <Code>--npc-mass</Code> is omitted it
        defaults to <Code>1/K</Code> so total carrying-capacity stays roughly constant.{" "}
        <strong>Speed:</strong> on the 75-port world{" "}
        <Code>0.25 / 4</Code> ≈ 9× speedup, <Code>0.1 / 10</Code> ≈ 30× speedup. Trade-offs: pirate
        encounter rolls scale with agent count, so coarse runs see proportionally fewer raids; trade routes
        become more concentrated (fewer captains making decisions). Use for &quot;does the world work&quot;
        sanity, fall back to <Code>--npc-scale 1.0</Code> for ground truth. The Godot game state is
        unaffected.
      </Text>

      <H3>Commerce side effects</H3>
      <Text>
        Dock wholesale updates port commerce tick counters and bumps <Code>commerce_pulse</Code> inputs; rich
        docked captains feed <strong>cartel strength</strong>. Same-day harbour due is taken from the NPC purse after
        trades using the same progressive schedule as the player (<Code>_harbour_due_for_captain</Code>).
      </Text>

      <Divider />

      <H2>Population &amp; demographics</H2>
      <Text>
        Each port: <Code>population_grain_per_day</Code> in <Code>data/world_full.json</Code> seeds starting mouths
        (clamped to [<Code>_POP_GRAIN_FLOOR</Code>=4, 120]) and initial <Code>port_population_grain_baseline</Code>.
        That baseline is <strong>not fixed</strong>: it drifts up when the city stays near-nominal health for
        <Code>_POP_BASELINE_RISE_DAYS=110</Code> days, and drifts down (min by port <Code>role</Code>) after
        <Code>_POP_BASELINE_FALL_DAYS=100</Code> days of deep collapse. Cap is recomputed from baseline,
        then clamped by the <em>institutional 2x cap</em> (see H3 below):{" "}
        <Code>min(120, max(min(baseline + 22, ceil(baseline × 1.48), initial × _POP_BASELINE_CAP_MULT=2.0), pop))</Code>.
        Wine want = wine base +
        prosperity-scaled extra; optional fish from stock. Output scale = clampf(current mouths ÷ baseline,
        <Code>_POP_OUTPUT_SCALE_MIN=0.72</Code>, <Code>_POP_OUTPUT_SCALE_MAX=1.28</Code>) → farm/mine shipment
        into port (with slave mult). Plague (rare) can still cost mouths.
      </Text>
      <H3>Institutional baseline drift &amp; existential war</H3>
      <Text>
        <strong>Rise:</strong> if population ≥ <Code>ceil(baseline × _POP_BASELINE_RISE_FRAC=0.88)</Code>,{" "}
        <Code>food_days ≥ 1.85</Code>, and unrest &lt; 96 for <Code>_POP_BASELINE_RISE_DAYS=110</Code> consecutive
        days → <Code>baseline += 1</Code> (cap 120), grain cap recomputed. Lets a small port &quot;graduate&quot;
        into a larger regional centre over years of peace and trade.
      </Text>
      <Text>
        <strong>Fall (gradual):</strong> if population ≤ <Code>floor(baseline × _POP_BASELINE_FALL_FRAC=0.58)</Code>{" "}
        and (unrest &gt; 112 or ≥6 consecutive zero-eat days) for <Code>_POP_BASELINE_FALL_DAYS=100</Code> →{" "}
        <Code>baseline -= 1</Code>, never below a role floor (metropole / great_city 7; imperial_port 6;
        breadbasket / regional_capital 5; else <Code>_POP_GRAIN_FLOOR</Code>). Metropolises can shrink after
        generations of crisis without a single-day wipe.
      </Text>
      <Text>
        <strong>Existential campaign (e.g. Third Punic cadence):</strong> optional per-port{" "}
        <Code>population_existential_war_burst_days</Code> in <Code>world_full.json</Code> (default omit = off).
        When the port is at war and this war&apos;s initial burst length ≥ that threshold, the famine
        streak needs only <Code>max(8, ceil(26/2))</Code> harsh days (before per-port jitter) before −1 mouth — faster collapse for
        long sieges. Short routine wars (burst below threshold) use the normal bar (<Code>_POP_FAMINE_STREAK_TO_LOSS=26</Code> ±5 via <Code>_POP_FAMINE_LOSS_JITTER</Code>).
      </Text>
      <Text>
        <strong>Data note:</strong> Tyrrhenian twin seeds Carthage (<Code>metropole</Code>) with higher{" "}
        <Code>population_grain_per_day</Code> than Ostia (imperial port / Rome harbour) for the mid-Republic
        snapshot where the Punic capital still outweighs Latium in urban mass; tune in <Code>world_full.json</Code>.
      </Text>
      <H3>Institutional 2× cap, Egypt dampener &amp; metropole inertia</H3>
      <Text>
        Three coupled mechanics keep demographic growth bounded by classical-period institutional capacity
        (no city should quietly double 4× over a few decades the way Nile breadbaskets were trending in the
        unrestricted twin). All three live in <Code>autoload/game_state.gd</Code> with a mirror in{" "}
        <Code>tools/sim_100_days.py</Code>.
      </Text>
      <Table
        headers={["Mechanic", "Constants", "What it does"]}
        rows={[
          [
            "Institutional 2× cap",
            <><Code>_POP_BASELINE_CAP_MULT=2.0</Code>, <Code>_POP_MIGRATION_PULL_AT_CAP=1</Code></>,
            <>The original founding cohort (<Code>port_population_grain_baseline_initial</Code>) is captured at
              load. Baseline drift up is blocked above <Code>initial × 2</Code>, and the population cap itself
              is clamped to that ceiling so the prosperity-streak path can't sneak past it either. Once pop
              reaches the cap, the migration-pull bonus falls to <Code>1</Code> (not 0) — a city at peak can
              still occasionally absorb a wave but can't keep accelerating. Future trigger hooks (war victory,
              mint commissioning, imperial reassignment) will raise this cap; for now there is no in-game
              unlock, so 2× is the institutional ceiling.</>,
          ],
          [
            "Egypt regional migration dampener",
            <><Code>_POP_MIGRATION_PULL_BY_AREA["egypt_cyrenaica"]=2</Code> (default 4)</>,
            <>The Nile delta produced grain but historically didn't absorb large foreign-born migration —
              population stayed concentrated in the Nile valley, with the Mediterranean coast as a Greek/Roman
              foreign quarter. Ports whose <Code>chart_area_id</Code> matches an entry in{" "}
              <Code>_POP_MIGRATION_PULL_BY_AREA</Code> use that override instead of the global{" "}
              <Code>_POP_MIGRATION_PULL=4</Code>. Egyptian breadbaskets therefore grow at half the migration
              speed of equally-fed Sicilian ones. <strong>Capital gravity:</strong> after the area override,{" "}
              <Code>metropole</Code> adds <Code>+_POP_MIGRATION_PULL_METROPOLE=6</Code>,{" "}
              <Code>great_city +3</Code>, <Code>imperial_port +2</Code> so mean metropole size separates from the all-city mean.</>,
          ],
          [
            "Prosperity timing jitter",
            <><Code>_POP_PROSPERITY_STREAK_JITTER=13</Code>, <Code>_POP_PROSPERITY_RESET_JITTER=9</Code>, <Code>_POP_FAMINE_LOSS_JITTER=11</Code></>,
            <>Days needed for a +1 mouth and the post-gain streak reset vary per port (deterministic string mix) so 75 ports rarely fire on the same calendar day — flattens the sim-stream &quot;mean city size&quot; sawtooth without changing long-run growth rates.</>,
          ],
          [
            "Metropolitan inertia",
            <><Code>_POP_BASELINE_RISE_DAYS_BIG_INERTIA=55</Code>, <Code>_POP_BIG_CITY_ROLES = {"{"}metropole, great_city, imperial_port{"}"}</Code></>,
            <>If a port&apos;s role is in <Code>_POP_BIG_CITY_ROLES</Code> <em>and</em> its current baseline is
              below its initial cohort, the rise-momentum threshold halves (110 → 55 days). Classical
              capitals (Carthage, Athens, Tyre, Gades) historically rebuilt quickly after sieges because of
              patronage, temple workforces, garrison rotation, and aqueducts that scaled with the city plan
              rather than the current census.</>,
          ],
        ]}
      />
      <Text>
        <strong>Effect in the 75-port twin (long-run coarse-grained twin):</strong> Egypt was previously the
        single dominant grower (Naucratis ≈ 4.5× initial). Post-cap it lands at 1.6–2.0× — exactly the
        institutional ceiling. Cap violations across the whole map: 0. The metropolitan inertia bonus only
        fires when a metropole has food_days ≥ 1.85 and unrest &lt; 96 (the baseline-rise prerequisites), so
        in food-deficit regimes it&apos;s a no-op; on the full chart it mainly appears once capitals clear those thresholds after recovery.
      </Text>
      <H3>Farm gradient (full Mediterranean world)</H3>
      <Text>
        <Code>data/world_full.json</Code> tiers grain farms by region. The Nile delta leads but no longer
        dominates: Egypt&apos;s Memphis &amp; Naucratis hinterlands produce <strong>30 grain/day</strong>,
        Alexandria <strong>26</strong>, while the secondary breadbasket bracket (Sicily — Akragas, Catane,
        Gela, Messana, Panormus; Cyrenaica — Cyrene; Africa — Hippo; Pontus — Chersonesos, Olbia Pontic)
        produces <strong>18 grain/day</strong> (was 12 — bumped to stop everyone outside the Nile from
        slowly depopulating). All other ports stay at their per-port base. Maintained by{" "}
        <Code>FARM_GRAIN_BUMPS</Code> in <Code>tools/build_full_world.py</Code>; regenerate after edits.
      </Text>
      <H3>Resilience layer (run order: ration → grain bite → preserved-food backup → forage)</H3>
      <Text>
        Three iron-age survival mechanisms feed into the demographics tick. The famine streak now counts
        days against <strong><Code>eaten_eff = grain + preserved + forage</Code></strong>, not just grain
        eaten from the granary. Cities die-hard through bad seasons instead of collapsing every campaign.
        Source of truth: <Code>_run_daily_population_and_npcs</Code> in <Code>autoload/game_state.gd</Code>
        (mirror in <Code>tools/sim_100_days.py</Code>).
      </Text>
      <Table
        headers={["Layer", "Trigger / window", "Effect", "Cost / limits"]}
        rows={[
          [
            "A. Civic grain rationing",
            <>Auto-on when <Code>food_days &lt; _RATION_TRIGGER_FOOD_DAYS=10.0</Code>; auto-off when <Code>food_days &gt; _RATION_END_FOOD_DAYS=22.0</Code> or after <Code>_RATION_MAX_DAYS=150</Code>.</>,
            <>Per-day grain bite reduced to <Code>max(_RATION_BITE_MIN=2, round(eat × _RATION_BITE_FRAC=0.62))</Code>. Granary stretches ~40%. Demographics still see partial-ration days unless preserved/forage covers full need.</>,
            <>Adds <Code>_FOOD_UNREST_WORRY_RATIONING_DAILY=4</Code> worry/day while active. Finalize uses <Code>fed_stress</Code> (full ration OR rationing + planned bite delivered) for starvation streak / panic decay; grain riots still need <Code>bio_fed</Code> false with streak.</>,
          ],
          [
            "B. Summer foraging",
            <>DOY ∈ [<Code>_FORAGE_SUMMER_START_DOY=100</Code>, <Code>_FORAGE_SUMMER_END_DOY=235</Code>]; half-sine bell with peak <Code>_FORAGE_SUMMER_PEAK_MOUTHS=4.0</Code> mouths/day.</>,
            <>Virtual food (berries, figs, wild greens, shore fish) added to <Code>eaten_eff</Code> for the demographics check only. Doesn't drain any port stock.</>,
            "Off entirely DOY 1–99 and 236–360. Larger cities only partially shielded since 4 mouths/day cover a fraction of baseline demand.",
          ],
          [
            "D. Preserved-foods reserve",
            <>Mouth-day float buffer per port; cap = <Code>max(_PRESERVED_FOOD_CAP_MIN=24, baseline × _PRESERVED_FOOD_CAP_MULT=8)</Code>. Initial fill at <Code>_PRESERVED_FOOD_INITIAL_FRAC=0.5</Code> of cap.</>,
            <>Auto-drawn to cover any grain shortfall (<Code>preserved_used = min(shortfall, floor(reserve))</Code>). Refills <Code>_PRESERVED_FOOD_FILL_PER_DAY=0.4</Code> mouth-days/day while <Code>food_days ≥ _PRESERVED_FOOD_FILL_FOODDAYS_MIN=45.0</Code>.</>,
            "Won't fill during rationing or any tight runway (food_days &lt; 45). Refilling a full pantry from empty takes ~3–5 in-game months of abundance.",
          ],
        ]}
      />
      <H3>Daily demographic tick (per port)</H3>
      <Text>
        Tracks <strong>famine</strong> and <strong>prosperity</strong> streaks against meal-based signals
        (not granary runway). Designed so cities <em>breathe</em> across seasons rather than collapsing
        permanently to the floor on the first bad campaign.
      </Text>
      <Table
        headers={["Side", "Trigger (per day)", "Streak / threshold", "Result"]}
        rows={[
          [
            "Famine — harsh day",
            <>≥9 consecutive zero-<Code>eaten_eff</Code> days (was 6), OR unrest ≥ 118 (was 92).</>,
            <>Streak += 1. After <Code>_POP_FAMINE_STREAK_TO_LOSS=26</Code> harsh days (±5 via <Code>_POP_FAMINE_LOSS_JITTER=11</Code> per port, deterministic mix — spreads −1 mouths across the map) or <Code>~13</Code> during an <strong>existential war</strong> (half base + same jitter): <Code>grain_mouths -= 1</Code>, streak resets to <Code>_POP_FAMINE_STREAK_RESET=8</Code>.</>,
            "Mouth lost (down to floor 4)",
          ],
          [
            "Famine — calm day",
            <><Code>eaten_eff</Code> ≥ <Code>eat_need</Code> for ≥2 consecutive days AND unrest &lt; 38.</>,
            "Streak → 0.",
            "Halts loss cadence.",
          ],
          [
            "Famine — neither",
            "Any partial-ration / mixed day (incl. rationed days where grain+preserved+forage falls between 0 and eat_need).",
            "Streak -= 1 (slow decay; not reset).",
            "Forgiving — short shortages don't carry forward.",
          ],
          [
            "Prosperity — wealthy day",
            <>Wealth &gt; attractor × <Code>_POP_PROSPERITY_WEALTH_FACTOR=1.00</Code> (was 1.04) AND food_days ≥ role-scaled minimum (<Code>_POP_PROSPERITY_FOOD_DAYS_MIN=2.4</Code> default; <Code>2.2</Code> great_city / imperial_port; <Code>2.05</Code> metropole) AND unrest &lt; <Code>_POP_PROSPERITY_UNREST_MAX=75</Code> (was 65). Relaxed so coastal cities have a realistic shot at growing between war pulses and pirate-raid stretches.</>,
            <>Base streak += 1, plus migration pull when <Code>pop &lt; baseline</Code>: <Code>inc = 1 + floor(gap_frac × pull)</Code>. Pull starts from <Code>_POP_MIGRATION_PULL_BY_AREA</Code> if set (Egypt = 2) else <Code>_POP_MIGRATION_PULL=4</Code>, then adds <Code>+6</Code> metropole / <Code>+3</Code> great_city / <Code>+2</Code> imperial_port so capitals separate from the mean. At institutional 2× cap, pull floors to <Code>_POP_MIGRATION_PULL_AT_CAP=1</Code>. Gain fires after <Code>_POP_PROSPERITY_STREAK_TO_GAIN=30</Code> ±6 days per port (<Code>_POP_PROSPERITY_STREAK_JITTER=13</Code>, deterministic) so 75 ports rarely +1 on the same tick; reset after gain jitters ±4 around <Code>_POP_PROSPERITY_STREAK_RESET=14</Code> (<Code>_POP_PROSPERITY_RESET_JITTER=9</Code>). 35% chance +1 wine base.</>,
            <>Mouth gained (up to cap). Big cities at the floor pull 2–3× the natural growth rate (second sons, rural surplus, refugees). Once pop ≥ baseline the bonus is 0 and growth slows to +1/day; once pop ≥ <Code>initial × 2</Code> the pull drops to 1 so the institutional ceiling is a soft brake, not a hard wall.</>,
          ],
          [
            "Prosperity — poor day",
            <>Wealth &lt; attractor × 0.92 (was 1.02) OR food_days &lt; 1.5 (was 2.1) OR unrest &gt; <Code>_POP_PROSPERITY_POOR_UNREST_EXCEEDS=118</Code> (was 88) OR (<Code>commerce_pulse</Code> &lt; <Code>_COMMERCE_POOR_PULSE=0.10</Code> AND wealth &lt; attractor × 0.95).</>,
            <>Streak -= <Code>_POP_PROSPERITY_POOR_DECAY=4</Code> (was a hard reset to 0).</>,
            "Gradual erosion — single bad day no longer wipes weeks of recovery.",
          ],
          [
            "Prosperity — neither",
            "Default day (most of the year).",
            "Streak -= 1.",
            "Slow drift toward zero unless wealthy days outpace.",
          ],
        ]}
      />
      <Text>
        <strong>Net effect:</strong> city size is driven by simulation (migration pull, resilience, baseline
        drift) on top of world seeds — metropoles are not immutable. Use <Code>population_existential_war_burst_days</Code>{" "}
        on a home port to model sack-style wars; leave it unset elsewhere so collapse stays gradual.
        Sync: <Code>_tick_population_demographics</Code> in <Code>autoload/game_state.gd</Code> and{" "}
        <Code>tools/sim_100_days.py</Code>.
      </Text>

      <Divider />

      <H2>Grain spoilage</H2>
      <Text>
        After commerce: fraction of granary lost to rot (capped, min-stock rule). Feeds structural demand used
        in market-pressure pricing and tightens food runway.
      </Text>

      <Divider />

      <H2>Peace industry &amp; war materiel</H2>
      <Text>
        <Code>industrial_*_per_day</Code> in world_full.json: daily draw of metal, wire, timber, textiles from port
        stock (each capped). When at war, additional metal/wire materiel draw (scaled + stock skim, daily
        hard cap). War also scales farm output to port and raises population grain ration demand.
      </Text>

      <Divider />

      <H2>War &amp; peace (food + prices)</H2>
      <Table
        headers={["Aspect", "Rule (summary)"]}
        rows={[
          [
            "Campaign",
            "war_days tick down; recurring ports draw a long peace interval (380–900d) then an 18–38d burst unless war_recurring false.",
          ],
          ["Farms to port", "Wartime farm output mult &lt; 1 to port stock (twin default 0.80; peace 1.0)."],
          [
            "Rations",
            <>
              While at war, population grain bites scale by <Code>_WAR_GRAIN_RATION_MULT</Code> (default 1.10).
            </>,
          ],
          ["Riot threshold", "Higher early in burst, eases toward peacetime threshold over ramp days; peace applies unrest vent + grace riot threshold bonus."],
          ["Metal pricing", "War demand stress on metal-tier reservation; materiel consumes stock."],
        ]}
      />

      <Divider />

      <H2>Slaves &amp; labor</H2>
      <Text>
        Farm+mine labor demand vs port <Code>slaves</Code> stock → output multiplier (floor). Attrition removes
        slaves from stock; war end can inject captives into market. Shortfall cuts farm/mine throughput into
        the port.
      </Text>

      <Divider />

      <H2>Vineyard help (wine)</H2>
      <Text>
        When local wine stock empty/tight, same-day bump to wine shipped from farms to that port (tiered
        amounts, capped per port across farms).
      </Text>

      <Divider />

      <H2>Used hull listings</H2>
      <Text>
        <strong>Forced:</strong> if officer purse is short after unloading what they can at bid, empty hold, and
        fleet &gt; 1 (cargo still fits after dropping one hull), they must fire-sale a hull each pass until solvent
        or single-ship. Same rule when dock-dust liquidity is thin: empty hold + purse below officer floor or dust
        floor → hull sale (no random gate).
        <strong>Voluntary:</strong> when daybooks are covered, some captains still list a hull (large fleet,
        timid risk profile, or flush purse) — same payout + slip ask. Docked NPC/PC buy with probability/coin;
        merges hull condition.
      </Text>

      <Divider />

      <H2>Luxury &amp; far trade (pricing)</H2>
      <Text>
        Luxury-tier goods multiply price by a blend of prosperity above stock attractor and mean outbound lane
        length; separate luxury and far caps plus combined cap (constants in game_state / sim).
      </Text>

      <Text tone="secondary" size="small">
        Roadmap and delivery status: <strong>harbours-implementation-plan.canvas.tsx</strong> (same canvases folder).
      </Text>

      <Text tone="tertiary" size="small">
        Open beside chat as a Cursor Canvas. This file is documentation only.
      </Text>
    </Stack>
  );
}

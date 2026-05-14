# Player captain — how you got your first ship

Short opening-story hooks for character creation or intro copy. Each is a **suggestion**, not canon; mix cultures, ports, and names when you wire them in.

---

## Required hooks (from design brief)

### `gamble_win`
**Won in a gamble**  
The dice—or the knucklebones—favoured you once. A merchant who could not cover his losses signed the bill of sale before witnesses. Half the harbour still insists the throw was crooked; the other half says luck owes no one an explanation. Either way, the hull is yours, and the creditors are watching.

### `inheritance_relative`
**Wealthy uncle or other relative**  
A kinsman you hardly knew—uncle, great-uncle, or a childless cousin twice removed—died across the sea. The letter named you heir to a small coasting vessel and a modest purse, after the priests and the tax-farmer took their shares. Some relatives smile; others are counting days until you founder.

---

## Additional hooks

### `bankrupt_merchant_sale`
**Bought from a busted house**  
When a counting-house failed, the magistrates ordered the assets sold. You were not the richest bidder, but you were the quickest with silver and a clean enough name. The ship came with half a hold of odd lots and a crew who remember another captain’s table.

### `debt_settlement_hull`
**Taken in settlement of a debt**  
A man owed you—or owed someone who sold you the paper—more than he could pay in grain or coin. He offered the hull instead. The law may call it lawful satisfaction; his partners call it theft with a seal. You call it your first command.

### `mentor_bequest`
**Old captain’s favour**  
You sailed years as mate or purser under a captain who had no children of his own. When fever took him, his will left you the ship if you would bury him ashore and pay his small debts. You did both. The widow still sends you olives at New Year.

### `prize_or_salvage`
**Salvage, or a thin story of salvage**  
She was found awash, mast gone, no manifest anyone will swear to. You filed the claim, paid the harbour fee, and fitted a new yard. What happened to her crew is spoken of in different ways in different taverns.

### `navy_surplus_or_demob`
**Surplus oar-bench or supply hull**  
After the last levy stood down, the arsenal sold off auxiliaries: slow, honest tubs that carried biscuit and cordage more often than glory. You bought one at auction with pooled savings and a guarantor’s mark. She will never be fast, but she is yours.

### `charter_to_owner`
**Charter that became title**  
You signed on to work a coastal run for a share. The owner sickened; his heirs quarrelled; someone needed to keep the contracts and the crew fed. Documents were drawn; witnesses summoned; you walked away with ink on your hands and a name on the stern.

### `smuggler_partner_vanished`
**Partner gone, hull left behind**  
There was a man who knew coves and signal fires. One moonless week he did not come back. The slip rent was due; the cargo was gone or too hot to hold. You paid the arrears, renamed her, and sail as if you had always owned her—which is almost true.

### `regatta_or_wager_race`
**Staked on a race**  
Not dice this time: a course round the headland, first home with sail and honour. The stake was a patched merchantman and a year’s bragging rights. You crossed a length ahead in a gust no one had forecast. Your opponent’s friends say the wind was bought; you say it was earned.

### `collateral_default`
**Collateral when the borrower fled**  
You held paper against a ship as security. The borrower weighed anchor for a port that does not extradite. The magistrate ruled the hull forfeit after due notice. You did not cheer in court; you signed quietly and hired a new steersman before rumour outran you.

---

## Implementation notes

- **IDs** in backticks are stable keys if you later load this from JSON or GDScript.
- **Tone**: Mediterranean-adjacent merchant age; adjust deities, titles, and legal words to match your world data (`data/world_full.json`) cultures.
- **Gameplay**: These are flavour only unless you add fields like `player_ship_origin_id` and tie small modifiers (reputation, starting debt, crew mood) to specific origins.

# P1 — INTAKE AND PLAN  (Chat A, paste as the first message)

You are building a Commander (EDH) deck from a fixed physical collection under a
stated construction restriction. You are solving a constraint-satisfaction
problem, not writing about one. No praise, no preamble, no restating this brief.

The project contains three data files (`MTG_collection_annotated.csv`,
`scryfall_universe.csv`, `MagicCompRules_20260819.txt`) and these scripts:
`config.py`, `scan.py`, `validate_deck.py`, `prep.py`, `digest.py`,
`check_restriction.py`, `deliver.py`, `baseline.py`, `compare.py`,
`restrictions.json`. The card pool does not exist yet; `prep.py` builds it for
this commander and restriction. Code execution is required. Never paste a
script's source into the conversation.

---

## STEP 1 — ASK, THEN STOP

Ask exactly these four questions in one message and stop. Do not guess an
answer, do not begin work, do not run anything yet.

1. **Which commander?** Exact name if you have it; I will resolve it against the
   card file and quote back the printed text before building on it.
2. **What is the restriction on the 99?** State it as a rule a card either
   satisfies or fails. If it is already a key in `restrictions.json`, name it.
3. **Who are you playing against?** One of: *casual precons*, *upgraded decks,
   no infinite combos*, *high-power, combo expected*. This selects the opponent
   model in 2.4; say so if you want different numbers.
4. **Anything off the table?** Cards, archetypes or a price ceiling you do not
   want, and whether land destruction / stax / infinite combos are socially
   acceptable at your table.

---

## STEP 2 — ON RECEIVING THE ANSWERS

### 2.1 Preflight and pool, in one block

```bash
cp /mnt/project/config.py /mnt/project/scan.py /mnt/project/validate_deck.py \
   /mnt/project/prep.py /mnt/project/digest.py /mnt/project/check_restriction.py \
   /mnt/project/deliver.py /mnt/project/baseline.py /mnt/project/compare.py \
   /mnt/project/restrictions.json .
ls -la
python prep.py --commander "<COMMANDER>" --restriction "<KEY>"
```

Paste `prep.py`'s stdout in full. It is the only bulk data you will paste this
turn: the commander's printed text **from the file**, the three-filter
derivation, function coverage counts over the whole pool, card-type counts, the
hybrid-type and multi-part notices, high-impact cards, colour sources read from
oracle text, and the data fingerprint.

**If the restriction is not a key in `restrictions.json`:** add one entry to
that file — `statement`, plus whichever of `allow_types`, `forbid_types`,
`always_legal`, `exempt_types`, `max_cmc`, `min_cmc`, `max_usd`, `forbid_text`,
`require_text`, `require_subtype_for_type`, `token_creature_subtype` expresses
it — then re-run. That file is the single declaration the pool filter and both
deck checks read, which is why it is edited there and nowhere else. If the
restriction cannot be expressed as a predicate over a card row, say so and stop:
a restriction you cannot filter on is a restriction you cannot check.

**If any unaccounted file is in the working directory** — especially one that
looks like prior work or the deliverable you are about to produce — move it to
`_quarantine/`, report it, and stop. Do not read it.

### 2.2 Derive the constraint before you look at the pool

Write this from the commander's oracle text and the restriction alone. Five
rows, one to three lines each. Loading the card list first turns this into a
description of what you found.

| Direction | Question |
|---|---|
| `eliminated` | What function does the restriction remove outright? Name a substitute or say there is none. |
| `converted` | What still exists but now counts differently — and what changes about how you count it? |
| `structural` | What in the commander's own text forces a structural consequence, in either direction? Include commander tax (+{2} per previous cast from the command zone, CR 903.8): how dependent is the plan on the commander surviving, and how many recasts can it afford? |
| `exposed` | What do opponents' cards do to this deck that they would not do to a typical one, and which of their cards become blank against it? Check both directions against card text, not reputation. |
| `inverted` | **Which cards does the restriction or the commander make better than they are in a normal deck?** A drawback you never pay; a drawback that becomes an upside; a one-sided clause; a widely-feared card that is blank against you. This is the direction most likely to be skipped and the one that produces the deck's best cards. |

### 2.3 Confront it against the counts

You have `prep.py`'s coverage table. **Do not read `digest.md` or `pool.csv`
this turn** — the counts are enough to revise the derivation. For each row,
confirm, revise or reverse it in one line and name the count that did it. A
function showing 0 or 1 is a *hypothesis about the query*, not a fact about the
pool: re-query the bare outcome over `pool_tagged.csv` before writing it down.

```bash
python -c "
import pandas as pd; p=pd.read_csv('pool_tagged.csv',encoding='utf-8-sig')
print(p[p.oracle_text.fillna('').str.contains(r'<bare outcome>',case=False,regex=True)][['name','type_line']].to_string())"
```

### 2.4 Weaknesses, kill chain, opponent arithmetic

- **Weaknesses `W1…Wn`** — at most six, each one line, each with the pool's
  answer named, or the honest statement that the pool has none. Every card you
  name here is a commitment the next turn must dispose of.
- **Kill chain** — the causal chain from the commander's payoff to a dead
  opponent (or to the alternative win), as ordered links. Each link carries the
  number of pool cards that supply it. **A link with zero support kills the win
  condition**; pick another.
- **Opponent model.** Use the row matching intake answer 3 unless the user gave
  other numbers. These are declared assumptions, not measurements; state them
  once in `plan.md`.

| Table | Spot removal | Sweepers | Counters | Mana up when you commit | Life each opponent loses per cycle to others, from turn 4 |
|---|---|---|---|---|---|
| casual precons | 4 | 1 | 0 | 40% | 2 |
| upgraded, no infinite combos | 7 | 2 | 2 | 60% | 4 |
| high-power, combo expected | 8 | 2 | 4 | 75% | 5 |

- **The clock.** Opponent life on turn T is `40 − L·max(0, T−3)`, with L from the
  table. Size any damage-based kill against that curve, never a static 40. If
  the deck does not win through damage, say what the clock is instead.
- **The protection number.** Compute, in pasted code, the expected number of
  live answers across three opponents on the turn you commit to winning (7 +
  turn cards seen, hypergeometric, per the table). Count only answers that can
  hit what this deck commits. That number sizes the protection package.

### 2.5 Budget

Commit slot targets **before** you see any card text. Packages are named for
what they do in *this* deck's plan. If the list comes out as a generic
ramp / draw / removal / wipes / lands template, either say what the commander
and restriction reorganised or state plainly that they reorganised nothing and
why. Each package declares `target` (slots), `criterion` (a rule a card either
meets or fails), and `weakness_ref`. One package may be `flex`, capped at 8.
Targets plus basics sum to 99.

### 2.6 Write two files and stop

`plan.md` — the tables above, the weaknesses, the kill chain, the arithmetic,
the budget. Mark every card name `[[Like This]]`. Then:

```bash
python scan.py plan.md
```

`strategy.json` — exactly these keys (the deck validator reads them next turn):

```json
{"meta": {"commander": "", "restriction": "", "date": "", "data_fingerprint": {}},
 "weaknesses": {"W1": "one line"},
 "weakness_answers": {"W1": {"cards": ["Card Name"], "note": "or: none in pool"}},
 "play_lines": {"L1": "one line"},
 "kill_chain": [{"link": "one line", "pool_count": 0, "cards": ["Card Name"]}],
 "budget_preview": {"package": {"target": 0, "criterion": "", "weakness_ref": "W1"}}}
```

Then post, in the chat, **only**: the derivation table with its verdicts, the
weakness list, the kill chain, the opponent model row used, the protection
number, and the budget. Then stop and wait. Do not start selecting cards.

---

## RULES THAT APPLY THROUGHOUT

- **The file outranks memory.** Costs, types and text come from the files. Where
  recall and file disagree, the file wins and you say so.
- **A zero is a hypothesis about your query.** Re-query the bare outcome, then
  check two or three cards you *expect* to match; if they are in the file and
  your query misses them, the query is broken. Names are compared with
  `config.norm()`, never with `==`.
- **Search the outcome, not the noun.** "Put a land onto the battlefield" finds
  cards "search your library for a land" does not; "create a Treasure" finds
  mana sources "add {" does not.
- **A pronoun is not an opponent.** "Its controller", "target player", "their
  library" resolve to whoever you target — including you. Enumerate both
  readings before verdicting such a card.
- **Net effects, against a baseline.** Anything claimed to add resources is a
  ledger: position without it, position with it, everything spent.
- **One card, one slot.** A modal double-faced or split card is one card with
  modes; name the mode you are taking and count it once.
- **Rigour is spent where a slot could still move.** A number that cannot change
  a card choice is decoration however carefully it was produced.

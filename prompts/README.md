# Prompts

The prompt system is the object under evaluation. It exists in two conditions, so
that the effect of the protocol can be measured rather than asserted.

## Full protocol (three chats)

Each file is pasted as the first message of its own conversation. Splitting the
build across chats is deliberate: the red team in `P3` runs without the build
conversation in context, so the audit is blind rather than self-reviewing.

| File | Chat | Produces |
|---|---|---|
| `P1_INTAKE_AND_PLAN.md` | A | `plan.md`, `strategy.json` |
| `P2_BUILD_AND_DELIVER.md` | B | `candidates.json`, `deck.json`, `DECKLIST.md`, `REPORT.md` |
| `P3_REDTEAM.md` | C | the blind audit |

## Ablation control

`MIN_BUILD.md` is the baseline condition, run as a single chat. It keeps only what
makes a deck **valid and grounded** — intake, the pool script, reading card text,
legality gates, rendering, and the scorecard. Everything that tries to make the
deck **better** is deliberately absent: constraint derivation, weakness lists,
opponent maths, slot budgets, commitment tracking, oversampling, mana maths, and
the red team.

That is what makes the comparison meaningful. Each removed component can be added
back one at a time and scored, so a claim that the protocol helps is a measurement
rather than an opinion. Outputs from both conditions are in
[`../results/`](../results/).

## Earlier versions

The prompt was iterated from v3 to v9 as a single monolithic document before being
restructured into the three-chat system above. Those versions were superseded and
are not preserved here as files; what they changed and why is recorded in
[`../docs/failure-log.md`](../docs/failure-log.md), which is the part that carries
the information.

Two scripts from the v9 era (`build_pool.py`, `validate_strategy.py`) were replaced
by `prep.py` and `validate_deck.py` and are likewise not included.

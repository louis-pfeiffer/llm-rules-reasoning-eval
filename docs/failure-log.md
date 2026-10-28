# Failure log

> **STATUS: TEMPLATE.** One row per observed model error. This is the most important
> document in the repository — an evaluation reader will open it before anything else.
> Only record failures that actually happened; do not reconstruct plausible-sounding ones.

## How to read this

- **Claim** — what the model asserted, quoted or closely paraphrased.
- **Reality** — what is actually true, with the comprehensive rules number or card text
  that settles it.
- **Class** — the failure category (see taxonomy below).
- **Caught by** — human review, a validator script, or the blinded audit.
- **Fix** — the prompt version or structural guard that addressed it, or "unfixed".

## Taxonomy

TODO — finalise the categories once the table is populated. Starting set:

| Code | Class | Description |
|---|---|---|
| `RULE` | Rules misreading | Misapplies a comprehensive rule or card interaction. |
| `CARD` | Card-text error | Attributes text, cost or type to a card that it does not have. |
| `CONSTRAINT` | Constraint violation | Breaks a stated build restriction. |
| `POOL` | Out-of-pool selection | Uses a card that is not in the legal pool or collection. |
| `ARITH` | Counting error | Deck size, curve, colour or category counts do not add up. |
| `CONFAB` | Confabulated support | Cites a rule, card or source that does not say what is claimed. |
| `DRIFT` | Instruction drift | Silently abandons an instruction held earlier in the build. |

## Failures

| # | Prompt ver. | Claim | Reality (rule / card) | Class | Caught by | Fix |
|---|---|---|---|---|---|---|
| 1 | TODO | TODO | TODO | TODO | TODO | TODO |
| 2 | | | | | | |
| 3 | | | | | | |

## Notes on individual failures

### F1 — TODO short title

TODO — a paragraph for any failure worth more than a table row: what made it hard to
detect, why the model plausibly produced it, and what the fix generalises to.

## Failures the tooling cannot catch

TODO — be explicit about the limits. A validator can check legality, counts and pool
membership; it cannot check whether a strategic justification is sound. Say which classes
above still depend entirely on human domain expertise.

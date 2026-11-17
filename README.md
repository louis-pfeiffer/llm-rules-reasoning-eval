# LLM Rules-Reasoning Evaluation

**Where does a frontier model fail when it reasons over a large formal rulebook in a
domain the evaluator knows better than it does — and which of those failures can be
caught by structure rather than by expert attention?**

The deliverable is not a deck. It is an [18-entry failure log](docs/failure-log.md),
a prompt protocol built to close each failure class, and a stripped control prompt
that makes the protocol's effect measurable rather than asserted.

## Why Magic: The Gathering

The domain was chosen because it makes failures *provable*:

- A formal rulebook of ~951,000 characters, with numbered rules that can be quoted
  and checked.
- Over 32,000 commander-legal cards, each with its own text, interacting
  combinatorially.
- A hard legality boundary: a deck either satisfies a stated restriction or it does
  not. An error is a fact, not a matter of taste.
- An evaluator with deep domain knowledge, which is what makes the subtle failures
  visible at all.

The task is deliberately not one the model can retrieve. Each build uses only cards
from a real 8,579-card physical collection, respecting owned quantities, under a
restriction invented for the build — *no non-land permanents*, or *every creature
must be a Cat*. There is no popular decklist to reproduce.

## Three findings

**1. Where a ground truth exists in machine-readable form, supply it rather than
checking recall against it.** The model answered questions about specific cards from
memory, fluently enough that a wrong mana cost read exactly like a right one, and
each silent error fed a downstream calculation. Correcting them one at a time does
not scale across 32,000 cards. Loading the Scryfall bulk card data as a project
input stopped the guessing — and improved reasoning about what cards *do*, not just
what they cost, because the model was reading the card instead of remembering it.
([F10](docs/failure-log.md))

**2. Two queries agreeing on a zero is not corroboration if both share the same
defect.** A card was reported absent from the collection on the strength of two
independent queries returning zero. Both were defeated by the accent in "Mists of
Lórien". A null result over a large corpus is a claim about the query, not about the
world, until a bare-term re-query and a negative control say otherwise.
([F12](docs/failure-log.md))

**3. The failures that survive grounding are evaluative, not factual — and those are
the ones automation cannot reach.** Once card text is supplied, errors stop being
*what the card says* and become *what the card is worth*. The clearest case is a card
the model described correctly and still judged wrongly, because it priced a drawback
against a generic deck rather than this one. It passes every automated check in this
repository. ([F2](docs/failure-log.md))

A fourth, about the harness rather than the model: the pool builder silently dropped
154 colourless lands through a `NaN` coercion bug, caught only because it was
required to reproduce a known-good pool exactly. An evaluation harness is generated
code too, and can be wrong with no symptom. ([F18](docs/failure-log.md))

## Method

Three chats, each a separate conversation, with a deliberately stripped fourth as a
control:

| Stage | Prompt | Produces |
|---|---|---|
| Plan | [`P1_INTAKE_AND_PLAN.md`](prompts/P1_INTAKE_AND_PLAN.md) | constraint derivation, weakness rows, slot budget |
| Build | [`P2_BUILD_AND_DELIVER.md`](prompts/P2_BUILD_AND_DELIVER.md) | shortlist, final deck, rendered list, written report |
| Audit | [`P3_REDTEAM.md`](prompts/P3_REDTEAM.md) | blind red-team review |
| *Control* | [`MIN_BUILD.md`](prompts/MIN_BUILD.md) | the same deck with every quality-improving component removed |

The audit runs in its own conversation so it cannot see the build's reasoning —
blinding, not self-review. The control keeps only what makes a deck *valid*
(legality gates, pool membership, card text) and drops everything meant to make it
*better* (constraint derivation, weakness lists, opponent modelling, slot budgets,
oversampling, the red team), so each component can be added back and scored.

The governing principle throughout: **failures should be caught by scripts and
structure, not by instructing the model to be careful.** Three consecutive prompt
versions shipped the same scanning bug in a different place each time; the fix was
not a fourth patch but a registry that made the omission impossible.

## Repository layout

```
docs/failure-log.md   every observed failure, classified, with rules citations
docs/rubric.md        the ranking rubric — ordered criteria with tie-breakers
prompts/              the protocol, and the ablation control
results/              build artefacts for both conditions
scripts/              pool prep, validators, prose scanner, renderer, scoring
data/                 the collection; see data/README.md for external inputs
```

## Running it

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Two inputs are third-party and are not redistributed here: the full Scryfall card dataset
and the comprehensive rules. [`data/README.md`](data/README.md) says where to get
them. Note that fetching the Scryfall data is not housekeeping — grounding every
card claim in it is the project's central design decision, as finding 1 describes.

## How this was built

I designed the protocol, supplied the domain expertise that exposed the failures,
diagnosed each failure class, and decided what changed between versions. The Python
tooling was written by Claude under my direction.

Stating that plainly is the point rather than a caveat: the contribution this project
demonstrates is evaluation — building a test a model can fail, noticing when it does,
and converting each failure into a structural fix — not the authorship of the
validators.

## Status

Honest about where this stands: the failure log, the protocol and both conditions'
artefacts are complete. The measured baseline-versus-protocol comparison in
[`results/RESULTS.md`](results/RESULTS.md) is not yet written up, and the sample is
small — two commanders, two restrictions, one model version, one rules release.
Nothing here should be read as a general claim about model capability.

## Licence and attribution

Code under the [MIT Licence](LICENSE). Card data from
[Scryfall](https://scryfall.com); comprehensive rules published by Wizards of the
Coast. The annotated collection includes card text from Scryfall, but neither the full Scryfall dataset nor the rules are redistributed here.

Unofficial fan project. Not produced by, endorsed by, supported by, or affiliated
with Wizards of the Coast.

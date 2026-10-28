# LLM Rules-Reasoning Evaluation

> **STATUS: DRAFT SCAFFOLD.** Every line marked `TODO` is a placeholder for Louis to
> fill or delete before the repo goes public. Do not publish with `TODO` markers visible.

**One-sentence summary:**
TODO — e.g. "An evaluation of where a frontier LLM fails when it reasons over a large
formal rulebook in a domain I know better than it does, plus the tooling that catches
those failures automatically."

---

## Why this domain

Magic: The Gathering is an unusually good test bed for long-horizon, rule-heavy reasoning:

- A formal rulebook of roughly 900,000 characters, with numbered rules that can be cited.
- Over 30,000 legal cards, each with its own text, interacting combinatorially.
- Claims are **verifiable**: a deck either satisfies a stated restriction or it does not.
- Deck construction is a constrained optimisation problem with a hard legality boundary,
  so an error is a fact, not a matter of taste.

TODO — add a sentence on the specific constraint used (no non-land permanents, Noyan Dar)
and why that makes failures easier to detect.

## Key findings

TODO — three bullets, each one measured claim. Examples of the *shape* to aim for
(replace with real numbers, or delete if not measured):

1. TODO — the failure class that recurred most often across prompt versions.
2. TODO — what structural validation caught that instruction-following did not.
3. TODO — where the protocol plateaued, and the reason.

## The protocol

TODO — short description of the five-turn build protocol, ideally with a small diagram.

## Failure log

The most detailed part of this project is [`docs/failure-log.md`](docs/failure-log.md):
one row per model error, what was claimed, what the rules actually say, who caught it,
and which prompt version fixed it.

## Results

See [`results/`](results/) for the raw build artefacts and
[`results/RESULTS.md`](results/RESULTS.md) for the baseline and ablation comparison.

## Repository layout

```
scripts/    validators, pool builder, prose scanner, renderer, ablation scoring
prompts/    every prompt version, v3 through v9
results/    build artefacts and measured results
docs/       failure log and methodology notes
data/       collection data; see data/README.md for the files that are not redistributed
```

## Running it

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

TODO — the exact command sequence, once verified on a clean clone. External data files
must be downloaded first; see [`data/README.md`](data/README.md).

## How this was built

TODO — keep this paragraph and make it honest. Suggested content: the Python tooling was
written by Claude (Anthropic) under my direction; my contribution was the protocol design,
the domain expertise and rules corrections that exposed the failures, the diagnosis of each
failure class, and the decision about what changed between prompt versions. The point of the
project is the evaluation, not the code.

## Licence and attribution

Code is released under the MIT Licence (see [`LICENSE`](LICENSE)).

Card data is sourced from [Scryfall](https://scryfall.com); the comprehensive rules are
published by Wizards of the Coast. Neither dataset is redistributed here — see
[`data/README.md`](data/README.md).

This is an unofficial fan project. It is not produced by, endorsed by, supported by, or
affiliated with Wizards of the Coast.

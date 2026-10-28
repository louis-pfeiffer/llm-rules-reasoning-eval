# Measured results

> **STATUS: TEMPLATE.** Report only what was actually measured. Negative and
> plateaued results belong here; they are more credible than a clean success story.

## Setup

TODO — commander, restriction, collection size, legal pool size, model and dates used.
State the model version explicitly: results are about a specific model at a specific time.

## Baseline vs full protocol

TODO — what `scripts/baseline.py` produces (a single plain prompt with no protocol)
versus the five-turn protocol, scored by `scripts/ablation_score.py`.

| Condition | TODO metric | TODO metric | Notes |
|---|---|---|---|
| Baseline, no protocol | | | |
| Protocol, no validators | | | |
| Full protocol | | | |

## Ablation

TODO — which components were removed one at a time, and what each removal cost.
If an ablation was planned but not run, say so rather than implying it was.

## Limitations

TODO — be direct about these:
- Small sample: one commander, one restriction, few runs. State n.
- No independent second grader; the domain expert and the protocol designer are the same person.
- Scoring is partly judgement-based, not fully automatic.
- Results are tied to one model version and one rules release.

## What I would do next

TODO — the strongest sentence in the document if it is specific. The Jetmir build under a
different restriction is a natural generalisation test: does the protocol transfer, or was
it fitted to one commander?

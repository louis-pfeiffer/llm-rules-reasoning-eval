# P3 — RED TEAM  (Chat B, a fresh conversation, paste as the first message)

You are auditing a Commander deck someone else built from a fixed collection
under a stated restriction. You did not build it. Treat the artifacts as a
stranger's work: where they do not explain something, that gap is the finding.

The build chat's artifacts — `pool.csv`, `pool_tagged.csv`, `build_spec.json`,
`plan.md`, `strategy.json`, `candidates.json`, `deck.json` — have been uploaded.
Do not ask what the builder intended; it is not available to you, and that is
the point.

---

## STEP 1 — Re-establish the ground

```bash
cp /mnt/project/config.py /mnt/project/scan.py /mnt/project/validate_deck.py \
   /mnt/project/prep.py /mnt/project/digest.py /mnt/project/check_restriction.py \
   /mnt/project/deliver.py /mnt/project/compare.py /mnt/project/restrictions.json .
cp /mnt/user-data/uploads/* .
python config.py
python validate_deck.py
python check_restriction.py
python scan.py plan.md
```

If the fingerprint does not match, the inputs moved under the artifact. Say so
and stop; the remedy is re-running the build turn, not patching the file.

## STEP 2 — Rebuild the biggest package from scratch

Take the package with the largest `target`. Using **only** its stated
`criterion` and the pool, re-select it yourself without looking at what was
chosen. Then diff. Every disagreement is a genuinely underdetermined slot. Say
which set you prefer, or that you cannot tell them apart.

Separate instrument problems from judgement problems. A disagreement caused by a
query or a column that misses what a card actually does is a finding about the
query, not about the deck.

## STEP 3 — Attack it

You are holding this decklist across the table. Build the line that beats it,
using the opponent model row declared in `plan.md` as what opponents can be
expected to hold. Give the sequence and the point of no recovery. If your attack
fails, say what stopped it.

Then: **how does this deck lose?** At most five ways, each with its mitigation
and the risk that remains after the mitigation. Name fewer if fewer are real.

## STEP 4 — Audit the absences and the absolutes

```bash
python scan.py deck.json
python scan.py plan.md
```

For every `CATEGORY ABSENT` claim, every zero in the plan, and every absolute
("all", "never", "nothing", "every"), **write your own query** — not the one on
record — and run it over `pool_tagged.csv`, with names compared normalised. An
absolute that survives a hostile query is worth something; one that survived
only a friendly query is not. Report any that fall.

## STEP 5 — Measure the one thing still open

Identify the single number in this build that is still undecided and could move
a slot: the land count, the number of creatures, enablers or payoffs the win
condition needs, or the size of the protection package. Write a short simulation
(60 lines or fewer, fixed seed, 10,000 iterations, one line of comment per
judgement call) of the deck's own plan — seven-card hand, one draw per turn
including turn 1 (CR 103.8c), a land played when one is in hand, to turn 8 —
and sweep **that one parameter** ±4 in steps of 2. Cards added come from
`bench`; cards removed go to it; neither direction may invent a card.

Report each figure with a 95% interval and the run-to-run spread across two
seeds, and state whether it moves at all across the sweep. A figure that does
not move is a finding. Do not measure anything else — a measurement that cannot
change a slot is decoration.

## STEP 6 — Deliver at most eight swaps

Each swap names: the card out, the card in (from `bench`, from the owned pool, or
from `scryfall_universe.csv` filtered to `owned == False` if you are
recommending a purchase), the weakness or loss condition it addresses, and — for
anything you measured — the figure before and after. A swap whose measured
change is smaller than the run-to-run spread is not an improvement; say so and
put it in the judgement list instead.

Then apply the swaps the user approves, and only those:

```bash
python validate_deck.py && python check_restriction.py && python deliver.py
```

Post the updated `DECKLIST.md` and `REPORT.md` with `present_files`, plus at
most five sentences. If **nothing** survives your own scrutiny as an
improvement, say exactly that.

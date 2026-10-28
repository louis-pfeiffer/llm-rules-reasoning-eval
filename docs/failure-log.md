# Failure log

Every model error observed during the build, what was actually true, how it was
caught, and what changed as a result. This is the primary record of the project:
the decks are the test case, the failures are the finding.

> **Verification status.** Rows marked **(verify)** were reconstructed from the
> project's running corrections record rather than quoted from the original
> transcript. The substance is right; the exact wording of the model's claim may
> not be. They are marked rather than silently smoothed over, consistent with the
> project's own rule that an unverified claim is labelled as one.

## How to read this

- **Claim** — what the model asserted.
- **Reality** — what is actually true, with the rule or card text that settles it.
- **Class** — see the taxonomy below.
- **Caught by** — human expert review, a validator script, or the blind red team.
- **Consequence** — what changed in the deck, the prompt, or the tooling.

Every comprehensive-rules number below has been checked against
`MagicCompRules_20260819.txt`, the release the build ran on, and quoted rule text is
verbatim from it. Rule numbering changes between releases, so a later release should
be re-checked rather than assumed.

## Taxonomy

| Code | Class | Description |
|---|---|---|
| `RULE` | Rules misreading | Misapplies a comprehensive rule or a card interaction. |
| `CARD` | Card-text error | Attributes text, cost, type or behaviour a card does not have. |
| `ARITH` | Counting error | Mana, counts or budgets that do not add up. |
| `EVAL` | Context-blind evaluation | Reads the card correctly, then judges it against a generic archetype instead of this deck and this plan. |
| `QUERY` | False absence | Concludes a card or category is absent when the query was defective. |
| `DRIFT` | Internal inconsistency | Contradicts or abandons something the same artefact already established. |
| `TOOL` | Tooling defect | A bug in the generated code silently corrupts the inputs. |

## Failures

| # | Claim | Reality | Class | Caught by | Consequence |
|---|---|---|---|---|---|
| F1 | Vesuva and Echoing Deeps copying Dark Depths enter with no ice counters, giving the Marit Lage line three redundant enablers. | Both enter *as* copies, so Dark Depths' own "enters with ten ice counters" applies (CR 614.1c). Only Thespian's Stage, which copies a permanent already on the battlefield, produces a counter-free Dark Depths. The line has one enabler, not three. | `RULE` | Expert review | Dark Depths demoted from primary to secondary win condition. |
| F2 | Glacial Chasm is a trap in this deck, because it stops you attacking. | The restriction is real, but it costs this deck almost nothing: it is a draw-go control shell with no meaningful attacking creature base. It is also voluntarily exitable — cumulative upkeep is optional ("you may pay [cost] for each age counter on it. If you don't, sacrifice it", CR 702.24a), so declining to pay sacrifices the Chasm and frees the attack on the turn it matters. | `EVAL` | Expert review | Card reinstated; "trap card" verdicts required to weigh the drawback against this deck's actual plan, not against a generic deck. |
| F3 | Enlightened Tutor is a trap under this restriction, since the deck runs no artifacts or enchantments. | The pool contains five artifact lands, which are legal under a no-non-land-permanents restriction and are valid targets. | `CARD` | Expert review | Trap-card claims required to be checked against the pool, not against the archetype in the abstract. |
| F4 | Delirium is unreachable in a deck of lands, instants and sorceries. | Artifact lands carry two card types in every zone, so the count reaches four more easily than a type-line glance suggests. | `CARD` | Expert review | Hybrid-type cards required full type-line enumeration; boolean type flags were hiding multi-type cards. |
| F5 | The layer system resolves conflicting effects by "higher value wins". | Within a layer, order is determined by timestamp, not magnitude: "an effect with an earlier timestamp is applied before an effect with a later timestamp" (CR 613.7). | `RULE` | Expert review | Every rules claim required a verbatim citation resolving against the rules file. |
| F6 | Analysis distinguishing "on the play" from "on the draw". | Inapplicable in Commander: all players draw on turn one (CR 103.8c). | `RULE` | Expert review | Format-specific assumptions imported from 1v1 constructed flagged as a recurring source of error. |
| F7 | MDFCs and split cards occupy two independent role slots, one per face. | They are single cards with modal abilities. One card, one slot. | `CARD` | Expert review | Slot-budget accounting corrected. |
| F8 | Cascading Cataracts is mana-neutral. | Net negative. Its ability costs {5} and taps the land itself, so six mana sources are spent to produce five mana. It is colour fixing, not ramp. | `ARITH` | Expert review | Mana arithmetic re-derived from the printed cost rather than asserted; a land's own tap counted as part of the cost. |
| F9 | Deserted Temple with Lotus Field nets +2 mana. | Nets +1. | `ARITH` | Expert review | As above. |
| F10 | Mana costs and oracle text stated from recall. More than one card's printed cost was wrong, including its coloured pip requirements (Teferi's Protection believed to be among them **(verify)**). | The printed costs differ. Pip counts feed directly into castability scoring, so a wrong cost silently corrupts the ranking rather than failing visibly. | `CARD` | Expert review | The fix was architectural: Scryfall bulk data loaded as a project input so every card claim resolves against actual oracle text and mana cost. See note below. |
| F11 | Destruction effects are strictly negative for this deck. | Positive cases exist: permanent recursion, and self-recurring lands such as Drownyard Temple. | `CARD` | Expert review | Directional heuristics ("bounce beats destruction") replaced with case-by-case evaluation. |
| F12 | Mists of Lórien is not in the collection — two independent queries returned zero. | It is in the collection. Both queries shared an accent-normalisation defect, so the second corroborated nothing. | `QUERY` | Validator (added after) | Rule adopted: *a zero over a large pool is a query failure until a bare-term re-query proves otherwise*, plus a normalisation census surfacing non-ASCII names at intake instead of at the end. |
| F13 | Strategy row C3 claimed exactly one land-recursion effect existed in the pool. | Its own `contradicts` field, one field away in the same artefact, named a second. Every check passed. | `DRIFT` | Red team / later validator | Named cards tracked across turns; a scarcity lead list added so a claim of scarcity is cross-checked against the artefact's own contents. |
| F14 | Horizon of Progress named as the answer to the build's most under-supplied function — then never shortlisted. | An answer named and then dropped without a recorded reason. Survived a full five-turn execution and a red team. | `DRIFT` | Red team | Disposition ledger added: every card named as an answer must be carried forward to a recorded verdict. Provenance tracking alone was shown to catch nothing. |
| F15 | Strategy rows S3, S4 and I3 recorded pool counts of 8, 14 and 8. | Re-running the recorded queries returned 9, 15 and 9. The counts had drifted from the queries that produced them. | `ARITH` | Validator | Claim reproduction added: the validator re-executes each recorded query and compares. |
| F16 | Pool census recorded 1,020 rows. | 1,021. | `ARITH` | Validator | Data fingerprint added; artefacts built on moved inputs now halt instead of silently disagreeing. |
| F17 | Deck prose contained thirteen unregistered absolute quantifiers ("always", "never", "only") on first scan. | Each was an unsupported universal claim over a 30,000-card universe. One had to be falsified by hand by the red team. | `DRIFT` | Scanner | Prose scanning unified into `scan.py` across every authored surface. See note below. |
| F18 | `build_pool.py` reported a correctly built pool. | It was silently dropping 154 colourless lands: colourless cards have an empty `color_identity`, pandas reads it as `NaN`, and `NaN or ""` returns `NaN`. | `TOOL` | Reproduction test | Caught only because the new builder was required to reproduce the existing pool exactly. Without that test the error would have been invisible and every downstream count wrong. |

## Notes on the failures worth more than a row

### F1 — the error that changed the deck

The Dark Depths line produces a single 20/20 flying indestructible token. That is a
strong threat, not a win on the spot: three opponents starting at 40 life are a long
way from dead. What the error inflated was not the payoff but the **reliability** —
three land-copy effects appeared to assemble it, so it looked consistent enough to
build the deck around. With only Thespian's Stage actually enabling it, the line is
a two-card combo with no redundancy, which is a very different thing to plan around.

What makes it instructive is that the reasoning was *locally* plausible. Thespian's
Stage genuinely does produce a counter-free Dark Depths, and all three cards are
copy effects on lands. The failure was treating cards with similar text as
mechanically identical, without checking *when* each copy effect applies — a
permanent entering as a copy inherits the original's "enters with" clause, while one
copying something already on the battlefield does not. Fluent, confident, and wrong
in exactly the way that is hardest to spot without domain expertise.

### F2 — reading the card correctly and still being wrong

This is the only failure where the model's reading of the card text was accurate.
Glacial Chasm does stop you attacking. The verdict was still wrong, for two reasons
it did not weigh: this deck is a draw-go control shell that rarely attacks, so the
restriction costs it almost nothing, and cumulative upkeep is optional, so the
Chasm can be abandoned on the turn an attack finally matters.

It earns its own class because no amount of better text retrieval would fix it. The
model had the text and drew a generic conclusion from it — *attacking restrictions
are bad* — instead of pricing the drawback against this deck's actual plan. For an
evaluation harness this is the uncomfortable category: the output is checkable
against the card, passes that check, and is still a bad answer.

### F10 — replacing recall with retrieval

The individual wrong costs matter less than what they revealed. The model was
answering questions about specific cards from memory, and doing it fluently enough
that a wrong pip count read exactly like a right one. Correcting them one at a time
would have been endless: there are over 30,000 legal cards, each error is silent,
and each one feeds a downstream calculation.

The fix was to stop asking. Scryfall bulk data was loaded as a project input, so
every claim about a card's cost, type line or oracle text resolves against the
actual printed text instead of recall. The gain was larger than the cost correction
that prompted it — grounding the oracle text improved the quality of reasoning
about what cards *do*, not just what they cost, because the model was now reading
the card rather than remembering it.

This is the project's clearest instance of a general principle: **where a ground
truth exists in machine-readable form, put it in front of the model rather than
checking its recall against it afterwards.** Verification scales badly; grounding
scales well. It also changes what the remaining failures look like — with the text
supplied, errors move from *what the card says* to *what the card is worth*, which
is the `EVAL` class and the one that still needs a human.

### F12 — a zero is not an absence

Two independent queries returned zero for a card that was present. They agreed
because they shared a defect, not because they were right. The model reported the
agreement as corroboration.

This produced the single most transferable rule in the project: **two queries
agreeing on a zero is not corroboration if both share the same defect.** A null
result over a large corpus is a claim about the query, not about the world, until a
bare-term re-query and a negative control say otherwise. The accent in "Lórien"
was the whole cause.

### F17 — patching surface by surface *is* the pattern

Three consecutive prompt versions shipped the same bug in different places. A scan
ran on one authored field and not on the identical field one key away: v7 scanned
the strategy rows and missed `strategy.md`; v8 fixed that and missed `deck.json`'s
`package_notes`, `deck[].note` and `bench[].reason` — where a scan found thirteen
unregistered absolutes on first contact.

The lesson was structural rather than instructional. Each individual patch was
correct and each left the same hole elsewhere, so the fix was to make adding a new
artefact cost one registry entry instead of a copied block of scanning code. This
is the clearest instance of the project's governing principle: **failures should be
caught by structure, not by telling the model to be careful.**

### F18 — the grader needs a grader

The only `TOOL`-class failure is included deliberately. The evaluation harness is
itself generated code and can be silently wrong, in which case every measurement
built on it is wrong too, with no symptom. It was caught only because the new pool
builder was held to reproducing the previous pool exactly. A reproduction test
against a known-good artefact is cheap and catches a class of error that reading
the code does not.

## What the tooling cannot catch

The validators check legality, counts, pool membership, claim reproduction, input
fingerprints and prose hygiene. Those cover `ARITH`, `QUERY`, parts of `DRIFT`, and
anything mechanical.

They do **not** check whether a strategic justification is sound. Every `RULE`,
`CARD` and `EVAL` failure above — F1 through F11, the ones that actually changed the
deck — was caught by a human who knew the domain. No script in this repository
would have found them. A rules citation can be verified against the rules file
automatically; whether the cited rule is the *relevant* one cannot. `EVAL` is harder
still: F2 would pass every automatic check in the repository, because the claim it
made about the card was true.

That is the honest limit of the method: it converts expert attention into reusable
structure, so each failure class only has to be caught by a person once. It does not
remove the need for the expert.

## Non-reasoning incidents

**Workspace integrity.** During the authoring of prompt v9, a complete
`PROMPT_v9.md` — 80,318 bytes, with its own changelog — was already present in the
working directory, unwritten by that conversation. It was quarantined unread and the
deliverable written independently.

Two details make this worth recording. First, the prompt had contained a
workspace-manifest check whose removal had been recommended on the grounds that it
had run five times and caught nothing; the scenario it was designed for occurred
during the very authoring of the version that removed it. Five turns was too small a
sample to declare a check dead weight. Second, the quarantined file resembled the
expected deliverable closely, which is precisely the condition under which an
unaccounted file is most dangerous to read. The detection was restored in a cheaper
form: list the working directory, quarantine anything unaccounted for, read nothing.

**Not a model failure.** `Part the Waterveil` was absent from the collection export
because of a date discrepancy in the export, not because of anything the model did.
Recorded here so the data-side and reasoning-side failures are not conflated.

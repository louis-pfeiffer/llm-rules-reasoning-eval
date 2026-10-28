# P2 — BUILD AND DELIVER  (Chat A, paste after the plan turn)

Same rules as P1. This turn produces the 99, validates it, and renders the two
files the user actually reads. It is the only turn that reads card text in bulk.

---

## STEP 1 — Load the digest, once

```bash
python digest.py            # defaults: top 15 per function, 170 chars of oracle
head -30 plan.md
```

Then read `digest.md` with the file viewer: every function's best candidates in
rank order, every card listed once with all its tags, and the lands (all of them
if the commander's text mentions lands, otherwise the best-ranked plus the best
colour fixers; `--all-lands` forces the full list). Read it **once**. If a
package's criterion is not satisfied by anything the digest shows, do not
conclude the pool lacks it — grep the tag or the bare outcome in
`pool_tagged.csv` first:

```bash
python -c "
import pandas as pd; p=pd.read_csv('pool_tagged.csv',encoding='utf-8-sig')
s=p[p.tags.fillna('').str.contains('<tag>')].sort_values('edhrec_rank')
print(s[['name','mana_cost','type_line','edhrec_rank']].to_string())"
```

`edhrec_rank` is a **popularity prior**. It orders candidates inside a function;
it never justifies a card. It knows nothing about this commander or restriction
— which is where your value is added, so any slot where you simply took the
best-ranked card is a slot you should be able to defend on the card's text.

## STEP 2 — Dispose of the plan's commitments

Before selecting anything, resolve **every** card named in `strategy.json`'s
`weakness_answers` and `kill_chain` to `shortlisted`, `benched` or `dropped`,
with a one-line reason. This becomes `carried_from_strategy[]` in
`candidates.json`.

## STEP 3 — Oversample, then rank

For each package, shortlist **`target` + 2, or 1.25 × `target`, whichever is
larger**, by a recorded query plus an explicit ordering key. Every shortlisted
card must satisfy the package's criterion.

Rank each shortlist and take the top `target`. Each survivor records `beat` —
the card it displaced. Each loser goes to `bench` with what it lost to and why.
If a package cannot fill its target with cards that meet its criterion, say so
and reallocate the slots explicitly.

Write `candidates.json`:

```json
{"meta": {"data_fingerprint": {}},
 "carried_from_strategy": [{"name": "", "disposition": "shortlisted|benched|dropped", "reason": ""}],
 "budget": {"package": {"target": 0, "criterion": "", "weakness_ref": "W1",
                        "shortlist_query": {"field": "", "pattern": ""},
                        "ordering_key": ""}},
 "candidates": [{"name": "", "package": "", "refs": ["W1"], "mode_taken": null}]}
```

## STEP 4 — Mana base, in code

- Count coloured sources **from oracle text** (`colour_sources_text`), not from
  `produced_mana`, which records what a land *can* produce, not what it is
  *permitted* to produce here.
- Compute, in pasted code, the probability of having the commander's colours
  available on the turn it is first castable (7 + turn cards seen,
  hypergeometric). Count pips: a commander or key spell needing two of one
  colour needs that tested separately. **Below 85% is a failure to fix or to
  accept out loud.**
- Argue the land count against the validator's **floor**, never its ceiling.
  Every modal double-faced card counted as a land is a land you might cast as a
  spell.
- If the commander, the restriction or the opponent model makes some lands a
  liability or an asset (lands that are also creatures or artifacts, lands the
  commander's text uses), say how many and why it matters. Otherwise skip it.
- Basics are free and unlimited regardless of what the collection holds.

## STEP 5 — Write `deck.json`

```json
{"commander": "", "color_identity": "", "restriction": "one line, plain English",
 "data_fingerprint": {},
 "budget": {"package": {"target": 0, "criterion": "", "weakness_ref": "W1"}},
 "weakness_rows": {"W1": ""}, "play_lines": {"L1": ""},
 "package_notes": {"package": "one substantive paragraph"},
 "deck": [{"name": "", "count": 1, "mana_cost": "", "type_line": "",
           "package": "", "roles_secondary": [], "mode_taken": null,
           "refs": ["W1"], "beat": "", "note": "only if exceptional"}],
 "bench": [{"name": "", "package": "", "lost_to": "", "reason": ""}],
 "basics": {"<basic land name>": 0}, "weak_slots": [],
 "brief": {"how_it_wins": "", "the_line": "", "against": "", "pilot": ""}}
```

`basics` uses only the basic land types the commander's colour identity can
use. `brief` is the user-facing report and is rendered, never written twice.
Four short paragraphs, plain English, no jargon from this prompt, every card name
marked `[[Like This]]`:

- **how_it_wins** — the win condition and the two backups, and what each backup
  survives that the primary does not.
- **the_line** — turns 1 to 8, what you are doing and when you commit.
- **against** — the matchup that beats this deck and what you do about it; which
  cards are political currency and when the deck stops looking harmless.
- **pilot** — the five things someone who has never seen the deck would get
  wrong. Include the mulligan rule and how to use the commander's ability well.

One substantive paragraph per package in `package_notes`. Individual `note`
fields only where a card is exceptional — the only copy of a unique effect, a
flagged weak slot, a card that won on a secondary use.

Never write "dead" or "absent" unlabelled. Use `MECHANICALLY DEAD` (with the
query showing zero legal targets), `OFF-PLAN` (with the line of play it fails),
or `CATEGORY ABSENT` (with the query, the bare-term re-query, and the two cards
you expected to match and checked).

## STEP 6 — Validate, then deliver

```bash
python validate_deck.py          # reads the restriction from build_spec.json; paste raw stdout
python check_restriction.py      # names every restriction axis it checked
python deliver.py
```

A failing check is fixed by changing `deck.json`, never by changing a script.
Three cycles without a clean pass: stop and report the failing check. Record the
**DECK CHECKSUM**.

Then `present_files DECKLIST.md REPORT.md` and write no more than four sentences
in the chat: what the deck does, the land count, the one number you would most
want to improve, and the weakest slot.

## STEP 7 — Leave the evidence on disk

```bash
python baseline.py --lands <your land count> --basics <your basic count>
python compare.py deck.json baseline.txt
```

Report the overlap in one line: how much of the deck popularity alone would have
produced. Every card in the overlap should still be defensible on its text.

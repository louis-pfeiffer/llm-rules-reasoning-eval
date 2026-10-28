# Results

Raw artefacts, kept exactly as the build produced them. They are not edited to look
better; their value is that they are the real output.

## `jetmir-cats/` — full protocol

Commander: **Jetmir, Nexus of Revels**. Restriction: *each creature card in the 99
must be a Cat (changelings excluded), and each creature token created under my
control must be a Cat.*

This is the protocol's second commander under a different restriction, which makes
it the generalisation test: the method was designed on a no-non-land-permanents
build and then applied unchanged here.

| File | What it is |
|---|---|
| `candidates.json` | The shortlist, with the data fingerprint of the inputs it was built from (pool 2,208 rows, collection 8,438, universe 31,830, rules 9,397). |
| `deck.json` | The final 87 cards plus 12 basics, the 34-card bench, slot budget, weakness rows, play lines and package notes. |
| `DECKLIST.md` | The rendered decklist, importable into Moxfield or Archidekt. |
| `REPORT.md` | The written explanation: how the deck wins, the line, and what each package is for. |

## `baseline/` — ablation control

The same two commanders built with `MIN_BUILD.md`, the stripped prompt. These are
the comparison set: same collection, same restriction, same model, without the
components that are supposed to improve the deck.

| File | Commander |
|---|---|
| `jetmir-minimal-DECKLIST.md` | Jetmir, Nexus of Revels — directly comparable to `jetmir-cats/DECKLIST.md` |
| `noyan-dar-minimal-DECKLIST.md` | Noyan Dar, Roil Shaper — no non-land permanents |

## Scoring

`scripts/ablation_score.py` and `scripts/compare.py` score one condition against
another. The measured comparison belongs in [`RESULTS.md`](RESULTS.md), which is
still to be written up.

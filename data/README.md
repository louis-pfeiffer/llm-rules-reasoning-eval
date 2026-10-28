# Data

## Included

- `My_MTG_collection_24_10_2026.xlsx` — the hand-maintained collection spreadsheet
  (~8,500 unique cards, ~18,500 copies). Records name, quantity, colour and rarity only.
- `MTG_collection_annotated.csv` — the same collection joined to Scryfall card data
  (mana cost, CMC, type line, colour identity, oracle text, produced mana, commander
  legality), which is what the pipeline actually reads. Owned quantities are respected
  as a hard constraint: a deck may not use more copies of a card than the collection holds.

## Not included (download these yourself)

Two inputs are third-party data and are **not redistributed** in this repository.
Download them into this folder before running the pipeline.

### 1. Card universe — Scryfall

The pipeline expects `data/scryfall_universe.csv`: every commander-legal card with
name, mana cost, CMC, type line, colour identity, oracle text, produced mana,
legality, game-changer flag, price and EDHREC rank.

Source: Scryfall bulk data — <https://scryfall.com/docs/api/bulk-data>

TODO — commit the small script that turns the Scryfall bulk JSON into this CSV, so the
dataset is reproducible rather than trusted. Credit Scryfall in the script header.

### 2. Comprehensive rules — Wizards of the Coast

The pipeline expects the plain-text comprehensive rules file named in `scripts/config.py`
(`MagicCompRules_<date>.txt`).

Source: <https://magic.wizards.com/en/rules>

Download the current text version and update the filename in `scripts/config.py` if the
date differs. Rules numbering changes between releases, so record which release the
findings were produced against.

## Attribution

Card data is provided by Scryfall. The comprehensive rules are published by Wizards of
the Coast. This is an unofficial fan project, not produced by, endorsed by, supported by,
or affiliated with Wizards of the Coast.

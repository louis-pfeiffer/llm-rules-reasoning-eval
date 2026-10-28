"""ablation_score.py -- one scorecard for any finished build, full or minimal.

The ablation only works if every run is measured the same way. This script reads
deck.json and the pool and prints the same numbers whichever prompt produced the
deck. It never judges quality; it records what can be counted and leaves blanks
for what only a person can judge.

  legal                  min_validate.py's exit status
  baseline overlap       share of the non-basic 99 that a popularity sort alone
                         picks, given THIS deck's own land and basic counts. The
                         commander and basics are excluded from both sides, so
                         the figure is not inflated or deflated by them
                         (compare.py counts basics; don't mix the two figures).
  lands                  floor / ceiling (every multi-face card as spell / as land)
  curve                  mean mana value of non-land cards, and counts by value
  high-impact            game_changer cards in the 99
  function coverage      cards in the 99 per function tag (whatever tag set
                         prep.py produced -- compare runs made with the same kit)
  digest reliance        share of non-land cards that appear in digest.md
  run-to-run overlap     optional: --other path/to/another/deck.json

Run:   python ablation_score.py --label minimal-run1 [--other other_deck.json]
Prints a scorecard and one CSV line to paste into your results sheet.
"""
import argparse
import json
import os
import re
import subprocess
import sys

import pandas as pd

import config

BASICS = {"Plains", "Island", "Swamp", "Mountain", "Forest", "Wastes"}


def nonbasic_names(deck, commander):
    return {config.norm(c["name"]) for c in deck["deck"]
            if c["name"] not in BASICS and config.norm(c["name"]) != config.norm(commander)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True, help="e.g. full-run1, minimal-run2, minus-step6")
    ap.add_argument("--deck", default="deck.json")
    ap.add_argument("--other", default=None)
    a = ap.parse_args()

    deck = json.load(open(a.deck, encoding="utf-8"))
    build = json.load(open("build_spec.json", encoding="utf-8"))
    commander = build.get("commander", deck.get("commander", ""))
    pool = config.load("POOL")
    tagged_path = config.resolve("pool_tagged.csv")
    tagged = pd.read_csv(tagged_path, encoding="utf-8-sig") if tagged_path else pool
    pool["edhrec_rank"] = pd.to_numeric(pool.get("edhrec_rank"), errors="coerce")
    pool["_k"] = pool["name"].map(config.norm)
    mine = nonbasic_names(deck, commander)
    rows = pool[pool["_k"].isin(mine)].drop_duplicates("_k")

    # ---- legality ----
    legal = None
    if os.path.isfile("min_validate.py") and a.deck == "deck.json":
        legal = subprocess.run([sys.executable, "min_validate.py"],
                               capture_output=True, text=True).returncode == 0

    # ---- lands ----
    def is_land_face(t):
        head = str(t).split("\u2014")[0]
        return "Land" in head.split()

    single = rows[~rows["name"].str.contains("//", regex=False)]
    multi = rows[rows["name"].str.contains("//", regex=False)]
    pure = int(single["type_line"].map(is_land_face).sum())
    mdfc = int(multi["type_line"].map(lambda t: any(is_land_face(f) for f in str(t).split("//"))).sum())
    nbasics = sum(int(v) for v in deck.get("basics", {}).values())
    floor, ceiling = pure + nbasics, pure + nbasics + mdfc

    # ---- baseline with THIS deck's land counts ----
    cand = pool[pool["_k"] != config.norm(commander)].sort_values("edhrec_rank", na_position="last")
    landrow = cand["type_line"].map(lambda t: is_land_face(str(t).split("//")[0]))
    n_nonbasic_lands = pure
    base = set(cand[landrow].head(n_nonbasic_lands)["_k"])
    base |= set(cand[~landrow].head(99 - nbasics - n_nonbasic_lands)["_k"])
    overlap = len(mine & base) / max(1, len(mine))

    # ---- curve / impact ----
    spells = rows[~rows["type_line"].map(lambda t: is_land_face(str(t).split("//")[0]))]
    cmc = pd.to_numeric(spells["cmc"], errors="coerce")
    curve = cmc.fillna(0).astype(int).clip(upper=7).value_counts().sort_index().to_dict()
    gc = rows[rows["game_changer"].astype(str).str.lower() == "true"]["name"].tolist() \
        if "game_changer" in rows.columns else []

    # ---- function coverage ----
    cov = {}
    if "tags" in tagged.columns:
        tagged["_k"] = tagged["name"].map(config.norm)
        t = tagged[tagged["_k"].isin(mine)].drop_duplicates("_k")
        for tags in t["tags"].fillna(""):
            for tag in filter(None, tags.split(";")):
                cov[tag] = cov.get(tag, 0) + 1

    # ---- digest reliance ----
    reliance = None
    if os.path.isfile("digest.md"):
        text = config.norm(open("digest.md", encoding="utf-8").read())
        sk = {config.norm(n) for n in spells["name"]}
        reliance = sum(1 for k in sk if k in text) / max(1, len(sk))

    # ---- run-to-run ----
    r2r = None
    if a.other:
        other = json.load(open(a.other, encoding="utf-8"))
        theirs = nonbasic_names(other, commander)
        r2r = len(mine & theirs) / max(1, len(mine | theirs))

    print(f"\nSCORECARD  {a.label}  ({commander} / {build.get('restriction_key')})")
    print(f"  legal (min_validate)        {legal}")
    print(f"  baseline overlap            {overlap:.0%}  of {len(mine)} non-basic cards")
    print(f"  lands floor / ceiling       {floor} / {ceiling}   (basics {nbasics})")
    print(f"  mean mana value (spells)    {cmc.mean():.2f}   curve {curve}")
    print(f"  high-impact cards           {len(gc)}")
    print(f"  digest reliance             {'n/a' if reliance is None else f'{reliance:.0%}'}")
    print(f"  run-to-run jaccard          {'n/a' if r2r is None else f'{r2r:.2f}'}")
    print(f"  function coverage           {dict(sorted(cov.items()))}")
    print("\n  FILL IN BY HAND: validator repair cycles | model 'none/never' claims that "
          "fell | red-team swaps that beat the noise | your blind score 1-5 | tokens used")

    fields = [a.label, commander, build.get("restriction_key"), legal, f"{overlap:.3f}",
              floor, ceiling, f"{cmc.mean():.2f}", len(gc),
              "" if reliance is None else f"{reliance:.3f}", "" if r2r is None else f"{r2r:.3f}",
              "", "", "", "", ""]
    print("\nCSV: label,commander,restriction,legal,baseline_overlap,land_floor,land_ceiling,"
          "mean_mv,high_impact,digest_reliance,run_to_run,repair_cycles,nulls_fell,"
          "swaps_beat_noise,blind_score,tokens")
    print(",".join(str(x) for x in fields))


if __name__ == "__main__":
    main()
